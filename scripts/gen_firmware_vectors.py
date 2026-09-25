#!/usr/bin/env python3
"""Sinh targets/esp32s3/main/vectors/ từ fixtures/traces/*.json (TSK-S4-09 phần 2).

Lúc khởi động, firmware replay ba vết ghi chuẩn mực (`main/trace_vectors.c`),
mỗi vết ghi một phiên `NE1`. Mỗi bước mang đúng đầu vào mà `neuroedge replay`
cấp lại cho engine host (`TracePlayer.recorded_steps()`): dữ kiện đã ghi, lần
thu thập suy giảm đã ghi (`gate_unreachable`, `budget_exceeded`), xác nhận của
người. Phán quyết, token và việc có phát lệnh chân hay không là **của thiết bị**
(walker C `ne_decide`, sổ token C). `neuroedge verify --targets esp32s3 --port
<uart>` so các phiên đó với chính các vết ghi chuẩn mực làm golden.

Đi kèm vì NETR v1 không mang: nhãn gate và chữ `on_block` (`to`, `message`,
`fallback_action`), sinh từ cùng gate đã phân giải. Và **bảng hành động**: lệnh
chân mỗi @action phát khi được phép, ghi bằng cách chạy action một lần trên
`SimHAL` sau một engine luôn-ALLOW — chỉ trong script này. Thiết bị quyết định
*có* phát và *chân nào* (token cấp cho chân của action); operation/duration là
của bảng, dựng trên host. Cách action thật sự chạy trên MCU: TSK-S4-01.

Những gì firmware chưa replay được thì script từ chối, không đoán: tham số có
giới hạn (RFC-0005), `degrade` + `fallback_action`, số đọc cảm biến, độ tin cậy
không phải số trong [0, 1] ghi được.

    python/.venv/bin/python scripts/gen_firmware_vectors.py           # ghi tệp
    python/.venv/bin/python scripts/gen_firmware_vectors.py --check   # thoát 1 nếu lệch

`python/tests/test_trace_vectors.py` chạy `--check`: đổi vết ghi chuẩn mực, gate
hay action mà quên sinh lại là fail — và `verify` trên thiết bị nói "firmware cũ".
"""

from __future__ import annotations

import argparse
import asyncio
import math
import re
import sys
import tempfile
from pathlib import Path

from neuroedge.actions import Conversation
from neuroedge.actions.spec import REGISTRY
from neuroedge.engine import ActionContractEngine, EventLog
from neuroedge.engine.binary_tree import c_string, domain_index
from neuroedge.engine.canonical import digest
from neuroedge.engine.compiler import build, load_actions, load_agent_manifest, resolve_gates
from neuroedge.engine.decision_tree import compile_tree
from neuroedge.engine.gate import GateResult
from neuroedge.engine.verdict import GateVerdict
from neuroedge.errors import NeuroEdgeError
from neuroedge.hal.board import load_board_by_id
from neuroedge.hal.sim import SimHAL
from neuroedge.paths import repo_root
from neuroedge.testing.player import recorded_steps
from neuroedge.trace import load_trace

ROOT = repo_root()
TRACES = ROOT / "fixtures" / "traces"
AGENTS = ROOT / "fixtures" / "agents"
TARGET = ROOT / "targets" / "esp32s3" / "main" / "vectors"
BOARD = "esp32s3-box-3"
DEGRADED = {None: 0, "gate_unreachable": 1, "budget_exceeded": 2}


def _refuse(where: str, why: str) -> NeuroEdgeError:
    return NeuroEdgeError(
        where=where,
        why=why,
        how="firmware replay does not cover this yet (TSK-S4-04): keep it out of the canonical "
        "traces, or extend main/trace_vectors.c and this script together",
    )


