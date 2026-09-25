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


def test_the_dashboard_shows_the_roadmap_progress_of_every_sprint() -> None:
    roadmap = (REPO_ROOT / "neuroedge-roadmap.md").read_text(encoding="utf-8")
    page = PAGE.read_text(encoding="utf-8")
    progress = re.findall(
        r"^\|[^|\n]*\| \*\*Sprint \d[^|]*\|[^|]*\|[^|]*\| \*\*([^*]+)\*\* \|", roadmap, re.M
    )
    assert len(progress) >= 5
    for value in progress:
        assert f"<b>{value}</b>" in page, value


def test_the_dashboard_needs_no_network() -> None:
    page = PAGE.read_text(encoding="utf-8")
    assert not re.search(r"(src|href)=\"(https?:)?//", page)
    assert "@import" not in page
