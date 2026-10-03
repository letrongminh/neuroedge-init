"""
Build-time capability check — `neuroedge build` (TSK-S2-02, FR-HAL-04/05, FR-ACE-04/05).

The board declares what it *has* (`boards/*.toml`); the agent declares what it
*needs* (`agent.toml [requires]` and each `@action`'s `requires`). The build
matches the two before anything runs on hardware, and collects **every**
problem so one run reports them all, each with where / why / how:

1. the manifest is well formed and supports the target;
2. each `[requires]` entry is met by the board (proposal Appendix A.1);
3. each `@action` asks only for what `[requires]` declares, and names a gate
   that `[gates]` declares;
4. every gate resolves (lint semantics) and compiles to a decision tree, and
   every `degrade` fallback names a declared action;
5. the command grammar (and `knowledge.toml`, if the agent ships one) loads,
   and every `action` a command names is a declared @action;
6. `[mcp]`, `[system_two]`, `[system_one]`, `[stt]` and `[tts]` are well formed — no
   API key in agent.toml — and every criterion `[system_one]` delegates to a model
   is one the agent's gates evaluate, with a budget longer than the model's `timeout_ms`.
7. for `esp32s3`, the agent links into the firmware (`firmware.firmware_problems`).

On success it writes each gate's decision tree and canonical artifact — and, for
`esp32s3`, the ESP-IDF project of the agent's firmware (`<out>/esp32s3/`, TSK-I3-01).
"""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import re
import sys
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import (
    AgentManifestError,
    BoardCapabilityError,
    BuildFailed,
    GateSchemaError,
    NeuroEdgeError,
)
from ..hal.audio import MAX_RATE_HZ, MIN_RATE_HZ, rate_ok
from ..hal.board import (
    ALL_PRIMITIVES,
    REFERENCE_BOARD,
    REFERENCE_BOARDS,
    REQUIRABLE_PRIMITIVES,
    BoardProfile,
    load_board_by_id,
)
from .canonical import gate_canonical_json, gate_digest
from .decision_tree import compile_tree, tree_bytes
from .gate_resolver import GateRegistry, ResolvedGate, resolve_gate_file, resolve_gate_uri

# An ISO-639-1 code is exactly two lowercase letters: "vi", "en". What the device
# UI ships is `firmware.UI_LANGUAGES`; `[stt] language` still accepts three
# letters on its own (perception/providers/config.py, another worker's file).
LANGUAGE = re.compile(r"^[a-z]{2}$")


def resolve_agent_language(
    agent_language: str | None, stt_language: str | None, source: Path
) -> str | None:
    """
    The one language the agent speaks: `[agent] language` when set, else a
    well-formed `[stt] language`, else None (the device UI then takes its
    default). Two different values stop the build on **every** target — a trace
    recorded from a session whose recognizer heard one language and whose screen
    showed another is not a trace of the same agent (docs/spec/ui.md §2).
    """
    if agent_language is not None and stt_language is not None and agent_language != stt_language:
        raise AgentManifestError(
            where=f"{source} -> [agent] language",
            why=f"language = {agent_language!r} but [stt] language = {stt_language!r}: the "
            "device UI and the recognizer would speak different languages",
            how=f"make the two equal, drop [stt] language and keep language = "
            f"{agent_language!r}, or drop [agent] language to follow [stt] "
            "(docs/spec/ui.md §Ngôn ngữ)",
        )
    return agent_language if agent_language is not None else stt_language


@dataclass(frozen=True)
class AgentManifest:
    name: str
    version: str
    requires: dict[str, dict[str, Any]]
    gates: dict[str, str]
    targets: tuple[str, ...]
    source: Path
    # The language the agent speaks: `[agent] language` else `[stt] language`,
    # resolved and conflict-checked at load for every target; None means the
    # device UI takes its default. The rule is docs/spec/ui.md §Ngôn ngữ.
    language: str | None = None

    @property
    def root(self) -> Path:
        return self.source.parent

    @property
    def label(self) -> str:
        return f"{self.name}@{self.version}"


def load_agent_manifest(path: str | Path) -> AgentManifest:
    path = Path(path)
    if not path.is_file():
        raise AgentManifestError(
            where=str(path),
            why="agent.toml does not exist",
            how="run the build from the agent project, or pass --agent <path/to/agent.toml>",
        )
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise AgentManifestError(
            where=str(path), why=f"not valid TOML: {exc}", how="repair the TOML syntax"
        ) from exc

    agent = document.get("agent", {})
    if not isinstance(agent.get("name"), str) or not isinstance(agent.get("version"), str):
        raise AgentManifestError(
            where=f"{path} -> [agent]",
            why="[agent] must declare string `name` and `version`",
            how='add name = "villa-concierge" and version = "0.1.0"',
        )
    requires = document.get("requires")
    if not isinstance(requires, dict):
        raise AgentManifestError(
            where=f"{path} -> [requires]",
            why="[requires] is missing; the build cannot match the agent against a board",
            how='declare what the agent needs, e.g. "digital.out" = { pins = ["door_lock"] }',
        )
    unknown = sorted(set(requires) - set(REQUIRABLE_PRIMITIVES))
    if unknown:
        raise AgentManifestError(
            where=f"{path} -> [requires]",
            why=f"{unknown} are not HAL primitives; primitives are {list(REQUIRABLE_PRIMITIVES)}",
            how="use the dotted primitive names from FR-HAL-01",
        )
    targets = document.get("targets", {}).get("supported", [])
    language = agent.get("language")
    if language is not None and (not isinstance(language, str) or not LANGUAGE.fullmatch(language)):
        raise AgentManifestError(
            where=f"{path} -> [agent] language",
            why=f"language = {language!r} is not an ISO-639-1 code: exactly two lowercase "
            'letters, such as "vi" or "en"',
            how='write language = "vi", or remove it; the device UI then takes [stt] '
            'language (default "vi") — docs/spec/ui.md §Ngôn ngữ',
        )
    # A `[stt] language` of another shape is parse_speech()'s to refuse; only a
    # string can take part in the conflict check here.
    stt = document.get("stt")
    stt_language = stt.get("language") if isinstance(stt, dict) else None
    if not isinstance(stt_language, str):
        stt_language = None
    return AgentManifest(
        name=agent["name"],
        version=agent["version"],
        requires={key: dict(value) for key, value in requires.items()},
        gates=dict(document.get("gates", {})),
        targets=tuple(targets),
        source=path,
        language=resolve_agent_language(language, stt_language, path),
    )


# --- 2. [requires] against the board -------------------------------------------


def _describe(board: BoardProfile) -> str:
    offered = []
    for primitive in ALL_PRIMITIVES:
        if not board.supports(primitive):
            continue
        if primitive == "digital.out":
            offered.append(f"digital.out:{list(board.pins)}")
        elif primitive == "sensor.read":
            offered.append(f"sensor.read:{list(board.sensors)}")
        elif primitive == "digital.in":
            offered.append(f"digital.in:{list(board.input_pins)}")
        elif primitive == "analog.in":
            offered.append(f"analog.in:{[channel['name'] for channel in board.analog_channels]}")
        elif primitive == "i2c":
            offered.append(f"i2c:{_i2c_devices(board)}")
        else:
            offered.append(primitive)
    return ", ".join(offered) or "nothing"


