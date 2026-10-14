#!/usr/bin/env python3
"""Generate docs/business/cpo-dashboard.html — the product dashboard for the CPO.

A self-contained HTML page (no CDN, no network), generated entirely from the sources of truth:

- `neuroedge-roadmap.md` §0.1–§0.3, the increment table §0.2, the eight user-facing release
  milestones §0.5 (the page leads with them; technical detail is collapsed at the bottom), the
  task tables and exit criteria of every increment §4–§8, A1–A12 (Q-39: a single roadmap);
- `TODOS.md` (deliberate deferrals, activation triggers);
- `neuroedge-prd.md` §15 (decisions not yet fully decided, the five most recent decisions);
- `CHANGELOG.md` `[Unreleased]` (recent changes).

Never edit the generated file by hand. The date on the page comes from the roadmap's "Last updated",
not the machine clock, so the output is deterministic and `--check` does not go stale daily.

    python3 scripts/gen_cpo_dashboard.py           # write the file
    python3 scripts/gen_cpo_dashboard.py --check   # write nothing; exit 1 if stale
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
ROADMAP = ROOT / "roadmap" / "neuroedge-roadmap.md"
TODOS = ROOT / "TODOS.md"
PRD = ROOT / "roadmap" / "neuroedge-prd.md"
CHANGELOG = ROOT / "CHANGELOG.md"
TARGET = ROOT / "docs" / "business" / "cpo-dashboard.html"

DATE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
INC = re.compile(r"\b(I\d+[a-z]?) —")

# Task states, by roadmap icon (CONTRIBUTING.md §8.2).
STATES = (
    ("done", "✅", "Done"),
    ("partial", "🟡", "In progress / waiting"),
    ("todo", "⏳", "Not started"),
    ("deferred", "⏸", "Deliberately deferred"),
    ("blocked", "🔴", "Blocked"),
)
STATE_LABEL = {key: label for key, _, label in STATES}


# --- reading Markdown ------------------------------------------------------------------------------


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def plain(text: str) -> str:
    """One-line Markdown → plain text (drops links, **, `, <br>)."""
    text = LINK.sub(r"\1", text).replace("<br>", " ")
    return re.sub(r"\*\*|`|\*", "", text).strip()


def inline(text: str) -> str:
    """One-line Markdown → safe HTML: `code` → <code>, **bold** → <b>, link → its text."""
    text = html.escape(LINK.sub(r"\1", text).replace("<br>", " "), quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)


def between(lines: list[str], start: str, end: str) -> list[str]:
    i = next(n for n, line in enumerate(lines) if line.startswith(start))
    j = next(n for n, line in enumerate(lines[i + 1 :], i + 1) if line.startswith(end))
    return lines[i:j]


def inc_id(text: str) -> str | None:
    """`I3` from "I3 — Gate on Box-3" or "4.4 I3 — …"; None if it is not an increment."""
    m = INC.search(plain(text))
    return m.group(1) if m else None


def inc_number(inc: str) -> int:
    return int(re.match(r"I(\d+)", inc).group(1))


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
    group: str
    increment: str | None


@dataclass
class Increment:
    milestone: str
    name: str
    forecast: str
    capability: str
    progress: str
    state: str
    deps: str
    release: str

    @property
    def id(self) -> str | None:
        return inc_id(self.name)


def roadmap_status(lines: list[str]) -> dict[str, str]:
    rows = {}
    for line in between(lines, "### 0.1", "### 0.2"):
        if line.startswith("| **"):
            cells = split_row(line)
            rows[plain(cells[0])] = cells[1]
            rows[plain(cells[0]) + " · notes"] = cells[2] if len(cells) > 2 else ""
    return rows


def roadmap_matrix(lines: list[str]) -> list[Increment]:
    part = between(lines, "### 0.2", "### 0.3")
    start = next(i for i, line in enumerate(part) if line.startswith("| Milestone |"))
    out, milestone = [], ""
    for line in part[start + 2 :]:
        if not line.startswith("|"):
            break
        cells = split_row(line) + [""] * 8
        milestone = plain(cells[0]) or milestone
        out.append(Increment(milestone, *cells[1:8]))
    return out


def roadmap_tasks(lines: list[str]) -> list[Task]:
    tasks: list[Task] = []
    group, columns = "", {}
    for line in lines:
        if line.startswith("### "):
            group = plain(line[4:])
            columns = {}
        elif line.startswith("| Task code"):
            columns = {plain(c): i for i, c in enumerate(split_row(line))}
        elif line.startswith("| **TSK-") and columns:
            cells = split_row(line)
            status_cell = cells[columns.get("Status", 4)]
            tasks.append(
                Task(
                    id=plain(cells[0]),
                    name=plain(cells[1]).split(" — ")[0][:110],
                    state=state_of(status_cell),
                    status=plain(status_cell)[:140],
                    owner=plain(cells[columns["Owner"]]) if "Owner" in columns else "",
                    group=group,
                    increment=inc_id(group),
                )
            )
    return tasks


def exit_criteria(lines: list[str]) -> list[tuple[str, int, int]]:
    """(section title, met, total) for each "Exit criteria" list."""
    out, group, done, total = [], "", 0, 0
    for line in lines + ["### "]:
        if line.startswith("### "):
            if total:
                out.append((group, done, total))
            group, done, total = plain(line[4:]), 0, 0
        elif re.match(r"- \[[ x]\] \*\*(Criterion|A\d+\*\* —)", line):
            total += 1
            done += line.startswith("- [x]")
    return out


def acceptance(lines: list[str]) -> list[tuple[str, str, bool]]:
    out = []
    for line in lines:
        m = re.match(r"- \[([ x])\] \*\*(A\d+)\*\* — (.*)", line)
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


# --- other sources ------------------------------------------------------------------------------


def todos() -> list[dict]:
    out, topic = [], ""
    for line in TODOS.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            topic = line[3:].strip()
        m = re.match(r"\| (\d+) \| (.*)", line)
        if m and topic != "Sources":
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
    """(code, title, status) — PRD §15 decisions not yet fully decided."""
    out = []
    lines = PRD.read_text(encoding="utf-8").splitlines()
    for line in between(lines, "## 15", "## Appendix"):
        if not line.startswith("| **Q-"):
            continue
        cells = split_row(line)
        status = plain(cells[2])
        if not status.startswith(("DECIDED", "DIRECTION DECIDED")) or "PARTIAL" in status:
            out.append((plain(cells[0]), plain(cells[1]), status))
    pending = sorted(set(re.findall(r"(?:waiting for|awaiting) \*{0,2}(Q-\d+)", "\n".join(lines))))
    known = {code for code, _, _ in out}
    for code in pending:
        if code not in known:
            out.append((code, "Mentioned as pending in the PRD", "WAITING"))
    return out


def recent_decisions(limit: int = 5) -> list[tuple[str, str, str]]:
    """(code, title, date) — the PRD §15 decisions with the highest numbers."""
    out = []
    lines = PRD.read_text(encoding="utf-8").splitlines()
    for line in between(lines, "## 15", "## Appendix"):
        if not line.startswith("| **Q-"):
            continue
        cells = split_row(line)
        found = DATE.search(cells[2])
        out.append((plain(cells[0]), plain(cells[1]), found.group(1) if found else ""))
    out.sort(key=lambda d: int(d[0].removeprefix("Q-")), reverse=True)
    return out[:limit]


def recent_changes(limit: int = 8) -> list[str]:
    lines = between(
        CHANGELOG.read_text(encoding="utf-8").splitlines(),
        "### [Unreleased]",
        "### Phase 1 Documentation Milestones",
    )
    out = []
    for line in lines:
        m = re.match(r"- \*\*(.+?)\*\*", line)
        if m:
            out.append(m.group(1))
        if len(out) == limit:
            break
    return out


# --- user-facing release milestones -----------------------------------------------------------


@dataclass
class Milestone:
    n: int
    name: str
    does: str
    why: str
    incs: list[str]
    who: str
    done: int = 0
    total: int = 0
    date: str | None = None
    after: str = ""
    state: str = "upcoming"

    @property
    def pct(self) -> int:
        return round(100 * self.done / self.total) if self.total else 0


def milestones(lines: list[str], matrix: list[Increment]) -> list[Milestone]:
    """The "User-facing release milestones" table (roadmap §0.5), joined to §0.2."""
    i = next(
        n for n, line in enumerate(lines) if line.startswith("#### User-facing release milestones")
    )
    out: list[Milestone] = []
    for line in lines[i + 1 :]:
        if line.startswith("#") or line.startswith("---"):
            break
        if not re.match(r"\| \d+ \|", line):
            continue
        c = split_row(line)
        incs = [x.strip() for x in plain(c[4]).split(",")]
        out.append(Milestone(int(c[0]), plain(c[1]), c[2], c[3], incs, plain(c[5])))
    by_id = {inc.id: inc for inc in matrix if inc.id}
    owner = {inc: m for m in out for inc in m.incs}
    missing = set(by_id) - set(owner)
    if missing or set(owner) - set(by_id):
        raise SystemExit(
            f"The release milestone table disagrees with §0.2: {sorted(missing or set(owner) - set(by_id))}"
        )
    for m in out:
        dates, refs, states = [], [], []
        for inc in m.incs:
            row = by_id[inc]
            a, b = (int(x) for x in re.findall(r"\d+", plain(row.progress))[:2])
            m.done, m.total = m.done + a, m.total + b
            found = DATE.findall(row.forecast)
            if found:
                dates.append(found[0])
            else:
                refs += [
                    r for r in re.findall(r"\bI\d+[a-z]?\b", plain(row.forecast)) if r not in m.incs
                ]
            states.append(state_of(row.state))
        if len(dates) == len(m.incs):
            m.date = max(dates)
        elif refs:
            m.after = "after " + max((owner[r] for r in refs if r in owner), key=lambda x: x.n).name
        if all(st == "done" for st in states):
            m.state = "done"
        elif m.done or any(st in ("done", "partial") for st in states):
            m.state = "active"
    return out


CODES = re.compile(r"\s*\((?=[^)]*(?:TSK-|Q-\d|§|#\d|RFC-|I\d))[^)]*\)")


def human(text: str) -> str:
    """Drop parenthesised internal codes — for readers who do not need the notation."""
    return re.sub(r"\s{2,}", " ", CODES.sub("", plain(text))).strip(" ·;")


# --- HTML --------------------------------------------------------------------------------------

CSS = """
:root{--bg:#f5f4f0;--surface:#fffefb;--line:#e6e3dc;--ink:#14130f;--ink2:#55534c;--ink3:#86837a;
--done:#1f8a4c;--done-bg:#e3f3e8;--active:#c77700;--active-bg:#fbefd9;--todo:#c9c6bd;--todo-bg:#efede7;
--deferred:#7a6fd6;--blocked:#c43d3d;--partial:#c77700;--accent:#2457c5;--accent-bg:#e5ecfb;--hero:#14130f;--hero-ink:#fffefb}
@media (prefers-color-scheme:dark){:root{--bg:#121210;--surface:#1b1a17;--line:#2f2d28;--ink:#f3f1ea;--ink2:#bdb9ad;
--ink3:#8a867c;--done:#4cc27b;--done-bg:#173322;--active:#f0a53a;--active-bg:#3a2c12;--todo:#4a4842;--todo-bg:#25241f;
--deferred:#9d93ef;--blocked:#ec6b6b;--partial:#f0a53a;--accent:#7aa2ff;--accent-bg:#1c2847;--hero:#f3f1ea;--hero-ink:#14130f}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1120px;margin:0 auto;padding:32px 16px 56px}
h1{font-size:28px;line-height:1.15;margin:0;letter-spacing:-.01em}
h2{font-size:18px;margin:0 0 4px}.lede{color:var(--ink2);margin:0 0 16px}
.top{display:flex;flex-wrap:wrap;gap:8px 24px;align-items:baseline;justify-content:space-between;margin-bottom:20px}
.tagline{color:var(--ink2);margin:6px 0 0;font-size:16px}.stamp{color:var(--ink3);font-size:13px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:18px;min-width:0}
.hero{background:var(--hero);color:var(--hero-ink);border:0;display:grid;grid-template-columns:1.3fr 1fr 1fr;gap:20px}
.hero .k{font-size:13px;opacity:.75;margin:0 0 6px}.hero .big{font-size:34px;font-weight:700;line-height:1.1;margin:0}
.hero .s{font-size:14px;opacity:.85;margin:6px 0 0}.hero .now{border-right:1px solid rgba(127,127,127,.35);padding-right:20px}
@media (max-width:820px){.hero{grid-template-columns:1fr}.hero .now{border-right:0;border-bottom:1px solid rgba(127,127,127,.35);padding:0 0 16px}}
.journey{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(320px,100%),1fr));gap:14px}
.ms{border:1px solid var(--line);border-radius:12px;padding:16px;background:var(--surface);display:flex;flex-direction:column;gap:8px;min-width:0}
.ms.launch{border:2px solid var(--accent)}
.ms h3{font-size:16px;margin:0;display:flex;gap:10px;align-items:center}
.num{flex:none;width:28px;height:28px;border-radius:50%;display:inline-grid;place-items:center;font-size:13px;font-weight:700;
background:var(--todo-bg);color:var(--ink2)}
.done .num{background:var(--done);color:#fff}.active .num{background:var(--active);color:#fff}
.ms p{margin:0}.ms .does{color:var(--ink)}.ms .why{color:var(--ink2);font-size:13px}
.meta{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center;font-size:13px;color:var(--ink2);margin-top:auto}
.pill{display:inline-block;font-size:12px;font-weight:600;padding:2px 9px;border-radius:999px;white-space:nowrap}
.pill.done{background:var(--done-bg);color:var(--done)}.pill.active{background:var(--active-bg);color:var(--active)}
.pill.upcoming{background:var(--todo-bg);color:var(--ink2)}.pill.launch{background:var(--accent-bg);color:var(--accent)}
.prog{height:8px;border-radius:999px;background:var(--todo-bg);overflow:hidden}
.prog span{display:block;height:100%;background:var(--done);border-radius:999px}
.active .prog span{background:var(--active)}
.later{margin-top:14px}.later summary{cursor:pointer;color:var(--ink2);font-weight:600}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}@media (max-width:820px){.grid2{grid-template-columns:1fr}}
.grid2>*{min-width:0}
ol.steps,ul.steps{margin:8px 0 0;padding-left:20px}.steps li{margin:6px 0}
.health{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(170px,100%),1fr));gap:12px}
.health div{border:1px solid var(--line);border-radius:10px;padding:12px}.health b{display:block;font-size:22px}
.health span{color:var(--ink2);font-size:13px}
.tl{overflow-x:auto}.tl svg{display:block;min-width:720px}
details.tech{margin-top:8px}details.tech>summary{cursor:pointer;font-weight:600;font-size:16px;padding:6px 0}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:7px 8px;border-top:1px solid var(--line);vertical-align:top;font-size:13px}
th{color:var(--ink2);font-weight:600;font-size:12px;border-top:0}td.r,th.r{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
code{font:12px ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--bg);padding:1px 4px;border-radius:4px}
.scroll{overflow-x:auto}.legend{display:flex;flex-wrap:wrap;gap:14px;color:var(--ink2);font-size:12px;margin:0 0 10px}
.sw{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.bar{display:flex;gap:2px;height:12px;min-width:120px}.bar span{display:block;height:100%}
.bar span:first-child{border-radius:4px 0 0 4px}.bar span:last-child{border-radius:0 4px 4px 0}.bar span:only-child{border-radius:4px}
.foot{color:var(--ink3);font-size:12px;margin-top:28px}
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


STATE_TEXT = {"done": "Done", "active": "In progress", "upcoming": "Not started"}


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def en_date(d: str) -> str:
    y, m, day = d.split("-")
    return f"{MONTHS[int(m) - 1]} {int(day)}, {y}"


def timeline(ms: list[Milestone], today: str, launch: set[int]) -> str:
    """Dated milestones on one time axis (SVG); labels are tiered so they do not overlap."""
    dated = sorted((m for m in ms if m.date), key=lambda m: m.date)
    dates = sorted({m.date for m in dated} | {today})
    first, last = date.fromisoformat(dates[0]), date.fromisoformat(dates[-1])
    span = max((last - first).days, 1)
    width, left, right, axis = 1080, 90, 90, 96
    lanes = [62, 30, 132, 164]  # two lanes above the axis, two below

    def x(d: str) -> float:
        return left + (date.fromisoformat(d) - first).days / span * (width - left - right)

    out = [
        f'<line x1="{left - 40}" y1="{axis}" x2="{width - right + 40}" y2="{axis}" stroke="var(--line)" '
        'stroke-width="3" stroke-linecap="round"/>',
        f'<line x1="{x(today):.1f}" y1="{axis - 18}" x2="{x(today):.1f}" y2="{axis + 18}" stroke="var(--accent)" '
        'stroke-width="2" stroke-dasharray="4 3"/>',
        f'<text x="{x(today):.1f}" y="{axis + 34}" text-anchor="middle" font-size="12" font-weight="600" '
        'fill="var(--accent)">today</text>',
    ]
    ends = [float("-inf")] * len(lanes)
    ends[2] = x(today) + 30  # leave room for the "today" label
    for m in dated:
        cx = x(m.date)
        label = f"{m.n}. {m.name}"
        half = max(len(label) * 3.6, len(en_date(m.date)) * 3.2) + 8
        lane = next((k for k in range(len(lanes)) if ends[k] < cx - half), 0)
        ends[lane] = cx + half
        y = lanes[lane]
        color = {"done": "var(--done)", "active": "var(--active)"}.get(m.state, "var(--ink3)")
        big = m.n in launch
        if big:
            color = "var(--accent)"
        tip = y + 10 if y < axis else y - 26
        out.append(
            f'<line x1="{cx:.1f}" y1="{axis}" x2="{cx:.1f}" y2="{tip}" stroke="var(--line)" stroke-width="1"/>'
        )
        out.append(
            f'<circle cx="{cx:.1f}" cy="{axis}" r="{8 if big else 6}" fill="{color}" stroke="var(--surface)" '
            f'stroke-width="2"><title>{html.escape(m.name)} — {m.date}</title></circle>'
        )
        out.append(
            f'<text x="{cx:.1f}" y="{y - 14}" text-anchor="middle" font-size="12" font-weight="{700 if big else 500}" '
            f'fill="var(--ink)">{html.escape(label)}</text>'
            f'<text x="{cx:.1f}" y="{y}" text-anchor="middle" font-size="11" fill="var(--ink3)">{en_date(m.date)}</text>'
        )
    return (
        f'<div class="tl"><svg viewBox="0 0 {width} 180" width="100%" role="img" '
        f'aria-label="Timeline of release milestones">{"".join(out)}</svg></div>'
    )


def milestone_card(m: Milestone, launch: set[int]) -> str:
    when = en_date(m.date) if m.date else html.escape(m.after or "no date yet")
    badge = '<span class="pill launch">Launch</span>' if m.n in launch else ""
    return (
        f'<article class="ms {m.state}{" launch" if m.n in launch else ""}">'
        f'<h3><span class="num">{m.n}</span>{html.escape(m.name)}</h3>'
        f'<p class="does">{inline(m.does)}</p><p class="why">{inline(m.why)}</p>'
        f'<div class="prog" role="img" aria-label="{m.pct}% of the work done"><span style="width:{m.pct}%"></span></div>'
        f'<div class="meta"><span class="pill {m.state}">{STATE_TEXT[m.state]}</span>{badge}'
        f"<span>{when}</span><span>{m.pct}% done</span><span>{html.escape(m.who)}</span></div></article>"
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
    ms = milestones(lines, matrix)

    updated = DATE.search(status["Last updated"]).group(1)
    today = date.fromisoformat(updated)

    public = next(m for m in ms if m.who.startswith("Everyone"))
    v10 = next(m for m in ms if "v1.0" in m.name)
    launch = {public.n, v10.n}
    current = next((m for m in ms if m.state != "done"), ms[-1])

    def days(m: Milestone) -> str:
        return f"{(date.fromisoformat(m.date) - today).days} days left" if m.date else m.after

    hero = (
        f'<section class="card hero" aria-label="Summary">'
        f'<div class="now"><p class="k">Today</p><p class="big">Milestone {current.n}: {html.escape(current.name)}</p>'
        f'<p class="s">{current.pct}% done · {STATE_TEXT[current.state].lower()}</p></div>'
        f'<div><p class="k">Usable by outsiders</p><p class="big">{en_date(public.date) if public.date else "—"}</p>'
        f'<p class="s">{html.escape(public.name)} · {days(public)}</p></div>'
        f'<div><p class="k">v1.0 — ready to ship in products</p><p class="big">{en_date(v10.date) if v10.date else "—"}</p>'
        f'<p class="s">{days(v10)}</p></div></section>'
    )

    core = [m for m in ms if m.n <= v10.n]
    after = [m for m in ms if m.n > v10.n]
    journey = (
        '<section class="card"><h2>The journey to a usable product</h2>'
        '<p class="lede">Each milestone is something a user can do. Dates are the team’s forecast; if one slips, the date moves and the scope is not cut.</p>'
        f"{timeline(ms, updated, launch)}"
        f'<div class="journey">{"".join(milestone_card(m, launch) for m in core)}</div>'
        f'<details class="later"><summary>After v1.0 — {len(after)} milestones: '
        f"{html.escape(' · '.join(m.name for m in after))}</summary>"
        f'<div class="journey" style="margin-top:12px">{"".join(milestone_card(m, launch) for m in after)}</div>'
        "</details></section>"
    )

    blockers = [
        human(b)
        for b in plain(status["Non-technical blockers · notes"]).replace("🔴", "").split(" · ")
    ]
    nexts = "".join(f"<li>{inline(item)}</li>" for item in card.get("3", []))
    dec = "".join(
        f'<li>{html.escape(t)} — <span class="stamp">{html.escape(s[:40])}</span></li>'
        for _, t, s in decisions
    )
    asks = "".join(f"<li>{html.escape(b[:1].upper() + b[1:])}</li>" for b in blockers if b)
    actions = (
        '<section class="card"><h2>Needs the product owner</h2><p class="lede">Things only a person can do; the team is waiting.</p>'
        f'<ul class="steps">{asks}</ul>'
        + (
            f'<p style="margin:12px 0 0"><b>Decisions still open</b></p><ul class="steps">{dec}</ul>'
            if dec
            else ""
        )
        + "</section>"
    )

    v1_tasks = [t for t in tasks if t.increment and inc_number(t.increment) <= 7]
    done_v1 = sum(t.state == "done" for t in v1_tasks)
    ci = re.search(r"PASS (\d+)/(\d+) · SKIP (\d+)", plain(status["Core CI status"]))
    passed = sum(ok for _, _, ok in accept)
    health = (
        '<section class="card"><h2>Health</h2><div class="health">'
        f"<div><b>{round(100 * done_v1 / len(v1_tasks))}%</b><span>of the work to v1.0 done ({done_v1}/{len(v1_tasks)})</span></div>"
        f"<div><b>{ci.group(1) if ci else '?'}</b><span>automated tests passing, {ci.group(3) if ci else '?'} skipped</span></div>"
        f"<div><b>{passed}/{len(accept)}</b><span>v1.0 acceptance criteria met</span></div>"
        f"<div><b>{len(todo_items)}</b><span>deliberate deferrals, each with an activation trigger</span></div>"
        "</div></section>"
    )

    def stamp(day: str) -> str:
        return f' — <span class="stamp">{en_date(day)}</span>' if day else ""

    recent = "".join(
        f"<li><b>{html.escape(code)}</b> · {html.escape(title)}{stamp(day)}</li>"
        for code, title, day in recent_decisions()
    )
    decided = (
        '<section class="card"><h2>Latest decisions</h2>'
        '<p class="lede">The five newest entries of the decision log (PRD §15).</p>'
        f'<ul class="steps">{recent}</ul></section>'
    )

    feats = []
    for line in between(
        CHANGELOG.read_text(encoding="utf-8").splitlines(),
        "#### Added",
        "#### Changed",
    ):
        m = re.match(r"- \*\*(.+?)\*\*", line)
        if m:
            text = m.group(1).split(" — ", 1)[-1]
            text = human(text).rstrip(".")
            feats.append(html.escape(text[:1].upper() + text[1:]))
    shipped = (
        '<section class="card"><h2>New capabilities in place</h2><p class="lede">From the CHANGELOG, not yet released externally.</p>'
        f'<ul class="steps">{"".join(f"<li>{f}</li>" for f in feats[:6])}</ul></section>'
    )

    # Technical detail for the team — keeps every figure of roadmap §0.2.
    by_inc: dict[str, dict[str, int]] = {}
    for task in tasks:
        if task.increment:
            by_inc.setdefault(task.increment, {}).setdefault(task.state, 0)
            by_inc[task.increment][task.state] += 1
    crit = {inc_id(name): (d, n) for name, d, n in criteria if inc_id(name)}
    owner = {inc: m for m in ms for inc in m.incs}
    rows = []
    for inc in matrix:
        counts = by_inc.get(inc.id, {}) if inc.id else {}
        bar = stacked_bar(counts, plain(inc.name)) if counts else "—"
        ec = crit.get(inc.id) if inc.id else None
        mname = f"{owner[inc.id].n}. {owner[inc.id].name}" if inc.id in owner else ""
        rows.append(
            f"<tr><td>{html.escape(mname)}</td><td>{inline(inc.name)}</td><td>{inline(inc.forecast)}</td>"
            f'<td class="r"><b>{inline(inc.progress)}</b></td><td>{bar}</td>'
            f'<td class="r">{f"{ec[0]}/{ec[1]}" if ec else "—"}</td><td>{inline(inc.state)}</td></tr>'
        )
    waiting = [t for t in tasks if t.state in ("partial", "blocked")]
    wait_rows = "".join(
        f"<tr><td><code>{t.id}</code></td><td>{html.escape(t.name)}</td><td>{html.escape(t.status)}</td></tr>"
        for t in waiting
    )
    dated = sorted((t for t in todo_items if t["date"]), key=lambda t: t["date"])
    todo_rows = "".join(
        f'<tr><td class="r">#{t["n"]}</td><td>{html.escape(t["title"])}</td><td>{inline(t["trigger"])[:300]}</td></tr>'
        for t in dated + [t for t in todo_items if not t["date"]]
    )
    tech = (
        '<section class="card"><details class="tech"><summary>Technical detail for the team</summary>'
        f'<p class="lede">Increments, tasks and deferrals under the roadmap’s own codes; the page above only groups them into milestones.</p>{legend()}'
        '<div class="scroll"><table><thead><tr><th>Milestone</th><th>Increment</th><th>Forecast</th><th class="r">Progress</th>'
        '<th>Tasks by status</th><th class="r">Exit criteria</th><th>Status</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
        f'<h3>The team’s next steps (handoff card, in order)</h3><ol class="steps">{nexts}</ol>'
        f'<h3>Tasks in progress or waiting on a person</h3><div class="scroll"><table><tbody>{wait_rows}</tbody></table></div>'
        f'<h3>Deliberate deferrals ({len(todo_items)})</h3><div class="scroll"><table><tbody>{todo_rows}</tbody></table></div>'
        "</details></section>"
    )

    return f"""<!doctype html>
<!-- GENERATED by scripts/gen_cpo_dashboard.py — do not edit by hand. Check: --check -->
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NeuroEdge — Product dashboard</title><style>{CSS}</style></head><body><main>
<header class="top"><div><h1>NeuroEdge</h1>
<p class="tagline">Where an idea becomes a physical AI product — build it, run it safely, share it and sell it (Q-72).</p></div>
<span class="stamp">CPO dashboard · figures as of {en_date(updated)}</span></header>
{hero}
{journey}
<div class="grid2">{actions}{shipped}</div>
{decided}
{health}
{tech}
<p class="foot">Generated by <code>scripts/gen_cpo_dashboard.py</code> from <code>roadmap/neuroedge-roadmap.md</code> (§0.1–§0.5, task tables),
<code>TODOS.md</code>, <code>roadmap/neuroedge-prd.md</code> §15 and <code>CHANGELOG.md</code>. Do not edit this page by hand.
Overall architecture: <a href="kien-truc-tong-the.html">kien-truc-tong-the.html</a>.</p>
</main></body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="write nothing; exit 1 if the file is stale"
    )
    args = parser.parse_args()
    content = render()
    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != content:
            print(
                f"{TARGET.relative_to(ROOT)} is stale. Run: python3 scripts/gen_cpo_dashboard.py",
                file=sys.stderr,
            )
            return 1
        print(f"{TARGET.relative_to(ROOT)} matches its source")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(content, encoding="utf-8")
    print(f"Wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
