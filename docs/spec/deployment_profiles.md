# Deployment profiles — Software Requirements Specification

**Status:** normative for Q-83 (2026-10-14). Structure follows ISO/IEC/IEEE 29148:2018 §9.6.
This file is the one place for what Profile A (full architecture) and Profile B (one chip) must
do (CONTRIBUTING.md §8.1); the architecture chapters, the roadmap and the business page cite its
requirement IDs and do not restate them. `python/tests/test_deployment_profiles_srs.py` keeps
the tables of §3 and §5 closed: every requirement has a test case, every implemented test case
names a test that exists, every planned one names a roadmap task.

---

## 1. Introduction

### 1.1 Purpose

NeuroEdge is sold as one product that can be deployed two ways. This specification states what
each way must guarantee, what both share, and how each requirement is verified, so that the
remaining work can be coded directly from it.

### 1.2 Scope

In scope: the boundary between the **brain** (NeuroClaw, repository `letrongminh/neuroclaw`) and
the **box** (NeuroEdge, this repository); the contract between them; installation per profile;
the single-chip firmware image; the local page that answers the device's questions.
Out of scope: gate semantics (`core_contracts.md`), the NETR layout (RFC-0003, RFC-0009), the
`trace.v1` schema, NeuroClaw's own channels and providers (`docs/reference/capabilities.md` in
that repository).

### 1.3 Definitions

| Term | Meaning |
|:---|:---|
| **Box** | The trusted runtime: gate, verdict tokens, confirmation book, HAL, traces, local command grammar, System 1, guard, proxies, plugins, MCP server. Deterministic; works offline. |
| **Brain** | The untrusted LLM agent: conversation, memory, retrieval, chat channels, reminders, heartbeat, LLM budget. It may be wrong or compromised. NeuroClaw (Go) in Profile A, NeuroClaw-ESP (C) in Profile B. |
| **Contract** | The tool list (names, input schemas) and the result shape `schemas/tool-result.v1.json` that the box offers and the brain consumes. |
| **Transport** | How the contract travels: MCP over HTTPS with mutual TLS in Profile A; a function call or FreeRTOS queue through `nc_gate` in Profile B. |
| **Profile A — Full** | Brain and box in separate trust domains: the same machine under separate OS users, two machines, or the brain on NeuroEdge Cloud. |
| **Profile B — One chip** | Brain and box in one ESP32-S3 firmware image; labelled `risk=single_chip` (Q-79). |
| **Profile B+** | One board with real isolation between brain and box (privilege separation, or two chips). Under evaluation only (DP-BP-01). |
| **Bridge** | `ne_brain_bridge`, the box-side component of Profile B that offers `ne_gate` to NeuroClaw-ESP as an `nc_gate`. |
| **Human source** | A source allowed to answer an `ask`: `HUMAN_SOURCES` in `python/neuroedge/actions/confirmation.py` (`local_grammar`, `ui`); in Profile B, the owner's Telegram callback or the board's button. |

### 1.4 References

PRD §15 Q-27, Q-72, Q-73, Q-76, Q-79, Q-80, Q-81, Q-83; NFR-RES-02, NFR-RES-03 (Q-3 budgets) ·
`schemas/tool-result.v1.json` · `docs/spec/tool_calling.md` §7 (trace events) ·
`docs/spec/threat_model.md` §2k, §2l · `docs/architecture/vi/15-target-architecture.md` §6.10 ·
`targets/esp32s3/components/ne_gate/include/ne_walker.h`, `ne_token.h` ·
NeuroClaw `esp32/components/neuroclaw/include/neuroclaw.h` (`nc_gate`).

---

## 2. Overall description

### 2.1 Product perspective

```
Profile A — Full                                   Profile B — One chip (risk=single_chip)

 📱 chat ─► NeuroClaw (brain, own OS user,          📱 Telegram ─► ┌── ESP32-S3, one image ──────────┐
            other machine, or Cloud)                               │ NeuroClaw-ESP (brain)           │
                 │ MCP · HTTPS · mTLS · JWT                        │   │ nc_gate: call / answer      │
                 ▼                                                 │   ▼                             │
            NeuroEdge box: gate ─► token ─► HAL ─► pins            │ ne_brain_bridge ─► ne_gate      │
                 ▲                                                 │   ─► token ─► HAL ─► pins       │
   person at home: local page (key) or box's own approval bot      └─────────────────────────────────┘
                                                                     owner: Telegram callback or button
```

