"""
TSK-I4-04 (slice 2, decision Q-50) — real-time voice session: `neuroedge run --mic [--half-duplex]`.

The session clock stays a `VirtualClock`, driven by the microphone's sample clock
instead of a file (`play_live`). A capture thread reads `source.frames()` into a bounded
queue so PortAudio does not overflow during provider calls. In half-duplex mode, frames
captured while a reply is playing are silenced to prevent echo through loudspeakers.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
import threading
import wave
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.errors import BoardCapabilityError, PerceptionUnavailableError
from neuroedge.hal.audio import AudioFrame, EnergyVAD, Speaker
from neuroedge.hal.sim import SimHAL
from neuroedge.perception import VirtualClock, VoiceParams, VoiceSession
from neuroedge.perception.live import LiveAudioCapture
from neuroedge.perception.providers import FakeSpeechToText, FakeTextToSpeech
from neuroedge.perception.providers.fake import tone
from neuroedge.sim import SimSession
from neuroedge.testing.recorder import TraceRecorder
from neuroedge.trace import load_trace

from .fake_sounddevice import FakeInputStream, FakeSounddevice

RATE = 16000
PARAMS = VoiceParams(vad_activation=True, think_timeout_ms=5000)

FAKES = """
[stt]
provider = "python:neuroedge.perception.providers.fake:stt"
[stt.options]
transcripts = ["mở cửa"]
latency_ms  = 100

