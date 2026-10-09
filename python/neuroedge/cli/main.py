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
from ..engine.gate_resolver import lint_registry
from ..errors import BoardCapabilityError, BuildFailed, NeuroEdgeError, VerificationError
from ..hal.board import (
    ALL_PRIMITIVES,
    PRIMITIVES,
    REFERENCE_BOARD,
    REFERENCE_BOARDS,
    SUPPORTED_TARGETS,
    available_boards,
    load_board_by_id,
)
from ..paths import fixtures_dir, gates_dir, repo_root
from ..sim.serve import MCP_INIT_TIMEOUT_S
from ..sim.serve import exit_on_signals as _exit_on_signals
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
add_app = typer.Typer(
    name="add",
    help="Add an action, gate and two-way test to an agent project",
    epilog=epilog("add"),
)

guard_app = typer.Typer(
    name="guard",
    help="Put a safety Guard in front of an existing tool server",
    epilog=epilog("guard"),
)
proxy_app = typer.Typer(
    name="proxy",
    help="Serve an existing MCP server's tools through a Guard (gate, token, trace)",
    epilog=epilog("proxy"),
)
plugin_app = typer.Typer(
    name="plugin", help="Check the extensions and the Guard around them", epilog=epilog("plugin")
)

app.add_typer(gate_app, name="gate")
app.add_typer(trace_app, name="trace")
app.add_typer(board_app, name="board")
app.add_typer(mcp_app, name="mcp")
app.add_typer(add_app, name="add")
app.add_typer(guard_app, name="guard")
app.add_typer(proxy_app, name="proxy")
app.add_typer(plugin_app, name="plugin")

console = Console()
err_console = Console(stderr=True)


def _fail(error: NeuroEdgeError, code: int = 1) -> None:
    """Render a three-part diagnostic to stderr and exit non-zero."""
    err_console.print(f"[bold red]✗ {error.code}[/bold red] [cyan]{escape(error.where)}[/cyan]")
    err_console.print(f"  [bold]why:[/bold] {escape(error.why)}")
    if isinstance(getattr(error, "principle", None), int):
        err_console.print(f"  [bold]rule:[/bold] Proposal Appendix B.5 principle {error.principle}")
    err_console.print(f"  [bold]fix:[/bold] {escape(error.how)}")
    raise typer.Exit(code=code)


def _warn_raw() -> None:
    """One stderr line whenever `--raw` writes a trace: the file keeps the user's words."""
    err_console.print(
        "warning: --raw keeps the user's words in the trace file as plain text "
        "(metadata.anonymized = false)",
        markup=False,
        highlight=False,
    )


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

    gate_registry = lint_registry(root, registry)

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
    _print_turn_summary(trace)


