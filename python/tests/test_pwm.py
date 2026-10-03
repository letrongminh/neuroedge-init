"""
TSK-W1-01 — PWM and the state-feedback channel of `digital.out` on `sim` (RFC-0010, §7).

`sim-rpi5` declares the reference fan: PWM channel `fan` (100..25000 Hz, 10 bits, `max_duty`
0.8, enable line `fan_en`) with a safety envelope. The envelope is given small numbers here, with
a fake clock, so each rule is one assertion. `linux` (a fake `/sys/class/pwm`, the fake gpiod and
the supervisor) is `test_hal_linux_pwm.py`; real kernel lines are `tests_linux/`.
"""

from __future__ import annotations

import itertools
import math
import re
import shutil
import textwrap
from pathlib import Path

import pytest

from neuroedge.engine.compiler import (
    check_capabilities,
    load_agent_manifest,
)
from neuroedge.engine.trace_sink import EventLog
from neuroedge.errors import (
    BoardCapabilityError,
    BuildFailed,
    EnvelopeRefusedError,
    GateSchemaError,
    PerceptionUnavailableError,
)
from neuroedge.hal import HardwareAbstractionLayer
from neuroedge.hal.board import load_board_by_id
from neuroedge.hal.envelope import EnvelopeLimits, SafetyEnvelope
from neuroedge.hal.pwm import MEASURED, quantize_duty
from neuroedge.hal.sim import SimHAL
from neuroedge.sim import SimSession
from neuroedge.testing import TraceRecorder
from neuroedge.testing.golden import safety_view
from neuroedge.testing.player import TracePlayer

BOARD = load_board_by_id("sim-rpi5")
LIMITS = EnvelopeLimits(
    window_s=100, max_on_ms_per_window=1_500, min_interval_ms=0, max_continuous_ms=1_000
)


class Clock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, ms: float) -> None:
        self.now += ms


class Authorizer:
    """`authorize`: counts the tokens it is asked to spend; can be told to refuse."""

    def __init__(self) -> None:
        self.calls = 0
        self.refuse = False

    def __call__(self, signature, pin, called_from) -> None:
        self.calls += 1
        if self.refuse:
            raise PermissionError("the ledger refuses")


def make(limits: EnvelopeLimits = LIMITS, board=BOARD):
    clock = Clock()
    events = EventLog(clock)
    envelope = SafetyEnvelope({"fan": limits}, clock=clock)
    authorize = Authorizer()
    hal = SimHAL(board, events=events, authorize=authorize, envelope=envelope)
    return hal, envelope, events, clock, authorize


def pwm(hal, *, frequency_hz=1000, duty=0.5, duration_ms=500, **kw):
    return hal.digital_out(
        "fan",
        "pwm",
        duration_ms,
        signature="token",
        called_from="actions/fan.py:3",
        frequency_hz=frequency_hz,
        duty=duty,
        **kw,
    )


def untouched(hal, envelope, events, authorize) -> None:
    """Nothing was reserved, no token spent, nothing recorded: a refusal before the envelope."""
    assert authorize.calls == 0
    assert envelope.live("fan") is None
    assert events.of_type("actuator_command") == [] and events.of_type("envelope_refused") == []
    assert hal.pin("fan").never_pulsed()


# --- the board's limits (RFC-0010 §3a, §3b): refused before the envelope and authorize ----------


@pytest.mark.parametrize("operation", ["on", "pulse"])
def test_on_and_pulse_on_a_pwm_channel_are_refused_with_no_token_spent(operation):
    hal, envelope, events, _, authorize = make()
    with pytest.raises(
        BoardCapabilityError, match="a PWM channel takes only 'pwm' and 'off'"
    ) as raised:
        hal.digital_out("fan", operation, 500, signature="token", called_from="actions/fan.py:9")
    assert raised.value.code == "NE3001" and "actions/fan.py:9" in raised.value.where
    untouched(hal, envelope, events, authorize)


def test_pwm_on_a_pin_that_is_not_a_pwm_channel_is_refused():
    hal, _, events, _, authorize = make()
    with pytest.raises(BoardCapabilityError, match="not a PWM channel"):
        hal.digital_out("door_lock", "pwm", 500, "token", "t", frequency_hz=1000, duty=0.5)
    assert authorize.calls == 0 and events.of_type("actuator_command") == []


