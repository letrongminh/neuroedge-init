"""
In-memory event log in the `trace.v1` shape.

Every engine, HAL and conversation component writes here, so one session yields
one trace that `neuroedge trace validate` accepts (A7). Time comes from an
injected clock in milliseconds; tests pass a fake one and never touch the wall
clock (CEO-S6-1). The file recorder of TSK-S3-01 is built on top of this.
"""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from ..trace import TRACE_SCHEMA_ID

Clock = Callable[[], float]


def monotonic_ms() -> float:
    return time.monotonic() * 1000.0


class EventLog:
    def __init__(
        self,
        clock: Clock = monotonic_ms,
        *,
        session_id: str | None = None,
        target: str = "sim",
        board_id: str = "sim-default",
        agent_version: str = "unknown@0.0.0",
    ) -> None:
        self.clock = clock
        self._t0 = clock()
        self.metadata: dict[str, Any] = {
            "session_id": session_id or f"sess_{secrets.token_hex(4)}",
            "timestamp_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "target": target,
            "board_id": board_id,
            "agent_version": agent_version,
        }
        self.events: list[dict[str, Any]] = []

    def elapsed_ms(self) -> int:
        """Milliseconds since the log started, on the same clock as `offset_ms`."""
        return max(0, int(self.clock() - self._t0))

    @property
    def session_id(self) -> str:
        return self.metadata["session_id"]

    def emit(self, type: str, data: dict[str, Any]) -> None:
        offset = max(0, int(self.clock() - self._t0))
        self.events.append({"offset_ms": offset, "type": type, "data": dict(data)})

    def of_type(self, type: str) -> list[dict[str, Any]]:
        return [event["data"] for event in self.events if event["type"] == type]

    def to_trace(self) -> dict[str, Any]:
        return {
            "$schema": TRACE_SCHEMA_ID,
            "metadata": dict(self.metadata),
            "events": [dict(event) for event in self.events],
        }