def _print_turn_summary(trace: dict[str, Any]) -> None:
    """Turns per System 1 / System 2 path and stage latency (TSK-I4-03), when timed."""
    from ..engine.latency import turn_summary

    # Recomputed from the `turn_latency` events, not read from `session_summary`.
    summary = turn_summary(trace["events"])
    if summary is None:
        return
    paths = " · ".join(
        f"{path} {count} ({summary['shares'][path]:.0%})"
        for path, count in summary["paths"].items()
    )
    console.print(f"[bold]{summary['turns']} turn(s):[/bold] {escape(paths)}")
    stages = " · ".join(
        f"{name} {value['sum']:g}/{value['max']:g}" for name, value in summary["stages_ms"].items()
    )
    console.print(f"stage ms (sum/max): {escape(stages)}")


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
    """Show one board's declared capabilities: the five core primitives and the extensions it has."""
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
    for primitive in ALL_PRIMITIVES:
        if board.supports(primitive):
            table.add_row(primitive, json.dumps(board.capability(primitive), ensure_ascii=False))
        elif primitive in PRIMITIVES:  # an extension a board lacks is not an omission
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
        None, "--trace-out", help="Write the session trace here on exit (text hashed by default)"
    ),
    raw: bool = typer.Option(
        False, "--raw", help="With --trace-out: keep the user's words in the trace as plain text"
    ),
    registry: Path | None = REGISTRY_OPTION,
    ui: bool = typer.Option(
        False, "--ui", help="Also serve this session as the live sim page on 127.0.0.1"
    ),
    port: int | None = typer.Option(
        None,
        "--port",
        help="Port for --ui (default 8765) or for --http (default 8443); 0 picks a free one",
    ),
    open_browser: bool = typer.Option(
        False, "--open", help="With --ui, open the page in a browser"
    ),
    init_timeout: float = typer.Option(
        MCP_INIT_TIMEOUT_S,
        "--init-timeout",
        help="Exit if no client sends `initialize` within this many seconds (stdio only; 0: wait forever)",
    ),
    http: bool = typer.Option(
        False,
        "--http",
        help="Serve over the network (Streamable HTTP, mTLS, OAuth 2.1 tokens) instead of stdio; "
        "needs every flag below",
    ),
    host: str | None = typer.Option(
        None, "--host", help="With --http, the address to listen on (default 127.0.0.1)"
    ),
    tls_cert: Path | None = typer.Option(
        None, "--tls-cert", help="With --http: the server certificate (PEM)"
    ),
    tls_key: Path | None = typer.Option(
        None, "--tls-key", help="With --http: the server certificate's private key (PEM)"
    ),
    client_ca: Path | None = typer.Option(
        None, "--client-ca", help="With --http: the CA of the devices' client certificates (mTLS)"
    ),
    issuer: str | None = typer.Option(
        None, "--issuer", help="With --http: the OAuth authorization server's issuer URL (https)"
    ),
    audience: str | None = typer.Option(
        None,
        "--audience",
        help="With --http: this server's MCP URL, the audience of every token (https)",
    ),
    jwks: Path | None = typer.Option(
        None, "--jwks", help="With --http: the issuer's public signing keys (JWKS file)"
    ),
    required_scope: str | None = typer.Option(
        None,
        "--required-scope",
        help="With --http: the scope a token must carry (default neuroedge:call)",
    ),
):
    """
    Serve the agent as a gated MCP server over stdio: every @action is a tool,
    and every tools/call goes through the tool schema, c.do() and the gate.
    On `--target linux` a tool call drives real GPIO lines (as `run --target linux`).
    With --ui (sim only) the same session is shown live in the browser: a tool call from
    the MCP client moves the virtual devices on the page at once. The page never
    takes the MCP server down: a taken port falls back to a free one (URL on stderr).

    With --http the server listens on the network instead: Streamable HTTP over mTLS
    (TLS 1.3, a client certificate required), and every request carries a per-device
    OAuth 2.1 bearer token bound to that certificate. Without every one of --tls-cert,
    --tls-key, --client-ca, --issuer, --audience and --jwks it does not start. The gate,
    the verdict token and the trace are the stdio server's, unchanged.
    """
    from ..mcp_server import _sdk
    from ..sim.serve import run_http, run_stdio

    try:
        _sdk()
    except NeuroEdgeError as error:
        _fail(error)
        return
    network = {
        "--host": host,
        "--tls-cert": tls_cert,
        "--tls-key": tls_key,
        "--client-ca": client_ca,
        "--issuer": issuer,
        "--audience": audience,
        "--jwks": jwks,
        "--required-scope": required_scope,
    }
    if http and ui:
        _fail(
            NeuroEdgeError(
                where="neuroedge mcp serve --http --ui",
                why="the live page and the network door are not combined: the page answers `ask` "
                "questions as the person on the device, and shares the session",
                how="drop --ui for the network server, or --http for the page (stdio)",
            ),
            code=2,
        )
        return
    if not http and any(value is not None for value in network.values()):
        given = ", ".join(flag for flag, value in network.items() if value is not None)
        _fail(
            NeuroEdgeError(
                where=f"neuroedge mcp serve {given}",
                why="those flags configure the network transport, which is off unless --http is given",
                how="add --http (with every flag it needs), or drop them to serve over stdio",
            )
        )
        return
    prepared = None
    if http:
        from ..mcp_http import DEFAULT_PORT, DEFAULT_SCOPE, HttpConfig, prepare

        try:  # before the session is wired and before any socket exists
            prepared = prepare(
                HttpConfig(
                    host=host or "127.0.0.1",
                    port=DEFAULT_PORT if port is None else port,
                    tls_cert=tls_cert,
                    tls_key=tls_key,
                    client_ca=client_ca,
                    issuer=issuer,
                    audience=audience,
                    jwks=jwks,
                    required_scope=required_scope or DEFAULT_SCOPE,
                )
            )
        except NeuroEdgeError as error:
            _fail(error)
            return
    if trace_out is not None and target != "linux" and not http:
        # SIGTERM / SIGHUP must still write the trace and close the HAL (TSK-N2-03): the host
        # that stops a server sends SIGTERM. `linux` installs the handlers in `_start_session`;
        # the network server (--http) listens for both signals itself and closes the same way.
        _exit_on_signals()
    session = _start_session(
        "mcp serve",
        agent,
        target,
        board,
        registry,
        events=_trace_log(trace_out, raw),
        ui=ui,
    )
    page = _mcp_page(session, 8765 if port is None else port) if ui else None
    # stdout is the protocol channel; anything for people goes to stderr.
    err_console.print(
        f"neuroedge MCP server · {escape(session.manifest.label)} · "
        f"{escape(session.target)}/{escape(session.hal.board.id)} · "
        f"{len(session.tools.specs)} tool(s) · {'https (mTLS)' if http else 'stdio'}"
    )
    warning = session.canned_fact_warning()
    if warning is not None:
        err_console.print(f"[yellow]! {escape(warning)}[/yellow]")
    if prepared is not None:

        def listening(bound_host: str, bound_port: int) -> None:
            err_console.print(
                f"listening on {bound_host}:{bound_port}{prepared.path} — "
                "mTLS, OAuth 2.1 bearer tokens; refused attempts are traced as mcp_auth_refused",
                markup=False,
                highlight=False,
            )

        try:
            run_http(session, prepared, trace_out=trace_out, on_ready=listening)
        except NeuroEdgeError as error:
            _fail(error)
        return
    if page is not None:
        err_console.print(f"sim UI at {page.url} (same session)", markup=False, highlight=False)

    def on_ready() -> None:
        if page is not None and open_browser:
            import webbrowser

            webbrowser.open(page.url)

    run_stdio(
        session,
        trace_out=trace_out,
        init_timeout=init_timeout,
        lock=page.lock if page is not None else None,
        on_change=page.notify if page is not None else None,
        on_ready=on_ready,
        on_close=page.stop if page is not None else None,
    )


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
    raw: bool = typer.Option(
        False, "--raw", help="With --trace-out: have the server keep the user's words in the trace"
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
    from ..mcp_desktop import (
        default_config_path,
        desktop_config_text,
        desktop_entry,
        write_entry,
    )

    agent_path = (agent or _default_agent()).expanduser().resolve()
    try:
        entry = desktop_entry(agent_path, ui=ui, port=port, trace_out=trace_out, raw=raw)
    except NeuroEdgeError as error:
        _fail(error)
        return
    session = _start_session("mcp desktop-config", agent_path, "sim", "sim-default", None)
    key = name or session.manifest.name
    if raw and trace_out is not None:
        _warn_raw()
    if "env" in entry:
        typer.echo(
            "note: this interpreter does not import this neuroedge on its own; "
            f"env.PYTHONPATH pins {entry['env']['PYTHONPATH']}",
            err=True,
        )
    if not write:
        # Plain stdout, not rich: the output is meant to be pasted or piped.
        typer.echo(desktop_config_text(key, entry))
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


@guard_app.command(name="init", epilog=epilog("guard init"))
def guard_init(
    mcp: str = typer.Option(
        None,
        "--mcp",
        help='An MCP server to put behind a Guard: a command ("python server.py") or an https URL',
    ),
    http: str = typer.Option(
        None,
        "--http",
        help="A local HTTP API to put behind a Guard: its base URL (http only on loopback)",
    ),
    route: list[str] = typer.Option(
        [], "--route", help='With --http: a route to expose, "METHOD /path/{param}" (repeatable)'
    ),
    directory: Path = typer.Option(
        Path("."), "--dir", help="Where to write guard.toml and gates/ (default: here)"
    ),
    name: str = typer.Option(None, "--name", help="Name of the guard (default: from the server)"),
    env_from: list[str] = typer.Option(
        [],
        "--env-from",
        help="With --mcp: environment variable the server's process needs (name only)",
    ),
    header_env: list[str] = typer.Option(
        [],
        "--header-env",
        help="HEADER=ENVVAR: send the value of ENVVAR as that header (e.g. Authorization=HA_TOKEN)",
    ),
    allow_lan_http: bool = typer.Option(
        False,
        "--allow-lan-http",
        help="Accept plain http to a home-LAN host (private IP, *.local, *.lan, *.home.arpa) and "
        "write allow_lan_http = true: calls and the token then travel in clear on the LAN",
    ),
):
    """
    Put an existing server behind a Guard: write guard.toml and one gate per tool or route.
    With --mcp, connect to the MCP server and list its tools; with --http, expose the routes you
    name. Every generated gate BLOCKS until you edit it on purpose. Never overwrites a file.
    Then: `neuroedge proxy mcp` or `neuroedge proxy http`.
    """
    if (mcp is None) == (http is None):
        _fail(
            NeuroEdgeError(
                where="neuroedge guard init",
                why="give exactly one of --mcp and --http",
                how='--mcp "python server.py" for an MCP server, --http http://127.0.0.1:8080 '
                '--route "POST /path" for an HTTP API',
            ),
            code=2,
        )
        return
    if (http is None and route) or (http is not None and not route):
        _fail(
            NeuroEdgeError(
                where="neuroedge guard init",
                why="--route belongs to --http (and --http needs at least one --route)",
                how='add --route "POST /cm/{cmd}" with --http, or drop --route with --mcp',
            ),
            code=2,
        )
        return
    try:
        if http is not None:
            from ..proxy_http import init as init_http

            plan = init_http(http, route, directory, name, header_env, allow_lan_http)
            nxt = "proxy http"
        else:
            from ..proxy_mcp import init

            plan = asyncio.run(init(mcp, directory, name, env_from, header_env, allow_lan_http))
            nxt = "proxy mcp"
    except NeuroEdgeError as error:
        _fail(error)
        return
    base = directory.resolve()
    for path in plan.files:
        typer.echo(f"wrote {path}")
    typer.echo(
        f"{len(plan.exposed)} tool(s) behind the Guard, all BLOCKED until you open their gate:"
    )
    for tool in plan.exposed:
        typer.echo(f"  {tool}")
    for tool, why in plan.not_exposed.items():
        typer.echo(f"NOT exposed: {tool} — {why}", err=True)
    for tool, dropped in plan.dropped.items():
        typer.echo(
            f"note: {tool}: optional parameter(s) not exposed: {', '.join(dropped)}", err=True
        )
    typer.echo("Next: edit gates/*.yaml to open what you mean to, then")
    typer.echo(f"  neuroedge {nxt} --config {base / 'guard.toml'}")


@proxy_app.command(name="http", epilog=epilog("proxy http"))
def proxy_http(
    config: Path = typer.Option(
        Path("guard.toml"), "--config", "-c", help="guard.toml with a \\[proxy.http] table"
    ),
    trace_out: Path = typer.Option(
        None, "--trace-out", help="Write the Guard's trace here on exit"
    ),
):
    """
    Serve, on loopback only, the routes declared in guard.toml: each is forwarded to the real HTTP
    API only if the gate allows it (the source is `bridge:<id>`, default `bridge:http`; a gate must
    list it). Anything undeclared gets a 404 and is never forwarded. Runs until Ctrl-C or SIGTERM,
    then writes the trace. Refuses to start when the real API cannot be reached.
    """
    from ..proxy_http import serve

    def ready(guard: Any, proxy: Any, port: int) -> None:
        err_console.print(
            f"neuroedge HTTP proxy · {escape(guard.config.name)} · {len(proxy.routes)} route(s) · "
            f"http://{proxy.host}:{port} → {escape(proxy.upstream)} (forwarded only after ALLOW; "
            f"source {escape(proxy.source)})",
        )

    try:
        asyncio.run(serve(config, trace_out=trace_out, on_ready=ready))
    except NeuroEdgeError as error:
        _fail(error)


@proxy_app.command(name="mcp", epilog=epilog("proxy mcp"))
def proxy_mcp(
    config: Path = typer.Option(
        Path("guard.toml"), "--config", "-c", help="guard.toml with a \\[proxy.mcp] table"
    ),
    trace_out: Path = typer.Option(
        None, "--trace-out", help="Write the Guard's trace here on exit"
    ),
    desktop_config: bool = typer.Option(
        False,
        "--desktop-config",
        help="Print the Claude Desktop mcpServers entry for this proxy instead of serving",
    ),
    write: bool = typer.Option(
        False,
        "--write",
        help="With --desktop-config: write the entry into Desktop's config (with a backup)",
    ),
    config_path: Path = typer.Option(
        None, "--config-path", help="Config file for --write (default: Claude Desktop's)"
    ),
    name: str = typer.Option(
        None, "--name", help="Key under mcpServers (default: the guard's name)"
    ),
):
    """
    Serve over stdio the tools of guard.toml, each forwarded to the real MCP server only if the
    gate allows the call (stdio only; a network front arrives with `proxy http`). It refuses to
    start when the real server cannot be reached or lacks a tool guard.toml declares.
    """
    from ..guard import load_config
    from ..mcp_server import _sdk
    from ..proxy_mcp import parse_upstream, serve

    try:
        _sdk()
        loaded = load_config(config)
        up = parse_upstream(loaded)
    except NeuroEdgeError as error:
        _fail(error)
        return
    if write and not desktop_config:
        _fail(
            NeuroEdgeError(
                where="neuroedge proxy mcp --write",
                why="--write belongs to --desktop-config",
                how="add --desktop-config",
            ),
            code=2,
        )
        return
    if desktop_config:
        from ..mcp_desktop import default_config_path, desktop_config_text, proxy_entry, write_entry

        entry = proxy_entry(config.expanduser(), trace_out=trace_out)
        key = name or loaded.name
        if up.env_from or up.headers_env:
            needed = sorted({*up.env_from, *up.headers_env.values()})
            typer.echo(
                f"note: Claude Desktop starts the proxy with a minimal environment: add {needed} "
                'to this entry\'s "env" yourself (they are not written here, to keep secrets out '
                "of files)",
                err=True,
            )
        if not write:
            typer.echo(desktop_config_text(key, entry))
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
        return
    _exit_on_signals()  # SIGTERM still writes the trace and closes the Guard

    def ready(guard: Any) -> None:
        err_console.print(
            f"neuroedge MCP proxy · {escape(loaded.name)} · {len(loaded.tools)} tool(s) · stdio "
            "→ upstream (forwarded only after ALLOW)",
        )

    try:
        asyncio.run(serve(config, trace_out=trace_out, on_ready=ready))
    except NeuroEdgeError as error:
        _fail(error)


@plugin_app.command(name="doctor", epilog=epilog("plugin doctor"))
def plugin_doctor(
    config: Path = typer.Option(
        Path("guard.toml"), "--config", "-c", help="guard.toml with a \\[proxy.mcp] table"
    ),
    as_json: bool = typer.Option(False, "--json", help="Machine-readable findings"),
):
    """
    Check what can be checked about "the proxy is the only road": the real server still reachable
    around it, another client entry that still launches it, a gate that never reads call_source.
    What it cannot check it says so. Exit 1 if there is any warning, 0 otherwise.
    """
    from ..proxy_mcp import doctor

    try:
        findings = doctor(config)
    except NeuroEdgeError as error:
        _fail(error)
        return
    warnings = [f for f in findings if f.level == "warning"]
    if as_json:
        typer.echo(
            json.dumps(
                {"warnings": len(warnings), "findings": [f.as_dict() for f in findings]},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for finding in findings:
            mark = {"warning": "CẢNH BÁO", "info": "ghi chú", "unverifiable": "?"}[finding.level]
            typer.echo(f"[{mark}] {finding.message}")
        typer.echo(
            f"{len(warnings)} cảnh báo. Doctor không chứng minh proxy là đường duy nhất: "
            "nó chỉ báo những lối vòng nó thấy."
        )
    if warnings:
        raise typer.Exit(code=1)


@plugin_app.command(name="list", epilog=epilog("plugin list"))
def plugin_list(
    as_json: bool = typer.Option(False, "--json", help="Machine-readable listing"),
):
    """
    Every installed NeuroEdge plugin entry point — kind, name, distribution, version — read from
    the package metadata without importing anything. Installed is not enabled: only
    \\[plugins] enable in agent.toml or guard.toml loads one (RFC-0016 §3d).
    """
    from ..plugins import discover

    found = discover()
    if as_json:
        typer.echo(
            json.dumps(
                [
                    {
                        "kind": e.kind,
                        "name": e.name,
                        "distribution": e.distribution,
                        "version": e.version,
                        "value": e.value,
                    }
                    for e in found
                ],
                indent=2,
            )
        )
        return
    for entry in found:
        typer.echo(f"{entry.kind:12} {entry.name:32} {entry.distribution} {entry.version}")
    typer.echo(
        f"{len(found)} entry point(s) installed; none runs unless [plugins] enable names its "
        "distribution."
    )


@app.command(epilog=epilog("conformance"))
def conformance(
    distribution: str = typer.Argument(..., help="The distribution to check (its PyPI name)"),
    kind: str = typer.Option(None, "--kind", help="Only this kind (actuator is implemented)"),
    as_json: bool = typer.Option(False, "--json", help="The machine-readable report"),
):
    """
    Run the conformance checks of RFC-0016 §3g on every NeuroEdge entry point of an installed
    distribution — loading it is what typing its name means. Actuators get the safe-off vectors
    of RFC-0018 §3e on the plugin's device double. Exit 0: every check passed; 1: a check failed
    or could not run, or the distribution has no entry point; 2: a kind not checked yet.
    """
    from ..plugins.conformance import run as run_conformance

    report = run_conformance(distribution, kind)
    if as_json:
        typer.echo(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        summary = report.as_dict()
        typer.echo(
            f"{report.distribution} {report.version or '(not installed)'} — sdk {summary['sdk']}, "
            f"core {summary['core']}, checker {summary['checker']}"
        )
        if report.problem:
            typer.echo(f"✗ {report.problem}")
        for result in report.results:
            mark = {"pass": "✓", "fail": "✗", "unverifiable": "?"}[result.result]
            detail = f" — {result.detail}" if result.detail else ""
            typer.echo(f"  {mark} {result.entry_point}: {result.check}{detail}")
        for entry in report.unimplemented:
            typer.echo(f"  - {entry}: not checked yet (TSK-I2c-12)")
        if not report.results and not report.unimplemented and not report.problem:
            typer.echo("✗ no NeuroEdge entry point: scanning nothing is never a pass")
        if report.editable:
            typer.echo("  ! editable install: no file hash, no badge")
    raise typer.Exit(code=report.exit_code)


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

    # RFC-0013 §3f item 7: besides the canonical traces its primitives allow, a board replays the
    # corpus of every extension primitive it carries — one directory of `fixtures/traces/` per
    # pack (`EXTENSION_TRACES`: `sensor-pack` for `digital.in`, `analog.in` and `i2c`; `vision` for
    # `vision.in`; `fine-control` for a PWM channel of `digital.out`; `motion` for `motion`; `kits` for
    # the three hardware kits, TSK-I2b-01).
    # These are not canonical: a board that lacks a primitive skips them, it does not fail, each
    # corpus is counted apart, and a corpus no board replayed is a failure.
    extension = []
    for directory in EXTENSION_TRACES:
        for path in sorted((traces_root / directory).glob("*.json")):
            try:
                load_trace(path)
                extension.append(path)
                console.print(f"  [green]✓[/green] {directory}/{path.name}")
            except NeuroEdgeError as error:
                problems += 1
                err_console.print(
                    f"  [red]✗[/red] {directory}/{path.name}: [{error.code}] {escape(error.why)}"
                )

    corpus_problems, tool_calls = _verify_tool_corpus()
    problems += corpus_problems

    # One column per (target, board): equivalence means something only once it has run on
    # every reference board of the target (RFC-0013 §3f). `esp32s3` replays on the device,
    # which declares its own board, so it keeps one column until a second board needs a port.
    columns: list[tuple[str, str, str | None]] = []
    for target in requested:
        boards = () if target == "esp32s3" else REFERENCE_BOARDS.get(target, ())
        columns += [(f"{target}/{b}", target, b) for b in boards] or [(target, target, None)]
    console.print(
        f"\n[bold]Replaying canonical traces on {', '.join(c[0] for c in columns)}[/bold]"
    )
    table = Table()
    table.add_column("Trace", style="cyan")
    for label, _target, _board in columns:
        table.add_column(label, justify="center")

    def row_of(path: Path) -> str:
        return path.name if path.parent == traces_root else f"{path.parent.name}/{path.name}"

    rows: dict[str, list[str]] = {row_of(path): [] for path in [*valid, *extension]}
    replayed_on: dict[str, int] = {label: 0 for label, _t, _b in columns}
    extension_replayed: dict[str, int] = {path.parent.name: 0 for path in extension}
    extension_on: dict[str, dict[str, int]] = {}
    for label, target, board_id in columns:
        for path in [*valid, *extension]:
            canonical = path.parent == traces_root
            if target == "esp32s3" and not canonical:
                rows[row_of(path)].append("[dim]—[/dim]")  # the device replays the canonical set
                continue
            if board_id is not None:
                lacking = _trace_lacks(load_board_by_id(board_id), load_trace(path))
                if lacking:
                    # A board replays what it declares enough for; the default board must
                    # replay all of it, so for that one a gap is a failure, not a skip.
                    rows[row_of(path)].append("[dim]—[/dim]")
                    if canonical and board_id == REFERENCE_BOARD[target]:
                        problems += 1
                        err_console.print(
                            f"  [red]✗[/red] {path.name} on {escape(label)}: the default board "
                            f"of {escape(target)} lacks {lacking}, and must replay every "
                            "canonical trace (RFC-0013 §3f)"
                        )
                    continue
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
                    # A canonical trace must be decided by the very gate it was recorded
                    # with (RFC-0008): a different gate_digest is refused, not compared.
                    result = asyncio.run(
                        TracePlayer(
                            path,
                            target=target,
                            board_id=board_id,
                            enforce_gate_digests=True,
                        ).replay()
                    )
                    verdicts = result.verdicts
                diff = GoldenComparator().compare(result, load_trace(path))
            except NeuroEdgeError as error:
                problems += 1
                rows[row_of(path)].append("[red]✗[/red]")
                err_console.print(
                    f"  [red]✗[/red] {path.name} on {escape(label)}: [{error.code}] "
                    f"{escape(error.why)}\n    fix: {escape(error.how)}"
                )
                continue
            if canonical:
                replayed += 1
                replayed_on[label] += 1
            else:  # counted apart: the canonical figures are what each board must reach
                corpus_name = path.parent.name
                extension_replayed[corpus_name] += 1
                counted = extension_on.setdefault(corpus_name, {})
                counted[label] = counted.get(label, 0) + 1
            if diff.ok:
                rows[row_of(path)].append(f"[green]✓[/green] {' '.join(verdicts)}")
            else:
                problems += 1
                rows[row_of(path)].append("[red]✗ differs[/red]")
                for difference in diff.differences:
                    err_console.print(
                        f"  [red]✗[/red] {path.name} on {escape(label)}: {escape(str(difference))}"
                    )
    for name, cells in rows.items():
        table.add_row(name, *cells)
    console.print(table)

    # RFC-0012 §3f clause 2: besides deciding alike, the model must *see* alike — each inference
    # golden of fixtures/vision/golden/ (per model SHA-256, per frame) is held to what each board
    # that declares `vision_in` gets, within that board's own tolerance. Counted apart.
    inference_problems, inference_on = _verify_inference(columns)
    problems += inference_problems

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
            # Each extension corpus must be replayed by at least one board that declares its
            # primitives (RFC-0013 §3f item 7); one nobody replayed proves nothing.
            **(
                {
                    f"{corpus} corpus replays compared": (
                        count,
                        traces_root / corpus,
                        "had no trace replayed on a board that declares its primitives",
                    )
                    for corpus, count in extension_replayed.items()
                }
                if any(t != "esp32s3" for t in requested)
                else {}
            ),
            # Zero on one board is a failure even when the others replayed (RFC-0013 §3f).
            **{
                f"replays compared on {label}": (
                    count,
                    traces_root,
                    "has no canonical trace this board declares enough primitives for",
                )
                for label, count in replayed_on.items()
                if len(columns) > 1
            },
            # Only when some board declares `vision_in` (RFC-0012 §3f clause 2): with none there
            # is no camera to hold to a golden, and nothing to count.
            **(
                {
                    "inference goldens compared": (
                        sum(inference_on.values()),
                        fixtures_dir() / "vision" / "golden",
                        "had no golden compared on a board that declares vision_in",
                    )
                }
                if inference_on
                else {}
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
            f"result, and {_replay_breakdown(replayed_on)} match the verdicts "
            "and pin commands they record."
            f"{_extension_breakdown(extension_on)}"
            f"{_inference_breakdown(inference_on)}"
            f"{on_device}\n\n"
            "[yellow]Compared:[/yellow] decisions only — not timing. Timing equivalence "
            "arrives with TSK-S4-04.",
            title="neuroedge verify",
            border_style="green",
        )
    )


# The primitive each event type of a trace needs from the board it replays on. A type not
# listed needs none: the core primitives are on every reference board (RFC-0013 §3a).
# fixtures/traces/<each>/: the corpus of an extension pack (RFC-0013 §3f item 7), each replayed on
# every board that declares the primitives its traces use.
EXTENSION_TRACES = ("sensor-pack", "vision", "fine-control", "motion", "kits")
_EVENT_PRIMITIVE = {
    "vision_fact": "vision.in",
    "camera_unavailable": "vision.in",
    "actuator_command": "digital.out",
    "actuator_command_rejected": "digital.out",
    "sensor_read": "sensor.read",
    "digital_in": "digital.in",
    "i2c_read": "i2c",
    "analog_in": "analog.in",
    "envelope_refused": "digital.out",
    "pin_state": "digital.out",
    "motion_command": "motion",
    "motion_safe": "motion",
}


def _trace_lacks(board: Any, trace: dict[str, Any]) -> list[str]:
    """
    What `board` lacks to replay `trace`: primitives it does not declare, and — PWM being a block
    of `digital.out`, not a primitive (RFC-0010) — a PWM channel when the trace commands or reads
    one (`pwm` commands, `pin_state`).
    """
    lacking = board.missing_primitives(_trace_primitives(trace))
    uses_pwm = any(
        e["type"] == "pin_state" or e.get("data", {}).get("operation") == "pwm"
        for e in trace["events"]
    )
    if uses_pwm and not board.pwm_pins:
        lacking.append("digital.out pwm")
    return lacking


def _trace_primitives(trace: dict[str, Any]) -> list[str]:
    """The primitives a trace uses, in HAL order: what a board must declare to replay it."""
    used = {_EVENT_PRIMITIVE[e["type"]] for e in trace["events"] if e["type"] in _EVENT_PRIMITIVE}
    return [p for p in ALL_PRIMITIVES if p in used]


def _verify_inference(columns: list[tuple[str, str, str | None]]) -> tuple[int, dict[str, int]]:
    """
    ``(problems, goldens compared per column)``: every inference golden of
    `fixtures/vision/golden/`, checked on each column whose board declares `vision_in`, with that
    board's `tolerance` (RFC-0012 §3f clause 2; `testing/vision_golden.py`). A board without a
    camera, and `esp32s3` (its inference is a device capture, TSK-I3a), are skipped.
    """
    from ..testing.vision import check_scene_inference
    from ..testing.vision_golden import InferenceGolden, tolerance_of

    golden_dir = fixtures_dir() / "vision" / "golden"
    compared: dict[str, int] = {}
    problems = 0
    for label, target, board_id in columns:
        if target == "esp32s3" or board_id is None:
            continue
        try:
            tolerance = tolerance_of(load_board_by_id(board_id))
        except NeuroEdgeError:
            continue  # a tree without this board: the empty-category check says so
        if tolerance is None:
            continue
        compared.setdefault(label, 0)
        console.print(
            f"\n[bold]Inference goldens on {escape(label)}[/bold] (score_abs "
            f"{tolerance.score_abs}, box_iou_min {tolerance.box_iou_min})"
        )
        for path in sorted(golden_dir.glob("*.json")):
            try:
                check_scene_inference(
                    fixtures_dir() / "vision" / path.stem,
                    InferenceGolden.load(path),
                    tolerance,
                    label,
                )
            except NeuroEdgeError as error:
                problems += 1
                err_console.print(
                    f"  [red]✗[/red] {path.name} on {escape(label)}: [{error.code}] "
                    f"{escape(error.why)}\n    fix: {escape(error.how)}"
                )
                continue
            compared[label] = compared.get(label, 0) + 1
            console.print(f"  [green]✓[/green] {path.stem}")
    return problems, compared


def _inference_breakdown(inference_on: dict[str, int]) -> str:
    if not any(inference_on.values()):
        return ""
    return (
        " The inference goldens match within each board's tolerance: "
        + ", ".join(f"{count} on {label}" for label, count in inference_on.items() if count)
        + "."
    )


def _extension_breakdown(extension_on: dict[str, dict[str, int]]) -> str:
    """The replays of each extension corpus (RFC-0013 §3f item 7), apart from the canonical ones."""
    return "".join(
        f" The `{corpus}` corpus replays alike: "
        + ", ".join(f"{count} on {label}" for label, count in counted.items())
        + "."
        for corpus, counted in extension_on.items()
    )


def _replay_breakdown(replayed_on: dict[str, int]) -> str:
    return ", ".join(f"{count} replay(s) on {label}" for label, count in replayed_on.items())


def _device_replay(sessions, path: Path, port: str) -> dict[str, Any]:
    """
    The session in which the device replayed the canonical trace `path`, as a trace.
    Refused, never compared, when the firmware replays an older trace or gate than
    this checkout holds: that would be a pass (or a failure) about something else.
    """
    from ..engine.canonical import digest
    from ..engine.compiler import load_agent_manifest, resolve_gates
    from ..errors import ReplayError
    from ..paths import fixtures_dir
    from ..testing.player import gate_digest_changes

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
    changes = gate_digest_changes(trace["events"], gates)
    if changes:
        change = changes[0]
        raise ReplayError(
            where=f"{port}: {path.name} {change.gate}",
            why=f"the device decides {change.gate} as {change.recorded}, "
            f"this checkout compiles it to {change.current}",
            how=stale,
        )
    return trace


@app.command(epilog=epilog("replay"))
def replay(
    trace_file: Path = typer.Argument(..., help="Trace JSON file"),
    target: str = typer.Option("sim", "--target", "-t", help="Target to replay on: sim or linux"),
    agent: Path = typer.Option(
        None,
        "--agent",
        "-a",
        help="agent.toml that produced the trace (default: ./agent.toml when it is that agent, "
        "else the sample agent named in the trace)",
    ),
    board: str = typer.Option(None, "--board", "-b", help="Board profile id (default per target)"),
    golden: Path = typer.Option(
        None, "--golden", "-g", help="Golden reference to compare against (default: the trace)"
    ),
    trace_out: Path = typer.Option(
        None, "--trace-out", help="Write the replayed trace here (text hashed by default)"
    ),
    raw: bool = typer.Option(
        False, "--raw", help="With --trace-out: keep text in the replayed trace as written"
    ),
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
    if agent is None:
        agent = _recording_agent_here(trace_file)
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
    for warning in result.warnings:
        console.print(f"[yellow]! {escape(warning)}[/yellow]")

    if trace_out is not None:
        dump(result, trace_out, anonymize=not raw)
        if raw:
            _warn_raw()
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
        help="minimal (1 action, 1 gate, tests), villa-concierge, home-voice, factory-monitor, "
        "gate-camera or blinds",
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


AGENT_OPTION = typer.Option(
    Path("agent.toml"), "--agent", "-a", help="Path to the project's agent.toml"
)
ADD_BOARD_OPTION = typer.Option(
    None,
    "--board",
    help="Board the generated test runs on (default: sim-default, or sim-rpi5 when the agent "
    "needs a primitive only that board has)",
)


def _check_added(agent: Path, board: str) -> None:
    """
    Build the project with the add applied (a scratch copy: `add` passes it), as `neuroedge
    build --target sim` would, then start a session on it: the tables that feed the gates
    (`[sim.*]`) are read there. The process-wide action registry is emptied for the check and
    put back after it: the copy defines the project's actions again, and a refused add must
    leave nothing behind, so that the same name can be tried again.
    """
    import sys

    from ..actions import REGISTRY
    from ..engine.compiler import build as run_build
    from ..sim import SimSession

    saved, modules = dict(REGISTRY), set(sys.modules)
    REGISTRY.clear()
    try:
        run_build(agent, target="sim", board_id=board, out_dir=agent.parent / "build")
        SimSession.load(agent, board_id=board).hal.close()
    finally:
        REGISTRY.clear()
        REGISTRY.update(saved)
        for module in set(sys.modules) - modules:
            if module.startswith("neuroedge_agent_"):
                del sys.modules[module]


def _is_servo(channel: str | None) -> bool:
    """
    Whether `channel` is a servo of the board that has motion (`sim-rpi5`), so the action calls
    `motion.servo` and not `motion.motor`. A channel the board does not have is left to the
    build check, which names it.
    """
    try:
        motion = load_board_by_id("sim-rpi5").capability("motion")
    except NeuroEdgeError:
        return False
    return any(servo.get("name") == channel for servo in motion.get("servo", []))


def _add(kind: str, name: str, agent: Path, **options: Any) -> None:
    from ..templates.add import add

    try:
        plan = add(agent.parent, kind, name, check=_check_added, manifest=agent.name, **options)
    except BuildFailed as failed:
        _fail_build(failed)
        return
    except NeuroEdgeError as error:
        _fail(error)
        return
    console.print(f"[bold green]✓[/bold green] added {escape(kind)} {escape(name)}")
    for path in plan.files:
        label = "created" if path in plan.created else "updated"
        console.print(f"  {label} {escape(str(path))}")
    for note in plan.notes:
        console.print(f"  [yellow]note:[/yellow] {escape(note)}")
    console.print(
        "\nNext:\n  neuroedge gate lint gates\n"
        f"  neuroedge build --target sim --board {plan.board}\n"
        "  neuroedge test"
    )


@add_app.command(name="action", epilog=epilog("add action"))
def add_action(
    name: str = typer.Argument(..., help="Name of the action (and of its gate and test)"),
    primitive: str = typer.Option(
        "digital.out", "--primitive", help="digital.out, motion, display or audio.out"
    ),
    pin: str = typer.Option(None, "--pin", help="digital.out and audio.out: the output pin"),
    channel: str = typer.Option(None, "--channel", help="motion: the motor or servo channel"),
    board: str = ADD_BOARD_OPTION,
    agent: Path = AGENT_OPTION,
):
    """Add an @action, its gate, a two-way test and its \\[requires] to the project."""
    servo = _is_servo(channel) if primitive.replace("_", ".") == "motion" else False
    _add(
        "action",
        name,
        agent,
        primitive=primitive,
        pin=pin,
        channel=channel,
        servo=servo,
        board=board,
    )


@add_app.command(name="sensor", epilog=epilog("add sensor"))
def add_sensor(
    name: str = typer.Argument(..., help="Name of the action (and of its gate and test)"),
    primitive: str = typer.Option(
        "sensor.read",
        "--primitive",
        help="sensor.read, digital.in, analog.in, vision.in or audio.in",
    ),
    source: str = typer.Option(
        None, "--source", help="What is read: a sensor, an input pin or an ADC channel"
    ),
    pin: str = typer.Option(None, "--pin", help="The output pin the action drives"),
    label: str = typer.Option(None, "--label", help="vision.in: the label to look for (person)"),
    board: str = ADD_BOARD_OPTION,
    agent: Path = AGENT_OPTION,
):
    """Add an action decided by a sensor, camera or microphone, with its gate and test."""
    _add(
        "sensor",
        name,
        agent,
        primitive=primitive,
        source=source,
        pin=pin,
        label=label,
        board=board,
    )


@add_app.command(name="device", epilog=epilog("add device"))
def add_device(
    name: str = typer.Argument(..., help="Name of the action (and of its gate and test)"),
    device: str = typer.Option(..., "--device", help="The I2C chip, as bus/device (i2c1/ina219)"),
    register: str = typer.Option(..., "--register", help="The register to read (0x02)"),
    width: int = typer.Option(2, "--width", help="Register width in bytes: 1 or 2"),
    board: str = ADD_BOARD_OPTION,
    agent: Path = AGENT_OPTION,
):
    """Add an action that reads an I2C chip and shows the value, with its gate and test."""
    try:
        number = int(register, 0)
        if not 0 <= number <= 0xFF or width not in (1, 2):
            raise ValueError(register)
    except ValueError:
        _fail(
            NeuroEdgeError(
                where=f"neuroedge add device {name}",
                why=f"--register {register!r} must be 0..0xFF and --width {width} 1 or 2",
                how="pass a register such as 0x02 and --width 2",
            )
        )
        return
    _add(
        "device",
        name,
        agent,
        primitive="i2c",
        device=device,
        register=number,
        width=width,
        board=board,
    )


@add_app.command(name="gate", epilog=epilog("add gate"))
def add_gate(
    name: str = typer.Argument(..., help="Name of the gate (and of its test)"),
    fact: list[str] = typer.Option(
        None, "--fact", help="A bool fact the gate needs true (repeatable; default user_verified)"
    ),
    agent: Path = AGENT_OPTION,
):
    """Add a fail-closed gate on its own, with a two-way test; an @action names it by `gate=`."""
    _add("gate", name, agent, facts=tuple(fact or ()))


def _recording_agent_here(trace_file: Path) -> Path | None:
    """
    `./agent.toml` when it is the agent that recorded the trace (same `[agent] name`
    as the trace's `agent_version`), else None and the player looks for the sample
    agent of that name. Replaying in the project that recorded it needs no --agent;
    an agent.toml of another agent is never used silently.
    """
    here = Path("agent.toml")
    if not here.is_file():
        return None
    try:
        metadata = json.loads(trace_file.read_text(encoding="utf-8"))["metadata"]
        recorded = str(metadata["agent_version"]).partition("@")[0]
        from ..engine.compiler import load_agent_manifest

        name = load_agent_manifest(here).name
    except (OSError, ValueError, KeyError, TypeError, NeuroEdgeError):
        return None  # the player reports what is wrong with the trace or the agent
    if name != recorded:
        console.print(
            f"[dim]./agent.toml is {escape(name)!r}, the trace was recorded by "
            f"{escape(recorded)!r}: not used (pass --agent to choose)[/dim]"
        )
        return None
    return here


def _default_agent() -> Path:
    """`agent.toml` here, else the sample agent of a source checkout."""
    here = Path("agent.toml")
    sample = repo_root() / "fixtures" / "agents" / "villa-concierge" / "agent.toml"
    return sample if not here.is_file() and sample.is_file() else here


def _trace_log(trace_out: Path | None, raw: bool):
    """
    The session's event log when `--trace-out` writes a file (NFR-PRIV-03, TSK-I1-01):
    a `TraceRecorder`, which hashes the user's words at the source unless `--raw`
    keeps them (then the trace says `metadata.anonymized = false`, said on stderr).
    Without `--trace-out` no file is written and the session keeps its plain log,
    so the live page still shows what was said.
    """
    if trace_out is None:
        return None
    from ..testing.recorder import TraceRecorder

    recorder = TraceRecorder(anonymize=False) if raw else TraceRecorder()
    if raw:
        _warn_raw()
    return recorder


def _start_session(
    verb: str,
    agent,
    target: str,
    board: str | None,
    registry,
    events=None,
    ui: bool = False,
    clock=None,
    target_options=None,
):
    """
    Load the agent for an interactive session on `sim` or `linux`, or exit with the
    right code: 2 for a target (or `--ui` on it) with no session yet, 1 when the agent
    does not fit the board or `linux` cannot run (no `gpiod`, no GPIO chip — Q-16).
    `clock`: the session's clock (a voice session runs on a virtual one).
    `target_options`: the HAL's own options (a voice session on `linux` passes
    ``audio="file"`` so it never opens a live device — TSK-S5-08).
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
            **({"clock": clock} if clock is not None else {}),
            **({"target_options": target_options} if target_options is not None else {}),
        )
    except BuildFailed as failed:
        _fail_build(failed)
    except NeuroEdgeError as error:
        _fail(error)
    raise AssertionError("unreachable")  # _fail* always exit


VOICE_FILE_OPTION = typer.Option(
    None,
    "--voice-file",
    help=(
        "Speak instead of typing: a WAV file (16 kHz mono 16-bit on sim; 8–96 kHz, 1–2 channels "
        "on linux, converted to the board's rate) heard through the agent's \\[stt] provider, "
        "replies spoken through \\[tts]"
    ),
)
VOICE_OUT_OPTION = typer.Option(
    None, "--voice-out", help="With --voice-file: write what the device said (TTS) as a WAV file"
)


def _voice_session(
    verb: str,
    agent,
    target: str,
    board: str | None,
    registry,
    *,
    voice_file: Path | None,
    voice_out: Path | None,
    command: str | None,
    ui: bool = False,
    trace_out: Path | None = None,
    anonymize: bool = True,
) -> int:
    """
    `--voice-file`: the WAV file is the session's `audio.in` (TSK-S3-13). On `linux`
    it goes through `LinuxHAL`'s file backend — converted to the board's rate, no
    microphone and no `sounddevice` (TSK-S5-08). Exit 1 on a flag it cannot combine
    with, 2 where voice is not implemented yet.
    """
    if voice_file is None:
        _fail(
            NeuroEdgeError(
                where=f"neuroedge {verb} --voice-out",
                why="--voice-out writes the replies of a --voice-file session, and none is given",
                how="add --voice-file <turn.wav>, or drop --voice-out",
            )
        )
    if command is not None:
        _fail(
            NeuroEdgeError(
                where=f"neuroedge {verb} --voice-file -c",
                why="-c is one typed command and --voice-file is spoken input: one session, one input",
                how="drop -c, or drop --voice-file",
            )
        )
    planned = None
    if ui:
        planned = ("--ui", "the live page does not play or record audio yet")
    elif target in PLANNED_SESSIONS:
        planned = (
            f"--target {target}",
            f"sessions on {target} arrive with {PLANNED_SESSIONS[target]}",
        )
    if planned is not None:
        err_console.print(
            Panel(
                f"`neuroedge {verb} --voice-file {planned[0]}` is not implemented yet: "
                f"{planned[1]}.\n\nSpoken input runs on `sim` today, in the terminal.",
                title=f"[yellow]Not implemented: {verb} --voice-file {escape(planned[0])}[/yellow]",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=2)
    from ..engine.compiler import load_agent_manifest
    from ..perception import VirtualClock
    from ..perception.providers import load_wake_word_config, make_wake_word
    from .voice import run_voice

    # The wake word's model files — and the detector library or adapter — are checked
    # here, before the session requests any GPIO line: the models are the user's own
    # and may live only on the device, and the build (rightly) no longer requires them
    # on this machine (TSK-I4-01, Q-45).
    try:
        manifest = load_agent_manifest(agent or _default_agent())
        wake_config = load_wake_word_config(manifest, check_files=True)
        if wake_config is not None:
            make_wake_word(wake_config, manifest.root)
    except NeuroEdgeError as error:
        _fail(error)

    clock = VirtualClock()
    events = None
    if trace_out is not None:
        from ..testing.recorder import TraceRecorder

        events = TraceRecorder(clock=clock)  # the default hashes (NFR-PRIV-03)
        if not anonymize:
            events = TraceRecorder(anonymize=False, clock=clock)
            _warn_raw()
    session = _start_session(
        verb,
        agent,
        target,
        board,
        registry,
        events=events,
        clock=clock,
        # A voice session is the file backend only, whatever the machine's
        # NEUROEDGE_LINUX_AUDIO says: live capture/playback drives no session yet
        # (TODOS.md #45), and the file backend must never open a device (TSK-S5-08).
        target_options={"audio": "file"} if target == "linux" else None,
    )
    if events is not None:
        trace_out = (
            trace_out if trace_out.suffix == ".json" else trace_out / f"{events.session_id}.json"
        )
    return run_voice(session, clock, voice_file, voice_out, trace_out, console, err_console)


def _voice_live_session(
    verb: str,
    agent,
    target: str,
    board: str | None,
    registry,
    *,
    half_duplex: bool = False,
    trace_out: Path | None = None,
    anonymize: bool = True,
) -> int:
    """
    `--mic`: live microphone session on `sim` (TSK-I4-04). The microphone is `audio.in`
    and the speaker is `audio.out` via PortAudio (`sounddevice`).
    """
    from ..engine.compiler import load_agent_manifest
    from ..perception import VirtualClock
    from ..perception.providers import load_wake_word_config, make_wake_word
    from .voice import run_voice_live

    try:
        manifest = load_agent_manifest(agent or _default_agent())
        wake_config = load_wake_word_config(manifest, check_files=True)
        if wake_config is not None:
            make_wake_word(wake_config, manifest.root)
    except NeuroEdgeError as error:
        _fail(error)

    clock = VirtualClock()
    events = None
    if trace_out is not None:
        from ..testing.recorder import TraceRecorder

        events = TraceRecorder(clock=clock)  # the default hashes (NFR-PRIV-03)
        if not anonymize:
            events = TraceRecorder(anonymize=False, clock=clock)
            _warn_raw()
    session = _start_session(
        verb,
        agent,
        target,
        board,
        registry,
        events=events,
        clock=clock,
        target_options={"audio": "live"},
    )
    if events is not None:
        trace_out = (
            trace_out if trace_out.suffix == ".json" else trace_out / f"{events.session_id}.json"
        )
    return run_voice_live(
        session,
        clock,
        half_duplex=half_duplex,
        trace_out=trace_out,
        console=console,
        err_console=err_console,
    )


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
        None,
        "--trace-out",
        help="Write the session trace (trace.v1 JSON) here on exit (text hashed by default)",
    ),
    raw: bool = typer.Option(
        False, "--raw", help="With --trace-out: keep the user's words in the trace as plain text"
    ),
    ui: bool = typer.Option(
        False, "--ui", help="Serve the session as a live page on 127.0.0.1 (FR-TGT-06)"
    ),
    port: int = typer.Option(8765, "--port", help="Port for --ui"),
    no_browser: bool = typer.Option(False, "--no-browser", help="With --ui, do not open a browser"),
    voice_file: Path = VOICE_FILE_OPTION,
    voice_out: Path = VOICE_OUT_OPTION,
    mic: bool = typer.Option(
        False,
        "--mic",
        help="Speak through the microphone in real time (sim target; needs neuroedge\\[audio])",
    ),
    half_duplex: bool = typer.Option(
        False,
        "--half-duplex",
        help=(
            "With --mic: mute the microphone while the agent speaks (for loudspeakers; "
            "barge-in disabled)"
        ),
    ),
    registry: Path | None = REGISTRY_OPTION,
):
    """
    Run the agent: type a command, see the gate verdict and the pins.
    With --ui (sim only) the same session is shown live in the browser.

    Input is typed text matched by the agent's commands.toml — no network, no
    key (Q-15). The agent is build-checked against the board first. On `linux`
    the pins are real GPIO lines (the `linux` extra; a board, or
    scripts/setup_gpio_sim.sh).

    With --voice-file the input is speech: each turn the VAD finds goes to
    the agent's STT provider, its transcript takes the typed line's path through
    the gate, and replies go to its TTS provider (--voice-out saves them). On
    `linux` the file is converted to the board's rate by `LinuxHAL`'s file
    backend; microphone and speaker (the `audio` extra, Q-22) are a later
    session (TODOS.md #45).

    With --mic, talk to the agent through the microphone in real time on sim.
    Replies play through the speaker. With --half-duplex, the microphone is muted
    while the agent speaks so it does not hear itself through loudspeakers
    (barge-in is disabled in that mode).
    """
    if half_duplex and not mic:
        _fail(
            NeuroEdgeError(
                where="neuroedge run --half-duplex",
                why="--half-duplex is only valid with --mic (live audio)",
                how="add --mic, or drop --half-duplex",
            )
        )
    if mic:
        if voice_file is not None:
            _fail(
                NeuroEdgeError(
                    where="neuroedge run --mic --voice-file",
                    why="--mic is live audio from the microphone and --voice-file is a prerecorded WAV file",
                    how="drop --voice-file for live audio, or drop --mic",
                )
            )
        if voice_out is not None:
            _fail(
                NeuroEdgeError(
                    where="neuroedge run --mic --voice-out",
                    why="--voice-out is for --voice-file sessions; live audio plays directly through the speaker",
                    how="drop --voice-out",
                )
            )
        if command is not None:
            _fail(
                NeuroEdgeError(
                    where="neuroedge run --mic -c",
                    why="-c is one typed command and --mic is live spoken input: one session, one input",
                    how="drop -c, or drop --mic",
                )
            )
        if target != "sim":
            err_console.print(
                Panel(
                    f"`neuroedge run --mic --target {escape(target)}` is not implemented yet: "
                    "Linux live audio waits for measured PipeWire echo cancellation "
                    "(Q-50, docs/spec/simulation_coverage.md §6.2).\n\n"
                    "Live audio runs on `sim` today.",
                    title=f"[yellow]Not implemented: run --mic on {escape(target)}[/yellow]",
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=2)
        if ui:
            err_console.print(
                Panel(
                    "`neuroedge run --mic --ui` is not implemented yet: "
                    "the live page does not play or record audio yet.\n\n"
                    "Spoken input runs on `sim` today, in the terminal.",
                    title="[yellow]Not implemented: run --mic --ui[/yellow]",
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=2)

        code = _voice_live_session(
            "run",
            agent,
            target,
            board,
            registry,
            half_duplex=half_duplex,
            trace_out=trace_out,
            anonymize=not raw,
        )
        raise typer.Exit(code=code)
    if voice_file is not None or voice_out is not None:
        code = _voice_session(
            "run",
            agent,
            target,
            board,
            registry,
            voice_file=voice_file,
            voice_out=voice_out,
            command=command,
            ui=ui,
            trace_out=trace_out,
            anonymize=not raw,
        )
        raise typer.Exit(code=code)
    from .run import run_session

    session = _start_session(
        "run", agent, target, board, registry, events=_trace_log(trace_out, raw), ui=ui
    )
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


@app.command(epilog=epilog("studio"))
def studio(
    agent: Path = typer.Option(
        None,
        "--agent",
        "-a",
        help="Path to agent.toml (default: ./agent.toml, else the villa-concierge sample)",
    ),
    port: int = typer.Option(8765, "--port", help="Port on 127.0.0.1 (0 picks a free one)"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Do not open a browser"),
    mic: bool = typer.Option(
        False, "--mic", help="Also listen to the microphone (sim; needs neuroedge\\[audio])"
    ),
    half_duplex: bool = typer.Option(
        False, "--half-duplex", help="With --mic: mute the microphone while the agent speaks"
    ),
):
    """
    Open NeuroEdge Studio: every capability of the agent in one local web app on
    127.0.0.1 — the live session (typed and, with --mic, spoken), gates and a what-if
    box, traces and replay, verify, the ESP32-S3 device views, MCP and the agent's
    configuration (docs/spec/studio.md). `sim` only; Ctrl-C to stop.
    """
    from ..studio import serve as serve_studio
    from ..studio import voice as studio_voice

    if half_duplex and not mic:
        _fail(
            NeuroEdgeError(
                where="neuroedge studio --half-duplex",
                why="--half-duplex mutes the microphone of a --mic session, and there is none",
                how="add --mic, or drop --half-duplex",
            )
        )
    agent_path = agent or _default_agent()
    clock = None
    target_options = None
    on_start = None
    if mic:
        from ..engine.compiler import load_agent_manifest
        from ..errors import AgentManifestError
        from ..perception import VirtualClock
        from ..perception.providers import (
            load_speech_configs,
            load_wake_word_config,
            make_wake_word,
        )

        try:
            manifest = load_agent_manifest(agent_path)
            stt_config, _ = load_speech_configs(manifest)
            if stt_config is None:
                raise AgentManifestError(
                    where=f"{manifest.source} -> [stt]",
                    why="--mic needs a speech-to-text provider, and the agent declares none",
                    how="add [stt] with model and api_key_env, or the base_url of a local server "
                    '(docs/user/huong-dan.md); or type the command: neuroedge run -c "…" (Q-15)',
                )
            wake_config = load_wake_word_config(manifest, check_files=True)
            if wake_config is not None:
                make_wake_word(wake_config, manifest.root)
        except NeuroEdgeError as error:
            _fail(error)

        clock = VirtualClock()
        target_options = {"audio": "live"}

        def on_start(server):
            studio_voice.start(server, half_duplex=half_duplex)

    session = _start_session(
        "studio",
        agent_path,
        "sim",
        None,
        None,
        ui=True,
        clock=clock,
        target_options=target_options,
    )

    try:
        serve_studio(
            session, agent_path, port, console, open_browser=not no_browser, on_start=on_start
        )
    except NeuroEdgeError as error:
        _fail(error)
    finally:
        session.close()


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
    """
    Match the agent's capability needs against the board and compile its gates.

    For esp32s3 it also writes the agent's firmware: an ESP-IDF project in
    <out>/esp32s3/ to build and flash with idf.py. Any problem: exit 1, nothing written.
    """
    from ..engine.compiler import build as run_build

    try:
        report = run_build(
            agent,
            target=target,
            board_id=board,  # None: the target's default board, never another one (RFC-0013 §3e)
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
    for warning in report.warnings:
        console.print(f"  warning: {warning}", markup=False, highlight=False)
    for artifact in report.artifacts:
        console.print(f"  wrote:   {artifact}")
    if report.firmware is not None:
        console.print(
            f"  firmware: {report.firmware} — ESP-IDF project, {report.firmware_files} files; "
            "build and flash it with idf.py (docs/user/nap-firmware.md)"
        )


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
    raw: bool = typer.Option(
        False, "--raw", help="Keep the user's words in the trace as plain text (anonymized: false)"
    ),
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
    voice_file: Path = VOICE_FILE_OPTION,
    voice_out: Path = VOICE_OUT_OPTION,
    registry: Path | None = REGISTRY_OPTION,
):
    """
    Record a session to a trace file that `trace validate` and `replay` accept.

    Same session as `run`, on `sim` or `linux`; on exit the trace is validated
    against trace.v1 and written to `--out` (default `traces/<session_id>.json`).
    A trace recorded on `linux` replays on `sim` to the same decisions.

    By default the trace stores decisions, not the user's words: raw text is
    hashed at the source (NFR-PRIV-03) and the trace says `anonymized: true`.
    `--raw` keeps text verbatim (it then says so on stderr and the trace says
    `anonymized: false`). `--anonymize` is still accepted, now the default.

    With `--target esp32s3 --port`, the device records: every `NE1` session it
    writes on its UART becomes one trace file, validated before it is written
    (docs/spec/simulation_coverage.md §4, TSK-S4-09).
    """
    if raw and anonymize:
        _fail(
            NeuroEdgeError(
                where="neuroedge record --raw --anonymize",
                why="--raw keeps the user's words and --anonymize hashes them: one trace, one "
                "choice",
                how="keep --raw (text stays verbatim, marked anonymized: false), or drop --raw "
                "(the default hashes)",
            ),
            code=2,
        )
    keep_raw = raw  # --anonymize is now the default; only --raw opts out
    if target == "esp32s3" or port is not None:
        if voice_file is not None or voice_out is not None:
            _fail(
                NeuroEdgeError(
                    where="neuroedge record --port --voice-file",
                    why="a device session is the firmware's: it hears through its own microphone",
                    how="drop --voice-file to read the device's UART, or drop --port for sim",
                )
            )
        if keep_raw:
            _warn_raw()
        _record_from_device(target, port, baud, timeout, out, keep_raw, board, agent, command)
        return
    if voice_file is not None or voice_out is not None:
        code = _voice_session(
            "record",
            agent,
            target,
            board,
            registry,
            voice_file=voice_file,
            voice_out=voice_out,
            command=command,
            trace_out=out,
            anonymize=not keep_raw,
        )
        raise typer.Exit(code=code)
    from ..testing.recorder import TraceRecorder
    from .run import run_session

    recorder = TraceRecorder(anonymize=False) if keep_raw else TraceRecorder()
    if keep_raw:
        _warn_raw()
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


def _record_from_device(target, port, baud, timeout, out, raw, board, agent, command) -> None:
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
            session.recorder(anonymize=not raw).save(path)
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
