#!/usr/bin/env python3
"""Sinh docs/business/cpo-dashboard.html — dashboard sản phẩm cho CPO.

Một trang HTML tự chứa (không CDN, không mạng), sinh hoàn toàn từ nguồn sự thật:

- `neuroedge-roadmap.md` §0.1–§0.3, bảng task §4–§8, tiêu chí ra, A1–A9;
- `TODOS.md` (việc hoãn có chủ ý, mốc kích hoạt);
- `neuroedge-prd.md` §15 (quyết định chưa chốt hẳn);
- `CHANGELOG.md` `[Chưa phát hành]` (thay đổi gần đây);
- Phụ lục C của `draft-ke-hoach-mo-rong-robot-fofoca.md` (quyết định chờ `Q-N`).

Không sửa tay tệp sinh ra. Ngày trên trang lấy từ "Lần cập nhật cuối" của roadmap,
không lấy đồng hồ máy, nên kết quả tất định và `--check` không báo lệch mỗi ngày.

    python3 scripts/gen_cpo_dashboard.py           # ghi tệp
    python3 scripts/gen_cpo_dashboard.py --check   # không ghi; thoát 1 nếu lệch
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "neuroedge-roadmap.md"
TODOS = ROOT / "TODOS.md"
PRD = ROOT / "neuroedge-prd.md"
CHANGELOG = ROOT / "CHANGELOG.md"
ROBOT_PLAN = ROOT / "draft-ke-hoach-mo-rong-robot-fofoca.md"
TARGET = ROOT / "docs" / "business" / "cpo-dashboard.html"

DATE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")

# Trạng thái task, theo icon của roadmap (CONTRIBUTING.md §8.2).
STATES = (
    ("done", "✅", "Xong"),
    ("partial", "🟡", "Đang làm / chờ"),
    ("todo", "⏳", "Chưa bắt đầu"),
    ("deferred", "⏸", "Hoãn có chủ ý"),
)
STATE_LABEL = {key: label for key, _, label in STATES}


# --- đọc Markdown ------------------------------------------------------------------------------


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def plain(text: str) -> str:
    """Markdown một dòng → chữ thường (bỏ link, **, `, <br>)."""
    text = LINK.sub(r"\1", text).replace("<br>", " ")
    return re.sub(r"\*\*|`|\*", "", text).strip()


def inline(text: str) -> str:
    """Markdown một dòng → HTML an toàn: `mã` → <code>, **đậm** → <b>, link → chữ."""
    text = html.escape(LINK.sub(r"\1", text).replace("<br>", " "), quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)


def between(lines: list[str], start: str, end: str) -> list[str]:
    i = next(n for n, line in enumerate(lines) if line.startswith(start))
    j = next(n for n, line in enumerate(lines[i + 1 :], i + 1) if line.startswith(end))
    return lines[i:j]


def state_of(cell: str) -> str:
    for key, icon, _ in STATES:
        if icon in cell:
            return key
    return "todo"


# --- roadmap -----------------------------------------------------------------------------------


@dataclass
class Task:
    id: str
    name: str
    state: str
    status: str
    owner: str
    sprint: str


@dataclass
class Sprint:
    milestone: str
    name: str
    period: str
    focus: str
    progress: str
    state: str


def roadmap_status(lines: list[str]) -> dict[str, str]:
    rows = {}
    for line in between(lines, "### 0.1", "### 0.2"):
        if line.startswith("| **"):
            cells = split_row(line)
            rows[plain(cells[0])] = cells[1]
            rows[plain(cells[0]) + " · ghi chú"] = cells[2] if len(cells) > 2 else ""
    return rows


def roadmap_matrix(lines: list[str]) -> list[Sprint]:
    part = between(lines, "### 0.2", "### 0.3")
    start = next(i for i, line in enumerate(part) if line.startswith("| Mốc |"))
    out, milestone = [], ""
    for line in part[start + 2 :]:
        if not line.startswith("|"):
            break
        cells = split_row(line)
        milestone = plain(cells[0]) or milestone
        out.append(Sprint(milestone, *cells[1:6]))
    return out


def roadmap_tasks(lines: list[str]) -> list[Task]:
    tasks: list[Task] = []
    sprint, columns = "", {}
    for line in lines:
        if line.startswith("### "):
            sprint = plain(line[4:])
            columns = {}
        elif line.startswith("| Mã Task") or line.startswith("| Mã task"):
            columns = {plain(c): i for i, c in enumerate(split_row(line))}
        elif line.startswith("| **TSK-") and columns:
            cells = split_row(line)
            status_cell = cells[columns.get("Trạng thái", 4)]
            tasks.append(
                Task(
                    id=plain(cells[0]),
                    name=plain(cells[1]).split(" — ")[0][:110],
                    state=state_of(status_cell),
                    status=plain(status_cell)[:140],
                    owner=plain(cells[columns["Người"]]) if "Người" in columns else "",
                    sprint=sprint,
                )
            )
    return tasks


def exit_criteria(lines: list[str]) -> list[tuple[str, int, int]]:
    """(sprint, đạt, tổng) cho mỗi danh sách "Tiêu chí ra"."""
    out, sprint, done, total = [], "", 0, 0
    for line in lines + ["### "]:
        if line.startswith("### "):
            if total:
                out.append((sprint, done, total))
            sprint, done, total = plain(line[4:]), 0, 0
        elif re.match(r"- \[[ x]\] \*\*Tiêu chí", line):
            total += 1
            done += line.startswith("- [x]")
    return out


def acceptance(lines: list[str]) -> list[tuple[str, str, bool]]:
    out = []
    for line in lines:
        m = re.match(r"- \[([ x])\] \*\*(A\d)\*\* — (.*)", line)
        if m:
            out.append((m.group(2), plain(m.group(3)), m.group(1) == "x"))
    return out


def handoff(lines: list[str]) -> dict[str, list[str]]:
    card = between(lines, "### 0.3", "### 0.4")
    groups: dict[str, list[str]] = {}
    current = None
    for line in card:
        body = line.strip().strip("│").rstrip()
        m = re.match(r"\s*(\d)\. (\S+)", body)
        if m and m.group(2).isalpha() and m.group(2).isupper() and len(m.group(2)) >= 3:
            current = m.group(1)
            groups[current] = []
            continue
        if current is None:
            continue
        item = body.strip()
        if not item or item.startswith(("┌", "├", "└", "```")):
            continue
        if re.match(r"(•|\d\.)\s", item):
            groups[current].append(re.sub(r"^(•|\d\.)\s+", "", item))
        elif groups[current]:
            groups[current][-1] += " " + item
    return groups


# --- các nguồn khác ------------------------------------------------------------------------------


def todos() -> list[dict]:
    out, topic = [], ""
    for line in TODOS.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            topic = line[3:].strip()
        m = re.match(r"\| (\d+) \| (.*)", line)
        if m and topic != "Nguồn":
            cells = split_row(line)
            title = re.search(r"\*\*(.+?)\*\*", cells[1])
            trigger = cells[-1]
            dates = DATE.findall(trigger)
            out.append(
                {
                    "n": int(cells[0]),
                    "topic": topic,
                    "title": plain(title.group(1) if title else cells[1])[:120],
                    "trigger": trigger,
                    "date": min(dates) if dates else None,
                }
            )
    return out


def open_decisions() -> list[tuple[str, str, str]]:
    """(mã, tiêu đề, trạng thái) — quyết định PRD §15 chưa chốt hẳn."""
    out = []
    lines = PRD.read_text(encoding="utf-8").splitlines()
    for line in between(lines, "## 15", "## Phụ lục"):
        if not line.startswith("| **Q-"):
            continue
        cells = split_row(line)
        status = plain(cells[2])
        if not status.startswith("ĐÃ CHỐT") or "MỘT PHẦN" in status:
            out.append((plain(cells[0]), plain(cells[1]), status))
    pending = sorted(set(re.findall(r"chờ \*{0,2}(Q-\d+)", "\n".join(lines))))
    known = {code for code, _, _ in out}
    for code in pending:
        if code not in known:
            out.append((code, "Được nhắc là đang chờ trong PRD", "CHỜ"))
    return out


def robot_decisions() -> list[str]:
    if not ROBOT_PLAN.exists():
        return []
    lines = ROBOT_PLAN.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("## Phụ lục C"))
    out = []
    for line in lines[start:]:
        m = re.match(r"\| (\d+) \| (.*)", line)
        if m:
            out.append(plain(split_row(line)[1]))
    return out


