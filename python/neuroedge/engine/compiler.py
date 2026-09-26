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
6. `[mcp]`, `[system_two]` and `[system_one]` are well formed — no API key in
   agent.toml — and every criterion `[system_one]` delegates to a model is one the
   agent's gates evaluate, with a budget longer than the model's `timeout_ms`.

On success it writes each gate's decision tree and canonical artifact.
"""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
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
from ..hal.board import PRIMITIVES, BoardProfile, load_board_by_id
from .canonical import gate_canonical_json, gate_digest
from .decision_tree import compile_tree, tree_bytes
from .gate_resolver import GateRegistry, ResolvedGate, resolve_gate_file, resolve_gate_uri


@dataclass(frozen=True)
class AgentManifest:
    name: str
    version: str
    requires: dict[str, dict[str, Any]]
    gates: dict[str, str]
    targets: tuple[str, ...]
    source: Path

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
    unknown = sorted(set(requires) - set(PRIMITIVES))
    if unknown:
        raise AgentManifestError(
            where=f"{path} -> [requires]",
            why=f"{unknown} are not HAL primitives; primitives are {list(PRIMITIVES)}",
            how="use the dotted primitive names from FR-HAL-01",
        )
    targets = document.get("targets", {}).get("supported", [])
    return AgentManifest(
        name=agent["name"],
        version=agent["version"],
        requires={key: dict(value) for key, value in requires.items()},
        gates=dict(document.get("gates", {})),
        targets=tuple(targets),
        source=path,
    )


# --- 2. [requires] against the board -------------------------------------------


def _describe(board: BoardProfile) -> str:
    offered = []
    for primitive in PRIMITIVES:
        if not board.supports(primitive):
            continue
        if primitive == "digital.out":
            offered.append(f"digital.out:{list(board.pins)}")
        elif primitive == "sensor.read":
            offered.append(f"sensor.read:{list(board.sensors)}")
        else:
            offered.append(primitive)
    return ", ".join(offered) or "nothing"


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
        elif primitive in ("digital.out", "sensor.read"):
            key, offered = (
                ("pins", board.pins) if primitive == "digital.out" else ("sensors", board.sensors)
            )
            for name in need.get(key, []):
                if name not in offered:
                    problems.append(
                        _mismatch(manifest, board, f"{primitive}:{name}", f"add {name!r} to {key}")
                    )
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
            key = {"digital.out": "pins", "sensor.read": "sensors"}.get(requirement.primitive)
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
    adapter it names can be imported, and each criterion it delegates to the model
    is evaluated by a gate whose budget outlasts `timeout_ms` (TSK-I4-02, FR-MDL-04).
    """
    from ..models.providers import load_adapter, load_system_one_config
    from ..models.system import FALLBACK_RESERVE_MS

    try:
        config = load_system_one_config(manifest)
        if config is not None and config.adapter is not None:
            load_adapter(config, manifest.root)
    except NeuroEdgeError as error:
        return [error]
    if config is None:
        return []
    where = f"{config.where} criteria"
    problems: list[NeuroEdgeError] = []
    for criterion in config.criteria:
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


def build(
    agent_toml: str | Path,
    *,
    target: str,
    board_id: str,
    out_dir: str | Path | None = None,
    registry: GateRegistry | None = None,
) -> BuildReport:
    """Check everything; raise `BuildFailed` with every problem, or write artifacts."""
    manifest = load_agent_manifest(agent_toml)
    board = load_board_by_id(board_id)
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
    problems += check_capabilities(manifest, board)
    actions = load_actions(manifest)
    problems += check_actions(manifest, actions)
    gates, gate_problems = resolve_gates(manifest, registry)
    problems += gate_problems
    problems += check_fallbacks(manifest, gates, actions)
    problems += check_gate_arguments(gates, actions)

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
    return report
