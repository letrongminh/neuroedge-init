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
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from typing import Any

from ..engine.gate import ActionContractEngine, GateResult
from ..engine.verdict import GateVerdict
from ..hal import digital
from .confirmation import ConfirmationBook, ConfirmationRefused, PendingConfirmation
from .spec import REGISTRY, ActionSpec, running, spec_of
from .token import TokenLedger

MAX_FALLBACK_DEPTH = 3


def _json_safe(values: dict[str, Any]) -> dict[str, Any]:
    """Arguments as the trace can hold them: JSON scalars kept, anything else by repr."""
    scalar = (str, int, float, bool, type(None))
    return {k: v if isinstance(v, scalar) else repr(v) for k, v in values.items()}


def _effective(spec: ActionSpec, kwargs: dict[str, Any]) -> dict[str, Any]:
    """
    The arguments the body will actually run with — defaults applied — which is
    what a gate's `arguments` limits must see (RFC-0005): a call that omits
    `duration_s` still pulses for the default.
    """
    try:
        bound = inspect.signature(spec.fn).bind(**kwargs)
    except TypeError:
        return dict(kwargs)  # the body call raises; the gate sees what was given
    bound.apply_defaults()
    return dict(bound.arguments)


@dataclass(frozen=True)
class ActionResult:
    action: str
    verdict: GateVerdict
    gate: GateResult | None = None
    value: Any = None
    fallback: ActionResult | None = None
    # RFC-0006: the question a person may answer, when the gate asked one.
    confirmation: PendingConfirmation | None = None

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
        self.confirmations = ConfirmationBook(engine.clock, self.events)
        # The `TurnMeter` of the turn a session is timing, or None (TSK-I4-03). It
        # only measures: nothing here reads it to decide.
        self.meter: Any = None

    def _stage(self, name: str) -> AbstractContextManager[Any]:
        return self.meter.stage(name) if self.meter is not None else nullcontext()

    async def do(self, target: Any, /, **kwargs: Any) -> ActionResult:
        return await self._do(spec_of(target), kwargs, visited=())

    async def confirm(self, confirm_id: str, source: str) -> ActionResult:
        """
        A person answered "yes" on the device (`source` in `HUMAN_SOURCES`):
        evaluate the same gate again with its `confirms` criteria stood in for,
        and run the action only if it now allows. Raises `ConfirmationRefused`
        for any other source, an unknown / used / expired question, or a gate
        that changed since it asked.
        """
        pending = self.confirmations.get(confirm_id)
        tree = self.engine.tree(pending.gate_key) if pending is not None else None
        taken = self.confirmations.take(
            confirm_id, source, None if tree is None else tree["gate_digest"]
        )
        spec = self.registry.get(taken.action)
        if spec is None:
            raise ConfirmationRefused(f"no @action {taken.action!r} to run")
        facts = dict(self.facts)
        source_of_request = taken.context.get("call_source")
        if source_of_request is not None:
            self.facts = {**facts, "call_source": source_of_request}
        try:
            return await self._do(spec, dict(taken.arguments), visited=(), confirmed=True)
        finally:
            self.facts = facts

    def decline(self, confirm_id: str, source: str) -> PendingConfirmation:
        """A person answered "no": the question closes, nothing runs."""
        return self.confirmations.decline(confirm_id, source)

    async def _do(
        self,
        spec: ActionSpec,
        kwargs: dict[str, Any],
        visited: tuple[str, ...],
        confirmed: bool = False,
    ) -> ActionResult:
        state = {"utterance": self.utterance, "action": spec.name, "arguments": dict(kwargs)}
        # Which action asked for which gate: a replay (TSK-S3-02) re-runs exactly this.
        self.events.emit(
            "action_requested",
            {"action": spec.name, "gate": spec.gate, "arguments": _json_safe(kwargs)},
        )
        with self._stage("gate"):
            result = await self.engine.evaluate(
                spec.gate,
                self.facts,
                state=state,
                arguments=_effective(spec, kwargs),
                confirmed=confirmed,
            )
        if result.verdict is GateVerdict.BLOCK:
            fallback = None
            if result.on_block_action == "degrade" and result.fallback_action:
                fallback = await self._fallback(result.fallback_action, visited + (spec.name,))
            pending = None
            if result.on_block_action == "ask" and result.confirms and not confirmed:
                # RFC-0006: the gate asked a question a person may answer. Nothing
                # runs now; `confirm()` evaluates the gate again if they say yes.
                tree = self.engine.tree(spec.gate)
                pending = self.confirmations.open(
                    action=spec.name,
                    arguments=_json_safe(kwargs),
                    gate=result.gate,
                    gate_key=spec.gate,
                    gate_digest=result.gate_digest,
                    message=result.message or "",
                    confirms=result.confirms,
                    p95_ms=tree["budget"]["p95_latency_ms"],
                    # The re-evaluation must see who asked originally, not who answered.
                    context={
                        "utterance": self.utterance,
                        "call_source": self.facts.get("call_source"),
                    },
                )
            return ActionResult(
                spec.name, GateVerdict.BLOCK, result, fallback=fallback, confirmation=pending
            )

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
            with self._stage("action"), running(spec), digital.grant(self.hal, token, spec.name):
                value = spec.fn(**kwargs)
                if inspect.isawaitable(value):
                    value = await value
        except BaseException:
            # A command the action scheduled before it raised never runs: the verdict
            # authorised the whole action, not the half that got through.
            cancel = getattr(self.hal, "cancel_scheduled", None)
            if cancel is not None:
                cancel(token)
            raise
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
