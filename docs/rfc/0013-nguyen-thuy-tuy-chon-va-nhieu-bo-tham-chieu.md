# RFC-0013: Board-Optional Extension Primitives and Multiple Reference Boards per Target

| | |
|:---|:---|
| **RFC ID** | 0013 |
| **Title** | Extension primitives are optional per board; multiple tier-1 reference boards per target; each `sim` profile mirrors exactly one reference board |
| **Affected Contract** | *(not in `schemas/`)* — primitive sets, reference board tables, and test invariants in `python/neuroedge/hal/board.py`, `python/tests/test_boards.py`; board selection in `neuroedge build` and `neuroedge verify` (`python/neuroedge/cli/main.py`) |
| **Related PRD Requirements** | FR-HAL-01, FR-HAL-04, FR-HAL-05, FR-HAL-08, FR-TGT-01, FR-TGT-06, FR-TGT-08 |
| **Author** | — |
| **Date Opened** | 2026-09-30 |
| **Status** | ✅ Approved (2026-10-01) — lead architect signed on PR #80; amended per review 2026-10-01 (§9, Q-62); implemented in second PR |
| **Approver** | **Lead Architect — mandatory** (modifies test invariants protecting target equivalence, RFC-0002 §5) |

> **When an RFC is required:** This RFC does not modify `schemas/`, but changes three invariants proposed by RFC-0002 §5a–§5c
> following review; changing them silently is precisely what RFC-0002 §5 warned against. This RFC is approved **prior to** RFC-0002 (§9 item 6).
> Tasks: TSK-I2a-06, TSK-I2a-07, TSK-I3a-01.
> Foundation decisions: `neuroedge-prd.md` §15 Q-52, **Q-53** (four primitive packs mandatory across all three tier-1 targets;
> ESP32-S3 board with camera; `sim-rpi5`; `analog.in` moved to RFC-0007), Q-54, Q-55, **Q-57** (§9).
> Dependencies: [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md), [RFC-0010](0010-pwm-trong-digital-out.md),
> [RFC-0011](0011-nguyen-thuy-motion.md), [RFC-0012](0012-nguyen-thuy-vision-in.md).

## 1. Problem

The previous four RFCs add new primitives (`digital.in`, I2C, `analog.in`, PWM, `motion.*`, `vision.in`). Three things in existing code and tests block this:

### 1a. Primitive Set Is Five, Mandatory for All Boards

`python/neuroedge/hal/board.py`:

```python
PRIMITIVES: tuple[str, ...] = ("audio.in", "audio.out", "digital.out", "sensor.read", "display")
```

`python/tests/test_boards.py::test_every_profile_declares_all_five_primitives` forces all profiles to declare all five. If six new primitives enter `PRIMITIVES`, every board must declare both cameras and motors — untrue to physical hardware.

### 1b. Exactly One Reference Board per Target

`REFERENCE_BOARD = {"sim": "sim-default", "linux": "linux-rpi5", "esp32s3": "esp32s3-box-3"}` (`board.py`), used as default in `cli/main.py` and `sim/session.py`. `test_reference_board_is_the_box_3_not_a_devkit` pins `esp32s3` to Box-3, and RFC-0002 §5c proposes "each tier-1 target has **exactly one** profile". But **Box-3 lacks an onboard camera**, while Q-53 demands `vision.in` present on `esp32s3`. With exactly one board per target, `esp32s3` only gains a camera if Box-3 itself carries one.

### 1c. `sim` Must Mirror Exactly One Board

`sim-default` mirrors Box-3 (annotated in `boards/sim-default.toml`); `test_sim_offers_no_pin_the_reference_board_lacks` and `…_sensor_…` verify this relation. `TODOS.md` #14 noted: `sim-default` must not declare a camera because Box-3 lacks one, preventing vision agents from running on `sim` — the frame Action CI has no `sim` path.

## 2. Why the Current Structure Does Not Solve It