def recent_changes(limit: int = 8) -> list[str]:
    lines = between(
        CHANGELOG.read_text(encoding="utf-8").splitlines(), "### [Chưa phát hành]", "### Mốc"
    )
    out = []
    for line in lines:
        m = re.match(r"- \*\*(.+?)\*\*", line)
        if m:
            out.append(m.group(1))
        if len(out) == limit:
            break
    return out


# --- HTML --------------------------------------------------------------------------------------

CSS = """
:root{--bg:#f6f6f4;--surface:#fcfcfb;--line:#e4e3de;--ink:#0b0b0b;--ink2:#52514e;--ink3:#7a7974;
--done:#0ca30c;--partial:#eda100;--todo:#c9c8c2;--deferred:#9085e9;--critical:#d03b3b;--accent:#2a78d6}
@media (prefers-color-scheme:dark){:root{--bg:#121211;--surface:#1a1a19;--line:#33332f;--ink:#fff;
--ink2:#c3c2b7;--ink3:#8f8e86;--done:#0ca30c;--partial:#c98500;--todo:#4a4a45;--deferred:#9085e9;
--critical:#e66767;--accent:#3987e5}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:22px;margin:0}h2{font-size:15px;margin:0 0 12px;letter-spacing:.01em}
.sub{color:var(--ink2);margin:4px 0 20px}.card{background:var(--surface);border:1px solid var(--line);
border-radius:10px;padding:16px;margin-bottom:16px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(150px,100%),1fr));gap:12px;margin-bottom:16px}
.kpis>*,.grid2>*,.card{min-width:0}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px}
.kpi .v{font-size:26px;font-weight:650;line-height:1.2}.kpi .l{color:var(--ink2);font-size:12px}
.kpi .n{color:var(--ink3);font-size:12px;margin-top:4px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media (max-width:820px){.grid2{grid-template-columns:1fr}}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:7px 8px;border-top:1px solid var(--line);vertical-align:top}
th{color:var(--ink2);font-weight:600;font-size:12px;border-top:0}td{font-size:13px}
.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
td code{white-space:nowrap}code{font:12px ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--bg);padding:1px 4px;border-radius:4px}
.legend{display:flex;flex-wrap:wrap;gap:14px;color:var(--ink2);font-size:12px;margin:0 0 10px}
.sw{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.bar{display:flex;gap:2px;height:14px;min-width:120px}.bar span{display:block;height:100%}
.bar span:first-child{border-radius:4px 0 0 4px}.bar span:last-child{border-radius:0 4px 4px 0}
.bar span:only-child{border-radius:4px}
.tag{display:inline-block;font-size:11px;padding:1px 7px;border-radius:999px;border:1px solid var(--line);color:var(--ink2);white-space:nowrap}
.tag.done{color:var(--done);border-color:var(--done)}.tag.crit{color:var(--critical);border-color:var(--critical)}
ul.plain{margin:0;padding-left:18px}ul.plain li{margin:3px 0}
details summary{cursor:pointer;color:var(--ink2);margin:6px 0}
.tl{position:relative;overflow-x:auto}.tl svg{display:block;min-width:640px}
.foot{color:var(--ink3);font-size:12px;margin-top:24px}
.scroll{overflow-x:auto}
"""


