"""
Canonicalisation and digests (Proposal §4.5).

Appendix A.2 requires every `digital.out` command to carry the signature of the
gate that authorised it. That only works if a gate's bytes are a function of its
meaning and nothing else — so a cosmetic YAML edit must not change the digest,
and a policy change must.
"""

from __future__ import annotations

import hashlib

import pytest

from neuroedge.engine import canonicalize, digest, gate_canonical_json, gate_digest
from neuroedge.engine.canonical import DIGEST_PREFIX
from neuroedge.engine.gate_resolver import resolve_gate_document

BASE = {
    "schema": "neuroedge.gate/v1",
    "name": "sample",
    "version": "1.0.0",
    "evaluate": {"ok": {"type": "bool", "instructions": "Placeholder"}},
    "allow_when": {"ok": True},
    "on_block": {"action": "deny"},
    "budget": {"p95_latency_ms": 100, "fail": "closed"},
}


def test_key_order_does_not_affect_the_digest():
    assert digest({"a": 1, "b": 2}) == digest({"b": 2, "a": 1})


def test_nested_key_order_does_not_affect_the_digest():
    assert digest({"x": {"p": 1, "q": 2}}) == digest({"x": {"q": 2, "p": 1}})


def test_list_order_does_affect_the_digest():
    """Lists are ordered data — `levels` ordering is semantic, not cosmetic."""
    assert digest({"a": [1, 2]}) != digest({"a": [2, 1]})


def test_canonical_form_has_no_insignificant_whitespace():
    assert canonicalize({"a": 1, "b": [1, 2]}) == b'{"a":1,"b":[1,2]}'


def test_digest_is_a_prefixed_sha256():
    value = {"a": 1}
    expected = DIGEST_PREFIX + hashlib.sha256(canonicalize(value)).hexdigest()
    assert digest(value) == expected
    assert digest(value).startswith("sha256:")


def test_cosmetic_yaml_differences_do_not_change_the_gate_digest(tmp_path):
    """
    The reason for the two-layer split: YAML has many byte forms per meaning.
    Reformatting a gate must not invalidate signatures issued against it.
    """
    from neuroedge.engine import resolve_gate_file

    terse = tmp_path / "terse.yaml"
    terse.write_text(
        "schema: neuroedge.gate/v1\n"
        "name: sample\n"
        "version: 1.0.0\n"
        "evaluate: {ok: {type: bool, instructions: Placeholder}}\n"
        "allow_when: {ok: true}\n"
        "on_block: {action: deny}\n"
        "budget: {p95_latency_ms: 100, fail: closed}\n",
        encoding="utf-8",
    )
    verbose = tmp_path / "verbose.yaml"
    verbose.write_text(
        "# a comment that carries no meaning\n"
        "budget:\n"
        '    fail:           "closed"\n'
        "    p95_latency_ms: 100\n"
        "on_block:\n"
        '    action: "deny"\n'
        "allow_when:\n"
        "    ok: true\n"
        "evaluate:\n"
        "    ok:\n"
        '        instructions: "Placeholder"\n'
        '        type:         "bool"\n'
        'version: "1.0.0"\n'
        'name:    "sample"\n'
        'schema:  "neuroedge.gate/v1"\n',
        encoding="utf-8",
    )
    assert gate_digest(resolve_gate_file(terse)) == gate_digest(resolve_gate_file(verbose))


@pytest.mark.parametrize(
    "mutation",
    [
        {"allow_when": {"ok": False}},
        {"budget": {"p95_latency_ms": 100, "fail": "open"}},
        {"budget": {"p95_latency_ms": 101, "fail": "closed"}},
        {"on_block": {"action": "escalate", "to": "human"}},
        {"version": "1.0.1"},
    ],
)
def test_a_policy_change_changes_the_digest(mutation):
    original = resolve_gate_document(BASE, source="<test>")
    changed = resolve_gate_document({**BASE, **mutation}, source="<test>")
    assert gate_digest(original) != gate_digest(changed)


def test_resolved_artifact_records_its_provenance():
    artifact = resolve_gate_document(BASE, source="<test>").to_artifact()
    assert artifact["resolved_from"] == ["sample@1.0.0"]
    assert artifact["schema"] == "neuroedge.gate/v1"


def test_canonical_json_is_utf8_bytes():
    payload = gate_canonical_json(resolve_gate_document(BASE, source="<test>"))
    assert isinstance(payload, bytes)
    payload.decode("utf-8")


def test_non_ascii_instructions_survive_canonicalisation():
    """Gate instructions are authored in Vietnamese; the digest must be stable."""
    document = {
        **BASE,
        "evaluate": {"ok": {"type": "bool", "instructions": "Khách đã xác thực"}},
    }
    resolved = resolve_gate_document(document, source="<test>")
    assert gate_digest(resolved) == gate_digest(resolve_gate_document(document, source="<test>"))
    assert "Khách đã xác thực" in gate_canonical_json(resolved).decode("utf-8")
