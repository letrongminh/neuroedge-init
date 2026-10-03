"""
PWM and the state-feedback channel of `digital.out` (RFC-0010, TSK-W1-01).

PWM is not a primitive of its own: it is a block of `digital.out` (`board.v1`
`digital_out.pwm`), commanded with `operation = "pwm"` and read back with `state()`. This module
holds what both targets share:

* `PwmLimits` — the board's hard limits of one channel (frequency range, resolution,
  `max_duty`, the HAL-owned `enable_pin`);
* `check_pwm` — the board-limit check of one command, run **before** the envelope and
  `authorize`, so a refused command reserves nothing and spends no token (§3b);
* `quantize_duty` — the duty the hardware can express, always rounded toward zero (§9.15), so
  quantisation can never carry a duty past `max_duty`;
* `PinState` — what `state()` returns: each quantity (`duty`, `frequency_hz`) with the
  `source` of the number, `measured` (read back from the hardware of a pin in
  `feedback.pins`) or `commanded` (what the HAL last wrote). A failed read-back is
  `PerceptionUnavailableError`, never the commanded value (§9.4, §9.12);
* `SysfsPwm` — the `linux` backend: the kernel's PWM (`/sys/class/pwm`) and nothing else.
  There is no bit-banged PWM (§9.1): a board that declares `pwm` on a kernel without the
  channel is refused where the agent is loaded, not run on a software fallback.

The enable line is the HAL's: it is raised only while a gated PWM command runs and dropped on
`off`, at the end of the on-time, on `close()` and when the supervisor loses the runtime
(§9.2). The duty that reaches the gate as a fact is always a `measured` one.
"""

from __future__ import annotations

import math
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..errors import BoardCapabilityError, PerceptionUnavailableError

if TYPE_CHECKING:
    from .board import BoardProfile

__all__ = [
    "COMMANDED",
    "MEASURED",
    "PWM_ENV",
    "PinState",
    "PwmLimits",
    "SysfsPwm",
    "check_pwm",
    "parse_channels",
    "pin_state_data",
    "pwm_limits",
    "quantize_duty",
]

MEASURED = "measured"
COMMANDED = "commanded"
PWM_ENV = "NEUROEDGE_LINUX_PWM"  # fan=pwmchip0/2;…
PWM_ROOT = "class/pwm"
EXPORT_WAIT_S = 1.0
# The scale of each read-back quantity (RFC-0010 §3b): `duty` is a ratio on [0, max_duty],
# `frequency_hz` is in Hz on the board's own range. `build` checks a criterion against these.
QUANTITIES = ("duty", "frequency_hz")


@dataclass(frozen=True)
class PwmLimits:
    """The hard limits `board.v1` declares for one PWM channel."""

    pin: str
    frequency_min: int
    frequency_max: int
    resolution_bits: int
    max_duty: float
    enable_pin: str
    max_continuous_ms: float | None = None  # the channel's envelope, when it has one

    def scale(self, quantity: str) -> tuple[str, float, float]:
        """`(unit, min, max)` of a read-back quantity."""
        if quantity == "duty":
            return "ratio", 0.0, self.max_duty
        if quantity == "frequency_hz":
            return "Hz", float(self.frequency_min), float(self.frequency_max)
        raise KeyError(quantity)


def pwm_limits(board: BoardProfile, pin: str) -> PwmLimits | None:
    """The limits of `pin` when it is one of the board's PWM channels, else None."""
    if pin not in board.pwm_pins:
        return None
    pwm = board.capabilities["digital_out"]["pwm"]
    envelope = board.envelope(pin)
    return PwmLimits(
        pin=pin,
        frequency_min=pwm["frequency_hz"]["min"],
        frequency_max=pwm["frequency_hz"]["max"],
        resolution_bits=pwm["resolution_bits"],
        max_duty=float(pwm["max_duty"]),
        enable_pin=pwm["enable_pin"][pin]["pin"],
        max_continuous_ms=None if envelope is None else envelope["max_continuous_ms"],
    )


def quantize_duty(duty: float, resolution_bits: int) -> float:
    """
    The duty the counter can hold: a whole number of `2**resolution_bits` steps, rounded
    toward zero. Rounding down is the safe direction — a quantised duty never exceeds the one
    that was checked against `max_duty` (RFC-0010 §9.15).
    """
    steps = 1 << resolution_bits
    return math.floor(duty * steps) / steps


