#!/usr/bin/env python3
"""Generate docs/user/trang-thai.md from neuroedge-roadmap.md §0.

Project status lives in one place (CONTRIBUTING.md §8.1): neuroedge-roadmap.md §0.
The generated file is a machine-made copy for users; never edit it by hand.

    python3 scripts/gen_user_status.py           # write the file
    python3 scripts/gen_user_status.py --check   # write nothing; exit 1 if stale

Run --check in CI (see python/tests/test_user_status_fresh.py) so the document
does not drift from its source. The printed date comes from the source, not the
machine clock, so the output is deterministic and --check does not go stale daily.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "roadmap" / "neuroedge-roadmap.md"
TARGET = ROOT / "docs" / "user" / "trang-thai.md"

STATUS_LABELS = (
    "Current phase",
    "Open increment",
    "Next milestone",
    "Core CI status",
    "Non-technical blockers",
    "Last updated",
)

MATRIX_HEADER = "| Milestone | Increment |"
MATRIX_COLUMNS = (0, 1, 2, 4, 5, 7)

LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")


def strip_links(text: str) -> str:
    return LINK.sub(r"\1", text)


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def section(lines: list[str], start_marker: str, end_marker: str) -> list[str]:
    start = next(i for i, line in enumerate(lines) if line.startswith(start_marker))
    end = next(i for i, line in enumerate(lines) if line.startswith(end_marker))
    return lines[start:end]


def parse_status_rows(lines: list[str]) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in lines:
        if not line.startswith("| **") or line.startswith("|:--"):
            continue
        cells = split_row(line)
        label = cells[0].strip("* ")
        if label in STATUS_LABELS:
            rows[label] = strip_links(cells[1])
    missing = [label for label in STATUS_LABELS if label not in rows]
    if missing:
        raise SystemExit(f"neuroedge-roadmap.md §0.1 is missing rows: {', '.join(missing)}")
    return rows


def parse_matrix(lines: list[str]) -> list[list[str]]:
    start = next(i for i, line in enumerate(lines) if line.startswith(MATRIX_HEADER))
    rows: list[list[str]] = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        cells = split_row(line)
        rows.append([strip_links(cells[i]) for i in MATRIX_COLUMNS])
    if not rows:
        raise SystemExit("neuroedge-roadmap.md §0.2 has no rows")
    return rows


def render() -> str:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    status = parse_status_rows(section(lines, "### 0.1", "### 0.2"))
    matrix = parse_matrix(section(lines, "### 0.2", "### 0.3"))

    out = [
        "<!-- GENERATED from neuroedge-roadmap.md §0 — do not edit by hand.",
        "     Regenerate: python3 scripts/gen_user_status.py (check: --check) -->",
        "",
        "# Project status",
        "",
        "> Generated from [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) §0 —",
        f"> the single source of truth for progress. Source last updated: {status['Last updated']}.",
        "",
        "## Executive status",
        "",
        "| Indicator | Current status |",
        "|:---|:---|",
    ]
    for label in STATUS_LABELS:
        out.append(f"| {label} | {status[label]} |")
    out += [
        "",
        "## Increments",
        "",
        "| Milestone | Increment | Forecast | Progress | Status | Release |",
        "|:---:|:---|:---|:---:|:---|:---|",
    ]
    for milestone, increment, forecast, progress, state, release in matrix:
        out.append(f"| {milestone} | {increment} | {forecast} | {progress} | {state} | {release} |")
    out += [
        "",
        "Capabilities, dependencies and assumptions behind the forecast dates: "
        "[`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) §0.",
        "",
    ]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="write nothing; exit 1 if the file is stale"
    )
    args = parser.parse_args()

    content = render()
    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != content:
            print(
                f"{TARGET.relative_to(ROOT)} is stale against {SOURCE.name} §0.\n"
                "Run: python3 scripts/gen_user_status.py",
                file=sys.stderr,
            )
            return 1
        print(f"{TARGET.relative_to(ROOT)} matches its source")
        return 0

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(content, encoding="utf-8")
    print(f"Wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
