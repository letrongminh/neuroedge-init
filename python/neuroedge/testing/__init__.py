"""
Action CI (FR-CI-01→04): record a session, replay it on a live HAL, assert the
gate verdicts and the pins, compare against a golden reference.

    from neuroedge.testing import replay, scenario

    s = replay("traces/unverified_attempt.json")
    assert s.action("unlock_door").blocked
    assert s.pin("door_lock").never_pulsed()

`replay()` and `scenario()` are the synchronous entry points of proposal §4.7;
`TracePlayer` is the async one. Both recompute verdicts and pin commands — see
`player.py`.
"""

from pathlib import Path
from typing import Any

from .assertions import (
    assert_action_aborted,
    assert_escalated_to,
    assert_gate_allowed,
    assert_gate_blocked,
    assert_never_pulsed,
    assert_pin_pulsed,
)
from .golden import GoldenComparator, GoldenDiffResult, assert_matches_golden, safety_view
from .player import (
    ActionState,
    GateState,
    RecordedStep,
    ReplayResult,
    TracePlayer,
    recorded_steps,
    replay_sync,
)
from .recorder import TraceRecorder

# Kept for code written against the Sprint 1 stub.
ReplaySession = ReplayResult


def replay(
    trace: str | Path | dict[str, Any],
    slow: str | None = None,
    target: str = "sim",
    **kwargs: Any,
) -> ReplayResult:
    """
    Replay a trace on `target` and return what the gate and the pins did.

    `slow` names a System 2 model to swap in. It is accepted so a test can say
    what it varied, and it never changes a verdict: System 2 text is not replayed
    or asserted on (FR-CI-LVL, L3).
    """
    return replay_sync(trace, slow=slow, target=target, **kwargs)


def scenario(
    trace: str | Path | dict[str, Any],
    network: str = "online",
    target: str = "sim",
    **kwargs: Any,
) -> ReplayResult:
    """
    Replay a trace under a changed condition. ``network="offline"`` keeps only
    the session-context facts and makes every model answer unreachable, so a
    fail-closed gate blocks with `gate_unreachable` (Q-14).
    """
    return replay_sync(trace, network=network, target=target, **kwargs)


__all__ = [
    "ActionState",
    "GateState",
    "GoldenComparator",
    "GoldenDiffResult",
    "RecordedStep",
    "ReplayResult",
    "ReplaySession",
    "TracePlayer",
    "TraceRecorder",
    "assert_action_aborted",
    "assert_escalated_to",
    "assert_gate_allowed",
    "assert_gate_blocked",
    "assert_matches_golden",
    "assert_never_pulsed",
    "assert_pin_pulsed",
    "recorded_steps",
    "replay",
    "safety_view",
    "scenario",
]