def _i2c_devices(board: BoardProfile) -> list[str]:
    """The `bus/device` names of the board's I2C allow-list."""
    return [f"{bus['id']}/{device['name']}" for bus in board.i2c_buses for device in bus["devices"]]


def _mismatch(manifest: AgentManifest, board: BoardProfile, need: str, fix: str) -> Exception:
    return BoardCapabilityError(
        where=f"{manifest.source} -> [requires] {need}",
        why=(
            f"board {board.id!r} ({board.source}) does not provide {need}; "
            f"it provides {_describe(board)}"
        ),
        how=f"{fix} in {board.source}, or remove it from [requires] in {manifest.source}",
    )


def check_capabilities(manifest: AgentManifest, board: BoardProfile) -> list[NeuroEdgeError]:
    problems: list[NeuroEdgeError] = []
    for primitive, need in manifest.requires.items():
        if not board.supports(primitive):
            problems.append(
                _mismatch(manifest, board, primitive, f"declare the {primitive} primitive")
            )
            continue
        has = board.capability(primitive)
        if primitive == "audio.in":
            if need.get("aec") and not has.get("aec"):
                problems.append(
                    _mismatch(manifest, board, "audio.in aec = true", "use a board with AEC")
                )
            if need.get("min_channels", 0) > has.get("channels", 0):
                problems.append(
                    _mismatch(
                        manifest,
                        board,
                        f"audio.in min_channels = {need['min_channels']}",
                        "raise channels",
                    )
                )
            if need.get("sample_rate_hz", 0) > has.get("sample_rate_hz", 0):
                problems.append(
                    _mismatch(
                        manifest,
                        board,
                        f"audio.in sample_rate_hz = {need['sample_rate_hz']}",
                        "raise sample_rate_hz",
                    )
                )
        elif primitive == "audio.out":
            if need.get("channels", 0) > has.get("channels", 0):
                problems.append(
                    _mismatch(
                        manifest,
                        board,
                        f"audio.out channels = {need['channels']}",
                        "raise channels",
                    )
                )
        elif primitive in ("digital.out", "sensor.read", "digital.in"):
            key, offered = {
                "digital.out": ("pins", board.pins),
                "sensor.read": ("sensors", board.sensors),
                "digital.in": ("pins", board.input_pins),
            }[primitive]
            names = need.get(key, [])
            if primitive == "digital.in" and not (
                isinstance(names, list) and all(isinstance(name, str) for name in names)
            ):
                problems.append(
                    AgentManifestError(
                        where=f"{manifest.source} -> [requires] digital.in",
                        why=f"`pins` must be a list of input pin names, found {names!r}",
                        how='write "digital.in" = { pins = ["door_contact_raw"] }',
                    )
                )
                continue
            for name in names:
                if name not in offered:
                    problems.append(
                        _mismatch(manifest, board, f"{primitive}:{name}", f"add {name!r} to {key}")
                    )
        elif primitive == "analog.in":
            problems += _check_analog_channels(manifest, board, need)
        elif primitive == "i2c":
            offered_devices = _i2c_devices(board)
            wanted = need.get("devices", [])
            if not isinstance(wanted, list) or not all(isinstance(n, str) for n in wanted):
                problems.append(
                    _mismatch(
                        manifest,
                        board,
                        f"i2c devices = {wanted!r}",
                        'write devices = ["i2c1/ina219"] (bus/device, as the board names them)',
                    )
                )
                wanted = []
            for name in wanted:
                if name not in offered_devices:
                    problems.append(
                        _mismatch(
                            manifest,
                            board,
                            f"i2c:{name}",
                            "declare the device under [[capabilities.i2c.buses.devices]]",
                        )
                    )
        elif primitive == "vision.in":
            problems += _check_vision_in(manifest, board, need)
        elif primitive == "display":
            for axis in ("width", "height"):
                wanted = need.get(f"min_{axis}", 0)
                if wanted > has.get(axis, 0):
                    problems.append(
                        _mismatch(
                            manifest,
                            board,
                            f"display min_{axis} = {wanted}",
                            f"raise display {axis}",
                        )
                    )
    return problems


def _check_analog_channels(
    manifest: AgentManifest, board: BoardProfile, need: Mapping[str, Any]
) -> list[NeuroEdgeError]:
    """
    `"analog.in" = { channels = ["adc0"] }`: each channel is one the board declares. A
    bare `analog.in` names no channel, so it would prove nothing about the board.
    """
    channels = need.get("channels")
    shape = (
        isinstance(channels, list)
        and bool(channels)
        and all(isinstance(name, str) for name in channels)
    )
    if not shape:
        return [
            AgentManifestError(
                where=f"{manifest.source} -> [requires] analog.in",
                why=f"`channels` must be a non-empty list of channel names, found {channels!r}",
                how='write "analog.in" = { channels = ["adc0"] }',
            )
        ]
    declared = [channel["name"] for channel in board.analog_channels]
    return [
        _mismatch(manifest, board, f"analog.in:{name}", f"add {name!r} to analog_in.channels")
        for name in channels
        if name not in declared
    ]


def _check_vision_in(
    manifest: AgentManifest, board: BoardProfile, need: Any
) -> list[NeuroEdgeError]:
    """
    `[requires] "vision.in"` is met when at least one mode of the board satisfies every bound
    (RFC-0012 §3b); otherwise the closest mode and what it misses are named (FR-HAL-05).
    """
    from ..hal.vision import Requirement, modes_of, nearest_mode, select_mode

    where = f"{manifest.source} -> [requires] vision.in"
    try:
        requirement = Requirement.parse(need, where)
    except NeuroEdgeError as error:
        return [error]
    modes = modes_of(board.capability("vision.in").get("modes", ()))
    if select_mode(modes, requirement) is not None:
        return []
    near = nearest_mode(modes, requirement)
    closest = f"; the closest mode, {near[0]}, misses {near[1]}" if near else ""
    return [
        BoardCapabilityError(
            where=where,
            why=(
                f"no camera mode of board {board.id!r} ({board.source}) meets {dict(need)}"
                f"{closest}; it declares {[str(m) for m in modes] or 'no mode'}"
            ),
            how=f"relax the bounds, add a mode to vision_in.modes in {board.source}, or build "
            "for a board whose camera does it",
        )
    ]


def default_board_hint(manifest: AgentManifest, board: BoardProfile) -> NeuroEdgeError:
    """
    The way out when `build` ran on a default board that does not satisfy `[requires]`:
    which other reference boards of the target do (RFC-0013 §3e). It names them and
    changes nothing: the build stays failed, and the user passes `--board` knowingly.
    """
    satisfying = [
        other
        for other in REFERENCE_BOARDS.get(board.target, ())
        if other != board.id and not check_capabilities(manifest, load_board_by_id(other))
    ]
    if satisfying:
        how = f"build with --board {satisfying[0]} (reference boards of {board.target} that satisfy [requires]: {satisfying})"
    else:
        how = (
            f"no reference board of {board.target} satisfies [requires] "
            f"({list(REFERENCE_BOARDS.get(board.target, ()))}); narrow [requires] in "
            f"{manifest.source}, or build for another target"
        )
    return BoardCapabilityError(
        where=f"{manifest.source} -> [requires] on the default board {board.id!r}",
        why=(
            f"no --board was given, so {board.id!r}, the default board of {board.target}, was "
            f"checked and does not satisfy [requires]; it provides {_describe(board)}"
        ),
        how=how,
    )


