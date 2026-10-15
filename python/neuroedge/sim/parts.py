"""
The parts catalogue and `[sim.parts]` of agent.toml (docs/spec/virtual_parts.md §3.2, Q-84 phase B).

A part is one entry of `[sim.parts]`: a name, a kind from `parts.toml`, the pin, sensor or channel it
is wired to, and the words the page shows. Parts describe; they never add a requirement: the target
of every part must already be in the agent's `[requires]` (VP-PT-03), which stays the one declaration
`build` checks on every target. An output part can also make its pin's envelope on `sim-virtual`
tighter than its kind's preset, never looser (VP-PT-04); on any other board it changes nothing.
"""

from __future__ import annotations

import math
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..errors import AgentManifestError, NeuroEdgeError

CATALOGUE = Path(__file__).with_name("parts.toml")

# How each primitive names its targets in `[requires]` (display has none: it is one flag).
REQUIRES_KEY = {
    "digital.out": "pins",
    "digital.in": "pins",
    "sensor.read": "sensors",
    "analog.in": "channels",
    "motion": "channels",
}
TARGET_KEYS = ("pin", "sensor", "channel")
# The primitives `SimHAL` implements (VP-PT-02): a kind names one of them and adds none.
SIM_PRIMITIVES = frozenset(
    {"digital.out", "digital.in", "sensor.read", "analog.in", "motion", "display"}
)
KIND_KEYS = frozenset({"primitive", "target", "word", "unit", "range", "envelope", "element"})
# An output part may tighten these (VP-PT-04). `window_s` is not one: a shorter window with the same
# budget would be looser, not tighter.
ENVELOPE_FIELDS = ("max_on_ms_per_window", "max_continuous_ms", "min_interval_ms")
PRESET_WINDOW = {"window_s": 3600, "max_on_ms_per_window": 600000}


@dataclass(frozen=True)
class Kind:
    name: str
    primitive: str
    target: str | None
    word: str
    unit: str | None = None
    range: tuple[float, float] | None = None
    envelope: Mapping[str, int] | None = None
    element: str | None = None


@dataclass(frozen=True)
class Part:
    name: str
    kind: Kind
    target: str | None
    label: str | None
    unit: str | None
    range: tuple[float, float] | None
    envelope: Mapping[str, int]  # only the fields the part itself gives (tighter than the preset)

    @property
    def shown(self) -> str:
        """What the page calls it: the part's label, else the kind's default word."""
        return self.label or self.kind.word


def _bad_catalogue(why: str) -> AgentManifestError:
    return AgentManifestError(
        where=str(CATALOGUE), why=why, how="fix the catalogue; docs/spec/virtual_parts.md §4.2"
    )


@lru_cache(maxsize=1)
def catalogue() -> dict[str, Kind]:
    """The kinds of `parts.toml`, in file order (VP-PT-02)."""
    table = tomllib.loads(CATALOGUE.read_text(encoding="utf-8")).get("kinds", {})
    kinds: dict[str, Kind] = {}
    for name, entry in table.items():
        if set(entry) - KIND_KEYS or entry.get("primitive") not in SIM_PRIMITIVES:
            raise _bad_catalogue(
                f"kind {name!r} must use only {sorted(KIND_KEYS)} and name one of the primitives "
                f"{sorted(SIM_PRIMITIVES)}"
            )
        target = entry.get("target")
        if (target is None) != (entry["primitive"] == "display") or target not in (
            None,
            *TARGET_KEYS,
        ):
            raise _bad_catalogue(
                f"kind {name!r}: `target` is pin, sensor or channel (none: display)"
            )
        kinds[name] = Kind(
            name=name,
            primitive=entry["primitive"],
            target=target,
            word=entry["word"],
            unit=entry.get("unit"),
            range=tuple(entry["range"]) if "range" in entry else None,
            envelope=dict(entry["envelope"]) if "envelope" in entry else None,
            element=entry.get("element"),
        )
    return kinds


def listing() -> str:
    """`neuroedge add part --list`: the catalogue as the spec's table shows it."""
    rows = []
    for kind in catalogue().values():
        wired = f"--{kind.target} <name>" if kind.target else "(no target)"
        reads = ""
        if kind.range:
            lo, hi = (f"{bound:g}" for bound in kind.range)
            reads = f"{lo}…{hi} {kind.unit or ''}".strip()
        rows.append(f"{kind.name:<12} {kind.primitive:<12} {wired:<19} {kind.word:<14} {reads}")
    return "\n".join(rows)


