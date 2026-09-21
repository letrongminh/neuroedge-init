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

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..errors import GateSchemaError

BOOL_OPERATORS = frozenset({"confidence_gte"})
LEVEL_OPERATORS = frozenset({"eq", "lte", "gte"})
CHOICE_OPERATORS = frozenset({"in", "not_in", "eq"})

_OPERATORS_BY_KIND = {
    "bool": BOOL_OPERATORS,
    "level": LEVEL_OPERATORS,
    "choice": CHOICE_OPERATORS,
}


@dataclass(frozen=True)
class Constraint:
    """
    One normalised `allow_when` clause.

    Attributes
    ----------
    criterion:
        The `evaluate` key this clause constrains.
    kind:
        The criterion's declared type: ``bool``, ``level`` or ``choice``.
    admitted:
        Outcome values that satisfy the clause. Booleans normalise to the
        strings ``"true"`` / ``"false"`` so every kind shares one comparison.
    confidence_floor:
        Minimum required confidence. ``0.0`` means unspecified. Only ``bool``
        criteria carry a floor (Appendix B.2).
    raw:
        The clause exactly as authored, for diagnostics.
    """

    criterion: str
    kind: str
    admitted: frozenset[str]
    confidence_floor: float
    raw: Any

    def describe(self) -> str:
        floor = f", confidence >= {self.confidence_floor}" if self.confidence_floor else ""
        return f"{{{', '.join(sorted(self.admitted))}}}{floor}"

    def is_at_least_as_strict_as(self, other: Constraint) -> bool:
        """
        True when this clause admits no more than ``other`` does.

        This is the decision procedure behind principle 2. Equality counts as
        tightening: restating a parent clause verbatim is always permitted.
        """
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

    raise _fail(
        criterion,
        f"evaluate.{criterion} declares unsupported type {kind!r}",
        "declare the criterion as bool, level or choice (Proposal Appendix B.2)",
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
