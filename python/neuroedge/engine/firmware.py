"""
The ESP-IDF project `neuroedge build --target esp32s3` writes (TSK-I3-01, FR-CLI-02, FR-TGT-03).

The firmware in `targets/esp32s3/` is the same for every agent. What is the
agent's own is one generated component, `components/ne_agent/`:

* each gate as `NETR` v1 bytes linked into flash (`gates/<key>.netree.h`, RFC-0003),
  byte for byte the `<key>.netree.h` the build writes next to the tree;
* the gate table: label, digest and `on_block` texts, which NETR v1 does not carry
  (`TODOS.md` #36);
* the pin table — the agent's `digital.out` pins; pin i is bit i of a token's pin mask;
* the action table — each @action, the gate that guards it and the pins its token may
  drive (its named `digital.out` requirements, as the host's token grants them);
* the boot self-test's checks: for every gate, facts varied one criterion at a time,
  and the **host engine's** verdict on them (`ActionContractEngine`, not a copy of it).
  The device decides every check with the C walker and refuses to start the gate
  runtime on the first disagreement (`main/gate_selftest.c`).

The build copies the firmware sources next to the component, so `<out>/esp32s3/` is a
complete project for `idf.py` (`docs/user/nap-firmware.md`). Rendering is pure: the
same agent gives the same bytes, and nothing is written until every check passed.

What the device does not do yet, the generated firmware does not pretend to: no GPIO
moves (the HAL on the chip is TSK-S4-01), and the pin table has names, not GPIO numbers.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import AgentManifestError, BoardCapabilityError, NeuroEdgeError
from .binary_tree import MAX_NODES, c_header, c_string, domain_index, encode
from .decision_tree import OUT_OF_DOMAIN, compile_tree
from .gate import ActionContractEngine, GateResult
from .gate_resolver import ResolvedGate
from .trace_sink import EventLog
from .verdict import Fact, Unavailable

# The project's directory under `--out`, and the component the build owns in it.
PROJECT_DIR = "esp32s3"
COMPONENT = "components/ne_agent"
# Written last, listing every file the build wrote: a later build removes only those.
MANIFEST = ".neuroedge-build"
MANIFEST_HEADER = "# Written by `neuroedge build --target esp32s3` (TSK-I3-01). Do not edit."

# The firmware sources copied into every project, relative to targets/esp32s3/.
# Host-only tooling (Makefiles, test/) and build output are not part of it.
SOURCES = (
    "CMakeLists.txt",
    "partitions.csv",
    "sdkconfig.defaults",
    "sdkconfig.qemu",
    "main/CMakeLists.txt",
    "main/Kconfig.projbuild",
    "main/*.c",
    "main/*.h",
    "main/idf_component.yml",
    "main/vectors/*.h",
    "components/ne_gate/CMakeLists.txt",
    "components/ne_gate/include/*.h",
    "components/ne_gate/src/*.c",
    "components/ne_trace/CMakeLists.txt",
    "components/ne_trace/include/*.h",
    "components/ne_trace/src/*.c",
)
# Without these the copy is not a firmware; `main/idf_component.yml` is optional.
REQUIRED = (
    "CMakeLists.txt",
    "main/main.c",
    "main/gate_selftest.c",
    "components/ne_gate/src/ne_walker.c",
)

MAX_PINS = 32  # NE_MAX_PINS: a token's pin mask is a u32
MAX_ENTRIES = 0xFFFF  # the tables index gates with u16
NO_NODE = 255  # NE_AGENT_NO_NODE: a check that varies no criterion
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# ne_walker.h enums, as python/tests/test_c_walker.py pins them against the walker.
_REASONS = {
    None: 0,
    "condition_not_met": 1,
    "criterion_unavailable": 2,
    "confidence_unavailable": 3,
    "argument_out_of_range": 4,
    "gate_unreachable": 5,
    "budget_exceeded": 6,
}
_FAIL_MODES = {None: 0, "open": 1, "closed": 2}
_DEGRADED_NONE, _DEGRADED_UNREACHABLE = 0, 1
_ARG_STRING, _ARG_INTEGER, _ARG_NUMBER, _ARG_BOOLEAN = 0, 1, 2, 3


def firmware_root(root: Path | None = None) -> Path:
    """`targets/esp32s3/` of the asset root (a checkout, or the copy in the wheel)."""
    from ..paths import repo_root

    return (root or repo_root()) / "targets" / "esp32s3"


# --- checks the firmware adds to the build ---------------------------------------------------


def firmware_problems(
    manifest: Any, gates: Mapping[str, ResolvedGate], source: Path | None = None
) -> list[NeuroEdgeError]:
    """
    What makes an agent impossible to link into the firmware, each as a three-part
    error: gate keys that are not C identifiers (or collide once upper-cased, as the
    header guards are), a gate without criteria (the walker refuses to load it), more
    pins than a token mask holds, and missing firmware sources.
    """
    problems: list[NeuroEdgeError] = []
    guards: dict[str, str] = {}
    for key, gate in gates.items():
        where = f"{manifest.source} -> [gates] {key}"
        if not _IDENT.fullmatch(key):
            problems.append(
                AgentManifestError(
                    where=where,
                    why=f"{key!r} names the gate's C symbol ne_tree_{key} in the firmware, "
                    "and it is not a C identifier",
                    how="rename the key to letters, digits and underscores, starting with a "
                    "letter (and the gate= of its @action with it)",
                )
            )
        elif key.upper() in guards:
            problems.append(
                AgentManifestError(
                    where=where,
                    why=f"{key!r} and {guards[key.upper()]!r} differ only in case; their "
                    f"firmware headers share the guard NE_TREE_{key.upper()}_H",
                    how="give the two gates keys that differ in more than case",
                )
            )
        else:
            guards[key.upper()] = key
        try:
            tree = compile_tree(gate)
        except NeuroEdgeError:
            continue  # already one of the build's problems (resolve_gates)
        try:
            encode(tree)  # the device layout's limits (RFC-0003)
        except NeuroEdgeError as error:
            problems.append(error)
            continue
        if not tree["nodes"]:
            problems.append(
                AgentManifestError(
                    where=f"{where} ({gate.name}@{gate.version})",
                    why="the gate has no allow_when criterion; the device walker refuses to "
                    "load a tree without one (RFC-0003), so the gate could never run",
                    how="give the gate at least one allow_when criterion",
                )
            )
    pins = _pins(manifest)
    if len(pins) > MAX_PINS:
        problems.append(
            BoardCapabilityError(
                where=f"{manifest.source} -> [requires] digital.out",
                why=f"{len(pins)} pins; a device token grants pins as bits of a u32 mask, "
                f"so the firmware has room for {MAX_PINS}",
                how=f"declare at most {MAX_PINS} digital.out pins for esp32s3",
            )
        )
    if len(gates) > MAX_ENTRIES:
        problems.append(
            AgentManifestError(
                where=f"{manifest.source} -> [gates]",
                why=f"{len(gates)} gates; the firmware tables index at most {MAX_ENTRIES}",
                how="split the agent",
            )
        )
    problems += _source_problems(source or firmware_root())
    return problems


def _source_problems(source: Path) -> list[NeuroEdgeError]:
    missing = [name for name in REQUIRED if not (source / name).is_file()]
    if not missing:
        return []
    return [
        NeuroEdgeError(
            where=str(source),
            why=f"the firmware sources are not here (missing {missing}): this install of "
            "neuroedge has no targets/esp32s3/ to build a firmware from",
            how="build from a NeuroEdge checkout, or set NEUROEDGE_ROOT=<checkout>",
        )
    ]


def _pins(manifest: Any) -> list[str]:
    return list(manifest.requires.get("digital.out", {}).get("pins", []))


# --- the self-test's checks -------------------------------------------------------------------


@dataclass(frozen=True)
class Check:
    """One row the device decides at boot, and the host engine's answer."""

    node: int | None  # the criterion varied from the baseline; None: the baseline as is
    fact: Fact | None  # its fact; None: removed
    confirmed: bool
    degraded: int
    expected: tuple[int, int, int, int, int, int, int]
    note: str


