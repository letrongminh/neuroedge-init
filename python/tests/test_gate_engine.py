"""
TSK-S2-03 — Gate Engine: evaluate, allow_when, on_block (Q-17), budget (FR-GATE-09).

The three canonical traces are the reference: the engine must produce the same
`gate_evaluation_result` data they record.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from neuroedge.engine import (
    ActionContractEngine,
    EventLog,
    Fact,
    GateRegistry,
    GateVerdict,
    Reason,
    Unavailable,
    resolve_gate_document,
    resolve_gate_file,
)
from neuroedge.trace import validate_trace


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, ms: float) -> None:
        self.now += ms


class ScriptedSource:
    """Answers from a script; optionally costs `delay_ms` of fake time per call."""

    def __init__(self, answers: dict, clock: FakeClock | None = None, delay_ms: float = 0) -> None:
        self.answers = answers
        self.clock = clock
        self.delay_ms = delay_ms
        self.calls: list[str] = []

    async def adjudicate(self, criterion, definition, state, deadline_ms):
        self.calls.append(criterion)
        if self.clock is not None:
            self.clock.advance(self.delay_ms)
        return self.answers.get(criterion, Unavailable("empty"))


def _canonical_result(root: Path, name: str) -> dict:
    trace = json.loads((root / "fixtures" / "traces" / f"{name}.json").read_text())
    return next(e["data"] for e in trace["events"] if e["type"] == "gate_evaluation_result")


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def engine_for(gates_dir: Path, clock: FakeClock):
    def build(rel: str = "unlock_door@1.2.0.yaml", **kwargs) -> ActionContractEngine:
        engine = ActionContractEngine(clock=clock, events=EventLog(clock), **kwargs)
        engine.register("unlock_door", resolve_gate_file(gates_dir / rel))
        return engine

    return build


HAPPY = {"guest_authenticated": True, "room_matches": True, "risk_level": "low"}
UNVERIFIED = {"guest_authenticated": False, "room_matches": False, "risk_level": "high"}


# --- The three canonical traces ---------------------------------------------


async def test_happy_path_matches_the_canonical_trace(root, engine_for):
    engine = engine_for()
    result = await engine.evaluate("unlock_door", HAPPY)
    assert result.verdict is GateVerdict.ALLOW
    assert result.blocked_by is None
    assert result.to_event_data() == _canonical_result(root, "happy-path")


async def test_unverified_attempt_escalates_and_contains_the_canonical_trace(root, engine_for):
    escalations = []
    engine = engine_for(on_escalate=escalations.append)
    result = await engine.evaluate("unlock_door", UNVERIFIED)

    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is Reason.CONDITION_NOT_MET
    assert result.failed_criterion == "guest_authenticated"
    assert result.escalated_to == "human_receptionist"
    assert escalations == [result]
    # The canonical trace predates `reason`; everything it records must match.
    assert _canonical_result(root, "unverified_attempt").items() <= result.to_event_data().items()


async def test_offline_without_a_fallback_matches_the_canonical_trace(root, engine_for):
    escalations = []
    source = ScriptedSource({"guest_authenticated": Unavailable("offline")})
    engine = engine_for(facts_source=source, on_escalate=escalations.append)
    result = await engine.evaluate("unlock_door", {"room_matches": True, "risk_level": "low"})

    assert result.reason is Reason.GATE_UNREACHABLE
    assert result.to_event_data() == _canonical_result(root, "network_offline")
    assert escalations == [], "a degraded verdict runs no on_block hook"


# --- Reasons -------------------------------------------------------------------


async def test_a_missing_fact_blocks_as_criterion_unavailable(engine_for):
    result = await engine_for().evaluate("unlock_door", {"guest_authenticated": True})
    assert result.reason is Reason.CRITERION_UNAVAILABLE
    assert result.failed_criterion == "risk_level"


async def test_an_out_of_domain_fact_blocks_as_criterion_unavailable(engine_for):
    facts = dict(HAPPY, risk_level="extreme")
    assert (
        await engine_for().evaluate("unlock_door", facts)
    ).reason is Reason.CRITERION_UNAVAILABLE


async def test_missing_confidence_on_a_floor_blocks_without_raising(engine_for):
    engine = engine_for("unlock_door_night@1.0.0.yaml")
    facts = dict(
        HAPPY,
        guest_authenticated=Fact(True, None),
        staff_co_authorized=True,
        request_channel="app",
    )
    result = await engine.evaluate("unlock_door", facts)
    assert result.reason is Reason.CONFIDENCE_UNAVAILABLE


async def test_the_fact_source_fills_what_the_context_lacks(engine_for):
    source = ScriptedSource({"guest_authenticated": Fact(True, 0.97, source="SystemOne")})
    engine = engine_for(facts_source=source)
    result = await engine.evaluate("unlock_door", {"room_matches": True, "risk_level": "low"})
    assert result.allowed
    assert source.calls == ["guest_authenticated"]


async def test_a_refused_answer_is_criterion_unavailable_not_degraded(engine_for):
    source = ScriptedSource({"guest_authenticated": Unavailable("malformed")})
    engine = engine_for(facts_source=source)
    result = await engine.evaluate("unlock_door", {"room_matches": True, "risk_level": "low"})
    assert result.reason is Reason.CRITERION_UNAVAILABLE
    assert result.on_block_action == "escalate"


async def test_an_unknown_gate_blocks(engine_for):
    result = await engine_for().evaluate("open_safe", HAPPY)
    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is Reason.GATE_NOT_FOUND
    assert result.blocked_by == "open_safe"


# --- on_block, Q-17 --------------------------------------------------------------

ONE_CRITERION = {
    "schema": "neuroedge.gate/v1",
    "version": "1.0.0",
    "evaluate": {"ok": {"type": "bool", "instructions": "Precondition holds"}},
    "allow_when": {"ok": True},
    "budget": {"p95_latency_ms": 100},
}


@pytest.mark.parametrize(
    ("on_block", "expected"),
    [
        ({"action": "deny"}, {}),
        (
            {"action": "escalate", "to": "night_duty_manager", "message": "Call"},
            {"escalated_to": "night_duty_manager", "message": "Call"},
        ),
        ({"action": "ask", "message": "Which room?"}, {"message": "Which room?"}),
        (
            {"action": "degrade", "fallback_action": "notify_front_desk"},
            {"fallback_action": "notify_front_desk"},
        ),
    ],
)
async def test_every_on_block_behaviour_blocks(clock, on_block, expected):
    calls = {"escalate": [], "ask": []}
    gate = resolve_gate_document(dict(ONE_CRITERION, name="one", on_block=on_block))
    engine = ActionContractEngine(
        {"one": gate},
        clock=clock,
        on_escalate=calls["escalate"].append,
        on_ask=calls["ask"].append,
    )
    result = await engine.evaluate("one", {"ok": False})

    assert result.verdict is GateVerdict.BLOCK
    assert result.on_block_action == on_block["action"]
    for key, value in expected.items():
        assert result.to_event_data()[key] == value
    assert len(calls["escalate"]) == (on_block["action"] == "escalate")
    assert len(calls["ask"]) == (on_block["action"] == "ask")


async def test_a_failing_hook_never_changes_the_verdict(engine_for):
    def explode(_):
        raise RuntimeError("pager down")

    engine = engine_for(on_escalate=explode)
    result = await engine.evaluate("unlock_door", UNVERIFIED)
    assert result.verdict is GateVerdict.BLOCK
    assert engine.events.of_type("on_block_hook_error")[0]["error"] == "RuntimeError: pager down"


# --- Budget, FR-GATE-09 ---------------------------------------------------------


async def test_a_slow_source_exceeds_the_budget_and_fails_closed(engine_for, clock):
    source = ScriptedSource({"guest_authenticated": Fact(True, 1.0)}, clock=clock, delay_ms=130)
    engine = engine_for(facts_source=source)
    result = await engine.evaluate("unlock_door", {"room_matches": True, "risk_level": "low"})
    assert result.reason is Reason.BUDGET_EXCEEDED
    assert (result.verdict, result.on_block_action, result.fail_mode) == (
        GateVerdict.BLOCK,
        "deny",
        "closed",
    )


async def test_a_timeout_answer_is_budget_exceeded(engine_for):
    source = ScriptedSource({"guest_authenticated": Unavailable("timeout")})
    engine = engine_for(facts_source=source)
    result = await engine.evaluate("unlock_door", {"room_matches": True, "risk_level": "low"})
    assert result.reason is Reason.BUDGET_EXCEEDED


async def test_the_leaf_budget_applies(engine_for, clock):
    """base 200 ms → unlock_door 120 → night 90: 100 ms of adjudication is too slow."""
    source = ScriptedSource({"guest_authenticated": Fact(True, 1.0)}, clock=clock, delay_ms=100)
    engine = engine_for("unlock_door_night@1.0.0.yaml", facts_source=source)
    facts = dict(HAPPY, staff_co_authorized=True, request_channel="app")
    del facts["guest_authenticated"]
    assert (await engine.evaluate("unlock_door", facts)).reason is Reason.BUDGET_EXCEEDED


async def test_a_gate_declaring_fail_open_allows_on_degradation(gate_fixtures_dir, clock):
    gate = resolve_gate_file(
        gate_fixtures_dir / "valid" / "explicit_fail_open.yaml",
        registry=GateRegistry(gate_fixtures_dir / "registry"),
    )
    source = ScriptedSource({}, clock=clock)
    source.answers = {name: Unavailable("offline") for name in gate.constraints}
    engine = ActionContractEngine({"g": gate}, facts_source=source, clock=clock)
    result = await engine.evaluate("g", {})
    assert result.verdict is GateVerdict.ALLOW
    assert (result.fail_mode, result.reason) == ("open", Reason.GATE_UNREACHABLE)


# --- Trace and I/O ----------------------------------------------------------------


async def test_every_emitted_trace_validates(engine_for):
    engine = engine_for()
    for facts in (HAPPY, UNVERIFIED, {}):
        await engine.evaluate("unlock_door", facts)
    await engine.evaluate("missing", {})
    validate_trace(engine.events.to_trace())
    begin = engine.events.of_type("gate_evaluation_begin")[0]
    assert begin["gate"] == "unlock_door@1.2.0"
    assert begin["gate_digest"].startswith("sha256:")


async def test_evaluate_does_no_file_io(engine_for, monkeypatch):
    engine = engine_for()

    def refuse(*args, **kwargs):
        raise AssertionError("evaluate() touched the filesystem")

    monkeypatch.setattr(GateRegistry, "load", refuse)
    monkeypatch.setattr("builtins.open", refuse)
    monkeypatch.setattr(Path, "read_text", refuse)
    assert (await engine.evaluate("unlock_door", HAPPY)).allowed
