"""
TSK-S5-09 — `sensor.read` and `display` on `linux`, against a fake /sys tree and a
fake framebuffer (a plain file), so these run everywhere, macOS included.

The same HAL against a real kernel — `i2c-stub` + `lm75` → hwmon — is in
`tests_linux/`, run by the `linux-hal` CI job.
"""

from __future__ import annotations

import dataclasses
import os
import sys
import time

import pytest

import neuroedge.hal.linux as linux
from neuroedge.engine.trace_sink import EventLog
from neuroedge.errors import BoardCapabilityError
from neuroedge.hal.board import load_board_by_id
from neuroedge.hal.framebuffer import (
    FbGeometry,
    FramebufferDisplay,
    MemoryDisplay,
    pack_general,
    pack_pixels,
)
from neuroedge.hal.linux import MISSING_ON_LINUX, LinuxHAL
from neuroedge.hal.sim import Frame, SimHAL, make_frame

from .test_hal_linux import LINES, FakeGpiod


@pytest.fixture(autouse=True)
def no_machine_wiring(monkeypatch):
    """The developer's own environment must not decide what these tests see."""
    monkeypatch.delenv(linux.SENSORS_ENV, raising=False)
    monkeypatch.delenv(linux.DISPLAY_ENV, raising=False)


@pytest.fixture
def sys_root(tmp_path):
    root = tmp_path / "sys"
    (root / "class" / "hwmon").mkdir(parents=True)
    (root / "bus" / "iio" / "devices").mkdir(parents=True)
    return root


def hwmon(root, index, name, files, at=None):
    device = root / "class" / "hwmon" / f"hwmon{index}"
    device.mkdir()
    (device / "name").write_text(f"{name}\n")
    for file, text in files.items():
        (device / file).write_text(f"{text}\n")
    if at is not None:
        target = root / "devices" / at
        target.mkdir(parents=True)
        os.symlink(target, device / "device")
    return device


def iio(root, index, name, files, at=None):
    device = root / "bus" / "iio" / "devices" / f"iio:device{index}"
    if at is None:
        device.mkdir()
    else:  # as the kernel lays it out: a child of the device it sits on
        real = root / "devices" / at / f"iio:device{index}"
        real.mkdir(parents=True)
        os.symlink(real, device)
    (device / "name").write_text(f"{name}\n")
    for file, text in files.items():
        (device / file).write_text(f"{text}\n")
    return device


def make(tmp_path, fake=None, **kwargs):
    """A LinuxHAL on fake lines. Pass `fake` to look at its requests after a refusal."""
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    fake = fake if fake is not None else FakeGpiod({str(chip): LINES})
    events = EventLog(target="linux", board_id="linux-rpi5")
    hal = LinuxHAL(
        chip_glob=str(tmp_path / "gpiochip*"),
        gpiod=fake,
        events=events,
        authorize=lambda *_: None,
        **kwargs,
    )
    return hal, fake


def test_only_audio_is_still_missing_on_linux():
    assert set(MISSING_ON_LINUX) == {"audio.in", "audio.out"}


# --- sensor.read: hwmon ---------------------------------------------------------------


def test_a_mapped_hwmon_channel_reads_in_degrees_and_records_what_sim_records(tmp_path, sys_root):
    hwmon(sys_root, 0, "cpu_thermal", {"temp1_input": 51000})
    hwmon(sys_root, 3, "lm75", {"temp1_input": 24500})
    hal, _ = make(tmp_path, sysfs_root=sys_root, sensor_sources={"temperature": "hwmon:lm75/temp1"})
    assert hal.sensor_read("temperature", called_from="test") == 24.5
    (event,) = hal.events.of_type("sensor_read")

    sim = SimHAL(events=EventLog())
    sim.set_sensor("temperature", 24.5, "C")
    sim.sensor_read("temperature")
    (on_sim,) = sim.events.of_type("sensor_read")
    assert event == on_sim == {"sensor": "temperature", "value": 24.5, "unit": "C"}


