"""
`neuroedge add` (TSK-I2b-04, FR-DX-08): scaffold one more action, gate and test into an agent
project that `neuroedge new` made.

Each primitive has a recipe — an `@action` template, a gate template and a two-way test
template, all under `templates/add/<recipe>/` — and a list of edits to the manifest: the
`[requires]` declaration, the `[gates]` entry and the `[sim.*]` tables that feed the gate's
criteria. The edits are text edits that keep the comments of the file, then checked: the new
text must parse to exactly the old document with the intended additions, or nothing is written.

Never overwrites: a file that exists, a gate key, an action or a command name that is taken
refuses the whole add with a three-part error, and nothing is written. The manifest keeps
what it already says — a value `add` would have to change is a refusal, not a rewrite.
Everything is planned in memory first; `add` can then check the result by a build of a
scratch copy (the CLI passes that check), so a project is never left half-added.
"""

from __future__ import annotations

import json
import keyword
import re
import shutil
import tempfile
import tomllib
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import AgentManifestError, NeuroEdgeError
from . import NAME

ADD_DIR = Path(__file__).parent / "add"
KINDS = ("action", "gate", "sensor", "device")
# The core board and the board that has the extension primitives (RFC-0013 §3d).
CORE_BOARD = "sim-default"
EXTENSION_BOARD = "sim-rpi5"
EXTENSION_PRIMITIVES = frozenset({"digital.in", "analog.in", "i2c", "motion", "vision.in"})
# What an action template imports: a function of one of these names would hide it.
RESERVED = frozenset({"action", "digital", "display", "i2c", "motion"})
IDENT = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
BUS_DEVICE = re.compile(r"^[a-z][a-z0-9_]*/[a-z][a-z0-9_]*$")
BOARD_LINE = 'BOARD = "sim-default"'
# Not copied into the scratch copy a build checks: nothing a build reads, often large.
COPY_IGNORE = shutil.ignore_patterns(
    ".git", ".venv", "venv", "build", "traces", "__pycache__", ".pytest_cache", "node_modules"
)

# kind -> (primitives it reaches, the default)
PRIMITIVES: dict[str, tuple[tuple[str, ...], str | None]] = {
    "action": (("digital.out", "motion", "display", "audio.out"), "digital.out"),
    "sensor": (("sensor.read", "digital.in", "analog.in", "vision.in", "audio.in"), "sensor.read"),
    "device": (("i2c",), "i2c"),
    "gate": ((), None),
}

# What a `sensor.read` sensor becomes: a bool fact with a conservative rule (a bound is
# inclusive), the value `sim` starts at, and a reading that passes, one that does not, and one
# that cannot be trusted — the last is the fail-closed test.
SENSORS: dict[str, dict[str, Any]] = {
    "temperature": {
        "rule": {"lte": 40.0},
        "words": "nhiệt độ ≤ 40 °C",
        "initial": {"value": 25, "unit": "C"},
        "allow": "25",
        "block": "45",
        "bad": 'float("nan")',
    },
    "humidity": {
        "rule": {"lte": 80.0},
        "words": "độ ẩm ≤ 80 %",
        "initial": {"value": 50, "unit": "%"},
        "allow": "50",
        "block": "90",
        "bad": 'float("nan")',
    },
    "door_contact": {
        "rule": {"equals": True},
        "words": "cửa đang đóng",
        "initial": True,
        "allow": "True",
        "block": "False",
        "bad": '"n/a"',
    },
    "motion": {
        "rule": {"equals": False},
        "words": "không có chuyển động",
        "initial": False,
        "allow": "False",
        "block": "True",
        "bad": '"n/a"',
    },
}

# Frames 5-12 of the virtual camera hold the label (as in the `gate-watch` sample).
VISION_FRAMES = range(5, 13)


@dataclass(frozen=True)
class Edit:
    """Set `table.key = value` in a manifest; `keep` leaves a different existing value alone."""

    table: tuple[str, ...]
    key: str
    value: Any
    keep: bool = False


