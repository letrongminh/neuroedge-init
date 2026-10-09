"""
TSK-I2c-16 — remote actuators in the HAL (RFC-0018 §3c–§3g, §3i): one road to the device, the
HAL's state of it, the off debt, P2, the trace and the replay. The reference plugin of
`fixtures/compliance/actuators/valid/` drives its in-memory double; the envelope's own part is in
`test_remote_actuator_envelope.py`, the declaration in `test_remote_actuator_build.py`.
"""

from __future__ import annotations

import dataclasses
import inspect
import socket

import pytest

from neuroedge import action, digital
from neuroedge.actions import Conversation
from neuroedge.engine import ActionContractEngine, resolve_gate_document
from neuroedge.errors import (
    ActionContractViolation,
    BoardCapabilityError,
    BuildFailed,
    EnvelopeRefusedError,
    TraceValidationError,
)
from neuroedge.hal import PinAssertion
from neuroedge.hal.envelope import SafetyEnvelope
from neuroedge.hal.remote import MAX_STATE_AGE_MS, OFF_RETRY_MS, FileRemoteStore
from neuroedge.trace import validate_trace

from .remote_support import Rig, actuator_toml, declaration, write_agent

pytestmark = pytest.mark.usefixtures("ref_plugins")


def l1_rig(**kwargs):
    return Rig({"valve": declaration("ref_l1")}, **kwargs)


def l2_rig(**kwargs):
    return Rig({"valve": declaration("ref_l2")}, **kwargs)


def at_the_next_apply(rig, name: str, happen, monkeypatch) -> None:
    """`happen()` right when the plugin sends the next on — after the state check read the device."""
    driver = rig.setup.checked.bound[name].driver
    real = driver.apply

    def apply(command):
        monkeypatch.setattr(driver, "apply", real)
        happen()
        return real(command)

    monkeypatch.setattr(driver, "apply", apply)


def sent(rig, operation: str) -> list[dict]:
    return [e for e in rig.of_type("remote_command_sent") if e["operation"] == operation]


# --- one road -----------------------------------------------------------------------------------

LEAKED: dict = {}


@action(name="t_remote_leak", requires="digital.out:valve", gate="valve")
def remote_leak() -> None:
    LEAKED["token"] = digital._active.get().token


@action(name="t_remote_on", requires="digital.out:valve", gate="valve")
def remote_on() -> None:
    digital.out("valve").pulse(ms=2_000)


def _conversation(rig: Rig) -> Conversation:
    engine = ActionContractEngine(clock=rig.clock, events=rig.events)
    engine.register(
        "valve",
        resolve_gate_document(
            {
                "schema": "neuroedge.gate/v1",
                "name": "valve",
                "version": "1.0.0",
                "evaluate": {"ok": {"type": "bool", "instructions": "Precondition holds"}},
                "allow_when": {"ok": True},
                "on_block": {"action": "deny"},
                "budget": {"p95_latency_ms": 100},
            }
        ),
    )
    return Conversation(engine=engine, hal=rig.hal, facts={"ok": True})


async def test_no_path_reaches_a_remote_actuator_without_a_valid_token():
    rig = l1_rig()
    c = _conversation(rig)
    await c.do(remote_leak)
    real = LEAKED["token"]
    for label, signature in {
        "no signature": "",
        "a string": "x",
        "a gate digest": real.gate_digest,
        "a forged token": dataclasses.replace(real, nonce="0" * 32),
        "a spent token": real,
    }.items():
        with pytest.raises(ActionContractViolation):
            rig.hal.digital_out("valve", "pulse", 1_000, signature=signature, called_from="t")
        assert not rig.double("valve").state(), label
        assert not sent(rig, "on"), label
    with pytest.raises(ActionContractViolation):  # outside c.do() there is no grant at all
        digital.out("valve").on()
    result = await c.do(remote_on)  # the one road: gate, token, envelope
    assert not result.blocked and rig.double("valve").state()
    assert len(sent(rig, "on")) == 1


