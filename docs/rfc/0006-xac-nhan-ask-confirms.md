# RFC-0006: Gates Declare Criteria Humans Can Confirm Instead — `on_block.confirms`

| | |
|:---|:---|
| **RFC ID** | 0006 |
| **Title** | `on_block: ask` with `confirms`: criteria that human confirmation on device can replace |
| **Affected Schema** | `gate.v1` (adds optional field in `on_block`) · resolution semantics · evaluation |
| **Related PRD Requirements** | FR-ACE-10, FR-GATE-06, NFR-SEC-09 |
| **Author** | V1 — Platform Core Engineer *(per TSK-S3-26)* |
| **Date Opened** | 2026-09-24 |
| **Status** | ✅ Approved · ✅ Implemented (TSK-S3-26, PR #25; C walker: TSK-S4-02, PR #27) |
| **Approver** | Trong-Minh Le (@letrongminh, lead architect), 2026-09-24 — selected "explicitly declared in gate" (Option A) among three options in §6 |
| **Verification** | §7 — `python/tests/test_tool_confirm.py`, corpus `fixtures/gates/invalid/` |

> **When an RFC is required:** all changes in `schemas/`, and all changes to gate resolution
> semantics. See `CONTRIBUTING.md` §3 for exact boundaries.

## 1. Problem

Q-26 decided: when a gate returns `on_block: ask`, **only humans, via device channels**,
may confirm, and confirmation triggers the gate to **re-evaluate** rather than bypassing
the gate. But `allow_when` is an **AND** of all clauses:

```yaml
# fixtures/agents/home-voice/gates/light_off@1.0.0.yaml (before RFC)
allow_when:
  call_source: { in: [local_grammar, system_one, system_two, mcp] }
  room_empty:  true
on_block: { action: ask, message: "Vẫn còn người trong phòng — bạn chắc muốn tắt đèn?" }
```

Room occupied ⇒ `room_empty = false` ⇒ BLOCK ⇒ ask. User answers "có" ("yes"). Adding
fact `human_confirmed = true` and re-evaluating: `room_empty` **remains** false, gate
**still** blocks. Confirmation never takes effect — `docs/spec/tool_calling.md` §6 v0 made
this exact mistake.

## 2. Why the Current Schema Does Not Solve It

- Structured `allow_when` only supports AND (Appendix B.2); CEL string form (which has OR)
  is forbidden in inheritance chains (RFC-0001) and not accepted by the resolver.
- `on_block` specifies `additionalProperties: false`: leaving no place to specify "what
  humans can replace".

## 3. Proposed Change

```yaml
on_block:
  action:   ask
  message:  "Vẫn còn người trong phòng — bạn chắc muốn tắt đèn?"
  confirms: [room_empty]        # new: criteria human confirmation can replace
```

```json
"confirms": {
  "type": "array", "items": { "type": "string", "minLength": 1 },
  "minItems": 1, "uniqueItems": true
}
// and in on_block's allOf: if confirms is present, action must be "ask"
```

**Semantics.**

1. Each element of `confirms` is an `allow_when` criterion (checked by resolver, mismatch ⇒
   `GateSchemaError`). Valid only with `action: ask` (enforced by schema).
2. When a gate blocks, a question is only **opened** (`tool_confirm_requested`) if a "có" ("yes")
   answer is **sufficient** to allow: given current facts, with criteria in `confirms` assumed
   satisfied, the gate must ALLOW. If the gate blocked due to a criterion not in `confirms`,
   or an argument constraint (RFC-0005), humans are not asked questions they cannot resolve.
3. When a human confirms (only `local_grammar` or `ui`, Q-26), the gate is **re-evaluated**
   with current facts and the original request's call source; criteria in `confirms` are assumed
   satisfied, while **all other criteria, argument constraints, and fail-closed still apply**.
   The result records `confirmed: [...]` in `gate_evaluation_result`.
4. Degraded adjudicators (`gate_unreachable`, `budget_exceeded`) still block per `budget.fail`
   — confirmation cannot replace a question no one could answer.

**Inheritance (B.5, principle 2).** Child gates may only **remove** elements from `confirms`:
adding a criterion, or switching from `deny`/`escalate` to `ask` with `confirms`, is a relaxation ⇒
`GateInheritanceError`. A child gate declaring `on_block` without `confirms` is a tightening — permitted.

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | Yes — `confirms` is optional |
| Do currently invalid files become valid? | Yes, exactly one category: `on_block` with `confirms` under `ask`. Schema relaxation, permissible within `v1` |
| Is a schema version bump required? | No |
| Impact on hashes of published gates? | None — gates without `confirms` hash identically to before |
| Impact on the three canonical trace files? | None |

## 5. Safety Impact

- No gate becomes more lax without explicitly declaring `confirms`: by default `ask` is informational only.
- Gate authors decide **in advance** what can be confirmed; users cannot override `call_source`,
  authentication, or argument constraints unless the gate lists them.
- Models and MCP clients have no path to confirm: no confirmation tool exists, and
  `ConfirmationBook` rejects all sources outside `HUMAN_SOURCES` (tested).
- Inheritance only narrows `confirms` (counterexample corpus present).

## 6. Alternatives Considered and Rejected

| Alternative | Reason for Rejection |
|:---|:---|
| Confirmation replaces whichever criterion just blocked (no schema change) | A "có" ("yes") response would override any criterion, including "guest unauthenticated" — something gate authors never permitted |
| Add OR (`any_of`) to `allow_when` | Must rewrite "child stricter than parent" proofs for expressions with OR, complicating the C walker; disproportionate to need |
| `human_confirmed` fact + current `allow_when` | Inexpressible (§1) |

## 7. Verification Evidence

- [x] Valid: `fixtures/gates/valid/narrows_confirms.yaml` (narrows `fixtures/gates/registry/ask-base@1.0.0.yaml`)
- [x] Counterexamples + `expected_errors.yaml`: `widens_confirms`, `introduces_confirms`, `confirms_without_ask`, `confirms_unknown_criterion`
- [x] `python/tests/test_tool_confirm.py`: actual confirmation turns off light through gate; only `local_grammar`/`ui`; single-use; expires; gate change ⇒ invalidates; only replaces declared criteria; does not ask when "có" is insufficient; degraded adjudicator still blocks; replay yields identical verdict
- [x] `neuroedge verify` remains green; three canonical traces unchanged

## 8. Tasks upon Approval

- [x] `schemas/gate.v1.json`
- [x] Appendix B.3 in `docs/spec/core_contracts.md`; `docs/spec/tool_calling.md` §6
- [x] `neuroedge-prd.md` Q-26, FR-ACE-10 · `neuroedge-roadmap.md` TSK-S3-26
- [x] Resolver, Python walker (`waived`), engine (`confirmed`), `c.do()`/`c.confirm()`, REPL, UI, `gate explain`, replay
- [x] C walker (TSK-S4-02) receives replaceable criteria set — RFC-0003 binary layout carries `confirms` (`confirm_mask`, PR #27)