def _ident(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", text.lower())


class _AllowAll(ActionContractEngine):
    """Allows every gate: only to learn what an action does once allowed."""

    async def evaluate(self, key, context=None, *, state=None, arguments=None, confirmed=False):
        tree = self.tree(key)
        return GateResult(gate=tree["gate"], verdict=GateVerdict.ALLOW, gate_digest=tree["gate_digest"])


async def _pin_commands(gates, action: str, arguments: dict) -> list[tuple[str, str, int]]:
    log = EventLog()
    hal = SimHAL(load_board_by_id("sim-default"), events=log)
    await Conversation(engine=_AllowAll(gates, events=log), hal=hal).do(action, **arguments)
    return [
        (data["pin"], data["operation"], int(data.get("duration_ms", 0)))
        for data in log.of_type("actuator_command")
    ]


def _fact(node, fact, where: str) -> tuple[str, str]:
    """(ne_fact initializer, source) — the walker's view of one recorded fact."""
    if fact is None or fact.value is None:
        return "{0u, 0u, 0u, 0u, 0.0}", "NULL"
    index = domain_index(node, fact.value)
    confidence = fact.confidence
    has = confidence is not None
    if has and (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or math.isnan(confidence)
        or math.isinf(confidence)
    ):
        raise _refuse(where, f"confidence {confidence!r} of {node['criterion']} is not a number")
    value = repr(float(confidence)) if has else "0.0"
    init = f"{{1u, {0 if index is None else 1}u, {index or 0}u, {1 if has else 0}u, {value}}}"
    return init, c_string(fact.source or "trace")


def _manifest_for(trace, path: Path):
    name = str(trace["metadata"].get("agent_version", "")).partition("@")[0]
    agent = AGENTS / name / "agent.toml"
    if not agent.is_file():
        raise _refuse(str(path), f"no sample agent {name!r} in fixtures/agents/ for this trace")
    return load_agent_manifest(agent)


def render() -> dict[str, str]:
    """Every file under main/vectors/, as this script produces it."""
    files: dict[str, str] = {}
    gate_rows: dict[str, tuple[int, str]] = {}  # label -> (index, initializer)
    body: list[str] = []
    vectors: list[str] = []
    for path in sorted(TRACES.glob("*.json")):
        trace = load_trace(path)
        manifest = _manifest_for(trace, path)
        if any(e["type"] == "sensor_read" for e in trace["events"]):
            raise _refuse(str(path), "the trace replays sensor readings")
        actions = {spec.name: spec for spec in load_actions(manifest)}
        gates, problems = resolve_gates(manifest, None)
        if problems:
            raise problems[0]
        pins = list(manifest.requires.get("digital.out", {}).get("pins", []))
        with tempfile.TemporaryDirectory() as out:
            build(manifest.source, target="esp32s3", board_id=BOARD, out_dir=out)
            headers = {key: (Path(out) / "gates" / f"{key}.netree.h").read_text() for key in gates}
        stem = _ident(path.stem)
        steps: list[str] = []
        for step in recorded_steps(trace):
            where = f"{path.name} gate evaluation #{step.index + 1} ({step.gate})"
            key = next((k for k, g in gates.items() if g.name == step.gate_name), None)
            if key is None:
                raise _refuse(where, f"{manifest.label} has no gate {step.gate_name!r}")
            tree = compile_tree(gates[key])
            if tree["gate"] != step.gate:
                raise _refuse(where, f"the agent's gate is {tree['gate']}, the trace says {step.gate}")
            if tree.get("arguments"):
                raise _refuse(where, "the gate limits arguments (RFC-0005)")
            if gates[key].on_block.get("action") == "degrade":
                raise _refuse(where, "on_block degrade runs a fallback action through its own gate")
            name = step.action or next(
                (spec.name for spec in actions.values() if spec.gate == key), None
            )
            spec = actions.get(name) or REGISTRY.get(name)
            if spec is None:
                raise _refuse(where, f"no @action behind {key}")
            label = tree["gate"]
            if label not in gate_rows:
                text = [
                    c_string(gates[key].on_block[k]) if gates[key].on_block.get(k) else "NULL"
                    for k in ("to", "message", "fallback_action")
                ]
                symbol = f"ne_tree_{key}"
                files[f"{key}.netree.h"] = headers[key]
                init = (
                    f"    {{{c_string(label)}, {symbol}, (uint32_t)sizeof {symbol}, "
                    f"{{{', '.join(text)}}}}}, /* {tree['gate_digest']} */"
                )
                gate_rows[label] = (len(gate_rows), init)
            prefix = f"ne_v_{stem}_{step.index}"
            facts = [
                _fact(node, step.facts.get(node["criterion"]), where) for node in tree["nodes"]
            ]
            body.append(f"/* {path.name} #{step.index + 1}: {label} */")
            body.append(
                f"static const ne_fact {prefix}_facts[{len(facts)}] = "
                f"{{{', '.join(f for f, _ in facts)}}};"
            )
            body.append(
                f"static const char *const {prefix}_sources[{len(facts)}] = "
                f"{{{', '.join(s for _, s in facts)}}};"
            )
            commands = asyncio.run(_pin_commands(gates, spec.name, dict(step.arguments)))
            for pin, _, _ in commands:
                if pin not in pins:
                    raise _refuse(where, f"{spec.name} drives {pin!r}, not in digital.out pins")
            if commands:
                rows = ", ".join(
                    f"{{{c_string(pin)}, {pins.index(pin)}u, {c_string(op)}, {ms}u}}"
                    for pin, op, ms in commands
                )
                body.append(
                    f"static const ne_vector_command {prefix}_commands[{len(commands)}] = {{{rows}}};"
                )
            mask = sum(1 << pins.index(pin) for pin in spec.pins if pin in pins)
            steps.append(
                f"    {{{gate_rows[label][0]}u, {DEGRADED[step.degraded]}u, "
                f"{1 if step.result.get('confirmed') else 0}u, {prefix}_facts, {prefix}_sources, "
                f"0x{mask:x}u, {f'{prefix}_commands' if commands else 'NULL'}, {len(commands)}u}},"
            )
        body.append(f"static const ne_vector_step ne_v_{stem}_steps[{len(steps)}] = {{")
        body += steps
        body.append("};")
        vectors.append(
            f"    {{{c_string(path.name)}, {c_string(digest(trace))}, "
            f"{c_string(manifest.label)}, ne_v_{stem}_steps, {len(steps)}u}},"
        )
    lines = [
        "/* Generated by scripts/gen_firmware_vectors.py from fixtures/traces/ — do not edit. */",
        "/* The canonical traces as the device replays them (TSK-S4-09): the recorded inputs; */",
        "/* the verdicts, tokens and whether a pin is driven are the device's own. */",
        "#ifndef NE_CANONICAL_VECTORS_H",
        "#define NE_CANONICAL_VECTORS_H",
        '#include "trace_vectors.h"',
        *(f'#include "vectors/{name}"' for name in sorted(files)),
        "",
        *body,
        "",
        f"#define NE_VECTOR_GATES {len(gate_rows)}u",
        "static const ne_vector_gate ne_vector_gates[NE_VECTOR_GATES] = {",
        *(init for _, init in sorted(gate_rows.values())),
        "};",
        f"#define NE_VECTORS {len(vectors)}u",
        "static const ne_vector ne_vectors[NE_VECTORS] = {",
        *vectors,
        "};",
        "#endif /* NE_CANONICAL_VECTORS_H */",
        "",
    ]
    files["canonical_vectors.h"] = "\n".join(lines)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="không ghi; thoát 1 nếu lệch")
    args = parser.parse_args()
    try:
        files = render()
    except NeuroEdgeError as error:
        print(error.render(), file=sys.stderr)
        return 1
    stale = [
        name
        for name, text in files.items()
        if not (TARGET / name).exists() or (TARGET / name).read_text(encoding="utf-8") != text
    ]
    extra = (
        sorted(p.name for p in TARGET.glob("*.h") if p.name not in files) if TARGET.exists() else []
    )
    if args.check:
        for name in stale + extra:
            print(f"lệch: targets/esp32s3/main/vectors/{name}")
        return 1 if stale or extra else 0
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (TARGET / name).write_text(text, encoding="utf-8")
    for name in extra:
        (TARGET / name).unlink()
    print(f"đã ghi {len(files)} tệp vào targets/esp32s3/main/vectors/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
