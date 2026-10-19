# Commands and operating guide — NeuroEdge

How to set up, run and check everything, with the expected output. The one place for commands, exit codes, error messages and CI jobs (CONTRIBUTING.md §8.1); what changed is in [`CHANGELOG.md`](../../CHANGELOG.md), what remains in [`roadmap/neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) §0.

## 1. Environment Setup

Requires **Python 3.11+** (uses standard library `tomllib`, no external TOML dependency).

```bash
cd python
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q          # expected: 0 failed, 0 skipped
```

Reproducible build (roadmap §3.9):

```bash
.venv/bin/python -m pip install -r requirements-lock.txt
```

Optional: System 2 with real models requires `.venv/bin/python -m pip install -e '.[cloud]'`, configure `[system_two]` in `agent.toml`, and export corresponding API keys. System 1 with Jev configured via `[system_one]` and `OPENROUTER_API_KEY`.

## 2. Quick Verification of All Artifacts

Commands run from the **repo root** (`paths.py` self-locates monorepo root):

```bash
V=python/.venv/bin

$V/neuroedge verify                      # expected: all gates resolve, traces validate, tool corpus matches, replay matches; 0 artifacts ⇒ NE4004 (code 1)
$V/neuroedge gate lint                   # expected: ✓ all gates resolved, code 0
$V/neuroedge trace validate fixtures/traces/*.json   # expected: each file VALID
$V/neuroedge board list                  # expected: lists profiles in boards/
python3 scripts/gen_cpo_dashboard.py     # regenerates CPO dashboard (docs/business/cpo-dashboard.html) after source change
$V/python scripts/check_digests.py --check   # expected: ✓ files match digests.lock
```

Inverse assertion — negative corpus **must** continue to fail:

```bash
$V/neuroedge gate lint fixtures/gates/invalid --registry fixtures/gates/registry
# expected: all files in invalid/ failed to resolve · exit code 1
```

## 3. CLI Command Reference

**Exit code contract** — CI and Action CI anchor to it:

| Code | Meaning |
|:---:|:---|
| `0` | Check ran and **passed** |
| `1` | Check ran and **failed** |
| `2` | Command (or that specific `--target` of the command) **not implemented yet** |

Code `2` is distinguished from `1` so CI separates "broken" from "not yet present". Currently exiting with code 2: `run` / `mcp serve --target esp32s3` (TSK-S4-01), `run --ui --target linux` (`mcp serve --ui` runs on `linux`, where the person at home answers `ask`: DP-A-05), `run` / `record --voice-file` along with `--ui`, `replay --target esp32s3` (TSK-S4-04). Unknown target is an error (code 1).

All commands loading gates accept `--registry <dir>` (`-r`), default `gates/`. `--agent` defaults to `./agent.toml` or sample agent `villa-concierge`.

| Command | Primary Function |
|:---|:---|
| `gate resolve <file\|URI>` | Resolve `extends` chain, print effective policy and digest. `--json` for machine reading |
| `gate lint [dir]` | Resolve all gates in directory (default `gates/`, `--registry`) |
| `gate publish <file>` | RFC 8785 canonicalize and print SHA-256 digest (stops at digest, not yet digitally signed) |
| `gate add <URI>` | Add gate from registry and analyze inheritance constraints |
| `gate explain <file\|URI>` | Explain gate for reviewers (criteria, tightening clauses, budget, `on_block`) |
| `trace validate <file…>` | Validate traces against `trace.v1.json` schema |
| `trace show <file>` | Print event timeline of trace |
| `trace view <file>` | Export self-contained HTML visualizing devices, sensors, verdicts, and scrubber bar |
| `trace export <file>` | Export Chrome Trace Event format for Perfetto (`--format chrome`) |
| `board list` / `board show <id>` | List or inspect board capabilities and supported primitives |
| `verify [--targets t]` | Comprehensive verification: gates, tool corpus, normative traces, and replay on each target |
| `build --target <t>` | Check agent ↔ board compatibility, compile gates to `NETR` tree, and generate ESP-IDF firmware |
| `replay <file> [--target t]` | Recompute verdicts and pin commands on real HAL and match against golden |
| `record [--target t]` | Record interactive session to validated trace; defaults to hashing raw text (`--raw` keeps verbatim) |
| `test [dir]` | Run agent's Action CI suite (pytest) |
| `run [--target t]` | Interactive CLI REPL (`-c` one-shot command, `--ui` local web, `--voice-file`, `--mic`); a page started by a script: `--exit-with-parent`, `--idle-timeout <s>`; leftovers: `bash scripts/kill-ui.sh` |
| `mcp tools` | Export schemas of `@action`s for MCP or OpenAI function-calling |
| `mcp serve` | MCP server over stdio or network (`--http` mTLS/OAuth 2.1) on `sim` or `linux` |
| `mcp desktop-config` | Generate or write connection configuration for Claude Desktop (`--write`) |
| `new <name> [--template T]` | Scaffold new project from template (`minimal`, `villa-concierge`, `home-voice`, etc.) |
| `add action\|sensor\|device\|gate` | Scaffold code component with default-block gate and bidirectional tests |

`python -m neuroedge …` is equivalent to `neuroedge …`. Detailed instructions and usage examples for each command can be found in [`docs/user/huong-dan.md`](../user/huong-dan.md).

## 4. Reading an Error Message

All errors have exactly three parts (FR-DX-04): **where** (`where`) · **why** (`why`) · **remediation** (`fix`). Inheritance errors include an additional `rule` line indicating the violated principle.

```
[NE2003] loosens-level@1.0.0 (fixtures/gates/invalid/loosens_level.yaml) -> allow_when.risk_level
  why: loosens the inherited condition: base admits {low}, this gate admits {high, low, medium}
  rule: Appendix B.5 principle 2
  fix: narrow allow_when.risk_level to a subset of the base condition (base clause: {'lte': 'low'}), …
```

List of `NE…` codes, error taxonomy, and occurrence contexts can be found in PRD [Appendix B](../../roadmap/neuroedge-prd.md#appendix-b--standard-error-code-catalog).

## 5. CI

List of workflows and jobs in the continuous integration system:

| Workflow | When | Jobs |
|:---|:---|:---|
| `ci-sim-linux.yml` | Every PR and push to `main` | `frozen-artifacts` · `tests` (Python 3.11/3.12/3.13) · `linux-hal` · `wheel-smoke` · `lint` · `licence-obligations` · `cloud-extra` · `ui-golden` (LVGL on host, TSK-S4-10) |
| `firmware-qemu.yml` | PR/push touching firmware sources (`targets/**`), generator, scripts, or nightly | `firmware-qemu` (boot ESP-IDF 5.4 on Espressif QEMU) · `firmware-size` (check flash budget, SRAM Q-3) · `ota-rollback` (phases a–g, RSA-3072) · `agent-firmware` (build and boot agent firmware) · `uart-trace` (read UART, validate and verify) |
| `release-pypi.yml` | Tag `v*.*.*` or manual dispatch | `build` · `sbom` · `smoke` · `attest` · `publish-testpypi` · `publish-pypi` · `github-release` (procedure in [`docs/release.md`](../release.md)) |
| `nightly-hardware.yml` | Nightly or manual dispatch | `firmware-build` (ESP-IDF 5.2.1) · `upstream-drift` · `drift-issue` · `memory-spike` · `report` |
| `security.yml` | Every PR/push, weekly, or manual dispatch | `pip-audit` · `gitleaks` (full history) · `actionlint` · `codeql` (Python, Actions) · `firmware-changed` + `codeql-c` |

Five required green CI gates before merge:
- **Skip test blocking gate:** Fails if any test is skipped (`CONTRIBUTING.md` §5).
- **Inverse assertion:** Entire negative corpus must continue to fail with exact exit code 1 (§2.2).
- **`digests.lock`:** Modifying normative gates without an RFC fails the build (`CONTRIBUTING.md` §3).
- **License gate:** `licence-obligations` checks entire core dependency tree; `cloud-extra` checks Q-11 policy.
- **Format check:** `ruff check .` and `ruff format --check .` in the `lint` job.

## 6. Firmware (When Hardware Boards Are Available)

Firmware flashing instructions for agents can be found in [`docs/user/nap-firmware.md`](../user/nap-firmware.md). Build sample `home-voice` firmware on device:

```bash
cd targets/esp32s3
idf.py set-target esp32s3
idf.py build
idf.py size --format json2 --output-file build/size.json
idf.py size-components --format json2 --output-file build/size-components.json
python ../../scripts/check_firmware_size.py build/neuroedge-esp32s3-box3.bin \
  --size-json build/size.json --components-json build/size-components.json   # Q-3 budget
idf.py -p /dev/ttyUSB0 flash monitor
```

Look for `NEUROEDGE_MEMORY_JSON` line in the monitor output to record metrics into `docs/reports/memory_spike_report.md`. When physical boards are not yet available, C walker runs on host (`make -C targets/esp32s3/components/ne_gate check-static`) and firmware boots on QEMU per `firmware-qemu.yml`.
