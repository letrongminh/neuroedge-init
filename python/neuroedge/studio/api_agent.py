"""`/api/agent`, `/api/gates…`, `/api/mcp` (docs/spec/studio.md §4). Slice S1a."""

from __future__ import annotations

import dataclasses
import os
from typing import Any

from ..actions.tools import source_channel
from ..engine.canonical import gate_digest
from ..engine.compiler import AgentManifest, load_agent_manifest, resolve_gates
from ..engine.decision_tree import compile_tree, walk
from ..engine.gate_explain import explain_gate_file, explain_gate_uri
from ..engine.gate_resolver import ResolvedGate
from ..engine.verdict import Fact, GateVerdict
from ..errors import NeuroEdgeError
from ..models.providers.config import load_system_one_config, load_system_two_config
from ..perception.providers.config import load_speech_configs, load_wake_word_config
from ..trace import json_safe

CALL_SOURCE = "call_source"
CALL_CHANNEL = "call_channel"
DEFAULT_CALL_SOURCE = "local_grammar"
DESKTOP_UI_PORT = 8765


# -- /api/agent ------------------------------------------------------------------------------


def _provider(role: str, label: str, key_env: str | None) -> dict[str, Any]:
    """One provider row: the variable's NAME and whether it is set — never its value."""
    return {
        "role": role,
        "label": label,
        "key_env": key_env,
        "key_present": bool(key_env and os.environ.get(key_env)),
    }


def _model_label(config: Any) -> str:
    if config.adapter is not None:
        return f"adapter {config.adapter}"
    where = f" at {config.api_base}" if config.api_base else ""
    return f"{config.model}{where}"


def _providers(manifest: AgentManifest) -> list[dict[str, Any]]:
    rows = []
    stt, tts = load_speech_configs(manifest)
    for role, config in (
        ("stt", stt),
        ("stt.fallback", None if stt is None else stt.fallback),
        ("tts", tts),
    ):
        if config is not None:
            rows.append(_provider(role, config.label, config.api_key_env))
    system_one = load_system_one_config(manifest)
    if system_one is not None:
        rows.append(_provider("system_one", _model_label(system_one), system_one.api_key_env))
    system_two = load_system_two_config(manifest)
    if system_two is not None:
        rows.append(_provider("system_two", _model_label(system_two), system_two.api_key_env))
    wake_word = load_wake_word_config(manifest)
    if wake_word is not None:
        rows.append(_provider("wake_word", wake_word.label, None))
    return rows


def agent(server: Any) -> dict[str, Any]:
    from ..templates import TEMPLATES

    manifest = load_agent_manifest(server.agent_path)
    with server.lock:
        board = server.session.hal.board
        board_row = {"id": board.id, "capabilities": board.capabilities}
    return json_safe(
        {
            "ok": True,
            "label": manifest.label,
            "root": str(manifest.root),
            "requires": manifest.requires,
            "targets": list(manifest.targets),
            "board": board_row,
            "providers": _providers(manifest),
            "templates": list(TEMPLATES),
        }
    )


# -- /api/gates ------------------------------------------------------------------------------


def _resolve(manifest: AgentManifest, key: str) -> ResolvedGate:
    """One gate of `[gates]`, resolved and compiled as the session does (`resolve_gates`)."""
    only = dataclasses.replace(manifest, gates={key: manifest.gates[key]})
    resolved, problems = resolve_gates(only)
    if problems:
        raise problems[0]
    return resolved[key]


def gates(server: Any) -> dict[str, Any]:
    manifest = load_agent_manifest(server.agent_path)
    rows = []
    for key, ref in manifest.gates.items():
        row: dict[str, Any] = {"name": key, "ref": ref}
        try:
            gate = _resolve(manifest, key)
        except NeuroEdgeError as error:
            rows.append(
                {
                    **row,
                    "version": None,
                    "digest": None,
                    "levels": None,
                    "fail": None,
                    "status": "FAIL",
                    "error": error.as_dict(),
                }
            )
            continue
        rows.append(
            {
                **row,
                "version": gate.version,
                "digest": gate_digest(gate),
                "levels": gate.inheritance_levels,
                "fail": gate.budget.get("fail", "closed"),
                "status": "OK",
            }
        )
    resolved = sum(1 for row in rows if row["status"] == "OK")
    return json_safe(
        {"ok": True, "gates": rows, "lint": {"resolved": resolved, "total": len(rows)}}
    )


def _find(manifest: AgentManifest, name: str) -> tuple[str, ResolvedGate]:
    """`name` is a key of `[gates]` or `name@version`; anything else is not found."""
    if name in manifest.gates:
        return name, _resolve(manifest, name)
    for key in manifest.gates:
        try:
            gate = _resolve(manifest, key)
        except NeuroEdgeError:
            continue
        if f"{gate.name}@{gate.version}" == name:
            return key, gate
    raise NeuroEdgeError(
        where=f"{manifest.source} -> [gates]",
        why=f"the agent has no gate {name!r}",
        how=f"use a key of [gates]: {sorted(manifest.gates)}",
    )


