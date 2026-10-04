"""
The five hardware kits (TSK-I2b-01, TSK-I2b-02): `villa-concierge`, `home-voice`, `factory-monitor`,
`gate-camera` (vision.in) and `blinds` (motion.*).

A kit is a template plus what it takes to build the device: a BOM, a wiring diagram per board, a
locked gate, golden traces and a guide, in `docs/user/kit-*.md`. The template itself — `new`, its
tests on `sim`, the wheel — is `test_cli_new.py` and `scripts/wheel_smoke.sh`; this file holds what
makes it a kit, so that the documents cannot drift from the boards and the agents:

* every `line:<pin>` and `sensor:<name>` in a wiring diagram exists in that board's profile, and
  every pin and sensor the agent needs is drawn;
* the kit's gates are in `digests.lock`;
* the golden traces are what the sample agent records (`scripts/gen_kit_traces.py --check`), hold the
  decisions they are named for, replay alike on every reference board, and never move a pin a gate
  blocked. On `linux` a fake gpiod stands in for the lines; the kernel's are `tests_linux/test_kit_*.py`.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

import neuroedge.hal.linux as linux
from neuroedge.cli.main import EXTENSION_TRACES, _trace_lacks
from neuroedge.hal.board import load_board_by_id
from neuroedge.testing import assert_matches_golden, replay
from neuroedge.trace import validate_trace

from .test_hal_linux import FakeGpiod, Value

KITS = {
    "villa-concierge": "kit-khoa-cua-villa.md",
    "home-voice": "kit-tro-ly-giong-noi.md",
    "factory-monitor": "kit-giam-sat-nha-may.md",
    "gate-camera": "kit-camera-cong.md",
    "blinds": "kit-rem-cua.md",
}
BOARDS = ("linux-rpi5", "esp32s3-box-3")
# A kit draws one diagram per reference board it builds for: the camera and motion kits only for the Pi.
KIT_BOARDS = dict.fromkeys(KITS, BOARDS) | {
    "gate-camera": ("linux-rpi5",),
    "blinds": ("linux-rpi5",),
}
WIRED = [(kit, board) for kit in KITS for board in KIT_BOARDS[kit]]
# The boards each kit's golden traces replay on: those that declare what the traces use.
REPLAY_BOARDS = {
    "gate-camera": ("sim-rpi5", "linux-rpi5"),
    "blinds": ("sim-rpi5", "linux-rpi5"),
}
SIM_DEFAULT_KITS = ("villa-concierge", "home-voice", "factory-monitor")
# The gates each kit's `agent.toml` names, as paths under the repository.
LOCKED_GATES = {
    "villa-concierge": ["gates/unlock_door@1.2.0.yaml"],
    "home-voice": [
        "fixtures/agents/home-voice/gates/light_on@1.0.0.yaml",
        "fixtures/agents/home-voice/gates/light_off@1.0.0.yaml",
    ],
    "factory-monitor": [
        f"fixtures/agents/factory-monitor/gates/{name}@1.0.0.yaml"
        for name in ("vent_on", "vent_off", "alarm_on", "alarm_off")
    ],
    "gate-camera": [
        f"fixtures/agents/gate-camera/gates/{name}@1.0.0.yaml"
        for name in ("stranger_light", "stranger_lock")
    ],
    "blinds": [
        f"fixtures/agents/blinds/gates/{name}@1.0.0.yaml"
        for name in ("blinds_open", "blinds_close")
    ],
}
# What each golden trace holds: gate verdicts in order, then every pin command (pin, operation).
ALLOW, BLOCK = "ALLOW", "BLOCK"
OUTCOMES = {
    "villa-concierge-allow": ([ALLOW], [("door_lock", "pulse")]),
    "villa-concierge-block": ([BLOCK] * 3, []),
    "home-voice-allow": ([ALLOW, ALLOW], [("porch_light", "on"), ("porch_light", "off")]),
    "home-voice-block": ([ALLOW, BLOCK, BLOCK], [("porch_light", "on")]),
    "factory-monitor-allow": (
        [ALLOW] * 4,
        [
            ("gate_relay", "on"),
            ("porch_light", "on"),
            ("gate_relay", "off"),
            ("porch_light", "off"),
        ],
    ),
    "factory-monitor-block": (
        [ALLOW, ALLOW, BLOCK, BLOCK, BLOCK, BLOCK],
        [("gate_relay", "on"), ("porch_light", "on")],
    ),
    "gate-camera-allow": (
        [ALLOW, ALLOW],
        [("porch_light", "on"), ("gate_relay", "pulse")],
    ),
    "gate-camera-block": ([BLOCK] * 5, []),
    "blinds-allow": ([ALLOW, ALLOW], []),
    "blinds-block": ([BLOCK, BLOCK, BLOCK, ALLOW, ALLOW], []),
}
WIRING = re.compile(r"<!-- wiring: (\S+) -->\n```mermaid\n(.*?)```", re.S)


def agent_manifest(root: Path, kit: str) -> dict:
    return tomllib.loads((root / "fixtures" / "agents" / kit / "agent.toml").read_text("utf-8"))


def board_profile(root: Path, board: str) -> dict:
    return tomllib.loads((root / "boards" / f"{board}.toml").read_text("utf-8"))["capabilities"]


def page(root: Path, kit: str) -> str:
    return (root / "docs" / "user" / KITS[kit]).read_text("utf-8")


def diagrams(root: Path, kit: str) -> dict[str, str]:
    return dict(WIRING.findall(page(root, kit)))


# --- documents: the wiring cannot drift from the boards ----------------------------------------


@pytest.mark.parametrize("kit", KITS)
def test_a_kit_page_draws_one_diagram_for_each_reference_board_it_builds_for(root, kit):
    assert sorted(diagrams(root, kit)) == sorted(KIT_BOARDS[kit])


@pytest.mark.parametrize(("kit", "board"), WIRED)
def test_every_name_in_a_wiring_diagram_exists_in_that_board_profile(root, kit, board):
    capabilities = board_profile(root, board)
    pins = {
        *capabilities["digital_out"]["pins"],
        *capabilities.get("digital_in", {}).get("pins", []),
    }
    sensors = set(capabilities["sensor_read"]["sensors"])
    channels = {
        channel["name"]
        for kind in ("motor", "servo")
        for channel in capabilities.get("motion", {}).get(kind, [])
    }
    modes = {
        f"{mode['width']}x{mode['height']}"
        for mode in capabilities.get("vision_in", {}).get("modes", [])
    }
    diagram = diagrams(root, kit)[board]
    drawn_pins = set(re.findall(r"line:([a-z0-9_]+)", diagram))
    drawn_sensors = set(re.findall(r"sensor:([a-z0-9_]+)", diagram))
    drawn_channels = set(re.findall(r"motion:([a-z0-9_]+)", diagram))
    drawn_modes = set(re.findall(r"camera:([0-9]+x[0-9]+)", diagram))
    drawn_analog = set(re.findall(r"analog:([a-z0-9_]+)", diagram))
    analog = {c["name"] for c in capabilities.get("analog_in", {}).get("channels", [])}
    assert drawn_pins or drawn_channels, f"{kit} on {board}: the diagram names no line"
    assert drawn_pins <= pins, f"{kit} on {board}: {sorted(drawn_pins - pins)} is not a pin"
    assert drawn_sensors <= sensors, (
        f"{kit} on {board}: {sorted(drawn_sensors - sensors)} is not a sensor"
    )
    assert drawn_channels <= channels, (
        f"{kit} on {board}: {sorted(drawn_channels - channels)} is not a motion channel"
    )
    assert drawn_modes <= modes, f"{kit} on {board}: {sorted(drawn_modes - modes)} is not a mode"
    assert drawn_analog <= analog, (
        f"{kit} on {board}: {sorted(drawn_analog - analog)} is no channel"
    )


@pytest.mark.parametrize(("kit", "board"), WIRED)
def test_a_wiring_diagram_draws_every_name_the_agent_needs(root, kit, board):
    requires = agent_manifest(root, kit)["requires"]
    diagram = diagrams(root, kit)[board]
    for pin in requires.get("digital.out", {}).get("pins", []):
        assert f"line:{pin}" in diagram, f"{kit} on {board}: {pin} is not wired"
    for pin in requires.get("digital.in", {}).get("pins", []):
        assert f"line:{pin}" in diagram, f"{kit} on {board}: input {pin} is not wired"
    for channel in requires.get("analog.in", {}).get("channels", []):
        assert f"analog:{channel}" in diagram, f"{kit} on {board}: {channel} is not wired"
    for sensor in requires.get("sensor.read", {}).get("sensors", []):
        assert f"sensor:{sensor}" in diagram, f"{kit} on {board}: {sensor} is not wired"
    for channel in requires.get("motion", {}).get("channels", []):
        assert f"motion:{channel}" in diagram, f"{kit} on {board}: {channel} is not wired"
        enable = next(
            c["enable_pin"]
            for kind in ("motor", "servo")
            for c in board_profile(root, board)["motion"][kind]
            if c["name"] == channel
        )
        assert f"line:{enable}" in diagram, (
            f"{kit} on {board}: the enable line {enable} is not wired"
        )
    if "vision.in" in requires:
        assert "camera:" in diagram, f"{kit} on {board}: the camera is not wired"


@pytest.mark.parametrize("kit", KITS)
def test_a_pin_an_agent_needs_is_a_pin_of_every_board_that_it_builds_for(root, kit):
    # The agent claims these targets; its pins must exist where it claims to run.
    manifest = agent_manifest(root, kit)
    boards = {"linux": "linux-rpi5", "esp32s3": "esp32s3-box-3"}
    for target in manifest["targets"]["supported"]:
        if target in boards:
            profile = board_profile(root, boards[target])
            for pin in manifest["requires"].get("digital.out", {}).get("pins", []):
                assert pin in profile["digital_out"]["pins"], (kit, target, pin)


@pytest.mark.parametrize("kit", KITS)
def test_a_kit_page_says_what_was_not_checked_on_hardware_and_invents_no_part(root, kit):
    text = page(root, kit)
    assert "chưa kiểm trên phần cứng thật" in text
    assert "## BOM" in text and "## Sơ đồ đấu dây" in text and "## Từ hộp tới chạy thật" in text
    assert "Không có mã hàng, giá hay nhà bán" in text
    assert not re.search(r"\$\s?\d|\d\s?(USD|VND|đồng)\b|₫", text), "a BOM carries no price"
    guide = (root / "docs" / "user" / "kit-phan-cung.md").read_text("utf-8")
    assert KITS[kit] in guide
    assert "`--template`" in guide and f"`{kit}`" in guide


def test_the_user_map_lists_the_kits(root):
    readme = (root / "docs" / "user" / "README.md").read_text("utf-8")
    assert "kit-phan-cung.md" in readme


def test_the_factory_kit_names_its_actuators_as_the_proposal_does(root):
    # Proposal §1.6 item 3: an exhaust valve or an alarm siren. The wording is one fact, said the
    # same way in the agent, the template and the kit page.
    text = page(root, "factory-monitor")
    assert "van xả" in text and "còi báo động" in text
    for path in (
        root / "fixtures" / "agents" / "factory-monitor" / "agent.toml",
        root / "fixtures" / "agents" / "factory-monitor" / "actions" / "plant.py",
        root / "python" / "neuroedge" / "templates" / "factory-monitor" / "README.md.tmpl",
    ):
        body = path.read_text("utf-8")
        assert "beacon" not in body and "đèn báo động" not in body, path.name
        assert "siren" in body or "còi báo động" in body, path.name


# --- the wheel and the lock ---------------------------------------------------------------------


@pytest.mark.parametrize("kit", KITS)
def test_every_kit_runs_in_the_wheel_smoke(root, kit):
    script = (root / "scripts" / "wheel_smoke.sh").read_text("utf-8")
    assert f"--template {kit}" in script
    assert f"fixtures/agents/{kit}/agent.toml" in script
    assert "fixtures/traces/kits/" in script


@pytest.mark.parametrize("kit", KITS)
def test_the_gates_of_a_kit_are_locked(root, kit):
    locked = yaml.safe_load((root / "digests.lock").read_text("utf-8"))["files"]
    for gate in LOCKED_GATES[kit]:
        assert (root / gate).is_file(), gate
        assert gate in locked, f"{gate} is not in digests.lock"
    named = agent_manifest(root, kit)["gates"].values()
    assert len(named) == len(LOCKED_GATES[kit])


def test_a_kit_with_a_gate_of_its_own_names_the_file_its_manifest_loads(root):
    # The lock holds the file the agent loads, not a copy of it.
    for kit in ("home-voice", "factory-monitor"):
        for key, reference in agent_manifest(root, kit)["gates"].items():
            assert f"fixtures/agents/{kit}/{reference}" in LOCKED_GATES[kit], (kit, key)
    reference = agent_manifest(root, "villa-concierge")["gates"]["unlock_door"]
    assert reference == "neuroedge://gates/unlock_door@1.2.0"


# --- golden traces -------------------------------------------------------------------------------


def corpus(root: Path) -> list[Path]:
    return sorted((root / "fixtures" / "traces" / "kits").glob("*.json"))


def events(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["events"]


def test_verify_knows_the_kits_corpus():
    assert "kits" in EXTENSION_TRACES


def test_the_corpus_is_closed_both_ways(root):
    assert [path.stem for path in corpus(root)] == sorted(OUTCOMES)


def test_the_corpus_is_what_the_sample_agents_record(root):
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "gen_kit_traces.py"), "--check"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr


def test_the_corpus_validates(root):
    for path in corpus(root):
        validate_trace(json.loads(path.read_text(encoding="utf-8")))


def test_every_trace_holds_the_decisions_and_pin_commands_it_is_named_for(root):
    for path in corpus(root):
        verdicts = [
            e["data"]["verdict"] for e in events(path) if e["type"] == "gate_evaluation_result"
        ]
        commands = [
            (e["data"]["pin"], e["data"]["operation"])
            for e in events(path)
            if e["type"] == "actuator_command"
        ]
        assert (verdicts, commands) == OUTCOMES[path.stem], path.name


def test_a_blocked_decision_never_reaches_a_pin(root):
    # One pin command per ALLOW at most, and none at all for a BLOCK: the traces say it in order.
    for path in corpus(root):
        steps = [
            e["type"]
            for e in events(path)
            if e["type"] in {"gate_evaluation_result", "actuator_command"}
        ]
        verdicts = [
            e["data"]["verdict"] for e in events(path) if e["type"] == "gate_evaluation_result"
        ]
        assert steps.count("actuator_command") <= verdicts.count(ALLOW), path.name
        for event in events(path):
            if event["type"] == "gate_evaluation_result" and event["data"]["verdict"] == BLOCK:
                assert event["data"].get("reason"), path.name


def test_the_block_traces_explain_every_refusal(root):
    expected = {
        "villa-concierge-block": [
            ("condition_not_met", "room_matches"),
            ("criterion_unavailable", "room_matches"),
            ("condition_not_met", "risk_level"),
        ],
        "home-voice-block": [
            ("condition_not_met", "room_empty"),
            ("criterion_unavailable", "room_empty"),
        ],
        "factory-monitor-block": [
            ("condition_not_met", "heat_level"),
            ("condition_not_met", "heat_level"),
            ("condition_not_met", "heat_level"),
            ("criterion_unavailable", "heat_level"),
        ],
    }
    for name, reasons in expected.items():
        blocked = [
            (e["data"]["reason"], e["data"]["failed_criterion"])
            for e in events(corpus_path(name))
            if e["type"] == "gate_evaluation_result" and e["data"]["verdict"] == BLOCK
        ]
        assert blocked == reasons, name


def corpus_path(name: str) -> Path:
    from neuroedge.paths import repo_root

    return repo_root() / "fixtures" / "traces" / "kits" / f"{name}.json"


@pytest.fixture
def gpio(monkeypatch, tmp_path):
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    names = ["door_lock", "porch_light", "gate_relay", "door_contact_raw", "limit_switch"]
    fake = FakeGpiod({str(chip): names})
    monkeypatch.setattr(linux, "CHIP_GLOB", str(tmp_path / "gpiochip*"))
    monkeypatch.setattr(linux, "_import_gpiod", lambda: fake)
    return fake


@pytest.mark.parametrize(
    ("target", "board"),
    [("sim", "sim-default"), ("sim", "sim-rpi5"), ("linux", "linux-rpi5")],
)
def test_the_corpus_replays_to_what_it_recorded_on_every_board_that_declares_its_primitives(
    root, gpio, target, board
):
    for path in corpus(root):
        recorded = json.loads(path.read_text(encoding="utf-8"))
        kit = path.stem.rsplit("-", 1)[0]
        agent = root / "fixtures" / "agents" / kit / "agent.toml"
        lacking = _trace_lacks(load_board_by_id(board), recorded)
        if board not in REPLAY_BOARDS.get(kit, (board,)):
            assert lacking, (board, path.name)  # a board without the camera or motion skips it
            continue
        assert lacking == [], (board, path.name)
        result = replay(path, agent=agent, target=target, board_id=board)
        assert result.verdicts == OUTCOMES[path.stem][0], path.name
        assert result.warnings == [] and result.divergences == []
        assert_matches_golden(result, recorded)


# --- the kits on the linux HAL, against the in-memory gpiod ---------------------------------------
# The same scenarios against the kernel's lines are `tests_linux/test_kit_*.py` (the `linux-hal` job).


def line_value(fake: FakeGpiod, pin: str):
    (path,) = fake.chips
    return fake.values.get((path, list(fake.chips[path]).index(pin)), None)


def is_high(fake: FakeGpiod, pin: str) -> bool:
    value = line_value(fake, pin)
    return value is not None and value.value == 1


def pi_variant_of_villa(root: Path, tmp_path: Path) -> Path:
    """The kit's agent without the voice front-end the Pi 5 profile cannot carry (`aec = false`)."""
    source = root / "fixtures" / "agents" / "villa-concierge"
    target = tmp_path / "villa"
    shutil.copytree(source, target)
    manifest = target / "agent.toml"
    kept = [
        text
        for text in manifest.read_text("utf-8").splitlines()
        if not text.startswith(('"audio.in"', '"audio.out"', '"display"'))
    ]
    manifest.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return manifest


