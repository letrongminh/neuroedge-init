"""
The greenhouse sample (`fixtures/agents/greenhouse`) on the virtual board `sim-virtual`
(docs/spec/virtual_parts.md, Q-84) and its demo (`demo/i2d-nha-kinh/`).

Four relays (`exhaust_fan`, `heater`, `mist_pump`, `grow_light`), a roof-vent servo (`roof_vent`)
and three sensors, all declared by the agent itself:

* gh_heater_on  — refused when the air is hot (>= 30 C), or with no reading;
* gh_fan_off    — refused while very hot (>= 35 C), or with no reading;
* gh_mist_on    — refused when the humidity is >= 90 %, or with no reading;
* gh_vent_close — refused while very hot (>= 35 C), or with no reading;
* heater off, fan on, mist off, vent open and the light — always allowed.
"""

from __future__ import annotations

import asyncio
import sys

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.errors import NeuroEdgeError
from neuroedge.paths import repo_root
from neuroedge.sim import SimSession

ROOT = repo_root()
AGENT = ROOT / "fixtures" / "agents" / "greenhouse" / "agent.toml"
runner = CliRunner()

HOT = [30, 30.001, 34.9, 40]  # air_hot from 30 C
COOL = [10, 25, 29.999]
VERY_HOT = [35, 35.001, 45]
NOT_VERY_HOT = [20, 30, 34.999]
NOT_A_READING = ["lỗi", float("nan"), True]
HUMID = [90, 90.001, 100]
DRY = [0, 60, 89.999]


@pytest.fixture(autouse=True)
def own_actions():
    """The agent registers its @actions process-wide; put the registry back after each test."""
    from neuroedge.actions import REGISTRY

    saved, modules = dict(REGISTRY), set(sys.modules)
    yield
    REGISTRY.clear()
    REGISTRY.update(saved)
    for module in set(sys.modules) - modules:
        if module.startswith("neuroedge_agent_"):
            del sys.modules[module]


def session_for(*, temp=None, humidity=None) -> SimSession:
    session = SimSession.load(AGENT)
    if temp is not None:
        session.set_sensor("air_temp", temp)
    if humidity is not None:
        session.set_sensor("air_humidity", humidity)
    return session


def say(session: SimSession, line: str):
    return asyncio.run(session.handle(line))


def commands(session: SimSession, pin: str) -> list[str]:
    return [operation for operation, _ in session.hal.pin(pin).commands]


def blocked_by(turn, fact: str) -> None:
    assert turn.result.blocked
    assert turn.result.gate.failed_criterion == fact
    assert turn.result.gate.on_block_action == "deny"


# --- the board ---------------------------------------------------------------------------


def test_the_greenhouse_runs_on_the_virtual_board_and_says_so():
    session = SimSession.load(AGENT)
    try:
        line = session.virtual_board.startup_line()
        assert line.startswith("risk=virtual_board added:")
        for added in (
            "exhaust_fan",
            "heater",
            "mist_pump",
            "grow_light",
            "roof_vent",
            "air_temp",
            "air_humidity",
            "soil_moisture",
        ):
            assert added in line
        assert "roof_vent" in session.hal.motion_values()
    finally:
        session.hal.close()


def test_every_part_is_declared_and_labelled_in_vietnamese():
    session = SimSession.load(AGENT)
    try:
        assert session.hal.sensor_values().keys() >= {"air_temp", "air_humidity", "soil_moisture"}
    finally:
        session.hal.close()
    import tomllib

    manifest = tomllib.loads(AGENT.read_text(encoding="utf-8"))
    parts = manifest["sim"]["parts"]
    assert {name: part["kind"] for name, part in parts.items()} == {
        "exhaust_fan": "fan",
        "heater": "heater",
        "mist_pump": "pump",
        "roof_vent": "servo",
        "grow_light": "light",
        "air_temp": "temperature",
        "air_humidity": "humidity",
        "soil_moisture": "humidity",
    }
    assert parts["roof_vent"]["label"] == "Cửa mái"
    assert parts["exhaust_fan"]["label"] == "Quạt hút"


# --- the heater ----------------------------------------------------------------------------


@pytest.mark.parametrize("temp", COOL)
def test_the_heater_comes_on_while_the_air_is_not_hot(temp):
    session = session_for(temp=temp)
    assert say(session, "bật sưởi").allowed
    assert commands(session, "heater") == ["on"]


@pytest.mark.parametrize("temp", HOT)
def test_the_heater_never_comes_on_in_hot_air(temp):
    session = session_for(temp=temp)
    blocked_by(say(session, "bật sưởi"), "air_hot")
    assert commands(session, "heater") == []


@pytest.mark.parametrize("temp", NOT_A_READING, ids=repr)
def test_without_a_reading_the_heater_stays_off(temp):
    session = session_for(temp=temp)
    turn = say(session, "bật sưởi")
    assert turn.result.blocked and turn.result.gate.reason == "criterion_unavailable"
    assert commands(session, "heater") == []


@pytest.mark.parametrize("temp", [*COOL, *HOT, *NOT_A_READING], ids=repr)
def test_the_heater_can_always_be_turned_off(temp):
    session = session_for(temp=temp)
    assert say(session, "tắt sưởi").allowed
    assert commands(session, "heater") == ["off"]


# --- the exhaust fan -----------------------------------------------------------------------


@pytest.mark.parametrize("temp", NOT_VERY_HOT)
def test_the_fan_can_be_turned_off_when_it_is_not_very_hot(temp):
    session = session_for(temp=temp)
    assert say(session, "tắt quạt").allowed
    assert commands(session, "exhaust_fan") == ["off"]


