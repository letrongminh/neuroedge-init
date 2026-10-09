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
import zlib
from pathlib import Path

import pytest

from neuroedge.engine import ActionContractEngine, EventLog
from neuroedge.engine.binary_tree import (
    HEADER_SIZE,
    LAYOUT_VERSION,
    MAX_DOMAIN,
    MAX_NODES,
    MAX_NUMERIC,
    NUMERIC_SIZE,
    c_header,
    domain_index,
    encode,
)
from neuroedge.engine.decision_tree import compile_tree, facts_from_row, truth_cases
from neuroedge.engine.firmware import (
    ARG_BOOLEAN,
    ARG_INTEGER,
    ARG_NUMBER,
    ARG_STRING,
    DEGRADED_BUDGET,
    DEGRADED_NONE,
    DEGRADED_UNREACHABLE,
    REASONS,
)
from neuroedge.engine.firmware import expected as expected_from_engine
from neuroedge.engine.gate_resolver import GateRegistry, resolve_gate_document, resolve_gate_file
from neuroedge.engine.verdict import Fact, Unavailable
from neuroedge.errors import GateSchemaError

STACK_LIMIT = 512  # bytes per function; the walker has no recursion
# The walker's enums come from the one host copy the firmware generator ships with
# (`neuroedge.engine.firmware`): deciding every gate here pins that copy, not a twin.
T_STRING, T_INTEGER, T_NUMBER, T_BOOLEAN = ARG_STRING, ARG_INTEGER, ARG_NUMBER, ARG_BOOLEAN
T_OTHER = 7  # no JSON type the walker knows: every limit refuses it


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
    found["synthetic:mixed-criteria"] = compile_tree(SYNTHETIC_MIXED)
    found["synthetic:mixed-open"] = compile_tree(SYNTHETIC_MIXED_OPEN)
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


SYNTHETIC_MIXED = resolve_gate_document(
    {
        "schema": "neuroedge.gate/v1",
        "name": "mixed-criteria",
        "version": "1.0.0",
        "arguments": {
            "rate": {"type": "number", "minimum": 0.0, "maximum": 100.0},
        },
        "evaluate": {
            "room_empty": {"type": "bool", "instructions": "Room is empty"},
            "speed": {
                "type": "level",
                "levels": ["low", "medium", "high"],
                "instructions": "Speed",
            },
            "mode": {
                "type": "choice",
                "options": ["manual", "auto", "test"],
                "instructions": "Mode",
            },
            "temp": {
                "type": "numeric",
                "unit": "celsius",
                "range": {"min": -20.0, "max": 120.0},
                "max_age_ms": 500,
                "instructions": "Temperature",
            },
        },
        "allow_when": {
            "room_empty": True,
            "speed": {"lte": "medium"},
            "mode": {"in": ["auto", "test"]},
            "temp": {"gte": 10.0, "lt": 80.0},
        },
        "on_block": {"action": "deny"},
        "budget": {"p95_latency_ms": 150},
    }
)


SYNTHETIC_MIXED_OPEN = resolve_gate_document(
    {
        "schema": "neuroedge.gate/v1",
        "name": "mixed-open",
        "version": "1.0.0",
        "evaluate": {
            "door_closed": {"type": "bool", "instructions": "Door is closed"},
            "pressure": {
                "type": "numeric",
                "unit": "bar",
                "range": {"min": 0.0, "max": 16.0},
                "max_age_ms": 500,
                "instructions": "Pressure",
            },
        },
        "allow_when": {"door_closed": True, "pressure": {"gte": 1.0, "lte": 8.0}},
        "on_block": {"action": "deny"},
        # `fail: open` excuses what a source could not say, never a lost numeric sensor.
        "budget": {"p95_latency_ms": 150, "fail": "open"},
    }
)


# --- the cases ---------------------------------------------------------------------------------


