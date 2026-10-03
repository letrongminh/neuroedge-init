"""
I2a exit criterion 3, the last two packs (RFC-0013 §3f item 7): the corpora `fixtures/traces/fine-control/`
(PWM and its read-back, sample agent `fan-pwm`) and `fixtures/traces/motion/` (leased motion, sample
agent `rover`), replayed by `neuroedge verify` beside `sensor-pack` and `vision`.

Each corpus is what its sample agent records (the generator's `--check`), replays to the same
verdicts, pin and motion commands, safe states and envelope refusals on every reference board that
declares what its traces use — `sim-rpi5` and, with a fake gpiod standing in for the lines,
`linux-rpi5` — and is skipped (`—`) on a board without. The agents on gpio-sim are the `linux-hal`
job's; the kernel PWM itself is the nightly Pi 5's.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

import neuroedge.hal.linux as linux
from neuroedge.cli.main import EXTENSION_TRACES, _trace_lacks, app
from neuroedge.hal.board import load_board_by_id
from neuroedge.testing import assert_matches_golden, replay
from neuroedge.trace import validate_trace

from .test_hal_linux import FakeGpiod

runner = CliRunner()

PACKS = {
    "fine-control": ("fan-pwm", "gen_fine_control_traces.py"),
    "motion": ("rover", "gen_motion_traces.py"),
}
# What each corpus holds: gate verdicts, in order, per trace.
OUTCOMES = {
    "fine-control": {
        "fan-pwm-allow": [("ALLOW", None, None), ("ALLOW", None, None)],
        "fan-pwm-block": [
            ("BLOCK", "argument_out_of_range", "duty"),
            ("BLOCK", "argument_out_of_range", "frequency_hz"),
            ("ALLOW", None, None),
            ("ALLOW", None, None),  # allowed by the gate, refused by the envelope: `already_on`
            ("ALLOW", None, None),
        ],
        "fan-pwm-measured": [("ALLOW", None, None), ("BLOCK", "condition_not_met", "fan_load")],
        "fan-pwm-unavailable": [("BLOCK", "criterion_unavailable", "fan_load")],
        "fan-pwm-commanded": [
            ("ALLOW", None, None),
            ("BLOCK", "criterion_unavailable", "fan_load"),
        ],
    },
    "motion": {
        "rover-drive-allow": [("ALLOW", None, None)] * 3,
        "rover-gate-block": [("ALLOW", None, None), ("BLOCK", "condition_not_met", "path_clear")],
        "rover-lease-expired": [("ALLOW", None, None)],
        "rover-speed-refused": [
            ("BLOCK", "argument_out_of_range", "speed"),
            ("ALLOW", None, None),
        ],
    },
}


def corpus(root: Path, pack: str) -> list[Path]:
    return sorted((root / "fixtures" / "traces" / pack).glob("*.json"))


def agent_of(root: Path, pack: str) -> Path:
    return root / "fixtures" / "agents" / PACKS[pack][0] / "agent.toml"


def events(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["events"]


def test_verify_knows_every_pack():
    assert set(PACKS) <= set(EXTENSION_TRACES)


@pytest.mark.parametrize("pack", PACKS)
def test_the_corpus_is_what_the_sample_agent_records(root, pack):
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / PACKS[pack][1]), "--check"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("pack", PACKS)
def test_the_corpus_holds_the_decisions_it_is_named_for(root, pack):
    outcomes = {
        path.stem: [
            (e["data"]["verdict"], e["data"].get("reason"), e["data"].get("failed_criterion"))
            for e in events(path)
            if e["type"] == "gate_evaluation_result"
        ]
        for path in corpus(root, pack)
    }
    assert outcomes == OUTCOMES[pack]


def test_fine_control_holds_pwm_commands_the_envelope_refusal_and_both_kinds_of_read_back(root):
    by_name = {path.stem: events(path) for path in corpus(root, "fine-control")}
    commands = [e["data"] for e in by_name["fan-pwm-allow"] if e["type"] == "actuator_command"]
    assert [(c["operation"], c.get("frequency_hz"), c.get("duty")) for c in commands] == [
        ("pwm", 1000, 0.5),
        ("off", None, None),
    ]
    refused = [e["data"] for e in by_name["fan-pwm-block"] if e["type"] == "envelope_refused"]
    assert [(r["pin"], r["operation"], r["reason"]) for r in refused] == [
        ("fan", "pwm", "already_on")
    ]

    def fact_reads(name):
        return [
            e["data"] for e in by_name[name] if e["type"] == "pin_state" and e["data"].get("use")
        ]

    assert [r["source"] for r in fact_reads("fan-pwm-measured")] == ["measured", "measured"]
    assert [r["duty"] for r in fact_reads("fan-pwm-measured")] == [0.1, 0.6]
    (failed,) = fact_reads("fan-pwm-unavailable")
    assert "source" not in failed and "does not answer" in failed["reason"]
    assert {r["source"] for r in fact_reads("fan-pwm-commanded")} == {"commanded"}
    # a commanded duty is never offered to the gate as a number
    commanded_facts = [e["data"] for e in by_name["fan-pwm-commanded"] if e["type"] == "gate_facts"]
    judged = [f["fan_load"] for f in commanded_facts if "fan_load" in f]
    assert judged and all(f["value"] is None for f in judged)


def test_motion_holds_a_renewed_lease_a_lapsed_one_and_a_block_that_stops_the_wheel(root):
    by_name = {path.stem: events(path) for path in corpus(root, "motion")}

    def of(name, kind):
        return [e["data"] for e in by_name[name] if e["type"] == kind]

    assert [c["run"] for c in of("rover-drive-allow", "motion_command")] == [
        "new",
        "renewed",
        "new",
    ]
    assert of("rover-lease-expired", "motion_safe") == [
        {"channel": "wheel_left", "state": "stop", "cause": "lease_expired"}
    ]
    assert of("rover-gate-block", "motion_safe") == [
        {"channel": "wheel_left", "state": "stop", "cause": "block"}
    ]
    assert [c["speed"] for c in of("rover-speed-refused", "motion_command")] == [0.5], (
        "the speed over the gate's limit never reached the wheel"
    )


@pytest.mark.parametrize("pack", PACKS)
def test_the_corpus_validates(root, pack):
    for path in corpus(root, pack):
        validate_trace(json.loads(path.read_text(encoding="utf-8")))


@pytest.fixture
def gpio(monkeypatch, tmp_path):
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    # the reference rig's lines, as a replay on `linux` requests them
    names = ["door_lock", "porch_light", "gate_relay", "door_contact_raw", "limit_switch"]
    fake = FakeGpiod({str(chip): names})
    monkeypatch.setattr(linux, "CHIP_GLOB", str(tmp_path / "gpiochip*"))
    monkeypatch.setattr(linux, "_import_gpiod", lambda: fake)
    return fake


@pytest.mark.parametrize("pack", PACKS)
@pytest.mark.parametrize(("target", "board"), [("sim", "sim-rpi5"), ("linux", "linux-rpi5")])
def test_the_corpus_replays_to_what_it_recorded_on_every_board_that_declares_its_primitives(
    root, gpio, pack, target, board
):  # on linux a replay does drive the (fake) lines, and never opens the kernel's PWM or the motors
    for path in corpus(root, pack):
        recorded = json.loads(path.read_text(encoding="utf-8"))
        result = replay(path, agent=agent_of(root, pack), target=target, board_id=board)
        assert result.verdicts == [
            e["data"]["verdict"]
            for e in recorded["events"]
            if e["type"] == "gate_evaluation_result"
        ], path.name
        assert result.warnings == [] and result.divergences == []
        assert_matches_golden(result, recorded)


@pytest.mark.parametrize("pack", PACKS)
def test_a_board_without_the_primitives_cannot_replay_the_corpus(root, pack):
    for board in ("sim-default", "esp32s3-box-3"):
        for path in corpus(root, pack):
            trace = json.loads(path.read_text(encoding="utf-8"))
            assert _trace_lacks(load_board_by_id(board), trace), (board, path.name)
    for board in ("sim-rpi5", "linux-rpi5"):
        for path in corpus(root, pack):
            assert _trace_lacks(load_board_by_id(board), json.loads(path.read_text())) == []


def test_verify_replays_every_corpus_where_it_is_declared_and_skips_it_elsewhere():
    result = runner.invoke(app, ["verify", "--targets", "sim"])
    assert result.exit_code == 0, result.output
    for pack, count in (("fine-control", 5), ("motion", 4)):
        table = [line for line in result.output.splitlines() if "│" in line and f"{pack}/" in line]
        assert len(table) >= count  # a verdict list may wrap onto a second line
        first = [line for line in table if ".json" in line or "…" in line]
        for line in first:
            cells = [cell.strip() for cell in line.split("│") if cell.strip()]
            assert cells[1] == "—" and cells[2].startswith("✓"), line  # sim-default skips
        assert f"The `{pack}` corpus replays alike: {count} on sim/sim-rpi5" in " ".join(
            result.output.replace("│", " ").split()
        )
    # counted apart: the canonical replays stay three per board
    assert "3 replay(s) on sim/sim-default, 3 replay(s) on sim/sim-rpi5" in " ".join(
        result.output.replace("│", " ").split()
    )


@pytest.mark.parametrize("pack", PACKS)
def test_a_corpus_no_board_can_replay_fails_verify_never_passes(root, monkeypatch, pack):
    import neuroedge.cli.main as main

    monkeypatch.setattr(
        main, "REFERENCE_BOARDS", {"sim": ("sim-default",), "linux": ("linux-rpi5",)}
    )
    result = runner.invoke(app, ["verify", "--targets", "sim"])
    assert result.exit_code != 0, result.output
    assert f"{pack} corpus replays compared" in " ".join(result.output.split())
