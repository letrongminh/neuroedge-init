"""
TSK-S3-13 — `neuroedge run --voice-file` / `record --voice-file`: speech on `sim`
through the agent's `[stt]` / `[tts]`, here the keyless fakes
(`perception.providers.fake`), so nothing leaves the machine.
"""

from __future__ import annotations

import json
import shutil
import wave

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.perception.providers.fake import tone
from neuroedge.trace import load_trace

runner = CliRunner()
RATE = 16000

FAKES = """
[stt]
provider = "python:neuroedge.perception.providers.fake:stt"
[stt.options]
transcripts = ["mở cửa"]
latency_ms  = 300

[tts]
provider = "python:neuroedge.perception.providers.fake:tts"
[tts.options]
ms_per_char = 40
"""


@pytest.fixture
def fresh_actions():
    from neuroedge.actions import spec

    saved = dict(spec.REGISTRY)
    spec.REGISTRY.clear()
    yield
    spec.REGISTRY.clear()
    spec.REGISTRY.update(saved)


@pytest.fixture
def project(root, tmp_path, fresh_actions):
    """voice-door with `extra` appended to agent.toml, and a one-command WAV file."""
    folder = tmp_path / "voice-door"
    shutil.copytree(root / "fixtures" / "agents" / "voice-door", folder)
    agent = folder / "agent.toml"
    base = agent.read_text(encoding="utf-8")
    wav = tmp_path / "turn.wav"
    write_wav(wav, bytes(2 * RATE // 2) + tone(900, RATE) + bytes(2 * RATE * 3))

    def make(extra: str = FAKES):
        agent.write_text(base + extra, encoding="utf-8")
        return agent, wav

    return make


def write_wav(path, pcm, rate=RATE):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


def invoke(*args):
    return runner.invoke(app, [str(a) for a in args])


def test_a_voice_file_runs_the_command_through_the_gate(project, tmp_path):
    agent, wav = project()
    trace, out = tmp_path / "t.json", tmp_path / "reply.wav"
    result = invoke(
        "run", "--agent", agent, "--voice-file", wav, "--voice-out", out, "--trace-out", trace
    )
    assert result.exit_code == 0, result.output
    assert "turn 1 · 2.6 s · heard: “mở cửa”" in result.output
    assert "ALLOW" in result.output and "PULSED 30s" in result.output
    assert "stt: adapter neuroedge.perception.providers.fake:stt" in result.output
    assert "1 turns" in result.output and "0 STT unavailable" in result.output
    events = load_trace(trace)["events"]  # validates against trace.v1
    kinds = [e["type"] for e in events]
    assert kinds.index("stt_result") < kinds.index("gate_evaluation_result")
    assert "actuator_command" in kinds
    with wave.open(str(out)) as w:
        assert (w.getframerate(), w.getnchannels()) == (RATE, 1)


def test_record_anonymises_a_voice_session(project, tmp_path):
    agent, wav = project()
    out = tmp_path / "traces" / "voice.json"
    result = invoke("record", "--agent", agent, "--voice-file", wav, "--out", out, "--anonymize")
    assert result.exit_code == 0, result.output
    trace = load_trace(out)
    assert trace["metadata"]["anonymized"] is True
    assert "mở cửa" not in json.dumps(trace["events"], ensure_ascii=False)
    (heard,) = [e for e in trace["events"] if e["type"] == "stt_result"]
    assert heard["data"]["text"].startswith("sha256:") and heard["offset_ms"] == 2600


def test_record_writes_into_a_traces_directory(project, tmp_path):
    agent, wav = project()
    result = invoke("record", "--agent", agent, "--voice-file", wav, "--out", tmp_path / "traces")
    assert result.exit_code == 0, result.output
    (written,) = (tmp_path / "traces").glob("sess_*.json")
    assert load_trace(written)["events"]


def test_no_stt_table_keeps_typed_input_and_says_so(project):
    agent, wav = project("")
    result = invoke("run", "--agent", agent, "--voice-file", wav)
    assert result.exit_code == 1
    assert "NE3002" in result.output and "[stt]" in result.output and "Q-15" in result.output
    # …and typed input is exactly as before, keyless.
    typed = invoke("run", "--agent", agent, "-c", "mở cửa")
    assert typed.exit_code == 0 and "ALLOW" in typed.output


def test_voice_out_needs_a_tts_table(project):
    agent, wav = project(FAKES.split("[tts]")[0])
    result = invoke("run", "--agent", agent, "--voice-file", wav, "--voice-out", "x.wav")
    assert result.exit_code == 1 and "[tts]" in result.output


def test_without_tts_replies_are_shown_not_heard(project):
    agent, wav = project(FAKES.split("[tts]")[0])
    result = invoke("run", "--agent", agent, "--voice-file", wav)
    assert result.exit_code == 0, result.output
    assert "tts: none — replies are shown, not heard" in result.output


@pytest.mark.parametrize(
    "args, fragment",
    [
        (["--voice-out", "x.wav"], "none is given"),
        (["-c", "mở cửa"], "one session, one input"),
    ],
)
def test_flags_voice_cannot_combine_with_exit_one(project, args, fragment):
    agent, wav = project()
    extra = [] if "--voice-out" in args else ["--voice-file", wav]
    result = invoke("run", "--agent", agent, *extra, *args)
    assert result.exit_code == 1 and fragment in result.output


@pytest.mark.parametrize(
    "args, fragment",
    [
        (["--ui"], "--ui"),
        (["--target", "linux"], "TSK-S5-08"),
        (["--target", "esp32s3"], "TSK-S4-01"),
    ],
)
def test_voice_where_it_is_not_implemented_exits_two(project, args, fragment):
    agent, wav = project()
    result = invoke("run", "--agent", agent, "--voice-file", wav, *args)
    assert result.exit_code == 2, result.output
    assert "Not implemented" in result.output and fragment in result.output


def test_a_file_the_board_does_not_take_exits_one(project, tmp_path):
    agent, _ = project()
    wide = tmp_path / "cd.wav"
    write_wav(wide, bytes(4410 * 2), rate=44100)
    result = invoke("run", "--agent", agent, "--voice-file", wide)
    assert result.exit_code == 1 and "NE3001" in result.output and "ffmpeg" in result.output


def test_record_from_a_device_takes_no_voice_file(project):
    agent, wav = project()
    result = invoke("record", "--target", "esp32s3", "--port", "uart.log", "--voice-file", wav)
    assert result.exit_code == 1 and "firmware" in result.output


def test_a_failing_stt_still_exits_zero_with_the_offline_line(project):
    agent, wav = project(FAKES.replace("latency_ms  = 300", "latency_ms  = 300\nfail = true"))
    result = invoke("run", "--agent", agent, "--voice-file", wav)
    assert result.exit_code == 0, result.output
    assert "STT unavailable" in result.output and "no action" in result.output
    assert "1 STT unavailable" in result.output and "ALLOW" not in result.output


def test_a_silent_file_hears_no_turn(project, tmp_path):
    agent, _ = project()
    quiet = tmp_path / "quiet.wav"
    write_wav(quiet, bytes(2 * RATE))
    result = invoke("run", "--agent", agent, "--voice-file", quiet)
    assert result.exit_code == 0 and "no turn was heard" in result.output


def test_a_real_provider_without_its_key_sends_nothing(project, monkeypatch):
    # FR-DX-02: the default provider with the variable unset — no request is made, the
    # device says the offline line, and the run is not a crash.
    monkeypatch.delenv("NEUROEDGE_NO_SUCH_KEY", raising=False)
    agent, wav = project('\n[stt]\nmodel = "whisper-1"\napi_key_env = "NEUROEDGE_NO_SUCH_KEY"\n')
    result = invoke("run", "--agent", agent, "--voice-file", wav)
    assert result.exit_code == 0, result.output
    assert "NEUROEDGE_NO_SUCH_KEY is not set (nothing was sent)" in result.output
