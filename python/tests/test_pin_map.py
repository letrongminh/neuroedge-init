"""
The per-board pin map (docs/spec/virtual_parts.md §3.3, Q-84 phase A+, TSK-I2d-32).

`[targets.<board-id>.pins]` lets an agent keep its own pin names (`heater`, `air_pump`) on a real
board: the board's pin, envelope and backend do the work, the agent's name is what actions,
gates, commands and traces say. Each test names the test case of the specification it implements;
the same agent on gpio-sim is `tests_linux/test_pin_map_linux.py`.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neuroedge.actions.tools import ToolCall
from neuroedge.cli.main import app
from neuroedge.engine.compiler import build
from neuroedge.errors import AgentManifestError, BoardCapabilityError
from neuroedge.hal.board import load_board_by_id
from neuroedge.hal.virtual_board import resolve_board
from neuroedge.paths import repo_root
from neuroedge.sim import SimSession
from neuroedge.testing import TracePlayer
from neuroedge.testing.recorder import TraceRecorder
from neuroedge.trace import validate_trace

from .hand_clock import HandClock
from .test_c_bridge import built, same_contract

ROOT = repo_root()
runner = CliRunner()

GATE = """schema:  neuroedge.gate/v1
name:    {gate}
version: 1.0.0
evaluate:
  owner_ok:
    type: bool
    instructions: "Chủ nhà cho phép"
allow_when:
  owner_ok: true
on_block:
  action:  deny
  message: "Không làm."
budget:
  p95_latency_ms: 150
  fail:           closed
"""

HEATER = '"digital.out" = { pins = ["heater", "air_pump"] }'
WIRING = '[targets.{board}.pins]\nheater = "gate_relay"\nair_pump = "door_lock"\n'
BOARDS = ("sim-default", "esp32s3-box-3", "linux-rpi5")


@pytest.fixture(autouse=True)
def own_actions():
    """These agents register their @actions process-wide; put the registry back after each test."""
    import sys

    from neuroedge.actions import REGISTRY

    saved, modules = dict(REGISTRY), set(sys.modules)
    yield
    REGISTRY.clear()
    REGISTRY.update(saved)
    for module in set(sys.modules) - modules:
        if module.startswith("neuroedge_agent_"):
            del sys.modules[module]


def make_agent(root: Path, extra: str = "", *, requires: str = HEATER, wire: bool = True) -> Path:
    """An agent with a `heater` and an `air_pump`, wired to a relay and a lock by default."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "actions").mkdir(exist_ok=True)
    (root / "gates").mkdir(exist_ok=True)
    maps = "".join(WIRING.format(board=board) for board in BOARDS) if wire else ""
    (root / "agent.toml").write_text(
        '[agent]\nname = "tank"\nversion = "0.1.0"\n\n'
        f"[requires]\n{requires}\n\n"
        '[gates]\nswitch = "gates/switch@1.0.0.yaml"\n\n'
        '[targets]\nsupported = ["sim", "linux", "esp32s3"]\n'
        f"{maps}{extra}\n"
        "[sim.facts]\nowner_ok = true\n",
        encoding="utf-8",
    )
    (root / "actions" / "tank.py").write_text(
        "from neuroedge import action, digital\n\n\n"
        '@action(name="pm_heater_on", requires="digital.out:heater", gate="switch")\n'
        "def pm_heater_on() -> None:\n"
        '    """Turn the heater on."""\n'
        '    digital.out("heater").on()\n\n\n'
        '@action(name="pm_pump_on", requires="digital.out:air_pump", gate="switch")\n'
        "def pm_pump_on() -> None:\n"
        '    """Turn the air pump on."""\n'
        '    digital.out("air_pump").on()\n',
        encoding="utf-8",
    )
    (root / "gates" / "switch@1.0.0.yaml").write_text(GATE.format(gate="switch"), encoding="utf-8")
    (root / "commands.toml").write_text(
        "[grammar]\nversion = 1\nthreshold = 0.80\n\n"
        '[[command]]\nintent = "heat"\npatterns = ["bật sưởi"]\n'
        'facts = { owner_ok = true }\ntool = "pm_heater_on"\n\n'
        '[[command]]\nintent = "pump"\npatterns = ["bật sục khí"]\n'
        'facts = { owner_ok = true }\ntool = "pm_pump_on"\n',
        encoding="utf-8",
    )
    return root / "agent.toml"


def say(session: SimSession, text: str):
    return asyncio.run(session.handle(text))


def pins_of(session: SimSession, kind: str = "actuator_command") -> list[str]:
    return [event["pin"] for event in session.events.of_type(kind)]


