# Guide 3 — Local device APIs via `neuroedge proxy http`

> **Goal:** place a gate before the HTTP API of a local smart home device (such as Tasmota, Shelly, ESPHome, or a custom REST service). Each route you **declare** is
> treated as a gated tool; requests are forwarded to the device **only after the gate allows them**; undeclared routes are rejected with HTTP 404 and never reach the device. **Duration:** ≤ 15 minutes from wheel installation.
>
> Verification status: the commands below are executed from the wheel by [`scripts/partner_guides_check.sh`](../../../scripts/partner_guides_check.sh) against a **test double** of a device API
> ([`fixtures/http_upstream/`](../../../fixtures/http_upstream/server.py)): Tasmota-style `GET /cm?cmnd=…` and REST-style `POST /api/{cmd}`. **Not verified on real devices**:
> your hardware may require authentication or formatting not modeled by the double — please record details in the [feedback form](phan-hoi.md). Limitations: [`gioi-han.md`](gioi-han.md).

## 0. Prerequisites

- Installed the wheel per [README](README.md); `curl` (available on macOS and Linux).
- Device API endpoint, e.g. `http://192.168.1.50` (Tasmota). If the device speaks plain http on LAN, you need the `--allow-lan-http` flag in Command 1 (risks: [`gioi-han.md`](gioi-han.md)).
- Port `8787` free on this host (proxy default; configurable via `listen` in `guard.toml`).

<!-- guide: skip reason="đặt biến môi trường: script đã đặt sẵn DEVICE_URL trỏ vào bản giả" -->
```bash
export DEVICE_URL="http://192.168.1.50"
```

## 1. Commands to initial value

**Command 1 — declare routes.** Each `--route "METHOD /path/{param}"` becomes a tool; the command generates `guard.toml` and a gate **blocking by default** for every route.
Example for Tasmota (`GET /cm?cmnd=Power On`) and a REST API (`POST /api/{cmd}`):

<!-- guide: run expect="2 tool(s) behind the Guard, all BLOCKED until you open their gate" expect="get_cm" expect="post_api_cmd" -->
```bash
neuroedge guard init --http "$DEVICE_URL" --route "GET /cm" --route "POST /api/{cmd}" --allow-lan-http --name plug --dir plug
```

Path parameters (`{cmd}`) are declared automatically. **Query parameters and body schemas must be declared manually**, one by one — undeclared parameters are rejected (400). Tasmota receives commands in the `cmnd` query parameter,
so declare it; the REST API expects integer payload in JSON:

<!-- guide: run -->
```bash
cat >> plug/guard.toml <<'TOML'

[tools.get_cm.parameters.cmnd]
type = "string"

[tools.post_api_cmd.parameters.value]
type = "integer"
required = false
TOML
```

**Command 2 — run the proxy** (keep this terminal open; press **Ctrl-C** to stop; the proxy writes traces upon exit):

<!-- guide: run bg=proxy wait="127.0.0.1:8787" -->
```bash
neuroedge proxy http --config plug/guard.toml --trace-out plug/trace-1.json
```

The proxy listens exclusively on `127.0.0.1` (refusing any other address: it has no authentication in front). From now on, your application/agent calls `http://127.0.0.1:8787` instead of `$DEVICE_URL`.

**Command 3 — send a test request** (in another terminal). Switch on the device via the proxy:

<!-- guide: run expect="HTTP 403" expect='"status": "BLOCK"' expect='"reason": "criterion_unavailable"' expect='"failed_criterion": "operator_approved"' log_lacks="DEVICE_LOG|Power" -->
```bash
curl -s -w '\nHTTP %{http_code}\n' "http://127.0.0.1:8787/cm?cmnd=Power%20On"
```

## 2. Observing BLOCK

