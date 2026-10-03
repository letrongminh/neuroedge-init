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

  * **Capabilities are a closed set.** The five core primitives (`audio.in`,
    `audio.out`, `digital.out`, `sensor.read`, `display`) and the five optional
    extension primitives (`digital.in`, `i2c`, `analog.in`, `motion`, `vision.in`;
    PWM is a block of `digital.out`) are fixed, so the device-side capability
    table is a static array sized at compile time — no allocator in the HAL.
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

# The five core primitives (FR-HAL-01, RFC-0013 §3a): every default board of a target
# and every full reference board declares all of them. The names carry dots in the agent
# API and underscores as declaration keys; both spellings are accepted below.
PRIMITIVES: tuple[str, ...] = (
    "audio.in",
    "audio.out",
    "digital.out",
    "sensor.read",
    "display",
)

# The optional extension primitives (RFC-0013 §3a): a board declares one only when its
# hardware has it — an absent key is "not offered", never a placeholder. PWM is not here:
# it is a block of `digital.out` (RFC-0010).
EXTENSION_PRIMITIVES: tuple[str, ...] = (
    "digital.in",
    "i2c",
    "analog.in",
    "motion",
    "vision.in",
)
ALL_PRIMITIVES: tuple[str, ...] = PRIMITIVES + EXTENSION_PRIMITIVES
# The extension primitives an agent's `[requires]` and `@action(requires=...)` may name so
# far: each one is added by the slice that gives it a precise capability check (the pin,
# bus, device or channel must be declared on the board), never as a bare "the board has it".
REQUIRABLE_EXTENSIONS: tuple[str, ...] = ("i2c",)

_CAPABILITY_KEYS = {
    "audio.in": "audio_in",
    "audio.out": "audio_out",
    "digital.out": "digital_out",
    "sensor.read": "sensor_read",
    "display": "display",
    "digital.in": "digital_in",
    "i2c": "i2c",
    "analog.in": "analog_in",
    "motion": "motion",
    "vision.in": "vision_in",
}

SUPPORTED_TARGETS: tuple[str, ...] = ("sim", "linux", "esp32s3")
# The reference boards of each tier-1 target (RFC-0013 §3b). The first is the default
# when no --board is given, and always declares the five core primitives. Every id here
# has a profile in boards/ whose target matches (test_boards.py).
REFERENCE_BOARDS: dict[str, tuple[str, ...]] = {
    "sim": ("sim-default", "sim-rpi5"),
    "linux": ("linux-rpi5",),
    "esp32s3": ("esp32s3-box-3",),
}
# The default board of each target — the first reference board, kept under its old name.
REFERENCE_BOARD = {target: boards[0] for target, boards in REFERENCE_BOARDS.items()}
# Reference boards exempt from the core-primitive rule (RFC-0013 §3b option (c)); never a
# default board. Empty: the camera board for `esp32s3` is a full board (Q-61).
EXTENSION_REFERENCE_BOARDS: frozenset[str] = frozenset()
# Which board each `sim-*` profile mirrors (RFC-0013 §3d). A table in core code, not a
# field of board.toml: a profile must not declare which board it mirrors, so the loader
# refuses a `mirrors` key.
SIM_MIRRORS: dict[str, str] = {"sim-default": "esp32s3-box-3", "sim-rpi5": "linux-rpi5"}


