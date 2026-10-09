"""
TSK-I2c-16 — the declaration of remote actuators and its one check (RFC-0018 §3b, §3f, §3k):
the corpus `fixtures/actuators/`, rule D5 at build and at load, and the build's boundaries
(`esp32s3`, the warning about network clients in action modules).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import yaml

from neuroedge.engine.compiler import AgentManifest, build, check_capabilities
from neuroedge.errors import AgentManifestError, BoardCapabilityError, BuildFailed
from neuroedge.guard import ActuatorDeclaration, Guard, Tool, check_actuators
from neuroedge.hal.board import load_board_by_id
from neuroedge.paths import repo_root
from neuroedge.plugins.actuators import parse_actuators, remote_setup

from .remote_support import actuator_toml, write_agent

pytestmark = pytest.mark.usefixtures("ref_plugins")

CORPUS = repo_root() / "fixtures" / "actuators"
EXPECTED = yaml.safe_load((CORPUS / "expected_errors.yaml").read_text(encoding="utf-8"))
ENVELOPE = {
    "window_s": 3600,
    "max_on_ms_per_window": 1_800_000,
    "min_interval_ms": 2000,
    "max_continuous_ms": 600_000,
}


def _check(path: Path, entry: dict):
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    board = load_board_by_id(entry.get("board", "sim-default"))
    setup = remote_setup(
        document,
        where=path.name,
        target=entry.get("target", "sim"),
        board=board,
        requires=document["requires"],
    )
    manifest = AgentManifest("corpus", "0.0.0", document["requires"], {}, (), path)
    return setup, setup.problems + check_capabilities(manifest, board, setup.names)


def test_the_corpus_is_closed_both_ways():
    for kind in ("valid", "invalid"):
        files = {p.name for p in (CORPUS / kind).glob("*.toml")}
        assert files == set(EXPECTED[kind]), kind
    assert set(EXPECTED) == {"valid", "invalid"}


@pytest.mark.parametrize("name", sorted(EXPECTED["valid"]))
def test_a_valid_declaration_passes_the_check(name):
    entry = EXPECTED["valid"][name]
    setup, problems = _check(CORPUS / "valid" / name, entry)
    assert problems == []
    assert len(setup.checked.warnings) == entry["warnings"]
    assert set(setup.checked.bound) == set(setup.declarations)


@pytest.mark.parametrize("name", sorted(EXPECTED["invalid"]))
def test_an_invalid_declaration_is_refused_with_exactly_its_errors(name):
    entry = EXPECTED["invalid"][name]
    _, problems = _check(CORPUS / "invalid" / name, entry)
    expected = entry["errors"]
    assert len(problems) == len(expected), [p.render() for p in problems]
    for problem, wanted in zip(problems, expected, strict=True):
        assert type(problem).__name__ == wanted["error"]
        assert problem.code == wanted["code"]
        assert wanted["where_contains"] in problem.where
        assert wanted["why_contains"] in problem.why
        assert problem.where and problem.why and problem.how, "three parts (FR-DX-04)"
        assert '"x"' not in problem.render() and "token = " not in problem.render()


def test_the_corpus_covers_every_rule_of_rfc_0018():
    codes = {e["code"] for entry in EXPECTED["invalid"].values() for e in entry["errors"]}
    assert codes == {"NE3001", "NE3002"}
    whys = " ".join(e["why_contains"] for v in EXPECTED["invalid"].values() for e in v["errors"])
    for rule in (
        "it is missing",  # safe_off absent
        "is not a level",
        "is a required property",  # an envelope key
        "already a digital.out pin",
        "not listed in [requires]",
        "does not provide digital.out:garden_valve",  # the other direction of the two-way rule
        "not fields of",
        "a secret must never be written",
        "is above what plugin",
        "with readback 'none'",
        "tolerance_ms",
        "no plugin loader",
        "is a remote actuator",
        'declares safe_off = "L1"',
    ):
        assert rule in whys, rule


# --- D5 (§3f) -------------------------------------------------------------------------------------


def test_an_irreversible_actuator_below_l2_is_refused_at_build(tmp_path, fresh_actions):
    agent = write_agent(tmp_path / "a", actuator_toml("ref_l1", "L1"))
    with pytest.raises(BuildFailed) as failed:
        build(agent, target="sim")
    problems = failed.value.problems
    d5 = [p for p in problems if p.code == "NE3002"]
    assert len(d5) == 1 and d5[0].where.endswith("[actuators.garden_valve] safe_off")
    assert "irreversible (reversible is not true)" in d5[0].why and "L2 or L3" in d5[0].how
    assert [p.code for p in problems if p is not d5[0]] == ["NE3001"]  # and the plugin's level
    # the same agent, declared reversible, builds — and so does an L2 one that stays irreversible
    build(write_agent(tmp_path / "b", actuator_toml("ref_l1", "L1", True)), target="sim")


def test_the_same_declaration_is_refused_at_load_without_agent_toml(tmp_path):
    (tmp_path / "lamp.yaml").write_text(
        (repo_root() / "gates" / "home" / "light@1.0.0.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    tool = Tool("water", str(tmp_path / "lamp.yaml"), ("digital.out:garden_valve",))
    irreversible = ActuatorDeclaration("garden_valve", "ref_l1", "L1", ENVELOPE)
    with pytest.raises(BuildFailed) as failed:
        Guard(
            [tool],
            board="sim-default",
            actuators=[irreversible],
            plugins=["neuroedge-ref-actuators"],
        )
    codes = sorted(p.code for p in failed.value.problems)
    assert codes == ["NE3001", "NE3002"]
    assert any("irreversible" in p.why for p in failed.value.problems)
    # the function a Guard calls is the one `neuroedge build` calls: public, same verdict
    from neuroedge.plugins import load_enabled, parse_plugins

    checked = check_actuators(
        {"garden_valve": irreversible},
        plugins=load_enabled(parse_plugins({"enable": ["neuroedge-ref-actuators"]}, "x")),
        target="sim",
        board=load_board_by_id("sim-default"),
        digital_out={"pins": ["garden_valve"]},
        where="code",
    )
    assert sorted(p.code for p in checked.problems) == ["NE3001", "NE3002"]
    reversible = ActuatorDeclaration("garden_valve", "ref_l1", "L1", ENVELOPE, reversible=True)
    guard = Guard(
        [tool], board="sim-default", actuators=[reversible], plugins=["neuroedge-ref-actuators"]
    )
    assert guard.hal.remote_names == ("garden_valve",)
    guard.close()


def test_reversible_is_false_when_not_declared():
    table = {
        "valve": {"plugin": "ref_l2", "safe_off": "L2", "envelope": ENVELOPE},
    }
    declarations, problems = parse_actuators(table, "agent.toml")
    assert problems == [] and declarations["valve"].reversible is False
    assert ActuatorDeclaration("v", "ref_l2", "L2", ENVELOPE).reversible is False
    with pytest.raises(AgentManifestError):  # neither a string nor a number stands for "true"
        from neuroedge.plugins.actuators import _declaration

        _declaration("valve", {**table["valve"], "reversible": 1}, "agent.toml")


def test_l0_builds_only_for_a_reversible_actuator_and_warns(tmp_path, fresh_actions):
    report = build(write_agent(tmp_path / "ok", actuator_toml("ref_l0", "L0", True)), target="sim")
    (warning,) = report.warnings
    assert 'safe_off = "L0"' in warning and "garden_valve" in warning
    with pytest.raises(BuildFailed) as failed:
        build(write_agent(tmp_path / "no", actuator_toml("ref_l0", "L0")), target="sim")
    assert {p.code for p in failed.value.problems} == {"NE3001", "NE3002"}


def test_an_irreversible_actuator_without_readback_is_refused(tmp_path, fresh_actions):
    toml = actuator_toml("ref_l2", "L2").replace(
        "[actuators.garden_valve.envelope]",
        '[actuators.garden_valve.config]\nreadback = "none"\n\n[actuators.garden_valve.envelope]',
    )
    with pytest.raises(BuildFailed) as failed:
        build(write_agent(tmp_path / "a", toml), target="sim")
    (problem,) = failed.value.problems
    assert isinstance(problem, BoardCapabilityError) and "with readback 'none'" in problem.why
    # reversible, the same plugin and config build: without P2 the level rests on P1 alone
    build(
        write_agent(
            tmp_path / "b", toml.replace('safe_off = "L2"', 'safe_off = "L2"\nreversible = true')
        ),
        target="sim",
    )


def test_the_home_assistant_plugin_cannot_declare_an_irreversible_actuator(tmp_path, fresh_actions):
    """
    The Home Assistant adapter (part B) declares L1 for every entity (§3j); an L1 plugin is what
    the rule is about, whoever wrote it: irreversible on it is refused (NE3002), and claiming L2
    for it is refused too (NE3001) — the build says no either way.
    """
    with pytest.raises(BuildFailed) as declared_l1:
        build(write_agent(tmp_path / "a", actuator_toml("ref_l1", "L1")), target="sim")
    assert "NE3002" in {p.code for p in declared_l1.value.problems}
    with pytest.raises(BuildFailed) as claimed_l2:
        build(write_agent(tmp_path / "b", actuator_toml("ref_l1", "L2")), target="sim")
    codes = [p.code for p in claimed_l2.value.problems]
    assert codes == ["NE3001", "NE3001"], "above the plugin's level, and below L2 for irreversible"


# --- boundaries ----------------------------------------------------------------------------------


def test_esp32s3_refuses_an_agent_with_remote_actuators(tmp_path, fresh_actions):
    agent = write_agent(tmp_path / "a", actuator_toml())
    build(agent, target="sim")  # the same agent is fine where there is a plugin loader
    with pytest.raises(BuildFailed) as failed:
        build(agent, target="esp32s3")
    remote = [p for p in failed.value.problems if "[actuators]" in p.where]
    assert len(remote) == 1 and remote[0].code == "NE3001"
    assert "no plugin loader" in remote[0].why


def test_build_warns_on_a_network_client_import_in_an_action_module(tmp_path, fresh_actions):
    quiet = build(write_agent(tmp_path / "quiet", actuator_toml()), target="sim")
    assert quiet.warnings == []
    for statement in (
        "import httpx",
        "import requests as r",
        "from aiohttp import ClientSession",
        "from urllib import request",
        "import urllib.request",
        "import socket",
    ):
        folder = tmp_path / statement.replace(" ", "_").replace(".", "_")
        guarded = f"try:\n    {statement}\nexcept ImportError:\n    pass\n"  # not installed here
        report = build(write_agent(folder, actuator_toml(), extra_imports=guarded), target="sim")
        (warning,) = report.warnings
        assert "valve.py" in warning and "RFC-0018" in warning, statement
    from typer.testing import CliRunner

    from neuroedge.cli.main import app

    guarded = "try:\n    import httpx\nexcept ImportError:\n    pass\n"
    agent = write_agent(tmp_path / "cli", actuator_toml(), extra_imports=guarded)
    result = CliRunner().invoke(
        app, ["build", "--target", "sim", "--agent", str(agent), "--out", str(tmp_path / "out")]
    )
    assert result.exit_code == 0, result.output
    assert "warning:" in result.output and "['httpx']" in result.output
