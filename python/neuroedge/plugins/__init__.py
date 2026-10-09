"""
The plugin loader (RFC-0016 §3d; the actuator part of TSK-I2c-11).

* **Discovery imports nothing.** `discover()` reads `importlib.metadata` entry points of the six
  NeuroEdge groups — name, distribution, version — without importing a package.
* **Only what the operator enabled is imported.** `[plugins] enable = ["dist", "dist==1.2"]` in
  `agent.toml` or `guard.toml` (PEP 503 names, an optional `==version` pin). Installing a package
  enables nothing; no command-line flag enables anything either.
* **Broken ⇒ nothing starts.** A distribution that is not installed, does not import, asks for
  another SDK, has the wrong version, gives an entry point name another enabled distribution
  also gives, or whose factory has the wrong shape is an `AgentManifestError` (NE3002), three
  parts — raised before the first gate is evaluated, never skipped.
* **Provenance.** Every loaded entry point has a `PluginRecord` — `{kind, name, distribution,
  version, files_sha256}` (or `editable: true` and no hash) — that a session writes to
  `metadata.plugins` and as a `plugin_loaded` event.

Only the actuator kind (`neuroedge.actuators`, RFC-0018) is implemented. An enabled distribution
that brings another kind is refused, naming TSK-I2c-11: a plugin the core cannot run must not be
silently ignored. The plugin config `[plugins.config.<entry point>]` follows the secret rules of
`[external]` (a variable's name in `*_env`, never a value).
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import importlib.metadata as metadata
import inspect
import json
import re
import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from ..errors import AgentManifestError
from ..models.providers.common import ENV_NAME, refuse_unknown, safe_name, secret_fields
from ..sdk import SDK_VERSION

__all__ = [
    "GROUPS",
    "IMPLEMENTED",
    "Listed",
    "LoadedPlugin",
    "PluginRecord",
    "PluginsConfig",
    "check_actuator",
    "discover",
    "load_enabled",
    "normalise",
    "parse_plugins",
    "sdk_compatible",
]

# kind -> entry point group (RFC-0016 §3c)
GROUPS: dict[str, str] = {
    "bridge": "neuroedge.bridges",
    "fact_source": "neuroedge.fact_sources",
    "actuator": "neuroedge.actuators",
    "board": "neuroedge.boards",
    "template": "neuroedge.templates",
    "exporter": "neuroedge.exporters",
}
IMPLEMENTED = ("actuator",)
LATER = "TSK-I2c-11 (the plugin loader of RFC-0016 §3d); this release loads actuators only"
CODE_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")
# A distribution name as written (PEP 508), and an optional exact pin.
_ENABLE = re.compile(
    r"([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)(?:==([A-Za-z0-9][A-Za-z0-9.+!-]*))?"
)
# The limits RFC-0018 §9.5 (Q-68) puts on what a plugin may declare.
MAX_COMMAND_TIMEOUT_MS = 5000
MAX_TOLERANCE_MS = 2000
LEVELS = ("L0", "L1", "L2", "L3")
READBACKS = ("push", "poll", "none")


def normalise(name: str) -> str:
    """The PEP 503 form of a distribution name: runs of `-_.` become `-`, all lowercase."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _manifest(where: str, why: str, how: str) -> AgentManifestError:
    return AgentManifestError(where=where, why=why, how=how)


# --- discovery ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Listed:
    """One entry point of a NeuroEdge group, as `plugin list` shows it (nothing imported)."""

    kind: str
    group: str
    name: str
    value: str
    distribution: str
    version: str


def _distribution_of(entry: metadata.EntryPoint) -> metadata.Distribution | None:
    return getattr(entry, "dist", None)


def discover() -> list[Listed]:
    """Every entry point of the six NeuroEdge groups that is installed. Imports no package."""
    found: list[Listed] = []
    for kind, group in GROUPS.items():
        for entry in metadata.entry_points(group=group):
            dist = _distribution_of(entry)
            found.append(
                Listed(
                    kind,
                    group,
                    entry.name,
                    entry.value,
                    normalise(dist.metadata["Name"]) if dist is not None else "?",
                    dist.version if dist is not None else "?",
                )
            )
    return sorted(found, key=lambda x: (x.group, x.name, x.distribution))


# --- [plugins] ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Enabled:
    distribution: str  # normalised
    pin: str | None = None


@dataclass(frozen=True)
class PluginsConfig:
    """`[plugins]` read and checked: what is enabled, and each entry point's config."""

    enable: tuple[Enabled, ...] = ()
    config: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    source: str = "<plugins>"


