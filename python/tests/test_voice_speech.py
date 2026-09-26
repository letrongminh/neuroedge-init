"""
TSK-S3-13 — the voice path on `sim`: a WAV file as `audio.in`, VAD, STT, the
conversation state machine, TTS on the speaker, barge-in (docs/spec/voice_fsm.md
§5, §7). Providers are the fakes of `perception.providers.fake`: no network, no
key, virtual time — every number below is exact.
"""

from __future__ import annotations

import asyncio
import json
import wave

import pytest

from neuroedge.engine.latency import TURN_EVENT
from neuroedge.errors import BoardCapabilityError
from neuroedge.hal.audio import (
    AudioFrame,
    EnergyVAD,
    Speaker,
    WavSource,
    energy_db,
    resample,
    to_mono,
)
from neuroedge.hal.sim import SimHAL
from neuroedge.perception import VirtualClock, VoiceParams, VoiceSession
from neuroedge.perception.providers import FakeSpeechToText, FakeTextToSpeech, Speech
from neuroedge.perception.providers.fake import tone
from neuroedge.sim import SimSession
from neuroedge.testing.recorder import TraceRecorder

RATE = 16000
PARAMS = VoiceParams(vad_activation=True, think_timeout_ms=5000)


@pytest.fixture(scope="module")
def door(root):
    return root / "fixtures" / "agents" / "voice-door" / "agent.toml"