class _Offline:
    """A fact source that cannot answer: the degraded check (`gate_unreachable`)."""

    async def adjudicate(self, criterion, definition, state, deadline_ms=None):
        return Unavailable("offline", "firmware self-test")


def _value(node: Mapping[str, Any], raw: str) -> bool | str:
    return (raw == "true") if node["kind"] == "bool" else raw


def _argument(limit: Mapping[str, Any]) -> Any:
    """A value for one argument limit: the self-test decides every check with it."""
    if "enum" in limit:
        return limit["enum"][0]
    kind = limit["type"]
    if kind == "boolean":
        return False
    if kind == "string":
        return ""
    bound = limit.get("minimum", limit.get("maximum", 0))
    return int(bound) if kind == "integer" else float(bound)


def _expected(tree: Mapping[str, Any], result: GateResult) -> tuple[int, ...]:
    """The host's verdict in the walker's fields (ne_result), as test_c_walker compares them."""
    names = [node["criterion"] for node in tree["nodes"]]
    arguments = [limit["name"] for limit in tree.get("arguments") or []]
    verdict = 0 if result.allowed else 1
    reason = _REASONS[None if result.reason is None else str(result.reason)]
    kind = index = 0
    if verdict == 1 and result.failed_criterion is not None:
        if reason == _REASONS["argument_out_of_range"]:
            kind, index = 2, arguments.index(result.failed_criterion)
        else:
            kind, index = 1, names.index(result.failed_criterion)
    mask = sum(1 << names.index(name) for name in result.confirmed)
    answerable = 1 if result.confirms else 0
    return verdict, reason, kind, index, answerable, _FAIL_MODES[result.fail_mode], mask


