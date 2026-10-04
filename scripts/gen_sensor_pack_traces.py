#!/usr/bin/env python3
"""
The corpus of the sensor pack (TSK-I2a-02/03/04, RFC-0013 §3f item 7): `fixtures/traces/sensor-pack/*.json`.

Three sessions of the sample agent `fixtures/agents/rail-gate` on `sim-rpi5`, recorded on a fake
clock so they are the same every time:

    rail-gate-allow.json         the supply is read over I2C and shown; the gate opens: ALLOW, ALLOW
    rail-gate-block.json         a sagging rail, then a gate not at its closed stop: BLOCK
                                 `condition_not_met` twice
    rail-gate-unavailable.json   an ADC reading past its range, an ADC reading 501 ms old (the gate
                                 allows 500) and a limit-switch line nobody set: BLOCK
                                 `criterion_unavailable` three times

`neuroedge verify` replays each on every reference board that declares `digital.in`, `analog.in`
and `i2c`, from the recorded readings alone — no line, no ADC, no bus — and the verdicts, the pin
commands and the frames must match (FR-CI-02). A board without those primitives skips them. Run it
only when the sample agent, its gates or the sensor contract changed on purpose; the diff is the
review:

    python scripts/gen_sensor_pack_traces.py            # rewrite the three files
    python scripts/gen_sensor_pack_traces.py --check    # exit 1 if they differ (what the test runs)

The session ids and the timestamp are fixed; everything else is what the session wrote.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures" / "traces" / "sensor-pack"
AGENT = ROOT / "fixtures" / "agents" / "rail-gate" / "agent.toml"
STEP_MS = 1000.0  # a person speaks about once a second: far apart for every max_age_ms


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, ms: float) -> None:
        self.now += ms


def analog(channel: str, value: float):
    return lambda session, clock: session.set_analog(channel, value)


def limit(level: bool):
    return lambda session, clock: session.hal.set_digital_in("limit_switch", level)


def lose_limit(session, clock) -> None:
    del session.hal._levels[
        "limit_switch"
    ]  # a line nobody set reads as a failure, not a level


def stale_adc(ms: float):
    """The ADC read finishes `ms` after its mark was taken: the fact is that old when judged."""

    def apply(session, clock) -> None:
        read = session.hal.analog_in

        def late(*args, **kwargs):
            value = read(*args, **kwargs)
            clock.advance(ms)
            return value

        session.hal.analog_in = late

    return apply


def fresh_adc(session, clock) -> None:
    session.hal.__dict__.pop("analog_in", None)  # back to the HAL's own, prompt read


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
        for tool, before in steps:
            clock.advance(STEP_MS)
            for change in before:
                change(session, clock)
            asyncio.run(session.call_tool(ToolCall(tool, {}, source="local_grammar")))
    finally:
        session.close()
    return recorder.to_trace()


def sessions() -> dict[str, dict]:
    return {
        "rail-gate-allow": record(
            "a11ce100", [("rail_report", []), ("rail_open_gate", [])]
        ),
        "rail-gate-block": record(
            "b10c0100",
            [
                ("rail_open_gate", [analog("adc0", 0.9)]),
                ("rail_open_gate", [analog("adc0", 1.8), limit(False)]),
            ],
        ),
        "rail-gate-unavailable": record(
            "c0a1e100",
            [
                ("rail_open_gate", [analog("adc0", 9.0)]),
                ("rail_open_gate", [analog("adc0", 1.8), stale_adc(501)]),
                ("rail_open_gate", [fresh_adc, lose_limit]),
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
        print(f"differs from the sample agent's sessions: {differs}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
