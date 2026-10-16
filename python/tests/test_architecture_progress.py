"""The progress blocks of docs/business/kien-truc-tong-the.html must match what is generated from the roadmap."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE = REPO_ROOT / "docs" / "business" / "kien-truc-tong-the.html"
ROADMAP = REPO_ROOT / "roadmap" / "neuroedge-roadmap.md"


def test_the_progress_on_the_architecture_page_is_fresh() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "gen_architecture_progress.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "docs/business/kien-truc-tong-the.html is stale against the roadmap.\n"
        "Run: python3 scripts/gen_architecture_progress.py\n"
        f"{result.stdout}{result.stderr}"
    )


INCREMENT_ROW = re.compile(
    r"^\|[^|\n]*\| \*\*(I\d+[a-z]?) — [^|\n]*\|[^|\n]*\|[^|\n]*\| \*\*([^*\n]+)\*\* \|", re.M
)


def test_every_increment_shows_its_progress_on_a_layer() -> None:
    """Each §0.2 increment gets one bar on the architecture layer it builds, with its task count."""
    roadmap = ROADMAP.read_text(encoding="utf-8")
    page = PAGE.read_text(encoding="utf-8")
    rows = INCREMENT_ROW.findall(roadmap)
    headings = re.findall(r"^### [\d.]+ (I\d+[a-z]?) — ", roadmap, re.M)
    assert rows and [inc for inc, _ in rows] == headings
    layers = "".join(re.findall(r"<!-- GENERATED:layer-\d -->(.*?)<!-- /GENERATED", page, re.S))
    for inc, value in rows:
        a, b = re.findall(r"\d+", value)[:2]
        assert layers.count(f'<span class="id">{inc}</span>') == 1, inc
        assert f'<span class="id">{inc}</span>' in layers and f"{a}/{b}</span>" in layers, inc


def test_every_increment_belongs_to_exactly_one_release_milestone() -> None:
    """Roadmap §0.5 groups increments into user-facing milestones; the architecture page and poster
    E-09 read it, so an increment missing from it, or listed twice, would silently drop off."""
    roadmap = ROADMAP.read_text(encoding="utf-8")
    part = roadmap.split("#### User-facing release milestones", 1)[1].split("\n---", 1)[0]
    grouped = [
        inc.strip()
        for row in re.findall(r"^\| \d+ \|(?:[^|\n]*\|){3}([^|\n]*)\|", part, re.M)
        for inc in row.split(",")
    ]
    increments = [inc for inc, _ in INCREMENT_ROW.findall(roadmap)]
    assert sorted(grouped) == sorted(increments)
    assert len(grouped) == len(set(grouped))


def _generator():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gen_architecture_progress", REPO_ROOT / "scripts" / "gen_architecture_progress.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up while the script loads
    spec.loader.exec_module(module)
    return module


def test_every_capability_of_today_is_a_card_on_the_page() -> None:
    """`00-overview.md` §6.1 is the one list of what a person can do today (CONTRIBUTING.md §8.1)."""
    roadmap = ROADMAP.read_text(encoding="utf-8")
    caps = _generator().capabilities(roadmap)
    page = PAGE.read_text(encoding="utf-8")
    today = re.search(r"<!-- GENERATED:today -->(.*?)<!-- /GENERATED:today -->", page, re.S)
    assert today and len(caps) >= 10
    assert today.group(1).count('<article class="ability ') == len(caps)
    for cap in caps:
        assert cap.status in ("done", "partial", "planned"), cap.what
        assert cap.evidence, cap.what


def _refused(gen, tmp_path, monkeypatch, row: str) -> str:
    overview = tmp_path / "00-overview.md"
    overview.write_text(
        "### 6.1 What a person can do today\n\n"
        "| Name | Capability | Try it | Runs on | Reach | Status | Evidence |\n"
        "|:---|:---|:---|:---|:---|:---|:---|\n"
        f"{row}\n\n### 6.2 By target\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(gen, "OVERVIEW", overview)
    try:
        gen.capabilities(ROADMAP.read_text(encoding="utf-8"))
    except SystemExit as stop:
        return str(stop)
    raise AssertionError(f"accepted: {row}")


def test_a_capability_whose_evidence_is_missing_is_refused(tmp_path, monkeypatch) -> None:
    row = "| Fly | Fly | `neuroedge fly` | `sim` | laptop ● | `done` | `python/tests/test_no_such_file.py` |"
    assert "test_no_such_file.py" in _refused(_generator(), tmp_path, monkeypatch, row)


def test_a_reach_that_contradicts_the_status_is_refused(tmp_path, monkeypatch) -> None:
    """A `planned` capability cannot work anywhere; a `done` one works somewhere; places are known."""
    gen, ev = _generator(), "`python/tests/test_architecture_progress.py`"
    for reach, status in (
        ("laptop ●", "planned"),
        ("laptop ○", "done"),
        ("laptop ●, qemu ◐", "done"),
        ("cloud ●", "done"),
    ):
        row = f"| Fly | Fly | `x` | `sim` | {reach} | `{status}` | {ev}, TSK-I2d-04 |"
        assert "§6.1" in _refused(gen, tmp_path, monkeypatch, row), (reach, status)


def test_the_reach_map_counts_what_works_in_each_place() -> None:
    caps = _generator().capabilities(ROADMAP.read_text(encoding="utf-8"))
    page = PAGE.read_text(encoding="utf-8")
    counts = re.findall(r'<span class="rm-count">(\d+)</span>', page)
    places = ("laptop", "linux", "qemu", "board")
    assert [int(n) for n in counts] == [sum(c.reach.get(p) == "done" for c in caps) for p in places]
    assert page.count('<div class="rm-row ') == len(caps) + 2  # head, rows, foot
