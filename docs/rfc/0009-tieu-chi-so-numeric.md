# RFC-0009: Numeric Criterion `evaluate.type: numeric` in `gate.v1`

| | |
|:---|:---|
| **RFC ID** | 0009 |
| **Title** | `numeric` criterion — threshold comparison, mandatory unit, scale, and reading age, narrowing-only inheritance, new node in `NETR` |
| **Affected Contract** | `gate.v1` (adds enum value and fields) · resolution semantics · `NETR` layout · new verdict reason `value_out_of_range` |
| **Related PRD Requirements** | FR-GATE-03, FR-GATE-06, FR-ACE-01, FR-HAL-01 |
| **Author** | — |
| **Date Opened** | 2026-09-30 |
| **Status** | ✅ Approved (2026-10-01) — lead architect signed on PR #76; amended per review 2026-10-01 (§9, Q-62) · ✅ Implemented (TSK-W1-02, 2026-10-03); binding `analog.in` channels (TSK-I2a-04) and PWM `state()` (RFC-0010) implemented alongside those primitives |
| **Approver** | **Lead Architect — mandatory** (touches `gate.v1`, resolution semantics, `NETR`) |

> **When an RFC is required:** `CONTRIBUTING.md` §3 — modifying `schemas/*.json`, modifying gate resolution
> semantics (`engine/gate_resolver.py`, `engine/constraints.py`), changing `NETR` layout. Task: TSK-W1-02.
> Sources: `TODOS.md` #30; FOFOCA robot draft (`docs/architecture/vi/15-target-architecture.md` §4.3), now consolidated into this RFC. Context:
> `neuroedge-prd.md` §15 Q-52, Q-54 (RFC-0012 relies on this criterion to lock confidence thresholds), Q-55, Q-57.

## 1. Problem

Gates cannot express numeric thresholds. Authors writing gates for air compressors wanting *"pressure < 8 bar"* must compromise today:

```yaml
# current gate — threshold lives elsewhere
evaluate:
  pressure_ok:
    type: bool
    instructions: "Pressure below permitted threshold"
allow_when:
  pressure_ok: true
```

`pressure_ok` is computed by the agent. The existing workaround is `bands` in `[sim.sensor_facts]` (`docs/spec/simulation_coverage.md`), converting readings into `level` facts. But **thresholds reside in the agent, not in the gate**: gates shared via registry cannot lock them, and agent authors changing `bands` loosen gates without `neuroedge gate lint` noticing — identical to why Q-25 rejected `argument_facts` in [RFC-0005](0005-rang-buoc-tham-so-trong-gate.md) §6. For this reason vision lacks `bands`: counts and confidence scores are `numeric` criteria of the gate ([RFC-0012](0012-nguyen-thuy-vision-in.md) §9.2).

## 2. Why the Current Schema Does Not Solve It

- `schemas/gate.v1.json`, `evaluate.*.type`: `"enum": ["bool", "level", "choice"]`, with `additionalProperties: false` — lacking numeric types and places to declare units, scales, or reading ages.
- `RFC-0005` constrains only **call arguments**; readings from sensors/cameras are **criteria facts**, not arguments.
- `confidence_gte` (`engine/constraints.py`, `BOOL_OPERATORS`) applies only to `bool` criteria and is strictly bounded to `[0, 1]`; it addresses fact confidence, not physical measurements.
- On-device decision trees operate solely on finite domain indices (`admitted_mask`, RFC-0003); lacking floating-point comparison nodes.

## 3. Proposed Change

### 3a. Schema

`evaluate.<name>` accepts `type: numeric` along with three **mandatory** fields (§9.4, §9.5):

```yaml
evaluate:
  line_pressure:
    type: numeric
    unit: bar                       # label, no unit conversion
    range: { min: 0, max: 16 }      # valid scale of readings
    max_age_ms: 500                 # older reading ⇒ BLOCK
    instructions: "Line pressure downstream of regulator"
allow_when:
  line_pressure: { lt: 8 }
```

