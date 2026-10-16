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
the NeuroClaw repository `letrongminh/neuroclaw`, not in this one).

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
- **C4** An approval never transits the brain in Profile A. In Profile B the owner's Telegram
  callback is received by brain code in the same image, so only the board button is a human
  channel independent of the brain; the callback path is accepted under `risk=single_chip`
  (Q-79), and the bridge's owner check guards against mistakes, not against a compromised brain.
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
| DP-COM-04 | An `ask` shall be answerable only from a human source; the LLM, an MCP client and System 2 shall have no tool or path to confirm. In Profile A this holds even against a compromised brain; in Profile B it holds against a misbehaving LLM but not against a compromised brain process (C4), which is what `risk=single_chip` labels. | "Only a person answers" (RFC-0006). | Q-26, Q-79 | T |
| DP-COM-05 | Every gate decision shall produce a `trace.v1` record that `neuroedge verify` can replay to the same verdict. | Evidence, not promises. | Q-72 | T |
| DP-COM-06 | Every risk label in force (`single_chip`, `readable_flash`, and the brain's own labels of Q-80) shall be printed at start-up and shown by `status`. | Transparency instead of prohibition. | Q-73, Q-79, Q-80 | T |
| DP-COM-07 | Each profile shall install with one command and one configuration file. | Two components must not mean two installs. | Q-83 | D |
| DP-COM-08 | Each tool listed by the box shall carry `_meta["dev.neuroedge/contract"] = "tool-result.v1"`; a brain that reads an unknown contract major version, or a `status` outside ALLOW / BLOCK / REJECTED, shall treat the call as REJECTED and shall not retry it as allowed. Unknown *keys* are still ignored, as the schema says. | Fail closed across independent release trains. | Q-83 | T |
| DP-COM-09 | At most 4 `ask`s shall be pending at once per box; another call that would ask while 4 are pending shall be a BLOCK with reason `budget_exceeded` and no question sent. | A brain cannot flood the person with questions, nor fill the chip's tables. | Q-83 | T |

### 3.2 Profile A — Full (DP-A)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| DP-A-01 | Over the network the box shall serve MCP only over HTTPS with TLS 1.3, a client certificate from the configured CA, and a JWT bound to that certificate (`cnf.x5t#S256`); refusals are traced as `mcp_auth_refused`. | The brain is untrusted and may be remote. | Q-76, TSK-P2-04 | T |
| DP-A-02 | Every POST to the local page (`run --ui`, `mcp serve --ui`, Studio) shall carry an `Origin` of the server and the header `X-NeuroEdge-UI-Key` equal to a key of at least 32 random bytes made for that run. The key shall never be printed nor appear in a page, `/state` or `/events`: the URL printed on the terminal carries after `#` a pairing code of at least 16 random bytes that `POST /pair` (Origin required) trades for the key once, within 10 minutes. A refused POST or pairing shall answer 403 and be traced as `ui_auth_refused` with `reason` and a `path` cut to 64 characters, never the key or code. | Any process on the box's machine, including a brain with a shell, could otherwise answer the device's question as the person at home; the printed URL lands in the browser's command line and in logs, so it may only hold a spent code. A process that uses the code before the person opens the page still wins; DP-A-03 removes that. | Q-83, threat model §2k | T |
| DP-A-03 | On a shared machine the brain shall run under its own OS user with no membership of device groups (`gpio`, `i2c`, `spi`, `dialout`, `video`) and no read access to the box's key directory, and `/proc` mounted with `hidepid=2` (or equivalent) so it cannot read other users' command lines; `neuroedge doctor` shall report a violation. | Isolation is the boundary in Profile A. | TSK-I2d-24 | T |
| DP-A-04 | Brain access tokens shall live at most 7 days; `neuroedge pair renew` shall issue a new one without restarting the box. | A leaked token expires; renewal is routine. | TSK-I2d-25 | T |
| DP-A-05 | On target `linux` a person shall be able to answer an `ask`: through the local page, or through the box's own approval bot (DP-A-06). | Without it, every `ask` on a real home expires. | TSK-I2d-25 | T |
| DP-A-06 | Remote approvals shall come only from the box's own bot token (never the brain's), as approval records signed by the box with nonce, expiry and gate digest; a `chat:<id>` source shall not be a human source unless its record verifies. | A "yes" relayed through the brain's chat could be forged by a compromised brain. | TSK-I2d-11, TSK-I2d-12 | T |
| DP-A-07 | NeuroClaw's CI shall run its MCP client against a pinned `neuroedge mcp serve --target sim` and check every result against `tool-result.v1`, including `fallback` and `escalated_to`. | The two repositories release independently. | TSK-I2d-26 | T |
| DP-A-08 | `SystemTwo` with a real LLM, `mcp_host.py` and the retrieval branch of `models/knowledge.py` shall be off unless `NEUROEDGE_LEGACY_SYSTEM_TWO=1`; with it off, `run` keeps the local grammar, System 1 and the offline answer unchanged. | One brain, not two. | Q-83, TSK-I2d-27 | T |
| DP-A-09 | `neuroedge install --profile full` shall create keys and certificates, the brain's OS user, service units for box and brain, and download NeuroClaw at a pinned version whose SHA-256 is checked. | One command per profile (DP-COM-07). | TSK-I2d-25 | D |
| DP-A-10 | Under a service manager the page URL shall be written to a file readable only by the owner (mode 0600) and `neuroedge ui-link` shall print a fresh pairing code; the URL shall not go to the journal. | A headless Pi has no terminal for the person to read. | TSK-I2d-25 | T |
| DP-A-11 | Brain client certificates shall be rotatable without restarting the box, and a revoked certificate thumbprint shall be refused at the TLS handshake. | A stolen brain key is revoked, not waited out. | TSK-I2d-25 | T |

