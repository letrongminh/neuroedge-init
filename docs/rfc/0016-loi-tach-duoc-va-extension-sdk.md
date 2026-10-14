# RFC-0016: Standalone Safety Core and Extension SDK — Extension Points, Trust Model, Compliance Test Suite

| | |
|:---|:---|
| **RFC Code** | 0016 |
| **Title** | Standalone safety core (`neuroedge.guard`) and Extension SDK (`neuroedge.sdk`): six extension point kinds via Python entry points, explicit activation and provenance recorded in traces, dedicated stability commitment, out-of-package assets (`--board <path>`, `--template`, multiple gate registry roots), type-specific compliance test suite — TSK-I2c-02 |
| **Affected contracts** | Two new public modules `neuroedge.guard`, `neuroedge.sdk` *(`docs/spec/python_api.md` §1 adds concept of "public by location"; §2, §6)* · `[plugins]` section of `agent.toml` and new file `guard.toml` with `[guard]`, `[registry]`, `[tools]`, `[plugins]` *(outside `schemas/`; checked at `neuroedge build` and load time, like `[external]` of RFC-0014; `guard.toml` also accepts `[external]` and `[actuators]` from RFC-0014, RFC-0018)* · CLI contracts *(new commands `plugin list`, `plugin doctor`, `conformance`, `bridge run`; flags `--board`, `--template` accept references, `--registry` repeatable — §4)* · file discovery locations of `GateRegistry` *(`engine/gate_resolver.py`: multiple roots; merge and inheritance unchanged — §3f)* · `docs/spec/threat_model.md` *(new section §2d)* · new specification `docs/spec/extension_sdk.md` · **does not** touch `schemas/`, `gate.v1`, `trace.v1`, `board.v1`, `NETR`, `digests.lock`, three canonical traces; **no** new error codes |
| **Related PRD requirements** | FR-EXT-01 → FR-EXT-05, FR-EXT-09, NFR-SEC-10 *(FR-EXT-08 only at hook point, §3g)* · FR-MDL-08, FR-GOV-03, A3, A13 |
| **Proposer** | — |
| **Date opened** | 2026-10-04 |
| **Status** | ✅ Approved (2026-10-04) — lead engineer signed off on PR #99; decisions for open questions in §9 (Q-68) |
| **Approvers** | **Lead Engineer — mandatory** (establishes a new public commitment for external parties; opens path for third-party code into gatekeeper process; modifies gate discovery location in `engine/gate_resolver.py`) |

> **When an RFC is required:** `CONTRIBUTING.md` §3. This RFC **does not** modify `schemas/*.json`, three canonical traces, `digests.lock`, or `NETR`; it touches `engine/gate_resolver.py` (§3: file discovery locations of `GateRegistry`, merge and
> inheritance intact — §3f) and establishes the stability commitment of `neuroedge.sdk` (D7), so it goes through an RFC like RFC-0013. Task: **TSK-I2c-02**; implementation: TSK-I2c-07, -08, -11, -12, -13, -18. Foundational decisions: `neuroedge-prd.md` §15
> **Q-67** — D1 (increment I2c), D4 (out-of-tree board portion; target enum portion in [RFC-0002](0002-mo-rong-target-va-nguyen-thuy-thi-giac.md)), D7 (`neuroedge.sdk`), D8 (licensing: PolyForm NC runtime, plugins per author).
> Aligned with: [RFC-0014](0014-du-kien-tu-tien-trinh-ngoai.md) (external facts), [RFC-0015](0015-hop-dong-cho-nguoi-tich-hop.md) (§3a `request`, §5), [RFC-0013](0013-nguyen-thuy-tuy-chon-va-nhieu-bo-tham-chieu.md) (reference boards),
> [RFC-0017](0017-nguon-goi-theo-khong-gian-ten.md) "Namespaced Call Sources and Client Identities", [RFC-0018](0018-co-cau-chap-hanh-tu-xa.md) "Remote Actuators and Auto-Off Levels" (drafted concurrently with this RFC; portions of each RFC take that RFC as source, only referenced here).
> All assertions about code verified against the repository at `7a43d93`; unverified items marked "unverified".

## 1. Problem

1. **Core is only usable via the agent model.** The path from call to pin is `dispatch(conversation, tools, call)` (`python/neuroedge/actions/tools.py:327`). `ToolSet` is built from `ActionSpec`, where `ActionSpec` is a Python function with `@action` (`actions/spec.py`), and `check_arguments` obtains
   the parameter schema **from the function signature** (`tools.py:75`, `:135`). The existing way to assemble engine + token ledger + envelope + trace is `SimSession.load`, requiring `agent.toml` and `commands.toml` (`sim/session.py:864–871`). An MCP proxy, a Muse bridge, or a ROS node has no `@action` and needs no command grammar.
2. **No extension points.** `python/pyproject.toml` contains only `[project.scripts]` (`:111`), no entry points. HAL backend is selected via `if target == "linux"` (`sim/session.py:917`, `:938`) and `SESSION_TARGETS` (`:621`). `--board` accepts only ids: `load_board_by_id` (`hal/board.py:738`) looks up `boards_dir()`;
   `load_board(path)` exists (`:733`) but no CLI flag uses it. `TEMPLATES` (`templates/__init__.py:31`) and `KINDS` (`templates/add.py:36`) are fixed tuples; `GateRegistry` has only one root (`engine/gate_resolver.py:110`). The only opened ingress is model providers: `provider = "python:pkg.mod:factory"` (`models/providers/common.py:36`, `:324`; FR-MDL-08).
3. **Opening via `python:` loses structural guarantees.** `Conversation(engine, hal=...)` accepts any HAL (`actions/conversation.py:72`, `hal: Any`) and `neuroedge.__all__` has `SimHAL`, `LinuxHAL`, `HardwareAbstractionLayer`, `digital`, `motion` (`__init__.py:63`): an adapter of type `python:` is handed the entire HAL.
   There is nowhere to state "bridges never touch pins", and nothing for the compliance suite to target.
4. **No commitment for external authors.** `python_api.md` §1 only promises names in `__all__`; submodules are "not promised"; in `0.x`, MINOR acts as MAJOR (§3). A plugin has no guarantee it will run on the next release.
5. **`@action` bodies calling external SDKs (HTTP to Home Assistant…) lack envelopes and do not auto-off.** The remote actuator portion belongs to RFC-0018; this RFC only reserves extension points (§3c).

## 2. Why the Current Mechanism Does Not Solve This

