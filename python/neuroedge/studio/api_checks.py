"""`/api/traces…`, `/api/record`, `/api/lint`, `/api/verify`, `/api/test` (docs/spec/studio.md §4). Slice S1b."""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from ..errors import NeuroEdgeError
from ..trace import load_trace, validate_trace

SUBPROCESS_TIMEOUT_S = 120
NAME = re.compile(r"[A-Za-z0-9_.@-]{1,128}")
# A trace in a subfolder of traces/ is named with `/` written as this character, one the
# route's name pattern accepts (`~` is not among its characters).
SEPARATOR = "@"
GOLDEN = "golden"  # traces/golden/ holds the golden references, not recordings


# -- traces ---------------------------------------------------------------------------


def _traces_root(server: Any) -> Path:
    return server.agent_root / "traces"


def _trace_files(server: Any) -> dict[str, Path]:
    """
    Every recording under `<agent>/traces/` (not `golden/`) by the name the API gives it:
    the path relative to `traces/`, without `.json`, `/` written as `@`. A file whose name
    the route cannot carry, that another file already took, or that leaves `traces/`
    through a link is not listed. The URL is only ever matched against this dict.
    """
    root = _traces_root(server)
    if not root.is_dir():
        return {}
    base = root.resolve()
    found: dict[str, Path] = {}
    for path in sorted(root.rglob("*.json")):
        relative = path.relative_to(root)
        if relative.parts[0] == GOLDEN or not path.is_file():
            continue
        if not path.resolve().is_relative_to(base):
            continue
        name = SEPARATOR.join(relative.with_suffix("").parts)
        if NAME.fullmatch(name) and name not in found:
            found[name] = path
    return found


def _listing(name: str, path: Path) -> dict[str, Any]:
    try:
        trace = load_trace(path)
    except NeuroEdgeError as error:
        return {
            "name": name,
            "valid": False,
            "error": error.why,
            "session_id": None,
            "events": None,
            "target": None,
            "board": None,
            "anonymized": None,
            "recorded_at": None,
        }
    metadata = trace["metadata"]
    return {
        "name": name,
        "valid": True,
        "session_id": metadata.get("session_id"),
        "events": len(trace["events"]),
        "target": metadata.get("target"),
        "board": metadata.get("board_id"),
        "anonymized": metadata.get("anonymized"),
        "recorded_at": metadata.get("timestamp_utc"),
    }


def _named(server: Any, name: str) -> Path:
    path = _trace_files(server).get(name)
    if path is None:
        raise NeuroEdgeError(
            where=f"traces/{name}",
            why="no such trace among the recordings of this agent",
            how="pick a name from GET /api/traces, or record the session first (POST /api/record)",
        )
    return path


def traces(server: Any) -> dict[str, Any]:
    listed = [_listing(name, path) for name, path in _trace_files(server).items()]
    return {"ok": True, "traces": listed}


def trace(server: Any, name: str) -> dict[str, Any]:
    return {"ok": True, **load_trace(_named(server, name))}


def replay(server: Any, name: str) -> dict[str, Any]:
    """`neuroedge replay <file>` on `sim`. The player builds its own HAL: the live session is untouched."""
    from ..testing.golden import GoldenComparator
    from ..testing.player import TracePlayer

    path = _named(server, name)
    player = TracePlayer(path, target="sim", agent=server.agent_path)
    result = asyncio.run(player.replay())
    diff = GoldenComparator().compare(result, player.trace)
    pins = [e["data"] for e in result.replayed["events"] if e["type"] == "actuator_command"]
    reply: dict[str, Any] = {
        "ok": True,
        "match": diff.ok,
        "verdicts": result.verdicts,
        "pins": pins,
    }
    detail = [str(difference) for difference in diff.differences] + list(result.warnings)
    if detail:
        reply["detail"] = "\n".join(detail)
    return reply


def record(server: Any) -> dict[str, Any]:
    """
    Write the live session to `<agent>/traces/<session_id>.json`, the user's words hashed.
    The studio's session logs plain events, so they are hashed here with the recorder's own
    function, as `neuroedge record` does at the source by default.
    """
    from ..testing.recorder import anonymise

    with server.lock:
        document = server.session.events.to_trace()
    document["events"] = [
        {**event, "data": anonymise(event["data"])} for event in document["events"]
    ]
    document["metadata"]["anonymized"] = True
    name = str(document["metadata"]["session_id"])
    if not NAME.fullmatch(name):
        raise NeuroEdgeError(
            where=f"session_id {name!r}",
            why="the session id cannot name a file the API can address",
            how="restart the studio for a new session",
        )
    path = _traces_root(server) / f"{name}.json"
    validate_trace(document, label=str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"ok": True, "name": name, "events": len(document["events"])}


# -- lint -----------------------------------------------------------------------------


def lint(server: Any) -> dict[str, Any]:
    """
    `neuroedge gate lint gates` in the agent's directory. An agent that keeps no `gates/` of
    its own uses the ones its `neuroedge://` references resolve against, as the CLI does.
    """
    from ..engine.gate_resolver import lint_registry, resolve_gate_file
    from ..paths import gates_dir

    own = server.agent_root / "gates"
    root = own if own.is_dir() else gates_dir()
    registry = lint_registry(root)
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.yaml")):
        try:
            gate = resolve_gate_file(path, registry=registry)
        except NeuroEdgeError as error:
            rows.append(
                {
                    "name": path.name,
                    "version": None,
                    "levels": None,
                    "fail": None,
                    "status": "FAIL",
                    "error": error.why,
                }
            )
            continue
        rows.append(
            {
                "name": gate.name,
                "version": gate.version,
                "levels": gate.inheritance_levels,
                "fail": gate.budget.get("fail", "closed"),
                "status": "OK",
            }
        )
    resolved = sum(row["status"] == "OK" for row in rows)
    return {"ok": True, "resolved": resolved, "total": len(rows), "gates": rows}


