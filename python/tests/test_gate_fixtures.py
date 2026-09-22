"""
Fixture-driven gate tests — the evidence for Sprint 1 exit criterion 1.

The criterion asks the frozen schemas to ship with valid examples *and*
invalid examples carrying their expected error message. These tests make that
a contract rather than a claim:

  * every file in fixtures/gates/invalid/ must fail, with the error class,
    stable code and Appendix B.5 principle recorded in expected_errors.yaml;
  * every file must have an entry, and every entry a file, so a new fixture
    cannot be added without stating what it proves;
  * every file in fixtures/gates/valid/ must resolve.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from neuroedge import errors as ne_errors
from neuroedge.engine import resolve_gate_file
from neuroedge.errors import NeuroEdgeError


def _invalid_files(gate_fixtures_dir: Path) -> list[Path]:
    return sorted((gate_fixtures_dir / "invalid").glob("*.yaml"))


def _valid_files(gate_fixtures_dir: Path) -> list[Path]:
    return sorted((gate_fixtures_dir / "valid").glob("*.yaml"))


def _ids(paths: list[Path]) -> list[str]:
    return [p.name for p in paths]


# Collected at import time so each fixture becomes its own test case.
_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "gates"
INVALID = _invalid_files(_FIXTURES_DIR)
VALID = _valid_files(_FIXTURES_DIR)


def test_invalid_fixtures_exist():
    assert INVALID, "the counter-example corpus must not be empty"


def test_every_invalid_fixture_has_a_recorded_expectation(expected_gate_errors):
    documented = set(expected_gate_errors)
    present = {p.name for p in INVALID}
    assert present - documented == set(), (
        "fixtures without a recorded expected error: "
        f"{sorted(present - documented)} — add them to fixtures/gates/expected_errors.yaml"
    )
    assert documented - present == set(), (
        f"expectations with no fixture: {sorted(documented - present)}"
    )


@pytest.mark.parametrize("path", INVALID, ids=_ids(INVALID))
def test_invalid_fixture_fails_exactly_as_recorded(path, expected_gate_errors, fixture_registry):
    expectation = expected_gate_errors[path.name]
    expected_class = getattr(ne_errors, expectation["error"])

    with pytest.raises(expected_class) as excinfo:
        resolve_gate_file(path, registry=fixture_registry)

    error = excinfo.value
    assert error.code == expectation["code"]
    assert expectation["where_contains"] in error.where, (
        f"expected {expectation['where_contains']!r} in where: {error.where!r}"
    )
    assert expectation["why_contains"] in error.why, (
        f"expected {expectation['why_contains']!r} in why: {error.why!r}"
    )
    if "principle" in expectation:
        assert error.principle == expectation["principle"]


@pytest.mark.parametrize("path", INVALID, ids=_ids(INVALID))
def test_invalid_fixture_diagnostic_has_all_three_parts(path, fixture_registry):
    """FR-DX-04: what is wrong, where, and how to fix it — for every rejection."""
    with pytest.raises(NeuroEdgeError) as excinfo:
        resolve_gate_file(path, registry=fixture_registry)
    error = excinfo.value
    assert error.where.strip(), "missing `where`"
    assert error.why.strip(), "missing `why`"
    assert error.how.strip(), "missing `how`"


@pytest.mark.parametrize("path", VALID, ids=_ids(VALID))
def test_valid_fixture_resolves(path, fixture_registry):
    resolved = resolve_gate_file(path, registry=fixture_registry)
    assert resolved.evaluate, "a resolved gate must adjudicate something"
    assert resolved.constraints, "a resolved gate must have at least one condition"
    assert resolved.on_block, "a resolved gate must say what happens on a block"


# --- Principle 4 behaviour, asserted on the on-disk corpus -----------------


def test_fail_open_base_resolves_to_closed_when_child_is_silent(
    gate_fixtures_dir, fixture_registry
):
    resolved = resolve_gate_file(
        gate_fixtures_dir / "valid" / "inherits_fail_open_as_closed.yaml",
        registry=fixture_registry,
    )
    assert resolved.budget["fail"] == "closed"
    assert resolved.fails_closed is True


def test_fail_open_is_honoured_when_declared_explicitly(gate_fixtures_dir, fixture_registry):
    resolved = resolve_gate_file(
        gate_fixtures_dir / "valid" / "explicit_fail_open.yaml",
        registry=fixture_registry,
    )
    assert resolved.budget["fail"] == "open"


def test_gate_declaring_only_identity_inherits_the_whole_contract(
    gate_fixtures_dir, fixture_registry
):
    """The document shape the pre-RFC-0001 schema could not express."""
    resolved = resolve_gate_file(
        gate_fixtures_dir / "valid" / "inherits_on_block_and_budget.yaml",
        registry=fixture_registry,
    )
    assert set(resolved.evaluate) == {"guest_authenticated", "risk_level", "request_channel"}
    assert resolved.on_block == {"action": "deny"}
    assert resolved.budget == {"p95_latency_ms": 150, "fail": "closed"}