@pytest.mark.parametrize(
    "change",
    [
        {"duration_ms": 0},
        {"duration_ms": -5},
        {"duration_ms": 1.5},
        {"duration_ms": True},
        {"duration_ms": None},
        {"frequency_hz": None},
        {"frequency_hz": 99},
        {"frequency_hz": 25_001},
        {"frequency_hz": 1000.5},
        {"frequency_hz": True},
        {"duty": None},
        {"duty": -0.1},
        {"duty": 1.1},
        {"duty": 0.81},
        {"duty": math.nan},
        {"duty": math.inf},
        {"duty": True},
        {"duty": "0.5"},
    ],
    ids=repr,
)
def test_a_pwm_command_outside_the_boards_limits_is_refused_with_no_token_spent(change):
    hal, envelope, events, _, authorize = make()
    kwargs = {"frequency_hz": 1000, "duty": 0.5, "duration_ms": 500, **change}
    with pytest.raises(BoardCapabilityError):
        pwm(hal, **kwargs)
    untouched(hal, envelope, events, authorize)


def test_the_boards_ceiling_is_max_duty_and_the_message_says_so():
    hal, *_ = make()
    pwm(hal, duty=0.8)  # exactly the ceiling is allowed
    hal.digital_out("fan", "off")
    with pytest.raises(BoardCapabilityError, match="above max_duty 0.8"):
        pwm(hal, duty=0.8001)


def test_the_enable_line_is_the_hals_and_no_agent_drives_it():
    hal, *_, authorize = make()
    for operation in ("on", "off", "pulse"):
        with pytest.raises(BoardCapabilityError, match="enable line"):
            hal.digital_out("fan_en", operation, 100, "token", "actions/fan.py:4")
    assert authorize.calls == 0 and hal.pins == {}


def test_the_enable_line_is_up_only_while_a_gated_pwm_command_runs():
    hal, envelope, _, clock, _ = make()
    assert not hal.pwm_enabled("fan")
    pwm(hal, duration_ms=400)
    assert hal.pwm_enabled("fan")
    clock.advance(399)
    assert hal.pwm_enabled("fan")
    clock.advance(2)
    assert not hal.pwm_enabled("fan"), "dropped when the time is up"
    pwm(hal, duration_ms=400)
    hal.digital_out("fan", "off")
    assert not hal.pwm_enabled("fan"), "and on off"
    with pytest.raises(BoardCapabilityError):
        pwm(hal, duty=0.9)
    assert not hal.pwm_enabled("fan"), "a refused command never raises it"


# --- quantisation toward zero (§9.15) ---------------------------------------------------------


def test_a_quantised_duty_never_exceeds_the_checked_one_or_max_duty():
    steps = 1 << 10
    duty = 0.0
    while duty <= 0.8:
        applied = quantize_duty(duty, 10)
        assert applied <= duty and applied <= 0.8
        assert (applied * steps).is_integer()
        assert duty - applied < 1 / steps
        duty += 0.000731  # not a multiple of any step
    assert quantize_duty(0.8, 10) == 819 / 1024 < 0.8


def test_the_applied_duty_is_what_the_trace_and_the_pin_record():
    hal, _, events, *_ = make()
    pwm(hal, frequency_hz=2000, duty=0.4)
    assert hal.pin("fan").pwm == [(2000, 409 / 1024)]
    assert hal.pin("fan").commands == [("pwm", 500)]
    assert events.of_type("actuator_command") == [
        {
            "pin": "fan",
            "operation": "pwm",
            "duration_ms": 500,
            "frequency_hz": 2000,
            "duty": 409 / 1024,
        }
    ]


def test_a_duty_that_quantises_to_nothing_is_the_safe_state_and_needs_no_token():
    hal, envelope, events, _, authorize = make()
    pwm(hal)  # running
    authorize.calls = 0
    pwm(hal, duty=0.0005)  # under one step of 1/1024: the channel is off
    assert authorize.calls == 0
    assert not hal.pwm_enabled("fan") and envelope.live("fan") is None
    assert events.of_type("actuator_command")[-1] == {
        "pin": "fan",
        "operation": "off",
        "duration_ms": 0,
        "cause": "duty_zero",
    }
    with pytest.raises(BoardCapabilityError):  # still validated: it is not a way past the limits
        pwm(hal, duty=0.0, frequency_hz=99)


