"""
The per-pin safety envelope at run time (RFC-0007 §3d, TSK-N2-01, TSK-N2-02, Q-62).

The board declares four numbers per actuator pin (`board.v1`, `BoardProfile.envelope`):
`window_s`, `max_on_ms_per_window`, `min_interval_ms`, `max_continuous_ms`. This module is
the policy that keeps a command inside them. It is the second, independent latch behind the
gate: it can only refuse (`EnvelopeRefusedError`), never allow, and it lives in the HAL
because the accumulated on-time is state of the hardware, not of a gate (invariant #4).

**One reservation per command, made atomically.** `reserve()` checks and reserves under the
pin's own lock, so two concurrent commands cannot both pass the budget that is left. The
reservation is exactly the time the pin will be on: `min(duration, max_continuous_ms)`, or
`max_continuous_ms` when the command has no duration — the HAL turns the pin off at that
deadline, always. A pin that is on (or has a command waiting to start) refuses another `on`
or `pulse`: a pin is not "re-armed" to stay on longer than `max_continuous_ms`.

**Toward the safe state nothing is ever refused.** `off`, the auto-off, an abort, `close()`
do not call `reserve()`; they call `ended()`, which gives the unused part of the reservation
back. `min_interval_ms` runs from the end of the previous on and only refuses the next `on`.

**Refunds.** `ended()` (the pin went off early) and `refund()` (the command never reached the
pin: `authorize` refused it, the line would not move) both return the unused on-time to the
window; `refund()` returns all of it and restores the interval clock as it was.

**It survives a restart.** With a `FileEnvelopeStore` the on-time is written *before* the pin
is turned on (write-ahead). After a restart there is no trusted clock across boots, so every
recorded on counts as having happened just before startup and holds budget until `window_s`
after it, and each pin waits `min_interval_ms` before its first on. A record that is missing,
corrupt or cannot be written means the window is treated as spent: the pin is refused
(`window_unreadable`), never allowed. `sim` keeps the same state in memory only.

The clock is injected (milliseconds, as `EventLog.clock`): tests and replay never read the
wall clock. `virtual=True` (`sim`) ends a reservation at its deadline by itself, because `sim`
has no timer that turns a pin off; with `virtual=False` (`linux`) only the HAL ending the pin
ends it, so a late timer never lets a second command start on a pin still driven.
"""

from __future__ import annotations

import contextlib
import json
import math
import os
import re
import tempfile
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..errors import EnvelopeRefusedError

if TYPE_CHECKING:
    from .board import BoardProfile

__all__ = [
    "INIT_ENV",
    "STATE_ENV",
    "EnvelopeLimits",
    "FileEnvelopeStore",
    "Reservation",
    "SafetyEnvelope",
    "default_state_dir",
]

Clock = Callable[[], float]
STATE_ENV = "NEUROEDGE_LINUX_ENVELOPE_STATE"  # the directory of the durable records (linux)
INIT_ENV = "NEUROEDGE_LINUX_ENVELOPE_INIT"  # "1": a new rig, start the records empty
_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")
_RECORD_VERSION = 1


def _monotonic_ms() -> float:
    return time.monotonic() * 1000.0


@dataclass(frozen=True)
class EnvelopeLimits:
    """The four numbers of one pin or channel, as `board.v1` declares them."""

    window_s: float
    max_on_ms_per_window: float
    min_interval_ms: float
    max_continuous_ms: float

    @classmethod
    def from_declaration(cls, declared: Mapping[str, Any]) -> EnvelopeLimits:
        return cls(
            window_s=declared["window_s"],
            max_on_ms_per_window=declared["max_on_ms_per_window"],
            min_interval_ms=declared["min_interval_ms"],
            max_continuous_ms=declared["max_continuous_ms"],
        )


