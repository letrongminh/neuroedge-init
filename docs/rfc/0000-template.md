# RFC-NNNN: <Short Title Describing the Change>

| | |
|:---|:---|
| **RFC ID** | NNNN |
| **Title** | |
| **Affected Contract** | `gate.v1` / `trace.v1` / `board.v1` / resolution semantics / `NETR` layout / *(none)* |
| **Related PRD Requirements** | FR-… , NFR-… |
| **Author** | |
| **Date Opened** | YYYY-MM-DD |
| **Status** | 🟡 Under discussion / ✅ Approved / ❌ Rejected / ⏳ Deferred |
| **Approver** | *(mandatory for breaking changes)* |

> **When an RFC is required:** the sole list is in `CONTRIBUTING.md` §3 (schemas, gate
> resolution semantics, canonical traces, gates locked in `digests.lock`, `NETR` layout).

## 1. Problem

*State the observed problem, not the solution. If the problem is an unvalidatable file
or an inexpressible proposition, paste that file here along with the actual error message.*

## 2. Why the Current Schema Does Not Solve It

*Cite specific fields or rules. If this is an internal schema contradiction, pinpoint
the two conflicting clauses.*

## 3. Proposed Change

*Diff or before/after. For JSON Schema, paste the before and after snippets.*

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | |
| Do currently invalid files become valid? | |
| Is a schema version bump required (`v1` → `v2`)? | |
| Impact on hashes / digital signatures of published gates? | |
| Impact on the three canonical trace files? | |
| Which gates in `digests.lock` change digest? | |
| Does the `NETR` layout or C walker need to change? | |
| Which answers in the tool-call corpus (`expected_results.yaml`) change? | |

**Rule:** if a currently valid file becomes invalid, it is a breaking change and
**requires** bumping the schema version. Relaxations (a currently invalid file
becomes valid) can be made within the same version.

## 5. Safety Impact

*Mandatory for `gate.v1`.* Does this change allow a gate to become **more lax**
in any way? Does it affect the five principles of inheritance (Appendix B.5)
or the fail-closed default?

If the answer is "yes" for any item, the RFC requires approval from the lead
architect.

## 6. Alternatives Considered and Rejected

| Alternative | Reason for Rejection |
|:---|:---|
| | |

## 7. Verification Evidence

*Tests proving the change works, and counterexample fixtures proving
it still rejects exactly what should be rejected.*

- [ ] Valid example added to `fixtures/`
- [ ] Invalid example with expected result added per that corpus's closure rule (`CONTRIBUTING.md` §3)
- [ ] Automated test added, specifying name
- [ ] `neuroedge gate lint` and `neuroedge verify` remain green

## 8. Tasks upon Approval

- [ ] Update `schemas/<schema>.json` (or corresponding contract)
- [ ] Update corresponding Appendix in `docs/spec/core_contracts.md`
- [ ] Update `neuroedge-prd.md` if any FR is affected; assign `Q-N` in §15 for new decisions
- [ ] Update `neuroedge-roadmap.md` if any task or exit criteria is affected
- [ ] Add/adjust fixtures and tests; locked gates: `scripts/check_digests.py --accept <file> --rfc NNNN`
- [ ] Update the RFC's row in `docs/rfc/README.md` and an entry in `CHANGELOG.md` `[Chưa phát hành]`