# --- duration, the envelope and the safe direction (§9.3, §9.5–§9.8, RFC-0007 §3d) ---------------


def test_a_command_over_max_continuous_ms_is_refused_whole_with_no_token_spent():
    hal, envelope, events, _, authorize = make()
    with pytest.raises(EnvelopeRefusedError) as raised:
        pwm(hal, duration_ms=1_001)
    assert raised.value.code == "NE1003" and raised.value.reason == "max_continuous_ms"
    assert events.of_type("envelope_refused") == [
        {
            "pin": "fan",
            "operation": "pwm",
            "reason": "max_continuous_ms",
            "limit_ms": 1_000,
            "requested_ms": 1_001,
        }
    ]
    assert authorize.calls == 0 and hal.pin("fan").never_pulsed() and envelope.live("fan") is None
    pwm(hal, duration_ms=1_000)  # at the ceiling is fine


def test_the_whole_time_with_duty_above_zero_counts_not_duty_times_time():
    hal, _, events, clock, _ = make()
    pwm(hal, duty=0.1, duration_ms=1_000)  # a tenth of the power: still 1000 ms of on-time
    clock.advance(1_000)
    with pytest.raises(EnvelopeRefusedError) as raised:
        pwm(hal, duty=0.1, duration_ms=1_000)  # 1000 + 1000 over the window's 1500
    assert raised.value.reason == "window_budget"
    (refused,) = events.of_type("envelope_refused")
    assert refused["used_ms"] == 1_000 and refused["requested_ms"] == 1_000
    assert refused["limit_ms"] == 1_500


def test_the_channel_goes_off_by_itself_when_the_time_is_up():
    hal, envelope, events, clock, _ = make()
    pwm(hal, duration_ms=300)
    assert hal.commanded_pwm("fan") == (1000, 0.5) and envelope.live("fan") is not None
    clock.advance(300)
    assert hal.commanded_pwm("fan") is None
    assert envelope.live("fan") is None
    assert hal.pin_state("fan").values == {"duty": 0.0, "frequency_hz": None}


def test_off_early_gives_back_the_unused_time():
    hal, _, _, clock, _ = make()
    pwm(hal, duration_ms=1_000)
    clock.advance(400)
    hal.digital_out("fan", "off")
    pwm(hal, duration_ms=1_000)  # 400 used + 1000 fits in 1500; it would not without the refund
    clock.advance(1_000)
    with pytest.raises(EnvelopeRefusedError, match="over max_on_ms_per_window"):
        pwm(hal, duration_ms=1_000)  # 400 + 1000 + 1000


def test_an_authorize_that_fails_gives_back_everything_it_held():
    hal, envelope, events, clock, authorize = make()
    authorize.refuse = True
    with pytest.raises(PermissionError):
        pwm(hal, duration_ms=1_000)
    assert envelope.live("fan") is None
    assert hal.pin("fan").never_pulsed() and events.of_type("actuator_command") == []
    assert not hal.pwm_enabled("fan")
    authorize.refuse = False
    pwm(hal, duration_ms=1_000)  # the full budget is still there
    clock.advance(1_000)
    pwm(hal, duration_ms=500)


def test_off_is_never_blocked_even_inside_min_interval_ms():
    hal, _, events, clock, authorize = make(
        EnvelopeLimits(
            window_s=100,
            max_on_ms_per_window=10_000,
            min_interval_ms=5_000,
            max_continuous_ms=1_000,
        )
    )
    pwm(hal, duration_ms=800)
    clock.advance(10)
    authorize.calls = 0
    hal.digital_out("fan", "off")  # straight after the on: no envelope, no token, no wait
    assert authorize.calls == 0 and not hal.pwm_enabled("fan")
    with pytest.raises(EnvelopeRefusedError) as raised:
        pwm(hal, duration_ms=100)  # min_interval_ms holds back the next on only
    assert raised.value.reason == "min_interval_ms"
    hal.digital_out("fan", "off")