# -- verify and test (subprocesses) -----------------------------------------------------


# One subprocess at a time per process: a second click while `verify` or `test` runs is
# told so instead of starting another (and `build` must not race itself on build/).
_BUSY = threading.Lock()
# Values of these variables never leave the server, even inside a test's output.
_SECRET_NAME = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD)", re.IGNORECASE)


def one_at_a_time(what: str) -> Any:
    """Context manager: the busy lock, or a NeuroEdgeError when another run holds it."""
    import contextlib

    @contextlib.contextmanager
    def held():
        if not _BUSY.acquire(blocking=False):
            raise NeuroEdgeError(
                where=f"studio {what}",
                why="another lint/test/verify/build run is still going",
                how="wait for it to finish, then press the button again",
            )
        try:
            yield
        finally:
            _BUSY.release()

    return held()


def redact(text: str) -> str:
    """Replace the value of every secret-looking environment variable with ***."""
    for name, value in os.environ.items():
        if value and len(value) >= 8 and _SECRET_NAME.search(name):
            text = text.replace(value, "***")
    return text


def _run(server: Any, *args: str) -> tuple[int, str]:
    """`python -m neuroedge <args>` in the agent's directory: (exit code, stdout + stderr)."""
    import neuroedge

    code_root = str(Path(neuroedge.__file__).resolve().parent.parent)
    env = {
        **os.environ,
        "COLUMNS": "1000",  # rich wraps to the terminal: keep one line per sentence
        "NO_COLOR": "1",
        "PYTHONPATH": os.pathsep.join(filter(None, [code_root, os.environ.get("PYTHONPATH")])),
    }
    command = [sys.executable, "-m", "neuroedge", *args]
    try:
        done = subprocess.run(
            command,
            cwd=server.agent_root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=SUBPROCESS_TIMEOUT_S,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        raise NeuroEdgeError(
            where=f"neuroedge {' '.join(args)}",
            why=f"did not finish within {SUBPROCESS_TIMEOUT_S} s and was stopped",
            how=f"run it in a terminal in {server.agent_root} to see where it waits",
        ) from None
    return done.returncode, redact(done.stdout + done.stderr)


def _text_lines(output: str) -> list[str]:
    """The output's lines without the panel border rich draws around a paragraph."""
    return [line.strip(" │") for line in output.splitlines()]


def _matrix(output: str, passed: bool) -> list[dict[str, Any]]:
    """One row per gate, canonical trace and the tool-call corpus that `verify` checks."""
    from ..engine.gate_resolver import resolve_gate_file
    from ..paths import fixtures_dir, gates_dir

    items: list[str] = []
    for path in sorted(gates_dir().rglob("*.yaml")):
        try:
            gate = resolve_gate_file(path)
            items.append(f"{gate.name}@{gate.version}")
        except NeuroEdgeError:
            items.append(path.name)
    items += [path.name for path in sorted((fixtures_dir() / "traces").glob("*.json"))]
    items.append("tool-call corpus")
    failing = [line for line in _text_lines(output) if line.startswith("✗")]
    named = {item for item in items if any(item in line for line in failing)}
    # a failing line that names no gate and no trace is the tool-call corpus's
    corpus = any(not any(item in line for item in items) for line in failing)

    def status(item: str) -> str:
        if passed:
            return "pass"
        return "fail" if item in named or (item == "tool-call corpus" and corpus) else "pass"

    return [
        {
            "item": item,
            "sim": {"status": status(item), "source": "local"},
            "linux": {"source": "ci", "job": "linux-hal"},
            "esp32s3": {"source": "ci", "job": "uart-trace"},
        }
        for item in items
    ]


def verify(server: Any) -> dict[str, Any]:
    with one_at_a_time("verify"):
        code, output = _run(server, "verify", "--targets", "sim")
    lines = [line for line in _text_lines(output) if line]
    summary = next((line for line in lines if line.startswith(("Passed:", "Failed:"))), None)
    if summary is None:
        summary = next(
            (line for line in lines if "problem(s) found" in line),
            lines[-1] if lines else f"neuroedge verify exited {code} without output",
        )
    compared = next((line for line in lines if line.startswith("Compared:")), "")
    compared = re.sub(r"^Compared:\s*", "", compared)
    compared = re.split(r"\.\s|\.$", compared, maxsplit=1)[0]
    return {
        "ok": True,
        "passed": code == 0,
        "summary": summary,
        "compared": compared,
        "matrix": _matrix(output, code == 0),
    }


def _count(tail: str, word: str) -> int:
    return sum(int(n) for n in re.findall(rf"(\d+) {word}", tail))


def test(server: Any) -> dict[str, Any]:
    with one_at_a_time("test"):
        _, output = _run(server, "test")
    lines = [line for line in output.splitlines() if line.strip()]
    tail = lines[-20:]
    # pytest's own summary line, e.g. "3 passed, 1 failed in 0.4s", is the last one that counts
    summary = next(
        (line for line in reversed(lines) if re.search(r"\d+ (passed|failed|error)", line)), ""
    )
    return {
        "ok": True,
        "passed": _count(summary, "passed"),
        "failed": _count(summary, "failed") + _count(summary, "error"),
        "output_tail": "\n".join(tail),
    }
