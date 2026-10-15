"""
The virtual board `sim-virtual` (docs/spec/virtual_parts.md §3.1, Q-84 phase A, TSK-I2d-29).

An agent that needs a pin or a sensor `sim-default` lacks runs on `sim` without a board file:
the board is built from its `[requires]`, labelled `risk=virtual_board`, recorded by digest and
refused off `sim`. Each test names the test case of the specification it implements.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.engine.compiler import build
from neuroedge.errors import BoardCapabilityError, NeuroEdgeError
from neuroedge.hal.board import available_boards, load_board_by_id
from neuroedge.hal.virtual_board import (
    DEFAULT_ENVELOPE,
    VirtualBoard,
    board_digest,
    canonical,
    virtual_board_document,
)
from neuroedge.paths import boards_dir, repo_root
from neuroedge.sim import SimSession
from neuroedge.templates import scaffold
from neuroedge.testing import TracePlayer
from neuroedge.testing.recorder import TraceRecorder
from neuroedge.trace import validate_trace

runner = CliRunner()

GATE = """schema:  neuroedge.gate/v1
name:    {gate}
version: 1.0.0
evaluate:
  command_recognized:
    type: bool
    instructions: "Câu lệnh khớp ngữ pháp"
allow_when:
  command_recognized: true
on_block:
  action:  deny
  message: "Không làm."
budget:
  p95_latency_ms: 150
  fail:           closed
"""


def make_agent(root: Path, name: str, *, sensors=("ph",), board_line: bool = True) -> Path:
    """An agent with a `heater` pin and a pH probe, neither of which sim-default has."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "actions").mkdir(exist_ok=True)
    (root / "gates").mkdir(exist_ok=True)
    sensor_list = ", ".join(f'"{s}"' for s in sensors)
    (root / "agent.toml").write_text(
        f'[agent]\nname = "{name.replace("_", "-")}"\nversion = "0.1.0"\n\n'
        f'[requires]\n"digital.out" = {{ pins = ["heater"] }}\n'
        f'"sensor.read" = {{ sensors = [{sensor_list}] }}\n\n'
        f'[gates]\n{name} = "gates/{name}@1.0.0.yaml"\n\n'
        '[targets]\nsupported = ["sim", "linux", "esp32s3"]\n'
        + ('\n[sim]\nboard = "sim-virtual"\n' if board_line else ""),
        encoding="utf-8",
    )
    (root / "actions" / f"{name}.py").write_text(
        "from neuroedge import action, digital\n\n\n"
        f'@action(name="{name}", requires="digital.out:heater", gate="{name}")\n'
        f"def {name}() -> None:\n"
        '    """Turn the heater on."""\n'
        '    digital.out("heater").on()\n',
        encoding="utf-8",
    )
    (root / "gates" / f"{name}@1.0.0.yaml").write_text(GATE.format(gate=name), encoding="utf-8")
    (root / "commands.toml").write_text(
        "[grammar]\nversion = 1\nthreshold = 0.80\n\n"
        f'[[command]]\nintent = "{name}"\npatterns = ["bật sưởi"]\n'
        f'facts = {{ command_recognized = true }}\ntool = "{name}"\n',
        encoding="utf-8",
    )
    return root / "agent.toml"


@pytest.fixture(autouse=True)
def own_actions():
    """These agents register their @actions process-wide; put the registry back after each test."""
    import sys

    from neuroedge.actions import REGISTRY

    saved, modules = dict(REGISTRY), set(sys.modules)
    REGISTRY.pop("operate_hardware", None)  # `neuroedge new` defines it again at a new path
    yield
    REGISTRY.clear()
    REGISTRY.update(saved)
    for module in set(sys.modules) - modules:
        if module.startswith("neuroedge_agent_"):
            del sys.modules[module]


@pytest.fixture(scope="module")
def agent(tmp_path_factory) -> Path:
    return make_agent(tmp_path_factory.mktemp("vb"), "vb_heat")


# --- TC-VB-01: opt-in, the default is unchanged --------------------------------------------


