"""
`[sim.sensor_facts]` rules — `bands`, `gte` / `lte`, `equals` — and how they fail.

``heat = { sensor = "temperature", bands = { low = -40, normal = 25, high = 40,
critical = 55 } }``: each band starts at its bound, inclusive, and ends where the
next one starts; the last has no upper end, so it must be the gate's highest level.
A reading that cannot be taken, or that one rule of its sensor rejects — not a finite
number, below the first bound, the wrong type for `equals` — leaves every fact of
that sensor undecided and writes `sensor_unavailable`: never a guessed band, never a
confident "not critical". A rule the gates cannot use is refused when the session
loads (docs/spec/simulation_coverage.md §2).
"""

from __future__ import annotations

import json
import math

import pytest

from neuroedge.errors import AgentManifestError, BoardCapabilityError, NeuroEdgeError
from neuroedge.sim import SimSession
from neuroedge.sim.session import SensorFact
from neuroedge.testing import TracePlayer
from neuroedge.testing.recorder import TraceRecorder

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
    assert HEAT.rejects(reading) is None
    assert HEAT.evaluate(reading) == band


@pytest.mark.parametrize(
    ("reading", "why"),
    [
        (-40.001, "below -40"),
        (math.nextafter(-40, -math.inf), "below -40"),
        (-1e9, "below -40"),
        (float("nan"), "not a finite number"),
        (float("inf"), "not a finite number"),
        (float("-inf"), "not a finite number"),
        (True, "not a finite number"),  # a bool is an int to Python, not a reading
        (False, "not a finite number"),
        ("high", "not a finite number"),  # a band name is not a reading
        ("30", "not a finite number"),
        (None, "not a finite number"),
    ],
    ids=repr,
)
def test_a_reading_no_band_can_place_is_rejected_and_undecided(reading, why):
    assert why in HEAT.rejects(reading)
    assert HEAT.evaluate(reading) is None


@pytest.mark.parametrize("reading", [float("nan"), float("inf"), "hot", True, None], ids=repr)
def test_a_comparison_of_a_reading_that_is_not_a_finite_number_is_undecided(reading):
    # NaN compares False with everything: `gte` would have read "not hot" and allowed.
    for rule in (SensorFact("t", gte=30), SensorFact("t", lte=30), SensorFact("t", gte=1, lte=3)):
        assert rule.rejects(reading) is not None
        assert rule.evaluate(reading) is None


def test_comparisons_include_their_bound():
    assert SensorFact("t", gte=55).evaluate(55) is True
    assert SensorFact("t", gte=55).evaluate(math.nextafter(55, -math.inf)) is False
    assert SensorFact("t", lte=25).evaluate(25) is True
    assert SensorFact("t", gte=10, lte=30).evaluate(31) is False


@pytest.mark.parametrize(
    ("expected", "reading", "fact"),
    [
        (False, False, True),
        (False, True, False),
        (True, True, True),
        ("open", "open", True),
        ("open", "closed", False),
        (1, 1.0, True),  # a number is a number
        (400, 399, False),
        (False, 0, None),  # 0 is not False
        (True, 1, None),  # 1 is not True
        (0, False, None),
        ("1", 1, None),
        (1, "1", None),
        (1, float("nan"), None),
        (False, None, None),
        ("open", float("inf"), None),
    ],
    ids=repr,
)
def test_equals_decides_only_on_a_reading_of_its_own_type(expected, reading, fact):
    rule = SensorFact("d", equals=expected)
    assert rule.evaluate(reading) is fact
    assert (rule.rejects(reading) is None) is (fact is not None)


@pytest.mark.parametrize("reading", [None, float("nan"), float("-inf")], ids=repr)
def test_the_reading_itself_is_never_none_or_non_finite(reading):
    assert SensorFact("d").evaluate(reading) is None
    assert SensorFact("d").evaluate("open") == "open"


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
  action: ask
  message: "Nóng — chắc chưa?"
  confirms: [heat]
budget:
  p95_latency_ms: 100
  fail: closed
"""
OPEN_GATE = """\
schema: neuroedge.gate/v1
name: open
version: 1.0.0
evaluate:
  call_source:
    type: choice
    options: [local_grammar, system_one, system_two, mcp, test]
    instructions: who called
