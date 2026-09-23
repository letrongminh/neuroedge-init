"""
Host-side decision tree: the one form of a gate that both walkers execute.

Q-9 option A puts no CEL VM on the microcontroller: the host compiles each
resolved gate into a flat tree and the firmware only walks it. This module is
the compiler and the Python walker; the C walker in Khối 1b must reproduce
`walk()` exactly — same verdict **and** same reason — which the truth tables in
`fixtures/decision_trees/` pin down (ENG-T1).

Two properties carry the weight:

* **`criteria_order` is root-first**, taken from the insertion order of
  `ResolvedGate.constraints`. The first failing criterion names the reason, so a
  lexicographic order would let a rename change what a trace says.
* **The tree carries `gate_digest`**, so a tree can always be traced back to
  the exact signed policy it was compiled from (ENG-T2).

The format is internal and not frozen; RFC-0003 freezes it before the first C
walker exists (TODOS.md #15).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..errors import GateSchemaError
from .canonical import canonicalize, gate_digest
from .constraints import parse_constraint
from .gate_resolver import ResolvedGate
from .verdict import Fact, GateVerdict, Reason

TREE_SCHEMA = "neuroedge.decision_tree/v1"
_SCHEMA_FILE = Path(__file__).with_name("decision_tree.v1.json")


def _domain(definition: Mapping[str, Any]) -> list[str]:
    kind = definition["type"]
    if kind == "bool":
        return ["false", "true"]
    if kind == "level":
        return list(definition["levels"])
    return sorted(definition["options"])


def compile_tree(gate: ResolvedGate) -> dict[str, Any]:
    """
    Compile a resolved gate into its decision tree.

    Compiled from the `ResolvedGate`, not from the signed artifact: canonical
    JSON sorts keys, so the artifact no longer carries the root-first order. The
    artifact is still re-parsed as a cross-check, so the tree can never describe
    a policy other than the one the digest covers.
    """
    artifact_allow_when = gate.to_artifact()["allow_when"]
    nodes = []
    for criterion, constraint in gate.constraints.items():
        definition = gate.evaluate[criterion]
        reparsed = parse_constraint(criterion, artifact_allow_when[criterion], definition)
        if reparsed != constraint:
            raise GateSchemaError(
                where=f"{gate.name}@{gate.version} -> allow_when.{criterion}",
                why="the resolved constraint differs from the one in the signed artifact",
                how="re-resolve the gate; this indicates a resolver defect, not an authoring error",
            )
        nodes.append(
            {
                "criterion": criterion,
                "kind": constraint.kind,
                "domain": _domain(definition),
                "admitted": sorted(constraint.admitted),
                "confidence_floor": constraint.confidence_floor,
            }
        )

    return {
        "schema": TREE_SCHEMA,
        "gate": f"{gate.name}@{gate.version}",
        "gate_digest": gate_digest(gate),
        "criteria_order": list(gate.constraints),
        "nodes": nodes,
        "on_block": dict(gate.on_block),
        "budget": dict(gate.budget),
    }


def tree_bytes(tree: Mapping[str, Any]) -> bytes:
    """RFC 8785 bytes of a tree — identical across builds for the same gate."""
    return canonicalize(tree)


@lru_cache(maxsize=1)
def _tree_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_FILE.read_text(encoding="utf-8"))


def validate_tree(tree: Mapping[str, Any], label: str = "<tree>") -> None:
    """Validate a tree against the internal decision_tree.v1.json."""
    import jsonschema

    validator = jsonschema.Draft202012Validator(_tree_schema())
    errors = sorted(validator.iter_errors(tree), key=lambda e: list(e.absolute_path))
    if errors:
        first = errors[0]
        location = ".".join(str(p) for p in first.absolute_path) or "<root>"
        raise GateSchemaError(
            where=f"{label} -> {location}",
            why=first.message,
            how="recompile the tree with neuroedge build; trees are generated, never hand-edited",
        )
    if [n["criterion"] for n in tree["nodes"]] != list(tree["criteria_order"]):
        raise GateSchemaError(
            where=f"{label} -> criteria_order",
            why="criteria_order does not match the order of nodes",
            how="recompile the tree with neuroedge build",
        )


@dataclass(frozen=True)
class TreeResult:
    """Outcome of walking a tree over a set of facts."""

    verdict: GateVerdict
    reason: Reason | None = None
    failed_criterion: str | None = None
    evaluations: dict[str, bool | str] = field(default_factory=dict)


def _valid_confidence(value: Any) -> bool:
    """A probability: a real number (not a bool) in [0, 1]. NaN fails the range test."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0.0 <= value <= 1.0


