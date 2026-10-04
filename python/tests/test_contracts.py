"""
RFC-0015 §3a, §3b, §3e — the Gated Tool Profile schemas and the counter-example corpus
`fixtures/contracts/`.

`schemas/tool-call.v1.json` and `schemas/tool-result.v1.json` are what a client written in
another language reads instead of `actions/tools.py`. These tests tie the two together: the
dataclass, the enums and the keys the code emits against the files, and every case of
`fixtures/tool_calls/` (I6 exit criterion 8) against the schemas. A schema that validates proves
the *shape* only; conformance of a runtime is the corpus run through `dispatch()`.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from neuroedge.actions.tools import SOURCES, ToolCall, mcp_tool, result_schema
from neuroedge.engine.binary_tree import ACTIONS as ON_BLOCK_ACTIONS
from neuroedge.engine.verdict import GateVerdict, Reason
from neuroedge.errors import BuildFailed
from neuroedge.hal.board import REFERENCE_BOARDS
from neuroedge.paths import repo_root
from neuroedge.sim import SimSession
from neuroedge.testing.tool_corpus import CALL_KEYS, case_files, execute, load_case

ROOT = repo_root()
SCHEMAS = ROOT / "schemas"
CONTRACTS = ROOT / "fixtures" / "contracts"
CALL = json.loads((SCHEMAS / "tool-call.v1.json").read_text(encoding="utf-8"))
RESULT = json.loads((SCHEMAS / "tool-result.v1.json").read_text(encoding="utf-8"))
GATE = json.loads((SCHEMAS / "gate.v1.json").read_text(encoding="utf-8"))
CASES = [load_case(path, kind) for kind, path in case_files()]
IDS = [case.name for case in CASES]


def _validator(schema: dict, fragment: str | None = None) -> jsonschema.Draft202012Validator:
    if fragment is not None:
        schema = {
            "$schema": schema["$schema"],
            "$ref": f"#/$defs/{fragment}",
            "$defs": schema["$defs"],
        }
    return jsonschema.Draft202012Validator(schema)


CALL_V = _validator(CALL, "call")
REQUEST_V = _validator(CALL, "request")
TOOL_V = _validator(CALL, "tool")
RESULT_V = jsonschema.Draft202012Validator(RESULT)


# --- the envelope: schema and code agree ------------------------------------------------------


def test_the_tool_call_schema_and_the_dataclass_agree():
    fields = {f.name for f in dataclasses.fields(ToolCall)}
    defs = CALL["$defs"]
    assert set(defs["call"]["properties"]) == fields
    assert set(defs["request"]["properties"]) == fields - {"source"}
    assert set(defs["source"]["enum"]) == set(SOURCES) and len(defs["source"]["enum"]) == 5
    assert set(CALL_KEYS) == fields - {
        "id"
    }  # the corpus's call keys: no id, the runtime numbers it
    assert defs["call"]["required"] == defs["request"]["required"] == ["name"]
    assert defs["call"]["additionalProperties"] is False
    assert defs["request"]["additionalProperties"] is False


def test_a_request_that_states_a_source_is_refused_at_the_envelope():
    assert REQUEST_V.is_valid({"name": "a"})
    assert not REQUEST_V.is_valid({"name": "a", "source": "mcp"})
    assert CALL_V.is_valid({"name": "a", "source": "mcp"})


def test_the_envelope_is_closed_and_the_result_is_open():
    """RFC-0015 §3b: strict with what we accept, wide with what a client must accept."""
    assert not CALL_V.is_valid({"name": "a", "extra": 1})
    assert RESULT_V.is_valid({"tool": "a", "status": "ALLOW", "extra": 1})
    assert RESULT["additionalProperties"] is True
    for name in ("fallback", "confirmation"):
        assert RESULT["$defs"][name]["additionalProperties"] is True


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_every_tool_call_corpus_case_validates_against_the_tool_call_schema(case):
    """I6 exit criterion 8: the call of every case of `fixtures/tool_calls/` is an envelope."""
    document = {
        "name": case.call.name,
        "arguments": case.call.arguments,
        "source": case.call.source,
    }
    CALL_V.validate(document)
    # as a caller sends it: the same, without the source the runtime assigns
    REQUEST_V.validate({k: v for k, v in document.items() if k != "source"})
    CALL_V.validate({**document, "id": ""})


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_every_tool_call_corpus_result_validates_against_the_tool_result_schema(case):
    session, result = asyncio.run(execute(case))
    RESULT_V.validate(result.content())


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_a_recorded_tool_call_event_validates_against_the_envelope_schema(case):
    """The `tool_call` event of the trace carries an envelope — without touching trace.v1."""
    session, _ = asyncio.run(execute(case))
    (event,) = session.events.of_type("tool_call")
    CALL_V.validate(event)


# --- the tool description (`tools/list`) ------------------------------------------------------

AGENTS = sorted((ROOT / "fixtures" / "agents").iterdir())


def _tools(agent: Path) -> list[dict]:
    """The agent's tools on the first reference board of `sim` that satisfies its `[requires]`."""
    for board in REFERENCE_BOARDS["sim"]:
        try:
            return SimSession.load(agent / "agent.toml", board_id=board).tools.mcp()
        except BuildFailed:
            continue
    raise AssertionError(f"{agent.name} builds on no reference board of `sim`")


