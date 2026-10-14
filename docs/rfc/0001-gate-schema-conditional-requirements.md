# RFC-0001: Conditional Field Requirements for Inherited Gates

| | |
|:---|:---|
| **RFC ID** | 0001 |
| **Affected Schema** | `gate.v1` |
| **Related PRD Requirements** | FR-GATE-02, FR-GATE-06, FR-GATE-07, FR-GATE-08, FR-DX-04 |
| **Author** | V1 — Platform Core Engineer |
| **Date Opened** | 2026-09-21 |
| **Status** | ✅ Approved · ✅ Implemented (TSK-S1-02, commit `de411c5`) |
| **Verification** | `python/tests/test_gate_fixtures.py`, `python/tests/test_gate_resolver.py` |

## 1. Problem

The initial `gate.v1.json` **could not validate an inherited gate**. Three independent
issues, all three discovered while implementing the resolver and writing three sample
gates:

### 1a. Unconditional Required Fields Block Principle 1

```json
"required": ["schema", "name", "version", "evaluate", "allow_when", "on_block", "budget"]
```

Inheritance principle 1 (Appendix B.5) states that child gates **automatically inherit the entirety**
of `evaluate` from parent gates. But the schema forced every document to declare `evaluate`,
`allow_when`, `on_block`, and `budget` itself. Consequence: a child gate wanting to inherit
had to copy the parent gate entirely — the exact thing `extends` exists to eliminate.

The following minimal document **must be valid** per Appendix B.5 but was rejected by
the schema:

```yaml
schema:  neuroedge.gate/v1
name:    unlock-door-night
version: 1.0.0
extends: neuroedge://gates/unlock_door@1.2.0
```

### 1b. `budget.fail` Is Both Required and Has a Default Value

```json
"budget": {
  "required": ["p95_latency_ms", "fail"],
  "properties": {
    "fail": { "enum": ["closed", "open"], "default": "closed" }
  }
}
```

This is an internal contradiction: for a required field, the default value is never
used. Appendix B.4 explicitly states `closed` is the **"Default"**, so `fail`
must be an optional field.

This contradiction has direct safety consequences. Principle 4 states `fail: open`
**is not inherited** and must be explicitly declared at each level. The natural way
to express "this level does not request fail-open" is **to write nothing** — and the
default must be `closed`. Requiring `fail` forced every child gate to manually write
`fail: closed`, where a single omission became a validation error instead of safe
behavior.

### 1c. Four `on_block` Behaviors Lack Corresponding Required Parameters

Appendix B.3 specifies `escalate` routes `to:`, `ask` prompts with `message:`,
and `degrade` switches to `fallback_action:`. The schema only required `action`, so
the following gate was valid per schema but meaningless at runtime:

```yaml
on_block:
  action: escalate     # escalate to whom?
```

## 2. Why the Current Schema Does Not Solve It

All three are limitations of flat JSON Schema: lacking `if`/`then`, it cannot express
"require X only when Y is absent". Draft 2020-12 supports `if`/`then` inside `allOf`,
so no draft version change is needed.

## 3. Proposed Change

### 3a. Required Fields Depend on the Presence of `extends`

```json
"required": ["schema", "name", "version"],
"allOf": [
  {
    "if":   { "not": { "required": ["extends"] } },
    "then": { "required": ["schema", "name", "version",
                           "evaluate", "allow_when", "on_block", "budget"] }
  }
]
```

Root gates (no `extends`) must still declare the full contract — no relaxation
here. Derived gates are allowed to inherit.

### 3b. `budget.fail` Becomes Optional, Absence Means `closed`

```json
"budget": { "required": ["p95_latency_ms"] }
```

### 3c. `on_block` Parameters Required per Behavior

```json
"allOf": [
  { "if":   { "properties": { "action": { "const": "escalate" } }, "required": ["action"] },
    "then": { "required": ["action", "to"] } },
  { "if":   { "properties": { "action": { "const": "ask" } }, "required": ["action"] },
    "then": { "required": ["action", "message"] } },
  { "if":   { "properties": { "action": { "const": "degrade" } }, "required": ["action"] },
    "then": { "required": ["action", "fallback_action"] } }
]
```

### 3d. Accompanying Tightening

Three minor items, following the same spirit of "the schema says exactly what Appendix B says":

| Field | Change |
|:---|:---|
| `extends` | Add `pattern` for URI `neuroedge://gates/<path>@<semver>` |
| `evaluate.*` | `level` requires `levels`; `choice` requires `options`; `bool` must not have either |
| `evaluate` | `minProperties: 1` — gate must evaluate at least one quantity |

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | **Yes**, except for the two cases below |
| Do currently invalid files become valid? | **Yes** — minimal derived gates, and `budget` without `fail` |
| Is a schema version bump required? | **No** — see reasoning below |
| Impact on digital signatures of published gates? | **None** — no gates published yet; Gate Registry is Block 3 |
| Impact on the three canonical trace files? | **None** — changes are only in `gate.v1` |

**Two tightening cases** (3c and 3d) cause some currently valid documents to become
invalid — in principle, a breaking change. We still keep `v1` because: the schema has
not been published outside the team, no gates have been signed yet, and freezing the
schema is itself an **active** item of Sprint 1. After Sprint 1 closes, any change
of this nature must go to `gate.v2`.