def _tightest(
    part: str, where: str, preset: Mapping[str, int], given: Mapping[str, Any]
) -> dict[str, int]:
    """The fields a part gives for its envelope: each one at least as strict as its kind's preset."""
    full = {**PRESET_WINDOW, **preset}
    out: dict[str, int] = {}
    for field in ENVELOPE_FIELDS:
        if field not in given:
            continue
        value = given[field]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise AgentManifestError(
                where=f"{where} {field}",
                why=f"part {part!r}: {field} = {value!r} is not a positive whole number of milliseconds",
                how=f"write {field} = {full[field]}, or a stricter value",
            )
        # Tighter is smaller for a budget, larger for the pause between two switchings.
        looser = value < full[field] if field == "min_interval_ms" else value > full[field]
        if looser:
            raise AgentManifestError(
                where=f"{where} {field}",
                why=(
                    f"part {part!r}: {field} = {value} is looser than its kind's preset "
                    f"({full[field]}); a part can make a pin safer, never looser (VP-PT-04)"
                ),
                how=f"write {field} = {full[field]}, or a {'larger' if field == 'min_interval_ms' else 'smaller'} value, or remove it",
            )
        out[field] = value
    return out


def _range(part: str, where: str, value: Any) -> tuple[float, float]:
    numbers = (
        isinstance(value, list)
        and len(value) == 2
        and all(
            isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v)
            for v in value
        )
    )
    if not numbers or value[0] >= value[1]:
        raise AgentManifestError(
            where=f"{where} range",
            why=f"part {part!r}: range = {value!r} is not two numbers, lowest first",
            how="write range = [0, 14]",
        )
    return (value[0], value[1])


def parse_parts(source: Path, document: Mapping[str, Any]) -> dict[str, Part]:
    """
    The `[sim.parts]` of an agent.toml document (VP-PT-01, VP-PT-03), or an `AgentManifestError`
    naming the part that is wrong. No `[sim.parts]`: no parts.
    """
    sim = document.get("sim", {})
    table = sim.get("parts") if isinstance(sim, Mapping) else None
    if table is None:
        return {}
    kinds = catalogue()
    if not isinstance(table, Mapping):
        raise AgentManifestError(
            where=f"{source} -> [sim.parts]",
            why=f"[sim.parts] must be a table of parts, found {table!r}",
            how='declare each part as [sim.parts.heater] with kind = "heater" and pin = "heater"',
        )
    requires = document.get("requires", {})
    parts: dict[str, Part] = {}
    claimed: dict[tuple[str, str], str] = {}
    for name, entry in table.items():
        where = f"{source} -> [sim.parts.{name}]"
        if not isinstance(entry, Mapping):
            raise AgentManifestError(
                where=where,
                why=f"part {name!r} must be a table, found {entry!r}",
                how=f'write [sim.parts.{name}] with kind = "..." and the pin, sensor or channel it is wired to',
            )
        kind = kinds.get(entry.get("kind")) if isinstance(entry.get("kind"), str) else None
        if kind is None:
            raise AgentManifestError(
                where=f"{where} kind",
                why=f"part {name!r}: kind {entry.get('kind')!r} is not in the catalogue; kinds are {list(kinds)}",
                how="use one of them (neuroedge add part --list), or add the kind to parts.toml in a PR",
            )
        allowed = {"kind", "label"}
        if kind.target:
            allowed.add(kind.target)
        if kind.primitive == "digital.out":
            allowed.update(ENVELOPE_FIELDS)
        if kind.primitive == "sensor.read":
            allowed.update({"range", "unit"})
        elif kind.range:
            allowed.add("range")
        unknown = sorted(set(entry) - allowed - (set(TARGET_KEYS) - {kind.target}))
        if unknown:
            raise AgentManifestError(
                where=where,
                why=f"part {name!r} ({kind.name}): unknown key(s) {unknown}; a {kind.name} takes {sorted(allowed)}",
                how="remove them, or use the keys listed",
            )
        given = [key for key in TARGET_KEYS if key in entry]
        wrong = [key for key in given if key != kind.target]
        if wrong and kind.target in entry:
            raise AgentManifestError(
                where=where,
                why=f"part {name!r} ({kind.name}) is wired twice: `{kind.target}` and `{wrong[0]}`",
                how=f"keep `{kind.target}` only",
            )
        if wrong:
            raise AgentManifestError(
                where=f"{where} {wrong[0]}",
                why=(
                    f"part {name!r}: a {kind.name} is {kind.primitive}, which is wired with "
                    f"`{kind.target}`, not `{wrong[0]}`"
                    if kind.target
                    else f"part {name!r}: a {kind.name} is a {kind.primitive} and has no pin, sensor or channel"
                ),
                how=f'write {kind.target} = "..."' if kind.target else f"remove `{wrong[0]}`",
            )
        target = entry.get(kind.target) if kind.target else None
        if kind.target and (not isinstance(target, str) or not target):
            raise AgentManifestError(
                where=f"{where} {kind.target}",
                why=f"part {name!r} ({kind.name}) needs its target: `{kind.target}` is "
                + ("missing" if kind.target not in entry else f"{target!r}, not a name"),
                how=f'write {kind.target} = "{name}"',
            )
        if kind.target is None and kind.primitive not in requires:
            raise AgentManifestError(
                where=f"{source} -> [requires] {kind.primitive}",
                why=f"part {name!r} ({kind.name}) is a {kind.primitive}, and [requires] does not declare it",
                how=f'add "{kind.primitive}" = {{}} to [requires]',
            )
        if kind.target:
            declared = (
                requires.get(kind.primitive, {}).get(REQUIRES_KEY[kind.primitive], [])
                if isinstance(requires.get(kind.primitive), Mapping)
                else []
            )
            if target not in declared:
                raise AgentManifestError(
                    where=f"{where} {kind.target}",
                    why=(
                        f"part {name!r} is wired to {kind.target} {target!r}, but [requires] "
                        f"{kind.primitive} does not declare it (VP-PT-03); parts describe, they "
                        "never add a requirement"
                    ),
                    how=(
                        f'add {target!r} to [requires] "{kind.primitive}" '
                        f"{REQUIRES_KEY[kind.primitive]}, or use `neuroedge add part`, which writes both"
                    ),
                )
            other = claimed.get((kind.primitive, target))
            if other is not None:
                raise AgentManifestError(
                    where=where,
                    why=f"parts {other!r} and {name!r} are both wired to {kind.primitive} {target!r}",
                    how="one part per pin, sensor or channel",
                )
            claimed[(kind.primitive, target)] = name
        label = entry.get("label")
        if label is not None and (not isinstance(label, str) or not label.strip()):
            raise AgentManifestError(
                where=f"{where} label",
                why=f"part {name!r}: label = {label!r} is not a word for people",
                how='write label = "Máy sưởi"',
            )
        unit = entry.get("unit", kind.unit)
        if not isinstance(unit, str | type(None)):
            raise AgentManifestError(
                where=f"{where} unit",
                why=f"part {name!r}: unit = {unit!r} is not a string",
                how='write unit = "pH"',
            )
        bounds = _range(name, where, entry["range"]) if "range" in entry else kind.range
        envelope = (
            _tightest(name, where, kind.envelope or {}, entry)
            if kind.primitive == "digital.out"
            else {}
        )
        parts[name] = Part(
            name, kind, target, label.strip() if label else None, unit, bounds, envelope
        )
    return parts