def random_fact(node, rng: random.Random):
    pick = rng.random()
    if pick < 0.1:
        return None
    if pick < 0.15:
        return Fact(None)
    if node["kind"] == "numeric":
        num = node["numeric"]
        rmin = float(num["range"]["min"])
        rmax = float(num["range"]["max"])
        max_age = int(num["max_age_ms"])
        candidates = [
            True,
            False,
            "bad",
            rmin,
            rmax,
            rmin - 10.0,
            rmax + 10.0,
            (rmin + rmax) / 2.0,
            float("nan"),
            float("inf"),
            float("-inf"),
        ]
        for bound in (num.get("lower"), num.get("upper")):
            if bound is not None:
                bv = float(bound["value"])
                candidates.extend([bv, math.nextafter(bv, -math.inf), math.nextafter(bv, math.inf)])
        candidates.append(rng.uniform(rmin, rmax))
        value = rng.choice(candidates)
        age_ms = rng.choice([None, -1, 0, max_age, max_age + 1, 100_000])
        return Fact(value, age_ms=age_ms)
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
    if rng.random() < 0.15:  # NaN compares False with every bound; both sides must refuse it
        return rng.choice([float("nan"), float("inf"), float("-inf")])
    return value


def cases(tree, rng: random.Random, random_rows: int = 400):
    rows = []
    limits = tree.get("arguments") or []
    base_args = {limit["name"]: _in_range(limit) for limit in limits}
    for row in truth_cases(tree):
        facts = facts_from_row(row)
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


class _WalkerEngine(ActionContractEngine):
    """The harness hands the engine readings with their ages already set, as replay does."""

    def _numeric_marks(self, criterion, fact, eval_offset_ms):
        if fact.age_ms is None:
            return None
        return eval_offset_ms - fact.age_ms, eval_offset_ms, fact.age_ms


async def engine_decision(tree_gate, facts, args, confirmed, source=None, clock=None):
    """What the real host engine decides — the reference the C walker must match."""
    kwargs = {} if clock is None else {"clock": clock}
    engine = _WalkerEngine(events=EventLog(), facts_source=source, **kwargs)
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


# --- encoding a case for the C runner ---------------------------------------------------------


