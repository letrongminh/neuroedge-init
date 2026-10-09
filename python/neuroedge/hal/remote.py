"""
Remote actuators in the HAL (RFC-0018 §3c–§3h, TSK-I2c-16).

A remote actuator is a named `digital.out` the board does not have, driven by a plugin of the
group `neuroedge.actuators`. Only the HAL holds the plugin. `HardwareAbstractionLayer` sends a
command for one through the path of every pin — `require_pin → state check → envelope →
authorize → record → apply` — and this module is the part after the name: the HAL's own state
of the device, the timers of its safe-off level, the off debt, and what the trace says about it.

**The state is the HAL's, not the device's** (§3g): `off` (confirmed), `on` (a command of
NeuroEdge is live), `uncertain` (the HAL does not know), `quarantined` (the device broke the
level it declared). An `on` or `pulse` passes the state check only from `off` with a reading no
older than `MAX_STATE_AGE_MS`; otherwise it is refused before the envelope and the token
(`actuator_state_unknown`, `actuator_quarantined`, `already_on`). Only a fresh reading of `off`
leaves `uncertain` — never a timer. A device that is not read back (`readback = "none"`) is
`off` once an off was acknowledged.

**The off debt.** The HAL only ever turns off what it turned on: an `on` it sent (or may have
sent) and nobody has confirmed off. The off is `Actuator.safe_off()` — no envelope, no token,
never refused, never raised to the caller (a failure is a `remote_command_failed` and a retry
every `OFF_RETRY_MS`). An `on` is never sent again by itself.

**The level** decides who ends an on (§3d), with `D` the reservation the envelope made:

* L0, L1 — the HAL sends the off at `D` (within `OFF_SLACK_MS`) and repeats it until confirmed;
* L2 — every `on` carries `duration_ms = D`; the device ends it;
* L3 — `on` carries a lease, renewed every lease/3 and never past `start + D − lease`.

At L2 and L3 the HAL reads the state back at `start + D + tolerance_ms` (P2, §3e): `off` is
evidence the level held; `on` is `remote_level_violated`, an off, and `quarantined`. Without a
read-back the HAL sends its off at `D` as at L1 and the on-time counts until the guarantee.

**The envelope** (§3h) ends a remote run only when the HAL knows the device is off (`ended(at=…)`),
or at the guarantee at L2/L3 without a read-back — never earlier. Its record is written before the
command, and so is the off debt (`RemoteStateStore`). After a restart every remote actuator is
`uncertain`; a record that cannot be read makes it `quarantined`, which only the operator lifts,
on the record.

`sim` drives the plugin's `DeviceDouble` (its `probe()`), never the device; the double's clock
follows the session's.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
import threading
from collections import deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import BoardCapabilityError, EnvelopeRefusedError
from .envelope import Reservation, SafetyEnvelope

__all__ = [
    "MAX_STATE_AGE_MS",
    "OFF_RETRY_MS",
    "OFF_SLACK_MS",
    "FileRemoteStore",
    "MemoryRemoteStore",
    "RemoteActuator",
    "RemoteBinding",
    "ReplayedRemote",
    "Vocabulary",
]

# RFC-0018 §9.5 (Q-68): fixed; loosening one is an RFC.
OFF_SLACK_MS = 100
OFF_RETRY_MS = 500
MAX_STATE_AGE_MS = 2000

LEVELS = ("L0", "L1", "L2", "L3")
_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")
_RECORD_VERSION = 1


@dataclass(frozen=True)
class Vocabulary:
    """
    The words a plugin speaks — `neuroedge.sdk`'s `Command` and its four errors — handed to the
    HAL by whoever wires it (`plugins.actuators.SDK_VOCABULARY`), so the HAL stays a leaf that
    imports no layer of plugins.
    """

    command: Callable[..., Any]
    not_sent: type[BaseException]
    rejected: type[BaseException]
    ambiguous: type[BaseException]
    read_failed: type[BaseException]


@dataclass(frozen=True)
class RemoteBinding:
    """What the HAL is given for one remote actuator: its name, its driver and its plugin."""

    name: str
    driver: Any  # an `Actuator`: on `sim`, already switched to its double by `probe()`
    plugin: str
    vocabulary: Vocabulary
    double: Any = None  # the `DeviceDouble` on `sim`; None on `linux`


# --- the durable record of the off debt and the quarantine -------------------------------------


class RecordUnreadable(Exception):
    """A remote actuator's state record is missing, corrupt or cannot be written."""


