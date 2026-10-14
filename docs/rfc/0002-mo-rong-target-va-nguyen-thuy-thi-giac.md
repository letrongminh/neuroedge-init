# RFC-0002: Expand Target List

| | |
|:---|:---|
| **RFC ID** | 0002 |
| **Affected Schema** | `board.v1`, `trace.v1` — `target` enum **only**; does **not** touch `gate.v1` |
| **Related PRD Requirements** | FR-TGT-08, FR-HAL-01, FR-HAL-04, FR-HAL-05 |
| **Author** | V1 — Platform Core Engineer |
| **Date Opened** | 2026-09-22 · scope narrowed 2026-09-23 after review (minutes: `docs/archive/rfc-0002-review-record.md` (deleted; `git show 7626b62:docs/archive/rfc-0002-review-record.md`)) |
| **Status** | ✅ Approved (2026-10-04) — lead architect signed per Q-67 (decision 4); implemented in I2c (§10) |
| **Approver** | **Lead Architect — mandatory.** RFC does not make gates more lax, but touches three test invariants protecting target equivalence (§5), and Block V1a Exit Criterion 1 requires lead architect sign-off (`docs/architecture/vi/15-target-architecture.md` §4.4) |
| **Verification** | *(none yet — belongs to the second pull request, now in increment I2c (Q-67; previously I11 after Developer Beta per Q-40), see §8 and §10)* |

> **Scope of this pull request:** RFC file only, **no schema edits yet**, following
> `docs/rfc/README.md` step 2. The three schemas in `schemas/` remain intact; the existing
> test suite must stay green after merging this RFC.

> **Scope narrowing (2026-09-23).** The initial RFC draft combined three items: expanding
> the `target` enum, adding the `vision.in` primitive, and the `vision_ref` convention in
> traces. Following review, this RFC **retains only the first item**, plus machine-readable
> target tiers. `vision.in` and visual evidence in traces are moved to §9 with activation
> triggers. The file name is retained to avoid breaking links.

> **Merge timing (2026-09-25, confirmed).** Timing prose in the header and §8 updated per
> PRD Q-40: the second pull request belongs to increment I11, after Developer Beta. Proposed
> content remains unchanged; the RFC is under discussion and still requires lead architect
> signature before approval.

---

## 1. Problem

Phase 2 (`docs/architecture/vi/15-target-architecture.md` §4.4) expands the hardware catalog
to Jetson (Tier 2), STM32, and RP2350 (Tier 3). Tier stratification is documented in
prose — `docs/architecture/vi/00-overview.md` §5.2, PRD FR-TGT-08, and Q-13 — but frozen
schemas do not recognize the three new targets, and source code is unaware of tiers.

### 1a. Target List Is a Closed Enum in Two Schemas

`schemas/board.v1.json`, field `board.target`:

```json
"target": { "type": "string", "enum": ["sim", "linux", "esp32s3"] }
```

`schemas/trace.v1.json`, field `metadata.target`:

```json
"target": {
  "type": "string",
  "enum": ["sim", "linux", "esp32s3"]
}
```

Practical consequence: a `boards/jetson-orin-nano.toml` file valid in every other respect
is rejected, and all traces generated from that board fail validation. No configuration
flag can relax this — the enum is inside frozen files.

This list is also repeated in Python, `python/neuroedge/hal/board.py`:

```python
SUPPORTED_TARGETS: tuple[str, ...] = ("sim", "linux", "esp32s3")
```

and in the counterexample corpus `fixtures/traces/expected_errors.yaml`, where expected
error messages match the **literal string** generated directly from the enum:

```yaml
unknown_target.json:
  why_contains: "is not one of ['sim', 'linux', 'esp32s3']"
```

All three locations must change simultaneously, or tests fail. Furthermore, `schemas/`
and `fixtures/traces/` require a **mandatory RFC** under `CONTRIBUTING.md` §3.

### 1b. Target Tiers Exist Only in Prose

