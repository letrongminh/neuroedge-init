# `esp32s3` device interface — screens, language, golden screenshots

**Trạng thái:** normative specification for TSK-S4-10 (FR-HAL-01, FR-CI-05, Q-21). Code:
[`targets/esp32s3/ui/`](../../targets/esp32s3/ui/); runner: `scripts/run_ui_golden.sh`. The `display` cell of
`esp32s3` in the coverage matrix is [`simulation_coverage.md`](simulation_coverage.md) §2.

Two sentences summarize this entire document: **the interface speaks the agent's language** (§2), and **agent text is data;
only interface text is translated** (§3).

## 1. Scope

320×240 RGB565 panel (ST7789) of Box-3 (`boards/esp32s3-box-3.toml`). The interface is pure C99 on the
LVGL v9.6.0 API (MIT, `NOTICE` section C): no ESP-IDF headers, so the same code builds on host to compare
golden screenshots on every PR (`ui-golden` job, `.github/workflows/ci-sim-linux.yml`) and links untouched into
firmware when drivers arrive.

**Out of scope:** SPI drivers for screen and touch (TSK-S4-01), and connecting the interface to running
firmware tasks. Component `targets/esp32s3/ui/CMakeLists.txt` is already registered for that point; today
firmware does not build this directory.

**Do not copy the interface into generated projects** (`neuroedge build --target esp32s3`): a project carries only
what it calls, and today nothing calls the interface yet. Copying it in would drag both LVGL and fonts into all firmware without
changing any behavior, while `SOURCES` of generator and `hatch_build.py` must match
(`tests/test_packaging.py`). Copying alongside the display driver is an intentional step in TSK-S4-01.
What firmware carries from now on is **language** (§2): `NE_AGENT_LANGUAGE` in `ne_agent.h`.

**Deterministic** rendering: no clock reading, no randomness, no autonomous animations (all calls with
animation parameters take `LV_ANIM_OFF`), no auto-scrolling. The same state struct yields the exact same pixels —
that is what makes golden screenshots meaningful.

## 2. Language — the single rule

Each agent has one language, selected in order:

| Step | Source | Result |
|:---:|:---|:---|
| 1 | `[agent] language` in `agent.toml` (ISO-639-1) | use it |
| 2 | absent ⇒ `[stt] language` | use it |
| 3 | both absent | `"vi"` |

Two errors **block build**, at two different layers:

- **Shape and conflict — all targets.** `[agent] language` must be ISO-639-1 in exactly **two** lowercase letters
  (`vi`, `en`); `vie`, `VI` are rejected. If both `[agent] language` and `[stt] language` are present and differ,
  `load_agent_manifest` stops — even on `sim`/`linux`: a session trace where the recognizer hears
  one language while the screen displays another is not a trace of the same agent. Message prints value
  verbatim (`!r`).
- **Character set and glyphs — only where interface exists.** `--target esp32s3` rejects codes that `UI_LANGUAGES`
  today (`["vi", "en"]`) lacks (even `[stt] language = "ja"`): missing character table **or** missing
  glyphs. `sim`/`linux` have no screen, so they do not check this part.

Implementation: `python/neuroedge/engine/compiler.py` (`load_agent_manifest`, `resolve_agent_language`)
and `python/neuroedge/engine/firmware.py` (`UI_LANGUAGES`, `ui_language`). Generated firmware carries the
result as `#define NE_AGENT_LANGUAGE "…"` in `ne_agent.h`.
`python/tests/test_ui_language.py` checks each branch, each error, and `sim`/`linux`;
`python/tests/test_ui_assets.py` ensures `UI_LANGUAGES`, character tables, and the **generated font cmap** match.

**C side, fail closed.** `ne_ui_language_from_code("…")` returns `NE_UI_LANG_NONE` for unknown codes, and
`ne_ui_init` returns `false` — no screen is drawn — if the language lacks a character table. Valid codes:
`ne_ui_language_code`, `ne_ui_language_supported`.

**Adding a language** (work for a normal PR): add `ne_ui_strings_<code\>` to
`targets/esp32s3/ui/src/ne_ui_strings.c`, add code to `UI_LANGUAGES`, add required glyph ranges to
`targets/esp32s3/ui/fonts/ranges.txt`, run `bash scripts/gen_ui_fonts.sh`, then
`bash scripts/run_ui_golden.sh --update`. `test_ui_assets.py` turns red if any step is missing.