@pytest.mark.parametrize("agent", AGENTS, ids=[a.name for a in AGENTS])
def test_the_published_output_schema_of_every_tool_is_the_frozen_result_schema_pinned_to_its_name(
    agent,
):
    tools = _tools(agent)
    assert tools, f"{agent.name} advertises no tool"
    frozen = json.loads((SCHEMAS / "tool-result.v1.json").read_text(encoding="utf-8"))
    del frozen["$id"], frozen["$schema"]
    for tool in tools:
        pinned = json.loads(json.dumps(frozen))
        pinned["properties"]["tool"]["const"] = tool["name"]
        assert tool["outputSchema"] == pinned, tool["name"]
        TOOL_V.validate(tool)  # name, description, inputSchema subset, outputSchema


def test_a_tool_description_that_breaks_the_inputschema_subset_is_refused():
    base = {
        "name": "t",
        "description": "d",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "outputSchema": {"type": "object"},
    }
    assert TOOL_V.is_valid(base)
    open_schema = {**base["inputSchema"], "additionalProperties": True}
    assert not TOOL_V.is_valid({**base, "inputSchema": open_schema})
    nested = {**base["inputSchema"], "properties": {"x": {"type": "object"}}}
    assert not TOOL_V.is_valid({**base, "inputSchema": nested})
    assert not TOOL_V.is_valid({**base, "description": ""})


def test_mcp_tool_emits_the_four_documented_fields(root):
    session = SimSession.load(root / "fixtures" / "agents" / "home-voice" / "agent.toml")
    (spec,) = [s for n, s in session.tools.specs.items() if n == "light_on"]
    assert set(mcp_tool(spec)) == set(CALL["$defs"]["tool"]["properties"])


# --- the result: schema and code agree --------------------------------------------------------


def test_the_known_reasons_of_the_schema_are_exactly_the_Reason_enum():
    known = RESULT["properties"]["reason"]["x-neuroedge-known"]
    assert len(known) == len(set(known))
    assert set(known) == {str(reason) for reason in Reason}
    pattern = RESULT["properties"]["reason"]["pattern"]
    import re

    assert all(re.match(pattern, value) for value in known)


def test_the_on_block_enum_is_the_gate_schemas():
    gate = GATE["properties"]["on_block"]["properties"]["action"]["enum"]
    assert RESULT["properties"]["on_block"]["enum"] == gate
    assert RESULT["$defs"]["fallback"]["properties"]["on_block"]["enum"] == gate
    assert set(gate) == set(ON_BLOCK_ACTIONS)


def test_the_status_enum_is_the_verdicts_and_rejected():
    assert RESULT["properties"]["status"]["enum"] == [*[str(v) for v in GateVerdict], "REJECTED"]
    assert RESULT["$defs"]["fallback"]["properties"]["status"]["enum"] == [
        str(v) for v in GateVerdict
    ]


def test_result_schema_is_the_static_file_pinned_and_without_its_identity():
    schema = result_schema("light_on")
    assert "$id" not in schema and "$schema" not in schema
    assert schema["properties"]["tool"] == {**RESULT["properties"]["tool"], "const": "light_on"}
    assert result_schema()["properties"]["tool"] == RESULT["properties"]["tool"]
    # a fresh copy each time: pinning one tool must not leak into the next call
    assert "const" not in result_schema()["properties"]["tool"]
    # the file itself is untouched by the pinning
    on_disk = json.loads((SCHEMAS / "tool-result.v1.json").read_text(encoding="utf-8"))
    assert on_disk == RESULT


def _declared_keys(schema: dict) -> set[str]:
    return set(schema["properties"])


def _undeclared(content: dict, schema: dict) -> list[str]:
    """Keys of `content`, recursively, that `schema` does not declare."""
    out = [k for k in content if k not in _declared_keys(schema)]
    for key in ("fallback", "confirmation"):
        if key in content:
            out += _undeclared(content[key], RESULT["$defs"][key])
    return out


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_the_mcp_server_emits_only_documented_result_keys(case):
    """The schema is open, so this is what stops the code adding a key without a decision."""
    session, result = asyncio.run(execute(case))
    assert _undeclared(result.content(), RESULT) == []


