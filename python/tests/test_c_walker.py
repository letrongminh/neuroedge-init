"""
TSK-S4-02 / TSK-S4-07 — the C99 walker decides exactly as the host engine does.

The walker in `targets/esp32s3/components/ne_gate/` is compiled on this host
with AddressSanitizer and UndefinedBehaviorSanitizer and run against:

* every recorded truth table in `fixtures/decision_trees/` (verdict, reason,
  failing criterion as recorded — independent of today's Python);
* for every gate in `gates/`, the fixture corpus and the sample agents: the
  truth-table rows and seeded random facts and arguments, each decided by the
  real `ActionContractEngine` (with and without a person's confirmation), and
  again with gathering degraded — a source offline, a source timing out, the
  evaluation overrunning its budget — through `ne_decide` (`fail: open|closed`);
* byte-level fuzzing of every tree (truncation, corruption, hostile structure).

Plus the static budget: no `.data`/`.bss` in the walker object, and every
function's stack frame under `STACK_LIMIT` bytes (`-fstack-usage`).
A missing C compiler is a failure, not a skip.
"""

from __future__ import annotations

import asyncio
import json
import math
import random
import re
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

from neuroedge.engine import ActionContractEngine, EventLog
from neuroedge.engine.binary_tree import (
    HEADER_SIZE,
    LAYOUT_VERSION,
    MAX_NODES,
    c_header,
    domain_index,
    encode,
)
from neuroedge.engine.decision_tree import compile_tree, truth_cases
from neuroedge.engine.gate_resolver import GateRegistry, resolve_gate_document, resolve_gate_file
from neuroedge.engine.verdict import Fact, Unavailable
from neuroedge.errors import GateSchemaError

STACK_LIMIT = 512  # bytes per function; the walker has no recursion
REASONS = {
    None: 0,
    "condition_not_met": 1,
    "criterion_unavailable": 2,
    "confidence_unavailable": 3,
    "argument_out_of_range": 4,
    "gate_unreachable": 5,
    "budget_exceeded": 6,
}
FAIL_MODES = {None: 0, "open": 1, "closed": 2}
DEGRADED_NONE, DEGRADED_UNREACHABLE, DEGRADED_BUDGET = 0, 1, 2
T_STRING, T_INTEGER, T_NUMBER, T_BOOLEAN, T_OTHER = 0, 1, 2, 3, 7


@pytest.fixture(scope="module")
def component(root) -> Path:
    return root / "targets" / "esp32s3" / "components" / "ne_gate"


def cc() -> str:
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    assert compiler, "a C compiler (cc/gcc/clang) is required for the walker conformance tests"
    return compiler


STRICT = ["-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Wconversion", "-Wshadow", "-Werror"]


