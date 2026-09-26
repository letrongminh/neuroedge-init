"""
`SystemOneApi` — a `SystemOne` primary over the System One HTTP API (TSK-I4-02, Q-4).

Jev (TypeSafe) is not a chat model: it takes a `state` and typed `questions` and
returns typed answers with probabilities, at ``POST {api_base}/systemone`` — the
same path on OpenRouter (``https://openrouter.ai/api/v1``, the default) and on
TypeSafe (``https://api.typesafe.ai/v1``). So there is no prompt to write and no
text to parse. One gate criterion is one question:

    bool   → {"type": "noul",   "instructions": ...}
    level  → {"type": "score",  "instructions": ..., "criteria": [levels, low → high]}
    choice → {"type": "choice", "instructions": ..., "criteria": {option: null, ...}}

The question comes from the gate (its `instructions`, levels, options). The
`state` is what the gate was asked about — the utterance, the action and its
arguments — sent as data, and nothing in it can add a question, a criterion or
a tool call.

The answer is untrusted data too. It becomes a `Fact` only when it is exactly one
answer, for the criterion asked, of the type asked, with a value inside the
declared levels or options and a confidence in [0, 1] at or above `threshold`
(`admit`). Anything else is `Unavailable`, and `SystemOne` asks the command
grammar instead (FR-MDL-03):

    offline       the key is not set (nothing sent) · network or TLS error · HTTP 401,
                  402, 404, 5xx · a redirect (never followed: it could carry the key away)
    timeout       no answer within min(timeout_ms, what the gate's budget has left) ·
                  HTTP 408, 504, 524
    rate_limited  HTTP 429, 529
    refused       HTTP 400, 403, 413, 422 — the provider refused the question · a
                  criterion not listed in `criteria` · a definition it cannot ask
    malformed     not a JSON object · not one answer for this criterion · the wrong
                  type · a value outside the declared levels or options · confidence
                  missing, not a number, or outside [0, 1]
    empty         confidence below `threshold` · two levels tied for the top

Confidence. Choice and score answers carry the model's own `confidence`. A noul
carries only P(yes); its confidence is |2·P(yes) − 1| — the same measure on two
outcomes (0 at 0.5, 1 at 0 or 1), rounded to 4 places so the threshold edge is
exact. A level is the one the model gives the highest probability.

Each call it makes is one `system_one_call` event: provider, model, criterion,
latency, status and, when the provider reports them, tokens and cost — never
the state, never the key (`docs/spec/tool_calling.md` §7). HTTP goes through the
standard library in a daemon thread: no extra, no SDK, and nothing leaves the
machine unless `[system_one]` is configured and its key is set (FR-DX-02).
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import math
import os
import re
import threading
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any

from ...engine.trace_sink import monotonic_ms
from ...engine.verdict import Fact, Unavailable
from .base import scrub
from .config import SystemOneConfig

NAME = "systemone"
CALL_EVENT = "system_one_call"
MAX_BODY = 64 * 1024  # a decision is a few hundred bytes; more is not an answer
MAX_LEVELS = 10  # the API accepts 2–10 score levels
MAX_OPTIONS = 255  # and at most 255 choice options
QUESTION_TYPE = {"bool": "noul", "level": "score", "choice": "choice"}
MODEL_ID = re.compile(r"[A-Za-z0-9_.:/@+-]{1,100}")

# HTTP status → Unavailable reason. Anything not listed (other 3xx/4xx, 5xx) is offline.
_STATUS_REASON = {
    400: "refused",
    403: "refused",
    413: "refused",
    422: "refused",
    408: "timeout",
    504: "timeout",
    524: "timeout",
    429: "rate_limited",
    529: "rate_limited",
}

# ``transport(url, headers, body, timeout_s) -> (status, body)``: a function (run in a
# daemon thread) or an ``async def`` one.
Transport = Callable[[str, Mapping[str, str], bytes, float], Any]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect is refused, not followed: urllib would resend the Authorization header."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def urllib_transport(
    url: str, headers: Mapping[str, str], body: bytes, timeout_s: float
) -> tuple[int, bytes]:
    """One POST with the standard library; an HTTP error is a status, not an exception."""
    request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=timeout_s) as response:
            return int(response.status), response.read(MAX_BODY + 1)
    except urllib.error.HTTPError as error:
        try:
            payload = error.read(MAX_BODY + 1)
        except Exception:
            payload = b""
        finally:
            error.close()
        return int(error.code), payload


def _in_daemon_thread(function: Callable[..., Any], *args: Any) -> asyncio.Future:
    """
    Run a blocking call off the loop. A daemon thread, not the default executor: a
    loop that closes after a timeout (each REPL turn is its own loop) must not wait
    for a request still stuck in DNS.
    """
    loop = asyncio.get_running_loop()
    future: asyncio.Future = loop.create_future()

    def deliver(setter: str, value: Any) -> None:
        if not future.done():
            getattr(future, setter)(value)

    def run() -> None:
        try:
            result = function(*args)
        except BaseException as exc:  # handed to the awaiting coroutine
            setter, value = "set_exception", exc
        else:
            setter, value = "set_result", result
        with contextlib.suppress(RuntimeError):  # the loop is gone: its caller timed out
            loop.call_soon_threadsafe(deliver, setter, value)

    threading.Thread(target=run, name="neuroedge-systemone", daemon=True).start()
    return future


def _names(values: Any) -> bool:
    return (
        isinstance(values, list | tuple)
        and all(isinstance(value, str) and value for value in values)
        and len(set(values)) == len(values)
    )


def question_for(definition: Mapping[str, Any]) -> dict[str, Any] | Unavailable:
    """The System One question for one gate criterion, or why it cannot be asked."""
    kind = definition.get("type")
    instructions = definition.get("instructions")
    if kind not in QUESTION_TYPE:
        return Unavailable("refused", f"System One asks bool, level or choice, not {kind!r}")
    if not isinstance(instructions, str) or not instructions.strip():
        return Unavailable("refused", "the criterion has no instructions to ask the model")
    question: dict[str, Any] = {"type": QUESTION_TYPE[kind], "instructions": instructions}
    if kind == "level":
        levels = definition.get("levels")
        if not _names(levels) or not 2 <= len(levels) <= MAX_LEVELS:
            return Unavailable("refused", f"a level needs 2–{MAX_LEVELS} distinct level names")
        question["criteria"] = list(levels)
    elif kind == "choice":
        options = definition.get("options")
        if not _names(options) or not 2 <= len(options) <= MAX_OPTIONS:
            return Unavailable("refused", f"a choice needs 2–{MAX_OPTIONS} distinct options")
        question["criteria"] = dict.fromkeys(options)
    return question


def state_for(state: Mapping[str, Any] | None) -> dict[str, Any]:
    """What the gate was asked about, as JSON data; values that are not JSON are left out."""
    out: dict[str, Any] = {}
    for key, value in (state or {}).items():
        if not isinstance(key, str):
            continue
        try:
            json.dumps(value, allow_nan=False)
        except (TypeError, ValueError):
            continue
        out[key] = value
    return out


def _probability(value: Any) -> float | None:
    """A finite number in [0, 1], else None. Booleans are not numbers here."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        return None
    return number


