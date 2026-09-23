"""
TSK-S3-26 / Q-26 / RFC-0006 — a person answers the device's `on_block: ask`.

The home-voice gate `light_off` asks while someone is in the room and declares
`confirms: [room_empty]`. A person's "có" on the device stands in for that one
criterion; the gate is evaluated again and only then does a token exist. Nobody
else can answer: not System 2, not an MCP client, not after the TTL, not twice,
not for a gate that changed.
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request

import anyio
import pytest
from mcp import Client

from neuroedge.actions.confirmation import (
    HUMAN_SOURCES,
    MIN_TTL_MS,
    ConfirmationBook,
    ConfirmationRefused,
)
from neuroedge.actions.tools import ToolCall
from neuroedge.engine import ActionContractEngine, EventLog, resolve_gate_document
from neuroedge.engine.decision_tree import compile_tree
from neuroedge.mcp_server import build_server
from neuroedge.models import SystemTwo
from neuroedge.sim import SimSession
from neuroedge.sim.ui import SessionServer
from neuroedge.testing import TracePlayer, assert_matches_golden
from neuroedge.testing.recorder import TraceRecorder


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture(scope="module")
def home(root):
    return root / "fixtures" / "agents" / "home-voice" / "agent.toml"


def occupied(home, **kwargs):
    session = SimSession.load(home, **kwargs)
    session.set_sensor("motion", True)
    return session


def say(session, *lines):
    return [asyncio.run(session.handle(line)) for line in lines]


def light(session):
    return session.hal.pin("porch_light").commands


# --- the happy path, on the device ------------------------------------------------------------


def test_a_person_saying_yes_switches_the_light_off_through_the_gate(home):
    session = occupied(home)
    _, asked, yes = say(session, "bật đèn", "tắt đèn", "có")
    assert asked.reply_source == "gate_ask" and asked.confirmation is not None
    assert light(session) == [("on", 0), ("off", 0)]
    assert (yes.reply_source, yes.reply) == ("confirmed", "Đã xác nhận.")
    (confirmed,) = session.events.of_type("tool_confirmed")
    assert confirmed == {"id": asked.confirmation.id, "source": "local_grammar"}
    # The token came from a second evaluation of the same gate, which records why.
    results = session.events.of_type("gate_evaluation_result")
    assert [r["verdict"] for r in results] == ["ALLOW", "BLOCK", "ALLOW"]
    assert results[-1]["confirmed"] == ["room_empty"]
    session.trace()  # the whole session still validates against trace.v1


def test_the_request_names_the_question_its_ttl_and_what_may_be_confirmed(home):
    session = occupied(home)
    say(session, "tắt đèn")
    (request,) = session.events.of_type("tool_confirm_requested")
    assert request["action"] == "light_off"
    assert request["confirms"] == ["room_empty"]
    assert request["message"] == "Vẫn còn người trong phòng — bạn chắc muốn tắt đèn?"
    assert request["ttl_ms"] == MIN_TTL_MS  # max(150 ms × 3, 10 s)


def test_expiry_is_written_in_trace_time_whatever_the_engine_clock_reads(home):
    """The page counts down from `expires_ms` against `offset_ms`: same time base."""
    clock = Clock()
    clock.now = 3_705_000_000.0  # a monotonic clock is far from zero on a real device
    session = occupied(home, clock=clock)
    say(session, "tắt đèn")
    (event,) = [e for e in session.trace()["events"] if e["type"] == "tool_confirm_requested"]
    assert event["data"]["expires_ms"] == event["offset_ms"] + MIN_TTL_MS


def test_no_declines_and_nothing_runs(home):
    session = occupied(home)
    _, no = say(session, "tắt đèn", "không")
    assert no.reply_source == "declined"
    assert light(session) == []
    assert session.events.of_type("tool_confirm_declined")[0]["source"] == "local_grammar"
    assert session.pending_confirmation() is None


def test_yes_without_a_pending_question_is_just_an_utterance(home):
    session = SimSession.load(home)
    (turn,) = say(session, "có")
    assert turn.reply_source != "confirmed"
    assert session.events.of_type("tool_confirmed") == []


# --- nobody but a person on the device ---------------------------------------------------------


@pytest.mark.parametrize("source", ["system_two", "system_one", "mcp", "test", "cloud"])
def test_only_a_person_on_the_device_may_answer(home, source):
    session = occupied(home)
    (asked,) = say(session, "tắt đèn")
    with pytest.raises(ConfirmationRefused, match="only a person on the device"):
        asyncio.run(session.conversation.confirm(asked.confirmation.id, source))
    assert light(session) == []
    rejected = session.events.of_type("tool_confirm_rejected")
    assert rejected[-1]["source"] == source
    # The refused attempt did not use the question up: a person can still answer.
    assert session.pending_confirmation() is not None
    assert set(HUMAN_SOURCES) == {"local_grammar", "ui"}


def test_system_two_cannot_answer_the_question_its_own_call_raised(home):
    """The model asks for light_off, is told to wait for a person, and says 'có' — nothing."""
    replies = [
        {"tool_calls": [{"name": "light_off", "arguments": {}}]},
        "có",  # the model's own text is speech, never an answer
    ]
    slow = SystemTwo(
        "scripted", provider=lambda task, name, state: replies.pop(0) if replies else ""
    )
    session = occupied(home, slow=slow)
    (turn,) = say(session, "tối rồi, tắt hết cho tiết kiệm")
    assert turn.reply_source == "gate_ask"
    (result,) = turn.tool_results
    assert result.content()["confirmation"]["who"].startswith("a person on the device")
    assert light(session) == [] and session.events.of_type("tool_confirmed") == []
    # A person then answers; the re-evaluation keeps the original caller's source.
    say(session, "có")
    assert light(session) == [("off", 0)]
    assert session.events.of_type("gate_facts")[-1]["call_source"]["value"] == "system_two"


def test_an_mcp_client_has_no_way_to_confirm(home):
    session = occupied(home)
    seen = {}

    async def main():
        async with Client(build_server(session)) as client:
            seen["tools"] = [t.name for t in (await client.list_tools()).tools]
            seen["off"] = await client.call_tool("light_off", {})
            seen["confirm"] = await client.call_tool("confirm", {"id": "confirm_1"})

    anyio.run(main)
    assert seen["tools"] == ["light_on", "light_off"]  # no confirm tool exists
    off = json.loads(seen["off"].content[0].text)
    assert (off["status"], off["on_block"]) == ("BLOCK", "ask")
    assert off["confirmation"]["id"] == "confirm_1"
    assert seen["confirm"].is_error  # no such tool: answering is not a tool
    assert light(session) == []


# --- once, in time, for the gate that asked ----------------------------------------------------


def test_a_confirmation_is_used_once(home):
    session = occupied(home)
    (asked,) = say(session, "tắt đèn")
    asyncio.run(session.confirm(asked.confirmation.id, source="ui"))
    with pytest.raises(ConfirmationRefused, match="already confirmed"):
        asyncio.run(session.conversation.confirm(asked.confirmation.id, "ui"))
    assert light(session) == [("off", 0)]


def test_a_confirmation_expires(home):
    clock = Clock()
    session = occupied(home, clock=clock)
    (asked,) = say(session, "tắt đèn")
    clock.now += MIN_TTL_MS + 1
    (late,) = say(session, "có")
    assert late.reply_source != "confirmed"
    assert session.events.of_type("tool_confirm_expired") == [{"id": asked.confirmation.id}]
    assert light(session) == []


def test_a_confirmation_is_void_if_the_gate_changed_meanwhile(home):
    session = occupied(home)
    (asked,) = say(session, "tắt đèn")
    engine = session.conversation.engine
    changed = dict(engine.gate("light_off").on_block, message="Khác")
    gate = engine.gate("light_off")
    engine.register(
        "light_off",
        resolve_gate_document(
            {
                "schema": "neuroedge.gate/v1",
                "name": gate.name,
                "version": gate.version,
                "evaluate": gate.evaluate,
                "allow_when": gate.allow_when,
                "on_block": changed,
                "budget": gate.budget,
            }
        ),
    )
    with pytest.raises(ConfirmationRefused, match="gate changed"):
        asyncio.run(session.conversation.confirm(asked.confirmation.id, "ui"))
    assert light(session) == []


# --- the gate still decides ----------------------------------------------------------------------


def gate(on_block, extra_criterion=None):
    evaluate = {"room_empty": {"type": "bool", "instructions": "Nobody is in the room"}}
    allow_when = {"room_empty": True}
    if extra_criterion:
        evaluate[extra_criterion] = {"type": "bool", "instructions": "Another condition"}
        allow_when[extra_criterion] = True
    return resolve_gate_document(
        {
            "schema": "neuroedge.gate/v1",
            "name": "t_gate",
            "version": "1.0.0",
            "evaluate": evaluate,
            "allow_when": allow_when,
            "on_block": on_block,
            "budget": {"p95_latency_ms": 100},
        }
    )


ASK = {"action": "ask", "message": "Chắc chứ?", "confirms": ["room_empty"]}


async def evaluate(g, facts, confirmed):
    engine = ActionContractEngine(events=EventLog())
    engine.register("g", g)
    return await engine.evaluate("g", facts, confirmed=confirmed)


async def test_confirmation_stands_in_only_for_the_listed_criteria():
    g = gate(ASK, extra_criterion="caller_ok")
    # room_empty is confirmable; caller_ok is not — a yes cannot rescue it.
    result = await evaluate(g, {"room_empty": False, "caller_ok": False}, confirmed=True)
    assert (result.verdict, result.failed_criterion) == ("BLOCK", "caller_ok")
    allowed = await evaluate(g, {"room_empty": False, "caller_ok": True}, confirmed=True)
    assert allowed.allowed and allowed.confirmed == ("room_empty",)


async def test_the_question_is_only_offered_when_a_yes_would_be_enough():
    g = gate(ASK, extra_criterion="caller_ok")
    useless = await evaluate(g, {"room_empty": False, "caller_ok": False}, confirmed=False)
    assert useless.on_block_action == "ask" and useless.confirms == ()  # nothing to answer
    useful = await evaluate(g, {"room_empty": False, "caller_ok": True}, confirmed=False)
    assert useful.confirms == ("room_empty",)


async def test_a_gate_without_confirms_only_informs():
    g = gate({"action": "ask", "message": "Chắc chứ?"})
    result = await evaluate(g, {"room_empty": False}, confirmed=True)
    assert result.verdict == "BLOCK" and result.confirms == ()


async def test_a_person_may_stand_in_for_a_criterion_nobody_could_decide():
    """Sensor broken, no fact: the person in the room is exactly who can say."""
    result = await evaluate(gate(ASK), {}, confirmed=True)
    assert result.allowed and result.confirmed == ("room_empty",)


async def test_confirmation_never_excuses_a_degraded_adjudicator():
    class Offline:
        async def adjudicate(self, criterion, definition, state, deadline_ms):
            raise ConnectionError("network down")

    g = gate(ASK, extra_criterion="caller_ok")
    engine = ActionContractEngine(events=EventLog(), facts_source=Offline())
    engine.register("g", g)
    # room_empty stood in for, caller_ok must come from the adjudicator, which is down.
    result = await engine.evaluate("g", {"room_empty": False}, confirmed=True)
    assert (result.verdict, result.reason, result.fail_mode) == (
        "BLOCK",
        "gate_unreachable",
        "closed",
    )


def test_the_walker_only_waives_what_it_is_given():
    tree = compile_tree(gate(ASK, extra_criterion="caller_ok"))
    from neuroedge.engine.decision_tree import walk
    from neuroedge.engine.verdict import Fact

    facts = {"room_empty": Fact(False), "caller_ok": Fact(True)}
    assert walk(tree, facts).verdict == "BLOCK"
    assert walk(tree, facts, frozenset({"room_empty"})).verdict == "ALLOW"
    assert walk(tree, facts, frozenset({"caller_ok"})).verdict == "BLOCK"


def test_book_ttl_is_three_p95_with_a_floor():
    book = ConfirmationBook(Clock(), EventLog())
    assert book.ttl_ms(150) == MIN_TTL_MS
    assert book.ttl_ms(5_000) == 15_000


# --- the device's page -------------------------------------------------------------------------


@pytest.fixture
def ui(home):
    session = occupied(home)
    server = SessionServer(session, port=0).start()
    yield server
    server.stop()


def post(server, path, body, headers=None):
    request = urllib.request.Request(
        server.url + path.lstrip("/"),
        data=body.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read())


def test_the_page_offers_the_buttons_and_the_answer_goes_through_the_gate(ui):
    with urllib.request.urlopen(ui.url, timeout=5) as response:
        body = response.read().decode("utf-8")
    assert "fetch('/confirm'" in body and "Thiết bị hỏi xác nhận" in body
    post(ui, "/command", "tắt đèn", {"Content-Type": "text/plain; charset=utf-8"})
    pending = ui.session.pending_confirmation()
    reply = post(ui, "/confirm", json.dumps({"id": pending.id, "answer": "yes"}))
    assert reply == {"ok": True, "reply": "Đã xác nhận.", "verdict": "ALLOW"}
    assert ui.session.events.of_type("tool_confirmed")[0]["source"] == "ui"
    assert light(ui.session) == [("off", 0)]


def test_the_page_rejects_a_malformed_answer(ui):
    assert post(ui, "/confirm", "yes")["ok"] is False
    assert post(ui, "/confirm", json.dumps({"id": "confirm_1", "answer": "maybe"}))["ok"] is False


def test_another_site_cannot_answer_for_the_person(ui):
    post(ui, "/command", "tắt đèn", {"Content-Type": "text/plain; charset=utf-8"})
    with pytest.raises(urllib.error.HTTPError) as refused:
        post(
            ui,
            "/confirm",
            json.dumps({"id": "confirm_1", "answer": "yes"}),
            {"Origin": "http://evil.example"},
        )
    assert refused.value.code == 403
    assert light(ui.session) == []


# --- the REPL and gate explain --------------------------------------------------------------


def test_the_repl_shows_the_question_and_answers_with_confirm(home):
    from rich.console import Console

    from neuroedge.cli.run import _meta, render_turn

    session = occupied(home)
    console = Console(record=True, width=200)
    (asked,) = say(session, "tắt đèn")
    render_turn(asked, session, console)
    _meta(":confirm", session, console)
    out = console.export_text()
    assert "? xác nhận confirm_1" in out and "says (confirmed): Đã xác nhận." in out
    assert light(session) == [("off", 0)]


def test_gate_explain_says_what_a_person_may_confirm(root):
    from typer.testing import CliRunner

    from neuroedge.cli.main import app

    gate_file = root / "fixtures" / "agents" / "home-voice" / "gates" / "light_off@1.0.0.yaml"
    result = CliRunner().invoke(app, ["gate", "explain", str(gate_file)])
    assert result.exit_code == 0, result.output
    assert "Người xác nhận trên thiết bị được thay cho" in result.output
    assert "room_empty" in result.output


# --- replay ---------------------------------------------------------------------------------------


def test_a_confirmed_session_replays_to_the_same_decisions(home):
    recorder = TraceRecorder()
    session = occupied(home, events=recorder)
    say(session, "bật đèn", "tắt đèn", "có")
    trace = recorder.to_trace()
    result = asyncio.run(TracePlayer(trace, agent=home).replay())
    assert result.verdicts == ["ALLOW", "BLOCK", "ALLOW"]
    assert_matches_golden(result, trace)
    assert result.pin("porch_light").commands == [("on", 0), ("off", 0)]


def test_a_tool_call_through_mcp_then_a_person_on_the_page(home):
    """The full demo: Claude Desktop asks, the person on the device's page decides."""
    session = occupied(home)
    server = SessionServer(session, port=0).start()
    try:
        result = asyncio.run(session.call_tool(ToolCall("light_off", {}, source="mcp")))
        assert result.content()["confirmation"]["id"] == "confirm_1"
        reply = post(server, "/confirm", json.dumps({"id": "confirm_1", "answer": "yes"}))
        assert reply["verdict"] == "ALLOW"
        assert session.events.of_type("gate_facts")[-1]["call_source"]["value"] == "mcp"
    finally:
        server.stop()
    assert light(session) == [("off", 0)]