def _refuse(where: str, why: str, how: str) -> BoardCapabilityError:
    return BoardCapabilityError(where=where, why=why, how=how)


def check_pwm(
    board: BoardProfile,
    pin: str,
    operation: str,
    duration_ms: Any,
    frequency_hz: Any,
    duty: Any,
    called_from: str,
) -> tuple[str, int, float]:
    """
    The board's side of a command on `pin`, before the envelope and `authorize` (RFC-0010 §3b).
    Returns the `(operation, duration_ms, duty)` to carry out; raises `BoardCapabilityError`
    (NE3001, nothing reserved, no token spent) for:

    * `on` or `pulse` on a PWM channel — they would drive a 100 % duty past `max_duty`;
    * `pwm` on a pin that is not a PWM channel;
    * a `pwm` command without a positive integer `duration_ms` (there is no PWM that runs
      forever), a `frequency_hz` outside the board's range, or a `duty` that is not a finite
      ratio in `[0, max_duty]`.

    A duty that quantises to zero is the safe state, so it is returned as `off`: it needs no
    token and is never refused (§9.6). Any other operation is returned as it came.
    """
    where = f"{called_from} -> digital.out {pin!r}"
    limits = pwm_limits(board, pin)
    if operation == "pwm":
        if limits is None:
            raise _refuse(
                where,
                f"{pin!r} is not a PWM channel of board {board.id!r} "
                f"(it has {list(board.pwm_pins) or 'none'})",
                "use a pin listed in [capabilities.digital_out.pwm].pins, or on/off/pulse for this one",
            )
        for name, value, kind in (
            ("frequency_hz", frequency_hz, "integer"),
            ("duty", duty, "number"),
        ):
            if value is None:
                raise _refuse(where, f"a pwm command needs {name}", f"pass {name}")
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise _refuse(where, f"{name} must be a {kind}, found {value!r}", f"pass a {kind}")
        if isinstance(duration_ms, bool) or not isinstance(duration_ms, int) or duration_ms <= 0:
            raise _refuse(
                where,
                f"a pwm command needs a positive integer duration_ms, found {duration_ms!r}; "
                "there is no PWM that runs forever (RFC-0010 §9.5)",
                "pass duration_ms=<milliseconds>, e.g. digital.out('fan').pwm(frequency_hz=1000, "
                "duty=0.4, ms=5000)",
            )
        if not float(frequency_hz).is_integer():
            raise _refuse(
                where,
                f"frequency_hz {frequency_hz!r} is not a whole number of Hz",
                "pass an integer",
            )
        frequency = int(frequency_hz)
        if not limits.frequency_min <= frequency <= limits.frequency_max:
            raise _refuse(
                where,
                f"frequency_hz {frequency} is outside the {limits.frequency_min}..{limits.frequency_max} Hz "
                f"board {board.id!r} declares for {pin!r}",
                "use a frequency inside the channel's range",
            )
        if not math.isfinite(duty) or not 0.0 <= duty <= 1.0:
            raise _refuse(
                where, f"duty {duty!r} is not a ratio in [0, 1]", "pass 0.0 <= duty <= max_duty"
            )
        if duty > limits.max_duty:
            raise _refuse(
                where,
                f"duty {duty} is above max_duty {limits.max_duty} of {pin!r}, the hard ceiling of its "
                f"load on board {board.id!r}",
                f"ask for at most {limits.max_duty}; a gate may narrow this, never widen it",
            )
        applied = quantize_duty(float(duty), limits.resolution_bits)
        if applied == 0.0:
            return "off", 0, 0.0
        return "pwm", duration_ms, applied
    if limits is not None and operation in ("on", "pulse"):
        raise _refuse(
            where,
            f"{operation!r} on {pin!r}, a PWM channel of board {board.id!r}, would drive it at a 100 % "
            f"duty, past max_duty {limits.max_duty}; a PWM channel takes only 'pwm' and 'off'",
            "command it with digital.out(pin).pwm(frequency_hz=..., duty=..., ms=...), or off()",
        )
    return operation, duration_ms, 0.0


