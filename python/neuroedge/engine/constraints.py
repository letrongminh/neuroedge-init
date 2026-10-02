"""
Normalised `allow_when` clauses and the partial order that decides tightening.

Appendix B.5 principle 2 says a derived gate may only ever *tighten*
`allow_when`. To enforce that mechanically rather than by review, each clause is
normalised into the set of adjudication outcomes it admits. "Tighter" then has
an exact meaning: the child's admitted set is a subset of the parent's, and the
child's confidence floor is no lower.

Operators come from Appendix B.2 and no others; an unknown operator is a schema
error, not a permissive default.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..errors import GateSchemaError

BOOL_OPERATORS = frozenset({"confidence_gte"})
LEVEL_OPERATORS = frozenset({"eq", "lte", "gte"})
CHOICE_OPERATORS = frozenset({"in", "not_in", "eq"})
NUMERIC_OPERATORS = frozenset({"gt", "gte", "lt", "lte"})

_OPERATORS_BY_KIND = {
    "bool": BOOL_OPERATORS,
    "level": LEVEL_OPERATORS,
    "choice": CHOICE_OPERATORS,
    "numeric": NUMERIC_OPERATORS,
}


def is_finite_number(value: Any) -> bool:
    """A real number that converts to a finite float; a bool, NaN, ±inf or a huge int is not."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False


def _format_num(v: float) -> str:
    """Format a threshold or bound cleanly, without trailing .0 for integers."""
    if math.isinf(v):
        return "-inf" if v < 0 else "+inf"
    if v == int(v):
        return str(int(v))
    return f"{v:g}"


@dataclass(frozen=True)
class IntervalBound:
    """One boundary of a numeric interval: a finite value and an open/closed flag."""

    value: float
    closed: bool  # True for closed (>= or <=), False for open (> or <)


def _bound_within(inner: IntervalBound | None, outer: IntervalBound | None, *, lower: bool) -> bool:
    """
    True when ``inner`` does not reach past ``outer`` on the same side.

    A missing ``outer`` bound is infinite and holds anything; a missing ``inner`` bound is infinite
    and holds nothing finite. On equal values a closed ``inner`` edge is looser than an open ``outer``.
    """
    if outer is None:
        return True
    if inner is None:
        return False
    if inner.value == outer.value:
        return outer.closed or not inner.closed
    return inner.value > outer.value if lower else inner.value < outer.value


@dataclass(frozen=True)
class Interval:
    """
    An admitted interval [lower, upper] on the real line.

    A missing lower bound means -inf; a missing upper bound means +inf.
    """

    lower: IntervalBound | None = None
    upper: IntervalBound | None = None

    def describe(self) -> str:
        left = "[" if self.lower is not None and self.lower.closed else "("
        low_str = _format_num(self.lower.value) if self.lower is not None else "-inf"
        right = "]" if self.upper is not None and self.upper.closed else ")"
        high_str = _format_num(self.upper.value) if self.upper is not None else "+inf"
        return f"{left}{low_str}, {high_str}{right}"

    def is_subset_of(self, other: Interval) -> bool:
        """
        True when this interval is a subset of other.

        Equality of bounds counts as tightening. Closed is looser than open for equal bounds:
        a child closing an edge the parent left open admits the boundary point that the parent
        forbade, so it is not a subset.
        """
        return _bound_within(self.lower, other.lower, lower=True) and _bound_within(
            self.upper, other.upper, lower=False
        )


