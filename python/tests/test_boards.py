"""
Board capability declarations — TSK-S1-11, the HAL review under MCU constraint.

The load-bearing assertion is target parity: `sim` must not offer a primitive
the reference board lacks, or an agent could pass in simulation and fail to
build for hardware, and the target-equivalence claim (A2) would be hollow.
"""

from __future__ import annotations

import pytest

from neuroedge.errors import BoardCapabilityError
from neuroedge.hal.board import (
    PRIMITIVES,
    SUPPORTED_TARGETS,
    available_boards,
    load_board,
    load_board_by_id,
    validate_board_document,
)

EXPECTED_PROFILES = {"sim-default", "esp32s3-box-3", "linux-rpi5"}


def test_one_profile_exists_per_supported_target(boards_dir):
    assert {p.stem for p in boards_dir.glob("*.toml")} == EXPECTED_PROFILES
    assert {b.target for b in available_boards()} == set(SUPPORTED_TARGETS)


@pytest.mark.parametrize("stem", sorted(EXPECTED_PROFILES))
def test_profile_validates_against_board_schema(boards_dir, stem):
    board = load_board(boards_dir / f"{stem}.toml")
    validate_board_document(board.to_document(), label=stem)


@pytest.mark.parametrize("stem", sorted(EXPECTED_PROFILES))
def test_every_profile_declares_all_five_primitives(boards_dir, stem):
    """FR-HAL-01: the primitive set is closed, and every target implements it."""
    board = load_board(boards_dir / f"{stem}.toml")
    assert board.missing_primitives(PRIMITIVES) == []


def test_profile_filename_matches_its_declared_id(boards_dir):
    """`load_board_by_id` keys off the filename, so the two must not drift."""
    for path in sorted(boards_dir.glob("*.toml")):
        assert load_board(path).id == path.stem


def test_primitive_names_accept_both_spellings():
    board = load_board_by_id("esp32s3-box-3")
    assert board.supports("digital.out") and board.supports("digital_out")
    assert board.capability("audio.in") == board.capability("audio_in")


def test_unknown_primitive_is_refused():
    board = load_board_by_id("sim-default")
    with pytest.raises(BoardCapabilityError) as excinfo:
        board.supports("network.out")
    assert "not one of the five HAL primitives" in excinfo.value.why


# --- Target parity: the property that makes equivalence meaningful --------


def test_sim_offers_no_pin_the_reference_board_lacks():
    sim = load_board_by_id("sim-default")
    box = load_board_by_id("esp32s3-box-3")
    assert set(sim.pins) <= set(box.pins), (
        "sim must not expose pins the reference board cannot drive"
    )


def test_sim_offers_no_sensor_the_reference_board_lacks():
    sim = load_board_by_id("sim-default")
    box = load_board_by_id("esp32s3-box-3")
    assert set(sim.sensors) <= set(box.sensors)


def test_all_three_targets_share_the_same_named_pins():
    """
    Agents address pins by name, so the same agent binary-equivalent source
    must resolve on every target. Divergent pin names would break replay
    across targets, which is what `neuroedge verify` compares.
    """
    pin_sets = {b.id: set(b.pins) for b in available_boards()}
    assert len(set(map(frozenset, pin_sets.values()))) == 1, pin_sets


def test_sim_audio_matches_the_reference_sample_rate():
    """A rate mismatch would silently change VAD and wake-word behaviour."""
    sim = load_board_by_id("sim-default").capability("audio.in")
    box = load_board_by_id("esp32s3-box-3").capability("audio.in")
    assert sim["sample_rate_hz"] == box["sample_rate_hz"] == 16000


# --- Capability errors carry the three mandated parts (FR-HAL-05) --------


def test_missing_pin_error_names_pin_alternatives_and_caller():
    board = load_board_by_id("esp32s3-box-3")
    with pytest.raises(BoardCapabilityError) as excinfo:
        board.require_pin("front_door", called_from="actions/unlock.py:42")
    error = excinfo.value
    assert "front_door" in error.where
    assert "actions/unlock.py:42" in error.where  # where the call came from
    assert "door_lock" in error.why  # what the board does offer
    assert "digital_out].pins" in error.how  # how to resolve it


def test_missing_sensor_error_names_alternatives():
    board = load_board_by_id("linux-rpi5")
    with pytest.raises(BoardCapabilityError) as excinfo:
        board.require_sensor("co2", called_from="actions/ventilate.py:8")
    assert "co2" in excinfo.value.where
    assert "temperature" in excinfo.value.why


def test_declared_pin_is_accepted():
    load_board_by_id("esp32s3-box-3").require_pin("door_lock")


def test_unknown_board_id_lists_what_is_available():
    with pytest.raises(BoardCapabilityError) as excinfo:
        load_board_by_id("esp32s3-devkitc")
    assert "esp32s3-box-3" in excinfo.value.why


def test_reference_board_is_the_box_3_not_a_devkit():
    """Q-1/Q-2 fixed the reference board; a silent swap would invalidate the spike."""
    board = load_board_by_id("esp32s3-box-3")
    assert board.target == "esp32s3"
    assert board.mcu == "esp32s3"
    assert "BOX-3" in board.name


# --- Malformed declarations ----------------------------------------------


def test_malformed_toml_is_reported(tmp_path):
    path = tmp_path / "broken.toml"
    path.write_text("[board\nid = 'x'", encoding="utf-8")
    with pytest.raises(BoardCapabilityError) as excinfo:
        load_board(path)
    assert "not valid TOML" in excinfo.value.why


def test_declaration_missing_required_field_is_reported(tmp_path):
    path = tmp_path / "incomplete.toml"
    path.write_text('[board]\nid = "x"\ntarget = "sim"\n\n[capabilities]\n', encoding="utf-8")
    with pytest.raises(BoardCapabilityError) as excinfo:
        load_board(path)
    assert "mcu" in excinfo.value.why


def test_unsupported_target_is_reported(tmp_path):
    path = tmp_path / "rp2040.toml"
    path.write_text(
        '[board]\nid = "pico"\ntarget = "rp2040"\nmcu = "rp2040"\n\n[capabilities]\n',
        encoding="utf-8",
    )
    with pytest.raises(BoardCapabilityError) as excinfo:
        load_board(path)
    assert "rp2040" in excinfo.value.why
