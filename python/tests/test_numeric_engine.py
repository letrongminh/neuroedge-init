"""
TSK-W1-02 Part 2b — Numeric criterion engine, trace, replay, and sim binding.

Covers:
  - Numeric gate compilation shape and schema validation against decision_tree.v1.json
  - End-to-end engine evaluation: offset computation, gate_facts emission, negative age,
    expired age, exact boundary age, plain context numbers without read_ms
  - Fail:open gate behaviour: present failing numeric facts remain blocked
  - Trace serialization: nan/inf/read_offset_ms/eval_offset_ms/age_ms in gate_facts
  - Replay round-trip: recorded_steps parsing nan/inf/offsets, replay reproducing verdicts
  - Tampered age_ms detection: warning emission, fact_age_mismatch event, re-walking with recomputed age
  - Missing read mark / offsets in replay resulting in unavailable (fail closed)
  - [sim.sensor_facts] binding refusal: BoardCapabilityError (NE3001) for numeric criteria
  - Canonical tree byte preservation for existing non-numeric gates
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest

from neuroedge.engine import (
    ActionContractEngine,
    EventLog,
    Fact,
    GateVerdict,
    Reason,
    Unavailable,
    canonicalize,
    compile_tree,
    gate_digest,
    resolve_gate_document,
    resolve_gate_file,
    tree_bytes,
    validate_tree,
)
from neuroedge.engine.compiler import (
    load_agent_manifest,
)
from neuroedge.errors import BoardCapabilityError
from neuroedge.sim.session import SensorFact, _check_bands
from neuroedge.testing import (
    GoldenComparator,
    TracePlayer,
    recorded_steps,
)
from neuroedge.testing.player import fact_mark_problems
from neuroedge.trace import validate_trace

# --- Helpers & Stubs ---------------------------------------------------------


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = float(start)

    def __call__(self) -> float:
        return self.now

    def advance(self, ms: float) -> None:
        self.now += ms


class ScriptedSource:
    """Answers from a script; optionally advances a FakeClock."""

    def __init__(
        self,
        answers: dict[str, Any],
        clock: FakeClock | None = None,
        delay_ms: float = 0,
    ) -> None:
        self.answers = answers
        self.clock = clock
        self.delay_ms = delay_ms
        self.calls: list[str] = []

    async def adjudicate(self, criterion, definition, state, deadline_ms=None):
        self.calls.append(criterion)
        if self.clock is not None:
            self.clock.advance(self.delay_ms)
        return self.answers.get(criterion, Unavailable("empty"))


def make_numeric_gate(
    allow_when: dict[str, Any] | None = None,
    range_bounds: dict[str, float] | None = None,
    max_age_ms: int = 500,
    unit: str = "bar",
    fail_mode: str = "closed",
    name: str = "numeric-test",
    version: str = "1.0.0",
):
    doc = {
        "schema": "neuroedge.gate/v1",
        "name": name,
        "version": version,
        "evaluate": {
            "pressure": {
                "type": "numeric",
                "unit": unit,
                "range": range_bounds or {"min": 0.0, "max": 16.0},
                "max_age_ms": max_age_ms,
                "instructions": "Pressure measurement",
            }
        },
        "allow_when": {
            "pressure": allow_when or {"gte": 2.0, "lt": 8.0},
        },
        "on_block": {"action": "deny"},
        "budget": {"p95_latency_ms": 100, "fail": fail_mode},
    }
    return resolve_gate_document(doc)


# --- 1. Tree Compilation Shape & Schema Validation ----------------------------


def test_numeric_node_exact_shape_and_validation():
    gate = make_numeric_gate(
        allow_when={"gte": 2.0, "lt": 8.0},
        range_bounds={"min": 0.0, "max": 16.0},
        max_age_ms=500,
        unit="bar",
    )
    tree = compile_tree(gate)
    assert len(tree["nodes"]) == 1
    node = tree["nodes"][0]

    # Verify exact top-level keys
    assert set(node.keys()) == {
        "criterion",
        "kind",
        "domain",
        "admitted",
        "confidence_floor",
        "numeric",
    }
    assert node["criterion"] == "pressure"
    assert node["kind"] == "numeric"
    assert node["domain"] == []
    assert node["admitted"] == []
    assert node["confidence_floor"] == 0.0

    # Verify exact numeric record keys
    num = node["numeric"]
    assert set(num.keys()) == {"unit", "range", "max_age_ms", "lower", "upper"}
    assert num["unit"] == "bar"
    assert num["range"] == {"min": 0.0, "max": 16.0}
    assert num["max_age_ms"] == 500
    assert num["lower"] == {"value": 2.0, "closed": True}
    assert num["upper"] == {"value": 8.0, "closed": False}

    # Validate against decision_tree.v1.json
    validate_tree(tree, label="test_numeric_node_exact_shape")


# --- 2. Engine Evaluation & Offset Computation --------------------------------


@pytest.mark.asyncio
async def test_engine_numeric_offsets_and_gate_facts_emission():
    clock = FakeClock(1000.0)
    events = EventLog(clock)
    gate = make_numeric_gate()

    # Reading taken at clock = 1050.0 (offset 50 ms)
    clock.now = 1050.0
    fact = Fact(5.0, read_ms=1050.0, source="sensor")

    # Evaluation occurs at clock = 1200.0 (offset 200 ms)
    clock.now = 1200.0
    source = ScriptedSource({"pressure": fact})
    engine = ActionContractEngine(
        {"numeric-test": gate}, facts_source=source, clock=clock, events=events
    )

    result = await engine.evaluate("numeric-test")
    assert result.verdict is GateVerdict.ALLOW

    # Verify gate_facts event data
    trace = events.to_trace()
    facts_event = next(e for e in trace["events"] if e["type"] == "gate_facts")
    entry = facts_event["data"]["pressure"]
    assert entry["value"] == 5.0
    assert entry["confidence"] is None
    assert entry["source"] == "sensor"
    assert entry["read_offset_ms"] == 50
    assert entry["eval_offset_ms"] == 200
    assert entry["age_ms"] == 150


@pytest.mark.asyncio
async def test_engine_numeric_causality_violation_negative_age():
    clock = FakeClock(1000.0)
    events = EventLog(clock)
    gate = make_numeric_gate()

    # Reading has read_ms in the future relative to eval: read_ms = 1300.0
    fact = Fact(5.0, read_ms=1300.0, source="sensor")

    # Eval runs at clock = 1200.0 (read_offset_ms = 300, eval_offset_ms = 200 -> age_ms = -100)
    clock.now = 1200.0
    source = ScriptedSource({"pressure": fact})
    engine = ActionContractEngine(
        {"numeric-test": gate}, facts_source=source, clock=clock, events=events
    )

    result = await engine.evaluate("numeric-test")
    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is Reason.CRITERION_UNAVAILABLE

    trace = events.to_trace()
    facts_event = next(e for e in trace["events"] if e["type"] == "gate_facts")
    entry = facts_event["data"]["pressure"]
    assert entry["read_offset_ms"] == 300
    assert entry["eval_offset_ms"] == 200
    assert entry["age_ms"] == -100


@pytest.mark.asyncio
async def test_engine_numeric_expired_age():
    clock = FakeClock(1000.0)
    events = EventLog(clock)
    gate = make_numeric_gate(max_age_ms=500)

    # Reading taken at 1050.0 (offset 50)
    fact = Fact(5.0, read_ms=1050.0, source="sensor")

    # Eval runs at 1700.0 (eval_offset_ms = 700 -> age_ms = 650 > 500)
    clock.now = 1700.0
    source = ScriptedSource({"pressure": fact})
    engine = ActionContractEngine(
        {"numeric-test": gate}, facts_source=source, clock=clock, events=events
    )

    result = await engine.evaluate("numeric-test")
    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is Reason.CRITERION_UNAVAILABLE


@pytest.mark.asyncio
async def test_engine_numeric_exact_boundary_age_allows():
    clock = FakeClock(1000.0)
    events = EventLog(clock)
    gate = make_numeric_gate(max_age_ms=500)

    # Reading taken at 1050.0 (offset 50)
    fact = Fact(5.0, read_ms=1050.0, source="sensor")

    # Eval runs at 1550.0 (eval_offset_ms = 550 -> age_ms = 500 == max_age_ms)
    clock.now = 1550.0
    source = ScriptedSource({"pressure": fact})
    engine = ActionContractEngine(
        {"numeric-test": gate}, facts_source=source, clock=clock, events=events
    )

    result = await engine.evaluate("numeric-test")
    assert result.verdict is GateVerdict.ALLOW


@pytest.mark.asyncio
async def test_engine_numeric_plain_context_number_unavailable():
    clock = FakeClock(1000.0)
    events = EventLog(clock)
    gate = make_numeric_gate()
    engine = ActionContractEngine({"numeric-test": gate}, clock=clock, events=events)

    # Plain context number has no read_ms
    clock.now = 1200.0
    result = await engine.evaluate("numeric-test", {"pressure": 5.0})
    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is Reason.CRITERION_UNAVAILABLE

    # Trace keeps exactly 3 keys for facts without read_ms
    trace = events.to_trace()
    facts_event = next(e for e in trace["events"] if e["type"] == "gate_facts")
    entry = facts_event["data"]["pressure"]
    assert set(entry.keys()) == {"value", "confidence", "source"}
    assert entry["value"] == 5.0
    assert "age_ms" not in entry


@pytest.mark.asyncio
async def test_engine_numeric_non_finite_json_safe():
    clock = FakeClock(1000.0)
    events = EventLog(clock)
    gate = make_numeric_gate()

    fact = Fact(float("nan"), read_ms=1050.0, source="sensor")
    clock.now = 1200.0
    source = ScriptedSource({"pressure": fact})
    engine = ActionContractEngine(
        {"numeric-test": gate}, facts_source=source, clock=clock, events=events
    )

    result = await engine.evaluate("numeric-test")
    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is Reason.VALUE_OUT_OF_RANGE

    trace = events.to_trace()
    facts_event = next(e for e in trace["events"] if e["type"] == "gate_facts")
    entry = facts_event["data"]["pressure"]
    assert entry["value"] == "nan"
    assert entry["read_offset_ms"] == 50
    assert entry["eval_offset_ms"] == 200
    assert entry["age_ms"] == 150
    validate_trace(trace)


# --- 3. Fail:Open Gate with Present Failing Fact ------------------------------


# --- 4. Replay: what the trace can account for ---------------------------------


def _setup_numeric_agent(copy_agent, tmp_path) -> Path:
    """Prepare a test agent whose unlock_door gate has a numeric pressure criterion."""
    manifest_path = copy_agent("villa-concierge")
    agent_dir = manifest_path.parent
    gate_yaml = """schema: neuroedge.gate/v1
