"""
The Gated Tool Profile corpus (TSK-S3-24, docs/spec/tool_calling.md §9).

A runtime is *NeuroEdge-gated* when every case of `fixtures/tool_calls/` gives
the result `expected_results.yaml` records for it. A case is one tool call and
the world it arrives in:

    agent:   home-voice                      # a directory of fixtures/agents/
    call:    { name: light_off, arguments: {}, source: mcp }
    facts:   { }                             # override [sim.facts] of the agent
    sensors: { motion: true }                # simulated readings, before the call

and its expectation — `status`, the verdict fields, the pin commands — lives in
`expected_results.yaml` under ``valid:`` or ``invalid:``, one entry per file and
one file per entry, like the gate corpus.

What `valid/` and `invalid/` mean, and how an expectation is compared, is
defined in §9 of the spec; the runner checks that split as well as each
expectation, so a case cannot sit in the wrong half.

Each case runs through the real `dispatch()` of a fresh `SimSession`, exactly
the road an MCP client or System 2 takes (`SimSession.call_tool`).
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from ..actions.tools import SOURCES, ToolCall, check_arguments
from ..errors import NeuroEdgeError
from ..paths import fixtures_dir

KINDS = ("valid", "invalid")
EXPECTED_FILE = "expected_results.yaml"
CASE_KEYS = {"agent", "call", "facts", "sensors"}
CALL_KEYS = {"name", "arguments", "source"}
# Verdict fields an expectation must state whenever the result carries them.
STRICT_FIELDS = ("reason", "failed_criterion", "on_block", "escalated_to")
# Compared only when the expectation states them: labels and wording may change.
OPTIONAL_FIELDS = ("gate", "message")
EXPECTED_KEYS = {
    "status",
    "pins",
    "problems",
    "confirmation",
    "fallback",
    *STRICT_FIELDS,
    *OPTIONAL_FIELDS,
}


def corpus_dir() -> Path:
    return fixtures_dir() / "tool_calls"


@dataclass(frozen=True)
class ToolCase:
    path: Path
    kind: str  # "valid" | "invalid"
    agent: str
    call: ToolCall
    facts: dict[str, Any] = field(default_factory=dict)
    sensors: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return f"{self.kind}/{self.path.name}"


@dataclass(frozen=True)
class CaseOutcome:
    case: ToolCase
    content: dict[str, Any]
    pins: list[dict[str, Any]]
    # The call matches the tool's advertised inputSchema, after §2 coercion.
    conforms: bool
    differences: list[str]

    @property
    def ok(self) -> bool:
        return not self.differences


def _corpus_error(where: Path | str, why: str, how: str) -> NeuroEdgeError:
    return NeuroEdgeError(where=str(where), why=why, how=how)


def _mapping(value: Any, where: str, what: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise _corpus_error(
            where, f"{what} must be a mapping, found {value!r}", f"write {what}: {{}}"
        )
    return dict(value)


def load_case(path: Path, kind: str) -> ToolCase:
    """One corpus file; `NeuroEdgeError` when it is not a well-formed case."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document = _mapping(document, str(path), "the case")
    unknown = set(document) - CASE_KEYS
    if unknown:
        raise _corpus_error(
            path, f"unknown keys {sorted(unknown)}", f"a case has only {sorted(CASE_KEYS)}"
        )
    agent = document.get("agent")
    if (
        not isinstance(agent, str)
        or not (fixtures_dir() / "agents" / agent / "agent.toml").is_file()
    ):
        raise _corpus_error(
            f"{path} -> agent",
            f"{agent!r} is not an agent of fixtures/agents/",
            "name a directory of fixtures/agents/ that holds an agent.toml",
        )
    call = _mapping(document.get("call"), f"{path} -> call", "call")
    if set(call) - CALL_KEYS or not isinstance(call.get("name"), str):
        raise _corpus_error(
            f"{path} -> call",
            f"a call is {{name, arguments, source}} with a string name, found {call!r}",
            "write call: { name: light_on, arguments: {}, source: mcp }",
        )
    source = call.get("source", "test")
    if source not in SOURCES:
        raise _corpus_error(
            f"{path} -> call.source",
            f"{source!r} is not a tool-call source",
            f"use one of {list(SOURCES)} — the runtime assigns it, as a connection would",
        )
    arguments = _mapping(call.get("arguments"), f"{path} -> call.arguments", "call.arguments")
    return ToolCase(
        path=path,
        kind=kind,
        agent=agent,
        call=ToolCall(call["name"], arguments, source),
        facts=_mapping(document.get("facts"), f"{path} -> facts", "facts"),
        sensors=_mapping(document.get("sensors"), f"{path} -> sensors", "sensors"),
    )


def load_expected(root: Path | None = None) -> dict[str, dict[str, Any]]:
    """`expected_results.yaml` as ``{"valid/<file>": expectation, …}``."""
    root = root or corpus_dir()
    document = _mapping(
        yaml.safe_load((root / EXPECTED_FILE).read_text(encoding="utf-8")),
        str(root / EXPECTED_FILE),
        "expected_results.yaml",
    )
    expected: dict[str, dict[str, Any]] = {}
    for kind, entries in document.items():
        if kind not in KINDS:
            raise _corpus_error(
                root / EXPECTED_FILE, f"unknown section {kind!r}", f"use only {list(KINDS)}"
            )
        for name, entry in _mapping(entries, f"{EXPECTED_FILE} -> {kind}", kind).items():
            where = f"{EXPECTED_FILE} -> {kind} -> {name}"
            entry = _mapping(entry, where, name)
            unknown = set(entry) - EXPECTED_KEYS
            if unknown or "status" not in entry:
                raise _corpus_error(
                    where,
                    f"an expectation needs `status` and has only {sorted(EXPECTED_KEYS)}; "
                    f"found {sorted(entry)}",
                    "fix the entry's keys",
                )
            expected[f"{kind}/{name}"] = entry
    return expected


