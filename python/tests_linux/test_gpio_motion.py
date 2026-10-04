"""
`motion.*` against real kernel GPIO lines — gpio-sim (RFC-0011 §3a, §3c, TSK-I2a-05).

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh`:

    cd python && python -m pytest -q tests_linux

What a CI machine can show is the half that is a GPIO line: the driver's **enable line**
(`motor_en`, `servo_en`) held by the real supervisor process, read back from sysfs
(`sim_gpioN/value`) independently of the process that drives it. The PWM is a fake `/sys/class/pwm`
tree in a temporary directory: the runner has no PWM controller and no motor. What is **not**
shown here, and needs the stage-B rig (RFC-0011 §3f): that a duty cycle turns a motor, that a pulse
moves a servo, that the driver really cuts power when its enable line drops, and the
crash-safe tests on the real board (SIGKILL, power loss mid-command).

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
from neuroedge.hal.linux import LinuxHAL

LINES = [
    "door_lock",
    "porch_light",
    "gate_relay",
    "door_contact_raw",
    "limit_switch",
    "fan_en",
    "motor_en",
    "servo_en",
]
SOURCES = {"wheel_left": "pwmchip0/0", "gripper": "pwmchip0/1"}


@pytest.fixture(scope="module")
def sysfs() -> Path:
    path = os.environ.get("NEUROEDGE_GPIO_SIM_SYSFS")
    assert path, "run scripts/setup_gpio_sim.sh first; it exports NEUROEDGE_GPIO_SIM_SYSFS"
    return Path(path)


@pytest.fixture
def pwm_root(tmp_path) -> Path:
    """`/sys` with the PWM channels already exported: the runner has no PWM controller."""
    root = tmp_path / "sys"
    chip = root / "class" / "pwm" / "pwmchip0"
    chip.mkdir(parents=True)
    (chip / "export").write_text("")
    (chip / "npwm").write_text("2\n")
    for index in (0, 1):
        (chip / f"pwm{index}").mkdir()
        for name in ("period", "duty_cycle", "enable"):
            (chip / f"pwm{index}" / name).write_text("0\n")
    return root


def kernel_value(sysfs: Path, pin: str) -> int:
    return int((sysfs / f"sim_gpio{LINES.index(pin)}" / "value").read_text().strip())


def wait_for(sysfs: Path, pin: str, value: int, timeout: float = 5.0) -> float | None:
    """Seconds until the kernel shows `pin` at `value`, or None when it never does."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if kernel_value(sysfs, pin) == value:
            return time.monotonic() - start
        time.sleep(0.005)
    return None


def open_hal(pwm_root, **kwargs) -> LinuxHAL:
    return LinuxHAL(
        events=EventLog(target="linux", board_id="linux-rpi5"),
        authorize=lambda *_: None,
        motion=["wheel_left", "gripper"],
        motion_sources=SOURCES,
        sysfs_root=pwm_root,
        **kwargs,
    )


def test_a_command_raises_the_enable_line_and_the_lease_drops_it(sysfs, pwm_root):
    hal = open_hal(pwm_root)
    try:
        assert kernel_value(sysfs, "motor_en") == 0
        hal.motion_motor("wheel_left", 0.3, called_from="test")
        assert wait_for(sysfs, "motor_en", 1, timeout=2), "the supervisor raised the driver"
        took = wait_for(sysfs, "motor_en", 0, timeout=3)  # the board's lease is 200 ms
        assert took is not None and took < 1.5, "nobody renewed it: the kernel line went down"
    finally:
        hal.close()


def test_the_servos_hold_keeps_its_enable_line_up_until_max_hold_ms(sysfs, pwm_root):
    hal = open_hal(pwm_root)
    try:
        hal.motion_servo("gripper", 45, called_from="test")
        assert wait_for(sysfs, "servo_en", 1, timeout=2)
        time.sleep(0.5)  # the 200 ms lease is over: the servo declares `hold` (max_hold_ms 2000)
        assert kernel_value(sysfs, "servo_en") == 1
        assert wait_for(sysfs, "servo_en", 0, timeout=4) is not None, "the hold ended: power off"
    finally:
        hal.close()


def test_a_barge_in_drops_the_line_at_once_and_close_leaves_every_driver_down(sysfs, pwm_root):
    hal = open_hal(pwm_root)
    try:
        hal.motion_motor("wheel_left", 0.3, called_from="test")
        assert wait_for(sysfs, "motor_en", 1, timeout=2)
        hal.motion_barge_in()
        assert wait_for(sysfs, "motor_en", 0, timeout=0.3) is not None
    finally:
        hal.close()
    assert kernel_value(sysfs, "motor_en") == 0 and kernel_value(sysfs, "servo_en") == 0


def test_the_enable_line_is_not_a_digital_out_pin_an_agent_can_reach(sysfs, pwm_root):
    hal = open_hal(pwm_root)
    try:
        with pytest.raises(Exception, match="enable line"):
            hal.digital_out("motor_en", "on", called_from="test")
        assert kernel_value(sysfs, "motor_en") == 0
    finally:
        hal.close()


# A runtime in a process of its own, the supervisor holding its lines: the test freezes it.
RUNTIME = textwrap.dedent(
    """
    import sys
    from neuroedge.engine.trace_sink import EventLog
    from neuroedge.hal.linux import LinuxHAL

    hal = LinuxHAL(
        authorize=lambda *args: None, events=EventLog(),
        supervise=True, supervisor_options={"heartbeat_timeout_ms": 500},
        motion=["wheel_left"], motion_sources={"wheel_left": "pwmchip0/0"}, sysfs_root=sys.argv[1],
    )
    hal.motion_motor("wheel_left", 0.3)
    print("moving", flush=True)
    sys.stdin.readline()
    hal.close()
    print("closed", flush=True)
    """
)


def test_a_runtime_stopped_with_sigstop_while_a_motor_runs_loses_its_driver(sysfs, pwm_root):
    """RFC-0011 §7 (the part a runner can show): the enable line drops within heartbeat + margin."""
    runtime = subprocess.Popen(
        [sys.executable, "-c", RUNTIME, str(pwm_root)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert runtime.stdout.readline().strip() == "moving"
        assert wait_for(sysfs, "motor_en", 1, timeout=3)
        os.kill(runtime.pid, signal.SIGSTOP)  # no lease timer of the runtime runs from here on
        took = wait_for(sysfs, "motor_en", 0, timeout=5)
        assert took is not None and took <= (500 + 50) / 1000 + 1.5, took
        os.kill(runtime.pid, signal.SIGCONT)
        runtime.stdin.write("go\n")
        runtime.stdin.flush()
        assert runtime.stdout.readline().strip() == "closed"
        assert runtime.wait(10) == 0
    finally:
        if runtime.poll() is None:
            os.kill(runtime.pid, signal.SIGCONT)
            runtime.kill()
            runtime.wait()
    assert kernel_value(sysfs, "motor_en") == 0


def test_a_runtime_that_dies_loses_its_driver_because_the_pipe_closes(sysfs, pwm_root):
    runtime = subprocess.Popen(
        [sys.executable, "-c", RUNTIME, str(pwm_root)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert runtime.stdout.readline().strip() == "moving"
        assert wait_for(sysfs, "motor_en", 1, timeout=3)
        runtime.kill()  # SIGKILL: no handler runs, no timer fires
        runtime.wait()
        assert wait_for(sysfs, "motor_en", 0, timeout=5) is not None
    finally:
        runtime.kill()
