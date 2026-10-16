#!/usr/bin/env python3
"""Fill the progress blocks of docs/business/kien-truc-tong-the.html from the roadmap.

The architecture page is hand-drawn; only the blocks between
`<!-- GENERATED:<key> -->` and `<!-- /GENERATED:<key> -->` are written here, so progress shows
on the architecture itself and never goes stale. Every figure comes from
`roadmap/neuroedge-roadmap.md`: the status table §0.1, the increment table §0.2, the
user-facing release milestones §0.5, and the demand gate date.

Keys:

- `pulse` — the strip under the headline: date of the figures, current milestone, demand gate,
  tests, items waiting on a person;
- `layer-1` … `layer-5` — one progress bar per increment, on the architecture layer it builds
  (`LAYERS` below; every increment sits on exactly one layer);
- `journey` — the eight release milestones on a timeline, then as cards, then what is waiting
  on a person;
- `inc-<ID>` — the bare progress of one increment, e.g. `11 / 20`, for use inside a sentence;
- `today` — what a person can do today, from `docs/architecture/vi/00-overview.md` §6.1: works now,
  works in part, next; each with the command to try it, where it runs and its evidence.

Never edit a generated block by hand. The date comes from the roadmap's "Last updated", not the
machine clock, so the output is deterministic and `--check` does not go stale daily.

    python3 scripts/gen_architecture_progress.py           # rewrite the blocks
    python3 scripts/gen_architecture_progress.py --check   # write nothing; exit 1 if stale
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
TARGET = ROOT / "docs" / "business" / "kien-truc-tong-the.html"
OVERVIEW = ROOT / "docs" / "architecture" / "vi" / "00-overview.md"

DATE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
INC = re.compile(r"\b(I\d+[a-z]?) —")
BLOCK = re.compile(r"(<!-- GENERATED:([\w-]+) -->)(.*?)(<!-- /GENERATED:\2 -->)", re.S)

# Increment states, by roadmap icon (CONTRIBUTING.md §8.2).
STATES = (
    ("done", "✅"),
    ("partial", "🟡"),
    ("todo", "⏳"),
    ("deferred", "⏸"),
    ("blocked", "🔴"),
)
STATE_TEXT = {
    "done": "done",
    "partial": "in progress",
    "todo": "not started",
    "deferred": "deferred",
    "blocked": "blocked",
}

# The architecture layer each increment builds (page chapter 2, `00-overview.md` §2.1).
LAYERS = {
    1: ("I2d",),
    2: ("I2c",),
    3: ("I0", "I1", "I2a"),
    4: ("I2", "I2b", "I3", "I3a"),
    5: ("I2e", "I2f", "I6", "I7", "I8"),
}


# --- reading Markdown ------------------------------------------------------------------------------


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def plain(text: str) -> str:
    """One-line Markdown → plain text (drops links, **, `, <br>)."""
    text = LINK.sub(r"\1", text).replace("<br>", " ")
    return re.sub(r"\*\*|`|\*", "", text).strip()


def between(lines: list[str], start: str, end: str) -> list[str]:
    i = next(n for n, line in enumerate(lines) if line.startswith(start))
    j = next(n for n, line in enumerate(lines[i + 1 :], i + 1) if line.startswith(end))
    return lines[i:j]


def inc_id(text: str) -> str | None:
    """`I3` from "I3 — Gate on Box-3"; None if it is not an increment."""
    m = INC.search(plain(text))
    return m.group(1) if m else None


def state_of(cell: str) -> str:
    for key, icon in STATES:
        if icon in cell:
            return key
    return "todo"


CODES = re.compile(r"\s*\((?=[^)]*(?:TSK-|Q-\d|§|#\d|RFC-|I\d))[^)]*\)")


def human(text: str) -> str:
    """Drop parenthesised internal codes — for readers who do not need the notation."""
    return re.sub(r"\s{2,}", " ", CODES.sub("", plain(text))).strip(" ·;")


# --- roadmap -----------------------------------------------------------------------------------


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

    @property
    def title(self) -> str:
        return human(plain(self.name).split(" — ", 1)[-1])

    @property
    def counts(self) -> tuple[int, int]:
        a, b = (int(x) for x in re.findall(r"\d+", plain(self.progress))[:2])
        return a, b

    @property
    def status(self) -> str:
        return state_of(self.state)


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


def gate_date(lines: list[str]) -> str:
    """The date of the 8-week demand gate (roadmap decision table, Q-74)."""
    for line in lines:
        m = re.search(r"(20\d\d-\d\d-\d\d) demand gate outcome", line)
        if m:
            return m.group(1)
    raise SystemExit("The roadmap no longer names the date of the demand gate outcome")


@dataclass
class Milestone:
    n: int
    name: str
    incs: list[str]
    done: int = 0
    total: int = 0
    date: str | None = None
    when: str = ""
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
        out.append(Milestone(int(c[0]), plain(c[1]), [x.strip() for x in plain(c[4]).split(",")]))
    by_id = {inc.id: inc for inc in matrix if inc.id}
    owner = {inc: m for m in out for inc in m.incs}
    if set(by_id) != set(owner):
        raise SystemExit(
            f"The release milestone table disagrees with §0.2: {sorted(set(by_id) ^ set(owner))}"
        )
    for m in out:
        dates, refs, states = [], [], []
        for inc in m.incs:
            row = by_id[inc]
            a, b = row.counts
            m.done, m.total = m.done + a, m.total + b
            found = DATE.findall(row.forecast)
            if found:
                dates.append(found[0])
            else:
                refs += [
                    r for r in re.findall(r"\bI\d+[a-z]?\b", plain(row.forecast)) if r not in m.incs
                ]
            states.append(row.status)
        if len(dates) == len(m.incs):
            m.date = max(dates)
            m.when = en_date(m.date)
        elif refs:
            m.when = "after milestone " + str(max(owner[r].n for r in refs if r in owner))
        else:
            m.when = re.sub(r"\s*\([^)]*\)", "", plain(by_id[m.incs[0]].forecast))
        if all(st == "done" for st in states):
            m.state = "done"
        elif m.done or any(st in ("done", "partial") for st in states):
            m.state = "active"
    return out


@dataclass
class Capability:
    what: str
    how: str
    where: str
    status: str
    evidence: list[str]


CAPABILITY_STATES = ("done", "partial", "planned")
TASK = re.compile(r"^TSK-[A-Za-z0-9]+-\d+$")


def capabilities(roadmap: str) -> list[Capability]:
    """`00-overview.md` §6.1; every evidence names a file that exists or a roadmap task."""
    lines = OVERVIEW.read_text(encoding="utf-8").splitlines()
    part = between(lines, "### 6.1", "### 6.2")
    start = next(i for i, line in enumerate(part) if line.startswith("| Capability |"))
    out = []
    for line in part[start + 2 :]:
        if not line.startswith("|"):
            break
        what, how, where, status, evidence = split_row(line)
        status = plain(status)
        if status not in CAPABILITY_STATES:
            raise SystemExit(f"00-overview.md §6.1: status {status!r} of {plain(what)!r}")
        refs = [plain(ref) for ref in evidence.split(",") if plain(ref)]
        for ref in refs:
            known = f"**{ref}**" in roadmap if TASK.match(ref) else (ROOT / ref).exists()
            if not known:
                raise SystemExit(
                    f"00-overview.md §6.1: evidence {ref!r} of {plain(what)!r} not found"
                )
        if status == "planned" and not any(TASK.match(ref) for ref in refs):
            raise SystemExit(f"00-overview.md §6.1: planned {plain(what)!r} names no roadmap task")
        out.append(Capability(plain(what), plain(how), plain(where), status, refs))
    if not out:
        raise SystemExit("00-overview.md §6.1 has no capabilities")
    return out


# --- HTML --------------------------------------------------------------------------------------

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def en_date(d: str) -> str:
    y, m, day = d.split("-")
    return f"{MONTHS[int(m) - 1]} {int(day)}, {y}"


def bar(pct: int, label: str) -> str:
    return (
        f'<span class="bar" role="img" aria-label="{html.escape(label)}">'
        f'<i style="width:{pct}%"></i></span>'
    )


def inc_row(inc: Increment) -> str:
    a, b = inc.counts
    pct = round(100 * a / b) if b else 0
    label = f"{inc.id} — {inc.title}: {a} of {b} tasks done, {STATE_TEXT[inc.status]}"
    return (
        f'<div class="inc {inc.status}" title="{html.escape(label)}">'
        f'<span class="id">{inc.id}</span><span class="nm">{html.escape(inc.title)}</span>'
        f'{bar(pct, label)}<span class="nb">{a}/{b}</span></div>'
    )


def layer(n: int, by_id: dict[str, Increment]) -> str:
    rows = "".join(inc_row(by_id[i]) for i in LAYERS[n])
    return f'<div class="incs">{rows}</div>'


def pulse(status: dict[str, str], ms: list[Milestone], gate: str, today: date) -> str:
    current = next((m for m in ms if m.state != "done"), ms[-1])
    ci = re.search(r"PASS (\d+)/(\d+) · SKIP (\d+)", plain(status["Core CI status"]))
    waiting = re.search(r"(\d+) blocking", plain(status["Non-technical blockers"]))
    days = (date.fromisoformat(gate) - today).days
    cells = [
        ("Figures as of", en_date(today.isoformat()), "roadmap §0"),
        ("Now", f"{current.n} · {current.name}", f"{current.pct}% done"),
        ("8-week demand gate", en_date(gate), f"{days} days away"),
        (
            "Tests",
            f"{int(ci.group(1)):,} passing" if ci else "?",
            f"{ci.group(3)} skipped" if ci else "",
        ),
        (
            "Waiting on a person",
            f"{waiting.group(1)} items" if waiting else "none",
            '<a href="#s11">see chapter 11</a>',
        ),
    ]
    return (
        '<div class="pulse">'
        + "".join(
            f'<div><span class="k">{k}</span><b>{html.escape(v)}</b><span class="s">{s}</span></div>'
            for k, v, s in cells
        )
        + "</div>"
    )


def timeline(ms: list[Milestone], gate: str, today: str) -> str:
    """Dated milestones, today and the demand gate on one time axis."""
    points = [(m.date, f"{m.n} · {m.name}", m.state) for m in ms if m.date]
    every = sorted([d for d, _, _ in points] + [gate, today])
    first, last = date.fromisoformat(every[0]), date.fromisoformat(every[-1])
    span = max((last - first).days, 1)
    width, left, right, axis = 900, 70, 70, 74

    def x(d: str) -> float:
        return left + (date.fromisoformat(d) - first).days / span * (width - left - right)

    out = [f'<line x1="20" y1="{axis}" x2="{width - 20}" y2="{axis}" class="ax"/>']
    for d, label, cls, y in (
        (today, "today", "now", axis + 34),
        (gate, "demand gate", "gate", axis + 34),
    ):
        out.append(
            f'<line x1="{x(d):.1f}" y1="{axis - 16}" x2="{x(d):.1f}" y2="{axis + 16}" class="{cls}"/>'
            f'<text x="{x(d):.1f}" y="{y}" text-anchor="middle" class="tl-{cls}">{label}</text>'
            f'<text x="{x(d):.1f}" y="{y + 15}" text-anchor="middle" class="tl-d">{en_date(d)}</text>'
        )
    for k, (d, label, state) in enumerate(sorted(points)):
        y = 24 if k % 2 == 0 else 44
        cx = x(d)
        # Keep labels inside the frame: near an edge, hang them from the dot instead of centring.
        anchor, tx = (
            ("end", cx + 8)
            if cx > width - 200
            else ("start", cx - 8)
            if cx < 200
            else ("middle", cx)
        )
        short = label if len(label) <= 34 else label[:33].rstrip(" ,") + "…"
        out.append(
            f'<line x1="{cx:.1f}" y1="{y + 6}" x2="{cx:.1f}" y2="{axis}" class="tick"/>'
            f'<circle cx="{cx:.1f}" cy="{axis}" r="7" class="dot-{state}"><title>{html.escape(label)}</title></circle>'
            f'<text x="{tx:.1f}" y="{y}" text-anchor="{anchor}" class="tl-m">{html.escape(short)}</text>'
        )
    return (
        f'<div class="fig"><svg viewBox="0 0 {width} 140" role="img" '
        f'aria-label="Dated release milestones, today and the demand gate">{"".join(out)}</svg></div>'
    )


def journey(status: dict[str, str], ms: list[Milestone], gate: str, today: str) -> str:
    cards = "".join(
        f'<article class="ms {m.state}"><div class="ms-top"><span class="num">{m.n}</span>'
        f'<span class="when">{html.escape(m.when)}</span></div>'
        f"<h3>{html.escape(m.name)}</h3>"
        f"{bar(m.pct, f'{m.pct}% of the work done')}"
        f'<div class="ms-meta"><span>{m.pct}%</span><span>{", ".join(m.incs)}</span></div></article>'
        for m in ms
    )
    asks = [
        human(b)
        for b in plain(status["Non-technical blockers · notes"]).replace("🔴", "").split(" · ")
    ]
    waiting = "".join(f"<li>{html.escape(b[:1].upper() + b[1:])}</li>" for b in asks if b)
    return (
        f"{timeline(ms, gate, today)}"
        f'<div class="ms-grid">{cards}</div>'
        f'<div class="panel waiting"><h3>Waiting on a person</h3><ul>{waiting}</ul></div>'
    )


CHIP = {"done": "ok", "partial": "part", "planned": "plan"}
TODAY_GROUPS = (
    ("done", "Works now"),
    ("partial", "Works in part"),
    ("planned", "Next"),
)


def today_block(caps: list[Capability], updated: str) -> str:
    counts = {key: sum(c.status == key for c in caps) for key, _ in TODAY_GROUPS}
    summary = (
        f'<p class="today-sum"><b>{counts["done"]}</b> things work now, <b>{counts["partial"]}</b> '
        f"in part, <b>{counts['planned']}</b> next · as of {en_date(updated)}</p>"
    )
    groups = []
    for key, title in TODAY_GROUPS:
        cards = "".join(
            f'<article class="ability {c.status}"><h3>{html.escape(c.what)}</h3>'
            f'<div class="ab-try"><span class="k">Try</span><code>{html.escape(c.how)}</code></div>'
            f'<div class="ab-where"><span class="k">Runs on</span>{html.escape(c.where)}</div>'
            f'<div class="ab-ev"><span class="k">Evidence</span><span class="ab-refs">'
            + "".join(f"<code>{html.escape(ref)}</code>" for ref in c.evidence)
            + "</span></div></article>"
            for c in caps
            if c.status == key
        )
        if cards:
            groups.append(
                f'<div class="ab-group {key}"><h3 class="ab-h"><span class="chip {CHIP[key]}">'
                f"{title}</span> {counts[key]}</h3>"
                f'<div class="ab-grid">{cards}</div></div>'
            )
    return summary + "".join(groups)


def blocks() -> dict[str, str]:
    lines = ROADMAP.read_text(encoding="utf-8").splitlines()
    status = roadmap_status(lines)
    matrix = roadmap_matrix(lines)
    by_id = {inc.id: inc for inc in matrix if inc.id}
    placed = [i for ids in LAYERS.values() for i in ids]
    if sorted(placed) != sorted(by_id):
        raise SystemExit(
            f"LAYERS must place every §0.2 increment exactly once: {sorted(set(placed) ^ set(by_id))}"
        )
    ms = milestones(lines, matrix)
    updated = DATE.search(status["Last updated"]).group(1)
    gate = gate_date(lines)
    out = {
        "pulse": pulse(status, ms, gate, date.fromisoformat(updated)),
        "journey": journey(status, ms, gate, updated),
        "today": today_block(capabilities("\n".join(lines)), updated),
    }
    out.update({f"layer-{n}": layer(n, by_id) for n in LAYERS})
    out.update({f"inc-{i}": f"{a} / {b}" for i, inc in by_id.items() for a, b in [inc.counts]})
    return out


def render(page: str) -> str:
    content = blocks()
    seen = set()

    def fill(m: re.Match[str]) -> str:
        key = m.group(2)
        if key not in content:
            raise SystemExit(f"Unknown generated block in {TARGET.name}: {key}")
        seen.add(key)
        return m.group(1) + content[key] + m.group(4)

    out = BLOCK.sub(fill, page)
    required = {"pulse", "journey", "today", *(f"layer-{n}" for n in LAYERS)}
    if required - seen:
        raise SystemExit(f"{TARGET.name} lost its generated blocks: {sorted(required - seen)}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="write nothing; exit 1 if the page is stale"
    )
    args = parser.parse_args()
    current = TARGET.read_text(encoding="utf-8")
    content = render(current)
    if args.check:
        if current != content:
            print(
                f"{TARGET.relative_to(ROOT)} is stale. Run: python3 scripts/gen_architecture_progress.py",
                file=sys.stderr,
            )
            return 1
        print(f"{TARGET.relative_to(ROOT)} matches the roadmap")
        return 0
    TARGET.write_text(content, encoding="utf-8")
    print(f"Wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
