#!/usr/bin/env python3
"""
Every installed package carries a licence the Q-11 policy allows (TSK-S2-11).

    pip-licenses --format=json > licences.json
    python scripts/check_licences.py licences.json

Allowed: MIT, BSD-2/3-Clause, Apache-2.0, ISC, PSF, CNRI-Python (`regex`, via
tiktoken), MPL-2.0 (used unmodified) — the list in PRD §15 Q-11. Everything else fails —
GPL/LGPL/AGPL, SSPL, BSL, commercial, and *unknown*. Stricter than
`pip-licenses --allow-only --partial-match`, whose substring test lets
"Limited" pass as "MIT" and passes "X AND <anything>" when X is allowed: here
each licence string is split into its parts (``;``, ``AND``, ``OR``,
SPDX grouping) and **every** part must be an allowed licence.

The product itself is skipped: `neuroedge` carries its own licence (PolyForm
Noncommercial 1.0.0 AND Apache-2.0, Q-45), and Q-11 governs its dependencies.

Standard library only: it runs in the environment it inspects.
"""

from __future__ import annotations

import json
import re
import sys

ALLOWED = [
    r"MIT( License)?",
    r"MIT-0",
    r"BSD( License)?",
    r"0BSD",
    r"BSD-[23]-Clause",
    r"[23]-Clause BSD License",
    r"Apache-2\.0",
    r"Apache Software License",
    r"Apache License,? (Version )?2\.0",
    r"ISC( License)?( \(ISCL\))?",
    r"PSF-2\.0",
    r"Python Software Foundation License",
    r"CNRI-Python",
    r"MPL-2\.0",
    r"Mozilla Public License 2\.0 \(MPL 2\.0\)",
]
ALLOWED_RE = re.compile(r"^(?:" + "|".join(ALLOWED) + r")$", re.IGNORECASE)
SPLIT = re.compile(r";|\s+AND\s+|\s+OR\s+", re.IGNORECASE)
PRODUCT = "neuroedge"  # the package under test, not a dependency (Q-45)


def parts(licence: str) -> list[str]:
    # A licence given as its full text (tiktoken ships the MIT text): its first line names it.
    first = licence.strip().splitlines()[0] if licence.strip() else ""
    out = []
    for piece in SPLIT.split(first):
        piece = piece.strip()
        # SPDX grouping, "(A OR B) AND C" — not the "(ISCL)" of "ISC License (ISCL)".
        while piece.startswith("(") and piece.count("(") > piece.count(")"):
            piece = piece[1:].strip()
        while piece.endswith(")") and piece.count(")") > piece.count("("):
            piece = piece[:-1].strip()
        if piece:
            out.append(piece)
    return out


def offenders(packages: list[dict]) -> list[tuple[str, str, str]]:
    bad = []
    for package in packages:
        if str(package.get("Name", "")).lower() == PRODUCT:
            continue
        licence = str(package.get("License", ""))
        pieces = parts(licence)
        rejected = [p for p in pieces if not ALLOWED_RE.match(p)] or ([] if pieces else ["UNKNOWN"])
        if rejected:
            bad.append((package.get("Name", "?"), package.get("Version", "?"), "; ".join(rejected)))
    return bad


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        print("usage: check_licences.py <pip-licenses --format=json output>", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as handle:
        packages = json.load(handle)
    bad = offenders(packages)
    for name, version, rejected in bad:
        print(f"::error::{name}=={version}: licence not allowed by Q-11: {rejected}")
    mpl = [
        p["Name"]
        for p in packages
        if any("MPL" in part.upper() for part in parts(str(p.get("License", ""))))
    ]
    print(f"  {len(packages)} packages checked; MPL-2.0 (use unmodified): {sorted(mpl) or 'none'}")
    if bad:
        return 1
    print("  ok  every licence is MIT / BSD / Apache-2.0 / ISC / PSF / CNRI-Python / MPL-2.0")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