class MemoryRemoteStore:
    """The record of `sim`: in memory, gone with the session (as the envelope's on `sim`)."""

    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}

    def load(self, name: str) -> dict[str, Any] | None:
        record = self.records.get(name)
        return None if record is None else dict(record)

    def save(self, name: str, record: Mapping[str, Any]) -> None:
        self.records[name] = dict(record)

    def create(self, name: str) -> None:
        self.records.setdefault(name, {"off_owed": False, "quarantined": None})

    def clear(self, name: str) -> None:
        """The operator lifts a quarantine: an explicit act on the record, never automatic."""
        self.records[name] = {"off_owed": False, "quarantined": None}


class FileRemoteStore:
    """
    One JSON record per remote actuator, ``<directory>/<name>.remote.json``, next to the
    envelope's records: ``{"version": 1, "name", "off_owed", "quarantined"}``. Written to a
    synced temporary file and renamed, like `FileEnvelopeStore`: never half a record.
    """

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def path(self, name: str) -> Path:
        if not _NAME.fullmatch(name):
            raise RecordUnreadable(f"{name!r} is not a remote actuator name")
        return self.directory / f"{name}.remote.json"

    def load(self, name: str) -> dict[str, Any] | None:
        path = self.path(name)
        try:
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise RecordUnreadable(f"{path} cannot be read: {exc.strerror or exc}") from exc
        try:
            record = json.loads(raw)
        except ValueError as exc:
            raise RecordUnreadable(f"{path} is not valid JSON ({exc})") from exc
        if not isinstance(record, dict) or record.get("version") != _RECORD_VERSION:
            raise RecordUnreadable(f"{path} is not a version {_RECORD_VERSION} record")
        if record.get("name") != name or not isinstance(record.get("off_owed"), bool):
            raise RecordUnreadable(f"{path} is not the record of {name!r}")
        quarantined = record.get("quarantined")
        if quarantined is not None and not isinstance(quarantined, str):
            raise RecordUnreadable(f"{path}: quarantined is a reason or null")
        return {"off_owed": record["off_owed"], "quarantined": quarantined}

    def save(self, name: str, record: Mapping[str, Any]) -> None:
        path = self.path(name)
        self.directory.mkdir(parents=True, exist_ok=True)
        document = {
            "version": _RECORD_VERSION,
            "name": name,
            "off_owed": bool(record.get("off_owed")),
            "quarantined": record.get("quarantined"),
        }
        handle, temporary = tempfile.mkstemp(dir=self.directory, prefix=f".{name}.", suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as out:
                out.write(json.dumps(document) + "\n")
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(temporary)
            raise

    def create(self, name: str) -> None:
        if not self.path(name).exists():
            self.save(name, {"off_owed": False, "quarantined": None})

    def clear(self, name: str) -> None:
        """The operator lifts a quarantine (and forgets the debt): an explicit act, never automatic."""
        self.save(name, {"off_owed": False, "quarantined": None})


# --- one remote actuator ----------------------------------------------------------------------


@dataclass
class _Run:
    """One on of NeuroEdge: its reservation, timers and what the HAL knows of its end."""

    reservation: Reservation
    command_id: str
    start: float
    duration: float  # D
    guarantee: float | None  # L2/L3: start + D + tolerance; None at L0/L1
    lease: int | None = None
    next_renew: float | None = None
    last_renew_at: float | None = None
    renewals: int = 0
    off_due: float | None = None  # when the HAL sends its own off
    checked: bool = False  # P2 done
    known_off: float | None = None  # the instant the HAL knows the device was off
    end_floor: float = 0.0  # the envelope's interval never ends before this
    ended: bool = False


@dataclass
class _Clock:
    now: Callable[[], float]
    offset: Callable[[float], int]


class RemoteActuator:
    """
    The HAL's side of one remote actuator. `guard()` before the envelope, `start()` after
    `authorize`, `off()` for every command toward the safe state, `tick()` for timers.
    Thread-safe: the HAL's timer thread and the caller may meet here.
    """

    def __init__(
        self,
        binding: RemoteBinding,
        *,
        envelope: SafetyEnvelope,
        clock: Callable[[], float],
        emit: Callable[[str, dict[str, Any]], None],
        offset: Callable[[float], int],
        store: Any,
        init_store: bool = False,
    ) -> None:
        self.name = binding.name
        self.words = binding.vocabulary
        self.driver = binding.driver
        self.plugin = binding.plugin
        self.double = binding.double
        self.level: str = binding.driver.safe_off_level
        self.readback: str = binding.driver.readback
        self.tolerance = int(binding.driver.tolerance_ms)
        self.timeout = int(binding.driver.command_timeout_ms)
        self.max_lease = binding.driver.max_lease_ms
        self.envelope = envelope
        self.clock = _Clock(clock, offset)
        self.emit = emit
        self.store = store
        self.lock = threading.RLock()
        self.run: _Run | None = None
        self.off_owed = False
        self.off_pending = False  # an off to send (again) at `off_next`
        self.off_next: float | None = None
        self.off_cause: str | None = None
        self.observed_on: bool | None = None  # the last reading
        self.read_ms: float | None = None  # its mark, on the session clock (the receiver's)
        self.quarantined: str | None = None
        self.uncertain_since: float | None = None
        self.status = "uncertain"
        self._sequence = 0
        self._synced = clock()
        self._restore(init_store)

    # -- the record ------------------------------------------------------------------------
    def _restore(self, init_store: bool) -> None:
        try:
            record = self.store.load(self.name)
            if record is None and init_store:
                self.store.create(self.name)
                record = {"off_owed": False, "quarantined": None}
            if record is None:
                raise RecordUnreadable(f"no state record for {self.name!r}")
        except (RecordUnreadable, OSError) as problem:
            record = {"off_owed": False, "quarantined": f"state record unusable: {problem}"}
        self.off_owed = bool(record.get("off_owed"))
        self.quarantined = record.get("quarantined")
        # After a start nothing is known, whatever the record says (§3h).
        self._unknown("restart")
        if self.quarantined is not None:
            self.status = "quarantined"
        if self.off_owed and self.level in ("L0", "L1"):
            self._schedule_off(self.clock.now(), "restart")  # a debt an L0/L1 device never pays

    def _persist(self) -> None:
        self.store.save(self.name, {"off_owed": self.off_owed, "quarantined": self.quarantined})

    def _persist_quietly(self) -> None:
        # A record that keeps the larger debt is safe-side stale: never a reason to stop.
        with contextlib.suppress(OSError, RecordUnreadable):
            self._persist()

    # -- events ------------------------------------------------------------------------------
    def _offset(self, ms: float) -> int:
        return self.clock.offset(ms)

    def _unknown(self, why: str) -> None:
        now = self.clock.now()
        if self.status != "uncertain" or self.uncertain_since is None:
            self.uncertain_since = now
        if self.status != "quarantined":
            self.status = "uncertain"
        self.emit(
            "remote_state_unknown",
            {"actuator": self.name, "why": why, "since_offset_ms": self._offset(now)},
        )

    def _confirmed(self, state: str) -> None:
        if self.status == "uncertain":
            since = self.uncertain_since if self.uncertain_since is not None else self.clock.now()
            self.emit(
                "remote_state_confirmed",
                {
                    "actuator": self.name,
                    "state": state,
                    "unknown_ms": max(0, int(self.clock.now() - since)),
                },
            )
            self.uncertain_since = None
        if self.status != "quarantined":
            self.status = state

    def _next_id(self, operation: str) -> str:
        self._sequence += 1
        return f"{self.name}-{operation}-{self._sequence}"

    # -- calling the plugin ------------------------------------------------------------------
    def _sync(self) -> None:
        """`sim`: the double's clock follows the session's."""
        now = self.clock.now()
        if self.double is not None and now > self._synced:
            self.double.advance(int(now - self._synced))
            self._synced += int(now - self._synced)

    def _call(self, function: Callable[[], Any]) -> tuple[Any, str | None, str]:
        """(result, failure kind or None, message). Anything unknown counts as ambiguous."""
        began = self.clock.now()
        words = self.words
        try:
            result = function()
        except Exception as problem:  # a plugin's own error: the HAL never guesses it was fine
            kind = (
                "not_sent"
                if isinstance(problem, words.not_sent)
                else "rejected"
                if isinstance(problem, words.rejected)
                else "readback_failed"
                if isinstance(problem, words.read_failed)
                else "ambiguous"
            )
            return None, kind, f"{type(problem).__name__}: {problem}"
        if self.clock.now() - began > self.timeout:
            return None, "ambiguous", f"took longer than command_timeout_ms {self.timeout}"
        return result, None, ""

    def _send(self, command: Any) -> str | None:
        """Send an on/renew (`command`) or the off (None); the failure kind, or None."""
        operation = "off" if command is None else command.operation
        command_id = self._next_id("off") if command is None else command.id
        data: dict[str, Any] = {
            "actuator": self.name,
            "command_id": command_id,
            "operation": operation,
            "level": self.level,
            "plugin": self.plugin,
        }
        if command is not None and command.duration_ms is not None:
            data["duration_ms"] = command.duration_ms
        if command is not None and command.lease_ms is not None:
            data["lease_ms"] = command.lease_ms
        self.emit("remote_command_sent", data)
        began = self.clock.now()
        if command is None:
            _, kind, _ = self._call(self.driver.safe_off)
        else:
            _, kind, _ = self._call(lambda: self.driver.apply(command))
        if kind is None:
            self.emit(
                "remote_command_acked",
                {
                    "actuator": self.name,
                    "command_id": command_id,
                    "latency_ms": max(0, int(self.clock.now() - began)),
                },
            )
            return None
        if kind == "readback_failed":
            kind = "ambiguous"
        self.emit(
            "remote_command_failed", {"actuator": self.name, "command_id": command_id, "kind": kind}
        )
        return kind

    def read(self) -> bool | None:
        """
        Read the state back (never with `readback = none`): the device's state when a fresh
        reading came, None when none did (the actuator is then `uncertain`).
        """
        if self.readback == "none":
            return None
        before = self.clock.now()
        result, kind, _ = self._call(self.driver.read_state)
        if kind is not None or not _reading(result):
            self.observed_on = None
            self._unknown("readback_failed" if kind is not None else "link_lost")
            return None
        on, age = bool(result[0]), int(result[1])
        mark = before - age  # the receiver's mark; the plugin's age only adds (RFC-0014 §3f)
        self.observed_on, self.read_ms = on, mark
        self.emit(
            "remote_state",
            {
                "actuator": self.name,
                "state": "on" if on else "off",
                "via": self.readback,
                "read_offset_ms": self._offset(mark),
            },
        )
        if self.clock.now() - mark > MAX_STATE_AGE_MS:
            self._unknown("stale")
            return None
        if not on:
            self._knew_off(mark)
        elif self.off_owed and (self.run is None or self.status == "uncertain"):
            # On when the HAL did not expect it: an on that arrived late (after an ambiguous
            # send), or an off that did not land. It turns off what it may have turned on — now.
            self._schedule_off(self.clock.now(), "late_on")
        return on

    def _knew_off(self, at: float) -> None:
        """The device is known off at `at`: the debt is paid and the run, if any, ends."""
        run = self.run
        if run is not None and run.known_off is None:
            run.known_off = at
        if self.off_owed:
            self.off_owed = False
            self._persist_quietly()
        self.off_pending, self.off_next, self.off_cause = False, None, None
        self._confirmed("off")
        self._settle_run(self.clock.now())

    # -- the state check, before the envelope ---------------------------------------------
    def guard(self, operation: str, called_from: str) -> None:
        """Refuse an on or a pulse the HAL cannot vouch for: before the envelope and the token."""
        with self.lock:
            self._sync()
            self.tick_locked()
            if self.status != "quarantined" and self.readback != "none":
                self.read()
                self.tick_locked()  # an off the reading made due goes now, before the answer
            reason, why = self._refusal()
            if reason is None:
                return
            refusal = EnvelopeRefusedError(
                f"{called_from} -> digital.out {self.name!r}",
                why,
                "`off` still works; "
                + {
                    "actuator_state_unknown": "the HAL accepts an on again once a fresh reading "
                    "says the device is off (or, with no read-back, once an off is acknowledged)",
                    "actuator_quarantined": "the device broke its declared safe-off level; the "
                    "operator lifts the quarantine on the state record, after checking it",
                    "already_on": "it is on already — wait for it to end, or turn it off first",
                }[reason],
                reason=reason,
                event={
                    "pin": self.name,
                    "operation": operation,
                    "reason": reason,
                    "state": self.status,
                },
            )
            self.emit("envelope_refused", refusal.event)
            raise refusal

    def _refusal(self) -> tuple[str | None, str]:
        if self.status == "quarantined":
            return "actuator_quarantined", (
                f"remote actuator {self.name!r} is quarantined ({self.quarantined})"
            )
        fresh = self.read_ms is not None and self.clock.now() - self.read_ms <= MAX_STATE_AGE_MS
        if fresh and self.observed_on and not self.off_owed:
            return "already_on", (
                f"a reading says {self.name!r} is on, and NeuroEdge did not turn it on: another "
                "controller did, and the HAL does not command on top of it"
            )
        if self.status == "uncertain":
            return "actuator_state_unknown", (
                f"the HAL does not know whether remote actuator {self.name!r} is off"
            )
        if self.status == "on" or self.run is not None:
            return "already_on", f"remote actuator {self.name!r} is on by an earlier command"
        if self.readback != "none":
            if self.read_ms is None or self.clock.now() - self.read_ms > MAX_STATE_AGE_MS:
                return "actuator_state_unknown", (
                    f"the last reading of {self.name!r} is older than {MAX_STATE_AGE_MS} ms"
                )
            if self.observed_on:
                return "already_on", (
                    f"a reading says {self.name!r} is on, and NeuroEdge did not turn it on: "
                    "another controller did, and the HAL does not command on top of it"
                )
        return None, ""

    # -- an on, after the envelope and the token -------------------------------------------
    def start(self, reservation: Reservation, operation: str) -> None:
        """Send the on the HAL admitted. Raises when it did not certainly reach the device."""
        with self.lock:
            now = self.clock.now()
            duration = reservation.reserved_ms
            lease = None
            if self.level == "L3":
                lease = int(min(duration, self.max_lease or duration))
            command = self.words.command(
                self._next_id("on"),
                "on",
                duration_ms=int(duration) if self.level == "L2" else None,
                lease_ms=lease,
            )
            owed_before = self.off_owed
            try:
                self.off_owed = True  # write-ahead: the debt exists before the command does
                self._persist()
            except (OSError, RecordUnreadable) as problem:
                self.off_owed = owed_before
                self.envelope.refund(reservation)
                raise BoardCapabilityError(
                    where=f"digital.out {self.name!r}",
                    why=f"the off debt could not be recorded before the command ({problem}), so "
                    "the command is not sent",
                    how="make the envelope state directory writable; `off` still works",
                ) from problem
            run = _Run(
                reservation,
                command.id,
                start=now,
                duration=duration,
                guarantee=now + duration + self.tolerance if self.level in ("L2", "L3") else None,
                lease=lease,
            )
            if self.level in ("L0", "L1") or self.readback == "none":
                run.off_due = now + duration
            if self.level in ("L2", "L3") and self.readback == "none":
                run.end_floor = now + duration + self.tolerance
            if lease is not None and duration > lease:
                run.next_renew = now + lease / 3
            self._sync()
            kind = self._send(command)
            if kind in ("not_sent", "rejected"):
                # Certainly not delivered: the device is as it was, and so are the HAL's books.
                self.envelope.refund(reservation)
                self.off_owed = owed_before
                self._persist_quietly()
                raise BoardCapabilityError(
                    where=f"digital.out {self.name!r}",
                    why=f"plugin {self.plugin!r} says the on did not reach the device ({kind})",
                    how="check the link to the device; the envelope gave the on-time back",
                )
            self.run = run
            run.last_renew_at = now
            if kind == "ambiguous":
                # It may have arrived: the reservation stays, the device may be on.
                self._unknown("command_timeout")
                raise BoardCapabilityError(
                    where=f"digital.out {self.name!r}",
                    why=f"plugin {self.plugin!r} cannot say whether the on reached the device "
                    "(ambiguous): it is treated as on, and the HAL will turn it off",
                    how="the actuator refuses another on until a fresh reading says it is off",
                )
            self._confirmed("on")
            self._wake()

    # -- toward the safe state: never refused, never raised -----------------------------------
    def off(self, cause: str = "command") -> None:
        """An off: always tried, needs nothing, failures recorded and retried while owed."""
        with self.lock:
            self._sync()
            self._send_off(cause)

    def _schedule_off(self, at: float, cause: str) -> None:
        self.off_pending = True
        if self.off_next is None or at < self.off_next:
            self.off_next = at
        self.off_cause = self.off_cause or cause
        self._wake()

    def _send_off(self, cause: str) -> None:
        now = self.clock.now()
        kind = self._send(None)
        if kind is not None:
            if self.off_owed or self.run is not None:
                if self.status not in ("uncertain", "quarantined"):
                    self._unknown("command_timeout" if kind == "ambiguous" else "link_lost")
                self.off_pending, self.off_next = True, now + OFF_RETRY_MS
                self.off_cause = self.off_cause or cause
            self._wake()
            return
        if self.readback == "none":
            self._knew_off(now)  # with no read-back, an acknowledged off is the confirmation
            return
        if self.read() is not False and (self.off_owed or self.run is not None):
            # Not known off yet (on, or no reading): the off is sent again until it is.
            self.off_pending, self.off_next = True, self.clock.now() + OFF_RETRY_MS
            self.off_cause = self.off_cause or cause
        self._wake()

    # -- timers ------------------------------------------------------------------------------
    def tick(self) -> None:
        with self.lock:
            self._sync()
            self.tick_locked()

    def tick_locked(self) -> None:
        now = self.clock.now()
        run = self.run
        if run is not None and not run.ended:
            self._renew(run, now)
            if run.off_due is not None and now >= run.off_due and run.known_off is None:
                run.off_due = None
                self._deadline_off(run)
            if (
                run.guarantee is not None
                and not run.checked
                and now >= run.guarantee
                and self.readback != "none"
            ):
                run.checked = True
                self._proof(run)
        if self.off_pending and self.off_next is not None and now >= self.off_next:
            self.off_pending, self.off_next = False, None
            self._send_off(self.off_cause or "retry")
        self._settle_run(self.clock.now())

    def _renew(self, run: _Run, now: float) -> None:
        if run.lease is None or run.next_renew is None:
            return
        stop = run.start + run.duration - run.lease
        while run.next_renew is not None and now >= run.next_renew:
            at = run.next_renew
            if at > stop or self.status != "on":
                run.next_renew = None
                return
            run.renewals += 1
            command = self.words.command(self._next_id("renew"), "renew", lease_ms=run.lease)
            kind = self._send(command)
            if kind is not None:
                # The device drops by itself when the lease ends; the HAL stops renewing and
                # does not claim to know more.
                run.next_renew = None
                self._unknown("command_timeout" if kind == "ambiguous" else "link_lost")
                return
            run.last_renew_at = at
            following = at + run.lease / 3
            run.next_renew = following if following <= stop else None

    def _deadline_off(self, run: _Run) -> None:
        """The HAL's own off at `D` (L0, L1, and any level without a read-back)."""
        cause = run.reservation.auto_off_cause
        if cause is not None:
            self.emit(
                "actuator_command",
                {"pin": self.name, "operation": "off", "duration_ms": 0, "cause": cause},
            )
        self._send_off(cause or "deadline")

    def _proof(self, run: _Run) -> None:
        """P2 (§3e): at the guarantee, the device is off — evidence — or it broke its level."""
        state = self.read()
        if state is None:
            self._schedule_off(self.clock.now(), "readback_failed")  # fall back to the HAL's off
            return
        if state is False:
            return  # `read()` recorded the evidence and ended the run
        self.quarantined = (
            f"still on {int(self.clock.now() - run.start)} ms after its {self.level} start"
        )
        self.status = "quarantined"
        self._persist_quietly()
        self.emit(
            "remote_level_violated",
            {
                "actuator": self.name,
                "level": self.level,
                "expected_off_ms": int(run.duration + self.tolerance),
                "observed": "on",
            },
        )
        self._send_off("level_violated")

    def _settle_run(self, now: float) -> None:
        run = self.run
        if run is None or run.ended or run.known_off is None:
            return
        if now < run.end_floor:
            self._wake()
            return
        run.ended = True
        self.envelope.ended(self.name, run.reservation, at=max(run.known_off, run.end_floor))
        self.run = None

    def next_due(self) -> float | None:
        """
        The next instant this actuator has something to do, or None. Read without the lock (a
        timer thread asks while another actuator holds its own): a stale answer only makes a
        tick come early, and every tick re-arms.
        """
        due: list[float] = []
        run = self.run
        if run is not None and not run.ended:
            for at in (run.next_renew, run.off_due):
                if at is not None:
                    due.append(at)
            if run.guarantee is not None and not run.checked and self.readback != "none":
                due.append(run.guarantee)
            if run.known_off is not None:
                due.append(run.end_floor)
        off_next = self.off_next
        if self.off_pending and off_next is not None:
            due.append(off_next)
        return min(due) if due else None

    wake: Callable[[], None] | None = None

    def _wake(self) -> None:
        if self.wake is not None:
            self.wake()

    def close(self) -> None:
        """The end of a session: one off for every debt (never raised); nothing else is touched."""
        with self.lock:
            self._sync()
            if self.off_owed or self.run is not None:
                self._send_off("close")
            self.off_pending, self.off_next = False, None


def _reading(result: Any) -> bool:
    return (
        isinstance(result, tuple)
        and len(result) == 2
        and isinstance(result[0], bool)
        and isinstance(result[1], int)
        and not isinstance(result[1], bool)
        and result[1] >= 0
    )


# --- replay: no plugin, the recorded decisions ------------------------------------------------


@dataclass
class ReplayedRemote:
    """
    A remote actuator in a replay (RFC-0018 §3i): no plugin is built, nothing is sent. Each on
    is checked against what the recording decided for the same attempt, in order — refused with
    the recorded reason, or let through to the envelope. An attempt the trace holds nothing for
    is refused (`actuator_state_unknown`): a replay never allows what it cannot show.
    """

    name: str
    outcomes: deque[str | None] = field(default_factory=deque)
    emit: Callable[[str, dict[str, Any]], None] | None = None

    def guard(self, operation: str, called_from: str) -> None:
        reason = self.outcomes.popleft() if self.outcomes else "actuator_state_unknown"
        if reason is None:
            return
        refusal = EnvelopeRefusedError(
            f"{called_from} -> digital.out {self.name!r}",
            f"the recorded session refused this on ({reason}), or holds no decision for it",
            "replay feeds back what was recorded; record the session again to change it",
            reason=reason,
            event={"pin": self.name, "operation": operation, "reason": reason, "state": "replay"},
        )
        if self.emit is not None:
            self.emit("envelope_refused", refusal.event)
        raise refusal

    def start(self, reservation: Reservation, operation: str) -> None:
        return None

    def off(self, cause: str = "command") -> None:
        return None

    def tick(self) -> None:
        return None

    def next_due(self) -> float | None:
        return None

    def close(self) -> None:
        return None


def recorded_outcomes(events: Iterable[Mapping[str, Any]], names: Iterable[str]) -> dict[str, list]:
    """
    For each remote actuator, what its state check decided for every on or pulse the recording
    attempted, in order: None (passed) or the reason it refused. A refusal by the envelope itself
    (it carries no `state`) passed the state check; the envelope decides it again in the replay.
    """
    wanted = set(names)
    outcomes: dict[str, list] = {name: [] for name in wanted}
    for event in events:
        kind, data = event.get("type"), event.get("data", {})
        pin = data.get("pin")
        if pin not in wanted or data.get("operation") in (None, "off"):
            continue
        if kind == "actuator_command" and "cause" not in data:
            outcomes[pin].append(None)
        elif kind == "envelope_refused":
            outcomes[pin].append(data.get("reason") if "state" in data else None)
    return outcomes
