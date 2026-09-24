"""
`neuroedge mcp desktop-config` — the entry Claude Desktop starts, started the way Desktop
starts it.

Desktop spawns an MCP server itself: working directory `/`, a minimal `PATH`, none of
the shell's virtualenv or `PYTHONPATH`. `test_mcp_serve_ui.py` launches the server with
the test's own environment, so it cannot see a config that only works from a shell. The
launch here uses nothing but the printed entry: `command`, `args` and `env`, on top of
the variables Desktop passes on (`get_default_environment()`, as the MCP SDK's stdio
client does), with `PATH=/usr/bin:/bin` and `cwd="/"`.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.mcp_desktop import default_config_path
from neuroedge.trace import validate_trace
from tests.test_mcp_serve_ui import poll

PYTHON_DIR = Path(__file__).resolve().parents[1]
MINIMAL_PATH = "/usr/bin:/bin"
TIMEOUT = 30.0
runner = CliRunner()


@pytest.fixture
def home(root):
    return root / "fixtures" / "agents" / "home-voice" / "agent.toml"


def desktop_config(*args: str):
    return runner.invoke(app, ["mcp", "desktop-config", *args])


def entry_for(home: Path, *extra: str) -> dict:
    result = desktop_config("--agent", str(home), *extra)
    assert result.exit_code == 0, result.output
    config = json.loads(result.stdout)
    assert list(config) == ["mcpServers"]
    return config["mcpServers"]["home-voice"]


# --- the printed entry ----------------------------------------------------------------------------


def test_the_entry_uses_only_absolute_paths(home, root, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # a relative --agent is resolved against where you ran it
    relative = os.path.relpath(home, tmp_path)
    entry = entry_for(Path(relative), "--ui", "--trace-out", "out/t.json")
    assert entry["command"] == os.path.abspath(sys.executable)
    assert entry["args"] == [
        "-m",
        "neuroedge",
        "mcp",
        "serve",
        "--agent",
        str(home.resolve()),
        "--ui",
        "--port",
        "8765",
        "--trace-out",
        str((tmp_path / "out" / "t.json").resolve()),
    ]
    # Pinned only when the interpreter alone would import some other neuroedge (a source
    # checkout on PYTHONPATH); a normal install needs no env at all.
    assert set(entry) <= {"command", "args", "env"}
    if "env" in entry:
        assert entry["env"] == {"PYTHONPATH": str(PYTHON_DIR)}


def test_name_defaults_to_the_agent_and_can_be_changed(home):
    result = desktop_config("--agent", str(home), "--name", "porch")
    assert result.exit_code == 0, result.output
    assert list(json.loads(result.stdout)["mcpServers"]) == ["porch"]


def test_an_agent_that_does_not_load_prints_no_entry(tmp_path):
    result = desktop_config("--agent", str(tmp_path / "nope.toml"))
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "agent.toml does not exist" in result.output


def test_without_the_mcp_sdk_it_says_what_to_install(home, monkeypatch):
    real = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util, "find_spec", lambda n, *a: None if n == "mcp" else real(n, *a)
    )
    result = desktop_config("--agent", str(home))
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "pip install 'neuroedge[mcp]'" in result.output


# --- started the way Claude Desktop starts it -----------------------------------------------------


def desktop_env(entry: dict) -> dict[str, str]:
    """What Desktop adds on top of the inherited variables: PATH, and the entry's env."""
    return {"PATH": MINIMAL_PATH, **entry.get("env", {})}


def test_desktop_starts_the_printed_entry_from_slash_with_a_minimal_path(home, tmp_path):
    trace_out = tmp_path / "desktop.json"
    entry = entry_for(home, "--ui", "--port", "0", "--trace-out", str(trace_out))
    params = StdioServerParameters(
        command=entry["command"], args=entry["args"], env=desktop_env(entry), cwd="/"
    )
    garbage: list[Exception] = []  # a non-JSON-RPC line on stdout arrives as an exception

    async def on_message(message):
        if isinstance(message, Exception):
            garbage.append(message)

    async def main():
        with (tmp_path / "stderr.txt").open("w", encoding="utf-8") as errlog:
            async with (
                stdio_client(params, errlog=errlog) as (read, write),
                ClientSession(read, write, message_handler=on_message) as client,
            ):
                with anyio.fail_after(TIMEOUT):
                    init = await client.initialize()
                    tools = [t.name for t in (await client.list_tools()).tools]
                    result = await client.call_tool("light_on", {})
        return init, tools, result

    init, tools, result = anyio.run(main)
    stderr = (tmp_path / "stderr.txt").read_text(encoding="utf-8")
    assert garbage == [], stderr
    assert init.server_info.name, stderr
    assert tools == ["light_on", "light_off"]
    assert (result.is_error, result.structured_content["status"]) == (False, "ALLOW")
    assert "neuroedge MCP server · home-voice@0.1.0" in stderr
    assert "sim UI at http://127.0.0.1:" in stderr
    assert "Warning" not in stderr  # Desktop's server log shows every stderr line
    # The trace path was absolute, so it landed here and not under `/`.
    trace = poll(lambda: trace_out.exists() and json.loads(trace_out.read_text("utf-8")))
    validate_trace(trace)
    (call,) = [e["data"] for e in trace["events"] if e["type"] == "tool_call"]
    assert (call["name"], call["source"]) == ("light_on", "mcp")


