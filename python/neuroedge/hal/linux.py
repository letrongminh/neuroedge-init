"""
HAL backend for target `linux` (TSK-S3-05, FR-TGT-02, Q-16).

`digital.out` drives real GPIO lines through the kernel character device, via
the libgpiod v2 Python bindings (`pip install 'neuroedge[linux]'`). The
bindings are LGPL-2.1-or-later: they are an optional extra, imported at run
time and never vendored, so the core carries no LGPL code (NOTICE §B).

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
from collections import deque
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


def _chip_error(path: str, exc: OSError) -> BoardCapabilityError:
    return BoardCapabilityError(
        where=f"LinuxHAL.__init__ -> {path}",
        why=f"cannot open the GPIO chip or its lines: {exc.strerror or exc}",
        how=(
            "check the user may read and write the chip (group `gpio`, or "
            "setup_gpio_sim.sh's chmod), and that no other process holds the lines "
            "(an earlier `neuroedge mcp serve` still running)"
        ),
    )


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
        denied: tuple[str, OSError] | None = None
        for path in chips:
            try:
                chip = self._gpiod.Chip(path)
            except OSError as exc:
                denied = denied or (path, exc)  # another chip may carry the line
                continue
            try:
                return path, int(chip.line_offset_from_id(name))
            except (OSError, ValueError, KeyError):
                continue
            finally:
                chip.close()
        if denied is not None:
            raise _chip_error(*denied) from denied[1]
        return None

    def _request_outputs(self, consumer: str) -> dict[str, Any]:
        line = self._gpiod.line
        settings = self._gpiod.LineSettings(
            direction=line.Direction.OUTPUT, output_value=line.Value.INACTIVE
        )
        by_chip: dict[str, list[int]] = {}
        for path, offset in self.lines.values():
            by_chip.setdefault(path, []).append(offset)
        requests: dict[str, Any] = {}
        for path, offsets in by_chip.items():
            try:
                requests[path] = self._gpiod.request_lines(
                    path, consumer=consumer, config={tuple(offsets): settings}
                )
            except OSError as exc:
                for held in requests.values():
                    held.release()
                raise _chip_error(path, exc) from exc
        return requests

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
            if not self._requests:
                return  # close() has already dropped and released every line
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
        # One line that fails to drop must not leave the others active or held.
        errors: list[OSError] = []
        for pin in self.lines:
            try:
                self._set(pin, False)
            except OSError as exc:
                errors.append(exc)
        with self._lock:  # a pulse ending now sees no requests and leaves the line alone
            requests, self._requests = self._requests, {}
        for request in requests.values():
            try:
                request.release()
            except OSError as exc:
                errors.append(exc)
        if errors:
            raise errors[0]


# Primitives `LinuxHAL` does not implement yet, and the task that brings each. An
# interactive session refuses an agent that needs one before any line is requested,
# rather than failing mid-session on the first turn that reaches it (Q-16).
MISSING_ON_LINUX = {
    "audio.in": "TSK-S5-08",
    "audio.out": "TSK-S5-08",
    "sensor.read": "TSK-S5-09",
    "display": "TSK-S5-09",
}


class TypedLinuxHAL(LinuxHAL):
    """
    `LinuxHAL` for an interactive session — `run`, `record`, `mcp serve` (TSK-S5-10).

    The pins are real kernel lines. The person types on the terminal, as on `sim`
    (Q-15): a typed line is the session's input and a reply is printed, with the
    same `text_input` / `tts_stream_start` events `SimHAL` writes, so a session
    recorded here has the shape of a `sim` one and replays on either target.
    Nothing is heard or spoken: microphone and speaker are TSK-S5-08.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._typed: deque[str] = deque()
        self.spoken: list[str] = []
        self.frames: list[Any] = []  # no `display` on linux yet (TSK-S5-09)

    def type_text(self, text: str) -> None:
        self._typed.append(text)

    def audio_in(self, called_from: str = "<unknown>") -> str | None:
        if not self._typed:
            return None
        text = self._typed.popleft()
        self.events.emit("text_input", {"text": text})
        return text

    def audio_out(self, text: str, called_from: str = "<unknown>") -> None:
        self.spoken.append(text)
        self.events.emit("tts_stream_start", {"text": text})

    def pulsing(self) -> list[str]:
        """The pins whose pulse is still in flight."""
        with self._lock:
            return sorted(self._timers)

    def driven(self) -> list[str]:
        """The pins whose line is active right now."""
        return [pin for pin in self.lines if self._requests and self.line_value(pin)]

    def settle(self) -> None:
        """
        Wait for every pulse in flight to end on its own. `run -c` does, so the one
        command it ran drives its line for the whole duration the gate allowed
        before `close()` drops every line; Ctrl-C drops them at once.
        """
        with self._lock:
            timers = list(self._timers.values())
        for timer in timers:
            timer.join()

    def sensor_values(self) -> dict[str, tuple[Any, str | None]]:
        return {}

    def set_sensor(self, sensor: str, value: Any, unit: str | None = None) -> None:
        self._not_on_target("sensor.read", "LinuxHAL.set_sensor()")
