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


@pytest.mark.parametrize("answer", [None, 42, "mở\x00cửa", "m\ufffd"])
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


def test_barge_in_stops_the_speaker(door, tmp_path, monkeypatch):
    # Reply starts at 2400 (turn end 2300 + STT 100) and would last 60 ms/char; the person
    # speaks again from 3000, confirmed at 3060: the speaker stops there, not at the end.
    stops: list[float] = []
    real_stop = Speaker.stop

    def spy(self, at_ms):
        stops.append(at_ms)
        real_stop(self, at_ms)

    monkeypatch.setattr(Speaker, "stop", spy)
    voice = _ask_turn(
        door, tmp_path, FakeTextToSpeech(ms_per_char=60), parts=(500, 900, 1600, 800, 3000)
    )
    assert stops == [3060]  # barge-in goes through the speaker's one stop rule
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


# --- wave-2 review: what a provider or a file may not do to the session ------------------------

from neuroedge.hal.audio import (  # noqa: E402 — grouped with the tests that need them
    MAX_REPLY_MS,
    Playback,
    read_wav_bytes,
    to_speaker,
    wav_bytes,
)
from neuroedge.perception.providers import SpeechUnavailable  # noqa: E402
from neuroedge.perception.providers.base import clean_transcript  # noqa: E402


class Says:
    """A TTS that returns whatever Speech it is given, for every sentence."""

    def __init__(self, speech):
        self.speech = speech

    def synthesize(self, text):
        return self.speech


def test_playback_stop_is_one_rule():
    early = Playback(1000, tone(500, RATE), RATE)
    early.stop(400)  # before it starts: nothing plays
    assert early.stopped_at_ms == 1000 and early.played == b""
    mid = Playback(1000, tone(500, RATE), RATE)
    mid.stop(1200)
    mid.stop(1300)  # stopped once, stays stopped where it was
    assert mid.stopped_at_ms == 1200 and len(mid.played) == 200 * 32
    done = Playback(1000, tone(500, RATE), RATE)
    done.stop(1500)  # at or after its end: it played whole
    assert done.stopped_at_ms is None and done.played == done.pcm
    speaker = Speaker(RATE)
    first, second = speaker.play(tone(500, RATE), 0), speaker.play(tone(500, RATE), 2000)
    speaker.stop(250)
    assert (first.stopped_at_ms, second.stopped_at_ms) == (250, 2000)  # the flush empties all


def test_the_speaker_writes_exactly_wav_bytes(tmp_path):
    speaker = Speaker(RATE)
    speaker.play(tone(100, RATE), 50)
    assert speaker.write(tmp_path / "out.wav").read_bytes() == wav_bytes(speaker.render(), RATE)


# F2 — a TTS header that lies about its rate, or a reply without end


@pytest.mark.parametrize(
    "speech, fragment",
    [
        (Speech(bytes(2048), 1), "outside 8000–96000 Hz"),
        (Speech(bytes(2048), 0), "outside 8000–96000 Hz"),
        (Speech(bytes(2048), 10_000_000), "outside 8000–96000 Hz"),
        (Speech(bytes(2048), 16000, channels=6), "channels"),
        (Speech(bytes(2048), 16000, sample_width=3), "16-bit"),
        (Speech(bytes(2 * 8000 * 121), 8000), "would pass 120 s"),
    ],
)
def test_speech_the_speaker_cannot_play_is_refused_before_any_work(speech, fragment):
    import time

    started = time.perf_counter()
    with pytest.raises(SpeechUnavailable) as caught:
        VoiceSession._for_speaker(speech, RATE)
    assert fragment in caught.value.why and caught.value.role == "tts"
    assert time.perf_counter() - started < 0.2  # checked from the header, nothing converted


def test_a_tts_rate_of_1_hz_is_a_failed_reply_not_a_frozen_session(door, tmp_path):
    import time

    started = time.perf_counter()
    voice = _ask_turn(door, tmp_path, Says(Speech(bytes(2048), 1)))
    assert time.perf_counter() - started < 2
    (failed,) = voice.events.of_type("tts_unavailable")
    assert "1 Hz is outside" in failed["reason"]
    assert voice.events.of_type("tts_stream_end")[0]["reason"] == "error"
    assert voice.hal.speaker().playbacks == []


def test_the_reply_budget_is_the_whole_reply(door, tmp_path):
    # Two sentences (the gate's question and its hint) of 70 s each: the second overruns.
    voice = _ask_turn(door, tmp_path, Says(Speech(bytes(2 * 8000 * 70), 8000)))
    (failed,) = voice.events.of_type("tts_unavailable")
    assert f"would pass {MAX_REPLY_MS // 1000} s" in failed["reason"]
    assert "this sentence: 70.0 s, 50.0 s left" in failed["reason"]


