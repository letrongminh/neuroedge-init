"""A clock that moves only when a test says so, in milliseconds (shared by session tests)."""

#: Longer than a pin's `max_continuous_ms` (60 s on the gate relay) plus `min_interval_ms`: after
#: it the safety envelope (RFC-0007 §3d) lets the next `on` of a pin through.
PAST_THE_ENVELOPE_MS = 62_000


class HandClock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, ms: float) -> None:
        self.now += ms
