"""
Board capability declarations — the L1 side of the two-way capability contract.

A board declares what it *has*; an agent declares what it *needs*; `neuroedge
build` matches the two before a single line runs on hardware (FR-HAL-04). This
module owns the "has" side: parsing `boards/*.toml`, validating it against
schemas/board.v1.json, and answering capability queries.

Design under MCU constraint (TSK-S1-11)
---------------------------------------
This model is read on a workstation, never on the microcontroller. That is a
deliberate consequence of the Q-9 decision: the host resolves and compiles,
the device only executes. Three properties follow, and the review in
docs/spec/hal_mcu_review.md explains why each is load-bearing:

  * **Capabilities are a closed set.** The five primitives (`audio.in`,
    `audio.out`, `digital.out`, `sensor.read`, `display`) are fixed, so the
    device-side capability table is a static array sized at compile time —
    no allocator in the HAL.
  * **Pins are named, not numbered, in agent code.** The board owns the
    mapping from `door_lock` to GPIO 11. An agent that hard-coded a pin number
    would not be portable across the three targets, and target equivalence is
    the product claim.
  * **Declarations are data, not code.** A board profile adds a TOML file and
    no Python, so porting to a fourth board cannot introduce host-only
    behaviour that the MCU build silently lacks.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import BoardCapabilityError
from ..paths import boards_dir, schema_path

# The five immutable primitives (FR-HAL-01). The names carry dots in the agent
# API and underscores as declaration keys; both spellings are accepted below.
PRIMITIVES: tuple[str, ...] = (
    "audio.in",
    "audio.out",
    "digital.out",
    "sensor.read",
    "display",
)

_CAPABILITY_KEYS = {
    "audio.in": "audio_in",
    "audio.out": "audio_out",
    "digital.out": "digital_out",
    "sensor.read": "sensor_read",
    "display": "display",
}

SUPPORTED_TARGETS: tuple[str, ...] = ("sim", "linux", "esp32s3")


def _normalise(primitive: str) -> str:
    """Accept either `digital.out` or `digital_out` and return the schema key."""
    if primitive in _CAPABILITY_KEYS:
        return _CAPABILITY_KEYS[primitive]
    if primitive in _CAPABILITY_KEYS.values():
        return primitive
    raise BoardCapabilityError(
        where=f"primitive {primitive!r}",
        why=(
            f"{primitive!r} is not one of the five HAL primitives; "
            f"the primitives are {list(PRIMITIVES)}"
        ),
        how=(
            "the primitive set is frozen by FR-HAL-01 — express the need in terms of "
            "an existing primitive, or raise an RFC to extend the HAL"
        ),
    )


@dataclass(frozen=True)
class BoardProfile:
    """
    One board declaration, parsed from `boards/<id>.toml`.

    Attributes
    ----------
    capabilities:
        Keyed by schema name (`audio_in`, `digital_out`, ...). A key that is
        absent means the board does not offer that primitive at all, which is
        different from offering it with empty parameters.
    """

    id: str
    target: str
    mcu: str
    name: str = ""
    capabilities: dict[str, Any] = field(default_factory=dict)
    source: str = "<memory>"

    # -- capability queries ------------------------------------------------
    def supports(self, primitive: str) -> bool:
        return _normalise(primitive) in self.capabilities

    def capability(self, primitive: str) -> dict[str, Any]:
        key = _normalise(primitive)
        declared = self.capabilities.get(key)
        if declared is None:
            raise BoardCapabilityError(
                where=f"{self.id} ({self.source})",
                why=f"board does not declare the {primitive!r} primitive",
                how=(
                    f"choose a board that provides {primitive!r}, or add a "
                    f"[capabilities.{key}] section to {self.source}"
                ),
            )
        return dict(declared)

    @property
    def pins(self) -> tuple[str, ...]:
        """Named digital-output pins, empty when the board has no `digital.out`."""
        return tuple(self.capabilities.get("digital_out", {}).get("pins", ()))

    @property
    def sensors(self) -> tuple[str, ...]:
        return tuple(self.capabilities.get("sensor_read", {}).get("sensors", ()))

    def require_pin(self, pin: str, called_from: str = "<unknown>") -> None:
        """
        Assert a named pin exists, with the three-part message FR-HAL-05 demands:
        what is missing, what the board does offer, and where the request came from.
        """
        if pin in self.pins:
            return
        raise BoardCapabilityError(
            where=f"{called_from} -> digital.out pin {pin!r}",
            why=(
                f"board {self.id!r} declares no pin named {pin!r}; "
                f"it offers {list(self.pins) or 'no digital.out pins'}"
            ),
            how=(
                f"use one of the declared pins, or add {pin!r} to "
                f"[capabilities.digital_out].pins in {self.source}"
            ),
        )

    def require_sensor(self, sensor: str, called_from: str = "<unknown>") -> None:
        if sensor in self.sensors:
            return
        raise BoardCapabilityError(
            where=f"{called_from} -> sensor.read {sensor!r}",
            why=(
                f"board {self.id!r} declares no sensor named {sensor!r}; "
                f"it offers {list(self.sensors) or 'no sensors'}"
            ),
            how=(
                f"use one of the declared sensors, or add {sensor!r} to "
                f"[capabilities.sensor_read].sensors in {self.source}"
            ),
        )

    def missing_primitives(self, required: Iterable[str]) -> list[str]:
        """Which of `required` this board cannot provide. Empty means a match."""
        return [p for p in required if not self.supports(p)]

    def to_document(self) -> dict[str, Any]:
        """Round-trip back to the board.v1.json document shape."""
        board: dict[str, Any] = {"id": self.id, "target": self.target, "mcu": self.mcu}
        if self.name:
            board["name"] = self.name
        return {"board": board, "capabilities": self.capabilities}


def _board_schema() -> dict[str, Any]:
    with open(schema_path("board.v1.json"), encoding="utf-8") as handle:
        return json.load(handle)


def validate_board_document(document: Mapping[str, Any], label: str) -> None:
    """Validate a board declaration against schemas/board.v1.json."""
    import jsonschema

    validator = jsonschema.Draft202012Validator(_board_schema())
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
    if not errors:
        return

    first = errors[0]
    location = ".".join(str(part) for part in first.absolute_path) or "<document root>"
    raise BoardCapabilityError(
        where=f"{label} -> {location}",
        why=first.message,
        how="correct the field against schemas/board.v1.json",
    )


def load_board_document(path: str | Path) -> dict[str, Any]:
    """Parse and validate one `boards/*.toml` declaration."""
    import tomllib

    path = Path(path)
    if not path.is_file():
        raise BoardCapabilityError(
            where=str(path),
            why="board declaration does not exist",
            how=f"list the available profiles in {boards_dir()}",
        )

    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise BoardCapabilityError(
            where=str(path),
            why=f"file is not valid TOML: {exc}",
            how="board declarations are TOML; repair the syntax above",
        ) from exc

    validate_board_document(document, label=str(path))
    return document


def board_from_document(document: Mapping[str, Any], source: str = "<memory>") -> BoardProfile:
    board = document["board"]
    return BoardProfile(
        id=board["id"],
        target=board["target"],
        mcu=board["mcu"],
        name=board.get("name", ""),
        capabilities=dict(document.get("capabilities", {})),
        source=source,
    )


def load_board(path: str | Path) -> BoardProfile:
    path = Path(path)
    return board_from_document(load_board_document(path), source=str(path))


def load_board_by_id(board_id: str, root: Path | None = None) -> BoardProfile:
    """
    Look up a board profile by id, e.g. ``load_board_by_id("esp32s3-box-3")``.

    The reference board is fixed at ESP32-S3-Box-3 (Q-1/Q-2); other profiles
    exist so that target equivalence has something to be equivalent across.
    """
    root = Path(root) if root is not None else boards_dir()
    candidate = root / f"{board_id}.toml"
    if not candidate.is_file():
        available = sorted(p.stem for p in root.glob("*.toml")) if root.is_dir() else []
        raise BoardCapabilityError(
            where=f"board id {board_id!r}",
            why=f"no declaration at {candidate}; available profiles: {available}",
            how=f"pick one of {available}, or add {board_id}.toml to {root}",
        )
    return load_board(candidate)


def available_boards(root: Path | None = None) -> list[BoardProfile]:
    root = Path(root) if root is not None else boards_dir()
    if not root.is_dir():
        return []
    return [load_board(p) for p in sorted(root.glob("*.toml"))]
