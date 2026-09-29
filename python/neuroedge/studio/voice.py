"""
`/api/voice…` — the microphone session behind the studio page (docs/spec/studio.md
§1, §4; TSK-I4-04, Q-50). Slice S2.
"""

from __future__ import annotations

from typing import Any


def status(server: Any) -> dict[str, Any]:
    if server.voice is None:
        return {"ok": True, "enabled": False, "running": False}
    raise NotImplementedError


def mute(server: Any, body: dict[str, Any]) -> dict[str, Any]:
    if server.voice is None:
        return {
            "ok": False,
            "error": {
                "why": "the studio runs without a microphone",
                "how": "restart it with --mic",
            },
        }
    raise NotImplementedError


def start(server: Any, *, half_duplex: bool = False) -> None:
    """Open the microphone behind the page (`studio --mic`); sets `server.voice`."""
    raise NotImplementedError
