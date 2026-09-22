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


class TraceValidationError(NeuroEdgeError):
    """A trace file violates schemas/trace.v1.json."""

    code = "NE4001"
