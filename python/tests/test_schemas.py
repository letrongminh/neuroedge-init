"""
Structural conformance of the three frozen schemas.

`jsonschema` is imported at module level on purpose. It used to be pulled in
with `pytest.importorskip`, which meant that on a machine without it these
tests skipped and the run still reported "4 passed" — the schema conformance
claim in the progress dashboard was resting on tests that never executed.
Conformance dependencies are mandatory dependencies (CONTRIBUTING.md §5).
"""

import json
from pathlib import Path

import jsonschema
import pytest

from neuroedge.paths import repo_root

ROOT_DIR = repo_root()
SCHEMAS_DIR = ROOT_DIR / "schemas"
FIXTURES_DIR = ROOT_DIR / "fixtures" / "traces"

SCHEMA_IDS = {
    "trace.v1.json": "https://schema.neuroedge.dev/trace/v1.json",
    "gate.v1.json": "https://schema.neuroedge.dev/gate/v1.json",
    "board.v1.json": "https://schema.neuroedge.dev/board/v1.json",
}


def _load(name: str) -> dict:
    with open(SCHEMAS_DIR / name, encoding="utf-8") as handle:
        return json.load(handle)


def test_schemas_directory_holds_exactly_the_three_frozen_schemas():
    """TSK-S1-07. A fourth schema appearing without an RFC is itself a finding."""
    assert {p.name for p in SCHEMAS_DIR.glob("*.json")} == set(SCHEMA_IDS)


@pytest.mark.parametrize("name", sorted(SCHEMA_IDS))
def test_schema_is_valid_draft_2020_12(name):
    jsonschema.Draft202012Validator.check_schema(_load(name))


@pytest.mark.parametrize("name, schema_id", sorted(SCHEMA_IDS.items()))
def test_schema_declares_its_canonical_id(name, schema_id):
    """The `$id` is what trace files and tooling reference; it must not drift."""
    schema = _load(name)
    assert schema["$id"] == schema_id
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_trace_schema_requires_metadata_and_events():
    schema = _load("trace.v1.json")
    assert "metadata" in schema["required"]
    assert "events" in schema["required"]


def test_gate_schema_requires_identity_unconditionally():
    """RFC-0001: identity is always required; the contract fields are conditional."""
    schema = _load("gate.v1.json")
    assert schema["required"] == ["schema", "name", "version"]


def test_gate_schema_requires_the_full_contract_for_a_root_gate():
    """A gate with no `extends` has nothing to inherit from, so it must declare everything."""
    schema = _load("gate.v1.json")
    conditional = [
        clause
        for clause in schema["allOf"]
        if clause.get("if", {}).get("not", {}).get("required") == ["extends"]
    ]
    assert len(conditional) == 1, "the RFC-0001 conditional must be present exactly once"
    assert set(conditional[0]["then"]["required"]) == {
        "schema",
        "name",
        "version",
        "evaluate",
        "allow_when",
        "on_block",
        "budget",
    }


def test_gate_schema_does_not_require_budget_fail():
    """Appendix B.4 calls `closed` the default, so the field must be optional."""
    budget = _load("gate.v1.json")["properties"]["budget"]
    assert budget["required"] == ["p95_latency_ms"]
    assert budget["properties"]["fail"]["default"] == "closed"


def test_gate_schema_enumerates_exactly_the_four_on_block_behaviours():
    on_block = _load("gate.v1.json")["properties"]["on_block"]
    assert set(on_block["properties"]["action"]["enum"]) == {"deny", "escalate", "ask", "degrade"}


def test_gate_schema_enumerates_exactly_the_three_evaluate_types():
    evaluate = _load("gate.v1.json")["properties"]["evaluate"]
    assert set(evaluate["additionalProperties"]["properties"]["type"]["enum"]) == {
        "bool",
        "level",
        "choice",
    }


def test_board_schema_enumerates_exactly_the_three_targets():
    board = _load("board.v1.json")["properties"]["board"]
    assert set(board["properties"]["target"]["enum"]) == {"sim", "linux", "esp32s3"}


@pytest.mark.parametrize(
    "trace_filename", ["happy-path.json", "unverified_attempt.json", "network_offline.json"]
)
def test_canonical_trace_conforms_to_the_trace_schema(trace_filename):
    schema = _load("trace.v1.json")
    with open(FIXTURES_DIR / trace_filename, encoding="utf-8") as handle:
        trace = json.load(handle)

    assert trace["$schema"] == SCHEMA_IDS["trace.v1.json"]
    assert trace["events"], "a trace with no events replays nothing"
    jsonschema.validate(instance=trace, schema=schema)


def test_schema_files_are_utf8_without_a_bom():
    """A BOM would break byte-exact tooling and the RFC 8785 pipeline."""
    for name in SCHEMA_IDS:
        raw = Path(SCHEMAS_DIR / name).read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{name} has a UTF-8 BOM"
        raw.decode("utf-8")
