# Standalone safety core and Extension SDK — `neuroedge.guard`, `neuroedge.sdk`

**Status:** normative for implemented portions (TSK-I2c-07, TSK-I2c-14, TSK-I2c-16 core portion); remaining portions explicitly marked "not yet". Foundation: [RFC-0016](../rfc/0016-loi-tach-duoc-va-extension-sdk.md)
(§3b, §3c, §3d, §3e, §3g), [RFC-0017](../rfc/0017-nguon-goi-theo-khong-gian-ten.md) (`bridge:<id>` source), [RFC-0018](../rfc/0018-co-cau-chap-hanh-tu-xa.md) (remote actuators).
**Source code:** `python/neuroedge/guard.py`, `python/neuroedge/sdk/__init__.py`, `python/neuroedge/sim/hal_build.py`, `python/neuroedge/plugins/` (loader, `[actuators]` declaration, `conformance`), `python/neuroedge/hal/remote.py`.
**Pinned tests:** `python/tests/test_guard.py`, `python/tests/test_sdk_api.py`, `python/tests/test_plugins.py`, `python/tests/test_remote_actuator*.py`, `python/tests/test_conformance.py`.
This document is the **sole** definition of `guard.toml` syntax and `drive` grammar; other locations link here. Commitment levels of the two modules: `python_api.md` §1.

## 1. `neuroedge.guard`

Any program (MCP proxy, bridge, ROS node) gets gate → token → envelope → trace without needing `agent.toml`, `@action`, or `SimSession`.
Runnable example: [`examples/guard/`](../../examples/guard/) (`guard.toml` + `run.py`; `test_the_guard_example_runs_and_writes_a_valid_trace`).

```python
from neuroedge.guard import Guard
from neuroedge.sdk import ToolRequest

async with Guard.load("guard.toml") as guard:      # exit ⇒ release pins, like SimSession.close()
    bridge = guard.dispatcher("ros_node")           # register `bridge:ros_node`; cannot claim other sources
    guard.set_fact("badge_ok", True)                # host program gate context, like `c.facts`
    outcome = await bridge.dispatch(ToolRequest("lamp_on", {"seconds": 3}))
    outcome.status, outcome.content                 # "ALLOW" | "BLOCK" | "REJECTED"; `ToolResult.content()`
    trace = guard.trace()                           # validated trace.v1
```

- **Single path to pins.** `Guard` constructs `ActionContractEngine`, token ledger, HAL with board envelope (shared builder with `SimSession`: `sim/hal_build.py`), and an internal
  `Conversation` **with its own action registry** (not touching global `@action` `REGISTRY`), then invokes standard `dispatch()` (`tool_calling.md` §2).
  Each `Tool` is an `ActionSpec` declared via data; `threat_model.md` §1–§2b apply completely.
- **ALLOW is a verdict; if `Tool` has a body, it is a single execution under token.** Body is `run` (Python function, sync or async, accepting validated, default-filled arguments) **or**
  `drive` (§3), not both; lacking a body, ALLOW is verdict-only. Pins move only inside bodies, under single-use tokens and board envelopes; bodies cannot touch pins undeclared in `requires`.
