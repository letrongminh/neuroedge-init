"""
The per-board pin map (docs/spec/virtual_parts.md §3.3, Q-84 phase A+, VP-PM-01 → VP-PM-05).

`[targets.<board-id>.pins]` in agent.toml maps an agent's pin name to a pin of that board, so an
agent keeps its own names from `sim` to a real board — the pattern of a Zephyr devicetree overlay,
where the code names logical devices and a per-board file says which pin each one is.

The map is applied by renaming the mapped pins inside the board's declaration, before anything
reads it: the HAL, the safety envelope, the token ledger, the trace and the generated chip pin
table then all see the agent's name, while the envelope and the backend stay the real pin's
(VP-PM-02) and `BoardProfile.pin_map` remembers which real pin each name stands for, which the
`linux` HAL needs to find the line. Only `digital.out` and `digital.in` pins are mapped: the enable
line of a PWM or motion channel belongs to the HAL, and a channel is not a pin.

A map decides which real device an allowed action moves (docs/spec/threat_model.md), so every
doubt is a refusal, checked at load and for every board the agent names — not only the one it is
built for.
"""

from __future__ import annotations

import copy
import dataclasses
import tomllib
from collections.abc import Mapping
from typing import Any

from ..errors import AgentManifestError, BoardCapabilityError
from .board import BoardProfile, _enable_pins
from .virtual_board import VIRTUAL_BOARD


def declared_maps(manifest: Any) -> dict[str, dict[str, str]]:
    """Each `[targets.<board-id>.pins]` of agent.toml, as written. `supported` is not a board."""
    targets = tomllib.loads(manifest.source.read_text(encoding="utf-8")).get("targets", {})
    maps: dict[str, dict[str, str]] = {}
    for board_id, table in targets.items():
        if board_id == "supported":
            continue
        where = f"{manifest.source} -> [targets.{board_id}]"
        if not isinstance(table, Mapping):
            continue  # an unknown scalar under [targets] was never read; it stays unread
        unknown = sorted(set(table) - {"pins"})
        pins = table.get("pins")
        if unknown or not isinstance(pins, Mapping):
            raise AgentManifestError(
                where=where,
                why=f"a board table holds `pins` only; found {sorted(table)}",
                how=f'write [targets.{board_id}.pins] with `agent_pin = "board_pin"` lines',
            )
        bad = sorted(name for name, value in pins.items() if not isinstance(value, str))
        if bad:
            raise AgentManifestError(
                where=f"{where}.pins",
                why=f"{bad} do not map to a pin name (a string)",
                how='write `heater = "gate_relay"`: the board pin the agent name stands for',
            )
        maps[board_id] = dict(pins)
    return maps


def _agent_pins(manifest: Any) -> tuple[list[str], list[str]]:
    requires = manifest.requires
    return (
        list(requires.get("digital.out", {}).get("pins", [])),
        list(requires.get("digital.in", {}).get("pins", [])),
    )


def _board_document(board_id: str, where: str) -> dict[str, Any]:
    from ..paths import boards_dir
    from .board import load_board_document

    path = boards_dir() / f"{board_id}.toml"
    if board_id == VIRTUAL_BOARD or not path.is_file():
        known = sorted(p.stem for p in boards_dir().glob("*.toml"))
        raise AgentManifestError(
            where=where,
            why=(
                f"the virtual board already has the agent's own pin names, so it takes no map "
                f"(VP-PM-05); known boards: {known}"
                if board_id == VIRTUAL_BOARD
                else f"no board {board_id!r}; known boards: {known}"
            ),
            how=(
                "remove the entry, or map for a board file"
                if board_id == VIRTUAL_BOARD
                else f"name one of {known}, or remove the entry"
            ),
        )
    return load_board_document(path)


