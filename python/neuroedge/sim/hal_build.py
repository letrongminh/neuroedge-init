"""
The HAL of a session, built one way for everyone who runs the core: `SimSession` and
`neuroedge.guard.Guard` (RFC-0016 §3b item 1). `sim` gets a `SimHAL` with the safety envelope of
its board; `linux` a `TypedLinuxHAL` on real GPIO lines with a durable envelope (RFC-0007 §3d).
The only differences between callers are what they read (`needs`, `sensors`…), never how the
envelope is made.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from ..hal.board import BoardProfile
from ..hal.envelope import INIT_ENV, FileEnvelopeStore, SafetyEnvelope, default_state_dir
from ..hal.sim import SimHAL


def linux_envelope(board: BoardProfile, clock: Any, options: dict[str, Any]) -> SafetyEnvelope:
    """
    The envelope of a `linux` session, with the durable record of each pin's on-time
    (RFC-0007 §3d): one directory per board (`default_state_dir`; `envelope_state` in the
    HAL options overrides it). `envelope_init` (or ``NEUROEDGE_LINUX_ENVELOPE_INIT=1``) says
    this is a new rig and starts the records empty; without it a missing record means the
    window is spent and the pin is refused. These options are consumed here, not the HAL's;
    so is `envelope`, an envelope built by the caller, which replaces all of it.
    """
    given = options.pop("envelope", None)
    state = options.pop("envelope_state", None)
    init = options.pop("envelope_init", None)
    if given is not None:
        return given
    if init is None:
        init = os.environ.get(INIT_ENV) == "1"
    return SafetyEnvelope.for_board(
        board,
        clock=clock,
        virtual=False,
        store=FileEnvelopeStore(state if state is not None else default_state_dir(board.id)),
        init_store=bool(init),
    )


def build_hal(
    target: str,
    board: BoardProfile,
    events: Any,
    options: dict[str, Any],
    *,
    needs: Mapping[str, Any] | None = None,
    units: Mapping[str, str] | None = None,
    sensors: Mapping[str, tuple[Any, Any]] | None = None,
    analog_values: Mapping[str, Any] | None = None,
    input_levels: Mapping[str, Any] | None = None,
    i2c_values: Any = (),
) -> Any:
    """
    The HAL of `target` ('sim' or 'linux') for `board`, writing to `events`. `options` are the
    HAL's own (and `envelope`, which replaces the board's); `needs` is what `LinuxHAL` checks
    before it requests a line. On `sim`, `sensors`, `analog_values`, `input_levels` and
    `i2c_values` are the readings the HAL starts with. Callers release the HAL (`close()`) if
    the rest of their wiring fails.
    """
    if target == "linux":
        from ..hal.linux import TypedLinuxHAL

        hal = TypedLinuxHAL(
            board,
            events=events,
            envelope=linux_envelope(board, events.clock, options),
            needs=needs,
            units=dict(units or {}),
            **options,
        )
        # An audit sees whether the out-of-process line supervisor was on (RFC-0007 §3d).
        events.metadata["supervision"] = hal.supervision
        # What the restart handed the envelope (on-time carried over from a previous run), so
        # that a replay decides the same way from the trace alone (RFC-0007 §3d).
        restored = hal.envelope.restored() if hal.envelope is not None else {}
        if restored:
            events.emit(
                "envelope_restored",
                {"boot_ms": events.offset_of(hal.envelope.boot_ms), "pins": restored},
            )
        return hal
    given = options.pop("envelope", None)  # a caller's own envelope replaces the board's
    if given is None:
        given = SafetyEnvelope.for_board(board, clock=events.clock, virtual=True)
    hal = SimHAL(board, events=events, envelope=given, **options)
    for name, (value, unit) in (sensors or {}).items():
        hal.set_sensor(name, value, unit)
    for channel, value in (analog_values or {}).items():
        hal.set_analog(channel, value)
    for pin, level in (input_levels or {}).items():
        hal.set_digital_in(pin, level)
    for bus, device, register, value, width in i2c_values:
        hal.set_i2c(bus, device, register, value, width=width)
    return hal


def release_hal(hal: Any) -> None:
    """
    End a session's use of its HAL: on linux every line is dropped inactive and released.
    A second Ctrl-C must not stop the lines dropping halfway (SIGTERM/SIGHUP are already
    ignored once their handler runs — cli/main.py), so SIGINT is held off for the call.
    """
    close = getattr(hal, "close", None)
    if close is None:
        return
    import signal
    import threading

    if threading.current_thread() is not threading.main_thread():
        close()
        return
    previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        close()
    finally:
        signal.signal(signal.SIGINT, previous)