@dataclass
class Reservation:
    """
    The on-time one command holds. `start_ms` is when the pin turns on (a scheduled command
    starts later than it was asked), `reserved_ms` how long it may stay on.
    """

    name: str
    operation: str
    requested_ms: int  # the duration the command carried; 0 = none
    start_ms: float
    reserved_ms: float
    previous_end_ms: float | None = field(repr=False)  # the interval clock before this command
    ended_ms: float | None = None

    @property
    def deadline_ms(self) -> float:
        return self.start_ms + self.reserved_ms

    @property
    def auto_off_cause(self) -> str | None:
        """
        Why the HAL turns the pin off, when the command itself did not say so: ``None``
        for a pulse or an `on` that carried its own duration, `max_continuous_ms` when the
        envelope cut the command short or it had no end.
        """
        if self.operation == "pulse" or self.requested_ms > 0:
            return "max_continuous_ms" if self.reserved_ms < self.requested_ms else None
        return "max_continuous_ms"


@dataclass
class _Interval:
    start: float
    end: float
    # A recorded on of a previous run: it holds `weight` ms of budget until `end` leaves the
    # window, whatever it measured (the restart rule).
    weight: float | None = None

    @property
    def length(self) -> float:
        return self.weight if self.weight is not None else self.end - self.start

    def counted(self, horizon: float) -> float:
        if self.weight is not None:
            return self.weight
        return max(0.0, self.end - max(self.start, horizon))


@dataclass
class _State:
    limits: EnvelopeLimits
    lock: threading.Lock = field(default_factory=threading.Lock)
    intervals: list[_Interval] = field(default_factory=list)
    live: Reservation | None = None
    last_end: float | None = None
    unreadable: str | None = None  # why the record cannot be trusted; the window is spent


class StateUnreadable(Exception):
    """A durable record is missing, corrupt, or cannot be written."""


# -- the durable record (linux) ----------------------------------------------------


def default_state_dir(board_id: str) -> Path:
    """
    Where a rig keeps the on-time of its pins: one directory per board, because the pins
    belong to the rig and not to whichever agent drives them today — two agents on one
    board share one window. `NEUROEDGE_LINUX_ENVELOPE_STATE` names the directory itself;
    otherwise ``$XDG_STATE_HOME`` (``~/.local/state``) / ``neuroedge/envelope/<board id>``.
    """
    explicit = os.environ.get(STATE_ENV)
    if explicit:
        return Path(explicit)
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "neuroedge" / "envelope" / board_id


