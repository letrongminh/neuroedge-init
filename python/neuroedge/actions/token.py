"""
Single-use verdict tokens (TSK-S2-05, FR-ACE-02; design doc, closed question 12).

An ALLOW becomes a token, and the HAL moves a pin only on a token this ledger
issued, for that pin, once, within its TTL:

* **TTL = p95 × 3.** A TTL of exactly p95 would expire ~5% of *valid* tokens by
  the definition of a percentile.
* **One way:** issued → consumed per pin, and closed when `c.do()` returns.
  Any later use is `token_replayed`.
* **A lease for a motion channel** (RFC-0011 §3c, Q-37). A token that grants `motion`
  channels carries one lease per channel: valid for the channel's `lease_ms` from the
  verdict, for exactly one command on that channel, and independent of `TTL_FACTOR`. A
  channel a token does not grant, a lease already used, or a lease past its time is refused;
  the only way to renew one is a new gate pass, a new token. `authorize` answers with the
  lease time that is left, which the HAL turns into the channel's deadline.
* **`process_instance_id`.** A token minted by another process instance (a
  restart) is refused as `token_expired`.

The threat in scope is bypassing a gate *by mistake* — a stale token, a
copy-paste of an earlier call. A deliberate forger inside the same process is
out of scope (docs/spec/threat_model.md, TODOS.md #2). Nonces never enter the
trace.
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from ..errors import ActionContractViolation, TokenReplayError

TTL_FACTOR = 3
PROCESS_INSTANCE_ID = uuid.uuid4().hex


class _Sink(Protocol):
    def emit(self, type: str, data: dict[str, Any]) -> None: ...


@dataclass(frozen=True)
class VerdictToken:
    nonce: str
    gate: str
    gate_digest: str
    action: str
    pins: frozenset[str]
    session_id: str
    process_instance_id: str
    issued_at_ms: float
    ttl_ms: float
    # RFC-0011 §3c: (channel, lease_ms) for each motion channel the action may command.
    leases: tuple[tuple[str, float], ...] = ()

    @property
    def channels(self) -> frozenset[str]:
        return frozenset(channel for channel, _ in self.leases)

    def lease_ms(self, channel: str) -> float | None:
        return dict(self.leases).get(channel)

    def __repr__(self) -> str:  # never print the nonce
        extra = f" channels={sorted(self.channels)}" if self.leases else ""
        return f"<VerdictToken {self.action} via {self.gate} pins={sorted(self.pins)}{extra}>"


class TokenLedger:
    def __init__(
        self,
        clock: Callable[[], float],
        *,
        events: _Sink | None = None,
        process_instance_id: str = PROCESS_INSTANCE_ID,
    ) -> None:
        self.clock = clock
        self.events = events
        self.process_instance_id = process_instance_id
        self._issued: dict[str, VerdictToken] = {}
        self._consumed: dict[str, set[str]] = {}
        self._closed: set[str] = set()

    def issue(
        self,
        *,
        gate: str,
        gate_digest: str,
        action: str,
        pins: frozenset[str],
        session_id: str,
        p95_ms: float,
        channels: Mapping[str, float] | None = None,
    ) -> VerdictToken:
        token = VerdictToken(
            nonce=secrets.token_hex(16),
            gate=gate,
            gate_digest=gate_digest,
            action=action,
            pins=frozenset(pins),
            session_id=session_id,
            process_instance_id=self.process_instance_id,
            issued_at_ms=self.clock(),
            ttl_ms=p95_ms * TTL_FACTOR,
            leases=tuple(sorted((channels or {}).items())),
        )
        self._issued[token.nonce] = token
        self._consumed[token.nonce] = set()
        return token

    def close(self, token: VerdictToken) -> None:
        self._closed.add(token.nonce)

    # -- the HAL authorizer --------------------------------------------------
    def authorize(self, signature: Any, pin: str, called_from: str) -> float | None:
        """
        Check the proof for `pin`, a `digital.out` pin or a `motion` channel the token grants.
        A pin is spent once and answers None; a channel's lease is spent once and answers the
        lease time still left, in ms (RFC-0011 §3c).
        """
        channel = isinstance(signature, VerdictToken) and pin in signature.channels
        where = f"{called_from} -> {'motion' if channel else 'digital.out'} {pin!r}"
        if not isinstance(signature, VerdictToken):
            self._reject(pin, "not_a_token", "NE1001")
            raise ActionContractViolation(
                where=where,
                why=f"expected a verdict token issued by c.do(), got {type(signature).__name__}",
                how="drive pins only from an @action body run by await c.do(...)",
            )
        if signature.process_instance_id != self.process_instance_id:
            self._reject(pin, "token_expired", "NE1002")
            raise TokenReplayError(
                where=where,
                why="the token was minted by another process instance (a restart)",
                how="re-run the action through c.do() to obtain a fresh verdict",
                reason="token_expired",
            )
        if self._issued.get(signature.nonce) != signature:
            self._reject(pin, "unknown_token", "NE1001")
            raise ActionContractViolation(
                where=where,
                why="this token was not issued by the session's ledger",
                how="tokens cannot be constructed by hand; call the action through c.do()",
            )
        if channel:
            return self._authorize_lease(signature, pin, where)
        if pin not in signature.pins:
            self._reject(pin, "pin_not_granted", "NE1001")
            raise ActionContractViolation(
                where=where,
                why=(
                    f"the token grants {sorted(signature.pins)}"
                    + (f" and channels {sorted(signature.channels)}" if signature.leases else "")
                    + f", not {pin!r}"
                ),
                how=f"declare 'digital.out:{pin}' (or 'motion:{pin}' for a channel) in the "
                "action's requires",
            )
        if signature.nonce in self._closed or pin in self._consumed[signature.nonce]:
            self._reject(pin, "token_replayed", "NE1002")
            raise TokenReplayError(
                where=where,
                why="this verdict token was already used",
                how="each c.do() call authorises one command per pin; call c.do() again",
                reason="token_replayed",
            )
        if self.clock() - signature.issued_at_ms > signature.ttl_ms:
            self._reject(pin, "token_expired", "NE1002")
            raise TokenReplayError(
                where=where,
                why=f"the verdict token outlived its TTL of {signature.ttl_ms:g} ms",
                how="act promptly after the verdict, or call c.do() again",
                reason="token_expired",
            )
        self._consumed[signature.nonce].add(pin)
        return None

    def _authorize_lease(self, signature: VerdictToken, channel: str, where: str) -> float:
        """One command per lease, within its time — never renewed, never extended (§3c)."""
        if signature.nonce in self._closed or channel in self._consumed[signature.nonce]:
            self._reject(channel, "lease_used", "NE1002")
            raise TokenReplayError(
                where=where,
                why="this lease already carried a command, or its gate pass is over",
                how="each gate pass leases the channel for one command; renew by calling "
                "c.do() again, which evaluates the gate again",
                reason="lease_used",
            )
        lease_ms = signature.lease_ms(channel) or 0.0
        remaining = lease_ms - (self.clock() - signature.issued_at_ms)
        if remaining <= 0:
            self._reject(channel, "lease_expired", "NE1002")
            raise TokenReplayError(
                where=where,
                why=f"the lease on {channel!r} ran out {lease_ms:g} ms after the verdict",
                how="command promptly after the verdict, or call c.do() again for a new lease",
                reason="lease_expired",
            )
        self._consumed[signature.nonce].add(channel)
        return remaining

    def _reject(self, pin: str, reason: str, code: str) -> None:
        if self.events is not None:
            self.events.emit(
                "actuator_command_rejected", {"pin": pin, "reason": reason, "code": code}
            )
