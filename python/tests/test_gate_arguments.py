"""
RFC-0005 / Q-25 / TSK-S3-25 — argument limits live in the gate.

A tool call chooses its arguments. `unlock_door(duration_s=3600)` from a
prompt-injected System 2 is well typed, so the tool schema admits it; the gate
must be what says no. These tests pin that down end to end: resolution, the
compiled tree, the engine (before any fact is gathered), `c.do()` with defaults
applied, tool calls, the tool schema models see, `build`, and replay.
"""

from __future__ import annotations

import asyncio

import pytest

from neuroedge import action
from neuroedge.actions import Conversation
from neuroedge.actions.tools import ToolCall, ToolSet, dispatch, input_schema
from neuroedge.engine import ActionContractEngine, EventLog, resolve_gate_document
from neuroedge.engine.compiler import check_gate_arguments
from neuroedge.engine.decision_tree import compile_tree, validate_tree
from neuroedge.hal import digital
from neuroedge.hal.sim import SimHAL
from neuroedge.sim import SimSession
from neuroedge.testing import TracePlayer, assert_matches_golden
from neuroedge.testing.recorder import TraceRecorder
from neuroedge.trace import validate_trace

LIMITS = {
    "duration_s": {"type": "integer", "minimum": 1, "maximum": 60},
    "mode": {"type": "string", "enum": ["eco", "normal"]},
    "note": {"type": "string", "max_length": 8},
}


@action(name="t_arg_unlock", requires="digital.out:door_lock", gate="arg_unlock")
def arg_unlock(duration_s: int = 30, mode: str = "eco", note: str = "") -> None:
    """Pulse the door lock."""
    digital.out("door_lock").pulse(seconds=duration_s)


@action(name="t_arg_long", requires="digital.out:door_lock", gate="arg_short")
def arg_long(duration_s: int = 30) -> None:
    digital.out("door_lock").pulse(seconds=duration_s)


def gate(name: str, arguments=None, on_block=None):
    document = {
        "schema": "neuroedge.gate/v1",
        "name": name,
        "version": "1.0.0",
        "evaluate": {"ok": {"type": "bool", "instructions": "Precondition holds"}},
        "allow_when": {"ok": True},
        "on_block": on_block or {"action": "deny"},
        "budget": {"p95_latency_ms": 100},
    }
    if arguments is not None:
        document["arguments"] = arguments
    return resolve_gate_document(document)


class CountingSource:
    """A fact source that records every question it is asked."""

    def __init__(self) -> None:
        self.asked: list[str] = []

    async def adjudicate(self, criterion, definition, state, deadline_ms):
        from neuroedge.engine.verdict import Fact

        self.asked.append(criterion)
        return Fact(True)


def conversation(on_block=None):
    events = EventLog()
    source = CountingSource()
    engine = ActionContractEngine(events=events, facts_source=source)
    engine.register("arg_unlock", gate("arg_unlock", LIMITS, on_block))
    engine.register(
        "arg_short", gate("arg_short", {"duration_s": {"type": "integer", "maximum": 20}})
    )
    hal = SimHAL(events=events)
    return Conversation(engine=engine, hal=hal, facts={"ok": True}), hal, events, source


# --- resolution and the tree ------------------------------------------------------------


def test_a_gate_without_limits_keeps_its_artifact_and_tree_unchanged():
    plain = gate("plain")
    assert "arguments" not in plain.to_artifact()
    assert "arguments" not in compile_tree(plain)


def test_limits_compile_into_the_tree_before_the_nodes():
    tree = compile_tree(gate("arg_unlock", LIMITS))
    validate_tree(tree)
    assert [limit["name"] for limit in tree["arguments"]] == ["duration_s", "mode", "note"]
    assert tree["arguments"][0] == {"name": "duration_s", **LIMITS["duration_s"]}


def test_limits_change_the_digest():
    """The limits are policy, so they are covered by what gets hashed and signed."""
    assert compile_tree(gate("g"))["gate_digest"] != compile_tree(gate("g", LIMITS))["gate_digest"]


# --- the engine and c.do() ---------------------------------------------------------------------


