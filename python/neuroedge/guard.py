"""
`neuroedge.guard` — the safety core without an agent (RFC-0016 §3b, TSK-I2c-07).

Any program — an MCP proxy, a bridge, a ROS node — gets gate → token → envelope → trace
through `Guard`, without `agent.toml`, `@action` or `SimSession`:

    guard = Guard.load("guard.toml")
    async with guard:                           # leaving releases the pins, like SimSession.close()
        lamp = guard.dispatcher("ros_node")     # the source is "bridge:ros_node", never stated
        outcome = await lamp.dispatch(ToolRequest("lamp_on", {"seconds": 5}))

There is exactly one road to a pin, and it is the one every other caller takes: the `Guard`
builds a `Conversation` of its own (with its own action registry, never the global one of
`@action`) and calls the real `dispatch()` — schema check, `c.do()`, gate, one-use token, the
HAL's envelope. What this module adds is only data: a `Tool` is an `ActionSpec` declared by a
table instead of a decorator, and its body is either a Python callable (`run`) or the
declarative `drive` of `guard.toml`.

What it deliberately does not do: no sandbox and no network block (it guards the road that
goes through it), no fail-open switch, no `ResolvedGate` built by hand (a gate is loaded from
a file or a `neuroedge://` URI and resolved at load), no confirmation by a person (an `ask`
shows up as a BLOCK with its question in `outcome.content`), and no defence against code in
the same process (`docs/spec/threat_model.md` §3).

Not public through `neuroedge.__all__` (RFC-0016 §9.2): `from neuroedge.guard import Guard`.
"""

from __future__ import annotations

import asyncio
import inspect
import re
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import __version__
from .actions import Conversation
from .actions.spec import ActionSpec, Requirement
from .actions.tools import ToolCall, ToolSet, dispatch, valid_source
from .engine import ActionContractEngine, EventLog, GateRegistry, ResolvedGate
from .errors import AgentManifestError, BoardCapabilityError, ToolCallError
from .hal import digital
from .hal.board import BoardProfile, load_board_by_id
from .models.providers.common import NAME, refuse_unknown, secret_fields
from .sdk import Outcome, ToolRequest
from .sim.hal_build import build_hal, release_hal
from .trace import validate_trace

__all__ = ["Dispatcher", "Drive", "Guard", "GuardConfig", "Tool", "load_config"]

_TOOL = re.compile(r"[a-z][a-z0-9_]{0,63}")
_TYPES: dict[str, type] = {"string": str, "integer": int, "number": float, "boolean": bool}
_OPERATIONS = ("on", "off", "pulse")
_RESERVED_FACTS = ("call_source", "call_channel")
_TARGETS = ("sim", "linux")
NO_BOARD = "none"


# --- the data a Guard is built from ---------------------------------------------------------


@dataclass(frozen=True)
class Drive:
    """One step of a declarative body: `digital.out(pin).<operation>(…)` under the token."""

    pin: str
    operation: str
    seconds_from: str | None = None