def test_a_labelled_channel_is_found_with_no_mapping(tmp_path, sys_root):
    hwmon(
        sys_root,
        1,
        "sht3x",
        {"temp1_input": 22000, "humidity1_input": 41250, "humidity1_label": "humidity"},
    )
    hal, _ = make(tmp_path, sysfs_root=sys_root)
    assert hal.sensor_read("humidity") == 41.25
    assert hal.events.of_type("sensor_read")[-1]["unit"] == "%RH"


def test_every_read_goes_to_the_kernel(tmp_path, sys_root):
    device = hwmon(sys_root, 0, "lm75", {"temp1_input": 20000})
    hal, _ = make(tmp_path, sysfs_root=sys_root, sensor_sources={"temperature": "hwmon:lm75/temp1"})
    assert hal.sensor_read("temperature") == 20.0
    (device / "temp1_input").write_text("21500\n")
    assert hal.sensor_read("temperature") == 21.5
    for file in device.iterdir():
        file.unlink()
    device.rmdir()
    with pytest.raises(BoardCapabilityError, match="no hwmon device named 'lm75'"):
        hal.sensor_read("temperature")
    assert [e["value"] for e in hal.events.of_type("sensor_read")] == [20.0, 21.5]


def test_no_source_and_no_label_never_reads_as_a_default(tmp_path, sys_root):
    hwmon(sys_root, 0, "lm75", {"temp1_input": 24500})
    hal, _ = make(tmp_path, sysfs_root=sys_root)
    with pytest.raises(BoardCapabilityError) as raised:
        hal.sensor_read("temperature", called_from="report()")
    assert "labelled 'temperature'" in raised.value.why and "Q-16" in raised.value.why
    assert "NEUROEDGE_LINUX_SENSORS" in raised.value.how
    assert "report() -> sensor.read 'temperature'" in raised.value.where
    assert hal.events.of_type("sensor_read") == []


def test_two_labelled_channels_are_ambiguous(tmp_path, sys_root):
    hwmon(sys_root, 0, "a", {"temp1_input": 1, "temp1_label": "temperature"})
    iio(sys_root, 0, "b", {"in_temp_input": 1, "in_temp_label": "temperature"})
    hal, _ = make(tmp_path, sysfs_root=sys_root)
    with pytest.raises(BoardCapabilityError, match="2 channels are labelled 'temperature'"):
        hal.sensor_read("temperature")


def test_two_devices_of_one_name_are_told_apart_by_the_device_they_sit_on(tmp_path, sys_root):
    hwmon(sys_root, 0, "lm75", {"temp1_input": 20000}, at="1-0048")
    hwmon(sys_root, 1, "lm75", {"temp1_input": 30000}, at="1-0049")
    hal, _ = make(tmp_path, sysfs_root=sys_root, sensor_sources={"temperature": "hwmon:lm75/temp1"})
    with pytest.raises(BoardCapabilityError, match=r"2 hwmon devices .*1-0048.*1-0049") as raised:
        hal.sensor_read("temperature")
    assert "hwmon:lm75@<device>/temp1" in raised.value.how
    hal.close()
    other = tmp_path / "other"
    other.mkdir()
    hal, _ = make(
        other, sysfs_root=sys_root, sensor_sources={"temperature": "hwmon:lm75@1-0049/temp1"}
    )
    assert hal.sensor_read("temperature") == 30.0


@pytest.mark.parametrize(
    ("files", "why"),
    [
        ({"temp1_input": "N/A"}, "holds 'N/A', not a number"),
        ({"temp1_input": ""}, "holds '', not a number"),
        ({}, "temp1_input does not exist"),
        ({"temp1_input": 24000, "temp1_fault": 1}, "flags temp1_fault"),
    ],
)
def test_a_reading_that_is_not_one_valid_number_raises(tmp_path, sys_root, files, why):
    hwmon(sys_root, 0, "lm75", files)
    hal, _ = make(tmp_path, sysfs_root=sys_root, sensor_sources={"temperature": "hwmon:lm75/temp1"})
    with pytest.raises(BoardCapabilityError, match=why):
        hal.sensor_read("temperature")
    assert hal.events.of_type("sensor_read") == []


