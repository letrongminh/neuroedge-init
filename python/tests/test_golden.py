"""
TSK-S3-04 — golden reference comparison (FR-CI-04, FR-CI-LVL L1).

Only decisions are compared: gate verdicts with their decision fields, and pin
commands. Timing, session ids and System 2 text are noise.
"""

from __future__ import annotations

import copy
import json

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.errors import SafetyRegressionError
from neuroedge.testing import (
    GoldenComparator,
    assert_matches_golden,
    replay,
    safety_view,
)

runner = CliRunner()


def canonical(traces_dir, name):
    return json.loads((traces_dir / f"{name}.json").read_text(encoding="utf-8"))


def _results(trace):
    return [e["data"] for e in trace["events"] if e["type"] == "gate_evaluation_result"]


def _commands(trace):
    return [e["data"] for e in trace["events"] if e["type"] == "actuator_command"]


# --- matching ------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["happy-path", "unverified_attempt", "network_offline"])
def test_each_canonical_trace_replays_to_its_own_golden(traces_dir, name):
    result = replay(traces_dir / f"{name}.json")
    assert_matches_golden(result, traces_dir / f"{name}.json")


def test_a_trace_matches_itself(traces_dir):
    trace = canonical(traces_dir, "happy-path")
    assert GoldenComparator().compare(trace, trace).ok


def test_noise_is_ignored(traces_dir):
    golden = canonical(traces_dir, "happy-path")
    actual = copy.deepcopy(golden)
    actual["metadata"]["session_id"] = "sess_ffffffff"
    actual["metadata"]["timestamp_utc"] = "2030-01-01T00:00:00Z"
    for event in actual["events"]:
        event["offset_ms"] += 1234
        if event["type"] == "tts_stream_start":
            event["data"]["text"] = "Something else entirely."  # L3: never compared
        if event["type"] == "intent_extracted":
            event["data"]["confidence"] = 0.51
    assert GoldenComparator().compare(actual, golden).ok


def test_a_decision_field_the_golden_lacks_is_not_compared(traces_dir):
    # The canonical unverified trace predates `reason`; the live engine adds it.
    golden = canonical(traces_dir, "unverified_attempt")
    assert "reason" not in _results(golden)[0]
    result = replay(golden)
    assert _results(result.replayed)[0]["reason"] == "condition_not_met"
    assert GoldenComparator().compare(result, golden).ok


# --- regressions ---------------------------------------------------------------------


def test_allow_turned_block_is_a_regression(traces_dir):
    golden = canonical(traces_dir, "happy-path")
    actual = copy.deepcopy(golden)
    _results(actual)[0]["verdict"] = "BLOCK"
    with pytest.raises(SafetyRegressionError) as raised:
        assert_matches_golden(actual, golden)
    assert "gate evaluation #1 (unlock_door@1.2.0).verdict" in raised.value.where
    assert "golden 'ALLOW', actual 'BLOCK'" in raised.value.why


def test_block_turned_allow_is_labelled_a_safety_regression(traces_dir):
    golden = canonical(traces_dir, "unverified_attempt")
    actual = copy.deepcopy(golden)
    _results(actual)[0]["verdict"] = "ALLOW"
    diff = GoldenComparator().compare(actual, golden)
    assert diff.unsafe
    assert str(diff.differences[0]).startswith("SAFETY REGRESSION")


def test_a_different_pin_is_a_safety_regression(traces_dir):
    golden = canonical(traces_dir, "happy-path")
    actual = copy.deepcopy(golden)
    _commands(actual)[0]["pin"] = "porch_light"
    with pytest.raises(SafetyRegressionError, match="actuator command #1"):
        assert_matches_golden(actual, golden)
    assert GoldenComparator().compare(actual, golden).unsafe


def test_a_different_pulse_duration_is_a_regression(traces_dir):
    golden = canonical(traces_dir, "happy-path")
    actual = copy.deepcopy(golden)
    _commands(actual)[0]["duration_ms"] = 60000
    with pytest.raises(SafetyRegressionError, match="duration_ms"):
        assert_matches_golden(actual, golden)


def test_an_extra_pin_command_is_a_safety_regression(traces_dir):
    golden = canonical(traces_dir, "unverified_attempt")
    actual = copy.deepcopy(golden)
    actual["events"].append(
        {
            "offset_ms": 700,
            "type": "actuator_command",
            "data": {"pin": "door_lock", "operation": "pulse", "duration_ms": 30000},
        }
    )
    diff = GoldenComparator().compare(actual, golden)
    assert diff.unsafe
    assert diff.differences[0].golden is None


def test_a_changed_escalation_recipient_is_a_regression(traces_dir):
    golden = canonical(traces_dir, "unverified_attempt")
    actual = copy.deepcopy(golden)
    _results(actual)[0]["escalated_to"] = "night_duty_manager"
    with pytest.raises(SafetyRegressionError, match="escalated_to"):
        assert_matches_golden(actual, golden)


def test_a_missing_evaluation_is_a_regression(traces_dir):
    golden = canonical(traces_dir, "happy-path")
    actual = copy.deepcopy(golden)
    actual["events"] = [e for e in actual["events"] if not e["type"].startswith("gate_")]
    diff = GoldenComparator().compare(actual, golden)
    assert not diff.ok
    assert diff.report  # the DeepDiff report of the two safety views


def test_the_replay_of_a_changed_fact_fails_against_the_original_golden(traces_dir):
    trace = canonical(traces_dir, "happy-path")
    for result in _results(trace):
        result["evaluations"]["guest_authenticated"] = False
    with pytest.raises(SafetyRegressionError, match="verdict"):
        assert_matches_golden(replay(trace), traces_dir / "happy-path.json")


def test_safety_view_is_just_the_decisions(traces_dir):
    assert safety_view(canonical(traces_dir, "happy-path")) == {
        "gates": [{"gate": "unlock_door@1.2.0", "verdict": "ALLOW"}],
        "actuators": [{"pin": "door_lock", "operation": "pulse", "duration_ms": 30000}],
    }


def test_a_regression_is_also_an_assertion_error(traces_dir):
    golden = canonical(traces_dir, "happy-path")
    actual = copy.deepcopy(golden)
    _results(actual)[0]["verdict"] = "BLOCK"
    with pytest.raises(AssertionError):
        assert_matches_golden(actual, golden)


# --- CLI -----------------------------------------------------------------------------


def test_replay_against_a_different_golden_exits_one(traces_dir):
    result = runner.invoke(
        app,
        [
            "replay",
            str(traces_dir / "happy-path.json"),
            "--golden",
            str(traces_dir / "unverified_attempt.json"),
        ],
    )
    assert result.exit_code == 1
    assert "NE4002" in result.output
    assert "verdict" in result.output


def test_replay_writes_the_replayed_trace(traces_dir, tmp_path):
    out = tmp_path / "replayed.json"
    result = runner.invoke(
        app, ["replay", str(traces_dir / "happy-path.json"), "--trace-out", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert _commands(json.loads(out.read_text("utf-8"))) == [
        {"pin": "door_lock", "operation": "pulse", "duration_ms": 30000}
    ]
