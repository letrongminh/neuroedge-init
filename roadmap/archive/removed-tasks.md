# Removed Tasks — Archive

Task rows removed from the roadmap. They are kept so that code, documents and history that cite a task
code still resolve (roadmap §2.4 R8); none of them is planned. Re-opening any of them needs a new `Q-N`
that moves the row back into an increment of `roadmap/neuroedge-roadmap.md`. Every status is ⏸.

## Removed by Q-92 (2026-10-19)

The lean path to the public launch (PRD §15 Q-92) removed the demand gate milestone and four I2e tasks.

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I2e-06** | BOM with affiliate links located on separate page outside kit (`docs/spec/blueprint.md` BL-KT-02) | FR-BP-07 | team lead + V3 | ⏸ Cut by Q-92 (2) — was: Not started | `docs/user/` |
| **TSK-I2e-12** | Home Assistant add-on running runtime, zero CLI commands (Q-74) | FR-DX-02, FR-AGT-01 | V3 | ⏸ Cut by Q-92 (2) — was: Awaiting TSK-I2d-16 | external add-on repository |
| **TSK-I2e-13** | SD card image for Pi, Telegram pairing via QR code that opens the approval bot; the one-time pairing code is shown only on the home machine, never in the QR (Q-74, Q-89) | FR-DX-02, FR-CH-03 | V3 | ⏸ Cut by Q-92 (2) — was: Awaiting TSK-I2d-12 | `scripts/` · `docs/user/` |
| **TSK-I2e-14** | `neuroedge new --layout host+mcu`: project scaffold for Pi + ESP32 (Q-75) | FR-DX-01, FR-BP-02 | V3 | ⏸ Cut by Q-92 (2) — was: Not started | `python/neuroedge/templates/` |
| **TSK-I2e-10** | Interviews for gate: ≥ 10 people (≥ 5 makers) | — | team lead | ⏸ Removed with the demand gate, Q-92 (1) — was: Gate milestone, 2026-12-06 (Q-90) — not started | `docs/business/` |
| **TSK-I2e-11** | 8-week demand gate (B6, B7, B8), record branch point | — | team lead + product owner | ⏸ Removed with the demand gate, Q-92 (1) — was: Gate milestone, 2026-12-06 (Q-90) — not started | `roadmap/neuroedge-prd.md` §15 |

## Removed by Q-77 (2026-10-12)

