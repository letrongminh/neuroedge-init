# RFC-0012: `vision.in` Primitive and Visual Perception Evidence

| | |
|:---|:---|
| **RFC ID** | 0012 |
| **Title** | `vision.in` (board capability), typed facts declared by makers from model labels, evidence in traces, equivalence across targets |
| **Affected Contract** | `board.v1` *(the `vision_in` key, including inference tolerance §3f)* · `agent.toml` `[vision]` block *(no schema in `schemas/`; checked in `neuroedge build`)* · visual `perception` event convention and semantic trace lint *(does not alter `trace.v1`: `events[].data` is free `object`, `metadata` open — §4)* · does **not** touch `gate.v1` · `neuroedge-prd.md` Appendix B: widens causes for three existing rows, **no new codes** (§4) |
| **Related PRD Requirements** | FR-HAL-01, FR-HAL-04, FR-HAL-05, FR-CI-02, FR-MDL-04, FR-MDL-07, NFR-PRIV-01, NFR-PRIV-03 |
| **Author** | — |
| **Date Opened** | 2026-09-30 |
| **Status** | ✅ Approved (2026-10-01) — lead architect signed on PR #79; amended per review 2026-10-01 (§9, Q-62); implemented in second PR |
| **Approver** | **Lead Architect — mandatory** (touches `board.v1`, camera privacy, perception/authority boundary) |

> **When an RFC is required:** `CONTRIBUTING.md` §3 — modifying `schemas/board.v1.json`. Tasks: TSK-V1b-07 (this RFC) and
> TSK-V1b-01, TSK-V1b-02, TSK-V1b-03, TSK-V1b-04, TSK-V1b-05, TSK-V1b-06, TSK-V1b-08, TSK-I3a-01. This is the RFC that RFC-0002 §9.1 and §9.2 deferred; known inputs reside there. Foundation
> decisions: `neuroedge-prd.md` §15 Q-52, Q-53 (camera present on all three targets; ESP32-S3 board has
> camera), **Q-54** (vision → facts declared by maker, gates lock thresholds using `numeric` criteria, **no
> dedicated gate semantics for vision**), Q-55, Q-57, **Q-61** (§9).

## 1. Problem

`vision.in` exists only on paper. Four gaps:

1. **Boards cannot declare cameras.** `sensor.read` returns discrete scalars (RFC-0002 §9.1), not frame streams. Initial experimental shape (integer `width`, `height`, `fps`, free string) could not match against agents.
2. **No path from model labels to verdicts.** `docs/architecture/vi/15-target-architecture.md` §4.4 intentionally left open the problem of dedicated gate semantics for vision; the existing constraint there (Q-54) works around it: mapping vision to typed facts the gate already knows how to evaluate, thresholds locked in the gate. Syntax and rules for that path do not yet exist.
3. **No trace rules.** Cameras in private spaces pose greater risk than microphones; precise rules are needed for what gets recorded (NFR-PRIV-01, NFR-PRIV-03), sufficient for `replay` to reproduce verdicts (FR-CI-02).
4. **No method to prove equivalence.** Vision models run across three targets with different hardware; "gates decide identically" and "models see identically" are two different propositions, neither of which has been tested.

## 2. Why the Current Schema Does Not Solve It

- `schemas/board.v1.json`: lacks a `vision_in` key; if someone adds it, validation passes because `capabilities` is open, but there is no type to validate against — and any shape alteration post-release is a tightening (RFC-0002 §6).
- `gate.v1` evaluates only `bool` / `level` / `choice`; RFC-0009 adds `numeric`. Nothing else is needed for vision if counts and confidence scores are represented as numeric facts. `confidence_gte` (`engine/constraints.py`, `BOOL_OPERATORS`) is a second path for confidence on `bool` criteria; gates do not know which criteria originate from vision, so `gate lint` cannot block that path — only at build time are both the gate and manifest available (§3c).
- `agent.toml` (`fixtures/agents/*/agent.toml`) provides no place to declare labels → facts. The existing workaround, `bands` under `[sim.sensor_facts]`, places thresholds in the agent — precisely what Q-54 and RFC-0009 §1 rejected.
- Agent `[requires]` has no matching rules for numeric parameters.

## 3. Proposed Change

### 3a. Board Capabilities

```toml
[capabilities.vision_in]
modes = [
  { width = 640,  height = 480, fps = 30.0,  pixel_format = "yuyv" },
  { width = 1280, height = 720, fps = 7.5,   pixel_format = "mjpeg" },
]
tolerance = { score_abs = 0.03, box_iou_min = 0.85 }
```

- `fps` is `number` (7.5 · 29.97), not an integer; sensors support multiple modes, so `modes[]` is a mandatory array (at least one element).
- `pixel_format` is a **closed enum**: `yuyv`, `mjpeg`, `rgb565`, `rgb888`, `gray8`; adding values requires an RFC (§9.1).
- `vision_in` additionally declares permitted **inference tolerance** relative to host golden, used in §3f (§9.6, §9.9). The `tolerance = { score_abs, box_iou_min }` field applies a single common value across all models on the board. The `board.v1` schema imposes a hard ceiling: `score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`. Boards declaring tolerance exceeding the hard ceiling are rejected with `BoardCapabilityError` (`NE3001`) at board load time.
- Selected camera board for `esp32s3`: M5Stack CoreS3 (Q-61), profile `esp32s3-cores3`. The board includes ESP32-S3, 16 MB flash, 8 MB PSRAM, 0.3 MP GC0308 camera (VGA), 2 mics via ES7210, 1 W speaker via AW88298 amplifier, 2" 320×240 touch display, BMI270 IMU, LTR-553 sensor, Grove and M5-Bus ports. GC0308 sensor maxes out at VGA, so example `modes` for this board has 640×480. The default board for `esp32s3` remains `esp32s3-box-3`. Recording SRAM/PSRAM measurements per Q-3 is a mandatory condition (TSK-I3a-01).
- Accelerators (`accelerator`) are not declared in this RFC: models and NPUs belong to agent configuration (TSK-V1b-03, TSK-V1b-05), not the board contract.

