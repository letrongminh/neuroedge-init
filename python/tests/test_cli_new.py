"""
`neuroedge new` (TSK-S3-07): the scaffold must produce a project that builds,
runs on `sim` and whose own tests pass — the first minutes of the TTFV journey.

The generated project's `neuroedge test` runs in a subprocess: its @action is registered
process-wide, and a fresh interpreter is what a user gets anyway.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

import neuroedge
from neuroedge.cli.main import app
from neuroedge.errors import AgentManifestError
from neuroedge.templates import TEMPLATES, scaffold

runner = CliRunner()

MINIMAL = [
    "README.md",
    "actions/operate_hardware.py",
    "agent.toml",
    "commands.toml",
    "gates/custom_lock@1.0.0.yaml",
    "tests/test_agent.py",
]


def _env() -> dict[str, str]:
    """Import this checkout's neuroedge in the subprocess, not an installed copy."""
    package_root = str(Path(neuroedge.__file__).resolve().parents[1])
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = package_root
    return env


def _pytest(project: Path) -> subprocess.CompletedProcess:
    """`neuroedge test` in the project, as FR-DX-01 states it: no edits, exit 0."""
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from neuroedge.cli.main import app; app()",
            "test",
            "--pytest-arg=-p",
            "--pytest-arg=no:cacheprovider",
        ],
        cwd=project,
        env=_env(),
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> Path:
    parent = tmp_path_factory.mktemp("new")
    cwd = Path.cwd()
    os.chdir(parent)
    try:
        result = runner.invoke(app, ["new", "test-agent"])
    finally:
        os.chdir(cwd)
    assert result.exit_code == 0, result.output
    return parent / "test-agent"


def test_new_writes_every_file_of_the_minimal_template(project):
    written = sorted(str(p.relative_to(project)) for p in project.rglob("*") if p.is_file())
    assert written == MINIMAL
    assert not list(project.rglob("*.tmpl"))


def test_the_project_name_is_the_agent_name(project):
    manifest = tomllib.loads((project / "agent.toml").read_text("utf-8"))
    assert manifest["agent"]["name"] == "test-agent"
    assert "{{name}}" not in (project / "README.md").read_text("utf-8")


def test_the_generated_project_builds_for_sim(project, tmp_path):
    result = runner.invoke(
        app,
        [
            "build",
            "--target",
            "sim",
            "--board",
            "sim-default",
            "--agent",
            str(project / "agent.toml"),
            "--out",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "1 action(s), 1 gate(s)" in result.output


def test_the_generated_gate_explains_and_lints(project):
    result = runner.invoke(
        app, ["gate", "explain", str(project / "gates" / "custom_lock@1.0.0.yaml")]
    )
    assert result.exit_code == 0, result.output
    assert "user_verified" in result.output
    result = runner.invoke(app, ["gate", "lint", str(project / "gates")])
    assert result.exit_code == 0, result.output


def test_the_generated_project_runs_on_sim(project):
    result = runner.invoke(app, ["run", "--agent", str(project / "agent.toml"), "-c", "mở khoá"])
    assert result.exit_code == 0, result.output
    assert "ALLOW" in result.output
    assert "PULSED 5s" in result.output


def test_the_generated_tests_pass(project):
    result = _pytest(project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "4 passed" in result.stdout


def test_the_villa_template_copies_the_sample_and_its_tests_pass(tmp_path):
    files = scaffold("my-villa", "villa-concierge", tmp_path)
    project = tmp_path / "my-villa"
    assert Path("actions/unlock_door.py") in files
    assert Path("tests/test_agent.py") in files
    manifest = tomllib.loads((project / "agent.toml").read_text("utf-8"))
    assert manifest["agent"]["name"] == "my-villa"
    result = _pytest(project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "4 passed" in result.stdout


def test_the_home_voice_template_copies_the_sample_and_its_tests_pass(tmp_path):
    files = scaffold("nha", "home-voice", tmp_path)
    project = tmp_path / "nha"
    for expected in (
        "actions/lights.py",
        "knowledge.toml",
        "gates/light_off@1.0.0.yaml",
        "tests/test_agent.py",
    ):
        assert Path(expected) in files
    manifest = tomllib.loads((project / "agent.toml").read_text("utf-8"))
    assert manifest["agent"]["name"] == "nha"
    result = _pytest(project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "4 passed" in result.stdout


def test_the_factory_monitor_template_copies_the_sample_and_its_tests_pass(tmp_path):
    files = scaffold("xuong", "factory-monitor", tmp_path)
    project = tmp_path / "xuong"
    for expected in (
        "actions/plant.py",
        "gates/vent_off@1.0.0.yaml",
        "gates/alarm_off@1.0.0.yaml",
        "tests/test_agent.py",
    ):
        assert Path(expected) in files
    manifest = tomllib.loads((project / "agent.toml").read_text("utf-8"))
    assert manifest["agent"]["name"] == "xuong"
    result = _pytest(project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "4 passed" in result.stdout


# --- refusals ------------------------------------------------------------------------


def test_an_existing_directory_is_never_overwritten(tmp_path):
    (tmp_path / "taken").mkdir()
    (tmp_path / "taken" / "keep.txt").write_text("mine", encoding="utf-8")
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["new", "taken"])
    finally:
        os.chdir(cwd)
    assert result.exit_code == 1
    assert "not empty" in result.output
    assert sorted(p.name for p in (tmp_path / "taken").iterdir()) == ["keep.txt"]


@pytest.mark.parametrize("name", ["Bad Name", "1agent", "../escape", ""])
def test_an_invalid_name_is_refused(name, tmp_path):
    with pytest.raises(AgentManifestError, match="project name"):
        scaffold(name, "minimal", tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_an_unknown_template_is_refused(tmp_path):
    result = runner.invoke(app, ["new", "x", "--template", "nope"])
    assert result.exit_code == 1
    assert "minimal" in result.output
    assert set(TEMPLATES) == {"minimal", "villa-concierge", "home-voice", "factory-monitor"}
