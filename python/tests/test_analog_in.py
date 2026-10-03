"""
TSK-I2a-04 — `analog.in` (ADC) on `sim` and `linux`, into the gate as a `numeric` criterion
(RFC-0007 §3c, §9.10; RFC-0009 §3c, §3f; Q-62).

A channel is `{name, unit, min, max}` in the board; an agent binds a numeric criterion to it
with ``line_voltage = { channel = "adc0" }`` under `[sim.analog_facts]`. `neuroedge build`
checks the binding (unit, range), `gate lint` refuses a numeric criterion in
`on_block.confirms`, and at run time a reading enters the gate as a `Fact` with the mark of
its HAL read, from which the engine computes `age_ms`. Any read failure BLOCKs
`criterion_unavailable`. The `linux` HAL against a fake sysfs is `test_hal_linux_analog.py`;
against the kernel (`i2c-stub` + `ads7828`), `tests_linux/test_analog_in.py`.
"""

from __future__ import annotations

import json
import math

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.engine.compiler import build
from neuroedge.errors import (
    AgentManifestError,
    BoardCapabilityError,
    BuildFailed,
    GateSchemaError,
    PerceptionUnavailableError,
)
from neuroedge.hal.sim import SimHAL
from neuroedge.sim import SimSession
from neuroedge.sim.ui import SessionServer
from neuroedge.testing import TracePlayer
from neuroedge.testing.recorder import TraceRecorder

from .hand_clock import PAST_THE_ENVELOPE_MS, HandClock

runner = CliRunner()

GATE = """\
schema: neuroedge.gate/v1
name: {name}
version: 1.0.0
evaluate:
  line_voltage:
    type: numeric
    unit: {unit}
    range: {{ min: {low}, max: {high} }}
    max_age_ms: {max_age_ms}
    instructions: Voltage after the divider
allow_when:
  line_voltage: {{ gte: 1.0, lt: 2.0 }}
on_block:
{on_block}
budget:
  p95_latency_ms: 100
  fail: closed
"""
DENY = "  action: deny"
ASK = '  action: ask\n  message: "Sure?"\n  confirms: [line_voltage]'


def agent(
    tmp_path,
    *,
    unit="V",
    low=0.0,
    high=2.5,
    max_age_ms=500,
    on_block=DENY,
    analog="adc0 = 1.5",
    facts='line_voltage = { channel = "adc0" }',
    requires='"analog.in" = { channels = ["adc0"] }',
):
    """`bật quạt` behind a gate that reads the ADC voltage; built for the `sim-rpi5` board."""
    name = f"adc_{abs(hash(str(tmp_path)))}"  # @action names are process-wide
    (tmp_path / "actions").mkdir(parents=True, exist_ok=True)
    (tmp_path / "actions" / "fan.py").write_text(
        "from neuroedge import action\n"
        "from neuroedge.hal import digital\n\n"
        f'@action(name="{name}_on", requires="digital.out:gate_relay", gate="volt")\n'
        "def fan_on() -> None:\n"
        '    digital.out("gate_relay").on()\n',
        encoding="utf-8",
    )
    (tmp_path / "volt.yaml").write_text(
        GATE.format(
            name="volt", unit=unit, low=low, high=high, max_age_ms=max_age_ms, on_block=on_block
        ),
        encoding="utf-8",
    )
    (tmp_path / "commands.toml").write_text(
        f'[grammar]\nversion = 1\n\n[[command]]\nintent = "fan_on"\npatterns = ["bật quạt"]\n'
        f'tool = "{name}_on"\n',
        encoding="utf-8",
    )
    (tmp_path / "agent.toml").write_text(
        '[agent]\nname = "adc-test"\nversion = "0.1.0"\n\n'
        f'[requires]\n"digital.out" = {{ pins = ["gate_relay"] }}\n{requires}\n\n'
        '[gates]\nvolt = "volt.yaml"\n\n'
        f"[sim.analog]\n{analog}\n\n[sim.analog_facts]\n{facts}\n",
        encoding="utf-8",
    )
    return tmp_path / "agent.toml"


def load(path, **kwargs):
    return SimSession.load(path, board_id="sim-rpi5", **kwargs)


def problems(path, board="sim-rpi5", target="sim"):
    with pytest.raises(BuildFailed) as raised:
        build(path, target=target, board_id=board)
    return raised.value.problems


