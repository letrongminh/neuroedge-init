"""
TSK-S3-11 — the conversation state machine and scheduled commands, below the
corpus (docs/spec/voice_fsm.md). What the corpus proves end to end lives in
test_voice_corpus.py; these pin down the parts it cannot reach on its own.
"""

from __future__ import annotations

import asyncio

import pytest

from neuroedge import action
from neuroedge.actions import Conversation
from neuroedge.engine import ActionContractEngine, EventLog, resolve_gate_file
from neuroedge.errors import ActionContractViolation, BoardCapabilityError
from neuroedge.hal import digital
from neuroedge.hal.linux import LinuxHAL
from neuroedge.hal.sim import PendingCommand, SimHAL
from neuroedge.paths import fixtures_dir
from neuroedge.perception import VirtualClock, VoiceParams, VoiceState, VoiceStateMachine
from neuroedge.testing import voice_corpus as vc

from .test_hal_linux import LINES, FakeGpiod

GATE = fixtures_dir() / "agents" / "voice-door" / "gates" / "unlock_door@1.0.0.yaml"


@action(name="fsm_unlock_later", requires="digital.out:door_lock", gate="unlock_door")
def _unlock_later() -> None:
    digital.out("door_lock").pulse(seconds=30, after_ms=2000)


def _machine(**params):
    clock = VirtualClock()
    events = EventLog(clock)
    return clock, events, VoiceStateMachine(VoiceParams(**params), events=events)


def _states(events):
    return [
        (e["from"], e["to"], e["trigger"], e["turn"]) for e in events.of_type("voice_state_changed")
    ]


def test_defaults_are_the_suggested_values_of_section_6():
    params = VoiceParams()
    assert (params.end_of_turn_silence_ms, params.listen_timeout_ms, params.max_reprompts) == (
        700,
        8000,
        1,
    )
    assert params.vad_activation is False


def test_unknown_parameters_are_refused():
    with pytest.raises(ValueError, match="unknown voice parameters"):
        VoiceParams.from_mapping({"silence_ms": 500})


def test_vad_opens_a_turn_only_when_vad_activation_is_on():
    _, events, fsm = _machine()
    fsm.vad_start()
    assert fsm.state is VoiceState.IDLE and _states(events) == []
    _, events, fsm = _machine(vad_activation=True)
    fsm.vad_start()
    assert _states(events) == [("IDLE", "LISTENING", "speech_start", 1)]


def test_listen_timeout_runs_only_until_someone_speaks():
    clock, events, fsm = _machine(listen_timeout_ms=1000)
    fsm.wake_word()
    clock.now = 999
    assert fsm.fire_due() == []
    fsm.vad_start()  # speech: the listen timeout no longer applies
    clock.now = 5000
    fsm.fire_due()
    assert fsm.state is VoiceState.LISTENING


def test_events_outside_the_table_change_nothing():
    _, events, fsm = _machine()
    fsm.vad_end()
    fsm.reply_ended()
    fsm.reply_started(ask=False)
    fsm.reply_empty()
    assert fsm.transcript(1, "mở cửa") is False
    assert fsm.state is VoiceState.IDLE and _states(events) == []


def test_the_end_of_a_turn_tells_the_driver_to_send_its_audio_to_stt():
    # T04's effect is "send the audio to STT" (§4): `fire_due` says so (TSK-S3-13).
    clock, _, fsm = _machine(think_timeout_ms=1000)
    fsm.wake_word()
    fsm.vad_start()
    fsm.vad_end()
    clock.now = 700
    assert fsm.fire_due() == ["turn_end"] and fsm.state is VoiceState.THINKING
    clock.now = 1700
    assert fsm.fire_due() == ["think_timeout"]


def _to_speaking(fsm, clock):
    fsm.wake_word()
    fsm.vad_start()
    fsm.vad_end()
    clock.now = 700
    fsm.fire_due()
    assert fsm.transcript(1, "x")
    fsm.reply_started(ask=False)