def encode_fact(node, fact) -> bytes:
    if fact is None or fact.value is None:
        return struct.pack("<BBBBIddq", 0, 0, 0, 0, 0, 0.0, 0.0, 0)
    if node["kind"] == "numeric":
        val = fact.value
        bad_val = isinstance(val, bool) or not isinstance(val, (int, float))
        bad_age = (
            fact.age_ms is None or isinstance(fact.age_ms, bool) or not isinstance(fact.age_ms, int)
        )
        if bad_val or bad_age:
            fval = 0.0
            age = -1
        else:
            try:
                fval = float(val)
            except OverflowError:
                fval = math.inf
            age = fact.age_ms
        return struct.pack("<BBBBIddq", 1, 0, 0, 0, 0, 0.0, fval, age)
    index = domain_index(node, fact.value)
    confidence = fact.confidence
    has = confidence is not None
    valid_number = isinstance(confidence, (int, float)) and not isinstance(confidence, bool)
    value = float(confidence) if has and valid_number else math.nan
    return struct.pack(
        "<BBBBIddq", 1, 0 if index is None else 1, index or 0, 1 if has else 0, 0, value, 0.0, 0
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
    """
    Rows are (facts, args, confirmed, expected[, degraded]); `expected` is the tuple of
    `neuroedge.engine.firmware.expected`: verdict, reason, failed kind, failed index,
    answerable, fail mode, confirmed mask.
    """
    limits = tree.get("arguments") or []
    body = bytearray(struct.pack("<4sIIII", b"NEVC", 3, len(tree["nodes"]), len(limits), len(rows)))
    for facts, args, confirmed, expected, *rest in rows:
        degraded = rest[0] if rest else DEGRADED_NONE
        for node in tree["nodes"]:
            body += encode_fact(node, facts.get(node["criterion"]))
        for limit in limits:
            body += encode_arg(args, limit["name"])
        verdict, reason, kind, index, answerable, fail_mode, mask = expected
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
    if name == "synthetic:mixed-criteria":
        return SYNTHETIC_MIXED
    if name == "synthetic:mixed-open":
        return SYNTHETIC_MIXED_OPEN
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
            facts = facts_from_row(row["facts"])
            verdict = 0 if row["verdict"] == "ALLOW" else 1
            failed = row["failed_criterion"]
            expected = (
                verdict,
                REASONS[row["reason"]],
                1 if failed else 0,
                names.index(failed) if failed else 0,
                0,  # these gates declare no confirms
                0,  # nor a degraded verdict
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


# Each mutant breaks one line of the numeric path of the walker; the conformance run against
# the host engine must fail for every one (RFC-0009 section 7). `old` occurs exactly once.
WALKER_MUTANTS = {
    "range lower edge exclusive": (
        "if (v < rmin || v > rmax) return NE_REASON_VALUE_OUT_OF_RANGE;",
        "if (v <= rmin || v > rmax) return NE_REASON_VALUE_OUT_OF_RANGE;",
    ),
    "range upper edge exclusive": (
        "if (v < rmin || v > rmax) return NE_REASON_VALUE_OUT_OF_RANGE;",
        "if (v < rmin || v >= rmax) return NE_REASON_VALUE_OUT_OF_RANGE;",
    ),
    "range not checked": (
        "if (v < rmin || v > rmax) return NE_REASON_VALUE_OUT_OF_RANGE;",
        "",
    ),
    "NaN and infinity not checked": (
        "if (is_nan(v) || !is_finite(v)) return NE_REASON_VALUE_OUT_OF_RANGE;",
        "",
    ),
    "a reading exactly as old as allowed is refused": (
        "if (fact->age_ms > (int64_t)max_age)",
        "if (fact->age_ms >= (int64_t)max_age)",
    ),
    "a reading one ms too old passes": (
        "if (fact->age_ms > (int64_t)max_age)",
        "if (fact->age_ms > (int64_t)max_age + 1)",
    ),
    "age not checked": (
        "if (fact->age_ms > (int64_t)max_age) return NE_REASON_CRITERION_UNAVAILABLE;",
        "",
    ),
    "a reading from the future passes": (
        "if (fact->age_ms < 0) return NE_REASON_CRITERION_UNAVAILABLE;",
        "",
    ),
    "a fresh reading (age 0) is refused": (
        "if (fact->age_ms < 0) return NE_REASON_CRITERION_UNAVAILABLE;",
        "if (fact->age_ms <= 0) return NE_REASON_CRITERION_UNAVAILABLE;",
    ),
    "an absent reading is judged": (
        "if (fact == NULL || !fact->present) return NE_REASON_CRITERION_UNAVAILABLE;\n\n        /* (b)",
        "if (fact == NULL) return NE_REASON_CRITERION_UNAVAILABLE;\n\n        /* (b)",
    ),
    "closed lower bound exclusive": ("if (v < lo) return", "if (v <= lo) return"),
    "open lower bound inclusive": ("if (v <= lo) return", "if (v < lo) return"),
    "closed upper bound exclusive": ("if (v > hi) return", "if (v >= hi) return"),
    "open upper bound inclusive": ("if (v >= hi) return", "if (v > hi) return"),
    "fail open excuses a lost numeric sensor": (
        "if (node_at(t, i)[N_KIND] == KIND_NUMERIC) {",
        "if (0) {",
    ),
}


def _numeric_inputs(root, tmp_path) -> list[str]:
    """Tree and case files of every gate with a numeric criterion, decided by the host engine."""
    rng = random.Random(20261002)
    argv: list[str] = []
    for name, tree in trees(root).items():
        if not any(node["kind"] == "numeric" for node in tree["nodes"]):
            continue
        gate = _gate_for(root, name)
        rows = []
        for facts, args, confirmed in cases(tree, rng, random_rows=300):
            result = asyncio.run(engine_decision(gate, facts, args, confirmed))
            rows.append((facts, args, confirmed, expected_from_engine(tree, result)))
        for facts, args, confirmed, degraded, source, clock in degraded_cases(tree, rng, 300):
            result = asyncio.run(engine_decision(gate, facts, args, confirmed, source, clock))
            rows.append((facts, args, confirmed, expected_from_engine(tree, result), degraded))
        stem = re.sub(r"[^a-z0-9_.-]", "_", name.lower())
        (tmp_path / f"{stem}.netree").write_bytes(encode(tree))
        write_cases(tmp_path / f"{stem}.nevc", tree, rows)
        argv += [str(tmp_path / f"{stem}.netree"), str(tmp_path / f"{stem}.nevc")]
    assert len(argv) >= 8, "the numeric fixtures and the synthetic gates are all in"
    return argv


def _compile_runner(component: Path, walker_c: Path, out: Path) -> None:
    command = [
        cc(),
        "-std=c99",
        "-O1",
        "-I",
        str(component / "include"),
        str(walker_c),
        str(component / "test" / "test_walker_host.c"),
        "-o",
        str(out),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_every_numeric_walker_mutant_is_caught(root, component, tmp_path):
    source = (component / "src" / "ne_walker.c").read_text("utf-8")
    inputs = _numeric_inputs(root, tmp_path)
    _compile_runner(component, component / "src" / "ne_walker.c", tmp_path / "original")
    clean = subprocess.run([str(tmp_path / "original"), *inputs], capture_output=True, text=True)
    assert clean.returncode == 0, "the unmutated walker must pass: " + clean.stdout[-2000:]
    survivors = []
    for label, (old, new) in WALKER_MUTANTS.items():
        assert source.count(old) == 1, f"{label}: `{old}` must occur exactly once"
        mutant = tmp_path / "mutant.c"
        mutant.write_text(source.replace(old, new), "utf-8")
        binary = tmp_path / "mutant"
        _compile_runner(component, mutant, binary)
        run = subprocess.run([str(binary), *inputs], capture_output=True, text=True)
        if run.returncode == 0:
            survivors.append(label)
    assert survivors == [], f"these walker bugs pass the conformance run: {survivors}"


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


def test_the_layout_header_is_what_rfc_0009_freezes():
    assert LAYOUT_VERSION == 2
    assert HEADER_SIZE == 80
    assert NUMERIC_SIZE == 48

    gate = resolve_gate_document(
        {
            "schema": "neuroedge.gate/v1",
            "name": "freeze-check",
            "version": "2.1.0",
            "evaluate": {
                "temp": {
                    "type": "numeric",
                    "unit": "celsius",
                    "range": {"min": -40.0, "max": 125.0},
                    "max_age_ms": 250,
                    "instructions": "Temperature",
                },
            },
            "allow_when": {"temp": {"gte": 15.0, "lt": 35.0}},
            "on_block": {
                "action": "escalate",
                "to": "supervisor",
                "message": "temp out of range",
            },
            "budget": {"p95_latency_ms": 100, "fail": "closed"},
        }
    )
    tree = compile_tree(gate)
    blob = encode(tree)
    assert encode(tree) == blob

    magic, ver, hdr_sz = struct.unpack_from("<4sHH", blob, 0)
    assert (magic, ver, hdr_sz) == (b"NETR", 2, 80)
    assert blob[8:40] == bytes.fromhex(tree["gate_digest"].removeprefix("sha256:"))

    (
        node_count,
        arg_count,
        enum_count,
        action,
        fail_open,
        p95,
        confirm_mask,
        str_sz,
        crc,
        num_count,
        name_off,
        version_off,
        to_off,
        msg_off,
        fallback_off,
        reserved,
    ) = struct.unpack_from("<HHHBBIIIIHHHHHHI", blob, 40)

    assert node_count == 1
    assert arg_count == 0
    assert enum_count == 0
    assert action == 1  # escalate
    assert fail_open == 0
    assert p95 == 100
    assert confirm_mask == 0
    assert num_count == 1
    assert reserved == 0

    str_base = 80 + 24 * node_count + 48 * num_count

    def read_str(off):
        assert off != 0xFFFF
        end = blob.index(b"\x00", str_base + off)
        return blob[str_base + off : end].decode("utf-8")

    assert read_str(name_off) == "freeze-check"
    assert read_str(version_off) == "2.1.0"
    assert read_str(to_off) == "supervisor"
    assert read_str(msg_off) == "temp out of range"
    assert fallback_off == 0xFFFF

    (
        n_kind,
        n_dom_sz,
        n_name_off,
        n_admitted,
        n_floor,
        n_dom_off,
        n_rsv16,
        n_rsv32,
    ) = struct.unpack_from("<BBHIdHHI", blob, 80)
    assert n_kind == 3
    assert n_dom_sz == 0
    assert read_str(n_name_off) == "temp"
    assert n_admitted == 0
    assert n_floor == 0.0
    assert n_dom_off == 0
    assert n_rsv16 == 0
    assert n_rsv32 == 0

    (
        lo,
        hi,
        rmin,
        rmax,
        max_age,
        unit_off,
        flags,
        rsv_u8,
        rsv_u64,
    ) = struct.unpack_from("<ddddIHBBQ", blob, 104)
    assert lo == 15.0
    assert hi == 35.0
    assert rmin == -40.0
    assert rmax == 125.0
    assert max_age == 250
    assert read_str(unit_off) == "celsius"
    assert flags == (1 | 2 | 4)  # lower has+closed, upper has+open
    assert rsv_u8 == 0
    assert rsv_u64 == 0


def test_numeric_limit_at_32(runner, tmp_path):
    criteria = {
        f"n{i}": {
            "type": "numeric",
            "unit": "volt",
            "range": {"min": 0.0, "max": 10.0},
            "max_age_ms": 100,
            "instructions": f"sensor {i}",
        }
        for i in range(MAX_NUMERIC)
    }
    allow = {f"n{i}": {"gte": 1.0, "lte": 9.0} for i in range(MAX_NUMERIC)}
    gate_32 = resolve_gate_document(
        {
            "schema": "neuroedge.gate/v1",
            "name": "numeric-32",
            "version": "1.0.0",
            "evaluate": criteria,
            "allow_when": allow,
            "on_block": {"action": "deny"},
            "budget": {"p95_latency_ms": 100},
        }
    )
    tree_32 = compile_tree(gate_32)
    blob_32 = encode(tree_32)
    numeric_count = struct.unpack_from("<H", blob_32, 64)[0]
    assert numeric_count == 32
    assert numeric_count * NUMERIC_SIZE == 1536

    tree_path = tmp_path / "numeric_32.netree"
    tree_path.write_bytes(blob_32)
    nevc_path = tmp_path / "numeric_32.nevc"
    write_cases(nevc_path, tree_32, [])
    res = subprocess.run(
        [str(runner), str(tree_path), str(nevc_path)], capture_output=True, text=True
    )
    assert res.returncode == 0, res.stderr
    assert "ALL OK" in res.stdout

    criteria_33 = dict(criteria)
    criteria_33["n32"] = {
        "type": "numeric",
        "unit": "volt",
        "range": {"min": 0.0, "max": 10.0},
        "max_age_ms": 100,
        "instructions": "sensor 32",
    }
    allow_33 = dict(allow)
    allow_33["n32"] = {"gte": 1.0, "lte": 9.0}
    gate_33 = resolve_gate_document(
        {
            "schema": "neuroedge.gate/v1",
            "name": "numeric-33",
            "version": "1.0.0",
            "evaluate": criteria_33,
            "allow_when": allow_33,
            "on_block": {"action": "deny"},
            "budget": {"p95_latency_ms": 100},
        }
    )
    with pytest.raises(GateSchemaError):
        encode(compile_tree(gate_33))


def test_encoder_refuses_numeric_in_confirms():
    gate = resolve_gate_document(
        {
            "schema": "neuroedge.gate/v1",
            "name": "numeric-confirm",
            "version": "1.0.0",
            "evaluate": {
                "temp": {
                    "type": "numeric",
                    "unit": "celsius",
                    "range": {"min": -20.0, "max": 120.0},
                    "max_age_ms": 500,
                    "instructions": "Temperature",
                },
            },
            "allow_when": {"temp": {"gte": 10.0}},
            "on_block": {"action": "deny"},
            "budget": {"p95_latency_ms": 150},
        }
    )
    tree = compile_tree(gate)
    tree["on_block"]["confirms"] = ["temp"]
    with pytest.raises(GateSchemaError, match="confirm_mask"):
        encode(tree)


def _recompute_crc(b: bytearray) -> bytes:
    struct.pack_into("<I", b, 60, 0)
    crc = zlib.crc32(b) & 0xFFFFFFFF
    struct.pack_into("<I", b, 60, crc)
    return bytes(b)


def _assert_refusal(runner, tmp_path, blob: bytes, status: int, label: str):
    tp = tmp_path / f"{label}.netree"
    tp.write_bytes(blob)
    vp = tmp_path / f"{label}.nevc"
    vp.write_bytes(struct.pack("<4sIIII", b"NEVC", 3, 0, 0, 0))
    res = subprocess.run([str(runner), str(tp), str(vp)], capture_output=True, text=True)
    assert res.returncode != 0, f"expected failure ({status}) for {label}, but passed"
    assert f"load failed ({status})" in res.stderr, (
        f"{label}: expected load failed ({status}), got: {res.stderr}"
    )


def test_the_c_loader_refuses_structural_and_semantic_violations(runner, tmp_path):
    base_blob = encode(compile_tree(SYNTHETIC_MIXED))

    # 1. layout_version != 2 -> NE_ERR_VERSION (4)
    b = bytearray(base_blob)
    struct.pack_into("<H", b, 4, 1)
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 4, "v1_layout")
    b = bytearray(base_blob)
    struct.pack_into("<H", b, 4, 3)
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 4, "v3_layout")

    # 2. header_size != 80 -> NE_ERR_VERSION (4)
    b = bytearray(base_blob)
    struct.pack_into("<H", b, 6, 64)
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 4, "hdr_size_64")

    # 3. size not sum -> NE_ERR_SIZE (2)
    b = bytearray(base_blob) + b"\x00"
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 2, "size_extra_byte")

    # 4. numeric_count > 32 -> NE_ERR_LIMITS (6)
    b = bytearray(base_blob)
    struct.pack_into("<H", b, 64, 33)
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 6, "num_count_33")

    # 5. numeric_count != number of kind-3 nodes -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    b[152] = 0  # node 3 kind set to 0 (bool)
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "num_node_count_mismatch")

    # 6. kind-3 node domain_size != 0 -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    b[153] = 1
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "num_domain_size_nonzero")

    # 7. kind-3 node admitted_mask != 0 -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    struct.pack_into("<I", b, 156, 1)
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "num_admitted_mask_nonzero")

    # 8. kind-3 node confidence_floor != 0.0 -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    struct.pack_into("<d", b, 160, 0.5)
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "num_floor_nonzero")

    # 9. kind-3 node domain_off >= numeric_count -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    struct.pack_into("<H", b, 168, 1)
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "num_domain_off_oob")

    # 10. kind-3 node domain_off duplicated -> NE_ERR_STRUCTURE (7)
    gate_2num = resolve_gate_document(
        {
            "schema": "neuroedge.gate/v1",
            "name": "two-num",
            "version": "1.0.0",
            "evaluate": {
                "t1": {
                    "type": "numeric",
                    "unit": "celsius",
                    "range": {"min": 0.0, "max": 100.0},
                    "max_age_ms": 100,
                    "instructions": "t1",
                },
                "t2": {
                    "type": "numeric",
                    "unit": "celsius",
                    "range": {"min": 0.0, "max": 100.0},
                    "max_age_ms": 100,
                    "instructions": "t2",
                },
            },
            "allow_when": {"t1": {"gte": 10.0}, "t2": {"gte": 10.0}},
            "on_block": {"action": "deny"},
            "budget": {"p95_latency_ms": 100},
        }
    )
    b2 = bytearray(encode(compile_tree(gate_2num)))
    # node 1 domain_off is at 80 + 24 + 16 = 120
    struct.pack_into("<H", b2, 120, 0)
    _assert_refusal(runner, tmp_path, _recompute_crc(b2), 7, "num_domain_off_dup")

    # 11. kind > 3 -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    b[152] = 4
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "kind_4")

    # 12. numeric record reserved field != 0 -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    b[215] = 1  # reserved u8
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "num_reserved_u8")
    b = bytearray(base_blob)
    struct.pack_into("<Q", b, 216, 1)  # reserved u64
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "num_reserved_u64")

    # 13. flags > 15 -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    b[214] = 16
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "flags_16")

    # 14. closed flag without has-bound flag -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    b[214] = 0b0010  # lower closed without has-lower
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "lower_closed_no_lower")
    b = bytearray(base_blob)
    b[214] = 0b1000  # upper closed without has-upper
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "upper_closed_no_upper")

    # 15. lo or hi not finite when present -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    struct.pack_into("<d", b, 176, float("nan"))
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "lo_nan")
    b = bytearray(base_blob)
    struct.pack_into("<d", b, 184, float("inf"))
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "hi_inf")

    # 16. range_min/range_max not finite or range_min >= range_max -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    struct.pack_into("<d", b, 192, float("nan"))
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "rmin_nan")
    b = bytearray(base_blob)
    struct.pack_into("<d", b, 200, float("-inf"))
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "rmax_inf")
    b = bytearray(base_blob)
    struct.pack_into("<d", b, 192, 120.0)  # rmin=120 >= rmax=120
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "rmin_gte_rmax")

    # 17. max_age_ms == 0 -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    struct.pack_into("<I", b, 208, 0)
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "max_age_zero")

    # 18. unit_off outside table -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    struct.pack_into("<H", b, 212, 0x7FFF)
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "unit_off_oob")

    # 19. bound outside [range_min, range_max] -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    struct.pack_into("<d", b, 176, -25.0)  # lo < range_min (-20.0)
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "lo_lt_rmin")
    b = bytearray(base_blob)
    struct.pack_into("<d", b, 184, 125.0)  # hi > range_max (120.0)
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "hi_gt_rmax")

    # 20. lower > upper -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    struct.pack_into("<d", b, 176, 50.0)
    struct.pack_into("<d", b, 184, 40.0)
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "lo_gt_hi")

    # 21. lower == upper with open edge -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    struct.pack_into("<d", b, 176, 50.0)
    struct.pack_into("<d", b, 184, 50.0)
    b[214] = 0b0101  # has-lower, open; has-upper, open
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "lo_eq_hi_open")

    # 22. label offset neither 0xFFFF nor valid string -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    struct.pack_into("<H", b, 66, 0x7FFF)
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "gate_name_off_oob")

    # 23. reserved u32 at offset 76 not 0 -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    struct.pack_into("<I", b, 76, 1)
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "hdr_reserved_nonzero")

    # 24. confirm_mask bit on numeric node -> NE_ERR_STRUCTURE (7)
    b = bytearray(base_blob)
    struct.pack_into("<I", b, 52, 1 << 3)
    _assert_refusal(runner, tmp_path, _recompute_crc(b), 7, "confirm_mask_on_numeric")


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