def test_the_villa_kit_as_shipped_is_refused_on_the_pi_and_no_line_is_requested(root, gpio):
    from neuroedge.errors import BuildFailed
    from neuroedge.sim import SimSession

    with pytest.raises(BuildFailed, match="NE3003") as raised:
        SimSession.load(root / "fixtures" / "agents" / "villa-concierge" / "agent.toml",
                        target="linux")  # fmt: skip
    assert "aec" in str(raised.value.__dict__) + raised.value.how
    assert gpio.requests == []


def test_on_the_pi_an_allowed_unlock_drives_the_line_and_it_ends_low(
    root, gpio, tmp_path, fresh_actions
):
    import anyio

    from neuroedge.sim import SimSession

    session = SimSession.load(pi_variant_of_villa(root, tmp_path), target="linux")
    try:
        turn = anyio.run(session.handle, "mở cửa phòng 101")
        assert turn.allowed
        assert is_high(gpio, "door_lock")
    finally:
        session.close()
    assert not is_high(gpio, "door_lock"), "the session ends with the line low"


@pytest.mark.parametrize(
    ("facts", "text"),
    [({}, "mở cửa phòng 202"), ({}, "mở cửa"), ({"risk_level": "high"}, "mở cửa phòng 101")],
    ids=["the wrong room", "no room", "a risky guest"],
)
def test_on_the_pi_a_blocked_unlock_never_drives_the_line(
    root, gpio, tmp_path, fresh_actions, facts, text
):
    import anyio

    from neuroedge.sim import SimSession

    session = SimSession.load(pi_variant_of_villa(root, tmp_path), target="linux", facts=facts)
    try:
        turn = anyio.run(session.handle, text)
        assert turn.result is not None and turn.result.blocked
        assert gpio.history == [] or ("door_lock", 1) not in gpio.history
        assert not is_high(gpio, "door_lock")
    finally:
        session.close()


