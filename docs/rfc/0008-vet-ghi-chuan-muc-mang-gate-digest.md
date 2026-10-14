# RFC-0008: Three Canonical Traces Carry `gate_digest` — Replay Checks It

| | |
|:---|:---|
| **RFC ID** | 0008 |
| **Title** | Three canonical traces carry `gate_digest` in `gate_evaluation_begin`; `verify` and `replay` check it |
| **Affected Contract** | `trace.v1` *(only `data` payload of the three canonical traces — schema file unchanged)* · replay semantics |
| **Related PRD Requirements** | FR-CI-02, FR-CI-04, FR-CI-07, FR-TRC-04 |
| **Author** | V1 — Platform Core Engineer |
| **Date Opened** | 2026-09-27 |
| **Status** | ✅ Approved · ✅ Implemented (this PR) |
| **Approver** | Product Owner, 2026-09-27 |
| **Verification** | §7 — `python/tests/test_player.py`, `python/tests/test_cli.py`, `python/tests/test_trace_vectors.py` |

> **When an RFC is required:** modifying the three canonical traces is an item in `CONTRIBUTING.md` §3.

## 1. Problem

The engine today records `gate_evaluation_begin {gate, gate_digest}` (`engine/gate.py`),
as does the device (`simulation_coverage.md` §4). But the three canonical traces in
`fixtures/traces/` (`happy-path.json`, `unverified_attempt.json`, `network_offline.json`)
predated this field: their `gate_evaluation_begin` only carries `{"gate": "unlock_door@1.2.0"}`.
Anyone implementing `trace.v1` from the three canonical examples would never see that field,
even though it enables on-device verdicts to trace back to the signed policy (ENG-T2, RFC-0003 §3).

## 2. Why the Status Quo Does Not Solve It

- `neuroedge verify` compares canonical traces against their goldens across all three targets,
  but on `sim`/`linux` no check ensures the trace was decided by the **exact gate it was recorded with**
  — the device checks (`_device_replay`), while host did not.
- `neuroedge replay` on user traces is unaware that gates changed since recording: users
  tightening gates and replaying (quickstart, hour 3) are not told that verdicts are being
  evaluated with the new gate.
- Traces without `gate_digest` cannot check either condition — necessitating changes to
  the three canonical traces, which requires an RFC.

## 3. Proposed Change

Each `gate_evaluation_begin` of the three canonical traces receives the exact value that
checkout compiles today for `unlock_door@1.2.0` (`compile_tree(resolve_gate_file("gates/unlock_door@1.2.0.yaml"))`):

```diff
     {
       "offset_ms": 550,
       "type": "gate_evaluation_begin",
-      "data": { "gate": "unlock_door@1.2.0" }
+      "data": {
+        "gate": "unlock_door@1.2.0",
+        "gate_digest": "sha256:2c20dc42616dbf9a3bf16b7967c3b01faa579e1186f55b928a85070a318a9ab5"
+      }
     }
```

Nothing else in the three files changes: JCS deviation ⇒ file `digest()` changes ⇒ firmware
vectors regenerated (`scripts/gen_firmware_vectors.py` embeds `digest(trace)` into `device_info.trace_digest`).

**Two replay rules, comparison housed in a single function** (`testing/player.gate_digest_changes`,
shared by host and device):

| Command | Trace | Recorded `gate_digest` Differs from Checkout Compilation |
|:---|:---|:---|
| `neuroedge verify` | Canonical (frozen gates) | **Error** (`ReplayError`, NE4003) — canonical trace must be evaluated by the exact gate it was recorded with, identical to device behavior |
| `neuroedge replay` | User trace | **No error** — gates may be intentionally tightened (quickstart hour 3); replay still re-evaluates verdicts and reports `SAFETY REGRESSION` as before, adding a warning indicating which gate changed (old digest → new digest) |

