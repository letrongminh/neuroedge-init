#!/usr/bin/env python3
"""
The corpus of fine control — PWM and its read-back (TSK-W1-01, RFC-0010, RFC-0013 §3f item 7):
`fixtures/traces/fine-control/*.json`.

Sessions of the sample agent `fixtures/agents/fan-pwm` on `sim-rpi5`, recorded on a fake clock so
they are the same every time:

    fan-pwm-allow.json        the fan runs at 0.5 duty / 1 kHz for 5 s and is stopped: ALLOW, ALLOW
    fan-pwm-block.json        a duty over the gate's narrowed 0.6, a frequency under its 200 Hz: BLOCK
                              `argument_out_of_range` twice; then a second run while the first still
                              holds the channel is refused by the envelope (`already_on`)
    fan-pwm-measured.json     `fan_assist` is gated by the fan's *measured* duty: 0.1 ⇒ ALLOW, 0.6 ⇒ BLOCK
                              `condition_not_met`
    fan-pwm-unavailable.json  the read-back fails ⇒ BLOCK `criterion_unavailable`
    fan-pwm-commanded.json    a board with no read-back: the duty is only ever commanded, never reaches
                              the gate ⇒ BLOCK `criterion_unavailable` (RFC-0010 §9.12)

The reference boards declare no `digital_out.feedback` yet, so the two sessions that need a
*measured* duty are recorded on a rig whose `sim-rpi5` declares one (the generator edits a private
copy of `boards/`, nothing in the repository). They carry `board_id: sim-rpi5` all the same:
replay never reads the controller, it feeds back the facts the trace recorded.

`neuroedge verify` replays each on every reference board that declares a PWM channel (`digital_out.pwm`),
from the recorded facts alone — no controller, no line — and the verdicts, the pin commands (frequency
and duty included) and the envelope refusals must match (FR-CI-02). A board without a PWM channel skips
them. Run it only when the sample agent, its gates or the PWM contract changed on purpose; the diff is
the review:

    python scripts/gen_fine_control_traces.py            # rewrite the files
    python scripts/gen_fine_control_traces.py --check    # exit 1 if they differ (what the test runs)

The session ids and the timestamp are fixed; everything else is what the session wrote.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures" / "traces" / "fine-control"
AGENT = ROOT / "fixtures" / "agents" / "fan-pwm" / "agent.toml"
STEP_MS = 1000.0
RUN = {"duty": 0.5, "frequency_hz": 1000, "duration_ms": 5000}


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, ms: float) -> None:
        self.now += ms


def tool(name: str, **arguments):
    """One tool call. An envelope refusal is part of the session, not a crash of the recording."""

    def apply(session, clock) -> None:
        from neuroedge.actions.tools import ToolCall
        from neuroedge.errors import EnvelopeRefusedError

        with contextlib.suppress(EnvelopeRefusedError):
            asyncio.run(session.call_tool(ToolCall(name, arguments, source="mcp")))

    return apply


def feedback(**readback):
    return lambda session, clock: session.hal.set_feedback("fan", **readback)


def wait(ms: float):
    return lambda session, clock: clock.advance(ms)


@contextlib.contextmanager
def rig_with_readback():
    """`boards/` with a read-back declared for the fan, in a private copy: the rig of a measured duty."""
    import neuroedge.hal.board as board

    original = board.boards_dir
    with tempfile.TemporaryDirectory() as tmp:
        boards = Path(tmp) / "boards"
        shutil.copytree(ROOT / "boards", boards)
        path = boards / "sim-rpi5.toml"
        text = path.read_text(encoding="utf-8")
        marker = "[capabilities.digital_in]"
        assert marker in text
        path.write_text(
            text.replace(
                marker, f'[capabilities.digital_out.feedback]\npins = ["fan"]\n\n{marker}', 1
            ),
            encoding="utf-8",
        )
        board.boards_dir = lambda: boards
        try:
            yield
        finally:
            board.boards_dir = original


def record(session_id: str, steps, *, readback: bool = False) -> dict:
    from neuroedge.sim import SimSession
    from neuroedge.testing.recorder import TraceRecorder

    clock = Clock()
    recorder = TraceRecorder(
        clock=clock, target="sim", board_id="sim-rpi5", session_id=f"sess_{session_id}"
    )
    recorder.metadata["timestamp_utc"] = "2026-10-03T12:00:00Z"
    with rig_with_readback() if readback else contextlib.nullcontext():
        session = SimSession.load(AGENT, board_id="sim-rpi5", clock=clock, events=recorder)
        try:
            for step in steps:
                clock.advance(STEP_MS)
                step(session, clock)
        finally:
            session.close()
    return recorder.to_trace()


def sessions() -> dict[str, dict]:
    return {
        "fan-pwm-allow": record(
            "a11ce200", [tool("fan_run", **RUN), tool("fan_stop")]
        ),
        "fan-pwm-block": record(
            "b10c0200",
            [
                tool("fan_run", duty=0.7, frequency_hz=1000, duration_ms=5000),
                tool("fan_run", duty=0.4, frequency_hz=150, duration_ms=5000),
                tool("fan_run", **RUN),
                tool("fan_run", **RUN),  # the channel is still running the first one
                tool("fan_stop"),
            ],
        ),
        "fan-pwm-measured": record(
            "d00d0200",
            [
                feedback(duty=0.1),
                tool("fan_assist"),
                wait(5000),
                feedback(duty=0.6),
                tool("fan_assist"),
            ],
            readback=True,
        ),
        "fan-pwm-unavailable": record(
            "c0a1e200",
            [feedback(fail="the PWM controller does not answer"), tool("fan_assist")],
            readback=True,
        ),
        "fan-pwm-commanded": record("c0de0200", [tool("fan_run", **RUN), tool("fan_assist")]),
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
        stale = sorted(p.name for p in OUT.glob("*.json") if p.stem not in made)
        if stale:
            differs += stale
    if differs:
        print(f"differs from the sample agent's sessions: {differs}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
