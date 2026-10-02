"""
Unit tests for numeric constraints, interval algebra, and parse validation.

Pure functions testing RFC-0009 interval algebra without fixtures:
  - open/closed edge combinations of is_at_least_as_strict_as
  - dropping and adding bounds
  - describe() formatting
  - cross-kind comparisons
  - parse_constraint validation and GateSchemaError diagnostics
"""

from __future__ import annotations

from typing import Any

import pytest

from neuroedge.engine.constraints import (
    Constraint,
    Interval,
    IntervalBound,
    parse_constraint,
)
from neuroedge.errors import GateSchemaError

PRESSURE_DEF: dict[str, Any] = {
    "type": "numeric",
    "unit": "bar",
    "range": {"min": 0, "max": 16},
    "max_age_ms": 500,
    "instructions": "Line pressure in bar",
}


def _bound(val: float, closed: bool) -> IntervalBound:
    return IntervalBound(value=float(val), closed=closed)


def _interval(
    lo: float | None = None,
    lo_closed: bool = True,
    hi: float | None = None,
    hi_closed: bool = False,
) -> Interval:
    lower = _bound(lo, lo_closed) if lo is not None else None
    upper = _bound(hi, hi_closed) if hi is not None else None
    return Interval(lower=lower, upper=upper)


def _constraint(
    lo: float | None = None,
    lo_closed: bool = True,
    hi: float | None = None,
    hi_closed: bool = False,
    criterion: str = "pressure",
) -> Constraint:
    return Constraint(
        criterion=criterion,
        kind="numeric",
        admitted=frozenset(),
        confidence_floor=0.0,
        raw={},
        interval=_interval(lo, lo_closed, hi, hi_closed),
    )


# --- Interval algebra: lower bound combinations ------------------------------


@pytest.mark.parametrize(
    "parent_lo, parent_closed, child_lo, child_closed, expected",
    [
        # Parent closed [2, ...):
        (2.0, True, 2.0, True, True),  # gte 2 allows gte 2 (equal)
        (2.0, True, 3.0, True, True),  # gte 2 allows gte 3 (tighter)
        (2.0, True, 1.0, True, False),  # gte 2 forbids gte 1 (looser)
        (2.0, True, 2.0, False, True),  # gte 2 allows gt 2 (tighter: excludes 2)
        (2.0, True, 3.0, False, True),  # gte 2 allows gt 3 (tighter)
        (2.0, True, 1.0, False, False),  # gte 2 forbids gt 1 (looser)
        # Parent open (2, ...):
        (2.0, False, 2.0, False, True),  # gt 2 allows gt 2 (equal)
        (2.0, False, 3.0, False, True),  # gt 2 allows gt 3 (tighter)
        (2.0, False, 1.0, False, False),  # gt 2 forbids gt 1 (looser)
        (2.0, False, 2.0, True, False),  # gt 2 forbids gte 2 (looser: admits 2!)
        (2.0, False, 3.0, True, True),  # gt 2 allows gte 3 (strictly above 2)
        (2.0, False, 1.0, True, False),  # gt 2 forbids gte 1 (looser)
    ],
)
def test_interval_lower_bound_combinations(
    parent_lo: float,
    parent_closed: bool,
    child_lo: float,
    child_closed: bool,
    expected: bool,
):
    parent = _interval(lo=parent_lo, lo_closed=parent_closed, hi=10.0, hi_closed=False)
    child = _interval(lo=child_lo, lo_closed=child_closed, hi=10.0, hi_closed=False)
    assert child.is_subset_of(parent) is expected

    parent_c = _constraint(lo=parent_lo, lo_closed=parent_closed, hi=10.0, hi_closed=False)
    child_c = _constraint(lo=child_lo, lo_closed=child_closed, hi=10.0, hi_closed=False)
    assert child_c.is_at_least_as_strict_as(parent_c) is expected


# --- Interval algebra: upper bound combinations ------------------------------


