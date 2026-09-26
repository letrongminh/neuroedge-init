"""
`bands` in `[sim.sensor_facts]`: a numeric reading → the `level` a gate compares.

``heat = { sensor = "temperature", bands = { low = -40, normal = 25, high = 40 } }``:
each band starts at its bound, inclusive, and ends where the next one starts; the
last has no upper end. A reading below the first bound, or one that is not a finite
number, is undecided — never a guessed band. A rule the gates cannot use is refused
when the session loads (docs/spec/simulation_coverage.md §2).
"""

from __future__ import annotations

import math

import pytest

from neuroedge.errors import AgentManifestError
from neuroedge.sim import SimSession
from neuroedge.sim.session import SensorFact

BANDS = (("low", -40), ("normal", 25), ("high", 40), ("critical", 55))
HEAT = SensorFact("temperature", bands=BANDS)


# --- evaluating a reading --------------------------------------------------------------


@pytest.mark.parametrize(
    ("reading", "band"),
    [
        (-40, "low"),  # the first bound belongs to the first band
        (-40.0, "low"),
        (24.999, "low"),
        (math.nextafter(25, -math.inf), "low"),
        (25, "normal"),  # a bound belongs to the band it starts, not the one below
        (25.0, "normal"),
        (39.5, "normal"),
        (40, "high"),
        (54.999, "high"),
        (55, "critical"),
        (10**400, "critical"),  # the last band has no upper end; a huge int still compares
    ],
)
def test_a_reading_is_in_the_last_band_whose_bound_it_reaches(reading, band):
    assert HEAT.evaluate(reading) == band


@pytest.mark.parametrize(
    "reading",
    [
        -40.001,
        math.nextafter(-40, -math.inf),
        -1e9,
        float("nan"),
        float("inf"),
        float("-inf"),
        True,  # a bool is an int to Python, not a reading
        False,
        "high",  # a band name is not a reading
        "30",
        None,
    ],
    ids=repr,
)
def test_a_reading_no_band_can_place_is_undecided(reading):
    assert HEAT.evaluate(reading) is None


def test_one_band_holds_every_reading_from_its_bound_up():
    only = SensorFact("t", bands=(("on", 0.5),))
    assert [only.evaluate(v) for v in (0.4, 0.5, 1e6)] == [None, "on", "on"]


@pytest.mark.parametrize("reading", [float("nan"), float("inf"), "hot", True, None], ids=repr)
def test_a_comparison_of_a_reading_that_is_not_a_finite_number_is_undecided(reading):
    # NaN compares False with everything: `gte` would have read "not hot" and allowed.
    assert SensorFact("t", gte=30).evaluate(reading) is None
    assert SensorFact("t", lte=30).evaluate(reading) is None
    assert SensorFact("t", gte=10, lte=30).evaluate(reading) is None


def test_comparisons_include_their_bound():
    assert SensorFact("t", gte=55).evaluate(55) is True
    assert SensorFact("t", gte=55).evaluate(math.nextafter(55, -math.inf)) is False
    assert SensorFact("t", lte=25).evaluate(25) is True
    assert SensorFact("t", gte=10, lte=30).evaluate(31) is False


# --- an agent with a level gate --------------------------------------------------------

LEVEL_GATE = """\
schema: neuroedge.gate/v1
name: cool
version: 1.0.0
evaluate:
  heat:
    type: level
    levels: [low, normal, high, critical]
    instructions: heat band
  hot:
    type: bool
    instructions: at or above 55
allow_when:
  heat: { lte: normal }
  hot: false
on_block:
  action: deny
budget:
  p95_latency_ms: 100
  fail: closed
"""