def read_answer(
    answer: Any, definition: Mapping[str, Any]
) -> tuple[bool | str, float] | Unavailable:
    """(value, confidence) from one System One answer, strictly; else `Unavailable`."""
    kind = definition.get("type")
    expected = QUESTION_TYPE.get(str(kind))
    if not isinstance(answer, Mapping):
        return Unavailable("malformed", "the answer is not an object")
    if answer.get("type") != expected:
        return Unavailable("malformed", f"expected a {expected} answer")
    if kind == "bool":
        yes = _probability(answer.get("noul"))
        if yes is None:
            return Unavailable("malformed", "noul is not a probability in [0, 1]")
        return yes > 0.5, round(abs(2.0 * yes - 1.0), 4)
    confidence = _probability(answer.get("confidence"))
    if confidence is None:
        return Unavailable("malformed", "confidence is missing or not in [0, 1]")
    probabilities = answer.get("probabilities")
    if kind == "choice":
        options = list(definition.get("options") or ())
        choice = answer.get("choice")
        if not isinstance(choice, str) or choice not in options:
            return Unavailable("malformed", "the choice is not one of the declared options")
        if probabilities is not None:
            spread = _distribution(probabilities, options)
            if spread is None or spread.get(choice, 0.0) < max(spread.values(), default=0.0):
                return Unavailable("malformed", "the choice is not the most probable option")
        return choice, round(confidence, 4)
    levels = list(definition.get("levels") or ())
    spread = _distribution(probabilities, [str(index) for index in range(len(levels))])
    if not spread:
        return Unavailable("malformed", "a score answer needs probabilities over the levels")
    score = answer.get("score")
    if score is not None and (
        isinstance(score, bool)
        or not isinstance(score, int | float)
        or not math.isfinite(float(score))
        or not -1e-6 <= float(score) <= len(levels) - 1 + 1e-6
    ):
        return Unavailable("malformed", "score lies outside the levels")
    top = max(spread.values())
    winners = [index for index, p in spread.items() if p == top]
    if len(winners) != 1:
        return Unavailable("empty", "two levels are tied for the top")
    return levels[int(winners[0])], round(confidence, 4)


