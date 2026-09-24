"""
NeuroEdge command line interface (Typer + Rich).

Sprint 1 implements the commands that operate on the frozen artifacts — gate
resolution, gate publication, trace validation, board inspection. Commands whose
engines land in later sprints say so and exit non-zero rather than printing a
result they did not compute: a CLI that prints "PASS" without running anything
is worse than one that is honest about being unfinished, because the output ends
up quoted as evidence.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from functools import partial
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from ..engine import (
    GateRegistry,
    ResolvedGate,
    gate_canonical_json,
    gate_digest,
    resolve_gate_file,
    resolve_gate_uri,
)
from ..errors import BuildFailed, NeuroEdgeError, VerificationError
from ..hal.board import available_boards, load_board_by_id
from ..paths import gates_dir, repo_root
from ..trace import load_trace

app = typer.Typer(
    name="neuroedge",
    help="NeuroEdge — Typed Action Contract Platform for Physical AI",
    add_completion=False,
)
gate_app = typer.Typer(name="gate", help="Resolve, lint and publish safety gates")
trace_app = typer.Typer(name="trace", help="Inspect and validate execution traces")
board_app = typer.Typer(name="board", help="Inspect board capability declarations")
mcp_app = typer.Typer(name="mcp", help="Serve the agent's gated tools over MCP")

app.add_typer(gate_app, name="gate")
app.add_typer(trace_app, name="trace")
app.add_typer(board_app, name="board")
app.add_typer(mcp_app, name="mcp")

console = Console()
err_console = Console(stderr=True)

# `mcp serve` exits when no client initializes within this window (a leaked, orphaned
# spawn). Clients send `initialize` at once, so 30 s only has to beat a slow start.
MCP_INIT_TIMEOUT_S = 30.0


def _fail(error: NeuroEdgeError) -> None:
    """Render a three-part diagnostic to stderr and exit non-zero."""
    err_console.print(f"[bold red]✗ {error.code}[/bold red] [cyan]{escape(error.where)}[/cyan]")
    err_console.print(f"  [bold]why:[/bold] {escape(error.why)}")
    if isinstance(getattr(error, "principle", None), int):
        err_console.print(f"  [bold]rule:[/bold] Proposal Appendix B.5 principle {error.principle}")
    err_console.print(f"  [bold]fix:[/bold] {escape(error.how)}")
    raise typer.Exit(code=1)


def _fail_build(failed: BuildFailed) -> None:
    """Render every problem a build check collected, then exit 1."""
    err_console.print(f"[bold red]✗ {failed.code} build failed[/bold red] {escape(failed.where)}")
    for problem in failed.problems:
        err_console.print(
            f"\n[bold red]✗ {problem.code}[/bold red] [cyan]{escape(problem.where)}[/cyan]"
        )
        err_console.print(f"  why: {escape(problem.why)}")
        err_console.print(f"  fix: {escape(problem.how)}")
    err_console.print(f"\n[bold red]{len(failed.problems)} problem(s).[/bold red]")
    raise typer.Exit(code=1)


def _load_gate(target: str, registry_root: Path | None = None) -> ResolvedGate:
    """Resolve a gate given either a `neuroedge://` URI or a filesystem path."""
    registry = GateRegistry(registry_root) if registry_root is not None else None
    if target.startswith("neuroedge://"):
        return resolve_gate_uri(target, registry=registry)
    return resolve_gate_file(Path(target), registry=registry)


REGISTRY_OPTION = typer.Option(
    None,
    "--registry",
    "-r",
    help="Directory backing neuroedge:// lookups (default: gates/)",
)


# --------------------------------------------------------------------------
# gate
# --------------------------------------------------------------------------


@gate_app.command(name="resolve")
def gate_resolve(
    target: str = typer.Argument(..., help="Gate YAML path or neuroedge:// URI"),
    as_json: bool = typer.Option(False, "--json", help="Emit the resolved artifact as JSON"),
    registry: Path = REGISTRY_OPTION,
):
    """
    Resolve a gate's `extends` chain and report the effective policy.

    Enforces the five inheritance safety principles (Proposal Appendix B.5).
    """
    try:
        gate = _load_gate(target, registry)
    except NeuroEdgeError as error:
        _fail(error)
        return

    if as_json:
        # Plain stdout, not rich: FORCE_COLOR would otherwise inject ANSI
        # codes and the "machine-readable" output would stop being JSON.
        typer.echo(json.dumps(gate.to_artifact(), indent=2, ensure_ascii=False))
        return

    console.print(
        Panel(
            f"[bold]{gate.name}@{gate.version}[/bold]\n"
            f"inheritance: {' → '.join(gate.chain)} "
            f"([cyan]{gate.inheritance_levels}[/cyan] level(s))\n"
            f"digest: [dim]{gate_digest(gate)}[/dim]",
            title="Resolved gate",
            border_style="green",
        )
    )

    table = Table(title="Effective allow_when")
    table.add_column("Criterion", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Authored clause", style="yellow")
    table.add_column("Admits", style="green")
    for criterion in sorted(gate.constraints):
        constraint = gate.constraints[criterion]
        table.add_row(
            criterion,
            constraint.kind,
            json.dumps(constraint.raw, ensure_ascii=False),
            constraint.describe(),
        )
    console.print(table)

    fail_policy = gate.budget.get("fail", "closed")
    style = "green" if fail_policy == "closed" else "bold red"
    console.print(
        f"on_block: [bold]{gate.on_block.get('action')}[/bold]"
        + (f" → {gate.on_block['to']}" if gate.on_block.get("to") else "")
    )
    console.print(
        f"budget:   p95 {gate.budget.get('p95_latency_ms')} ms · "
        f"fail [{style}]{fail_policy}[/{style}]"
    )


@gate_app.command(name="explain")
def gate_explain(
    target: str = typer.Argument(..., help="Gate YAML path or neuroedge:// URI"),
    registry: Path = REGISTRY_OPTION,
):
    """
    Explain a gate for a reviewer who does not read YAML: where each criterion
    comes from, what a child tightened, and what happens when it blocks.
    """
    from ..engine.gate_explain import explain_gate_file, explain_gate_uri
    from .explain import render

    gate_registry = GateRegistry(registry) if registry is not None else None
    try:
        if target.startswith("neuroedge://"):
            explanation = explain_gate_uri(target, gate_registry)
        else:
            explanation = explain_gate_file(Path(target), gate_registry)
    except NeuroEdgeError as error:
        _fail(error)
        return
    render(explanation, console)


@gate_app.command(name="lint")
def gate_lint(
    directory: Path = typer.Argument(None, help="Directory of gate YAML files (default: gates/)"),
    registry: Path = REGISTRY_OPTION,
):
    """
    Resolve every gate in a directory and report any that violate the schema
    or the inheritance safety principles.
    """
    root = directory or gates_dir()
    if not root.is_dir():
        err_console.print(f"[red]✗ no such directory: {root}[/red]")
        raise typer.Exit(code=1)

    paths = sorted(root.rglob("*.yaml"))
    if not paths:
        console.print(f"[yellow]No gate files found under {root}[/yellow]")
        raise typer.Exit(code=1)

    # Bases are addressed by neuroedge:// URI. An explicit --registry wins;
    # otherwise a fixture tree keeps its bases in a sibling `registry/`
    # directory, and the real corpus resolves against gates/.
    if registry is not None:
        gate_registry = GateRegistry(registry)
    else:
        for candidate in (root / "registry", root.parent / "registry"):
            if candidate.is_dir():
                gate_registry = GateRegistry(candidate)
                break
        else:
            gate_registry = GateRegistry()

    failures = 0
    table = Table(title=f"Gate lint — {root}")
    table.add_column("Gate", style="cyan")
    table.add_column("Levels", justify="right")
    table.add_column("Fail policy")
    table.add_column("Status", style="bold")

    for path in paths:
        try:
            gate = resolve_gate_file(path, registry=gate_registry)
        except NeuroEdgeError as error:
            failures += 1
            table.add_row(path.name, "—", "—", "[red]FAIL[/red]")
            err_console.print(
                f"\n[bold red]✗ {error.code}[/bold red] [cyan]{escape(error.where)}[/cyan]"
            )
            err_console.print(f"  why: {escape(error.why)}")
            err_console.print(f"  fix: {escape(error.how)}")
            continue
        policy = gate.budget.get("fail", "closed")
        table.add_row(
            f"{gate.name}@{gate.version}",
            str(gate.inheritance_levels),
            policy if policy == "closed" else f"[bold red]{policy}[/bold red]",
            "[green]OK[/green]",
        )

    console.print(table)
    if failures:
        err_console.print(
            f"[bold red]{failures} of {len(paths)} gate(s) failed to resolve.[/bold red]"
        )
        raise typer.Exit(code=1)
    console.print(f"[bold green]✓ {len(paths)} gate(s) resolved.[/bold green]")


@gate_app.command(name="publish")
def gate_publish(
    gate_file: Path = typer.Argument(..., help="Path to the gate YAML file"),
    out: Path = typer.Option(None, "--out", "-o", help="Write canonical JSON here"),
    registry: Path = REGISTRY_OPTION,
):
    """
    Compile a gate to RFC 8785 canonical JSON and report its SHA-256 digest.

    The canonical bytes and the digest are the artifact that gets signed and
    distributed. Signing itself needs the registry key material, which arrives
    with the Gate Registry in Khối 3 — so this command stops at the digest
    rather than claiming to have signed anything.
    """
    try:
        gate = _load_gate(str(gate_file), registry)
    except NeuroEdgeError as error:
        _fail(error)
        return

    payload = gate_canonical_json(gate)
    console.print(f"[bold]Compiled[/bold] [cyan]{gate_file}[/cyan] → RFC 8785 canonical JSON")
    console.print(f"  gate:   [bold]{gate.name}@{gate.version}[/bold]")
    console.print(f"  chain:  {' → '.join(gate.chain)}")
    console.print(f"  bytes:  {len(payload)}")
    # Plain stdout so the digest is copyable byte-for-byte under any terminal.
    typer.echo(f"  digest: {gate_digest(gate)}")

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(payload)
        console.print(f"  written: [cyan]{out}[/cyan]")

    console.print(
        "[yellow]Note:[/yellow] cryptographic signing and registry upload require the "
        "Gate Registry (Khối 3); this command produces the canonical bytes and digest only."
    )


@gate_app.command(name="add")
def gate_add(
    uri: str = typer.Argument(..., help="Gate URI, e.g. neuroedge://gates/unlock_door@1.2.0"),
):
    """Resolve a gate from the registry and report what inheriting it would impose."""
    try:
        gate = resolve_gate_uri(uri)
    except NeuroEdgeError as error:
        _fail(error)
        return
    console.print(f"[bold green]✓[/bold green] {uri} resolves to {gate.name}@{gate.version}")
    console.print(f"  criteria:    {sorted(gate.evaluate)}")
    console.print(f"  fail policy: {gate.budget.get('fail', 'closed')}")
    console.print(
        "[yellow]Note:[/yellow] signature verification and remote fetch arrive with the "
        "Gate Registry (Khối 3); this resolves against the local gates/ directory."
    )


# --------------------------------------------------------------------------
# trace
# --------------------------------------------------------------------------


@trace_app.command(name="validate")
def trace_validate(
    trace_files: list[Path] = typer.Argument(..., help="Trace JSON file(s) to validate"),
):
    """Validate traces against schemas/trace.v1.json (FR-TRC-08)."""
    failures = 0
    for path in trace_files:
        try:
            trace = load_trace(path)
        except NeuroEdgeError as error:
            failures += 1
            err_console.print(
                f"[bold red]✗ {error.code}[/bold red] [cyan]{escape(error.where)}[/cyan]"
            )
            err_console.print(f"  why: {escape(error.why)}")
            err_console.print(f"  fix: {escape(error.how)}")
            continue
        console.print(
            f"[bold green]✓ VALID[/bold green] [cyan]{path}[/cyan] — "
            f"{len(trace['events'])} event(s), target {trace['metadata']['target']}"
        )
    if failures:
        raise typer.Exit(code=1)


@trace_app.command(name="view")
def trace_view(
    trace_file: Path = typer.Argument(..., help="Trace JSON file"),
    out: Path = typer.Option(
        None, "--out", "-o", help="HTML file to write (default: next to the trace)"
    ),
    open_browser: bool = typer.Option(False, "--open", help="Open the page in the default browser"),
):
    """
    Write a self-contained HTML view of a trace: devices, sensors, screen,
    gate verdicts and a timeline you can scrub. Opens offline, no server.
    """
    from ..viz import render_trace_html

    try:
        trace = load_trace(trace_file)
    except NeuroEdgeError as error:
        _fail(error)
        return
    target = out or trace_file.with_suffix(".html")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_trace_html(trace), encoding="utf-8")
    console.print(
        f"[bold green]✓[/bold green] {escape(str(target))} ({len(trace['events'])} events)"
    )
    if open_browser:
        import webbrowser

        webbrowser.open(target.resolve().as_uri())


@trace_app.command(name="export")
def trace_export(
    trace_file: Path = typer.Argument(..., help="Trace JSON file"),
    format: str = typer.Option("chrome", "--format", "-f", help="Export format: chrome"),
    out: Path = typer.Option(
        None, "--out", "-o", help="Output file (default: <trace>.chrome.json)"
    ),
):
    """
    Export a trace for timing analysis. `chrome` writes Chrome Trace Event JSON
    that Perfetto (ui.perfetto.dev) and chrome://tracing open.
    """
    from ..viz import to_chrome_trace

    if format != "chrome":
        _fail(
            NeuroEdgeError(
                where=f"--format {format}",
                why="unknown export format",
                how="use --format chrome",
            )
        )
        return
    try:
        trace = load_trace(trace_file)
    except NeuroEdgeError as error:
        _fail(error)
        return
    target = out or trace_file.with_suffix(".chrome.json")
    target.write_text(json.dumps(to_chrome_trace(trace), ensure_ascii=False), encoding="utf-8")
    console.print(f"[bold green]✓[/bold green] {escape(str(target))} — open it in ui.perfetto.dev")


@trace_app.command(name="show")
def trace_show(
    trace_file: Path = typer.Argument(..., help="Trace JSON file"),
):
    """Print a trace's event timeline."""
    try:
        trace = load_trace(trace_file)
    except NeuroEdgeError as error:
        _fail(error)
        return

    metadata = trace["metadata"]
    console.print(
        Panel(
            f"session [bold cyan]{metadata['session_id']}[/bold cyan]\n"
            f"target {metadata['target']} · board {metadata['board_id']}\n"
            f"agent {metadata['agent_version']} · {metadata['timestamp_utc']}",
            title=str(trace_file),
            border_style="green",
        )
    )
    table = Table()
    table.add_column("Offset", justify="right", style="dim")
    table.add_column("Event", style="bold")
    table.add_column("Data")
    for event in trace["events"]:
        table.add_row(
            f"{event['offset_ms']} ms",
            event["type"],
            json.dumps(event["data"], ensure_ascii=False),
        )
    console.print(table)


