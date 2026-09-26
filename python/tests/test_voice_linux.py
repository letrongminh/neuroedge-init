"""
TSK-S5-08 — `--voice-file` on `linux`: the WAV is `audio.in` through `LinuxHAL`'s
file backend (converted to the board's 48 kHz), the pins are the fake gpiod lines
of `test_hal_linux.py`, and `--voice-out` is the board-rate timeline. Nothing here
opens a microphone or a `sounddevice` device.
"""

from __future__ import annotations

import shutil
import wave

import pytest
from typer.testing import CliRunner

import neuroedge.hal.linux as linux
from neuroedge.cli.main import app
from neuroedge.errors import BoardCapabilityError, BuildFailed
from neuroedge.perception.providers.fake import tone
from neuroedge.sim import SimSession
from neuroedge.testing import assert_matches_golden, replay
from neuroedge.trace import load_trace, validate_trace

from .test_hal_linux import LINES, FakeGpiod
from .test_hal_linux_audio import FakeSounddevice

runner = CliRunner()
RATE = 16000  # the WAV is a 16 kHz mono recording, as `--voice-file` documents

AGENT = """\
[agent]
name    = "voice-driveway"
version = "0.1.0"

[requires]
"audio.in"    = { sample_rate_hz = 16000 }
"audio.out"   = {}
"digital.out" = { pins = ["door_lock", "gate_relay", "porch_light"] }

[gates]
buzz_in        = "gates/buzz_in@1.0.0.yaml"
open_gate      = "gates/open_gate@1.0.0.yaml"
porch_light_on = "gates/porch_light_on@1.0.0.yaml"

[targets]
supported = ["sim", "linux"]

[sim.facts]
visitor_expected = true
light_allowed    = true

[stt]
provider = "python:neuroedge.perception.providers.fake:stt"
[stt.options]
transcripts = ["bật đèn hiên"]
latency_ms  = 300

[tts]
provider = "python:neuroedge.perception.providers.fake:tts"
[tts.options]
ms_per_char = 40
"""


def write_wav(path, pcm, rate=RATE):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return path


@pytest.fixture
def gpio(monkeypatch, tmp_path):
    """Virtual lines named after the board pins, where `LinuxHAL` looks for them."""
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    fake = FakeGpiod({str(chip): LINES})
    monkeypatch.setattr(linux, "CHIP_GLOB", str(tmp_path / "gpiochip*"))
    monkeypatch.setattr(linux, "_import_gpiod", lambda: fake)
    return fake


@pytest.fixture
def fresh_actions():
    """A copied agent registers its @actions again: free the names between tests."""
    from neuroedge.actions import spec

    saved = dict(spec.REGISTRY)
    spec.REGISTRY.clear()
    yield
    spec.REGISTRY.clear()
    spec.REGISTRY.update(saved)


