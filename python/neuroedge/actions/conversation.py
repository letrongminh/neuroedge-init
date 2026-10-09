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
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from typing import Any

from ..engine.gate import ActionContractEngine, GateResult
from ..engine.verdict import GateVerdict
from ..errors import EnvelopeRefusedError, ToolCallError
from ..hal import digital, ensure_envelope
from ..hal.motion_core import lease_ms_of
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
class _Frame:
    """
    What one call of `c.do()` decides on, fixed when the call begins: the conversation's `facts`
    with the facts of that call laid over them (who asked: `call_source`), and the utterance. A
    call waits — a gate for its adjudicator, an action body — and other calls run meanwhile on the
    same conversation: what it reads after the wait is its own frame, never `self.facts`, which
    those other calls and agent code are free to replace. Nothing a call lays over is ever
    written into `self.facts` either, so no other call, concurrent or later, can see it.
    """

    facts: Mapping[str, Any]
    utterance: str


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
        # What every call starts from. Read once, when a call begins (`_Frame`): a call never
        # writes it, and replacing it does not change a call already running.
        self.facts = dict(facts or {})
        self.utterance = utterance
        self.registry = registry
        self.events = engine.events
        self.ledger = ledger or TokenLedger(engine.clock, events=self.events)
        # From here on the HAL accepts only tokens from this ledger.
        hal.authorize = self.ledger.authorize
        # ... and bounded by the safety envelope of its board (RFC-0007 §3d, TSK-N2-01).
        ensure_envelope(hal, engine.clock)
        self.confirmations = ConfirmationBook(engine.clock, self.events)
        # The `TurnMeter` of the turn a session is timing, or None (TSK-I4-03). It
        # only measures: nothing here reads it to decide.
        self.meter: Any = None
        # Facts a gate is given that are not `facts`: functions of the gate's tree, called just
        # before it is evaluated (the camera of `vision.in`, `sim/vision/feed.py`). Each returns
        # the criteria it speaks for — `None` for one it could not read, so the engine blocks
        # it instead of asking another source. Their names are theirs: they win over `facts`.
        self.fact_sources: list[Callable[[Mapping[str, Any]], Mapping[str, Any]]] = []
        # The `bridge:<id>` / `mcp:<client>` sources whoever loads them has registered (RFC-0017
        # §3b.4). Internal: the loader of bridges and `[mcp.clients]` fill it, a `dispatch()` of
        # any other such source is a programming error.
        self._registered_sources: set[str] = set()

    def register_source(self, source: str) -> None:
        """
        Make a `bridge:<id>` / `mcp:<client>` source one `dispatch()` accepts. An id outside the
        grammar, a built-in name (they need no registration) and an id registered twice are
        refused (NE1004): nobody takes another's name by loading order.
        """
        from .tools import NAMESPACES, SOURCES, valid_source

        if source in SOURCES or not valid_source(source):
            raise ToolCallError(
                where=f"Conversation.register_source({source!r})",
                why=f"{source!r} is not a namespaced source",
                how=f"register `bridge:<id>` or `mcp:<client>`, not a built-in name ({list(SOURCES)})",
            )
        if source in self._registered_sources:
            raise ToolCallError(
                where=f"Conversation.register_source({source!r})",
                why=f"{source!r} is already registered",
                how=f"give each of the {list(NAMESPACES)} sources one id; a second loader must not "
                "share the first one's",
            )
        self._registered_sources.add(source)

    def require_registered(self, source: str) -> None:
        """NE1004 for a `bridge:<id>` / `mcp:<client>` nobody registered; built-in names pass."""
        from .tools import SOURCES

        if source not in SOURCES and source not in self._registered_sources:
            raise ToolCallError(
                where=f"dispatch(source={source!r})",
                why=f"{source!r} is not a registered source of this session",
                how="register it first (the bridge loader, or the `[mcp.clients]` table, does)",
            )

    def stage(self, name: str) -> AbstractContextManager[Any]:
        """Time `name` on the turn's meter, if a session is timing one."""
        return self.meter.stage(name) if self.meter is not None else nullcontext()

    def _frame(self, own: Mapping[str, Any] | None = None) -> _Frame:
        """A call's frame, now: a copy of `facts` with `own` over it (`own` wins)."""
        return _Frame({**self.facts, **(own or {})}, self.utterance)

    async def do(self, target: Any, /, **kwargs: Any) -> ActionResult:
        return await self._do(spec_of(target), kwargs, visited=(), frame=self._frame())

    async def do_with(
        self, facts: Mapping[str, Any], target: Any, /, **kwargs: Any
    ) -> ActionResult:
        """
        `do()` with `facts` of its own in front of the gate, over the conversation's: the
        dispatcher's `call_source`. They belong to this call alone — `self.facts` is neither
        written nor restored — so calls that overlap on one conversation do not see each other's.
        """
        return await self._do(spec_of(target), kwargs, visited=(), frame=self._frame(facts))

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
        # The gate is judged again as the call that raised the question, not as whoever answers.
        source_of_request = taken.context.get("call_source")
        own = {} if source_of_request is None else {"call_source": source_of_request}
        return await self._do(
            spec, dict(taken.arguments), visited=(), confirmed=True, frame=self._frame(own)
        )

    def decline(self, confirm_id: str, source: str) -> PendingConfirmation:
        """A person answered "no": the question closes, nothing runs."""
        return self.confirmations.decline(confirm_id, source)

    def _context(self, key: str, frame: _Frame) -> Mapping[str, Any]:
        """The call's facts, plus what each fact source reads for the gate `key` (if it exists)."""
        tree = self.engine.tree(key) if self.fact_sources else None
        context = dict(frame.facts)
        if tree is not None:
            for source in self.fact_sources:
                context.update(source(tree))
        # Last, so nothing above can set it: `call_channel` is the family of this call's own
        # `call_source` (RFC-0017 §3d). No source, or not one, means no channel — the gate
        # reads it as unavailable and blocks.
        from .tools import CALL_CHANNEL_FACT, CALL_SOURCE_FACT, source_channel

        context.pop(CALL_CHANNEL_FACT, None)
        channel = source_channel(frame.facts.get(CALL_SOURCE_FACT))
        if channel is not None:
            context[CALL_CHANNEL_FACT] = channel
        return context

    async def _do(
        self,
        spec: ActionSpec,
        kwargs: dict[str, Any],
        visited: tuple[str, ...],
        confirmed: bool = False,
        *,
        frame: _Frame,
    ) -> ActionResult:
        state = {"utterance": frame.utterance, "action": spec.name, "arguments": dict(kwargs)}
        # Which action asked for which gate: a replay (TSK-S3-02) re-runs exactly this.
        self.events.emit(
            "action_requested",
            {"action": spec.name, "gate": spec.gate, "arguments": _json_safe(kwargs)},
        )
        with self.stage("gate"):
            result = await self.engine.evaluate(
                spec.gate,
                self._context(spec.gate, frame),
                state=state,
                arguments=_effective(spec, kwargs),
                confirmed=confirmed,
            )
        if result.verdict is GateVerdict.BLOCK:
            fallback = None
            if result.on_block_action == "degrade" and result.fallback_action:
                fallback = await self._fallback(
                    result.fallback_action, visited + (spec.name,), frame
                )
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
                        "utterance": frame.utterance,
                        "call_source": frame.facts.get("call_source"),
                    },
                )
            # RFC-0011 §3d: a BLOCK of a command for a motion channel sends the channel to its
            # safe state at once, and the lease it held is not renewed. Toward the safe state:
            # nothing waits for it, nothing refuses it.
            safe = getattr(self.hal, "motion_safe", None)
            if safe is not None:
                for channel in sorted(spec.channels):
                    safe(channel, "block", called_from=f"c.do({spec.name})")
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
            # RFC-0011 §3c: a lease per motion channel, as long as the board says (not TTL_FACTOR).
            channels={c: lease_ms_of(getattr(self.hal, "board", None), c) for c in spec.channels},
        )
        try:
            with self.stage("action"), running(spec), digital.grant(self.hal, token, spec.name):
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

    async def _fallback(
        self, name: str, visited: tuple[str, ...], frame: _Frame
    ) -> ActionResult | None:
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
        try:
            # The fallback is part of the call that was blocked: it is judged as that call.
            return await self._do(self.registry[name], {}, visited, frame=frame)
        except EnvelopeRefusedError as refusal:
            # The verdict already stands as a BLOCK and the fallback is the best effort that
            # follows it: a pin the envelope would not move (already on, resting) stays as it
            # is, and the refusal is in the trace (`envelope_refused`) — it is not the caller's
            # error (RFC-0007 §3d).
            self.events.emit(
                "fallback_skipped",
                {"action": name, "reason": f"the envelope refused it ({refusal.reason})"},
            )
            return None

    async def say(self, text: str) -> None:
        self.hal.audio_out(text)
