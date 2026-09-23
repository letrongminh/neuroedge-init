"""
TSK-S3-03 — the Action CI assertion library and `neuroedge test` (FR-CI-03, FR-CLI-03).

Each assertion must pass on the session that satisfies it and raise an
`AssertionError` carrying the evidence on the one that does not.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import neuroedge
from neuroedge.engine.trace_sink import EventLog
from neuroedge.hal.sim import SimHAL
from neuroedge.sim import SimSession
from neuroedge.testing import (
    assert_action_aborted,
    assert_escalated_to,
    assert_gate_allowed,
    assert_gate_blocked,
    assert_never_pulsed,
    assert_pin_pulsed,
    replay,
)


@pytest.fixture(scope="module")
def happy(traces_dir):
    return replay(traces_dir / "happy-path.json")


@pytest.fixture(scope="module")
def unverified(traces_dir):
    return replay(traces_dir / "unverified_attempt.json")


@pytest.fixture(scope="module")
def offline(traces_dir):
    return replay(traces_dir / "network_offline.json")


# --- gate verdicts ------------------------------------------------------------------


def test_allowed_passes_on_allow_and_fails_on_block(happy, unverified):
    assert_gate_allowed(happy, "unlock_door")
    assert_gate_allowed(happy, "unlock_door@1.2.0")
    with pytest.raises(AssertionError, match="never allowed.*BLOCK"):
        assert_gate_allowed(unverified, "unlock_door")


def test_blocked_passes_on_block_and_checks_the_reason(unverified, offline, happy):
    assert_gate_blocked(unverified, "unlock_door")
    assert_gate_blocked(unverified, "unlock_door", reason="condition_not_met")
    assert_gate_blocked(offline, "unlock_door", reason="gate_unreachable")
    with pytest.raises(AssertionError, match="reason 'condition_not_met', not 'gate_unreachable'"):
        assert_gate_blocked(unverified, "unlock_door", reason="gate_unreachable")
    with pytest.raises(AssertionError, match="allowed 1 of 1"):
        assert_gate_blocked(happy, "unlock_door")


def test_blocked_fails_when_the_gate_was_never_evaluated(unverified):
    with pytest.raises(AssertionError, match="never evaluated"):
        assert_gate_blocked(unverified, "order_food")


def test_escalated_to(unverified, offline):
    assert_escalated_to(unverified, "human_receptionist")
    with pytest.raises(AssertionError, match="night_duty_manager"):
        assert_escalated_to(unverified, "night_duty_manager")
    with pytest.raises(AssertionError):
        assert_escalated_to(offline, "human_receptionist")  # a degraded block escalates to no one


# --- pins ---------------------------------------------------------------------------


def test_pin_pulsed(happy, unverified):
    assert_pin_pulsed(happy, "door_lock")
    assert_pin_pulsed(happy, "door_lock", duration_ms=30000, times=1)
    with pytest.raises(AssertionError, match="none 5000 ms"):
        assert_pin_pulsed(happy, "door_lock", duration_ms=5000)
    with pytest.raises(AssertionError, match="never pulsed"):
        assert_pin_pulsed(unverified, "door_lock")


def test_never_pulsed(happy, unverified):
    assert_never_pulsed(unverified, "door_lock")
    with pytest.raises(AssertionError, match="was driven"):
        assert_never_pulsed(happy, "door_lock")


def test_a_misspelled_pin_raises_instead_of_passing(unverified):
    with pytest.raises(Exception, match="door_lok"):
        assert_never_pulsed(unverified, "door_lok")


def test_action_aborted():
    events = EventLog()
    # The authoriser is opened here only to get a PendingCommand to cancel (RB-3).
    hal = SimHAL(events=events, authorize=lambda *_: None)
    subject = {"events": events.events}
    pending = hal.digital_out("door_lock", "pulse", 30000)
    with pytest.raises(AssertionError, match="no abort"):
        assert_action_aborted(subject, "door_lock")
    pending.cancel()
    assert_action_aborted(subject, "door_lock")
    with pytest.raises(AssertionError):
        assert_action_aborted(subject, "door_lock", reason="SOMETHING_ELSE")


async def test_assertions_accept_a_live_session_a_trace_dict_and_a_hal(root, happy):
    session = SimSession.load(root / "fixtures" / "agents" / "villa-concierge" / "agent.toml")
    await session.handle("mở cửa phòng 202")
    assert_gate_blocked(session, "unlock_door", reason="condition_not_met")
    assert_never_pulsed(session, "door_lock")
    assert_gate_allowed(happy.replayed, "unlock_door")
    assert_never_pulsed(happy.hal, "porch_light")


# --- L3 ------------------------------------------------------------------------------


def test_text_is_refused_where_a_session_is_expected():
    with pytest.raises(AssertionError, match="L3"):
        assert_gate_allowed("Door unlocked. Welcome home.", "unlock_door")
    with pytest.raises(AssertionError, match="L3"):
        assert_never_pulsed("Door unlocked.", "door_lock")


def test_replies_are_off_limits(happy):
    with pytest.raises(AssertionError, match="L3"):
        _ = happy.replies


# --- neuroedge test -----------------------------------------------------------------


def _neuroedge_test(path: Path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = str(Path(neuroedge.__file__).resolve().parents[1])
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from neuroedge.cli.main import app; app()",
            "test",
            str(path),
            "--pytest-arg=-p",
            "--pytest-arg=no:cacheprovider",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


PASSING = """
from neuroedge.testing import replay, assert_gate_blocked, assert_never_pulsed

def test_unverified_guest_is_blocked():
    result = replay("unverified_attempt.json")
    assert_gate_blocked(result, "unlock_door")
    assert_never_pulsed(result, "door_lock")
"""

FAILING = """
from neuroedge.testing import replay, assert_never_pulsed

def test_this_claim_is_false():
    assert_never_pulsed(replay("happy-path.json"), "door_lock")
"""


def test_neuroedge_test_exits_zero_when_every_test_passes(tmp_path):
    (tmp_path / "test_ok.py").write_text(PASSING, encoding="utf-8")
    result = _neuroedge_test(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout


def test_neuroedge_test_exits_one_when_a_safety_assertion_fails(tmp_path):
    (tmp_path / "test_ok.py").write_text(PASSING, encoding="utf-8")
    (tmp_path / "test_bad.py").write_text(FAILING, encoding="utf-8")
    result = _neuroedge_test(tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "was driven" in result.stdout


def test_neuroedge_test_exits_one_when_nothing_is_collected(tmp_path):
    result = _neuroedge_test(tmp_path)
    assert result.returncode == 1
    assert "no tests collected" in result.stderr
