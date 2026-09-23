"""
Regressions for the adversarial review of Sprint 2 / A1 (2026-09-23).

Each test reproduces one finding exactly as it was reported — two of them moved
a pin that the design says must stay still — and must keep failing closed.
"""

from __future__ import annotations

import asyncio
import math
from pathlib import Path

import pytest

from neuroedge import action
from neuroedge.actions import Conversation
from neuroedge.engine import (
    ActionContractEngine,
    BreakerState,
    DegradationBreaker,
    EventLog,
    Fact,
    GateRegistry,
    Reason,
    resolve_gate_document,
    resolve_gate_file,
)
from neuroedge.engine.compiler import build
from neuroedge.errors import ActionContractViolation, BuildFailed
from neuroedge.hal import digital
from neuroedge.hal.sim import SimHAL
from neuroedge.models import CommandGrammar, ScriptedSource, SystemOne
from neuroedge.trace import validate_trace

NIGHT_PASSING = {
    "risk_level": "low",
    "room_matches": True,
    "staff_co_authorized": True,
    "request_channel": "in_person",
}


@action(name="rg_unlock", requires="digital.out:door_lock", gate="door")
def _unlock() -> None:
    digital.out("door_lock").pulse(seconds=30)


def _session(gate, *, facts, system_one=None):
    events = EventLog()
    engine = ActionContractEngine({"door": gate}, facts_source=system_one, events=events)
    hal = SimHAL(events=events)
    return Conversation(engine=engine, hal=hal, facts=facts), hal, events


# --- 1. A confidence that is not a probability never passes a floor ---------------


@pytest.mark.parametrize("confidence", [math.nan, True, 5.0, -0.1, "0.99"])
async def test_a_non_probability_confidence_blocks(gates_dir, confidence):
    gate = resolve_gate_file(gates_dir / "unlock_door_night@1.0.0.yaml")
    facts = dict(NIGHT_PASSING, guest_authenticated=Fact(True, confidence))
    c, hal, _ = _session(gate, facts=facts)
    result = await c.do(_unlock)
    assert result.blocked
    assert result.gate.reason is Reason.CRITERION_UNAVAILABLE
    assert hal.pin("door_lock").never_pulsed()


async def test_a_nan_from_the_provider_blocks(gates_dir):
    gate = resolve_gate_file(gates_dir / "unlock_door_night@1.0.0.yaml")
    fast = SystemOne("jev", primary=ScriptedSource({"guest_authenticated": Fact(True, math.nan)}))
    c, hal, _ = _session(gate, facts=NIGHT_PASSING, system_one=fast)
    assert (await c.do(_unlock)).blocked
    assert hal.pin("door_lock").never_pulsed()


# --- 2. fail: open never overrides a decided "no" ---------------------------------


class Slow:
    async def adjudicate(self, *args, **kwargs):
        await asyncio.sleep(10)


@pytest.mark.parametrize("scenario", ["offline", "slow"])
async def test_fail_open_still_blocks_on_a_known_failing_fact(gate_fixtures_dir, scenario):
    gate = resolve_gate_file(
        gate_fixtures_dir / "registry" / "strict-base@1.0.0.yaml",
        registry=GateRegistry(gate_fixtures_dir / "registry"),
    )
    assert not gate.fails_closed
    fast = (
        SystemOne("jev", network="offline")
        if scenario == "offline"
        else SystemOne("jev", primary=Slow())
    )
    facts = {"risk_level": "high", "request_channel": "phone"}
    c, hal, _ = _session(gate, facts=facts, system_one=fast)
    result = await c.do(_unlock)
    assert result.blocked
    assert result.gate.reason is Reason.CONDITION_NOT_MET
    assert hal.pin("door_lock").never_pulsed()


async def test_fail_open_allows_only_what_could_not_be_decided(gate_fixtures_dir):
    gate = resolve_gate_file(gate_fixtures_dir / "registry" / "strict-base@1.0.0.yaml")
    facts = {"risk_level": "low", "request_channel": "app"}
    c, hal, _ = _session(gate, facts=facts, system_one=SystemOne("jev", network="offline"))
    result = await c.do(_unlock)
    assert not result.blocked
    assert (result.gate.fail_mode, result.gate.reason) == ("open", Reason.GATE_UNREACHABLE)


# --- 3. A provider that raises or hangs is a degraded verdict -------------------------


class Raising:
    async def adjudicate(self, *args, **kwargs):
        raise ConnectionError("provider reset the connection")


async def test_a_raising_primary_trips_the_breaker_and_uses_the_fallback(root):
    grammar = CommandGrammar.load(
        root / "fixtures" / "agents" / "villa-concierge" / "commands.toml"
    )
    breaker = DegradationBreaker(failure_threshold=1)
    gate = resolve_gate_document(
        {
            "schema": "neuroedge.gate/v1",
            "name": "voice",
            "version": "1.0.0",
            "evaluate": {"command_recognized": {"type": "bool", "instructions": "Known command"}},
            "allow_when": {"command_recognized": {"confidence_gte": 0.8}},
            "on_block": {"action": "deny"},
            "budget": {"p95_latency_ms": 500},
        }
    )
    fast = SystemOne("jev", primary=Raising(), fallback=grammar, breaker=breaker)
    c, hal, events = _session(gate, facts={}, system_one=fast)
    c.utterance = "mở cửa"
    result = await c.do(_unlock)
    assert not result.blocked, "the grammar fallback answered"
    assert breaker.state is BreakerState.OPEN


