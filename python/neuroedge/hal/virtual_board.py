"""
The virtual board `sim-virtual` (docs/spec/virtual_parts.md §3.1, Q-84 phase A).

An agent that needs a pin, a sensor or a channel the reference sim boards lack gets them here,
on `sim` only: the board is the reference sim board plus exactly what the agent's `[requires]`
names and the reference board does not have (VP-VB-02). It is built in memory from the agent,
validated as any `board.v1` document, never written to `boards/` and never listed by
`available_boards()` (VP-VB-07). A session on it carries `risk=virtual_board` and the board's
digest, which replay checks (VP-VB-05, VP-VB-06).
"""

from __future__ import annotations

import copy
import hashlib
import json
import tomllib
from collections.abc import Mapping
from typing import Any

from ..errors import BoardCapabilityError
from .board import (
    REFERENCE_BOARD,
    BoardProfile,
    board_from_document,
    load_board_document,
    validate_board_document,
)

VIRTUAL_BOARD = "sim-virtual"
RISK_LABEL = "virtual_board"

# VP-VB-03: the strictest value of each field over the output pins of the reference sim boards.
DEFAULT_ENVELOPE: dict[str, int] = {
    "window_s": 3600,
    "max_on_ms_per_window": 600000,
    "min_interval_ms": 2000,
    "max_continuous_ms": 60000,
}

# What an added channel copies from `sim-rpi5` (VP-VB-02).
_ANALOG_TEMPLATE = "adc0"
_MOTOR_TEMPLATE = "wheel_left"
_SERVO_TEMPLATE = "gripper"
_RICH_BASE = "sim-rpi5"


def is_virtual(board_id: str | None) -> bool:
    return board_id == VIRTUAL_BOARD


def _reference(board_id: str) -> dict[str, Any]:
    from ..paths import boards_dir

    return load_board_document(boards_dir() / f"{board_id}.toml")


def _names(requires: Mapping[str, Any], primitive: str, key: str) -> list[str]:
    need = requires.get(primitive, {})
    names = need.get(key, []) if isinstance(need, Mapping) else []
    return [name for name in names if isinstance(name, str)] if isinstance(names, list) else []


def _base_id(requires: Mapping[str, Any]) -> str:
    """`sim-default`, or `sim-rpi5` when the agent needs a primitive only that board has."""
    from .board import _normalise

    default = _reference(REFERENCE_BOARD["sim"])["capabilities"]
    if all(_normalise(primitive) in default for primitive in requires):
        return REFERENCE_BOARD["sim"]
    return _RICH_BASE


def servo_channels(source: Mapping[str, Any]) -> set[str]:
    """Motion channels the agent's `[sim.parts]` declares as servos (phase B); motors otherwise."""
    parts = source.get("sim", {}).get("parts", {})
    if not isinstance(parts, Mapping):
        return set()
    return {
        part["channel"]
        for part in parts.values()
        if isinstance(part, Mapping) and part.get("kind") == "servo" and "channel" in part
    }


def virtual_board_document(
    requires: Mapping[str, Any],
    *,
    servos: set[str] | None = None,
    envelopes: Mapping[str, Mapping[str, int]] | None = None,
) -> tuple[dict[str, Any], dict[str, list[str]]]:
    """
    The `board.v1` document of `sim-virtual` for an agent's `[requires]`, and what was added
    to the reference board, by primitive. `envelopes` gives an added output pin's envelope
    (a part's kind preset, VP-PT-04); the rest get `DEFAULT_ENVELOPE`. Deterministic: added
    names are sorted, so the same agent gives the same document (VP-VB-08).
    """
    base_id = _base_id(requires)
    document = copy.deepcopy(_reference(base_id))
    capabilities: dict[str, Any] = document["capabilities"]
    added: dict[str, list[str]] = {}
    rich = _reference(_RICH_BASE)["capabilities"] if base_id != _RICH_BASE else None

    def note(primitive: str, name: str) -> None:
        added.setdefault(primitive, []).append(name)

    digital = capabilities.setdefault("digital_out", {"pins": [], "backend": "virtual"})
    digital.setdefault("envelope", {})
    for pin in sorted(set(_names(requires, "digital.out", "pins")) - set(digital["pins"])):
        digital["pins"].append(pin)
        digital["envelope"][pin] = dict((envelopes or {}).get(pin, DEFAULT_ENVELOPE))
        note("digital.out", pin)

    if "digital.in" in requires:
        inputs = capabilities.setdefault("digital_in", {"pins": [], "backend": "virtual"})
        for pin in sorted(set(_names(requires, "digital.in", "pins")) - set(inputs["pins"])):
            inputs["pins"].append(pin)
            note("digital.in", pin)

    if "sensor.read" in requires:
        sensors = capabilities.setdefault("sensor_read", {"sensors": []})
        for sensor in sorted(
            set(_names(requires, "sensor.read", "sensors")) - set(sensors["sensors"])
        ):
            sensors["sensors"].append(sensor)
            note("sensor.read", sensor)

    source = rich if rich is not None else capabilities
    if "analog.in" in requires:
        analog = capabilities.setdefault("analog_in", {"channels": []})
        have = {channel["name"] for channel in analog["channels"]}
        template = next(c for c in source["analog_in"]["channels"] if c["name"] == _ANALOG_TEMPLATE)
        for name in sorted(set(_names(requires, "analog.in", "channels")) - have):
            analog["channels"].append({**copy.deepcopy(template), "name": name})
            note("analog.in", name)

    if "motion" in requires:
        motion = capabilities.setdefault("motion", {})
        have = {c["name"] for kind in ("motor", "servo") for c in motion.get(kind, [])}
        for name in sorted(set(_names(requires, "motion", "channels")) - have):
            kind, template_name = (
                ("servo", _SERVO_TEMPLATE)
                if name in (servos or set())
                else ("motor", _MOTOR_TEMPLATE)
            )
            template = next(c for c in source["motion"][kind] if c["name"] == template_name)
            enable = f"{name}_en"
            motion.setdefault(kind, []).append(
                {**copy.deepcopy(template), "name": name, "enable_pin": enable}
            )
            motion.setdefault("envelope", {})[name] = copy.deepcopy(
                source["motion"]["envelope"][template_name]
            )
            if enable not in digital["pins"]:
                digital["pins"].append(enable)
            note("motion", name)

    document["board"] = {
        **document["board"],
        "id": VIRTUAL_BOARD,
        "name": "NeuroEdge virtual board",
    }
    return document, added


