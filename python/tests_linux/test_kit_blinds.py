"""
The blinds kit on a real kernel (TSK-I2b-02): the servo's enable line on gpio-sim.

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh` (the lines `servo_en` and `limit_switch`) and
`scripts/setup_i2c_stub.sh` (an `ads7828` bound to its hwmon driver at 0x4a, the current-sense reading):

    cd python && python -m pytest -q tests_linux

`servo_en` is a gpio-sim line, read from sysfs independently of the process that drives it; the emergency
stop is the gpio-sim line `limit_switch` whose `pull` is its level, and the current-sense volts are the ADC's
channel 0 read through hwmon (codes as in `test_rail_gate.py`: 656 is 0.4 V, 1639 is 1.0 V). The PWM is a
fake `/sys/class/pwm` tree in a temporary directory: the runner has no PWM controller and no servo. What
is not shown here — that a pulse tilts the slats, that the driver cuts power when its enable line drops —
needs the stage-B rig (RFC-0011 §3f; `docs/user/kit-rem-cua.md`, "Chưa kiểm").

These load the canonical agent in place (no copy), so none uses `fresh_actions`: clearing the action
registry while the agent's module is already imported leaves it with no `@action` (NE3003 at build).

NOTE: written without a kernel at hand (the author's machine is not Linux); the same scenarios against
an in-memory gpiod are `python/tests/test_kits.py`. If a gpio-sim detail differs, CI shows it here.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from pathlib import Path

import pytest

from neuroedge.errors import BoardCapabilityError
from neuroedge.hal.linux import ANALOG_ENV
from neuroedge.hal.motion_pwm import MOTION_ENV
from neuroedge.paths import fixtures_dir
from neuroedge.sim import SimSession
from neuroedge.testing import assert_matches_golden, replay

AGENT = fixtures_dir() / "agents" / "blinds" / "agent.toml"
GOLDEN = fixtures_dir() / "traces" / "kits"
# The lines in the order `scripts/setup_gpio_sim.sh` creates them: sim_gpioN is the N-th.
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
    # One sysfs root serves the PWM and the ADC (`LinuxHAL(sysfs_root=...)`): the PWM tree is fake, the
    # ADS7828 is the kernel's, so the root's hwmon class is the real one.
    (root / "class" / "hwmon").symlink_to("/sys/class/hwmon")
    return root


HEALTHY_CODE, OVERLOADED_CODE = (
    656,
    1639,
)  # 0.4 V and 1.0 V on the channel (the gate wants <= 0.8 V)


def env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"{name} is not set; run the setup script that exports it first"
    return value


def set_adc(code: int) -> None:
    """The 12-bit conversion result of channel 0 (an SMBus word is little-endian)."""
    word = ((code & 0xFF) << 8) | (code >> 8)
    subprocess.run(
        ["i2cset", "-f", "-y", env("NEUROEDGE_I2C_STUB_BUS"), "0x4a", "0x8c", hex(word), "w"],
        check=True,
    )


def pull(sysfs: Path, pin: str, high: bool) -> None:
    """What the emergency-stop contact does: gpio-sim's `pull` is the level an input reads."""
    (sysfs / f"sim_gpio{LINES.index(pin)}" / "pull").write_text("pull-up" if high else "pull-down")


@pytest.fixture
def wired(monkeypatch, sysfs):
    """The blinds rig: PWM wired, emergency stop released, a healthy current-sense reading."""
    monkeypatch.setenv(MOTION_ENV, "gripper=pwmchip0/1")
    monkeypatch.setenv(ANALOG_ENV, f"adc0=hwmon:ads7828@{env('NEUROEDGE_ADS7828_DEVICE')}/in0")
    pull(sysfs, "limit_switch", True)
    set_adc(HEALTHY_CODE)
    yield
    pull(sysfs, "limit_switch", True)
    set_adc(0x800)


def kernel_value(sysfs: Path, pin: str) -> int:
    return int((sysfs / f"sim_gpio{LINES.index(pin)}" / "value").read_text().strip())


def wait_for(sysfs: Path, pin: str, value: int, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if kernel_value(sysfs, pin) == value:
            return True
        time.sleep(0.01)
    return False


def say(session: SimSession, text: str):
    return asyncio.run(session.handle(text))


@pytest.mark.usefixtures("wired")
def test_an_allowed_open_raises_the_enable_line_and_the_lease_drops_it(sysfs, pwm_root):
    session = SimSession.load(AGENT, target="linux", target_options={"sysfs_root": pwm_root})
    try:
        assert kernel_value(sysfs, "servo_en") == 0
        assert say(session, "mở rèm").allowed
        assert wait_for(sysfs, "servo_en", 1), "the supervisor raised the driver"
        # nobody renews the 200 ms lease: the servo holds (max_hold_ms 2000), then power goes off
        assert wait_for(sysfs, "servo_en", 0, timeout=5.0), "the hold ended: power off"
    finally:
        session.close()
    assert kernel_value(sysfs, "servo_en") == 0, "the session ends with the driver down"


@pytest.mark.usefixtures("wired")
@pytest.mark.parametrize(
    ("trouble", "text", "criterion"),
    [
        ("estop", "mở rèm", "estop_released"),
        ("overload", "mở rèm", "motor_current_sense"),
        ("hand", "đóng rèm", "path_clear"),
    ],
    ids=["emergency stop", "too much current", "a hand in the slot"],
)
def test_a_blocked_command_never_raises_the_enable_line(sysfs, pwm_root, trouble, text, criterion):
    facts = {"path_clear": False} if trouble == "hand" else {}
    if trouble == "estop":
        pull(sysfs, "limit_switch", False)
    if trouble == "overload":
        set_adc(OVERLOADED_CODE)
    session = SimSession.load(
        AGENT, target="linux", facts=facts, target_options={"sysfs_root": pwm_root}
    )
    try:
        turn = say(session, text)
        assert turn.result is not None and turn.result.blocked
        assert turn.result.gate.failed_criterion == criterion
        assert not wait_for(sysfs, "servo_en", 1, timeout=0.3), "a BLOCK never powers the servo"
    finally:
        session.close()


def test_without_a_wired_pwm_the_session_is_refused_before_any_line_moves(
    sysfs, pwm_root, monkeypatch
):
    monkeypatch.delenv(MOTION_ENV, raising=False)
    with pytest.raises(BoardCapabilityError, match="no PWM channel is wired"):
        SimSession.load(AGENT, target="linux", target_options={"sysfs_root": pwm_root})
    assert kernel_value(sysfs, "servo_en") == 0


@pytest.mark.parametrize("name", ["blinds-allow", "blinds-block"])
@pytest.mark.usefixtures("wired")
def test_the_golden_traces_replay_on_the_kernel_lines_as_recorded(name, sysfs):
    path = GOLDEN / f"{name}.json"
    linux = replay(path, target="linux", agent=AGENT, board_id="linux-rpi5")
    assert linux.verdicts == linux.recorded_verdicts
    assert linux.warnings == [] and linux.divergences == []
    assert_matches_golden(linux, path)
    assert kernel_value(sysfs, "servo_en") == 0, "replay releases the lines when it ends"
