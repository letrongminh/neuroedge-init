"""
One flaw per entry point, each built on the reference driver (`neuroedge_ref_actuators`). The
check of `neuroedge conformance` that must catch it is in
fixtures/compliance/actuators/expected_results.yaml.
"""

from __future__ import annotations

import socket
from collections.abc import Mapping
from typing import Any

import neuroedge.hal
from neuroedge.sdk import Command, NotSent, Rejected
from neuroedge_ref_actuators import RefActuator, RefDouble

sdk_requires = (1, 0)
conformance_config: Mapping[str, Any] = {}


class _IgnoresTimer(RefActuator):
    def make_double(self) -> RefDouble:
        return RefDouble(honors_timer=False)  # the device keeps running past its duration


class _IgnoresLease(RefActuator):
    def make_double(self) -> RefDouble:
        return RefDouble(honors_lease=False)  # the device keeps running past its lease


class _DropsDuration(RefActuator):
    def message_for(self, command: Command) -> dict[str, Any]:
        message = super().message_for(command)
        message.pop("duration_ms", None)  # claims L2, sends an on with no duration
        return message


class _ReportsOffUnconfirmed(RefActuator):
    """Says the device is off whenever it cannot tell: the off "succeeds" with the link cut."""

    def safe_off(self) -> None:
        try:
            super().safe_off()
        except NotSent:
            pass

    def read_state(self) -> tuple[bool, int]:
        try:
            return super().read_state()
        except Exception:
            return False, 0


class _OffNeedsToken(RefActuator):
    def safe_off(self, token: Any = None) -> None:  # type: ignore[override]
        if token is None:
            raise Rejected("this driver sends an off only with a verdict token")
        super().safe_off()


class _OffNotIdempotent(RefActuator):
    def __init__(self, level: str, config: Mapping[str, Any]) -> None:
        super().__init__(level, config)
        self._sent_off = False

    def apply(self, command: Command) -> None:
        super().apply(command)
        self._sent_off = False

    def safe_off(self) -> None:
        if self._sent_off:
            raise Rejected("the device is off already")
        super().safe_off()
        self._sent_off = True


class _RawErrors(RefActuator):
    def _send(self, message: dict[str, Any]) -> dict[str, Any]:
        try:
            return super()._send(message)
        except NotSent as problem:
            raise ConnectionError(str(problem)) from None  # not one of the SDK's errors


class _HoldsHal(RefActuator):
    def __init__(self, level: str, config: Mapping[str, Any]) -> None:
        super().__init__(level, config)
        self.hal = neuroedge.hal.HardwareAbstractionLayer  # a handle on the core


class _WrongShape:
    safe_off_level = "L1"
    readback = "poll"
    tolerance_ms = 50
    command_timeout_ms = 1000
    max_lease_ms = None

    def apply(self, command: Command) -> None:
        return None

    def safe_off(self) -> None:
        return None

    def probe(self) -> RefDouble:
        return RefDouble()  # and no read_state()


class _NoProbe(RefActuator):
    def probe(self) -> RefDouble:
        raise NotImplementedError("this driver has no double")


def ignores_timer(config: Mapping[str, Any]) -> RefActuator:
    return _IgnoresTimer("L2", config)


def ignores_lease(config: Mapping[str, Any]) -> RefActuator:
    return _IgnoresLease("L3", config)


def l2_without_duration(config: Mapping[str, Any]) -> RefActuator:
    return _DropsDuration("L2", config)


def reports_off_unconfirmed(config: Mapping[str, Any]) -> RefActuator:
    return _ReportsOffUnconfirmed("L1", config)


def off_needs_token(config: Mapping[str, Any]) -> RefActuator:
    return _OffNeedsToken("L1", config)


def off_not_idempotent(config: Mapping[str, Any]) -> RefActuator:
    return _OffNotIdempotent("L1", config)


def io_at_build(config: Mapping[str, Any]) -> RefActuator:
    try:  # "just checking the device is there" — I/O in the factory
        socket.create_connection(("127.0.0.1", 9), timeout=0.05).close()
    except OSError:
        pass
    return RefActuator("L1", config)


def raw_errors(config: Mapping[str, Any]) -> RefActuator:
    return _RawErrors("L1", config)


def holds_hal(config: Mapping[str, Any]) -> RefActuator:
    return _HoldsHal("L1", config)


def wrong_shape(config: Mapping[str, Any]) -> Any:
    return _WrongShape()


def named_badly(config: Mapping[str, Any]) -> RefActuator:
    return RefActuator("L1", config)  # nothing wrong but the entry point's name


def no_probe(config: Mapping[str, Any]) -> RefActuator:
    return _NoProbe("L1", config)
