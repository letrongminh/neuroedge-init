"""
TSK-S3-23 — `sensor.read` and `display` on `sim`, end to end.

Scripted sensors feed gate facts and action bodies; frames are recorded with a
digest; replay feeds the recorded readings back (docs/spec/simulation_coverage.md).
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.engine.trace_sink import EventLog
from neuroedge.errors import ActionContractViolation, AgentManifestError, BoardCapabilityError
from neuroedge.hal import HardwareAbstractionLayer, display, sensor
from neuroedge.hal.sim import Frame, SimHAL
from neuroedge.sim import SimSession
from neuroedge.testing import TracePlayer
from neuroedge.testing.recorder import TraceRecorder

runner = CliRunner()


# --- SimHAL ----------------------------------------------------------------------------


def test_a_read_is_recorded_with_its_unit():
    events = EventLog()
    hal = SimHAL(events=events)
    hal.set_sensor("temperature", 24.5, unit="C")
    assert hal.sensor_read("temperature") == 24.5
    assert events.of_type("sensor_read") == [{"sensor": "temperature", "value": 24.5, "unit": "C"}]


def test_scripted_readings_come_back_in_order_then_stay():
    hal = SimHAL()
    hal.script_sensor("motion", [False, True])
    assert [hal.sensor_read("motion") for _ in range(3)] == [False, True, True]


def test_a_text_frame_is_recorded_with_its_digest():
    events = EventLog()
    hal = SimHAL(events=events)
    frame = hal.display("Xin chào")
    (event,) = events.of_type("display_frame")
    assert event == {
        "width": 320,
        "height": 240,
        "format": "text",
        "sha256": frame.sha256,
        "text": "Xin chào",
    }


def test_a_pixel_frame_must_match_its_size_and_format():
    hal = SimHAL()
    pixels = bytes(4 * 2 * 2)
    frame = hal.display(pixels, width=4, height=2, format="rgb565")
    assert frame.format == "rgb565" and len(frame.rgb888()) == 4 * 2 * 3
    with pytest.raises(BoardCapabilityError, match="needs 16 bytes"):
        hal.display(bytes(10), width=4, height=2, format="rgb565")
    with pytest.raises(BoardCapabilityError, match="unknown pixel format"):
        hal.display(pixels, width=4, height=2, format="yuv")


def test_rgb565_white_becomes_rgb888_white():
    frame = Frame.make(b"\xff\xff", 1, 1, "rgb565", where="t")
    assert frame.rgb888() == b"\xff\xff\xff"


def test_a_target_without_sensor_read_says_so():
    hal = HardwareAbstractionLayer(target="esp32s3")
    with pytest.raises(BoardCapabilityError, match="not implemented on target 'esp32s3'"):
        hal.sensor_read("temperature")
    with pytest.raises(BoardCapabilityError, match="display"):
        hal.display("x")


def test_sensor_and_display_calls_need_an_active_c_do():
    with pytest.raises(ActionContractViolation, match="inside an @action"):
        sensor.read("temperature")
    with pytest.raises(ActionContractViolation, match="inside an @action"):
        display.show("x")


# --- an agent that reads sensors and draws ------------------------------------------------


def _agent(tmp_path, sensors='temperature = { value = 24.5, unit = "C" }\ndoor_contact = true\n'):
    name = f"report_{abs(hash(str(tmp_path)))}"
    (tmp_path / "actions").mkdir()
    (tmp_path / "actions" / "report.py").write_text(
        "from neuroedge import action\n"
        "from neuroedge.hal import display, sensor\n\n"
        f'@action(name="{name}", requires="sensor.read:temperature", gate="panel")\n'
        "def report() -> None:\n"
        "    display.show(f\"Nhiệt độ: {sensor.read('temperature')} C\")\n",
        encoding="utf-8",
    )
    (tmp_path / "panel.yaml").write_text(
        "schema: neuroedge.gate/v1\nname: panel\nversion: 1.0.0\n"
        "evaluate:\n  door_closed:\n    type: bool\n    instructions: door closed\n"
        "allow_when:\n  door_closed: true\n"
        "on_block:\n  action: deny\n"
        "budget:\n  p95_latency_ms: 100\n  fail: closed\n",
        encoding="utf-8",
    )
    (tmp_path / "commands.toml").write_text(
        f'[grammar]\nversion = 1\n\n[[command]]\nintent = "report"\npatterns = ["báo nhiệt độ"]\naction = "{name}"\n',
        encoding="utf-8",
    )
    (tmp_path / "agent.toml").write_text(
        '[agent]\nname = "panel-test"\nversion = "0.1.0"\n\n'
        '[requires]\n"sensor.read" = { sensors = ["temperature", "door_contact"] }\n"display" = {}\n\n'
        '[gates]\npanel = "panel.yaml"\n\n'
        "[sim.sensors]\n" + sensors + "\n"
        '[sim.sensor_facts]\ndoor_closed = { sensor = "door_contact" }\n',
        encoding="utf-8",
    )
    return tmp_path / "agent.toml"


async def test_a_sensor_fact_and_an_action_read_flow_into_the_trace(tmp_path):
    session = SimSession.load(_agent(tmp_path))
    turn = await session.handle("báo nhiệt độ")
    assert turn.allowed
    assert session.hal.frames[-1].text == "Nhiệt độ: 24.5 C"
    reads = session.events.of_type("sensor_read")
    assert {"sensor": "door_contact", "value": True, "use": "fact"} in reads
    assert {"sensor": "temperature", "value": 24.5, "unit": "C"} in reads
    assert session.events.of_type("display_frame")[-1]["text"] == "Nhiệt độ: 24.5 C"


async def test_a_sensor_changes_the_verdict(tmp_path):
    session = SimSession.load(_agent(tmp_path))
    session.hal.set_sensor("door_contact", False)
    turn = await session.handle("báo nhiệt độ")
    assert turn.result.blocked
    assert turn.result.gate.failed_criterion == "door_closed"
    assert session.hal.frames == []


async def test_replay_feeds_the_recorded_reading_back(tmp_path):
    agent = _agent(tmp_path)
    recorder = TraceRecorder()
    session = SimSession.load(agent, events=recorder)
    session.hal.set_sensor("temperature", 31.0, unit="C")
    await session.handle("báo nhiệt độ")

    result = await TracePlayer(recorder.to_trace(), agent=agent).replay()
    assert result.verdicts == ["ALLOW"]
    # The manifest says 24.5; the recording said 31.0, and replay must use the recording.
    assert result.hal.frames[-1].text == "Nhiệt độ: 31.0 C"


def test_comparisons_in_sensor_facts(tmp_path):
    from neuroedge.sim.session import SensorFact

    assert SensorFact("t", gte=30).evaluate(31) is True
    assert SensorFact("t", lte=30).evaluate(31) is False
    assert SensorFact("d", equals="open").evaluate("open") is True
    assert SensorFact("d").evaluate(0.5) == 0.5


def test_a_malformed_sensor_table_is_a_manifest_error(tmp_path):
    with pytest.raises(AgentManifestError, match="value"):
        SimSession.load(_agent(tmp_path, sensors='temperature = { unit = "C" }\n'))


def test_a_sensor_the_board_lacks_is_refused(tmp_path):
    with pytest.raises(BoardCapabilityError, match="co2"):
        SimSession.load(_agent(tmp_path, sensors="co2 = 400\n"))


# --- REPL ------------------------------------------------------------------------------


def test_the_repl_sets_sensors_and_shows_the_screen(tmp_path):
    agent = _agent(tmp_path)
    stdin = ":sensors\n:sensor temperature 30\nbáo nhiệt độ\n:screen\n:sensor door_contact false\nbáo nhiệt độ\nexit\n"
    result = runner.invoke(app, ["run", "--agent", str(agent)], input=stdin)
    assert result.exit_code == 0, result.output
    assert "24.5 C" in result.output  # :sensors
    assert "temperature = 30" in result.output
    assert "Nhiệt độ: 30 C" in result.output  # the frame, after the verdict and again on :screen
    assert result.output.count("Nhiệt độ: 30 C") == 2
    assert "criterion: door_closed" in result.output
