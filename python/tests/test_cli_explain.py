"""
`neuroedge gate explain` (TSK-S3-18): a resolved gate for a reviewer who does not
read YAML (J6). The provenance it prints must agree with the resolver, so the
tests check the data (`explain_gate_*`) as well as the rendered text.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.engine import GateRegistry
from neuroedge.engine.gate_explain import explain_gate_file, explain_gate_uri
from neuroedge.errors import GateInheritanceError

runner = CliRunner()


def explain(*args: str):
    return runner.invoke(app, ["gate", "explain", *args])


def test_explain_shows_evaluate_allow_when_and_on_block(gates_dir):
    result = explain(str(gates_dir / "unlock_door@1.2.0.yaml"))
    assert result.exit_code == 0, result.output
    out = result.output
    assert "Gate: unlock_door@1.2.0" in out
    assert "Kế thừa từ: neuroedge://gates/hospitality/base-access@1.0.0" in out
    assert "Phân cấp: 2 cấp" in out
    assert "fail-closed" in out
    for section in ("1. Các tiêu chí đánh giá", "2. Điều kiện cho phép", "3. Ngân sách"):
        assert section in out
    for criterion in ("guest_authenticated", "risk_level", "room_matches"):
        assert criterion in out
    assert "(Từ base-access@1.0.0)" in out
    assert "(Mới)" in out
    assert "cha cho phép {low, medium} — con đã siết chặt" in out
    assert "120 ms (kế thừa và siết chặt từ cha 200 ms)" in out
    assert "escalate → human_receptionist" in out


def test_explain_accepts_a_registry_uri():
    result = explain("neuroedge://gates/unlock_door_night@1.0.0")
    assert result.exit_code == 0, result.output
    assert "Phân cấp: 3 cấp" in result.output
    assert "(Từ unlock_door@1.2.0)" in result.output
    assert "cha: escalate → human_receptionist" in result.output


def test_a_root_gate_says_it_inherits_nothing(gates_dir):
    result = explain(str(gates_dir / "hospitality" / "base-access@1.0.0.yaml"))
    assert result.exit_code == 0, result.output
    assert "Gate gốc" in result.output
    assert "(Từ " not in result.output


def test_an_invalid_gate_exits_one_with_a_three_part_diagnostic(gate_fixtures_dir):
    result = explain(
        str(gate_fixtures_dir / "invalid" / "loosens_level.yaml"),
        "--registry",
        str(gate_fixtures_dir / "registry"),
    )
    assert result.exit_code == 1
    assert "NE2003" in result.output
    assert "why:" in result.output and "fix:" in result.output
    assert "principle 2" in result.output


def test_a_missing_file_exits_one(tmp_path):
    result = explain(str(tmp_path / "nope.yaml"))
    assert result.exit_code == 1
    assert "NE20" in result.output


def test_fail_open_is_called_out(gate_fixtures_dir):
    result = explain(
        str(gate_fixtures_dir / "valid" / "explicit_fail_open.yaml"),
        "--registry",
        str(gate_fixtures_dir / "registry"),
    )
    assert result.exit_code == 0, result.output
    assert "fail-open" in result.output
    assert "trừ khi một tiêu chí đã biết là không đạt" in result.output


def test_degrade_names_its_fallback(gate_fixtures_dir):
    result = explain(
        str(gate_fixtures_dir / "valid" / "keeps_inherited_degrade.yaml"),
        "--registry",
        str(gate_fixtures_dir / "registry"),
    )
    assert result.exit_code == 0, result.output
    assert "degrade → chạy notify_front_desk qua gate riêng của nó" in result.output


# --- the provenance data ----------------------------------------------------------


def test_every_resolved_criterion_and_clause_is_explained(gates_dir):
    explanation = explain_gate_uri("neuroedge://gates/unlock_door_night@1.0.0")
    assert {c.name for c in explanation.criteria} == set(explanation.gate.evaluate)
    assert {c.criterion for c in explanation.clauses} == set(explanation.gate.constraints)
    origins = {c.name: c.introduced_by for c in explanation.criteria}
    assert origins["guest_authenticated"] == "base-access@1.0.0"
    assert origins["room_matches"] == "unlock_door@1.2.0"
    assert origins["staff_co_authorized"] == "unlock_door_night@1.0.0"
    status = {c.criterion: c.status for c in explanation.clauses}
    assert status == {
        "guest_authenticated": "tightened",
        "risk_level": "inherited",
        "room_matches": "inherited",
        "staff_co_authorized": "new",
        "request_channel": "new",
    }


@pytest.mark.parametrize(
    "fixture", ["restates_identically.yaml", "inherits_on_block_and_budget.yaml"]
)
def test_restating_or_omitting_a_clause_is_not_a_change(gate_fixtures_dir, fixture):
    registry = GateRegistry(gate_fixtures_dir / "registry")
    explanation = explain_gate_file(gate_fixtures_dir / "valid" / fixture, registry)
    assert {c.status for c in explanation.clauses} == {"inherited"}
    assert not explanation.on_block_changed
    assert explanation.parent_p95 == explanation.p95


def test_the_explanation_raises_what_the_resolver_raises(gate_fixtures_dir):
    registry = GateRegistry(gate_fixtures_dir / "registry")
    with pytest.raises(GateInheritanceError):
        explain_gate_file(gate_fixtures_dir / "invalid" / "loosens_level.yaml", registry)