## 3. Screens

Each screen has a function `ne_ui_show_*` in `ne_ui.h`; accompanying state struct is data (§ below).
Agent text — action name, `on_block` message, response, readings — renders **verbatim**, not
translated. Interface labels live in `ne_ui_strings.c`, one table per language.

| Function | Runtime state | What it draws |
|:---|:---|:---|
| `ne_ui_show_boot` | boot-time gate self-test (`main/gate_selftest.c`) | `NE_UI_BOOT_RUNNING` (progress bar) · `_PASSED` · `_FAILED` with reason (data) |
| `ne_ui_show_idle` | `VoiceState.IDLE` (`perception/voice_fsm.py`) | agent name, how to start speaking, network up/down |
| `ne_ui_show_voice` | `LISTENING` | input level 0..100 |
| `ne_ui_show_voice` | `BARGE_IN` | same as `LISTENING` with `interrupted` flag |
| `ne_ui_show_voice` | `THINKING` | transcript of heard utterance |
| `ne_ui_show_voice` | `SPEAKING` | transcript + response (wrapped, scrollable) |
| `ne_ui_show_confirm` | `on_block.action = ask` (RFC-0006) | action, prompt message (data), `fallback_action`, how to answer "có"/"không" (yes/no) |
| `ne_ui_show_verdict` | gate verdict | ALLOW / BLOCK, action, **reason code** (table below), details (data) |
| `ne_ui_show_degraded` | cloud STT/TTS or System 2 unavailable | which part is down, local commands still running (data) |
| `ne_ui_show_sensor` | `sensor.read` | name, value, unit, range (data) |
| `ne_ui_show_ota` | firmware update (OTA task) | 6 phases, progress, details (data) |
| `ne_ui_show_fatal` | halting gate | reason (data) |

Seven reason codes for BLOCK — exactly matching walker `ne_reason` table (`ne_walker.h`) and `firmware.REASONS`:
`condition_not_met`, `criterion_unavailable`, `confidence_unavailable`, `argument_out_of_range`,
`gate_unreachable`, `budget_exceeded`, `value_out_of_range`. Their labels live in `ne_ui_strings.c`; `test_ui_assets.py` keeps
C enum and Python table in sync. `NE_UI_REASON_NONE` belongs to ALLOW.

Functions receive struct pointers; `const char *` fields are data, `NULL` renders as an empty line. Screens do not
retain pointers after function returns (LVGL copies strings), so callers can pass ephemeral data.

## 4. Long text and malformed text never overflow the panel

Agent text is untrusted data — generated by a model, a human, a gate message. Four
rules, implemented in `ne_ui_text.c` and `ne_ui.c`, are deterministic:

1. **Truncate according to cell budget.** Default `NE_UI_TEXT_MAX` (320) bytes; every single-line cell has its own
   budget, 6–40 bytes (agent name, action name, sensor name, value, unit, range, command line…), small enough
   so remainder **always** terminates with visible `…`. Truncate at UTF-8 code point boundaries, append
   `…` when truncated — never truncate midway through a character. Chips and sensor row cells additionally have
   `max_width` as a safety net for wide glyphs: when width is exhausted LVGL appends ellipsis, not overflowing
   into neighboring cells.
2. **Invalid bytes become `?`.** Missing continuation bytes, overlong forms, surrogates, above U+10FFFF: each
   corrupt byte becomes one `?`. Functions never read beyond the first NUL, even if sequence ends midway through a
   multibyte character. `python/tests/test_ui_text.py` builds C driver with ASan+UBSan and runs thousands of
   random byte strings alongside hand-crafted cases (truncated tails, `\xF0`, overlong, surrogate, embedded NUL).
3. **Single-line labels stay strictly single-line.** Newlines and control characters in data become spaces
   (`ne_ui_text_single_line`), labels receive `lv_label_set_max_lines(…, 1)`, height is exactly one
   line with `LV_LABEL_LONG_MODE_DOTS`. Without this step, LVGL 9.6 **automatically wraps** (DOTS only clips
   when height is fixed) and agent text overlaps labels below.