async def test_a_call_in_range_runs():
    c, hal, _, _ = conversation()
    result = await c.do(arg_unlock, duration_s=10, mode="normal", note="ok")
    assert not result.blocked
    assert hal.pin("door_lock").pulsed_once(duration_ms=10_000)


async def test_an_hour_long_unlock_is_blocked_before_any_fact_is_asked():
    c, hal, events, source = conversation()
    result = await c.do(arg_unlock, duration_s=3600)
    assert result.blocked
    assert (result.gate.reason, result.gate.failed_criterion) == (
        "argument_out_of_range",
        "duration_s",
    )
    assert source.asked == []  # deterministic: no model, no budget
    assert hal.pin("door_lock").never_pulsed()
    assert events.of_type("argument_out_of_range") == [
        {"argument": "duration_s", "why": "3600 > maximum 60"}
    ]
    validate_trace(events.to_trace())


async def test_the_default_value_is_what_the_gate_checks():
    """`t_arg_long()` pulses for its default 30 s; a 20 s limit must see that."""
    c, hal, _, _ = conversation()
    result = await c.do(arg_long)
    assert result.blocked and result.gate.failed_criterion == "duration_s"
    assert hal.pin("door_lock").never_pulsed()


@pytest.mark.parametrize(
    ("arguments", "argument", "why"),
    [
        ({"duration_s": 0}, "duration_s", "0 < minimum 1"),
        ({"duration_s": True}, "duration_s", "True is not a integer"),
        ({"mode": "boost"}, "mode", "'boost' is not one of ['eco', 'normal']"),
        ({"note": "much too long"}, "note", "length 13 > max_length 8"),
    ],
)
async def test_each_kind_of_limit_blocks(arguments, argument, why):
    c, _, events, _ = conversation()
    result = await c.do(arg_unlock, **arguments)
    assert result.blocked and result.gate.failed_criterion == argument
    assert events.of_type("argument_out_of_range")[0]["why"] == why


async def test_an_argument_block_goes_through_on_block_like_any_other():
    c, _, _, _ = conversation({"action": "ask", "message": "Mở lâu vậy thật chứ?"})
    result = await c.do(arg_unlock, duration_s=3600)
    assert (result.gate.on_block_action, result.gate.message) == ("ask", "Mở lâu vậy thật chứ?")


# --- tool calls and the schema models see --------------------------------------------------------


async def test_a_system_two_tool_call_with_a_dangerous_argument_is_blocked_by_the_gate():
    c, hal, _, _ = conversation()
    tools = ToolSet([arg_unlock.__neuroedge_action__], {"t_arg_unlock": LIMITS})
    call = ToolCall("t_arg_unlock", {"duration_s": 3600}, source="system_two")
    result = await dispatch(c, tools, call)
    # Well typed, so the schema check passes; the gate refuses (not REJECTED).
    assert result.status == "BLOCK"
    assert result.content()["reason"] == "argument_out_of_range"
    assert result.content()["failed_criterion"] == "duration_s"
    assert hal.pin("door_lock").never_pulsed()


def test_the_tool_schema_shows_the_gates_limits():
    spec = arg_unlock.__neuroedge_action__
    properties = input_schema(spec, LIMITS)["properties"]
    assert properties["duration_s"] == {
        "type": "integer",
        "default": 30,
        "minimum": 1,
        "maximum": 60,
    }
    assert properties["mode"]["enum"] == ["eco", "normal"]
    assert properties["note"]["maxLength"] == 8
    assert "maximum" not in input_schema(spec)["properties"]["duration_s"]


# --- build ---------------------------------------------------------------------------------------


def test_build_refuses_a_limit_on_a_parameter_the_action_does_not_take():
    gates = {"arg_unlock": gate("arg_unlock", {"seconds": {"type": "integer", "maximum": 5}})}
    (problem,) = check_gate_arguments(gates, [arg_unlock.__neuroedge_action__])
    assert "has no parameter 'seconds'" in problem.why


def test_build_refuses_a_limit_whose_type_differs_from_the_signature():
    gates = {"arg_unlock": gate("arg_unlock", {"duration_s": {"type": "number", "maximum": 5}})}
    (problem,) = check_gate_arguments(gates, [arg_unlock.__neuroedge_action__])
    assert "declares it integer" in problem.why


