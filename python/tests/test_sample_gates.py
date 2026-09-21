"""
The three hand-written sample gates — Sprint 1 exit criterion 2.

> "Ba gate mẫu viết tay được công cụ phân giải đúng, gồm một trường hợp
>  kế thừa 2 cấp."

The corpus in gates/ is a three-document chain:

    base-access@1.0.0            (level 1, the hospitality baseline)
      -> unlock_door@1.2.0       (level 2, Proposal §4.5)
        -> unlock_door_night@1.0.0  (level 3 — the two-level inheritance case)

"Resolved correctly" is spelled out here as: the right criteria are inherited,
the right conditions survive tightening, the fail policy is right, and the
resolution is reproducible byte-for-byte.
"""

from __future__ import annotations

import pytest

from neuroedge.engine import gate_canonical_json, gate_digest, resolve_gate_file, resolve_gate_uri

SAMPLE_GATES = ["hospitality/base-access@1.0.0", "unlock_door@1.2.0", "unlock_door_night@1.0.0"]


@pytest.fixture(scope="module")
def base(gates_dir):
    return resolve_gate_file(gates_dir / "hospitality" / "base-access@1.0.0.yaml")


@pytest.fixture(scope="module")
def door(gates_dir):
    return resolve_gate_file(gates_dir / "unlock_door@1.2.0.yaml")


@pytest.fixture(scope="module")
def night(gates_dir):
    return resolve_gate_file(gates_dir / "unlock_door_night@1.0.0.yaml")


def test_there_are_exactly_three_sample_gates(gates_dir):
    found = sorted(p.relative_to(gates_dir).as_posix() for p in gates_dir.rglob("*.yaml"))
    assert found == sorted(f"{name}.yaml" for name in SAMPLE_GATES)


@pytest.mark.parametrize("name", SAMPLE_GATES)
def test_every_sample_gate_resolves(gates_dir, name):
    assert resolve_gate_file(gates_dir / f"{name}.yaml") is not None


# --- Level 1: the baseline -------------------------------------------------


def test_base_access_is_a_root_gate(base):
    assert base.inheritance_levels == 1
    assert base.chain == ["base-access@1.0.0"]


def test_base_access_conditions(base):
    assert base.constraints["guest_authenticated"].admitted == frozenset({"true"})
    assert base.constraints["risk_level"].admitted == frozenset({"low", "medium"})
    assert base.fails_closed is True


# --- Level 2: one level of inheritance ------------------------------------


def test_unlock_door_inherits_and_adds(door):
    assert door.inheritance_levels == 2
    assert door.chain == ["base-access@1.0.0", "unlock_door@1.2.0"]
    # Principle 1: inherited from the baseline.
    assert "guest_authenticated" in door.evaluate
    assert "risk_level" in door.evaluate
    # Principle 3: added here.
    assert door.evaluate["room_matches"]["type"] == "bool"


def test_unlock_door_tightens_inherited_risk_tolerance(door):
    """medium -> low. This is the tightening Appendix B.5 principle 2 permits."""
    assert door.constraints["risk_level"].admitted == frozenset({"low"})


def test_unlock_door_keeps_the_inherited_authentication_clause(door):
    assert door.constraints["guest_authenticated"].admitted == frozenset({"true"})


def test_unlock_door_overrides_the_latency_budget(door):
    assert door.budget == {"p95_latency_ms": 120, "fail": "closed"}


# --- Level 3: the two-level inheritance case ------------------------------


def test_night_gate_is_the_two_level_inheritance_case(night):
    """Inherits through unlock_door, which itself inherits from base-access."""
    assert night.inheritance_levels == 3
    assert night.chain == [
        "base-access@1.0.0",
        "unlock_door@1.2.0",
        "unlock_door_night@1.0.0",
    ]


def test_night_gate_accumulates_criteria_from_all_three_levels(night):
    assert set(night.evaluate) == {
        "guest_authenticated",  # level 1
        "risk_level",  # level 1
        "room_matches",  # level 2
        "staff_co_authorized",  # level 3
        "request_channel",  # level 3
    }


def test_night_gate_carries_the_grandparent_tightening_forward(night):
    """`risk_level` was narrowed at level 2 and is untouched at level 3."""
    assert night.constraints["risk_level"].admitted == frozenset({"low"})


def test_night_gate_inherits_room_matches_from_the_middle_level(night):
    assert night.constraints["room_matches"].admitted == frozenset({"true"})


def test_night_gate_raises_the_authentication_confidence_floor(night):
    constraint = night.constraints["guest_authenticated"]
    assert constraint.admitted == frozenset({"true"})
    assert constraint.confidence_floor == 0.95


def test_night_gate_restricts_the_request_channel(night):
    assert night.constraints["request_channel"].admitted == frozenset({"in_person", "app"})


def test_night_gate_escalates_to_the_night_manager(night):
    assert night.on_block["action"] == "escalate"
    assert night.on_block["to"] == "night_duty_manager"


def test_night_gate_fails_closed(night):
    assert night.fails_closed is True
    assert night.budget == {"p95_latency_ms": 90, "fail": "closed"}


# --- The chain only ever narrows -----------------------------------------


def test_conditions_narrow_monotonically_down_the_chain(base, door, night):
    """
    The product claim behind `extends`: inheriting a community gate can only
    make a device stricter. Asserted here on the real corpus, for every
    criterion each pair of levels shares.
    """
    for parent, derived in ((base, door), (door, night)):
        for criterion, parent_constraint in parent.constraints.items():
            derived_constraint = derived.constraints[criterion]
            assert derived_constraint.is_at_least_as_strict_as(parent_constraint), (
                f"{criterion} widened from {parent_constraint.describe()} "
                f"to {derived_constraint.describe()}"
            )


def test_no_sample_gate_fails_open(base, door, night):
    for gate in (base, door, night):
        assert gate.fails_closed, f"{gate.name} must deny on timeout or loss of network"


# --- Addressing and reproducibility --------------------------------------


@pytest.mark.parametrize(
    "uri, expected",
    [
        ("neuroedge://gates/hospitality/base-access@1.0.0", "base-access"),
        ("neuroedge://gates/unlock_door@1.2.0", "unlock_door"),
        ("neuroedge://gates/unlock_door_night@1.0.0", "unlock_door_night"),
    ],
)
def test_sample_gates_resolve_by_uri(uri, expected):
    assert resolve_gate_uri(uri).name == expected


def test_uri_and_path_resolution_agree(gates_dir):
    by_path = resolve_gate_file(gates_dir / "unlock_door_night@1.0.0.yaml")
    by_uri = resolve_gate_uri("neuroedge://gates/unlock_door_night@1.0.0")
    assert gate_digest(by_path) == gate_digest(by_uri)


def test_resolution_is_reproducible(gates_dir):
    """Re-resolving must produce identical canonical bytes, not merely equal objects."""
    path = gates_dir / "unlock_door_night@1.0.0.yaml"
    assert gate_canonical_json(resolve_gate_file(path)) == gate_canonical_json(
        resolve_gate_file(path)
    )


def test_each_sample_gate_has_a_distinct_digest(base, door, night):
    digests = {gate_digest(g) for g in (base, door, night)}
    assert len(digests) == 3
