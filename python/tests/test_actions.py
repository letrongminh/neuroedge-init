"""
TSK-S2-05 — `@action`, `c.do()` / `c.say()`, and single-use verdict tokens.

Covers Sprint 2 exit criterion 2 (a direct call raises and the pin stays idle)
and Sprint 3 exit criterion A3 (no path to a pin without a valid token).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from neuroedge import action
from neuroedge.actions import TTL_FACTOR, Conversation, VerdictToken
from neuroedge.engine import (
    ActionContractEngine,
    EventLog,
    resolve_gate_document,
    resolve_gate_file,
)
from neuroedge.errors import ActionContractViolation, TokenReplayError
from neuroedge.hal import digital
from neuroedge.hal.sim import SimHAL
from neuroedge.trace import validate_trace


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, ms: float) -> None:
        self.now += ms


CLOCK = FakeClock()
LEAKED: dict[str, VerdictToken] = {}
RAN: list[str] = []


@action(name="t_unlock_door", requires="digital.out:door_lock", gate="unlock_door")
def unlock_door(guest_id: str = "g-1", duration_s: int = 30) -> None:
    RAN.append("t_unlock_door")
    digital.out("door_lock").pulse(seconds=duration_s)


@action(name="t_double_pulse", requires="digital.out:door_lock", gate="unlock_door")
def double_pulse() -> None:
    digital.out("door_lock").pulse(seconds=1)
    digital.out("door_lock").pulse(seconds=1)


@action(name="t_wrong_pin", requires="digital.out:door_lock", gate="unlock_door")
def wrong_pin() -> None:
    digital.out("porch_light").on()


@action(name="t_slow", requires="digital.out:door_lock", gate="unlock_door")
def slow() -> None:
    CLOCK.advance(120 * TTL_FACTOR + 1)
    digital.out("door_lock").pulse(seconds=1)


@action(name="t_leak", requires="digital.out:door_lock", gate="unlock_door")
def leak() -> None:
    LEAKED["token"] = digital._active.get().token


@action(name="t_porch", requires="digital.out:porch_light", gate="porch")
def porch_light() -> None:
    digital.out("porch_light").on()


@action(name="t_degrading", requires="digital.out:door_lock", gate="degrading")
def degrading() -> None:
    digital.out("door_lock").pulse(seconds=30)


@action(name="t_loop", requires="digital.out:gate_relay", gate="loop")
def loop() -> None:
    digital.out("gate_relay").pulse(seconds=1)


def _gate(name: str, on_block: dict) -> object:
    return resolve_gate_document(
        {
            "schema": "neuroedge.gate/v1",
            "name": name,
            "version": "1.0.0",
            "evaluate": {"ok": {"type": "bool", "instructions": "Precondition holds"}},
            "allow_when": {"ok": True},
            "on_block": on_block,
            "budget": {"p95_latency_ms": 100},
        }
    )


HAPPY = {"guest_authenticated": True, "room_matches": True, "risk_level": "low"}


@pytest.fixture
def session(gates_dir: Path):
    def build(facts=None, *, porch_ok: bool = True):
        CLOCK.now = 0.0
        RAN.clear()
        events = EventLog(CLOCK)
        engine = ActionContractEngine(clock=CLOCK, events=events)
        engine.register("unlock_door", resolve_gate_file(gates_dir / "unlock_door@1.2.0.yaml"))
        engine.register("porch", _gate("porch", {"action": "deny"}))
        engine.register(
            "degrading", _gate("degrading", {"action": "degrade", "fallback_action": "t_porch"})
        )
        engine.register("loop", _gate("loop", {"action": "degrade", "fallback_action": "t_loop"}))
        hal = SimHAL(events=events)
        merged = dict(HAPPY if facts is None else facts)
        merged.setdefault("ok", porch_ok)
        return Conversation(engine=engine, hal=hal, facts=merged), hal, events

    return build


# --- c.do ------------------------------------------------------------------------


async def test_an_allowed_action_pulses_exactly_once(session):
    c, hal, events = session()
    result = await c.do(unlock_door, guest_id="g-7")
    assert not result.blocked
    assert hal.pin("door_lock").pulsed_once(duration_ms=30_000)
    assert events.of_type("actuator_command") == [
        {"pin": "door_lock", "operation": "pulse", "duration_ms": 30_000}
    ]
    validate_trace(events.to_trace())


async def test_a_blocked_action_never_runs_its_body(session):
    c, hal, _ = session(dict(HAPPY, guest_authenticated=False))
    result = await c.do(unlock_door)
    assert result.blocked
    assert RAN == []
    assert hal.pin("door_lock").never_pulsed()


async def test_c_do_accepts_the_registered_name(session):
    c, hal, _ = session()
    assert not (await c.do("t_unlock_door")).blocked


async def test_say_evaluates_no_gate_and_issues_no_token(session):
    c, hal, events = session()
    await c.say("Xin chào.")
    assert events.of_type("tts_stream_start") == [{"text": "Xin chào."}]
    assert events.of_type("gate_evaluation_begin") == []
    assert events.of_type("gate_evaluation_result") == []


# --- Sprint 2 exit criterion 2: direct calls ----------------------------------------


def test_a_direct_call_is_a_contract_violation_naming_the_caller(session):
    _, hal, _ = session()
    with pytest.raises(ActionContractViolation) as excinfo:
        unlock_door()
    assert "test_actions.py" in excinfo.value.where
    assert "c.do" in excinfo.value.how
    assert hal.pin("door_lock").never_pulsed()


def test_digital_out_outside_c_do_is_a_contract_violation():
    with pytest.raises(ActionContractViolation) as excinfo:
        digital.out("door_lock").pulse(seconds=1)
    assert "no verdict token" in excinfo.value.why


# --- Token rules ------------------------------------------------------------------------


async def test_a_second_pulse_in_one_action_is_token_replayed(session):
    c, hal, events = session()
    with pytest.raises(TokenReplayError) as excinfo:
        await c.do(double_pulse)
    assert (excinfo.value.code, excinfo.value.reason) == ("NE1002", "token_replayed")
    assert len(events.of_type("actuator_command")) == 1
    assert events.of_type("actuator_command_rejected") == [
        {"pin": "door_lock", "reason": "token_replayed", "code": "NE1002"}
    ]


async def test_a_token_kept_past_c_do_is_token_replayed(session):
    c, hal, _ = session()
    await c.do(leak)
    with pytest.raises(TokenReplayError) as excinfo:
        hal.digital_out("door_lock", "pulse", 1_000, signature=LEAKED["token"])
    assert excinfo.value.reason == "token_replayed"
    assert hal.pin("door_lock").never_pulsed()


async def test_a_token_used_after_its_ttl_is_token_expired(session):
    c, hal, _ = session()
    with pytest.raises(TokenReplayError) as excinfo:
        await c.do(slow)
    assert excinfo.value.reason == "token_expired"
    assert hal.pin("door_lock").never_pulsed()


async def test_a_token_from_another_process_instance_is_token_expired(session):
    c, hal, _ = session()
    await c.do(leak)
    c.ledger.process_instance_id = "restarted"
    with pytest.raises(TokenReplayError) as excinfo:
        hal.digital_out("door_lock", "pulse", 1_000, signature=LEAKED["token"])
    assert excinfo.value.reason == "token_expired"
    assert "another process instance" in excinfo.value.why


async def test_a_token_for_one_pin_cannot_drive_another(session):
    c, hal, _ = session()
    with pytest.raises(ActionContractViolation) as excinfo:
        await c.do(wrong_pin)
    assert not isinstance(excinfo.value, TokenReplayError)
    assert hal.pin("porch_light").never_pulsed()


async def test_the_trace_never_contains_a_nonce(session):
    c, _, events = session()
    await c.do(leak)
    assert LEAKED["token"].nonce not in json.dumps(events.to_trace())
    assert LEAKED["token"].nonce not in repr(LEAKED["token"])


# --- Sprint 3 A3: every path to a pin without a valid token is refused ----------


async def test_no_path_reaches_a_pin_without_a_valid_token(session):
    c, hal, _ = session()
    await c.do(leak)
    real = LEAKED["token"]
    forged = dataclasses.replace(real, nonce="0" * 32)
    attempts = {
        "no signature": "",
        "a string": "x",
        "a gate digest": real.gate_digest,
        "a forged token": forged,
    }
    for label, signature in attempts.items():
        with pytest.raises(ActionContractViolation):
            hal.digital_out("door_lock", "pulse", 1_000, signature=signature)
        assert hal.pin("door_lock").never_pulsed(), label


# --- degrade runs the fallback through its own gate (Q-17) ------------------------


async def test_degrade_runs_the_fallback_through_its_own_gate(session):
    c, hal, _ = session({"ok": False})
    result = await c.do(degrading)
    assert result.blocked
    assert result.fallback is not None
    assert result.fallback.action == "t_porch"
    assert result.fallback.blocked, "the porch gate sees ok=false too"
    assert hal.pin("door_lock").never_pulsed()
    assert hal.pin("porch_light").never_pulsed()


async def test_a_self_referencing_fallback_is_skipped(session):
    c, hal, events = session({"ok": False})
    result = await c.do(loop)
    assert result.blocked
    assert result.fallback is None, "the cycle is caught before running anything"
    assert events.of_type("fallback_skipped") == [{"action": "t_loop", "reason": "fallback cycle"}]
    assert hal.pin("gate_relay").never_pulsed()


def test_an_action_name_cannot_be_defined_twice():
    with pytest.raises(ActionContractViolation) as excinfo:

        @action(name="t_unlock_door", requires="digital.out:door_lock", gate="unlock_door")
        def imposter() -> None:
            return None

    assert "already defined" in excinfo.value.why


def test_requires_must_name_a_primitive():
    with pytest.raises(ActionContractViolation) as excinfo:

        @action(name="t_bad", requires="gpio:door_lock", gate="unlock_door")
        def bad() -> None:
            return None

    assert "primitive" in excinfo.value.why