# --------------------------------------------------------------------------
# board
# --------------------------------------------------------------------------


@board_app.command(name="list")
def board_list():
    """List the board capability declarations in boards/."""
    boards = available_boards()
    if not boards:
        console.print("[yellow]No board declarations found.[/yellow]")
        raise typer.Exit(code=1)

    table = Table(title="Board profiles")
    table.add_column("Board id", style="cyan")
    table.add_column("Target", style="magenta")
    table.add_column("MCU")
    table.add_column("digital.out pins", style="green")
    for board in boards:
        table.add_row(board.id, board.target, board.mcu, ", ".join(board.pins) or "—")
    console.print(table)


@board_app.command(name="show")
def board_show(
    board_id: str = typer.Argument(..., help="Board id, e.g. esp32s3-box-3"),
):
    """Show one board's declared capabilities across the five HAL primitives."""
    try:
        board = load_board_by_id(board_id)
    except NeuroEdgeError as error:
        _fail(error)
        return

    console.print(
        Panel(
            f"[bold]{board.name or board.id}[/bold]\n"
            f"id {board.id} · target {board.target} · mcu {board.mcu}",
            title="Board",
            border_style="green",
        )
    )
    table = Table()
    table.add_column("Primitive", style="cyan")
    table.add_column("Declared parameters")
    for primitive in ("audio.in", "audio.out", "digital.out", "sensor.read", "display"):
        if board.supports(primitive):
            table.add_row(primitive, json.dumps(board.capability(primitive), ensure_ascii=False))
        else:
            table.add_row(primitive, "[red]not provided[/red]")
    console.print(table)