def test_the_board_comes_from_the_flag_or_agent_toml_and_the_default_is_unchanged(agent, tmp_path):
    session = SimSession.load(agent)  # [sim] board = "sim-virtual"
    assert session.events.metadata["board_id"] == "sim-virtual"
    session.hal.close()
    plain = make_agent(tmp_path / "plain", "vb_plain", board_line=False)
    with pytest.raises(NeuroEdgeError):  # sim-default has no `heater`: nothing changed
        SimSession.load(plain)
    flagged = SimSession.load(plain, board_id="sim-virtual")
    assert flagged.events.metadata["board_id"] == "sim-virtual"
    flagged.hal.close()


@pytest.mark.parametrize(
    "trace", ["happy-path.json", "network_offline.json", "unverified_attempt.json"]
)
def test_the_canonical_traces_replay_unchanged_on_their_default_board(trace):
    """VP-NF-02: nothing that ran on sim-default before the virtual board moves."""
    from neuroedge.testing import replay

    result = replay(repo_root() / "fixtures" / "traces" / trace)
    assert result.verdicts == result.recorded_verdicts


# --- TC-VB-02: exactly what the agent declares is added -------------------------------------


def test_exactly_what_the_agent_needs_is_added_and_nothing_is_removed():
    requires = {
        "digital.out": {"pins": ["heater", "door_lock"]},
        "sensor.read": {"sensors": ["ph", "temperature"]},
        "digital.in": {"pins": ["float_switch"]},
    }
    document, added = virtual_board_document(requires)
    assert added == {
        "digital.out": ["heater"],
        "digital.in": ["float_switch"],
        "sensor.read": ["ph"],
    }
    base = load_board_by_id("sim-rpi5").capabilities  # digital.in is only on sim-rpi5
    capabilities = document["capabilities"]
    assert set(base) <= set(capabilities)
    assert set(base["digital_out"]["pins"]) <= set(capabilities["digital_out"]["pins"])
    assert capabilities["digital_out"]["pins"][-1] == "heater"
    from neuroedge.hal.board import validate_board_document

    validate_board_document(document, "test")


def test_an_added_motor_and_servo_copy_the_reference_channels_with_their_enable_pins():
    document, added = virtual_board_document(
        {"motion": {"channels": ["arm", "pan"]}, "analog.in": {"channels": ["knob"]}},
        servos={"pan"},
    )
    motion = document["capabilities"]["motion"]
    assert any(c["name"] == "arm" and c["enable_pin"] == "arm_en" for c in motion["motor"])
    assert any(c["name"] == "pan" and c["enable_pin"] == "pan_en" for c in motion["servo"])
    assert {"arm", "pan"} <= set(motion["envelope"])
    assert any(c["name"] == "knob" for c in document["capabilities"]["analog_in"]["channels"])
    assert added == {"analog.in": ["knob"], "motion": ["arm", "pan"]}


# --- TC-VB-03: an added pin has the default envelope -------------------------------------


def test_an_added_pin_without_a_part_gets_the_default_envelope(agent):
    board = VirtualBoard(_manifest(agent))
    assert board.document["capabilities"]["digital_out"]["envelope"]["heater"] == DEFAULT_ENVELOPE
    from .hand_clock import HandClock

    clock = HandClock()
    recorder = TraceRecorder(clock=clock)
    session = SimSession.load(agent, events=recorder, clock=clock)
    try:
        assert asyncio.run(session.handle("bật sưởi")).allowed
        clock.advance(59_999)
        session.hal.run_due()
        assert session.hal.pin("heater").commands == [("on", 0)]
        clock.advance(1)
        session.hal.run_due()  # held on: the pin turns itself off at max_continuous_ms
        off = [e for e in recorder.to_trace()["events"] if e["type"] == "actuator_command"][-1]
        assert off["data"]["operation"] == "off" and off["data"]["cause"] == "max_continuous_ms"
    finally:
        session.hal.close()


# --- TC-VB-04: refused off sim; graduation checks the real board ---------------------------


