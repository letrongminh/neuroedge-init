"""
Trace loading and validation against schemas/trace.v1.json.

FR-TRC-08 requires `neuroedge trace validate` to be the single authority on
whether a trace is well formed, and A7 requires 100% of sessions to pass it.
The CLI and the test suite therefore share this one implementation — a second
validator would be a second definition of "valid".

Format assertions (`date-time`, `uri`) are annotations in JSON Schema unless a
format checker is supplied. They are checked here, because a trace whose
timestamp cannot be parsed is not replayable, which is the whole point of the
file.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .errors import TraceValidationError
from .paths import schema_path

TRACE_SCHEMA_ID = "https://schema.neuroedge.dev/trace/v1.json"


def json_safe(value: Any) -> Any:
    """
    `value` with every NaN / inf float written as the string "nan", "inf" or "-inf".

    JSON has no such numbers: Python writes a bare `NaN`, which `JSON.parse` in a
    browser and strict parsers refuse — a trace view that stops, a live page that
    stops updating. Every event goes through here (`EventLog.emit`), and so does
    anything embedded in a page (`viz`, `sim/ui.py`).
    """
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return tuple(json_safe(item) for item in value)
    return value


def trace_schema() -> dict[str, Any]:
    with open(schema_path("trace.v1.json"), encoding="utf-8") as handle:
        return json.load(handle)


def _validator():
    import jsonschema

    return jsonschema.Draft202012Validator(
        trace_schema(),
        format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
    )


def validate_trace(trace: dict[str, Any], label: str = "<memory>") -> None:
    """
    Validate one parsed trace.

    Raises
    ------
    TraceValidationError
        Carrying the three-part diagnostic required by FR-DX-04, pointed at the
        first offending JSON path.
    """
    errors = sorted(_validator().iter_errors(trace), key=lambda e: list(e.absolute_path))
    if not errors:
        return

    first = errors[0]
    location = ".".join(str(part) for part in first.absolute_path) or "<document root>"
    extra = f" (+{len(errors) - 1} further problem(s))" if len(errors) > 1 else ""
    raise TraceValidationError(
        where=f"{label} -> {location}",
        why=f"{first.message}{extra}",
        how=(
            "correct the field against schemas/trace.v1.json "
            "(event reference: Proposal Appendix C.1)"
        ),
    )


class _NonFinite(ValueError):
    pass


def _no_constant(name: str) -> Any:
    raise _NonFinite(name)  # NaN, Infinity, -Infinity: Python's extension, not JSON


def load_trace(path: str | Path, validate: bool = True) -> dict[str, Any]:
    """Read a trace file, validating it against the frozen schema by default."""
    path = Path(path)
    if not path.is_file():
        raise TraceValidationError(
            where=str(path),
            why="file does not exist",
            how="check the path, or record a session with `neuroedge record`",
        )

    try:
        trace = json.loads(path.read_text(encoding="utf-8"), parse_constant=_no_constant)
    except json.JSONDecodeError as exc:
        raise TraceValidationError(
            where=f"{path} -> line {exc.lineno}, column {exc.colno}",
            why=f"file is not valid JSON: {exc.msg}",
            how="traces are UTF-8 JSON objects; repair the syntax at the position above",
        ) from exc
    except _NonFinite as exc:
        raise TraceValidationError(
            where=str(path),
            why=f"the file holds a bare {exc.args[0]}, which JSON does not have",
            how='write the value as a string ("nan", "inf", "-inf"), as `neuroedge record` does',
        ) from None

    if not isinstance(trace, dict):
        raise TraceValidationError(
            where=str(path),
            why=f"top level must be a JSON object, found {type(trace).__name__}",
            how=f'a trace starts with {{"$schema": "{TRACE_SCHEMA_ID}", ...}}',
        )

    if validate:
        validate_trace(trace, label=str(path))
    return trace
