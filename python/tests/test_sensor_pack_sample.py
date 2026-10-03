"""
TSK-I2a-02/03/04 — the sample agent of the sensor pack, `fixtures/agents/rail-gate`, and its
corpus `fixtures/traces/sensor-pack/` (I2a exit criterion 3, RFC-0013 §3f item 7).

A battery-powered gate: `digital.in` (the limit switch) and `analog.in` (the rail through a
divider) decide `rail_open_gate`; `i2c` (an ina219) is read inside `rail_report`'s body and never
enters a gate. It builds for `sim-rpi5` and `linux-rpi5` and is refused on a board without the
primitives. The corpus is what the agent records, replays on every board that declares the three
primitives, and is counted apart from the canonical traces. The agent on gpio-sim + i2c-stub is
`tests_linux/test_rail_gate.py`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

import neuroedge.hal.linux as linux
from neuroedge.cli.main import app
from neuroedge.engine.compiler import build
from neuroedge.errors import AgentManifestError, BoardCapabilityError, BuildFailed
from neuroedge.sim import SimSession
from neuroedge.testing import assert_matches_golden, replay
from neuroedge.trace import validate_trace

from .test_hal_linux import LINES, FakeGpiod

runner = CliRunner()


@pytest.fixture
def agent(root) -> Path:
    return root / "fixtures" / "agents" / "rail-gate" / "agent.toml"


def corpus(root: Path) -> list[Path]:
    return sorted((root / "fixtures" / "traces" / "sensor-pack").glob("*.json"))


def load(agent: Path):
    return SimSession.load(agent, board_id="sim-rpi5")


async def call(session, tool: str):
    from neuroedge.actions.tools import ToolCall

    result = await session.call_tool(ToolCall(tool, {}, source="local_grammar"))
    return result.action


# -- build ----------------------------------------------------------------------------------


@pytest.mark.parametrize(("target", "board"), [("sim", "sim-rpi5"), ("linux", "linux-rpi5")])
def test_the_sample_builds_on_the_boards_that_declare_the_three_primitives(agent, target, board):
    report = build(agent, target=target, board_id=board)
    assert report.board == board and report.requirements == 5 and report.actions == 2


@pytest.mark.parametrize(
    ("target", "board"), [("sim", "sim-default"), ("esp32s3", "esp32s3-box-3")]
)
def test_a_board_without_the_primitives_refuses_the_sample_naming_each_missing_one(
    agent, target, board
):
    with pytest.raises(BuildFailed) as raised:
        build(agent, target=target, board_id=board)
    whys = " ".join(e.why for e in raised.value.problems)
    for primitive in ("digital.in", "analog.in", "i2c"):
        assert f"does not provide {primitive}" in whys, (board, primitive)


def test_the_default_sim_board_names_the_board_that_has_the_pack(agent):
    with pytest.raises(BuildFailed) as raised:
        build(agent, target="sim")
    assert any("--board sim-rpi5" in e.how for e in raised.value.problems)


# -- the agent on sim -----------------------------------------------------------------------


async def test_a_closed_gate_on_a_healthy_rail_opens(agent):
    session = load(agent)
    action = await call(session, "rail_open_gate")
    assert not action.blocked and session.hal.pin("gate_relay").commands == [("pulse", 20000)]
    facts = session.events.of_type("gate_facts")[-1]
    assert facts["limit_closed"]["value"] is True and facts["rail_voltage"]["value"] == 1.8
    assert facts["rail_voltage"]["age_ms"] >= 0


@pytest.mark.parametrize(
    ("set_up", "criterion"),
    [
        (lambda s: s.set_analog("adc0", 1.19), "rail_voltage"),  # the closed lower bound is 1.2
        (lambda s: s.hal.set_digital_in("limit_switch", False), "limit_closed"),
    ],
    ids=["a sagging rail", "a gate off its stop"],
)
async def test_a_condition_the_gate_does_not_admit_blocks_without_a_pulse(agent, set_up, criterion):
    session = load(agent)
    set_up(session)
    action = await call(session, "rail_open_gate")
    assert action.blocked and action.gate.reason == "condition_not_met"
    assert action.gate.failed_criterion == criterion
    assert session.hal.pin("gate_relay").never_pulsed()


async def test_the_rail_bound_is_closed_at_exactly_1_2_volts(agent):
    session = load(agent)
    session.set_analog("adc0", 1.2)
    assert not (await call(session, "rail_open_gate")).blocked


@pytest.mark.parametrize(
    "break_it",
    [
        lambda s: s.set_analog("adc0", 2.6),  # past the channel's range: a fault, never a clamp
        lambda s: s.set_analog("adc0", float("nan")),
        lambda s: s.hal._analog.pop("adc0"),
        lambda s: s.hal._levels.pop("limit_switch"),
    ],
    ids=["ADC past range", "ADC NaN", "ADC never set", "limit line never set"],
)
async def test_a_read_that_fails_blocks_criterion_unavailable_never_allows(agent, break_it):
    session = load(agent)
    break_it(session)
    action = await call(session, "rail_open_gate")
    assert action.blocked and action.gate.reason == "criterion_unavailable"
    assert session.hal.pin("gate_relay").never_pulsed()


async def test_the_supply_is_read_over_i2c_inside_the_action_and_shown(agent):
    session = load(agent)
    action = await call(session, "rail_report")
    assert not action.blocked
    assert session.events.of_type("i2c_read") == [
        {"bus": "i2c1", "device": "ina219", "address": 0x40, "register": 2, "value": 24000}
    ]
    assert session.hal.frames[-1].text == "Nguồn: 12000 mV"
    # I2C is not a gate fact: the report's gate reads only who asked.
    assert set(session.events.of_type("gate_facts")[-1]) == {"call_source"}


async def test_a_dead_ina219_raises_ne5001_out_of_the_action_and_shows_nothing(agent):
    from neuroedge.errors import PerceptionUnavailableError
    from neuroedge.hal.i2c_bus import ReadFault

    session = load(agent)
    session.hal.script_i2c("i2c1", "ina219", 2, [ReadFault("NACK")], width=2)
    with pytest.raises(PerceptionUnavailableError) as raised:
        await call(session, "rail_report")
    assert raised.value.code == "NE5001"
    assert session.hal.frames == []


# -- [sim.i2c] ------------------------------------------------------------------------------


def edit(agent: Path, tmp_path: Path, old: str, new: str) -> Path:
    """A copy of the sample with one line changed (@action names are process-wide: renamed)."""
    import shutil

    copy = tmp_path / "rail-gate"
    shutil.copytree(agent.parent, copy)
    text = (copy / "agent.toml").read_text(encoding="utf-8")
    assert old in text
    (copy / "agent.toml").write_text(text.replace(old, new), encoding="utf-8")
    suffix = f"_{abs(hash(str(tmp_path)))}"
    for tool in ("rail_open_gate", "rail_report"):
        for file, pattern in (
            ("actions/rail_gate.py", 'name="{}"'),
            ("commands.toml", 'tool     = "{}"'),
        ):
            path = copy / file
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    pattern.format(tool), pattern.format(tool + suffix)
                ),
                encoding="utf-8",
            )
    return copy / "agent.toml"


@pytest.mark.parametrize(
    ("old", "new", "match"),
    [
        ('"0x02" = { value = 24000, width = 2 }', '"0x02" = { value = 70000, width = 2 }', "fits"),
        ('"0x02" = { value = 24000, width = 2 }', '"0x02" = { value = 1, width = 3 }', "fits"),
        ('"0x02" = { value = 24000, width = 2 }', '"zz" = 5', "not a register"),
        ('"0x02" = { value = 24000, width = 2 }', '"0x02" = { value = true }', "not a register"),
        ('[sim.i2c."i2c1/ina219"]', '[sim.i2c."ina219"]', "bus/device"),
    ],
)
def test_a_malformed_sim_i2c_table_is_a_manifest_error(agent, tmp_path, old, new, match):
    broken = edit(agent, tmp_path, old, new)
    with pytest.raises(BuildFailed) as raised:
        build(broken, target="sim", board_id="sim-rpi5")
    (error,) = raised.value.problems
    assert isinstance(error, AgentManifestError) and match in error.why


def test_sim_i2c_serves_only_what_the_board_lets_an_agent_read(agent, tmp_path):
    broken = edit(agent, tmp_path, '"0x02" = {', '"0x09" = {')  # ina219 lists 0x01..0x04
    with pytest.raises(BuildFailed) as raised:
        build(broken, target="sim", board_id="sim-rpi5")
    (error,) = raised.value.problems
    assert isinstance(error, BoardCapabilityError) and "0x09" in error.why


def test_sim_i2c_of_a_device_requires_does_not_list_is_refused(agent, tmp_path):
    broken = edit(agent, tmp_path, '"i2c"         = { devices = ["i2c1/ina219"] }\n', "")
    with pytest.raises(BuildFailed) as raised:
        build(broken, target="sim", board_id="sim-rpi5")
    assert any("[requires] i2c does not list i2c1/ina219" in e.why for e in raised.value.problems)


# -- the corpus -----------------------------------------------------------------------------


def test_the_corpus_is_what_the_sample_agent_records(root):
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "gen_sensor_pack_traces.py"), "--check"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr


def test_the_corpus_holds_an_allow_two_sensor_blocks_and_three_failed_reads(root):
    outcomes = {
        path.stem: [
            (e["data"]["verdict"], e["data"].get("reason"), e["data"].get("failed_criterion"))
            for e in json.loads(path.read_text(encoding="utf-8"))["events"]
            if e["type"] == "gate_evaluation_result"
        ]
        for path in corpus(root)
    }
    assert outcomes == {
        "rail-gate-allow": [("ALLOW", None, None), ("ALLOW", None, None)],
        "rail-gate-block": [
            ("BLOCK", "condition_not_met", "rail_voltage"),
            ("BLOCK", "condition_not_met", "limit_closed"),
        ],
        "rail-gate-unavailable": [
            ("BLOCK", "criterion_unavailable", "rail_voltage"),  # the ADC read past its range
            ("BLOCK", "criterion_unavailable", "rail_voltage"),  # 501 ms old, the gate allows 500
            ("BLOCK", "criterion_unavailable", "limit_closed"),  # a line nobody set
        ],
    }


def test_the_corpus_records_the_marks_the_replay_recomputes_the_age_from(root):
    trace = json.loads((corpus(root)[2]).read_text(encoding="utf-8"))
    stale = [e["data"] for e in trace["events"] if e["type"] == "gate_facts"][1]["rail_voltage"]
    assert stale["age_ms"] == stale["eval_offset_ms"] - stale["read_offset_ms"] == 501


def test_the_corpus_validates_and_reads_every_primitive_of_the_pack(root):
    seen = set()
    for path in corpus(root):
        trace = json.loads(path.read_text(encoding="utf-8"))
        validate_trace(trace)
        seen |= {e["type"] for e in trace["events"]}
    assert {"digital_in", "analog_in", "i2c_read", "display_frame", "actuator_command"} <= seen


@pytest.fixture
def gpio(monkeypatch, tmp_path):
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    fake = FakeGpiod({str(chip): LINES})
    monkeypatch.setattr(linux, "CHIP_GLOB", str(tmp_path / "gpiochip*"))
    monkeypatch.setattr(linux, "_import_gpiod", lambda: fake)
    return fake


@pytest.mark.parametrize(("target", "board"), [("sim", "sim-rpi5"), ("linux", "linux-rpi5")])
def test_the_corpus_replays_to_what_it_recorded_on_every_board_with_the_pack(
    root, agent, gpio, target, board
):  # on linux a replay does drive the (fake) lines, as the canonical traces do
    for path in corpus(root):
        recorded = json.loads(path.read_text(encoding="utf-8"))
        result = replay(path, agent=agent, target=target, board_id=board)
        assert result.verdicts == [
            e["data"]["verdict"]
            for e in recorded["events"]
            if e["type"] == "gate_evaluation_result"
        ], path.name
        assert result.warnings == [] and result.divergences == []
        assert_matches_golden(result, recorded)


def test_verify_replays_the_corpus_where_the_pack_is_declared_and_skips_it_elsewhere():
    result = runner.invoke(app, ["verify", "--targets", "sim"])
    assert result.exit_code == 0, result.output
    rows = [line for line in result.output.splitlines() if "sensor-pack/rail-gate-" in line]
    assert len(rows) == 6  # three validated, three in the table
    table = [line for line in rows if "│" in line]
    assert len(table) == 3
    for line in table:
        cells = [cell.strip() for cell in line.split("│") if cell.strip()]
        assert cells[1] == "—" and cells[2].startswith("✓"), (
            line
        )  # sim-default skips, sim-rpi5 passes
    # Counted apart: the canonical replays stay 3 per board, the corpus is 3 on sim-rpi5 only.
    assert "3 replay(s) on sim/sim-default, 3 replay(s) on sim/sim-rpi5" in result.output
    assert "3 on sim/sim-rpi5" in result.output
    pack = result.output.split("The `sensor-pack` corpus replays alike:")[1]
    assert "sim/sim-default" not in pack.split(".")[0]


def test_a_corpus_a_board_cannot_replay_does_not_make_that_board_pass(root, monkeypatch):
    """`verify` fails when no board replayed the corpus at all: zero is a failure, never a pass."""
    import neuroedge.cli.main as main

    monkeypatch.setattr(
        main, "REFERENCE_BOARDS", {"sim": ("sim-default",), "linux": ("linux-rpi5",)}
    )
    result = runner.invoke(app, ["verify", "--targets", "sim"])
    assert result.exit_code != 0, result.output
    assert "sensor-pack corpus replays compared" in result.output
