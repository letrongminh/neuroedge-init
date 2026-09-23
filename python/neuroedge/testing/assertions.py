"""
Safety assertions for Action CI (TSK-S3-03, FR-CI-03, FR-CI-LVL).

Every assertion reads what the gate decided and what the pins did — never what
System 2 said. They accept a `ReplayResult`, a `SimSession`, a trace dict, or
(for pins) a HAL, and raise `AssertionError` with the evidence, so a failing
Action CI run says which verdict or which pin was wrong.

    result = replay("traces/unverified_attempt.json")
    assert_gate_blocked(result, "unlock_door", reason="condition_not_met")
    assert_escalated_to(result, "human_receptionist")
    assert_never_pulsed(result, "door_lock")

L3 is enforced, not just documented: passing text where a session is expected
raises, and `ReplayResult.replies` raises.
"""

from __future__ import annotations

from typing import Any

from ..hal.sim import ABORTED_BY_BARGE_IN

L3 = (
    "L3 (FR-CI-LVL): System 2 text is not deterministic and is never asserted on; "
    "assert the gate verdict and the pins instead"
)


def _events(subject: Any) -> list[dict[str, Any]]:
    if isinstance(subject, str):
        raise AssertionError(f"{L3} — got the string {subject[:40]!r}")
    if isinstance(subject, dict) and "events" in subject:
        return subject["events"]
    replayed = getattr(subject, "replayed", None)
    if replayed is not None:
        return replayed["events"]
    log = getattr(subject, "events", None)
    if log is not None and hasattr(log, "events"):
        return log.events
    raise TypeError(f"expected a ReplayResult, SimSession or trace, not {type(subject).__name__}")


def _hal(subject: Any) -> Any:
    if isinstance(subject, str):
        raise AssertionError(f"{L3} — got the string {subject[:40]!r}")
    hal = getattr(subject, "hal", None)
    return hal if hal is not None else subject


def _evaluations(subject: Any, gate: str) -> list[dict[str, Any]]:
    """The results of every evaluation of `gate` (by name, or by name@version)."""
    found, current = [], None
    for event in _events(subject):
        if event["type"] == "gate_evaluation_begin":
            current = event["data"].get("gate", "")
        elif event["type"] == "gate_evaluation_result" and current is not None:
            if current == gate or current.partition("@")[0] == gate:
                found.append(event["data"])
            current = None
    return found


def _summary(subject: Any) -> str:
    rows, current = [], None
    for event in _events(subject):
        if event["type"] == "gate_evaluation_begin":
            current = event["data"].get("gate")
        elif event["type"] == "gate_evaluation_result":
            data = event["data"]
            rows.append(f"{current}: {data['verdict']} ({data.get('reason', '-')})")
    return "; ".join(rows) or "no gate was evaluated"


def assert_gate_allowed(subject: Any, gate: str) -> None:
    """`gate` was evaluated, and allowed at least once."""
    results = _evaluations(subject, gate)
    if not any(r["verdict"] == "ALLOW" for r in results):
        raise AssertionError(f"gate {gate!r} never allowed; verdicts: {_summary(subject)}")


def assert_gate_blocked(subject: Any, gate: str, reason: str | None = None) -> None:
    """`gate` was evaluated and **never** allowed; with `reason`, its last block says so."""
    results = _evaluations(subject, gate)
    if not results:
        raise AssertionError(f"gate {gate!r} was never evaluated; verdicts: {_summary(subject)}")
    allowed = [r for r in results if r["verdict"] == "ALLOW"]
    if allowed:
        raise AssertionError(
            f"gate {gate!r} allowed {len(allowed)} of {len(results)} time(s); "
            f"verdicts: {_summary(subject)}"
        )
    if reason is not None and results[-1].get("reason") != reason:
        raise AssertionError(
            f"gate {gate!r} blocked with reason {results[-1].get('reason')!r}, not {reason!r}"
        )


def assert_escalated_to(subject: Any, recipient: str) -> None:
    """Some block escalated to `recipient` (on_block: escalate, Q-17)."""
    escalations = [
        e["data"].get("escalated_to")
        for e in _events(subject)
        if e["type"] == "gate_evaluation_result" and e["data"].get("action") == "escalate"
    ]
    if recipient not in escalations:
        raise AssertionError(f"no block escalated to {recipient!r}; escalations: {escalations}")


def assert_pin_pulsed(
    subject: Any, pin: str, duration_ms: int | None = None, *, times: int | None = None
) -> None:
    """`pin` was pulsed; with `duration_ms`, some pulse lasted exactly that; with `times`, that often."""
    state = _hal(subject).pin(pin)
    pulses = state.pulses
    if not pulses:
        raise AssertionError(f"pin {pin!r} was never pulsed; commands: {state.commands}")
    if duration_ms is not None and duration_ms not in pulses:
        raise AssertionError(f"pin {pin!r} pulses were {pulses} ms, none {duration_ms} ms")
    if times is not None and len(pulses) != times:
        raise AssertionError(f"pin {pin!r} was pulsed {len(pulses)} time(s), not {times}")


def assert_never_pulsed(subject: Any, pin: str) -> None:
    """`pin` accepted no command at all — not a pulse, not an on() or off()."""
    state = _hal(subject).pin(pin)
    if not state.never_pulsed():
        raise AssertionError(f"pin {pin!r} was driven: {state.commands}")


def assert_action_aborted(subject: Any, pin: str, reason: str = ABORTED_BY_BARGE_IN) -> None:
    """A pending command on `pin` was cancelled with `reason` (RB-3)."""
    aborts = [e["data"] for e in _events(subject) if e["type"] == "actuator_aborted"]
    if not any(a.get("pin") == pin and a.get("reason") == reason for a in aborts):
        raise AssertionError(f"no abort of {pin!r} with reason {reason!r}; aborts: {aborts}")


__all__ = [
    "assert_action_aborted",
    "assert_escalated_to",
    "assert_gate_allowed",
    "assert_gate_blocked",
    "assert_never_pulsed",
    "assert_pin_pulsed",
]
