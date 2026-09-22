"""
Repository layout discovery.

The monorepo (Proposal Appendix D) keeps language-neutral assets outside the
Python package: `schemas/`, `gates/`, `fixtures/`, `boards/`, `targets/`. The
SDK has to find them whether it runs from a source checkout, an editable
install, or a wheel installed next to a project directory.
"""

from __future__ import annotations

import os
from pathlib import Path

_MARKERS = ("schemas", "fixtures")


def repo_root() -> Path:
    """
    Locate the monorepo root.

    Resolution order:
      1. ``NEUROEDGE_ROOT`` environment variable, when set.
      2. The nearest ancestor of this file containing `schemas/` and `fixtures/`.
      3. The nearest such ancestor of the current working directory.
    """
    override = os.environ.get("NEUROEDGE_ROOT")
    if override:
        return Path(override).expanduser().resolve()

    for start in (Path(__file__).resolve(), Path.cwd().resolve() / "_"):
        for candidate in start.parents:
            if all((candidate / marker).is_dir() for marker in _MARKERS):
                return candidate

    # Fall back to the checkout layout: python/neuroedge/paths.py -> repo root.
    return Path(__file__).resolve().parents[2]


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
