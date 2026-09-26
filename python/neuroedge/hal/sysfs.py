"""
`sensor.read` on target `linux`: the kernel's hwmon and IIO sysfs (TSK-S5-09, FR-TGT-02).

A board sensor is found by **name**, never by the kernel's index — `hwmon3` and
`iio:device0` are numbered in probe order and change across boots. Two ways:

* **a label**, the default: the hwmon channel whose ``temp1_label`` reads
  ``temperature``, or the IIO channel whose ``in_temp_label`` (or the one-channel
  IIO device whose ``label``) does. A device tree sets these, the way gpio-sim
  lines are named after the board pins;
* **a source**, when the kernel carries no label: ``hwmon:<name>/<channel>`` or
  ``iio:<name>/<channel>``, where ``<name>`` is the device's ``name`` file
  (``lm75``, ``bme280``) and ``<channel>`` the sysfs channel (``temp1``,
  ``humidityrelative``, ``voltage0``). ``<name>@<device>`` picks one of two
  devices with the same name by the kernel device they sit on (``lm75@1-0048``).

Every read goes to the kernel, and the file layout is looked up again on each
read, so a device that went away fails instead of answering from an old path.
(The kernel's value is as fresh as the driver's own update interval — lm75
about 1.5 s — and no fresher.) Anything that is not one finite, numeric,
fault-free value — no source, two sources, an unreadable file, NaN or inf, a
fault flag, a channel type whose unit is unknown — raises `BoardCapabilityError`.
A sensor never reads as a default (Q-16).
"""

from __future__ import annotations

import math
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ..errors import BoardCapabilityError

SYSFS_ROOT = "/sys"
HWMON_DIR = "class/hwmon"
IIO_DIR = "bus/iio/devices"

# hwmon sysfs ABI (Documentation/hwmon/sysfs-interface): integer in these units.
HWMON_UNITS: dict[str, tuple[float, str]] = {
    "temp": (1000, "C"),  # millidegree Celsius
    "humidity": (1000, "%RH"),  # milli-percent
    "in": (1000, "V"),  # millivolt
    "curr": (1000, "A"),  # milliampere
    "power": (1_000_000, "W"),  # microwatt
    "energy": (1_000_000, "J"),  # microjoule
    "fan": (1, "RPM"),
}

# IIO sysfs ABI (Documentation/ABI/testing/sysfs-bus-iio): `(raw + offset) * scale`,
# or `_input`, is in these units.
IIO_UNITS: dict[str, tuple[float, str]] = {
    "temp": (1000, "C"),  # millidegree Celsius
    "humidityrelative": (1000, "%RH"),  # milli-percent
    "pressure": (1, "kPa"),
    "voltage": (1000, "V"),  # millivolt
    "current": (1000, "A"),  # milliampere
    "illuminance": (1, "lx"),
    "accel": (1, "m/s^2"),
    "anglvel": (1, "rad/s"),
}

MAPPING_HINT = (
    "label the channel after the sensor in the device tree, or map it by name: "
    "LinuxHAL(sensor_sources={...}) or NEUROEDGE_LINUX_SENSORS="
    "'temperature=hwmon:lm75/temp1;humidity=iio:bme280/humidityrelative'"
)

_SOURCE = re.compile(r"^(hwmon|iio):([^/@\s]+)(?:@([^/\s]+))?/([a-z][a-z0-9_]*)$")


@dataclass(frozen=True)
class SensorSource:
    """Where a board sensor lives in sysfs, by device name and channel."""

    kind: str  # "hwmon" or "iio"
    device: str  # the device's `name` file
    channel: str  # temp1, humidityrelative, voltage0 …
    at: str | None = None  # the kernel device it sits on, e.g. 1-0048

    @classmethod
    def parse(cls, sensor: str, spec: str, where: str) -> SensorSource:
        match = _SOURCE.match(spec.strip())
        if match is None:
            raise BoardCapabilityError(
                where=f"{where} -> sensor {sensor!r}",
                why=f"{spec!r} is not a sensor source",
                how="write hwmon:<name>/<channel> or iio:<name>/<channel>, e.g. hwmon:lm75/temp1",
            )
        kind, device, at, channel = match.groups()
        return cls(kind, device, channel, at)

    def __str__(self) -> str:
        at = f"@{self.at}" if self.at else ""
        return f"{self.kind}:{self.device}{at}/{self.channel}"


