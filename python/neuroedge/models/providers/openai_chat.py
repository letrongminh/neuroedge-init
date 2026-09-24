"""
`state` ⇄ OpenAI chat completions (Q-12: the OpenAI API is the default contract).

`to_messages` turns what a session hands System 2 into OpenAI chat messages;
`from_response` turns a chat-completion response — a LiteLLM `ModelResponse`,
an OpenAI SDK object, or plain JSON — into the reply `parse_tool_calls`
reads. A custom adapter (FR-MDL-08) that talks to an OpenAI-shaped endpoint
can reuse both.

Nothing is guessed. Tool arguments that are not a JSON object are passed on
as the raw string, so dispatch rejects the call (`__unparseable__`) and no pin
moves (docs/spec/tool_calling.md §2).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from ...errors import PerceptionUnavailableError


def _json(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def _system(task: str, name: str | None, state: Mapping[str, Any]) -> str:
    parts: list[str] = []
    instructions = state.get("instructions")
    if instructions:
        parts.append(str(instructions))
    if task == "extract" and name:
        parts.append(f"Trích giá trị `{name}` từ lời người dùng; chỉ trả lời bằng giá trị đó.")
    context = state.get("context")
    if context:
        lines = [_json(entry) for entry in context]
        parts.append("Context:\n" + "\n".join(f"- {line}" for line in lines))
    return "\n\n".join(parts)


def _assistant(message: Mapping[str, Any]) -> dict[str, Any]:
    calls = [
        {
            "id": str(call.get("id") or ""),
            "type": "function",
            "function": {
                "name": str(call.get("name", "")),
                "arguments": _json(call.get("arguments", {})),
            },
        }
        for call in message.get("tool_calls") or ()
    ]
    out: dict[str, Any] = {"role": "assistant", "content": message.get("content") or None}
    if calls:
        out["tool_calls"] = calls
    return out


def _tool(message: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": str(message.get("tool_call_id") or ""),
        "content": _json(message.get("content", "")),
    }


def to_messages(task: str, name: str | None, state: Mapping[str, Any] | None) -> list[dict]:
    """
    System (instructions, and `context` for the knowledge task), the user's
    words, then the rounds of this turn: each assistant tool call with its
    arguments as a JSON string, each tool result as JSON text.
    """
    state = state or {}
    messages: list[dict[str, Any]] = []
    system = _system(task, name, state)
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": str(state.get("utterance") or "")})
    for message in state.get("messages") or ():
        role = message.get("role")
        if role == "assistant":
            messages.append(_assistant(message))
        elif role == "tool":
            messages.append(_tool(message))
        else:
            raise ValueError(f"unknown message role {role!r} in state['messages']")
    return messages


def tools_of(state: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """The OpenAI tool list of the turn; empty when there is none."""
    return list((state or {}).get("tools") or ())


# --- the response ---------------------------------------------------------------------------


def _get(obj: Any, key: str) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key)
    return getattr(obj, key, None)


def _arguments(raw: Any) -> Any:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, Mapping):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return raw  # passed on: dispatch rejects it
        return parsed if isinstance(parsed, dict) else raw
    return raw


class MalformedResponse(PerceptionUnavailableError):
    """The provider answered, but not with a chat completion."""


def from_response(response: Any, *, where: str = "SystemTwo") -> dict[str, Any]:
    """``{"text": str | None, "tool_calls": [{"id", "name", "arguments"}]}``."""
    choices = _get(response, "choices")
    if not isinstance(choices, Sequence) or isinstance(choices, str) or not choices:
        raise MalformedResponse(
            where=where,
            why="the model's response has no choices",
            how="check the model name and the provider's status; the reply was not used",
        )
    message = _get(choices[0], "message")
    if message is None:
        raise MalformedResponse(
            where=where,
            why="the model's first choice has no message",
            how="check the model name and the provider's status; the reply was not used",
        )
    content = _get(message, "content")
    if content is not None and not isinstance(content, str):
        raise MalformedResponse(
            where=where,
            why=f"the model's message content is {type(content).__name__}, not text",
            how="use a chat model; the reply was not used",
        )
    calls = []
    for raw in _get(message, "tool_calls") or ():
        function = _get(raw, "function") or {}
        calls.append(
            {
                "id": str(_get(raw, "id") or ""),
                "name": str(_get(function, "name") or ""),
                "arguments": _arguments(_get(function, "arguments")),
            }
        )
    # Some models open with blank lines or trail spaces; speech and the REPL get the text.
    text = content.strip() if content else ""
    return {"text": text or None, "tool_calls": calls}


def usage_of(response: Any) -> dict[str, Any]:
    usage = _get(response, "usage")
    out: dict[str, Any] = {}
    for key in ("prompt_tokens", "completion_tokens"):
        value = _get(usage, key) if usage is not None else None
        if isinstance(value, int) and not isinstance(value, bool):
            out[key] = value
    return out
