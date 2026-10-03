"""
Hardware Abstraction Layer (HAL) — L1.

Five immutable primitives (FR-HAL-01): `audio.in`, `audio.out`, `digital.out`,
`sensor.read`, `display`. The set is closed on purpose; see
docs/spec/hal_mcu_review.md for what that buys on the microcontroller. Extension primitives
(RFC-0013) are optional per board: `digital.in` (RFC-0007 §3a) is read with `digital_in()`.
"""

import time
from collections import deque
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any, NamedTuple

from ..errors import ActionContractViolation, BoardCapabilityError, PerceptionUnavailableError
from .board import (
    ALL_PRIMITIVES,
    EXTENSION_PRIMITIVES,
    PRIMITIVES,
    REQUIRABLE_PRIMITIVES,
    SUPPORTED_TARGETS,
    BoardProfile,
    available_boards,
    load_board,
    load_board_by_id,
)

if TYPE_CHECKING:
    from .audio import WavSource
    from .audio_live import LiveAudioIn, LiveAudioOut

__all__ = [
    "ALL_PRIMITIVES",
    "EXTENSION_PRIMITIVES",
    "PRIMITIVES",
    "REQUIRABLE_PRIMITIVES",
    "SUPPORTED_TARGETS",
    "BoardProfile",
    "DigitalReading",
    "HardwareAbstractionLayer",
    "PinAssertion",
    "available_boards",
    "load_board",
    "load_board_by_id",
]


class PinAssertion:
    """
    Observed state of one digital output, as asserted by Action CI (FR-CI-03).

    `never_pulsed()` is the assertion that matters most: the compliance suite
    proves a blocked action left the physical pin untouched, not merely that a
    verdict object said BLOCK.
    """

    def __init__(
        self,
        pin_name: str,
        pulsed: bool = False,
        duration_ms: int = 0,
        commands: list[tuple[str, int]] | None = None,
    ):
        self.pin_name = pin_name
        # Every accepted command, in order. The history — not the last write —
        # is what the assertions read, so an `on()` or an `off()` after a pulse
        # can never make a touched pin look untouched.
        self.commands: list[tuple[str, int]] = (
            list(commands) if commands is not None else ([("pulse", duration_ms)] if pulsed else [])
        )

    def record(self, operation: str, duration_ms: int) -> None:
        self.commands.append((operation, duration_ms))

    @property
    def pulses(self) -> list[int]:
        return [duration for operation, duration in self.commands if operation == "pulse"]

    @property
    def pulsed(self) -> bool:
        return bool(self.pulses)

    @property
    def duration_ms(self) -> int:
        return self.pulses[-1] if self.pulses else 0

    def never_pulsed(self) -> bool:
        """True only if the pin never accepted *any* command."""
        return not self.commands

    def pulsed_once(self, duration_ms: int = 0) -> bool:
        if len(self.commands) != 1 or not self.pulsed:
            return False
        return duration_ms <= 0 or self.pulses[0] == duration_ms

    def __repr__(self) -> str:  # pragma: no cover - diagnostic aid
        state = f"pulse {self.duration_ms}ms" if self.pulsed else "idle"
        return f"<PinAssertion {self.pin_name} {state}>"


class DigitalReading(NamedTuple):
    """
    One `digital.in` level and the instant the HAL read it (RFC-0007 §3a).

    `read_ms` is on the clock of the HAL's event log — the clock the gate ages a reading by —
    and is taken before the line is read, so a reading is never younger than it looks.
    """

    value: bool
    read_ms: float


def _monotonic_ms() -> float:
    return time.monotonic() * 1000.0


Authorizer = Callable[[Any, str, str], None]


def _require_signature(signature: Any, pin: str, called_from: str) -> None:
    """
    Default check: refuse everything. Only a token ledger — installed by `c.do()`'s
    `Conversation` — can authorise a pin, so a HAL that nobody wired up cannot be
    driven by any string that merely looks like proof (A3).
    """
    if not signature:
        why = (
            "actuator command carries no gate signature; every digital.out "
            "must prove which gate authorised it (Proposal Appendix A.2)"
        )
    else:
        why = "no verdict-token ledger is installed on this HAL, so no proof can be checked"
    raise ActionContractViolation(
        where=f"{called_from} -> digital.out {pin!r}",
        why=why,
        how=(
            "route the command through an @action function run by c.do(), which "
            "installs the ledger and attaches a single-use verdict token"
        ),
    )


