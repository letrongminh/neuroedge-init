"""
Board capability declarations — TSK-S1-11, the HAL review under MCU constraint; the tables
and invariants of RFC-0013 (TSK-I2a-06, TSK-I2a-07).

The load-bearing assertion is target parity: a `sim` profile must not offer anything the
board it mirrors lacks (`SIM_MIRRORS`), or an agent could pass in simulation and fail to
build for hardware, and the target-equivalence claim (A2) would be hollow.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from neuroedge.errors import BoardCapabilityError
from neuroedge.hal.board import (
    ALL_PRIMITIVES,
    BOARD_SCHEMA,
    EXTENSION_PRIMITIVES,
    EXTENSION_REFERENCE_BOARDS,
    PRIMITIVES,
    REFERENCE_BOARD,
    REFERENCE_BOARDS,
    SIM_MIRRORS,
    SUPPORTED_TARGETS,
    BoardProfile,
    available_boards,
    load_board,
    load_board_by_id,
    load_board_document,
    validate_board_document,
)

EXPECTED_PROFILES = {"sim-default", "sim-rpi5", "esp32s3-box-3", "linux-rpi5"}
# Every board that stands for a tier-1 target in full: the five core primitives and the
# shared pin names are mandatory on all of them (RFC-0013 §3a, §3b).
FULL_REFERENCE_BOARDS = sorted(
    {b for boards in REFERENCE_BOARDS.values() for b in boards} - EXTENSION_REFERENCE_BOARDS
)


def test_at_least_one_profile_exists_per_supported_target(boards_dir):
    """RFC-0013 §3b replaces "exactly one": a target may have several reference boards."""
    assert {p.stem for p in boards_dir.glob("*.toml")} == EXPECTED_PROFILES
    boards = available_boards()
    assert {b.target for b in boards} == set(SUPPORTED_TARGETS)
    assert all(b.target in SUPPORTED_TARGETS for b in boards)


def test_the_reference_tables_name_real_profiles_of_the_right_target(boards_dir):
    """Every id in `REFERENCE_BOARDS` / `EXTENSION_REFERENCE_BOARDS` has a profile, and back."""
    assert set(REFERENCE_BOARDS) == set(SUPPORTED_TARGETS)
    listed = {b for boards in REFERENCE_BOARDS.values() for b in boards}
    assert listed | EXTENSION_REFERENCE_BOARDS == EXPECTED_PROFILES
    for target, ids in REFERENCE_BOARDS.items():
        assert ids, f"{target} has no reference board"
        for board_id in ids:
            assert load_board_by_id(board_id).target == target
    assert listed >= EXTENSION_REFERENCE_BOARDS
    assert EXTENSION_REFERENCE_BOARDS.isdisjoint({ids[0] for ids in REFERENCE_BOARDS.values()}), (
        "an extension reference board is never the default of its target (RFC-0013 §3b)"
    )


def test_the_default_board_of_each_target_is_the_first_reference_board():
    """`REFERENCE_BOARD` stays as the old spelling of the default (RFC-0013 §3b)."""
    assert {t: ids[0] for t, ids in REFERENCE_BOARDS.items()} == REFERENCE_BOARD
    assert REFERENCE_BOARD == {
        "sim": "sim-default",
        "linux": "linux-rpi5",
        "esp32s3": "esp32s3-box-3",
    }


@pytest.mark.parametrize("stem", sorted(EXPECTED_PROFILES))
def test_profile_validates_against_board_schema(boards_dir, stem):
    board = load_board(boards_dir / f"{stem}.toml")
    validate_board_document(board.to_document(), label=stem)


@pytest.mark.parametrize("board_id", FULL_REFERENCE_BOARDS)
def test_every_full_reference_board_declares_all_five_core_primitives(board_id):
    """FR-HAL-01, RFC-0013 §3a: the core set is closed, and every full reference board has it."""
    assert load_board_by_id(board_id).missing_primitives(PRIMITIVES) == []


@pytest.mark.parametrize("target", SUPPORTED_TARGETS)
def test_the_default_board_of_each_target_declares_all_five_core_primitives(target):
    """The default board is never exempt, whatever `EXTENSION_REFERENCE_BOARDS` holds."""
    default = REFERENCE_BOARDS[target][0]
    assert default not in EXTENSION_REFERENCE_BOARDS
    assert load_board_by_id(default).missing_primitives(PRIMITIVES) == []


def test_profile_filename_matches_its_declared_id(boards_dir):
    """`load_board_by_id` keys off the filename, so the two must not drift."""
    for path in sorted(boards_dir.glob("*.toml")):
        assert load_board(path).id == path.stem


def test_primitive_names_accept_both_spellings():
    board = load_board_by_id("esp32s3-box-3")
    assert board.supports("digital.out") and board.supports("digital_out")
    assert board.capability("audio.in") == board.capability("audio_in")


def test_unknown_primitive_is_refused_and_the_message_lists_every_primitive():
    """The text is generated from the two lists, so it cannot go stale when one grows."""
    board = load_board_by_id("sim-default")
    with pytest.raises(BoardCapabilityError) as excinfo:
        board.supports("network.out")
    why = excinfo.value.why
    assert "not one of the HAL primitives" in why
    assert all(name in why for name in ALL_PRIMITIVES)


def test_both_primitive_sets_are_queryable_in_both_spellings():
    board = load_board_by_id("linux-rpi5")
    assert board.supports("digital.in") and board.supports("digital_in")
    assert board.supports("vision.in") and board.supports("vision_in")
    assert board.capability("analog.in") == board.capability("analog_in")
    bare = load_board_by_id("esp32s3-box-3")
    assert bare.missing_primitives(("audio.in", "vision.in", "motion")) == ["vision.in", "motion"]


def test_the_primitive_sets_are_disjoint_and_ordered_core_first():
    assert set(PRIMITIVES).isdisjoint(EXTENSION_PRIMITIVES)
    assert ALL_PRIMITIVES == PRIMITIVES + EXTENSION_PRIMITIVES
    assert EXTENSION_PRIMITIVES == ("digital.in", "i2c", "analog.in", "motion", "vision.in")


# --- Target parity: the property that makes equivalence meaningful --------

MIRROR_PAIRS = sorted(SIM_MIRRORS.items())


def _declared(board: BoardProfile) -> dict[str, set[str]]:
    """What a board offers, as sets of names, comparable pairwise (sim ⊆ mirrored)."""
    return {
        "primitives": {p for p in ALL_PRIMITIVES if board.supports(p)},
        "pins": set(board.pins),
        "sensors": set(board.sensors),
        "input pins": set(board.input_pins),
        "pwm pins": set(board.pwm_pins),
        "signal pins": set(board.signal_pins),
        "enable pins": set(board.enable_pins),
        "i2c devices": {
            (bus["id"], d["name"], d["address"]) for bus in board.i2c_buses for d in bus["devices"]
        },
        "i2c registers": {
            (bus["id"], d["address"], r)
            for bus in board.i2c_buses
            for d in bus["devices"]
            for r in d.get("readable_registers", ())
        },
        "analog channels": {(c["name"], c["unit"]) for c in board.analog_channels},
        "motion channels": {(c["kind"], c["name"]) for c in board.motion_channels},
        "camera modes": {tuple(sorted(m.items())) for m in board.vision_modes},
    }


def _excess_over(sim: BoardProfile, mirrored: BoardProfile) -> dict[str, set]:
    """What `sim` offers beyond the board it mirrors; empty is the invariant."""
    sim_has, ref_has = _declared(sim), _declared(mirrored)
    return {
        kind: sim_has[kind] - ref_has[kind] for kind in sim_has if sim_has[kind] - ref_has[kind]
    }


def test_every_sim_profile_has_a_mirror_and_back():
    """`SIM_MIRRORS` is a table in core code; a profile cannot declare its own (RFC-0013 §3d)."""
    sim_profiles = {b.id for b in available_boards() if b.target == "sim"}
    assert set(SIM_MIRRORS) == sim_profiles
    for sim_id, mirrored_id in SIM_MIRRORS.items():
        assert load_board_by_id(mirrored_id).target != "sim", f"{sim_id} must mirror a real board"
        assert mirrored_id in {b for ids in REFERENCE_BOARDS.values() for b in ids}


@pytest.mark.parametrize(("sim_id", "mirrored_id"), MIRROR_PAIRS)
def test_sim_offers_no_pin_the_reference_board_lacks(sim_id, mirrored_id):
    sim, mirrored = load_board_by_id(sim_id), load_board_by_id(mirrored_id)
    assert set(sim.pins) <= set(mirrored.pins), (
        f"{sim_id} must not expose pins {mirrored_id} cannot drive"
    )


@pytest.mark.parametrize(("sim_id", "mirrored_id"), MIRROR_PAIRS)
def test_sim_offers_no_sensor_the_reference_board_lacks(sim_id, mirrored_id):
    sim, mirrored = load_board_by_id(sim_id), load_board_by_id(mirrored_id)
    assert set(sim.sensors) <= set(mirrored.sensors)


@pytest.mark.parametrize(("sim_id", "mirrored_id"), MIRROR_PAIRS)
def test_a_sim_profile_is_never_richer_than_the_board_it_mirrors(sim_id, mirrored_id):
    """RFC-0013 §3d, per pair: primitives, pins, buses, channels and camera modes."""
    excess = _excess_over(load_board_by_id(sim_id), load_board_by_id(mirrored_id))
    assert excess == {}, f"{sim_id} offers more than {mirrored_id}: {excess}"


@pytest.mark.parametrize(("sim_id", "mirrored_id"), MIRROR_PAIRS)
def test_a_sim_profile_keeps_the_limits_of_the_board_it_mirrors(sim_id, mirrored_id):
    """Looser limits in simulation would let a gate pass there and be refused on hardware."""
    sim, mirrored = load_board_by_id(sim_id), load_board_by_id(mirrored_id)
    shared = (set(sim.pins) | {c["name"] for c in sim.motion_channels}) & (
        set(mirrored.pins) | {c["name"] for c in mirrored.motion_channels}
    )
    for name in shared:
        assert sim.envelope(name) == mirrored.envelope(name), name
    for key in ("pwm", "feedback"):
        shared_block = sim.capability("digital.out").get(key)
        if shared_block is not None:
            assert shared_block == mirrored.capability("digital.out").get(key)
    for primitive in ("motion", "vision.in"):
        if sim.supports(primitive):
            for field in ("tolerance", "motor", "servo"):
                assert sim.capability(primitive).get(field) == mirrored.capability(primitive).get(
                    field
                ), (primitive, field)


def test_the_mirror_invariant_is_red_when_a_sim_profile_is_richer():
    """Counter-proof (RFC-0013 §7): the check fails for a `sim` that declares what its mirror lacks."""
    sim, mirrored = load_board_by_id("sim-default"), load_board_by_id("esp32s3-box-3")
    assert _excess_over(sim, mirrored) == {}
    camera = load_board_by_id("sim-rpi5").capability("vision.in")
    richer = dataclasses.replace(sim, capabilities={**sim.capabilities, "vision_in": camera})
    assert _excess_over(richer, mirrored) == {
        "primitives": {"vision.in"},
        "camera modes": {tuple(sorted(m.items())) for m in camera["modes"]},
    }
    wider_pins = {**sim.capabilities["digital_out"], "pins": [*sim.pins, "siren"]}
    wider = dataclasses.replace(sim, capabilities={**sim.capabilities, "digital_out": wider_pins})
    assert _excess_over(wider, mirrored) == {"pins": {"siren"}}


def test_sim_default_carries_no_extension_the_box_3_lacks():
    """RFC-0013 §9 item 5: `sim-default` mirrors the Box-3 and adds nothing to it."""
    sim, box = load_board_by_id("sim-default"), load_board_by_id("esp32s3-box-3")
    assert {p for p in EXTENSION_PRIMITIVES if sim.supports(p)} <= {
        p for p in EXTENSION_PRIMITIVES if box.supports(p)
    }


def _core_pins(board: BoardProfile) -> set[str]:
    """The pins an agent addresses on every board: all but the extension hardware's own."""
    return set(board.pins) - set(board.pwm_pins) - set(board.enable_pins)