def test_a_second_pwm_command_while_one_runs_is_refused_not_restarted():
    hal, *_ = make()
    pwm(hal, duration_ms=800)
    with pytest.raises(EnvelopeRefusedError) as raised:
        pwm(hal, duty=0.7, duration_ms=800)
    assert raised.value.reason == "already_on"
    assert hal.commanded_pwm("fan") == (1000, 0.5), "the running command is untouched"


def test_a_pwm_command_cannot_be_scheduled():
    hal, *_, authorize = make()
    hal.enable_scheduling(lambda: 0.0)
    with pytest.raises(BoardCapabilityError, match="cannot be scheduled"):
        pwm(hal, delay_ms=100)
    assert authorize.calls == 0


def test_close_ends_every_on_time():
    hal, envelope, *_ = make()
    pwm(hal)
    hal.close()
    assert envelope.live("fan") is None


# --- state() and the read-back (§3b, §9.4, §9.12) -------------------------------------------


def test_the_state_of_a_pin_with_no_read_back_is_what_was_commanded():
    hal, _, events, *_ = make()
    pwm(hal, frequency_hz=1000, duty=0.5)
    state = hal.pin_state("fan", called_from="actions/fan.py:12", use="fact")
    assert (state.source, state.duty, state.frequency_hz) == ("commanded", 0.5, 1000.0)
    assert events.of_type("pin_state") == [
        {"pin": "fan", "source": "commanded", "duty": 0.5, "frequency_hz": 1000.0, "use": "fact"}
    ]


def test_a_pin_the_board_gives_a_read_back_is_measured_not_commanded(feedback_board):
    hal, _, events, *_ = make(board=feedback_board)
    pwm(hal, duty=0.5)
    hal.set_feedback("fan", duty=0.41, frequency_hz=990)  # the fan is not doing what it was told
    state = hal.pin_state("fan")
    assert state.source == MEASURED == "measured"
    assert (state.duty, state.frequency_hz) == (0.41, 990.0)
    assert events.of_type("pin_state")[-1]["source"] == "measured"
    hal.clear_feedback("fan")
    assert hal.pin_state("fan").duty == 0.5


def test_a_read_back_that_fails_is_ne5001_and_never_the_commanded_value(feedback_board):
    hal, _, events, *_ = make(board=feedback_board)
    pwm(hal, duty=0.5)
    hal.set_feedback("fan", fail="the tach wire is cut")
    with pytest.raises(PerceptionUnavailableError, match="tach wire") as raised:
        hal.pin_state("fan", called_from="actions/fan.py:12")
    assert raised.value.code == "NE5001"
    assert events.of_type("pin_state") == [{"pin": "fan", "reason": raised.value.why}]


def test_there_is_no_read_back_to_set_where_the_board_has_none():
    hal, *_ = make()
    with pytest.raises(BoardCapabilityError, match="declares no feedback"):
        hal.set_feedback("fan", duty=0.3)


def test_state_reads_back_a_pwm_channel_and_nothing_else():
    hal, *_ = make()
    with pytest.raises(BoardCapabilityError, match="not a PWM channel"):
        hal.pin_state("door_lock")
    with pytest.raises(BoardCapabilityError, match="enable line"):
        hal.pin_state("fan_en")


def test_a_target_with_no_read_back_yet_says_so(feedback_board):
    hal = HardwareAbstractionLayer(board=feedback_board, target="esp32s3")
    with pytest.raises(BoardCapabilityError, match="not implemented on target 'esp32s3'"):
        hal.pin_state("fan")


def test_replay_feeds_the_recorded_state_back_with_its_source():
    hal, *_ = make()
    hal.script_pin_state(
        "fan",
        [{"source": "measured", "duty": 0.25, "frequency_hz": 800.0}, None],
    )
    first = hal.pin_state("fan")
    assert (first.source, first.duty, first.frequency_hz) == ("measured", 0.25, 800.0)
    with pytest.raises(PerceptionUnavailableError, match="holds no state"):
        hal.pin_state("fan")  # the recorded read that failed fails again
    with pytest.raises(PerceptionUnavailableError):
        hal.pin_state("fan")  # and reading past the end is a failed read, not the last value


