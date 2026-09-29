"""
TSK-I4-04 (slice 2, decision Q-50) — real-time voice session: `neuroedge run --mic [--half-duplex]`.

The session clock stays a `VirtualClock`, driven by the microphone's sample clock
instead of a file (`play_live`). A capture thread reads `source.frames()` into a bounded
queue so PortAudio does not overflow during provider calls. In half-duplex mode, frames
captured while a reply is playing are silenced to prevent echo through loudspeakers.
"""

from __future__ import annotations

import asyncio
import shutil
import sys
import threading
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.errors import BoardCapabilityError, PerceptionUnavailableError
from neuroedge.hal.audio import AudioFrame, Speaker, WavSource
from neuroedge.hal.sim import SimHAL
from neuroedge.perception import VirtualClock, VoiceParams, VoiceSession
from neuroedge.perception.live import LiveAudioCapture
from neuroedge.perception.providers import FakeSpeechToText, FakeTextToSpeech
from neuroedge.perception.providers.fake import tone
from neuroedge.sim import SimSession
from neuroedge.testing.recorder import TraceRecorder
from neuroedge.trace import load_trace

from .fake_sounddevice import FakeSounddevice
from .test_voice_speech import (
    PARAMS,
    RATE,
    at,
    silence,
    states,
)

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


def make_speech_pcm(*parts: int) -> bytes:
    """Alternating silence and speech tone: make_speech_pcm(500, 900, 3000)."""
    return b"".join(silence(ms) if i % 2 == 0 else tone(ms, RATE) for i, ms in enumerate(parts))


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


def _run_both(
    build_voice: Callable[[], VoiceSession],
    pcm: bytes,
    *,
    settle_ms: float = 60_000,
    before_run: Callable[[VoiceSession], None] | None = None,
) -> tuple[VoiceSession, VoiceSession]:
    """
    Run the same audio scenario through both play(WavSource) and play_live(ScriptedLiveSource),
    asserting complete equivalence between the file and live paths.
    """
    # 1. Virtual clock driven by file:
    voice_file = build_voice()
    if before_run is not None:
        before_run(voice_file)
    asyncio.run(voice_file.play(WavSource("turn.wav", pcm, RATE), settle_ms=settle_ms))

    # 2. Virtual clock driven by live source (mic sample clock):
    voice_live = build_voice()
    if before_run is not None:
        before_run(voice_live)
    asyncio.run(voice_live.play_live(ScriptedLiveSource(pcm, RATE), settle_ms=settle_ms))

    # Event equivalence: identical (type, data)
    events_file = [(e["type"], e["data"]) for e in voice_file.events.events]
    events_live = [(e["type"], e["data"]) for e in voice_live.events.events]
    assert events_live == events_file, f"Events mismatch:\nlive: {events_live}\nfile: {events_file}"

    # Turns equivalence:
    assert len(voice_live.turns) == len(voice_file.turns)
    for t_live, t_file in zip(voice_live.turns, voice_file.turns):
        assert t_live.heard == t_file.heard
        assert (t_live.result.allowed if t_live.result else None) == (
            t_file.result.allowed if t_file.result else None
        )
        assert t_live.stt_failure == t_file.stt_failure

    # Pin states equivalence:
    for pin_name in voice_file.hal._pins:
        p_file = voice_file.hal.pin(pin_name)
        p_live = voice_live.hal.pin(pin_name)
        assert p_live.pulsed == p_file.pulsed
        assert len(p_live.pulses) == len(p_file.pulses)

    # Speaker playbacks equivalence:
    pb_file = voice_file.hal.speaker().playbacks
    pb_live = voice_live.hal.speaker().playbacks
    assert len(pb_live) == len(pb_file)
    for p_live, p_file in zip(pb_live, pb_file):
        assert p_live.stopped_at_ms == p_file.stopped_at_ms
        assert p_live.played == p_file.played

    return voice_file, voice_live


# --- 1. Capture thread unit tests -----------------------------------------------------------------


def test_capture_thread_frames_flow_in_order_then_error_surfaces() -> None:
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
        err = None
        try:
            await capture.next_frame(loop)
        except BoardCapabilityError as exc:
            err = exc
        return (f1, f2, f3), err

    (f1, f2, f3), err = asyncio.run(run())
    assert f1 is not None and f1.pcm == first and f1.start_ms == 0 and f1.end_ms == 20
    assert f2 is not None and f2.pcm == second and f2.start_ms == 20 and f2.end_ms == 40
    assert f3 is not None and f3.pcm == third and f3.start_ms == 40 and f3.end_ms == 60
    assert err is not None
    assert "stopped answering" in err.why

    capture.close()
    assert sd.inputs[0].closed
    hal.close()