@dataclass(frozen=True)
class Tool:
    """
    One tool, declared by data (the counterpart of an `@action`).

    `gate` is a `neuroedge://` URI or a gate file; `requires` are `digital.out:<pin>` entries;
    `parameters` maps a parameter name to ``{"type": …, "default": …}`` — a parameter not
    declared here is REJECTED. The body is `run` (a Python callable, sync or async, called with
    the validated arguments, defaults applied) or `drive` (declarative), never both; neither is
    a verdict only: ALLOW and nothing moves.
    """

    name: str
    gate: str
    requires: tuple[str, ...] = ()
    parameters: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    drive: tuple[Drive, ...] = ()
    run: Callable[..., Any] | None = None

    def __post_init__(self) -> None:
        where = f"Tool({self.name!r})"
        if not isinstance(self.name, str) or not _TOOL.fullmatch(self.name):
            raise _manifest(where, f"{self.name!r} is not a tool name", "use [a-z][a-z0-9_]{0,63}")
        if not isinstance(self.gate, str) or not self.gate:
            raise _manifest(where, "`gate` must name a gate file or neuroedge:// URI", "set gate")
        object.__setattr__(self, "requires", tuple(self.requires))
        object.__setattr__(self, "drive", tuple(self.drive))
        pins = []
        for entry in self.requires:
            parsed = Requirement.parse(str(entry), where) if isinstance(entry, str) else None
            if parsed is None or parsed.primitive != "digital.out" or not parsed.name:
                raise _manifest(
                    f"{where} requires",
                    f"{entry!r}: a Guard drives named `digital.out:<pin>` pins only for now",
                    'write requires = ["digital.out:<pin>"]',
                )
            pins.append(parsed.name)
        for index, step in enumerate(self.drive):
            self._check_step(f"{where} drive[{index}]", step, pins)
        if self.run is not None and self.drive:
            raise _manifest(where, "both `run` and `drive` are given", "give one body, or none")
        if self.run is not None and not callable(self.run):
            raise _manifest(where, "`run` is not callable", "pass a function")
        self._check_parameters(where)
        if self.run is not None:
            try:
                inspect.signature(self.run).bind(**dict.fromkeys(self.parameters))
            except TypeError as problem:
                raise _manifest(
                    where,
                    f"`run` does not accept the declared parameters {sorted(self.parameters)}: "
                    f"{problem}",
                    "make run take exactly the parameters the tool declares",
                ) from None

    def _check_parameters(self, where: str) -> None:
        for name, schema in self.parameters.items():
            if not isinstance(name, str) or not _TOOL.fullmatch(name):
                raise _manifest(f"{where} parameters", f"{name!r} is not a parameter name", "x")
            if not isinstance(schema, Mapping):
                raise _manifest(f"{where} parameters.{name}", "must be a table", "add a `type`")
            refuse_unknown(
                schema,
                f"{where} parameters.{name}",
                f"tools.{self.name}.parameters.{name}",
                ("type", "default", "description"),
                "describe a parameter with type, default and description only; limits belong "
                "to the gate's `arguments`",
            )
            kind = schema.get("type")
            if kind not in _TYPES:
                raise _manifest(
                    f"{where} parameters.{name}",
                    f"`type` must be one of {list(_TYPES)}",
                    f'write type = "{next(iter(_TYPES))}"',
                )
            default = schema.get("default")
            if "default" in schema and not _fits(default, kind):
                raise _manifest(
                    f"{where} parameters.{name}",
                    f"the default is not of type {kind}",
                    "give a default of the declared type",
                )

    def _check_step(self, where: str, step: Any, pins: list[str]) -> None:
        if not isinstance(step, Drive):
            raise _manifest(where, "a drive step is a Drive(pin, operation, seconds_from)", "x")
        if step.operation not in _OPERATIONS:
            raise _manifest(
                where,
                f"operation {step.operation!r} is not one of {list(_OPERATIONS)}",
                "use on, off or pulse",
            )
        if step.pin not in pins:
            raise _manifest(
                where,
                f"pin {step.pin!r} is not in `requires`; the token grants only what is declared",
                f'add "digital.out:{step.pin}" to requires',
            )
        if step.operation == "pulse":
            kind = (self.parameters.get(step.seconds_from or "") or {}).get("type")
            if kind not in ("integer", "number"):
                raise _manifest(
                    where,
                    "a pulse takes its length from `seconds_from`, a declared integer or "
                    "number parameter",
                    'write seconds_from = "<parameter>" and declare it with type = "integer"',
                )
        elif step.seconds_from is not None:
            raise _manifest(where, "`seconds_from` belongs to pulse only", "remove it")

    @property
    def pins(self) -> tuple[str, ...]:
        return tuple(Requirement.parse(r, self.name).name or "" for r in self.requires)


def _fits(value: Any, kind: str) -> bool:
    if kind == "boolean":
        return isinstance(value, bool)
    if isinstance(value, bool):
        return False
    if kind == "integer":
        return isinstance(value, int)
    if kind == "number":
        return isinstance(value, int | float)
    return isinstance(value, str)


def _manifest(where: str, why: str, how: str) -> AgentManifestError:
    return AgentManifestError(where=where, why=why, how=how)


@dataclass(frozen=True)
class GuardConfig:
    """`guard.toml`, read and checked: everything but the gates (those resolve at load)."""

    name: str
    tools: tuple[Tool, ...]
    board: str | None = None
    registry_root: Path | None = None
    base: Path | None = None  # relative gate files are found next to guard.toml
    source: str = "<guard>"


# --- guard.toml -----------------------------------------------------------------------------

_LATER = {
    "external": "TSK-I2c-09 (external facts, RFC-0014)",
    "actuators": "TSK-I2c-16 (remote actuators, RFC-0018)",
}