`HTTP 403` with `BLOCK` + `criterion_unavailable`: the gate operates correctly. It required `operator_approved` which was never set, so **the device received nothing** (the test verifies the double's log is empty).
HTTP status codes from the proxy: **403** = gate blocked; **400** = bad request (undeclared parameter, malformed JSON, duplicate query parameter) and dropped before reaching gate or device; **404** = undeclared route; **413** = body > 1 MiB;
**502** = gate allowed but upstream device error — and proxy **never retries** (the call might have already taken effect).

Undeclared routes are never forwarded, regardless of gate settings:

<!-- guide: run expect="HTTP 404" expect="only declared routes pass" expect="nothing was forwarded" log_lacks="DEVICE_LOG|admin" -->
```bash
curl -s -w '\nHTTP %{http_code}\n' http://127.0.0.1:8787/admin
```

## 3. Intentionally opening a gate and observing ALLOW

Stop the proxy first (gates are loaded during startup only):

<!-- guide: stop=proxy -->
```text
Ctrl-C in the terminal running `neuroedge proxy http`
```

Open the gate for `GET /cm` — `plug/gates/get_cm@1.0.0.yaml`; instructions are located at the top of the file. The fastest way is removing `operator_approved` from both locations, or editing in a text editor:

<!-- guide: run -->
```bash
f="plug/gates/get_cm@1.0.0.yaml"
awk '/^  operator_approved:/ {skip=1; next} skip && /^    / {next} {skip=0; print}' "$f" > "$f.new" && mv "$f.new" "$f"
```

**Source is `bridge:http`, not `mcp`.** HTTP does not have a built-in caller identity (adding one alters schema, requiring an RFC), so the proxy runs as a *core bridge*: all its requests carry
`call_source = bridge:http`. The gate **must list it** — gates listing only `mcp` will block all HTTP requests. The generated gate handles this correctly:

<!-- guide: run expect='in: ["bridge:http"]' -->
```bash
grep -n 'bridge:http' plug/gates/get_cm@1.0.0.yaml
```

Restart the proxy and issue the request again:

<!-- guide: run bg=proxy wait="127.0.0.1:8787" -->
```bash
neuroedge proxy http --config plug/guard.toml --trace-out plug/trace-2.json
```

<!-- guide: run expect="HTTP 200" expect='"POWER": "ON"' log_has="DEVICE_LOG|/cm?cmnd=Power%20On" -->
```bash
curl -s -w '\nHTTP %{http_code}\n' "http://127.0.0.1:8787/cm?cmnd=Power%20On"
```

This time the request passes the gate and **reaches** the device verbatim (matching method, path, and query as sent). The other route remains blocked:

<!-- guide: run expect="HTTP 403" log_lacks="DEVICE_LOG|/api/" -->
```bash
curl -s -w '\nHTTP %{http_code}\n' -X POST -H 'Content-Type: application/json' -d '{"value": 1}' http://127.0.0.1:8787/api/relay
```

Unknown or duplicate parameters violate request validation and are rejected before reaching upstream:

<!-- guide: run expect="HTTP 400" expect="unknown argument 'x'" -->
```bash
curl -s -w '\nHTTP %{http_code}\n' "http://127.0.0.1:8787/cm?cmnd=Power&x=1"
```

<!-- guide: run expect="HTTP 400" expect="a query parameter is given twice" -->
```bash
curl -s -w '\nHTTP %{http_code}\n' "http://127.0.0.1:8787/cm?cmnd=Power&cmnd=Power"
```

Client credentials are **never** forwarded to upstream devices (the proxy forwards only headers declared under `headers_env`):

<!-- guide: run expect="HTTP 200" log_lacks="DEVICE_LOG|Bearer cua-client" -->
```bash
CLIENT_AUTH='Bearer cua-client'
curl -s -w '\nHTTP %{http_code}\n' -H "Authorization: $CLIENT_AUTH" "http://127.0.0.1:8787/cm?cmnd=Power%20On"
```

Does the device require authentication via headers (e.g. `Authorization`)? Declare the header name and **environment variable name** holding the secret — never raw secret values — then `export` that variable:

<!-- guide: skip reason="ví dụ cấu hình; thiết bị giả không đòi xác thực" -->
```toml
[proxy.http]
headers_env = { Authorization = "DEVICE_AUTH" }
```

## 4. Inspecting traces

<!-- guide: stop=proxy -->
```text
Ctrl-C in the terminal running `neuroedge proxy http` — proxy flushes trace on exit
```

<!-- guide: run expect="VALID" -->
```bash
neuroedge trace validate plug/trace-2.json
```

<!-- guide: run expect="gate_evaluation_result" expect="bridge:http" expect="tool_call" -->
```bash
neuroedge trace show plug/trace-2.json
```

Every request reaching a gate creates a `tool_call` entry with source `bridge:http` and **parameters** (path, query, body scalars) — unhashed. Requests rejected at 400/404 fail early and create no `tool_call`
(never evaluated by gate). Treat traces as private local data when submitting them to us ([`phan-hoi.md`](phan-hoi.md)).

## 5. Making the proxy the sole path

The proxy guards traffic passing **through it**; the device continues listening at its original address. `plugin doctor` tests connectivity directly to the upstream and explains what it cannot verify:

<!-- guide: run exit=1 expect="target still reachable without the proxy" expect="firewall" expect="allow_lan_http is on" expect="cannot verify: plugin (TSK-I2c-11)" -->
```bash
neuroedge plugin doctor --config plug/guard.toml
```

For local APIs, doctor **always** raises warnings (exit code `1`): the device is always reachable directly from your machine. Real hardening measures are yours to enforce:

- Place device APIs behind router firewall rules/ACLs, or configure the device to whitelist only the proxy host IP. Any application/agent still reaching `http://192.168.1.50` constitutes a bypass.
- Never bind the proxy outside loopback for convenience: it lacks authentication in front and will refuse to start if `listen` is bound to non-loopback addresses.
- If the device uses tokens/passwords: only the proxy should hold them.

## 6. Lỗi thường gặp (real messages)

**`listen` is not loopback**:

<!-- guide: run exit=1 expect="the proxy listens on loopback only" expect="use 127.0.0.1" -->
```bash
sed 's/127.0.0.1:8787/0.0.0.0:8787/' plug/guard.toml > plug/loi-listen.toml && neuroedge proxy http --config plug/loi-listen.toml
```

**Device is offline or address is incorrect** — proxy fails to start:

<!-- guide: run exit=1 expect="cannot reach the real API" -->
```bash
sed 's#^upstream = .*#upstream = "http://127.0.0.1:9"#' plug/guard.toml > plug/loi-tat.toml && neuroedge proxy http --config plug/loi-tat.toml
```

**Plain http to LAN device without enabling flag**:

<!-- guide: run exit=1 expect="plain http to another machine on the LAN sends the calls and the token in clear" expect="allow_lan_http = true" -->
```bash
neuroedge guard init --http "http://192.168.1.50" --route "GET /cm" --dir plug-loi
```

**Plain http to non-LAN address** — the flag cannot bypass this constraint:

<!-- guide: run exit=1 expect="plain http to a host outside loopback and the home LAN would send the token in clear over the internet" -->
```bash
neuroedge guard init --http "http://thiet-bi.example.com" --route "GET /cm" --allow-lan-http --dir plug-loi
```

**Invalid path or method in `--route`**:

<!-- guide: run exit=1 expect="not `METHOD /path`" -->
```bash
neuroedge guard init --http "http://127.0.0.1:1" --route "cm" --dir plug-loi
```

**All requests return 403 after editing gates** — gates are only loaded at proxy startup: stop and restart the proxy. If 403 persists, examine `reason` in response: `criterion_unavailable` means fact unsupplied,
`condition_not_met` indicates failing gate logic; verify the gate lists `bridge:http` (see §3).

**`Address already in use` when starting proxy** — port `8787` is occupied by another process. Change `listen = "127.0.0.1:8787"` in `plug/guard.toml` to an open port, or terminate the conflicting process.
(In this release this error produces a full traceback rather than a succinct error message; this is tracked.)

## 7. Next steps

Submit feedback via [`phan-hoi.md`](phan-hoi.md). The other two guides: [`home-assistant-mcp.md`](home-assistant-mcp.md), [`guard-python.md`](guard-python.md).
