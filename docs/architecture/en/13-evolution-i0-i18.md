# 13 · Architecture evolution by release milestone

> **Scope:** how the architecture grows across ten user-facing release milestones, what is already prepared,
> what needs an RFC. **Sources:** the ten milestones and increments for each milestone in roadmap §0.5 ("Ten
> user-facing release milestones"); status, progress, and forecast dates live only in roadmap §0.2 (Q-39) — this page does not copy
> them, and Figure E-09 is **generated from those very two tables**. The design of expansion directions is in
> `neuroedge-design-lab-mcp.md`, `neuroedge-design-phase2.md`, `draft-ke-hoach-mo-rong-robot-fofoca.md`,
> `draft-rfc-node-giao-thuc-dieu-phoi.md`.

## 1. One spine, ten milestones

NeuroEdge grows in **breadth**, not by **exceptions**. Each milestone adds a place where the gate runs (Pi, chip,
multi-node), a type of thing the gate guards (sensors, PWM, cameras, motors), or a way to call in (voice,
conversation, network MCP, third-party bridges). No milestone adds a path to hardware without passing through the gate. That is the product
spirit in [`00`](00-overview.md) §1.1, written into architectural law: **the architecture may widen, but the
execution spine `dispatch()` → gate → token → HAL → trace may not shorten.**

Therefore, each milestone in §3 answers four questions in the same order: what the user can do, what the architecture adds,
which contracts change, and **which safety promise is proven again** on the new scope.

![E-09 · Evolution](../assets/svg/E-09-evolution.svg)
*Figure E-09 — Ten release milestones, each grouping its increments; status, progress, and forecast dates
read from roadmap §0.2 when the figure is generated.*

Milestone 6 (**public launch**) is the first time outsiders can use it; Milestone 7 (**v1.0**) is the first time it is reliable enough to
ship in commercial devices. The MVP is the full v1.0, a single launch: if it slips the date moves, scope is not cut (Q-52).
The critical path (roadmap §2.2): boards arrive → memory spike (TSK-S1-10) → Milestone 3 → Milestones 4 and 5 on chip → Milestone 6 →
Milestone 7. The CPO Dashboard (`docs/business/cpo-dashboard.html`) reads the same milestone table.

## 2. What does not change across any milestone

This is the part that **must not evolve**. Each new milestone must prove these exact propositions again on
its scope; the last column is the milestone where proof becomes the hardest.

| Product promise | Architectural mechanism | Evidence | Hardest at milestone |
|:---|:---|:---|:---|
| No command reaches hardware without a gate | One single path `dispatch()` → `c.do()` → gate → single-use token → HAL; the only exception is safe-state commands (Q-62) | `docs/spec/threat_model.md` §1–§2b; tests blocking each shortcut | 4 (barge-in), 10 (multi-node) |
| When unsure, do not act | Fail-closed in every direction (invariant 2); stale, missing, or mistyped facts ⇒ `BLOCK` | `fixtures/traces/network_offline.json`; counterexample corpus | 2 (sensors, camera), 3 (offline on chip) |
| One contract everywhere | Same gate file, pure resolution (invariant 4); Python and C share the same spec; `verify` compares verdicts | [`10`](10-target-equivalence.md); `neuroedge verify --targets sim,linux,esp32s3` | 3 (real chip), 10 (community boards) |
| Evidence over promises | Every verdict into the trace `trace.v1`; replay recomputes without calling the model | [`06`](06-runtime-flows.md) §7; Action CI | 5 (client-written drafts), 9 (field traces) |
| Humans hold the final authority | Models and MCP clients cannot confirm `ask` (Q-26); drafts an MCP client writes through NeuroEdge Lab must be approved by a human (Q-71); no one can confirm in place of a measurement (Q-62) | `confirms` tests; RFC-0006, RFC-0009 | 5 (build by conversation) |
| Plug into other stacks | MCP is the caller surface; models and voice are replaceable providers (P-4); schemas, specifications, compliance test suite and compliance corpus under Apache-2.0 (Q-45, Q-67); from I2c, third parties wire themselves in through `neuroedge.sdk` plug points without touching the core, and the safety invariants do not change (Q-67) | `docs/spec/tool_calling.md`; `fixtures/tool_calls/`; plug-in compliance suite (I2c, `planned`) | 2 (open platform, Q-67), 6 (network MCP, Q-58) |

## 3. Architecture across milestones

The `done` / `partial` / `planned` labels follow the convention in [`README.md`](../README.md); detailed status for each
increment is in roadmap §0.2.

### Milestone 1 — Try it on a laptop *(I0, I1)*

- **What the user can do:** install one package, run a gated agent on `sim` in under 10 minutes; no hardware,
  no accounts, no API keys (M1).
- **What the architecture adds:** safety contract core — Action Contract Engine, `sim` with local web UI, CLI, MCP
  server and host, System 2 via LiteLLM (Q-10); C walker, token ledger, and UART traces on QEMU; NeuroEdge
  Studio (Q-51); traces hash user text at source by default (TSK-I1-01) `done`. Internal wheel package and
  TTFV measurement `partial`.
- **Contracts:** `gate.v1`, `trace.v1`, `board.v1` frozen — all subsequent milestones build on them; RFC-0008 pins
  `gate_digest` into three normative traces.
- **The promise is proven by:** three normative traces replay in CI; `wheel-smoke` runs the complete journey
  from the installed package.

### Milestone 2 — Real devices on a Raspberry Pi *(I2, I2a, I2b, I2c)*

- **What the user can do:** wire a kit (light, door, fan, sensor, camera, motor) to a Pi 5; same agent, same
  gate as on the laptop; connect another vendor's product (Muse, Home Assistant, an existing MCP server)
  through a plug-in and a proxy.
- **What the architecture adds:** `LinuxHAL` on par with `sim` — `run`, `record`, `mcp serve --target linux`,
  hwmon/IIO sensors, framebuffer display `done` on virtual hardware; nightly on Pi 5 `planned`. **Four board-optional
  primitive packs** (Q-53): sensors (`digital.in`, read-only I2C, `analog.in`, `numeric` criterion),
  fine control (PWM), vision (`vision.in`), motion (`motion.*`); **safety envelope** becomes a shared mechanism
  for all actuators; `sim-rpi5` profile; five sample kits and `neuroedge add` → [`15`](15-target-architecture.md)
  §2.1, §4.2, §4.4. On `sim` and `linux` (gpio-sim, `i2c-stub`, `vivid` in job `linux-hal`): the safety envelope, `digital.in`, read-only I2C, `analog.in`, vision, the `numeric` criterion and `NETR` v2, the `sim-rpi5` profile, the five sample kits, the gate library and `neuroedge add` are `done` (kits not yet built on real hardware, `TODOS.md` #59); PWM and `motion.*` are `done` on `sim`, on `linux` so far only against a fake sysfs tree. Still `planned`: `verify` replaying the `fan-pwm` and `rover` agents, real PWM channels and actuators, a camera lost mid-session on the kernel, the vision inference golden, the `esp32s3` cells (I3a). **I2c — Open platform** (Q-67; depends on I2b, graph in roadmap §2.1; **I11 —
  opening the target list — has been merged into I2c**): a third party wires NeuroEdge to a new product in a few
  commands, without touching the core and without waiting for the core team. The safety core is usable on its
  own through `neuroedge.guard` (no `agent.toml`, `@action` or `SimSession` needed); the Extension SDK
  `neuroedge.sdk` with six plug-in kinds through entry points — bridge, fact source, actuator, board, template,
  exporter — and a per-kind compliance suite (`neuroedge conformance`); two universal proxies,
  `neuroedge proxy mcp` and `proxy http`; remote actuators with a declared self-off level, Home Assistant first;
  `--board <path>` for out-of-repo community boards and an open, tiered target list (RFC-0002); a community
  index for `plugin search/install`. I4a, I6, I13, I14 and I16 depend on I2c →
  `neuroedge-design-open-platform.md`, [`16`](16-ecosystem-landscape.md) §3, §8. `planned`; the RFC-0002
  signature and the switch of the compliance corpus to Apache-2.0 are `done` (2026-10-04).
- **Contracts:** six RFCs approved (2026-10-01): RFC-0007, RFC-0009 → RFC-0013 — `board.v1` receives new
  blocks; `gate.v1` receives the `numeric` criterion; `NETR` v2 pins bytes in RFC-0009 §3d. For I2c: RFC-0002
  signed (2026-10-04); RFC-0016 (standalone core and Extension SDK), RFC-0017 (namespaced `source`,
  `bridge:<id>`) and RFC-0018 (remote actuators) are accepted (Q-68); the RFC-0014 code (facts from
  an external process) is pulled forward into I2c; `neuroedge.sdk` has its own version and stability promise,
  stricter than the package's `0.x`; the compliance corpus (`fixtures/tool_calls/`, `fixtures/contracts/`,
  `fixtures/traces/`, `fixtures/agents/`) is under Apache-2.0 (`LICENSING.md`).