@dataclass(frozen=True)
class Constraint:
    """
    One normalised `allow_when` clause.

    Attributes
    ----------
    criterion:
        The `evaluate` key this clause constrains.
    kind:
        The criterion's declared type: ``bool``, ``level``, ``choice`` or ``numeric``.
    admitted:
        Outcome values that satisfy the clause. Booleans normalise to the
        strings ``"true"`` / ``"false"`` so every kind shares one comparison.
        Empty for ``numeric`` constraints.
    confidence_floor:
        Minimum required confidence. ``0.0`` means unspecified. Only ``bool``
        criteria carry a floor (Appendix B.2).
    raw:
        The clause exactly as authored, for diagnostics.
    interval:
        For ``numeric`` criteria, the normalised interval admitted by the clause.
    """

    criterion: str
    kind: str
    admitted: frozenset[str]
    confidence_floor: float
    raw: Any
    interval: Interval | None = None

    def describe(self) -> str:
        if self.kind == "numeric" and self.interval is not None:
            return self.interval.describe()
        floor = f", confidence >= {self.confidence_floor}" if self.confidence_floor else ""
        return f"{{{', '.join(sorted(self.admitted))}}}{floor}"

    def is_at_least_as_strict_as(self, other: Constraint) -> bool:
        """
        True when this clause admits no more than ``other`` does.

        This is the decision procedure behind principle 2. Equality counts as
        tightening: restating a parent clause verbatim is always permitted.
        """
        if self.kind != other.kind:
            return False
        if self.kind == "numeric":
            if self.interval is None or other.interval is None:
                return False
            return self.interval.is_subset_of(other.interval)
        return self.admitted <= other.admitted and self.confidence_floor >= other.confidence_floor


def _fail(criterion: str, why: str, how: str) -> GateSchemaError:
    return GateSchemaError(where=f"allow_when.{criterion}", why=why, how=how)


def _operator_clause(criterion: str, kind: str, clause: Mapping[str, Any]) -> tuple[str, Any]:
    """Extract the single permitted operator from a mapping clause."""
    permitted = _OPERATORS_BY_KIND[kind]
    keys = list(clause.keys())
    if len(keys) != 1:
        raise _fail(
            criterion,
            f"a clause must carry exactly one operator, found {len(keys)}: {sorted(keys)}",
            f"split the clause, or use a single operator from {sorted(permitted)}",
        )
    operator = keys[0]
    if operator not in permitted:
        raise _fail(
            criterion,
            f"operator {operator!r} is not defined for a {kind!r} criterion",
            f"use one of {sorted(permitted)} (Proposal Appendix B.2)",
        )
    return operator, clause[operator]


def _parse_bool(criterion: str, clause: Any) -> Constraint:
    if isinstance(clause, bool):
        return Constraint(criterion, "bool", frozenset({str(clause).lower()}), 0.0, clause)

    if isinstance(clause, Mapping):
        _, value = _operator_clause(criterion, "bool", clause)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise _fail(
                criterion,
                f"confidence_gte expects a number, got {type(value).__name__}",
                "write a value between 0.0 and 1.0, e.g. { confidence_gte: 0.9 }",
            )
        if not 0.0 <= float(value) <= 1.0:
            raise _fail(
                criterion,
                f"confidence_gte must lie in [0.0, 1.0], got {value}",
                "confidence is a probability; rescale the threshold into [0.0, 1.0]",
            )
        # confidence_gte asserts the criterion held, with at least this confidence.
        return Constraint(criterion, "bool", frozenset({"true"}), float(value), dict(clause))

    raise _fail(
        criterion,
        f"a bool criterion accepts true, false or {{ confidence_gte: x }}, got {clause!r}",
        "see Proposal Appendix B.2 for the bool operator set",
    )


def _parse_level(criterion: str, clause: Any, levels: list[str]) -> Constraint:
    def index_of(value: Any) -> int:
        if value not in levels:
            raise _fail(
                criterion,
                f"{value!r} is not a declared level; declared levels are {levels}",
                f"use one of {levels}, or add the level to evaluate.{criterion}.levels",
            )
        return levels.index(value)

    if isinstance(clause, str):
        # Bare level is shorthand for equality.
        index_of(clause)
        return Constraint(criterion, "level", frozenset({clause}), 0.0, clause)

    if isinstance(clause, Mapping):
        operator, value = _operator_clause(criterion, "level", clause)
        position = index_of(value)
        if operator == "eq":
            admitted = {levels[position]}
        elif operator == "lte":
            admitted = set(levels[: position + 1])
        else:  # gte
            admitted = set(levels[position:])
        return Constraint(criterion, "level", frozenset(admitted), 0.0, dict(clause))

    raise _fail(
        criterion,
        f"a level criterion accepts a bare level or one of {sorted(LEVEL_OPERATORS)}, got {clause!r}",
        "see Proposal Appendix B.2 for the level operator set",
    )