@pytest.fixture
def fake_sys(monkeypatch, tmp_path):
    """A /sys with the hwmon devices a test adds; the kernel's own is `tests_linux/`."""
    import neuroedge.hal.sysfs as sysfs

    monkeypatch.setattr(sysfs, "SYSFS_ROOT", str(tmp_path / "sys"))

    def add(index: int, name: str, channel: str, raw: str) -> Path:
        device = tmp_path / "sys" / "class" / "hwmon" / f"hwmon{index}"
        device.mkdir(parents=True, exist_ok=True)
        (device / "name").write_text(f"{name}\n")
        (device / f"{channel}_input").write_text(f"{raw}\n")
        return device

    return add


def test_the_home_voice_kit_on_the_pi_is_refused_without_a_motion_source(root, gpio):
    from neuroedge.errors import BoardCapabilityError
    from neuroedge.sim import SimSession

    agent = root / "fixtures" / "agents" / "home-voice" / "agent.toml"
    with pytest.raises(BoardCapabilityError, match="motion"):
        SimSession.load(agent, target="linux")
    assert gpio.requests == []


def test_the_home_voice_kit_on_the_pi_never_turns_the_light_off_on_a_sysfs_number(
    root, gpio, fake_sys, monkeypatch
):
    import anyio

    from neuroedge.sim import SimSession

    agent = root / "fixtures" / "agents" / "home-voice" / "agent.toml"
    fake_sys(3, "pir", "in0", "0")
    monkeypatch.setenv(linux.SENSORS_ENV, "motion=hwmon:pir/in0")
    session = SimSession.load(agent, target="linux")
    try:
        assert anyio.run(session.handle, "bật đèn").allowed
        assert is_high(gpio, "porch_light")
        off = anyio.run(session.handle, "tắt đèn")
        assert off.result.blocked and off.result.gate.failed_criterion == "room_empty"
        assert is_high(gpio, "porch_light"), (
            "a sysfs number is not a verdict that the room is empty"
        )
    finally:
        session.close()


