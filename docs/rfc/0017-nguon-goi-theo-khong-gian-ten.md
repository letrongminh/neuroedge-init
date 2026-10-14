# RFC-0017: Namespaced Call Sources (`bridge:<id>`) and Client Identity

| | |
|:---|:---|
| **RFC Code** | 0017 |
| **Title** | `source` of `ToolCall` becomes a namespace: `bridge:<id>` assigned by core per loaded bridge, `mcp:<client>` for labeled network clients, and derived fact `call_channel` enabling a gate to express "all bridges" — TSK-I2c-03 (code: TSK-I2c-10) |
| **Affected contracts** | `schemas/tool-call.v1.json` *(relaxes `$defs/source` from 5-value `enum` to `anyOf` enum ∪ pattern, §3a)* · `call_source` contract in `docs/spec/tool_calling.md` §1, §5 and table in §2b of `docs/spec/threat_model.md` · `[mcp.clients]` section of `agent.toml` *(outside `schemas/`; checked at `neuroedge build` and agent load time, §3c)* · **does not** touch `gate.v1`, evaluation semantics, `trace.v1`, `board.v1`, `NETR` layout, `digests.lock`, three canonical traces (§4) |
| **Related PRD requirements** | FR-ACE-09, FR-MDL-10, FR-EXT-02, FR-EXT-03, NFR-SEC-09, NFR-SEC-10 |
| **Proposer** | — |
| **Date opened** | 2026-10-04 |
| **Status** | ✅ Approved (2026-10-04) — lead engineer signed off on PR #99; decisions for open questions in §9 (Q-68) |
| **Approvers** | **Lead Engineer — mandatory** (modifies `schemas/tool-call.v1.json`; opens an identity path into the safety gate; reverses a signed decision). **Product Owner** for open questions in §9 |

> **When an RFC is required:** `CONTRIBUTING.md` §3 — editing `schemas/*.json` (`tool-call.v1.json`). The `call_source` contract is also locked by `docs/spec/tool_calling.md` §5:
> *"adding a value to the source list … requires an RFC"*. Task: **TSK-I2c-03** (this RFC), code **TSK-I2c-10**. Foundational decision: `neuroedge-prd.md` §15
> **Q-67 D2** — expand `source` into a namespace. **This RFC reverses [RFC-0015](0015-hop-dong-cho-nguoi-tich-hop.md) §10 question 11** (*"Do not anticipate new `source`
> values (such as `mcp_network`) … add only when needed"*): the need has arrived and been decided. Aligned with RFC-0014 (external sources, logical identity), RFC-0016 (`Guard`, `Dispatcher`, plugin loader). All assertions about code verified against repository at `7a43d93`; unverified items explicitly marked "unverified".

## 1. Problem

`source` of a tool call is a closed set of five values, kept synchronized in three places: `SOURCES` (`python/neuroedge/actions/tools.py:42`), `ToolCall.__post_init__` raising `ToolCallError`
NE1004 on unknown values (`tools.py:56-62`), and the `enum` in `schemas/tool-call.v1.json:22-25`. A bridge (Muse, Home Assistant, xiaozhi — Q-67) is third-party code translating an external protocol into
a `ToolCall`. Today it faces two options, both wrong:

1. **Borrow an existing source** — `mcp` or, worse, `local_grammar`. The gate cannot distinguish Muse from Home Assistant from an MCP client, and a bridge declaring "I am `local_grammar`" is exactly what
   `tool_calling.md` §5 forbids. Values are assigned solely by the core.
2. **Wait for the core team to add a value for each product** — each value requiring an RFC, a `SOURCES` update, and a release. This is precisely what Q-67 set out to eliminate.

Network MCP clients suffer from the same gap: authenticated tokens carry mandatory `sub` and certificate bindings (`mcp_http.py:332-346`), but `build_app` constructs a single `build_server(session)` with source
`mcp` (`mcp_http.py:432-434`, `mcp_server.py:75-100`), so the identity never reaches `dispatch()`. `threat_model.md` §2b (section *"Trust boundaries of `mcp serve --http`"*) notes this exact limitation: *"All calls over the network, regardless of device, have `call_source = mcp`; the gate cannot specifically forbid a particular device or the network ingress alone …"*.

Verified by trial run: `ToolCall("light_on", source="bridge:muse")` raises `ToolCallError` NE1004, *"'bridge:muse' is not a tool-call source"* (same case category as `python/tests/test_public_api.py:178`).

## 2. Why the Current Mechanism Does Not Solve This — and the Premise of RFC-0015 §10 Question 11

RFC-0015 kept the closed set on the grounds that *"each value enters `NETR` as a `choice` index"* (§3a, §10 question 11). That premise was re-examined; it is only half true:

| Check | Result | Location |
|:---|:---|:---|
| What happens to a `choice` value **outside** a gate's `options`? | `BLOCK`, `criterion_unavailable`, `failed_criterion` is the criterion itself. Under `fail: open` it still yields `BLOCK` (`known_failure` reclassifies **present** facts). Verified by trial run: gate enumerating `bridge:muse`, `call_source = bridge:other` ⇒ `BLOCK criterion_unavailable`; `mqtt:x` ⇒ same result | `engine/decision_tree.py:260-261`, `:497-522` |
| Is the index in `NETR` a global index? | **No.** It is the index in `sorted(options)` **of that specific gate** (`_domain`); the only strings in the string table are that gate's `options`. The C walker treats `!in_domain` as `criterion_unavailable`; the truth table already has an "out-of-domain" row for all non-numeric nodes (`bool`, `level`, `choice`). A new source changes zero bytes of `NETR` until a gate **enumerates** it (at which point only that gate's digest changes, as with any gate edit) | `decision_tree.py:42-50`, `:440`; `binary_tree.py:33-36`, `:49` (`LAYOUT_VERSION = 2`); `ne_walker.c:413`; `targets/esp32s3/components/ne_agent/ne_agent.c:39` |
| Does `gate.v1` block an `option` like `bridge:muse`? | No: `items` is `string`, no `pattern`, no `maxLength`. YAML parses `bridge:muse` as a string. Verified by trial run: such a gate passes `resolve_gate_file`, `compile_tree`, `binary_tree.encode` | `schemas/gate.v1.json:52-58` |
| What is the real limit on enumerating sources in a gate? | At most **32** values per domain (`admitted_mask` is `u32`); exceeding it ⇒ `GateSchemaError` NE2002 at build time. One cannot enumerate "all bridges", and nobody knows bridge ids in advance when writing a gate | `binary_tree.py:57`, `:217` |
| Does the `ask` confirmation path preserve the source? | Yes: the question stores original `call_source` and `confirm()` evaluates again with it. Any new derived fact **must** survive this path, otherwise a "yes" answer always results in `BLOCK` | `actions/conversation.py:131-133`, `:193-196` |
| Does the trace constrain `source`? | No: `tool_call.source` and `gate_facts.call_source.value` are free-form strings in `events[].data` | `docs/spec/tool_calling.md` §7 (paragraph following event table); `schemas/trace.v1.json` has no `source` key |
| Does any locked gate change? | No: no gate enumerates new values | `digests.lock` |

