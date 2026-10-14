#!/usr/bin/env python3
"""
A stand-in LLM for end-to-end runs of the brain (Q-83 TC-A-09-1): an OpenAI-compatible
`/v1/chat/completions` that answers every new user message by calling the one tool whose name
contains `--tool`, and, once the tool's result comes back, writes that result to `--log` (one
JSON line) and answers in words. Streaming (SSE) and plain JSON both.

    python3 scripts/fake_llm.py --port 18080 --tool living_light_on --log llm.jsonl

No model, no network: what the brain does with the box is the thing under test.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def reply(body: dict, tool: str, log: Path) -> dict:
    """The assistant message for this request: a tool call, or words after the tool's result."""
    messages = body.get("messages") or []
    last = messages[-1] if messages else {}
    if last.get("role") == "tool":
        content = last.get("content")
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        with log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"tool_result": content}, ensure_ascii=False) + "\n")
        return {"role": "assistant", "content": "Done."}
    names = [t.get("function", {}).get("name", "") for t in body.get("tools") or []]
    chosen = next((name for name in names if tool in name), None)
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"tools": names, "chosen": chosen}) + "\n")
    if chosen is None:
        return {"role": "assistant", "content": f"No tool named like {tool}."}
    call = {"id": "call_1", "type": "function", "function": {"name": chosen, "arguments": "{}"}}
    return {"role": "assistant", "content": None, "tool_calls": [call]}


class Handler(BaseHTTPRequestHandler):
    tool = ""
    log = Path("llm.jsonl")

    def log_message(self, *args) -> None:  # quiet
        pass

    def do_GET(self) -> None:  # /v1/models, health checks
        self._json({"object": "list", "data": [{"id": "fake-model", "object": "model"}]})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        message = reply(body, self.tool, self.log)
        finish = "tool_calls" if message.get("tool_calls") else "stop"
        base = {"id": "fake", "created": int(time.time()), "model": body.get("model", "fake-model")}
        if not body.get("stream"):
            self._json(
                {
                    **base,
                    "object": "chat.completion",
                    "choices": [{"index": 0, "message": message, "finish_reason": finish}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }
            )
            return
        delta = dict(message)
        if "tool_calls" in delta:
            delta["tool_calls"] = [
                {**call, "index": i} for i, call in enumerate(delta["tool_calls"])
            ]
        chunks = [
            {**base, "object": "chat.completion.chunk",
             "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
            {**base, "object": "chat.completion.chunk",
             "choices": [{"index": 0, "delta": {}, "finish_reason": finish}]},
        ]  # fmt: skip
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for chunk in chunks:
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")

    def _json(self, data: dict) -> None:
        raw = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--tool", required=True, help="call the tool whose name contains this")
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args(argv)
    Handler.tool, Handler.log = args.tool, args.log
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"fake LLM on http://127.0.0.1:{args.port}/v1", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
