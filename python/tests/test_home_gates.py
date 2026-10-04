"""
TSK-I2b-03 — the starter gate library of `gates/home/` (A5, I2b exit criterion 4).

Seven parent gates a maker `extends`: door, light, valve, siren, HVAC, camera, motor. Each is fail-closed
and each has a counter-example: a child that loosens it, refused by `neuroedge gate lint`
(`fixtures/gates/home/invalid/`, answers in `expected_errors.yaml`, closed both ways). A library gate
added later without a counter-example fails `test_every_library_gate_has_a_loosening_counter_example`.
The children resolve against `gates/`, so they live beside, not in, the fixture registry of `fixtures/gates/`.
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
LIBRARY = ROOT / "gates" / "home"
CORPUS = ROOT / "fixtures" / "gates" / "home"
INVALID = sorted((CORPUS / "invalid").glob("*.yaml"))
VALID = sorted((CORPUS / "valid").glob("*.yaml"))
EXPECTED = yaml.safe_load((CORPUS / "expected_errors.yaml").read_text(encoding="utf-8"))
LIBRARY_GATES = sorted(p.stem for p in LIBRARY.glob("*.yaml"))
runner = CliRunner()


@pytest.fixture(scope="module")
def registry(gates_dir):
    return GateRegistry(gates_dir)


def _extends(path: Path) -> str:
    """`door-lock@1.0.0` for a child that extends `neuroedge://gates/home/door-lock@1.0.0`."""
    uri = yaml.safe_load(path.read_text(encoding="utf-8"))["extends"]
    prefix = "neuroedge://gates/home/"
    assert uri.startswith(prefix), f"{path.name} extends {uri!r}, not a library gate"
    return uri.removeprefix(prefix)


def test_the_library_is_the_seven_starter_gates():
    assert [name.split("@")[0] for name in LIBRARY_GATES] == [
        "camera",
        "door-lock",
        "hvac",
        "light",
        "motor",
        "siren",
        "valve",
    ]


@pytest.mark.parametrize("name", LIBRARY_GATES)
def test_a_library_gate_is_fail_closed_with_a_short_budget(gates_dir, name):
    gate = resolve_gate_file(LIBRARY / f"{name}.yaml")
    assert gate.fails_closed and gate.budget["fail"] == "closed"
    assert gate.budget["p95_latency_ms"] <= 150
    assert gate.on_block["action"] in {"deny", "escalate", "ask"}
    for criterion, definition in gate.evaluate.items():
        if definition["type"] == "numeric":
            assert definition["max_age_ms"] <= 1000, criterion


@pytest.mark.parametrize("name", LIBRARY_GATES)
def test_every_library_gate_has_a_loosening_counter_example(name, registry):
    """I2b exit criterion 4: a parent gate no child loosens without `gate lint` saying so."""
    children = [p for p in INVALID if _extends(p) == name]
    assert children, (
        f"gates/home/{name}.yaml has no counter-example in fixtures/gates/home/invalid/"
    )
    for child in children:
        result = runner.invoke(app, ["gate", "lint", str(child), "--registry", str(ROOT / "gates")])
        assert result.exit_code == 1, f"{child.name}: lint accepted a child that loosens {name}"
    # One loosening is not enough: thresholds, freshness lock and budget are separate locks.
    assert len(children) >= 3, (
        f"{name}: cover the thresholds, the freshness lock and the budget too"
    )


@pytest.mark.parametrize("name", LIBRARY_GATES)
def test_every_library_gate_has_a_valid_tightening_child(name):
    children = [p for p in VALID if _extends(p) == name]
    assert children, f"gates/home/{name}.yaml has no valid child in fixtures/gates/home/valid/"


# --- the counter-examples, closed both ways ----------------------------------------------------


def test_every_counter_example_has_an_entry_and_every_entry_a_file():
    assert INVALID and VALID
    assert {p.name for p in INVALID} == set(EXPECTED)


@pytest.mark.parametrize("path", INVALID, ids=[p.name for p in INVALID])
def test_a_child_that_loosens_a_library_gate_is_refused(path, registry):
    expectation = EXPECTED[path.name]
    with pytest.raises(getattr(ne_errors, expectation["error"])) as excinfo:
        resolve_gate_file(path, registry=registry)
    error = excinfo.value
    assert error.code == expectation["code"] and error.principle == expectation["principle"]
    assert expectation["where_contains"] in error.where
    assert expectation["why_contains"] in error.why


@pytest.mark.parametrize("path", VALID, ids=[p.name for p in VALID])
def test_a_child_that_only_tightens_a_library_gate_resolves(path, registry):
    gate = resolve_gate_file(path, registry=registry)
    assert gate.inheritance_levels == 2
    assert gate.fails_closed


def test_gate_lint_is_green_on_the_library_and_red_on_each_counter_example():
    gates = str(ROOT / "gates")
    ok = runner.invoke(app, ["gate", "lint", str(LIBRARY)])
    assert ok.exit_code == 0, ok.output
    good = runner.invoke(app, ["gate", "lint", str(CORPUS / "valid"), "--registry", gates])
    assert good.exit_code == 0, good.output
    bad = runner.invoke(app, ["gate", "lint", str(CORPUS / "invalid"), "--registry", gates])
    assert bad.exit_code == 1
    assert f"{len(INVALID)} of {len(INVALID)} gate(s) failed" in bad.output
