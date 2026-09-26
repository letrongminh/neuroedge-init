"""
TSK-I4-02 — SystemOne's cloud primary, swapped in by `[system_one]` of agent.toml
(FR-MDL-04, Q-4, Q-14): Jev over the System One API, the command grammar as its
fallback (FR-MDL-03).

CI has no key and no network: every request goes to a fake transport, the same
callable `SystemOneApi` hands its HTTP to, or to a server on 127.0.0.1. Each
fail-closed branch of `models/providers/systemone_api.py` has a test here, and the
session tests prove that no `[system_one]` leaves an agent exactly as it was. What
`[system_one]` shares with the other provider tables — the endpoint check, never
echoing a key, the HTTP layer — is tested once for all of them in
`test_provider_common.py`.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error

import pytest
from typer.testing import CliRunner

from neuroedge.actions.tools import ToolCall
from neuroedge.cli.main import app
from neuroedge.engine import (
    ActionContractEngine,
    BreakerState,
    DegradationBreaker,
    EventLog,
    Fact,
    GateVerdict,
    Reason,
    Unavailable,
    resolve_gate_document,
)
from neuroedge.engine.compiler import build
from neuroedge.errors import AgentManifestError, BuildFailed
from neuroedge.models import BACKEND, CommandGrammar, ScriptedSource, SystemOne, SystemTwo
from neuroedge.models.providers import (
    SystemOneApi,
    SystemOneConfig,
    make_system_one_source,
    parse_system_one,
    system_one_for,
    systemone_api,
)
from neuroedge.models.system import FALLBACK_RESERVE_MS
from neuroedge.sim import SimSession
from neuroedge.testing.recorder import TraceRecorder
from neuroedge.trace import validate_trace

KEY = "sk-or-test-DO-NOT-LEAK-0123456789abcdef"
ENV = "NEUROEDGE_TEST_S1_KEY"
MODEL = "typesafe/jev-1.13"
ENDPOINT = "https://openrouter.ai/api/v1/systemone"

BOOL = {"type": "bool", "instructions": "The person asks to turn the light on"}
LEVEL = {
    "type": "level",
    "levels": ["low", "medium", "high"],
    "instructions": "How urgent the request is",
}
CHOICE = {
    "type": "choice",
    "options": ["unlock", "light", "other"],
    "instructions": "What the person asks for",
}
DEFINITIONS = {"wants_light": BOOL, "urgency": LEVEL, "request_kind": CHOICE}
WORDS = "bật đèn giúp mình"
# What `c.do()` hands the fact source: the words, and the caller's action and arguments.
STATE = {"utterance": WORDS, "action": "light_on", "arguments": {"note": "the owner said yes"}}


# --- the fake transport -----------------------------------------------------------------------


def reply(criterion: str, answer: dict, *, status: int = 200, **top) -> tuple[int, bytes]:
    """A System One response, shaped like OpenRouter's (docs: `POST /api/v1/systemone`)."""
    body = {
        "id": "gen-dec-1790015143-test",
        "model": "typesafe/jev-1.13-20260917",
        "provider": "TypeSafe",
        "answers": {criterion: answer},
        "usage": {"input_tokens": 120, "output_tokens": 9, "cost": 0.00000504},
        **top,
    }
    return status, json.dumps(body).encode()


def noul(p: float, criterion: str = "wants_light") -> tuple[int, bytes]:
    return reply(criterion, {"type": "noul", "noul": p})


def score(probabilities: dict, confidence: float, value: float = 1.0) -> tuple[int, bytes]:
    answer = {
        "type": "score",
        "score": value,
        "confidence": confidence,
        "probabilities": probabilities,
        "legend": {"0": "low", "1": "medium", "2": "high"},
    }
    return reply("urgency", answer)


def choice(option: str, confidence: float, probabilities: dict | None = None):
    """A choice answer; by default all the probability on `option` (the API always sends it)."""
    if probabilities is None:
        probabilities = {name: float(name == option) for name in CHOICE["options"]}
    answer = {
        "type": "choice",
        "choice": option,
        "confidence": confidence,
        "probabilities": probabilities,
    }
    return reply("request_kind", answer)


