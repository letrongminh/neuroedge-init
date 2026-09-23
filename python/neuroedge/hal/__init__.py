"""
Hardware Abstraction Layer (HAL) — L1.

Five immutable primitives (FR-HAL-01): `audio.in`, `audio.out`, `digital.out`,
`sensor.read`, `display`. The set is closed on purpose; see
docs/spec/hal_mcu_review.md for what that buys on the microcontroller.
"""

from collections.abc import Callable
from typing import Any

from ..errors import ActionContractViolation
from .board import (
    PRIMITIVES,
    SUPPORTED_TARGETS,
    BoardProfile,
    available_boards,
    load_board,
    load_board_by_id,
)

__all__ = [
    "PRIMITIVES",
    "SUPPORTED_TARGETS",
    "BoardProfile",
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

    def pin(self, name: str) -> PinAssertion:
        """
        Observed state of a pin. A name the board does not declare raises, so a
        misspelled assertion can never pass as "never pulsed" (CEO-S5-2).
        """
        if self.board is not None:
            self.board.require_pin(name, called_from="hal.pin()")
        return self.pins.get(name, PinAssertion(name, pulsed=False))
