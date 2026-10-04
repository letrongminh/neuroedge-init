"""
`call_source` belongs to one call (Q-24, `docs/spec/tool_calling.md` §5).

`dispatch()` once put the source into the *shared* `Conversation.facts` for the length of the call
and put the old dict back afterwards. Two calls that overlap on one conversation — an `mcp` call and
a `system_two` call, say, while an action body awaits or a gate waits for an adjudicator — saved
each other's source and restored it at the end, so a source outlived the call it described, and a
call that read `facts` after an `await` (the fallback of a `degrade`, the question of an `ask`) read
whoever had written last. Every test here overlaps two calls on purpose, step by step, with events
the test sets: nothing depends on timing.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import pytest

from neuroedge import action
from neuroedge.actions import Conversation
from neuroedge.actions.spec import spec_of
from neuroedge.actions.tools import CALL_SOURCE_FACT, SOURCES, ToolCall, ToolSet, dispatch
from neuroedge.engine import ActionContractEngine, EventLog, resolve_gate_document
from neuroedge.engine.verdict import Fact
from neuroedge.hal.sim import SimHAL

BASE = {"room_empty": False}


class Clock:
    def __call__(self) -> float:
        return 0.0


@dataclass
class World:
    """The events each test steps through, and what the action bodies did."""

    entered: dict[str, asyncio.Event] = field(default_factory=dict)  # name -> reached it
    released: dict[str, asyncio.Event] = field(default_factory=dict)  # name -> may go on
    ran: list[str] = field(default_factory=list)

    def entered_(self, name: str) -> asyncio.Event:
        return self.entered.setdefault(name, asyncio.Event())

    def released_(self, name: str) -> asyncio.Event:
        return self.released.setdefault(name, asyncio.Event())

    async def reaches(self, name: str) -> None:
        await asyncio.wait_for(self.entered_(name).wait(), timeout=5)

    async def stop_at(self, name: str) -> None:
        """Called by the thing that waits: say it is here, then wait to be released."""
        self.entered_(name).set()
        await self.released_(name).wait()

    def release(self, name: str) -> None:
        self.released_(name).set()


WORLD = World()


class Adjudicator:
    """
    The engine's fact source, standing in for System 1: it answers `armed` with True, but only
    once the test releases `gate:<who>` — a gate evaluation held open while another call starts.
    """

    async def adjudicate(self, criterion, definition, state, deadline_ms):
        await WORLD.stop_at(f"gate:{state['arguments'].get('who', '')}")
        return Fact(True)


@action(name="csi_hold", requires="digital.out:porch_light", gate="csi_open")
async def hold(who: str = "") -> None:
    """Allowed for `local_grammar` and `mcp`; the body waits for the test."""
    WORLD.ran.append(f"hold:{who}")
    await WORLD.stop_at(f"body:{who}")


@action(name="csi_local_only", requires="digital.out:porch_light", gate="csi_local_only")
async def local_only(who: str = "") -> None:
    """Allowed for `local_grammar` only, once `armed`; the body waits for the test."""
    WORLD.ran.append(f"local_only:{who}")
    await WORLD.stop_at(f"body:{who}")


@action(name="csi_fallback", requires="digital.out:porch_light", gate="csi_fallback_gate")
def fallback() -> None:
    """The fallback of `csi_local_only`: its own gate allows `local_grammar` only."""
    WORLD.ran.append("fallback")


@action(name="csi_ask", requires="digital.out:porch_light", gate="csi_ask")
def ask(who: str = "") -> None:
    """Asks a person (`room_empty`) for `local_grammar` and `mcp`, once `armed`."""
    WORLD.ran.append(f"ask:{who}")


def _gate(
    name: str, sources: list[str], on_block: dict, *, armed: bool = False, room: bool = False
):
    evaluate = {
        CALL_SOURCE_FACT: {
            "type": "choice",
            "options": list(SOURCES),
            "instructions": "Who asked; set by the dispatcher",
        }
    }
    allow_when: dict = {CALL_SOURCE_FACT: {"in": sources}}
    for criterion, wanted in (("armed", armed), ("room_empty", room)):
        if wanted:
            evaluate[criterion] = {"type": "bool", "instructions": f"`{criterion}` holds"}
            allow_when[criterion] = True
    return resolve_gate_document(
        {
            "schema": "neuroedge.gate/v1",
            "name": name,
            "version": "1.0.0",
            "evaluate": evaluate,
            "allow_when": allow_when,
            "on_block": on_block,
            "budget": {"p95_latency_ms": 5000},  # the engine waits on a real timer
        }
    )


@dataclass
class Rig:
    c: Conversation
    tools: ToolSet
    events: EventLog

    def start(self, tool: str, source: str, **arguments) -> asyncio.Task:
        """A call of `source`, running on its own task, as two connections would."""
        call = ToolCall(tool, arguments, source=source)
        return asyncio.ensure_future(dispatch(self.c, self.tools, call))

    def gate_sources(self) -> list[str]:
        return [f[CALL_SOURCE_FACT]["value"] for f in self.events.of_type("gate_facts")]


@pytest.fixture
def rig():
    global WORLD
    WORLD = World()
    clock = Clock()
    events = EventLog(clock)
    engine = ActionContractEngine(clock=clock, events=events, facts_source=Adjudicator())
    both = ["local_grammar", "mcp"]
    engine.register("csi_open", _gate("csi_open", both, {"action": "deny"}))
    engine.register(
        "csi_local_only",
        _gate(
            "csi_local_only",
            ["local_grammar"],
            {"action": "degrade", "fallback_action": "csi_fallback"},
            armed=True,
        ),
    )
    engine.register(
        "csi_fallback_gate", _gate("csi_fallback_gate", ["local_grammar"], {"action": "deny"})
    )
    engine.register(
        "csi_ask",
        _gate(
            "csi_ask",
            both,
            {"action": "ask", "message": "Still someone in the room?", "confirms": ["room_empty"]},
            armed=True,
            room=True,
        ),
    )
    conversation = Conversation(engine=engine, hal=SimHAL(events=events), facts=BASE)
    tools = ToolSet(spec_of(fn) for fn in (hold, local_only, fallback, ask))
    return Rig(conversation, tools, events)


# --- 1. nothing of a call stays in the conversation ---------------------------------------------


async def test_two_overlapping_calls_leave_no_source_in_the_conversation(rig):
    c = rig.c
    first = rig.start("csi_hold", "local_grammar", who="a")
    await WORLD.reaches("body:a")
    second = rig.start("csi_hold", "mcp", who="b")
    await WORLD.reaches("body:b")
    # Both are inside their action body: the source is theirs, not the conversation's.
    assert CALL_SOURCE_FACT not in c.facts

    WORLD.release("body:a")  # the earlier call finishes first: the order that used to leak
    assert (await first).status == "ALLOW"
    assert CALL_SOURCE_FACT not in c.facts
    WORLD.release("body:b")
    assert (await second).status == "ALLOW"

    assert c.facts == BASE
    assert rig.gate_sources() == ["local_grammar", "mcp"]  # each was judged as who it was


async def test_a_call_does_not_take_the_facts_another_one_set_meanwhile(rig):
    c = rig.c
    first = rig.start("csi_hold", "local_grammar", who="a")
    await WORLD.reaches("body:a")
    c.facts = {**BASE, "room_empty": True}  # agent code replaces the conversation's facts
    WORLD.release("body:a")
    await first
    assert c.facts == {**BASE, "room_empty": True}  # not put back to what it was before the call


# --- 2. no cross-attribution: a gate for `local_grammar` never admits `mcp` --------------------


async def test_an_mcp_call_is_not_judged_as_the_local_call_in_flight_beside_it(rig):
    """
    An `mcp` call asks for `csi_local_only` (gate: `local_grammar` only; on block: degrade to a
    fallback whose gate is `local_grammar` only too). While its gate waits for the adjudicator, a
    `local_grammar` call is allowed and sits in its body. The `mcp` call then resumes: it is
    blocked, and so must its fallback be — it is not the call in flight.
    """
    mcp = rig.start("csi_local_only", "mcp", who="m")
    await WORLD.reaches("gate:m")
    local = rig.start("csi_local_only", "local_grammar", who="l")
    WORLD.release("gate:l")
    await WORLD.reaches("body:l")  # the local call is allowed and in flight

    WORLD.release("gate:m")
    result = await mcp

    assert result.status == "BLOCK"
    assert result.action.fallback is not None and result.action.fallback.blocked
    assert WORLD.ran == ["local_only:l"]  # neither the mcp call's body nor its fallback ran
    WORLD.release("body:l")
    assert (await local).status == "ALLOW"
    assert CALL_SOURCE_FACT not in rig.c.facts


# --- 3. `ask`: the question and the answer keep the source of the call that raised it ----------


async def test_a_question_records_the_source_of_its_own_call_under_overlap(rig):
    asked = rig.start("csi_ask", "mcp", who="a")
    await WORLD.reaches("gate:a")
    other = rig.start("csi_ask", "local_grammar", who="b")
    await WORLD.reaches("gate:b")  # both gates are waiting: whoever writes `facts` last is `b`

    WORLD.release("gate:a")
    first = await asked
    WORLD.release("gate:b")
    second = await other

    pending = {r.call.source: r.action.confirmation for r in (first, second)}
    assert pending["mcp"].context[CALL_SOURCE_FACT] == "mcp"
    assert pending["local_grammar"].context[CALL_SOURCE_FACT] == "local_grammar"
    assert CALL_SOURCE_FACT not in rig.c.facts


async def test_a_confirmation_is_judged_again_with_the_original_source_under_overlap(rig):
    asked = rig.start("csi_ask", "mcp", who="a")
    await WORLD.reaches("gate:a")
    WORLD.release("gate:a")
    (question,) = [(await asked).action.confirmation]
    assert question.context[CALL_SOURCE_FACT] == "mcp"

    # A person answers on the device while a `local_grammar` call is in flight beside the answer.
    WORLD.entered_("gate:a").clear()
    WORLD.released_("gate:a").clear()  # the re-evaluation waits for the adjudicator again
    answer = asyncio.ensure_future(rig.c.confirm(question.id, "local_grammar"))
    await WORLD.reaches("gate:a")
    other = rig.start("csi_hold", "local_grammar", who="b")
    await WORLD.reaches("body:b")
    WORLD.release("gate:a")
    result = await answer

    assert not result.blocked and result.gate.confirmed == ("room_empty",)
    assert rig.gate_sources()[-1:] == ["mcp"]  # the confirmed evaluation saw the original source
    assert CALL_SOURCE_FACT not in rig.c.facts
    WORLD.release("body:b")
    await other
    assert rig.c.facts == BASE


# --- 4. the trace says which source each evaluation saw -----------------------------------------


async def test_the_trace_carries_the_right_source_for_each_call(rig):
    mcp = rig.start("csi_local_only", "mcp", who="m")
    await WORLD.reaches("gate:m")
    local = rig.start("csi_local_only", "local_grammar", who="l")
    WORLD.release("gate:l")
    await WORLD.reaches("body:l")
    WORLD.release("gate:m")
    await mcp
    WORLD.release("body:l")
    await local

    calls = [(e["id"], e["source"]) for e in rig.events.of_type("tool_call")]
    assert calls == [("call_1", "mcp"), ("call_2", "local_grammar")]
    # Evaluations, in the order they finished: the local call's gate; the mcp call's gate; and the
    # fallback of the mcp call — judged as the mcp call.
    assert rig.gate_sources() == ["local_grammar", "mcp", "mcp"]
    results = rig.events.of_type("gate_evaluation_result")
    assert [r["verdict"] for r in results] == ["ALLOW", "BLOCK", "BLOCK"]
    assert rig.events.of_type("gate_evaluation_begin")[-1]["gate"].startswith("csi_fallback_gate")
