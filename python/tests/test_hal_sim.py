"""
TSK-S2-01 — HAL backend for `sim` (FR-TGT-01, FR-HAL-01).

Includes the seam test shared with TSK-S2-03: a gate ALLOW reaches the pin, a
BLOCK leaves it untouched, and a misspelled pin can never pass as untouched.
"""

from __future__ import annotations

import pytest

from neuroedge.engine import ActionContractEngine, EventLog, resolve_gate_file
from neuroedge.errors import ActionContractViolation, BoardCapabilityError
from neuroedge.hal import load_board_by_id
from neuroedge.hal.sim import ABORTED_BY_BARGE_IN, SimHAL
from neuroedge.trace import validate_trace


@pytest.fixture
def events() -> EventLog:
    return EventLog()


@pytest.fixture
def hal(events: EventLog) -> SimHAL:
    return SimHAL(events=events)


# --- The five primitives on sim-default --------------------------------------


def test_digital_out_records_the_canonical_actuator_command(hal, events):
    pending = hal.digital_out("door_lock", "pulse", 30_000, signature="proof")
    assert hal.pin("door_lock").pulsed_once(duration_ms=30_000)
    assert events.of_type("actuator_command") == [
        {"pin": "door_lock", "operation": "pulse", "duration_ms": 30_000}
    ]
    assert not pending.cancelled


def test_a_pending_command_can_be_cancelled_once(hal, events):
    pending = hal.digital_out("door_lock", "pulse", 30_000, signature="proof")
    pending.cancel()
    pending.cancel()
    assert pending.cancelled
    assert events.of_type("actuator_aborted") == [
        {"pin": "door_lock", "reason": ABORTED_BY_BARGE_IN}
    ]


def test_sensor_read_returns_the_scripted_value(hal):
    hal.set_sensor("temperature", 24.5)
    assert hal.sensor_read("temperature") == 24.5


def test_an_unscripted_sensor_raises_instead_of_inventing_a_reading(hal):
    with pytest.raises(BoardCapabilityError) as excinfo:
        hal.sensor_read("humidity", called_from="actions/climate.py:8")
    assert "actions/climate.py:8" in excinfo.value.where
    assert "set_sensor" in excinfo.value.how


def test_typed_text_is_the_default_audio_input(hal, events):
    hal.type_text("mở cửa phòng 101")
    assert hal.audio_in() == "mở cửa phòng 101"
    assert hal.audio_in() is None
    assert events.of_type("text_input") == [{"text": "mở cửa phòng 101"}]


def test_audio_out_records_tts(hal, events):
    hal.audio_out("Door unlocked. Welcome home.")
    assert events.of_type("tts_stream_start") == [{"text": "Door unlocked. Welcome home."}]


def test_display_respects_the_declared_resolution(hal):
    hal.display("welcome", width=320, height=240)
    assert hal.frame == "welcome"
    with pytest.raises(BoardCapabilityError) as excinfo:
        hal.display("too wide", width=640)
    assert "320" in excinfo.value.why


def test_every_trace_the_sim_writes_validates(hal, events):
    hal.type_text("bật đèn")
    hal.audio_in()
    hal.digital_out("porch_light", "on", signature="proof")
    hal.audio_out("Light on.")
    validate_trace(events.to_trace())


# --- Contract checks -----------------------------------------------------------


def test_an_unsigned_command_is_a_contract_violation(hal):
    with pytest.raises(ActionContractViolation):
        hal.digital_out("door_lock", "pulse", 30_000)
    assert hal.pin("door_lock").never_pulsed()


@pytest.mark.parametrize("call", ["digital_out", "set_sensor"])
def test_unknown_pins_and_sensors_are_three_part_errors(hal, call):
    with pytest.raises(BoardCapabilityError) as excinfo:
        if call == "digital_out":
            hal.digital_out("garage_door", "pulse", signature="proof")
        else:
            hal.set_sensor("co2", 400)
    error = excinfo.value
    assert "sim-default" in error.why
    assert error.where and error.how


def test_an_unknown_pin_is_refused_before_the_proof_is_spent(events):
    spent = []
    hal = SimHAL(events=events, authorize=lambda signature, pin, where: spent.append(pin))
    with pytest.raises(BoardCapabilityError):
        hal.digital_out("door_lok", "pulse", signature="proof")
    assert spent == []


def test_a_misspelled_pin_assertion_raises(hal):
    with pytest.raises(BoardCapabilityError):
        hal.pin("door_lok").never_pulsed()
    assert hal.pin("porch_light").never_pulsed()


def test_an_unknown_operation_is_refused(hal):
    with pytest.raises(BoardCapabilityError):
        hal.digital_out("door_lock", "blink", signature="proof")


def test_a_board_for_another_target_is_refused():
    with pytest.raises(BoardCapabilityError) as excinfo:
        SimHAL(load_board_by_id("esp32s3-box-3"))
    assert "esp32s3" in excinfo.value.why


# --- Seam with the Gate Engine (shared with TSK-S2-03) ---------------------------


@pytest.mark.parametrize(
    ("facts", "pulsed"),
    [
        ({"guest_authenticated": True, "room_matches": True, "risk_level": "low"}, True),
        ({"guest_authenticated": False, "room_matches": True, "risk_level": "low"}, False),
    ],
)
async def test_only_an_allowed_verdict_reaches_the_pin(gates_dir, facts, pulsed):
    events = EventLog()
    engine = ActionContractEngine(events=events)
    engine.register("unlock_door", resolve_gate_file(gates_dir / "unlock_door@1.2.0.yaml"))
    hal = SimHAL(events=events)

    result = await engine.evaluate("unlock_door", facts)
    if result.allowed:
        hal.digital_out("door_lock", "pulse", 30_000, signature=result.gate_digest)

    assert hal.pin("door_lock").pulsed_once(duration_ms=30_000) is pulsed
    assert hal.pin("door_lock").never_pulsed() is not pulsed
    validate_trace(events.to_trace())
