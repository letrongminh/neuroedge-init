#!/usr/bin/env python3
"""
The LiteLLM adapter on the **real** `litellm==1.102.0` — offline, no key (TSK-S2-11).

    pip install -e 'python[cloud]'
    python scripts/cloud_smoke.py

The unit tests (`python/tests/test_providers.py`) use a fake `litellm`; this
proves the adapter reads what the real library returns. LiteLLM answers
locally when a request carries ``mock_response`` / ``mock_tool_calls`` /
``mock_timeout`` (litellm/main.py `mock_completion`, checked in 1.102.0), so
the script wraps `litellm.acompletion` to add them to each request the adapter
sends — the adapter itself is unchanged — and drives the home-voice agent:

1. a tool call → ALLOW through the gate → pin on → the model's text is spoken;
2. the knowledge task: the retrieved context is sent, the reply is spoken;
3. tool arguments that are not JSON → REJECTED, no pin moves;
4. a provider error (`litellm.RateLimitError`) and a timeout → the offline line;
5. every model call traced as `system_two_call` with tokens and cost, the
   trace valid, and the (dummy) key in no trace, print or log line.

Exit 0 when all hold. Run in the CI job `cloud-extra`.
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import io
import json
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

KEY_ENV = "NEUROEDGE_SMOKE_KEY"
KEY = "sk-smoke-not-a-real-key-6f1d2c"
REPO = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(f"::error::{message}")
    sys.exit(1)


def check(condition: bool, message: str) -> None:
    if not condition:
        fail(message)
    print(f"  ok  {message}")


def agent(work: Path) -> Path:
    target = work / "home-voice"
    shutil.copytree(REPO / "fixtures" / "agents" / "home-voice", target)
    manifest = target / "agent.toml"
    manifest.write_text(
        manifest.read_text("utf-8")
        + "\n[system_two]\n"
        + 'provider    = "litellm"\n'
        + 'model       = "anthropic/claude-sonnet-5"\n'
        + f'api_key_env = "{KEY_ENV}"\n',
        encoding="utf-8",
    )
    return manifest


def tool_call(name: str, arguments: str) -> dict:
    return {
        "id": f"call_smoke_{name}",
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }


async def main() -> None:
    try:
        import litellm
    except ImportError:
        fail("litellm is not installed: pip install -e 'python[cloud]'")
    from neuroedge.sim import SimSession

    print(
        f"litellm {getattr(litellm, '__version__', None) or _version()} (real library, mock responses)"
    )
    os.environ[KEY_ENV] = KEY
    real = litellm.acompletion
    mocks: list[dict] = []
    requests: list[dict] = []

    async def acompletion(**request):
        requests.append(request)
        return await real(**request, **(mocks.pop(0) if mocks else {"mock_response": "…"}))

    litellm.acompletion = acompletion

    # 1. tool call → gate → pin → spoken reply
    work = Path(tempfile.mkdtemp(prefix="cloud-smoke-"))
    session = SimSession.load(agent(work))
    mocks[:] = [
        {"mock_response": "", "mock_tool_calls": [tool_call("light_on", "{}")]},
        {"mock_response": "Đã bật đèn hiên."},
    ]
    turn = await session.handle("trời tối quá")
    check(
        [r.status for r in turn.tool_results] == ["ALLOW"],
        "the model's light_on is ALLOWed by the gate",
    )
    check(session.hal.pin("porch_light").commands == [("on", 0)], "porch_light turned on")
    check(
        (turn.reply, turn.reply_source) == ("Đã bật đèn hiên.", "system_two"),
        "the model's text is spoken",
    )
    sent = requests[1]["messages"]
    check(
        sent[2]["tool_calls"][0]["function"] == {"name": "light_on", "arguments": "{}"}
        and json.loads(sent[3]["content"])["status"] == "ALLOW",
        "the tool result went back to the model in OpenAI shape",
    )
    check(
        requests[0]["api_key"] == KEY and requests[0]["tools"],
        "the key and the tools were passed per call",
    )
    calls = session.events.of_type("system_two_call")
    check(
        len(calls) == 2
        and all(
            c["status"] == "ok" and c["prompt_tokens"] > 0 and c["completion_tokens"] > 0
            for c in calls
        ),
        "each model call traced with its tokens",
    )
    check(
        all("cost_usd" in c for c in calls),
        f"cost priced by litellm: {[c.get('cost_usd') for c in calls]}",
    )
    trace = json.dumps(session.trace(), ensure_ascii=False)  # validated against trace.v1
    check(KEY not in trace, "the trace is valid and holds no key")

    # 2. knowledge: context sent, reply spoken
    requests.clear()
    mocks[:] = [{"mock_response": "Wifi là NhaMinh nhé."}]
    turn = await session.handle("mật khẩu wifi")
    check(
        turn.reply_source == "knowledge_rag" and turn.reply == "Wifi là NhaMinh nhé.",
        "knowledge answer spoken",
    )
    check(
        "NhaMinh" in requests[0]["messages"][0]["content"] and "tools" not in requests[0],
        "context sent, no tools",
    )

    # 3. arguments that are not JSON → REJECTED, nothing moves
    before = list(session.hal.pin("porch_light").commands)
    mocks[:] = [
        {"mock_response": "", "mock_tool_calls": [tool_call("light_off", '{"oops')]},
        {"mock_response": "Xin lỗi, mình gọi sai."},
    ]
    turn = await session.handle("phòng chói quá, cho tối lại giùm")
    check(
        [r.status for r in turn.tool_results] == ["REJECTED"], "unparseable arguments are REJECTED"
    )
    check(session.hal.pin("porch_light").commands == before, "no pin moved")

    # 4. provider error and timeout → the offline line
    mocks[:] = [{"mock_response": "litellm.RateLimitError"}]
    turn = await session.handle("đọc tin tức")
    reason = session.events.of_type("system_two_unavailable")[-1]["reason"]
    check(
        turn.reply_source == "offline" and "rate limiting" in reason,
        f"rate limit ⇒ offline line ({reason})",
    )
    provider = session.slow.provider  # the same agent, with a short timeout
    provider.config = dataclasses.replace(provider.config, timeout_s=0.2)
    mocks[:] = [{"mock_timeout": True}]
    turn = await session.handle("đọc tin tức")
    reason = session.events.of_type("system_two_unavailable")[-1]["reason"]
    check(turn.reply_source == "offline" and "time" in reason, f"timeout ⇒ offline line ({reason})")
    shutil.rmtree(work, ignore_errors=True)
    trace = json.dumps(session.trace(), ensure_ascii=False)
    check(KEY not in trace, "after every failure, the trace still holds no key")


def run() -> None:
    """`main()`, with everything it prints and logs captured: the key must be in none of it."""
    captured = io.StringIO()
    handler = logging.StreamHandler(captured)
    handler.setLevel(logging.DEBUG)
    loggers = [logging.getLogger(), logging.getLogger("LiteLLM")]
    for logger in loggers:
        logger.addHandler(handler)
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        try:
            asyncio.run(main())
        except SystemExit:
            print(captured.getvalue(), end="", file=sys.__stdout__)
            raise
    for logger in loggers:
        logger.removeHandler(handler)
    output = captured.getvalue()
    print(output, end="")
    check(KEY not in output, "nothing printed or logged holds the key")
    print("cloud smoke: all checks passed")


def _version() -> str:
    from importlib.metadata import version

    return version("litellm")


if __name__ == "__main__":
    run()