One row per task is preserved so code and docs cross-references remain traceable; status reflects final state prior to Q-77.

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S2-07** | Canonical specification of conversational state machine | FR-PER-02, FR-PER-03 | V1 | ⏸ Removed from roadmap (Q-77) — completed 2026-09-25 | `docs/spec/voice_fsm.md` |
| **TSK-S3-10** | Compliance test vector suite for voice FSM | FR-CI-07, FR-TGT-04 | V1 | ⏸ Removed from roadmap (Q-77) — completed 2026-09-25 | `fixtures/compliance/voice/` |
| **TSK-S3-11** | Python implementation of conversational state machine | FR-PER-02→05 | V1 | ⏸ Removed from roadmap (Q-77) — completed 2026-09-25 | `python/neuroedge/perception/` |
| **TSK-S3-13** | ASR/TTS cloud provider integration for `sim` and `linux` | FR-MDL-09, FR-PER-07 | V1 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/perception/providers/` |
| **TSK-S5-08** | `audio.in` / `audio.out` on `linux` via PipeWire/sounddevice | FR-TGT-02, FR-PER-01 | V2 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/hal/linux.py` |
| **TSK-I4-01** | Local command fallback and host wake-word | FR-PER-01, FR-MDL-03 | V1 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/perception/providers/wake.py` |
| **TSK-I4-02** | Configurable `SystemOne` swap | FR-MDL-04 | V1 | ⏸ Removed from roadmap (Q-77) — completed 2026-09-26 | `python/neuroedge/models/providers/systemone_api.py` |
| **TSK-I4-03** | Per-leg latency and System 1 / System 2 ratio in traces | FR-ACE-06, FR-TEL-03, NFR-OBS-02 | V1 | ⏸ Removed from roadmap (Q-77) — completed 2026-09-26 | `python/neuroedge/engine/latency.py` |
| **TSK-I4-04** | Real-time live voice session on laptop (`run --mic`) | FR-PER-01, FR-PER-02, FR-PER-07 | V1 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/hal/audio_live.py` |
| **TSK-N0-01** | Q-71 entry for NeuroEdge Lab via MCP | — | V2 | ⏸ Removed from roadmap (Q-77) — completed 2026-10-10 | `neuroedge-prd.md` §15 |
| **TSK-N0-04** | Threat model update for lab actions and MCP | NFR-SEC-09 | V2 | ⏸ Removed from roadmap (Q-77) — completed 2026-10-10 | `docs/spec/threat_model.md` §2c |
| **TSK-N0-05** | Approval workflow for `-draft` draft gates via PR | FR-GATE-* | V2 | ⏸ Removed from roadmap (Q-77) | `CONTRIBUTING.md` §3 |
| **TSK-N0-06** | Extend Q-11 for OFL-1.1 fonts and IBM Plex NOTICE entry | — | V2 | ⏸ Removed from roadmap (Q-77) | `neuroedge-prd.md` Q-11 · `NOTICE` |
| **TSK-N1-01** | `lab_pulse` sample action + gate limiting `duration_ms ≤ 2000` | FR-MDL-10 | V2 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-N1-03** | `neuroedge build --release` rejects when `[lab] enabled` | FR-CLI-02 | V2 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/cli/main.py` |
| **TSK-N1-06** | `board show --lab` and `lab_board` tool verifying pin allow-list | FR-HAL-05 | V2 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/cli/main.py` |
| **TSK-N1-07** | B-1 boundary test scanning AST forbidding `lab/` from calling HAL | — | V2 | ⏸ Removed from roadmap (Q-77) | `python/tests/test_lab_boundary.py` |
| **TSK-N1-08** | `lab_read` on `digital.in` primitive | FR-HAL-01 | — | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-N3-01** | Bus scan via read-byte, read chip ID, no heuristics | FR-HAL-01 | — | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/hal/` |
| **TSK-N3-02** | I2C test on `i2c-stub` + `lm75`: device, NACK, timeout | FR-TGT-02 | — | ⏸ Removed from roadmap (Q-77) — in progress: chip detected passed; empty bus remaining | `python/tests_linux/test_i2c_read.py` |
| **TSK-N4-01** | Workbench notebook recording pin roles and chip IDs | — | — | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-N4-02** | `lab_board_draft` tool accepting new board profiles | FR-HAL-05 | — | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/hal/board.py` |
| **TSK-N4-03** | MCU-specific pin warnings (strapping, flash, PSRAM) | — | — | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-N5-04** | Draft PR prints verbal `gate explain` alongside diff | — | — | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-N5b-01** | Queue oldest asks first, default focus on Cancel | — | — | ⏸ Removed from roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-02** | SSE disconnection displays yellow banner, dims devices | — | — | ⏸ Removed from roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-03** | Active pins display remaining duration, per-pin timeline | — | — | ⏸ Removed from roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-04** | Color envelope ruler by window percentage from `board.v1` | — | — | ⏸ Removed from roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-05** | 4-color badge verdict cards, click opens `gate explain` | — | — | ⏸ Removed from roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-06** | Tab titles flag pending confirmations, rewind preserves active ask/live state | — | — | ⏸ Removed from roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-07** | Restyle full sim page, bundle IBM Plex font | — | — | ⏸ Removed from roadmap (Q-77) | `viz/assets/ui.css` |
| **TSK-I4a-01** | NeuroEdge Lab covering four packages for MCP clients | FR-MDL-10, FR-DX-01 | V2 + V7 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-I2d-18** | Lab loop ① for mission contracts via MCP tools (`docs/spec/missions.md` MS-LB-01) | FR-DX-10, FR-MSN-13 | V7 | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/lab/` |
| **TSK-N1-02** | `[lab] enabled` flag in `agent.toml`, off by default | — | V2 | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/lab/` |
| **TSK-N1-04** | Lab call result with `gate explain` to revise commands | FR-MDL-10 | V2 | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/lab/` |
| **TSK-N1-05** | Single-step client configuration: `mcp desktop-config --lab` | FR-CLI-12 | V2 | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/mcp_desktop.py` |
| **TSK-N5-01** | Tools `lab_draft_write` and `lab_draft_check` (Q-71) | FR-DX-01, FR-DX-10 | — | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/lab/` |
| **TSK-N5-02** | Mandatory bidirectional tests (at least one ALLOW and one BLOCK) | FR-CI-* | — | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/lab/` |
| **TSK-N5-03** | Malformed proposals return 3-part error, no junk files written | — | — | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/lab/` |
| **TSK-N5-05** | `trace export --report` and Markdown `lab_report` tool | FR-TRC-* | — | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/cli/main.py` |
| **TSK-N5-06** | `neuroedge lab check` in Action CI on PR | FR-CI-*, FR-DX-10 | — | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/lab/` |
| **TSK-N6-04** | Tool `lab_trigger_check`: evaluate draft trigger declarations | FR-DX-10 | — | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/lab/` |
| **TSK-S5-01** | Integrate WebRTC AEC, libfvad (VAD), Opus streaming | FR-PER-06 | V2 | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/audio/` |
| **TSK-S5-02** | Port audio capture/playback path, no on-chip STT/TTS | FR-PER-01 | V2 | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/drivers/audio_path.c` |
| **TSK-S5-03** | C/C++ implementation of voice FSM per `voice_fsm.md` | FR-PER-02, FR-PER-03, FR-PER-05 | V1 + V2 | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/fsm/voice_fsm.c` |
| **TSK-S5-04** | Revoke unexecuted actuator commands upon barge-in | FR-PER-02 | V1 + V2 | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/fsm/actuator_abort.c` |
| **TSK-S5-05** | Memory optimization per Q-3 budget | NFR-RES-01, NFR-RES-02 | V2 | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/sdkconfig.defaults` |
| **TSK-S5-06** | Audio streaming client to cloud provider | FR-PER-07, FR-GW-04 | V2 | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/audio/provider_client.c` |
| **TSK-S5-07** | Local fallback on `esp32s3` (MultiNet or TFLite Micro) | FR-MDL-03, FR-ACE-03, NFR-RES-01 | V2 | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/fallback/` |
| **TSK-N7-01** | On-chip lab action + gate via C walker and token ledger | — | — | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/` |
| **TSK-N7-03** | Selective porting from ESP-Claw to ESP32-S3 | — | — | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/` |
| **TSK-K2-01** | Self-hosted provider: unified endpoint, credentials, key rotation | FR-GW-01, FR-GW-02 | V4 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/models/providers/auth.py` |
| **TSK-K2-02** | Self-hosted provider: multi-LLM routing, failover, quotas | FR-GW-03, FR-GW-05, FR-TEL-06 | V4 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/models/providers/routing.py` |
| **TSK-K2-03** | Self-hosted provider: edge protocols, unified traces | FR-GW-04, FR-GW-06, FR-GW-07 | V4 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/models/providers/traces.py` |
| **TSK-K2-04** | Fleet: device identity and certificate provisioning | FR-FLT-01 | V4 | ⏸ Removed from roadmap (Q-77) | `services/fleet/provisioning.py` |
| **TSK-K2-05** | Fleet: device inventory, health monitoring, dashboard | FR-FLT-03, FR-FLT-06 | V4 | ⏸ Removed from roadmap (Q-77) | `services/fleet/inventory.py` |
| **TSK-K2-06** | Fleet: remote sync for configuration, secrets, and gates | FR-FLT-04 | V4 | ⏸ Removed from roadmap (Q-77) | `services/fleet/config_sync.py` |
| **TSK-K2-07** | Fleet: canary OTA orchestration 1% → 10% → 100% | FR-FLT-02 | V4 | ⏸ Removed from roadmap (Q-77) | `services/fleet/canary.py` |
| **TSK-K2-08** | Fleet: automatic crash trace ingestion to repository | FR-FLT-05 | V4 | ⏸ Removed from roadmap (Q-77) | `services/fleet/trace_collector.py` |
| **TSK-K2-09** | Device certificate revocation | NFR-SEC-05 | V4 | ⏸ Removed from roadmap (Q-77) | `services/fleet/` |
| **TSK-K3-01** | Stable identity for devices, agents, gates | FR-REG-05 | V4 | ⏸ Removed from roadmap (Q-77) | `services/registry/identity.py` |
| **TSK-K3-02** | Metering system for agent calls and gate evaluations | FR-REG-06, FR-TEL-04 | V4 | ⏸ Removed from roadmap (Q-77) | `services/metering/engine.py` |
| **TSK-K3-03** | Manifest and SemVer versioning standard | FR-REG-02, FR-GATE-10 | V4 | ⏸ Removed from roadmap (Q-77) | `schemas/manifest.v1.json` |
| **TSK-K3-04** | Free public Gate repository | FR-REG-01 | V4 | ⏸ Removed from roadmap (Q-77) | `services/registry/oci_store.py` |
| **TSK-K3-05** | Permissions and sandbox mechanisms | FR-REG-07 | V4 | ⏸ Removed from roadmap (Q-77) | `services/registry/sandbox.py` |
| **TSK-K3-06** | Community provider adapter registry | FR-REG-08 | V4 | ⏸ Removed from roadmap (Q-77) | `services/registry/adapters.py` |
| **TSK-W2-04** | Gate signing and on-device signature verification (OCI/ORAS); trace signing | FR-REG-04 | V4 | ⏸ Removed from roadmap (Q-77) | `services/registry/` |
| **TSK-P1-01** | Language-independent compliance vector suite packaged externally | FR-GOV-03 | V1 | ⏸ Removed from roadmap (Q-77) | `fixtures/compliance/portable/` |
| **TSK-P1-02** | HAL porting guide: minimal contract, self-certification | FR-TGT-08, FR-GOV-03 | V3 | ⏸ Removed from roadmap (Q-77) | `docs/porting/` |
| **TSK-P1-03** | Reference port scaffold for non-ESP32 microcontrollers | FR-TGT-08 | V3 | ⏸ Removed from roadmap (Q-77) | `targets/_template/` |
| **TSK-P1-04** | Tier-3 accreditation process: contributor self-testing and publication | FR-TGT-08 | V3 | ⏸ Removed from roadmap (Q-77) | `docs/porting/tier3.md` |
| **TSK-P1-05** | `neuroedge board check <file>` pass/fail validation against tier | FR-TGT-08 | V1 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/cli/` |
| **TSK-W2-01** | mTLS or PSK between Pi and nodes | NFR-SEC-04 | V2 | ⏸ Removed from roadmap (Q-77) | firmware · `python/` |
| **TSK-W2-03** | TPM for Pi (`linux`) augmenting Secure Boot | NFR-SEC-02, NFR-SEC-03 | V2 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/hal/linux.py` |
| **TSK-W3-01** | Zenoh-pico ↔ Pi spike on ESP32-S3 and RP2350 (Q-36) | — | V2 | ⏸ Removed from roadmap (Q-77) | `docs/reports/` |
| **TSK-W3-02** | Node RFC: multi-node, wire, black channel — extension of minimal RFC TSK-I3a-06 | FR-TGT-08 | V1 | ⏸ Removed from roadmap (Q-77) | `docs/rfc/` |
| **TSK-W3-03** | Black channel layer: wrapper + watchdog + replay protection | NFR-SEC-09 | V1 + V2 | ⏸ Removed from roadmap (Q-77) | `python/` + firmware |
| **TSK-W3-04** | Unified multi-node traces (Option A, Q-32) | FR-TRC-05 | V1 | ⏸ Removed from roadmap (Q-77) | `fixtures/compliance/multinode/` |
| **TSK-W3-06** | `verify` for node clusters; divergence → NE4002 | FR-CI-07 | V1 | ⏸ Removed from roadmap (Q-77) | CLI + CI |
| **TSK-W3-07** | Port RP2350 as second node (Q-33): C HAL, C99 walker | FR-TGT-08 | V2 | ⏸ Removed from roadmap (Q-77) | `targets/rp2350/` |
| **TSK-P2-05** | MCP for MCU via gateway; MCU independently evaluates gate | FR-GW-01, FR-MDL-10 | V1 + V2 | ⏸ Removed from roadmap (Q-77) | `docs/spec/tool_calling.md` §8 |
| **TSK-W4-01** | ROS 2 bridge at gate boundary (`linux`) + Nav2 (Q-34) | FR-MDL-10 | V1 | ⏸ Removed from roadmap (Q-77) | `python/` |
| **TSK-W4-07** | Mobile robot safety RFC and C6 with robot buyers | — | V1 + team lead | ⏸ Removed from roadmap (Q-77) | `docs/rfc/` |
| **TSK-V2-01** | Port HAL to Jetson Orin via JetPack | FR-TGT-08, FR-HAL-01 | V5 | ⏸ Removed from roadmap (Q-77) | `targets/jetson/hal/` |
| **TSK-V2-02** | GPU-accelerated vision pipeline, preserving abstractions | FR-MDL-04 | V5 | ⏸ Removed from roadmap (Q-77) | `targets/jetson/vision/` |
| **TSK-V2-03** | `neuroedge verify` for `jetson` on verdict domain | FR-CI-07, FR-TGT-08 | V1 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/cli/main.py` |
| **TSK-V2-04** | `jetson-orin-nano` board profile | FR-HAL-02 | V5 | ⏸ Removed from roadmap (Q-77) | `boards/jetson-orin-nano.toml` |
| **TSK-V3-01** | Fuse voice, vision, and sensors into single FSM | FR-PER-01→05 | V1 + V5 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/perception/fusion/` |
| **TSK-V3-02** | Extend compliance test suite for multimodal streams | FR-CI-07 | V1 | ⏸ Removed from roadmap (Q-77) | `fixtures/compliance/multimodal/` |
| **TSK-V3-03** | Multimodal gate | FR-GATE-03 | V1 | ⏸ Removed from roadmap (Q-77) | `schemas/gate.v2.json` |
| **TSK-V3-04** | Visual evidence gate semantics RFC | FR-GATE-03 | V1 | ⏸ Removed from roadmap (Q-77) | `docs/rfc/` |
| **TSK-P2-01** | Adapter repository and community HAL ports on Registry | FR-TGT-08 | V3 | ⏸ Removed from roadmap (Q-77) | `services/registry/ports.py` |
| **TSK-P2-02** | Adapter compliance status visible on Fleet Dashboard | FR-FLT-03 | V3 | ⏸ Removed from roadmap (Q-77) | `services/fleet/compliance_view.py` |
| **TSK-P2-03** | Free hardware certification, self-tested | FR-GOV-03 | V3 | ⏸ Removed from roadmap (Q-77) | `docs/porting/certification.md` |
| **TSK-I2c-13** | Plugin template and 30-minute plugin authoring guide | FR-EXT-02, FR-DX-04 | V3 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/templates/` |
| **TSK-I2c-17** | `neuroedge-muse` bridge test authored in dedicated repository | FR-EXT-02, FR-EXT-04 | V3 + tester | ⏸ Removed from roadmap (Q-77) | `neuroedge-muse` repo |
| **TSK-V1a-02** | Open `target` enum in two schemas | FR-TGT-08 | V1 | ⏸ Removed from roadmap (Q-77) | `schemas/board.v1.json` · `schemas/trace.v1.json` |
| **TSK-V1a-03** | Core-owned machine-readable `TARGET_TIERS` | FR-TGT-08, FR-HAL-05 | V1 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/hal/board.py` |
| **TSK-V1a-04** | Tighten three test invariants by tier | FR-HAL-04, FR-TGT-08 | V1 | ⏸ Removed from roadmap (Q-77) | `python/tests/test_boards.py` |
| **TSK-V1a-05** | CLI: `board validate`, `board show` | FR-HAL-05 | V1 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/cli/main.py` |
| **TSK-V1a-06** | Update `unknown_target.json` counter-example corpus | FR-TRC-08 | V1 | ⏸ Removed from roadmap (Q-77) | `fixtures/traces/expected_errors.yaml` |