def test_a_remote_actuator_plugin_receives_no_hal_no_ledger_and_no_envelope():
    rig = l1_rig()
    bound = rig.setup.checked.bound["valve"]
    (parameter,) = inspect.signature(bound.plugin.factory).parameters.values()
    assert parameter.name == "config"
    seen = []

    def spy(config):
        seen.append(config)
        return bound.plugin.factory(config)

    from neuroedge.plugins import build_actuator

    build_actuator(dataclasses.replace(bound.plugin, factory=spy), {"port": 9}, "here")
    (config,) = seen
    assert dict(config) == {"port": 9} and not hasattr(config, "__setitem__")
    from neuroedge.actions.token import TokenLedger
    from neuroedge.hal import HardwareAbstractionLayer

    forbidden = (HardwareAbstractionLayer, TokenLedger, SafetyEnvelope, Conversation)

    def reachable(value, depth=0):
        yield value
        if depth < 3:
            for item in list(getattr(value, "__dict__", {}).values()):
                yield from reachable(item, depth + 1)

    for item in reachable(bound.driver):
        assert not isinstance(item, forbidden), item
        assert item not in forbidden
    # the agent never gets the plugin either: digital.out returns the HAL's command handle
    handle = rig.pulse("valve", 1_000)
    assert handle is not bound.driver and not hasattr(handle, "apply")


def test_the_order_is_require_pin_state_guard_envelope_authorize_record_apply(monkeypatch):
    rig = l1_rig()
    order: list[str] = []
    hal, remote, envelope = rig.hal, rig.remote("valve"), rig.hal.envelope

    def spy(name, function):
        def call(*args, **kwargs):
            order.append(name)
            return function(*args, **kwargs)

        return call

    monkeypatch.setattr(hal, "_require_pin", spy("require_pin", hal._require_pin))
    monkeypatch.setattr(remote, "guard", spy("state_guard", remote.guard))
    monkeypatch.setattr(envelope, "reserve", spy("envelope", envelope.reserve))
    hal.authorize = spy("authorize", hal.authorize)
    monkeypatch.setattr(PinAssertion, "record", spy("record", PinAssertion.record))
    driver = rig.setup.checked.bound["valve"].driver
    monkeypatch.setattr(driver, "apply", spy("apply", driver.apply))
    rig.pulse("valve", 1_000)
    first = list(dict.fromkeys(order))  # the order in which each step first ran
    assert first == ["require_pin", "state_guard", "envelope", "authorize", "record", "apply"]
    # the name is checked before the state: an unknown name never reaches a plugin
    with pytest.raises(BoardCapabilityError):
        hal.digital_out("no_such_valve", "on", signature="t", called_from="t")


def test_a_refused_remote_on_spends_no_token_and_holds_no_envelope():
    rig = l1_rig()
    rig.double("valve").cut_link()
    with pytest.raises(EnvelopeRefusedError) as refused:
        rig.on("valve")
    assert refused.value.reason == "actuator_state_unknown" and refused.value.code == "NE1003"
    assert rig.allow.calls == [], "authorize — the token — is never reached"
    assert rig.hal.envelope.live("valve") is None
    assert rig.hal.envelope._states["valve"].intervals == []
    assert rig.of_type("envelope_refused") == [
        {
            "pin": "valve",
            "operation": "on",
            "reason": "actuator_state_unknown",
            "state": "uncertain",
        }
    ]
    assert rig.hal.pin("valve").never_pulsed() and not sent(rig, "on")


def test_off_to_a_remote_actuator_needs_no_token_and_is_never_refused():
    rig = l1_rig()
    rig.on("valve")
    from neuroedge.hal import _require_signature

    rig.hal.authorize = _require_signature  # the ledger refuses everything now
    rig.off("valve")
    assert not rig.double("valve").state() and rig.state("valve") == "off"
    rig.advance(1_100)
    rig.hal.authorize = rig.allow
    rig.on("valve")
    rig.double("valve").cut_link()
    rig.hal.authorize = _require_signature
    rig.off("valve")  # cannot reach the device: recorded, retried, never raised
    assert rig.of_type("remote_command_failed")[-1]["kind"] == "not_sent"
    assert rig.state("valve") == "uncertain"
    tries = len(sent(rig, "off"))
    rig.advance(OFF_RETRY_MS + 50)
    assert len(sent(rig, "off")) == tries + 1, "an owed off is sent again"
    rig.double("valve").heal_link()
    rig.advance(OFF_RETRY_MS + 50)
    assert not rig.double("valve").state() and rig.state("valve") == "off"