- **Gate resolved at load time.** Each `Tool` has a gate (filepath or `neuroedge://…`) fully resolved (inheritance, full invariants `CHANGELOG.md` §3.3 #1) **before** constructing HAL; unresolvable gate
  ⇒ fails to load, no pins held. Gate vanishing at runtime ⇒ `BLOCK`, `gate_not_found`. No fail-open switch, rejects manually constructed `ResolvedGate`.
- **Source and ID.** Callers **do not** specify `source`: `guard.dispatcher(id)` (pattern `[a-z][a-z0-9_]{0,31}`) registers `bridge:<id>` via `Conversation.register_source` (RFC-0017 §3b); invalid grammar
  or duplicate ID ⇒ `ToolCallError` (NE1004). `ToolRequest` has no `source` field, and `Dispatcher.dispatch` rejects a `ToolCall`. Source `test` available only via `Guard(..., testing=True).testing_dispatcher()`.
  Gates read sources via `call_source` / `call_channel` (`tool_calling.md` §5).
- **Serialization.** All `Dispatcher.dispatch` calls on a `Guard` run under a **single** `asyncio.Lock`. Not because of sources: `call_source` belongs to individual calls (`Conversation.do_with`), so concurrent calls
  never see each other's sources (`test_two_concurrent_dispatches_never_share_a_call_source`). Rather for traces: two concurrent calls interleaving events could cause a post-verdict pin command from A to fall after request B, whereas replay reads traces
  as linear steps (`test_concurrent_dispatches_are_recorded_one_after_another_and_replay`). Consequence to note: a slow `run` body (network forwarding) holds other bridges waiting.
- **Trace and replay.** `guard.trace()` = `EventLog.to_trace()` + `validate_trace`; `metadata.agent_version = "guard:<name>@<neuroedge_version>"`, `board_id = "none"` when no board is specified.
  `TracePlayer(trace, guard="guard.toml")` replays traces using `Tool` tables (cannot provide both `agent=` and `guard=`): `test_a_guard_trace_replays_to_the_same_verdicts`.
  Python code `run` bodies do not reside in `guard.toml`, so replay executes `drive` bodies and verdicts-only for the remainder.
- **One Guard per process**, in-memory token ledger (RFC-0016 §3b item 7). No board ⇒ no HAL: `Tool` with `requires` rejected at load (`BoardCapabilityError`), and bodies calling `digital.out` rejected.
- **Intentionally omitted:** no sandboxing or network interception (guards the path passing through it, does not prevent direct target calls); no `agent.toml`, grammar, models, voice, UI, or MCP servers; no human confirmation path
  (`on_block: ask` surfaces as `BLOCK` with question in `outcome.content`); no protection against same-process hostile code (`threat_model.md` §3). `Guard` is not in `neuroedge.__all__`.

Constructor `Guard(tools, *, name, board, target, registry_root, base, events, testing, hal_options, source, actuators, plugins)`: `board` is a board ID (or `None`); `target` is `sim` or `linux`, defaulting by board
(`esp32s3` has no Python Guard — MCU uses `ne_gate` + `NETR`). Gates reside on individual `Tool` instances, so the function has no standalone `gates=` parameter from RFC-0016 §3b (example there); gate `fallback_action` is another `Tool`.
`actuators` are programmatic `ActuatorDeclaration` instances and `plugins` is a list of enabled distributions (like `[plugins] enable`): they undergo the **same** `check_actuators` as declared files (§7), before pins are held.

## 2. `neuroedge.sdk`

The portion of the Extension SDK needed by `guard` and actuator plugins:

| Name | Description |
|:---|:---|
| `ToolRequest(name, arguments={}, id="")` | `tool-call.v1#/$defs/request`: **no `source`**; immutable |
| `Outcome(status, content)` | Plain data: `status` and `ToolResult.content()` (valid per `tool-result.v1`), does not carry values returned by action bodies |
| `SDK_VERSION = (1, 0)` | Standalone `(MAJOR, MINOR)` tuple, distinct from package `__version__` |
| `Actuator` | Protocol for `neuroedge.actuators` plugins; signature matches RFC-0018 §3c (sole source), re-exported by SDK: `safe_off_level`, `readback`, `tolerance_ms`, `command_timeout_ms`, `max_lease_ms`, `apply(command)`, `safe_off()`, `read_state()`, `probe()`. Today the safe side is always `off`; *planned · Q-72, awaiting RFC:* symmetric `safe_state` (§7) |
| `Command(id, operation, duration_ms=None, lease_ms=None)` | Command delivered by HAL to plugin after authorization: `operation` is `"on"` or `"renew"`; `duration_ms` always present in L2, `lease_ms` in L3; represents **duration**, never timestamps. Unique `id` per command (device identifies duplicate commands, late renewals) |
| `DeviceDouble` | Protocol for device mock returned by `probe()`: `state()`, `cut_link()`, `heal_link()`, `advance(ms)` |
| `ActuatorError` and `NotSent`, `Rejected`, `Ambiguous`, `ReadFailed` | Plugin self-classifies transmission errors (definitely undelivered · explicitly rejected · unknown delivery) and read errors; not `NE…` error codes |

Its `__all__` is `["SDK_VERSION", "Actuator", "ActuatorError", "Ambiguous", "Command", "DeviceDouble", "NotSent", "Outcome", "ReadFailed", "Rejected", "ToolRequest"]`; no HAL names, no `Guard`, no `Conversation`, no names from `neuroedge.__all__` (`test_the_sdk_exports_no_hal_name_and_no_name_of_all`), importing only core `errors`.
Plugins declare `sdk_requires = (MAJOR, MINOR)` in entry point modules (§6). **Not yet implemented (TSK-I2c-11/12):** `Protocol` for bridges, fact sources, exporters; loader and conformance for those categories. Full stability commitment: RFC-0016 §3e.

## 3. `guard.toml`

Subset of `agent.toml`. Unknown keys, plaintext secret fields (`api_key`, `token`, …; environment variable names `*_env` only), and unimplemented features ⇒ `AgentManifestError` (NE3002), three-part,
**never silently ignored** — unimplemented features raise errors naming the task that will deliver them.

```toml
[guard]
name  = "door-proxy"              # mandatory; ⇒ metadata.agent_version = "guard:door-proxy@<version>"
board = "sim-default"             # id of a board in boards/; absent ⇒ no HAL, verdicts only

[registry]
roots = ["gates"]                 # directory (relative to guard.toml) for `neuroedge://`; multiple roots: TSK-I2c-08

[tools.lamp_on]                   # name: [a-z][a-z0-9_]{0,63}
gate     = "gates/lamp_on@1.0.0.yaml"          # file (relative to guard.toml) or neuroedge://…
requires = ["digital.out:porch_light"]         # only `digital.out:<pin>`; requires board; pin must exist on board
drive    = [{ pin = "porch_light", operation = "pulse", seconds_from = "seconds" }]

[tools.lamp_on.parameters.seconds]             # undeclared parameter ⇒ REJECTED
type    = "integer"               # string | integer | number | boolean
default = 5                       # optional, typed; default provided ⇒ optional parameter
```

| Table | Key | Notes |
|:---|:---|:---|
| `[guard]` | `name`, `board` | `board` as path or `pkg:…` ⇒ rejected, citing TSK-I2c-08 |
| `[registry]` | `roots` | more than one root ⇒ rejected, citing TSK-I2c-08 |
| `[tools.<name>]` | `gate`, `requires`, `drive`, `parameters` | |
| `[tools.<name>.parameters.<p>]` | `type`, `default`, `description`, `required` | value bounds belong to gate `arguments` (RFC-0005), not here. Lacking `default` and lacking `required = false` ⇒ mandatory parameter; `required = false` without `default` ⇒ optional parameter omitted from `run` if caller does not provide it |
| `[proxy.mcp]` | `command` or `url`, `env_from`, `headers_env`, `names` | read only by `proxy mcp` and `plugin doctor` (§4); ignored by `Guard` |
| `[proxy.http]` | `upstream`, `listen`, `id`, `headers_env`, `[[routes]]` (`method`, `path`, `tool`) | read only by `proxy http` and `plugin doctor` (§5); exactly one of `[proxy.mcp]` / `[proxy.http]` per file |
| `[plugins]` | `enable`, `config` | §6; only actuator category loadable, distributions carrying other categories ⇒ rejected, citing TSK-I2c-11 |
| `[actuators.<name>]` | `plugin`, `safe_off`, `reversible`, `envelope`, `config` | §7 (`safe_state` key not declared here: *planned · Q-72*, in `board.v1` only); same declaration and verification functions as `agent.toml`. Tools access it via `requires = ["digital.out:<name>"]`: "declared but unused" bidirectional rule verified against tool `requires` |
| `[external]` | — | rejected, citing TSK-I2c-09 |

### `drive` grammar

`drive` is a list of steps, executed sequentially within tool bodies, under token. Each step is a table:

| Key | Meaning |
|:---|:---|
| `pin` | pin name; **must** exist in `requires` (`digital.out:<pin>`) |
| `operation` | `on`, `off`, or `pulse` |
| `seconds_from` | for `pulse` only, **mandatory** there: name of declared parameter, type `integer` or `number`; pulse duration (seconds) taken from this parameter |

Guard builds steps into `digital.out(pin).on()`, `.off()`, or `.pulse(seconds=<param>)`. Out-of-bounds values are handled by gates (`argument_out_of_range`) and board envelopes.
Nothing else exists in `drive`: remote actuators are named `digital.out` pins (§7), so `{ pin = "garden_valve", operation = "pulse", … }` reaches them via the same path. For arbitrary bodies, use `Tool(run=…)` in Python.

## 4. `neuroedge proxy mcp` — an existing MCP server behind NeuroEdge (TSK-I2c-14, FR-EXT-06)

Three commands on a clean machine: `pip install 'neuroedge[mcp]'`, then `neuroedge guard init --mcp "<command or https://…>"`, then `neuroedge proxy mcp`
(`test_three_commands_put_a_server_behind_the_proxy`, via a real MCP client). All `tools/call` pass through `Guard` (gate → token → envelope → trace) and
are **forwarded to the upstream server strictly inside the tool's `run` body**, meaning after ALLOW: there is no "if ALLOW then forward" logic that could be written incorrectly.

### 4.1 `[proxy.mcp]` table

```toml
[proxy.mcp]
command  = ["python", "my_server.py"]       # stdio; OR  url = "https://ha.local/mcp"  (Streamable HTTP) — exactly one of the two
env_from = ["HA_TOKEN"]                      # (stdio) environment variable names passed to child process — NAMES only
headers_env = { Authorization = "HA_TOKEN" } # (url) header name → environment variable NAME; never values
[proxy.mcp.names]                            # guard tool name → upstream server tool name, when different
get_state = "get-state"                      # guard tool name is [a-z][a-z0-9_]{0,63}; MCP permits `-`, `.`, uppercase
```

Plaintext secret values are rejected (NE3002) and never echoed: keys named like secrets, `command` arguments resembling API keys, URLs containing credentials or query parameters named like secrets,
`headers_env` values that are not variable names. `http://` accepted only for `localhost`/`127.0.0.1`/`::1` (tokens never travel cleartext over networks) — unless `allow_lan_http` is enabled (§4.1a). Stated environment variables missing in shell ⇒ connection refused.

### 4.1a `allow_lan_http` — plain HTTP to devices on home network (and for `proxy http`, §5.1)

Real devices (Home Assistant `http://192.168.1.10:8123/api/mcp`, Tasmota, Shelly) often speak only plain HTTP on LAN. Key `allow_lan_http = true` in `[proxy.mcp]` (requires `url`) and `[proxy.http]` is an **intentional opt-in**, disabled by default (disabled ⇒ unchanged behavior: HTTP loopback only).
When enabled, plain HTTP is accepted solely for `host` matching:

- literal private/link-local/loopback IP: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `127.0.0.0/8`; IPv6 `fc00::/7`, `fe80::/10`, `::1`;
- or hostnames matching `*.local`, `*.lan`, `*.home.arpa` (possessing at least one label preceding suffix).

**All other hosts remain rejected even with flag enabled:** public names or addresses, CGNAT range `100.64.0.0/10` (intentionally rejected), IPv6 documentation/`fec0::/10`, IPv4-mapped IPv6 addresses, bare hostnames (`homeassistant`) — tokens never travel cleartext over the internet
(`test_any_other_host_stays_refused_even_with_the_flag`). Credentials in URLs remain rejected. `listen` in `proxy http` remains loopback only (flag does not touch frontend).
`guard init --mcp|--http … --allow-lan-http` writes key with comments; `plugin doctor` outputs **WARNING** when key is enabled: calls and tokens travel plain HTTP on LAN, allowing anyone eavesdropping on the home network to read and replay tokens.
If devices support HTTPS, use HTTPS; this flag represents the cost of devices lacking it.

Proxy tools do not manipulate pins (`requires`, `drive` rejected): they forward a call.

### 4.2 `guard init --mcp`

`neuroedge guard init --mcp <command|url> [--dir DIR] [--name NAME] [--env-from NAME]… [--header-env HEADER=VAR]…` connects as an MCP client, enumerates upstream tools, then writes `guard.toml` and a gate for each tool in `gates/`:

- **Generated gates block by default.** Gates declare `call_source` with explicit `options` (source of client in front of proxy is `mcp`) **and** an unset criterion (`operator_approved`, `allow_when: operator_approved: true`),
  so tools yield `BLOCK` with `criterion_unavailable` until operators edit gates **intentionally**; each file header explains how to unblock (`test_a_generated_gate_blocks_until_the_operator_opens_it`).
- **Parameters.** Scalar attributes of `inputSchema` (`string`, `integer`, `number`, `boolean`; including `Optional[…]`) map to `[tools.X.parameters]`; default values write `default`, optional without default writes `required = false`.
  Tools possessing **mandatory non-scalar parameters are not exposed**: recorded as commented-out blocks with rationale and printed to stderr (`test_a_tool_with_a_required_object_parameter_is_not_exposed`); optional non-scalar parameters are dropped with notes.
- Upstream tool names invalid for guard (`get-state`) are converted (`get_state`) and recorded in `[proxy.mcp.names]`. Arguments to `--mcp` matching existing files write absolute paths.
- **Never overwrites:** if any target file already exists ⇒ three-part error, writes nothing (`test_guard_init_never_overwrites_a_file`). Generated files undergo trial load (`Guard.load`, gate resolution) in temporary copies **before** writing, ensuring `guard init` never leaves unloadable configurations.

### 4.3 `proxy mcp`

`neuroedge proxy mcp [--config guard.toml] [--trace-out PATH]` serves **strictly over stdio** (`--http` is TSK-I2c-15, not yet implemented) exactly the tools in `guard.toml`, descriptions inherited from upstream. On startup it connects upstream and validates each guard tool:
tools must be present upstream (per `[proxy.mcp.names]`), declared parameters must match types, and all mandatory upstream parameters must be declared. **Missing tools, schema mismatches, or connection failures ⇒ fails to start** (exit code 1, three-part error), never "serving the remainder".

- **Source.** Calls retain frontend client source `mcp` via internal pathway `Guard._dispatch_front` (RFC-0016 §3b item 4): unreachable by any `Dispatcher`, so bridges remain strictly `bridge:<id>` (`test_a_bridge_cannot_obtain_the_front_source`).
- **Results.** ALLOW ⇒ verbatim upstream result. BLOCK ⇒ verdict (JSON, `isError` = false); REJECTED ⇒ verdict, `isError` = true — matching `mcp serve`.
- **Upstream failure after ALLOW** ⇒ error result (`status = ALLOW`, `isError` = true, "was not retried"); **never retried**, because call side-effects may have occurred (`test_an_upstream_error_after_allow_is_an_error_result_not_a_retry`).
- **Traces.** `--trace-out` writes `guard.trace()` on exit (including SIGTERM); `metadata.proxy = {kind, upstream}` — without command arguments or query URLs. Traces retain **call arguments** as received from client (unhashed): treated as upstream data. Replay: `TracePlayer(trace, guard="guard.toml")`, never touching upstream (`test_the_proxy_trace_validates_and_replays`).
- **Claude Desktop.** `neuroedge proxy mcp --desktop-config [--write] [--config-path P] [--name N]` prints (or writes, with backups, exactly one `mcpServers` entry) configuration for Desktop to run proxy. Desktop launches with minimal environment: variables in `env_from`/`headers_env` must be added to the entry's `env` block **manually** (prompted, never writing secrets to files).
- Not yet implemented: network frontend (for MCP: TSK-I2c-15 implements `proxy http` for HTTP APIs, §5), `--init-timeout` like `mcp serve`, gates reading facts from upstream itself.

### 4.4 `plugin doctor` — "proxy is the only path" can only be partially checked

`neuroedge plugin doctor [--config guard.toml] [--json]` (RFC-0016 §3d item 6, §5 risks 3, 8). It **warns** about findings and **states clearly** what it cannot check; never printing a bare "OK":

| Check | Result |
|:---|:---|
| `url`: try direct TCP connection to target (2 seconds) | connected ⇒ **WARNING** "đích còn tới được mà không qua proxy" (target still reachable without going through proxy); cannot connect ⇒ "không kiểm được" (unverifiable) (other machines unknown) |
| stdio: read Claude Desktop config (`mcp_desktop.default_config_path`) | other entry (not proxy) launches same command ⇒ **WARNING**; cannot read config ⇒ "không kiểm được" (unverifiable); always includes "không kiểm được: ứng dụng khác (Cursor, VS Code, shell…)" (unverifiable: other applications...) |
| each tool: gate reads `call_source` or `call_channel` | no ⇒ **WARNING** (RFC-0016 §5 risk 8) |
| plugin | loads distributions from `[plugins] enable` like Guard: load failure ⇒ **WARNING**; installed editable ⇒ **WARNING** (no file hashes, no badge); otherwise notes distribution, version, `files_sha256`. Always includes "không kiểm được: plugin (TSK-I2c-11) loại …" (unverifiable: plugin category...): categories other than actuator, and auto-kill levels (proven only via `conformance` on doubles) |

Exit code: `1` if at least one warning exists, `0` otherwise ("không kiểm được" [unverifiable] lines do not affect exit codes — they are not proof). `0` **does not** mean the proxy is the sole path: it simply means doctor detected no bypasses.
More reliable: isolate real servers behind firewalls/ACLs so only proxies reach them; doctor cannot perform network isolation.

## 5. `neuroedge proxy http` — an existing local HTTP API behind NeuroEdge (TSK-I2c-15, FR-EXT-06)

For Tasmota/Shelly/ESPHome web APIs, custom REST services, or Home Assistant REST endpoints. Each **declared route** is a `Guard` tool; requests forward to upstream APIs **strictly inside the tool's `run` body**, meaning after ALLOW; undeclared
routes return 404 and are never forwarded. Behavior and rigor match `proxy mcp` (§4): `guard init --http` → edit gates intentionally → `proxy http`.

### 5.1 `[proxy.http]` table

```toml
[proxy.http]
upstream = "http://127.0.0.1:8080"   # http only to loopback (or LAN with allow_lan_http, §4.1a); https to anywhere; no credentials/query/fragment
allow_lan_http = false               # default false; true: accepts plain http to private IP / *.local / *.lan / *.home.arpa (§4.1a)
listen   = "127.0.0.1:8787"          # loopback ONLY (127.0.0.0/8, ::1, localhost): front has no authentication in this release
id       = "http"                    # bridge id ⇒ source `bridge:http`
headers_env = { Authorization = "DEVICE_TOKEN" }   # header name → environment variable NAME; never values

[[proxy.http.routes]]
method = "POST"                      # GET | POST | PUT | PATCH | DELETE
path   = "/cm/{cmd}"                 # `{param}` is a full path segment; no `..`, no `%`, no query
tool   = "post_cm_cmd"               # a [tools.<name>] in same file
```

Load-time verification (NE3002, three-part): `listen` address not loopback; `upstream` HTTP to non-local hosts; plaintext secrets (keys named like secrets, `headers_env` values that are not variable names — never echoed);
duplicate routes (ignoring parameter names); missing tools; `{param}` not declared as tool parameter (which would cause all requests to be `REJECTED`); tools lacking routes; both `[proxy.mcp]` and `[proxy.http]` present.
Upstream connection failures or missing environment variables ⇒ fails to start.

### 5.2 Source is `bridge:<id>`

HTTP lacks built-in sources (adding enum values requires RFCs in `schemas/`), so this frontend is **a core bridge**: it calls `guard.dispatcher(id)` and all calls carry source `bridge:<id>` (default `bridge:http`, RFC-0017 §3b).
Gates **must explicitly list it**: gates listing only `mcp` block it (`criterion_unavailable`, HTTP 403) — `test_the_proxy_dispatches_as_a_bridge_and_a_gate_listing_only_mcp_blocks_it`. Generated gates explicitly list the file's `bridge:<id>`.

### 5.3 Request → tool

- **Tool parameters:** path parameters, query parameters, and **top-level scalars** of JSON bodies. Validated via `Guard` schemas: undeclared parameters ⇒ `REJECTED` (400).
- **400 without dispatch:** body not JSON, body not an object, nested/`null` values, duplicate JSON keys, duplicate parameters (within query, or across path/query/body), empty or unsafe path segments (`%2f`, `%5c`, `%00`, `//`, `.`/`..` after decoding).
- **Verbatim forwarding:** method, path, query, and body forwarded **as received** (not reconstructed) to `upstream`, accompanied by configured headers. Hop-by-hop headers stripped (including headers named in `Connection`), `Host` (reset), `Content-Length` (recalculated),
  `Expect`; **client `Authorization` and `Cookie` are never forwarded** — configured headers in `headers_env` take their place.
- **Responses:** ALLOW ⇒ upstream status, headers (minus hop-by-hop), and body; BLOCK ⇒ **403** + verdict JSON; `REJECTED` ⇒ **400** + verdict; undeclared route ⇒ **404** (stating only declared routes pass, forwarding nothing);
  body > 1 MiB ⇒ **413** (unread); `Transfer-Encoding` ⇒ 411; upstream error after ALLOW ⇒ **502** + verdict + issue description, **never retried**; upstream requests timeout at 30 seconds.
- Single request per connection (`Connection: close`); `dispatch` serialized under `Guard` lock.

### 5.4 Commands

- `neuroedge guard init --http <upstream> --route "METHOD /path/{param}" [--route …] [--dir DIR] [--name NAME] [--header-env HEADER=VAR]`: writes `guard.toml` and a **fail-closed** gate for each route (matching `operator_approved` template from `guard init --mcp`;
  `call_source` includes `bridge:http` in `options` and `allow_when` accepts only that); path parameters declared type `string`; query/body parameters must be added manually; never overwrites (`test_guard_init_http_never_overwrites_a_file`).
  `--mcp` and `--http` mutually exclusive; `--route` valid only with `--http`.
- `neuroedge proxy http [--config guard.toml] [--trace-out PATH]`: serves **loopback only** until SIGINT/SIGTERM, then writes trace (`metadata.proxy = {kind: "http", upstream}`); replay via `TracePlayer(trace, guard=…)` does not touch upstream.
- `neuroedge plugin doctor` (same command as §4.4): for `[proxy.http]`, **API reachable directly ⇒ WARNING** — for local APIs this is always true; operators must place device APIs behind firewalls/ACLs or accept requests only from proxy host. Doctor scans no networks,
  stating "không kiểm được" (unverifiable) for other machines/apps; gate not reading `call_source` ⇒ WARNING; plugins: "không kiểm được" (unverifiable). Exit codes per §4.4.
- **Not yet implemented:** TLS and authentication on frontend (hence loopback only), websockets, streaming bodies, `--init-timeout`.

## 6. Plugins: enable, load, provenance (RFC-0016 §3d; actuator part of TSK-I2c-11)

Code: `neuroedge/plugins/__init__.py`. Six entry point groups (`neuroedge.bridges`, `neuroedge.fact_sources`, `neuroedge.actuators`, `neuroedge.boards`, `neuroedge.templates`,
`neuroedge.exporters`); **only `neuroedge.actuators` is loaded** in this version.

**Chat channel adapters are not plugins** (*planned · Q-72, I2d*). The operator agent of Q-72 connects chat channels
(Telegram first). That adapter holds bot tokens and verifies approval records — determining whether a reply constitutes human
approval (`tool_calling.md` §6). Therefore, in MVP, adapters live in the **trusted runtime** authored by NeuroEdge
(architecture review per Q-72, 2026-10-11), not as third-party plugins; the Extension SDK provides no entry
point groups for chat channels. Third-party channels require dedicated RFCs (source `chat:<id>`, `threat_model.md` §2e).

- **Discovery without import.** `neuroedge plugin list [--json]` inspects `importlib.metadata` — group, entry point name, distribution, version — importing no packages (`test_listing_plugins_imports_nothing`).
- **Enabled in committed files, not CLI flags.** `[plugins] enable = ["neuroedge-ha", "neuroedge-ros2==0.4.1"]` in `agent.toml` or `guard.toml`: distribution name (PEP 503 matching), optional `==version` pin.
  Installation via `pip` enables nothing; **no CLI flags** enable plugins. `[plugins.config.<entry_point>]` is shared configuration for that entry point, merged **under** `[actuators.<name>.config]` on build; secret rules match `[external]`: plaintext secret fields ⇒ NE3002, `*_env` indicates variable names only (values never echoed).
- **Broken ⇒ fails to start.** Uninstalled · unimportable · `sdk_requires` incompatible (matching MAJOR, installed MINOR ≥ required MINOR; missing ⇒ incompatible) · version pin mismatch · duplicate entry point names across enabled distributions ·
  entry point name outside `[a-z][a-z0-9_]{0,31}` · factory does not accept exactly **one** argument (`config`) · enabled distribution possesses no NeuroEdge entry points · entry points present belonging to unimplemented categories (citing TSK-I2c-11) ·
  `[plugins.config.X]` targeting entry points unprovided by enabled distributions ⇒ `AgentManifestError` (NE3002), three-part, before pins are held and before first gate turn.
  `neuroedge build` raises identical errors (wrapped in `BuildFailed`).
- **Provenance.** Each loaded entry point: one line to stderr on startup, one entry in `metadata.plugins` across **all** session/Guard traces, and a `plugin_loaded` event, sharing data
  `{kind, name, distribution, version, files_sha256}` — `files_sha256` = `sha256:` of package files (filepath, on-disk byte sha256) in `dist.files`, not read from `RECORD`.
  Editable installs (`direct_url.json` containing `dir_info.editable`) carry `editable: true` instead of `files_sha256`. No enabled plugins ⇒ key `metadata.plugins` omitted (canonical traces unchanged).

## 7. Remote actuators (RFC-0018; TSK-I2c-16 core part)

> **Planned · Q-72, awaiting conditional safety RFC.** This section and §8 today treat **safety = off**: `safe_off`, tiers
> L0–L3 are promises about who restores actuators to `off`, `Actuator.safe_off()` sends `off`, tests `actuator.off_*` prove
> `off`. Q-72 finalized direction for symmetric `safe_state`: all actuators have `safe_state` declared in `board.v1` (default `off`),
> tiers and tests will refer to "returning to `safe_state`", moving *away* from `safe_state` is constrained by gates and limits.
> `safe_state` other than `off` declared strictly in `board.v1`, accompanied by hardware interlocks, never in `[actuators]` or
> plugins. All existing declarations (`off`) preserve exact behavior below. SDK names and signatures change only upon RFC
> approval. Threats: `threat_model.md` §2j.

Semantics and rationale: [RFC-0018](../rfc/0018-co-cau-chap-hanh-tu-xa.md) §3b–§3i (approved; constants in §9.5). Documents code behavior and design choices where RFC left options open.

**Declaration** (`agent.toml`, `guard.toml`, or programmatic `ActuatorDeclaration`):

```toml
[requires]
"digital.out" = { pins = ["garden_valve"] }      # remote actuator name declared alongside board pins

[plugins]
enable = ["neuroedge-ref-actuators"]

[actuators.garden_valve]
plugin     = "ref_l2"          # entry point name of an enabled distribution
safe_off   = "L2"              # tier relied upon by deployer; mandatory
reversible = false             # absent ⇒ false (irreversible)
[actuators.garden_valve.envelope]   # four keys of board.v1 #/$defs/envelope, all mandatory
window_s = 3600
max_on_ms_per_window = 1800000
min_interval_ms = 2000
max_continuous_ms = 600000
[actuators.garden_valve.config]     # passed (read-only) to plugin factory; no plaintext secrets
token_env = "NE_VALVE_TOKEN"
```

**Single validation function** — `check_actuators` (`neuroedge.guard`), via `plugins.actuators.remote_setup` for files — executes in `neuroedge build` (`engine/compiler.py`), in `SimSession.load`, and in `Guard`; covering all rules in §3b,
D5 (§3f), and §3k of the RFC; rule catalog with error codes is corpus `fixtures/actuators/` (`expected_errors.yaml`, bidirectionally closed). Warns, does not block: tier `L0`; `@action` modules importing
`httpx`, `requests`, `aiohttp`, `urllib.request`, or `socket` (printed in `neuroedge build`, `BuildReport.warnings`).

**Hardware pathway.** `digital_out` in `SimHAL` and `LinuxHAL` branches at function start into `HardwareAbstractionLayer._remote_out`: `require_pin → state interlock → envelope → authorize → record → apply`
(`test_the_order_is_require_pin_state_guard_envelope_authorize_record_apply`). `on`, `off`, `pulse` only; `after_ms` (scheduled commands) rejected (`BoardCapabilityError`). Only HAL holds plugins;
HAL receives class `Command` and four SDK exceptions via `hal.remote.Vocabulary` (HAL remains leaf, importing no `sdk`). Send errors `NotSent`/`Rejected` ⇒ refund pre-reservation, raise `BoardCapabilityError`;
`Ambiguous` (or unknown plugin errors, or exceeding `command_timeout_ms`) ⇒ retain pre-reservation, enter `uncertain`, raise `BoardCapabilityError`. `off` never raises.

**RFC open choices resolved by code (fail-closed):**

| Topic | Code implementation | Rationale |
|:---|:---|:---|
| Timing control when declared `safe_off` is lower than plugin `safe_off_level` | HAL utilizes **plugin tier** (device protocol): L2 always sends `duration_ms`, L3 always leases | Device guarantees are never discarded; D5 still evaluates declared tier |
| L0 | HAL still delivers its `off` at deadline `D` (matching L1) | Turn-off debt belongs to HAL; nothing forbids safe state |
| Pre-command readback | If `readback` supported: each `on`/`pulse` queries state immediately before interlock | Interlock requires reading ≤ `max_state_age_ms` |
| Reading `on` with zero turn-off debt | `already_on`, even while `uncertain`; emits no `off` | §3g: never turn off what it did not turn on |
| Lacking `readback` | Acknowledged `off` serves as turn-off confirmation; after reboot an acknowledged `off` is mandatory before first turn-on | §3g "off is the latest confirmed off" |
| State persistence | `<envelope_dir>/<name>.remote.json` `{version, name, off_owed, quarantined}`, written prior to command; missing without `envelope_init` (linux), or corrupt ⇒ `quarantined` | Matches envelope record rules (RFC-0007 §3d) |
| Clearing `quarantined` | Operator edits record (`"quarantined": null`) or calls `FileRemoteStore(<dir>).clear("<name>")`, then restarts (⇒ `uncertain` until fresh `off` readback) | No automated unquarantine path |
| Replay | Instantiates no plugins; each turn-on receives recorded state interlock verdict (`script_remote_state`), depleted data ⇒ `actuator_state_unknown`; envelope re-evaluates against recorded timeline, terminating at deadline `D` like all replay pins | `remote_*` events informational only (§3i) |
| Readback as gate facts (§3e end) | **Not yet implemented** (requires TSK-I2c-09): unprovided by sources, gates requiring it see absent facts ⇒ `BLOCK` | `test_uncertain_and_quarantined_are_absent_facts_so_a_gate_blocks` |
| `pwm`, `motion` on remote actuators; `esp32s3` | NE3001 at build time; runtime `pwm` ⇒ `BoardCapabilityError` | RFC-0018 §3a, §9.4 |

`sim` always drives plugin `DeviceDouble` (`probe()` invoked during HAL construction before I/O; missing `probe()` ⇒ unsupported on `sim`); mock clocks track session clocks. Trace events:
`simulation_coverage.md` §3; lint `remote_command_sent` (NE4001): `python/neuroedge/trace.py::lint_remote`.

Reference plugins (Apache-2.0, `fixtures/compliance/actuators/valid/neuroedge-ref-actuators/`): four entry points `ref_l0` … `ref_l3`, toy TCP protocols to mock devices, used solely via doubles.
Home Assistant adapter represents part B of TSK-I2c-16, not yet implemented.

## 8. `neuroedge conformance` — actuator category (RFC-0016 §3g, RFC-0018 §3e; TSK-I2c-12 part)

`neuroedge conformance <distribution> [--kind actuator] [--json]` loads **strictly** that distribution (typing name is explicit opt-in) and verifies each of its entry points. Code: `neuroedge/plugins/conformance.py`.
Dynamic checks run plugin doubles **through real HAL code** (`hal/remote.py`) on virtual clocks; factories invoked with module `conformance_config` (`Mapping`, defaulting to `{}`).

Checks `actuator.off_*` and tier vectors of `actuator.level_proven` today prove `off`; under conditional safety RFC
(*planned · Q-72*) they will prove declared `safe_state` (§7).

| Check | Passing criteria |
|:---|:---|
| `plugin.loads` | importable; factory accepts exactly one argument; returns an `Actuator` with complete attributes and methods, within RFC-0018 §9.5 limits |
| `plugin.sdk_range` | `sdk_requires` compatible with `SDK_VERSION` |
| `plugin.name_pattern` | entry point name matches `[a-z][a-z0-9_]{0,31}` |
| `actuator.level_proven` | declared tier vectors: L0 — `on` carries no duration; L1 — communication severed before deadline ⇒ HAL distrusts off state, retries every `OFF_RETRY_MS`, turns off and confirms upon reconnection; L2 — (a) `duration_ms ≤ D` on all `on`, (b) severed post-delivery ⇒ off before `D + tolerance_ms`, (c) severed pre-delivery ⇒ on duration does not exceed `D`; L3 — (a) runtime freezes ⇒ off ≤ `lease_ms + tolerance_ms` following last renewal, (b) duplicate/late renewals do not extend beyond `start + D + tolerance_ms`, (c) `lease_ms ≤ max_lease_ms` |
| `actuator.off_is_idempotent` | `safe_off()` twice (while off, then following an `on`) without error |
| `actuator.off_is_unconditional` | HAL with ledger rejecting all commands can still turn off device |
| `actuator.builds_without_io` | factory executes with `socket` blocked, attempting zero network connections |
| `actuator.classifies_errors` | communication severed: `apply`/`safe_off` raise `NotSent`, `Rejected`, or `Ambiguous`; `read_state` raises `ReadFailed` |
| `actuator.receives_no_handles` | factory receives `config` only; driver holds zero core objects (outside `neuroedge.sdk`/`errors`) |

Results `pass` · `fail` · `unverifiable` (missing `probe()`: four dynamic checks). Failed load ⇒ all `actuator.*` checks `fail`. Exit codes: §6 of `python_api.md`.
Report `--json`: `{distribution, version, files_sha256, editable, sdk, core, checker, results: [{entry_point, check, result, detail}], unimplemented, problem, badge_eligible, exit_code}` —
`badge_eligible` true strictly when all checks `pass`, non-editable, and `files_sha256` present (badges are TSK-I2c-18); not yet in `schemas/` (RFC-0016 §3g).
Corpus `fixtures/compliance/actuators/{valid,invalid}/` + `expected_results.yaml`: each check catches at least one counter-example (`test_every_check_of_every_kind_catches_a_counter_example`).
P1 proves how plugins construct protocol commands on doubles, **not** that physical firmware honors commands (RFC-0018 §3e).