def test_every_known_reason_and_every_source_appears_in_a_valid_contract_example():
    """The coverage RFC-0015 §3e asks of `fixtures/contracts/`: no enum value is untried."""
    reasons, sources, statuses, on_blocks = set(), set(), set(), set()
    for path in (CONTRACTS / "tool-result" / "valid").glob("*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        node = doc
        while node:
            statuses.add(node["status"])
            reasons |= {node["reason"]} if "reason" in node else set()
            on_blocks |= {node["on_block"]} if "on_block" in node else set()
            node = node.get("fallback")
    for path in (CONTRACTS / "tool-call" / "valid").glob("call_source_*.json"):
        sources.add(json.loads(path.read_text(encoding="utf-8"))["source"])
    assert reasons >= {str(r) for r in Reason}
    assert sources == set(SOURCES)
    assert statuses == {"ALLOW", "BLOCK", "REJECTED"}
    assert on_blocks == set(ON_BLOCK_ACTIONS)


def test_the_corpus_of_tool_calls_covers_every_source():
    """RFC-0015 F2: `system_one` was the one source no case used."""
    assert {case.call.source for case in CASES} >= set(SOURCES) - {"test"}


# --- fixtures/contracts/ ---------------------------------------------------------------------------

EXPECTED = yaml.safe_load((CONTRACTS / "expected_errors.yaml").read_text(encoding="utf-8"))
SCHEMA_FILES = {
    "tool-call.v1.json": CALL,
    "tool-result.v1.json": RESULT,
    "error.v1.json": json.loads((SCHEMAS / "error.v1.json").read_text(encoding="utf-8")),
    "board.v1.json": json.loads((SCHEMAS / "board.v1.json").read_text(encoding="utf-8")),
}


def _contract_validator(against: str) -> jsonschema.Draft202012Validator:
    name, _, fragment = against.partition("#/$defs/")
    return _validator(SCHEMA_FILES[name], fragment or None)


def _contract_files(kind: str) -> set[str]:
    return {str(p.relative_to(CONTRACTS)) for p in CONTRACTS.glob(f"*/{kind}/*.json")}


def test_every_contract_example_has_an_expectation_and_every_expectation_an_example():
    """Closed both ways (CONTRIBUTING.md §3)."""
    assert set(EXPECTED) == {"valid", "invalid"}
    for kind in ("valid", "invalid"):
        assert set(EXPECTED[kind]) == _contract_files(kind), kind
    assert _contract_files("valid") and _contract_files("invalid")


@pytest.mark.parametrize("name", sorted(EXPECTED["valid"]))
def test_a_valid_contract_example_validates(name):
    document = json.loads((CONTRACTS / name).read_text(encoding="utf-8"))
    _contract_validator(EXPECTED["valid"][name]["against"]).validate(document)


@pytest.mark.parametrize("name", sorted(EXPECTED["invalid"]))
def test_an_invalid_contract_example_fails_the_way_its_expectation_says(name):
    entry = EXPECTED["invalid"][name]
    document = json.loads((CONTRACTS / name).read_text(encoding="utf-8"))
    errors = list(_contract_validator(entry["against"]).iter_errors(document))
    assert errors, f"{name} is valid, but sits in invalid/"
    wanted = entry["error"]
    found = [(e.validator, "/".join(str(x) for x in e.absolute_path), e.message) for e in errors]
    assert any(
        keyword == wanted["keyword"]
        and path == wanted["path"]
        and wanted["message_contains"] in msg
        for keyword, path, msg in found
    ), f"{name}: wanted {wanted}, got {found}"


def test_a_contract_example_in_the_wrong_half_is_noticed():
    """The runner above is not vacuous: a valid example fails as an invalid one, and conversely."""
    valid = json.loads((CONTRACTS / "tool-result" / "valid" / "allow.json").read_text("utf-8"))
    assert list(RESULT_V.iter_errors(valid)) == []
    invalid = json.loads(
        (CONTRACTS / "tool-result" / "invalid" / "block_without_gate.json").read_text("utf-8")
    )
    assert list(RESULT_V.iter_errors(invalid)) != []


def test_every_error_code_of_the_catalog_has_a_valid_error_example():
    catalog = json.loads((SCHEMAS / "error-codes.v1.json").read_text(encoding="utf-8"))
    seen = {
        json.loads(p.read_text(encoding="utf-8"))["code"]
        for p in (CONTRACTS / "error" / "valid").glob("*.json")
    }
    assert seen == {entry["code"] for entry in catalog["codes"]}
