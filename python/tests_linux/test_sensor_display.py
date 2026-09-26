"""
`sensor.read` and `display` on `linux` against a real kernel (TSK-S5-09).

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh`,
`scripts/setup_i2c_stub.sh` (i2c-stub + the kernel's lm75 driver → a hwmon
device) and `scripts/setup_vfb.sh` (the kernel's virtual framebuffer):

    cd python && python -m pytest -q tests_linux

The temperature is set in the chip's register with `i2cset`; the HAL reads it back
through the lm75 driver and hwmon sysfs, as it would a sensor on a Pi. A missing
device is a failure, never a skip.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from neuroedge.engine.trace_sink import EventLog
from neuroedge.errors import BoardCapabilityError
from neuroedge.hal.framebuffer import kernel_geometry, pack_pixels
from neuroedge.hal.linux import DISPLAY_ENV, SENSORS_ENV, LinuxHAL
from neuroedge.hal.sim import SimHAL
from neuroedge.paths import fixtures_dir
from neuroedge.testing import replay

FACTORY = fixtures_dir() / "agents" / "factory-monitor" / "agent.toml"
ADDR = "0x48"


def env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"{name} is not set; run the setup script that exports it first"
    return value


@pytest.fixture(scope="module")
def lm75() -> str:
    """The kernel device the lm75 driver is bound to, e.g. 3-0048."""
    return env("NEUROEDGE_LM75_DEVICE")


def set_temperature(celsius: float) -> None:
    """Write the LM75 temperature register (9-bit, 0.5 °C steps) through i2c-stub."""
    register = (round(celsius * 2) & 0x1FF) << 7
    word = ((register & 0xFF) << 8) | (register >> 8)  # SMBus words are little-endian
    bus = env("NEUROEDGE_I2C_STUB_BUS")
    subprocess.run(["i2cset", "-f", "-y", bus, ADDR, "0x00", f"0x{word:04x}", "w"], check=True)


def read_until(hal: LinuxHAL, expected: float, timeout: float = 3.0) -> float:
    deadline = time.monotonic() + timeout
    value = hal.sensor_read("temperature", called_from="test")
    while value != expected and time.monotonic() < deadline:
        time.sleep(0.05)
        value = hal.sensor_read("temperature", called_from="test")
    return value


@pytest.fixture
def hal(lm75):
    hal = LinuxHAL(
        events=EventLog(target="linux", board_id="linux-rpi5"),
        authorize=lambda *_: None,
        sensor_sources={"temperature": "hwmon:lm75/temp1"},
        display="memory",
    )
    yield hal
    hal.close()
    set_temperature(25.0)


def test_the_hal_reads_the_lm75_through_hwmon(hal):
    set_temperature(25.0)
    assert read_until(hal, 25.0) == 25.0
    set_temperature(31.5)
    assert read_until(hal, 31.5) == 31.5, "every read reaches the chip; none is cached"
    set_temperature(-5.0)
    assert read_until(hal, -5.0) == -5.0
    last = hal.events.of_type("sensor_read")[-1]
    assert last == {"sensor": "temperature", "value": -5.0, "unit": "C"}


def test_the_device_is_found_by_name_and_the_bus_it_sits_on(lm75):
    hal = LinuxHAL(
        authorize=lambda *_: None, sensor_sources={"temperature": f"hwmon:lm75@{lm75}/temp1"}
    )
    try:
        set_temperature(22.5)
        assert read_until(hal, 22.5) == 22.5
    finally:
        hal.close()


def test_a_sensor_the_kernel_does_not_have_fails_closed(hal):
    missing = LinuxHAL(
        authorize=lambda *_: None, sensor_sources={"humidity": "hwmon:sht3x/humidity1"}
    )
    try:
        with pytest.raises(BoardCapabilityError, match="no hwmon device named 'sht3x'") as raised:
            missing.sensor_read("humidity")
        assert "lm75" in raised.value.why, "it lists what the kernel does have"
        with pytest.raises(BoardCapabilityError, match="labelled 'temperature'"):
            missing.sensor_read("temperature")  # no label on i2c-stub, no source for it
    finally:
        missing.close()


def test_frames_on_the_memory_backend_are_what_sim_records(hal):
    sim = SimHAL(events=EventLog())
    pixels = bytes(range(8))
    for frame, kwargs in (("24,5 °C", {"width": 320, "height": 240}),
                          (pixels, {"width": 2, "height": 2, "format": "rgb565"})):  # fmt: skip
        assert hal.display(frame, **kwargs) == sim.display(frame, **kwargs)
    assert hal.events.of_type("display_frame") == sim.events.of_type("display_frame")


def test_a_frame_reaches_the_kernel_framebuffer():
    device = env("NEUROEDGE_VFB_DEVICE")
    hal = LinuxHAL(authorize=lambda *_: None, display=device)
    try:
        pixels = bytes([0xF8, 0x00, 0x07, 0xE0, 0x00, 0x1F, 0xFF, 0xFF, 0x12, 0x34, 0x56, 0x78])
        shown = hal.display(pixels, width=3, height=2, format="rgb565")
        fd = os.open(device, os.O_RDONLY)
        try:
            geometry = kernel_geometry(fd)
            packed = pack_pixels(shown, geometry)
            row = 3 * geometry.bits_per_pixel // 8
            for y in range(2):
                on_screen = os.pread(fd, row, y * geometry.line_length)
                assert on_screen == packed[y * row : (y + 1) * row]
        finally:
            os.close(fd)
        assert (geometry.xres, geometry.yres) == (800, 480)
        assert hal.frames == [shown]
    finally:
        hal.close()


# --- end to end: an interactive session and its trace --------------------------------

CHILD_ENV = {
    **os.environ,
    "NO_COLOR": "1",
    "COLUMNS": "200",
    SENSORS_ENV: "temperature=hwmon:lm75/temp1",
    DISPLAY_ENV: "memory",
}


def neuroedge(*args: str, stdin: str = "", timeout: float = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "neuroedge", *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=CHILD_ENV,
        timeout=timeout,
    )


def test_a_session_on_linux_decides_on_the_kernel_reading_and_replays(lm75, tmp_path: Path):
    set_temperature(26.5)
    out = tmp_path / "factory.json"
    done = neuroedge(
        "record", "--target", "linux", "--agent", str(FACTORY), "--out", str(out),
        stdin="bật quạt\ntắt quạt\nexit\n",
    )  # fmt: skip
    assert done.returncode == 0, done.stdout + done.stderr
    trace = json.loads(out.read_text(encoding="utf-8"))
    reads = [e["data"] for e in trace["events"] if e["type"] == "sensor_read"]
    assert reads and all(r == {"sensor": "temperature", "value": 26.5, "unit": "C", "use": "fact"}
                         for r in reads)  # fmt: skip
    # The gates compare heat bands; a reading in degrees is no band, so vent_off is refused.
    assert "ALLOW" in done.stdout and "BLOCK" in done.stdout

    sim = replay(out, target="sim", agent=FACTORY)
    linux = replay(out, target="linux", agent=FACTORY)
    assert linux.verdicts == sim.verdicts == sim.recorded_verdicts


def test_a_session_whose_sensor_is_not_found_exits_before_any_line(lm75):
    done = subprocess.run(
        [sys.executable, "-m", "neuroedge", "run", "--target", "linux", "--agent", str(FACTORY),
         "-c", "bật quạt"],
        capture_output=True, text=True, timeout=30,
        env={**CHILD_ENV, SENSORS_ENV: "temperature=hwmon:nothing/temp1"},
    )  # fmt: skip
    assert done.returncode == 1, done.stdout + done.stderr
    assert "no hwmon device named 'nothing'" in done.stdout + done.stderr
