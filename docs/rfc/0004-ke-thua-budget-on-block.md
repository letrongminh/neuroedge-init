# RFC-0004: Child Gates Cannot Relax `budget` and `on_block`

| | |
|:---|:---|
| **RFC ID** | 0004 |
| **Title** | Extend inheritance principles 2 and 4 to `budget` and `on_block` |
| **Affected Schema** | *(none)* — resolution semantics only (`python/neuroedge/engine/gate_resolver.py`) |
| **Related PRD Requirements** | FR-GATE-06, FR-GATE-07, FR-GATE-09, NFR-RES-04 |
| **Author** | V1 — Platform Core Engineer *(drafted following `ENG-A2` finding, Phase 1 design doc)* |
| **Date Opened** | 2026-09-23 |
| **Status** | ✅ Approved · ✅ Implemented (TSK-S2-13, PR #6) |
| **Approver** | Trong-Minh Le (@letrongminh), 2026-09-23 — decision **Q-18** (`neuroedge-prd.md` §15) |

> Amending gate resolution semantics requires an RFC (`CONTRIBUTING.md` §3) even without
> touching `schemas/`. This RFC does **not** modify schemas, and does **not** modify
> the three canonical traces.

## 1. Problem

The core promise of `extends` is *a child gate is never more lax than its parent gate*.
The resolver currently maintains that promise only for `allow_when`. The following
gate **resolves successfully** on `gates/` today (reconstructed in design doc, `ENG-A2`):

```yaml
schema:  neuroedge.gate/v1
name:    lax-night
version: 1.0.0
extends: neuroedge://gates/unlock_door@1.2.0   # parent: 120 ms, closed, escalate
on_block:
  action:          degrade
  fallback_action: unlock_door_no_auth
budget:
  p95_latency_ms: 900000
  fail:           open
```

```
RESOLVED OK
  budget   = {'p95_latency_ms': 900000, 'fail': 'open'}
  on_block = {'action': 'degrade', 'fallback_action': 'unlock_door_no_auth'}
  allow_when inherited intact
```

Combined meaning: *wait for evaluation up to 15 minutes; on timeout allow through;
on block unlock door without authentication.* `allow_when` did not change a single
character, so the principle 2 check saw nothing.

## 2. Why Existing Rules Do Not Solve It

Three places, same file:

1. `_resolve_budget()` overwrites the parent's `p95_latency_ms` with the child's
   **without comparison**. The budget is the evaluation engine's timeout; expanding
   it widens the window where `fail` determines the outcome.
2. Principle 4 only prevents `fail: open` from **cascading down** from parents. It
   does not stop children from **self-declaring** `open` in a chain where the parent
   was `closed`.
3. The resolution loop comment stated *"on_block only takes effect once the action
   is already denied"*, exempting `on_block` from Appendix B.5 governance. True for
   `deny`/`escalate`/`ask`, but **false for `degrade`**: `fallback_action` **is
   executed**, meaning an alternate physical action runs instead.

## 3. Proposed Change

Three rules, applied when a document has `extends` (depth ≥ 2 of the chain).
Violation ⇒ `GateInheritanceError` (`NE2003`), conforming to the 3-part error contract.

| # | Rule | Principle B.5 | Reason |
|:---:|:---|:---:|:---|
| **R1** | Child's `budget.p95_latency_ms` **≤** parent's resolved value | 2 | Longer budget is a more lax evaluation window |
| **R2** | If parent's resolved `budget.fail` is `closed` (declared or default), child **must not declare** `fail: open` | 4 | `open` can only be retained in chains where the parent itself selected `open`; cannot be *opened up* mid-chain |
| **R3** | Child **must not introduce** `on_block.action: degrade`. Child may: retain `degrade` **with parent's exact `fallback_action`**; switch to `deny`, `escalate`, or `ask`; modify `to` / `message` | 2 | `degrade` executes an action; the other three behaviors only block and notify. Changing recipients does not change the fact that the action is blocked |

Unchanged:

- Root gates (no `extends`) declare `budget` and `on_block` arbitrarily within the schema.
- Child silence ⇒ inherits intact per RFC-0001; principle 4 still turns a parent's
  `open` into `closed` when the child does not re-declare.
- Chains where the parent is `open` allow the child to re-declare `open` —
  `fixtures/gates/valid/explicit_fail_open.yaml` remains valid.

### Runtime `on_block` Behavior (Q-17, Recorded to Give R3 Meaning)

For **every** `on_block`, the original action is blocked. `deny`: blocks. `escalate`/`ask`:
blocks + records event in trace + invokes hook (default no-op). `degrade`: executes
`fallback_action` **through its own gate**. R3 exists because `degrade` is the only
behavior that executes an additional action.

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | **Yes, for all files in repository.** Reconciled: 3 sample gates (`p95` 200 → 120 → 90, `closed`, `escalate` changes `to` at level 3), 5 `valid/` fixtures (`tightens_every_kind` 150 → 80; `explicit_fail_open` under `open` parent). Gates like `lax-night` become unresolvable — that is the intent |
| Do currently invalid files become valid? | No |
| Is a schema version bump required (`v1` → `v2`)? | **No.** Schemas are unchanged. Semantically: no gates published outside repository yet (registry is Block 3), so no external documents are broken |
| Impact on hashes / digital signatures of published gates? | None — canonical bytes of resolvable gates do not change |
| Impact on the three canonical trace files? | None |

## 5. Safety Impact

This change **strictly tightens**: it rejects additional gates, accepting no new ones.
It closes three of the four loosening surfaces identified by `ENG-A2` (`allow_when`
was closed in Sprint 1). The fourth surface — re-publishing a parent gate at the same
version — belongs to RFC-0003 (pinning `extends` via digest), deferred to Sprint 4
(`TODOS.md` #15).

Known limitation: R3 allows children to change `escalate.to`. A non-existent recipient
causes escalation to drop into a void — but the action remains blocked, making it an
availability bug rather than a safety vulnerability.

## 6. Alternatives Considered and Rejected

| Alternative | Reason for Rejection |
|:---|:---|
| Total lockdown: children with `extends` cannot declare `budget`/`on_block` | Breaks `gates/unlock_door_night@1.0.0.yaml` (switches to `night_duty_manager`, legitimate) and forbids tightening `p95` which is inherently safe |
| Full hierarchy for `on_block` (`deny > escalate > ask > degrade`, comparing `fallback_action`) | Whether `escalate` is "stricter" than `ask` is an untestable question. Only `degrade` executes an action — that is the sole boundary requiring verification |
| Defer, record risk in threat model | Core promise would be violated throughout the 2026-10-25 demo and initial PyPI release (`TSK-S3-14`) |

## 7. Verification Evidence *(`TSK-S2-13`)*

- [x] Valid examples: 3 sample gates + 5 `valid/` fixtures still resolve; added `valid/keeps_inherited_degrade.yaml`
- [x] Invalid examples: `invalid/loosens_p95.yaml` (R1), `invalid/reopens_closed_chain.yaml` (R2), `invalid/introduces_degrade.yaml` (R3), `invalid/changes_fallback_action.yaml` (R3) + corresponding entries in `expected_errors.yaml`
- [x] Automated tests: 10 `test_rfc0004_*` tests in `test_gate_resolver.py`, including the exact `lax-night` case; test suite 210 → 229, 0 skipped
- [x] `neuroedge gate lint` green on `gates/` (3) and `fixtures/gates/valid/` (6), exits 1 on `fixtures/gates/invalid/` (19)

## 8. Tasks upon Approval

- [x] Implement R1–R3 in `python/neuroedge/engine/gate_resolver.py` (`_resolve_budget`, `_resolve_on_block`), remove "on_block not subject to B.5 governance" comment; with `lru_cache` for `_gate_schema()` (TODOS #5, ENG-Q4)
- [x] Update Appendix B.5 of `docs/spec/core_contracts.md` *(session 2026-09-23)*
- [x] Update FR-GATE-06 in `neuroedge-prd.md` *(session 2026-09-23)*
- [x] Update `neuroedge-roadmap.md`: `TSK-S2-13` *(session 2026-09-23)*
- [x] Add fixtures and tests (§7); registry adds `degrade-base@1.0.0.yaml`
