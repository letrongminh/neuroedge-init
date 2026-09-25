"""docs/business/cpo-dashboard.html phải khớp bản sinh từ roadmap, TODOS, PRD, CHANGELOG."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE = REPO_ROOT / "docs" / "business" / "cpo-dashboard.html"


def test_the_dashboard_is_fresh() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "gen_cpo_dashboard.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "docs/business/cpo-dashboard.html đã cũ so với nguồn.\n"
        "Chạy: python3 scripts/gen_cpo_dashboard.py\n"
        f"{result.stdout}{result.stderr}"
    )


INCREMENT_ROW = re.compile(
    r"^\|[^|\n]*\| \*\*(I\d+[a-z]?) — [^|\n]*\|[^|\n]*\|[^|\n]*\| \*\*([^*\n]+)\*\* \|", re.M
)


def test_the_dashboard_shows_the_roadmap_progress_of_every_increment() -> None:
    roadmap = (REPO_ROOT / "neuroedge-roadmap.md").read_text(encoding="utf-8")
    page = PAGE.read_text(encoding="utf-8")
    rows = INCREMENT_ROW.findall(roadmap)
    headings = re.findall(r"^### [\d.]+ (I\d+[a-z]?) — ", roadmap, re.M)
    assert rows and [inc for inc, _ in rows] == headings
    for _, value in rows:
        assert f"<b>{value}</b>" in page, value


def test_every_increment_with_tasks_gets_its_bar() -> None:
    """The matrix joins §0.2 rows to task tables by increment ID; a failed join used to fall
    back silently to a placeholder instead of the bar."""
    page = PAGE.read_text(encoding="utf-8")
    for inc, value in INCREMENT_ROW.findall(
        (REPO_ROOT / "neuroedge-roadmap.md").read_text(encoding="utf-8")
    ):
        if not value.endswith(" 0"):
            assert f'class="bar" role="img" aria-label="{inc} — ' in page, inc


def test_the_dashboard_needs_no_network() -> None:
    page = PAGE.read_text(encoding="utf-8")
    assert not re.search(r"(src|href)=\"(https?:)?//", page)
    assert "@import" not in page