| Field | Rule |
|:---|:---|
| `unit` | Mandatory; label for human readers, `mcp tools`, and traces; engine **does not convert units** |
| `range` | Mandatory; `min`, `max` are finite `f64`, `min < max`; reading valid when `min ≤ x ≤ max` |
| `max_age_ms` | Mandatory; integer > 0; reading age measured from HAL read timestamp (§3c) |
| `confidence` | **None** — confidence is a separate `numeric` criterion (§9.3) |
| `levels` / `options` | Forbidden with `numeric`, enforced via `allOf` `if/then` similar to existing three types |

Operators in `allow_when`: `gt`, `gte`, `lt`, `lte`, combinable to define intervals (`{ gte: 2, lt: 8 }`). **No `eq`** on floating-point numbers, **no `confidence_gte`** on `numeric` criteria (`GateSchemaError`, `NE2002`). Thresholds are finite `f64` within `range`; empty intervals ⇒ `GateSchemaError` (a gate that can never allow is an invalid gate, per RFC-0005).

A `numeric` criterion **cannot** appear in `on_block.confirms` of RFC-0006: `neuroedge gate lint` rejects (`GateSchemaError`, `NE2002`). Humans cannot confirm physical measurement limits instead.

Vision confidence and counts follow the identical path ([RFC-0012](0012-nguyen-thuy-vision-in.md) §9.2–9.3): `confidence` is `numeric` with `range: { min: 0, max: 1 }`, `count` is non-negative integer `numeric` (compared as `f64`, no dedicated integer type). Sharing the three mandatory fields:

```yaml
evaluate:
  person_confidence:
    type: numeric
    unit: ratio
    range: { min: 0, max: 1 }
    max_age_ms: 300
    instructions: "Confidence score of person label"
allow_when:
  person_confidence: { gte: 0.85 }
```

### 3b. Inheritance (Appendix B.5, Principle 2)

Numeric criteria admit an **interval**. Child gates may only narrow: the child's interval must be a **subset** of the parent's interval (open/closed bounds accounted for: parent `gte: 2` permits child `gt: 2` or `gte: 3`, rejecting `gte: 1`).

| Constraint | Child Permitted |
|:---|:---|
| Lower bound (`gt`/`gte`) | Increase, or identical value with stricter boundary |
| Upper bound (`lt`/`lte`) | Decrease, or identical value with stricter boundary |
| `unit` | Unchanged (changing unit changes threshold meaning) |
| `range` | Unchanged; narrowing `range` does not narrow verdicts and cannot be used for narrowing |
| `max_age_ms` | Unchanged |
| Criterion omitted | Inherited intact, like `allow_when` |

`unit`, `range`, `max_age_ms` reside in `evaluate`: child re-declaring them differently from parent redefines inherited criteria, rejected today (`GateInheritanceError`, `NE2003`, principle 1 — `_merge_evaluate` in `engine/gate_resolver.py`); declaring identically or omitting inherits intact. When overriding `allow_when`, if parent has a bound and child drops it (e.g. parent has both lower and upper bounds, child specifies only lower bound expanding interval) ⇒ loosens inherited conditions because child interval is no longer a subset of parent interval ⇒ `GateInheritanceError` (`NE2003`, principle 2 — `_merge_allow_when`). If child omits the criterion in `allow_when`, the parent clause inherits intact without being considered dropped.

### 3c. Evaluation and Fail-Closed

Readings arrive at the engine as `f64` with HAL read timestamps. Evaluation instant is the verdict event offset on the same monotonic session timeline as HAL read timestamps. Age `age_ms` = evaluation instant − HAL read timestamp. Traces record both HAL read timestamp and `age_ms`; `replay` recomputes and compares. For vision, window age is the age of the oldest frame in the window. Checked in order, all branches BLOCK:

