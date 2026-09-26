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
from ..errors import BoardCapabilityError, BuildFailed, NeuroEdgeError, VerificationError
from ..hal.board import REFERENCE_BOARD, SUPPORTED_TARGETS, available_boards, load_board_by_id
from ..paths import gates_dir, repo_root
from ..trace import load_trace
from .examples import epilog

app = typer.Typer(
    name="neuroedge",
    help="NeuroEdge — Typed Action Contract Platform for Physical AI",
    add_completion=False,
    epilog=epilog(""),
)
gate_app = typer.Typer(
    name="gate", help="Resolve, lint and publish safety gates", epilog=epilog("gate")
)
trace_app = typer.Typer(
    name="trace", help="Inspect and validate execution traces", epilog=epilog("trace")
)
board_app = typer.Typer(
    name="board", help="Inspect board capability declarations", epilog=epilog("board")
)
mcp_app = typer.Typer(
    name="mcp", help="Serve the agent's gated tools over MCP", epilog=epilog("mcp")
)

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


# Targets `replay` knows but cannot replay an arbitrary trace on yet, and the task that
# brings each. Asking for one exits 2 ("not implemented"), not 1 ("ran and failed").
# `verify --targets esp32s3` runs: the device replays the canonical traces (TSK-S4-09).
PLANNED_TARGETS = {"esp32s3": "TSK-S4-04"}

# Targets an interactive session (`run`, `record`, `mcp serve`) knows but does not run
# on yet, and the task that brings each. Same exit-2 contract as `PLANNED_TARGETS`.
PLANNED_SESSIONS = {"esp32s3": "TSK-S4-01"}


def _not_implemented_target(verb: str, target: str) -> None:
    """Say which task brings `target` to `verb`, then exit 2 (CONTRIBUTING.md §2)."""
    err_console.print(
        Panel(
            f"`neuroedge {verb}` on `{escape(target)}` is not implemented yet: replaying any "
            "trace needs its facts sent to the device and the live HAL on the board "
            f"({PLANNED_TARGETS[target]}).\n\n"
            "Replay on `sim` or `linux` today. The canonical traces already replay on the "
            "device: `neuroedge verify --targets esp32s3 --port <uart>`.",
            title=f"[yellow]Not implemented: {verb} on {escape(target)}[/yellow]",
            border_style="yellow",
        )
    )
    raise typer.Exit(code=2)


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


@gate_app.command(name="resolve", epilog=epilog("gate resolve"))
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


@gate_app.command(name="explain", epilog=epilog("gate explain"))
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


@gate_app.command(name="lint", epilog=epilog("gate lint"))
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


@gate_app.command(name="publish", epilog=epilog("gate publish"))
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


@gate_app.command(name="add", epilog=epilog("gate add"))
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


@trace_app.command(name="validate", epilog=epilog("trace validate"))
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


@trace_app.command(name="view", epilog=epilog("trace view"))
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


@trace_app.command(name="export", epilog=epilog("trace export"))
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


@trace_app.command(name="show", epilog=epilog("trace show"))
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


@board_app.command(name="list", epilog=epilog("board list"))
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


@board_app.command(name="show", epilog=epilog("board show"))
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


