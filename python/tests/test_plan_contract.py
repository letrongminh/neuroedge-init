"""
Anti-drift rules of the roadmap (`roadmap/neuroedge-roadmap.md` §2.4, Q-39).

The roadmap is the only place that records task status, exit criteria, forecasts, dependencies
and release cards; design notes carry none of them. The tests below keep that true after every
PR — something eyeballed review could not do while the plan lived in four files.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "roadmap"
ROADMAP = DOCS / "neuroedge-roadmap.md"
ARCHIVE = DOCS / "archive" / "removed-tasks.md"
DESIGN_NOTES = ("docs/spec/lab_mcp.md",)
GLYPHS = "✅🟡⏳⏸🔴"
DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
TASK_ROW = re.compile(r"^\| \*\*(TSK-[A-Za-z0-9]+-\d+)\*\* \|")
CODE = re.compile(r"\bTSK-[A-Z][A-Za-z0-9]*-\d{2}\b")
INC = re.compile(r"^I(\d+)([a-z]?)$")

LINES = ROADMAP.read_text(encoding="utf-8").splitlines()


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def glyphs(text: str) -> int:
    return sum(text.count(g) for g in GLYPHS)


def matrix() -> list[list[str]]:
    """The increment rows of §0.2: (milestone, **Ix — name**, forecast, …)."""
    start = next(i for i, line in enumerate(LINES) if line.startswith("### 0.2"))
    header = next(
        i for i in range(start, len(LINES)) if LINES[i].startswith("| Milestone | Increment |")
    )
    rows = []
    for line in LINES[header + 2 :]:
        if not line.startswith("|"):
            break
        rows.append(cells(line))
    return rows


def inc_of(cell: str) -> str | None:
    m = re.match(r"\*\*(I\d+[a-z]?) — ", cell)
    return m.group(1) if m else None


def key(inc: str) -> tuple[int, str]:
    m = INC.match(inc)
    assert m, inc
    return int(m.group(1)), m.group(2)


INCREMENTS = [(inc_of(row[1]), row) for row in matrix() if inc_of(row[1])]


def task_rows() -> dict[str | None, list[list[str]]]:
    """Task rows grouped by the increment of the `###` section they sit in (None: no increment)."""
    out: dict[str | None, list[list[str]]] = {}
    current = None
    for line in LINES:
        if line.startswith("### "):
            m = re.match(r"### [\d.]+ (I\d+[a-z]?) — ", line)
            current = m.group(1) if m else None
        if TASK_ROW.match(line):
            out.setdefault(current, []).append(cells(line))
    return out


TASKS = task_rows()
ALL_TASKS = [row for rows in TASKS.values() for row in rows]
ARCHIVED = [
    cells(line) for line in ARCHIVE.read_text(encoding="utf-8").splitlines() if TASK_ROW.match(line)
]


# --- R1: plan data lives only in the roadmap ------------------------------------------------


@pytest.mark.parametrize("note", DESIGN_NOTES)
def test_design_notes_carry_no_tasks_criteria_or_cut_ladders(note: str) -> None:
    text = (ROOT / note).read_text(encoding="utf-8")
    offenders = [
        line
        for line in text.splitlines()
        if TASK_ROW.match(line)
        or line.startswith("| Task code")
        or re.match(r"- \[[ x]\] \*\*Criterion", line)
        or re.match(r"#+ .*Scope-cut ladder", line)
    ]
    assert not offenders, f"{note} still carries plan data (R1): {offenders[:3]}"


# --- R2, R3, R4: increment IDs, dependencies, forecasts ------------------------------------


def test_increment_ids_are_unique_and_ascending() -> None:
    ids = [inc for inc, _ in INCREMENTS]
    assert len(ids) == len(set(ids)), ids
    assert ids == sorted(ids, key=key), ids
    headings = [
        m.group(1) for line in LINES if (m := re.match(r"### [\d.]+ (I\d+[a-z]?) — ", line))
    ]
    assert headings == ids, (
        "every increment in §0.2 needs exactly one `### x.y Ix —` section, in the same order"
    )


def test_dependencies_point_only_to_earlier_increments() -> None:
    for inc, row in INCREMENTS:
        for dep in re.findall(r"\bI\d+[a-z]?\b", row[6]):
            assert key(dep) < key(inc), (
                f"{inc} depends on {dep} — a dependency pointing forward (R3)"
            )


def test_every_increment_has_exactly_one_forecast() -> None:
    for inc, row in INCREMENTS:
        forecast = row[2]
        found = DATE.findall(forecast)
        conditional = forecast.startswith(("after ", "when "))
        assert len(found) == 1 or (conditional and not found), f"{inc}: forecast {forecast!r} (R4)"


# --- R8, R9, R10: tasks ---------------------------------------------------------------------


def test_every_task_code_has_exactly_one_row() -> None:
    codes = [row[0].strip("*") for row in ALL_TASKS + ARCHIVED]
    dupes = sorted({c for c in codes if codes.count(c) > 1})
    assert not dupes, f"codes with more than one task row (R8): {dupes}"
    assert None not in TASKS or all("⏸" in row[4] for row in TASKS[None]), (
        "a task outside an increment may only be a deferred task (§8.2)"
    )
    assert all("⏸" in row[4] for row in ARCHIVED), "an archived task is never planned (R8, Q-92)"


def test_every_cited_task_code_exists_in_the_roadmap() -> None:
    known = {row[0].strip("*") for row in ALL_TASKS + ARCHIVED}
    places = [
        ROOT / p for p in (*DESIGN_NOTES, "roadmap/neuroedge-prd.md", "TODOS.md", "CONTRIBUTING.md")
    ]
    for folder in ("python", "scripts", "targets", ".github", "docs"):
        places += [
            p
            for p in (ROOT / folder).rglob("*")
            if p.is_file()
            and p.suffix in {".py", ".c", ".h", ".yml", ".yaml", ".md", ".toml", ".txt"}
            and "archive" not in p.parts
            and ".venv" not in p.parts
            and "build" not in p.parts
        ]
    missing: dict[str, set[str]] = {}
    for path in places:
        for code in CODE.findall(path.read_text(encoding="utf-8", errors="replace")):
            if code not in known:
                missing.setdefault(code, set()).add(str(path.relative_to(ROOT)))
    assert not missing, f"task codes cited but absent from the roadmap (R8): {missing}"


def test_every_status_cell_has_exactly_one_glyph() -> None:
    for row in ALL_TASKS + ARCHIVED:
        assert glyphs(row[4]) == 1, f"{row[0]}: status cell {row[4][:60]!r} (R9)"
    for inc, row in INCREMENTS:
        assert glyphs(row[5]) == 1, f"{inc}: §0.2 status cell {row[5]!r} (R9)"


def test_matrix_progress_matches_the_task_tables() -> None:
    for inc, row in INCREMENTS:
        rows = TASKS.get(inc, [])
        done = sum("✅" in r[4] for r in rows)
        assert row[4] == f"**{done} / {len(rows)}**", (
            f"{inc}: §0.2 says {row[4]}, the task table says {done}/{len(rows)} (R10)"
        )


# --- R6, R11: time labels and cross-references across the repo ------------------------------

SWEPT = {".md", ".py", ".c", ".h", ".yml", ".yaml", ".toml"}
SKIPPED_DIRS = {
    ".git",
    ".venv",
    "build",
    "node_modules",
    "archive",
    "__pycache__",
    "managed_components",
}
TIME_LABEL = re.compile(r"(?<!\w)(Tuần|Tháng|Week|Month) \d|Mốc \d+([.,]\d)? tháng")
MD_LINE_REF = re.compile(r"[\w./-]+\.md:\d+")
ROADMAP_REF = re.compile(r"(?:neuroedge-roadmap\.md`?\)?|[Rr]oadmap) §(\d+(?:\.\d+)?)")


def repo_text() -> list[tuple[str, str]]:
    """(path, text) of every swept file; CHANGELOG.md only from §2 on — §1 is history."""
    out = []
    for path in ROOT.rglob("*"):
        if path.suffix not in SWEPT or not path.is_file():
            continue
        parts = path.relative_to(ROOT).parts
        if SKIPPED_DIRS & set(parts) or any(p.startswith(".") and p != ".github" for p in parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.name == "CHANGELOG.md":
            text = text[text.index("## 2. ") :]
        out.append((str(path.relative_to(ROOT)), text))
    return out


REPO = repo_text()


def test_no_numbered_week_or_month_labels() -> None:
    """R6: time is measured by increments; a duration counts from when an increment opens."""
    hits = [f"{path}: {m.group(0)}" for path, text in REPO for m in TIME_LABEL.finditer(text)]
    assert not hits, f"numbered week/month labels (R6): {hits[:10]}"


def test_no_line_number_references_into_markdown() -> None:
    """R11: a `file.md:NNN` reference goes stale at the next edit; cite a section or a code."""
    hits = [f"{path}: {m.group(0)}" for path, text in REPO for m in MD_LINE_REF.finditer(text)]
    assert not hits, f"line-number references (R11): {hits[:10]}"


def test_roadmap_section_references_resolve() -> None:
    headings = {
        m.group(1) for line in LINES if (m := re.match(r"#{2,4} (\d+(?:\.\d+)?)[. ]", line))
    }
    broken = [
        f"{path}: §{m.group(1)}"
        for path, text in REPO
        for m in ROADMAP_REF.finditer(text)
        if m.group(1) not in headings
    ]
    assert not broken, f"references to roadmap sections that do not exist (R11): {broken[:10]}"