class Transport:
    """Records each request and answers from a script (a reply, an exception, or a callable)."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests: list[dict] = []

    def __call__(self, url, headers, body, timeout_s):
        self.requests.append(
            {"url": url, "headers": dict(headers), "body": json.loads(body), "timeout_s": timeout_s}
        )
        answer = self.replies.pop(0) if self.replies else noul(0.97)
        if callable(answer):
            answer = answer()
        if isinstance(answer, BaseException):
            raise answer
        return answer


def config(**overrides) -> SystemOneConfig:
    fields = {
        "model": MODEL,
        "api_key_env": ENV,
        "criteria": ("wants_light", "urgency", "request_kind"),
        "threshold": 0.8,
        "timeout_ms": 1500.0,
    }
    return SystemOneConfig(**{**fields, **overrides})


def source(transport, *, environ=None, events=None, **overrides) -> SystemOneApi:
    environ = {ENV: KEY} if environ is None else environ
    return SystemOneApi(config(**overrides), events=events, environ=environ, transport=transport)


async def ask(
    transport, criterion="wants_light", *, events=None, deadline_ms=None, state=STATE, **kw
):
    s1 = source(transport, events=events, **kw)
    return await s1.adjudicate(criterion, DEFINITIONS[criterion], state, deadline_ms)


# --- the happy path, per type -----------------------------------------------------------------


async def test_a_bool_criterion_is_one_noul_question_about_the_persons_words():
    transport = Transport(noul(0.96))
    answer = await ask(transport)
    assert answer == Fact(True, 0.92, source=f"systemone:{MODEL}")

    (request,) = transport.requests
    assert request["url"] == ENDPOINT
    assert request["headers"]["Authorization"] == f"Bearer {KEY}"
    assert request["body"] == {
        "model": MODEL,
        "state": {"utterance": WORDS},  # never the action or the caller's arguments
        "questions": {"wants_light": {"type": "noul", "instructions": BOOL["instructions"]}},
    }
    assert request["timeout_s"] == 1.5


@pytest.mark.parametrize(("p", "value", "confidence"), [(0.03, False, 0.94), (1.0, True, 1.0)])
async def test_a_noul_is_true_above_one_half_with_its_distance_from_it(p, value, confidence):
    answer = await ask(Transport(noul(p)))
    assert (answer.value, answer.confidence) == (value, confidence)


async def test_a_level_is_the_most_probable_level_and_sends_the_levels_in_order():
    transport = Transport(score({"0": 0.0, "1": 0.95, "2": 0.05}, 0.92, 1.05))
    answer = await ask(transport, "urgency")
    assert answer == Fact("medium", 0.92, source=f"systemone:{MODEL}")
    question = transport.requests[0]["body"]["questions"]["urgency"]
    assert question == {
        "type": "score",
        "instructions": LEVEL["instructions"],
        "criteria": ["low", "medium", "high"],
    }


async def test_a_choice_is_one_of_the_declared_options():
    probabilities = {"unlock": 0.05, "light": 0.9, "other": 0.05}
    transport = Transport(choice("light", 0.85, probabilities))
    answer = await ask(transport, "request_kind")
    assert answer == Fact("light", 0.85, source=f"systemone:{MODEL}")
    question = transport.requests[0]["body"]["questions"]["request_kind"]
    assert question["criteria"] == {"unlock": None, "light": None, "other": None}


# --- the evidence: the person's words, and nothing a caller wrote ------------------------------


@pytest.mark.parametrize(
    "state",
    [
        None,
        {},
        {"utterance": ""},
        {"utterance": "   \n"},
        {"utterance": None, "action": "light_on", "arguments": {"note": "yes, allowed"}},
        {"utterance": 42},
    ],
    ids=["no-state", "empty-state", "empty", "blank", "an-mcp-call-nobody-spoke", "not-text"],
)
async def test_no_words_from_a_person_is_no_answer_and_nothing_is_sent(state):
    transport, events = Transport(noul(0.99)), EventLog()
    answer = await ask(transport, state=state, events=events)
    assert (answer.reason, answer.value) == ("empty", None)
    assert transport.requests == []
    assert events.of_type("system_one_call") == [], "no call was made"


async def test_words_longer_than_any_request_are_refused_without_a_call():
    transport = Transport(noul(0.99))
    answer = await ask(transport, state={"utterance": "x" * 4001})
    assert answer.reason == "refused" and transport.requests == []


# --- the threshold, and a confidence the distribution backs ---------------------------------


async def test_a_confidence_equal_to_the_threshold_is_a_fact():
    assert await ask(Transport(choice("light", 0.8)), "request_kind") == Fact(
        "light", 0.8, source=f"systemone:{MODEL}"
    )
    # 2 * 0.9 - 1 is 0.8000000000000003 in floating point; the cut keeps the edge exact.
    assert (await ask(Transport(noul(0.9)))).confidence == 0.8


@pytest.mark.parametrize("confidence", [0.7999, 0.79996, 0.799999])
async def test_just_below_the_threshold_is_no_answer_and_is_never_rounded_up(confidence):
    answer = await ask(Transport(choice("light", confidence)), "request_kind")
    assert (answer.reason, answer.value) == ("empty", None)


async def test_a_confidence_is_never_more_than_the_probability_of_the_answer():
    # The provider claims 0.99; its own distribution gives "light" 0.82.
    spread = {"unlock": 0.13, "light": 0.82, "other": 0.05}
    answer = await ask(Transport(choice("light", 0.99, spread)), "request_kind")
    assert answer.confidence == 0.82
    level = await ask(Transport(score({"0": 0.3, "1": 0.7, "2": 0.0}, 0.99)), "urgency")
    assert (level.reason, level.value) == ("empty", None), "0.7 is below 0.8, whatever it claims"


async def test_below_the_threshold_is_empty_and_the_event_keeps_the_confidence():
    events = EventLog()
    answer = await ask(Transport(noul(0.7)), events=events)  # confidence 0.4
    assert (answer.reason, answer.value) == ("empty", None)
    (call,) = events.of_type("system_one_call")
    assert (call["status"], call["reason"], call["confidence"]) == ("unavailable", "empty", 0.4)


async def test_a_noul_of_exactly_one_half_decides_nothing():
    answer = await ask(Transport(noul(0.5)), threshold=0.5)
    assert answer.reason == "empty"


@pytest.mark.parametrize("threshold", [0.0, 0.49, 1.01])
def test_a_threshold_under_one_half_is_refused_even_when_built_in_code(threshold):
    with pytest.raises(ValueError, match=r"\[0.5, 1\]"):
        source(Transport(), threshold=threshold)


# --- fail closed: nothing sent ------------------------------------------------------------------


async def test_without_the_key_nothing_is_sent_and_no_call_is_traced():
    transport, events = Transport(), EventLog()
    answer = await ask(transport, environ={ENV: "  "}, events=events)
    assert answer.reason == "offline"
    assert f"{ENV} is not set" in answer.detail
    assert transport.requests == []
    assert events.of_type("system_one_call") == []


async def test_a_key_with_a_trailing_newline_is_sent_stripped():
    transport = Transport(noul(0.97))
    await ask(transport, environ={ENV: f"{KEY}\n"})
    assert transport.requests[0]["headers"]["Authorization"] == f"Bearer {KEY}"


@pytest.mark.parametrize("value", [f"{KEY}\r\nX-Evil: 1", f"{KEY[:10]} {KEY[10:]}", f"{KEY}\x00"])
async def test_a_key_with_control_characters_inside_is_not_used_and_not_repeated(value):
    transport = Transport(noul(0.97))
    answer = await ask(transport, environ={ENV: value})
    assert answer.reason == "offline" and transport.requests == []
    assert KEY not in answer.detail and KEY[:10] not in answer.detail


async def test_a_criterion_not_listed_is_refused_without_a_call():
    transport = Transport()
    answer = await ask(transport, "urgency", criteria=("wants_light",))
    assert answer.reason == "refused"
    assert transport.requests == []


@pytest.mark.parametrize(
    "definition",
    [
        {"type": "bool", "instructions": "  "},
        {"type": "bool"},
        {"type": "level", "levels": [f"l{i}" for i in range(11)], "instructions": "x"},
        {"type": "level", "levels": ["low", "low"], "instructions": "x"},
        {"type": "choice", "options": ["only"], "instructions": "x"},
        {"type": "number", "instructions": "x"},
    ],
    ids=["blank", "no-instructions", "11-levels", "repeated-level", "one-option", "number"],
)
async def test_a_definition_the_api_cannot_ask_is_refused_without_a_call(definition):
    transport = Transport()
    s1 = source(transport)
    answer = await s1.adjudicate("wants_light", definition, STATE, None)
    assert answer.reason == "refused"
    assert transport.requests == []


async def test_no_budget_left_is_a_timeout_without_a_call():
    transport = Transport()
    assert (await ask(transport, deadline_ms=0)).reason == "timeout"
    assert transport.requests == []


async def test_the_gates_remaining_budget_caps_the_models_timeout():
    transport = Transport(noul(0.97))
    await ask(transport, deadline_ms=400)
    assert transport.requests[0]["timeout_s"] == 0.4


# --- fail closed: the call fails ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (400, "refused"),
        (401, "offline"),
        (402, "offline"),
        (403, "refused"),
        (404, "offline"),
        (408, "timeout"),
        (413, "refused"),
        (422, "refused"),
        (429, "rate_limited"),
        (500, "offline"),
        (502, "offline"),
        (503, "offline"),
        (504, "timeout"),
        (524, "timeout"),
        (529, "rate_limited"),
        (302, "offline"),
    ],
)
async def test_each_http_error_is_an_unavailable_reason(status, reason):
    events = EventLog()
    answer = await ask(Transport((status, b"")), events=events)
    assert (answer.reason, answer.value) == (reason, None)
    (call,) = events.of_type("system_one_call")
    assert (call["status"], call["reason"], call["http_status"]) == ("unavailable", reason, status)


@pytest.mark.parametrize(
    "error",
    [
        urllib.error.URLError("nodename nor servname provided"),
        ConnectionResetError("reset by peer"),
        OSError("TLS handshake failed"),
    ],
)
async def test_a_network_error_is_offline(error):
    answer = await ask(Transport(error))
    assert answer.reason == "offline"


async def test_a_network_error_is_reported_by_its_class_name_only():
    events = EventLog()
    answer = await ask(Transport(ConnectionError(f"bad header {KEY!r}")), events=events)
    assert answer.detail.endswith("(ConnectionError)")
    assert KEY not in answer.detail and KEY not in json.dumps(events.to_trace())


async def test_a_model_that_does_not_answer_in_time_is_a_timeout():
    async def hang(url, headers, body, timeout_s):
        await asyncio.sleep(5)

    events = EventLog()
    started = time.monotonic()
    answer = await ask(hang, events=events, timeout_ms=50.0)
    assert time.monotonic() - started < 2
    assert answer.reason == "timeout"
    (call,) = events.of_type("system_one_call")
    assert call["reason"] == "timeout"


async def test_an_object_with_an_async_call_is_awaited_on_the_loop():
    class Async:
        async def __call__(self, url, headers, body, timeout_s):
            return noul(0.97)

    assert (await ask(Async())).value is True


async def test_a_blocking_transport_that_hangs_is_cut_off_too():
    answer = await ask(Transport(lambda: time.sleep(0.5) or noul(0.99)), timeout_ms=50.0)
    assert answer.reason == "timeout"


async def test_a_call_cancelled_by_its_caller_is_still_traced():
    async def hang(url, headers, body, timeout_s):
        await asyncio.sleep(5)

    events = EventLog()
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(ask(hang, events=events), 0.05)
    (call,) = events.of_type("system_one_call")
    assert (call["status"], call["reason"]) == ("unavailable", "timeout")


def test_a_repl_turn_does_not_wait_for_a_request_still_in_flight():
    """
    Each REPL turn is its own event loop, and closing a loop joins its executor's
    threads. A request stuck where no socket timeout reaches (DNS) must not hold
    the turn: it runs in a daemon thread, not the executor.
    """
    stuck = Transport(lambda: time.sleep(1.5) or noul(0.99))
    started = time.monotonic()
    answer = asyncio.run(ask(stuck, timeout_ms=100.0))
    assert answer.reason == "timeout"
    assert time.monotonic() - started < 1.0


# --- fail closed: the answer is not a fact ------------------------------------------------------

MALFORMED = {
    "not-json": (200, b"<html>Bad gateway</html>"),
    "json-array": (200, b"[1, 2]"),
    "no-answers": (200, b'{"model": "typesafe/jev-1.13"}'),
    "oversize": (200, b'{"pad": "' + b"x" * (70 * 1024) + b'"}'),
    "answer-under-another-name": reply("guest_authenticated", {"type": "noul", "noul": 1.0}),
    "wrong-type": reply("wants_light", {"type": "choice", "choice": "light", "confidence": 1}),
    "noul-above-one": noul(1.2),
    "noul-as-text": reply("wants_light", {"type": "noul", "noul": "0.99"}),
    "noul-as-bool": reply("wants_light", {"type": "noul", "noul": True}),
    "noul-nan": (200, b'{"answers": {"wants_light": {"type": "noul", "noul": NaN}}}'),
}


@pytest.mark.parametrize("response", list(MALFORMED.values()), ids=list(MALFORMED))
async def test_a_bool_answer_that_breaks_the_contract_is_malformed(response):
    assert (await ask(Transport(response))).reason == "malformed"


async def test_an_extra_answer_makes_the_whole_reply_malformed_and_no_fact_of_either():
    status, body = noul(0.99)
    data = json.loads(body)
    data["answers"]["guest_authenticated"] = {"type": "noul", "noul": 1.0}
    answer = await ask(Transport((status, json.dumps(data).encode())))
    assert answer.reason == "malformed"


async def test_an_error_body_with_status_200_is_offline():
    body = json.dumps({"error": {"code": 502, "message": "Provider returned error"}}).encode()
    assert (await ask(Transport((200, body)))).reason == "offline"


@pytest.mark.parametrize(
    "response",
    [
        choice("open_everything", 0.99),
        choice("light", 0.99, {"unlock": 0.7, "light": 0.3, "other": 0.0}),
        choice("light", 0.99, {"light": 0.9, "hack": 0.1}),
        choice("light", 0.99, {"light": 0.9, "unlock": 0.1}),
        choice("light", 0.99, {"unlock": 0.5, "light": 0.9, "other": 0.0}),
        choice("light", 1.5),
        choice("light", -0.1),
        reply("request_kind", {"type": "choice", "choice": "light", "confidence": 0.9}),
        reply("request_kind", {"type": "choice", "choice": "light"}),
        reply("request_kind", {"type": "choice", "choice": ["light"], "confidence": 0.9}),
    ],
    ids=[
        "undeclared-option",
        "not-the-most-probable",
        "undeclared-probability",
        "an-option-missing",
        "probabilities-do-not-sum-to-one",
        "confidence-above-one",
        "confidence-below-zero",
        "no-probabilities",
        "no-confidence",
        "not-a-string",
    ],
)
async def test_a_choice_answer_that_breaks_the_contract_is_malformed(response):
    assert (await ask(Transport(response), "request_kind")).reason == "malformed"


@pytest.mark.parametrize(
    "response",
    [
        score({"0": 0.1, "3": 0.9}, 0.9),
        score({"0": 0.1, "1": 1.4, "2": 0.0}, 0.9),
        score({"1": 1.0}, 0.9),
        reply("urgency", {"type": "score", "score": 1.0, "confidence": 0.9}),
        score({"0": 0.0, "1": 1.0, "2": 0.0}, 0.9, value=7.0),
        reply("urgency", {"type": "score", "score": 1.0, "probabilities": {"1": 1.0}}),
    ],
    ids=[
        "level-outside",
        "probability-above-one",
        "a-level-missing",
        "no-probabilities",
        "score-outside",
        "no-conf",
    ],
)
async def test_a_score_answer_that_breaks_the_contract_is_malformed(response):
    assert (await ask(Transport(response), "urgency")).reason == "malformed"


async def test_two_levels_or_options_tied_for_the_top_decide_nothing():
    answer = await ask(Transport(score({"0": 0.5, "1": 0.0, "2": 0.5}, 0.9)), "urgency")
    assert answer.reason == "empty"
    tie = {"unlock": 0.5, "light": 0.5, "other": 0.0}
    answer = await ask(Transport(choice("light", 0.99, tie)), "request_kind")
    assert answer.reason == "empty"


# --- the trace: what System 2 calls record, never the state or the key -------------------------


async def test_each_call_is_one_event_with_model_latency_usage_and_cost():
    events = EventLog()
    await ask(Transport(noul(0.97)), events=events)
    (call,) = events.of_type("system_one_call")
    assert call == {
        "provider": "systemone",
        "model": MODEL,
        "criterion": "wants_light",
        "latency_ms": call["latency_ms"],
        "status": "ok",
        "confidence": 0.94,
        "served_by": "typesafe/jev-1.13-20260917",
        "prompt_tokens": 120,
        "completion_tokens": 9,
        "cost_usd": 0.00000504,
    }
    assert isinstance(call["latency_ms"], int) and call["latency_ms"] >= 0
    text = json.dumps(events.to_trace(), ensure_ascii=False)
    assert WORDS not in text
    assert KEY not in text
    validate_trace(events.to_trace())


async def test_usage_the_provider_reports_wrongly_is_left_out():
    status, body = noul(0.97)
    data = json.loads(body)
    data["usage"] = {"input_tokens": -1, "output_tokens": True, "cost": "free"}
    events = EventLog()
    await ask(Transport((status, json.dumps(data).encode())), events=events)
    (call,) = events.of_type("system_one_call")
    assert not {"prompt_tokens", "completion_tokens", "cost_usd"} & set(call)


async def test_a_model_id_that_is_not_an_id_is_not_traced():
    status, body = noul(0.97)
    data = json.loads(body)
    data["model"] = "bật đèn giúp mình"
    events = EventLog()
    await ask(Transport((status, json.dumps(data).encode())), events=events)
    (call,) = events.of_type("system_one_call")
    assert "served_by" not in call


async def test_a_reply_the_parser_did_not_foresee_is_malformed_not_a_crash(monkeypatch):
    def explode(*args):
        raise RecursionError("nested too deep")

    monkeypatch.setattr(systemone_api, "read_answer", explode)
    assert (await ask(Transport(noul(0.97)))).reason == "malformed"


# --- the real transport, against a server on 127.0.0.1 -------------------------------------------


@pytest.fixture
def server(proxies):
    """A local System One server: /ok answers, /limited is 429, /moved redirects, /slow hangs."""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    seen: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            seen.append(
                {"path": self.path, "headers": dict(self.headers), "body": self.rfile.read(length)}
            )
            if self.path.startswith("/slow/"):
                time.sleep(1.0)
            if self.path.startswith("/moved/"):
                self.send_response(302)
                self.send_header("Location", "/elsewhere/systemone")
                self.end_headers()
                return
            status, payload = (429, b'{"error": {"code": 429}}')
            if not self.path.startswith("/limited/"):
                status, payload = noul(0.97)
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass  # /slow: the client gave up first, as it should

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", seen
    httpd.shutdown()
    httpd.server_close()


async def test_the_standard_library_transport_posts_the_question_with_the_key(server):
    base, seen = server
    s1 = SystemOneApi(config(api_base=f"{base}/ok"), environ={ENV: KEY})
    answer = await s1.adjudicate("wants_light", BOOL, STATE)
    assert answer == Fact(True, 0.94, source=f"systemone:{MODEL}")
    (request,) = seen
    assert request["path"] == "/ok/systemone"
    assert request["headers"]["Authorization"] == f"Bearer {KEY}"
    assert request["headers"]["Content-Type"] == "application/json"
    assert json.loads(request["body"])["state"] == {"utterance": WORDS}


async def test_the_standard_library_transport_reads_an_http_error_as_a_status(server):
    base, _ = server
    s1 = SystemOneApi(config(api_base=f"{base}/limited"), environ={ENV: KEY})
    assert (await s1.adjudicate("wants_light", BOOL, STATE)).reason == "rate_limited"


async def test_a_redirect_is_not_followed_so_the_key_goes_nowhere_else(server):
    base, seen = server
    s1 = SystemOneApi(config(api_base=f"{base}/moved"), environ={ENV: KEY})
    assert (await s1.adjudicate("wants_light", BOOL, STATE)).reason == "offline"
    assert [request["path"] for request in seen] == ["/moved/systemone"]


async def test_a_slow_server_is_a_timeout(server):
    base, _ = server
    s1 = SystemOneApi(config(api_base=f"{base}/slow", timeout_ms=100.0), environ={ENV: KEY})
    started = time.monotonic()
    assert (await s1.adjudicate("wants_light", BOOL, STATE)).reason == "timeout"
    assert time.monotonic() - started < 0.9


# --- SystemOne: routing, fallback, breaker ------------------------------------------------------


@pytest.fixture(scope="module")
def villa_grammar(root) -> CommandGrammar:
    return CommandGrammar.load(root / "fixtures" / "agents" / "villa-concierge" / "commands.toml")


class Spy:
    def __init__(self, answer=Fact(True, 0.99, source="spy")):
        self.answer = answer
        self.calls: list[tuple[str, float | None]] = []

    async def adjudicate(self, criterion, definition, state, deadline_ms=None):
        self.calls.append((criterion, deadline_ms))
        return self.answer


async def test_only_the_listed_criteria_reach_the_primary():
    primary, events = Spy(), EventLog()
    fallback = ScriptedSource({"room_matches": Fact(True, 1.0, source=BACKEND)})
    fast = SystemOne(MODEL, primary=primary, fallback=fallback, events=events, criteria={"a"})
    answer = await fast.adjudicate("room_matches", BOOL, STATE, 500)
    assert answer == Fact(True, 1.0, source=BACKEND)
    assert primary.calls == []
    assert events.of_type("system_one_fallback") == [], "nothing failed: not the model's to decide"

    alone = SystemOne(MODEL, primary=primary, criteria={"a"})
    assert (await alone.adjudicate("room_matches", BOOL, STATE, 500)).reason == "refused"


async def test_a_failing_model_falls_back_to_the_grammar_with_one_event(villa_grammar):
    events = EventLog()
    primary = source(Transport((503, b"")), events=events, criteria=("command_recognized",))
    fast = SystemOne(
        MODEL, primary=primary, fallback=villa_grammar, events=events, criteria=primary.criteria
    )
    definition = {"type": "bool", "instructions": "A known unlock command was spoken"}
    answer = await fast.adjudicate("command_recognized", definition, {"utterance": "mở cửa"}, 500)
    assert answer == Fact(True, 1.0, source=BACKEND)
    assert events.of_type("system_one_fallback") == [
        {"from": MODEL, "to": BACKEND, "reason": "offline", "criterion": "command_recognized"}
    ]


def _gate(p95: int):
    return resolve_gate_document(
        {
            "schema": "neuroedge.gate/v1",
            "name": "voice_unlock",
            "version": "1.0.0",
            "evaluate": {
                "command_recognized": {"type": "bool", "instructions": "A known command"},
            },
            "allow_when": {"command_recognized": True},
            "on_block": {"action": "deny"},
            "budget": {"p95_latency_ms": p95, "fail": "closed"},
        }
    )


async def test_a_hanging_model_leaves_the_grammar_time_to_answer_inside_the_budget(villa_grammar):
    async def hang(url, headers, body, timeout_s):
        await asyncio.sleep(5)

    events = EventLog()
    primary = source(hang, events=events, criteria=("command_recognized",), timeout_ms=5000.0)
    fast = SystemOne(MODEL, primary=primary, fallback=villa_grammar, events=events)
    engine = ActionContractEngine({"door": _gate(300)}, facts_source=fast, events=events)
    result = await engine.evaluate("door", {}, state={"utterance": "mở cửa"})
    assert result.verdict is GateVerdict.ALLOW, result
    assert [e["reason"] for e in events.of_type("system_one_fallback")] == ["timeout"]
    (call,) = events.of_type("system_one_call")
    assert call["reason"] == "timeout"


async def test_a_hanging_model_without_a_fallback_blocks_on_the_budget():
    async def hang(url, headers, body, timeout_s):
        await asyncio.sleep(5)

    primary = source(hang, criteria=("command_recognized",), timeout_ms=5000.0)
    engine = ActionContractEngine(
        {"door": _gate(100)}, facts_source=SystemOne(MODEL, primary=primary)
    )
    result = await engine.evaluate("door", {}, state={"utterance": "mở cửa"})
    assert (result.verdict, result.reason) == (GateVerdict.BLOCK, Reason.BUDGET_EXCEEDED)


async def test_the_primary_waits_at_most_its_timeout_and_leaves_the_fallback_its_reserve():
    primary = Spy()
    fast = SystemOne(MODEL, primary=primary, fallback=ScriptedSource({}), timeout_ms=1500)
    await fast.adjudicate("x", BOOL, None, 3000)
    await fast.adjudicate("x", BOOL, None, 500)
    assert [deadline for _, deadline in primary.calls] == [1500, 500 - FALLBACK_RESERVE_MS]


async def test_no_room_for_the_model_is_not_held_against_it():
    primary, events = Spy(), EventLog()
    breaker = DegradationBreaker(failure_threshold=1)
    fallback = ScriptedSource({"x": Fact(True, 1.0, source=BACKEND)})
    fast = SystemOne(MODEL, primary=primary, fallback=fallback, events=events, breaker=breaker)
    answer = await fast.adjudicate("x", BOOL, None, FALLBACK_RESERVE_MS / 2)
    assert answer == Fact(True, 1.0, source=BACKEND)
    assert primary.calls == []
    assert breaker.state is BreakerState.CLOSED
    assert [e["reason"] for e in events.of_type("system_one_fallback")] == ["timeout"]


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


async def test_the_breaker_stops_calling_a_dead_model_and_tries_again_after_cooldown():
    clock = Clock()
    transport = Transport((503, b""), (503, b""), noul(0.97))
    breaker = DegradationBreaker(failure_threshold=2, cooldown_ms=1000, clock=clock)
    fallback = ScriptedSource({"wants_light": Fact(True, 1.0, source=BACKEND)})
    fast = SystemOne(MODEL, primary=source(transport), fallback=fallback, breaker=breaker)

    for _ in range(3):
        assert await fast.adjudicate("wants_light", BOOL, STATE) == Fact(True, 1.0, source=BACKEND)
    assert len(transport.requests) == 2, "open after two failures: the third went to the grammar"
    assert breaker.state is BreakerState.OPEN

    clock.now = 1000.0  # half-open: one trial call, which succeeds and closes it
    answer = await fast.adjudicate("wants_light", BOOL, STATE)
    assert answer == Fact(True, 0.94, source=f"systemone:{MODEL}")
    assert breaker.state is BreakerState.CLOSED


async def test_answers_below_the_threshold_do_not_open_the_breaker():
    transport = Transport(*[noul(0.6)] * 4)  # confidence 0.2 every time
    breaker = DegradationBreaker(failure_threshold=2)
    fallback = ScriptedSource({"wants_light": Fact(True, 1.0, source=BACKEND)})
    fast = SystemOne(MODEL, primary=source(transport), fallback=fallback, breaker=breaker)
    for _ in range(4):
        await fast.adjudicate("wants_light", BOOL, STATE)
    assert len(transport.requests) == 4, "a model that answers, unsure, is not a dead model"
    assert breaker.state is BreakerState.CLOSED


@pytest.mark.parametrize(
    ("replies", "definition", "state"),
    [
        ([(413, b"")] * 3, BOOL, STATE),
        ([(422, b"")] * 3, BOOL, STATE),
        ([], {"type": "level", "levels": [f"l{i}" for i in range(11)], "instructions": "x"}, STATE),
        ([], BOOL, {"utterance": "", "action": "light_on"}),
        ([], BOOL, {"utterance": "x" * 5000}),
    ],
    ids=["413-too-large", "422-refused", "a-definition-it-cannot-ask", "nobody-spoke", "too-long"],
)
async def test_what_says_nothing_about_the_providers_health_never_opens_the_breaker(
    replies, definition, state
):
    """Any MCP client can send these; if they counted, it could knock the cloud out."""
    transport = Transport(*replies)
    breaker = DegradationBreaker(failure_threshold=1)
    fast = SystemOne(MODEL, primary=source(transport), fallback=ScriptedSource({}), breaker=breaker)
    for _ in range(3):
        await fast.adjudicate("wants_light", definition, state, 3000)
    assert breaker.state is BreakerState.CLOSED


async def test_a_timeout_counts_only_when_the_model_had_its_whole_timeout():
    async def hang(url, headers, body, timeout_s):
        await asyncio.sleep(5)

    breaker = DegradationBreaker(failure_threshold=1)
    fallback = ScriptedSource({})
    fast = SystemOne(
        MODEL, primary=source(hang), fallback=fallback, breaker=breaker, timeout_ms=100
    )
    # The gate had 120 ms left: the model got 70, less than its own 100 — the budget's doing.
    await fast.adjudicate("wants_light", BOOL, STATE, 120)
    assert breaker.state is BreakerState.CLOSED
    # With room for all of its 100 ms, a model that does not answer is a slow provider.
    await fast.adjudicate("wants_light", BOOL, STATE, 1000)
    assert breaker.state is BreakerState.OPEN


# --- a custom adapter (FR-MDL-08), held to the same contract ------------------------------------

ADAPTER = '''
"""A System 1 adapter written outside NeuroEdge: it imports nothing from it."""


class Answer:
    def __init__(self, value, confidence):
        self.value, self.confidence = value, confidence


def make_source(config):
    from neuroedge.engine.verdict import Fact

    class Local:
        name = "local-s1"
        seen = []

        async def adjudicate(self, criterion, definition, state, deadline_ms=None):
            self.seen.append(state)
            mode = config.options["mode"]
            if mode == "raise":
                raise RuntimeError("model file vanished")
            if mode == "outside":
                return Fact("open_everything", 0.99, source="context")
            if mode == "junk":
                return Answer(True, 1.0)
            return Fact(True, 0.95, source="context")

    return Local()
'''


@pytest.fixture
def adapter_config(tmp_path):
    (tmp_path / "my_s1.py").write_text(ADAPTER, encoding="utf-8")

    def make(mode: str) -> SystemOneConfig:
        return config(provider="python:my_s1:make_source", model="local", options={"mode": mode})

    yield make
    sys.modules.pop("my_s1", None)


@pytest.mark.parametrize(
    ("mode", "criterion", "expected"),
    [
        ("ok", "wants_light", Fact(True, 0.95, source="local-s1:local")),
        ("outside", "request_kind", Unavailable("malformed")),
        ("junk", "wants_light", Unavailable("malformed")),
        ("raise", "wants_light", Unavailable("offline")),
    ],
)
async def test_a_custom_adapter_is_checked_labelled_and_traced(
    tmp_path, adapter_config, mode, criterion, expected
):
    events = EventLog()
    s1 = make_system_one_source(adapter_config(mode), tmp_path, events)
    answer = await s1.adjudicate(criterion, DEFINITIONS[criterion], STATE, None)
    if isinstance(expected, Fact):
        assert answer == expected, "a fact is labelled with who decided it, never 'context'"
    else:
        assert answer.reason == expected.reason
    (call,) = events.of_type("system_one_call")
    assert (call["provider"], call["model"], call["criterion"]) == ("local-s1", "local", criterion)
    assert s1.inner.seen == [{"utterance": WORDS}], "an adapter sees the words, never the caller's"


async def test_a_custom_adapter_is_never_asked_without_a_persons_words(tmp_path, adapter_config):
    s1 = make_system_one_source(adapter_config("ok"), tmp_path, EventLog())
    answer = await s1.adjudicate("wants_light", BOOL, {"utterance": "", "action": "x"}, None)
    assert answer.reason == "empty" and s1.inner.seen == []


def test_an_adapter_factory_that_fails_or_returns_no_fact_source_is_a_three_part_error(tmp_path):
    (tmp_path / "bad_s1.py").write_text(
        "def boom(config):\n    raise RuntimeError('no endpoint')\n\n"
        "def nothing(config):\n    return 42\n",
        encoding="utf-8",
    )
    try:
        for factory, why in (("boom", "raised RuntimeError"), ("nothing", "not a FactSource")):
            with pytest.raises(AgentManifestError) as raised:
                make_system_one_source(config(provider=f"python:bad_s1:{factory}"), tmp_path)
            assert why in raised.value.why
            assert raised.value.where.endswith("[system_one] provider")
    finally:
        sys.modules.pop("bad_s1", None)


# --- [system_one] in agent.toml -------------------------------------------------------------------


def test_a_minimal_table_reads_with_its_defaults():
    parsed = parse_system_one({"model": MODEL, "api_key_env": ENV, "criteria": ["wants_light"]})
    assert parsed == SystemOneConfig(
        model=MODEL, api_key_env=ENV, criteria=("wants_light",), threshold=0.8, timeout_ms=1500.0
    )
    assert parsed.endpoint == ENDPOINT
    direct = parse_system_one(
        {"model": "jev-1.13", "api_base": "https://api.typesafe.ai/v1/", "criteria": ["x"]}
    )
    assert direct.endpoint == "https://api.typesafe.ai/v1/systemone"


GOOD = {"model": MODEL, "api_key_env": ENV, "criteria": ["wants_light"]}


@pytest.mark.parametrize(
    ("table", "where", "complaint"),
    [
        ({**GOOD, "temp": 1}, "temp", "not fields"),
        ({**GOOD, "provider": "litellm"}, "provider", "provider must"),
        ({**GOOD, "provider": "openai"}, "provider", "provider must"),
        ({"api_key_env": ENV, "criteria": ["x"]}, "model", "needs a string `model`"),
        ({"model": MODEL, "criteria": ["x"]}, "api_key_env", "does not say where"),
        ({**GOOD, "api_base": "ftp://h"}, "api_base", "http"),
        ({"model": MODEL, "api_key_env": ENV}, "criteria", "nothing is delegated"),
        ({**GOOD, "criteria": []}, "criteria", "nothing is delegated"),
        ({**GOOD, "criteria": "wants_light"}, "criteria", "nothing is delegated"),
        ({**GOOD, "criteria": ["a", 3]}, "criteria", "nothing is delegated"),
        ({**GOOD, "criteria": ["a", "a"]}, "criteria", "more than once"),
        ({**GOOD, "criteria": ["a", "call_source"]}, "criteria", "dispatcher"),
        ({**GOOD, "threshold": 0}, "threshold", "[0.5, 1]"),
        ({**GOOD, "threshold": 0.49}, "threshold", "[0.5, 1]"),
        ({**GOOD, "threshold": 1.5}, "threshold", "[0.5, 1]"),
        ({**GOOD, "threshold": True}, "threshold", "[0.5, 1]"),
        ({**GOOD, "threshold": float("nan")}, "threshold", "[0.5, 1]"),
        ({**GOOD, "timeout_ms": 0}, "timeout_ms", "milliseconds"),
        ({**GOOD, "timeout_ms": 20_000}, "timeout_ms", "milliseconds"),
        ({**GOOD, "options": {"a": 1}}, "options", "custom adapter"),
        ({**GOOD, "provider": "python:m:f", "options": {"token": "t"}}, "options.token", "never"),
    ],
)
def test_a_bad_system_one_table_is_a_three_part_error(table, where, complaint):
    with pytest.raises(AgentManifestError) as raised:
        parse_system_one(table)
    assert raised.value.where.endswith(where)
    assert complaint in raised.value.why
    assert raised.value.how


def test_the_criteria_hint_says_which_criteria_never_to_delegate():
    with pytest.raises(AgentManifestError) as raised:
        parse_system_one({"model": MODEL, "api_key_env": ENV})
    for name in ("guest_authenticated", "staff_co_authorized", "room_matches"):
        assert name in raised.value.how
    assert "session facts from the property system" in raised.value.how


def test_the_threshold_bounds_are_allowed():
    assert parse_system_one({**GOOD, "threshold": 1}).threshold == 1.0
    assert parse_system_one({**GOOD, "threshold": 0.5}).threshold == 0.5


def test_even_without_a_key_the_model_is_never_reached_in_clear_text():
    """A man in the middle would decide the gate's facts (outside review, 2026-09-26)."""
    keyless = {"model": MODEL, "criteria": ["x"], "api_base": "http://10.0.0.5:8080/v1"}
    with pytest.raises(AgentManifestError) as raised:
        parse_system_one(keyless)
    assert "clear text" in raised.value.why and "forge" in raised.value.why
    assert parse_system_one({**keyless, "api_base": "http://127.0.0.2:8080/v1"}).api_key_env is None