Both profiles offer the **same contract**; only the transport differs (DP-COM-01). MCP and TLS
are not run between brain and gate on one chip: they share an address space, so a channel
between them adds no isolation and costs about 40 KB of RAM per TLS session (§2.4).

### 2.2 Code boundary

| Lives in the box (this repository) | Lives in the brain (NeuroClaw) |
|:---|:---|
| `engine/`, `actions/` (tokens, `c.do`, confirmation), `hal/`, `sim/`, `trace.py`, `testing/` | LLM loop, tool selection, provider fallback |
| `models/grammar.py`, System 1 (`SystemOne` is a fact source on the decision path) | Memory, retrieval (seahorse), conversation summaries |
| `guard.py`, `proxy_mcp.py`, `proxy_http.py`, `plugins/` | Chat channels, reminders (`cron`), heartbeat, `llm_budget` |
| `mcp_server.py`, `mcp_http.py`, Studio inspection, `targets/esp32s3/` incl. the bridge | Voice in and out (when reopened, Q-77) |

`SystemTwo` with a real LLM, `mcp_host.py` and `models/knowledge.py` retrieval are deprecated in
the box (DP-A-08); `SystemTwo("sim")` stays as an offline null provider for simulation and replay.

### 2.3 User classes

| Class | Profile | Needs |
|:---|:---|:---|
| Home owner, non-technical | A (self-hosted or Cloud) or B | One install command, chat, approvals they trust |
| Maker | B | Cheapest hardware, one flash command |
| Integrator / product team | A | Any AI client over MCP, audit traces, signed updates |
| Developer of NeuroEdge | both | Requirements that are testable on `sim` and QEMU |

### 2.4 Operating environment and constraints

- Profile A box: Linux (Raspberry Pi 5, x86_64), macOS for development; Python 3.11+.
- Profile A brain: any platform NeuroClaw releases for; or NeuroEdge Cloud (I2f, conditional).
- Profile B: ESP32-S3 with 16 MB flash and 8 MB PSRAM (DevKitC N16R8, Box-3); QEMU for CI.
- **C1** Image ≤ 3.5 MB; free internal SRAM ≥ 120 KB and PSRAM ≥ 2 MB at run time (NFR-RES-02,
  NFR-RES-03, Q-3).
- **C2** `ne_*` components: C99, no heap allocation, no recursion, stack ≤ 512 B per call.
- **C3** No MCP server and no TLS server on the chip.
- **C4** An approval never transits the brain in Profile A; in Profile B the owner's identity is
  checked by the box side (DP-B-07).
- **C5** Changing `schemas/`, the NETR layout or gate semantics needs an RFC (CONTRIBUTING.md §3).

### 2.5 Assumptions and dependencies

- Profile B hardware work depends on the HAL port (TSK-S4-01) and the DevKitC board profile
  (TSK-I3a-08). Until then Profile B is verified on QEMU with simulated pins.
- NeuroClaw-ESP keeps the `nc_gate` interface (tools, call, answer); DP-B-07 adds the
  answering user's ID to `answer`, an interface change made in the NeuroClaw repository.

---

## 3. Specific requirements

Verification methods: **T** test, **I** inspection, **A** analysis, **D** demonstration.