def test_the_old_readme_entry_bare_neuroedge_is_not_found_by_desktop(home):
    # It works in a shell because the venv's bin is on PATH there; Desktop's PATH is not.
    assert (Path(sys.executable).parent / "neuroedge").exists()
    assert shutil.which("neuroedge", path=MINIMAL_PATH) is None
    env = {"HOME": os.environ.get("HOME", "/"), "PATH": MINIMAL_PATH}
    with pytest.raises(FileNotFoundError):
        subprocess.run(
            ["neuroedge", "mcp", "serve", "--agent", str(home)],
            env=env,
            cwd="/",
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=60,
        )


# --- --write ---------------------------------------------------------------------------------------


def write(home: Path, config: Path, *extra: str):
    return desktop_config("--agent", str(home), "--write", "--config-path", str(config), *extra)


def backups(config: Path) -> list[Path]:
    return sorted(config.parent.glob(config.name + ".bak-*"))


def test_write_sets_one_entry_keeps_the_rest_and_backs_up(home, tmp_path):
    config = tmp_path / "claude_desktop_config.json"
    before = {
        "mcpServers": {"other": {"command": "/bin/other", "args": []}},
        "globalShortcut": "Ctrl+Space",
        "somethingNew": {"nested": [1, 2]},
    }
    config.write_text(json.dumps(before), encoding="utf-8")
    result = write(home, config)
    assert result.exit_code == 0, result.output
    after = json.loads(config.read_text(encoding="utf-8"))
    assert after["mcpServers"]["other"] == before["mcpServers"]["other"]
    assert {k: v for k, v in after.items() if k != "mcpServers"} == {
        "globalShortcut": "Ctrl+Space",
        "somethingNew": {"nested": [1, 2]},
    }
    entry = after["mcpServers"]["home-voice"]
    assert entry == entry_for(home)
    (backup,) = backups(config)
    assert json.loads(backup.read_text(encoding="utf-8")) == before
    assert str(config) in result.output and str(backup) in result.output
    assert "Quit Claude Desktop completely" in result.output
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def test_write_twice_changes_nothing_the_second_time(home, tmp_path):
    config = tmp_path / "claude_desktop_config.json"
    config.write_text('{"mcpServers": {}}', encoding="utf-8")
    assert write(home, config).exit_code == 0
    first = config.read_text(encoding="utf-8")
    again = write(home, config)
    assert again.exit_code == 0, again.output
    assert "already up to date" in again.output
    assert config.read_text(encoding="utf-8") == first
    assert len(backups(config)) == 1


def test_write_creates_a_missing_file_without_a_backup(home, tmp_path):
    config = tmp_path / "Claude" / "claude_desktop_config.json"
    result = write(home, config, "--name", "porch", "--ui")
    assert result.exit_code == 0, result.output
    written = json.loads(config.read_text(encoding="utf-8"))
    assert list(written) == ["mcpServers"] and list(written["mcpServers"]) == ["porch"]
    assert "--ui" in written["mcpServers"]["porch"]["args"]
    assert backups(config) == []


@pytest.mark.parametrize(
    "text",
    ['{"mcpServers": {', "[1, 2]", '{"mcpServers": ["not", "an", "object"]}'],
    ids=["broken-json", "not-an-object", "mcpServers-not-an-object"],
)
def test_write_refuses_a_file_it_cannot_merge_and_writes_nothing(home, tmp_path, text):
    config = tmp_path / "claude_desktop_config.json"
    config.write_text(text, encoding="utf-8")
    result = write(home, config)
    assert result.exit_code == 1
    assert "nothing was written" in result.output
    assert config.read_text(encoding="utf-8") == text
    assert sorted(p.name for p in tmp_path.iterdir()) == ["claude_desktop_config.json"]


def test_the_default_config_path_is_claude_desktops(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    expected = {
        "darwin": tmp_path / "Library" / "Application Support" / "Claude",
        "win32": tmp_path / "Roaming" / "Claude",
        "linux": tmp_path / ".config" / "Claude",
    }
    for platform, folder in expected.items():
        monkeypatch.setattr(sys, "platform", platform)
        assert default_config_path() == folder / "claude_desktop_config.json"
