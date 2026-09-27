"""
TSK-S4-09 — the device replays the canonical traces; `verify --targets esp32s3` compares.

The firmware replays each trace of `fixtures/traces/` at boot (`targets/esp32s3/main/
trace_vectors.c`, data generated into `main/vectors/` by `scripts/gen_firmware_vectors.py`)
and writes one `NE1` session per trace: the recorded inputs, the device's own verdicts
(`ne_decide`), tokens and pin decisions. Here that boot is compiled on the host with
AddressSanitizer and UndefinedBehaviorSanitizer; its UART output is what
`neuroedge verify --targets esp32s3 --port` reads, exactly as from QEMU or the board.

Checked: the committed vectors match a fresh generation; every canonical trace passes
on the device; a firmware replaying an older trace or gate is refused, not compared; a
missing session fails; deliberate bugs in the C decision or the replay are caught —
a BLOCK turned ALLOW as a SAFETY REGRESSION (NE4002).
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.errors import NeuroEdgeError

from .test_c_trace import compile_exe
from .test_firmware_build import selftest_counts

runner = CliRunner()

BOOT_DRIVER = r"""
#include <stdio.h>
#include "gate_selftest.h"
#include "trace_vectors.h"
static unsigned state = 1u;
static uint32_t clock_ms = 4294967000u;
static void fill(void *buf, size_t len) {
    unsigned char *p = buf;
    for (size_t i = 0; i < len; i++) { state = state * 1103515245u + 12345u; p[i] = (unsigned char)(state >> 16); }
}
static void emit(void *ctx, const char *line) { (void)ctx; printf("%s\n", line); }
static uint32_t now(void *ctx) { (void)ctx; return clock_ms += 7u; }
static char buf[NE_TRACE_LINE_MAX + 1];
static ne_ledger ledger;
int main(void) {
    char line[96];
    ne_trace_sink sink = {emit, now, NULL, buf, sizeof buf, 0, 0, 0};
    const ne_device_info info = {"esp32s3-box-3", NE_AGENT_VERSION, "qemu", 0x2468u, NULL, NULL};
    printf("I (31) boot: ESP-IDF v5.4 2nd stage bootloader\n");
    ne_trace_open(&sink, &info);
    int rc = neuroedge_gate_selftest(&ne_agent_linked, fill, info.boot_id, clock_ms, line,
                                     sizeof line, &sink);
    ne_trace_close(&sink);
    puts(line);
    int n = neuroedge_trace_vectors(&sink, &info, &ledger, fill, info.boot_id);
    printf("NE_TRACE DONE sessions=%d\n", 1 + (n > 0 ? n : 0));
    return rc != 0 || n != 3;
}
"""


@pytest.fixture(scope="module")
def dirs(root) -> dict[str, Path]:
    targets = root / "targets" / "esp32s3"
    return {
        "gate": targets / "components" / "ne_gate",
        "trace": targets / "components" / "ne_trace",
        "agent": targets / "components" / "ne_agent",
        "main": targets / "main",
    }


def boot(dirs, work: Path, walker: Path | None = None, vectors: Path | None = None) -> Path:
    """The firmware's boot on the host: its UART output, as a log file."""
    driver = work / "boot.c"
    driver.write_text(BOOT_DRIVER)
    exe = compile_exe(
        dirs,
        work / "boot",
        [
            walker or dirs["gate"] / "src" / "ne_walker.c",
            dirs["gate"] / "src" / "ne_token.c",
            dirs["trace"] / "src" / "ne_trace.c",
            dirs["main"] / "gate_selftest.c",
            dirs["agent"] / "ne_agent.c",
            vectors or dirs["main"] / "trace_vectors.c",
            driver,
        ],
        strict=True,
        sanitize=walker is None and vectors is None,
    )
    result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    log = work / "uart.log"
    log.write_text(result.stdout)
    return log


@pytest.fixture(scope="module")
def uart(dirs, tmp_path_factory) -> Path:
    return boot(dirs, tmp_path_factory.mktemp("boot"))


def verify(log: Path, targets: str = "esp32s3"):
    return runner.invoke(app, ["verify", "--targets", targets, "--port", str(log)])


def edited(uart: Path, tmp_path: Path, edit) -> Path:
    log = tmp_path / "edited.log"
    log.write_text(edit(uart.read_text()))
    return log


# --- the generated vectors -------------------------------------------------------------------


def test_the_firmware_vectors_match_a_fresh_generation(root):
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "gen_firmware_vectors.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "targets/esp32s3/main/vectors/ is stale against fixtures/traces/ and the sample agents.\n"
        "Run: python/.venv/bin/python scripts/gen_firmware_vectors.py\n"
        f"{result.stdout}{result.stderr}"
    )


