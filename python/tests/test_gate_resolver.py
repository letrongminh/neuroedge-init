"""
Unit tests for the five `extends` safety principles (Proposal Appendix B.5).

These build gate documents in memory so each principle is tested in isolation,
independent of the on-disk fixtures. The fixture-driven counterpart, which
also pins the exact diagnostics, lives in test_gate_fixtures.py.

Coverage map:
  principle 1 -> test_principle_1_*   (FR-GATE-06 context)
  principle 2 -> test_principle_2_*   (FR-GATE-06)
  principle 3 -> test_principle_3_*
  principle 4 -> test_principle_4_*   (FR-GATE-07)
  principle 5 -> test_principle_5_*   (FR-GATE-08)
"""

from __future__ import annotations

import pytest

from neuroedge.engine import MAX_INHERITANCE_LEVELS, GateRegistry, resolve_gate_document
from neuroedge.errors import GateInheritanceError, GateNotFoundError, GateSchemaError

BASE_URI = "neuroedge://gates/base@1.0.0"

BASE = {
    "schema": "neuroedge.gate/v1",
    "name": "base",
    "version": "1.0.0",
    "evaluate": {
        "authenticated": {"type": "bool", "instructions": "Identity verified"},
        "risk": {
            "type": "level",
            "levels": ["low", "medium", "high"],
            "instructions": "Anomaly risk",
        },
        "channel": {
            "type": "choice",
            "options": ["in_person", "app", "phone", "web"],
            "instructions": "Request channel",
        },
    },
    "allow_when": {
        "authenticated": True,
        "risk": {"lte": "medium"},
        "channel": {"in": ["in_person", "app"]},
    },
    "on_block": {"action": "escalate", "to": "human"},
    "budget": {"p95_latency_ms": 150, "fail": "closed"},
}


class DictRegistry(GateRegistry):
    """In-memory registry, so unit tests need no files on disk."""

    def __init__(self, documents: dict[str, dict]) -> None:
        self.documents = documents

    def load(self, uri: str):
        if uri not in self.documents:
            raise GateNotFoundError(
                where=uri, why="not in the in-memory registry", how="register it in the test"
            )
        return dict(self.documents[uri]), uri


def child(**overrides) -> dict:
    document = {
        "schema": "neuroedge.gate/v1",
        "name": "child",
        "version": "1.0.0",
        "extends": BASE_URI,
    }
    document.update(overrides)
    return document


@pytest.fixture
def registry() -> DictRegistry:
    return DictRegistry({BASE_URI: BASE})


def resolve(document: dict, registry: DictRegistry):
    return resolve_gate_document(document, source="<test>", registry=registry)


# --- Principle 1: inherit every base criterion -----------------------------


def test_principle_1_child_inherits_all_evaluate_criteria(registry):
    resolved = resolve(child(), registry)
    assert set(resolved.evaluate) == {"authenticated", "risk", "channel"}


def test_principle_1_child_inherits_allow_when_it_does_not_mention(registry):
    """Omitting a clause means inheriting it — never dropping it."""
    resolved = resolve(child(allow_when={"authenticated": True}), registry)
    assert resolved.constraints["risk"].admitted == frozenset({"low", "medium"})
    assert resolved.constraints["channel"].admitted == frozenset({"in_person", "app"})


def test_principle_1_child_inherits_on_block_and_latency(registry):
    resolved = resolve(child(), registry)
    assert resolved.on_block == {"action": "escalate", "to": "human"}
    assert resolved.budget["p95_latency_ms"] == 150


def test_principle_1_redefining_an_inherited_criterion_is_refused(registry):
    """Re-ordering `levels` would flip the meaning of an inherited clause."""
    document = child(
        evaluate={
            "risk": {
                "type": "level",
                "levels": ["high", "medium", "low"],
                "instructions": "Anomaly risk",
            }
        }
    )
    with pytest.raises(GateInheritanceError) as excinfo:
        resolve(document, registry)
    assert excinfo.value.principle == 1
    assert "redefines a criterion" in excinfo.value.why


def test_principle_1_restating_a_criterion_identically_is_allowed(registry):
    document = child(evaluate={"risk": dict(BASE["evaluate"]["risk"])})
    assert resolve(document, registry).evaluate["risk"] == BASE["evaluate"]["risk"]


# --- Principle 2: tighten only (FR-GATE-06) --------------------------------


