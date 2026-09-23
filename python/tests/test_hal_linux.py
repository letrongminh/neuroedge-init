"""
TSK-S3-05 — `LinuxHAL` logic, against an in-memory stand-in for the gpiod v2 bindings.

These run everywhere. The same HAL against real kernel lines (gpio-sim) is
`tests_linux/`, run by the `linux-hal` CI job (Q-16) — kept out of this suite
because a machine without gpio-sim could only skip them, and no test may skip.
"""

from __future__ import annotations

import time
from enum import Enum
from types import SimpleNamespace

import pytest

from neuroedge.actions import Conversation
from neuroedge.engine.compiler import load_actions, load_agent_manifest, resolve_gates
from neuroedge.engine.gate import ActionContractEngine
from neuroedge.engine.trace_sink import EventLog
from neuroedge.errors import ActionContractViolation, BoardCapabilityError
from neuroedge.hal.board import load_board_by_id
from neuroedge.hal.linux import LinuxHAL
from neuroedge.testing import assert_matches_golden, replay


class Direction(Enum):
    INPUT = 1
    OUTPUT = 2


class Value(Enum):
    INACTIVE = 0
    ACTIVE = 1


class FakeChip:
    """A chip whose lines are named; the kernel does the same for gpio-sim."""

    def __init__(self, world, path):
        self.world, self.path = world, path

    def line_offset_from_id(self, name):
        names = self.world.chips[self.path]
        if name not in names:
            raise OSError(2, "No such line")
        return names.index(name)

    def close(self):
        pass


class FakeRequest:
    def __init__(self, world, path, offsets):
        self.world, self.path, self.offsets = world, path, offsets
        self.released = False

    def set_value(self, offset, value):
        assert not self.released and offset in self.offsets
        self.world.values[(self.path, offset)] = value
        self.world.history.append((self.world.chips[self.path][offset], value.value))

    def get_value(self, offset):
        return self.world.values.get((self.path, offset), Value.INACTIVE)

    def release(self):
        self.released = True


class FakeGpiod:
    def __init__(self, chips):
        self.chips = chips
        self.values = {}
        self.history = []
        self.requests = []
        self.line = SimpleNamespace(Direction=Direction, Value=Value)

    def Chip(self, path):  # noqa: N802 - mirrors gpiod.Chip
        return FakeChip(self, path)

    def LineSettings(self, direction, output_value):  # noqa: N802 - mirrors gpiod.LineSettings
        assert direction is Direction.OUTPUT and output_value is Value.INACTIVE
        return {"direction": direction, "output_value": output_value}

    def request_lines(self, path, consumer, config):
        (offsets,) = config
        request = FakeRequest(self, path, offsets)
        self.requests.append(request)
        return request


LINES = ["door_lock", "porch_light", "gate_relay", "spare"]


@pytest.fixture
def chips(tmp_path):
    path = tmp_path / "gpiochip0"
    path.write_text("")
    return str(tmp_path / "gpiochip*"), {str(path): LINES}


def make_hal(chips, **kwargs):
    pattern, table = chips
    fake = FakeGpiod(table)
    hal = LinuxHAL(chip_glob=pattern, gpiod=fake, events=kwargs.pop("events", None), **kwargs)
    return hal, fake


# --- Q-16: never a silent no-op ------------------------------------------------------


def test_no_gpio_chip_raises_a_three_part_error(tmp_path):
    with pytest.raises(BoardCapabilityError) as raised:
        LinuxHAL(chip_glob=str(tmp_path / "gpiochip*"), gpiod=FakeGpiod({}))
    error = raised.value
    assert error.where == "LinuxHAL.__init__"
    assert "no GPIO chip" in error.why and "no-op" in error.why
    assert "setup_gpio_sim.sh" in error.how


def test_a_chip_without_the_board_pins_raises(tmp_path):
    path = tmp_path / "gpiochip0"
    path.write_text("")
    with pytest.raises(BoardCapabilityError, match="door_lock"):
        LinuxHAL(chip_glob=str(tmp_path / "gpiochip*"), gpiod=FakeGpiod({str(path): ["x", "y"]}))


def test_a_sim_board_is_refused(chips):
    with pytest.raises(BoardCapabilityError, match="not 'linux'"):
        LinuxHAL(load_board_by_id("sim-default"), chip_glob=chips[0], gpiod=FakeGpiod(chips[1]))


def test_line_names_map_board_pins_to_kernel_lines(tmp_path):
    path = tmp_path / "gpiochip0"
    path.write_text("")
    fake = FakeGpiod({str(path): ["GPIO17", "GPIO27", "GPIO22"]})
    hal = LinuxHAL(
        chip_glob=str(tmp_path / "gpiochip*"),
        gpiod=fake,
        line_names={"door_lock": "GPIO17", "porch_light": "GPIO27", "gate_relay": "GPIO22"},
    )
    assert hal.lines["door_lock"] == (str(path), 0)


