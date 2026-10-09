"""
The declaration of remote actuators, `[actuators.<name>]`, and its one check (RFC-0018 §3b, §3f,
§3k; TSK-I2c-16).

`ActuatorDeclaration` is the data; `parse_actuators` reads it from a TOML table (`agent.toml`,
`guard.toml`) and `check_actuators` is **the** check — `neuroedge build` calls it, and so do
`SimSession.load` and `Guard` at load time, whether the declarations came from a file or from
code. Nothing reaches the HAL around it.

What it refuses, and with which code:

* NE3002 (`AgentManifestError`, §3b, §3f): a bad name or one that is already a pin, an enable
  line, a motion channel or another actuator of the board; a missing or unknown `plugin`,
  `safe_off`, `envelope` (four keys, `board.v1#/$defs/envelope`); `reversible` not a bool; an
  unknown key; a secret written as a value; a name not listed in `[requires] "digital.out".pins`;
  a plugin that is not an entry point of an enabled distribution, or that refuses its config;
  **D5**: an irreversible actuator (`reversible` not true) whose `safe_off` is below L2.
* NE3001 (`BoardCapabilityError`, §3k): `[actuators]` on a target with no plugin loader
  (`esp32s3`); `safe_off` above the plugin's `safe_off_level`; an irreversible actuator whose
  plugin is below L2 or has no read-back; `max_continuous_ms` not above the plugin's
  `tolerance_ms`; `pwm` or `motion` naming a remote actuator.

A warning (never a refusal): level L0, which only a reversible actuator may have.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import jsonschema

from ..errors import AgentManifestError, BoardCapabilityError, BuildFailed, NeuroEdgeError
from ..hal.board import _board_schema
from ..hal.remote import Vocabulary
from ..models.providers.common import refuse_unknown, safe_name, secret_fields
from ..sdk import Ambiguous, Command, NotSent, ReadFailed, Rejected
from . import (
    CODE_NAME,
    LEVELS,
    LoadedPlugin,
    PluginsConfig,
    build_actuator,
    check_config,
    load_enabled,
    parse_plugins,
)

__all__ = [
    "ActuatorDeclaration",
    "BoundActuator",
    "Checked",
    "check_actuators",
    "level_rank",
    "parse_actuators",
]

_KEYS = ("plugin", "safe_off", "reversible", "envelope", "config")
# What the HAL catches and builds when it drives a plugin: the SDK's own classes.
SDK_VOCABULARY = Vocabulary(Command, NotSent, Rejected, Ambiguous, ReadFailed)
_ENVELOPE_KEYS = ("window_s", "max_on_ms_per_window", "min_interval_ms", "max_continuous_ms")
REMOTE_TARGETS = ("sim", "linux")


def level_rank(level: str) -> int:
    return LEVELS.index(level)


@dataclass(frozen=True)
class ActuatorDeclaration:
    """
    One remote actuator: the plugin entry point that drives it, the safe-off level the deployer
    relies on, whether leaving it on harms nothing (`reversible`, default False), its envelope
    (the four keys of RFC-0007 §3d) and the plugin's config (no I/O, no secret values).
    """

    name: str
    plugin: str
    safe_off: str
    envelope: Mapping[str, int]
    reversible: bool = False
    config: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BoundActuator:
    """A declaration that passed the check, with the driver its plugin built for it."""

    declaration: ActuatorDeclaration
    plugin: LoadedPlugin
    driver: Any


@dataclass
class Checked:
    """What `check_actuators` found: the problems (all of them), the warnings, the drivers."""

    problems: list[NeuroEdgeError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    bound: dict[str, BoundActuator] = field(default_factory=dict)


def _manifest(where: str, why: str, how: str) -> AgentManifestError:
    return AgentManifestError(where=where, why=why, how=how)


def _capability(where: str, why: str, how: str) -> BoardCapabilityError:
    return BoardCapabilityError(where=where, why=why, how=how)


def _envelope_problem(envelope: Any) -> str | None:
    schema = _board_schema()
    validator = jsonschema.Draft202012Validator(
        {"$ref": "#/$defs/envelope", "$defs": schema["$defs"]}
    )
    errors = sorted(validator.iter_errors(envelope), key=lambda e: list(e.absolute_path))
    if not errors:
        return None
    first = errors[0]
    path = ".".join(str(p) for p in first.absolute_path)
    return f"{path + ': ' if path else ''}{first.message}"


def parse_actuators(
    table: Any, where: str
) -> tuple[dict[str, ActuatorDeclaration], list[NeuroEdgeError]]:
    """`[actuators]` as declarations; every rule of the table itself (§3b) is checked here."""
    declarations: dict[str, ActuatorDeclaration] = {}
    problems: list[NeuroEdgeError] = []
    if table is None:
        return declarations, problems
    if not isinstance(table, Mapping):
        return declarations, [_manifest(f"{where} [actuators]", "must be a table", "x")]
    for name, spec in table.items():
        here = f"{where} [actuators.{name if CODE_NAME.fullmatch(str(name)) else '?'}]"
        try:
            declarations[name] = _declaration(name, spec, here)
        except NeuroEdgeError as problem:
            problems.append(problem)
    return declarations, problems


def _declaration(name: Any, spec: Any, here: str) -> ActuatorDeclaration:
    if not isinstance(name, str) or not CODE_NAME.fullmatch(name):
        raise _manifest(
            here,
            f"{safe_name(name)} is not a remote actuator name",
            "use [a-z][a-z0-9_]{0,31}: lowercase letters, digits and underscores",
        )
    if not isinstance(spec, Mapping):
        raise _manifest(here, "a remote actuator is a table", f"write [actuators.{name}]")
    secrets = [s for s in secret_fields(spec) if not s.endswith("_env")]
    if secrets:
        # Never repeat the value: it may be a live key.
        raise _manifest(
            f"{here} {secrets[0]}",
            "a secret must never be written in a committed file — the file is shared with it",
            f"delete `{secrets[0]}`, export it and name the variable: "
            f'{secrets[0].rsplit(".", 1)[-1]}_env = "NE_..."',
        )
    refuse_unknown(
        spec,
        here,
        f"actuators.{name}",
        _KEYS,
        "a remote actuator takes plugin, safe_off, reversible, envelope and config (RFC-0018 §3b)",
    )
    plugin = spec.get("plugin")
    if not isinstance(plugin, str) or not CODE_NAME.fullmatch(plugin):
        raise _manifest(
            f"{here} plugin",
            "`plugin` is required: the name of a neuroedge.actuators entry point",
            'write plugin = "home_assistant" and enable its distribution in [plugins] enable',
        )
    safe_off = spec.get("safe_off")
    if safe_off not in LEVELS:
        raise _manifest(
            f"{here} safe_off",
            f"`safe_off` is required and one of {list(LEVELS)}; "
            + ("it is missing" if safe_off is None else f"{safe_name(safe_off)} is not a level"),
            "declare the level you rely on (RFC-0018 §3d); a level is never guessed",
        )
    reversible = spec.get("reversible", False)
    if not isinstance(reversible, bool):
        raise _manifest(
            f"{here} reversible",
            "`reversible` is true or false (left out: false, irreversible)",
            "write reversible = true only if leaving it on harms nothing and off undoes it",
        )
    envelope = spec.get("envelope")
    if envelope is None:
        raise _manifest(
            f"{here} envelope",
            "the envelope is required: a remote actuator is an actuator (RFC-0007 §3d)",
            f"add [actuators.{name}.envelope] with {', '.join(_ENVELOPE_KEYS)}",
        )
    problem = _envelope_problem(envelope)
    if problem is not None:
        raise _manifest(
            f"{here} envelope",
            f"{problem} (board.v1 #/$defs/envelope)",
            f"declare exactly the four keys {list(_ENVELOPE_KEYS)} as positive whole numbers",
        )
    config = spec.get("config", {})
    if not isinstance(config, Mapping):
        raise _manifest(f"{here} config", "`config` is a table", f"write [actuators.{name}.config]")
    check_config(config, f"{here} config")
    return ActuatorDeclaration(name, plugin, safe_off, dict(envelope), reversible, dict(config))


def check_actuators(
    declarations: Mapping[str, ActuatorDeclaration],
    *,
    plugins: Mapping[str, LoadedPlugin],
    target: str,
    board: Any,
    digital_out: Mapping[str, Any],
    motion: Sequence[str] = (),
    where: str,
    build: bool = True,
) -> Checked:
    """
    The rules of RFC-0018 §3b, §3f and §3k that need the board, `[requires]` and the plugins.
    `digital_out` is `[requires] "digital.out"` (`pins`, `pwm`), `motion` the motion channels
    `[requires]` names. With `build`, each plugin's factory is called once per declaration (no
    I/O) and the driver is kept in the result. Returns every problem, never stops at the first.
    """
    checked = Checked()
    problems = checked.problems
    if not declarations:
        return checked
    if target not in REMOTE_TARGETS:
        problems.append(
            _capability(
                f"{where} [actuators] on target {target!r}",
                f"remote actuators run on {' and '.join(REMOTE_TARGETS)} only: {target} has "
                "no plugin loader (RFC-0018 §3a)",
                "build for sim or linux, or drive the device from a gateway (I14)",
            )
        )
        return checked
    if board is None:
        problems.append(
            _capability(
                f"{where} [actuators]",
                "a remote actuator is driven by the HAL, and there is no board, so no HAL",
                "set the board ([guard] board in guard.toml)",
            )
        )
        return checked
    taken = {
        **dict.fromkeys(board.pins, "a digital.out pin"),
        **dict.fromkeys(board.input_pins, "a digital.in pin"),
        **dict.fromkeys(board.enable_pins, "an enable line"),
        **{c["name"]: "a motion channel" for c in board.motion_channels},
    }
    pins = digital_out.get("pins", [])
    pins = pins if isinstance(pins, list) else []
    pwm = digital_out.get("pwm", [])
    pwm = pwm if isinstance(pwm, list) else []
    for name, declaration in declarations.items():
        here = f"{where} [actuators.{name}]"
        if name in taken:
            problems.append(
                _manifest(
                    here,
                    f"{name!r} is already {taken[name]} of board {board.id!r}: one name, one "
                    "target, or a command meant for the device would move the board's pin",
                    "give the remote actuator a name of its own",
                )
            )
            continue
        if name not in pins:
            problems.append(
                _manifest(
                    here,
                    f"{name!r} is declared here and not listed in [requires] "
                    '"digital.out".pins: a remote actuator is a digital.out the agent needs',
                    f'add {name!r} to [requires] "digital.out" = {{ pins = [...] }}',
                )
            )
        if name in pwm or name in motion:
            kind = "pwm" if name in pwm else "motion"
            problems.append(
                _capability(
                    f"{where} [requires] {kind} {name!r}",
                    f"{name!r} is a remote actuator: only on, off and pulse reach one; a "
                    f"{kind} command has no bound for a lost link (RFC-0018 §3a, §9.4)",
                    f"remove {name!r} from {kind}",
                )
            )
        if not declaration.reversible and level_rank(declaration.safe_off) < level_rank("L2"):
            problems.append(
                _manifest(
                    f"{here} safe_off",
                    f"the actuator is irreversible (reversible is not true) and declares "
                    f'safe_off = "{declaration.safe_off}": this runtime sends the off, so a lost '
                    "link or a frozen runtime leaves it on",
                    "use a plugin and device kind that reach L2 or L3 and set safe_off to it, or "
                    "— only if leaving it on harms nothing — set reversible = true "
                    "(RFC-0018 §3f)",
                )
            )
        plugin = plugins.get(declaration.plugin)
        if plugin is None:
            problems.append(
                _manifest(
                    f"{here} plugin",
                    f"{declaration.plugin!r} is not an entry point of an enabled distribution "
                    f"(enabled: {sorted(plugins) or 'none'})",
                    "add the plugin's distribution to [plugins] enable, or fix the name",
                )
            )
            continue
        if not build:
            continue
        try:
            driver = build_actuator(plugin, declaration.config, here)
        except NeuroEdgeError as problem:
            problems.append(problem)
            continue
        found = _plugin_problems(declaration, driver, here)
        problems += found
        if declaration.safe_off == "L0":
            checked.warnings.append(
                f'{here}: safe_off = "L0" — nobody turns {name!r} off if NeuroEdge stops or the '
                "link is lost; only acceptable because reversible = true"
            )
        if not found:
            checked.bound[name] = BoundActuator(declaration, plugin, driver)
    return checked


def _plugin_problems(
    declaration: ActuatorDeclaration, driver: Any, here: str
) -> list[NeuroEdgeError]:
    problems: list[NeuroEdgeError] = []
    level, readback = driver.safe_off_level, driver.readback
    if level_rank(declaration.safe_off) > level_rank(level):
        problems.append(
            _capability(
                f"{here} safe_off",
                f'safe_off = "{declaration.safe_off}" is above what plugin '
                f"{declaration.plugin!r} proves for this config ({level}): a level is never "
                "raised at run time",
                f'set safe_off to "{level}" or lower, or use a plugin that proves more',
            )
        )
    if not declaration.reversible and (level_rank(level) < level_rank("L2") or readback == "none"):
        problems.append(
            _capability(
                f"{here} plugin",
                f"the actuator is irreversible and plugin {declaration.plugin!r} proves {level} "
                f"with readback {readback!r}: irreversible needs L2 or L3 and a read-back, "
                "or the level rests on the plugin's word only (RFC-0018 §3f)",
                "use a plugin and device that turn themselves off and can be read back",
            )
        )
    tolerance = driver.tolerance_ms
    ceiling = declaration.envelope["max_continuous_ms"]
    if ceiling <= tolerance:
        problems.append(
            _capability(
                f"{here} envelope max_continuous_ms",
                f"max_continuous_ms {ceiling} is not above the plugin's tolerance_ms "
                f"{tolerance}: the device may run {tolerance} ms past any deadline",
                f"raise max_continuous_ms above {tolerance}",
            )
        )
    return problems


@dataclass
class RemoteSetup:
    """`[plugins]` and `[actuators]` of one file, loaded and checked together."""

    declarations: dict[str, ActuatorDeclaration] = field(default_factory=dict)
    plugins: dict[str, LoadedPlugin] = field(default_factory=dict)
    checked: Checked = field(default_factory=Checked)
    # Every name `[actuators]` declares, well formed or not: `[requires]` is matched against
    # these, so a broken declaration is reported once, as itself.
    names: tuple[str, ...] = ()

    @property
    def problems(self) -> list[NeuroEdgeError]:
        return self.checked.problems

    @property
    def records(self) -> list[Any]:
        return [plugin.record for plugin in self.plugins.values()]

    def raise_problems(self, where: str) -> None:
        """Nothing starts with a problem: one is raised as is, several as `BuildFailed`."""
        if len(self.problems) == 1:
            raise self.problems[0]
        if self.problems:
            raise BuildFailed(where=where, problems=self.problems)


def remote_setup(
    document: Mapping[str, Any],
    *,
    where: str,
    target: str,
    board: Any,
    requires: Mapping[str, Any],
    build: bool = True,
    declarations: Mapping[str, ActuatorDeclaration] | None = None,
) -> RemoteSetup:
    """
    Read `[plugins]` and `[actuators]` of `document` (agent.toml or guard.toml), import the
    enabled distributions and run `check_actuators`. `declarations` made in code are checked
    the same way, beside the file's; `document["plugins"]` may be a `PluginsConfig` already read.
    """
    setup = RemoteSetup()
    parsed, problems = parse_actuators(document.get("actuators"), where)
    setup.declarations = {**parsed, **dict(declarations or {})}
    table = document.get("actuators")
    written = [str(n) for n in table] if isinstance(table, Mapping) else []
    setup.names = tuple(dict.fromkeys([*written, *setup.declarations]))
    setup.checked.problems += problems
    try:
        config = (
            document["plugins"]
            if isinstance(document.get("plugins"), PluginsConfig)
            else parse_plugins(document.get("plugins"), where)
        )
        setup.plugins = load_enabled(config, where)
    except NeuroEdgeError as problem:
        setup.checked.problems.append(problem)
        return setup  # without the plugins, every further rule would only repeat this one
    digital_out = requires.get("digital.out", {})
    motion = requires.get("motion", {}).get("channels", [])
    checked = check_actuators(
        setup.declarations,
        plugins=setup.plugins,
        target=target,
        board=board,
        digital_out=digital_out if isinstance(digital_out, Mapping) else {},
        motion=motion if isinstance(motion, list) else [],
        where=where,
        build=build,
    )
    checked.problems[:0] = setup.checked.problems
    setup.checked = checked
    return setup