def baseline(tree: Mapping[str, Any]) -> dict[str, Fact]:
    """Every criterion at its first admitted value, fully confident; unsatisfiable ones absent."""
    return {
        node["criterion"]: Fact(_value(node, node["admitted"][0]), 1.0)
        for node in tree["nodes"]
        if node["admitted"]
    }


def arguments(tree: Mapping[str, Any]) -> dict[str, Any]:
    return {limit["name"]: _argument(limit) for limit in tree.get("arguments") or []}


def checks(key: str, gate: ResolvedGate) -> list[Check]:
    """
    The rows of one gate: the baseline; then, one criterion at a time, every value of
    its domain, the fact removed, a value outside the domain and — under a confidence
    floor — no confidence, just below, at, and outside [0, 1]; one degraded row (a
    fact missing, its source offline: `fail` decides); and, for a gate that asks
    (RFC-0006), each row a person's "có" could change, confirmed.

    Each row is decided by the real host engine, with a fixed clock so no budget runs out.
    """
    tree = compile_tree(gate)
    base = baseline(tree)
    variants: list[tuple[int | None, Fact | None, str]] = [(None, None, "baseline")]
    for index, node in enumerate(tree["nodes"]):
        name = node["criterion"]
        present = base.get(name)
        for raw in node["domain"]:
            fact = Fact(_value(node, raw), 1.0)
            if fact != present:
                variants.append((index, fact, f"{name} = {raw}"))
        if present is not None:
            variants.append((index, None, f"{name} missing"))
        variants.append((index, Fact(OUT_OF_DOMAIN, 1.0), f"{name} outside its domain"))
        floor = node["confidence_floor"]
        if floor > 0 and node["admitted"]:
            admitted = _value(node, node["admitted"][0])
            for confidence, what in (
                (None, "no confidence"),
                (round(floor - 0.001, 6), "confidence below the floor"),
                (floor, "confidence at the floor"),
                (1.5, "confidence outside [0, 1]"),
            ):
                variants.append((index, Fact(admitted, confidence), f"{name}: {what}"))

    args = arguments(tree)

    def decide(node, fact, confirmed, degraded) -> tuple[int, ...]:
        facts = dict(base)
        if node is not None:
            name = tree["nodes"][node]["criterion"]
            facts.pop(name, None)
            if fact is not None:
                facts[name] = fact
        engine = ActionContractEngine(
            {key: gate},
            facts_source=_Offline() if degraded else None,
            clock=lambda: 0.0,
            events=EventLog(lambda: 0.0),
        )
        result = asyncio.run(engine.evaluate(key, facts, arguments=args, confirmed=confirmed))
        return _expected(tree, result)

    rows = [
        Check(node, fact, False, _DEGRADED_NONE, decide(node, fact, False, False), note)
        for node, fact, note in variants
    ]
    removable = next((i for i, n in enumerate(tree["nodes"]) if n["criterion"] in base), None)
    rows.append(
        Check(
            removable,
            None,
            False,
            _DEGRADED_UNREACHABLE,
            decide(removable, None, False, True),
            "a fact missing and its source offline",
        )
    )
    on_block = tree["on_block"]
    if on_block.get("action") == "ask" and on_block.get("confirms"):
        for row in list(rows):
            verdict, answerable = row.expected[0], row.expected[4]
            if row.degraded or not (verdict == 0 or answerable):
                continue  # a confirmed BLOCK reads in a trace as an unconfirmed one
            rows.append(
                Check(
                    row.node,
                    row.fact,
                    True,
                    _DEGRADED_NONE,
                    decide(row.node, row.fact, True, False),
                    f"{row.note}, confirmed",
                )
            )
    return rows