- `__all__` promises by **name**, lacking any concept of "plugin surface" with independent versioning (`python_api.md` §1, §3). D7 demands a module with a commitment distinct from `__all__`.
- The `python:` adapter is a factory function returning an object: no protocol, no version, no grouping. `load_adapter` simply calls `import_module` (`common.py:324`); no `plugin list`, no version reconciliation, no provenance in traces.
- **`dispatch` is not safe for multiple concurrent callers on a single `Conversation`.** It temporarily sets `conversation.facts` and restores it (`tools.py:351–356`). Verified by trial run on `fixtures/agents/home-voice`: two concurrent `dispatch`es (`mcp` then `system_two`), each `evaluate` sees its own correct
  `call_source`, but when both finish, `conversation.facts["call_source"]` remains `"mcp"` (the latter call restored the former call's snapshot). `Conversation._do` also reads `self.facts` after an `await` to log the source of an `ask` prompt (`conversation.py:195`; this path is **unverified**).
  A Guard serving multiple bridges must handle this (§3b item 5).
- Entry points: `importlib.metadata` is standard library, `requires-python >= 3.11` (`pyproject.toml:11`), adding zero dependencies (`:36`). Verified by trial run on Python 3.13.6: listing entry points **imports no** package; `Distribution.locate_file` returns paths without importing; for editable installs
  (`direct_url.json` has `dir_info.editable`), `files` of `neuroedge` itself lists only `.pth` and `dist-info` files, **not** source code (hence cannot be hashed, §3d). Python 3.11 and 3.12: unverified.

## 3. Proposed Changes

### 3a. Scope

| This RFC decides | Deferred, not done here |
|:---|:---|
| `neuroedge.guard` (§3b) · `neuroedge.sdk`: Protocol, structural invariants, stability (§3c, §3e) · activation, trust, provenance (§3d) · out-of-package assets (§3f) · compliance framework and test check list (§3g) | External fact pipeline and receiver: RFC-0014 (code: TSK-I2c-09) · `source` grammar, bridge id, client identity: RFC-0017 (TSK-I2c-03, -10) · `Actuator` function signature, L0–L3 auto-off levels, `[actuators]` declaration, actuator compliance vectors: RFC-0018 (TSK-I2c-04, -16) · target enum, `TARGET_TIERS`, `board validate`: RFC-0002 (TSK-I2c-05) · pinning `extends` via digest, gates from git/OCI: TSK-S3-21 (`TODOS.md` #15) · `proxy mcp/http`, `guard init`: TSK-I2c-14, -15 · index, `plugin search/install`, badges: TSK-I2c-18 · plugin signing: I10 |

### 3b. `neuroedge.guard` — Standalone Core

Any program (MCP proxy, bridge, ROS node) gets gate → token → envelope → trace without needing `agent.toml`, `@action`, or `SimSession`:

```python
from neuroedge.guard import Guard, Tool
from neuroedge.sdk import ToolRequest

guard = Guard.load("guard.toml")        # or Guard(tools=[Tool(...)], gates=[...], board=None): no agent.toml needed
async with guard:                       # exit ⇒ releases pins, like SimSession.close()
    ros = guard.dispatcher("ros_node")  # register id (grammar of RFC-0017 §3a); source is always "bridge:ros_node", cannot be stated otherwise
    guard.set_fact("badge_ok", True)    # gate context set by host program, like `c.facts`
    outcome = await ros.dispatch(ToolRequest("unlock_door", {"duration_s": 5}))   # `request` of tool-call.v1 (RFC-0015 §3a): no `source`
    outcome.status      # "ALLOW" | "BLOCK" | "REJECTED" — `ToolResult.status` (tools.py:248)
    outcome.content     # exact `ToolResult.content()` (tools.py:256), valid per tool-result.v1
    trace = guard.trace()   # validated trace.v1, like `SimSession.trace()` (sim/session.py:1793)
```

```toml
# guard.toml — subset of agent.toml; unknown keys and literal secret fields ⇒ rejected, like [external] of RFC-0014 §3c
[guard]
name = "door-proxy"                 # ⇒ metadata.agent_version = "guard:door-proxy@<version>"
board = "esp32s3-box-3"             # <id> | .toml path | pkg:… (§3f); absent ⇒ no HAL, verdict only
[registry]
roots = ["gates", "vendor/gates"]   # §3f
[tools.unlock_door]
gate = "neuroedge://gates/hospitality/unlock@1.0.0"
requires = ["digital.out:door_lock"]            # like @action(requires=…); requires board
drive = [{ pin = "door_lock", operation = "pulse", seconds_from = "duration_s" }]   # declarative body (syntax in extension_sdk.md): Guard builds into `digital.out(pin).pulse(…)` under token
[tools.unlock_door.parameters.duration_s]       # JSON Schema subset of tool-call.v1 §3a.2; undeclared parameters ⇒ REJECTED (tools.py:150)
type = "integer"
default = 5
[plugins]
enable = ["neuroedge-muse"]         # §3d; remote actuators: add [actuators.<name>] from RFC-0018 §3b, same validation function as agent.toml
```

1. **Constructed from existing classes; exactly one path to pin.** `Guard` constructs `ActionContractEngine` (`engine/gate.py:148`), `TokenLedger` (`actions/token.py:70`), board HAL with `SafetyEnvelope` via `ensure_envelope` (`hal/__init__.py:737`), an `EventLog` (or `TraceRecorder` passed via `events=`,
   `testing/recorder.py:70`), and an internal `Conversation` (receiving dedicated `registry=`, `conversation.py:81`, not touching global `REGISTRY` of `@action`), then calls the **exact** `dispatch()` (`tools.py:327`). Each `Tool` becomes a data-declared `ActionSpec`. With no second code path to pins, `threat_model.md` §1–§2b applies fully (§5).
   HAL for `linux` and `sim` is constructed with the same function as `SimSession` (TSK-I2c-07 extracts block `sim/session.py:917–942` into a constructor function; `test_architecture_layers.py` updated concurrently); `esp32s3` has no Python Guard (MCU uses `ne_gate` + `NETR`, RFC-0003).
2. **ALLOW is a verdict; if `Tool` has `run`, it executes once under token.** After ALLOW, `Conversation._do` issues a single-use token (`conversation.py:210`), runs `run` inside `digital.grant` (`:221`), and closes the token (`:233`); HAL verifies `require_pin → envelope → authorize → record` (`hal/__init__.py:231`).
   `run` is the **only** way for a `Tool` to reach pins or a real server: proxies forward downstream calls **inside** `run`, leaving no "if ALLOW then forward" logic to get wrong. No board ⇒ no HAL: a `Tool` with `requires` is rejected at load time (`BoardCapabilityError`) and all tokens lack pins so `authorize` rejects pin commands (`token.py:148`).
   `run` is a Python function (`Tool(run=…)`) or, in `guard.toml`, a declarative `drive` — zero author code; all `pin`s in `drive` must be in `requires` (undeclared pins rejected by HAL like `@action`, `token.py:148`). Remote actuators are named `digital.out` pins (RFC-0018 §3a): `requires = ["digital.out:porch_light"]` follows the same `_admit` path.
3. **Gates resolve at load time, not merely validating schema.** `Guard.load` calls `register_gate` (`gate.py:170`) for each `Tool` — full resolution (invariant `CHANGELOG.md` §3.3 #1); unresolvable gate ⇒ fail to load; gate missing at runtime ⇒ `BLOCK gate_not_found` (`gate.py:206`). No fail-open switch.
4. **`source` and `facts`.** Caller **does not** specify `source`: host program requests `guard.dispatcher(id)`; Guard registers `id` (pattern `[a-z][a-z0-9_]{0,31}`, duplicate ⇒ error, RFC-0017 §3a, §3b) and constructs `ToolCall` with `source = "bridge:<id>"` internally. No path to default `"test"` (`tools.py:51`; F9 in RFC-0015) except `Guard(..., testing=True)`.
   `neuroedge proxy mcp|http` (core) preserves frontend client source (`mcp`, `mcp:<label>`) via an internal private path: question RFC-0017 §9.2, settled on Guard's side here (§9.9). `facts` set via `set_fact` are operator-trusted context like `c.facts`; ignored for criteria with `external_source` (RFC-0014 §3c). Bridges **cannot** touch `facts` (§3c).
5. **Serialization.** Because one Guard serves multiple bridges, `dispatch` across all `Dispatcher`s runs under an `asyncio` lock. The root fix — passing `call_source` per call rather than via `conversation.facts` — is TSK-I2c-10 (RFC-0017 modifies precisely this injection point, `tools.py:350`); the lock can then be removed.
6. **Traces and replay.** `guard.trace()` = `EventLog.to_trace()` (`trace_sink.py:91`) + `validate_trace`; `metadata` carries `target`, `board_id`, `agent_version` and open keys from §3d, §3f (`trace.v1.json` has `metadata.additionalProperties: true` ⇒ schema unchanged); each plugin also emits a `plugin_loaded` event at load time (§3d item 4).
   `TracePlayer` today requires `agent.toml` (`testing/player.py:588`): TSK-I2c-07 adds `TracePlayer(trace, guard="guard.toml")` using the `Tool` table. Question §9.3.
7. **One Guard per process.** In-memory token ledger bound to `PROCESS_INSTANCE_ID` (`token.py:37`); on `linux`, watchdog process releases pins when runtime dies or hangs, as with `SimSession` (`threat_model.md` §2).

**Guard deliberately does not do:** no sandboxing or network blocking — it guards the path through it, not preventing anyone from calling targets directly (§5, risk 3) · no `agent.toml`, mandatory `@action`, command grammar, `SystemOne`/`SystemTwo` models, voice, UI, or MCP server (the `proxy` commands in TSK-I2c-14, -15 build atop Guard) ·
no fail-open switch; only gates loaded from files or URIs, rejecting hand-constructed `ResolvedGate`s · no human confirmation path (`Conversation.confirm` requires on-device human, `tool_calling.md` §6): `on_block: ask` on Guard appears as a block with the question in `outcome.content` · no defense against same-process adversaries (`threat_model.md` §3) · no signing, no distribution.

### 3c. `neuroedge.sdk` — Six Extension Point Kinds and Structural Invariants

Each kind is an entry point group. **Code** kinds (bridge, fact source, actuator, exporter) have `typing.Protocol`s in `neuroedge.sdk`; **data** kinds (board, template) **have no Protocol** — not a single line of author code runs when using them.

| Entry point group | SDK | Plugin receives | Plugin **never** receives or does | Contract |
|:---|:---|:---|:---|:---|
| `neuroedge.bridges` | `Bridge`: `serve(dispatcher, context)`, `probe()` | `Dispatcher` — single method `dispatch(ToolRequest) -> Outcome`; core constructs `ToolCall` with `source = bridge:<entry point name>` internally (RFC-0017 §3b). `BridgeContext(id, config)` | HAL, `Guard`, `Conversation`, token ledger, `GateResult`, `facts` parameter, `source` (`ToolRequest` type contains none of these). `Outcome` is data (`status`, `content`), not carrying `ActionResult.value` | RFC-0016, RFC-0017 |
| `neuroedge.fact_sources` | `FactProducer`: `run(sink)`, `probe()` | `FactSink.push(facts: Mapping[str, int \| float], *, observed_age_ms: int = 0)`. Core measures `recv_ms`, assigns `seq` and `connection`, routes through **same receiver** as RFC-0014 (§3d layer 4, §3e, §3g; like `sim` virtual source, §3h) | `read_ms`, `age_ms`, `seq` (no parameter); strings, `bool`; names undeclared in `[external.sources.<id>.facts.*]`; criteria without `external_source`; querying engine back. `run` ending or failing ⇒ core drops all facts from source (RFC-0014 §3g, §3i) | RFC-0014, RFC-0016 |
| `neuroedge.actuators` | Protocol `Actuator` — signature in RFC-0018 §3c (`apply`, `safe_off`, `read_state`, `probe`, `safe_off_level`, `readback`, `tolerance_ms`, `command_timeout_ms`, `max_lease_ms`; factory `module:factory(config) -> Actuator`, no I/O on construction); re-exported by `neuroedge.sdk`, pinned by test | Core constructs plugin from declaration `[actuators.<name>] plugin = …`; only HAL retains reference and calls it, `apply` only **after** `_admit` (`hal/__init__.py:231`). `safe_off` follows safety-return path (`_auto_off` `:215`, `close()`), bypassing envelope and token (`threat_model.md` §1) | Commands bypassing token and envelope; receiving HAL, token ledger, or envelope; being called by anyone outside HAL. Auto-off levels L0–L3, "no auto-off" forbidden for non-reversible, communication loss: RFC-0018 | RFC-0016, RFC-0018 |
| `neuroedge.boards` | *data*: entry point value is `<package>:<directory>` | Directory of `<id>.toml` files per `board.v1`, read via `Distribution.locate_file` **without importing package**, through `validate_board_document` (`board.py:666`) like any file | Tier, `mirrors` (`board.py:382`), reference board status; colliding with reference board or in-tree board ids (§3f) | RFC-0002, RFC-0016 |
| `neuroedge.templates` | *data* | Directory of `*.tmpl` files containing only `{{name}}` (`templates/__init__.py:39`); `scaffold` performs only `write_text` (`:123`) | Running code on install or `new`; network access; writing outside project directory; overwriting existing files; gate colliding with standard or locked gate URIs | RFC-0016 |
| `neuroedge.exporters` | `Exporter`: `export(events)` | Deep copy of **already-anonymized** events as in trace, via bounded queue, off the decision path; isolated failure (precedent `_call_hook`, `gate.py:440`: "a hook can never change a verdict") | References to session, `Guard`, or HAL; modifying verdicts; raw un-anonymized text; delaying decisions | RFC-0016 |

- **Shape.** Entry point value for code kinds is `module:factory`, called once with `config` (a `Mapping`) and returning an object conforming to Protocol; loader verifies signature via `inspect.signature`, not merely `isinstance`. Code kind entry point names match `^[a-z][a-z0-9_]{0,31}$` (id pattern of RFC-0017 §3a, matching `source_id` of RFC-0014 §3c); data kinds match template `NAME`
  (`templates/__init__.py:40`).
- **`Dispatcher`** constructed by core, one per bridge, bound to locked id; routes to `dispatch()` path (`tools.py:327`) of `Guard` or a session (`neuroedge bridge run <id> --guard|--agent`): same path as `mcp serve` (`python_api.md` §4). PRD FR-EXT-03 states `dispatch(ToolCall)`; here parameter is `ToolRequest` =
  `ToolCall` without `source` (RFC-0015 §3a `request`). RFC-0017 §3b.3 allows API to accept `ToolCall` then reconstruct; choosing `ToolRequest` makes "bridge setting `source` different from channel" inexpressible at the type level.
- **`probe()`** is in-memory ingress through real plugin code path, allowing compliance suite (§3g) to inject scenarios (for actuators, `probe()` returns `DeviceDouble`, RFC-0018 §3c) — a call, an observation captured `D` ms prior, broken connection, communication loss — without real ecosystem protocols. Missing `probe()` ⇒ dynamic checks report `unverifiable`, no badge.

### 3d. Activation, Trust, Provenance

1. **Import-free discovery.** `neuroedge plugin list` reads `importlib.metadata.entry_points(group=…)`: name, package, version — **imports no** package (verified, §2).
2. **Code kinds load only when explicitly enabled.** `[plugins] enable = ["neuroedge-muse", "neuroedge-ros2==0.4.1"]` in `agent.toml` or `guard.toml`: **distribution** name (PEP 503 normalized), optional version pin. Installing via `pip` enables nothing; transitive dependencies carrying entry points enable nothing. **No CLI flag enables plugins into a session**
   (precedent RFC-0014 §9 question 9): enablement lives in committed files; only `conformance <distribution>` (§3g) loads the specified distribution, exclusively for verification. Plugin configuration at `[plugins.config.<entry point name>]`, same secret rules as `[external]` (only `*_env` environment variable names, reusing `SECRET`, `ENV_NAME` from `common.py:40`, `:38`). Referencing a plugin by name elsewhere (`plugin = "home_assistant"` in `[actuators.<name>]` of RFC-0018, `plugin = …` in `[external.sources.<id>]`) only looks up within **enabled** distributions; absent name ⇒ `NE3002`.
   **Data** kinds do not need an allowlist: no code runs; typing a reference `pkg:<distribution>:<name>` on the command line (§3f) is explicit action.
3. **Failure ⇒ fail to start, never silent skip.** Not installed; import failure; factory raises; object violates Protocol or signature; incompatible `sdk_requires` (§3e); version pin mismatch; two enabled distributions supplying the same entry point name in a group (RFC-0017 §3b.2: duplicate bridge id) ⇒ `AgentManifestError` (`NE3002`, 3-part message, exit code 1)
   and **no gate evaluation runs**: all plugins resolve before the first evaluation. Precedent: `load_adapter` and `call_adapter` also raise `NE3002` (`common.py:324`, `:359`). Unlike unavailable external MCP servers which are skipped (`threat_model.md` §2b): there only tools are omitted; plugins modify what reaches gates or HAL.
4. **Provenance.** Every enabled plugin and used out-of-package asset prints to stderr at startup, is recorded in `metadata.plugins` of all traces, and emits a `plugin_loaded` event (name added to `tool_calling.md` §7 upon implementation; binds `bridge:<id>` in `tool_call` to code, RFC-0017 §3b): `{kind, name, distribution, version, files_sha256}`. `files_sha256` hashes **on-disk bytes** of `dist.files` belonging to entry point package (not taken from `RECORD`: mutable itself).
   Editable installs (`direct_url.json`) omit source files ⇒ missing `files_sha256`, `editable: true`; `plugin doctor` warns and badge is denied (§3g).
5. **In-process plugins are operator-trusted code.** Same standing as `python:` adapter and `@action` body; `threat_model.md` §3 remains out of scope. This RFC **does not** claim defense against malicious plugins: no sandbox, plugins can still `import gpiod` or open `/dev/gpiochip`. SDK provides **structural** guarantees (no handles in API), compliance suite catches inadvertent and lazy mistakes, provenance makes choices auditable.
   Plugin signing: TSK-I2c-18 and I10, not here. `plugin install` (TSK-I2c-18) should only accept pre-built wheels (`--only-binary :all:`) to avoid running author build scripts — behavior unverified.
6. **`neuroedge plugin doctor [--config=]`** loads the enabled set under these rules and prints each check it **cannot** verify ("cannot verify: …", never a plain "OK"); for proxies, "target still reachable without going through proxy" is supplied by TSK-I2c-14 (§5, risk 3).

### 3e. Stability of `neuroedge.sdk` and Relationship with `__all__`

- **Dedicated version:** `neuroedge.sdk.SDK_VERSION = (1, 0)`, independent of `__version__` (`__init__.py:9`, `0.1.0`). Plugin declares `sdk_requires = (1, 0)`: compatible ⇔ same MAJOR and installed MINOR ≥ required MINOR. Pure integer tuple, requiring no `packaging` dependency in core. Loader imports module **after** operator enables it, reads `sdk_requires`, then calls factory.
- **Stricter than package `0.x` (D7).** Full SemVer from SDK 1.0, **not** following "MINOR acts as MAJOR" interpretation (`python_api.md` §3): only MAJOR releases remove, rename, change signatures, or alter documented behavior. Deprecation: marked in MINOR, supported for at least two SDK MINOR releases (§5 of `python_api.md` requires one; §9.4).
  Surface pinned by tests just as `test_public_api.py` pins `__all__` (§7). Core underneath `0.x` changes freely; all SDK-to-core touchpoints reside in a bridge module, so core changes do not break SDK.
- **Safety exception, stated explicitly:** changes closing a bypass around gates are permitted in MINOR/PATCH of SDK even if existing plugins depend on them, documented in `CHANGELOG.md` (`python_api.md` §3 first paragraph, §5 item 4; `CHANGELOG.md` §3.3 #2). New compliance checks added in MINOR only if closing a safety bypass; otherwise in MAJOR.
- **Public by location.** `python_api.md` §1 adds exactly two path-promised modules: `neuroedge.sdk` (commitment above) and `neuroedge.guard` (same level as `__all__`, §9.1). Each module has its own `__all__`. `neuroedge.__all__` **remains unchanged** (§9.2). SDK re-exports no names from `neuroedge.__all__` and contains no HAL names; bridge, fact source, and exporter plugins
  may only import `neuroedge.sdk` (compliance check, §3g).
- **Licensing (D8).** `neuroedge.sdk` and `neuroedge.guard` reside in PolyForm NC package (Q-45); plugins only *import* them when running alongside core; plugin licensing belongs to its author (`LICENSING.md` adds clause, TSK-I2c-06). Plugin compliance corpus lives in `fixtures/compliance/<group>/` (§3g) — part of existing Apache-2.0 tier of `fixtures/compliance/`.

### 3f. Out-of-Package Assets

Single reference syntax for all three: **id/name** as today · **path** (contains `/` or `\`, or `.toml` suffix) · **`pkg:<distribution>:<name>`** (read via `Distribution.locate_file`, no import).

| Asset | Rules |
|:---|:---|
| **Board** `--board <reference>` | A single `resolve_board(ref)` function alongside `load_board` (`board.py:733`) replaces all calls to `load_board_by_id(board_id)` in `engine/compiler.py:1659`, `sim/session.py:897`, `testing/player.py:611`, `cli/main.py`. Out-of-tree boards are **community boards**: reference board ⇔ id in `REFERENCE_BOARDS` (`board.py:98`) **and** `source` is an in-tree file. Out-of-tree profile borrowing id of reference board or `boards/` ⇒ `BoardCapabilityError` (NE3001). `verify` only traverses `REFERENCE_BOARDS` (`cli/main.py:1123`) and lacks `--board` (`test_cli_contract.py`), so community boards **never** enter tier 1 equivalence. Tier derived from **target** per `TARGET_TIERS` (RFC-0002 §3b; no code yet, TSK-I2c-05), not profile. All commands accepting `--board` (`build`, `run`, `mcp serve`, `record`, `replay`) and `board validate <path>` print label **"community, self-attested"** on first line; traces carry `metadata.board_origin = "community"` and `metadata.board_digest` (canonical JSON sha256 of board document). `replay` with community board requires `--board` and matches digest: mismatch or missing ⇒ `ReplayError` (NE4003), aligned with RFC-0008. Safety: `board validate` already rejects actuator pins without envelopes (`_check_actuator_envelopes`, `board.py:536`) and unknown capability keys (`:392`); **numbers** in envelope are board author's word; `board validate` prints envelope table for operator review |
| **Template** `--template <reference>` | Adds format `git+<URL>@<sha>` (full 40-hex sha; branches and tags rejected as unpinned; no hooks, no submodules; specific `git` command in TSK-I2c-08). Layout matches `templates/<name>/`; rejects symlinks, absolute paths, `..`; never overwrites existing files; only `write_text` — **zero code execution**. Prints provenance (path or sha, or distribution + version) to stderr |
| **Gate registry roots** | `GateRegistry(root)` (`gate_resolver.py:110`) accepts one or more roots; `--registry\|-r` repeatable (`gate lint`, `gate resolve`, `build`, …) and `[registry] roots` in `guard.toml`; each root is path or `pkg:<distribution>:<directory>`. In-tree `gates/` is always searched. **A URI existing in multiple roots ⇒ `GateNotFoundError` (NE2001) "non-unique"**, unless both files are byte-for-byte identical — no "first root wins", so package gates cannot shadow in-tree `neuroedge://gates/hospitality/…`. Resolution remains pure (`CHANGELOG.md` §3.3 #4). Pinning `extends` via digest and gates from git/OCI: TSK-S3-21, separate RFC |

### 3g. Type-Specific Compliance Test Suite

`neuroedge conformance <distribution> [--kind=] [--json]`: loads **only** that distribution (typing name is explicit activation) and executes checks for all its NeuroEdge entry points. Outcome per check: `pass` · `fail` · `unverifiable` (missing `probe()`) · `self_attested` (hardware claims of boards only). Exits `0` when no `fail`
or `unverifiable`; `1` if any; `2` for unimplemented kind (`CHANGELOG.md` §2.3). Distribution with zero NeuroEdge entry points ⇒ `1`, not `0` ("scanning 0 is never a pass", RFC-0013 §3f). Machine-readable JSON report: distribution, version, `files_sha256`, `sdk`, core version, harness version, list of (entry point, check, outcome,
details) — specified in `docs/spec/extension_sdk.md`, **not yet** in `schemas/` (freeze when users exist, same rationale as Q-65 question 5). Badge (TSK-I2c-18) awarded only when all checks `pass` (boards: `self_attested` on hardware claims), non-editable, valid `sdk_requires`; badge **does not** imply plugin is safe (§5, risk 4).

| Kind | Check (`<kind>.<name>`) |
|:---|:---|
| Common | `plugin.loads` (factory, Protocol, signature) · `plugin.sdk_range` · `plugin.name_pattern` · `plugin.not_editable` (badge only) |
| `bridge` | `imports_only_sdk` (static AST scan: from `neuroedge` only `neuroedge.sdk`; blocks `gpiod` and similar — list in spec, static heuristic so bypassable) · `block_is_not_success` (runs corpus `fixtures/tool_calls/` via `probe()`: external caller observes success only when `status = ALLOW`) · `source_not_claimable` (call carrying `call_source` in arguments ⇒ `REJECTED`, recorded source remains `bridge:<id>`) · `one_call_one_dispatch` (one incoming call ⇒ exactly one `dispatch`, no trying alternative tools on block, no raw commands like `system.run`) · `core_down_is_failure` (closing Guard or `dispatch` raising ⇒ timed failure, no local execution, **no re-queueing to run** when core recovers) |
| `fact_source` | `numbers_only` (all pushed values are `int`/`float`, no `bool`) · `age_from_capture` (simulated observation captured `D` ms prior ⇒ `observed_age_ms ≥ D − 10`; RFC-0014 §5 risk 1) · `drops_on_disconnect` (probe disconnects source ⇒ `run` terminates, no re-pushing stale values with new age) · `declared_names_only` · `rate_limit` (≤ 100 `push`/s, RFC-0014 §9 question 10) |
| `actuator` | Governed by RFC-0018 §3e: `actuator.level_proven` (L0–L3 vectors on `DeviceDouble` from `probe()`, one counter-example per vector) · `off_is_idempotent` · `off_is_unconditional` · `builds_without_io` · `classifies_errors` · `receives_no_handles`. This RFC merely connects them into `neuroedge conformance` and reports |
| `board` | `validates` (`board validate`, including envelopes) · `not_reference` (id not in `REFERENCE_BOARDS`, `SIM_MIRRORS`, or `boards/`) · `no_tier_or_mirror_claim` · `target_known` (RFC-0002) · `hardware_claims` ⇒ always `self_attested` |
| `template` | `new_works` (`new` into temp dir) · `lint_clean` (`gate lint`) · `own_tests_green` (≥ 1 ALLOW case and 1 BLOCK case, FR-DX-08) · `no_code_at_install` (measured via `sys.addaudithook`, PEP 578, in subprocess: no `subprocess`, network, writes outside temp dir — **feasibility unverified**, initial step of TSK-I2c-12 is spike) · `no_gate_shadow` |
| `exporter` | `copies_only` (traces and verdicts of session identical with and without exporter) · `error_isolated` (exporter raising or hanging ⇒ verdict unchanged) · `off_decision_path` (decision latency does not increase) · `anonymised_only` |

Each check has a counter-example case in `fixtures/compliance/<group>/{valid,invalid}/` (`bridges`, `fact_sources`, `boards`, `templates`, `exporters`; `actuators` per RFC-0018 §3e) with `expected_results.yaml`, bidirectionally closed (`CONTRIBUTING.md` §3; FR-EXT-04). Corpus packages into wheel so `conformance` runs from installed package.

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | Yes. No schema changes. `agent.toml` without `[plugins]` runs as before; `--board <id>`, `--template <name>`, single `--registry` run as before |
| Do currently invalid files become valid? | Yes, narrow: `--board ./x.toml` (currently errors "no profile"), `--template <path>`, multiple `--registry`. Additive, not tightening |
| Does it require bumping schema version? | No. `trace.v1`: `metadata` open (`metadata.plugins`, `board_origin`, `board_digest`); existing traces remain valid. `board.v1`, `gate.v1`: unchanged |
| Gate hashes / signatures, `digests.lock`, three canonical traces, `NETR`, tool call corpus expectations | Unchanged; adds corpus `fixtures/compliance/<group>/` |
| Gate resolution semantics | Merge and inheritance **unchanged**; file discovery location changes (single root → multiple roots) and adds rejection when URI is non-unique. Because `gate_resolver.py` is in `CONTRIBUTING.md` §3, this RFC is where it is approved |
| Python API (`python_api.md`) | MINOR: adds two public modules by location (§1, §2); `neuroedge.__all__` unchanged, `test_public_api.py` unchanged; adds `tests/test_sdk_api.py` |
| CLI (`python_api.md` §6, `test_cli_contract.py`) | MINOR: adds `plugin list`, `plugin doctor` (`--config=`, `--json`), `conformance` (`<distribution> --json --kind=`), `bridge run` (`<id> --agent\|-a= --guard= --registry\|-r=*`); `--registry\|-r=` becomes repeatable (`=*`; all previous calls remain valid); `--board`, `--template` still take one value. Snapshot and §6 updated in same PR |
| Architecture | Three new units `guard`, `sdk`, `plugins` (loader): edges into `tests/test_architecture_layers.py` (`ALLOWED`, `:19`) and `docs/architecture/vi/03-component-host-c4l3.md` in same change |
| Error codes | No new codes. `AgentManifestError` (NE3002) broadens *Cause*: `[plugins]`, plugin load, SDK mismatch, `guard.toml`; `BoardCapabilityError` (NE3001): invalid board reference, borrowing reference board id; `GateNotFoundError` (NE2001): non-unique URI; `ReplayError` (NE4003): board digest mismatch |
| Packaging | No new dependencies (`importlib.metadata`, `pyproject.toml:36` unchanged). `scripts/wheel_smoke.sh` additionally runs `conformance` on a sample plugin installed from wheel |
| RFC-0014 | Unchanged text. Adds parallel `token_env`: source declares `plugin = "<entry point name>"` in `[external.sources.<id>]`; mutually exclusive keys; all bidirectional gate ↔ agent rules (§3c of RFC-0014) apply fully; `[external]` section does not require `socket` when no source uses sockets. Question §9.6 |

## 5. Safety Impact

**Gates do not become looser and no additional paths to pins are opened.** Verdict semantics, five inheritance principles, fail-closed default unchanged; Guard follows same `dispatch`, same token ledger and envelope (§3b item 1). New section for `threat_model.md` — "§2d. In scope: third-party plugins" (written upon implementation; §2c reserved for RFC-0014):

| Shortcut | Blocked by | Result |
|:---|:---|:---|
| Bridge self-declares `source` or `call_source` | `ToolRequest` has no `source` field; `call_source` in arguments is unknown parameter | `REJECTED`; recorded source remains `bridge:<id>` |
| Bridge touches HAL | API contains no handle; compliance check `imports_only_sdk` | No path in API; bypassing via direct import is risk 1 |
| Fact source self-declares age / supplies fact to criterion with undeclared source | `push` has no age parameter; `observed_age_ms` only adds (RFC-0014 §3f); criteria without `external_source` ignore fact | Fact dropped ⇒ `criterion_unavailable` ⇒ BLOCK |
| Actuator receives command bypassing HAL | Only HAL holds reference; command enabled via `_admit` | Denied; `safe_off` still runs without token |
| `pip install` auto-enables a plugin | Enablement list in committed file; import-free discovery; no CLI flag | Not loaded |
| Broken plugin, SDK mismatch, name collision silently ignored | Fails to start (§3d item 3) | `NE3002`, exit 1 |
| Out-of-tree board claims reference board identity; enters tier 1 equivalence | Borrowed id rejected; `verify` only traverses `REFERENCE_BOARDS` | `NE3001`; no tier 1 column |
| Gate package shadows in-tree standard gate | Non-unique URI rejected | `NE2001` |
| Template runs code / overwrites files | Only `write_text`, no overwriting | Rejected |
| Exporter alters verdict or causes latency | Deep copy, bounded queue, failure isolation | Verdict unchanged |

**Non-regressions (tests in §7):** A3 retains 0 bypasses when executed via Guard (re-run A3 test suite on Guard); safety-return commands never blocked (Q-62): plugin error, latency, or hang cannot impede `close()`, auto-off, `safe_off`; no fail-open switch; missing plugin ≠ missing control.

**Residual risks — stated plainly:**
1. **Malicious or buggy in-process plugin** (`import gpiod`, private threads, reading token ledger memory): `threat_model.md` §3, out of scope. Mitigated by explicit enablement, version pinning, `files_sha256` in trace, compliance static scan. If process dies, on `linux` pins still release (watchdog process, `threat_model.md` §2).
2. **Supply chain:** hijacked package or typosquatting. Version pinning and `files_sha256` catch **changes after review**, not initial install; signing is I10; editable installs lack hash.
3. **Bypassed proxy:** Guard only guards paths traversing it. If MCP server, Home Assistant, or device still listens directly, gate is mere ornament. **Proxy must be the single path**; `plugin doctor` prints warning or "cannot verify" (TSK-I2c-14 provides check), and documentation makes this clear — cannot be guaranteed by core.
4. **Compliance suite cannot prove absence:** static scan bypassable; dynamic tests trust `probe()` written by plugin itself. "NeuroEdge-gated" is proof of passing tests, not safety certification (PRD §14, Q-38).
5. **Bridge lying externally:** physical effect is governed by gate, but outside caller may believe "turned on" when core returned BLOCK. Test `block_is_not_success` catches accidental bugs, not deliberate deception.
6. **Community board declaring loose envelope:** envelope is secondary lock whose numbers are set by board author. Labels, printed tables, and `metadata.board_origin` make this visible, not self-correcting.
7. **`facts` set by host program via `set_fact`** are operator-trusted, like `c.facts` today.
8. **Gate not reading `call_source` accepts all sources**, including newly enabled `bridge:<id>` (RFC-0017 §5 risk 3). `guard init` generates gates explicitly enumerating sources; `plugin doctor` warns for each tool whose gate does not read `call_source` when bridges are enabled.

## 6. Alternatives Considered and Rejected

| Alternative | Rejection rationale |
|:---|:---|
| Out-of-process plugins via IPC (each plugin in separate process) | Stronger isolation, but requires second *command* protocol alongside RFC-0014 (facts only, unidirectional, numeric) and reopens "what on the socket constitutes command path"; adds latency to decision path and process lifecycle complexity. Not permanently rejected: `Dispatcher` is data-in/data-out so out-of-process wrapper can implement same Protocol; revisit when plugin signing lands (I10) |
| WASM sandboxing immediately | Maturity unassessed for Python plugins needing hardware access; adding runtime requires Q-11 approval. Deferred until real plugin needs it |
| Keep fork-and-PR (no core changes) | Violates Q-67: third parties must not wait on core team |
| Expand `provider = "python:…"` for everything | No discovery (`plugin list`), no versions, no structural invariants (factory receives anything, imports anything), no target for compliance suite, no auditable provenance (§1 item 3, §2). Retained strictly for model providers |
| Load all installed entry points | `pip install` becomes enablement; transitive dependency changes gate path. Violates RFC-0014 §9 question 9 precedent |
| Ignore broken plugin and continue running | Silently loses safety path component; violates `CHANGELOG.md` §3.3 #2 |
| `neuroedge.sdk` re-exporting `neuroedge.__all__` | Hands `SimHAL`, `LinuxHAL`, `digital`, `motion` to bridge (§1 item 3) and binds SDK commitment to `0.x` |
| Handing `Guard` or `Conversation` to bridge | Both hold HAL and token ledger (`conversation.py:84–92`) |
| Declaring tier or "reference" in board profile; counting community boards in `verify` via flag | Tier is core team's promise (RFC-0002 §3b, §6); 100% tier 1 `verify` only meaningful for core-committed boards |
| "First root wins" on multiple gate roots | Packages could shadow standard gates; replaced by rejecting non-unique URIs |
| Putting compliance report into `schemas/` immediately | Freezing before users exist turns every fix into `v2` (Q-65 question 5); leave in `docs/spec/extension_sdk.md` |
| Seventh entry point group for gate packages | Six kinds decided; `pkg:<distribution>:<directory>` is sufficient and executes zero code |

## 7. Verification Evidence

Tests below are **proposed names**, not existing until RFC is approved. Corpus follows bidirectional closure rule (`CONTRIBUTING.md` §3; add row for `fixtures/compliance/<group>/` in table there).

- [ ] **Guard** (`python/tests/test_guard.py`): `test_a_guard_gates_an_action_without_agent_toml_action_or_session` (criterion FR-EXT-01) · `test_a_guard_trace_validates_and_names_its_guard` · `test_the_a3_suite_holds_on_a_guard` (re-runs `test_no_path_reaches_a_pin_without_a_valid_token` and adjacent cases) · `test_a_guard_without_a_board_refuses_a_tool_that_requires_a_pin` · `test_a_declarative_drive_moves_a_pin_only_after_allow_and_through_token_and_envelope` · `test_a_guard_hands_out_a_dispatcher_only_for_a_unique_valid_id_and_test_is_unreachable` ·
  `test_a_guard_has_no_fail_open_switch` · `test_a_gate_that_does_not_resolve_stops_the_load` · `test_a_missing_gate_blocks_with_gate_not_found` · `test_the_same_facts_give_the_same_verdict_on_a_guard_and_a_session` · `test_two_concurrent_dispatches_never_share_a_call_source` (pins bug from §2) · `test_a_guard_trace_replays_to_the_same_verdicts` (§9.3)
- [ ] **SDK** (`tests/test_sdk_api.py`): `test_the_sdk_surface_is_pinned` (names, Protocol members, signatures) · `test_the_sdk_version_is_not_the_package_version` · `test_the_sdk_exports_no_hal_name_and_no_name_of_all` · `test_a_plugin_for_another_sdk_major_or_a_newer_minor_is_refused` · update `test_architecture_layers.py` for `guard`, `sdk`, `plugins`
- [ ] **Loader** (`tests/test_plugins.py`): `test_listing_plugins_imports_nothing` (package whose entry point raises on import still lists) · `test_an_installed_plugin_that_is_not_enabled_never_loads` · `test_a_plugin_that_fails_to_import_refuses_start_and_starts_nothing` · `test_an_sdk_mismatch_refuses_start` ·
  `test_a_factory_of_the_wrong_shape_refuses_start` · `test_two_enabled_distributions_with_one_entry_point_name_refuse_start` · `test_a_version_pin_that_does_not_match_refuses_start` · `test_provenance_is_printed_and_recorded_in_the_trace_metadata` · `test_an_editable_install_has_no_file_hash_and_doctor_warns` ·
  `test_no_cli_flag_enables_a_plugin` · `test_a_plugin_config_with_a_literal_secret_is_refused` · `test_board_and_template_plugins_load_without_importing_the_package` · `test_doctor_says_what_it_cannot_check`
- [ ] **Structural invariants**: `test_a_bridge_receives_a_dispatcher_and_nothing_else` · `test_the_dispatcher_stamps_the_source_and_a_request_cannot_carry_one` · `test_a_fact_source_cannot_state_read_ms_age_or_seq` · `test_a_fact_for_a_criterion_without_external_source_is_dropped` · `test_an_actuator_is_reachable_only_through_the_hal` ·
  `test_safe_off_needs_no_token_and_no_envelope` · `test_an_exporter_gets_copies_and_cannot_change_a_verdict` · `test_a_raising_exporter_leaves_the_verdict_alone` · `test_exporters_see_anonymised_events`
- [ ] **Assets** (`test_boards.py`, `test_templates.py`, `test_gate_registry.py`): `test_a_board_path_loads_and_is_labelled_community` · `test_an_out_of_tree_board_cannot_take_a_reference_board_id` · `test_verify_never_replays_a_community_board` · `test_the_trace_of_a_community_board_records_origin_and_digest` · `test_replay_refuses_a_board_whose_digest_changed_or_is_missing` ·
  `test_a_template_from_a_path_copies_files_and_runs_nothing` · `test_a_template_refuses_symlinks_dotdot_and_absolute_paths` · `test_a_git_template_needs_a_full_commit_sha` · `test_a_template_never_overwrites_a_file` · `test_a_uri_in_two_gate_roots_is_refused_unless_identical` · `test_a_third_party_root_cannot_shadow_a_shipped_gate` ·
  `test_the_shipped_gates_root_is_always_searched` · `test_one_registry_flag_behaves_as_before`
- [ ] **Compliance** (`tests/test_conformance.py`): `test_every_plugin_example_has_an_expectation_and_every_expectation_an_example` · `test_every_check_of_every_kind_catches_a_counter_example` · `test_a_distribution_with_no_neuroedge_entry_point_fails` · `test_conformance_exit_codes` · `test_the_report_names_sdk_core_and_file_hash` · `test_an_editable_install_is_refused_a_badge`
- [ ] **Contracts**: `test_cli_contract.py` (new lines in §4) · `scripts/wheel_smoke.sh` green on installed package · `neuroedge gate lint`, `neuroedge verify` green · `pytest -q` 0 failed, 0 skipped

## 8. Implementation Steps Upon Approval

- [x] **TSK-I2c-07** — `neuroedge.guard` (§3b), shared HAL constructor function, `dispatch` lock, replay path via `guard.toml`; `python_api.md` §1, §2; `test_architecture_layers.py`, `03-component-host-c4l3.md`
- [ ] **TSK-I2c-08** — `resolve_board`, `--template` path / `pkg:` / `git+URL@sha`, multiple `GateRegistry` roots and repeatable `--registry` (§3f); `board validate` alongside TSK-I2c-05 (RFC-0002)
- [ ] **TSK-I2c-11** — `neuroedge.sdk` (Protocol, `SDK_VERSION`), entry point loader, `[plugins]`, `plugin list`, `plugin doctor`, `bridge run`, provenance into `metadata.plugins` and `plugin_loaded` event; `threat_model.md` §2d; `plugin` key in `[external.sources.<id>]` alongside TSK-I2c-09
- [ ] **TSK-I2c-12** — type-specific checks (§3g), `fixtures/compliance/<group>/` (alongside actuator vectors of RFC-0018), `neuroedge conformance`, `docs/spec/extension_sdk.md`; spike `sys.addaudithook` first
- [ ] **TSK-I2c-13** — plugin templates for each kind and "write a plugin in 30 minutes" guide (can be generated via `--template` mechanism itself: decide in TSK)
- [ ] **TSK-I2c-18** — index and badges consuming report from §3g; `plugin install` accepts only pre-built wheels
- [ ] `python_api.md` §3 (SDK commitment), §6; `CONTRIBUTING.md` §3 (new corpus row); `LICENSING.md` (plugin clause, TSK-I2c-06); `docs/user/thuat-ngu.md` (plugin, bridge, SDK, community board); `neuroedge-prd.md` (FR-EXT-01 → 05, 09, NFR-SEC-10 ticked); `neuroedge-roadmap.md`; `docs/rfc/README.md` (RFC-0016 row); `CHANGELOG.md` `[Unreleased]`

## 9. Decisions for Open Questions (Q-68, 2026-10-04)

Q-67 settled eight decisions, leaving the following points open. Lead engineer **accepts the recommendations for all questions below**, under the highest-safety principle of Q-57; each recommendation is a decision (Q-68, 2026-10-04). This section is the decision record: if §3–§8 conflict with it, fix §3–§8.

1. **Stability level of `neuroedge.guard`.** Recommendation: same level as `__all__` (`0.x`, MINOR acts as MAJOR) — D7 specifies only `neuroedge.sdk`; revisit when package reaches `v1.0` (at which point `python_api.md` §3 takes full effect).
2. **Add `Guard` to `neuroedge.__all__`?** Recommendation: no; use `from neuroedge.guard import Guard`. Each name added to `__all__` is a decision (`python_api.md` §3); adding later is MINOR.
3. **Is Guard trace replay in scope for I2c?** Recommendation: yes, in TSK-I2c-07 — "core" includes replay (design notes §3), and without it `verify` and CI Actions cannot touch Guard traces. If schedule slips: split into task immediately following I2c; Guard traces still support `trace validate/show/view/export`.
4. **SDK deprecation window.** Recommendation: two SDK MINOR releases (§3e), counted by `SDK_VERSION`, not by calendar days.
5. **Permit file hash pinning in enable list** (`"neuroedge-muse==0.4.1#sha256=…"`). Recommendation: permit, optional, not mandatory; mandatory pinning arrives with plugin signing (I10).
6. **Minor adjustment to RFC-0014** (`plugin` key in `[external.sources.<id>]`, `socket` optional when no source uses sockets, §4). Recommendation: accepted — in-process fact sources (TSK-I2c-09) need declaration point without sockets; bidirectional gate ↔ agent rules remain unchanged.
7. **Split an Apache-2.0 `neuroedge-sdk` distribution containing only Protocols** so plugin authors do not depend on PolyForm NC package at build time. Recommendation: not yet; D8 settled licensing implications, and Protocols are tied to core. Revisit at Beta fork point (Q-59, `TODOS.md` #51).
8. **`git+URL@sha` for `--board` and `--registry` like templates.** Recommendation: not yet — gates and boards from git require digest pinning (TSK-S3-21) first; users fetch files themselves and supply paths.
9. **Two questions forwarded from RFC-0017** (§9.2: which source `Guard` and proxies assign; §9.5: does a bridge specify an allowed tool list). Recommendation: (a) programs using `Guard` declare an id and receive `bridge:<id>`, core proxy preserves frontend client source (§3b item 4); (b) **no** per-bridge tool list — gates are already the decision point via `call_source` or `call_channel` (RFC-0017 §3d), `guard init` generates gates enumerating sources, and `plugin doctor` warns about gates not reading them (§5, risk 8).
