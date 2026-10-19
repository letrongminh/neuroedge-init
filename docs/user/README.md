# NeuroEdge — user documentation

NeuroEdge aims to be **the place to turn intent into AI physical products** — build, run
safely, share and sell (Q-72; direction decided, the three flywheels and NeuroEdge Blueprint **have no code yet**).
What is in the repository today is the **Action Contract** core, the trust layer of that direction: every action
to hardware passes through a *gate* with a frozen schema, runnable across peer environments
(`sim`, `linux`, `esp32s3`) without target-specific branching logic.

Every truth in the repository has **exactly one place** (`CONTRIBUTING.md` §8.1). This map
answers the question *"which file to read to know X"* — other files link to code, not duplicate.

## What to read based on needs

| You need | Read | Notes |
|:---|:---|:---|
| **Newcomer** | | |
| What the system has, what runs today, what to read next — in plain words, no code | [`bat-dau.md`](bat-dau.md) | read first, 5 minutes |
| **Try it out** | | |
| Installation and running tests | [`python/README.md`](../../python/README.md) | venv + `pip install -e '.[dev]'` |
| All CLI commands and expected outputs | [`docs/reference/cli.md`](../reference/cli.md) | sole source for command syntax |
| What the product does, in which environments, and step-by-step testing | [`huong-dan.md`](huong-dan.md) | capabilities by group (§3–§4) and step-by-step testing scenarios (§5) |
| Current status | [`trang-thai.md`](trang-thai.md) | machine-generated from roadmap §0 |
| Try devices without hardware: the samples named by parts, a greenhouse and a full fish tank on the virtual board, with screenshots | [`vi-du-linh-kien-ao.md`](vi-du-linh-kien-ao.md) | `sim` only; TSK-I2d-33, Q-84 |
| Build real devices from five kits (BOM, wiring diagrams, from out-of-the-box to live run) | [`kit-phan-cung.md`](kit-phan-cung.md) | villa smart lock, voice assistant, machine room monitor, gate camera, window blinds; unverified on real hardware |
| Partner pilots: shield Home Assistant, Python agents, or device APIs with a gate (pilot run, Q-70) | [`doi-tac/README.md`](doi-tac/README.md) | three runnable guides from wheel, boundary pages, feedback form; agreement list and test sessions in [`docs/business/doi-tac/`](../business/doi-tac/buoi-do.md) |
| Flash your agent onto ESP32-S3-BOX-3 (or QEMU, esp-emulator) | [`nap-firmware.md`](nap-firmware.md) | `build --target esp32s3` → `idf.py flash`; sole source for flashing procedure |
| Chat with home: connect the NeuroClaw brain to the box, choose open or bounded brain | [`chat-voi-nha.md`](chat-voi-nha.md) | runs with `sim`; keys and tokens for demo script |
| Run brain and gate on a single ESP32-S3 (Q-79): serial control console, safe mode, storage for tokens and keys | [`esp32-mot-chip.md`](esp32-mot-chip.md) | Stage 1 and NeuroClaw-ESP on QEMU; firmware embedding and real Wi-Fi awaiting boards |
| **Understand the product** | | |
| `FR-*` / `NFR-*` requirements | [`neuroedge-prd.md`](../../roadmap/neuroedge-prd.md) | decision log is §15 (`Q-N` codes) |
| Product proposal: three loops build · run · share and sell, operator agent, NeuroEdge Blueprint, launch path | [`product-proposal.md`](../business/product-proposal.md) | direction decided proposal; decision in PRD §15 Q-72, lean path in Q-92; no code yet |
| API specification, gate (Appendix B), HAL, traces | [`core_contracts.md`](../spec/core_contracts.md) | |
| Decoder for abbreviations (`FR-*`, `Q-N`, `A1`, `CEO-X1`…) | [`thuat-ngu.md`](thuat-ngu.md) | sole source |
| Overall architecture with live progress (layers, release milestones, items waiting on a person) | [`docs/business/kien-truc-tong-the.html`](../business/kien-truc-tong-the.html) | open in browser; progress blocks generated from roadmap §0 — do not edit them by hand |
| Plan: increment I0–I8 and I2a–I2h, what to do when, forecast dates | [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) | sole roadmap (Q-39); increment table in §0.2 |
| Task tables cut by Q-92 (TSK-I2e-06, I2e-10 to I2e-14) | [`removed-tasks.md`](../../roadmap/archive/removed-tasks.md) | codes stay valid |
| **Removed from roadmap (Q-77), kept for lookup** | | |
| NeuroEdge Lab design (replaced by the standard MCP tool set TSK-I2d-23, Q-88) | [`lab_mcp.md`](../spec/lab_mcp.md) | trimmed to the sections still cited; removed items: roadmap §6 |
| Voice conversation state machine: turns, barge-in, wake-word, STT/TTS | [`docs/spec/voice_fsm.md`](../spec/voice_fsm.md) | host voice removed (Q-77), host code still ships; on-chip voice of Profile B follows it (TSK-I2f-19, Q-93) |
| Design notes — hierarchical robot (FOFOCA) | `docs/architecture/15-target-architecture.md` §4.3 | I14 removed from the roadmap (Q-77); see roadmap §6 |
| **Contributing** | | |
| Conventions, processes, task completion | [`CONTRIBUTING.md`](../../CONTRIBUTING.md) | §8 is the mandatory checklist |
| Modifying `schemas/` (frozen schemas) | [`docs/rfc/README.md`](../rfc/README.md) | RFC process |
| Reviewed and deferred work | [`TODOS.md`](../../TODOS.md) | each item includes trigger milestone |
| Release: internal tag before I6, PyPI from I6 | [`docs/release.md`](../release.md) | push tag; PyPI switch turns on only at I6 |
| What AI agents read first | [`CLAUDE.md`](../../CLAUDE.md) | |
| **Reference** | | |
| Schemas, sample gates, traces, boards | `schemas/` · `gates/` · `fixtures/` · `boards/` | machine-readable artifacts |
| Tool calling, MCP, `ask` confirmation (Gated Tool Profile) | [`docs/spec/tool_calling.md`](../spec/tool_calling.md) | sole source for tool calls |
| Device UI: screens, language rules, golden images | [`docs/spec/ui.md`](../spec/ui.md) | language rules in §2 |
| Blocked bypass paths around gate, and out-of-scope items | [`docs/spec/threat_model.md`](../spec/threat_model.md) | includes test names |
| Each HAL primitive × target: execution mechanism, test locations | [`docs/spec/simulation_coverage.md`](../spec/simulation_coverage.md) | Q-21, Q-22 |
| MCU constraints for HAL | [`docs/spec/hal_mcu_review.md`](../spec/hal_mcu_review.md) | RB-1…RB-4 |
| Memory footprint measurements on `esp32s3` | [`docs/reports/memory_spike_report.md`](../reports/memory_spike_report.md) | TSK-S1-10 |

## Repository layout

The repository map is [`CONTRIBUTING.md`](../../CONTRIBUTING.md) §6; the docs router is [`docs/README.md`](../README.md).

## Conventions

- English; identifiers, commands, paths kept as-is.
- Cite codes when referencing a truth (`TSK-S2-03`, `Q-17`, `RFC-0004`, `FR-GATE-03`,
  `TODOS.md #15`) — do not duplicate content.
- Schedule using increment (`I3`) or absolute date (`2026-09-28`); do not use "next week"
  or numbered week/month labels (`CONTRIBUTING.md` §8.3).
- `trang-thai.md` is machine-generated: edit [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md)
  §0 and run `python3 scripts/gen_user_status.py`, **do not edit manually**.
