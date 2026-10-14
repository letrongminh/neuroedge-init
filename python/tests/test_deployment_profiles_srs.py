"""
docs/spec/deployment_profiles.md (Q-83) stays closed against the code and the roadmap.

Every requirement of §3 has a test case in §5; every test case verifies requirements that exist;
an implemented test case names a test function that exists; a planned one names a roadmap task;
every decision and task the specification cites exists. So the specification cannot drift from
what is built, and nothing waits as a skipped test.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRS = REPO_ROOT / "docs" / "spec" / "deployment_profiles.md"
ROADMAP = REPO_ROOT / "roadmap" / "neuroedge-roadmap.md"
PRD = REPO_ROOT / "roadmap" / "neuroedge-prd.md"

REQ_ROW = re.compile(r"^\| (DP-[A-Z]+-\d{2}) \|", re.M)
TC_ROW = re.compile(r"^\| (TC-[A-Z]+-\d{2}-\d+) \| ([^|]+) \|[^|]+\|[^|]+\| ([^|\n]+) \|$", re.M)
IMPLEMENTED = re.compile(r"^implemented — (python/tests/[\w/]+\.py)::(test_\w+)$")
PLANNED = re.compile(r"^planned — (TSK-[A-Za-z0-9]+-\d+)$")


def text() -> str:
    return SRS.read_text(encoding="utf-8")


def requirements() -> list[str]:
    """The IDs of §3 (the traceability table of §6 repeats some; it is not where they are defined)."""
    section = text().split("## 3. Specific requirements", 1)[1].split("## 4. Interfaces", 1)[0]
    return REQ_ROW.findall(section)


def cases() -> list[tuple[str, list[str], str]]:
    return [
        (tc, [r.strip() for r in verifies.split(",")], status.strip())
        for tc, verifies, status in TC_ROW.findall(text())
    ]


def test_the_specification_has_requirements_and_cases() -> None:
    assert len(requirements()) >= 30
    assert len(cases()) >= len(requirements())
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


@pytest.mark.parametrize("tc", [tc for tc, _, s in cases() if s.startswith("implemented")])
def test_an_implemented_test_case_names_a_test_that_exists(tc: str) -> None:
    status = next(s for name, _, s in cases() if name == tc)
    found = IMPLEMENTED.match(status)
    assert found, (tc, status)
    path, function = found.groups()
    source = (REPO_ROOT / path).read_text(encoding="utf-8")
    assert re.search(rf"^def {function}\(", source, re.M), (tc, path, function)


def test_a_planned_test_case_names_a_roadmap_task() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    for tc, _, status in cases():
        if status.startswith("implemented"):
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