def _normalise(primitive: str) -> str:
    """Accept either `digital.out` or `digital_out` and return the schema key."""
    if primitive in _CAPABILITY_KEYS:
        return _CAPABILITY_KEYS[primitive]
    if primitive in _CAPABILITY_KEYS.values():
        return primitive
    raise BoardCapabilityError(
        where=f"primitive {primitive!r}",
        why=(
            f"{primitive!r} is not one of the HAL primitives; the core primitives are "
            f"{list(PRIMITIVES)} and the optional extension primitives are "
            f"{list(EXTENSION_PRIMITIVES)}"
        ),
        how=(
            "the primitive set is frozen by FR-HAL-01 and RFC-0013 — express the need in "
            "terms of an existing primitive, or raise an RFC to extend the HAL"
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
        if pin in self.enable_pins:
            raise BoardCapabilityError(
                where=f"{called_from} -> digital.out pin {pin!r}",
                why=(
                    f"{pin!r} is the enable line of a PWM or motion channel of board "
                    f"{self.id!r}; the HAL owns it and no agent drives it (RFC-0010 §3a)"
                ),
                how="command the channel the pin serves, never its enable line",
            )
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
        """
        Which of `required` this board cannot provide. Empty means a match. Both the core
        and the extension primitives are accepted (`ALL_PRIMITIVES`).
        """
        return [p for p in required if not self.supports(p)]

    # -- extension declarations (RFC-0007, RFC-0010, RFC-0011, RFC-0012) ---
    @property
    def input_pins(self) -> tuple[str, ...]:
        """Named digital-input pins, empty when the board has no `digital.in`."""
        return tuple(self.capabilities.get("digital_in", {}).get("pins", ()))

    @property
    def signal_pins(self) -> tuple[str, ...]:
        """`digital.out` pins that only carry a signal (no load), exempt from an envelope."""
        return tuple(self.capabilities.get("digital_out", {}).get("signal_pins", ()))

    @property
    def pwm_pins(self) -> tuple[str, ...]:
        """`digital.out` pins that are hardware PWM channels; empty without a `pwm` block."""
        return tuple(self.capabilities.get("digital_out", {}).get("pwm", {}).get("pins", ()))

    @property
    def enable_pins(self) -> tuple[str, ...]:
        """
        The `enable_pin` of every PWM and motion channel. The HAL owns them: an agent
        never drives one, and they carry no envelope of their own (RFC-0010 §3a).
        """
        return tuple(sorted(_enable_pins(self.capabilities)))

    def envelope(self, name: str) -> dict[str, int] | None:
        """
        The safety envelope of a `digital.out` pin or a `motion` channel, or None when
        it has none (a signal pin, an enable pin, or an unknown name).
        """
        digital = self.capabilities.get("digital_out", {}).get("envelope", {})
        motion = self.capabilities.get("motion", {}).get("envelope", {})
        declared = digital.get(name, motion.get(name))
        return dict(declared) if declared is not None else None

    @property
    def i2c_buses(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.capabilities.get("i2c", {}).get("buses", ()))

    @property
    def analog_channels(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.capabilities.get("analog_in", {}).get("channels", ()))

    @property
    def motion_channels(self) -> tuple[dict[str, Any], ...]:
        """Motor and servo records, each with a `kind` of `motor` or `servo` added."""
        motion = self.capabilities.get("motion", {})
        return tuple(
            {**channel, "kind": kind}
            for kind in ("motor", "servo")
            for channel in motion.get(kind, ())
        )

    @property
    def vision_modes(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.capabilities.get("vision_in", {}).get("modes", ()))

    def to_document(self) -> dict[str, Any]:
        """Round-trip back to the board.v1.json document shape."""
        board: dict[str, Any] = {"id": self.id, "target": self.target, "mcu": self.mcu}
        if self.name:
            board["name"] = self.name
        return {"board": board, "capabilities": self.capabilities}


def _board_schema() -> dict[str, Any]:
    with open(schema_path("board.v1.json"), encoding="utf-8") as handle:
        return json.load(handle)


def _enable_pins(capabilities: Mapping[str, Any]) -> set[str]:
    """Every `enable_pin` named by a PWM channel or a motion channel."""
    pins = {
        entry.get("pin")
        for entry in capabilities.get("digital_out", {})
        .get("pwm", {})
        .get("enable_pin", {})
        .values()
        if isinstance(entry, Mapping)
    }
    motion = capabilities.get("motion", {})
    for kind in ("motor", "servo"):
        pins |= {channel.get("enable_pin") for channel in motion.get(kind, ())}
    return {pin for pin in pins if isinstance(pin, str)}


def _refuse(label: str, location: str, why: str, how: str) -> BoardCapabilityError:
    return BoardCapabilityError(where=f"{label} -> {location}", why=why, how=how)


def _check_declaration_keys(document: Mapping[str, Any], label: str) -> None:
    """
    Refuse what the schema cannot say well: a profile that declares which board it
    mirrors (RFC-0013 §3d) and a misspelt capability key (RFC-0013 §3a). Both would
    otherwise be accepted or reported without the way out.
    """
    board = document.get("board")
    capabilities = document.get("capabilities")
    for owner, location in (
        (document, "<document root>"),
        (board, "board"),
        (capabilities, "capabilities"),
    ):
        if isinstance(owner, Mapping) and "mirrors" in owner:
            raise _refuse(
                label,
                f"{location}.mirrors" if owner is not document else "mirrors",
                "a profile may not declare which board it mirrors",
                "the mirror relation is the SIM_MIRRORS table in neuroedge/hal/board.py "
                "(RFC-0013 §3d); remove `mirrors` from the profile",
            )
    if not isinstance(capabilities, Mapping):
        return
    known = set(_CAPABILITY_KEYS.values())
    unknown = sorted(set(capabilities) - known)
    if unknown:
        raise _refuse(
            label,
            f"capabilities.{unknown[0]}",
            f"{unknown} are not capability keys of board.v1; the keys are {sorted(known)}",
            "capability keys use underscores (`digital_in`, not `digital.in`); "
            "a primitive this list lacks needs an RFC",
        )


def _check_digital_out(label: str, capabilities: Mapping[str, Any]) -> None:
    digital = capabilities.get("digital_out")
    if digital is None:
        return
    pins = set(digital.get("pins", ()))
    signal = set(digital.get("signal_pins", ()))
    envelope = digital.get("envelope", {})
    pwm = digital.get("pwm")
    pwm_pins = set(pwm["pins"]) if pwm else set()
    enable = _enable_pins(capabilities)
    where = "capabilities.digital_out"

    stray = sorted(signal - pins)
    if stray:
        raise _refuse(
            label,
            f"{where}.signal_pins",
            f"signal_pins names {stray}, which digital_out.pins does not declare "
            f"(it declares {sorted(pins) or 'no pins'})",
            "signal_pins must be a subset of pins; fix the name or add the pin to pins",
        )
    bad = sorted(signal & (pwm_pins | enable))
    if bad:
        raise _refuse(
            label,
            f"{where}.signal_pins",
            f"{bad} drive a load (a PWM channel) or are HAL-owned enable pins, "
            "and cannot be signal pins",
            "remove them from signal_pins; every PWM channel is an actuator (RFC-0010 §3a)",
        )
    stray = sorted(set(envelope) - pins)
    if stray:
        raise _refuse(
            label,
            f"{where}.envelope.{stray[0]}",
            f"envelope names {stray}, which digital_out.pins does not declare",
            "name a declared pin, or add it to pins",
        )
    feedback = digital.get("feedback")
    if feedback:
        stray = sorted(set(feedback["pins"]) - pins)
        if stray:
            raise _refuse(
                label,
                f"{where}.feedback.pins",
                f"feedback names {stray}, which digital_out.pins does not declare",
                "feedback lists only declared pins that have a hardware readback",
            )
    if not pwm:
        return
    frequency = pwm["frequency_hz"]
    if frequency["min"] > frequency["max"]:
        raise _refuse(
            label,
            f"{where}.pwm.frequency_hz",
            f"min ({frequency['min']}) is greater than max ({frequency['max']})",
            "declare the range the hardware can produce, min <= max",
        )
    stray = sorted(pwm_pins - pins)
    if stray:
        raise _refuse(
            label,
            f"{where}.pwm.pins",
            f"pwm.pins names {stray}, which digital_out.pins does not declare",
            "pwm.pins must be a subset of pins",
        )
    channels = pwm["enable_pin"]
    if set(channels) != pwm_pins:
        raise _refuse(
            label,
            f"{where}.pwm.enable_pin",
            f"enable_pin covers {sorted(channels)} but the PWM channels are {sorted(pwm_pins)}; "
            "every channel needs exactly one enable_pin",
            "add or remove entries so enable_pin has one key per pwm.pins channel",
        )
    shared: dict[str, str] = {}
    for channel, entry in channels.items():
        if entry["pin"] in shared:
            raise _refuse(
                label,
                f"{where}.pwm.enable_pin.{channel}",
                f"enable pin {entry['pin']!r} serves both PWM channels {shared[entry['pin']]!r} "
                f"and {channel!r}",
                "give every PWM channel its own enable pin (RFC-0010 §9.15)",
            )
        shared[entry["pin"]] = channel
        if entry["pin"] not in pins or entry["pin"] in pwm_pins:
            raise _refuse(
                label,
                f"{where}.pwm.enable_pin.{channel}",
                f"enable pin {entry['pin']!r} must be a declared digital_out pin "
                "that is not itself a PWM channel",
                "add the pin to digital_out.pins and use a different pin for each channel",
            )


def _check_motion_enable_pins(label: str, capabilities: Mapping[str, Any]) -> None:
    """
    A motion channel's enable pin is a declared `digital_out` line that is not a PWM
    channel, and serves that channel alone: a shared line would cut two actuators at once
    (RFC-0010 §9.15, RFC-0011 §3a). PWM enable pins are checked with `digital_out`.
    """
    digital = capabilities.get("digital_out", {})
    pins = set(digital.get("pins", ()))
    pwm = digital.get("pwm", {})
    pwm_pins = set(pwm.get("pins", ()))
    claimed = {
        entry["pin"]: f"pwm channel {name!r}" for name, entry in pwm.get("enable_pin", {}).items()
    }
    motion = capabilities.get("motion", {})
    for kind in ("motor", "servo"):
        for channel in motion.get(kind, ()):
            owner, pin = f"motion {kind} {channel['name']!r}", channel["enable_pin"]
            where = f"capabilities.motion.{kind}.{channel['name']}.enable_pin"
            if pin not in pins or pin in pwm_pins:
                raise _refuse(
                    label,
                    where,
                    f"{owner} has enable pin {pin!r}, which is not a declared digital_out "
                    "pin, or is a PWM channel itself",
                    "the enable pin is its own digital_out line; add it to digital_out.pins",
                )
            if pin in claimed:
                raise _refuse(
                    label,
                    where,
                    f"enable pin {pin!r} serves both {claimed[pin]} and {owner}",
                    "give every PWM and motion channel its own enable pin",
                )
            claimed[pin] = owner


def _check_actuator_envelopes(label: str, capabilities: Mapping[str, Any]) -> None:
    """
    Every pin is an actuator unless declared otherwise: a limit that is absent would be a
    pin with no physical bound (RFC-0007 §3d). Enable pins are bounded by the envelope of
    the channel they serve. Runs after the checks that establish which pins are enable pins,
    so a misdeclared enable pin is reported as that, not as a missing envelope.
    """
    digital = capabilities.get("digital_out")
    if digital is None:
        return
    pins = set(digital.get("pins", ()))
    signal = set(digital.get("signal_pins", ()))
    envelope = digital.get("envelope", {})
    missing = sorted(pins - signal - _enable_pins(capabilities) - set(envelope))
    if missing:
        raise _refuse(
            label,
            f"capabilities.digital_out.envelope.{missing[0]}",
            f"pin {missing[0]!r} has no envelope and is not in signal_pins; "
            "every digital.out pin is an actuator unless declared a signal pin "
            f"(no envelope for {missing})",
            f"add [capabilities.digital_out.envelope.{missing[0]}] with window_s, "
            "max_on_ms_per_window, min_interval_ms and max_continuous_ms, "
            "or list the pin in signal_pins if it drives no load",
        )


def _check_i2c(label: str, capabilities: Mapping[str, Any]) -> None:
    buses = capabilities.get("i2c", {}).get("buses", ())
    seen_buses: set[str] = set()
    for bus in buses:
        if bus["id"] in seen_buses:
            raise _refuse(
                label,
                "capabilities.i2c.buses",
                f"bus {bus['id']!r} is declared twice",
                "give each bus one entry",
            )
        seen_buses.add(bus["id"])
        names: set[str] = set()
        addresses: set[int] = set()
        for device in bus["devices"]:
            if device["name"] in names or device["address"] in addresses:
                raise _refuse(
                    label,
                    f"capabilities.i2c.buses.{bus['id']}",
                    f"device {device['name']!r} at {device['address']:#04x} repeats a name "
                    "or an address of the same bus",
                    "name and address are each unique within a bus",
                )
            names.add(device["name"])
            addresses.add(device["address"])


def _check_analog_in(label: str, capabilities: Mapping[str, Any]) -> None:
    seen: set[str] = set()
    for channel in capabilities.get("analog_in", {}).get("channels", ()):
        where = f"capabilities.analog_in.channels.{channel['name']}"
        if channel["name"] in seen:
            raise _refuse(label, where, "channel declared twice", "one entry per channel name")
        seen.add(channel["name"])
        if channel["min"] >= channel["max"]:
            raise _refuse(
                label,
                where,
                f"min ({channel['min']}) is not below max ({channel['max']})",
                "declare the scale the ADC can report, min < max; a value outside it "
                "is a read error, never clipped",
            )


def _check_motion(label: str, capabilities: Mapping[str, Any]) -> None:
    motion = capabilities.get("motion")
    if motion is None:
        return
    where = "capabilities.motion"
    names: list[str] = []
    for kind in ("motor", "servo"):
        for channel in motion.get(kind, ()):
            names.append(channel["name"])
            at = f"{where}.{kind}.{channel['name']}"
            holds = channel.get("holds_position", False)
            if channel.get("safe_state", "stop") == "hold" and not (
                holds and "max_hold_ms" in channel
            ):
                raise _refuse(
                    label,
                    at,
                    'safe_state = "hold" needs holds_position = true and max_hold_ms',
                    'a channel that cannot hold stops; declare both fields or use "stop"',
                )
            if kind == "servo" and channel["target_min"] >= channel["target_max"]:
                raise _refuse(
                    label,
                    at,
                    f"target_min ({channel['target_min']}) is not below "
                    f"target_max ({channel['target_max']})",
                    "declare the travel the servo has, target_min < target_max",
                )
    pins = set(capabilities.get("digital_out", {}).get("pins", ()))
    duplicated = sorted({name for name in names if names.count(name) > 1} | (set(names) & pins))
    if duplicated:
        raise _refuse(
            label,
            where,
            f"names {duplicated} are used more than once: across motor and servo channels, "
            "or as a digital_out pin too",
            "a name addresses exactly one pin or channel, so envelope(name) is unambiguous",
        )
    envelope = motion.get("envelope", {})
    stray = sorted(set(envelope) - set(names))
    if stray:
        raise _refuse(
            label,
            f"{where}.envelope.{stray[0]}",
            f"envelope names {stray}, which are not motion channels ({sorted(names)})",
            "name a declared channel",
        )
    missing = sorted(set(names) - set(envelope))
    if missing:
        raise _refuse(
            label,
            f"{where}.envelope.{missing[0]}",
            f"motion channel {missing[0]!r} has no envelope; every channel is an actuator "
            f"(no envelope for {missing})",
            f"add [capabilities.motion.envelope.{missing[0]}] with window_s, "
            "max_on_ms_per_window, min_interval_ms and max_continuous_ms",
        )


def validate_board_document(document: Mapping[str, Any], label: str) -> None:
    """
    Validate a board declaration against schemas/board.v1.json, then the rules a JSON
    schema cannot state: every cross-reference between the blocks (a signal pin must be
    a pin, a channel needs its envelope and enable pin) and every min <= max.
    """
    import jsonschema

    _check_declaration_keys(document, label)
    validator = jsonschema.Draft202012Validator(_board_schema())
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "<document root>"
        raise BoardCapabilityError(
            where=f"{label} -> {location}",
            why=first.message,
            how="correct the field against schemas/board.v1.json",
        )

    capabilities = document["capabilities"]
    _check_digital_out(label, capabilities)
    _check_motion_enable_pins(label, capabilities)
    _check_actuator_envelopes(label, capabilities)
    _check_i2c(label, capabilities)
    _check_analog_in(label, capabilities)
    _check_motion(label, capabilities)


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
