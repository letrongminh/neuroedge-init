# 13 · Evolution I0–I18: current state and plan

> **Scope:** how the architecture will grow across increments, what is already prepared, what needs an
> RFC. **Sources:** status, progress and forecast dates live only in roadmap §0.2 (Q-39) — this page
> does not copy them; figure E-09 is **generated from that very table**. The design of the expansion
> directions is in `neuroedge-design-neurobrain.md`, `neuroedge-design-phase2.md`,
> `draft-ke-hoach-mo-rong-robot-fofoca.md`, `draft-rfc-node-giao-thuc-dieu-phoi.md`.

## 1. The picture

![E-09 · Evolution](../assets/svg/E-09-evolution.svg)
*Figure E-09 — Nineteen increments, status, progress and forecast dates read from roadmap §0.2 when the figure is generated.*

The critical path (roadmap §2.2): boards arrive → memory spike (TSK-S1-10) → I3 → I5 → I6 → I7. The
demand gate (Q-20; date in roadmap §0.2) decides Go / Adjust / Stop for I3–I7.

## 2. What the architecture changes at each stage

| Stage | New container or component | Contract change | Today's architecture already prepares |
|:---|:---|:---|:---|
| **I0** Core on `sim` | Safety contract core: Action Contract Engine, `sim` + web UI, CLI, MCP server/host, System 2 via LiteLLM (Q-10); C walker, token ledger, and UART traces on QEMU ([`00`](00-overview.md)) → [`15`](15-target-architecture.md) §2.1 | — (project's frozen contract baseline) | 42/42 tasks completed; `gate.v1`, `trace.v1`, `board.v1` frozen; Action CI fully running on GitHub Actions |
| **I1** Internal preview | Developer experience: internal wheel package, TTFV < 10 minutes on `sim` (M1), traces hash user text at source by default (`--raw` to keep text, TSK-I1-01) | — (RFC-0008 pins `gate_digest` into three normative traces, 2026-09-27) | `sim/ui.py`, `neuroedge new` scaffold, `test_packaging.py` test suite, and `wheel-smoke` CI job |
| **I2** `linux` matches `sim` | `LinuxHAL` complete on par with `sim`: `run`, `record`, `mcp serve --target linux`; hwmon/IIO sensors, framebuffer display; nightly runner on Raspberry Pi 5 (TSK-I2-01) | — | `linux-hal` job verifies `LinuxHAL` on `gpio-sim`, `i2c-stub` + `lm75`, and `vkms`; `simulation_coverage.md` §2 |
| **I3** Gate on Box-3 | On-chip HAL (GPIO, I2C — TSK-S4-01, TSK-S4-03); nightly runner with real boards (TSK-S4-05) → [`15`](15-target-architecture.md) §2.1 | — | walker, token ledger, UART trace, component generated for the agent, boot self-test — all already run on QEMU; four C connection points ([`11`](11-hal-port-guide.md) §5) |
| **I4** Voice on host | Real-time voice session with real microphone; FSM state machine, wake word, AEC, barge-in, STT/TTS via cloud providers, Jev via System One API (Q-4, Q-12) | — | state machine, providers, `live` mic/speaker backend on `sounddevice` (`hal/linux.py`, only opens device); AEC via PipeWire per Q-22 when Pi nightly passes; `TODOS.md` #45 |
| **I5** Voice on Box-3 | On-chip audio path (I2S, AEC, VAD, Opus), audio streaming client, state machine in C/C++ (TSK-S5-03, Q-8) → [`15`](15-target-architecture.md) §2.2, §2.3 | — | the normative spec `voice_fsm.md` and a compliance vector suite shared by Python and C (Q-8) |
| **I6** Public | `neuroedge` package on PyPI and launch (repo already public since 2026-09-25, Q-45), public schema URLs (A9); voice demo video across 3 tier-1 targets | — | the schema `$id` is already `https://schema.neuroedge.dev/…`; the release workflow has CycloneDX SBOM and Sigstore attestation |
| **I7** v1.0 | Secure Boot, flash encryption, physical microphone switch (TSK-S6-05); achieves all criteria A1–A9 ([`neuroedge-prd.md`](../../../neuroedge-prd.md) §11.1) → [`15`](15-target-architecture.md) §2.4 | — | signed OTA and A/B dual-partition rollback already run on QEMU; `sdkconfig.ota` is a separate layer |
| **I8** Developer Beta | Feature freeze on `1.0.x` line, 50–100 external developers; measure metrics B1–B5, branch into 3 forks A/B/C ([`neuroedge-roadmap.md`](../../../neuroedge-roadmap.md) §5) → [`15`](15-target-architecture.md) §1, §3 | — (freeze new features on `1.0.x`; exceptions for blocker and safety bugs; RFCs, specs, CI still merge — roadmap §5.2) | — (TSK-S3-09 anonymous telemetry not started yet, part of I6; criteria for fork A are B1 and B2, Q-41) |
| **I9** Fleet OS | **New server-side container**: batched OTA rollout (Hawkbit EPL-2.0, Q-11), permissive-license MQTT broker, incident trace store (90-day / 3-year retention, Q-6), device identity provisioning (TSK-K2-04); **self-hosted provider layer** bundling a single endpoint/credential, multi-provider routing, and failover via `agent.toml` (TSK-K2-01→03, FR-GW, Q-28) → [`15`](15-target-architecture.md) §3.1, §3.3 | may add fields to the trace `metadata` (no RFC needed) | `metadata` accepts extra fields; `device_id` already exists; device-level OTA belongs to the core, campaigns to Fleet OS (proposal §6.4); provider interface `neuroedge.models.providers` (Q-10) and failover contract `SystemTwo(provider=…, fallback=…)` (Q-28) already left open |
| **I10** Gate Registry | **New container**: OCI store (ORAS, Harbor), usage metering (OpenMeter) → [`15`](15-target-architecture.md) §3.2 | sign gates and verify signatures on device (TSK-W2-04); pinning `extends` by digest needs an RFC (TSK-S3-21) | `neuroedge://` identifier, JCS digest, `gate publish`, `digests.lock`, `GateRegistry` is the backend-swap point |
| **I11** Open the target list | `TARGET_TIERS` tier table in core, `board validate` → [`15`](15-target-architecture.md) §4.1 | **RFC-0002**: `target` enum in two schemas (`board.v1`, `trace.v1`) | target list is closed in one place (`hal/board.py`, `schemas/`) |
| **I12** NeuroBrain | Building Physical AI by conversation (Q-31): gated lab-room actions, physical safety envelope in HAL, read-only I2C → [`15`](15-target-architecture.md) §4.2 | **RFC-0007**: `digital.in`, read-only I2C, envelope field in `board.v1` (`gate.v1` unchanged) | everything must go through `dispatch()` → gate (invariant B-1 of the NeuroBrain design) |
| **I13** Community port kit | compliance vectors packaged to run outside repo, `board check`, test framework for OEMs and community (Q-13, FR-TGT-08) → [`15`](15-target-architecture.md) §4.1, §4.5 | — | C99 core with no ESP-IDF dependency; port contract ([`11`](11-hal-port-guide.md) §2) |
| **I14** Layered robotics | Pi 5 as the brain, multiple MCU nodes (ESP32-S3 + RP2350 ported by core team, Q-33) each evaluating gates locally; Zenoh-pico communication (Q-36); ROS 2 / Nav2 integration with gate controlling all velocity commands (Q-34) → [`15`](15-target-architecture.md) §4.3 | RFC-node, RFC-motion (`motion.*`, time-limited lease tokens — Q-37, actuator safety — Q-35), RFC-numeric (`TODOS.md` #30), mobile robot safety RFC (TSK-W4-07) | multi-node traces extend `trace.v1` with optional fields (Q-32); pure gate reused on each node |
| **I15–I17** Vision | Vision HAL on `linux`, then `jetson` (tier 2); reuses vision stack from `neuroedge-design-phase2.md`: GStreamer and V4L2 (camera stream), ONNX Runtime and Ultralytics YOLO (models), HailoRT and Edge TPU (NPU), JetPack and TensorRT (`jetson`) → [`15`](15-target-architecture.md) §4.4 | RFC `vision.in` (TSK-V1b-07); RFC visual-evidence gate semantics (TSK-V3-04) | vision is an L2 input, never L3 authority: must be reduced by a `SystemOne` to `bool`/`level`/`choice` |
| **I18** Ecosystem | adapter store and HAL ports on Registry infrastructure, free hardware certification, self-verification (TSK-P2-03); complete C4 ecosystem landscape ([`16`](16-ecosystem-landscape.md)) → [`15`](15-target-architecture.md) §4.5 | — | `python:` adapter and port contract; open Apache-2.0 standards for `schemas/`, `docs/spec/`, `fixtures/compliance/` (Q-45) |

## 3. Variation points already in place

Places today's architecture has deliberately left open, so the stages above do not have to tear the
foundation up:

| Point | Where | Allows |
|:---|:---|:---|
| Fact source | the `FactSource` protocol (`engine/gate.py`) | adding a decision model, sensors, vision as fact sources without changing the engine |
| Model and speech providers | `models/providers/`, `perception/providers/`, the `python:` adapter | swapping provider by configuration |
| HAL | the `HardwareAbstractionLayer` subclass + `boards/` profiles | new targets (after RFC-0002) |
| Backend registry | `GateRegistry` (`gate_resolver.py`) — the docstring says plainly it will be replaced by OCI lookup | the Gate Registry (I10) |
| Trace events | `type` is a free string in `trace.v1`; `metadata` accepts extra fields | new events, multi-node traces, with no need for `trace.v2` |
| Firmware config layers | layered `SDKCONFIG_DEFAULTS` | enabling a feature per board without branching code |
| The tree on the device | `NETR` has `layout_version` | layout v2 when needed (for example carrying gate labels — `TODOS.md` #36); the v1 walker refuses v2 instead of misreading it |

## 4. Known architecture debt

Each item is a deliberate choice, with a trigger milestone in `TODOS.md`:

| Debt | Why accepted today | `TODOS.md` |
|:---|:---|:---|
| Traces are not signed | needs device keys; belongs to Fleet OS | #1 |
| The token is an in-memory `(nonce, digest)`, not signed | the in-scope threat is skipping by mistake | #2 |
| `extends` is not pinned by digest yet | no registry yet; `digests.lock` covers CI | #15 |
| The Gated Tool Profile is not frozen into `schemas/` yet | no outside client uses it yet | #23 |
| An MCP connection lives for one turn only | one event loop per REPL turn | #25 |
| No numeric criteria in gates yet | needs an RFC; `bands` suffice for the current samples | #30 |
| `NETR` v1 carries no gate labels and no `on_block` text | the tree is linked with the firmware so it cannot drift | #36 |
| Pin command operation and duration on chip come from a table built on host | how an action runs on the MCU is not settled yet | #37 |
| `linux` sensor reads block the event loop | no agent both speaks and reads sensors yet | #48 |
