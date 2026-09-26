"""
Hatch build hook: ship the language-neutral assets inside the package (TSK-S3-17).

`schemas/`, `boards/`, `gates/`, `fixtures/traces/`, `fixtures/agents/` and
`fixtures/tool_calls/` (the Gated Tool Profile corpus `neuroedge verify` runs) live at
the monorepo root, outside `python/`. A wheel without them installs, but
`neuroedge build`, `run`, `test` and `gate lint` all fail — measured 2026-09-23.
This hook copies them to `neuroedge/_data/`, where `neuroedge.paths` finds them
when there is no source checkout.

`neuroedge build --target esp32s3` copies the firmware sources into the agent's
ESP-IDF project (TSK-I3-01), so the wheel carries them too — only the files
`FIRMWARE_SOURCES` names, the project's own C99 and build files. Never build
output, and never a vendored third-party component: ESP-SR's licence is for
Espressif chips only and must not reach the Python package (`TODOS.md` #17).
`tests/test_packaging.py` keeps the list equal to `neuroedge.engine.firmware.SOURCES`.

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
FIRMWARE = "targets/esp32s3"
FIRMWARE_SOURCES = (
    "CMakeLists.txt",
    "partitions.csv",
    "sdkconfig.defaults",
    "sdkconfig.qemu",
    "main/CMakeLists.txt",
    "main/Kconfig.projbuild",
    "main/*.c",
    "main/*.h",
    "main/idf_component.yml",
    "main/vectors/*.h",
    "components/ne_gate/CMakeLists.txt",
    "components/ne_gate/include/*.h",
    "components/ne_gate/src/*.c",
    "components/ne_trace/CMakeLists.txt",
    "components/ne_trace/include/*.h",
    "components/ne_trace/src/*.c",
)
# Never shipped from any asset: what building in place leaves behind — an agent's
# `neuroedge build` (build/, its esp32s3/ project) or `idf.py` inside fixtures/agents/<name>/
# (build/, managed_components/, sdkconfig) — and Python caches. `sdkconfig.defaults` and
# `sdkconfig.qemu` are sources; `sdkconfig` is a machine's own configuration.
EXCLUDED_DIRS = ("build", "managed_components", "__pycache__", ".pytest_cache", ".venv")
EXCLUDED_FILES = ("sdkconfig", "sdkconfig.old", "dependencies.lock", ".neuroedge-build")
EXCLUDED_SUFFIXES = (".pyc",)


def shipped(path: Path, repo: Path) -> bool:
    """Whether `path`, a file under `repo`, may go into the wheel."""
    parts = path.relative_to(repo).parts
    return (
        path.is_file()
        and not any(part in EXCLUDED_DIRS for part in parts)
        and path.name not in EXCLUDED_FILES
        and path.suffix not in EXCLUDED_SUFFIXES
    )


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        repo = Path(self.root).parent
        if not (repo / "schemas").is_dir():
            # Building from an sdist: the assets are already under neuroedge/_data.
            return
        for asset in ASSETS:
            for path in sorted((repo / asset).rglob("*")):
                if not shipped(path, repo):
                    continue
                relative = path.relative_to(repo).as_posix()
                build_data["force_include"][str(path)] = f"{TARGET}/{relative}"
        for pattern in FIRMWARE_SOURCES:
            for path in sorted((repo / FIRMWARE).glob(pattern)):
                if shipped(path, repo):
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
