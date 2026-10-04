"""
LinuxHAL against real kernel GPIO lines — gpio-sim (TSK-S3-05, Q-16).

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh`:

    cd python && python -m pytest -q tests_linux

Not in `tests/`: without gpio-sim these could only skip, and no test may skip.
Here the opposite holds — a missing chip is a failure, never a skip. Line
state is read from sysfs (`sim_gpioN/value`), independently of the process
that drives the line.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from neuroedge.cli.main import app
from neuroedge.engine.trace_sink import EventLog
from neuroedge.errors import PerceptionUnavailableError
from neuroedge.hal.linux import LinuxHAL
from neuroedge.paths import fixtures_dir
from neuroedge.sim import SimSession
from neuroedge.testing import assert_matches_golden, replay
from neuroedge.trace import validate_trace

PINS = ["door_lock", "porch_light", "gate_relay"]
# Input lines (`digital_in` of linux-rpi5), created after the outputs by setup_gpio_sim.sh.
INPUTS = ["door_contact_raw", "limit_switch"]
TRACES = fixtures_dir() / "traces"


@pytest.fixture(scope="module")
def sysfs() -> Path:
    path = os.environ.get("NEUROEDGE_GPIO_SIM_SYSFS")
    assert path, "run scripts/setup_gpio_sim.sh first; it exports NEUROEDGE_GPIO_SIM_SYSFS"
    return Path(path)


def kernel_value(sysfs: Path, pin: str) -> int:
    return int((sysfs / f"sim_gpio{PINS.index(pin)}" / "value").read_text().strip())


def wait_for(sysfs: Path, pin: str, value: int, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if kernel_value(sysfs, pin) == value:
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def hal():
    hal = LinuxHAL(
        events=EventLog(target="linux", board_id="linux-rpi5"), authorize=lambda *_: None
    )
    yield hal
    hal.close()


def test_the_hal_finds_every_board_pin_on_the_virtual_chip(hal):
    assert set(hal.lines) == set(PINS)


def test_a_pulse_reaches_the_kernel_line_and_ends(hal, sysfs):
    assert kernel_value(sysfs, "door_lock") == 0
    hal.digital_out("door_lock", "pulse", 200)
    assert wait_for(sysfs, "door_lock", 1)
    assert wait_for(sysfs, "door_lock", 0), "the pulse must end after its duration"


def test_cancel_drops_the_kernel_line_at_once(hal, sysfs):
    pending = hal.digital_out("door_lock", "pulse", 30000)
    assert wait_for(sysfs, "door_lock", 1)
    pending.cancel()
    assert wait_for(sysfs, "door_lock", 0, timeout=0.2)


def test_the_default_authoriser_leaves_the_kernel_line_untouched(sysfs):
    hal = LinuxHAL()
    try:
        with pytest.raises(Exception, match="ledger|signature"):
            hal.digital_out("door_lock", "pulse", 1000, signature="forged")
        assert kernel_value(sysfs, "door_lock") == 0
    finally:
        hal.close()


@pytest.mark.parametrize("name", ["happy-path", "unverified_attempt", "network_offline"])
def test_each_canonical_trace_decides_the_same_on_linux_as_on_sim(name, sysfs):
    sim = replay(TRACES / f"{name}.json", target="sim")
    linux = replay(TRACES / f"{name}.json", target="linux")
    assert linux.verdicts == sim.verdicts
    assert linux.pin("door_lock").commands == sim.pin("door_lock").commands
    assert_matches_golden(linux, TRACES / f"{name}.json")
    assert kernel_value(sysfs, "door_lock") == 0, "replay releases the lines when it ends"


def test_verify_reaches_target_equivalence_on_sim_and_linux():
    from typer.testing import CliRunner

    result = CliRunner().invoke(app, ["verify", "--targets", "sim,linux"])
    assert result.exit_code == 0, result.output
    assert "linux" in result.output


# --- TSK-S5-10: interactive sessions on linux drive the kernel lines ---------------------

DRIVEWAY = fixtures_dir() / "agents" / "driveway" / "agent.toml"


def child_env() -> dict[str, str]:
    """The environment of a child process, read when it starts: `conftest.py` gives each test its own."""
    return {**os.environ, "NO_COLOR": "1", "COLUMNS": "200"}


def neuroedge(*args: str) -> subprocess.Popen:
    """The real command in a child process: it holds the lines, the test reads sysfs."""
    return subprocess.Popen(
        [sys.executable, "-m", "neuroedge", *args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=child_env(),
    )


def test_the_repl_on_linux_holds_the_line_until_the_session_ends(sysfs):
    child = neuroedge("run", "--target", "linux", "--agent", str(DRIVEWAY))
    try:
        child.stdin.write("bật đèn hiên\n")
        child.stdin.flush()
        assert wait_for(sysfs, "porch_light", 1, timeout=10), "the ALLOW must reach the line"
        output, _ = child.communicate("exit\n", timeout=10)
    finally:
        child.kill()
    assert child.returncode == 0, output
    assert "ALLOW" in output and "on linux (linux-rpi5)" in output
    assert kernel_value(sysfs, "porch_light") == 0, "leaving the session drops every line"


def test_a_blocked_command_on_linux_never_moves_the_kernel_line(sysfs):
    child = neuroedge("run", "--target", "linux", "--agent", str(DRIVEWAY))
    output, _ = child.communicate(":set light_allowed false\nbật đèn hiên\nexit\n", timeout=20)
    assert child.returncode == 0, output
    assert "BLOCK" in output
    assert kernel_value(sysfs, "porch_light") == 0


def test_run_c_on_linux_keeps_the_pulse_for_its_whole_duration(sysfs):
    started = time.monotonic()
    child = neuroedge("run", "--target", "linux", "--agent", str(DRIVEWAY), "-c", "mở cửa ngách")
    try:
        assert wait_for(sysfs, "door_lock", 1, timeout=10)
        output, _ = child.communicate(timeout=20)
    finally:
        child.kill()
    assert child.returncode == 0, output
    assert time.monotonic() - started >= 4.5, "buzz_in pulses 5 s; -c must not cut it short"
    assert kernel_value(sysfs, "door_lock") == 0


def test_a_trace_recorded_on_linux_replays_the_same_on_sim_and_linux(sysfs, tmp_path):
    out = tmp_path / "linux.json"
    child = neuroedge("record", "--target", "linux", "--agent", str(DRIVEWAY), "--out", str(out))
    output, _ = child.communicate(
        "bật đèn hiên\n:set visitor_expected false\nmở cổng\nexit\n", timeout=30
    )
    assert child.returncode == 0, output
    check = neuroedge("trace", "validate", str(out))
    checked, _ = check.communicate(timeout=20)
    assert check.returncode == 0, checked

    sim = replay(out, target="sim", agent=DRIVEWAY)
    linux = replay(out, target="linux", agent=DRIVEWAY)
    assert linux.verdicts == sim.verdicts == sim.recorded_verdicts
    for pin in ("porch_light", "gate_relay"):
        assert linux.pin(pin).commands == sim.pin(pin).commands
    assert_matches_golden(linux, out)
    assert all(kernel_value(sysfs, pin) == 0 for pin in PINS)


def test_mcp_serve_on_linux_drives_the_kernel_line_through_the_gate(sysfs, tmp_path):
    trace_out = tmp_path / "mcp.json"
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            *("-m", "neuroedge", "mcp", "serve", "--target", "linux"),
            *("--agent", str(DRIVEWAY), "--trace-out", str(trace_out)),
        ],
        env=child_env(),
    )

    async def main():
        with (tmp_path / "stderr.txt").open("w", encoding="utf-8") as errlog:
            async with (
                stdio_client(params, errlog=errlog) as (read, write),
                ClientSession(read, write) as client,
            ):
                with anyio.fail_after(20):
                    await client.initialize()
                    result = await client.call_tool("porch_light_on", {})
                    driven = await anyio.to_thread.run_sync(wait_for, sysfs, "porch_light", 1)
        return result, driven

    result, driven = anyio.run(main)
    assert result.structured_content["status"] == "ALLOW"
    assert driven, "the tools/call must reach the kernel line"
    deadline = time.monotonic() + 10
    while not trace_out.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert trace_out.exists(), "closing stdin ends the server and writes the trace"
    assert wait_for(sysfs, "porch_light", 0), "the server drops every line when it ends"
    trace = json.loads(trace_out.read_text(encoding="utf-8"))
    validate_trace(trace)
    assert trace["metadata"]["target"] == "linux"


def test_sigterm_ends_a_linux_session_with_every_line_dropped(sysfs):
    """An MCP host stops its server with SIGTERM: the line must not stay driven."""
    child = neuroedge("run", "--target", "linux", "--agent", str(DRIVEWAY))
    try:
        child.stdin.write("bật đèn hiên\n")
        child.stdin.flush()
        assert wait_for(sysfs, "porch_light", 1, timeout=10), "the ALLOW must reach the line"
        child.terminate()
        output, _ = child.communicate(timeout=10)
    finally:
        child.kill()
    assert child.returncode == 143, output
    assert kernel_value(sysfs, "porch_light") == 0, "SIGTERM runs close(): every line inactive"


def test_sigterm_ends_mcp_serve_on_linux_even_with_stdin_still_open(sysfs):
    """The SDK's stdin thread is not a daemon: SIGTERM must still end the server, lines dropped."""
    child = neuroedge("mcp", "serve", "--target", "linux", "--agent", str(DRIVEWAY))
    try:
        time.sleep(3)  # the server holds the lines and waits on stdin
        child.terminate()
        output, _ = child.communicate(timeout=10)
    finally:
        child.kill()
    assert child.returncode == 143, output
    assert all(kernel_value(sysfs, pin) == 0 for pin in PINS)