def agent(tmp_path, facts: str, sensors: str = 'temperature = { value = 30, unit = "C" }'):
    name = f"fan_off_{abs(hash(str(tmp_path)))}"  # @action names are process-wide
    (tmp_path / "actions").mkdir(exist_ok=True)
    (tmp_path / "actions" / "fan.py").write_text(
        "from neuroedge import action\n"
        "from neuroedge.hal import digital\n\n"
        f'@action(name="{name}", requires="digital.out:gate_relay", gate="cool")\n'
        "def fan_off() -> None:\n"
        '    digital.out("gate_relay").off()\n',
        encoding="utf-8",
    )
    (tmp_path / "cool.yaml").write_text(LEVEL_GATE, encoding="utf-8")
    (tmp_path / "commands.toml").write_text(
        '[grammar]\nversion = 1\n\n[[command]]\nintent = "fan_off"\npatterns = ["tắt quạt"]\n'
        f'tool = "{name}"\n',
        encoding="utf-8",
    )
    (tmp_path / "agent.toml").write_text(
        '[agent]\nname = "bands-test"\nversion = "0.1.0"\n\n'
        '[requires]\n"digital.out" = { pins = ["gate_relay"] }\n'
        '"sensor.read" = { sensors = ["temperature"] }\n\n'
        '[gates]\ncool = "cool.yaml"\n\n'
        f"[sim.sensors]\n{sensors}\n\n[sim.sensor_facts]\n{facts}\n",
        encoding="utf-8",
    )
    return tmp_path / "agent.toml"


GOOD = (
    'heat = { sensor = "temperature", bands = { low = -40, normal = 25, high = 40, critical = 55 } }\n'
    'hot  = { sensor = "temperature", gte = 55 }'
)


@pytest.mark.parametrize(
    ("reading", "allowed"),
    [(24.5, True), (25, True), (39.999, True), (40, False), (55, False), (-40.5, False)],
)
async def test_the_band_decides_the_gate(tmp_path, reading, allowed):
    session = SimSession.load(agent(tmp_path, GOOD))
    session.set_sensor("temperature", reading)
    turn = await session.handle("tắt quạt")
    assert turn.allowed is allowed
    assert session.hal.pin("gate_relay").commands == ([("off", 0)] if allowed else [])


async def test_an_undecided_band_is_recorded_as_no_value_and_blocks(tmp_path):
    session = SimSession.load(agent(tmp_path, GOOD))
    session.set_sensor("temperature", float("nan"))
    turn = await session.handle("tắt quạt")
    assert turn.result.blocked
    assert turn.result.gate.reason == "criterion_unavailable"
    facts = session.events.of_type("gate_facts")[-1]
    assert facts["heat"]["value"] is None and facts["hot"]["value"] is None


async def test_an_undecided_band_is_not_replaced_by_a_canned_fact(tmp_path):
    # [sim.facts] says `low`; the sensor fact of the same name wins, undecided or not.
    path = agent(tmp_path, GOOD)
    path.write_text(path.read_text("utf-8") + '\n[sim.facts]\nheat = "low"\n', "utf-8")
    session = SimSession.load(path)
    session.set_sensor("temperature", "not a number")
    turn = await session.handle("tắt quạt")
    assert turn.result.blocked and turn.result.gate.failed_criterion == "heat"


# --- a rule the gates cannot use is refused at load ----------------------------------------


def refused(tmp_path, facts, sensors='temperature = { value = 30, unit = "C" }'):
    with pytest.raises(AgentManifestError) as raised:
        SimSession.load(agent(tmp_path, facts, sensors))
    error = raised.value
    assert error.where and error.why and error.how, "where, why and how (FR-DX-04)"
    return error


def heat(bands: str, extra: str = "") -> str:
    return f'heat = {{ sensor = "temperature", bands = {bands}{extra} }}\nhot = {{ sensor = "temperature", gte = 55 }}'


@pytest.mark.parametrize(
    ("bands", "where", "why"),
    [
        ("{}", "heat -> bands", "must be a table"),
        ('"high"', "heat -> bands", "must be a table"),
        ("[25, 40]", "heat -> bands", "must be a table"),
        ('{ low = "cold", normal = 25 }', "heat -> bands.low", "not a finite number"),
        ("{ low = true, normal = 25 }", "heat -> bands.low", "not a finite number"),
        ("{ low = -40, normal = nan }", "heat -> bands.normal", "not a finite number"),
        ("{ low = -40, normal = inf }", "heat -> bands.normal", "not a finite number"),
        ("{ low = -inf, normal = 25 }", "heat -> bands.low", "not a finite number"),
        ("{ low = -40, normal = 25, high = 25 }", "heat -> bands.high", "strictly ascending"),
        ("{ low = -40, normal = 40, high = 25 }", "heat -> bands.high", "strictly ascending"),
        ("{ low = 25.0, normal = 25 }", "heat -> bands.normal", "strictly ascending"),
    ],
)
def test_bounds_that_are_not_finite_and_strictly_ascending_are_refused(tmp_path, bands, where, why):
    error = refused(tmp_path, heat(bands))
    assert f"[sim.sensor_facts] {where}" in error.where
    assert why in error.why