- `board.v1.json` already treats all capability keys as optional (only `board` and `capabilities` are required); the "declare all five" requirement lives **entirely in code and tests**, so it can be changed without schema modifications.
- `REFERENCE_BOARD` is a 1-to-1 mapping `target → id`; cannot express two reference boards.
- No table specifies which board a `sim-*` mirrors; the relation is hardcoded into test names.
- The coverage rule (each extension primitive must exist across all three targets) is not enforced anywhere, allowing Q-53 to be silently violated.
- `neuroedge verify` and nightly only recognize one board per target, so a second reference board would never be replayed.

## 3. Proposed Change

### 3a. Core and Extension Primitives

```python
PRIMITIVES = ("audio.in", "audio.out", "digital.out", "sensor.read", "display")   # core
EXTENSION_PRIMITIVES = ("digital.in", "i2c", "analog.in", "motion", "vision.in")  # optional (PWM is block in digital.out)
ALL_PRIMITIVES = PRIMITIVES + EXTENSION_PRIMITIVES
```

- **Five core primitives mandatory for all tier-1 reference boards outside `EXTENSION_REFERENCE_BOARDS`** (§3b), and always mandatory for each target's default board. Tier 2/3: optional, per RFC-0002.
- Extension primitives are **optional per board**; `BoardProfile.supports()` / `missing_primitives()` accept both sets; `_normalise()` messages generated dynamically from list, not hardcoding "five" (RFC-0002 §3c.1).
- Mistyped extension keys rejected at load time (RFC-0002 §3c.2), now checked against `ALL_PRIMITIVES`.
- Reference boards carrying `vision.in` (`linux-rpi5`, `esp32s3-cores3`, `sim-rpi5`) must declare inference tolerance `tolerance = { score_abs, box_iou_min }` in `capabilities.vision_in` (RFC-0012).
- **Never declare capabilities hardware lacks**, core or extension: boards lacking hardware omit keys, never declaring dummies to pass tests (§9 item 1).

### 3b. Multiple Reference Boards per Target

```python
REFERENCE_BOARDS: dict[str, tuple[str, ...]] = {
    "sim":     ("sim-default", "sim-rpi5"),
    "linux":   ("linux-rpi5",),
    "esp32s3": ("esp32s3-box-3", "esp32s3-cores3"),  # option (a) per Q-61; fallbacks: (b) or (c)
}
EXTENSION_REFERENCE_BOARDS: frozenset[str] = frozenset()  # non-empty only if camera board takes option (c)
```

The first element is the **default** when `--board` is omitted (preserves current behavior of `cli/main.py`, `sim/session.py`); Box-3 remains the default for `esp32s3`. The legacy `REFERENCE_BOARD` is preserved as an alias for the first element to avoid breaking callers. `EXTENSION_REFERENCE_BOARDS` is a core table, not declared in `board.toml`, for the same reason as `SIM_MIRRORS` (§3d).

**Camera Board Selection** (TSK-I3a-01, §9 item 1): **M5Stack CoreS3** (`esp32s3-cores3`) selected per Q-61 (2026-10-01), satisfying option (a). Options (b) and (c) retained as fallback rules if Q-3 measurements fail on CoreS3:

| Option | Condition | Consequence |
|:---|:---|:---|
| (a) | An ESP32-S3 camera board declares **all five core primitives** and common pin set (RFC-0002 §5a); **M5Stack CoreS3 selected** (Q-61) | Full second reference board for `esp32s3`, listed after Box-3 |
| (b) | Fallback: option (a) unavailable; camera module attached to Box-3 while meeting Q-3 memory budget | `esp32s3` retains one board; Box-3 with module declares `vision_in` |
| (c) | Fallback: neither (a) nor (b) available | **Extension reference board**: id added to `EXTENSION_REFERENCE_BOARDS`, declares only what hardware has, **never** the first element of target |