Thus, the part of RFC-0015 that was correct is *"requires an RFC"* and *"changes gate `call_source` contract"*; the part that was incorrect is *"enters `NETR`"*: overhead in `NETR` is zero. The rule allowing `enum` relaxation without bumping `v1` already exists
(PRD §10.3, row "Tool call schema"; RFC-0015 §3f).

## 3. Proposed Changes

### 3a. Grammar of `source`

| Form | Family (`call_channel`) | Who assigns, from where | Today |
|:---|:---|:---|:---:|
| `local_grammar` | `local_grammar` | command grammar matching `commands.toml` (`sim/session.py:1447`) | yes |
| `system_one` | `system_one` | reserved; outside corpus and tests, **nowhere constructs** `ToolCall` with it | yes |
| `system_two` | `system_two` | in-process MCP connection `build_server(source="system_two")` (`mcp_host.py:207`), `parse_tool_calls` (`sim/session.py:1649`) | yes |
| `mcp` | `mcp` | `neuroedge mcp serve` via stdio; network clients **not yet** labeled (§3c) | yes |
| `mcp:<client>` | `mcp` | core, from verified token `sub` via `[mcp.clients]` table (§3c) | new |
| `bridge:<id>` | `bridge` | core, from locked id of loaded bridge (§3b) | new |
| `test` | `test` | CI | yes |

`<id>` matches `[a-z][a-z0-9_]{0,31}` — exact pattern of `source_id` in RFC-0014 §3c: lowercase letters, digits, underscores; no hyphens, no dots; maximum `source` string length is 39 characters. Families outside `bridge` and `mcp` ⇒
`ToolCallError` (NE1004) on construction. **Built-in set remains closed:** adding a family or built-in value still requires an RFC. Note for `TSK-N6-01` (`call_source = "trigger"`, task TSK-N6-01 in `roadmap/neuroedge-roadmap.md`): that task states
no RFC is needed because `SOURCES` *"does not live in `schemas/`"*; after RFC-0015 that is no longer true, `trigger` is a sixth built-in value and modifying enum ⇒ RFC (this RFC does not add it).

