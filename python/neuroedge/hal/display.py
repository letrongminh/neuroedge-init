"""
`display.show(frame)` — draw on the board's display from inside an `@action` body.

    display.show("Cửa phòng 101 đã mở")                          # a text screen
    display.show(pixels, width=320, height=240, format="rgb565")  # raw pixels

Like `sensor.read`, it uses the HAL of the running `c.do()`; the frame is checked
against the board's declared resolution and recorded as `display_frame` with a
SHA-256 digest (docs/spec/simulation_coverage.md §3).
"""

from __future__ import annotations

from typing import Any

from ..errors import ActionContractViolation
from .digital import _active, _caller


def show(
    frame: str | bytes,
    *,
    width: int | None = None,
    height: int | None = None,
    format: str | None = None,
) -> Any:
    active = _active.get()
    where = _caller()
    if active is None:
        raise ActionContractViolation(
            where=f"{where} -> display.show()",
            why="no HAL is active; the display is drawn inside an @action run by c.do()",
            how="call display.show() in an @action body, or hal.display() in a test",
        )
    return active.hal.display(
        frame, width=width, height=height, format=format, called_from=f"{where} ({active.action})"
    )
