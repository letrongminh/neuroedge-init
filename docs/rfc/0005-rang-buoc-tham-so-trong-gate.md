# RFC-0005: Gates Declare Action Argument Constraints

| | |
|:---|:---|
| **RFC ID** | 0005 |
| **Title** | `arguments:` block in gates — tool call argument constraints, narrowing-only inheritance |
| **Affected Schema** | `gate.v1` (adds optional field) · resolution semantics · Q-23 binary layout |
| **Related PRD Requirements** | FR-ACE-08, FR-GATE-06, FR-MDL-10 |
| **Author** | V1 — Platform Core Engineer *(per decision Q-25)* |
| **Date Opened** | 2026-09-23 |
| **Status** | ✅ Approved · ✅ Implemented (TSK-S3-25, PR #22; C walker: TSK-S4-02, PR #27) |
| **Approver** | Trong-Minh Le (@letrongminh, lead architect), 2026-09-24 — decision **Q-25** (`neuroedge-prd.md` §15); no `arguments_closed` in v1 |
| **Verification** | §7 — `python/tests/test_gate_arguments.py`, corpus `fixtures/gates/invalid/`, `fixtures/tool_calls/invalid/` |

> **When an RFC is required:** all changes in `schemas/`, and all changes to gate resolution
> semantics. See `CONTRIBUTING.md` §3 for exact boundaries.

## 1. Problem

Since Q-24, actions arrive from LLMs and MCP clients, not just pre-composed commands.
The model selects **arguments too**. Today's gates do not see arguments:

```python
# System 2 prompt-injected, or simply mistaken
ToolCall("unlock_door", {"guest_id": "101", "duration_s": 3600}, source="system_two")
```

Gate `unlock_door@1.2.0` checks authenticated guest, room match — and allows through.
The door unlocks for one hour. There is no way to write *"at most 60 seconds"* in the gate.

## 2. Why the Current Schema Does Not Solve It

- `evaluate` only supports three types `bool` / `level` / `choice` (Appendix B.2), and
  each criterion is a **fact** supplied by System 1 or session — not a call argument.
- `gate.v1.json` sets `additionalProperties: false` at top level, leaving no place for declarations.
- A workaround is computing facts at the agent (`duration_ok = duration_s ≤ 60` in
  `agent.toml`). But then the **meaning** of `duration_ok` lives outside the gate: an agent author
  writing `duration_ok = duration_s ≤ 3600` loosens a shared gate without `gate lint`
  noticing — violating the core promise of `extends` (B.5). Q-25 rejected this approach.

## 3. Proposed Change

Add optional top-level field `arguments`:

```yaml
schema:  neuroedge.gate/v1
name:    unlock_door
version: 1.3.0
arguments:                      # new — constraints on @action arguments
  duration_s: { type: integer, minimum: 1, maximum: 60 }
  guest_id:   { type: string, max_length: 16 }
evaluate: { ... }               # unchanged
allow_when: ...                 # unchanged
```

```json
"arguments": {
  "type": "object",
  "additionalProperties": {
    "type": "object",
    "required": ["type"],
    "properties": {
      "type":       { "enum": ["string", "integer", "number", "boolean"] },
      "minimum":    { "type": "number" },
      "maximum":    { "type": "number" },
      "enum":       { "type": "array", "minItems": 1 },
      "max_length": { "type": "integer", "minimum": 0 }
    },
    "additionalProperties": false
  }
}
```

**Evaluation.** Argument constraints run **before** `evaluate`, deterministically, with
zero model budget cost. Violation ⇒ `BLOCK`, `reason = argument_out_of_range`,
`failed_criterion = <argument name>`, followed by `on_block` like any block. An argument
present in `arguments` but absent in `@action` ⇒ `neuroedge build` error (gate and action mismatch).

**Inheritance (B.5).** Child gates may only narrow:

| Constraint | Child Permitted |
|:---|:---|
| `minimum` / `maximum` | Increase / decrease (effective range is **intersection** with parent) |
| `enum` | Subset of parent |
| `max_length` | Less than or equal |
| `type` | Unchanged |
| Remove parent-declared constraint | **Impossible** — not restating means inheriting intact, identical to `allow_when`; no syntax exists for removal |

Empty range after intersection (`minimum > maximum`) ⇒ `GateSchemaError`: a gate that
can never allow is an invalid gate.

**Compiler and MCU.** `neuroedge build` emits argument-comparison nodes preceding the
decision tree. The Q-23 binary layout adds a node kind (`ARG_CMP`: argument index,
comparison operation, constant) and **bumps layout version** — before TSK-S4-02 writes
the C walker, so no devices need re-flashing.

**Tool schema.** `mcp tools` and `openai` include constraints in `inputSchema`
(`minimum`, `maximum`, `enum`, `maxLength`), so models see boundaries before calling
(`docs/spec/tool_calling.md` §3).

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | Yes — `arguments` is optional |
| Do currently invalid files become valid? | Yes, exactly one category: gates with an `arguments` block (currently rejected by `additionalProperties: false`). Schema relaxation, permissible within `v1` |
| Is a schema version bump required (`v1` → `v2`)? | No |
| Impact on hashes / digital signatures of published gates? | None — gates without `arguments` hash identically to before |
| Impact on the three canonical trace files? | None |

## 5. Safety Impact

This change adds only ways to **block**; there is no path to make a gate more lax:

- Gates without `arguments` retain identical semantics.
- Inheritance only narrows, and not restating means inheriting so constraints cannot be dropped — matching the shape of Q-18 for `budget`.
- Constraints execute deterministically before the model, introducing no new degradation causes
  (`gate_unreachable` / `budget_exceeded` do not apply).

One point requiring review: arguments **not** declared in `arguments` are unconstrained beyond
signature types. Should there be an `arguments_closed: true` mode forcing all arguments to be declared?
**Decision (2026-09-24): no** in v1 — add later if the first shared gate requires it.

## 6. Alternatives Considered and Rejected

| Alternative | Reason for Rejection |
|:---|:---|
| `argument_facts` in `agent.toml` (boolean facts computed from arguments) | Safety meaning resides outside the gate: agent authors can loosen without `lint` noticing; gates shared via registry do not carry constraints (Q-25) |
| CEL expression over arguments in `allow_when` (`arguments.temp <= 30`) | Inheritance cannot compare arbitrary expressions to prove "child is stricter"; MCU lacks CEL (Q-9) |
| Rely solely on tool JSON Schema | Advisory for models, not enforcement; MCP clients can bypass it |

## 7. Verification Evidence

- [x] Valid example: `fixtures/gates/valid/narrows_arguments.yaml` narrows all four constraint kinds from
  `fixtures/gates/registry/args-base@1.0.0.yaml`. *(Do not edit `gates/unlock_door@1.2.0.yaml`: changing it changes
  digests of the three canonical traces.)*
- [x] Counterexamples in `fixtures/gates/invalid/` + `expected_errors.yaml`: relaxing `maximum`, lowering `minimum`, non-subset enum,
  type changes, empty intervals, string upper bounds, unknown keywords
- [x] Test (`python/tests/test_gate_arguments.py`): `ToolCall` with `duration_s = 3600` from `system_two` ⇒ BLOCK
  `argument_out_of_range`, pins unchanged, no facts queried; default values also verified; agent
  on `sim` records and replays to identical verdict
- [x] `neuroedge verify` remains green; three canonical traces unchanged

## 8. Tasks upon Approval

- [x] Update `schemas/gate.v1.json`
- [x] Appendix B.6 in `docs/spec/core_contracts.md` promoted from "proposal" to normative
- [x] `neuroedge-prd.md` FR-ACE-08 promoted to P0
- [x] `neuroedge-roadmap.md` TSK-S3-25 ✅ · TSK-S4-02 (C walker reads tree `arguments` block)
- [x] Resolver, `gate lint`, compiler (`check_gate_arguments`), decision tree, engine, `c.do()` (default
  values), `input_schema()`, `gate explain`; fixtures and tests
