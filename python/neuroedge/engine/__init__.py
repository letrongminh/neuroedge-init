"""
Action Contract Engine (L3) — the core safety engine.

Sprint 1 freezes the declarative half: gate documents, their inheritance
semantics, and the canonical form that gets hashed and signed. The evaluating
half (CEL compilation, circuit breaker, `@action` enforcement) lands in
Sprint 2.
"""

from dataclasses import dataclass
from typing import Any

from .canonical import canonicalize, digest, gate_canonical_json, gate_digest
from .constraints import Constraint, parse_allow_when, parse_constraint
from .decision_tree import TREE_SCHEMA, TreeResult, compile_tree, tree_bytes, validate_tree, walk
from .gate_resolver import (
    MAX_INHERITANCE_LEVELS,
    GateRegistry,
    ResolvedGate,
    load_gate_document,
    resolve_gate_document,
    resolve_gate_file,
    resolve_gate_uri,
    validate_gate_document,
)
from .verdict import DEGRADED_REASONS, Fact, GateVerdict, Reason

__all__ = [
    "DEGRADED_REASONS",
    "MAX_INHERITANCE_LEVELS",
    "TREE_SCHEMA",
    "Fact",
    "Reason",
    "TreeResult",
    "compile_tree",
    "tree_bytes",
    "validate_tree",
    "walk",
    "ActionContractEngine",
    "Constraint",
    "Gate",
    "GateRegistry",
    "GateVerdict",
    "ResolvedGate",
    "canonicalize",
    "digest",
    "gate_canonical_json",
    "gate_digest",
    "load_gate_document",
    "parse_allow_when",
    "parse_constraint",
    "resolve_gate_document",
    "resolve_gate_file",
    "resolve_gate_uri",
    "validate_gate_document",
]


@dataclass
class Gate:
    name: str
    version: str
    verdict: GateVerdict = GateVerdict.BLOCK
    blocked_by: str | None = None
    reason: str | None = None
    escalated_to: str | None = None


class ActionContractEngine:
    """
    Enforces that every physical actuator command passes an authorised gate.

    Fail-closed is the default in every direction: an unregistered gate, an
    unreachable adjudicator or an exceeded budget all deny the action. Full
    evaluation arrives with TSK-S2-03; what exists here is the safe default it
    must preserve.
    """

    def __init__(self, fail_closed: bool = True):
        self.fail_closed = fail_closed
        self.gates: dict[str, Gate] = {}

    def evaluate(self, gate_name: str, context: dict[str, Any]) -> Gate:
        if gate_name not in self.gates:
            return Gate(
                name=gate_name,
                version="unknown",
                verdict=GateVerdict.BLOCK,
                blocked_by=gate_name,
                reason="gate_not_found",
            )
        return self.gates[gate_name]
