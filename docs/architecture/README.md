# NeuroEdge Architecture

This document suite describes the **structure and behavior** of NeuroEdge as it exists on the `main` branch, going
from the big picture down to each byte: context (C4 L1) → container (L2) → component (L3) → code
(L4), followed by runtime flows, data contracts, non-functional requirements, architecture decisions, and
how the system will grow.

Designs without code are also recorded in place within each viewpoint, but always carry the `planned` label — the
Blueprint positioning section records `planned · Q-72` with increments (I2d, I2e) — and are drawn with dashed lines in diagrams, so
readers can always separate what currently exists on `main` from what is newly planned.

> Chapters are written in English, as are diagram labels.

## Where to start reading

| You are | Goal | Read in order |
|:---|:---|:---|
| Completely new | What the system includes (NeuroClaw brain, NeuroEdge box, device), what can run | [`bat-dau.md`](../user/bat-dau.md), then `00` §2 |
| New engineer | Run the system and understand it on day one | [`python/README.md`](../../python/README.md) → `00` → `02` → `03` |
| Core engineer | Understand each layer and how they call each other | `00` → `02` → `03` → `05` → `06` → `07` → `15` |
| Embedded engineer | Firmware, memory, boot, OTA, deployment | `02` → `04` → `05` → `06` → `02` §6 |
| OEM partner | Port HAL to a new board | `10` §7 → `10` → `07` → `04` |
| Safety reviewer, QA | Why it is safe, where the evidence is | `00` §9.4 → `06` → `10`; PRD §9 requirements, PRD §15 decisions |
| Planner | What is already here, what comes later | `00` → `15`; milestones and dates in roadmap §0.2 |

## File map

Q-77 (2026-10-12) consolidated this suite from 17 down to 10 chapters: context into `00`, deployment into `02`, porting guide into
`10`, variation points and architecture debt into `15`; removed chapters that duplicate PRD §9 (NFR), PRD §15 (ADR), and
`python/README.md` (day one). Old version: `git show f7278fc:docs/architecture/<file>`.

| File | Content | Viewpoint |
|:---|:---|:---|
| [`00-overview.md`](00-overview.md) | What NeuroEdge is, six promises, principles, architecture characteristics, status; §9 context: users, external systems, trust boundaries | Overview · C4 L1 |
| [`02-container-c4l2.md`](02-container-c4l2.md) | Processes, libraries, firmware, file stores, and how they communicate; §6 where it runs (dev machine, CI, gpio-sim, QEMU, Pi, Box-3) | C4 L2 · Deployment |
| [`03-component-host-c4l3.md`](03-component-host-c4l3.md) | Python packages, real dependencies between them, package responsibilities | C4 L3 · host |
| [`04-component-device-c4l3.md`](04-component-device-c4l3.md) | ESP32-S3 firmware components, boot sequence, memory | C4 L3 · device |
| [`05-code-gate-hal-c4l4.md`](05-code-gate-hal-c4l4.md) | Gates from YAML to pins: resolution, decision tree, NETR, tokens, HAL | C4 L4 · Code |
| [`06-runtime-flows.md`](06-runtime-flows.md) | Runtime flows: keystroke turns, confirmation, MCP, models, replay, boot, OTA | Dynamic |
| [`07-data-contracts.md`](07-data-contracts.md) | All file formats and wire formats, versioning scheme | Data |
| [`10-target-equivalence.md`](10-target-equivalence.md) | Why the same gate yields the same verdict on `sim`, `linux`, `esp32s3`; §7 porting HAL to a new board | Cross-cutting · Guide |
| [`15-target-architecture.md`](15-target-architecture.md) | Target architecture: v1.0, range Q-72 → Q-88 (operator agent, Blueprint, brain, optional cloud, two deployment profiles, missions, Blueprint packaging), variation points, architecture debt | To-be |
| [`16-ecosystem-landscape.md`](16-ecosystem-landscape.md) | Participating parties, shared assets, platforms, and commercial boundaries | System Landscape |

## Conventions

1. **Status of everything drawn.** Every box, every row in tables carries one of three labels:

   | Label | Meaning | In diagrams |
   |:---|:---|:---|
   | `done` | Has code in `main` and has tests running in CI | solid line |
   | `partial` | Partially coded; the remainder is explicitly stated | solid line, glyph ◐ |
   | `planned` | Only in PRD, roadmap, RFC, or draft; no code yet | dashed line, glyph ○ |

   No "reasonable-looking" detail is drawn without a source: every assertion links to code files,
   tests, or planning documents stating it.
2. **Single source of truth** (`CONTRIBUTING.md` §8.1). This suite describes structure and behavior. Requirements cite
   `FR-*`/`NFR-*` codes to PRD; decisions cite `Q-N` to PRD §15; progress and dates cite increment `I-N`
   to roadmap §0.2; command syntax cites `docs/reference/cli.md` §3; notation cites
   [`docs/user/thuat-ngu.md`](../user/thuat-ngu.md). Do not duplicate, do not record test counts.
3. **Reference by name**, not by line numbers: `engine/gate.py` · `ActionContractEngine.evaluate`.
4. **Two kinds of diagrams.** Mermaid diagrams live directly on the page, precise down to function names, edited alongside prose.
   Posters (`assets/svg/`) are the big picture for printing or presentation.

## Editing diagrams

**Posters** are generated from a single model, [`scripts/gen_architecture_diagrams.py`](../../scripts/gen_architecture_diagrams.py),
into both `assets/excalidraw/<id>.excalidraw` (opened with Excalidraw to view or sketch) and
`assets/svg/<id>.svg` (images embedded in pages). To change a poster: edit that poster's function and then run

```bash
python3 scripts/gen_architecture_diagrams.py           # rewrite SVG and .excalidraw
python3 scripts/gen_architecture_diagrams.py --check   # CI: exit 1 if files drift from model
```

The model lints layout before writing: overlapping boxes, text overflowing boxes, labels colliding with boxes, arrows pointing to
missing boxes are all rejected. Do not hand-edit the two generated files; sketch in Excalidraw then copy
changes back to the model.

**Mermaid** is rendered directly by GitHub; a single syntax error turns the diagram into raw text. Before pushing:

```bash
npm install -g @mermaid-js/mermaid-cli        # once
python3 scripts/check_architecture_mermaid.py  # every block must render
```

`python/tests/test_architecture_diagrams.py` (run in CI) preserves the following invariants: posters match the model,
`.excalidraw` files are real drawings, every poster is embedded in a page, and every relative link points to a real file.