# --- state and a lost link ---------------------------------------------------------------------


def test_an_ambiguous_send_failure_holds_the_reservation_and_marks_the_actuator_uncertain(
    monkeypatch,
):
    rig = l1_rig()
    rig.advance(10)
    at_the_next_apply(rig, "valve", rig.double("valve").drop_next_reply, monkeypatch)
    with pytest.raises(BoardCapabilityError, match="ambiguous"):
        rig.pulse("valve", 2_000)
    assert rig.state("valve") == "uncertain"
    live = rig.hal.envelope.live("valve")
    assert live is not None and live.reserved_ms == 2_000, "the reservation stays"
    assert rig.of_type("remote_command_failed")[-1]["kind"] == "ambiguous"
    unknown = rig.of_type("remote_state_unknown")[-1]
    assert unknown["why"] == "command_timeout"
    rig.double("valve").cut_link()  # and nothing can be learnt about it now
    with pytest.raises(EnvelopeRefusedError) as again:
        rig.on("valve")
    assert again.value.reason == "actuator_state_unknown"
    assert rig.hal.envelope.live("valve") is live, "still held while it may be on"


def test_a_not_sent_failure_refunds_the_reservation(monkeypatch):
    rig = l1_rig()
    at_the_next_apply(rig, "valve", rig.double("valve").cut_link, monkeypatch)
    with pytest.raises(BoardCapabilityError, match="not_sent"):
        rig.pulse("valve", 2_000)
    assert rig.hal.envelope.live("valve") is None
    state = rig.hal.envelope._states["valve"]
    assert state.intervals == [] and state.last_end is None, "every millisecond went back"
    assert not rig.remote("valve").off_owed and rig.remote("valve").run is None
    assert rig.of_type("remote_command_failed")[-1]["kind"] == "not_sent"


def test_an_uncertain_actuator_refuses_on_but_still_sends_off():
    rig = l1_rig()
    rig.double("valve").cut_link()
    with pytest.raises(EnvelopeRefusedError, match="does not know"):
        rig.on("valve")
    assert rig.state("valve") == "uncertain"
    rig.off("valve")
    assert len(sent(rig, "off")) == 1
    rig.double("valve").heal_link()
    rig.off("valve")  # acknowledged, then read back off: known
    assert rig.state("valve") == "off"
    rig.advance(10)
    rig.on("valve")
    assert rig.double("valve").state()


def test_uncertain_ends_only_on_a_fresh_off_readback_never_on_a_timer():
    rig = l1_rig()
    rig.pulse("valve", 1_000)
    rig.advance(900)
    rig.double("valve").cut_link()
    rig.advance(300)  # the deadline: the HAL's off cannot be delivered
    assert rig.state("valve") == "uncertain" and rig.double("valve").state()
    rig.advance(10 * 60_000)  # any amount of time
    assert rig.state("valve") == "uncertain"
    with pytest.raises(EnvelopeRefusedError):
        rig.on("valve")
    rig.double("valve").heal_link()
    rig.advance(OFF_RETRY_MS + 50)  # the next retry lands, and a fresh reading says off
    assert rig.state("valve") == "off" and not rig.double("valve").state()
    confirmed = rig.of_type("remote_state_confirmed")[-1]
    assert confirmed["state"] == "off" and confirmed["unknown_ms"] >= 10 * 60_000


def test_a_reading_of_on_nobody_commanded_is_already_on_not_a_command_to_turn_off():
    rig = l1_rig()
    rig.double("valve").force(True)  # a person, a wall switch
    with pytest.raises(EnvelopeRefusedError) as refused:
        rig.on("valve")
    assert refused.value.reason == "already_on"
    rig.advance(5_000)
    assert rig.double("valve").state(), "the HAL does not turn off what it did not turn on"
    assert not sent(rig, "off") and rig.allow.calls == []


def test_the_hal_turns_off_only_what_it_turned_on():
    rig = l1_rig()
    rig.pulse("valve", 1_000)
    rig.advance(1_200)
    assert len(sent(rig, "off")) == 1  # its own on: its own off, at the deadline
    rig.double("valve").force(True)  # then somebody else
    rig.advance(60_000)
    rig.hal.close()
    assert len(sent(rig, "off")) == 1 and rig.double("valve").state()


