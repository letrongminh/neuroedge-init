#!/usr/bin/env python3
"""
The corpus of the three hardware kits (TSK-I2b-01): `fixtures/traces/kits/*.json`.

Six sessions of the sample agents behind the kits (`villa-concierge`, `home-voice`,
`factory-monitor`) on `sim-default`, recorded on a fake clock so they are the same every time:

    villa-concierge-allow.json     the right room: the door lock is pulsed once for 30 s
    villa-concierge-block.json     the wrong room, no room, a risky guest: BLOCK, the lock never moves
    home-voice-allow.json          the light on, and off once the room is empty: ALLOW, ALLOW
    home-voice-block.json          the light off while someone is moving, then with the sensor
                                   unreadable: BLOCK, the light stays on
    factory-monitor-allow.json     fan and alarm on, the fan off at a normal reading, the alarm off
                                   once the room has cooled: ALLOW x4
    factory-monitor-block.json     the fan off while hot (asks) and critical (refuses), the alarm off
                                   while hot, a reading the bands cannot place: BLOCK, nothing is
                                   switched off

`neuroedge verify` replays each on every reference board that declares `digital.out`, plus
`sensor.read` for the two kits that read a sensor, and the verdicts, pin commands and frames must
match (FR-CI-02). Run it only when a sample agent, its gates or the sensor contract changed on
purpose; the diff is the review:

    python scripts/gen_kit_traces.py            # rewrite the six files
    python scripts/gen_kit_traces.py --check    # exit 1 if they differ (what the test runs)

The session ids and the timestamp are fixed; everything else is what the session wrote.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures" / "traces" / "kits"
AGENTS = ROOT / "fixtures" / "agents"
BOARD = "sim-default"
STEP_MS = 1000.0  # a person speaks about once a second: far apart for every max_age_ms


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, ms: float) -> None:
        self.now += ms


def say(text: str):
    return lambda session: asyncio.run(session.handle(text))


def sensor(name: str, value):
    return lambda session: session.set_sensor(name, value)


def fact(criterion: str, value):
    return lambda session: session.set_fact(criterion, value)


def record(agent: str, session_id: str, steps) -> dict:
    from neuroedge.sim import SimSession
    from neuroedge.testing.recorder import TraceRecorder

    clock = Clock()
    recorder = TraceRecorder(
        clock=clock, target="sim", board_id=BOARD, session_id=f"sess_{session_id}"
    )
    recorder.metadata["timestamp_utc"] = "2026-10-04T12:00:00Z"
    session = SimSession.load(
        AGENTS / agent / "agent.toml", board_id=BOARD, clock=clock, events=recorder
    )
    try:
        for step in steps:
            clock.advance(STEP_MS)
            step(session)
    finally:
        session.close()
    return recorder.to_trace()


def sessions() -> dict[str, dict]:
    return {
        "villa-concierge-allow": record(
            "villa-concierge", "b1170a11", [say("mở cửa phòng 101")]
        ),
        "villa-concierge-block": record(
            "villa-concierge",
            "b117b10c",
            [
                say("mở cửa phòng 202"),
                say("mở cửa"),
                fact("risk_level", "high"),
                say("mở cửa phòng 101"),
            ],
        ),
        "home-voice-allow": record(
            "home-voice",
            "40e0a11e",
            [sensor("motion", False), say("bật đèn"), say("tắt đèn")],
        ),
        "home-voice-block": record(
            "home-voice",
            "40e0b10c",
            [
                sensor("motion", False),
                say("bật đèn"),
                sensor("motion", True),
                say("tắt đèn"),
                sensor("motion", "unreadable"),
                say("tắt đèn"),
            ],
        ),
        "factory-monitor-allow": record(
            "factory-monitor",
            "fac7a11e",
            [
                sensor("temperature", 30),
                say("bật quạt"),
                say("bật báo động"),
                say("tắt quạt"),
                say("tắt báo động"),
            ],
        ),
        "factory-monitor-block": record(
            "factory-monitor",
            "fac7b10c",
            [
                sensor("temperature", 45),
                say("bật quạt"),
                say("bật báo động"),
                say("tắt quạt"),
                sensor("temperature", 60),
                say("tắt quạt"),
                say("tắt báo động"),
                sensor("temperature", "high"),
                say("tắt quạt"),
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
        print(f"differs from the sample agents' sessions: {differs}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