```json
// before — schemas/tool-call.v1.json:22-25
"source": { "description": "Where the call came from. Assigned by the runtime from the connection (tool_calling.md §5); never the caller's to state.",
            "enum": ["local_grammar", "system_one", "system_two", "mcp", "test"] }

// after — $defs/request unchanged: still lacks `source`, additionalProperties: false (lines 26-36)
"source": { "description": "Where the call came from. Assigned by the runtime — from the connection, a bridge's registration or the verified client — never the caller's to state (tool_calling.md §5). A built-in name, or `bridge:<id>` / `mcp:<client>`.",
            "type": "string",
            "anyOf": [ { "enum": ["local_grammar", "system_one", "system_two", "mcp", "test"] },
                       { "pattern": "^(bridge|mcp):[a-z][a-z0-9_]{0,31}$" } ] }
```

Verified with `jsonschema`: `bridge:muse`, `mcp:hub` are valid; `mcp_network`, `mqtt:muse`, `bridge:`, `bridge:neuroedge-muse`, `bridge:Muse`, `local_grammar:x`, and 33-character ids are invalid. **A pitfall encountered:** Python's `$` matches *before* a trailing `\n`, so `jsonschema` (Python) accepts `bridge:muse\n`, whereas ECMA 262 does not. Code **must** validate using `re.fullmatch`, not `re.search`; that case is tested in code, not placed in `fixtures/contracts/`.

Code (`actions/tools.py`): `SOURCES` retains five built-in values; adds `SOURCE_ID`, `valid_source()`, `source_channel()`; `ToolCall.__post_init__` and `testing/tool_corpus.py:138` use `valid_source`; NE1004 message lists
five names and two namespaces.

### 3b. Bridge: ID and Channel

API shape of bridges belongs to RFC-0016 (§3b: `Dispatcher.dispatch(ToolRequest)`; `Guard` registers id and constructs `ToolCall` internally); this RFC only locks down four source invariants:

1. **ID is the entry point name** in the bridge group, matching `[a-z][a-z0-9_]{0,31}` (package `neuroedge-muse` declares entry point `muse`). Non-matching ⇒ **fails to start**, 3-part error; loader error code provided by RFC-0016, this RFC adds no code.
2. **Duplicate ID ⇒ fails to start** (two packages sharing entry point name, even with different targets). No "last package wins" or "first package wins" rule: a bridge cannot usurp another bridge's identity via loading order.
3. **Source is assigned solely by core.** Bridge receives a `Dispatcher` hard-bound to its id at load time (RFC-0016 §3b); its `ToolRequest` is `tool-call.v1#/$defs/request` — **lacks a `source` field** to declare. Core constructs `ToolCall` with `source = "bridge:<id>"` internally, leaving no path to default `"test"` (`tools.py:51`). Messages from vendor cloud (even messages carrying a `"source"` field) are merely data for the bridge to translate; no path reaches source.
4. **`dispatch()` raises NE1004** (programming error, not a verdict — `errors.py:107-112`) for calls with `bridge:<id>` or `mcp:<client>` where id does not belong to session's registered id set; `Guard` (via loader) populates bridge ids, `[mcp.clients]` populates labels.
   Catches typos and out-of-`Dispatcher` code; does not defend against malicious same-process code (§5). Runner `testing/tool_corpus.py` acts as loader: registers ids it reads from case `call.source`.

**Concurrency.** Today `dispatch` temporarily sets `conversation.facts` and restores it (`tools.py:350-356`), so multiple concurrent callers on a single `Conversation` are unsafe — RFC-0016 §2 and §3b item 5 document the issue and leave `Guard` serialized under a lock until the root cause is resolved. That root cause is **not** resolved by this RFC: a separate fix (branch `fix/call-source-isolation`) handles `call_source` per call, and TSK-I2c-10 builds atop that fix; `call_channel` (§3d) is derived at that exact per-call point, introducing no shared state.

ID binds `tool_call` to plugin load events in RFC-0016 (package, version, file hash — NFR-SEC-10): reading traces reveals which code corresponds to `bridge:muse`.

### 3c. Network MCP Clients: `mcp:<client>`, Deliberate Labeling

**Decision (recommendation, §9 question 1): `mcp:<client>`, not a second fact `call_client`.** Labels are *logical* names assigned by the operator, not raw `sub` values.

```toml
[mcp.clients.hub]                        # logical label; gate writes `mcp:hub`
subjects = ["device-a", "device-b"]      # validated token `sub` — not keys, not secrets
```

- **Off by default, zero change:** absent `[mcp.clients]` ⇒ all MCP connections remain `mcp`; no gate changes behavior.
- **Table present:** `build_server` accepts source as a *function of the request*; `--http` port reads verified `AccessToken` from the request itself (`sub` — `mcp_http.py:332-359`), looks up table ⇒ `mcp:<label>`. `sub` not in table ⇒ `mcp` (client passed mTLS and token;
  simply unlabelled). `--http` port without verified principal ⇒ **does not dispatch**, does not fall back to `mcp` (raises 3-part contract error, not a `BLOCK` verdict). stdio lacks identity, always `mcp`.
