"""
Every `--help` ends with at least one runnable example (TSK-I1-03, FR-CLI-07).

The walk covers every command and command group Typer builds, so a new command
without an entry in `neuroedge/cli/examples.py` fails here. Each example is parsed
by the real parser — an example naming a flag or argument that no longer exists
fails too — and the rendered `--help` page must show it. Last, every example that
does not start a server, open a browser or need GPIO runs in a project that
`neuroedge new` just created, and must exit 0.
"""

from __future__ import annotations

import glob
import re
import shlex

import pytest
import typer
from typer.testing import CliRunner

from neuroedge.cli.examples import EXAMPLES
from neuroedge.cli.main import app

runner = CliRunner()
ROOT = typer.main.get_command(app)


def _is_group(command) -> bool:
    # Typer builds on its own copy of click, so duck-type rather than isinstance.
    return hasattr(command, "commands")


def _paths(group, path: tuple[str, ...] = ()):
    yield path, group
    for name, command in sorted(group.commands.items()):
        if _is_group(command):
            yield from _paths(command, (*path, name))
        else:
            yield (*path, name), command


COMMANDS = list(_paths(ROOT))
IDS = [" ".join(path) or "neuroedge" for path, _ in COMMANDS]


def _squash(text: str) -> str:
    # On GitHub Actions typer forces a terminal and rich still bolds options under
    # NO_COLOR (it drops colour, not style): the escape codes go first.
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    return re.sub(r"[\s│╭╮╰╯─]+", "", text)


def _parse(example: str) -> tuple[str, ...]:
    """Parse `example` with the real parser and return its command path; raise on misuse."""
    words = shlex.split(example, comments=True)
    assert words[0] == "neuroedge", example
    words = words[1:]
    command = ROOT
    path: tuple[str, ...] = ()
    ctx = command.make_context("neuroedge", [], resilient_parsing=True)
    while _is_group(command) and words and not words[0].startswith("-"):
        name = words.pop(0)
        sub = command.get_command(ctx, name)
        assert sub is not None, f"{example!r}: no command {name!r}"
        command, path = sub, (*path, name)
        if _is_group(command):
            ctx = command.make_context(name, [], parent=ctx, resilient_parsing=True)
    if _is_group(command):
        assert not words, f"{example!r}: a group takes a subcommand, not {words}"
        return path
    # Not resilient: an unknown option, a missing argument or a bad value raises.
    with command.make_context(command.name, words, parent=ctx):
        pass
    return path


def test_the_walk_finds_groups_and_nested_commands():
    assert {"neuroedge", "gate", "mcp", "gate lint", "mcp desktop-config", "record"} <= set(IDS)


def test_every_command_has_an_entry_and_every_entry_a_command():
    # Closed both ways: no command without examples, no examples for a removed command.
    assert sorted(EXAMPLES) == sorted(" ".join(path) for path, _ in COMMANDS)
    assert all(EXAMPLES[key] for key in EXAMPLES), "an entry needs at least one example"


@pytest.mark.parametrize("path,command", COMMANDS, ids=IDS)
def test_help_shows_the_examples(path, command):
    result = runner.invoke(app, [*path, "--help"], env={"COLUMNS": "200"})
    assert result.exit_code == 0, result.output
    assert "Examples:" in result.output
    page = _squash(result.output)
    for example in EXAMPLES[" ".join(path)]:
        assert _squash(example) in page, f"`{' '.join(path)} --help` does not show {example!r}"


@pytest.mark.parametrize("path,command", COMMANDS, ids=IDS)
def test_every_example_parses_under_its_own_command(path, command):
    # A group's examples run one of its subcommands; a command's run that command.
    for example in EXAMPLES[" ".join(path)]:
        parsed = _parse(example)
        if _is_group(command):
            assert parsed[: len(path)] == path and len(parsed) > len(path), example
        else:
            assert parsed == path, f"{example!r} is not an example of {' '.join(path)}"


@pytest.mark.parametrize(
    "example,error",
    [
        ("neuroedge record --no-such-flag", "NoSuchOption"),
        ("neuroedge board show", "MissingParameter"),  # the board id is required
        ("neuroedge run --port not-a-number", "BadParameter"),
    ],
)
def test_a_stale_example_is_caught(example, error):
    with pytest.raises(Exception) as caught:
        _parse(example)
    assert type(caught.value).__name__ == error
    assert caught.value.exit_code == 2  # a usage error, as on the command line