- **The promise is proven by:** safe-state commands are never blocked; all `digital_out` pins default
  to actuators and have envelopes persisted across reboots; auto-off at
  `min(command duration, max_continuous_ms)`; out-of-process watchdog when runtime hangs (RFC-0007 §9); visual
  evidence evaluated frame-by-frame then ANDed, frozen camera ⇒ `BLOCK` (RFC-0012). For plug-ins: a bridge has
  only `dispatch(ToolCall)` and no HAL handle, a fact source cannot declare the age of its own facts, an
  actuator can be driven by the HAL only after a token and the envelope (FR-EXT-03), each with a counterexample
  the compliance suite catches; a proxy is worth something only when it is the only path to its target
  (`plugin doctor` warns when the target is still reachable without the proxy); remote actuators declare a
  self-off level, and an irreversible action needs a level the device can reach on its own even when contact is
  lost (RFC-0018 §7); the `neuroedge-muse` bridge is written in its own repository with no core line changed
  (A13).

### Milestone 3 — The gate on a $5 chip *(I3, I3a)*

- **What the user can do:** flash the agent onto ESP32-S3 (Box-3 and M5Stack CoreS3 — Q-61); the gate decides right
  on the chip, still blocking correctly when offline.
- **What the architecture adds:** on-chip HAL (GPIO, I2C — TSK-S4-01, TSK-S4-03); nightly runner with real boards
  (TSK-S4-05); four primitive packs on the chip, envelope enforced in firmware from a `const` table in
  flash → [`15`](15-target-architecture.md) §2.1. Walker, token ledger, UART trace, generated component for
  the agent, self-test and LVGL UI `done` on QEMU and host; everything on silicon `planned`.
