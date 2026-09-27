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


def test_a_sensor_the_kernel_does_not_have_fails_closed(lm75):
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


def read(path: str) -> str:
    with open(path, encoding="ascii") as file:
        return file.read().strip()


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
        assert geometry.bits_per_pixel in (16, 24, 32)
        assert geometry.xres >= 800 and geometry.yres >= 480, "the board's display fits"
        # The ioctl parse, checked against what sysfs says without it: packing and the
        # read-back above both use `geometry`, so a misread would agree with itself.
        sysfs = f"/sys/class/graphics/{os.path.basename(device)}"
        assert int(read(f"{sysfs}/stride")) == geometry.line_length
        assert int(read(f"{sysfs}/bits_per_pixel")) == geometry.bits_per_pixel
        # And one pixel spelled out: pixel 0 is full red (0xF800).
        with open(device, "rb") as fb:
            first = fb.read(4)
        if geometry.bits_per_pixel == 32 and geometry.red == (16, 8):
            assert first[:3] == bytes([0x00, 0x00, 0xFF]), first  # XRGB8888: B, G, R
        elif geometry.bits_per_pixel == 16:
            assert first[:2] == bytes([0x00, 0xF8]), first  # RGB565, little-endian
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


def lm75_hwmon(device: str, timeout: float = 5.0) -> Path:
    """The hwmon directory of the lm75 bound to `device` — found by name, as the HAL does."""
    deadline = time.monotonic() + timeout
    while True:
        for directory in Path("/sys/class/hwmon").glob("hwmon*"):
            name = directory / "name"
            if (
                name.exists()
                and name.read_text(encoding="ascii").strip() == "lm75"
                and (directory / "device").resolve().name == device
            ):
                return directory
        assert time.monotonic() < deadline, f"no lm75 hwmon device on {device}"
        time.sleep(0.05)


def wait_for_kernel(celsius: float, timeout: float = 5.0) -> None:
    """
    Wait until the lm75 driver reports the register just written (it refreshes on its
    own interval), reading sysfs directly: a LinuxHAL here would hold the lines the
    session under test needs.
    """
    path = lm75_hwmon(env("NEUROEDGE_LM75_DEVICE")) / "temp1_input"
    expected = round(celsius * 1000)
    deadline = time.monotonic() + timeout
    while (reported := int(path.read_text(encoding="ascii"))) != expected:
        assert time.monotonic() < deadline, f"{path} reports {reported}, not {expected}"
        time.sleep(0.05)


def events(trace: dict, kind: str) -> list[dict]:
    return [event["data"] for event in trace["events"] if event["type"] == kind]


@pytest.mark.parametrize(
    ("celsius", "band", "verdicts", "fan"),
    [
        # `normal`: vent_off is allowed; the "có" after it answers nothing.
        (30.0, "normal", ["ALLOW", "ALLOW"], [("on", 0), ("off", 0)]),
        # `high`: vent_off asks (on_block: ask); the operator's "có" stops the fan.
        (45.0, "high", ["ALLOW", "BLOCK", "ALLOW"], [("on", 0), ("off", 0)]),
        (54.5, "high", ["ALLOW", "BLOCK", "ALLOW"], [("on", 0), ("off", 0)]),
        # `critical` starts at 55 °C, inclusive: refused, nothing asked, "có" is no answer.
        (55.0, "critical", ["ALLOW", "BLOCK"], [("on", 0)]),
        (60.0, "critical", ["ALLOW", "BLOCK"], [("on", 0)]),
    ],
)
def test_the_kernel_reading_decides_the_fan_through_its_band_and_replays(
    lm75, tmp_path: Path, celsius, band, verdicts, fan
):
    set_temperature(celsius)
    try:
        wait_for_kernel(celsius)
        out = tmp_path / "factory.json"
        done = neuroedge(
            "record", "--target", "linux", "--agent", str(FACTORY), "--out", str(out),
            stdin="bật quạt\ntắt quạt\ncó\nexit\n",
        )  # fmt: skip
    finally:
        set_temperature(25.0)
    assert done.returncode == 0, done.stdout + done.stderr
    trace = json.loads(out.read_text(encoding="utf-8"))
    reads = events(trace, "sensor_read")
    assert reads and all(r == {"sensor": "temperature", "value": celsius, "unit": "C", "use": "fact"}
                         for r in reads)  # fmt: skip
    vent_off = [f for f in events(trace, "gate_facts") if "heat_level" in f]
    assert vent_off and all(f["heat_level"]["value"] == band for f in vent_off)
    assert all(f["heat_critical"]["value"] is (celsius >= 55) for f in vent_off)
    assert [r["verdict"] for r in events(trace, "gate_evaluation_result")] == verdicts
    assert bool(events(trace, "tool_confirm_requested")) is (band == "high")

    sim = replay(out, target="sim", agent=FACTORY)
    linux = replay(out, target="linux", agent=FACTORY)
    assert linux.verdicts == sim.verdicts == sim.recorded_verdicts == verdicts
    assert linux.pin("gate_relay").commands == sim.pin("gate_relay").commands == fan


