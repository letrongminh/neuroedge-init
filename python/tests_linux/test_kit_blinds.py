"""
The blinds kit on a real kernel (TSK-I2b-02): the servo's enable line on gpio-sim.

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh`:

    cd python && python -m pytest -q tests_linux

`servo_en` is a gpio-sim line, read from sysfs independently of the process that drives it. The PWM is a
fake `/sys/class/pwm` tree in a temporary directory: the runner has no PWM controller and no servo. What
is not shown here — that a pulse tilts the slats, that the driver cuts power when its enable line drops —
needs the stage-B rig (RFC-0011 §3f; `docs/user/kit-rem-cua.md`, "Chưa kiểm").

NOTE: written without a kernel at hand (the author's machine is not Linux); the same scenarios against
an in-memory gpiod are `python/tests/test_kits.py`. If a gpio-sim detail differs, CI shows it here.
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

import pytest

from neuroedge.errors import BoardCapabilityError
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
    return root


@pytest.fixture
def wired(monkeypatch):
    monkeypatch.setenv(MOTION_ENV, "gripper=pwmchip0/1")


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


@pytest.mark.usefixtures("fresh_actions", "wired")
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


@pytest.mark.usefixtures("fresh_actions", "wired")
@pytest.mark.parametrize(
    ("facts", "text"),
    [
        ({"estop_released": False}, "mở rèm"),
        ({"device_fault_free": False}, "mở rèm"),
        ({"path_clear": False}, "đóng rèm"),
    ],
    ids=["emergency stop", "driver fault", "a hand in the slot"],
)
def test_a_blocked_command_never_raises_the_enable_line(sysfs, pwm_root, facts, text):
    session = SimSession.load(
        AGENT, target="linux", facts=facts, target_options={"sysfs_root": pwm_root}
    )
    try:
        turn = say(session, text)
        assert turn.result is not None and turn.result.blocked
        assert not wait_for(sysfs, "servo_en", 1, timeout=0.3), "a BLOCK never powers the servo"
    finally:
        session.close()


@pytest.mark.usefixtures("fresh_actions")
def test_without_a_wired_pwm_the_session_is_refused_before_any_line_moves(
    sysfs, pwm_root, monkeypatch
):
    monkeypatch.delenv(MOTION_ENV, raising=False)
    with pytest.raises(BoardCapabilityError, match="no PWM channel is wired"):
        SimSession.load(AGENT, target="linux", target_options={"sysfs_root": pwm_root})
    assert kernel_value(sysfs, "servo_en") == 0


@pytest.mark.parametrize("name", ["blinds-allow", "blinds-block"])
def test_the_golden_traces_replay_on_the_kernel_lines_as_recorded(name, sysfs):
    path = GOLDEN / f"{name}.json"
    linux = replay(path, target="linux", agent=AGENT, board_id="linux-rpi5")
    assert linux.verdicts == linux.recorded_verdicts
    assert linux.warnings == [] and linux.divergences == []
    assert_matches_golden(linux, path)
    assert kernel_value(sysfs, "servo_en") == 0, "replay releases the lines when it ends"