def _distribution(probabilities: Any, keys: list[str]) -> dict[str, float] | None:
    """`probabilities` keyed by a subset of `keys`, each a probability; else None."""
    if not isinstance(probabilities, Mapping) or not probabilities:
        return None
    out: dict[str, float] = {}
    for key, value in probabilities.items():
        number = _probability(value)
        if key not in keys or number is None:
            return None
        out[key] = number
    return out


def admit(
    value: Any, confidence: Any, definition: Mapping[str, Any], threshold: float, source: str
) -> Fact | Unavailable:
    """
    A model's answer as a `Fact` of this criterion — in its domain, with a confidence
    in [0, 1] at or above `threshold` — or `Unavailable`. Used on every cloud answer,
    the built-in adapter's and a custom adapter's alike.
    """
    kind = definition.get("type")
    if kind == "bool":
        in_domain = isinstance(value, bool)
    elif kind == "level":
        in_domain = isinstance(value, str) and value in (definition.get("levels") or ())
    elif kind == "choice":
        in_domain = isinstance(value, str) and value in (definition.get("options") or ())
    else:
        in_domain = False
    if not in_domain:
        return Unavailable("malformed", "the value lies outside the criterion's domain")
    number = _probability(confidence)
    if number is None:
        return Unavailable("malformed", "confidence is missing or not in [0, 1]")
    if number < threshold:
        return Unavailable("empty", f"confidence {number:g} is below the threshold {threshold:g}")
    return Fact(value, number, source=source)


def _usage(body: Mapping[str, Any]) -> dict[str, Any]:
    usage = body.get("usage")
    out: dict[str, Any] = {}
    if not isinstance(usage, Mapping):
        return out
    for theirs, ours in (("input_tokens", "prompt_tokens"), ("output_tokens", "completion_tokens")):
        value = usage.get(theirs)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            out[ours] = value
    cost = usage.get("cost")
    if (
        isinstance(cost, int | float)
        and not isinstance(cost, bool)
        and math.isfinite(float(cost))
        and cost >= 0
    ):
        out["cost_usd"] = round(float(cost), 8)
    return out


