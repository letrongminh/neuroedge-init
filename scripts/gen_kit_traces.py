#!/usr/bin/env python3
"""
The corpus of the five hardware kits (TSK-I2b-01, TSK-I2b-02): `fixtures/traces/kits/*.json`.

Ten sessions of the sample agents behind the kits (`villa-concierge`, `home-voice`,
`factory-monitor` on `sim-default`; `gate-camera`, `blinds` on `sim-rpi5`, the board with a camera and
motion channels), recorded on a fake clock so they are the same every time:

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
    gate-camera-allow.json         a stranger at the gate for three frames: light on, gate locked: ALLOW x2
    gate-camera-block.json         nobody there, consent withdrawn, a stranger seen at 0.60, a stranger
                                   with a person in the private zone, then the camera lost: BLOCK x5,
                                   no pin moves
    blinds-allow.json              open, close: ALLOW x2, the servo is commanded; a lease nobody renews
                                   ends in its safe state (`hold`) before the close renews the run
    blinds-block.json              emergency stop pressed, a hand in the slot, the driver faulted: BLOCK x3,
                                   the servo never moves; then an open, the hold running out
                                   (`stop`, `max_hold_ms`), and a close inside the envelope's interval,
                                   allowed by the gate and refused by the envelope

`neuroedge verify` replays each on every reference board that declares what its trace uses
(`digital.out`, plus `sensor.read` for the two kits that read a sensor, `vision.in` for gate-camera,
`motion` for blinds), and the verdicts, pin and motion commands and frames must match (FR-CI-02). Run it
only when a sample agent, its gates or the sensor contract changed on purpose; the diff is the review:

    python scripts/gen_kit_traces.py            # rewrite the ten files
    python scripts/gen_kit_traces.py --check    # exit 1 if they differ (what the test runs)

The session ids and the timestamp are fixed; everything else is what the session wrote.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures" / "traces" / "kits"
AGENTS = ROOT / "fixtures" / "agents"
BOARD = "sim-default"
RIG = "sim-rpi5"  # the board with `vision.in` and `motion`: gate-camera, blinds
STEP_MS = 1000.0  # a person speaks about once a second: far apart for every max_age_ms
FRAME_MS = 1000.0 / 30.0  # the first mode of the rig's camera: 640x480 @ 30 fps


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


def tool(name: str):
    def apply(session) -> None:
        from neuroedge.actions.tools import ToolCall
        from neuroedge.errors import EnvelopeRefusedError

        with contextlib.suppress(EnvelopeRefusedError):  # the refusal is in the trace
            asyncio.run(session.call_tool(ToolCall(name, {}, source="local_grammar")))

    return apply


def frames_to(n: float):
    """Move the fake clock so that the camera has shown frame `n` (`n.5`: half a period past it)."""

    def apply(session) -> None:
        session.clock.now = 1000.0 + n * FRAME_MS

    return apply


def lose_camera(session) -> None:
    session.vision.camera.close()


def wait(ms: float):
    return lambda session: session.clock.advance(ms)


def settle(session) -> None:
    session.hal.settle_motion()  # the clock ticked: a lease that ran out goes safe


def record(agent: str, session_id: str, steps, board: str = BOARD, step_ms: float = STEP_MS) -> dict:
    from neuroedge.sim import SimSession
    from neuroedge.testing.recorder import TraceRecorder

    clock = Clock()
    recorder = TraceRecorder(
        clock=clock, target="sim", board_id=board, session_id=f"sess_{session_id}"
    )
    recorder.metadata["timestamp_utc"] = "2026-10-04T12:00:00Z"
    session = SimSession.load(
        AGENTS / agent / "agent.toml", board_id=board, clock=clock, events=recorder
    )
    session.clock = clock
    try:
        for step in steps:
            clock.advance(step_ms)
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
        "gate-camera-allow": record(
            "gate-camera",
            "6a7ca11e",
            [frames_to(8.5), tool("stranger_light"), tool("stranger_lock")],
            RIG,
            0.0,
        ),
        "gate-camera-block": record(
            "gate-camera",
            "6a7cb10c",
            [
                frames_to(3.5),
                tool("stranger_light"),  # nobody at the gate
                frames_to(8.5),
                fact("recording_consent", False),
                tool("stranger_light"),  # a stranger, but nobody agreed to be recorded
                fact("recording_consent", True),
                frames_to(24.5),
                tool("stranger_lock"),  # seen at 0.60: not sure enough to lock
                frames_to(44.5),
                tool("stranger_light"),  # a person in the private zone as well
                lose_camera,
                wait(100),
                tool("stranger_light"),  # no frames at all
            ],
            RIG,
            0.0,
        ),
        "blinds-allow": record(
            "blinds",
            "b11da11e",
            [
                tool("blinds_open"),
                wait(300),
                settle,  # nobody renewed the lease: the servo holds its place
                wait(500),
                tool("blinds_close"),  # still holding: this command renews the run
            ],
            RIG,
            0.0,
        ),
        "blinds-block": record(
            "blinds",
            "b11db10c",
            [
                fact("estop_released", False),
                tool("blinds_open"),  # the emergency stop is pressed
                fact("estop_released", True),
                fact("path_clear", False),
                tool("blinds_close"),  # a hand in the slot
                fact("path_clear", True),
                fact("device_fault_free", False),
                tool("blinds_open"),  # the driver reports a fault: nobody's "có" stands in for it
                fact("device_fault_free", True),
                tool("blinds_open"),
                wait(300),
                settle,
                wait(2000),
                settle,  # the hold is over: the servo is off
                wait(300),
                tool("blinds_close"),  # the gate allows it, the envelope's 1 s interval does not
            ],
            RIG,
            0.0,
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
