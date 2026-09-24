"""
Human confirmation of `on_block: ask` — Q-26, RFC-0006, TSK-S3-26.

A gate that blocks with ``on_block: {action: ask, confirms: [room_empty]}``
asks a person. The person — and only a person, on the device — may answer.
Their "yes" does not bypass the gate: the gate is evaluated again with the
listed criteria stood in for by the confirmation; every other criterion, the
argument limits and fail-closed still apply.

    c.do(light_off)                 → BLOCK ask, pending `confirm_1` (TTL)
    c.confirm("confirm_1", "local_grammar")
                                    → tool_confirmed → gate again → ALLOW → token

Rules (docs/spec/tool_calling.md §6):

* only `HUMAN_SOURCES` may confirm or decline: typed / spoken words matched on
  the device (`local_grammar`) or a button on the device's own page (`ui`).
  `system_two`, `mcp` and anything else are refused — a prompt-injected model
  or an automated client must never answer a question meant for a person;
* one confirmation answers one request, once; it expires after its TTL
  (``max(p95 × 3, 10 s)``);
* it is bound to the gate's digest: if the gate changed in between, it is void;
* a gate that declares no `confirms` only informs — nothing is pending.

Every step is an event in the trace, so a replay reproduces the decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

HUMAN_SOURCES = ("local_grammar", "ui")
MIN_TTL_MS = 10_000
TTL_FACTOR = 3


@dataclass
class PendingConfirmation:
    """One question the device asked a person, awaiting an answer."""

    id: str
    action: str
    arguments: dict[str, Any]
    gate: str
    gate_key: str
    gate_digest: str
    message: str
    confirms: tuple[str, ...]
    created_ms: float  # on the engine's clock — what expiry is decided on
    expires_ms: float
    expires_offset_ms: float = 0.0  # the same instant as a trace offset (what the page shows)
    state: str = "pending"  # pending | confirmed | declined | expired
    context: dict[str, Any] = field(default_factory=dict)

    def to_event_data(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "gate": self.gate,
            "message": self.message,
            "confirms": list(self.confirms),
            "expires_ms": round(self.expires_offset_ms, 3),  # trace time, like offset_ms
            "ttl_ms": round(self.expires_ms - self.created_ms, 3),
        }

    def describe(self) -> dict[str, Any]:
        """What a caller (an LLM, an MCP client) is told: a person must answer."""
        return {
            "id": self.id,
            "message": self.message,
            "expires_in_ms": round(self.expires_ms - self.created_ms, 3),
            "who": "a person on the device (voice or the device's page); not this caller",
        }


class ConfirmationRefused(Exception):
    """An answer that cannot be accepted; `reason` is recorded in the trace."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ConfirmationBook:
    """The pending questions of one conversation."""

    def __init__(self, clock, events) -> None:
        self.clock = clock
        self.events = events
        self._pending: dict[str, PendingConfirmation] = {}
        self._count = 0

    def ttl_ms(self, p95_ms: float) -> float:
        return max(float(p95_ms) * TTL_FACTOR, float(MIN_TTL_MS))

    def open(
        self,
        *,
        action: str,
        arguments: dict[str, Any],
        gate: str,
        gate_key: str,
        gate_digest: str,
        message: str,
        confirms: tuple[str, ...],
        p95_ms: float,
        context: dict[str, Any] | None = None,
    ) -> PendingConfirmation:
        self._count += 1
        now = self.clock()
        ttl = self.ttl_ms(p95_ms)
        pending = PendingConfirmation(
            id=f"confirm_{self._count}",
            action=action,
            arguments=dict(arguments),
            gate=gate,
            gate_key=gate_key,
            gate_digest=gate_digest,
            message=message,
            confirms=tuple(confirms),
            created_ms=now,
            expires_ms=now + ttl,
            expires_offset_ms=self.events.elapsed_ms() + ttl,
            context=dict(context or {}),
        )
        self._pending[pending.id] = pending
        self.events.emit("tool_confirm_requested", pending.to_event_data())
        return pending

    def _expire_due(self) -> None:
        now = self.clock()
        for pending in self._pending.values():
            if pending.state == "pending" and now > pending.expires_ms:
                pending.state = "expired"
                self.events.emit("tool_confirm_expired", {"id": pending.id})

    def get(self, confirm_id: str) -> PendingConfirmation | None:
        return self._pending.get(confirm_id)

    def latest(self) -> PendingConfirmation | None:
        """The most recent question still awaiting an answer, if any."""
        self._expire_due()
        waiting = [p for p in self._pending.values() if p.state == "pending"]
        return waiting[-1] if waiting else None

    def take(self, confirm_id: str, source: str, current_digest: str | None) -> PendingConfirmation:
        """
        Accept a "yes": validate, mark it used, record it. Raises
        `ConfirmationRefused` (already recorded as `tool_confirm_rejected`).
        """
        pending = self._check(confirm_id, source)
        if current_digest is not None and current_digest != pending.gate_digest:
            pending.state = "expired"
            self._refuse(confirm_id, source, "the gate changed since the question was asked")
        pending.state = "confirmed"  # single use: spent even if the gate then blocks again
        self.events.emit("tool_confirmed", {"id": pending.id, "source": source})
        return pending

    def decline(self, confirm_id: str, source: str) -> PendingConfirmation:
        pending = self._check(confirm_id, source)
        pending.state = "declined"
        self.events.emit("tool_confirm_declined", {"id": pending.id, "source": source})
        return pending

    def _check(self, confirm_id: str, source: str) -> PendingConfirmation:
        if source not in HUMAN_SOURCES:
            self._refuse(
                confirm_id,
                source,
                f"only a person on the device may answer ({', '.join(HUMAN_SOURCES)}); "
                f"{source!r} may not",
            )
        self._expire_due()
        pending = self._pending.get(confirm_id)
        if pending is None:
            self._refuse(confirm_id, source, "no such question")
        if pending.state != "pending":
            self._refuse(confirm_id, source, f"the question is already {pending.state}")
        return pending

    def _refuse(self, confirm_id: str, source: str, reason: str):
        self.events.emit(
            "tool_confirm_rejected", {"id": confirm_id, "source": source, "reason": reason}
        )
        raise ConfirmationRefused(reason)