@pytest.mark.parametrize("target", ["linux", "esp32s3"])
def test_the_virtual_board_is_refused_off_sim(agent, target):
    with pytest.raises(BoardCapabilityError) as refused:
        build(agent, target=target, board_id="sim-virtual")
    assert "sim-virtual" in refused.value.where and target in refused.value.where
    result = runner.invoke(
        app, ["run", "--agent", str(agent), "--target", "linux", "--board", "sim-virtual"]
    )
    assert result.exit_code != 0


def test_building_for_the_chip_names_the_pins_box3_lacks(agent):
    with pytest.raises(NeuroEdgeError) as failed:
        build(agent, target="esp32s3")
    assert "heater" in str(getattr(failed.value, "problems", failed.value))


# --- TC-VB-05: the label is printed, recorded and shown -----------------------------------


def test_a_session_on_the_virtual_board_is_labelled(agent):
    recorder = TraceRecorder()
    session = SimSession.load(agent, events=recorder)
    try:
        assert session.virtual_board.startup_line() == (
            "risk=virtual_board added: digital.out heater · sensor.read ph"
        )
        asyncio.run(session.handle("bật sưởi"))
    finally:
        session.hal.close()
    trace = recorder.to_trace()
    assert trace["metadata"]["risks"] == ["virtual_board"]
    assert trace["metadata"]["virtual_board_digest"].startswith("sha256:")
    validate_trace(trace)
    result = runner.invoke(app, ["build", "--agent", str(agent), "--target", "sim"])
    assert result.exit_code == 0, result.output
    assert "risk=virtual_board" in result.output


def test_the_page_shows_the_label(agent):
    from neuroedge.sim.ui import SessionServer

    session = SimSession.load(agent)
    server = SessionServer(session, port=0).start()
    try:
        import urllib.request

        with urllib.request.urlopen(server.url, timeout=5) as response:
            body = response.read().decode("utf-8")
    finally:
        server.stop()
    assert '"virtual_board"' in body and "Bảng mạch ảo" in body


# --- TC-VB-06: replay rebuilds the board and checks its digest ----------------------------


def test_a_recording_replays_on_the_same_board_and_is_refused_on_another(tmp_path):
    agent = make_agent(tmp_path / "replayed", "vb_replay")
    recorder = TraceRecorder()
    session = SimSession.load(agent, events=recorder)
    asyncio.run(session.handle("bật sưởi"))
    session.hal.close()
    trace = recorder.to_trace()
    result = asyncio.run(TracePlayer(trace, agent=agent).replay())
    assert result.verdicts == result.recorded_verdicts == ["ALLOW"]
    text = agent.read_text(encoding="utf-8").replace('sensors = ["ph"]', 'sensors = ["ph", "orp"]')
    agent.write_text(text, encoding="utf-8")
    with pytest.raises(NeuroEdgeError) as refused:
        asyncio.run(TracePlayer(trace, agent=agent).replay())
    assert trace["metadata"]["virtual_board_digest"] in str(refused.value.why)


# --- TC-VB-07: never a profile file ---------------------------------------------------------


def test_the_virtual_board_is_never_a_profile():
    assert "sim-virtual" not in {board.id for board in available_boards()}
    assert not (boards_dir() / "sim-virtual.toml").exists()
    with pytest.raises(BoardCapabilityError) as refused:
        load_board_by_id("sim-virtual")
    assert "VP-VB-01" in refused.value.why


# --- TC-VB-08: deterministic -----------------------------------------------------------------


def test_the_same_agent_gives_the_same_board_whatever_the_order():
    one, _ = virtual_board_document(
        {"digital.out": {"pins": ["b", "a"]}, "sensor.read": {"sensors": ["y", "x"]}}
    )
    two, _ = virtual_board_document(
        {"sensor.read": {"sensors": ["x", "y"]}, "digital.out": {"pins": ["a", "b"]}}
    )
    assert canonical(one) == canonical(two)
    assert board_digest(one) == board_digest(two)
    json.loads(canonical(one))