# --- 3. @action against the manifest -------------------------------------------


def load_actions(manifest: AgentManifest) -> list[Any]:
    """Import `actions/*.py` of the agent project and return their `ActionSpec`s."""
    from ..actions import REGISTRY

    folder = manifest.root / "actions"
    # The folder is part of the module name: two projects with the same agent
    # name (two `neuroedge new` runs) must not share one cached module.
    project = hashlib.sha256(str(folder.resolve()).encode()).hexdigest()[:8]
    for path in sorted(folder.glob("*.py")) if folder.is_dir() else []:
        module_name = f"neuroedge_agent_{manifest.name.replace('-', '_')}_{project}.{path.stem}"
        if module_name in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    root = str(folder.resolve())
    return [
        spec for spec in REGISTRY.values() if str(Path(spec.source_file).resolve()).startswith(root)
    ]


def check_actions(manifest: AgentManifest, actions: Iterable[Any]) -> list[NeuroEdgeError]:
    problems: list[NeuroEdgeError] = []
    for spec in actions:
        for requirement in spec.requires:
            declared = manifest.requires.get(requirement.primitive)
            key = {
                "digital.out": "pins",
                "sensor.read": "sensors",
                "digital.in": "pins",
                "i2c": "devices",
            }.get(requirement.primitive)
            missing = declared is None or (
                key is not None
                and requirement.name is not None
                and requirement.name not in declared.get(key, [])
            )
            if missing:
                problems.append(
                    AgentManifestError(
                        where=f"{spec.where} -> requires {requirement}",
                        why=f"action {spec.name!r} needs {requirement}, which [requires] does not declare",
                        how=f"add {requirement} to [requires] in {manifest.source}",
                    )
                )
        if spec.gate not in manifest.gates:
            problems.append(
                AgentManifestError(
                    where=f"{spec.where} -> gate {spec.gate!r}",
                    why=f"[gates] declares {sorted(manifest.gates)}, not {spec.gate!r}",
                    how=f'add {spec.gate} = "neuroedge://gates/..." to [gates] in {manifest.source}',
                )
            )
    return problems


# --- 4. gates ---------------------------------------------------------------------


def resolve_gates(
    manifest: AgentManifest, registry: GateRegistry | None = None
) -> tuple[dict[str, ResolvedGate], list[NeuroEdgeError]]:
    resolved: dict[str, ResolvedGate] = {}
    problems: list[NeuroEdgeError] = []
    for key, ref in manifest.gates.items():
        try:
            if ref.startswith("neuroedge://"):
                resolved[key] = resolve_gate_uri(ref, registry=registry)
            else:
                resolved[key] = resolve_gate_file(manifest.root / ref, registry=registry)
            compile_tree(resolved[key])
        except NeuroEdgeError as error:
            problems.append(error)
    return resolved, problems


def check_gate_arguments(
    gates: Mapping[str, ResolvedGate], actions: Iterable[Any]
) -> list[NeuroEdgeError]:
    """
    Every argument a gate limits is a parameter of the action it guards, with the
    same JSON type (RFC-0005). A limit on a name the action does not take would
    never be checked against anything the body uses.
    """
    from ..actions.tools import input_schema

    problems: list[NeuroEdgeError] = []
    for spec in actions:
        gate = gates.get(spec.gate)
        if gate is None or not gate.arguments:
            continue
        properties = input_schema(spec)["properties"]
        for name, limit in gate.arguments.items():
            where = f"{gate.name}@{gate.version} -> arguments.{name}"
            if name not in properties:
                problems.append(
                    GateSchemaError(
                        where=where,
                        why=f"@action {spec.name} has no parameter {name!r}; "
                        f"it takes {sorted(properties)}",
                        how=f"limit a parameter of {spec.name}, or rename the parameter",
                    )
                )
                continue
            declared = properties[name].get("type")
            if declared is not None and declared != limit["type"]:
                problems.append(
                    GateSchemaError(
                        where=where,
                        why=f"the gate limits {name} as {limit['type']}, "
                        f"but {spec.name} declares it {declared}",
                        how=f"declare type: {declared} in the gate, or change the annotation",
                    )
                )
    return problems


def numeric_sensor_fact_error(
    where: str, criterion: str, gate: ResolvedGate
) -> BoardCapabilityError | None:
    """
    The refusal of a `[sim.sensor_facts]` rule on a criterion `gate` evaluates as numeric, or None.

    `sensor.read` declares no unit and no scale, so it cannot feed a numeric criterion
    (RFC-0009 §3f). Shared by `neuroedge build` and by the session at load, so the two say the same.
    """
    definition = gate.evaluate.get(criterion)
    if definition is None or definition.get("type") != "numeric":
        return None
    return BoardCapabilityError(
        where=f"{where} -> [sim.sensor_facts] {criterion}",
        why=(
            f"gate {gate.name}@{gate.version} evaluates {criterion!r} as 'numeric', and primitive "
            "'sensor.read' declares no unit and no scale (RFC-0009 §3f)"
        ),
        how=(
            f"bind {criterion!r} to a channel with declared unit and range, or "
            "evaluate it as 'level' with bands"
        ),
    )


def check_sensor_facts(
    manifest: AgentManifest, gates: Mapping[str, ResolvedGate]
) -> list[NeuroEdgeError]:
    """No `[sim.sensor_facts]` rule feeds a numeric criterion (RFC-0009 §3f)."""
    sim = tomllib.loads(manifest.source.read_text(encoding="utf-8")).get("sim", {})
    rules = sim.get("sensor_facts", {}) if isinstance(sim, dict) else {}
    if not isinstance(rules, dict):
        return []
    problems: list[NeuroEdgeError] = []
    for criterion in rules:
        for gate in gates.values():
            error = numeric_sensor_fact_error(str(manifest.source), criterion, gate)
            if error is not None:
                problems.append(error)
    return problems


def analog_fact_channels(manifest: AgentManifest) -> dict[str, str]:
    """
    `[sim.analog_facts]`: ``line_voltage = { channel = "adc0" }`` binds a numeric criterion to
    an `analog.in` channel (RFC-0007 §3c, RFC-0009 §3f) — the criterion's value is the channel's
    reading, taken each time the gate facts are gathered. Returns criterion -> channel.
    """
    sim = tomllib.loads(manifest.source.read_text(encoding="utf-8")).get("sim", {})
    rules = sim.get("analog_facts", {}) if isinstance(sim, dict) else {}
    where = f"{manifest.source} -> [sim.analog_facts]"
    if not isinstance(rules, dict):
        raise AgentManifestError(
            where=where,
            why=f"[sim.analog_facts] must be a table of criterion = {{ channel = ... }}, found {rules!r}",
            how='write line_voltage = { channel = "adc0" }',
        )
    channels: dict[str, str] = {}
    for criterion, rule in rules.items():
        if (
            not isinstance(rule, dict)
            or set(rule) != {"channel"}
            or not isinstance(rule["channel"], str)
        ):
            raise AgentManifestError(
                where=f"{where} {criterion}",
                why=f"an analog fact is exactly `channel = <name>`, found {rule!r}",
                how=f'write {criterion} = {{ channel = "adc0" }}',
            )
        channels[criterion] = rule["channel"]
    return channels