### 3.1 Common to both profiles (DP-COM)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| DP-COM-01 | Every tool call result, in either transport, shall be a JSON object valid against `schemas/tool-result.v1.json`. | One brain code path reads results in both profiles. | Q-83 | T |
| DP-COM-02 | For the same agent, the tool names and input schemas offered over MCP and through the bridge shall be identical. | A skill written for one profile works on the other. | Q-83 | T |
| DP-COM-03 | For the same gate digest, facts, arguments and confirmation state, the verdict, reason and failed criterion shall be identical on `sim`, `linux` and `esp32s3`, in either profile. | The safety promise does not depend on where the box runs. | Q-72, `10-target-equivalence` | T |
| DP-COM-04 | An `ask` shall be answerable only from a human source; the brain, an MCP client and System 2 shall never be able to confirm. | "Only a person answers" (RFC-0006). | Q-26, Q-79 | T |
| DP-COM-05 | Every gate decision shall produce a `trace.v1` record that `neuroedge verify` can replay to the same verdict. | Evidence, not promises. | Q-72 | T |
| DP-COM-06 | Every risk label in force (`single_chip`, `readable_flash`, and the brain's own labels of Q-80) shall be printed at start-up and shown by `status`. | Transparency instead of prohibition. | Q-73, Q-79, Q-80 | T |
| DP-COM-07 | Each profile shall install with one command and one configuration file. | Two components must not mean two installs. | Q-83 | D |
| DP-COM-08 | Each tool listed by the box shall carry `_meta["dev.neuroedge/contract"] = "tool-result.v1"`; a brain that reads an unknown major version, or a `status` outside ALLOW / BLOCK / REJECTED, shall treat the call as REJECTED and shall not retry it as allowed. | Fail closed across independent release trains. | Q-83 | T |

### 3.2 Profile A — Full (DP-A)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| DP-A-01 | Over the network the box shall serve MCP only over HTTPS with TLS 1.3, a client certificate from the configured CA, and a JWT bound to that certificate (`cnf.x5t#S256`); refusals are traced as `mcp_auth_refused`. | The brain is untrusted and may be remote. | Q-76, TSK-P2-04 | T |
| DP-A-02 | Every POST to the local page (`run --ui`, `mcp serve --ui`, Studio) shall carry an `Origin` of the server and the header `X-NeuroEdge-UI-Key` equal to a key of at least 32 random bytes made for that run; the key shall appear only after `#` in the URL printed on the terminal, never in a page, `/state` or `/events`; a refused POST shall answer 403 and be traced as `ui_auth_refused` with `reason` and `path` and never the key. | Any process on the box's machine, including a brain with a shell, could otherwise answer the device's question as the person at home. | Q-83, threat model §2k | T |
| DP-A-03 | On a shared machine the brain shall run under its own OS user with no membership of device groups (`gpio`, `i2c`, `spi`, `dialout`, `video`) and no read access to the box's key directory; `neuroedge doctor` shall report a violation. | Isolation is the boundary in Profile A. | TSK-I2d-24 | T |
| DP-A-04 | Brain access tokens shall live at most 7 days; `neuroedge pair renew` shall issue a new one without restarting the box. | A leaked token expires; renewal is routine. | TSK-I2d-25 | T |
| DP-A-05 | On target `linux` a person shall be able to answer an `ask`: through the local page, or through the box's own approval bot (DP-A-06). | Without it, every `ask` on a real home expires. | TSK-I2d-25 | T |
| DP-A-06 | Remote approvals shall come only from the box's own bot token (never the brain's), as approval records signed by the box with nonce, expiry and gate digest; a `chat:<id>` source shall not be a human source unless its record verifies. | A "yes" relayed through the brain's chat could be forged by a compromised brain. | TSK-I2d-11, TSK-I2d-12 | T |
| DP-A-07 | NeuroClaw's CI shall run its MCP client against a pinned `neuroedge mcp serve --target sim` and check every result against `tool-result.v1`, including `fallback` and `escalated_to`. | The two repositories release independently. | TSK-I2d-26 | T |
| DP-A-08 | `SystemTwo` with a real LLM, `mcp_host.py` and the retrieval branch of `models/knowledge.py` shall be off unless `NEUROEDGE_LEGACY_SYSTEM_TWO=1`; with it off, `run` keeps the local grammar, System 1 and the offline answer unchanged. | One brain, not two. | Q-83, TSK-I2d-27 | T |
| DP-A-09 | `neuroedge install --profile full` shall create keys and certificates, the brain's OS user, service units for box and brain, and download NeuroClaw at a pinned version whose SHA-256 is checked. | One command per profile (DP-COM-07). | TSK-I2d-25 | D |