@pytest.mark.parametrize(
    "parent_hi, parent_closed, child_hi, child_closed, expected",
    [
        # Parent closed (..., 8]:
        (8.0, True, 8.0, True, True),  # lte 8 allows lte 8 (equal)
        (8.0, True, 7.0, True, True),  # lte 8 allows lte 7 (tighter)
        (8.0, True, 9.0, True, False),  # lte 8 forbids lte 9 (looser)
        (8.0, True, 8.0, False, True),  # lte 8 allows lt 8 (tighter: excludes 8)
        (8.0, True, 7.0, False, True),  # lte 8 allows lt 7 (tighter)
        (8.0, True, 9.0, False, False),  # lte 8 forbids lt 9 (looser)
        # Parent open (..., 8):
        (8.0, False, 8.0, False, True),  # lt 8 allows lt 8 (equal)
        (8.0, False, 7.0, False, True),  # lt 8 allows lt 7 (tighter)
        (8.0, False, 9.0, False, False),  # lt 8 forbids lt 9 (looser)
        (8.0, False, 8.0, True, False),  # lt 8 forbids lte 8 (looser: admits 8!)
        (8.0, False, 7.0, True, True),  # lt 8 allows lte 7 (strictly below 8)
        (8.0, False, 9.0, True, False),  # lt 8 forbids lte 9 (looser)
    ],
)
def test_interval_upper_bound_combinations(
    parent_hi: float,
    parent_closed: bool,
    child_hi: float,
    child_closed: bool,
    expected: bool,
):
    parent = _interval(lo=0.0, lo_closed=True, hi=parent_hi, hi_closed=parent_closed)
    child = _interval(lo=0.0, lo_closed=True, hi=child_hi, hi_closed=child_closed)
    assert child.is_subset_of(parent) is expected

    parent_c = _constraint(lo=0.0, lo_closed=True, hi=parent_hi, hi_closed=parent_closed)
    child_c = _constraint(lo=0.0, lo_closed=True, hi=child_hi, hi_closed=child_closed)
    assert child_c.is_at_least_as_strict_as(parent_c) is expected


# --- Missing / dropped bounds ------------------------------------------------


def test_child_dropping_lower_bound_is_looser():
    parent_c = _constraint(lo=2.0, hi=8.0)
    child_c = _constraint(lo=None, hi=8.0)  # dropped lower bound (-inf)
    assert child_c.is_at_least_as_strict_as(parent_c) is False


def test_child_dropping_upper_bound_is_looser():
    parent_c = _constraint(lo=2.0, hi=8.0)
    child_c = _constraint(lo=2.0, hi=None)  # dropped upper bound (+inf)
    assert child_c.is_at_least_as_strict_as(parent_c) is False


def test_child_adding_lower_bound_is_tighter():
    parent_c = _constraint(lo=None, hi=8.0)  # (-inf, 8)
    child_c = _constraint(lo=2.0, hi=8.0)  # [2, 8)
    assert child_c.is_at_least_as_strict_as(parent_c) is True


def test_child_adding_upper_bound_is_tighter():
    parent_c = _constraint(lo=2.0, hi=None)  # [2, +inf)
    child_c = _constraint(lo=2.0, hi=8.0)  # [2, 8)
    assert child_c.is_at_least_as_strict_as(parent_c) is True


def test_both_unbounded_on_a_side():
    parent_c = _constraint(lo=None, hi=8.0)
    child_c = _constraint(lo=None, hi=7.0)
    assert child_c.is_at_least_as_strict_as(parent_c) is True

    parent_c2 = _constraint(lo=2.0, hi=None)
    child_c2 = _constraint(lo=3.0, hi=None)
    assert child_c2.is_at_least_as_strict_as(parent_c2) is True


# --- Constraint.describe() ---------------------------------------------------


@pytest.mark.parametrize(
    "lo, lo_closed, hi, hi_closed, expected",
    [
        (2.0, True, 8.0, False, "[2, 8)"),
        (2.0, False, 8.0, True, "(2, 8]"),
        (2.0, True, 8.0, True, "[2, 8]"),
        (2.0, False, 8.0, False, "(2, 8)"),
        (None, False, 8.0, False, "(-inf, 8)"),
        (None, False, 8.0, True, "(-inf, 8]"),
        (2.0, True, None, False, "[2, +inf)"),
        (2.0, False, None, False, "(2, +inf)"),
        (0.85, True, 1.0, True, "[0.85, 1]"),
    ],
)
def test_constraint_describe(
    lo: float | None,
    lo_closed: bool,
    hi: float | None,
    hi_closed: bool,
    expected: str,
):
    c = _constraint(lo, lo_closed, hi, hi_closed)
    assert c.describe() == expected


# --- Cross-kind constraint comparison safety ---------------------------------


def test_numeric_vs_non_numeric_comparison_does_not_crash():
    c_num = _constraint(lo=2.0, hi=8.0)
    c_bool = Constraint("b", "bool", frozenset({"true"}), 0.0, True)

    assert c_num.is_at_least_as_strict_as(c_bool) is False
    assert c_bool.is_at_least_as_strict_as(c_num) is False


# --- Parse constraint: valid inputs ------------------------------------------


