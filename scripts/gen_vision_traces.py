#!/usr/bin/env python3
"""
The corpus of `vision.in` (TSK-V1b-02, RFC-0013 §3f item 7): `fixtures/traces/vision/*.json`.

Three sessions of the sample agent `fixtures/agents/gate-watch` on `sim-rpi5`, recorded on a fake
clock so they are the same every time:

    gate-watch-allow.json         a person stands at the gate for three frames: `watch_open_gate` ALLOW
    gate-watch-block.json         nobody there: `watch_open_gate` BLOCK `condition_not_met`
    gate-watch-camera-lost.json   the camera is lost mid-session: BLOCK `criterion_unavailable`

`neuroedge verify` replays each on every reference board that declares `vision.in`, from the
recorded labels alone — no camera, no model — and the verdicts and pin commands must match
(FR-CI-02). Run it only when the sample agent, its gates or the perception contract changed on
purpose; the diff is the review:

    python scripts/gen_vision_traces.py            # rewrite the three files
    python scripts/gen_vision_traces.py --check    # exit 1 if they differ (what the test runs)

The session ids (`sess_a11ce000`, `sess_b10c0000`, `sess_c0a1e000`) and the timestamp are fixed; everything else is what the session wrote.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures" / "traces" / "vision"
AGENT = ROOT / "fixtures" / "agents" / "gate-watch" / "agent.toml"
FRAME_MS = 1000.0 / 30.0  # the first mode of the rig: 640x480 @ 30 fps


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, ms: float) -> None:
        self.now += ms


def record(session_id: str, steps) -> dict:
    from neuroedge.actions.tools import ToolCall
    from neuroedge.sim import SimSession
    from neuroedge.testing.recorder import TraceRecorder

    clock = Clock()
    recorder = TraceRecorder(
        clock=clock, target="sim", board_id="sim-rpi5", session_id=f"sess_{session_id}"
    )
    recorder.metadata["timestamp_utc"] = "2026-10-03T12:00:00Z"
    session = SimSession.load(AGENT, board_id="sim-rpi5", clock=clock, events=recorder)
    try:
        for periods, tool, before in steps:
            clock.advance(periods * FRAME_MS)
            if before is not None:
                before(session)
            asyncio.run(session.call_tool(ToolCall(tool, {}, source="local_grammar")))
    finally:
        session.close()
    return recorder.to_trace()


def sessions() -> dict[str, dict]:
    return {
        "gate-watch-allow": record("a11ce000", [(8.5, "watch_open_gate", None)]),
        "gate-watch-block": record("b10c0000", [(3.5, "watch_open_gate", None)]),
        "gate-watch-camera-lost": record(
            "c0a1e000",
            [(8.5, "watch_open_gate", None), (1.0, "watch_open_gate", lambda s: s.vision.camera.close())],
        ),
    }


def render(trace: dict) -> str:
    return json.dumps(trace, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if a file differs")
    args = parser.parse_args()
    differs = []
    with tempfile.TemporaryDirectory():
        for name, trace in sessions().items():
            path = OUT / f"{name}.json"
            text = render(trace)
            if args.check:
                if not path.is_file() or path.read_text(encoding="utf-8") != text:
                    differs.append(path.name)
            else:
                OUT.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
                print(f"wrote {path.relative_to(ROOT)}")
    if differs:
        print(f"differs from the sample agent's sessions: {differs}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
