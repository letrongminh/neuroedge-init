"""
Gate resolution and the five `extends` safety principles.

A gate is authored as YAML (Proposal §4.5) and may inherit from a base gate via
`extends`. Resolution flattens the chain into a single `ResolvedGate` while
enforcing Appendix B.5, which exists so that pulling a safety policy off the
community registry can never silently weaken a device:

  1. A derived gate inherits every `evaluate` criterion from its base.
  2. A derived gate may only *tighten* `allow_when` — never loosen it.
  3. A derived gate may add new `evaluate` criteria.
  4. `fail: open` is never inherited; each level must declare it explicitly.
  5. Inheritance depth is capped at 3 levels and dependency cycles are refused.

Principles 2, 4 and 5 map to FR-GATE-06, FR-GATE-07 and FR-GATE-08.

Resolution is a pure function of the gate documents: no clock, no network, no
randomness. That is what lets `neuroedge verify` prove the same chain resolves
identically on `sim`, `linux` and `esp32s3`.
"""

from __future__ import annotations

import functools
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import GateInheritanceError, GateNotFoundError, GateSchemaError
from ..paths import gates_dir, schema_path
from .arguments import merge_arguments
from .constraints import Constraint, parse_allow_when

# Appendix B.5 principle 5. A "level" is one document in the chain: the root
# counts as level 1, so at most two `extends` hops are permitted and a
# four-document chain is refused (FR-GATE-08).
MAX_INHERITANCE_LEVELS = 3

GATE_URI_PATTERN = re.compile(
    r"^neuroedge://gates/(?P<path>[a-z0-9_/-]+)@(?P<version>\d+\.\d+\.\d+)$"
)


@dataclass
class ResolvedGate:
    """
    A fully flattened gate, ready for evaluation, canonicalisation and signing.

    `chain` records the provenance root-first, so a trace can name every
    document that contributed to a verdict.
    """

    name: str
    version: str
    evaluate: dict[str, Any]
    allow_when: dict[str, Any]
    constraints: dict[str, Constraint]
    on_block: dict[str, Any]
    budget: dict[str, Any]
    chain: list[str] = field(default_factory=list)
    # RFC-0005: limits on the action's arguments, root-first; empty when none.
    arguments: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def fails_closed(self) -> bool:
        """True when a timeout or unreachable adjudicator denies the action."""
        return self.budget.get("fail", "closed") == "closed"

    @property
    def inheritance_levels(self) -> int:
        return len(self.chain)

    def to_artifact(self) -> dict[str, Any]:
        """
        The canonical resolved-gate document.

        This dict — not the YAML source — is what gets serialised to RFC 8785
        canonical JSON, hashed and signed, and what the device-side decision
        tree is compiled from.
        """
        artifact = {
            "schema": "neuroedge.gate/v1",
            "name": self.name,
            "version": self.version,
            "resolved_from": list(self.chain),
            "evaluate": self.evaluate,
            "allow_when": self.allow_when,
            "on_block": self.on_block,
            "budget": self.budget,
        }
        # Only when declared: a gate without limits keeps the digest it always had.
        if self.arguments:
            artifact["arguments"] = self.arguments
        return artifact