# --- TSK-I2a-02: digital.in on real kernel lines (RFC-0007 §3a) -----------------------------


def pull(sysfs: Path, pin: str, high: bool) -> None:
    """What a switch wired to the line does: gpio-sim's `pull` is the level an input reads."""
    index = [*PINS, *INPUTS].index(pin)
    (sysfs / f"sim_gpio{index}" / "pull").write_text("pull-up" if high else "pull-down")


@pytest.mark.parametrize("pin", INPUTS)
def test_an_input_line_reads_the_level_the_kernel_holds(hal, sysfs, pin):
    pull(sysfs, pin, True)
    assert hal.digital_in(pin, called_from="test") is True
    pull(sysfs, pin, False)
    assert hal.digital_in(pin, called_from="test") is False
    events = [e["data"] for e in hal.events.events if e["type"] == "digital_in"]
    assert events == [{"pin": pin, "value": True}, {"pin": pin, "value": False}]


def test_an_input_line_is_requested_as_an_input_and_never_driven(hal, sysfs):
    pull(sysfs, "limit_switch", True)
    assert hal.digital_in("limit_switch", called_from="test") is True
    index = [*PINS, *INPUTS].index("limit_switch")
    value = int((sysfs / f"sim_gpio{index}" / "value").read_text().strip())
    assert value == 1, "an output driven inactive would read 0 here; an input reads its pull"
    assert not any(kernel_value(sysfs, pin) for pin in PINS), "no output line moved"