def test_all_full_reference_boards_share_the_same_named_pins():
    """
    Agents address pins by name, so the same agent binary-equivalent source
    must resolve on every target. Divergent pin names would break replay
    across targets, which is what `neuroedge verify` compares. A PWM channel and the
    enable lines of PWM and motion channels exist only on a board that has that
    hardware, so they are the one thing allowed to differ (RFC-0013 §3b).
    """
    pin_sets = {b: _core_pins(load_board_by_id(b)) for b in FULL_REFERENCE_BOARDS}
    assert len(set(map(frozenset, pin_sets.values()))) == 1, pin_sets


@pytest.mark.parametrize("board_id", FULL_REFERENCE_BOARDS)
def test_extension_pins_are_declared_digital_out_pins(board_id):
    board = load_board_by_id(board_id)
    assert set(board.pwm_pins) | set(board.enable_pins) <= set(board.pins)


@pytest.mark.parametrize(("sim_id", "mirrored_id"), MIRROR_PAIRS)
def test_sim_audio_matches_the_reference_sample_rate(sim_id, mirrored_id):
    """A rate mismatch would silently change VAD and wake-word behaviour."""
    sim = load_board_by_id(sim_id).capability("audio.in")
    ref = load_board_by_id(mirrored_id).capability("audio.in")
    assert sim["sample_rate_hz"] == ref["sample_rate_hz"]
    assert sim["channels"] <= ref["channels"], "sim must not offer more channels"
    assert not (sim["aec"] and not ref["aec"]), "sim must not offer AEC the board lacks"