def test_a_pwm_command_is_part_of_the_golden_safety_view():
    def trace(duty):
        hal, _, events, *_ = make()
        pwm(hal, duty=duty)
        return {"events": events.to_trace()["events"]}

    assert safety_view(trace(0.5)) == safety_view(trace(0.5))
    assert safety_view(trace(0.5)) != safety_view(trace(0.6)), "a higher duty is a regression"
    (command,) = safety_view(trace(0.5))["actuators"]
    assert command["frequency_hz"] == 1000 and command["duty"] == 0.5


# --- the agent: [requires], the @action API, the gate, replay ------------------------------


FAN = Path(__file__).resolve().parents[2] / "fixtures" / "agents" / "fan-pwm"


def test_requires_names_the_pwm_channels_the_board_declares():
    manifest = load_agent_manifest(FAN / "agent.toml")
    assert manifest.requires["digital.out"] == {"pins": ["fan"], "pwm": ["fan"]}
    for board in ("sim-rpi5", "linux-rpi5"):
        assert check_capabilities(manifest, load_board_by_id(board)) == []
    problems = check_capabilities(manifest, load_board_by_id("sim-default"))
    assert {p.where.split("[requires] ")[1] for p in problems} == {
        "digital.out:fan",
        "digital.out pwm:fan",
    }
    assert all("sim-default" in p.why for p in problems)


def manifest_with(tmp_path, requires: str):
    path = tmp_path / "agent.toml"
    path.write_text(
        f'[agent]\nname = "x"\nversion = "0.0.1"\n\n[requires]\n{requires}\n', encoding="utf-8"
    )
    return load_agent_manifest(path)


@pytest.mark.parametrize(
    ("requires", "why"),
    [
        (
            '"digital.out" = { pins = ["door_lock"], pwm = ["door_lock"] }',
            "digital.out pwm:door_lock",
        ),
        ('"digital.out" = { pins = ["fan"], pwm = ["fan_en"] }', "digital.out pwm:fan_en"),
        ('"digital.out" = { pins = ["door_lock"], pwm = ["fan"] }', "not in this agent's"),
        ('"digital.out" = { pins = ["fan"], pwm = "fan" }', "must be a list of PWM channel names"),
        ('"digital.out" = { pins = ["fan"], pwm = [1] }', "must be a list of PWM channel names"),
    ],
)
def test_a_pwm_requirement_the_board_or_the_agent_cannot_meet_is_a_build_error(
    tmp_path, requires, why
):
    problems = check_capabilities(manifest_with(tmp_path, requires), BOARD)
    assert problems
    assert any(why in p.where or why in p.why for p in problems)


_copies = itertools.count(1)


def copy_agent(tmp_path) -> tuple[Path, str]:
    """
    A private copy of fan-pwm. Actions register by name in one process-wide registry, so a copy
    gets its own names (`fan_run_3`); the manifest-local gate keys stay as they are.
    """
    tag = f"_{next(_copies)}"
    folder = tmp_path / "agent"
    shutil.copytree(FAN, folder)
    for path in (folder / "actions").glob("*.py"):
        path.write_text(
            re.sub(r'name="(\w+)"', rf'name="\1{tag}"', path.read_text(encoding="utf-8")),
            encoding="utf-8",
        )
    commands = folder / "commands.toml"
    commands.write_text(
        re.sub(
            r'tool     = "(\w+)"', rf'tool     = "\1{tag}"', commands.read_text(encoding="utf-8")
        ),
        encoding="utf-8",
    )
    return folder, tag


@pytest.fixture
def session():
    return SimSession.load(FAN / "agent.toml", board_id="sim-rpi5")


async def test_an_action_runs_the_fan_through_its_gate(session):
    result = await session.call_tool(
        _call("fan_run", duty=0.5, frequency_hz=1000, duration_ms=5000)
    )
    assert result.status == "ALLOW"
    (command,) = session.events.of_type("actuator_command")
    assert command == {
        "pin": "fan",
        "operation": "pwm",
        "duration_ms": 5000,
        "frequency_hz": 1000,
        "duty": 0.5,
    }
    assert session.hal.pwm_enabled("fan")
    stop = await session.call_tool(_call("fan_stop", source="local_grammar"))
    assert stop.status == "ALLOW" and not session.hal.pwm_enabled("fan")
    assert "cause" not in session.events.of_type("actuator_command")[-1]


def _call(name, source="mcp", **arguments):
    from neuroedge.actions.tools import ToolCall

    return ToolCall(name, arguments, source)


