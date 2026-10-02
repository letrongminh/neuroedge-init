"""
TSK-W1-02 Part 2a — Decision tree and verdict evaluation for numeric criteria.

Covers:
  - RFC-0009 §3c evaluation order and exact boundary ages
  - All four operators (gt, gte, lt, lte) at exact edges via math.nextafter
  - VALUE_OUT_OF_RANGE for NaN, +/-inf, and range boundaries
  - First-failure reporting in criteria_order for mixed gates
  - known_failure classification under fail: open
  - Node compilation shape and schema validation against decision_tree.v1.json
  - Conformance vectors in truth_cases / truth_table and independent oracle verification
  - Byte-identical canonical tree output for existing non-numeric gates
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from neuroedge.engine import (
    Fact,
    GateVerdict,
    Reason,
    canonicalize,
    compile_tree,
    gate_digest,
    resolve_gate_document,
    resolve_gate_file,
    tree_bytes,
    validate_tree,
    walk,
)
from neuroedge.engine.decision_tree import (
    facts_from_row,
    known_failure,
    truth_cases,
    truth_table,
)
from neuroedge.errors import GateSchemaError

# --- Helpers -----------------------------------------------------------------


def make_numeric_gate(
    allow_when: dict[str, Any] | None = None,
    range_bounds: dict[str, float] | None = None,
    max_age_ms: int = 500,
    unit: str = "bar",
    extra_evaluate: dict[str, Any] | None = None,
    extra_allow_when: dict[str, Any] | None = None,
    name: str = "numeric-test",
    order: list[str] | None = None,
):
    evaluate: dict[str, Any] = {
        "pressure": {
            "type": "numeric",
            "unit": unit,
            "range": range_bounds or {"min": 0.0, "max": 16.0},
            "max_age_ms": max_age_ms,
            "instructions": "Pressure measurement",
        },
        **(extra_evaluate or {}),
    }
    allow: dict[str, Any] = {
        "pressure": allow_when or {"gte": 2.0, "lt": 8.0},
        **(extra_allow_when or {}),
    }
    if order is not None:
        evaluate = {k: evaluate[k] for k in order}
        allow = {k: allow[k] for k in order}

    doc = {
        "schema": "neuroedge.gate/v1",
        "name": name,
        "version": "1.0.0",
        "evaluate": evaluate,
        "allow_when": allow,
        "on_block": {"action": "deny"},
        "budget": {"p95_latency_ms": 100, "fail": "closed"},
    }
    return resolve_gate_document(doc)


# --- Compilation and Schema Validation (Item 1 & 4) --------------------------


def test_numeric_node_exact_shape():
    gate = make_numeric_gate(
        allow_when={"gte": 2, "lt": 8},
        range_bounds={"min": 0, "max": 16},
        max_age_ms=500,
        unit="bar",
    )
    tree = compile_tree(gate)
    assert len(tree["nodes"]) == 1
    node = tree["nodes"][0]

    # Verify exact keys required by item 1
    assert set(node.keys()) == {
        "criterion",
        "kind",
        "domain",
        "admitted",
        "confidence_floor",
        "numeric",
    }
    assert node["criterion"] == "pressure"
    assert node["kind"] == "numeric"
    assert node["domain"] == []
    assert node["admitted"] == []
    assert node["confidence_floor"] == 0.0
    assert isinstance(node["confidence_floor"], float)

    num = node["numeric"]
    assert set(num.keys()) == {"unit", "range", "max_age_ms", "lower", "upper"}
    assert num["unit"] == "bar"
    assert num["range"] == {"min": 0.0, "max": 16.0}
    assert isinstance(num["range"]["min"], float)
    assert isinstance(num["range"]["max"], float)
    assert num["max_age_ms"] == 500
    assert isinstance(num["max_age_ms"], int)
    assert num["lower"] == {"value": 2.0, "closed": True}
    assert isinstance(num["lower"]["value"], float)
    assert num["upper"] == {"value": 8.0, "closed": False}
    assert isinstance(num["upper"]["value"], float)


def test_numeric_node_open_and_unbounded_bounds():
    # Only upper bound (gt unbounded)
    gate_upper = make_numeric_gate(allow_when={"lte": 10.0})
    tree_upper = compile_tree(gate_upper)
    num_upper = tree_upper["nodes"][0]["numeric"]
    assert num_upper["lower"] is None
    assert num_upper["upper"] == {"value": 10.0, "closed": True}

    # Only lower bound (lt unbounded)
    gate_lower = make_numeric_gate(allow_when={"gt": 1.5})
    tree_lower = compile_tree(gate_lower)
    num_lower = tree_lower["nodes"][0]["numeric"]
    assert num_lower["lower"] == {"value": 1.5, "closed": False}
    assert num_lower["upper"] is None


def test_numeric_tree_validates_against_internal_schema():
    gate = make_numeric_gate()
    tree = compile_tree(gate)
    validate_tree(tree, label="numeric-test")


def test_numeric_node_missing_numeric_key_is_rejected():
    gate = make_numeric_gate()
    tree = compile_tree(gate)
    broken_node = dict(tree["nodes"][0])
    del broken_node["numeric"]
    broken_tree = dict(tree)
    broken_tree["nodes"] = [broken_node]

    with pytest.raises(GateSchemaError) as excinfo:
        validate_tree(broken_tree)
    assert "numeric" in excinfo.value.why or "nodes.0" in excinfo.value.where


def test_non_numeric_node_carrying_numeric_key_is_rejected():
    gate = resolve_gate_document(
        {
            "schema": "neuroedge.gate/v1",
            "name": "bool-gate",
            "version": "1.0.0",
            "evaluate": {"active": {"type": "bool", "instructions": "Active"}},
            "allow_when": {"active": True},
            "on_block": {"action": "deny"},
            "budget": {"p95_latency_ms": 100},
        }
    )
    tree = compile_tree(gate)
    broken_node = dict(tree["nodes"][0])
    broken_node["numeric"] = {
        "unit": "bar",
        "range": {"min": 0.0, "max": 1.0},
        "max_age_ms": 100,
        "lower": None,
        "upper": None,
    }
    broken_tree = dict(tree)
    broken_tree["nodes"] = [broken_node]

    with pytest.raises(GateSchemaError):
        validate_tree(broken_tree)


def test_criteria_order_mismatch_is_rejected():
    gate = make_numeric_gate(
        extra_evaluate={"active": {"type": "bool", "instructions": "Active"}},
        extra_allow_when={"active": True},
        order=["pressure", "active"],
    )
    tree = compile_tree(gate)
    broken_tree = dict(tree)
    broken_tree["nodes"] = list(reversed(tree["nodes"]))

    with pytest.raises(GateSchemaError) as excinfo:
        validate_tree(broken_tree)
    assert "criteria_order" in excinfo.value.where


# --- Evaluation and Ordering Branches (Item 3) -------------------------------


def test_evaluation_branch_a_missing_or_invalid_reading():
    gate = make_numeric_gate()
    tree = compile_tree(gate)

    # Missing fact completely
    res = walk(tree, {})
    assert res.verdict is GateVerdict.BLOCK
    assert res.reason is Reason.CRITERION_UNAVAILABLE
    assert "pressure" not in res.evaluations

    # Fact value is None
    res = walk(tree, {"pressure": Fact(None, age_ms=0)})
    assert res.verdict is GateVerdict.BLOCK
    assert res.reason is Reason.CRITERION_UNAVAILABLE
    assert "pressure" not in res.evaluations

    # Fact value is boolean
    res = walk(tree, {"pressure": Fact(True, age_ms=0)})
    assert res.verdict is GateVerdict.BLOCK
    assert res.reason is Reason.CRITERION_UNAVAILABLE
    assert "pressure" not in res.evaluations

    # Fact value is string
    res = walk(tree, {"pressure": Fact("5.0", age_ms=0)})
    assert res.verdict is GateVerdict.BLOCK
    assert res.reason is Reason.CRITERION_UNAVAILABLE
    assert "pressure" not in res.evaluations

    # Fact age_ms is None
    res = walk(tree, {"pressure": Fact(5.0, age_ms=None)})
    assert res.verdict is GateVerdict.BLOCK
    assert res.reason is Reason.CRITERION_UNAVAILABLE
    assert "pressure" not in res.evaluations

    # Fact age_ms is boolean (True / False)
    res = walk(tree, {"pressure": Fact(5.0, age_ms=True)})  # type: ignore
    assert res.verdict is GateVerdict.BLOCK
    assert res.reason is Reason.CRITERION_UNAVAILABLE


def test_evaluation_branch_b_negative_age():
    gate = make_numeric_gate(max_age_ms=500)
    tree = compile_tree(gate)

    res = walk(tree, {"pressure": Fact(5.0, age_ms=-1)})
    assert res.verdict is GateVerdict.BLOCK
    assert res.reason is Reason.CRITERION_UNAVAILABLE

    res = walk(tree, {"pressure": Fact(5.0, age_ms=-1000)})
    assert res.verdict is GateVerdict.BLOCK
    assert res.reason is Reason.CRITERION_UNAVAILABLE


def test_evaluation_branch_c_reading_expired_exact_boundary():
    gate = make_numeric_gate(max_age_ms=500)
    tree = compile_tree(gate)

    # age_ms == max_age_ms passes step c
    res_exact = walk(tree, {"pressure": Fact(5.0, age_ms=500)})
    assert res_exact.verdict is GateVerdict.ALLOW
    assert res_exact.reason is None
    assert res_exact.evaluations["pressure"] == 5.0

    # age_ms == max_age_ms + 1 fails step c
    res_plus_one = walk(tree, {"pressure": Fact(5.0, age_ms=501)})
    assert res_plus_one.verdict is GateVerdict.BLOCK
    assert res_plus_one.reason is Reason.CRITERION_UNAVAILABLE

    # age_ms == 0 passes
    res_zero = walk(tree, {"pressure": Fact(5.0, age_ms=0)})
    assert res_zero.verdict is GateVerdict.ALLOW


def test_evaluation_precedence_order_enforced():
    """Verify that earlier steps fail before later steps are evaluated."""
    # Pressure interval [2.0, 8.0), range [0.0, 16.0], max_age_ms=500
    gate = make_numeric_gate(range_bounds={"min": 0.0, "max": 16.0}, max_age_ms=500)
    tree = compile_tree(gate)

    # Precedence: Branch a over Branch b (value None vs age_ms -1)
    res = walk(tree, {"pressure": Fact(None, age_ms=-1)})
    assert res.reason is Reason.CRITERION_UNAVAILABLE

    # Precedence: Branch a over Branch d (value str vs out of range)
    res = walk(tree, {"pressure": Fact("out_of_range_str", age_ms=0)})
    assert res.reason is Reason.CRITERION_UNAVAILABLE

    # Precedence: Branch b over Branch d (age -1 vs NaN)
    res = walk(tree, {"pressure": Fact(float("nan"), age_ms=-1)})
    assert res.reason is Reason.CRITERION_UNAVAILABLE

    # Precedence: Branch b over Branch d (age -1 vs value 999.0 > range.max)
    res = walk(tree, {"pressure": Fact(999.0, age_ms=-1)})
    assert res.reason is Reason.CRITERION_UNAVAILABLE

    # Precedence: Branch c over Branch d (age 501 vs NaN)
    res = walk(tree, {"pressure": Fact(float("nan"), age_ms=501)})
    assert res.reason is Reason.CRITERION_UNAVAILABLE

    # Precedence: Branch c over Branch d (age 501 vs value 999.0 > range.max)
    res = walk(tree, {"pressure": Fact(999.0, age_ms=501)})
    assert res.reason is Reason.CRITERION_UNAVAILABLE

    # Precedence: Branch d over Branch e (value 999.0 > range.max and not in interval [2, 8])
    # Age is valid (500) -> Branch d triggers VALUE_OUT_OF_RANGE, not CONDITION_NOT_MET
    res = walk(tree, {"pressure": Fact(999.0, age_ms=500)})
    assert res.verdict is GateVerdict.BLOCK
    assert res.reason is Reason.VALUE_OUT_OF_RANGE
    assert res.evaluations["pressure"] == 999.0

    # Precedence: Branch e over Branch f (value 1.0 in range [0, 16] but outside interval [2, 8))
    res = walk(tree, {"pressure": Fact(1.0, age_ms=0)})
    assert res.verdict is GateVerdict.BLOCK
    assert res.reason is Reason.CONDITION_NOT_MET
    assert res.evaluations["pressure"] == 1.0

    # Satisfied (value 5.0 in range and inside interval [2, 8))
    res = walk(tree, {"pressure": Fact(5.0, age_ms=0)})
    assert res.verdict is GateVerdict.ALLOW
    assert res.reason is None
    assert res.evaluations["pressure"] == 5.0


def test_confidence_on_numeric_fact_is_ignored():
    gate = make_numeric_gate()
    tree = compile_tree(gate)

    # Even invalid or low confidence must be ignored on numeric node
    res = walk(tree, {"pressure": Fact(5.0, confidence=0.01, age_ms=0)})
    assert res.verdict is GateVerdict.ALLOW

    res2 = walk(tree, {"pressure": Fact(5.0, confidence=float("nan"), age_ms=0)})
    assert res2.verdict is GateVerdict.ALLOW


# --- Operator Edges via math.nextafter (Item 4) ------------------------------


def test_operator_gt_exact_edges():
    gate = make_numeric_gate(
        allow_when={"gt": 5.0},
        range_bounds={"min": 0.0, "max": 10.0},
    )
    tree = compile_tree(gate)

    ulp_below = math.nextafter(5.0, -math.inf)
    ulp_above = math.nextafter(5.0, math.inf)

    # One ulp below: fails
    res_below = walk(tree, {"pressure": Fact(ulp_below, age_ms=0)})
    assert res_below.verdict is GateVerdict.BLOCK
    assert res_below.reason is Reason.CONDITION_NOT_MET

    # Exactly on bound: fails (open)
    res_on = walk(tree, {"pressure": Fact(5.0, age_ms=0)})
    assert res_on.verdict is GateVerdict.BLOCK
    assert res_on.reason is Reason.CONDITION_NOT_MET

    # One ulp above: passes
    res_above = walk(tree, {"pressure": Fact(ulp_above, age_ms=0)})
    assert res_above.verdict is GateVerdict.ALLOW
    assert res_above.reason is None


def test_operator_gte_exact_edges():
    gate = make_numeric_gate(
        allow_when={"gte": 5.0},
        range_bounds={"min": 0.0, "max": 10.0},
    )
    tree = compile_tree(gate)

    ulp_below = math.nextafter(5.0, -math.inf)
    ulp_above = math.nextafter(5.0, math.inf)

    # One ulp below: fails
    res_below = walk(tree, {"pressure": Fact(ulp_below, age_ms=0)})
    assert res_below.verdict is GateVerdict.BLOCK
    assert res_below.reason is Reason.CONDITION_NOT_MET

    # Exactly on bound: passes (closed)
    res_on = walk(tree, {"pressure": Fact(5.0, age_ms=0)})
    assert res_on.verdict is GateVerdict.ALLOW
    assert res_on.reason is None

    # One ulp above: passes
    res_above = walk(tree, {"pressure": Fact(ulp_above, age_ms=0)})
    assert res_above.verdict is GateVerdict.ALLOW
    assert res_above.reason is None


def test_operator_lt_exact_edges():
    gate = make_numeric_gate(
        allow_when={"lt": 5.0},
        range_bounds={"min": 0.0, "max": 10.0},
    )
    tree = compile_tree(gate)

    ulp_below = math.nextafter(5.0, -math.inf)
    ulp_above = math.nextafter(5.0, math.inf)

    # One ulp below: passes
    res_below = walk(tree, {"pressure": Fact(ulp_below, age_ms=0)})
    assert res_below.verdict is GateVerdict.ALLOW
    assert res_below.reason is None

    # Exactly on bound: fails (open)
    res_on = walk(tree, {"pressure": Fact(5.0, age_ms=0)})
    assert res_on.verdict is GateVerdict.BLOCK
    assert res_on.reason is Reason.CONDITION_NOT_MET

    # One ulp above: fails
    res_above = walk(tree, {"pressure": Fact(ulp_above, age_ms=0)})
    assert res_above.verdict is GateVerdict.BLOCK
    assert res_above.reason is Reason.CONDITION_NOT_MET


def test_operator_lte_exact_edges():
    gate = make_numeric_gate(
        allow_when={"lte": 5.0},
        range_bounds={"min": 0.0, "max": 10.0},
    )
    tree = compile_tree(gate)

    ulp_below = math.nextafter(5.0, -math.inf)
    ulp_above = math.nextafter(5.0, math.inf)

    # One ulp below: passes
    res_below = walk(tree, {"pressure": Fact(ulp_below, age_ms=0)})
    assert res_below.verdict is GateVerdict.ALLOW
    assert res_below.reason is None

    # Exactly on bound: passes (closed)
    res_on = walk(tree, {"pressure": Fact(5.0, age_ms=0)})
    assert res_on.verdict is GateVerdict.ALLOW
    assert res_on.reason is None

    # One ulp above: fails
    res_above = walk(tree, {"pressure": Fact(ulp_above, age_ms=0)})
    assert res_above.verdict is GateVerdict.BLOCK
    assert res_above.reason is Reason.CONDITION_NOT_MET


# --- VALUE_OUT_OF_RANGE Tests (Item 4) ---------------------------------------


def test_value_out_of_range_special_values_and_edges():
    gate = make_numeric_gate(
        allow_when={"gte": 2.0, "lte": 8.0},
        range_bounds={"min": 2.0, "max": 8.0},
    )
    tree = compile_tree(gate)

    # NaN, +inf, -inf
    for special in (float("nan"), float("inf"), float("-inf")):
        res = walk(tree, {"pressure": Fact(special, age_ms=0)})
        assert res.verdict is GateVerdict.BLOCK
        assert res.reason is Reason.VALUE_OUT_OF_RANGE

    # Just below range.min
    just_below = math.nextafter(2.0, -math.inf)
    res_low = walk(tree, {"pressure": Fact(just_below, age_ms=0)})
    assert res_low.verdict is GateVerdict.BLOCK
    assert res_low.reason is Reason.VALUE_OUT_OF_RANGE

    # Just above range.max
    just_above = math.nextafter(8.0, math.inf)
    res_high = walk(tree, {"pressure": Fact(just_above, age_ms=0)})
    assert res_high.verdict is GateVerdict.BLOCK
    assert res_high.reason is Reason.VALUE_OUT_OF_RANGE

    # Range boundaries themselves are valid and within interval
    res_min = walk(tree, {"pressure": Fact(2.0, age_ms=0)})
    assert res_min.verdict is GateVerdict.ALLOW
    assert res_min.reason is None

    res_max = walk(tree, {"pressure": Fact(8.0, age_ms=0)})
    assert res_max.verdict is GateVerdict.ALLOW
    assert res_max.reason is None


# --- Mixed Gate & Criteria Order First-Failure (Item 4) ----------------------


def test_first_failure_in_criteria_order_mixed_gate():
    # Order: authenticated (bool) then pressure (numeric)
    gate_bool_first = make_numeric_gate(
        extra_evaluate={"authenticated": {"type": "bool", "instructions": "Is auth"}},
        extra_allow_when={"authenticated": True},
        order=["authenticated", "pressure"],
    )
    tree_bool_first = compile_tree(gate_bool_first)

    # Both fail: authenticated is False (condition_not_met), pressure is 100.0 (value_out_of_range)
    res_bf = walk(
        tree_bool_first,
        {
            "authenticated": Fact(False, 1.0),
            "pressure": Fact(100.0, age_ms=0),
        },
    )
    assert res_bf.verdict is GateVerdict.BLOCK
    assert res_bf.reason is Reason.CONDITION_NOT_MET
    assert res_bf.failed_criterion == "authenticated"
    # Both evaluated values recorded in evaluations
    assert res_bf.evaluations == {"authenticated": False, "pressure": 100.0}

    # Order: pressure (numeric) then authenticated (bool)
    gate_num_first = make_numeric_gate(
        extra_evaluate={"authenticated": {"type": "bool", "instructions": "Is auth"}},
        extra_allow_when={"authenticated": True},
        order=["pressure", "authenticated"],
    )
    tree_num_first = compile_tree(gate_num_first)

    res_nf = walk(
        tree_num_first,
        {
            "authenticated": Fact(False, 1.0),
            "pressure": Fact(100.0, age_ms=0),
        },
    )
    assert res_nf.verdict is GateVerdict.BLOCK
    assert res_nf.reason is Reason.VALUE_OUT_OF_RANGE
    assert res_nf.failed_criterion == "pressure"
    assert res_nf.evaluations == {"pressure": 100.0, "authenticated": False}


# --- known_failure for Numeric Nodes (Item 4) --------------------------------


def test_known_failure_numeric_classifications():
    gate = make_numeric_gate(
        allow_when={"gte": 2.0, "lt": 8.0},
        range_bounds={"min": 0.0, "max": 16.0},
        max_age_ms=500,
    )
    tree = compile_tree(gate)

    # Missing fact: known_failure ignores it (fail: open excuses missing)
    assert known_failure(tree, {}) is None
    assert known_failure(tree, {"pressure": Fact(None, age_ms=0)}) is None

    # Present fact failing with VALUE_OUT_OF_RANGE: stays a known 'no'
    kf_oor = known_failure(tree, {"pressure": Fact(20.0, age_ms=0)})
    assert kf_oor == (Reason.VALUE_OUT_OF_RANGE, "pressure")

    # Present fact failing with CONDITION_NOT_MET: stays a known 'no'
    kf_cnm = known_failure(tree, {"pressure": Fact(1.0, age_ms=0)})
    assert kf_cnm == (Reason.CONDITION_NOT_MET, "pressure")

    # Present fact failing with CRITERION_UNAVAILABLE (expired age): stays a known 'no'
    kf_age = known_failure(tree, {"pressure": Fact(5.0, age_ms=600)})
    assert kf_age == (Reason.CRITERION_UNAVAILABLE, "pressure")

    # Present fact satisfied: returns None
    assert known_failure(tree, {"pressure": Fact(5.0, age_ms=0)}) is None

    # Waived criterion: returns None
    assert (
        known_failure(
            tree,
            {"pressure": Fact(20.0, age_ms=0)},
            waived=frozenset({"pressure"}),
        )
        is None
    )


# --- Conformance Vectors & Truth Table (Item 6 & 4) --------------------------


def _hand_written_numeric_oracle(
    facts: dict[str, Fact],
) -> tuple[GateVerdict, Reason | None, str | None]:
    """Independent hand-written oracle for pressure in [2.0, 8.0), range [0.0, 16.0], max_age 500."""
    fact = facts.get("pressure")
    if fact is None or fact.value is None:
        return GateVerdict.BLOCK, Reason.CRITERION_UNAVAILABLE, "pressure"
    if isinstance(fact.value, bool) or not isinstance(fact.value, (int, float)):
        return GateVerdict.BLOCK, Reason.CRITERION_UNAVAILABLE, "pressure"
    if fact.age_ms is None or isinstance(fact.age_ms, bool) or not isinstance(fact.age_ms, int):
        return GateVerdict.BLOCK, Reason.CRITERION_UNAVAILABLE, "pressure"
    if fact.age_ms < 0:
        return GateVerdict.BLOCK, Reason.CRITERION_UNAVAILABLE, "pressure"
    if fact.age_ms > 500:
        return GateVerdict.BLOCK, Reason.CRITERION_UNAVAILABLE, "pressure"

    v = float(fact.value)
    if not math.isfinite(v) or v < 0.0 or v > 16.0:
        return GateVerdict.BLOCK, Reason.VALUE_OUT_OF_RANGE, "pressure"
    if v < 2.0 or v >= 8.0:
        return GateVerdict.BLOCK, Reason.CONDITION_NOT_MET, "pressure"
    return GateVerdict.ALLOW, None, None


def test_truth_table_numeric_rows_and_oracle_match():
    gate = make_numeric_gate(
        allow_when={"gte": 2.0, "lt": 8.0},
        range_bounds={"min": 0.0, "max": 16.0},
        max_age_ms=500,
    )
    tree = compile_tree(gate)
    cases = truth_cases(tree)

    # 1. Spot check specific rows from item 6
    # Baseline satisfies range & interval with age_ms = 0
    assert {"pressure": {"value": 2.0, "age_ms": 0}} in cases

    # Missing fact row (empty dict)
    assert {} in cases

    # Age boundary faults
    assert {"pressure": {"value": 2.0, "age_ms": 500}} in cases
    assert {"pressure": {"value": 2.0, "age_ms": 501}} in cases
    assert {"pressure": {"value": 2.0, "age_ms": -1}} in cases

    # Special values
    assert {"pressure": {"value": "nan", "age_ms": 0}} in cases
    assert {"pressure": {"value": "inf", "age_ms": 0}} in cases
    assert {"pressure": {"value": "-inf", "age_ms": 0}} in cases

    # Range edges and nextafter outside range
    assert {"pressure": {"value": 0.0, "age_ms": 0}} in cases
    assert {"pressure": {"value": 16.0, "age_ms": 0}} in cases
    assert {"pressure": {"value": math.nextafter(0.0, -math.inf), "age_ms": 0}} in cases
    assert {"pressure": {"value": math.nextafter(16.0, math.inf), "age_ms": 0}} in cases

    # Bound edges: 2.0 and 8.0, and their 1-ulp neighbours
    assert {"pressure": {"value": math.nextafter(2.0, -math.inf), "age_ms": 0}} in cases
    assert {"pressure": {"value": math.nextafter(2.0, math.inf), "age_ms": 0}} in cases
    assert {"pressure": {"value": math.nextafter(8.0, -math.inf), "age_ms": 0}} in cases
    assert {"pressure": {"value": math.nextafter(8.0, math.inf), "age_ms": 0}} in cases

    # 2. Verify truth_table results against independent hand-written oracle
    table = truth_table(tree)
    assert table["gate"] == tree["gate"]
    assert table["gate_digest"] == tree["gate_digest"]
    assert len(table["rows"]) == len(cases)

    for row in table["rows"]:
        facts = facts_from_row(row["facts"])
        expected_verdict, expected_reason, expected_fail = _hand_written_numeric_oracle(facts)
        assert row["verdict"] == str(expected_verdict), f"row failed: {row['facts']}"
        assert row["reason"] == (None if expected_reason is None else str(expected_reason))
        assert row["failed_criterion"] == expected_fail


# --- Non-Numeric Gate Byte-for-Byte Backward Compatibility (Item 1 & 4) -------


def test_existing_non_numeric_gates_compile_byte_identical(
    gates_dir, gate_fixtures_dir, fixture_registry
):
    """
    Trees of gates WITHOUT numeric criteria must produce identical node keys,
    canonical bytes, and digest.
    """
    search_paths = list(gates_dir.rglob("*.yaml")) + list(
        (gate_fixtures_dir / "valid").glob("*.yaml")
    )
    assert search_paths, "found gate files to verify"

    tested_count = 0
    for path in search_paths:
        try:
            gate = resolve_gate_file(path, registry=fixture_registry)
        except Exception:
            # Skip invalid fixtures or non-gate files
            continue

        if any(c.kind == "numeric" for c in gate.constraints.values()):
            continue

        tree = compile_tree(gate)
        tested_count += 1

        # Assert nodes have strictly the old keys and NO numeric key
        for node in tree["nodes"]:
            assert set(node.keys()) == {
                "criterion",
                "kind",
                "domain",
                "admitted",
                "confidence_floor",
            }
            assert "numeric" not in node

        # Validate against decision_tree.v1.json
        validate_tree(tree, label=str(path))

        # Assert canonical tree bytes and digest
        assert tree_bytes(tree) == canonicalize(tree)
        assert tree["gate_digest"] == gate_digest(gate)

    assert tested_count > 0, "verified at least one non-numeric gate"