def check_analog_facts(
    manifest: AgentManifest, board: BoardProfile, gates: Mapping[str, ResolvedGate]
) -> list[NeuroEdgeError]:
    """
    Every `[sim.analog_facts]` rule is a numeric criterion fed by a channel it fits
    (RFC-0007 §3c, RFC-0009 §3f). For each gate that evaluates the criterion:

    * it is `numeric` — a channel has a unit and a range, which a bool or a level has not;
    * its `unit` is the channel's, and the channel's `[min, max]` lies inside its `range`:
      a reading the channel can legitimately give is one the criterion can judge, and a
      criterion range wider than the channel is the only way the two can differ.

    A mismatch is `BoardCapabilityError` (NE3001), found here and not as a wrong verdict
    on the device. The channel is also one `[requires]` declares. (Tiering a numeric
    criterion into `on_block.confirms` is refused by the gate resolver for every numeric
    criterion, so a bound one cannot be waived by a person either.)
    """
    try:
        bound = analog_fact_channels(manifest)
    except AgentManifestError as error:
        return [error]
    required = manifest.requires.get("analog.in", {}).get("channels", [])
    required = required if isinstance(required, list) else []
    sensors = tomllib.loads(manifest.source.read_text(encoding="utf-8")).get("sim", {})
    sensor_rules = sensors.get("sensor_facts", {}) if isinstance(sensors, dict) else {}
    problems: list[NeuroEdgeError] = []
    for criterion, channel in bound.items():
        where = f"{manifest.source} -> [sim.analog_facts] {criterion}"
        if isinstance(sensor_rules, dict) and criterion in sensor_rules:
            problems.append(
                AgentManifestError(
                    where=where,
                    why=f"{criterion!r} is also a [sim.sensor_facts] rule, so two readings would feed it",
                    how="keep one source for the criterion",
                )
            )
            continue
        if channel not in required:
            problems.append(
                AgentManifestError(
                    where=where,
                    why=f"channel {channel!r} is not one [requires] declares for analog.in",
                    how=f'add "analog.in" = {{ channels = ["{channel}"] }} to [requires]',
                )
            )
            continue
        declared = next((c for c in board.analog_channels if c["name"] == channel), None)
        if declared is None:
            continue  # check_capabilities already names the channel the board lacks
        readers = [gate for gate in gates.values() if criterion in gate.evaluate]
        if not readers:
            problems.append(
                AgentManifestError(
                    where=where,
                    why=f"no gate of the agent evaluates {criterion!r}, so the reading would feed nothing",
                    how=f"name the rule after a numeric criterion of a gate, or remove {criterion}",
                )
            )
        for gate in readers:
            problems += _analog_binding_problems(where, criterion, declared, gate)
    return problems


def _analog_binding_problems(
    where: str, criterion: str, channel: Mapping[str, Any], gate: ResolvedGate
) -> list[NeuroEdgeError]:
    label = f"{gate.name}@{gate.version}"
    definition = gate.evaluate[criterion]
    if definition.get("type") != "numeric":
        return [
            BoardCapabilityError(
                where=where,
                why=(
                    f"gate {label} evaluates {criterion!r} as {definition.get('type')!r}, and an "
                    f"analog.in channel feeds only a 'numeric' criterion (RFC-0009 §3f)"
                ),
                how=f"evaluate {criterion!r} as numeric, with the unit and range of {channel['name']!r}",
            )
        ]
    problems: list[NeuroEdgeError] = []
    if definition.get("unit") != channel["unit"]:
        problems.append(
            BoardCapabilityError(
                where=where,
                why=(
                    f"gate {label} measures {criterion!r} in {definition.get('unit')!r}, and channel "
                    f"{channel['name']!r} reads in {channel['unit']!r}; the engine converts nothing"
                ),
                how=f"set unit: {channel['unit']} on {criterion!r} (the gate and its children)",
            )
        )
    low, high = definition["range"]["min"], definition["range"]["max"]
    if not (low <= channel["min"] and channel["max"] <= high):
        problems.append(
            BoardCapabilityError(
                where=where,
                why=(
                    f"channel {channel['name']!r} reads from {channel['min']} to {channel['max']} "
                    f"{channel['unit']}, which is not inside the range [{low}, {high}] gate {label} "
                    f"gives {criterion!r}"
                ),
                how=f"widen range of {criterion!r} to cover [{channel['min']}, {channel['max']}], "
                "or narrow the channel in the board profile",
            )
        )
    return problems


@dataclass(frozen=True)
class DigitalFact:
    """
    A gate fact read from an input line (`[sim.digital_facts]`, RFC-0007 §3a): the level
    itself, or whether it equals `equals` (``equals = false`` is the line low). RFC-0007 binds
    no criterion to a pin, so this is the smallest binding that fits: it follows
    `[sim.sensor_facts]`, which already binds sensors to criteria.
    """

    pin: str
    equals: bool | None = None

    def evaluate(self, level: bool) -> bool:
        return level if self.equals is None else level == self.equals


def parse_digital_facts(source: Path, sim: Mapping[str, Any]) -> dict[str, DigitalFact]:
    """`[sim.digital_facts]` as rules, or an `AgentManifestError` naming the one that is wrong."""
    table = sim.get("digital_facts", {})
    where = f"{source} -> [sim.digital_facts]"
    if not isinstance(table, dict):
        raise AgentManifestError(
            where=where,
            why=f"[sim.digital_facts] must be a table, found {table!r}",
            how='write [sim.digital_facts] with lines such as door_closed = { pin = "door_contact_raw" }',
        )
    rules: dict[str, DigitalFact] = {}
    for criterion, rule in table.items():
        if (
            not isinstance(rule, dict)
            or not isinstance(rule.get("pin"), str)
            or set(rule) - {"pin", "equals"}
            or ("equals" in rule and not isinstance(rule["equals"], bool))
        ):
            raise AgentManifestError(
                where=f"{where} {criterion}",
                why=(
                    "a digital fact needs a string `pin`, and optionally `equals = true` or "
                    f"`equals = false`, found {rule!r}"
                ),
                how=f'write {criterion} = {{ pin = "door_contact_raw" }}, or add equals = false for the line low',
            )
        rules[criterion] = DigitalFact(rule["pin"], rule.get("equals"))
    return rules


def parse_digital_levels(source: Path, sim: Mapping[str, Any]) -> dict[str, bool]:
    """`[sim.inputs]`: the level each input line starts at on `sim`."""
    table = sim.get("inputs", {})
    where = f"{source} -> [sim.inputs]"
    if not isinstance(table, dict):
        raise AgentManifestError(
            where=where,
            why=f"[sim.inputs] must be a table of pin = true|false, found {table!r}",
            how="write [sim.inputs] with lines such as door_contact_raw = true",
        )
    for pin, level in table.items():
        if not isinstance(level, bool):
            raise AgentManifestError(
                where=f"{where} {pin}",
                why=f"{level!r} is not a logic level",
                how=f"write {pin} = true (the line high) or {pin} = false",
            )
    return dict(table)


