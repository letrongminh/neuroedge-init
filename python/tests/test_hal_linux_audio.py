"""
TSK-S5-08 — `audio.in` / `audio.out` on `linux`, against the fake gpiod of
`test_hal_linux.py` and a fake `sounddevice`, so these run everywhere (macOS
included). The real-kernel cases (file backend on gpio-sim) are in `tests_linux/`.

Two backends, chosen, never guessed: the file one a `--voice-file` session uses
(a WAV at any rate in 8–96 kHz, 1–2 channels, converted to the board's 48 kHz
mono) and the live one through `sounddevice` (PipeWire echo-cancel nodes of Q-22).
A missing device, a device that disappears or a wrong format is a three-part
error — never silence passed off as input.
"""

from __future__ import annotations

import sys
import threading
import wave

import pytest

import neuroedge.hal.linux as linux
from neuroedge.engine.compiler import build
from neuroedge.engine.trace_sink import EventLog
from neuroedge.errors import BoardCapabilityError
from neuroedge.hal.audio import EnergyVAD, energy_db
from neuroedge.hal.board import load_board_by_id
from neuroedge.hal.linux import LinuxHAL, LiveSpeaker
from neuroedge.perception.providers.fake import tone

from .fake_sounddevice import FakeInputStream, FakeSounddevice, stereo
from .test_hal_linux import LINES, FakeGpiod

RATE = 48000
INPUT_DEVICE = linux.AUDIO_IN_NODE
OUTPUT_DEVICE = linux.AUDIO_OUT_NODE


@pytest.fixture(autouse=True)
def no_machine_wiring(monkeypatch):
    """The developer's own environment must not decide what these tests see."""
    for name in (linux.AUDIO_ENV, linux.AUDIO_IN_ENV, linux.AUDIO_OUT_ENV):
        monkeypatch.delenv(name, raising=False)


def write_wav(path, pcm, rate=RATE, channels=1, width=2):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(pcm)
    return path


def make(tmp_path, fake=None, **kwargs):
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    fake = fake if fake is not None else FakeGpiod({str(chip): LINES})
    hal = LinuxHAL(
        chip_glob=str(tmp_path / "gpiochip*"),
        gpiod=fake,
        events=EventLog(target="linux", board_id="linux-rpi5"),
        authorize=lambda *_: None,
        **kwargs,
    )
    return hal, fake


# --- the file backend -----------------------------------------------------------------


def test_the_board_declares_48k_stereo_and_no_aec():
    board = load_board_by_id("linux-rpi5")
    assert board.capability("audio.in") == {
        "channels": 2,
        "sample_rate_hz": 48000,
        "aec": False,
        "vad": True,
    }
    assert board.capability("audio.out")["sample_rate_hz"] == 48000