def test_the_box_3_and_sim_default_sample_at_16_khz():
    sim = load_board_by_id("sim-default").capability("audio.in")
    box = load_board_by_id("esp32s3-box-3").capability("audio.in")
    assert sim["sample_rate_hz"] == box["sample_rate_hz"] == 16000


# --- Safety envelopes of the tier-1 profiles (RFC-0007 §3d, §4) ------------


@pytest.mark.parametrize("board_id", sorted(EXPECTED_PROFILES))
def test_every_digital_out_pin_has_an_envelope_unless_declared_otherwise(board_id):
    """A signal pin carries no load and an enable pin is bounded by the channel it serves."""
    board = load_board_by_id(board_id)
    exempt = set(board.signal_pins) | set(board.enable_pins)
    for pin in board.pins:
        if pin not in exempt:
            assert board.envelope(pin) is not None, f"{board_id}: {pin} has no envelope"
    for channel in board.motion_channels:
        assert board.envelope(channel["name"]) is not None, channel["name"]


@pytest.mark.parametrize("board_id", sorted(EXPECTED_PROFILES))
def test_the_envelopes_are_wide_enough_for_the_canonical_traces(board_id, traces_dir):
    """The three canonical traces must replay unchanged: no recorded pulse may exceed its pin's cap."""
    board = load_board_by_id(board_id)
    pulses = 0
    for path in sorted(traces_dir.glob("*.json")):
        for event in json.loads(path.read_text(encoding="utf-8"))["events"]:
            if event["type"] != "actuator_command":
                continue
            data = event["data"]
            envelope = board.envelope(data["pin"])
            assert envelope is not None, f"{board_id}: {data['pin']} has no envelope"
            assert data.get("duration_ms", 0) <= envelope["max_continuous_ms"], (
                f"{path.name}: {data} exceeds the envelope of {board_id}"
            )
            pulses += 1
    assert pulses, "no actuator command found in the canonical traces: nothing was checked"
    assert board.envelope("door_lock")["max_continuous_ms"] >= 30000  # RFC-0007 §4