# --- C ---------------------------------------------------------------------------------------


def _comment(text: str) -> str:
    """Text safe inside a C block comment: no `*/`, no trigraph, ASCII only."""
    return re.sub(r"[^A-Za-z0-9 _@.:=,()\[\]<>+-]", "_", text)


def _double(value: float) -> str:
    text = repr(float(value))
    return text if any(c in text for c in ".e") else f"{text}.0"


def _fact(node: Mapping[str, Any], fact: Fact | None) -> str:
    """A `ne_fact` initializer: present, in_domain, index, has_confidence, confidence."""
    if fact is None or fact.value is None:
        return "{0u, 0u, 0u, 0u, 0.0}"
    index = domain_index(node, fact.value)  # the walker's view, as the vectors write it
    has = fact.confidence is not None
    confidence = _double(fact.confidence) if has else "0.0"
    return f"{{1u, {int(index is not None)}u, {index or 0}u, {int(has)}u, {confidence}}}"


def _arg(value: Any) -> str:
    """A `ne_arg_value` initializer: present, type, str_len, str, number."""
    if isinstance(value, bool):
        return f"{{1u, {_ARG_BOOLEAN}u, 0u, NULL, {1.0 if value else 0.0}}}"
    if isinstance(value, str):
        return f"{{1u, {_ARG_STRING}u, {len(value.encode('utf-8'))}u, {c_string(value)}, 0.0}}"
    number = float(value)
    kind = _ARG_INTEGER if number.is_integer() else _ARG_NUMBER
    return f"{{1u, {kind}u, 0u, NULL, {_double(number)}}}"


def _text(gate: ResolvedGate) -> str:
    return (
        "{"
        + ", ".join(
            c_string(gate.on_block[key]) if gate.on_block.get(key) else "NULL"
            for key in ("to", "message", "fallback_action")
        )
        + "}"
    )