def parse_i2c_values(source: Path, sim: Mapping[str, Any]) -> list[tuple[str, str, int, int, int]]:
    """
    `[sim.i2c."i2c1/ina219"]`: what a read of a register returns on `sim`, as
    ``(bus, device, register, value, width)``. A line is ``"0x02" = 24000`` (one byte) or
    ``"0x02" = { value = 24000, width = 2 }`` (a 16-bit register, value in wire order).
    """
    table = sim.get("i2c", {})
    where = f"{source} -> [sim.i2c]"
    how = 'write [sim.i2c."i2c1/ina219"] with lines such as "0x02" = { value = 24000, width = 2 }'
    if not isinstance(table, dict):
        raise AgentManifestError(
            where=where, why=f"[sim.i2c] must be a table of tables, found {table!r}", how=how
        )
    values: list[tuple[str, str, int, int, int]] = []
    for name, registers in table.items():
        bus, slash, device = name.partition("/")
        if not slash or not bus or not device or not isinstance(registers, dict):
            raise AgentManifestError(
                where=f"{where} {name}",
                why=f"{name!r} is not a `bus/device` table of registers",
                how=how,
            )
        for key, entry in registers.items():
            entry = {"value": entry} if not isinstance(entry, dict) else dict(entry)
            try:
                register = int(key, 0)
            except ValueError:
                register = -1
            value, width = entry.get("value"), entry.get("width", 1)
            valid = (
                0 <= register <= 0xFF
                and set(entry) <= {"value", "width"}
                and width in (1, 2)
                and not isinstance(width, bool)
                and isinstance(value, int)
                and not isinstance(value, bool)
                and 0 <= value < 256**width
            )
            if not valid:
                raise AgentManifestError(
                    where=f"{where} {name} {key}",
                    why=(
                        f"{key!r} = {entry!r} is not a register (0..255) with an integer `value` "
                        "that fits `width` (1 or 2 bytes)"
                    ),
                    how=how,
                )
            values.append((bus, device, register, value, width))
    return values


def check_i2c_values(manifest: AgentManifest, board: BoardProfile) -> list[NeuroEdgeError]:
    """`[sim.i2c]` sets only registers the board lets an agent read, of devices `[requires]` lists."""
    sim = tomllib.loads(manifest.source.read_text(encoding="utf-8")).get("sim", {})
    if not isinstance(sim, dict) or "i2c" not in sim:
        return []
    try:
        values = parse_i2c_values(manifest.source, sim)
    except NeuroEdgeError as error:
        return [error]
    declared = manifest.requires.get("i2c", {}).get("devices", [])
    problems: list[NeuroEdgeError] = []
    for bus, device, register, _value, _width in values:
        where = f'{manifest.source} -> [sim.i2c."{bus}/{device}"] {register:#04x}'
        found = next((b for b in board.i2c_buses if b["id"] == bus), None)
        entry = next((d for d in found["devices"] if d["name"] == device), None) if found else None
        if entry is None or register not in entry.get("readable_registers", ()):
            problems.append(
                BoardCapabilityError(
                    where=where,
                    why=(
                        f"board {board.id!r} lets an agent read no register {register:#04x} of "
                        f"{bus}/{device}; the simulator serves only what `linux` would allow"
                    ),
                    how="set a register in readable_registers of that device, or remove the line",
                )
            )
        elif f"{bus}/{device}" not in declared:
            problems.append(
                AgentManifestError(
                    where=where,
                    why=f"[requires] i2c does not list {bus}/{device}",
                    how=f'add "{bus}/{device}" to "i2c" = {{ devices = [...] }} in {manifest.source}',
                )
            )
    return problems


def check_digital_facts(
    manifest: AgentManifest, gates: Mapping[str, ResolvedGate], board: BoardProfile
) -> list[NeuroEdgeError]:
    """
    Every `[sim.digital_facts]` rule reads a pin the board declares *and* `[requires]` lists,
    and feeds a criterion that some gate evaluates and that every gate evaluating it declares
    `bool` — a level is a bool fact, never a number, a level or an option (RFC-0007 §3a).
    `[sim.inputs]` sets only declared pins.
    """
    sim = tomllib.loads(manifest.source.read_text(encoding="utf-8")).get("sim", {})
    if not isinstance(sim, dict):
        return []
    try:
        rules = parse_digital_facts(manifest.source, sim)
        levels = parse_digital_levels(manifest.source, sim)
    except NeuroEdgeError as error:
        return [error]
    declared = manifest.requires.get("digital.in", {}).get("pins", [])
    problems: list[NeuroEdgeError] = []
    for pin in levels:
        try:
            board.require_input_pin(pin, called_from=f"{manifest.source} -> [sim.inputs]")
        except BoardCapabilityError as error:
            problems.append(error)
    for criterion, rule in rules.items():
        where = f"{manifest.source} -> [sim.digital_facts] {criterion}"
        try:
            board.require_input_pin(rule.pin, called_from=where)
        except BoardCapabilityError as error:
            problems.append(error)
        sensor_rules = sim.get("sensor_facts", {})
        if isinstance(sensor_rules, dict) and criterion in sensor_rules:
            problems.append(
                AgentManifestError(
                    where=where,
                    why=f"{criterion!r} is also a [sim.sensor_facts] rule: one criterion, one source",
                    how="keep the rule of the line or the rule of the sensor, not both",
                )
            )
        if rule.pin not in declared:
            problems.append(
                AgentManifestError(
                    where=where,
                    why=f"the fact reads input pin {rule.pin!r}, which [requires] digital.in does not declare",
                    how=f'add {rule.pin!r} to "digital.in" = {{ pins = [...] }} in {manifest.source}',
                )
            )
        readers = [gate for gate in gates.values() if criterion in gate.evaluate]
        if not readers:
            problems.append(
                AgentManifestError(
                    where=where,
                    why=f"no gate of the agent evaluates {criterion!r}, so nothing would read this line",
                    how=f"name the fact after the gate's `bool` criterion, or remove {criterion}",
                )
            )
        for gate in readers:
            declared_type = gate.evaluate[criterion].get("type")
            if declared_type != "bool":
                problems.append(
                    AgentManifestError(
                        where=where,
                        why=(
                            f"gate {gate.name}@{gate.version} evaluates {criterion!r} as "
                            f"{declared_type!r}, and a digital.in level is a bool fact (RFC-0007 §3a)"
                        ),
                        how=f"evaluate {criterion!r} as `bool` in the gate",
                    )
                )
    return problems


def check_fallbacks(
    manifest: AgentManifest, gates: Mapping[str, ResolvedGate], actions: Iterable[Any]
) -> list[NeuroEdgeError]:
    declared = {spec.name: spec for spec in actions}
    problems: list[NeuroEdgeError] = []
    for key, gate in gates.items():
        fallback = gate.on_block.get("fallback_action")
        if gate.on_block.get("action") != "degrade":
            continue
        if fallback in declared:
            try:
                inspect.signature(declared[fallback].fn).bind()
            except TypeError:
                problems.append(
                    AgentManifestError(
                        where=f"{declared[fallback].where} -> {fallback}",
                        why="a degrade fallback is called with no arguments, but this action requires some",
                        how="give every parameter of the fallback action a default value",
                    )
                )
            continue
        problems.append(
            AgentManifestError(
                where=f"{manifest.source} -> [gates] {key} -> on_block.fallback_action",
                why=f"gate {gate.name}@{gate.version} degrades to {fallback!r}, which is not an @action here",
                how=f"define @action(name={fallback!r}, ...) in actions/, or change the gate",
            )
        )
    return problems


# --- 5. the command grammar -------------------------------------------------------


