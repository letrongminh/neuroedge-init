"""
The factory-monitor sample (TSK-S3-08): physical actions gated on one `level` fact.

The `temperature` sensor reports degrees Celsius; `[sim.sensor_facts]` turns the
reading into the heat band the gates compare (`low · normal · high · critical`,
starting at -40, 25, 40 and 55 °C) and into `heat_critical` (≥ 55 °C). `gate_relay`
is the fan, `porch_light` the alarm beacon; every assertion is on those pins.

* vent_on / alarm_on — allowed at any band;
* vent_off           — allowed up to `normal`, asks at `high` (RFC-0006), refused
                       without a question at `critical`;
* alarm_off          — refused above `normal`.

The same agent on `linux`, against a real kernel reading: `tests_linux/`.
"""

from __future__ import annotations

import asyncio
import math
import tomllib

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.engine import resolve_gate_file
from neuroedge.sim import SimSession
from neuroedge.testing import TracePlayer, assert_matches_golden
from neuroedge.testing.recorder import TraceRecorder

runner = CliRunner()
LEVELS = ["low", "normal", "high", "critical"]
# Readings in each band, its bounds included: a bound belongs to the band it starts.
READINGS = {
    "low": [-40, -39.5, 0, 24.5, 24.999],
    "normal": [25, 25.001, 30, 39.5, 39.999],
    "high": [40, 40.001, 45, 54.5, 54.999],
    "critical": [55, 55.001, 60, 125],
}
BANDED = [(band, reading) for band, readings in READINGS.items() for reading in readings]
# One reading a person would set for each band.
TYPICAL = {"low": 20, "normal": 30, "high": 45, "critical": 60}
# Not a number the bands can place: the gate decides nothing on it.
NOT_A_READING = ["high", float("nan"), float("inf"), float("-inf"), True]


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


def facts_at(session, reading):
    session.set_sensor("temperature", reading)
    return session.gate_facts(session.grammar.recognize("tắt quạt"))


# --- the gates are level gates; the agent turns degrees into the level -------------------


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


def test_sim_starts_hot_in_degrees(agent):
    session = session_for(agent)
    assert session.hal.sensor_values()["temperature"] == (45, "C")
    assert session.gate_facts(session.grammar.recognize("tắt quạt"))["heat_level"] == "high"


@pytest.mark.parametrize(("band", "reading"), BANDED)
def test_a_reading_falls_in_exactly_its_band(agent, band, reading):
    assert facts_at(session_for(agent), reading)["heat_level"] == band


@pytest.mark.parametrize("reading", [-40.001, -41, -300])
def test_below_the_lowest_bound_neither_fact_is_decided(agent, reading):
    # An open or shorted probe: heat_critical must not read as a confident False.
    facts = facts_at(session_for(agent), reading)
    assert facts["heat_level"] is None and facts["heat_critical"] is None


def test_heat_level_and_heat_critical_agree_at_and_around_the_critical_bound(agent):
    rules = tomllib.loads(agent.read_text(encoding="utf-8"))["sim"]["sensor_facts"]
    bound = rules["heat_level"]["bands"]["critical"]
    assert rules["heat_critical"] == {"sensor": "temperature", "gte": bound}
    session = session_for(agent)
    offsets = [-1, -0.5, -0.001, -1e-9, 0, 1e-9, 0.001, 0.5, 1]
    sweep = [bound + offset for offset in offsets] + [math.nextafter(bound, -math.inf)]
    for reading in sweep + [reading for _, reading in BANDED] + [-41, *NOT_A_READING]:
        facts = facts_at(session, reading)
        if facts["heat_level"] is None:  # undecided together, never one without the other
            assert facts["heat_critical"] is None, reading
            continue
        assert (facts["heat_level"] == "critical") is facts["heat_critical"], reading
    at = facts_at(session, bound)
    assert (at["heat_level"], at["heat_critical"]) == ("critical", True)
    below = facts_at(session, math.nextafter(bound, -math.inf))
    assert (below["heat_level"], below["heat_critical"]) == ("high", False)