def test_the_factory_kit_on_the_pi_follows_the_lm75_and_a_block_never_switches_off(
    root, gpio, fake_sys, monkeypatch
):
    import anyio

    from neuroedge.sim import SimSession

    agent = root / "fixtures" / "agents" / "factory-monitor" / "agent.toml"
    monkeypatch.setenv(linux.SENSORS_ENV, "temperature=hwmon:lm75/temp1")
    device = fake_sys(3, "lm75", "temp1", "30000")

    def heat(millidegrees: int) -> None:
        (device / "temp1_input").write_text(f"{millidegrees}\n")

    session = SimSession.load(agent, target="linux")
    try:
        assert anyio.run(session.handle, "bật quạt").allowed and is_high(gpio, "gate_relay")
        assert anyio.run(session.handle, "bật báo động").allowed and is_high(gpio, "porch_light")
        heat(45000)
        asked = anyio.run(session.handle, "tắt quạt")
        assert asked.result.blocked and asked.confirmation is not None
        heat(60000)
        refused = anyio.run(session.handle, "tắt quạt")
        assert refused.result.blocked and refused.confirmation is None
        assert anyio.run(session.handle, "tắt báo động").result.blocked
        assert is_high(gpio, "gate_relay") and is_high(gpio, "porch_light")
        heat(30000)
        assert anyio.run(session.handle, "tắt báo động").allowed
        assert not is_high(gpio, "porch_light")
        assert anyio.run(session.handle, "tắt quạt").allowed
        assert not is_high(gpio, "gate_relay")
    finally:
        session.close()


