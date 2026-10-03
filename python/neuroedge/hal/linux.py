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

`digital.in` (RFC-0007 §3a) reads the board's input pins through the same character
device: each line is found by name like an output, requested as an input — never driven,
no bias or edge detection set — and held until `close()`. An agent's session requests its
lines when the HAL is built; a line first read later is requested then. A line that cannot
be found, requested or read is a failed read (`PerceptionUnavailableError`), which the gate
turns into BLOCK `criterion_unavailable`: a level is never invented.

`sensor.read` reads hwmon and IIO sysfs, each board sensor found by name
(`hal/sysfs.py`); `display` checks and records a frame exactly as `sim` does, then
hands it to the backend chosen for the machine — `memory` or `/dev/fbN`
(`hal/framebuffer.py`) — never to one guessed. Both open their files per call and
close them at once, so neither holds anything `close()` would have to release
(TSK-S5-09). `analog.in` (TSK-I2a-04) reads the same sysfs, each declared channel found
the same way — ``adc0=hwmon:ads7828/in0`` in `NEUROEDGE_LINUX_ANALOG`, or a label — converted
to the channel's unit (the kernel's millivolts to volts) and refused, as a read failure,
outside the channel's `[min, max]` (`hal/analog.py`). Where no argument is given, the choice comes from the environment
of the machine: `NEUROEDGE_LINUX_SENSORS`, `NEUROEDGE_LINUX_ANALOG` and
`NEUROEDGE_LINUX_DISPLAY`.

`i2c_read` (RFC-0007 §3b) reads the devices the board allow-lists, through `/dev/i2c-N`
(`hal/i2c_bus.py`); the node of each board bus is the machine's, `NEUROEDGE_LINUX_I2C`
(`i2c1=/dev/i2c-1`), never guessed. It carries no data-write path, and replay feeds it the
recorded readings without opening a node.

