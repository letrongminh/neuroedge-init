"""
TSK-S2-08 — SystemOne / SystemTwo, deterministic doubles, and the local
fixed-command grammar (Q-14, Q-15). Covers Sprint 2 exit criterion 3.
"""

from __future__ import annotations

import json
import re
import socket
import time
from pathlib import Path

import pytest

from neuroedge.engine import (
    ActionContractEngine,
    EventLog,
    Fact,
    GateVerdict,
    Reason,
    Unavailable,
    resolve_gate_document,
)
from neuroedge.errors import PerceptionUnavailableError
from neuroedge.models import (
    BACKEND,
    CommandGrammar,
    GrammarAdjudicator,
    ScriptedSource,
    SystemOne,
    SystemTwo,
    normalise,
)
from neuroedge.trace import validate_trace

# A test-only gate: one criterion SystemOne adjudicates, the rest from context.
OFFLINE_GATE = {
    "schema": "neuroedge.gate/v1",
    "name": "unlock_offline",
    "version": "1.0.0",
    "evaluate": {
        "command_recognized": {"type": "bool", "instructions": "A known unlock command was spoken"},
        "guest_authenticated": {"type": "bool", "instructions": "Guest verified this session"},
    },
    "allow_when": {"command_recognized": {"confidence_gte": 0.8}, "guest_authenticated": True},
    "on_block": {"action": "deny"},
    "budget": {"p95_latency_ms": 200},
}


@pytest.fixture(scope="module")
def grammar(root: Path) -> CommandGrammar:
    return CommandGrammar.load(root / "fixtures" / "agents" / "villa-concierge" / "commands.toml")


def _engine(system_one: SystemOne, events: EventLog) -> ActionContractEngine:
    gate = resolve_gate_document(OFFLINE_GATE)
    return ActionContractEngine({"unlock": gate}, facts_source=system_one, events=events)


async def _unlock(grammar, utterance: str, *, fallback="grammar"):
    events = EventLog()
    fallback = grammar if fallback == "grammar" else fallback
    fast = SystemOne("jev-latest", fallback=fallback, network="offline", events=events)
    engine = _engine(fast, events)
    result = await engine.evaluate(
        "unlock", {"guest_authenticated": True}, state={"utterance": utterance}
    )
    return result, events


# --- Sprint 2 exit criterion 3 (Q-14) ----------------------------------------


async def test_offline_a_known_command_is_still_adjudicated(grammar):
    result, events = await _unlock(grammar, "Mở cửa phòng 101!")
    assert result.verdict is GateVerdict.ALLOW
    assert events.of_type("system_one_fallback") == [
        {
            "from": "jev-latest",
            "to": BACKEND,
            "reason": "offline",
            "criterion": "command_recognized",
        }
    ]
    validate_trace(events.to_trace())


@pytest.mark.parametrize("utterance", ["hát một bài đi", "", "mo cua"])
async def test_offline_an_unknown_command_blocks_by_normal_criteria(grammar, utterance):
    result, _ = await _unlock(grammar, utterance)
    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is Reason.CRITERION_UNAVAILABLE
    assert result.fail_mode is None, "a normal block, not a degraded one"


async def test_offline_without_a_fallback_is_gate_unreachable(root, grammar):
    result, _ = await _unlock(grammar, "mở cửa", fallback=None)
    assert result.reason is Reason.GATE_UNREACHABLE
    assert (result.fail_mode, result.on_block_action) == ("closed", "deny")


async def test_a_fallback_that_cannot_load_is_rejected_at_construction(tmp_path):
    with pytest.raises(PerceptionUnavailableError) as excinfo:
        SystemOne("jev-latest", fallback=BACKEND, grammar=tmp_path / "missing.toml")
    assert excinfo.value.code == "NE5001"
    assert "missing.toml" in excinfo.value.where
    assert excinfo.value.how


async def test_a_fallback_that_fails_at_run_time_is_gate_unreachable(grammar):
    class Broken:
        async def adjudicate(self, *args, **kwargs):
            raise PerceptionUnavailableError(where="x", why="model file vanished", how="reinstall")

    result, _ = await _unlock(grammar, "mở cửa", fallback=Broken())
    assert result.reason is Reason.GATE_UNREACHABLE


# --- Primary → fallback chain (FR-MDL-03) --------------------------------------


@pytest.mark.parametrize(
    ("reason", "verdict_reason"),
    [
        ("offline", Reason.GATE_UNREACHABLE),
        ("timeout", Reason.BUDGET_EXCEEDED),
        ("rate_limited", Reason.CRITERION_UNAVAILABLE),
        ("malformed", Reason.CRITERION_UNAVAILABLE),
        ("refused", Reason.CRITERION_UNAVAILABLE),
        ("empty", Reason.CRITERION_UNAVAILABLE),
    ],
)
async def test_each_unavailable_reason_maps_to_a_verdict(reason, verdict_reason):
    primary = ScriptedSource({"command_recognized": Unavailable(reason)})
    fast = SystemOne("jev-latest", primary=primary)
    result = await _engine(fast, EventLog()).evaluate("unlock", {"guest_authenticated": True})
    assert result.reason is verdict_reason


async def test_the_primary_answers_when_it_can(grammar):
    primary = ScriptedSource({"command_recognized": Fact(True, 0.99, source="jev")})
    events = EventLog()
    fast = SystemOne("jev-latest", primary=primary, fallback=grammar, events=events)
    result = await _engine(fast, events).evaluate("unlock", {"guest_authenticated": True})
    assert result.allowed
    assert events.of_type("system_one_fallback") == []


