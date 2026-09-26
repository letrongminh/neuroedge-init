# 09 · Architecture Decision Index (ADR)

> Decision content: PRD §15 (the only register, `Q-N` codes). RFCs: `docs/rfc/`.
> This table only connects each decision to where it lands in the architecture.

## 1. Decided ADRs (architecture-touching excerpt)

| ADR | One-line decision | Lands in |
|:---|:---|:---|
| Q-2/Q-3 | Single Box-3 reference; SRAM ≥ 120 KB, PSRAM ≥ 2 MB, firmware ≤ 3.5 MB | `04`, `08` (RES) |
| Q-4/Q-14/Q-15 | Jev + local fixed-command fallback P0; typed-text `sim` default | `03` (models/grammar), `06`, `12` |
| Q-8/Q-9/Q-23 + RFC-0003 | C/C++ firmware; build compiles gates → trees; trees are NETR v1 binaries | `04`, `05` |
| Q-10/Q-12/Q-28 | LiteLLM as SDK behind `providers/`, `cloud` extra; OpenAI API + adapters; minimal FR-GW in v1.0 | `02`, `03`, `06` |
| Q-11/Q-45 | License allowlist; PolyForm Noncommercial core, Apache-2.0 standards | `08` (COMP), `CONTRIBUTING.md` §4 |
| Q-13 + RFC-0002 PR2 | Target tiers 1/2/3; core team commits to tier 1 | `10-target-equivalence.md` |
| Q-16/Q-21/Q-22 | gpio-sim + i2c-stub + QEMU in CI; PipeWire AEC on linux | `10` |
| Q-17/Q-26 + RFC-0006 | Every `on_block` blocks; only humans via device confirm `ask` | `05`, `06` |
| Q-18 + RFC-0004 | Inheritance tightens `budget`/`on_block` too (still 5 principles) | `05` |
| Q-24/Q-25 + RFC-0005 | Every `@action` is a tool; argument limits live in gates | `05`, `06`, `07` |
| Q-27 | System 2 is an MCP host; external servers are information-only (allowlist) | `03`, `06` |
| Q-29/Q-30/Q-31 | Watch MHS, don't invest; contract positioning; NeuroBrain drops "Copilot" | `00`, `13` |
| Q-32..Q-38 | Post-Beta tiered robot: Zenoh-pico, `motion.*` lease tokens, cert OUT + hard e-stop | `13` |
| Q-39..Q-44 | I0–I18 increments, post-Beta order, C6 as tracking, no scope-cut ladder 5 | `00`, `13` |
| RFC-0001/0002 | Conditional-required gates; open target enum + tiers (discussing, schemas unchanged) | `05`, `10` |

## 2. New-ADR rule

New architectural decisions made during execution → get a `Q-N` code in PRD
§15 (same PR), then one row here. A separate RFC is needed only when touching
the `CONTRIBUTING.md` §3 list (schemas, resolution semantics, golden traces,
`digests.lock`, NETR).