### 3.3 Profile B — One chip (DP-B)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| DP-B-01 | `neuroedge build --target esp32s3 --brain neuroclaw` shall write one ESP-IDF project containing `ne_*`, the bridge and NeuroClaw-ESP at a pinned version; a SHA-256 mismatch of the fetched component shall fail the build. | One image, reproducible. | TSK-I2f-14 | T |
| DP-B-02 | Brain and bridge shall talk through `nc_gate` (function calls, or a FreeRTOS queue); the image shall contain no MCP server and no TLS server. | C3; no isolation is gained on one chip. | Q-79, Q-83 | I |
| DP-B-03 | The bridge shall offer one tool per `@action` with the name and input schema the box offers over MCP (DP-COM-02), generated at build time. | Same contract. | TSK-I2f-12 | T |
| DP-B-04 | The bridge shall parse a call's JSON arguments into `ne_arg_value[]` by `ne_argument_name`; an unknown argument, a missing one or a wrong type shall give REJECTED with `problems`, and no gate is evaluated. | Typed queue into `ne_gate` (Q-79). | TSK-I2f-12 | T |
| DP-B-05 | Facts shall come only from on-chip fact sources declared by the board profile (HAL inputs, sensors, clock, owner settings in `ne_config`); a value the LLM puts in a call shall never become a fact. | The brain may be wrong; facts decide. | Q-79, TSK-I2f-12 | T |
| DP-B-06 | The bridge shall map `ne_result` to a `tool-result.v1` object: verdict to `status`, reason enum to `reason`, `failed_index` to `failed_criterion`, `ne_on_block_message` to `message`, an answerable block to `on_block: "ask"` with a confirmation. | DP-COM-01. | TSK-I2f-12 | T |
| DP-B-07 | Pending confirmations shall be at most `NE_TOKEN_SLOTS`, each single-use with a TTL; `answer` shall be accepted only from the board button or a Telegram callback whose user ID equals `telegram.owner` in `ne_config`, checked by the bridge; an accepted answer re-evaluates with `ne_decide(..., confirmed=1, ...)`. | Q-79 (2): button or the right owner ID. | TSK-I2f-12 | T |
| DP-B-08 | A pin shall move only between `ne_token_issue` and `ne_token_close` for an ALLOW, through `ne_token_authorize(token, pin)`; the HAL entry points shall require the token. | No LLM-to-GPIO path. | TSK-I2f-12, TSK-S4-01 | T |
| DP-B-09 | The partition table shall hold `factory`, `ota_0`, `ota_1` each ≥ the image, a LittleFS `ws` ≥ 1 MB for the brain's workspace (taken from `storage`), `ne_config` and `nvs_keys` (encrypted under `sdkconfig.secure`). | Brain workspace and signed OTA together. | TSK-I2f-14 | T |
| DP-B-10 | `ne_config` shall hold Wi-Fi, Telegram token and owner, primary and fallback LLM URL / key / model, search key and time zone; the brain receives them at start-up; no secret is ever written to the UART. | One store for secrets, as Q-79 (3). | TSK-I2f-14 | T |
| DP-B-11 | One component shall own Wi-Fi and one `esp_console`; the brain registers its commands on it and does not start Wi-Fi itself. | Two owners race at boot. | TSK-I2f-14 | T |
| DP-B-12 | Each decision at run time shall emit `NE1` trace lines on the UART, interleaved safely with other output; `neuroedge record --port` shall keep reading until stopped and write replayable `trace.v1`. | DP-COM-05 on the chip. | TSK-I2f-16, TSK-S4-04 | T |
| DP-B-13 | The combined image shall meet C1, and the stack high-water mark of every task shall be reported in CI; `ne_*` keeps the 512 B rule. | Q-3 budgets with the brain inside. | TSK-I2f-15 | T |
| DP-B-14 | The image shall print `risk=single_chip` at boot and in `status`, and `risk=readable_flash` while flash encryption is off. | Q-79 (3), DP-COM-06. | TSK-I2f-14 | T |
| DP-B-15 | A signed OTA shall replace the whole image (brain and box); the boot self-test that confirms an update shall include a bridge self-check. | One update path; rollback covers the brain. | TSK-I2f-14 | T |
| DP-B-16 | Without Wi-Fi, a board button bound to an action shall still go through the gate, and an action to the safe state shall always be allowed. | The box works offline. | TSK-I2f-15 | T |

