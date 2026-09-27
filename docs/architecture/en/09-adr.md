# 09 · Architecture decisions (ADR)

> **Scope:** the decisions that shape the architecture, each as an ADR: context → decision →
> consequences → where it is enforced. **Sources:** the single decision register is PRD §15 (codes
> `Q-N`); changes to frozen contracts are RFCs (`docs/rfc/`). This page does **not** replace those two
> sources: it shows what each decision looks like in the architecture, and which code holds it.

ADR identifiers are the `Q-N` or `RFC-NNNN` codes, so there are no two numbering systems. The full
status of the 46 decisions is in PRD §15; below are the decisions with architectural consequences.

## 1. Execution and safety

### Q-24 · Every action is a tool call through a single path
- **Context.** An action can come from local grammar, an LLM, another agent. Multiple entry paths are
  multiple places to forget the gate.
- **Decision.** Every `@action` is a tool with a schema generated from the function signature. Every
  source sends the same `ToolCall` through `dispatch()` → `c.do()` → gate → token; the dispatcher
  inserts `call_source`.
- **Consequences.** A single enforcement point; the gate can distinguish call sources; MCP is a thin
  adapter.
- **Enforcement.** `actions/tools.py::dispatch`, `mcp_server.py`; `docs/spec/tool_calling.md`; corpus
  `fixtures/tool_calls/`.

### Q-9 · No CEL on the microcontroller (option A)
- **Context.** An expression evaluator on chip is one more implementation to keep in sync, in the
  safety layer.
- **Decision.** `neuroedge build` compiles gates into a deterministic decision tree; firmware only
  walks the tree. `allow_when` today is an operator mapping; CEL is an optional front-end later
  (TSK-S2-06, on hold).
- **Consequences.** Gate semantics have one source (the Python engine); the chip is small and
  deterministic; every new operator must compile down to the same tree.
- **Enforcement.** `engine/decision_tree.py`; the resolver rejects string-form `allow_when`.

### Q-23, RFC-0003 · The on-device tree is the fixed binary layout `NETR` v1
- **Context.** A JSON parser on an MCU costs flash, RAM and is an attack surface.
- **Decision.** Little-endian binary layout, no pointers, with magic, version and CRC, linked as a
  `const` array in flash; `decision_tree.v1.json` is only the host's internal format.
- **Consequences.** The walker reads in place, does not allocate; changing the layout is an RFC matter
  and bumps `layout_version`.
- **Enforcement.** `engine/binary_tree.py` ↔ `components/ne_gate/`; `test_c_walker.py`.

### Q-18, RFC-0004 · Child gates may not loosen `budget` and `on_block`
- **Decision.** Child `p95` ≤ parent; a chain already `closed` cannot reopen; a child may not add
  `degrade` or change `fallback_action`.
- **Consequences.** Inheritance is a tighten-only relation on **every** field with a safety effect, not
  just `allow_when`.
- **Enforcement.** `engine/gate_resolver.py`; corpus `fixtures/gates/invalid/`.

### Q-25, RFC-0005 · Argument limits live in the gate
- **Decision.** Ranges, sets and lengths of arguments are declared in the gate (not in `agent.toml`),
  may only be narrowed on inheritance, are checked before every fact including default values, and
  appear in `inputSchema`.
- **Consequences.** A dangerous argument (`duration_s = 3600`) is blocked by the gate, independent of
  the caller.
- **Enforcement.** `engine/arguments.py`; the argument record in `NETR`.

### Q-26, RFC-0006 · Only the person at the device can confirm, and only for criteria the gate lists
- **Decision.** Only `local_grammar` and `ui` can answer an `ask` question; a confirmation
  **re-evaluates** the gate, exempting only the criteria in `on_block.confirms`.
- **Consequences.** A "yes" never gets past another criterion; models and MCP clients have no
  confirmation path.
- **Enforcement.** `actions/confirmation.py`; `test_tool_confirm.py`; `confirm_mask` in `NETR`.

### Q-17 · Every `on_block` blocks the physical action
- **Decision.** `escalate` and `ask` still record a trace and call hooks (which do nothing by default);
  `degrade` runs `fallback_action` **through its own gate**.