- **Labels derive only from tokens:** `sub` has passed signature, `iss`, `aud`, `exp`, certificate binding (`tool_calling.md` §8.1) — not from parameters, headers, or request body. Clients sending `source` or label in requests are ignored / `REJECTED` as unknown parameters (§5).
- **`AgentManifestError` (NE3002) rules**, at build and load time: label matches `[a-z][a-z0-9_]{0,31}`; `subjects` is non-empty list of strings; one `sub` in two labels ⇒ error; unknown keys ⇒ error (`refuse_unknown`, like `[external]` of RFC-0014 §3c).
- **Impact on existing gates when operator adds table:** gates enumerating plain `mcp` will `BLOCK` labeled clients (`mcp:hub` outside `options` ⇒ `criterion_unavailable`) — tightening direction, never looser. Gate authors switch to `call_channel in [mcp]` ("all MCP clients") or enumerate labels.
- **Unverified:** `mcp` SDK 2.2.0 has `get_access_token()` (`mcp/server/auth/middleware/auth_context.py:13`) and `ServerRequestContext.request` (`mcp/server/context.py`), but whether a path reaches handler `on_call_tool` of `build_server`
  via Streamable HTTP is unverified. That is the first test of item (b) in §8; if no path exists, source must bind per MCP session instead of per request, or the client label portion is deferred (§9 question 1).

Why not `call_client`: (1) D2 chose namespacing within **one** `call_source`; (2) `allow_when` is a conjunction (AND) across criteria, so "grammar *or* hub" with two facts requires padding values present everywhere (`none`, `stdio`) — with a single string, `call_source: { in: [local_grammar, mcp:hub] }` works immediately;
(3) labeling places logical names in gates and deployment bindings in `agent.toml`, matching the `external_source` pattern of RFC-0014 §3c. Honest downside: `call_client` preserves absolute compatibility without opt-in flags; this approach requires intentional operator labeling.

### 3d. Gate: Exact String `call_source`, Family-Based `call_channel`

`gate.v1` **does not change** (§2). `call_source` remains a `choice` enumerated by the gate:

```yaml
evaluate:
  call_source:
    type: choice
    options: [local_grammar, mcp, mcp:hub, bridge:muse, test]
    instructions: "Source of tool call, set by dispatcher (Q-24)"
  call_channel:
    type: choice
    options: [local_grammar, system_one, system_two, mcp, bridge, test]
    instructions: "Family of call source, derived by dispatcher from call_source"
allow_when:
  call_source:  { in: [local_grammar, bridge:muse] }     # exact Muse; other bridge ⇒ BLOCK
# or, for "all enabled bridges":  call_channel: { in: [local_grammar, bridge] }
```

- **`call_channel` is a derived fact:** portion before first `:` in `call_source` (or entire string). Injected in **one place** — the exact point where `call_source` enters gate context for *each call* (today `Conversation._context`, `conversation.py:143-151`; after `fix/call-source-isolation`, its per-call injection point), from that call's `call_source`, *after* merging fact sources — so all paths
  contain it (`dispatch`, `ask` confirmation, nested `c.do()`, fallback `degrade` — all routed through `_do`) and no `c.facts`, `[sim.facts]`, or fact source can overwrite it. No `call_source` ⇒ no `call_channel` ⇒ `criterion_unavailable`.
- **Same rules as `call_source`:** add `call_channel` to `RUNTIME_CRITERIA` (`models/providers/config.py:121`, checked at `:320`) so `[system_one]` cannot delegate judgment to models; Studio what-if (`studio/api_agent.py:221-222`) derives it from default `call_source`.
- **Fail-closed, verified (§2):** values outside `options` ⇒ `BLOCK criterion_unavailable`, even under `fail: open`. All existing gates enumerating five sources ⇒ **all bridges `BLOCK` by default** until a gate explicitly names it or its family.
- **Why a family fact rather than a new operator:** `call_channel` allows gates to match "all bridges" without changing gate language, evaluation semantics (`constraints.py`), or C walker; its domain today has 6 values (7 when `trigger` from TSK-N6-01 enters), well below the 32 limit.

### 3e. Traces, Replay, Confirmation

- `tool_call.source` and `gate_facts.call_source.value` carry new strings; `gate_facts.call_channel` present when gate declares it. `trace.v1` unchanged; `tool_call` records remain valid per `tool-call.v1#/$defs/call` (RFC-0015 §3e).
- **Replay uses only recorded `gate_facts`** (`tool_calling.md` §7, paragraph following event table): no plugins loaded, no bridge presence required. Traces containing `bridge:muse` replay on machines without `neuroedge-muse` installed.
- **`ask` confirmation:** `HUMAN_SOURCES = ("local_grammar", "ui")` (`actions/confirmation.py:33`, checked at `:167`). `bridge:*` and `mcp:*` cannot answer on-device prompts — no code change, tests added. Q-26 holds (§9 question 3).

