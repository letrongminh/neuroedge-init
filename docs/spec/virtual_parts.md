# Virtual parts — Software Requirements Specification

**Status:** normative for Q-84 (2026-10-15). Structure follows ISO/IEC/IEEE 29148:2018 §9.6.
This file is the one place for what the virtual board, the parts catalogue and the parts canvas
must do (CONTRIBUTING.md §8.1); the roadmap, the CHANGELOG and `simulation_coverage.md` §5.1 cite
its requirement IDs and do not restate them. `python/tests/test_virtual_parts_srs.py` keeps the
tables of §3 and §5 closed: every requirement has a test case, every implemented test case names
a test that exists, every planned one names a roadmap task.

---

## 1. Introduction

### 1.1 Purpose

Trying a new use case on `sim` today means borrowing one of the three output pins and four
sensors that `boards/sim-default.toml` declares: the fish tank's air pump is `door_lock`, and a
pH probe has nowhere to go. This specification states how an agent gets the parts it needs on
`sim` without a board file per use case, without loosening what the real boards check, and how
those parts are later placed by drag and drop.

### 1.2 Scope

In scope, in three phases (Q-84):

| Phase | What | Requirements | Task | State |
|:---|:---|:---|:---|:---|
| **A** | A virtual board derived from the agent, on `sim` only, labelled `risk=virtual_board` | VP-VB-* | TSK-I2d-29 | decided |
| **B** | A catalogue of universal part kinds, `[sim.parts]` in agent.toml, `neuroedge add part` | VP-PT-* | TSK-I2d-30 | decided |
| **C** | A drag-and-drop canvas on the sim page that writes `[sim.parts]` | VP-CV-* | TSK-I2d-31 | deferred: reopens with data after the 2026-12-06 demand gate (Q-77, Q-84) |

Out of scope: gate semantics and their authoring (`core_contracts.md`; a gate is never drawn,
VP-CV-03), the `board.v1` and `trace.v1` schemas (unchanged, VP-NF-01), electrical simulation
(SPICE, timing of real buses), running firmware in a browser simulator (Wokwi: the engine is a
closed service; QEMU already runs the chip, `scripts/qemu_aquarium.py`), remote actuators
(RFC-0018), and mapping a virtual pin name to a real board's pin (VP-OQ-01).

### 1.3 Definitions

| Term | Meaning |
|:---|:---|
| **Reference sim board** | `boards/sim-default.toml`, or `sim-rpi5` when the agent needs a primitive only that board has (the rule `neuroedge add` already applies). |
| **Virtual board** | The board profile `sim-virtual`, built in memory from the reference sim board plus exactly what the agent declares that the reference board lacks. Never a file in `boards/`. |
| **Part** | One entry of `[sim.parts]`: a name, a kind, the pin, sensor or channel it is wired to, and the words the page shows. |
| **Kind** | An entry of the parts catalogue: which primitive the part is, its icon, unit, range and envelope preset. A kind adds no primitive; it names an existing one. |
| **Envelope preset** | The safety envelope (RFC-0007 §3d: `window_s`, `max_on_ms_per_window`, `min_interval_ms`, `max_continuous_ms`) a kind gives an output pin on the virtual board. |
| **Graduation** | Building the same agent for `linux` or `esp32s3`: checked against the real board profile, never against the virtual board. |

### 1.4 References

