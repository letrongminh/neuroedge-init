# Vision — from frames to gate facts and evidence in traces

**Trạng thái:** canonical specification (TSK-V1b-03, V1b-04, V1b-06, V1b-08). Original contract: [RFC-0012](../rfc/0012-nguyen-thuy-vision-in.md)
§3c–§3e, §9; decisions Q-54 (vision reduces to typed facts, thresholds locked at gate), Q-62; requirements
FR-MDL-04, FR-MDL-07, FR-CI-02, NFR-PRIV-01, NFR-PRIV-03. Implementation: `python/neuroedge/perception/vision/`,
lint in `python/neuroedge/trace.py`, replay in `python/neuroedge/testing/player.py`. Keywords **MUST**,
**MUST NOT** carry their RFC 2119 meanings.

This document is the **single place** defining the path from camera frames to gate facts, the contract of
vision models, and the `vision_fact` event shape. RFC-0012 preserves rationale; here preserves integration points (§2) for
`vision.in` (TSK-V1b-01, V1b-02) and for frame-level Action CI (TSK-V1b-04).

## 1. Principles

1. **Models only provide facts, no authority.** Model outputs are **untrusted** inputs:
   domain check (§3.2), then threshold, then gate. Confidence thresholds and counts are `numeric` criteria locked at the gate
   (Q-54, RFC-0009); the perception layer has no thresholds other than two constants pinned in code (§4.1).
