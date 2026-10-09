"""
TSK-I2c-16 — the envelope of a remote actuator (RFC-0018 §3h): the four keys of RFC-0007 §3d with
the same meaning, a run that ends only when the HAL knows the device is off (never earlier), the
ceiling `max_continuous_ms + tolerance_ms` counted, the same ending on `sim` and `linux`, and the
records written before the command.
"""

from __future__ import annotations

import json

import pytest

from neuroedge.errors import EnvelopeRefusedError
from neuroedge.hal.remote import OFF_RETRY_MS, OFF_SLACK_MS

from .remote_support import ENVELOPE, Rig, declaration
from .test_hal_linux import LINES, FakeGpiod

pytestmark = pytest.mark.usefixtures("ref_plugins")


def linux_options(tmp_path, **more):
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    return {
        "gpiod": FakeGpiod({str(chip): LINES}),
        "chip_glob": str(tmp_path / "gpiochip*"),
        "envelope_state": tmp_path / "state",
        "envelope_init": True,
        **more,
    }


def sent(rig, operation):
    return [e for e in rig.of_type("remote_command_sent") if e["operation"] == operation]


def reservation_of(rig, name="valve"):
    return rig.remote(name).run.reservation


def test_the_remote_envelope_keys_have_the_meaning_of_rfc_0007():
    tight = {**ENVELOPE, "max_continuous_ms": 10_000, "max_on_ms_per_window": 15_000}
    rig = Rig({"valve": declaration("ref_l2", envelope=tight)})
    # max_continuous_ms caps D: a longer pulse and an `on` with no end both carry D = 10 s
    rig.pulse("valve", 20_000)
    assert sent(rig, "on")[-1]["duration_ms"] == 10_000
    rig.advance(10_100)
    with pytest.raises(EnvelopeRefusedError) as resting:  # min_interval_ms, from the known end
        rig.on("valve")
    assert resting.value.reason == "min_interval_ms"
    rig.advance(1_000)
    with pytest.raises(EnvelopeRefusedError) as spent:  # max_on_ms_per_window: 10 s + 10 s > 15 s
        rig.on("valve")
    assert spent.value.reason == "window_budget"
    rig.pulse("valve", 4_000)  # what is left of the window
    assert sent(rig, "on")[-1]["duration_ms"] == 4_000
    with pytest.raises(EnvelopeRefusedError) as running:
        rig.pulse("valve", 100)
    assert running.value.reason == "already_on"
    # L1: the HAL sends the off at D, within OFF_SLACK_MS, and says why
    l1 = Rig({"lamp": declaration("ref_l1", envelope=tight)})
    l1.on("lamp")
    l1.advance(10_000 - 60)
    assert not sent(l1, "off")
    l1.advance(OFF_SLACK_MS)
    assert len(sent(l1, "off")) == 1
    assert l1.of_type("actuator_command")[-1] == {
        "pin": "lamp",
        "operation": "off",
        "duration_ms": 0,
        "cause": "max_continuous_ms",
    }


def test_the_window_counts_until_the_hal_knows_the_actuator_is_off():
    rig = Rig({"valve": declaration("ref_l1")})
    start = rig.clock.now
    rig.pulse("valve", 1_000)
    reservation = reservation_of(rig)
    rig.advance(900)
    rig.double("valve").cut_link()
    rig.advance(5_000)  # the off at the deadline did not land: the device may still be on
    assert rig.state("valve") == "uncertain"
    assert rig.hal.envelope.live("valve") is reservation
    state = rig.hal.envelope._states["valve"]
    assert state.intervals[-1].end >= rig.clock.now - 1, "the on-time counts to now, not to D"
    rig.double("valve").heal_link()
    rig.advance(OFF_RETRY_MS + 50)
    assert rig.hal.envelope.live("valve") is None
    assert reservation.ended_ms > start + 5_000, "ended when the HAL knew, not at the deadline"