def _generator(root, monkeypatch, tmp_path, trace: dict):
    spec = importlib.util.spec_from_file_location(
        "gen_firmware_vectors", root / "scripts" / "gen_firmware_vectors.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "trace.json").write_text(json.dumps(trace))
    monkeypatch.setattr(module, "TRACES", tmp_path)
    return module


@pytest.mark.parametrize(
    ("change", "why"),
    [
        (
            lambda t: t["events"].insert(
                0, _event("sensor_read", {"sensor": "motion", "value": 1})
            ),
            "sensor readings",
        ),
        (
            lambda t: t["events"].insert(  # after gate_evaluation_begin
                3, _event("gate_facts", {"risk_level": {"value": "low", "confidence": "x"}})
            ),
            "not a number",
        ),
    ],
)
def test_what_the_firmware_cannot_replay_is_refused_not_guessed(
    root, traces_dir, monkeypatch, tmp_path, change, why
):
    trace = json.loads((traces_dir / "happy-path.json").read_text())
    change(trace)
    module = _generator(root, monkeypatch, tmp_path, trace)
    with pytest.raises(NeuroEdgeError, match=why):
        module.render()


def _event(type: str, data: dict, offset: int = 1) -> dict:
    return {"offset_ms": offset, "type": type, "data": data}


# --- verify on the device ----------------------------------------------------------------------


def test_the_device_replays_every_canonical_trace_to_its_golden(root, uart):
    text = uart.read_text()
    walker, token = selftest_counts(root / "fixtures" / "agents" / "home-voice" / "agent.toml")
    assert f"NE_SELFTEST PASS walker={walker} token={token}" in text
    assert "NE_TRACE DONE sessions=4" in text
    result = verify(uart, "sim,esp32s3")
    assert result.exit_code == 0, result.output
    assert "6 replay(s) on sim, esp32s3" in result.output
    for name, verdict in [
        ("happy-path.json", "ALLOW"),
        ("network_offline.json", "BLOCK"),
        ("unverified_attempt.json", "BLOCK"),
    ]:
        row = next(line for line in result.output.splitlines() if name in line and "│" in line)
        assert row.count(f"✓ {verdict}") == 2, row
    assert "esp32s3 (device qemu)" in result.output
    assert "operation and duration come from the action table built on the host" in result.output


def test_the_device_decides_fail_closed_and_drives_only_what_its_token_allows(uart):
    lines = [
        json.loads(line[4:]) for line in uart.read_text().splitlines() if line.startswith("NE1 ")
    ]
    sessions, current = {}, None
    for event in lines:
        if event["type"] == "device_info":
            current = sessions.setdefault(event["data"].get("replay_of"), [])
        current.append(event)
    offline = [
        e["data"]
        for e in sessions["network_offline.json"]
        if e["type"].startswith(("gate_ev", "act"))
    ]
    assert offline[-1] == {
        "verdict": "BLOCK",
        "fail_mode": "closed",
        "reason": "gate_unreachable",
        "blocked_by": "unlock_door@1.2.0",
        "action": "deny",
    }
    for name in ("network_offline.json", "unverified_attempt.json"):
        assert not [e for e in sessions[name] if e["type"] == "actuator_command"], name
    [pulse] = [e["data"] for e in sessions["happy-path.json"] if e["type"] == "actuator_command"]
    assert pulse == {"pin": "door_lock", "operation": "pulse", "duration_ms": 30000}


def test_a_firmware_replaying_an_older_trace_is_refused_not_compared(uart, tmp_path):
    log = edited(
        uart,
        tmp_path,
        lambda text: re.sub(r'("trace_digest":"sha256:)[0-9a-f]{4}', r"\g<1>0000", text, count=1),
    )
    result = verify(log)
    assert result.exit_code == 1
    assert "NE4003" in result.output and "firmware is stale" in result.output


def test_a_firmware_deciding_an_older_gate_is_refused_not_compared(uart, tmp_path):
    def older_gate(text: str) -> str:
        head, sep, tail = text.partition('"replay_of":"happy-path.json"')
        return (
            head + sep + re.sub(r'("gate_digest":"sha256:)[0-9a-f]{4}', r"\g<1>0000", tail, count=1)
        )

    result = verify(edited(uart, tmp_path, older_gate))
    assert result.exit_code == 1
    assert "unlock_door@1.2.0" in result.output and "firmware is stale" in result.output


def test_a_trace_the_device_did_not_replay_fails(uart, tmp_path):
    def drop(text: str) -> str:
        lines = text.splitlines(keepends=True)
        start = next(
            i for i, line in enumerate(lines) if '"replay_of":"unverified_attempt.json"' in line
        )
        end = next(i for i in range(start, len(lines)) if '"type":"trace_end"' in lines[i])
        return "".join(lines[:start] + lines[end + 1 :])

    result = verify(edited(uart, tmp_path, drop))
    assert result.exit_code == 1
    assert "no session replaying unverified_attempt.json" in result.output


MUTANTS = {
    # ne_walker.c: fail closed turned ALLOW — network_offline would unlock the door.
    "fail closed allows": (
        "walker",
        "    out->verdict = NE_BLOCK;\n    out->reason = why;\n    out->fail_mode = NE_FAIL_MODE_CLOSED;",
        "    out->verdict = NE_ALLOW;\n    out->reason = why;\n    out->fail_mode = NE_FAIL_MODE_CLOSED;",
        "SAFETY REGRESSION",
    ),
    # trace_vectors.c: the token no longer grants the action's pins.
    "token without the action's pins": (
        "vectors",
        "ne_token_issue(ledger, &tree, step->pin_mask,",
        "ne_token_issue(ledger, &tree, 0u,",
        "actuator command #1",
    ),
    # trace_vectors.c: the pin driven before the verdict is known.
    "pin driven on a BLOCK": (
        "vectors",
        "if (r.verdict != NE_ALLOW) return 0;",
        "",
        "SAFETY REGRESSION",
    ),
}


@pytest.mark.parametrize("label", sorted(MUTANTS))
def test_every_deliberate_device_bug_is_caught(dirs, tmp_path, label):
    which, old, new, expect = MUTANTS[label]
    source = (
        dirs["gate"] / "src" / "ne_walker.c"
        if which == "walker"
        else dirs["main"] / "trace_vectors.c"
    )
    text = source.read_text()
    assert text.count(old) == 1, label
    mutant = tmp_path / source.name
    mutant.write_text(text.replace(old, new))
    log = boot(dirs, tmp_path, **{which: mutant})
    result = verify(log)
    assert result.exit_code == 1, f"{label} passed verify:\n{result.output}"
    assert expect in result.output, result.output