# --- TC-PM-01-1: a corpus of maps -----------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "table", "requires", "names"),
    [
        (
            "unknown_board",
            '[targets.nowhere.pins]\nheater = "gate_relay"\n',
            HEATER,
            ["nowhere"],
        ),
        (
            "missing_board_pin",
            '[targets.sim-default.pins]\nheater = "boiler"\n',
            HEATER,
            ["heater", "boiler", "sim-default"],
        ),
        (
            "wrong_primitive",
            '[targets.sim-rpi5.pins]\nheater = "limit_switch"\n',
            HEATER,
            ["heater", "limit_switch", "digital.out"],
        ),
        (
            "the_other_primitive_wrongly",
            '[targets.sim-rpi5.pins]\nswitch_in = "gate_relay"\n',
            HEATER + '\n"digital.in" = { pins = ["switch_in"] }',
            ["switch_in", "gate_relay", "digital.in"],
        ),
        (
            "a_pin_the_hal_owns",
            '[targets.sim-rpi5.pins]\nheater = "fan_en"\n',
            HEATER,
            ["heater", "fan_en"],
        ),
        (
            "two_names_on_one_pin",
            '[targets.sim-default.pins]\nheater = "gate_relay"\nair_pump = "gate_relay"\n',
            HEATER,
            ["heater", "air_pump", "gate_relay"],
        ),
        (
            "a_name_onto_a_pin_used_directly",
            '[targets.sim-default.pins]\nheater = "gate_relay"\n',
            '"digital.out" = { pins = ["heater", "gate_relay"] }',
            ["heater", "gate_relay"],
        ),
        (
            "a_name_the_agent_does_not_declare",
            '[targets.sim-default.pins]\nboiler = "gate_relay"\n',
            HEATER,
            ["boiler"],
        ),
        (
            "a_name_that_is_another_pin_of_the_board",
            '[targets.sim-default.pins]\ndoor_lock = "gate_relay"\n',
            '"digital.out" = { pins = ["door_lock"] }',
            ["door_lock", "gate_relay"],
        ),
    ],
)
def test_each_wrong_map_fails_at_load_naming_both_pins(tmp_path, name, table, requires, names):
    agent = make_agent(tmp_path, table, requires=requires, wire=False)
    for load in (
        lambda: build(agent, target="sim", board_id="sim-default"),
        lambda: resolve_board("sim-default", "sim", _manifest(agent)),
    ):
        with pytest.raises((AgentManifestError, BoardCapabilityError)) as failed:
            load()
        text = f"{failed.value.where} {failed.value.why} {failed.value.how}"
        assert all(part in text for part in names), (name, text)
        assert failed.value.how


def _manifest(agent: Path):
    from neuroedge.engine.compiler import load_agent_manifest

    return load_agent_manifest(agent)


def test_a_valid_map_is_accepted_and_applies_only_to_its_own_board(tmp_path):
    agent = make_agent(
        tmp_path,
        wire=False,
        extra='[targets.esp32s3-box-3.pins]\nheater = "gate_relay"\nair_pump = "door_lock"\n',
    )
    manifest = _manifest(agent)
    box, _ = resolve_board("esp32s3-box-3", "esp32s3", manifest)
    assert box.pin_map == {"heater": "gate_relay", "air_pump": "door_lock"}
    assert sorted(box.pins) == ["air_pump", "heater", "porch_light"]
    # Another board is the board as it is: the map names the box only.
    other, _ = resolve_board("sim-default", "sim", manifest)
    assert other.pin_map == {} and other.pins == load_board_by_id("sim-default").pins
    # `supported` is still the target list, and the unmapped agent still fails its own check.
    assert manifest.targets == ("sim", "linux", "esp32s3")


# --- TC-PM-02-1: the board pin's envelope governs -------------------------------------------


def test_the_mapped_pin_has_the_board_pins_envelope_and_a_token_drives_only_it(tmp_path):
    agent = make_agent(tmp_path)
    clock = HandClock()
    session = SimSession.load(agent, clock=clock)
    board = load_board_by_id("sim-default")
    assert session.hal.board.envelope("heater") == board.envelope("gate_relay")
    assert session.hal.board.envelope("air_pump") == board.envelope("door_lock")
    assert say(session, "bật sưởi").allowed
    assert pins_of(session) == ["heater"]  # the air pump and the real names did not move
    assert [op for op, _ in session.hal.pin("heater").commands] == ["on"]
    assert session.hal.pin("air_pump").commands == []
    # Held on, it goes off at the relay's 60 s: neither a part's 30 s nor the virtual board's.
    limit = board.envelope("gate_relay")["max_continuous_ms"]
    assert limit == 60_000
    clock.advance(limit - 1)
    session.hal.run_due()
    assert session.hal.pin("heater").commands[-1][0] == "on"
    clock.advance(1)
    session.hal.run_due()
    cut = session.events.of_type("actuator_command")[-1]
    assert (cut["pin"], cut["operation"], cut["cause"]) == ("heater", "off", "max_continuous_ms")
    session.hal.close()


# --- TC-PM-03-1: the agent's names everywhere, on every target -------------------------------


