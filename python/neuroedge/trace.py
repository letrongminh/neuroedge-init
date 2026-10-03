"""
Trace loading and validation against schemas/trace.v1.json.

FR-TRC-08 requires `neuroedge trace validate` to be the single authority on
whether a trace is well formed, and A7 requires 100% of sessions to pass it.
The CLI and the test suite therefore share this one implementation — a second
validator would be a second definition of "valid".

Vision evidence (TSK-V1b-08, RFC-0012 §3d) adds no schema: `type` is an open string and `data` an
object, so the rules for a `vision_fact` event are a semantic lint, `lint_vision`, run by
`validate_trace` after the schema. It keeps a trace from carrying a picture (`vision_ref` is a hash
and a size, a `uri` only with `metadata.raw_capture`), and from claiming a verdict its own frames
cannot support (window length, consecutive frame numbers, the age of the oldest frame).

Format assertions (`date-time`, `uri`) are annotations in JSON Schema unless a
format checker is supplied. They are checked here, because a trace whose
timestamp cannot be parsed is not replayable, which is the whole point of the
file.
"""

from __future__ import annotations

import json
import math
import re
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
        lint_vision(trace, label)
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


# --- vision evidence (TSK-V1b-08, RFC-0012 §3d) ------------------------------------------------

VISION_EVENT = "vision_fact"  # the one name `perception/vision/facts.py` writes (pinned by a test)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_VISION_KINDS = ("present", "count", "confidence")
_VISION_DATA = {
    "fact", "kind", "label", "zone", "min_frames", "value", "values", "unavailable", "age_ms",
    "max_frame_age_ms", "present_score_floor", "model", "frames",
}  # fmt: skip
_VISION_FRAME = {"frame_seq", "vision_ref", "captured_ms", "labels", "rejected"}
_VISION_REF = {"sha256", "size", "uri"}
_VISION_LABEL = {"label", "zone", "score"}
# A string this long made only of base64 characters, or a data: URI, is an image in the trace.
_BLOB = re.compile(r"^[A-Za-z0-9+/_=-]{128,}$")
_NON_FINITE_TEXT = ("nan", "inf", "-inf")