def test_both_facts_come_from_one_reading_per_evaluation(agent):
    session = session_for(agent, 45)
    say(session, "tắt quạt")
    reads = [r for r in session.events.of_type("sensor_read") if r.get("use") == "fact"]
    assert reads == [{"sensor": "temperature", "value": 45, "unit": "C", "use": "fact"}]


# --- the fan -----------------------------------------------------------------------------


@pytest.mark.parametrize("heat", TYPICAL.values())
def test_the_fan_starts_at_any_heat(agent, heat):
    session = session_for(agent, heat)
    (turn,) = say(session, "bật quạt")
    assert turn.allowed
    assert session.hal.pin("gate_relay").commands == [("on", 0)]


@pytest.mark.parametrize(("band", "reading"), BANDED)
def test_stopping_the_fan_follows_the_band(agent, band, reading):
    session = session_for(agent, reading)
    _, off = say(session, "bật quạt", "tắt quạt")
    if band in ("low", "normal"):
        assert off.allowed
        assert session.hal.pin("gate_relay").commands == [("on", 0), ("off", 0)]
        return
    assert off.result.blocked
    assert off.result.gate.failed_criterion == "heat_level"
    if band == "high":
        assert off.confirmation is not None and off.confirmation.confirms == ("heat_level",)
    else:
        assert off.confirmation is None  # a yes would not be enough: heat_critical fails
    assert session.hal.pin("gate_relay").commands == [("on", 0)]


def test_at_high_heat_stopping_the_fan_asks_an_operator(agent):
    session = session_for(agent, 45)
    _, off = say(session, "bật quạt", "tắt quạt")
    assert off.result.blocked
    assert off.result.gate.failed_criterion == "heat_level"
    assert off.result.gate.on_block_action == "ask"
    assert off.reply_source == "gate_ask"
    assert off.confirmation is not None
    assert off.confirmation.confirms == ("heat_level",)
    assert session.hal.pin("gate_relay").commands == [("on", 0)]


def test_an_operators_yes_stops_the_fan_and_is_recorded(agent):
    session = session_for(agent, 45)
    *_, yes = say(session, "bật quạt", "tắt quạt", "có")
    assert yes.allowed
    assert yes.result.gate.confirmed == ("heat_level",)
    assert session.hal.pin("gate_relay").commands == [("on", 0), ("off", 0)]


def test_an_operators_no_keeps_the_fan_running(agent):
    session = session_for(agent, 45)
    say(session, "bật quạt", "tắt quạt", "không")
    assert session.hal.pin("gate_relay").commands == [("on", 0)]


def test_a_yes_is_decided_on_a_fresh_reading(agent):
    session = session_for(agent, 45)
    say(session, "bật quạt", "tắt quạt")
    session.set_sensor("temperature", 55)  # the room reached critical while asking
    (yes,) = say(session, "có")
    assert not yes.allowed
    assert session.hal.pin("gate_relay").commands == [("on", 0)]


def test_at_critical_heat_the_fan_cannot_be_stopped_and_nothing_is_asked(agent):
    session = session_for(agent, 60)
    _, off, _ = say(session, "bật quạt", "tắt quạt", "có")
    assert off.result.blocked
    assert off.confirmation is None  # a yes would not be enough: heat_critical still fails
    assert session.conversation.confirmations.latest() is None
    assert session.hal.pin("gate_relay").commands == [("on", 0)]


# --- the alarm ---------------------------------------------------------------------------


@pytest.mark.parametrize("heat", TYPICAL.values())
def test_the_alarm_can_always_be_raised(agent, heat):
    session = session_for(agent, heat)
    (turn,) = say(session, "bật báo động")
    assert turn.allowed
    assert session.hal.pin("porch_light").commands == [("on", 0)]