def _classify(
    node: Mapping[str, Any], fact: Fact | None
) -> tuple[Reason | None, bool | str | None]:
    """Return (reason or None when satisfied, the JSON-native value for the trace)."""
    if fact is None or fact.value is None:
        return Reason.CRITERION_UNAVAILABLE, None

    is_bool = node["kind"] == "bool"
    if is_bool and not isinstance(fact.value, bool):
        return Reason.CRITERION_UNAVAILABLE, None
    key = str(fact.value).lower() if is_bool else fact.value
    if key not in node["domain"]:
        return Reason.CRITERION_UNAVAILABLE, None

    confidence = fact.confidence
    if confidence is not None and not _valid_confidence(confidence):
        # NaN compares False with everything, so `nan < floor` would pass the floor.
        return Reason.CRITERION_UNAVAILABLE, None
    floor = node["confidence_floor"]
    if floor > 0 and confidence is None:
        return Reason.CONFIDENCE_UNAVAILABLE, fact.value
    if key not in node["admitted"] or (floor > 0 and fact.confidence < floor):
        return Reason.CONDITION_NOT_MET, fact.value
    return None, fact.value


OUT_OF_DOMAIN = "__out_of_domain__"


def truth_cases(tree: Mapping[str, Any]) -> list[dict[str, dict[str, Any]]]:
    """
    Fact sets for a conformance truth table — a few hundred rows, not a product
    of every fault.

    * every combination of in-domain values, at confidence 1.0;
    * from an all-admitted baseline, one fault at a time: the fact missing,
      out of domain, and — on nodes with a floor — confidence absent, just
      below, exactly at the floor, and outside [0, 1].

    Each row maps criterion → ``{"value", "confidence"}``; a missing fact is
    simply absent. The C walker replays these rows (ENG-T1).
    """
    import itertools

    nodes = tree["nodes"]

    def fact(node: Mapping[str, Any], raw: str, confidence: float | None) -> dict[str, Any]:
        value: bool | str = (raw == "true") if node["kind"] == "bool" else raw
        return {"value": value, "confidence": confidence}

    rows: list[dict[str, dict[str, Any]]] = []
    for combo in itertools.product(*(node["domain"] for node in nodes)):
        rows.append(
            {n["criterion"]: fact(n, raw, 1.0) for n, raw in zip(nodes, combo, strict=True)}
        )

    baseline = {n["criterion"]: fact(n, n["admitted"][0], 1.0) for n in nodes if n["admitted"]}
    for node in nodes:
        name = node["criterion"]
        faults: list[dict[str, Any] | None] = [None, {"value": OUT_OF_DOMAIN, "confidence": 1.0}]
        floor = node["confidence_floor"]
        if floor > 0 and node["admitted"]:
            admitted = node["admitted"][0]
            faults += [
                fact(node, admitted, None),
                fact(node, admitted, round(floor - 0.001, 6)),
                fact(node, admitted, floor),
                fact(node, admitted, 1.5),  # not a probability: unavailable, never a pass
            ]
        for fault in faults:
            row = dict(baseline)
            if fault is None:
                row.pop(name, None)
            else:
                row[name] = fault
            rows.append(row)
    return rows


def facts_from_row(row: Mapping[str, Mapping[str, Any]]) -> dict[str, Fact]:
    return {name: Fact(cell["value"], cell["confidence"]) for name, cell in row.items()}


def truth_table(tree: Mapping[str, Any]) -> dict[str, Any]:
    """The conformance vector for one tree: its rows and the walker's answers."""
    rows = []
    for case in truth_cases(tree):
        result = walk(tree, facts_from_row(case))
        rows.append(
            {
                "facts": case,
                "verdict": str(result.verdict),
                "reason": None if result.reason is None else str(result.reason),
                "failed_criterion": result.failed_criterion,
            }
        )
    return {"gate": tree["gate"], "gate_digest": tree["gate_digest"], "rows": rows}


def known_failure(tree: Mapping[str, Any], facts: Mapping[str, Fact]) -> tuple[Reason, str] | None:
    """
    The first criterion whose fact is *present* and fails, ignoring missing facts.

    Used when adjudication degraded under `fail: open`: open may excuse what
    could not be decided, never a fact that was decided and said no.
    """
    for node in tree["nodes"]:
        fact = facts.get(node["criterion"])
        if fact is None or fact.value is None:
            continue
        reason, _ = _classify(node, fact)
        if reason is not None:
            return reason, node["criterion"]
    return None


def walk(tree: Mapping[str, Any], facts: Mapping[str, Fact]) -> TreeResult:
    """
    Walk a tree. Pure: no clock, no I/O.

    Every criterion is evaluated so the trace lists them all; the verdict is
    ALLOW only if every node is satisfied, and the reason is the first failure
    in `criteria_order`.
    """
    first: tuple[Reason, str] | None = None
    evaluations: dict[str, bool | str] = {}
    for node in tree["nodes"]:
        criterion = node["criterion"]
        reason, value = _classify(node, facts.get(criterion))
        if value is not None:
            evaluations[criterion] = value
        if reason is not None and first is None:
            first = (reason, criterion)

    if first is None:
        return TreeResult(GateVerdict.ALLOW, evaluations=evaluations)
    return TreeResult(GateVerdict.BLOCK, first[0], first[1], evaluations)