def test_a_file_the_kernel_will_not_read_raises(tmp_path, sys_root):
    device = hwmon(sys_root, 0, "lm75", {})
    (device / "temp1_input").mkdir()  # reading it fails with an OSError, as EIO would
    hal, _ = make(tmp_path, sysfs_root=sys_root, sensor_sources={"temperature": "hwmon:lm75/temp1"})
    with pytest.raises(BoardCapabilityError, match="cannot read"):
        hal.sensor_read("temperature")


def test_a_fault_flag_of_zero_is_a_valid_reading(tmp_path, sys_root):
    hwmon(sys_root, 0, "lm75", {"temp1_input": 24000, "temp1_fault": 0})
    hal, _ = make(tmp_path, sysfs_root=sys_root, sensor_sources={"temperature": "hwmon:lm75/temp1"})
    assert hal.sensor_read("temperature") == 24.0


def test_a_channel_type_with_no_known_unit_raises(tmp_path, sys_root):
    hwmon(sys_root, 0, "odd", {"pwm1_input": 128})
    hal, _ = make(tmp_path, sysfs_root=sys_root, sensor_sources={"temperature": "hwmon:odd/pwm1"})
    with pytest.raises(BoardCapabilityError, match="'pwm' has no known unit"):
        hal.sensor_read("temperature")


def test_a_sensor_the_board_does_not_declare_is_refused_before_sysfs(tmp_path, sys_root):
    hal, _ = make(tmp_path, sysfs_root=sys_root)
    with pytest.raises(BoardCapabilityError, match="declares no sensor named 'pressure'"):
        hal.sensor_read("pressure")


def test_a_device_that_is_not_on_the_named_bus_address_is_not_read(tmp_path, sys_root):
    hwmon(sys_root, 0, "lm75", {"temp1_input": 20000}, at="1-0048")
    hal, _ = make(
        tmp_path, sysfs_root=sys_root, sensor_sources={"temperature": "hwmon:lm75@9-0099/temp1"}
    )
    with pytest.raises(BoardCapabilityError, match="named 'lm75' on 9-0099"):
        hal.sensor_read("temperature")
    assert hal.events.of_type("sensor_read") == []


# --- sensor.read: IIO -----------------------------------------------------------------


def test_an_iio_raw_channel_applies_offset_and_scale(tmp_path, sys_root):
    iio(sys_root, 0, "tmp117", {"in_temp_raw": 1250, "in_temp_offset": 250, "in_temp_scale": 20})
    iio(sys_root, 1, "ads1015", {"in_voltage0_raw": 2048, "in_voltage_scale": "0.805664062"})
    hal, _ = make(
        tmp_path,
        sysfs_root=sys_root,
        sensor_sources={"temperature": "iio:tmp117/temp", "humidity": "iio:ads1015/voltage0"},
    )
    assert hal.sensor_read("temperature") == 30.0
    assert hal.sensor_read("humidity") == pytest.approx(1.65, abs=1e-6)
    assert [e["unit"] for e in hal.events.of_type("sensor_read")] == ["C", "V"]


@pytest.mark.parametrize("text", ["nan", "inf", "-inf", "NaN", "Infinity"])
@pytest.mark.parametrize(
    "file", ["in_temp_input", "in_temp_raw", "in_temp_scale", "in_temp_offset"]
)
def test_a_non_finite_iio_value_is_no_reading(tmp_path, sys_root, file, text):
    # NaN compares False to everything: read as a value, `gte = 80` would be False and allow.
    files = {"in_temp_raw": 1000, "in_temp_scale": 1, "in_temp_offset": 0}
    if file == "in_temp_input":
        files = {"in_temp_input": text}
    else:
        files[file] = text
    iio(sys_root, 0, "tmp117", files)
    hal, _ = make(tmp_path, sysfs_root=sys_root, sensor_sources={"temperature": "iio:tmp117/temp"})
    with pytest.raises(BoardCapabilityError, match="not a number"):
        hal.sensor_read("temperature")
    assert hal.events.of_type("sensor_read") == []


