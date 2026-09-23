"""
CLI behaviour, with emphasis on exit codes.

CI and Action CI both key off exit status, so a command that prints a failure
but exits 0 is a silent hole in the pipeline. Every assertion below pins the
status as well as the output.

Exit-code contract:
    0  the requested check ran and passed
    1  the check ran and failed
    2  the command is not implemented yet
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app

runner = CliRunner()


@pytest.fixture(scope="module")
def invoke():
    def _invoke(*args: str):
        return runner.invoke(app, list(args))

    return _invoke


# --- gate resolve ---------------------------------------------------------


def test_gate_resolve_by_uri(invoke):
    result = invoke("gate", "resolve", "neuroedge://gates/unlock_door_night@1.0.0")
    assert result.exit_code == 0, result.output
    assert "unlock_door_night@1.0.0" in result.output
    assert "3 level(s)" in result.output


def test_gate_resolve_by_path(invoke, gates_dir):
    result = invoke("gate", "resolve", str(gates_dir / "unlock_door@1.2.0.yaml"))
    assert result.exit_code == 0, result.output
    assert "2 level(s)" in result.output


def test_gate_resolve_json_is_machine_readable(invoke):
    result = invoke("gate", "resolve", "neuroedge://gates/unlock_door@1.2.0", "--json")
    assert result.exit_code == 0, result.output
    artifact = json.loads(result.output)
    assert artifact["name"] == "unlock_door"
    assert artifact["resolved_from"] == ["base-access@1.0.0", "unlock_door@1.2.0"]
    assert artifact["budget"]["fail"] == "closed"


def test_gate_resolve_reports_the_three_part_diagnostic(invoke, gate_fixtures_dir):
    result = invoke(
        "gate",
        "resolve",
        str(gate_fixtures_dir / "invalid" / "loosens_level.yaml"),
        "--registry",
        str(gate_fixtures_dir / "registry"),
    )
    assert result.exit_code == 1
    combined = result.output + result.stderr
    assert "NE2003" in combined
    assert "why:" in combined and "fix:" in combined
    assert "principle 2" in combined


def test_gate_resolve_missing_file_exits_one(invoke, tmp_path):
    result = invoke("gate", "resolve", str(tmp_path / "nope.yaml"))
    assert result.exit_code == 1


# --- gate lint ------------------------------------------------------------


def test_gate_lint_passes_on_the_sample_corpus(invoke):
    result = invoke("gate", "lint")
    assert result.exit_code == 0, result.output
    assert "3 gate(s) resolved" in result.output


def test_gate_lint_fails_on_the_invalid_corpus(invoke, gate_fixtures_dir):
    result = invoke("gate", "lint", str(gate_fixtures_dir / "invalid"))
    assert result.exit_code == 1
    assert "failed to resolve" in result.output + result.stderr


def test_gate_lint_on_empty_directory_exits_one(invoke, tmp_path):
    assert invoke("gate", "lint", str(tmp_path)).exit_code == 1


# --- gate publish ---------------------------------------------------------


def test_gate_publish_emits_canonical_bytes_and_digest(invoke, gates_dir, tmp_path):
    out = tmp_path / "unlock_door.canonical.json"
    result = invoke("gate", "publish", str(gates_dir / "unlock_door@1.2.0.yaml"), "--out", str(out))
    assert result.exit_code == 0, result.output
    assert "sha256:" in result.output
    payload = out.read_bytes()
    # RFC 8785 output is compact, sorted and self-consistent.
    assert payload.startswith(b"{") and b", " not in payload
    assert json.loads(payload)["name"] == "unlock_door"


def test_gate_publish_does_not_claim_to_have_signed(invoke, gates_dir):
    """Signing needs registry key material (Khối 3); the command must not overstate."""
    result = invoke("gate", "publish", str(gates_dir / "unlock_door@1.2.0.yaml"))
    assert result.exit_code == 0
    assert "canonical bytes and digest only" in result.output


def test_gate_publish_digest_matches_the_library(invoke, gates_dir):
    from neuroedge.engine import gate_digest, resolve_gate_file

    path = gates_dir / "unlock_door_night@1.0.0.yaml"
    expected = gate_digest(resolve_gate_file(path))
    result = invoke("gate", "publish", str(path))
    assert expected.split(":")[1][:16] in result.output.replace("\n", "")


# --- trace ----------------------------------------------------------------


def test_trace_validate_accepts_the_canonical_traces(invoke, traces_dir):
    paths = [str(p) for p in sorted(traces_dir.glob("*.json"))]
    result = invoke("trace", "validate", *paths)
    assert result.exit_code == 0, result.output
    assert result.output.count("VALID") == 3


@pytest.mark.parametrize(
    "name", ["bad_session_id.json", "bad_timestamp.json", "unknown_target.json"]
)
def test_trace_validate_rejects_invalid_traces(invoke, traces_dir, name):
    result = invoke("trace", "validate", str(traces_dir / "invalid" / name))
    assert result.exit_code == 1
    assert "NE4001" in result.output + result.stderr


def test_trace_validate_fails_the_batch_if_any_trace_is_invalid(invoke, traces_dir):
    result = invoke(
        "trace",
        "validate",
        str(traces_dir / "happy-path.json"),
        str(traces_dir / "invalid" / "negative_offset.json"),
    )
    assert result.exit_code == 1, "one bad trace must fail the whole invocation"


def test_trace_show_prints_the_timeline(invoke, traces_dir):
    result = invoke("trace", "show", str(traces_dir / "happy-path.json"))
    assert result.exit_code == 0, result.output
    assert "actuator_command" in result.output
    assert "sess_a1b2c3d4" in result.output


# --- board ----------------------------------------------------------------


def test_board_list_shows_every_profile(invoke):
    result = invoke("board", "list")
    assert result.exit_code == 0, result.output
    for board_id in ("sim-default", "esp32s3-box-3", "linux-rpi5"):
        assert board_id in result.output


def test_board_show_lists_all_five_primitives(invoke):
    result = invoke("board", "show", "esp32s3-box-3")
    assert result.exit_code == 0, result.output
    for primitive in ("audio.in", "audio.out", "digital.out", "sensor.read", "display"):
        assert primitive in result.output


def test_board_show_unknown_id_exits_one(invoke):
    result = invoke("board", "show", "esp32s3-devkitc")
    assert result.exit_code == 1
    assert "NE3001" in result.output + result.stderr


# --- verify ---------------------------------------------------------------


def test_verify_passes_and_states_what_it_did_not_check(invoke):
    result = invoke("verify")
    assert result.exit_code == 0, result.output
    assert "all gates resolve" in result.output
    # A2 is only partly discharged; the command must not imply otherwise.
    assert "Not yet covered" in result.output


# --- replay ---------------------------------------------------------------


@pytest.mark.parametrize("name", ["happy-path", "unverified_attempt", "network_offline"])
def test_replay_executes_each_canonical_trace_and_matches_it(invoke, traces_dir, name):
    result = invoke("replay", str(traces_dir / f"{name}.json"))
    assert result.exit_code == 0, result.output
    assert "decisions match the recording" in result.output


def test_replay_rejects_an_invalid_trace(invoke, traces_dir):
    result = invoke("replay", str(traces_dir / "invalid" / "missing_board_id.json"))
    assert result.exit_code == 1


# --- not-yet-implemented paths ----------------------------------------------


def test_a_target_without_a_live_session_exits_two_and_names_what_works():
    """
    A command must not print a result it did not compute. Exit code 2 keeps
    "not implemented" distinguishable from a genuine failure in CI.
    """
    result = runner.invoke(app, ["run", "--target", "linux", "-c", "x"])
    assert result.exit_code == 2, result.output
    assert "replay" in result.output


def test_help_lists_the_implemented_command_groups(invoke):
    result = invoke("--help")
    assert result.exit_code == 0
    for group in ("gate", "trace", "board", "verify"):
        assert group in result.output


def test_registry_option_redirects_base_lookups(invoke, gate_fixtures_dir):
    """Without --registry the fixture base is not found; with it, resolution succeeds."""
    gate = str(gate_fixtures_dir / "valid" / "restates_identically.yaml")
    assert invoke("gate", "resolve", gate).exit_code == 1
    result = invoke("gate", "resolve", gate, "--registry", str(gate_fixtures_dir / "registry"))
    assert result.exit_code == 0, result.output
    assert "restates-identically@1.0.0" in result.output


def test_gate_lint_accepts_an_explicit_registry(invoke, gate_fixtures_dir):
    """
    `gate lint --registry` must exist and be honoured.

    Regression guard. The inverted assertion in ci-sim-linux.yml runs exactly
    this invocation and requires exit code 1. If the option went missing, Typer
    would exit 2 for a usage error, and a check written as `if ! cmd` would
    still have looked satisfied while never running the command at all.
    """
    result = invoke(
        "gate",
        "lint",
        str(gate_fixtures_dir / "invalid"),
        "--registry",
        str(gate_fixtures_dir / "registry"),
    )
    assert result.exit_code == 1, (
        f"expected 1 (ran and failed), got {result.exit_code} — "
        f"2 would mean the option was not recognised"
    )
    assert "failed to resolve" in result.output + result.stderr


def test_gate_lint_registry_option_changes_the_outcome(invoke, gate_fixtures_dir):
    """The option must actually redirect lookups, not merely be accepted."""
    valid = str(gate_fixtures_dir / "valid")
    # Fixture bases live in a sibling registry/, which lint auto-detects.
    assert invoke("gate", "lint", valid).exit_code == 0
    # Pointing at the real gates/ corpus instead, the bases are absent.
    result = invoke("gate", "lint", valid, "--registry", "gates")
    assert result.exit_code == 1
    assert "NE2001" in result.output + result.stderr