def test_barge_in_cancels_only_undelivered_commands_and_closes_their_tokens():
    clock = VirtualClock()
    events = EventLog(clock)
    delivered = PendingCommand("porch_light", "on", 0, events, token="t-delivered")
    waiting = PendingCommand(
        "door_lock", "pulse", 30_000, events, delivered=False, deliver_at_ms=9000, token="t-wait"
    )
    closed: list[str] = []
    fsm = VoiceStateMachine(
        events=events, pending_commands=lambda: [delivered, waiting], close_token=closed.append
    )
    _to_speaking(fsm, clock)
    clock.now = 1200
    fsm.vad_start()
    assert not delivered.cancelled  # §5.3: delivered commands run to the end
    assert waiting.cancelled and closed == ["t-wait"] and fsm.aborted == [waiting]
    kinds = [e["type"] for e in events.events]
    # §5.2 order: abort, then the TTS stop, then the state changes.
    assert kinds == [
        *kinds[: kinds.index("actuator_aborted")],
        "actuator_aborted",
        "tts_stream_end",
        "voice_state_changed",
        "voice_state_changed",
    ]
    assert events.of_type("tts_stream_end") == [{"duration_ms": 500, "reason": "barge_in"}]
    assert fsm.state is VoiceState.LISTENING and fsm.turn == 2
    assert not fsm.accepts(1)


def test_reprompts_stop_after_max_and_restart_after_a_transcript():
    clock, events, fsm = _machine(vad_activation=True, max_reprompts=2)
    for text in ["", "", "", "mở cửa", ""]:
        fsm.vad_start()
        fsm.vad_end()
        clock.now += 700
        fsm.fire_due()
        if fsm.transcript(fsm.turn, text):
            fsm.reply_empty()
    assert events.of_type("voice_reprompt") == [
        {"turn": 1, "count": 1},
        {"turn": 2, "count": 2},
        {"turn": 5, "count": 1},
    ]


def test_a_scheduled_command_needs_a_driver():
    events = EventLog()
    hal = SimHAL(events=events, authorize=lambda *_: None)
    with pytest.raises(BoardCapabilityError, match="driver"):
        hal.digital_out("door_lock", "pulse", 1000, signature="proof", delay_ms=500)
    assert hal.pin("door_lock").never_pulsed()
    assert hal.pending_commands() == []


def test_a_scheduled_command_moves_the_pin_only_when_due():
    clock = VirtualClock()
    events = EventLog(clock)
    hal = SimHAL(events=events, authorize=lambda *_: None)
    hal.enable_scheduling(clock)
    command = hal.digital_out("door_lock", "pulse", 1000, signature="proof", delay_ms=500)
    assert not command.delivered and hal.pending_commands() == [command]
    clock.now = 499
    assert hal.run_due() == [] and hal.pin("door_lock").never_pulsed()
    clock.now = 500
    assert hal.run_due() == [command] and hal.pin("door_lock").pulsed_once(1000)
    assert events.of_type("actuator_command") == [
        {"pin": "door_lock", "operation": "pulse", "duration_ms": 1000}
    ]


async def test_linux_refuses_a_scheduled_command_instead_of_delivering_it_now(tmp_path):
    path = tmp_path / "gpiochip0"
    path.write_text("")
    fake = FakeGpiod({str(path): LINES})
    events = EventLog()
    hal = LinuxHAL(chip_glob=str(tmp_path / "gpiochip*"), gpiod=fake, events=events)
    engine = ActionContractEngine(events=events)
    engine.register("unlock_door", resolve_gate_file(GATE))
    conversation = Conversation(engine=engine, hal=hal, facts={"guest_authenticated": True})
    with pytest.raises(BoardCapabilityError, match="cannot schedule"):
        await conversation.do(_unlock_later)
    assert fake.history == [] and events.of_type("actuator_command") == []


def test_the_same_case_gives_the_same_events_twice():
    case = vc.load_case(vc.corpus_dir() / "v1_barge_in_cancels_scheduled_unlock.json")
    first = vc.observe(asyncio.run(vc.execute(case)).events.events)
    second = vc.observe(asyncio.run(vc.execute(case)).events.events)
    assert first == second