All documents eliminated by tightening are **meaningless at runtime** (`escalate`
without recipient, `level` without scale, gate evaluating nothing). No meaningful
documents are lost.

## 5. Safety Impact

**Does this change make gates more lax: no.** Item by item:

| Change | Safety Direction Impact |
|:---|:---|
| 3a — conditional required fields | Neutral. Root gates must still declare everything. Derived gates inherit through the resolver, where the five B.5 principles are enforced |
| 3b — optional `fail` | **Tightened.** Absence means `closed`. Before the change, forgetting `fail` was a validation error; after the change, forgetting `fail` is the safest behavior. This is also what makes principle 4 expressible |
| 3c — `on_block` parameters | **Tightened.** Eliminates escalation gates with no recipient |
| 3d — `extends` pattern, `evaluate` types | **Tightened.** Eliminates unresolvable URIs and unevaluable criteria |

One point to state clearly: item 3a transfers the responsibility of enforcing
principles 1–5 from JSON Schema to the **resolver** (`python/neuroedge/engine/gate_resolver.py`).
JSON Schema cannot express "child gate may only tighten `allow_when`" — that is a
proposition over two documents, whereas a schema validates only one. Therefore:

> **Schema validation alone is NOT sufficient to conclude a gate is safe.**
> `neuroedge gate resolve` is the true check gate. A document passing only the
> schema without being resolvable cannot be loaded onto devices.

This has been recorded in `CONTRIBUTING.md` §3 and enforced in CI: workflow
`ci-sim-linux.yml` runs `neuroedge gate lint`, not just schema validation.

### Resulting Consequence: Expression-Form `allow_when` in Inheritance Chains

While implementing principle 2, a fourth issue emerged and is addressed here under
the same theme: `allow_when` permits both **expression strings** (CEL, for Q-9
option A) and **operator mappings** (Appendix B.2).

Principle 2 requires **proving** that the child gate is not more lax than the
parent gate. With mappings, the proof compares accepted value sets. With two
arbitrary CEL strings, that is an **undecidable** problem in the general case.

**Decision:** the resolver **rejects** string form when a gate is in an inheritance
chain, raising `GateInheritanceError` citing principle 2. Fail-closed instead of
approximating a safety check. Standalone gates (no `extends`, no children) may
still use CEL once the gate compiler is completed in TSK-S2-06.

Recorded in the schema description for the `allow_when` field.

## 6. Alternatives Considered and Rejected

| Alternative | Reason for Rejection |
|:---|:---|
| Force child gates to copy all fields from parent gates | Destroys the value of `extends`; every parent gate change requires manual edits across all child gates, silently diverging if forgotten |
| Drop `required` completely, let resolver check everything | Loses file-level diagnostics. Errors would point to flattened artifacts — something authors never see — rather than the lines they just wrote. Violates FR-DX-04 |
| Create `gate.v2` for inherited gates | Two schemas for one concept; `extends` is a core v1 feature per Appendix B.1, not an extension |
| Approximate CEL comparison via parsing | A safety check that is "mostly" correct fails exactly on the edge cases attackers target |

## 7. Verification Evidence

- [x] Valid examples: `fixtures/gates/valid/` (5 files) and `gates/` (3 sample gates)
- [x] Invalid examples with expected error messages: `fixtures/gates/invalid/` (15 files) and `fixtures/gates/expected_errors.yaml`
- [x] Automated tests: `test_gate_resolver.py` (35 tests, covering all 5 principles), `test_gate_fixtures.py` (40 tests), `test_sample_gates.py` (26 tests)
- [x] `neuroedge gate lint` green on `gates/`, red on `fixtures/gates/invalid/`
- [x] Direct case for 1a: `fixtures/gates/valid/inherits_on_block_and_budget.yaml` — 4-line identity document resolves to full contract
- [x] Direct case for 1b: `fixtures/gates/valid/inherits_fail_open_as_closed.yaml` — parent gate `fail: open`, child gate silent, result is `closed`

## 8. Tasks Completed

- [x] Update `schemas/gate.v1.json`
- [x] Note `$comment` referencing RFC-0001 at root `allOf` block
- [x] Implement enforcement of 5 principles in `python/neuroedge/engine/gate_resolver.py`
- [x] Add fixtures and tests
- [x] Update `neuroedge-roadmap.md` (TSK-S1-02, TSK-S1-03, Exit Criteria 1 and 2)
- [x] Synchronize Appendix B.1, B.3, and B.4 of `docs/spec/core_contracts.md` — *completed 2026-09-23, proposal v5.5*

## 9. Open Tasks

Appendix B.1 of `docs/spec/core_contracts.md` marked `evaluate`, `allow_when`,
`on_block`, and `budget` as unconditionally **"Required"**, and Appendix B.4 called
`closed` "Default" without clarifying that the field is optional. Following this
RFC, those two sections must be reworded to match:

- B.1: clarify that the four fields are required **for root gates**, and inheritable when `extends` is present
- B.4: clarify that `fail` is an **optional** field, where absence means `closed`
- B.3: clarify required parameters per behavior

This is a textual amendment to the proposal, not a change to code or schema, so it
is separated from this RFC to keep scope clean.
