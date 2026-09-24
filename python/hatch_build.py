"""
Hatch build hook: ship the language-neutral assets inside the package (TSK-S3-17).

`schemas/`, `boards/`, `gates/`, `fixtures/traces/`, `fixtures/agents/` and
`fixtures/tool_calls/` (the Gated Tool Profile corpus `neuroedge verify` runs) live at
the monorepo root, outside `python/`. A wheel without them installs, but
`neuroedge build`, `run`, `test` and `gate lint` all fail — measured 2026-09-23.
This hook copies them to `neuroedge/_data/`, where `neuroedge.paths` finds them
when there is no source checkout.

It runs for the sdist too, so a wheel built *from* the sdist (what PyPI users
get) already has `neuroedge/_data/` as ordinary package files and needs no repo.

The PyPI page is the root `README.md` (TSK-S3-20), also outside `python/`, and
hatchling refuses a `readme` path outside the project directory. So `readme` is
dynamic and `ReadmeHook` reads the root file. The sdist records it in `PKG-INFO`;
hatchling fills dynamic fields from `PKG-INFO` when it builds the wheel from that
sdist, so the hook never runs there. No copy of the README is committed.
"""

from __future__ import annotations

from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.metadata.plugin.interface import MetadataHookInterface

ASSETS = (
    "schemas",
    "boards",
    "gates",
    "fixtures/traces",
    "fixtures/agents",
    "fixtures/tool_calls",
)
TARGET = "neuroedge/_data"


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        repo = Path(self.root).parent
        if not (repo / "schemas").is_dir():
            # Building from an sdist: the assets are already under neuroedge/_data.
            return
        for asset in ASSETS:
            for path in sorted((repo / asset).rglob("*")):
                if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                    continue
                relative = path.relative_to(repo).as_posix()
                build_data["force_include"][str(path)] = f"{TARGET}/{relative}"


class ReadmeHook(MetadataHookInterface):
    def update(self, metadata: dict) -> None:
        if "readme" in metadata:
            return  # building from an sdist: hatchling already took it from PKG-INFO
        readme = Path(self.root).parent / "README.md"
        metadata["readme"] = {
            "content-type": "text/markdown",
            "text": readme.read_text(encoding="utf-8"),
        }