def test_a_factory_sensor_that_is_gone_blocks_every_switch_off_and_the_safe_ones_still_run(
    root, gpio, fake_sys, monkeypatch
):
    import anyio

    from neuroedge.hal.sysfs import SensorSource
    from neuroedge.sim import SimSession

    agent = root / "fixtures" / "agents" / "factory-monitor" / "agent.toml"
    monkeypatch.setenv(linux.SENSORS_ENV, "temperature=hwmon:lm75/temp1")
    fake_sys(3, "lm75", "temp1", "30000")
    session = SimSession.load(agent, target="linux")
    try:
        assert anyio.run(session.handle, "bật quạt").allowed and is_high(gpio, "gate_relay")
        session.hal.sensors.sources["temperature"] = SensorSource.parse(
            "temperature", "hwmon:lm76/temp1", "test"
        )
        off = anyio.run(session.handle, "tắt quạt")
        assert off.result.blocked and off.confirmation is None
        assert off.result.gate.reason.value == "criterion_unavailable"
        assert is_high(gpio, "gate_relay")
        assert anyio.run(session.handle, "bật báo động").allowed and is_high(gpio, "porch_light")
    finally:
        session.close()


@pytest.mark.parametrize("kit", KITS)
def test_a_new_project_from_a_kit_carries_its_golden_traces_and_they_replay(root, kit, tmp_path):
    from neuroedge.templates import scaffold

    files = scaffold("proj", kit, tmp_path)
    project = tmp_path / "proj"
    names = sorted(name for name in OUTCOMES if name.startswith(f"{kit}-"))
    assert names, kit
    for name in names:
        relative = Path("traces/golden") / f"{name}.json"
        assert relative in files
        assert (project / relative).read_bytes() == corpus_path(name).read_bytes()
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "neuroedge",
                "replay",
                str(relative),
                "--agent",
                "agent.toml",
                "--golden",
                str(relative),
                *(["--board", "sim-rpi5"] if kit in REPLAY_BOARDS else []),
            ],  # fmt: skip
            cwd=project,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stdout + result.stderr