# --- The extension primitives on every tier-1 target (RFC-0013 §3c, §9 item 5) ---

_EXTENSION_HAS = {
    "digital.in": lambda b: b.supports("digital.in"),
    "i2c": lambda b: b.supports("i2c"),
    "pwm": lambda b: bool(b.pwm_pins),  # a block of digital.out, not a primitive of its own
    "analog.in": lambda b: b.supports("analog.in"),
    "motion": lambda b: b.supports("motion"),
    "vision.in": lambda b: b.supports("vision.in"),
}
_NO_CAMERA = ("digital.in", "i2c", "pwm", "analog.in", "motion")
# The table of RFC-0013 §9 item 5: which board carries which primitive. Each cell is its own
# assertion; a cell the hardware does not allow means opening a `Q-N`, not dropping the cell.
_CELLS: set[tuple[str, str]] = (
    {(what, board) for what in _NO_CAMERA for board in ("sim-default", "sim-rpi5", "linux-rpi5")}
    | {(what, "esp32s3-box-3") for what in _NO_CAMERA}
    | {("vision.in", "sim-rpi5"), ("vision.in", "linux-rpi5"), ("vision.in", "esp32s3-cores3")}
)
# Cells that cannot be declared yet, because filling them needs facts only the hardware gives
# (CONTRIBUTING.md §3): the dock pins, ADC channel and motor driver of the Box-3, the whole
# CoreS3 profile (TSK-I3a-01). `sim-default` waits with the Box-3 it mirrors. The board keeps
# no key meanwhile — never a placeholder — and the test below fails the day a cell is filled,
# so this set can only shrink.
_AWAITING_HARDWARE: frozenset[tuple[str, str]] = frozenset(
    {(what, "esp32s3-box-3") for what in _NO_CAMERA}
    | {(what, "sim-default") for what in _NO_CAMERA}
    | {("vision.in", "esp32s3-cores3")}
)


