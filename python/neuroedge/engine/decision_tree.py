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

This JSON form is internal to the host and not frozen. The device reads the
same tree in the binary layout RFC-0003 freezes (`NETR` v1, `binary_tree.py`).
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..errors import GateSchemaError
from .canonical import canonicalize, gate_digest
from .constraints import parse_constraint
from .gate_resolver import ResolvedGate
from .verdict import DIGITAL_IN_MAX_AGE_MS, DIGITAL_IN_SOURCE, Fact, GateVerdict, Reason

TREE_SCHEMA = "neuroedge.decision_tree/v1"
_SCHEMA_FILE = Path(__file__).with_name("decision_tree.v1.json")


def _domain(definition: Mapping[str, Any]) -> list[str]:
    kind = definition["type"]
    if kind == "bool":
        return ["false", "true"]
    if kind == "level":
        return list(definition["levels"])
    if kind == "numeric":
        return []
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
        node: dict[str, Any] = {
            "criterion": criterion,
            "kind": constraint.kind,
            "domain": _domain(definition),
            "admitted": sorted(constraint.admitted),
            "confidence_floor": constraint.confidence_floor,
        }
        if constraint.kind == "numeric":
            interval = constraint.interval
            lower = interval.lower if interval is not None else None
            upper = interval.upper if interval is not None else None
            range_def = definition["range"]
            node["numeric"] = {
                "unit": str(definition["unit"]),
                "range": {
                    "min": float(range_def["min"]),
                    "max": float(range_def["max"]),
                },
                "max_age_ms": int(definition["max_age_ms"]),
                "lower": (
                    {"value": float(lower.value), "closed": bool(lower.closed)}
                    if lower is not None
                    else None
                ),
                "upper": (
                    {"value": float(upper.value), "closed": bool(upper.closed)}
                    if upper is not None
                    else None
                ),
            }
        nodes.append(node)

    on_block = gate.on_block
    confirmed_numeric = [
        node["criterion"]
        for node in nodes
        if node["kind"] == "numeric"
        and node["criterion"] in (on_block.get("confirms") or ())
        and on_block.get("action") == "ask"
    ]
    if confirmed_numeric:
        raise GateSchemaError(
            where=f"{gate.name}@{gate.version} -> on_block.confirms",
            why=f"numeric criteria {confirmed_numeric} cannot be confirmed by a person (RFC-0009 §3a)",
            how=f"remove {confirmed_numeric} from on_block.confirms",
        )

    tree = {
        "schema": TREE_SCHEMA,
        "gate": f"{gate.name}@{gate.version}",
        "gate_digest": gate_digest(gate),
        "criteria_order": list(gate.constraints),
        "nodes": nodes,
        "on_block": dict(gate.on_block),
        "budget": dict(gate.budget),
    }
    if gate.arguments:
        # RFC-0005: checked before any node, in declaration order (root first).
        tree["arguments"] = [{"name": name, **limit} for name, limit in gate.arguments.items()]
    return tree


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
    evaluations: dict[str, Any] = field(default_factory=dict)