### 3b. Matching Against `[requires]`

Agents declare minimum requirements; a board satisfies them if **at least one mode exists** meeting all thresholds:

```toml
[requires]
"vision.in" = { min_width = 640, min_height = 480, min_fps = 10.0, pixel_formats = ["yuyv", "mjpeg"] }
```

For example, `min_width = 640, min_height = 480` passes on `esp32s3-cores3` with VGA GC0308 camera.

`neuroedge build` (`engine/compiler.py`) rejects boards without a satisfying mode with `BoardCapabilityError` (`NE3001`), a three-part error stating the closest mode (FR-HAL-05). Matching is deterministic because `pixel_format` is a closed enum.

### 3c. From Model Labels to Typed Facts (Q-54, §9.2–9.3)

The **maker** declares in `agent.toml` which labels become which facts; the **gate** locks thresholds. Example — opening gate when someone is at the gate, closing gate when nobody remains:

```toml
# agent.toml — declared by maker
[vision]
model = "models/person-det.tflite"

[vision.zones]
gate_area = [0.25, 0.40, 0.75, 1.00]   # [x0, y0, x1, y1] normalised in [0, 1], x0 < x1, y0 < y1

[vision.facts.person_at_gate]
label      = "person"
zone       = "gate_area"
kind       = "present"      # → bool criterion
min_frames = 3              # default 3, minimum 2

[vision.facts.person_confidence]
label = "person"
zone  = "gate_area"
kind  = "confidence"        # → numeric criterion, [0, 1]

[vision.facts.people_at_gate]
label = "person"
zone  = "gate_area"
kind  = "count"             # → numeric criterion, integer ≥ 0
```

```yaml
# gates/open_gate — authority
evaluate:
  person_at_gate:    { type: bool, instructions: "Person in gate area" }
  person_confidence: { type: numeric, unit: ratio, range: { min: 0, max: 1 }, max_age_ms: 300,
                       instructions: "Confidence score of person label in gate area" }
allow_when:
  person_at_gate: true
  person_confidence: { gte: 0.85 }      # locked in gate, inheritance only narrows (RFC-0009)

# gates/close_gate
evaluate:
  person_at_gate:    { type: bool, instructions: "Person in gate area" }
  people_at_gate:    { type: numeric, unit: count, range: { min: 0, max: 50 }, max_age_ms: 300,
                       instructions: "Number of people in gate area" }
  person_confidence: { type: numeric, unit: ratio, range: { min: 0, max: 1 }, max_age_ms: 300,
                       instructions: "Confidence score of person label in gate area" }
allow_when:
  people_at_gate: { lte: 0 }
  person_confidence: { lte: 0.10 }      # mandatory confidence pair to carry max_age_ms, prevent freeze
```

**Fact Rules:**

| Field | Rule |
|:---|:---|
| `[vision] model` | A single model file; identity = name + sha256 of file (§3d) |
| `kind` | `present` → `bool` · `count` → `numeric` (integer ≥ 0) · `confidence` → `numeric` in `[0, 1]`. No `level`/`choice`, no `bands` |
| Fact name | Matches gate criterion name; criterion type of same name must match `kind` |
| `zone` | Must be declared in `[vision.zones]`. Zone is a normalized rectangle `[x0, y0, x1, y1]` in `[0, 1]`, `x0 < x1`, `y0 < y1`. This version supports rectangles only; polygons require a future RFC |
| `min_frames` | Default 3, minimum 2. "Consecutive" measured by camera frame sequence numbers; missing frame (gap in sequence) ⇒ window restarts. Insufficient consecutive frames ⇒ undecided ⇒ BLOCK |
| Window evaluation | Evaluates criteria on every frame of `min_frames` window then ANDs: all frames must satisfy. Equivalent to using minimum value for `gt`/`gte` and maximum value for `lt`/`lte`, applied to both `confidence` and `count` |
| `present` | Score threshold to compute `present` is constant `PRESENT_SCORE_FLOOR = 0.5` pinned in perception code and recorded in traces, not declared by maker; true safety threshold remains the gate's companion `confidence` criterion. A `present` (or `count`) fact for a label must be paired with companion `numeric` `confidence` criterion for same label, same zone, in gate `allow_when`; missing ⇒ rejected by `neuroedge build` and agent loader |

**No thresholds exist in `agent.toml`.** All thresholds on counts and confidence live in gate `numeric` criteria (Q-54, RFC-0009 §1). Makers choose *which labels become which facts*; **makers cannot choose safety thresholds**. There are no dedicated gate operators for vision: everything passes through `bool`/`numeric`.

**`present` and `count` cannot stand alone.** `bool` criteria have no reading age (`max_age_ms`). If a gate permits passage when `present: false` (or `people_at_gate: { lte: 0 }`, e.g., closing gate when no person is seen) and camera freezes repeating an old frame, the gate would incorrectly permit passage. Therefore, gates using vision facts `present` (or `count`) for a label must pair it with a `numeric` `confidence` criterion for the same label **and same zone**, located in `allow_when` of that exact gate — criteria declared only in `evaluate` without appearing in `allow_when` are not evaluated by the walker and do not count. This locks thresholds and `max_age_ms` in the gate, per Q-54. Missing ⇒ rejected by `neuroedge build` and agent loader. Additionally, the perception layer enforces a hardcoded 1000 ms frame age ceiling in code, non-configurable, recorded in traces: oldest frame > 1000 ms ⇒ fact undecided ⇒ BLOCK. The score threshold for computing `present` is the constant `PRESENT_SCORE_FLOOR = 0.5` recorded in traces, not declared by maker.