# --- the camera and motion kits ------------------------------------------------------------------


def test_the_camera_and_motion_kits_are_skipped_by_the_boards_without_the_primitives(root):
    for board in ("sim-default", "esp32s3-box-3"):
        for kit, needs in (("gate-camera", "vision.in"), ("blinds", "motion")):
            for path in corpus(root):
                if path.stem.startswith(f"{kit}-"):
                    lacking = _trace_lacks(
                        load_board_by_id(board), json.loads(path.read_text(encoding="utf-8"))
                    )
                    assert needs in lacking, (board, path.name, lacking)
    for kit, boards in REPLAY_BOARDS.items():
        assert set(boards) == {"sim-rpi5", "linux-rpi5"}, kit


def by_name(root: Path, name: str) -> list[dict]:
    return events(corpus_path(name))


def test_the_camera_kit_traces_hold_a_stranger_the_refusals_and_a_lost_camera(root):
    reasons = [
        (e["data"]["reason"], e["data"]["failed_criterion"])
        for e in by_name(root, "gate-camera-block")
        if e["type"] == "gate_evaluation_result"
    ]
    assert reasons == [
        ("condition_not_met", "stranger_at_gate"),
        ("condition_not_met", "recording_consent"),
        ("condition_not_met", "stranger_confidence"),
        ("condition_not_met", "person_in_private_zone"),
        ("criterion_unavailable", "person_in_private_zone"),
    ]
    assert [e["type"] for e in by_name(root, "gate-camera-block")].count("camera_unavailable") == 1
    assert any(e["type"] == "vision_fact" for e in by_name(root, "gate-camera-allow"))