def test_a_pin_the_board_does_not_declare_as_an_input_is_refused_and_no_line_is_touched(hal, sysfs):
    with pytest.raises(Exception, match="declares no input pin"):
        hal.digital_in("door_lock", called_from="test")
    assert kernel_value(sysfs, "door_lock") == 0


def test_a_line_released_by_close_cannot_be_read_again(sysfs):
    hal = LinuxHAL(events=EventLog(target="linux", board_id="linux-rpi5"))
    pull(sysfs, "limit_switch", True)
    assert hal.digital_in("limit_switch", called_from="test") is True
    hal.close()
    with pytest.raises(PerceptionUnavailableError):
        hal.digital_in("limit_switch", called_from="test")
    # The kernel line is free again: another process may request it.
    other = LinuxHAL(events=EventLog(target="linux", board_id="linux-rpi5"))
    try:
        assert other.digital_in("limit_switch", called_from="test") is True
    finally:
        other.close()


GATE = """\
schema: neuroedge.gate/v1
name: shut
version: 1.0.0
evaluate:
  door_closed:
    type: bool
    instructions: the door contact reads closed
allow_when:
  door_closed: true
on_block:
  action: deny
budget:
  p95_latency_ms: 100
  fail: closed
"""


def digital_agent(directory: Path) -> Path:
    """`đóng cổng` behind a gate that reads the door contact line."""
    (directory / "actions").mkdir()
    (directory / "actions" / "gate.py").write_text(
        "from neuroedge import action\n"
        "from neuroedge.hal import digital\n\n"
        '@action(name="gpio_sim_shut", requires="digital.out:gate_relay", gate="shut")\n'
        "def shut() -> None:\n"
        '    digital.out("gate_relay").on()\n',
        encoding="utf-8",
    )
    (directory / "shut.yaml").write_text(GATE, encoding="utf-8")
    (directory / "commands.toml").write_text(
        '[grammar]\nversion = 1\n\n[[command]]\nintent = "shut"\npatterns = ["đóng cổng"]\n'
        'tool = "gpio_sim_shut"\n',
        encoding="utf-8",
    )
    (directory / "agent.toml").write_text(
        '[agent]\nname = "gpio-sim-digital-in"\nversion = "0.1.0"\n\n'
        '[requires]\n"digital.out" = { pins = ["gate_relay"] }\n'
        '"digital.in" = { pins = ["door_contact_raw"] }\n\n'
        '[gates]\nshut = "shut.yaml"\n\n'
        '[sim.digital_facts]\ndoor_closed = { pin = "door_contact_raw" }\n',
        encoding="utf-8",
    )
    return directory / "agent.toml"