def test_an_iio_value_that_overflows_is_no_reading(tmp_path, sys_root):
    iio(sys_root, 0, "tmp117", {"in_temp_raw": "1e308", "in_temp_scale": "1e308"})
    hal, _ = make(tmp_path, sysfs_root=sys_root, sensor_sources={"temperature": "iio:tmp117/temp"})
    with pytest.raises(BoardCapabilityError, match="not a finite number"):
        hal.sensor_read("temperature")


@pytest.mark.parametrize("attr", ["scale", "offset"])
def test_an_unreadable_iio_scale_or_offset_fails_rather_than_defaulting(tmp_path, sys_root, attr):
    device = iio(sys_root, 0, "tmp117", {"in_temp_raw": 1000})
    (device / f"in_temp_{attr}").write_text("N/A\n")
    hal, _ = make(tmp_path, sysfs_root=sys_root, sensor_sources={"temperature": "iio:tmp117/temp"})
    with pytest.raises(BoardCapabilityError, match=f"in_temp_{attr} holds 'N/A'"):
        hal.sensor_read("temperature")
    (device / f"in_temp_{attr}").unlink()
    (device / f"in_temp_{attr}").mkdir()  # exists, but reading it fails
    with pytest.raises(BoardCapabilityError, match="cannot read"):
        hal.sensor_read("temperature")
    assert hal.events.of_type("sensor_read") == []


def test_two_iio_devices_of_one_name_are_told_apart_by_the_device_they_sit_on(tmp_path, sys_root):
    iio(sys_root, 0, "bme280", {"in_temp_input": 20000}, at="1-0076")
    iio(sys_root, 1, "bme280", {"in_temp_input": 30000}, at="1-0077")
    hal, _ = make(tmp_path, sysfs_root=sys_root, sensor_sources={"temperature": "iio:bme280/temp"})
    with pytest.raises(BoardCapabilityError, match=r"2 iio devices .*1-0076.*1-0077"):
        hal.sensor_read("temperature")
    hal.close()
    other = tmp_path / "other"
    other.mkdir()
    hal, _ = make(
        other, sysfs_root=sys_root, sensor_sources={"temperature": "iio:bme280@1-0077/temp"}
    )
    assert hal.sensor_read("temperature") == 30.0


def test_an_iio_processed_channel_and_labels(tmp_path, sys_root):
    iio(
        sys_root,
        0,
        "bme280",
        {
            "in_humidityrelative_input": 45123,
            "in_temp_input": 21000,
            "in_humidityrelative_label": "humidity",
        },
    )
    iio(sys_root, 1, "tmp117", {"in_temp_raw": 3000, "in_temp_scale": 10})
    (sys_root / "bus" / "iio" / "devices" / "iio:device1" / "label").write_text("temperature\n")
    hal, _ = make(tmp_path, sysfs_root=sys_root)
    assert hal.sensor_read("humidity") == pytest.approx(45.123)
    assert hal.sensor_read("temperature") == 30.0


def test_an_iio_device_label_on_several_channels_is_ambiguous(tmp_path, sys_root):
    device = iio(sys_root, 0, "bme280", {"in_temp_input": 1, "in_pressure_input": 101})
    (device / "label").write_text("temperature\n")
    hal, _ = make(tmp_path, sysfs_root=sys_root)
    with pytest.raises(BoardCapabilityError, match="has channels"):
        hal.sensor_read("temperature")


# --- where the mapping comes from -----------------------------------------------------


def test_the_mapping_can_come_from_the_environment(tmp_path, sys_root, monkeypatch):
    hwmon(sys_root, 0, "lm75", {"temp1_input": 19000})
    monkeypatch.setenv(linux.SENSORS_ENV, " temperature = hwmon:lm75/temp1 ; ")
    hal, _ = make(tmp_path, sysfs_root=sys_root)
    assert hal.sensor_read("temperature") == 19.0


def fake_lines(tmp_path):
    return FakeGpiod({str(tmp_path / "gpiochip0"): LINES})


