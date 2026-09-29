"""
TSK-I4-04 (slice 1) — opt-in live audio backend on `SimHAL` (target `sim`).

`sim` defaults to no microphone and the timeline speaker (no `sounddevice` or `gpiod`
import). When `audio="live"` or `NEUROEDGE_AUDIO=live`, `audio_source()` and `audio_sink()`
open PortAudio streams at the board's rate (16000 Hz mono on `sim-default`) with default
device None (system default, no PipeWire dependency). Missing `sounddevice` produces a
three-part `BoardCapabilityError` referencing `SimHAL`.
"""

from __future__ import annotations

import sys

import pytest

import neuroedge.hal.sim as sim
from neuroedge.errors import BoardCapabilityError
from neuroedge.hal.audio import Speaker
from neuroedge.hal.audio_live import LiveAudioIn, LiveAudioOut, LiveSpeaker
from neuroedge.hal.sim import SimHAL

from .fake_sounddevice import FakeSounddevice

RATE = 16000


@pytest.fixture(autouse=True)
def no_machine_wiring(monkeypatch: pytest.MonkeyPatch) -> None:
    """The developer's own environment must not decide what these tests see."""
    for name in (sim.AUDIO_ENV, sim.AUDIO_IN_ENV, sim.AUDIO_OUT_ENV):
        monkeypatch.delenv(name, raising=False)


def test_default_simhal_never_imports_sounddevice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sim,
        "_import_sounddevice",
        lambda *args, **kwargs: pytest.fail("default SimHAL must not import sounddevice"),
    )
    hal = SimHAL()
    assert hal.audio_backend is None
    assert hal._sounddevice is None

    speaker = hal.speaker()
    assert isinstance(speaker, Speaker)
    assert not isinstance(speaker, LiveSpeaker)
    assert speaker.sample_rate_hz == RATE
    assert hal._sounddevice is None


def test_non_live_simhal_refuses_audio_source_and_sink() -> None:
    hal = SimHAL()
    for method, primitive in ((hal.audio_source, "audio.in"), (hal.audio_sink, "audio.out")):
        with pytest.raises(BoardCapabilityError) as raised:
            method(called_from="test_call")
        err = raised.value
        assert f"test_call -> {primitive}" in err.where
        assert "refusing to guess" in err.why
        assert "--mic" in err.how
        assert sim.AUDIO_ENV in err.how


def test_live_simhal_opens_default_device_at_16k_mono() -> None:
    sd = FakeSounddevice()
    hal = SimHAL(audio="live", sounddevice=sd)
    assert hal.audio_backend == "live"
    assert hal.audio_in_device is None
    assert hal.audio_out_device is None

    source = hal.audio_source()
    assert isinstance(source, LiveAudioIn)
    assert len(sd.inputs) == 1
    assert sd.inputs[0].device is None
    assert sd.inputs[0].rate == RATE
    assert sd.inputs[0].channels == 1
    assert sd.inputs[0].started

    sink = hal.audio_sink()
    assert isinstance(sink, LiveAudioOut)
    assert len(sd.outputs) == 1
    assert sd.outputs[0].device is None
    assert sd.outputs[0].rate == RATE
    assert sd.outputs[0].channels == 1

    speaker = hal.speaker()
    assert isinstance(speaker, LiveSpeaker)
    assert speaker.sample_rate_hz == RATE

    hal.close()
    assert sd.inputs[0].closed
    assert sd.outputs[0].closed


def test_env_backend_and_device_names_passed_through(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(sim.AUDIO_ENV, "live")
    monkeypatch.setenv(sim.AUDIO_IN_ENV, "laptop_mic")
    monkeypatch.setenv(sim.AUDIO_OUT_ENV, "laptop_speaker")

    sd = FakeSounddevice(devices={"laptop_mic", "laptop_speaker"})
    hal = SimHAL(sounddevice=sd)
    assert hal.audio_backend == "live"
    assert hal.audio_in_device == "laptop_mic"
    assert hal.audio_out_device == "laptop_speaker"

    hal.audio_source()
    assert sd.inputs[0].device == "laptop_mic"

    hal.audio_sink()
    assert sd.outputs[0].device == "laptop_speaker"

    hal.close()


def test_explicit_device_arguments_override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(sim.AUDIO_IN_ENV, "env_mic")
    monkeypatch.setenv(sim.AUDIO_OUT_ENV, "env_speaker")

    sd = FakeSounddevice(devices={"arg_mic", "arg_speaker"})
    hal = SimHAL(
        audio="live",
        audio_in_device="arg_mic",
        audio_out_device="arg_speaker",
        sounddevice=sd,
    )
    assert hal.audio_in_device == "arg_mic"
    assert hal.audio_out_device == "arg_speaker"

    hal.audio_source()
    assert sd.inputs[0].device == "arg_mic"

    hal.audio_sink()
    assert sd.outputs[0].device == "arg_speaker"

    hal.close()


def test_speaker_is_livespeaker_when_live_and_plain_speaker_otherwise() -> None:
    sd = FakeSounddevice()
    hal_live = SimHAL(audio="live", sounddevice=sd)
    speaker_live = hal_live.speaker()
    assert isinstance(speaker_live, LiveSpeaker)
    assert speaker_live.sample_rate_hz == RATE

    pcm = b"\x00\x00" * 320  # 20 ms 16 kHz mono
    playback = speaker_live.play(pcm, 0)
    assert hal_live.audio_sink().wait()
    assert sd.outputs[0].written == [pcm]
    assert playback in speaker_live.playbacks
    hal_live.close()

    hal_file = SimHAL(audio="file")
    speaker_file = hal_file.speaker()
    assert isinstance(speaker_file, Speaker)
    assert not isinstance(speaker_file, LiveSpeaker)
    assert speaker_file.sample_rate_hz == RATE
    speaker_file.play(pcm, 0)
    assert hal_file._sounddevice is None


def test_missing_sounddevice_is_three_part_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "sounddevice", None)
    hal = SimHAL(audio="live")
    with pytest.raises(BoardCapabilityError) as raised:
        hal.audio_source()
    err = raised.value
    assert "SimHAL" in err.where
    assert "audio.in/audio.out" in err.where
    assert "sounddevice" in err.why and "not installed" in err.why
    assert "pip install 'neuroedge[audio]'" in err.how

    with pytest.raises(BoardCapabilityError) as raised:
        SimHAL(audio="live").audio_sink()
    err = raised.value
    assert "SimHAL" in err.where
    assert "pip install 'neuroedge[audio]'" in err.how


