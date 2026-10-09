"""
`neuroedge.sdk` — what an extension may touch, and nothing else (RFC-0016 §3c, §3e).

A bridge exchanges two data types with the core. A `ToolRequest` is
`tool-call.v1#/$defs/request` — it has **no** `source`: the core stamps the source (RFC-0017
§3b.3), so a bridge cannot say where its call came from. An `Outcome` is data only: the status
and the `ToolResult.content()` of the call, never the value an action body returned.

A remote actuator plugin (entry point group `neuroedge.actuators`, RFC-0018 §3c) implements the
`Actuator` Protocol: the HAL is its only caller, `apply` comes only after the HAL's admission
(state check → envelope → token → record), `safe_off` needs neither a token nor the envelope.
The plugin receives a `Command` and raises one of the four `ActuatorError`s; it never receives a
HAL, a token ledger or an envelope. `probe()` returns its `DeviceDouble`, the in-memory device
the conformance checks and the `sim` target drive through the plugin's own code.

No HAL name, no `Guard`, no `Conversation` and no name of `neuroedge.__all__` is exported here.

`SDK_VERSION` is the SDK's own SemVer pair `(MAJOR, MINOR)`, independent of the package
version: a plugin that asks for `(1, 0)` works on every SDK 1.x (docs/spec/extension_sdk.md).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from ..errors import ToolCallError

SDK_VERSION = (1, 0)

__all__ = [
    "SDK_VERSION",
    "Actuator",
    "ActuatorError",
    "Ambiguous",
    "Command",
    "DeviceDouble",
    "NotSent",
    "Outcome",
    "ReadFailed",
    "Rejected",
    "ToolRequest",
]


@dataclass(frozen=True)
class ToolRequest:
    """What a bridge asks for: a tool name, its arguments and, optionally, its own call id."""

    name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    id: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not isinstance(self.id, str):
            raise ToolCallError(
                where="ToolRequest",
                why="`name` and `id` must be strings",
                how="build it as ToolRequest('tool_name', {'argument': value})",
            )
        if not isinstance(self.arguments, Mapping):
            raise ToolCallError(
                where=f"ToolRequest({self.name!r})",
                why=f"`arguments` must be a mapping, not {type(self.arguments).__name__}",
                how="pass the arguments as a dict: ToolRequest('tool_name', {'argument': value})",
            )


@dataclass(frozen=True)
class Outcome:
    """
    The core's answer: `status` is "ALLOW", "BLOCK" or "REJECTED"; `content` is the
    `tool-result.v1` document the caller is told (reason, failed criterion, fallback…).
    """

    status: str
    content: Mapping[str, Any]


# --- remote actuators (RFC-0018 §3c) -----------------------------------------------------------


class ActuatorError(Exception):
    """
    A command to a remote device did not go as asked. The plugin says which way, the HAL never
    guesses (RFC-0018 §3g). Not a `NeuroEdgeError`: the HAL turns it into its own record.
    """


class NotSent(ActuatorError):
    """The command certainly did not reach the device (no connection, refused before sending)."""


class Rejected(ActuatorError):
    """The hub or device answered and explicitly refused the command."""


class Ambiguous(ActuatorError):
    """
    The command may or may not have reached the device: a timeout, or the link broke after it
    was sent. The HAL keeps the reservation and treats the device as possibly on.
    """


class ReadFailed(ActuatorError):
    """The state of the device could not be read back."""


@dataclass(frozen=True)
class Command:
    """
    What the HAL asks a plugin to send, after the HAL admitted it. `operation` is ``"on"`` or
    ``"renew"`` (a lease extension, level L3); the command toward the safe state is
    `Actuator.safe_off()`, not a `Command`. `duration_ms` is always given at level L2 (the device
    turns itself off after it), `lease_ms` at level L3; both are intervals, never instants.
    `id` is unique per command, so a device can tell a duplicate or a late renewal.
    """

    id: str
    operation: Literal["on", "renew"]
    duration_ms: int | None = None
    lease_ms: int | None = None


@runtime_checkable
class DeviceDouble(Protocol):
    """
    The in-memory device a plugin's `probe()` returns, on a virtual clock: the plugin's
    `apply`, `safe_off` and `read_state` reach it through the plugin's own code. `state()` is
    whether the device is on; `cut_link()` and `heal_link()` break and restore the link between
    the plugin and the device; `advance(ms)` moves the device's clock (its timers and leases).
    """

    def state(self) -> bool: ...

    def cut_link(self) -> None: ...

    def heal_link(self) -> None: ...

    def advance(self, ms: int) -> None: ...


@runtime_checkable
class Actuator(Protocol):
    """
    A remote actuator driver (RFC-0018 §3c), built by ``factory(config: Mapping[str, Any])`` —
    called once, with no I/O. Every method is synchronous, blocks at most `command_timeout_ms`,
    and may be called from the HAL's timer thread.

    * `safe_off_level` — the highest level proven for this config: ``"L0"`` (none), ``"L1"``
      (the host's timer), ``"L2"`` (a timer in the device: every `on` carries `duration_ms`),
      ``"L3"`` (a lease in the device: `lease_ms` and `renew`).
    * `readback` — how the state is read back: ``"push"``, ``"poll"`` or ``"none"``.
    * `tolerance_ms` (≥ 0, at most 2000) — the most the device turns off after its deadline;
      `command_timeout_ms` (> 0, at most 5000); `max_lease_ms` (L3 only, else None).
    * `apply(command)` — returning means the hub or device *received* it, not that it is on.
      Raises `NotSent`, `Rejected` or `Ambiguous`.
    * `safe_off()` — the command toward the safe state: no token, no envelope, repeatable (an
      off device stays off without an error). Raises the same three.
    * `read_state()` — ``(is_on, observed_age_ms)``; the age only adds to the receiver's own
      mark. Never called when `readback` is ``"none"``. Raises `ReadFailed`.
    * `probe()` — the plugin's `DeviceDouble`; from then on this instance drives the double.
    """

    safe_off_level: Literal["L0", "L1", "L2", "L3"]
    readback: Literal["push", "poll", "none"]
    tolerance_ms: int
    command_timeout_ms: int
    max_lease_ms: int | None

    def apply(self, command: Command) -> None: ...

    def safe_off(self) -> None: ...

    def read_state(self) -> tuple[bool, int]: ...

    def probe(self) -> DeviceDouble: ...