def check_pin_maps(manifest: Any) -> dict[str, dict[str, str]]:
    """
    VP-PM-01: every map the agent declares, checked against its board's declaration — an unknown
    board, a pin the board lacks or has for another primitive (or that the HAL owns), two agent
    names on one board pin, an agent name on a board pin the agent also uses by its own name, and
    a rename that would give a board two pins one name. Returns the maps; raises on the first
    problem, naming both pins.
    """
    maps = declared_maps(manifest)
    outputs, inputs = _agent_pins(manifest)
    for board_id, pins in maps.items():
        where = f"{manifest.source} -> [targets.{board_id}.pins]"
        document = _board_document(board_id, where)
        capabilities = document.get("capabilities", {})
        digital_out = capabilities.get("digital_out", {})
        out_pins = list(digital_out.get("pins", []))
        in_pins = list(capabilities.get("digital_in", {}).get("pins", []))
        owned = set(_enable_pins(capabilities)) | set(digital_out.get("pwm", {}).get("pins", []))
        by_board_pin: dict[str, str] = {}
        for agent_pin, board_pin in pins.items():
            at = f"{where} {agent_pin}"
            if agent_pin in outputs and agent_pin in inputs:
                raise AgentManifestError(
                    where=at,
                    why=f"{agent_pin!r} is both a digital.out and a digital.in pin of the agent",
                    how="give the output and the input different names",
                )
            if agent_pin not in outputs and agent_pin not in inputs:
                raise AgentManifestError(
                    where=at,
                    why=f"{agent_pin!r} is not a digital.out or digital.in pin of [requires]; "
                    f"the agent declares {outputs + inputs or 'none'}",
                    how="map a pin the agent declares, or declare it in [requires]",
                )
            primitive, mine, other = (
                ("digital.out", out_pins, in_pins)
                if agent_pin in outputs
                else ("digital.in", in_pins, out_pins)
            )
            if board_pin in owned and primitive == "digital.out":
                raise BoardCapabilityError(
                    where=at,
                    why=f"{board_pin!r} on board {board_id!r} is a PWM channel or the enable line "
                    "of a channel; the HAL owns it and no agent pin stands for it",
                    how="map to a plain digital.out pin of the board",
                )
            if board_pin not in mine:
                raise BoardCapabilityError(
                    where=at,
                    why=(
                        f"{agent_pin!r} is a {primitive} pin but {board_pin!r} on board "
                        f"{board_id!r} is "
                        f"{'a pin of the other primitive' if board_pin in other else 'not a pin'}"
                        f"; the board has {primitive} pins {mine or 'none'}"
                    ),
                    how=f"map {agent_pin!r} to one of {mine or 'no pin: pick another board'}",
                )
            if board_pin in by_board_pin:
                raise AgentManifestError(
                    where=at,
                    why=f"{by_board_pin[board_pin]!r} and {agent_pin!r} are both mapped to "
                    f"{board_pin!r} of {board_id!r}: one line cannot be two devices",
                    how="give each agent pin its own board pin",
                )
            by_board_pin[board_pin] = agent_pin
        direct = [pin for pin in outputs + inputs if pin not in pins]
        for board_pin, agent_pin in by_board_pin.items():
            if board_pin in direct:
                raise AgentManifestError(
                    where=f"{where} {agent_pin}",
                    why=f"{agent_pin!r} is mapped to {board_pin!r} of {board_id!r}, which the "
                    f"agent also uses by its own name {board_pin!r}",
                    how=f"map {board_pin!r} elsewhere too, or choose another pin for {agent_pin!r}",
                )
        for section, board_pins in (("digital.out", out_pins), ("digital.in", in_pins)):
            kept = {pin for pin in board_pins if pin not in by_board_pin}
            for agent_pin, board_pin in pins.items():
                if board_pin in board_pins and agent_pin in kept:
                    raise AgentManifestError(
                        where=f"{where} {agent_pin}",
                        why=f"after the map {agent_pin!r} names {board_pin!r} and also the "
                        f"{section} pin {agent_pin!r} of board {board_id!r}",
                        how=f"map {agent_pin!r} to the pin of {board_id!r} named {agent_pin!r}, "
                        "or rename the agent pin",
                    )
    return maps


def _renamed(names: list[str], pins: Mapping[str, str]) -> list[str]:
    back = {board_pin: agent_pin for agent_pin, board_pin in pins.items()}
    return [back.get(name, name) for name in names]


def apply_pin_map(board: BoardProfile, manifest: Any) -> BoardProfile:
    """
    The board with the agent's pin names, when the agent maps this board; the same board object
    otherwise (VP-PM-04: no map, no change). The maps are checked first (`check_pin_maps`).
    """
    pins = check_pin_maps(manifest).get(board.id)
    if not pins:
        return board
    outputs, _ = _agent_pins(manifest)
    mapped = {name: pin for name, pin in pins.items() if name in outputs}
    in_map = {name: pin for name, pin in pins.items() if name not in outputs}
    capabilities = copy.deepcopy(board.capabilities)
    if "digital_out" in capabilities:
        digital = capabilities["digital_out"]
        back = {board_pin: agent_pin for agent_pin, board_pin in mapped.items()}
        digital["pins"] = _renamed(digital["pins"], mapped)
        if "signal_pins" in digital:
            digital["signal_pins"] = _renamed(digital["signal_pins"], mapped)
        if "feedback" in digital:
            digital["feedback"]["pins"] = _renamed(digital["feedback"]["pins"], mapped)
        if "envelope" in digital:
            digital["envelope"] = {
                back.get(name, name): limits for name, limits in digital["envelope"].items()
            }
    if "digital_in" in capabilities:
        capabilities["digital_in"]["pins"] = _renamed(capabilities["digital_in"]["pins"], in_map)
    return dataclasses.replace(board, capabilities=capabilities, pin_map=dict(pins))


def startup_line(pin_map: Mapping[str, str]) -> str:
    """VP-PM-04: `pins: heater → gate_relay, air_pump → door_lock`."""
    return "pins: " + ", ".join(f"{name} → {pin}" for name, pin in pin_map.items())
