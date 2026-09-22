"""
Trace schema conformance, valid and invalid — the trace half of exit criterion 1.

The three canonical traces are the compliance yardstick for Khối 1a and 1b
(§3.8) and the direct input to `neuroedge verify`, so they are asserted on
scenario content, not merely on schema validity.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from neuroedge.errors import TraceValidationError
from neuroedge.trace import TRACE_SCHEMA_ID, load_trace, validate_trace

CANONICAL_TRACES = ["happy-path.json", "unverified_attempt.json", "network_offline.json"]

_INVALID_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "traces" / "invalid"
INVALID = sorted(_INVALID_DIR.glob("*.json"))


# --- The three canonical traces ------------------------------------------


@pytest.mark.parametrize("name", CANONICAL_TRACES)
def test_canonical_trace_validates(traces_dir, name):
    trace = load_trace(traces_dir / name)
    assert trace["$schema"] == TRACE_SCHEMA_ID
    assert trace["events"], "a trace with no events replays nothing"


def test_exactly_the_three_canonical_traces_are_present(traces_dir):
    found = sorted(p.name for p in traces_dir.glob("*.json"))
    assert found == sorted(CANONICAL_TRACES)


def test_happy_path_pulses_the_lock_for_thirty_seconds(traces_dir):
    trace = load_trace(traces_dir / "happy-path.json")
    verdicts = [e for e in trace["events"] if e["type"] == "gate_evaluation_result"]
    commands = [e for e in trace["events"] if e["type"] == "actuator_command"]
    assert [v["data"]["verdict"] for v in verdicts] == ["ALLOW"]
    assert len(commands) == 1
    assert commands[0]["data"] == {
        "pin": "door_lock",
        "operation": "pulse",
        "duration_ms": 30000,
    }


def test_unverified_attempt_never_touches_the_lock(traces_dir):
    trace = load_trace(traces_dir / "unverified_attempt.json")
    verdicts = [e for e in trace["events"] if e["type"] == "gate_evaluation_result"]
    assert [v["data"]["verdict"] for v in verdicts] == ["BLOCK"]
    assert not [e for e in trace["events"] if e["type"] == "actuator_command"], (
        "a blocked action must leave no actuator command in the trace"
    )


def test_network_offline_fails_closed_with_the_documented_reason(traces_dir):
    trace = load_trace(traces_dir / "network_offline.json")
    verdicts = [e for e in trace["events"] if e["type"] == "gate_evaluation_result"]
    assert [v["data"]["verdict"] for v in verdicts] == ["BLOCK"]
    assert any(v["data"].get("reason") == "gate_unreachable" for v in verdicts)
    assert not [e for e in trace["events"] if e["type"] == "actuator_command"]


def test_event_offsets_are_monotonic(traces_dir):
    """Replay depends on ordering; an out-of-order trace is not replayable."""
    for name in CANONICAL_TRACES:
        offsets = [e["offset_ms"] for e in load_trace(traces_dir / name)["events"]]
        assert offsets == sorted(offsets), f"{name} has out-of-order events"


# --- The counter-examples -------------------------------------------------


def test_every_invalid_trace_has_a_recorded_expectation(expected_trace_errors):
    documented = set(expected_trace_errors)
    present = {p.name for p in INVALID}
    assert present - documented == set(), (
        f"fixtures without a recorded expected error: {sorted(present - documented)}"
    )
    assert documented - present == set(), (
        f"expectations with no fixture: {sorted(documented - present)}"
    )


@pytest.mark.parametrize("path", INVALID, ids=[p.name for p in INVALID])
def test_invalid_trace_fails_as_recorded(path, expected_trace_errors):
    expectation = expected_trace_errors[path.name]
    with pytest.raises(TraceValidationError) as excinfo:
        load_trace(path)
    error = excinfo.value
    assert error.code == "NE4001"
    assert expectation["where_contains"] in error.where
    assert expectation["why_contains"] in error.why
    assert error.how.strip(), "FR-DX-04 requires a remediation hint"


def test_non_object_trace_is_rejected(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(TraceValidationError) as excinfo:
        load_trace(path)
    assert "must be a JSON object" in excinfo.value.why


def test_malformed_json_reports_a_position(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text('{"metadata": ', encoding="utf-8")
    with pytest.raises(TraceValidationError) as excinfo:
        load_trace(path)
    assert "line" in excinfo.value.where and "column" in excinfo.value.where


def test_missing_file_is_reported_clearly(tmp_path):
    with pytest.raises(TraceValidationError) as excinfo:
        load_trace(tmp_path / "absent.json")
    assert "does not exist" in excinfo.value.why


def test_validate_trace_accepts_a_minimal_trace():
    validate_trace(
        {
            "$schema": TRACE_SCHEMA_ID,
            "metadata": {
                "session_id": "sess_0",
                "timestamp_utc": "2026-09-21T08:00:00Z",
                "target": "sim",
                "board_id": "sim-default",
                "agent_version": "test@0.0.1",
            },
            "events": [],
        }
    )