def test_capture_thread_drains_queued_frames_before_raising_error() -> None:
    frame_bytes = bytes(2 * RATE * 20 // 1000)
    frames_list = [AudioFrame(frame_bytes, i * 20, 20, RATE) for i in range(5)]

    class FailingSource:
        def frames(self):
            for f in frames_list:
                yield f
            raise OSError(19, "Microphone disconnected")

    source = FailingSource()
    capture = LiveAudioCapture(source)
    capture.start()

    async def run():
        loop = asyncio.get_running_loop()
        received = []
        err = None
        try:
            while True:
                f = await capture.next_frame(loop)
                if f is None:
                    break
                received.append(f)
        except OSError as exc:
            err = exc
        return received, err

    received, err = asyncio.run(run())
    assert len(received) == 5
    assert [f.start_ms for f in received] == [0, 20, 40, 60, 80]
    assert err is not None and "Microphone disconnected" in str(err)
    capture.close()


def test_capture_thread_keyboard_interrupt_drains_frames_first() -> None:
    frame_bytes = bytes(2 * RATE * 20 // 1000)
    frames_list = [AudioFrame(frame_bytes, i * 20, 20, RATE) for i in range(5)]

    class InterruptingSource:
        def frames(self):
            for f in frames_list:
                yield f
            raise KeyboardInterrupt

    source = InterruptingSource()
    capture = LiveAudioCapture(source)
    capture.start()

    async def run():
        loop = asyncio.get_running_loop()
        received = []
        err = None
        try:
            while True:
                f = await capture.next_frame(loop)
                if f is None:
                    break
                received.append(f)
        except KeyboardInterrupt as exc:
            err = exc
        return received, err

    received, err = asyncio.run(run())
    assert len(received) == 5
    assert isinstance(err, KeyboardInterrupt)
    capture.close()


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

    threading.Timer(0.05, stop.set).start()

    async def run():
        loop = asyncio.get_running_loop()
        while True:
            f = await capture.next_frame(loop)
            if f is None:
                break

    asyncio.run(run())
    capture.close()
    assert sd.inputs[0].closed
    hal.close()


def test_capture_thread_clean_end_with_scripted_source() -> None:
    pcm = silence(60)
    source = ScriptedLiveSource(pcm)
    capture = LiveAudioCapture(source)
    capture.start()

    async def run():
        loop = asyncio.get_running_loop()
        frames = []
        while True:
            f = await capture.next_frame(loop)
            if f is None:
                break
            frames.append(f)
        return frames

    frames = asyncio.run(run())
    assert len(frames) == 3
    assert [f.start_ms for f in frames] == [0, 20, 40]
    capture.close()
    assert source.closed


# --- 2. Equivalence tests against test_voice_speech.py scenarios ----------------------------------


def test_a_spoken_command_goes_through_stt_and_the_gate(door: Path) -> None:
    stt = FakeSpeechToText(["mở cửa"], latency_ms=300)
    pcm = make_speech_pcm(500, 900, 3000)
    _, voice = _run_both(
        lambda: voice_on(door, stt=stt, tts=FakeTextToSpeech()),
        pcm,
    )

    assert states(voice)[:2] == [
        ("IDLE", "LISTENING", "speech_start", 1),
        ("LISTENING", "THINKING", "turn_end", 1),
    ]
    assert at(voice, "audio_in_vad_start") == [560] and at(voice, "audio_in_vad_end") == [1600]
    assert at(voice, "voice_state_changed")[1] == 2300 and at(voice, "stt_result") == [2600]
    assert voice.events.of_type("stt_result") == [{"turn": 1, "text": "mở cửa"}]
    assert [
        e["type"]
        for e in voice.events.events
        if e["type"] in ("text_input", "action_requested", "gate_evaluation_result", "actuator_command")
    ] == ["text_input", "action_requested", "gate_evaluation_result", "actuator_command"]
    assert voice.hal.pin("door_lock").pulsed_once(30000)
    assert voice.settled


def test_the_reply_plays_to_its_end_on_the_speaker(door: Path) -> None:
    pcm = make_speech_pcm(500, 900, 6000)
    _, voice = _run_both(
        lambda: voice_on(door, stt=FakeSpeechToText(["tắt đèn"]), tts=FakeTextToSpeech(ms_per_char=20)),
        pcm,
        before_run=lambda v: v.session.set_sensor("motion", True),
    )

    message, hint = voice.hal.spoken
    reply_ms = (len(message) + len(hint)) * 20
    start = at(voice, "tts_stream_start")[0]
    (end,) = voice.events.of_type("tts_stream_end")
    assert end["reason"] == "done" and end["duration_ms"] == reply_ms
    assert end["sha256"].startswith("sha256:")
    assert at(voice, "tts_stream_end") == [start + reply_ms]
    assert ("SPEAKING", "LISTENING", "ask_asked", 2) in states(voice)
    (playback,) = voice.hal.speaker().playbacks
    assert playback.stopped_at_ms is None and len(playback.played) == reply_ms * 32


def test_barge_in_stops_the_speaker(door: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stops: list[float] = []
    real_stop = Speaker.stop

    def spy(self, at_ms):
        stops.append(at_ms)
        real_stop(self, at_ms)

    monkeypatch.setattr(Speaker, "stop", spy)
    pcm = make_speech_pcm(500, 900, 1600, 800, 3000)
    _, voice = _run_both(
        lambda: voice_on(door, stt=FakeSpeechToText(["tắt đèn"]), tts=FakeTextToSpeech(ms_per_char=60)),
        pcm,
        before_run=lambda v: v.session.set_sensor("motion", True),
    )

    assert 3060 in stops
    (cut,) = voice.events.of_type("tts_stream_end")
    assert cut == {"duration_ms": 660, "reason": "barge_in"}
    assert at(voice, "tts_stream_end") == [3060]
    (playback, *_) = voice.hal.speaker().playbacks
    assert playback.stopped_at_ms == 3060 and len(playback.played) == 660 * 32
    assert len(playback.pcm) > len(playback.played)
    assert voice.session.pending_confirmation() is not None


def test_barge_in_during_tts_still_cancels_the_pending_command(door: Path) -> None:
    class SystemTwoFeederVoiceSession(VoiceSession):
        async def advance(self, to_ms: float, *, inclusive: bool = False) -> None:
            await super().advance(to_ms, inclusive=inclusive)
            if to_ms == 2700 and self._awaiting is not None:
                await self.feed(
                    "system_two_reply",
                    {
                        "turn": 1,
                        "text": "Cửa sẽ mở sau hai giây.",
                        "tool_calls": [{"name": "open_door_later", "arguments": {}}],
                    },
                )

    def build_voice() -> VoiceSession:
        clock = VirtualClock()
        session = SimSession.load(door, clock=clock)
        return SystemTwoFeederVoiceSession(
            session,
            clock=clock,
            params=PARAMS,
            stt=FakeSpeechToText(["làm ơn mở giúp cái cửa sau hai giây", ""]),
            tts=FakeTextToSpeech(ms_per_char=60),
            system_two=True,
        )

    pcm = make_speech_pcm(500, 900, 1400, 600, 2000)
    _, voice = _run_both(build_voice, pcm)

    kinds = [e["type"] for e in voice.events.events]
    abort = kinds.index("actuator_aborted")
    assert kinds[abort + 1] == "tts_stream_end"
    assert voice.events.of_type("actuator_aborted") == [
        {"pin": "door_lock", "reason": "ACTUATOR_ABORTED_BY_BARGE_IN"}
    ]
    assert voice.hal.pin("door_lock").never_pulsed()
    (playback,) = voice.hal.speaker().playbacks
    assert playback.stopped_at_ms == 2860
    assert "actuator_command" not in kinds


def test_stt_slower_than_the_think_timeout_is_stt_failing(door: Path) -> None:
    pcm = make_speech_pcm(500, 900, 12000)
    _, voice = _run_both(
        lambda: voice_on(door, stt=FakeSpeechToText(["mở cửa"], latency_ms=9000), tts=FakeTextToSpeech()),
        pcm,
    )

    assert voice.hal.spoken == [voice.session.unheard_help()]
    assert at(voice, "stt_unavailable") == [7300]
    assert "think timeout" in voice.events.of_type("stt_unavailable")[0]["reason"]
    assert voice.events.of_type("voice_late_result_dropped") == [{"turn": 1, "input": "stt_result"}]
    assert at(voice, "voice_late_result_dropped") == [11300]
    assert voice.hal.pin("door_lock").never_pulsed()


def test_play_live_half_duplex_silences_echo_and_prevents_barge_in(door: Path) -> None:
    # 1. Base run from test_the_reply_plays_to_its_end_on_the_speaker to determine reply window:
    base_pcm = make_speech_pcm(500, 900, 6000)
    v_base = voice_on(door, stt=FakeSpeechToText(["tắt đèn"]), tts=FakeTextToSpeech(ms_per_char=20))
    v_base.session.set_sensor("motion", True)
    asyncio.run(v_base.play(WavSource("base.wav", base_pcm, RATE)))

    start = at(v_base, "tts_stream_start")[0]
    (end,) = v_base.events.of_type("tts_stream_end")
    reply_duration = end["duration_ms"]

    # 2. Add loud tone frames inside reply playback window:
    silence_between = int(start + 200 - 1400)
    interrupt_pcm = (
        silence(500)
        + tone(900, RATE)
        + silence(silence_between)
        + tone(400, RATE)
        + silence(3000)
    )

    # 3. Full-duplex: loud tone barges in and cuts speaker early
    v_fd = voice_on(door, stt=FakeSpeechToText(["tắt đèn", ""]), tts=FakeTextToSpeech(ms_per_char=20))
    v_fd.session.set_sensor("motion", True)
    asyncio.run(v_fd.play_live(ScriptedLiveSource(interrupt_pcm, RATE), half_duplex=False))

    (cut_fd,) = v_fd.events.of_type("tts_stream_end")
    assert cut_fd["reason"] == "barge_in"
    assert cut_fd["duration_ms"] < reply_duration
    (pb_fd,) = v_fd.hal.speaker().playbacks
    assert pb_fd.stopped_at_ms is not None

    # 4. Half-duplex: frame is replaced by silence while reply plays, so no barge-in
    v_hd = voice_on(door, stt=FakeSpeechToText(["tắt đèn", ""]), tts=FakeTextToSpeech(ms_per_char=20))
    v_hd.session.set_sensor("motion", True)
    asyncio.run(v_hd.play_live(ScriptedLiveSource(interrupt_pcm, RATE), half_duplex=True))

    (end_hd,) = v_hd.events.of_type("tts_stream_end")
    assert end_hd["reason"] == "done"
    assert end_hd["duration_ms"] == reply_duration
    assert at(v_hd, "tts_stream_end") == [start + reply_duration]
    (pb_hd,) = v_hd.hal.speaker().playbacks
    assert pb_hd.stopped_at_ms is None
    assert len(pb_hd.played) == reply_duration * 32


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
    block_bytes = 2 * RATE * 20 // 1000
    blocks = [bytes(block_bytes)] * 25 + [tone(20, RATE)] * 45 + [bytes(block_bytes)] * 100
    sd = FakeSounddevice(blocks)
    monkeypatch.setitem(sys.modules, "sounddevice", sd)

    # When FakeSounddevice runs out of blocks, simulate Ctrl+C ending the session
    orig_next = LiveAudioCapture.next_frame

    async def next_frame_then_ctrl_c(self, loop):
        try:
            return await orig_next(self, loop)
        except BoardCapabilityError:
            raise KeyboardInterrupt from None

    monkeypatch.setattr(LiveAudioCapture, "next_frame", next_frame_then_ctrl_c)

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
    sd = FakeSounddevice(blocks)
    monkeypatch.setitem(sys.modules, "sounddevice", sd)

    orig_next = LiveAudioCapture.next_frame

    async def next_frame_then_ctrl_c(self, loop):
        try:
            return await orig_next(self, loop)
        except BoardCapabilityError:
            raise KeyboardInterrupt from None

    monkeypatch.setattr(LiveAudioCapture, "next_frame", next_frame_then_ctrl_c)

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
    sd = FakeSounddevice(blocks, blocking=True)
    monkeypatch.setitem(sys.modules, "sounddevice", sd)

    # Simulate Ctrl+C in the main thread during asyncio.run after receiving frames
    frame_count = 0
    orig_next = LiveAudioCapture.next_frame

    async def interrupt_main_thread(self, loop):
        nonlocal frame_count
        frame = await orig_next(self, loop)
        if frame is not None:
            frame_count += 1
            if frame_count >= 20:
                raise KeyboardInterrupt
        return frame

    monkeypatch.setattr(LiveAudioCapture, "next_frame", interrupt_main_thread)

    trace = tmp_path / "trace.json"
    result = runner.invoke(
        app,
        ["run", "--mic", "--agent", str(agent), "--trace-out", str(trace)],
    )

    assert result.exit_code == 0, result.output
    assert trace.exists()
    trace_data = load_trace(trace)
    assert trace_data["events"]
    assert sd.inputs[0].closed


def test_help_shows_mic_and_half_duplex() -> None:
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "--mic" in result.output
    assert "--half-duplex" in result.output