def test_a_restart_leaves_every_remote_actuator_uncertain(tmp_path):
    options = {"remote_state": tmp_path / "state"}
    first = Rig(
        {"valve": declaration("ref_l1"), "pump": declaration("ref_l2")}, target_options=options
    )
    first.on("valve")  # and the process dies: no close(), the debt stays on disk
    second = Rig(
        {"valve": declaration("ref_l1"), "pump": declaration("ref_l2")}, target_options=options
    )
    assert second.state("valve") == "uncertain" and second.state("pump") == "uncertain"
    restarts = [e for e in second.of_type("remote_state_unknown") if e["why"] == "restart"]
    assert {e["actuator"] for e in restarts} == {"valve", "pump"}
    second.advance(10)
    assert [e["actuator"] for e in sent(second, "off")] == ["valve"], (
        "only the L1 debt is paid at start; nothing it did not turn on is touched"
    )
    second.pulse("pump", 1_000)  # a fresh reading clears `uncertain`
    assert second.state("pump") == "on"


def test_a_late_delivered_on_is_seen_by_readback_and_turned_off(monkeypatch):
    rig = l1_rig()
    # the on arrives, its answer is lost
    at_the_next_apply(rig, "valve", rig.double("valve").drop_next_reply, monkeypatch)
    with pytest.raises(BoardCapabilityError):
        rig.on("valve")
    assert rig.double("valve").state() and rig.state("valve") == "uncertain"
    with pytest.raises(EnvelopeRefusedError):
        rig.on("valve")  # the state check reads it on: unexpected, so the off goes now
    assert len(sent(rig, "off")) == 1 and not rig.double("valve").state()
    assert len(sent(rig, "on")) == 1, "an on is never sent again by itself"


# --- P2: the level is tested on every run -------------------------------------------------------


def test_a_device_that_turns_itself_off_is_recorded_as_evidence():
    rig = l2_rig()
    rig.pulse("valve", 2_000)
    assert sent(rig, "on")[0]["duration_ms"] == 2_000
    rig.advance(2_000 + 60)  # past start + D + tolerance
    readings = [e["state"] for e in rig.of_type("remote_state")]
    assert readings[-1] == "off"
    assert rig.state("valve") == "off" and not sent(rig, "off"), "no off of the HAL was needed"
    assert not rig.of_type("remote_level_violated")
    assert rig.hal.envelope.live("valve") is None


def test_a_device_still_on_after_its_guarantee_is_commanded_off_and_quarantined():
    rig = l2_rig()
    rig.double("valve").honors_timer = False  # the device breaks the level it declared
    rig.pulse("valve", 2_000)
    rig.advance(2_000 + 60)
    assert rig.of_type("remote_level_violated") == [
        {"actuator": "valve", "level": "L2", "expected_off_ms": 2_050, "observed": "on"}
    ]
    assert len(sent(rig, "off")) == 1 and not rig.double("valve").state()
    assert rig.state("valve") == "quarantined"


def test_a_quarantined_actuator_refuses_every_on_until_the_record_is_cleared(tmp_path):
    options = {"remote_state": tmp_path / "state"}
    rig = Rig({"valve": declaration("ref_l2")}, target_options=options)
    rig.double("valve").honors_timer = False
    rig.pulse("valve", 1_000)
    rig.advance(1_100)
    for _ in range(3):
        rig.advance(5_000)
        with pytest.raises(EnvelopeRefusedError) as refused:
            rig.pulse("valve", 500)
        assert refused.value.reason == "actuator_quarantined"
    rig.hal.close()
    restarted = Rig({"valve": declaration("ref_l2")}, target_options=options)
    assert restarted.state("valve") == "quarantined", "no way out by restarting"
    with pytest.raises(EnvelopeRefusedError, match="quarantined"):
        restarted.pulse("valve", 500)
    FileRemoteStore(tmp_path / "state").clear("valve")  # the operator, on the record
    cleared = Rig({"valve": declaration("ref_l2")}, target_options=options)
    assert cleared.state("valve") == "uncertain"
    cleared.pulse("valve", 500)
    assert cleared.state("valve") == "on"


