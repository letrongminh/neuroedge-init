# 08 · Non-functional requirements → tactics → evidence

> **Scope:** which tactic the architecture uses to satisfy each NFR group of PRD §9, and where the
> evidence is today. **Sources:** PRD §9 (requirements, thresholds), PRD §11.1 (A1–A13), tests in
> `python/tests/`, CI jobs in `.github/workflows/` (single list: `CHANGELOG.md` §2.5).

Evidence labels: **checked** — a test or CI job runs on every PR · **partial** — a measurement tool or a
partial check exists · **not measured yet** — no evidence yet · **`planned · Q-72`** — new requirements of [Q-72](../../../roadmap/neuroedge-prd.md#15-sổ-quyết-định) for the operating agent, chat channels and NeuroEdge Blueprint (I2d, I2e); no code yet, so no evidence yet. These rows carry no NFR identifier yet: identifiers are assigned in PRD §9, the only place that records thresholds.

## 1. Overview

| Group | Question | Main architectural tactic | Status |
|:---|:---|:---|:---|
| Security (SEC) | Is there any path to a pin that does not go through a gate? | A single path; a HAL with no token ledger refuses; callers are untrusted | checked (SEC-01, 09); device: not yet |
| Reliability (REL) | What happens when a part fails? | Fail-closed default; circuit breaker; normative traces frozen | checked (REL-02); REL-01, 03: not yet |
| Resources (RES) | Does it fit the chip? Does it run offline? | Binary `NETR`, non-allocating walker; local fallback | partial |
| Performance (PERF) | Is it fast enough? | Time budget per gate, fail-closed enforcement; per-stage measurement | tools exist; thresholds **not measured yet** |
| Privacy (PRIV) | What data is stored? | No audio stored; hashing at the source by default | checked (PRIV-02, 03, 04); PRIV-01: no dedicated test yet |
| Observability (OBS) | Can we understand what happened? | One trace per session (Q-72 24/7 runtime: one chain of segments, each replayable — `planned`, I2d); per-stage latency; System 1/2 ratio | checked |
| Compatibility (COMP) | Can it be opened and swapped? | Schemas opened via RFC; providers swappable; Python 3.11+ | partial (ARM64 not yet) |
| Operating agent, chat, NeuroEdge Blueprint (`planned · Q-72`) | Is running 24/7 safe, how much does it cost, does data leak? | Two processes (trusted runtime, untrusted LLM worker); reflexes need no LLM; egress; approval records; segmented traces | not yet — I2d, I2e |

## 2. Security — NFR-SEC

| NFR | Tactic | Evidence | Status |
|:---|:---|:---|:---|
| SEC-01 No shortcut to actuator | `c.do()` is the only path; one-time tokens; the HAL refuses by default; calling `@action` directly ⇒ `NE1001` | Shortcut table in `docs/spec/threat_model.md` §2, one test per line; `tests_linux/test_gpio_sim.py` proves the kernel line does not change when blocked | checked; no penetration test yet |
| SEC-02, 03 Secure Boot, flash encryption, TPM, mic switch | — | TSK-S6-05, TSK-W2-03 (status: roadmap) | not yet |
| SEC-04, 05 device ↔ cloud mTLS, per-device certificates | — | Tied to Fleet OS (I9); mTLS or PSK between Pi and node is planned separately (TSK-W2-01, I14, does not need Fleet OS) → [`15`](15-target-architecture.md) §4.3 | not yet |
| SEC-06 Signed firmware, verified on chip | RSA-3072 verified on every OTA image; bad or unsigned ⇒ rejected, slot erased; high-water mark blocks downgrade | job `ota-rollback` (phases a–g), `test_c_ota_policy.py` | partial — on QEMU; Secure Boot, eFuse missing |
| SEC-07 Sandbox third-party code restricting access to sensitive actuator pins (P0 v1.1, PRD §9.4) | Registry permission sandbox (TSK-K3-05, → [`15`](15-target-architecture.md) §3.2) | — | not yet |
| SEC-08 TLS to providers, provider recorded in the trace | Provider name and model in `system_one_call`, `system_two_call`; no prompt, no key recorded | `test_providers.py::test_each_model_call_is_traced_without_prompt_or_key` | partial — no TLS 1.3 test yet |
| SEC-09 MCP stdio only; LLM and MCP client untrusted | `dispatch()`: schema check, `call_source` assigned by the runtime, no self-confirming tools | threat model table §2b; corpus `fixtures/tool_calls/` | checked |
| SEC-10 Third-party plug-ins (Q-67) | A plug-in running in-process is code the operator trusts (`docs/spec/threat_model.md` §3): loaded only when explicitly enabled; origin (package, version, file hash) printed and recorded in the trace; no `neuroedge.sdk` API hands a hardware handle to a bridge or fact source (FR-EXT-02, FR-EXT-03) | Plug-in loader and per-kind compliance suite (TSK-I2c-11, TSK-I2c-12; RFC-0016 is still a draft) | not yet — I2c |
| Data leak prevention (`planned · Q-72`, I2d) | The runtime decides what the LLM worker *sees* and sends only to destinations the user declared (LLM provider, chat channel, relay, webhook); the LLM worker's network is blocked at the operating-system level, reaching only the declared provider endpoint; sending to an undeclared destination is blocked and traced. The goal is to prevent hacking, prompt injection and theft — not to restrict flows the user builds. Residual risk: a tricked worker can still send allowed data to an allowed destination | Contract: [`07`](07-data-contracts.md) §12.3; tests when code lands | not yet |
| Approvals over chat (`planned · Q-72`, I2d, pending the RFC for the `chat:<id>` source) | Approval record `{id, nonce, expiry, change digest, approval summary ≤ 5 lines}`; the runtime checks that the sender was paired locally, is not a group, the nonce is unused, the record has not expired by the monotonic clock, and the digest matches; the LLM worker never approves; approvals do not go through the relay. Revocation, pairing expiry, approval cap: deferred (`TODOS.md` #62) | Flow: [`06`](06-runtime-flows.md) §11.4 | not yet |
| BYOK key and bot token (`planned · Q-72`, I2d) | The user's LLM key lives only in the LLM worker process; the chat bot token lives only in the runtime; neither enters the trace; the process holding the HAL does not hold the LLM key | — | not yet |
| NeuroEdge Blueprint install checks the digest (`planned · Q-72`, I2e) | The digest covers the whole package (kit, firmware, contract templates, detectors, evidence traces), checked at install; mismatch ⇒ refused with a three-part error; the package only declares; a `safe_state` other than `off` comes only from `board.v1` with an interlock; evidence is marked "unsigned" | Contract: [`07`](07-data-contracts.md) §12.2 | not yet |

## 3. Reliability — NFR-REL

| NFR | Tactic | Evidence | Status |
|:---|:---|:---|:---|
| REL-01 OTA at team scale | A/B updates, confirmation after self-test, rollback | job `ota-rollback` on QEMU; scale needs Fleet OS | not yet (premise on QEMU) |
| REL-02 Degraded default is block | `budget.fail` defaults to `closed`; `fail: open` is not inherited, still blocks on a known "no"; the circuit breaker only routes. *Will change under Q-72 (`planned`, pending the conditional-safety RFC):* for **commands**, still "when unsure, block"; added: a degraded actuator returns to the `safe_state` declared in `board.v1` (default `off`, so every existing profile keeps its behaviour) | Matrix A4: `test_fail_closed.py`; `test_safety_regressions.py` | checked (command part); `safe_state` part: not yet |
| REL-03 Nightly run on real boards | Workflow `nightly-hardware.yml`; job `memory-spike` needs a runner with a Box-3 and **says clearly it is skipped** when there is none | No runner yet | not yet |
| REL-04 Old traces still replay after a minor upgrade | `trace.v1` envelope frozen; three normative traces frozen; firmware rejects (does not compare) traces older than itself | `test_golden.py`, `test_trace_vectors.py` | partial — no minor release yet to cross-compare |
| Runtime alive 24/7 (`planned · Q-72`, I2d) | The runtime runs under systemd and restarts itself; when the LLM worker dies or hangs, the runtime keeps running reflexes, detectors and hard-template alerts and restarts the worker; durations, approval expiry and the watchdog use the monotonic clock | Failure branches: [`06`](06-runtime-flows.md) §11.6 | not yet |
| Reflexes when the network or the LLM is lost (`planned · Q-72`, I2d) | The mission compiler lowers clauses to the lowest tier (reflex on an MCU with `ne_gate`, skill on the host); losing the network, losing the LLM or a relay outage does not touch the safety part; chat channel down ⇒ bounded queue + local alert on the UI. Wall-clock fact `unsynced` ⇒ time-window clauses treat it as a missing fact (fail-closed) | Checked on simulation G1 `sim`, G2 `linux` on gpio-sim, G3 ESP32 firmware (Q-72) | not yet |

## 4. Resources — NFR-RES

| NFR | Tactic | Evidence | Status |
|:---|:---|:---|:---|
| RES-01 24-hour stability on board | No allocation on the audio path (RB-1…RB-4, `docs/spec/hal_mcu_review.md`) | TSK-S6-06 (status: roadmap) | not yet |
| RES-02 Free SRAM, PSRAM (Q-3) | Walker, token ledger, trace buffer use no static RAM; state is allocated by the application | jobs `firmware-size`, `firmware-qemu`; numbers in `memory_spike_report.md` §4.1 | partial — static floor and QEMU heap; PSRAM not measured yet |
| RES-03 Firmware size ≤ A/B slot | Binary tree instead of JSON; no CEL on chip | jobs `firmware-size`, `ota-rollback`, `nightly-hardware` | checked |
| RES-04 Safety functions run offline | Local command grammar is the fallback for every model; no fallback ⇒ `gate_unreachable` | `test_fail_closed.py`, `test_offline_fallback.py`, trace `network_offline.json` | checked on `sim`/`linux`; `esp32s3` not yet (TSK-S5-07) |
| LLM cost cap (`planned · Q-72`, I2d) | `llm_budget` declared in the mission contract; deterministic detectors run first, and the LLM is called only when there is an event; cap reached ⇒ reflexes and hard-template alerts keep running, only the analysis is lost | — | not yet |
| Message budget (`planned · Q-72`, I2d) | The agent's proactive reports are batched and limited by a configurable message budget, so the chat channel does not become a source of noise; details belong to FR-AGT (PRD) | — | not yet |

## 5. Performance — NFR-PERF

The architecture measures every performance threshold — each turn records `turn_latency` with the stages
`perception`, `system_two`, `gate`, `action`, `other`, and every model call records latency, tokens,
cost. But **no latency or cost threshold is measured yet** against PRD §9.1, because there is no
real-time voice session and CI does not call real models.

| NFR | Tactic | Evidence today |
|:---|:---|:---|
| PERF-01, 07 End-to-end voice latency | Voice pipeline split into stages; STT/TTS run in the cloud or host | Measurement tool: `test_turn_latency.py`; thresholds: not measured yet |
| PERF-02 Local gate evaluation | Pre-compiled decision tree; traversal O(number of nodes) | Budget enforced and fail-closed (`test_gate_engine.py`); P95: not measured yet |
| PERF-03, 04 Evaluation needs cloud facts; structured decision | The model deadline is bounded by the gate's remaining budget | `test_system_one_cloud.py`; P95: not measured yet |
| PERF-05 Savings from two-model routing | Grammar and System 1 answer first, System 2 only when needed | Ratio and cost per session in `session_summary`; savings: not measured yet |
| PERF-06 Sample Action CI runtime | The agent's test runs on `sim`, no network | The sample test runs; no time assertion yet |

## 6. Privacy — NFR-PRIV

| NFR | Tactic | Evidence | Status |
|:---|:---|:---|:---|
| PRIV-01 Audio not stored by default | Audio events carry metadata only (energy, duration, digest) | No PCM field anywhere in the code | by design, no dedicated test yet |
| PRIV-02 Cloud-first, user chooses the provider | Every model behind a protocol; self-written adapters | `test_providers.py` | checked |
| PRIV-03 Traces store decisions by default, not raw data | Hashed at the source by default; `--raw` is the explicit opt-in that keeps text verbatim, and that trace carries `metadata.anonymized = false` | `test_recorder.py::test_the_default_hashes_raw_text_and_keeps_every_decision`, `test_cli_run.py::test_trace_out_writes_a_valid_trace_of_the_session`, `test_uart_trace.py::test_anonymize_hashes_raw_text_at_the_source` | checked |
| PRIV-04 Hashing at the source does not break replay | `TraceRecorder` hashes `text`, `utterance`, `transcript` | `test_recorder.py` (including `test_record_replay_matches_between_the_default_and_a_raw_trace`), `test_voice_speech.py`, `test_uart_trace.py` | checked |

## 7. Observability — NFR-OBS

| NFR | Tactic | Evidence | Status |
|:---|:---|:---|:---|
| OBS-01 One session, one complete trace | The session's `EventLog`; `session_summary` computed on export, exactly once. *Will change under Q-72 (`planned`, pending a `trace.v1` RFC):* the 24/7 runtime writes a chain of segments, each segment replayable ([`07`](07-data-contracts.md) §7) | `test_turn_latency.py`, CI step "three normative traces valid" | checked (command sessions); segment chain: not yet |
| OBS-02 System 1/2 ratio, cost, every gate outcome | `turn_latency.path`, `system_two_usage` | `test_turn_latency.py` | checked |
| OBS-03 Per-stage latency comparable to `p95_latency_ms` | Nested `TurnMeter.stage` does not double count | `test_turn_latency.py` | checked |
| Trace retention and write cadence on the home machine (`planned · Q-72`, I2d) | Keep 30 days locally; older segments are compressed then deleted, or exported through the relay encrypted on the home machine; flushed on a timer (about 10 seconds, configurable) and **immediately** on a blocking verdict or an approval; a power loss loses at most the tail of ordinary events, and `replay` reports a truncated segment | Measure the size of 30 days of traces on G1 `sim` (fast-forwarded), then record the number in PRD §9 | not measured yet |

## 8. Compatibility — NFR-COMP

| NFR | Tactic | Evidence | Status |
|:---|:---|:---|:---|
| COMP-01 Core license and standards (Q-45) | PolyForm Noncommercial code; `schemas/`, `docs/spec/`, `fixtures/compliance/` Apache-2.0 | `test_packaging.py` | checked |
| COMP-02 No safety feature locked behind a paid account | The safety core is entirely in the package | Boundary review, no test | by design |
| COMP-03 Every cloud service behind a swappable interface | `models/providers/`, `perception/providers/` | `test_providers.py` | checked |
| COMP-04 Open schemas, governed via RFC | `docs/rfc/`, `digests.lock`, job `frozen-artifacts` | `test_schemas.py`, `test_digests_lock.py` | checked; public URL at I6 |
| COMP-05 Python 3.11+ | `requires-python >= 3.11` | CI matrix 3.11 / 3.12 / 3.13 | checked |
| COMP-06 `linux` on ARM64 and x86-64 | — | Every job runs x86-64; no ARM64 job yet | partial |

## 9. v1.0 acceptance criteria (A1–A13)

| # | Criterion | Related NFR | Evidence today |
|:---:|:---|:---|:---|
| A1 | TTFV under 10 minutes | — | not measured yet; only a proxy (`test_readme_quickstart.py`, `wheel-smoke`) |
| A2 | `verify` 100 % on three targets | REL-03, COMP-05/06 | `sim` + `linux` pass; `esp32s3` on QEMU, decision level |
| A3 | No shortcut to actuator | SEC-01, 09 | threat model test table; no penetration test yet |
| A4 | Fail-closed 100 % | RES-04, REL-02 | `test_fail_closed.py`, `test_safety_regressions.py` |
| A5 | Safe gate inheritance | — | corpus `fixtures/gates/invalid/`, `gate lint` in CI |
| A6 | 24-hour stability on chip | RES-01/02/03 | not measured yet |
| A7 | Traces 100 % valid | REL-04, PRIV, OBS | validated in CI, including UART traces |
| A8 | Docs, three runnable samples | — | three samples have tests; not checked on a clean machine by a third party yet |
| A9 | Public schemas with a compliance suite | COMP-01→04 | partial — seven schemas in `schemas/`, `$id` asserted (`test_schemas.py`); compliance corpora exist: `fixtures/compliance/voice/` (voice), `fixtures/tool_calls/` (Gated Tool Profile) and `fixtures/contracts/` (board, error, tool-call, tool-result; `test_contracts.py`), under Apache-2.0 (Q-67); not yet served at a public URL (TSK-I6-02, I6) and no evidence yet that a third party has run them |
| A10 | Every extension primitive on three targets (FR-HAL-08, Q-53) | REL-03, COMP-05/06 | partial — RFC-0007, RFC-0009 → RFC-0013 approved; `digital.in`, read-only I2C, `analog.in`, vision and the envelope done on `sim` and `linux` (job `linux-hal`), PWM and `motion.*` done on `sim` (I2a); `verify` does not yet replay the `fan-pwm` and `rover` agents; `esp32s3` not started (I3a) |
| A11 | Building by conversation under contract (NeuroEdge Lab over MCP, Q-55, Q-71; measured on two clients) | SEC-01 | not started (I4a, I5a) |
| A12 | Sample kits buildable in a day (Q-52) | — | partial — five kits with BOM, wiring diagram, golden traces and tests on `sim`, `linux` (I2b); not yet built on real hardware (`TODOS.md` #59), TTFV not yet measured on people; A12 is measured at I7 |
| A13 | Open platform: a third party wires up a new ecosystem in ≤ 1 day, wraps an existing MCP server in ≤ 3 commands (Q-67) | SEC-10 | not started — I2c; to be measured by the `neuroedge-muse` test (TSK-I2c-17) and a CI test that installs an out-of-repo plug-in |
