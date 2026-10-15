"""
The aquarium sample (`fixtures/agents/aquarium`) and its demos on simulation and emulation
(`demo/i2b-be-ca-gia-lap/`).

`gate_relay` is the heater, `door_lock` the air pump, `porch_light` the tank light; the water
probe is the board's `temperature`, and `[sim.sensor_facts]` turns it into `water_hot` (≥ 29 °C).

* tank_heater_on   — refused while the water is warm, or while the probe reports nothing;
* tank_aerator_off — asks the owner; refused without a question while the water is warm;
* tank_heater_off, tank_aerator_on, the light — always allowed.

The same rules on the chip (the bridge, host-compiled) are checked against the box below; on a
real kernel (gpio-sim, an LM75 on i2c-stub) in `tests_linux/test_kit_aquarium.py`; on QEMU by
`scripts/qemu_aquarium.py` in the `aquarium-qemu` job (firmware-qemu.yml).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neuroedge.actions.tools import ToolCall
from neuroedge.cli.main import app
from neuroedge.paths import repo_root
from neuroedge.sim import SimSession
from neuroedge.testing import TracePlayer
from neuroedge.testing.recorder import TraceRecorder

from .hand_clock import HandClock
from .test_c_bridge import built, same_contract

ROOT = repo_root()
AGENT = ROOT / "fixtures" / "agents" / "aquarium" / "agent.toml"
DAY = ROOT / "demo" / "i2b-be-ca-gia-lap" / "mot-ngay.txt"
WARM = [29, 29.001, 31, 40]
COOL = [18, 24, 28.5, 28.999]
NOT_A_READING = ["lỗi", float("nan"), True]
# The presenter's pace (`chay-sim.sh` waits about this long between lines): past a relay's
# min_interval_ms, well inside a question's 10 s and the relays' max_continuous_ms.
PACE_MS = 1_500


def session_for(reading=None, **options) -> SimSession:
    session = SimSession.load(AGENT, **options)
    if reading is not None:
        session.set_sensor("temperature", reading)
    return session


def say(session: SimSession, *lines: str):
    return [asyncio.run(session.handle(line)) for line in lines]


def commands(session: SimSession, pin: str) -> list[str]:
    return [operation for operation, _ in session.hal.pin(pin).commands]


# --- the heater ----------------------------------------------------------------------------


@pytest.mark.parametrize("reading", COOL)
def test_the_heater_comes_on_while_the_water_is_cool(reading):
    session = session_for(reading)
    (on,) = say(session, "bật sưởi")
    assert on.allowed
    assert commands(session, "gate_relay") == ["on"]


@pytest.mark.parametrize("reading", WARM)
def test_the_heater_never_comes_on_in_warm_water_and_nobody_is_asked(reading):
    session = session_for(reading)
    (on,) = say(session, "bật sưởi")
    assert on.result.blocked
    assert on.result.gate.failed_criterion == "water_hot"
    assert on.result.gate.on_block_action == "deny"
    assert on.confirmation is None
    assert commands(session, "gate_relay") == []


@pytest.mark.parametrize("reading", NOT_A_READING, ids=repr)
def test_without_a_reading_the_heater_stays_off(reading):
    session = session_for(reading)
    (on,) = say(session, "bật sưởi")
    assert on.result.blocked
    assert on.result.gate.reason == "criterion_unavailable"
    assert commands(session, "gate_relay") == []


@pytest.mark.parametrize("reading", [*COOL, *WARM, *NOT_A_READING], ids=repr)
def test_the_heater_can_always_be_turned_off(reading):
    session = session_for(reading)
    (off,) = say(session, "tắt sưởi")
    assert off.allowed
    assert commands(session, "gate_relay") == ["off"]


# --- the air pump: safe means on -------------------------------------------------------------


@pytest.mark.parametrize("reading", [*COOL, *WARM, *NOT_A_READING], ids=repr)
def test_the_air_pump_can_always_be_turned_on(reading):
    session = session_for(reading)
    (on,) = say(session, "bật sục khí")
    assert on.allowed
    assert commands(session, "door_lock") == ["on"]


def test_turning_the_air_pump_off_asks_the_owner_and_a_yes_turns_it_off():
    session = session_for(24)
    off, yes = say(session, "tắt sục khí", "có")
    assert off.result.blocked
    assert off.result.gate.failed_criterion == "owner_confirmed"
    assert off.confirmation is not None and off.confirmation.confirms == ("owner_confirmed",)
    assert yes.allowed
    assert commands(session, "door_lock") == ["off"]


def test_a_no_keeps_the_air_pump_running():
    session = session_for(24)
    say(session, "tắt sục khí", "không")
    assert commands(session, "door_lock") == []


@pytest.mark.parametrize("reading", [*WARM, *NOT_A_READING], ids=repr)
def test_in_warm_water_the_air_pump_cannot_be_turned_off_and_nothing_is_asked(reading):
    session = session_for(reading)
    off, yes = say(session, "tắt sục khí", "có")
    assert off.result.blocked
    assert off.confirmation is None  # a yes would not be enough: water_hot fails too
    assert not yes.allowed
    assert commands(session, "door_lock") == []


def test_a_yes_is_decided_on_a_fresh_reading():
    session = session_for(24)
    say(session, "tắt sục khí")
    session.set_sensor("temperature", 30)  # the tank warmed while the owner was asked
    (yes,) = say(session, "có")
    assert not yes.allowed
    assert commands(session, "door_lock") == []


def test_a_brain_over_mcp_is_told_a_question_waits_and_cannot_answer_it():
    session = session_for(24)
    result = asyncio.run(
        session.call_tool(ToolCall("tank_aerator_off", {}, source="mcp"))
    ).content()
    assert result["status"] == "BLOCK" and result["on_block"] == "ask"
    assert "confirmation" in result
    assert commands(session, "door_lock") == []


@pytest.mark.parametrize("reading", [*COOL, *WARM], ids=repr)
def test_the_light_is_free(reading):
    session = session_for(reading)
    on, off = say(session, "bật đèn bể", "tắt đèn bể")
    assert on.allowed and off.allowed
    assert commands(session, "porch_light") == ["on", "off"]


# --- the demo: one day of the tank, then replay ----------------------------------------------

# What each line of `mot-ngay.txt` must do, in order: a verdict for a command, None for a
# `:sensor` line, "asks" / "confirmed" / "declined" for a question and its answer.
DAY_EXPECTED = [
    "ALLOW",  # bật đèn bể
    "ALLOW",  # bật sưởi (25 °C)
    "ALLOW",  # bật sục khí
    None,  # 29 °C
    "BLOCK",  # bật sưởi: warm water
    "ALLOW",  # tắt sưởi
    None,  # 31 °C
    "BLOCK",  # tắt sục khí: refused, nothing asked
    None,  # the probe reports garbage
    "BLOCK",  # bật sưởi: no reading, fail closed
    None,  # 24 °C
    "ALLOW",  # bật sưởi
    "asks",  # tắt sục khí
    "declined",  # không
    "asks",  # tắt sục khí
    "confirmed",  # có
    "ALLOW",  # bật sục khí
    "ALLOW",  # tắt đèn bể
]


def run_the_day(clock: HandClock, recorder: TraceRecorder | None = None) -> list:
    session = SimSession.load(AGENT, events=recorder, clock=clock)
    outcomes = []
    for line in DAY.read_text(encoding="utf-8").splitlines():
        if line == "exit":
            break
        if line.startswith(":sensor "):
            _, name, value = line.split(" ", 2)
            try:
                reading: float | str = float(value)
            except ValueError:
                reading = value
            session.set_sensor(name, reading)
            outcomes.append(None)
            continue
        turn = asyncio.run(session.handle(line))
        if line in ("có", "không"):
            outcomes.append("confirmed" if turn.allowed else "declined")
        elif turn.confirmation is not None:
            outcomes.append("asks")
        else:
            outcomes.append("ALLOW" if turn.allowed else "BLOCK")
        clock.advance(PACE_MS)
    return [session, outcomes]


def test_one_day_of_the_tank_does_what_the_demo_says():
    session, outcomes = run_the_day(HandClock())
    assert outcomes == DAY_EXPECTED
    assert commands(session, "gate_relay") == ["on", "off", "on"]
    assert commands(session, "door_lock") == ["on", "off", "on"]
    assert commands(session, "porch_light") == ["on", "off"]


async def test_the_day_replays_to_the_same_decisions(tmp_path: Path):
    clock = HandClock()
    recorder = TraceRecorder(clock=clock)
    await asyncio.to_thread(run_the_day, clock, recorder)
    result = await TracePlayer(recorder.to_trace(), agent=AGENT).replay()
    assert result.verdicts == result.recorded_verdicts
    assert result.verdicts.count("BLOCK") >= 3


# --- the same rules on the chip (Profile B bridge, host-compiled) ------------------------------

# The box reads the probe; on the chip the console's `fact water_hot` stands in for it (DP-B-05).
CHIP_STEPS = [
    (25, "tank_heater_on"),
    (25, "tank_aerator_off"),
    (31, "tank_heater_on"),
    (31, "tank_aerator_off"),
    (25, "tank_heater_off"),
    (31, "tank_aerator_on"),
    (25, "tank_light_on"),
]


def test_the_chip_decides_as_the_box_does(tmp_path):
    bridge = built(tmp_path, AGENT.parent)
    lines = ["fact owner_confirmed false"]
    for reading, tool in CHIP_STEPS:
        lines += [f"fact water_hot {'true' if reading >= 29 else 'false'}", f"call {tool} {{}}"]
    chip = bridge.results(*lines)
    box = []
    session = SimSession.load(AGENT)
    for reading, tool in CHIP_STEPS:
        session.set_sensor("temperature", reading)
        box.append(asyncio.run(session.call_tool(ToolCall(tool, {}, source="mcp"))).content())
    same_contract(box, chip)
    assert [r["status"] for r in chip] == ["ALLOW", "BLOCK", "BLOCK", "BLOCK"] + ["ALLOW"] * 3
    assert "confirmation" in chip[1] and "confirmation" not in chip[3]


def test_the_chips_decisions_replay_on_the_laptop(tmp_path):
    """D3: NE1 sessions from the chip, typed facts and all, replay to the same decisions."""
    bridge = built(tmp_path, AGENT.parent)
    out = bridge.run(
        "trace on",
        "fact owner_confirmed false",
        "fact water_hot false",
        "call tank_heater_on {}",
        "call tank_aerator_on {}",
        "fact water_hot true",
        "call tank_heater_on {}",
        "call tank_aerator_off {}",
        "fact water_hot false",
        "call tank_aerator_off {}",
        "button confirm_1 1",
    )
    log = tmp_path / "uart.log"
    log.write_text(
        "\n".join([*(line for line in out if line.startswith("NE1 ")), "NE_TRACE DONE", ""]),
        encoding="utf-8",
    )
    traces = tmp_path / "traces"
    recorded = CliRunner().invoke(
        app, ["record", "--target", "esp32s3", "--port", str(log), "--out", f"{traces}/"]
    )
    assert recorded.exit_code == 0, recorded.output
    sessions = sorted(traces.glob("sess_*.json"))
    assert len(sessions) == 6
    for trace in sessions:
        replayed = CliRunner().invoke(app, ["replay", str(trace), "--agent", str(AGENT)])
        assert replayed.exit_code == 0, replayed.output
        assert "decisions match the recording" in replayed.output