def test_barge_in_never_cuts_a_pulse_linux_has_delivered(tmp_path):
    """§5.3 on `linux`: `PendingCommand.cancel()` there drops the line — for SIGTERM, not barge-in."""
    path = tmp_path / "gpiochip0"
    path.write_text("")
    fake = FakeGpiod({str(path): LINES})
    clock = VirtualClock()
    events = EventLog(clock)
    hal = LinuxHAL(
        chip_glob=str(tmp_path / "gpiochip*"), gpiod=fake, events=events, authorize=lambda *_: None
    )
    running = hal.digital_out("door_lock", "pulse", 30_000, signature="proof")
    fsm = VoiceStateMachine(events=events, pending_commands=lambda: [running])
    _to_speaking(fsm, clock)
    fsm.vad_start()
    assert not running.cancelled and hal.line_value("door_lock")
    assert events.of_type("actuator_aborted") == []
    hal.close()


@action(name="fsm_unlock_half_ms", requires="digital.out:door_lock", gate="unlock_door")
def _unlock_half_ms() -> None:
    digital.out("door_lock").pulse(seconds=1, after_ms=0.5)


@action(name="fsm_unlock_in_the_past", requires="digital.out:door_lock", gate="unlock_door")
def _unlock_in_the_past() -> None:
    digital.out("door_lock").pulse(seconds=1, after_ms=-5)


def _scheduling_conversation():
    clock = VirtualClock()
    events = EventLog(clock)
    hal = SimHAL(events=events)
    hal.enable_scheduling(clock)
    engine = ActionContractEngine(events=events, clock=clock)
    engine.register("unlock_door", resolve_gate_file(GATE))
    conversation = Conversation(engine=engine, hal=hal, facts={"guest_authenticated": True})
    return clock, hal, conversation


async def test_a_sub_millisecond_delay_is_scheduled_never_delivered_at_once():
    clock, hal, conversation = _scheduling_conversation()
    await conversation.do(_unlock_half_ms)
    (command,) = hal.pending_commands()
    assert command.deliver_at_ms == clock.now + 1 and hal.pin("door_lock").never_pulsed()


async def test_a_negative_delay_is_refused_before_anything_is_scheduled():
    _, hal, conversation = _scheduling_conversation()
    with pytest.raises(BoardCapabilityError, match="negative"):
        await conversation.do(_unlock_in_the_past)
    assert hal.pending_commands() == [] and hal.pin("door_lock").never_pulsed()


@action(name="fsm_unlock_past_ttl", requires="digital.out:door_lock", gate="unlock_door")
def _unlock_past_ttl() -> None:
    digital.out("door_lock").pulse(seconds=1, after_ms=2101)  # TTL of unlock_door: 2100 ms


@action(
    name="fsm_unlock_then_fail",
    requires=["digital.out:door_lock", "digital.out:porch_light"],
    gate="unlock_door",
)
def _unlock_then_fail() -> None:
    digital.out("door_lock").pulse(seconds=1, after_ms=500)
    raise RuntimeError("the second half of the action failed")


async def test_a_scheduled_command_past_the_verdict_ttl_is_refused():
    _, hal, conversation = _scheduling_conversation()
    with pytest.raises(ActionContractViolation, match="past its TTL"):
        await conversation.do(_unlock_past_ttl)
    assert hal.pending_commands() == [] and hal.pin("door_lock").never_pulsed()


async def test_an_action_that_raises_after_scheduling_never_moves_the_pin():
    clock, hal, conversation = _scheduling_conversation()
    with pytest.raises(RuntimeError, match="second half"):
        await conversation.do(_unlock_then_fail)
    assert hal.pending_commands() == []
    clock.now = 10_000
    assert hal.run_due() == [] and hal.pin("door_lock").never_pulsed()
    assert conversation.events.of_type("actuator_aborted") == [
        {"pin": "door_lock", "reason": "ACTUATOR_ABORTED_BY_ACTION_ERROR"}
    ]
