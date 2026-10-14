"""docs/user/trang-thai.md must match what is generated from neuroedge-roadmap.md §0."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_user_status_is_fresh() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "gen_user_status.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "docs/user/trang-thai.md is stale against neuroedge-roadmap.md §0.\n"
        "Run: python3 scripts/gen_user_status.py\n"
        f"{result.stdout}{result.stderr}"
    )
