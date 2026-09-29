"""`/api/agent`, `/api/gates…`, `/api/mcp` (docs/spec/studio.md §4). Slice S1a."""

from __future__ import annotations

from typing import Any


def agent(server: Any) -> dict[str, Any]:
    raise NotImplementedError


def gates(server: Any) -> dict[str, Any]:
    raise NotImplementedError


def gate(server: Any, name: str) -> dict[str, Any]:
    raise NotImplementedError


def whatif(server: Any, name: str, body: dict[str, Any]) -> dict[str, Any]:
    raise NotImplementedError


def mcp(server: Any) -> dict[str, Any]:
    raise NotImplementedError
