"""
TSK-S5-10 — interactive sessions on `linux`: `run`, `record`, `mcp serve --target linux`.

Against the in-memory gpiod stand-in of `test_hal_linux.py`, so these run everywhere.
The same commands against real kernel lines (gpio-sim) are in `tests_linux/`.
"""

from __future__ import annotations

import json
import sys
import tomllib

import anyio
import pytest
from mcp import Client
from typer.testing import CliRunner

import neuroedge.hal.linux as linux
from neuroedge.actions.tools import ToolCall
from neuroedge.cli.main import app
from neuroedge.errors import BoardCapabilityError
from neuroedge.hal.linux import TypedLinuxHAL
from neuroedge.mcp_server import build_server
from neuroedge.sim import SimSession
from neuroedge.testing import assert_matches_golden, replay
from neuroedge.trace import validate_trace

from .test_hal_linux import LINES, FakeGpiod, Value

runner = CliRunner()


@pytest.fixture
def driveway(root):
    return root / "fixtures" / "agents" / "driveway" / "agent.toml"


@pytest.fixture
def gpio(monkeypatch, tmp_path):
    """Virtual lines named after the board pins, where `LinuxHAL` looks for them."""
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    fake = FakeGpiod({str(chip): LINES})
    monkeypatch.setattr(linux, "CHIP_GLOB", str(tmp_path / "gpiochip*"))
    monkeypatch.setattr(linux, "_import_gpiod", lambda: fake)
    return fake


def line(fake: FakeGpiod, pin: str) -> Value:
    (path,) = fake.chips
    return fake.values.get((path, LINES.index(pin)), Value.INACTIVE)


def invoke(*args, stdin=None):
    return runner.invoke(app, list(args), input=stdin)


# --- run --------------------------------------------------------------------------------


def test_run_c_drives_a_real_line_and_releases_it_on_exit(driveway, gpio):
    result = invoke("run", "--target", "linux", "--agent", str(driveway), "-c", "bật đèn hiên")
    assert result.exit_code == 0, result.output
    assert "ALLOW" in result.output and "porch_light_on()" in result.output
    assert "GPIO lines" in result.output
    # Driven on by the command, then dropped inactive when the session ended.
    assert gpio.history[0] == ("porch_light", 1)
    assert ("porch_light", 0) in gpio.history[1:]
    assert all(value == 0 for _, value in gpio.history[1:]), "every line inactive at the end"
    assert all(request.released for request in gpio.requests)


