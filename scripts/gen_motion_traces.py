#!/usr/bin/env python3
"""
The corpus of `motion.*` (TSK-I2a-05, RFC-0011, RFC-0013 §3f item 7): `fixtures/traces/motion/*.json`.

Sessions of the sample agent `fixtures/agents/rover` on `sim-rpi5`, recorded on a fake clock so
they are the same every time. The rover has one motor (`wheel_left`, lease 200 ms, speed_max 0.6
on the board, 0.5 in the `drive` gate) and one servo (`gripper`):

    rover-drive-allow.json      the wheel is driven and the lease renewed before it ends (`run: new`,
                                `run: renewed`), the gripper closes: ALLOW three times
    rover-gate-block.json       the wheel is running when the path stops being clear: BLOCK
                                `condition_not_met`, and the channel goes to its safe state (`motion_safe`
                                `stop`, cause `block`)
    rover-lease-expired.json    nobody renews the lease: `motion_safe` `stop`, cause `lease_expired`
    rover-speed-refused.json    a speed over the gate's 0.5 is BLOCK `argument_out_of_range` and the wheel
                                does not move; exactly 0.5 is allowed

`neuroedge verify` replays each on every reference board that declares `motion`, on the clock the
session recorded (a lease that ran out by then has gone safe, a block cuts the run) — no motor, no
servo, no PWM — and the verdicts, the motion commands and the safe states must match (FR-CI-02). A
board without `motion` skips them. Run it only when the sample agent, its gates or the motion contract
changed on purpose; the diff is the review:

    python scripts/gen_motion_traces.py            # rewrite the files
    python scripts/gen_motion_traces.py --check    # exit 1 if they differ (what the test runs)

The session ids and the timestamp are fixed; everything else is what the session wrote.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures" / "traces" / "motion"
AGENT = ROOT / "fixtures" / "agents" / "rover" / "agent.toml"
GAP_MS = 3000.0  # the wheel's envelope keeps 2 s between two runs


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, ms: float) -> None:
        self.now += ms


def tool(name: str, **arguments):
    def apply(session, clock) -> None:
        from neuroedge.actions.tools import ToolCall

        asyncio.run(session.call_tool(ToolCall(name, arguments, source="mcp")))

    return apply


def wait(ms: float):
    return lambda session, clock: clock.advance(ms)


def settle(session, clock) -> None:
    session.hal.settle_motion()  # the clock ticked: a lease that ran out goes safe


def path_clear(clear: bool):
    return lambda session, clock: session.facts.__setitem__("path_clear", clear)


def record(session_id: str, steps) -> dict:
    from neuroedge.sim import SimSession
    from neuroedge.testing.recorder import TraceRecorder

    clock = Clock()
    recorder = TraceRecorder(
        clock=clock, target="sim", board_id="sim-rpi5", session_id=f"sess_{session_id}"
    )
    recorder.metadata["timestamp_utc"] = "2026-10-03T12:00:00Z"
    session = SimSession.load(AGENT, board_id="sim-rpi5", clock=clock, events=recorder)
    try:
        for step in steps:
            step(session, clock)
    finally:
        session.close()
    return recorder.to_trace()


def sessions() -> dict[str, dict]:
    return {
        "rover-drive-allow": record(
            "a11ce300",
            [
                tool("drive", speed=0.3),
                wait(100),  # inside the 200 ms lease: the run is renewed, not restarted
                tool("drive", speed=0.4),
                wait(100),
                tool("grip", angle=45.0),
            ],
        ),
        "rover-gate-block": record(
            "b10c0300",
            [
                tool("drive", speed=0.3),
                wait(50),
                path_clear(False),
                tool("drive", speed=0.3),  # BLOCK: the running wheel is sent to its safe state
            ],
        ),
        "rover-lease-expired": record(
            "c0a1e300",
            [tool("drive", speed=0.3), wait(300), settle],
        ),
        "rover-speed-refused": record(
            "d00d0300",
            [
                tool("drive", speed=0.55),  # over the gate's 0.5 (the board's own is 0.6)
                wait(GAP_MS),
                tool("drive", speed=0.5),  # exactly the gate's limit
            ],
        ),
    }


def render(trace: dict) -> str:
    return json.dumps(trace, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if a file differs")
    args = parser.parse_args()
    differs = []
    made = sessions()
    for name, trace in made.items():
        path = OUT / f"{name}.json"
        text = render(trace)
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                differs.append(path.name)
        else:
            OUT.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
    if args.check:
        differs += sorted(p.name for p in OUT.glob("*.json") if p.stem not in made)
    if differs:
        print(f"differs from the sample agent's sessions: {differs}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
