#!/usr/bin/env python3
"""
The home-voice agent on a **real** model, with a real key — run by hand, never in CI.

    pip install -e 'python[cloud]'
    export ANTHROPIC_API_KEY=...
    python scripts/live_llm_smoke.py                                  # claude-sonnet-5 (Q-4)
    python scripts/live_llm_smoke.py openai/gpt-4o-mini OPENAI_API_KEY

It spends a few cents. It types three lines — one the model should turn into
`light_on` (through the gate), one knowledge question, one news request —
and prints each turn and each `system_two_call` (tokens, cost, latency).
Exit 1 when the key is not set; exit 0 when the model's light_on met the gate.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


async def main(model: str, key_env: str) -> int:
    if not os.environ.get(key_env, "").strip():
        print(f"{key_env} is not set — export {key_env}=<your key> and run again.")
        print("Nothing was sent. (This script is manual; CI runs scripts/cloud_smoke.py.)")
        return 1
    from neuroedge.sim import SimSession

    work = Path(tempfile.mkdtemp(prefix="live-llm-"))
    target = work / "home-voice"
    shutil.copytree(REPO / "fixtures" / "agents" / "home-voice", target)
    manifest = target / "agent.toml"
    manifest.write_text(
        manifest.read_text("utf-8")
        + f'\n[system_two]\nprovider = "litellm"\nmodel = "{model}"\napi_key_env = "{key_env}"\n',
        encoding="utf-8",
    )
    try:
        session = SimSession.load(manifest)
        for line in ("trời tối quá, mình không thấy gì", "mật khẩu wifi", "đọc tin tức"):
            turn = await session.handle(line)
            calls = [f"{r.call.name}→{r.status}" for r in turn.tool_results]
            print(f"> {line}\n  tools: {calls or '-'}\n  says ({turn.reply_source}): {turn.reply}")
        for event in session.events.of_type("system_two_call"):
            print("  system_two_call", json.dumps(event, ensure_ascii=False))
        for event in session.events.of_type("system_two_unavailable"):
            print("  system_two_unavailable", event["reason"])
        session.trace()  # validated against trace.v1
        lit = session.hal.pin("porch_light").commands
        print(f"porch_light commands: {lit}")
        return 0 if lit == [("on", 0)] else 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    model = args[0] if args else "anthropic/claude-sonnet-5"
    key_env = args[1] if len(args) > 1 else "ANTHROPIC_API_KEY"
    sys.exit(asyncio.run(main(model, key_env)))