def test_a_level_set_through_gpio_sim_is_a_gate_fact_that_allows_and_blocks(sysfs, tmp_path):
    path = digital_agent(tmp_path)
    session = SimSession.load(path, target="linux")
    try:
        pull(sysfs, "door_contact_raw", False)
        blocked = asyncio.run(session.handle("đóng cổng"))
        assert not blocked.allowed and blocked.result.gate.reason == "condition_not_met"
        assert kernel_value(sysfs, "gate_relay") == 0
        pull(sysfs, "door_contact_raw", True)
        allowed = asyncio.run(session.handle("đóng cổng"))
        assert allowed.allowed and wait_for(sysfs, "gate_relay", 1)
        fact = session.events.of_type("gate_facts")[-1]["door_closed"]
        assert fact["value"] is True and fact["source"] == "digital.in"
        assert fact["age_ms"] == fact["eval_offset_ms"] - fact["read_offset_ms"] >= 0
    finally:
        session.close()
    assert kernel_value(sysfs, "gate_relay") == 0


@pytest.mark.usefixtures("fresh_actions")
def test_an_input_line_that_cannot_be_read_blocks_criterion_unavailable(sysfs, tmp_path):
    import gpiod

    path = digital_agent(tmp_path)
    session = SimSession.load(path, target="linux")
    squatter = None
    try:
        pull(sysfs, "door_contact_raw", True)
        # The session's request is lost, and another process takes the line: the next read
        # cannot request it again.
        for request, _offset in session.hal._inputs.values():
            request.release()
        session.hal._inputs.clear()
        offset = [*PINS, *INPUTS].index("door_contact_raw")
        squatter = gpiod.request_lines(
            os.environ["NEUROEDGE_GPIO_SIM_CHIP"],
            consumer="squatter",
            config={
                (offset,): gpiod.LineSettings(direction=gpiod.line.Direction.INPUT),
            },
        )
        turn = asyncio.run(session.handle("đóng cổng"))
        assert not turn.allowed and turn.result.gate.reason == "criterion_unavailable"
        assert kernel_value(sysfs, "gate_relay") == 0
        assert "cannot be read" in session.events.of_type("digital_in")[-1]["reason"]
    finally:
        if squatter is not None:
            squatter.release()
        session.close()
