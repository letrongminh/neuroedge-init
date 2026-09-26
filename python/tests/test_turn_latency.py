"""
TSK-I4-03 — stage latency and the System 1 / System 2 ratio in the trace
(FR-ACE-06, FR-TEL-03, NFR-OBS-02). Event shapes: docs/spec/tool_calling.md §7.1.

Time is a virtual clock that moves only where a test moves it, so every latency
asserted here is exact and no answer depends on the wall clock.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.engine.latency import (
    PATHS,
    SUMMARY_EVENT,
    TURN_EVENT,
    TurnMeter,
    turn_path,
    turn_summary,
)
from neuroedge.engine.trace_sink import EventLog
from neuroedge.models import SystemTwo
from neuroedge.perception.voice_fsm import VoiceParams
from neuroedge.perception.voice_session import VirtualClock, VoiceSession
from neuroedge.sim import SimSession
from neuroedge.testing import TracePlayer, assert_matches_golden
from neuroedge.testing.recorder import TraceRecorder
from neuroedge.trace import load_trace, validate_trace

runner = CliRunner()


@pytest.fixture(scope="module")
def villa(root):
    return root / "fixtures" / "agents" / "villa-concierge" / "agent.toml"


@pytest.fixture(scope="module")
def home(root):
    return root / "fixtures" / "agents" / "home-voice" / "agent.toml"


def turns(trace_or_session):
    events = trace_or_session.events.events if hasattr(trace_or_session, "events") else None
    events = events if events is not None else trace_or_session["events"]
    return [e["data"] for e in events if e["type"] == TURN_EVENT]


def spend(clock: VirtualClock, ms: float, fn):
    """`fn`, taking `ms` of virtual time before it runs."""

    def wrapped(*args, **kwargs):
        clock.now += ms
        return fn(*args, **kwargs)

    return wrapped


def spend_async(clock: VirtualClock, ms: float, fn):
    async def wrapped(*args, **kwargs):
        clock.now += ms
        return await fn(*args, **kwargs)

    return wrapped


def model(clock: VirtualClock, ms: float, answer="Xin chào, mình giúp gì được?"):
    """A System 2 provider that takes `ms` to answer (or to fail, for an exception)."""

    def provider(task, name, state):
        clock.now += ms
        if isinstance(answer, Exception):
            raise answer
        return answer

    return provider


# --- the meter ---------------------------------------------------------------------------


def test_stages_add_up_to_the_turn_and_other_is_the_rest():
    clock = VirtualClock(100.0)
    meter = TurnMeter(clock)
    with meter.stage("perception"):
        clock.now += 2
    with meter.stage("gate"):
        clock.now += 3
    clock.now += 4  # speech, plumbing
    with meter.stage("gate"):  # a second gate in the same turn is summed
        clock.now += 1
    data = meter.event_data(1, "system_1", "command")
    assert data == {
        "turn": 1,
        "path": "system_1",
        "stages_ms": {"perception": 2, "system_two": 0, "gate": 4, "action": 0, "other": 4},
        "total_ms": 10,
        "reply_source": "command",
    }


def test_a_nested_stage_is_not_counted_twice():
    clock = VirtualClock()
    meter = TurnMeter(clock)
    with meter.stage("action"):
        clock.now += 1
        with meter.stage("gate"):  # an action body that calls c.do() again
            clock.now += 5
    stages = meter.event_data(1, "system_1", None)["stages_ms"]
    assert (stages["action"], stages["gate"], stages["other"]) == (6, 0, 0)


def test_a_stage_that_raises_still_counts_and_closes():
    clock = VirtualClock()
    meter = TurnMeter(clock)
    with pytest.raises(RuntimeError), meter.stage("system_two"):
        clock.now += 7
        raise RuntimeError("provider down")
    with meter.stage("gate"):
        clock.now += 1
    assert meter.event_data(1, "fallback", None)["stages_ms"]["system_two"] == 7
    assert meter.event_data(1, "fallback", None)["stages_ms"]["gate"] == 1


def test_a_clock_that_raises_leaves_no_stage_open():
    ticks = iter([0.0, 5.0])

    def clock():
        value = next(ticks, None)
        if value is None:
            raise RuntimeError("clock gone")
        return value

    meter = TurnMeter(clock)
    with pytest.raises(RuntimeError, match="clock gone"), meter.stage("gate"):
        pass  # entering reads 5.0; leaving raises
    with pytest.raises(RuntimeError, match="clock gone"), meter.stage("gate"):
        pass  # entering raises before the stage opens
    assert meter._open is None


def test_times_are_never_negative():
    clock = VirtualClock(50.0)
    meter = TurnMeter(clock, started_ms=80.0)  # a start in the future is clamped to now
    meter.add("system_two", -5)
    data = meter.event_data(1, "none", None)
    assert data["total_ms"] == 0 and all(v >= 0 for v in data["stages_ms"].values())


def test_an_unknown_stage_is_refused():
    meter = TurnMeter(VirtualClock())
    with pytest.raises(ValueError, match="unknown stage"), meter.stage("thinking"):
        pass
    with pytest.raises(ValueError, match="unknown stage"):
        meter.add("thinking", 1)


@pytest.mark.parametrize(
    "reply_source,system_two,local,path",
    [
        ("command", None, True, "system_1"),
        (None, None, True, "system_1"),  # a recognised command that ran its tool
        (None, None, False, "none"),  # nothing recognised, no System 2
        ("confirmed", None, False, "none"),  # a person pressed a button
        ("system_two", True, False, "system_2"),
        ("knowledge_rag", True, True, "system_2"),
        (None, True, False, "system_2"),  # System 2 answered with nothing
        ("knowledge_local", False, True, "fallback"),
        ("offline_help", True, False, "fallback"),  # a later round failed: fallback
        ("gate_ask", False, False, "fallback"),
        ("offline", None, False, "none"),  # no System 2 to ask: nothing served the turn
        ("knowledge_local", None, True, "system_1"),  # no System 2: the device answered
    ],
)
def test_the_path_of_a_turn(reply_source, system_two, local, path):
    assert turn_path(reply_source, system_two=system_two, served_locally=local) == path


# --- a sim turn ----------------------------------------------------------------------------


def test_a_sim_turn_records_its_stages_after_its_decisions(villa):
    clock = VirtualClock()
    session = SimSession.load(villa, clock=clock)
    hal, engine = session.hal, session.conversation.engine
    hal.type_text = spend(clock, 2, hal.type_text)  # perception
    engine.evaluate = spend_async(clock, 3, engine.evaluate)  # gate
    hal.digital_out = spend(clock, 5, hal.digital_out)  # inside the @action body
    turn = asyncio.run(session.handle("mở cửa phòng 101"))
    assert turn.allowed

    events = session.events.events
    kinds = [e["type"] for e in events]
    assert kinds.count(TURN_EVENT) == 1
    at = kinds.index(TURN_EVENT)
    assert at == len(kinds) - 1, "the turn's timing comes after everything the turn did"
    assert kinds.index("gate_evaluation_result") < at and kinds.index("actuator_command") < at
    offsets = [e["offset_ms"] for e in events]
    assert offsets == sorted(offsets)
    assert events[at]["data"] == {
        "turn": 1,
        "path": "system_1",
        "stages_ms": {"perception": 2, "system_two": 0, "gate": 3, "action": 5, "other": 0},
        "total_ms": 10,
    }
    assert events[at]["offset_ms"] == 10


def test_every_turn_is_numbered_and_non_negative(villa):
    session = SimSession.load(villa)  # the real clock: values vary, their shape does not
    for line in ("mở cửa phòng 101", "mở cửa phòng 202", "hát một bài"):
        asyncio.run(session.handle(line))
    timed = turns(session)
    assert [t["turn"] for t in timed] == [1, 2, 3]
    assert [t["path"] for t in timed] == ["system_1", "system_1", "none"]
    for data in timed:
        stages = data["stages_ms"]
        assert set(stages) == {"perception", "system_two", "gate", "action", "other"}
        assert all(value >= 0 for value in stages.values())
        assert sum(stages.values()) == pytest.approx(data["total_ms"], abs=0.01)


# --- the System 1 / System 2 ratio -----------------------------------------------------


def test_the_ratio_over_a_mix_of_turns(villa, home):
    clock = VirtualClock()
    session = SimSession.load(villa, clock=clock)
    slow = {
        "up": SystemTwo("up", provider=model(clock, 40), events=session.events),
        "down": SystemTwo(
            "down", provider=model(clock, 25, ConnectionError("no route")), events=session.events
        ),
        "none": SystemTwo("sim", events=session.events),  # no provider: a grammar-only device
    }
    script = [
        ("mở cửa phòng 101", "none", "system_1"),
        ("chào bạn", "up", "system_2"),
        ("mở cửa phòng 202", "up", "system_1"),  # a recognised command never asks System 2
        ("kể chuyện cười đi", "down", "fallback"),
        ("hát một bài", "none", "none"),
        ("chào buổi sáng", "up", "system_2"),
    ]
    for line, which, _ in script:
        session.slow = slow[which]
        asyncio.run(session.handle(line))
    timed = turns(session)
    assert [t["path"] for t in timed] == [path for *_, path in script]
    assert [t["stages_ms"]["system_two"] for t in timed] == [0, 40, 0, 25, 0, 40]
    assert timed[3]["reply_source"] == "offline_help"

    trace = session.trace()
    summary = trace["events"][-1]
    assert summary["type"] == SUMMARY_EVENT
    assert summary["offset_ms"] >= trace["events"][-2]["offset_ms"]
    data = summary["data"]
    assert data["turns"] == 6
    assert data["paths"] == {"system_1": 2, "system_2": 2, "fallback": 1, "none": 1}
    assert data["shares"] == {
        "system_1": 0.3333,
        "system_2": 0.3333,
        "fallback": 0.1667,
        "none": 0.1667,
    }
    assert data["stages_ms"]["system_two"] == {"sum": 105, "max": 40}
    assert list(data["paths"]) == list(PATHS)


def test_knowledge_answered_by_system_two_or_locally(home):
    clock = VirtualClock()
    session = SimSession.load(home, clock=clock)
    session.slow = SystemTwo(
        "up", provider=model(clock, 12, "Wifi là NhaMinh."), events=session.events
    )
    asyncio.run(session.handle("wifi nhà mình là gì"))
    session.slow = SystemTwo("sim", events=session.events)  # no provider
    asyncio.run(session.handle("wifi nhà mình là gì"))
    assert [(t["path"], t["reply_source"]) for t in turns(session)] == [
        ("system_2", "knowledge_rag"),
        ("fallback", "knowledge_local"),
    ]


def test_a_spoken_yes_is_system_1_and_a_button_is_nobody(home):
    session = SimSession.load(home)
    session.set_sensor("motion", True)
    for line in ("bật đèn", "tắt đèn", "có", "tắt đèn"):
        asyncio.run(session.handle(line))
    asyncio.run(session.confirm(source="ui"))
    assert [(t["path"], t.get("reply_source")) for t in turns(session)] == [
        ("system_1", None),
        ("system_1", "gate_ask"),
        ("system_1", "confirmed"),
        ("system_1", "gate_ask"),
        ("none", "confirmed"),
    ]


def test_a_declined_question_is_nobody(home):
    session = SimSession.load(home)
    session.set_sensor("motion", True)
    for line in ("bật đèn", "tắt đèn"):
        asyncio.run(session.handle(line))
    asyncio.run(session.decline(source="ui"))
    assert [t["path"] for t in turns(session)] == ["system_1", "system_1", "none"]


def test_a_turn_that_raises_writes_no_timing_and_the_next_turn_is_timed(villa):
    session = SimSession.load(villa)
    engine = session.conversation.engine
    real = engine.evaluate

    async def broken(*args, **kwargs):
        raise RuntimeError("engine fault")

    engine.evaluate = broken
    with pytest.raises(RuntimeError, match="engine fault"):
        asyncio.run(session.handle("mở cửa phòng 101"))
    # The meter is let go, or every later turn would look nested and write nothing.
    assert session.conversation.meter is None
    assert turns(session) == []
    engine.evaluate = real
    asyncio.run(session.handle("mở cửa phòng 101"))
    assert [t["turn"] for t in turns(session)] == [1]


class Billed:
    """A System 2 provider that reports tokens and cost, as the real ones do."""

    name, model = "fake", "fake-1"

    def __init__(self, usage):
        self.last_usage = usage

    def __call__(self, task, name, state):
        return "Chào bạn."


def test_the_cost_of_each_turn_and_of_the_session(villa):
    session = SimSession.load(villa)
    usage = {"prompt_tokens": 120, "completion_tokens": 8, "cost_usd": 0.0004}
    session.slow = SystemTwo("x", provider=Billed(usage), events=session.events)
    for line in ("chào bạn", "mở cửa phòng 101", "chào buổi sáng"):
        asyncio.run(session.handle(line))
    timed = turns(session)
    assert [t.get("usage") for t in timed] == [usage, None, usage]
    summary = session.trace()["events"][-1]["data"]
    assert summary["usage"] == {"prompt_tokens": 240, "completion_tokens": 16, "cost_usd": 0.0008}


def test_a_hand_edited_turn_does_not_break_the_summary():
    events = [
        {"type": TURN_EVENT, "data": {"path": "system_1", "stages_ms": "fast", "total_ms": "?"}},
        {"type": TURN_EVENT, "data": {"path": "martian", "stages_ms": {"gate": True}}},
        {"type": TURN_EVENT, "data": "not an object"},
        {"type": TURN_EVENT, "data": {"path": "system_2", "usage": {"cost_usd": "free"}}},
    ]
    summary = turn_summary(events)
    assert summary["turns"] == 3
    assert summary["paths"]["system_1"] == 1 and summary["paths"]["martian"] == 1
    assert summary["stages_ms"]["gate"] == {"sum": 0, "max": 0}
    assert "usage" not in summary


def test_a_trace_without_turns_has_no_summary(root):
    trace = load_trace(root / "fixtures" / "traces" / "happy-path.json")
    assert turn_summary(trace["events"]) is None
    # A log with events but no turn (a replay, a device session) gets no summary.
    log = EventLog(clock=lambda: 0.0)
    log.emit("gate_evaluation_result", {"verdict": "ALLOW"})
    assert [e["type"] for e in log.to_trace()["events"]] == ["gate_evaluation_result"]


def test_an_imported_summary_is_replaced_not_repeated():
    log = EventLog(clock=lambda: 0.0)
    log.emit(TURN_EVENT, {"turn": 1, "path": "system_1", "stages_ms": {}, "total_ms": 1})
    log.emit(SUMMARY_EVENT, {"turns": 99})
    types = [e["type"] for e in log.to_trace()["events"]]
    assert types == [TURN_EVENT, SUMMARY_EVENT]
    assert log.to_trace()["events"][-1]["data"]["turns"] == 1


def test_an_export_carries_exactly_one_summary(villa):
    session = SimSession.load(villa)
    asyncio.run(session.handle("mở cửa phòng 101"))
    first = session.trace()
    asyncio.run(session.handle("mở cửa phòng 202"))
    second = session.trace()
    for trace, count in ((first, 1), (second, 2)):
        kinds = [e["type"] for e in trace["events"]]
        assert kinds.count(SUMMARY_EVENT) == 1 and kinds[-1] == SUMMARY_EVENT
        assert trace["events"][-1]["data"]["turns"] == count
    assert SUMMARY_EVENT not in {e["type"] for e in session.events.events}  # never in the log


# --- the voice driver --------------------------------------------------------------------

PARAMS = VoiceParams(think_timeout_ms=5000)


def HEARD(text):  # noqa: N802 — reads as a constant script
    """One utterance, timed as the voice corpus times it (fixtures/compliance/voice/)."""
    return [
        (300, "audio_in_vad_start", {"energy_db": -18.0}),
        (1500, "audio_in_vad_end", {}),
        (2300, "stt_result", {"turn": 1, "text": text}),
    ]


async def play(voice, inputs):
    for offset, kind, data in inputs:
        await voice.advance(offset)
        await voice.feed(kind, data)


def test_the_voice_wait_for_system_two_is_the_system_two_stage(root):
    agent = root / "fixtures" / "agents" / "voice-door" / "agent.toml"
    clock = VirtualClock()
    voice = VoiceSession.load(agent, clock=clock, system_two=True, params=PARAMS)

    async def run():
        await play(voice, [(0, "wake_word_detected", {"word": "hey_neuro", "score": 0.93})])
        await play(voice, HEARD("chào bạn nhé"))
        await play(voice, [(3500, "system_two_reply", {"turn": 1, "text": "Chào bạn!"})])

    asyncio.run(run())
    (timed,) = turns(voice.session)
    assert timed["path"] == "system_2"
    assert timed["stages_ms"]["system_two"] == 1200  # stt_result at 2300 → reply at 3500
    assert timed["total_ms"] == 1200


def test_a_voice_turn_system_two_never_answers_is_a_fallback(root):
    agent = root / "fixtures" / "agents" / "voice-door" / "agent.toml"
    clock = VirtualClock()
    voice = VoiceSession.load(agent, clock=clock, system_two=True, params=PARAMS)

    async def run():
        await play(voice, [(0, "wake_word_detected", {"word": "hey_neuro", "score": 0.93})])
        await play(voice, HEARD("kể chuyện đi"))
        await voice.advance(2300 + 5000, inclusive=True)  # past the think timeout

    asyncio.run(run())
    (timed,) = turns(voice.session)
    assert (timed["path"], timed["reply_source"]) == ("fallback", "offline_help")
    # THINKING began at 2200 (vad_end 1500 + 700 ms of silence), so the timeout fires
    # at 7200; the transcript came at 2300: 4900 ms waiting for System 2.
    assert timed["stages_ms"]["system_two"] == 4900
    assert timed["total_ms"] == 4900
    assert voice.hal.spoken[-1] == voice.session.offline_help()


# --- the trace file ------------------------------------------------------------------------


def test_a_recorded_trace_with_timing_validates_and_replays(villa, tmp_path):
    clock = VirtualClock()
    recorder = TraceRecorder(clock=clock)
    session = SimSession.load(villa, events=recorder, clock=clock)
    for line in ("mở cửa phòng 101", "mở cửa phòng 202", "hát một bài"):
        asyncio.run(session.handle(line))
    path = tmp_path / "timed.json"
    session.write_trace(path)
    trace = load_trace(path)  # validates against schemas/trace.v1.json, unchanged
    validate_trace(recorder.to_trace())
    kinds = [e["type"] for e in trace["events"]]
    assert kinds.count(TURN_EVENT) == 3 and kinds[-1] == SUMMARY_EVENT

    result = asyncio.run(TracePlayer(path, agent=villa).replay())
    assert result.verdicts == ["ALLOW", "BLOCK"]
    assert_matches_golden(result, trace)

    cli = runner.invoke(app, ["replay", str(path), "--agent", str(villa)])
    assert cli.exit_code == 0, cli.output
    cli = runner.invoke(app, ["trace", "validate", str(path)])
    assert cli.exit_code == 0, cli.output


def test_trace_show_prints_the_ratio_and_the_stages(villa, tmp_path):
    session = SimSession.load(villa)
    asyncio.run(session.handle("mở cửa phòng 101"))
    asyncio.run(session.handle("hát một bài"))
    path = tmp_path / "s.json"
    session.write_trace(path)
    result = runner.invoke(app, ["trace", "show", str(path)])
    assert result.exit_code == 0, result.output
    assert "2 turn(s): system_1 1 (50%) · system_2 0 (0%) · fallback 0 (0%) · none 1 (50%)" in (
        result.output
    )
    assert "stage ms (sum/max): perception" in result.output


def test_trace_show_of_an_old_trace_prints_no_ratio(root):
    result = runner.invoke(
        app, ["trace", "show", str(root / "fixtures" / "traces" / "happy-path.json")]
    )
    assert result.exit_code == 0, result.output
    assert "turn(s):" not in result.output


def test_anonymised_timing_carries_no_text(villa, tmp_path):
    recorder = TraceRecorder(anonymize=True)
    session = SimSession.load(villa, events=recorder)
    lines = ("mở cửa phòng 101", "hát một bài")
    for line in lines:
        asyncio.run(session.handle(line))
    path = tmp_path / "anon.json"
    session.write_trace(path)
    text = path.read_text("utf-8")
    for line in lines:
        assert line not in text
    for event in load_trace(path)["events"]:
        if event["type"] in (TURN_EVENT, SUMMARY_EVENT):
            assert not {"text", "utterance", "transcript"} & set(event["data"])
            dumped = json.dumps(event, ensure_ascii=False)
            assert "sha256:" not in dumped and all(line not in dumped for line in lines)