@mcp_app.command(name="tools", epilog=epilog("mcp tools"))
def mcp_tools(
    agent: Path = typer.Option(None, "--agent", "-a", help="agent.toml (default as for `run`)"),
    as_json: bool = typer.Option(False, "--json", help="Print the MCP tool list as JSON"),
    openai: bool = typer.Option(
        False, "--openai", help="Print OpenAI function-calling tools (JSON)"
    ),
    external: bool = typer.Option(
        False,
        "--external",
        help="Also connect to the \\[mcp.servers] of agent.toml and list their allowed tools",
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


@mcp_app.command(name="serve", epilog=epilog("mcp serve"))
def mcp_serve(
    agent: Path = typer.Option(None, "--agent", "-a", help="agent.toml (default as for `run`)"),
    target: str = typer.Option(
        "sim", "--target", "-t", help="Target to serve on: sim, or linux (real GPIO lines)"
    ),
    board: str = typer.Option(
        None, "--board", "-b", help="Board profile id (default: the target's reference board)"
    ),
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
    On `--target linux` a tool call drives real GPIO lines (as `run --target linux`).
    With --ui (sim only) the same session is shown live in the browser: a tool call from
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
    session = _start_session("mcp serve", agent, target, board, registry, ui=ui)
    page = _mcp_page(session, port) if ui else None
    # stdout is the protocol channel; anything for people goes to stderr.
    err_console.print(
        f"neuroedge MCP server · {escape(session.manifest.label)} · "
        f"{escape(session.target)}/{escape(session.hal.board.id)} · "
        f"{len(session.tools.specs)} tool(s) · stdio"
    )
    from .run import canned_fact_warning

    warning = canned_fact_warning(session)
    if warning is not None:
        err_console.print(f"[yellow]! {escape(warning)}[/yellow]")
    if page is not None:
        err_console.print(f"sim UI at {page.url} (same session)", markup=False, highlight=False)

    def on_ready() -> None:
        if page is not None and open_browser:
            import webbrowser

            webbrowser.open(page.url)

    def close() -> None:
        if page is not None:
            page.stop()
        try:
            if trace_out is not None:
                session.write_trace(trace_out)
        finally:
            session.close()  # on linux: every line inactive and released

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
    except SystemExit as stop:
        # SIGTERM / SIGHUP (`_exit_on_signals`): drop the lines, then leave at once —
        # the SDK's stdin thread is not a daemon and would hold the exit (as above).
        # The exit happens even when the cleanup raises.
        try:
            close()
        finally:
            sys.stderr.flush()
            os._exit(stop.code if isinstance(stop.code, int) else 1)
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


@mcp_app.command(name="desktop-config", epilog=epilog("mcp desktop-config"))
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


def _verify_tool_corpus() -> tuple[int, int]:
    """The Gated Tool Profile corpus (docs/spec/tool_calling.md §9): (problems, cases run)."""
    from ..testing.tool_corpus import corpus_dir, run_corpus

    console.print("\n[bold]Running the tool-call corpus in fixtures/tool_calls/ on sim[/bold]")
    if not corpus_dir().is_dir():
        return 0, 0  # zero cases: verify's count check reports it (NE4004)
    try:
        outcomes, closure = run_corpus()
    except NeuroEdgeError as error:
        err_console.print(f"  [red]✗[/red] [{error.code}] {escape(error.why)}")
        return 1, 0
    for problem in closure:
        err_console.print(f"  [red]✗[/red] {escape(problem)}")
    failed = [outcome for outcome in outcomes if not outcome.ok]
    for outcome in failed:
        for difference in outcome.differences:
            err_console.print(f"  [red]✗[/red] {outcome.case.name}: {escape(difference)}")
    valid = sum(outcome.case.kind == "valid" for outcome in outcomes)
    if not failed and not closure:
        console.print(
            f"  [green]✓[/green] {len(outcomes)} tool calls ({valid} valid, "
            f"{len(outcomes) - valid} invalid) give the recorded result"
        )
    return len(failed) + len(closure), len(outcomes)


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


@app.command(epilog=epilog("verify"))
def verify(
    targets: str = typer.Option(
        "sim", "--targets", help="Comma-separated targets to replay on: sim, linux, esp32s3"
    ),
    port: str = typer.Option(
        None,
        "--port",
        help=(
            "esp32s3: the device's UART, where the firmware replays the canonical traces at "
            "boot — a log file (QEMU -serial file:…), tcp://host:port or /dev/ttyACM0"
        ),
    ),
    baud: int = typer.Option(921600, "--baud", help="Serial baud rate for --port"),
    timeout: float = typer.Option(
        30.0, "--timeout", help="Seconds to wait for NE_TRACE DONE on a live --port"
    ),
):
    """
    Verify the frozen artifacts and target equivalence (A2).

    Every gate resolves, every canonical trace validates, every case of the
    Gated Tool Profile corpus (fixtures/tool_calls/) gives its recorded result,
    and every canonical trace replays on each requested target to the decisions
    it records — verdict sequence and pin commands (FR-CI-07). `linux` needs GPIO lines:
    a board, or `scripts/setup_gpio_sim.sh`. `esp32s3` replays on the device itself and
    needs `--port` (docs/spec/simulation_coverage.md §4).
    """
    from ..testing.golden import GoldenComparator
    from ..testing.player import TracePlayer
    from ..testing.tool_corpus import corpus_dir as tool_corpus_dir
    from ..testing.uart import read_sessions

    root = repo_root()
    gates_root = gates_dir()
    traces_root = root / "fixtures" / "traces"
    requested = [t.strip() for t in targets.split(",") if t.strip()]
    device = None
    if "esp32s3" in requested:
        if port is None:
            _fail(
                NeuroEdgeError(
                    where=f"neuroedge verify --targets {targets}",
                    why=(
                        "on esp32s3 the device replays the canonical traces itself; "
                        "the host reads the sessions it writes on its UART"
                    ),
                    how=(
                        "boot the firmware and pass --port: build/uart.log (QEMU "
                        "-serial file:), tcp://localhost:5555 (QEMU -serial tcp::5555,server), "
                        "or /dev/ttyACM0 (board)"
                    ),
                )
            )
            return
        try:
            device = read_sessions(port, baud=baud, timeout_s=timeout)
        except NeuroEdgeError as error:
            _fail(error)
            return
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

    corpus_problems, tool_calls = _verify_tool_corpus()
    problems += corpus_problems

    console.print(f"\n[bold]Replaying canonical traces on {', '.join(requested)}[/bold]")
    table = Table()
    table.add_column("Trace", style="cyan")
    for target in requested:
        table.add_column(target, justify="center")
    rows: dict[str, list[str]] = {path.name: [] for path in valid}
    for target in requested:
        for path in valid:
            try:
                if target == "esp32s3":
                    result = _device_replay(device, path, port)
                    verdicts = [
                        e["data"]["verdict"]
                        for e in result["events"]
                        if e["type"] == "gate_evaluation_result"
                    ]
                else:
                    if target == "linux":
                        _exit_on_signals()  # the replay drives real lines
                    result = asyncio.run(TracePlayer(path, target=target).replay())
                    verdicts = result.verdicts
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
                rows[path.name].append(f"[green]✓[/green] {' '.join(verdicts)}")
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
            "tool calls compared": (
                tool_calls,
                tool_corpus_dir(),
                "has no tool-call case with a recorded result",
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

    on_device = ""
    if device is not None:
        ids = ", ".join(sorted({s.info["device_id"] for s in device if s.replay_of}))
        on_device = (
            f"\n\n[yellow]esp32s3 (device {escape(ids)}):[/yellow] the verdicts, and whether "
            "and which pin is driven, are computed on the device (C walker + token ledger); "
            "operation and duration come from the action table built on the host — no HAL "
            "yet (TSK-S4-01)."
        )
    console.print(
        Panel(
            f"[green]Passed:[/green] all {resolved} gate(s) resolve, all {len(valid)} "
            "canonical trace(s) validate, every tool call of the corpus gives its recorded "
            f"result, and {replayed} replay(s) on {', '.join(requested)} match the verdicts "
            "and pin commands they record."
            f"{on_device}\n\n"
            "[yellow]Compared:[/yellow] decisions only — not timing. Timing equivalence "
            "arrives with TSK-S4-04.",
            title="neuroedge verify",
            border_style="green",
        )
    )


def _device_replay(sessions, path: Path, port: str) -> dict[str, Any]:
    """
    The session in which the device replayed the canonical trace `path`, as a trace.
    Refused, never compared, when the firmware replays an older trace or gate than
    this checkout holds: that would be a pass (or a failure) about something else.
    """
    from ..engine.canonical import digest
    from ..engine.compiler import load_agent_manifest, resolve_gates
    from ..engine.decision_tree import compile_tree
    from ..errors import ReplayError
    from ..paths import fixtures_dir

    stale = "the firmware is stale: python/.venv/bin/python scripts/gen_firmware_vectors.py, "
    stale += "then build and flash again (QEMU: firmware-qemu.yml)"
    matches = [s for s in sessions if s.replay_of == path.name]
    if not matches:
        raise ReplayError(
            where=port,
            why=f"the device wrote no session replaying {path.name}",
            how="flash a firmware with CONFIG_NEUROEDGE_REPLAY_VECTORS and main/vectors/ for "
            "the canonical traces, and capture from boot to NE_TRACE DONE",
        )
    session = matches[-1]
    golden = load_trace(path)
    if session.info.get("trace_digest") != digest(golden):
        raise ReplayError(
            where=f"{port}:{session.line}",
            why=f"the device replays {path.name} as {session.info.get('trace_digest')}, "
            f"this checkout holds {digest(golden)}",
            how=stale,
        )
    trace = session.trace()
    agent = fixtures_dir() / "agents" / session.info["agent_version"].partition("@")[0]
    gates, problems = resolve_gates(load_agent_manifest(agent / "agent.toml"), None)
    if problems:
        raise problems[0]
    digests = {tree["gate"]: tree["gate_digest"] for tree in map(compile_tree, gates.values())}
    for event in trace["events"]:
        data = event["data"]
        if event["type"] == "gate_evaluation_begin" and digests.get(data["gate"]) != data.get(
            "gate_digest"
        ):
            raise ReplayError(
                where=f"{port}: {path.name} {data['gate']}",
                why=f"the device decides {data['gate']} as {data.get('gate_digest')}, "
                f"this checkout compiles it to {digests.get(data['gate'])}",
                how=stale,
            )
    return trace


@app.command(epilog=epilog("replay"))
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
    trace itself), 1 on any difference (FR-CI-02, FR-CI-04), 2 on a target that
    has no replay yet (esp32s3).
    """
    from ..testing.golden import GoldenComparator, load_golden
    from ..testing.player import TracePlayer, dump

    if target in PLANNED_TARGETS:
        _not_implemented_target("replay", target)
    if target == "linux":
        _exit_on_signals()  # the replay drives real lines
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


@app.command(epilog=epilog("new"))
def new(
    name: str = typer.Argument(..., help="Name of the new agent project (and its directory)"),
    template: str = typer.Option(
        "minimal",
        "--template",
        help="minimal (1 action, 1 gate, tests), villa-concierge, home-voice or factory-monitor",
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


def _exit_on_signals() -> None:
    """
    SIGTERM and SIGHUP end the process through `SystemExit`, so the session's
    `finally: session.close()` runs and every line drops inactive. Python's default
    for both ends the process at once: a door-lock pulse in flight, or a line left
    `on`, would stay driven after the process is gone (an MCP host stops its server
    with SIGTERM; closing the terminal sends SIGHUP). SIGKILL cannot be caught.
    """
    import signal

    names = [name for name in ("SIGTERM", "SIGHUP") if hasattr(signal, name)]

    def _exit(signum: int, _frame: Any) -> None:
        # A second signal must not cut the cleanup short between two lines.
        for name in names:
            signal.signal(getattr(signal, name), signal.SIG_IGN)
        raise SystemExit(128 + signum)

    for name in names:
        signal.signal(getattr(signal, name), _exit)


def _start_session(
    verb: str, agent, target: str, board: str | None, registry, events=None, ui: bool = False
):
    """
    Load the agent for an interactive session on `sim` or `linux`, or exit with the
    right code: 2 for a target (or `--ui` on it) with no session yet, 1 when the agent
    does not fit the board or `linux` cannot run (no `gpiod`, no GPIO chip — Q-16).
    """
    from ..sim import SimSession

    if target not in SUPPORTED_TARGETS:
        _fail(
            BoardCapabilityError(
                where=f"--target {target}",
                why=f"{target!r} is not a target; the targets are {', '.join(SUPPORTED_TARGETS)}",
                how="pass --target sim or --target linux: interactive sessions run on those",
            )
        )
    if target in PLANNED_SESSIONS:
        err_console.print(
            Panel(
                f"`neuroedge {verb} --target {escape(target)}` is not implemented yet "
                f"({PLANNED_SESSIONS[target]}).\n\n"
                "Interactive sessions run on `sim` and `linux` today.",
                title=f"[yellow]Not implemented: {verb} --target {escape(target)}[/yellow]",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=2)
    if ui and target != "sim":
        err_console.print(
            Panel(
                f"`neuroedge {verb} --ui --target {escape(target)}` is not implemented: the "
                "live page shows the simulator's virtual devices.\n\n"
                f"On `{escape(target)}` the session runs in the terminal: drop --ui.",
                title=f"[yellow]Not implemented: {verb} --ui --target {escape(target)}[/yellow]",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=2)
    if target == "linux":
        _exit_on_signals()  # before the lines are requested
    try:
        return SimSession.load(
            agent or _default_agent(),
            target=target,
            board_id=board,  # None: the target's reference board
            registry=GateRegistry(registry) if registry is not None else None,
            events=events,
        )
    except BuildFailed as failed:
        _fail_build(failed)
    except NeuroEdgeError as error:
        _fail(error)
    raise AssertionError("unreachable")  # _fail* always exit


@app.command(epilog=epilog("run"))
def run(
    agent: Path = typer.Option(
        None,
        "--agent",
        "-a",
        help="Path to agent.toml (default: ./agent.toml, else the villa-concierge sample)",
    ),
    target: str = typer.Option(
        "sim", "--target", "-t", help="Target to run on: sim, or linux (real GPIO lines)"
    ),
    board: str = typer.Option(
        None, "--board", "-b", help="Board profile id (default: the target's reference board)"
    ),
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
    Run the agent: type a command, see the gate verdict and the pins.
    With --ui (sim only) the same session is shown live in the browser.

    Input is typed text matched by the agent's commands.toml — no network, no
    key (Q-15). The agent is build-checked against the board first. On `linux`
    the pins are real GPIO lines (the `linux` extra; a board, or
    scripts/setup_gpio_sim.sh) and the agent may need `digital.out` only.
    """
    from .run import run_session

    session = _start_session("run", agent, target, board, registry, ui=ui)
    if ui:
        from ..sim.ui import serve

        try:
            serve(session, port, console, open_browser=not no_browser)
        except NeuroEdgeError as error:
            _fail(error)  # e.g. the port is taken
        finally:
            if trace_out is not None:
                session.write_trace(trace_out)
        return
    code = run_session(session, console, err_console, command=command, trace_out=trace_out)
    raise typer.Exit(code=code)


@app.command(epilog=epilog("build"))
def build(
    target: str = typer.Option(..., "--target", "-t", help="Target runtime environment"),
    board: str = typer.Option(
        None,
        "--board",
        "-b",
        help="Board profile id (default: the target's reference board, e.g. sim → sim-default)",
    ),
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
            board_id=board or REFERENCE_BOARD.get(target, "esp32s3-box-3"),
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


@app.command(epilog=epilog("test"))
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


@app.command(epilog=epilog("record"))
def record(
    agent: Path = typer.Option(
        None, "--agent", "-a", help="Path to agent.toml (default as for `run`)"
    ),
    target: str = typer.Option(
        "sim",
        "--target",
        "-t",
        help="Target to record on: sim, linux (real GPIO lines), or esp32s3 with --port",
    ),
    board: str = typer.Option(
        None, "--board", "-b", help="Board profile id (default: the target's reference board)"
    ),
    out: Path = typer.Option(Path("traces"), "--out", "-o", help="Directory, or a .json path"),
    command: str = typer.Option(None, "--command", "-c", help="Record one typed command and exit"),
    anonymize: bool = typer.Option(
        False, "--anonymize", help="Hash raw text at the source (FR-TRC-07); verdicts unchanged"
    ),
    port: str = typer.Option(
        None,
        "--port",
        help=(
            "esp32s3 only — where the device's UART is: a log file (QEMU -serial file:…), "
            "tcp://host:port (QEMU -serial tcp::5555,server) or a serial device such as "
            "/dev/ttyACM0 (needs neuroedge\\[serial]). Not the UI port of `run`."
        ),
    ),
    baud: int = typer.Option(
        921600,
        "--baud",
        help="Serial baud rate (PRD Appendix D.2); ignored for files, tcp, USB-CDC",
    ),
    timeout: float = typer.Option(
        30.0, "--timeout", help="Seconds to wait for NE_TRACE DONE on a live port"
    ),
    registry: Path | None = REGISTRY_OPTION,
):
    """
    Record a session to a trace file that `trace validate` and `replay` accept.

    Same session as `run`, on `sim` or `linux`; on exit the trace is validated
    against trace.v1 and written to `--out` (default `traces/<session_id>.json`).
    A trace recorded on `linux` replays on `sim` to the same decisions.

    With `--target esp32s3 --port`, the device records: every `NE1` session it
    writes on its UART becomes one trace file, validated before it is written
    (docs/spec/simulation_coverage.md §4, TSK-S4-09).
    """
    if target == "esp32s3" or port is not None:
        _record_from_device(target, port, baud, timeout, out, anonymize, board, agent, command)
        return
    from ..testing.recorder import TraceRecorder
    from .run import run_session

    recorder = TraceRecorder(anonymize=anonymize)
    session = _start_session(
        "record",
        agent,
        target,
        board or REFERENCE_BOARD.get(target, "sim-default"),
        registry,
        events=recorder,
    )
    path = out if out.suffix == ".json" else out / f"{recorder.session_id}.json"
    code = run_session(session, console, err_console, command=command, trace_out=path)
    raise typer.Exit(code=code)


def _record_from_device(target, port, baud, timeout, out, anonymize, board, agent, command) -> None:
    """`record --target esp32s3 --port`: the device's sessions, one trace file each."""
    from ..testing.uart import read_sessions

    usage = None
    if target != "esp32s3":
        usage = (f"--target {target}", "--port reads a device's UART, and only esp32s3 has one")
    elif port is None:
        usage = (
            "--target esp32s3",
            "the device records the session and the host only reads its UART: --port is needed",
        )
    elif agent is not None or command is not None:
        usage = (
            "--agent / --command",
            "an esp32s3 session is the firmware's: the agent and what runs are on the device",
        )
    if usage is not None:
        _fail(
            NeuroEdgeError(
                where=f"neuroedge record {usage[0]}",
                why=usage[1],
                how=(
                    "neuroedge record --target esp32s3 --port build/uart.log (QEMU), "
                    "tcp://localhost:5555, or /dev/ttyACM0 (board)"
                ),
            )
        )
        return
    try:
        sessions = read_sessions(port, baud=baud, timeout_s=timeout)
    except NeuroEdgeError as error:
        _fail(error)
        return
    other = [s for s in sessions if board is not None and s.info["board_id"] != board]
    if other:
        _fail(
            NeuroEdgeError(
                where=f"{port}:{other[0].line}",
                why=f"the device says board {other[0].info['board_id']!r}, --board says {board!r}",
                how="drop --board (the device declares its board), or flash the right image",
            )
        )
        return
    single = out.suffix == ".json"
    if single and len(sessions) != 1:
        _fail(
            NeuroEdgeError(
                where=str(out),
                why=f"the device wrote {len(sessions)} sessions, and a .json path holds one",
                how="pass a directory to --out: each session becomes <session_id>.json",
            )
        )
        return
    for session in sessions:
        path = out if single else out / f"{session.session_id}.json"
        try:
            session.recorder(anonymize=anonymize).save(path)
        except NeuroEdgeError as error:
            _fail(error)
            return
        evaluations = sum(1 for e in session.events if e["type"] == "gate_evaluation_result")
        what = session.replay_of or session.info["agent_version"]
        console.print(
            f"[green]✓[/green] {escape(str(path))} — {evaluations} gate evaluation(s), "
            f"{escape(what)}, device {escape(session.info['device_id'])}"
        )
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
