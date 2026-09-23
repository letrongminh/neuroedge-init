"""
The verdict vocabulary shared by the decision tree, the Gate Engine and traces.

A `Reason` is a *verdict value*, never an exception: every way a gate can block
must land in the trace so a session can be replayed and explained. Exceptions
are reserved for contract violations (a forged or replayed token, a direct call
to an actuator) — things that should never be retried.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GateVerdict(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


class Reason(StrEnum):
    # A fact was present but not admitted, or its confidence fell below the floor.
    CONDITION_NOT_MET = "condition_not_met"
    # No fact after every source was asked, or the fact lies outside the domain.
    CRITERION_UNAVAILABLE = "criterion_unavailable"
    # The clause has a confidence floor and the fact carries no confidence at all.
    # Treated neither as 0 nor as 1 (design doc, closed question 10).
    CONFIDENCE_UNAVAILABLE = "confidence_unavailable"
    # The adjudicator is unreachable and no local fallback can run (Q-14).
    GATE_UNREACHABLE = "gate_unreachable"
    # Adjudication took longer than budget.p95_latency_ms (FR-GATE-09).
    BUDGET_EXCEEDED = "budget_exceeded"
    # The action names a gate the engine does not hold.
    GATE_NOT_FOUND = "gate_not_found"
    # Verdict-token failures, kept apart so a trace says which one happened.
    TOKEN_REPLAYED = "token_replayed"
    TOKEN_EXPIRED = "token_expired"


# Reasons produced when the adjudicator itself failed, as opposed to answering
# "no". A degraded verdict applies `budget.fail` and skips `on_block` (Q-17).
DEGRADED_REASONS = frozenset({Reason.GATE_UNREACHABLE, Reason.BUDGET_EXCEEDED})


@dataclass(frozen=True)
class Fact:
    """
    One adjudicated value for one criterion.

    `value` is ``True``/``False`` for a bool criterion and a level or option name
    otherwise. `confidence` is ``None`` when the source gave none, which is
    different from ``0.0``.
    """

    value: bool | str | None
    confidence: float | None = None
    source: str = "context"