FR-TGT-08 requires *"Tiers are explicitly declared, not inferred"*, and the 100%
`verify` threshold only binds Tier 1. But not a single line of code knows whether `jetson`
is Tier 2 or `rp2350` is Tier 3. Consequence: no test can distinguish between "Tier 1
board missing `display`" (error) and "Tier 3 board missing `display`" (permitted).

### 1c. Three Tests Enforce a Fixed Board Set

`python/tests/test_boards.py` currently asserts three properties true for the three
reference boards, but written in ways that break immediately when the target list grows:

| Test | Assertion | How It Breaks When Targets Are Added |
|:---|:---|:---|
| `test_one_profile_exists_per_supported_target` | Profile set in `boards/` strictly equals `SUPPORTED_TARGETS` | Red immediately: `jetson`, `stm32`, `rp2350` have no profiles, while real profiles need hardware (§9.4) |
| `test_all_three_targets_share_the_same_named_pins` | Every profile declares the same named pin set | A Tier 3 board controlling industrial valves would have to declare a fake `porch_light` to pass |
| `test_every_profile_declares_all_five_primitives` | Every profile declares all five primitives | STM32 has no display; RP2350 has no hardware AEC |

---

## 2. Why the Current Schema Does Not Solve It

For `target`, the enum is closed in both schemas and in Python, consistently closed.
There is no path forward other than modifying the enum.

An additional related discrepancy, fixed at code level (§3c) rather than schema:
`capabilities` in `board.v1.json` lacks `additionalProperties: false`, so a mistyped
key like `vison_in` **passes validation**. `board.py::board_from_document()` preserves
all keys upon loading; `_normalise()` only rejects when a component **queries** that
primitive. Unknown keys are thus accepted silently.

---

## 3. Proposed Change

### 3a. Expand `target` Enum

`schemas/board.v1.json` and `schemas/trace.v1.json`, before:

```json
"enum": ["sim", "linux", "esp32s3"]
```

after:

```json
"enum": ["sim", "linux", "esp32s3", "jetson", "stm32", "rp2350"]
```

with `$comment` referencing RFC-0002 at both enum sites, following RFC-0001 precedent.

The enum **remains closed** — this is deliberate, see §6. What changes is the list,
not the nature of the constraint. The schema only answers "is this target name recognized";
it does not carry tiers.

### 3b. Machine-Readable Target Tiers Owned by Core

`python/neuroedge/hal/board.py`:

```python
# FR-TGT-08: committed tiers of the core team for each target. Core owns this table;
# board.toml does not self-declare tiers — a community port cannot self-claim tier 1.
TARGET_TIERS: dict[str, int] = {
    "sim": 1, "linux": 1, "esp32s3": 1,
    "jetson": 2,
    "stm32": 3, "rp2350": 3,
}
SUPPORTED_TARGETS: tuple[str, ...] = tuple(TARGET_TIERS)
```

Tier is a **property of the target**, not of individual boards, and represents the
**promise of the core team**. If placed in `board.toml`, a community board could declare
`tier = 1` and claim a quality guarantee the core team never provided. Therefore, the
acceptance criterion of FR-TGT-08 changes *"in `board.toml`"* to *"in the core code tier
table (`TARGET_TIERS`); `board.toml` does not self-declare tiers"* (§8).

### 3c. Accompanying Code (Not Schemas)

1. **Do not hard-code "five".** Messages in `board.py::_normalise()` and docstrings
   generate from the primitive list, without writing the literal word "five". The primitive
   set **remains five** in this RFC (FR-HAL-01 unchanged); this ensures future vision
   RFCs can add an element without updating prose in seven places.
2. **Reject unknown capability keys at load.** `board_from_document()` rejects keys
   outside the valid set with a three-part `BoardCapabilityError` (FR-HAL-05), suggesting
   the closest key (`vison_in` → `vision_in` when present; currently → list of five keys).
   Implemented in code rather than closing `capabilities` in schema, as closing is a
   tightening (§6).
