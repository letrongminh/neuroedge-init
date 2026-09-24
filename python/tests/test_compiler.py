"""
TSK-S2-02 — build-time capability check (FR-HAL-04/05, FR-ACE-04/05, FR-DX-04).

The sample agent needs hardware AEC: it builds for sim-default and
esp32s3-box-3 and is refused on linux-rpi5 — the board drift (Tension 4) this
check exists to catch before anything reaches a device.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neuroedge.actions import Conversation
from neuroedge.cli.main import app
from neuroedge.engine import ActionContractEngine, EventLog, GateRegistry
from neuroedge.engine.compiler import (
    build,
    check_capabilities,
    load_actions,
    load_agent_manifest,
    resolve_gates,
)
from neuroedge.errors import AgentManifestError, BoardCapabilityError, BuildFailed
from neuroedge.hal import BoardProfile
from neuroedge.hal.sim import SimHAL
from neuroedge.trace import validate_trace

runner = CliRunner()


@pytest.fixture(scope="module")
def sample(root: Path) -> Path:
    return root / "fixtures" / "agents" / "villa-concierge" / "agent.toml"


def _agent(tmp_path: Path, body: str, *, actions: dict[str, str] | None = None) -> Path:
    path = tmp_path / "agent.toml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    for name, source in (actions or {}).items():
        folder = tmp_path / "actions"
        folder.mkdir(exist_ok=True)
        (folder / f"{name}.py").write_text(textwrap.dedent(source), encoding="utf-8")
    return path


MINIMAL = """
[agent]
name = "tmp-agent"
version = "0.0.1"

[requires]
{requires}

[gates]
{gates}

[targets]
supported = ["sim", "linux", "esp32s3"]
"""


def _minimal(tmp_path, requires='"digital.out" = { pins = ["door_lock"] }', gates="", **kw):
    return _agent(tmp_path, MINIMAL.format(requires=requires, gates=gates), **kw)


def _problems(excinfo) -> list:
    return excinfo.value.problems


# --- The sample agent across the three boards -------------------------------------


@pytest.mark.parametrize(
    ("target", "board"), [("sim", "sim-default"), ("esp32s3", "esp32s3-box-3")]
)
def test_the_sample_agent_builds_where_the_board_has_aec(sample, tmp_path, target, board):
    report = build(sample, target=target, board_id=board, out_dir=tmp_path)
    assert (report.actions, report.gates, report.requirements) == (1, 1, 4)
    assert (tmp_path / "gates" / "unlock_door.tree.json").is_file()


def test_the_sample_agent_is_refused_on_a_board_without_aec(sample):
    with pytest.raises(BuildFailed) as excinfo:
        build(sample, target="linux", board_id="linux-rpi5")
    (problem,) = _problems(excinfo)
    assert isinstance(problem, BoardCapabilityError)
    assert "aec" in problem.where
    assert "linux-rpi5" in problem.why
    assert problem.how


def test_build_artifacts_are_byte_identical_across_builds(sample, tmp_path):
    build(sample, target="sim", board_id="sim-default", out_dir=tmp_path / "a")
    build(sample, target="sim", board_id="sim-default", out_dir=tmp_path / "b")
    for name in sorted(p.name for p in (tmp_path / "a" / "gates").iterdir()):
        assert (tmp_path / "a" / "gates" / name).read_bytes() == (
            tmp_path / "b" / "gates" / name
        ).read_bytes()


# --- [requires] against the board (Appendix A.1) -----------------------------------------


@pytest.mark.parametrize(
    ("requires", "where"),
    [
        ('"digital.out" = { pins = ["garage_door"] }', "digital.out:garage_door"),
        ('"sensor.read" = { sensors = ["co2"] }', "sensor.read:co2"),
        ('"display" = { min_width = 1024 }', "display min_width = 1024"),
        ('"audio.in" = { sample_rate_hz = 96000 }', "audio.in sample_rate_hz = 96000"),
        ('"audio.in" = { min_channels = 4 }', "audio.in min_channels = 4"),
        ('"audio.out" = { channels = 8 }', "audio.out channels = 8"),
    ],
)
def test_each_unmet_requirement_is_a_three_part_error(tmp_path, requires, where):
    with pytest.raises(BuildFailed) as excinfo:
        build(_minimal(tmp_path, requires=requires), target="sim", board_id="sim-default")
    (problem,) = _problems(excinfo)
    assert where in problem.where
    assert "sim-default" in problem.why and "it provides" in problem.why
    assert "boards/sim-default.toml" in problem.how


def test_a_primitive_the_board_lacks_is_reported(tmp_path):
    manifest = load_agent_manifest(_minimal(tmp_path, requires='"display" = {}'))
    headless = BoardProfile(id="headless", target="sim", mcu="none", capabilities={})
    (problem,) = check_capabilities(manifest, headless)
    assert "display" in problem.where
    assert "provides nothing" in problem.why


# --- @action against the manifest --------------------------------------------------------

ACTION = """
from neuroedge import action
from neuroedge.hal import digital