PRD §15 Q-72, Q-73, Q-77, Q-84; FR-DX-01, FR-DX-02, FR-DX-03, FR-DX-08, FR-TGT-06 ·
`CONTRIBUTING.md` §3 (board profiles need physical hardware; no dummy declarations) ·
RFC-0007 §3d (an envelope per output pin), RFC-0013 §3a · `docs/spec/simulation_coverage.md` §5 ·
`docs/spec/deployment_profiles.md` DP-A-02 (the page's key) · `python/neuroedge/hal/board.py`
(`validate_board_document`, `board_from_document`) · `python/neuroedge/templates/add/` ·
Wokwi `diagram.json` (parts and connections, the shape `[sim.parts]` follows) and Wokwi Elements
(MIT, visuals only).

---

## 2. Overall description

### 2.1 Product perspective

```
 agent.toml ─┬─ [requires]   (what the agent needs; build checks it on every target)
             ├─ [sim.parts]  (phase B: what each pin or sensor is, in people's words)
             └─ [sim] board = "sim-virtual"
                      │
                      ▼
 reference sim board + what [requires] / [sim.parts] add  ──►  sim-virtual (memory only)
                      │                                         risk=virtual_board
                      ▼
        SimSession · run --ui page · trace (board_id sim-virtual, digest)
                      ▲
 phase C: canvas ─────┘  writes [sim.parts] and [requires] through the page, then reloads

 build --target linux | esp32s3  ──►  real board profile, unchanged (graduation)
```

### 2.2 Why three phases

A and B are files and commands: everything they produce is reviewed in a PR, linted and tested
like any agent. C is the same files edited by drag and drop; it belongs to the authoring loop that
Q-77 removed with NeuroEdge Lab, so it waits for measurements. Writing C's requirements now keeps
A and B from closing doors C needs (VP-PT-01 is the canvas's save format).

### 2.3 User classes

| Class | Uses |
|:---|:---|
| Maker trying a use case | A + B: declares parts, runs `run --ui`, never writes a board file |
| Tester of someone else's agent | The page (`simulation_coverage.md` §5.1), labels and kinds from B |
| Reviewer | The PR diff of agent.toml; `risk=virtual_board` on every trace |
| Non-programmer (phase C) | The canvas; gates come from `add` templates, reviewed by a programmer |

### 2.4 Constraints

1. No change to any row of `CONTRIBUTING.md` §3: `schemas/`, gate resolution, the three
   normative traces, `digests.lock`, NETR (VP-NF-01).
2. `boards/` keeps only profiles of hardware that exists (RFC-0013 §3a): the virtual board is
   never written there and never listed by `available_boards()` (VP-VB-07).
3. The page stays one offline file: no CDN, no build step (FR-DX-02, `simulation_coverage.md` §5).
4. Risk labels, not prohibitions (Q-73): a virtual board is allowed on `sim` and says so.

### 2.5 Assumptions and dependencies

- The agent's `[requires]` stays the single declaration of what it needs; parts describe, they do
  not replace it (VP-PT-03).
- Every primitive a kind names is already implemented by `SimHAL` (digital.out, digital.in,
  sensor.read, analog.in, motion, display).

---

## 3. Specific requirements

Verification methods: **T** test, **I** inspection, **A** analysis, **D** demonstration.

### 3.1 Phase A — Virtual board (VP-VB)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| VP-VB-01 | The board `sim-virtual` shall be selected by `--board sim-virtual` on `run`, `mcp serve`, `test`, `build --target sim` and `neuroedge add`, or by `[sim] board = "sim-virtual"` in agent.toml; with neither, the default board is unchanged. | Opt-in: existing agents and the canonical traces keep `sim-default`. | Q-84 | T |
| VP-VB-02 | The virtual board shall be the reference sim board plus every `digital.out` and `digital.in` pin, sensor, `analog.in` channel and `motion` channel that the agent's `[requires]` or `[sim.parts]` names and the reference board lacks; nothing else is added and nothing of the reference board is removed. An added `analog.in` channel copies `adc0` of `sim-rpi5`, an added motor `wheel_left` and an added servo `gripper` (limits, lease, safe state, envelope), with an enable pin `<name>_en` added beside it. The result shall pass `validate_board_document` unchanged. | The agent gets exactly what it declares; the board stays a valid `board.v1` document. | Q-84 | T |
| VP-VB-03 | Each added `digital.out` pin shall get an envelope: its part's kind preset (VP-PT-04), else the default `window_s` 3600, `max_on_ms_per_window` 600000, `min_interval_ms` 2000, `max_continuous_ms` 60000 (the strictest value of each field over the output pins of the reference sim boards). | RFC-0007 §3d: no output pin without an envelope. | RFC-0007, Q-84 | T |
| VP-VB-04 | `sim-virtual` shall be refused with an error naming the board and the target on any target other than `sim` (`build`, `run`, `mcp serve`, `test`), and `build --target linux` or `esp32s3` shall check the agent against the real board exactly as before. | Graduation is checked against hardware that exists. | CONTRIBUTING §3, RFC-0013 §3a | T |
| VP-VB-05 | A session on `sim-virtual` shall print `risk=virtual_board` at start, list the pins, sensors and channels the virtual board added, write `"risks": ["virtual_board"]` and `"virtual_board_digest"` into the trace metadata (extra keys `trace.v1` already allows), and show the label in the page header. | Transparency instead of prohibition. | Q-73 | T |
| VP-VB-06 | `virtual_board_digest` shall be the SHA-256 of the virtual board's canonical JSON (sorted keys, no whitespace). `replay` and `verify` of a trace recorded on `sim-virtual` shall rebuild the board from the agent and refuse, naming both digests, when it differs; when equal, they shall reach the recorded verdicts. | A recording proves something only about the board it ran on. | Q-72, Q-84 | T |
| VP-VB-07 | `load_board_by_id("sim-virtual")` without an agent, `available_boards()` and `boards/` shall not contain or produce the virtual board; asking for it without an agent shall fail naming VP-VB-01. | No dummy board in the profile set. | RFC-0013 §3a | T |
| VP-VB-08 | Building the virtual board from the same agent shall give the same canonical JSON on every run and machine. | The digest of VP-VB-06 is stable. | Q-84 | T |

### 3.2 Phase B — Parts catalogue (VP-PT)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| VP-PT-01 | `[sim.parts.<name>]` in agent.toml shall declare a part with `kind` (required), the one target key its kind names (`pin`, `sensor` or `channel`; none for `display`), optional `label`, and the kind's optional attributes (§4.1). An unknown key, an unknown kind, a missing or doubled target, or a target of the wrong primitive shall fail at load with the part's name. | One declared, checked shape; it is also phase C's save format. | Q-84 | T |
| VP-PT-02 | The catalogue shall be one data file, `python/neuroedge/sim/parts.toml`, with the kinds of §4.2. Every kind shall name exactly one primitive `SimHAL` implements; a kind adds no primitive and no gate behaviour. Adding a kind shall be a regular PR. | One place for the catalogue; universal parts without new HAL code. | Q-84 | T |
| VP-PT-03 | A part's target shall appear in the agent's `[requires]` under the kind's primitive; a part wired to something `[requires]` does not declare shall fail at load naming both. `neuroedge add part` writes both. | `[requires]` stays the one declaration build checks on every target. | Q-84 | T |
| VP-PT-04 | On `sim-virtual`, an output part's envelope shall be its kind's preset; the part may give smaller values per field (`max_continuous_ms = 5000`), never larger, and a larger one shall fail at load. On any other board, parts shall not change envelopes. | A part can make a pin safer, never looser; real boards keep their own envelopes. | RFC-0007, Q-84 | T |
| VP-PT-05 | A sensor part with a `range` shall refuse, from `:sensor` and from the page, a value outside it, with a message naming the range; "Mất tín hiệu" (no reading) stays allowed. A reading the session already holds is never changed by the range. | A typo cannot pass for a reading; a lost probe is still testable. | Q-84 | T |
| VP-PT-06 | The page shall show a part's `label` (else the kind's default word), its kind's icon, unit and range; `[ui.labels]` shall keep working and win over a part's label for the same name. | People's words on every card; agents written before B unchanged. | Q-84 | T |
| VP-PT-07 | `neuroedge add part <kind> <name> [--pin/--sensor/--channel] [--label]` shall write the part and its `[requires]` entry and, for output kinds, run `add action` (or `add sensor` for sensor kinds) so the part arrives with an action, a fail-closed gate and a two-way test; it shall refuse an unknown kind by listing the catalogue, and change nothing when any step fails. `neuroedge add part --list` prints the catalogue. | The command phase C's "drop a part" will call. | FR-DX-08, Q-84 | T |
| VP-PT-08 | The aquarium sample shall declare its heater, air pump, light and water probe as parts on its existing pins (its `[ui.labels]` replaced), and keep passing `test_aquarium.py`, `tests_linux/test_kit_aquarium.py` and the `aquarium-qemu` job unchanged. | The first use case proves B without breaking graduation. | TSK-I2d-28 | T |

### 3.3 Phase C — Parts canvas (VP-CV), deferred

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| VP-CV-01 | On `run --ui` with `sim-virtual`, the page shall offer a palette of the catalogue's kinds; dropping a kind on the canvas and wiring it to a pin or sensor name shall propose a `[sim.parts]` entry and its `[requires]` entry. | Wire it like a breadboard. | Q-84 | D |
| VP-CV-02 | The page shall show the agent.toml diff before writing; the write shall go through `POST /parts` with the page's key (DP-A-02), be atomic (temporary file, rename), and leave the file unchanged when the result would fail VP-PT-01 or VP-PT-03. The canvas shall not be offered by `mcp serve` or on any target but `sim`. | The file stays the truth; only the person at the page can change it. | DP-A-02, Q-84 | T |
| VP-CV-03 | The canvas shall create gates only through `neuroedge add part` (VP-PT-07) and shall offer no control that edits a gate's criteria, `allow_when` or `on_block`. | Safety rules stay files that are linted and reviewed. | CHANGELOG §3.3 #1 | T |
| VP-CV-04 | After a write, the session shall restart on the new agent as a new trace session; a pending `ask` shall expire, and nothing of the old session shall carry over. | One recording, one board. | VP-VB-06 | T |
| VP-CV-05 | The canvas shall stay inside the one offline page: SVG drawn by the page's own script; Wokwi Elements may be bundled (MIT notice kept), never fetched. | FR-DX-02: `sim` runs offline. | FR-DX-02 | T |

### 3.4 Non-functional requirements (VP-NF)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| VP-NF-01 | Phases A, B and C shall change no row of `CONTRIBUTING.md` §3: `schemas/*.json`, `engine/gate_resolver.py`, `engine/constraints.py`, `fixtures/traces/*.json`, `digests.lock`, NETR. | Outside the RFC list by construction. | CONTRIBUTING §3 | T |
| VP-NF-02 | Every agent and canonical trace that runs on `sim-default` or `sim-rpi5` today shall give the same verdicts and pin commands after A and B. | Opt-in means nothing else moves. | Q-84 | T |

---

## 4. Interfaces

### 4.1 `[sim.parts]`

```toml
[sim]
board = "sim-virtual"

[requires]
"digital.out" = { pins = ["heater", "air_pump"] }
"sensor.read" = { sensors = ["water_temp", "ph"] }

[sim.parts.heater]
kind  = "heater"
pin   = "heater"
label = "Máy sưởi"
max_continuous_ms = 30000          # tighter than the kind's preset (VP-PT-04)

[sim.parts.air_pump]
kind = "pump"
pin  = "air_pump"

[sim.parts.water_temp]
kind   = "temperature"
sensor = "water_temp"
range  = [0, 45]

[sim.parts.ph]
kind   = "ph"
sensor = "ph"
```

### 4.2 Catalogue, first version

| Kind | Primitive | Target key | Default word | Unit, range | Envelope preset (`max_continuous_ms`, `min_interval_ms`) |
|:---|:---|:---|:---|:---|:---|
| `relay` | digital.out | `pin` | Relay | — | 60000, 2000 |
| `light` | digital.out | `pin` | Đèn | — | 600000, 2000 |
| `heater` | digital.out | `pin` | Máy sưởi | — | 60000, 2000 |
| `pump` | digital.out | `pin` | Máy bơm | — | 60000, 2000 |
| `fan` | digital.out | `pin` | Quạt | — | 600000, 2000 |
| `lock` | digital.out | `pin` | Khoá | — | 60000, 1000 |
| `button` | digital.in | `pin` | Nút bấm | — | — |
| `contact` | digital.in | `pin` | Cảm biến cửa | — | — |
| `temperature` | sensor.read | `sensor` | Nhiệt độ | °C, −40…125 | — |
| `humidity` | sensor.read | `sensor` | Độ ẩm | %, 0…100 | — |
| `level` | sensor.read | `sensor` | Mực nước | %, 0…100 | — |
| `ph` | sensor.read | `sensor` | Độ pH | pH, 0…14 | — |
| `sensor` | sensor.read | `sensor` | Cảm biến | from `unit`, `range` | — |
| `knob` | analog.in | `channel` | Núm vặn | V, 0…2.5 (as `adc0`) | — |
| `motor` | motion | `channel` | Động cơ | — | as `wheel_left` of `sim-rpi5` (10000, 2000) |
| `servo` | motion | `channel` | Servo | deg, 0…90 | as `gripper` of `sim-rpi5` (3000, 1000) |
| `display` | display | — | Màn hình | — | — |

Every `digital.out` preset has `window_s` 3600 and `max_on_ms_per_window` 600000; no preset is looser than the
reference board's loosest pin of the same use (`porch_light` for lights).

### 4.3 Command line

```
neuroedge run --agent agent.toml --ui --board sim-virtual
neuroedge add part --list
neuroedge add part heater heater --pin heater --label "Máy sưởi"
neuroedge add part ph ph --sensor ph
```

Start-up line (VP-VB-05): `risk=virtual_board added: digital.out heater, air_pump · sensor.read ph`.

### 4.4 Trace metadata (VP-VB-05, VP-VB-06)

```json
"metadata": { "target": "sim", "board_id": "sim-virtual",
              "risks": ["virtual_board"], "virtual_board_digest": "sha256:…" }
```

---

## 5. Verification

Status `implemented — <file>::<test>` names a test in this repository; `planned — <TSK>` names
the roadmap task that adds the test with the code. No test is skipped in the meantime
(CONTRIBUTING.md §5).

| TC | Verifies | Level | Procedure → expected | Status |
|:---|:---|:---|:---|:---|
| TC-VB-01-1 | VP-VB-01, VP-NF-02 | integration | An agent with and without `--board sim-virtual` / `[sim] board` → board id `sim-virtual` / `sim-default`; every canonical trace replays unchanged | planned — TSK-I2d-29 |
| TC-VB-02-1 | VP-VB-02 | unit | Agent needing `heater`, `ph`, a `digital.in` pin → the three added, every reference capability kept, nothing else; `validate_board_document` passes | planned — TSK-I2d-29 |
| TC-VB-03-1 | VP-VB-03 | unit | An added pin without a part → the default envelope; a held `on` turns itself off after 60 s | planned — TSK-I2d-29 |
| TC-VB-04-1 | VP-VB-04 | unit | `sim-virtual` with `build`/`run`/`mcp serve`/`test` on `linux` and `esp32s3` → error naming board and target; `build --target esp32s3` of the same agent names the pins Box-3 lacks | planned — TSK-I2d-29 |
| TC-VB-05-1 | VP-VB-05 | integration | `run` on `sim-virtual` → start-up line lists the additions; trace metadata carries `risks` and the digest and validates against `trace.v1`; page header shows the label | planned — TSK-I2d-29 |
| TC-VB-06-1 | VP-VB-06 | integration | Record on `sim-virtual`, replay → same verdicts; add a pin to the agent, replay → refused naming both digests | planned — TSK-I2d-29 |
| TC-VB-07-1 | VP-VB-07 | unit | `available_boards()` and `boards/` → no `sim-virtual`; `load_board_by_id("sim-virtual")` → error naming VP-VB-01 | planned — TSK-I2d-29 |
| TC-VB-08-1 | VP-VB-08 | unit | Build the virtual board twice, with `[requires]` keys in another order → identical canonical JSON and digest | planned — TSK-I2d-29 |
| TC-PT-01-1 | VP-PT-01 | unit | Corpus of `[sim.parts]` tables: valid ones load; unknown key, unknown kind, no target, two targets, wrong primitive → each fails naming the part | planned — TSK-I2d-30 |
| TC-PT-02-1 | VP-PT-02 | unit | Every kind of `parts.toml` names one primitive `SimHAL` implements; every kind of §4.2 is in the file and nothing else | planned — TSK-I2d-30 |
| TC-PT-03-1 | VP-PT-03 | unit | A part on a pin `[requires]` lacks → load fails naming both | planned — TSK-I2d-30 |
| TC-PT-04-1 | VP-PT-04 | unit | Preset applied; a tighter `max_continuous_ms` applied; a looser one fails; on `sim-default` the part leaves the envelope unchanged | planned — TSK-I2d-30 |
| TC-PT-05-1 | VP-PT-05 | integration | `:sensor ph 15` and the page's "Đặt" with 15 → refused naming 0…14; "Mất tín hiệu" → accepted | planned — TSK-I2d-30 |
| TC-PT-06-1 | VP-PT-06 | unit | `[ui.labels]` keeps only non-empty strings and is read by the page | implemented — python/tests/test_sim_ui.py::test_labels_are_words_for_people_and_anything_else_is_left_out |
| TC-PT-06-2 | VP-PT-06 | integration | Page of an agent with parts → each card has the part's label, icon, unit; a `[ui.labels]` entry wins | planned — TSK-I2d-30 |
| TC-PT-07-1 | VP-PT-07 | integration | `add part heater` in a fresh `neuroedge new` project → part, `[requires]`, action, gate, test written; `neuroedge test` passes; an unknown kind or a failing step leaves every file unchanged | planned — TSK-I2d-30 |
| TC-PT-08-1 | VP-PT-08 | integration | The aquarium with parts → `test_aquarium.py` passes unchanged; its agent.toml has no `[ui.labels]` | planned — TSK-I2d-30 |
| TC-CV-01-1 | VP-CV-01, VP-CV-05 | browser | Drop a `pump` on the canvas, wire it to `air_pump` → proposed diff shows the part and `[requires]`; page has no external URL | planned — TSK-I2d-31 |
| TC-CV-02-1 | VP-CV-02 | integration | `POST /parts` without the key, with an invalid part, from `mcp serve` → refused, file byte-identical; valid → file written atomically | planned — TSK-I2d-31 |
| TC-CV-03-1 | VP-CV-03 | inspection | The page's script has no control that writes a gate file; new gates come from `add part` only | planned — TSK-I2d-31 |
| TC-CV-04-1 | VP-CV-04 | integration | A write while an `ask` is pending → the question expires, a new session id starts on the new board digest | planned — TSK-I2d-31 |
| TC-VNF-01-1 | VP-NF-01 | unit | The files of VP-NF-01 are unchanged by the phases' commits (`check_digests.py`, `git diff` of `schemas/` against the commit before TSK-I2d-29) | planned — TSK-I2d-29 |

---

## 6. Traceability

| Decision / source | Requirements |
|:---|:---|
| Q-84 (this work) | all |
| Q-73 (risk labels, not prohibitions) | VP-VB-05 |
| Q-77 (Lab removed; reopen with data) | VP-CV-* deferred |
| RFC-0007 §3d (envelope per output) | VP-VB-03, VP-PT-04 |
| RFC-0013 §3a, CONTRIBUTING §3 (no dummy boards) | VP-VB-04, VP-VB-07, VP-NF-01 |
| DP-A-02 (page key) | VP-CV-02 |
| FR-DX-02 (offline sim) | VP-CV-05 |
| FR-DX-08 (`neuroedge add`) | VP-PT-07 |

## 7. Open questions

| ID | Question | Default until decided |
|:---|:---|:---|
| VP-OQ-01 | Graduation: should agent.toml map a virtual pin name to a real board pin (`[targets.esp32s3.pins] heater = "gate_relay"`)? It touches `build` on every target. | No mapping: the agent renames its pins, or a board profile with those pins is added once the hardware exists. |
| VP-OQ-02 | Should `neuroedge new` write `[sim] board = "sim-virtual"`? It makes every new project carry `risk=virtual_board`. | No: opt-in. |
| VP-OQ-03 | Phase C visuals: bundle Wokwi Elements (size against the page budget) or draw the 17 kinds in SVG? | Decided with TSK-I2d-31. |