def parse_plugins(table: Any, where: str) -> PluginsConfig:
    """`[plugins]` of agent.toml or guard.toml; every problem is NE3002, a secret never echoed."""
    here = f"{where} [plugins]"
    if table is None:
        return PluginsConfig(source=where)
    if not isinstance(table, Mapping):
        raise _manifest(here, "[plugins] must be a table", 'write [plugins] enable = ["<dist>"]')
    refuse_unknown(
        table,
        here,
        "plugins",
        ("enable", "config"),
        "[plugins] takes enable (distributions) and config (one table per entry point)",
    )
    raw = table.get("enable", [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise _manifest(
            f"{here} enable",
            "`enable` is a list of distribution names",
            'write enable = ["neuroedge-ha", "neuroedge-ros2==0.4.1"]',
        )
    enabled: list[Enabled] = []
    seen: set[str] = set()
    for item in raw:
        match = _ENABLE.fullmatch(item.strip())
        if match is None:
            raise _manifest(
                f"{here} enable",
                f"{safe_name(item)} is not a distribution name with an optional ==version pin",
                'write the PyPI name, e.g. "neuroedge-ha" or "neuroedge-ha==1.2.0"',
            )
        name = normalise(match.group(1))
        if name in seen:
            raise _manifest(f"{here} enable", f"{name!r} is enabled twice", "list it once")
        seen.add(name)
        enabled.append(Enabled(name, match.group(2)))
    configs = table.get("config", {})
    if not isinstance(configs, Mapping) or not all(
        isinstance(v, Mapping) for v in configs.values()
    ):
        raise _manifest(
            f"{here} config",
            "`config` is a table of tables, one per entry point name",
            "write [plugins.config.<entry point>] with its keys",
        )
    for name, values in configs.items():
        check_config(values, f"{here} config.{name}")
    return PluginsConfig(tuple(enabled), {k: dict(v) for k, v in configs.items()}, where)


def check_config(values: Mapping[str, Any], where: str) -> None:
    """
    A plugin's config as written in a committed file: no field named like a secret, and every
    `*_env` names an environment variable (RFC-0014 §3c rules). The value is never repeated.
    """
    secrets = [s for s in secret_fields(values) if not s.endswith("_env")]
    if secrets:
        raise _manifest(
            f"{where} {secrets[0]}",
            "a secret must never be written in a committed file — the file is shared with it",
            f"delete `{secrets[0]}`, export the value and name the variable: "
            f'{secrets[0].rsplit(".", 1)[-1]}_env = "NE_..."',
        )
    for key, value in _flat(values):
        if key.endswith("_env") and (not isinstance(value, str) or not ENV_NAME.match(value)):
            raise _manifest(
                f"{where} {key}",
                f"{key} must be the NAME of an environment variable (letters, digits, _); the "
                "value given is not one — if it is the secret itself, revoke it",
                f'write {key} = "NE_..." and export the secret in that variable',
            )


def _flat(values: Mapping[str, Any], prefix: str = "") -> Iterable[tuple[str, Any]]:
    for key, value in values.items():
        if isinstance(value, Mapping):
            yield from _flat(value, f"{prefix}{key}.")
        else:
            yield f"{prefix}{key}", value


# --- loading -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class PluginRecord:
    """The provenance of one loaded entry point (RFC-0016 §3d item 4)."""

    kind: str
    name: str
    distribution: str
    version: str
    files_sha256: str | None
    editable: bool = False

    def as_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "kind": self.kind,
            "name": self.name,
            "distribution": self.distribution,
            "version": self.version,
        }
        if self.editable:
            data["editable"] = True
        else:
            data["files_sha256"] = self.files_sha256
        return data


@dataclass(frozen=True)
class LoadedPlugin:
    """An enabled entry point: imported, its SDK checked, its factory of the right shape."""

    name: str
    kind: str
    factory: Callable[[Mapping[str, Any]], Any]
    record: PluginRecord
    config: Mapping[str, Any] = field(default_factory=dict)  # [plugins.config.<name>]


def sdk_compatible(required: Any) -> bool:
    """Same MAJOR, and the installed MINOR at least the one asked for (RFC-0016 §3e)."""
    if (
        not isinstance(required, tuple)
        or len(required) != 2
        or not all(isinstance(n, int) and not isinstance(n, bool) and n >= 0 for n in required)
    ):
        return False
    return required[0] == SDK_VERSION[0] and required[1] <= SDK_VERSION[1]


def _installed(name: str) -> metadata.Distribution | None:
    for dist in metadata.distributions():
        if normalise(dist.metadata["Name"] or "") == name:
            return dist
    return None


def _editable(dist: metadata.Distribution) -> bool:
    raw = dist.read_text("direct_url.json")
    if not raw:
        return False
    try:
        return bool(json.loads(raw).get("dir_info", {}).get("editable"))
    except (ValueError, AttributeError):
        return False


def files_sha256(dist: metadata.Distribution, module: str, where: str) -> str | None:
    """
    The SHA-256 over the bytes on disk of the distribution's files that belong to the package
    of `module` (never read from RECORD, which can be edited with them). None when the
    distribution lists none of them.
    """
    top = module.split(".", 1)[0]
    lines = []
    for path in dist.files or ():
        parts = path.parts
        if not parts or "__pycache__" in parts or path.suffix == ".pyc":
            continue
        if parts[0] != top and str(path) != f"{top}.py":
            continue
        try:
            data = path.locate().read_bytes()
        except OSError as problem:
            raise _manifest(
                where,
                f"{path} of the plugin cannot be read to hash it: {problem.strerror or problem}",
                "reinstall the distribution",
            ) from None
        lines.append(f"{path.as_posix()}\0{hashlib.sha256(data).hexdigest()}\n")
    if not lines:
        return None
    return "sha256:" + hashlib.sha256("".join(sorted(lines)).encode()).hexdigest()


def load_enabled(plugins: PluginsConfig, where: str | None = None) -> dict[str, LoadedPlugin]:
    """
    Import the enabled distributions and check each actuator entry point; keyed by entry point
    name. Any problem is NE3002 and nothing is returned: the caller starts nothing.
    """
    where = where or plugins.source
    here = f"{where} [plugins]"
    loaded: dict[str, LoadedPlugin] = {}
    owners: dict[str, str] = {}
    for wanted in plugins.enable:
        dist = _installed(wanted.distribution)
        if dist is None:
            raise _manifest(
                f"{here} enable {wanted.distribution!r}",
                f"the distribution {wanted.distribution!r} is enabled and not installed",
                f"install it (pip install {wanted.distribution}) or remove it from enable",
            )
        if wanted.pin is not None and dist.version != wanted.pin:
            raise _manifest(
                f"{here} enable {wanted.distribution!r}",
                f"enable pins version {wanted.pin} and {dist.version} is installed",
                f"install {wanted.distribution}=={wanted.pin}, or change the pin after a review",
            )
        entries = [e for e in dist.entry_points if e.group in GROUPS.values()]
        if not entries:
            raise _manifest(
                f"{here} enable {wanted.distribution!r}",
                f"{wanted.distribution!r} gives no NeuroEdge entry point; enabling it does nothing",
                "remove it from enable, or enable the distribution that has the plugin",
            )
        for entry in entries:
            kind = next(k for k, g in GROUPS.items() if g == entry.group)
            if kind not in IMPLEMENTED:
                raise _manifest(
                    f"{here} enable {wanted.distribution!r}",
                    f"its entry point {safe_name(entry.name)} is a {kind} plugin "
                    f"({entry.group}), which is not implemented yet: {LATER}",
                    "remove it from enable until that task lands",
                )
            if not CODE_NAME.fullmatch(entry.name):
                raise _manifest(
                    f"{here} enable {wanted.distribution!r}",
                    f"entry point {safe_name(entry.name)} does not match [a-z][a-z0-9_]{{0,31}}",
                    "ask the plugin's author to rename it",
                )
            if entry.name in owners:
                raise _manifest(
                    f"{here} enable",
                    f"{owners[entry.name]!r} and {wanted.distribution!r} both give the "
                    f"{kind} entry point {entry.name!r}: one name, one plugin",
                    "enable one of them",
                )
            owners[entry.name] = wanted.distribution
            loaded[entry.name] = _load(entry, kind, dist, wanted.distribution, plugins, here)
    unknown = sorted(set(plugins.config) - set(loaded))
    if unknown:
        raise _manifest(
            f"{here} config.{unknown[0]}",
            f"no enabled distribution gives the entry point {unknown[0]!r}",
            "enable its distribution, or remove the config",
        )
    return loaded


def _load(
    entry: metadata.EntryPoint,
    kind: str,
    dist: metadata.Distribution,
    name: str,
    plugins: PluginsConfig,
    here: str,
) -> LoadedPlugin:
    where = f"{here} {kind} {entry.name!r} ({name} {dist.version})"
    try:
        factory = entry.load()
    except Exception as problem:
        raise _manifest(
            where,
            f"the plugin does not import: {type(problem).__name__}: {problem}",
            "fix or reinstall the distribution, or remove it from enable",
        ) from None
    module = sys.modules.get(entry.module) or importlib.import_module(entry.module)
    required = getattr(module, "sdk_requires", None)
    if not sdk_compatible(required):
        raise _manifest(
            where,
            f"it asks for SDK {required!r} and this core has neuroedge.sdk {SDK_VERSION}: "
            "a plugin declares sdk_requires = (MAJOR, MINOR) with the same MAJOR and a MINOR "
            "not above this one",
            "install a version of the plugin built for this SDK, or a core that has its SDK",
        )
    check_factory(factory, where)
    editable = _editable(dist)
    record = PluginRecord(
        kind,
        entry.name,
        name,
        dist.version,
        None if editable else files_sha256(dist, entry.module, where),
        editable,
    )
    return LoadedPlugin(entry.name, kind, factory, record, plugins.config.get(entry.name, {}))


def check_factory(factory: Any, where: str) -> None:
    """`factory(config)`: callable with exactly one argument and nothing else (no handle)."""
    if not callable(factory):
        raise _manifest(where, "the entry point is not a factory", "point it at module:factory")
    try:
        signature = inspect.signature(factory)
    except (TypeError, ValueError):
        raise _manifest(
            where, "the factory's signature cannot be read", "def factory(config)"
        ) from None
    params = list(signature.parameters.values())
    positional = (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    if len(params) != 1 or params[0].kind not in positional:
        raise _manifest(
            where,
            f"the factory takes {signature}; it must take exactly one argument, the config "
            "mapping — a plugin receives nothing else (no HAL, ledger or envelope)",
            "write def factory(config: Mapping[str, Any]) -> Actuator",
        )


# --- the actuator kind -------------------------------------------------------------------------

_METHODS = {"apply": 1, "safe_off": 0, "read_state": 0, "probe": 0}


def check_actuator(made: Any, where: str) -> None:
    """
    What a factory returned is an `Actuator` (RFC-0018 §3c): the five attributes within the
    limits of §9.5, and the four methods callable with the arguments the HAL passes.
    """
    level = getattr(made, "safe_off_level", None)
    if level not in LEVELS:
        raise _manifest(where, f"safe_off_level is {level!r}, not one of {list(LEVELS)}", "fix it")
    readback = getattr(made, "readback", None)
    if readback not in READBACKS:
        raise _manifest(where, f"readback is {readback!r}, not one of {list(READBACKS)}", "fix it")
    for attribute, low, high in (
        ("tolerance_ms", 0, MAX_TOLERANCE_MS),
        ("command_timeout_ms", 1, MAX_COMMAND_TIMEOUT_MS),
    ):
        value = getattr(made, attribute, None)
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise _manifest(
                where,
                f"{attribute} is {value!r}; it must be a whole number from {low} to {high} ms "
                "(RFC-0018 §9.5)",
                "declare a value inside the limit, measured on the device",
            )
    lease = getattr(made, "max_lease_ms", "missing")
    if level == "L3":
        if isinstance(lease, bool) or not isinstance(lease, int) or lease <= 0:
            raise _manifest(where, f"an L3 plugin declares max_lease_ms > 0, not {lease!r}", "x")
    elif lease is not None:
        raise _manifest(where, f"max_lease_ms is {lease!r}; it is None below L3", "set it None")
    for method, arity in _METHODS.items():
        function = getattr(made, method, None)
        if not callable(function):
            raise _manifest(where, f"the actuator has no method {method}()", f"define {method}")
        try:
            inspect.signature(function).bind(*([None] * arity))
        except (TypeError, ValueError):
            raise _manifest(
                where,
                f"{method} cannot be called with {arity} argument(s), as the HAL calls it",
                "match the Actuator protocol of neuroedge.sdk",
            ) from None


def build_actuator(plugin: LoadedPlugin, config: Mapping[str, Any], where: str) -> Any:
    """
    One actuator from its plugin: ``factory(config)`` once, with a read-only copy of the plugin
    config merged under the declaration's own; a `ValueError` (or anything else it raises) is
    NE3002 three parts. The result is checked against the Protocol.
    """
    merged = MappingProxyType(copy.deepcopy({**plugin.config, **config}))
    try:
        made = plugin.factory(merged)
    except Exception as problem:
        raise _manifest(
            where,
            f"the plugin {plugin.name!r} refused its config: {type(problem).__name__}: {problem}",
            "fix [actuators.<name>.config] (or [plugins.config]) as the plugin documents it",
        ) from None
    check_actuator(made, where)
    return made