# Examples that are not run here, each with the reason. Everything else runs, in a
# project `neuroedge new my-agent` just created, and must exit 0.
NOT_RUN = {
    # TSK-I2c-14: they need a real MCP server to connect to (or a guard.toml made from one);
    # tests/test_proxy_mcp.py runs each against the fixture upstream of fixtures/mcp_upstream/
    'neuroedge guard init --mcp "python my_server.py"': "connects to a real MCP server",
    "neuroedge guard init --mcp https://ha.local/mcp --header-env Authorization=HA_TOKEN --dir ha": (
        "connects to a real MCP server over the network"
    ),
    "neuroedge proxy mcp": "an MCP stdio server; needs a guard.toml made by `guard init`",
    # TSK-I2c-15: a loopback server that runs until interrupted, and a guard.toml of a real API;
    # tests/test_proxy_http.py runs each against the fixture upstream
    "neuroedge proxy http": "serves until interrupted; needs a guard.toml made by `guard init --http`",
    "neuroedge proxy http --config plug/guard.toml --trace-out plug/session.json": (
        "serves until interrupted"
    ),
    'neuroedge guard init --http http://127.0.0.1:8080 --route "POST /cm/{cmd}"': (
        "writes guard.toml and gates/ into the current directory (test_guard_init_http_… runs it)"
    ),
    'neuroedge guard init --http http://127.0.0.1:8080 --route "POST /cm/{cmd}" --dir plug': (
        "writes into a new directory (test_guard_init_http_… runs it)"
    ),
    "neuroedge proxy mcp --config ha/guard.toml --trace-out ha/session.json": (
        "an MCP stdio server"
    ),
    "neuroedge proxy mcp --desktop-config --write": (
        "writes Claude Desktop's real config (test_the_proxy_registers_in_claude_desktop_like_mcp_serve "
        "covers --write on a copy)"
    ),
    "neuroedge plugin doctor": "needs a guard.toml made by `guard init`",
    "neuroedge conformance neuroedge-ref-actuators": (
        "needs the reference plugin installed; tests/test_conformance.py installs and runs it"
    ),
    "neuroedge conformance neuroedge-ha --kind actuator --json": (
        "needs a plugin installed; tests/test_conformance.py runs the command on the fixtures"
    ),
    "neuroedge plugin doctor --config ha/guard.toml --json": "needs a guard.toml made by `guard init`",
    "neuroedge run --ui": "serves a page until interrupted",
    "neuroedge studio                 # every capability in one local web app": (
        "serves a page until interrupted; tests/test_studio_server.py drives the server"
    ),
    "neuroedge studio --mic           # plus the laptop microphone (headphones)": (
        "a page and a microphone; tests/test_studio_voice.py covers it on a fake device"
    ),
    "neuroedge mcp serve --ui": "an MCP stdio server runs until its client leaves",
    "neuroedge mcp serve --agent agent.toml": "an MCP stdio server",
    "neuroedge mcp serve --ui --trace-out traces/mcp.json": "an MCP stdio server",
    "neuroedge mcp desktop-config --agent agent.toml --ui --write": (
        "writes Claude Desktop's real config (tests/test_mcp_desktop.py covers --write)"
    ),
    "neuroedge trace view traces/session.json --open": "opens a browser",
    "neuroedge verify --targets sim,linux": "linux needs GPIO lines (job linux-hal)",
    "neuroedge test": "pytest inside pytest; tests/test_cli_new.py runs it in a subprocess",
    "neuroedge test tests/ --pytest-arg=-x": "as above",
    "neuroedge run --mic              # live voice session through the laptop mic": (
        "needs [stt] and a microphone (TSK-I4-04)"
    ),
    "neuroedge run --voice-file turn.wav --voice-out reply.wav   # speech: needs stt/tts tables": (
        "needs [stt]/[tts] in agent.toml and a WAV file; tests/test_voice_cli.py runs it on the "
        "fake providers"
    ),
    "neuroedge record --voice-file turn.wav   # transcripts hashed in the trace": (
        "needs [stt]/[tts] in agent.toml and a WAV file; tests/test_voice_cli.py runs it on the "
        "fake providers"
    ),
    "neuroedge run --voice-file turn.wav --target linux   # real lines; the WAV is audio.in": (
        "needs [stt]/[tts] in agent.toml, a WAV file and GPIO lines; "
        "tests/test_hal_linux_audio.py runs it on the fake gpiod"
    ),
    "neuroedge record --voice-file turn.wav --target linux --out traces/voice.json": "as above",
}


def _runnable() -> list[str]:
    seen: list[str] = []
    for examples in EXAMPLES.values():
        for example in examples:
            if example not in seen and example not in NOT_RUN:
                seen.append(example)
    # A session is recorded before the examples that read it.
    return sorted(seen, key=lambda e: not e.startswith("neuroedge record"))


def test_every_not_run_example_is_still_an_example():
    listed = {example for examples in EXAMPLES.values() for example in examples}
    assert set(NOT_RUN) <= listed


@pytest.fixture
def fresh_actions():
    """
    The scaffold defines `operate_hardware` at a new path: free that one name. The
    rest stays — `verify` replays sample agents whose modules are already imported.
    """
    from neuroedge.actions import spec

    saved = dict(spec.REGISTRY)
    spec.REGISTRY.pop("operate_hardware", None)
    yield
    spec.REGISTRY.clear()
    spec.REGISTRY.update(saved)


def test_the_examples_run_in_a_new_project(tmp_path, monkeypatch, fresh_actions):
    (tmp_path / "work").mkdir()
    (tmp_path / "fresh").mkdir()  # where the `new` examples create their own project
    monkeypatch.chdir(tmp_path / "work")
    assert runner.invoke(app, ["new", "my-agent"]).exit_code == 0
    project = tmp_path / "work" / "my-agent"
    for example in _runnable():
        words = shlex.split(example, comments=True)[1:]
        monkeypatch.chdir(tmp_path / "fresh" if words[0] == "new" else project)
        if "--golden" in words:
            golden = project / "traces" / "golden" / "unlock.json"
            golden.write_bytes((project / "traces" / "session.json").read_bytes())
        words = [w for word in words for w in (sorted(glob.glob(word)) if "*" in word else [word])]
        result = runner.invoke(app, words, input="exit\n")
        assert result.exit_code == 0, f"{example!r} exited {result.exit_code}:\n{result.output}"
