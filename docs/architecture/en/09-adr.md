# 09 · Architecture decisions (ADR)

> **Scope:** the decisions that shape the architecture, each as an ADR: context → decision →
> consequences → where it is enforced. **Sources:** the single decision register is PRD §15 (codes
> `Q-N`); changes to frozen contracts are RFCs (`docs/rfc/`). This page does **not** replace those two
> sources: it shows what each decision looks like in the architecture, and which code holds it.

**What this chapter is for:** For systems engineers, safety reviewers, and QA. This chapter answers the question: *why the architecture has its current shape and which decisions shape each safety mechanism*. Read after [`00-overview.md`](00-overview.md) and [`01-context-c4l1.md`](01-context-c4l1.md); read before proposing major changes or opening a new RFC at [`docs/rfc/`](../../rfc/).

ADR identifiers are the `Q-N` or `RFC-NNNN` codes, so there are no two numbering systems. The full
status of the 46 decisions is in PRD §15; below are the decisions with architectural consequences.

## 1. Execution and safety

### Q-24 · Every action is a tool call through a single path
- **Context.** An action can come from local grammar, an LLM, another agent. Multiple entry paths are
  multiple places to forget the gate.
- **Decision.** Every `@action` is a tool with a schema generated from the function signature. Every
  source sends the same `ToolCall` through `dispatch()` → `c.do()` → gate → token; the dispatcher
  inserts `call_source`.
- **Consequences.** A single enforcement point; the gate can distinguish call sources; MCP is a thin
  adapter.
- **Enforcement.** `actions/tools.py::dispatch`, `mcp_server.py`; `docs/spec/tool_calling.md`; corpus
  `fixtures/tool_calls/`.

### Q-9 · No CEL on the microcontroller (option A)
- **Context.** An expression evaluator on chip is one more implementation to keep in sync, in the
  safety layer.
- **Decision.** `neuroedge build` compiles gates into a deterministic decision tree; firmware only
  walks the tree. `allow_when` today is an operator mapping; CEL is an optional front-end later
  (TSK-S2-06, on hold).
- **Consequences.** Gate semantics have one source (the Python engine); the chip is small and
  deterministic; every new operator must compile down to the same tree.
- **Enforcement.** `engine/decision_tree.py`; the resolver rejects string-form `allow_when`.

### Q-23, RFC-0003 · The on-device tree is the fixed binary layout `NETR` v1
- **Context.** A JSON parser on an MCU costs flash, RAM and is an attack surface.
- **Decision.** Little-endian binary layout, no pointers, with magic, version and CRC, linked as a
  `const` array in flash; `decision_tree.v1.json` is only the host's internal format.
- **Consequences.** The walker reads in place, does not allocate; changing the layout is an RFC matter
  and bumps `layout_version`.
- **Enforcement.** `engine/binary_tree.py` ↔ `components/ne_gate/`; `test_c_walker.py`.

### Q-18, RFC-0004 · Child gates may not loosen `budget` and `on_block`
- **Decision.** Child `p95` ≤ parent; a chain already `closed` cannot reopen; a child may not add
  `degrade` or change `fallback_action`.
- **Consequences.** Inheritance is a tighten-only relation on **every** field with a safety effect, not
  just `allow_when`.
- **Enforcement.** `engine/gate_resolver.py`; corpus `fixtures/gates/invalid/`.

### Q-25, RFC-0005 · Argument limits live in the gate
- **Decision.** Ranges, sets and lengths of arguments are declared in the gate (not in `agent.toml`),
  may only be narrowed on inheritance, are checked before every fact including default values, and
  appear in `inputSchema`.
- **Consequences.** A dangerous argument (`duration_s = 3600`) is blocked by the gate, independent of
  the caller.
- **Enforcement.** `engine/arguments.py`; the argument record in `NETR`.

### Q-26, RFC-0006 · Only the person at the device can confirm, and only for criteria the gate lists
- **Decision.** Only `local_grammar` and `ui` can answer an `ask` question; a confirmation
  **re-evaluates** the gate, exempting only the criteria in `on_block.confirms`.
- **Consequences.** A "yes" never gets past another criterion; models and MCP clients have no
  confirmation path.
- **Enforcement.** `actions/confirmation.py`; `test_tool_confirm.py`; `confirm_mask` in `NETR`.

