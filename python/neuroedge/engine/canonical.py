"""
Canonicalisation of resolved gates for hashing and signing.

Proposal §4.5 sets up a deliberate two-layer split:

  * authors write YAML, which is pleasant to review in a pull request but has
    many byte representations for the same meaning (indentation, key order,
    quoting style);
  * the system compiles that to **RFC 8785 canonical JSON (JCS)**, which has
    exactly one byte representation per value.

Only the canonical form is hashed and signed. Appendix A.2 requires every
`digital.out` command to carry the signature of the gate that authorised it, so
a gate digest that shifted with cosmetic YAML edits would invalidate signatures
on every reformat.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from .gate_resolver import ResolvedGate

DIGEST_ALGORITHM = "sha256"
DIGEST_PREFIX = f"{DIGEST_ALGORITHM}:"


def canonicalize(value: Mapping[str, Any]) -> bytes:
    """
    Serialise a mapping to RFC 8785 canonical JSON bytes.

    Deterministic across runs, machines and Python versions: keys sort by UTF-16
    code unit, numbers use the shortest round-tripping form, and there is no
    insignificant whitespace.
    """
    import rfc8785

    return rfc8785.dumps(value)


def digest(value: Mapping[str, Any]) -> str:
    """Prefixed SHA-256 digest of the canonical form, e.g. ``sha256:1f3a...``."""
    return DIGEST_PREFIX + hashlib.sha256(canonicalize(value)).hexdigest()


def gate_digest(gate: ResolvedGate) -> str:
    """
    Digest of a resolved gate.

    Computed over the *resolved* artifact rather than the authored YAML, so two
    gates that reach the same policy by different inheritance routes are
    distinguishable only if their effective policy differs.
    """
    return digest(gate.to_artifact())


def gate_canonical_json(gate: ResolvedGate) -> bytes:
    """The exact byte stream that gets hashed, signed and shipped to devices."""
    return canonicalize(gate.to_artifact())