### 3f. Contracts, Documentation, Corpus, Firmware

| Item | Changes |
|:---|:---|
| `docs/spec/tool_calling.md` | §1 (`source` table: "one of five sources" ⇒ grammar in §3a); §5 rewritten (paragraph *"calls over the network are `mcp`, without dedicated source"* ⇒ intentional labeling; adds `call_channel`, §3d example); §9 states corpus covers families |
| `docs/spec/threat_model.md` | §2b: update *"No device distinction at gate"* (section *"Trust boundaries of `mcp serve --http`"*) — remains true for unlabeled devices; adds bridge row (§5) |
| `docs/spec/python_api.md` (error table and MCP section), `docs/user/thuat-ngu.md` (`call_source` row) | `ToolCall` accepts two new source formats; terminology `bridge:<id>`, `mcp:<client>`, `call_channel` |
| `fixtures/contracts/` | `tool-call/valid/`: `call_source_bridge.json`, `call_source_mcp_client.json`; `invalid/`: `call_source_unknown_family.json` (`mqtt:muse`), `call_source_bridge_without_an_id.json`, `call_source_bridge_id_with_a_hyphen.json`, `call_source_bridge_id_too_long.json`; rename `call_source_outside_the_five.json` (`mcp_network`) to `call_source_outside_the_grammar.json` and update entry in `expected_errors.yaml` (`keyword: enum` ⇒ `anyOf`; message `…is not valid under any of the given schemas`) |
| `fixtures/tool_calls/` | `valid/open_gate_from_a_bridge_degrades.yaml` (agent `driveway`, `source: bridge:muse`: `BLOCK criterion_unavailable`, `failed_criterion: call_source`, `degrade` triggers `porch_light_on` — mirror of `open_gate_mcp_degrades.yaml`); new minimal fixture agent `bridge-lamp` (gate declaring `call_source` exact `bridge:muse` and `call_channel`) with `ALLOW` case for `bridge:muse`, `BLOCK` for `bridge:other`, `ALLOW` by family; case `mcp:hub`. Does not touch locked gates in `digests.lock` |
| Firmware / `NETR` | **Unchanged** (§2). `LAYOUT_VERSION` 2, C walker, `ne_agent` regenerate as with any gate `options` edit. Note: adding an `option` alters `sorted(options)` ordering, shifting `build`-generated indices — hand-coded C with hardcoded indices is author error (index header explicitly documented as not for firmware use) |
| `CONTRIBUTING.md` §3 (`NETR` row) | Calls `NETR` "v1" while `binary_tree.py:49` is 2 — pre-existing discrepancy, out of scope; integrator decides whether to fix in this PR |

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | **Yes.** All existing `call`s, gates, agents, traces. Existing gates do not change meaning: new values outside their `options` ⇒ `BLOCK` |
| Do currently invalid files become valid? | Yes, exactly two forms: `source: bridge:<id>` and `mcp:<id>` in `tool-call.v1#/$defs/call`, and `ToolCall(…, source="bridge:x")` in code. `mcp_network` (RFC-0015 §10 question 11 example) **remains invalid**. *Older `neuroedge` versions reject documents carrying new sources* — fail-closed, not a breaking change |
| Does it require bumping schema version (`v1` → `v2`)? | **No.** Relaxing `enum`, not renaming/removing/tightening fields (PRD §10.3; RFC-0015 §3f) |
| Impact on issued gate hashes / signatures? | None |
| Impact on three canonical trace files? | None (`trace.v1` unchanged; no trace has new sources) |
| Does any gate in `digests.lock` change digest? | No gates change. Sample gates using new sources (agent `bridge-lamp`) added via regular PR |
| Must `NETR` layout or C walker change? | **No** — verified in §2 |
| Does any expected answer in tool call corpus change? | No expected answers change; **adds** cases (§3f). `fixtures/contracts/expected_errors.yaml`: one entry updates keyword (`enum` ⇒ `anyOf`) |
| Public Python API (`python_api.md`) | `ToolCall` accepts two additional source formats (additive, MINOR); `SOURCES` is not public and retains five values; `valid_source`, `source_channel` internal |
| Behavior of `mcp serve --http` | Unchanged until operator adds `[mcp.clients]` (§3c) |
| CLI | Unchanged |

## 5. Safety Impact