@pytest.mark.parametrize(
    ("arguments", "criterion"),
    [
        ({"duty": 0.7, "frequency_hz": 1000, "duration_ms": 5000}, "duty"),
        ({"duty": 0.4, "frequency_hz": 150, "duration_ms": 5000}, "frequency_hz"),
        ({"duty": 0.4, "frequency_hz": 1000, "duration_ms": 20_000}, "duration_ms"),
    ],
)
async def test_a_value_outside_the_gates_limits_is_blocked_and_the_fan_does_not_move(
    session, arguments, criterion
):
    result = await session.call_tool(_call("fan_run", **arguments))
    content = result.content()
    assert (content["status"], content["reason"]) == ("BLOCK", "argument_out_of_range")
    assert content["failed_criterion"] == criterion
    assert session.hal.pin("fan").never_pulsed() and not session.hal.pwm_enabled("fan")


async def test_a_call_that_leaves_out_the_duration_is_rejected(session):
    result = await session.call_tool(_call("fan_run", duty=0.4, frequency_hz=1000))
    assert result.status == "REJECTED"
    assert session.hal.pin("fan").never_pulsed()


async def test_the_default_of_an_action_parameter_is_checked_too(tmp_path):
    folder, tag = copy_agent(tmp_path)
    action = folder / "actions" / "fan.py"
    action.write_text(
        action.read_text(encoding="utf-8")
        .replace("duty: float, frequency", "duty: float = 0.7, frequency")
        .replace(
            "frequency_hz: int, duration_ms: int",
            "frequency_hz: int = 1000, duration_ms: int = 500",
        ),
        encoding="utf-8",
    )
    session = SimSession.load(folder / "agent.toml", board_id="sim-rpi5")
    result = await session.call_tool(_call(f"fan_run{tag}"))
    assert result.content()["reason"] == "argument_out_of_range"  # 0.7 > the gate's 0.6
    assert session.hal.pin("fan").never_pulsed()


async def test_a_recorded_fan_session_replays_to_the_same_commands():
    recorder = TraceRecorder()
    live = SimSession.load(FAN / "agent.toml", board_id="sim-rpi5", events=recorder)
    await live.call_tool(_call("fan_run", duty=0.5, frequency_hz=1000, duration_ms=5000))
    await live.call_tool(_call("fan_stop", source="local_grammar"))
    trace = recorder.to_trace()
    result = await TracePlayer(trace, agent=FAN / "agent.toml", board_id="sim-rpi5").replay()
    assert safety_view(result.replayed) == safety_view(trace)
    assert [c["operation"] for c in safety_view(trace)["actuators"]] == ["pwm", "off"]


# --- feedback as a numeric fact the gate reads (§9.12) -------------------------------------


def feedback_agent(tmp_path, unit="ratio", allow="lt: 0.5", extra=""):
    """fan-pwm plus a gate `fan_boost` that reads the measured duty, and the rule feeding it."""
    folder, tag = copy_agent(tmp_path)
    (folder / "gates" / "fan_boost@1.0.0.yaml").write_text(
        textwrap.dedent(
            f"""\
            schema:  neuroedge.gate/v1
            name:    fan_boost
            version: 1.0.0
            evaluate:
              fan_duty:
                type: numeric
                unit: {unit}
                range: {{ min: 0, max: 0.8 }}
                max_age_ms: 5000
                instructions: "Duty đo được của quạt"
            allow_when:
              fan_duty: {{ {allow} }}
            on_block:
              action: deny
            budget:
              p95_latency_ms: 150
              fail: closed
            """
        ),
        encoding="utf-8",
    )
    (folder / "actions" / "boost.py").write_text(
        textwrap.dedent(
            f"""\
            from neuroedge import action, digital


            @action(name="fan_boost{tag}", requires="digital.out:fan", gate="fan_boost")
            def fan_boost() -> None:
                digital.out("fan").pwm(frequency_hz=1000, duty=0.7, ms=500)


            @action(name="fan_probe{tag}", requires="digital.out:fan", gate="fan_stop")
            def fan_probe() -> None:
                digital.out("fan").state()
            """
        ),
        encoding="utf-8",
    )
    text = (folder / "agent.toml").read_text(encoding="utf-8")
    text = text.replace(
        'fan_stop = "gates/fan_stop@1.0.0.yaml"',
        'fan_stop = "gates/fan_stop@1.0.0.yaml"\nfan_boost = "gates/fan_boost@1.0.0.yaml"',
    )
    text += '\n[sim.feedback_facts]\nfan_duty = { pin = "fan", quantity = "duty" }\n' + extra
    (folder / "agent.toml").write_text(text, encoding="utf-8")
    return folder / "agent.toml"