@pytest.mark.parametrize(
    "criterion, clause, expected",
    [
        ("risk", {"lte": "low"}, {"low"}),
        ("risk", {"eq": "low"}, {"low"}),
        ("channel", {"eq": "in_person"}, {"in_person"}),
        ("channel", {"in": ["app"]}, {"app"}),
        ("channel", {"not_in": ["app", "phone", "web"]}, {"in_person"}),
        ("authenticated", {"confidence_gte": 0.95}, {"true"}),
    ],
)
def test_principle_2_tightening_is_accepted(registry, criterion, clause, expected):
    resolved = resolve(child(allow_when={criterion: clause}), registry)
    assert resolved.constraints[criterion].admitted == frozenset(expected)


@pytest.mark.parametrize(
    "criterion, clause",
    [
        ("risk", {"lte": "high"}),
        ("risk", {"gte": "medium"}),
        ("risk", {"eq": "high"}),
        ("channel", {"in": ["in_person", "app", "web"]}),
        ("channel", {"not_in": ["phone"]}),
        ("channel", {"eq": "web"}),
    ],
)
def test_principle_2_loosening_is_refused(registry, criterion, clause):
    with pytest.raises(GateInheritanceError) as excinfo:
        resolve(child(allow_when={criterion: clause}), registry)
    assert excinfo.value.principle == 2
    assert "loosens the inherited condition" in excinfo.value.why


def test_principle_2_lowering_a_confidence_floor_is_refused(registry):
    strict = dict(BASE, allow_when=dict(BASE["allow_when"], authenticated={"confidence_gte": 0.9}))
    reg = DictRegistry({BASE_URI: strict})
    with pytest.raises(GateInheritanceError) as excinfo:
        resolve(child(allow_when={"authenticated": {"confidence_gte": 0.5}}), reg)
    assert excinfo.value.principle == 2


def test_principle_2_raising_a_confidence_floor_is_accepted(registry):
    strict = dict(BASE, allow_when=dict(BASE["allow_when"], authenticated={"confidence_gte": 0.9}))
    reg = DictRegistry({BASE_URI: strict})
    resolved = resolve(child(allow_when={"authenticated": {"confidence_gte": 0.99}}), reg)
    assert resolved.constraints["authenticated"].confidence_floor == 0.99


def test_principle_2_flipping_a_bool_to_false_is_refused(registry):
    """`false` admits a different outcome than `true`, so it is not a subset."""
    with pytest.raises(GateInheritanceError) as excinfo:
        resolve(child(allow_when={"authenticated": False}), registry)
    assert excinfo.value.principle == 2


def test_principle_2_opaque_expression_in_a_chain_is_refused(registry):
    """Tightening is undecidable for a CEL string, so resolution fails closed."""
    with pytest.raises(GateInheritanceError) as excinfo:
        resolve(child(allow_when="authenticated == true"), registry)
    assert excinfo.value.principle == 2
    assert "cannot be proven" in excinfo.value.why


# --- Principle 3: add new criteria -----------------------------------------


def test_principle_3_child_may_add_criteria(registry):
    document = child(
        evaluate={"supervisor": {"type": "bool", "instructions": "Supervisor present"}},
        allow_when={"supervisor": True},
    )
    resolved = resolve(document, registry)
    assert resolved.constraints["supervisor"].admitted == frozenset({"true"})
    # Added criteria never displace inherited ones.
    assert set(resolved.evaluate) == {"authenticated", "risk", "channel", "supervisor"}


def test_allow_when_clause_without_a_criterion_is_refused(registry):
    """A clause naming nothing would silently never apply."""
    with pytest.raises(GateSchemaError) as excinfo:
        resolve(child(allow_when={"supervisr": True}), registry)
    assert "is declared in evaluate" in excinfo.value.why


# --- Principle 4: fail-open is never inherited (FR-GATE-07) ----------------


def test_principle_4_fail_open_does_not_cross_the_boundary():
    open_base = dict(BASE, budget={"p95_latency_ms": 150, "fail": "open"})
    reg = DictRegistry({BASE_URI: open_base})
    resolved = resolve(child(), reg)
    assert resolved.budget["fail"] == "closed"
    assert resolved.fails_closed is True


def test_principle_4_fail_open_declared_explicitly_takes_effect():
    open_base = dict(BASE, budget={"p95_latency_ms": 150, "fail": "open"})
    reg = DictRegistry({BASE_URI: open_base})
    resolved = resolve(child(budget={"p95_latency_ms": 100, "fail": "open"}), reg)
    assert resolved.budget["fail"] == "open"
    assert resolved.fails_closed is False


def test_principle_4_omitting_fail_on_a_root_gate_means_closed():
    root = dict(BASE, budget={"p95_latency_ms": 150})
    resolved = resolve(root, DictRegistry({}))
    assert resolved.budget["fail"] == "closed"