def parse_sources(text: str, where: str) -> dict[str, str]:
    """`temperature=hwmon:lm75/temp1;humidity=iio:bme280/humidityrelative` → a mapping."""
    sources: dict[str, str] = {}
    for item in filter(None, (part.strip() for part in text.split(";"))):
        sensor, sep, spec = item.partition("=")
        if not sep or not sensor.strip() or not spec.strip():
            raise BoardCapabilityError(
                where=where,
                why=f"{item!r} is not sensor=source",
                how="separate entries with ';', e.g. temperature=hwmon:lm75/temp1",
            )
        sources[sensor.strip()] = spec.strip()
    return sources


@dataclass(frozen=True)
class Reading:
    value: float
    unit: str
    path: str  # the file the value came from, for error messages


@dataclass(frozen=True)
class _Channel:
    kind: str
    directory: Path
    channel: str
    found_by: str  # how it was found, for error messages

    def describe(self) -> str:
        return f"{self.directory / self.channel} ({self.found_by})"


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeDecodeError):
        return None


def _sits_on(kind: str, directory: Path) -> str:
    """
    The kernel device a sensor sits on (``1-0048``). A hwmon class device points at
    it through its ``device`` link; an IIO device is a child of it, and has no link.
    """
    if kind == "hwmon":
        return os.path.basename(os.path.realpath(directory / "device"))
    return os.path.basename(os.path.dirname(os.path.realpath(directory)))


def _channel_type(channel: str) -> str:
    match = re.match(r"[a-z]+", channel)
    return match.group(0) if match else channel