3. **Unknown target error provides guidance.** When the schema rejects `board.target`,
   the `how` section lists recognized targets by tier and references this RFC.
4. **CLI.** `neuroedge board show` iterates over the primitive list rather than a fixed
   tuple of five names in `cli/main.py`. A new command `neuroedge board validate <path>`
   loads any TOML file and prints target, tier, and present/missing primitives. All
   `--target` / `--targets` flags (`verify`, `run`, `build`, `record`, `replay`) validate
   names against `SUPPORTED_TARGETS` via a shared helper; currently `verify --targets esp32s2`
   exits 0 silently.

---

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | **Yes** for schemas — no exceptions. Schema changes in §3a are pure relaxations. Separately, the Python loader (§3c.2) rejects unknown capability keys that the schema accepts; no files in the repository contain unknown keys |
| Do currently invalid files become valid? | **Yes** — `board.toml` and traces declaring Tier 2/3 targets |
| Forward compatibility | **None.** Older `neuroedge` tools will reject `board.toml` and traces declaring `jetson`, `stm32`, `rp2350`, with clear enum errors. No traces outside the repository depend on new targets |
| Is a schema version bump required (`v1` → `v2`)? | **No** — see reasoning below |
| Impact on hashes / digital signatures of published gates? | **None** — this RFC does not touch `gate.v1`. Gate hashes are computed over gate documents, unrelated to targets |
| Impact on the three canonical trace files? | **None** — all three declare `target: "esp32s3"`, remaining within the expanded enum and validating intact |

### Reconciling with RFC-0001's `v2` Declaration

RFC-0001 §4 states:

> After Sprint 1 closes, any change of this nature must go to `gate.v2`.

This statement **does not apply to RFC-0002**, for two independent reasons, each
sufficient on its own:

1. **Different scope.** That statement addresses `gate.v2` and sits inside an RFC modifying
   only `gate.v1`. "Changes of this nature" refers to the two **tightening** cases in
   RFC-0001 items 3c and 3d — changes causing valid documents to become invalid. RFC-0002
   contains no schema tightening cases.
2. **Different nature.** The foundational rule in `0000-template.md` draws a clear
   distinction: breaking changes require a version bump; *"relaxations (a currently invalid
   file becomes valid) **can be made within the same version**"*. §3a is a pure relaxation.

In other words: RFC-0001 had to invoke "Sprint 1 has not closed" as an exception because
it **contained** tightening. RFC-0002 requires no exception.

A corollary of that reasoning: being a relaxation, this change **can be introduced at
any time** in `v1` without breaking any documents. There is no "rewrite cost" forcing early
adoption — which is why §8 permits deferring to I11 (PRD Q-40).

Noted for transparency: should the committee still prefer `board.v2`/`trace.v2`, the cost
is two new schema files, two new `$id`s, and a migration script for existing traces — while
technical benefit is zero, as no documents are broken. We recommend retaining `v1`.

---

## 5. Safety Impact

**Does this change make gates more lax: no.** RFC-0002 does not touch `gate.v1`, does
not touch the five principles of inheritance (Appendix B.5), does not touch the fail-closed
default, and does not touch `gate_resolver.py`. The gate engine is unaware of which
target is executing.

The focus of scrutiny is the **three test invariants** in §1c. General principle:
**narrow scope by tier, do not drop assertions.** The alternative gate invoked by the
first RFC draft — checking `[requires]` in `agent.toml` against board capabilities at
build (FR-HAL-04) — **does not yet exist**: `neuroedge build` remains a stub (`cli/main.py`,
TSK-S2-02), no parser exists for `agent.toml`, and `missing_primitives()` has no callers
outside tests. Dropping invariants before that gate exists leaves an unguarded void.

> **Update 2026-09-24 — premise changed.** That gate now exists: `neuroedge build` checks
> `[requires]` in `agent.toml` against the board (TSK-S2-02, `engine/compiler.py`). The prose
> above is preserved to document review reasoning; before approving this RFC, re-evaluate
> §5a–§5c against the existing gate rather than a "non-existent gate".