# --- build: the channel against the criterion (RFC-0007 §3c, RFC-0009 §3f) -----------------


def test_an_agent_whose_criterion_fits_its_channel_builds(tmp_path):
    report = build(agent(tmp_path), target="sim", board_id="sim-rpi5")
    assert report.board == "sim-rpi5"


@pytest.mark.parametrize(
    ("low", "high"),
    [(0.0, 2.5), (-1.0, 2.5), (0.0, 3.3), (-5, 5)],
    ids=["equal", "wider below", "wider above", "wider both"],
)
def test_a_criterion_range_that_contains_the_channel_range_builds(tmp_path, low, high):
    build(agent(tmp_path, low=low, high=high), target="sim", board_id="sim-rpi5")


@pytest.mark.parametrize(
    ("low", "high", "word"),
    [
        (0.1, 2.5, "[0.1, 2.5]"),  # the channel reads down to 0.0: below the criterion's range
        (0.0, 2.4, "[0.0, 2.4]"),  # and up to 2.5: above it
        (1.0, 2.0, "[1.0, 2.0]"),
    ],
    ids=["channel below", "channel above", "channel on both sides"],
)
def test_a_criterion_range_the_channel_can_leave_is_refused_at_build(tmp_path, low, high, word):
    (error,) = problems(agent(tmp_path, low=low, high=high))
    assert isinstance(error, BoardCapabilityError) and error.code == "NE3001"
    assert "line_voltage" in error.where and word in error.why and "adc0" in error.why


@pytest.mark.parametrize("unit", ["mV", "A", "v"])
def test_a_criterion_in_another_unit_than_the_channel_is_refused_at_build(tmp_path, unit):
    (error,) = problems(agent(tmp_path, unit=unit, high=2500 if unit == "mV" else 2.5))
    assert isinstance(error, BoardCapabilityError) and error.code == "NE3001"
    assert f"'{unit}'" in error.why and "'V'" in error.why and "converts nothing" in error.why


def test_both_a_wrong_unit_and_a_wrong_range_are_reported_together(tmp_path):
    errors = problems(agent(tmp_path, unit="A", low=1.0, high=2.0))
    assert [e.code for e in errors] == ["NE3001", "NE3001"]


def test_a_channel_binding_a_bool_or_level_criterion_is_refused(tmp_path):
    path = agent(tmp_path)
    gate = (tmp_path / "volt.yaml").read_text(encoding="utf-8")
    numeric = gate.split("evaluate:\n")[1].split("allow_when:")[0]
    gate = gate.replace(numeric, "  line_voltage:\n    type: bool\n    instructions: ok\n")
    gate = gate.replace("{ gte: 1.0, lt: 2.0 }", "true")
    (tmp_path / "volt.yaml").write_text(gate, encoding="utf-8")
    (error,) = problems(path)
    assert error.code == "NE3001" and "feeds only a 'numeric' criterion" in error.why


def test_a_binding_no_gate_reads_is_refused(tmp_path):
    (error,) = problems(agent(tmp_path, facts='pressure = { channel = "adc0" }'))
    assert error.code == "NE3002" and "no gate of the agent evaluates 'pressure'" in error.why


def test_a_channel_the_board_does_not_declare_is_refused(tmp_path):
    errors = problems(
        agent(
            tmp_path,
            requires='"analog.in" = { channels = ["adc7"] }',
            facts='line_voltage = { channel = "adc7" }',
        )
    )
    (error,) = errors
    assert error.code == "NE3001" and "analog.in:adc7" in error.where
    assert "analog.in:['adc0']" in error.why  # what the board does offer


def test_a_binding_to_a_channel_requires_does_not_declare_is_refused(tmp_path):
    (error,) = problems(agent(tmp_path, requires='"display" = {}'))
    assert "not one [requires] declares for analog.in" in error.why


def test_analog_in_on_a_board_without_it_is_refused(tmp_path):
    path = agent(tmp_path)
    for board, target in (("sim-default", "sim"), ("esp32s3-box-3", "esp32s3")):
        errors = problems(path, board=board, target=target)
        assert any("does not provide analog.in" in e.why for e in errors), board


