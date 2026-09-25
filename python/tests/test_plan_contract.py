"""
Luật chống lệch của roadmap (`neuroedge-roadmap.md` §2.4, Q-39).

Roadmap là nơi duy nhất ghi trạng thái task, tiêu chí ra, dự báo, phụ thuộc và thẻ phát
hành; ghi chú thiết kế không có chúng. Các test dưới đây giữ cho điều đó còn đúng sau mỗi
PR — thứ mà review bằng mắt đã không giữ được khi kế hoạch nằm ở bốn tệp.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ROADMAP = ROOT / "neuroedge-roadmap.md"
DESIGN_NOTES = (
    "neuroedge-roadmap-phase1-5.md",
    "neuroedge-roadmap-phase2.md",
    "draft-ke-hoach-mo-rong-robot-fofoca.md",
    "draft-rfc-node-giao-thuc-dieu-phoi.md",
)
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
    header = next(i for i in range(start, len(LINES)) if LINES[i].startswith("| Mốc | Increment |"))
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


# --- R1: plan data lives only in the roadmap ------------------------------------------------


@pytest.mark.parametrize("note", DESIGN_NOTES)
def test_design_notes_carry_no_tasks_criteria_or_cut_ladders(note: str) -> None:
    text = (ROOT / note).read_text(encoding="utf-8")
    offenders = [
        line
        for line in text.splitlines()
        if TASK_ROW.match(line)
        or line.startswith("| Mã Task")
        or re.match(r"- \[[ x]\] \*\*Tiêu chí", line)
        or re.match(r"#+ .*Thang cắt phạm vi", line)
    ]
    assert not offenders, f"{note} còn dữ liệu kế hoạch (R1): {offenders[:3]}"


# --- R2, R3, R4: increment IDs, dependencies, forecasts ------------------------------------


def test_increment_ids_are_unique_and_ascending() -> None:
    ids = [inc for inc, _ in INCREMENTS]
    assert len(ids) == len(set(ids)), ids
    assert ids == sorted(ids, key=key), ids
    headings = [
        m.group(1) for line in LINES if (m := re.match(r"### [\d.]+ (I\d+[a-z]?) — ", line))
    ]
    assert headings == ids, "mỗi increment ở §0.2 cần đúng một mục `### x.y Ix —`, cùng thứ tự"


def test_dependencies_point_only_to_earlier_increments() -> None:
    for inc, row in INCREMENTS:
        for dep in re.findall(r"\bI\d+[a-z]?\b", row[6]):
            assert key(dep) < key(inc), f"{inc} phụ thuộc {dep} — phụ thuộc trỏ tới sau (R3)"


def test_every_increment_has_exactly_one_forecast() -> None:
    for inc, row in INCREMENTS:
        forecast = row[2]
        found = DATE.findall(forecast)
        conditional = forecast.startswith(("sau ", "khi "))
        assert len(found) == 1 or (conditional and not found), f"{inc}: dự báo {forecast!r} (R4)"


# --- R8, R9, R10: tasks ---------------------------------------------------------------------


def test_every_task_code_has_exactly_one_row() -> None:
    codes = [row[0].strip("*") for row in ALL_TASKS]
    dupes = sorted({c for c in codes if codes.count(c) > 1})
    assert not dupes, f"mã có nhiều hơn một dòng task (R8): {dupes}"
    assert None not in TASKS or all("⏸" in row[4] for row in TASKS[None]), (
        "task ngoài increment chỉ được là task hoãn (§8.2)"
    )


def test_every_cited_task_code_exists_in_the_roadmap() -> None:
    known = {row[0].strip("*") for row in ALL_TASKS}
    places = [ROOT / p for p in (*DESIGN_NOTES, "TODOS.md", "neuroedge-prd.md", "CONTRIBUTING.md")]
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
    assert not missing, f"mã task được dẫn nhưng không có dòng trong roadmap (R8): {missing}"


def test_every_status_cell_has_exactly_one_glyph() -> None:
    for row in ALL_TASKS:
        assert glyphs(row[4]) == 1, f"{row[0]}: ô trạng thái {row[4][:60]!r} (R9)"
    for inc, row in INCREMENTS:
        assert glyphs(row[5]) == 1, f"{inc}: ô trạng thái §0.2 {row[5]!r} (R9)"


def test_matrix_progress_matches_the_task_tables() -> None:
    for inc, row in INCREMENTS:
        rows = TASKS.get(inc, [])
        done = sum("✅" in r[4] for r in rows)
        assert row[4] == f"**{done} / {len(rows)}**", (
            f"{inc}: §0.2 ghi {row[4]}, bảng task là {done}/{len(rows)} (R10)"
        )
