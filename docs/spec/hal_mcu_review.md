# HAL design review under microcontroller constraints

| | |
|:---|:---|
| **Mã task** | TSK-S1-11 |
| **Assignee** | V2 — Embedded Engineer (part-time until board arrives) |
| **Inputs** | `schemas/board.v1.json`, `python/neuroedge/hal/board.py`, `boards/*.toml` |
| **Trạng thái** | ✅ Xong · conclusions implemented in code |

## 0. Why this review had to happen in Sprint 1 *(context at review time)*

Roadmap §1.2 stated bluntly: *"A HAL designed without the voice of an embedded engineer
will have to be rewritten in I3."* This document is that voice, placed before any
HAL implementation exists (`sim` in I0, `linux` in I2, `esp32s3` in I3) — because afterwards, every conclusion here becomes a rewrite.

Baseline constraint: ESP32-S3-WROOM-1-N16R8 has **512 KB internal SRAM**, in which Q-3 reserves
only **≥ 120 KB** for the application after deducting the network stack and the operating system. Every
design decision below is measured against that ruler.

---

## 1. Five review conclusions

### KL-1 — Primitive set must be closed, and it is closed

`audio.in`, `audio.out`, `digital.out`, `sensor.read`, `display` — exactly five, fixed
by FR-HAL-01.

**Why it matters on MCU:** a closed set allows the device-side capability table to be
a **static array sized at compile time**. If the primitive set were extensible
at runtime, firmware would need dynamic allocation in the HAL — which is forbidden
on the audio path, because heap fragmentation after hours of running is one of the top two
causes of audio frame drops.

**Implemented:** `PRIMITIVES` in `python/neuroedge/hal/board.py` is a
`tuple`, and any unknown primitive name is rejected immediately in `_normalise()` with a message
stating the valid set. Verified: `test_unknown_primitive_is_refused`.

### KL-2 — Agent code must address pins by NAME, not by number

An agent writes `c.do("door_lock")`, not `gpio_set_level(11, 1)`. The board owns
the mapping `door_lock → GPIO 11` via `[capabilities.digital_out].pins`.

**Why it matters:** this is a necessary condition for target parity. `sim` has no
GPIO 11; `linux-rpi5` has GPIO 11 but wired to something else. An agent that pins
numbers will not be able to run across three targets, and target parity is the core product thesis.

**Implemented:** `boards/*.toml` declare the same set of pin names across all
full reference boards of all three targets; pins of hardware extensions (PWM channels and
enable pins of PWM/`motion`, RFC-0013 §3b) exist only on real boards with that hardware.
Verified: `test_all_full_reference_boards_share_the_same_named_pins`.

### KL-3 — `sim` must not be richer in capabilities than reference boards

**Risk blocked:** if `sim` declared 4 input audio channels or 48 kHz while
Box-3 has only 2 channels at 16 kHz, developers would write agents that run fine in simulation
then fail at `neuroedge build` — or worse, fail while running on
device. Then the promise of "TTFV under 10 minutes without buying hardware" (A1) becomes
a trap: it saves 10 minutes upfront and adds two days of debugging.

**Implemented:** `boards/sim-default.toml` accurately mirrors Box-3 parameters —
16 kHz, AEC, VAD, same set of pins, same set of sensors; `boards/sim-rpi5.toml` mirrors
`linux-rpi5` (RFC-0013 §3d, table `SIM_MIRRORS`). Invariants apply per pair
(sim, mirrored board), including extended primitives, envelopes, and camera modes. Verified:
`test_sim_offers_no_pin_the_reference_board_lacks`,
`test_sim_offers_no_sensor_the_reference_board_lacks`,
`test_a_sim_profile_is_never_richer_than_the_board_it_mirrors`,
`test_sim_audio_matches_the_reference_sample_rate`.

*Intentional exception:* `display` of `linux-rpi5` is 800×480 while Box-3 is 320×240.
Acceptable because `display` is not in the safety decision domain — no
gate verdict depends on screen size. The parity constraint applies only to
`sim` compared to the reference board, not between two real hardware targets.

### KL-4 — Board declarations are DATA, not CODE

Adding a board = adding a TOML file. Not adding a single line of Python.