@pytest.fixture(scope="module")
def runner(component, tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("walker") / "test_walker_host"
    command = [
        cc(),
        *STRICT[:-1],  # the test program itself is not held to -Wconversion
        "-O1",
        "-g",
        "-fsanitize=address,undefined",
        "-fno-sanitize-recover=all",
        "-fno-omit-frame-pointer",
        "-I",
        str(component / "include"),
        str(component / "src" / "ne_walker.c"),
        str(component / "test" / "test_walker_host.c"),
        "-o",
        str(out),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return out


# --- trees under test --------------------------------------------------------------------------


def trees(root) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for path in sorted((root / "gates").rglob("*.yaml")):
        found[path.stem] = compile_tree(resolve_gate_file(path))
    fixtures = GateRegistry(root / "fixtures" / "gates" / "registry")
    for path in sorted((root / "fixtures" / "gates" / "valid").glob("*.yaml")):
        found["fixture:" + path.stem] = compile_tree(resolve_gate_file(path, registry=fixtures))
    for path in sorted((root / "fixtures" / "agents").glob("*/gates/*.yaml")):
        found[f"agent:{path.parent.parent.name}:{path.stem}"] = compile_tree(
            resolve_gate_file(path)
        )
    found["synthetic:every-limit"] = compile_tree(SYNTHETIC)
    return found


SYNTHETIC = resolve_gate_document(
    {
        "schema": "neuroedge.gate/v1",
        "name": "every-limit",
        "version": "1.0.0",
        "arguments": {
            "duration_s": {"type": "integer", "minimum": 1, "maximum": 60},
            "level": {"type": "number", "minimum": -1.5, "maximum": 2.25},
            "mode": {"type": "string", "enum": ["eco", "bình thường"], "max_length": 11},
            "note": {"type": "string", "max_length": 5},
            "count": {"type": "integer", "enum": [1, 2, 3]},
            "force": {"type": "boolean", "enum": [False]},
        },
        "evaluate": {
            "room_empty": {"type": "bool", "instructions": "Nobody in the room"},
            "risk": {"type": "level", "levels": ["low", "medium", "high"], "instructions": "Risk"},
            "channel": {"type": "choice", "options": ["web", "app", "voice"], "instructions": "Ch"},
            "verified": {"type": "bool", "instructions": "Verified"},
        },
        "allow_when": {
            "room_empty": True,
            "risk": {"lte": "medium"},
            "channel": {"in": ["app", "voice"]},
            "verified": {"confidence_gte": 0.8},
        },
        "on_block": {"action": "ask", "message": "Chắc chứ?", "confirms": ["room_empty", "risk"]},
        "budget": {"p95_latency_ms": 200},
    }
)


# --- the cases ---------------------------------------------------------------------------------


def random_fact(node, rng: random.Random):
    pick = rng.random()
    if pick < 0.1:
        return None
    if pick < 0.15:
        return Fact(None)
    if pick < 0.25:
        value = rng.choice(["__out_of_domain__", 1, "true", 0.5])
    elif node["kind"] == "bool":
        value = rng.choice([True, False])
    else:
        value = rng.choice(node["domain"])
    floor = node["confidence_floor"]
    confidence = rng.choice(
        [
            None,
            1.0,
            0.0,
            rng.random(),
            floor,
            max(0.0, round(floor - 0.001, 6)),
            1.5,
            -0.1,
            float("nan"),
            True,
        ]
    )
    return Fact(value, confidence)


def random_argument(limit, rng: random.Random):
    kind = limit["type"]
    pick = rng.random()
    if pick < 0.08:
        return "__absent__"
    if pick < 0.12:
        return None
    if pick < 0.2:
        return rng.choice([True, False, 7, 2.5, "x", ["list"]])
    if kind == "boolean":
        return rng.choice([True, False])
    if kind == "string":
        pool = list(limit.get("enum", [])) + ["", "eco", "bình thường", "gió", "abcdef", "ạ" * 6]
        return rng.choice(pool)
    low, high = limit.get("minimum", -5), limit.get("maximum", 5)
    candidates = [low, high, low - 1, high + 1, (low + high) / 2, *limit.get("enum", [])]
    value = rng.choice(candidates)
    if kind == "integer":
        return rng.choice([int(value), float(int(value)), value + 0.5])
    return value


def cases(tree, rng: random.Random, random_rows: int = 400):
    rows = []
    limits = tree.get("arguments") or []
    base_args = {limit["name"]: _in_range(limit) for limit in limits}
    for row in truth_cases(tree):
        facts = {name: Fact(cell["value"], cell["confidence"]) for name, cell in row.items()}
        for confirmed in (False, True):
            rows.append((facts, dict(base_args), confirmed))
    for _ in range(random_rows):
        facts = {}
        for node in tree["nodes"]:
            fact = random_fact(node, rng)
            if fact is not None:
                facts[node["criterion"]] = fact
        args = {}
        for limit in limits:
            value = random_argument(limit, rng) if rng.random() < 0.5 else base_args[limit["name"]]
            if value != "__absent__":
                args[limit["name"]] = value
        rows.append((facts, args, rng.random() < 0.5))
    return rows


def _in_range(limit):
    if "enum" in limit:
        return limit["enum"][0]
    return {
        "boolean": False,
        "string": "",
        "integer": int(limit.get("minimum", 0)),
        "number": float(limit.get("minimum", 0.0)),
    }[limit["type"]]


class _Down:
    """A fact source that cannot answer: offline (gate_unreachable) or timing out."""

    def __init__(self, reason: str) -> None:
        self.answer = Unavailable(reason, "test")

    async def adjudicate(self, criterion, definition, state, deadline_ms=None):
        return self.answer


def _overrun_clock(p95):
    """t0, then every later reading past the budget: the evaluation overran p95."""
    readings = iter([0.0])
    return lambda: next(readings, p95 + 1.0)


async def engine_decision(tree_gate, facts, args, confirmed, source=None, clock=None):
    """What the real host engine decides — the reference the C walker must match."""
    kwargs = {} if clock is None else {"clock": clock}
    engine = ActionContractEngine(events=EventLog(), facts_source=source, **kwargs)
    engine.register("g", tree_gate)
    return await engine.evaluate("g", facts, arguments=args, confirmed=confirmed)


def degraded_cases(tree, rng: random.Random, rows: int = 120):
    """
    (facts, args, confirmed, degraded, source, clock): gathering that failed, as the
    engine meets it. A source is asked only for a fact the context lacks, so an
    offline or timing-out source degrades only then; an overrun budget degrades
    even with every fact given. When the host would not degrade, neither does C.
    """
    out = []
    names = [node["criterion"] for node in tree["nodes"]]
    for facts, args, confirmed in cases(tree, rng, random_rows=rows)[-rows:]:
        if rng.random() < 0.6 and names:
            facts = {k: v for k, v in facts.items() if k != rng.choice(names)}
        missing = any(name not in facts for name in names)
        kind = rng.choice(["offline", "timeout", "overrun"])
        if kind == "overrun":
            p95 = tree["budget"]["p95_latency_ms"]
            out.append((facts, args, confirmed, DEGRADED_BUDGET, None, _overrun_clock(p95)))
        elif missing:
            degraded = DEGRADED_UNREACHABLE if kind == "offline" else DEGRADED_BUDGET
            out.append((facts, args, confirmed, degraded, _Down(kind), None))
        else:
            out.append((facts, args, confirmed, DEGRADED_NONE, _Down(kind), None))
    return out


def expected_from_engine(tree, result):
    names = [n["criterion"] for n in tree["nodes"]]
    arg_names = [a["name"] for a in tree.get("arguments") or []]
    verdict = 0 if str(result.verdict) == "ALLOW" else 1
    reason = REASONS[None if result.reason is None else str(result.reason)]
    kind = index = 0
    if verdict == 1 and result.failed_criterion is not None:
        if reason == REASONS["argument_out_of_range"]:
            kind, index = 2, arg_names.index(result.failed_criterion)
        else:
            kind, index = 1, names.index(result.failed_criterion)
    confirmed_mask = sum(1 << names.index(c) for c in result.confirmed)
    answerable = 1 if result.confirms else 0
    return verdict, reason, kind, index, answerable, confirmed_mask, FAIL_MODES[result.fail_mode]


# --- encoding a case for the C runner ---------------------------------------------------------


def encode_fact(node, fact) -> bytes:
    if fact is None or fact.value is None:
        return struct.pack("<BBBBId", 0, 0, 0, 0, 0, 0.0)
    index = domain_index(node, fact.value)
    confidence = fact.confidence
    has = confidence is not None
    valid_number = isinstance(confidence, (int, float)) and not isinstance(confidence, bool)
    value = float(confidence) if has and valid_number else math.nan
    return struct.pack(
        "<BBBBId", 1, 0 if index is None else 1, index or 0, 1 if has else 0, 0, value
    )


def encode_arg(args, name) -> bytes:
    if name not in args or args[name] is None:
        return struct.pack("<BBHId64s", 0, 0, 0, 0, 0.0, b"")
    value = args[name]
    raw = b""
    if isinstance(value, bool):
        kind, number = T_BOOLEAN, float(value)
    elif isinstance(value, int):
        kind, number = T_INTEGER, float(value)
    elif isinstance(value, float):
        kind, number = (T_INTEGER if value.is_integer() else T_NUMBER), value
    elif isinstance(value, str):
        kind, number, raw = T_STRING, 0.0, value.encode("utf-8")
    else:
        kind, number = T_OTHER, 0.0
    assert len(raw) <= 64
    return struct.pack("<BBHId64s", 1, kind, len(raw), 0, number, raw)


def write_cases(path: Path, tree, rows) -> None:
    """Rows are (facts, args, confirmed, expected[, degraded]); `expected` may omit fail_mode."""
    limits = tree.get("arguments") or []
    body = bytearray(struct.pack("<4sIIII", b"NEVC", 2, len(tree["nodes"]), len(limits), len(rows)))
    for facts, args, confirmed, expected, *rest in rows:
        degraded = rest[0] if rest else DEGRADED_NONE
        for node in tree["nodes"]:
            body += encode_fact(node, facts.get(node["criterion"]))
        for limit in limits:
            body += encode_arg(args, limit["name"])
        verdict, reason, kind, index, answerable, mask, *mode = expected
        fail_mode = mode[0] if mode else 0
        body += struct.pack(
            "<BBBBBBBBI",
            1 if confirmed else 0,
            verdict,
            reason,
            kind,
            index,
            answerable,
            degraded,
            fail_mode,
            mask,
        )
    path.write_bytes(bytes(body))


# --- the tests -----------------------------------------------------------------------------------


def test_the_c_walker_matches_the_host_engine_on_every_gate(root, runner, tmp_path):
    rng = random.Random(20260924)
    argv = [str(runner)]
    total = 0
    degraded_rows = {"open": 0, "closed": 0, "None": 0}
    for name, tree in trees(root).items():
        gate = _gate_for(root, name)
        rows = []
        for facts, args, confirmed in cases(tree, rng):
            result = asyncio.run(engine_decision(gate, facts, args, confirmed))
            rows.append((facts, args, confirmed, expected_from_engine(tree, result)))
        # Few gates declare `fail: open`, and open is where degraded verdicts differ most.
        many = 1500 if tree["budget"]["fail"] == "open" else 120
        for facts, args, confirmed, degraded, source, clock in degraded_cases(tree, rng, many):
            result = asyncio.run(engine_decision(gate, facts, args, confirmed, source, clock))
            degrades = result.fail_mode is not None or (
                degraded != DEGRADED_NONE and not result.allowed and result.reason is not None
            )
            assert degrades or degraded == DEGRADED_NONE, (name, facts, result)
            rows.append((facts, args, confirmed, expected_from_engine(tree, result), degraded))
            degraded_rows[str(result.fail_mode)] += degraded != DEGRADED_NONE
        stem = re.sub(r"[^a-z0-9_.-]", "_", name.lower())
        (tmp_path / f"{stem}.netree").write_bytes(encode(tree))
        write_cases(tmp_path / f"{stem}.nevc", tree, rows)
        argv += [str(tmp_path / f"{stem}.netree"), str(tmp_path / f"{stem}.nevc")]
        total += len(rows)
    result = subprocess.run(argv, capture_output=True, text=True, timeout=600)
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
    assert "ALL OK" in result.stdout
    assert total > 5000
    # Both fail modes met, and a fail-open known "no" that still blocks (fail_mode None).
    assert min(degraded_rows.values()) > 50, degraded_rows


def _gate_for(root, name):
    if name == "synthetic:every-limit":
        return SYNTHETIC
    if name.startswith("fixture:"):
        path = root / "fixtures" / "gates" / "valid" / (name.split(":", 1)[1] + ".yaml")
        return resolve_gate_file(
            path, registry=GateRegistry(root / "fixtures" / "gates" / "registry")
        )
    if name.startswith("agent:"):
        _, agent, stem = name.split(":", 2)
        return resolve_gate_file(root / "fixtures" / "agents" / agent / "gates" / f"{stem}.yaml")
    return resolve_gate_file(next((root / "gates").rglob(f"{name}.yaml")))


def test_the_c_walker_reproduces_the_recorded_truth_tables(root, runner, tmp_path):
    """The recorded verdicts, reasons and failing criteria — not recomputed in Python."""
    argv = [str(runner)]
    for table_path in sorted((root / "fixtures" / "decision_trees").glob("*.truth.json")):
        table = json.loads(table_path.read_text("utf-8"))
        gate_file = next((root / "gates").rglob(table["gate"] + ".yaml"))
        tree = compile_tree(resolve_gate_file(gate_file))
        assert tree["gate_digest"] == table["gate_digest"], "the truth table is stale"
        names = [n["criterion"] for n in tree["nodes"]]
        rows = []
        for row in table["rows"]:
            facts = {n: Fact(c["value"], c["confidence"]) for n, c in row["facts"].items()}
            verdict = 0 if row["verdict"] == "ALLOW" else 1
            failed = row["failed_criterion"]
            expected = (
                verdict,
                REASONS[row["reason"]],
                1 if failed else 0,
                names.index(failed) if failed else 0,
                0,  # these gates declare no confirms
                0,
            )
            rows.append((facts, {}, False, expected))
        stem = table["gate"].replace("@", "_")
        (tmp_path / f"{stem}.netree").write_bytes(encode(tree))
        write_cases(tmp_path / f"{stem}.nevc", tree, rows)
        argv += [str(tmp_path / f"{stem}.netree"), str(tmp_path / f"{stem}.nevc")]
    assert len(argv) > 1
    result = subprocess.run(argv, capture_output=True, text=True, timeout=600)
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]


def test_the_walker_uses_no_static_ram_and_a_small_stack(component, tmp_path):
    obj = tmp_path / "ne_walker.o"
    command = [
        cc(),
        *STRICT,
        "-O2",
        "-fstack-usage",
        "-I",
        str(component / "include"),
        "-c",
        str(component / "src" / "ne_walker.c"),
        "-o",
        str(obj),
    ]
    result = subprocess.run(command, capture_output=True, text=True, cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    symbols = subprocess.run(["nm", str(obj)], capture_output=True, text=True, check=True).stdout
    writable = [line for line in symbols.splitlines() if re.search(r"\s[bBdDC]\s", line)]
    assert writable == [], f"the walker must hold no .data/.bss state: {writable}"
    usage = (tmp_path / "ne_walker.su").read_text()
    frames = {m.group(1): int(m.group(2)) for m in re.finditer(r":(\w+)\s+(\d+)\s+\w+", usage)}
    assert "ne_evaluate" in frames and "ne_tree_load" in frames, usage
    assert max(frames.values()) <= STACK_LIMIT, frames


def test_the_layout_header_is_what_rfc_0003_freezes(root):
    tree = compile_tree(resolve_gate_file(root / "gates" / "unlock_door@1.2.0.yaml"))
    blob = encode(tree)
    magic, version, header_size = struct.unpack_from("<4sHH", blob, 0)
    assert (magic, version, header_size) == (b"NETR", LAYOUT_VERSION, HEADER_SIZE)
    assert blob[8:40] == bytes.fromhex(tree["gate_digest"].removeprefix("sha256:"))
    assert encode(tree) == blob  # deterministic: same gate, same bytes


def test_a_gate_too_large_for_the_device_is_refused_at_build():
    criteria = {f"c{i}": {"type": "bool", "instructions": "x"} for i in range(MAX_NODES + 1)}
    gate = resolve_gate_document(
        {
            "schema": "neuroedge.gate/v1",
            "name": "too-big",
            "version": "1.0.0",
            "evaluate": criteria,
            "allow_when": dict.fromkeys(criteria, True),
            "on_block": {"action": "deny"},
            "budget": {"p95_latency_ms": 100},
        }
    )
    with pytest.raises(GateSchemaError, match="limit of 32"):
        encode(compile_tree(gate))


def test_the_c_header_embeds_the_same_bytes(root):
    tree = compile_tree(resolve_gate_file(root / "gates" / "unlock_door@1.2.0.yaml"))
    header = c_header(tree, "unlock_door")
    listed = bytes(int(x, 16) for x in re.findall(r"0x([0-9a-f]{2})", header))
    assert listed == encode(tree)
    assert f"static const uint8_t ne_tree_unlock_door[{len(listed)}]" in header


def test_build_writes_the_device_tree_next_to_the_json(root, tmp_path):
    from neuroedge.engine.compiler import build

    agent = root / "fixtures" / "agents" / "home-voice" / "agent.toml"
    report = build(agent, target="sim", board_id="sim-default", out_dir=tmp_path)
    names = sorted(p.name for p in report.artifacts)
    assert "light_off.netree" in names and "light_off.netree.h" in names
    assert (tmp_path / "gates" / "light_off.netree").read_bytes()[:4] == b"NETR"
