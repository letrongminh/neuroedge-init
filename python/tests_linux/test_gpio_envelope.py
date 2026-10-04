"""
The safety envelope against real kernel GPIO lines — gpio-sim (RFC-0007 §3d, TSK-N2-02, TSK-N2-03).

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh`:

    cd python && python -m pytest -q tests_linux

The logic is `tests/test_envelope.py`, `tests/test_hal_linux_envelope.py` and
`tests/test_supervisor.py` (the same supervisor process on a stand-in gpiod). What only a kernel
can show is here: line state is read from sysfs (`sim_gpioN/value`), independently of the process
that drives the line, and a stopped or terminated runtime is a real process.

Not in `tests/`: without gpio-sim these could only skip, and no test may skip.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from neuroedge.engine.trace_sink import EventLog
from neuroedge.hal.envelope import EnvelopeLimits, SafetyEnvelope
from neuroedge.hal.linux import LinuxHAL
from neuroedge.paths import fixtures_dir

PINS = ["door_lock", "porch_light", "gate_relay"]
DRIVEWAY = fixtures_dir() / "agents" / "driveway" / "agent.toml"


@pytest.fixture(scope="module")
def sysfs() -> Path:
    path = os.environ.get("NEUROEDGE_GPIO_SIM_SYSFS")
    assert path, "run scripts/setup_gpio_sim.sh first; it exports NEUROEDGE_GPIO_SIM_SYSFS"
    return Path(path)


def kernel_value(sysfs: Path, pin: str) -> int:
    return int((sysfs / f"sim_gpio{PINS.index(pin)}" / "value").read_text().strip())


def wait_for(sysfs: Path, pin: str, value: int, timeout: float = 5.0) -> float | None:
    """Seconds until the kernel shows `pin` at `value`, or None when it never does."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if kernel_value(sysfs, pin) == value:
            return time.monotonic() - start
        time.sleep(0.005)
    return None


def neuroedge(*args: str) -> subprocess.Popen:
    """The real command in a child process: it holds the lines, the test reads sysfs."""
    return subprocess.Popen(
        [sys.executable, "-m", "neuroedge", *args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ, "NO_COLOR": "1", "COLUMNS": "200"},
    )


def test_the_hal_turns_an_on_off_at_max_continuous_ms_on_a_real_line(sysfs):
    limits = EnvelopeLimits(
        window_s=60, max_on_ms_per_window=60_000, min_interval_ms=0, max_continuous_ms=300
    )
    events = EventLog(target="linux", board_id="linux-rpi5")
    hal = LinuxHAL(
        events=events,
        authorize=lambda *_: None,
        envelope=SafetyEnvelope({"porch_light": limits}, virtual=False),
    )
    try:
        hal.digital_out("porch_light", "on")  # no duration: the envelope's cap is the end
        assert wait_for(sysfs, "porch_light", 1, timeout=2)
        took = wait_for(sysfs, "porch_light", 0, timeout=3)
        assert took is not None and took < 1.5, "the kernel line went down by the cap"
        # The line goes down first, then the auto-off is recorded (the safe state never
        # waits on the log): wait for the record, then it is exact.
        deadline = time.monotonic() + 2
        while "cause" not in events.of_type("actuator_command")[-1] and time.monotonic() < deadline:
            time.sleep(0.01)
        assert events.of_type("actuator_command")[-1]["cause"] == "max_continuous_ms"
    finally:
        hal.close()


# A runtime in a process of its own, with the supervisor holding its lines: the test freezes it.
RUNTIME = textwrap.dedent(
    """
    import sys, time
    from neuroedge.engine.trace_sink import EventLog
    from neuroedge.hal.board import load_board_by_id
    from neuroedge.hal.envelope import SafetyEnvelope
    from neuroedge.hal.linux import LinuxHAL

    board = load_board_by_id("linux-rpi5")
    hal = LinuxHAL(
        board, authorize=lambda *args: None, events=EventLog(),
        envelope=SafetyEnvelope.for_board(board, virtual=False),
        supervise=True, supervisor_options={"heartbeat_timeout_ms": 500},
    )
    hal.digital_out("porch_light", "on")  # reserved 600 s: only the supervisor ends it soon
    print("on", flush=True)
    sys.stdin.readline()
    hal.close()
    print("closed", flush=True)
    """
)


def test_a_runtime_stopped_with_sigstop_while_an_actuator_is_on_loses_the_line(sysfs):
    """RFC-0007 §7: the line drops within the heartbeat timeout plus a margin (500 ms + 50 ms)."""
    runtime = subprocess.Popen(
        [sys.executable, "-c", RUNTIME],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert runtime.stdout.readline().strip() == "on"
        assert wait_for(sysfs, "porch_light", 1, timeout=5), "the actuator is on"
        os.kill(runtime.pid, signal.SIGSTOP)
        took = wait_for(sysfs, "porch_light", 0, timeout=10)
        assert took is not None, "a frozen runtime must not leave the line on"
        assert took <= (500 + 50) / 1000 + 2.0, f"dropped after {took:.2f} s"
        os.kill(runtime.pid, signal.SIGCONT)
        runtime.stdin.write("go\n")
        runtime.stdin.flush()
        assert runtime.stdout.readline().strip() == "closed"
        assert runtime.wait(15) == 0
    finally:
        if runtime.poll() is None:
            os.kill(runtime.pid, signal.SIGCONT)
            runtime.kill()
            runtime.wait()
    assert kernel_value(sysfs, "porch_light") == 0


def test_a_runtime_that_is_killed_loses_its_lines_with_the_pipe(sysfs):
    runtime = subprocess.Popen(
        [sys.executable, "-c", RUNTIME],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert runtime.stdout.readline().strip() == "on"
        assert wait_for(sysfs, "porch_light", 1, timeout=5)
        runtime.kill()  # SIGKILL: no handler, no timer
        runtime.wait()
        assert wait_for(sysfs, "porch_light", 0, timeout=5) is not None
    finally:
        runtime.kill()


def test_sigterm_in_the_middle_of_a_pulse_drops_the_line(sysfs):
    """Exit criterion N2.2: the session leaves through `hal.close()` while the door pulse runs."""
    child = neuroedge("run", "--target", "linux", "--agent", str(DRIVEWAY))
    try:
        child.stdin.write("mở cửa ngách\n")  # buzz_in: the door_lock pulses for 5 s
        child.stdin.flush()
        assert wait_for(sysfs, "door_lock", 1, timeout=10), "the pulse is on the line"
        child.terminate()
        output, _ = child.communicate(timeout=10)
    finally:
        child.kill()
    assert child.returncode == 143, output
    assert kernel_value(sysfs, "door_lock") == 0, "SIGTERM mid-pulse: the line is down"


def test_a_second_session_after_a_restart_waits_out_min_interval_before_it_turns_a_pin_on(sysfs):
    """RFC-0007 §7: the record outlives the process, and a restart starts every pin's wait."""
    first = neuroedge("run", "--target", "linux", "--agent", str(DRIVEWAY))
    out, _ = first.communicate("bật đèn hiên\nexit\n", timeout=30)
    assert first.returncode == 0, out
    assert kernel_value(sysfs, "porch_light") == 0

    restarted = neuroedge("run", "--target", "linux", "--agent", str(DRIVEWAY))
    out, _ = restarted.communicate("bật đèn hiên\nexit\n", timeout=30)
    assert "NE1003" in out and "min_interval_ms" in out, out
    assert kernel_value(sysfs, "porch_light") == 0, "the refused command never reached the line"