@pytest.mark.parametrize(
    ("value", "why"),
    [("temperature", "is not sensor=source"), ("temperature=lm75", "is not a sensor source")],
)
def test_a_malformed_mapping_fails_before_any_line(tmp_path, monkeypatch, value, why):
    monkeypatch.setenv(linux.SENSORS_ENV, value)
    fake = fake_lines(tmp_path)
    with pytest.raises(BoardCapabilityError, match=why):
        make(tmp_path, fake=fake)
    assert fake.requests == []


def test_a_session_preflight_refuses_an_unreadable_sensor_before_any_line(tmp_path, sys_root):
    fake = fake_lines(tmp_path)
    with pytest.raises(BoardCapabilityError, match="labelled 'temperature'"):
        make(
            tmp_path,
            fake=fake,
            sysfs_root=sys_root,
            needs={"sensors": ["temperature"], "where": "agent"},
        )
    with pytest.raises(BoardCapabilityError, match="no display backend"):
        make(tmp_path, fake=fake, needs={"display": True, "where": "agent"})
    assert fake.requests == [], "a refused preflight requests no line"
    hwmon(sys_root, 0, "lm75", {"temp1_input": 1000, "temp1_label": "temperature"})
    hal, fake = make(
        tmp_path,
        sysfs_root=sys_root,
        display="memory",
        needs={"sensors": ["temperature"], "display": True},
    )
    assert fake.requests and hal.events.of_type("sensor_read") == [], "preflight records nothing"


# --- replay: recorded readings in place of the kernel's -------------------------------


def test_replay_feeds_recorded_readings_and_never_touches_sysfs(tmp_path, sys_root):
    hal, _ = make(tmp_path, sysfs_root=sys_root)  # no sensor in /sys at all
    hal.script_sensor("temperature", [24.5, 25.0], "C")
    with pytest.raises(BoardCapabilityError, match="holds no reading"):
        hal.sensor_read("temperature", use="fact")
    assert hal.sensor_read("temperature") == 24.5
    # A fact read repeats the last replayed reading; it takes nothing from the queue.
    assert hal.sensor_read("temperature", use="fact") == 24.5
    assert [hal.sensor_read("temperature") for _ in range(2)] == [25.0, 25.0]
    assert hal.events.of_type("sensor_read")[0] == {
        "sensor": "temperature",
        "value": 24.5,
        "unit": "C",
    }


def test_replay_never_reads_a_sensor_the_trace_does_not_hold(tmp_path, sys_root):
    hwmon(sys_root, 0, "lm75", {"temp1_input": 31000, "temp1_label": "temperature"})
    hal, _ = make(tmp_path, sysfs_root=sys_root, replay=True)
    with pytest.raises(BoardCapabilityError, match="holds no reading of this sensor"):
        hal.sensor_read("temperature")
    assert hal.events.of_type("sensor_read") == []
    assert isinstance(hal.display_backend, MemoryDisplay), "a replay draws in memory"


def test_the_machines_wiring_does_not_enter_a_replay(tmp_path, sys_root, monkeypatch):
    # A Pi set up for a panel and its sensors: replay still draws in memory, and a
    # stale mapping for a sensor the board lacks does not stop it.
    monkeypatch.setenv(linux.DISPLAY_ENV, "/dev/fb0")
    monkeypatch.setenv(linux.SENSORS_ENV, "pressure=hwmon:lm75/temp1")
    hal, _ = make(tmp_path, sysfs_root=sys_root, replay=True)
    assert isinstance(hal.display_backend, MemoryDisplay)
    assert hal.sensors.sources == {}


def test_a_replay_preflight_reads_no_sensor(tmp_path, sys_root, monkeypatch):
    def no_kernel(*args, **kwargs):
        raise AssertionError("a replay read sysfs")

    monkeypatch.setattr(linux.SysfsSensors, "read", no_kernel)
    hal, fake = make(
        tmp_path,
        sysfs_root=sys_root,  # empty: a kernel read would fail anyway
        replay=True,
        needs={"sensors": ["temperature"], "display": True, "where": "agent"},
    )
    assert fake.requests, "the preflight passed and the lines were requested"
    with pytest.raises(BoardCapabilityError, match="declares no sensor named 'pressure'"):
        hal.preflight(sensors=["pressure"], where="agent")  # the board is still checked