def case_files(root: Path | None = None) -> list[tuple[str, Path]]:
    root = root or corpus_dir()
    return [(kind, path) for kind in KINDS for path in sorted((root / kind).glob("*.yaml"))]


def closure_problems(root: Path | None = None) -> list[str]:
    """Every file has an expectation and every expectation a file (§9)."""
    present = {f"{kind}/{path.name}" for kind, path in case_files(root)}
    documented = set(load_expected(root))
    problems = [
        f"{name}: no entry in {EXPECTED_FILE} — say what it proves"
        for name in sorted(present - documented)
    ]
    problems += [
        f"{name}: an entry in {EXPECTED_FILE} with no file" for name in sorted(documented - present)
    ]
    return problems


def _conforms(session: Any, call: ToolCall) -> bool:
    """The call as the tool's advertised `inputSchema` sees it, after §2 coercion."""
    spec = session.tools.specs.get(call.name)
    if spec is None:
        return False
    coerced, problems = check_arguments(spec, call.arguments)
    if problems:
        return False
    (schema,) = [tool["inputSchema"] for tool in session.tools.mcp() if tool["name"] == call.name]
    return jsonschema.Draft202012Validator(schema).is_valid(coerced)


def session_for(case: ToolCase) -> Any:
    """A fresh `SimSession` of the case's agent, with the case's facts and readings."""
    from ..sim import SimSession

    agent = fixtures_dir() / "agents" / case.agent / "agent.toml"
    session = SimSession.load(agent, facts=case.facts)
    for sensor, value in case.sensors.items():
        session.set_sensor(sensor, value)
    return session


async def execute(case: ToolCase) -> tuple[Any, Any]:
    """The case through `dispatch()`, as an MCP client or System 2 reaches it: `(session, ToolResult)`."""
    session = session_for(case)
    return session, await session.call_tool(case.call)


def _compare(label: str, expected: Mapping[str, Any], content: Mapping[str, Any]) -> list[str]:
    """Differences between one expectation and one result content (recursive for `fallback`)."""
    out: list[str] = []
    if content.get("status") != expected.get("status"):
        out.append(f"{label}status: expected {expected.get('status')}, got {content.get('status')}")
    if "tool" in expected and content.get("tool") != expected["tool"]:
        out.append(f"{label}tool: expected {expected['tool']!r}, got {content.get('tool')!r}")
    for key in STRICT_FIELDS:
        if content.get(key) != expected.get(key):
            out.append(f"{label}{key}: expected {expected.get(key)!r}, got {content.get(key)!r}")
    for key in OPTIONAL_FIELDS:
        if key in expected and content.get(key) != expected[key]:
            out.append(f"{label}{key}: expected {expected[key]!r}, got {content.get(key)!r}")
    problems = content.get("problems", [])
    wanted = expected.get("problems", [])
    if len(problems) != len(wanted) or any(
        w not in p for w, p in zip(wanted, problems, strict=False)
    ):
        out.append(f"{label}problems: expected substrings {wanted!r}, got {problems!r}")
    for key in ("confirmation", "fallback"):
        if (key in expected) != (key in content):
            state = "missing" if key in expected else "unexpected"
            out.append(f"{label}{key}: {state} (got {content.get(key)!r})")
    if "confirmation" in expected and "confirmation" in content:
        for key, value in expected["confirmation"].items():
            if content["confirmation"].get(key) != value:
                out.append(
                    f"{label}confirmation.{key}: expected {value!r}, "
                    f"got {content['confirmation'].get(key)!r}"
                )
    if "fallback" in expected and "fallback" in content:
        out += _compare(f"{label}fallback.", expected["fallback"], content["fallback"])
    return out


def compare(case: ToolCase, expected: Mapping[str, Any], outcome: tuple[Any, Any]) -> CaseOutcome:
    session, result = outcome
    content = result.content()
    pins = [
        {"pin": e["pin"], "operation": e["operation"], "duration_ms": e["duration_ms"]}
        for e in session.events.of_type("actuator_command")
    ]
    conforms = _conforms(session, case.call)
    differences = _compare("", expected, content)
    wanted_pins = [dict(p) for p in expected.get("pins") or []]
    if pins != wanted_pins:
        differences.append(f"pins: expected {wanted_pins}, got {pins}")
    if case.kind == "valid":
        if not conforms:
            differences.append("in valid/, but the call does not match the tool's inputSchema")
        if content["status"] == "REJECTED":
            differences.append("in valid/, but the call was REJECTED")
    else:
        if conforms:
            differences.append("in invalid/, but the call matches the tool's inputSchema")
        if content["status"] == "ALLOW":
            differences.append("in invalid/, but the call was ALLOWed")
    return CaseOutcome(case, content, pins, conforms, differences)


async def run_case(case: ToolCase, expected: Mapping[str, Any]) -> CaseOutcome:
    return compare(case, expected, await execute(case))


def run_corpus(root: Path | None = None) -> tuple[list[CaseOutcome], list[str]]:
    """Every case against its expectation, and the closure problems of the corpus."""
    expected = load_expected(root)
    outcomes = []
    for kind, path in case_files(root):
        case = load_case(path, kind)
        if case.name in expected:
            outcomes.append(asyncio.run(run_case(case, expected[case.name])))
    return outcomes, closure_problems(root)
