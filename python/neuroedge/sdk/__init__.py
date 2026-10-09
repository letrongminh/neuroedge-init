"""
`neuroedge.sdk` — what an extension may touch, and nothing else (RFC-0016 §3c, §3e).

This is the part of TSK-I2c-11 that `neuroedge.guard` needs: the two data types a bridge
exchanges with the core, and the version of this surface. A `ToolRequest` is
`tool-call.v1#/$defs/request` — it has **no** `source`: the core stamps the source (RFC-0017
§3b.3), so a bridge cannot say where its call came from. An `Outcome` is data only: the status
and the `ToolResult.content()` of the call, never the value an action body returned. No HAL
name, no `Guard`, no `Conversation` and no name of `neuroedge.__all__` is exported here.

`SDK_VERSION` is the SDK's own SemVer pair `(MAJOR, MINOR)`, independent of the package
version: a plugin that asks for `(1, 0)` works on every SDK 1.x (docs/spec/extension_sdk.md).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..errors import ToolCallError

SDK_VERSION = (1, 0)

__all__ = ["SDK_VERSION", "Outcome", "ToolRequest"]


@dataclass(frozen=True)
class ToolRequest:
    """What a bridge asks for: a tool name, its arguments and, optionally, its own call id."""

    name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    id: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not isinstance(self.id, str):
            raise ToolCallError(
                where="ToolRequest",
                why="`name` and `id` must be strings",
                how="build it as ToolRequest('tool_name', {'argument': value})",
            )
        if not isinstance(self.arguments, Mapping):
            raise ToolCallError(
                where=f"ToolRequest({self.name!r})",
                why=f"`arguments` must be a mapping, not {type(self.arguments).__name__}",
                how="pass the arguments as a dict: ToolRequest('tool_name', {'argument': value})",
            )


@dataclass(frozen=True)
class Outcome:
    """
    The core's answer: `status` is "ALLOW", "BLOCK" or "REJECTED"; `content` is the
    `tool-result.v1` document the caller is told (reason, failed criterion, fallback…).
    """

    status: str
    content: Mapping[str, Any]