4. **Multiline text stays only inside fixed-size scrollboxes** (prompt message, response, transcript,
   verdict reason and details, boot/fatal reason, OTA details). The box clips overflow and scrolls at
   runtime, but never expands upwards to cover other widgets. Element count rendered has a ceiling:
   `NE_UI_MAX_READINGS` and `NE_UI_MAX_COMMANDS` — longer arrays remain safe.

Text should reach interface in **NFC** form: Vietnamese NFD (decomposed combining characters) lacks glyphs in the font
and renders as boxes; normalizing before calling `ne_ui_show_*` is caller's responsibility.

## 5. Fonts

Be Vietnam Pro (OFL-1.1 — `LICENSES/OFL-1.1.txt`, `NOTICE` section A.5) provides full Vietnamese diacritics; Montserrat built-in
fonts in LVGL do not. Three sizes used in screens: **12** (secondary labels), **16**
(body), **22** (titles, readings).

`scripts/gen_ui_fonts.sh` downloads two source weights (Regular, SemiBold) by URL + SHA-256, runs
`lv_font_conv@1.5.3` via `npx`, and writes `targets/esp32s3/ui/fonts/ne_font_{12,16,22}.c`. Each generated file
carries an inline notice: source file, SHA-256, license (CONTRIBUTING.md §4 obligation 3). Glyph
ranges live in `fonts/ranges.txt` — single place, including `₫` (U+20AB) so future price strings do not require
regenerating fonts; `test_ui_assets.py` verifies all characters in both C character tables are present in the **cmap of each
generated font**, not just in `ranges.txt`.

Fonts are RLE compressed: without `LV_USE_FONT_COMPRESSED 1`, LVGL merely logs and draws blank glyphs, so
`fonts/ne_fonts.h` contains `#error` blocking build. Each generated file is a **Modified Version** under OFL 1.1
(not the font software itself); Be Vietnam Pro does **not** declare Reserved Font Name, so `ne_font_*` names
are valid. Firmware images linking this font are distributing font software: that image must carry copyright
notice and OFL text (`LICENSES/OFL-1.1.txt`) — details in `NOTICE` section A.5.

## 6. Golden screenshots

Host harness `targets/esp32s3/ui/host/` fetches LVGL **v9.6.0** pinned URL + SHA-256 in CMake; download
mismatch ⇒ CMake stops. For each **screen × language × representative state** (matrix in
`host/main.c`), harness instantiates `lv_test_display` 320×240 and compares via `lv_test_screenshot_compare` against
`targets/esp32s3/ui/golden/<lang>/<case>.png`. Display is set to **RGB565** — panel's true format —
before rendering, so golden screenshots reflect true palette; `lv_test_screenshot_compare` converts frames
to XRGB8888 for PNG output. Harness builds with ASan+UBSan (`NE_UI_SANITIZE` variable, default ON): agent
text is untrusted data, buffer over-reads must turn red here, not on the board.

After each case, harness also **checks layout** (`check_layout` in `host/main.c`): every rendered label, chip, and
bar must fit within 320×240 and no two overlap — text in scrollboxes is clipped according to the box exactly as LVGL
renders, so intentional scroll areas are not considered overlaps. A violating case stops both test and `--update`
modes, making it impossible to generate overlapping goldens; checker itself has self-tests (an intentional overlap
must be flagged).

```bash
bash scripts/run_ui_golden.sh            # verify; NEVER write golden
bash scripts/run_ui_golden.sh --update   # rebuild golden and verify again
```

Verification mode copies goldens into build directory and runs there: discrepancies leave `<case>_err.png` in build
directory, while committed goldens are untouched. Missing golden, 1-pixel discrepancy, harness build failure,
or language/reason check failure ⇒ non-zero exit. CI runs that exact script inside `espressif/idf:v5.4` container
— same toolchain that generated goldens (cmake 3.30, gcc 13) — verifying pinned bytes, not a second renderer.

## 7. What this document does not promise

- Physical SPI pins, touch, and interface embedded in firmware tasks: TSK-S4-01.
- Actual firmware update: OTA screen only renders status; OTA code is a separate task.
- Animations, screen transition effects: intentionally omitted (deterministic).
- Vietnamese text outside glyph ranges in `ranges.txt`: add ranges and regenerate fonts (§5).