@pytest.mark.parametrize(("band", "reading"), BANDED)
def test_the_alarm_is_silenced_only_up_to_normal(agent, band, reading):
    session = session_for(agent, reading)
    _, off = say(session, "bật báo động", "tắt báo động")
    if band in ("low", "normal"):
        assert off.allowed
        assert session.hal.pin("porch_light").commands == [("on", 0), ("off", 0)]
        return
    assert off.result.blocked
    assert off.result.gate.failed_criterion == "heat_level"
    assert off.result.gate.on_block_action == "deny"
    assert off.confirmation is None
    assert session.hal.pin("porch_light").commands == [("on", 0)]


def test_the_alarm_is_silenced_once_the_room_cools(agent):
    session = session_for(agent, 45)
    say(session, "bật báo động", "tắt báo động")
    session.set_sensor("temperature", 30)
    (off,) = say(session, "tắt báo động")
    assert off.allowed
    assert session.hal.pin("porch_light").commands == [("on", 0), ("off", 0)]


# --- fail closed -------------------------------------------------------------------------


@pytest.mark.parametrize("reading", [*NOT_A_READING, -40.5, -41, -300], ids=repr)
def test_a_reading_no_band_can_place_decides_nothing_and_nothing_is_asked(agent, reading):
    """
    NaN, a band name, a bool — or a number below -40 °C, an open or shorted probe:
    both heat facts are undecided, so vent_off and alarm_off refuse without a question
    (a "yes" could stand in for heat_level only), and vent_on / alarm_on still work.
    """
    session = session_for(agent, reading)
    turns = say(session, "bật quạt", "bật báo động", "tắt quạt", "có", "tắt báo động")
    fan_on, alarm_on, fan_off, yes, alarm_off = turns
    assert fan_on.allowed and alarm_on.allowed, "a gate that reads no heat fact still decides"
    for turn in (fan_off, alarm_off):
        assert turn.result.blocked
        assert turn.result.gate.reason == "criterion_unavailable"
        assert turn.confirmation is None, "heat_critical is undecided too: a yes is not enough"
    assert not yes.allowed
    assert session.hal.pin("gate_relay").commands == [("on", 0)]
    assert session.hal.pin("porch_light").commands == [("on", 0)]
    facts = session.events.of_type("gate_facts")[-1]
    assert facts["heat_level"]["value"] is None
    assert {e["sensor"] for e in session.events.of_type("sensor_unavailable")} == {"temperature"}


def test_a_probe_that_fails_low_while_asking_refuses_the_yes(agent):
    session = session_for(agent, 45)
    _, off = say(session, "bật quạt", "tắt quạt")
    assert off.confirmation is not None
    session.set_sensor("temperature", -41)
    (yes,) = say(session, "có")
    assert not yes.allowed
    assert session.hal.pin("gate_relay").commands == [("on", 0)]


# --- trace, replay, CLI ------------------------------------------------------------------


async def test_a_recorded_session_replays_to_the_same_decisions(agent):
    recorder = TraceRecorder()
    session = session_for(agent, events=recorder)
    for line in ("bật quạt", "tắt báo động"):
        await session.handle(line)
    session.set_sensor("temperature", 30)
    await session.handle("tắt quạt")
    session.set_sensor("temperature", "high")  # no band: recorded as undecided
    await session.handle("tắt báo động")
    trace = recorder.to_trace()
    result = await TracePlayer(trace, agent=agent).replay()
    assert result.verdicts == ["ALLOW", "BLOCK", "ALLOW", "BLOCK"]
    assert result.verdicts == result.recorded_verdicts
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


def test_the_repl_sets_the_temperature_in_degrees(agent):
    stdin = (
        ":sensor temperature 60\ntắt quạt\n:sensor temperature 45\ntắt quạt\nkhông\n"
        ":sensor temperature 30\ntắt báo động\nexit\n"
    )
    result = runner.invoke(app, ["run", "--agent", str(agent)], input=stdin)
    assert result.exit_code == 0, result.output
    critical, high = result.output.split("temperature = 45")
    high, normal = high.split("temperature = 30")
    assert "BLOCK vent_off" in critical and "xác nhận confirm_" not in critical
    assert "BLOCK vent_off" in high and "xác nhận confirm_" in high
    assert "ALLOW alarm_off" in normal
