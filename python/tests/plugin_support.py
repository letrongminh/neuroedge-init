"""
Plugins installed for a test without pip, a build backend or the network.

`install()` writes what pip would leave in `site-packages` — the package files and a
`<name>-<version>.dist-info` with `METADATA`, `entry_points.txt`, `RECORD` (and `direct_url.json`
for an editable install) — into a directory the test puts on `sys.path`. `importlib.metadata` then
finds the distribution exactly as it finds one pip installed, so the loader under test runs its
real discovery. The reference plugins live in `fixtures/compliance/actuators/` with their own
`pyproject.toml`; `scripts/wheel_smoke.sh` installs one of them with pip.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import importlib
import shutil
import sys
import tomllib
from collections.abc import Iterator, Mapping
from pathlib import Path

from neuroedge.paths import repo_root

ACTUATORS = repo_root() / "fixtures" / "compliance" / "actuators"
REFERENCE = ACTUATORS / "valid" / "neuroedge-ref-actuators"
FLAWED = ACTUATORS / "invalid" / "neuroedge-ref-flawed"


def _record_line(root: Path, path: Path) -> str:
    data = path.read_bytes()
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    return f"{path.relative_to(root).as_posix()},sha256={digest},{len(data)}"


def write_distribution(
    target: Path,
    name: str,
    version: str,
    entry_points: Mapping[str, Mapping[str, str]],
    files: Mapping[str, str],
    *,
    editable: bool = False,
) -> Path:
    """A distribution in `target`: `files` (relative path -> source) and its dist-info."""
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for relative, source in files.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        written.append(path)
    info = target / f"{name.replace('-', '_')}-{version}.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n", encoding="utf-8"
    )
    lines = [
        f"[{group}]\n" + "".join(f"{key} = {value}\n" for key, value in entries.items())
        for group, entries in entry_points.items()
    ]
    (info / "entry_points.txt").write_text("\n".join(lines), encoding="utf-8")
    if editable:
        (info / "direct_url.json").write_text(
            '{"url": "file:///src", "dir_info": {"editable": true}}', encoding="utf-8"
        )
        written = []  # an editable install lists no source files (RFC-0016 §2)
    records = [_record_line(target, p) for p in written]
    records += [f"{info.name}/{f},," for f in ("METADATA", "entry_points.txt", "RECORD")]
    (info / "RECORD").write_text("\n".join(records) + "\n", encoding="utf-8")
    return info


def install(project: Path, target: Path, *, editable: bool = False) -> str:
    """Install the fixture distribution at `project` (its pyproject.toml) into `target`."""
    meta = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    packages = meta.get("entry-points", {})
    files: dict[str, str] = {}
    for package in (p for p in project.iterdir() if p.is_dir() and (p / "__init__.py").is_file()):
        for source in package.rglob("*.py"):
            files[source.relative_to(project).as_posix()] = source.read_text(encoding="utf-8")
    write_distribution(target, meta["name"], meta["version"], packages, files, editable=editable)
    return meta["name"]


def forget(*packages: str) -> None:
    """Drop imported plugin modules, so the next import reads the newly installed files."""
    for name in list(sys.modules):
        if name.split(".", 1)[0] in packages:
            del sys.modules[name]
    importlib.invalidate_caches()


@contextlib.contextmanager
def on_path(directory: Path) -> Iterator[Path]:
    """`directory` on `sys.path` for the block, and every module imported from it forgotten after."""
    sys.path.insert(0, str(directory))
    importlib.invalidate_caches()
    before = set(sys.modules)
    try:
        yield directory
    finally:
        sys.path.remove(str(directory))
        for name in set(sys.modules) - before:
            module = sys.modules.get(name)
            origin = getattr(module, "__file__", None) or ""
            if origin.startswith(str(directory)):
                del sys.modules[name]
        importlib.invalidate_caches()


@contextlib.contextmanager
def reference_plugins(tmp: Path, *, flawed: bool = False) -> Iterator[Path]:
    """The reference distribution (and the flawed one) installed in `tmp`, on `sys.path`."""
    install(REFERENCE, tmp)
    if flawed:
        install(FLAWED, tmp)
    with on_path(tmp):
        yield tmp


def copy_project(project: Path, target: Path) -> Path:
    shutil.copytree(project, target, ignore=shutil.ignore_patterns("__pycache__"))
    return target