def agent_parts(manifest: Any) -> dict[str, Part]:
    """`[sim.parts]` of a loaded agent, checked."""
    try:
        document = tomllib.loads(manifest.source.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}  # `load_agent_manifest` has said what is wrong with the file
    return parse_parts(manifest.source, document)


def part_envelopes(manifest: Any) -> dict[str, dict[str, int]]:
    """
    `{pin: envelope}` of the output parts on `sim-virtual` (VP-PT-04): the kind's preset with the
    fields the part tightens. Only `virtual_board` calls it, so no other board's envelope moves.
    """
    return {
        part.target: {**PRESET_WINDOW, **(part.kind.envelope or {}), **part.envelope}
        for part in agent_parts(manifest).values()
        if part.kind.primitive == "digital.out" and part.target is not None
    }


def sensor_ranges(manifest: Any) -> dict[str, tuple[Any, tuple[float, float], str | None]]:
    """`{sensor: (part name, (lowest, highest), unit)}` of the sensor parts that have a range."""
    return {
        part.target: (part.name, part.range, part.unit)
        for part in agent_parts(manifest).values()
        if part.kind.primitive == "sensor.read" and part.target and part.range
    }


def check_reading(
    ranges: Mapping[str, tuple[Any, tuple[float, float], str | None]], sensor: str, value: Any
) -> None:
    """
    VP-PT-05: refuse a number outside the range of the sensor's part. Anything that is not a
    number ("lỗi", NaN, a bool) is no reading, which stays allowed: a lost probe is still testable.
    """
    if sensor not in ranges or isinstance(value, bool) or not isinstance(value, int | float):
        return
    part, (low, high), unit = ranges[sensor]
    if math.isnan(value) or low <= value <= high:
        return
    shown = f"{low:g}…{high:g}" + (f" {unit}" if unit else "")
    raise NeuroEdgeError(
        where=f"sensor {sensor} (part {part})",
        why=f"{value:g} is outside the range {shown} of this sensor; nothing was changed",
        how=f"type a value from {low:g} to {high:g}, or a word such as lỗi for a lost signal",
    )


def describe_parts(manifest: Any) -> list[dict[str, Any]]:
    """What the page needs of each part (VP-PT-06): its words, kind, unit and range."""
    return [
        {
            "name": part.name,
            "kind": part.kind.name,
            "primitive": part.kind.primitive,
            "target": part.target,
            "label": part.shown,
            "word": part.kind.word,
            "unit": part.unit,
            "range": list(part.range) if part.range else None,
        }
        for part in agent_parts(manifest).values()
    ]
