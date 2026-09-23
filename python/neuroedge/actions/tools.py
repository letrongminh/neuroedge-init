"""
Actions as tools: one path from any model to the physical world (Q-24).

Every `@action` is a **tool**. Whoever wants something done — System 2 (an LLM
with function calling), System 1, an external MCP client, or the offline
command grammar — produces the same `ToolCall`:

    {"name": "light_off", "arguments": {}, "source": "system_two"}

and `dispatch()` is the only way it reaches hardware:

    ToolCall ─► arguments checked against the tool schema ─► c.do() ─► gate ─► token ─► HAL

Sources: ``local_grammar`` (the fixed-command grammar — also what runs offline,
Q-14), ``system_one``, ``system_two``, ``mcp``, ``test``.

A tool call is an *intention*, never a permission. Arguments a model invents
are checked against the schema derived from the action's signature before
the gate sees them; a call that fails the check is rejected and moves
nothing. The dispatcher also puts the trusted fact ``call_source`` into the
gate's context, so a gate can say which sources may trigger an action
(``call_source: { in: [local_grammar] }``) — a model cannot claim it.

Schemas come in the two shapes models speak: MCP (`inputSchema`) and OpenAI
function calling (Q-12).
"""

from __future__ import annotations

import inspect
import json
import typing
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from .conversation import ActionResult, Conversation
from .spec import ActionSpec

SOURCES = ("local_grammar", "system_one", "system_two", "mcp", "test")
CALL_SOURCE_FACT = "call_source"
_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean"}


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    source: str = "test"
    # Empty: the dispatcher numbers it per session (call_1, call_2…), so two runs
    # of the same session record the same trace. Models and MCP clients send theirs.
    id: str = ""

    def __post_init__(self) -> None:
        if self.source not in SOURCES:
            raise ValueError(f"unknown tool-call source {self.source!r}; one of {SOURCES}")


# --- schemas ------------------------------------------------------------------------------


def _description(spec: ActionSpec) -> str:
    doc = inspect.getdoc(spec.fn) or spec.name.replace("_", " ")
    first = doc.strip().split("\n\n", 1)[0].replace("\n", " ")
    # The model is told the truth: calling is asking, and the gate may refuse.
    return f"{first} (Guarded by gate `{spec.gate}`: the call may be blocked.)"


def input_schema(spec: ActionSpec) -> dict[str, Any]:
    """JSON Schema of the action's parameters, from its signature and type hints."""
    hints = typing.get_type_hints(spec.fn)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, parameter in inspect.signature(spec.fn).parameters.items():
        if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
            continue
        prop: dict[str, Any] = {}
        kind = _JSON_TYPES.get(hints.get(name))
        if kind is not None:
            prop["type"] = kind
        if parameter.default is parameter.empty:
            required.append(name)
        else:
            prop["default"] = parameter.default
        properties[name] = prop
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def mcp_tool(spec: ActionSpec) -> dict[str, Any]:
    return {"name": spec.name, "description": _description(spec), "inputSchema": input_schema(spec)}


def openai_tool(spec: ActionSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": _description(spec),
            "parameters": input_schema(spec),
        },
    }


