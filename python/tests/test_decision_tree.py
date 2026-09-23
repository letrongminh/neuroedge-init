"""
TSK-S2-12 — host decision-tree compiler and walker.

Covers ENG-T1 (truth tables pin verdict *and* reason for the future C walker)
and ENG-T2 (recompiling is byte-identical and the tree carries the digest).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from neuroedge.engine import (
    Fact,
    GateVerdict,
    Reason,
    compile_tree,
    gate_digest,
    resolve_gate_document,
    resolve_gate_file,
    tree_bytes,
    validate_tree,
    walk,
)
from neuroedge.engine.decision_tree import facts_from_row, truth_cases, truth_table
from neuroedge.errors import GateSchemaError

SAMPLE_GATES = {
    "base-access@1.0.0": "hospitality/base-access@1.0.0.yaml",
    "unlock_door@1.2.0": "unlock_door@1.2.0.yaml",
    "unlock_door_night@1.0.0": "unlock_door_night@1.0.0.yaml",
}

ROOT_FIRST = {
    "base-access@1.0.0": ["guest_authenticated", "risk_level"],
    "unlock_door@1.2.0": ["guest_authenticated", "risk_level", "room_matches"],
    "unlock_door_night@1.0.0": [
        "guest_authenticated",
        "risk_level",
        "room_matches",
        "staff_co_authorized",
        "request_channel",
    ],
}


@pytest.fixture(scope="module")
def trees(gates_dir: Path) -> dict[str, dict]:
    return {
        key: compile_tree(resolve_gate_file(gates_dir / rel)) for key, rel in SAMPLE_GATES.items()
    }


def _load_generator(root: Path):
    spec = importlib.util.spec_from_file_location(
        "generate_truth_tables", root / "scripts" / "generate_truth_tables.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- Compilation -------------------------------------------------------------


@pytest.mark.parametrize("gate", sorted(SAMPLE_GATES))
def test_criteria_order_is_root_first(trees, gate):
    assert trees[gate]["criteria_order"] == ROOT_FIRST[gate]


def test_root_first_differs_from_lexicographic_on_the_night_gate(trees):
    order = trees["unlock_door_night@1.0.0"]["criteria_order"]
    assert order != sorted(order)


@pytest.mark.parametrize("gate", sorted(SAMPLE_GATES))
def test_recompiling_is_byte_identical_and_carries_the_digest(gates_dir, gate):
    first = resolve_gate_file(gates_dir / SAMPLE_GATES[gate])
    second = resolve_gate_file(gates_dir / SAMPLE_GATES[gate])
    assert tree_bytes(compile_tree(first)) == tree_bytes(compile_tree(second))
    assert compile_tree(first)["gate_digest"] == gate_digest(first)


def test_a_policy_change_changes_the_tree_digest(gates_dir):
    gate = resolve_gate_file(gates_dir / SAMPLE_GATES["unlock_door@1.2.0"])
    tree = compile_tree(gate)
    gate.budget["p95_latency_ms"] = 119
    assert compile_tree(gate)["gate_digest"] != tree["gate_digest"]


@pytest.mark.parametrize("gate", sorted(SAMPLE_GATES))
def test_every_sample_tree_validates(trees, gate):
    validate_tree(trees[gate], label=gate)


@pytest.mark.parametrize("field", ["schema", "criteria_order", "gate_digest"])
def test_a_tree_missing_a_required_field_is_refused(trees, field):
    broken = dict(trees["unlock_door@1.2.0"])
    del broken[field]
    with pytest.raises(GateSchemaError):
        validate_tree(broken)


def test_nodes_out_of_order_are_refused(trees):
    broken = dict(trees["unlock_door@1.2.0"])
    broken["nodes"] = list(reversed(broken["nodes"]))
    with pytest.raises(GateSchemaError) as excinfo:
        validate_tree(broken)
    assert "criteria_order" in excinfo.value.where


# --- Walking -----------------------------------------------------------------


def _oracle(gate, facts: dict[str, Fact]) -> tuple[GateVerdict, Reason | None]:
    """An independent restatement of the walk semantics, from the constraints."""
    for name, constraint in gate.constraints.items():
        definition = gate.evaluate[name]
        domain = (
            {"true", "false"}
            if constraint.kind == "bool"
            else set(definition.get("levels") or definition.get("options"))
        )
        fact = facts.get(name)
        if fact is None or fact.value is None:
            return GateVerdict.BLOCK, Reason.CRITERION_UNAVAILABLE
        if constraint.kind == "bool" and not isinstance(fact.value, bool):
            return GateVerdict.BLOCK, Reason.CRITERION_UNAVAILABLE
        key = str(fact.value).lower() if constraint.kind == "bool" else fact.value
        if key not in domain:
            return GateVerdict.BLOCK, Reason.CRITERION_UNAVAILABLE
        if constraint.confidence_floor and fact.confidence is None:
            return GateVerdict.BLOCK, Reason.CONFIDENCE_UNAVAILABLE
        if key not in constraint.admitted or (
            constraint.confidence_floor and fact.confidence < constraint.confidence_floor
        ):
            return GateVerdict.BLOCK, Reason.CONDITION_NOT_MET
    return GateVerdict.ALLOW, None


@pytest.mark.parametrize("gate", sorted(SAMPLE_GATES))
def test_walk_matches_the_oracle_on_every_truth_row(gates_dir, gate):
    resolved = resolve_gate_file(gates_dir / SAMPLE_GATES[gate])
    tree = compile_tree(resolved)
    for row in truth_cases(tree):
        facts = facts_from_row(row)
        result = walk(tree, facts)
        assert (result.verdict, result.reason) == _oracle(resolved, facts), row


@pytest.mark.parametrize("gate", sorted(SAMPLE_GATES))
def test_committed_truth_tables_are_current(root, trees, gate):
    """Stale vectors would let the C walker conform to an old policy."""
    path = root / "fixtures" / "decision_trees" / f"{gate}.truth.json"
    assert path.is_file(), "run scripts/generate_truth_tables.py"
    expected = _load_generator(root).render(truth_table(trees[gate]))
    assert path.read_text(encoding="utf-8") == expected, "run scripts/generate_truth_tables.py"


def test_allow_lists_every_evaluation(trees):
    facts = {
        "guest_authenticated": Fact(True, 1.0),
        "risk_level": Fact("low"),
        "room_matches": Fact(True),
    }
    result = walk(trees["unlock_door@1.2.0"], facts)
    assert result.verdict is GateVerdict.ALLOW
    assert result.reason is None
    assert result.evaluations == {
        "guest_authenticated": True,
        "risk_level": "low",
        "room_matches": True,
    }


def test_first_failure_in_root_first_order_names_the_reason(trees):
    facts = {
        "guest_authenticated": Fact(False, 1.0),
        "risk_level": Fact("low"),
        "room_matches": Fact(True),
        "staff_co_authorized": Fact(True),
        "request_channel": Fact("phone"),
    }
    result = walk(trees["unlock_door_night@1.0.0"], facts)
    assert result.reason is Reason.CONDITION_NOT_MET
    assert result.failed_criterion == "guest_authenticated"
    # Every criterion is still evaluated, so the trace can list them all.
    assert result.evaluations["request_channel"] == "phone"


def test_missing_confidence_on_a_floor_node_is_its_own_reason(trees):
    facts = {
        "guest_authenticated": Fact(True, None),
        "risk_level": Fact("low"),
        "room_matches": Fact(True),
        "staff_co_authorized": Fact(True),
        "request_channel": Fact("app"),
    }
    result = walk(trees["unlock_door_night@1.0.0"], facts)
    assert result.reason is Reason.CONFIDENCE_UNAVAILABLE


@pytest.mark.parametrize(
    ("value", "reason"),
    [(None, Reason.CRITERION_UNAVAILABLE), ("extreme", Reason.CRITERION_UNAVAILABLE)],
)
def test_missing_or_out_of_domain_facts_block(trees, value, reason):
    facts = {
        "guest_authenticated": Fact(True),
        "risk_level": Fact(value),
        "room_matches": Fact(True),
    }
    assert walk(trees["unlock_door@1.2.0"], facts).reason is reason


def test_confidence_exactly_at_the_floor_passes(trees):
    facts = {
        "guest_authenticated": Fact(True, 0.95),
        "risk_level": Fact("low"),
        "room_matches": Fact(True),
        "staff_co_authorized": Fact(True),
        "request_channel": Fact("in_person"),
    }
    assert walk(trees["unlock_door_night@1.0.0"], facts).verdict is GateVerdict.ALLOW


def test_not_in_covering_every_option_admits_nothing():
    gate = resolve_gate_document(
        {
            "schema": "neuroedge.gate/v1",
            "name": "nothing-passes",
            "version": "1.0.0",
            "evaluate": {
                "channel": {"type": "choice", "options": ["app", "web"], "instructions": "Channel"}
            },
            "allow_when": {"channel": {"not_in": ["app", "web"]}},
            "on_block": {"action": "deny"},
            "budget": {"p95_latency_ms": 100},
        }
    )
    tree = compile_tree(gate)
    for value in ("app", "web"):
        assert walk(tree, {"channel": Fact(value)}).reason is Reason.CONDITION_NOT_MET
