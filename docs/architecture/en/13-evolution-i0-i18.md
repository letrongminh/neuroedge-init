# 13 · Evolution I0–I18 (as-is vs planned)

> Dates/tags: roadmap §0.2 (only place). Below says only *what changes
> architecturally* per stage — no dates or task statuses copied.

![E-08 · Roadmap](../assets/svg/E-08-roadmap-timeline.svg)

## 1. As-is: I0–I4 (done, code exists)

Typed gates + safe inheritance, `sim`+`linux` parity, Action CI
(record/replay/assert/golden), MCP + System 2 via LiteLLM, Python voice FSM +
barge-in, C walker/token/UART on QEMU. The 2026-10-25 demand gate (Q-20)
decides Go/Adjust/Stop for I3–I7.

## 2. Planned: I5–I7 (v1.0)

| Increment | Architectural change | Held risk |
|:---|:---|:---|
| I5 voice on chip | Second C/C++ FSM implementation (XiaoZhi/Pipecat ports, same vectors); Opus streaming to providers | R-1 memory (TSK-S1-10 spike; on miss open a `Q-N` replan, never cut voice — Q-44) |
| I6 public | Schemas at public URLs; SBOM + provenance; first PyPI | Commercial license terms (`TODOS.md` #44) |
| I7 v1.0 | Signed OTA A/B + rollback; Secure Boot + flash encryption; 24h stability; A1–A9 complete | SEC-02→06/08 criteria debt (appendix A.3) must close first |

## 3. Planned: after Beta

| Stage | Architectural variation point | Opens when |
|:---|:---|:---|
| I8 Beta | Frozen `1.0.x` line (blockers + safety only); RFCs/specs still merge (R12) | I7 hits A1–A9 |
| I9–I10 Fleet + Registry | One endpoint/credential per fleet; declared failover; canary OTA; signed ORAS registry; metering | Beta hits B1 + B2 (Q-41) |
| I11 open targets | Tiered `target` enum + `TARGET_TIERS` + `board validate` (RFC-0002 PR2) | I8 |
| I12 NeuroBrain | `neuroedge.brain` via `dispatch()` only (B-1); gated lab actions; safety envelope | I11 (+ I2/I3) |
| I13 port kit | Tier-3 docs + vectors + port frame (links `11`) | I11 |
| I14 tiered robot | Per-node HAL + gates; Zenoh-pico wire (Q-36); `motion.*` lease tokens (Q-37); ROS 2/Nav2 gating every velocity command (Q-34); per-mechanism safe states (Q-35) | I13 (+ I4/I7/I11/I12) |
| I15–I17 vision | `vision.in` via its own RFC; tier-2 `jetson`; multimodal gates | Measured camera demand |
| I18 ecosystem | Multi-device SDK, HAL port index, free self-checked certification | I13 (+ I9/I10) |

Off-roadmap: field AURA (public APIs only), Marketplace (blocked until G1–G4).