def test_invalid_neuroedge_audio_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(BoardCapabilityError) as raised:
        SimHAL(audio="alsa")
    assert "SimHAL(audio=...)" in raised.value.where
    assert "unknown audio backend 'alsa'" in raised.value.why
    assert "file" in raised.value.how and "live" in raised.value.how

    monkeypatch.setenv(sim.AUDIO_ENV, "pulse")
    with pytest.raises(BoardCapabilityError) as raised:
        SimHAL()
    assert raised.value.where == sim.AUDIO_ENV
    assert "unknown audio backend 'pulse'" in raised.value.why
    assert "file" in raised.value.how and "live" in raised.value.how


def test_close_closes_streams_and_is_idempotent() -> None:
    sd = FakeSounddevice()
    hal = SimHAL(audio="live", sounddevice=sd)
    hal.audio_source()
    hal.audio_sink()
    assert not sd.inputs[0].closed
    assert not sd.outputs[0].closed

    hal.close()
    assert sd.inputs[0].closed
    assert sd.outputs[0].closed

    # Second close() is quiet and idempotent
    hal.close()
    assert sd.inputs[0].closed
    assert sd.outputs[0].closed


def test_close_reports_playback_failure_once() -> None:
    sd = FakeSounddevice()
    hal = SimHAL(audio="live", sounddevice=sd)
    sink = hal.audio_sink()
    sd.outputs[0].fail_after = 0
    sink.play(b"\x00\x00" * 320)
    assert sink.wait()

    with pytest.raises(BoardCapabilityError) as raised:
        hal.close()
    assert "failed while playing" in raised.value.why

    # Second close() is idempotent and quiet
    hal.close()

    with pytest.raises(BoardCapabilityError, match="previous reply failed"):
        sink.play(b"\x00\x00" * 320)


def test_live_capture_reads_frames() -> None:
    first = b"\x01\x00" * 320
    second = b"\x02\x00" * 320
    sd = FakeSounddevice([first, second])
    hal = SimHAL(audio="live", sounddevice=sd)
    frames = hal.audio_source().frames()
    one = next(frames)
    two = next(frames)

    assert one.pcm == first
    assert one.sample_rate_hz == RATE
    assert one.duration_ms == 20
    assert one.start_ms == 0
    assert one.end_ms == 20

    assert two.pcm == second
    assert two.start_ms == 20
    assert two.end_ms == 40

    hal.close()


def test_live_simhal_missing_device_raises_three_part_error() -> None:
    sd = FakeSounddevice(devices=set())
    hal = SimHAL(audio="live", sounddevice=sd)
    with pytest.raises(BoardCapabilityError) as raised_in:
        hal.audio_source()
    err_in = raised_in.value
    assert "SimHAL -> audio.in (None)" in err_in.where
    assert "no input device named None" in err_in.why
    assert sim.AUDIO_IN_ENV in err_in.how

    with pytest.raises(BoardCapabilityError) as raised_out:
        hal.audio_sink()
    err_out = raised_out.value
    assert "SimHAL -> audio.out (None)" in err_out.where
    assert "no output device named None" in err_out.why
    assert sim.AUDIO_OUT_ENV in err_out.how


def test_live_simhal_refused_format_raises_three_part_error() -> None:
    sd = FakeSounddevice(fail_format=True)
    hal = SimHAL(audio="live", sounddevice=sd)
    with pytest.raises(BoardCapabilityError) as raised:
        hal.audio_source()
    assert "refuses 16000 Hz, 1 channel(s), 16-bit" in raised.value.why
    assert "fix the board profile or the device" in raised.value.how

    with pytest.raises(BoardCapabilityError) as raised_out:
        hal.audio_sink()
    assert "refuses 16000 Hz, 1 channel(s), 16-bit" in raised_out.value.why


def test_env_backend_file_and_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(sim.AUDIO_ENV, "file")
    hal = SimHAL()
    assert hal.audio_backend == "file"
    speaker = hal.speaker()
    assert isinstance(speaker, Speaker)
    assert not isinstance(speaker, LiveSpeaker)


def test_no_sounddevice_or_gpiod_in_sys_modules() -> None:
    # Verifies import of neuroedge.hal.sim and neuroedge.hal.audio_live
    # did not eagerly import sounddevice or gpiod
    assert "sounddevice" not in sys.modules
    assert "gpiod" not in sys.modules

