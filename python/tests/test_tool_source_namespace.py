"""
RFC-0017 §3a-§3e, TSK-I2c-10 (a) — `bridge:<id>` / `mcp:<client>` as the source of a tool call, and
the derived trusted fact `call_channel` (the family of `call_source`).

The gate sees the source as one string it lists in `options`; a source it does not list blocks with
`criterion_unavailable`, even under `fail: open`. `call_channel` is put in front of the gate at the
one point where each call's own facts are laid over the conversation's, last, so nothing else can
set it. Registration of the ids is what the bridge loader (TSK-I2c-11) and `[mcp.clients]` do; the
corpus runner stands in for them.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import pytest

from neuroedge import action
from neuroedge.actions import Conversation
from neuroedge.actions.confirmation import HUMAN_SOURCES
from neuroedge.actions.spec import spec_of
from neuroedge.actions.tools import (
    CALL_CHANNEL_FACT,
    CALL_SOURCE_FACT,
    SOURCES,
    ToolCall,
    ToolSet,
    dispatch,
    source_channel,
)
from neuroedge.engine import ActionContractEngine, EventLog, resolve_gate_document
from neuroedge.errors import ToolCallError
from neuroedge.hal.sim import SimHAL
from neuroedge.sim import SimSession
from neuroedge.testing import TracePlayer
from neuroedge.testing.recorder import TraceRecorder
from neuroedge.trace import validate_trace

FAMILIES = ["local_grammar", "system_one", "system_two", "mcp", "bridge", "test"]


@pytest.fixture(scope="module")
def lamp(root):
    return root / "fixtures" / "agents" / "bridge-lamp" / "agent.toml"


def lamp_session(lamp, source=None, **kwargs):
    session = SimSession.load(lamp, **kwargs)
    if source is not None and source not in SOURCES:
        session.conversation.register_source(source)
    return session


def call(tool, source):
    return ToolCall(tool, {}, source=source)


def gate_facts(session):
    return session.events.of_type("gate_facts")[-1]


def run(coroutine):
    return asyncio.run(coroutine)


# --- the gate meets the source as one string ---------------------------------------------------


def test_a_bridge_call_meets_the_gate_with_its_own_source(lamp):
    session = lamp_session(lamp, "bridge:muse")
    result = run(session.call_tool(call("lamp_on", "bridge:muse")))
    assert result.status == "ALLOW"
    assert gate_facts(session)[CALL_SOURCE_FACT]["value"] == "bridge:muse"
    assert session.hal.pin("porch_light").commands, "the lamp was switched"


def test_a_gate_that_lists_one_bridge_blocks_another(lamp):
    session = lamp_session(lamp, "bridge:other")
    result = run(session.call_tool(call("lamp_on", "bridge:other")))
    assert result.status == "BLOCK"
    assert result.content()["failed_criterion"] == "call_source"
    assert session.hal.pin("porch_light").never_pulsed()


@pytest.mark.parametrize("source", ["bridge:other", "mcp:hub"])
def test_a_source_outside_a_gates_options_blocks_with_criterion_unavailable(lamp, source):
    session = lamp_session(lamp, source)
    content = run(session.call_tool(call("lamp_on", source))).content()
    assert (content["status"], content["reason"]) == ("BLOCK", "criterion_unavailable")
    assert content["failed_criterion"] == "call_source"


def choice(**options):
    return {
        name: {"type": "choice", "options": values, "instructions": f"`{name}` as dispatched"}
        for name, values in options.items()
    }


class Clock:
    def __call__(self) -> float:
        return 0.0


def _rig(evaluate, allow_when, *, fail="closed", body=None, on_block=None):
    """One conversation, one action `ns_probe` behind a gate built from the arguments."""
    clock = Clock()
    events = EventLog(clock)
    engine = ActionContractEngine(clock=clock, events=events)
    engine.register(
        "ns_gate",
        resolve_gate_document(
            {
                "schema": "neuroedge.gate/v1",
                "name": "ns_gate",
                "version": "1.0.0",
                "evaluate": evaluate,
                "allow_when": allow_when,
                "on_block": on_block or {"action": "deny"},
                "budget": {"p95_latency_ms": 5000, "fail": fail},
            }
        ),
    )

    @action(name="ns_probe", requires="digital.out:porch_light", gate="ns_gate")
    def probe() -> None:
        """Probe action of the namespace tests."""

    conversation = Conversation(engine=engine, hal=SimHAL(events=events), **(body or {}))
    return conversation, ToolSet([spec_of(probe)]), events


@pytest.mark.parametrize("fail", ["closed", "open"])
def test_a_source_outside_a_gates_options_blocks_even_under_fail_open(fail):
    listed = ["local_grammar", "bridge:muse"]
    c, tools, _ = _rig(choice(call_source=listed), {"call_source": {"in": listed}}, fail=fail)
    c.register_source("bridge:other")
    result = run(dispatch(c, tools, call("ns_probe", "bridge:other")))
    assert result.status == "BLOCK"
    assert str(result.action.gate.reason) == "criterion_unavailable"
    assert result.action.gate.failed_criterion == "call_source"


# --- call_channel: derived, last, nobody else's to set ----------------------------------------


@pytest.mark.parametrize(
    ("source", "family"),
    [
        ("local_grammar", "local_grammar"),
        ("system_one", "system_one"),
        ("system_two", "system_two"),
        ("mcp", "mcp"),
        ("test", "test"),
        ("mcp:hub", "mcp"),
        ("bridge:muse", "bridge"),
        ("bridge:a_1", "bridge"),
    ],
)
def test_call_channel_is_the_family_of_call_source(source, family):
    assert source_channel(source) == family
    c, tools, events = _rig(choice(call_channel=FAMILIES), {"call_channel": {"in": [family]}})
    if source not in SOURCES:
        c.register_source(source)
    result = run(dispatch(c, tools, call("ns_probe", source)))
    assert result.status == "ALLOW"
    assert events.of_type("gate_facts")[-1][CALL_CHANNEL_FACT]["value"] == family


@pytest.mark.parametrize("source", [None, "mqtt:x", "bridge:", "bridge:muse\n", 7])
def test_there_is_no_channel_without_a_source(source):
    assert source_channel(source) is None


def test_call_channel_cannot_be_set_by_facts_sim_facts_or_a_fact_source(lamp):
    forged = "local_grammar"
    # c.facts and a fact source, on a conversation: the channel is the family of the source
    c, tools, events = _rig(
        choice(call_channel=FAMILIES),
        {"call_channel": {"in": ["local_grammar"]}},
        body={"facts": {CALL_CHANNEL_FACT: forged}},
    )
    c.fact_sources.append(lambda tree: {CALL_CHANNEL_FACT: forged})
    c.register_source("bridge:muse")
    result = run(dispatch(c, tools, call("ns_probe", "bridge:muse")))
    assert result.status == "BLOCK" and result.action.gate.failed_criterion == "call_channel"
    assert events.of_type("gate_facts")[-1][CALL_CHANNEL_FACT]["value"] == "bridge"
    assert c.facts == {CALL_CHANNEL_FACT: forged}, "nothing was written back"

    # no call_source (a plain `c.do()`): no channel to forge either — the gate cannot read it
    result = run(c.do(tools.specs["ns_probe"]))
    assert str(result.gate.reason) == "criterion_unavailable"

    # `[sim.facts]` of an agent: the same, through a whole session
    session = lamp_session(lamp, "mcp:hub", facts={CALL_CHANNEL_FACT: "bridge"})
    content = run(session.call_tool(call("lamp_off", "mcp:hub"))).content()
    assert (content["status"], content["failed_criterion"]) == ("BLOCK", "call_channel")
    assert gate_facts(session)[CALL_CHANNEL_FACT]["value"] == "mcp"


def test_the_confirmation_path_keeps_both_source_facts():
    evaluate = choice(
        call_source=["local_grammar", "bridge:muse", "test"], call_channel=FAMILIES
    ) | {"room_empty": {"type": "bool", "instructions": "Nobody is in the room"}}
    c, tools, events = _rig(
        evaluate,
        {
            "call_source": {"in": ["bridge:muse"]},
            "call_channel": {"in": ["bridge"]},
            "room_empty": True,
        },
        on_block={"action": "ask", "message": "Sure?", "confirms": ["room_empty"]},
        body={"facts": {"room_empty": False}},
    )
    c.register_source("bridge:muse")
    asked = run(dispatch(c, tools, call("ns_probe", "bridge:muse")))
    assert asked.status == "BLOCK" and asked.action.confirmation is not None
    # A person answers on the device; the gate is judged again as the call that asked.
    confirmed = run(c.confirm(asked.action.confirmation.id, "local_grammar"))
    assert not confirmed.blocked
    facts = events.of_type("gate_facts")[-1]
    assert facts[CALL_SOURCE_FACT]["value"] == "bridge:muse"
    assert facts[CALL_CHANNEL_FACT]["value"] == "bridge"


@dataclass
class World:
    entered: dict[str, asyncio.Event] = field(default_factory=dict)
    released: dict[str, asyncio.Event] = field(default_factory=dict)

    def event(self, table, name):
        return table.setdefault(name, asyncio.Event())


def test_two_concurrent_dispatches_each_see_their_own_call_channel():
    world = World()

    @action(name="ns_hold", requires="digital.out:porch_light", gate="ns_gate")
    async def hold(who: str = "") -> None:
        """Waits for the test, so two calls overlap on one conversation."""
        world.event(world.entered, who).set()
        await world.event(world.released, who).wait()

    c, _, events = _rig(
        choice(call_source=["bridge:muse", "mcp:hub"], call_channel=FAMILIES),
        {
            "call_source": {"in": ["bridge:muse", "mcp:hub"]},
            "call_channel": {"in": ["bridge", "mcp"]},
        },
    )
    tools = ToolSet([spec_of(hold)])
    for source in ("bridge:muse", "mcp:hub"):
        c.register_source(source)

    async def scenario():
        first = asyncio.ensure_future(
            dispatch(c, tools, ToolCall("ns_hold", {"who": "a"}, source="bridge:muse"))
        )
        await asyncio.wait_for(world.event(world.entered, "a").wait(), 5)
        second = asyncio.ensure_future(
            dispatch(c, tools, ToolCall("ns_hold", {"who": "b"}, source="mcp:hub"))
        )
        await asyncio.wait_for(world.event(world.entered, "b").wait(), 5)
        assert CALL_CHANNEL_FACT not in c.facts and CALL_SOURCE_FACT not in c.facts
        world.event(world.released, "a").set()  # the earlier call ends first: the order that leaks
        world.event(world.released, "b").set()
        return [await first, await second]

    results = run(scenario())
    assert [r.status for r in results] == ["ALLOW", "ALLOW"]
    seen = [
        (f[CALL_SOURCE_FACT]["value"], f[CALL_CHANNEL_FACT]["value"])
        for f in events.of_type("gate_facts")
    ]
    assert seen == [("bridge:muse", "bridge"), ("mcp:hub", "mcp")]
    assert c.facts == {}


def test_a_degrade_fallback_is_judged_with_the_channel_of_the_call_that_was_blocked():
    """The fallback of a BLOCK runs through its own gate as the same call: same source, same channel."""
    # driveway: open_gate lists no bridge, so `bridge:muse` degrades to `porch_light_on`
    # (the corpus case `open_gate_from_a_bridge_degrades.yaml` runs it end to end); here the
    # frame is the thing: a second gate that reads `call_channel` sees the family too.
    clock = Clock()
    events = EventLog(clock)
    engine = ActionContractEngine(clock=clock, events=events)
    for name, allow, on_block in (
        ("ns_main", ["mcp"], {"action": "degrade", "fallback_action": "ns_fallback"}),
        ("ns_fb", ["bridge"], {"action": "deny"}),
    ):
        engine.register(
            name,
            resolve_gate_document(
                {
                    "schema": "neuroedge.gate/v1",
                    "name": name,
                    "version": "1.0.0",
                    "evaluate": choice(call_channel=FAMILIES),
                    "allow_when": {"call_channel": {"in": allow}},
                    "on_block": on_block,
                    "budget": {"p95_latency_ms": 5000},
                }
            ),
        )

    @action(name="ns_main", requires="digital.out:porch_light", gate="ns_main")
    def main() -> None:
        """Allowed for the `mcp` family only; a bridge degrades."""

    @action(name="ns_fallback", requires="digital.out:porch_light", gate="ns_fb")
    def fallback() -> None:
        """Allowed for the `bridge` family only."""

    c = Conversation(engine=engine, hal=SimHAL(events=events))
    c.register_source("bridge:muse")
    result = run(dispatch(c, ToolSet([spec_of(main)]), call("ns_main", "bridge:muse")))
    assert result.status == "BLOCK"
    assert result.action.fallback is not None and not result.action.fallback.blocked
    assert [f[CALL_CHANNEL_FACT]["value"] for f in events.of_type("gate_facts")] == ["bridge"] * 2


# --- who may answer an ask, and replay -----------------------------------------------------------


def test_bridge_and_mcp_sources_are_not_human_sources():
    assert set(HUMAN_SOURCES) == {"local_grammar", "ui"}
    assert not any(s.startswith(("bridge:", "mcp:")) for s in HUMAN_SOURCES)


async def test_a_replayed_trace_with_a_bridge_source_needs_no_plugin(lamp):
    recorder = TraceRecorder()
    session = SimSession.load(lamp, events=recorder)
    session.conversation.register_source("bridge:muse")
    assert (await session.call_tool(call("lamp_on", "bridge:muse"))).status == "ALLOW"
    trace = recorder.to_trace()
    validate_trace(trace)  # the free-string source and the new fact are valid in trace.v1
    recorded = [e["data"] for e in trace["events"] if e["type"] == "tool_call"]
    assert recorded[0]["source"] == "bridge:muse"

    # A fresh player: it registers nobody and loads no plugin; it replays what was recorded.
    result = await TracePlayer(trace, agent=lamp).replay()
    assert result.verdicts == result.recorded_verdicts == ["ALLOW"]
    assert result.divergences == []


# --- registration: the id a call names must be one somebody registered -----------------------


def test_a_call_for_a_source_nobody_registered_is_refused_by_dispatch(lamp):
    session = lamp_session(lamp)
    for source in ("bridge:typo", "mcp:hub"):
        with pytest.raises(ToolCallError) as raised:
            run(session.call_tool(call("lamp_on", source)))
        error = raised.value
        assert error.code == "NE1004" and source in error.why and error.where and error.how
    assert session.events.of_type("tool_call") == [], "nothing was dispatched"
    assert session.hal.pin("porch_light").never_pulsed()
    # the five built-in names need no registration
    assert run(session.call_tool(call("lamp_on", "local_grammar"))).status == "ALLOW"


def test_a_source_registered_for_one_session_is_not_registered_for_another(lamp):
    first, second = lamp_session(lamp, "bridge:muse"), lamp_session(lamp)
    assert run(first.call_tool(call("lamp_on", "bridge:muse"))).status == "ALLOW"
    with pytest.raises(ToolCallError):
        run(second.call_tool(call("lamp_on", "bridge:muse")))


def test_the_same_id_registered_twice_is_refused(lamp):
    session = lamp_session(lamp, "bridge:muse")
    with pytest.raises(ToolCallError, match="already registered") as raised:
        session.conversation.register_source("bridge:muse")
    assert raised.value.code == "NE1004" and raised.value.how
    session.conversation.register_source("mcp:muse")  # another family, another source


@pytest.mark.parametrize(
    "source",
    ["mcp", "local_grammar", "bridge:", "bridge:Muse", "bridge:a-b", "mqtt:x", "bridge:muse\n"],
)
def test_an_id_outside_the_grammar_or_a_built_in_name_is_not_registered(lamp, source):
    session = lamp_session(lamp)
    with pytest.raises(ToolCallError) as raised:
        session.conversation.register_source(source)
    assert raised.value.code == "NE1004" and raised.value.how