### 5a. Common Named Pin Set

| | |
|:---|:---|
| **Why this invariant exists** | Cheapest way to guarantee the same agent runs across targets without branching — principle P-2 (PRD §1.5), KL-2 of `docs/spec/hal_mcu_review.md` |
| **Why the current form is no longer valid** | It mistakes the *named pin set of one use case class* (villa door lock) for a *global contract*. Forcing an STM32 board to declare a fake `porch_light` to pass tests is **worse** for safety |
| **Changed to** | Assertion retained, **applied to Tier 1 boards**. Agent-level invariants (*every board targeted by an agent must declare all pins required by the agent*) will only substitute in when TSK-S2-02 lands with its own tests — not earlier |

### 5b. All Five Primitives Present

| | |
|:---|:---|
| **Why this invariant exists** | For the three reference boards chosen by the core team, it catches forgotten declarations |
| **Why the current form is no longer valid** | It turns *capability* into *obligation* across all tiers. Forcing small boards to declare all five means faking capabilities or permanent disqualification |
| **Changed to** | Tier 1 must still declare **all five**. Tier 2/3: primitives are declared as yes/no. Tier 2/3 boards have no way to run agents before TSK-S2-02, because `build` and `run` are still stubs, so there is no unguarded execution gap |

### 5c. One Profile per Target

`test_one_profile_exists_per_supported_target` splits into two assertions: **each
Tier 1 target has exactly one profile** in `boards/`, and **every profile** has a target
within `SUPPORTED_TARGETS`. `boards/` still contains only Tier 1 profiles until real
hardware is available (§9.4).

### 5d. Real Risk of This RFC

Does not lie in schemas, but in **commitments**. A six-target enum creates the impression
that the core team guarantees quality for all six. That is not the case:

- **Tier 1** (`sim`, `linux`, `esp32s3`): `neuroedge verify` 100%, nightly hardware, maintained by core team.
- **Tier 2** (`jetson`): maintained by core team, verify on verdict domain.
- **Tier 3** (`stm32`, `rp2350`): community ports, verified via Conformance Test Suite
  (`docs/architecture/vi/16-ecosystem-landscape.md` §6 pillar 2). **No core team commitment.**

This stratification **has been recorded** in `docs/architecture/vi/00-overview.md` §5.2
and PRD FR-TGT-08 (commit `eddfc59`), satisfying the "docs first, schema second" rule.
`TARGET_TIERS` (§3b) brings that exact table into code.

---

## 6. Alternatives Considered and Rejected

| Alternative | Reason for Rejection |
|:---|:---|
| Create `board.v2` and `trace.v2` | Unnecessary breaking change. No currently valid documents break (§4), so migration costs yield zero technical benefit |
| Drop `target` enum, use `"type": "string"` | Loses typo gate. A trace declaring `target: "esp32s2"` would pass silently. Counterexample corpus `unknown_target.json` loses meaning |
| Use `pattern` instead of `enum` (e.g. `^[a-z0-9]+$`) | Same issue as above, varying only in degree |
| Declare tier in `board.toml` (`board.tier` field in schema) | Tiers are the core team's promises regarding a target, not self-declared board attributes. Storing in board files lets community ports self-claim Tier 1; preventing this requires reconciling with a core table, meaning two copies must match |
| Close `capabilities` with `additionalProperties: false` | Is a tightening — currently valid files could become invalid — requiring `board.v2`. Checking unknown keys in the loader (§3c.2) achieves the same goal |
| Relax the two agent invariants in this RFC immediately | The build gate on which new invariants rely does not yet exist (§5) |
| Keep `vision.in` and `vision_ref` in this RFC | Freezing camera parameter contracts before having a single camera, vision agent, or `[requires]` reconciler; every subsequent fix (`fps` type, adding `required`) is a tightening requiring `board.v2`. Since expanding the enum is a relaxation feasible at any time, separating costs nothing. See §9.1–9.2 |