def _source_gate(name, sources, *, channel=None):
    evaluate = {
        "call_source": {"type": "choice", "options": sources, "instructions": "Who asked"},
    }
    allow = {"call_source": {"in": sources[:1]}}
    if channel is not None:
        evaluate["call_channel"] = {
            "type": "choice",
            "options": channel,
            "instructions": "The family of who asked",
        }
        allow["call_channel"] = {"in": channel[:1]}
    return resolve_gate_document(
        {
            "schema": "neuroedge.gate/v1",
            "name": name,
            "version": "1.0.0",
            "evaluate": evaluate,
            "allow_when": allow,
            "on_block": {"action": "deny"},
            "budget": {"p95_latency_ms": 100},
        }
    )


def test_a_gate_with_a_bridge_option_encodes_with_the_unchanged_layout():
    """RFC-0017 §2: a namespaced source is a string in the gate's own domain; no byte of the layout moves."""
    listed = ["local_grammar", "bridge:muse", "mcp:hub", "test"]
    tree = compile_tree(_source_gate("bridge-source", listed))
    blob = encode(tree)
    assert LAYOUT_VERSION == 2
    magic, version = struct.unpack_from("<4sH", blob, 0)
    assert (magic, version) == (b"NETR", 2)
    assert b"bridge:muse\0" in blob and b"mcp:hub\0" in blob
    (node,) = [n for n in tree["nodes"] if n["criterion"] == "call_source"]
    # the index the device compares is the position in the gate's own sorted options
    assert domain_index(node, "bridge:muse") == sorted(listed).index("bridge:muse")
    assert (
        domain_index(node, "bridge:other") is None
    )  # outside the domain: unavailable, not a verdict
    # a gate that never names it carries no such string: the table is the gate's, not global
    other = encode(compile_tree(_source_gate("plain-source", ["local_grammar", "test"])))
    assert b"bridge:muse" not in other


def test_a_source_domain_over_32_values_is_refused_at_build():
    """Why `call_channel` exists: "every bridge" cannot be listed, a domain stops at 32 (`u32` mask)."""
    bridges = [f"bridge:b{i:02d}" for i in range(MAX_DOMAIN)]
    with pytest.raises(GateSchemaError, match="limit of 32"):
        encode(compile_tree(_source_gate("too-many-sources", ["local_grammar", *bridges])))
    # 32 fit; and the family is one value however many bridges are loaded
    encode(compile_tree(_source_gate("exactly-32-sources", bridges)))
    encode(
        compile_tree(
            _source_gate(
                "by-family",
                ["local_grammar", "test"],
                channel=["local_grammar", "system_one", "system_two", "mcp", "bridge", "test"],
            )
        )
    )


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