# --- an agent: home-voice with one criterion delegated to Jev ----------------------------------

LIGHT_ON = """schema:  neuroedge.gate/v1
name:    light_on
version: 1.0.0

evaluate:
  call_source:
    type: choice
    options: [local_grammar, system_one, system_two, mcp, test]
    instructions: "Nguồn của tool call, do dispatcher đặt (Q-24)"
  wants_light:
    type: bool
    instructions: "The person asks for the light to be turned on"

allow_when:
  call_source: { in: [local_grammar, system_one, system_two, mcp] }
  wants_light: true

on_block:
  action: deny

budget:
  p95_latency_ms: 3000
  fail:           closed
"""

SYSTEM_ONE = f"""
[system_one]
model       = "{MODEL}"
api_key_env = "{ENV}"
criteria    = ["wants_light"]
threshold   = 0.8
timeout_ms  = 1500
"""


@pytest.fixture
def agent(root, copy_agent, monkeypatch):
    """home-voice with `wants_light` in its light_on gate; `agent(table)` appends `table`."""
    monkeypatch.setenv(ENV, KEY)
    commands = (root / "fixtures" / "agents" / "home-voice" / "commands.toml").read_text("utf-8")
    # Offline, the grammar settles `wants_light` for its own command (Q-14).
    decides = commands.replace(
        'tool     = "light_on"', 'tool     = "light_on"\nfacts    = { wants_light = true }'
    )

    def make(table: str = SYSTEM_ONE, *, grammar_decides: bool = True, gates=None):
        files = {"gates/light_on@1.0.0.yaml": LIGHT_ON, **(gates or {})}
        if grammar_decides:
            files["commands.toml"] = decides
        return copy_agent("home-voice", table, files)

    return make


