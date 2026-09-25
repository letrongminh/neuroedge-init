"""
The root README is the front door, and the PyPI page (TSK-S3-20), so it must never lie.

Its quickstart commands are run exactly as written, its gate excerpt must match the
file it quotes (CONTRIBUTING.md §8.1 allows the README at most three quickstart
commands on that condition), and every link is an absolute GitHub URL that resolves in
this tree: on PyPI a relative link points nowhere. Whether the page *renders* on PyPI
is `twine check --strict` in `.github/workflows/release-pypi.yml`.
"""

from __future__ import annotations

import json
import re
import shlex
import tomllib
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from neuroedge.cli.main import app

runner = CliRunner()
BLOB = "https://github.com/letrongminh/neuroedge-init/blob/main/"


def _text(root: Path) -> str:
    return (root / "README.md").read_text(encoding="utf-8")


def _blocks(root: Path, language: str) -> list[str]:
    return re.findall(rf"```{language}\n(.*?)```", _text(root), re.S)


def _quickstart_lines(root: Path) -> list[str]:
    (block,) = _blocks(root, "bash")
    return [line.split("#", 1)[0].strip() for line in block.splitlines() if line.strip()]


def test_the_quickstart_has_at_most_three_commands(root):
    assert len(_quickstart_lines(root)) <= 3


def test_the_quickstart_installs_the_bare_package(root):
    """PRD Hành trình 1: no key, no account — the extras are named, not required."""
    install = _quickstart_lines(root)[0]
    assert install == "pip install neuroedge"
    declared = tomllib.loads((root / "python" / "pyproject.toml").read_text("utf-8"))
    extras = declared["project"]["optional-dependencies"]
    # The comment on that line names the extras for a real LLM; both must exist.
    (block,) = _blocks(root, "bash")
    for group in re.findall(r"neuroedge\[([a-z,]+)\]", block):
        assert set(group.split(",")) <= set(extras), group


@pytest.fixture
def fresh_actions():
    """The scaffold defines home-voice's @action names at a new path: isolate the registry."""
    from neuroedge.actions import spec

    saved = dict(spec.REGISTRY)
    spec.REGISTRY.clear()
    yield
    spec.REGISTRY.clear()
    spec.REGISTRY.update(saved)


def test_every_quickstart_command_runs_and_succeeds(root, tmp_path, monkeypatch, fresh_actions):
    monkeypatch.chdir(tmp_path)  # a stranger's empty directory, not the checkout
    lines = _quickstart_lines(root)
    commands = [shlex.split(line)[1:] for line in lines if line.startswith("neuroedge ")]
    assert commands, "the README quickstart lost its neuroedge commands"
    for argv in commands:
        result = runner.invoke(app, argv)
        assert result.exit_code == 0, f"neuroedge {' '.join(argv)}\n{result.output}"
    assert "ALLOW" in result.output, "the last quickstart command should show the gate allow"


def test_the_claude_desktop_path_runs(root, tmp_path, monkeypatch, fresh_actions):
    """The README's second path: the exact `desktop-config` command it quotes."""
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["new", "my-home", "--template", "home-voice"]).exit_code == 0
    (quoted,) = re.findall(r"`(neuroedge mcp desktop-config [^`]+)`", _text(root))
    argv = shlex.split(quoted)[1:]
    assert "--write" in argv
    config = tmp_path / "claude_desktop_config.json"  # never the real Desktop config
    result = runner.invoke(app, [*argv, "--config-path", str(config)])
    assert result.exit_code == 0, result.output
    (entry,) = json.loads(config.read_text("utf-8"))["mcpServers"].values()
    assert str((tmp_path / "my-home" / "agent.toml").resolve()) in entry["args"]
    assert entry["args"][-3:] == ["--ui", "--port", "8765"]


def test_the_command_for_people_without_desktop_exists(root):
    assert "`cd my-home && neuroedge run --ui`" in _text(root)
    # Click rejects an unknown option before it reaches --help, so exit 0 proves --ui.
    result = runner.invoke(app, ["run", "--ui", "--help"])
    assert result.exit_code == 0, result.output


def _subset(excerpt, actual) -> bool:
    if isinstance(excerpt, dict):
        return isinstance(actual, dict) and all(
            key in actual and _subset(value, actual[key]) for key, value in excerpt.items()
        )
    return excerpt == actual


def test_the_gate_excerpt_matches_the_gate_file(root):
    (block,) = _blocks(root, "yaml")
    excerpt = yaml.safe_load(block)
    actual = yaml.safe_load((root / "gates" / "unlock_door@1.2.0.yaml").read_text("utf-8"))
    assert _subset(excerpt, actual)


def test_the_readme_has_no_relative_link(root):
    targets = re.findall(r"\]\(([^)]+)\)", _text(root))
    assert targets
    relative = [t for t in targets if not t.startswith("https://")]
    assert relative == [], "PyPI shows the README outside the repo: use absolute URLs"


def test_every_github_link_in_the_readme_resolves_in_this_tree(root):
    targets = re.findall(r"\]\((https://github\.com/[^)#]+)", _text(root))
    blobs = [t for t in targets if t.startswith(BLOB)]
    assert blobs == targets, "links go to this repository's main branch"
    missing = [t for t in blobs if not (root / t.removeprefix(BLOB)).exists()]
    assert missing == []