def check_mcp_servers(manifest: AgentManifest, actions: Iterable[Any]) -> list[NeuroEdgeError]:
    """
    `[mcp]` of agent.toml is well formed, and no external tool name
    (`server__tool`) shadows one of the agent's @actions (Q-27).
    """
    from ..mcp_host import load_mcp_config

    try:
        config = load_mcp_config(manifest)
    except NeuroEdgeError as error:
        return [error]
    declared = {spec.name for spec in actions}
    return [
        AgentManifestError(
            where=f"{manifest.source} -> [mcp.servers.{server.name}] tools",
            why=f"external tool {server.tool_name(tool)!r} has the name of an @action; "
            "a device action must never be reachable through an external server",
            how="rename the server table or the @action",
        )
        for server in config.servers
        for tool in server.tools
        if server.tool_name(tool) in declared
    ]


def check_system_two(manifest: AgentManifest) -> list[NeuroEdgeError]:
    """
    `[system_two]` of agent.toml is well formed — never an API key in it — and a
    custom adapter it names can be imported (TSK-S2-11, Q-10, Q-12).
    """
    from ..models.providers import load_adapter, load_system_two_config

    try:
        config = load_system_two_config(manifest)
        if config is not None and config.adapter is not None:
            load_adapter(config, manifest.root)
    except NeuroEdgeError as error:
        return [error]
    return []


def check_system_one(
    manifest: AgentManifest, gates: Mapping[str, ResolvedGate]
) -> list[NeuroEdgeError]:
    """
    `[system_one]` of agent.toml is well formed — never an API key in it — a custom
    adapter it names can be imported, and each criterion it delegates to the model:

    * is evaluated by a gate, as a question the System One API can ask;
    * is not one the agent computes itself (`[sim.facts]`, `[sim.slot_facts]`,
      `[sim.sensor_facts]`): session state — identity, a booking, a reading — is never
      a model's judgment of what a person said, and when the computation leaves it
      undecided (a slot the guest did not say) the gate must block, not ask a model;
    * has a gate budget that outlasts `timeout_ms` and the grammar after it.

    (TSK-I4-02, FR-MDL-04.)
    """
    from ..models.providers import load_adapter, load_system_one_config
    from ..models.providers.systemone_api import question_for
    from ..models.system import FALLBACK_RESERVE_MS
    from .verdict import Unavailable

    try:
        config = load_system_one_config(manifest)
        if config is not None and config.adapter is not None:
            load_adapter(config, manifest.root)
    except NeuroEdgeError as error:
        return [error]
    if config is None:
        return []
    where = f"{config.where} criteria"
    sim = tomllib.loads(manifest.source.read_text(encoding="utf-8")).get("sim", {})
    sim = sim if isinstance(sim, dict) else {}
    computed = {
        f"sim.{table}": set(sim[table])
        for table in ("facts", "slot_facts", "sensor_facts", "analog_facts")
        if isinstance(sim.get(table), dict)
    }
    vision = tomllib.loads(manifest.source.read_text(encoding="utf-8")).get("vision")
    if isinstance(vision, dict) and isinstance(vision.get("facts"), dict):
        computed["vision.facts"] = set(vision["facts"])  # what the camera sees is not what is said
    problems: list[NeuroEdgeError] = []
    for criterion in config.criteria:
        owners = [table for table, names in computed.items() if criterion in names]
        if owners:
            problems.append(
                AgentManifestError(
                    where=where,
                    why=f"{criterion!r} is computed by the agent ([{owners[0]}]); a model must "
                    "never decide it from what a person said — and where the computation leaves "
                    "it undecided (a room the guest did not say), the gate has to block",
                    how=f"remove {criterion!r} from [system_one] criteria. Delegate only what the "
                    "words alone settle; identity, authorization and booking criteria "
                    "(guest_authenticated, staff_co_authorized, room_matches) are session "
                    "facts from the property system",
                )
            )
            continue
        using = [(key, gate) for key, gate in gates.items() if criterion in gate.evaluate]
        if not using:
            evaluated = sorted({name for gate in gates.values() for name in gate.evaluate})
            problems.append(
                AgentManifestError(
                    where=where,
                    why=f"no gate of this agent evaluates {criterion!r}; they evaluate {evaluated}",
                    how="list only criteria of the agent's gates, and check the spelling",
                )
            )
            continue
        for key, gate in using:
            question = question_for(gate.evaluate[criterion])
            if isinstance(question, Unavailable):
                problems.append(
                    AgentManifestError(
                        where=where,
                        why=f"gate {key!r} defines {criterion!r} in a way the System One API "
                        f"cannot ask: {question.detail}",
                        how=f"fix {criterion!r} in the gate, or remove it from [system_one] criteria",
                    )
                )
            p95 = gate.budget.get("p95_latency_ms")
            if isinstance(p95, int | float) and config.timeout_ms + FALLBACK_RESERVE_MS > p95:
                room = p95 - FALLBACK_RESERVE_MS
                raise_budget = f"raise the budget of {key!r} for a cloud round trip"
                problems.append(
                    AgentManifestError(
                        where=f"{config.where} timeout_ms",
                        why=f"gate {key!r} gives all of its facts {p95:g} ms "
                        f"(budget.p95_latency_ms), but the model may take {config.timeout_ms:g} "
                        f"ms for {criterion!r} and the grammar needs {FALLBACK_RESERVE_MS:g} ms "
                        "after it — the gate would cut the model off first",
                        how=f"lower timeout_ms to {room:g} or less, or {raise_budget}"
                        if room > 0
                        else raise_budget,
                    )
                )
    return problems