def test_every_line_starts_inactive_and_is_requested_as_output(chips):
    hal, fake = make_hal(chips)
    assert set(hal.lines) == {"door_lock", "porch_light", "gate_relay"}
    assert all(not hal.line_value(pin) for pin in hal.lines)
    (request,) = fake.requests
    assert sorted(request.offsets) == [0, 1, 2]


# --- the A3 contract holds on linux too ----------------------------------------------


def test_the_default_authoriser_refuses_every_command(chips):
    hal, fake = make_hal(chips)
    with pytest.raises(ActionContractViolation):
        hal.digital_out("door_lock", "pulse", 1000, signature="looks-like-proof")
    assert fake.history == []
    assert hal.pin("door_lock").never_pulsed()


# --- pulses, on/off, cancel ----------------------------------------------------------


def open_hal(chips, **kwargs):
    return make_hal(chips, authorize=lambda *_: None, **kwargs)


def test_a_pulse_drives_the_line_then_releases_it(chips):
    events = EventLog()
    hal, fake = open_hal(chips, events=events)
    hal.digital_out("door_lock", "pulse", 50)
    assert hal.line_value("door_lock")
    deadline = time.monotonic() + 2
    while hal.line_value("door_lock") and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not hal.line_value("door_lock")
    assert fake.history[-2:] == [("door_lock", 1), ("door_lock", 0)]
    assert events.of_type("actuator_command") == [
        {"pin": "door_lock", "operation": "pulse", "duration_ms": 50}
    ]
    assert hal.pin("door_lock").pulsed_once(duration_ms=50)


def test_cancel_drops_the_line_at_once_and_records_why(chips):
    events = EventLog()
    hal, _ = open_hal(chips, events=events)
    pending = hal.digital_out("door_lock", "pulse", 30000)
    assert hal.line_value("door_lock")
    pending.cancel()
    assert not hal.line_value("door_lock")
    assert events.of_type("actuator_aborted") == [
        {"pin": "door_lock", "reason": "ACTUATOR_ABORTED_BY_BARGE_IN"}
    ]
    assert hal._timers == {}


def test_on_and_off(chips):
    hal, _ = open_hal(chips)
    hal.digital_out("porch_light", "on")
    assert hal.line_value("porch_light")
    hal.digital_out("porch_light", "off")
    assert not hal.line_value("porch_light")


def test_a_new_command_supersedes_a_pending_pulse(chips):
    hal, _ = open_hal(chips)
    hal.digital_out("gate_relay", "pulse", 30)
    hal.digital_out("gate_relay", "on")
    time.sleep(0.1)
    assert hal.line_value("gate_relay"), "the old pulse's timer must not switch the line off"


def test_close_releases_every_line_inactive(chips):
    hal, fake = open_hal(chips)
    hal.digital_out("door_lock", "pulse", 30000)
    hal.close()
    assert fake.values[(next(iter(fake.chips)), 0)] is Value.INACTIVE
    assert all(request.released for request in fake.requests)
    hal.close()  # idempotent


def test_an_unknown_operation_is_refused(chips):
    hal, _ = open_hal(chips)
    with pytest.raises(BoardCapabilityError, match="unknown operation"):
        hal.digital_out("door_lock", "blink")


# --- equivalence: the same session on sim and on linux --------------------------------


@pytest.mark.parametrize("name", ["happy-path", "unverified_attempt", "network_offline"])
def test_each_canonical_trace_gives_the_same_decisions_on_linux(chips, traces_dir, name):
    hal, _ = make_hal(chips)
    result = replay(traces_dir / f"{name}.json", target="linux", hal=hal)
    assert result.hal is hal
    assert_matches_golden(result, traces_dir / f"{name}.json")


async def test_c_do_drives_a_linux_line_through_the_token_ledger(chips, root):
    manifest = load_agent_manifest(root / "fixtures" / "agents" / "villa-concierge" / "agent.toml")
    load_actions(manifest)
    gates, _ = resolve_gates(manifest)
    events = EventLog(target="linux", board_id="linux-rpi5")
    hal, fake = make_hal(chips, events=events)
    engine = ActionContractEngine(gates, events=events)
    facts = {"guest_authenticated": True, "risk_level": "low", "room_matches": True}
    c = Conversation(engine=engine, hal=hal, facts=facts)
    result = await c.do("unlock_door", guest_id="101")
    assert not result.blocked
    assert hal.line_value("door_lock")
    assert fake.history == [("door_lock", 1)]
    hal.close()


def test_replay_on_linux_builds_the_linux_hal(monkeypatch, chips, traces_dir):
    pattern, table = chips
    import neuroedge.hal.linux as linux

    fake = FakeGpiod(table)
    monkeypatch.setattr(linux, "CHIP_GLOB", pattern)
    monkeypatch.setattr(linux, "_import_gpiod", lambda: fake)
    result = replay(traces_dir / "happy-path.json", target="linux")
    assert isinstance(result.hal, LinuxHAL)
    assert result.hal.board.id == "linux-rpi5"
    assert result.replayed["metadata"]["target"] == "linux"
    assert fake.history[0] == ("door_lock", 1)
    assert all(request.released for request in fake.requests), "replay closes the HAL"