### 3.3 Profile B — One chip (DP-B)

| ID | Requirement | Rationale | Source | Verification |
|:---|:---|:---|:---|:---|
| DP-B-01 | `neuroedge build --target esp32s3 --brain neuroclaw` shall write one ESP-IDF project containing `ne_*`, the bridge and NeuroClaw-ESP at a pinned version; a SHA-256 mismatch of the fetched component shall fail the build. | One image, reproducible. | TSK-I2f-14 | T |
| DP-B-02 | Brain and bridge shall talk through `nc_gate` (function calls, or a FreeRTOS queue); the image shall contain no MCP server and no TLS server. | C3; no isolation is gained on one chip. | Q-79, Q-83 | I |
| DP-B-03 | The bridge shall offer one tool per `@action` with the name and input schema the box offers over MCP (DP-COM-02), generated at build time. | Same contract. | TSK-I2f-12 | T |
| DP-B-04 | The bridge shall parse a call's JSON arguments into `ne_arg_value[]` by `ne_argument_name`; an unknown argument, a missing one or a wrong type shall give REJECTED with `problems`, and no gate is evaluated. | Typed queue into `ne_gate` (Q-79). | TSK-I2f-12 | T |
| DP-B-05 | Facts shall come only from on-chip fact sources declared by the board profile (HAL inputs, sensors, clock, owner settings in `ne_config`); a value the LLM puts in a call shall never become a fact; a value the box itself commanded is not a reading (`present = 0`), and `age_ms` is measured from the HAL read mark (`ne_walker.h`). | The brain may be wrong; facts decide. | Q-79, TSK-I2f-12 | T |
| DP-B-06 | The bridge shall map `ne_result` to a `tool-result.v1` object: verdict to `status`; reason enum to `reason` (an argument failure is `argument_out_of_range`); `failed_index` to a name through `ne_criterion_name` or `ne_argument_name` as `failed_kind` says; `ne_on_block_message` to `message`; an answerable block to `on_block: "ask"` with `confirmation` {`id`, `message`, `expires_in_ms` from DP-B-07's TTL, `who` naming the board button or the owner}. | DP-COM-01. | TSK-I2f-12 | T |
| DP-B-07 | Pending confirmations shall live in the bridge's own table of `NE_BRIDGE_PENDING` = 4 entries (not the token ledger), each holding the tool, its parsed arguments and the gate digest, single-use, with TTL `max(3 × p95, 10 s)` as on the host (`confirmation.py`); `answer` shall be accepted only from the board button, or from a Telegram callback whose user ID equals `telegram.owner` in `ne_config` (checked by the bridge, C4); an accepted answer re-reads the facts and re-evaluates the stored arguments with `ne_decide(..., confirmed=1, ...)`. | Q-79 (2): button or the right owner ID. | TSK-I2f-12 | T |
| DP-B-08 | A pin shall move only between `ne_token_issue` and `ne_token_close` for an ALLOW, through `ne_token_authorize(token, pin)`; the HAL entry points shall require the token. | No LLM-to-GPIO path. | TSK-I2f-12, TSK-S4-01 | T |
| DP-B-09 | The partition table shall hold `factory`, `ota_0`, `ota_1` each ≥ the image, a LittleFS `ws` ≥ 1 MB for the brain's workspace (taken from `storage`), `ne_config` and `nvs_keys` (encrypted under `sdkconfig.secure`), at the box's offsets. | Brain workspace and signed OTA together; `factory` stays as the image to come back to when both OTA slots are lost, which rules out ESP-IDF's eFuse anti-rollback (DP-B-17). | TSK-I2f-14 | T |
| DP-B-10 | `ne_config` shall hold Wi-Fi, Telegram token and owner, primary and fallback LLM URL / key / model, search key and time zone; the brain receives them at start-up; no secret is ever written to the UART. | One store for secrets, as Q-79 (3). | TSK-I2f-14 | T |
| DP-B-11 | One component shall own Wi-Fi and one `esp_console`; the brain registers its commands on it and does not start Wi-Fi itself. | Two owners race at boot. | TSK-I2f-14 | T |
| DP-B-12 | Each decision at run time shall emit `NE1` trace lines on the UART, each written whole by one call of at most 512 bytes so other output cannot split it; `neuroedge record --port` shall keep reading until stopped and write replayable `trace.v1`. | DP-COM-05 on the chip. | TSK-I2f-16, TSK-S4-04 | T |
| DP-B-13 | The combined image shall meet C1, and the stack high-water mark of every task shall be reported in CI; `ne_*` keeps the 512 B rule. | Q-3 budgets with the brain inside. | TSK-I2f-15 | T |
| DP-B-14 | The image shall print `risk=single_chip` at boot and in `status`, and `risk=readable_flash` while flash encryption is off. | Q-79 (3), DP-COM-06. | TSK-I2f-14 | T |
| DP-B-15 | A signed OTA shall replace the whole image (brain and box); the boot self-test that confirms an update shall include a bridge self-check. | One update path; rollback covers the brain. | TSK-I2f-14 | T |
| DP-B-16 | Without Wi-Fi, a board button bound to an action shall be decided by the gate exactly as with Wi-Fi: no criterion of the box needs the network. | The box works offline; only chat and the LLM stop. | TSK-I2f-15 | T |
| DP-B-17 | OTA shall refuse an image whose version is not above the highest one confirmed (the box's NVS high-water mark), and pairing shall print `risk=readable_flash` and refuse to store the owner's tokens until the owner acknowledges it when flash encryption is off. | A rolled-back image would reopen fixed holes; secrets in clear flash are a choice made knowingly. No eFuse anti-rollback: it needs a table without `factory` (DP-B-09), and the owner kept `factory` (2026-10-15); a downgrade through the flash cable stays possible until Secure Boot (TSK-S6-05). | TSK-I2f-14 | T |

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
| Answer an `ask` | never over MCP: local page (DP-A-02) or box approval bot (DP-A-06) | `answer(ctx, confirmation_id, approve, &out)` from NeuroClaw-ESP's Telegram callback, which has already dropped every sender but the configured owner (`nc_core.c`); the adapter hands the bridge that owner's id, so the owner check rests on brain code (accepted under `risk=single_chip`); or `ne_bridge_answer_button` from the board (DP-B-07) |
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

The core both builds share, tested on the host against the box (`python/tests/test_c_bridge.py`).
The `nc_gate` NeuroClaw-ESP takes is the image's `main/brain.c`: it fills `nc_tool_result` field by
field with `ne_bridge_result_field`, takes one lock around every bridge call, drives pins through
`ne_hal` as the action's body would (`ne_agent_pin_op`, recorded at build time by
`engine/chip_actions.py`: on, off, or a pulse whose length may follow one argument; anything else
is refused on the chip), and writes every decision as an NE1 session (DP-B-12).

```c
#define NE_BRIDGE_CONTRACT    "tool-result.v1"
#define NE_BRIDGE_CALL_SOURCE "mcp"   /* call_source / call_channel: the bridge's, never a source's */
#define NE_BRIDGE_PENDING     4u      /* DP-COM-09 */

typedef struct {
    void *ctx;
    /* Fill facts[i] for every criterion of `gate` from on-chip sources only (DP-B-05). */
    ne_degraded (*read)(void *ctx, const ne_tree *gate, uint32_t gate_index, ne_fact *facts,
                        uint32_t count, uint32_t now_ms);
} ne_fact_source;

typedef struct {   /* run() moves pins only through ne_token_authorize (DP-B-08) */
    void *ctx;
    uint32_t (*now_ms)(void *ctx);
    ne_random_fn fill_random;
    void (*run)(void *ctx, uint32_t action, const ne_arg_value *args, uint32_t arg_count,
                ne_ledger *ledger, const ne_token *token);
} ne_bridge_hal;

typedef struct { ne_bridge_status status; uint32_t len; char json[NE_BRIDGE_RESULT_MAX]; } ne_bridge_result;

int      ne_bridge_init(ne_bridge *b, const ne_agent *agent, ne_ledger *ledger,
                        const ne_fact_source *facts, const ne_bridge_hal *hal, const char *owner_id);
uint32_t ne_bridge_tool_count(const ne_bridge *b);
int      ne_bridge_tool(const ne_bridge *b, uint32_t i, const char **name,
                        const char **description, const char **input_schema);
void     ne_bridge_call(ne_bridge *b, const char *name, const char *arguments_json,
                        ne_bridge_result *out);
void     ne_bridge_answer(ne_bridge *b, const char *confirmation_id, int approve,
                          const char *from_id, ne_bridge_result *out);   /* owner, Telegram */
void     ne_bridge_answer_button(ne_bridge *b, const char *confirmation_id, int approve,
                                ne_bridge_result *out); /* the question the board shows, by id */
uint32_t ne_bridge_waiting(ne_bridge *b);
/* An adapter reads a result back: `reason`, `message`, the first of `problems`, `confirmation.id` */
int      ne_bridge_result_field(const ne_bridge_result *r, const char *object, const char *name,
                                char *out, uint32_t cap);
/* DP-B-12: one NE1 session per decision (action_requested, gate events, the pins, trace_end) */
void     ne_bridge_trace(ne_bridge *b, ne_trace_sink *sink, const ne_device_info *info);
void     ne_bridge_trace_pin(ne_bridge *b, uint32_t pin, int driven, const char *operation,
                             uint32_t duration_ms, ne_token_reason why);   /* from run() */
uint32_t ne_bridge_pulse_ms(const ne_bridge *b, uint32_t action, const ne_agent_pin_op *op,
                            const ne_arg_value *args, uint32_t arg_count);
```

`ne_bridge` is static storage the application owns; no heap, no globals, no recursion, every
stack frame ≤ 512 bytes (C2). Each `@action` of the generated `ne_agent` carries the
`description` and compact `input_schema` that `neuroedge mcp serve` lists (DP-B-03). Answers that
cannot be taken are REJECTED with `problems` (wrong sender, no such question, already
answered, past its TTL, gate changed); a "no" is BLOCK with `reason: "declined"`. Where the box is
more lenient the bridge refuses: arguments over 256 bytes or 16 keys, a duplicate key, a numeric
string that is not a plain decimal.

### 4.4 Local page key (DP-A-02)

The terminal prints `http://127.0.0.1:<port>/#c=<code>`. The page reads `c` from
`location.hash`, removes it from the address bar, trades it at `POST /pair` (`{"code": …}`,
Origin required, no key) for `{"ok": true, "key": …}`, keeps the key in `sessionStorage`, and
sends `X-NeuroEdge-UI-Key: <key>` with every other POST. The code works once and for 10 minutes;
after that the printed URL ends in `#c=spent`. Refusal reasons: `foreign_host`, `no_origin`,
`foreign_origin`, `no_key`, `wrong_key`, `bad_code`, `bad_control`. Every page also writes `ui.json`
(mode 0600, `$STATE_DIRECTORY` or `$XDG_STATE_HOME/neuroedge`) with its URL and a control secret;
under a service manager the URL is not printed, and `neuroedge ui-link` trades the control secret
at `POST /pair/new` for a fresh code, which voids the previous one (DP-A-10). At most 10,000 refusals are traced per
session; the last one carries `last_recorded: true`.

---

## 5. Verification

Status `implemented — <file>::<test>` names a test in this repository;
`implemented in NeuroClaw — <file>::<Test>` names a Go test of the NeuroClaw repository, run by
its `neuroedge-contract` workflow against this box at a pinned commit; `implemented in CI —
<workflow>::<job>` names the job that runs a test case only an ESP-IDF build or Espressif QEMU can
run (`firmware-qemu.yml` job `brain-firmware`: scripts/qemu_brain.py, scripts/check_brain_image.py,
scripts/qemu_ota.sh with NEUROEDGE_OTA_BRAIN=1, whose host halves are tested in this repository),
and one of its steps names the test case; `planned — <TSK>` names
the roadmap task that adds the test with the code. No test is skipped in the meantime
(CONTRIBUTING.md §5).

| TC | Verifies | Level | Procedure → expected | Status |
|:---|:---|:---|:---|:---|
| TC-COM-01-1 | DP-COM-01 | unit | Every tool-call corpus result → valid against tool-result.v1 | implemented — python/tests/test_contracts.py::test_every_tool_call_corpus_result_validates_against_the_tool_result_schema |
| TC-COM-01-2 | DP-COM-01, DP-COM-02 | host C | Same agent and facts through the box (`call_tool`, source `mcp`) and through the bridge host harness → equal result objects per call, each valid against tool-result.v1 (only `confirmation.who` names the chip's human channel) | implemented — python/tests/test_c_bridge.py::test_the_same_calls_give_the_same_results_through_mcp_and_through_the_bridge |
| TC-COM-02-1 | DP-COM-02 | unit | Published `outputSchema` of every tool → the frozen schema pinned to its name | implemented — python/tests/test_contracts.py::test_the_published_output_schema_of_every_tool_is_the_frozen_result_schema_pinned_to_its_name |
| TC-COM-03-1 | DP-COM-03 | host C | C walker vs host engine on every gate → same verdict, reason, failed criterion | implemented — python/tests/test_c_walker.py::test_the_c_walker_matches_the_host_engine_on_every_gate |
| TC-COM-03-2 | DP-COM-03 | integration | Same facts with and without the network transport → same verdict | implemented — python/tests/test_mcp_http.py::test_the_same_facts_give_the_same_verdict_with_or_without_the_network |
| TC-COM-04-1 | DP-COM-04 | unit | `confirm` from each non-human source → refused | implemented — python/tests/test_tool_confirm.py::test_only_a_person_on_the_device_may_answer |
| TC-COM-04-2 | DP-COM-04 | unit | System 2 tries to answer the question its own call raised → refused | implemented — python/tests/test_tool_confirm.py::test_system_two_cannot_answer_the_question_its_own_call_raised |
| TC-COM-04-3 | DP-COM-04 | integration | MCP client lists tools → no confirm tool; cannot answer | implemented — python/tests/test_tool_confirm.py::test_an_mcp_client_has_no_way_to_confirm |
| TC-COM-05-1 | DP-COM-05 | integration | `verify` replays every canonical trace → same verdicts, names what it did not check | implemented — python/tests/test_cli.py::test_verify_replays_every_canonical_trace_and_states_what_it_did_not_check |
| TC-COM-05-2 | DP-COM-05 | QEMU | Device replays every canonical trace → matches golden | implemented — python/tests/test_trace_vectors.py::test_the_device_replays_every_canonical_trace_to_its_golden |
| TC-COM-06-1 | DP-COM-06 | QEMU | Profile B, box and brain in one image without flash encryption → `risk=single_chip` and `risk=readable_flash` each printed once at start, both listed by `status` | implemented in CI — .github/workflows/firmware-qemu.yml::brain-firmware |
| TC-COM-06-2 | DP-COM-06 | integration | Profile A: start box and brain with a risky option on (NeuroClaw's own Q-80 labels, the box's legacy System 2) → each label printed once at start and listed by `status` | implemented in CI — .github/workflows/ci-sim-linux.yml::install-full |
| TC-COM-07-1 | DP-COM-07 | demo | A blank Ubuntu machine (the CI runner) → `neuroedge install --profile full` → box and brain up, and the brain turns the light on through the box (a stand-in LLM, Telegram off) | implemented in CI — .github/workflows/ci-sim-linux.yml::install-full |
| TC-COM-07-2 | DP-COM-07 | board | A blank DevKitC → one command flashes the one image and the owner chats to the light | planned — TSK-I2f-13 |
| TC-COM-08-1 | DP-COM-08 | unit (Go) | NeuroClaw reads a result with `status: "MAYBE"` and one with contract `tool-result.v2` → REJECTED, no retry as allowed | implemented in NeuroClaw — pkg/tools/integration/neuroedge_result_test.go::TestNeuroEdgeToolGuidance_AnUnknownStatusOrMajorIsNotDone |
| TC-COM-08-2 | DP-COM-08 | integration | `tools/list` over MCP → every tool carries `_meta["dev.neuroedge/contract"] = "tool-result.v1"`, the name of `schemas/tool-result.v1.json` | implemented — python/tests/test_contracts.py::test_every_listed_tool_names_the_result_contract_it_answers_in |
| TC-COM-09-1 | DP-COM-09 | integration | Five calls that ask, none answered → four questions pending, the fifth is BLOCK `budget_exceeded` with no question (Profile A) | implemented — python/tests/test_tool_confirm.py::test_a_fifth_question_while_four_wait_is_a_block_and_no_question |
| TC-COM-09-2 | DP-COM-09 | host C | Same on the bridge's pending table (Profile B) | implemented — python/tests/test_c_bridge.py::test_four_questions_wait_at_most_and_allow_still_runs |
| TC-A-01-1 | DP-A-01 | integration | No token, bad token, wrong scope, other device's token → 401/403, nothing dispatched, traced | implemented — python/tests/test_mcp_http.py::test_a_request_without_a_valid_token_is_refused_and_nothing_is_dispatched |
| TC-A-01-2 | DP-A-01 | integration | Client without a trusted certificate → TLS handshake fails before HTTP | implemented — python/tests/test_mcp_http.py::test_a_client_without_a_trusted_certificate_never_reaches_http |
| TC-A-01-3 | DP-A-01 | integration | Client limited to TLS 1.2 → refused | implemented — python/tests/test_mcp_http.py::test_a_client_that_will_not_speak_tls_13_is_refused |
| TC-A-02-1 | DP-A-02 | integration | POST /confirm with the right Origin and no key → 403, no `tool_confirmed`, pin unchanged, `ui_auth_refused` `no_key` | implemented — python/tests/test_tool_confirm.py::test_a_local_process_without_the_key_cannot_answer_the_device |
| TC-A-02-2 | DP-A-02 | integration | Wrong key → 403, traced `wrong_key`, key absent from the trace | implemented — python/tests/test_tool_confirm.py::test_a_wrong_key_is_refused_and_traced_without_the_key |
| TC-A-02-3 | DP-A-02 | integration | Right key, no Origin (curl) → 403, traced `no_origin` | implemented — python/tests/test_tool_confirm.py::test_a_request_with_no_origin_is_refused_even_with_the_key |
| TC-A-02-4 | DP-A-02 | integration | Page headers (Origin + key) → answer accepted with source `ui`, light switches | implemented — python/tests/test_tool_confirm.py::test_the_page_offers_the_buttons_and_the_answer_goes_through_the_gate |
| TC-A-02-5 | DP-A-02 | integration | GET `/`, `/state`, `/events` and the printed URL → key absent; URL ends in `#c=<code>`; key ≥ 43 characters | implemented — python/tests/test_sim_ui.py::test_the_key_is_never_in_the_page_the_state_or_the_printed_url |
| TC-A-02-6 | DP-A-02 | integration | Two servers → two different keys | implemented — python/tests/test_sim_ui.py::test_each_run_has_its_own_key |
| TC-A-02-7 | DP-A-02 | integration | Studio `/api/lint` POST without the key → 403, traced `no_key` | implemented — python/tests/test_studio_server.py::test_the_studio_refuses_an_action_without_the_runs_key |
| TC-A-02-8 | DP-A-02 | integration | `mcp serve --ui` prints the URL with `#c=<code>` on one line of stderr and never `#k=` | implemented — python/tests/test_mcp_serve_ui.py::test_a_taken_port_moves_the_page_and_keeps_serving_mcp |
| TC-A-02-9 | DP-A-02 | integration | Pair with the printed code → the key; pair again with it → 403 `bad_code`; URL now ends in `#c=spent` | implemented — python/tests/test_sim_ui.py::test_the_printed_code_pairs_once_and_then_is_spent |
| TC-A-02-10 | DP-A-02 | integration | Wrong code, no Origin, or after 10 minutes → 403 | implemented — python/tests/test_sim_ui.py::test_a_wrong_or_late_code_does_not_pair |
| TC-A-02-11 | DP-A-02 | integration | Refused POST to a 5,000-character path → traced path is 64 characters | implemented — python/tests/test_sim_ui.py::test_a_refused_path_is_traced_cut_short |
| TC-A-03-1 | DP-A-03 | linux | Brain user in group `gpio`, able to read the key directory, or `/proc` without `hidepid` → `neuroedge doctor` exits 1 naming it | implemented — python/tests/test_isolation.py::test_doctor_exits_one_naming_each_problem |
| TC-A-03-2 | DP-A-03 | linux | Process as brain user opens `/dev/gpiochip0` and the box key → EACCES; POST /confirm → 403 | implemented in CI — .github/workflows/ci-sim-linux.yml::linux-hal |
| TC-A-04-1 | DP-A-04 | integration | Token with 8-day lifetime → refused at issue; `pair renew` → new token accepted, old one refused after expiry, box not restarted | implemented — python/tests/test_mcp_http.py::test_a_token_lives_at_most_seven_days_and_renews_without_a_restart |
| TC-A-05-1 | DP-A-05 | linux | `mcp serve --http --ui --target linux` with an `ask` → page answers it; without page and bot → expires and is traced | implemented — python/tests/test_session_linux.py::test_on_linux_the_page_at_home_answers_the_boxs_question |
| TC-A-06-1 | DP-A-06 | integration | Approval record with bad signature, reused nonce, expired, other gate digest → refused; valid → accepted as `chat:<id>` | planned — TSK-I2d-11 |
| TC-A-06-2 | DP-A-06 | integration | Brain's bot token configured as approval bot → box refuses to start | planned — TSK-I2d-12 |
| TC-A-07-1 | DP-A-07 | CI (Go) | NeuroClaw integration job starts the pinned box on `sim`, calls light / door / night cases and `fixtures/agents/contract-bench` → every result validates, `fallback` and `escalated_to` handled | implemented in NeuroClaw — pkg/tools/integration/neuroedge_box_test.go::TestNeuroEdgeBox_EscalationAndFallback |
| TC-A-08-1 | DP-A-08 | unit | Without the flag: `run` answers with grammar, System 1 and the offline answer; no LiteLLM import; with the flag: the old path works | implemented — python/tests/test_legacy_system_two.py::test_without_the_flag_the_box_answers_with_grammar_and_the_offline_line |
| TC-A-09-1 | DP-A-09 | demo | Blank VM → `neuroedge install --profile full` → services up, brain user isolated (TC-A-03-2 passes), chat turns on the light | implemented in CI — .github/workflows/ci-sim-linux.yml::install-full |
| TC-A-10-1 | DP-A-10 | linux | Box under systemd → URL file mode 0600 owned by the box user; journal has no `#c=`; `neuroedge ui-link` prints a new code and the old one stops working | implemented — python/tests/test_mcp_serve_ui.py::test_under_a_service_manager_the_link_goes_to_a_private_file_and_ui_link_renews_it |
| TC-A-11-1 | DP-A-11 | integration | Rotate the brain certificate → new one works without restart; revoked thumbprint → handshake refused | implemented — python/tests/test_mcp_http.py::test_a_brain_certificate_rotates_without_a_restart_and_a_revoked_one_is_cut_off |
| TC-B-01-1 | DP-B-01 | unit | `build --brain neuroclaw` writes the component pin; tampered SHA-256 → build error naming the file | implemented — python/tests/test_firmware_brain.py::test_a_tampered_brain_fails_the_build_naming_the_pin |
| TC-B-02-1 | DP-B-02 | inspection | Image symbols contain no MCP server, no `mbedtls_ssl_conf_*` server role | implemented in CI — .github/workflows/firmware-qemu.yml::brain-firmware |
| TC-B-03-1 | DP-B-03 | host C | Bridge tool list for the demo agent equals the MCP tool list (names, schemas) | implemented — python/tests/test_c_bridge.py::test_the_bridge_offers_the_tools_the_box_lists_over_mcp |
| TC-B-04-1 | DP-B-04 | host C | Arguments table: unknown key, missing key, string for number, out of range → REJECTED with `problems`; walker never called | implemented — python/tests/test_c_bridge.py::test_bad_arguments_are_rejected_before_any_gate |
| TC-B-05-1 | DP-B-05 | host C | Call carries `"temperature": 99`; fact source reads 25 → verdict follows 25 | implemented — python/tests/test_c_bridge.py::test_a_value_in_the_call_never_becomes_a_fact |
| TC-B-06-1 | DP-B-06 | host C | Every `ne_result` reason and `on_block` action → mapped JSON valid against tool-result.v1 | implemented — python/tests/test_c_bridge.py::test_every_reason_and_on_block_action_maps_to_a_valid_result |
| TC-B-07-1 | DP-B-07 | host C | Expired confirmation, second answer, wrong `from_id` → refused; owner callback and button → ALLOW once with the stored arguments and freshly read facts; ALLOW tokens still issue while 4 asks are pending | implemented — python/tests/test_c_bridge.py::test_only_the_owner_or_the_button_answers_once_and_facts_are_read_again |
| TC-B-08-1 | DP-B-08 | host C | HAL drive without token, with closed token, with token for another pin → refused, pin unchanged | implemented — python/tests/test_c_hal.py::test_a_pin_moves_only_on_its_own_live_token |
| TC-B-09-1 | DP-B-09 | unit | Generated partition table: offsets aligned, OTA slots ≥ image, `ws` ≥ 1 MB, `nvs_keys` encrypted | implemented — python/tests/test_firmware_brain.py::test_the_brains_partition_table_holds_box_brain_and_signed_ota |
| TC-B-10-1 | DP-B-10 | QEMU | Set all keys at the hidden prompt, reboot → brain configured; UART capture contains no secret | implemented in CI — .github/workflows/firmware-qemu.yml::brain-firmware |
| TC-B-11-1 | DP-B-11 | QEMU | Boot combined image → one Wi-Fi start, one console with both command sets | implemented in CI — .github/workflows/firmware-qemu.yml::brain-firmware |
| TC-B-12-1 | DP-B-12 | QEMU | Three tool calls → `record --port` writes a trace that `verify` replays to the same verdicts | implemented — python/tests/test_c_bridge.py::test_every_decision_is_a_trace_session_that_replays_to_the_same_verdicts |
| TC-B-13-1 | DP-B-13 | QEMU | Size job: image ≤ 3.5 MB; free SRAM ≥ 120 KB after brain start; stack report per task; `ne_*` ≤ 512 B | implemented in CI — .github/workflows/firmware-qemu.yml::brain-firmware |
| TC-B-14-1 | DP-B-14 | QEMU | Boot without flash encryption → both labels at boot and in `status` | implemented in CI — .github/workflows/firmware-qemu.yml::brain-firmware |
| TC-B-15-1 | DP-B-15 | QEMU | OTA to an image whose bridge self-check fails → rollback to the previous image | implemented in CI — .github/workflows/firmware-qemu.yml::brain-firmware |
| TC-B-16-1 | DP-B-16 | QEMU | Network down; button bound to `light_off` → ALLOW; to `front_door_unlock` at night → BLOCK; same verdicts as with the network | implemented in CI — .github/workflows/firmware-qemu.yml::brain-firmware |
| TC-B-17-1 | DP-B-17 | QEMU | OTA of the image of box and brain to a lower version → refused (`reason=downgrade`), old image keeps running; pairing without flash encryption → label printed, tokens stored only after acknowledgement | implemented in CI — .github/workflows/firmware-qemu.yml::brain-firmware |
| TC-BP-01-1 | DP-BP-01 | analysis | Decision note merged under `docs/reports/` with measurements and a recommendation | planned — TSK-I2f-17 |
| TC-NF-01-1 | DP-NF-01 | board | 1,000 calls on DevKitC → bridge overhead p95 ≤ 5 ms | planned — TSK-I2f-15 |
| TC-NF-02-1 | DP-NF-02 | inspection | Every place that fetches NeuroClaw names a version and a SHA-256 (today `build --brain neuroclaw`, from `targets/esp32s3/brain/neuroclaw.lock`; the installer of DP-A-09 reads the same kind of pin) | implemented — python/tests/test_firmware_brain.py::test_the_committed_pin_names_a_commit_and_a_tree |

---

## 6. Traceability

| Requirement | Decision | Task | Test cases |
|:---|:---|:---|:---|
| DP-COM-01 … 09 | Q-83, Q-72, Q-73, Q-79 | TSK-I2d-25, TSK-I2d-26, TSK-I2f-12 | TC-COM-* |
| DP-A-01 … 11 | Q-76, Q-83 | TSK-I2d-11, TSK-I2d-12, TSK-I2d-24, TSK-I2d-25, TSK-I2d-26, TSK-I2d-27 | TC-A-* |
| DP-B-01 … 17 | Q-79, Q-83 | TSK-I2f-12, TSK-I2f-14, TSK-I2f-15, TSK-I2f-16, TSK-S4-01, TSK-S4-04 | TC-B-* |
| DP-BP-01 | Q-83 | TSK-I2f-17 | TC-BP-01-1 |
| DP-NF-01, 02 | Q-83 | TSK-I2f-15, TSK-I2d-26 | TC-NF-* |