async def test_a_failing_primary_falls_back_once(grammar):
    primary = ScriptedSource({"command_recognized": Unavailable("rate_limited")})
    events = EventLog()
    fast = SystemOne("jev-latest", primary=primary, fallback=grammar, events=events)
    engine = _engine(fast, events)
    result = await engine.evaluate(
        "unlock", {"guest_authenticated": True}, state={"utterance": "mở cửa"}
    )
    assert result.allowed
    assert [e["reason"] for e in events.of_type("system_one_fallback")] == ["rate_limited"]


async def test_systemone_refuses_types_outside_bool_level_choice():
    fast = SystemOne("jev-latest", primary=ScriptedSource({}))
    answer = await fast.adjudicate("n", {"type": "number"}, None)
    assert isinstance(answer, Unavailable)
    assert answer.reason == "refused"


async def test_choice_intent_emits_intent_extracted_and_reads_like_the_proposal(grammar):
    events = EventLog()
    fast = SystemOne("jev-latest", fallback=grammar, network="offline", events=events)
    intent = await fast.choice(
        "intent", options=["unlock", "light_on", "faq", "other"], state={"utterance": "bật đèn"}
    )
    assert (intent.top, intent.confidence) == ("light_on", 1.0)
    assert events.of_type("intent_extracted")[-1] == {
        "intent": "light_on",
        "confidence": 1.0,
        "system": "SystemOne",
        "backend": BACKEND,
    }
    missing = await fast.choice("intent", options=["unlock"], state={"utterance": "hello"})
    assert missing.top is None


# --- The grammar ---------------------------------------------------------------


def test_normalise_keeps_vietnamese_diacritics():
    assert normalise("  Mở CỬA,  phòng 101! ") == "mở cửa phòng 101"
    assert normalise("mở cửa") != normalise("mo cua")


def test_a_template_match_captures_slots(grammar):
    recognition = grammar.recognize("mở cửa phòng 204")
    assert (recognition.intent, recognition.confidence, recognition.slots) == (
        "unlock",
        1.0,
        {"room": "204"},
    )


def test_a_near_miss_scores_by_similarity(grammar):
    near = grammar.recognize("bật đèn hiên đi")
    assert near.intent == "light_on"
    assert grammar.threshold <= near.confidence < 1.0


def test_recognition_is_deterministic(grammar):
    first = grammar.recognize("bật đèn hiên đi")
    assert all(grammar.recognize("bật đèn hiên đi") == first for _ in range(1000))


async def test_the_adjudicator_answers_only_what_the_command_declares(grammar):
    adjudicator = GrammarAdjudicator(grammar)
    state = {"utterance": "mấy giờ trả phòng"}
    answer = await adjudicator.adjudicate("command_recognized", {"type": "bool"}, state)
    assert isinstance(answer, Unavailable), "faq declares no facts"
    assert answer.reason == "refused"


@pytest.mark.parametrize(
    ("toml", "where"),
    [
        ("[grammar]\nversion = 2\n", "grammar.version"),
        ("[grammar]\nversion = 1\nthreshold = 1.5\n", "grammar.threshold"),
        ('[grammar]\nversion = 1\n[[command]]\nintent = "x"\n', "command[0]"),
        ("[grammar]\nversion = 1\n", "commands.toml"),
        ("not = [toml", "commands.toml"),
    ],
)
def test_a_malformed_grammar_is_a_three_part_error(tmp_path, toml, where):
    path = tmp_path / "commands.toml"
    path.write_text(toml, encoding="utf-8")
    with pytest.raises(PerceptionUnavailableError) as excinfo:
        CommandGrammar.load(path)
    assert where in excinfo.value.where
    assert excinfo.value.why and excinfo.value.how


async def test_the_offline_path_opens_no_socket(grammar, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("the offline path tried to open a socket")

    monkeypatch.setattr(socket, "socket", refuse)
    result, _ = await _unlock(grammar, "mở cửa phòng 101")
    assert result.allowed


def test_recognition_p95_is_measured(grammar, capsys):
    """Mandatory measurement (CEO-S7-2). Printed, and bounded loosely so it never flakes."""
    utterances = ["mở cửa phòng 101", "bật đèn hiên đi", "hát một bài", "what time is checkout"]
    samples = []
    for index in range(1000):
        start = time.perf_counter()
        grammar.recognize(utterances[index % len(utterances)])
        samples.append((time.perf_counter() - start) * 1000)
    p95 = sorted(samples)[int(0.95 * len(samples))]
    print(json.dumps({"recognize_p95_ms": round(p95, 4)}))
    assert p95 < 50


# --- SystemTwo and the core's dependencies --------------------------------------


async def test_systemtwo_uses_the_fallback_when_the_provider_fails():
    def broken(task, name, state):
        raise ConnectionError("down")

    slow = SystemTwo("claude-sonnet-5", provider=broken, fallback=lambda *a: "fallback reply")
    assert await slow.reply() == "fallback reply"


async def test_systemtwo_with_nothing_configured_is_a_three_part_error():
    with pytest.raises(PerceptionUnavailableError) as excinfo:
        await SystemTwo("claude-sonnet-5").extract("dish_name")
    assert excinfo.value.code == "NE5001"


def test_the_core_imports_no_provider_sdk(root):
    """Q-10: a provider SDK is named only behind `neuroedge.models.providers`."""
    pattern = re.compile(r"^\s*(import|from)\s+(openai|litellm|anthropic)\b", re.MULTILINE)
    providers = root / "python" / "neuroedge" / "models" / "providers"
    offenders = [
        str(path.relative_to(root))
        for path in (root / "python" / "neuroedge").rglob("*.py")
        if providers not in path.parents and pattern.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