---

## 7. Verification Evidence

*This entire section belongs to the **second pull request**, after the RFC is approved.
Deliberately left blank per `docs/rfc/README.md` steps 2 and 4.*

- [ ] Do **not** add any profiles to `boards/`. Tier 2/3 profiles used as evidence are synthesized in `tmp_path` / in-memory in tests; same for traces declaring `target: "jetson"`
- [ ] Corpus: keep `unknown_target.json` with `rp2040` — a realistic typo close to `rp2350`, still outside the new enum. Only modify `why_contains` in `expected_errors.yaml`
- [ ] Automated tests: `test_target_lists_agree` (enum `board.v1` == enum `trace.v1` == `SUPPORTED_TARGETS`), `test_target_tiers_are_declared` (keys of `TARGET_TIERS` == `SUPPORTED_TARGETS`, Tier 1 == `{sim, linux, esp32s3}`), `test_board_schema_enumerates_the_supported_targets` (replacing `…_exactly_the_three_targets`), three tier-based invariants in §5, unknown capability key test, CLI tests for `board validate`, `board show`, and `--target` name validation
- [ ] `cd python && .venv/bin/python -m pytest -q` green, **0 skipped**; `ls boards/` remains exactly three files
- [ ] `neuroedge verify` remains green on Tier 1 targets

---

## 8. Tasks upon Approval

**Timing:** second pull request merges in increment **I11**, after Developer Beta
(PRD Q-40; prior decision in `docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md` deferred it
to Phase 2 to avoid adding work to the v1.0 critical path). Sole exception: earlier if a
**real** Tier 2/3 profile is actively being written.

**Order: documentation first, code second.**

Completed prior to this RFC (commit `eddfc59`):

- [x] Three-tier stratification in `docs/architecture/vi/00-overview.md` §5.2
- [x] FR-TGT-08 in `neuroedge-prd.md` §4.2; Q-13
- [x] Proposal KPI: 100% `verify` threshold applies only to Tier 1

Documentation (same pull request as this RFC):

- [x] Reword FR-TGT-08 acceptance criteria: tier resides in core code `TARGET_TIERS`, `board.toml` does not self-declare tier
- [x] `docs/architecture/vi/15-target-architecture.md` §4.4 Block V1a: remove `vision_in` and `vision_ref` from tasks and exit criteria; move to V1b
- [x] `CONTRIBUTING.md`: Tier 2/3 profiles require physical hardware

Second pull request:

- [ ] `schemas/board.v1.json`, `schemas/trace.v1.json`: `target` enum + `$comment` RFC-0002
- [ ] `python/neuroedge/hal/board.py`: `TARGET_TIERS`, `SUPPORTED_TARGETS`, drop hard-coded "five", validate unknown capability keys at load, `how` for unknown targets; export `TARGET_TIERS` via `hal/__init__.py`
- [ ] `python/neuroedge/cli/main.py`: `board show` iterates over primitive list, `board validate <path>`, shared target name validation helper
- [ ] `fixtures/traces/expected_errors.yaml`: `why_contains` for `unknown_target.json`
- [ ] `python/tests/test_boards.py`, `test_schemas.py`, `test_cli.py`: per §5 and §7
- [ ] `CHANGELOG.md`: record RFC-0002

---

## 9. Open Tasks

Items intentionally left out of this RFC's scope, with activation triggers, so that
no one needs to re-derive them:

