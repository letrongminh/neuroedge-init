"""
The root README is the front door, so it must never lie.

Its quickstart commands are run exactly as written, and its two excerpts — a
gate and an @action — must match the files they quote (CONTRIBUTING.md §8.1
allows the README at most three quickstart commands on that condition).
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import yaml
from typer.testing import CliRunner

from neuroedge.cli.main import app

runner = CliRunner()


def _blocks(root: Path, language: str) -> list[str]:
    text = (root / "README.md").read_text(encoding="utf-8")
    return re.findall(rf"```{language}\n(.*?)```", text, re.S)


def _quickstart(root: Path) -> list[list[str]]:
    (block,) = _blocks(root, "bash")
    commands = []
    for line in block.splitlines():
        line = line.split("#", 1)[0].strip()
        if line.startswith("neuroedge "):
            commands.append(shlex.split(line)[1:])
    return commands


def test_the_quickstart_has_at_most_three_commands(root):
    (block,) = _blocks(root, "bash")
    assert len([line for line in block.splitlines() if line.strip()]) <= 3


def test_every_quickstart_command_runs_and_succeeds(root, tmp_path, monkeypatch):
    commands = _quickstart(root)
    assert commands, "the README quickstart lost its neuroedge commands"
    monkeypatch.chdir(root)
    for argv in commands:
        if argv[0] == "build":
            argv = [*argv, "--out", str(tmp_path)]
        result = runner.invoke(app, argv)
        assert result.exit_code == 0, f"neuroedge {' '.join(argv)}\n{result.output}"


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


def test_the_action_excerpt_matches_the_action_file(root):
    (block,) = _blocks(root, "python")
    source = (
        root / "fixtures" / "agents" / "villa-concierge" / "actions" / "unlock_door.py"
    ).read_text(encoding="utf-8")
    code = [line.split("#", 1)[0].rstrip() for line in source.splitlines()]
    for line in block.splitlines():
        stripped = line.split("#", 1)[0].rstrip()
        if stripped:
            assert stripped in code, f"README quotes a line the file does not have: {line!r}"


def test_every_relative_link_in_the_readme_resolves(root):
    text = (root / "README.md").read_text(encoding="utf-8")
    targets = [t for t in re.findall(r"\]\(([^)#]+)", text) if "://" not in t]
    assert targets
    missing = [t for t in targets if not (root / t).exists()]
    assert missing == []