- **Enforcement.** `engine/gate.py`, `actions/conversation.py`.

### Q-14 · Offline, the gate still evaluates with local command grammar
- **Decision.** Block with `gate_unreachable` only when there is no fallback or it cannot run. Fallback
  is P0; one backend per target on the same grammar.
- **Enforcement.** `models/grammar.py`, `models/system.py`; `test_offline_fallback.py`. On `esp32s3`:
  not yet (TSK-S5-07).

## 2. Models and providers

### Q-4, Q-12 · System 1 is Jev via the System One API; System 2 is a standard OpenAI LLM
- **Decision.** The default standard is an OpenAI-compatible platform (one base URL, one key): chat
  completions, audio, and a typed decision endpoint (`POST /systemone`). Other providers go through
  self-written adapters.
- **Consequences.** Changing provider is changing configuration; models return only facts
  (`Fact`/`Unavailable`), never verdicts.
- **Enforcement.** `models/providers/`, `perception/providers/`.

### Q-10 · LiteLLM is a library, not a proxy
- **Decision.** Use LiteLLM as an SDK, always behind `neuroedge.models.providers`, installed only via
  the `cloud` extra.
- **Consequences.** `pip install neuroedge` is light and needs no key; no server is operated by
  NeuroEdge.
- **Enforcement.** `pyproject.toml`; job `cloud-extra`.

### Q-27 · System 2 is an MCP host
- **Decision.** Device tools go through the agent's own MCP server (still through the gate); external
  MCP servers are only for information, per an allowlist, and their results are untrusted data. The MCU
  is never a host.
- **Enforcement.** `mcp_host.py`; `test_mcp_host.py`.

### Q-7, Q-45 · Wake word: the user supplies the model
- **Decision.** openWakeWord on host, microWakeWord on chip (Q-7). openWakeWord's bundled models have a
  non-commercial license, incompatible with Q-45 ⇒ not shipped, not downloaded.
- **Enforcement.** `perception/providers/wake.py`; `TODOS.md` #49.

## 3. Hardware, targets, simulation

### Q-2, Q-3 · One reference board and one memory budget
- **Decision.** ESP32-S3-BOX-3 is the only reference board (invariant 6). Budget: SRAM ≥ 120 KB and
  PSRAM ≥ 2 MB for the application, firmware ≤ 3.5 MB to fit A/B on 16 MB flash.
- **Enforcement.** `boards/esp32s3-box-3.toml`, `partitions.csv`, `scripts/check_firmware_size.py`.

### Q-8 · C on ESP-IDF for the chip, Python for the host
- **Consequences.** Two implementations of one spec ⇒ a normative spec and shared compliance vectors
  are mandatory.
- **Enforcement.** `test_c_walker.py`, `test_c_token.py`, `test_c_trace.py`; boot self-test.

### Q-13 · Three target tiers
- **Decision.** Tier 1 (`sim`, `linux`, `esp32s3`) keeps all commitments; tier 2 is maintained by the
  core team with narrower commitments; tier 3 is ported by the community and self-checked with the
  compliance suite.
- **Status.** A machine-readable tier table (`TARGET_TIERS`) is only proposed in RFC-0002; the code
  today has exactly three targets.

### Q-16, Q-21 · Layered simulation with proven open-source tools
- **Decision.** Do not write a simulator. One tool per layer: `SimHAL`, gpio-sim, `i2c-stub` + `lm75`,
  virtual framebuffer, LVGL golden images built on host, C compiled on host, Espressif QEMU; real
  boards for audio, display, memory. Renode and Wokwi are not used.
- **Enforcement.** `docs/spec/simulation_coverage.md`; jobs `linux-hal`, `ui-golden`, `firmware-qemu`.

### Q-22 · Software echo cancellation on `linux`
- **Decision.** `audio.in` reads PipeWire `module-echo-cancel`'s echo-cancelled source node; `audio.out`
  plays into its sink node as the reference signal. `linux-rpi5` declares `aec = true` only once
  measured.
- **Enforcement.** `hal/linux.py`, `pipewire/neuroedge-echo-cancel.conf`.

