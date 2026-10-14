# Licensing

Decision: **Q-45** (`neuroedge-prd.md` §15, 2026-09-25), extended for standards in **Q-67** (2026-10-04). This file
states which parts of the repository fall under which license; the rationale and substance of the decision reside solely in Q-45 and Q-67.

| Part | License | Text |
|:---|:---|:---|
| NeuroEdge codebase — Python runtime, CLI, firmware, services, tooling, tests, documentation (everything not listed below) | **PolyForm Noncommercial 1.0.0** | [`LICENSE`](LICENSE) |
| Open standards — `schemas/`, `docs/spec/`, `fixtures/compliance/` | **Apache-2.0** | [`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt) |
| Compliance corpus — `fixtures/tool_calls/`, `fixtures/contracts/`, `fixtures/traces/`, and `fixtures/agents/` used by the corpus (Q-67) | **Apache-2.0** | [`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt) |
| Code ported or adapted from third parties | Its original license | [`NOTICE`](NOTICE) |
| Device UI fonts — `targets/esp32s3/ui/fonts/` (Be Vietnam Pro, generated with `scripts/gen_ui_fonts.sh`) | **OFL-1.1** | [`LICENSES/OFL-1.1.txt`](LICENSES/OFL-1.1.txt) · NOTICE section A.5 |

**Noncommercial** — individuals, research, education, non-profit organizations, and any other purpose
permitted by PolyForm Noncommercial — may use, modify, and redistribute the entire codebase free of charge,
in accordance with the terms in `LICENSE`.

**Commercial** — using NeuroEdge in enterprise products, services, or operations, including internal
use — requires a separate **commercial license**. Contact the author via the address in
[`python/pyproject.toml`](python/pyproject.toml). In commercial licensing, core safety features are
never split off into paid add-ons (PRD P-3).

**Open standards** and **compliance corpus** remain Apache-2.0 so third parties can implement the standards
and prove compliance via the test harness (criteria A9, A13) without using PolyForm Noncommercial files,
and to transfer specification governance to a neutral body upon reaching G1 (`docs/architecture/vi/16-ecosystem-landscape.md` §6).

**Third-party plugins and adapters** (Extension SDK, Q-67) reside in their authors' repositories under licenses
chosen by their authors; NeuroEdge claims no copyright over them. Plugins run alongside the NeuroEdge runtime, so
*using* them together with the runtime still follows the runtime terms in the first row of the table (noncommercial is free, commercial requires a license).

**Prior to this change:** all releases up to commit `f68a47f` (2026-09-25) were released under MIT. Anyone who received
those releases retains their MIT rights for those specific releases; after that commit, the codebase follows the table above.

**Contributions:** external pull requests require a CLA prior to merging, so NeuroEdge can grant commercial
licenses for contributed code and relicense in the future (`TODOS.md` #43, `CONTRIBUTING.md` §2).

**Future:** the codebase remains PolyForm Noncommercial through v1.0; open-source licensing will be revisited at the Beta fork point
(Q-59, `TODOS.md` #51).

*This file is a summary; the license text is binding. This is not legal advice.*
