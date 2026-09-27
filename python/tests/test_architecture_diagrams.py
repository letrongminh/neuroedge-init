"""
The architecture posters (docs/architecture/assets/) come from one model in
scripts/gen_architecture_diagrams.py: the SVG a reader sees and the .excalidraw
an editor opens must both match it, and the model itself must pass the layout
lint (no overlapping boxes, no text wider than its box, no arrow to a missing box).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS = REPO_ROOT / "docs" / "architecture" / "assets"
ARCH = REPO_ROOT / "docs" / "architecture"


def test_the_posters_match_their_model() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "gen_architecture_diagrams.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "docs/architecture/assets/ is stale or the diagram model fails its lint.\n"
        "Run: python3 scripts/gen_architecture_diagrams.py\n"
        f"{result.stdout}{result.stderr}"
    )


def test_every_excalidraw_file_is_a_real_drawing() -> None:
    files = sorted((ASSETS / "excalidraw").glob("*.excalidraw"))
    assert files, "no .excalidraw poster"
    for path in files:
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc["type"] == "excalidraw" and doc["version"] == 2, path.name
        boxes = [e for e in doc["elements"] if e["type"] == "rectangle"]
        labels = [e for e in doc["elements"] if e["type"] == "text" and e.get("containerId")]
        # A matrix poster (E-07) has no arrows, so what a real drawing needs is labelled boxes.
        assert len(boxes) >= 5 and labels, (
            f"{path.name} is not a drawing: {len(boxes)} boxes, {len(labels)} labels"
        )
        ids = {e["id"] for e in doc["elements"]}
        for e in doc["elements"]:
            if e.get("containerId"):
                assert e["containerId"] in ids, f"{path.name}: text bound to a missing element"
            for end in ("startBinding", "endBinding"):
                if e.get(end):
                    assert e[end]["elementId"] in ids, f"{path.name}: arrow bound to a missing box"


def test_every_poster_has_both_files_and_is_embedded() -> None:
    svgs = {p.stem for p in (ASSETS / "svg").glob("*.svg")}
    drawings = {p.stem for p in (ASSETS / "excalidraw").glob("*.excalidraw")}
    assert svgs == drawings, f"poster without its pair: {sorted(svgs ^ drawings)}"
    embedded = set()
    for md in ARCH.rglob("*.md"):
        embedded |= set(re.findall(r"assets/svg/([\w.-]+)\.svg", md.read_text(encoding="utf-8")))
    assert svgs <= embedded, f"poster no page shows: {sorted(svgs - embedded)}"
    assert embedded <= svgs, f"page shows a poster that does not exist: {sorted(embedded - svgs)}"


# --- the two language trees ---------------------------------------------------------

MERMAID = re.compile(r"```mermaid\n(.*?)```", re.S)
HEADING = re.compile(r"^(#{1,4}) ", re.M)
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
FENCE = re.compile(r"```.*?```", re.S)


def _headings(text: str) -> list[int]:
    return [len(h) for h in HEADING.findall(FENCE.sub("", text))]


def _tree(lang: str) -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted((ARCH / lang).glob("*.md"))}


def test_the_english_tree_mirrors_the_vietnamese_one() -> None:
    vi, en = _tree("vi"), _tree("en")
    assert vi and set(vi) == set(en), f"files differ: {sorted(set(vi) ^ set(en))}"
    for name in vi:
        assert _headings(vi[name]) == _headings(en[name]), (
            f"{name}: the heading structure of vi/ and en/ differs"
        )
        # diagram labels are English in both trees, so the diagrams are the same bytes
        assert MERMAID.findall(vi[name]) == MERMAID.findall(en[name]), (
            f"{name}: mermaid blocks differ"
        )


def test_every_relative_link_in_the_architecture_docs_resolves() -> None:
    broken = []
    for md in ARCH.rglob("*.md"):
        for target in LINK.findall(md.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("mailto:"):
                continue
            if not (md.parent / target).exists():
                broken.append(f"{md.relative_to(REPO_ROOT)} -> {target}")
    assert not broken, "broken links:\n  " + "\n  ".join(broken)