def stacked_bar(counts: dict[str, int], label: str) -> str:
    total = sum(counts.values()) or 1
    parts = []
    for key, _, name in STATES:
        n = counts.get(key, 0)
        if n:
            parts.append(
                f'<span style="flex:{n};background:var(--{key})" '
                f'title="{html.escape(label)}: {name} {n}/{total}"></span>'
            )
    return f'<div class="bar" role="img" aria-label="{html.escape(label)}">{"".join(parts)}</div>'


def legend() -> str:
    items = "".join(
        f'<span><span class="sw" style="background:var(--{key})"></span>{icon} {name}</span>'
        for key, icon, name in STATES
    )
    return f'<div class="legend">{items}</div>'


def timeline(points: list[tuple[str, str, bool]], today: str) -> str:
    """Các mốc có ngày tuyệt đối trên một trục thời gian (SVG)."""
    dates = sorted({d for d, _, _ in points} | {today})
    first, last = date.fromisoformat(dates[0]), date.fromisoformat(dates[-1])
    span = max((last - first).days, 1)
    width, left, right = 1100, 80, 110

    def x(d: str) -> float:
        return left + (date.fromisoformat(d) - first).days / span * (width - left - right)

    marks = [
        f'<line x1="{left}" y1="60" x2="{width - right}" y2="60" stroke="var(--line)" stroke-width="2"/>',
        f'<line x1="{x(today):.1f}" y1="20" x2="{x(today):.1f}" y2="100" stroke="var(--accent)" '
        f'stroke-width="2" stroke-dasharray="4 3"/>',
        f'<text x="{x(today):.1f}" y="14" text-anchor="middle" font-size="11" fill="var(--accent)">'
        f"hôm nay {today}</text>",
    ]
    for i, (d, name, hard) in enumerate(sorted(points)):
        up = i % 2 == 0
        y = (44 if (i // 2) % 2 == 0 else 26) if up else (84 if (i // 2) % 2 == 0 else 108)
        color = "var(--critical)" if hard else "var(--ink2)"
        marks.append(
            f'<circle cx="{x(d):.1f}" cy="60" r="5" fill="var(--surface)" stroke="{color}" '
            f'stroke-width="2"><title>{html.escape(name)} — {d}</title></circle>'
        )
        marks.append(
            f'<text x="{x(d):.1f}" y="{y}" text-anchor="middle" font-size="11" fill="var(--ink)">'
            f'{html.escape(name[:34])}</text><text x="{x(d):.1f}" y="{y + (-12 if up else 13)}" '
            f'text-anchor="middle" font-size="10" fill="var(--ink3)">{d}</text>'
        )
    return (
        f'<div class="tl"><svg viewBox="0 0 {width} 130" width="100%" role="img" '
        f'aria-label="Dòng thời gian các mốc">{"".join(marks)}</svg></div>'
    )


def render() -> str:
    lines = ROADMAP.read_text(encoding="utf-8").splitlines()
    status = roadmap_status(lines)
    matrix = roadmap_matrix(lines)
    tasks = roadmap_tasks(lines)
    criteria = exit_criteria(lines)
    accept = acceptance(lines)
    card = handoff(lines)
    todo_items = todos()
    decisions = open_decisions()
    robot = robot_decisions()
    changes = recent_changes()

    updated = DATE.search(status["Lần cập nhật cuối"]).group(1)
    today = date.fromisoformat(updated)

    # Mỗi mã task đếm một lần (một task đổi sprint thì xuất hiện ở cả hai bảng).
    unique: dict[str, Task] = {}
    for task in tasks:
        unique[task.id] = task
    phase1 = [t for t in unique.values() if re.match(r"TSK-S\d", t.id)]
    done = sum(t.state == "done" for t in phase1)

    ci = re.search(r"PASS (\d+)/(\d+) · SKIP (\d+)", plain(status["Trạng thái CI Lõi"]))
    m1_date = DATE.search(status["Cột mốc tiếp theo · ghi chú"] + status["Cột mốc tiếp theo"])
    m1_days = (date.fromisoformat(m1_date.group(1)) - today).days if m1_date else None
    blockers = plain(status["Chặn ngoài tầm kỹ thuật · ghi chú"])
    passed = sum(ok for _, _, ok in accept)

    kpis = [
        (
            f"{done}/{len(phase1)}",
            "Task Giai đoạn 1 đã xong",
            f"{round(100 * done / len(phase1))}% — Sprint 1→6",
        ),
        (
            f"{ci.group(1)}/{ci.group(2)}" if ci else "?",
            "Test CI lõi đạt",
            f"skip {ci.group(3)} — CI chặn mọi skip" if ci else "",
        ),
        (
            f"{m1_days} ngày" if m1_days is not None else "?",
            "Tới M1 (TTFV < 10 phút)",
            f"hạn {m1_date.group(1)}" if m1_date else "",
        ),
        (f"{passed}/{len(accept)}", "Tiêu chí nghiệm thu v1.0 (A1–A9)", "đạt khi đóng Sprint 6"),
        (
            str(len(decisions) + len(robot)),
            "Quyết định còn chờ",
            f"PRD §15: {len(decisions)} · bản nháp robot: {len(robot)}",
        ),
        (str(len(todo_items)), "Việc hoãn có mốc (TODOS)", "mỗi mục có mốc kích hoạt"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="v">{html.escape(v)}</div><div class="l">{html.escape(label)}</div>'
        f'<div class="n">{html.escape(n)}</div></div>'
        for v, label, n in kpis
    )

    # Ma trận sprint: tiến độ chính thức (§0.2) + phân rã theo task.
    by_sprint: dict[str, dict[str, int]] = {}
    for task in tasks:
        by_sprint.setdefault(task.sprint, {}).setdefault(task.state, 0)
        by_sprint[task.sprint][task.state] += 1
    crit = {name: (d, n) for name, d, n in criteria}

    def sprint_key(sp: Sprint) -> str | None:
        m = re.search(r"Sprint (\d)", plain(sp.name))
        needle = f"Sprint {m.group(1)} " if m else None
        if needle is None and sp.milestone.startswith("Khối ") and sp.milestone[-1] in "23":
            needle = sp.milestone
        return next((k for k in by_sprint if needle and needle in k), None)

    rows = []
    for sp in matrix:
        key = sprint_key(sp)
        counts = by_sprint.get(key, {}) if key else {}
        bar = (
            stacked_bar(counts, plain(sp.name)) if counts else '<span class="tag">theo khối</span>'
        )
        ec = crit.get(key) if key else None
        rows.append(
            f"<tr><td>{inline(sp.milestone)}</td><td>{inline(sp.name)}</td><td>{inline(sp.period)}</td>"
            f'<td class="num"><b>{inline(sp.progress)}</b></td><td>{bar}</td>'
            f'<td class="num">{f"{ec[0]}/{ec[1]}" if ec else "—"}</td><td>{inline(sp.state)}</td></tr>'
        )
    matrix_html = (
        '<div class="scroll"><table><thead><tr><th>Khối</th><th>Sprint / giai đoạn</th><th>Thời gian</th>'
        '<th class="num">Tiến độ (§0.2)</th><th>Task theo trạng thái</th><th class="num">Tiêu chí ra</th>'
        f"<th>Trạng thái</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )

    # Mốc có ngày tuyệt đối.
    points = []
    for sp in matrix:
        found = DATE.findall(sp.period)
        if found:
            points.append((found[0], f"Mở {plain(sp.name).split(' — ')[0]}", False))
    if m1_date:
        points.append((m1_date.group(1), "M1 — TTFV < 10 phút", True))
    gate = DATE.search(status.get("Hoãn có chủ ý · ghi chú", ""))
    if gate:
        points.append((gate.group(1), "Cổng nhu cầu (Q-20)", True))
    tl_html = timeline(points, updated)

    # Đã làm được, theo sprint.
    done_groups = []
    for key in by_sprint:
        items = [t for t in tasks if t.sprint == key and t.state == "done"]
        if items:
            lis = "".join(f"<li><code>{t.id}</code> {html.escape(t.name)}</li>" for t in items)
            done_groups.append(
                f"<details><summary><b>{html.escape(key)}</b> — {len(items)} task xong</summary>"
                f'<ul class="plain">{lis}</ul></details>'
            )

    # Pending — cần người.
    waiting = [t for t in unique.values() if t.state == "partial"]
    wait_rows = "".join(
        f"<tr><td><code>{t.id}</code></td><td>{html.escape(t.name)}</td><td>{html.escape(t.status)}</td>"
        f"<td>{html.escape(t.owner)}</td></tr>"
        for t in waiting
    )
    next_items = "".join(f"<li>{inline(item)}</li>" for item in card.get("3", []))
    doing_items = "".join(f"<li>{inline(item)}</li>" for item in card.get("2", []))
    dec_rows = "".join(
        f'<tr><td><code>{html.escape(c)}</code></td><td>{html.escape(t)}</td><td><span class="tag crit">'
        f"{html.escape(s[:60])}</span></td></tr>"
        for c, t, s in decisions
    )
    robot_items = "".join(f"<li>{html.escape(q)}</li>" for q in robot)

    # Hoãn có chủ ý: mốc có ngày lên trước.
    dated = sorted((t for t in todo_items if t["date"]), key=lambda t: t["date"])
    todo_rows = "".join(
        f'<tr><td class="num">#{t["n"]}</td><td>{html.escape(t["title"])}</td><td>{html.escape(t["topic"])}</td>'
        f"<td>{inline(t['trigger'])[:300]}</td></tr>"
        for t in dated + [t for t in todo_items if not t["date"]]
    )
    topics: dict[str, int] = {}
    for t in todo_items:
        topics[t["topic"]] = topics.get(t["topic"], 0) + 1
    topic_tags = " ".join(
        f'<span class="tag">{html.escape(k)} · {v}</span>' for k, v in topics.items()
    )

    changes_html = "".join(f"<li>{inline(c)}</li>" for c in changes)
    accept_html = "".join(
        f"<tr><td><code>{a}</code></td><td>{html.escape(t)}</td><td>"
        f'<span class="tag{" done" if ok else ""}">{"✅ đạt" if ok else "chưa"}</span></td></tr>'
        for a, t, ok in accept
    )

    return f"""<!doctype html>
<!-- SINH TỰ ĐỘNG bởi scripts/gen_cpo_dashboard.py — đừng sửa tay. Kiểm: --check -->
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NeuroEdge — Dashboard sản phẩm</title><style>{CSS}</style></head><body><main>
<h1>NeuroEdge — Dashboard sản phẩm</h1>
<p class="sub">Cho CPO · số liệu tới <b>{updated}</b> · pha: {inline(status["Pha đang thực thi"])}</p>

<section class="kpis" aria-label="Chỉ số chính">{kpi_html}</section>

<section class="card"><h2>Tiến độ theo sprint và khối</h2>{legend()}{matrix_html}</section>

<section class="card"><h2>Dòng thời gian các mốc</h2>
<p class="sub" style="margin-top:-6px">Đỏ = mốc có hạn cứng. {inline(status["Cột mốc tiếp theo · ghi chú"])}</p>{tl_html}</section>

<div class="grid2">
<section class="card"><h2>Pending — cần người</h2>
<p><b>Chặn ngoài tầm kỹ thuật:</b> {html.escape(blockers)}</p>
<p><b>Đang làm:</b></p><ul class="plain">{doing_items}</ul>
<p><b>Việc tiếp theo (đúng thứ tự):</b></p><ol class="plain">{next_items}</ol></section>
<section class="card"><h2>Quyết định còn chờ</h2>
<div class="scroll"><table><thead><tr><th>Mã</th><th>Quyết định</th><th>Trạng thái</th></tr></thead><tbody>{dec_rows}</tbody></table></div>
<details><summary>Bản nháp robot phân tầng — {len(robot)} câu hỏi chờ <code>Q-N</code></summary><ol class="plain">{robot_items}</ol></details>
</section></div>

<section class="card"><h2>Task đang dở hoặc chờ người</h2><div class="scroll"><table><thead><tr><th>Mã</th><th>Task</th>
<th>Trạng thái</th><th>Người</th></tr></thead><tbody>{wait_rows}</tbody></table></div></section>

<div class="grid2">
<section class="card"><h2>Đã làm được</h2>{"".join(done_groups)}</section>
<section class="card"><h2>Tiêu chí nghiệm thu v1.0</h2><table><tbody>{accept_html}</tbody></table></section>
</div>

<section class="card"><h2>Hoãn có chủ ý — {len(todo_items)} mục</h2><p>{topic_tags}</p>
<details><summary>Xem tất cả (mốc có ngày lên trước)</summary><div class="scroll"><table><thead><tr><th class="num">#</th>
<th>Hạng mục</th><th>Chủ đề</th><th>Mốc kích hoạt</th></tr></thead><tbody>{todo_rows}</tbody></table></div></details></section>

<section class="card"><h2>Thay đổi gần đây (CHANGELOG, chưa phát hành)</h2><ul class="plain">{changes_html}</ul></section>

<p class="foot">Sinh bởi <code>scripts/gen_cpo_dashboard.py</code> từ <code>neuroedge-roadmap.md</code>, <code>TODOS.md</code>,
<code>neuroedge-prd.md</code> §15, <code>CHANGELOG.md</code> và <code>draft-ke-hoach-mo-rong-robot-fofoca.md</code>.
Nguồn sự thật là các tệp đó; trang này không được sửa tay.</p>
</main></body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="không ghi; thoát 1 nếu tệp đã cũ")
    args = parser.parse_args()
    content = render()
    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != content:
            print(
                f"{TARGET.relative_to(ROOT)} đã cũ. Chạy: python3 scripts/gen_cpo_dashboard.py",
                file=sys.stderr,
            )
            return 1
        print(f"{TARGET.relative_to(ROOT)} khớp nguồn")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(content, encoding="utf-8")
    print(f"Đã ghi {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
