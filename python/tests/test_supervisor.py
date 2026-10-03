"""
TSK-N2-02 — out-of-process supervision of the actuator lines on `linux` (RFC-0007 §3d, §7).

`LineSupervisor` is the logic and is tested with a fake clock. The processes are real: a
runtime child and the supervisor it starts, on the stand-in gpiod of `tests/fake_gpiod`, whose
line values land in a file the test reads. The same with real kernel lines (gpio-sim) is
`tests_linux/test_gpio_envelope.py`.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from neuroedge.errors import BoardCapabilityError
from neuroedge.hal.supervisor import (
    HEARTBEAT_TIMEOUT_MS,
    POLL_MARGIN_MS,
    LineSupervisor,
    SupervisorClient,
)

FAKE_GPIOD = str(Path(__file__).parent / "fake_gpiod")
LINES = ["door_lock", "porch_light", "gate_relay"]


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class Lines:
    """What `LineSupervisor` drives in a unit test: a dict, and a line that can refuse to move."""

    def __init__(self) -> None:
        self.values: dict[str, bool] = {}
        self.stuck: set[str] = set()

    def __call__(self, pin: str, active: bool) -> None:
        if pin in self.stuck and not active:
            raise OSError(5, "I/O error")
        self.values[pin] = active


def supervisor(timeout_ms: float = 1000.0):
    clock, lines = Clock(), Lines()
    return LineSupervisor(lines, clock=clock, heartbeat_timeout_ms=timeout_ms), lines, clock


# --- the logic ------------------------------------------------------------------------


def test_a_line_goes_off_at_its_deadline_even_when_the_runtime_keeps_beating():
    sup, lines, clock = supervisor()
    sup.command("porch_light", True, limit_ms=4_000)
    for _ in range(5):
        clock.now += 800
        sup.beat()
        sup.tick()
    assert lines.values["porch_light"] is False
    assert sup.take_dropped() == [{"pin": "porch_light", "cause": "deadline"}]
    assert sup.take_dropped() == [], "a drop is reported once"


def test_a_frozen_runtime_loses_every_line_that_is_on_within_the_heartbeat_timeout():
    sup, lines, clock = supervisor(timeout_ms=1_000)
    sup.command("porch_light", True, limit_ms=600_000)
    sup.command("door_lock", True)  # no deadline: only the heartbeat watches it
    clock.now += 999
    sup.tick()
    assert lines.values == {"porch_light": True, "door_lock": True}
    clock.now += 1
    sup.tick()
    assert lines.values == {"porch_light": False, "door_lock": False}
    assert {d["cause"] for d in sup.take_dropped()} == {"heartbeat"}


def test_a_beat_keeps_the_lines_and_a_silent_runtime_with_nothing_on_is_left_alone():
    sup, lines, clock = supervisor(timeout_ms=1_000)
    clock.now += 10_000
    sup.tick()  # nothing is on: nothing to drop
    assert sup.next_due_ms() is None
    sup.command("porch_light", True)
    for _ in range(10):
        clock.now += 900
        sup.beat()
        sup.tick()
    assert lines.values["porch_light"] is True


def test_off_is_always_carried_out_and_clears_the_deadline():
    sup, lines, clock = supervisor()
    sup.command("porch_light", True, limit_ms=1_000)
    clock.now += 5_000  # long past: the runtime that asks for off is late, not refused
    sup.command("porch_light", False)
    assert lines.values["porch_light"] is False and not sup.is_on("porch_light")
    sup.tick()
    assert sup.take_dropped() == [], "an off the runtime asked for is not a drop"


def test_a_line_that_will_not_drop_is_retried_and_stays_on_the_books():
    sup, lines, clock = supervisor()
    sup.command("porch_light", True, limit_ms=100)
    lines.stuck.add("porch_light")
    clock.now += 200
    sup.tick()
    assert sup.is_on("porch_light") and sup.take_dropped() == []
    assert sup.next_due_ms() == 0.0
    lines.stuck.clear()
    sup.tick()
    assert not sup.is_on("porch_light")


def test_next_due_is_the_earliest_of_the_deadlines_and_the_heartbeat():
    sup, _, clock = supervisor(timeout_ms=1_000)
    sup.command("porch_light", True, limit_ms=300)
    sup.command("door_lock", True, limit_ms=5_000)
    assert sup.next_due_ms() == 300
    clock.now += 100
    assert sup.next_due_ms() == 200


def test_closing_drops_what_is_on():
    sup, lines, _ = supervisor()
    sup.command("porch_light", True)
    sup.drop_all("close")
    assert lines.values["porch_light"] is False
    assert sup.take_dropped() == [{"pin": "porch_light", "cause": "close"}]


# --- real processes on the fake gpiod ----------------------------------------------------


@pytest.fixture
def rig(tmp_path):
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    state = tmp_path / "state.json"
    env = {
        "PYTHONPATH": FAKE_GPIOD + os.pathsep + os.environ.get("PYTHONPATH", ""),
        "FAKE_GPIOD_STATE": str(state),
        "FAKE_GPIOD_LINES": json.dumps({str(chip): LINES}),
    }

    def value(pin: str) -> int | None:
        try:
            return json.loads(state.read_text(encoding="utf-8")).get(f"{chip}:{LINES.index(pin)}")
        except (FileNotFoundError, ValueError):
            return None

    return {"chip": str(chip), "env": env, "value": value, "tmp": tmp_path}


def wait_for(condition, timeout_s: float, what: str) -> float:
    """Seconds until `condition()` held; fails when it never does."""
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        if condition():
            return time.monotonic() - start
        time.sleep(0.01)
    pytest.fail(f"{what} did not happen within {timeout_s:g} s")


RUNTIME = textwrap.dedent(
    """
    import json, sys, time
    from neuroedge.engine.trace_sink import EventLog
    from neuroedge.hal.board import load_board_by_id
    from neuroedge.hal.envelope import SafetyEnvelope
    from neuroedge.hal.linux import LinuxHAL

    events = EventLog()
    board = load_board_by_id("linux-rpi5")
    hal = LinuxHAL(
        board, chip_glob=sys.argv[1], authorize=lambda *args: None, events=events,
        envelope=SafetyEnvelope.for_board(board, virtual=False),
        supervise=True, supervisor_options={"heartbeat_timeout_ms": 400},
    )
    hal.digital_out("porch_light", "on")  # reserved 600 s: only the supervisor can end it soon
    print("on", flush=True)
    sys.stdin.readline()  # the test froze and resumed this process; now let it be told
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not [
        e for e in events.of_type("actuator_command") if "cause" in e
    ]:
        time.sleep(0.02)
    print(json.dumps(events.of_type("actuator_command")), flush=True)
    hal.close()
    print("closed", flush=True)
    """
)


def start_runtime(rig):
    return subprocess.Popen(
        [sys.executable, "-c", RUNTIME, rig["chip"] + "*"],
        env={**os.environ, **rig["env"]},
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )


def test_a_runtime_stopped_with_sigstop_while_a_line_is_on_loses_the_line(rig):
    """RFC-0007 §7: SIGSTOP on the runtime, an actuator on => the line drops in time + margin."""
    runtime = start_runtime(rig)
    try:
        assert runtime.stdout.readline().strip() == "on"
        wait_for(lambda: rig["value"]("porch_light") == 1, 5, "the line going on")
        os.kill(runtime.pid, signal.SIGSTOP)
        # the declared limit is the heartbeat timeout (400 ms here) plus the supervisor's
        # polling margin; a loaded CI machine gets a generous allowance on top
        took = wait_for(lambda: rig["value"]("porch_light") == 0, 5, "the line dropping")
        assert took <= (400 + POLL_MARGIN_MS) / 1000 + 1.5, took
        os.kill(runtime.pid, signal.SIGCONT)
        runtime.stdin.write("go\n")
        runtime.stdin.flush()
        commands = json.loads(runtime.stdout.readline())
        # when it wakes the runtime is told, and records, that the supervisor took the line
        assert commands[-1] == {
            "pin": "porch_light",
            "operation": "off",
            "duration_ms": 0,
            "cause": "supervisor_heartbeat",
        }
        assert runtime.stdout.readline().strip() == "closed"
        assert runtime.wait(10) == 0
    finally:
        if runtime.poll() is None:
            os.kill(runtime.pid, signal.SIGCONT)
            runtime.kill()
            runtime.wait()
    assert rig["value"]("porch_light") == 0


def test_a_runtime_that_dies_loses_its_lines_because_the_pipe_closes(rig):
    runtime = start_runtime(rig)
    try:
        assert runtime.stdout.readline().strip() == "on"
        wait_for(lambda: rig["value"]("porch_light") == 1, 5, "the line going on")
        runtime.kill()  # SIGKILL: no handler runs, no timer fires
        runtime.wait()
        wait_for(lambda: rig["value"]("porch_light") == 0, 5, "the line dropping")
    finally:
        runtime.kill()


def test_the_client_commands_lines_and_close_drops_them(rig):
    client = SupervisorClient(
        {"door_lock": (rig["chip"], 0), "porch_light": (rig["chip"], 1)},
        env=rig["env"],
        heartbeat_timeout_ms=HEARTBEAT_TIMEOUT_MS,
    )
    try:
        client.set("porch_light", True, limit_ms=60_000)
        assert client.get("porch_light") and not client.get("door_lock")
        assert rig["value"]("porch_light") == 1
        client.set("porch_light", False)
        assert rig["value"]("porch_light") == 0
        client.set("door_lock", True, limit_ms=60_000)
        assert rig["value"]("door_lock") == 1
    finally:
        client.close()
    assert rig["value"]("door_lock") == 0
    client.close()  # idempotent
    with pytest.raises(BoardCapabilityError, match="not running"):
        client.get("door_lock")


def test_lines_the_supervisor_cannot_take_are_an_error_and_start_no_process(rig):
    with pytest.raises(BoardCapabilityError, match="could not take the lines"):
        SupervisorClient({"door_lock": ("/dev/no-such-chip", 0)}, env=rig["env"])