1. **Vision primitive `vision.in`** — a separate RFC, opened in **Block V1b**, once
   three conditions are met: V1b is activated (≥ 2 AURA customers state specific camera
   needs), a board with a camera is on the bench, and the build-time `[requires]`
   reconciler (TSK-S2-02) exists — this condition was satisfied on 2026-09-23. Known inputs
   for that RFC:
   - `sensor.read` cannot express frame streams (returns discrete scalars).
   - Initial draft shape (`width`, `height`, integer `fps`, free-form string `pixel_format`
     and `accelerator`) was insufficient: `fps` must be `number` (7.5, 29.97); sensors have
     multiple modes requiring `modes[]`; `pixel_format` requires an enum for reconciliation;
     and matching rules against agent `[requires]` must be specified **before** finalizing.
   - Primitive is **optional per board**, firmware capability table remains a static array
     (KL-1, RB-4); SRAM budget measured on physical hardware (Q-3).
   - The invariant "`sim` is no richer than reference boards" must be restated per
     reference board, otherwise vision agents cannot run on `sim` (`TODOS.md` #14).
2. **Visual evidence in traces** — **no schema RFC required**: `events[].data` is already
   free-form and `metadata` is open. Implemented when the **first vision trace** arrives:
   - Vision results (labels, bounding boxes, confidence, model ID) enter events in the
     `perception` group of Appendix C.1 — this is what `replay` uses to reproduce verdicts
     (FR-CI-02). A frame hash cannot be replayed.
   - Frames leave only identity: `vision_ref` comprises `sha256` and size, without
     embedding raw images (NFR-PRIV-01, NFR-PRIV-03); recorded only for frames leading
     to a decision, not every frame (30 fps ≈ 13 MB/hour of traces).
   - Semantic lint in `trace.py`: `sha256` matches `^[0-9a-f]{64}$`; `uri` permitted
     only when `metadata.raw_capture == true`; reject base64 blobs in `data`. Accompanied
     by counterexample fixtures in `fixtures/traces/invalid/` and corresponding entries
     in `expected_errors.yaml` — regular PR (`CONTRIBUTING.md` §3 only requires an RFC
     for the three canonical traces).
3. **Gate semantics for visual evidence** — distinct problem, touching `gate.v1`,
   requiring lead architect approval, belonging to **a dedicated RFC (number assigned
   upon opening)**; the next two RFC numbers are reserved for two `gate.v1` changes in
   the Phase 1 design doc. **Until that RFC exists, vision may only be used as
   informational input, not as direct basis for actuator verdicts.**
4. **Physical hardware profiles for Tier 2/3** — `boards/jetson-orin-nano.toml`,
   `boards/stm32-*.toml`, `boards/rp2350-*.toml` require real hardware to determine
   accurate parameters. Dependent on procurement schedule; outside the second pull request.

---

## 10. Approval (Q-67, 2026-10-04)

Lead architect signed this RFC as decision 4 of **Q-67** (open platform, `neuroedge-prd.md` §15).
Things changed since writing:

1. **Implementation pulled forward to I2c.** The second pull request no longer waits
   until after Developer Beta: it is TSK-V1a-02 → V1a-06 in increment **I2c — Open platform**
   (`neuroedge-roadmap.md` §4.3.3). Reason: community boards loaded from path (`--board <path>`,
   RFC-0016) need machine-readable target tiers in core code.
2. **"Three Tier 1 profiles" is now "reference boards".** RFC-0013 gives each Tier 1 target
   multiple reference boards (`REFERENCE_BOARDS`, `SIM_MIRRORS`); references to "three profiles"
   or "one profile per target" in this RFC should be read per RFC-0013. `boards/` still only
   contains reference boards.
3. **Out-of-tree boards.** A profile loaded from path or plugin is never a reference board
   and never counted toward Tier 1 equivalence by `verify`; its tier is the tier of its
   declared target, per `TARGET_TIERS` of §3b. That rule lives in RFC-0016; this RFC is
   unchanged.
4. **Unchanged:** enum remains closed (§6); `board.toml` does not self-declare tier (§3b);
   Tier 2 commitment for `jetson` remains in I16; real hardware profiles for Tiers 2 and 3
   still require physical boards (§9.4).

## Review Record

Review minutes from 2026-09-23 (Review record, Decision Audit Trail, GSTACK REVIEW REPORT) moved to `docs/archive/rfc-0002-review-record.md` (deleted; `git show 7626b62:docs/archive/rfc-0002-review-record.md`).