@dataclass(frozen=True)
class PinState:
    """
    One `state()` of a `digital.out` pin: each quantity with the `source` of the numbers.
    `values` holds `None` for a quantity the pin has no value for now (the frequency of a
    channel that is off). Never `commanded` where the board declares `feedback` for the pin:
    then it is `measured`, or the read raised `PerceptionUnavailableError`.
    """

    pin: str
    source: str
    values: Mapping[str, float | bool | None]
    read_ms: float | None = None

    @property
    def duty(self) -> float | None:
        value = self.values.get("duty")
        return None if value is None else float(value)

    @property
    def frequency_hz(self) -> float | None:
        value = self.values.get("frequency_hz")
        return None if value is None else float(value)


def pin_state_data(
    pin: str,
    state: PinState | None = None,
    *,
    reason: str | None = None,
    use: str | None = None,
) -> dict[str, Any]:
    """`pin_state` event data, the same on every target: `{pin, source, <quantity>…}` or `{pin, reason}`."""
    data: dict[str, Any] = {"pin": pin}
    if state is None:
        data["reason"] = reason or "the pin's state could not be read"
    else:
        data["source"] = state.source
        data.update({k: v for k, v in state.values.items() if v is not None})
    if use is not None:
        data["use"] = use
    return data


def parse_channels(text: str, where: str) -> dict[str, str]:
    """`fan=pwmchip0/2;…` → a mapping from board PWM pin to its kernel `chip/channel`."""
    channels: dict[str, str] = {}
    for item in filter(None, (part.strip() for part in text.split(";"))):
        pin, sep, channel = item.partition("=")
        if not sep or not pin.strip() or not channel.strip():
            raise _refuse(
                where,
                f"{item!r} is not pin=pwmchipN/channel",
                "separate entries with ';', e.g. fan=pwmchip0/2",
            )
        channels[pin.strip()] = channel.strip()
    return channels