async def boost(session):
    session.events.events.clear()
    tag = next(n for n in session.tools.specs if n.startswith("fan_boost"))[len("fan_boost") :]
    result = await session.call_tool(_call(f"fan_boost{tag}", source="mcp"))
    facts = session.events.of_type("gate_facts")
    return result.content(), facts[-1]["fan_duty"] if facts else None


async def test_a_commanded_duty_never_reaches_the_gate(tmp_path):
    session = SimSession.load(
        feedback_agent(tmp_path), board_id="sim-rpi5"
    )  # no read-back declared
    session.hal.authorize = lambda *_: None  # this test is about facts, not tokens
    session.hal.digital_out("fan", "pwm", 500, "token", "t", frequency_hz=1000, duty=0.3)
    content, fact = await boost(session)
    assert (content["status"], content["reason"]) == ("BLOCK", "criterion_unavailable")
    assert fact["value"] is None, "the commanded 0.3 was not offered as a measurement"
    assert session.events.of_type("pin_state")[-1]["source"] == "commanded"


async def test_a_measured_duty_decides_the_gate_and_a_failed_read_back_blocks_it(
    tmp_path, feedback_board
):
    session = SimSession.load(feedback_agent(tmp_path), board_id="sim-rpi5")
    session.hal.set_feedback("fan", duty=0.3)
    content, fact = await boost(session)
    assert content["status"] == "ALLOW", content
    assert fact["value"] == 0.3 and "age_ms" in fact and fact["age_ms"] >= 0
    session.hal.digital_out("fan", "off")
    session.hal.set_feedback("fan", duty=0.7)
    content, _ = await boost(session)
    assert (content["status"], content["reason"]) == ("BLOCK", "condition_not_met")
    session.hal.set_feedback("fan", fail="no signal")
    content, fact = await boost(session)
    assert (content["status"], content["reason"]) == ("BLOCK", "criterion_unavailable")
    assert fact["value"] is None
    assert session.events.of_type("pin_state")[-1] == {
        "pin": "fan",
        "reason": session.events.of_type("pin_state")[-1]["reason"],
        "use": "fact",
    }


@pytest.mark.parametrize(
    ("unit", "why"),
    [("percent", "'percent'"), ("ratio", None)],
)
def test_build_checks_the_unit_and_the_range_of_a_read_back_criterion(tmp_path, unit, why):
    from neuroedge.engine.compiler import build

    agent = feedback_agent(tmp_path, unit=unit)
    if why is None:
        build(agent, target="sim", board_id="sim-rpi5", out_dir=tmp_path / "out")
        return
    with pytest.raises(BuildFailed) as raised:
        build(agent, target="sim", board_id="sim-rpi5")
    (problem,) = raised.value.problems
    assert isinstance(problem, BoardCapabilityError) and why in problem.why


def test_build_refuses_a_criterion_range_narrower_than_the_channels_scale(tmp_path):
    from neuroedge.engine.compiler import build

    agent = feedback_agent(tmp_path)
    gate = agent.parent / "gates" / "fan_boost@1.0.0.yaml"
    gate.write_text(
        gate.read_text(encoding="utf-8").replace("max: 0.8", "max: 0.5"), encoding="utf-8"
    )
    with pytest.raises(BuildFailed) as raised:
        build(agent, target="sim", board_id="sim-rpi5")
    (problem,) = raised.value.problems
    assert "not inside the range [0, 0.5]" in problem.why


def test_a_feedback_rule_must_name_a_channel_the_agent_requires(tmp_path):
    from neuroedge.engine.compiler import build

    agent = feedback_agent(tmp_path)
    agent.write_text(
        agent.read_text(encoding="utf-8").replace(', pwm = ["fan"]', ""), encoding="utf-8"
    )
    with pytest.raises(BuildFailed) as raised:
        build(agent, target="sim", board_id="sim-rpi5")
    assert any(
        "not one [requires] declares under digital.out `pwm`" in p.why
        for p in raised.value.problems
    )


