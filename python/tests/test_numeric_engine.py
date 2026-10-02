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
from neuroedge.testing.player import fact_age_mismatches
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


@pytest.mark.asyncio
async def test_fail_open_gate_blocks_present_failing_numeric_fact():
    gate = make_numeric_gate(
        allow_when={"gte": 2.0, "lt": 8.0},
        range_bounds={"min": 0.0, "max": 16.0},
        max_age_ms=500,
        fail_mode="open",
    )

    # Case A: Value outside admitted interval (condition_not_met)
    clock = FakeClock(1000.0)
    events = EventLog(clock)
    clock.now = 1050.0
    fact = Fact(10.0, read_ms=1050.0, source="sensor")
    clock.now = 1200.0
    engine = ActionContractEngine(
        {"numeric-test": gate},
        facts_source=ScriptedSource({"pressure": fact}),
        clock=clock,
        events=events,
    )
    result = await engine.evaluate("numeric-test")
    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is Reason.CONDITION_NOT_MET

    # Case B: Value outside declared range (value_out_of_range)
    clock = FakeClock(1000.0)
    events = EventLog(clock)
    clock.now = 1050.0
    fact_oor = Fact(20.0, read_ms=1050.0, source="sensor")
    clock.now = 1200.0
    engine_oor = ActionContractEngine(
        {"numeric-test": gate},
        facts_source=ScriptedSource({"pressure": fact_oor}),
        clock=clock,
        events=events,
    )
    result_oor = await engine_oor.evaluate("numeric-test")
    assert result_oor.verdict is GateVerdict.BLOCK
    assert result_oor.reason is Reason.VALUE_OUT_OF_RANGE

    # Case C: Expired age (criterion_unavailable)
    clock = FakeClock(1000.0)
    events = EventLog(clock)
    clock.now = 1050.0
    fact_exp = Fact(5.0, read_ms=1050.0, source="sensor")
    clock.now = 1700.0  # age 650 > 500
    engine_exp = ActionContractEngine(
        {"numeric-test": gate},
        facts_source=ScriptedSource({"pressure": fact_exp}),
        clock=clock,
        events=events,
    )
    result_exp = await engine_exp.evaluate("numeric-test")
    assert result_exp.verdict is GateVerdict.BLOCK
    assert result_exp.reason is Reason.CRITERION_UNAVAILABLE


# --- 4. Replay & Tampered Age Verification ------------------------------------


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


@pytest.mark.asyncio
async def test_replay_reproduces_numeric_verdict(copy_agent, tmp_path):
    agent_path = _setup_numeric_agent(copy_agent, tmp_path)
    trace = {
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
            {
                "offset_ms": 20,
                "type": "gate_facts",
                "data": {
                    "pressure": {
                        "value": 5.0,
                        "confidence": None,
                        "source": "sensor",
                        "read_offset_ms": 50,
                        "eval_offset_ms": 200,
                        "age_ms": 150,
                    }
                },
            },
            {
                "offset_ms": 30,
                "type": "gate_evaluation_result",
                "data": {"verdict": "ALLOW", "evaluations": {"pressure": 5.0}},
            },
        ],
    }

    # Step parsing
    steps = recorded_steps(trace)
    assert len(steps) == 1
    assert steps[0].facts["pressure"].age_ms == 150
    assert steps[0].facts["pressure"].value == 5.0

    # Full replay
    player = TracePlayer(trace, target="sim", agent=agent_path)
    result = await player.replay()
    assert result.verdicts == ["ALLOW"]
    assert result.recorded_verdicts == ["ALLOW"]


