"""
HAL backend for target `linux` (TSK-S3-05, FR-TGT-02, Q-16).

`digital.out` drives real GPIO lines through the kernel character device, via
the libgpiod v2 Python bindings (`pip install 'neuroedge[linux]'`). The
bindings are LGPL-2.1-or-later: they are an optional extra, imported at run
time and never vendored, so the MIT core carries no LGPL code (NOTICE §B).

In CI the lines are **gpio-sim** virtual lines (`scripts/setup_gpio_sim.sh`);
on the nightly rig they are a Raspberry Pi 5's. Each board pin is found by
line *name* — `door_lock` on gpio-sim, or whatever `line_names` maps it to
(e.g. ``{"door_lock": "GPIO17"}`` on a Pi).

Q-16: with no `/dev/gpiochip*` the HAL **raises**. A HAL that silently did
nothing would turn every Action CI run on a misconfigured runner into a pass.

A pulse sets the line active and returns immediately; a timer makes it
inactive after the duration. `PendingCommand.cancel()` drops the line at once
(RB-3, barge-in). `close()` releases every line inactive.
"""

from __future__ import annotations

import glob
import threading
from collections.abc import Mapping
from typing import Any

from ..errors import BoardCapabilityError
from . import Authorizer, HardwareAbstractionLayer, _require_signature
from .board import BoardProfile, load_board_by_id
from .sim import EventSink, PendingCommand, _NullSink

CHIP_GLOB = "/dev/gpiochip*"
SETUP_HINT = (
    "connect the board, or create virtual lines with scripts/setup_gpio_sim.sh "
    "(gpio-sim, kernel >= 5.19)"
)


def _import_gpiod() -> Any:
    try:
        import gpiod
    except ImportError as exc:
        raise BoardCapabilityError(
            where="LinuxHAL.__init__",
            why="the libgpiod v2 Python bindings (`gpiod`) are not installed",
            how="pip install 'neuroedge[linux]' (LGPL-2.1, optional; see NOTICE §B)",
        ) from exc
    return gpiod


class LinuxHAL(HardwareAbstractionLayer):
    def __init__(
        self,
        board: BoardProfile | None = None,
        *,
        events: EventSink | None = None,
        authorize: Authorizer = _require_signature,
        line_names: Mapping[str, str] | None = None,
        chip_glob: str | None = None,
        gpiod: Any = None,
        consumer: str = "neuroedge",
    ) -> None:
        board = board if board is not None else load_board_by_id("linux-rpi5")
        if board.target != "linux":
            raise BoardCapabilityError(
                where=f"LinuxHAL(board={board.id!r})",
                why=f"board {board.id!r} targets {board.target!r}, not 'linux'",
                how="use a linux board such as linux-rpi5, or the HAL for that target",
            )
        super().__init__(target="linux", board=board, authorize=authorize)
        self.events: EventSink = events if events is not None else _NullSink()
        self._gpiod = gpiod if gpiod is not None else _import_gpiod()
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

        chip_glob = chip_glob or CHIP_GLOB
        chips = sorted(glob.glob(chip_glob))
        if not chips:
            raise BoardCapabilityError(
                where="LinuxHAL.__init__",
                why=f"no GPIO chip found at {chip_glob}; refusing to run as a no-op (Q-16)",
                how=SETUP_HINT,
            )
        names = {pin: (line_names or {}).get(pin, pin) for pin in board.pins}
        self.lines: dict[str, tuple[str, int]] = {}
        for pin, name in names.items():
            location = self._find(chips, name)
            if location is not None:
                self.lines[pin] = location
        missing = sorted(set(names) - set(self.lines))
        if missing:
            raise BoardCapabilityError(
                where="LinuxHAL.__init__",
                why=(
                    f"no line named {[names[p] for p in missing]} on {chips} for board "
                    f"pins {missing} of {board.id!r}"
                ),
                how=f"name the lines after the pins (setup_gpio_sim.sh does), or pass line_names; {SETUP_HINT}",
            )
        self._requests = self._request_outputs(consumer)

    def _find(self, chips: list[str], name: str) -> tuple[str, int] | None:
        for path in chips:
            chip = self._gpiod.Chip(path)
            try:
                return path, int(chip.line_offset_from_id(name))
            except (OSError, ValueError, KeyError):
                continue
            finally:
                chip.close()
        return None

    def _request_outputs(self, consumer: str) -> dict[str, Any]:
        line = self._gpiod.line
        settings = self._gpiod.LineSettings(
            direction=line.Direction.OUTPUT, output_value=line.Value.INACTIVE
        )
        by_chip: dict[str, list[int]] = {}
        for path, offset in self.lines.values():
            by_chip.setdefault(path, []).append(offset)
        return {
            path: self._gpiod.request_lines(
                path, consumer=consumer, config={tuple(offsets): settings}
            )
            for path, offsets in by_chip.items()
        }

    # -- the line itself -------------------------------------------------------------
    def _set(self, pin: str, active: bool) -> None:
        path, offset = self.lines[pin]
        value = self._gpiod.line.Value
        self._requests[path].set_value(offset, value.ACTIVE if active else value.INACTIVE)

    def line_value(self, pin: str) -> bool:
        """What the line is driven to right now (True = active)."""
        path, offset = self.lines[pin]
        return self._requests[path].get_value(offset) == self._gpiod.line.Value.ACTIVE

    def _stop_timer(self, pin: str) -> None:
        with self._lock:
            timer = self._timers.pop(pin, None)
        if timer is not None:
            timer.cancel()

    def _end_pulse(self, pin: str, timer: threading.Timer | None = None) -> None:
        with self._lock:
            if timer is not None and self._timers.get(pin) is not timer:
                return  # a newer command owns the line
            self._timers.pop(pin, None)
        self._set(pin, False)

    # -- digital.out -----------------------------------------------------------------
    def digital_out(
        self,
        pin: str,
        operation: str,
        duration_ms: int = 0,
        signature: Any = "",
        called_from: str = "<unknown>",
    ) -> PendingCommand:
        if operation not in ("pulse", "on", "off"):
            raise BoardCapabilityError(
                where=f"{called_from} -> digital.out {pin!r}",
                why=f"unknown operation {operation!r}",
                how="use one of 'pulse', 'on', 'off'",
            )
        super().digital_out(pin, operation, duration_ms, signature, called_from)
        self._stop_timer(pin)
        self._set(pin, operation != "off")
        if operation == "pulse":
            timer = threading.Timer(duration_ms / 1000.0, lambda: self._end_pulse(pin, timer))
            timer.daemon = True
            with self._lock:
                self._timers[pin] = timer
            timer.start()
        self.events.emit(
            "actuator_command", {"pin": pin, "operation": operation, "duration_ms": duration_ms}
        )
        return PendingCommand(
            pin, operation, duration_ms, self.events, on_cancel=lambda: self._abort(pin)
        )

    def _abort(self, pin: str) -> None:
        self._stop_timer(pin)
        self._set(pin, False)

    def close(self) -> None:
        """Drop every line inactive and release it. The session is over; nothing is recorded."""
        if not self._requests:
            return
        for pin in list(self._timers):
            self._stop_timer(pin)
        for pin in self.lines:
            self._set(pin, False)
        for request in self._requests.values():
            request.release()
        self._requests = {}
