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
from ..errors import BuildFailed, NeuroEdgeError
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

app.add_typer(gate_app, name="gate")
app.add_typer(trace_app, name="trace")
app.add_typer(board_app, name="board")

console = Console()
err_console = Console(stderr=True)


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


@app.command()
def verify(
    targets: str = typer.Option("sim,linux", "--targets", help="Comma-separated target list"),
):
    """
    Verify the frozen artifacts: every gate resolves and every trace validates.

    Cross-target replay equivalence — the full meaning of acceptance criterion
    A2 — needs the `sim` and `linux` HALs from Sprints 2 and 3. What this command
    checks today is the part that exists, and it says which part that is.
    """
    root = repo_root()
    requested = [t.strip() for t in targets.split(",") if t.strip()]
    problems = 0

    console.print("[bold]Resolving gates in gates/[/bold]")
    for path in sorted(gates_dir().rglob("*.yaml")):
        try:
            gate = resolve_gate_file(path)
            console.print(
                f"  [green]✓[/green] {gate.name}@{gate.version} "
                f"({gate.inheritance_levels} level(s), fail {gate.budget.get('fail')})"
            )
        except NeuroEdgeError as error:
            problems += 1
            err_console.print(f"  [red]✗[/red] {path.name}: [{error.code}] {escape(error.why)}")

    console.print("\n[bold]Validating canonical traces in fixtures/traces/[/bold]")
    for path in sorted((root / "fixtures" / "traces").glob("*.json")):
        try:
            load_trace(path)
            console.print(f"  [green]✓[/green] {path.name}")
        except NeuroEdgeError as error:
            problems += 1
            err_console.print(f"  [red]✗[/red] {path.name}: [{error.code}] {escape(error.why)}")

    console.print("\n[bold]Board capability declarations[/bold]")
    for board in available_boards():
        marker = "[green]✓[/green]" if board.target in requested else "[dim]·[/dim]"
        console.print(f"  {marker} {board.id} (target {board.target})")

    if problems:
        err_console.print(f"\n[bold red]{problems} problem(s) found.[/bold red]")
        raise typer.Exit(code=1)

    console.print(
        Panel(
            "[green]Schema-level verification passed:[/green] all gates resolve, all "
            "canonical traces validate.\n\n"
            "[yellow]Not yet covered:[/yellow] replaying traces on live targets and "
            "comparing verdict sequences across them (acceptance criterion A2). That "
            "needs the sim HAL (TSK-S2-01) and the linux HAL (TSK-S3-05).",
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
        "minimal", "--template", help="minimal (1 action, 1 gate, tests) or villa-concierge"
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
    registry: Path | None = REGISTRY_OPTION,
):
    """
    Run the agent on `sim`: type a command, see the gate verdict and the pins.

    Input is typed text matched by the agent's commands.toml — no network, no
    key (Q-15). The agent is build-checked against the board first.
    """
    from .run import run_session

    session = _start_session("run", agent, target, board, registry)
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