def test_the_blinds_traces_hold_a_lease_that_ends_safe_a_refusal_and_the_envelope(root):
    allow = by_name(root, "blinds-allow")
    assert [
        (e["data"]["target"], e["data"]["run"]) for e in allow if e["type"] == "motion_command"
    ] == [
        (90.0, "new"),
        (0.0, "renewed"),
    ]
    safe = [(e["data"]["state"], e["data"]["cause"]) for e in allow if e["type"] == "motion_safe"]
    assert safe[0] == ("hold", "lease_expired")
    block = by_name(root, "blinds-block")
    assert [
        (e["data"]["state"], e["data"]["cause"]) for e in block if e["type"] == "motion_safe"
    ] == [("hold", "lease_expired"), ("stop", "max_hold_ms")]
    assert [
        e["data"]["failed_criterion"]
        for e in block
        if e["type"] == "gate_evaluation_result" and e["data"]["verdict"] == BLOCK
    ] == ["estop_released", "path_clear", "motor_current_sense"]
    assert [e["data"]["target"] for e in block if e["type"] == "motion_command"] == [90.0], (
        "a BLOCK and an envelope refusal never reached the servo"
    )
    assert [e["data"]["reason"] for e in block if e["type"] == "envelope_refused"] == [
        "min_interval_ms"
    ]


def test_the_kit_gates_extend_the_library_and_only_tighten_it(root):
    for kit, parent in (("gate-camera", "camera"), ("blinds", "motor")):
        for gate in LOCKED_GATES[kit]:
            document = yaml.safe_load((root / gate).read_text("utf-8"))
            assert document["extends"] == f"neuroedge://gates/home/{parent}@1.0.0", gate
            assert "on_block" not in document or document["on_block"]["action"] != "allow"


@pytest.fixture
def pwm_sys(tmp_path):
    """`/sys` with one PWM chip of two channels already exported, as the pwm-2chan overlay gives."""
    chip = tmp_path / "sys" / "class" / "pwm" / "pwmchip0"
    chip.mkdir(parents=True)
    (chip / "export").write_text("")
    (chip / "npwm").write_text("2\n")
    for index in (0, 1):
        (chip / f"pwm{index}").mkdir()
        for name in ("period", "duty_cycle", "enable"):
            (chip / f"pwm{index}" / name).write_text("0\n")
    return tmp_path / "sys"


@pytest.fixture
def motion_gpio(monkeypatch, tmp_path, fake_sys):
    """The blinds rig: `servo_en` is a line, `limit_switch` is the emergency-stop contact (released),
    the ADC reads 0.4 V on the servo driver's current-sense pin, and the PWM is wired."""
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    names = [
        "door_lock", "porch_light", "gate_relay", "door_contact_raw", "limit_switch",
        "fan_en", "motor_en", "servo_en",
    ]  # fmt: skip
    fake = FakeGpiod({str(chip): names})
    fake.values[(str(chip), names.index("limit_switch"))] = Value.ACTIVE
    fake.estop = lambda released: fake.values.__setitem__(
        (str(chip), names.index("limit_switch")), Value.ACTIVE if released else Value.INACTIVE
    )
    monkeypatch.setattr(linux, "CHIP_GLOB", str(tmp_path / "gpiochip*"))
    monkeypatch.setattr(linux, "_import_gpiod", lambda: fake)
    monkeypatch.setenv(linux.MOTION_ENV, "gripper=pwmchip0/1")
    monkeypatch.setenv(linux.ANALOG_ENV, "adc0=hwmon:ads7828/in0")
    fake.adc = fake_sys(2, "ads7828", "in0", "400")
    return fake


