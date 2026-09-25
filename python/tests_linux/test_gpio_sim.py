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
from neuroedge.hal.linux import LinuxHAL
from neuroedge.paths import fixtures_dir
from neuroedge.testing import assert_matches_golden, replay
from neuroedge.trace import validate_trace

PINS = ["door_lock", "porch_light", "gate_relay"]
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
CHILD_ENV = {**os.environ, "NO_COLOR": "1", "COLUMNS": "200"}


def neuroedge(*args: str) -> subprocess.Popen:
    """The real command in a child process: it holds the lines, the test reads sysfs."""
    return subprocess.Popen(
        [sys.executable, "-m", "neuroedge", *args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=CHILD_ENV,
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
        env=CHILD_ENV,
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