class FileEnvelopeStore:
    """
    One JSON record per pin, ``<directory>/<pin>.json``: ``{"version": 1, "name": pin,
    "on_ms": [...]}``, the reserved on-time of every command still inside the window. A pin
    has its own file so that the pin's own lock covers its write. Writes go to a temporary
    file that is synced and renamed into place, then the directory is synced: a crash leaves
    the old record or the new one, never half of one.
    """

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def path(self, name: str) -> Path:
        if not _NAME.fullmatch(name):
            raise StateUnreadable(f"{name!r} is not a name this store can keep a record under")
        return self.directory / f"{name}.json"

    def load(self, name: str) -> list[float] | None:
        """The recorded on-times, or None when there is no record. Raises when it is unreadable."""
        path = self.path(name)
        try:
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise StateUnreadable(f"{path} cannot be read: {exc.strerror or exc}") from exc
        try:
            record = json.loads(raw)
        except ValueError as exc:
            raise StateUnreadable(f"{path} is not valid JSON ({exc})") from exc
        if not isinstance(record, dict) or record.get("version") != _RECORD_VERSION:
            raise StateUnreadable(f"{path} is not a version {_RECORD_VERSION} record")
        if record.get("name") != name:
            raise StateUnreadable(f"{path} belongs to {record.get('name')!r}, not {name!r}")
        on_ms = record.get("on_ms")
        if not isinstance(on_ms, list) or not all(
            isinstance(x, int | float) and not isinstance(x, bool) and math.isfinite(x) and x >= 0
            for x in on_ms
        ):
            raise StateUnreadable(f"{path}: on_ms is not a list of non-negative numbers")
        return [float(x) for x in on_ms]

    def create(self, name: str) -> None:
        """An empty record, only where there is none: a new rig starts its budget here."""
        path = self.path(name)
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            return
        except OSError as exc:
            raise StateUnreadable(f"{path} cannot be created: {exc.strerror or exc}") from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(self._document(name, []))
            handle.flush()
            os.fsync(handle.fileno())
        self._sync_directory()

    def save(self, name: str, on_ms: Sequence[float]) -> None:
        """Replace the record. Raises `OSError` when it cannot be made durable."""
        path = self.path(name)
        self.directory.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=self.directory, prefix=f".{name}.", suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as out:
                out.write(self._document(name, on_ms))
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(temporary)
            raise
        self._sync_directory()

    @staticmethod
    def _document(name: str, on_ms: Sequence[float]) -> str:
        return json.dumps({"version": _RECORD_VERSION, "name": name, "on_ms": list(on_ms)}) + "\n"

    def _sync_directory(self) -> None:
        descriptor = os.open(self.directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


# -- the policy --------------------------------------------------------------------


class SafetyEnvelope:
    def __init__(
        self,
        limits: Mapping[str, EnvelopeLimits],
        *,
        clock: Clock = _monotonic_ms,
        virtual: bool = True,
        store: FileEnvelopeStore | None = None,
        init_store: bool = False,
    ) -> None:
        """
        `limits` maps a pin (or, later, a PWM or motion channel) to its numbers. With a
        `store`, each pin's record is read now: a record that exists is carried over and the
        pin waits `min_interval_ms` before its first on; one that is missing makes the pin
        refuse every on, unless `init_store` says this is a new rig and starts it empty.
        """
        self.clock = clock
        self.virtual = virtual
        self.store = store
        # Called, outside every lock, for each reservation the envelope itself ended at its
        # deadline (`virtual`): the HAL records that the pin went off and why.
        self.on_auto_off: Callable[[Reservation], None] | None = None
        self._states = {name: _State(declared) for name, declared in limits.items()}
        if store is not None:
            self._restore(init_store)

    @classmethod
    def for_board(cls, board: BoardProfile, **options: Any) -> SafetyEnvelope:
        """The envelope of every pin and channel `board` declares one for."""
        names = [*board.pins, *(c["name"] for c in board.motion_channels)]
        declared = {name: board.envelope(name) for name in names}
        return cls(
            {name: EnvelopeLimits.from_declaration(d) for name, d in declared.items() if d},
            **options,
        )

    # -- what the envelope covers ---------------------------------------------------
    def covers(self, name: str) -> bool:
        return name in self._states

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._states)

    def limits(self, name: str) -> EnvelopeLimits:
        return self._states[name].limits

    def live(self, name: str) -> Reservation | None:
        """The command that holds the pin on (or waits to start), if any."""
        state = self._states.get(name)
        if state is None:
            return None
        fired: list[Reservation] = []
        with state.lock:
            self._settle(state, self.clock(), fired)
            live = state.live
        self._announce(fired)
        return live

    # -- the restart rule ------------------------------------------------------------
    def _restore(self, init_store: bool) -> None:
        assert self.store is not None
        boot = self.clock()
        for name, state in self._states.items():
            try:
                recorded = self.store.load(name)
                if recorded is None and init_store:
                    self.store.create(name)
                    continue  # nothing ran before: no carried budget, no wait
                if recorded is None:
                    raise StateUnreadable(f"{self.store.path(name)} does not exist")
            except StateUnreadable as exc:
                state.unreadable = str(exc)
                continue
            # No trusted clock across boots: a recorded on counts as just before startup.
            state.intervals = [_Interval(boot, boot, weight=on) for on in recorded if on > 0]
            state.last_end = boot

    def _persist(self, name: str, state: _State) -> None:
        """Write the pin's on-time down. The caller holds the pin's lock."""
        if self.store is None:
            return
        self.store.save(name, [math.ceil(i.length) for i in state.intervals])

    # -- check and reserve -----------------------------------------------------------
    def reserve(
        self,
        name: str,
        duration_ms: int,
        *,
        operation: str,
        after_ms: float = 0,
        called_from: str = "<unknown>",
    ) -> Reservation | None:
        """
        Check the command against the envelope and reserve its on-time, as one step under
        the pin's lock. Returns the reservation, or None for a pin the envelope does not
        cover (a `signal_pins` pin: it behaves as it always did). `after_ms` is how long a
        scheduled command waits before it turns the pin on. Raises `EnvelopeRefusedError`; nothing is held then.

        Never call this for a command toward the safe state: that is `ended()`.
        """
        state = self._states.get(name)
        if state is None:
            return None
        fired: list[Reservation] = []
        try:
            with state.lock:
                now = self.clock()
                start = now + max(0.0, after_ms)
                self._settle(state, now, fired)
                limits = state.limits
                where = f"{called_from} -> digital.out {name!r}"
                if state.unreadable is not None:
                    raise self._refusal(
                        name,
                        operation,
                        "window_unreadable",
                        where,
                        f"the record of this pin's on-time is unusable ({state.unreadable}), so "
                        "the whole window counts as spent",
                        "restore the record, or on a new rig start it empty "
                        "(LinuxHAL envelope_init / NEUROEDGE_LINUX_ENVELOPE_INIT=1); "
                        "`off` still works",
                    )
                if state.live is not None:
                    raise self._refusal(
                        name,
                        operation,
                        "already_on",
                        where,
                        "the pin is already on (or a command for it is waiting to start); a "
                        "second on would restart its max_continuous_ms",
                        "wait for it to end, or turn it off first",
                        remaining_ms=_whole(max(0.0, state.live.deadline_ms - now)),
                    )
                if state.last_end is not None:
                    wait = state.last_end + limits.min_interval_ms - start
                    if wait > 0:
                        raise self._refusal(
                            name,
                            operation,
                            "min_interval_ms",
                            where,
                            f"the pin turned off {_whole(start - state.last_end)} ms ago and "
                            f"must stay off for min_interval_ms {_whole(limits.min_interval_ms)}",
                            f"retry in {_whole(wait)} ms",
                            limit_ms=_whole(limits.min_interval_ms),
                            wait_ms=_whole(wait),
                        )
                if duration_ms > 0:
                    reserved = float(min(duration_ms, limits.max_continuous_ms))
                else:
                    reserved = float(limits.max_continuous_ms) if operation != "pulse" else 0.0
                horizon = start - limits.window_s * 1000.0
                state.intervals = [i for i in state.intervals if i.end > horizon]
                used = sum(i.counted(horizon) for i in state.intervals)
                if used + reserved > limits.max_on_ms_per_window:
                    raise self._refusal(
                        name,
                        operation,
                        "window_budget",
                        where,
                        f"{_whole(reserved)} ms on would bring the last {_whole(limits.window_s)}"
                        f" s to {_whole(used + reserved)} ms, over max_on_ms_per_window "
                        f"{_whole(limits.max_on_ms_per_window)} ({_whole(used)} ms already used)",
                        "ask for less, or wait for earlier on-time to leave the window",
                        limit_ms=_whole(limits.max_on_ms_per_window),
                        used_ms=_whole(used),
                        requested_ms=_whole(reserved),
                    )
                reservation = Reservation(
                    name, operation, int(duration_ms), start, reserved, state.last_end
                )
                state.intervals.append(_Interval(start, reservation.deadline_ms))
                state.live = reservation
                try:
                    self._persist(name, state)  # write-ahead: before the pin is turned on
                except (OSError, StateUnreadable) as exc:
                    state.intervals.pop()
                    state.live = None
                    raise self._refusal(
                        name,
                        operation,
                        "window_unreadable",
                        where,
                        f"the on-time could not be recorded before the pin is turned on "
                        f"({getattr(exc, 'strerror', None) or exc}), so the command is refused",
                        "make the envelope state directory writable "
                        f"({self.store.directory if self.store else '-'})",
                    ) from exc
                return reservation
        finally:
            self._announce(fired)

    def _refusal(
        self,
        name: str,
        operation: str,
        reason: str,
        where: str,
        why: str,
        how: str,
        **numbers: int,
    ) -> EnvelopeRefusedError:
        return EnvelopeRefusedError(
            where,
            why,
            how,
            reason=reason,
            event={"pin": name, "operation": operation, "reason": reason, **numbers},
        )

    # -- the end of an on --------------------------------------------------------------
    def ended(self, name: str, reservation: Reservation | None = None) -> Reservation | None:
        """
        The pin is in its safe state now: whatever it was holding ends here and the unused
        part of the reservation goes back to the window. A command that had not yet turned
        the pin on is refunded in full. Never refuses; returns the reservation it closed.
        With `reservation`, only that command is ended: an abort of a command that is long
        over must not end the one that holds the pin now.
        """
        state = self._states.get(name)
        if state is None:
            return None
        fired: list[Reservation] = []
        try:
            with state.lock:
                now = self.clock()
                self._settle(state, now, fired)
                live = state.live
                if live is None or (reservation is not None and live is not reservation):
                    return None
                if now < live.start_ms:
                    return self._refund(name, state, live)
                end = min(now, live.deadline_ms) if self.virtual else now
                self._finish(state, live, end)
                self._persist_quietly(name, state)
                return live
        finally:
            self._announce(fired)

    def refund(self, reservation: Reservation) -> None:
        """The command never reached the pin: give back every millisecond it reserved."""
        state = self._states.get(reservation.name)
        if state is None:
            return
        with state.lock:
            if state.live is reservation:
                self._refund(reservation.name, state, reservation)

    def _refund(self, name: str, state: _State, reservation: Reservation) -> Reservation:
        # The reservation's interval is the newest one: nothing else can start while it lives.
        state.intervals.pop()
        state.live = None
        state.last_end = reservation.previous_end_ms
        reservation.ended_ms = reservation.start_ms
        self._persist_quietly(name, state)
        return reservation

    def _finish(self, state: _State, reservation: Reservation, end: float) -> None:
        end = max(end, reservation.start_ms)
        state.intervals[-1].end = end
        state.last_end = end
        state.live = None
        reservation.ended_ms = end

    def _persist_quietly(self, name: str, state: _State) -> None:
        # A record that could not be lowered still holds the larger, reserved figure:
        # safe-side stale, so a failure here is not a reason to hold the pin on.
        with contextlib.suppress(OSError, StateUnreadable):
            self._persist(name, state)

    # -- sim: the pin goes off by itself ------------------------------------------------
    def _settle(self, state: _State, now: float, fired: list[Reservation]) -> None:
        live = state.live
        if self.virtual and live is not None and live.deadline_ms <= now:
            self._finish(state, live, live.deadline_ms)
            self._persist_quietly(live.name, state)
            fired.append(live)
        elif live is not None and not self.virtual:
            state.intervals[-1].end = max(state.intervals[-1].end, now)  # on past its deadline

    def settle(self) -> None:
        """Let every virtual reservation whose deadline has come end (the `sim` clock ticked)."""
        for name in self._states:
            with self._states[name].lock:
                fired: list[Reservation] = []
                self._settle(self._states[name], self.clock(), fired)
            self._announce(fired)

    def end_all(self) -> None:
        """`close()`: every pin is in its safe state, so nothing is held any more."""
        for name in self._states:
            self.ended(name)

    def _announce(self, fired: list[Reservation]) -> None:
        if self.on_auto_off is not None:
            for reservation in fired:
                self.on_auto_off(reservation)


def _whole(value: float) -> int:
    return math.ceil(value)
