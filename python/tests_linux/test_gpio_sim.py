"""
LinuxHAL against real kernel GPIO lines — gpio-sim (TSK-S3-05, Q-16).

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh`:

    cd python && python -m pytest -q tests_linux

Not in `tests/`: without gpio-sim these could only skip, and no test may skip.
Here the opposite holds — a missing chip is a failure, never a skip. Line
state is read from sysfs (`sim_gpioN/value`), independently of the process
that drives the line.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from neuroedge.cli.main import app
from neuroedge.engine.trace_sink import EventLog
from neuroedge.hal.linux import LinuxHAL
from neuroedge.paths import fixtures_dir
from neuroedge.testing import assert_matches_golden, replay

PINS = ["door_lock", "porch_light", "gate_relay"]
TRACES = fixtures_dir() / "traces"


@pytest.fixture(scope="module")
def sysfs() -> Path:
    path = os.environ.get("NEUROEDGE_GPIO_SIM_SYSFS")
    assert path, "run scripts/setup_gpio_sim.sh first; it exports NEUROEDGE_GPIO_SIM_SYSFS"
    return Path(path)


def kernel_value(sysfs: Path, pin: str) -> int:
    return int((sysfs / f"sim_gpio{PINS.index(pin)}" / "value").read_text().strip())


def wait_for(sysfs: Path, pin: str, value: int, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if kernel_value(sysfs, pin) == value:
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def hal():
    hal = LinuxHAL(
        events=EventLog(target="linux", board_id="linux-rpi5"), authorize=lambda *_: None
    )
    yield hal
    hal.close()


def test_the_hal_finds_every_board_pin_on_the_virtual_chip(hal):
    assert set(hal.lines) == set(PINS)


def test_a_pulse_reaches_the_kernel_line_and_ends(hal, sysfs):
    assert kernel_value(sysfs, "door_lock") == 0
    hal.digital_out("door_lock", "pulse", 200)
    assert wait_for(sysfs, "door_lock", 1)
    assert wait_for(sysfs, "door_lock", 0), "the pulse must end after its duration"


def test_cancel_drops_the_kernel_line_at_once(hal, sysfs):
    pending = hal.digital_out("door_lock", "pulse", 30000)
    assert wait_for(sysfs, "door_lock", 1)
    pending.cancel()
    assert wait_for(sysfs, "door_lock", 0, timeout=0.2)


def test_the_default_authoriser_leaves_the_kernel_line_untouched(sysfs):
    hal = LinuxHAL()
    try:
        with pytest.raises(Exception, match="ledger|signature"):
            hal.digital_out("door_lock", "pulse", 1000, signature="forged")
        assert kernel_value(sysfs, "door_lock") == 0
    finally:
        hal.close()


@pytest.mark.parametrize("name", ["happy-path", "unverified_attempt", "network_offline"])
def test_each_canonical_trace_decides_the_same_on_linux_as_on_sim(name, sysfs):
    sim = replay(TRACES / f"{name}.json", target="sim")
    linux = replay(TRACES / f"{name}.json", target="linux")
    assert linux.verdicts == sim.verdicts
    assert linux.pin("door_lock").commands == sim.pin("door_lock").commands
    assert_matches_golden(linux, TRACES / f"{name}.json")
    assert kernel_value(sysfs, "door_lock") == 0, "replay releases the lines when it ends"


def test_verify_reaches_target_equivalence_on_sim_and_linux():
    from typer.testing import CliRunner

    result = CliRunner().invoke(app, ["verify", "--targets", "sim,linux"])
    assert result.exit_code == 0, result.output
    assert "linux" in result.output
