"""
Regenerate fixtures/decision_trees/<gate>.truth.json from gates/.

These files are the conformance vectors the C walker must reproduce (ENG-T1).
`tests/test_decision_tree.py` fails when a file is stale, so run this after any
change to a sample gate or to the walker, and review the diff:

    python/.venv/bin/python scripts/generate_truth_tables.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from neuroedge.engine import compile_tree, resolve_gate_file
from neuroedge.engine.decision_tree import truth_table
from neuroedge.paths import gates_dir, repo_root


def render(table: dict) -> str:
    import json

    return json.dumps(table, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    out = repo_root() / "fixtures" / "decision_trees"
    out.mkdir(parents=True, exist_ok=True)
    for path in sorted(Path(gates_dir()).rglob("*.yaml")):
        tree = compile_tree(resolve_gate_file(path))
        target = out / f"{tree['gate']}.truth.json"
        target.write_text(render(truth_table(tree)), encoding="utf-8")
        print(f"wrote {target.relative_to(repo_root())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
