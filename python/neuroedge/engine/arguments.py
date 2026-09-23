"""
Argument limits in a gate — RFC-0005, decision Q-25.

A tool call from System 2 or an MCP client chooses its arguments as well as the
action. The gate says how far they may go:

    arguments:
      duration_s: { type: integer, minimum: 1, maximum: 60 }
      mode:       { type: string, enum: [eco, normal] }

Three things live here, all pure functions of the documents:

* `validate_limit` — a limit is coherent for its type (a bound on a number, a
  length on a string, enum values of the declared type, a non-empty range);
* `merge_arguments` — Appendix B.5 for arguments: a derived gate may only
  narrow what its base admits; a limit it does not restate is inherited, so
  omission can never remove one;
* `check` — the runtime test the Gate Engine runs **before** any fact is
  gathered: deterministic, no model, no budget.

A parameter the gate does not mention is limited only by the action's type
signature (`arguments_closed` is deliberately not in v1 — RFC-0005 §5).
"""

from __future__ import annotations

import functools
from collections.abc import Mapping
from typing import Any

from ..errors import GateInheritanceError, GateSchemaError

NUMERIC = ("integer", "number")
BOUNDS = ("minimum", "maximum")


def _is(kind: str, value: Any) -> bool:
    if kind == "boolean":
        return isinstance(value, bool)
    if isinstance(value, bool):  # bool is an int in Python; never a number here
        return False
    if kind == "integer":
        return isinstance(value, int) or (isinstance(value, float) and value.is_integer())
    if kind == "number":
        return isinstance(value, (int, float))
    return isinstance(value, str)


def validate_limit(name: str, limit: Mapping[str, Any], label: str) -> None:
    """A limit makes sense for its type; `GateSchemaError` naming the first problem."""
    where = f"{label} -> arguments.{name}"
    kind = limit["type"]
    if kind not in NUMERIC and any(key in limit for key in BOUNDS):
        raise GateSchemaError(
            where=where,
            why=f"minimum/maximum bound a number, but {name} is {kind}",
            how="declare type: integer or number, or drop the bound",
        )
    if kind != "string" and "max_length" in limit:
        raise GateSchemaError(
            where=where,
            why=f"max_length limits a string, but {name} is {kind}",
            how="declare type: string, or drop max_length",
        )
    for value in limit.get("enum", ()):
        if not _is(kind, value):
            raise GateSchemaError(
                where=where,
                why=f"enum value {value!r} is not a {kind}",
                how=f"list only {kind} values in arguments.{name}.enum",
            )
    low, high = limit.get("minimum"), limit.get("maximum")
    if low is not None and high is not None and low > high:
        raise GateSchemaError(
            where=where,
            why=f"the admitted range is empty (minimum {low} > maximum {high})",
            how="a gate that can never allow is a mistake; widen the range or drop the action",
        )
    if "enum" in limit and not limit["enum"]:
        raise GateSchemaError(where=where, why="enum admits nothing", how="list the values")


def _loosens(where: str, why: str, how: str) -> GateInheritanceError:
    return GateInheritanceError(where=where, why=why, how=how, principle=2)


def merge_arguments(
    inherited: Mapping[str, dict[str, Any]],
    child: Mapping[str, Any] | None,
    label: str,
) -> dict[str, dict[str, Any]]:
    """
    Principle 2 for arguments: every restated limit is at least as strict.

    Keys the child does not restate are inherited verbatim; the effective
    range of a restated bound is the one the child declares, which must lie
    inside the base's.
    """
    merged = {name: dict(limit) for name, limit in inherited.items()}
    for name, limit in (child or {}).items():
        base = merged.get(name)
        if base is None:
            validate_limit(name, limit, label)
            merged[name] = dict(limit)
            continue
        where = f"{label} -> arguments.{name}"
        loosens = functools.partial(_loosens, where)
        if limit["type"] != base["type"]:
            raise loosens(
                f"retypes an inherited argument: base declares {base['type']}, "
                f"this gate declares {limit['type']}",
                f"keep type: {base['type']}",
            )
        combined = dict(base)
        if "minimum" in limit:
            if "minimum" in base and limit["minimum"] < base["minimum"]:
                raise loosens(
                    f"minimum {limit['minimum']} loosens the inherited minimum {base['minimum']}",
                    f"declare minimum >= {base['minimum']}, or omit it to inherit",
                )
            combined["minimum"] = limit["minimum"]
        if "maximum" in limit:
            if "maximum" in base and limit["maximum"] > base["maximum"]:
                raise loosens(
                    f"maximum {limit['maximum']} loosens the inherited maximum {base['maximum']}",
                    f"declare maximum <= {base['maximum']}, or omit it to inherit",
                )
            combined["maximum"] = limit["maximum"]
        if "max_length" in limit:
            if "max_length" in base and limit["max_length"] > base["max_length"]:
                raise loosens(
                    f"max_length {limit['max_length']} loosens the inherited "
                    f"max_length {base['max_length']}",
                    f"declare max_length <= {base['max_length']}, or omit it to inherit",
                )
            combined["max_length"] = limit["max_length"]
        if "enum" in limit:
            extra = [v for v in limit["enum"] if "enum" in base and v not in base["enum"]]
            if extra:
                raise loosens(
                    f"enum admits {extra}, which the inherited enum {base['enum']} does not",
                    "list a subset of the inherited values, or omit enum to inherit",
                )
            combined["enum"] = list(limit["enum"])
        validate_limit(name, combined, label)
        merged[name] = combined
    return merged


def check(limits: list[Mapping[str, Any]], arguments: Mapping[str, Any]) -> tuple[str, str] | None:
    """
    The first argument outside its limit, as ``(name, why)``; None when all fit.

    `limits` is the tree form — ``[{"name": ..., "type": ..., ...}]`` in
    declaration order, root first, so the reported argument is stable. A
    limited argument that is absent or None is out of range: fail closed.
    """
    for limit in limits:
        name, kind = limit["name"], limit["type"]
        value = arguments.get(name)
        if value is None:
            return name, "no value"
        if not _is(kind, value):
            return name, f"{value!r} is not a {kind}"
        if "enum" in limit and value not in limit["enum"]:
            return name, f"{value!r} is not one of {limit['enum']}"
        if "minimum" in limit and value < limit["minimum"]:
            return name, f"{value!r} < minimum {limit['minimum']}"
        if "maximum" in limit and value > limit["maximum"]:
            return name, f"{value!r} > maximum {limit['maximum']}"
        if "max_length" in limit and len(value) > limit["max_length"]:
            return name, f"length {len(value)} > max_length {limit['max_length']}"
    return None


def schema_hint(limit: Mapping[str, Any]) -> dict[str, Any]:
    """The JSON Schema keywords a tool's `inputSchema` gains from a gate limit."""
    hint = {key: limit[key] for key in ("minimum", "maximum", "enum") if key in limit}
    if "max_length" in limit:
        hint["maxLength"] = limit["max_length"]
    return hint