# --- TC-VB-09: `neuroedge new` --------------------------------------------------------------


def test_new_keeps_sim_default_and_takes_the_virtual_board_on_request(tmp_path, monkeypatch):
    import tomllib

    scaffold("plain_one", parent=tmp_path)
    assert "sim" not in tomllib.loads(
        (tmp_path / "plain_one" / "agent.toml").read_text(encoding="utf-8")
    ) or (
        "board"
        not in tomllib.loads((tmp_path / "plain_one" / "agent.toml").read_text(encoding="utf-8"))[
            "sim"
        ]
    )
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["new", "free_one", "--board", "sim-virtual"])
    assert result.exit_code == 0, result.output
    assert "risk=virtual_board" in result.output
    assert "--board sim-virtual" in result.output
    text = (tmp_path / "free_one" / "agent.toml").read_text(encoding="utf-8")
    assert tomllib.loads(text)["sim"]["board"] == "sim-virtual"
    session = SimSession.load(tmp_path / "free_one" / "agent.toml")
    try:
        assert session.events.metadata["board_id"] == "sim-virtual"
    finally:
        session.hal.close()
    with pytest.raises(NeuroEdgeError):
        scaffold("other_one", parent=tmp_path, board="sim-rpi5")


# --- TC-VNF-01: nothing of CONTRIBUTING §3 changes ----------------------------------------

# The files of CONTRIBUTING.md §3 as they were before TSK-I2d-29 (main at c41820b). A phase of
# virtual_parts.md must not change them; an RFC that does updates this table and names itself.
RFC_FILES = {
    "schemas/board.v1.json": "f298f4f4a398ac908ce7791cd362850ecbd9f9274dd612fb60de98a7ea0dda18",
    "schemas/error-codes.v1.json": "3546112eeff7bb31b5e875cad110a372ec91bf504fa50537144f96f8b6a3b546",
    "schemas/error.v1.json": "ba096fcb509d8184cc3f42c4245b7f661249bc848d138dbcc48243afaa889232",
    "schemas/gate.v1.json": "5c72bb8b76cf02f674e73a482793bb7628325304b88566c6b8343967d8d7ee4e",
    "schemas/tool-call.v1.json": "f9bf5322d018809ef64ff7eeb1dd39d114d58f9cf40d2271254d4466c0466f38",
    "schemas/tool-result.v1.json": "e2d44b62d767888079102c77b86c3e4890ce0dd4e68708eb92c06eb9a13d57d4",
    "schemas/trace.v1.json": "5be583e56e594de7be2c84631a790883728da3862356b338064d7b80a7062c78",
    "python/neuroedge/engine/gate_resolver.py": "edd602bfa8c358486411fe5896e4d0d1c08b5234d8ff0ad03195656096a60e53",
    "python/neuroedge/engine/constraints.py": "69dae5f8f40b0f0c83607d7dc8268b0d13ce467d43781c78ae6a39413c5ece27",
    "python/neuroedge/engine/binary_tree.py": "090701a1141347f30c35e459680fab39a27f29a3ae2e450b1320336ef252674b",
    "fixtures/traces/happy-path.json": "959474fdcdd09db15150a6fad60096851832f436c67794a7c9a1f2434fa0e94a",
    "fixtures/traces/network_offline.json": "c921b4fbaa290c04d077b895f6bafd2bc6b03bf6d27879829543ddfbaa3abdb3",
    "fixtures/traces/unverified_attempt.json": "649c8230ead8f169b24a184193501eb45ef5bb9f0eed603bf91abc73592fdd31",
}


def test_the_rfc_files_are_untouched_by_the_virtual_parts_phases():
    import hashlib

    root = repo_root()
    for path, digest in RFC_FILES.items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, (
            f"{path} changed: an RFC file (CONTRIBUTING.md §3); update RFC_FILES only with its RFC"
        )


def _manifest(agent: Path):
    from neuroedge.engine.compiler import load_agent_manifest

    return load_agent_manifest(agent)