**Is there any avenue making gates looser? No.** A new source only passes a gate that actively names it or its family (`BLOCK` outside `options`, even under `fail: open`). Two pre-existing exceptions documented below: gates not reading `call_source`,
and operator-authored label tables.

| Shortcut | Blocked by | Result |
|:---|:---|:---|
| Vendor cloud message carries `"source": "local_grammar"` | Bridge translates to `request` (lacks `source`); channel assigns `bridge:<id>` (§3b.3) | Source is `bridge:<id>` |
| Bridge A claims its call is from bridge B | `ToolRequest` has no `source` (§3b.3); only core constructs `ToolCall`. Direct `ToolCall` construction possible only by malicious in-process code (risk 1) | Source is `bridge:A` |
| Two packages share entry point name to hijack identity | Duplicate ID ⇒ fails to start (§3b.2) | Does not run |
| Unregistered source (`bridge:typo`) | `dispatch()` (§3b.4) | NE1004, no call executed |
| Unknown family (`mqtt:x`) | `ToolCall`, schema | NE1004 / invalid; reaches gate via other means ⇒ `criterion_unavailable` |
| Network client claims to be `mcp:hub` | Labels derive only from verified `sub` (§3c); `source` is not a parameter | `REJECTED` like `caller_declares_call_source.yaml` |
| Bridge or network client answers `ask` question | `HUMAN_SOURCES` (`confirmation.py:167`) | `tool_confirm_rejected` |
| Agent code, `[sim.facts]`, fact sources, or models setting `call_channel` | Injected last, `RUNTIME_CRITERIA` (§3d) | Overwritten / rejected by `[system_one]` |

**Residual risks — stated plainly:**

1. **Plugins are operator-trusted in-process code** (NFR-SEC-10, `threat_model.md` §3). A hostile bridge can call `dispatch()` directly with the source of another *enabled* bridge. Checking registered ID sets guards against mistakes and external input; **not** a sandbox. Root of trust is operator enablement and trace provenance (RFC-0016).
2. **IDs are author-assigned names**, not proving authorship. A gate specifying `bridge:muse` trusts the bridge enabled by the operator under that name.
3. **Gates not reading `call_source` accept all sources**, including bridges — exactly as with `mcp` and `system_two` today (`test_the_same_call_from_any_source_meets_the_same_gate`). Non-reversible action gates should explicitly enumerate sources; generating them by default is handled by `guard init` (RFC-0016 §9.9, TSK-I2c-14).
4. **`BLOCK` on unfamiliar sources can block a bridge's own "stop" call** if maker's `stop` gate does not enumerate it. The safety side of HAL — auto-off, lease expiration, `hal.close()`, watchdog — is source-independent and bypasses gates (`threat_model.md` §1, sections on safety-direction commands and leased motion; Q-62), so Q-62 is not violated.
5. **Client labels are operator declarations:** mapping `sub` to a high-privilege label by mistake is a configuration error visible during `agent.toml` review. Network ingress limits (no instant revocation, no rate limiting — `tool_calling.md` §8.1 "Not yet implemented") remain unchanged.

`threat_model.md` §2b: line *"No device distinction at gate"* replaced with *"distinguished by label when operator sets labels; unlabeled devices remain `mcp`"*. Lead engineer sign-off required because this touches `schemas/tool-call.v1.json`, opens identity into gates, and reverses RFC-0015 §10 question 11.

## 6. Alternatives Considered and Rejected

| Alternative | Rejection rationale |
|:---|:---|
| Keep closed set; bridges use `mcp` | Gate cannot distinguish two bridges; Q-67 D2 decided otherwise |
| Bridge self-declares source string, core only validates prefix | Source stated by caller — exactly what `tool_calling.md` §5 forbids; ids become guessable/spoofable |
| Adding an `enum` value for each product (`muse`, `homeassistant`…) | Every product requires an RFC and a release: core team remains bottleneck |
| Prefix / wildcard operators in gates (`call_source: { prefix: "bridge:" }`, `bridge:*` in `options`) | Changes gate language and evaluation semantics (`CHOICE_OPERATORS`, `constraints.py`), C walker, and `NETR` (devices compare domain indices, not strings). `call_channel` provides same capability with zero changes |
| `source` as object `{family, id}` | Breaks `choice`, `NETR`, traces, and all gates; offers no benefit over prefixed strings |
| Second fact `call_client` instead of `mcp:<client>` | Absolute compatibility, but two criteria for one concept; AND conjunction requires padding values to express "A or B" (§3c). Close trade-off; rejected per D2. Question 1 in §9 remains open for Product Owner |
| Raw `mcp:<sub>`, or auto-deriving labels from `client_id` | Injects deployment device ids into signed/distributed gates; behavior fluctuates with claim shape; unbounded domain (exceeds 32 ceiling). Logical labels in `agent.toml` match `external_source` pattern |
| Auto-assigning `mcp:<label>` to every token with `client_id` | All gates enumerating plain `mcp` would immediately `BLOCK` all network clients on upgrade; RFC 9068 §2.2 lists `client_id` as mandatory claim so nearly all real tokens would trigger this |
| Unfamiliar families treated as `mcp` (fail-open) | Violates `CHANGELOG.md` §3.3 #2; unknown sources must `BLOCK` |
| ID as package name (`neuroedge-muse`) instead of entry point name | A package can carry multiple bridges; package names contain hyphens outside grammar; entry point is registration unit |
| Allowing bridges to answer `ask` confirmation on vendor user's behalf | Q-26; §9 question 3 |
| Modifying `NETR` to carry prefixes | Unnecessary (§2) |

