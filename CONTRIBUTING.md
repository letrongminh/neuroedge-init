# Contribution Guidelines — NeuroEdge

> **Task code:** TSK-S1-13 · **Related requirements:** FR-DX-04, FR-CI-05, §3.9

This document explains how to submit changes, which changes require special procedures due to safety layers or legal obligations, and what must be done upon completing a task.

---

## 1. Environment Setup

Commands for environment setup, reproducible builds, and quick artifact verification: `CHANGELOG.md`
[`docs/reference/cli.md` §1–§2](docs/reference/cli.md). Before making any changes, `pytest -q` must be green:
0 failed, 0 skipped.

## 2. Standard Contribution Cycle

**Contribution licensing (Q-45).** Code is licensed under PolyForm Noncommercial 1.0.0; schemas, specifications, and conformance test suites under Apache-2.0 — scope table in [`LICENSING.md`](LICENSING.md). External PRs require a signed CLA before merge, enabling NeuroEdge to grant commercial licenses for contributed code; without a CLA, PRs may be reviewed but not merged (`TODOS.md` #43).

1. Branch from `main`, named `<type>/<task-code>-<short-description>`, e.g.
   `feat/TSK-S2-03-gate-engine`.
2. Write tests before writing implementation if changes are observable.
3. `pytest -q` green. **No tests skipped due to missing dependencies** — see §5.
4. **Commit author is the contributor's GitHub identity** (for the core team: project lead, `Trong-Minh Le
   <59441846+letrongminh@users.noreply.github.com>`), configured via `git config user.name` and
   `git config user.email` in the repository. Do not commit using local machine identities; legacy identities have been mapped
   to the project lead in [`.mailmap`](.mailmap). Commits follow Conventional Commits, with body referencing
   task codes:

   ```
   feat(engine): enforce five gate inheritance principles

   TSK-S1-02, TSK-S1-03. Implement FR-GATE-06 → FR-GATE-08.
   ```

5. Complete per **§8**: roadmap progress, changelog entry, specification update if behavior
   changed — in the same PR as code.

### Error Messages: Three-Component Contract

FR-DX-04 mandates that **all** error messages state all three components: **where it went wrong**,
**why**, **how to fix it**. This is not a recommendation — it is structurally enforced: inherit `NeuroEdgeError` and pass all three arguments.

```python
raise GateSchemaError(
    where=f"{path} -> allow_when.{criterion}",                  # where
    why=f"operator {operator!r} is not defined for {kind!r}",    # why
    how="use one of ['eq', 'gte', 'lte'] (Appendix B.2)",         # how to fix
)
```

Do not use `raise ValueError("bad gate")`. Test
`test_invalid_fixture_diagnostic_has_all_three_parts` verifies this across the
entire negative corpus. Error codes (`NE…`) are allocated in PRD
[Appendix B](roadmap/neuroedge-prd.md#appendix-b--standard-error-code-catalog).

### Do Not Print Results You Have Not Computed

Commands (or `--target`s) without an engine exit with **code 2** and name which task will implement
them — invariant `CHANGELOG.md` §3.3 #10; exit code table in `docs/reference/cli.md` §3.

## 3. Changes Requiring an RFC

This is the **sole list** of changes that require an RFC. Other locations (`CLAUDE.md`, RFC template,
`docs/rfc/README.md`) refer here.

| Change | Procedure |
|:---|:---|
| Modifying `schemas/*.json` — all schemas, including `tool-call`, `tool-result`, `error`, `error-codes` (RFC-0015) | **RFC** |
| Modifying gate resolution semantics (`engine/gate_resolver.py`, `engine/constraints.py`) | **RFC** |
| Modifying the three normative traces `fixtures/traces/*.json` | **RFC** |
| Modifying or deleting gates locked in `digests.lock` (`gates/`, `fixtures/gates/valid/`, `fixtures/gates/registry/`, and four kit gates in `fixtures/agents/{home-voice,factory-monitor,gate-camera,blinds}/gates/`) | **RFC**, then `python scripts/check_digests.py --accept <file> --rfc NNNN`; missing RFC causes CI to fail (TSK-S3-16) |
| Changing on-device `NETR` binary tree layout (v1 in [RFC-0003](docs/rfc/0003-bo-cuc-nhi-phan-cay.md), v2 from RFC-0009): `engine/binary_tree.py` ↔ walker `targets/esp32s3/components/ne_gate/` | **RFC** (bump layout version number) |
| Adding gates to `gates/` or `fixtures/gates/{valid,registry}/` | Regular PR — `python scripts/check_digests.py --update` to lock digest |
| Adding negative fixtures, or tool call / voice corpus cases | Regular PR — following bidirectional closure rules below |
| Adding board profiles in `boards/` | Regular PR — requires physical hardware to fill parameters (extended primitives declared only when physical board possesses them, no dummy declarations to pass tests — RFC-0013 §3a). *`test_boards.py` accepts tier-1 reference boards in `REFERENCE_BOARDS` (`neuroedge/hal/board.py`); each `sim-*` profile must have an entry in `SIM_MIRRORS` and not be more capable than the board it mirrors; tier 2/3 awaits RFC-0002* |

Procedure: copy `docs/rfc/0000-template.md`, open a PR **containing only the RFC file**, discuss,
then modify code in a second PR referencing the RFC number. Changes touching `gate.v1` or resolution
semantics require approval from the **lead engineer**. [RFC-0001](docs/rfc/0001-gate-schema-conditional-requirements.md)
is a complete exemplar.

Schema validation alone does not prove a gate is safe; the verification gate is
`neuroedge gate lint` — invariant `CHANGELOG.md` §3.3 #1.

### Adding a Negative Fixture

Every corpus is **bidirectionally closed**: each file has one expected answer entry, each entry has one file.
Tests enforce both directions, so you cannot add a fixture without specifying what it
proves.

| Corpus | File | Expected Answer |
|:---|:---|:---|
| Gate | `fixtures/gates/invalid/` | `fixtures/gates/expected_errors.yaml` |
| Trace | `fixtures/traces/invalid/` | `fixtures/traces/expected_errors.yaml` |
| Tool call | `fixtures/tool_calls/{valid,invalid}/` | `fixtures/tool_calls/expected_results.yaml` — rules in [`docs/spec/tool_calling.md`](docs/spec/tool_calling.md) §9 |
| Board | `fixtures/boards/{valid,invalid}/` | `fixtures/boards/expected_errors.yaml` |
| Integrator contracts | `fixtures/contracts/{tool-call,tool-result,error}/{valid,invalid}/*.json` | `fixtures/contracts/expected_errors.yaml` — one entry per file: `against` (schema, optionally with `#/$defs/…`) and, for `invalid/`, `error: {keyword, path, message_contains}`; tests also require `valid/` files to cover all known `status`, `on_block`, `source`, `reason` values and all catalog error codes |
| Conversational FSM | `fixtures/compliance/voice/*.json` | `fixtures/compliance/voice/expected_results.yaml` — rules in [`docs/spec/voice_fsm.md`](docs/spec/voice_fsm.md) §9 |
| Vision scene | `fixtures/vision/<scene>/` (frames + `scene.toml`) | `fixtures/vision/expected_results.yaml` — frame-by-frame verdict sequence; `fixtures/vision/golden/<scene>.json` is model inference golden for that scene ([`docs/spec/vision.md`](docs/spec/vision.md) §6a, §6c) |
| Remote actuator declaration | `fixtures/actuators/{valid,invalid}/*.toml` | `fixtures/actuators/expected_errors.yaml` — one entry per file: `valid/` has warning count, `invalid/` has **full** ordered error list (`error`, `code`, `where_contains`, `why_contains`); rules in RFC-0018 §3b, §3f, §3k |
| Actuator plugin compliance | `fixtures/compliance/actuators/{valid,invalid}/<dist>/` (installable package, with `pyproject.toml`) | `fixtures/compliance/actuators/expected_results.yaml` — one entry per distribution, one entry per entry point: checks not returning `pass` and their results, and (for `invalid/`) checks targeted by the counter-example; each check must be caught by at least one counter-example ([`docs/spec/extension_sdk.md`](docs/spec/extension_sdk.md) §8) |

```yaml
# fixtures/gates/expected_errors.yaml
ten_fixture.yaml:
  error: GateInheritanceError    # error class
  code: NE2003                   # stable code
  principle: 2                   # violated B.5 principle
  where_contains: "allow_when.risk_level"
  why_contains: "loosens the inherited condition"
```

Then run `pytest -q`: missing either step fails CI. `where_contains` and `why_contains`
match substrings, so error wording may be improved; **error class, stable code, and
principle B.5 must not drift silently**.

## 4. Porting Open Source Code — Obligations Before Writing the First Line

The five source attribution obligations are **legal obligations**, not paperwork
(specification: roadmap §3; deadline: roadmap §3.9). How to fulfill each requirement in this repository,
completed before porting:

| # | Obligation | How to Fulfill in This Repo |
|:---:|:---|:---|
| 1 | License matrix | Update [`NOTICE`](NOTICE): project, version, license, verification date, usage scope |
| 2 | Root `NOTICE` file | One entry per component |
| 3 | In-situ attribution in code | Header comment in ported files, specifying **original file and reference commit** |
| 4 | Attribution in public docs | Do not conceal in source code |
| 5 | Pin versions of all dependencies | `requirements-lock.txt`; nightly builds detect upstream breaking changes |

In-situ attribution template:

```python
# Ported from Pipecat (https://github.com/pipecat-ai/pipecat)
# Source file: src/pipecat/processors/frame_processor.py @ commit <sha>
# License: BSD-2-Clause (Copyright Daily). See NOTICE entry 2.
```

Which licenses are admitted into distribution artifacts: policy **Q-11**
([PRD §15](roadmap/neuroedge-prd.md#15-decision-log)); no strong copyleft is
invariant `CHANGELOG.md` §3.3 #9. Hawkbit approved conditionally under Q-11 (publish modifications if modified); EMQX not used.

## 5. Tests Must Not Skip Silently

A test `skip`ped due to missing dependencies looks like a passing test in summaries.
I0 experienced exactly this: four schema conformance tests were skipped because
`jsonschema` was not installed, while the progress table reported "PASS 100% (4/4)".

Therefore:

- Do not use `pytest.importorskip` for dependencies declared in `pyproject.toml`.
- Dependencies required for conformance are **mandatory** dependencies, not optional.
- CI runs `python -m pytest -q --strict-markers --junit-xml=../junit.xml`
  (`.github/workflows/ci-sim-linux.yml`), then parses `junit.xml` and **fails if skipped
  test count is non-zero or total test count is zero**.
- `python/tests_linux/` requires gpio-sim and is excluded from `testpaths`, running in dedicated job
  `linux-hal` — rather than skipping on machines lacking gpio-sim.
- CLI output is asserted as plain text. `tests/conftest.py` removes
  `FORCE_COLOR` and sets `NO_COLOR` before importing CLI; machine-readable output (`--json`,
  digest) must write directly to stdout without passing through `rich`. Square brackets in `help=`
  must be escaped (`\[mcp.servers]`), otherwise `rich` strips them — `tests/test_cli_help.py`.

When reading test results, check the skip column as well.

## 6. Repository Structure

This is the **sole map** of the repository; other locations refer here.

**Naming and language.** Content is written in English unless a document is Vietnamese by audience (user guides in `docs/user/`, business and partner material in `docs/business/`). Existing Vietnamese file and folder names (`thuat-ngu.md`, `app-di-dong/`, `kien-truc-tong-the.html`…) are kept: tests, CLI strings and generator scripts reference them.

| Path | Contents | Modification Procedure |
|:---|:---|:---|
| `schemas/` | Seven frozen schemas: `gate.v1` · `trace.v1` · `board.v1` · `tool-call.v1` · `tool-result.v1` · `error.v1` · `error-codes.v1` (error code catalog, source of `NE…` structure; RFC-0015) | **RFC** (§3) |
| `gates/` | Sample, resolvable gates including inheritance chains | Adding: regular PR; modifying/deleting: **RFC** (§3) |
| `digests.lock` | JCS digest of all normative gates | Exclusively via `scripts/check_digests.py` (§3) |
| `boards/` | Board capability declarations (TOML) | Regular PR (§3) |
| `pipewire/` | Drop-in `neuroedge-echo-cancel.conf` for software AEC on `linux` (Q-22); packaged into wheel via `hatch_build.py`, located via `neuroedge.paths.echo_cancel_conf()` | Regular PR |
| `fixtures/traces/*.json` | Three normative traces | **RFC** |
| `fixtures/traces/invalid/`, `fixtures/gates/invalid/` | Negative corpus + `expected_errors.yaml` | Regular PR, closed (§3) |
| `fixtures/gates/valid/`, `fixtures/gates/registry/` | Correctly resolving gates; base gates for fixtures | Adding: regular PR; modifying/deleting: **RFC** |
| `fixtures/tool_calls/` | Gated Tool Profile corpus + `expected_results.yaml` | Regular PR, closed (§3) |
| `fixtures/contracts/` | Negative corpus for `tool-call`, `tool-result`, `error` + `expected_errors.yaml` (RFC-0015) | Regular PR, closed (§3) |
| `fixtures/decision_trees/` | Truth tables for C walker | Generated by `scripts/generate_truth_tables.py`, do not edit manually |
| `fixtures/agents/` | Sample agents `villa-concierge`, `home-voice`, `factory-monitor`, `gate-camera`, `blinds`, `driveway`, `voice-door`, `rail-gate` (sensor pack: `digital.in` + `analog.in` + `i2c`), `chat-den-cua` (free lights, door asks owner; demo `demo/i2f-chat-den-cua/`), `aquarium` (fish tank, demo `demo/i2b-be-ca-gia-lap/`), `bridge-lamp` (namespaced call source, RFC-0017), `contract-bench` (one gate per `tool-result.v1` field, Q-83), `fan-pwm` (PWM and feedback), `gate-watch` (camera at a gate, RFC-0012), `rover` (`motion.*`); `neuroedge new --template` copies the first five | Regular PR |
| `fixtures/traces/sensor-pack/` | Sensor pack corpus: three sessions of `rail-gate` on `sim-rpi5`, generated by `scripts/gen_sensor_pack_traces.py` (`--check` runs in tests); `verify` replays across all boards declaring `digital.in`, `analog.in`, and `i2c`, counted separately from three normative traces (RFC-0013 §3f item 7) | Regular PR; regenerate when agent, gate, or sensor contract intentionally changes |
| `fixtures/traces/fine-control/` | PWM and feedback channel corpus: five sessions of `fan-pwm` on `sim-rpi5` (two sessions with recorded `measured` readback on testbed declaring `feedback`), generated by `scripts/gen_fine_control_traces.py` (`--check` runs in tests); `verify` replays across all boards declaring one PWM channel, counted separately (RFC-0013 §3f item 7) | Regular PR; regenerate when agent, gate, or PWM contract intentionally changes |
| `fixtures/traces/motion/` | `motion.*` corpus: four sessions of `rover` on `sim-rpi5` (lease renewal and expiration, BLOCK resets channel to safe state, speed exceeds gate limit), generated by `scripts/gen_motion_traces.py` (`--check` runs in tests); `verify` replays across all boards declaring `motion`, counted separately | Regular PR; regenerate when agent, gate, or motion contract intentionally changes |
| `fixtures/traces/kits/` | Five hardware kits corpus ([`kit-phan-cung.md`](docs/user/kit-phan-cung.md)): two sessions (allow, block) for each agent `villa-concierge`, `home-voice`, `factory-monitor` on `sim-default` and `gate-camera`, `blinds` on `sim-rpi5`, generated by `scripts/gen_kit_traces.py` (`--check` runs in tests); `verify` replays across all reference boards declaring sufficient capabilities, counted separately | Regular PR; regenerate when sample agent, gate, or sensor contract intentionally changes |
| `fixtures/compliance/voice/` | Conversational state machine compliance vector suite + `expected_results.yaml`, shared between Python and C implementations | Regular PR, closed (§3) |
| `python/neuroedge/engine/` | L3 — gate resolution, canonicalization, Gate Engine, decision trees, `NETR` layout, `build` compiler, agent's `esp32s3` firmware generator (`firmware.py`) | **RFC** if changing resolution semantics or `NETR` layout |
| `python/neuroedge/actions/` | `@action`, `c.do()`/`c.say()`, single-use verdict token | Regular PR; boundaries in [`threat_model.md`](docs/spec/threat_model.md) |
| `python/neuroedge/hal/` | L1 — five primitives, board model, `sim.py`, `linux.py`, `audio.py` (desktop PCM: WAV files, VAD, timeline speaker) | Regular PR; see [MCU review](docs/spec/hal_mcu_review.md) |
| `python/neuroedge/models/` | L2 — SystemOne/SystemTwo, local command grammar, knowledge base, `providers/` (LiteLLM, System One API for Jev, adapters; `common.py`: shared logic for all provider tables — endpoints, no duplicate keys, adapter loading) | Regular PR |
| `python/neuroedge/perception/` | L2 — conversational state machine (`voice_fsm.py`), its driver (`voice_session.py`: audio in, STT, TTS, barge-in), `providers/` (STT/TTS: OpenAI audio adapter, mock provider; `[stt]`/`[tts]` tables), `vision/` (vision model interface, mock model, `[vision]` table, frames → gate facts, `vision_fact` events) | Regular PR; behavior per [`voice_fsm.md`](docs/spec/voice_fsm.md) and [`vision.md`](docs/spec/vision.md) |
| `python/neuroedge/sim/` | `SimSession` (text typing REPL), `ui.py` (local `--ui` page) | Regular PR |
| `python/neuroedge/mcp_server.py`, `mcp_host.py`, `mcp_desktop.py`, `mcp_http.py` | MCP server · System 2 as MCP host · Claude Desktop configuration · MCP over HTTP (mTLS, tokens) | Regular PR |
| `python/neuroedge/guard.py`, `proxy_mcp.py`, `proxy_http.py` | `Guard` (safety core without an agent, RFC-0016) · `proxy mcp` and `proxy http` (Q-70) | Regular PR; boundaries in [`threat_model.md`](docs/spec/threat_model.md) |
| `python/neuroedge/install.py`, `install_pins.json`, `isolation.py`, `pairing.py` | `neuroedge install` and its pinned inputs · worker isolation · pairing the box with a chat channel or brain (Q-83, [`deployment_profiles.md`](docs/spec/deployment_profiles.md)) | Regular PR |
| `python/neuroedge/plugins/`, `sdk/` | Extension points: actuator plugins and conformance suite, SDK surface ([`extension_sdk.md`](docs/spec/extension_sdk.md), RFC-0016) | Regular PR |
| `python/neuroedge/studio/` | NeuroEdge Studio server and page; **paused** (Q-72, TSK-I1-04), spec [`studio.md`](docs/spec/studio.md) | Regular PR |
| `examples/guard/` | Runnable `Guard` example: `guard.toml`, gates, `run.py` | Regular PR |
| `python/neuroedge/testing/` | Action CI — recorder, player (replay), assertions, golden, `tool_corpus`, `voice_corpus`, `uart` (traces from device UART) | Regular PR |
| `python/neuroedge/viz/` | `trace view`, Perfetto export | Regular PR |
| `python/neuroedge/templates/` | Project templates for `neuroedge new` and primitive templates for `neuroedge add` (`add/`) (`*.tmpl`, pure Python generator) | Regular PR |
| `python/neuroedge/cli/` | Typer CLI: `main.py`, `run.py` (REPL), `explain.py` | Regular PR |
| `python/neuroedge/errors.py`, `trace.py`, `paths.py`, `net.py` | Three-component error contract · trace validation · asset location (checkout, editable, wheel) · HTTP to providers (no proxy, no redirects, bounded timeouts) | Regular PR; touching `paths.py` requires running `scripts/wheel_smoke.sh`; a new error class requires a code in `schemas/error-codes.v1.json` **and** a row in PRD Appendix B (`test_error_catalog.py` fails if either is missing) |
| `python/tests/` | Main test suite (`testpaths`) | Regular PR |
| `python/tests_linux/` | Tests on gpio-sim, `linux-hal` job | Regular PR |
| `python/hatch_build.py`, `pyproject.toml`, `requirements-lock.txt`, `pip-audit-ignore.txt`, `LICENSE` | Packaging (assets into `neuroedge/_data/`, root README into metadata) · pinned dependencies · approved `pip-audit` exceptions (`pip-audit` job) · copy of root `LICENSE` | Regular PR; run `scripts/wheel_smoke.sh` |
| `targets/esp32s3/` (root) | ESP-IDF project: `CMakeLists.txt`, `sdkconfig.defaults` (16 MB flash, PSRAM, FreeRTOS 1000 Hz), `sdkconfig.qemu` (overlay for QEMU), `partitions.csv` (factory + OTA A/B) | Regular PR; `firmware-qemu` job |
| `targets/esp32s3/main/` | ESP-IDF firmware, shared across all agents: `main.c`, memory benchmarking framework (including heap line `NEUROEDGE_HEAP_JSON`), gate self-test on linked agent (records trace `NE1`), normative trace replay (`trace_vectors.c`); `vectors/` generated by `scripts/gen_firmware_vectors.py` | Regular PR; modifying normative traces, gates, or actions ⇒ regenerate `vectors/` |
| `targets/esp32s3/components/ne_agent/` | Agent component generated by `neuroedge build --target esp32s3`, here for sample agent `home-voice`: `NETR` tree, gate · pin · action tables, self-test checks with host engine verdicts | Do not edit manually — `scripts/gen_firmware_gates.py` (`--check` runs in pytest) |
| `targets/esp32s3/components/ne_gate/` | C99 walker and C token ledger | Regular PR; `NETR` layout: **RFC** |
| `targets/esp32s3/components/ne_boot/`, `ne_config/`, `ne_console/`, `ne_hal/`, `ne_ota/`, `ne_brain_bridge/` | Boot guard · encrypted NVS configuration · serial console · HAL · OTA A/B · bridge to the brain (Q-79, Q-83) | Regular PR; `firmware-qemu` job |
| `targets/esp32s3/components/ne_trace/` | `NE1` trace stream over UART — C99 format, no global variables ([`simulation_coverage.md`](docs/spec/simulation_coverage.md) §4) | Regular PR; `firmware-qemu` job |
| `targets/esp32s3/ui/` | Device LVGL interface: screens (`ne_ui.h`), vi/en character tables, pre-rendered Be Vietnam Pro fonts, golden images and dedicated host harness; UI language rules in [`docs/spec/ui.md`](docs/spec/ui.md) | Regular PR; modifying screens, character tables, fonts, or golden cases ⇒ `bash scripts/run_ui_golden.sh --update`; `ui-golden` job |
| `scripts/` | CI and release tooling | Regular PR |
| `.github/` | Five workflows in `workflows/` — job list in `docs/reference/cli.md` §5; `dependabot.yml` (pins Actions SHAs), `actionlint.yaml` | Regular PR |
| `docs/rfc/`, `docs/spec/` | RFCs, normative specifications (`lab_mcp.md` is historical: Lab removed, Q-77, Q-88) | Regular PR |
| `docs/reports/` | Dated spikes and studies (`README.md` lists them): memory benchmark, esp-emulator spike, market snapshot, MVP estimate (superseded by Q-72/Q-77 for I3–I8; see banner) | Regular PR |
| `docs/business/app-di-dong/` | Home web and app (I2g box API and home web, I2h native app; Q-91, Q-92): user stories, BRD, SRS, clickable prototype | Regular PR |
| `LICENSES/`, `NOTICE`, `LICENSING.md` | License texts of ported code (zclaw, MimiClaw, Apache-2.0, OFL) · third-party component matrix (Q-11) · licensing summary | Regular PR; license policy per Q-11 |
| `CLAUDE.md` | Instructions for coding agents | Regular PR |
| `docs/architecture/` | Product architecture: `README.md` · 10 chapters `00`–`16` (gaps after Q-77, in English; the `vi/` folder was flattened and the `en/` tree retired, see git history) · `assets/svg/` + `assets/excalidraw/` (posters **generated** from `scripts/gen_architecture_diagrams.py`, do not edit manually) | Regular PR — update poster models then re-run script; mermaid blocks verified by `scripts/check_architecture_mermaid.py`; new inter-package import edges declared in `python/tests/test_architecture_layers.py`; content references code, does not duplicate (§8.1) |
| *(git history)* | Closed documents not retained in working tree: plans, Phase 1 review minutes, old proposals, the demand-gate interview kit and merged design notes. Retrieve with `git log --all -- <path>` then `git show <commit>:<path>` | Do not restore into tree; reference current truth from PRD, roadmap, architecture |
| `docs/business/` | Router `README.md` · product proposal `product-proposal.md` · BRD `brd-ambient-intelligence.md` (Q-85) · `app-di-dong/` (row above) · `doi-tac/` (row below; interview guide `doi-tac/phong-van.md`) · `kien-truc-tong-the.html` — overall architecture page for non-technical stakeholders: diagrams hand-drawn (source of truth remains `docs/architecture/`), progress blocks between `GENERATED` markers written from roadmap §0 | Regular PR — re-run `python3 scripts/gen_architecture_progress.py` when the roadmap changes; never edit a generated block by hand |
| `wireframe/` | Reference HTML wireframes for UI (snapshot `ui.css`, unpackaged) — currently only the Studio wireframe (`studio-v1.html`; Lab wireframes removed, Q-77) | Regular PR |
| `demo/` | Per-increment demo scenarios (`demo/<increment>/`): narrative script, commands, real outputs, verified replay commit; catalog in `demo/README.md` (Q-49) | Regular PR; reviewer replays scenario |
| `docs/user/` | User documentation; `thuat-ngu.md` is the sole symbol decoder; `trang-thai.md` generated from roadmap §0 | Regular PR — `python3 scripts/gen_user_status.py` |
| `docs/user/doi-tac/` · `docs/business/doi-tac/` · `fixtures/ha_mcp_double/` | Partner trial package (Q-70): three runnable guides, limitations page, feedback form · agreements list, feedback channels, benchmark sessions · Home Assistant MCP Server **mock** for guides | Regular PR — all command blocks in guides are marked (`scripts/guide_runner.py`, `test_partner_guides.py`); run `scripts/partner_guides_check.sh <wheel>` when guides change |
| `docs/README.md` | Docs router: where to start by reader, what lives in each `docs/` folder | Regular PR |
| `docs/reference/cli.md` | The one place for commands: every command, expected output, exit codes, error messages, CI jobs | Regular PR — update in the same PR as a CLI or CI change |
| `docs/release.md` | Release procedure: internal tags before I6, PyPI from I6 | Regular PR |
| `README.md` | Landing page and PyPI page (absolute links) | Regular PR — `tests/test_readme_quickstart.py` |
| `roadmap/` | Two product documents: roadmap (progress) and PRD (requirements, decisions) | Per file in rows below |
| `roadmap/neuroedge-roadmap.md` | Single roadmap (Q-39): phases and release milestones (§0.5), increments I0–I8 and I2a–I2h (removed items: §6), task statuses, exit criteria, forecasts, dependencies, release tags, scope cut ladder | Regular PR, per §8; divergence prevention rules R1–R12 in roadmap §2.4 |
| `docs/spec/lab_mcp.md` | NeuroEdge Lab design, **historical** (Lab removed, Q-77, Q-88; the draft robot node protocol RFC was deleted, see git history). No schedule, no status, no exit criteria (R1, R8) | Regular PR; mergeable even during Beta freeze (R12) |
| `TODOS.md` | Evaluated and intentionally deferred items, with trigger milestones | Regular PR |

## 7. CI

Workflows, jobs, and gates: `docs/reference/cli.md` §5. `ci-sim-linux.yml` must be green prior to
merge.

## 8. Completing a Task — Updating Documentation, Progress, Changelog

This is the **sole place** defining what must be done when a task is finished. Roadmap §0.4,
roadmap §11.2, `CLAUDE.md`, and the PR template refer here.

A task is **not done** until the updates below are included **in the same PR** as the code.

### 8.1 Every Truth Has Exactly One Place

| Truth | Sole Place | Allowed Elsewhere |
|:---|:---|:---|
| Task status, artifact, commit | Task table in increment section, `neuroedge-roadmap.md` §4–§8 | Reference task code |
| Objective, entry conditions, measurement signals, staffing of an increment | Card at the head of that increment's section (roadmap §4–§7) | Reference increment code (`I3`) |
| Exit criteria met or not, with evidence | Exit criteria list directly below increment task table | Reference increment code + criterion number (`I3 criterion 2`) |
| Schedule: forecast date, dependencies, release tag | Roadmap §0.2 (increment table) | Reference increment code; do not copy dates or tags |
| Progress overview, current test count, blocked items | Roadmap §0.1–§0.2 | Do not copy numbers |
| User release milestones and per-milestone increments | Roadmap §0.5 ("User Release Milestones" table) | The architecture page progress blocks and poster E-09 read this table at generation; other places reference milestone name or number |
| What a person can do today: capability, how to try it, where it runs, evidence | `docs/architecture/00-overview.md` §6.1 | Chapter 12 of the architecture page reads it at generation; other places reference the section |
| Next steps, what is currently underway | Roadmap §0.3 (Handoff Card) | None |
| Scope cut ladder | Roadmap §9 | Reference tier or increment |
| Measurement values B1–B5 (and full A1 measurement) | Roadmap §5.5 | Thresholds in PRD §11; other places reference code |
| Design (no schedule, no status) | `docs/spec/` (`lab_mcp.md` is historical) · `docs/rfc/` | Roadmap links to it; design notes reference TSK codes, do not state status (R1) |
| Product risks (`R-n`) | PRD §13.2 | Reference code |
| What has changed | `CHANGELOG.md` §1 | None |
| How to run, commands, expected output, CI workflows and jobs | `docs/reference/cli.md` | Root `README.md` (also PyPI landing page, so all links absolute): max 3 quickstart commands, linking §2 — `tests/test_readme_quickstart.py` runs those exact commands |
| Invariants that must not be broken | `CHANGELOG.md` §3.3 | Reference invariant number |
| Which changes require an RFC | §3 | Reference §3 |
| Repository structure | §6 | Reference §6 |
| Decisions | `neuroedge-prd.md` §15 (`Q-N` codes) | Reference `Q-N` code |
| License policy (allowlist) | `neuroedge-prd.md` §15, Q-11 | `NOTICE` lists per-component matrix, referencing Q-11 |
| Error codes `NE…`: existence, class name, parent, status | `schemas/error-codes.v1.json` (RFC-0015, Q-66) | Reference code; `errors.py`, PRD Appendix B, and `targets/` are test-verified against catalog |
| Error message text (when, why, system reaction) | PRD Appendix B | Reference code |
| Meaning of a code / symbol | `docs/user/thuat-ngu.md` | Reference code |
| Requirements and specifications | PRD (`FR-*`, `NFR-*`) · `docs/spec/core_contracts.md` · `docs/rfc/` · `docs/spec/` | Reference code |
| Intentionally deferred work | `TODOS.md`, with trigger milestone | Reference item number |
| Demo scenario for an increment | `demo/<increment>/kich-ban.md`; catalog in `demo/README.md` (Q-49) | Reference directory; do not duplicate commands or output |

Other locations **reference the code** (`TSK-S2-03`, `Q-17`, `RFC-0004`, `TODOS.md #15`), rather than copying
content. When copying a sentence feels necessary for readability, that is a signal to reference the code instead.

### 8.2 Checklist, in Order

1. **Green build.** `pytest -q` → 0 failed, 0 skipped · `ruff check .` and
   `ruff format --check .` (in `python/`) clean · `neuroedge gate lint` green. CI also executes
   gates in `docs/reference/cli.md` §5 (digest, negative corpus, licensing, wheel).
2. **Progress, in roadmap.**
   - Task rows: status cell has **exactly one** glyph (R9) — ✅ done · 🟡 in progress or partially
     completed · ⏳ not started · ⏸ deferred · 🔴 blocked. Done: `✅ Done (YYYY-MM-DD)` +
     artifact path + commit or PR. Deferred: `⏸ Deferred` + one-line reason + milestone (and a
     `TODOS.md` entry). Blocked: `🔴` + blocker.
   - New tasks: assign codes per family prefix in roadmap §2.4 — if work belongs to an existing family, use that prefix;
     otherwise `TSK-I<n>-<nn>` where `n` is the first increment scheduling it. Codes are never
     reassigned; moving a task to another increment moves its row.
   - Exit criteria: `[x]` + **reproducible evidence** (command + result, or test name).
   - Demo (Q-49): when an increment — or its hardware-free portion — completes, add
     or rerun scenarios in `demo/<increment>/`, record verified replay commit, and update table
     in `demo/README.md`. Reviewer reruns scenario.
   - §0.2: update increment "Progress" column whenever one of its tasks changes status (number of ✅
     over total tasks, R10), and "Status" column if needed. "Forecast" column updates only **in the same PR
     with evidence** driving the change, shifting all dependent increments simultaneously (R5).
   - §0.1: update metrics (test count, blocked items).
   - Capabilities: when a task changes what a person can do (a command starts working, a target moves
     from QEMU to a board, `planned` becomes `partial`), update its row in `docs/architecture/00-overview.md`
     §6.1 and run `python3 scripts/gen_architecture_progress.py`; `test_architecture_progress.py` fails otherwise.
   - §0.3: **replace** stale entries, do not append. See §8.3.
3. **Changelog.** One entry in `### [Unreleased]` at top of `CHANGELOG.md` §1,
   under the appropriate section *Added / Changed / Fixed / Removed*:

   ```markdown
   - **TSK-S2-03 — Gate Engine returns verdicts.** `python/neuroedge/engine/gate.py`.
     Verify: `pytest tests/test_gate_engine.py`. (FR-GATE-03, Q-17)
   ```

   Maximum 3 lines, starting with task code (or `Q-N` / `FR-*` if no task exists); may prepend
   increment code (`**I3 · TSK-S4-01 — …**`). First sentence is **observable** change;
   followed by location and verification method. **One feature per entry:** if task already has
   an entry in `[Unreleased]`, edit it to reflect final state, do not add a
   new entry. Decisions only reference `Q-N` codes — details live in PRD §15. Extended rationale and context
   belong in PR or RFC. If commands or expected output change, update `docs/reference/cli.md`. If
   adding an invariant, update §3.3.
4. **Specifications, only when behavior differs from spec.** Update FR/NFR or Appendices to match. Changes
   listed in §3 **require an RFC**. New decisions receive a `Q-N` code in PRD §15.
5. **Deferrals.** Work cut from tasks goes to `TODOS.md`, with trigger milestone — an increment, task
   code, or observable event, not calendar weeks or months. When a task completes work in a `TODOS.md` item,
   **delete** that item and record in changelog. For items whose trigger milestone
   mentions the completed task, **re-evaluate the milestone** — if reached, execute or rewrite.
6. **Scan for stale references.** For each updated truth (status, metric, name),
   search for old codes or numbers across `*.md` and update. A sentence that was true yesterday but false today
   is worse than no sentence at all.

### 8.3 Writing Rules

- **Replace, do not append.** Status tables and Handoff Card describe *the present*. History
  belongs in `CHANGELOG.md` and git.
- **Keep Handoff Card concise.** *Just completed* lists only task codes or decisions from the
  **most recent session**, one line per item. *Next steps* has at most 5 items, strictly in execution
  order. *Notes* retains only items not already in `CHANGELOG.md` §3.3, one line per item with code.
- **Do not record volatile numbers outside their home.** Test counts, fixture counts, and progress
  live only in roadmap §0.1–§0.2; forecast dates only in §0.2. Elsewhere, write conditions
  (*"0 failed, 0 skipped"*, *"all files in `invalid/` are rejected"*), not numbers.
- **Schedule using increments and absolute dates.** Schedule via increment codes (`I3`, "after
  I8") or absolute dates (`2026-11-16`); do not use `Week N`, `Month N`, `Sprint N`,
  or "next week" for new schedules (R6). Duration measures from when an increment opens
  ("2 weeks after I8 opens"). Legacy sprint and block names are used only for historical reference.
- **Reference by code or section**, not line number (`file.md:NNN`) — R11.
- **Short sentences, one idea.** Tables when there are three or more items of the same structure. English;
  code, commands, paths kept unchanged.
