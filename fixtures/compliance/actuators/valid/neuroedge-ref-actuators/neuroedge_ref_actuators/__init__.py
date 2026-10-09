"""
The reference `neuroedge.actuators` plugin (RFC-0018 §3c–§3e).

One driver, four entry points — `ref_l0` … `ref_l3` — each declaring the level its device keeps:

* L0, L1: `on` carries no duration; the device stays on until it is told `off`.
* L2: every `on` carries `duration_ms`; the device turns itself off after it.
* L3: `on` and `renew` carry `lease_ms`; the device turns itself off when the lease runs out.

The driver talks a toy protocol, one JSON object per line over TCP (`host`, `port` in the
config), to a device that does not exist. The factory does no I/O: the connection is opened by
the first command. `probe()` swaps that transport for `RefDouble`, the in-memory device on a
virtual clock, so the conformance checks and the `sim` target run the driver's own code against
it. Only `neuroedge.sdk` is imported.

Config keys (all optional): `host`, `port`, `readback` ("poll", "push" or "none"),
`tolerance_ms`, `command_timeout_ms`, `max_lease_ms` (L3), `token_env` (the name of the variable
that holds the device's token: read when the first command is sent, never by the factory).
"""

from __future__ import annotations

import json
import os
import socket
from collections.abc import Callable, Mapping
from typing import Any

from neuroedge.sdk import Ambiguous, Command, NotSent, ReadFailed, Rejected

sdk_requires = (1, 0)
conformance_config: Mapping[str, Any] = {}

_KEYS = (
    "host",
    "port",
    "readback",
    "tolerance_ms",
    "command_timeout_ms",
    "max_lease_ms",
    "token_env",
)


class LinkDown(Exception):
    """The double's link is cut: nothing reaches the device."""


class ReplyLost(Exception):
    """The device took the message, and its answer never came back."""


class RefDouble:
    """
    The device, in memory, on a virtual clock (`advance`). It keeps its promise: a duration or a
    lease turns it off on time; a renewal older than the newest one it took is ignored.
    `honors_timer` / `honors_lease` off make a device that lies (the counter-examples).
    """

    def __init__(self, *, honors_timer: bool = True, honors_lease: bool = True) -> None:
        self.now = 0
        self.on = False
        self.off_at: int | None = None
        self.link = True
        self.newest = -1  # the sequence number of the newest on or renewal taken
        self.honors_timer = honors_timer
        self.honors_lease = honors_lease
        self.received: list[dict[str, Any]] = []  # every message the device took, for tests
        self._drop_reply = False
        self._reject = False
        self._listeners: list[Callable[[bool | None], None]] = []

    # -- the DeviceDouble protocol -----------------------------------------------------------
    def state(self) -> bool:
        return self.on

    def cut_link(self) -> None:
        self.link = False
        self._tell(None)

    def heal_link(self) -> None:
        self.link = True
        self._tell(self.on)

    def advance(self, ms: int) -> None:
        self.now += max(0, int(ms))
        if self.on and self.off_at is not None and self.now >= self.off_at:
            self._set(False)

    # -- what a test may also do to the device -----------------------------------------------
    def drop_next_reply(self) -> None:
        """The next message reaches the device, and its answer is lost (an ambiguous send)."""
        self._drop_reply = True

    def reject_next(self) -> None:
        """The next message is refused by the device, which does nothing."""
        self._reject = True

    def force(self, on: bool) -> None:
        """Somebody else (a wall switch, a person) turns the device on or off."""
        self.off_at = None
        self._set(on)

    def subscribe(self, listener: Callable[[bool | None], None]) -> None:
        self._listeners.append(listener)
        listener(self.on if self.link else None)

    # -- the device side of the protocol -----------------------------------------------------
    def receive(self, message: dict[str, Any]) -> dict[str, Any]:
        if not self.link:
            raise LinkDown("the link to the device is cut")
        if self._reject:
            self._reject = False
            return {"error": "refused by the device"}
        self.received.append(dict(message))
        op = message.get("op")
        if op == "on":
            self.newest = max(self.newest, int(message.get("seq", 0)))
            self.off_at = None
            if message.get("duration_ms") is not None and self.honors_timer:
                self.off_at = self.now + int(message["duration_ms"])
            if message.get("lease_ms") is not None and self.honors_lease:
                self.off_at = self.now + int(message["lease_ms"])
            self._set(True)
        elif op == "renew":
            seq = int(message.get("seq", 0))
            if seq > self.newest and self.on:
                self.newest = seq
                if self.honors_lease:
                    self.off_at = self.now + int(message["lease_ms"])
        elif op == "off":
            self.off_at = None
            self._set(False)
        reply: dict[str, Any] = {"ok": True}
        if op == "state":
            reply = {"on": self.on, "age_ms": 0}
        if self._drop_reply:
            self._drop_reply = False
            raise ReplyLost("the answer was lost")
        return reply

    def _set(self, on: bool) -> None:
        changed = on != self.on
        self.on = on
        if changed and self.link:
            self._tell(on)

    def _tell(self, value: bool | None) -> None:
        for listener in self._listeners:
            listener(value)