@pytest.mark.asyncio
async def test_replay_tampered_age_ms_mismatch(copy_agent, tmp_path):
    agent_path = _setup_numeric_agent(copy_agent, tmp_path)
    # The recorded trace claims age_ms: 150 and verdict ALLOW, but eval - read = 700 - 50 = 650 > 500!
    trace = {
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
            {
                "offset_ms": 20,
                "type": "gate_facts",
                "data": {
                    "pressure": {
                        "value": 5.0,
                        "confidence": None,
                        "source": "sensor",
                        "read_offset_ms": 50,
                        "eval_offset_ms": 700,
                        "age_ms": 150,  # Tampered: 700 - 50 != 150
                    }
                },
            },
            {
                "offset_ms": 30,
                "type": "gate_evaluation_result",
                "data": {"verdict": "ALLOW", "evaluations": {"pressure": 5.0}},
            },
        ],
    }

    # Verify fact_age_mismatches detects the discrepancy
    mismatches = fact_age_mismatches(trace["events"])
    assert len(mismatches) == 1
    assert mismatches[0].recorded_age_ms == 150
    assert mismatches[0].recomputed_age_ms == 650

    # Replay re-walks with recomputed age 650 -> blocks with criterion_unavailable
    player = TracePlayer(trace, target="sim", agent=agent_path)
    result = await player.replay()

    assert result.verdicts == ["BLOCK"]
    assert result.recorded_verdicts == ["ALLOW"]
    assert result.reason == "criterion_unavailable"
    assert any("differs from eval_offset_ms - read_offset_ms" in w for w in result.warnings)
    assert any(e["type"] == "fact_age_mismatch" for e in result.replayed["events"])

    diff = GoldenComparator().compare(result, trace)
    assert not diff.ok


@pytest.mark.asyncio
async def test_replay_missing_offsets_replays_unavailable(copy_agent, tmp_path):
    agent_path = _setup_numeric_agent(copy_agent, tmp_path)
    # A numeric entry missing read_offset_ms / eval_offset_ms / age_ms
    trace = {
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
            {
                "offset_ms": 20,
                "type": "gate_facts",
                "data": {
                    "pressure": {
                        "value": 5.0,
                        "confidence": None,
                        "source": "sensor",
                        # Missing read_offset_ms, eval_offset_ms, age_ms
                    }
                },
            },
            {
                "offset_ms": 30,
                "type": "gate_evaluation_result",
                "data": {"verdict": "ALLOW", "evaluations": {"pressure": 5.0}},
            },
        ],
    }

    # Must parse with age_ms = None
    steps = recorded_steps(trace)
    assert steps[0].facts["pressure"].age_ms is None

    # Replay re-walks as unavailable, never as a pass
    player = TracePlayer(trace, target="sim", agent=agent_path)
    result = await player.replay()
    assert result.verdicts == ["BLOCK"]
    assert result.reason == "criterion_unavailable"


def test_replay_numeric_nan_inf_strings_parsed():
    trace = {
        "events": [
            {
                "type": "gate_evaluation_begin",
                "data": {"gate": "gate@1.0.0"},
            },
            {
                "type": "gate_facts",
                "data": {
                    "p_nan": {
                        "value": "nan",
                        "read_offset_ms": 10,
                        "eval_offset_ms": 20,
                        "age_ms": 10,
                    },
                    "p_inf": {
                        "value": "inf",
                        "read_offset_ms": 10,
                        "eval_offset_ms": 20,
                        "age_ms": 10,
                    },
                    "p_ninf": {
                        "value": "-inf",
                        "read_offset_ms": 10,
                        "eval_offset_ms": 20,
                        "age_ms": 10,
                    },
                    "p_plain": {"value": "nan"},  # non-numeric / missing age: stays string
                },
            },
            {
                "type": "gate_evaluation_result",
                "data": {"verdict": "BLOCK"},
            },
        ]
    }
    steps = recorded_steps(trace)
    assert len(steps) == 1
    facts = steps[0].facts
    assert math.isnan(facts["p_nan"].value)
    assert facts["p_inf"].value == float("inf")
    assert facts["p_ninf"].value == float("-inf")
    assert facts["p_plain"].value == "nan"  # not parsed to float without age_ms


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
    assert not fact_age_mismatches(events.to_trace()["events"])
    tree = compile_tree(make_numeric_gate())
    from neuroedge.engine.decision_tree import walk

    replayed = walk(tree, step.facts)
    assert replayed.verdict is live.verdict
    assert replayed.reason is live.reason