def _header(label: str, board: str, max_nodes: int) -> str:
    return f"""/* Generated by `neuroedge build --target esp32s3` from {_comment(label)} — do not edit. */
/*
 * The agent linked into this image (TSK-I3-01): its gates as NETR v1 trees in flash,
 * its digital.out pins, its @actions with the gate and pins of each, and the checks
 * the boot self-test decides with the C walker (main/gate_selftest.c). Every expected
 * verdict is the host engine's (python/neuroedge/engine/gate.py) for the same facts.
 */
#ifndef NE_AGENT_H
#define NE_AGENT_H

#include <stdint.h>

#include "ne_trace.h"
#include "ne_walker.h"

#ifdef __cplusplus
extern "C" {{
#endif

#define NE_AGENT_VERSION {c_string(label)}
#define NE_AGENT_BOARD {c_string(board)}
/* The most criteria of any gate of this agent: the self-test's fact buffer. */
#define NE_AGENT_MAX_NODES {max_nodes}u
#define NE_AGENT_NO_NODE {NO_NODE}u

typedef struct {{
    const char *label;          /* "light_on@1.0.0" */
    const uint8_t *tree;        /* NETR v1 bytes, in flash */
    uint32_t tree_size;
    uint8_t digest[32];         /* the gate digest the host compiled the tree from */
    uint16_t node_count;
    ne_on_block_text text;      /* what NETR v1 does not carry (TODOS.md #36) */
    const ne_fact *baseline;    /* self-test: one fact per criterion */
    const ne_arg_value *args;   /* self-test: one value per argument limit, or NULL */
}} ne_agent_gate;

typedef struct {{
    const char *name;           /* the @action */
    uint16_t gate;              /* index into gates: the gate that guards it */
    uint32_t pin_mask;          /* bit i = pins[i]: what a token for it may drive */
}} ne_agent_action;

typedef struct {{
    uint16_t gate;              /* index into gates */
    uint8_t node;               /* the criterion this check varies, or NE_AGENT_NO_NODE */
    uint8_t confirmed;          /* a person said "co" (RFC-0006) */
    uint8_t degraded;           /* ne_degraded */
    /* The host engine's answer, field by field as ne_result has it. */
    uint8_t verdict;
    uint8_t reason;
    uint8_t failed_kind;
    uint8_t failed_index;
    uint8_t answerable;
    uint8_t fail_mode;
    uint32_t confirmed_mask;
    ne_fact fact;               /* the fact of `node` (present 0: removed) */
}} ne_agent_check;

typedef struct {{
    const char *version;
    const char *board;
    const ne_agent_gate *gates;
    uint32_t gate_count;
    const char *const *pins;
    uint32_t pin_count;
    const ne_agent_action *actions;
    uint32_t action_count;
    const ne_agent_check *checks;
    uint32_t check_count;
}} ne_agent;

/* The agent this image was built for. */
extern const ne_agent ne_agent_linked;

#ifdef __cplusplus
}}
#endif

#endif /* NE_AGENT_H */
"""


_CMAKE = """# Generated by `neuroedge build --target esp32s3` — do not edit.
# The agent linked into this image (TSK-I3-01): include/ne_agent.h.
idf_component_register(SRCS "ne_agent.c"
                       INCLUDE_DIRS "include"
                       REQUIRES ne_gate ne_trace)
target_compile_options(${COMPONENT_LIB} PRIVATE -std=c99 -Wall -Wextra -Wconversion -Werror)
"""


def _source(
    manifest: Any,
    gates: Mapping[str, ResolvedGate],
    rows: Mapping[str, list[Check]],
    actions: list[tuple[str, int, int]],
) -> str:
    pins = _pins(manifest)
    keys = list(gates)
    out = [
        f"/* Generated by `neuroedge build --target esp32s3` from {_comment(manifest.label)} "
        "— do not edit. */",
        "/* The agent's tables (ne_agent.h). */",
        '#include "ne_agent.h"',
        "",
        "#include <stddef.h>",
        "",
        *(f'#include "gates/{key}.netree.h"' for key in keys),
        "",
    ]
    table: list[str] = []
    check_rows: list[str] = []
    for g, key in enumerate(keys):
        gate = gates[key]
        tree = compile_tree(gate)
        nodes = tree["nodes"]
        base = baseline(tree)
        out.append(
            f"static const ne_fact ne_agent_baseline_{g}[{len(nodes)}] = "
            f"{{{', '.join(_fact(n, base.get(n['criterion'])) for n in nodes)}}};"
        )
        args = arguments(tree)
        if args:
            out.append(
                f"static const ne_arg_value ne_agent_args_{g}[{len(args)}] = "
                f"{{{', '.join(_arg(value) for value in args.values())}}};"
            )
        digest = bytes.fromhex(tree["gate_digest"].removeprefix("sha256:"))
        table.append(
            f"    {{{c_string(tree['gate'])}, ne_tree_{key}, (uint32_t)sizeof ne_tree_{key},\n"
            f"     {{{', '.join(f'0x{b:02x}' for b in digest)}}},\n"
            f"     {len(nodes)}u, {_text(gate)}, ne_agent_baseline_{g}, "
            f"{f'ne_agent_args_{g}' if args else 'NULL'}}},"
        )
        check_rows.append(f"    /* {_comment(tree['gate'])} */")
        for row in rows[key]:
            node = NO_NODE if row.node is None else row.node
            fact = "{0u, 0u, 0u, 0u, 0.0}" if row.node is None else _fact(nodes[row.node], row.fact)
            verdict, reason, kind, index, answerable, fail_mode, mask = row.expected
            check_rows.append(
                f"    {{{g}u, {node}u, {int(row.confirmed)}u, {row.degraded}u, {verdict}u, "
                f"{reason}u, {kind}u, {index}u, {answerable}u, {fail_mode}u, 0x{mask:x}u, "
                f"{fact}}}, /* {_comment(row.note)} */"
            )
    out.append("")

    def array(ctype: str, name: str, body: list[str]) -> list[str]:
        if not body:
            return []
        return [f"static const {ctype} {name}[{_count(body)}] = {{", *body, "};", ""]

    out += array("ne_agent_gate", "ne_agent_gate_table", table)
    out += array("char *const", "ne_agent_pin_table", [f"    {c_string(pin)}," for pin in pins])
    out += array(
        "ne_agent_action",
        "ne_agent_action_table",
        [f"    {{{c_string(name)}, {gate}u, 0x{mask:x}u}}," for name, gate, mask in actions],
    )
    out += array("ne_agent_check", "ne_agent_check_table", check_rows)
    counts = {
        "gate": len(table),
        "pin": len(pins),
        "action": len(actions),
        "check": sum(len(rows[key]) for key in keys),
    }
    fields = []
    for name in ("gate", "pin", "action", "check"):
        fields.append(f"ne_agent_{name}_table" if counts[name] else "NULL")
        fields.append(f"{counts[name]}u")
    out += [
        "const ne_agent ne_agent_linked = {",
        "    NE_AGENT_VERSION, NE_AGENT_BOARD,",
        *(f"    {fields[i]}, {fields[i + 1]}," for i in range(0, len(fields), 2)),
        "};",
        "",
    ]
    return "\n".join(out)