# --------------------------------------------------------------------------
# top level
# --------------------------------------------------------------------------


@mcp_app.command(name="tools")
def mcp_tools(
    agent: Path = typer.Option(None, "--agent", "-a", help="agent.toml (default as for `run`)"),
    as_json: bool = typer.Option(False, "--json", help="Print the MCP tool list as JSON"),
    openai: bool = typer.Option(
        False, "--openai", help="Print OpenAI function-calling tools (JSON)"
    ),
    external: bool = typer.Option(
        False,
        "--external",
        help="Also connect to the [mcp.servers] of agent.toml and list their allowed tools",
    ),
):
    """List the agent's tools — one per @action, with the schema models see."""
    session = _start_session("mcp tools", agent, "sim", "sim-default", None)
    if external:
        _external_tools(session, as_json=as_json, openai=openai)
        return
    if as_json or openai:
        typer.echo(
            json.dumps(
                session.tools.openai() if openai else session.tools.mcp(),
                indent=2,
                ensure_ascii=False,
            )
        )
        return
    table = Table(title=f"Tools of {session.manifest.label}")
    table.add_column("Tool", style="cyan")
    table.add_column("Gate")
    table.add_column("Arguments")
    for spec in session.tools.specs.values():
        from ..actions.tools import input_schema

        props = input_schema(spec)["properties"]
        table.add_row(spec.name, spec.gate, escape(", ".join(props) or "—"))
    console.print(table)