@pytest.fixture
def wire(monkeypatch):
    """Point every `SystemOneApi` built from agent.toml at a fake transport."""

    def install(*replies) -> Transport:
        transport = Transport(*replies)
        monkeypatch.setattr(systemone_api, "urllib_transport", transport)
        return transport

    return install


async def test_the_model_decides_its_criterion_and_the_light_turns_on(agent, wire):
    transport = wire(noul(0.97))
    session = SimSession.load(agent())
    turn = await session.handle("bật đèn")

    assert turn.allowed
    assert session.hal.pin("porch_light").commands == [("on", 0)]
    (request,) = transport.requests
    assert request["body"]["questions"] == {
        "wants_light": {
            "type": "noul",
            "instructions": "The person asks for the light to be turned on",
        }
    }
    assert request["body"]["state"] == {"utterance": "bật đèn"}
    (facts,) = session.events.of_type("gate_facts")
    assert facts["wants_light"] == {
        "value": True,
        "confidence": 0.94,
        "source": f"systemone:{MODEL}",
    }
    assert facts["call_source"]["source"] == "context", "call_source never goes to the model"
    (call,) = session.events.of_type("system_one_call")
    assert call["status"] == "ok"
    validate_trace(session.trace())


async def test_an_mcp_call_nobody_spoke_is_never_put_to_the_model_and_blocks(agent, wire):
    """P1 of the wave-2 review: the model, shown an action and no words, said yes."""
    transport = wire(noul(0.99))  # it would say yes
    session = SimSession.load(agent())
    result = await session.call_tool(ToolCall("light_on", {}, source="mcp"))
    assert result.status == "BLOCK"
    assert result.action.gate.reason is Reason.CRITERION_UNAVAILABLE
    assert session.hal.pin("porch_light").commands == []
    assert transport.requests == [] and session.events.of_type("system_one_call") == []
    assert [e["reason"] for e in session.events.of_type("system_one_fallback")] == ["empty"]