class GateRegistry:
    """
    Maps `neuroedge://gates/<path>@<version>` URIs onto gate documents.

    The default backing store is the monorepo's `gates/` directory, where a URI
    maps to `gates/<path>@<version>.yaml`. Tests point `root` at a fixture
    directory; the hosted registry will later swap in an OCI-backed lookup
    without changing resolution semantics.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else gates_dir()

    def path_for(self, uri: str) -> Path:
        match = GATE_URI_PATTERN.match(uri)
        if match is None:
            raise GateNotFoundError(
                where=uri,
                why="not a well-formed gate URI",
                how=(
                    "use neuroedge://gates/<namespace>/<name>@<major.minor.patch>, "
                    "e.g. neuroedge://gates/hospitality/base-access@1.0.0"
                ),
            )
        relative = f"{match.group('path')}@{match.group('version')}.yaml"
        return self.root / relative

    def load(self, uri: str) -> tuple[dict[str, Any], Path]:
        path = self.path_for(uri)
        if not path.is_file():
            raise GateNotFoundError(
                where=uri,
                why=f"no gate document at {path}",
                how=(
                    f"publish the gate with `neuroedge gate publish`, or check the "
                    f"version in the extends URI against the files in {self.root}"
                ),
            )
        return load_gate_document(path), path


@functools.lru_cache(maxsize=1)
def _gate_schema() -> dict[str, Any]:
    # Parsed once per process: resolving an N-gate registry used to re-read and
    # re-parse the schema at every level of every chain (TODOS.md #5, ENG-Q4).
    with open(schema_path("gate.v1.json"), encoding="utf-8") as handle:
        return json.load(handle)


def validate_gate_document(document: Mapping[str, Any], label: str) -> None:
    """
    Validate one gate document against schemas/gate.v1.json.

    Structural validation happens per document, before any merging, so an error
    points at the file the author actually wrote rather than at a flattened
    artifact they have never seen.
    """
    import jsonschema

    validator = jsonschema.Draft202012Validator(_gate_schema())
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
    if not errors:
        return

    first = errors[0]
    location = ".".join(str(part) for part in first.absolute_path) or "<document root>"
    raise GateSchemaError(
        where=f"{label} -> {location}",
        why=first.message,
        how=(
            "correct the field against schemas/gate.v1.json "
            "(field reference: Proposal Appendix B.1)"
        ),
    )


def load_gate_document(path: str | Path) -> dict[str, Any]:
    """Parse and schema-validate a single gate YAML file."""
    import yaml

    path = Path(path)
    if not path.is_file():
        raise GateNotFoundError(
            where=str(path),
            why="file does not exist",
            how="check the path, or run `neuroedge gate add <uri>` to fetch the gate",
        )

    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise GateSchemaError(
            where=str(path),
            why=f"file is not valid YAML: {exc}",
            how="fix the YAML syntax; gate documents are plain YAML mappings",
        ) from exc

    if not isinstance(document, dict):
        raise GateSchemaError(
            where=str(path),
            why=f"top level must be a mapping, found {type(document).__name__}",
            how="a gate document starts with `schema: neuroedge.gate/v1` at column 0",
        )

    validate_gate_document(document, label=str(path))
    return document


def _label(document: Mapping[str, Any], source: str) -> str:
    name = document.get("name", "<unnamed>")
    version = document.get("version", "<unversioned>")
    return f"{name}@{version} ({source})"


def _load_chain(
    document: Mapping[str, Any],
    source: str,
    registry: GateRegistry,
) -> list[tuple[dict[str, Any], str]]:
    """
    Walk `extends` from the leaf to the root, returning the chain root-first.

    Enforces principle 5 in both directions: the depth cap and cycle detection.
    """
    chain: list[tuple[dict[str, Any], str]] = [(dict(document), source)]
    seen: list[str] = []

    leaf_label = _label(document, source)
    current: Mapping[str, Any] = document
    current_source = source

    def walked(final: str) -> str:
        """The chain as traversed, leaf first, ending at the offending edge."""
        return " -> ".join([_label(doc, src) for doc, src in chain] + [final])

    while "extends" in current:
        parent_uri = current["extends"]

        if parent_uri in seen:
            raise GateInheritanceError(
                where=f"{leaf_label} -> extends chain",
                why=(
                    f"dependency cycle detected: {walked(parent_uri)}; "
                    f"{_label(current, current_source)} re-enters {parent_uri}"
                ),
                how="break the cycle; a gate may not inherit from its own descendant",
                principle=5,
            )
        seen.append(parent_uri)

        if len(chain) + 1 > MAX_INHERITANCE_LEVELS:
            raise GateInheritanceError(
                where=f"{leaf_label} -> extends chain",
                why=(
                    f"chain would be {len(chain) + 1} levels deep, exceeding the limit "
                    f"of {MAX_INHERITANCE_LEVELS}: {walked(parent_uri)}"
                ),
                how=(
                    "flatten an intermediate gate, or publish the shared criteria as a "
                    "single base gate so the chain fits within 3 levels"
                ),
                principle=5,
            )

        parent_document, parent_path = registry.load(parent_uri)
        chain.append((parent_document, parent_uri))
        current = parent_document
        current_source = str(parent_path)

    chain.reverse()  # root first
    return chain


def _merge_evaluate(
    inherited: Mapping[str, Any],
    child: Mapping[str, Any],
    child_label: str,
) -> dict[str, Any]:
    """
    Principles 1 and 3: inherit every base criterion, and permit new ones.

    Silently *redefining* an inherited criterion is refused. Re-typing
    `risk_level` or reordering its `levels` would change what an inherited
    `allow_when` clause means, which is a loosening that principle 2 could not
    see. Restating a criterion identically is harmless and allowed.
    """
    merged = dict(inherited)
    for criterion, definition in child.items():
        if criterion in inherited and inherited[criterion] != definition:
            raise GateInheritanceError(
                where=f"{child_label} -> evaluate.{criterion}",
                why=(
                    "redefines a criterion inherited from the base gate; "
                    f"base declares {inherited[criterion]!r}, "
                    f"this gate declares {definition!r}"
                ),
                how=(
                    f"remove evaluate.{criterion} to inherit it unchanged, or add the "
                    f"new semantics under a different criterion name"
                ),
                principle=1,
            )
        merged[criterion] = definition
    return merged


def _merge_allow_when(
    inherited: Mapping[str, Constraint],
    inherited_raw: Mapping[str, Any],
    child_constraints: Mapping[str, Constraint],
    child_raw: Mapping[str, Any],
    child_label: str,
) -> tuple[dict[str, Constraint], dict[str, Any]]:
    """
    Principle 2: every overridden clause must be at least as strict as the base.

    Clauses the child does not mention are inherited verbatim, so a child cannot
    loosen a policy by simply omitting it — omission means inheritance, not
    removal.
    """
    constraints = dict(inherited)
    raw = dict(inherited_raw)

    for criterion, child_constraint in child_constraints.items():
        base = inherited.get(criterion)
        if base is not None and not child_constraint.is_at_least_as_strict_as(base):
            raise GateInheritanceError(
                where=f"{child_label} -> allow_when.{criterion}",
                why=(
                    f"loosens the inherited condition: base admits "
                    f"{base.describe()}, this gate admits {child_constraint.describe()}"
                ),
                how=(
                    f"narrow allow_when.{criterion} to a subset of the base condition "
                    f"(base clause: {base.raw!r}), or inherit it by removing the override"
                ),
                principle=2,
            )
        constraints[criterion] = child_constraint
        raw[criterion] = child_raw[criterion]

    return constraints, raw


def _resolve_budget(
    inherited: Mapping[str, Any] | None,
    child: Mapping[str, Any] | None,
    child_label: str,
    has_base: bool = False,
) -> dict[str, Any]:
    """
    Principle 4: `fail: open` never crosses an inheritance boundary.

    A base gate declaring `fail: open` must not hand that permission to a child
    that never asked for it. The child's own document is the only thing that can
    put a resolved gate into `open`; anything else resolves to `closed`.

    RFC-0004 closes the two ways a child could still loosen the budget:
    R1 (principle 2) — a longer p95 widens the adjudication window, so a child
    may only shorten it; R2 (principle 4) — once the chain has resolved to
    `closed`, a child may not reopen it by declaring `open` itself.
    """
    budget: dict[str, Any] = dict(inherited or {})
    child = dict(child or {})

    if "p95_latency_ms" in child:
        base_p95 = budget.get("p95_latency_ms")
        if has_base and base_p95 is not None and child["p95_latency_ms"] > base_p95:
            raise GateInheritanceError(
                where=f"{child_label} -> budget.p95_latency_ms",
                why=(
                    f"p95_latency_ms {child['p95_latency_ms']} loosens the inherited "
                    f"budget of {base_p95} ms; a longer adjudication window is more permissive"
                ),
                how=f"declare p95_latency_ms <= {base_p95}, or omit it to inherit",
                principle=2,
            )
        budget["p95_latency_ms"] = child["p95_latency_ms"]

    if has_base and child.get("fail") == "open" and budget.get("fail", "closed") == "closed":
        raise GateInheritanceError(
            where=f"{child_label} -> budget.fail",
            why="declares fail: open in a chain that has already resolved to closed",
            how="omit budget.fail (closed), or start a new root gate that chooses open",
            principle=4,
        )

    budget["fail"] = "open" if child.get("fail") == "open" else "closed"

    if "p95_latency_ms" not in budget:
        raise GateSchemaError(
            where=f"{child_label} -> budget",
            why="no p95_latency_ms is declared anywhere in the inheritance chain",
            how="declare budget.p95_latency_ms on this gate or on its base",
        )
    return budget


def _resolve_on_block(
    inherited: Mapping[str, Any],
    child: Mapping[str, Any] | None,
    child_label: str,
    has_base: bool,
) -> dict[str, Any]:
    """
    RFC-0004 R3: a child may not introduce `degrade`.

    `deny`, `escalate` and `ask` only block and report, so a child may switch
    between them and change the recipient or message freely. `degrade` is the
    one behaviour that *runs* something — its `fallback_action` — so a child may
    only keep the exact `degrade` it inherited, never introduce or retarget one.
    """
    if not child:
        return dict(inherited)
    if has_base and child.get("confirms"):
        # RFC-0006: what a person may stand in for can only shrink down a chain.
        base = set(inherited.get("confirms") or ()) if inherited.get("action") == "ask" else set()
        extra = sorted(set(child["confirms"]) - base)
        if extra:
            raise GateInheritanceError(
                where=f"{child_label} -> on_block.confirms",
                why=(
                    f"lets a person's confirmation stand in for {extra}, which the inherited "
                    f"on_block does not ({sorted(base) or 'nothing'}); that is more permissive"
                ),
                how="list a subset of the inherited confirms, or omit confirms",
                principle=2,
            )
    if has_base and child.get("action") == "degrade":
        kept = inherited.get("action") == "degrade" and child.get(
            "fallback_action"
        ) == inherited.get("fallback_action")
        if not kept:
            raise GateInheritanceError(
                where=f"{child_label} -> on_block.action",
                why=(
                    "introduces degrade with fallback_action "
                    f"{child.get('fallback_action')!r}; degrade runs another action, "
                    "which is more permissive than the inherited "
                    f"{inherited.get('action')!r}"
                ),
                how=(
                    "use deny, escalate or ask, or omit on_block to inherit; "
                    "a new fallback_action needs a new root gate"
                ),
                principle=2,
            )
    return dict(child)


def _guard_opaque_allow_when(
    document: Mapping[str, Any],
    label: str,
    has_base: bool,
) -> Mapping[str, Any]:
    """
    Reject the string (CEL) form of `allow_when` inside an inheritance chain.

    Q-9 chose to compile CEL to a decision tree at build time, so a CEL string
    is legitimate for a standalone gate. But principle 2 requires *proving* that
    a child is no more permissive than its base, and subset-checking two opaque
    expressions is undecidable in general. Rather than approximate the check,
    resolution fails closed and asks the author for the structured form.
    """
    allow_when = document.get("allow_when")
    if allow_when is None:
        return {}

    if isinstance(allow_when, Mapping):
        return allow_when

    if not has_base and not document.get("extends"):
        raise GateSchemaError(
            where=f"{label} -> allow_when",
            why=(
                "the expression form is not yet supported by the resolver "
                f"(found {type(allow_when).__name__})"
            ),
            how=(
                "use the structured operator form from Proposal Appendix B.2; "
                "CEL compilation is deferred (TSK-S2-06)"
            ),
        )

    raise GateInheritanceError(
        where=f"{label} -> allow_when",
        why=(
            "a gate in an extends chain must use the structured operator form; "
            "tightening cannot be proven for an opaque expression"
        ),
        how=(
            "rewrite allow_when as a mapping of criterion to operator "
            "(Proposal Appendix B.2), or drop `extends` and inline the base conditions"
        ),
        principle=2,
    )


def resolve_gate_document(
    document: Mapping[str, Any],
    source: str = "<memory>",
    registry: GateRegistry | None = None,
) -> ResolvedGate:
    """
    Flatten a gate document and its `extends` chain into a `ResolvedGate`.

    Raises
    ------
    GateSchemaError
        The document, or one of its bases, violates gate.v1.json or Appendix B.2.
    GateInheritanceError
        The chain violates one of the five Appendix B.5 principles.
    GateNotFoundError
        A base gate named by `extends` cannot be located.
    """
    registry = registry or GateRegistry()
    validate_gate_document(document, label=source)
    chain = _load_chain(document, source, registry)

    evaluate: dict[str, Any] = {}
    constraints: dict[str, Constraint] = {}
    raw_allow_when: dict[str, Any] = {}
    on_block: dict[str, Any] = {}
    budget: dict[str, Any] | None = None
    arguments: dict[str, dict[str, Any]] = {}
    provenance: list[str] = []

    for level, (doc, doc_source) in enumerate(chain, start=1):
        label = _label(doc, doc_source)
        provenance.append(f"{doc.get('name')}@{doc.get('version')}")
        has_base = level > 1

        # Principles 1 and 3.
        evaluate = _merge_evaluate(evaluate, doc.get("evaluate", {}) or {}, label)

        # Principle 2.
        child_raw = _guard_opaque_allow_when(doc, label, has_base)
        child_constraints = parse_allow_when(child_raw, evaluate, label)
        constraints, raw_allow_when = _merge_allow_when(
            constraints, raw_allow_when, child_constraints, child_raw, label
        )

        # RFC-0004 R3 (principle 2).
        on_block = _resolve_on_block(on_block, doc.get("on_block"), label, has_base)

        # Principle 4, plus RFC-0004 R1/R2.
        budget = _resolve_budget(budget, doc.get("budget"), label, has_base)

        # RFC-0005 (principle 2 for arguments): only narrowed, never dropped.
        arguments = merge_arguments(arguments, doc.get("arguments"), label)

    leaf, leaf_source = chain[-1]
    leaf_label = _label(leaf, leaf_source)

    if not evaluate:
        raise GateSchemaError(
            where=f"{leaf_label} -> evaluate",
            why="no evaluate criteria are declared anywhere in the inheritance chain",
            how="declare at least one criterion to adjudicate before authorising the action",
        )
    if not constraints:
        raise GateSchemaError(
            where=f"{leaf_label} -> allow_when",
            why="no allow_when clause is declared anywhere in the inheritance chain",
            how=(
                "declare at least one clause; a gate with no condition would authorise "
                "every request, which the fail-closed contract forbids"
            ),
        )
    if not on_block:
        raise GateSchemaError(
            where=f"{leaf_label} -> on_block",
            why="no on_block behaviour is declared anywhere in the inheritance chain",
            how="declare on_block with one of: deny, escalate, ask, degrade (Appendix B.3)",
        )
    unknown = [c for c in on_block.get("confirms", ()) if c not in constraints]
    if unknown:
        raise GateSchemaError(
            where=f"{leaf_label} -> on_block.confirms",
            why=f"{unknown} are not allow_when criteria of this gate, so there is nothing to confirm",
            how=f"list only criteria of allow_when: {sorted(constraints)}",
        )

    return ResolvedGate(
        name=leaf["name"],
        version=leaf["version"],
        evaluate=evaluate,
        allow_when=raw_allow_when,
        constraints=constraints,
        on_block=on_block,
        budget=budget or {},
        chain=provenance,
        arguments=arguments,
    )


def resolve_gate_file(path: str | Path, registry: GateRegistry | None = None) -> ResolvedGate:
    """Load a gate YAML file from disk and resolve its inheritance chain."""
    path = Path(path)
    document = load_gate_document(path)
    return resolve_gate_document(document, source=str(path), registry=registry)


def resolve_gate_uri(uri: str, registry: GateRegistry | None = None) -> ResolvedGate:
    """Resolve a gate addressed by `neuroedge://` URI."""
    registry = registry or GateRegistry()
    document, path = registry.load(uri)
    return resolve_gate_document(document, source=str(path), registry=registry)