@pytest.mark.parametrize(
    "requires",
    ['"analog.in" = {}', '"analog.in" = { channels = [] }', '"analog.in" = { channels = "adc0" }'],
    ids=["no channels", "empty", "a string"],
)
def test_requires_analog_in_must_name_its_channels(tmp_path, requires):
    errors = problems(agent(tmp_path, requires=requires))
    assert any("non-empty list of channel names" in e.why for e in errors)


@pytest.mark.parametrize(
    "facts",
    [
        'line_voltage = { channel = "adc0", unit = "V" }',
        'line_voltage = "adc0"',
        "line_voltage = {}",
    ],
)
def test_a_malformed_analog_fact_is_a_manifest_error(tmp_path, facts):
    (error,) = problems(agent(tmp_path, facts=facts))
    assert isinstance(error, AgentManifestError) and "exactly `channel = <name>`" in error.why


def test_a_criterion_fed_by_a_sensor_and_a_channel_is_refused(tmp_path):
    path = agent(tmp_path)
    path.write_text(
        path.read_text(encoding="utf-8")
        + '\n[sim.sensor_facts]\nline_voltage = { sensor = "temperature" }\n',
        encoding="utf-8",
    )
    errors = problems(path)
    assert any("two readings would feed it" in e.why for e in errors)


# --- gate lint: a measurement is never confirmed by a person (RFC-0009 §3a) ----------------


def test_a_numeric_criterion_bound_to_a_channel_cannot_be_in_confirms(tmp_path):
    """RFC-0009 refuses a numeric criterion in `on_block.confirms` outright, bound or not."""
    errors = problems(agent(tmp_path, on_block=ASK))
    (error,) = [e for e in errors if isinstance(e, GateSchemaError)]
    assert error.code == "NE2002" and "line_voltage" in error.why


def test_gate_lint_refuses_the_same_gate(tmp_path):
    agent(tmp_path, on_block=ASK)
    (tmp_path / "gates").mkdir()
    (tmp_path / "volt.yaml").rename(tmp_path / "gates" / "volt.yaml")
    result = runner.invoke(app, ["gate", "lint", str(tmp_path / "gates")])
    assert result.exit_code == 1 and "NE2002" in result.output


# --- sim: a value set in [sim.analog], the REPL and the UI ---------------------------------


async def test_a_reading_inside_the_gate_interval_allows_and_a_reading_outside_blocks(tmp_path):
    clock = HandClock()
    session = load(agent(tmp_path), clock=clock)
    allowed = await session.handle("bật quạt")
    assert allowed.allowed and session.hal.pin("gate_relay").commands == [("on", 0)]
    for value, reason in ((0.99, "condition_not_met"), (2.0, "condition_not_met")):
        session.set_analog("adc0", value)
        turn = await session.handle("bật quạt")
        assert turn.result.blocked and turn.result.gate.reason == reason, value
    session.set_analog("adc0", 1.0)  # the lower bound is closed
    clock.advance(PAST_THE_ENVELOPE_MS)  # the first `on` is over: the envelope allows the next
    assert (await session.handle("bật quạt")).allowed
    assert session.hal.pin("gate_relay").commands == [("on", 0)] * 2


async def test_each_read_is_recorded_and_the_fact_carries_its_read_marks(tmp_path):
    session = load(agent(tmp_path))
    await session.handle("bật quạt")
    assert session.events.of_type("analog_in") == [
        {"channel": "adc0", "value": 1.5, "unit": "V", "use": "fact"}
    ]
    entry = session.events.of_type("gate_facts")[-1]["line_voltage"]
    assert entry["value"] == 1.5 and entry["source"] == "context"
    assert entry["age_ms"] == entry["eval_offset_ms"] - entry["read_offset_ms"] >= 0


@pytest.mark.parametrize(
    ("value", "why"),
    [
        (2.5000001, "outside the range [0.0, 2.5]"),  # past the top: a fault, not "2.5"
        (-0.0001, "outside the range"),
        (float("nan"), "not a finite number"),
        (float("inf"), "not a finite number"),
        ("1.5", "not a finite number"),
        (True, "not a finite number"),
    ],
    ids=repr,
)
async def test_a_reading_the_channel_cannot_give_blocks_criterion_unavailable(tmp_path, value, why):
    session = load(agent(tmp_path))
    session.set_analog("adc0", value)
    turn = await session.handle("bật quạt")
    assert turn.result.blocked and turn.result.gate.reason == "criterion_unavailable"
    assert session.hal.pin("gate_relay").never_pulsed()
    (failed,) = session.events.of_type("analog_in")
    assert failed["channel"] == "adc0" and "value" not in failed and why in failed["error"]
    assert session.events.of_type("gate_facts")[-1]["line_voltage"]["value"] is None