async def test_uncertain_and_quarantined_are_absent_facts_so_a_gate_blocks():
    """
    The read-back as a gate fact needs the in-process fact source of TSK-I2c-09; until then no
    source gives it, so a gate that asks for it finds it absent and blocks — whatever the HAL's
    state (RFC-0018 §3e: uncertain and quarantined are never values).
    """
    for setup in ("uncertain", "quarantined", "off"):
        rig = l2_rig()
        if setup == "uncertain":
            rig.double("valve").cut_link()
            rig.hal.settle_remote()
        elif setup == "quarantined":
            rig.double("valve").honors_timer = False
            rig.pulse("valve", 500)
            rig.advance(600)
        engine = ActionContractEngine(clock=rig.clock, events=rig.events)
        engine.register(
            "valve",
            resolve_gate_document(
                {
                    "schema": "neuroedge.gate/v1",
                    "name": "valve",
                    "version": "1.0.0",
                    "evaluate": {"valve_off": {"type": "bool", "instructions": "Valve is off"}},
                    "allow_when": {"valve_off": True},
                    "on_block": {"action": "deny"},
                    "budget": {"p95_latency_ms": 100},
                }
            ),
        )
        c = Conversation(engine=engine, hal=rig.hal, facts={})
        result = await c.do(remote_on)
        assert result.blocked and result.gate.reason == "criterion_unavailable", setup


def test_the_state_fact_age_is_measured_by_the_receiver(monkeypatch):
    rig = l1_rig()
    driver = rig.setup.checked.bound["valve"].driver
    rig.clock.advance(4_000)
    monkeypatch.setattr(driver, "read_state", lambda: (False, 300))
    before = rig.clock.now
    rig.pulse("valve", 500)
    reading = rig.of_type("remote_state")[-1]
    assert reading["read_offset_ms"] == rig.events.offset_of(before - 300)
    assert rig.remote("valve").read_ms == before - 300
    rig.advance(2_000)
    monkeypatch.setattr(driver, "read_state", lambda: (False, MAX_STATE_AGE_MS + 1))
    with pytest.raises(EnvelopeRefusedError) as refused:
        rig.pulse("valve", 500)
    assert refused.value.reason == "actuator_state_unknown"
    assert rig.of_type("remote_state_unknown")[-1]["why"] == "stale"
    monkeypatch.setattr(driver, "read_state", lambda: (False, -5))  # an age cannot be negative
    with pytest.raises(EnvelopeRefusedError):
        rig.pulse("valve", 500)


# --- the trace ------------------------------------------------------------------------------------


def test_every_remote_command_sent_follows_an_actuator_command():
    rig = Rig({"valve": declaration("ref_l3", config={"max_lease_ms": 600})})
    rig.pulse("valve", 2_000)
    rig.advance(2_200)
    trace = rig.events.to_trace()
    validate_trace(trace)  # on, renewals, the end: every one where the lint wants it
    kinds = [e["type"] for e in trace["events"]]
    on = next(i for i, e in enumerate(trace["events"]) if e["type"] == "remote_command_sent")
    assert kinds[on - 1] == "actuator_command"

    def without(index):
        events = [e for i, e in enumerate(trace["events"]) if i != index]
        return {**trace, "events": events}

    with pytest.raises(TraceValidationError) as broken:
        validate_trace(without(on - 1))
    assert broken.value.code == "NE4001" and "no actuator_command" in broken.value.why
    renew = next(
        i
        for i, e in enumerate(trace["events"])
        if e["type"] == "remote_command_sent" and e["data"]["operation"] == "renew"
    )
    stray = dict(trace["events"][renew])
    lone = {**trace, "events": [trace["events"][0], stray]}
    with pytest.raises(TraceValidationError, match="renews a lease"):
        validate_trace(lone)
    moved = list(trace["events"])
    moved.insert(
        on, {"offset_ms": moved[on]["offset_ms"], "type": "gate_evaluation_begin", "data": {}}
    )
    with pytest.raises(TraceValidationError):
        validate_trace({**trace, "events": moved})  # a step boundary in between


def _session(agent, **kwargs):
    from neuroedge.sim.session import SimSession

    return SimSession.load(agent, **kwargs)


