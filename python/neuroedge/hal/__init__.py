"""
Hardware Abstraction Layer (HAL) — L1.

Five immutable primitives (FR-HAL-01): `audio.in`, `audio.out`, `digital.out`,
`sensor.read`, `display`. The set is closed on purpose; see
docs/spec/hal_mcu_review.md for what that buys on the microcontroller.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ..errors import ActionContractViolation, BoardCapabilityError, EnvelopeRefusedError
from .board import (
    ALL_PRIMITIVES,
    EXTENSION_PRIMITIVES,
    PRIMITIVES,
    SUPPORTED_TARGETS,
    BoardProfile,
    available_boards,
    load_board,
    load_board_by_id,
)
from .envelope import Reservation, SafetyEnvelope

if TYPE_CHECKING:
    from .audio import WavSource
    from .audio_live import LiveAudioIn, LiveAudioOut

__all__ = [
    "ALL_PRIMITIVES",
    "EXTENSION_PRIMITIVES",
    "PRIMITIVES",
    "SUPPORTED_TARGETS",
    "BoardProfile",
    "HardwareAbstractionLayer",
    "PinAssertion",
    "available_boards",
    "ensure_envelope",
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

    `digital_out` is the only way a pin changes state. It asks the safety envelope first and
    `authorize` second; both are installed from outside. The default `authorize` refuses
    every command; `Conversation` (TSK-S2-05) installs the single-use verdict-token check and,
    for a board that declares envelopes, the envelope (RFC-0007 §3d, TSK-N2-01).
    """

    def __init__(
        self,
        target: str = "sim",
        board: BoardProfile | None = None,
        *,
        authorize: Authorizer = _require_signature,
        envelope: SafetyEnvelope | None = None,
    ):
        self.target = target
        self.board = board
        self.authorize = authorize
        self.pins: dict[str, PinAssertion] = {}
        self._envelope: SafetyEnvelope | None = None
        self.envelope = envelope

    @property
    def envelope(self) -> SafetyEnvelope | None:
        """
        The per-pin safety envelope, or None when none is installed: then `digital_out` is
        what it was before the envelope existed (a pin the board does not bound moves as it
        always did).
        """
        return self._envelope

    @envelope.setter
    def envelope(self, envelope: SafetyEnvelope | None) -> None:
        self._envelope = envelope
        if envelope is not None:
            envelope.on_auto_off = self._auto_off

    def _emit(self, type: str, data: dict[str, Any]) -> None:
        events = getattr(self, "events", None)
        if events is not None:
            events.emit(type, data)

    def _auto_off(self, reservation: Reservation) -> None:
        """The HAL turned a pin off itself (a command toward the safe state, never refused)."""
        if reservation.auto_off_cause is not None:
            self._emit(
                "actuator_command",
                {
                    "pin": reservation.name,
                    "operation": "off",
                    "duration_ms": 0,
                    "cause": reservation.auto_off_cause,
                },
            )

    def _admit(
        self,
        pin: str,
        operation: str,
        duration_ms: int,
        signature: Any,
        called_from: str,
        *,
        after_ms: float = 0,
        record: bool = True,
    ) -> Reservation | None:
        """
        What every target does before it moves a pin: `require_pin`, then the envelope, then
        `authorize`, then `record`. The envelope stands before `authorize`, so a refused
        command spends no token; and a command `authorize` refuses gives back every
        millisecond it reserved. The command toward the safe state (`off`) is none of the
        envelope's business and needs no proof (RFC-0007 §3d): it only has to name a real pin.
        Returns the reservation the caller must `ended()` or `refund()` once the pin has moved
        (or not), or None.
        """
        if self.board is not None:
            self.board.require_pin(pin, called_from=called_from)
        reservation = None
        if operation != "off":
            envelope = self._envelope
            if envelope is not None:
                try:
                    reservation = envelope.reserve(
                        pin,
                        duration_ms,
                        operation=operation,
                        after_ms=after_ms,
                        called_from=called_from,
                    )
                except EnvelopeRefusedError as refusal:
                    self._emit("envelope_refused", refusal.event)
                    raise
            try:
                self.authorize(signature, pin, called_from)
            except BaseException:
                if reservation is not None and envelope is not None:
                    envelope.refund(reservation)
                raise
        if record:
            self.pins.setdefault(pin, PinAssertion(pin)).record(operation, duration_ms)
        return reservation

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
        spent, so a typo never consumes a verdict token. The one exception is the
        command toward the safe state, `off`, which is never blocked (RFC-0007 §3d).
        """
        self._admit(pin, operation, duration_ms, signature, called_from)
        if operation == "off" and self._envelope is not None:
            self._envelope.ended(pin)

    def _not_on_target(self, primitive: str, called_from: str) -> None:
        raise BoardCapabilityError(
            where=f"{called_from} -> {primitive}",
            why=f"{primitive} is not implemented on target {self.target!r} yet",
            how="see docs/spec/simulation_coverage.md for the task that adds it; `sim` has it",
        )

    def sensor_read(self, sensor: str, called_from: str = "<unknown>") -> Any:
        self._not_on_target("sensor.read", called_from)

    def display(self, frame: Any, *, called_from: str = "<unknown>", **_: Any) -> Any:
        self._not_on_target("display", called_from)

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


def ensure_envelope(hal: Any, clock: Callable[[], float], *, virtual: bool | None = None) -> None:
    """
    Give a HAL the envelope its board declares, unless one is installed already (a session
    installs its own, with the durable record on `linux`). `Conversation` calls this next to
    installing the token ledger, so a HAL driven through `c.do()` is bounded by its board
    whoever built it. `clock` is the session's, in milliseconds. On `sim` the envelope ends
    an on-time by itself at its deadline (there is no timer); anywhere else the HAL ends it
    — unless `virtual` says otherwise (replay decides by recorded time on every target).
    """
    if not isinstance(hal, HardwareAbstractionLayer) or hal.envelope is not None:
        return
    if hal.board is None:
        return
    envelope = SafetyEnvelope.for_board(
        hal.board, clock=clock, virtual=hal.target == "sim" if virtual is None else virtual
    )
    if envelope.names:
        hal.envelope = envelope