def test_to_speaker_and_resample_refuse_absurd_rates():
    assert len(to_speaker(tone(100, 8000), 8000, 1, 2, to_hz=RATE)) == 100 * 32
    for bad in (0, 1, 7999, 96001, True, 16000.0):
        with pytest.raises(ValueError):
            resample(tone(20, RATE), bad, RATE)
        with pytest.raises(ValueError):
            to_speaker(tone(20, RATE), bad, 1, 2, to_hz=RATE)


@pytest.mark.parametrize("rate", [0, 1, 200_000])
def test_a_wav_answer_with_an_absurd_rate_is_not_wav(rate):
    data = bytearray(wav_bytes(tone(20, RATE), RATE))
    data[24:28] = rate.to_bytes(4, "little")
    with pytest.raises(ValueError, match="outside"):
        read_wav_bytes(bytes(data))


# F4 — what a transcript may hold


@pytest.mark.parametrize(
    "text, category",
    [
        ("mở\ud800cửa", "lone surrogate"),
        ("mở \u202ecửa", "format"),  # right-to-left override: the console lies
        ("mở cửa\U000e0069\U000e0067", "format"),  # tag characters: hidden text for a model
        ("mở \ue000", "private-use"),
        ("mở \u0378", "unassigned"),
    ],
)
def test_a_transcript_that_is_not_plain_speech_is_garbled(text, category):
    with pytest.raises(SpeechUnavailable) as caught:
        clean_transcript(text, "STT")
    assert category in caught.value.why and "U+" in caught.value.why
    assert "cửa" not in caught.value.why  # the code point is named, never the text around it


def test_joiners_stay_and_invisible_spaces_go():
    assert clean_transcript("a\u200db\u200cc", "w") == "a\u200db\u200cc"
    assert clean_transcript("\ufeffmở\u200b cửa\u00ad", "w") == "mở cửa"


def test_a_lone_surrogate_from_stt_never_reaches_the_trace(door, tmp_path):
    voice = voice_on(door, stt=FakeSpeechToText(["mở\ud800 cửa"]), anonymize=True)
    asyncio.run(voice.play(speech_file(tmp_path, 500, 900, 3000)))
    assert voice.events.of_type("stt_unavailable") and not voice.events.of_type("stt_result")
    _no_physical_act(voice)
    json.dumps(voice.session.trace(), ensure_ascii=False).encode("utf-8")  # encodes cleanly


# F5 — a WAV header checked before it is used


def _patched(path, offset, value):
    data = bytearray(path.read_bytes())
    data[offset : offset + 4] = value.to_bytes(4, "little")
    path.write_bytes(bytes(data))
    return path


def test_a_wav_with_rate_0_is_refused_not_divided_by(tmp_path):
    path = _patched(write_wav(tmp_path / "zero.wav", silence(100)), 24, 0)
    with pytest.raises(BoardCapabilityError) as caught:
        WavSource.open(path, sample_rate_hz=RATE, called_from="t")
    assert "the file is 0 Hz" in caught.value.why


def test_the_format_is_checked_before_the_length_and_before_reading(tmp_path, monkeypatch):
    path = write_wav(tmp_path / "cd.wav", bytes(4410 * 2), rate=44100)
    _patched(path, 40, 0x7FFFFFF0)  # claims hours of audio
    read = []
    monkeypatch.setattr(wave.Wave_read, "readframes", lambda self, n: read.append(n) or b"")
    with pytest.raises(BoardCapabilityError) as caught:
        WavSource.open(path, sample_rate_hz=RATE, called_from="t")
    assert "44100 Hz" in caught.value.why and read == []


def test_a_file_too_long_is_refused_before_it_is_read(tmp_path, monkeypatch):
    path = _patched(write_wav(tmp_path / "long.wav", silence(100)), 40, 0x7FFFFFF0)
    read = []
    monkeypatch.setattr(wave.Wave_read, "readframes", lambda self, n: read.append(n) or b"")
    with pytest.raises(BoardCapabilityError, match="read whole, up to 600 s"):
        WavSource.open(path, sample_rate_hz=RATE, called_from="t")
    assert read == []


# F8 — board rates and declared latencies that would break the clock


@pytest.mark.parametrize("rate", [0, 40, 1_000_000])
def test_a_board_rate_outside_the_range_is_refused(tmp_path, rate):
    good = write_wav(tmp_path / "ok.wav", silence(100))
    with pytest.raises(BoardCapabilityError, match="the board declares audio.in"):
        WavSource.open(good, sample_rate_hz=rate, called_from="t")
    with pytest.raises(BoardCapabilityError, match="the board declares audio.out"):
        Speaker(rate)
    with pytest.raises(ValueError, match="no samples"):
        list(WavSource(good, silence(100), rate).frames())