def _external_tools(session: Any, *, as_json: bool, openai: bool) -> None:
    """What System 2 is offered as an MCP host (Q-27): device tools, then external ones."""
    import anyio

    from ..mcp_host import SEPARATOR, ToolHost

    async def offered() -> list[dict[str, Any]]:
        async with ToolHost(session) as host:
            return host.tools()

    tools = anyio.run(offered)
    down = {e["server"]: e["reason"] for e in session.events.of_type("mcp_server_unavailable")}
    if as_json or openai:
        shaped = (
            tools
            if openai
            else [
                {
                    "name": t["function"]["name"],
                    "description": t["function"]["description"],
                    "inputSchema": t["function"]["parameters"],
                }
                for t in tools
            ]
        )
        typer.echo(json.dumps(shaped, indent=2, ensure_ascii=False))
        return
    table = Table(title=f"Tools System 2 is offered — {session.manifest.label}")
    table.add_column("Tool", style="cyan")
    table.add_column("Through")
    table.add_column("Arguments")
    for tool in tools:
        name = tool["function"]["name"]
        through = (
            f"external `{name.split(SEPARATOR, 1)[0]}` · information only"
            if SEPARATOR in name and name not in session.tools
            else "this agent's MCP server · gate"
        )
        props = tool["function"]["parameters"].get("properties", {})
        table.add_row(escape(name), escape(through), escape(", ".join(props) or "—"))
    console.print(table)
    for server, reason in down.items():
        console.print(f"[yellow]✗ {escape(server)} unavailable:[/yellow] {escape(reason)}")