async def test_a_source_that_raises_through_the_engine_is_gate_unreachable(gates_dir):
    gate = resolve_gate_file(gates_dir / "unlock_door@1.2.0.yaml")
    c, hal, events = _session(
        gate, facts={"room_matches": True, "risk_level": "low"}, system_one=Raising()
    )
    result = await c.do(_unlock)
    assert result.gate.reason is Reason.GATE_UNREACHABLE
    assert events.of_type("gate_evaluation_result"), "the trace records the verdict"
    validate_trace(events.to_trace())
    assert hal.pin("door_lock").never_pulsed()


async def test_a_hanging_primary_is_cut_off_at_the_budget(gates_dir):
    gate = resolve_gate_file(gates_dir / "unlock_door@1.2.0.yaml")
    fast = SystemOne("jev", primary=Slow())
    c, hal, _ = _session(gate, facts={"room_matches": True, "risk_level": "low"}, system_one=fast)
    result = await asyncio.wait_for(c.do(_unlock), timeout=2)
    assert result.gate.reason is Reason.BUDGET_EXCEEDED
    assert hal.pin("door_lock").never_pulsed()


# --- 4. A fallback that needs arguments is refused, not a TypeError -------------------


@action(name="rg_notify", requires="digital.out:porch_light", gate="notify")
def _notify(room: str) -> None:
    digital.out("porch_light").on()


def _one(name, on_block):
    return resolve_gate_document(
        {
            "schema": "neuroedge.gate/v1",
            "name": name,
            "version": "1.0.0",
            "evaluate": {"ok": {"type": "bool", "instructions": "Precondition"}},
            "allow_when": {"ok": True},
            "on_block": on_block,
            "budget": {"p95_latency_ms": 100},
        }
    )


async def test_a_fallback_requiring_arguments_is_skipped_at_run_time():
    events = EventLog()
    engine = ActionContractEngine(
        {
            "door": _one("door", {"action": "degrade", "fallback_action": "rg_notify"}),
            "notify": _one("notify", {"action": "deny"}),
        },
        events=events,
    )
    c = Conversation(engine=engine, hal=SimHAL(events=events), facts={"ok": False})
    result = await c.do(_unlock)
    assert result.blocked and result.fallback is None
    assert events.of_type("fallback_skipped") == [
        {"action": "rg_notify", "reason": "fallback requires arguments"}
    ]


def test_the_build_refuses_a_fallback_requiring_arguments(tmp_path: Path, gate_fixtures_dir):
    (tmp_path / "gates").mkdir()
    (tmp_path / "gates" / "door.yaml").write_text(
        "schema: neuroedge.gate/v1\nname: door\nversion: 1.0.0\n"
        "evaluate:\n  ok: { type: bool, instructions: Precondition }\n"
        "allow_when:\n  ok: true\n"
        "on_block: { action: degrade, fallback_action: rg_build_notify }\n"
        "budget: { p95_latency_ms: 100 }\n",
        encoding="utf-8",
    )
    (tmp_path / "actions").mkdir()
    (tmp_path / "actions" / "notify.py").write_text(
        "from neuroedge import action\n"
        "@action(name='rg_build_notify', requires='digital.out:porch_light', gate='door')\n"
        "def notify(room: str) -> None:\n    return None\n",
        encoding="utf-8",
    )
    (tmp_path / "agent.toml").write_text(
        '[agent]\nname = "rg-agent"\nversion = "0.0.1"\n'
        '[requires]\n"digital.out" = { pins = ["porch_light"] }\n'
        '[gates]\ndoor = "gates/door.yaml"\n',
        encoding="utf-8",
    )
    with pytest.raises(BuildFailed) as excinfo:
        build(tmp_path / "agent.toml", target="sim", board_id="sim-default")
    assert any("requires some" in p.why for p in excinfo.value.problems)


# --- 5. Any accepted command makes a pin "touched" --------------------------------------


@action(name="rg_on", requires="digital.out:door_lock", gate="door")
def _switch_on() -> None:
    digital.out("door_lock").on()


@action(name="rg_pulse_then_off", requires="digital.out:porch_light", gate="door")
def _pulse_then_off() -> None:
    digital.out("porch_light").pulse(seconds=1)


async def test_on_is_not_never_pulsed_and_off_does_not_erase_a_pulse():
    engine = ActionContractEngine({"door": _one("door", {"action": "deny"})})
    hal = SimHAL(events=engine.events)
    c = Conversation(engine=engine, hal=hal, facts={"ok": True})
    await c.do(_switch_on)
    assert not hal.pin("door_lock").never_pulsed()

    await c.do(_pulse_then_off)
    hal.pins["porch_light"].record("off", 0)
    assert hal.pin("porch_light").pulsed
    assert not hal.pin("porch_light").pulsed_once(), "two commands is not once"


# --- 6. A task spawned in the body cannot rerun the action after c.do() ---------------

LATER: list[asyncio.Task] = []
BODY_RAN: list[str] = []


@action(name="rg_spawner", requires="digital.out:door_lock", gate="door")
def _spawner() -> None:
    BODY_RAN.append("ran")
    LATER.append(asyncio.get_running_loop().create_task(_call_later()))


async def _call_later() -> None:
    await asyncio.sleep(0)
    _spawner()


async def test_a_spawned_task_cannot_call_the_action_after_c_do_returns():
    engine = ActionContractEngine({"door": _one("door", {"action": "deny"})})
    c = Conversation(engine=engine, hal=SimHAL(events=engine.events), facts={"ok": True})
    BODY_RAN.clear()
    await c.do(_spawner)
    with pytest.raises(ActionContractViolation):
        await LATER.pop()
    assert BODY_RAN == ["ran"]