### Q-17 · Every `on_block` blocks the physical action
- **Decision.** `escalate` and `ask` still record a trace and call hooks (which do nothing by default);
  `degrade` runs `fallback_action` **through its own gate**.
- **Enforcement.** `engine/gate.py`, `actions/conversation.py`.

### Q-14 · Offline, the gate still evaluates with local command grammar
- **Decision.** Block with `gate_unreachable` only when there is no fallback or it cannot run. Fallback
  is P0; one backend per target on the same grammar.
- **Enforcement.** `models/grammar.py`, `models/system.py`; `test_offline_fallback.py`. On `esp32s3`:
  not yet (TSK-S5-07).

### Q-46 · Spoken "yes"/"no" only answers the ask question of that exact turn
- **Context.** When the user answers by voice via STT, the risk of misrecognition from noise or a late
  utterance can inadvertently confirm a dangerous question from a previous turn.
- **Decision.** A spoken answer only answers the `ask` question of that exact turn: during the turn in
  which the question is open (T11), or spoken as barge-in while the question is being read. If TTS
  encounters an error while reading the question, the state machine returns to IDLE, without opening an
  answer turn (an unheard question cannot be confirmed). Text typing and UI buttons remain unchanged per
  RFC-0006. (PRD §15 Q-46).
- **Consequences.** An STT hallucination from noise, or a "yes" to a different question, cannot substitute
  for a criterion in `confirms`.
- **Enforcement.** `docs/spec/voice_fsm.md` §4 (T12), §5.4, §9 (V4); `perception/voice_fsm.py`,
  `perception/voice_session.py`, `sim/session.py`.

### Q-48 · The conversation state machine is L2, not L4
- **Context.** The five-layer diagram in proposal §3.1 placed the "conversation state machine" in L4, while proposal §3.4 and the code (`perception/` declares itself L2) place it in L2.
- **Decision.** The turn state machine (listen, think, speak, barge-in) belongs to **L2 — perception and conversation runtime**; L4 is agent logic, context memory, gated tool calls (MCP) and System 2 (PRD §15 Q-48).
- **Consequences.** It runs in real time on both chip and host with one compliance vector suite; on barge-in it cancels pending actuator commands, but it never evaluates a gate and never drives a pin. No code change; the proposal §3.1 diagram was corrected.
- **Enforcement.** `perception/voice_fsm.py`, `docs/spec/voice_fsm.md`, `fixtures/compliance/voice/`; the layer table in [`03`](03-component-host-c4l3.md) §2.

## 2. Models and providers

### Q-4, Q-12 · System 1 is Jev via the System One API; System 2 is a standard OpenAI LLM
- **Decision.** The default standard is an OpenAI-compatible platform (one base URL, one key): chat
  completions, audio, and a typed decision endpoint (`POST /systemone`). Other providers go through
  self-written adapters.
- **Consequences.** Changing provider is changing configuration; models return only facts
  (`Fact`/`Unavailable`), never verdicts.
- **Enforcement.** `models/providers/`, `perception/providers/`.

### Q-10 · LiteLLM is a library, not a proxy
- **Decision.** Use LiteLLM as an SDK, always behind `neuroedge.models.providers`, installed only via
  the `cloud` extra.
- **Consequences.** `pip install neuroedge` is light and needs no key; no server is operated by
  NeuroEdge.
- **Enforcement.** `pyproject.toml`; job `cloud-extra`.

### Q-27 · System 2 is an MCP host
- **Decision.** Device tools go through the agent's own MCP server (still through the gate); external
  MCP servers are only for information, per an allowlist, and their results are untrusted data. The MCU
  is never a host.
- **Enforcement.** `mcp_host.py`; `test_mcp_host.py`.

### Q-7, Q-45 · Wake word: the user supplies the model
- **Decision.** openWakeWord on host, microWakeWord on chip (Q-7). openWakeWord's bundled models have a
  non-commercial license, incompatible with Q-45 ⇒ not shipped, not downloaded.
- **Enforcement.** `perception/providers/wake.py`; `TODOS.md` #49.

### Q-28 · Delivery milestone for the provider abstraction layer (FR-GW)
- **Context.** The provider abstraction layer (FR-GW) needs to support multi-provider and failover, but
  building the entire centralized fleet management capability too early would bloat the v1.0 scope.
