"""
Single-use verdict tokens (TSK-S2-05, FR-ACE-02; design doc, closed question 12).

An ALLOW becomes a token, and the HAL moves a pin only on a token this ledger
issued, for that pin, once, within its TTL:

* **TTL = p95 × 3.** A TTL of exactly p95 would expire ~5% of *valid* tokens by
  the definition of a percentile.
* **One way:** issued → consumed per pin, and closed when `c.do()` returns.
  Any later use is `token_replayed`.
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
from collections.abc import Callable
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

    def __repr__(self) -> str:  # never print the nonce
        return f"<VerdictToken {self.action} via {self.gate} pins={sorted(self.pins)}>"


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
        )
        self._issued[token.nonce] = token
        self._consumed[token.nonce] = set()
        return token

    def close(self, token: VerdictToken) -> None:
        self._closed.add(token.nonce)

    # -- the HAL authorizer --------------------------------------------------
    def authorize(self, signature: Any, pin: str, called_from: str) -> None:
        where = f"{called_from} -> digital.out {pin!r}"
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
        if pin not in signature.pins:
            self._reject(pin, "pin_not_granted", "NE1001")
            raise ActionContractViolation(
                where=where,
                why=f"the token grants {sorted(signature.pins)}, not {pin!r}",
                how=f"declare 'digital.out:{pin}' in the action's requires",
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

    def _reject(self, pin: str, reason: str, code: str) -> None:
        if self.events is not None:
            self.events.emit(
                "actuator_command_rejected", {"pin": pin, "reason": reason, "code": code}
            )