@pytest.mark.parametrize("latency", [float("inf"), float("nan"), -1.0])
def test_the_fakes_refuse_latencies_that_break_the_clock(latency):
    with pytest.raises(ValueError, match="finite"):
        FakeTextToSpeech(latency_ms=latency)
    with pytest.raises(ValueError, match="finite"):
        FakeSpeechToText(latency_ms=latency)
    with pytest.raises(ValueError, match="finite"):
        FakeTextToSpeech(ms_per_char=latency)
    with pytest.raises(ValueError, match="8000"):
        FakeTextToSpeech(sample_rate_hz=1)


@pytest.mark.parametrize("latency", [float("inf"), float("nan"), -5.0, "soon", True])
def test_a_tts_that_declares_a_broken_latency_is_a_failed_reply(door, tmp_path, latency):
    voice = _ask_turn(door, tmp_path, Says(Speech(tone(100, RATE), RATE, latency_ms=latency)))
    (failed,) = voice.events.of_type("tts_unavailable")
    assert "not a finite number" in failed["reason"]
    assert voice.events.of_type("tts_stream_end")[0]["reason"] == "error"


@pytest.mark.parametrize("latency", [float("inf"), float("nan")])
def test_an_stt_that_declares_a_broken_latency_is_a_failed_turn(door, tmp_path, latency):
    class Stt:
        def transcribe(self, clip):
            return type(FakeSpeechToText().transcribe(clip))("mở cửa", latency_ms=latency)

    voice = voice_on(door, stt=Stt())
    asyncio.run(voice.play(speech_file(tmp_path, 500, 900, 3000)))
    (failed,) = voice.events.of_type("stt_unavailable")
    assert "not a finite number" in failed["reason"]
    _no_physical_act(voice)


def test_the_fake_factories_refuse_infinite_options():
    from types import SimpleNamespace

    from neuroedge.perception.providers.fake import stt as fake_stt
    from neuroedge.perception.providers.fake import tts as fake_tts

    with pytest.raises(ValueError, match="finite"):
        fake_tts(SimpleNamespace(options={"ms_per_char": float("inf")}))
    with pytest.raises(ValueError, match="finite"):
        fake_stt(SimpleNamespace(options={"latency_ms": float("nan")}))


# F7 — a provider that never answers


class HangingAsync:
    def __init__(self, timeout_s=None):
        self.config = None if timeout_s is None else type("C", (), {"timeout_s": timeout_s})()

    async def transcribe(self, clip):
        await asyncio.Event().wait()

    async def synthesize(self, text):
        await asyncio.Event().wait()


class HangingSync:
    """Blocks its thread for 5 s — a blocking HTTP client, a deadlock."""

    def __init__(self):
        import threading

        self.release = threading.Event()

    def transcribe(self, clip):
        self.release.wait(5)
        return "mở cửa"


def test_a_hung_async_stt_is_unavailable_within_its_timeout(door, tmp_path):
    import time

    started = time.perf_counter()
    voice = voice_on(door, stt=HangingAsync(timeout_s=0.1), tts=FakeTextToSpeech())
    asyncio.run(voice.play(speech_file(tmp_path, 500, 900, 3000)))
    assert time.perf_counter() - started < 3  # 0.1 s × 1.25 + 1 s margin
    (failed,) = voice.events.of_type("stt_unavailable")
    assert "did not answer within" in failed["reason"]
    assert voice.hal.spoken == [voice.session.unheard_help()]
    _no_physical_act(voice)


def test_a_blocking_sync_stt_is_bounded_by_the_think_timeout(door, tmp_path):
    import time

    stt = HangingSync()
    params = VoiceParams(vad_activation=True, think_timeout_ms=300)
    started = time.perf_counter()
    try:
        voice = voice_on(door, stt=stt, params=params)
        asyncio.run(voice.play(speech_file(tmp_path, 500, 900, 3000)))  # returns: no join
        assert time.perf_counter() - started < 3
    finally:
        stt.release.set()
    # The bound (0.3 s of wall time) lands on the virtual clock at or just after the think
    # timeout (300 ms): either way STT failed, the offline line is said, nothing acts.
    reason = voice.events.of_type("stt_unavailable")[0]["reason"]
    assert "within 0.3 s" in reason or "before the think timeout" in reason
    assert voice.hal.spoken == [voice.session.unheard_help()]
    _no_physical_act(voice)


def test_a_hung_tts_is_a_failed_reply(door, tmp_path):
    import time

    started = time.perf_counter()
    voice = _ask_turn(door, tmp_path, HangingAsync(timeout_s=0.1))
    assert time.perf_counter() - started < 3
    (failed,) = voice.events.of_type("tts_unavailable")
    assert "TTS provider did not answer" in failed["reason"]
    assert voice.events.of_type("tts_stream_end")[0]["reason"] == "error"
