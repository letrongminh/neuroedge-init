"""
Board declaration conformance, valid and invalid — the board half of the RFC-0007, 0010,
0011, 0012 and 0013 counter-example evidence.

Every invalid fixture is the valid example with one change (a second pin or channel where
the rule needs one), so a diagnostic is about that change and nothing else. The corpus is
closed both ways (CONTRIBUTING.md §3): each file has an entry in `expected_errors.yaml` and
each entry has a file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from neuroedge.errors import BoardCapabilityError
from neuroedge.hal.board import EXTENSION_PRIMITIVES, PRIMITIVES, load_board

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "boards"
VALID = sorted((_FIXTURES / "valid").glob("*.toml"))
INVALID = sorted((_FIXTURES / "invalid").glob("*.toml"))


@pytest.mark.parametrize("path", VALID, ids=[p.name for p in VALID])
def test_valid_board_fixture_loads(path):
    board = load_board(path)
    assert board.id == path.stem


def test_the_valid_example_declares_every_extension_key():
    """The example stays the one place that shows each new key, so a new key must join it."""
    board = load_board(_FIXTURES / "valid" / "all-extensions.toml")
    assert board.missing_primitives(PRIMITIVES + EXTENSION_PRIMITIVES) == []
    digital = board.capability("digital.out")
    assert {"signal_pins", "envelope", "pwm", "feedback"} <= set(digital)
    assert board.signal_pins == ("status_led",)
    assert board.pwm_pins == ("fan",)
    assert board.enable_pins == ("fan_en", "motor_en", "servo_en")
    assert board.input_pins == ("button_boot", "door_contact_raw")
    assert {c["kind"] for c in board.motion_channels} == {"motor", "servo"}
    assert board.envelope("door_lock") is not None
    assert board.envelope("wheel_left") is not None
    assert board.envelope("status_led") is None, "a signal pin has no envelope"
    assert board.envelope("fan_en") is None, "an enable pin has no envelope of its own"
    assert len(board.vision_modes) == 2


def test_a_board_without_extensions_stays_valid():
    board = load_board(_FIXTURES / "valid" / "core-only.toml")
    assert board.missing_primitives(EXTENSION_PRIMITIVES) == list(EXTENSION_PRIMITIVES)
    assert board.signal_pins == ("status_led",)


def test_every_invalid_board_has_a_recorded_expectation(expected_board_errors):
    documented = set(expected_board_errors)
    present = {p.name for p in INVALID}
    assert present - documented == set(), (
        f"fixtures without a recorded expected error: {sorted(present - documented)}"
    )
    assert documented - present == set(), (
        f"expectations with no fixture: {sorted(documented - present)}"
    )


@pytest.mark.parametrize("path", INVALID, ids=[p.name for p in INVALID])
def test_invalid_board_fails_as_recorded(path, expected_board_errors):
    expectation = expected_board_errors[path.name]
    with pytest.raises(BoardCapabilityError) as excinfo:
        load_board(path)
    error = excinfo.value
    assert error.code == "NE3001"
    assert expectation["where_contains"] in error.where
    assert expectation["why_contains"] in error.why
    assert error.how.strip(), "FR-HAL-05 requires a remediation hint"