@pytest.mark.parametrize(("what", "board_id"), sorted(_CELLS))
def test_each_cell_of_the_extension_table_is_declared_by_its_board(what, board_id, boards_dir):
    """A filled cell: the board declares it. An awaiting cell: it must still not, or shrink the set."""
    awaiting = (what, board_id) in _AWAITING_HARDWARE
    if not (boards_dir / f"{board_id}.toml").is_file():
        assert awaiting, f"{board_id} has no profile and its {what} cell is not awaiting hardware"
        return
    has = _EXTENSION_HAS[what](load_board_by_id(board_id))
    if awaiting:
        assert not has, f"{board_id} now declares {what}: remove the cell from _AWAITING_HARDWARE"
    else:
        assert has, f"{board_id} must declare {what} (RFC-0013 §9 item 5)"


def test_the_awaiting_cells_are_cells_of_the_table():
    assert _AWAITING_HARDWARE <= _CELLS


def test_every_extension_primitive_on_every_tier1_target():
    """
    RFC-0013 §3c: each extension primitive (and PWM) is on at least one reference board of
    each tier-1 target. Complete for `sim` and `linux`. For `esp32s3` every cell awaits
    hardware facts (TSK-I3a-01), so the gap is pinned exactly: the day a cell is filled this
    fails, and the list shrinks. A gap anywhere else is a bug.
    """
    gaps = {
        (what, target)
        for target, ids in REFERENCE_BOARDS.items()
        for what, has in _EXTENSION_HAS.items()
        if not any(has(load_board_by_id(b)) for b in ids)
    }
    assert gaps == {(what, "esp32s3") for what in _EXTENSION_HAS}, (
        "extension primitives missing from a tier-1 target: "
        f"{sorted(gaps)} (esp32s3 is expected to be the only target with gaps, until TSK-I3a-01)"
    )


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