def test_principle_4_child_inherits_latency_but_not_fail_open():
    open_base = dict(BASE, budget={"p95_latency_ms": 150, "fail": "open"})
    reg = DictRegistry({BASE_URI: open_base})
    resolved = resolve(child(), reg)
    assert resolved.budget == {"p95_latency_ms": 150, "fail": "closed"}


# --- Principle 5: depth cap and cycles (FR-GATE-08) ------------------------


def _chain(levels: int) -> tuple[dict, DictRegistry]:
    """Build a chain of `levels` documents, returning the leaf and a registry."""
    documents: dict[str, dict] = {"neuroedge://gates/l1@1.0.0": BASE}
    for index in range(2, levels + 1):
        documents[f"neuroedge://gates/l{index}@1.0.0"] = {
            "schema": "neuroedge.gate/v1",
            "name": f"l{index}",
            "version": "1.0.0",
            "extends": f"neuroedge://gates/l{index - 1}@1.0.0",
        }
    leaf = documents.pop(f"neuroedge://gates/l{levels}@1.0.0")
    return leaf, DictRegistry(documents)


def test_principle_5_three_levels_resolve():
    leaf, reg = _chain(MAX_INHERITANCE_LEVELS)
    resolved = resolve(leaf, reg)
    assert resolved.inheritance_levels == MAX_INHERITANCE_LEVELS
    assert resolved.chain == ["base@1.0.0", "l2@1.0.0", "l3@1.0.0"]


def test_principle_5_four_levels_are_refused():
    leaf, reg = _chain(MAX_INHERITANCE_LEVELS + 1)
    with pytest.raises(GateInheritanceError) as excinfo:
        resolve(leaf, reg)
    assert excinfo.value.principle == 5
    assert f"exceeding the limit of {MAX_INHERITANCE_LEVELS}" in excinfo.value.why


def test_principle_5_dependency_cycle_is_refused():
    reg = DictRegistry(
        {
            "neuroedge://gates/a@1.0.0": {
                "schema": "neuroedge.gate/v1",
                "name": "a",
                "version": "1.0.0",
                "extends": "neuroedge://gates/b@1.0.0",
            },
            "neuroedge://gates/b@1.0.0": {
                "schema": "neuroedge.gate/v1",
                "name": "b",
                "version": "1.0.0",
                "extends": "neuroedge://gates/a@1.0.0",
            },
        }
    )
    with pytest.raises(GateInheritanceError) as excinfo:
        resolve(child(extends="neuroedge://gates/a@1.0.0"), reg)
    assert excinfo.value.principle == 5
    assert "dependency cycle" in excinfo.value.why


def test_principle_5_self_reference_is_refused():
    reg = DictRegistry(
        {
            "neuroedge://gates/loop@1.0.0": {
                "schema": "neuroedge.gate/v1",
                "name": "loop",
                "version": "1.0.0",
                "extends": "neuroedge://gates/loop@1.0.0",
            }
        }
    )
    with pytest.raises(GateInheritanceError) as excinfo:
        resolve(child(extends="neuroedge://gates/loop@1.0.0"), reg)
    assert excinfo.value.principle == 5


# --- Resolution invariants -------------------------------------------------


def test_missing_base_names_the_uri(registry):
    with pytest.raises(GateNotFoundError) as excinfo:
        resolve(child(extends="neuroedge://gates/absent@2.0.0"), DictRegistry({}))
    assert "absent@2.0.0" in excinfo.value.where


def test_resolution_is_deterministic(registry):
    """Same input, same artifact — the basis of the target-equivalence claim."""
    first = resolve(child(allow_when={"risk": {"eq": "low"}}), registry)
    second = resolve(child(allow_when={"risk": {"eq": "low"}}), registry)
    assert first.to_artifact() == second.to_artifact()


def test_resolved_artifact_records_provenance(registry):
    resolved = resolve(child(), registry)
    assert resolved.to_artifact()["resolved_from"] == ["base@1.0.0", "child@1.0.0"]


def test_every_error_carries_the_three_part_diagnostic(registry):
    with pytest.raises(GateInheritanceError) as excinfo:
        resolve(child(allow_when={"risk": {"lte": "high"}}), registry)
    error = excinfo.value
    assert error.where and error.why and error.how, "FR-DX-04 requires all three parts"
    assert error.code == "NE2003"
    rendered = error.render()
    for part in (error.where, error.why, error.how, "principle 2"):
        assert part in rendered
