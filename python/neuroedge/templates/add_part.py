"""
`neuroedge add part` (VP-PT-07, VP-PT-09, docs/spec/virtual_parts.md): one part of the catalogue
into an agent project.

A part is `[sim.parts.<name>]` and the `[requires]` entry it is wired to; an output kind also
arrives with an action, a fail-closed gate and a two-way test, made by the `add action` recipe of
`templates/add.py`, and a sensor kind with `--drives <pin>` by the `add sensor` recipe. The edits
are planned in memory like any `add`, so a step that fails changes no file. The part's target must
be on the project's board: a board that lacks it is refused with the two ways on, and the command
never switches the board itself (VP-PT-09).
"""

from __future__ import annotations

import keyword
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..errors import NeuroEdgeError
from ..hal.board import BoardProfile, load_board_by_id
from ..hal.virtual_board import VIRTUAL_BOARD
from ..sim.parts import REQUIRES_KEY, Kind, catalogue
from . import NAME
from .add import (
    COPY_IGNORE,
    RESERVED,
    SENSORS,
    Edit,
    Plan,
    _as_project,
    _board_for,
    _read_toml,
    _refuse,
    _write,
    edit_manifest,
    plan_add,
)


def _board_lacks(board: BoardProfile, kind: Kind, target: str | None) -> list[str] | None:
    """None when the board has the target; else the names it does offer for the kind's primitive."""
    offered: dict[str, list[str]] = {
        "digital.out": list(board.pins),
        "digital.in": list(board.input_pins),
        "sensor.read": list(board.sensors),
        "analog.in": [channel["name"] for channel in board.analog_channels],
        "motion": [channel["name"] for channel in board.motion_channels],
    }
    if kind.primitive == "display":
        return None if board.supports("display") else []
    names = offered[kind.primitive]
    return None if target in names else names