name: unlock_door
version: 1.0.0
evaluate:
  pressure:
    type: numeric
    unit: bar
    range: { min: 0.0, max: 16.0 }
    max_age_ms: 500
    instructions: Pressure measurement
allow_when:
  pressure: { gte: 2.0, lt: 8.0 }
on_block:
  action: deny
budget:
  p95_latency_ms: 100
  fail: closed
"""
    (agent_dir / "numeric_gate.yaml").write_text(gate_yaml, encoding="utf-8")
    agent_toml = """[agent]
name = "villa-concierge"
version = "0.1.0"

[requires]
"digital.out" = { pins = ["door_lock"] }

[gates]
unlock_door = "numeric_gate.yaml"

[targets]
supported = ["sim", "linux", "esp32s3"]
"""
    manifest_path.write_text(agent_toml, encoding="utf-8")
    return manifest_path


def _trace_with(entry: dict[str, Any], verdict: str = "ALLOW") -> dict[str, Any]:
    """A recorded evaluation (events at 10, 20, 30 ms) whose one fact is `entry`."""
    return {
        "$schema": "https://schema.neuroedge.dev/trace/v1.json",
        "metadata": {
            "session_id": "sess_1111222233334444",
            "timestamp_utc": "2026-01-01T00:00:00Z",
            "target": "sim",
            "board_id": "sim-default",
            "agent_version": "villa-concierge@0.1.0",
        },
        "events": [
            {
                "offset_ms": 0,
                "type": "action_requested",
                "data": {"action": "unlock_door", "arguments": {}},
            },
            {
                "offset_ms": 10,
                "type": "gate_evaluation_begin",
                "data": {"gate": "unlock_door@1.0.0"},
            },
            {"offset_ms": 20, "type": "gate_facts", "data": {"pressure": entry}},
            {
                "offset_ms": 30,
                "type": "gate_evaluation_result",
                "data": {"verdict": verdict, "evaluations": {"pressure": entry.get("value")}},
            },
        ],
    }


def _reading(**marks: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {"value": 5.0, "confidence": None, "source": "sensor"}
    entry.update(marks)
    return entry


CONSISTENT = {"read_offset_ms": 5, "eval_offset_ms": 20, "age_ms": 15}


@pytest.mark.asyncio
async def test_replay_reproduces_a_consistent_numeric_reading(copy_agent, tmp_path):
    agent_path = _setup_numeric_agent(copy_agent, tmp_path)
    trace = _trace_with(_reading(**CONSISTENT))
    [step] = recorded_steps(trace)
    assert step.facts["pressure"].age_ms == 15
    assert step.marks == {"pressure": (5, 20, 15)}
    assert not step.mark_problems
    result = await TracePlayer(trace, target="sim", agent=agent_path).replay()
    assert result.verdicts == ["ALLOW"]
    assert not result.warnings


@pytest.mark.asyncio
async def test_a_replay_can_itself_be_replayed(copy_agent, tmp_path):
    """The replayed trace keeps the read marks, so replaying it again gives the same verdict."""
    agent_path = _setup_numeric_agent(copy_agent, tmp_path)
    first = await TracePlayer(
        _trace_with(_reading(**CONSISTENT)), target="sim", agent=agent_path
    ).replay()
    assert first.verdicts == ["ALLOW"]
    second = await TracePlayer(first.replayed, target="sim", agent=agent_path).replay()
    assert second.verdicts == ["ALLOW"]
    assert not second.warnings


@pytest.mark.asyncio
async def test_replay_with_a_tampered_age_treats_the_reading_as_unavailable(copy_agent, tmp_path):
    agent_path = _setup_numeric_agent(copy_agent, tmp_path)
    # The age claimed is 5 ms but eval - read is 15: the trace was altered.
    trace = _trace_with(_reading(read_offset_ms=5, eval_offset_ms=20, age_ms=5))
    [problem] = fact_mark_problems(trace)
    assert problem.criterion == "pressure"
    assert "differs from eval_offset_ms - read_offset_ms" in problem.why
    result = await TracePlayer(trace, target="sim", agent=agent_path).replay()
    assert result.verdicts == ["BLOCK"]
    assert result.reason == "criterion_unavailable"
    assert any("altered" in w for w in result.warnings)
    assert any(e["type"] == "fact_mark_problem" for e in result.replayed["events"])
    assert not GoldenComparator().compare(result, trace).ok  # recorded ALLOW, replayed BLOCK


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "marks",
    [
        {"read_offset_ms": -9000, "eval_offset_ms": 100000, "age_ms": 109000},  # past the events
        {"read_offset_ms": 19900, "eval_offset_ms": 19990, "age_ms": 90},  # forged, consistent
        {"read_offset_ms": 5, "eval_offset_ms": 9, "age_ms": 4},  # before the evaluation began
    ],
    ids=["after-the-events", "far-after-the-events", "before-begin"],
)
async def test_an_evaluation_instant_outside_the_evaluations_own_events_is_refused(
    copy_agent, tmp_path, marks
):
    agent_path = _setup_numeric_agent(copy_agent, tmp_path)
    trace = _trace_with(_reading(**marks))
    [problem] = fact_mark_problems(trace)
    assert "outside the events of this evaluation" in problem.why
    result = await TracePlayer(trace, target="sim", agent=agent_path).replay()
    assert result.verdicts == ["BLOCK"]
    assert result.reason == "criterion_unavailable"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "marks",
    [
        {"age_ms": 15},  # offsets missing: the age is the trace's own claim
        {"read_offset_ms": 5, "age_ms": 15},
        {"read_offset_ms": 5, "eval_offset_ms": 20},  # no age
        {"read_offset_ms": 5.0, "eval_offset_ms": 20, "age_ms": 15},
        {"read_offset_ms": "5", "eval_offset_ms": 20, "age_ms": 15},
        {"read_offset_ms": True, "eval_offset_ms": 20, "age_ms": 19},
        {"read_offset_ms": 5, "eval_offset_ms": 20, "age_ms": 15.0},
        {"read_offset_ms": None, "eval_offset_ms": 20, "age_ms": 15},
    ],
    ids=repr,
)
async def test_partial_or_malformed_read_marks_replay_as_unavailable(copy_agent, tmp_path, marks):
    agent_path = _setup_numeric_agent(copy_agent, tmp_path)
    trace = _trace_with(_reading(**marks))
    [step] = recorded_steps(trace)
    assert step.facts["pressure"].age_ms is None
    assert "pressure" in step.mark_problems
    result = await TracePlayer(trace, target="sim", agent=agent_path).replay()
    assert result.verdicts == ["BLOCK"]
    assert result.reason == "criterion_unavailable"


@pytest.mark.asyncio
async def test_a_reading_without_any_read_marks_replays_as_unavailable(copy_agent, tmp_path):
    agent_path = _setup_numeric_agent(copy_agent, tmp_path)
    trace = _trace_with(_reading())
    [step] = recorded_steps(trace)
    assert step.facts["pressure"].age_ms is None
    result = await TracePlayer(trace, target="sim", agent=agent_path).replay()
    assert result.verdicts == ["BLOCK"]
    assert result.reason == "criterion_unavailable"


@pytest.mark.parametrize(
    ("text", "check"),
    [("nan", math.isnan), ("inf", lambda v: v == math.inf), ("-inf", lambda v: v == -math.inf)],
)
def test_non_finite_readings_come_back_from_the_trace_as_floats(text, check):
    trace = _trace_with(_reading(value=text, **CONSISTENT))
    [step] = recorded_steps(trace)
    assert check(step.facts["pressure"].value)


def test_a_string_that_looks_non_finite_stays_a_string_without_read_marks():
    [step] = recorded_steps(_trace_with(_reading(value="nan")))
    assert step.facts["pressure"].value == "nan"


# --- 5. [sim.sensor_facts] Refusal on Numeric Criteria (RFC-0009 §3f) ----------


def test_sim_sensor_facts_binding_numeric_refused(copy_agent):
    gate = make_numeric_gate()
    manifest_path = copy_agent("villa-concierge")
    manifest = load_agent_manifest(manifest_path)

    # Direct check via _check_bands
    sensor_facts = {"pressure": SensorFact(sensor="press_1")}
    with pytest.raises(BoardCapabilityError) as exc_info:
        _check_bands(manifest, sensor_facts, {"numeric-test": gate})

    err = exc_info.value
    assert err.code == "NE3001"
    assert "[sim.sensor_facts] pressure" in err.where
    assert "evaluates 'pressure' as 'numeric'" in err.why
    assert "sensor.read" in err.why
    assert "RFC-0009 §3f" in err.why
    assert "bind 'pressure' to a channel with declared unit and range" in err.how


# --- 6. Canonical Tree Byte Preservation for Existing Non-Numeric Gates -------


def test_existing_non_numeric_gates_compile_canonical_bytes(
    gates_dir, gate_fixtures_dir, fixture_registry
):
    """
    Every existing gate without numeric criteria must produce canonical tree bytes
    equal to canonicalize(tree), preserving stored byte representations.
    """
    search_paths = list(gates_dir.rglob("*.yaml")) + list(
        (gate_fixtures_dir / "valid").glob("*.yaml")
    )
    assert search_paths, "found gate files to verify"

    count = 0
    for path in search_paths:
        try:
            gate = resolve_gate_file(path, registry=fixture_registry)
        except Exception:
            continue

        if any(c.kind == "numeric" for c in gate.constraints.values()):
            continue

        tree = compile_tree(gate)
        count += 1

        # Must have no numeric record
        for node in tree["nodes"]:
            assert "numeric" not in node

        validate_tree(tree, label=str(path))
        assert tree_bytes(tree) == canonicalize(tree)
        assert tree["gate_digest"] == gate_digest(gate)

    assert count > 0, "verified canonical bytes on existing non-numeric gates"


# --- 7. Only a HAL read mark makes an age (a source cannot state its own) --------


@pytest.mark.asyncio
@pytest.mark.parametrize("claimed_age", [0, 1, 499])
async def test_a_source_cannot_state_its_own_age(claimed_age):
    """`age_ms` set by a source, with no read mark, must not pass the freshness check."""
    clock = FakeClock(1000.0)
    engine = ActionContractEngine(
        {"g": make_numeric_gate()},
        facts_source=ScriptedSource({"pressure": Fact(5.0, age_ms=claimed_age)}),
        clock=clock,
        events=EventLog(clock),
    )
    result = await engine.evaluate("g")
    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is Reason.CRITERION_UNAVAILABLE


@pytest.mark.asyncio
async def test_a_source_age_does_not_override_the_read_mark():
    """A stale read mark stays stale however fresh the source says the reading is."""
    clock = FakeClock(1000.0)
    events = EventLog(clock)
    clock.now = 2000.0  # the reading is a full second old at evaluation
    engine = ActionContractEngine(
        {"g": make_numeric_gate(max_age_ms=500)},
        facts_source=ScriptedSource({"pressure": Fact(5.0, read_ms=1000.0, age_ms=0)}),
        clock=clock,
        events=events,
    )
    result = await engine.evaluate("g")
    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is Reason.CRITERION_UNAVAILABLE


@pytest.mark.asyncio
async def test_a_live_trace_replays_to_the_same_numeric_verdict_and_age():
    """Live evaluation -> trace -> recorded_steps: the recomputed age is the live age."""
    clock = FakeClock(1000.0)
    events = EventLog(clock)
    clock.now = 1050.0
    fact = Fact(5.0, read_ms=1050.0, source="sensor")
    clock.now = 1200.0
    engine = ActionContractEngine(
        {"g": make_numeric_gate()},
        facts_source=ScriptedSource({"pressure": fact}),
        clock=clock,
        events=events,
    )
    live = await engine.evaluate("g")
    [step] = recorded_steps(events.to_trace())
    assert step.facts["pressure"].age_ms == 150
    assert not fact_mark_problems(events.to_trace())
    tree = compile_tree(make_numeric_gate())
    from neuroedge.engine.decision_tree import walk

    replayed = walk(tree, step.facts)
    assert replayed.verdict is live.verdict
    assert replayed.reason is live.reason


# --- 8. Review fixes: stale marks, malformed marks, rounding, fail:open ---------


def _engine(gate, source, *, start=1000.0, **kwargs):
    clock = FakeClock(start)
    events = EventLog(clock)
    engine = ActionContractEngine(
        {"g": gate}, facts_source=source, clock=clock, events=events, **kwargs
    )
    return engine, clock, events


@pytest.mark.asyncio
@pytest.mark.parametrize("read_ms", [50000.0, 0.0, -5.0])
async def test_a_reading_from_before_the_log_began_is_as_old_as_it_is(read_ms):
    """Not clamped to the start of the log: a cached pre-restart reading is stale, not fresh."""
    engine, clock, events = _engine(make_numeric_gate(max_age_ms=500), None, start=100000.0)
    engine.facts_source = ScriptedSource({"pressure": Fact(5.0, read_ms=read_ms)})
    clock.now = 100100.0
    result = await engine.evaluate("g")
    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is Reason.CRITERION_UNAVAILABLE
    entry = events.of_type("gate_facts")[0]["pressure"]
    assert entry["read_offset_ms"] < 0 and entry["age_ms"] > 500


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "read_ms", [float("nan"), float("inf"), float("-inf"), "abc", True, [1.0], 10**400]
)
async def test_a_malformed_read_mark_blocks_instead_of_raising(read_ms):
    engine, clock, events = _engine(make_numeric_gate(), None)
    engine.facts_source = ScriptedSource({"pressure": Fact(5.0, read_ms=read_ms)})
    result = await engine.evaluate("g")
    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is Reason.CRITERION_UNAVAILABLE
    assert events.of_type("gate_evaluation_result"), "the verdict reaches the trace"


@pytest.mark.asyncio
async def test_ages_are_never_rounded_down_to_fit_the_limit():
    """A reading 500.9 ms old is older than a 500 ms limit; one exactly 500 ms old is not."""
    for evaluated_at, allowed in ((1500.0, True), (1500.4, False), (1500.9, False)):
        engine, clock, _ = _engine(make_numeric_gate(max_age_ms=500), None)
        engine.facts_source = ScriptedSource({"pressure": Fact(5.0, read_ms=1000.0)})
        clock.now = evaluated_at
        assert (await engine.evaluate("g")).allowed is allowed, evaluated_at


@pytest.mark.asyncio
async def test_a_commanded_value_never_satisfies_a_numeric_criterion():
    engine, clock, _ = _engine(make_numeric_gate(), None)
    engine.facts_source = ScriptedSource(
        {"pressure": Fact(5.0, source="commanded", read_ms=clock())}
    )
    result = await engine.evaluate("g")
    assert (result.verdict, result.reason) == (GateVerdict.BLOCK, Reason.CRITERION_UNAVAILABLE)


MIXED_OPEN = {
    "schema": "neuroedge.gate/v1",
    "name": "mixed-open",
    "version": "1.0.0",
    "evaluate": {
        "pressure": {
            "type": "numeric",
            "unit": "bar",
            "range": {"min": 0.0, "max": 16.0},
            "max_age_ms": 500,
            "instructions": "Pressure",
        },
        "door_closed": {"type": "bool", "instructions": "Door is closed"},
    },
    "allow_when": {"pressure": {"lt": 8.0}, "door_closed": True},
    "on_block": {"action": "deny"},
    "budget": {"p95_latency_ms": 100, "fail": "open"},
}


async def _open_gate(answers):
    gate = resolve_gate_document(MIXED_OPEN)
    engine, clock, _ = _engine(gate, ScriptedSource(answers))
    return await engine.evaluate("g")


OFFLINE = Unavailable("offline", "test")


@pytest.mark.asyncio
async def test_fail_open_still_excuses_what_a_non_numeric_source_could_not_say():
    """Regression: the open policy is unchanged when only the bool criterion is unanswered."""
    result = await _open_gate({"pressure": Fact(5.0, read_ms=1000.0), "door_closed": OFFLINE})
    assert result.verdict is GateVerdict.ALLOW
    assert result.fail_mode == "open"
    assert result.reason is Reason.GATE_UNREACHABLE


@pytest.mark.asyncio
async def test_fail_open_does_not_excuse_a_lost_numeric_sensor():
    """RFC-0009 §5: every branch of a numeric criterion blocks, degraded gathering included."""
    result = await _open_gate({"pressure": OFFLINE, "door_closed": Fact(True)})
    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is Reason.CRITERION_UNAVAILABLE
    assert result.failed_criterion == "pressure"


@pytest.mark.asyncio
async def test_fail_open_keeps_a_present_failing_numeric_reading_blocked():
    result = await _open_gate({"pressure": Fact(12.0, read_ms=1000.0), "door_closed": OFFLINE})
    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is Reason.CONDITION_NOT_MET
    assert result.failed_criterion == "pressure"