### 3.4 Profile B+ (DP-BP)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| DP-BP-01 | A decision note shall compare ESP Privilege Separation on ESP32-S3 (support status, RAM cost, placing gate, ledger and HAL in the protected app) with a two-chip board (S3 brain, C3 gate, UART with a MAC per frame), and recommend one or neither. | Real isolation on one board for buyers who need it. | TSK-I2f-17 | A |

### 3.5 Non-functional requirements (DP-NF)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| DP-NF-01 | The bridge shall add at most 5 ms (p95) to a decision on ESP32-S3 at 240 MHz, measured from `call` entry to result. | The gate's own p95 budget stays meaningful. | Q-83 | T |
| DP-NF-02 | NeuroClaw (both builds) shall be pinned by version and SHA-256 wherever the box fetches it; upgrading is a one-line change plus a passing DP-A-07 run. | Easy, safe updates across repositories. | Q-83 | I |

---

## 4. Interfaces

### 4.1 One contract, two transports

| Step | Profile A (MCP) | Profile B (`nc_gate`) |
|:---|:---|:---|
| List tools | `tools/list` → name, `inputSchema`, `outputSchema`, `_meta` | `tools(ctx, &out)` → `nc_tool[]` (name, description, schema JSON) |
| Call | `tools/call` → `structuredContent` (tool-result.v1) | `call(ctx, name, arguments_json, &out)` → `nc_tool_result` rendered from the same JSON |
| Answer an `ask` | never over MCP: local page (DP-A-02) or box approval bot (DP-A-06) | `answer(ctx, confirmation_id, approve, from_id, &out)` from button or owner callback (DP-B-07) |
| Contract version | `_meta["dev.neuroedge/contract"]` | `NE_BRIDGE_CONTRACT` = `"tool-result.v1"` |

### 4.2 Result examples (tool-result.v1)

```json
{"tool": "living_light_on", "status": "ALLOW"}
{"tool": "front_door_unlock", "status": "BLOCK", "gate": "front_door_unlock@1.0.0",
 "reason": "condition_not_met", "on_block": "ask", "message": "Open the door for the guest?",
 "confirmation": {"id": "confirm_1", "message": "Open the door for the guest?", "expires_in_ms": 60000,
                  "who": "a person on the device (voice or the device's page); not this caller"}}
{"tool": "front_door_unlock", "status": "REJECTED", "problems": ["duration_s: 45 is above 30"]}
```

### 4.3 Bridge (`targets/esp32s3/components/ne_brain_bridge/include/ne_brain_bridge.h`)

```c
#define NE_BRIDGE_CONTRACT "tool-result.v1"

typedef struct ne_fact_source {
    void *ctx;
    /* Fill facts[i] for every criterion of `gate` from on-chip sources only (DP-B-05). */
    void (*read)(void *ctx, const ne_tree *gate, ne_fact *facts, uint32_t count, uint32_t now_ms);
} ne_fact_source;

typedef struct ne_bridge ne_bridge;   /* static storage: no heap (C2) */

void     ne_bridge_init(ne_bridge *b, const ne_agent *agent, ne_ledger *ledger,
                        const ne_fact_source *facts, const ne_hal *hal);
nc_gate  ne_bridge_gate(ne_bridge *b);                       /* what neuroclaw_start() takes */
void     ne_bridge_answer_button(ne_bridge *b, uint8_t button); /* board button = owner */
bool     ne_bridge_selftest(ne_bridge *b);                   /* part of the OTA self-test (DP-B-15) */
```

### 4.4 Local page key (DP-A-02)

The terminal prints `http://127.0.0.1:<port>/#k=<key>`. The page reads `k` from
`location.hash`, keeps it in `sessionStorage`, removes it from the address bar, and sends
`X-NeuroEdge-UI-Key: <key>` with every POST. Refusal reasons: `foreign_host`, `no_origin`,
`foreign_origin`, `no_key`, `wrong_key`. At most 10,000 refusals are traced per session; the
last one carries `last_recorded: true`.