**Vision Fact Values on a Frame.** `confidence` = highest score of label in zone; no detections ⇒ `0.0` (absence is score 0, not "undecided"). `count` = number of detections of label in zone with score ≥ `PRESENT_SCORE_FLOOR`. `present` = `count ≥ 1`. Thus, the `close_gate` example (`person_confidence: { lte: 0.10 }`) has well-defined semantics: every frame in the window has no `person` detection in zone with score above 0.10.

**Single Path for Confidence.** Gates using `confidence_gte` on criteria declared as vision facts in `agent.toml` are rejected both at `neuroedge build` and agent loading. `gate lint` cannot perform this check: gates do not know which facts originate from vision; only build or agent loading possesses both gate and manifest. (`confidence_gte` on `numeric` criteria is already rejected by `gate lint`, RFC-0009 §3a.)

**Rejected with `AgentManifestError` (`NE3002`):** `kind` outside three values; unknown keys in `[vision.facts.*]`, including `bands`; `min_frames` < 2; `zone` undeclared or coordinates not matching `[x0, y0, x1, y1]`; criterion type of same name does not match `kind`; gate using `confidence_gte` on vision facts (rejected at build and agent load); gate using `present` or `count` lacking companion `numeric` `confidence` criterion for same label (rejected at build and agent load). Consolidated into `BuildFailed` (`NE3003`) like other build issues.

### 3d. Traces

Each vision fact evaluated for a verdict records an event in the `perception` group (Appendix C.1 of `docs/spec/core_contracts.md`; event names recorded in `docs/spec/simulation_coverage.md` §3 — §8):

```json
{ "offset_ms": 1840, "type": "vision_fact", "data": {
    "fact": "person_at_gate", "kind": "present", "min_frames": 3, "value": true, "age_ms": 140,
    "model": { "name": "person-det", "sha256": "…" },
    "frames": [
      { "frame_seq": 101, "vision_ref": { "sha256": "…", "size": 61440 }, "captured_ms": 1700, "labels": [{ "label": "person", "zone": "gate_area", "score": 0.93 }] },
      { "frame_seq": 102, "vision_ref": { "sha256": "…", "size": 61312 }, "captured_ms": 1767, "labels": [ … ] },
      { "frame_seq": 103, "vision_ref": { "sha256": "…", "size": 61500 }, "captured_ms": 1833, "labels": [ … ] } ] } }
```

- **Model identity** (name + sha256 of model file) resides on **every** visual `perception` event, along with a list of all models used in the session under `metadata` (§9.4). Swapping models mid-session still traces back to each verdict.
- **`vision_ref` = `{ sha256, size }`** recorded for **all frames in the window** that generated the fact for the verdict, not frames outside window (§9.5). **Raw images are not embedded.** Timestamps `captured_ms` and `frame_seq` (camera frame sequence numbers) of each frame are recorded so `replay` recalculates frame age and verifies sequence continuity identically to runtime (RFC-0009 §3c).
- Labels, zones, and scores of each frame in window are recorded; this is what `replay` uses to reproduce verdicts (FR-CI-02). A frame hash alone cannot be replayed.
- **Vision Fact Age:** Evaluation timestamp = offset of verdict event on same monotonic session timeline as HAL read timestamp. Traces record HAL read timestamp, `captured_ms`, and `age_ms`; `replay` recalculates and compares. `age_ms < 0` (read timestamp after evaluation timestamp) ⇒ BLOCK `criterion_unavailable`. For vision, window age is the age of the oldest frame in window: `age_ms = offset_ms - captured_ms_oldest`.
- **Fixed Age Ceiling and Score Threshold:** The perception layer has a fixed 1000 ms frame age ceiling in code, non-configurable, recorded in traces; oldest frame > 1000 ms ⇒ fact undecided ⇒ BLOCK. Score threshold for `present` is constant `PRESENT_SCORE_FLOOR = 0.5` recorded in traces, not declared by maker. **Frozen frames:** two adjacent frames in window having identical `vision_ref.sha256` ⇒ treated as camera freeze ⇒ fact undecided ⇒ BLOCK, even if driver attaches new `captured_ms` timestamp to repeated frame.
- `trace.v1` is **unchanged** (§4). Semantic lint in `python/neuroedge/trace.py` (TSK-V1b-08), violations ⇒ `TraceValidationError` (`NE4001`):
  - `sha256` (of `vision_ref` and `model`) matches `^[0-9a-f]{64}$`;
  - `uri` only when `metadata.raw_capture == true`; rejects base64 blobs in `data`;
  - visual `perception` event missing `model.name`/`model.sha256`, or model sha256 not listed in `metadata`;
  - element count of `frames` differs from event's `min_frames` (missing frames in window or excess frames outside window);
  - `frame_seq` non-consecutive (gaps in camera frame sequence numbers);
  - `age_ms` negative or inconsistent with HAL read timestamp and oldest frame.

### 3e. Fail-Closed (§9.7)

Checked in order, all branches BLOCK, **no interpolation from prior frames**, no default "no person seen" value:

