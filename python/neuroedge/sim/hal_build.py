"""
The HAL of a session, built one way for everyone who runs the core: `SimSession` and
`neuroedge.guard.Guard` (RFC-0016 §3b item 1). `sim` gets a `SimHAL` with the safety envelope of
its board; `linux` a `TypedLinuxHAL` on real GPIO lines with a durable envelope (RFC-0007 §3d).
The only differences between callers are what they read (`needs`, `sensors`…), never how the
envelope is made.

Remote actuators (RFC-0018) are wired here too, the same way for both callers: their envelopes
join the board's (ended only by the HAL), and the HAL gets their drivers — on `sim` always the
plugin's `DeviceDouble` (`probe()`), never the device; on `linux` the driver itself, with the off
debt kept on disk next to the envelope's records.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from ..errors import BoardCapabilityError
from ..hal.board import BoardProfile
from ..hal.envelope import (
    INIT_ENV,
    EnvelopeLimits,
    FileEnvelopeStore,
    SafetyEnvelope,
    default_state_dir,
)
from ..hal.remote import FileRemoteStore, MemoryRemoteStore, RemoteBinding
from ..hal.sim import SimHAL
from ..plugins.actuators import SDK_VOCABULARY


def linux_envelope(
    board: BoardProfile,
    clock: Any,
    options: dict[str, Any],
    remote: Mapping[str, EnvelopeLimits] | None = None,
) -> SafetyEnvelope:
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
    directory = state if state is not None else default_state_dir(board.id)
    # Where the remote actuators keep their off debt: next to the envelope's records.
    options["_remote_store"] = (FileRemoteStore(directory), bool(init))
    return SafetyEnvelope.for_board(
        board,
        remote=remote,
        clock=clock,
        virtual=False,
        store=FileEnvelopeStore(directory),
        init_store=bool(init),
    )


def remote_limits(remote: Mapping[str, Any]) -> dict[str, EnvelopeLimits]:
    """The envelope of each remote actuator, from its declaration (`[actuators.<name>.envelope]`)."""
    return {
        name: EnvelopeLimits.from_declaration(bound.declaration.envelope)
        for name, bound in remote.items()
    }


def remote_bindings(remote: Mapping[str, Any], target: str) -> list[RemoteBinding]:
    """
    What the HAL drives for each remote actuator. On `sim` the plugin's double, always: a
    simulated session never reaches a device (RFC-0018 §3a); a plugin with no `probe()` cannot
    run on `sim` at all.
    """
    bindings = []
    for name, bound in remote.items():
        double = None
        if target == "sim":
            try:
                double = bound.driver.probe()
            except Exception as problem:
                raise BoardCapabilityError(
                    where=f"[actuators.{name}] plugin {bound.plugin.name!r} on target 'sim'",
                    why="sim drives a remote actuator only through its plugin's device double, "
                    f"and probe() failed: {type(problem).__name__}: {problem}",
                    how="use a plugin that ships a DeviceDouble, or run on linux",
                ) from None
        bindings.append(
            RemoteBinding(name, bound.driver, bound.plugin.name, SDK_VOCABULARY, double)
        )
    return bindings


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
    remote: Mapping[str, Any] | None = None,
) -> Any:
    """
    The HAL of `target` ('sim' or 'linux') for `board`, writing to `events`. `options` are the
    HAL's own (and `envelope`, which replaces the board's); `needs` is what `LinuxHAL` checks
    before it requests a line. On `sim`, `sensors`, `analog_values`, `input_levels` and
    `i2c_values` are the readings the HAL starts with. `remote` are the checked remote
    actuators (`plugins.actuators.BoundActuator` by name). Callers release the HAL (`close()`) if
    the rest of their wiring fails.
    """
    remote = dict(remote or {})
    if target == "linux":
        from ..hal.linux import TypedLinuxHAL

        envelope = linux_envelope(board, events.clock, options, remote_limits(remote))
        store, init = options.pop("_remote_store", (MemoryRemoteStore(), True))
        hal = TypedLinuxHAL(
            board,
            events=events,
            envelope=envelope,
            needs=needs,
            units=dict(units or {}),
            **options,
        )
        try:
            if remote:
                hal.install_remote(remote_bindings(remote, target), store=store, init_store=init)
        except BaseException:
            release_hal(hal)
            raise
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
        given = SafetyEnvelope.for_board(
            board, remote=remote_limits(remote), clock=events.clock, virtual=True
        )
    elif remote:
        given.extend(remote_limits(remote), hal_ended=True)
    store = options.pop("remote_state", None)  # a directory: the record on disk, as on linux
    hal = SimHAL(board, events=events, envelope=given, **options)
    if remote:
        hal.install_remote(
            remote_bindings(remote, target),
            store=FileRemoteStore(store) if store is not None else MemoryRemoteStore(),
            init_store=True,  # a missing record on sim is a new rig; a corrupt one still is not
        )
    for name, (value, unit) in (sensors or {}).items():
        hal.set_sensor(name, value, unit)
    for channel, value in (analog_values or {}).items():
        hal.set_analog(channel, value)
    for pin, level in (input_levels or {}).items():
        hal.set_digital_in(pin, level)
    for bus, device, register, value, width in i2c_values:
        hal.set_i2c(bus, device, register, value, width=width)
    return hal


def announce_plugins(records: Any, events: Any) -> None:
    """
    Provenance of every enabled plugin (RFC-0016 §3d item 4): printed to stderr at start, in
    `metadata.plugins` of the trace and as one `plugin_loaded` event each. Nothing when none.
    """
    import sys

    records = list(records)
    if not records:
        return
    events.metadata["plugins"] = [record.as_data() for record in records]
    for record in records:
        data = record.as_data()
        events.emit("plugin_loaded", data)
        digest = "editable, no file hash" if record.editable else record.files_sha256
        print(
            f"neuroedge: plugin {record.kind} {record.name!r} from {record.distribution} "
            f"{record.version} ({digest})",
            file=sys.stderr,
        )


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