class SysfsSensors:
    """Board sensors read from hwmon and IIO under `root` (a fake tree in the tests)."""

    def __init__(
        self, root: str | Path | None = None, sources: Mapping[str, str] | None = None
    ) -> None:
        self.root = Path(root if root is not None else SYSFS_ROOT)
        self.sources = {
            sensor: SensorSource.parse(sensor, spec, "LinuxHAL sensor_sources")
            for sensor, spec in (sources or {}).items()
        }

    # -- finding the channel ---------------------------------------------------------
    def _devices(self, kind: str) -> list[Path]:
        base = self.root / (HWMON_DIR if kind == "hwmon" else IIO_DIR)
        pattern = "hwmon*" if kind == "hwmon" else "iio:device*"
        return sorted(base.glob(pattern)) if base.is_dir() else []

    def locate(self, sensor: str, where: str) -> _Channel:
        source = self.sources.get(sensor)
        return self._by_source(sensor, source, where) if source else self._by_label(sensor, where)

    def _by_source(self, sensor: str, source: SensorSource, where: str) -> _Channel:
        devices = self._devices(source.kind)
        named = [d for d in devices if _read_text(d / "name") == source.device]
        if source.at is not None:
            named = [d for d in named if _sits_on(source.kind, d) == source.at]
        if not named:
            seen = sorted({_read_text(d / "name") or "?" for d in devices})
            raise BoardCapabilityError(
                where=f"{where} ({source})",
                why=(
                    f"no {source.kind} device named {source.device!r}"
                    f"{f' on {source.at}' if source.at else ''} under {self.root}; "
                    f"found {seen or 'none'}"
                ),
                how="check the driver is bound (dmesg, /sys/bus/i2c/devices), or fix the source",
            )
        if len(named) > 1:
            ats = [_sits_on(source.kind, d) for d in named]
            raise BoardCapabilityError(
                where=f"{where} ({source})",
                why=f"{len(named)} {source.kind} devices are named {source.device!r} (on {ats})",
                how=f"say which one: {source.kind}:{source.device}@<device>/{source.channel}",
            )
        return _Channel(source.kind, named[0], source.channel, f"source {source}")

    def _by_label(self, sensor: str, where: str) -> _Channel:
        found: list[_Channel] = []
        for directory in self._devices("hwmon"):
            for label in sorted(directory.glob("*_label")):
                if _read_text(label) == sensor:
                    channel = label.name[: -len("_label")]
                    found.append(_Channel("hwmon", directory, channel, f"{label.name} = {sensor}"))
        for directory in self._devices("iio"):
            for label in sorted(directory.glob("in_*_label")):
                if _read_text(label) == sensor:
                    channel = label.name[len("in_") : -len("_label")]
                    found.append(_Channel("iio", directory, channel, f"{label.name} = {sensor}"))
            if _read_text(directory / "label") == sensor:
                channels = self._iio_channels(directory)
                if len(channels) == 1:
                    found.append(_Channel("iio", directory, channels[0], f"label = {sensor}"))
                else:
                    raise BoardCapabilityError(
                        where=f"{where} ({directory})",
                        why=f"the IIO device labelled {sensor!r} has channels {channels}, not one",
                        how=f"map the sensor to one of them; {MAPPING_HINT}",
                    )
        if not found:
            raise BoardCapabilityError(
                where=where,
                why=(
                    f"no hwmon or IIO channel under {self.root} is labelled {sensor!r}, and the "
                    "sensor has no source; refusing to invent a reading (Q-16)"
                ),
                how=MAPPING_HINT,
            )
        if len(found) > 1:
            raise BoardCapabilityError(
                where=where,
                why=f"{len(found)} channels are labelled {sensor!r}: {[c.describe() for c in found]}",
                how=f"map the sensor to one of them; {MAPPING_HINT}",
            )
        return found[0]

    @staticmethod
    def _iio_channels(directory: Path) -> list[str]:
        names = set()
        for path in directory.glob("in_*"):
            for suffix in ("_raw", "_input"):
                if path.name.endswith(suffix):
                    names.add(path.name[len("in_") : -len(suffix)])
        return sorted(names)

    # -- reading it ------------------------------------------------------------------
    def read(self, sensor: str, where: str) -> Reading:
        channel = self.locate(sensor, where)
        if channel.kind == "hwmon":
            return self._read_hwmon(channel, where)
        return self._read_iio(channel, where)

    def _number(self, path: Path, where: str, channel: _Channel, cast=float) -> float:
        try:
            text = path.read_text(encoding="ascii").strip()
        except FileNotFoundError:
            raise BoardCapabilityError(
                where=f"{where} ({channel.describe()})",
                why=f"{path} does not exist",
                how="check the channel name against the files the driver creates",
            ) from None
        except (OSError, UnicodeDecodeError) as exc:
            raise BoardCapabilityError(
                where=f"{where} ({channel.describe()})",
                why=f"cannot read {path}: {getattr(exc, 'strerror', None) or exc}",
                how="check the sensor is wired and powered, and the user may read sysfs",
            ) from exc
        try:
            value = cast(text)
            # float() takes "nan" and "inf": a comparison against NaN is always False,
            # so a gate fact such as `gte = 80` would read False and allow.
            if not math.isfinite(value):
                raise ValueError(text)
        except ValueError:
            raise BoardCapabilityError(
                where=f"{where} ({channel.describe()})",
                why=f"{path} holds {text!r}, not a number",
                how="check the driver; a sensor that does not report a number is not read",
            ) from None
        return value

    def _units(self, table, kind: str, channel: _Channel, where: str) -> tuple[float, str]:
        kind_type = _channel_type(channel.channel)
        if kind_type not in table:
            raise BoardCapabilityError(
                where=f"{where} ({channel.describe()})",
                why=f"{kind} channel type {kind_type!r} has no known unit",
                how=f"read one of the types {sorted(table)}",
            )
        return table[kind_type]

    def _read_hwmon(self, channel: _Channel, where: str) -> Reading:
        divisor, unit = self._units(HWMON_UNITS, "hwmon", channel, where)
        fault = channel.directory / f"{channel.channel}_fault"
        if fault.exists() and self._number(fault, where, channel, int) != 0:
            raise BoardCapabilityError(
                where=f"{where} ({channel.describe()})",
                why=f"the driver flags {fault.name}: the reading is not valid",
                how="check the sensor's wiring (an open or shorted probe)",
            )
        path = channel.directory / f"{channel.channel}_input"
        raw = self._number(path, where, channel, int)
        return Reading(raw / divisor, unit, str(path))

    def _read_iio(self, channel: _Channel, where: str) -> Reading:
        divisor, unit = self._units(IIO_UNITS, "IIO", channel, where)
        directory, name = channel.directory, channel.channel
        processed = directory / f"in_{name}_input"
        if processed.exists():
            value = self._number(processed, where, channel)
            return Reading(round(value / divisor, 9), unit, str(processed))
        raw_path = directory / f"in_{name}_raw"
        raw = self._number(raw_path, where, channel)
        # A missing scale or offset means 1 and 0 (IIO ABI); an unreadable one fails.
        shared = _channel_type(name)
        scale = self._attribute(directory, name, shared, "scale", 1.0, where, channel)
        offset = self._attribute(directory, name, shared, "offset", 0.0, where, channel)
        value = (raw + offset) * scale / divisor
        if not math.isfinite(value):  # finite inputs can still overflow
            raise BoardCapabilityError(
                where=f"{where} ({channel.describe()})",
                why=f"({raw} + {offset}) * {scale} is not a finite number",
                how="check the driver's scale and offset",
            )
        return Reading(round(value, 9), unit, str(raw_path))

    def _attribute(self, directory, name, shared, attr, absent, where, channel) -> float:
        for candidate in (f"in_{name}_{attr}", f"in_{shared}_{attr}"):
            path = directory / candidate
            if path.exists():
                return self._number(path, where, channel)
        return absent
