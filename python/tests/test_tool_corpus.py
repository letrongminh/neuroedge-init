"""
The Gated Tool Profile corpus (TSK-S3-24, docs/spec/tool_calling.md §9).

  * every case of fixtures/tool_calls/{valid,invalid}/ gives, through the real
    `dispatch()` of a `SimSession`, the result expected_results.yaml records;
  * every file has an entry and every entry a file;
  * every result matches the `outputSchema` each MCP tool declares (§4), and an
    MCP client gets exactly the same result over the protocol — the SDK checks
    the structured content of every non-error result against that schema.
"""

from __future__ import annotations

import asyncio
import json
import shutil

import anyio
import jsonschema
import pytest
from mcp import Client

from neuroedge.actions.tools import ToolCall, result_schema
from neuroedge.mcp_server import build_server
from neuroedge.testing.tool_corpus import (
    case_files,
    closure_problems,
    compare,
    corpus_dir,
    execute,
    load_case,
    load_expected,
    run_case,
    session_for,
)

CASES = [load_case(path, kind) for kind, path in case_files()]
IDS = [case.name for case in CASES]


@pytest.fixture(scope="module")
def expected():
    return load_expected()


def test_both_halves_of_the_corpus_exist():
    kinds = {case.kind for case in CASES}
    assert kinds == {"valid", "invalid"}, "the corpus needs calls that pass and calls that fail"


def test_every_case_has_an_expectation_and_every_expectation_a_case():
    assert closure_problems() == []


def test_closure_is_checked_both_ways(tmp_path):
    shutil.copytree(corpus_dir(), tmp_path / "corpus")
    (tmp_path / "corpus" / "valid" / "stray.yaml").write_text("agent: home-voice\n")
    (tmp_path / "corpus" / "invalid" / "unknown_tool.yaml").unlink()
    assert closure_problems(tmp_path / "corpus") == [
        "valid/stray.yaml: no entry in expected_results.yaml — say what it proves",
        "invalid/unknown_tool.yaml: an entry in expected_results.yaml with no file",
    ]


@pytest.mark.parametrize("case", CASES, ids=IDS)
async def test_case_gives_the_recorded_result(case, expected):
    outcome = await run_case(case, expected[case.name])
    assert outcome.differences == [], outcome.content


@pytest.mark.parametrize("case", CASES, ids=IDS)
async def test_result_matches_the_declared_output_schema(case):
    session, result = await execute(case)
    known = case.call.name in session.tools
    schema = result_schema(case.call.name if known else None)
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(result.content())


def test_the_runner_notices_a_wrong_expectation_and_a_case_in_the_wrong_half(expected):
    case = next(c for c in CASES if c.name == "valid/open_gate_mcp_degrades.yaml")
    ran = asyncio.run(execute(case))
    wrong = {**expected[case.name], "fallback": {"tool": "porch_light_on", "status": "BLOCK"}}
    assert compare(case, wrong, ran).differences == ["fallback.status: expected BLOCK, got ALLOW"]
    no_pins = {**expected[case.name], "pins": []}
    assert any(d.startswith("pins:") for d in compare(case, no_pins, ran).differences)
    misplaced = load_case(case.path, "invalid")
    assert "in invalid/, but the call matches the tool's inputSchema" in (
        compare(misplaced, expected[case.name], ran).differences
    )


def test_a_result_field_the_expectation_omits_is_a_difference(expected):
    case = next(c for c in CASES if c.name == "valid/unlock_door_escalates_on_risk.yaml")
    ran = asyncio.run(execute(case))
    silent = {k: v for k, v in expected[case.name].items() if k != "escalated_to"}
    assert compare(case, silent, ran).differences == [
        "escalated_to: expected None, got 'human_receptionist'"
    ]


# --- outputSchema over MCP ----------------------------------------------------------------------


def _over_mcp(case):
    """The case through an MCP client whose connection carries the case's source."""
    session = session_for(case)
    seen = {}

    async def main():
        async with Client(build_server(session, source=case.call.source)) as client:
            seen["tools"] = (await client.list_tools()).tools
            seen["result"] = await client.call_tool(case.call.name, dict(case.call.arguments))

    anyio.run(main)
    return seen["tools"], seen["result"]


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_an_mcp_client_gets_the_same_result_and_its_sdk_accepts_it(case):
    direct = asyncio.run(execute(case))[1].content()
    tools, result = _over_mcp(case)
    assert {tool.name: tool.output_schema for tool in tools} == {
        tool.name: result_schema(tool.name) for tool in tools
    }
    # Non-error results were already checked by the SDK client against the outputSchema.
    assert result.structured_content == direct
    assert json.loads(result.content[0].text) == direct
    assert result.is_error is (direct["status"] == "REJECTED")
    if result.is_error:
        # The SDK skips the check for an error result; the schema still covers it.
        name = case.call.name if case.call.name in {t.name for t in tools} else None
        jsonschema.Draft202012Validator(result_schema(name)).validate(result.structured_content)


def test_the_sdk_client_really_checks_the_output_schema(monkeypatch, root):
    """Guard for the test above: a result that breaks the declared schema is refused."""
    import neuroedge.actions.tools as tools
    from neuroedge.sim import SimSession

    strict = tools.result_schema
    monkeypatch.setattr(
        tools, "result_schema", lambda name=None: {**strict(name), "required": ["never_sent"]}
    )
    session = SimSession.load(root / "fixtures" / "agents" / "home-voice" / "agent.toml")

    async def main():
        async with Client(build_server(session)) as client:
            with pytest.raises(RuntimeError, match="Invalid structured content"):
                await client.call_tool("light_on", {})

    anyio.run(main)


def test_the_output_schema_refuses_what_the_profile_never_returns():
    validator = jsonschema.Draft202012Validator(result_schema("light_off"))
    assert not validator.is_valid({"tool": "light_on", "status": "ALLOW"})  # another tool
    assert not validator.is_valid({"tool": "light_off", "status": "BLOCK"})  # no gate, no on_block
    assert not validator.is_valid({"tool": "light_off", "status": "REJECTED"})  # no problems
    assert not validator.is_valid({"tool": "light_off", "status": "ALLOW", "token": "x"})
    assert not validator.is_valid(
        {
            "tool": "light_off",
            "status": "BLOCK",
            "gate": "light_off@1.0.0",
            "on_block": "degrade",
            "fallback": {"tool": "porch_light_on", "status": "REJECTED"},
        }
    )


def test_a_degrade_result_tells_the_caller_what_ran_instead(root):
    """ToolResult.content() carries the fallback's own verdict (§4)."""
    from neuroedge.sim import SimSession

    session = SimSession.load(root / "fixtures" / "agents" / "driveway" / "agent.toml")
    result = asyncio.run(session.call_tool(ToolCall("open_gate", {}, source="mcp")))
    assert result.action.fallback is not None
    assert result.content()["fallback"] == {"tool": "porch_light_on", "status": "ALLOW"}
    assert session.hal.pin("gate_relay").commands == []
    assert session.hal.pin("porch_light").commands == [("on", 0)]