def test_the_blinds_kit_on_the_pi_drives_the_enable_line_and_a_block_never_does(
    root, motion_gpio, pwm_sys
):
    import anyio

    from neuroedge.sim import SimSession

    agent = root / "fixtures" / "agents" / "blinds" / "agent.toml"
    options = {"sysfs_root": pwm_sys}
    session = SimSession.load(agent, target="linux", target_options=options)
    try:
        assert session.hal.motion_values().keys() == {"gripper"}
        assert anyio.run(session.handle, "mở rèm").allowed
        # the 200 ms lease may already have dropped the line on a slow machine: the history shows it rose
        assert ("servo_en", 1) in motion_gpio.history
    finally:
        session.close()
    assert not is_high(motion_gpio, "servo_en"), "the session ends with the driver down"
    raised = motion_gpio.history.count(("servo_en", 1))

    def blocked(text, after):
        session = SimSession.load(agent, target="linux", target_options=options)
        try:
            after()
            turn = anyio.run(session.handle, text)
            assert turn.result is not None and turn.result.blocked
            assert motion_gpio.history.count(("servo_en", 1)) == raised, "a BLOCK never powers it"
            return turn.result.gate.failed_criterion
        finally:
            session.close()

    assert blocked("mở rèm", lambda: motion_gpio.estop(False)) == "estop_released"
    motion_gpio.estop(True)
    motion_gpio.adc.joinpath("in0_input").write_text("900\n")  # 0.9 V: over the gate's 0.8 V
    assert blocked("mở rèm", lambda: None) == "motor_current_sense"
    motion_gpio.adc.joinpath("in0_input").write_text("400\n")


def test_a_blinds_current_sense_that_is_gone_refuses_the_session_and_the_servo_stays_off(
    root, motion_gpio, pwm_sys
):
    from neuroedge.errors import BoardCapabilityError
    from neuroedge.sim import SimSession

    agent = root / "fixtures" / "agents" / "blinds" / "agent.toml"
    motion_gpio.adc.joinpath("in0_input").unlink()  # the ADC no longer answers
    with pytest.raises(BoardCapabilityError, match="in0_input"):
        SimSession.load(agent, target="linux", target_options={"sysfs_root": pwm_sys})
    assert not is_high(motion_gpio, "servo_en")


def test_the_blinds_kit_on_the_pi_is_refused_when_no_pwm_is_wired_and_no_line_is_requested(
    root, motion_gpio, pwm_sys, monkeypatch
):
    from neuroedge.errors import BoardCapabilityError
    from neuroedge.sim import SimSession

    monkeypatch.delenv(linux.MOTION_ENV)
    agent = root / "fixtures" / "agents" / "blinds" / "agent.toml"
    with pytest.raises(BoardCapabilityError, match="no PWM channel is wired"):
        SimSession.load(agent, target="linux", target_options={"sysfs_root": pwm_sys})
    assert motion_gpio.requests == []


@pytest.mark.parametrize("kit", ["gate-camera", "blinds"])
def test_the_camera_and_motion_kits_build_for_linux_on_the_pi_again_and_again(root, kit):
    # What `tests_linux/test_kit_*.py` do: load the canonical agent once per test, in one process. The
    # action module is imported on the first build and cached for the rest, so a later build must still
    # find its `@action`s (a registry cleared in between, `fresh_actions`, would leave it none: NE3003).
    from neuroedge.engine.compiler import build

    agent = root / "fixtures" / "agents" / kit / "agent.toml"
    for _ in range(2):
        build(agent, target="linux", board_id="linux-rpi5")  # raises BuildFailed on any problem


@pytest.mark.parametrize("kit", ["gate_camera", "blinds"])
def test_a_linux_kit_test_that_loads_the_canonical_agent_does_not_clear_the_action_registry(
    root, kit
):
    text = (root / "python" / "tests_linux" / f"test_kit_{kit}.py").read_text("utf-8")
    uses = "fresh_actions" in text.replace("`fresh_actions`", "")
    assert uses == (kit == "gate_camera"), "only the tests that copy the agent isolate the registry"
