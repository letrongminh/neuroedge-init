# RFC — Proposals to Change Frozen Contracts

Schemas in `schemas/`, gate resolution semantics, the three canonical traces, gates locked
in `digests.lock`, and the `NETR` binary layout are conformance measures and subjects of
gate digital signatures, so they are not changed via a regular pull request. The exact list
of what requires an RFC: [`CONTRIBUTING.md` §3](../../CONTRIBUTING.md#3-changes-requiring-an-rfc).

## Process

1. Copy `0000-template.md` to `NNNN-<short-name>.md` with the next number.
2. Open a pull request **containing only the RFC file**, without modifying contracts yet.
3. Discuss on that pull request. Section 4 (compatibility) and section 5 (safety) are two
   sections that must not be left empty.
4. When approved, make changes in a second pull request, referencing the RFC number in
   the commit message, and update the RFC's row in the catalog below.

Approvers: `CONTRIBUTING.md` §3.

## Catalog

| RFC | Title | Schema | Status |
|:---|:---|:---|:---:|
| [0001](0001-gate-schema-conditional-requirements.md) | Conditional field requirements for inherited gates | `gate.v1` | ✅ Approved · ✅ Implemented |
| [0002](0002-mo-rong-target-va-nguyen-thuy-thi-giac.md) | Expand target list (Q-67); code removed from the roadmap by Q-77 | `board.v1` · `trace.v1` (`target` enum only) | ✅ Approved · ⏸ implementation removed from roadmap (Q-77, TSK-V1a-02) |
| [0003](0003-bo-cuc-nhi-phan-cay.md) | On-device tree `NETR` v1 binary layout (Q-23) — narrowed; pinning `extends` still deferred (`TODOS.md` #15) | *(new format, outside `schemas/`)* | ✅ Approved · ✅ Implemented |
| [0004](0004-ke-thua-budget-on-block.md) | Child gates cannot relax `budget` and `on_block` | *(none — resolution semantics)* | ✅ Approved · ✅ Implemented |
| [0005](0005-rang-buoc-tham-so-trong-gate.md) | Gates declare action argument constraints (Q-25) | `gate.v1` · resolution semantics · Q-23 layout | ✅ Approved · ✅ Implemented |
| [0006](0006-xac-nhan-ask-confirms.md) | `on_block.confirms` — criterion of person on device confirmed instead (Q-26) | `gate.v1` · resolution semantics · evaluation | ✅ Approved · ✅ Implemented |
| [0007](0007-digital-in-i2c-analog-in-phong-bi.md) | `digital.in`, read-only I2C bus, `analog.in`, and safety envelope in `board.v1` — TSK-N0-03 (Q-53) | `board.v1` (`gate.v1` unchanged) | ✅ Approved · implemented in a second PR |
| [0008](0008-vet-ghi-chuan-muc-mang-gate-digest.md) | Three canonical traces carry `gate_digest` — replay checks it | `trace.v1` *(only `data` of three traces; schema file unchanged)* | ✅ Approved · ✅ Implemented |
| [0009](0009-tieu-chi-so-numeric.md) | Numeric criterion `evaluate.type: numeric` — TSK-W1-02 (Q-53, Q-54) | `gate.v1` · resolution semantics · `NETR` | ✅ Approved · ✅ Implemented |
| [0010](0010-pwm-trong-digital-out.md) | PWM in `digital.out` — TSK-W1-01 (Q-53) | `board.v1` | ✅ Approved · implemented in a second PR |
| [0011](0011-nguyen-thuy-motion.md) | `motion.*` primitives, time-limited leased tokens, safe state per mechanism — TSK-W1-03 (Q-53) | `board.v1` · token log · `NETR` | ✅ Approved · implemented in a second PR |
| [0012](0012-nguyen-thuy-vision-in.md) | `vision.in` primitive; vision results enter gate as facts — TSK-V1b-07 (Q-53, Q-54) | `board.v1` *(`trace.v1` unchanged)* | ✅ Approved · implemented in a second PR |
| [0013](0013-nguyen-thuy-tuy-chon-va-nhieu-bo-tham-chieu.md) | Optional extended primitives per board; multiple reference boards per target; `sim-rpi5` — TSK-I2a-07 (Q-53) | *(none — test invariants, amends RFC-0002 §5b, §5c)* | ✅ Approved · implemented in a second PR |
| [0014](0014-du-kien-tu-tien-trinh-ngoai.md) | Numeric facts from external processes (Frigate, OpenCV, sensor box, Home Assistant): source declared in gate, source identity recorded in trace, `age_ms` per Q-62, source down ⇒ BLOCK — TSK-I6-07 (Q-63; post-v1.0 code, `TODOS.md` #56) | `gate.v1` *(one optional key)* · resolution semantics · `agent.toml` (`trace.v1`, `board.v1` unchanged) | ✅ Approved · code after v1.0 (`TODOS.md` #56) |
| [0015](0015-hop-dong-cho-nguoi-tich-hop.md) | Freeze contracts for integrators: Gated Tool Profile (`tool-call.v1`, `tool-result.v1`), `board.v1` version identifier, `NE*` error code catalog (`error.v1`, `error-codes.v1`) — TSK-I6-05 (Q-58, Q-63) | `schemas/` (four new schemas) · `board.v1` (`schema` key) | ✅ Approved · ✅ Implemented |
| [0016](0016-loi-tach-duoc-va-extension-sdk.md) | Standalone safety core and Extension SDK: extension points, trust model, compliance test suite — TSK-I2c-02 (Q-67) | *(not in `schemas/`)* — new APIs, `agent.toml` `[plugins]`, CLI | ✅ Approved |
| [0017](0017-nguon-goi-theo-khong-gian-ten.md) | Namespaced call sources (`bridge:<id>`) and client identity — TSK-I2c-03 (Q-67) | `tool-call.v1` (`source`) · `docs/spec/tool_calling.md` | ✅ Approved · half (a) implemented (`bridge:<id>`); half (b) `[mcp.clients]` open (TSK-I2c-10) |
| [0018](0018-co-cau-chap-hanh-tu-xa.md) | Remote actuators and auto-kill levels — TSK-I2c-04 (Q-67) | *(not in `schemas/`)* — `agent.toml` `[actuators]` block, HAL `_admit` channel, envelope, trace events (`trace.v1` unchanged) | ✅ Approved |

## In flight and planned

Not in this directory yet; each is named in roadmap §0.2 (I2d row), roadmap §0.3 or `docs/spec/missions.md`.

| RFC | Subject | Where it is stated |
|:---|:---|:---|
| RFC-0019 (draft, PR #133) | Box-signed approval records and the box's own approval bot (`chat:<id>` source), TSK-I2d-11 | roadmap §0.3 and §8 (waiting for the lead engineer); `docs/spec/missions.md` MS-CH-02, MS-CH-03 |
| Unnumbered, planned | `board.v1` must-understand list `requires = [...]` (TSK-I2d-01), then conditional safety `safe_state` (TSK-I2d-02, MS-SF-01 → 06) | roadmap §4.3.4; `docs/spec/missions.md` §3 |
| Unnumbered, planned | `mission.v1` mission contract and `trace.v1` segments (TSK-I2d-04, MS-CT-01, MS-TS-01) | roadmap §4.3.4; `docs/spec/missions.md` §4.1 |
| Unnumbered, planned | `NETR` reflex terms (Q-87(2), MS-CP-04): reflex tier on the chip waits for it | PRD §15 Q-87; `docs/spec/missions.md` MS-CP-04, MS-D-02 |

The unnumbered draft RFC for the node coordination protocol of tiered robots was deleted on 2026-10-16 (robots left the roadmap, Q-77); it can be recovered from git history.