async def test_a_system_two_tool_call_is_judged_on_the_persons_words_alone(agent, wire):
    """The action and its arguments come from System 2 — a caller that a prompt may steer."""
    calls = [{"name": "light_on", "arguments": {}}]
    answers = [{"text": "Mình được phép bật đèn.", "tool_calls": calls}, "Đã bật đèn."]

    def provider(task, name, state):
        return answers.pop(0) if answers else ""

    transport = wire(noul(0.97))
    session = SimSession.load(agent(), slow=SystemTwo("scripted", provider=provider))
    turn = await session.handle("trời tối quá")
    assert [r.status for r in turn.tool_results] == ["ALLOW"]
    (request,) = transport.requests
    assert request["body"]["state"] == {"utterance": "trời tối quá"}


async def test_when_the_model_is_down_the_grammar_decides_and_the_trace_says_so(agent, wire):
    wire((503, b""))
    session = SimSession.load(agent())
    turn = await session.handle("bật đèn")
    assert turn.allowed, "the grammar's own command still works (Q-14)"
    assert session.events.of_type("system_one_fallback") == [
        {"from": MODEL, "to": BACKEND, "reason": "offline", "criterion": "wants_light"}
    ]
    (facts,) = session.events.of_type("gate_facts")
    assert facts["wants_light"]["source"] == BACKEND