def _parse_choice(criterion: str, clause: Any, options: list[str]) -> Constraint:
    def check(values: list[Any]) -> list[str]:
        unknown = [v for v in values if v not in options]
        if unknown:
            raise _fail(
                criterion,
                f"{unknown!r} are not declared options; declared options are {options}",
                f"use values from {options}, or extend evaluate.{criterion}.options",
            )
        return [str(v) for v in values]

    if isinstance(clause, str):
        return Constraint(criterion, "choice", frozenset(check([clause])), 0.0, clause)

    if isinstance(clause, Mapping):
        operator, value = _operator_clause(criterion, "choice", clause)
        if operator == "eq":
            if not isinstance(value, str):
                raise _fail(
                    criterion,
                    f"eq expects a single option name, got {type(value).__name__}",
                    "use `in` for a set of options",
                )
            admitted = set(check([value]))
        else:
            if not isinstance(value, list):
                raise _fail(
                    criterion,
                    f"{operator} expects a list of option names, got {type(value).__name__}",
                    f"write {operator}: [option_a, option_b]",
                )
            listed = set(check(value))
            admitted = listed if operator == "in" else set(options) - listed
        return Constraint(criterion, "choice", frozenset(admitted), 0.0, dict(clause))

    raise _fail(
        criterion,
        f"a choice criterion accepts a bare option or one of {sorted(CHOICE_OPERATORS)}, got {clause!r}",
        "see Proposal Appendix B.2 for the choice operator set",
    )


def _parse_numeric(criterion: str, clause: Any, definition: Mapping[str, Any]) -> Constraint:
    if not isinstance(clause, Mapping):
        raise _fail(
            criterion,
            f"a numeric criterion accepts an operator mapping ({', '.join(sorted(NUMERIC_OPERATORS))}), got {clause!r}",
            "write an interval mapping, e.g. { gte: 2, lt: 8 } or { lt: 8 }",
        )

    if not clause:
        raise _fail(
            criterion,
            "a numeric clause must contain at least one operator, found none",
            f"use one or two operators from {sorted(NUMERIC_OPERATORS)}, e.g. {{ lt: 8 }}",
        )

    for op in clause:
        if op not in NUMERIC_OPERATORS:
            raise _fail(
                criterion,
                f"operator {op!r} is not defined for a 'numeric' criterion",
                f"use one or two operators from {sorted(NUMERIC_OPERATORS)} (RFC-0009 §3a)",
            )

    has_gt = "gt" in clause
    has_gte = "gte" in clause
    has_lt = "lt" in clause
    has_lte = "lte" in clause

    if has_gt and has_gte:
        raise _fail(
            criterion,
            "at most one lower bound (gt or gte) is allowed, found both 'gt' and 'gte'",
            "choose either 'gt' (open) or 'gte' (closed)",
        )
    if has_lt and has_lte:
        raise _fail(
            criterion,
            "at most one upper bound (lt or lte) is allowed, found both 'lt' and 'lte'",
            "choose either 'lt' (open) or 'lte' (closed)",
        )

    range_obj = definition.get("range", {})
    range_min = range_obj.get("min")
    range_max = range_obj.get("max")
    if not is_finite_number(range_min) or not is_finite_number(range_max) or range_min >= range_max:
        raise _fail(
            criterion,
            f"declared range [{range_min}, {range_max}] is invalid",
            "declare finite min and max with min < max",
        )

    range_min_f = float(range_min)
    range_max_f = float(range_max)

    for op, val in clause.items():
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise _fail(
                criterion,
                f"{op} expects a finite number, got {type(val).__name__}",
                "write a numeric threshold, e.g. { lt: 8 }",
            )
        if not is_finite_number(val):
            raise _fail(
                criterion,
                f"threshold for {op} must be a finite number, got {val!r}",
                f"provide a finite threshold in [{_format_num(range_min_f)}, {_format_num(range_max_f)}]",
            )
        val_f = float(val)
        if val_f < range_min_f or val_f > range_max_f:
            raise _fail(
                criterion,
                f"threshold {val} for {op} is outside declared range [{_format_num(range_min_f)}, {_format_num(range_max_f)}]",
                f"choose a threshold within [{_format_num(range_min_f)}, {_format_num(range_max_f)}]",
            )

    lower: IntervalBound | None = None
    if has_gt:
        lower = IntervalBound(value=float(clause["gt"]), closed=False)
    elif has_gte:
        lower = IntervalBound(value=float(clause["gte"]), closed=True)

    upper: IntervalBound | None = None
    if has_lt:
        upper = IntervalBound(value=float(clause["lt"]), closed=False)
    elif has_lte:
        upper = IntervalBound(value=float(clause["lte"]), closed=True)

    if lower is not None and upper is not None:
        if lower.value > upper.value:
            raise _fail(
                criterion,
                f"empty interval: lower bound {lower.value} > upper bound {upper.value}",
                "ensure lower bound <= upper bound",
            )
        if lower.value == upper.value and (not lower.closed or not upper.closed):
            raise _fail(
                criterion,
                f"empty interval: lower and upper bounds coincide at {lower.value} with an open edge",
                "an open edge with equal bounds admits no values",
            )

    if lower is not None and not lower.closed and lower.value >= range_max_f:
        raise _fail(
            criterion,
            f"empty interval: gt {lower.value} excludes all of declared range [{_format_num(range_min_f)}, {_format_num(range_max_f)}]",
            f"threshold must be strictly less than range.max ({_format_num(range_max_f)}) for gt",
        )

    if upper is not None and not upper.closed and upper.value <= range_min_f:
        raise _fail(
            criterion,
            f"empty interval: lt {upper.value} excludes all of declared range [{_format_num(range_min_f)}, {_format_num(range_max_f)}]",
            f"threshold must be strictly greater than range.min ({_format_num(range_min_f)}) for lt",
        )

    interval = Interval(lower=lower, upper=upper)
    return Constraint(
        criterion=criterion,
        kind="numeric",
        admitted=frozenset(),
        confidence_floor=0.0,
        raw=dict(clause),
        interval=interval,
    )