@dataclass
class Plan:
    """What an add writes: new files, changed files (the whole new text), notes for the user."""

    name: str
    kind: str
    primitive: str | None
    board: str
    created: dict[Path, str] = field(default_factory=dict)
    changed: dict[Path, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def files(self) -> list[Path]:
        return sorted({*self.created, *self.changed})


def _refuse(where: str, why: str, how: str) -> AgentManifestError:
    return AgentManifestError(where=where, why=why, how=how)


# -- TOML text editing -----------------------------------------------------------------------


def _key(text: str) -> str:
    return text if re.fullmatch(r"[A-Za-z0-9_-]+", text) else json.dumps(text, ensure_ascii=False)


def _value(value: Any) -> str:
    """An inline TOML value."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, Mapping):
        if not value:
            return "{}"
        return "{ " + ", ".join(f"{_key(k)} = {_value(v)}" for k, v in value.items()) + " }"
    if isinstance(value, Sequence):
        return "[" + ", ".join(_value(v) for v in value) + "]"
    raise TypeError(f"no TOML form for {value!r}")


def _merge(old: Any, new: Any, keep: bool, where: str) -> Any:
    """`old` with `new` added: dicts merge, lists take new items, equal scalars stay."""
    if isinstance(old, dict) and isinstance(new, dict):
        merged = dict(old)
        for key, item in new.items():
            merged[key] = _merge(old[key], item, keep, f"{where}.{key}") if key in old else item
        return merged
    if isinstance(old, list) and isinstance(new, list):
        return [*old, *(item for item in new if item not in old)]
    if old == new or keep:
        return old
    raise _refuse(
        where,
        f"it is already {old!r} and `neuroedge add` would need {new!r}; it never rewrites a value",
        "edit agent.toml by hand, or choose a name or an option that does not clash",
    )


def _header(table: tuple[str, ...]) -> str:
    return "[" + ".".join(_key(part) for part in table) + "]"


def _span(lines: list[str], table: tuple[str, ...]) -> tuple[int, int] | None:
    """`(header line, one past the last line of the table)` or None."""
    header = _header(table)
    for index, line in enumerate(lines):
        if line.strip().split("#")[0].strip() == header:
            for end in range(index + 1, len(lines)):
                if lines[end].lstrip().startswith("["):
                    return index, end
            return index, len(lines)
    return None


def _apply_edit(text: str, edit: Edit, merged: Any) -> str:
    """Write `merged` as the value of `edit.key` in `edit.table`, keeping the rest of the text."""
    lines = text.split("\n")
    line = f"{_key(edit.key)} = {_value(merged)}"
    span = _span(lines, edit.table)
    if span is None:
        body = text.rstrip("\n")
        return (
            f"{body}\n\n{_header(edit.table)}\n{line}\n"
            if body
            else f"{_header(edit.table)}\n{line}\n"
        )
    start, end = span
    pattern = re.compile(rf'^\s*("{re.escape(edit.key)}"|{re.escape(edit.key)})\s*=')
    for index in range(start + 1, end):
        if pattern.match(lines[index]):
            lines[index] = line
            return "\n".join(lines)
    last = start  # after the last key line: comments and blanks before the next table stay put
    for index in range(start + 1, end):
        if lines[index].strip() and not lines[index].lstrip().startswith("#"):
            last = index
    lines.insert(last + 1, line)
    return "\n".join(lines)


def edit_manifest(text: str, edits: Sequence[Edit], where: str) -> str:
    """
    `text` with `edits` applied and verified: the result must parse to the old document plus
    the edits and nothing else, so a layout this editor does not understand is a refusal, never
    a half-edited manifest.
    """
    expected = tomllib.loads(text)
    for edit in edits:
        table = expected
        for part in edit.table:
            table = table.setdefault(part, {})
            if not isinstance(table, dict):
                raise _refuse(where, f"{'.'.join(edit.table)} is not a table", "fix agent.toml")
        name = ".".join((*edit.table, edit.key))
        present = edit.key in table
        before = table.get(edit.key)
        table[edit.key] = (
            _merge(before, edit.value, edit.keep, f"{where} -> {name}")
            if present
            else deepcopy(edit.value)
        )
        if not present or table[edit.key] != before:  # an unchanged value keeps its own line
            text = _apply_edit(text, edit, table[edit.key])
    try:
        actual = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise _refuse(where, f"the edited manifest does not parse ({error})", _BY_HAND) from error
    if actual != expected:
        raise _refuse(
            where, "its layout is one `neuroedge add` cannot edit without changing it", _BY_HAND
        )
    return text


_BY_HAND = (
    "write the new lines into the manifest by hand, or restore the plain layout: one [table] "
    "header per line"
)


# -- the recipes -----------------------------------------------------------------------------


def _template(folder: str, piece: str, context: Mapping[str, str]) -> str:
    text = (ADD_DIR / folder / piece).read_text(encoding="utf-8")
    for key, value in context.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def _normal(primitive: str) -> str:
    return primitive.replace("_", ".")


def _need(option: str, value: Any, where: str, example: str) -> Any:
    if value in (None, ""):
        raise _refuse(
            where,
            f"{option} is required for this primitive: it names what the action works on",
            f"pass {option}, e.g. {example}",
        )
    return value


def _ident(option: str, value: str, where: str) -> str:
    if not IDENT.match(value):
        raise _refuse(
            where,
            f"{option} {value!r} is not a name: lowercase letters, digits and '_', starting with a letter",
            "use the name the board profile gives it (neuroedge board show <board>)",
        )
    return value


@dataclass
class Recipe:
    """What one primitive adds: template folders, context, and the manifest edits."""

    action: str | None
    gate: str
    test: str
    context: dict[str, str]
    edits: list[Edit]
    grammar_facts: dict[str, Any] | None = None


def _pin_edits(pin: str) -> list[Edit]:
    return [Edit(("requires",), "digital.out", {"pins": [pin]})]


def _recipe(  # noqa: C901 - one flat table of primitives, kept in one place
    kind: str,
    primitive: str | None,
    name: str,
    options: Mapping[str, Any],
    where: str,
) -> Recipe:
    pin = options.get("pin")
    if primitive in ("digital.out", "audio.out"):
        pin = _ident("--pin", _need("--pin", pin, where, "--pin door_lock"), where)
        edits = _pin_edits(pin)
        if primitive == "audio.out":
            edits.append(Edit(("requires",), "audio.out", {}))
        return Recipe("digital-out", "digital-out", "digital-out", {"pin": pin}, edits)
    if primitive == "motion":
        channel = _ident(
            "--channel",
            _need("--channel", options.get("channel"), where, "--channel wheel_left"),
            where,
        )
        servo = options.get("servo", False)
        folder = "motion-servo" if servo else "motion-motor"
        edits = [Edit(("requires",), "motion", {"channels": [channel]})]
        return Recipe(folder, folder, folder, {"channel": channel}, edits)
    if primitive == "display":
        return Recipe("display", "display", "display", {}, [Edit(("requires",), "display", {})])
    if primitive == "i2c":
        device = _need("--device", options.get("device"), where, "--device i2c1/ina219")
        if not BUS_DEVICE.match(device):
            raise _refuse(
                where, f"--device {device!r} is not bus/device", "write it like i2c1/ina219"
            )
        register = _need("--register", options.get("register"), where, "--register 0x02")
        bus, _, dev = device.partition("/")
        width = options.get("width", 2)
        context = {
            "device": device,
            "bus": bus,
            "dev": dev,
            "register": f"0x{register:02x}",
            "width": str(width),
        }
        edits = [
            Edit(("requires",), "i2c", {"devices": [device]}),
            Edit(("requires",), "display", {}),
            Edit(
                ("sim", "i2c", device), f"0x{register:02x}", {"value": 1, "width": width}, keep=True
            ),
        ]
        return Recipe("i2c", "i2c", "i2c", context, edits)
    # The sensors: an action on an output pin, decided by what the sensor says.
    pin = _ident("--pin", _need("--pin", pin, where, "--pin porch_light"), where)
    edits = _pin_edits(pin)
    context = {"pin": pin}
    if primitive == "audio.in":
        edits.append(Edit(("requires",), "audio.in", {"sample_rate_hz": 16000}))
        return Recipe(
            "digital-out", "audio-in", "digital-out", context, edits, {"command_recognized": True}
        )
    source = (
        _ident(
            "--source",
            _need("--source", options.get("source"), where, "--source temperature"),
            where,
        )
        if primitive != "vision.in"
        else ""
    )
    if primitive == "sensor.read":
        if source not in SENSORS:
            raise _refuse(
                where,
                f"--source {source!r} is not a sensor with a safe default rule; those are {sorted(SENSORS)}",
                "use one of them, or write the gate and [sim.sensor_facts] by hand",
            )
        spec = SENSORS[source]
        fact = f"{source}_ok"
        context.update(
            sensor=source,
            fact=fact,
            rule=spec["words"],
            allow_value=spec["allow"],
            block_value=spec["block"],
            bad_value=spec["bad"],
        )
        edits += [
            Edit(("requires",), "sensor.read", {"sensors": [source]}),
            Edit(("sim", "sensors"), source, spec["initial"], keep=True),
            Edit(("sim", "sensor_facts"), fact, {"sensor": source, **spec["rule"]}),
        ]
        return Recipe("sensor-read", "sensor-read", "sensor-read", context, edits)
    if primitive == "digital.in":
        fact = f"{source}_high"
        context.update(source=source, fact=fact)
        edits += [
            Edit(("requires",), "digital.in", {"pins": [source]}),
            Edit(("sim", "digital_facts"), fact, {"pin": source}),
            Edit(("sim", "inputs"), source, True, keep=True),
        ]
        return Recipe("digital-in", "digital-in", "digital-in", context, edits)
    if primitive == "analog.in":
        fact = f"{source}_voltage"
        context.update(source=source, fact=fact)
        edits += [
            Edit(("requires",), "analog.in", {"channels": [source]}),
            Edit(("sim", "analog_facts"), fact, {"channel": source}),
            Edit(("sim", "analog"), source, 1.8, keep=True),
        ]
        return Recipe("analog-in", "analog-in", "analog-in", context, edits)
    if primitive == "vision.in":
        label = _ident("--label", options.get("label") or "person", where)
        context.update(label=label, fact=label)
        script = {
            str(n): [{"label": label, "score": 0.93, "box": [0.4, 0.5, 0.6, 0.9]}]
            for n in VISION_FRAMES
        }
        edits += [
            Edit(
                ("requires",), "vision.in", {"min_width": 640, "min_height": 480, "min_fps": 10.0}
            ),
            Edit(("vision",), "provider", "replay"),
            Edit(("vision",), "timeout_ms", 200),
            Edit(("vision", "zones"), "watch_area", [0.25, 0.40, 0.75, 1.00]),
            Edit(("vision", "facts", f"{label}_present"), "label", label),
            Edit(("vision", "facts", f"{label}_present"), "zone", "watch_area"),
            Edit(("vision", "facts", f"{label}_present"), "kind", "present"),
            Edit(("vision", "facts", f"{label}_confidence"), "label", label),
            Edit(("vision", "facts", f"{label}_confidence"), "zone", "watch_area"),
            Edit(("vision", "facts", f"{label}_confidence"), "kind", "confidence"),
            Edit(("vision", "options"), "name", f"{label}-det"),
            Edit(("vision", "options"), "labels", [label]),
            Edit(("vision", "options"), "default", []),
            *(Edit(("vision", "options", "script"), key, value) for key, value in script.items()),
            Edit(("sim", "vision"), "source", "synthetic"),
            Edit(("sim", "vision"), "frames", 60),
        ]
        return Recipe("vision-in", "vision-in", "vision-in", context, edits)
    raise _refuse(where, f"no recipe for primitive {primitive!r}", "see neuroedge add --help")


# -- planning and writing --------------------------------------------------------------------


def _where(kind: str, name: str) -> str:
    return f"neuroedge add {kind} {name}"


def _read_toml(path: Path, where: str) -> tuple[str, dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    try:
        return text, tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise _refuse(
            f"{where} -> {path}", f"{path.name} does not parse ({error})", "fix it first"
        ) from error


def _gate_recipe(facts: Sequence[str], where: str) -> Recipe:
    facts = list(facts) or ["user_verified"]
    for fact in facts:
        _ident("--fact", fact, where)
    if len(set(facts)) != len(facts):
        raise _refuse(where, f"--fact {facts} names a fact twice", "list each fact once")
    criteria = "\n".join(
        f'  {fact}:\n    type: bool\n    instructions: "Dữ kiện {fact}: mô tả nó ở đây"'
        for fact in facts
    )
    context = {
        "criteria": criteria,
        "allow_when": "\n".join(f"  {fact}: true" for fact in facts),
        "facts": repr(facts),
    }
    # No `[sim.facts]` value: a fact the maker has not set on `sim` leaves the gate blocking.
    return Recipe(None, "gate", "gate", context, [])


def _board_for(requires: Mapping[str, Any]) -> str:
    """`sim-rpi5` when the agent needs a primitive only that board has, else `sim-default`."""
    digital = requires.get("digital.out")
    pwm = isinstance(digital, dict) and bool(digital.get("pwm"))
    needs = pwm or any(primitive in EXTENSION_PRIMITIVES for primitive in requires)
    return EXTENSION_BOARD if needs else CORE_BOARD


def plan_add(
    project: Path,
    kind: str,
    name: str,
    *,
    primitive: str | None = None,
    board: str | None = None,
    facts: Sequence[str] = (),
    manifest: str = "agent.toml",
    **options: Any,
) -> Plan:
    """The files an add writes, planned in memory; raises `AgentManifestError` if it cannot."""
    where = _where(kind, name)
    if kind not in KINDS:
        raise _refuse(where, f"unknown kind {kind!r}; available: {list(KINDS)}", "use one of them")
    if not NAME.match(name) or keyword.iskeyword(name.replace("-", "_")):
        raise _refuse(
            where,
            "a name becomes the action, gate and file names: lowercase letters, digits, '-' or '_', "
            "starting with a letter, and not a Python keyword",
            "pick a name such as open-gate or heat_guard",
        )
    ident = name.replace("-", "_")
    if ident in RESERVED:
        raise _refuse(
            where,
            f"{ident!r} is a name the generated action module imports from neuroedge; a function "
            "of that name would hide it",
            "pick another name, e.g. show-status instead of display",
        )
    manifest_path = project / manifest
    if not manifest_path.is_file():
        raise _refuse(
            str(manifest_path),
            "there is no agent.toml here: `neuroedge add` works inside an agent project",
            "cd into a project made by `neuroedge new`, or pass --agent <path/to/agent.toml>",
        )
    manifest_text, document = _read_toml(manifest_path, where)
    if not isinstance(document.get("agent", {}).get("name"), str):
        raise _refuse(
            str(manifest_path), "it has no [agent] name: not an agent manifest", "add [agent] name"
        )

    allowed, default = PRIMITIVES[kind]
    primitive = _normal(primitive) if primitive else default
    if kind != "gate" and primitive not in allowed:
        raise _refuse(
            where,
            f"--primitive {primitive!r} is not one `add {kind}` reaches; it reaches {list(allowed)}",
            "action: digital.out, motion, display, audio.out · sensor: sensor.read, digital.in, "
            "analog.in, vision.in, audio.in · device: i2c",
        )
    if kind == "gate":
        recipe = _gate_recipe(facts, where)
    else:
        recipe = _recipe(kind, primitive, name, options, where)
    if primitive == "vision.in" and "vision" in document:
        raise _refuse(
            f"{manifest_path} -> [vision]",
            "the agent already has a [vision] table, and `neuroedge add` does not merge a camera "
            "model, zones and scenes",
            "add the gate and the action for the new label by hand, beside the existing ones",
        )

    # Never overwrite: every file and every name this add needs must be free.
    paths = {
        "gate": Path("gates") / f"{name}@1.0.0.yaml",
        "test": Path("tests") / f"test_{ident}.py",
    }
    if recipe.action:
        paths["action"] = Path("actions") / f"{ident}.py"
    taken = [str(path) for path in paths.values() if (project / path).exists()]
    if taken:
        raise _refuse(
            where,
            f"{', '.join(taken)} already exist(s); nothing was written (`add` never overwrites)",
            "choose another name, or remove the file(s) first",
        )
    if name in document.get("gates", {}):
        raise _refuse(
            f"{manifest_path} -> [gates] {name}",
            "that gate key is already declared; nothing was written",
            "choose another name",
        )
    commands_path = project / "commands.toml"
    commands = commands_path.read_text(encoding="utf-8") if commands_path.is_file() else ""
    if recipe.action:
        grammar = _read_toml(commands_path, where)[1] if commands else {}
        if any(name in (c.get("intent"), c.get("tool")) for c in grammar.get("command", [])):
            raise _refuse(
                f"{commands_path} -> command {name}",
                "a command with that intent or tool already exists; nothing was written",
                "choose another name",
            )
        for path in sorted((project / "actions").glob("*.py")):
            if re.search(rf'name\s*=\s*"{re.escape(name)}"', path.read_text(encoding="utf-8")):
                raise _refuse(
                    str(path),
                    f"an @action named {name!r} is already defined; nothing was written",
                    "choose another name",
                )

    edits = [Edit(("gates",), name, paths["gate"].as_posix())]
    if kind != "gate":
        edits.append(Edit(("sim", "facts"), "user_verified", True, keep=True))
    new_manifest = edit_manifest(manifest_text, [*edits, *recipe.edits], str(manifest_path))
    requires = tomllib.loads(new_manifest).get("requires", {})
    board = board or _board_for(requires)

    context = {
        "name": name,
        "fn": ident,
        "phrase": name.replace("-", " ").replace("_", " "),
        "board": board,
        **recipe.context,
    }
    plan = Plan(name, kind, primitive, board)
    plan.changed[Path(manifest)] = new_manifest
    plan.created[paths["gate"]] = _template(recipe.gate, "gate.yaml.tmpl", context)
    plan.created[paths["test"]] = _template(recipe.test, "test.py.tmpl", context)
    if recipe.action:
        plan.created[paths["action"]] = _template(recipe.action, "action.py.tmpl", context)
        block = (
            f'[[command]]\nintent   = "{name}"\npatterns = [{_value(context["phrase"])}]\n'
            f'tool     = "{name}"\n'
        )
        if recipe.grammar_facts:
            block += f"facts    = {_value(recipe.grammar_facts)}\n"
        if commands:
            plan.changed[Path("commands.toml")] = commands.rstrip("\n") + "\n\n" + block
        else:
            header = "[grammar]\nversion   = 1\nthreshold = 0.80\n\n"
            plan.created[Path("commands.toml")] = header + block
        _check_grammar(
            plan.changed.get(Path("commands.toml")) or plan.created[Path("commands.toml")], where
        )

    # The tests already in the project load the board they were written for: every one that
    # still says the default board moves to the board this agent now needs.
    for existing in sorted((project / "tests").glob("test_*.py")) if board != CORE_BOARD else []:
        relative = existing.relative_to(project)
        if relative in plan.created:
            continue
        text = existing.read_text(encoding="utf-8")
        if BOARD_LINE in text.splitlines():
            plan.changed[relative] = text.replace(BOARD_LINE, f'BOARD = "{board}"', 1)
        elif "SimSession.load(AGENT" in text and "board_id" not in text:
            # the sample agents' tests: the same one-argument change at every load
            plan.changed[relative] = text.replace(
                "SimSession.load(AGENT", f'SimSession.load(AGENT, board_id="{board}"'
            )
        elif "SimSession.load(" in text and "board_id" not in text:
            plan.notes.append(
                f"{relative} loads the default board {CORE_BOARD}, which lacks what this agent "
                f"now requires: pass board_id={board!r} to SimSession.load there"
            )
    if board != CORE_BOARD:
        plan.notes.append(
            f"this agent now needs board {board}: neuroedge build --target sim --board {board}"
        )
        if "esp32s3" in document.get("targets", {}).get("supported", []):
            plan.notes.append(
                "esp32s3-box-3 declares none of the extension primitives: take esp32s3 out of "
                "[targets] supported, or the build for it will refuse"
            )
    return plan


def _check_grammar(text: str, where: str) -> None:
    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise _refuse(
            where, f"the edited commands.toml does not parse ({error})", _BY_HAND
        ) from error


def _as_project(error: NeuroEdgeError, scratch: str, project: str) -> None:
    """Make `error` and the problems it carries name the project, not the scratch copy."""
    for each in (error, *getattr(error, "problems", ())):
        for part in ("where", "why", "how"):
            setattr(each, part, getattr(each, part).replace(scratch, project))


def _write(root: Path, plan: Plan) -> None:
    for relative, text in plan.created.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as handle:  # never clobbers, even in a race
            handle.write(text)
    for relative, text in plan.changed.items():
        (root / relative).write_text(text, encoding="utf-8")


def add(
    project: Path,
    kind: str,
    name: str,
    *,
    check: Callable[[Path, str], None] | None = None,
    manifest: str = "agent.toml",
    **options: Any,
) -> Plan:
    """
    Plan an add, check it, then write it.

    `check(agent_toml, board)` runs on a scratch copy of the project with the add applied and
    raises if the result does not build: the project itself is written only after it passes.
    """
    plan = plan_add(project, kind, name, manifest=manifest, **options)
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
