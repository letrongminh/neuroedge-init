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
| All CLI commands and expected outputs | [`CHANGELOG.md`](../../CHANGELOG.md) §2 | sole source for command syntax |
| What the product does, in which environments, and step-by-step testing | [`huong-dan.md`](huong-dan.md) | capabilities by group (§3–§4) and step-by-step testing scenarios (§5) |
| Current status | [`trang-thai.md`](trang-thai.md) | machine-generated from roadmap §0 |
| Build real devices from five kits (BOM, wiring diagrams, from out-of-the-box to live run) | [`kit-phan-cung.md`](kit-phan-cung.md) | villa smart lock, voice assistant, machine room monitor, gate camera, window blinds; unverified on real hardware |
| Partner pilots: shield Home Assistant, Python agents, or device APIs with a gate (pilot run, Q-70) | [`doi-tac/README.md`](doi-tac/README.md) | three runnable guides from wheel, boundary pages, feedback form; agreement list and test sessions in [`docs/business/doi-tac/`](../business/doi-tac/buoi-do.md) |
| Flash your agent onto ESP32-S3-BOX-3 (or QEMU) | [`nap-firmware.md`](nap-firmware.md) | `build --target esp32s3` → `idf.py flash`; sole source for flashing procedure |
| Chat with home: connect the NeuroClaw brain to the box, choose open or bounded brain | [`chat-voi-nha.md`](chat-voi-nha.md) | runs with `sim`; keys and tokens for demo script |
| Run brain and gate on a single ESP32-S3 (Q-79): serial control console, safe mode, storage for tokens and keys | [`esp32-mot-chip.md`](esp32-mot-chip.md) | Stage 1 and NeuroClaw-ESP on QEMU; firmware embedding and real Wi-Fi awaiting boards |
| **Understand the product** | | |
| `FR-*` / `NFR-*` requirements | [`neuroedge-prd.md`](../../roadmap/neuroedge-prd.md) | decision log is §15 (`Q-N` codes) |
| Q-72 positioning: three flywheels build · run · share and sell, operator agent, NeuroEdge Blueprint, 8-week demand gate | [`proposal-blueprint-2026-10-11.md`](../business/proposal-blueprint-2026-10-11.md) | direction decided proposal; decision in PRD §15 Q-72; no code yet |
| API specification, gate (Appendix B), HAL, traces | [`core_contracts.md`](../spec/core_contracts.md) | |
| Decoder for abbreviations (`FR-*`, `Q-N`, `A1`, `CEO-X1`…) | [`thuat-ngu.md`](thuat-ngu.md) | sole source |
| Why Stage 1 went "`sim` wedge first" | `docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md` (deleted; `git show 7626b62:docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md`) | historical, frozen 2026-09-23 — current plan in roadmap |
| Minutes of review rounds | `docs/archive/` (deleted, see git history) | archive, non-normative |
| Overall architecture with live progress (layers, release milestones, items waiting on a person) | [`docs/business/kien-truc-tong-the.html`](../business/kien-truc-tong-the.html) | open in browser; progress blocks generated from roadmap §0 — do not edit them by hand |
| Demand gate 2026-10-25 (interviews, demos, scoring) | [`docs/business/cong-nhu-cau-2026-10-25/`](../business/cong-nhu-cau-2026-10-25/README.md) | business documentation; data for 8-week demand gate (Q-72, reversing Q-56) |
| Plan: increment I0–I8 and I2a–I2f, what to do when, forecast dates | [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) | sole roadmap (Q-39); increment table in §0.2 |
| **Removed from roadmap (Q-77), kept for lookup** | | |
| NeuroEdge Lab design (lab via MCP; replaced by the standard MCP tool set TSK-I2d-23, Q-88) | [`lab_mcp.md`](../spec/lab_mcp.md) | removed items: roadmap §6 |
| Voice conversation state machine: turns, barge-in, wake-word, STT/TTS | [`docs/spec/voice_fsm.md`](../spec/voice_fsm.md) | voice removed from the roadmap; host code still ships |
| Design notes — hierarchical robot (FOFOCA) | `docs/architecture/vi/15-target-architecture.md` §4.3 | I14 removed from the roadmap (Q-77); see roadmap §6 |
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

```text
neuroedge-init/
├── schemas/            frozen schemas (modifiable only via RFC)
├── gates/              resolvable sample gates
├── boards/             board capability declarations (TOML)
├── fixtures/           canonical traces + counterexample corpus
├── python/             SDK: hal/ · engine/ · cli/ · tests/
├── targets/esp32s3/    ESP-IDF firmware (ui/: LVGL interface and golden images)
├── pipewire/           PipeWire echo cancellation configuration for mic/speaker on linux
├── scripts/            CI tools (doc generation, firmware size checks)
└── docs/
    ├── user/           user documentation  ← you are here
    ├── rfc/            schema changes
    ├── spec/           specifications and constraints
    ├── reports/        measurement reports
    ├── business/       business documentation (interview pack)
    ├── release.md      release process (internal tags, PyPI from I6)
    └── archive/        archive: review minutes, frozen designs
```

## Conventions

- English; identifiers, commands, paths kept as-is.
- Cite codes when referencing a truth (`TSK-S2-03`, `Q-17`, `RFC-0004`, `FR-GATE-03`,
  `TODOS.md #15`) — do not duplicate content.
- Schedule using increment (`I3`) or absolute date (`2026-09-28`); do not use "next week"
  or numbered week/month labels (`CONTRIBUTING.md` §8.3).
- `trang-thai.md` is machine-generated: edit [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md)
  §0 and run `python3 scripts/gen_user_status.py`, **do not edit manually**.
