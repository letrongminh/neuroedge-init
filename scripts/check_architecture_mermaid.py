#!/usr/bin/env python3
"""Render every ```mermaid block of docs/architecture/ with mermaid-cli; fail on any error.

GitHub renders these blocks; one syntax error turns a diagram into raw text, so
every block is rendered here before it ships. Needs mermaid-cli (`mmdc`):

    npm install -g @mermaid-js/mermaid-cli     # or: NE_MMDC=/path/to/mmdc
    python3 scripts/check_architecture_mermaid.py

Exit 0 when every block renders, 1 otherwise (each failure names file:line).
Not run in CI (it needs Node and a headless Chrome); run it with every change to
a diagram, as docs/architecture/README.md says.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCK = re.compile(r"```mermaid\n(.*?)```", re.S)


def main() -> int:
    mmdc = os.environ.get("NE_MMDC") or shutil.which("mmdc")
    if not mmdc:
        print("mmdc not found: npm install -g @mermaid-js/mermaid-cli, or set NE_MMDC", file=sys.stderr)
        return 2
    total = failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        for md in sorted((ROOT / "docs" / "architecture").rglob("*.md")):
            text = md.read_text(encoding="utf-8")
            for m in BLOCK.finditer(text):
                total += 1
                src = Path(tmp) / (hashlib.sha1(m.group(1).encode()).hexdigest()[:12] + ".mmd")
                src.write_text(m.group(1), encoding="utf-8")
                run = subprocess.run(
                    [mmdc, "-q", "-i", str(src), "-o", str(src.with_suffix(".svg"))],
                    capture_output=True,
                    text=True,
                )
                if run.returncode != 0:
                    failed += 1
                    line = text[: m.start()].count("\n") + 1
                    first = next((s for s in (run.stderr or run.stdout).splitlines() if "rror" in s), "?")
                    print(f"FAIL {md.relative_to(ROOT)}:{line}: {first.strip()}")
    print(f"{total - failed}/{total} mermaid blocks render")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