async def test_replay_never_builds_the_plugin_opens_a_socket_or_reads_the_key(
    tmp_path, fresh_actions, monkeypatch, ref_plugins
):
    from neuroedge.testing import TraceRecorder
    from neuroedge.testing.player import TracePlayer

    from .plugin_support import forget

    toml = actuator_toml().replace(
        "[actuators.garden_valve.envelope]",
        '[actuators.garden_valve.config]\ntoken_env = "NE_VALVE_TOKEN"\n\n'
        "[actuators.garden_valve.envelope]",
    )
    agent = write_agent(tmp_path / "agent", toml)
    recorder = TraceRecorder()
    session = _session(agent, events=recorder)
    turn = await session.handle("water the garden")
    assert turn.allowed
    session.close()
    trace = recorder.to_trace()
    assert {p["name"] for p in trace["metadata"]["plugins"]} == {
        "ref_l0",
        "ref_l1",
        "ref_l2",
        "ref_l3",
    }
    # the plugin leaves the machine, the network and the key are off limits
    import sys

    sys.path.remove(str(ref_plugins))
    forget("neuroedge_ref_actuators")

    def no_socket(*args, **kwargs):
        raise AssertionError("replay opened a socket")

    monkeypatch.setattr(socket, "create_connection", no_socket)
    monkeypatch.setattr(socket.socket, "connect", no_socket)
    import os

    read: list[str] = []
    real_get = os.environ.get

    def watch(key, default=None):
        read.append(key)
        return real_get(key, default)

    monkeypatch.setattr(os.environ, "get", watch)
    result = await TracePlayer(trace, agent=agent).replay()
    sys.path.insert(0, str(ref_plugins))
    assert not result.divergences and result.verdicts == ["ALLOW"]
    assert "NE_VALVE_TOKEN" not in read
    assert "neuroedge_ref_actuators" not in sys.modules


async def test_replay_refuses_the_same_on_it_refused_when_recorded(tmp_path, fresh_actions):
    from neuroedge.testing import TraceRecorder
    from neuroedge.testing.player import TracePlayer

    agent = write_agent(tmp_path / "agent", actuator_toml())
    recorder = TraceRecorder()
    session = _session(agent, events=recorder)
    session.hal._remote["garden_valve"].double.cut_link()
    with pytest.raises(EnvelopeRefusedError):
        await session.handle("water the garden")
    session.close()
    trace = recorder.to_trace()
    refusals = [e["data"] for e in trace["events"] if e["type"] == "envelope_refused"]
    assert refusals and refusals[0]["reason"] == "actuator_state_unknown"
    assert not session.hal._remote["garden_valve"].double.state()
    result = await TracePlayer(trace, agent=agent).replay()
    assert not result.divergences, result.divergences
    replayed = [e["data"] for e in result.replayed["events"] if e["type"] == "envelope_refused"]
    assert replayed[0]["reason"] == "actuator_state_unknown"
    assert result.hal.pin("garden_valve").never_pulsed()


def test_the_canonical_traces_do_not_change(traces_dir):
    from neuroedge.trace import load_trace

    for path in sorted(traces_dir.glob("*.json")):
        trace = load_trace(path)  # validated, the remote lint included
        assert "plugins" not in trace["metadata"], path.name
        assert not [e for e in trace["events"] if e["type"].startswith(("remote_", "plugin_"))]


# --- boundaries -----------------------------------------------------------------------------------


async def test_sim_never_uses_the_real_plugin(tmp_path, fresh_actions, monkeypatch):
    attempts: list[object] = []

    def record(*args, **kwargs):
        attempts.append(args)
        raise OSError("blocked by the test")

    monkeypatch.setattr(socket, "create_connection", record)
    monkeypatch.setenv("NE_VALVE_TOKEN", "x")
    toml = actuator_toml().replace(
        "[actuators.garden_valve.envelope]",
        '[actuators.garden_valve.config]\nhost = "valve.example"\ntoken_env = "NE_VALVE_TOKEN"\n\n'
        "[actuators.garden_valve.envelope]",
    )
    agent = write_agent(tmp_path / "agent", toml)
    session = _session(agent)
    turn = await session.handle("water the garden")
    assert turn.allowed
    double = session.hal._remote["garden_valve"].double
    assert double is not None and double.state(), "the double was driven"
    assert [m["op"] for m in double.received][-1] == "on"
    session.close()
    assert attempts == [], "sim never reached the device"