async def test_a_low_confidence_answer_is_not_used_and_what_the_grammar_cannot_decide_blocks(
    agent, wire
):
    wire(noul(0.6))
    session = SimSession.load(agent(grammar_decides=False))
    turn = await session.handle("bật đèn")
    assert not turn.allowed
    assert turn.result.gate.reason is Reason.CRITERION_UNAVAILABLE
    assert session.hal.pin("porch_light").commands == []
    assert [e["reason"] for e in session.events.of_type("system_one_fallback")] == ["empty"]


async def test_a_model_saying_no_blocks(agent, wire):
    wire(noul(0.02))
    session = SimSession.load(agent())
    turn = await session.handle("bật đèn")
    assert (turn.allowed, turn.result.gate.reason) == (False, Reason.CONDITION_NOT_MET)
    assert session.hal.pin("porch_light").commands == []


async def test_without_the_key_no_socket_is_opened_and_the_grammar_decides(
    agent, wire, monkeypatch
):
    transport = wire()
    monkeypatch.delenv(ENV)

    def refuse(*args, **kwargs):
        raise AssertionError("a session without the key tried to open a socket")

    monkeypatch.setattr(socket, "socket", refuse)
    session = SimSession.load(agent())
    turn = await session.handle("bật đèn")
    assert turn.allowed
    assert transport.requests == []
    assert session.events.of_type("system_one_call") == []
    assert [e["reason"] for e in session.events.of_type("system_one_fallback")] == ["offline"]