@pytest.fixture
def project(root, tmp_path, fresh_actions):
    """`driveway` with audio declared and the keyless fake providers, plus a WAV."""
    folder = tmp_path / "voice-driveway"
    shutil.copytree(root / "fixtures" / "agents" / "driveway", folder)
    (folder / "agent.toml").write_text(AGENT, encoding="utf-8")
    wav = write_wav(
        tmp_path / "turn.wav", bytes(2 * RATE // 2) + tone(900, RATE) + bytes(2 * RATE * 3)
    )
    return folder / "agent.toml", wav


def invoke(*args):
    return runner.invoke(app, [str(a) for a in args])


def test_a_voice_file_runs_on_linux_through_the_file_backend(project, gpio, tmp_path):
    agent, wav = project
    out = tmp_path / "reply.wav"
    result = invoke(
        "run", "--target", "linux", "--agent", agent, "--voice-file", wav, "--voice-out", out
    )
    assert result.exit_code == 0, result.output
    assert "on linux (linux-rpi5)" in result.output
    assert "heard: “bật đèn hiên”" in result.output and "ALLOW" in result.output
    assert "1 turns" in result.output and "0 STT unavailable" in result.output
    with wave.open(str(out)) as w:
        assert (w.getframerate(), w.getnchannels()) == (48000, 1), "the board's rate"
    assert ("porch_light", 1) in gpio.history and all(
        value == 0 for _, value in gpio.history[1:]
    ), "the line is dropped at the end"


def test_record_on_linux_replays_to_the_same_decisions_on_sim(project, gpio, tmp_path):
    agent, wav = project
    out = tmp_path / "linux-voice.json"
    result = invoke(
        "record", "--target", "linux", "--agent", agent, "--voice-file", wav, "--out", out
    )
    assert result.exit_code == 0, result.output
    trace = load_trace(out)  # validates against trace.v1
    validate_trace(trace)
    assert trace["metadata"]["target"] == "linux"
    assert trace["metadata"]["board_id"] == "linux-rpi5"
    (segment,) = [e for e in trace["events"] if e["type"] == "audio_in_segment"]
    assert segment["data"]["sample_rate_hz"] == 48000, "converted on the way in"

    on_sim = replay(out, target="sim", agent=agent)
    on_linux = replay(out, target="linux", agent=agent)
    assert on_sim.verdicts == on_linux.verdicts == on_sim.recorded_verdicts
    assert on_sim.pin("porch_light").commands == on_linux.pin("porch_light").commands
    assert_matches_golden(on_sim, out)


def test_a_voice_file_session_never_opens_the_live_devices(project, gpio, monkeypatch):
    # `--voice-file` is the file backend even when the machine's environment says
    # live: no microphone, no speaker, no sounddevice import (TSK-S5-08, TODOS #45).
    monkeypatch.setenv(linux.AUDIO_ENV, "live")
    monkeypatch.setattr(
        linux,
        "_import_sounddevice",
        lambda: pytest.fail("a --voice-file session must not open sounddevice"),
    )
    agent, wav = project
    result = invoke("run", "--target", "linux", "--agent", agent, "--voice-file", wav)
    assert result.exit_code == 0, result.output
    assert "ALLOW" in result.output


def test_a_live_session_refuses_a_missing_device_before_any_line(project, gpio, monkeypatch):
    monkeypatch.setenv(linux.AUDIO_ENV, "live")
    monkeypatch.setattr(linux, "_import_sounddevice", lambda: FakeSounddevice(devices=set()))
    agent, _ = project
    with pytest.raises(BoardCapabilityError, match="no input device named"):
        SimSession.load(agent, target="linux")
    assert gpio.requests == [], "no GPIO line is requested for a device that cannot open"


def test_a_live_session_opens_both_devices_then_requests_the_lines(project, gpio, monkeypatch):
    fake = FakeSounddevice()
    monkeypatch.setenv(linux.AUDIO_ENV, "live")
    monkeypatch.setattr(linux, "_import_sounddevice", lambda: fake)
    agent, _ = project
    session = SimSession.load(agent, target="linux")
    try:
        assert fake.inputs and fake.outputs, "both live devices were preflighted"
        assert gpio.requests, "the lines were requested after the devices opened"
    finally:
        session.close()
    assert fake.inputs[0].closed and fake.outputs[0].closed


def test_the_build_check_still_refuses_what_linux_has_not(root, gpio):
    villa = root / "fixtures" / "agents" / "villa-concierge" / "agent.toml"
    result = invoke("run", "--target", "linux", "--agent", villa, "--voice-file", "x.wav")
    assert result.exit_code == 1
    assert "aec" in result.output and "build failed" in result.output
    assert gpio.requests == [], "no line is requested for an agent that does not build"
    with pytest.raises(BuildFailed):
        SimSession.load(villa, target="linux")


def test_ui_still_exits_two_on_linux(project, gpio):
    agent, wav = project
    result = invoke("run", "--target", "linux", "--agent", agent, "--voice-file", wav, "--ui")
    assert result.exit_code == 2, result.output
    assert "does not play or record audio" in result.output
