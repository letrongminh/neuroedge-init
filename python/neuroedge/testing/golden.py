"""
Golden reference comparison (TSK-S3-04, FR-CI-04, FR-CI-LVL L1).

A golden reference is a trace whose **decisions** are the expected ones. Two
traces match when their safety views are equal:

* the gate sequence — for each evaluation, in order: the gate, the verdict, and
  every decision field the golden records (`reason`, `blocked_by`, `action`,
  `escalated_to`, `fail_mode`, `fallback_action`);
* the actuator sequence — every `actuator_command` (pin, operation, duration)
  and `actuator_aborted` (pin, reason), in order.

Everything else is noise and ignored: `session_id`, `timestamp_utc`,
`offset_ms`, latency, perception details, System 2 text (L3). A decision field
the golden does not record is not compared — the canonical traces predate
`reason` — but one it does record must match exactly.

Any difference raises `SafetyRegressionError` naming the first differing event
and field. A difference that makes the system *less* safe — a BLOCK turned
ALLOW, a pin command the golden does not have — is labelled so.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from deepdiff import DeepDiff

from ..errors import SafetyRegressionError
from ..trace import load_trace

DECISION_FIELDS = ("reason", "blocked_by", "action", "escalated_to", "fail_mode", "fallback_action")


def _events(subject: Any) -> list[dict[str, Any]]:
    if isinstance(subject, dict):
        return subject.get("events", [])
    replayed = getattr(subject, "replayed", None)
    if replayed is not None:
        return replayed["events"]
    log = getattr(subject, "events", None)
    if log is not None and hasattr(log, "to_trace"):
        return log.to_trace()["events"]
    raise TypeError(f"expected a trace, ReplayResult or SimSession, not {type(subject).__name__}")


def safety_view(trace: Any) -> dict[str, list[dict[str, Any]]]:
    """The decisions of a trace, stripped of timing and noise."""
    gates: list[dict[str, Any]] = []
    actuators: list[dict[str, Any]] = []
    current = None
    for event in _events(trace):
        kind, data = event["type"], event.get("data", {})
        if kind == "gate_evaluation_begin":
            current = data.get("gate")
        elif kind == "gate_evaluation_result":
            entry = {"gate": current or data.get("blocked_by"), "verdict": data.get("verdict")}
            entry.update({k: data[k] for k in DECISION_FIELDS if k in data})
            gates.append(entry)
            current = None
        elif kind == "actuator_command":
            actuators.append(
                {
                    "pin": data.get("pin"),
                    "operation": data.get("operation"),
                    "duration_ms": data.get("duration_ms", 0),
                }
            )
        elif kind == "actuator_aborted":
            actuators.append({"pin": data.get("pin"), "aborted": data.get("reason")})
    return {"gates": gates, "actuators": actuators}


@dataclass(frozen=True)
class Difference:
    where: str
    golden: Any
    actual: Any
    unsafe: bool

    def __str__(self) -> str:
        label = "SAFETY REGRESSION" if self.unsafe else "changed"
        return f"{label}: {self.where}: golden {self.golden!r}, actual {self.actual!r}"


@dataclass
class GoldenDiffResult:
    golden: dict[str, Any]
    actual: dict[str, Any]
    differences: list[Difference] = field(default_factory=list)
    report: str = ""

    @property
    def ok(self) -> bool:
        return not self.differences

    @property
    def unsafe(self) -> bool:
        return any(d.unsafe for d in self.differences)

    def raise_for_regression(self, label: str = "actual") -> None:
        if self.ok:
            return
        first = self.differences[0]
        more = f" (+{len(self.differences) - 1} more)" if len(self.differences) > 1 else ""
        raise SafetyRegressionError(
            where=f"{label} -> {first.where}",
            why=f"{first}{more}",
            how=(
                "fix the regression; if the new behaviour is intended, re-record the golden "
                "reference and review the diff of its decisions in the PR"
            ),
        )


def _compare_gates(golden: list[dict], actual: list[dict]) -> list[Difference]:
    out: list[Difference] = []
    for index, (want, got) in enumerate(zip(golden, actual, strict=False)):
        where = f"gate evaluation #{index + 1} ({want.get('gate')})"
        for key in ("gate", "verdict", *DECISION_FIELDS):
            if key not in want:
                continue
            if want[key] != got.get(key):
                unsafe = key == "verdict" and want[key] == "BLOCK" and got.get(key) == "ALLOW"
                out.append(Difference(f"{where}.{key}", want[key], got.get(key), unsafe))
    for index in range(len(actual), len(golden)):
        out.append(Difference(f"gate evaluation #{index + 1}", golden[index], None, unsafe=False))
    for index in range(len(golden), len(actual)):
        extra = actual[index]
        out.append(
            Difference(
                f"gate evaluation #{index + 1}", None, extra, unsafe=extra.get("verdict") == "ALLOW"
            )
        )
    return out


def _compare_actuators(golden: list[dict], actual: list[dict]) -> list[Difference]:
    out: list[Difference] = []
    for index, (want, got) in enumerate(zip(golden, actual, strict=False)):
        if want != got:
            out.append(Difference(f"actuator command #{index + 1}", want, got, unsafe=True))
    for index in range(len(actual), len(golden)):
        out.append(Difference(f"actuator command #{index + 1}", golden[index], None, unsafe=False))
    for index in range(len(golden), len(actual)):
        # A pin command the golden never issued is the regression Action CI exists for.
        out.append(Difference(f"actuator command #{index + 1}", None, actual[index], unsafe=True))
    return out


class GoldenComparator:
    def compare(self, actual_trace: Any, golden_trace: Any) -> GoldenDiffResult:
        golden = safety_view(golden_trace)
        actual = safety_view(actual_trace)
        differences = _compare_gates(golden["gates"], actual["gates"]) + _compare_actuators(
            golden["actuators"], actual["actuators"]
        )
        report = "" if not differences else DeepDiff(golden, actual, verbose_level=2).pretty()
        return GoldenDiffResult(golden, actual, differences, report)


def load_golden(golden: str | Path | dict[str, Any]) -> dict[str, Any]:
    return golden if isinstance(golden, dict) else load_trace(Path(golden))


def assert_matches_golden(actual: Any, golden: str | Path | dict[str, Any]) -> GoldenDiffResult:
    """Raise `SafetyRegressionError` unless `actual`'s decisions equal the golden's."""
    label = str(golden) if not isinstance(golden, dict) else "golden"
    result = GoldenComparator().compare(actual, load_golden(golden))
    result.raise_for_regression(label=f"{label} vs actual")
    return result
