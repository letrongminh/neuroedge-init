"""
The agent as a **gated MCP server** (Q-24): `neuroedge mcp serve`.

Every `@action` of the agent is listed as an MCP tool, with the JSON schema
derived from its signature (`neuroedge.actions.tools`). A `tools/call` from any
MCP client — an IDE assistant, another agent, a cloud LLM — becomes a
`ToolCall` with ``source = "mcp"`` and takes the one road to hardware:
arguments checked against the schema, then `c.do()`, the gate, a single-use
verdict token, the HAL. A client that was prompt-injected or hallucinates a
call is refused by the gate exactly like anyone else.

What the client gets back is the verdict, as JSON text and structured content:
``{"tool": "light_off", "status": "BLOCK", "reason": "condition_not_met", …}``.
A BLOCK is the gate working, not an error (`isError` stays false); a call the
schema rejects is an error (`isError` true), and nothing moved. Every tool
declares that shape as its `outputSchema` (`neuroedge.actions.tools.result_schema`),
which an MCP client checks the structured content of every non-error result against.

`neuroedge mcp serve --ui` (TSK-S3-27) also serves the session as the live
`sim` page (`neuroedge.sim.ui`); the two share one session through the hooks of
`build_server` — a lock and a change callback — so this module never imports
the page.

Needs the official MCP Python SDK: ``pip install 'neuroedge[mcp]'`` (MIT, every
transitive dependency permissive — NOTICE §B).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Protocol

from .actions.tools import ToolCall
from .errors import NeuroEdgeError


def _sdk() -> tuple[Any, Any]:
    try:
        import mcp.types as types
        from mcp.server.lowlevel import Server
    except ImportError as exc:
        raise NeuroEdgeError(
            where="neuroedge mcp serve",
            why="the MCP Python SDK (`mcp`) is not installed",
            how="pip install 'neuroedge[mcp]'",
        ) from exc
    return types, Server


class ThreadLock(Protocol):
    """A `threading.Lock`, or anything with the same blocking `acquire()` / `release()`."""

    def acquire(self, blocking: bool = ..., timeout: float = ...) -> bool: ...

    def release(self) -> None: ...


def build_server(
    session: Any,
    source: str = "mcp",
    raised: list | None = None,
    *,
    lock: ThreadLock | None = None,
    on_change: Callable[[], None] | None = None,
) -> Any:
    """
    An MCP `Server` over one agent session. Tool calls run one at a time, like turns.

    `source` is bound to the connection by whoever builds it — ``"mcp"`` for
    `neuroedge mcp serve`, ``"system_two"`` for System 2's in-process connection
    (`neuroedge.mcp_host`). A client never states its own `call_source`.

    A contract violation is never an MCP result. It propagates, and for an
    in-process caller that passes `raised`, the original exception is kept there
    so the caller re-raises it rather than the protocol's wrapper.

    When other threads share the session (the `sim` web page of
    `neuroedge mcp serve --ui` runs its turns on HTTP threads), pass their
    `lock`: every tool call then holds it as well, taken off the event loop so
    the loop never blocks. `on_change` runs after every call, whatever its
    outcome, so a watcher (the page's event stream) shows it at once. This
    module knows neither hook's owner.
    """
    import anyio
    import anyio.to_thread

    from . import __version__

    types, Server = _sdk()
    turns = anyio.Lock()

    async def list_tools(ctx: Any, params: Any) -> Any:
        return types.ListToolsResult(
            tools=[
                types.Tool(
                    name=tool["name"],
                    description=tool["description"],
                    input_schema=tool["inputSchema"],
                    output_schema=tool["outputSchema"],
                )
                for tool in session.tools.mcp()
            ]
        )

    async def call_tool(ctx: Any, params: Any) -> Any:
        call = ToolCall(params.name, dict(params.arguments or {}), source=source)
        async with turns:
            if lock is not None:
                # Shielded: once the worker thread holds the lock, this task must release it.
                with anyio.CancelScope(shield=True):
                    await anyio.to_thread.run_sync(lock.acquire)
            try:
                result = await session.call_tool(call)
            except NeuroEdgeError as error:
                if raised is not None:
                    raised.append(error)
                raise
            finally:
                if lock is not None:
                    lock.release()
                if on_change is not None:
                    on_change()
        content = result.content()
        return types.CallToolResult(
            content=[types.TextContent(text=json.dumps(content, ensure_ascii=False))],
            structured_content=content,
            is_error=result.status == "REJECTED",
        )

    return Server(
        f"neuroedge:{session.manifest.label}",
        version=__version__,
        instructions=(
            "Each tool is a physical action behind a NeuroEdge safety gate. Calling a tool asks "
            "for it; the gate decides. A BLOCK result says why and what happens instead."
        ),
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )


async def serve_stdio(
    session: Any,
    *,
    lock: ThreadLock | None = None,
    on_change: Callable[[], None] | None = None,
    on_ready: Callable[[], None] | None = None,
    init_timeout: float | None = None,
    on_no_initialize: Callable[[], None] | None = None,
) -> None:
    """
    Serve until the client closes stdin. `lock` and `on_change` as for `build_server`.

    `on_ready` runs once the SDK holds stdout: from then on fd 1 points at stderr
    for everything but the protocol, so nothing it starts (a browser) can write
    into the JSON-RPC channel.

    `init_timeout`: when no `initialize` request has arrived that many seconds after
    the transport opened, `on_no_initialize` runs. A client that let go of the
    process without closing its end of stdin (Claude Desktop does, when it restarts
    a server before the handshake) would otherwise leave it running forever. The
    SDK reads stdin in a thread that cancellation cannot interrupt, so the callback
    is expected to end the process; if it returns, serving goes on. Once
    initialized, a session may idle as long as it likes.
    """
    import anyio
    from mcp.server.stdio import stdio_server
    from mcp.shared.message import SessionMessage

    server = build_server(session, lock=lock, on_change=on_change)
    initialized = anyio.Event()

    async def watch(source: Any, sink: Any) -> None:
        async with source, sink:
            async for item in source:
                message = item.message if isinstance(item, SessionMessage) else None
                message = getattr(message, "root", message)  # older SDKs wrap it in a RootModel
                if getattr(message, "method", None) == "initialize":
                    initialized.set()
                await sink.send(item)

    async def watchdog() -> None:
        with anyio.move_on_after(init_timeout):
            await initialized.wait()
        if not initialized.is_set() and on_no_initialize is not None:
            on_no_initialize()

    async with stdio_server() as (read_stream, write_stream):
        if on_ready is not None:
            on_ready()
        sink, seen = anyio.create_memory_object_stream[Any](0)
        async with anyio.create_task_group() as group:
            group.start_soon(watch, read_stream, sink)
            if init_timeout:
                group.start_soon(watchdog)
            await server.run(seen, write_stream, server.create_initialization_options())
            group.cancel_scope.cancel()