def test_a_blocked_command_on_linux_leaves_the_line_untouched_and_exits_zero(driveway, gpio):
    result = invoke(
        "run", "--target", "linux", "--agent", str(driveway),
        stdin=":set light_allowed false\nbật đèn hiên\nexit\n",
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    assert "BLOCK" in result.output
    assert ("porch_light", 1) not in gpio.history


def test_the_repl_on_linux_names_the_target_and_board(driveway, gpio):
    result = invoke("run", "--target", "linux", "--agent", str(driveway), stdin="exit\n")
    assert result.exit_code == 0, result.output
    assert "driveway@0.1.0 on linux (linux-rpi5)" in result.output


def test_leaving_the_repl_drops_a_pulse_in_flight(driveway, gpio):
    result = invoke(
        "run", "--target", "linux", "--agent", str(driveway), stdin="mở cửa ngách\nexit\n"
    )
    assert result.exit_code == 0, result.output
    assert gpio.history[0] == ("door_lock", 1)
    assert ("door_lock", 0) in gpio.history[1:]
    assert all(value == 0 for _, value in gpio.history[1:]), "every line inactive at the end"
    assert all(request.released for request in gpio.requests)


def test_run_c_waits_for_its_pulse_before_dropping_the_lines(driveway, gpio, monkeypatch):
    settled: list[list[str]] = []
    monkeypatch.setattr(TypedLinuxHAL, "settle", lambda self: settled.append(self.pulsing()))
    result = invoke("run", "--target", "linux", "--agent", str(driveway), "-c", "mở cửa ngách")
    assert result.exit_code == 0, result.output
    assert settled == [["door_lock"]]
    assert "waiting for the pulse on door_lock" in result.output


def test_settle_returns_when_the_pulse_ends(tmp_path):
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    fake = FakeGpiod({str(chip): LINES})
    hal = TypedLinuxHAL(
        chip_glob=str(tmp_path / "gpiochip*"), gpiod=fake, authorize=lambda *_: None
    )
    hal.digital_out("door_lock", "pulse", 50)
    assert hal.pulsing() == ["door_lock"]
    hal.settle()
    assert hal.pulsing() == [] and not hal.line_value("door_lock")
    hal.close()


# --- what linux cannot run: a clear diagnostic, exit 1, no traceback ---------------------


def test_no_gpiod_is_a_three_part_error_not_a_traceback(driveway, monkeypatch):
    monkeypatch.setitem(sys.modules, "gpiod", None)  # `import gpiod` raises ImportError
    result = invoke("run", "--target", "linux", "--agent", str(driveway), "-c", "bật đèn hiên")
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert "gpiod" in result.output and "neuroedge[linux]" in result.output
    assert "why:" in result.output and "fix:" in result.output


def test_no_gpio_chip_is_a_three_part_error_not_a_no_op(driveway, monkeypatch, tmp_path):
    monkeypatch.setattr(linux, "CHIP_GLOB", str(tmp_path / "gpiochip*"))
    monkeypatch.setattr(linux, "_import_gpiod", lambda: FakeGpiod({}))
    for verb in (["run"], ["record", "--out", str(tmp_path / "t.json")]):
        result = invoke(*verb, "--target", "linux", "--agent", str(driveway), "-c", "bật đèn hiên")
        assert result.exit_code == 1, result.output
        assert isinstance(result.exception, SystemExit)
        assert "no GPIO chip" in result.output and "setup_gpio_sim.sh" in result.output
    assert not (tmp_path / "t.json").exists()


def test_an_agent_that_does_not_fit_the_linux_board_fails_the_build_check(root, gpio):
    villa = root / "fixtures" / "agents" / "villa-concierge" / "agent.toml"
    result = invoke("run", "--target", "linux", "--agent", str(villa), "-c", "mở cửa phòng 101")
    assert result.exit_code == 1
    assert "build failed" in result.output and "aec" in result.output
    assert gpio.requests == [], "no line is requested for an agent that does not build"


def test_an_agent_needing_a_primitive_linux_lacks_is_refused_before_any_line(root, gpio):
    home = root / "fixtures" / "agents" / "home-voice" / "agent.toml"
    with pytest.raises(BoardCapabilityError) as raised:
        SimSession.load(home, target="linux")
    assert "sensor.read (TSK-S5-09)" in raised.value.why
    assert "audio.out (TSK-S5-08)" in raised.value.why
    assert gpio.requests == []
    result = invoke("run", "--target", "linux", "--agent", str(home), "-c", "bật đèn")
    assert result.exit_code == 1
    assert "TSK-S5-09" in result.output


def test_ui_on_linux_exits_two(driveway, gpio):
    for verb in (["run", "--ui"], ["mcp", "serve", "--ui"]):
        result = invoke(*verb, "--target", "linux", "--agent", str(driveway))
        assert result.exit_code == 2, result.output
        assert "drop --ui" in result.output
    assert gpio.requests == []


@pytest.mark.parametrize("verb", [["run", "-c", "x"], ["mcp", "serve"]])
def test_esp32s3_sessions_still_exit_two(driveway, verb):
    result = invoke(*verb, "--target", "esp32s3", "--agent", str(driveway))
    assert result.exit_code == 2, result.output
    assert "TSK-S4-01" in result.output


# --- record: a linux trace validates and replays to the same decisions -------------------


def test_a_trace_recorded_on_linux_validates_and_replays_the_same_on_sim_and_linux(
    driveway, gpio, tmp_path
):
    out = tmp_path / "linux.json"
    result = invoke(
        "record", "--target", "linux", "--agent", str(driveway), "--out", str(out),
        stdin="bật đèn hiên\n:set visitor_expected false\nmở cổng\nexit\n",
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    trace = json.loads(out.read_text(encoding="utf-8"))
    validate_trace(trace)
    assert trace["metadata"]["target"] == "linux"
    assert trace["metadata"]["board_id"] == "linux-rpi5"
    assert invoke("trace", "validate", str(out)).exit_code == 0

    sim = replay(out, target="sim", agent=driveway)
    on_linux = replay(out, target="linux", agent=driveway)
    assert sim.verdicts == on_linux.verdicts == sim.recorded_verdicts
    for pin in ("porch_light", "gate_relay"):
        assert sim.pin(pin).commands == on_linux.pin(pin).commands
    assert_matches_golden(sim, out)
    assert_matches_golden(on_linux, out)
    for target in ("sim", "linux"):
        replayed = invoke("replay", str(out), "--target", target, "--agent", str(driveway))
        assert replayed.exit_code == 0, replayed.output


def test_record_on_linux_defaults_to_the_reference_board(driveway, gpio, tmp_path):
    result = invoke(
        "record", "--target", "linux", "--agent", str(driveway),
        "--out", str(tmp_path), "-c", "bật đèn hiên",
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    (written,) = tmp_path.glob("*.json")
    assert json.loads(written.read_text("utf-8"))["metadata"]["board_id"] == "linux-rpi5"


# --- mcp serve: a tools/call drives the line through the gate ----------------------------


def test_an_mcp_tool_call_on_linux_goes_through_the_gate_to_the_line(driveway, gpio):
    session = SimSession.load(driveway, target="linux")
    try:

        async def main():
            async with Client(build_server(session)) as client:
                allowed = await client.call_tool("porch_light_on", {})
                # `call_source` of open_gate refuses an MCP client (driveway's gate).
                refused = await client.call_tool("open_gate", {})
                return allowed, refused

        allowed, refused = anyio.run(main)
        assert allowed.structured_content["status"] == "ALLOW"
        assert refused.structured_content["status"] == "BLOCK"
        assert line(gpio, "porch_light") is Value.ACTIVE
        assert ("gate_relay", 1) not in gpio.history
        validate_trace(session.trace())
        assert session.trace()["metadata"]["target"] == "linux"
    finally:
        session.close()
    assert line(gpio, "porch_light") is Value.INACTIVE


def test_an_unauthorised_command_on_a_linux_session_never_reaches_the_line(driveway, gpio):
    """Only c.do() moves a pin: the session's HAL takes its ledger's tokens and nothing else."""
    session = SimSession.load(driveway, target="linux")
    try:
        with pytest.raises(Exception, match="ledger|token|signature"):
            session.hal.digital_out("door_lock", "pulse", 1000, signature="forged")
        assert gpio.history == []
        result = anyio.run(session.call_tool, ToolCall("porch_light_on", {}, source="mcp"))
        assert result.status == "ALLOW"
    finally:
        session.close()


def test_mcp_serve_on_linux_without_a_chip_exits_one(driveway, monkeypatch, tmp_path):
    monkeypatch.setattr(linux, "CHIP_GLOB", str(tmp_path / "gpiochip*"))
    monkeypatch.setattr(linux, "_import_gpiod", lambda: FakeGpiod({}))
    result = invoke("mcp", "serve", "--target", "linux", "--agent", str(driveway))
    assert result.exit_code == 1, result.output
    assert "no GPIO chip" in result.output


def test_a_failure_after_the_lines_are_requested_releases_them(driveway, gpio, monkeypatch):
    import neuroedge.sim.session as session_module

    def broken(manifest):
        raise RuntimeError("mcp config broke")

    monkeypatch.setattr(session_module, "load_mcp_config", broken)
    with pytest.raises(RuntimeError, match="mcp config broke"):
        SimSession.load(driveway, target="linux")
    assert gpio.requests and all(request.released for request in gpio.requests)


@pytest.fixture(autouse=True)
def restore_signals():
    """Every linux session installs process-wide SIGTERM/SIGHUP handlers: put them back."""
    import signal

    saved = {name: signal.getsignal(getattr(signal, name)) for name in ("SIGTERM", "SIGHUP")}
    yield signal
    for name, handler in saved.items():
        signal.signal(getattr(signal, name), handler)


def test_a_linux_session_ends_on_sigterm_and_sighup_through_its_finally(
    driveway, gpio, restore_signals
):
    signal = restore_signals
    result = invoke("run", "--target", "linux", "--agent", str(driveway), "-c", "bật đèn hiên")
    assert result.exit_code == 0, result.output
    handlers = {name: signal.getsignal(getattr(signal, name)) for name in ("SIGTERM", "SIGHUP")}
    for name, handler in handlers.items():
        number = getattr(signal, name)
        assert callable(handler), f"{name} must not end the process without close()"
        with pytest.raises(SystemExit) as caught:
            handler(number, None)
        assert caught.value.code == 128 + number


def test_a_sim_session_leaves_the_signal_handlers_alone(root, restore_signals):
    signal = restore_signals
    before = signal.getsignal(signal.SIGTERM)
    agent = root / "fixtures" / "agents" / "driveway" / "agent.toml"
    assert invoke("run", "--agent", str(agent), "-c", "bật đèn hiên").exit_code == 0
    assert signal.getsignal(signal.SIGTERM) is before


def test_ctrl_c_while_run_c_waits_for_its_pulse_exits_130_and_drops_the_line(
    driveway, gpio, monkeypatch
):
    def interrupt(self):
        raise KeyboardInterrupt

    monkeypatch.setattr(TypedLinuxHAL, "settle", interrupt)
    result = invoke("run", "--target", "linux", "--agent", str(driveway), "-c", "mở cửa ngách")
    assert result.exit_code == 130, result.output
    assert ("door_lock", 1) in gpio.history, "the pulse started"
    assert line(gpio, "door_lock") == Value.INACTIVE, "Ctrl-C drops the line at once"
    assert all(request.released for request in gpio.requests)


def test_sensor_facts_without_sensor_read_in_requires_are_still_refused_on_linux(root, tmp_path):
    import shutil

    agent = tmp_path / "factory"
    shutil.copytree(root / "fixtures" / "agents" / "factory-monitor", agent)
    toml = agent / "agent.toml"
    toml.write_text(
        toml.read_text(encoding="utf-8").replace(
            '"sensor.read" = { sensors = ["temperature"] }\n', ""
        ),
        encoding="utf-8",
    )
    # The check itself, on the manifest: loading the copy would register its @actions
    # a second time in the process-wide registry.
    from neuroedge.engine.compiler import load_agent_manifest
    from neuroedge.sim.session import _require_linux_primitives, _sim_sensors

    manifest = load_agent_manifest(toml)
    assert "sensor.read" not in manifest.requires
    sim_table = tomllib.loads(toml.read_text(encoding="utf-8"))["sim"]
    _, sensor_facts = _sim_sensors(manifest, sim_table)
    with pytest.raises(BoardCapabilityError, match=r"sensor\.read \(TSK-S5-09\)"):
        _require_linux_primitives(manifest, sensor_facts)


def test_linux_sessions_warn_that_sim_facts_decide_for_real_lines(driveway, gpio):
    result = invoke("run", "--target", "linux", "--agent", str(driveway), stdin="exit\n")
    assert result.exit_code == 0, result.output
    assert "fixed values from [sim.facts]" in result.output
    on_sim = invoke("run", "--agent", str(driveway), stdin="exit\n")
    assert "[sim.facts]" not in on_sim.output


def test_a_line_left_on_is_reported_when_the_session_drops_it(driveway, gpio):
    result = invoke("run", "--target", "linux", "--agent", str(driveway), "-c", "bật đèn hiên")
    assert result.exit_code == 0, result.output
    assert "porch_light dropped inactive" in result.output
    assert line(gpio, "porch_light") == Value.INACTIVE


def test_a_second_signal_during_cleanup_is_ignored(driveway, gpio, restore_signals):
    signal = restore_signals
    assert (
        invoke("run", "--target", "linux", "--agent", str(driveway), "-c", "bật đèn hiên").exit_code
        == 0
    )
    handler = signal.getsignal(signal.SIGTERM)
    with pytest.raises(SystemExit):
        handler(signal.SIGTERM, None)
    assert signal.getsignal(signal.SIGTERM) is signal.SIG_IGN
    assert signal.getsignal(signal.SIGHUP) is signal.SIG_IGN


def test_a_voice_session_refuses_a_clock_other_than_the_sessions(root):
    from neuroedge.perception import VirtualClock, VoiceSession

    agent = root / "fixtures" / "agents" / "voice-door" / "agent.toml"
    session = SimSession.load(agent, clock=VirtualClock())
    with pytest.raises(ValueError, match="clock the session was loaded with"):
        VoiceSession(session, clock=VirtualClock())