def _count(body: list[str]) -> int:
    return sum(1 for line in body if not line.lstrip().startswith("/*"))


def action_table(
    manifest: Any, gates: Mapping[str, ResolvedGate], specs: Iterable[Any]
) -> list[tuple[str, int, int]]:
    """(name, gate index, pin mask) per @action, sorted by name — the pins its token may drive."""
    keys = list(gates)
    pins = _pins(manifest)
    return [
        (spec.name, keys.index(spec.gate), sum(1 << pins.index(pin) for pin in spec.pins))
        for spec in sorted(specs, key=lambda spec: spec.name)
    ]


def _macro(*parts: str) -> str:
    return "_".join(re.sub(r"[^A-Z0-9]", "_", str(part).upper()) for part in parts)


def _indices(manifest: Any, gates: Mapping[str, ResolvedGate]) -> str:
    """
    Positions for code written against this one agent (the host tests of the firmware):
    `NE_GATE_<KEY>_<CRITERION>` = criterion index, `..._<VALUE>` = domain index,
    `NE_GATE_<KEY>_GATE` / `_NODES` / `_ON_BLOCK_TEXT`, `NE_PIN_<PIN>` = pin index. A name
    two things would share is defined for neither: no code gets the other's index.
    """
    macros: list[tuple[str, str]] = []
    for key, gate in gates.items():
        tree = compile_tree(gate)
        macros.append((_macro("NE_GATE", key, "GATE"), c_string(tree["gate"])))
        macros.append((_macro("NE_GATE", key, "ON_BLOCK_TEXT"), _text(gate)))
        macros.append((_macro("NE_GATE", key, "NODES"), f"{len(tree['nodes'])}u"))
        for i, node in enumerate(tree["nodes"]):
            macros.append((_macro("NE_GATE", key, node["criterion"]), f"{i}u"))
            for j, value in enumerate(node["domain"]):
                macros.append((_macro("NE_GATE", key, node["criterion"], value), f"{j}u"))
    for i, pin in enumerate(_pins(manifest)):
        macros.append((_macro("NE_PIN", pin), f"{i}u"))
    seen: dict[str, int] = {}
    for name, _ in macros:
        seen[name] = seen.get(name, 0) + 1
    lines = [
        f"/* Generated by `neuroedge build --target esp32s3` from {_comment(manifest.label)} "
        "— do not edit. */",
        "/* Criterion, domain and pin positions of this agent, for code written against it */",
        "/* (the firmware's host tests). The firmware itself never includes this header. */",
        "#ifndef NE_AGENT_INDICES_H",
        "#define NE_AGENT_INDICES_H",
    ]
    for name, value in macros:
        if seen[name] > 1:
            lines.append(f"/* {name}: two names share it, so it is not defined */")
        else:
            lines.append(f"#define {name} {value}")
    return "\n".join([*dict.fromkeys(lines), "#endif /* NE_AGENT_INDICES_H */", ""])


