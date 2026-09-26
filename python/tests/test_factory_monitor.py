"""
The factory-monitor sample (TSK-S3-08): physical actions gated on one `level` fact.

The heat band of the machine room (`low · normal · high · critical`) comes from
the `temperature` sensor on `sim`. `gate_relay` is the fan, `porch_light` the
alarm beacon; every assertion is on those pins.

* vent_on / alarm_on — allowed at any band;
* vent_off           — allowed up to `normal`, asks at `high` (RFC-0006), refused
                       without a question at `critical`;
* alarm_off          — refused above `normal`.
"""

from __future__ import annotations

import asyncio

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.engine import resolve_gate_file
from neuroedge.sim import SimSession
from neuroedge.testing import TracePlayer, assert_matches_golden
from neuroedge.testing.recorder import TraceRecorder

runner = CliRunner()
LEVELS = ["low", "normal", "high", "critical"]


@pytest.fixture(scope="module")
def sample(root):
    return root / "fixtures" / "agents" / "factory-monitor"


@pytest.fixture(scope="module")
def agent(sample):
    return sample / "agent.toml"


def session_for(agent, heat=None, *, events=None):
    session = SimSession.load(agent, events=events)
    if heat is not None:
        session.set_sensor("temperature", heat)
    return session


def say(session, *lines):
    return [asyncio.run(session.handle(line)) for line in lines]


# --- the gates are level gates -----------------------------------------------------------


@pytest.mark.parametrize("gate", ["vent_off", "alarm_off"])
def test_the_heat_criterion_is_a_level_not_a_number(sample, gate):
    resolved = resolve_gate_file(sample / "gates" / f"{gate}@1.0.0.yaml")
    assert resolved.evaluate["heat_level"] == {
        "type": "level",
        "levels": LEVELS,
        "instructions": resolved.evaluate["heat_level"]["instructions"],
    }
    assert resolved.constraints["heat_level"].admitted == frozenset({"low", "normal"})
    assert resolved.fails_closed


def test_sim_starts_hot(agent):
    session = session_for(agent)
    assert session.hal.sensor_values()["temperature"] == ("high", None)


# --- the fan -----------------------------------------------------------------------------


@pytest.mark.parametrize("heat", LEVELS)
def test_the_fan_starts_at_any_heat(agent, heat):
    session = session_for(agent, heat)
    (turn,) = say(session, "bật quạt")
    assert turn.allowed
    assert session.hal.pin("gate_relay").commands == [("on", 0)]


@pytest.mark.parametrize("heat", ["low", "normal"])
def test_the_fan_stops_when_the_room_is_cool(agent, heat):
    session = session_for(agent, heat)
    say(session, "bật quạt", "tắt quạt")
    assert session.hal.pin("gate_relay").commands == [("on", 0), ("off", 0)]


def test_at_high_heat_stopping_the_fan_asks_an_operator(agent):
    session = session_for(agent, "high")
    _, off = say(session, "bật quạt", "tắt quạt")
    assert off.result.blocked
    assert off.result.gate.failed_criterion == "heat_level"
    assert off.result.gate.on_block_action == "ask"
    assert off.reply_source == "gate_ask"
    assert off.confirmation is not None
    assert off.confirmation.confirms == ("heat_level",)
    assert session.hal.pin("gate_relay").commands == [("on", 0)]


def test_an_operators_yes_stops_the_fan_and_is_recorded(agent):
    session = session_for(agent, "high")
    *_, yes = say(session, "bật quạt", "tắt quạt", "có")
    assert yes.allowed
    assert yes.result.gate.confirmed == ("heat_level",)
    assert session.hal.pin("gate_relay").commands == [("on", 0), ("off", 0)]


def test_an_operators_no_keeps_the_fan_running(agent):
    session = session_for(agent, "high")
    say(session, "bật quạt", "tắt quạt", "không")
    assert session.hal.pin("gate_relay").commands == [("on", 0)]


def test_at_critical_heat_the_fan_cannot_be_stopped_and_nothing_is_asked(agent):
    session = session_for(agent, "critical")
    _, off, _ = say(session, "bật quạt", "tắt quạt", "có")
    assert off.result.blocked
    assert off.confirmation is None  # a yes would not be enough: heat_critical still fails
    assert session.conversation.confirmations.latest() is None
    assert session.hal.pin("gate_relay").commands == [("on", 0)]


# --- the alarm ---------------------------------------------------------------------------


@pytest.mark.parametrize("heat", LEVELS)
def test_the_alarm_can_always_be_raised(agent, heat):
    session = session_for(agent, heat)
    (turn,) = say(session, "bật báo động")
    assert turn.allowed
    assert session.hal.pin("porch_light").commands == [("on", 0)]


@pytest.mark.parametrize("heat", ["high", "critical"])
def test_the_alarm_cannot_be_silenced_while_the_room_is_hot(agent, heat):
    session = session_for(agent, heat)
    _, off = say(session, "bật báo động", "tắt báo động")
    assert off.result.blocked
    assert off.result.gate.failed_criterion == "heat_level"
    assert off.result.gate.on_block_action == "deny"
    assert off.confirmation is None
    assert session.hal.pin("porch_light").commands == [("on", 0)]


def test_the_alarm_is_silenced_once_the_room_cools(agent):
    session = session_for(agent, "high")
    say(session, "bật báo động", "tắt báo động")
    session.set_sensor("temperature", "normal")
    (off,) = say(session, "tắt báo động")
    assert off.allowed
    assert session.hal.pin("porch_light").commands == [("on", 0), ("off", 0)]


def test_an_unknown_band_is_not_a_cool_room(agent):
    session = session_for(agent, 21.5)  # a raw reading, not a band: fail closed
    (off,) = say(session, "tắt báo động")
    assert off.result.blocked
    assert session.hal.pin("porch_light").never_pulsed()


# --- trace, replay, CLI ------------------------------------------------------------------


async def test_a_recorded_session_replays_to_the_same_decisions(agent):
    recorder = TraceRecorder()
    session = session_for(agent, events=recorder)
    for line in ("bật quạt", "tắt báo động"):
        await session.handle(line)
    session.set_sensor("temperature", "normal")
    await session.handle("tắt quạt")
    trace = recorder.to_trace()
    result = await TracePlayer(trace, agent=agent).replay()
    assert result.verdicts == ["ALLOW", "BLOCK", "ALLOW"]
    assert_matches_golden(result, trace)


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("bật quạt", "ALLOW vent_on@1.0.0"),
        ("tắt quạt", "BLOCK vent_off@1.0.0"),
        ("tắt báo động", "BLOCK alarm_off@1.0.0"),
    ],
)
def test_the_readme_commands_run_offline(agent, command, expected):
    result = runner.invoke(app, ["run", "--agent", str(agent), "-c", command])
    assert result.exit_code == 0, result.output
    assert expected in result.output