---

## 5. Verification

Status `implemented — <file>::<test>` names a test in this repository; `planned — <TSK>` names
the roadmap task that adds the test with the code. No test is skipped in the meantime
(CONTRIBUTING.md §5).

| TC | Verifies | Level | Procedure → expected | Status |
|:---|:---|:---|:---|:---|
| TC-COM-01-1 | DP-COM-01 | unit | Every tool-call corpus result → valid against tool-result.v1 | implemented — python/tests/test_contracts.py::test_every_tool_call_corpus_result_validates_against_the_tool_result_schema |
| TC-COM-01-2 | DP-COM-01, DP-COM-02 | host C | Same agent through MCP and through the bridge host harness → byte-identical canonical JSON per call | planned — TSK-I2f-12 |
| TC-COM-02-1 | DP-COM-02 | unit | Published `outputSchema` of every tool → the frozen schema pinned to its name | implemented — python/tests/test_contracts.py::test_the_published_output_schema_of_every_tool_is_the_frozen_result_schema_pinned_to_its_name |
| TC-COM-03-1 | DP-COM-03 | host C | C walker vs host engine on every gate → same verdict, reason, failed criterion | implemented — python/tests/test_c_walker.py::test_the_c_walker_matches_the_host_engine_on_every_gate |
| TC-COM-03-2 | DP-COM-03 | integration | Same facts with and without the network transport → same verdict | implemented — python/tests/test_mcp_http.py::test_the_same_facts_give_the_same_verdict_with_or_without_the_network |
| TC-COM-04-1 | DP-COM-04 | unit | `confirm` from each non-human source → refused | implemented — python/tests/test_tool_confirm.py::test_only_a_person_on_the_device_may_answer |
| TC-COM-04-2 | DP-COM-04 | unit | System 2 tries to answer the question its own call raised → refused | implemented — python/tests/test_tool_confirm.py::test_system_two_cannot_answer_the_question_its_own_call_raised |
| TC-COM-04-3 | DP-COM-04 | integration | MCP client lists tools → no confirm tool; cannot answer | implemented — python/tests/test_tool_confirm.py::test_an_mcp_client_has_no_way_to_confirm |
| TC-COM-05-1 | DP-COM-05 | integration | `verify` replays every canonical trace → same verdicts, names what it did not check | implemented — python/tests/test_cli.py::test_verify_replays_every_canonical_trace_and_states_what_it_did_not_check |
| TC-COM-05-2 | DP-COM-05 | QEMU | Device replays every canonical trace → matches golden | implemented — python/tests/test_trace_vectors.py::test_the_device_replays_every_canonical_trace_to_its_golden |
| TC-COM-06-1 | DP-COM-06 | integration | Start box and brain with a risky option on → the label is printed once at start and listed by `status` | planned — TSK-I2d-25 |
| TC-COM-07-1 | DP-COM-07 | demo | Blank Debian 12 VM and a blank DevKitC → one command each reaches a working chat-to-light demo | planned — TSK-I2d-25 |
| TC-COM-08-1 | DP-COM-08 | unit (Go) | NeuroClaw reads a result with `status: "MAYBE"` and one with contract `tool-result.v2` → REJECTED, no retry as allowed | planned — TSK-I2d-26 |
| TC-A-01-1 | DP-A-01 | integration | No token, bad token, wrong scope, other device's token → 401/403, nothing dispatched, traced | implemented — python/tests/test_mcp_http.py::test_a_request_without_a_valid_token_is_refused_and_nothing_is_dispatched |
| TC-A-01-2 | DP-A-01 | integration | Client without a trusted certificate → TLS handshake fails before HTTP | implemented — python/tests/test_mcp_http.py::test_a_client_without_a_trusted_certificate_never_reaches_http |
| TC-A-01-3 | DP-A-01 | integration | Client limited to TLS 1.2 → refused | implemented — python/tests/test_mcp_http.py::test_a_client_that_will_not_speak_tls_13_is_refused |
| TC-A-02-1 | DP-A-02 | integration | POST /confirm with the right Origin and no key → 403, no `tool_confirmed`, pin unchanged, `ui_auth_refused` `no_key` | implemented — python/tests/test_tool_confirm.py::test_a_local_process_without_the_key_cannot_answer_the_device |
| TC-A-02-2 | DP-A-02 | integration | Wrong key → 403, traced `wrong_key`, key absent from the trace | implemented — python/tests/test_tool_confirm.py::test_a_wrong_key_is_refused_and_traced_without_the_key |
| TC-A-02-3 | DP-A-02 | integration | Right key, no Origin (curl) → 403, traced `no_origin` | implemented — python/tests/test_tool_confirm.py::test_a_request_with_no_origin_is_refused_even_with_the_key |
| TC-A-02-4 | DP-A-02 | integration | Page headers (Origin + key) → answer accepted with source `ui`, light switches | implemented — python/tests/test_tool_confirm.py::test_the_page_offers_the_buttons_and_the_answer_goes_through_the_gate |
| TC-A-02-5 | DP-A-02 | integration | GET `/`, `/state`, `/events` → key absent; `open_url` = `url#k=key`; key ≥ 43 characters | implemented — python/tests/test_sim_ui.py::test_the_key_is_never_in_the_page_or_the_state |
| TC-A-02-6 | DP-A-02 | integration | Two servers → two different keys | implemented — python/tests/test_sim_ui.py::test_each_run_has_its_own_key |
| TC-A-02-7 | DP-A-02 | integration | Studio `/api/lint` POST without the key → 403, traced `no_key` | implemented — python/tests/test_studio_server.py::test_the_studio_refuses_an_action_without_the_runs_key |
| TC-A-02-8 | DP-A-02 | integration | `mcp serve --ui` prints the URL with `#k=` on one line of stderr | implemented — python/tests/test_mcp_serve_ui.py::test_a_taken_port_moves_the_page_and_keeps_serving_mcp |
| TC-A-03-1 | DP-A-03 | linux | Brain user in group `gpio` or able to read the key directory → `neuroedge doctor` exits 1 naming it | planned — TSK-I2d-24 |
| TC-A-03-2 | DP-A-03 | linux | Process as brain user opens `/dev/gpiochip0` and the box key → EACCES; POST /confirm → 403 | planned — TSK-I2d-24 |
| TC-A-04-1 | DP-A-04 | integration | Token with 8-day lifetime → refused at issue; `pair renew` → new token accepted, old one refused after expiry, box not restarted | planned — TSK-I2d-25 |
| TC-A-05-1 | DP-A-05 | linux | `mcp serve --http --ui --target linux` with an `ask` → page answers it; without page and bot → expires and is traced | planned — TSK-I2d-25 |
| TC-A-06-1 | DP-A-06 | integration | Approval record with bad signature, reused nonce, expired, other gate digest → refused; valid → accepted as `chat:<id>` | planned — TSK-I2d-11 |
| TC-A-06-2 | DP-A-06 | integration | Brain's bot token configured as approval bot → box refuses to start | planned — TSK-I2d-12 |
| TC-A-07-1 | DP-A-07 | CI (Go) | NeuroClaw integration job starts the pinned box on `sim`, calls light / door / night cases → every result validates, `fallback` and `escalated_to` handled | planned — TSK-I2d-26 |
| TC-A-08-1 | DP-A-08 | unit | Without the flag: `run` answers with grammar, System 1 and the offline answer; no LiteLLM import; with the flag: the old path works | planned — TSK-I2d-27 |
| TC-A-09-1 | DP-A-09 | demo | Blank VM → `neuroedge install --profile full` → services up, brain user isolated (TC-A-03-2 passes), chat turns on the light | planned — TSK-I2d-25 |
| TC-B-01-1 | DP-B-01 | unit | `build --brain neuroclaw` writes the component pin; tampered SHA-256 → build error naming the file | planned — TSK-I2f-14 |
| TC-B-02-1 | DP-B-02 | inspection | Image symbols contain no MCP server, no `mbedtls_ssl_conf_*` server role | planned — TSK-I2f-15 |
| TC-B-03-1 | DP-B-03 | host C | Bridge tool list for the demo agent equals the MCP tool list (names, schemas) | planned — TSK-I2f-12 |
| TC-B-04-1 | DP-B-04 | host C | Arguments table: unknown key, missing key, string for number, out of range → REJECTED with `problems`; walker never called | planned — TSK-I2f-12 |
| TC-B-05-1 | DP-B-05 | host C | Call carries `"temperature": 99`; fact source reads 25 → verdict follows 25 | planned — TSK-I2f-12 |
| TC-B-06-1 | DP-B-06 | host C | Every `ne_result` reason and `on_block` action → mapped JSON valid against tool-result.v1 | planned — TSK-I2f-12 |
| TC-B-07-1 | DP-B-07 | host C | Expired confirmation, second answer, wrong `from_id`, fifth pending → refused; owner callback and button → ALLOW once | planned — TSK-I2f-12 |
| TC-B-08-1 | DP-B-08 | host C | HAL drive without token, with closed token, with token for another pin → refused, pin unchanged | planned — TSK-S4-01 |
| TC-B-09-1 | DP-B-09 | unit | Generated partition table: offsets aligned, OTA slots ≥ image, `ws` ≥ 1 MB, `nvs_keys` encrypted | planned — TSK-I2f-14 |
| TC-B-10-1 | DP-B-10 | QEMU | Set all keys at the hidden prompt, reboot → brain configured; UART capture contains no secret | planned — TSK-I2f-14 |
| TC-B-11-1 | DP-B-11 | QEMU | Boot combined image → one Wi-Fi start, one console with both command sets | planned — TSK-I2f-14 |
| TC-B-12-1 | DP-B-12 | QEMU | Three tool calls → `record --port` writes a trace that `verify` replays to the same verdicts | planned — TSK-I2f-16 |
| TC-B-13-1 | DP-B-13 | QEMU | Size job: image ≤ 3.5 MB; free SRAM ≥ 120 KB after brain start; stack report per task; `ne_*` ≤ 512 B | planned — TSK-I2f-15 |
| TC-B-14-1 | DP-B-14 | QEMU | Boot without flash encryption → both labels at boot and in `status` | planned — TSK-I2f-14 |
| TC-B-15-1 | DP-B-15 | QEMU | OTA to an image whose bridge self-check fails → rollback to the previous image | planned — TSK-I2f-14 |
| TC-B-16-1 | DP-B-16 | QEMU | Network down; button bound to `light_off` → ALLOW; to `front_door_unlock` at night → BLOCK | planned — TSK-I2f-15 |
| TC-BP-01-1 | DP-BP-01 | analysis | Decision note merged under `docs/reports/` with measurements and a recommendation | planned — TSK-I2f-17 |
| TC-NF-01-1 | DP-NF-01 | board | 1,000 calls on DevKitC → bridge overhead p95 ≤ 5 ms | planned — TSK-I2f-15 |
| TC-NF-02-1 | DP-NF-02 | inspection | Every place that fetches NeuroClaw names a version and a SHA-256 | planned — TSK-I2d-26 |

---

## 6. Traceability

| Requirement | Decision | Task | Test cases |
|:---|:---|:---|:---|
| DP-COM-01 … 08 | Q-83, Q-72, Q-73, Q-79 | TSK-I2d-25, TSK-I2d-26, TSK-I2f-12 | TC-COM-* |
| DP-A-01 … 09 | Q-76, Q-83 | TSK-I2d-11, TSK-I2d-12, TSK-I2d-24, TSK-I2d-25, TSK-I2d-26, TSK-I2d-27 | TC-A-* |
| DP-B-01 … 16 | Q-79, Q-83 | TSK-I2f-12, TSK-I2f-14, TSK-I2f-15, TSK-I2f-16, TSK-S4-01, TSK-S4-04 | TC-B-* |
| DP-BP-01 | Q-83 | TSK-I2f-17 | TC-BP-01-1 |
| DP-NF-01, 02 | Q-83 | TSK-I2f-15, TSK-I2d-26 | TC-NF-* |