def silence(ms: int) -> bytes:
    return bytes(2 * RATE * ms // 1000)


def write_wav(path, pcm: bytes, rate: int = RATE, channels: int = 1, width: int = 2):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(pcm)
    return path


def speech_file(tmp_path, *parts) -> WavSource:
    """Alternating silence and 'speech' (a tone), in ms: speech_file(p, 500, 900, 3000)."""
    pcm = b"".join(silence(ms) if i % 2 == 0 else tone(ms, RATE) for i, ms in enumerate(parts))
    return WavSource.open(
        write_wav(tmp_path / "turn.wav", pcm), sample_rate_hz=RATE, called_from="t"
    )


def voice_on(door, *, stt, tts=None, params=PARAMS, system_two=False, anonymize=None):
    clock = VirtualClock()
    events = None if anonymize is None else TraceRecorder(anonymize=anonymize, clock=clock)
    session = SimSession.load(door, clock=clock, events=events)
    return VoiceSession(
        session, clock=clock, params=params, stt=stt, tts=tts, system_two=system_two
    )


def states(voice):
    return [
        (e["from"], e["to"], e["trigger"], e["turn"])
        for e in voice.events.of_type("voice_state_changed")
    ]


def at(voice, kind):
    return [e["offset_ms"] for e in voice.events.events if e["type"] == kind]


# --- audio.in and audio.out on sim ----------------------------------------------------------------


def test_the_wav_source_takes_only_what_the_board_takes(tmp_path):
    good = write_wav(tmp_path / "ok.wav", silence(100))
    assert WavSource.open(good, sample_rate_hz=RATE, called_from="t").duration_ms == 100
    for name, kwargs in [
        ("rate.wav", {"rate": 44100}),
        ("stereo.wav", {"channels": 2}),
        ("wide.wav", {"width": 3}),
    ]:
        path = write_wav(tmp_path / name, silence(100), **kwargs)
        with pytest.raises(BoardCapabilityError) as caught:
            WavSource.open(path, sample_rate_hz=RATE, called_from="t")
        assert "16000 Hz mono 16-bit" in caught.value.why and "ffmpeg" in caught.value.how
    (tmp_path / "junk.wav").write_bytes(b"not a wav at all")
    for path in (tmp_path / "junk.wav", tmp_path / "missing.wav"):
        with pytest.raises(BoardCapabilityError) as caught:
            WavSource.open(path, sample_rate_hz=RATE, called_from="t")
        assert caught.value.where.endswith(path.name)


def test_the_board_decides_the_rate(tmp_path):
    hal = SimHAL()
    source = hal.audio_file(write_wav(tmp_path / "ok.wav", silence(40)), called_from="t")
    assert (
        source.sample_rate_hz == 16000 == hal.speaker().sample_rate_hz
    )  # sim-default mirrors Box-3


def test_frames_are_20_ms_and_the_vad_is_deterministic():
    frames = list(WavSource("x", silence(100) + tone(200, RATE) + silence(400), RATE).frames())
    assert {f.duration_ms for f in frames} == {20} and frames[-1].end_ms == 700
    vad = EnergyVAD()
    edges = [(f.end_ms, edge[0]) for f in frames if (edge := vad.push(f)) is not None]
    # Speech from 100 ms: confirmed after 60 ms. Quiet from 300 ms: ended after 200 ms.
    assert edges == [(160, "start"), (500, "end")]
    assert energy_db(tone(20, RATE)) == pytest.approx(-23.0, abs=0.1)  # a -20 dBFS peak sine
    assert energy_db(silence(20)) == -120.0


def test_resample_and_downmix():
    assert len(resample(tone(100, 24000), 24000, 16000)) == 1600 * 2
    assert resample(b"", 24000, 16000) == b""
    stereo = b"".join(s + s for s in (tone(10, RATE)[i : i + 2] for i in range(0, 320, 2)))
    assert to_mono(stereo, 2) == tone(10, RATE)


def test_the_speaker_is_a_timeline_cut_where_it_stops(tmp_path):
    speaker = Speaker(RATE)
    first = speaker.play(tone(1000, RATE), 500)
    speaker.stop(900)  # barge-in 400 ms into it
    speaker.play(tone(200, RATE), 2000)
    assert first.played == tone(1000, RATE)[: 400 * 32]
    path = speaker.write(tmp_path / "out.wav")
    with wave.open(str(path)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getnframes()) == (RATE, 1, 2200 * 16)


# --- a turn from audio ------------------------------------------------------------------------------


def test_a_spoken_command_goes_through_stt_and_the_gate(door, tmp_path):
    stt = FakeSpeechToText(["mở cửa"], latency_ms=300)
    voice = voice_on(door, stt=stt, tts=FakeTextToSpeech())
    asyncio.run(voice.play(speech_file(tmp_path, 500, 900, 3000)))
    # vad start 560 (60 ms in) · vad end 1600 (200 ms quiet) · turn end 2300 · STT +300 ms
    assert states(voice)[:2] == [
        ("IDLE", "LISTENING", "speech_start", 1),
        ("LISTENING", "THINKING", "turn_end", 1),
    ]
    assert at(voice, "audio_in_vad_start") == [560] and at(voice, "audio_in_vad_end") == [1600]
    assert at(voice, "voice_state_changed")[1] == 2300 and at(voice, "stt_result") == [2600]
    assert voice.events.of_type("stt_result") == [{"turn": 1, "text": "mở cửa"}]
    # The same path as a typed line: grammar → c.do() → gate → pin.
    assert [
        e["type"]
        for e in voice.events.events
        if e["type"]
        in ("text_input", "action_requested", "gate_evaluation_result", "actuator_command")
    ] == ["text_input", "action_requested", "gate_evaluation_result", "actuator_command"]
    assert voice.hal.pin("door_lock").pulsed_once(30000)
    # The clip sent to STT: 300 ms of pre-roll before speech was confirmed, to the turn's end.
    (sent,) = stt.clips
    assert sent.turn == 1 and sent.sample_rate_hz == RATE
    assert sent.duration_ms == 2300 - (560 - 20 - 300)
    assert voice.events.of_type("audio_in_segment") == [
        {"sha256": sent.sha256, "duration_ms": sent.duration_ms, "sample_rate_hz": RATE}
    ]
    assert voice.settled


def test_the_stt_wait_is_the_turns_perception_stage(door, tmp_path):
    voice = voice_on(door, stt=FakeSpeechToText(["mở cửa"], latency_ms=300))
    asyncio.run(voice.play(speech_file(tmp_path, 500, 900, 3000)))
    (timed,) = voice.events.of_type(TURN_EVENT)
    assert timed["stages_ms"]["perception"] == 300 and timed["total_ms"] == 300
    assert timed["path"] == "system_1"


def test_a_system_two_turn_splits_stt_and_the_model_wait(door, tmp_path):
    voice = voice_on(door, stt=FakeSpeechToText(["chào bạn nhé"], latency_ms=300), system_two=True)

    async def run():
        source = speech_file(tmp_path, 500, 900, 1500)
        for frame in source.frames():
            await voice.advance(frame.end_ms)
            await voice.feed_audio(frame)
        await voice.advance(3500)
        await voice.feed("system_two_reply", {"turn": 1, "text": "Chào bạn!"})

    asyncio.run(run())
    (timed,) = voice.events.of_type(TURN_EVENT)
    # sent 2300, heard 2600, answered 3500
    assert (timed["stages_ms"]["perception"], timed["stages_ms"]["system_two"]) == (300, 900)
    assert timed["path"] == "system_2" and timed["total_ms"] == 1200


def test_noise_the_stt_hears_nothing_in_is_t06(door, tmp_path):
    voice = voice_on(door, stt=FakeSpeechToText([""]))
    asyncio.run(voice.play(speech_file(tmp_path, 500, 300, 2000)))
    assert states(voice)[-1] == ("THINKING", "IDLE", "transcript_empty", 1)
    assert voice.events.of_type("voice_reprompt") == [{"turn": 1, "count": 1}]
    assert "action_requested" not in {e["type"] for e in voice.events.events}


def test_a_file_that_ends_mid_speech_still_ends_the_turn(door, tmp_path):
    voice = voice_on(door, stt=FakeSpeechToText(["mở cửa"]))
    asyncio.run(voice.play(speech_file(tmp_path, 500, 1000)))
    assert at(voice, "audio_in_vad_end") == [1500]  # the input ended: speech ends with it
    assert voice.hal.pin("door_lock").pulsed


# --- §7: STT gone, slow, broken --------------------------------------------------------------------


def _no_physical_act(voice):
    kinds = {e["type"] for e in voice.events.events}
    assert not kinds & {"action_requested", "gate_evaluation_result", "actuator_command"}
    assert voice.hal.pin("door_lock").never_pulsed()


def test_stt_unavailable_says_the_offline_line_and_never_acts(door, tmp_path):
    voice = voice_on(door, stt=FakeSpeechToText(["mở cửa"], fail=True), tts=FakeTextToSpeech())
    asyncio.run(voice.play(speech_file(tmp_path, 500, 900, 3000)))
    (failed,) = voice.events.of_type("stt_unavailable")
    assert failed["turn"] == 1 and "fail" in failed["reason"]
    assert voice.hal.spoken == [voice.session.unheard_help()]
    assert "gõ" in voice.hal.spoken[0]  # back to typed input + the local grammar (FR-MDL-03)
    _no_physical_act(voice)
    (timed,) = voice.events.of_type(TURN_EVENT)
    assert (timed["path"], timed["reply_source"]) == ("none", "offline_help")
    assert timed["stages_ms"]["perception"] == 100  # the fake's latency, spent failing
    assert voice.turns[0].heard is None and voice.turns[0].stt_failure


def test_an_adapter_that_crashes_is_unavailable_and_its_message_is_not_kept(door, tmp_path):
    class Broken:
        def transcribe(self, clip):
            raise RuntimeError("the user said: mở cửa kho SECRET")

    voice = voice_on(door, stt=Broken())
    asyncio.run(voice.play(speech_file(tmp_path, 500, 900, 3000)))
    (failed,) = voice.events.of_type("stt_unavailable")
    assert "RuntimeError" in failed["reason"] and "SECRET" not in json.dumps(voice.events.events)
    _no_physical_act(voice)


@pytest.mark.parametrize("answer", [None, 42, "mở\x00cửa", "m�"])
def test_a_garbled_transcript_is_unavailable_not_a_command(door, tmp_path, answer):
    voice = voice_on(door, stt=FakeSpeechToText(lambda clip: answer))
    asyncio.run(voice.play(speech_file(tmp_path, 500, 900, 3000)))
    assert voice.events.of_type("stt_unavailable") and not voice.events.of_type("stt_result")
    _no_physical_act(voice)


def test_stt_slower_than_the_think_timeout_is_stt_failing(door, tmp_path):
    voice = voice_on(door, stt=FakeSpeechToText(["mở cửa"], latency_ms=9000))
    asyncio.run(voice.play(speech_file(tmp_path, 500, 900, 12000)))
    # Turn end 2300 + think timeout 5000: the offline line at 7300; the transcript at 11300 is late.
    assert voice.hal.spoken == [voice.session.unheard_help()]
    assert at(voice, "stt_unavailable") == [7300]
    assert "think timeout" in voice.events.of_type("stt_unavailable")[0]["reason"]
    assert voice.events.of_type("voice_late_result_dropped") == [{"turn": 1, "input": "stt_result"}]
    assert at(voice, "voice_late_result_dropped") == [11300]
    _no_physical_act(voice)


# --- TTS, and barge-in on the speaker -------------------------------------------------------------


def _ask_turn(door, tmp_path, tts, parts=(500, 900, 6000)):
    """'tắt đèn' with someone in the room: the gate asks (RFC-0006), so the device speaks."""
    voice = voice_on(door, stt=FakeSpeechToText(["tắt đèn"]), tts=tts)
    voice.session.set_sensor("motion", True)
    asyncio.run(voice.play(speech_file(tmp_path, *parts)))
    return voice


def test_the_reply_plays_to_its_end_on_the_speaker(door, tmp_path):
    voice = _ask_turn(door, tmp_path, FakeTextToSpeech(ms_per_char=20))
    message, hint = voice.hal.spoken
    reply_ms = (len(message) + len(hint)) * 20
    start = at(voice, "tts_stream_start")[0]
    (end,) = voice.events.of_type("tts_stream_end")
    assert end["reason"] == "done" and end["duration_ms"] == reply_ms
    assert end["sha256"].startswith("sha256:")
    assert at(voice, "tts_stream_end") == [start + reply_ms]
    assert ("SPEAKING", "LISTENING", "ask_asked", 2) in states(voice)  # T11: the floor stays open
    (playback,) = voice.hal.speaker().playbacks
    assert playback.stopped_at_ms is None and len(playback.played) == reply_ms * 32


def test_tts_is_resampled_to_the_boards_speaker():
    class Wide:
        def synthesize(self, text):
            return Speech(tone(300, 24000) * 2, 24000, channels=1)

    assert len(VoiceSession._for_speaker(Wide().synthesize("x"), 16000)) == 600 * 32


def test_tts_unavailable_ends_the_stream_with_error_and_the_words_stay_shown(door, tmp_path):
    voice = _ask_turn(door, tmp_path, FakeTextToSpeech(fail=True))
    assert voice.events.of_type("tts_unavailable")
    (end,) = voice.events.of_type("tts_stream_end")
    assert (end["reason"], end["duration_ms"]) == ("error", 0)
    assert voice.events.of_type("tts_stream_start")[0]["text"] == voice.hal.spoken[0]
    assert ("SPEAKING", "LISTENING", "ask_asked", 2) in states(voice)  # error ends as done does
    assert voice.hal.speaker().playbacks == []


def test_barge_in_stops_the_speaker(door, tmp_path):
    # Reply starts at 2400 (turn end 2300 + STT 100) and would last 60 ms/char; the person
    # speaks again from 3000, confirmed at 3060: the speaker stops there, not at the end.
    voice = _ask_turn(
        door, tmp_path, FakeTextToSpeech(ms_per_char=60), parts=(500, 900, 1600, 800, 3000)
    )
    (cut,) = voice.events.of_type("tts_stream_end")
    assert cut == {"duration_ms": 660, "reason": "barge_in"}
    assert at(voice, "tts_stream_end") == [3060]
    (playback, *_) = voice.hal.speaker().playbacks
    assert playback.stopped_at_ms == 3060 and len(playback.played) == 660 * 32
    assert len(playback.pcm) > len(playback.played)  # the rest never reached the speaker
    # The question stays open (§5.4): barge-in does not spend it.
    assert voice.session.pending_confirmation() is not None


def test_barge_in_during_tts_still_cancels_the_pending_command(door, tmp_path):
    # V1 over audio: System 2 schedules the unlock 2 s out and speaks; the person talks
    # over the reply — the pending pulse is cancelled, its token closed, the speaker cut.
    voice = voice_on(
        door,
        stt=FakeSpeechToText(["làm ơn mở giúp cái cửa sau hai giây", ""]),
        tts=FakeTextToSpeech(ms_per_char=60),
        system_two=True,
    )

    async def run():
        source = speech_file(tmp_path, 500, 900, 1400, 600, 2000)
        for frame in source.frames():
            await voice.advance(frame.end_ms)
            if frame.end_ms == 2700:
                await voice.feed(
                    "system_two_reply",
                    {
                        "turn": 1,
                        "text": "Cửa sẽ mở sau hai giây.",
                        "tool_calls": [{"name": "open_door_later", "arguments": {}}],
                    },
                )
            await voice.feed_audio(frame)
        await voice.settle(voice.clock.now + 60_000)

    asyncio.run(run())
    kinds = [e["type"] for e in voice.events.events]
    abort = kinds.index("actuator_aborted")
    assert kinds[abort + 1] == "tts_stream_end"  # §5.2: step 1 before step 3
    assert voice.events.of_type("actuator_aborted") == [
        {"pin": "door_lock", "reason": "ACTUATOR_ABORTED_BY_BARGE_IN"}
    ]
    assert voice.hal.pin("door_lock").never_pulsed()  # its time (4700) came and went
    (playback,) = voice.hal.speaker().playbacks
    assert playback.stopped_at_ms == 2860  # speech again at 2800, confirmed 60 ms later
    assert "actuator_command" not in kinds


# --- the trace -----------------------------------------------------------------------------------


def test_an_anonymised_voice_trace_carries_no_words(door, tmp_path):
    voice = voice_on(
        door, stt=FakeSpeechToText(["tắt đèn"]), tts=FakeTextToSpeech(), anonymize=True
    )
    voice.session.set_sensor("motion", True)
    asyncio.run(voice.play(speech_file(tmp_path, 500, 900, 4000)))
    trace = voice.session.trace()  # validated against trace.v1
    for event in trace["events"]:
        for key in ("text", "utterance", "transcript"):
            if isinstance(event["data"].get(key), str):
                assert event["data"][key].startswith("sha256:"), event
    # Nothing the person said or heard, anywhere — but the gate's own question, which is
    # the agent's text (`tool_confirm_requested.message`), not theirs.
    (message,) = [
        e["data"]["message"] for e in trace["events"] if e["type"] == "tool_confirm_requested"
    ]
    dumped = json.dumps(trace, ensure_ascii=False).replace(message, "")
    for words in ["tắt đèn", *voice.hal.spoken]:
        assert words not in dumped
    (heard,) = [e for e in trace["events"] if e["type"] == "stt_result"]
    assert heard["offset_ms"] == 2400 and heard["data"]["turn"] == 1  # virtual time, kept
    assert voice.hal.pin("porch_light").never_pulsed()  # the gate asked; no one said "có"


def test_an_anonymised_failure_keeps_no_words_either(door, tmp_path):
    voice = voice_on(
        door, stt=FakeSpeechToText([], fail=True), tts=FakeTextToSpeech(), anonymize=True
    )
    asyncio.run(voice.play(speech_file(tmp_path, 500, 900, 3000)))
    dumped = json.dumps(voice.session.trace(), ensure_ascii=False)
    assert voice.hal.spoken[0] not in dumped and "stt_unavailable" in dumped


def test_a_voice_file_run_is_deterministic(door, tmp_path):
    def once():
        voice = voice_on(door, stt=FakeSpeechToText(["mở cửa"]), tts=FakeTextToSpeech())
        asyncio.run(voice.play(speech_file(tmp_path, 500, 900, 3000)))
        return [(e["offset_ms"], e["type"], e["data"]) for e in voice.events.events]

    assert once() == once()


def test_a_frame_is_a_frame():
    frame = AudioFrame(silence(20), 40, 20, RATE)
    assert frame.end_ms == 60