allow_when:
  call_source: { in: [local_grammar] }
on_block:
  action: deny
budget:
  p95_latency_ms: 100
  fail: closed
"""


def agent(tmp_path, facts: str, sensors: str = 'temperature = { value = 30, unit = "C" }'):
    """`tắt quạt` behind the heat gate (ask on heat); `bật quạt` behind a gate with no heat fact."""
    name = f"fan_{abs(hash(str(tmp_path)))}"  # @action names are process-wide
    (tmp_path / "actions").mkdir(parents=True, exist_ok=True)
    (tmp_path / "actions" / "fan.py").write_text(
        "from neuroedge import action\n"
        "from neuroedge.hal import digital\n\n"
        f'@action(name="{name}_off", requires="digital.out:gate_relay", gate="cool")\n'
        "def fan_off() -> None:\n"
        '    digital.out("gate_relay").off()\n\n'
        f'@action(name="{name}_on", requires="digital.out:gate_relay", gate="open")\n'
        "def fan_on() -> None:\n"
        '    digital.out("gate_relay").on()\n',
        encoding="utf-8",
    )
    (tmp_path / "cool.yaml").write_text(LEVEL_GATE, encoding="utf-8")
    (tmp_path / "open.yaml").write_text(OPEN_GATE, encoding="utf-8")
    (tmp_path / "commands.toml").write_text(
        '[grammar]\nversion = 1\n\n[[command]]\nintent = "fan_off"\npatterns = ["tắt quạt"]\n'
        f'tool = "{name}_off"\n\n[[command]]\nintent = "fan_on"\npatterns = ["bật quạt"]\n'
        f'tool = "{name}_on"\n',
        encoding="utf-8",
    )
    (tmp_path / "agent.toml").write_text(
        '[agent]\nname = "bands-test"\nversion = "0.1.0"\n\n'
        '[requires]\n"digital.out" = { pins = ["gate_relay"] }\n'
        '"sensor.read" = { sensors = ["temperature"] }\n\n'
        '[gates]\ncool = "cool.yaml"\nopen = "open.yaml"\n\n'
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


@pytest.mark.parametrize(
    ("reading", "why"),
    [
        (-40.5, "heat: -40.5 is below -40, where the lowest band ('low') starts"),
        (-300, "heat: -300 is below -40"),  # an open thermistor
        (float("nan"), "heat: nan is not a finite number"),
        ("high", "heat: 'high' is not a finite number"),
    ],
    ids=repr,
)
async def test_a_rejected_reading_makes_every_fact_of_its_sensor_undecided(tmp_path, reading, why):
    """Below range the veto (`hot`, a comparison) is not a confident False: no question."""
    session = SimSession.load(agent(tmp_path, GOOD))
    session.set_sensor("temperature", reading)
    on, off, yes = [await session.handle(line) for line in ("bật quạt", "tắt quạt", "có")]
    assert on.allowed, "a gate that reads no fact of the sensor decides as usual"
    assert off.result.blocked and off.result.gate.reason == "criterion_unavailable"
    assert off.confirmation is None, "nothing a person could stand in for: nothing asked"
    assert not yes.allowed
    assert session.hal.pin("gate_relay").commands == [("on", 0)]
    facts = session.events.of_type("gate_facts")[-1]
    assert facts["heat"]["value"] is None and facts["hot"]["value"] is None
    (unavailable, *_) = session.events.of_type("sensor_unavailable")
    assert unavailable["sensor"] == "temperature" and why in unavailable["reason"]


async def test_a_sensor_that_fails_between_the_question_and_the_yes_refuses(tmp_path):
    session = SimSession.load(agent(tmp_path, GOOD))
    session.set_sensor("temperature", 45)
    off = await session.handle("tắt quạt")
    assert off.confirmation is not None  # `high`: a person may stand in for heat
    session.set_sensor("temperature", -41)  # the probe opens while the question waits
    yes = await session.handle("có")
    assert not yes.allowed
    assert session.hal.pin("gate_relay").never_pulsed()


async def test_a_reading_the_simulator_does_not_have_is_undecided_not_a_crash(tmp_path):
    session = SimSession.load(agent(tmp_path, GOOD))
    del session.hal._sensors["temperature"]  # what an unset sensor looks like to SimHAL
    on, off = [await session.handle(line) for line in ("bật quạt", "tắt quạt")]
    assert on.allowed
    assert off.result.blocked and off.confirmation is None
    assert "no scripted value" in session.events.of_type("sensor_unavailable")[-1]["reason"]


# --- nothing non-finite leaves the process -----------------------------------------------


def strict(text: str):
    def refuse(name):
        raise AssertionError(f"bare {name} in JSON")

    return json.loads(text, parse_constant=refuse)


async def test_a_nan_reading_leaves_only_strict_json_and_replays_the_same(tmp_path):
    from neuroedge.sim.ui import SessionServer
    from neuroedge.viz import page

    path = agent(tmp_path, GOOD)
    recorder = TraceRecorder()
    session = SimSession.load(path, events=recorder)
    session.set_sensor("temperature", float("nan"))
    await session.handle("tắt quạt")
    session.set_sensor("temperature", float("-inf"))
    await session.handle("tắt quạt")

    out = tmp_path / "nan.json"
    session.write_trace(out)
    trace = strict(out.read_text(encoding="utf-8"))
    sets = [e["data"] for e in trace["events"] if e["type"] == "sensor_set"]
    assert sets[0] == {"sensor": "temperature", "value": "nan", "non_finite": True}
    reads = [e["data"] for e in trace["events"] if e["type"] == "sensor_read"]
    assert reads[-1]["value"] == "-inf" and reads[-1]["non_finite"] is True

    server = SessionServer(session)
    try:
        from neuroedge.sim.ui import _json

        strict(_json(server.state()))
    finally:
        server.httpd.server_close()
    raw = [*trace["events"], {"offset_ms": 0, "type": "x", "data": {"v": float("nan")}}]
    html = page(title="t", meta=trace["metadata"], events=raw, board={})
    embedded = html.split('id="ne-data"', 1)[1].split(">", 1)[1].split("</script>", 1)[0]
    assert strict(embedded)["events"][-1]["data"] == {"v": "nan"}

    result = await TracePlayer(out, agent=path).replay()
    assert result.verdicts == result.recorded_verdicts == ["BLOCK", "BLOCK"]


def test_a_trace_file_with_a_bare_nan_is_refused(tmp_path):
    from neuroedge.errors import TraceValidationError
    from neuroedge.trace import load_trace

    bad = tmp_path / "bad.json"
    bad.write_text('{"metadata": {}, "events": [{"data": {"value": NaN}}]}', encoding="utf-8")
    with pytest.raises(TraceValidationError, match="bare NaN"):
        load_trace(bad, validate=False)


def test_a_non_finite_action_reading_replays_as_the_float(tmp_path):
    from neuroedge.hal.sim import reading_data, reading_value

    for value in (float("nan"), float("inf"), float("-inf")):
        data = json.loads(json.dumps(reading_data("t", value, "C")))
        assert data["non_finite"] is True and isinstance(data["value"], str)
        back = reading_value(data)
        assert isinstance(back, float) and repr(back) == repr(value)
    assert reading_value(reading_data("t", "nan")) == "nan", "a string reading stays a string"


# --- replay notices changed rules --------------------------------------------------------


async def test_replay_warns_when_the_sensor_rules_changed_since_the_recording(tmp_path):
    path = agent(tmp_path, GOOD)
    recorder = TraceRecorder()
    session = SimSession.load(path, events=recorder)
    await session.handle("tắt quạt")
    trace = recorder.to_trace()
    assert trace["metadata"]["sensor_facts_digest"].startswith("sha256:")

    same = await TracePlayer(trace, agent=path).replay()
    assert same.warnings == []
    path.write_text(path.read_text("utf-8").replace("normal = 25", "normal = 20"), "utf-8")
    moved = await TracePlayer(trace, agent=path).replay()
    assert moved.verdicts == same.verdicts, "replay still feeds the recorded facts"
    (warning,) = moved.warnings
    assert "[sim.sensor_facts]" in warning and "record the session again" in warning
    assert [e["type"] for e in moved.replayed["events"]].count("sensor_facts_changed") == 1


# --- a fact a sensor decides cannot also be set ------------------------------------------


def test_a_fixed_value_for_a_sensor_fact_is_refused(tmp_path):
    path = agent(tmp_path, GOOD)
    path.write_text(path.read_text("utf-8") + '\n[sim.facts]\nheat = "low"\n', "utf-8")
    error = refused_load(path)
    assert "[sim.facts] heat" in error.where and "would never be used" in error.why
    with pytest.raises(AgentManifestError, match="would never be used"):
        SimSession.load(agent(tmp_path / "b", GOOD), facts={"hot": False})


def test_set_on_a_sensor_fact_says_it_has_no_effect(tmp_path):
    session = SimSession.load(agent(tmp_path, GOOD))
    with pytest.raises(NeuroEdgeError, match="would never be read") as raised:
        session.set_fact("heat", "low")
    assert ":sensor temperature" in raised.value.how
    assert "heat" not in session.facts
    session.set_fact("guest", True)
    assert session.facts["guest"] is True


def test_the_repl_refuses_set_on_a_sensor_fact(tmp_path):
    from typer.testing import CliRunner

    from neuroedge.cli.main import app

    stdin = ":set heat low\n:facts\nexit\n"
    result = CliRunner().invoke(app, ["run", "--agent", str(agent(tmp_path, GOOD))], input=stdin)
    assert result.exit_code == 0, result.output
    assert "would never be read" in result.output
    assert "from sensor temperature ([sim.sensor_facts])" in result.output


# --- a rule the gates cannot use is refused at load ----------------------------------------


def refused_load(path):
    with pytest.raises(AgentManifestError) as raised:
        SimSession.load(path)
    error = raised.value
    assert error.where and error.why and error.how, "where, why and how (FR-DX-04)"
    return error


def refused(tmp_path, facts, sensors='temperature = { value = 30, unit = "C" }'):
    return refused_load(agent(tmp_path, facts, sensors))


FULL = "{ low = -40, normal = 25, high = 40, critical = 55 }"


def heat(bands: str = FULL, extra: str = "", hot: str = "gte = 55") -> str:
    return (
        f'heat = {{ sensor = "temperature", bands = {bands}{extra} }}\n'
        f'hot = {{ sensor = "temperature", {hot} }}'
    )


@pytest.mark.parametrize(
    ("bands", "where", "why"),
    [
        ("{}", "heat -> bands", "must be a table"),
        ('"high"', "heat -> bands", "must be a table"),
        ("[25, 40]", "heat -> bands", "must be a table"),
        ('{ low = "cold", critical = 55 }', "heat -> bands.low", "not a finite number"),
        ("{ low = true, critical = 55 }", "heat -> bands.low", "not a finite number"),
        ("{ low = -40, critical = nan }", "heat -> bands.critical", "not a finite number"),
        ("{ low = -40, critical = inf }", "heat -> bands.critical", "not a finite number"),
        ("{ low = -inf, critical = 55 }", "heat -> bands.low", "not a finite number"),
        ("{ low = -40, high = 25, critical = 25 }", "heat -> bands.critical", "strictly ascending"),
        ("{ low = -40, high = 55, critical = 40 }", "heat -> bands.critical", "strictly ascending"),
        ("{ low = 55.0, critical = 55 }", "heat -> bands.critical", "strictly ascending"),
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


@pytest.mark.parametrize("bands", ["{ low = -40, normal = 25 }", "{ low = -40, high = 40 }"])
def test_bands_that_stop_below_the_gates_highest_level_are_refused(tmp_path, bands):
    # `{ low = -40, normal = 25 }`: at 200 °C the room would still be `normal`.
    error = refused(tmp_path, heat(bands, hot="gte = 25" if "normal" in bands else "gte = 40"))
    assert "[sim.sensor_facts] heat -> bands" in error.where
    assert "has no upper end" in error.why and "'critical' above it" in error.why
    assert "end the bands with critical" in error.how


def test_bands_may_skip_lower_and_middle_levels(tmp_path):
    session = SimSession.load(agent(tmp_path, heat("{ normal = 0, critical = 55 }")))
    assert session.sensor_facts["heat"].evaluate(54) == "normal"
    assert session.sensor_facts["heat"].evaluate(-1) is None


@pytest.mark.parametrize("other", ['equals = "high"', "gte = 40", "lte = 40", "gte = 10, lte = 40"])
def test_bands_with_another_rule_are_refused(tmp_path, other):
    error = refused(tmp_path, heat(extra=f", {other}"))
    assert "a sensor fact is one rule" in error.why
    assert "bands" in error.why


def test_equals_with_a_comparison_is_refused(tmp_path):
    error = refused(tmp_path, heat(hot="equals = 55, gte = 55"))
    assert "[sim.sensor_facts] hot" in error.where
    assert "['equals', 'gte']" in error.why


@pytest.mark.parametrize("value", ["nan", "inf", "[1, 2]", "{ a = 1 }", "1979-05-27"])
def test_an_equals_value_that_is_not_a_bool_string_or_finite_number_is_refused(tmp_path, value):
    error = refused(tmp_path, heat() + f'\nopen = {{ sensor = "door_contact", equals = {value} }}')
    assert "[sim.sensor_facts] open -> equals" in error.where
    assert "not a bool, a string or a finite number" in error.why


@pytest.mark.parametrize("threshold", ['"hot"', "nan", "inf", "true"])
def test_a_threshold_that_is_not_a_finite_number_is_refused(tmp_path, threshold):
    error = refused(tmp_path, heat(hot=f"gte = {threshold}"))
    assert "[sim.sensor_facts] hot -> gte" in error.where
    assert "not a finite number" in error.why


@pytest.mark.parametrize("gte", ["50", "54.5", "0"])
def test_a_threshold_off_the_band_bounds_of_its_sensor_is_refused(tmp_path, gte):
    # critical = 55, gte = 50: at 52 °C `heat` is `high` and `hot` true — or, with
    # the numbers the other way round, `critical` and a confident "not hot".
    error = refused(tmp_path, heat(hot=f"gte = {gte}"))
    assert "[sim.sensor_facts] hot -> gte" in error.where
    assert "is not a bound of the bands of 'heat'" in error.why
    assert "[-40, 25, 40, 55]" in error.how


@pytest.mark.parametrize("gte", ["55", "40", "-40", "55.0"])
def test_a_threshold_on_a_band_bound_loads(tmp_path, gte):
    session = SimSession.load(agent(tmp_path, heat(hot=f"gte = {gte}")))
    assert session.sensor_facts["hot"].gte == float(gte)


@pytest.mark.parametrize("hot", ["lte = 55", "gte = 25, lte = 55"])
def test_lte_on_a_banded_sensor_is_refused(tmp_path, hot):
    error = refused(tmp_path, heat(hot=hot))
    assert "[sim.sensor_facts] hot -> lte" in error.where
    assert "would disagree there" in error.why


@pytest.mark.parametrize(
    "facts",
    [
        GOOD,  # bands and gte
        'hot = { sensor = "temperature", gte = 55 }',
        'cool = { sensor = "temperature", lte = 25 }',
    ],
)
def test_a_numeric_rule_on_a_sensor_without_a_declared_unit_is_refused(tmp_path, facts):
    error = refused(tmp_path, facts, sensors="temperature = 30")
    assert "[sim.sensor_facts]" in error.where
    assert "declares none for 'temperature'" in error.why
    assert 'unit = "C"' in error.how


def test_bands_for_a_criterion_the_gate_reads_as_a_bool_are_refused(tmp_path):
    error = refused(tmp_path, heat(hot=f"bands = {FULL}"))
    assert "[sim.sensor_facts] hot -> bands" in error.where
    assert "evaluates 'hot' as 'bool'" in error.why


def test_bands_no_gate_reads_are_refused(tmp_path):
    typo = f'\nheat_levl = {{ sensor = "temperature", bands = {FULL} }}'
    error = refused(tmp_path, GOOD + typo)
    assert "[sim.sensor_facts] heat_levl -> bands" in error.where
    assert "no gate of the agent evaluates 'heat_levl'" in error.why


def test_a_sensor_fact_on_a_sensor_the_board_lacks_is_refused_at_load(tmp_path):
    with pytest.raises(BoardCapabilityError, match="co2"):
        SimSession.load(agent(tmp_path, GOOD + '\nair = { sensor = "co2" }'))


def test_a_misspelt_rule_key_is_refused(tmp_path):
    error = refused(tmp_path, 'heat = { sensor = "temperature", band = { low = 0 } }')
    assert "[sim.sensor_facts] heat" in error.where
    assert "`bands`" in error.why
