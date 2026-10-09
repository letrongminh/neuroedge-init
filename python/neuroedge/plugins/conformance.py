"""
`neuroedge conformance <distribution>` — the checks of RFC-0016 §3g for the actuator kind, with
the vectors of RFC-0018 §3e (P1). Part of TSK-I2c-12; only `neuroedge.actuators` is implemented.

Typing the distribution's name is the explicit act that loads it (nothing else in it is enabled
anywhere). Every entry point of the distribution is checked on its own; each check is `pass`,
`fail` or `unverifiable` (no `probe()`: the dynamic checks cannot run). The dynamic checks drive
the plugin's `DeviceDouble` through the HAL's own remote-actuator code (`hal.remote`) on a
virtual clock, so what is proven is the plugin *and* the core around it:

* `plugin.loads` — imports, the factory takes one argument, builds an `Actuator` within the limits
  of RFC-0018 §9.5; `plugin.sdk_range` — `sdk_requires` fits this SDK; `plugin.name_pattern`;
* `actuator.level_proven` — the vector of the level it claims (L0 … L3), each able to catch a
  device that lies (a timer or a lease ignored, an on without its duration, an off reported
  without a confirmation);
* `actuator.off_is_idempotent`, `actuator.off_is_unconditional` (a HAL whose ledger refuses
  everything still turns it off), `actuator.builds_without_io` (the factory runs with sockets
  blocked), `actuator.classifies_errors` (a cut link is `NotSent` / `Rejected` / `Ambiguous`, a
  failed read `ReadFailed`), `actuator.receives_no_handles` (the factory gets a config and
  nothing else; the driver holds nothing of the core).

Exit codes (RFC-0016 §3g): 0 when every check passes; 1 when one fails or is unverifiable, or the
distribution has no NeuroEdge entry point ("scanning nothing is never a pass"); 2 when it has a
kind this release does not check yet.
"""

from __future__ import annotations

import contextlib
import importlib
import importlib.metadata as metadata
import socket
import sys
import types
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from .. import __version__
from ..errors import NeuroEdgeError
from ..hal import HardwareAbstractionLayer
from ..hal.envelope import EnvelopeLimits, SafetyEnvelope
from ..hal.remote import OFF_RETRY_MS, OFF_SLACK_MS, MemoryRemoteStore, RemoteBinding
from ..sdk import SDK_VERSION, Ambiguous, Command, NotSent, ReadFailed, Rejected
from . import (
    CODE_NAME,
    GROUPS,
    IMPLEMENTED,
    _editable,
    check_actuator,
    check_factory,
    files_sha256,
    normalise,
    sdk_compatible,
)
from .actuators import SDK_VOCABULARY

__all__ = ["ACTUATOR_CHECKS", "CHECKER_VERSION", "COMMON_CHECKS", "Report", "Result", "run"]

CHECKER_VERSION = "1.0"
COMMON_CHECKS = ("plugin.loads", "plugin.sdk_range", "plugin.name_pattern")
ACTUATOR_CHECKS = (
    "actuator.level_proven",
    "actuator.off_is_idempotent",
    "actuator.off_is_unconditional",
    "actuator.builds_without_io",
    "actuator.classifies_errors",
    "actuator.receives_no_handles",
)
_DYNAMIC = (
    "actuator.level_proven",
    "actuator.off_is_idempotent",
    "actuator.off_is_unconditional",
    "actuator.classifies_errors",
)
NAME = "dut"  # the remote actuator's name on the bench


@dataclass(frozen=True)
class Result:
    entry_point: str
    check: str
    result: str  # pass | fail | unverifiable
    detail: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "entry_point": self.entry_point,
            "check": self.check,
            "result": self.result,
            "detail": self.detail,
        }