def test_a_reading_in_another_unit_than_the_agent_declares_is_refused(tmp_path, sys_root):
    iio(sys_root, 0, "bme280", {"in_pressure_input": 101.3, "in_pressure_label": "temperature"})
    hal, fake = make(tmp_path, sysfs_root=sys_root, units={"temperature": "C"})
    with pytest.raises(BoardCapabilityError, match="in 'kPa'.*declares 'C'"):
        hal.sensor_read("temperature")
    assert hal.events.of_type("sensor_read") == []
    other = tmp_path / "other"
    other.mkdir()
    fake = fake_lines(other)
    with pytest.raises(BoardCapabilityError, match="declares 'C'"):
        make(
            other,
            fake=fake,
            sysfs_root=sys_root,
            units={"temperature": "C"},
            needs={"sensors": ["temperature"], "where": "agent"},
        )
    assert fake.requests == []


def test_a_mapping_for_a_sensor_the_board_lacks_is_refused(tmp_path, sys_root, monkeypatch):
    monkeypatch.setenv(linux.SENSORS_ENV, "temprature=hwmon:lm75/temp1")
    fake = fake_lines(tmp_path)
    with pytest.raises(BoardCapabilityError, match="declares no sensor named 'temprature'"):
        make(tmp_path, fake=fake, sysfs_root=sys_root)
    assert fake.requests == []


# --- display --------------------------------------------------------------------------

PIXELS_565 = bytes([0xF8, 0x00, 0x07, 0xE0, 0x00, 0x1F, 0xFF, 0xFF])  # red green blue white


def test_display_records_the_same_frame_as_sim(tmp_path):
    hal, _ = make(tmp_path, display="memory")
    sim = SimHAL(events=EventLog())
    for call in (
        {"frame": "Nhiệt độ 24,5 °C", "width": 320, "height": 240},
        {"frame": PIXELS_565, "width": 2, "height": 2, "format": "rgb565"},
    ):
        frame = call.pop("frame")
        assert hal.display(frame, **call) == sim.display(frame, **call)
    assert hal.events.of_type("display_frame") == sim.events.of_type("display_frame")
    assert hal.frames == sim.frames and hal.frame == PIXELS_565


def test_display_refuses_what_sim_refuses(tmp_path):
    hal, _ = make(tmp_path, display="memory")
    with pytest.raises(BoardCapabilityError, match="exceeds the board's 800"):
        hal.display("x", width=801)
    with pytest.raises(BoardCapabilityError, match="needs 8 bytes"):
        hal.display(b"\x00", width=2, height=2, format="rgb565")
    assert hal.frames == [] and hal.events.of_type("display_frame") == []


def test_no_display_backend_is_guessed(tmp_path):
    hal, _ = make(tmp_path)
    with pytest.raises(BoardCapabilityError) as raised:
        hal.display("hello", called_from="show()")
    assert "refusing to guess" in raised.value.why
    assert "NEUROEDGE_LINUX_DISPLAY" in raised.value.how
    assert hal.frames == [] and hal.events.of_type("display_frame") == []


def test_the_backend_can_come_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv(linux.DISPLAY_ENV, "memory")
    hal, _ = make(tmp_path)
    assert isinstance(hal.display_backend, MemoryDisplay)
    monkeypatch.setenv(linux.DISPLAY_ENV, "/dev/fb97")
    with pytest.raises(BoardCapabilityError, match="no framebuffer at"):
        make(tmp_path)
    for path in ("/dev/fb0/../../etc/passwd", "/dev/fb-panel", "/dev/fb"):
        monkeypatch.setenv(linux.DISPLAY_ENV, path)
        with pytest.raises(BoardCapabilityError, match="not a display backend"):
            make(tmp_path)
    monkeypatch.setenv(linux.DISPLAY_ENV, "hdmi")
    with pytest.raises(BoardCapabilityError, match="not a display backend"):
        make(tmp_path)


