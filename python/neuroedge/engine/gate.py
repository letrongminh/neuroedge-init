"""
Gate Engine — evaluates a resolved gate against facts and returns a verdict.

The engine never actuates anything. It answers one question — may this action
run? — and records the answer in the trace. `c.do()` (TSK-S2-05) is the only
caller that turns an ALLOW into a verdict token and a pin change.

Evaluation, in order:

1. Gather a `Fact` for every criterion: the caller's context first, then the
   fact source (SystemOne, TSK-S2-08), within the gate's latency budget.
   Before that, the call's arguments meet the gate's `arguments` limits
   (RFC-0005): deterministic, no fact source, no budget. Out of range ⇒ BLOCK
   `argument_out_of_range`, dispatched through `on_block` like any refusal.
2. Walk the compiled decision tree (TSK-S2-12).
3. **Degraded** — the source was unreachable or the budget was exceeded:
   apply `budget.fail`. `closed` blocks with action `deny` and runs no hooks,
   exactly as `fixtures/traces/network_offline.json` records.
4. **Condition not met** — dispatch `on_block` (Q-17). Every behaviour blocks the
   physical action; `escalate` / `ask` also call a hook, `degrade` names a
   `fallback_action` that `c.do()` must run through that action's own gate.

The budget window starts when fact gathering starts and includes every call to
the fact source (design doc, closed question 11): the source is the part that
can be slow or unreachable. Perception (audio → intent) is outside it.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from . import arguments as argument_limits
from .decision_tree import TreeResult, compile_tree, known_failure, walk
from .gate_resolver import GateRegistry, ResolvedGate, resolve_gate_file, resolve_gate_uri
from .trace_sink import Clock, EventLog, monotonic_ms
from .verdict import DEGRADED_REASONS, Fact, GateVerdict, Reason, Unavailable


class FactSource(Protocol):
    """Anything that can adjudicate one criterion — SystemOne in practice."""

    async def adjudicate(
        self,
        criterion: str,
        definition: Mapping[str, Any],
        state: Mapping[str, Any] | None,
        deadline_ms: float,
    ) -> Fact | Unavailable:
        """`deadline_ms` is the budget still left, in ms; the engine enforces it."""
        ...


Hook = Callable[["GateResult"], None]


def _noop(_: GateResult) -> None:
    return None


@dataclass(frozen=True)
class GateResult:
    """One verdict, in the shape the trace records it."""

    gate: str
    verdict: GateVerdict
    gate_digest: str = ""
    reason: Reason | None = None
    failed_criterion: str | None = None
    blocked_by: str | None = None
    on_block_action: str | None = None
    escalated_to: str | None = None
    message: str | None = None
    fallback_action: str | None = None
    fail_mode: str | None = None
    evaluations: dict[str, bool | str] = field(default_factory=dict)
    elapsed_ms: float = 0.0

    @property
    def allowed(self) -> bool:
        return self.verdict is GateVerdict.ALLOW

    @property
    def degraded(self) -> bool:
        return self.reason in DEGRADED_REASONS

    def to_event_data(self) -> dict[str, Any]:
        """
        `gate_evaluation_result` data. Reproduces the canonical traces' keys and
        adds `reason` / `failed_criterion` on a condition block.
        """
        data: dict[str, Any] = {"verdict": str(self.verdict)}
        if self.fail_mode is not None:
            data["fail_mode"] = self.fail_mode
        if self.reason is not None:
            data["reason"] = str(self.reason)
        if not self.degraded and self.reason is not Reason.GATE_NOT_FOUND:
            data["evaluations"] = dict(self.evaluations)
        if self.verdict is GateVerdict.BLOCK:
            data["blocked_by"] = self.blocked_by
            data["action"] = self.on_block_action
        optional = {
            "failed_criterion": self.failed_criterion,
            "escalated_to": self.escalated_to,
            "message": self.message,
            "fallback_action": self.fallback_action,
        }
        data.update({key: value for key, value in optional.items() if value is not None})
        return data


# Gate alias kept so `neuroedge.Gate` from Sprint 1 still names the verdict type.
Gate = GateResult


@dataclass(frozen=True)
class _Registered:
    gate: ResolvedGate
    tree: dict[str, Any]

    @property
    def label(self) -> str:
        return self.tree["gate"]


def _as_fact(value: Any) -> Fact:
    return value if isinstance(value, Fact) else Fact(value)


class ActionContractEngine:
    """
    Holds compiled gates and evaluates them.

    Gates are resolved and compiled once, at registration; `evaluate()` does no
    file I/O (CEO-S7-1). There is no fail-open switch on the engine: a gate is
    fail-open only if its own resolved document says `fail: open`.
    """

    def __init__(
        self,
        gates: Mapping[str, ResolvedGate] | None = None,
        *,
        facts_source: FactSource | None = None,
        clock: Clock = monotonic_ms,
        events: EventLog | None = None,
        on_escalate: Hook = _noop,
        on_ask: Hook = _noop,
    ) -> None:
        self.facts_source = facts_source
        self.clock = clock
        self.events = events if events is not None else EventLog(clock)
        self.hooks: dict[str, Hook] = {"escalate": on_escalate, "ask": on_ask}
        self._gates: dict[str, _Registered] = {}
        for key, gate in (gates or {}).items():
            self.register(key, gate)

    # -- registration --------------------------------------------------------
    def register(self, key: str, gate: ResolvedGate) -> None:
        self._gates[key] = _Registered(gate, compile_tree(gate))

    def register_gate(
        self, key: str, ref: str | Path, registry: GateRegistry | None = None
    ) -> None:
        """Register a gate from a `neuroedge://` URI or a file path."""
        if isinstance(ref, str) and ref.startswith("neuroedge://"):
            gate = resolve_gate_uri(ref, registry=registry)
        else:
            gate = resolve_gate_file(ref, registry=registry)
        self.register(key, gate)

    def gate(self, key: str) -> ResolvedGate | None:
        registered = self._gates.get(key)
        return None if registered is None else registered.gate

    def tree(self, key: str) -> dict[str, Any] | None:
        registered = self._gates.get(key)
        return None if registered is None else registered.tree

    # -- evaluation ------------------------------------------------------------
    async def evaluate(
        self,
        key: str,
        context: Mapping[str, Any] | None = None,
        *,
        state: Mapping[str, Any] | None = None,
        arguments: Mapping[str, Any] | None = None,
    ) -> GateResult:
        """
        `arguments` are the action's effective arguments — defaults applied — as
        `c.do()` will call it; a gate with `arguments` limits checks them first.
        """
        registered = self._gates.get(key)
        if registered is None:
            result = GateResult(
                gate=key,
                verdict=GateVerdict.BLOCK,
                reason=Reason.GATE_NOT_FOUND,
                blocked_by=key,
                on_block_action="deny",
            )
            self.events.emit("gate_evaluation_result", result.to_event_data())
            return result

        tree = registered.tree
        self.events.emit(
            "gate_evaluation_begin", {"gate": registered.label, "gate_digest": tree["gate_digest"]}
        )
        t0 = self.clock()
        limits = tree.get("arguments")
        if limits:
            violation = argument_limits.check(limits, dict(arguments or {}))
            if violation is not None:
                name, why = violation
                self.events.emit("argument_out_of_range", {"argument": name, "why": why})
                refused = TreeResult(GateVerdict.BLOCK, Reason.ARGUMENT_OUT_OF_RANGE, name, {})
                result = self._on_block(registered, refused, self.clock() - t0)
                self.events.emit("gate_evaluation_result", result.to_event_data())
                self._call_hook(result)
                return result
        facts, degraded = await self._gather(registered, dict(context or {}), state, t0)
        if facts:
            # The inputs of the verdict, with confidence and source: what a replay
            # feeds back in (TSK-S3-02). `evaluations` in the result keeps only values.
            self.events.emit(
                "gate_facts",
                {
                    criterion: {
                        "value": fact.value,
                        "confidence": fact.confidence,
                        "source": fact.source,
                    }
                    for criterion, fact in facts.items()
                },
            )
        walked = walk(tree, facts)
        elapsed = self.clock() - t0
        if degraded is None and elapsed > tree["budget"]["p95_latency_ms"]:
            degraded = Reason.BUDGET_EXCEEDED

        if degraded is not None:
            result = self._degraded(registered, degraded, walked, facts, elapsed)
        elif walked.verdict is GateVerdict.ALLOW:
            result = GateResult(
                gate=registered.label,
                verdict=GateVerdict.ALLOW,
                gate_digest=tree["gate_digest"],
                evaluations=walked.evaluations,
                elapsed_ms=elapsed,
            )
        else:
            result = self._on_block(registered, walked, elapsed)

        self.events.emit("gate_evaluation_result", result.to_event_data())
        if result.verdict is GateVerdict.BLOCK and not result.degraded:
            self._call_hook(result)
        return result

    async def _gather(
        self,
        registered: _Registered,
        context: dict[str, Any],
        state: Mapping[str, Any] | None,
        t0: float,
    ) -> tuple[dict[str, Fact], Reason | None]:
        """
        Facts for every criterion, and the degraded reason if the source failed.

        Once the source degrades it is not asked again, but facts already in the
        context are still collected: under `fail: open` a known "no" must still
        block. A source that raises or overruns the budget is a degraded verdict,
        never an exception out of `evaluate()`.
        """
        tree = registered.tree
        p95 = tree["budget"]["p95_latency_ms"]
        facts: dict[str, Fact] = {}
        degraded: Reason | None = None
        for criterion in tree["criteria_order"]:
            if criterion in context:
                facts[criterion] = _as_fact(context[criterion])
                continue
            if self.facts_source is None or degraded is not None:
                continue  # walk() reports criterion_unavailable
            remaining = t0 + p95 - self.clock()
            try:
                answer = await asyncio.wait_for(
                    self.facts_source.adjudicate(
                        criterion,
                        registered.gate.evaluate[criterion],
                        state,
                        deadline_ms=remaining,
                    ),
                    timeout=max(remaining, 0) / 1000.0,
                )
            except TimeoutError:
                degraded = Reason.BUDGET_EXCEEDED
                continue
            except Exception as exc:  # an adjudicator failure is a verdict, not a crash
                self.events.emit(
                    "fact_source_error",
                    {"criterion": criterion, "error": f"{type(exc).__name__}: {exc}"},
                )
                degraded = Reason.GATE_UNREACHABLE
                continue
            if self.clock() - t0 > p95:
                degraded = Reason.BUDGET_EXCEEDED
                continue
            if isinstance(answer, Unavailable):
                reason = answer.as_reason()
                if reason in DEGRADED_REASONS:
                    degraded = reason
                continue  # criterion_unavailable, reported by walk()
            facts[criterion] = answer
        return facts, degraded

    def _degraded(
        self,
        registered: _Registered,
        reason: Reason,
        walked,
        facts: Mapping[str, Fact],
        elapsed: float,
    ) -> GateResult:
        tree = registered.tree
        if tree["budget"]["fail"] == "open":
            # Only a gate that itself declares `fail: open` gets here (principle 4),
            # and open excuses only what could not be decided.
            failure = known_failure(tree, facts)
            if failure is not None:
                known = TreeResult(GateVerdict.BLOCK, failure[0], failure[1], walked.evaluations)
                return self._on_block(registered, known, elapsed)
            return GateResult(
                gate=registered.label,
                verdict=GateVerdict.ALLOW,
                gate_digest=tree["gate_digest"],
                reason=reason,
                fail_mode="open",
                evaluations=walked.evaluations,
                elapsed_ms=elapsed,
            )
        return GateResult(
            gate=registered.label,
            verdict=GateVerdict.BLOCK,
            gate_digest=tree["gate_digest"],
            reason=reason,
            blocked_by=registered.label,
            on_block_action="deny",
            fail_mode="closed",
            elapsed_ms=elapsed,
        )

    def _on_block(self, registered: _Registered, walked, elapsed: float) -> GateResult:
        on_block = registered.gate.on_block
        action = on_block["action"]
        return GateResult(
            gate=registered.label,
            verdict=GateVerdict.BLOCK,
            gate_digest=registered.tree["gate_digest"],
            reason=walked.reason,
            failed_criterion=walked.failed_criterion,
            blocked_by=registered.label,
            on_block_action=action,
            escalated_to=on_block.get("to") if action == "escalate" else None,
            message=on_block.get("message") if action in ("escalate", "ask") else None,
            fallback_action=on_block.get("fallback_action") if action == "degrade" else None,
            evaluations=walked.evaluations,
            elapsed_ms=elapsed,
        )

    def _call_hook(self, result: GateResult) -> None:
        hook = self.hooks.get(result.on_block_action or "")
        if hook is None:
            return
        try:
            hook(result)
        except Exception as exc:  # a hook can never change a verdict
            self.events.emit(
                "on_block_hook_error",
                {"action": result.on_block_action, "error": f"{type(exc).__name__}: {exc}"},
            )
