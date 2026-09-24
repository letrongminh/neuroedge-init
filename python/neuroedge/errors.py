"""
NeuroEdge error hierarchy.

FR-DX-04 and PRD §4.9 make a hard requirement of every diagnostic the platform
emits: it must state **where** the problem is, **why** it is a problem, and
**how to fix it**. `NeuroEdgeError` enforces that shape structurally so the
three parts cannot be forgotten, and so tests can assert on them individually.
"""

from __future__ import annotations


class NeuroEdgeError(Exception):
    """
    Base class carrying the mandatory three-part diagnostic.

    Parameters
    ----------
    where:
        The precise location: a file path, a gate URI, a criterion name, a
        source line. Never a vague subsystem name.
    why:
        What rule was broken, quoting the offending and expected values.
    how:
        A concrete next action the reader can take.
    code:
        Stable machine-readable identifier for tests and telemetry.
    """

    code = "NE0000"

    def __init__(self, where: str, why: str, how: str, code: str | None = None) -> None:
        self.where = where
        self.why = why
        self.how = how
        if code is not None:
            self.code = code
        super().__init__(self.render())

    def render(self) -> str:
        return f"[{self.code}] {self.where}\n  why: {self.why}\n  fix: {self.how}"

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "where": self.where, "why": self.why, "how": self.how}


class ActionContractViolation(NeuroEdgeError):
    """A physical actuator was commanded without a valid gate signature."""

    code = "NE1001"


class TokenReplayError(ActionContractViolation):
    """
    A verdict token was used again, after its TTL, or by another process
    instance. `reason` is ``token_replayed`` or ``token_expired``. A contract
    violation, never a retryable denial.
    """

    code = "NE1002"

    def __init__(self, where: str, why: str, how: str, reason: str) -> None:
        self.reason = reason
        super().__init__(where, why, how)

    def as_dict(self) -> dict[str, str]:
        data = super().as_dict()
        data["reason"] = self.reason
        return data


class GateError(NeuroEdgeError):
    """Base class for gate authoring, schema and resolution failures."""

    code = "NE2000"


class GateNotFoundError(GateError):
    """A gate URI or path could not be resolved to a gate document."""

    code = "NE2001"


class GateSchemaError(GateError):
    """A gate document violates schemas/gate.v1.json or the Appendix B operator set."""

    code = "NE2002"


class GateInheritanceError(GateError):
    """
    A gate chain violates one of the five extends safety principles
    (Proposal Appendix B.5 / FR-GATE-06, FR-GATE-07, FR-GATE-08).
    """

    code = "NE2003"

    def __init__(
        self, where: str, why: str, how: str, principle: int, code: str | None = None
    ) -> None:
        self.principle = principle
        super().__init__(where, why, how, code=code)

    def render(self) -> str:
        return (
            f"[{self.code}] {self.where}\n"
            f"  why: {self.why}\n"
            f"  rule: Appendix B.5 principle {self.principle}\n"
            f"  fix: {self.how}"
        )

    def as_dict(self) -> dict[str, str]:
        data = super().as_dict()
        data["principle"] = str(self.principle)
        return data


class BoardCapabilityError(NeuroEdgeError):
    """A board declaration is malformed or does not satisfy a requested capability."""

    code = "NE3001"


class AgentManifestError(NeuroEdgeError):
    """`agent.toml` is malformed, or an `@action` disagrees with it (FR-ACE-04/05)."""

    code = "NE3002"


class BuildFailed(NeuroEdgeError):
    """
    `neuroedge build` found one or more problems. Carries every problem so one
    run reports them all, each with its own three-part diagnostic.
    """

    code = "NE3003"

    def __init__(self, where: str, problems: list[NeuroEdgeError]) -> None:
        self.problems = list(problems)
        super().__init__(
            where=where,
            why=f"{len(self.problems)} problem(s) found; the build produced no artifacts",
            how="fix each problem listed below, then build again",
        )


class TraceValidationError(NeuroEdgeError):
    """A trace file violates schemas/trace.v1.json."""

    code = "NE4001"


class SafetyRegressionError(NeuroEdgeError, AssertionError):
    """
    A replayed session's gate verdicts or pin commands differ from its golden
    reference (FR-CI-04). An `AssertionError` too, so pytest reports it as a
    failed test rather than an error.
    """

    code = "NE4002"


class ReplayError(NeuroEdgeError):
    """A trace cannot be replayed against this agent — not a verdict difference."""

    code = "NE4003"


class VerificationError(NeuroEdgeError):
    """
    `neuroedge verify` found nothing to verify in one category — no gate, no
    canonical trace, or no replay — or the directory is missing (FR-CLI-03).
    A sweep over zero artifacts must never read as a pass.
    """

    code = "NE4004"


class PerceptionUnavailableError(NeuroEdgeError):
    """
    A perception component cannot be constructed: a missing or malformed command
    grammar, an unknown model reference. Raised at build or load time; at run time
    the engine turns an unrunnable fallback into a `gate_unreachable` verdict.
    """

    code = "NE5001"
