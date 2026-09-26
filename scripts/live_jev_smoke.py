#!/usr/bin/env python3
"""
SystemOne's cloud primary on the **real** Jev, with a real key — run by hand, never in CI.

    export OPENROUTER_API_KEY=...
    python scripts/live_jev_smoke.py                              # typesafe/jev-1.13 (Q-4)
    python scripts/live_jev_smoke.py typesafe/jev-1.13 OPENROUTER_API_KEY

It makes exactly three calls to the System One API (`POST {api_base}/systemone`,
TSK-I4-02) — one per gate type: a bool (noul), a level (score), a choice — about
one Vietnamese request, and prints each answer, its latency, the snapshot that
served it, tokens and cost (`system_one_call`). Jev bills input tokens only; three
calls cost a fraction of a cent.

Exit 1 when the key is not set (nothing is sent); exit 0 when every answer kept
the contract — a `Fact`, or an answer below the threshold (`empty`); exit 2
otherwise (malformed, refused, offline, timeout).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

# What the model is shown: the person's words, and nothing else (systemone_api.evidence).
STATE = {"utterance": "bật đèn phòng khách giúp mình, trời tối quá"}
QUESTIONS = {
    "wants_light": {
        "type": "bool",
        "instructions": "The person asks for the light to be turned on",
    },
    "urgency": {
        "type": "level",
        "levels": ["low", "medium", "high"],
        "instructions": "How urgent the person's request is",
    },
    "request_kind": {
        "type": "choice",
        "options": ["light", "door", "news", "other"],
        "instructions": "What the person asks the device to do",
    },
}


async def main(model: str, key_env: str) -> int:
    if not os.environ.get(key_env, "").strip():
        print(f"{key_env} is not set — export {key_env}=<your key> and run again.")
        print("Nothing was sent. (This script is manual; CI never calls a model.)")
        return 1
    from neuroedge.engine.trace_sink import EventLog
    from neuroedge.engine.verdict import Fact
    from neuroedge.models.providers import SystemOneApi, SystemOneConfig

    config = SystemOneConfig(
        model=model,
        api_key_env=key_env,
        criteria=tuple(QUESTIONS),
        threshold=0.5,
        timeout_ms=10_000,
    )
    events = EventLog()
    source = SystemOneApi(config, events=events)
    held = True
    for criterion, definition in QUESTIONS.items():
        answer = await source.adjudicate(criterion, definition, STATE)
        if isinstance(answer, Fact):
            print(f"{criterion} ({definition['type']}): {answer.value!r} @ {answer.confidence}")
        else:
            print(
                f"{criterion} ({definition['type']}): unavailable — {answer.reason}: {answer.detail}"
            )
            held = held and answer.reason == "empty"
    for event in events.of_type("system_one_call"):
        print("  system_one_call", json.dumps(event, ensure_ascii=False))
    events.to_trace()
    return 0 if held else 2


if __name__ == "__main__":
    args = sys.argv[1:]
    model = args[0] if args else "typesafe/jev-1.13"
    key_env = args[1] if len(args) > 1 else "OPENROUTER_API_KEY"
    sys.exit(asyncio.run(main(model, key_env)))