def test_parse_valid_numeric_clauses():
    c1 = parse_constraint("pressure", {"lt": 8}, PRESSURE_DEF)
    assert c1.kind == "numeric"
    assert c1.describe() == "(-inf, 8)"
    assert c1.interval.lower is None
    assert c1.interval.upper == IntervalBound(8.0, closed=False)

    c2 = parse_constraint("pressure", {"gte": 2, "lt": 8}, PRESSURE_DEF)
    assert c2.describe() == "[2, 8)"
    assert c2.interval.lower == IntervalBound(2.0, closed=True)
    assert c2.interval.upper == IntervalBound(8.0, closed=False)

    c3 = parse_constraint("pressure", {"gt": 2, "lte": 8}, PRESSURE_DEF)
    assert c3.describe() == "(2, 8]"
    assert c3.interval.lower == IntervalBound(2.0, closed=False)
    assert c3.interval.upper == IntervalBound(8.0, closed=True)


# --- Parse constraint: error cases -------------------------------------------


@pytest.mark.parametrize(
    "clause, why_pattern",
    [
        (8, "numeric criterion accepts an operator mapping"),
        ("8", "numeric criterion accepts an operator mapping"),
        (True, "numeric criterion accepts an operator mapping"),
        ({}, "must contain at least one operator"),
        ({"eq": 8}, "operator 'eq' is not defined for a 'numeric' criterion"),
        (
            {"confidence_gte": 0.9},
            "operator 'confidence_gte' is not defined for a 'numeric' criterion",
        ),
        ({"in": [2, 4]}, "operator 'in' is not defined for a 'numeric' criterion"),
        ({"gt": 2, "gte": 2}, "at most one lower bound"),
        ({"lt": 8, "lte": 8}, "at most one upper bound"),
        ({"lt": True}, "lt expects a finite number"),
        ({"lt": "8"}, "lt expects a finite number"),
        ({"lt": float("inf")}, "must be a finite number"),
        ({"lt": float("nan")}, "must be a finite number"),
        ({"lt": 20}, "outside declared range"),
        ({"gte": -1}, "outside declared range"),
        ({"gte": 8, "lte": 2}, "lower bound 8.0 > upper bound 2.0"),
        ({"gt": 5, "lt": 5}, "bounds coincide at 5.0 with an open edge"),
        ({"gte": 5, "lt": 5}, "bounds coincide at 5.0 with an open edge"),
        ({"gt": 5, "lte": 5}, "bounds coincide at 5.0 with an open edge"),
        ({"gt": 16}, "gt 16.0 excludes all of declared range"),
        ({"lt": 0}, "lt 0.0 excludes all of declared range"),
    ],
)
def test_parse_numeric_errors(clause: Any, why_pattern: str):
    with pytest.raises(GateSchemaError) as excinfo:
        parse_constraint("pressure", clause, PRESSURE_DEF)
    error = excinfo.value
    assert error.code == "NE2002"
    assert "allow_when.pressure" in error.where
    assert why_pattern in error.why
    assert error.how.strip()


# --- Gate explain formatting -------------------------------------------------


def test_gate_explain_numeric_formatting():
    from neuroedge.engine.gate_explain import _detail, explain
    from neuroedge.engine.gate_resolver import ResolvedGate

    detail_str = _detail(PRESSURE_DEF)
    assert "unit: bar" in detail_str
    assert "range: [0, 16]" in detail_str
    assert "max_age_ms: 500" in detail_str

    c = parse_constraint("pressure", {"gte": 2, "lt": 8}, PRESSURE_DEF)
    gate = ResolvedGate(
        name="test-numeric",
        version="1.0.0",
        evaluate={"pressure": PRESSURE_DEF},
        allow_when={"pressure": {"gte": 2, "lt": 8}},
        constraints={"pressure": c},
        on_block={"action": "deny"},
        budget={"p95_latency_ms": 100},
    )
    explanation = explain([gate], extends=None)
    assert len(explanation.criteria) == 1
    assert explanation.criteria[0].detail == detail_str
    assert len(explanation.clauses) == 1
    assert explanation.clauses[0].admits == "[2, 8) bar"


def test_a_threshold_too_large_for_a_float_is_a_schema_error_not_an_overflow() -> None:
    with pytest.raises(GateSchemaError):
        parse_constraint("pressure", {"lt": 10**400}, PRESSURE_DEF)
    huge_range = {**PRESSURE_DEF, "range": {"min": 0, "max": 10**400}}
    with pytest.raises(GateSchemaError):
        parse_constraint("pressure", {"lt": 8}, huge_range)
