"""
Every `--help` shows its text in full.

Typer renders help as Rich markup, so a bare `[mcp.servers]` in a help string is read
as a markup tag and silently dropped: `mcp tools --help` once said "Also connect to the
of agent.toml". This walks every command and requires each bracketed span of its help
source to appear in the rendered page (an escaped `\\[x]` must render as `[x]`).
"""

from __future__ import annotations

import re

import pytest
import typer
from typer.testing import CliRunner

from neuroedge.cli.main import app

runner = CliRunner()
BRACKETED = re.compile(r"\\?\[[^\]\s]+\]")


def _commands(group, path: tuple[str, ...] = ()):
    for name, command in sorted(group.commands.items()):
        yield (*path, name), command
        if hasattr(command, "commands"):  # a sub-app such as `mcp`
            yield from _commands(command, (*path, name))


def _sources(command) -> list[str]:
    texts = [command.help or ""]
    texts += [getattr(param, "help", None) or "" for param in command.params]
    return texts


def _squash(text: str) -> str:
    # Wrapping splits a span across table rows; compare without layout characters.
    return re.sub(r"[\s│╭╮╰╯─]+", "", text)


COMMANDS = list(_commands(typer.main.get_command(app)))


def test_the_walk_finds_the_nested_commands():
    paths = {" ".join(path) for path, _ in COMMANDS}
    assert {"mcp tools", "mcp serve", "gate lint", "trace view", "verify"} <= paths


@pytest.mark.parametrize("path,command", COMMANDS, ids=[" ".join(p) for p, _ in COMMANDS])
def test_help_keeps_every_bracketed_span(path, command):
    result = runner.invoke(app, [*path, "--help"], env={"COLUMNS": "100"})
    assert result.exit_code == 0, result.output
    page = _squash(result.output)
    for text in _sources(command):
        for span in BRACKETED.findall(text):
            assert _squash(span.lstrip("\\")) in page, f"`{' '.join(path)} --help` drops {span!r}"