async def test_a_value_exactly_at_a_channel_edge_is_a_valid_reading(tmp_path):
    session = load(agent(tmp_path))
    for edge in (0.0, 2.5):
        session.set_analog("adc0", edge)
        assert session.hal.analog_in("adc0") == edge
    turn = await session.handle("bật quạt")  # 2.5 V is above `lt: 2.0`: decided, not unavailable
    assert turn.result.gate.reason == "condition_not_met"


async def test_a_channel_nobody_set_is_unavailable_not_a_default(tmp_path):
    session = load(agent(tmp_path, analog="# nothing set"))
    turn = await session.handle("bật quạt")
    assert turn.result.blocked and turn.result.gate.reason == "criterion_unavailable"
    assert "no value for this channel" in session.events.of_type("analog_in")[-1]["error"]


def test_the_hal_raises_ne5001_for_a_failed_read():
    from neuroedge.hal.board import load_board_by_id

    hal = SimHAL(load_board_by_id("sim-rpi5"))
    with pytest.raises(PerceptionUnavailableError) as raised:
        hal.analog_in("adc0")
    assert raised.value.code == "NE5001" and "set_analog" in raised.value.how
    hal.set_analog("adc0", 9.0)
    with pytest.raises(PerceptionUnavailableError, match="outside the range"):
        hal.analog_in("adc0")
    with pytest.raises(BoardCapabilityError, match="adc7"):
        hal.analog_in("adc7")
    with pytest.raises(BoardCapabilityError, match="adc7"):
        hal.set_analog("adc7", 1.0)


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


async def test_a_reading_older_than_max_age_is_unavailable_and_exactly_that_old_is_valid(tmp_path):
    clock = Clock()
    session = load(agent(tmp_path, max_age_ms=500), clock=clock)
    read = session.hal.analog_in

    def slow(*args, **kwargs):  # the read finishes long after its mark: the fact is that old
        value = read(*args, **kwargs)
        clock.now += slow.delay
        return value

    session.hal.analog_in = slow
    slow.delay = 500  # age == max_age_ms passes (RFC-0009 §3c)
    assert (await session.handle("bật quạt")).allowed
    entry = session.events.of_type("gate_facts")[-1]["line_voltage"]
    assert entry["age_ms"] == 500
    slow.delay = 501
    turn = await session.handle("bật quạt")
    assert turn.result.blocked and turn.result.gate.reason == "criterion_unavailable"
    assert session.events.of_type("gate_facts")[-1]["line_voltage"]["age_ms"] == 501


async def test_a_read_mark_after_the_evaluation_instant_is_unavailable(tmp_path):
    clock = Clock()
    session = load(agent(tmp_path), clock=clock)
    read = session.hal.analog_in

    def backwards(*args, **kwargs):  # the clock steps back after the read: a negative age
        value = read(*args, **kwargs)
        clock.now -= 100
        return value

    session.hal.analog_in = backwards
    turn = await session.handle("bật quạt")
    assert turn.result.blocked and turn.result.gate.reason == "criterion_unavailable"
    assert session.events.of_type("gate_facts")[-1]["line_voltage"]["age_ms"] < 0
    assert session.hal.pin("gate_relay").never_pulsed()


# --- the same, from the REPL and the UI -----------------------------------------------------


def test_the_repl_sets_a_channel_and_the_verdict_follows(tmp_path):
    path = agent(tmp_path)
    stdin = ":analogs\n:analog adc0 0.5\nbật quạt\n:analog adc0 1.5\nbật quạt\n:facts\nexit\n"
    result = runner.invoke(app, ["run", "--agent", str(path), "--board", "sim-rpi5"], input=stdin)
    assert result.exit_code == 0, result.output
    assert "1.5 V" in result.output  # :analogs, from [sim.analog]
    assert "adc0 = 0.5" in result.output
    assert "criterion: line_voltage" in result.output  # the BLOCK, then an ALLOW
    assert "from analog.in adc0" in result.output  # :facts


