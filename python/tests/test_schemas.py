import json
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).parents[2]
SCHEMAS_DIR = ROOT_DIR / "schemas"
FIXTURES_DIR = ROOT_DIR / "fixtures" / "traces"

def test_trace_schema_loads_and_is_valid_json():
    trace_schema_file = SCHEMAS_DIR / "trace.v1.json"
    assert trace_schema_file.exists()
    with open(trace_schema_file, "r", encoding="utf-8") as f:
        schema = json.load(f)
    assert schema["$id"] == "https://schema.neuroedge.dev/trace/v1.json"
    assert "metadata" in schema["required"]
    assert "events" in schema["required"]

    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator.check_schema(schema)

@pytest.mark.parametrize("trace_filename", [
    "happy-path.json",
    "unverified_attempt.json",
    "network_offline.json"
])
def test_all_fixtures_conform_to_trace_schema(trace_filename):
    trace_schema_file = SCHEMAS_DIR / "trace.v1.json"
    fixture_file = FIXTURES_DIR / trace_filename
    assert fixture_file.exists(), f"Fixture {trace_filename} must exist"

    with open(trace_schema_file, "r", encoding="utf-8") as sf, open(fixture_file, "r", encoding="utf-8") as ff:
        schema = json.load(sf)
        trace_data = json.load(ff)

    assert trace_data["$schema"] == "https://schema.neuroedge.dev/trace/v1.json"
    assert "metadata" in trace_data
    assert "events" in trace_data
    assert len(trace_data["events"]) > 0

    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(instance=trace_data, schema=schema)