def load_config(path: str | Path) -> GuardConfig:
    """
    `guard.toml` as a `GuardConfig`. An unknown key, a field named like a secret, a table that a
    later task implements (`[external]`, `[actuators]`, a non-empty `[plugins]`, a second
    registry root, a board that is not an id) are all `AgentManifestError` (NE3002), three
    parts, naming the task when one is coming.
    """
    path = Path(path)
    where = str(path)
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as problem:
        raise _manifest(where, f"cannot read guard.toml: {problem}", "fix the file") from None
    secrets = secret_fields(document)
    if secrets:
        # Never repeat the value: it may be a live key.
        raise _manifest(
            f"{where} {secrets[0]}",
            "a secret must never be written in guard.toml — the file is committed and shared",
            f"delete `{secrets[0]}` and name an environment variable (`*_env`) instead",
        )
    for table, task in _LATER.items():
        if table in document:
            raise _manifest(
                f"{where} [{table}]",
                f"[{table}] is not implemented yet: {task}",
                f"remove [{table}] until that task lands",
            )
    refuse_unknown(document, where, "guard.toml", ("guard", "registry", "tools", "plugins"), "x")
    head = _table(document.get("guard"), where, "guard")
    refuse_unknown(head, where, "guard", ("name", "board"), "a [guard] has name and board")
    name = head.get("name")
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise _manifest(
            f"{where} [guard] name",
            "`name` is required: letters, digits, `_`, `.`, `-`",
            'write name = "door-proxy"',
        )
    board = head.get("board")
    if board is not None and (
        not isinstance(board, str) or not NAME.fullmatch(board) or board.startswith("pkg:")
    ):
        raise _manifest(
            f"{where} [guard] board",
            "only a board id is accepted today; a path or `pkg:` reference arrives with TSK-I2c-08",
            'write board = "<id of a board in boards/>"',
        )
    _plugins(_table(document.get("plugins"), where, "plugins"), where)
    root = _registry(_table(document.get("registry"), where, "registry"), where, path.parent)
    tools_table = _table(document.get("tools"), where, "tools")
    tools = tuple(_tool(name_, spec, where) for name_, spec in tools_table.items())
    return GuardConfig(
        name=name,
        tools=tools,
        board=board,
        registry_root=root,
        base=path.parent,
        source=where,
    )