## 7. Verification Evidence

Names below are **proposed** — not existing until RFC is approved; existing tests explicitly marked.

- [ ] **Valid and counter-example cases** (`fixtures/contracts/`, `fixtures/tool_calls/`; bidirectional closure rule, `CONTRIBUTING.md` §3): exact list in §3f
- [ ] **Grammar and schema** (`python/tests/test_contracts.py`, `test_tools.py`, `test_public_api.py`):
  - `test_the_tool_call_schema_and_the_dataclass_agree` *(existing, update: `anyOf` = `SOURCES` ∪ pattern)* · `test_the_source_pattern_of_the_schema_is_the_one_of_the_code`
  - `test_a_bridge_or_client_source_is_valid_and_a_made_up_family_is_not` (`bridge:muse`, `mcp:hub` ok; `mqtt:x`, `bridge:`, `bridge:Muse`, `bridge:a-b`, 33 characters, `bridge:muse:x`, `mcp_network` ⇒ NE1004) · `test_a_source_with_a_trailing_newline_is_refused`
  - `test_an_unknown_tool_call_source_is_an_ne_error_with_three_parts` *(existing; message updated)* · `test_every_known_reason_and_every_source_appears_in_a_valid_contract_example` *(existing, update: covers both namespaces)* · `test_the_corpus_of_tool_calls_covers_every_family`
- [ ] **Gate and engine** (`tests/test_tool_source_namespace.py`, new; engine in `test_decision_tree.py`):
  - `test_a_bridge_call_meets_the_gate_with_its_own_source` · `test_a_gate_that_lists_one_bridge_blocks_another` · `test_a_source_outside_a_gates_options_blocks_with_criterion_unavailable` · `test_a_source_outside_a_gates_options_blocks_even_under_fail_open`
  - `test_call_channel_is_the_family_of_call_source` · `test_call_channel_cannot_be_set_by_facts_sim_facts_or_a_fact_source` · `test_the_confirmation_path_keeps_both_source_facts` · `test_two_concurrent_dispatches_each_see_their_own_call_channel` · `test_system_one_may_not_judge_call_channel` · `test_a_model_cannot_claim_its_own_call_channel` (alongside `test_a_model_cannot_claim_its_own_call_source`)
  - `test_a_bridge_or_a_labelled_client_cannot_answer_an_ask_question` (add parameters to `test_only_a_person_on_the_device_may_answer`) · `test_a_replayed_trace_with_a_bridge_source_needs_no_plugin`
- [ ] **Bridge and registration** (alongside TSK-I2c-11/12; RFC-0016 bridge compliance suite reused):
  - `test_a_bridge_dispatcher_assigns_its_own_source_and_a_request_has_no_source_to_state` · `test_two_bridges_with_the_same_id_refuse_to_start` · `test_a_bridge_id_outside_the_grammar_is_refused_at_load` · `test_a_call_for_a_source_nobody_registered_is_refused_by_dispatch` · `test_a_bridge_cannot_dispatch_under_another_bridges_source`
- [ ] **Network clients** (`tests/test_mcp_http.py`, `test_compiler.py`; real mTLS like existing tests):
  - `test_without_a_clients_table_every_connection_is_plain_mcp` · `test_a_mapped_device_gets_its_label_as_the_source` · `test_an_unmapped_authenticated_device_is_plain_mcp` · `test_two_devices_with_different_labels_meet_different_verdicts`
  - `test_the_label_comes_from_the_verified_token_and_not_from_the_request` · `test_an_http_call_without_a_verified_principal_is_not_dispatched` · `test_stdio_stays_plain_mcp`
  - `test_a_clients_table_with_a_bad_label_a_shared_subject_or_an_unknown_key_is_refused` (`AgentManifestError` NE3002)