async def test_a_guard_toml_drives_a_remote_actuator_and_its_trace_replays(tmp_path):
    from neuroedge.guard import Guard
    from neuroedge.paths import repo_root
    from neuroedge.sdk import ToolRequest
    from neuroedge.testing.player import TracePlayer

    (tmp_path / "light.yaml").write_text(
        (repo_root() / "gates" / "home" / "light@1.0.0.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    path = tmp_path / "guard.toml"
    path.write_text(
        """[guard]
name  = "garden"
board = "sim-default"

[plugins]
enable = ["neuroedge-ref-actuators"]

[actuators.garden_valve]
plugin     = "ref_l1"
safe_off   = "L1"
reversible = true
[actuators.garden_valve.envelope]
window_s             = 3600
max_on_ms_per_window = 600000
min_interval_ms      = 1000
max_continuous_ms    = 60000

[tools.water]
gate     = "light.yaml"
requires = ["digital.out:garden_valve"]
drive    = [{ pin = "garden_valve", operation = "pulse", seconds_from = "seconds" }]

[tools.water.parameters.seconds]
type    = "integer"
default = 5
""",
        encoding="utf-8",
    )
    guard = Guard.load(path)
    guard.set_fact("device_fault_free", True)
    guard.set_fact("quiet_hours_ok", True)
    bridge = guard.dispatcher("garden")
    outcome = await bridge.dispatch(ToolRequest("water", {"seconds": 3}))
    assert outcome.status == "ALLOW"
    double = guard.hal._remote["garden_valve"].double
    assert double.state() and double.received[-1] == {"op": "on", "seq": 1}
    trace = guard.trace()
    guard.close()
    assert {p["name"] for p in trace["metadata"]["plugins"]} >= {"ref_l1"}
    sent_on = [
        e
        for e in trace["events"]
        if e["type"] == "remote_command_sent" and e["data"]["operation"] == "on"
    ]
    assert sent_on[0]["data"]["level"] == "L1" and sent_on[0]["data"]["plugin"] == "ref_l1"
    result = await TracePlayer(trace, guard=path).replay()
    assert not result.divergences and result.verdicts == ["ALLOW"]
    assert result.hal.pin("garden_valve").pulses == [3_000]
    # the same file with the actuator irreversible does not load: the one check, at load
    path.write_text(path.read_text(encoding="utf-8").replace("reversible = true\n", ""))
    with pytest.raises(BuildFailed):
        Guard.load(path)


async def test_a_recorded_off_ends_the_run_in_the_replay_too(tmp_path):
    """Replay ends a remote run where the recording's off ended it, not at its deadline."""
    from neuroedge.guard import Guard
    from neuroedge.paths import repo_root
    from neuroedge.sdk import ToolRequest
    from neuroedge.testing.player import TracePlayer

    (tmp_path / "light.yaml").write_text(
        (repo_root() / "gates" / "home" / "light@1.0.0.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    path = tmp_path / "guard.toml"
    path.write_text(
        """[guard]
name  = "valve"
board = "sim-default"
[plugins]
enable = ["neuroedge-ref-actuators"]
[actuators.garden_valve]
plugin     = "ref_l1"
safe_off   = "L1"
reversible = true
[actuators.garden_valve.envelope]
window_s             = 3600
max_on_ms_per_window = 600000
min_interval_ms      = 0
max_continuous_ms    = 60000
[tools.open]
gate     = "light.yaml"
requires = ["digital.out:garden_valve"]
drive    = [{ pin = "garden_valve", operation = "on" }]
[tools.close]
gate     = "light.yaml"
requires = ["digital.out:garden_valve"]
drive    = [{ pin = "garden_valve", operation = "off" }]
""",
        encoding="utf-8",
    )
    guard = Guard.load(path)
    guard.set_fact("device_fault_free", True)
    guard.set_fact("quiet_hours_ok", True)
    bridge = guard.dispatcher("valve")
    for tool in ("open", "close", "open"):
        assert (await bridge.dispatch(ToolRequest(tool))).status == "ALLOW"
    trace = guard.trace()
    guard.close()
    assert not [e for e in trace["events"] if e["type"] == "envelope_refused"]
    result = await TracePlayer(trace, guard=path).replay()
    assert not result.divergences, result.divergences
    assert [op for op, _ in result.hal.pin("garden_valve").commands] == ["on", "off", "on"]
