"""
`neuroedge run --target sim` — the typed-text REPL (TSK-S3-06, FR-CLI-02, Q-15).

Each line typed at ``neuroedge>`` goes through `SimSession.handle()`: the local
command grammar recognises it, the command's @action runs through `c.do()`,
and the gate verdict and the virtual pins are printed. Lines starting with
``:`` inspect or change the session facts the gate reads.

Exit codes: 0 on ``exit`` / ``quit`` / Ctrl-D, and after ``--command`` whatever
the verdict (a BLOCK is the gate working, not the command failing); 1 when the
agent does not load, or the ``--command`` turn raises a contract violation;
130 on Ctrl-C.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markup import escape
from rich.table import Table

from ..actions import ActionResult
from ..errors import NeuroEdgeError
from ..sim import SimSession, Turn

PROMPT = "neuroedge> "
EXIT_WORDS = ("exit", "quit", ":q")

HELP = """\
Type a command the agent's grammar knows, e.g. "mở cửa phòng 101".
  :facts              show the session facts the gate reads
  :set <name> <value> set a fact (true/false, a number, or text)
  :unset <name>       forget a fact — the gate then treats it as undecided
  :pins               show the virtual pins
  :sensors            show the simulated sensor values
  :sensor <name> <v>  set a sensor value (what sensor.read returns)
  :screen             show the last display frame
  :help               this help
  exit | quit | Ctrl-D  leave"""


def parse_value(text: str) -> Any:
    lowered = text.casefold()
    if lowered in ("true", "false"):
        return lowered == "true"
    for kind in (int, float):
        try:
            return kind(text)
        except ValueError:
            continue
    return text


def pin_state(session: SimSession, pin: str) -> str:
    commands = session.hal.pin(pin).commands
    if not commands:
        return "LOW"
    operation, duration_ms = commands[-1]
    if operation == "pulse":
        return f"PULSED {duration_ms / 1000:g}s"
    return "HIGH" if operation == "on" else "LOW"


def pin_table(session: SimSession) -> Table:
    table = Table(title="Virtual pins", title_justify="left")
    table.add_column("Pin", style="cyan")
    table.add_column("State", style="bold")
    table.add_column("Commands", justify="right")
    for pin in session.pins:
        state = pin_state(session, pin)
        style = "green" if state.startswith(("PULSED", "HIGH")) else "dim"
        table.add_row(pin, f"[{style}]{state}[/{style}]", str(len(session.hal.pin(pin).commands)))
    return table


def _verdict_line(result: ActionResult, indent: str = "", call: str = "()") -> str:
    gate = result.gate
    label = escape(gate.gate if gate is not None else result.action)
    if not result.blocked:
        return f"{indent}[bold green]✓ ALLOW[/bold green] {label} → {escape(result.action + call)}"
    detail = [f"reason: {gate.reason}"] if gate is not None and gate.reason else []
    if gate is not None and gate.failed_criterion:
        detail.append(f"criterion: {gate.failed_criterion}")
    line = f"{indent}[bold red]✗ BLOCK[/bold red] {label} ({escape(', '.join(detail))})"
    if gate is not None and gate.on_block_action:
        line += f"\n{indent}  action: [bold]{escape(gate.on_block_action)}[/bold]"
        if gate.escalated_to:
            line += f" to {escape(gate.escalated_to)}"
        if gate.fallback_action:
            line += f" → {escape(gate.fallback_action)}"
        if gate.message:
            line += f' — "{escape(gate.message)}"'
    return line


def frame_line(frame) -> str:
    if frame.text is not None:
        return f"  [bold]screen[/bold] ({frame.width}x{frame.height}): {escape(frame.text)}"
    return f"  [bold]screen[/bold] {frame.format} {frame.width}x{frame.height} {frame.sha256[:19]}…"


def render_turn(turn: Turn, session: SimSession, console: Console, frames_before: int = 0) -> None:
    recognition = turn.recognition
    if not turn.recognised:
        console.print(
            f"[bold red]✗ BLOCK[/bold red] command not recognized "
            f"(best match {recognition.confidence:.2f} < threshold {session.grammar.threshold:.2f})"
            " — no action ran, no pin moved (Q-14)"
        )
        return
    slots = ", ".join(f"{k}={v}" for k, v in recognition.slots.items())
    console.print(
        f"[dim]intent[/dim] [bold]{escape(recognition.intent)}[/bold] "
        f"({recognition.confidence:.2f}){escape(f' [{slots}]') if slots else ''}"
    )
    if turn.result is None:
        console.print(
            "  no physical action for this intent; spoken replies need SystemTwo (TSK-S2-11)"
        )
        return
    call = ", ".join(f"{k}={v!r}" for k, v in turn.arguments.items())
    console.print(_verdict_line(turn.result, call=f"({call})"))
    fallback = turn.result.fallback
    while fallback is not None:
        console.print(_verdict_line(fallback, indent="  fallback: "))
        fallback = fallback.fallback
    for frame in session.hal.frames[frames_before:]:
        console.print(frame_line(frame))
    console.print(pin_table(session))


def _meta(line: str, session: SimSession, console: Console) -> None:
    name, _, rest = line[1:].partition(" ")
    if name == "facts":
        table = Table(title="Session facts", title_justify="left")
        table.add_column("Criterion", style="cyan")
        table.add_column("Value")
        for key, value in sorted(session.facts.items()):
            table.add_row(key, json.dumps(value, ensure_ascii=False))
        for key, (slot, expected) in sorted(session.slot_facts.items()):
            table.add_row(key, f"[dim]from slot {{{slot}}} == {expected!r}[/dim]")
        console.print(table)
    elif name == "set" and len(rest.split(maxsplit=1)) == 2:
        key, value = rest.split(maxsplit=1)
        session.facts[key] = parse_value(value)
        console.print(f"  {escape(key)} = {json.dumps(session.facts[key], ensure_ascii=False)}")
    elif name == "unset" and rest.strip():
        session.facts.pop(rest.strip(), None)
        console.print(f"  {escape(rest.strip())} is now undecided")
    elif name == "pins":
        console.print(pin_table(session))
    elif name == "sensors":
        table = Table(title="Simulated sensors", title_justify="left")
        table.add_column("Sensor", style="cyan")
        table.add_column("Value")
        for sensor, (value, unit) in session.hal.sensor_values().items():
            shown = (
                "[dim]not set[/dim]" if value is None else escape(f"{value} {unit or ''}".strip())
            )
            table.add_row(sensor, shown)
        console.print(table)
    elif name == "sensor" and len(rest.split(maxsplit=1)) == 2:
        sensor, value = rest.split(maxsplit=1)
        try:
            session.hal.set_sensor(sensor, parse_value(value))
        except NeuroEdgeError as error:
            console.print(f"[red]{escape(error.why)}[/red]")
            return
        console.print(f"  {escape(sensor)} = {escape(value)}")
    elif name == "screen":
        if not session.hal.frames:
            console.print("  nothing has been drawn yet")
        else:
            console.print(frame_line(session.hal.frames[-1]))
    elif name == "help":
        console.print(escape(HELP))
    else:
        console.print(f"[yellow]unknown command {escape(line)}; try :help[/yellow]")


def _turn(text: str, session: SimSession, console: Console, err_console: Console) -> bool:
    """Run one line. False when it raised a contract violation."""
    frames_before = len(session.hal.frames)
    try:
        turn = asyncio.run(session.handle(text))
    except NeuroEdgeError as error:
        err_console.print(f"[bold red]✗ {error.code}[/bold red] [cyan]{escape(error.where)}[/cyan]")
        err_console.print(f"  why: {escape(error.why)}")
        err_console.print(f"  fix: {escape(error.how)}")
        return False
    render_turn(turn, session, console, frames_before)
    return True


def banner(session: SimSession, console: Console) -> None:
    manifest = session.manifest
    gates = ", ".join(f"{key} → {ref}" for key, ref in manifest.gates.items()) or "none"
    console.print(
        f"[bold]{escape(manifest.label)}[/bold] on [cyan]sim[/cyan] "
        f"([cyan]{escape(session.hal.board.id)}[/cyan]) · offline, typed text (Q-15)"
    )
    console.print(f"  gates: {escape(gates)}")
    console.print(f"  grammar: {escape(session.grammar.source)}")


def run_session(
    session: SimSession,
    console: Console,
    err_console: Console,
    *,
    command: str | None = None,
    trace_out: Path | None = None,
) -> int:
    """Drive the session and return the exit code."""
    try:
        if command is not None:
            return 0 if _turn(command, session, console, err_console) else 1
        banner(session, console)
        console.print(pin_table(session))
        console.print("[dim]:help for commands · exit to leave[/dim]")
        while True:
            try:
                line = input(PROMPT).strip()
            except EOFError:
                console.print()
                return 0
            except KeyboardInterrupt:
                console.print()
                return 130
            if not line:
                continue
            if line in EXIT_WORDS:
                return 0
            if line.startswith(":"):
                _meta(line, session, console)
            else:
                _turn(line, session, console, err_console)
    finally:
        if trace_out is not None:
            trace_out.parent.mkdir(parents=True, exist_ok=True)
            trace_out.write_text(
                json.dumps(session.trace(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            console.print(f"trace: {escape(str(trace_out))} ({len(session.events.events)} events)")