`audio.in` / `audio.out` (TSK-S5-08, Q-22) have two explicit backends, never
guessed: the **file** one a `--voice-file` session and replay use (a WAV read at
any rate in 8–96 kHz, 1 or 2 channels, downmixed and resampled to the board's
`audio_in.sample_rate_hz`; the speaker stays the `sim` timeline), and the **live**
one through `sounddevice` (PortAudio, optional extra `neuroedge[audio]`, imported
only when chosen). Live capture reads the PipeWire echo-cancel node
`neuroedge.ec.source` by default and live playback writes to `neuroedge.ec.sink` —
the two nodes `libpipewire-module-echo-cancel` creates (Q-22, `pipewire/
neuroedge-echo-cancel.conf`) — so what `audio.out` plays is the reference the AEC
subtracts. A device that is missing, that stops answering, or that refuses the
board's rate/channels is a three-part error: silence is never passed off as input.
The machine's choice comes from `NEUROEDGE_LINUX_AUDIO` (`file` | `live`);
`NEUROEDGE_LINUX_AUDIO_IN` / `NEUROEDGE_LINUX_AUDIO_OUT` name the nodes.
"""

from __future__ import annotations

import contextlib
import glob
import os
import threading
from collections import deque
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from ..errors import BoardCapabilityError, EnvelopeRefusedError, PerceptionUnavailableError
from . import Authorizer, HardwareAbstractionLayer, _require_signature
from .analog import analog_data, check_reading, unavailable
from .audio import (
    Speaker,
    WavSource,
    open_audio_file,
)
from .audio_live import (
    LiveAudioIn,
    LiveAudioOut,
    LiveSpeaker,
    _audio_node,
    _import_sounddevice,
    _interleave,
    _LiveAudio,
)
from .board import BoardProfile, load_board_by_id
from .envelope import Reservation, SafetyEnvelope
from .framebuffer import DisplayBackend, display_backend
from .i2c_bus import I2CReader, ReadFault, ScriptedI2C, open_mapped, parse_buses
from .sim import (
    EventSink,
    Frame,
    PendingCommand,
    _i2c_value,
    _NullSink,
    make_frame,
    reading_data,
)
from .supervisor import DEADLINE_MARGIN_MS, SupervisorClient
from .sysfs import Reading, SysfsSensors, parse_sources

__all__ = [
    "ANALOG_ENV",
    "AUDIO_BACKENDS",
    "AUDIO_ENV",
    "AUDIO_IN_ENV",
    "AUDIO_IN_NODE",
    "AUDIO_OUT_ENV",
    "AUDIO_OUT_NODE",
    "DISPLAY_ENV",
    "I2C_ENV",
    "LinuxHAL",
    "LiveAudioIn",
    "LiveAudioOut",
    "LiveSpeaker",
    "MISSING_ON_LINUX",
    "SENSORS_ENV",
    "TypedLinuxHAL",
    "_LiveAudio",
    "_audio_node",
    "_import_sounddevice",
    "_interleave",
]

CHIP_GLOB = "/dev/gpiochip*"
SETUP_HINT = (
    "connect the board, or create virtual lines with scripts/setup_gpio_sim.sh "
    "(gpio-sim, kernel >= 5.19)"
)
# Per-machine wiring, when the caller passes none (a session, a replay).
SENSORS_ENV = "NEUROEDGE_LINUX_SENSORS"  # temperature=hwmon:lm75/temp1;…
ANALOG_ENV = "NEUROEDGE_LINUX_ANALOG"  # adc0=hwmon:ads7828/in0;…
DISPLAY_ENV = "NEUROEDGE_LINUX_DISPLAY"  # memory | /dev/fb0
I2C_ENV = "NEUROEDGE_LINUX_I2C"  # i2c1=/dev/i2c-1;…
AUDIO_ENV = "NEUROEDGE_LINUX_AUDIO"  # file | live
AUDIO_IN_ENV = "NEUROEDGE_LINUX_AUDIO_IN"  # a PipeWire node (PortAudio name)
AUDIO_OUT_ENV = "NEUROEDGE_LINUX_AUDIO_OUT"
AUDIO_BACKENDS = ("file", "live")
SUPERVISE_ENV = (
    "NEUROEDGE_LINUX_SUPERVISE"  # "0" opts out of the supervisor process (tests, debugging)
)
# The nodes `libpipewire-module-echo-cancel` creates (Q-22, §6.1 of
# docs/spec/simulation_coverage.md): capture reads the echo-cancelled `source`,
# playback writes the reference into `sink`. Named on purpose: the default device
# is the one with echo cancellation, never a bare microphone or speaker.
AUDIO_IN_NODE = "neuroedge.ec.source"
AUDIO_OUT_NODE = "neuroedge.ec.sink"


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
        envelope: SafetyEnvelope | None = None,
        line_names: Mapping[str, str] | None = None,
        chip_glob: str | None = None,
        gpiod: Any = None,
        consumer: str = "neuroedge",
        sensor_sources: Mapping[str, str] | None = None,
        analog_sources: Mapping[str, str] | None = None,
        i2c_nodes: Mapping[str, str] | None = None,
        sysfs_root: str | Path | None = None,
        display: str | DisplayBackend | None = None,
        audio: str | None = None,
        audio_in_device: str | None = None,
        audio_out_device: str | None = None,
        sounddevice: Any = None,
        needs: Mapping[str, Any] | None = None,
        units: Mapping[str, str] | None = None,
        replay: bool = False,
        supervise: bool | None = None,
        supervisor_options: Mapping[str, Any] | None = None,
    ) -> None:
        board = board if board is not None else load_board_by_id("linux-rpi5")
        if board.target != "linux":
            raise BoardCapabilityError(
                where=f"LinuxHAL(board={board.id!r})",
                why=f"board {board.id!r} targets {board.target!r}, not 'linux'",
                how="use a linux board such as linux-rpi5, or the HAL for that target",
            )
        super().__init__(target="linux", board=board, authorize=authorize, envelope=envelope)
        self.events: EventSink = events if events is not None else _NullSink()
        self._gpiod = gpiod if gpiod is not None else _import_gpiod()
        self._timers: dict[str, threading.Timer] = {}
        # The pins whose timer is a pulse the agent asked for, as opposed to the envelope's cap
        # on an `on` that had no end: `settle()` waits for the first kind only.
        self._pulses: set[str] = set()
        self._lock = threading.Lock()
        # sensor.read and display are settled before any line is requested (Q-16):
        # `needs` = preflight()'s arguments, what the session's agent will read and draw.
        # Replay recomputes from the trace alone: a sensor it holds no reading of is
        # an error, never the room's reading today, and frames stay in memory — the
        # machine's wiring (its environment) does not enter a replay at all.
        self.replay = replay
        sources_where = "LinuxHAL(sensor_sources=...)"
        if sensor_sources is None and os.environ.get(SENSORS_ENV) and not replay:
            sensor_sources = parse_sources(os.environ[SENSORS_ENV], SENSORS_ENV)
            sources_where = SENSORS_ENV
        for sensor in sensor_sources or {}:
            # A misspelt key would leave the real sensor to label discovery, which can
            # find some other channel labelled after it.
            board.require_sensor(sensor, called_from=sources_where)
        self.sensors = SysfsSensors(sysfs_root, sensor_sources)
        # `analog.in` channels are found the same way (a source, or a label), under their
        # own names: a channel is not a sensor, and the two never share a mapping.
        analog_where = "LinuxHAL(analog_sources=...)"
        if analog_sources is None and os.environ.get(ANALOG_ENV) and not replay:
            analog_sources = parse_sources(os.environ[ANALOG_ENV], ANALOG_ENV)
            analog_where = ANALOG_ENV
        for channel in analog_sources or {}:
            board.require_analog(channel, called_from=analog_where)
        self.analog = SysfsSensors(sysfs_root, analog_sources)
        # Which /dev/i2c-N each board bus is: the machine's wiring, like the sensors'.
        # Replay never opens a node, so it ignores the environment altogether.
        i2c_where = "LinuxHAL(i2c_nodes=...)"
        if i2c_nodes is None and os.environ.get(I2C_ENV) and not replay:
            i2c_nodes = parse_buses(os.environ[I2C_ENV], I2C_ENV)
            i2c_where = I2C_ENV
        declared_buses = [bus["id"] for bus in board.i2c_buses]
        for bus in i2c_nodes or {}:
            if bus not in declared_buses:
                raise BoardCapabilityError(
                    where=i2c_where,
                    why=f"board {board.id!r} declares no I2C bus {bus!r}; it declares {declared_buses}",
                    how="name a bus of [capabilities.i2c] in the board profile",
                )
        self.i2c_nodes = dict(i2c_nodes or {})
        self._i2c_script = ScriptedI2C()
        self._i2c = I2CReader(
            board, self._open_i2c, lambda type, data: self.events.emit(type, data)
        )
        # The unit the agent declares for a sensor ([sim.sensors]); a kernel reading
        # in another unit is refused, not compared against a threshold meant for it.
        self.expected_units = dict(units or {})
        where = "LinuxHAL(display=...)" if display is not None else DISPLAY_ENV
        if replay:
            choice: Any = "memory"
        else:
            choice = display if display is not None else os.environ.get(DISPLAY_ENV) or None
        self.display_backend = display_backend(choice, where)
        self.frame: str | bytes | None = None
        self.frames: list[Frame] = []
        # The audio backend is chosen, never guessed (`file` | `live`); replay keeps to
        # the file/timeline roles, so it never opens a microphone or a speaker. The live
        # device is imported only when the live backend is chosen.
        audio_where = "LinuxHAL(audio=...)" if audio is not None else AUDIO_ENV
        if replay:
            audio_choice: Any = "file"
        else:
            audio_choice = audio if audio is not None else os.environ.get(AUDIO_ENV) or None
        if audio_choice is not None and audio_choice not in AUDIO_BACKENDS:
            raise BoardCapabilityError(
                where=audio_where,
                why=f"unknown audio backend {audio_choice!r}; the backends are {list(AUDIO_BACKENDS)}",
                how=f"set {AUDIO_ENV}=file for WAV sessions, or =live for sounddevice (Q-22)",
            )
        self.audio_backend: str | None = audio_choice
        self._sounddevice = sounddevice
        self._audio_in: LiveAudioIn | None = None
        self._audio_out: LiveAudioOut | None = None
        self._speaker: Any = None
        self.audio_in_device = _audio_node(audio_in_device, AUDIO_IN_ENV, AUDIO_IN_NODE)
        self.audio_out_device = _audio_node(audio_out_device, AUDIO_OUT_ENV, AUDIO_OUT_NODE)
        # Recorded readings replay feeds back (`script_sensor`), in place of the kernel's.
        self._scripted: dict[str, deque[Any]] = {}
        self._replayed: dict[str, Any] = {}
        self._units: dict[str, str] = {}

        chip_glob = chip_glob or CHIP_GLOB
        chips = sorted(glob.glob(chip_glob))
        if not chips:
            raise BoardCapabilityError(
                where="LinuxHAL.__init__",
                why=f"no GPIO chip found at {chip_glob}; refusing to run as a no-op (Q-16)",
                how=SETUP_HINT,
            )
        # The lines `digital.in` reads (RFC-0007 §3a): requested as inputs, by name, when the
        # session needs them or on the first read, and released by close().
        self._chips = chips
        self._line_names = dict(line_names or {})
        self._consumer = consumer
        self._inputs: dict[str, tuple[Any, int]] = {}
        self._closed = False
        # The kernel PWM channel and the HAL-owned enable lines are served by the PWM and
        # motion backends (RFC-0010, RFC-0011), not by this plain-GPIO path: no line is
        # requested for them, and digital_out() refuses a PWM pin until that backend exists.
        gpio_pins = [p for p in board.pins if p not in board.pwm_pins + board.enable_pins]
        names = {pin: (line_names or {}).get(pin, pin) for pin in gpio_pins}
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
        if needs:
            self.preflight(**needs)
        # Supervision is ON: the lines of the pins that have an envelope are held by a process
        # of its own, which drops them when the runtime freezes (RFC-0007 §3d, §9 item 9,
        # hal/supervisor.py); the runtime keeps only the pins that carry no load. The opt-out
        # is explicit — `supervise=False` or NEUROEDGE_LINUX_SUPERVISE=0, for tests and
        # debugging — and is recorded: `supervision` is "on", "off" or "failed" (a session
        # writes it to the trace metadata). Replay never supervises: it is no deployment.
        if supervise is None:
            supervise = os.environ.get(SUPERVISE_ENV) != "0" and not replay
        self.supervisor: SupervisorClient | None = None
        self.supervision = "on" if supervise else "off"
        self._supervisor_error: str | None = None
        self._supervised = frozenset(
            pin for pin in self.lines if supervise and board.envelope(pin) is not None
        )
        self._requests = self._request_outputs(consumer)
        if self._supervised:
            try:
                self.supervisor = SupervisorClient(
                    {pin: self.lines[pin] for pin in sorted(self._supervised)},
                    consumer=consumer,
                    on_drop=self._supervisor_dropped,
                    **dict(supervisor_options or {}),
                )
            except (BoardCapabilityError, OSError) as exc:
                # Never "carry on unsupervised": the pins it would have held are refused an
                # `on` (`supervisor_unavailable`) and an `off` is a no-op, nobody holds them.
                self.supervision = "failed"
                self._supervisor_error = getattr(exc, "why", None) or str(exc)
                self.events.emit("supervision_unavailable", {"reason": self._supervisor_error})
            except BaseException:
                for held in self._requests.values():
                    held.release()
                raise
        # The `digital.in` lines stay in the runtime (they are inputs: no envelope, no
        # supervisor); the supervisor holds only the output lines, so the two never request
        # the same line.
        if needs and not replay:
            try:
                for pin in dict.fromkeys(needs.get("digital_in", ())):
                    self._input_line(pin, f"{needs.get('where', '')} -> digital.in {pin!r}")
            except BaseException:
                # The session never starts: no output line may stay held, no input requested,
                # and the supervisor goes down with them.
                with contextlib.suppress(OSError):
                    self.close()
                raise

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
        for pin, (path, offset) in self.lines.items():
            if pin not in self._supervised:
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

    # -- scheduling (a voice session's hooks) -----------------------------------------
    # LinuxHAL does not schedule commands: `after_ms` is refused with a three-part
    # error (`schedules_commands` stays False, voice_fsm.md §5.5), so a pin never moves
    # on a later clock tick here. The voice driver still asks for these hooks —
    # barge-in cancels a *pending* command, and there are none — and they are honest
    # no-ops: nothing is ever delivered early.
    schedules_commands = False

    def enable_scheduling(self, clock: Any) -> None:
        self._schedule_clock = clock  # the clock a scheduled command would use; none is

    def pending_commands(self) -> list[Any]:
        return []

    def next_delivery_ms(self) -> float | None:
        return None

    def run_due(self) -> list[Any]:
        return []

    def cancel_scheduled(self, token: Any, reason: str = "") -> None:
        return None

    # -- the line itself -------------------------------------------------------------
    def _set(self, pin: str, active: bool, limit_ms: float | None = None) -> None:
        """Drive a line. `limit_ms`: with supervision, the longest the line may stay on."""
        if pin in self._supervised:
            if self.supervisor is None or not self.supervisor.alive():
                if active:
                    raise BoardCapabilityError(
                        where=f"LinuxHAL -> digital.out {pin!r}",
                        why="the supervisor of the actuator lines is not running",
                        how="restart the session; a pin is never turned on without it",
                    )
                return  # nobody holds the line, so it is down: an off has nothing to do
            self.supervisor.set(pin, active, limit_ms)
            return
        path, offset = self.lines[pin]
        value = self._gpiod.line.Value
        self._requests[path].set_value(offset, value.ACTIVE if active else value.INACTIVE)

    def line_value(self, pin: str) -> bool:
        """What the line is driven to right now (True = active)."""
        if pin in self._supervised:
            if self.supervisor is None or not self.supervisor.alive():
                return False
            return self.supervisor.get(pin)
        path, offset = self.lines[pin]
        return self._requests[path].get_value(offset) == self._gpiod.line.Value.ACTIVE

    def _supervisor_alive(self) -> bool:
        return self.supervisor is not None and self.supervisor.alive()

    def _supervisor_dropped(self, pin: str, cause: str) -> None:
        """The supervisor took a line down by itself — the runtime was late or frozen."""
        self._stop_timer(pin)
        if self.envelope is not None:
            self.envelope.ended(pin)
        self._emit(
            "actuator_command",
            {"pin": pin, "operation": "off", "duration_ms": 0, "cause": f"supervisor_{cause}"},
        )

    def _stop_timer(self, pin: str) -> None:
        with self._lock:
            timer = self._timers.pop(pin, None)
            self._pulses.discard(pin)
        if timer is not None:
            timer.cancel()

    def _end_pulse(
        self, pin: str, timer: threading.Timer | None = None, reservation: Reservation | None = None
    ) -> None:
        with self._lock:
            if timer is not None and self._timers.get(pin) is not timer:
                return  # a newer command owns the line
            self._timers.pop(pin, None)
            self._pulses.discard(pin)
            if self._closed:
                return  # close() has already dropped and released every line
            self._set(pin, False)
        # The line is down: the envelope gets the on-time back, and the trace says why it went.
        if (
            reservation is not None
            and self.envelope is not None
            and self.envelope.ended(pin, reservation) is not None
        ):
            self._auto_off(reservation)

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
        if pin in self.board.pwm_pins:
            raise BoardCapabilityError(
                where=f"{called_from} -> digital.out {pin!r}",
                why=f"{pin!r} is a PWM channel of {self.board.id!r}; LinuxHAL has no PWM backend yet",
                how="the PWM backend (RFC-0010 §3e) is not built yet; until then the channel is not driven",
            )
        if operation != "off" and pin in self._supervised and not self._supervisor_alive():
            # Before the envelope and `authorize`: nothing is reserved and no token is spent.
            refusal = EnvelopeRefusedError(
                f"{called_from} -> digital.out {pin!r}",
                "the supervisor that must hold this actuator line is "
                f"{'not running' if self.supervision == 'on' else 'unavailable'}"
                f"{f' ({self._supervisor_error})' if self._supervisor_error else ''}, "
                "so the pin is not turned on",
                "restart the session; `off` still works. Opting out is for tests and debugging: "
                "NEUROEDGE_LINUX_SUPERVISE=0",
                reason="supervisor_unavailable",
                event={"pin": pin, "operation": operation, "reason": "supervisor_unavailable"},
            )
            self._emit("envelope_refused", refusal.event)
            raise refusal
        reservation = self._admit(pin, operation, duration_ms, signature, called_from)
        envelope = self.envelope
        if operation == "off":
            # Toward the safe state. The timer that would end the pin anyway is cancelled only
            # once the line is known to be down: an off that fails must not strand the pin.
            self._set(pin, False)
            self._stop_timer(pin)
            if envelope is not None:
                envelope.ended(pin)
        else:
            self._turn_on(pin, operation, duration_ms, reservation)
        self.events.emit(
            "actuator_command", {"pin": pin, "operation": operation, "duration_ms": duration_ms}
        )
        return PendingCommand(
            pin,
            operation,
            duration_ms,
            self.events,
            on_cancel=lambda: self._abort(pin, reservation),
        )

    def _turn_on(
        self, pin: str, operation: str, duration_ms: int, reservation: Reservation | None
    ) -> None:
        envelope = self.envelope
        self._stop_timer(pin)
        limit = None if reservation is None else reservation.reserved_ms + DEADLINE_MARGIN_MS
        try:
            self._set(pin, True, limit)
        except BaseException:
            # The line did not move as asked. The command gives its on-time back only once the
            # line is known to be down; otherwise the reservation stays, the safe side of not
            # knowing.
            if reservation is not None and envelope is not None:
                try:
                    self._set(pin, False)
                except BaseException:
                    pass
                else:
                    envelope.refund(reservation)
            raise
        # A pin under an envelope always has an end: the reserved on-time. Without one only a
        # pulse does, as before.
        if reservation is not None:
            seconds: float | None = reservation.reserved_ms / 1000.0
        else:
            seconds = duration_ms / 1000.0 if operation == "pulse" else None
        if seconds is not None:
            self._arm(pin, seconds, reservation, pulse=operation == "pulse" or duration_ms > 0)

    def _arm(
        self, pin: str, seconds: float, reservation: Reservation | None, *, pulse: bool
    ) -> None:
        """Turn the pin off after `seconds`: the timer that ends a pulse or an enveloped on."""
        timer = threading.Timer(seconds, lambda: self._end_pulse(pin, timer, reservation))
        timer.daemon = True
        with self._lock:
            self._timers[pin] = timer
            if pulse:
                self._pulses.add(pin)
        try:
            timer.start()
        except BaseException:
            # No timer, no off edge: never leave a line driven without one.
            with self._lock:
                self._timers.pop(pin, None)
                self._pulses.discard(pin)
            self._set(pin, False)
            if reservation is not None and self.envelope is not None:
                self.envelope.refund(reservation)
            raise

    def _abort(self, pin: str, reservation: Reservation | None = None) -> None:
        self._stop_timer(pin)
        with self._lock:
            if self._closed:  # after close() every line is already dropped
                return
            self._set(pin, False)
        if self.envelope is not None:
            self.envelope.ended(pin, reservation)

    def close(self) -> None:
        """
        Drop every line inactive, release it, then close any live audio device. The
        session is over; nothing is recorded. One line that fails to drop must not
        leave the others active or held, so every step runs before the first error
        goes up.
        """
        # One line that fails to drop must not leave the others active or held.
        errors: list[BaseException] = []
        with self._lock:
            first = not self._closed
            self._closed = True  # a pulse ending now sees the HAL closed and leaves the lines alone
            inputs, self._inputs = self._inputs, {}
        for request, _offset in inputs.values():
            try:
                request.release()
            except OSError as exc:
                errors.append(exc)
        if first:
            for pin in list(self._timers):
                self._stop_timer(pin)
            for pin in self.lines:
                try:
                    self._set(pin, False)
                except OSError as exc:
                    errors.append(exc)  # the line may still be on: its reservation stays held
                else:
                    if self.envelope is not None:
                        self.envelope.ended(pin)
            with self._lock:
                requests, self._requests = self._requests, {}
            for request in requests.values():
                try:
                    request.release()
                except OSError as exc:
                    errors.append(exc)
            if self.supervisor is not None:
                try:
                    self.supervisor.close()
                except BaseException as exc:
                    errors.append(exc)
        for device in (self._audio_in, self._audio_out):
            if device is None:
                continue
            try:
                device.close()
            except BaseException as exc:  # a dead speaker/printer must still raise
                errors.append(exc)
        try:
            self._i2c.close()
        except OSError as exc:
            errors.append(exc)
        if errors:
            raise errors[0]

    # -- digital.in ------------------------------------------------------------------
    def _input_line(self, pin: str, where: str) -> tuple[Any, int]:
        """The held request of an input line, requested now if nothing has read it yet."""
        with self._lock:
            if self._closed:
                raise BoardCapabilityError(
                    where=where,
                    why="the HAL is closed and holds no input line any more",
                    how="build a new HAL to read inputs",
                )
            held = self._inputs.get(pin)
            if held is not None:
                return held
            name = self._line_names.get(pin, pin)
            location = self._find(self._chips, name)
            if location is None:
                raise BoardCapabilityError(
                    where=where,
                    why=f"no line named {name!r} on {self._chips} for input pin {pin!r} of {self.board.id!r}",
                    how=f"name the line after the pin (setup_gpio_sim.sh does), or pass line_names; {SETUP_HINT}",
                )
            path, offset = location
            settings = self._gpiod.LineSettings(direction=self._gpiod.line.Direction.INPUT)
            try:
                request = self._gpiod.request_lines(
                    path, consumer=self._consumer, config={(offset,): settings}
                )
            except OSError as exc:
                raise _chip_error(path, exc) from exc
            self._inputs[pin] = (request, offset)
            return request, offset

    def _read_level(self, pin: str, where: str) -> bool:
        if self.replay:
            # A replay never reads the machine, not even to see what its lines say today.
            raise PerceptionUnavailableError(
                where=where,
                why="the trace being replayed holds no reading of this line",
                how="replay a trace recorded with its digital_in events",
            )
        try:
            request, offset = self._input_line(pin, where)
            value = request.get_value(offset)
        except (OSError, BoardCapabilityError, ValueError, RuntimeError) as exc:
            reason = exc.why if isinstance(exc, BoardCapabilityError) else str(exc)
            raise PerceptionUnavailableError(
                where=where,
                why=f"the line cannot be read: {reason}",
                how="check the wiring and that no other process holds the line; the criterion stays undecided",
            ) from exc
        return value == self._gpiod.line.Value.ACTIVE

    # -- sensor.read -----------------------------------------------------------------
    def sensor_read(
        self, sensor: str, called_from: str = "<unknown>", use: str | None = None
    ) -> Any:
        """
        One fresh reading from the kernel, recorded as `sensor_read` with the same data
        as `sim` (`use="fact"`: read to compute a gate fact). Replay's scripted readings
        take the kernel's place, as they take `set_sensor`'s on `sim`.
        """
        self.board.require_sensor(sensor, called_from=called_from)
        where = f"{called_from} -> sensor.read {sensor!r}"
        if sensor in self._scripted:
            queue = self._scripted[sensor]
            if queue and use is None:
                self._replayed[sensor] = queue.popleft()
            if sensor not in self._replayed:
                raise BoardCapabilityError(
                    where=where,
                    why="the trace being replayed holds no reading of this sensor yet",
                    how="replay a trace recorded with its sensor_read events",
                )
            value, unit = self._replayed[sensor], self._units.get(sensor)
        elif self.replay:
            raise BoardCapabilityError(
                where=where,
                why="the trace being replayed holds no reading of this sensor",
                how="replay a trace recorded with its sensor_read events",
            )
        else:
            reading = self._kernel_read(sensor, where)
            value, unit = reading.value, reading.unit
        self.events.emit("sensor_read", reading_data(sensor, value, unit, use))
        return value

    def _kernel_read(self, sensor: str, where: str) -> Reading:
        reading = self.sensors.read(sensor, where)
        expected = self.expected_units.get(sensor)
        if expected is not None and reading.unit != expected:
            raise BoardCapabilityError(
                where=where,
                why=(
                    f"the kernel reports {sensor!r} in {reading.unit!r} ({reading.path}), "
                    f"and the agent declares {expected!r}"
                ),
                how="map the sensor to the channel that measures it, or fix the declared unit",
            )
        return reading

    # -- analog.in -------------------------------------------------------------------
    def analog_in(
        self, channel: str, called_from: str = "<unknown>", use: str | None = None
    ) -> float:
        """
        One fresh reading of `channel` from the kernel, in the channel's declared unit,
        recorded as `analog_in` (`use="fact"`: read to compute a gate fact). Any failure to
        read it — no device, a file that is gone or holds garbage, another unit, a value
        outside `[min, max]` — is `PerceptionUnavailableError` (NE5001), recorded as a failed
        read: the gate then blocks `criterion_unavailable`, it never gets a clamped value.
        A replay never reads the machine (the recorded facts are fed back instead).
        """
        declared = self.board.require_analog(channel, called_from=called_from)
        where = f"{called_from} -> analog.in {channel!r}"
        try:
            if self.replay:
                raise unavailable(
                    where,
                    "a replay does not read the machine; the trace holds the recorded facts",
                    "replay a trace recorded with its gate_facts events",
                )
            value = check_reading(declared, *self._kernel_analog(channel, where), where)
        except PerceptionUnavailableError as error:
            self.events.emit("analog_in", analog_data(channel, use=use, error=error.why))
            raise
        self.events.emit("analog_in", analog_data(channel, value, declared["unit"], use))
        return value

    def _kernel_analog(self, channel: str, where: str) -> tuple[float, str]:
        """The kernel's value and unit for `channel`; every way it can fail is NE5001."""
        try:
            reading = self.analog.read(channel, where)
        except BoardCapabilityError as error:  # no source, no device, unreadable, not a number
            raise unavailable(error.where, error.why, error.how) from error
        except OSError as error:  # sysfs went away under the lookup itself
            raise unavailable(
                where,
                f"cannot read the kernel: {error.strerror or error}",
                "check the ADC is bound and the user may read sysfs",
            ) from error
        return reading.value, reading.unit

    def script_sensor(self, sensor: str, values: list[Any], unit: str | None = None) -> None:
        """Readings returned in order, one per read, instead of the kernel's — replay only."""
        self.board.require_sensor(sensor, called_from="LinuxHAL.script_sensor()")
        self._scripted[sensor] = deque(values)
        if unit is not None:
            self._units[sensor] = unit

    # -- i2c -------------------------------------------------------------------------
    def _open_i2c(self, bus: str, where: str) -> Any:
        # Replay, and a bus a test scripted, read the script: no node is opened for them.
        if self.replay or self._i2c_script.has_bus(bus):
            return self._i2c_script.transport(bus)
        return open_mapped(self.i2c_nodes, self.board, bus, where)

    def i2c_read(
        self,
        bus: str,
        device: str | int,
        register: int | None = None,
        *,
        width: int = 1,
        called_from: str = "<unknown>",
    ) -> int:
        """
        One read of an allow-listed device, recorded as `i2c_read` as on `sim`. The board
        decides first — an undeclared bus, device or register is refused before a node is
        chosen or a transaction sent. A NACK or timeout is tried once more, then NE5001.
        """
        return self._i2c.read(bus, device, register, width=width, called_from=called_from)

    def i2c_scan(self, bus: str, called_from: str = "<unknown>") -> list[Any]:
        if self.replay:
            raise BoardCapabilityError(
                where=f"{called_from} -> i2c.scan {bus!r}",
                why="a replay never touches a bus, and a scan has nothing recorded to replay",
                how="scan on a live linux HAL",
            )
        return self._i2c.scan(bus, called_from=called_from)

    def script_i2c(
        self,
        bus: str,
        device: str | int,
        register: int | None,
        values: list[int | ReadFault],
        *,
        width: int = 1,
    ) -> None:
        """Readings returned in order, one per read, instead of the bus's — replay only."""
        where = "LinuxHAL.script_i2c()"
        declared = self._i2c.resolve(bus, device, register, width, where)
        checked = [v if isinstance(v, ReadFault) else _i2c_value(v, width, where) for v in values]
        self._i2c_script.script(bus, declared["address"], register, checked)

    # -- audio -----------------------------------------------------------------------
    def _audio_capability(self, primitive: str, called_from: str) -> dict[str, Any]:
        """The board's declaration for `audio.in` / `audio.out`, or a three-part refusal."""
        if not self.board.supports(primitive):
            raise BoardCapabilityError(
                where=f"{called_from} -> {primitive}",
                why=f"board {self.board.id!r} does not declare the {primitive!r} primitive",
                how=f"add it to {self.board.source}, or choose a board that provides it",
            )
        return self.board.capability(primitive)

    def _audio_rate(self, primitive: str, called_from: str) -> int:
        rate = self._audio_capability(primitive, called_from).get("sample_rate_hz")
        if isinstance(rate, bool) or not isinstance(rate, int) or rate <= 0:
            raise BoardCapabilityError(
                where=f"{called_from} -> {primitive}",
                why=f"board {self.board.id!r} declares {primitive} without a sample_rate_hz, and "
                "PCM audio needs one",
                how=f"add sample_rate_hz = 48000 to {primitive} in {self.board.source}",
            )
        return rate

    def audio_file(self, path: Any, called_from: str = "<unknown>") -> WavSource:
        """
        A WAV file as `audio.in`, whatever rate (8–96 kHz) and 1–2 channels it has:
        the file backend a `--voice-file` session uses, converted to the board's rate
        as a capture device would be. It never touches a microphone.
        """
        capability = self._audio_capability("audio.in", called_from)
        rate = self._audio_rate("audio.in", called_from)
        return open_audio_file(
            path,
            sample_rate_hz=rate,
            called_from=called_from,
            max_channels=int(capability.get("channels") or 2),
        )

    def _device(self) -> Any:
        if self._sounddevice is None:
            self._sounddevice = _import_sounddevice()
        return self._sounddevice

    def audio_source(self, called_from: str = "<unknown>") -> LiveAudioIn:
        """The live capture node (`neuroedge.ec.source` by default); live backend only."""
        if self.audio_backend != "live":
            raise BoardCapabilityError(
                where=f"{called_from} -> audio.in",
                why="no live audio backend is chosen for this machine; refusing to guess one",
                how=(
                    f"set {AUDIO_ENV}=live on the device (PipeWire echo-cancel nodes, Q-22) or "
                    "pass LinuxHAL(audio='live'); a WAV session uses --voice-file"
                ),
            )
        capability = self._audio_capability("audio.in", called_from)
        if self._audio_in is None:
            self._audio_in = LiveAudioIn(
                self._device(),
                sample_rate_hz=self._audio_rate("audio.in", called_from),
                channels=int(capability.get("channels") or 1),
                device=self.audio_in_device,
                events=self.events,
            )
        # Opened eagerly: a session that prelights its audio before asking for lines
        # (preflight, Q-16) fails on a missing microphone before a pin is held.
        self._audio_in.open()
        return self._audio_in

    def audio_sink(self, called_from: str = "<unknown>") -> LiveAudioOut:
        """The live playback node (`neuroedge.ec.sink` by default); live backend only."""
        if self.audio_backend != "live":
            raise BoardCapabilityError(
                where=f"{called_from} -> audio.out",
                why="no live audio backend is chosen for this machine; refusing to guess one",
                how=(
                    f"set {AUDIO_ENV}=live on the device (PipeWire echo-cancel nodes, Q-22) or "
                    "pass LinuxHAL(audio='live'); --voice-out writes a WAV instead"
                ),
            )
        capability = self._audio_capability("audio.out", called_from)
        if self._audio_out is None:
            self._audio_out = LiveAudioOut(
                self._device(),
                sample_rate_hz=self._audio_rate("audio.out", called_from),
                channels=int(capability.get("channels") or 1),
                device=self.audio_out_device,
            )
        # Opened eagerly: a session that prelights its audio before asking for lines
        # (preflight, Q-16) fails on a missing speaker before a pin is held.
        self._audio_out.open()
        return self._audio_out

    def speaker(self, called_from: str = "<unknown>") -> Any:
        """
        `audio.out` as a timeline at the board's rate — what `--voice-out` writes and
        what `VoiceSession` plays a reply on. With the live backend the same `play()`
        also writes to the device; with the file backend the timeline is all there is.
        """
        rate = self._audio_rate("audio.out", called_from)
        if self._speaker is None:
            self._speaker = (
                LiveSpeaker(self.audio_sink(called_from), rate)
                if self.audio_backend == "live"
                else Speaker(rate)
            )
        return self._speaker

    # -- display ---------------------------------------------------------------------
    def display(
        self,
        frame: str | bytes,
        *,
        width: int | None = None,
        height: int | None = None,
        format: str | None = None,
        called_from: str = "<unknown>",
    ) -> Frame:
        """Check the frame as `sim` does, show it on the chosen backend, then record it."""
        shown = make_frame(self.board, frame, width, height, format, called_from)
        self._require_display_backend(f"{called_from} -> display").show(
            shown, f"{called_from} -> display"
        )
        self.frame = frame
        self.frames.append(shown)
        self.events.emit("display_frame", shown.event_data())
        return shown

    def _require_display_backend(self, where: str) -> DisplayBackend:
        if self.display_backend is None:
            raise BoardCapabilityError(
                where=where,
                why="no display backend was chosen for this machine; refusing to guess one",
                how=(
                    f"set {DISPLAY_ENV}=/dev/fb0 on a Pi with a panel, or {DISPLAY_ENV}=memory "
                    "(CI, headless); or pass LinuxHAL(display=...)"
                ),
            )
        return self.display_backend

    def preflight(
        self,
        sensors: Iterable[str] = (),
        display: bool = False,
        audio: Iterable[str] = (),
        i2c: Iterable[str] = (),
        where: str = "",
        analog: Iterable[str] = (),
        digital_in: Iterable[str] = (),
    ) -> None:
        """
        Fail now, not mid-session, if a sensor the agent reads cannot be read, it
        draws with no display backend chosen, or (with the live backend) the
        microphone/speaker it needs cannot be opened. The reading taken here is not
        recorded. `preflight` runs before `__init__` requests any GPIO line, so a
        missing live device is refused before a pin is held (Q-16).

        `audio` names the primitives the session will use; the file backend needs no
        device, so nothing is opened unless the machine chose `live` (Q-22).

        `analog` names the `analog.in` channels the session reads for gate facts: each must
        read now (not recorded), so an ADC that is not there is refused at load as a board
        problem, not found on the first turn that needs it (TSK-I2a-04). `i2c` names the
        buses the agent reads: each must be declared, have a device node chosen and open —
        no transaction is sent.
        """
        for sensor in dict.fromkeys(sensors):
            self.board.require_sensor(sensor, called_from=where)
            if not self.replay:  # a replay never reads the machine, not even to check it
                self._kernel_read(sensor, f"{where} -> sensor.read {sensor!r}")
        for channel in dict.fromkeys(analog):
            declared = self.board.require_analog(channel, called_from=where)
            if not self.replay:
                channel_where = f"{where} -> analog.in {channel!r}"
                try:
                    check_reading(
                        declared, *self._kernel_analog(channel, channel_where), channel_where
                    )
                except PerceptionUnavailableError as error:
                    raise BoardCapabilityError(error.where, error.why, error.how) from error
        for bus in dict.fromkeys(i2c):  # a declared bus with a node chosen; a replay's is scripted
            self._i2c.check_bus(bus, f"{where} -> i2c {bus!r}")
        for pin in dict.fromkeys(digital_in):
            # Found now, requested once the output lines are held: a missing input line is
            # refused before any pin is (RFC-0007 §3a, Q-16).
            self.board.require_input_pin(pin, called_from=where)
            name = self._line_names.get(pin, pin)
            if not self.replay and self._find(self._chips, name) is None:
                raise BoardCapabilityError(
                    where=f"{where} -> digital.in {pin!r}",
                    why=f"no line named {name!r} on {self._chips} for input pin {pin!r} of {self.board.id!r}",
                    how=f"name the line after the pin (setup_gpio_sim.sh does), or pass line_names; {SETUP_HINT}",
                )
        if display:
            self._require_display_backend(f"{where} -> display")
        if self.audio_backend == "live":
            for primitive in dict.fromkeys(audio):
                if primitive == "audio.in":
                    self.audio_source(f"{where} -> preflight")
                elif primitive == "audio.out":
                    self.audio_sink(f"{where} -> preflight")


