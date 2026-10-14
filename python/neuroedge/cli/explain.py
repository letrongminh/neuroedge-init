"""
`neuroedge gate explain` — a resolved gate for a reviewer who does not read YAML
(TSK-S3-18, FR-GATE-01, FR-CLI-05, journey J6).

Output is Vietnamese, like the gates' own `instructions`: it is read by the
property's operators and safety reviewers, not by the developer who wrote it.
"""

from __future__ import annotations

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from ..engine.gate_explain import GateExplanation


def _fail_policy(fail: str) -> str:
    if fail == "open":
        return (
            "[bold red]fail-open[/bold red] (error or timeout → ALLOW, "
            "unless a known criterion fails)"
        )
    return "[green]fail-closed[/green] (error or timeout → BLOCK)"


def render(explanation: GateExplanation, console: Console) -> None:
    gate = explanation.gate
    header = []
    if explanation.extends:
        header.append(f"Extends: [cyan]{escape(explanation.extends)}[/cyan]")
    else:
        header.append("Root gate — extends no other gate")
    header.append(
        f"Levels: {gate.inheritance_levels} ({escape(' → '.join(gate.chain))}) · "
        f"Failure policy: {_fail_policy(gate.budget.get('fail', 'closed'))}"
    )
    console.print(
        Panel("\n".join(header), title=f"Gate: {escape(explanation.label)}", border_style="cyan")
    )

    console.print("\n[bold]1. Evaluation criteria (evaluate):[/bold]")
    table = Table()
    table.add_column("Criterion", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Source / Description")
    for criterion in explanation.criteria:
        origin = f"(From {criterion.introduced_by})" if criterion.inherited else "(New)"
        detail = f" ({criterion.detail})" if criterion.detail else ""
        table.add_row(
            criterion.name,
            criterion.kind,
            f"[dim]{escape(origin)}[/dim] {escape(criterion.instructions)}{escape(detail)}",
        )
    console.print(table)

    console.print("\n[bold]2. Allow conditions (allow_when)[/bold] — ALL must hold:")
    for clause in explanation.clauses:
        note = ""
        if clause.status == "tightened":
            note = (
                f" [yellow](parent allows {escape(clause.parent_admits)} — "
                f"child tightened it)[/yellow]"
            )
        elif clause.status == "inherited":
            note = " [dim](inherited unchanged from parent)[/dim]"
        elif explanation.parent is not None:
            note = " [dim](new in this gate)[/dim]"
        console.print(
            f"  [green]✓[/green] {escape(clause.criterion)} ∈ {escape(clause.admits)}{note}"
        )
    console.print(
        "  [dim]A criterion that cannot be determined (network lost, command not recognised) → BLOCK.[/dim]"
    )
    if gate.arguments:
        parent = explanation.parent.arguments if explanation.parent is not None else {}
        console.print(
            "\n[bold]Argument limits (arguments, RFC-0005)[/bold] — checked before any criterion:"
        )
        for name, limit in gate.arguments.items():
            bounds = ", ".join(f"{key}={value}" for key, value in limit.items() if key != "type")
            note = ""
            if name in parent and parent[name] != limit:
                note = " [yellow](child narrowed it versus parent)[/yellow]"
            elif name in parent:
                note = " [dim](inherited unchanged from parent)[/dim]"
            console.print(
                f"  [green]✓[/green] {escape(name)}: {escape(limit['type'])}"
                f"{escape(' · ' + bounds) if bounds else ''}{note}"
            )
        console.print(
            "  [dim]Outside the limits → BLOCK argument_out_of_range, then on_block.[/dim]"
        )

    console.print("\n[bold]3. Budget & behaviour when blocked:[/bold]")
    p95, parent_p95 = explanation.p95, explanation.parent_p95
    if parent_p95 is None:
        budget_note = ""
    elif parent_p95 == p95:
        budget_note = f" (inherited unchanged from parent, {parent_p95} ms)"
    else:
        budget_note = f" (inherited from parent {parent_p95} ms and tightened)"
    console.print(f"  • Time budget (p95): {p95} ms{escape(budget_note)}")

    on_block = gate.on_block
    behaviour = escape(str(on_block.get("action")))
    if on_block.get("to"):
        behaviour += f" → {escape(on_block['to'])}"
    if on_block.get("fallback_action"):
        behaviour += f" → runs {escape(on_block['fallback_action'])} through its own gate"
    console.print(f"  • on_block behaviour: [bold]{behaviour}[/bold]")
    if on_block.get("message"):
        console.print(f'    Message: "{escape(on_block["message"])}"')
    if on_block.get("confirms"):
        console.print(
            "    A confirmation on the device stands in for: "
            f"[bold]{escape(', '.join(on_block['confirms']))}[/bold] — every other condition must "
            "still hold; System 2 and MCP clients cannot confirm (RFC-0006)"
        )
    if explanation.on_block_changed:
        parent = explanation.parent.on_block
        was = escape(str(parent.get("action")))
        if parent.get("to"):
            was += f" → {escape(parent['to'])}"
        console.print(f"    [dim](parent: {was}; change checked under RFC-0004)[/dim]")
    console.print(
        "  • When blocked, the physical action does [bold]not[/bold] run — "
        "on_block only decides what happens instead."
    )