- **Contracts:** unchanged — chip reads the exact contracts from milestones 1 and 2; v1 walker rejects v2 trees instead of
  misreading them.
- **The promise is proven by:** `verify` across three targets on each reference board (RFC-0013 §3f); memory
  spike against Q-3 thresholds, decision rules settled before measuring (Q-44).

### Milestone 4 — Talk to the device *(I4, I5)*

- **What the user can do:** issue voice commands on laptop, Pi and chip; barge-in cancels unexecuted commands.
- **What the architecture adds:** five-state conversation state machine, wake-word, STT/TTS via providers, Jev via
  System One API (Q-4, Q-12); `run --mic` on laptop `done`; AEC via PipeWire (Q-22) and live sessions on Pi
  `planned`; on-chip audio path (I2S, AEC, VAD, Opus) and C state machine (TSK-S5-03, Q-8)
  `planned` → [`15`](15-target-architecture.md) §2.2, §2.3.
- **Contracts:** `docs/spec/voice_fsm.md` is the normative specification for both implementations; shared
  compliance vector suite.
- **The promise is proven by:** physical command revocation contract (`voice_fsm.md` §5) — barge-in revokes
  undelivered commands in ≤ 1 audio frame; `motion.*` stops immediately (Q-57).

### Milestone 5 — Build by conversation *(I4a, I5a)*