| Scenario | `reason` |
|:---|:---|
| Lost camera, lost model, model fails to respond | `criterion_unavailable` |
| Two adjacent frames in window have identical `vision_ref.sha256` (frozen camera, driver still stamping new time) | `criterion_unavailable` |
| Stale frame: oldest frame age in window > `max_age_ms` of companion `numeric` criterion (RFC-0009 §3c) or > fixed 1000 ms perception ceiling; read timestamp after evaluation timestamp (`age_ms < 0`) | `criterion_unavailable` |
| Window lacks `min_frames` consecutive frames: dropped frame (gap in camera `frame_seq`); corrupted output filtered by perception layer before reaching gate (label outside model set, negative or non-integer `count`); missing companion `confidence` criterion for `present`/`count` | `criterion_unavailable` |
| Complete window, all frames have facts, but at least one frame fails `allow_when` range (evaluated per frame then ANDed) | `condition_not_met` |
| Score or count is NaN, ±inf, or outside `numeric` criterion `range` | `value_out_of_range` (RFC-0009 §9.1) |

By requiring companion `numeric` `confidence` criteria alongside `present` and calculating age from the oldest frame, frozen cameras repeating "nobody there" frames are blocked: `age_ms` of oldest frame exceeds `max_age_ms` (or 1000 ms ceiling), resulting in BLOCK `criterion_unavailable`, preventing erroneous ALLOW for hazardous commands (like closing gates).

### 3f. Equivalence Across Targets (§9.6)

Two propositions, verified separately, both must be demonstrated:

1. **Gates decide identically.** Virtual camera in `sim` (TSK-V1b-02) replays recorded frame sequence **and** recorded `perception` results; `neuroedge verify` compares verdicts across targets from identical `perception` events. Divergence ⇒ `SafetyRegressionError` (`NE4002`).
2. **Models see identically.** For each model sha256, inference results on each target must match host golden results within board's declared `vision_in` tolerance (`tolerance = { score_abs, box_iou_min }`, §3a). The `board.v1` schema sets a hard ceiling: `score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`, preventing boards from declaring inflated tolerances that make equivalence checks vacuous. Exceeding tolerance ⇒ `SafetyRegressionError` (`NE4002`). Inference golden and Action CI for frames: TSK-V1b-04.

### 3g. Points Decided at Review 2026-10-01

Four previously open points decided by product owner under maximum safety principle (Q-57, Q-62, §9); confirmed by lead architect when signing RFC:

1. **Zone shape:** Normalized rectangle `[x0, y0, x1, y1]` in `[0, 1]`, satisfying `x0 < x1`, `y0 < y1`. Only rectangular zones supported in this version; polygonal zones require a future RFC.
2. **Inference tolerance:** Declared in `vision_in` under `tolerance = { score_abs, box_iou_min }`, applying a single common value across all models on board. Schema `board.v1` sets hard ceiling: `score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`. Boards declaring values exceeding hard ceiling rejected at board load time with `BoardCapabilityError` (`NE3001`).
3. **Window aggregation of `count` and facts:** Evaluated per frame across window then ANDed (all frames must satisfy gate criteria). Equivalent to maximum value for `lte`/`lt` and minimum value for `gte`/`gt`, applied to both `count` and `confidence`. Dropped frames (gap in camera sequence numbers) restart the window from beginning.
4. **Frame age and safety for `present` facts:** `present` (or `count`) facts must be accompanied by companion `numeric` `confidence` criterion for same label, same zone, in gate `allow_when` (locks threshold and `max_age_ms`, Q-54). Visual window age is the age of oldest frame in window. Perception layer adds fixed 1000 ms age ceiling in code. Score threshold for `present` is fixed constant recorded in traces.

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | Yes — no profile in `boards/` declares `vision_in`, no agent in `fixtures/agents/` has `[vision]` block |
| Do currently invalid files become valid? | Yes — profiles declaring `vision_in` with correct shape (`modes[]`, enum `pixel_format`, `tolerance = { score_abs, box_iou_min }` within hard ceiling). Four open points decided (§3g), `board.v1` ready to freeze. Camera profile for `esp32s3` is M5Stack CoreS3 (`esp32s3-cores3`, Q-61) |
| Does schema version need bumping (`v1` → `v2`)? | No. `trace.v1` unchanged: `events[].data` constrains only `"type": "object"` and `metadata` has `additionalProperties: true`, so `model`, `frames`, `vision_ref`, and model list in `metadata` validate cleanly; rules in §3d are semantic lint in `trace.py`, not schema changes (RFC-0002 §9.2) |
| Impact on published gate hashes / signatures? | None |
| Impact on three canonical trace files? | None — they contain no visual events, so new lint does not touch them |
| Which gates in `digests.lock` change digest? | None; three sample vision gates (TSK-V1b-06) enter `digests.lock` via normal PR |
| Must `NETR` layout or C walker change? | Not for this RFC specifically; uses RFC-0009 `numeric` nodes |
| Do any answers in tool call corpus (`expected_results.yaml`) change? | None |

**Error Codes** (`neuroedge-prd.md` Appendix B): This RFC adds no codes. All classes used already exist in `python/neuroedge/errors.py`; on approval, the *Cause* column for three rows is widened:

| Class | Added Cause |
|:---|:---|
| `AgentManifestError` (`NE3002`) | Invalid `[vision]` block (§3c), gate using `confidence_gte` on vision facts (rejected at build and agent load), or gate using `present`/`count` lacking companion `numeric` `confidence` criterion for same label (rejected at build and agent load) |
| `TraceValidationError` (`NE4001`) | Visual semantic lint (§3d) — row currently specifies only schema and UART streams; checks consecutive `frame_seq`, oldest frame age matching non-negative `age_ms` |
| `SafetyRegressionError` (`NE4002`) | Model inference on target diverges from host golden beyond tolerance declared on board (§3f) |

`BoardCapabilityError` (`NE3001`): Widens causes to include declaring `tolerance` exceeding hard ceiling (`score_abs > 0.05` or `box_iou_min < 0.8`) alongside requesting capabilities board does not provide (§3b). `criterion_unavailable` and `value_out_of_range` are verdict reasons (RFC-0009), not exceptions.

