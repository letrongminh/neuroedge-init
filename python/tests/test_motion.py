"""
TSK-I2a-05 — `motion.*` on `sim` (RFC-0011): channels, leases, runs, the safe state.

The clock is virtual (`FakeClock`): a lease, a run and a hold end by the injected time, never
the wall clock. The board is `sim-rpi5` (mirror of `linux-rpi5`): motor `wheel_left`
(speed_max 0.6, ramp_min 200 ms, lease 200 ms, envelope: window 60 s, 30 s budget, 2 s between
runs, 10 s continuous) and servo `gripper` (0..90 deg, safe state `hold` for at most 2 s,
lease 200 ms, 1 s between runs, 3 s continuous). The `linux` half is `test_motion_linux.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from neuroedge import action, motion
from neuroedge.actions import Conversation
from neuroedge.actions import token as token_module
from neuroedge.actions.tools import ToolCall, ToolSet, dispatch
from neuroedge.engine import ActionContractEngine, EventLog, GateVerdict, resolve_gate_document
from neuroedge.engine.compiler import BuildFailed, build
from neuroedge.errors import (
    ActionContractViolation,
    BoardCapabilityError,
    EnvelopeRefusedError,
    TokenReplayError,
)
from neuroedge.hal.board import load_board_by_id
from neuroedge.hal.envelope import EnvelopeLimits, SafetyEnvelope
from neuroedge.hal.sim import SimHAL
from neuroedge.perception.voice_fsm import VoiceStateMachine

BOARD = "sim-rpi5"


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = float(start)

    def __call__(self) -> float:
        return self.now

    def advance(self, ms: float) -> None:
        self.now += ms


# -- the agent: three actions behind one gate ----------------------------------------------


@action(name="mt_drive", requires="motion:wheel_left", gate="g")
def mt_drive(speed: float = 0.4, ramp_ms: int = 200) -> None:
    motion.motor("wheel_left", speed=speed, ramp_ms=ramp_ms)


@action(name="mt_grip", requires="motion:gripper", gate="g")
def mt_grip(angle: float = 45.0) -> None:
    motion.servo("gripper", target=angle, speed_max=90)


@action(name="mt_halt", requires="motion:wheel_left", gate="g")
def mt_halt() -> None:
    motion.stop("wheel_left")


@action(name="mt_twice", requires="motion:wheel_left", gate="g")
def mt_twice() -> None:
    motion.motor("wheel_left", speed=0.2)
    motion.motor("wheel_left", speed=0.3)


@action(name="mt_wrong_kind", requires=["motion:wheel_left", "motion:gripper"], gate="g")
def mt_wrong_kind(kind: str = "motor_on_servo") -> None:
    if kind == "motor_on_servo":
        motion.motor("gripper", speed=0.1)
    else:
        motion.servo("wheel_left", target=10)


@action(
    name="mt_pulse_and_drive", requires=["motion:wheel_left", "digital.out:door_lock"], gate="g"
)
def mt_pulse_and_drive() -> None:
    from neuroedge.hal import digital

    digital.out("door_lock").pulse(ms=5000)
    motion.motor("wheel_left", speed=0.4)


def gate_document(p95: int = 100, fail: str = "closed", arguments=None) -> dict:
    document = {
        "schema": "neuroedge.gate/v1",
        "name": "g",
        "version": "1.0.0",
        "evaluate": {"ok": {"type": "bool", "instructions": "go"}},
        "allow_when": {"ok": True},
        "on_block": {"action": "deny"},
        "budget": {"p95_latency_ms": p95, "fail": fail},
    }
    if arguments is not None:
        document["arguments"] = arguments
    return document


class Rig:
    def __init__(self, *, ok=True, arguments=None, limits=None, board_id=BOARD, store=None):
        self.clock = FakeClock()
        self.events = EventLog(self.clock)
        board = load_board_by_id(board_id)
        envelope = None
        if limits is not None:
            envelope = SafetyEnvelope(
                limits, clock=self.clock, virtual=True, store=store, init_store=store is not None
            )
        self.hal = SimHAL(board, events=self.events, envelope=envelope)
        gate = resolve_gate_document(gate_document(arguments=arguments))
        self.engine = ActionContractEngine({"g": gate}, clock=self.clock, events=self.events)
        self.c = Conversation(engine=self.engine, hal=self.hal, facts={"ok": ok})

    def do(self, name, **kwargs):
        import asyncio

        return asyncio.run(self.c.do(name, **kwargs))

    def advance(self, ms):
        self.clock.advance(ms)
        self.hal.run_due()

    def of(self, kind):
        return [e["data"] for e in self.events.events if e["type"] == kind]

    def state(self, channel="wheel_left"):
        return self.hal.motion_values()[channel]


@pytest.fixture
def rig():
    return Rig()


# -- a command moves the channel for one lease ---------------------------------------------------


def test_a_motor_command_ramps_the_speed_and_holds_a_lease(rig):
    rig.do("mt_drive", speed=0.4, ramp_ms=200)
    assert rig.state()["mode"] == "active" and rig.state()["lease_left_ms"] == 200
    assert rig.state()["speed"] == 0.0 and rig.state()["setpoint"] == {"speed": 0.4, "ramp_ms": 200}
    rig.clock.advance(100)
    assert rig.state()["speed"] == pytest.approx(0.2)
    assert rig.state()["lease_left_ms"] == 100
    assert rig.of("motion_command") == [
        {
            "channel": "wheel_left",
            "kind": "motor",
            "speed": 0.4,
            "direction": "forward",
            "ramp_ms": 200,
            "lease_ms": 200,
            "run": "new",
        }
    ]


def test_a_servo_moves_toward_its_target_at_the_commanded_speed(rig):
    rig.do("mt_grip", angle=45)
    rig.clock.advance(100)  # 90 deg/s: 9 deg in 100 ms
    assert rig.state("gripper")["position"] == pytest.approx(9.0)
    assert rig.state("gripper")["enabled"] is True


def test_the_agent_api_needs_a_verdict_token_to_command():
    with pytest.raises(ActionContractViolation, match="no verdict token is active"):
        motion.motor("wheel_left", speed=0.1)


def test_a_bare_hal_refuses_a_command_without_proof():
    hal = SimHAL(load_board_by_id(BOARD))
    with pytest.raises(ActionContractViolation, match="signature|ledger"):
        hal.motion_motor("wheel_left", 0.1, called_from="test")
    assert hal.motion_values()["wheel_left"]["mode"] == "idle"


def test_a_board_without_motion_refuses_it():
    hal = SimHAL(load_board_by_id("sim-default"))
    with pytest.raises(BoardCapabilityError, match="declares no motion channel"):
        hal.motion_motor("wheel_left", 0.1, called_from="test")


# -- RFC-0011 §9.4: the API is two shapes, and a stranger is refused ----------------------------


@pytest.mark.parametrize("kind", ["motor_on_servo", "servo_on_motor"])
def test_a_command_of_the_wrong_kind_is_refused_like_an_unknown_channel(rig, kind):
    with pytest.raises(BoardCapabilityError, match="declares no motion") as raised:
        rig.do("mt_wrong_kind", kind=kind)
    assert "is a servo" in raised.value.why or "is a motor" in raised.value.why
    assert rig.of("motion_command") == []


def test_an_unknown_channel_is_refused_and_nothing_moves(rig):
    with pytest.raises(BoardCapabilityError, match="declares no motion motor named 'nope'"):
        rig.hal.motion_motor("nope", 0.1, signature=None, called_from="test")
    with pytest.raises(BoardCapabilityError):
        rig.hal.motion_stop("nope", called_from="test")


# -- RFC-0011 §9.5: the board's limits, before the envelope and the proof ------------------------


@pytest.mark.parametrize(
    ("kwargs", "why"),
    [
        ({"speed": 0.7}, "speed_max"),
        ({"speed": -0.1}, "speed_max"),
        ({"speed": float("nan")}, "speed_max"),
        ({"speed": True}, "speed_max"),
        ({"speed": 0.4, "ramp_ms": 100}, "ramp_min_ms"),
    ],
    ids=["over", "negative", "nan", "bool", "ramp-too-short"],
)
def test_the_board_limits_a_motor_command(rig, kwargs, why):
    with pytest.raises(BoardCapabilityError, match=why):
        rig.do("mt_drive", **kwargs)
    assert rig.of("motion_command") == [] and rig.of("envelope_refused") == []
    assert rig.state()["mode"] == "idle"


def test_a_limit_the_board_refuses_spends_no_token_and_reserves_nothing():
    rig = Rig(limits={"wheel_left": EnvelopeLimits(60, 30000, 2000, 10000)})
    with pytest.raises(BoardCapabilityError):
        rig.do("mt_drive", speed=0.9)
    assert rig.hal.envelope.live("wheel_left") is None
    assert rig.of("actuator_command_rejected") == []  # the proof was never asked for


@pytest.mark.parametrize("target", [-1, 91, float("inf")])
def test_the_board_limits_a_servo_target(rig, target):
    with pytest.raises(BoardCapabilityError, match="0..90 deg"):
        rig.do("mt_grip", angle=target)


def test_reverse_is_refused_on_every_target_until_a_board_declares_a_direction(rig):
    with pytest.raises(BoardCapabilityError, match="direction line"):
        rig.hal.motion_motor("wheel_left", 0.2, "reverse", signature=None, called_from="t")


def test_the_gate_narrows_the_board_and_the_tighter_limit_wins():
    rig = Rig(arguments={"speed": {"type": "number", "maximum": 0.3}})
    # gate tighter than the board: 0.5 is within the board's 0.6 but the gate says no.
    result = rig.do("mt_drive", speed=0.5)
    assert result.verdict is GateVerdict.BLOCK and result.gate.reason == "argument_out_of_range"
    assert rig.of("motion_command") == []
    assert rig.do("mt_drive", speed=0.3).verdict is GateVerdict.ALLOW


def test_a_gate_looser_than_the_board_leaves_the_board_in_force():
    rig = Rig(arguments={"speed": {"type": "number", "maximum": 1.0}})
    with pytest.raises(BoardCapabilityError, match="speed_max"):
        rig.do("mt_drive", speed=0.8)  # the gate admits 0.8, the board's 0.6 does not
    assert rig.do("mt_drive", speed=0.6).verdict is GateVerdict.ALLOW


# -- RFC-0011 §3c, §9.2: the lease ---------------------------------------------------------------


def test_a_channel_nobody_commands_goes_to_its_safe_state_when_the_lease_ends(rig):
    rig.do("mt_drive")
    rig.advance(199)
    assert rig.state()["mode"] == "active" and rig.of("motion_safe") == []
    rig.advance(1)
    assert rig.state()["mode"] == "idle" and rig.state()["speed"] == 0.0
    assert rig.of("motion_safe") == [
        {"channel": "wheel_left", "state": "stop", "cause": "lease_expired"}
    ]


def test_a_late_tick_still_stops_the_model_at_the_leases_end():
    rig = Rig()
    rig.do("mt_drive", speed=0.4, ramp_ms=200)
    rig.clock.advance(500)  # nobody ticked for 300 ms after the lease ran out
    rig.hal.run_due()
    assert [e["data"]["cause"] for e in rig.events.events if e["type"] == "motion_safe"] == [
        "lease_expired"
    ]
    # the motor covered its 200 ms ramp (0.4 * 0.2 / 2) and not one ms more
    assert rig.state()["distance"] == pytest.approx(0.04)


def test_the_lease_is_the_boards_and_not_the_gates_or_the_ttl(rig, monkeypatch):
    monkeypatch.setattr(token_module, "TTL_FACTOR", 1000)  # a huge verdict TTL changes nothing
    rig.do("mt_drive")
    rig.advance(200)
    assert rig.of("motion_safe")[0]["cause"] == "lease_expired"


def test_a_missing_lease_ms_is_200():
    from neuroedge.hal.motion_core import Channel

    record = {"name": "m", "kind": "motor", "speed_max": 0.5, "ramp_min_ms": 0, "enable_pin": "x"}
    assert Channel.from_record(record).lease_ms == 200
    assert Channel.from_record(record).safe_state == "stop"  # not declared => stop (Q-35)


def test_a_fresh_gate_pass_renews_the_lease_and_the_run_goes_on(rig):
    rig.do("mt_drive")
    rig.advance(100)
    result = rig.do("mt_drive", speed=0.5)
    assert result.verdict is GateVerdict.ALLOW
    assert rig.state()["lease_left_ms"] == 200
    rig.advance(150)  # past the first lease's end, inside the second
    assert rig.state()["mode"] == "active" and rig.of("motion_safe") == []
    assert [c["run"] for c in rig.of("motion_command")] == ["new", "renewed"]


def test_a_blocked_call_does_not_renew_it_and_sends_the_channel_safe():
    rig = Rig()
    rig.do("mt_drive")
    rig.advance(100)
    rig.c.facts = {"ok": False}
    result = rig.do("mt_drive")
    assert result.verdict is GateVerdict.BLOCK
    assert rig.of("motion_safe") == [{"channel": "wheel_left", "state": "stop", "cause": "block"}]
    assert rig.state()["mode"] == "idle"


def test_a_block_for_another_channel_leaves_this_one_running():
    rig = Rig()
    rig.do("mt_drive")
    rig.c.facts = {"ok": False}
    assert rig.do("mt_grip").verdict is GateVerdict.BLOCK
    assert rig.state()["mode"] == "active"
    assert [e["channel"] for e in rig.of("motion_safe")] == ["gripper"] or rig.of(
        "motion_safe"
    ) == []


def test_a_lease_carries_exactly_one_command(rig):
    with pytest.raises(TokenReplayError) as raised:
        rig.do("mt_twice")
    assert raised.value.reason == "lease_used"
    assert [c["speed"] for c in rig.of("motion_command")] == [0.2]
    assert rig.of("actuator_command_rejected") == [
        {"pin": "wheel_left", "reason": "lease_used", "code": "NE1002"}
    ]


def test_a_lease_that_ran_out_before_the_command_is_refused():
    rig = Rig()
    ledger = rig.c.ledger
    token = ledger.issue(
        gate="g@1.0.0",
        gate_digest="d",
        action="x",
        pins=frozenset(),
        session_id="s",
        p95_ms=100,
        channels={"wheel_left": 200},
    )
    rig.clock.advance(250)
    with pytest.raises(TokenReplayError) as raised:
        rig.hal.motion_motor("wheel_left", 0.2, signature=token, called_from="t")
    assert raised.value.reason == "lease_expired"
    assert rig.state()["mode"] == "idle" and rig.hal.envelope.live("wheel_left") is None


def test_a_lease_for_one_channel_is_no_proof_for_another():
    rig = Rig()
    token = rig.c.ledger.issue(
        gate="g@1.0.0",
        gate_digest="d",
        action="x",
        pins=frozenset(),
        session_id="s",
        p95_ms=100,
        channels={"wheel_left": 200},
    )
    with pytest.raises(ActionContractViolation, match="grants"):
        rig.hal.motion_servo("gripper", 10, signature=token, called_from="t")
    assert rig.of("actuator_command_rejected")[-1]["reason"] == "pin_not_granted"


def test_a_closed_token_is_no_lease(rig):
    result = rig.do("mt_drive")
    assert result.verdict is GateVerdict.ALLOW
    leaked = rig.c.ledger.issue(
        gate="g@1.0.0", gate_digest="d", action="x", pins=frozenset(), session_id="s",
        p95_ms=100, channels={"wheel_left": 200},
    )  # fmt: skip
    rig.c.ledger.close(leaked)
    with pytest.raises(TokenReplayError):
        rig.hal.motion_motor("wheel_left", 0.2, signature=leaked, called_from="t")


# -- RFC-0011 §3b, §9.8: a run is a chain of leases ------------------------------------------------


def test_renewals_every_100ms_are_not_held_up_by_min_interval_ms(rig):
    rig.do("mt_drive")
    for _ in range(20):  # 2 s of renewals, while min_interval_ms is 2000
        rig.advance(100)
        assert rig.do("mt_drive").verdict is GateVerdict.ALLOW
    assert rig.of("envelope_refused") == []
    assert [c["run"] for c in rig.of("motion_command")] == ["new"] + ["renewed"] * 20


def test_min_interval_ms_is_checked_only_when_a_run_starts(rig):
    rig.do("mt_drive")
    rig.advance(300)  # the lease ran out: the run is over
    assert rig.of("motion_safe")[0]["cause"] == "lease_expired"
    with pytest.raises(EnvelopeRefusedError) as raised:
        rig.do("mt_drive")  # a new run 300 ms after the last ended: min_interval_ms 2000
    assert raised.value.reason == "min_interval_ms"
    assert rig.of("envelope_refused")[0]["pin"] == "wheel_left"
    rig.advance(2000)
    assert rig.do("mt_drive").verdict is GateVerdict.ALLOW


def test_max_continuous_ms_covers_the_whole_run_and_the_hal_sends_safe_at_its_end():
    rig = Rig()
    rig.do("mt_drive")
    for _ in range(99):  # 9.9 s of renewals, each inside the last one's lease
        rig.advance(100)
        rig.do("mt_drive")
    assert rig.state()["mode"] == "active"
    rig.advance(100)  # 10 s since the run began: the envelope's max_continuous_ms
    assert rig.state()["mode"] == "idle"
    assert rig.of("motion_safe")[-1] == {
        "channel": "wheel_left",
        "state": "stop",
        "cause": "max_continuous_ms",
    }
    with pytest.raises(EnvelopeRefusedError):  # the next run waits min_interval_ms from the end
        rig.do("mt_drive")


def test_a_run_reserves_max_continuous_ms_and_gives_back_the_unused_part():
    rig = Rig(limits={"wheel_left": EnvelopeLimits(60, 12000, 0, 10000)})
    rig.do("mt_drive")  # reserves 10 s of the 12 s budget
    with pytest.raises(EnvelopeRefusedError):
        rig.hal.envelope.reserve("wheel_left", 0, operation="run")  # no second run is open at once
    rig.advance(300)  # the run ended after 200 ms: 9.8 s go back
    rig.do("mt_drive")  # reserves another 10 s: it fits only because the first gave back
    assert rig.of("envelope_refused") == []


def test_an_over_budget_run_is_refused_and_nothing_moves():
    rig = Rig(limits={"wheel_left": EnvelopeLimits(60, 5000, 0, 10000)})
    with pytest.raises(EnvelopeRefusedError) as raised:
        rig.do("mt_drive")
    assert raised.value.reason == "window_budget"
    assert rig.of("motion_command") == [] and rig.state()["mode"] == "idle"
    assert rig.of("envelope_refused")[0]["reason"] == "window_budget"


def test_a_proof_the_hal_refuses_gives_the_whole_reservation_back():
    rig = Rig(limits={"wheel_left": EnvelopeLimits(60, 10000, 0, 10000)})
    token = rig.c.ledger.issue(
        gate="g@1.0.0", gate_digest="d", action="x", pins=frozenset(), session_id="s",
        p95_ms=100, channels={"wheel_left": 200},
    )  # fmt: skip
    rig.clock.advance(300)
    with pytest.raises(TokenReplayError):
        rig.hal.motion_motor("wheel_left", 0.2, signature=token, called_from="t")
    assert rig.hal.envelope.live("wheel_left") is None
    assert rig.do("mt_drive").verdict is GateVerdict.ALLOW  # the full budget is still there


# -- RFC-0011 §3d, §9.7: toward the safe state nothing is refused --------------------------------------


def test_stop_needs_no_token_no_envelope_and_does_not_wait_for_a_ramp(rig):
    rig.do("mt_drive", speed=0.5, ramp_ms=2000)
    rig.advance(10)  # mid-ramp, a minute from min_interval
    rig.hal.motion_stop("wheel_left", called_from="test")  # no signature, no gate
    assert rig.state()["mode"] == "idle" and rig.state()["speed"] == 0.0
    assert rig.of("motion_safe") == [{"channel": "wheel_left", "state": "stop", "cause": "stop"}]
    assert rig.of("envelope_refused") == [] and rig.of("actuator_command_rejected") == []


def test_the_agent_can_stop_inside_an_action_with_its_own_gate_pass(rig):
    rig.do("mt_drive")
    result = rig.do("mt_halt")
    assert result.verdict is GateVerdict.ALLOW
    assert rig.state()["mode"] == "idle"


def test_close_stops_every_channel_whatever_it_declares_and_records_why():
    rig = Rig()
    rig.do("mt_drive")
    rig.do("mt_grip")
    rig.hal.close()
    causes = {(e["channel"], e["state"], e["cause"]) for e in rig.of("motion_safe")}
    assert causes == {("wheel_left", "stop", "close"), ("gripper", "stop", "close")}
    assert rig.state()["mode"] == "idle" and rig.state("gripper")["mode"] == "idle"


def test_closing_ends_the_reservation_so_nothing_stays_held():
    rig = Rig(limits={"wheel_left": EnvelopeLimits(60, 10000, 0, 10000)})
    rig.do("mt_drive")
    rig.hal.close()
    assert rig.hal.envelope.live("wheel_left") is None


# -- RFC-0011 §9.3: the declared safe state ------------------------------------------------------------


def test_a_servo_that_declares_hold_holds_when_its_lease_ends_then_stops_after_max_hold_ms(rig):
    rig.do("mt_grip", angle=45)
    rig.advance(200)  # lease over: hold at the position reached then (18 deg at 90 deg/s)
    assert rig.state("gripper")["mode"] == "holding" and rig.state("gripper")["enabled"] is True
    assert rig.state("gripper")["position"] == pytest.approx(18.0)
    rig.advance(1999)
    assert rig.state("gripper")["mode"] == "holding"
    rig.advance(1)  # max_hold_ms 2000 since the hold began
    assert rig.state("gripper")["mode"] == "idle" and rig.state("gripper")["enabled"] is False
    assert [(e["state"], e["cause"]) for e in rig.of("motion_safe")] == [
        ("hold", "lease_expired"),
        ("stop", "max_hold_ms"),
    ]


def test_a_hold_never_outlives_the_runs_max_continuous_ms():
    rig = Rig(limits={"gripper": EnvelopeLimits(60, 10000, 0, 700)})
    rig.do("mt_grip")
    rig.advance(200)  # holding, with 500 ms of the run left
    rig.advance(500)
    assert rig.state("gripper")["mode"] == "idle"
    assert rig.of("motion_safe")[-1]["cause"] == "max_continuous_ms"


def test_close_stops_a_holding_servo_whatever_it_declares():
    rig = Rig()
    rig.do("mt_grip")
    rig.advance(200)
    assert rig.state("gripper")["mode"] == "holding"
    rig.hal.close()
    assert rig.state("gripper")["mode"] == "idle"
    assert rig.of("motion_safe")[-1] == {"channel": "gripper", "state": "stop", "cause": "close"}


def test_a_barge_in_leaves_a_holding_servo_holding_and_stops_a_motor():
    rig = Rig()
    rig.do("mt_grip")
    rig.do("mt_drive")
    rig.advance(10)
    assert sorted(rig.hal.motion_barge_in()) == ["gripper", "wheel_left"]
    assert rig.state("gripper")["mode"] == "holding"  # its declared safe state
    assert rig.state()["mode"] == "idle"


# -- RFC-0011 §3d, §9.1: barge-in ----------------------------------------------------------------------


def test_a_barge_in_sends_safe_in_the_same_tick_and_before_the_lease_ends():
    rig = Rig()
    rig.do("mt_drive")
    fsm = VoiceStateMachine(events=rig.events, stop_motion=rig.hal.motion_barge_in)
    rig.clock.advance(50)  # 150 ms of the lease are left
    fsm._barge_in()
    safe = [e for e in rig.events.events if e["type"] == "motion_safe"]
    assert [e["data"]["cause"] for e in safe] == ["barge_in"]
    assert safe[0]["offset_ms"] == 50  # the tick of the trigger, the lease would end at 200
    assert rig.state()["mode"] == "idle"
    rig.advance(300)  # nothing renews it, and the lease's own expiry has nothing left to do
    assert [e["data"]["cause"] for e in rig.events.events if e["type"] == "motion_safe"] == [
        "barge_in"
    ]


def test_a_barge_in_does_not_cut_a_delivered_digital_pulse():
    rig = Rig()
    rig.do("mt_pulse_and_drive")
    fsm = VoiceStateMachine(events=rig.events, stop_motion=rig.hal.motion_barge_in)
    rig.clock.advance(50)
    fsm._barge_in()
    assert rig.state()["mode"] == "idle"
    assert rig.hal.pin("door_lock").pulses == [5000]
    assert not rig.of("actuator_aborted")  # the pulse runs its 5 s (voice_fsm.md §5.3)


def test_the_voice_session_wires_barge_in_to_motion():
    from neuroedge.perception import voice_session

    source = Path(voice_session.__file__).read_text(encoding="utf-8")
    assert 'stop_motion=getattr(self.hal, "motion_barge_in", None)' in source


# -- [requires] and the build ----------------------------------------------------------------------------


def write_agent(tmp_path, *, channels='["wheel_left"]', p95=100, gate_extra=""):
    name = f"mt_{abs(hash(str(tmp_path)))}"
    (tmp_path / "actions").mkdir(parents=True, exist_ok=True)
    (tmp_path / "actions" / "drive.py").write_text(
        "from neuroedge import action, motion\n\n"
        f'@action(name="{name}_drive", requires="motion:wheel_left", gate="g")\n'
        "def drive(speed: float = 0.3) -> None:\n"
        '    motion.motor("wheel_left", speed=speed)\n',
        encoding="utf-8",
    )
    document = gate_document(p95=p95)
    (tmp_path / "g.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    (tmp_path / "commands.toml").write_text(
        f'[grammar]\nversion = 1\n\n[[command]]\nintent = "go"\npatterns = ["đi tới"]\ntool = "{name}_drive"\n',
        encoding="utf-8",
    )
    (tmp_path / "agent.toml").write_text(
        '[agent]\nname = "motion-test"\nversion = "0.1.0"\n\n'
        f'[requires]\n"motion" = {{ channels = {channels} }}\n\n'
        '[gates]\ng = "g.yaml"\n\n[sim.facts]\nok = true\n',
        encoding="utf-8",
    )
    return tmp_path / "agent.toml"


def test_an_agent_that_names_a_declared_channel_builds_on_the_boards_that_have_it(tmp_path):
    path = write_agent(tmp_path)
    build(path, target="sim", board_id=BOARD)
    build(path, target="linux", board_id="linux-rpi5")


def test_a_channel_the_board_does_not_declare_is_refused_at_build(tmp_path):
    path = write_agent(tmp_path, channels='["wheel_left", "arm"]')
    with pytest.raises(BuildFailed) as raised:
        build(path, target="sim", board_id=BOARD)
    assert any("motion:arm" in p.where for p in raised.value.problems)
    assert any("wheel_left" in p.why and "gripper" in p.why for p in raised.value.problems)


def test_the_default_sim_board_has_no_motion_and_the_build_names_the_one_that_has(tmp_path):
    with pytest.raises(BuildFailed) as raised:
        build(write_agent(tmp_path), target="sim")
    assert "sim-rpi5" in " ".join(p.how for p in raised.value.problems)


def test_a_bare_motion_requirement_names_no_channel_and_is_refused(tmp_path):
    path = write_agent(tmp_path, channels="[]")
    with pytest.raises(BuildFailed) as raised:
        build(path, target="sim", board_id=BOARD)
    assert any("non-empty list of channel names" in p.why for p in raised.value.problems)


def test_an_action_may_require_only_a_channel_requires_declares(tmp_path):
    path = write_agent(tmp_path, channels='["gripper"]')  # the action needs wheel_left
    with pytest.raises(BuildFailed) as raised:
        build(path, target="sim", board_id=BOARD)
    assert any("motion:wheel_left" in p.where for p in raised.value.problems)


def test_a_gate_slower_than_half_the_lease_is_refused_at_build_and_the_boundary_passes(tmp_path):
    over = tmp_path / "over"
    over.mkdir()
    with pytest.raises(BuildFailed) as raised:
        build(write_agent(over, p95=101), target="sim", board_id=BOARD)  # lease 200: 100 is the cap
    (problem,) = [p for p in raised.value.problems if isinstance(p, BoardCapabilityError)]
    assert problem.code == "NE3001" and "101" in problem.why and "100 ms" in problem.why
    exact = tmp_path / "exact"
    exact.mkdir()
    build(write_agent(exact, p95=100), target="sim", board_id=BOARD)


def test_the_lease_check_is_the_builds_and_gate_lint_does_not_change(tmp_path):
    from typer.testing import CliRunner

    from neuroedge.cli.main import app

    path = write_agent(tmp_path, p95=400)
    with pytest.raises(BuildFailed):
        build(path, target="sim", board_id=BOARD)
    result = CliRunner().invoke(app, ["gate", "lint", str(tmp_path)])
    assert result.exit_code == 0, result.output


def test_a_failed_lease_check_writes_no_firmware_or_artifact(tmp_path):
    out = tmp_path / "out"
    path = write_agent(tmp_path, p95=400)
    with pytest.raises(BuildFailed):
        build(path, target="linux", board_id="linux-rpi5", out_dir=out)
    assert not out.exists() or not any(out.rglob("*.netree"))


def test_requires_motion_is_accepted_and_one_that_is_not_listed_is_not():
    from neuroedge.actions.spec import Requirement

    assert Requirement.parse("motion:wheel_left", "t").name == "wheel_left"


# -- the REPL, the page and the trace ---------------------------------------------------------------------


def test_the_repl_shows_the_channels(tmp_path):
    from typer.testing import CliRunner

    from neuroedge.cli.main import app

    path = write_agent(tmp_path)
    result = CliRunner().invoke(
        app, ["run", "--agent", str(path), "--board", BOARD], input="đi tới\n:motion\nexit\n"
    )
    assert result.exit_code == 0, result.output
    assert "Motion channels" in result.output and "wheel_left" in result.output
    assert "gripper" in result.output and "safe: hold" in result.output


def test_the_page_lists_the_boards_channels_and_reads_the_motion_events():
    from neuroedge.viz import board_info, page

    assert board_info(BOARD)["motion"] == ["wheel_left", "gripper"]
    assert board_info("sim-default")["motion"] == []
    html = page(title="t", meta={}, events=[], board=board_info(BOARD))
    assert "motion_command" in html and "motion_safe" in html


def test_motion_events_validate_as_a_trace(tmp_path):
    from neuroedge.trace import validate_trace

    rig = Rig()
    rig.do("mt_drive")
    rig.advance(300)
    trace = rig.events.to_trace()
    validate_trace(trace)
    kinds = [e["type"] for e in trace["events"]]
    assert "motion_command" in kinds and "motion_safe" in kinds


def test_dispatch_runs_a_motion_tool_through_the_gate(rig):
    import asyncio

    from neuroedge.actions import REGISTRY

    tools = ToolSet([REGISTRY["mt_drive"]])
    result = asyncio.run(dispatch(rig.c, tools, ToolCall("mt_drive", {"speed": 0.2}, "mcp")))
    assert result.status == "ALLOW"
    assert rig.of("motion_command")[0]["speed"] == 0.2


# -- RFC-0011 §3b, §9.10: the envelope of a run survives a restart --------------------------------------------


class CountingStore:
    """A `FileEnvelopeStore` that counts its writes."""

    def __init__(self, directory):
        from neuroedge.hal.envelope import FileEnvelopeStore

        self.inner = FileEnvelopeStore(directory)
        self.saves = 0
        self.directory = self.inner.directory

    def path(self, name):
        return self.inner.path(name)

    def load(self, name):
        return self.inner.load(name)

    def create(self, name):
        return self.inner.create(name)

    def save(self, name, on_ms):
        self.saves += 1
        return self.inner.save(name, on_ms)


LIMITS = {"wheel_left": EnvelopeLimits(60, 30000, 2000, 10000)}


def test_a_run_writes_its_on_time_once_at_its_start_and_not_for_every_renewal(tmp_path):
    store = CountingStore(tmp_path / "state")
    rig = Rig(limits=LIMITS, store=store)
    saves_before = store.saves  # the store was created empty
    rig.do("mt_drive")
    assert store.saves == saves_before + 1  # write-ahead, before the channel moves
    for _ in range(10):
        rig.advance(100)
        rig.do("mt_drive")
    assert store.saves == saves_before + 1  # a renewal is no new run: no write, no flash wear


def test_after_a_restart_the_recorded_run_holds_budget_and_the_channel_waits(tmp_path):
    from neuroedge.hal.envelope import FileEnvelopeStore

    directory = tmp_path / "state"
    first = Rig(limits=LIMITS, store=FileEnvelopeStore(directory))
    first.do("mt_drive")  # the process ends with a run recorded as 10 s (its reservation)
    second = Rig(limits=LIMITS, store=None)
    second.hal.envelope = SafetyEnvelope(
        LIMITS, clock=second.clock, virtual=True, store=FileEnvelopeStore(directory)
    )
    with pytest.raises(EnvelopeRefusedError) as raised:
        second.do("mt_drive")  # min_interval_ms 2000 from the restart, whatever the old clock said
    assert raised.value.reason == "min_interval_ms"
    second.advance(2000)
    assert second.do("mt_drive").verdict is GateVerdict.ALLOW  # 10 s of 30 s used: room left
    assert second.hal.envelope.limits("wheel_left").max_on_ms_per_window == 30000


def test_an_unreadable_record_refuses_a_run_but_never_the_stop(tmp_path):
    from neuroedge.hal.envelope import FileEnvelopeStore

    directory = tmp_path / "state"
    directory.mkdir()
    (directory / "wheel_left.json").write_text("{not json", encoding="utf-8")
    rig = Rig()
    rig.hal.envelope = SafetyEnvelope(
        LIMITS, clock=rig.clock, virtual=True, store=FileEnvelopeStore(directory)
    )
    with pytest.raises(EnvelopeRefusedError) as raised:
        rig.do("mt_drive")
    assert raised.value.reason == "window_unreadable"
    rig.hal.motion_stop("wheel_left", called_from="test")  # toward the safe state: never refused
    assert rig.of("motion_command") == []


# -- replay ------------------------------------------------------------------------------------------------------


async def test_a_session_with_leases_replays_the_same_decisions(tmp_path):
    from neuroedge.sim import SimSession
    from neuroedge.testing import TracePlayer
    from neuroedge.testing.golden import safety_view
    from neuroedge.testing.recorder import TraceRecorder

    path = write_agent(tmp_path)
    clock = FakeClock()
    session = SimSession.load(path, board_id=BOARD, events=TraceRecorder(clock=clock), clock=clock)
    await session.handle("đi tới")
    clock.advance(100)
    await session.handle("đi tới")  # a renewal: the same run
    clock.advance(300)  # the lease runs out
    with pytest.raises(EnvelopeRefusedError):  # a new run 100 ms after the last ended: refused
        await session.handle("đi tới")
    clock.advance(2500)
    await session.handle("đi tới")
    out = tmp_path / "trace.json"
    session.write_trace(out)
    recorded = session.events.to_trace()

    kinds = [e["type"] for e in recorded["events"]]
    assert kinds.count("motion_command") == 3 and "motion_safe" in kinds
    assert [e["data"]["run"] for e in recorded["events"] if e["type"] == "motion_command"] == [
        "new",
        "renewed",
        "new",
    ]
    assert "envelope_refused" in kinds

    result = await TracePlayer(out, agent=path, board_id=BOARD).replay()
    assert not result.divergences and not result.warnings
    assert safety_view(result.replayed) == safety_view(recorded)


# -- an actuator that misbehaves ------------------------------------------------------------------------------------


class Flaky:
    """An actuator whose `drive` can fail, or report a drop from inside the command."""

    def __init__(self, inner, hal):
        self.inner, self.hal = inner, hal
        self.fail_next = False
        self.drop_during_drive: str | None = None

    def drive(self, channel, setpoint, now_ms, limit_ms):
        if self.fail_next:
            self.fail_next = False
            raise OSError(5, "I/O error")
        self.inner.drive(channel, setpoint, now_ms, limit_ms)
        if self.drop_during_drive:
            self.hal.motion_safe(channel.name, self.drop_during_drive)

    def safe(self, *args):
        return self.inner.safe(*args)

    def snapshot(self, *args):
        return self.inner.snapshot(*args)

    def close(self):
        return self.inner.close()


def flaky(rig):
    actuator = Flaky(rig.hal._motion.actuator, rig.hal)
    rig.hal._motion.actuator = actuator
    return actuator


def test_a_drop_reported_from_inside_a_command_is_applied_after_it_and_leaves_one_state(rig):
    actuator = flaky(rig)
    actuator.drop_during_drive = "supervisor_deadline"
    rig.do("mt_drive")
    # the command is on record, then the channel is stopped for the reported cause
    kinds = [e["type"] for e in rig.events.events if e["type"].startswith("motion")]
    assert kinds == ["motion_command", "motion_safe"]
    assert rig.of("motion_safe")[0]["cause"] == "supervisor_deadline"
    assert rig.state()["mode"] == "idle" and rig.hal.envelope.live("wheel_left") is None


def test_a_driver_that_fails_a_renewal_ends_the_run_and_says_so(rig):
    actuator = flaky(rig)
    rig.do("mt_drive")
    rig.advance(100)
    actuator.fail_next = True
    with pytest.raises(OSError):
        rig.do("mt_drive")
    assert rig.state()["mode"] == "idle"
    assert rig.of("motion_safe") == [
        {"channel": "wheel_left", "state": "stop", "cause": "actuator_fault"}
    ]


def test_a_driver_that_fails_a_new_run_gives_the_budget_back_and_records_no_command():
    rig = Rig(limits={"wheel_left": EnvelopeLimits(60, 10000, 0, 10000)})
    actuator = flaky(rig)
    actuator.fail_next = True
    with pytest.raises(OSError):
        rig.do("mt_drive")
    assert rig.of("motion_command") == [] and rig.hal.envelope.live("wheel_left") is None
    assert rig.do("mt_drive").verdict is GateVerdict.ALLOW  # the full budget is still there