def test_a_band_the_gate_does_not_declare_is_refused(tmp_path):
    error = refused(tmp_path, heat("{ low = -40, warm = 25, critical = 55 }"))
    assert "[sim.sensor_facts] heat -> bands" in error.where
    assert "['warm'] is not a level of 'heat' in gate cool@1.0.0" in error.why
    assert "['low', 'normal', 'high', 'critical']" in error.how


def test_bands_out_of_the_gates_level_order_are_refused(tmp_path):
    # Ascending bounds, but 40 °C would be `normal` and 25 °C `high`.
    error = refused(tmp_path, heat("{ low = -40, high = 25, normal = 40, critical = 55 }"))
    assert "not in the order of gate cool@1.0.0's levels" in error.why
    assert "a higher reading would give a lower level" in error.why


def test_bands_may_skip_levels_in_order(tmp_path):
    session = SimSession.load(agent(tmp_path, heat("{ normal = 0, critical = 55 }")))
    assert session.sensor_facts["heat"].evaluate(54) == "normal"


@pytest.mark.parametrize("other", ['equals = "high"', "gte = 40", "lte = 40", "gte = 10, lte = 40"])
def test_bands_with_another_rule_are_refused(tmp_path, other):
    error = refused(tmp_path, heat("{ low = -40, normal = 25 }", f", {other}"))
    assert "a sensor fact is one rule" in error.why
    assert "bands" in error.why


def test_equals_with_a_comparison_is_refused(tmp_path):
    facts = 'heat = { sensor = "temperature", bands = { low = -40 } }\n'
    facts += 'hot = { sensor = "temperature", equals = 55, gte = 55 }'
    error = refused(tmp_path, facts)
    assert "[sim.sensor_facts] hot" in error.where
    assert "['equals', 'gte']" in error.why


@pytest.mark.parametrize("threshold", ['"hot"', "nan", "inf", "true"])
def test_a_threshold_that_is_not_a_finite_number_is_refused(tmp_path, threshold):
    facts = f'heat = {{ sensor = "temperature", bands = {{ low = -40 }} }}\nhot = {{ sensor = "temperature", gte = {threshold} }}'
    error = refused(tmp_path, facts)
    assert "[sim.sensor_facts] hot -> gte" in error.where
    assert "not a finite number" in error.why


def test_bands_on_a_sensor_without_a_declared_unit_are_refused(tmp_path):
    error = refused(tmp_path, GOOD, sensors="temperature = 30")
    assert "[sim.sensor_facts] heat" in error.where
    assert "declares none for 'temperature'" in error.why
    assert 'unit = "C"' in error.how


def test_bands_for_a_criterion_the_gate_reads_as_a_bool_are_refused(tmp_path):
    facts = 'heat = { sensor = "temperature", bands = { low = -40 } }\n'
    facts += 'hot = { sensor = "temperature", bands = { low = -40 } }'
    error = refused(tmp_path, facts)
    assert "[sim.sensor_facts] hot -> bands" in error.where
    assert "evaluates 'hot' as 'bool'" in error.why


def test_bands_no_gate_reads_are_refused(tmp_path):
    error = refused(
        tmp_path, GOOD + '\nheat_levl = { sensor = "temperature", bands = { low = 0 } }'
    )
    assert "[sim.sensor_facts] heat_levl -> bands" in error.where
    assert "no gate of the agent evaluates 'heat_levl'" in error.why


def test_a_misspelt_rule_key_is_refused(tmp_path):
    error = refused(tmp_path, 'heat = { sensor = "temperature", band = { low = 0 } }')
    assert "[sim.sensor_facts] heat" in error.where
    assert "`bands`" in error.why
