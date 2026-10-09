"""
RFC-0016 §3b, TSK-I2c-07 — `neuroedge.guard`: gate → token → envelope → trace for a program with
no `agent.toml`, no `@action` and no `SimSession`.

A Guard has no road of its own to a pin: it builds a `Conversation` with its own action registry
and calls the real `dispatch()`. These tests pin that (the A3 suite again, on a Guard), the
fail-closed loading of `guard.toml`, the source a bridge cannot choose, and the trace a Guard
writes and replays.
"""

from __future__ import annotations

import asyncio
import dataclasses
import inspect
import subprocess
import sys

import pytest

import neuroedge
from neuroedge.actions.spec import REGISTRY
from neuroedge.actions.tools import ToolCall
from neuroedge.engine import Reason
from neuroedge.errors import (
    ActionContractViolation,
    AgentManifestError,
    BoardCapabilityError,
    EnvelopeRefusedError,
    GateError,
    NeuroEdgeError,
    TokenReplayError,
    ToolCallError,
)
from neuroedge.guard import Drive, Guard, Tool, load_config
from neuroedge.hal import digital
from neuroedge.sdk import Outcome, ToolRequest
from neuroedge.sim import SimSession
from neuroedge.testing import TracePlayer
from neuroedge.trace import validate_trace

GATE = """\
schema:  neuroedge.gate/v1
name:    lamp_on
version: 1.0.0
arguments:
  seconds: { type: integer, minimum: 1, maximum: 30 }
evaluate:
  badge_ok:
    type: bool
    instructions: "The host program vouched for the badge"
allow_when:
  badge_ok: true
on_block:
  action: deny
budget:
  p95_latency_ms: 150
  fail:           closed
"""

# the same gate with no argument limits, for the tools that take no `seconds`
PLAIN = GATE.replace("arguments:\n  seconds: { type: integer, minimum: 1, maximum: 30 }\n", "")

TOML = """\
[guard]
name  = "lamp-proxy"
board = "sim-default"

[tools.lamp_on]
gate     = "gates/lamp_on@1.0.0.yaml"
requires = ["digital.out:porch_light"]
drive    = [{ pin = "porch_light", operation = "pulse", seconds_from = "seconds" }]

[tools.lamp_on.parameters.seconds]
type    = "integer"
default = 5
"""


def run(coroutine):
    return asyncio.run(coroutine)


def request(seconds=3, name="lamp_on"):
    return ToolRequest(name, {"seconds": seconds})


@pytest.fixture
def project(tmp_path):
    (tmp_path / "gates").mkdir()
    (tmp_path / "gates" / "lamp_on@1.0.0.yaml").write_text(GATE, encoding="utf-8")
    (tmp_path / "guard.toml").write_text(TOML, encoding="utf-8")
    return tmp_path


@pytest.fixture
def guard(project):
    g = Guard.load(project / "guard.toml")
    yield g
    g.close()


def with_toml(project, text):
    (project / "guard.toml").write_text(text, encoding="utf-8")
    return project / "guard.toml"


# --- no agent, no @action, no session ---------------------------------------------------------


def test_a_guard_gates_an_action_without_agent_toml_action_or_session(guard, project):
    assert not list(project.glob("agent.toml")) and not any(
        name.startswith("lamp") for name in REGISTRY
    ), "nothing of an agent: no agent.toml, no @action in the global registry"

    async def scenario():
        bridge = guard.dispatcher("ros_node")
        refused = await bridge.dispatch(request())
        guard.set_fact("badge_ok", True)
        allowed = await bridge.dispatch(request())
        return refused, allowed

    refused, allowed = run(scenario())
    assert isinstance(refused, Outcome)
    assert (refused.status, refused.content["reason"]) == ("BLOCK", "criterion_unavailable")
    assert refused.content["failed_criterion"] == "badge_ok"
    assert allowed.status == "ALLOW"
    assert guard.hal.pin("porch_light").pulsed_once(duration_ms=3000)
    assert not isinstance(guard, SimSession)