def canonical(document: Mapping[str, Any]) -> str:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def board_digest(document: Mapping[str, Any]) -> str:
    """VP-VB-06: SHA-256 of the canonical JSON of the board."""
    return "sha256:" + hashlib.sha256(canonical(document).encode("utf-8")).hexdigest()


class VirtualBoard:
    """`sim-virtual` for one agent: the profile, its digest and what it added."""

    def __init__(self, manifest: Any) -> None:
        source = tomllib.loads(manifest.source.read_text(encoding="utf-8"))
        envelopes = envelope_presets(manifest) if _has_parts(source) else None
        document, self.added = virtual_board_document(
            manifest.requires, servos=servo_channels(source), envelopes=envelopes
        )
        validate_board_document(document, label=f"{VIRTUAL_BOARD} ({manifest.source})")
        self.document = document
        self.digest = board_digest(document)
        self.profile: BoardProfile = board_from_document(
            document, source=f"{VIRTUAL_BOARD} (built from {manifest.source})"
        )

    def startup_line(self) -> str:
        """VP-VB-05: `risk=virtual_board added: digital.out heater, air_pump · sensor.read ph`."""
        if not self.added:
            return f"risk={RISK_LABEL} added: nothing (the reference board has everything)"
        parts = [f"{primitive} {', '.join(names)}" for primitive, names in self.added.items()]
        return f"risk={RISK_LABEL} added: " + " · ".join(parts)

    def metadata(self) -> dict[str, Any]:
        return {"risks": [RISK_LABEL], "virtual_board_digest": self.digest}


def _has_parts(source: Mapping[str, Any]) -> bool:
    return isinstance(source.get("sim", {}).get("parts"), Mapping)


def envelope_presets(manifest: Any) -> dict[str, dict[str, int]]:
    """Envelopes of `[sim.parts]` output pins: each kind's preset, tightened by the part (VP-PT-04)."""
    from .parts import part_envelopes

    return part_envelopes(manifest)


def sim_board_of(manifest: Any) -> str | None:
    """`[sim] board = "…"` of agent.toml (VP-VB-01), or None."""
    board = tomllib.loads(manifest.source.read_text(encoding="utf-8")).get("sim", {}).get("board")
    return board if isinstance(board, str) and board else None


def refuse_off_sim(target: str, where: str = "--board sim-virtual") -> BoardCapabilityError:
    """VP-VB-04: the virtual board exists on `sim` only; graduation checks the real board."""
    return BoardCapabilityError(
        where=f"{where} --target {target}",
        why=(
            f"board {VIRTUAL_BOARD!r} is built for target 'sim' only; on {target!r} the agent is "
            "checked against a real board profile (docs/spec/virtual_parts.md VP-VB-04)"
        ),
        how=(
            f"drop --board (the default board of {target} is {REFERENCE_BOARD.get(target, '?')!r}), "
            "or run on --target sim; to keep the agent's pin names on a real board, map them "
            "with [targets.<board>.pins]"
        ),
    )


def resolve_board(
    board_id: str | None, target: str, manifest: Any
) -> tuple[BoardProfile, VirtualBoard | None]:
    """
    The board a build or a session runs on: `board_id`, else `[sim] board` on `sim`, else the
    target's reference board. `sim-virtual` is built from the agent; off `sim` it is refused.
    A real board comes with the agent's pin names when agent.toml maps it (VP-PM-01 → 03), so
    every consumer — build, session, replay — sees the same mapped board.
    """
    from .board import load_board_by_id
    from .pin_map import apply_pin_map, check_pin_maps

    check_pin_maps(manifest)  # VP-PM-01: every map the agent declares, for any board
    chosen = board_id
    if chosen is None and target == "sim":
        chosen = sim_board_of(manifest)
    if is_virtual(chosen):
        if target != "sim":
            raise refuse_off_sim(
                target, "--board sim-virtual" if board_id else f"{manifest.source} -> [sim] board"
            )
        virtual = VirtualBoard(manifest)
        return virtual.profile, virtual
    board = load_board_by_id(chosen or REFERENCE_BOARD.get(target, "esp32s3-box-3"))
    return apply_pin_map(board, manifest), None