def test_an_agent_never_drives_the_enable_line_of_a_pwm_or_motion_channel():
    """RFC-0010 §3a: enable pins are the HAL's; the refusal comes before any token is spent."""
    board = load_board_by_id("linux-rpi5")
    for pin in ("fan_en", "motor_en", "servo_en"):
        assert pin in board.pins
        with pytest.raises(BoardCapabilityError) as excinfo:
            board.require_pin(pin, called_from="actions/fan.py:3")
        assert "enable line" in excinfo.value.why
        assert "actions/fan.py:3" in excinfo.value.where
    board.require_pin("fan")  # the channel itself is addressable


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


# --- the declaration-format version key (RFC-0015 §3c, PR B) ----------------------------------------


@pytest.mark.parametrize("stem", sorted(EXPECTED_PROFILES))
def test_every_shipped_board_declares_its_schema(boards_dir, stem):
    """The shipped profiles teach the key: each declares `schema` at its root."""
    import tomllib

    document = tomllib.loads((boards_dir / f"{stem}.toml").read_text(encoding="utf-8"))
    assert document["schema"] == BOARD_SCHEMA == "neuroedge.board/v1"


def test_a_board_without_a_schema_key_is_read_as_v1(boards_dir, tmp_path):
    text = (boards_dir / "sim-default.toml").read_text(encoding="utf-8")
    stripped = text.replace('schema = "neuroedge.board/v1"\n', "")
    assert stripped != text
    path = tmp_path / "sim-default.toml"
    path.write_text(stripped, encoding="utf-8")
    assert "schema" not in load_board_document(path)
    assert load_board(path).to_document()["schema"] == "neuroedge.board/v1"


@pytest.mark.parametrize("declared", ["neuroedge.board/v2", "neuroedge.gate/v1", "rubbish", 1])
def test_a_board_with_a_schema_key_of_another_version_is_refused_before_validation(
    boards_dir, tmp_path, declared
):
    """Refused with NE3001 and the way out, before the open v1 schema can accept the file."""
    text = (boards_dir / "sim-default.toml").read_text(encoding="utf-8")
    value = f'"{declared}"' if isinstance(declared, str) else str(declared)
    path = tmp_path / "sim-default.toml"
    # A key the v1 schema would reject on its own: the version check must fire first.
    path.write_text(
        text.replace('schema = "neuroedge.board/v1"', f"schema = {value}\nnonsense = 1"),
        encoding="utf-8",
    )
    with pytest.raises(BoardCapabilityError) as caught:
        load_board_document(path)
    error = caught.value
    assert error.code == "NE3001"
    assert error.where.endswith("-> schema")
    assert repr(declared) in error.why and "neuroedge.board/v1" in error.why
    assert "upgrade neuroedge" in error.how


def test_a_board_document_in_memory_is_refused_for_another_version_too(boards_dir):
    document = load_board(boards_dir / "sim-default.toml").to_document()
    document["schema"] = "neuroedge.board/v2"
    with pytest.raises(BoardCapabilityError, match="neuroedge.board/v2"):
        validate_board_document(document, label="memory")


@pytest.mark.parametrize("stem", sorted(EXPECTED_PROFILES))
def test_board_to_document_round_trips_the_schema_key(boards_dir, stem, tmp_path):
    import tomllib

    path = boards_dir / f"{stem}.toml"
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    document = load_board(path).to_document()
    assert document["schema"] == raw["schema"]
    assert {k: document[k] for k in ("schema", "board", "capabilities")} == {
        k: raw[k] for k in ("schema", "board", "capabilities")
    }
    validate_board_document(document, label=stem)