## 5. Safety Impact

- **Gates no looser and no new vision semantics** (Q-54): `gate.v1`, resolution, and five inheritance principles unchanged. Constraint from `docs/architecture/vi/15-target-architecture.md` §4.4 — mapping vision to typed facts gate already knows how to evaluate, confidence thresholds locked with `numeric` — preserved intact.
- **Perception never becomes authority:** models supply facts only; all count and confidence thresholds are locked by gates and only narrow under inheritance. Makers cannot loosen thresholds via `agent.toml` because thresholds do not reside there (`bands` rejected).
- **Single path for confidence:** `confidence_gte` on vision facts rejected at both `neuroedge build` and agent load time, eliminating second path where locking could be omitted (§3c).
- **`present` and `count` do not stand alone:** Gates using `present` or `count` must include companion `numeric` `confidence` criterion for same label, same zone, in `allow_when` carrying `max_age_ms`. Eliminates risk of frozen cameras repeating "nobody there" frames granting ALLOW for `close_gate` written with `present: false`.
- **Per-frame evaluation then ANDed:** Criteria evaluated across each frame in `min_frames` window then ANDed: conservative in correct direction for both `gte`/`gt` and `lte`/`lt`, applied to both `confidence` and `count`. Dropped frames (gap in camera sequence numbers) restart window.
- **No interpolation and unified age check:** Lost camera, lost model, stale frame ⇒ BLOCK (§3e). Window age measured from oldest frame in window, combined with 1000 ms hard perception age ceiling. Read timestamp after evaluation timestamp (`age_ms < 0`) ⇒ BLOCK.
- **Privacy:** no raw frames in traces by default; raw image capture must be explicitly enabled (`metadata.raw_capture`). Only frames in window leave `vision_ref`. Stricter than microphones, never looser.
- **Model identity on every event:** changing models changes behavior; traces must reveal which model produced which conclusion, even if models swap mid-session.
- **Two-tier equivalence and tolerance ceiling (§3f):** "Gates decide identically" does not prove "models see identically"; both are tested. Schema `board.v1` enforces hard ceiling on inference tolerance (`score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`), preventing boards from declaring inflated tolerances making equivalence tests vacuous.
- **Remaining risk:** high-confidence model errors (confident misclassifications). Mitigated by numeric thresholds in gate, multi-frame windows, and — for irreversible actions — `on_block: ask`; cannot be eliminated completely. Four previously open points conclusively settled in §3g (review 2026-10-01, Q-62).
- **`esp32s3` memory budget:** Selected camera board is M5Stack CoreS3 (`esp32s3-cores3`, Q-61) with 16 MB flash, 8 MB PSRAM, 640×480 VGA GC0308 camera. Measuring SRAM/PSRAM on physical board per Q-3 is mandatory condition (TSK-I3a-01).

## 6. Alternatives Considered and Rejected

| Alternative | Reason for Rejection |
|:---|:---|
| Dedicated gate semantics for vision evidence (exclusion zones, people count) | Q-54: breaks rule engine determinism, requires major `gate.v1` RFC; mapping to typed facts suffices for priority use cases |
| Makers setting thresholds in `agent.toml` (including `bands` for `count`) | Safety semantics outside gate, hidden from `gate lint`; same rationale as RFC-0005 §6 and RFC-0009 §1 |
| Allowing `confidence_gte` in parallel with `numeric` criteria | Two paths means one will be left unlocked (§9.3) |
| Rejecting `confidence_gte` on vision facts only at build time while ignoring agent load | Dynamically loaded or externally distributed agents could bypass it; must reject at both build and agent load time |
| Checking `confidence_gte` on vision facts in `gate lint` | Gates do not know which facts come from vision; only build or agent loader possesses both gate and manifest |
| Aggregation rules "confidence = min", "count = min" across window | Direction-dependent (min correct for `gte`, incorrect for `lte`, e.g., `count lte 0`); replaced by "evaluate per frame then AND" (§9.2) |
| `present` or `count` standing alone without companion `confidence` criterion | `bool` criteria lack `max_age_ms`; frozen camera repeating "nobody there" grants dangerous ALLOW on `close_gate`; rejected (§3c) |
| `present` decided from single frame; `confidence` averaged or last frame | Single noisy frame unlocks door; averaging conceals weak frames (§9.2) |
| Allowing boards to freely declare inference tolerance without hard ceiling | Boards could declare overly permissive tolerances making target equivalence tests vacuous; rejected (§3a) |
| Integer `fps`, free string `pixel_format` | Cannot represent 7.5 fps; cannot match deterministically (RFC-0002 §9.1; §9.1) |
| Expanding `sensor.read` | Cannot carry frame streams; see arguments in RFC-0007 §2 |
| Recording every frame in traces | Violates NFR-PRIV-01, NFR-PRIV-03; 30 fps ≈ 13 MB/hour for hashes and metadata alone |
| Recording `vision_ref` only for final frame | Cannot audit `min_frames` rule and per-frame evaluation post-hoc (§9.5) |
| Model identity in `metadata` only | If models swap mid-session, cannot trace which verdict was produced by which model (§9.4) |
| Interpolating from prior frames on lost camera or stale frame | Hung camera appears as "nothing changed" (§9.7, RFC-0009 §9.5) |
| `verify` comparing verdicts only | Does not prove model produces identical results across all targets (§9.6) |

## 7. Verification Evidence

Each item indicates the §9 decision it covers. Corpus follows bidirectional closure rule (`CONTRIBUTING.md` §3).