def check_vision(
    manifest: AgentManifest, gates: Mapping[str, ResolvedGate]
) -> list[NeuroEdgeError]:
    """
    `[vision]` of agent.toml (RFC-0012 §3c, §8; Q-54): the table is well formed, the agent declares
    the primitive it reads (`vision.in` — a board without it fails the capability check, not
    mid-conversation), the model it names can be found, and each fact meets the gates that read it:

    * the criterion of the same name has the type its `kind` gives it (`present` → `bool`,
      `count` and `confidence` → `numeric`);
    * no gate puts `confidence_gte` on a vision fact — one road for confidence, the `numeric`
      criterion, so there is no second threshold to forget to lock;
    * a gate that uses `present` or `count` of a label and zone also has the `numeric` `confidence`
      of the same label and zone in its `allow_when` (`facts.unpaired`): a `bool` has no
      `max_age_ms`, so without that pair a camera repeating "nobody there" would pass
      `present: false`;
    * some gate reads the fact (a fact nothing reads is a typo that would block silently).

    A gate may not give a vision criterion to a model that reads words (`check_system_one`).
    Every problem is reported.
    """
    from types import SimpleNamespace

    from ..models.providers import load_adapter
    from ..perception.vision import BUILTIN, parse_vision, unpaired

    document = tomllib.loads(manifest.source.read_text(encoding="utf-8"))
    if "vision" not in document:
        return []
    try:
        config = parse_vision(document["vision"], manifest.source)
        if config.adapter is not None:
            load_adapter(config, manifest.root)
    except NeuroEdgeError as error:
        return [error]
    where = config.where
    problems: list[NeuroEdgeError] = []
    if "vision.in" not in manifest.requires:
        problems.append(
            AgentManifestError(
                where=f"{manifest.source} -> [requires]",
                why="[vision] reads frames through vision.in, which [requires] does not declare",
                how='add "vision.in" = { min_width = 640, min_height = 480 } to [requires], or '
                "remove [vision]",
            )
        )
    if config.provider is None or (config.adapter is None and config.provider not in BUILTIN):
        problems.append(
            AgentManifestError(
                where=f"{where} provider",
                why="[vision] does not name a model that can be built"
                if config.provider is None
                else f"no built-in vision model is named {config.provider!r}; built in: {sorted(BUILTIN)}",
                how='add provider = "replay" (a scripted model) or "python:my_vision.adapter:make"',
            )
        )
    for name, spec in config.facts.items():
        readers = [(key, gate) for key, gate in gates.items() if name in gate.evaluate]
        if not readers:
            problems.append(
                AgentManifestError(
                    where=f"{where}.facts.{name}",
                    why=f"no gate of this agent evaluates {name!r}, so nothing reads this fact",
                    how="name the fact after the criterion of the gate that uses it, or remove it",
                )
            )
        for key, gate in readers:
            declared = gate.evaluate[name].get("type")
            if declared != spec.criterion_type:
                problems.append(
                    AgentManifestError(
                        where=f"{where}.facts.{name}",
                        why=f"gate {key!r} evaluates {name!r} as {declared!r}, and kind "
                        f"{spec.kind!r} is a {spec.criterion_type!r} criterion",
                        how=f"declare {name!r} as {spec.criterion_type!r} in the gate, or change kind",
                    )
                )
    for key, gate in gates.items():
        tree = compile_tree(gate)
        nodes = {node["criterion"]: node for node in tree["nodes"]}
        for name in config.facts.keys() & nodes.keys():
            if nodes[name].get("confidence_floor", 0.0) > 0:
                problems.append(
                    AgentManifestError(
                        where=f"gate {key!r} -> allow_when.{name}",
                        why=f"{name!r} is a vision fact, and the gate gives it `confidence_gte`: "
                        "the camera's confidence is a `numeric` criterion of the gate, never a "
                        "second threshold (RFC-0012 §3c, §9.3)",
                        how=f"remove confidence_gte, and lock the threshold with the numeric "
                        f"confidence criterion of {config.facts[name].label!r}",
                    )
                )
        readings = {
            name: SimpleNamespace(spec=config.facts[name])
            for name in config.facts.keys() & nodes.keys()
        }
        for name in sorted(unpaired(readings, tree)):
            spec = config.facts[name]
            problems.append(
                AgentManifestError(
                    where=f"gate {key!r} -> allow_when.{name}",
                    why=f"{name!r} is a {spec.kind!r} of {spec.label!r} in zone {spec.zone!r}, and "
                    "the gate has no numeric `confidence` criterion of the same label and zone "
                    "in allow_when: a bool has no max_age_ms, so a frozen camera repeating "
                    f"'nobody there' would pass (RFC-0012 §3c, §9.10)",
                    how=f"add a `confidence` fact for {spec.label!r} in {spec.zone!r} and a numeric "
                    "criterion for it to allow_when, with a max_age_ms",
                )
            )
    return problems


def check_speech(
    manifest: AgentManifest, board: BoardProfile | None = None
) -> list[NeuroEdgeError]:
    """
    `[stt]` and `[tts]` of agent.toml are well formed — never an API key in them,
    never a key over plain http to another machine — a custom adapter they name
    can be imported, and the agent declares the primitive each one needs: STT
    hears through `audio.in`, TTS speaks through `audio.out`, so a board without
    them fails here, not mid-conversation (TSK-S3-13, FR-MDL-09, Q-12). With a
    `board` that declares the primitive, it must also give its `sample_rate_hz`: PCM
    audio has no meaning without one. Every bad table is reported.
    """
    from ..models.providers import load_adapter
    from ..perception.providers.config import ROLES, parse_speech

    document = tomllib.loads(manifest.source.read_text(encoding="utf-8"))
    problems: list[NeuroEdgeError] = []
    for role in ROLES:
        if role not in document:
            continue
        primitive = "audio.in" if role == "stt" else "audio.out"
        if primitive not in manifest.requires:
            example = "{ sample_rate_hz = 16000 }" if role == "stt" else "{}"
            problems.append(
                AgentManifestError(
                    where=f"{manifest.source} -> [requires]",
                    why=f"[{role}] needs {primitive}, which [requires] does not declare",
                    how=f'add "{primitive}" = {example} to [requires], or remove [{role}]',
                )
            )
        elif board is not None and board.supports(primitive):
            rate = board.capability(primitive).get("sample_rate_hz")
            # The rates the audio path runs at (8–96 kHz); outside them PCM is refused at
            # run time, so the build says so first.
            if not rate_ok(rate):
                low, high = MIN_RATE_HZ, MAX_RATE_HZ
                problems.append(
                    BoardCapabilityError(
                        where=f"{board.source} -> {primitive}",
                        why=f"[{role}] plays PCM through {primitive}, and board {board.id!r} "
                        f"declares no sample_rate_hz for it from {low} to {high} Hz",
                        how=f"add sample_rate_hz = 16000 to {primitive} in {board.source}",
                    )
                )
        try:
            config = parse_speech(role, document[role], manifest.source)
            for table in (config, config.fallback):
                if table is not None and table.adapter is not None:
                    load_adapter(table, manifest.root)
        except NeuroEdgeError as error:
            problems.append(error)
    return problems


def check_wake_word(
    manifest: AgentManifest, board: BoardProfile | None = None
) -> list[NeuroEdgeError]:
    """
    `[wake_word]` of agent.toml is well formed (TSK-I4-01, FR-PER-01, Q-7): a
    provider that is openWakeWord or a `python:` adapter, the three model paths for
    the builtin provider (their *files* may live on the device, so a build checks
    the table's shape only — a voice session checks the files before any line),
    a threshold in (0, 1], and the primitive it needs declared: a detector reads
    `audio.in`, whose rate the board must declare (8–96 kHz), so a board without it
    fails here, not when the session starts. A table with no wake word at all is
    fine: a turn opens on VAD (T01). Every bad table is reported.
    """
    from ..models.providers import load_adapter
    from ..perception.providers.config import parse_wake_word

    document = tomllib.loads(manifest.source.read_text(encoding="utf-8"))
    if "wake_word" not in document:
        return []
    problems: list[NeuroEdgeError] = []
    if "audio.in" not in manifest.requires:
        problems.append(
            AgentManifestError(
                where=f"{manifest.source} -> [requires]",
                why="[wake_word] hears frames through audio.in, which [requires] does not declare",
                how='add "audio.in" = { sample_rate_hz = 16000 } to [requires], or remove '
                "[wake_word] (a turn then opens on VAD, T01)",
            )
        )
    elif board is not None and not board.supports("audio.in"):
        problems.append(
            BoardCapabilityError(
                where=f"{board.source} -> audio.in",
                why=f"[wake_word] reads audio.in, and board {board.id!r} does not declare it",
                how=f"add a [capabilities.audio_in] section to {board.source}, or remove [wake_word]",
            )
        )
    elif board is not None:
        rate = board.capability("audio.in").get("sample_rate_hz")
        if not rate_ok(rate):
            problems.append(
                BoardCapabilityError(
                    where=f"{board.source} -> audio.in",
                    why=f"[wake_word] reads PCM through audio.in, and board {board.id!r} declares "
                    f"no sample_rate_hz for it from {MIN_RATE_HZ} to {MAX_RATE_HZ} Hz",
                    how=f"add sample_rate_hz = 16000 to audio.in in {board.source}",
                )
            )
    if board is not None and board.target == "esp32s3":
        # Q-7 plans microWakeWord on Box-3; the device runtime has no detector yet, and
        # accepting the table would let a firmware build silently ignore the wake word.
        problems.append(
            AgentManifestError(
                where=f"{manifest.source} -> [wake_word]",
                why="the esp32s3 runtime has no wake-word detector yet (Q-7: microWakeWord on "
                "Box-3), so a build would silently ignore this table",
                how="use [wake_word] on sim or linux, or remove it for esp32s3",
            )
        )
    try:
        config = parse_wake_word(document["wake_word"], manifest.source, manifest.root)
        if config.adapter is not None:
            load_adapter(config, manifest.root)
    except NeuroEdgeError as error:
        problems.append(error)
    return problems


