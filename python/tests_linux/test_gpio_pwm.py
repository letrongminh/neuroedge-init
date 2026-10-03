"""
The enable line of a PWM channel on real kernel GPIO lines — gpio-sim (RFC-0010 §9.2, §9.11, TSK-W1-01).

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh` (which names a line `fan_en`):

    cd python && python -m pytest -q tests_linux

What is real here is the line and the processes: the enable line is held by the supervisor
process, its level is read from sysfs (`sim_gpioN/value`) independently of whoever drives it, and
a stopped or killed runtime is a real process. What is **not** real is the PWM controller: no
runner kernel has a PWM chip (`gpio-sim` makes lines, nothing makes `/sys/class/pwm`; there is no
`pwm-sim`), so the controller is a tree of plain files in a temporary directory, exactly the
fake of `tests/test_hal_linux_pwm.py`. The hardware PWM itself is the nightly Pi 5's to show
(RFC-0010 §9.1); nothing here pretends to be it.

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

PINS = ["door_lock", "porch_light", "gate_relay", "door_contact_raw", "limit_switch", "fan_en"]


@pytest.fixture(scope="module")
def gpio_sysfs() -> Path:
    path = os.environ.get("NEUROEDGE_GPIO_SIM_SYSFS")
    assert path, "run scripts/setup_gpio_sim.sh first; it exports NEUROEDGE_GPIO_SIM_SYSFS"
    return Path(path)


@pytest.fixture
def pwm_sysfs(tmp_path) -> Path:
    """A `/sys` with one PWM chip of four channels, channel 2 exported: files, not a kernel."""
    chip = tmp_path / "sys" / "class" / "pwm" / "pwmchip0"
    (chip / "pwm2").mkdir(parents=True)
    (chip / "npwm").write_text("4\n")
    for name in ("period", "duty_cycle", "enable"):
        (chip / "pwm2" / name).write_text("0\n")
    return tmp_path / "sys"


def kernel_value(gpio_sysfs: Path, pin: str) -> int:
    return int((gpio_sysfs / f"sim_gpio{PINS.index(pin)}" / "value").read_text().strip())


def wait_for(gpio_sysfs: Path, pin: str, value: int, timeout: float = 5.0) -> float | None:
    """Seconds until the kernel shows `pin` at `value`, or None when it never does."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if kernel_value(gpio_sysfs, pin) == value:
            return time.monotonic() - start
        time.sleep(0.005)
    return None


def controller(pwm_sysfs: Path) -> dict[str, int]:
    channel = pwm_sysfs / "class" / "pwm" / "pwmchip0" / "pwm2"
    while True:
        try:
            return {n: int((channel / n).read_text()) for n in ("period", "duty_cycle", "enable")}
        except ValueError:  # the HAL's timer thread is between truncating a file and writing it
            time.sleep(0.001)


def open_hal(pwm_sysfs: Path, max_continuous_ms: int = 300) -> LinuxHAL:
    limits = EnvelopeLimits(
        window_s=60,
        max_on_ms_per_window=60_000,
        min_interval_ms=0,
        max_continuous_ms=max_continuous_ms,
    )
    return LinuxHAL(
        events=EventLog(target="linux", board_id="linux-rpi5"),
        authorize=lambda *_: None,
        envelope=SafetyEnvelope({"fan": limits}, virtual=False),
        sysfs_root=pwm_sysfs,
        pwm_channels={"fan": "pwmchip0/2"},
        needs={"pwm": ["fan"], "where": "tests_linux"},
    )


def test_the_enable_line_is_up_while_a_pwm_command_runs_and_down_when_it_ends(
    gpio_sysfs, pwm_sysfs
):
    hal = open_hal(pwm_sysfs)
    try:
        assert kernel_value(gpio_sysfs, "fan_en") == 0, "nothing is driven before a command"
        hal.digital_out("fan", "pwm", 200, "token", "tests_linux", frequency_hz=1000, duty=0.5)
        assert wait_for(gpio_sysfs, "fan_en", 1, timeout=2), "the kernel line is up"
        assert controller(pwm_sysfs) == {"period": 1_000_000, "duty_cycle": 500_000, "enable": 1}
        assert wait_for(gpio_sysfs, "fan_en", 0, timeout=5), "and dropped when the time is up"
        deadline = time.monotonic() + 2
        while controller(pwm_sysfs)["enable"] and time.monotonic() < deadline:
            time.sleep(0.01)
        assert controller(pwm_sysfs) == {"period": 1_000_000, "duty_cycle": 0, "enable": 0}
    finally:
        hal.close()
    assert kernel_value(gpio_sysfs, "fan_en") == 0


