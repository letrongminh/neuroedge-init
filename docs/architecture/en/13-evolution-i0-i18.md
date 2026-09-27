# 13 · Evolution I0–I18: current state and plan

> **Scope:** how the architecture will grow across increments, what is already prepared, what needs an
> RFC. **Sources:** status, progress and forecast dates live only in roadmap §0.2 (Q-39) — this page
> does not copy them; figure E-09 is **generated from that very table**. The design of the expansion
> directions is in `neuroedge-roadmap-phase1-5.md`, `neuroedge-roadmap-phase2.md`,
> `draft-ke-hoach-mo-rong-robot-fofoca.md`, `draft-rfc-node-giao-thuc-dieu-phoi.md`.

## 1. The picture

![E-09 · Evolution](../assets/svg/E-09-evolution.svg)
*Figure E-09 — Nineteen increments, status, progress and forecast dates read from roadmap §0.2 when the figure is generated.*

The critical path (roadmap §2.2): boards arrive → memory spike (TSK-S1-10) → I3 → I5 → I6 → I7. The
demand gate on 2026-10-25 (Q-20) decides Go / Adjust / Stop for I3–I7.

## 2. What the architecture changes at each stage

| Stage | New container or component | Contract change | Today's architecture already prepares |
|:---|:---|:---|:---|
| **I3** Gate on Box-3 | On-chip HAL (GPIO, I2C); the nightly runner has a board | — | walker, token ledger, UART trace, component generated for the agent, boot self-test — all already run on QEMU; four C connection points ([`11`](11-hal-port-guide.md) §5) |
| **I4** Voice on host | A real-time voice session with a real microphone | — | state machine, providers, `live` mic/speaker backend (only opens the device); `TODOS.md` #45 |
| **I5** Voice on Box-3 | On-chip audio path (I2S, AEC, VAD, Opus), audio streaming client, state machine in C | — | the normative spec `voice_fsm.md` and a compliance vector suite shared by Python and C (Q-8) |
| **I6** Public | Schemas at public URLs; PyPI | — | the schema `$id` is already `https://schema.neuroedge.dev/…`; the release workflow has SBOM and attestation |
| **I7** v1.0 | Secure Boot, flash encryption, microphone switch (TSK-S6-05) | — | signed OTA and rollback already run on QEMU; `sdkconfig.ota` is a separate layer |
| **I9** Fleet OS | **New server-side container**: batched OTA rollout (Hawkbit), permissive-licence MQTT broker, incident trace store, device identity | may add fields to the trace `metadata` (no RFC needed) | `metadata` accepts extra fields; `device_id` already exists; device-level OTA belongs to the core, campaigns to Fleet OS (proposal §6.4) |
| **I10** Gate Registry | **New container**: OCI store (ORAS, Harbor), metering (OpenMeter) | sign gates and verify signatures on the device (TSK-W2-04); pinning `extends` by digest needs an RFC (TSK-S3-21) | the `neuroedge://` identifier, JCS digest, `gate publish`, `digests.lock`, `GateRegistry` is the backend-swap point |
| **I11** Open the target list | the tier table `TARGET_TIERS` in the core, `board validate` | **RFC-0002**: the `target` enum in the two schemas | the target list is closed in one place (`hal/board.py`, `schemas/`) |
| **I12** NeuroBrain | gated lab-room actions, a physical safety envelope in the HAL, read-only I2C | **RFC-0007**: `digital.in`, read-only I2C, envelope fields in `board.v1` | everything must go through `dispatch()` → gate (invariant B-1 of the NeuroBrain design) |
| **I13** Community port kit | compliance vectors packaged to run outside the repo, `board check` | — | a C99 core with no ESP-IDF dependency; the port contract ([`11`](11-hal-port-guide.md) §2) |
| **I14** Layered robot | Pi as the brain, many MCU nodes each evaluating its own gate; Zenoh-pico wire | RFC-node, RFC-motion (`motion.*`, time-limited lease tokens — Q-37), numeric criteria (`TODOS.md` #30) | multi-node traces extend `trace.v1` with optional fields (Q-32); the pure gate is reused on each node |
| **I15–I17** Vision | a vision HAL on `linux`, then `jetson` | RFC `vision.in`; RFC on the semantics of visual evidence | vision is an L2 input, never L3 authority: a `SystemOne` must reduce it to `bool`/`level`/`choice` |
| **I18** Ecosystem | a store of adapters and HAL ports on top of the Registry infrastructure | — | the `python:` adapter and the port contract |

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
