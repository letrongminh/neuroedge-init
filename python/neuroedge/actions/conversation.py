"""
`Conversation` — `c.do()` for physical actions, `c.say()` for speech (FR-ACE-07).

`c.do()` is the single gate in front of the physical world:

1. evaluate the action's gate;
2. BLOCK — issue nothing, run nothing. For `degrade`, run the gate's
   `fallback_action` through **its own** `c.do()` and gate (Q-17);
3. ALLOW — issue a single-use verdict token, run the action body with the token
   granted to `digital.out`, then close the token.

`c.say()` never evaluates a gate and never issues a token: speech can be
corrected, a door pulse cannot.
"""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..engine.gate import ActionContractEngine, GateResult
from ..engine.verdict import GateVerdict
from ..hal import digital
from .spec import REGISTRY, ActionSpec, running, spec_of
from .token import TokenLedger

MAX_FALLBACK_DEPTH = 3


@dataclass(frozen=True)
class ActionResult:
    action: str
    verdict: GateVerdict
    gate: GateResult | None = None
    value: Any = None
    fallback: ActionResult | None = None

    @property
    def blocked(self) -> bool:
        return self.verdict is GateVerdict.BLOCK


class Conversation:
    def __init__(
        self,
        *,
        engine: ActionContractEngine,
        hal: Any,
        fast: Any = None,
        slow: Any = None,
        facts: Mapping[str, Any] | None = None,
        utterance: str = "",
        registry: Mapping[str, ActionSpec] = REGISTRY,
        ledger: TokenLedger | None = None,
    ) -> None:
        self.engine = engine
        self.hal = hal
        self.fast = fast
        self.slow = slow
        self.facts = dict(facts or {})
        self.utterance = utterance
        self.registry = registry
        self.events = engine.events
        self.ledger = ledger or TokenLedger(engine.clock, events=self.events)
        # From here on the HAL accepts only tokens from this ledger.
        hal.authorize = self.ledger.authorize

    async def do(self, target: Any, /, **kwargs: Any) -> ActionResult:
        return await self._do(spec_of(target), kwargs, visited=())

    async def _do(
        self, spec: ActionSpec, kwargs: dict[str, Any], visited: tuple[str, ...]
    ) -> ActionResult:
        state = {"utterance": self.utterance, "action": spec.name, "arguments": dict(kwargs)}
        result = await self.engine.evaluate(spec.gate, self.facts, state=state)
        if result.verdict is GateVerdict.BLOCK:
            fallback = None
            if result.on_block_action == "degrade" and result.fallback_action:
                fallback = await self._fallback(result.fallback_action, visited + (spec.name,))
            return ActionResult(spec.name, GateVerdict.BLOCK, result, fallback=fallback)

        tree = self.engine.tree(spec.gate)
        token = self.ledger.issue(
            gate=result.gate,
            gate_digest=result.gate_digest,
            action=spec.name,
            pins=spec.pins,
            session_id=self.events.session_id,
            p95_ms=tree["budget"]["p95_latency_ms"],
        )
        try:
            with running(spec), digital.grant(self.hal, token, spec.name):
                value = spec.fn(**kwargs)
                if inspect.isawaitable(value):
                    value = await value
        finally:
            self.ledger.close(token)
        return ActionResult(spec.name, GateVerdict.ALLOW, result, value=value)

    async def _fallback(self, name: str, visited: tuple[str, ...]) -> ActionResult | None:
        problem = None
        if name not in self.registry:
            problem = "not a registered @action"
        elif name in visited:
            problem = "fallback cycle"
        elif len(visited) >= MAX_FALLBACK_DEPTH:
            problem = f"fallback depth exceeds {MAX_FALLBACK_DEPTH}"
        else:
            try:
                inspect.signature(self.registry[name].fn).bind()
            except TypeError:
                problem = "fallback requires arguments"
        if problem is not None:
            self.events.emit("fallback_skipped", {"action": name, "reason": problem})
            return None
        return await self._do(self.registry[name], {}, visited)

    async def say(self, text: str) -> None:
        self.hal.audio_out(text)