def test_a_board_without_display_is_refused(tmp_path):
    board = load_board_by_id("linux-rpi5")
    bare = type(board)(
        id="bare",
        target="linux",
        mcu="x",
        capabilities={k: v for k, v in board.capabilities.items() if k != "display"},
    )
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    hal = LinuxHAL(bare, chip_glob=str(chip), gpiod=FakeGpiod({str(chip): LINES}), display="memory")
    with pytest.raises(BoardCapabilityError, match="does not declare the 'display'"):
        hal.display("x")


# --- the framebuffer ------------------------------------------------------------------


def geometry(bpp, xres=4, yres=3, line_length=None, rgb=None, offset=(0, 0)):
    default = {
        16: ((11, 5), (5, 6), (0, 5)),
        24: ((16, 8), (8, 8), (0, 8)),
        32: ((16, 8), (8, 8), (0, 8)),
    }
    red, green, blue = rgb or default.get(bpp, ((0, 8), (0, 8), (0, 8)))
    line = line_length if line_length is not None else xres * bpp // 8
    return FbGeometry(xres, yres, offset[0], offset[1], bpp, line, red, green, blue)


def fb_file(tmp_path, geo):
    path = tmp_path / "fb0"
    path.write_bytes(b"\xee" * (geo.line_length * (geo.yres + geo.yoffset)))
    return path


def show(tmp_path, geo, frame_bytes, fmt="rgb565", width=2, height=2):
    path = fb_file(tmp_path, geo)
    hal, _ = make(tmp_path, display=FramebufferDisplay(path, geometry=lambda fd: geo))
    hal.display(frame_bytes, width=width, height=height, format=fmt)
    return path.read_bytes(), hal


def test_rgb565_lands_on_a_16_bit_framebuffer_row_by_row(tmp_path):
    geo = geometry(16, line_length=10)  # 4 px = 8 bytes, padded to 10
    data, hal = show(tmp_path, geo, PIXELS_565)
    order = sys.byteorder
    row0 = (0xF800).to_bytes(2, order) + (0x07E0).to_bytes(2, order)
    row1 = (0x001F).to_bytes(2, order) + (0xFFFF).to_bytes(2, order)
    assert data[0:4] == row0 and data[4:10] == b"\xee" * 6
    assert data[10:14] == row1 and data[14:] == b"\xee" * 16
    assert len(hal.events.of_type("display_frame")) == 1


def test_rgb888_lands_on_a_32_bit_framebuffer(tmp_path):
    frame = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 10, 20, 30])
    data, _ = show(tmp_path, geometry(32), frame, fmt="rgb888")
    order = sys.byteorder
    pixels = [0xFF0000, 0x00FF00, 0x0000FF, 0x0A141E]
    expected = [p.to_bytes(4, order) for p in pixels]
    assert data[0:8] == expected[0] + expected[1]
    assert data[16:24] == expected[2] + expected[3]


def test_bgr_and_24_bit_layouts_use_the_offsets_the_kernel_reports(tmp_path):
    bgr = ((0, 8), (8, 8), (16, 8))
    data, _ = show(tmp_path, geometry(24, rgb=bgr), bytes([1, 2, 3] * 4), fmt="rgb888")
    assert data[0:3] == (0x030201).to_bytes(3, sys.byteorder)


def rgb565_by_hand(data):
    """The widening rule written out per pixel: what `Frame.rgb888` must equal."""
    out = bytearray()
    for i in range(0, len(data), 2):
        v = (data[i] << 8) | data[i + 1]
        r, g, b = (v >> 11) & 0x1F, (v >> 5) & 0x3F, v & 0x1F
        out += bytes(((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)))
    return bytes(out)


EVERY_565 = bytes(range(256)) * 2 + bytes(reversed(range(256))) * 2  # every byte, both halves
EVERY_888 = bytes(range(256)) * 3


