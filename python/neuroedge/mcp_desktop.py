"""
`neuroedge mcp desktop-config` — the `mcpServers` entry Claude Desktop needs, and a safe
way to write it.

Claude Desktop does not start a server from your shell. It spawns the process itself,
with the working directory at `/` and a minimal `PATH` (`/usr/bin:/bin` on macOS), and it
never sees a virtualenv you activated. So `"command": "neuroedge"` is not found, and a
relative `--agent` points nowhere. The entry built here uses only absolute paths: the
interpreter running this command, `-m neuroedge`, and the agent's resolved path.

One more case: from a source checkout imported through `PYTHONPATH`, the interpreter on
its own may import a *different* neuroedge (another checkout's editable install) or none.
`server_entry` asks the interpreter, the way Desktop will start it, which neuroedge it
imports, and pins `env.PYTHONPATH` to this code only when the answer differs.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from .errors import NeuroEdgeError

CONFIG_NAME = "claude_desktop_config.json"

# What Claude Desktop passes on to a server it spawns (the MCP SDK's stdio client keeps the
# same list). Nothing Python-specific: no PYTHONPATH, no VIRTUAL_ENV.
_INHERITED = (
    ("APPDATA", "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA", "PATH", "PROCESSOR_ARCHITECTURE")
    + ("SYSTEMDRIVE", "SYSTEMROOT", "TEMP", "USERNAME", "USERPROFILE")
    if sys.platform == "win32"
    else ("HOME", "LOGNAME", "PATH", "SHELL", "TERM", "USER")
)


def default_config_path() -> Path:
    """Where Claude Desktop reads its configuration on this OS."""
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Claude" / CONFIG_NAME
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        return (Path(appdata) if appdata else home / "AppData" / "Roaming") / "Claude" / CONFIG_NAME
    config_home = os.environ.get("XDG_CONFIG_HOME")
    return (Path(config_home) if config_home else home / ".config") / "Claude" / CONFIG_NAME


def _desktop_like_env() -> dict[str, str]:
    return {k: v for k in _INHERITED if (v := os.environ.get(k)) is not None}


def _pythonpath_pin(interpreter: str) -> str | None:
    """The `PYTHONPATH` Desktop's process needs to import this neuroedge, or None."""
    here = Path(__file__).resolve().parent
    probe = subprocess.run(
        [interpreter, "-c", "import neuroedge, sys; sys.stdout.write(neuroedge.__file__)"],
        cwd=Path(os.path.abspath(os.sep)),
        env=_desktop_like_env(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=60,
    )
    if probe.returncode == 0:
        imported = Path(probe.stdout.decode("utf-8", "replace").strip()).resolve().parent
        if imported == here:
            return None
    return str(here.parent)


def server_entry(
    agent: Path, *, ui: bool, port: int, trace_out: Path | None, interpreter: str | None = None
) -> dict[str, Any]:
    """One `mcpServers` value: absolute interpreter, module form, absolute paths."""
    # abspath, not resolve: a venv's python is a symlink, and resolving it leaves the venv.
    command = os.path.abspath(interpreter or sys.executable)
    args = ["-m", "neuroedge", "mcp", "serve", "--agent", str(agent.resolve())]
    if ui:
        args += ["--ui", "--port", str(port)]
    if trace_out is not None:
        args += ["--trace-out", str(trace_out.expanduser().resolve())]
    entry: dict[str, Any] = {"command": command, "args": args}
    pin = _pythonpath_pin(command)
    if pin is not None:
        entry["env"] = {"PYTHONPATH": pin}
    return entry


def _refuse(path: Path, why: str) -> NeuroEdgeError:
    return NeuroEdgeError(
        where=str(path),
        why=why,
        how="fix the file by hand (or move it aside), then run the command again; "
        "nothing was written",
    )


def write_entry(path: Path, name: str, entry: dict[str, Any]) -> tuple[bool, Path | None]:
    """
    Set `mcpServers[name]` in Desktop's config, keeping every other key as it is.

    Returns (changed, backup). A file that is not a JSON object is refused before anything
    is written. The old file is copied to `<file>.bak-<YYYYmmdd-HHMMSS>` first; the new
    one replaces it atomically. Writing the same entry again changes nothing.
    """
    config: dict[str, Any] = {}
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if text.strip():
            try:
                config = json.loads(text)
            except json.JSONDecodeError as exc:
                raise _refuse(path, f"not valid JSON ({exc})") from exc
            if not isinstance(config, dict):
                raise _refuse(path, f"the top level is a {type(config).__name__}, not an object")
    servers = config.get("mcpServers", {})
    if not isinstance(servers, dict):
        raise _refuse(path, f"`mcpServers` is a {type(servers).__name__}, not an object")
    if servers.get(name) == entry:
        return False, None
    updated = {**config, "mcpServers": {**servers, name: entry}}

    path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if path.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{path.name}.bak-{stamp}")
        n = 1
        while backup.exists():  # two writes in one second keep both originals
            backup = path.with_name(f"{path.name}.bak-{stamp}-{n}")
            n += 1
        shutil.copy2(path, backup)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(json.dumps(updated, indent=2, ensure_ascii=False) + "\n")
        if backup is not None:
            shutil.copymode(backup, tmp)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return True, backup