- **What the user can do:** describe a device in words to the AI they already use (Claude Code, Claude Desktop);
  the AI writes actions, gates, and envelopes through NeuroEdge Lab's tools; NeuroEdge checks them; a human approves
  before locking (Q-55, Q-71).
- **What the architecture adds:** isolated `lab/` package with no LLM loop — gated acting tools, tools to build
  and check draft contracts (`neuroedge lab check`, rerun in Action CI), Lab Monitor, event-driven triggers — on host, then lab actions, gates, and envelopes on chip (block N7) →
  [`15`](15-target-architecture.md) §4.2. `planned`.
- **Contracts:** `gate.v1` unchanged; `motion.*` drafts must declare an envelope and safe state, `lab check` refuses
  them if missing.
- **The promise is proven by:** every acting call from the client still goes through `dispatch()` → gate; drafts are
  only locked after `lab check`, `gate lint` and human review; no tool locks policy; the model never confirms on its
  own; a client with a shell does not hold device permissions (`threat_model.md` §2c).

### Milestone 6 — Public launch *(I6)*

- **What the user can do:** anyone can `pip install neuroedge`; call devices from Claude, Home Assistant, or an
  agent framework via authenticated MCP. **First time outsiders can use it.**
- **What the architecture adds:** package on PyPI with SBOM and attestation; schemas at public URLs `schema.neuroedge.dev`
  (A9); **integration surface** (Q-58): network MCP — Streamable HTTP, OAuth 2.1, per-device mTLS, disabled by default
  (TSK-P2-04) — and Gated Tool Profile frozen into `schemas/` (TSK-I6-05); a **public Python API** with a written
  spec and versioning (TSK-I6-06, Q-63). `partial`: secret scanning, SBOM, authenticated network MCP (not yet tried across two machines), the integrator contracts in `schemas/` (RFC-0015) and the public Python surface `done`; PyPI and schemas at public URLs `planned`.
- **Contracts:** envelope schemas for `ToolCall` and results, a schema-version identifier for `board.v1`, and the error-code
  catalogue go into `schemas/` via RFC; from here other OSS can implement
  the profile under Apache-2.0 without depending on PolyForm NC code (Q-59).
- **The promise is proven by:** clients on other machines still only send *requests*; missing authentication ⇒ rejected;
  enabling network port without auth configuration ⇒ refuses to start; repeating a call N times ⇒ N times `BLOCK`.

### Milestone 7 — v1.0: ready to ship in products *(I7)*

- **What the user can do:** signed firmware update, lock device, 24-hour stable run; satisfies acceptance
  criteria A1–A13 (PRD §11.1).
- **What the architecture adds:** Secure Boot, flash encryption, anti-rollback eFuses, physical microphone switch (TSK-S6-05)
  `planned`; signed OTA and A/B dual-partition rollback `done` on QEMU → [`15`](15-target-architecture.md) §2.4.
- **Contracts:** unchanged; `sdkconfig.ota` is a separate configuration layer.
- **The promise is proven by:** third parties implement the standard from public schemas (A9); 10 outsiders
  install from PyPI (A1); 5 people build kits (A12); a third party wires up a new ecosystem in ≤ 1 day with no
  core line changed (A13).

### Milestone 8 — Developer Beta *(I8)*

- **What the user can do:** 50–100 external developers in real use on the `1.0.x` line.
- **What the architecture adds:** no added features; anonymous, opt-out telemetry (TSK-S3-09, from milestone 6) measuring B1–B5.
- **Contracts:** feature freeze on `1.0.x` — blocker and safety bugs only (R12); RFCs, specifications, CI still
  merge.
- **The promise is proven by:** real metrics, not assumptions, decide commercial direction (decision forks,
  roadmap §5.6; Q-41).

### Milestone 9 — Run a fleet *(I9, I10)*

- **What the user can do:** update thousands of devices in batches, pull incident traces remotely, share gates
  via a signed registry.