@dataclass
class Report:
    distribution: str
    version: str | None = None
    files_sha256: str | None = None
    editable: bool = False
    results: list[Result] = field(default_factory=list)
    unimplemented: list[str] = field(default_factory=list)  # entry points of kinds not checked
    problem: str | None = None

    @property
    def exit_code(self) -> int:
        if self.unimplemented:
            return 2
        if self.problem is not None or not self.results:
            return 1
        return 0 if all(r.result == "pass" for r in self.results) else 1

    @property
    def badge_eligible(self) -> bool:
        """Every check passed, on a non-editable install (RFC-0016 §3g; the badge is TSK-I2c-18)."""
        return self.exit_code == 0 and not self.editable and self.files_sha256 is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "distribution": self.distribution,
            "version": self.version,
            "files_sha256": self.files_sha256,
            "editable": self.editable,
            "sdk": ".".join(map(str, SDK_VERSION)),
            "core": __version__,
            "checker": CHECKER_VERSION,
            "results": [r.as_dict() for r in self.results],
            "unimplemented": list(self.unimplemented),
            "problem": self.problem,
            "badge_eligible": self.badge_eligible,
            "exit_code": self.exit_code,
        }


# --- the bench ---------------------------------------------------------------------------------


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class _Refuse:
    """A token ledger that refuses everything (the off must not need it)."""

    def __call__(self, signature: Any, pin: str, called_from: str) -> None:
        from ..errors import ActionContractViolation

        raise ActionContractViolation(f"bench -> {pin}", "the ledger refuses everything", "-")


class _Spy:
    """Wraps the driver's methods: what the HAL sent, and how often it sent the off."""

    def __init__(self, driver: Any) -> None:
        self.commands: list[Any] = []
        self.offs = 0
        apply, safe_off = driver.apply, driver.safe_off

        def spied_apply(command: Any) -> None:
            self.commands.append(command)
            apply(command)

        def spied_off() -> None:
            self.offs += 1
            safe_off()

        driver.apply, driver.safe_off = spied_apply, spied_off


class Bench:
    """One driver on a HAL of its own: a virtual clock, an envelope of `ceiling_ms`, no board."""

    def __init__(self, driver: Any, double: Any, ceiling_ms: int) -> None:
        self.clock = _Clock()
        self.driver, self.double = driver, double
        self.spy = _Spy(driver)
        limits = EnvelopeLimits(
            window_s=86_400,
            max_on_ms_per_window=10 * ceiling_ms,
            min_interval_ms=0,
            max_continuous_ms=ceiling_ms,
        )
        envelope = SafetyEnvelope({NAME: limits}, clock=self.clock, virtual=True, hal_ended=(NAME,))
        self.hal = HardwareAbstractionLayer(
            target="sim", board=None, authorize=lambda *_: None, envelope=envelope
        )
        self.hal.install_remote(
            [RemoteBinding(NAME, driver, "bench", SDK_VOCABULARY, double)],
            store=MemoryRemoteStore(),
            init_store=True,
        )

    @property
    def remote(self) -> Any:
        return self.hal._remote[NAME]

    @property
    def state(self) -> str:
        return self.hal.remote_state(NAME)

    def pulse(self, ms: int) -> None:
        self.hal.digital_out(NAME, "pulse", ms, signature="bench", called_from="bench")

    def off(self) -> None:
        self.hal.digital_out(NAME, "off", called_from="bench")

    def advance(self, ms: float, *, tick: bool = True) -> None:
        """Time passes; with `tick` the HAL's timers run, without it the runtime is frozen."""
        left = float(ms)
        while left > 0:
            step = min(10.0, left)
            self.clock.now += step
            left -= step
            if tick:
                self.hal.settle_remote()
            else:
                self.double.advance(int(step))


class _Fail(Exception):
    """A vector caught the plugin."""


# --- the checks ----------------------------------------------------------------------------------


def run(distribution: str, kind: str | None = None) -> Report:
    """Check every entry point of `distribution` (only those of `kind`, when given)."""
    name = normalise(distribution)
    report = Report(name)
    dist = next(
        (d for d in metadata.distributions() if normalise(d.metadata["Name"] or "") == name), None
    )
    if dist is None:
        report.problem = f"{name!r} is not installed"
        return report
    report.version = dist.version
    report.editable = _editable(dist)
    entries = [e for e in dist.entry_points if e.group in GROUPS.values()]
    for entry in entries:
        entry_kind = next(k for k, g in GROUPS.items() if g == entry.group)
        if kind is not None and entry_kind != kind:
            continue
        if entry_kind not in IMPLEMENTED:
            report.unimplemented.append(f"{entry_kind}:{entry.name}")
            continue
        report.results += _actuator(entry)
        if report.files_sha256 is None and not report.editable:
            with contextlib.suppress(NeuroEdgeError):
                report.files_sha256 = files_sha256(dist, entry.module, name)
    if kind is not None and kind not in GROUPS:
        report.problem = f"unknown kind {kind!r}; the kinds are {list(GROUPS)}"
    return report