def test_set_fact_refuses_a_criterion_a_channel_decides(tmp_path):
    session = load(agent(tmp_path))
    with pytest.raises(Exception, match="analog.in channel 'adc0'"):
        session.set_fact("line_voltage", 1.5)


def test_a_fixed_fact_for_a_bound_criterion_is_refused_at_load(tmp_path):
    path = agent(tmp_path)
    with pytest.raises(AgentManifestError, match="would never be used"):
        load(path, facts={"line_voltage": 1.5})


def test_the_ui_sets_a_channel(tmp_path):
    session = load(agent(tmp_path))
    server = SessionServer(session)
    try:
        assert server.command(":analog adc0 1.25") == {"ok": True, "analog": "adc0"}
        assert session.hal.analog_values()["adc0"] == (1.25, "V")
        reply = server.command(":analog adc9 1.0")
        assert reply["ok"] is False and "adc9" in reply["error"]["why"]
    finally:
        server.httpd.server_close()
    assert session.events.of_type("analog_set") == [{"channel": "adc0", "value": 1.25}]


# --- replay recomputes the verdict from the recorded reading, age included -----------------


async def test_replay_reproduces_every_verdict_from_the_recorded_readings(tmp_path):
    path = agent(tmp_path)
    clock = HandClock()
    recorder = TraceRecorder(clock=clock)
    session = load(path, events=recorder, clock=clock)
    for value in (1.5, 0.5, float("nan"), 2.5, 1.0):
        session.set_analog("adc0", value)
        await session.handle("bật quạt")
        clock.advance(PAST_THE_ENVELOPE_MS)  # the envelope lets the next `on` of the fan relay in
    out = tmp_path / "adc.json"
    session.write_trace(out)
    trace = json.loads(out.read_text(encoding="utf-8"))
    assert [e["data"]["verdict"] for e in trace["events"] if e["type"] == "gate_evaluation_result"] == [
        "ALLOW", "BLOCK", "BLOCK", "BLOCK", "ALLOW",
    ]  # fmt: skip

    result = await TracePlayer(out, agent=path, board_id="sim-rpi5").replay()
    assert result.verdicts == result.recorded_verdicts
    assert result.warnings == []
    recorded = [e["data"]["line_voltage"] for e in trace["events"] if e["type"] == "gate_facts"]
    replayed = [
        e["data"]["line_voltage"] for e in result.replayed["events"] if e["type"] == "gate_facts"
    ]
    seen = [(f["value"], f.get("age_ms")) for f in replayed]
    assert seen == [(f["value"], f.get("age_ms")) for f in recorded]
    assert [age is None for _, age in seen] == [False, False, True, False, False]  # NaN: no mark


async def test_replay_distrusts_a_trace_whose_age_was_altered(tmp_path):
    path = agent(tmp_path)
    recorder = TraceRecorder()
    session = load(path, events=recorder)
    await session.handle("bật quạt")
    trace = recorder.to_trace()
    for event in trace["events"]:
        if event["type"] == "gate_facts":
            event["data"]["line_voltage"]["age_ms"] = 0
            event["data"]["line_voltage"]["read_offset_ms"] = 99999  # a reading from the future
    result = await TracePlayer(trace, agent=path, board_id="sim-rpi5").replay()
    assert result.verdicts == ["BLOCK"] and result.warnings


def test_the_recorded_trace_is_strict_json(tmp_path):
    path = agent(tmp_path)
    session = load(path, events=TraceRecorder())
    session.set_analog("adc0", math.nan)
    out = tmp_path / "nan.json"
    session.write_trace(out)
    assert "NaN" not in out.read_text(encoding="utf-8")


async def test_a_hal_that_let_an_out_of_range_value_through_is_still_judged_by_the_engine(tmp_path):
    """Defence in depth: the criterion's own range catches what a faulty driver did not refuse."""
    session = load(agent(tmp_path))
    session.hal.analog_in = lambda *args, **kwargs: 3.0  # beyond the channel's 2.5 V
    turn = await session.handle("bật quạt")
    assert turn.result.blocked and turn.result.gate.reason == "value_out_of_range"
    assert session.hal.pin("gate_relay").never_pulsed()
