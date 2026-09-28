# 08 · Non-functional requirements → tactics → evidence

> **Scope:** which tactic the architecture uses to satisfy each NFR group of PRD §9, and where the
> evidence is today. **Sources:** PRD §9 (requirements, thresholds), PRD §11.1 (A1–A9), tests in
> `python/tests/`, CI jobs in `.github/workflows/` (single list: `CHANGELOG.md` §2.5).

Evidence labels: **checked** — a test or CI job runs on every PR · **partial** — a measurement tool or a
partial check exists · **not measured yet** — no evidence yet.

## 1. Overview

| Group | Question | Main architectural tactic | Status |
|:---|:---|:---|:---|
| Security (SEC) | Is there any path to a pin that does not go through a gate? | A single path; a HAL with no token ledger refuses; callers are untrusted | checked (SEC-01, 09); device: not yet |
| Reliability (REL) | What happens when a part fails? | Fail-closed default; circuit breaker; normative traces frozen | checked (REL-02); REL-01, 03: not yet |
| Resources (RES) | Does it fit the chip? Does it run offline? | Binary `NETR`, non-allocating walker; local fallback | partial |
| Performance (PERF) | Is it fast enough? | Time budget per gate, fail-closed enforcement; per-stage measurement | tools exist; thresholds **not measured yet** |
| Privacy (PRIV) | What data is stored? | No audio stored; hashing at the source by default | checked (PRIV-02, 03, 04); PRIV-01: no dedicated test yet |
| Observability (OBS) | Can we understand what happened? | One trace per session; per-stage latency; System 1/2 ratio | checked |
| Compatibility (COMP) | Can it be opened and swapped? | Schemas opened via RFC; providers swappable; Python 3.11+ | partial (ARM64 not yet) |

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

## 3. Reliability — NFR-REL

| NFR | Tactic | Evidence | Status |
|:---|:---|:---|:---|
| REL-01 OTA at team scale | A/B updates, confirmation after self-test, rollback | job `ota-rollback` on QEMU; scale needs Fleet OS | not yet (premise on QEMU) |
| REL-02 Degraded default is block | `budget.fail` defaults to `closed`; `fail: open` is not inherited, still blocks on a known "no"; the circuit breaker only routes | Matrix A4: `test_fail_closed.py`; `test_safety_regressions.py` | checked |
| REL-03 Nightly run on real boards | Workflow `nightly-hardware.yml`; job `memory-spike` needs a runner with a Box-3 and **says clearly it is skipped** when there is none | No runner yet | not yet |
| REL-04 Old traces still replay after a minor upgrade | `trace.v1` envelope frozen; three normative traces frozen; firmware rejects (does not compare) traces older than itself | `test_golden.py`, `test_trace_vectors.py` | partial — no minor release yet to cross-compare |

## 4. Resources — NFR-RES

| NFR | Tactic | Evidence | Status |
|:---|:---|:---|:---|
| RES-01 24-hour stability on board | No allocation on the audio path (RB-1…RB-4, `docs/spec/hal_mcu_review.md`) | TSK-S6-06 (status: roadmap) | not yet |
| RES-02 Free SRAM, PSRAM (Q-3) | Walker, token ledger, trace buffer use no static RAM; state is allocated by the application | jobs `firmware-size`, `firmware-qemu`; numbers in `memory_spike_report.md` §4.1 | partial — static floor and QEMU heap; PSRAM not measured yet |
| RES-03 Firmware size ≤ A/B slot | Binary tree instead of JSON; no CEL on chip | jobs `firmware-size`, `ota-rollback`, `nightly-hardware` | checked |
| RES-04 Safety functions run offline | Local command grammar is the fallback for every model; no fallback ⇒ `gate_unreachable` | `test_fail_closed.py`, `test_offline_fallback.py`, trace `network_offline.json` | checked on `sim`/`linux`; `esp32s3` not yet (TSK-S5-07) |

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
| OBS-01 One session, one complete trace | The session's `EventLog`; `session_summary` computed on export, exactly once | `test_turn_latency.py`, CI step "three normative traces valid" | checked |
| OBS-02 System 1/2 ratio, cost, every gate outcome | `turn_latency.path`, `system_two_usage` | `test_turn_latency.py` | checked |
| OBS-03 Per-stage latency comparable to `p95_latency_ms` | Nested `TurnMeter.stage` does not double count | `test_turn_latency.py` | checked |

## 8. Compatibility — NFR-COMP

| NFR | Tactic | Evidence | Status |
|:---|:---|:---|:---|
| COMP-01 Core license and standards (Q-45) | PolyForm Noncommercial code; `schemas/`, `docs/spec/`, `fixtures/compliance/` Apache-2.0 | `test_packaging.py` | checked |
| COMP-02 No safety feature locked behind a paid account | The safety core is entirely in the package | Boundary review, no test | by design |
| COMP-03 Every cloud service behind a swappable interface | `models/providers/`, `perception/providers/` | `test_providers.py` | checked |
| COMP-04 Open schemas, governed via RFC | `docs/rfc/`, `digests.lock`, job `frozen-artifacts` | `test_schemas.py`, `test_digests_lock.py` | checked; public URL at I6 |
| COMP-05 Python 3.11+ | `requires-python >= 3.11` | CI matrix 3.11 / 3.12 / 3.13 | checked |
| COMP-06 `linux` on ARM64 and x86-64 | — | Every job runs x86-64; no ARM64 job yet | partial |

## 9. v1.0 acceptance criteria (A1–A9)

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
| A9 | Public schemas with a compliance suite | COMP-01→04 | `$id` asserted; `fixtures/compliance/` today has only `voice/`; public URL at I6 |