class SystemOneApi:
    """A `FactSource`: ``await source.adjudicate(criterion, definition, state, deadline_ms)``."""

    name = NAME

    def __init__(
        self,
        config: SystemOneConfig,
        *,
        events: Any = None,
        environ: Mapping[str, str] | None = None,
        transport: Transport | None = None,
    ) -> None:
        self.config = config
        self.model = config.model
        self.criteria = frozenset(config.criteria)
        self.events = events
        self.environ = os.environ if environ is None else environ
        self.transport = urllib_transport if transport is None else transport

    @property
    def source(self) -> str:
        """What `gate_facts` records as the source of a fact this model decided."""
        return f"{self.name}:{self.model}"

    def _clock(self) -> float:
        return self.events.clock() if self.events is not None else monotonic_ms()

    def _key(self) -> str | None | Unavailable:
        name = self.config.api_key_env
        if name is None:
            return None  # a keyless local server (api_base)
        key = self.environ.get(name, "")
        if not key.strip():
            return Unavailable("offline", f"{name} is not set — nothing was sent")
        return key

    async def adjudicate(
        self,
        criterion: str,
        definition: Mapping[str, Any],
        state: Mapping[str, Any] | None,
        deadline_ms: float | None = None,
    ) -> Fact | Unavailable:
        if criterion not in self.criteria:
            return Unavailable("refused", f"{criterion!r} is not in [system_one] criteria")
        question = question_for(definition)
        if isinstance(question, Unavailable):
            return question
        key = self._key()
        if isinstance(key, Unavailable):
            return key
        limit_ms = self.config.timeout_ms
        if deadline_ms is not None:
            limit_ms = min(limit_ms, deadline_ms)
        if limit_ms <= 0:
            return Unavailable("timeout", "no time left in the gate's budget for the model")
        body = json.dumps(
            {"model": self.model, "state": state_for(state), "questions": {criterion: question}},
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        started = self._clock()
        status: int | None = None
        call: dict[str, Any] = {}
        answer: Fact | Unavailable | None = None
        try:
            try:
                status, payload = await self._post(body, key, limit_ms)
            except TimeoutError:
                answer = Unavailable(
                    "timeout", f"{self.model} did not answer within {limit_ms:g} ms"
                )
            except Exception as exc:  # network, TLS, DNS: the provider is unreachable
                detail = scrub(f"{type(exc).__name__}: {exc}", key)[:200]
                answer = Unavailable("offline", f"{self.model} unreachable: {detail}")
            else:
                try:
                    answer = self._answer(status, payload, criterion, definition, call)
                except Exception as exc:  # a reply this parser did not foresee is no answer
                    answer = Unavailable("malformed", f"unreadable answer: {type(exc).__name__}")
            return answer
        finally:
            # Cancelled by a caller's deadline (SystemOne, the gate budget): still one call.
            self._trace(
                criterion,
                started,
                answer if answer is not None else Unavailable("timeout"),
                status,
                call,
            )

    async def _post(self, body: bytes, key: str | None, limit_ms: float) -> tuple[int, bytes]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if key is not None:
            headers["Authorization"] = f"Bearer {key}"
        timeout_s = limit_ms / 1000.0
        transport = self.transport
        args = (self.config.endpoint, headers, body, timeout_s)
        if inspect.iscoroutinefunction(transport):
            pending = transport(*args)
        else:
            pending = _in_daemon_thread(transport, *args)
        status, payload = await asyncio.wait_for(pending, timeout_s)
        return status, payload

    def _answer(
        self,
        status: Any,
        payload: Any,
        criterion: str,
        definition: Mapping[str, Any],
        call: dict[str, Any],
    ) -> Fact | Unavailable:
        if not isinstance(status, int) or isinstance(status, bool):
            return Unavailable("offline", "the transport returned no HTTP status")
        if not 200 <= status < 300:
            reason = _STATUS_REASON.get(status, "offline")
            return Unavailable(reason, f"{self.model} answered HTTP {status}")
        if not isinstance(payload, bytes | bytearray) or len(payload) > MAX_BODY:
            return Unavailable("malformed", "the response is not a System One answer")
        try:
            body = json.loads(payload)
        except (ValueError, UnicodeDecodeError):
            return Unavailable("malformed", "the response is not JSON")
        if not isinstance(body, dict):
            return Unavailable("malformed", "the response is not a JSON object")
        call.update(_usage(body))
        served = body.get("model")
        if isinstance(served, str) and MODEL_ID.fullmatch(served):
            call["served_by"] = served  # an id, never free text: the trace keeps no prose
        answers = body.get("answers")
        if not isinstance(answers, dict):
            if "error" in body:
                return Unavailable("offline", f"{self.model} returned an error")
            return Unavailable("malformed", "the response has no answers")
        if set(answers) != {criterion}:
            # Only the question asked is read: an answer under another name is never a fact.
            return Unavailable("malformed", f"expected exactly one answer, for {criterion!r}")
        read = read_answer(answers[criterion], definition)
        if isinstance(read, Unavailable):
            return read
        value, confidence = read
        call["confidence"] = confidence
        return admit(value, confidence, definition, self.config.threshold, self.source)

    def _trace(
        self,
        criterion: str,
        started: float,
        answer: Fact | Unavailable,
        status: int | None,
        call: Mapping[str, Any],
    ) -> None:
        if self.events is None:
            return
        data: dict[str, Any] = {
            "provider": self.name,
            "model": self.model,
            "criterion": criterion,
            "latency_ms": max(0, int(self._clock() - started)),
            "status": "ok" if isinstance(answer, Fact) else "unavailable",
        }
        if isinstance(answer, Unavailable):
            data["reason"] = answer.reason
        if isinstance(status, int) and not isinstance(status, bool) and status != 200:
            data["http_status"] = status
        for key in ("confidence", "served_by", "prompt_tokens", "completion_tokens", "cost_usd"):
            if key in call:
                data[key] = call[key]
        self.events.emit(CALL_EVENT, data)


class TracedSource:
    """
    A custom `[system_one]` adapter (FR-MDL-08), held to the same contract as the
    built-in one: every answer passes `admit` (domain, confidence, threshold) and
    is labelled with who decided it, and each call is a `system_one_call` event.
    """

    def __init__(self, source: Any, config: SystemOneConfig, events: Any = None) -> None:
        self.inner = source
        self.config = config
        self.events = events
        self.name = str(getattr(source, "name", "custom"))
        self.model = config.model or str(getattr(source, "model", "") or self.name)
        self.criteria = frozenset(config.criteria)

    def _clock(self) -> float:
        return self.events.clock() if self.events is not None else monotonic_ms()

    async def adjudicate(
        self,
        criterion: str,
        definition: Mapping[str, Any],
        state: Mapping[str, Any] | None,
        deadline_ms: float | None = None,
    ) -> Fact | Unavailable:
        if criterion not in self.criteria:
            return Unavailable("refused", f"{criterion!r} is not in [system_one] criteria")
        started = self._clock()
        answer: Fact | Unavailable | None = None
        try:
            raw = await self.inner.adjudicate(criterion, definition, state, deadline_ms)
            if isinstance(raw, Unavailable):
                answer = raw
            elif isinstance(raw, Fact):
                answer = admit(
                    raw.value,
                    raw.confidence,
                    definition,
                    self.config.threshold,
                    f"{self.name}:{self.model}",
                )
            else:
                answer = Unavailable(
                    "malformed", "the adapter returned neither Fact nor Unavailable"
                )
        except Exception as exc:
            answer = Unavailable("offline", f"{self.name} failed: {type(exc).__name__}")
        finally:
            # Cancelled by SystemOne's deadline: the call happened and timed out.
            self._trace(
                criterion, started, answer if answer is not None else Unavailable("timeout")
            )
        return answer

    def _trace(self, criterion: str, started: float, answer: Fact | Unavailable) -> None:
        if self.events is None:
            return
        data: dict[str, Any] = {
            "provider": self.name,
            "model": self.model,
            "criterion": criterion,
            "latency_ms": max(0, int(self._clock() - started)),
            "status": "ok" if isinstance(answer, Fact) else "unavailable",
        }
        if isinstance(answer, Unavailable):
            data["reason"] = answer.reason
        self.events.emit(CALL_EVENT, data)
