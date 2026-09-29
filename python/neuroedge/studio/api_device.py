"""`/api/device…` (docs/spec/studio.md §4). Slice S1b."""

from __future__ import annotations

from typing import Any


def device(server: Any) -> dict[str, Any]:
    raise NotImplementedError


def build(server: Any) -> dict[str, Any]:
    raise NotImplementedError


def golden(server: Any, lang: str, name: str) -> tuple[bytes, str]:
    """The PNG as `(bytes, "image/png")`."""
    raise NotImplementedError