**Replaces RFC-0002 §5c:** "each tier-1 target has **at least one** reference profile, and all profiles have targets in `SUPPORTED_TARGETS`". **Replaces §5b:** core primitives mandatory for all tier-1 reference boards outside `EXTENSION_REFERENCE_BOARDS` and for default boards; extension primitives declared only when physical board has them. **§5a** (common named pin set) applies to that same board set. Since this RFC is approved first, RFC-0002 §5b/§5c links to this RFC rather than restating it (§9 item 6).

### 3c. Coverage Rule (Q-53)

**Each extension primitive must exist on at least one tier-1 reference board of EACH tier-1 target** (`sim`, `linux`, `esp32s3`). Test `test_every_extension_primitive_on_every_tier1_target` iterates `REFERENCE_BOARDS` and `available_boards()`; missing on any target ⇒ red, suggesting board to add.

The table of boards providing each primitive is §9 item 5; **each cell is an individual assertion** in coverage tests (the board in the cell declares that primitive), not merely "exists somewhere on target". If physical hardware prevents a cell ⇒ open `Q-N` and slip schedule, do not drop cell (Q-52). Cell `motion.*` × `esp32s3` follows RFC-0011 §9 item 6, including its fallback (camera board carries it if Box-3 dock lacks pins); changing a cell's board requires amending §9 item 5 via `Q-N`, not silent test edits.

### 3d. Each `sim` Profile Mirrors Exactly One Reference Board

Add `boards/sim-rpi5.toml` mirroring `linux-rpi5` (including camera when `linux-rpi5` has one), just as `sim-default` mirrors Box-3. The mirroring relation is **a table in core code**, not a field in `board.toml`: a profile cannot self-declare which board it mirrors (same rationale as `TARGET_TIERS`, RFC-0002 §3b; §9 item 4). The loader rejects profiles declaring `mirrors`.

```python
SIM_MIRRORS = {"sim-default": "esp32s3-box-3", "sim-rpi5": "linux-rpi5"}
```