- **Decision.** v1.0 (Block 1a) only ships minimal FR-GW-01 (a single `[system_two]` table in `agent.toml`,
  keys read from environment variables, not stored in files or code) and FR-GW-03 (failover contract in
  source code). The remainder belongs to v1.1 (Block 2, TSK-K2-01→03): declaring multiple providers and
  failover in `agent.toml` (TSK-K2-02), a shared endpoint and credential for the entire fleet,
  server-side FR-GW-02/04, FR-GW-05→07 (TR-1, TR-6). (PRD §15 Q-28).
- **Consequences.** v1.0 runs on `sim`/`linux` with a single provider whose keys are held by the user,
  requiring no NeuroEdge servers; the fleet-level part of the provider layer (v1.1) remains a
  self-operated core, unmonetized (roadmap §6.1), and only makes sense when Fleet OS exists.
- **Enforcement.** `models/providers/config.py`, `agent.toml`; [`15`](15-target-architecture.md) §3.3.

### Q-47 · Fleet OS uses FastAPI WebSockets for connection and telemetry only
- **Context.** Proposal §6.2 used to say Fleet OS uses FastAPI WebSockets "for audio streams" — a leftover from the commercial Inference Gateway; proposal §6.1, §8.4, roadmap §3.4, §6.1 and FR-GW-04 all make audio the job of the core provider layer.
- **Decision.** Fleet OS uses FastAPI WebSockets (alongside the MQTT broker, Q-11) **only for connection and telemetry**; audio does not pass through Fleet OS (PRD §15 Q-47).
- **Consequences.** The device's audio WebSocket (binary Opus frames, PRD Appendix D.2) terminates at the self-hosted provider layer (FR-GW-04); a device can talk without a Fleet OS account (P-3); the Fleet OS store keeps decisions only (Q-6, NFR-PRIV-03); NeuroEdge does not sit in the token flow (N4).
- **Enforcement.** No code yet — `targets/esp32s3/audio/provider_client.c` (TSK-S5-06), `services/fleet/` (TSK-K2-04…09); [`15`](15-target-architecture.md) §3.1, §3.3.

## 3. Hardware, targets, simulation

### Q-2, Q-3 · One reference board and one memory budget
- **Decision.** ESP32-S3-BOX-3 is the only reference board (invariant 6). Budget: SRAM ≥ 120 KB and
  PSRAM ≥ 2 MB for the application, firmware ≤ 3.5 MB to fit A/B on 16 MB flash.
- **Enforcement.** `boards/esp32s3-box-3.toml`, `partitions.csv`, `scripts/check_firmware_size.py`.

### Q-8 · C on ESP-IDF for the chip, Python for the host
- **Consequences.** Two implementations of one spec ⇒ a normative spec and shared compliance vectors
  are mandatory.
- **Enforcement.** `test_c_walker.py`, `test_c_token.py`, `test_c_trace.py`; boot self-test.

### Q-13 · Three target tiers
- **Decision.** Tier 1 (`sim`, `linux`, `esp32s3`) keeps all commitments; tier 2 is maintained by the
  core team with narrower commitments; tier 3 is ported by the community and self-checked with the
  compliance suite.
- **Status.** A machine-readable tier table (`TARGET_TIERS`) is only proposed in RFC-0002; the code
  today has exactly three targets.

### Q-16, Q-21 · Layered simulation with proven open-source tools
- **Decision.** Do not write a simulator. One tool per layer: `SimHAL`, gpio-sim, `i2c-stub` + `lm75`,
  virtual framebuffer, LVGL golden images built on host, C compiled on host, Espressif QEMU; real
  boards for audio, display, memory. Renode and Wokwi are not used.
- **Enforcement.** `docs/spec/simulation_coverage.md`; jobs `linux-hal`, `ui-golden`, `firmware-qemu`.

### Q-22 · Software echo cancellation on `linux`
- **Decision.** `audio.in` reads PipeWire `module-echo-cancel`'s echo-cancelled source node; `audio.out`
  plays into its sink node as the reference signal. `linux-rpi5` declares `aec = true` only once
  measured.
- **Enforcement.** `hal/linux.py`, `pipewire/neuroedge-echo-cancel.conf`.

### Q-15 · Default input for sim
- **Context.** The first 10-minute journey (TTFV < 10 minutes, M1) requires developers to be able to test
  immediately after installation, uninterrupted by microphone setup, downloading models, or registering
  cloud API keys.
