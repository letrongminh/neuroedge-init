"""
TSK-S5-08 — audio on `linux` against real kernel GPIO lines (gpio-sim).

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh`:

    cd python && python -m pytest -q tests_linux

The file backend touches no device (a WAV is the microphone), so what needs the
kernel here is the session around it: the lines are the virtual chip's, and the
test reads them back through sysfs, independently of the process driving them.
The macOS stand-ins for the live `sounddevice` backend are in
`tests/test_hal_linux_audio.py`; a real microphone and speaker need the Pi
(nightly, TSK-S4-05), so they are not tested here.
"""

from __future__ import annotations

import asyncio
import os
import wave
from pathlib import Path

import pytest

from neuroedge.engine.trace_sink import EventLog
from neuroedge.hal.audio import EnergyVAD
from neuroedge.hal.linux import LinuxHAL
from neuroedge.paths import fixtures_dir
from neuroedge.perception import VirtualClock, VoiceParams, VoiceSession
from neuroedge.perception.providers import FakeSpeechToText, FakeTextToSpeech
from neuroedge.perception.providers.fake import tone
from neuroedge.sim import SimSession

RATE = 16000
WAV_RATE = 48000
PINS = ["door_lock", "porch_light", "gate_relay"]


@pytest.fixture(scope="module")
def sysfs() -> Path:
    path = os.environ.get("NEUROEDGE_GPIO_SIM_SYSFS")
    assert path, "run scripts/setup_gpio_sim.sh first; it exports NEUROEDGE_GPIO_SIM_SYSFS"
    return Path(path)


@pytest.fixture
def hal():
    hal = LinuxHAL(
        events=EventLog(target="linux", board_id="linux-rpi5"), authorize=lambda *_: None
    )
    yield hal
    hal.close()


def kernel_value(sysfs: Path, pin: str) -> int:
    return int((sysfs / f"sim_gpio{PINS.index(pin)}" / "value").read_text().strip())


def wait_for(sysfs: Path, pin: str, value: int, timeout: float = 2.0) -> bool:
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if kernel_value(sysfs, pin) == value:
            return True
        time.sleep(0.01)
    return False


def write_wav(path: Path, pcm: bytes, rate: int = RATE) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return path


def test_the_file_backend_converts_to_the_board_rate_on_the_real_hal(hal, tmp_path):
    path = write_wav(
        tmp_path / "turn.wav", bytes(2 * RATE // 2) + tone(400, RATE) + bytes(2 * RATE // 2)
    )
    source = hal.audio_file(path, called_from="test_linux")
    assert source.sample_rate_hz == WAV_RATE
    frames = list(source.frames())
    assert frames and {f.duration_ms for f in frames} == {20}
    assert all(f.sample_rate_hz == WAV_RATE for f in frames)
    vad = EnergyVAD()
    assert [edge[0] for f in frames if (edge := vad.push(f)) is not None] == ["start", "end"]
    written = hal.speaker(called_from="test_linux")
    written.play(tone(100, WAV_RATE), 0)
    out = written.write(tmp_path / "reply.wav")
    with wave.open(str(out)) as w:
        assert (w.getframerate(), w.getnchannels()) == (WAV_RATE, 1)


def test_a_wav_session_on_linux_drives_the_kernel_line_through_the_gate(sysfs, tmp_path):
    driveway = fixtures_dir() / "agents" / "driveway" / "agent.toml"
    clock = VirtualClock()
    session = SimSession.load(driveway, target="linux", clock=clock)
    try:
        voice = VoiceSession(
            session,
            clock=clock,
            params=VoiceParams(vad_activation=True),
            stt=FakeSpeechToText(["bật đèn hiên"], latency_ms=100),
            tts=FakeTextToSpeech(ms_per_char=20),
        )
        source = session.hal.audio_file(
            write_wav(tmp_path / "turn.wav", tone(600, RATE)), called_from="test_linux"
        )
        asyncio.run(voice.play(source))
        assert [t.heard for t in voice.turns] == ["bật đèn hiên"]
        verdicts = session.events.of_type("gate_evaluation_result")
        assert verdicts and verdicts[-1]["verdict"] == "ALLOW"
        assert kernel_value(sysfs, "porch_light") == 1, "the ALLOW reached the kernel line"
    finally:
        session.close()
    assert kernel_value(sysfs, "porch_light") == 0, "the session drops the line on close"