def _explanation(manifest: AgentManifest, key: str) -> dict[str, Any]:
    ref = manifest.gates[key]
    if ref.startswith("neuroedge://"):
        explained = explain_gate_uri(ref)
    else:
        explained = explain_gate_file(manifest.root / ref)
    return {
        "label": explained.label,
        "extends": explained.extends,
        "criteria": [dataclasses.asdict(item) for item in explained.criteria],
        "clauses": [dataclasses.asdict(item) for item in explained.clauses],
        "p95": explained.p95,
        "parent_p95": explained.parent_p95,
        "on_block_changed": explained.on_block_changed,
    }


def gate(server: Any, name: str) -> dict[str, Any]:
    manifest = load_agent_manifest(server.agent_path)
    key, resolved = _find(manifest, name)
    return json_safe(
        {
            "ok": True,
            "name": resolved.name,
            "version": resolved.version,
            "chain": list(resolved.chain),
            "evaluate": resolved.evaluate,
            "allow_when": resolved.allow_when,
            "on_block": resolved.on_block,
            "budget": resolved.budget,
            "explanation": _explanation(manifest, key),
        }
    )


def _fact(criterion: str, given: Any) -> Fact:
    """A fact from the request: a plain value, or `{"value": v, "confidence": c}`."""
    confidence = None
    if isinstance(given, dict):
        if not set(given) <= {"value", "confidence"} or "value" not in given:
            raise ValueError(
                f"fact {criterion!r}: an object needs `value` and may add `confidence`"
            )
        given, confidence = given["value"], given.get("confidence")
    if given is not None and not isinstance(given, str | int | float | bool):
        raise ValueError(f"fact {criterion!r} must be a boolean, a number or a string")
    if confidence is not None and (
        isinstance(confidence, bool) or not isinstance(confidence, int | float)
    ):
        raise ValueError(f"fact {criterion!r}: `confidence` must be a number")
    return Fact(given, confidence)


def whatif(server: Any, name: str, body: dict[str, Any]) -> dict[str, Any]:
    """The gate's verdict on the given facts alone: no session, HAL, ledger or event is touched."""
    given = body.get("facts")
    if not isinstance(given, dict):
        raise ValueError('the body must be {"facts": {criterion: value}}')
    manifest = load_agent_manifest(server.agent_path)
    _, resolved = _find(manifest, name)
    tree = compile_tree(resolved)
    # `call_source` may be stated for a gate that reads only `call_channel`: it is the caller
    # the channel is derived from (RFC-0017 §3d), never the channel itself.
    known = set(tree["criteria_order"])
    if CALL_CHANNEL in known:
        known.add(CALL_SOURCE)
    unknown = sorted(set(given) - known)
    if unknown:
        raise ValueError(
            f"{resolved.name} has no criterion {unknown}; it has {tree['criteria_order']}"
        )
    facts = {criterion: _fact(criterion, value) for criterion, value in given.items()}
    criteria = tree["criteria_order"]
    if CALL_SOURCE in criteria or CALL_CHANNEL in criteria:
        facts.setdefault(CALL_SOURCE, Fact(DEFAULT_CALL_SOURCE))
    # The dispatcher derives the channel from the source; a what-if never states it (RFC-0017 §3d).
    facts.pop(CALL_CHANNEL, None)
    channel = source_channel(facts[CALL_SOURCE].value) if CALL_SOURCE in facts else None
    if CALL_CHANNEL in criteria and channel is not None:
        facts[CALL_CHANNEL] = Fact(channel)
    if CALL_SOURCE not in criteria:
        facts.pop(CALL_SOURCE, None)
    walked = walk(tree, facts)
    answer: dict[str, Any] = {
        "ok": True,
        "verdict": str(walked.verdict),
        "evaluations": dict(walked.evaluations),
    }
    if walked.verdict is GateVerdict.BLOCK:
        answer["reason"] = str(walked.reason)
        answer["failed_criterion"] = walked.failed_criterion
        answer["action"] = resolved.on_block.get("action")
    return json_safe(answer)


# -- /api/mcp --------------------------------------------------------------------------------


def mcp(server: Any) -> dict[str, Any]:
    from ..mcp_desktop import desktop_config_text, desktop_entry

    manifest = load_agent_manifest(server.agent_path)
    with server.lock:
        tools = [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["inputSchema"],
            }
            for tool in server.session.tools.mcp()
        ]
        servers = [
            {"name": external.name, "tools": list(external.tools)}
            for external in server.session.mcp.servers
        ]
    # The tools are the session's own; only the Desktop entry needs the MCP SDK. Without
    # it the page still lists the tools and says why there is no Desktop config.
    config: str | None = None
    config_error: dict[str, Any] | None = None
    try:
        entry = desktop_entry(server.agent_path, ui=True, port=DESKTOP_UI_PORT)
        config = desktop_config_text(manifest.name, entry)
    except NeuroEdgeError as error:
        config_error = error.as_dict()
    reply: dict[str, Any] = {
        "ok": True,
        "tools": tools,
        "desktop_config": config,
        "servers": servers,
    }
    if config_error is not None:
        reply["desktop_config_error"] = config_error
    return json_safe(reply)
