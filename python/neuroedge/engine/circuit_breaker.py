"""
Degradation circuit breaker (TSK-S2-04, FR-ACE-03, NFR-REL-02).

Wraps SystemOne's *primary* provider. After `failure_threshold` consecutive
failures the breaker opens and the primary is skipped — straight to the local
fallback — so a dead provider stops eating every gate's latency budget. After
`cooldown_ms` one trial call is let through (half-open); success closes the
breaker, failure re-opens it.

The breaker only routes. It never produces an ALLOW: with the breaker open and
no fallback, SystemOne answers `Unavailable("offline")` and the gate fails
closed with `gate_unreachable`, like any other unreachable adjudicator.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

from .trace_sink import Clock, monotonic_ms


class BreakerState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class _Sink(Protocol):
    def emit(self, type: str, data: dict[str, Any]) -> None: ...


class DegradationBreaker:
    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        cooldown_ms: float = 30_000,
        clock: Clock = monotonic_ms,
        events: _Sink | None = None,
    ) -> None:
        if failure_threshold < 1 or cooldown_ms <= 0:
            raise ValueError("failure_threshold must be ≥ 1 and cooldown_ms > 0")
        self.failure_threshold = failure_threshold
        self.cooldown_ms = cooldown_ms
        self.clock = clock
        self.events = events
        self._state = BreakerState.CLOSED
        self._failures = 0
        self._opened_at = 0.0

    @property
    def state(self) -> BreakerState:
        if self._state is BreakerState.OPEN and self.clock() - self._opened_at >= self.cooldown_ms:
            self._move(BreakerState.HALF_OPEN, "cooldown elapsed")
        return self._state

    def allow_primary(self) -> bool:
        """False while open: skip the primary and go to the fallback."""
        return self.state is not BreakerState.OPEN

    def record_success(self) -> None:
        self._failures = 0
        if self._state is not BreakerState.CLOSED:
            self._move(BreakerState.CLOSED, "primary answered")

    def record_failure(self, reason: str) -> None:
        self._failures += 1
        if self._state is BreakerState.HALF_OPEN or self._failures >= self.failure_threshold:
            self._opened_at = self.clock()
            if self._state is not BreakerState.OPEN:
                self._move(BreakerState.OPEN, reason)

    def _move(self, state: BreakerState, reason: str) -> None:
        self._state = state
        if self.events is not None:
            self.events.emit("circuit_breaker", {"state": str(state), "reason": reason})
