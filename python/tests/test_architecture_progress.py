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
