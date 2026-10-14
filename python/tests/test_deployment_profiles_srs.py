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
# A Go test of the NeuroClaw repository (TSK-I2d-26), run there against this box at a pinned
# commit; this repository cannot see it, so only its form is checked.
IN_NEUROCLAW = re.compile(r"^implemented in NeuroClaw — pkg/[\w/]+_test\.go::Test\w+$")
# A test case only an ESP-IDF build or Espressif QEMU can run: the CI job that runs it, which names
# the test case in its own steps.
IN_CI = re.compile(r"^implemented in CI — (\.github/workflows/[\w-]+\.yml)::([\w-]+)$")


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
    # A row the parser cannot read would silently drop out: every table row is a parsed row.
    section = text().split("## 3. Specific requirements", 1)[1].split("## 4. Interfaces", 1)[0]
    assert len(re.findall(r"^\| DP-", section, re.M)) == len(requirements())
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


@pytest.mark.parametrize("tc", [tc for tc, _, s in cases() if s.startswith("implemented — ")])
def test_an_implemented_test_case_names_a_test_that_exists(tc: str) -> None:
    status = next(s for name, _, s in cases() if name == tc)
    found = IMPLEMENTED.match(status)
    assert found, (tc, status)
    path, function = found.groups()
    source = (REPO_ROOT / path).read_text(encoding="utf-8")
    found = re.search(rf"((?:^@.*\n)*)^def {function}\(", source, re.M)
    assert found, (tc, path, function)
    # A top-level test (collected) that is not skipped or expected to fail.
    assert not re.search(r"skip|xfail", found.group(1)), (tc, "decorated as skipped or xfail")


def test_a_planned_test_case_names_a_roadmap_task() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    for tc, _, status in cases():
        if status.startswith("implemented — "):
            continue
        if status.startswith("implemented in NeuroClaw"):
            assert IN_NEUROCLAW.match(status), (tc, status)
            continue
        if status.startswith("implemented in CI"):
            continue
        found = PLANNED.match(status)
        assert found, (tc, status)
        assert f"**{found.group(1)}**" in roadmap, (tc, found.group(1))


@pytest.mark.parametrize("tc", [tc for tc, _, s in cases() if s.startswith("implemented in CI")])
def test_a_test_case_run_in_ci_names_a_job_that_runs_it(tc: str) -> None:
    import yaml

    status = next(s for name, _, s in cases() if name == tc)
    found = IN_CI.match(status)
    assert found, (tc, status)
    path, job = found.groups()
    workflow = yaml.safe_load((REPO_ROOT / path).read_text(encoding="utf-8"))
    assert job in workflow["jobs"], (tc, path, job)
    steps = workflow["jobs"][job]["steps"]
    assert any(tc in step.get("name", "") for step in steps), (tc, "no step of the job names it")


def test_every_decision_and_task_the_specification_cites_exists() -> None:
    srs, roadmap, prd = text(), ROADMAP.read_text(encoding="utf-8"), PRD.read_text(encoding="utf-8")
    decisions = set(re.findall(r"\| \*\*(Q-\d+)\*\* \|", prd))
    for q in sorted(set(re.findall(r"\bQ-\d+\b", srs))):
        assert q in decisions, q
    for task in sorted(set(re.findall(r"\bTSK-[A-Za-z0-9]+-\d+\b", srs))):
        assert f"**{task}**" in roadmap, task


CITING = [
    REPO_ROOT / "roadmap" / "neuroedge-roadmap.md",
    REPO_ROOT / "roadmap" / "neuroedge-prd.md",
    REPO_ROOT / "CHANGELOG.md",
    REPO_ROOT / "docs" / "spec" / "threat_model.md",
    REPO_ROOT / "docs" / "spec" / "tool_calling.md",
    REPO_ROOT / "docs" / "spec" / "studio.md",
    REPO_ROOT / "docs" / "user" / "thuat-ngu.md",
    REPO_ROOT / "docs" / "business" / "kien-truc-tong-the.html",
    *sorted((REPO_ROOT / "docs" / "architecture" / "vi").glob("*.md")),
]


def test_every_requirement_cited_elsewhere_exists() -> None:
    known = set(requirements())
    for path in CITING:
        for req in set(re.findall(r"\bDP-[A-Z]+-\d{2}\b", path.read_text(encoding="utf-8"))):
            assert req in known, (path.name, req)


def test_the_refusal_reasons_agree_in_the_spec_the_trace_catalogue_and_the_code() -> None:
    from neuroedge.sim import ui

    source = Path(ui.__file__).read_text(encoding="utf-8")
    in_code = set(re.findall(r'return "(\w+)"', source)) | set(
        re.findall(r'refuse\("(\w+)"', source)
    )
    srs = text().split("### 4.4", 1)[1].split("## 5.", 1)[0]
    in_srs = set(re.findall(r"`(\w+)`", srs.split("Refusal reasons:", 1)[1].split(".", 1)[0]))
    catalogue = (REPO_ROOT / "docs" / "spec" / "tool_calling.md").read_text(encoding="utf-8")
    row = next(line for line in catalogue.splitlines() if line.startswith("| `ui_auth_refused` |"))
    in_catalogue = set(re.findall(r"`(\w+)`", row.split("`reason`:", 1)[1].split(".", 1)[0]))
    assert in_code == in_srs == in_catalogue, (in_code, in_srs, in_catalogue)
    assert {"no_origin", "no_key", "wrong_key", "bad_code"} <= in_code
