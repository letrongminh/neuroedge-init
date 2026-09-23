"""
Repository layout discovery.

The monorepo (Proposal Appendix D) keeps language-neutral assets outside the
Python package: `schemas/`, `gates/`, `fixtures/`, `boards/`, `targets/`. The
SDK has to find them whether it runs from a source checkout, an editable
install, or an installed wheel — which carries a copy under `neuroedge/_data/`
(TSK-S3-17, `python/hatch_build.py`).
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from .errors import NeuroEdgeError

_MARKERS = ("schemas", "fixtures")
PACKAGED = Path(__file__).resolve().parent / "_data"


def _has_assets(candidate: Path) -> bool:
    return all((candidate / marker).is_dir() for marker in _MARKERS)


def resolve_root(override: str | None, starts: Iterable[Path], packaged: Path = PACKAGED) -> Path:
    """
    The asset root, in order:

      1. ``NEUROEDGE_ROOT``, when set and non-empty;
      2. the nearest ancestor of this file with `schemas/` and `fixtures/` —
         a source checkout or an editable install;
      3. the copy packaged in the wheel (`neuroedge/_data/`);
      4. the nearest such ancestor of the working directory.

    Nothing found is an error, never a guess: a wrong root makes every later
    diagnostic point at a path that does not exist.
    """
    if override:
        return Path(override).expanduser().resolve()
    starts = list(starts)
    for candidate in starts[0].parents if starts else ():
        if _has_assets(candidate):
            return candidate
    if _has_assets(packaged):
        return packaged
    for start in starts[1:]:
        for candidate in start.parents:
            if _has_assets(candidate):
                return candidate
    raise NeuroEdgeError(
        where="neuroedge.paths.repo_root()",
        why=(
            "found no schemas/ and fixtures/: not in a NeuroEdge source checkout, and this "
            f"install has no packaged assets at {packaged}"
        ),
        how="reinstall neuroedge from PyPI or a built wheel, or set NEUROEDGE_ROOT=<checkout>",
    )


def repo_root() -> Path:
    return resolve_root(
        os.environ.get("NEUROEDGE_ROOT"),
        (Path(__file__).resolve(), Path.cwd().resolve() / "_"),
    )


def schemas_dir() -> Path:
    return repo_root() / "schemas"


def gates_dir() -> Path:
    return repo_root() / "gates"


def fixtures_dir() -> Path:
    return repo_root() / "fixtures"


def boards_dir() -> Path:
    return repo_root() / "boards"


def schema_path(name: str) -> Path:
    """Path to an official schema, e.g. ``schema_path("gate.v1.json")``."""
    return schemas_dir() / name