def test_no_system_one_table_leaves_the_agent_exactly_as_before(root):
    session = SimSession.load(root / "fixtures" / "agents" / "home-voice" / "agent.toml")
    fast = session.fast
    assert fast is session.conversation.engine.facts_source
    assert (fast.model, fast.primary, fast.network) == ("sim", None, "offline")
    assert (fast.criteria, fast.timeout_ms, fast.breaker) == (None, None, None)
    assert system_one_for(session.manifest) is None
    asyncio.run(session.handle("bật đèn"))
    assert session.events.of_type("system_one_call") == []


def test_a_replay_recomputes_from_the_recorded_facts_without_the_model_or_its_key(
    agent, wire, monkeypatch
):
    from neuroedge.testing.player import replay_sync

    transport = wire(noul(0.97), noul(0.01))
    manifest = agent()
    session = SimSession.load(manifest)
    asyncio.run(session.handle("bật đèn"))
    asyncio.run(session.handle("bật đèn"))
    trace = session.trace()
    assert len(transport.requests) == 2

    monkeypatch.delenv(ENV)
    later = wire(AssertionError("replay asked the model"))
    result = replay_sync(trace, agent=manifest)
    assert result.divergences == []
    assert [a.blocked for a in result.actions] == [False, True]
    assert later.requests == [] and len(transport.requests) == 2, "replay asked no model"
    assert result.replayed["events"] and not [
        e for e in result.replayed["events"] if e["type"] == "system_one_call"
    ]


