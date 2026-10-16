"""
docs/spec/blueprint.md (FR-BP, Q-72, Q-85) stays closed against the code and the roadmap.

Every requirement of §3 has a test case in §5; every test case verifies requirements that exist;
an implemented test case names a test function that exists; a planned one names a roadmap task;
every decision and task the specification cites exists.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRS = REPO_ROOT / "docs" / "spec" / "blueprint.md"
ROADMAP = REPO_ROOT / "roadmap" / "neuroedge-roadmap.md"
PRD = REPO_ROOT / "roadmap" / "neuroedge-prd.md"

REQ_ROW = re.compile(r"^\| (BL-[A-Z]+-\d{2}) \|", re.M)
TC_ROW = re.compile(r"^\| (TC-[A-Z]+-\d{2}-\d+) \| ([^|]+) \|[^|]+\|[^|]+\| ([^|\n]+) \|$", re.M)
IMPLEMENTED = re.compile(r"^implemented — (python/tests/[\w/]+\.py)::(test_\w+)$")
PLANNED = re.compile(r"^planned — (TSK-[A-Za-z0-9]+-\d+)$")


def text() -> str:
    return SRS.read_text(encoding="utf-8")


def section() -> str:
    return text().split("## 3. Specific requirements", 1)[1].split("## 4. Interfaces", 1)[0]


def requirements() -> list[str]:
    return REQ_ROW.findall(section())


def cases() -> list[tuple[str, list[str], str]]:
    return [
        (tc, [r.strip() for r in verifies.split(",")], status.strip())
        for tc, verifies, status in TC_ROW.findall(text())
    ]


def test_the_specification_has_requirements_and_cases() -> None:
    assert len(requirements()) >= 20
    # A row the parser cannot read would silently drop out: every table row is a parsed row.
    assert len(re.findall(r"^\| BL-", section(), re.M)) == len(requirements())
    assert len(re.findall(r"^\| TC-", text(), re.M)) == len(cases())
    assert len(set(requirements())) == len(requirements()), "a requirement ID is used twice"
    names = [tc for tc, _, _ in cases()]
    assert len(set(names)) == len(names), "a test case ID is used twice"


def test_every_requirement_is_verified_by_a_test_case() -> None:
    covered = {req for _, verifies, _ in cases() for req in verifies}
    assert sorted(set(requirements()) - covered) == []


def test_every_test_case_verifies_requirements_that_exist() -> None:
    known = set(requirements())
    for tc, verifies, _ in cases():
        assert set(verifies) <= known, (tc, sorted(set(verifies) - known))


def test_an_implemented_test_case_names_a_test_that_exists() -> None:
    # A loop, not parametrize: while every case is planned, an empty parametrize would skip (§5).
    for tc, _, status in cases():
        if not status.startswith("implemented — "):
            continue
        found = IMPLEMENTED.match(status)
        assert found, (tc, status)
        path, function = found.groups()
        source = (REPO_ROOT / path).read_text(encoding="utf-8")
        found = re.search(rf"((?:^@.*\n)*)^def {function}\(", source, re.M)
        assert found, (tc, path, function)
        assert not re.search(r"skip|xfail", found.group(1)), (tc, "decorated as skipped or xfail")


def test_a_planned_test_case_names_a_roadmap_task() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    for tc, _, status in cases():
        if status.startswith("implemented — "):
            continue
        found = PLANNED.match(status)
        assert found, (tc, status)
        assert f"**{found.group(1)}**" in roadmap, (tc, found.group(1))


def test_every_decision_and_task_the_specification_cites_exists() -> None:
    srs, roadmap, prd = text(), ROADMAP.read_text(encoding="utf-8"), PRD.read_text(encoding="utf-8")
    decisions = set(re.findall(r"\| \*\*(Q-\d+)\*\* \|", prd))
    for q in sorted(set(re.findall(r"\bQ-\d+\b", srs))):
        assert q in decisions, q
    for task in sorted(set(re.findall(r"\bTSK-[A-Za-z0-9]+-\d+\b", srs))):
        assert f"**{task}**" in roadmap, task


def test_every_requirement_cited_elsewhere_exists() -> None:
    known = set(requirements()) | set(re.findall(r"^\| (BL-D-\d{2}) \|", text(), re.M))
    for path in (
        ROADMAP,
        PRD,
        REPO_ROOT / "CHANGELOG.md",
        REPO_ROOT / "docs" / "user" / "thuat-ngu.md",
    ):
        for req in set(re.findall(r"\bBL-[A-Z]+-\d{2}\b", path.read_text(encoding="utf-8"))):
            assert req in known, (path.name, req)
