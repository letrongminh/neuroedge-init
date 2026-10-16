"""
The full fish tank sample (`fixtures/agents/aquarium-full`) on the virtual board `sim-virtual`
(docs/spec/virtual_parts.md, Q-84) and its demo (`demo/i2d-be-ca-day-du/`).

Five outputs and four sensors with names of their own, none on `sim-default`:

* reef_heater_on     — refused while the water is warm (≥ 29 °C) or unmeasured;
* reef_air_pump_off  — asks the owner; refused without a question on low oxygen (< 5 mg/L), warm
                       water or no reading;
* reef_filter_on     — refused when the water level is low (< 30 %) or unmeasured;
* reef_filter_off    — asks the owner;
* reef_co2_on        — refused when pH < 6.5, oxygen < 5 mg/L, or either is unmeasured;
* heater off, air pump on, CO₂ off, the light — always allowed.
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

from .hand_clock import HandClock

ROOT = repo_root()
AGENT = ROOT / "fixtures" / "agents" / "aquarium-full" / "agent.toml"
LOST = ["lỗi", float("nan")]
PINS = ["heater", "air_pump", "filter_pump", "co2_valve", "tank_light"]
SENSORS = ["water_temp", "ph", "oxygen", "water_level"]


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


@pytest.fixture
def make():
    """Sessions of the tank, each with its readings set; closed after the test."""
    opened = []

    def session_for(**readings) -> SimSession:
        session = SimSession.load(AGENT, clock=HandClock())
        opened.append(session)
        for sensor, value in readings.items():
            session.set_sensor(sensor, value)
        return session

    yield session_for
    for session in opened:
        session.hal.close()


def say(session: SimSession, *lines: str):
    return [asyncio.run(session.handle(line)) for line in lines]


def commands(session: SimSession, pin: str) -> list[str]:
    return [operation for operation, _ in session.hal.pin(pin).commands]


# --- the board ---------------------------------------------------------------------------------


def test_it_loads_on_the_virtual_board_and_lists_what_it_added(make):
    session = make()
    assert session.events.metadata["board_id"] == "sim-virtual"
    assert session.events.metadata["risks"] == ["virtual_board"]
    line = session.virtual_board.startup_line()
    assert line.startswith("risk=virtual_board added:")
    for name in [*PINS, *SENSORS]:
        assert name in line
    values = session.hal.sensor_values()
    assert [values[name][0] for name in SENSORS] == [25, 7.0, 7.5, 80]


def test_it_runs_on_sim_only():
    result = CliRunner().invoke(app, ["run", "--agent", str(AGENT), "--target", "linux"])
    assert result.exit_code != 0


def test_run_on_sim_builds_and_starts_labelled():
    result = CliRunner().invoke(
        app, ["run", "--agent", str(AGENT), "--target", "sim"], input="exit\n"
    )
    assert result.exit_code == 0, result.output
    assert "risk=virtual_board" in result.output


# --- the heater --------------------------------------------------------------------------------


@pytest.mark.parametrize("temp", [10, 25, 28.999])
def test_the_heater_comes_on_while_the_water_is_cool(make, temp):
    session = make(water_temp=temp)
    (on,) = say(session, "bật sưởi")
    assert on.allowed
    assert commands(session, "heater") == ["on"]


@pytest.mark.parametrize("temp", [29, 31, 40])
def test_the_heater_stays_off_in_warm_water_and_nobody_is_asked(make, temp):
    session = make(water_temp=temp)
    (on,) = say(session, "bật sưởi")
    assert on.result.blocked
    assert on.result.gate.failed_criterion == "water_hot"
    assert on.confirmation is None
    assert commands(session, "heater") == []


@pytest.mark.parametrize("lost", LOST, ids=repr)
def test_without_a_temperature_reading_the_heater_stays_off(make, lost):
    session = make(water_temp=lost)
    (on,) = say(session, "bật sưởi")
    assert on.result.blocked
    assert on.result.gate.reason == "criterion_unavailable"
    assert commands(session, "heater") == []


@pytest.mark.parametrize("temp", [*LOST, 35])
def test_the_heater_can_always_be_turned_off(make, temp):
    session = make(water_temp=temp)
    (off,) = say(session, "tắt sưởi")
    assert off.allowed
    assert commands(session, "heater") == ["off"]


# --- the air pump ------------------------------------------------------------------------------


@pytest.mark.parametrize("sensor", ["oxygen", "water_temp"])
def test_the_air_pump_can_always_be_turned_on(make, sensor):
    session = make(**{sensor: "lỗi"})
    (on,) = say(session, "bật sục khí")
    assert on.allowed
    assert commands(session, "air_pump") == ["on"]


def test_turning_the_air_pump_off_asks_the_owner_and_a_yes_does_it(make):
    session = make()
    off, yes = say(session, "tắt sục khí", "có")
    assert off.result.blocked
    assert off.result.gate.failed_criterion == "owner_confirmed"
    assert off.confirmation is not None and off.confirmation.confirms == ("owner_confirmed",)
    assert yes.allowed
    assert commands(session, "air_pump") == ["off"]


def test_a_no_keeps_the_air_pump_running(make):
    session = make()
    say(session, "tắt sục khí", "không")
    assert commands(session, "air_pump") == []


@pytest.mark.parametrize(
    "readings",
    [
        {"oxygen": 4.9},
        {"oxygen": 0},
        {"water_temp": 29},
        {"water_temp": 33},
        {"oxygen": "lỗi"},
        {"water_temp": "lỗi"},
    ],
    ids=repr,
)
def test_on_low_oxygen_warm_water_or_no_reading_the_air_pump_stays_on_and_nothing_is_asked(
    make, readings
):
    session = make(**readings)
    off, yes = say(session, "tắt sục khí", "có")
    assert off.result.blocked
    assert off.confirmation is None
    assert not yes.allowed
    assert commands(session, "air_pump") == []


def test_oxygen_of_exactly_five_is_enough_to_ask(make):
    session = make(oxygen=5)
    (off,) = say(session, "tắt sục khí")
    assert off.confirmation is not None


def test_a_yes_is_decided_on_a_fresh_reading(make):
    session = make()
    say(session, "tắt sục khí")
    session.set_sensor("oxygen", 3)  # the oxygen fell while the owner was asked
    (yes,) = say(session, "có")
    assert not yes.allowed
    assert commands(session, "air_pump") == []


# --- the filter --------------------------------------------------------------------------------


@pytest.mark.parametrize("level", [30, 55, 100])
def test_the_filter_comes_on_when_there_is_water_enough(make, level):
    session = make(water_level=level)
    (on,) = say(session, "bật lọc")
    assert on.allowed
    assert commands(session, "filter_pump") == ["on"]


@pytest.mark.parametrize("level", [0, 12, 29.9, "lỗi"], ids=repr)
def test_the_filter_never_runs_dry_or_blind(make, level):
    session = make(water_level=level)
    (on,) = say(session, "bật lọc")
    assert on.result.blocked
    assert on.confirmation is None
    assert commands(session, "filter_pump") == []


def test_turning_the_filter_off_asks_the_owner(make):
    session = make()
    on, off, yes = say(session, "bật lọc", "tắt lọc", "có")
    assert on.allowed
    assert off.result.blocked and off.confirmation is not None
    assert yes.allowed
    assert commands(session, "filter_pump") == ["on", "off"]


def test_a_no_keeps_the_filter_running(make):
    session = make()
    say(session, "bật lọc", "tắt lọc", "không")
    assert commands(session, "filter_pump") == ["on"]


# --- CO2 ---------------------------------------------------------------------------------------


def test_co2_opens_in_a_healthy_tank(make):
    session = make()
    (on,) = say(session, "bơm CO2")
    assert on.allowed
    assert commands(session, "co2_valve") == ["on"]


@pytest.mark.parametrize(
    "readings,criterion",
    [
        ({"ph": 6.4}, "ph_ok"),
        ({"ph": 3}, "ph_ok"),
        ({"ph": "lỗi"}, None),
        ({"oxygen": 4.9}, "oxygen_ok"),
        ({"oxygen": "lỗi"}, None),
    ],
    ids=repr,
)
def test_co2_is_refused_on_low_ph_low_oxygen_or_no_reading(make, readings, criterion):
    session = make(**readings)
    (on,) = say(session, "bơm CO2")
    assert on.result.blocked
    assert on.confirmation is None
    if criterion:
        assert on.result.gate.failed_criterion == criterion
    else:
        assert on.result.gate.reason == "criterion_unavailable"
    assert commands(session, "co2_valve") == []


def test_ph_of_exactly_six_and_a_half_is_enough(make):
    (on,) = say(make(ph=6.5), "bơm CO2")
    assert on.allowed


@pytest.mark.parametrize("readings", [{}, {"ph": 4}, {"oxygen": 1}, {"ph": "lỗi"}], ids=repr)
def test_co2_can_always_be_closed(make, readings):
    session = make(**readings)
    (off,) = say(session, "tắt CO2")
    assert off.allowed
    assert commands(session, "co2_valve") == ["off"]


# --- the light, and values no probe can read ----------------------------------------------------


@pytest.mark.parametrize("readings", [{}, {"water_temp": 40, "oxygen": 1, "water_level": 5}])
def test_the_light_is_free(make, readings):
    session = make(**readings)
    on, off = say(session, "bật đèn bể", "tắt đèn bể")
    assert on.allowed and off.allowed
    assert commands(session, "tank_light") == ["on", "off"]


@pytest.mark.parametrize(
    "sensor,value",
    [("ph", 15), ("ph", -1), ("oxygen", 25), ("oxygen", -0.1), ("water_level", 101)],
)
def test_a_value_outside_a_parts_range_is_refused(make, sensor, value):
    session = make()
    before = session.hal.sensor_values()[sensor][0]
    with pytest.raises(NeuroEdgeError):
        session.set_sensor(sensor, value)
    assert session.hal.sensor_values()[sensor][0] == before