# Primitives `LinuxHAL` does not implement yet, and the task that brings each. An
# interactive session refuses an agent that needs one before any line is requested,
# rather than failing mid-session on the first turn that reaches it (Q-16). Empty
# since TSK-S5-08: all five primitives run on `linux`.
MISSING_ON_LINUX: dict[str, str] = {}


class TypedLinuxHAL(LinuxHAL):
    """
    `LinuxHAL` for an interactive session — `run`, `record`, `mcp serve` (TSK-S5-10).

    The pins are real kernel lines. The person types on the terminal, as on `sim`
    (Q-15): a typed line is the session's input and a reply is printed, with the
    same `text_input` / `tts_stream_start` events `SimHAL` writes, so a session
    recorded here has the shape of a `sim` one and replays on either target. The
    person hears nothing and speaks nothing: an agent that needs `audio.in` /
    `audio.out` in a *voice* session gets its frames from `audio_file` (file
    backend) or the live nodes (TSK-S5-08); this class only substitutes the typed
    line for a microphone, exactly as `SimHAL` does on `sim`.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._typed: deque[str] = deque()
        self.spoken: list[str] = []

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
            return sorted(self._pulses)

    def driven(self) -> list[str]:
        """The pins whose line is active right now."""
        return [pin for pin in self.lines if not self._closed and self.line_value(pin)]

    def settle(self) -> None:
        """
        Wait for every pulse in flight to end on its own. `run -c` does, so the one
        command it ran drives its line for the whole duration the gate allowed
        before `close()` drops every line; Ctrl-C drops them at once.
        """
        with self._lock:
            timers = [self._timers[pin] for pin in self._pulses if pin in self._timers]
        for timer in timers:
            timer.join()

    def sensor_values(self) -> dict[str, tuple[Any, str | None]]:
        return {}  # `:sensors` lists values set on sim; on linux the kernel owns them

    def digital_in_values(self) -> dict[str, bool | None]:
        return {}  # on linux the kernel owns the lines; `:inputs` lists levels set on sim

    def set_digital_in(self, pin: str, level: bool) -> None:
        raise BoardCapabilityError(
            where=f"LinuxHAL.set_digital_in({pin!r})",
            why="on linux an input line is read from the kernel (gpiod); a level cannot be set",
            how="change what drives the line, or set the level on sim (--target sim)",
        )

    def set_sensor(self, sensor: str, value: Any, unit: str | None = None) -> None:
        raise BoardCapabilityError(
            where=f"LinuxHAL.set_sensor({sensor!r})",
            why="on linux a sensor is read from the kernel (hwmon, IIO); a reading cannot be set",
            how="change what the sensor measures, or set the value on sim (--target sim)",
        )

    def analog_values(self) -> dict[str, tuple[Any, str]]:
        return {}  # `:analogs` lists values set on sim; on linux the kernel owns them

    def set_analog(self, channel: str, value: Any) -> None:
        raise BoardCapabilityError(
            where=f"LinuxHAL.set_analog({channel!r})",
            why="on linux an analog.in channel is read from the kernel (hwmon, IIO); a reading cannot be set",
            how="change what the channel measures, or set the value on sim (--target sim)",
        )