class _SocketTransport:
    """One JSON line out, one back, over TCP; opened on first use (never by the factory)."""

    def __init__(self, host: str, port: int, timeout_ms: int, token_env: str | None) -> None:
        self.host, self.port, self.timeout = host, port, timeout_ms / 1000.0
        self.token_env = token_env

    def send(self, message: dict[str, Any]) -> dict[str, Any]:
        if self.token_env is not None:
            token = os.environ.get(self.token_env)
            if not token:
                raise NotSent(f"the variable {self.token_env} holding the device token is unset")
            message = {**message, "token": token}
        try:
            connection = socket.create_connection((self.host, self.port), timeout=self.timeout)
        except OSError as problem:
            raise NotSent(f"cannot reach {self.host}:{self.port}: {problem}") from problem
        with connection:
            try:
                connection.sendall((json.dumps(message) + "\n").encode())
            except OSError as problem:
                raise Ambiguous(f"the link broke while sending: {problem}") from problem
            try:
                line = connection.makefile().readline()
            except OSError as problem:
                raise Ambiguous(f"no answer within the timeout: {problem}") from problem
        if not line:
            raise Ambiguous("the device closed the link without answering")
        return json.loads(line)

    def subscribe(self, listener: Callable[[bool | None], None]) -> None:
        raise ReadFailed("push read-back needs the double, or a device that pushes; none here")


class _DoubleTransport:
    """The same messages, handed to the double instead of a socket."""

    def __init__(self, double: RefDouble) -> None:
        self.double = double

    def send(self, message: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.double.receive(message)
        except LinkDown as problem:
            raise NotSent(str(problem)) from problem
        except ReplyLost as problem:
            raise Ambiguous(str(problem)) from problem

    def subscribe(self, listener: Callable[[bool | None], None]) -> None:
        self.double.subscribe(listener)


def _number(config: Mapping[str, Any], key: str, default: int, low: int) -> int:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < low:
        raise ValueError(f"{key} must be a whole number of at least {low}")
    return value


class RefActuator:
    """The driver: `Command`s become protocol messages; the device's answers become errors."""

    def __init__(self, level: str, config: Mapping[str, Any]) -> None:
        unknown = sorted(set(config) - set(_KEYS))
        if unknown:
            raise ValueError(f"unknown config keys {unknown}; the plugin takes {list(_KEYS)}")
        readback = config.get("readback", "poll")
        if readback not in ("push", "poll", "none"):
            raise ValueError("readback must be push, poll or none")
        host = config.get("host", "127.0.0.1")
        if not isinstance(host, str) or not host:
            raise ValueError("host must be a host name")
        token_env = config.get("token_env")
        if token_env is not None and not isinstance(token_env, str):
            raise ValueError("token_env names an environment variable")
        self.safe_off_level = level
        self.readback = readback
        self.tolerance_ms = _number(config, "tolerance_ms", 50, 0)
        self.command_timeout_ms = _number(config, "command_timeout_ms", 1000, 1)
        self.max_lease_ms = _number(config, "max_lease_ms", 1000, 1) if level == "L3" else None
        self._transport: Any = _SocketTransport(
            host, _number(config, "port", 9, 1), self.command_timeout_ms, token_env
        )
        self._seq = 0
        self._seqs: dict[str, int] = {}  # command id -> the sequence number it was sent with
        self._pushed: bool | None = None
        self._subscribed = False

    def _sequence(self, command_id: str) -> int:
        # A command sent again (same id) keeps its number, so the device can tell a duplicate.
        if command_id not in self._seqs:
            self._seq += 1
            self._seqs[command_id] = self._seq
        return self._seqs[command_id]

    def _send(self, message: dict[str, Any]) -> dict[str, Any]:
        reply = self._transport.send(message)
        if "error" in reply:
            raise Rejected(str(reply["error"]))
        return reply

    def message_for(self, command: Command) -> dict[str, Any]:
        message: dict[str, Any] = {"op": command.operation, "seq": self._sequence(command.id)}
        if self.safe_off_level == "L2":
            if command.duration_ms is None:
                raise Rejected("an L2 command carries its duration")
            message["duration_ms"] = command.duration_ms
        if self.safe_off_level == "L3":
            if command.lease_ms is None or command.lease_ms > (self.max_lease_ms or 0):
                raise Rejected("an L3 command carries a lease within max_lease_ms")
            message["lease_ms"] = command.lease_ms
        if command.operation == "renew" and self.safe_off_level != "L3":
            raise Rejected("only an L3 device renews a lease")
        return message

    def apply(self, command: Command) -> None:
        self._send(self.message_for(command))

    def safe_off(self) -> None:
        self._send({"op": "off"})

    def read_state(self) -> tuple[bool, int]:
        if self.readback == "none":
            raise ReadFailed("this device is not read back")
        if self.readback == "push":
            if not self._subscribed:
                self._subscribed = True
                self._transport.subscribe(self._on_push)
            if self._pushed is None:
                raise ReadFailed("no state pushed since the link came up")
            return self._pushed, 0
        try:
            reply = self._send({"op": "state"})
        except (NotSent, Ambiguous, Rejected) as problem:
            raise ReadFailed(str(problem)) from problem
        return bool(reply["on"]), int(reply.get("age_ms", 0))

    def _on_push(self, value: bool | None) -> None:
        self._pushed = value

    def probe(self) -> RefDouble:
        double = self.make_double()
        self._transport = _DoubleTransport(double)
        return double

    def make_double(self) -> RefDouble:
        return RefDouble()


def l0(config: Mapping[str, Any]) -> RefActuator:
    return RefActuator("L0", config)


def l1(config: Mapping[str, Any]) -> RefActuator:
    return RefActuator("L1", config)


def l2(config: Mapping[str, Any]) -> RefActuator:
    return RefActuator("L2", config)


def l3(config: Mapping[str, Any]) -> RefActuator:
    return RefActuator("L3", config)