def test_the_same_agent_says_the_same_pin_names_on_the_box_and_on_the_chip(tmp_path):
    agent = make_agent(tmp_path / "agent")
    bridge = built(tmp_path / "chip", agent.parent)  # esp32s3-box-3, host-compiled
    generated = (tmp_path / "chip" / "out").rglob("ne_agent.c")
    table = next(generated).read_text(encoding="utf-8")
    assert '"heater"' in table and '"air_pump"' in table
    assert "gate_relay" not in table and "door_lock" not in table

    steps = ["fact owner_ok true", "call pm_heater_on {}", "call pm_pump_on {}"]
    chip = bridge.results(*steps)
    out = bridge.run("trace on", *steps)
    drives = [line.split("\t")[1] for line in out if line.startswith("drive\t")]
    assert drives == ["heater", "air_pump"]
    ne1 = "\n".join(line for line in out if line.startswith("NE1 "))
    assert '"heater"' in ne1 and "gate_relay" not in ne1 and "door_lock" not in ne1

    session = SimSession.load(agent)
    box = [
        asyncio.run(session.call_tool(ToolCall(tool, {}, source="mcp"))).content()
        for tool in ("pm_heater_on", "pm_pump_on")
    ]
    same_contract(box, chip)
    assert pins_of(session) == drives  # the same names, in the same order
    session.hal.close()


async def test_the_recording_carries_the_map_validates_and_replays(tmp_path):
    agent = make_agent(tmp_path)
    clock = HandClock()
    recorder = TraceRecorder(clock=clock)
    session = SimSession.load(agent, clock=clock, events=recorder)
    await asyncio.to_thread(say, session, "bật sưởi")
    clock.advance(1_500)
    await asyncio.to_thread(say, session, "bật sục khí")
    trace = recorder.to_trace()
    assert trace["metadata"]["pin_map"] == {"heater": "gate_relay", "air_pump": "door_lock"}
    validate_trace(trace)  # trace.v1 allows the extra key
    pins = {e["data"]["pin"] for e in trace["events"] if e["type"] == "actuator_command"}
    assert pins == {"heater", "air_pump"}
    result = await TracePlayer(trace, agent=agent).replay()
    assert result.verdicts == result.recorded_verdicts
    # A trace of this board with another wiring is not this agent's recording.
    trace["metadata"]["pin_map"] = {"heater": "porch_light", "air_pump": "door_lock"}
    from neuroedge.errors import NeuroEdgeError

    with pytest.raises(NeuroEdgeError, match="pin map"):
        await TracePlayer(trace, agent=agent).replay()
    session.hal.close()


# --- TC-PM-04-1: the map in force is printed; no map, no change -------------------------------


def test_build_and_run_print_the_map_in_force(tmp_path):
    agent = make_agent(tmp_path)
    line = "pins: heater → gate_relay, air_pump → door_lock"
    built_on_sim = runner.invoke(app, ["build", "--agent", str(agent), "--target", "sim"])
    assert built_on_sim.exit_code == 0, built_on_sim.output
    assert line in built_on_sim.output
    ran = runner.invoke(app, ["run", "--agent", str(agent), "-c", "bật sưởi"])
    assert ran.exit_code == 0, ran.output
    assert line in ran.output
    tools = runner.invoke(app, ["mcp", "tools", "--agent", str(agent)])
    assert tools.exit_code == 0, tools.output
    assert line in tools.output


@pytest.mark.parametrize("sample", ["aquarium", "chat-den-cua"])
def test_a_sample_without_a_map_builds_and_records_as_before(sample, tmp_path):
    manifest = ROOT / "fixtures" / "agents" / sample / "agent.toml"
    for target, board in (("sim", "sim-default"), ("esp32s3", "esp32s3-box-3")):
        report = build(manifest, target=target, board_id=board, out_dir=str(tmp_path / target))
        assert not [w for w in report.warnings if w.startswith("pins:")]
        profile, virtual = resolve_board(board, target, _manifest(manifest))
        assert virtual is None and profile == load_board_by_id(board) and profile.pin_map == {}
    session = SimSession.load(manifest)
    assert "pin_map" not in session.events.metadata
    session.hal.close()
    named = runner.invoke(app, ["build", "--agent", str(manifest), "--target", "sim"])
    assert "pins:" not in named.output


# --- TC-PM-05-1: sim boards take a map, the virtual board does not ----------------------------


def test_a_map_for_a_sim_board_is_applied_and_one_for_the_virtual_board_fails(tmp_path):
    agent = make_agent(tmp_path / "rpi", extra='[targets.sim-rpi5.pins]\nheater = "gate_relay"\n')
    for board in ("sim-default", "sim-rpi5"):
        profile, _ = resolve_board(board, "sim", _manifest(agent))
        assert profile.pin_map["heater"] == "gate_relay" and "heater" in profile.pins
        assert "gate_relay" not in profile.pins
        assert profile.envelope("heater") == load_board_by_id(board).envelope("gate_relay")
    virtual = make_agent(
        tmp_path / "virtual", extra='[targets.sim-virtual.pins]\nheater = "heater"\n'
    )
    with pytest.raises(AgentManifestError, match="virtual board"):
        build(virtual, target="sim", board_id="sim-virtual")
    with pytest.raises(AgentManifestError, match="sim-virtual"):
        build(virtual, target="sim", board_id="sim-default")