def test_off_and_close_drop_the_enable_line(gpio_sysfs, pwm_sysfs):
    hal = open_hal(pwm_sysfs, max_continuous_ms=60_000)
    hal.digital_out("fan", "pwm", 30_000, "token", "tests_linux", frequency_hz=1000, duty=0.5)
    assert wait_for(gpio_sysfs, "fan_en", 1, timeout=2)
    hal.digital_out("fan", "off")
    assert kernel_value(gpio_sysfs, "fan_en") == 0
    hal.digital_out("fan", "pwm", 30_000, "token", "tests_linux", frequency_hz=1000, duty=0.5)
    assert wait_for(gpio_sysfs, "fan_en", 1, timeout=2)
    hal.close()
    assert kernel_value(gpio_sysfs, "fan_en") == 0
    assert controller(pwm_sysfs)["enable"] == 0


RUNTIME = textwrap.dedent(
    """\
    import sys
    from neuroedge.engine.trace_sink import EventLog
    from neuroedge.hal.envelope import EnvelopeLimits, SafetyEnvelope
    from neuroedge.hal.linux import LinuxHAL

    limits = EnvelopeLimits(
        window_s=60, max_on_ms_per_window=600_000, min_interval_ms=0, max_continuous_ms=600_000
    )
    hal = LinuxHAL(
        events=EventLog(), authorize=lambda *args: None,
        envelope=SafetyEnvelope({"fan": limits}, virtual=False),
        sysfs_root=sys.argv[1], pwm_channels={"fan": "pwmchip0/2"},
        needs={"pwm": ["fan"], "where": "child"},
        supervise=True, supervisor_options={"heartbeat_timeout_ms": 500},
    )
    hal.digital_out("fan", "pwm", 300_000, "token", "child", frequency_hz=1000, duty=0.5)
    print("on", flush=True)
    sys.stdin.readline()
    hal.close()
    print("closed", flush=True)
    """
)


def spawn(pwm_sysfs: Path) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-c", RUNTIME, str(pwm_sysfs)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )


def test_a_runtime_stopped_with_sigstop_while_the_fan_runs_loses_the_enable_line(
    gpio_sysfs, pwm_sysfs
):
    """RFC-0010 §7, §9.11: the fan is unpowered within the heartbeat timeout plus a margin."""
    runtime = spawn(pwm_sysfs)
    try:
        assert runtime.stdout.readline().strip() == "on"
        assert wait_for(gpio_sysfs, "fan_en", 1, timeout=5), "the fan is powered"
        os.kill(runtime.pid, signal.SIGSTOP)
        took = wait_for(gpio_sysfs, "fan_en", 0, timeout=10)
        assert took is not None, "a frozen runtime must not leave the fan powered"
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
    assert kernel_value(gpio_sysfs, "fan_en") == 0


def test_a_runtime_that_is_killed_while_the_fan_runs_loses_the_enable_line(gpio_sysfs, pwm_sysfs):
    """RFC-0010 §9.2: SIGKILL leaves the kernel's PWM running, but the enable line is not held."""
    runtime = spawn(pwm_sysfs)
    try:
        assert runtime.stdout.readline().strip() == "on"
        assert wait_for(gpio_sysfs, "fan_en", 1, timeout=5)
        runtime.kill()  # SIGKILL: no handler, no timer
        runtime.wait()
        assert wait_for(gpio_sysfs, "fan_en", 0, timeout=5) is not None
    finally:
        runtime.kill()
    assert controller(pwm_sysfs)["enable"] == 1, (
        "the controller still runs: the line is what cuts it"
    )