- **What the architecture adds:** **first server-side containers.** Fleet OS: batched OTA rollout (Hawkbit, Q-11),
  permissive-license MQTT broker, incident trace store (Q-6), device identity provisioning (TSK-K2-04), self-hosted
  provider layer bundling endpoints and failover (TSK-K2-01→03, Q-28). Gate Registry: OCI store (ORAS,
  Harbor), usage metering (OpenMeter) → [`15`](15-target-architecture.md) §3.1–§3.3. `planned`.
- **Contracts:** new fields in trace `metadata` (no RFC needed); sign gates and verify signatures on the device
  (TSK-W2-04); pinning `extends` by digest (TSK-S3-21) has been pulled forward into I2c — an RFC, then code (Q-67).
- **The promise is proven by:** device-level OTA remains with the core, campaigns belong to Fleet OS (proposal
  §6.4) — services never sit on the gate's decision path; 1,000 devices, 0 bricks (M5).

### Milestone 10 — Grow the ecosystem *(I13, I14, I16, I17, I18)*

- **What the user can do:** community ports new boards independently; Pi 5 robot with multiple MCU nodes; Jetson; voice
  together with vision.
- **What the architecture adds:** port kit with compliance vectors running outside the repo (Q-13), built on the
  target tiers `TARGET_TIERS` and `board validate` (RFC-0002) — formerly I11, now merged into I2c (Q-67,
  milestone 2); layered robotics — each node evaluates gates locally, Zenoh-pico (Q-36),
  loss of communication reverts to safe state per actuator (Q-35), gated ROS 2 / Nav2 (Q-34); Tier 2 `jetson`;
  free hardware certification, self-verification (the SDK and the "NeuroEdge-gated" certification have moved up
  to I2c) → [`15`](15-target-architecture.md) §4, [`16`](16-ecosystem-landscape.md). `planned`.
- **Contracts:** RFC-node, mobile robot safety RFC (TSK-W4-07); multi-node traces via optional fields
  (Q-32). RFC-0002 (`target` enum) is no longer at this milestone — signed 2026-10-04, its code moved into I2c (milestone 2).
- **The promise is proven by:** on-device gates, no centralized gate, even when the system spans multiple chips;
  black channel does not trust transport; mobile robots strictly require a hardware emergency stop button (Q-38).

## 4. Variation points already in place

Places today's architecture has deliberately left open, so the stages above do not have to tear the
foundation up:

| Point | Where | Allows |
|:---|:---|:---|
| Fact source | the `FactSource` protocol (`engine/gate.py`) | adding a decision model, sensors, vision as fact sources without changing the engine |
| Model and speech providers | `models/providers/`, `perception/providers/`, the `python:` adapter | swapping provider by configuration |
| HAL | the `HardwareAbstractionLayer` subclass + `boards/` profiles | new targets (RFC-0002 signed; its code is in I2c) |
| Backend registry | `GateRegistry` (`gate_resolver.py`) — the docstring says plainly it will be replaced by OCI lookup | the Gate Registry (I10) |
| Trace events | `type` is a free string in `trace.v1`; `metadata` accepts extra fields | new events, multi-node traces, with no need for `trace.v2` |
| Firmware config layers | layered `SDKCONFIG_DEFAULTS` | enabling a feature per board without branching code |
| The tree on the device | `NETR` has `layout_version` | layout v2 (RFC-0009 §3d: `numeric` table, gate labels) implemented in TSK-W1-02; the walker refuses any other layout instead of misreading it |

## 5. Known architecture debt

Each item is a deliberate choice, with a trigger milestone in `TODOS.md`:

| Debt | Why accepted today | `TODOS.md` |
|:---|:---|:---|
| Traces are not signed | needs device keys; belongs to Fleet OS | #1 |
| The token is an in-memory `(nonce, digest)`, not signed | the in-scope threat is skipping by mistake | #2 |
| `extends` is not pinned by digest yet | no registry yet; `digests.lock` covers CI; scheduled in I2c (TSK-S3-21, Q-67) | #15 |
| An MCP connection lives for one turn only | one event loop per REPL turn | #25 |
| Pin command operation and duration on chip come from a table built on host | how an action runs on the MCU is not settled yet | #37 |
| `linux` sensor reads block the event loop | no agent both speaks and reads sensors yet | #48 |