# --- an agent on sim, recorded and replayed ------------------------------------------------------


AGENT = """[agent]
name    = "arg-door"
version = "0.1.0"

[requires]
"digital.out" = { pins = ["door_lock"] }

[gates]
open_door = "gates/open_door@1.0.0.yaml"

[targets]
supported = ["sim"]

[sim.facts]
guest_authenticated = true
"""

GATE = """schema:  neuroedge.gate/v1
name:    open_door
version: 1.0.0
arguments:
  duration_s: { type: integer, minimum: 1, maximum: 60 }
evaluate:
  guest_authenticated: { type: bool, instructions: "Guest is verified" }
allow_when:
  guest_authenticated: true
on_block: { action: deny }
budget: { p95_latency_ms: 150 }
"""

ACTION = '''from neuroedge import action
from neuroedge.hal import digital


@action(name="open_door", requires="digital.out:door_lock", gate="open_door")
def open_door(duration_s: int = 30) -> None:
    """Open the door for `duration_s` seconds."""
    digital.out("door_lock").pulse(seconds=duration_s)
'''

COMMANDS = """[grammar]
version = 1

[[command]]
intent   = "open_short"
patterns = ["mở cửa"]
tool     = "open_door"

[[command]]
intent       = "open_long"
patterns     = ["mở cửa cả ngày"]
tool         = "open_door"
default_args = { duration_s = 86400 }
"""


@pytest.fixture
def door_agent(tmp_path):
    from neuroedge.actions import spec

    saved = dict(spec.REGISTRY)
    spec.REGISTRY.pop("open_door", None)
    (tmp_path / "gates").mkdir()
    (tmp_path / "actions").mkdir()
    (tmp_path / "agent.toml").write_text(AGENT, encoding="utf-8")
    (tmp_path / "commands.toml").write_text(COMMANDS, encoding="utf-8")
    (tmp_path / "gates" / "open_door@1.0.0.yaml").write_text(GATE, encoding="utf-8")
    (tmp_path / "actions" / "door.py").write_text(ACTION, encoding="utf-8")
    yield tmp_path / "agent.toml"
    spec.REGISTRY.clear()
    spec.REGISTRY.update(saved)


def test_on_sim_the_gate_limits_what_the_grammar_asks_and_the_replay_agrees(door_agent):
    recorder = TraceRecorder()
    session = SimSession.load(door_agent, events=recorder)
    short = asyncio.run(session.handle("mở cửa"))
    long = asyncio.run(session.handle("mở cửa cả ngày"))
    assert short.allowed and not long.allowed
    assert long.result.gate.reason == "argument_out_of_range"
    assert session.hal.pin("door_lock").commands == [("pulse", 30_000)]
    # The tool schema the models see carries the limit.
    (tool,) = session.tools.mcp()
    assert tool["inputSchema"]["properties"]["duration_s"]["maximum"] == 60

    trace = recorder.to_trace()
    result = asyncio.run(TracePlayer(trace, agent=door_agent).replay())
    assert result.verdicts == ["ALLOW", "BLOCK"]
    assert_matches_golden(result, trace)


def test_gate_explain_shows_the_limits_and_what_the_child_narrowed(root):
    from typer.testing import CliRunner

    from neuroedge.cli.main import app

    fixtures = root / "fixtures" / "gates"
    result = CliRunner().invoke(
        app,
        [
            "gate",
            "explain",
            str(fixtures / "valid" / "narrows_arguments.yaml"),
            "--registry",
            str(fixtures / "registry"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Giới hạn tham số" in result.output
    assert "con đã thu hẹp so với cha" in result.output


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize(
    "limit",
    [
        {"minimum": 0, "maximum": 10},
        {"minimum": 0},  # a one-sided limit would admit +inf
        {"maximum": 10},  # … and -inf
        {"enum": [1.5, 2.5]},
    ],
)
def test_a_non_finite_number_argument_is_out_of_range(limit, value):
    # NaN compares False with every bound; a JSON tool call (MCP, System 2) can carry it.
    from neuroedge.engine.arguments import check

    assert check([{"name": "level", "type": "number", **limit}], {"level": value}) == (
        "level",
        f"{value!r} is not a finite number",
    )
