"""
Record a session to a `trace.v1` file (TSK-S3-01, FR-CI-01, FR-TRC-01→07).

`TraceRecorder` is the session's `EventLog`: every component (HAL, SystemOne,
Gate Engine, `c.do()`) already writes to it, so recording adds only the file
and anonymisation. What a session writes, in order:

    text_input / audio_in_*          what came in
    intent_extracted                 what SystemOne (or the grammar) decided
    action_requested                 which @action asked for which gate
    gate_evaluation_begin            the gate and its digest
    gate_facts                       the facts the verdict read, with confidence
    gate_evaluation_result           the verdict
    actuator_command / _aborted      what the pins did
    tts_stream_start                 what the agent said

`anonymize=True` (FR-TRC-07) replaces raw text **at the source** — before it
reaches the in-memory log — with ``sha256:<hex>``, and leaves every decision
field untouched, so the trace still replays to the same verdicts.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path
from typing import Any

from ..engine.trace_sink import Clock, EventLog, monotonic_ms
from ..trace import validate_trace

# Fields that carry what a person said or heard. Decision fields (intent,
# verdict, evaluations, pins) are never hashed: they are what a replay checks.
RAW_TEXT_FIELDS = frozenset({"text", "utterance", "transcript"})


def digest_text(text: str) -> str:
    normalised = unicodedata.normalize("NFC", text).encode("utf-8")
    return "sha256:" + hashlib.sha256(normalised).hexdigest()


def anonymise(data: dict[str, Any]) -> dict[str, Any]:
    return {
        key: digest_text(value) if key in RAW_TEXT_FIELDS and isinstance(value, str) else value
        for key, value in data.items()
    }


class TraceRecorder(EventLog):
    def __init__(
        self,
        *,
        target: str = "sim",
        board_id: str = "sim-default",
        agent_version: str = "unknown@0.0.0",
        anonymize: bool = False,
        clock: Clock = monotonic_ms,
        session_id: str | None = None,
        path: str | Path | None = None,
    ) -> None:
        super().__init__(
            clock,
            session_id=session_id,
            target=target,
            board_id=board_id,
            agent_version=agent_version,
        )
        self.anonymize = anonymize
        self.path = None if path is None else Path(path)
        if anonymize:
            self.metadata["anonymized"] = True

    def emit(self, type: str, data: dict[str, Any]) -> None:
        super().emit(type, anonymise(data) if self.anonymize else data)

    def save(self, path: str | Path | None = None) -> dict[str, Any]:
        """Validate against `trace.v1.json` and write; a trace that fails is never written."""
        target = Path(path) if path is not None else self.path
        if target is None:
            raise ValueError("TraceRecorder.save() needs a path")
        if target.suffix != ".json":
            target = target / f"{self.session_id}.json"
        trace = self.to_trace()
        validate_trace(trace, label=str(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.path = target
        return trace

    def __enter__(self) -> TraceRecorder:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        # A session that raised is still evidence: save it too.
        if self.path is not None:
            self.save()