**Why it matters:** if a board profile were Python code, it could contain behavior
that the MCU build lacks (and cannot have). Then "the board declared this capability"
would mean different things between host and device — right at the layer where bidirectional
capability verification must be trustworthy.

**Implemented:** `boards/` contains only TOML, validated against
`schemas/board.v1.json`. Filenames match `id` so lookups do not drift. Verified:
`test_profile_filename_matches_its_declared_id`,
`test_profile_validates_against_board_schema`.

### KL-5 — No CEL evaluator, no JSON parser on MCU

This is the direct consequence of **Q-9 option A** (and Q-23 on formats) and is the conclusion
with the greatest impact on HAL design. The device **does** evaluate gates — via a precompiled
tree walker (TSK-S4-02) — but all parsing and compiling happen on the computer.

| Runs on computer | Runs on device |
|:---|:---|
| Resolve `extends` (5 principles of B.5) | — |
| Parse CEL syntax | — |
| Compile to decision tree, encode `NETR` v1 binary layout (Q-23, RFC-0003) | C99 walker traverses `NETR` tree in-place in flash |
| Canonicalise RFC 8785, hash | Check magic, layout version, CRC of tree before use |
| Digitally sign gate (Block 3, Gate Registry) | Signature verification — also Block 3, not yet implemented |

**Device-side budget:** walker allocates no heap, uses no static RAM, no
recursion, no syntax parsing, no CEL virtual machine; stack ≤ 512 bytes
(`targets/esp32s3/components/ne_gate/src/ne_walker.c`,
`test_the_walker_uses_no_static_ram_and_a_small_stack`).

*Note 2026-09-24:* the initial review (Sprint 1) formulated KL-5 as "no gate engine
runs on MCU" and planned "JSON decision tree" + "a C function of around 100 lines"; Q-23 and
RFC-0003 replaced it with a binary layout. The spirit of the conclusion — the device does not parse, only walks
— remains unchanged. The board model in
`board.py` **is read only on the computer** — which is why it is allowed to use Pydantic,
`jsonschema`, `tomllib` without incurring any technical debt for firmware.

**Forbidden:** embedding `cel-python` or any expression evaluator
into firmware. Roadmap §3.8 explicitly rejected option B (a trimmed CEL evaluator
in C) because it creates a second implementation that must be kept in sync right at the safety
layer.

---

## 2. Four constraints carrying over to I3

The statements below are contracts that `hal/esp32s3` must satisfy, recorded here so
I3 does not need to deduce them again:

| # | Constraint | Reason |
|:---:|:---|:---|
| RB-1 | No `malloc` on audio path after initialization finishes | Heap fragmentation after hours of running causes frame drops; I5 criterion 4 (roadmap §6) measures memory remaining after 4 hours |
| RB-2 | Audio buffers statically allocated in PSRAM, named and measurable | Q-3 reserves ≥ 2 MB PSRAM for ring buffer, VAD, and wake-word; if not measurable, cannot be verified |
| RB-3 | `digital.out` must cancel pending command in ≤ 1 audio frame | Physical command revocation contract ([`voice_fsm.md`](voice_fsm.md) §5): barge-in must cancel pending door latch pulse, log `ACTUATOR_ABORTED_BY_BARGE_IN` |
| RB-4 | Capability table is `const` in flash, not a runtime-built structure | Saves SRAM and eliminates possibility of capabilities being modified at runtime — a shortcut bypassing gates (A3) |

**RB-3 is the hardest constraint.** It says `digital_out` cannot be a
blocking call. The current signature in
`python/neuroedge/hal/__init__.py` takes `duration_ms` and records the pin state
immediately — sufficient for `sim`, but the `esp32s3` implementation will need a cancellable handle.
Recorded as **known design debt**, to be resolved in TSK-S4-01 concurrently with
the command revocation contract, not after.

## 3. What this review does NOT conclude

This review speaks to *design shape*, not to *memory feasibility*. The question
"do AEC + VAD + Opus fit within 120 KB SRAM and 2 MB PSRAM" can only be answered by
measurements on real hardware — that is TSK-S1-10, and its status in
[`docs/reports/memory_spike_report.md`](../reports/memory_spike_report.md) is:
**no measurements yet**.

The two items are independent: the HAL design can be correct while the memory budget
still slips — in that case, replan I5 according to Q-44, do not cut voice.