@pytest.mark.parametrize("temp", VERY_HOT)
def test_the_fan_is_not_turned_off_while_very_hot(temp):
    session = session_for(temp=temp)
    blocked_by(say(session, "tắt quạt"), "air_very_hot")
    assert commands(session, "exhaust_fan") == []


@pytest.mark.parametrize("temp", NOT_A_READING, ids=repr)
def test_without_a_reading_the_fan_is_not_turned_off(temp):
    session = session_for(temp=temp)
    turn = say(session, "tắt quạt")
    assert turn.result.blocked and turn.result.gate.reason == "criterion_unavailable"
    assert commands(session, "exhaust_fan") == []


@pytest.mark.parametrize("temp", [*NOT_VERY_HOT, *VERY_HOT, *NOT_A_READING], ids=repr)
def test_the_fan_can_always_be_turned_on(temp):
    session = session_for(temp=temp)
    assert say(session, "bật quạt").allowed
    assert commands(session, "exhaust_fan") == ["on"]


# --- the misting pump ----------------------------------------------------------------------


@pytest.mark.parametrize("humidity", DRY)
def test_the_mist_runs_while_the_air_is_not_humid(humidity):
    session = session_for(humidity=humidity)
    assert say(session, "phun sương").allowed
    assert commands(session, "mist_pump") == ["on"]


@pytest.mark.parametrize("humidity", HUMID)
def test_the_mist_does_not_run_in_humid_air(humidity):
    session = session_for(humidity=humidity)
    blocked_by(say(session, "phun sương"), "air_humid")
    assert commands(session, "mist_pump") == []


@pytest.mark.parametrize("humidity", NOT_A_READING, ids=repr)
def test_without_a_reading_the_mist_does_not_run(humidity):
    session = session_for(humidity=humidity)
    turn = say(session, "phun sương")
    assert turn.result.blocked and turn.result.gate.reason == "criterion_unavailable"
    assert commands(session, "mist_pump") == []


@pytest.mark.parametrize("humidity", [*DRY, *HUMID, *NOT_A_READING], ids=repr)
def test_the_mist_can_always_be_turned_off(humidity):
    session = session_for(humidity=humidity)
    assert say(session, "tắt phun sương").allowed
    assert commands(session, "mist_pump") == ["off"]


# --- the roof vent (servo) -----------------------------------------------------------------


@pytest.mark.parametrize("temp", NOT_VERY_HOT)
def test_the_vent_closes_when_it_is_not_very_hot(temp):
    session = session_for(temp=temp)
    assert say(session, "đóng cửa mái").allowed


@pytest.mark.parametrize("temp", VERY_HOT)
def test_the_vent_is_not_closed_while_very_hot(temp):
    session = session_for(temp=temp)
    blocked_by(say(session, "đóng cửa mái"), "air_very_hot")


@pytest.mark.parametrize("temp", NOT_A_READING, ids=repr)
def test_without_a_reading_the_vent_is_not_closed(temp):
    session = session_for(temp=temp)
    turn = say(session, "đóng cửa mái")
    assert turn.result.blocked and turn.result.gate.reason == "criterion_unavailable"


@pytest.mark.parametrize("temp", [*NOT_VERY_HOT, *VERY_HOT, *NOT_A_READING], ids=repr)
def test_the_vent_can_always_be_opened(temp):
    session = session_for(temp=temp)
    assert say(session, "mở cửa mái").allowed


# --- the grow light is free --------------------------------------------------------------


@pytest.mark.parametrize("temp", [*COOL, *HOT, *NOT_A_READING], ids=repr)
def test_the_grow_light_is_free(temp):
    session = session_for(temp=temp)
    assert say(session, "bật đèn").allowed
    assert commands(session, "grow_light") == ["on"]


# --- a typed value stays inside the part's range -----------------------------------------


@pytest.mark.parametrize(
    ("sensor", "value"),
    [("air_temp", 126), ("air_temp", -41), ("air_humidity", 101), ("soil_moisture", -1)],
)
def test_a_value_outside_the_parts_range_is_refused_and_changes_nothing(sensor, value):
    session = SimSession.load(AGENT)
    try:
        before = session.hal.sensor_values()[sensor][0]
        with pytest.raises(NeuroEdgeError):
            session.set_sensor(sensor, value)
        assert session.hal.sensor_values()[sensor][0] == before
    finally:
        session.hal.close()


# --- the build ---------------------------------------------------------------------------


def test_the_agent_builds_for_sim_and_prints_the_risk_label():
    result = runner.invoke(app, ["build", "--agent", str(AGENT), "--target", "sim"])
    assert result.exit_code == 0, result.output
    assert "risk=virtual_board" in result.output


def test_run_on_sim_builds_the_virtual_board_and_decides():
    result = runner.invoke(app, ["run", "--agent", str(AGENT), "--target", "sim", "-c", "bật đèn"])
    assert result.exit_code == 0, result.output
    assert "risk=virtual_board" in result.output
    assert "ALLOW" in result.output


# --- the demo script ---------------------------------------------------------------------


def test_the_demo_day_does_what_the_script_says():
    from .hand_clock import HandClock

    clock = HandClock()
    session = SimSession.load(AGENT, clock=clock)
    verdicts = []
    day = ROOT / "demo" / "i2d-nha-kinh" / "mot-ngay.txt"
    try:
        for line in day.read_text(encoding="utf-8").splitlines():
            if line == "exit":
                break
            if line.startswith(":sensor "):
                _, name, value = line.split(" ", 2)
                try:
                    session.set_sensor(name, float(value))
                except ValueError:
                    session.set_sensor(name, value)
                continue
            verdicts.append(say(session, line).allowed)
            clock.advance(2_500)
    finally:
        session.hal.close()
    # light, vent open | heater (31) | fan off, vent close (36), fan on | mist (95), (lost), (70)
    assert verdicts == [True, True, False, False, False, True, False, False, True]