| Scenario | `reason` |
|:---|:---|
| Missing reading (sensor lost, source unresponsive) | `criterion_unavailable` |
| `age_ms < 0` (HAL read timestamp after evaluation instant) | `criterion_unavailable` |
| Age (`age_ms`) > `max_age_ms` | `criterion_unavailable` |
| NaN, ±inf, or outside `range` | `value_out_of_range` |
| Finite, inside `range`, not satisfying `allow_when` interval | `condition_not_met` |

No fallback default values, no interpolation from previous readings, no clamping to `range` bounds before comparing (sharing RFC-0003's "confidence not probability ⇒ unavailable" philosophy). Separating `value_out_of_range` from `criterion_unavailable` allows post-audits to distinguish "lost sensor" from "sensor returning garbage"; verdicts remain identical (§9.1).

### 3d. `NETR` and C Walker

RFC-0003's 24-byte criterion record lacks room for four floats (`lo`, `hi`, scale `min`, `max`), boundary flags, and `max_age_ms`. `layout_version` bumps **once** to 2, in **a single PR** led by TSK-W1-02 (RFC-0009). The PR incorporates the `numeric` table plus fields from `TODOS.md` #36 (gate labels and `on_block` text). RFC-0011 adds **no** fields to `NETR`, modifying only token log `ne_token.c`. Host engine (`engine/binary_tree.py`) and C walker update in the same PR; walker v1 rejects v2 trees (`NE_ERR_VERSION`, RFC-0003 §4) — fail-closed (§9.2). Byte layout is pinned directly:

**Header — 80 bytes** (offsets 0–63 retain v1 definitions from RFC-0003, except `layout_version = 2` and `header_size = 80`; `crc32` at offset 60 computed over whole file with those 4 bytes set to 0):

| Offset | Type | Field | Specification |
|---:|:---|:---|:---|
| 0 | `char[4]` | `magic` | `"NETR"` |
| 4 | `u16` | `layout_version` | `2` |
| 6 | `u16` | `header_size` | `80` |
| 8 | `u8[32]` | `gate_digest` | Raw SHA-256 of resolved gate |
| 40 | `u16` | `node_count` | 1..32 — `allow_when` criteria, following `criteria_order` |
| 42 | `u16` | `arg_count` | 0..16 — RFC-0005 argument limits, in declaration order |
| 44 | `u16` | `enum_count` | 0..64 |
| 46 | `u8` | `on_block_action` | 0 deny · 1 escalate · 2 ask · 3 degrade |
| 47 | `u8` | `fail_open` | 0 closed · 1 open |
| 48 | `u32` | `p95_latency_ms` | > 0 |
| 52 | `u32` | `confirm_mask` | bit *i*: criterion *i* confirmed by human instead (RFC-0006) |
| 56 | `u32` | `strings_size` | 1..16384, final byte is NUL |
| 60 | `u32` | `crc32` | CRC-32 of entire file with these 4 bytes set to 0 |
| 64 | `u16` | `numeric_count` | 0..32 — number of records in numeric table |
| 66 | `u16` | `gate_name_off` | Offset of gate name in string table; `0xFFFF` = none |
| 68 | `u16` | `gate_version_off` | Offset of gate version in string table; `0xFFFF` = none |
| 70 | `u16` | `on_block_to_off` | Offset of escalation destination `to` in string table; `0xFFFF` = none |
| 72 | `u16` | `on_block_message_off` | Offset of `message` in string table; `0xFFFF` = none |
| 74 | `u16` | `fallback_action_off` | Offset of fallback action in string table; `0xFFFF` = none |
| 76 | `u32` | reserved | Zero |

**Criteria nodes — 24 bytes × `node_count`**

For nodes with `kind = 3` (numeric):
- `domain_size = 0`
- `admitted_mask = 0`
- `confidence_floor = 0.0`
- `domain_off` = index in numeric table (0..`numeric_count - 1`)
- Remaining bytes are zero.

(Nodes with `kind` 0 bool, 1 level, 2 choice retain RFC-0003 layout).

**Numeric records — 48 bytes × `numeric_count`**

| Offset | Type | Field | Specification |
|---:|:---|:---|:---|
| 0 | `f64` | `lo` | Lower bound; 0.0 if no lower bound |
| 8 | `f64` | `hi` | Upper bound; 0.0 if no upper bound |
| 16 | `f64` | `range_min` | Lower bound of valid scale |
| 24 | `f64` | `range_max` | Upper bound of valid scale (`range_min < range_max`) |
| 32 | `u32` | `max_age_ms` | Maximum permitted reading age (> 0) |
| 36 | `u16` | `unit_off` | Offset of unit string in string table |
| 38 | `u8` | `flags` | Bit 0 (1): lower bound present · Bit 1 (2): lower bound closed (`gte`) · Bit 2 (4): upper bound present · Bit 3 (8): upper bound closed (`lte`) |
| 39 | `u8` | reserved | Zero |
| 40 | `u64` | reserved | Zero |

**Table ordering and file size:**
1. Header (80 bytes)
2. Criteria nodes (24 bytes × `node_count`)
3. Numeric records (48 bytes × `numeric_count`)
4. Argument limits (32 bytes × `arg_count`)
5. Enum (16 bytes × `enum_count`)
6. String table

Total size = 80 + 24·n + 48·m + 32·a + 16·e + strings, **strictly equal** to file length (as in v1). `numeric_count` strictly equals number of `kind = 3` nodes; each node has a dedicated record, no sharing. `confirm_mask` is non-zero only for `ask` (as in v1) and never contains bits for `kind = 3` nodes. `ne_tree_load` rejects files violating any rule here. Numeric table occupies at most 48 bytes × 32 = 1,536 bytes (1.5 KB) flash.

**C Walker ABI:**
Numeric facts arrive at the walker as structs containing `u8 available` (0 = no reading), `f64 value`, and `i64 age_ms` (replacing finite domain indices). `available = 0` ⇒ `criterion_unavailable` before all other checks, preventing walker from confusing missing sensors with NaN (`value_out_of_range`). Walker checks in strict §3c order and compares using only `>`/`>=`/`<`/`<=` on `f64`, without hidden tolerances (§9.6). `ne_reason` (`ne_walker.h`) and `firmware.REASONS` add `value_out_of_range`. Walker v1 rejects v2 trees (`NE_ERR_VERSION`). C walker stack limit remains ≤ 512 bytes (no recursion, no dynamic allocation).

### 3e. Compiler, Tooling, and Corpus

`neuroedge build` emits nodes; `gate explain` prints thresholds with units, `range`, and `max_age_ms`; `input_schema()`/`mcp tools` unchanged (facts, not arguments). Device screens display labels for new reasons (`ne_ui_strings.c`, `docs/spec/ui.md`). Corpus in `fixtures/gates/` follows closure rules (`CONTRIBUTING.md` §3).

### 3f. Binding Numeric Facts to HAL Channels

When an agent binds a `numeric` criterion to a HAL channel (`analog.in`, readback `feedback`; `sensor.read` currently lacks `unit` and scale declarations so **cannot** bind to `numeric` criteria — binding ⇒ `BoardCapabilityError` (`NE3001`)), `neuroedge build` statically verifies:
1. Hardware channel `unit` and criterion `unit` must match identically.
2. Declared hardware channel scale `[min, max]` must fit entirely within criterion `range` (`range.min ≤ channel.min` and `channel.max ≤ range.max`).

Mismatch on either condition ⇒ `BoardCapabilityError` (`NE3001`).

For criteria bound to digital pin states `digital.out(...).state()`, gates accept only values with `source = measured` (readings measured physically from feedback circuits). Values with `source = commanded` (software logical command state) sent to gates ⇒ treated as lacking valid measured readings ⇒ BLOCK `criterion_unavailable`.

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | Yes — `numeric` is a new enum value, existing three types unchanged |
| Do currently invalid files become valid? | Yes, exactly one category: gates with `type: numeric` having `unit`, `range`, `max_age_ms` (schema relaxation, permissible in `v1`, like RFC-0005) |
| Is a schema version bump required (`v1` → `v2`)? | No for `gate.v1`. **Yes** for `NETR` layout: `layout_version` 2, one-off (§3d) |
| Impact on hashes / digital signatures of published gates? | None — gates not using `numeric` hash identically to before |
| Impact on the three canonical trace files? | None. `trace.v1` unchanged (`events[].data` already open); HAL read timestamp and `age_ms` of `numeric` readings are new event data, specified in `docs/spec/simulation_coverage.md` §4 |
| Which gates in `digests.lock` change digest? | No gates. New gates using `numeric` enter `digests.lock` via regular PR |
| Does the `NETR` layout or C walker need to change? | **Yes** — `kind = 3`, `numeric` table, `layout_version` 2, fact ABI `u8 available` + `f64 value` + `i64 age_ms`, `ne_reason` adds `value_out_of_range`; `engine/binary_tree.py` ↔ `targets/esp32s3/components/ne_gate/` |
| Which answers in the tool-call corpus (`expected_results.yaml`) change? | No |

Firmware flashed with v1 trees must be re-built alongside v2 trees; per RFC-0003 §4 walker v1 rejects v2, making version mismatches clear load errors rather than incorrect verdicts.

**Error codes** (`neuroedge-prd.md` Appendix B): this RFC utilizes `GateSchemaError` (`NE2002`) (malformed structure, or containing `numeric` criteria in `on_block.confirms`), `GateInheritanceError` (`NE2003`) (violating inheritance principle 1 in `_merge_evaluate` or principle 2 in `_merge_allow_when`), and `BoardCapabilityError` (`NE3001`) (`neuroedge build` detecting HAL channel `unit` mismatch or `[min, max]` exceeding `range`). `value_out_of_range` is a **verdict reason**, not an exception: added to `Reason` (`engine/verdict.py`), `firmware.REASONS`/`ne_reason`, and the reasons table in `docs/spec/ui.md` (six expanding to seven); Appendix B adds no new rows.

## 5. Safety Impact

- **Where is it more lax?** Nowhere: `numeric` adds the ability to *express* thresholds, and inheritance semantics only narrow. The sole "relaxation" is schema-level, never verdict-level.
- **Principle 2** is extended to numeric intervals; open/closed boundary errors (child `gte` when parent `gt`) represent the most error-prone area — mutation tests mandatory (§7).
- **Fail-closed** preserved and strengthened: missing sensors, readings violating causality (`age_ms < 0`), readings exceeding `max_age_ms`, NaN, ±inf, outside scale all BLOCK unconditionally. Mandatory `range` and `max_age_ms`: without scales, absurd values cannot be caught; hung sensors repeating the last value look deceptively "safe" (§9.4, §9.5).
- **No human confirmation of measurements:** `on_block.confirms` rejects `numeric` criteria (`GateSchemaError`, `NE2002`). Humans on devices cannot confirm objective physical measurements instead.
- **Hardware channel matching at build time:** `neuroedge build` statically verifies `unit` and scale `[min, max]` against `range` (`BoardCapabilityError`, `NE3001`), eliminating misconfigured sensors. Pin state `state()` accepts only `source = measured`, preventing software from using `commanded` to simulate passing conditions.
- **Single path for confidence:** `numeric` criteria lack `confidence`; confidence is a dedicated `numeric` criterion, lockable via `gate lint` (§9.3, RFC-0012).
- **Debt paid down:** numeric thresholds currently in agents (`bands`) move into gates, enforced by `gate lint`. `[sim.sensor_facts]` remains unchanged in this RFC, but ceases to be the sole mechanism; vision lacks `bands` (RFC-0012 §9.2).
- **Floating-point numbers:** thresholds, `range`, and readings are finite `f64`; deterministic comparisons on host and MCU via four operations, zero hidden tolerances (§9.6). Inputs from ADC/sensors convert to declared units prior to reaching gates (`analog.in`, [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md)).
- **Host and chip never interpret trees with divergent meanings:** `layout_version` 2 updates host and walker in the same PR led by TSK-W1-02 (§9.2). Byte layout pinned conclusively; C walker strictly bounds stack ≤ 512 bytes and numeric table flash budget to 1.5 KB maximum.

## 6. Alternatives Considered and Rejected

| Alternative | Reason for Rejection |
|:---|:---|
| Keep `bands` in agent | Threshold lives outside gate, agent authors can loosen without `lint` noticing (§1) |
| CEL expressions over readings | Cannot prove "child stricter than parent" between arbitrary expressions; MCU lacks CEL (Q-9) |
| `eq` on floating-point numbers | Exact equality on `f64` has no physical measurement meaning; use narrow intervals |
| Comparisons with tolerance (epsilon) | Hidden tolerance causes discrepancies between host and MCU; use only four operators `>`/`>=`/`<`/`<=` (§9.6) |
| `level` only with fixed bands | Carries no units, thresholds become labels; still effectively `bands` |
| Optional `range` | Without scale, absurd values cannot be detected (§9.4) |
| No reading age limit / optional `max_age_ms` | Hung sensors repeat last value looking permanently "safe" (§9.5) |
| Out-of-range/NaN reports `criterion_unavailable` | Post-audit cannot distinguish missing sensor from sensor returning garbage (§9.1) |
| `confidence` field on `numeric` criterion | Two paths for confidence means one will be neglected from locking (§9.3) |
| Bump `layout_version` separately per RFC | Repeated firmware breaking changes; periods where host and chip interpret trees with divergent meanings (§9.2) |
| Push to `gate.v2` | No valid files break; `v2` provides zero value (same reasoning as RFC-0002 §4) |
| Allow `on_block.confirms` with `numeric` criteria | Humans cannot confirm physical measurements instead; violates fail-closed safety |
| Criteria bound to `digital.out.state()` accept `source = commanded` | Allows software to fake passing states without real feedback sensors |

## 7. Verification Evidence

- [x] Valid examples in `fixtures/gates/valid/`: `numeric` gates with full `unit`/`range`/`max_age_ms`, child gates narrowing lower/upper/open boundaries, confidence gates with `range: { min: 0, max: 1 }`
- [x] Counterexamples in `fixtures/gates/invalid/` + `expected_errors.yaml`: missing `unit`, missing `range`, missing `max_age_ms`, `max_age_ms` ≤ 0, `range` with `min ≥ max` or non-finite, non-finite thresholds, thresholds outside `range`, empty intervals, `eq`, `confidence_gte` on `numeric`, `confidence` field, `levels`/`options` accompanying `numeric`, `numeric` criteria in `on_block.confirms` (`GateSchemaError`, `NE2002`); inheritance: loosening bounds, dropping parent bounds on override, changing `unit`, changing `range`, changing `max_age_ms` (`GateInheritanceError`, `NE2003`)
- [ ] *(alongside TSK-I2a-04 and RFC-0010; `sensor.read` ⇒ `NE3001` and `commanded` ⇒ BLOCK present; **`analog.in` portion passed** in TSK-I2a-04: `tests/test_analog_in.py`, bound via `[sim.analog_facts]`; pending `feedback` readback of RFC-0010)* HAL channel binding: `neuroedge build` validates matching `unit` and HAL channel `[min, max]` within `range` of `numeric` criterion; counterexamples with mismatched `unit` or `[min, max]` exceeding `range` rejected with `BoardCapabilityError` (`NE3001`); test criteria bound to `digital.out(...).state()` receiving `source = commanded` ⇒ BLOCK `criterion_unavailable`, passing only when `source = measured`
- [x] Engine: missing reading ⇒ BLOCK `criterion_unavailable`; `age_ms < 0` (HAL read timestamp after evaluation instant) ⇒ BLOCK `criterion_unavailable`; age > `max_age_ms` ⇒ BLOCK `criterion_unavailable` (edge case age exactly equal to `max_age_ms` passes); NaN, ±inf, outside `range` ⇒ BLOCK `value_out_of_range`; check ordering per §3c
- [x] Replay: traces carry both HAL read timestamp and `age_ms`; `replay` recomputes age and validates; vision evaluates window age by oldest frame
- [x] C walker matches host engine across all gates (expanded `python/tests/test_c_walker.py`), including C tests for all boundaries: closed/open (`gt`, `gte`, `lt`, `lte`), NaN, ±inf, exact `range` bounds (`min`, `max`), `age_ms = max_age_ms`, `age_ms = max_age_ms + 1`, `age_ms < 0`; fact ABI validation `f64 value` + `i64 age_ms`; mutation tests (inverting `<`/`<=`, skipping NaN check, skipping `range` check, skipping age check); C walker stack limit ≤ 512 bytes; numeric table flash budget check (48 bytes × max 32 items = 1,536 bytes)
- [x] Walker v1 rejects v2 trees (`NE_ERR_VERSION`); `test_ui_assets.py` preserves alignment between `ne_reason` and `firmware.REASONS` after adding `value_out_of_range`
- [x] `neuroedge gate lint` and `neuroedge verify` remain green; `scripts/check_digests.py` preserves locked gate digests

## 8. Tasks upon Approval

- [x] Update `schemas/gate.v1.json` (`type` enum, mandatory `unit`, `range`, `max_age_ms`, `if/then` branches)
- [x] Update Appendix B.2/B.5 in `docs/spec/core_contracts.md`; FR-GATE-03 in `neuroedge-prd.md`; record approval in Q-57 (`neuroedge-prd.md` §15)
- [x] Update `neuroedge-roadmap.md` (TSK-W1-02) and close `TODOS.md` #30
- [x] `engine/constraints.py`, `engine/gate_resolver.py`, `engine/verdict.py` (`value_out_of_range`), `engine/binary_tree.py`, `engine/firmware.py` (`REASONS`), C walker (`ne_walker.h`), `gate explain`
- [x] Update `neuroedge gate lint` to reject `numeric` criteria in `on_block.confirms` (`GateSchemaError`, `NE2002`)
- [ ] *(alongside TSK-I2a-04 and RFC-0010; **`analog.in` portion passed**: `check_analog_facts` in `engine/compiler.py` checks `unit` and `range`; pending `source = measured` for `digital.out` readback)* Update `neuroedge build` to validate HAL channel bindings to `numeric` criteria (`unit`, `range`, `source = measured`) (`BoardCapabilityError`, `NE3001`)
- [x] Record both HAL read timestamp and `age_ms` in traces; update `replay` to recompute and compare; handle `age_ms < 0` ⇒ BLOCK `criterion_unavailable`; update `docs/spec/simulation_coverage.md` §4 and reasons table in `docs/spec/ui.md` (labels in `ne_ui_strings.c`)
- [x] Single PR bumping `layout_version` to 2 led by TSK-W1-02 including `numeric` table and `TODOS.md` #36 fields (RFC-0011 adds no fields to `NETR`); C walker ABI accepts `f64 value` + `i64 age_ms`, verifies stack ≤ 512 bytes and numeric table flash budget 48 bytes × 32 (§3d)
- [x] Add fixtures and tests; update `docs/rfc/README.md` and `CHANGELOG.md`

## 9. Decisions on Open Questions (Q-57, 2026-09-30; Q-62, 2026-10-01)

Product owner delegated resolving open questions under the **maximum safety** principle: between two alternatives, choose the fail-closed and harder-to-misuse option, even when more costly. The decisions below **have been incorporated into §3–§8**; this section is retained as the decision log (Q-57). RFC approval still requires lead architect signature (`CONTRIBUTING.md` §3).

1. **Error reason.** Add dedicated reason `value_out_of_range` (readings outside `range`, NaN, ±inf); `criterion_unavailable` reserved for missing readings. Both BLOCK. *Why:* post-audits distinguish "lost sensor" from "sensor returning garbage", verdicts unchanged.
2. **`NETR` layout.** Bump `layout_version` to 2 **once**, in a single PR led by TSK-W1-02 incorporating the `numeric` table of this RFC and `TODOS.md` #36 fields (RFC-0011 adds no fields to `NETR`); pin byte layout directly within RFC-0009; host engine and C walker change in same PR; walker v1 rejects v2 trees (`NE_ERR_VERSION`, fail-closed). *Why:* prevents any period where host and chip interpret trees with divergent meanings; binary format frozen conclusively.
3. **Confidence.** `numeric` criteria lack `confidence` fields; confidence, when needed, is **a separate `numeric` criterion** (RFC-0012 path). *Why:* single path, lockable via `gate lint`.
4. **Mandatory `range`.** *Why:* without scale, absurd values cannot be detected, fail-closed loses edge.
5. **Reading age.** `max_age_ms` is **mandatory** for all `numeric` criteria; older readings ⇒ `criterion_unavailable` ⇒ BLOCK. HAL read timestamp and `age_ms` recorded in traces for `replay` recomputation and comparison; `age_ms < 0` (read timestamp after evaluation instant) ⇒ BLOCK `criterion_unavailable`. *Why:* hung sensors repeat last value looking permanently "safe"; gates must reject stale readings or causality violations.
6. **Floating-point comparisons.** Thresholds, `range`, and readings are finite `f64`; host and C walker use strictly four operators `>`, `>=`, `<`, `<=`, without hidden tolerances; conformance vectors include cases exactly equal to thresholds at all boundaries.
7. **HAL channel bindings and numeric confirmation prohibition** (review 2026-10-01, Q-62). Agents binding `numeric` criteria to HAL channels (`analog.in`, readback `feedback`; `sensor.read` currently lacks `unit` and scale declarations so **cannot** bind to `numeric` criteria — binding ⇒ `BoardCapabilityError` (`NE3001`)) must match `unit` and channel `[min, max]` must fit within criterion `range`, mismatch ⇒ `BoardCapabilityError` (`NE3001`); `digital.out(...).state()` accepts only `source = measured` (receiving `commanded` ⇒ `criterion_unavailable`); `numeric` criteria strictly forbidden in `on_block.confirms` (`GateSchemaError`, `NE2002`). *Why:* humans cannot confirm physical measurement limits instead; prevents software logical commanded states or scaled-mismatched sensors from bypassing gates.
8. **Fact age definition and replay evaluation** (review 2026-10-01, Q-62). Evaluation instant is verdict event offset on same monotonic session timeline as HAL read timestamp; age = evaluation instant − HAL read timestamp; traces record both read timestamp and `age_ms`; `replay` recomputes and compares; `age_ms < 0` ⇒ BLOCK `criterion_unavailable`. For vision, window age is the age of the oldest frame in the window. *Why:* ensures determinism during replay and eliminates clock skew or future read timestamp risks relative to verdicts.
9. **Freezing `NETR` v2 layout and walker ABI** (review 2026-10-01, Q-62). Directly pin 80-byte header and 48-byte `numeric` table layout in RFC-0009; C walker numeric fact ABI accepts `f64 value` and `i64 age_ms`; C walker stack limit ≤ 512 bytes; flash budget for `numeric` table is 48 bytes × max 32 items (1,536 bytes max). *Why:* resolves contradiction of deferring byte pinning to second PR; freezes ABI and strictly controls MCU firmware flash and stack resources.