@mcp_app.command(name="serve")
def mcp_serve(
    agent: Path = typer.Option(None, "--agent", "-a", help="agent.toml (default as for `run`)"),
    board: str = typer.Option("sim-default", "--board", "-b", help="Board profile id"),
    trace_out: Path = typer.Option(
        None, "--trace-out", help="Write the session trace here on exit"
    ),
    registry: Path | None = REGISTRY_OPTION,
    ui: bool = typer.Option(
        False, "--ui", help="Also serve this session as the live sim page on 127.0.0.1"
    ),
    port: int = typer.Option(8765, "--port", help="Port for --ui (0 picks a free one)"),
    open_browser: bool = typer.Option(
        False, "--open", help="With --ui, open the page in a browser"
    ),
    init_timeout: float = typer.Option(
        MCP_INIT_TIMEOUT_S,
        "--init-timeout",
        help="Exit if no client sends `initialize` within this many seconds (0: wait forever)",
    ),
):
    """
    Serve the agent as a gated MCP server over stdio: every @action is a tool,
    and every tools/call goes through the tool schema, c.do() and the gate.
    With --ui the same session is shown live in the browser: a tool call from
    the MCP client moves the virtual devices on the page at once. The page never
    takes the MCP server down: a taken port falls back to a free one (URL on stderr).
    """
    import anyio

    from ..mcp_server import _sdk, serve_stdio

    try:
        _sdk()
    except NeuroEdgeError as error:
        _fail(error)
        return
    session = _start_session("mcp serve", agent, "sim", board, registry)
    page = _mcp_page(session, port) if ui else None
    # stdout is the protocol channel; anything for people goes to stderr.
    err_console.print(
        f"neuroedge MCP server · {escape(session.manifest.label)} · "
        f"{len(session.tools.specs)} tool(s) · stdio"
    )
    if page is not None:
        err_console.print(f"sim UI at {page.url} (same session)", markup=False, highlight=False)

    def on_ready() -> None:
        if page is not None and open_browser:
            import webbrowser

            webbrowser.open(page.url)

    def close() -> None:
        if page is not None:
            page.stop()
        if trace_out is not None:
            trace_out.parent.mkdir(parents=True, exist_ok=True)
            trace_out.write_text(
                json.dumps(session.trace(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )

    def on_no_initialize() -> None:
        # The client started us and let go without closing stdin (Claude Desktop does
        # this when it restarts a server before the handshake). Nothing will ever
        # arrive, and the SDK's stdin thread cannot be cancelled: free the port, exit.
        err_console.print(
            f"no MCP client sent `initialize` within {init_timeout:g} s; exiting so an "
            "orphaned server does not hold the UI port (--init-timeout 0 waits forever)",
            markup=False,
            highlight=False,
        )
        close()
        sys.stderr.flush()
        os._exit(0)

    serve = partial(
        serve_stdio,
        session,
        lock=page.lock if page is not None else None,
        on_change=page.notify if page is not None else None,
        on_ready=on_ready,
        init_timeout=init_timeout or None,
        on_no_initialize=on_no_initialize,
    )
    try:
        anyio.run(serve)
    except KeyboardInterrupt:
        pass
    finally:
        close()


def _mcp_page(session: Any, port: int) -> Any:
    """
    The `--ui` page for `mcp serve`, which must never cost the MCP server itself.

    The port is taken most often by an older server of the same agent that Claude
    Desktop left running. Exiting would only show "Server disconnected" in Desktop,
    so a taken port — the default or one passed with --port — falls back to a free
    one, and the real URL goes to stderr (Desktop's server log). Only when no port
    at all can be had does the server run without the page.
    """
    from ..sim.ui import SessionServer

    try:
        return SessionServer(session, port=port).start()
    except NeuroEdgeError as error:
        taken = error
    if port != 0:
        try:
            page = SessionServer(session, port=0).start()
        except NeuroEdgeError as error:
            taken = error
        else:
            err_console.print(
                f"warning: sim UI port {port} is taken ({taken.why}) — an older server may "
                f"still be running; the page is at {page.url} instead",
                markup=False,
                highlight=False,
            )
            return page
    err_console.print(
        f"warning: no sim UI ({taken.why}); serving MCP without the page",
        markup=False,
        highlight=False,
    )
    return None


@mcp_app.command(name="desktop-config")
def mcp_desktop_config(
    agent: Path = typer.Option(None, "--agent", "-a", help="agent.toml (default as for `run`)"),
    ui: bool = typer.Option(False, "--ui", help="Serve with --ui: the live sim page too"),
    port: int = typer.Option(8765, "--port", help="Port for --ui"),
    trace_out: Path = typer.Option(
        None, "--trace-out", help="Have the server write its session trace here on exit"
    ),
    name: str = typer.Option(None, "--name", help="Key under mcpServers (default: agent name)"),
    write: bool = typer.Option(
        False, "--write", help="Write the entry into Claude Desktop's config (with a backup)"
    ),
    config_path: Path = typer.Option(
        None, "--config-path", help="Config file for --write (default: Claude Desktop's)"
    ),
):
    """
    Print the Claude Desktop `mcpServers` entry for `mcp serve` — absolute paths only,
    because Desktop starts the server from `/` with a minimal PATH, not from your shell.
    With --write, set that one entry in Desktop's config file and keep everything else.
    """
    import importlib.util

    from ..mcp_desktop import default_config_path, server_entry, write_entry

    if importlib.util.find_spec("mcp") is None:
        _fail(
            NeuroEdgeError(
                where="neuroedge mcp desktop-config",
                why="the MCP Python SDK (`mcp`) is not installed, so Desktop's "
                "`mcp serve` would exit at once",
                how="pip install 'neuroedge[mcp]'",
            )
        )
        return
    agent_path = (agent or _default_agent()).expanduser().resolve()
    session = _start_session("mcp desktop-config", agent_path, "sim", "sim-default", None)
    key = name or session.manifest.name
    entry = server_entry(agent_path, ui=ui, port=port, trace_out=trace_out)
    if "env" in entry:
        typer.echo(
            "note: this interpreter does not import this neuroedge on its own; "
            f"env.PYTHONPATH pins {entry['env']['PYTHONPATH']}",
            err=True,
        )
    if not write:
        # Plain stdout, not rich: the output is meant to be pasted or piped.
        typer.echo(json.dumps({"mcpServers": {key: entry}}, indent=2, ensure_ascii=False))
        return
    target = config_path or default_config_path()
    try:
        changed, backup = write_entry(target, key, entry)
    except NeuroEdgeError as error:
        _fail(error)
        return
    if not changed:
        typer.echo(f"mcpServers[{key!r}] in {target} is already up to date.")
        return
    typer.echo(f"Wrote mcpServers[{key!r}] to {target}")
    if backup is not None:
        typer.echo(f"Backup of the previous file: {backup}")
    typer.echo("Quit Claude Desktop completely (not just close the window), then reopen it.")


def _empty_categories(counts: dict[str, tuple[int, Path, str]]) -> VerificationError | None:
    """
    A `VerificationError` naming every category `verify` counted zero of, or
    None. Zero artifacts is a failure, never a pass (FR-CLI-03, TSK-S3-19).
    """
    empty = [(label, where, state) for label, (n, where, state) in counts.items() if n == 0]
    if not empty:
        return None
    reasons = []
    for label, where, state in empty:
        reasons.append(f"0 {label}: {where} {state if where.is_dir() else 'does not exist'}")
    return VerificationError(
        where=", ".join(dict.fromkeys(str(where) for _, where, _ in empty)),
        why="; ".join(reasons) + " — a sweep over zero artifacts proves nothing",
        how=(
            "run from a NeuroEdge checkout or an installed wheel, or point NEUROEDGE_ROOT "
            f"(now {repo_root()}) at a tree with gates/ and fixtures/traces/; "
            "pass at least one target to --targets"
        ),
    )


@app.command()
def verify(
    targets: str = typer.Option(
        "sim", "--targets", help="Comma-separated targets to replay on: sim, linux"
    ),
):
    """
    Verify the frozen artifacts and target equivalence (A2).

    Every gate resolves, every canonical trace validates, and every canonical
    trace replays on each requested target to the decisions it records —
    verdict sequence and pin commands (FR-CI-07). `linux` needs GPIO lines:
    a board, or `scripts/setup_gpio_sim.sh`.
    """
    from ..testing.golden import GoldenComparator
    from ..testing.player import TracePlayer

    root = repo_root()
    gates_root = gates_dir()
    traces_root = root / "fixtures" / "traces"
    requested = [t.strip() for t in targets.split(",") if t.strip()]
    problems = 0
    resolved = 0
    replayed = 0

    console.print("[bold]Resolving gates in gates/[/bold]")
    for path in sorted(gates_root.rglob("*.yaml")):
        try:
            gate = resolve_gate_file(path)
            resolved += 1
            console.print(
                f"  [green]✓[/green] {gate.name}@{gate.version} "
                f"({gate.inheritance_levels} level(s), fail {gate.budget.get('fail')})"
            )
        except NeuroEdgeError as error:
            problems += 1
            err_console.print(f"  [red]✗[/red] {path.name}: [{error.code}] {escape(error.why)}")

    console.print("\n[bold]Validating canonical traces in fixtures/traces/[/bold]")
    traces = sorted(traces_root.glob("*.json"))
    valid = []
    for path in traces:
        try:
            load_trace(path)
            valid.append(path)
            console.print(f"  [green]✓[/green] {path.name}")
        except NeuroEdgeError as error:
            problems += 1
            err_console.print(f"  [red]✗[/red] {path.name}: [{error.code}] {escape(error.why)}")

    console.print(f"\n[bold]Replaying canonical traces on {', '.join(requested)}[/bold]")
    table = Table()
    table.add_column("Trace", style="cyan")
    for target in requested:
        table.add_column(target, justify="center")
    rows: dict[str, list[str]] = {path.name: [] for path in valid}
    for target in requested:
        for path in valid:
            try:
                result = asyncio.run(TracePlayer(path, target=target).replay())
                diff = GoldenComparator().compare(result, load_trace(path))
            except NeuroEdgeError as error:
                problems += 1
                rows[path.name].append("[red]✗[/red]")
                err_console.print(
                    f"  [red]✗[/red] {path.name} on {escape(target)}: [{error.code}] "
                    f"{escape(error.why)}\n    fix: {escape(error.how)}"
                )
                continue
            replayed += 1
            if diff.ok:
                rows[path.name].append(f"[green]✓[/green] {' '.join(result.verdicts)}")
            else:
                problems += 1
                rows[path.name].append("[red]✗ differs[/red]")
                for difference in diff.differences:
                    err_console.print(
                        f"  [red]✗[/red] {path.name} on {escape(target)}: {escape(str(difference))}"
                    )
    for name, cells in rows.items():
        table.add_row(name, *cells)
    console.print(table)

    empty = _empty_categories(
        {
            "gates resolved": (resolved, gates_root, "has no *.yaml gate that resolves"),
            "canonical traces validated": (
                len(valid),
                traces_root,
                "has no *.json trace that validates",
            ),
            "replays compared": (
                replayed,
                traces_root,
                f"had no trace replayed on targets {targets!r}",
            ),
        }
    )
    if empty is not None:
        _fail(empty)
    if problems:
        err_console.print(f"\n[bold red]{problems} problem(s) found.[/bold red]")
        raise typer.Exit(code=1)

    console.print(
        Panel(
            f"[green]Passed:[/green] all {resolved} gate(s) resolve, all {len(valid)} "
            f"canonical trace(s) validate, and {replayed} replay(s) on "
            f"{', '.join(requested)} match the verdicts and pin commands they record.\n\n"
            "[yellow]Compared:[/yellow] decisions only — not timing. Timing equivalence and "
            "the esp32s3 target arrive with Sprint 4 (TSK-S4-04).",
            title="neuroedge verify",
            border_style="green",
        )
    )


@app.command()
def replay(
    trace_file: Path = typer.Argument(..., help="Trace JSON file"),
    target: str = typer.Option("sim", "--target", "-t", help="Target to replay on: sim or linux"),
    agent: Path = typer.Option(
        None, "--agent", "-a", help="agent.toml that produced the trace (default: from metadata)"
    ),
    board: str = typer.Option(None, "--board", "-b", help="Board profile id (default per target)"),
    golden: Path = typer.Option(
        None, "--golden", "-g", help="Golden reference to compare against (default: the trace)"
    ),
    trace_out: Path = typer.Option(None, "--trace-out", help="Write the replayed trace here"),
    registry: Path | None = REGISTRY_OPTION,
):
    """
    Replay a trace on a live HAL and compare its decisions with a golden reference.

    The recorded facts are fed back in; gate verdicts and pin commands are
    recomputed on `--target`. Exit 0 when they match the golden (by default the
    trace itself), 1 on any difference (FR-CI-02, FR-CI-04).
    """
    from ..testing.golden import GoldenComparator, load_golden
    from ..testing.player import TracePlayer, dump

    try:
        player = TracePlayer(
            trace_file,
            target=target,
            agent=agent,
            board_id=board,
            registry=GateRegistry(registry) if registry is not None else None,
        )
        result = asyncio.run(player.replay())
        reference = load_golden(golden) if golden is not None else player.trace
    except NeuroEdgeError as error:
        _fail(error)
        return

    metadata = player.trace["metadata"]
    console.print(
        f"[bold]Replayed[/bold] [cyan]{escape(str(trace_file))}[/cyan] "
        f"(recorded on {escape(metadata['target'])} / {escape(metadata['board_id'])}) "
        f"on [bold]{escape(target)}[/bold] / {escape(result.hal.board.id)}"
    )
    table = Table(title="Gate verdicts")
    table.add_column("#", justify="right")
    table.add_column("Gate", style="cyan")
    table.add_column("Recorded")
    table.add_column("Replayed", style="bold")
    table.add_column("Reason")
    begins = [
        e["data"]["gate"] for e in result.replayed["events"] if e["type"] == "gate_evaluation_begin"
    ]
    for index, replayed in enumerate(result.gate_results):
        recorded = result.steps[index].result.get("verdict") if index < len(result.steps) else "—"
        style = "green" if replayed["verdict"] == recorded else "bold red"
        table.add_row(
            str(index + 1),
            escape(begins[index] if index < len(begins) else "?"),
            str(recorded),
            f"[{style}]{replayed['verdict']}[/{style}]",
            escape(str(replayed.get("reason", "—"))),
        )
    console.print(table)
    commands = [e["data"] for e in result.replayed["events"] if e["type"] == "actuator_command"]
    if commands:
        for command in commands:
            console.print(
                f"  pin {escape(command['pin'])}: {command['operation']} {command['duration_ms']} ms"
            )
    else:
        console.print("  no pin was driven")

    if trace_out is not None:
        dump(result, trace_out)
        console.print(f"  replayed trace: {escape(str(trace_out))}")

    diff = GoldenComparator().compare(result, reference)
    if diff.ok:
        what = escape(str(golden)) if golden is not None else "the recording"
        console.print(f"[bold green]✓ decisions match {what}[/bold green]")
        return
    err_console.print(
        f"[bold red]✗ NE4002 {len(diff.differences)} difference(s) from the golden reference"
        + (" — SAFETY REGRESSION" if diff.unsafe else "")
        + "[/bold red]"
    )
    for difference in diff.differences:
        err_console.print(f"  {escape(str(difference))}")
    raise typer.Exit(code=1)


@app.command()
def new(
    name: str = typer.Argument(..., help="Name of the new agent project (and its directory)"),
    template: str = typer.Option(
        "minimal",
        "--template",
        help="minimal (1 action, 1 gate, tests), villa-concierge or home-voice",
    ),
):
    """Scaffold an agent project: agent.toml, commands.toml, a gate, an @action, tests."""
    from ..templates import scaffold

    try:
        files = scaffold(name, template)
    except NeuroEdgeError as error:
        _fail(error)
        return
    console.print(f"[bold green]✓[/bold green] created {escape(name)}/ from template {template}")
    for path in files:
        console.print(f"  {escape(str(path))}")
    console.print(
        f"\nNext:\n  cd {escape(name)}\n"
        "  neuroedge build --target sim --board sim-default\n"
        "  neuroedge run\n"
        "  neuroedge test"
    )


def _default_agent() -> Path:
    """`agent.toml` here, else the sample agent of a source checkout."""
    here = Path("agent.toml")
    sample = repo_root() / "fixtures" / "agents" / "villa-concierge" / "agent.toml"
    return sample if not here.is_file() and sample.is_file() else here


def _start_session(verb: str, agent, target: str, board: str, registry, events=None):
    """Load the agent for an interactive `sim` session, or exit with the right code."""
    from ..sim import SimSession

    if target != "sim":
        err_console.print(
            Panel(
                f"`neuroedge {verb} --target {escape(target)}` is not implemented yet.\n\n"
                "Interactive sessions run on `sim` today. On `linux`, replay a trace "
                "instead: `neuroedge replay <trace> --target linux` (TSK-S3-05).",
                title=f"[yellow]Not implemented: {verb} --target {escape(target)}[/yellow]",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=2)
    try:
        return SimSession.load(
            agent or _default_agent(),
            board_id=board,
            registry=GateRegistry(registry) if registry is not None else None,
            events=events,
        )
    except BuildFailed as failed:
        _fail_build(failed)
    except NeuroEdgeError as error:
        _fail(error)
    raise AssertionError("unreachable")  # _fail* always exit


@app.command()
def run(
    agent: Path = typer.Option(
        None,
        "--agent",
        "-a",
        help="Path to agent.toml (default: ./agent.toml, else the villa-concierge sample)",
    ),
    target: str = typer.Option("sim", "--target", "-t", help="Target runtime environment"),
    board: str = typer.Option("sim-default", "--board", "-b", help="Board profile id"),
    command: str = typer.Option(
        None, "--command", "-c", help="Run one typed command and exit (for scripts and CI)"
    ),
    trace_out: Path = typer.Option(
        None, "--trace-out", help="Write the session trace (trace.v1 JSON) here on exit"
    ),
    ui: bool = typer.Option(
        False, "--ui", help="Serve the session as a live page on 127.0.0.1 (FR-TGT-06)"
    ),
    port: int = typer.Option(8765, "--port", help="Port for --ui"),
    no_browser: bool = typer.Option(False, "--no-browser", help="With --ui, do not open a browser"),
    registry: Path | None = REGISTRY_OPTION,
):
    """
    Run the agent on `sim`: type a command, see the gate verdict and the pins.
    With --ui the same session is shown live in the browser.

    Input is typed text matched by the agent's commands.toml — no network, no
    key (Q-15). The agent is build-checked against the board first.
    """
    from .run import run_session

    session = _start_session("run", agent, target, board, registry)
    if ui:
        from ..sim.ui import serve

        try:
            serve(session, port, console, open_browser=not no_browser)
        except NeuroEdgeError as error:
            _fail(error)  # e.g. the port is taken
        finally:
            if trace_out is not None:
                trace_out.parent.mkdir(parents=True, exist_ok=True)
                trace_out.write_text(
                    json.dumps(session.trace(), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
        return
    code = run_session(session, console, err_console, command=command, trace_out=trace_out)
    raise typer.Exit(code=code)


@app.command()
def build(
    target: str = typer.Option(..., "--target", "-t", help="Target runtime environment"),
    board: str = typer.Option("esp32s3-box-3", "--board", "-b", help="Board profile id"),
    agent: Path = typer.Option(Path("agent.toml"), "--agent", "-a", help="Path to agent.toml"),
    out: Path = typer.Option(Path("build"), "--out", "-o", help="Directory for build artifacts"),
    registry: Path | None = REGISTRY_OPTION,
):
    """Match the agent's capability needs against the board and compile its gates."""
    from ..engine.compiler import build as run_build

    try:
        report = run_build(
            agent,
            target=target,
            board_id=board,
            out_dir=out,
            registry=GateRegistry(registry) if registry is not None else None,
        )
    except BuildFailed as failed:
        _fail_build(failed)
        return
    except NeuroEdgeError as error:
        _fail(error)
        return

    console.print(
        f"[bold green]✓[/bold green] {report.agent} builds for {report.target} on {report.board}"
    )
    console.print(
        f"  checked: {report.requirements} requirement(s), {report.actions} action(s), "
        f"{report.gates} gate(s)"
    )
    for artifact in report.artifacts:
        console.print(f"  wrote:   {artifact}")


@app.command()
def test(
    path: Path = typer.Argument(None, help="Test directory or file (default: tests/ if present)"),
    pytest_args: list[str] = typer.Option(
        None, "--pytest-arg", help="Extra argument passed to pytest (repeatable)"
    ),
):
    """
    Run the agent's Action CI suite (pytest) and exit 0 only if every test passed.

    Exit codes (FR-CLI-03): 0 all passed · 1 a test failed, nothing was collected,
    or pytest could not run.
    """
    try:
        import pytest
    except ImportError:
        _fail(
            NeuroEdgeError(
                where="neuroedge test",
                why="pytest is not installed in this environment",
                how="pip install pytest (or pip install 'neuroedge[dev]')",
            )
        )
        return
    target = path if path is not None else (Path("tests") if Path("tests").is_dir() else Path("."))
    if not target.exists():
        _fail(
            NeuroEdgeError(
                where=str(target),
                why="no such test directory or file",
                how="pass the directory holding the agent's tests, e.g. neuroedge test tests/",
            )
        )
        return
    code = int(pytest.main([str(target), "-q", *(pytest_args or [])]))
    if code == pytest.ExitCode.NO_TESTS_COLLECTED:
        err_console.print(f"[bold red]✗ no tests collected under {escape(str(target))}[/bold red]")
    raise typer.Exit(code=0 if code == pytest.ExitCode.OK else 1)


@app.command()
def record(
    agent: Path = typer.Option(
        None, "--agent", "-a", help="Path to agent.toml (default as for `run`)"
    ),
    target: str = typer.Option("sim", "--target", "-t", help="Target to record on"),
    board: str = typer.Option("sim-default", "--board", "-b", help="Board profile id"),
    out: Path = typer.Option(Path("traces"), "--out", "-o", help="Directory, or a .json path"),
    command: str = typer.Option(None, "--command", "-c", help="Record one typed command and exit"),
    anonymize: bool = typer.Option(
        False, "--anonymize", help="Hash raw text at the source (FR-TRC-07); verdicts unchanged"
    ),
    registry: Path | None = REGISTRY_OPTION,
):
    """
    Record a session to a trace file that `trace validate` and `replay` accept.

    Same session as `run`; on exit the trace is validated against trace.v1 and
    written to `--out` (default `traces/<session_id>.json`).
    """
    from ..testing.recorder import TraceRecorder
    from .run import run_session

    recorder = TraceRecorder(anonymize=anonymize)
    session = _start_session("record", agent, target, board, registry, events=recorder)
    path = out if out.suffix == ".json" else out / f"{recorder.session_id}.json"
    code = run_session(session, console, err_console, command=command, trace_out=path)
    raise typer.Exit(code=code)


if __name__ == "__main__":
    app()
