"""
TSK-S4-09 — the device's trace lines are the host's events.

`targets/esp32s3/components/ne_trace/` formats each trace event as one `NE1 `
line on the UART. It is compiled on this host with AddressSanitizer and
UndefinedBehaviorSanitizer and checked for:

* every line being one `trace.v1` event the host reader accepts, within
  `NE_TRACE_LINE_MAX`, JSON-escaped, and refused whole — never cut — when the
  buffer is too small (the C runner tries every size);
* the verdict lines having exactly the keys and values the host engine writes
  (`GateResult.to_event_data()`), with the host's reason and `on_block` names;
* the boot self-test, traced: its session read back by `neuroedge.testing.uart`,
  validated, and replayed on `sim` — every gate event the device wrote is the
  event the host engine writes for the same facts;
* the static budget (no `.data`/`.bss`, stack <= 512 B), and a mutation check.

A missing C compiler is a failure, not a skip.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
from pathlib import Path

import pytest

from neuroedge.engine import ActionContractEngine
from neuroedge.engine.binary_tree import ACTIONS
from neuroedge.engine.gate_resolver import resolve_gate_file
from neuroedge.engine.verdict import Fact, Reason, Unavailable
from neuroedge.errors import TraceValidationError
from neuroedge.testing.player import TracePlayer
from neuroedge.testing.uart import LINE_MAX, parse_line, read_sessions, sessions_from_lines
from neuroedge.trace import validate_trace

from .test_c_walker import STACK_LIMIT, STRICT, cc

SAN = ["-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-fno-omit-frame-pointer"]

GATE_EVENTS = ("gate_evaluation_begin", "gate_facts", "gate_evaluation_result")

SELFTEST_DRIVER = r"""
#include <stdio.h>
#include "gate_selftest.h"
#include "gates/home_voice_indices.h"
static unsigned state = 1u;
static uint32_t clock_ms = 4294967000u;
static void fill(void *buf, size_t len) {
    unsigned char *p = buf;
    for (size_t i = 0; i < len; i++) { state = state * 1103515245u + 12345u; p[i] = (unsigned char)(state >> 16); }
}
static void emit(void *ctx, const char *line) { (void)ctx; printf("%s\n", line); }
static uint32_t now(void *ctx) { (void)ctx; return clock_ms += 7u; }
static char buf[NE_TRACE_LINE_MAX + 1];
int main(void) {
    char line[96];
    ne_trace_sink sink = {emit, now, NULL, buf, sizeof buf, 0, 0, 0};
    const ne_device_info info = {"esp32s3-box-3", NE_AGENT_VERSION, "host", 0x2468u, NULL, NULL};
    printf("I (31) boot: ESP-IDF v5.4 2nd stage bootloader\n");
    ne_trace_open(&sink, &info);
    int rc = neuroedge_gate_selftest(fill, 0x2468u, clock_ms, line, sizeof line, &sink);
    ne_trace_close(&sink);
    puts(line);
    puts("NE_TRACE DONE sessions=1");
    return rc;
}
"""


@pytest.fixture(scope="module")
def dirs(root) -> dict[str, Path]:
    targets = root / "targets" / "esp32s3"
    return {
        "gate": targets / "components" / "ne_gate",
        "trace": targets / "components" / "ne_trace",
        "main": targets / "main",
    }


def compile_exe(dirs, out: Path, sources: list[Path], strict=False, sanitize=True) -> Path:
    command = [
        cc(),
        *(STRICT if strict else STRICT[:-1]),
        "-O1",
        "-g",
        *(SAN if sanitize else []),
        "-I",
        str(dirs["gate"] / "include"),
        "-I",
        str(dirs["trace"] / "include"),
        "-I",
        str(dirs["main"]),
        *(str(source) for source in sources),
        "-o",
        str(out),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return out


def run_harness(dirs, out: Path, trace_source: Path | None = None, sanitize=True):
    exe = compile_exe(
        dirs,
        out,
        [
            trace_source or dirs["trace"] / "src" / "ne_trace.c",
            dirs["gate"] / "src" / "ne_walker.c",
            dirs["gate"] / "src" / "ne_token.c",
            dirs["trace"] / "test" / "test_trace_host.c",
        ],
        sanitize=sanitize,
    )
    return subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)


@pytest.fixture(scope="module")
def harness(dirs, tmp_path_factory):
    result = run_harness(dirs, tmp_path_factory.mktemp("trace") / "test_trace_host")
    cases, reasons, actions, sink = {}, {}, {}, []
    for row in result.stdout.splitlines():
        parts = row.split("\t")
        if parts[0] == "reason":
            reasons[int(parts[1])] = parts[2]
        elif parts[0] == "on_block":
            actions[int(parts[1])] = parts[2]
        elif parts[0] == "sink":
            sink.append(parts[2])
        elif len(parts) == 3:
            cases[parts[0]] = (int(parts[1]), parts[2])
    return {"result": result, "cases": cases, "reasons": reasons, "actions": actions, "sink": sink}


def data(harness, case: str) -> dict:
    length, line = harness["cases"][case]
    assert length == len(line.encode("utf-8")) > 0, case
    event = parse_line(line, case)
    assert event is not None, case
    return event["data"]


class _Offline:
    async def adjudicate(self, criterion, definition, state, deadline_ms=None):
        return Unavailable("offline", "test")


def host_result(
    root, gate: str, facts: dict[str, Fact], confirmed: bool = False, source=None
) -> dict:
    """What the host engine writes as `gate_evaluation_result` for these facts."""
    path = root / "fixtures" / "agents" / "home-voice" / "gates" / f"{gate}@1.0.0.yaml"
    engine = ActionContractEngine({gate: resolve_gate_file(path)}, facts_source=source)
    asyncio.run(engine.evaluate(gate, facts, confirmed=confirmed))
    return engine.events.of_type("gate_evaluation_result")[-1]


# --- the formatter ---------------------------------------------------------------------------


def test_every_line_fits_whole_or_is_refused_whole(harness):
    result = harness["result"]
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
    assert result.stdout.rstrip().endswith("ALL OK")
    assert len(harness["cases"]) == 18


def test_every_line_is_one_trace_v1_event_within_the_line_limit(harness):
    lines = [line for length, line in harness["cases"].values() if length > 0]
    assert len(lines) == 15
    for line in lines:
        assert len(line.encode("utf-8")) <= LINE_MAX
        event = parse_line(line, "harness")
        assert set(event) == {"offset_ms", "type", "data"}
    assert harness["cases"]["too_long"] == (-1, "")
    assert harness["cases"]["rejected_authorized"] == (-1, "")
    assert harness["cases"]["gate_facts_none"] == (0, "")  # as the host: no facts, no event


def test_device_info_says_where_the_evidence_came_from(harness):
    assert data(harness, "device_info") == {
        "board_id": "esp32s3-box-3",
        "agent_version": "home-voice@0.1.0",
        "device_id": "qemu",
        "boot_id": "deadbeef",
    }
    replay = data(harness, "device_info_replay")
    assert replay["replay_of"] == "happy-path.json" and replay["trace_digest"] == "sha256:0123"


def test_strings_are_escaped_as_json(harness):
    assert data(harness, "device_info_escaped")["board_id"] == 'a"b\\c\x01\x1f dé'


def test_facts_are_the_inputs_a_replay_feeds_back(harness):
    assert data(harness, "gate_facts") == {
        "call_source": {"value": "local_grammar", "confidence": None, "source": "context"},
        "room_empty": {"value": True, "confidence": 0.96, "source": "sensor"},
    }
    # Out of the domain, or a NaN confidence: unavailable on the device, and null in
    # the trace so a replay also finds it unavailable (NaN is not JSON).
    assert data(harness, "gate_facts_unreadable") == {
        "call_source": {"value": None, "confidence": None, "source": "context"},
        "room_empty": {"value": None, "confidence": None, "source": "context"},
    }


def test_a_verdict_line_is_what_the_host_engine_writes(root, harness):
    assert data(harness, "result_allow") == host_result(root, "light_on", {"call_source": "mcp"})
    blocked = host_result(root, "light_off", {"call_source": "system_two", "room_empty": False})
    assert data(harness, "result_block_ask") == blocked
    assert blocked["message"] and blocked["action"] == "ask"


def test_a_degraded_verdict_applies_fail_not_on_block(root, harness):
    # room_empty is missing and its source is offline: light_off is `fail: closed`.
    closed = host_result(root, "light_off", {"call_source": "local_grammar"}, source=_Offline())
    assert data(harness, "result_closed") == closed
    assert closed == {
        "verdict": "BLOCK",
        "fail_mode": "closed",
        "reason": "gate_unreachable",
        "blocked_by": "light_off@1.0.0",
        "action": "deny",  # not the gate's `ask`: a degraded verdict skips on_block (Q-17)
    }
    # `fail: open` (no home-voice gate declares it): ALLOW, the reason, no evaluations.
    assert data(harness, "result_open") == {
        "verdict": "ALLOW",
        "fail_mode": "open",
        "reason": "budget_exceeded",
    }


def test_confirmed_criteria_are_sorted_as_the_host_writes_them(harness):
    assert data(harness, "result_confirmed")["confirmed"] == ["call_source", "room_empty"]


def test_an_argument_refusal_records_no_evaluations(harness):
    refused = data(harness, "result_argument")
    assert refused["reason"] == "argument_out_of_range" and refused["evaluations"] == {}


def test_pin_lines_carry_the_host_fields(harness):
    assert data(harness, "actuator_command") == {
        "pin": "door_lock",
        "operation": "pulse",
        "duration_ms": 30000,
    }
    assert data(harness, "actuator_rejected") == {
        "pin": "door_lock",
        "reason": "token_replayed",
        "code": "NE1002",
    }
    assert parse_line(harness["cases"]["trace_end"][1], "end")["offset_ms"] == 2**32 - 1


def test_reason_and_on_block_names_are_the_hosts(harness):
    walker_reasons = [
        Reason.CONDITION_NOT_MET,
        Reason.CRITERION_UNAVAILABLE,
        Reason.CONFIDENCE_UNAVAILABLE,
        Reason.ARGUMENT_OUT_OF_RANGE,
        Reason.GATE_UNREACHABLE,
        Reason.BUDGET_EXCEEDED,
    ]
    assert harness["reasons"] == {
        0: "-",
        **{i + 1: str(reason) for i, reason in enumerate(walker_reasons)},
        7: "-",
    }
    assert harness["actions"] == {**{code: name for name, code in ACTIONS.items()}, 4: "-"}


def test_the_sink_counts_a_line_it_could_not_fit(harness):
    lines = harness["sink"]
    assert len(lines) == 3
    assert parse_line(lines[1], "sink")["offset_ms"] == 5  # across the clock's wrap
    with pytest.raises(TraceValidationError, match="wrote 3 line.*2 arrived"):
        sessions_from_lines(lines, "sink")


def test_the_trace_formatter_uses_no_static_ram_and_a_small_stack(dirs, tmp_path):
    obj = tmp_path / "ne_trace.o"
    command = [
        cc(),
        *STRICT,
        "-O2",
        "-fstack-usage",
        "-I",
        str(dirs["trace"] / "include"),
        "-I",
        str(dirs["gate"] / "include"),
        "-c",
        str(dirs["trace"] / "src" / "ne_trace.c"),
        "-o",
        str(obj),
    ]
    result = subprocess.run(command, capture_output=True, text=True, cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    symbols = subprocess.run(["nm", str(obj)], capture_output=True, text=True, check=True).stdout
    writable = [line for line in symbols.splitlines() if re.search(r"\s[bBdDC]\s", line)]
    assert writable == [], f"the trace formatter must hold no .data/.bss state: {writable}"
    usage = (tmp_path / "ne_trace.su").read_text()
    frames = {m.group(1): int(m.group(2)) for m in re.finditer(r":(\w+)\s+(\d+)\s+\w+", usage)}
    assert "ne_trace_gate_result" in frames and "ne_trace_gate_facts" in frames, usage
    assert max(frames.values()) <= STACK_LIMIT, frames


# --- the traced boot self-test, end to end ----------------------------------------------------


def traced_selftest(dirs, tmp_path: Path, trace_source: Path | None = None) -> Path:
    driver = tmp_path / "driver.c"
    driver.write_text(SELFTEST_DRIVER)
    exe = compile_exe(
        dirs,
        tmp_path / "selftest",
        [
            dirs["gate"] / "src" / "ne_walker.c",
            dirs["gate"] / "src" / "ne_token.c",
            trace_source or dirs["trace"] / "src" / "ne_trace.c",
            dirs["main"] / "gate_selftest.c",
            driver,
        ],
        strict=True,
    )
    result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    log = tmp_path / "uart.log"
    log.write_text(result.stdout)
    return log


def differences_from_the_host(log: Path, tmp_path: Path) -> list[str]:
    """Every way the device's gate events differ from the host engine's, replaying them."""
    try:
        [session] = read_sessions(str(log))
        trace = session.trace()
        validate_trace(trace, str(log))
    except (TraceValidationError, ValueError) as error:
        return [f"unreadable: {error}"]
    path = tmp_path / "device.json"
    path.write_text(json.dumps(trace))
    replayed = asyncio.run(TracePlayer(path, target="sim").replay()).replayed
    device = [(e["type"], e["data"]) for e in trace["events"] if e["type"] in GATE_EVENTS]
    host = [(e["type"], e["data"]) for e in replayed["events"] if e["type"] in GATE_EVENTS]
    out = [
        f"#{i}: device {d} host {h}"
        for i, (d, h) in enumerate(zip(device, host, strict=False))
        if d != h
    ]
    if len(device) != len(host):
        out.append(f"{len(device)} device gate events, {len(host)} on the host")
    return out


def test_a_traced_self_test_is_the_host_engine_again(dirs, tmp_path):
    log = traced_selftest(dirs, tmp_path)
    text = log.read_text()
    assert "NE_SELFTEST PASS walker=6 token=6" in text
    [session] = read_sessions(str(log))
    trace = session.trace()
    assert trace["metadata"]["target"] == "esp32s3"
    assert trace["metadata"]["device_id"] == "host"
    assert trace["metadata"]["agent_version"] == "home-voice@0.1.0"
    assert [e["type"] for e in trace["events"]].count("gate_evaluation_result") == 6
    assert differences_from_the_host(log, tmp_path) == []


MUTANTS = {
    "confirmed criteria dropped": (
        "if (result->confirmed_mask != 0u) {",
        "if (0) {",
    ),
    "a bool written as a string": (
        'w_raw(w, value); /* "true" / "false" as JSON literals */',
        "w_str(w, value);",
    ),
    "on_block action ignored": ("w_str(&w, action);", 'w_str(&w, action ? "deny" : action);'),
    "a dropped line not counted": (
        "    sink->lines++;\n    if (len < 0) {",
        "    if (len < 0) {\n        return;",
    ),
    "evaluations of a missing fact": (
        "if (fact == NULL || !fact->present || !fact->in_domain) return 0;",
        "if (fact == NULL) return 0;",
    ),
}


def test_every_deliberate_formatter_bug_is_caught(dirs, tmp_path):
    source = (dirs["trace"] / "src" / "ne_trace.c").read_text()
    survivors = []
    for label, (old, new) in MUTANTS.items():
        assert source.count(old) == 1, label
        work = tmp_path / re.sub(r"\W+", "_", label)
        work.mkdir()
        mutant = work / "ne_trace.c"
        mutant.write_text(source.replace(old, new))
        harness = run_harness(dirs, work / "harness", trace_source=mutant, sanitize=False)
        caught = harness.returncode != 0 or "ALL OK" not in harness.stdout
        sink = [row.split("\t")[2] for row in harness.stdout.splitlines() if row.startswith("sink")]
        try:
            sessions_from_lines(sink, "sink")
            caught = True  # the dropped line must be reported
        except TraceValidationError:
            pass
        if not caught:
            caught = bool(differences_from_the_host(traced_selftest(dirs, work, mutant), work))
        if not caught:
            survivors.append(label)
    assert survivors == [], f"these bugs pass every test: {survivors}"