- **Decision.** The `sim` simulator defaults to typed text input (CLI or web UI) fed into the local
  command grammar matcher from Q-14: requiring absolutely no network, no API key, and executing
  deterministically. Voice and cloud STT are only optional when a key is present; on-chip speech
  recognition models (WakeNet/MultiNet/TFLite Micro) only belong to the `esp32s3` target (FR-DX-02).
  (PRD §15 Q-15).
- **Consequences.** The first run is deterministic, offline, and keyless (FR-DX-02); steps 2–4 of the
  10-minute journey adapt accordingly (PRD §2.3).
- **Enforcement.** `sim/`, `models/grammar.py`; sample grammars `fixtures/agents/*/commands.toml`.

## 4. Governance, licensing, schedule

### Q-11 · Allowed license list
- **Decision.** Allow MIT, BSD, Apache-2.0, ISC, PSF, CNRI-Python, MPL-2.0 (unmodified), Zlib,
  CC0-1.0; forbid GPL/LGPL/AGPL, SSPL, BSL. Hawkbit (EPL-2.0) is used unmodified as a service; **EMQX
  (BSL) is not used**.
- **Consequences.** `gpiod` (LGPL) is only an optional extra; the Fleet OS MQTT broker is chosen among
  Mosquitto, NanoMQ, VerneMQ.
- **Enforcement.** `scripts/check_licences.py`; jobs `cloud-extra`, `licence-obligations`.

### Q-45 · NeuroEdge's license
- **Decision.** Code under PolyForm Noncommercial 1.0.0; `schemas/`, `docs/spec/`, `fixtures/compliance/`
  under Apache-2.0 so anyone can implement the standard.
- **Enforcement.** `LICENSE`, `LICENSING.md`, `test_packaging.py`.

### Q-39 · Roadmap by increment
- **Decision.** One roadmap, measured in increments I0…I18 (adding I2a, I2b, I3a, I4a, I5a; dropping I12 and I15 — Q-52), each increment with one forecast date, one
  tag and one measurement signal; no external release before I6.
- **Enforcement.** `neuroedge-roadmap.md` §0.2; `test_plan_contract.py`.

### Q-38 · Not a certified safety function
- **Decision.** Temporarily OUT: no SIL, no PL; mobile robots must have a hardware emergency stop
  button.

### Q-6 · Fleet OS trace retention policy
- **Context.** Traces from the device fleet contain personal data (who opened the door and when);
  storage cost is not a constraint (~1.3 KB per session).
- **Decision.** Fleet Standard retains traces for 90 days; Fleet Enterprise retains them for 3 years.
  Traces sent to the store under FR-FLT-05 contain only decisions, no raw data (NFR-PRIV-03);
  retention periods are ceilings, not floors. Per-device quotas exist only to prevent runaway devices,
  not as a pricing lever (~23 GB/year for 1,000 devices × 50 sessions/day (estimated); PRD §15 Q-6).
- **Consequences.** The store holds only decisions, no raw data (NFR-PRIV-03); because traces still
  contain personal data (who opened the door and when), the retention period is a ceiling, not a floor.
- **Enforcement.** No code yet — Fleet OS trace store (TSK-K2-08, `services/fleet/trace_collector.py`,
  proposal §6.4); [`15`](15-target-architecture.md) §3.1.

## 5. Decisions for the expansion direction (no code yet)