class HardwareAbstractionLayer:
    """
    Standard interface across `sim`, `linux` and `esp32s3`.

    `digital_out` is the only way a pin changes state, and it always asks
    `authorize` first. The default refuses every command; `Conversation`
    (TSK-S2-05) installs the single-use verdict-token check.
    """

    def __init__(
        self,
        target: str = "sim",
        board: BoardProfile | None = None,
        *,
        authorize: Authorizer = _require_signature,
    ):
        self.target = target
        self.board = board
        self.authorize = authorize
        self.pins: dict[str, PinAssertion] = {}
        self._replayed_levels: dict[str, deque[bool | None]] = {}

    def digital_out(
        self,
        pin: str,
        operation: str,
        duration_ms: int = 0,
        signature: Any = "",
        called_from: str = "<unknown>",
    ) -> None:
        """
        Drive a digital output.

        Appendix A.2 makes the gate signature non-optional: there is no code
        path from agent logic to a physical pin that does not carry proof of an
        authorising gate. An unsigned command is a contract violation, not a
        permission error to be retried. The pin is checked before the proof is
        spent, so a typo never consumes a verdict token.
        """
        if self.board is not None:
            self.board.require_pin(pin, called_from=called_from)
        self.authorize(signature, pin, called_from)
        self.pins.setdefault(pin, PinAssertion(pin)).record(operation, duration_ms)

    # -- digital.in (RFC-0007 §3a) -------------------------------------------------------
    # `SimHAL` and `LinuxHAL` set the event sink; the clock of an `EventLog` is the clock the
    # gate ages a reading by, so a HAL with another sink still marks reads on its own clock.
    events: Any = None

    def _clock_ms(self) -> float:
        clock = getattr(self.events, "clock", None)
        return clock() if callable(clock) else _monotonic_ms()

    def digital_in(self, pin: str, called_from: str = "<unknown>", use: str | None = None) -> bool:
        """
        The logic level of an input line: True is the line high. Reading moves nothing, so it
        needs no token (as `sensor.read`), and every read is a `digital_in` event. A read that
        fails raises `PerceptionUnavailableError` (NE5001), never a level. `use="fact"` marks a
        read made to compute a gate fact rather than by an action.
        """
        return self.digital_reading(pin, called_from, use).value

    def digital_reading(
        self, pin: str, called_from: str = "<unknown>", use: str | None = None
    ) -> DigitalReading:
        """`digital_in()` with the read mark the gate ages the level by."""
        if self.board is not None:
            self.board.require_input_pin(pin, called_from=called_from)
        where = f"{called_from} -> digital.in {pin!r}"
        read_ms = self._clock_ms()
        try:
            queue = self._replayed_levels.get(pin)
            if queue is not None:
                level = self._next_replayed_level(pin, queue, where)
            else:
                level = self._read_level(pin, where)
            if not isinstance(level, bool):
                raise PerceptionUnavailableError(
                    where=where,
                    why=f"the line gave {level!r}, not a logic level",
                    how="check the wiring of the input, or the backend that reads it",
                )
        except PerceptionUnavailableError as error:
            self._emit_digital_in({"pin": pin, "reason": error.why}, use)
            raise
        self._emit_digital_in({"pin": pin, "value": level}, use)
        return DigitalReading(level, read_ms)

    def _emit_digital_in(self, data: dict[str, Any], use: str | None) -> None:
        if use is not None:
            data["use"] = use
        if self.events is not None:
            self.events.emit("digital_in", data)

    def _read_level(self, pin: str, where: str) -> bool:
        """The target's own read of a declared input line; a read that fails raises NE5001."""
        raise BoardCapabilityError(
            where=where,
            why=f"digital.in is not implemented on target {self.target!r} yet",
            how="see docs/spec/simulation_coverage.md for the task that adds it; `sim` and `linux` have it",
        )

    def script_digital_in(self, pin: str, values: Iterable[bool | None]) -> None:
        """
        Levels returned in order, one per read, instead of the line's own — how replay feeds a
        recorded session back; a None is a read that failed when it was recorded. Reading past
        the last one is a failed read, never the last level again.
        """
        if self.board is not None:
            self.board.require_input_pin(
                pin, called_from=f"{type(self).__name__}.script_digital_in()"
            )
        self._replayed_levels[pin] = deque(values)

    @staticmethod
    def _next_replayed_level(pin: str, queue: deque[bool | None], where: str) -> bool:
        level = queue.popleft() if queue else None
        if level is None:
            raise PerceptionUnavailableError(
                where=where,
                why="the trace being replayed holds no reading of this line here (it had failed, or ended)",
                how="replay a trace recorded with its digital_in events",
            )
        return level

    def _not_on_target(self, primitive: str, called_from: str) -> None:
        raise BoardCapabilityError(
            where=f"{called_from} -> {primitive}",
            why=f"{primitive} is not implemented on target {self.target!r} yet",
            how="see docs/spec/simulation_coverage.md for the task that adds it; `sim` has it",
        )

    def sensor_read(self, sensor: str, called_from: str = "<unknown>") -> Any:
        self._not_on_target("sensor.read", called_from)

    def analog_in(
        self, channel: str, called_from: str = "<unknown>", use: str | None = None
    ) -> float:
        """One reading of an `analog.in` channel, in the unit the board declares (RFC-0007 §3c)."""
        self._not_on_target("analog.in", called_from)

    def display(self, frame: Any, *, called_from: str = "<unknown>", **_: Any) -> Any:
        self._not_on_target("display", called_from)

    # -- i2c (RFC-0007 §3b): read-only; there is no method that writes data ----------
    def i2c_read(
        self,
        bus: str,
        device: str | int,
        register: int | None = None,
        *,
        width: int = 1,
        called_from: str = "<unknown>",
    ) -> int:
        """A receive byte, or a declared register (`width` 1 or 2 bytes), of an allow-listed device."""
        self._not_on_target("i2c", called_from)

    def i2c_scan(self, bus: str, called_from: str = "<unknown>") -> list[Any]:
        """The addresses that answer a read-byte probe, tagged with their allow-list name or None."""
        self._not_on_target("i2c", called_from)

    # -- audio: the signatures `SimHAL` and `LinuxHAL` implement -------------------
    def audio_in(self, called_from: str = "<unknown>") -> str | None:
        """One typed utterance, or None when nothing is queued (the text input of `sim`)."""
        self._not_on_target("audio.in", called_from)

    def audio_out(self, text: str, called_from: str = "<unknown>") -> None:
        """Say `text` (the text output of `sim`)."""
        self._not_on_target("audio.out", called_from)

    def audio_file(self, path: Any, called_from: str = "<unknown>") -> "WavSource":
        """A WAV file as `audio.in`: PCM frames from a file, never a microphone."""
        self._not_on_target("audio.in", called_from)

    def audio_source(self, called_from: str = "<unknown>") -> "LiveAudioIn":
        """The live capture device as `audio.in`."""
        self._not_on_target("audio.in", called_from)

    def audio_sink(self, called_from: str = "<unknown>") -> "LiveAudioOut":
        """The live playback device as `audio.out`."""
        self._not_on_target("audio.out", called_from)

    def speaker(self, called_from: str = "<unknown>") -> Any:
        """`audio.out` as a timeline at the board's rate (`play`, `stop`, `render`, `write`)."""
        self._not_on_target("audio.out", called_from)

    def pin(self, name: str) -> PinAssertion:
        """
        Observed state of a pin. A name the board does not declare raises, so a
        misspelled assertion can never pass as "never pulsed" (CEO-S5-2).
        """
        if self.board is not None:
            self.board.require_pin(name, called_from="hal.pin()")
        return self.pins.get(name, PinAssertion(name, pulsed=False))