@action(name="{name}", requires="{requires}", gate="{gate}")
def act() -> None:
    digital.out("door_lock").pulse(seconds=1)
"""


def test_an_action_needing_what_requires_omits_names_its_source_line(tmp_path):
    source = ACTION.format(name="cmp_porch", requires="digital.out:porch_light", gate="unlock_door")
    agent = _minimal(
        tmp_path,
        gates='unlock_door = "neuroedge://gates/unlock_door@1.2.0"',
        actions={"porch": source},
    )
    with pytest.raises(BuildFailed) as excinfo:
        build(agent, target="sim", board_id="sim-default")
    (problem,) = _problems(excinfo)
    assert isinstance(problem, AgentManifestError)
    assert "porch.py:" in problem.where and "digital.out:porch_light" in problem.where


def test_an_action_naming_an_undeclared_gate_is_refused(tmp_path):
    source = ACTION.format(name="cmp_nogate", requires="digital.out:door_lock", gate="open_safe")
    agent = _minimal(tmp_path, actions={"nogate": source})
    with pytest.raises(BuildFailed) as excinfo:
        build(agent, target="sim", board_id="sim-default")
    (problem,) = _problems(excinfo)
    assert "open_safe" in problem.where


# --- Gates -------------------------------------------------------------------------------


def test_an_unresolvable_gate_propagates_its_own_error(tmp_path):
    agent = _minimal(tmp_path, gates='missing = "neuroedge://gates/does-not-exist@9.9.9"')
    with pytest.raises(BuildFailed) as excinfo:
        build(agent, target="sim", board_id="sim-default")
    assert [p.code for p in _problems(excinfo)] == ["NE2001"]


def test_a_loosening_gate_is_refused_with_its_principle(tmp_path, gate_fixtures_dir):
    loose = gate_fixtures_dir / "invalid" / "loosens_level.yaml"
    agent = _minimal(tmp_path, gates=f'loose = "{loose}"')
    with pytest.raises(BuildFailed) as excinfo:
        build(
            agent,
            target="sim",
            board_id="sim-default",
            registry=GateRegistry(gate_fixtures_dir / "registry"),
        )
    (problem,) = _problems(excinfo)
    assert (problem.code, problem.principle) == ("NE2003", 2)


def test_a_degrade_fallback_must_be_a_declared_action(tmp_path, gate_fixtures_dir):
    agent = _minimal(tmp_path, gates='door = "neuroedge://gates/degrade-base@1.0.0"')
    with pytest.raises(BuildFailed) as excinfo:
        build(
            agent,
            target="sim",
            board_id="sim-default",
            registry=GateRegistry(gate_fixtures_dir / "registry"),
        )
    (problem,) = _problems(excinfo)
    assert "notify_front_desk" in problem.why


def test_a_broken_command_grammar_is_reported(tmp_path):
    agent = _minimal(tmp_path)
    (tmp_path / "commands.toml").write_text("[grammar]\nversion = 2\n", encoding="utf-8")
    with pytest.raises(BuildFailed) as excinfo:
        build(agent, target="sim", board_id="sim-default")
    assert [p.code for p in _problems(excinfo)] == ["NE5001"]


# --- Manifest and target -----------------------------------------------------------------


def test_every_problem_is_reported_in_one_run(tmp_path):
    requires = '"digital.out" = { pins = ["garage_door"] }\n"display" = { min_width = 1024 }'
    agent = _minimal(tmp_path, requires=requires, gates='x = "neuroedge://gates/nope@1.0.0"')
    with pytest.raises(BuildFailed) as excinfo:
        build(agent, target="linux", board_id="sim-default")
    codes = sorted(p.code for p in _problems(excinfo))
    assert codes == ["NE2001", "NE3001", "NE3001", "NE3001"]
    assert "4 problem(s)" in excinfo.value.why


def test_a_manifest_without_requires_is_refused(tmp_path):
    path = _agent(tmp_path, '[agent]\nname = "x"\nversion = "1.0.0"\n')
    with pytest.raises(AgentManifestError) as excinfo:
        load_agent_manifest(path)
    assert "[requires]" in excinfo.value.where


def test_an_unsupported_target_is_refused(tmp_path):
    body = MINIMAL.format(requires="", gates="").replace(
        '["sim", "linux", "esp32s3"]', '["esp32s3"]'
    )
    with pytest.raises(BuildFailed) as excinfo:
        build(_agent(tmp_path, body), target="sim", board_id="sim-default")
    assert "[targets]" in _problems(excinfo)[0].where


# --- CLI ------------------------------------------------------------------------------------


def test_cli_build_succeeds_and_writes_the_trees(sample, tmp_path):
    result = runner.invoke(
        app,
        [
            "build",
            "--target",
            "sim",
            "--board",
            "sim-default",
            "--agent",
            str(sample),
            "--out",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "builds for sim on sim-default" in result.output
    assert (tmp_path / "gates" / "unlock_door.tree.json").is_file()


@pytest.mark.parametrize(("target", "board"), [("sim", "sim-default"), ("linux", "linux-rpi5")])
def test_cli_build_without_board_uses_the_targets_reference_board(sample, tmp_path, target, board):
    # `--target sim` alone once picked esp32s3-box-3 and failed: the board follows the target.
    result = runner.invoke(
        app, ["build", "--target", target, "--agent", str(sample), "--out", str(tmp_path)]
    )
    assert f"on {board}" in result.output or f"'{board}'" in result.output, result.output
    assert "esp32s3-box-3" not in result.output


def test_cli_build_fails_with_exit_1_and_every_problem(sample, tmp_path):
    result = runner.invoke(
        app,
        [
            "build",
            "--target",
            "linux",
            "--board",
            "linux-rpi5",
            "--agent",
            str(sample),
            "--out",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1
    assert "aec" in result.output
    # Diagnostics quote TOML tables; rich must not swallow them as markup.
    assert "[requires]" in result.output
    assert not (tmp_path / "gates").exists(), "a failed build writes nothing"


# --- Sprint 2 exit criterion 1: the sample agent runs on sim ---------------------


@pytest.mark.parametrize(
    ("facts", "pulsed"),
    [
        ({"guest_authenticated": True, "room_matches": True, "risk_level": "low"}, True),
        ({"guest_authenticated": True, "room_matches": True, "risk_level": "high"}, False),
    ],
)
async def test_the_sample_agent_runs_on_sim_and_its_gate_decides(sample, facts, pulsed):
    manifest = load_agent_manifest(sample)
    (unlock_door,) = load_actions(manifest)
    gates, problems = resolve_gates(manifest)
    assert problems == []

    events = EventLog()
    engine = ActionContractEngine(gates, events=events)
    hal = SimHAL(events=events)
    c = Conversation(engine=engine, hal=hal, facts=facts)
    result = await c.do(unlock_door, guest_id="g1")

    assert result.blocked is not pulsed
    assert hal.pin("door_lock").pulsed_once(duration_ms=30_000) is pulsed
    validate_trace(events.to_trace())