- [ ] **Boards (§9.1, §9.9, §9.11):** valid examples — `linux` profile and `esp32s3-cores3` profile (M5Stack CoreS3, GC0308 VGA 640×480) declaring `vision_in` with valid `modes` and `tolerance`; negative tests — string `fps`, empty `modes`, `pixel_format` outside five enum values, missing `tolerance`, `tolerance.score_abs > 0.05` or `tolerance.box_iou_min < 0.8` ⇒ `BoardCapabilityError` (`NE3001`)
- [ ] **M5Stack CoreS3 memory measurements (TSK-I3a-01, Q-3, §9.11):** run model on `esp32s3-cores3` with GC0308 camera (VGA 640×480), record remaining SRAM and PSRAM, verify no heap overflow
- [ ] **`[requires]` (§3b, §9.11):** sample agent with `[requires] "vision.in"` with `min_width = 640, min_height = 480` matches successfully against `esp32s3-cores3`; board lacking satisfying mode (demands 1280×720) ⇒ `BoardCapabilityError` stating closest mode
- [ ] **Fact syntax and zones (§9.2, §9.9)** — `python/tests/test_compiler.py`: sample agent with valid `[vision]` builds cleanly; normalized rectangular zones `[x0, y0, x1, y1]`; each error ⇒ `AgentManifestError` (`NE3002`): unknown `kind`, `bands`, `min_frames = 1`, undeclared `zone`, coordinates outside `[0, 1]`, `x0 >= x1`, `y0 >= y1`, polygon zone shapes
- [ ] **Companion criterion constraints (§9.10):** gate using `present` or `count` facts without companion `numeric` `confidence` criterion for same label ⇒ rejected by `neuroedge build` and agent loader with `AgentManifestError` (`NE3002`)
- [ ] **Single path for confidence (§9.3):** gate using `confidence_gte` on vision facts **passes** `gate lint` but rejected at both `neuroedge build` and agent load time with `AgentManifestError` (`NE3002`) — pins lint/build/load boundaries
- [x] **Frame aggregation and dropped frames (§9.2, §9.9):** window `min_frames = 3`: 3 consecutive satisfying frames ⇒ ALLOW. Dropped camera frame sequence (`frame_seq`) ⇒ window reset ⇒ BLOCK `criterion_unavailable`. Per-frame evaluation then ANDed: with gate `count` `lte: 0`, sequence `[0, 1, 0]` ⇒ BLOCK, sequence `[0, 0, 0]` ⇒ ALLOW; with gate `confidence` `gte: 0.85`, sequence `[0.90, 0.80, 0.90]` ⇒ BLOCK, sequence `[0.86, 0.90, 0.88]` ⇒ ALLOW *(Completed: `python/tests/test_vision_facts.py`: `test_three_good_frames_allow_the_open_gate`, `test_confidence_gte_is_judged_on_every_frame`, `test_count_lte_zero_is_judged_on_every_frame`, `test_a_lost_frame_restarts_the_window`)*
- [x] **Frame age and frozen cameras (§9.7, §9.8, §9.10):** window age measured from oldest frame. Oldest frame with `age_ms > max_age_ms` of companion `confidence` ⇒ BLOCK `criterion_unavailable`. Oldest frame > 1000 ms (perception ceiling) ⇒ BLOCK `criterion_unavailable` even if gate `max_age_ms` is larger. HAL read timestamp after evaluation timestamp (`age_ms < 0`) ⇒ BLOCK `criterion_unavailable`. Frozen camera repeating "nobody there" (`people_at_gate: { lte: 0 }` or `person_at_gate: false`) ⇒ companion `confidence` exceeds age ⇒ BLOCK `criterion_unavailable`, preventing erroneous unlock. Two adjacent frames in window having identical `vision_ref.sha256` (driver stamping new `captured_ms`) ⇒ BLOCK `criterion_unavailable`. *(Completed: `test_vision_facts.py`: `test_a_window_older_than_the_ceiling_blocks_even_when_the_gate_allows_longer`, `test_a_window_older_than_the_gates_max_age_blocks_even_inside_the_ceiling`, `test_a_frame_read_after_the_instant_it_is_judged_blocks`, `test_a_camera_that_repeats_a_frame_is_frozen_whatever_time_it_stamps`, `test_a_frozen_camera_cannot_close_the_gate`; negative age to trace: `test_vision_trace.py::test_a_refused_window_is_recorded_and_valid_even_short_or_in_the_future`)*
- [x] **Model identity (§9.4)** — `fixtures/traces/invalid/` + `expected_errors.yaml`: visual `perception` event missing `model`, model sha256 not in `metadata`; session swapping models mid-run ⇒ each verdict traceable to its model *(Completed: `fixtures/traces/invalid/vision_model_missing.json`, `vision_model_not_listed.json`, `vision_model_bad_sha256.json`; mid-session model swap: `test_vision_trace.py::test_a_model_swap_mid_session_leaves_every_verdict_traceable_to_its_model`)*
- [x] **`vision_ref` and sequence continuity (§9.5)** — `fixtures/traces/invalid/`: `frames` count fewer or greater than `min_frames`; malformed `sha256`; `uri` without `raw_capture`; base64 in `data`; non-consecutive `frame_seq`; `age_ms` negative or inconsistent with HAL read timestamp and oldest frame *(Completed: `fixtures/traces/invalid/vision_frames_too_few.json`, `vision_frames_too_many.json`, `vision_ref_bad_sha256.json`, `vision_uri_without_raw_capture.json`, `vision_base64_blob.json`, `vision_image_field.json`, `vision_frame_seq_gap.json`, `vision_age_mismatch.json`, `vision_age_negative.json`; rules in `docs/spec/vision.md` §5)*
- [ ] **Equivalence and tolerance ceilings (§9.6, §9.9):** `verify` produces identical verdicts on `sim`, `linux`, `esp32s3` from identical `perception` events. Model inference matches host golden within board declared tolerance (`score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`) ⇒ green; exceeding tolerance ⇒ `SafetyRegressionError` (`NE4002`) *(Partial: host inference half completed — `python/tests/test_vision_golden.py`: identical inference and within-tolerance drift ⇒ green; exceeding `score_abs`, IoU below `box_iou_min`, missing/extra detections, wrong model golden ⇒ rejected; `neuroedge verify` runs all goldens in `fixtures/vision/golden/` across all boards declaring `vision_in` with that board's tolerance. Pending: physical model inference on NPU/`esp32s3` and verdict comparison on `esp32s3` from identical `perception` events.)*
- [x] `replay` reproduces verdicts from `perception` events without frame images, verifying frame age from `captured_ms` and `age_ms` *(Completed: `test_vision_trace.py`: `test_replay_reproduces_an_allow_from_the_perception_events`, `test_replay_reproduces_a_block_and_its_reason`, `test_replay_reproduces_a_fail_closed_block`, `test_the_verdict_comes_from_the_recorded_labels_not_the_recorded_gate_fact` — model invocation forbidden during replay)*
- [ ] `neuroedge gate lint` and `neuroedge verify` green
- [ ] Four open points of §3g fully settled per review 2026-10-01 with corresponding tests before approval

## 8. Post-Approval Tasks

- [x] Update `schemas/board.v1.json` (`vision_in`: `modes[]`, enum `pixel_format`, `tolerance = { score_abs, box_iou_min }` field with hard ceilings `score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`) — *met: `modes[]`, enum `pixel_format`, mandatory `tolerance` with hard ceilings — `tests/test_board_fixtures.py` (`vision_*`)*
- [ ] Add `esp32s3-cores3` (M5Stack CoreS3) board profile for ESP32-S3 with GC0308 VGA 640×480 camera (Q-61); carry out SRAM/PSRAM measurements per Q-3 (TSK-I3a-01)
- [ ] Update Appendix C.1 in `docs/spec/core_contracts.md`; FR-HAL-01 in `neuroedge-prd.md`; PRD Appendix B — widen causes for three rows in §4; `TODOS.md` #14 (fix resides in RFC-0013)
- [x] `docs/spec/simulation_coverage.md`: visual `perception` event names in §3, `vision.in` row in matrix §2 *(Completed: `camera_unavailable` in §3, `vision.in` item in matrix §2; `docs/spec/camera.md`)*
- [x] `neuroedge-roadmap.md`: TSK-V1b-07 done; open TSK-V1b-01, TSK-V1b-02, TSK-V1b-03, TSK-V1b-04, TSK-V1b-05, TSK-V1b-06, TSK-V1b-08 *(Completed 2026-10-04: six rows V1b-01 → V1b-08 in roadmap; V1b-01 and V1b-04 remain 🟡, V1b-05 ⏳)*
- [x] `engine/compiler.py` and agent loader runtime: `[vision]` block, rectangular zones `[x0, y0, x1, y1]`, reject `confidence_gte` on vision facts at both build and agent load, require companion `numeric` `confidence` criterion alongside `present`/`count`, match `modes[]` *(Completed: `check_vision` and `_check_vision_in` in `engine/compiler.py`; `[requires] "vision.in"` matches `modes[]` in `hal/vision.py::Requirement`; session rejects loading when camera fails to open — `tests/test_vision_camera.py`: `test_a_bound_no_mode_meets_is_refused_naming_the_closest_mode`, `test_confidence_gte_on_a_vision_fact_is_refused_one_road_for_confidence`, `test_present_without_its_confidence_pair_is_refused_a_bool_has_no_age`)*
- [x] `perception/vision/`: per-frame evaluation then AND logic, check consecutive `frame_seq` and reset window on dropped frames, calculate window age from oldest frame, enforce fixed 1000 ms perception layer age ceiling, pin constant `present` score threshold in traces *(Completed: `python/neuroedge/perception/vision/` (`facts.py`, `pipeline.py`); spec `docs/spec/vision.md`)*
- [x] `python/neuroedge/trace.py`: semantic lint §3d (check `frame_seq`, check oldest frame age and non-negative `age_ms`) *(Completed: `lint_vision` in `python/neuroedge/trace.py`, 15 invalid fixture files `fixtures/traces/invalid/vision_*.json`)*
- [ ] `python/neuroedge/hal/` (`linux.py`, `sim.py`), virtual camera in `sim` (TSK-V1b-02), inference golden by model sha256 and tolerance check in `verify` (TSK-V1b-04) *(Partial — completed: `LinuxHAL.vision_in` via V4L2 (`hal/v4l2.py`), `SimHAL.vision_in` + virtual camera `sim/vision/`, corpus `fixtures/traces/vision/` replay across all boards declaring `vision.in` (`neuroedge verify`). Pending: inference golden and tolerance checking (TSK-V1b-04); on-chip camera. Running on kernel: `tests_linux/test_camera_v4l2.py` on `vivid` (CI run 37153005998))*
- [ ] Fixtures/tests; update `docs/rfc/README.md` and `CHANGELOG.md`

## 9. Decisions on Open Questions (Q-57, 2026-09-30; Q-62, 2026-10-01)

Product owner delegated decision on open questions under the **maximum safety** principle: between two alternatives, choose the one that is fail-closed and harder to misuse, even if it requires more effort. The decisions below have been **incorporated into §3–§8**; this section is preserved as a decision log (Q-57). RFC approval still requires lead architect signature (`CONTRIBUTING.md` §3).

1. **`pixel_format`** is a closed enum: `yuyv`, `mjpeg`, `rgb565`, `rgb888`, `gray8`; adding values requires an RFC. *Why:* matching against `[requires]` must be deterministic.
2. **Fact syntax** in `agent.toml`: `[vision] model = "<file>"` and each fact is `[vision.facts.<name>]` with `label`, `zone` (declared in `[vision.zones]`), `kind` ∈ {`present` → `bool`, `count` → `numeric` (integer ≥ 0), `confidence` → `numeric` in [0, 1]}, and `min_frames`. No `bands`: all count and confidence thresholds reside in gate `numeric` criteria (Q-54, RFC-0009 §1). Fact names match gate criteria names. `present` requires `min_frames` consecutive frames (default 3, minimum 2). Window aggregation: evaluate criteria on each frame across `min_frames` window then AND (all frames must satisfy); equivalent to min for `gte`/`gt` and max for `lte`/`lt`, applied to both `confidence` and `count`. "Consecutive" measured by camera frame sequence numbers; dropped frames ⇒ reset window. *Why:* min rule is correct only for `gte`, incorrect for `lte` (e.g. `count lte 0`); per-frame AND is conservative and correct in all comparison directions.
3. **Single path for confidence:** `numeric` criteria only (RFC-0009). `neuroedge build` and agent loader reject (`AgentManifestError`, NE3002) gates using `confidence_gte` on criteria declared as vision facts in `agent.toml` — gates do not know which facts come from vision; only build or agent loader possesses both gate and manifest. *Why:* two paths means one will be left unlocked.
4. **Model identity** (name + sha256 of model file) resides on **every** `perception` event, along with list in `metadata`. *Why:* models swapped mid-session remain traceable to each verdict.
5. **`vision_ref`** recorded for **all frames in the window** that generated facts for a verdict, not frames outside window. *Why:* sufficient for auditing without bloating traces.
6. **Equivalence.** Virtual camera in `sim` replays recorded frame sequences **and** recorded `perception` results; `verify` compares verdicts across targets from identical `perception` events. Model inference is tested separately: for each model sha256, results on each target must match host golden results within board's declared tolerance (`tolerance = { score_abs, box_iou_min }`, hard ceilings `score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`); exceeding tolerance ⇒ `SafetyRegressionError` (NE4002). *Why:* separates "gates decide identically" from "models see identically", both must be proven.
7. **Lost camera or model, stale frames** (exceeding `max_age_ms` of RFC-0009, calculated from oldest frame in window) ⇒ facts undecided ⇒ BLOCK; no interpolation from prior frames.
8. **Vision fact age** (review 2026-10-01, Q-62). HAL read timestamp compared to evaluation timestamp (verdict offset); `age_ms < 0` ⇒ BLOCK `criterion_unavailable`. Visual window age is the age of oldest frame in window. Perception layer enforces fixed 1000 ms age ceiling in traces; exceeding ceiling ⇒ BLOCK. *Why:* unifies fact age definition, preventing camera lag or stale frames from slipping past verdicts.
9. **Frame aggregation and tolerance ceilings** (review 2026-10-01, Q-62). Evaluate per frame then AND; dropped frames (gap in camera sequence numbers) ⇒ restart window. Zone is normalized rectangle `[x0, y0, x1, y1]` in `[0, 1]`, `x0 < x1`, `y0 < y1`. Inference tolerance in `vision_in` is `tolerance = { score_abs, box_iou_min }` with schema hard ceiling `score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`. *Why:* conclusively settles open points of §3g; blocks boards from declaring inflated tolerances making equivalence tests vacuous.
10. **`present` does not stand alone** (review 2026-10-01, Q-62). Gates using `present` (or `count`) for a label must pair it with companion `numeric` `confidence` criterion for same label, same zone, in `allow_when` carrying `max_age_ms`; missing ⇒ rejected by `neuroedge build` and agent loader. Score threshold for `present` is constant `PRESENT_SCORE_FLOOR = 0.5` recorded in traces, not declared by maker. *Why:* `bool` criteria have no `max_age_ms`; if `present: false` stands alone during camera freeze it would grant dangerous ALLOW (e.g. `close_gate`). Mandatory companion `confidence` ensures gate locks threshold and age ceiling per Q-54.
11. **ESP32-S3 camera board** (review 2026-10-01, Q-62). Selects M5Stack CoreS3 board (Q-61), profile `esp32s3-cores3`. GC0308 0.3 MP camera (VGA 640×480), 16 MB flash, 8 MB PSRAM. Measuring SRAM/PSRAM per Q-3 is mandatory condition (TSK-I3a-01). Default board for `esp32s3` remains `esp32s3-box-3`. *Why:* M5Stack CoreS3 satisfies criteria for all five core primitives plus camera; GC0308 VGA accommodates 640×480 resolution of base models.
12. **Frozen frames and `present` threshold** (review 2026-10-01, Q-62). Two adjacent frames in window sharing identical `vision_ref.sha256` ⇒ camera freeze ⇒ BLOCK `criterion_unavailable`. `PRESENT_SCORE_FLOOR = 0.5` pinned in perception code, recorded in traces. *Why:* frame age fails to catch drivers attaching fresh timestamps to identical images; real sensors always carry noise, so byte-identical frames indicate freezing. Threshold for `present` must be concrete number for replay reproduction; safety threshold resides in gate `confidence` criterion.
13. **Vision fact values and companion criteria** (review 2026-10-01, Q-62). On each frame: `confidence` = highest score of label in zone, no detections ⇒ `0.0`; `count` = detections with score ≥ `PRESENT_SCORE_FLOOR`; `present` = `count ≥ 1`. Companion `confidence` criterion for `present`/`count` must share label and zone and reside in `allow_when`. Frame failing `allow_when` range ⇒ `condition_not_met`, not `criterion_unavailable` (RFC-0009 §3c). *Why:* criteria declared only in `evaluate` are not evaluated by walker so carry no age; undefined values on missing detections render close-gate examples meaningless.