- [ ] **Firmware** (`tests/test_c_walker.py`, `test_decision_tree.py`): `test_the_c_walker_matches_the_host_engine_on_every_gate` *(existing, green)* · `test_a_gate_with_a_bridge_option_encodes_with_the_unchanged_layout` (`LAYOUT_VERSION == 2`, string `bridge:muse` sits in string table of that specific gate) · `test_a_source_domain_over_32_values_is_refused_at_build` (rationale for `call_channel`)
- [ ] `neuroedge gate lint`, `neuroedge verify` green; `pytest -q` 0 failed, 0 skipped; `scripts/wheel_smoke.sh` green (`schemas/` packaged into wheel); `ruff check .` and `ruff format --check .`

## 8. Implementation Steps Upon Approval

Two independent halves, executed in order: **(a)** bridge, grammar, and `call_channel` (independent of network port, alongside TSK-I2c-11); **(b)** network client labels (touches `mcp_http.py`, after token path test in §3c passes).

- [x] Update `schemas/tool-call.v1.json` (§3a); `fixtures/contracts/` and `expected_errors.yaml` (§3f)
- [x] **TSK-I2c-10 (a):** `actions/tools.py` (`SOURCE_ID`, `valid_source`, `source_channel`, `__post_init__`, check registered ID set in `dispatch`), `testing/tool_corpus.py:138`, `actions/conversation.py` (per-call injection point, registered ID set), `models/providers/config.py:121`, `studio/api_agent.py:221-222`; built atop `fix/call-source-isolation` fix (per-call `call_source`), not re-solving; once fix lands, `Guard` serialization lock (RFC-0016 §3b item 5) can be removed — that task belongs to RFC-0016, not this RFC; `Dispatcher` source assignment and duplicate ID rules reside with `Guard` and loader (RFC-0016, TSK-I2c-07/11)
- [ ] **TSK-I2c-10 (b):** `mcp_server.py::build_server` (source as function of request), `mcp_http.py::build_app`, `[mcp.clients]` table (parsing, NE3002 check, `neuroedge build`), SDK token path test
- [ ] Corpus: cases in §3f, agent `bridge-lamp`; add "client labels" row if required by `CONTRIBUTING.md` §3
- [ ] `docs/spec/tool_calling.md` §1/§5/§9; `docs/spec/threat_model.md` §2b; `docs/spec/python_api.md`; `docs/user/thuat-ngu.md`; `docs/architecture/{vi,en}/07-data-contracts.md` (new `agent.toml` block — exact placement unverified)
- [ ] `neuroedge-prd.md`: FR-ACE-09 (namespaced call sources), Appendix B row `ToolCallError` (prose "not in source set" ⇒ "violates source grammar"), assign `Q-N` to decisions in §9; `neuroedge-roadmap.md`: TSK-I2c-03/10 and note for `TSK-N6-01` (requires RFC, §3a)
- [ ] Do not touch `digests.lock`; `docs/rfc/README.md` (RFC-0017 row) and one `CHANGELOG.md` entry under `[Unreleased]`

## 9. Decisions for Open Questions (Q-68, 2026-10-04)

Lead Engineer **accepts recommendations for all questions below**, under the highest-safety principle of Q-57; each recommendation is a decision (Q-68, 2026-10-04). This section is the decision record: if §3–§8 conflict with it, fix §3–§8.

1. **Are network client identities in scope for this RFC, and formatted as `mcp:<client>` or `call_client`?** *Recommendation:* `mcp:<client>` with deliberate labeling (§3c), implemented following half (a). If SDK token path test fails or Product Owner requests absolute zero-opt-in compatibility, split §3c into a separate RFC and reserve only the grammar; bridge portion is independent.
2. **Sources assigned by `neuroedge.guard` and `neuroedge proxy mcp|http` — answered in RFC-0016 §9.9** (single source of truth). Summary: programs using `Guard` receive `bridge:<id>` following grammar and duplicate ID rules of this RFC; core proxies preserve frontend client source (`mcp` or `mcp:<label>`).
3. **May bridges forward vendor user's "yes" (confirming `ask`)?** *Recommendation:* **no** in this RFC; `bridge:*` ∉ `HUMAN_SOURCES` (Q-26). Human-authenticated confirmation path requires a dedicated RFC when a real bridge requires it (signal: test TSK-I2c-17).
4. **Does `neuroedge gate lint` warn about out-of-grammar `call_source` options (misspelled `bridge:muze`)?** Gates remain valid and fail-closed; warning only spares author troubleshooting. *Recommendation:* yes, warning only, verdict unaffected; if Lead Engineer views lint as part of "resolution semantics" (`gate_resolver.py`), defer.
5. **Does enabling a bridge include an allowed tool list — answered in RFC-0016 §9.9.** Summary: no; gates are already the decision point via `call_source` or `call_channel` (§3d). Risk 3 in §5 (gates not reading `call_source`) remains here; mitigations (`guard init`, `plugin doctor`) reside in RFC-0016.