[tts]
provider = "python:neuroedge.perception.providers.fake:tts"
[tts.options]
ms_per_char = 30
"""

runner = CliRunner()


def silence(ms: int) -> bytes:
    return bytes(2 * RATE * ms // 1000)


def write_wav(path: Path, pcm: bytes, rate: int = RATE) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return path


class ScriptedLiveSource:
    """A scripted live audio source yielding 20 ms AudioFrames stamped on sample clock."""

    def __init__(self, pcm: bytes, rate: int = RATE, frame_ms: int = 20) -> None:
        self.pcm = pcm
        self.rate = rate
        self.frame_ms = frame_ms
        self.block_bytes = 2 * rate * frame_ms // 1000
        self.closed = False

    def frames(self) -> Iterator[AudioFrame]:
        at_ms = 0
        for offset in range(0, len(self.pcm), self.block_bytes):
            if self.closed:
                break
            chunk = self.pcm[offset : offset + self.block_bytes]
            if len(chunk) < self.block_bytes:
                chunk = chunk + b"\x00" * (self.block_bytes - len(chunk))
            frame = AudioFrame(chunk, at_ms, self.frame_ms, self.rate)
            at_ms += self.frame_ms
            yield frame

    def close(self) -> None:
        self.closed = True


class EndingFakeInputStream(FakeInputStream):
    """Fake input stream that closes the wrapping LiveAudioIn when blocks run out."""

    def read(self, frames: int) -> tuple[bytes, bool]:
        if not self.started:
            raise RuntimeError("Stream is stopped")
        if self.world.blocks:
            return self.world.blocks.pop(0), False
        import inspect

        cur = inspect.currentframe()
        while cur:
            obj = cur.f_locals.get("self")
            if hasattr(obj, "_closed") and hasattr(obj, "close"):
                obj.close()
                break
            cur = cur.f_back
        raise OSError(19, "End of scripted stream")


class EndingFakeSounddevice(FakeSounddevice):
    def RawInputStream(  # noqa: N802
        self, *, samplerate: int, channels: int, dtype: str, device: Any, blocksize: int
    ) -> EndingFakeInputStream:
        stream = EndingFakeInputStream(self, device, channels, samplerate)
        self.inputs.append(stream)
        return stream


class InterruptingFakeInputStream(FakeInputStream):
    def read(self, frames: int) -> tuple[bytes, bool]:
        if not self.started:
            raise RuntimeError("Stream is stopped")
        if self.world.blocks:
            return self.world.blocks.pop(0), False
        raise KeyboardInterrupt


class InterruptingFakeSounddevice(FakeSounddevice):
    def RawInputStream(  # noqa: N802
        self, *, samplerate: int, channels: int, dtype: str, device: Any, blocksize: int
    ) -> InterruptingFakeInputStream:
        stream = InterruptingFakeInputStream(self, device, channels, samplerate)
        self.inputs.append(stream)
        return stream


@pytest.fixture(scope="module")
def door(root: Path) -> Path:
    return root / "fixtures" / "agents" / "voice-door" / "agent.toml"


@pytest.fixture
def fresh_actions():
    from neuroedge.actions import spec

    saved = dict(spec.REGISTRY)
    spec.REGISTRY.clear()
    yield
    spec.REGISTRY.clear()
    spec.REGISTRY.update(saved)


@pytest.fixture
def project(root: Path, tmp_path: Path, fresh_actions: None):
    folder = tmp_path / "voice-door"
    shutil.copytree(root / "fixtures" / "agents" / "voice-door", folder)
    agent = folder / "agent.toml"
    base = agent.read_text(encoding="utf-8")

    def make(extra: str = FAKES) -> Path:
        agent.write_text(base + extra, encoding="utf-8")
        return agent

    return make


def voice_on(
    door: Path,
    *,
    stt: Any,
    tts: Any = None,
    params: VoiceParams = PARAMS,
    system_two: bool = False,
    anonymize: bool | None = None,
    stopwatch: Any = None,
) -> VoiceSession:
    clock = VirtualClock()
    events = None if anonymize is None else TraceRecorder(anonymize=anonymize, clock=clock)
    session = SimSession.load(door, clock=clock, events=events)
    kwargs: dict[str, Any] = {}
    if stopwatch is not None:
        kwargs["stopwatch"] = stopwatch
    return VoiceSession(
        session,
        clock=clock,
        params=params,
        stt=stt,
        tts=tts,
        system_two=system_two,
        **kwargs,
    )


# --- 1. Capture thread unit tests -----------------------------------------------------------------


def test_capture_thread_frames_flow_in_order() -> None:
    first = b"\x01\x00" * 320
    second = b"\x02\x00" * 320
    third = b"\x03\x00" * 320
    sd = FakeSounddevice([first, second, third])
    hal = SimHAL(audio="live", sounddevice=sd)
    source = hal.audio_source()
    capture = LiveAudioCapture(source)
    capture.start()

    async def run():
        loop = asyncio.get_running_loop()
        f1 = await capture.next_frame(loop)
        f2 = await capture.next_frame(loop)
        f3 = await capture.next_frame(loop)
        f4 = await capture.next_frame(loop)
        return f1, f2, f3, f4

    f1, f2, f3, f4 = asyncio.run(run())
    assert f1 is not None and f1.pcm == first and f1.start_ms == 0 and f1.end_ms == 20
    assert f2 is not None and f2.pcm == second and f2.start_ms == 20 and f2.end_ms == 40
    assert f3 is not None and f3.pcm == third and f3.start_ms == 40 and f3.end_ms == 60
    assert f4 is None

    capture.close()
    assert sd.inputs[0].closed
    hal.close()


def test_capture_thread_full_queue_raises_three_part_error() -> None:
    blocks = [b"\x01\x00" * 320] * 10
    sd = FakeSounddevice(blocks)
    hal = SimHAL(audio="live", sounddevice=sd)
    source = hal.audio_source()
    capture = LiveAudioCapture(source, max_frames=3)
    capture.start()

    async def run():
        loop = asyncio.get_running_loop()
        for _ in range(15):
            await capture.next_frame(loop)

    with pytest.raises(PerceptionUnavailableError) as raised:
        asyncio.run(run())

    err = raised.value
    assert "capture queue" in err.where
    assert "filled" in err.why
    assert "providers" in err.how or "load" in err.how
    capture.close()
    hal.close()


def test_capture_thread_exception_surfaces() -> None:
    sd = FakeSounddevice(mode="gone")
    hal = SimHAL(audio="live", sounddevice=sd)
    source = hal.audio_source()
    capture = LiveAudioCapture(source)
    capture.start()

    async def run():
        loop = asyncio.get_running_loop()
        await capture.next_frame(loop)

    with pytest.raises(BoardCapabilityError) as raised:
        asyncio.run(run())

    assert "stopped answering" in raised.value.why
    capture.close()
    hal.close()


def test_capture_thread_stop_ends_loop_and_closes_streams() -> None:
    sd = FakeSounddevice(blocking=True)
    hal = SimHAL(audio="live", sounddevice=sd)
    source = hal.audio_source()
    stop = threading.Event()
    capture = LiveAudioCapture(source, stop=stop)
    capture.start()
    assert not sd.inputs[0].closed

    stop.set()
    capture.close()
    assert sd.inputs[0].closed
    hal.close()


# --- 2. VoiceSession.play_live tests --------------------------------------------------------------


def test_play_live_command_reaches_gate_and_speaker_plays_reply(door: Path) -> None:
    # 500 ms silence + 900 ms speech tone ("mở cửa") + 2000 ms silence
    pcm = silence(500) + tone(900, RATE) + silence(2000)
    source = ScriptedLiveSource(pcm)
    voice = voice_on(
        door,
        stt=FakeSpeechToText(["mở cửa"], latency_ms=100),
        tts=FakeTextToSpeech(ms_per_char=30),
    )

    asyncio.run(voice.play_live(source))

    assert len(voice.turns) == 1
    turn = voice.turns[0]
    assert turn.heard == "mở cửa"
    assert turn.result.allowed is True
    assert voice.hal.pin("door_lock").pulsed is True
    playbacks = voice.hal.speaker().playbacks
    assert len(playbacks) == 1
    assert playbacks[0].stopped_at_ms is None


def test_play_live_barge_in_stops_speaker_and_cancels_pending_command(door: Path) -> None:
    # Turn 1: 500 ms silence + 900 ms tone ("mở cửa sau hai giây") + 600 ms silence.
    # At 2000 ms, turn ends. STT latency 100 ms => transcript delivered at 2100 ms.
    # open_door_later schedules door_lock pulse at 2100 + 2000 = 4100 ms.
    # Reply has 24 chars * 50 ms = 1200 ms (plays from 2100 to 3300 ms).
    # Person speaks from 2600 to 3200 ms: VAD confirms start at 2660 ms.
    # Speaker must stop at 2660 ms (< 300 ms after 2600 ms speech start).
    # Pending command at 4100 ms must be cancelled and its token closed.
    parts = (500, 900, 1200, 600, 2000)
    pcm = b"".join(silence(ms) if i % 2 == 0 else tone(ms, RATE) for i, ms in enumerate(parts))
    source = ScriptedLiveSource(pcm)
    voice = voice_on(
        door,
        stt=FakeSpeechToText(["mở cửa sau hai giây", ""]),
        tts=FakeTextToSpeech(ms_per_char=50),
    )

    asyncio.run(voice.play_live(source))

    kinds = [e["type"] for e in voice.events.events]
    assert "actuator_aborted" in kinds
    assert voice.events.of_type("actuator_aborted") == [
        {"pin": "door_lock", "reason": "ACTUATOR_ABORTED_BY_BARGE_IN"}
    ]
    assert voice.hal.pin("door_lock").never_pulsed()
    (cut,) = voice.events.of_type("tts_stream_end")
    assert cut["reason"] == "barge_in"

    (playback,) = voice.hal.speaker().playbacks
    # Speech started at 2600 ms; barge-in confirmed at 2660 ms (stop is 60 ms < 300 ms after start)
    assert playback.stopped_at_ms is not None
    assert playback.stopped_at_ms == 2660
    assert playback.stopped_at_ms - 2600 < 300


def test_play_live_slow_stt_drops_late_transcript(door: Path) -> None:
    # Turn 1: 500 ms silence + 900 ms tone + 600 ms silence (turn ends at 2000 ms).
    # STT latency 1500 ms => scheduled at 3500 ms.
    # Person speaks again from 2300 to 3100 ms (speech start at 2360 ms).
    # Turn 2 opens. At 3500 ms, Turn 1 STT result arrives late and is dropped.
    parts = (500, 900, 900, 800, 2000)
    pcm = b"".join(silence(ms) if i % 2 == 0 else tone(ms, RATE) for i, ms in enumerate(parts))
    source = ScriptedLiveSource(pcm)
    voice = voice_on(
        door,
        stt=FakeSpeechToText(["mở cửa", "mở cửa"], latency_ms=1500),
        tts=FakeTextToSpeech(ms_per_char=20),
    )

    asyncio.run(voice.play_live(source))

    dropped = voice.events.of_type("voice_late_result_dropped")
    assert dropped == [{"turn": 1, "input": "stt_result"}]


def test_play_live_half_duplex_silences_echo_and_prevents_barge_in(door: Path) -> None:
    # Same audio as barge-in test, where reply plays during 2100..3300 ms and loud echo
    # arrives at 2600..3200 ms. With half_duplex=True, the frames during reply are
    # replaced by silence, so no VAD start triggers, no barge-in, and playback finishes.
    parts = (500, 900, 1200, 600, 2000)
    pcm = b"".join(silence(ms) if i % 2 == 0 else tone(ms, RATE) for i, ms in enumerate(parts))

    source_hd = ScriptedLiveSource(pcm)
    voice_hd = voice_on(
        door,
        stt=FakeSpeechToText(["mở cửa sau hai giây", ""]),
        tts=FakeTextToSpeech(ms_per_char=50),
    )
    asyncio.run(voice_hd.play_live(source_hd, half_duplex=True))

    (end_hd,) = voice_hd.events.of_type("tts_stream_end")
    assert end_hd["reason"] == "done"  # NOT barge_in
    assert not voice_hd.events.of_type("actuator_aborted")
    (playback_hd,) = voice_hd.hal.speaker().playbacks
    assert playback_hd.stopped_at_ms is None  # played completely
    assert len(voice_hd.turns) == 1


# --- 3. CLI tests ---------------------------------------------------------------------------------


def test_cli_mic_on_linux_exits_2() -> None:
    result = runner.invoke(app, ["run", "--mic", "--target", "linux"])
    assert result.exit_code == 2
    assert "PipeWire echo cancellation" in result.output
    assert "Q-50" in result.output
    assert "docs/spec/simulation_coverage.md §6.2" in result.output


def test_cli_mic_with_ui_exits_2() -> None:
    result = runner.invoke(app, ["run", "--mic", "--ui"])
    assert result.exit_code == 2
    assert "the live page does not play or record audio yet" in result.output


@pytest.mark.parametrize(
    "flags",
    [
        ["run", "--mic", "--voice-file", "x.wav"],
        ["run", "--mic", "--voice-out", "x.wav"],
        ["run", "--mic", "-c", "mở cửa"],
        ["run", "--half-duplex"],
    ],
)
def test_cli_mic_mutually_exclusive_flags_exit_1(flags: list[str]) -> None:
    result = runner.invoke(app, flags)
    assert result.exit_code == 1
    assert "✗" in result.output or "Error" in result.output


def test_cli_mic_without_stt_exits_1(project: Any) -> None:
    agent = project("")
    result = runner.invoke(app, ["run", "--mic", "--agent", str(agent)])
    assert result.exit_code == 1
    assert "NE3002" in result.output
    assert "[stt]" in result.output
    assert "Q-15" in result.output


def test_cli_mic_missing_sounddevice_exits_1(
    project: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = project()
    monkeypatch.setitem(sys.modules, "sounddevice", None)
    result = runner.invoke(app, ["run", "--mic", "--agent", str(agent)])
    assert result.exit_code == 1
    assert "NE3001" in result.output
    assert "sounddevice" in result.output
    assert "pip install 'neuroedge[audio]'" in result.output


def test_cli_mic_happy_path(
    project: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = project()
    # 500 ms silence (25 blocks) + 900 ms tone (45 blocks) + 2000 ms silence (100 blocks)
    block_bytes = 2 * RATE * 20 // 1000
    blocks = [bytes(block_bytes)] * 25 + [tone(20, RATE)] * 45 + [bytes(block_bytes)] * 100
    sd = EndingFakeSounddevice(blocks)
    monkeypatch.setitem(sys.modules, "sounddevice", sd)

    trace = tmp_path / "trace.json"
    result = runner.invoke(
        app,
        ["run", "--mic", "--agent", str(agent), "--trace-out", str(trace)],
    )

    assert result.exit_code == 0, result.output
    assert "turn 1 ·" in result.output
    assert "heard: “mở cửa”" in result.output
    assert "ALLOW" in result.output
    assert "Dùng tai nghe — loa ngoài thì thêm --half-duplex" in result.output
    assert "1 turns" in result.output

    trace_data = load_trace(trace)
    kinds = [e["type"] for e in trace_data["events"]]
    assert "stt_result" in kinds
    assert "actuator_command" in kinds


def test_cli_mic_half_duplex_banner(
    project: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = project()
    block_bytes = 2 * RATE * 20 // 1000
    blocks = [bytes(block_bytes)] * 5
    sd = EndingFakeSounddevice(blocks)
    monkeypatch.setitem(sys.modules, "sounddevice", sd)

    result = runner.invoke(
        app,
        ["run", "--mic", "--half-duplex", "--agent", str(agent)],
    )
    assert result.exit_code == 0, result.output
    assert "half-duplex: bật" in result.output


def test_cli_mic_ctrl_c_exits_0(
    project: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = project()
    block_bytes = 2 * RATE * 20 // 1000
    blocks = [bytes(block_bytes)] * 25 + [tone(20, RATE)] * 45 + [bytes(block_bytes)] * 10
    sd = InterruptingFakeSounddevice(blocks)
    monkeypatch.setitem(sys.modules, "sounddevice", sd)

    trace = tmp_path / "trace.json"
    result = runner.invoke(
        app,
        ["run", "--mic", "--agent", str(agent), "--trace-out", str(trace)],
    )

    assert result.exit_code == 0, result.output
    assert trace.exists()
    trace_data = load_trace(trace)
    assert trace_data["events"]


def test_help_shows_mic_and_half_duplex() -> None:
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "--mic" in result.output
    assert "--half-duplex" in result.output