def check_arguments(
    spec: ActionSpec, arguments: Mapping[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """
    Arguments coerced to the schema, and every problem with them.

    Strings are coerced where the schema says number or boolean — grammar slots
    are text — but nothing else is guessed: an unknown or missing argument, or
    a value of the wrong type, is a problem, and the call does not run.
    """
    schema = input_schema(spec)
    properties = schema["properties"]
    problems: list[str] = []
    coerced: dict[str, Any] = {}
    for key in sorted(set(arguments) - set(properties)):
        problems.append(f"unknown argument {key!r}; {spec.name} takes {sorted(properties)}")
    for key in schema.get("required", []):
        if key not in arguments:
            problems.append(f"missing required argument {key!r}")
    for key, value in arguments.items():
        if key not in properties:
            continue
        kind = properties[key].get("type")
        ok, value = _coerce(value, kind)
        if not ok:
            problems.append(f"argument {key!r} must be {kind}, got {value!r}")
        coerced[key] = value
    return coerced, problems


def _coerce(value: Any, kind: str | None) -> tuple[bool, Any]:
    if kind is None:
        return True, value
    if kind == "string":
        return isinstance(value, str), value
    if kind == "boolean":
        if isinstance(value, bool):
            return True, value
        if isinstance(value, str) and value.casefold() in ("true", "false"):
            return True, value.casefold() == "true"
        return False, value
    if isinstance(value, bool):  # bool is an int in Python; never a number here
        return False, value
    caster = int if kind == "integer" else float
    if isinstance(value, (int, float)) and (kind == "number" or float(value).is_integer()):
        return True, caster(value)
    if isinstance(value, str):
        try:
            return True, caster(value)
        except ValueError:
            return False, value
    return False, value


# --- the tool set of an agent -------------------------------------------------------------


class ToolSet:
    """The agent's @actions, exposed as tools. Nothing outside it can be called."""

    def __init__(self, specs: Iterable[ActionSpec]) -> None:
        self.specs = {spec.name: spec for spec in specs}

    def __contains__(self, name: str) -> bool:
        return name in self.specs

    def mcp(self) -> list[dict[str, Any]]:
        return [mcp_tool(spec) for spec in self.specs.values()]

    def openai(self) -> list[dict[str, Any]]:
        return [openai_tool(spec) for spec in self.specs.values()]


def parse_tool_calls(payload: Any, source: str) -> tuple[str | None, list[ToolCall]]:
    """
    Text and tool calls from a model reply. Accepts plain text, or a mapping
    with ``text`` / ``content`` and ``tool_calls`` in either the flat shape
    ``{"name", "arguments"}`` or the OpenAI shape
    ``{"function": {"name", "arguments": "<json>"}}``.
    """
    if isinstance(payload, str):
        return payload, []
    if not isinstance(payload, Mapping):
        return str(payload), []
    text = payload.get("text", payload.get("content"))
    calls: list[ToolCall] = []
    for raw in payload.get("tool_calls") or []:
        function = raw.get("function", raw)
        arguments = function.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments or "{}")
            except json.JSONDecodeError:
                arguments = {"__unparseable__": arguments}
        if not isinstance(arguments, dict):
            arguments = {"__unparseable__": arguments}
        call_id = str(raw.get("id") or "")
        calls.append(ToolCall(str(function.get("name", "")), arguments, source, call_id))
    return (str(text) if text is not None else None), calls


# --- dispatch -------------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolResult:
    call: ToolCall
    status: str  # "ALLOW" | "BLOCK" | "REJECTED"
    action: ActionResult | None = None
    problems: tuple[str, ...] = ()

    @property
    def allowed(self) -> bool:
        return self.status == "ALLOW"

    def content(self) -> dict[str, Any]:
        """What the caller (an LLM, an MCP client) is told back."""
        out: dict[str, Any] = {"tool": self.call.name, "status": self.status}
        if self.problems:
            out["problems"] = list(self.problems)
        gate = self.action.gate if self.action is not None else None
        if gate is not None and self.status == "BLOCK":
            out.update(
                {
                    k: v
                    for k, v in {
                        "gate": gate.gate,
                        "reason": str(gate.reason) if gate.reason else None,
                        "failed_criterion": gate.failed_criterion,
                        "on_block": gate.on_block_action,
                        "message": gate.message,
                        "escalated_to": gate.escalated_to,
                    }.items()
                    if v is not None
                }
            )
        return out


async def dispatch(conversation: Conversation, tools: ToolSet, call: ToolCall) -> ToolResult:
    """The only road from a tool call to a pin: check, then `c.do()` through the gate."""
    events = conversation.events
    if not call.id:
        count = getattr(conversation, "_tool_calls", 0) + 1
        conversation._tool_calls = count
        call = ToolCall(call.name, dict(call.arguments), call.source, f"call_{count}")
    events.emit(
        "tool_call",
        {
            "id": call.id,
            "name": call.name,
            "arguments": dict(call.arguments),
            "source": call.source,
        },
    )
    spec = tools.specs.get(call.name)
    if spec is None:
        problems = [f"no tool named {call.name!r}; the agent has {sorted(tools.specs)}"]
        arguments: dict[str, Any] = {}
    else:
        arguments, problems = check_arguments(spec, call.arguments)
    if problems:
        events.emit("tool_call_rejected", {"id": call.id, "name": call.name, "problems": problems})
        return ToolResult(call, "REJECTED", problems=tuple(problems))
    # The dispatcher, not the model, says where the call came from.
    facts = dict(conversation.facts)
    conversation.facts = {**facts, CALL_SOURCE_FACT: call.source}
    try:
        result = await conversation.do(spec, **arguments)
    finally:
        conversation.facts = facts
    return ToolResult(call, "BLOCK" if result.blocked else "ALLOW", action=result)