def render_component(
    manifest: Any, board: str, gates: Mapping[str, ResolvedGate], specs: Iterable[Any]
) -> dict[str, str]:
    """Every file of `components/ne_agent/`, keyed by its path in the component."""
    rows = {key: checks(key, gate) for key, gate in gates.items()}
    trees = {key: compile_tree(gate) for key, gate in gates.items()}
    max_nodes = max([len(tree["nodes"]) for tree in trees.values()] + [1])
    assert max_nodes <= MAX_NODES  # encode() refuses more
    files = {
        "CMakeLists.txt": _CMAKE,
        "include/ne_agent.h": _header(manifest.label, board, max_nodes),
        "include/ne_agent_indices.h": _indices(manifest, gates),
        "ne_agent.c": _source(manifest, gates, rows, action_table(manifest, gates, specs)),
    }
    for key, tree in trees.items():
        files[f"gates/{key}.netree.h"] = c_header(tree, key)
    return files


def render_project(
    manifest: Any,
    board: str,
    gates: Mapping[str, ResolvedGate],
    specs: Iterable[Any],
    source: Path | None = None,
) -> dict[str, bytes]:
    """
    The whole project, keyed by its path under `<out>/esp32s3/`: the firmware
    sources as they are in `targets/esp32s3/`, the agent's component, and the
    manifest of what was written. Sorted, so two renders are the same bytes.
    """
    source = source or firmware_root()
    files: dict[str, bytes] = {}
    for pattern in SOURCES:
        for path in sorted(source.glob(pattern)):
            if path.is_file():
                files[path.relative_to(source).as_posix()] = path.read_bytes()
    for name, text in render_component(manifest, board, gates, specs).items():
        files[f"{COMPONENT}/{name}"] = text.encode("utf-8")
    listing = [MANIFEST_HEADER, f"agent {manifest.label}", *sorted(files)]
    files[MANIFEST] = ("\n".join(listing) + "\n").encode("utf-8")
    return dict(sorted(files.items()))


def previous_files(project: Path) -> list[str] | None:
    """
    The files an earlier build wrote into `project`, or None when `project` holds
    anything this build did not write (it is then never touched).
    """
    if not project.exists():
        return []
    marker = project / MANIFEST
    if marker.is_file():
        lines = marker.read_text(encoding="utf-8").splitlines()
        if lines and lines[0] == MANIFEST_HEADER:
            return [line for line in lines[2:] if line and not line.startswith("#")]
    if project.is_dir() and not any(project.iterdir()):
        return []
    return None


def project_problem(project: Path) -> NeuroEdgeError | None:
    if previous_files(project) is not None:
        return None
    return NeuroEdgeError(
        where=str(project),
        why="the directory exists and was not written by `neuroedge build --target esp32s3` "
        f"(no {MANIFEST}): building would overwrite files that are not the build's",
        how="pass another --out, or move that directory away",
    )


def write_project(project: Path, files: Mapping[str, bytes]) -> None:
    """
    Write the project; remove only files an earlier build listed and this one does not
    write. Build output (`build/`, `sdkconfig`) and anything else is left alone.
    """
    earlier = previous_files(project)
    if earlier is None:
        problem = project_problem(project)
        assert problem is not None
        raise problem
    root = project.resolve()
    for name in earlier:
        path = project / name
        if name not in files and path.is_file() and root in path.resolve().parents:
            path.unlink()
    for name, data in files.items():
        if name == MANIFEST:
            continue
        path = project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (project / MANIFEST).write_bytes(files[MANIFEST])
