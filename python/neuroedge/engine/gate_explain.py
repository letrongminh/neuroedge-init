"""
Provenance of a resolved gate — the data behind `neuroedge gate explain` (TSK-S3-18).

A reviewer who does not read YAML (J6) needs three answers the flattened
`ResolvedGate` no longer carries: which document introduced each criterion,
which clauses a child tightened relative to its parent, and whether the budget
and `on_block` were inherited or changed. They are recovered by resolving every
prefix of the `extends` chain and comparing consecutive levels. Nothing here
decides anything: the verdict semantics stay in the resolver and the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .gate_resolver import (
    GateRegistry,
    ResolvedGate,
    _load_chain,
    load_gate_document,
    resolve_gate_document,
)


@dataclass(frozen=True)
class CriterionOrigin:
    name: str
    kind: str
    instructions: str
    introduced_by: str
    inherited: bool
    detail: str = ""


@dataclass(frozen=True)
class ClauseChange:
    criterion: str
    admits: str
    status: str  # "inherited" | "tightened" | "new"
    parent_admits: str | None = None


@dataclass(frozen=True)
class GateExplanation:
    gate: ResolvedGate
    parent: ResolvedGate | None
    extends: str | None
    criteria: list[CriterionOrigin]
    clauses: list[ClauseChange]

    @property
    def label(self) -> str:
        return f"{self.gate.name}@{self.gate.version}"

    @property
    def p95(self) -> Any:
        return self.gate.budget.get("p95_latency_ms")

    @property
    def parent_p95(self) -> Any:
        return None if self.parent is None else self.parent.budget.get("p95_latency_ms")

    @property
    def on_block_changed(self) -> bool:
        """The behaviour or its recipient changed; a reworded message does not count."""
        keys = ("action", "to", "fallback_action")
        return self.parent is not None and any(
            self.parent.on_block.get(key) != self.gate.on_block.get(key) for key in keys
        )


def _detail(definition: dict[str, Any]) -> str:
    if definition.get("type") == "level":
        return " / ".join(definition.get("levels", []))
    if definition.get("type") == "choice":
        return " / ".join(definition.get("options", []))
    return ""


def explain(levels: list[ResolvedGate], extends: str | None) -> GateExplanation:
    """Explain the last of `levels`, the chain resolved one prefix at a time, root first."""
    gate = levels[-1]
    parent = levels[-2] if len(levels) > 1 else None

    criteria = []
    for name, definition in gate.evaluate.items():
        origin = next(level for level in levels if name in level.evaluate)
        criteria.append(
            CriterionOrigin(
                name=name,
                kind=definition.get("type", "?"),
                instructions=definition.get("instructions", ""),
                introduced_by=f"{origin.name}@{origin.version}",
                inherited=origin is not gate,
                detail=_detail(definition),
            )
        )

    clauses = []
    for name in sorted(gate.constraints):
        constraint = gate.constraints[name]
        before = None if parent is None else parent.constraints.get(name)
        if before is None:
            status = "new"
        elif before.describe() == constraint.describe():
            status = "inherited"  # restating the parent's clause changes nothing
        else:
            status = "tightened"  # the resolver admits no other change (principle 2)
        clauses.append(
            ClauseChange(
                criterion=name,
                admits=constraint.describe(),
                status=status,
                parent_admits=None if before is None else before.describe(),
            )
        )
    return GateExplanation(gate, parent, extends, criteria, clauses)


def explain_gate_document(
    document: dict[str, Any], source: str, registry: GateRegistry | None = None
) -> GateExplanation:
    registry = registry or GateRegistry()
    resolve_gate_document(document, source=source, registry=registry)  # every error surfaces here
    chain = _load_chain(document, source, registry)
    levels = [resolve_gate_document(doc, source=src, registry=registry) for doc, src in chain]
    return explain(levels, document.get("extends"))


def explain_gate_file(path: str | Path, registry: GateRegistry | None = None) -> GateExplanation:
    path = Path(path)
    return explain_gate_document(load_gate_document(path), str(path), registry)


def explain_gate_uri(uri: str, registry: GateRegistry | None = None) -> GateExplanation:
    registry = registry or GateRegistry()
    document, path = registry.load(uri)
    return explain_gate_document(document, str(path), registry)