2. **Missing data blocks.** Model missing, model times out, garbage output, dropped frames, frozen camera, frames
   too old ⇒ facts **unresolved** ⇒ gate blocks with `criterion_unavailable`. No interpolation from previous frames,
   no default "không thấy người" ("no person seen") value (invariant #2).
3. **Traces do not contain images.** Only `vision_ref` (hash + size) and labels/scores of frames in the window.
   `uri` only when `metadata.raw_capture` is `true`.
4. **Replay does not invoke models.** Verdicts are recomputed from recorded labels (§6).

## 2. Integration point for camera — frames in, facts out

```text
 vision.in (HAL: linux / sim)            perception/vision/                       engine
 ───────────────────────────             ─────────────────────────────            ─────────────────
 Frame(seq, captured_ms, pixels)  ──►    VisionPipeline.push(frame)
                                            model.detect(frame)   (untrusted)
                                            sanitize → zone → window buffer
                                         VisionPipeline.facts_for(engine.tree(key))
                                            vision_fact × each fact     ──►  EventLog
                                            {criterion: Fact}           ──►  engine.evaluate(key, facts)
```

Contract for camera side (TSK-V1b-01 on `linux`, TSK-V1b-02 virtual camera on `sim`):

| `Frame` field | Meaning |
|:---|:---|
| `seq` | Frame sequence number **of the camera**: integer, increments by 1 per frame. Sequence jumps (dropped frames) or repeated sequence numbers cause the window to **restart** |
| `captured_ms` | HAL read timestamp, on session **`EventLog` clock** (same clock as `Fact.read_ms`). Finite number; `Frame` rejects other values |
| `pixels` | Image bytes. In memory only; never in traces. `vision_ref.sha256` is the SHA-256 of these exact bytes |
| `width`, `height`, `pixel_format` | Frame description; perception layer does not use them for decisions |

Call order in a session: `push` every frame as soon as delivered by HAL; **immediately before** `engine.evaluate`, call
`facts_for(engine.tree(key))` and pass result as `context` of `evaluate`. `facts_for` records
`vision_fact` events at the offset of the evaluation timestamp, so they precede `gate_evaluation_begin` of the same
verdict. Facts that cannot be read are **absent** from the result; engine blocks with `criterion_unavailable`.

Virtual camera in `sim` (V1b-02) replays recorded frame sequences **and** — for `verify` cross-target decision comparisons
— recorded `perception` results (RFC-0012 §3f); that is the responsibility of that slice, using this same `Frame`.

## 3. Vision models

### 3.1 Interface (FR-MDL-04, FR-MDL-07)

One method: **frames in, detections out**.

```python
class VisionModel(Protocol):
    identity: ModelIdentity            # model name + sha256 of file
    labels: Collection[str]            # CLOSED set of labels the model can predict
    def detect(self, frame: Frame) -> Sequence[Detection] | Inference: ...
```

- `Detection(label, score, box)`: `box` is normalized `(x0, y0, x1, y1)` in `[0, 1]`, `x0 < x1`, `y0 < y1`.
- `Inference(detections, latency_ms)`: returned instead of raw sequence when simulation model wants to specify how long it took
  (virtual session time; doubles never sleep). Without `latency_ms`, perception layer measures it.
- `detect` is **synchronous**. Asynchronous adapters (cloud) wrap calls internally; `detect` returning an awaitable is treated as
  `model_error`, never awaited implicitly.

### 3.2 Everything the model says is untrusted

`sanitize` checks domains. **The entire frame is rejected** (`rejected: garbage`, all facts on that frame unresolved) when:
result is not list/tuple; exceeds `MAX_DETECTIONS` (1000) detections; an element is not a `Detection`;
label is outside model's `labels`; `score` is not a number (string, `bool`, `None`); `box` missing, malformed, or
outside `[0, 1]`. (Detections without a `box` are rejected: cannot be assigned to a zone, and discarding it would falsely under-report presence.)

Scores that are **numeric but invalid** (NaN, ±inf, outside `[0, 1]`) are **retained**: the `confidence`/`count` fact
for that frame becomes NaN, so the gate returns `value_out_of_range` regardless of declared `range`; `present` facts (boolean
without a range) remain unresolved (`garbage`). Both result in BLOCK (RFC-0012 §3e, last line).

### 3.3 Model errors

| What happens | Frame rejected with | Recorded in |
|:---|:---|:---|
| `detect` raises `VisionUnavailable` (model lost, connection lost) | `model_unavailable` | `frames[].rejected` |
| `detect` raises other exception | `model_error` | as above |
| Responds after `timeout_ms` (default 200; `[vision] timeout_ms`), or `latency_ms` is not a finite number ≥ 0 | `timeout` | as above |
| Garbage output (§3.2) | `garbage` | as above |

`latency_ms` self-reported by model is only trusted upward: actual measured call duration is never reduced.

`push` **never raises** on model errors. Rejected frames still enter the window: all facts on a window containing
it remain unresolved until it rolls out (`min_frames` frames later). `VisionUnavailable` is a subclass of
`PerceptionUnavailableError` (`NE5001`): does not add an error code.

### 3.4 Model selection via configuration (`[vision]` block)

```toml
[vision]
provider   = "replay"                        # or "python:pkg.mod:factory"
model      = "models/person-det.tflite"      # YOUR file; NeuroEdge does not ship or download it
timeout_ms = 200

[vision.options]                             # for your adapter
```

Changing model = changing `provider` line (and `[vision.options]`); camera, facts, gates remain unchanged. Similar to `[stt]`/`[tts]`
(`perception/providers/`): `registry.make_vision_model(config, root)`; custom adapters are
`factory(config) -> VisionModel`, validated (has `identity`, non-empty string `labels`, `detect`).
Missing `provider` ⇒ valid table but `make_vision_model` rejects (no real default). Built-in: `replay`.
Real models (ONNX, cloud, NPU behind `accel/`: TSK-V1b-05) are adapters; no heavy dependencies added.

`parse_vision` validates tables (syntax RFC-0012 §3c): `kind` ∈ {`present`, `count`, `confidence`}; unknown keys in
`[vision.facts.*]` (including `bands`, any thresholds) are rejected; integer `min_frames` 2–64 (default 3); `zone` required;
zone is normalized rectangle `[x0, y0, x1, y1]` (polygons rejected); API keys rejected, values not echoed.
Errors are `AgentManifestError` (`NE3002`). **Wiring into `neuroedge build`** (checking matching criterion types, `confidence_gte`
on visual facts, `present` lacking `confidence` at agent build/load time) is pending in this slice (§8).

### 3.5 Test double model (`provider = "replay"`)

`ScriptedVisionModel` (`fake.py`): no ML, no network, deterministic, used for tests, `sim`, and frame Action CI.
`script` specifies what model sees at each frame sequence number; **frames outside script are not "empty"**:
model is not ready for that frame (`model_unavailable`) unless `default = []` explicitly specifies an empty scene. `fail` lists frame
numbers where it raises errors. Identity when no file is present: SHA-256 of the script itself and label set.

## 4. Facts

Each `[vision.facts.<name>]` becomes a gate criterion of the same name: `present` → `bool`; `count`, `confidence` → `numeric`.

### 4.1 Per-frame values

Computed from scores of detections **matching label, within zone** of the fact (detection belongs to zone when box **center** lies within
rectangle, boundary inclusive):

| `kind` | Value |
|:---|:---|
| `confidence` | highest score; **no detections ⇒ `0.0`** (absence is score 0, not unresolved) |
| `count` | number of detections with score ≥ `PRESENT_SCORE_FLOOR` (**0.5**, pinned constant in code) |
| `present` | `count ≥ 1` |

Two pinned constants in code, non-configurable, recorded in every `vision_fact` for replay verification: `PRESENT_SCORE_FLOOR = 0.5`
and `MAX_FRAME_AGE_MS = 1000`. True safety thresholds are the gate's `confidence` `numeric` criteria.

### 4.2 Windows and AND conjunction

Window is the latest `min_frames` **consecutive** frames. Gate evaluates criteria **on each frame then ANDs**: a single
noisy frame cannot open anything, a single bad frame always blocks — holds for both `gte`/`gt` and `lte`/`lt`
(`count lte 0` with `[0, 1, 0]` ⇒ BLOCK, `[0, 0, 0]` ⇒ ALLOW; `confidence gte 0.85` with `[0.90, 0.80, 0.90]` ⇒ BLOCK).
Implementation that **preserves gate semantics**: `engine_fact` walks window frames through decision tree's
own `walk` and presents the engine **one** `Fact` — value of first frame rejected by criterion, otherwise the
last frame. Engine walks tree normally and records exact AND verdict, alongside `reason` of the first bad frame.

### 4.3 When facts are unresolved

`FactReading.unavailable` belongs to `UNAVAILABLE`; gate blocks with `criterion_unavailable`:

| Reason | When |
|:---|:---|
| `model_unavailable`, `model_error`, `timeout`, `garbage` | a frame in the window was rejected (§3.3), or `present` on invalid score |
| `window_size` | fewer than `min_frames` frames (startup, or just **restarted** due to dropped frame) |
| `frame_gap` | non-consecutive `frame_seq` in window (only observed in replay: live pipeline already restarted window) |
| `frozen` | two consecutive frames share identical `vision_ref.sha256`, even if driver attached a new timestamp (RFC-0012 §9.12) |
| `future` | a frame was read after evaluation timestamp (`age_ms < 0`) |
| `stale` | oldest frame is older than `MAX_FRAME_AGE_MS` = 1000 ms, even if gate `max_age_ms` is larger |
| `unpaired` | gate uses `present`/`count` **without** companion `numeric` `confidence` criterion for same label, same zone in `allow_when` (§9.10). `bool` has no `max_age_ms`: without this pair, a frozen camera repeating "không có người" ("no person present") would pass `present: false`. Build rejects such gates; this is the same rule at runtime and replay |
| `mismatch` | replay only: recorded event does not match its own labels (§6) |

Age: `age_ms = offset_ms − min(captured_ms)` — of the **oldest** frame, measured to offset of the
`vision_fact` event itself. Accompanying `numeric` criteria also check their `max_age_ms` against this same age (RFC-0009 §3c). Switching models
mid-session (`set_model`) **restarts the window**: no window mixes outputs from two models.

## 5. `vision_fact` event (`perception` group)

`trace.v1` is unchanged (`type` open, `data` is object). Each visual fact evaluated for a verdict records an
event, at offset of evaluation timestamp, preceding `gate_evaluation_begin`:

| `data` field | Meaning |
|:---|:---|
| `fact`, `kind`, `label`, `zone`, `min_frames` | fact and its configuration |
| `value` | **newest** frame value; `null` when fact is unresolved. NaN written as `"nan"` |
| `values` | values across each frame in the window, same order as `frames` |
| `unavailable` | present **if and only if** `value` is `null`: a value from `UNAVAILABLE` |
| `age_ms` | age of oldest frame (§4.3); `null` when no frames exist |
| `max_frame_age_ms`, `present_score_floor` | two pinned constants (§4.1) |
| `model` | `{name, sha256}` of the model that read the frames (RFC-0012 §9.4) |
| `frames[]` | `{frame_seq, vision_ref: {sha256, size}, captured_ms, labels: [{label, zone, score}], rejected?}` |

`labels` only retains detections matching label and zone of this fact — sufficient for recomputation, nothing more. `metadata.vision_models`
lists all models in the session (`[{name, sha256}]`); `metadata.raw_capture` is `true` only when deliberately saving raw images.

### Semantic lint (`lint_vision`, `validate_trace`, `NE4001`)

Every violation has a counter-example fixture in `fixtures/traces/invalid/` (bidirectionally locked with `expected_errors.yaml`):

| Rule | File |
|:---|:---|
| `uri` only when `metadata.raw_capture == true` | `vision_uri_without_raw_capture` |
| `sha256` of `vision_ref` strictly matches `^[0-9a-f]{64}$` | `vision_ref_bad_sha256` |
| model `sha256` well-formed · `model` present · listed in `metadata.vision_models` | `vision_model_bad_sha256`, `vision_model_missing`, `vision_model_not_listed` |
| number of `frames` = `min_frames` when fact was read (no fewer, no more) | `vision_frames_too_few`, `vision_frames_too_many` |
| `frame_seq` consecutive | `vision_frame_seq_gap` |
| `age_ms` = `offset_ms` − oldest `captured_ms`; no frame read after evaluation timestamp when fact was read | `vision_age_mismatch`, `vision_age_negative` |
| no embedded images (base64, `data:`) and no unknown fields | `vision_base64_blob`, `vision_image_field` |
| `value` and `unavailable` are mutually exclusive | `vision_value_with_unavailable` |
| recorded labels match fact label/zone | `vision_foreign_label` |
| `metadata.raw_capture` is boolean | `vision_raw_capture_not_boolean` |

Windows rejected by perception layer (`unavailable`) are **valid** even if shorter than `min_frames` or containing future frames (negative age):
that is precisely how a BLOCK verdict is recorded. Remaining checks still apply. Three canonical traces contain no visual
events, so lint does not touch them.

## 6. Replay (FR-CI-02)

`neuroedge replay` recomputes verdicts from `perception` events, **without invoking models and without requiring frames**.
For each verdict, `testing/player.py` retrieves preceding `vision_fact` events, calls `reading_from_event` — recomputing per-frame values
from recorded labels, verifying sequence continuity, freeze, age — then uses `facts_for_tree` (same function used in live path) and supplies
engine **instead** of recorded `gate_facts` for those criteria. Events are re-recorded onto the replay timeline (age
preserved), so replayed traces are also replayable.

Events failing to match their own labels (value, `values`, `age_ms`, `unavailable`, two pinned constants) ⇒ `mismatch`: fact
absent, gate blocks with `criterion_unavailable`, replay warns and records `vision_fact_problem`. Modified traces can only block
more, never allow more. Identical `perception` events yield identical verdicts across all targets: that is the
"gates decide identically" proposition of RFC-0012 §3f (`verify` and virtual camera: V1b-02, V1b-04).

## 6a. Action CI for frames (TSK-V1b-04, FR-CI-01→04)

`python/neuroedge/testing/vision.py`. A **scene** (`fixtures/vision/<scene>/`) is a frame directory: `scene.toml`
(`gate`, `action`, `step_ms`, `[context]` for non-visual facts, `[vision]` for zones and facts), frame files,
and `<name>.json` for each frame — what the (double) model sees. Numbered filenames are **camera frame numbers** (missing numbers = dropped frames);
frames **without** `.json` represent non-responding models, not empty scenes (`[]` is an empty scene).

| FR-CI Component | Function | Notes |
|:---|:---|:---|
| Record (CI-01) | `run_scene`, `record_scene(scene, path, raw=False)` | one evaluation per frame, simulated clock; trace contains only `vision_ref` (hash + size). `raw=True` is an explicit choice (NFR-PRIV-03): frames copied to `frames/<sha256>.bin` next to trace, `metadata.raw_capture = true`, each `vision_ref` has `uri` |
| Replay (CI-02) | `replay_verdicts(trace, gates)`, or `neuroedge replay` / `TracePlayer` when agent is present | recomputes verdicts from recorded `vision_fact` and `gate_facts`; no model, no frames |
| Assert (CI-03) | `assert_verdicts(run, [...], reason=…)`, `assert_replay_matches(run)` | sequence of verdicts across frames; replay must match live run |
| Golden (CI-04) | `assert_matches_golden(run.trace, golden)` | same as all traces (`golden.py`) |

Scene repository is bidirectionally locked with `fixtures/vision/expected_results.yaml` (one entry per folder, one folder per entry); five
existing scenes include stranger entering/exiting door zone, frozen camera, frame drop, silent model, person in curtain zone, parcel.
No separate CLI command or GitHub Action input exists yet for frames (repo has no `action.yml` yet; adding commands requires updating CLI snapshot).

## 6b. Three sample gates (TSK-V1b-06, `gates/vision/`)

`entry-no-stranger` (do not unlock when stranger in door zone), `zone-clear` (blinds/roller door do not move when person
in zone), and `package-notify` (notify package only when certain). Each gate uses `present` paired with a companion `confidence` `numeric`
criterion with same label and zone, `max_age_ms` ≤ 500; thresholds locked at the gate (Q-54). Counter-examples in `fixtures/gates/vision/` (not
in `fixtures/gates/invalid/` because they inherit gates from `gates/`, not fixture registry): children loosening thresholds or
`max_age_ms`/`range` are rejected by `gate lint`; children only tightening are valid.

## 6c. Inference golden and cross-target tolerance (TSK-V1b-04, RFC-0012 §3f proposition 2, §9.6, §9.9)

"Gates decide identically" (replay, §6) and "models see identically" are two distinct propositions. The latter is verified
by `python/neuroedge/testing/vision_golden.py`.

**Golden** (`neuroedge.vision-golden/v1`, JSON, `fixtures/vision/golden/<scene>.json`): model identity (`name` +
`sha256`) and, indexed by **content hash of each frame** (`vision_ref.sha256`, without pixels), detections `{label, score, box}`
the model produces on host. A golden belongs to exactly one model: comparing inferences of a different model against it is **rejected**
(`VerificationError`, NE4004), never compared implicitly. Recording golden (`record_golden`) rejects models failing to respond for a frame,
returning garbage, scores outside `[0, 1]`, or two frames with identical bytes producing different outputs.

**Tolerance** is `vision_in.tolerance = {score_abs, box_iou_min}` of the **board itself** (`tolerance_of(board)`; hard ceiling of
`board.v1`: `score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`, rechecked in `Tolerance`). Boards without cameras do not have this check.

**Matching rules** (one-to-one, deterministic), per frame:

1. only match two detections **with same label** whose bounding boxes overlap with IoU ≥ `box_iou_min`;
2. all candidate pairs are matched in order of highest IoU, then smallest score discrepancy, then position; each detection used at most once;
3. each pair must satisfy |score − golden score| ≤ `score_abs` (boundary inclusive, plus 1e-9 for floating-point error);
4. golden detections that remain unmatched are **missing**; target detections that remain unmatched are **spurious** — spurious is also a regression, even with low score,
   because it alters `confidence` facts read by gates.

Target frames that fail to run inference, or golden frames missing, are also regressions. First discrepancy ⇒ `SafetyRegressionError` (NE4002) reporting frame
(hash), detection, and values; remaining regressions recorded alongside.

**Integration.** `neuroedge verify` runs all goldens in `fixtures/vision/golden/` across **every board declaring `vision_in`** for requested
targets (`sim-rpi5`, `linux-rpi5`), using that board's tolerance, counted separately; no golden compared ⇒ NE4004 like other groups. Action CI APIs:
`record_scene_golden`, `check_scene_inference(scene, golden, tolerance)`, `check_model`.

**Unproven here** (requires real models or real boards): on `sim` and `linux` models run on host CPU, so checks
only prove frames and plumbing match; it truly bites when a target runs models with different runtimes or hardware — NPU (TSK-V1b-05),
`esp32s3` (TSK-I3a-04) — and delivers detections to checks in golden format (`InferenceGolden.load`). Golden for a real network
also requires real models; existing goldens belong to `replay` models on sample scenes.

## 7. Implementation interpretive decisions

RFC-0012 left the following points open; this implementation chose safer alternatives:

1. **Zone contains detection when box center lies within, boundary inclusive.** Detections without boxes are rejected (§3.2).
2. **Event `value` is newest frame**; per-frame values in `values`.
3. **Age measured to offset of `vision_fact`**, immediately before gate evaluation; `gate_facts` additionally records age at engine timestamp.
4. **`labels` recorded per fact** (only its label and zone), not entire frame: less exposure, still recomputable.
5. **`unpaired` checked at runtime** in addition to build time, so gates slipping past build cannot escape.
6. **NaN/±inf/out-of-`[0, 1]` scores** are type-valid but domain-invalid: numeric facts become NaN ⇒ `value_out_of_range`.

## 8. Not yet implemented in this release

- NPU (TSK-V1b-05) and **real** model inference on target (V1b-05, I3a-04): real network goldens and on-device comparison — §6c.
- Wiring `parse_vision` into `neuroedge build` and agent loading: criterion type matching, `confidence_gte` on visual facts, `present`/`count` lacking `confidence` — RFC-0012 §8 (`engine/compiler.py`).
- Constants `MAX_FRAME_AGE_MS`, `PRESENT_SCORE_FLOOR` reside in `perception/vision/model.py`; `trace.py` does not import them (layering) and `replay` verifies recorded values against them.
