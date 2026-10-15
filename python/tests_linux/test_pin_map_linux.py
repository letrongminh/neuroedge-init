"""
The pin map on a real kernel (docs/spec/virtual_parts.md TC-PM-03-1, TSK-I2d-32).

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh`:

    cd python && python -m pytest -q tests_linux

An agent whose pins are `heater` and `air_pump` is mapped on `linux-rpi5` to `gate_relay` and
`door_lock`: the gpio-sim lines carry the board's names, the events and the trace the agent's. A
missing device is a failure, never a skip.
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

import pytest

from neuroedge.sim import SimSession
from neuroedge.testing import TracePlayer
from neuroedge.testing.recorder import TraceRecorder

# The lines in the order `scripts/setup_gpio_sim.sh` creates them: sim_gpioN is the N-th.
LINES = ["door_lock", "porch_light", "gate_relay"]

GATE = """schema:  neuroedge.gate/v1
name:    switch
version: 1.0.0
evaluate:
  owner_ok:
    type: bool
    instructions: "Chủ nhà cho phép"
allow_when:
  owner_ok: true
on_block:
  action:  deny
  message: "Không làm."
budget:
  p95_latency_ms: 150
  fail:           closed
"""


def kernel_value(sysfs: Path, pin: str) -> int:
    return int((sysfs / f"sim_gpio{LINES.index(pin)}" / "value").read_text().strip())


def wait_for(sysfs: Path, pin: str, value: int, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if kernel_value(sysfs, pin) == value:
            return True
        time.sleep(0.01)
    return False


def make_agent(root: Path) -> Path:
    (root / "actions").mkdir(parents=True)
    (root / "gates").mkdir()
    (root / "agent.toml").write_text(
        '[agent]\nname = "tank"\nversion = "0.1.0"\n\n'
        '[requires]\n"digital.out" = { pins = ["heater", "air_pump"] }\n\n'
        '[gates]\nswitch = "gates/switch@1.0.0.yaml"\n\n'
        '[targets]\nsupported = ["sim", "linux"]\n\n'
        '[targets.linux-rpi5.pins]\nheater = "gate_relay"\nair_pump = "door_lock"\n\n'
        "[sim.facts]\nowner_ok = true\n",
        encoding="utf-8",
    )
    (root / "actions" / "tank.py").write_text(
        "from neuroedge import action, digital\n\n\n"
        '@action(name="heater_on", requires="digital.out:heater", gate="switch")\n'
        "def heater_on() -> None:\n"
        '    """Turn the heater on."""\n'
        '    digital.out("heater").on()\n',
        encoding="utf-8",
    )
    (root / "gates" / "switch@1.0.0.yaml").write_text(GATE, encoding="utf-8")
    (root / "commands.toml").write_text(
        "[grammar]\nversion = 1\nthreshold = 0.80\n\n"
        '[[command]]\nintent = "heat"\npatterns = ["bật sưởi"]\n'
        'facts = { owner_ok = true }\ntool = "heater_on"\n',
        encoding="utf-8",
    )
    return root / "agent.toml"


@pytest.fixture(autouse=True)
def own_actions():
    """The agent registers its @action process-wide; put the registry back after each test."""
    import sys

    from neuroedge.actions import REGISTRY

    saved, modules = dict(REGISTRY), set(sys.modules)
    yield
    REGISTRY.clear()
    REGISTRY.update(saved)
    for module in set(sys.modules) - modules:
        if module.startswith("neuroedge_agent_"):
            del sys.modules[module]


def test_the_heater_moves_the_boards_gate_relay_line_and_the_trace_says_heater(tmp_path):
    sysfs = os.environ.get("NEUROEDGE_GPIO_SIM_SYSFS")
    assert sysfs, "NEUROEDGE_GPIO_SIM_SYSFS is not set; run scripts/setup_gpio_sim.sh first"
    agent = make_agent(tmp_path)
    recorder = TraceRecorder()
    session = SimSession.load(agent, target="linux", events=recorder)
    try:
        assert asyncio.run(session.handle("bật sưởi")).allowed
        assert wait_for(Path(sysfs), "gate_relay", 1)
        assert kernel_value(Path(sysfs), "door_lock") == 0  # only the mapped line moved
        trace = recorder.to_trace()
    finally:
        session.close()
    assert trace["metadata"]["pin_map"] == {"heater": "gate_relay", "air_pump": "door_lock"}
    pins = {e["data"]["pin"] for e in trace["events"] if e["type"] == "actuator_command"}
    assert pins == {"heater"}
    result = asyncio.run(TracePlayer(trace, agent=agent, target="linux").replay())
    assert result.verdicts == result.recorded_verdicts
