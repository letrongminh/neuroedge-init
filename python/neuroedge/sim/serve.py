"""
`neuroedge mcp serve`, as code: serve one agent as a gated MCP server over stdio.

`serve_mcp` is the public entry point (`neuroedge.serve_mcp`); `neuroedge mcp serve`
runs the same `run_stdio`, so the gate, the shutdown and the trace default are one
path whoever starts the server. `SimSession.load` is the one place the agent is
wired (docs/architecture/vi/03-component-host-c4l3.md §2), and `mcp_server` the one
place a tool call becomes a `ToolCall` (docs/spec/tool_calling.md).
"""

from __future__ import annotations

import os
import signal
import sys
import threading
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..engine import GateRegistry
from ..mcp_server import ThreadLock, _sdk, serve_stdio
from .session import SimSession

# `mcp serve` exits when no client initializes within this window (a leaked, orphaned
# spawn). Clients send `initialize` at once, so 30 s only has to beat a slow start.
MCP_INIT_TIMEOUT_S = 30.0


def exit_on_signals() -> Callable[[], None]:
    """
    SIGTERM and SIGHUP end the process through `SystemExit`, so the session's
    `finally: session.close()` runs and every line drops inactive. Python's default
    for both ends the process at once: a door-lock pulse in flight, or a line left
    `on`, would stay driven after the process is gone (an MCP host stops its server
    with SIGTERM; closing the terminal sends SIGHUP). SIGKILL cannot be caught.

    Returns a function that puts the previous handlers back. Off the main thread a
    handler cannot be set: nothing is installed, and the function does nothing.
    """
    if threading.current_thread() is not threading.main_thread():
        return lambda: None
    names = [name for name in ("SIGTERM", "SIGHUP") if hasattr(signal, name)]

    def _exit(signum: int, _frame: Any) -> None:
        # A second signal must not cut the cleanup short between two lines.
        for name in names:
            signal.signal(getattr(signal, name), signal.SIG_IGN)
        raise SystemExit(128 + signum)

    previous = {name: signal.signal(getattr(signal, name), _exit) for name in names}

    def restore() -> None:
        for name, handler in previous.items():
            signal.signal(getattr(signal, name), handler)

    return restore


def run_stdio(
    session: SimSession,
    *,
    trace_out: Path | None = None,
    init_timeout: float = MCP_INIT_TIMEOUT_S,
    lock: ThreadLock | None = None,
    on_change: Callable[[], None] | None = None,
    on_ready: Callable[[], None] | None = None,
    on_close: Callable[[], None] | None = None,
) -> None:
    """
    Serve `session` over stdio until the client closes stdin, then close it.

    On the way out — stdin closed, Ctrl-C, SIGTERM — it runs `on_close`, writes the
    session trace to `trace_out` when given, and closes the session (on `linux`: every
    line dropped inactive and released). `init_timeout` 0 waits forever; otherwise a
    server no client initializes within that many seconds exits, so an orphaned spawn
    does not hold a port. The other arguments are those of `mcp_server.serve_stdio`.
    """
    import anyio

    def close() -> None:
        try:
            if on_close is not None:
                on_close()
            if trace_out is not None:
                session.write_trace(trace_out)
        finally:
            session.close()

    def on_no_initialize() -> None:
        # The client started us and let go without closing stdin (Claude Desktop does
        # this when it restarts a server before the handshake). Nothing will ever
        # arrive, and the SDK's stdin thread cannot be cancelled: free the port, exit.
        print(
            f"no MCP client sent `initialize` within {init_timeout:g} s; exiting so an "
            "orphaned server does not hold the UI port (--init-timeout 0 waits forever)",
            file=sys.stderr,
        )
        close()
        sys.stderr.flush()
        os._exit(0)

    async def serve() -> None:
        await serve_stdio(
            session,
            lock=lock,
            on_change=on_change,
            on_ready=on_ready,
            init_timeout=init_timeout or None,
            on_no_initialize=on_no_initialize,
        )

    try:
        anyio.run(serve)
    except KeyboardInterrupt:
        pass
    except SystemExit as stop:
        # SIGTERM / SIGHUP (`exit_on_signals`): drop the lines, then leave at once —
        # the SDK's stdin thread is not a daemon and would hold the exit (as above).
        # The exit happens even when the cleanup raises.
        try:
            close()
        finally:
            sys.stderr.flush()
            os._exit(stop.code if isinstance(stop.code, int) else 1)
    finally:
        close()


def serve_mcp(
    agent: str | Path = "agent.toml",
    *,
    target: str = "sim",
    board: str | None = None,
    registry: GateRegistry | str | Path | None = None,
    trace_out: str | Path | None = None,
    raw: bool = False,
    init_timeout: float = MCP_INIT_TIMEOUT_S,
) -> None:
    """
    Serve the agent of `agent` (an `agent.toml`) as a gated MCP server over stdio, and
    return when the client closes stdin — what `neuroedge mcp serve` does, from Python.

    Every `@action` of the agent is a tool, and every `tools/call` takes the one road
    to hardware: the tool schema, `c.do()`, the gate, a single-use verdict token, the
    HAL. `target` is ``"sim"`` or ``"linux"`` (real GPIO lines; the process then leaves
    through its cleanup on SIGTERM and SIGHUP); `board` defaults to the target's
    reference board; `registry` resolves `neuroedge://` gate URIs.

    `trace_out` writes the session trace there on exit. The user's words are hashed in
    it unless `raw=True` keeps them as plain text (a `UserWarning`, and the trace says
    ``metadata.anonymized = false``). stdout belongs to the protocol: anything for
    people goes to stderr. Needs the MCP SDK: ``pip install 'neuroedge[mcp]'``
    (`NeuroEdgeError` otherwise, before anything is wired).

    It owns the process: when no client sends `initialize` within `init_timeout`
    seconds (0 waits forever), and on SIGTERM/SIGHUP with `target="linux"`, it cleans
    up and then ends the whole process with `os._exit` — the SDK's stdin thread cannot
    be cancelled any other way. Run it in a process of its own.
    """
    _sdk()
    events = None
    if trace_out is not None:
        from ..testing.recorder import TraceRecorder

        events = TraceRecorder(anonymize=not raw)
        if raw:
            warnings.warn(
                "raw=True keeps the user's words in the trace file as plain text "
                "(metadata.anonymized = false)",
                UserWarning,
                stacklevel=2,
            )
    restore = exit_on_signals() if target == "linux" else None  # before the lines are requested
    try:
        session = SimSession.load(
            agent,
            target=target,
            board_id=board,
            registry=GateRegistry(registry) if isinstance(registry, str | Path) else registry,
            events=events,
        )
        warning = session.canned_fact_warning()
        if warning is not None:
            print(f"! {warning}", file=sys.stderr)
        run_stdio(
            session,
            trace_out=None if trace_out is None else Path(trace_out),
            init_timeout=init_timeout,
        )
    finally:
        if restore is not None:
            restore()