def _actuator(entry: metadata.EntryPoint) -> list[Result]:
    results: dict[str, Result] = {}

    def put(check: str, ok: bool | None, detail: str = "") -> None:
        result = "unverifiable" if ok is None else "pass" if ok else "fail"
        results[check] = Result(entry.name, check, result, detail)

    put(
        "plugin.name_pattern",
        bool(CODE_NAME.fullmatch(entry.name)),
        "" if CODE_NAME.fullmatch(entry.name) else "the name is not [a-z][a-z0-9_]{0,31}",
    )
    try:
        with _no_network():
            factory = entry.load()
        module = sys.modules.get(entry.module) or importlib.import_module(entry.module)
    except Exception as problem:
        detail = f"does not import: {type(problem).__name__}: {problem}"
        for check in COMMON_CHECKS[:2] + ACTUATOR_CHECKS:
            put(check, False, detail)
        return _ordered(results)
    required = getattr(module, "sdk_requires", None)
    put(
        "plugin.sdk_range",
        sdk_compatible(required),
        "" if sdk_compatible(required) else f"sdk_requires {required!r} against {SDK_VERSION}",
    )
    config = dict(getattr(module, "conformance_config", {}) or {})
    attempts: list[str] = []
    try:
        check_factory(factory, entry.name)
        with _no_network(attempts):
            driver = factory(types.MappingProxyType(dict(config)))
        check_actuator(driver, entry.name)
    except NeuroEdgeError as problem:
        put("plugin.loads", False, problem.why)
    except Exception as problem:
        put("plugin.loads", False, f"the factory raised {type(problem).__name__}: {problem}")
    else:
        put("plugin.loads", True)
    if results["plugin.loads"].result != "pass":
        for check in ACTUATOR_CHECKS:
            put(check, False, "the plugin does not load")
        if attempts:
            put("actuator.builds_without_io", False, f"the factory tried {attempts[0]}")
        return _ordered(results)
    put(
        "actuator.builds_without_io",
        not attempts,
        f"the factory tried {attempts[0]}" if attempts else "",
    )
    held = _handles(driver)
    put("actuator.receives_no_handles", not held, f"the driver holds {held}" if held else "")

    def fresh() -> tuple[Any, Any]:
        made = factory(types.MappingProxyType(dict(config)))
        return made, made.probe()

    try:
        fresh()
    except Exception as problem:
        for check in _DYNAMIC:
            put(check, None, f"no device double: probe() raised {type(problem).__name__}")
        return _ordered(results)
    for check, vector in (
        ("actuator.level_proven", _level_proven),
        ("actuator.off_is_idempotent", _off_is_idempotent),
        ("actuator.off_is_unconditional", _off_is_unconditional),
        ("actuator.classifies_errors", _classifies_errors),
    ):
        try:
            vector(fresh)
        except _Fail as caught:
            put(check, False, str(caught))
        except Exception as problem:
            put(check, False, f"{type(problem).__name__}: {problem}")
        else:
            put(check, True)
    return _ordered(results)


def _ordered(results: dict[str, Result]) -> list[Result]:
    return [results[c] for c in (*COMMON_CHECKS, *ACTUATOR_CHECKS) if c in results]


@contextlib.contextmanager
def _no_network(attempts: list[str] | None = None) -> Iterator[None]:
    """Sockets cannot be made while the block runs; every try is recorded in `attempts`."""
    record = attempts if attempts is not None else []

    def blocked(what: str) -> Callable[..., Any]:
        def refuse(*args: Any, **kwargs: Any) -> Any:
            record.append(f"{what}{args[:2]!r}")
            raise OSError(f"conformance: {what} is blocked while the plugin is built")

        return refuse

    saved = (socket.socket, socket.create_connection, socket.getaddrinfo)

    class Blocked(socket.socket):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            blocked("socket.socket")(*args)

    socket.socket = Blocked  # type: ignore[misc]
    socket.create_connection = blocked("socket.create_connection")  # type: ignore[assignment]
    socket.getaddrinfo = blocked("socket.getaddrinfo")  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket, socket.create_connection, socket.getaddrinfo = saved  # type: ignore[misc]