def _whole(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _real(value: Any) -> bool:
    return (isinstance(value, int | float) and not isinstance(value, bool)) or (
        isinstance(value, str) and value in _NON_FINITE_TEXT
    )


def _blobs(value: Any, path: str):
    """Every place under `value` holding what looks like an embedded image."""
    if isinstance(value, str):
        if value.startswith("data:") or _BLOB.match(value.strip()):
            yield path
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _blobs(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _blobs(item, f"{path}.{index}")


def lint_vision(trace: dict[str, Any], label: str = "<memory>") -> None:
    """
    The semantic lint of RFC-0012 §3d over every `vision_fact` event, run by `validate_trace`.

    Raises `TraceValidationError` (NE4001) for the first of: a field that could carry pixels, a
    `uri` without `metadata.raw_capture`, a bad `sha256`, a model that is missing or not listed in
    `metadata.vision_models`, a window whose length is not `min_frames` (when the fact was read) or
    whose `frame_seq` is not consecutive, an `age_ms` that is not `offset_ms` minus the oldest
    `captured_ms`, or a read after the instant of judgement. A window the perception layer refused
    (`unavailable`) may be short, and may be in the future; everything else about it is checked all
    the same. Traces without such events — the three canonical ones — are untouched.
    """
    metadata = trace.get("metadata", {})
    raw_capture = metadata.get("raw_capture")

    def fail(where: str, why: str, how: str) -> TraceValidationError:
        return TraceValidationError(where=f"{label} -> {where}", why=why, how=how)

    if "raw_capture" in metadata and not isinstance(raw_capture, bool):
        raise fail(
            "metadata.raw_capture",
            "raw_capture must be true or false",
            "write true only for a session recorded on purpose with raw frames (NFR-PRIV-01)",
        )
    models = metadata.get("vision_models")
    listed: set[str] = set()
    if "vision_models" in metadata:
        if not isinstance(models, list) or not all(
            isinstance(m, dict)
            and isinstance(m.get("name"), str)
            and m["name"]
            and isinstance(m.get("sha256"), str)
            and _SHA256.match(m["sha256"])
            for m in models
        ):
            raise fail(
                "metadata.vision_models",
                "vision_models must list {name, sha256} of every model the session used, "
                "with a lowercase 64-hex sha256",
                "write the identity of each model: its name and the SHA-256 of its file",
            )
        listed = {m["sha256"] for m in models}

    for index, event in enumerate(trace.get("events", [])):
        if event.get("type") != VISION_EVENT:
            continue
        data, at = event["data"], f"events.{index}.data"
        hint = "a vision_fact carries labels and vision_ref only (docs/spec/vision.md §4)"

        extra = sorted(set(data) - _VISION_DATA)
        if extra:
            raise fail(at, f"unexpected field {extra[0]!r}: no pixels or free-form data", hint)
        for path in _blobs(data, at):
            raise fail(path, "an embedded image (base64 or a data: URI) is not allowed", hint)
        for key in ("fact", "label", "zone"):
            if not isinstance(data.get(key), str) or not data[key]:
                raise fail(f"{at}.{key}", f"{key} must be a non-empty string", hint)
        if data.get("kind") not in _VISION_KINDS:
            raise fail(f"{at}.kind", f"kind must be one of {list(_VISION_KINDS)}", hint)
        min_frames = data.get("min_frames")
        if not _whole(min_frames) or min_frames < 2:
            raise fail(f"{at}.min_frames", "min_frames must be a whole number, at least 2", hint)
        if "value" not in data or "values" not in data or not isinstance(data["values"], list):
            raise fail(at, "a vision_fact states its `value` and its per-frame `values`", hint)
        for key in ("max_frame_age_ms", "present_score_floor"):
            if not _real(data.get(key)) or isinstance(data.get(key), str):
                raise fail(f"{at}.{key}", f"{key} is a pinned constant and must be recorded", hint)

        # -- model identity (§9.4)
        model = data.get("model")
        if (
            not isinstance(model, dict)
            or not isinstance(model.get("name"), str)
            or not model["name"]
            or not isinstance(model.get("sha256"), str)
        ):
            raise fail(
                f"{at}.model",
                "a vision_fact names its model: {name, sha256}",
                "record the model that read the frames (RFC-0012 §3d)",
            )
        if not _SHA256.match(model["sha256"]):
            raise fail(f"{at}.model.sha256", "sha256 must be 64 lowercase hex characters", hint)
        if model["sha256"] not in listed:
            raise fail(
                f"{at}.model.sha256",
                "this model is not in metadata.vision_models",
                "list every model of the session there, so a swap mid-session stays traceable",
            )

        # -- the frames of the window
        frames = data.get("frames")
        if not isinstance(frames, list):
            raise fail(f"{at}.frames", "frames must be a list", hint)
        unavailable = data.get("unavailable")
        if (unavailable is None) != (data["value"] is not None):
            raise fail(
                at,
                "a fact is either read (`value`, no `unavailable`) or refused (`value` null, "
                "`unavailable` says why)",
                hint,
            )
        if unavailable is not None and (not isinstance(unavailable, str) or not unavailable):
            raise fail(f"{at}.unavailable", "unavailable must be a non-empty string", hint)
        if len(frames) > min_frames or (unavailable is None and len(frames) != min_frames):
            raise fail(
                f"{at}.frames",
                f"{len(frames)} frames recorded for min_frames={min_frames}: the window is "
                "exactly min_frames frames — none missing, none from outside it",
                "record the vision_ref of every frame of the window and of no other (§9.5)",
            )
        if len(data["values"]) != len(frames):
            raise fail(f"{at}.values", "values has one entry per frame", hint)

        previous: int | None = None
        for position, frame in enumerate(frames):
            where = f"{at}.frames.{position}"
            if not isinstance(frame, dict) or set(frame) - _VISION_FRAME:
                raise fail(where, "a frame holds frame_seq, vision_ref, captured_ms, labels", hint)
            seq, captured = frame.get("frame_seq"), frame.get("captured_ms")
            if not _whole(seq) or not _whole(captured):
                raise fail(where, "frame_seq and captured_ms must be whole numbers", hint)
            ref = frame.get("vision_ref")
            if not isinstance(ref, dict) or set(ref) - _VISION_REF:
                raise fail(f"{where}.vision_ref", "vision_ref holds sha256 and size only", hint)
            if "uri" in ref and raw_capture is not True:
                raise fail(
                    f"{where}.vision_ref.uri",
                    "a uri is allowed only when metadata.raw_capture is true: by default a "
                    "trace carries no image (NFR-PRIV-01, NFR-PRIV-03)",
                    "remove the uri, or record the session with raw capture on purpose",
                )
            if "uri" in ref and not isinstance(ref["uri"], str):
                raise fail(f"{where}.vision_ref.uri", "uri must be a string", hint)
            if not isinstance(ref.get("sha256"), str) or not _SHA256.match(ref["sha256"]):
                raise fail(
                    f"{where}.vision_ref.sha256", "sha256 must be 64 lowercase hex characters", hint
                )
            if not _whole(ref.get("size")) or ref["size"] < 0:
                raise fail(f"{where}.vision_ref.size", "size must be a whole number of bytes", hint)
            labels = frame.get("labels")
            if not isinstance(labels, list):
                raise fail(f"{where}.labels", "labels must be a list", hint)
            for place, item in enumerate(labels):
                if (
                    not isinstance(item, dict)
                    or set(item) != _VISION_LABEL
                    or item["label"] != data["label"]
                    or item["zone"] != data["zone"]
                    or not _real(item["score"])
                ):
                    raise fail(
                        f"{where}.labels.{place}",
                        "a label is {label, zone, score} of this fact's own label and zone",
                        "record only the detections the fact was computed from (§3d)",
                    )
            if "rejected" in frame and (
                not isinstance(frame["rejected"], str) or not frame["rejected"]
            ):
                raise fail(f"{where}.rejected", "rejected must be a non-empty string", hint)
            if previous is not None and seq != previous + 1:
                raise fail(
                    f"{where}.frame_seq",
                    f"frame_seq {seq} follows {previous}: frames of one window are consecutive "
                    "camera frames, a jump restarts the window",
                    "record only the consecutive frames since the last gap",
                )
            previous = seq

        # -- age (§3d): measured to this event, from the oldest frame
        age = data.get("age_ms")
        if not frames:
            if age is not None:
                raise fail(f"{at}.age_ms", "a window with no frames has no age", hint)
            continue
        oldest = min(frame["captured_ms"] for frame in frames)
        if not _whole(age) or age != event["offset_ms"] - oldest:
            raise fail(
                f"{at}.age_ms",
                f"age_ms={age!r} is not offset_ms - the oldest captured_ms "
                f"({event['offset_ms']} - {oldest} = {event['offset_ms'] - oldest})",
                "age_ms is recomputed by replay from the read marks; write what they give",
            )
        if unavailable is None and (
            age > data["max_frame_age_ms"]
            or any(frame["captured_ms"] > event["offset_ms"] for frame in frames)
        ):
            raise fail(
                f"{at}.age_ms",
                "a fact that was read cannot have a frame read after the instant it is judged at, "
                f"nor a window older than max_frame_age_ms={data['max_frame_age_ms']}",
                "such a window is `unavailable` (future / stale), not a value",
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