def test_a_read_back_criterion_cannot_be_waived_by_a_person(tmp_path):
    from neuroedge.engine.compiler import build

    agent = feedback_agent(tmp_path)
    gate = agent.parent / "gates" / "fan_boost@1.0.0.yaml"
    gate.write_text(
        gate.read_text(encoding="utf-8").replace(
            "on_block:\n  action: deny",
            "on_block:\n  action: ask\n  message: Chắc chưa?\n  confirms: [fan_duty]",
        ),
        encoding="utf-8",
    )
    with pytest.raises(BuildFailed) as raised:
        build(agent, target="sim", board_id="sim-rpi5")
    assert any(
        isinstance(p, GateSchemaError) and p.code == "NE2002" for p in raised.value.problems
    ), "a person's yes cannot stand in for a measurement (RFC-0010 §9.12)"


async def test_replay_feeds_back_a_measured_state_with_its_source(tmp_path, feedback_board):
    agent = feedback_agent(tmp_path)
    recorder = TraceRecorder()
    live = SimSession.load(agent, board_id="sim-rpi5", events=recorder)
    live.hal.set_feedback("fan", duty=0.3, frequency_hz=900)
    tag = next(n for n in live.tools.specs if n.startswith("fan_probe"))
    assert (await live.call_tool(_call(tag, source="mcp"))).status == "ALLOW"
    trace = recorder.to_trace()

    def reads(
        events,
    ):  # what the action read; the gate's own fact reads (`use: fact`) are not replayed
        return [e["data"] for e in events if e["type"] == "pin_state" and "use" not in e["data"]]

    recorded = reads(trace["events"])
    assert recorded == [{"pin": "fan", "source": "measured", "duty": 0.3, "frequency_hz": 900}]
    # The replaying HAL has no hardware and was never told 0.3: the number comes from the trace.
    result = await TracePlayer(trace, agent=agent, board_id="sim-rpi5").replay()
    assert reads(result.replayed["events"]) == recorded


def test_a_pwm_command_is_written_ahead_and_a_restart_keeps_its_time(tmp_path):
    from neuroedge.hal.envelope import FileEnvelopeStore

    store = FileEnvelopeStore(tmp_path / "state")
    clock = Clock()
    first = SafetyEnvelope({"fan": LIMITS}, clock=clock, store=store, init_store=True)
    hal = SimHAL(BOARD, events=EventLog(clock), authorize=Authorizer(), envelope=first)
    pwm(hal, duration_ms=1_000)
    assert store.load("fan") == [1_000.0], "recorded before the channel is up, as its reserved time"
    # A restart: no clock is trusted across boots, so the recorded on-time still holds the window
    # and the channel waits min_interval_ms (none here) before its first on.
    clock2 = Clock()
    again = SafetyEnvelope({"fan": LIMITS}, clock=clock2, store=store)
    hal2 = SimHAL(BOARD, events=EventLog(clock2), authorize=Authorizer(), envelope=again)
    with pytest.raises(EnvelopeRefusedError, match="over max_on_ms_per_window"):
        pwm(hal2, duration_ms=1_000)  # 1000 recorded + 1000 over the window's 1500
    pwm(hal2, duration_ms=500)
    # A record that is gone or damaged is a spent window, never an open one.
    (tmp_path / "state" / "fan.json").write_text("not json", encoding="utf-8")
    broken = SafetyEnvelope({"fan": LIMITS}, clock=Clock(), store=store)
    hal3 = SimHAL(BOARD, events=EventLog(Clock()), authorize=Authorizer(), envelope=broken)
    with pytest.raises(EnvelopeRefusedError) as raised:
        pwm(hal3, duration_ms=100)
    assert raised.value.reason == "window_unreadable"
    hal3.digital_out("fan", "off")  # and off still works


def test_a_hal_with_no_board_cannot_check_a_pwm_command_so_it_refuses_it():
    hal = HardwareAbstractionLayer(authorize=Authorizer())
    with pytest.raises(BoardCapabilityError, match="has no board"):
        hal.digital_out("fan", "pwm", 500, "token", "t", frequency_hz=1000, duty=0.5)