def _handles(driver: Any) -> list[str]:
    """Anything of the core the driver holds (a HAL, a ledger, an envelope…), a few levels deep."""
    found: list[str] = []
    seen: set[int] = set()

    def core(value: Any) -> bool:
        module = getattr(value, "__module__", None) or getattr(type(value), "__module__", "")
        if isinstance(value, types.ModuleType):
            module = value.__name__
        return (
            isinstance(module, str)
            and (module == "neuroedge" or module.startswith("neuroedge."))
            and not module.startswith(("neuroedge.sdk", "neuroedge.errors"))
        )

    def walk(value: Any, path: str, depth: int) -> None:
        if id(value) in seen or depth > 3:
            return
        seen.add(id(value))
        if depth > 0 and core(value):
            found.append(path)
            return
        members = getattr(value, "__dict__", None)
        if isinstance(members, dict) and not isinstance(value, type | types.ModuleType):
            for key, item in members.items():
                walk(item, f"{path}.{key}", depth + 1)
        elif isinstance(value, list | tuple | set | frozenset):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]", depth + 1)
        elif isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{path}[{key!r}]", depth + 1)

    walk(driver, "driver", 0)
    return found


def _ceiling(driver: Any) -> int:
    """D on the bench: well above the tolerance, and three leases at L3 (renewals happen)."""
    tolerance = int(driver.tolerance_ms)
    if driver.safe_off_level == "L3":
        return max(3 * int(driver.max_lease_ms), 2 * tolerance + 1_000)
    return max(2_000, 2 * tolerance + 1_000)


def _level_proven(fresh: Callable[[], tuple[Any, Any]]) -> None:
    driver, double = fresh()
    level = driver.safe_off_level
    {"L0": _l0, "L1": _l1, "L2": _l2, "L3": _l3}[level](driver, double, fresh)


def _l0(driver: Any, double: Any, fresh: Any) -> None:
    bench = Bench(driver, double, _ceiling(driver))
    bench.pulse(500)
    command = bench.spy.commands[-1]
    if command.duration_ms is not None or command.lease_ms is not None:
        raise _Fail("L0: the on carried a duration or a lease")
    bench.off()
    if double.state():
        raise _Fail("L0: the device is still on after an acknowledged off")


def _l1(driver: Any, double: Any, fresh: Any) -> None:
    ceiling = _ceiling(driver)
    bench = Bench(driver, double, ceiling)
    bench.pulse(ceiling)
    bench.advance(ceiling - 20)
    double.cut_link()  # the link breaks just before the deadline
    bench.advance(20 + OFF_SLACK_MS)
    if bench.state == "off" or (bench.state != "uncertain" and double.state()):
        raise _Fail(
            "L1: with the link cut at the deadline the HAL was told the device is off — the "
            "plugin reported an off it could not have had confirmed"
        )
    first = bench.spy.offs
    bench.advance(2 * OFF_RETRY_MS + 20)
    if bench.spy.offs < first + 2:
        raise _Fail("L1: the off is not sent again every OFF_RETRY_MS while unconfirmed")
    double.heal_link()
    bench.advance(OFF_RETRY_MS + 20)
    if double.state() or bench.state != "off":
        raise _Fail("L1: once the link is back the off does not land, or is not confirmed")


def _l2(driver: Any, double: Any, fresh: Any) -> None:
    ceiling = _ceiling(driver)
    tolerance = int(driver.tolerance_ms)
    bench = Bench(driver, double, ceiling)
    bench.pulse(ceiling)
    command = bench.spy.commands[-1]
    if command.duration_ms is None or command.duration_ms > ceiling:  # (a)
        raise _Fail("L2 (a): an on went out without its duration, or longer than D")
    double.cut_link()  # (b) the link breaks right after the device took the command
    bench.advance(ceiling + tolerance)
    if double.state():
        raise _Fail(
            "L2 (b): with the link cut after the on, the device is still on at D + tolerance_ms "
            "— it did not turn itself off (its on carried no duration, or it ignored it)"
        )
    driver, double = fresh()  # (c) the link breaks before the command is delivered
    double.cut_link()
    with contextlib.suppress(NotSent, Rejected, Ambiguous):
        driver.apply(Command("vector-c", "on", duration_ms=ceiling))
    double.heal_link()
    double.advance(ceiling + tolerance)
    if double.state():
        raise _Fail("L2 (c): a command that did not reach the device left it on past D")


