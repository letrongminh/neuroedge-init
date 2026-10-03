"""
TSK-V1b-06 — the three vision gates of `gates/vision/` (RFC-0012 §3c, §9.2, Q-54).

Each locks its confidence threshold in the gate as a `numeric` criterion; a maker's `[vision.facts.*]`
only names which label feeds which criterion. The counter-examples (`fixtures/gates/vision/invalid/`)
are children that loosen them (A5 style): all refused, each as `expected_errors.yaml` says, and the
corpus is closed both ways. They resolve against `gates/`, so they live beside, not in, the
fixture registry of `fixtures/gates/`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from neuroedge import errors as ne_errors
from neuroedge.cli.main import app
from neuroedge.engine import GateRegistry, resolve_gate_file

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "fixtures" / "gates" / "vision"
INVALID = sorted((CORPUS / "invalid").glob("*.yaml"))
VALID = sorted((CORPUS / "valid").glob("*.yaml"))
EXPECTED = yaml.safe_load((CORPUS / "expected_errors.yaml").read_text(encoding="utf-8"))
runner = CliRunner()


@pytest.fixture(scope="module")
def registry(gates_dir):
    return GateRegistry(gates_dir)


def _gate(gates_dir, name):
    return resolve_gate_file(gates_dir / "vision" / f"{name}.yaml")


def _numeric(gate, criterion):
    return gate.evaluate[criterion]


# --- the gates ---------------------------------------------------------------------------------


def test_entry_gate_locks_the_stranger_threshold_and_freshness(gates_dir):
    gate = _gate(gates_dir, "entry-no-stranger@1.0.0")
    assert gate.fails_closed
    assert gate.constraints["stranger_at_door"].admitted == frozenset({"false"})
    interval = gate.constraints["stranger_confidence"].interval
    assert interval.upper.value == 0.10 and interval.upper.closed and interval.lower is None
    spec = _numeric(gate, "stranger_confidence")
    assert spec["type"] == "numeric" and spec["max_age_ms"] == 300
    assert spec["range"] == {"min": 0, "max": 1}
    assert gate.on_block["action"] == "escalate"


def test_zone_gate_needs_presence_count_and_confidence_together(gates_dir):
    gate = _gate(gates_dir, "zone-clear@1.0.0")
    assert set(gate.constraints) == {"person_in_zone", "people_in_zone", "person_confidence"}
    assert gate.constraints["person_in_zone"].admitted == frozenset({"false"})
    assert gate.constraints["people_in_zone"].interval.upper.value == 0
    assert gate.constraints["person_confidence"].interval.upper.value == 0.10
    assert _numeric(gate, "people_in_zone")["range"] == {"min": 0, "max": 50}


def test_package_gate_floors_the_confidence(gates_dir):
    gate = _gate(gates_dir, "package-notify@1.0.0")
    assert gate.constraints["package_present"].admitted == frozenset({"true"})
    interval = gate.constraints["package_confidence"].interval
    assert interval.lower.value == 0.80 and interval.lower.closed and interval.upper is None
    assert _numeric(gate, "package_confidence")["max_age_ms"] == 500


@pytest.mark.parametrize(
    "name", ["entry-no-stranger@1.0.0", "zone-clear@1.0.0", "package-notify@1.0.0"]
)
def test_a_vision_boolean_never_stands_alone_in_a_sample_gate(gates_dir, name):
    """RFC-0012 §3c: every presence or count criterion has its numeric confidence beside it."""
    gate = _gate(gates_dir, name)
    kinds = {c: d["type"] for c, d in gate.evaluate.items()}
    assert "numeric" in kinds.values()
    for criterion, kind in kinds.items():
        if criterion in gate.constraints and kind == "numeric":
            assert _numeric(gate, criterion)["max_age_ms"] <= 500


# --- the counter-examples, closed both ways ----------------------------------------------------


def test_every_vision_counter_example_has_an_entry_and_every_entry_a_file():
    assert INVALID and VALID
    assert {p.name for p in INVALID} == set(EXPECTED)


@pytest.mark.parametrize("path", INVALID, ids=[p.name for p in INVALID])
def test_a_child_that_loosens_a_vision_gate_is_refused(path, registry):
    expectation = EXPECTED[path.name]
    with pytest.raises(getattr(ne_errors, expectation["error"])) as excinfo:
        resolve_gate_file(path, registry=registry)
    error = excinfo.value
    assert error.code == expectation["code"] and error.principle == expectation["principle"]
    assert expectation["where_contains"] in error.where
    assert expectation["why_contains"] in error.why


@pytest.mark.parametrize("path", VALID, ids=[p.name for p in VALID])
def test_a_child_that_only_tightens_a_vision_gate_resolves(path, registry):
    gate = resolve_gate_file(path, registry=registry)
    assert gate.inheritance_levels == 2


def test_gate_lint_is_green_on_the_corpus_and_red_on_each_counter_example():
    ok = runner.invoke(app, ["gate", "lint"])
    assert ok.exit_code == 0, ok.output
    assert "entry-no-stranger@1.0.0" in ok.output
    gates = str(ROOT / "gates")
    good = runner.invoke(app, ["gate", "lint", str(CORPUS / "valid"), "--registry", gates])
    assert good.exit_code == 0, good.output
    bad = runner.invoke(app, ["gate", "lint", str(CORPUS / "invalid"), "--registry", gates])
    assert bad.exit_code == 1
    assert f"{len(INVALID)} of {len(INVALID)} gate(s) failed" in bad.output
