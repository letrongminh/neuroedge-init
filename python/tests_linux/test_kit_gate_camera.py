"""
The gate-camera kit on a real kernel (TSK-I2b-02): a stranger at the gate, seen by a V4L2 camera.

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh` and `scripts/setup_vivid.sh`:

    cd python && python -m pytest -q tests_linux

`porch_light` and `gate_relay` are gpio-sim lines, read from sysfs independently of the process that
drives them. The camera is `vivid`, the kernel's virtual capture device: it streams real frames, and the
sample's scripted model (`provider = "replay"`) says what it "sees" in each, so a stranger at the gate is
a script that names one. What this does not show — a real model on a real camera, a lock that holds a
gate — is the stage-B rig's (`docs/user/kit-camera-cong.md`, "Chưa kiểm").

NOTE: written without a kernel at hand (the author's machine is not Linux); the same scenarios on `sim`
are `python/tests/test_kits.py` and the project's own tests. If a vivid detail differs, CI shows it here.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from pathlib import Path

import pytest

from neuroedge.actions.tools import ToolCall
from neuroedge.paths import fixtures_dir
from neuroedge.sim import SimSession
from neuroedge.testing import assert_matches_golden, replay

AGENT = fixtures_dir() / "agents" / "gate-camera"
GOLDEN = fixtures_dir() / "traces" / "kits"
# The lines in the order `scripts/setup_gpio_sim.sh` creates them: sim_gpioN is the N-th.
LINES = [
    "door_lock",
    "porch_light",
    "gate_relay",
    "door_contact_raw",
    "limit_switch",
    "fan_en",
    "motor_en",
    "servo_en",
]
STRANGER = '[{ label = "unknown_person", score = 0.93, box = [0.4, 0.5, 0.6, 0.9] }]'
UNSURE = '[{ label = "unknown_person", score = 0.60, box = [0.4, 0.5, 0.6, 0.9] }]'


@pytest.fixture(scope="module")
def sysfs() -> Path:
    path = os.environ.get("NEUROEDGE_GPIO_SIM_SYSFS")
    assert path, "run scripts/setup_gpio_sim.sh first; it exports NEUROEDGE_GPIO_SIM_SYSFS"
    return Path(path)


def kernel_value(sysfs: Path, pin: str) -> int:
    return int((sysfs / f"sim_gpio{LINES.index(pin)}" / "value").read_text().strip())


def wait_for(sysfs: Path, pin: str, value: int, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if kernel_value(sysfs, pin) == value:
            return True
        time.sleep(0.01)
    return False


def seen(tmp_path: Path, scene: str) -> Path:
    """A copy of the sample whose scripted model sees `scene` in frames 0-4000."""
    project = tmp_path / "gate-camera"
    shutil.copytree(AGENT, project, ignore=shutil.ignore_patterns("__pycache__"))
    toml = project / "agent.toml"
    text = toml.read_text(encoding="utf-8")
    head = text.split("[vision.options.script]")[0]
    tail = "# Camera ảo của `sim`" + text.split("# Camera ảo của `sim`")[1]
    script = "\n".join(f"{n} = {scene}" for n in range(4001))
    toml.write_text(f"{head}[vision.options.script]\n{script}\n\n{tail}", encoding="utf-8")
    return toml


def ask(session: SimSession, tool: str) -> dict:
    return asyncio.run(session.call_tool(ToolCall(tool, {}, source="local_grammar"))).content()


def until(session: SimSession, tool: str, status: str, seconds: float = 8.0) -> dict:
    """Ask until the answer is `status`: the first frames of a stream are not a window yet."""
    answer, deadline = {}, time.monotonic() + seconds
    while time.monotonic() < deadline:
        time.sleep(0.1)
        answer = ask(session, tool)
        if answer["status"] == status:
            break
    return answer


@pytest.mark.usefixtures("fresh_actions")
def test_a_stranger_on_the_kernel_camera_turns_the_light_on_and_locks_the_gate(tmp_path, sysfs):
    session = SimSession.load(seen(tmp_path, STRANGER), target="linux")
    try:
        assert until(session, "stranger_light", "ALLOW")["status"] == "ALLOW"
        assert wait_for(sysfs, "porch_light", 1), "stranger_light reaches the kernel line"
        assert until(session, "stranger_lock", "ALLOW")["status"] == "ALLOW"
        assert wait_for(sysfs, "gate_relay", 1), "stranger_lock reaches the kernel line"
    finally:
        session.close()
    assert kernel_value(sysfs, "porch_light") == 0 and kernel_value(sysfs, "gate_relay") == 0


@pytest.mark.usefixtures("fresh_actions")
def test_an_empty_scene_and_an_unsure_model_never_move_a_line(tmp_path, sysfs):
    quiet = SimSession.load(seen(tmp_path / "empty", "[]"), target="linux")
    try:
        answer = until(quiet, "stranger_light", "ALLOW", seconds=2.0)
        assert answer["status"] == "BLOCK" and answer["failed_criterion"] == "stranger_at_gate"
    finally:
        quiet.close()
    unsure = SimSession.load(seen(tmp_path / "unsure", UNSURE), target="linux")
    try:
        answer = until(unsure, "stranger_lock", "ALLOW", seconds=2.0)
        assert answer["status"] == "BLOCK" and answer["failed_criterion"] == "stranger_confidence"
    finally:
        unsure.close()
    assert not wait_for(sysfs, "porch_light", 1, timeout=0.3), "a BLOCK never moves the light"
    assert not wait_for(sysfs, "gate_relay", 1, timeout=0.3), "a BLOCK never moves the lock"


@pytest.mark.usefixtures("fresh_actions")
def test_without_consent_the_camera_does_not_act(tmp_path, sysfs):
    session = SimSession.load(seen(tmp_path, STRANGER), target="linux")
    try:
        session.set_fact("recording_consent", False)
        answer = until(session, "stranger_light", "ALLOW", seconds=2.0)
        assert answer["status"] == "BLOCK" and answer["failed_criterion"] == "recording_consent"
    finally:
        session.close()
    assert kernel_value(sysfs, "porch_light") == 0


@pytest.mark.parametrize("name", ["gate-camera-allow", "gate-camera-block"])
def test_the_golden_traces_replay_on_the_kernel_lines_as_recorded(name, sysfs):
    path = GOLDEN / f"{name}.json"
    linux = replay(path, target="linux", agent=AGENT / "agent.toml", board_id="linux-rpi5")
    assert linux.verdicts == linux.recorded_verdicts
    assert linux.warnings == [] and linux.divergences == []
    assert_matches_golden(linux, path)
    assert kernel_value(sysfs, "porch_light") == 0 and kernel_value(sysfs, "gate_relay") == 0