def plan_part(
    project: Path,
    part_kind: str,
    name: str,
    *,
    pin: str | None = None,
    sensor: str | None = None,
    channel: str | None = None,
    drives: str | None = None,
    label: str | None = None,
    board: str | None = None,
    manifest: str = "agent.toml",
) -> Plan:
    """The files `add part` writes, planned in memory; raises `AgentManifestError` if it cannot."""
    where = f"neuroedge add part {part_kind} {name}"
    kinds = catalogue()
    kind = kinds.get(part_kind)
    if kind is None:
        raise _refuse(
            where,
            f"unknown kind {part_kind!r}; the catalogue has {list(kinds)}",
            "pick one of them (neuroedge add part --list shows what each is)",
        )
    given = {
        key: value
        for key, value in (("pin", pin), ("sensor", sensor), ("channel", channel))
        if value
    }
    if kind.target is None or kind.target not in given or len(given) > 1:
        wired = (
            f"it is wired with --{kind.target}"
            if kind.target
            else "it has no pin, sensor or channel"
        )
        raise _refuse(
            where,
            f"a {kind.name} is {kind.primitive}: {wired}"
            + (f", and {sorted(given)} was given" if given else ""),
            f"pass --{kind.target} <name>"
            if kind.target
            else "leave --pin, --sensor and --channel out",
        )
    target = given.get(kind.target) if kind.target else None
    ident = name.replace("-", "_")
    if not NAME.match(name) or keyword.iskeyword(ident) or ident in RESERVED:
        raise _refuse(
            where,
            "a part's name becomes its action, gate and test: lowercase letters, digits, '-' or "
            "'_', starting with a letter, not a Python keyword or a name the action module imports",
            "pick a name such as heater or water-probe",
        )
    output = kind.primitive in ("digital.out", "motion", "display")
    if drives and output:
        raise _refuse(
            where,
            f"--drives names the output that an action decided by a sensor drives; a {kind.name} "
            "is the output",
            "remove --drives",
        )
    manifest_path = project / manifest
    if not manifest_path.is_file():
        raise _refuse(
            str(manifest_path),
            "there is no agent.toml here: `neuroedge add part` works inside an agent project",
            "cd into a project made by `neuroedge new`, or pass --agent <path/to/agent.toml>",
        )
    text, document = _read_toml(manifest_path, where)
    if name in (document.get("sim", {}).get("parts") or {}):
        raise _refuse(
            f"{manifest_path} -> [sim.parts.{name}]",
            "that part is already declared; nothing was written",
            "choose another name",
        )

    # VP-PT-09: the target must be on the board the project is on; the board is never switched here.
    declared = document.get("sim", {}).get("board")
    requires = {**document.get("requires", {}), kind.primitive: {}}
    chosen = board or (declared if isinstance(declared, str) else None) or _board_for(requires)
    if chosen != VIRTUAL_BOARD:
        offers = _board_lacks(load_board_by_id(chosen), kind, target)
        if offers is not None:
            raise _refuse(
                where,
                f"board {chosen!r} has no {kind.primitive} {target or kind.name!r} (it has "
                f"{offers or 'none'}); nothing was changed, and the board stays as it is",
                "either run on the virtual board, which adds what the agent declares and says "
                f"risk=virtual_board: neuroedge add part {part_kind} {name} "
                + (f"--{kind.target} {target} " if kind.target else "")
                + f"--board {VIRTUAL_BOARD}; or keep the agent's name and map it to a pin of "
                f"{chosen} with a [targets.{chosen}.pins] entry in agent.toml (VP-PM-01)",
            )

    edits = [Edit(("sim", "parts", name), "kind", kind.name)]
    if kind.target:
        edits.append(Edit(("sim", "parts", name), kind.target, target))
    if label:
        edits.append(Edit(("sim", "parts", name), "label", label))

    if output:
        plan = plan_add(
            project,
            "action",
            name,
            primitive=kind.primitive,
            pin=pin,
            channel=channel,
            servo=kind.name == "servo",
            board=board,
            manifest=manifest,
        )
    elif drives:
        plan = plan_add(
            project,
            "sensor",
            name,
            primitive=kind.primitive,
            source=target,
            pin=drives,
            like=kind.name,
            board=board,
            manifest=manifest,
        )
    else:
        # Only the part: its `[requires]` entry and a start value. An action decided by it is --drives.
        edits.insert(
            0, Edit(("requires",), kind.primitive, {REQUIRES_KEY[kind.primitive]: [target]})
        )
        if kind.primitive == "sensor.read" and part_kind in SENSORS:
            edits.append(Edit(("sim", "sensors"), target, SENSORS[part_kind]["initial"], keep=True))
        elif kind.primitive == "digital.in":
            edits.append(Edit(("sim", "inputs"), target, True, keep=True))
        elif kind.primitive == "analog.in":
            edits.append(Edit(("sim", "analog"), target, 1.8, keep=True))
        plan = Plan(name, "part", kind.primitive, chosen)
        plan.notes.append(
            f"{name} has no action yet: pass --drives <output pin> to make one decided by it "
            f"(or neuroedge add sensor <action> --source {target} --pin <output pin>)"
        )
    planned = plan.changed.get(Path(manifest), text)
    plan.changed[Path(manifest)] = edit_manifest(planned, edits, str(manifest_path))
    plan.kind = "part"
    return plan


def add_part(
    project: Path,
    part_kind: str,
    name: str,
    *,
    check: Callable[[Path, str], None] | None = None,
    manifest: str = "agent.toml",
    **options: Any,
) -> Plan:
    """Plan an `add part`, check it on a scratch copy as `add` does, then write it."""
    plan = plan_part(project, part_kind, name, manifest=manifest, **options)
    if check is not None:
        with tempfile.TemporaryDirectory(prefix="neuroedge-add-") as scratch:
            copy = Path(scratch) / "project"
            shutil.copytree(project, copy, ignore=COPY_IGNORE)
            _write(copy, plan)
            try:
                check(copy / manifest, plan.board)
            except NeuroEdgeError as error:
                _as_project(error, str(copy), str(project))
                raise
    _write(project, plan)
    return plan