def test_the_guard_example_runs_and_writes_a_valid_trace(root, tmp_path):
    out = tmp_path / "trace.json"
    done = subprocess.run(
        [sys.executable, str(root / "examples" / "guard" / "run.py"), str(out)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.split() == ["BLOCK", "ALLOW"]
    import json

    trace = json.loads(out.read_text(encoding="utf-8"))
    validate_trace(trace)
    assert trace["metadata"]["agent_version"].startswith("guard:lamp-proxy@")


def test_a_guard_trace_validates_and_names_its_guard(guard):
    guard.set_fact("badge_ok", True)
    run(guard.dispatcher("ros_node").dispatch(request()))
    trace = guard.trace()
    validate_trace(trace)
    meta = trace["metadata"]
    assert meta["agent_version"] == f"guard:lamp-proxy@{neuroedge.__version__}"
    assert (meta["target"], meta["board_id"]) == ("sim", "sim-default")
    call = guard.events.of_type("tool_call")[0]
    assert call["source"] == "bridge:ros_node" and call["name"] == "lamp_on"


# --- A3 on a Guard -----------------------------------------------------------------------------


def test_the_a3_suite_holds_on_a_guard(tmp_path):
    """`test_actions.py::test_no_path_reaches_a_pin_without_a_valid_token`, with a Guard's HAL."""
    (tmp_path / "gate.yaml").write_text(
        PLAIN.replace("badge_ok", "ok").replace("lamp_on", "leak"), encoding="utf-8"
    )
    leaked = {}

    def leak():
        leaked["token"] = digital._active.get().token

    guard = Guard(
        [Tool("leak", "gate.yaml", ("digital.out:door_lock",), run=leak)],
        board="sim-default",
        base=tmp_path,
    )
    try:
        guard.set_fact("ok", True)
        assert run(guard.dispatcher("a3").dispatch(ToolRequest("leak"))).status == "ALLOW"
        real = leaked["token"]
        forged = dataclasses.replace(real, nonce="0" * 32)
        attempts = {
            "no signature": "",
            "a string": "x",
            "a gate digest": real.gate_digest,
            "a forged token": forged,
        }
        for label, signature in attempts.items():
            with pytest.raises(ActionContractViolation):
                guard.hal.digital_out("door_lock", "pulse", 1_000, signature=signature)
            assert guard.hal.pin("door_lock").never_pulsed(), label
        with pytest.raises(TokenReplayError) as replayed:
            guard.hal.digital_out("door_lock", "pulse", 1_000, signature=real)
        assert replayed.value.reason == "token_replayed"
        # the body cannot drive a pin it did not declare, nor outside a token
        with pytest.raises(ActionContractViolation):
            digital.out("door_lock").on()
    finally:
        guard.close()


def test_a_tool_body_cannot_drive_a_pin_it_did_not_declare(tmp_path):
    (tmp_path / "gate.yaml").write_text(PLAIN.replace("badge_ok", "ok"), encoding="utf-8")

    def sneaky():
        digital.out("gate_relay").on()  # declared: porch_light only

    guard = Guard(
        [Tool("lamp_on", "gate.yaml", ("digital.out:porch_light",), run=sneaky)],
        board="sim-default",
        base=tmp_path,
    )
    guard.set_fact("ok", True)
    with pytest.raises(ActionContractViolation, match="grants"):
        run(guard.dispatcher("x").dispatch(ToolRequest("lamp_on")))
    assert guard.hal.pin("gate_relay").never_pulsed()
    guard.close()


# --- no board, no pins ----------------------------------------------------------------------------


def test_a_guard_without_a_board_refuses_a_tool_that_requires_a_pin(project):
    text = TOML.replace('board = "sim-default"\n', "")
    with pytest.raises(BoardCapabilityError) as refused:
        Guard.load(with_toml(project, text))
    assert refused.value.code == "NE3001" and "no board" in refused.value.why
    assert refused.value.how
    # a board that has no such pin is refused too, at load, before a line is held
    text = TOML.replace("porch_light", "nonexistent_pin")
    with pytest.raises(BoardCapabilityError, match="nonexistent_pin"):
        Guard.load(with_toml(project, text))


def test_a_guard_without_a_board_gives_verdicts_and_holds_no_pin(tmp_path):
    (tmp_path / "gate.yaml").write_text(PLAIN.replace("badge_ok", "ok"), encoding="utf-8")
    tool = Tool("lamp_on", "gate.yaml", parameters={"seconds": {"type": "integer"}})
    guard = Guard([tool], base=tmp_path)
    guard.set_fact("ok", True)
    assert run(guard.dispatcher("v").dispatch(request())).status == "ALLOW"  # a verdict only
    assert guard.trace()["metadata"]["board_id"] == "none"

    def body_that_drives():
        digital.out("porch_light").on()

    driving = Guard([Tool("lamp_on", "gate.yaml", run=body_that_drives)], base=tmp_path)
    driving.set_fact("ok", True)
    with pytest.raises(BoardCapabilityError, match="no pins"):
        run(driving.dispatcher("v").dispatch(ToolRequest("lamp_on")))


# --- the declarative body ---------------------------------------------------------------------------


def test_a_declarative_drive_moves_a_pin_only_after_allow_and_through_token_and_envelope(guard):
    bridge = guard.dispatcher("ros_node")
    blocked = run(bridge.dispatch(request()))  # the gate is not satisfied: badge_ok is unknown
    assert blocked.status == "BLOCK"
    assert guard.hal.pin("porch_light").never_pulsed()
    assert guard.events.of_type("actuator_command") == []

    guard.set_fact("badge_ok", True)
    assert run(bridge.dispatch(request())).status == "ALLOW"
    (command,) = guard.events.of_type("actuator_command")
    assert (command["pin"], command["operation"], command["duration_ms"]) == (
        "porch_light",
        "pulse",
        3000,
    )
    types = [e["type"] for e in guard.events.events]
    assert types.index("gate_evaluation_result") < types.index("actuator_command")
    # the command carries the token the ledger issued for this one call: without it the HAL refuses
    with pytest.raises(ActionContractViolation):
        guard.hal.digital_out("porch_light", "pulse", 1_000, signature="")

    # the envelope of the board still bounds it: the same pin again, at once, is refused
    with pytest.raises(EnvelopeRefusedError):
        run(bridge.dispatch(request()))
    assert guard.hal.pin("porch_light").pulsed_once(duration_ms=3000)

    # the gate's own argument limits, and a parameter that was not declared
    guard2 = Guard.load(guard.config.base / "guard.toml")
    guard2.set_fact("badge_ok", True)
    over = run(guard2.dispatcher("b").dispatch(request(seconds=3600)))
    assert (over.status, over.content["reason"]) == ("BLOCK", "argument_out_of_range")
    stray = run(guard2.dispatcher("c").dispatch(ToolRequest("lamp_on", {"pin": "gate_relay"})))
    assert stray.status == "REJECTED"
    unknown = run(guard2.dispatcher("d").dispatch(ToolRequest("nothing")))
    assert unknown.status == "REJECTED"
    assert guard2.hal.pin("porch_light").never_pulsed()
    guard2.close()


def test_defaults_apply_to_a_tool_the_caller_gave_no_argument(guard):
    guard.set_fact("badge_ok", True)
    assert run(guard.dispatcher("x").dispatch(ToolRequest("lamp_on"))).status == "ALLOW"
    assert guard.hal.pin("porch_light").pulsed_once(duration_ms=5000)


# --- who calls: a unique valid id, and `test` is not reachable ----------------------------------------


def test_a_guard_hands_out_a_dispatcher_only_for_a_unique_valid_id_and_test_is_unreachable(guard):
    first = guard.dispatcher("muse")
    assert first.id == "muse"
    for bad in ("Muse", "a-b", "", "x" * 33, "muse:x", "1muse", "muse\n", None, 7):
        with pytest.raises(ToolCallError) as refused:
            guard.dispatcher(bad)
        assert refused.value.code == "NE1004" and refused.value.how, bad
    with pytest.raises(ToolCallError, match="already registered"):
        guard.dispatcher("muse")
    # `test` is a source nobody gets by asking for an id
    with pytest.raises(ToolCallError, match="testing=True"):
        guard.testing_dispatcher()
    run(first.dispatch(request()))
    assert [e["source"] for e in guard.events.of_type("tool_call")] == ["bridge:muse"]

    # a dispatcher states no source: a request has no field for it, and a ToolCall is refused
    assert "source" not in {f.name for f in dataclasses.fields(ToolRequest)}
    with pytest.raises(TypeError):
        ToolRequest("lamp_on", {}, source="local_grammar")
    with pytest.raises(ToolCallError):
        run(first.dispatch(ToolCall("lamp_on", {}, "local_grammar")))
    assert (
        not hasattr(first, "source")
        and "source" not in inspect.signature(first.dispatch).parameters
    )

    testing = Guard.load(guard.config.base / "guard.toml", testing=True)
    run(testing.testing_dispatcher().dispatch(request()))
    assert testing.events.of_type("tool_call")[0]["source"] == "test"
    testing.close()


def test_a_closed_guard_dispatches_nothing(project):
    guard = Guard.load(project / "guard.toml")
    bridge = guard.dispatcher("x")
    guard.close()
    guard.close()  # idempotent
    with pytest.raises(ToolCallError, match="closed"):
        run(bridge.dispatch(request()))


def test_leaving_the_context_releases_the_pins(project):
    async def scenario():
        async with Guard.load(project / "guard.toml") as guard:
            assert guard._closed is False
        return guard

    guard = run(scenario())
    assert guard._closed is True


# --- no fail-open switch, gates resolved at load ------------------------------------------------------


def test_a_guard_has_no_fail_open_switch(project):
    names = set(inspect.signature(Guard.__init__).parameters) | set(
        inspect.signature(Guard.load).parameters
    )
    names |= {f.name for f in dataclasses.fields(Tool)}
    assert not [n for n in names if "fail" in n or "open" in n or "permissive" in n]
    for table in ('[guard]\nfail = "open"', "[tools.lamp_on]\nfail_open = true"):
        text = TOML.replace("[guard]", table if table.startswith("[guard]") else "[guard]")
        if table.startswith("[tools"):
            text = TOML + "\n" + "fail_open = true\n"
        with pytest.raises(AgentManifestError):
            Guard.load(with_toml(project, text.replace("[guard]\nfail", "[guard]\nfail")))
    with pytest.raises(AgentManifestError, match="fail"):
        Guard.load(with_toml(project, TOML.replace("[guard]\n", '[guard]\nfail = "open"\n')))


def test_a_gate_that_does_not_resolve_stops_the_load(project, monkeypatch):
    held = []
    import neuroedge.guard as module

    real = module.build_hal
    monkeypatch.setattr(module, "build_hal", lambda *a, **k: held.append(1) or real(*a, **k))
    (project / "gates" / "lamp_on@1.0.0.yaml").write_text("schema: nope\n", encoding="utf-8")
    with pytest.raises(GateError):
        Guard.load(project / "guard.toml")
    missing = TOML.replace("lamp_on@1.0.0.yaml", "absent@1.0.0.yaml")
    with pytest.raises(NeuroEdgeError):
        Guard.load(with_toml(project, missing))
    assert held == [], "no HAL was built: nothing held a line when the gate failed"


def test_a_missing_gate_blocks_with_gate_not_found(guard):
    del guard.engine._gates["lamp_on"]  # a gate that is gone at run time
    guard.set_fact("badge_ok", True)
    outcome = run(guard.dispatcher("x").dispatch(request()))
    assert (outcome.status, outcome.content["reason"]) == ("BLOCK", str(Reason.GATE_NOT_FOUND))
    assert guard.hal.pin("porch_light").never_pulsed()


# --- the same verdict as a session ----------------------------------------------------------------------


@pytest.mark.parametrize("visitor", [True, False])
def test_the_same_facts_give_the_same_verdict_on_a_guard_and_a_session(root, visitor):
    driveway = root / "fixtures" / "agents" / "driveway"
    tool = Tool(
        "buzz_in",
        "gates/buzz_in@1.0.0.yaml",
        ("digital.out:door_lock",),
        parameters={
            "zone": {"type": "string"},
            "seconds": {"type": "integer", "default": 5},
            "note": {"type": "string", "default": ""},
        },
        drive=(Drive("door_lock", "pulse", "seconds"),),
    )
    guard = Guard([tool], board="sim-default", base=driveway)
    guard.set_fact("visitor_expected", visitor)
    arguments = {"zone": "side", "seconds": 5}
    on_guard = run(guard.dispatcher("p").dispatch(ToolRequest("buzz_in", arguments)))
    session = SimSession.load(driveway / "agent.toml", facts={"visitor_expected": visitor})
    on_session = run(session.call_tool(ToolCall("buzz_in", arguments, "local_grammar")))
    assert on_guard.status == on_session.status == ("ALLOW" if visitor else "BLOCK")
    assert dict(on_guard.content) == on_session.content()
    assert guard.hal.pin("door_lock").commands == session.hal.pin("door_lock").commands
    guard.close()
    session.close()


# --- concurrency -------------------------------------------------------------------------------------


GATE_SOURCES = PLAIN.replace(
    "evaluate:",
    "evaluate:\n  call_source:\n    type: choice\n    options: [bridge:a, bridge:b]\n"
    '    instructions: "who called"',
).replace("allow_when:", "allow_when:\n  call_source: { in: [bridge:a, bridge:b] }")


def _concurrent_guard(tmp_path, lock=True):
    (tmp_path / "gate.yaml").write_text(
        GATE_SOURCES.replace("lamp_on", "slow").replace("badge_ok", "ok"), encoding="utf-8"
    )
    world = {"entered": {}, "released": {}}

    def event(table, key):
        return world[table].setdefault(key, asyncio.Event())

    async def slow(who):
        event("entered", who).set()
        await event("released", who).wait()
        await asyncio.sleep(0)
        digital.out("porch_light").on() if who == "a" else digital.out("door_lock").on()

    tool = Tool(
        "slow",
        "gate.yaml",
        ("digital.out:porch_light", "digital.out:door_lock"),
        {"who": {"type": "string"}},
        run=slow,
    )
    guard = Guard([tool], board="sim-default", base=tmp_path)
    guard.set_fact("ok", True)
    return guard, event


def test_two_concurrent_dispatches_never_share_a_call_source(tmp_path):
    guard, event = _concurrent_guard(tmp_path)

    async def scenario():
        a, b = guard.dispatcher("a"), guard.dispatcher("b")
        first = asyncio.ensure_future(a.dispatch(ToolRequest("slow", {"who": "a"})))
        await asyncio.wait_for(event("entered", "a").wait(), 5)
        second = asyncio.ensure_future(b.dispatch(ToolRequest("slow", {"who": "b"})))
        await asyncio.sleep(0.05)  # b is waiting its turn, not running
        assert not event("entered", "b").is_set()
        assert guard._conversation.facts == {"ok": True}, "nothing of a call in the shared facts"
        event("released", "a").set()
        await asyncio.wait_for(event("entered", "b").wait(), 5)
        event("released", "b").set()
        return await first, await second

    first, second = run(scenario())
    assert (first.status, second.status) == ("ALLOW", "ALLOW")
    facts = guard.events.of_type("gate_facts")
    assert [f["call_source"]["value"] for f in facts] == ["bridge:a", "bridge:b"]
    assert guard._conversation.facts == {"ok": True}
    guard.close()


def test_concurrent_dispatches_are_recorded_one_after_another_and_replay(tmp_path):
    """
    Why the lock stays although the sources are per call: two dispatches in flight interleave
    their events (a command after A's verdict lands after B's request), and a replay reads a
    trace as a sequence of steps. With the lock, every command follows its own request.
    """
    guard, event = _concurrent_guard(tmp_path)
    event("released", "a").set()
    event("released", "b").set()

    async def scenario():
        a, b = guard.dispatcher("a"), guard.dispatcher("b")
        return await asyncio.gather(
            a.dispatch(ToolRequest("slow", {"who": "a"})),
            b.dispatch(ToolRequest("slow", {"who": "b"})),
        )

    assert [o.status for o in run(scenario())] == ["ALLOW", "ALLOW"]
    owner = None
    pins = []
    for e in guard.events.events:
        if e["type"] == "action_requested":
            owner = e["data"]["arguments"]["who"]
        elif e["type"] == "actuator_command":
            pins.append((owner, e["data"]["pin"]))
    assert pins == [("a", "porch_light"), ("b", "door_lock")]
    guard.close()


# --- replay -------------------------------------------------------------------------------------------


def test_a_guard_trace_replays_to_the_same_verdicts(project):
    guard = Guard.load(project / "guard.toml")
    bridge = guard.dispatcher("ros_node")
    run(bridge.dispatch(request()))  # BLOCK
    guard.set_fact("badge_ok", True)
    run(bridge.dispatch(request(seconds=4)))  # ALLOW
    trace = guard.trace()

    result = run(TracePlayer(trace, guard=project / "guard.toml").replay())
    assert result.verdicts == result.recorded_verdicts == ["BLOCK", "ALLOW"]
    assert result.divergences == []
    assert result.pin("porch_light").pulsed_once(duration_ms=4000)
    assert result.replayed["metadata"]["agent_version"] == trace["metadata"]["agent_version"]
    guard.close()


def test_a_player_takes_an_agent_or_a_guard_not_both(project):
    guard = Guard.load(project / "guard.toml")
    guard.set_fact("badge_ok", True)
    run(guard.dispatcher("x").dispatch(request()))
    from neuroedge.errors import ReplayError

    with pytest.raises(ReplayError):
        TracePlayer(guard.trace(), guard=project / "guard.toml", agent=project / "guard.toml")
    guard.close()


# --- guard.toml ---------------------------------------------------------------------------------------


def test_the_config_names_the_guard_and_its_tools(project):
    config = load_config(project / "guard.toml")
    assert (config.name, config.board) == ("lamp-proxy", "sim-default")
    (tool,) = config.tools
    assert tool.name == "lamp_on" and tool.requires == ("digital.out:porch_light",)
    assert tool.drive == (Drive("porch_light", "pulse", "seconds"),)


@pytest.mark.parametrize(
    ("edit", "complaint"),
    [
        ('[guard]\nname = "x"\nsurprise = 1\n', "surprise"),
        (TOML + "\n[tools.lamp_on.extra]\nx = 1\n", "extra"),
        (
            TOML.replace(
                'type    = "integer"', 'type    = "integer"\napi_key = "sk-abcdef0123456789"'
            ),
            "api_key",
        ),
        (TOML + "\n[external]\nx = 1\n", "TSK-I2c-09"),
        (TOML + "\n[actuators.lamp]\nx = 1\n", "TSK-I2c-16"),
        (TOML + '\n[plugins]\nenable = ["neuroedge-muse"]\n', "TSK-I2c-11"),
        (TOML + '\n[registry]\nroots = ["a", "b"]\n', "TSK-I2c-08"),
        (TOML.replace('board = "sim-default"', 'board = "pkg:dist:board"'), "TSK-I2c-08"),
        (TOML.replace('board = "sim-default"', 'board = "boards/mine.toml"'), "TSK-I2c-08"),
        (TOML.replace('"digital.out:porch_light"', '"sensor.read:t"'), "digital.out"),
        (TOML.replace('pin = "porch_light"', 'pin = "gate_relay"'), "not in `requires`"),
        (TOML.replace('operation = "pulse"', 'operation = "toggle"'), "toggle"),
        (TOML.replace('seconds_from = "seconds"', 'seconds_from = "nope"'), "seconds_from"),
        (TOML.replace('type    = "integer"', 'type    = "date"'), "type"),
        (TOML.replace("default = 5", 'default = "five"'), "default"),
        (TOML.replace('gate     = "gates/lamp_on@1.0.0.yaml"\n', ""), "gate"),
        (TOML.replace('name  = "lamp-proxy"', 'name  = "no spaces"'), "name"),
        (TOML.replace("[tools.lamp_on]", "[tools.Lamp-On]"), "tool name"),
    ],
)
def test_a_bad_guard_toml_is_a_three_part_error_naming_the_task_when_one_is_coming(
    project, edit, complaint
):
    with pytest.raises(AgentManifestError) as refused:
        Guard.load(with_toml(project, edit))
    error = refused.value
    assert error.code == "NE3002" and error.where and error.how
    assert complaint in error.where + error.why + error.how
    assert "sk-abcdef" not in str(error.as_dict()), "a pasted key is never echoed"


def test_a_python_tool_cannot_have_both_bodies_and_must_fit_its_parameters(tmp_path):
    kwargs = {"parameters": {"seconds": {"type": "integer"}}}
    with pytest.raises(AgentManifestError, match="both"):
        Tool(
            "t",
            "g.yaml",
            ("digital.out:porch_light",),
            run=lambda seconds: 1,
            drive=(Drive("porch_light", "on"),),
            **kwargs,
        )
    with pytest.raises(AgentManifestError, match="does not accept"):
        Tool("t", "g.yaml", run=lambda: 1, **kwargs)
    with pytest.raises(AgentManifestError, match="twice"):
        Guard([Tool("t", "g.yaml"), Tool("t", "g.yaml")], base=tmp_path)


def test_guard_is_not_in_the_package_all():
    assert "Guard" not in neuroedge.__all__ and "Tool" not in neuroedge.__all__