async def test_anonymize_hashes_the_text_and_the_model_call_carries_none(agent, wire):
    transport = wire(noul(0.97))
    recorder = TraceRecorder(anonymize=True)
    session = SimSession.load(agent(), events=recorder)
    await session.handle("bật đèn")
    text = json.dumps(session.trace(), ensure_ascii=False)
    assert "bật đèn" not in text
    (call,) = recorder.of_type("system_one_call")
    assert not {"text", "utterance", "transcript", "state"} & set(call)
    # The trace is anonymised; the provider is still sent what the person said.
    assert transport.requests[0]["body"]["state"]["utterance"] == "bật đèn"


def test_the_repl_banner_names_the_model_its_criteria_and_the_key_variable(agent, wire):
    from rich.console import Console

    from neuroedge.cli.run import banner

    wire()
    console = Console(record=True, width=200)
    banner(SimSession.load(agent()), console)
    text = console.export_text()
    assert f"system 1: systemone {MODEL} for wants_light (key from ${ENV};" in text
    assert "offline, typed text" not in text
    assert KEY not in text


def test_the_banner_says_when_the_key_is_missing(agent, wire, monkeypatch):
    from rich.console import Console

    from neuroedge.cli.run import banner

    wire()
    monkeypatch.delenv(ENV)
    console = Console(record=True, width=200)
    banner(SimSession.load(agent()), console)
    assert f"(${ENV} not set: the grammar decides)" in console.export_text()


# --- the build ------------------------------------------------------------------------------------


def _problems(manifest) -> list:
    with pytest.raises(BuildFailed) as failed:
        build(manifest, target="sim", board_id="sim-default")
    for problem in failed.value.problems:
        assert problem.where and problem.why and problem.how  # FR-DX-04
    return failed.value.problems


def test_a_criterion_no_gate_evaluates_fails_the_build(agent):
    (problem,) = _problems(agent(SYSTEM_ONE.replace('["wants_light"]', '["wants_lihgt"]')))
    assert problem.where.endswith("[system_one] criteria")
    assert "'wants_lihgt'" in problem.why and "wants_light" in problem.why


@pytest.mark.parametrize(
    ("name", "criterion", "table"),
    [
        ("villa-concierge", "guest_authenticated", "sim.facts"),
        ("villa-concierge", "room_matches", "sim.slot_facts"),
        ("home-voice", "room_empty", "sim.sensor_facts"),
    ],
)
def test_a_criterion_the_agent_computes_itself_is_never_delegated(
    copy_agent, name, criterion, table
):
    """A missing slot left room_matches undecided — and a model would have decided it."""
    extra = SYSTEM_ONE.replace('["wants_light"]', f'["{criterion}"]')
    (problem,) = _problems(copy_agent(name, extra))
    assert problem.where.endswith("[system_one] criteria")
    assert f"[{table}]" in problem.why and criterion in problem.why
    assert "session facts from the property system" in problem.how


def test_a_criterion_its_gate_defines_beyond_what_the_api_can_ask_fails_the_build(agent):
    many = LIGHT_ON.replace(
        "  wants_light:\n    type: bool\n",
        "  wants_light:\n    type: level\n    levels: [l0, l1, l2, l3, l4, l5, l6, l7, l8, l9, la]\n",
    ).replace("  wants_light: true", "  wants_light: { gte: l5 }")
    (problem,) = _problems(agent(gates={"gates/light_on@1.0.0.yaml": many}))
    assert problem.where.endswith("[system_one] criteria")
    assert "cannot ask" in problem.why and "2–10" in problem.why


def test_a_timeout_the_gate_budget_cannot_hold_fails_the_build(agent):
    (problem,) = _problems(agent(SYSTEM_ONE.replace("timeout_ms  = 1500", "timeout_ms  = 2990")))
    assert problem.where.endswith("[system_one] timeout_ms")
    assert "'light_on'" in problem.why
    assert f"{3000 - FALLBACK_RESERVE_MS:g}" in problem.how


def test_an_api_key_in_system_one_fails_the_build_without_repeating_it(agent):
    manifest = agent(SYSTEM_ONE + f'api_key = "{KEY}"\n')
    with pytest.raises(BuildFailed) as failed:
        SimSession.load(manifest)
    assert KEY not in failed.value.render() + "".join(p.render() for p in failed.value.problems)
    result = CliRunner().invoke(app, ["build", "--agent", str(manifest), "--target", "sim"])
    assert result.exit_code != 0
    assert "api_key" in result.output
    assert KEY not in result.output


def test_an_adapter_that_cannot_be_imported_fails_the_build(agent):
    (problem,) = _problems(agent(SYSTEM_ONE + 'provider = "python:no_such_s1:make"\n'))
    assert "cannot import" in problem.why


def test_a_well_formed_table_builds(agent):
    report = build(agent(), target="sim", board_id="sim-default")
    assert report.gates == 2


# --- the manual live check ------------------------------------------------------------------------


def test_the_live_script_without_its_key_sends_nothing_and_exits_one(root):
    script = root / "scripts" / "live_jev_smoke.py"
    out = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        env={k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"},
    )
    assert out.returncode == 1
    assert "Nothing was sent" in out.stdout
