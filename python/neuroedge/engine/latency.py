"""
Stage latency and the System 1 / System 2 path of each turn (TSK-I4-03, FR-ACE-06,
FR-TEL-03, NFR-OBS-02).

A `TurnMeter` times one turn of a session on the trace's own clock — the clock of
`offset_ms`, injectable, virtual in tests — and splits it into stages that never
overlap:

    perception   the input read and matched: typed text / transcript → command grammar
    system_two   waiting for System 2 (every `respond` / `reply`, or the voice driver's wait)
    gate         `ActionContractEngine.evaluate()` — every gate of the turn, summed
    action       the @action bodies that ran after an ALLOW, summed
    other        the rest of the turn: speech, orchestration, tool plumbing

A stage entered while another is open is not counted twice: the outer one keeps the
time. At the end of the turn the session writes one `turn_latency` event. A trace
exported from a log that holds any (`EventLog.to_trace()`) ends with one
`session_summary`, computed from them by `turn_summary()` and never kept in the log,
so every export carries exactly one, up to date. Event shapes and the meaning of
each `path`: `docs/spec/tool_calling.md` §7.1.

Nothing here decides anything. Replay and the golden comparison ignore both events
(decisions only), and neither carries text, so an anonymised trace stays anonymised.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from typing import Any

Clock = Callable[[], float]  # as `trace_sink.Clock`, which imports this module

TURN_EVENT = "turn_latency"
SUMMARY_EVENT = "session_summary"

STAGES = ("perception", "system_two", "gate", "action")
# system_1: the device's grammar / System 1 served the turn, System 2 never asked.
# system_2: System 2 answered.  fallback: System 2 was asked and could not answer,
# and the device answered locally (Q-14).  none: no model served the turn — nothing
# was recognised, or a person answered with a button.
PATHS = ("system_1", "system_2", "fallback", "none")
# Replies the device says itself because System 2 could not answer.
FALLBACK_REPLIES = frozenset({"offline", "offline_help", "knowledge_local"})
# What a `system_two_call` may report about its cost (FR-MDL-06), summed per turn.
USAGE_KEYS = ("prompt_tokens", "completion_tokens", "cost_usd")


def _ms(value: float) -> float:
    return round(max(0.0, float(value)), 3)


def _number(value: Any) -> float:
    """A number read from a trace; anything else (a hand-edited file) counts as 0."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0.0
    return float(value)


def _add_usage(totals: dict[str, float], usage: Mapping[str, Any]) -> None:
    for key in USAGE_KEYS:
        value = usage.get(key)
        if not isinstance(value, bool) and isinstance(value, int | float):
            totals[key] = totals.get(key, 0) + value
    if "cost_usd" in totals:
        totals["cost_usd"] = round(totals["cost_usd"], 6)


def system_two_usage(events: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    """Tokens and cost the `system_two_call` events among `events` reported, summed."""
    totals: dict[str, float] = {}
    for event in events:
        data = event.get("data")
        if event.get("type") == "system_two_call" and isinstance(data, Mapping):
            _add_usage(totals, data)
    return totals


class TurnMeter:
    """The stage times of one turn, on `clock` (milliseconds)."""

    def __init__(
        self, clock: Clock, *, started_ms: float | None = None, first_event: int = 0
    ) -> None:
        self.clock = clock
        # Index of the turn's first event in the session's log (for its System 2 cost).
        self.first_event = first_event
        now = clock()
        # A start in the future would make the turn negative: clamp it to now.
        self.started_ms = now if started_ms is None else min(float(started_ms), now)
        # Whether System 2 answered: None never asked, True at least one answer,
        # False asked and never answered (`answered()`).
        self.system_two: bool | None = None
        # Set when something other than a recognised command served the turn locally
        # (a spoken "có" / "không"); None: decided from the turn's recognition.
        self.served_locally: bool | None = None
        self._ms = dict.fromkeys(STAGES, 0.0)
        self._open: str | None = None

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        if name not in self._ms:
            raise ValueError(f"unknown stage {name!r}; the stages are {STAGES}")
        if self._open is not None:
            yield  # nested: the stage already open counts this time
            return
        start = self.clock()  # before the stage opens: a clock that raises leaves none open
        self._open = name
        try:
            yield
        finally:
            try:
                self._ms[name] += max(0.0, self.clock() - start)
            finally:
                self._open = None

    def answered(self, ok: bool) -> None:
        """System 2 was asked; `ok` when it answered. One answer in the turn is enough."""
        self.system_two = bool(ok) or bool(self.system_two)

    def add(self, name: str, ms: float) -> None:
        """Time spent in `name` before the meter existed (the voice driver's wait)."""
        if name not in self._ms:
            raise ValueError(f"unknown stage {name!r}; the stages are {STAGES}")
        self._ms[name] += max(0.0, float(ms))

    def event_data(
        self,
        turn: int,
        path: str,
        reply_source: str | None,
        usage: Mapping[str, float] | None = None,
    ) -> dict[str, Any]:
        total = max(0.0, self.clock() - self.started_ms)
        stages = {name: _ms(value) for name, value in self._ms.items()}
        stages["other"] = _ms(total - sum(self._ms.values()))
        data: dict[str, Any] = {
            "turn": turn,
            "path": path,
            "stages_ms": stages,
            "total_ms": _ms(total),
        }
        if reply_source is not None:
            data["reply_source"] = reply_source
        if usage:
            data["usage"] = dict(usage)
        return data


def turn_path(reply_source: str | None, *, system_two: bool | None, served_locally: bool) -> str:
    """
    Which path served a turn. A reply the device said because System 2 could not
    answer is `fallback` even if an earlier round of System 2 did answer; the same
    reply with no System 2 to ask is `system_1` or `none`, from the recognition.
    """
    if reply_source in FALLBACK_REPLIES and system_two is not None:
        return "fallback"
    if system_two is not None:
        return "system_2" if system_two else "fallback"
    return "system_1" if served_locally else "none"


def turn_summary(events: Iterable[Mapping[str, Any]]) -> dict[str, Any] | None:
    """
    `session_summary` data from a trace's `turn_latency` events: turns per path, each
    path's share, per stage the total and the slowest turn, and the System 2 usage
    the turns reported. None when the trace has no `turn_latency` (a trace from
    before TSK-I4-03, a replay, a device session).
    """
    turns = [
        e["data"] for e in events if e.get("type") == TURN_EVENT and isinstance(e.get("data"), dict)
    ]
    if not turns:
        return None
    paths = dict.fromkeys(PATHS, 0)
    usage: dict[str, float] = {}
    for data in turns:
        path = str(data.get("path"))
        paths[path] = paths.get(path, 0) + 1
        if isinstance(data.get("usage"), Mapping):
            _add_usage(usage, data["usage"])
    stages: dict[str, dict[str, float]] = {}
    for name in (*STAGES, "other", "total"):
        values = []
        for data in turns:
            stage_ms = data.get("stages_ms")
            stage_ms = stage_ms if isinstance(stage_ms, Mapping) else {}
            values.append(_number(data.get("total_ms") if name == "total" else stage_ms.get(name)))
        stages[name] = {"sum": _ms(sum(values)), "max": _ms(max(values))}
    summary: dict[str, Any] = {
        "turns": len(turns),
        "paths": paths,
        "shares": {path: round(count / len(turns), 4) for path, count in paths.items()},
        "stages_ms": stages,
    }
    if usage:
        summary["usage"] = usage
    return summary
