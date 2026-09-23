"""
TSK-S2-04 — fail-closed and the degradation circuit breaker.

The A4 matrix: every way adjudication can degrade must BLOCK and leave the pin
untouched, on every sample gate. Offline *with* a working fallback is the one
row that evaluates normally (Q-14).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from neuroedge.engine import (
    ActionContractEngine,
    BreakerState,
    DegradationBreaker,
    EventLog,
    Fact,
    GateVerdict,
    Reason,
    Unavailable,
    resolve_gate_file,
)
from neuroedge.errors import PerceptionUnavailableError
from neuroedge.hal.sim import SimHAL
from neuroedge.models import ScriptedSource, SystemOne
from neuroedge.trace import validate_trace


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, ms: float) -> None:
        self.now += ms


class Broken:
    async def adjudicate(self, *args, **kwargs):
        raise PerceptionUnavailableError(where="fallback", why="crashed", how="restart")


SAMPLE_GATES = {
    "base-access": "hospitality/base-access@1.0.0.yaml",
    "unlock_door": "unlock_door@1.2.0.yaml",
    "unlock_door_night": "unlock_door_night@1.0.0.yaml",
}

# Everything but guest_authenticated passes; that one comes from SystemOne.
PASSING_CONTEXT = {
    "risk_level": "low",
    "room_matches": True,
    "staff_co_authorized": True,
    "request_channel": "in_person",
}


def _system_one(scenario: str, clock: FakeClock, events: EventLog) -> SystemOne | None:
    if scenario == "offline_no_fallback":
        return SystemOne("jev", network="offline", events=events)
    if scenario == "offline_fallback_crashes":
        return SystemOne("jev", network="offline", fallback=Broken(), events=events)
    if scenario == "breaker_open_no_fallback":
        breaker = DegradationBreaker(failure_threshold=1, clock=clock)
        breaker.record_failure("timeout")
        return SystemOne("jev", primary=ScriptedSource({}), breaker=breaker)
    answers = {
        "timeout": Unavailable("timeout"),
        "malformed": Unavailable("malformed"),
        "out_of_domain": Fact("maybe", 1.0),
        "missing_criterion": Unavailable("empty"),
    }
    if scenario == "slow":
        return SystemOne(
            "jev",
            primary=ScriptedSource(
                {"guest_authenticated": Fact(True, 1.0)}, clock=clock, delay_ms=10_000
            ),
        )
    return SystemOne("jev", primary=ScriptedSource({"guest_authenticated": answers[scenario]}))


DEGRADATIONS = {
    "offline_no_fallback": Reason.GATE_UNREACHABLE,
    "offline_fallback_crashes": Reason.GATE_UNREACHABLE,
    "breaker_open_no_fallback": Reason.GATE_UNREACHABLE,
    "timeout": Reason.BUDGET_EXCEEDED,
    "slow": Reason.BUDGET_EXCEEDED,
    "malformed": Reason.CRITERION_UNAVAILABLE,
    "out_of_domain": Reason.CRITERION_UNAVAILABLE,
    "missing_criterion": Reason.CRITERION_UNAVAILABLE,
}


async def _attempt(gates_dir: Path, gate: str, system_one, clock, events, key="door"):
    engine = ActionContractEngine(facts_source=system_one, clock=clock, events=events)
    engine.register("door", resolve_gate_file(gates_dir / SAMPLE_GATES[gate]))
    hal = SimHAL(events=events)
    result = await engine.evaluate(key, PASSING_CONTEXT)
    if result.allowed:
        hal.digital_out("door_lock", "pulse", 30_000, signature=result.gate_digest)
    return result, hal


# --- The A4 matrix ------------------------------------------------------------------


@pytest.mark.parametrize("gate", sorted(SAMPLE_GATES))
@pytest.mark.parametrize("scenario", sorted(DEGRADATIONS))
async def test_every_degradation_blocks_and_leaves_the_pin_untouched(gates_dir, gate, scenario):
    clock, events = FakeClock(), EventLog()
    result, hal = await _attempt(
        gates_dir, gate, _system_one(scenario, clock, events), clock, events
    )

    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is DEGRADATIONS[scenario]
    assert hal.pin("door_lock").never_pulsed()
    validate_trace(events.to_trace())


async def test_missing_confidence_on_a_floor_node_blocks(gates_dir):
    clock, events = FakeClock(), EventLog()
    fast = SystemOne("jev", primary=ScriptedSource({"guest_authenticated": Fact(True, None)}))
    result, hal = await _attempt(gates_dir, "unlock_door_night", fast, clock, events)
    assert result.reason is Reason.CONFIDENCE_UNAVAILABLE
    assert hal.pin("door_lock").never_pulsed()


@pytest.mark.parametrize("gate", sorted(SAMPLE_GATES))
async def test_an_unknown_gate_blocks_and_leaves_the_pin_untouched(gates_dir, gate):
    clock, events = FakeClock(), EventLog()
    fast = SystemOne("jev", primary=ScriptedSource({"guest_authenticated": Fact(True, 1.0)}))
    result, hal = await _attempt(gates_dir, gate, fast, clock, events, key="safe")
    assert result.reason is Reason.GATE_NOT_FOUND
    assert hal.pin("door_lock").never_pulsed()


@pytest.mark.parametrize("gate", sorted(SAMPLE_GATES))
async def test_offline_with_a_working_fallback_evaluates_normally(gates_dir, gate):
    clock, events = FakeClock(), EventLog()
    fallback = ScriptedSource({"guest_authenticated": Fact(True, 1.0, source="local")})
    fast = SystemOne("jev", network="offline", fallback=fallback, events=events)
    result, hal = await _attempt(gates_dir, gate, fast, clock, events)
    assert result.allowed
    assert hal.pin("door_lock").pulsed_once(duration_ms=30_000)


# --- The breaker state machine --------------------------------------------------------


def test_the_breaker_opens_after_the_threshold_and_half_opens_after_cooldown():
    clock, events = FakeClock(), EventLog()
    breaker = DegradationBreaker(failure_threshold=3, cooldown_ms=1_000, clock=clock, events=events)
    for _ in range(2):
        breaker.record_failure("timeout")
    assert breaker.state is BreakerState.CLOSED
    breaker.record_failure("timeout")
    assert breaker.state is BreakerState.OPEN
    assert not breaker.allow_primary()

    clock.advance(999)
    assert breaker.state is BreakerState.OPEN
    clock.advance(1)
    assert breaker.state is BreakerState.HALF_OPEN
    assert breaker.allow_primary()
    assert [e["state"] for e in events.of_type("circuit_breaker")] == ["open", "half_open"]


def test_a_half_open_success_closes_and_a_failure_reopens():
    clock = FakeClock()
    breaker = DegradationBreaker(failure_threshold=1, cooldown_ms=100, clock=clock)
    breaker.record_failure("offline")
    clock.advance(100)
    assert breaker.state is BreakerState.HALF_OPEN
    breaker.record_failure("offline")
    assert breaker.state is BreakerState.OPEN

    clock.advance(100)
    assert breaker.state is BreakerState.HALF_OPEN
    breaker.record_success()
    assert breaker.state is BreakerState.CLOSED


def test_a_success_resets_the_failure_count():
    breaker = DegradationBreaker(failure_threshold=2, clock=FakeClock())
    breaker.record_failure("timeout")
    breaker.record_success()
    breaker.record_failure("timeout")
    assert breaker.state is BreakerState.CLOSED


@pytest.mark.parametrize("kwargs", [{"failure_threshold": 0}, {"cooldown_ms": 0}])
def test_invalid_breaker_settings_are_refused(kwargs):
    with pytest.raises(ValueError):
        DegradationBreaker(**kwargs)


async def test_while_open_the_primary_is_never_called_and_the_fallback_answers():
    clock = FakeClock()
    breaker = DegradationBreaker(failure_threshold=1, clock=clock)
    primary = ScriptedSource({"guest_authenticated": Unavailable("timeout")})
    fallback = ScriptedSource({"guest_authenticated": Fact(True, 1.0)})
    fast = SystemOne("jev", primary=primary, fallback=fallback, breaker=breaker)
    definition = {"type": "bool"}

    await fast.adjudicate("guest_authenticated", definition, None)
    assert breaker.state is BreakerState.OPEN
    answer = await fast.adjudicate("guest_authenticated", definition, None)

    assert primary.calls == ["guest_authenticated"], "skipped while open"
    assert answer == Fact(True, 1.0)