def test_a_session_whose_sensor_is_not_found_exits_before_any_line(lm75):
    done = subprocess.run(
        [sys.executable, "-m", "neuroedge", "run", "--target", "linux", "--agent", str(FACTORY),
         "-c", "bật quạt"],
        capture_output=True, text=True, timeout=30,
        env={**CHILD_ENV, SENSORS_ENV: "temperature=hwmon:nothing/temp1"},
    )  # fmt: skip
    assert done.returncode == 1, done.stdout + done.stderr
    assert "no hwmon device named 'nothing'" in done.stdout + done.stderr


def lm75_driver(action: str, device: str) -> None:
    """Unbind or bind the kernel's lm75 driver from the chip: the sensor goes away, or back."""
    subprocess.run(
        ["sudo", "-n", "tee", f"/sys/bus/i2c/drivers/lm75/{action}"],
        input=device, text=True, capture_output=True, check=True, timeout=10,
    )  # fmt: skip


def test_a_sensor_that_goes_away_mid_session_leaves_only_its_facts_undecided(lm75, monkeypatch):
    """
    Last in the file: it unbinds the driver. The session started on a healthy sensor
    (preflight read it); then the kernel device disappears. The heat gates refuse
    without asking, the gates that read no heat fact still decide, and nothing raises.
    """
    import asyncio

    from neuroedge.sim import SimSession

    monkeypatch.setenv(SENSORS_ENV, "temperature=hwmon:lm75/temp1")
    set_temperature(30.0)
    wait_for_kernel(30.0)
    session = SimSession.load(FACTORY, target="linux")
    try:
        assert asyncio.run(session.handle("tắt báo động")).allowed, "30 °C is `normal`"
        lm75_driver("unbind", lm75)
        try:
            lines = ("bật quạt", "bật báo động", "tắt quạt", "có", "tắt báo động")
            fan_on, alarm_on, fan_off, yes, alarm_off = [
                asyncio.run(session.handle(line)) for line in lines
            ]
        finally:
            lm75_driver("bind", lm75)
            lm75_hwmon(lm75)  # back, for whatever runs next
        unavailable = session.events.of_type("sensor_unavailable")
    finally:
        session.close()
    assert fan_on.allowed and alarm_on.allowed, "gates that read no heat fact still decide"
    for turn in (fan_off, alarm_off):
        assert turn.result.blocked and turn.result.gate.reason == "criterion_unavailable"
        assert turn.confirmation is None, "nothing a person could stand in for: nothing asked"
    assert not yes.allowed
    assert unavailable and all(u["sensor"] == "temperature" for u in unavailable)
    assert "no hwmon device named 'lm75'" in unavailable[0]["reason"]