def _valid_confidence(value: Any) -> bool:
    """A probability: a real number (not a bool) in [0, 1]. NaN fails the range test."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0.0 <= value <= 1.0


def _level_is_fresh(fact: Fact) -> bool:
    """A `digital.in` level was read at most `DIGITAL_IN_MAX_AGE_MS` before the evaluation, not after it."""
    age = fact.age_ms
    if age is None or isinstance(age, bool) or not isinstance(age, int):
        return False
    return 0 <= age <= DIGITAL_IN_MAX_AGE_MS


def _classify(node: Mapping[str, Any], fact: Fact | None) -> tuple[Reason | None, Any]:
    """Return (reason or None when satisfied, the value for the trace)."""
    if node["kind"] == "numeric":
        # RFC-0009 §3c evaluation order:
        # a. Missing reading, invalid type, or missing age_ms -> CRITERION_UNAVAILABLE
        if fact is None or fact.value is None:
            return Reason.CRITERION_UNAVAILABLE, None
        if isinstance(fact.value, bool) or not isinstance(fact.value, (int, float)):
            return Reason.CRITERION_UNAVAILABLE, None
        if fact.source == "commanded":
            # RFC-0009 §3f: what software asked for is not what a sensor measured.
            return Reason.CRITERION_UNAVAILABLE, None
        if fact.age_ms is None or isinstance(fact.age_ms, bool) or not isinstance(fact.age_ms, int):
            return Reason.CRITERION_UNAVAILABLE, None

        # b. Causal violation: age_ms < 0 -> CRITERION_UNAVAILABLE
        if fact.age_ms < 0:
            return Reason.CRITERION_UNAVAILABLE, None

        num = node["numeric"]
        # c. Reading expired: age_ms > max_age_ms -> CRITERION_UNAVAILABLE (age == max_age_ms passes)
        if fact.age_ms > num["max_age_ms"]:
            return Reason.CRITERION_UNAVAILABLE, None

        # d. Non-finite or outside declared range -> VALUE_OUT_OF_RANGE
        try:
            val = float(fact.value)
        except OverflowError:  # an int no float can hold is out of any range
            return Reason.VALUE_OUT_OF_RANGE, fact.value
        range_min = float(num["range"]["min"])
        range_max = float(num["range"]["max"])
        if not math.isfinite(val) or val < range_min or val > range_max:
            return Reason.VALUE_OUT_OF_RANGE, fact.value

        # e. Finite, in range, but outside admitted interval -> CONDITION_NOT_MET
        lower = num.get("lower")
        if lower is not None:
            low_val = float(lower["value"])
            if lower["closed"]:
                if val < low_val:
                    return Reason.CONDITION_NOT_MET, fact.value
            else:
                if val <= low_val:
                    return Reason.CONDITION_NOT_MET, fact.value

        upper = num.get("upper")
        if upper is not None:
            high_val = float(upper["value"])
            if upper["closed"]:
                if val > high_val:
                    return Reason.CONDITION_NOT_MET, fact.value
            else:
                if val >= high_val:
                    return Reason.CONDITION_NOT_MET, fact.value

        # f. Satisfied
        return None, fact.value

    if fact is None or fact.value is None:
        return Reason.CRITERION_UNAVAILABLE, None

    if fact.source == DIGITAL_IN_SOURCE and not _level_is_fresh(fact):
        # RFC-0007 §3a: a bool has no `max_age_ms`, so the age of a digital.in level is
        # capped in code, and a level without a usable read mark has no age at all.
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


def numeric_baseline_value(node: Mapping[str, Any]) -> float:
    """A reading inside both the interval and the range of a numeric node (the all-satisfied row)."""
    num = node["numeric"]
    range_min = float(num["range"]["min"])
    range_max = float(num["range"]["max"])
    lower = num.get("lower")
    upper = num.get("upper")

    def satisfies(val: float) -> bool:
        if not (range_min <= val <= range_max):
            return False
        if lower is not None:
            low_val = float(lower["value"])
            if lower["closed"]:
                if val < low_val:
                    return False
            else:
                if val <= low_val:
                    return False
        if upper is not None:
            high_val = float(upper["value"])
            if upper["closed"]:
                if val > high_val:
                    return False
            else:
                if val >= high_val:
                    return False
        return True

    candidates: list[float] = []
    if lower is not None:
        candidates.append(float(lower["value"]))
    if upper is not None:
        candidates.append(float(upper["value"]))
    lo = float(lower["value"]) if lower is not None else range_min
    hi = float(upper["value"]) if upper is not None else range_max
    candidates.append((lo + hi) / 2.0)
    candidates.append(range_min)
    candidates.append(range_max)

    for c in candidates:
        if satisfies(c):
            return c
    raise ValueError(
        f"could not find a satisfying baseline for numeric criterion {node['criterion']}"
    )


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
    has_numeric = any(n["kind"] == "numeric" for n in nodes)

    if not has_numeric:

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
            faults: list[dict[str, Any] | None] = [
                None,
                {"value": OUT_OF_DOMAIN, "confidence": 1.0},
            ]
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

    def non_num_fact(node: Mapping[str, Any], raw: str, confidence: float | None) -> dict[str, Any]:
        value: bool | str = (raw == "true") if node["kind"] == "bool" else raw
        return {"value": value, "confidence": confidence}

    # (i) All-satisfied baseline
    baseline: dict[str, dict[str, Any]] = {}
    for n in nodes:
        if n["kind"] == "numeric":
            baseline[n["criterion"]] = {
                "value": numeric_baseline_value(n),
                "age_ms": 0,
            }
        else:
            admitted = n["admitted"][0] if n["admitted"] else n["domain"][0]
            baseline[n["criterion"]] = non_num_fact(n, admitted, 1.0)

    rows: list[dict[str, dict[str, Any]]] = []

    # Combos of bool/level/choice nodes with numeric baseline
    non_numeric_nodes = [n for n in nodes if n["kind"] != "numeric"]
    if non_numeric_nodes:
        for combo in itertools.product(*(n["domain"] for n in non_numeric_nodes)):
            row = dict(baseline)
            for n, raw in zip(non_numeric_nodes, combo, strict=True):
                row[n["criterion"]] = non_num_fact(n, raw, 1.0)
            rows.append(row)
    else:
        rows.append(dict(baseline))

    # (ii) Faults per node
    for node in nodes:
        name = node["criterion"]
        if node["kind"] == "numeric":
            num = node["numeric"]
            base_val = baseline[name]["value"]
            max_age_ms = num["max_age_ms"]
            range_min = float(num["range"]["min"])
            range_max = float(num["range"]["max"])

            faults: list[dict[str, Any] | None] = [
                None,
                {"value": base_val, "age_ms": max_age_ms},
                {"value": base_val, "age_ms": max_age_ms + 1},
                {"value": base_val, "age_ms": -1},
                {"value": "nan", "age_ms": 0},
                {"value": "inf", "age_ms": 0},
                {"value": "-inf", "age_ms": 0},
                {"value": range_min, "age_ms": 0},
                {"value": range_max, "age_ms": 0},
                {"value": math.nextafter(range_min, -math.inf), "age_ms": 0},
                {"value": math.nextafter(range_max, math.inf), "age_ms": 0},
            ]
            for bound in (num.get("lower"), num.get("upper")):
                if bound is not None:
                    bv = float(bound["value"])
                    for v in (bv, math.nextafter(bv, -math.inf), math.nextafter(bv, math.inf)):
                        if range_min <= v <= range_max:
                            faults.append({"value": v, "age_ms": 0})
        else:
            faults = [None, {"value": OUT_OF_DOMAIN, "confidence": 1.0}]
            floor = node["confidence_floor"]
            if floor > 0 and node["admitted"]:
                admitted = node["admitted"][0]
                faults += [
                    non_num_fact(node, admitted, None),
                    non_num_fact(node, admitted, round(floor - 0.001, 6)),
                    non_num_fact(node, admitted, floor),
                    non_num_fact(node, admitted, 1.5),
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
    facts: dict[str, Fact] = {}
    for name, cell in row.items():
        val = cell["value"]
        if "age_ms" in cell:
            if val == "nan":
                num_val = float("nan")
            elif val == "inf":
                num_val = float("inf")
            elif val == "-inf":
                num_val = float("-inf")
            else:
                num_val = val
            facts[name] = Fact(num_val, age_ms=cell["age_ms"])
        else:
            facts[name] = Fact(val, cell.get("confidence"))
    return facts


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


def known_failure(
    tree: Mapping[str, Any], facts: Mapping[str, Fact], waived: frozenset[str] = frozenset()
) -> tuple[Reason, str] | None:
    """
    The first criterion whose fact is *present* and fails, ignoring missing facts.

    Used when adjudication degraded under `fail: open`: open may excuse what
    could not be decided, never a fact that was decided and said no. A numeric
    criterion is the exception: a missing reading is a lost sensor, and RFC-0009 §5
    blocks every branch of it, so open does not excuse it either.
    """
    for node in tree["nodes"]:
        if node["criterion"] in waived:
            continue
        fact = facts.get(node["criterion"])
        if fact is None or fact.value is None:
            # A lost digital.in line is a lost input, like a lost numeric sensor: not
            # something `fail: open` may excuse (RFC-0007 §3e). A source of any other kind
            # that gave no value is what open is for.
            if node["kind"] == "numeric" or (fact is not None and fact.source == DIGITAL_IN_SOURCE):
                return Reason.CRITERION_UNAVAILABLE, node["criterion"]
            continue
        reason, _ = _classify(node, fact)
        if reason is not None:
            return reason, node["criterion"]
    return None


def walk(
    tree: Mapping[str, Any], facts: Mapping[str, Fact], waived: frozenset[str] = frozenset()
) -> TreeResult:
    """
    Walk a tree. Pure: no clock, no I/O.

    Every criterion is evaluated so the trace lists them all; the verdict is
    ALLOW only if every node is satisfied, and the reason is the first failure
    in `criteria_order`.

    `waived` are criteria a person confirmed (RFC-0006): they count as
    satisfied whatever their fact says. The engine passes only criteria the
    gate's own `on_block.confirms` lists, and only after a confirmation.
    """
    first: tuple[Reason, str] | None = None
    evaluations: dict[str, Any] = {}
    for node in tree["nodes"]:
        criterion = node["criterion"]
        reason, value = _classify(node, facts.get(criterion))
        if value is not None:
            evaluations[criterion] = value
        if criterion in waived:
            reason = None
        if reason is not None and first is None:
            first = (reason, criterion)

    if first is None:
        return TreeResult(GateVerdict.ALLOW, evaluations=evaluations)
    return TreeResult(GateVerdict.BLOCK, first[0], first[1], evaluations)
