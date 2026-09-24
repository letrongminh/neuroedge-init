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
            "[bold red]fail-open[/bold red] (lỗi hoặc quá hạn → CHO PHÉP, "
            "trừ khi một tiêu chí đã biết là không đạt)"
        )
    return "[green]fail-closed[/green] (lỗi hoặc quá hạn → CHẶN)"


def render(explanation: GateExplanation, console: Console) -> None:
    gate = explanation.gate
    header = []
    if explanation.extends:
        header.append(f"Kế thừa từ: [cyan]{escape(explanation.extends)}[/cyan]")
    else:
        header.append("Gate gốc — không kế thừa gate nào")
    header.append(
        f"Phân cấp: {gate.inheritance_levels} cấp ({escape(' → '.join(gate.chain))}) · "
        f"Chính sách khi lỗi: {_fail_policy(gate.budget.get('fail', 'closed'))}"
    )
    console.print(
        Panel("\n".join(header), title=f"Gate: {escape(explanation.label)}", border_style="cyan")
    )

    console.print("\n[bold]1. Các tiêu chí đánh giá (evaluate):[/bold]")
    table = Table()
    table.add_column("Tiêu chí", style="cyan")
    table.add_column("Kiểu", style="magenta")
    table.add_column("Nguồn / Mô tả")
    for criterion in explanation.criteria:
        origin = f"(Từ {criterion.introduced_by})" if criterion.inherited else "(Mới)"
        detail = f" ({criterion.detail})" if criterion.detail else ""
        table.add_row(
            criterion.name,
            criterion.kind,
            f"[dim]{escape(origin)}[/dim] {escape(criterion.instructions)}{escape(detail)}",
        )
    console.print(table)

    console.print("\n[bold]2. Điều kiện cho phép (allow_when)[/bold] — phải đạt TẤT CẢ:")
    for clause in explanation.clauses:
        note = ""
        if clause.status == "tightened":
            note = (
                f" [yellow](cha cho phép {escape(clause.parent_admits)} — "
                f"con đã siết chặt)[/yellow]"
            )
        elif clause.status == "inherited":
            note = " [dim](kế thừa nguyên từ cha)[/dim]"
        elif explanation.parent is not None:
            note = " [dim](mới ở gate này)[/dim]"
        console.print(
            f"  [green]✓[/green] {escape(clause.criterion)} ∈ {escape(clause.admits)}{note}"
        )
    console.print(
        "  [dim]Tiêu chí không xác định được (mất mạng, không nhận ra lệnh) → CHẶN.[/dim]"
    )
    if gate.arguments:
        parent = explanation.parent.arguments if explanation.parent is not None else {}
        console.print(
            "\n[bold]Giới hạn tham số (arguments, RFC-0005)[/bold] — kiểm trước mọi tiêu chí:"
        )
        for name, limit in gate.arguments.items():
            bounds = ", ".join(f"{key}={value}" for key, value in limit.items() if key != "type")
            note = ""
            if name in parent and parent[name] != limit:
                note = " [yellow](con đã thu hẹp so với cha)[/yellow]"
            elif name in parent:
                note = " [dim](kế thừa nguyên từ cha)[/dim]"
            console.print(
                f"  [green]✓[/green] {escape(name)}: {escape(limit['type'])}"
                f"{escape(' · ' + bounds) if bounds else ''}{note}"
            )
        console.print("  [dim]Ngoài giới hạn → CHẶN argument_out_of_range, rồi on_block.[/dim]")

    console.print("\n[bold]3. Ngân sách & Hành vi khi bị chặn:[/bold]")
    p95, parent_p95 = explanation.p95, explanation.parent_p95
    if parent_p95 is None:
        budget_note = ""
    elif parent_p95 == p95:
        budget_note = f" (kế thừa nguyên từ cha {parent_p95} ms)"
    else:
        budget_note = f" (kế thừa và siết chặt từ cha {parent_p95} ms)"
    console.print(f"  • Ngân sách thời gian (p95): {p95} ms{escape(budget_note)}")

    on_block = gate.on_block
    behaviour = escape(str(on_block.get("action")))
    if on_block.get("to"):
        behaviour += f" → {escape(on_block['to'])}"
    if on_block.get("fallback_action"):
        behaviour += f" → chạy {escape(on_block['fallback_action'])} qua gate riêng của nó"
    console.print(f"  • Hành vi on_block: [bold]{behaviour}[/bold]")
    if on_block.get("message"):
        console.print(f'    Lời nhắn: "{escape(on_block["message"])}"')
    if on_block.get("confirms"):
        console.print(
            "    Người xác nhận trên thiết bị được thay cho: "
            f"[bold]{escape(', '.join(on_block['confirms']))}[/bold] — mọi điều kiện khác vẫn "
            "phải đạt; System 2 và client MCP không xác nhận được (RFC-0006)"
        )
    if explanation.on_block_changed:
        parent = explanation.parent.on_block
        was = escape(str(parent.get("action")))
        if parent.get("to"):
            was += f" → {escape(parent['to'])}"
        console.print(f"    [dim](cha: {was}; thay đổi đã được kiểm theo RFC-0004)[/dim]")
    console.print(
        "  • Khi bị chặn, hành động vật lý [bold]không[/bold] chạy — "
        "on_block chỉ quyết định việc xảy ra thay thế."
    )