class SysfsPwm:
    """
    The kernel's PWM sysfs (`<root>/class/pwm/pwmchipN/pwmM/{period,duty_cycle,enable}`),
    one board PWM pin per `pwmchipN/M`. Every access goes to the files again, so a channel
    that vanished fails instead of answering from an old path. Writing order keeps the
    kernel's `duty_cycle <= period` rule: the duty goes to zero before the period changes.
    """

    def __init__(
        self, sysfs_root: str | Path | None, mapping: Mapping[str, str], where: str
    ) -> None:
        self.root = Path(sysfs_root if sysfs_root is not None else "/sys") / PWM_ROOT
        self.channels: dict[str, tuple[str, int]] = {}
        for pin, spec in mapping.items():
            chip, _, channel = spec.partition("/")
            if not chip.startswith("pwmchip") or not channel.isdigit():
                raise _refuse(
                    f"{where} -> {pin}",
                    f"{spec!r} is not a kernel PWM channel",
                    "write pwmchipN/M, e.g. pwmchip0/2",
                )
            self.channels[pin] = (chip, int(channel))

    def _where(self, pin: str, called_from: str) -> str:
        return f"{called_from} -> digital.out {pin!r}"

    def _channel(self, pin: str, called_from: str) -> tuple[str, int]:
        if pin not in self.channels:
            raise _refuse(
                self._where(pin, called_from),
                f"no kernel PWM channel is chosen for {pin!r} on this machine; refusing to guess one "
                "(the chip and channel of a pin differ between boards and kernels)",
                f"set {PWM_ENV}='{pin}=pwmchip0/0' on the device, or pass "
                f"LinuxHAL(pwm_channels={{'{pin}': 'pwmchip0/0'}})",
            )
        return self.channels[pin]

    def check(self, pin: str, called_from: str = "<unknown>") -> None:
        """The channel exists in this kernel: refuse now, with no software PWM to fall back on (§9.1)."""
        chip, channel = self._channel(pin, called_from)
        try:
            count = int((self.root / chip / "npwm").read_text(encoding="utf-8").strip())
        except (OSError, ValueError) as exc:
            raise _refuse(
                self._where(pin, called_from),
                f"the kernel has no PWM chip {chip!r} under {self.root} ({exc})",
                "enable the hardware PWM overlay (e.g. dtoverlay=pwm on a Pi); PWM is never "
                "bit-banged (RFC-0010 §9.1)",
            ) from exc
        if not 0 <= channel < count:
            raise _refuse(
                self._where(pin, called_from),
                f"{chip} has {count} channel(s), and {pin!r} is mapped to channel {channel}",
                "fix the mapping, or the overlay",
            )

    def _dir(self, pin: str, called_from: str) -> Path:
        chip, channel = self._channel(pin, called_from)
        directory = self.root / chip / f"pwm{channel}"
        if not directory.is_dir():
            (self.root / chip / "export").write_text(f"{channel}\n", encoding="utf-8")
            deadline = time.monotonic() + EXPORT_WAIT_S
            while not directory.is_dir():
                if time.monotonic() > deadline:
                    raise OSError(f"{directory} did not appear after export")
                time.sleep(0.02)
        return directory

    @staticmethod
    def _write(directory: Path, name: str, value: int) -> None:
        (directory / name).write_text(f"{value}\n", encoding="utf-8")

    def apply(
        self, pin: str, frequency_hz: int, duty: float, called_from: str = "<unknown>"
    ) -> None:
        """Program period and duty, then enable the channel. `OSError` when the kernel refuses."""
        directory = self._dir(pin, called_from)
        period = round(1e9 / frequency_hz)
        # Toward zero again: the nanosecond duty never exceeds the checked ratio.
        duty_ns = min(math.floor(duty * period), period)
        self._write(directory, "duty_cycle", 0)
        self._write(directory, "period", period)
        self._write(directory, "duty_cycle", duty_ns)
        self._write(directory, "enable", 1)

    def off(self, pin: str, called_from: str = "<unknown>") -> None:
        """
        Disable the channel and zero its duty. `OSError` when the kernel refuses. A channel
        that was never exported is not running, so there is nothing to disable (and nothing to
        export just to switch it off).
        """
        chip, channel = self._channel(pin, called_from)
        directory = self.root / chip / f"pwm{channel}"
        if not directory.is_dir():
            return
        self._write(directory, "enable", 0)
        self._write(directory, "duty_cycle", 0)

    def read(
        self, pin: str, limits: PwmLimits, called_from: str = "<unknown>"
    ) -> dict[str, float | None]:
        """
        What the PWM controller reports it is outputting: `duty` as a ratio (0 when the channel
        is disabled), `frequency_hz` (None when disabled). Anything the files do not hold as
        consistent numbers — an unreadable file, a duty above the period or above `max_duty`, a
        frequency outside the board's range — is `PerceptionUnavailableError`.
        """
        where = self._where(pin, called_from)
        try:
            directory = self._dir(pin, called_from)

            def number(name: str) -> int:
                return int((directory / name).read_text(encoding="utf-8").strip())

            enabled, period, duty_ns = number("enable"), number("period"), number("duty_cycle")
        except (OSError, ValueError) as exc:
            raise PerceptionUnavailableError(
                where=where,
                why=f"the kernel PWM channel of {pin!r} cannot be read back: {exc}",
                how="check the PWM overlay and the channel mapping; the criterion stays undecided",
            ) from exc
        if enabled not in (0, 1) or period < 0 or not 0 <= duty_ns <= max(period, 0):
            raise PerceptionUnavailableError(
                where=where,
                why=f"inconsistent PWM registers (enable={enabled}, period={period}, duty_cycle={duty_ns})",
                how="the controller is in a state the HAL did not set; reset the channel",
            )
        if not enabled or period == 0:
            return {"duty": 0.0, "frequency_hz": None}
        duty = duty_ns / period
        frequency = 1e9 / period
        # A hair over for the nanosecond rounding of the period, never more.
        if duty > limits.max_duty + 1.0 / period or not (
            limits.frequency_min * 0.999 <= frequency <= limits.frequency_max * 1.001
        ):
            raise PerceptionUnavailableError(
                where=where,
                why=f"the channel reads back duty {duty:.4f} at {frequency:.0f} Hz, outside what the "
                f"board allows (max_duty {limits.max_duty}, {limits.frequency_min}..{limits.frequency_max} Hz)",
                how="the output is not what was commanded; the HAL never reports it as a valid measurement",
            )
        return {"duty": duty, "frequency_hz": float(round(frequency))}
