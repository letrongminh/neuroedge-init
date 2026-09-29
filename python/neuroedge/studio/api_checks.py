"""`/api/traces…`, `/api/record`, `/api/lint`, `/api/verify`, `/api/test` (docs/spec/studio.md §4). Slice S1b."""

from __future__ import annotations

from typing import Any


def traces(server: Any) -> dict[str, Any]:
    raise NotImplementedError


def trace(server: Any, name: str) -> dict[str, Any]:
    raise NotImplementedError


def replay(server: Any, name: str) -> dict[str, Any]:
    raise NotImplementedError


def record(server: Any) -> dict[str, Any]:
    raise NotImplementedError


def lint(server: Any) -> dict[str, Any]:
    raise NotImplementedError


def verify(server: Any) -> dict[str, Any]:
    raise NotImplementedError


def test(server: Any) -> dict[str, Any]:
    raise NotImplementedError