def check_commands(grammar: Any, actions: Iterable[Any]) -> list[NeuroEdgeError]:
    """
    Every `tool` a command calls is a declared @action, and its slot-mapped and
    default arguments fit that tool's schema (Q-24).
    """
    from ..actions.tools import input_schema

    declared = {spec.name: spec for spec in actions}
    problems: list[NeuroEdgeError] = []
    for index, command in enumerate(grammar.commands):
        if command.tool is None:
            continue
        where = f"{grammar.source} -> command[{index}] ({command.intent})"
        spec = declared.get(command.tool)
        if spec is None:
            problems.append(
                AgentManifestError(
                    where=f"{where}.tool",
                    why=f"{command.tool!r} is not an @action of this agent; it has {sorted(declared)}",
                    how=f"define @action(name={command.tool!r}, ...) in actions/, or fix the name",
                )
            )
            continue
        properties = input_schema(spec)["properties"]
        for field_name, names in (
            ("arguments", command.arguments),
            ("default_args", command.default_args),
        ):
            unknown = sorted(set(names) - set(properties))
            if unknown:
                problems.append(
                    AgentManifestError(
                        where=f"{where}.{field_name}",
                        why=f"{spec.name} has no parameter(s) {unknown}; it takes {sorted(properties)}",
                        how=f"use only parameters of {spec.name}",
                    )
                )
        from ..actions.tools import check_arguments

        _, bad = check_arguments(
            spec, {**dict.fromkeys(spec_required(spec), "x"), **command.default_args}
        )
        for problem in bad:
            if problem.startswith("argument "):
                problems.append(
                    AgentManifestError(
                        where=f"{where}.default_args",
                        why=problem,
                        how=f"give {spec.name} a value of the declared type",
                    )
                )
    return problems


def spec_required(spec: Any) -> list[str]:
    from ..actions.tools import input_schema

    return list(input_schema(spec).get("required", []))


# --- the build -------------------------------------------------------------------


@dataclass
class BuildReport:
    agent: str
    target: str
    board: str
    actions: int
    gates: int
    requirements: int
    artifacts: list[Path] = field(default_factory=list)
    # esp32s3: the ESP-IDF project written for the agent, and how many files it has.
    firmware: Path | None = None
    firmware_files: int = 0


def build(
    agent_toml: str | Path,
    *,
    target: str,
    board_id: str | None = None,
    out_dir: str | Path | None = None,
    registry: GateRegistry | None = None,
) -> BuildReport:
    """
    Check everything; raise `BuildFailed` with every problem, or write artifacts.

    `board_id` None builds on the target's default board. It is never replaced by another
    board that would fit: the user must know which board they flash (RFC-0013 §3e).
    """
    manifest = load_agent_manifest(agent_toml)
    explicit_board = board_id is not None
    board = load_board_by_id(board_id or REFERENCE_BOARD.get(target, "esp32s3-box-3"))
    problems: list[NeuroEdgeError] = []

    if manifest.targets and target not in manifest.targets:
        problems.append(
            AgentManifestError(
                where=f"{manifest.source} -> [targets] supported",
                why=f"the agent supports {list(manifest.targets)}, not {target!r}",
                how=f"add {target!r} to [targets] supported, or build for a supported target",
            )
        )
    if board.target != target:
        problems.append(
            BoardCapabilityError(
                where=f"--board {board.id}",
                why=f"board {board.id!r} targets {board.target!r}, not {target!r}",
                how=f"pick a {target} board, or build with --target {board.target}",
            )
        )
    capability_problems = check_capabilities(manifest, board)
    problems += capability_problems
    if capability_problems and not explicit_board:
        problems.append(default_board_hint(manifest, board))
    actions = load_actions(manifest)
    problems += check_actions(manifest, actions)
    gates, gate_problems = resolve_gates(manifest, registry)
    problems += gate_problems
    problems += check_fallbacks(manifest, gates, actions)
    problems += check_gate_arguments(gates, actions)
    problems += check_sensor_facts(manifest, gates)
    problems += check_analog_facts(manifest, board, gates)
    problems += check_digital_facts(manifest, gates, board)
    problems += check_i2c_values(manifest, board)

    grammar = manifest.root / "commands.toml"
    if grammar.is_file():
        from ..models.knowledge import load_agent_grammar

        try:
            problems += check_commands(load_agent_grammar(manifest.root)[0], actions)
        except NeuroEdgeError as error:
            problems.append(error)
    problems += check_mcp_servers(manifest, actions)
    problems += check_system_two(manifest)
    problems += check_system_one(manifest, gates)
    problems += check_vision(manifest, gates)
    problems += check_speech(manifest, board)
    problems += check_wake_word(manifest, board)
    project: Path | None = None
    if target == "esp32s3":
        from . import firmware

        problems += firmware.firmware_problems(manifest, gates)
        if out_dir is not None:
            project = Path(out_dir) / firmware.PROJECT_DIR
            problem = firmware.project_problem(project)
            if problem is not None:
                problems.append(problem)

    if problems:
        raise BuildFailed(where=f"{manifest.label} for {target} on {board.id}", problems=problems)

    report = BuildReport(
        agent=manifest.label,
        target=target,
        board=board.id,
        actions=len(actions),
        gates=len(gates),
        requirements=len(manifest.requires),
    )
    if out_dir is not None:
        # Rendered before anything is written: a failure here leaves `out_dir` as it was.
        project_files: dict[str, bytes] = {}
        if project is not None:
            from . import firmware

            project_files = firmware.render_project(manifest, board.id, gates, actions)
        folder = Path(out_dir) / "gates"
        folder.mkdir(parents=True, exist_ok=True)
        from .binary_tree import c_header, encode

        for key, gate in gates.items():
            tree = compile_tree(gate)
            tree_path = folder / f"{key}.tree.json"
            tree_path.write_bytes(tree_bytes(tree))
            artifact_path = folder / f"{gate_digest(gate).removeprefix('sha256:')}.json"
            artifact_path.write_bytes(gate_canonical_json(gate))
            # The device's form of the same tree (Q-23, RFC-0003): NETR v1 bytes, and a
            # C header that links them into the firmware image as const (flash).
            binary_path = folder / f"{key}.netree"
            binary_path.write_bytes(encode(tree))
            header_path = folder / f"{key}.netree.h"
            header_path.write_text(c_header(tree, key), encoding="utf-8")
            report.artifacts += [tree_path, artifact_path, binary_path, header_path]
        if project is not None:
            from . import firmware

            firmware.write_project(project, project_files)
            report.firmware, report.firmware_files = project, len(project_files)
    return report