| Code | Decision | Consequence when implemented |
|:---|:---|:---|
| Q-32 | Layered robotics after Developer Beta; multi-node traces extend `trace.v1` with optional fields | No `trace.v2` needed |
| Q-33 | **Context:** Layered robotics needs an independent node handling actuators/manipulators. **Decision:** RP2350 is the second reference node ported by the core team: C HAL on Pico SDK (`digital.out`, `sensor.read`), C99 walker and token ledger compiled for ARM, board profile, and real board test runner. | The core team takes on another long-term maintained target; an intentional exception to the exclusion catalog in PRD §14; reference board for v1.0 remains Box-3 (Q-2); [`15`](15-target-architecture.md) §4.3 |
| Q-34 | **Context:** Mobile robots need navigation and obstacle avoidance, but NeuroEdge does not redevelop SLAM/navigation itself. **Decision:** Native integration of ROS 2 and Nav2 via adapters at the gate boundary; gate evaluates every velocity command (`cmd_vel`), even when Nav2 is autonomously navigating. | Establishes a new mobile robot safety tier (10–20 Hz cycle gate, forbidden zones); requires a mobile robot safety RFC and survey of question C6 from robot buyers (Q-38, `TODOS.md` #40); [`15`](15-target-architecture.md) §4.3 |
| Q-35 | Every actuator declares its safe state on loss of communication; no declaration means stop | Needs an RFC for the declaration field |
| Q-36 | Zenoh-pico on the MCU, `zenohd` on the Pi; spike with pass/fail thresholds, micro-ROS is plan B | Node RFC draft |
| Q-37 | Time-limited lease tokens for `motion.*` (channel, maximum amplitude, short TTL), renewed through each gated command | Different from today's one-time token; needs RFC-0011 |
| Q-40 | **Context:** Multiple post-Beta expansion directions (NeuroBrain, layered robotics, vision, community ports) risk diluting core team resources without prioritization. **Decision:** Post-Beta expansion sequence anchored on dependencies: open target list (I11) → community porting kit (I13) → layered robotics (I14); ecosystem (I18) after I13 and Registry. *(Amended 2026-09-30: the NeuroBrain part is replaced by Q-55 — in the MVP at I4a, I5a; basic vision is replaced by Q-53 — in the MVP at I2a, I3a; I12 and I15 are no longer increments.)* | Protects the v1.0 critical path and V2 effort (R-7) — now per Q-52 by moving the date rather than cutting scope; [`15`](15-target-architecture.md) §4 |
| Q-52 | **MVP = the full v1.0**, one launch; if it slips the date moves, scope is not cut; four phases P0 → MVP → Beta and commercial → expansion (`neuroedge-prd.md` §15) | The roadmap adds I2a, I2b, I3a, I4a, I5a; acceptance A1–A12; planning assumes full staffing V1–V7 |
| Q-53 | Four extension primitive packs (sensors, PWM, vision, motion) mandatory on all three tier-1 targets, optional per board | Six RFCs (RFC-0007, RFC-0009 → RFC-0013); adds an ESP32-S3 camera board and the `sim-rpi5` profile |
| Q-54 | Vision enters the gate as maker-declared facts; the gate locks the confidence threshold with the `numeric` criterion | No vision-specific gate semantics; traces carry no raw images |
| Q-55 | NeuroBrain in the MVP on all three targets, covering the four primitive packs | I4a (host) and I5a (chip); replaces the NeuroBrain ordering of Q-40 |

## 6. RFCs

| RFC | Contract | Status | Implementation |
|:---|:---|:---|:---|
| [0001](../../rfc/0001-gate-schema-conditional-requirements.md) | `gate.v1`: conditionally required fields for inherited gates | Accepted, implemented | `schemas/gate.v1.json` |
| [0002](../../rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md) | Open the target list by tier | **Under discussion**; part of I11 | not yet |
| [0003](../../rfc/0003-bo-cuc-nhi-phan-cay.md) | Binary layout `NETR` v1 | Accepted, implemented | `binary_tree.py`, `ne_gate/` |
| [0004](../../rfc/0004-ke-thua-budget-on-block.md) | No loosening of `budget`, `on_block` on inheritance | Accepted, implemented | `gate_resolver.py` |
| [0005](../../rfc/0005-rang-buoc-tham-so-trong-gate.md) | Argument limits in the gate | Accepted, implemented | `arguments.py`, `NETR` argument record |
| [0006](../../rfc/0006-xac-nhan-ask-confirms.md) | `on_block.confirms` | Accepted, implemented | `confirmation.py`, `confirm_mask` |
| [0007](../../rfc/0007-digital-in-i2c-analog-in-phong-bi.md) | `digital.in`, read-only I2C bus, `analog.in`, envelope declaration in `board.v1` (TSK-N0-03). Read logic levels and scan lab bus without modifying `gate.v1` | Accepted (2026-10-01); host part implemented: `digital.in`, I2C, `analog.in`, envelope; `esp32s3` left | `hal/envelope.py`, `hal/i2c_bus.py`, `hal/__init__.py`, `board.v1` |
| [0008](../../rfc/0008-vet-ghi-chuan-muc-mang-gate-digest.md) | Three normative traces bearing `gate_digest` in `trace.v1` — verification replay. Prevents undetectable replay of traces on gates whose safety semantics have changed | Accepted, implemented | `fixtures/traces/`, `verify`, `replay` |
| [0009](../../rfc/0009-tieu-chi-so-numeric.md) | `numeric` criterion: `evaluate.type: numeric` in `gate.v1`, numeric comparison nodes in `NETR` and the C walker; lets gates check continuous numeric thresholds (pressure, temperature) rather than only enum `bool`/`level`/`choice` (TSK-W1-02, `TODOS.md` #30) | Accepted (2026-10-01), implemented | `engine/constraints.py`, `NETR` v2, `ne_walker.c` |
| [0010](../../rfc/0010-pwm-trong-digital-out.md) | PWM (frequency, pulse width) and a state-feedback channel in `digital.out` (TSK-W1-01) | Accepted (2026-10-01); host part implemented (branch `feat/pwm`); `esp32s3` left | `hal/pwm.py` |
| [0011](../../rfc/0011-nguyen-thuy-motion.md) | `motion.*` primitive (motor/servo), extended physical safety envelope, time-limited lease tokens (Q-37) and per-actuator safe states on loss of communication (Q-35) (TSK-W1-03) | Accepted (2026-10-01); host part implemented (branch `feat/motion`); `esp32s3` left | `hal/motion_core.py` |
| [0012](../../rfc/0012-nguyen-thuy-vision-in.md) | `vision.in` primitive with hardware parameters (`fps`, `modes[]`, enum `pixel_format`), `[requires]` matching rules (RFC-0002 §9.1) and the trace privacy rule (TSK-V1b-07) | Accepted (2026-10-01); host part implemented: model, trace, virtual camera, V4L2; inference golden and `esp32s3` left | `perception/vision/`, `sim/vision/`, `hal/v4l2.py` |
| [0013](../../rfc/0013-nguyen-thuy-tuy-chon-va-nhieu-bo-tham-chieu.md) | Board-optional extension primitives; several reference boards for one tier-1 target (TSK-I2a-07) | Accepted (2026-10-01); host part implemented; the `esp32s3` cells left (TSK-I3a-01) | `hal/board.py` (`REFERENCE_BOARDS`, `SIM_MIRRORS`), `verify` |

### Planned unnumbered RFCs (planned RFCs)

Each RFC below resolves an architectural bottleneck for expansion stages, opened by a specific task:

| Planned RFC | Capability and architectural purpose (Why needed) | Opening task | Stage |
|:---|:---|:---|:---|
| **RFC-node** | Specifies the multi-node coordination protocol on the wire (Zenoh-pico, Q-36), black channel structure, heartbeat-triggered safety on disconnect (Q-35), and multi-node trace unification in `trace.v1` (Q-32) | TSK-W3-02 | I14 |
| **RFC-pin-extends** | Enables pinning gate inheritance by content hash `@<ver>#sha256:…` in `gate.v1`, upgrading `digests.lock` into a lockfile for inheritance chains; defends against gate substitution attacks on public Registries (`TODOS.md` #11, #15) | TSK-S3-21 | I10 |
| **RFC visual-evidence gate semantics** | Defines dedicated gate semantics for visual evidence; until this RFC exists, vision enters the gate as maker-declared facts with the threshold locked by the `numeric` criterion (Q-54, `neuroedge-design-phase2.md` §2.2); prerequisite for multimodal gates | TSK-V3-04 | I17 |
| **RFC mobile-robot safety** | Safety framework for mobile robots: maximum speed limits, forbidden navigation zones, 10–20 Hz real-time gate cycle, ROS 2 / Nav2 control flow integration (Q-34), and question C6 from robot buyers (Q-38, `TODOS.md` #40) | TSK-W4-07 | I14 |

## 7. Making a new architecture decision

1. **The decision** is recorded in PRD §15 with a new `Q-N` code — the only place.
2. If it changes something in the `CONTRIBUTING.md` §3 list (schemas, resolution semantics, normative
   traces, locked gates, `NETR` layout) it needs an **RFC**: the first PR contains only the RFC file;
   the next PR cites the RFC number.
3. If it has architectural consequences, add an ADR entry to this page (context, decision,
   consequences, enforcement), citing the `Q-N` code — do not copy the decision text.
4. If it changes the dependency graph between packages, edit `ALLOWED` in
   `python/tests/test_architecture_layers.py` and the table in [`03`](03-component-host-c4l3.md) §2 in
   the same change.
