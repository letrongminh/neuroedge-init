"""
TSK-S3-01 — recording a session to a `trace.v1` file (FR-CI-01, FR-TRC-07).

A recorded trace must validate, and must carry what a replay needs: which
action asked for which gate, and the facts the verdict read.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.errors import TraceValidationError
from neuroedge.sim import SimSession
from neuroedge.testing.recorder import TraceRecorder, digest_text
from neuroedge.trace import load_trace

runner = CliRunner()


@pytest.fixture(scope="module")
def villa(root):
    return root / "fixtures" / "agents" / "villa-concierge" / "agent.toml"


async def _record(villa, *lines, anonymize=False, **facts):
    recorder = TraceRecorder(anonymize=anonymize)
    session = SimSession.load(villa, events=recorder, facts=facts)
    for line in lines:
        await session.handle(line)
    return recorder


async def test_a_recorded_unlock_validates_and_carries_the_replay_inputs(villa, tmp_path):
    recorder = await _record(villa, "mở cửa phòng 101")
    trace = recorder.save(tmp_path / "unlock.json")

    assert load_trace(tmp_path / "unlock.json") == trace  # validates against trace.v1
    metadata = trace["metadata"]
    assert metadata["session_id"].startswith("sess_")
    assert (metadata["target"], metadata["board_id"]) == ("sim", "sim-default")
    assert metadata["agent_version"] == "villa-concierge@0.1.0"

    types = [event["type"] for event in trace["events"]]
    assert types == [
        "text_input",
        "intent_extracted",
        "tool_call",
        "action_requested",
        "gate_evaluation_begin",
        "gate_facts",
        "gate_evaluation_result",
        "actuator_command",
        "turn_latency",  # TSK-I4-03
        "session_summary",
    ]
    by_type = {event["type"]: event["data"] for event in trace["events"]}
    assert by_type["action_requested"] == {
        "action": "unlock_door",
        "gate": "unlock_door",
        "arguments": {"guest_id": "101"},
    }
    assert by_type["gate_facts"]["guest_authenticated"] == {
        "value": True,
        "confidence": None,
        "source": "context",
    }
    assert by_type["actuator_command"] == {
        "pin": "door_lock",
        "operation": "pulse",
        "duration_ms": 30000,
    }


async def test_anonymize_hashes_raw_text_and_keeps_every_decision(villa, tmp_path):
    plain = (await _record(villa, "mở cửa phòng 101")).to_trace()
    hidden = (await _record(villa, "mở cửa phòng 101", anonymize=True)).save(tmp_path / "a.json")

    text = json.dumps(hidden, ensure_ascii=False)
    assert "mở cửa" not in text
    assert hidden["metadata"]["anonymized"] is True
    (text_input,) = [e["data"] for e in hidden["events"] if e["type"] == "text_input"]
    assert text_input == {"text": digest_text("mở cửa phòng 101")}
    assert text_input["text"].startswith("sha256:")

    # Timing (TSK-I4-03) is measured, not decided: two runs differ in it, never in path.
    timing = {"text_input", "turn_latency", "session_summary"}

    def decisions(trace):
        return [(e["type"], e["data"]) for e in trace["events"] if e["type"] not in timing]

    def paths(trace):
        return [e["data"]["path"] for e in trace["events"] if e["type"] == "turn_latency"]

    assert decisions(hidden) == decisions(plain)
    assert paths(hidden) == paths(plain) == ["system_1"]


async def test_unrecognised_text_is_hashed_too(villa):
    recorder = await _record(villa, "hát một bài", anonymize=True)
    (event,) = recorder.of_type("command_not_recognized")
    assert event["text"] == digest_text("hát một bài")


def test_the_digest_is_stable_across_unicode_forms():
    composed = "mở"
    decomposed = "mở"
    assert composed != decomposed
    assert digest_text(composed) == digest_text(decomposed)


def test_a_trace_that_fails_the_schema_is_never_written(tmp_path):
    recorder = TraceRecorder(target="sim")
    recorder.metadata["target"] = "mars"
    with pytest.raises(TraceValidationError):
        recorder.save(tmp_path / "bad.json")
    assert not (tmp_path / "bad.json").exists()


def test_a_directory_path_is_named_after_the_session(tmp_path):
    recorder = TraceRecorder()
    recorder.emit("text_input", {"text": "x"})
    recorder.save(tmp_path)
    assert (tmp_path / f"{recorder.session_id}.json").is_file()


def test_the_context_manager_saves_even_when_the_session_raises(tmp_path):
    out = tmp_path / "crash.json"
    with pytest.raises(RuntimeError), TraceRecorder(path=out) as recorder:
        recorder.emit("text_input", {"text": "x"})
        raise RuntimeError("boom")
    assert load_trace(out)["events"][0]["type"] == "text_input"


# --- CLI ----------------------------------------------------------------------------


def test_record_writes_a_valid_trace_into_the_out_directory(villa, tmp_path):
    result = runner.invoke(
        app,
        ["record", "--agent", str(villa), "--out", str(tmp_path), "-c", "mở cửa phòng 101"],
    )
    assert result.exit_code == 0, result.output
    (path,) = tmp_path.glob("sess_*.json")
    trace = load_trace(path)
    assert any(e["type"] == "actuator_command" for e in trace["events"])


def test_record_anonymize_flag_reaches_the_file(villa, tmp_path):
    out = tmp_path / "anon.json"
    result = runner.invoke(
        app,
        [
            "record",
            "--agent",
            str(villa),
            "--out",
            str(out),
            "--anonymize",
            "-c",
            "mở cửa phòng 101",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "mở cửa" not in out.read_text(encoding="utf-8")


def test_record_on_linux_build_checks_the_agent_against_the_linux_board(villa, tmp_path):
    # villa-concierge needs hardware AEC, which linux-rpi5 does not have: refused before
    # any GPIO line is looked for (the linux session itself: test_session_linux.py).
    result = runner.invoke(app, ["record", "--agent", str(villa), "--target", "linux", "-c", "x"])
    assert result.exit_code == 1
    assert "build failed" in result.output and "aec" in result.output


def test_record_on_an_unknown_target_exits_one(villa):
    result = runner.invoke(app, ["record", "--agent", str(villa), "--target", "stm32", "-c", "x"])
    assert result.exit_code == 1
    assert "NE3001" in result.output