The invariant **"`sim` is no richer than reference board"** (`TODOS.md` #14) is reformulated **pair-wise**: for each `sim-*`, primitive set, pins, sensors, and camera modes ⊆ those of the board it mirrors. Two existing tests (`test_sim_offers_no_pin…`, `…_sensor…`) become parameterized over `SIM_MIRRORS`. Not all reference boards have a mirroring `sim-*`: the `esp32s3` camera board has none; `vision.in` on `sim` lives only on `sim-rpi5` (§9 item 5). Vision agents run on `sim-rpi5`; frame Action CI gains a `sim` path (TSK-V1b-02). `TODOS.md` #14 closes when the reference camera board and `sim-rpi5` land.

### 3e. Board Selection at Build Time

`neuroedge build` matches `[requires]` against boards (FR-HAL-04), rules in §9 item 3:

- With `--board`: use that exact board.
- Without `--board`: use default board if it satisfies `[requires]`. If not ⇒ `BoardCapabilityError` (NE3001, wrapped in `BuildFailed` NE3003), exit code 1, no artifact written; three-part message (FR-HAL-05) states missing capability, what default board provides, and **lists target reference boards satisfying `[requires]`** (suggesting `--board <id>`), or clearly states none satisfy.
- **Never auto-select another board**: users must know exactly which board they are flashing.

### 3f. `verify` and Nightly Run All Reference Boards

Rules in §9 item 2 and item 7: equivalence only has meaning when run on the exact board delivered to users.

- `neuroedge verify --targets <t,…>` replays traces across **every** board in `REFERENCE_BOARDS[t]`, not just the first element, reporting results per (target, board) pair.
- **Trace replay set per board capability (§9 item 7):** Each board replays only canonical traces whose primitives it fully declares, plus the dedicated corpus for extension primitives it carries. The default board of each target must replay all three canonical traces. A board with zero applicable traces ⇒ failure, exit code 1, `VerificationError` (NE4004) — following the "zero scans is never a pass" principle. With the current selection of M5Stack CoreS3 (all five core primitives per option (a)), `esp32s3-cores3` replays all three canonical traces plus its dedicated vision corpus.
- `sim`, `linux`: host loops through boards. `esp32s3`: each reference board requires its own replay session (`--port` per board; device declares `board_id`, `testing/uart.py`). Missing replay session for a board ⇒ failure, exit code 1, `VerificationError` (NE4004); no board skipped silently.
- Nightly hardware (`.github/workflows/nightly-hardware.yml`) includes one job per physical reference board; tests check job matrix against `REFERENCE_BOARDS`.

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | Yes — `schemas/` unchanged; three tier-1 profiles in `boards/` must add `[capabilities.digital_out.envelope.<name>]` envelopes in implementation PR, with values wide enough for canonical traces to replay unchanged (no external profiles yet). Adds `esp32s3-cores3` and `sim-rpi5` profiles, no keys removed |
| Do currently invalid files become valid? | Yes, at loader level: previously silently tolerated extension keys are now valid keys; second profile per target accepted by `test_boards.py`. Conversely, profiles declaring `mirrors` rejected by loader (§3d) |
| Does schema version need bumping (`v1` → `v2`)? | No |
| Impact on published gate hashes / signatures? | None |
| Impact on three canonical trace files? | Files unchanged — all three still declare `target: "esp32s3"`, `board_id: "esp32s3-box-3"`. Each reference board replays only canonical traces whose primitives it fully declares (§3f, §9 item 7); default board of each target replays all three; `esp32s3-cores3` declares all five core primitives so replays all three canonical traces. Profiles must have envelopes wide enough for all three traces to replay identically |
| Which gates in `digests.lock` change digest? | None |
| Must `NETR` layout or C walker change? | No |
| Do any answers in tool call corpus (`expected_results.yaml`) change? | No |
| Error codes (`neuroedge-prd.md` Appendix B) | No new classes or codes added: `BoardCapabilityError` (NE3001), `BuildFailed` (NE3003), `VerificationError` (NE4004) already exist. On approval: row NE3001 adds behavior "no `--board` and default board unsatisfied ⇒ list satisfying reference boards" (§3e); row NE4004 adds cause "a reference board of requested target lacks replay session or has no applicable traces" (§3f, §9 item 7) |

CLI behavior: `build` without `--board` unchanged when default board satisfies, still exit 1 when unsatisfied — message adds board list; `verify` runs additional boards so runs slower and may fail on new boards — that is intentional.

Tests needing edits: `test_one_profile_exists_per_supported_target` (→ "at least one per tier-1 target"), `test_all_three_targets_share_the_same_named_pins` and `test_every_profile_declares_all_five_primitives` (→ all tier-1 reference boards outside `EXTENSION_REFERENCE_BOARDS`, and all default boards), `test_reference_board_is_the_box_3_not_a_devkit` (kept, applied to first element of `esp32s3`). Legacy `REFERENCE_BOARD` retained so `cli/main.py` and `sim/session.py` do not break.

## 5. Safety Impact

This RFC does not touch `gate.v1`, resolution, five inheritance principles, or fail-closed semantics. Risks lie in **test invariants** and **board selection**:

- **No assertions dropped, only scope updated**: core primitives and common pin sets remain mandatory for all full tier-1 reference boards and always for default boards; "sim no richer than board" is **stricter** (pairwise instead of single profile). The sole exception is extension reference boards (§3b option (c)), which are never default boards.
- **Replacement gate already exists:** `neuroedge build` matches `[requires]` against boards (TSK-S2-02, `engine/compiler.py`), so agents requiring `vision.in` are rejected on boards lacking it — leaves no unguarded gap.
- **Doubled test matrix — accepted:** `verify` and nightly run all reference boards (§3f), because vision agents passing on `sim-rpi5` prove nothing on `esp32s3` camera board (`esp32s3-cores3`). Cost: CI time and self-hosted runner per hardware board.
- **Replay by capability (§3f, §9 item 7):** Extension boards replay only traces whose primitives they support, avoiding forcing runs on boards missing required primitives; default boards must replay all three canonical traces. Zero replayed traces is a fail-closed violation and rejected.
- **No silent board selection:** `build` never auto-switches boards (§3e).
- **`sim` richer than reference board is safety fault:** agent passes simulation but cannot build on hardware. Pairwise testing is the enforcement gate.
- **Declaring absent capabilities is safety fault:** failing coverage tests require opening `Q-N` and slipping dates (§3c), not declaring dummies.
- Requires lead architect approval because RFC-0002 §5 requires signatures to alter these invariants.

## 6. Alternatives Considered and Rejected

| Alternative | Reason for Rejection |
|:---|:---|
| Moving all new primitives into mandatory `PRIMITIVES` | Forces boards to fake capabilities; RFC-0002 §5b pointed out same for tier 2/3 |
| Attaching camera to Box-3 as first choice | Box-3 is the board with measured memory budget (Q-1, Q-2, Q-3); adding camera could invalidate spike measurements. Kept only as fallback option (b) in §3b, if Q-3 budget holds |
| Camera board lacking core primitives as default `esp32s3` board | Voice agents without `--board` fail to build; five core primitives rule applies to default boards (§9 item 1) |
| Camera only on `linux` | Q-53 requires all extension primitives across all three targets |
| `sim` declaring camera without mirroring a board | Violates "sim no richer than board" invariant — exactly `TODOS.md` #14 |
| Declaring `mirrors` in `board.toml` | Allows any profile, even community boards, to self-declare what it mirrors; core `SIM_MIRRORS` table (§9 item 4) |
| `verify` and nightly running default board only | Agent passing on default board proves nothing on other reference board of same target (§9 item 2) |
| `build` without `--board` auto-selecting satisfying reference board | Users do not know which board they are targeting (§9 item 3) |

## 7. Verification Evidence

- [ ] `boards/sim-rpi5.toml` and `boards/esp32s3-cores3.toml` (TSK-I3a-01, Q-61) valid under `board.v1`; declare valid `tolerance` for `vision_in` (RFC-0012) and envelopes for `digital_out`, parameters sourced from real hardware (`CONTRIBUTING.md` §3); fallback option (b) with Q-3 budget report in `docs/reports/`
- [x] Board table tests (§3a, §3b): all five core primitives and common pin set on all tier-1 reference boards outside `EXTENSION_REFERENCE_BOARDS`; first element of all `REFERENCE_BOARDS[t]` declares all five core primitives and not in `EXTENSION_REFERENCE_BOARDS`; all IDs in both tables have profiles in `boards/` with matching target; unknown extension keys rejected at load time; boards carrying `vision.in` lacking `tolerance` rejected at load time — *met: `test_boards.py` (`test_the_reference_tables_name_real_profiles_of_the_right_target`, `test_every_full_reference_board_declares_all_five_core_primitives`, …) and `fixtures/boards/invalid/` (`capability_key_*`, `vision_tolerance_missing`); first element and empty `EXTENSION_REFERENCE_BOARDS` verified*
- [ ] Coverage tests (§3c): `test_every_extension_primitive_on_every_tier1_target`, and **each cell** of §9 item 5 (board in cell declares that primitive); negative test: removing key from cell board ⇒ red with suggestion
- [x] Mirroring tests (§3d, §9 item 5): `sim-*` ⊆ mirrored board (parameterized over `SIM_MIRRORS`); all `sim-*` in `boards/` have entries in `SIM_MIRRORS` and vice versa; profile declaring `mirrors` rejected at load time; `sim-default` does not carry `motion.*` if `esp32s3-box-3` does not; negative test: `sim` profile declaring `vision_in` when mirrored board lacks it ⇒ red — *met: `test_a_sim_profile_is_never_richer_than_the_board_it_mirrors` (parameterized over `SIM_MIRRORS`), `test_every_sim_profile_has_a_mirror_and_back`, `mirrors_*` in `fixtures/boards/invalid/`, negative test `test_the_mirror_invariant_is_red_when_a_sim_profile_is_richer`*
- [x] Build tests (§3e): without `--board`, default board satisfies ⇒ build on default board; unsatisfied ⇒ exit 1, `BoardCapabilityError` lists satisfying reference boards, no artifact written, no build on other board; `--board <id>` ⇒ uses that exact board — *met: `tests/test_compiler.py` (`test_without_a_board_the_default_is_checked_and_the_ones_that_fit_are_named`, `test_the_hint_never_builds_on_the_board_it_names`, `test_when_no_reference_board_fits_the_build_says_so`)*
- [ ] Verify tests (§3f, §9 item 7): `verify` checks each board replays only traces whose primitives the board fully declares; default board of each target replays all three canonical traces; `esp32s3-cores3` replays all three canonical traces plus vision corpus; negative test: a reference board with no applicable traces ⇒ red, exit 1 (`VerificationError`, NE4004); missing replay session for a physical reference board ⇒ exit 1
- [ ] `cd python && .venv/bin/python -m pytest -q` green, 0 skipped; `neuroedge verify --targets sim,linux,esp32s3` green across all tier-1 reference boards, in CI and nightly (A10)

## 8. Post-Approval Tasks

- [ ] Order (§9 item 6): approve this RFC before RFC-0002; notes in RFC-0002 §5b/§5c reference this RFC, and when RFC-0002 is approved, its §5b/§5c references this RFC instead of restating
- [ ] Update invariants in `CHANGELOG.md` §3.3: #6 becomes "default reference board of `esp32s3` is ESP32-S3-BOX-3; second reference board (with camera) is M5Stack CoreS3 (Q-61); do not change to DevKitC — spike measurements become meaningless"; #7 becomes "each `sim` profile is no richer in capabilities than board it mirrors (`SIM_MIRRORS`)"
- [ ] `python/neuroedge/hal/board.py` (`EXTENSION_PRIMITIVES`, `REFERENCE_BOARDS`, `EXTENSION_REFERENCE_BOARDS`, `SIM_MIRRORS`), `python/neuroedge/hal/__init__.py`, `python/neuroedge/cli/main.py` (`build` §3e, `verify` §3f), `python/neuroedge/sim/session.py`
- [ ] `.github/workflows/nightly-hardware.yml`: one job per physical reference board
- [ ] Add `boards/sim-rpi5.toml` and `boards/esp32s3-cores3.toml` (TSK-I3a-01, Q-61); update `python/tests/test_boards.py`; add `envelope` blocks for `digital_out` pins of three tier-1 profiles
- [x] `neuroedge-prd.md` FR-HAL-01, FR-TGT-08, Appendix B rows NE3001 and NE4004 (§4); `neuroedge-roadmap.md` (TSK-I2a-06, TSK-I2a-07, TSK-I3a-01); close `TODOS.md` #14 *(Completed 2026-10-04: PRD at commit `b2338a6`; roadmap TSK-I2a-06 ✅, TSK-I2a-07 🟡, TSK-I3a-01 🟡; `TODOS.md` #14 deleted)*
- [x] `CONTRIBUTING.md` §3 (board profile row); update `docs/rfc/README.md` and `CHANGELOG.md` *(Completed: `CONTRIBUTING.md` §3 at `b2338a6`, `CHANGELOG.md` `[Unreleased]` section 2026-10-04)*

## 9. Decisions on Open Questions (Q-57, 2026-09-30; Q-62, 2026-10-01)

Product owner delegated decision on open questions under the **maximum safety** principle: between two alternatives, choose the one that is fail-closed and harder to misuse, even if it requires more effort. The decisions below have been **incorporated into §3–§8**; this section is preserved as a decision log (Q-57) — if §3–§8 conflict with this section, fix §3–§8. RFC approval still requires lead architect signature (`CONTRIBUTING.md` §3).

1. **Camera Board.** TSK-I3a-01 selects **M5Stack CoreS3** (Q-61, 2026-10-01) — satisfying (a). Board includes ESP32-S3, 16 MB flash, 8 MB PSRAM, 0.3 MP GC0308 camera (VGA), 2 mics via ES7210, 1 W speaker via AW88298 amplifier, 2" 320×240 touch screen, BMI270 IMU, LTR-553 light/proximity sensor, Grove and M5-Bus ports. Board satisfies option (a), declaring all five core primitives plus camera. Planned profile name: `esp32s3-cores3`. Default board for `esp32s3` remains `esp32s3-box-3`. Options (b) and (c) retained as fallback rules if Q-3 measurements fail on CoreS3: (b) camera module attached to Box-3 while meeting Q-3 memory budget; (c) camera board is **extension reference board** (`EXTENSION_REFERENCE_BOARDS`), declaring only what hardware has, never default board of target, and "declare all five core primitives" rule applies to default board. Never declare capabilities hardware lacks.
2. **`verify` and nightly run all reference boards** of all tier-1 targets, not just default boards; trace set replayed per board capability (item 7). *Why:* equivalence only has meaning when run on exact board delivered to users.
3. **`build` without `--board`:** use default board if it satisfies `[requires]`; if not, report three-part error (FR-HAL-05) listing satisfying reference boards. Never auto-select another board. *Why:* users must know exactly which board they are flashing.
4. **`SIM_MIRRORS` is a table in core code**, not a field in `board.toml`. *Why:* a profile cannot self-declare what it mirrors (same rationale as `TARGET_TIERS`).
5. **Boards providing each extension primitive:**

   | Primitive | `sim` | `linux` | `esp32s3` |
   |:---|:---|:---|:---|
   | `digital.in`, read-only I2C, PWM | `sim-default`, `sim-rpi5` | `linux-rpi5` | `esp32s3-box-3` |
   | `analog.in` | `sim-default`, `sim-rpi5` | `linux-rpi5` + on-board I2C ADC | `esp32s3-box-3` (on-chip ADC, verified in TSK-I3a-01) |
   | `motion.*` | `sim-default`, `sim-rpi5` | `linux-rpi5` + driver with `enable_pin` | `esp32s3-box-3` via dock pins; if dock lacks pins, `esp32s3-cores3` (item 1) carries it — RFC-0011 §9.6, verified in TSK-I3a-01 |
   | `vision.in` | `sim-rpi5` | `linux-rpi5` + camera | `esp32s3-cores3` (item 1) |

   Each cell is a commitment testable by coverage tests in §3c; physical hardware preventing a cell requires opening `Q-N` and slipping dates, not dropping cells (Q-52).

   *Note on `motion.*` on `sim`:* `sim-default` carries `motion.*` only when `esp32s3-box-3` carries it; if `motion.*` moves to `esp32s3-cores3`, only `sim-rpi5` (and a `sim` profile mirroring CoreS3 if created) carries it; `sim-default` does not carry it to avoid violating the "sim is no richer than the board it mirrors" invariant.
6. **Approval Order:** This RFC is approved **prior to** RFC-0002, because I2a needs it while RFC-0002 is only needed for I11; when RFC-0002 is approved, its §5b and §5c reference this RFC rather than restating it.
7. **Trace replay set per board capability** (review 2026-10-01, Q-62). Each reference board replays only canonical traces whose primitives it fully declares, plus dedicated corpus for extension primitives it carries; default board of each target must replay all three canonical traces; a board with zero applicable traces fails (zero scans is never a pass). With current selection of M5Stack CoreS3 (all five core primitives per option (a)), CoreS3 replays all three canonical traces plus dedicated vision corpus. *Why:* avoids forcing extension boards lacking core primitives to run tests containing unsupported hardware primitives leading to false failures, while never allowing tests to be silently skipped.