def test_rgb565_widens_to_rgb888_as_by_hand():
    frame = Frame(len(EVERY_565) // 2, 1, "rgb565", EVERY_565)
    assert frame.rgb888() == rgb565_by_hand(EVERY_565)


@pytest.mark.parametrize(
    "geo",
    [
        geometry(16),
        geometry(24),
        geometry(32),
        geometry(24, rgb=((0, 8), (8, 8), (16, 8))),
        geometry(32, rgb=((0, 8), (8, 8), (16, 8))),
    ],
    ids=["rgb565", "rgb888", "xrgb8888", "bgr888", "xbgr8888"],
)
def test_the_fast_packers_equal_the_general_one(geo):
    frames = (
        Frame(len(EVERY_565) // 2, 1, "rgb565", EVERY_565),
        Frame(len(EVERY_888) // 3, 1, "rgb888", EVERY_888),
    )
    for frame in frames:
        assert pack_pixels(frame, geo) == pack_general(frame.rgb888(), geo)


@pytest.mark.parametrize("change", [{"grayscale": 1}, {"msb_right": True}])
def test_a_mode_that_is_not_packed_rgb_is_refused(tmp_path, change):
    geo = dataclasses.replace(geometry(32), **change)
    with pytest.raises(BoardCapabilityError, match="grayscale, FOURCC or msb_right"):
        show(tmp_path, geo, PIXELS_565)


def test_a_full_panel_frame_packs_in_well_under_a_second():
    frame = Frame(800, 480, "rgb888", bytes(range(256)) * (800 * 480 * 3 // 256))
    started = time.perf_counter()
    for geo in (geometry(16, 800, 480), geometry(32, 800, 480)):
        pack_pixels(frame, geo)
    assert time.perf_counter() - started < 1.0


def test_the_framebuffer_is_written_at_the_panned_origin(tmp_path):
    geo = geometry(16, offset=(1, 1))
    data, _ = show(tmp_path, geo, PIXELS_565)
    start = geo.line_length + 2
    assert data[start : start + 2] == (0xF800).to_bytes(2, sys.byteorder)
    assert data[:start] == b"\xee" * start


@pytest.mark.parametrize(
    ("geo", "frame", "fmt", "why"),
    [
        (geometry(16), "hello", None, "renders no fonts"),
        (geometry(16, xres=1), PIXELS_565, "rgb565", "exceeds the framebuffer's 1x3"),
        (geometry(8), PIXELS_565, "rgb565", "16, 24 or 32 bits per pixel"),
    ],
)
def test_the_framebuffer_refuses_what_it_cannot_show(tmp_path, geo, frame, fmt, why):
    path = fb_file(tmp_path, geo)
    before = path.read_bytes()
    hal, _ = make(tmp_path, display=FramebufferDisplay(path, geometry=lambda fd: geo))
    with pytest.raises(BoardCapabilityError, match=why):
        hal.display(frame, width=2, height=2, format=fmt)
    assert path.read_bytes() == before, "nothing half-drawn"
    assert hal.frames == [] and hal.events.of_type("display_frame") == []


def test_a_row_the_framebuffer_cuts_short_is_an_error(tmp_path):
    geo = geometry(16)
    display = FramebufferDisplay(fb_file(tmp_path, geo), geometry=lambda fd: geo)

    class Short:
        def seek(self, offset):
            pass

        def write(self, data):
            return len(data) - 1

    shown = SimHAL(events=EventLog())
    frame = make_frame(shown.board, PIXELS_565, 2, 2, "rgb565", "test")
    with pytest.raises(BoardCapabilityError, match="row 0 was cut short"):
        display._write(Short(), frame, geo, "test")


def test_a_framebuffer_that_cannot_be_opened_is_an_error_not_a_skip(tmp_path):
    hal, _ = make(tmp_path, display=FramebufferDisplay(tmp_path / "gone", geometry=lambda fd: None))
    with pytest.raises(BoardCapabilityError, match="cannot write the framebuffer"):
        hal.display(PIXELS_565, width=2, height=2, format="rgb565")
    assert hal.events.of_type("display_frame") == []


def test_close_after_sensor_and_display_use_stays_idempotent(tmp_path, sys_root):
    hwmon(sys_root, 0, "lm75", {"temp1_input": 1000, "temp1_label": "temperature"})
    hal, fake = make(tmp_path, sysfs_root=sys_root, display="memory")
    hal.sensor_read("temperature")
    hal.display("ok")
    hal.close()
    hal.close()
    assert all(request.released for request in fake.requests)