def _l3(driver: Any, double: Any, fresh: Any) -> None:
    ceiling = _ceiling(driver)
    tolerance, lease = int(driver.tolerance_ms), int(driver.max_lease_ms)
    bench = Bench(driver, double, ceiling)
    bench.pulse(ceiling)
    if any((c.lease_ms or 0) > lease or c.lease_ms is None for c in bench.spy.commands):  # (c)
        raise _Fail("L3 (c): a command carried no lease, or one above max_lease_ms")
    bench.advance(lease / 3 + 10)  # one renewal
    renewals = [c for c in bench.spy.commands if c.operation == "renew"]
    if not renewals:
        raise _Fail("L3: the HAL did not renew the lease")
    bench.advance(lease + tolerance, tick=False)  # (a) the runtime freezes: no message at all
    if double.state():
        raise _Fail(
            "L3 (a): with the runtime frozen the device is still on lease_ms + tolerance_ms after "
            "the last renewal it took — it ignores its lease"
        )
    driver, double = fresh()  # (b) duplicated and reordered renewals
    bench = Bench(driver, double, ceiling)
    bench.pulse(ceiling)
    start = bench.clock.now
    bench.advance(ceiling - 10)
    renewals = [c for c in bench.spy.commands if c.operation == "renew"]
    for late in (renewals[-1], renewals[0]) if renewals else ():
        with contextlib.suppress(NotSent, Rejected, Ambiguous):
            driver.apply(late)  # a duplicate of the newest, then the oldest, delivered late
    bench.advance(start + ceiling + tolerance - bench.clock.now + 10)
    if double.state():
        raise _Fail(
            "L3 (b): a duplicated or late renewal kept the device on past start + D + tolerance_ms"
        )


def _on_command(driver: Any) -> Any:
    level = driver.safe_off_level
    return Command(
        "idempotent",
        "on",
        duration_ms=1_000 if level == "L2" else None,
        lease_ms=min(1_000, int(driver.max_lease_ms)) if level == "L3" else None,
    )


def _off_is_idempotent(fresh: Callable[[], tuple[Any, Any]]) -> None:
    driver, double = fresh()
    try:
        driver.safe_off()
        driver.safe_off()  # an off device stays off, without an error
        driver.apply(_on_command(driver))
        driver.safe_off()
        driver.safe_off()
    except (NotSent, Rejected, Ambiguous) as problem:
        raise _Fail(f"safe_off() twice raised {type(problem).__name__}: {problem}") from None
    if double.state():
        raise _Fail("the device is on after two offs")


def _off_is_unconditional(fresh: Callable[[], tuple[Any, Any]]) -> None:
    driver, double = fresh()
    bench = Bench(driver, double, _ceiling(driver))
    bench.pulse(500)
    bench.hal.authorize = _Refuse()  # from here the ledger refuses everything
    bench.off()
    if double.state():
        raise _Fail(
            "the off of a HAL whose token ledger refuses everything did not turn the device off "
            "(the off needs no token and no envelope)"
        )


def _classifies_errors(fresh: Callable[[], tuple[Any, Any]]) -> None:
    driver, double = fresh()
    double.cut_link()
    sdk = (NotSent, Rejected, Ambiguous)
    for what, call in (
        ("apply()", lambda: driver.apply(_on_command(driver))),
        ("safe_off()", driver.safe_off),
    ):
        try:
            call()
        except sdk:
            continue
        except Exception as problem:
            raise _Fail(
                f"{what} with the link cut raised {type(problem).__name__}, not NotSent, "
                "Rejected or Ambiguous"
            ) from None
        raise _Fail(f"{what} returned as if delivered with the link cut")
    if driver.readback != "none":
        try:
            driver.read_state()
        except ReadFailed:
            return
        except Exception as problem:
            raise _Fail(
                f"read_state() with the link cut raised {type(problem).__name__}, not ReadFailed"
            ) from None
        raise _Fail("read_state() returned a state with the link cut")