def parse_constraint(criterion: str, clause: Any, definition: Mapping[str, Any]) -> Constraint:
    """
    Normalise one `allow_when` clause against its `evaluate` declaration.

    Raises
    ------
    GateSchemaError
        If the clause uses an operator or value the criterion does not define.
    """
    kind = definition.get("type")
    if kind == "bool":
        return _parse_bool(criterion, clause)
    if kind == "level":
        return _parse_level(criterion, clause, list(definition.get("levels", [])))
    if kind == "choice":
        return _parse_choice(criterion, clause, list(definition.get("options", [])))
    if kind == "numeric":
        return _parse_numeric(criterion, clause, definition)

    raise _fail(
        criterion,
        f"evaluate.{criterion} declares unsupported type {kind!r}",
        "declare the criterion as bool, level, choice or numeric (Proposal Appendix B.2)",
    )


def parse_allow_when(
    allow_when: Mapping[str, Any],
    evaluate: Mapping[str, Any],
    gate_label: str,
) -> dict[str, Constraint]:
    """
    Normalise every clause in an `allow_when` block.

    Every clause must name a criterion the merged `evaluate` block declares;
    a clause referring to nothing would otherwise silently never apply.
    """
    constraints: dict[str, Constraint] = {}
    for criterion, clause in allow_when.items():
        definition = evaluate.get(criterion)
        if definition is None:
            raise GateSchemaError(
                where=f"{gate_label} -> allow_when.{criterion}",
                why=(
                    f"no criterion named {criterion!r} is declared in evaluate; "
                    f"declared criteria are {sorted(evaluate)}"
                ),
                how=(
                    f"add evaluate.{criterion} with a type and instructions, "
                    f"or correct the clause name"
                ),
            )
        try:
            constraints[criterion] = parse_constraint(criterion, clause, definition)
        except GateSchemaError as exc:
            # parse_constraint knows the criterion but not which document it came
            # from; prepend the gate so the diagnostic names a file (FR-DX-04).
            raise GateSchemaError(
                where=f"{gate_label} -> {exc.where}",
                why=exc.why,
                how=exc.how,
            ) from exc
    return constraints