## 4. Governance, licensing, schedule

### Q-11 · Allowed license list
- **Decision.** Allow MIT, BSD, Apache-2.0, ISC, PSF, CNRI-Python, MPL-2.0 (unmodified), Zlib,
  CC0-1.0; forbid GPL/LGPL/AGPL, SSPL, BSL. Hawkbit (EPL-2.0) is used unmodified as a service; **EMQX
  (BSL) is not used**.
- **Consequences.** `gpiod` (LGPL) is only an optional extra; the Fleet OS MQTT broker is chosen among
  Mosquitto, NanoMQ, VerneMQ.
- **Enforcement.** `scripts/check_licences.py`; jobs `cloud-extra`, `licence-obligations`.

### Q-45 · NeuroEdge's license
- **Decision.** Code under PolyForm Noncommercial 1.0.0; `schemas/`, `docs/spec/`, `fixtures/compliance/`
  under Apache-2.0 so anyone can implement the standard.
- **Enforcement.** `LICENSE`, `LICENSING.md`, `test_packaging.py`.

### Q-39 · Roadmap by increment
- **Decision.** One roadmap, measured in increments I0…I18, each increment with one forecast date, one
  tag and one measurement signal; no external release before I6.
- **Enforcement.** `neuroedge-roadmap.md` §0.2; `test_plan_contract.py`.

### Q-38 · Not a certified safety function
- **Decision.** Temporarily OUT: no SIL, no PL; mobile robots must have a hardware emergency stop
  button.

## 5. Decisions for the expansion direction (no code yet)

| Code | Decision | Consequence when implemented |
|:---|:---|:---|
| Q-32 | Tiered robotics after Developer Beta; multi-node traces extend `trace.v1` with optional fields | No `trace.v2` needed |
| Q-35 | Every actuator declares its safe state on loss of communication; no declaration means stop | Needs an RFC for the declaration field |
| Q-36 | Zenoh-pico on the MCU, `zenohd` on the Pi; spike with pass/fail thresholds, micro-ROS is plan B | Node RFC draft |
| Q-37 | Time-limited lease tokens for `motion.*` (channel, maximum amplitude, short TTL), renewed through each gated command | Different from today's one-time token; needs an RFC-motion |

## 6. RFCs

| RFC | Contract | Status | Implementation |
|:---|:---|:---|:---|
| [0001](../../rfc/0001-gate-schema-conditional-requirements.md) | `gate.v1`: conditionally required fields for inherited gates | Accepted, implemented | `schemas/gate.v1.json` |
| [0002](../../rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md) | Open the target list by tier | **Under discussion**; part of I11 | not yet |
| [0003](../../rfc/0003-bo-cuc-nhi-phan-cay.md) | Binary layout `NETR` v1 | Accepted, implemented | `binary_tree.py`, `ne_gate/` |
| [0004](../../rfc/0004-ke-thua-budget-on-block.md) | No loosening of `budget`, `on_block` on inheritance | Accepted, implemented | `gate_resolver.py` |
| [0005](../../rfc/0005-rang-buoc-tham-so-trong-gate.md) | Argument limits in the gate | Accepted, implemented | `arguments.py`, `NETR` argument record |
| [0006](../../rfc/0006-xac-nhan-ask-confirms.md) | `on_block.confirms` | Accepted, implemented | `confirmation.py`, `confirm_mask` |

## 7. Making a new architecture decision

1. **The decision** is recorded in PRD §15 with a new `Q-N` code — the only place.
2. If it changes something in the `CONTRIBUTING.md` §3 list (schemas, resolution semantics, normative
   traces, locked gates, `NETR` layout) it needs an **RFC**: the first PR contains only the RFC file;
   the next PR cites the RFC number.
3. If it has architectural consequences, add an ADR entry to this page (context, decision,
   consequences, enforcement), citing the `Q-N` code — do not copy the decision text.
4. If it changes the dependency graph between packages, edit `ALLOWED` in
   `python/tests/test_architecture_layers.py` and the table in [`03`](03-component-host-c4l3.md) §2 in
   the same change.