def test_the_physical_ceiling_is_max_continuous_plus_tolerance_and_is_counted():
    # without a read-back the HAL cannot know sooner: the run lasts until the device's guarantee
    rig = Rig({"valve": declaration("ref_l2", reversible=True, config={"readback": "none"})})
    rig.hal.digital_out("valve", "off", called_from="t")  # an acknowledged off: known off
    start = rig.clock.now
    rig.pulse("valve", 1_000)
    reservation = reservation_of(rig)
    rig.advance(1_000 + 10)
    assert len(sent(rig, "off")) == 2, "the HAL's own off at D, as at L1"
    assert rig.hal.envelope.live("valve") is reservation, "not over before D + tolerance"
    rig.advance(100)
    assert reservation.ended_ms == start + 1_000 + 50
    used = sum(i.length for i in rig.hal.envelope._states["valve"].intervals)
    assert used == 1_050, "the tolerance is counted in the window"
    # with a read-back, the evidence at D + tolerance ends it where it was read
    proven = Rig({"valve": declaration("ref_l2")})
    begun = proven.clock.now
    proven.pulse("valve", 1_000)
    run = reservation_of(proven)
    proven.advance(1_100)
    assert run.ended_ms == begun + 1_050


@pytest.mark.parametrize("plugin", ["ref_l1", "ref_l2", "ref_l3"])
def test_sim_and_linux_end_a_remote_on_the_same_way(tmp_path, plugin):
    config = {"max_lease_ms": 600} if plugin == "ref_l3" else None
    rigs = {
        "sim": Rig({"valve": declaration(plugin, config=config)}),
        "linux": Rig(
            {"valve": declaration(plugin, config=config)},
            target="linux",
            target_options=linux_options(tmp_path),
        ),
    }
    seen = {}
    for target, rig in rigs.items():
        start = rig.clock.now
        rig.pulse("valve", 1_500)
        reservation = reservation_of(rig)
        rig.advance(1_000)
        rig.double("valve").cut_link()
        rig.advance(1_000)
        rig.double("valve").heal_link()
        rig.advance(2_000)
        trail = [
            (
                e["type"],
                e["data"].get("operation") or e["data"].get("state") or e["data"].get("why"),
            )
            for e in rig.events.to_trace()["events"]
            if e["type"].startswith("remote_") or e["type"] == "actuator_command"
        ]
        seen[target] = (trail, reservation.ended_ms - start, rig.state("valve"))
        rig.hal.close()
    assert seen["sim"] == seen["linux"]
    assert seen["sim"][2] == "off"


def test_the_remote_on_time_is_written_before_the_command_is_sent(tmp_path, monkeypatch):
    rig = Rig(
        {"valve": declaration("ref_l2")}, target="linux", target_options=linux_options(tmp_path)
    )
    state = tmp_path / "state"
    driver = rig.setup.checked.bound["valve"].driver
    real = driver.apply
    seen: list[tuple] = []

    def apply(command):
        envelope = json.loads((state / "valve.json").read_text(encoding="utf-8"))
        remote = json.loads((state / "valve.remote.json").read_text(encoding="utf-8"))
        seen.append((envelope["on_ms"], remote["off_owed"], rig.double("valve").state()))
        return real(command)

    monkeypatch.setattr(driver, "apply", apply)
    rig.pulse("valve", 1_500)
    assert seen == [([1_500], True, False)], "both records first, then the command"
    rig.hal.close()


def test_a_corrupt_record_makes_a_remote_actuator_quarantined(tmp_path):
    options = linux_options(tmp_path)
    state = tmp_path / "state"
    state.mkdir()
    (state / "valve.remote.json").write_text("{not json", encoding="utf-8")
    rig = Rig({"valve": declaration("ref_l2")}, target="linux", target_options=options)
    assert rig.state("valve") == "quarantined"
    with pytest.raises(EnvelopeRefusedError) as refused:
        rig.pulse("valve", 500)
    assert refused.value.reason == "actuator_quarantined"
    assert "state record unusable" in refused.value.why
    rig.hal.close()
    # the envelope's own record, corrupt: the window is spent (RFC-0007 §3d), on a remote name too
    (state / "valve.remote.json").unlink()
    (state / "valve.json").write_text("[]", encoding="utf-8")
    again = Rig(
        {"valve": declaration("ref_l2")}, target="linux", target_options=linux_options(tmp_path)
    )
    with pytest.raises(EnvelopeRefusedError) as spent:
        again.pulse("valve", 500)
    assert spent.value.reason == "window_unreadable"
    assert not again.double("valve").state()
    again.hal.close()