def _table(value: Any, where: str, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise _manifest(f"{where} [{name}]", f"[{name}] must be a table", f"write [{name}]")
    return value


def _plugins(table: dict[str, Any], where: str) -> None:
    refuse_unknown(table, where, "plugins", ("enable", "config"), "x")
    if table.get("enable") or table.get("config"):
        raise _manifest(
            f"{where} [plugins]",
            "plugins are not implemented yet: TSK-I2c-11 (the loader, RFC-0016 §3d); a Guard "
            "that asked for one would run without it",
            "leave [plugins] empty until TSK-I2c-11 lands",
        )


def _registry(table: dict[str, Any], where: str, base: Path) -> Path | None:
    refuse_unknown(table, where, "registry", ("roots",), "a [registry] has roots only")
    roots = table.get("roots", [])
    if not isinstance(roots, list) or not all(isinstance(r, str) and r for r in roots):
        raise _manifest(f"{where} [registry] roots", "`roots` is a list of directories", "x")
    if len(roots) > 1:
        raise _manifest(
            f"{where} [registry] roots",
            f"{len(roots)} roots: `GateRegistry` searches one directory today; several arrive "
            "with TSK-I2c-08",
            "list one root",
        )
    return (base / roots[0]) if roots else None


def _tool(name: str, spec: Any, where: str) -> Tool:
    here = f"{where} [tools.{name}]"
    if not isinstance(spec, dict):
        raise _manifest(here, "a tool is a table", f"write [tools.{name}]")
    refuse_unknown(spec, here, f"tools.{name}", ("gate", "requires", "drive", "parameters"), "x")
    requires = spec.get("requires", [])
    if not isinstance(requires, list) or not all(isinstance(r, str) for r in requires):
        raise _manifest(f"{here} requires", "`requires` is a list of strings", "x")
    steps = spec.get("drive", [])
    if not isinstance(steps, list) or not all(isinstance(s, dict) for s in steps):
        raise _manifest(f"{here} drive", "`drive` is a list of tables", "x")
    drive = []
    for index, step in enumerate(steps):
        refuse_unknown(
            step,
            f"{here} drive[{index}]",
            f"tools.{name}.drive",
            ("pin", "operation", "seconds_from"),
            "a drive step has pin, operation and seconds_from",
        )
        pin, operation = step.get("pin"), step.get("operation")
        if not isinstance(pin, str) or not isinstance(operation, str):
            raise _manifest(f"{here} drive[{index}]", "`pin` and `operation` are required", "x")
        seconds_from = step.get("seconds_from")
        if seconds_from is not None and not isinstance(seconds_from, str):
            raise _manifest(f"{here} drive[{index}]", "`seconds_from` names a parameter", "x")
        drive.append(Drive(pin, operation, seconds_from))
    parameters = spec.get("parameters", {})
    if not isinstance(parameters, dict):
        raise _manifest(f"{here} parameters", "`parameters` is a table of tables", "x")
    gate = spec.get("gate")
    if not isinstance(gate, str):
        raise _manifest(f"{here} gate", "`gate` is required", 'write gate = "neuroedge://…"')
    return Tool(name, gate, tuple(requires), parameters, tuple(drive))


# --- tools as action specs ------------------------------------------------------------------


def _body(tool: Tool) -> Callable[..., Any]:
    """The function the `ActionSpec` runs under the token, with the signature the tool declares."""
    params = [
        inspect.Parameter(
            name,
            inspect.Parameter.KEYWORD_ONLY,
            default=schema.get("default", inspect.Parameter.empty),
            annotation=_TYPES[schema["type"]],
        )
        for name, schema in tool.parameters.items()
    ]
    signature = inspect.Signature(params)
    drive = tool.drive
    run = tool.run

    def body(**given: Any) -> Any:
        bound = signature.bind(**given)
        bound.apply_defaults()  # `dispatch` passes only what the caller gave
        arguments = dict(bound.arguments)
        if run is not None:
            return run(**arguments)
        for step in drive:
            pin = digital.out(step.pin)
            if step.operation == "pulse":
                pin.pulse(seconds=float(arguments[step.seconds_from or ""]))
            elif step.operation == "on":
                pin.on()
            else:
                pin.off()
        return None

    body.__signature__ = signature  # type: ignore[attr-defined]
    body.__annotations__ = {p.name: p.annotation for p in params}
    body.__name__ = tool.name
    body.__doc__ = f"Guarded tool {tool.name} (gate {tool.gate})."
    return body


def specs_of(tools: Sequence[Tool], where: str = "<guard>") -> dict[str, ActionSpec]:
    """The tools as `ActionSpec`s keyed by name; the gate key of each is the tool's name."""
    specs: dict[str, ActionSpec] = {}
    for tool in tools:
        if tool.name in specs:
            raise _manifest(where, f"tool {tool.name!r} is declared twice", "name each tool once")
        specs[tool.name] = ActionSpec(
            name=tool.name,
            requires=tuple(Requirement.parse(r, where) for r in tool.requires),
            gate=tool.name,
            fn=_body(tool),
            source_file=where,
            source_line=0,
        )
    return specs


def label_of(config: GuardConfig) -> str:
    """`metadata.agent_version` of a Guard's trace: `guard:<name>@<neuroedge version>`."""
    return f"guard:{config.name}@{__version__}"


def _gate_ref(tool: Tool, base: Path | None) -> str | Path:
    if tool.gate.startswith("neuroedge://") or base is None:
        return tool.gate
    return base / tool.gate


def resolve_gates(config: GuardConfig) -> dict[str, ResolvedGate]:
    """Every tool's gate, fully resolved (inheritance and all) — not merely schema-valid."""
    from .engine import resolve_gate_file, resolve_gate_uri

    registry = GateRegistry(config.registry_root) if config.registry_root else None
    gates: dict[str, ResolvedGate] = {}
    for tool in config.tools:
        ref = _gate_ref(tool, config.base)
        if isinstance(ref, str) and ref.startswith("neuroedge://"):
            gates[tool.name] = resolve_gate_uri(ref, registry=registry)
        else:
            gates[tool.name] = resolve_gate_file(ref, registry=registry)
    return gates


class NoHal:
    """
    The HAL of a Guard with no board: it holds no pin. A token still exists for every ALLOW
    (the ledger is the HAL's authorizer), but any attempt to drive a pin is refused.
    """

    target = "sim"
    board = None
    envelope = None

    def __init__(self) -> None:
        self.authorize: Any = None

    def digital_out(self, pin: str, *args: Any, **kwargs: Any) -> Any:
        raise BoardCapabilityError(
            where=f"digital.out({pin!r})",
            why="this Guard has no board, so it has no pins",
            how="set [guard] board in guard.toml, or drop the pin from the tool",
        )

    def close(self) -> None:
        return None


# --- the Guard ------------------------------------------------------------------------------


class Dispatcher:
    """
    What a bridge gets: one method, bound to one id at creation. The source of what it sends
    is `bridge:<id>`, stamped by the core — a `ToolRequest` has no field to state another.
    """

    __slots__ = ("_id", "_source", "_send")

    def __init__(self, ident: str, source: str, send: Callable[[str, ToolRequest], Any]) -> None:
        self._id = ident
        self._source = source
        self._send = send

    @property
    def id(self) -> str:
        return self._id

    async def dispatch(self, request: ToolRequest) -> Outcome:
        outcome: Outcome = await self._send(self._source, request)
        return outcome


class Guard:
    """
    Gate → token → envelope → trace for a program that has no agent.

    `tools` are declared as data; each tool's gate is loaded and resolved here, so a gate that
    does not resolve stops the load before anything holds a pin. `board` is a board id (or
    None: verdicts only, no pins, and a tool that `requires` a pin is refused with
    `BoardCapabilityError`); `target` is `sim` or `linux` and defaults to the board's.
    `testing=True` is the only way to reach the source `test` (`testing_dispatcher`).
    """

    def __init__(
        self,
        tools: Sequence[Tool],
        *,
        name: str = "guard",
        board: str | None = None,
        target: str | None = None,
        registry_root: str | Path | None = None,
        base: str | Path | None = None,
        events: EventLog | None = None,
        testing: bool = False,
        hal_options: Mapping[str, Any] | None = None,
        source: str = "<guard>",
    ) -> None:
        if not isinstance(name, str) or not NAME.fullmatch(name):
            raise _manifest(source, f"{name!r} is not a guard name", "use letters, digits, _ . -")
        config = GuardConfig(
            name=name,
            tools=tuple(tools),
            board=board,
            registry_root=Path(registry_root) if registry_root else None,
            base=Path(base) if base else None,
            source=source,
        )
        self.config = config
        self.testing = bool(testing)
        self._closed = False
        self._lock = asyncio.Lock()
        specs = specs_of(config.tools, source)
        profile = self._board(config, specs)
        chosen = target or (profile.target if profile is not None else "sim")
        if chosen not in _TARGETS or (profile is not None and profile.target != chosen):
            raise BoardCapabilityError(
                where=f"Guard(board={board!r}, target={target!r})",
                why=(
                    f"a Guard runs on {' or '.join(_TARGETS)}"
                    + (f"; board {board!r} targets {profile.target!r}" if profile else "")
                ),
                how="pick a sim or linux board (the MCU runs ne_gate + NETR, RFC-0003)",
            )
        events = events if events is not None else EventLog()
        events.metadata.update(
            target=chosen,
            board_id=profile.id if profile is not None else NO_BOARD,
            agent_version=label_of(config),
        )
        self.events = events
        # Gates first: one that does not resolve stops the load before a line is requested.
        engine = ActionContractEngine(clock=events.clock, events=events)
        resolved = resolve_gates(config)
        for key, gate in resolved.items():
            engine.register(key, gate)
        hal = (
            build_hal(
                chosen,
                profile,
                events,
                dict(hal_options or {}),
                needs={"where": f"{source} on target {chosen!r}"} if chosen == "linux" else None,
            )
            if profile is not None
            else NoHal()
        )
        try:
            self._conversation = Conversation(engine=engine, hal=hal, registry=specs)
            self._tools = ToolSet(
                specs.values(),
                {n: g.arguments for n, g in resolved.items() if g.arguments},
            )
        except BaseException:
            release_hal(hal)
            raise
        self.hal = hal
        self.engine = engine

    @staticmethod
    def _board(config: GuardConfig, specs: Mapping[str, ActionSpec]) -> BoardProfile | None:
        needs = sorted({pin for tool in config.tools for pin in tool.pins})
        if config.board is None:
            if needs:
                tool = next(t for t in config.tools if t.pins)
                raise BoardCapabilityError(
                    where=f"{config.source} -> [tools.{tool.name}] requires",
                    why=f"the tool needs pins {needs} and this Guard has no board",
                    how="set [guard] board (an id from boards/), or drop `requires`",
                )
            return None
        profile = load_board_by_id(config.board)
        for tool in config.tools:
            for pin in tool.pins:
                profile.require_pin(pin, called_from=f"{config.source} -> [tools.{tool.name}]")
        return profile

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        events: EventLog | None = None,
        target: str | None = None,
        testing: bool = False,
        hal_options: Mapping[str, Any] | None = None,
    ) -> Guard:
        """A Guard from `guard.toml`; relative gate files and the registry root are next to it."""
        config = load_config(path)
        return cls(
            config.tools,
            name=config.name,
            board=config.board,
            target=target,
            registry_root=config.registry_root,
            base=config.base,
            events=events,
            testing=testing,
            hal_options=hal_options,
            source=config.source,
        )

    # -- who calls ------------------------------------------------------------------------

    def dispatcher(self, ident: str) -> Dispatcher:
        """
        A `Dispatcher` for the bridge `ident` (`[a-z][a-z0-9_]{0,31}`): registers `bridge:<id>`.
        A second request for the same id, or an id outside the grammar, is refused (NE1004).
        """
        source = f"bridge:{ident}" if isinstance(ident, str) else ""
        if not valid_source(source):
            raise ToolCallError(
                where=f"Guard.dispatcher({ident!r})",
                why=f"{ident!r} is not a bridge id",
                how="use [a-z][a-z0-9_]{0,31}: lowercase letters, digits and underscores",
            )
        self._conversation.register_source(source)
        return Dispatcher(ident, source, self._send)

    def testing_dispatcher(self) -> Dispatcher:
        """The one road to the source `test` — only on a `Guard(..., testing=True)`."""
        if not self.testing:
            raise ToolCallError(
                where="Guard.testing_dispatcher()",
                why="the source `test` is reachable only on a Guard built with testing=True",
                how="build the Guard with testing=True in a test, or ask for dispatcher(<id>)",
            )
        return Dispatcher("test", "test", self._send)

    async def _send(self, source: str, request: ToolRequest) -> Outcome:
        if not isinstance(request, ToolRequest):
            raise ToolCallError(
                where=f"Dispatcher.dispatch({type(request).__name__})",
                why="a bridge sends a ToolRequest; it has no `source` to state",
                how="build ToolRequest(name, arguments)",
            )
        if self._closed:
            raise ToolCallError(
                where="Guard.dispatch",
                why="this Guard is closed",
                how="build a new Guard; a closed one holds no pins",
            )
        call = ToolCall(request.name, dict(request.arguments), source, request.id)
        # One at a time (RFC-0016 §3b item 5). The sources no longer need it — they belong to
        # each call (`Conversation.do_with`) — but the trace does: two dispatches in flight
        # would interleave their events, and a replay reads a trace as a sequence of steps.
        async with self._lock:
            result = await dispatch(self._conversation, self._tools, call)
        return Outcome(result.status, result.content())

    def set_fact(self, name: str, value: Any) -> None:
        """A fact of the program's own, in front of every gate, like `c.facts`."""
        if not isinstance(name, str) or not name or name in _RESERVED_FACTS:
            raise ToolCallError(
                where=f"Guard.set_fact({name!r})",
                why="the name is empty or one the core sets itself (call_source, call_channel)",
                how="name a criterion your gates declare",
            )
        if not isinstance(value, str | int | float | bool):
            raise ToolCallError(
                where=f"Guard.set_fact({name!r})",
                why=f"a fact is a string, a number or a bool, not {type(value).__name__}",
                how="pass a scalar",
            )
        self._conversation.facts[name] = value

    # -- the record and the end -----------------------------------------------------------

    def trace(self) -> dict[str, Any]:
        """The Guard's session so far as a `trace.v1` document, validated before it is returned."""
        trace = self.events.to_trace()
        validate_trace(trace, label=f"guard {self.events.session_id}")
        return trace

    def close(self) -> None:
        """Release the pins, like `SimSession.close()`. Idempotent."""
        self._closed = True
        release_hal(self.hal)

    async def __aenter__(self) -> Guard:
        return self

    async def __aexit__(self, *exc: object) -> None:
        self.close()