def test_a_16k_mono_wav_is_converted_to_the_board_rate(tmp_path):
    pcm = bytes(2 * 16000 // 10) + tone(200, 16000) + bytes(2 * 16000 * 3 // 10)
    path = write_wav(tmp_path / "turn.wav", pcm, rate=16000)
    hal, _ = make(tmp_path)
    source = hal.audio_file(path, called_from="test")
    assert source.sample_rate_hz == RATE
    assert abs(source.duration_ms - 600) <= 5, "100 + 200 + 300 ms of audio, at 48 kHz"
    frames = list(source.frames())
    assert {f.duration_ms for f in frames} == {20}
    assert all(f.sample_rate_hz == RATE for f in frames)
    # The tone survives the conversion: the VAD hears speech where the tone is.
    vad = EnergyVAD()
    edges = [(f.end_ms, edge[0]) for f in frames if (edge := vad.push(f)) is not None]
    assert [kind for _, kind in edges] == ["start", "end"]
    assert 160 <= edges[0][0] <= 200 and 480 <= edges[1][0] <= 580


def test_a_stereo_file_is_downmixed_and_a_44k_file_resampled(tmp_path):
    stereo = b"".join(s + s for s in (tone(50, 44100)[i : i + 2] for i in range(0, 4410, 2)))
    path = write_wav(tmp_path / "st.wav", stereo, rate=44100, channels=2)
    hal, _ = make(tmp_path)
    source = hal.audio_file(path, called_from="test")
    assert source.sample_rate_hz == RATE and abs(source.duration_ms - 50) <= 2
    assert energy_db(b"".join(f.pcm for f in source.frames())) > -30, "the tone is still there"


def test_a_file_the_device_would_not_take_is_refused_with_where_why_how(tmp_path):
    hal, _ = make(tmp_path)
    good = write_wav(tmp_path / "ok.wav", bytes(2 * RATE * 200 // 1000))  # 200 ms
    cases = [
        (write_wav(tmp_path / "wide.wav", bytes(300), width=3), "24-bit"),
        (write_wav(tmp_path / "many.wav", bytes(600), channels=3), "3 channels"),
        (write_wav(tmp_path / "slow.wav", bytes(800), rate=4000), "4000 Hz"),
        (write_wav(tmp_path / "long.wav", bytes(2 * 16000 * 601), rate=16000), "601 s long"),
        (tmp_path / "junk.wav", "not a PCM WAV"),
        (tmp_path / "missing.wav", "no such file"),
    ]
    (tmp_path / "junk.wav").write_bytes(b"not a wav at all")
    for path, why in cases:
        with pytest.raises(BoardCapabilityError) as raised:
            hal.audio_file(path, called_from="report()")
        error = raised.value
        assert why in error.why, (path, error.why)
        assert error.where.startswith("report() -> audio.in ") and path.name in error.where
        assert error.how, "the three-part contract: a way to fix it"
    assert hal.events.of_type("audio_in_segment") == [], "a refused file records nothing"
    assert hal.audio_file(good, called_from="test").duration_ms == 200


def test_the_speaker_is_the_board_timeline_at_48k(tmp_path):
    hal, _ = make(tmp_path)
    speaker = hal.speaker(called_from="test")
    assert speaker.sample_rate_hz == RATE and isinstance(speaker, type(speaker))
    speaker.play(tone(200, RATE), 0)
    path = speaker.write(tmp_path / "out.wav")
    with wave.open(str(path)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getnframes()) == (RATE, 1, 9600)


def test_replay_keeps_to_the_file_backend_and_opens_no_device(tmp_path):
    hal, _ = make(tmp_path, audio="live", replay=True)
    assert hal.audio_backend == "file"
    with pytest.raises(BoardCapabilityError, match="no live audio backend"):
        hal.audio_source()


# --- the live backend: explicit choice -------------------------------------------------


def test_live_audio_is_refused_unless_the_backend_is_chosen(tmp_path):
    hal, _ = make(tmp_path)
    assert hal.audio_backend is None
    for call in (hal.audio_source, hal.audio_sink):
        with pytest.raises(BoardCapabilityError) as raised:
            call(called_from="session")
        assert "refusing to guess" in raised.value.why
        assert linux.AUDIO_ENV in raised.value.how
    assert hal.speaker().sample_rate_hz == RATE, "the file timeline still works"


def test_the_live_backend_and_its_nodes_come_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv(linux.AUDIO_ENV, "live")
    monkeypatch.setenv(linux.AUDIO_IN_ENV, "my.mic")
    hal, _ = make(tmp_path, sounddevice=FakeSounddevice())
    assert hal.audio_backend == "live"
    assert hal.audio_in_device == "my.mic"
    assert hal.audio_out_device == linux.AUDIO_OUT_NODE
    monkeypatch.delenv(linux.AUDIO_IN_ENV)
    other = tmp_path / "b"
    other.mkdir()
    hal, _ = make(other, sounddevice=FakeSounddevice())
    assert hal.audio_in_device == linux.AUDIO_IN_NODE


def test_a_bad_backend_value_is_refused_before_any_line(tmp_path, monkeypatch):
    monkeypatch.setenv(linux.AUDIO_ENV, "alsa")
    with pytest.raises(BoardCapabilityError) as raised:
        make(tmp_path, audio="alsa")
    assert "unknown audio backend" in raised.value.why
    assert "file" in raised.value.how and "live" in raised.value.how


def test_sounddevice_missing_is_a_three_part_error(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "sounddevice", None)  # `import sounddevice` raises
    hal, _ = make(tmp_path, audio="live")
    with pytest.raises(BoardCapabilityError) as raised:
        hal.audio_source(called_from="session")
    assert "sounddevice" in raised.value.why and "not installed" in raised.value.why
    assert "neuroedge[audio]" in raised.value.how


# --- the live backend: capture ---------------------------------------------------------


def test_live_capture_reads_the_board_format_as_mono_frames(tmp_path):
    first, second = tone(20, RATE), tone(20, RATE)
    sd = FakeSounddevice([stereo(first), stereo(second)])
    hal, _ = make(tmp_path, audio="live", sounddevice=sd)
    frames = hal.audio_source(called_from="session").frames()
    one, two = next(frames), next(frames)
    with pytest.raises(BoardCapabilityError) as raised:
        next(frames)  # the script ends: the device stopped answering
    assert one.pcm == first and one.start_ms == 0 and one.duration_ms == 20
    assert two.start_ms == 20 and two.end_ms == 40
    assert sd.inputs[0].started
    assert "stopped answering" in raised.value.why and INPUT_DEVICE in raised.value.where
    assert "restart the session" in raised.value.how
    hal.close()
    assert sd.inputs[0].aborted and sd.inputs[0].closed


def test_live_capture_never_reads_silence_as_input(tmp_path):
    sd = FakeSounddevice(mode="empty")
    hal, _ = make(tmp_path, audio="live", sounddevice=sd)
    with pytest.raises(BoardCapabilityError) as raised:
        next(hal.audio_source().frames())
    assert "empty block" in raised.value.why
    assert "silence is never passed off" in raised.value.why
    hal.close()


def test_a_device_that_is_not_there_or_refuses_the_format_fails_closed(tmp_path):
    first = tmp_path / "a"
    first.mkdir()
    hal, _ = make(first, audio="live", sounddevice=FakeSounddevice(devices=set()))
    with pytest.raises(BoardCapabilityError) as raised:
        hal.audio_source(called_from="listen()")
    assert "no input device named" in raised.value.why and INPUT_DEVICE in raised.value.why
    assert linux.AUDIO_IN_ENV in raised.value.how
    assert hal.events.of_type("audio_in_segment") == []

    second = tmp_path / "b"
    second.mkdir()
    hal, _ = make(second, audio="live", sounddevice=FakeSounddevice(fail_format=True))
    with pytest.raises(BoardCapabilityError) as raised:
        hal.audio_source()
    assert "refuses 48000 Hz, 2 channel(s), 16-bit" in raised.value.why
    with pytest.raises(BoardCapabilityError) as raised:
        hal.audio_sink()
    assert "refuses 48000 Hz, 2 channel(s), 16-bit" in raised.value.why
    assert OUTPUT_DEVICE in raised.value.where
    missing = tmp_path / "c"
    missing.mkdir()
    hal, _ = make(missing, audio="live", sounddevice=FakeSounddevice(devices=set()))
    with pytest.raises(BoardCapabilityError) as raised:
        hal.audio_sink()
    assert "no output device named" in raised.value.why and OUTPUT_DEVICE in raised.value.why


def test_an_input_overflow_is_recorded_and_stops_the_frames(tmp_path):
    sd = FakeSounddevice(mode="overflow")
    hal, _ = make(tmp_path, audio="live", sounddevice=sd)
    with pytest.raises(BoardCapabilityError) as raised:
        next(hal.audio_source().frames())
    assert "overflowed" in raised.value.why and "cannot be trusted" in raised.value.why
    assert raised.value.how and "keep up" in raised.value.how
    (overflow,) = hal.events.of_type("audio_in_overflow")
    assert overflow == {}, "the overflow is visible in the trace, not silent"
    hal.close()


def test_a_stream_that_will_not_start_is_closed_not_dropped(tmp_path):
    class BadStart(FakeInputStream):
        def start(self):
            raise OSError(19, "No such device")

    class BadSounddevice(FakeSounddevice):
        def RawInputStream(self, **kwargs):  # noqa: N802 - mirrors sounddevice
            stream = BadStart(self, kwargs["device"], kwargs["channels"], kwargs["samplerate"])
            self.inputs.append(stream)
            return stream

    sd = BadSounddevice()
    hal, _ = make(tmp_path, audio="live", sounddevice=sd)
    with pytest.raises(BoardCapabilityError, match="refuses 48000 Hz"):
        hal.audio_source()
    assert sd.inputs[0].closed, "a half-open stream is closed, never just dropped"
    hal.close()


def test_preflight_opens_live_devices_before_any_line_is_requested(tmp_path):
    sd = FakeSounddevice()
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    hal = LinuxHAL(
        chip_glob=str(tmp_path / "gpiochip*"),
        gpiod=FakeGpiod({str(chip): LINES}),
        audio="live",
        sounddevice=sd,
        needs={"audio": ("audio.in", "audio.out"), "where": "agent"},
    )
    assert [type(stream).__name__ for stream in (*sd.inputs, *sd.outputs)] == [
        "FakeInputStream",
        "FakeOutputStream",
    ], "both devices opened, and before __init__ requested the lines"
    hal.close()


def test_a_live_device_that_cannot_open_refuses_before_any_line(tmp_path):
    fake = FakeGpiod({str(tmp_path / "gpiochip0"): LINES})
    (tmp_path / "gpiochip0").write_text("")
    with pytest.raises(BoardCapabilityError, match="no input device named"):
        LinuxHAL(
            chip_glob=str(tmp_path / "gpiochip*"),
            gpiod=fake,
            audio="live",
            sounddevice=FakeSounddevice(devices=set()),
            needs={"audio": ("audio.in",), "where": "agent"},
        )
    assert fake.requests == [], "no GPIO line is requested for a device that cannot open"


def test_a_close_while_capture_waits_ends_the_frames(tmp_path):
    sd = FakeSounddevice(blocking=True)
    hal, _ = make(tmp_path, audio="live", sounddevice=sd)
    frames = hal.audio_source().frames()
    seen: list[object] = []
    waiting = threading.Event()

    def read_until_closed():
        try:
            waiting.set()  # the thread is about to block in read()
            seen.append(next(frames))  # blocks until close() aborts the stream
        except StopIteration:
            seen.append("closed")

    reader = threading.Thread(target=read_until_closed)
    reader.start()
    assert waiting.wait(2.0), "the reader thread started"
    hal.close()
    reader.join(timeout=2.0)
    assert seen == ["closed"] and not reader.is_alive()


# --- the live backend: playback ---------------------------------------------------------


def test_live_playback_interleaves_to_the_device_and_stop_aborts(tmp_path):
    sd = FakeSounddevice()
    hal, _ = make(tmp_path, audio="live", sounddevice=sd)
    speaker = hal.speaker(called_from="VoiceSession")
    assert isinstance(speaker, LiveSpeaker)
    pcm = tone(100, RATE)
    playback = speaker.play(pcm, 0)
    assert hal.audio_sink().wait(), "the writer finished"
    written = b"".join(sd.outputs[0].written)
    assert written == stereo(pcm), "mono 48 kHz on a stereo node, byte for byte"
    assert playback in speaker.playbacks, "the WAV timeline still holds the reply"
    speaker.stop(50)
    assert sd.outputs[0].aborted and playback.played == pcm[: 50 * RATE // 1000 * 2]
    hal.close()
    assert sd.outputs[0].closed


def test_playback_restarts_an_aborted_stream_instead_of_writing_to_a_stopped_one(tmp_path):
    # abort() (a stop, or the next reply replacing one in flight) leaves PortAudio's
    # stream stopped: the next write must be preceded by start(), or it fails with
    # "Stream is stopped" — the fake raises exactly that when a write finds it stopped.
    sd = FakeSounddevice()
    hal, _ = make(tmp_path, audio="live", sounddevice=sd)
    sink = hal.audio_sink()
    first, second, third = tone(20, RATE), tone(20, RATE), tone(40, RATE)
    sink.play(first)
    assert sink.wait(), "the first reply played"
    sink.stop()  # barge-in: abort() stops the stream
    assert not sd.outputs[0].started
    sink.play(second)  # a reply after the stop: start() again before writing
    assert sink.wait() and sd.outputs[0].started
    sink.play(third)  # a reply replacing one in flight: play() aborts, then starts
    assert sink.wait()
    assert b"".join(sd.outputs[0].written) == stereo(first) + stereo(second) + stereo(third)
    hal.close()


def test_a_speaker_that_fails_is_never_just_quiet(tmp_path):
    sd = FakeSounddevice()
    hal, _ = make(tmp_path, audio="live", sounddevice=sd)
    sink = hal.audio_sink()
    sd.outputs[0].fail_after = 0  # the very first write fails as if the device went away
    sink.play(tone(60, RATE))
    assert sink.wait(), "the failed writer ended"
    assert sink._error is not None
    with pytest.raises(BoardCapabilityError) as raised:
        hal.close()
    assert "failed while playing" in raised.value.why
    hal.close()  # reported once: closing again is quiet
    with pytest.raises(BoardCapabilityError, match="previous reply failed"):
        sink.play(tone(60, RATE))


def test_the_live_speaker_is_never_opened_by_a_file_session(tmp_path, monkeypatch):
    monkeypatch.setenv(linux.AUDIO_ENV, "live")
    hal, _ = make(tmp_path, audio="file")  # --voice-file forces this, env or not
    assert hal.audio_backend == "file"
    speaker = hal.speaker()
    assert not isinstance(speaker, LiveSpeaker)
    speaker.play(tone(20, RATE), 0)
    assert hal._sounddevice is None, "a file session never imports sounddevice"


# --- the build never grants a capability the board does not have ------------------------


def test_linux_keeps_aec_false_and_the_build_refuses_an_agent_that_needs_it(root):
    villa = root / "fixtures" / "agents" / "villa-concierge" / "agent.toml"
    failed = None
    try:
        build(villa, target="linux", board_id="linux-rpi5")
    except Exception as exc:  # BuildFailed aggregates the problems
        failed = exc
    assert failed is not None
    problems = list(getattr(failed, "problems", []))
    whys = " ".join(getattr(p, "why", "") for p in problems)
    hows = " ".join(getattr(p, "how", "") for p in problems)
    assert "does not provide audio.in aec = true" in whys
    assert "use a board with AEC" in hows


def test_linux_implements_every_primitive():
    assert linux.MISSING_ON_LINUX == {}, "TSK-S5-08 brought the last one: audio"
