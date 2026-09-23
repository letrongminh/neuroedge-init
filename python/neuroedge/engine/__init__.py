"""
Action Contract Engine (L3) — the core safety engine.

Declarative half: gate documents, inheritance, canonical form (Sprint 1).
Evaluating half: decision tree (TSK-S2-12) and Gate Engine (TSK-S2-03).
This module is a façade; the implementations live in the submodules.
"""

from .canonical import canonicalize, digest, gate_canonical_json, gate_digest
from .constraints import Constraint, parse_allow_when, parse_constraint
from .decision_tree import TREE_SCHEMA, TreeResult, compile_tree, tree_bytes, validate_tree, walk
from .gate import ActionContractEngine, FactSource, Gate, GateResult
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
from .trace_sink import EventLog, monotonic_ms
from .verdict import DEGRADED_REASONS, Fact, GateVerdict, Reason, Unavailable

__all__ = [
    "DEGRADED_REASONS",
    "EventLog",
    "FactSource",
    "GateResult",
    "Unavailable",
    "monotonic_ms",
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