Traces lacking the field (recorded before RFC-0008) replay exactly as before — having nothing to compare.

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | Yes — `trace.v1` leaves `data` open; adding keys to `data` requires no schema change |
| Do currently invalid files become valid? | No |
| Is a schema version bump required (`v1` → `v2`)? | No — `schemas/trace.v1.json` is unchanged |
| Impact on hashes / digital signatures of published gates? | None — `digests.lock` only locks gates; gates are unchanged |
| Impact on the three canonical trace files? | **Yes — this exact change** (RFC); `digest()` of each file changes, firmware vectors regenerated |
| Which gates in `digests.lock` change digest? | No gates |
| Does the `NETR` layout or C walker need to change? | No — device already recorded `gate_digest` previously (`ne_trace.c`) |
| Which answers in the tool-call corpus (`expected_results.yaml`) change? | No |

Legacy traces without the field remain replayable (section 3); `verify` on device rejects
older firmware as before.

## 5. Safety Impact

This change **has no path to make verdicts more lax**:

- The check only **adds** a rejection condition, dropping none: golden compares decisions
  as before, `SAFETY REGRESSION` (NE4002) as before, fail-closed as before.
- In `verify`, canonical traces decided by gates other than those recorded with them are
  errors, never allowed to pass — a "pass" on a different gate is a meaningless result.
- In `replay`, warnings do not alter comparisons: users tightening gates that weaken safety
  still exit with code 1 and `SAFETY REGRESSION`. The warning merely states the fact
  "this verdict was evaluated using a new gate" — identical pattern to existing `[sim.sensor_facts]`
  warning (`_sensor_rules_changed`).
- Traces lacking the field are not compared (nothing to compare): this **preserves legacy
  behavior**, rather than bypassing an existing check.

## 6. Alternatives Considered and Rejected

| Alternative | Reason for Rejection |
|:---|:---|
| Modify `schemas/trace.v1.json` to require `gate_digest` in `gate_evaluation_begin` | Schema change requires dedicated RFC; traces recorded before RFC-0008 would become invalid — unnecessary breaking change |
| `verify` only warns like `replay` | Canonical traces and their gates freeze together; "passing" on a different gate evaluates a different entity |
| `replay` also errors when gates differ | Replay after gate tightening is an intended workflow (quickstart hour 3); erroring breaks the exact scenario replay is designed to verify |

## 7. Verification Evidence

- [x] Three canonical traces carry the field, matching compiled checkout values —
  `python/tests/test_player.py::test_canonical_traces_carry_the_compiled_gate_digest`
- [x] `verify` errors clearly when a canonical trace digest is altered (tmp copy, fixture
  intact) — `python/tests/test_cli.py::test_verify_refuses_a_canonical_trace_decided_by_another_gate`
- [x] `replay` on pre-tightened traces: warning indicates old gate → new gate, verdicts still
  compared as before — `python/tests/test_player.py::test_replay_reports_a_gate_that_changed_since_the_recording`
- [x] Traces lacking the field replay as before —
  `python/tests/test_player.py::test_a_trace_without_gate_digest_replays_unchanged`
- [x] Firmware vectors regenerated, `--check` green — `python/tests/test_trace_vectors.py`
  (device self-checks digest: `test_a_firmware_deciding_an_older_gate_is_refused_not_compared`)
- [x] `neuroedge verify` remains green; zero tests skipped

## 8. Tasks upon Approval

- [x] Update three canonical traces; regenerate `targets/esp32s3/main/vectors/` using
  `scripts/gen_firmware_vectors.py`
- [x] `testing/player.py`: single comparison function, warning for `replay`, optional enforcement for `verify`;
  `_device_replay` routes to same function
- [x] `docs/spec/simulation_coverage.md` §4; `docs/architecture/{vi,en}/07-data-contracts.md`;
  `docs/architecture/{vi,en}/10-target-equivalence.md` — single source of truth, referencing RFC-0008
- [x] RFC row in `docs/rfc/README.md`
- [x] Appendix of `docs/spec/core_contracts.md` unchanged — event contract resides in
  `docs/spec/simulation_coverage.md` §3; schema unchanged
