# Guide 1 — Home Assistant via `neuroedge proxy mcp`

> **Goal:** place a gate before *every AI command sent to Home Assistant* (HA) via HA's **MCP Server** integration — Claude Desktop or any
> other MCP client talks to the proxy, not directly to HA. **Duration:** ≤ 15 minutes from wheel installation.
>
> **Verification status — read first:** this guide is **chưa kiểm trên Home Assistant thật** (not verified on real Home Assistant). All commands below are executed
> from the wheel by [`scripts/partner_guides_check.sh`](../../../scripts/partner_guides_check.sh) against a **test double**
> ([`fixtures/ha_mcp_double/`](../../../fixtures/ha_mcp_double/server.py)) modeled after public documentation of the MCP Server integration (endpoints,
> `Bearer` tokens, `HassTurnOn`-style tool names). Real HA tool names, parameters, and `/api/mcp` endpoints may differ; any discrepancy is valuable feedback —
> submit it using the [feedback form](phan-hoi.md). Additional limitations: [`gioi-han.md`](gioi-han.md).

## 0. Prerequisites

- Installed the wheel per [README](README.md) (`neuroedge --help` runs).
- Inside HA: **Model Context Protocol Server** integration is enabled; we recommend creating **a dedicated HA user for the proxy** with a *long-lived access token*
  (Profile → Security). Keep tokens strictly in environment variables, **never** in committed files.
- HA MCP URL, e.g. `http://192.168.1.10:8123/api/mcp` (home LAN, plain http) or `https://…` if configured.

Set the two variables (`read -s` prevents printing and history logging):

<!-- guide: skip reason="đặt biến môi trường: script đã đặt sẵn HA_MCP_URL và HA_AUTH trỏ vào bản giả" -->
```bash
export HA_MCP_URL="http://192.168.1.10:8123/api/mcp"
read -rs HA_TOKEN && export HA_AUTH="Bearer $HA_TOKEN" && unset HA_TOKEN
```

## 1. Three commands to initial value

**Command 1 — connect to HA, list tools, generate configuration and gates.** `--allow-lan-http` is only required when HA uses plain http on the local network; omit it
when using `https://` (rationale and security risks: [`gioi-han.md`](gioi-han.md)).

<!-- guide: run expect="tool(s) behind the Guard, all BLOCKED until you open their gate" expect="wrote" -->
```bash
neuroedge guard init --mcp "$HA_MCP_URL" --header-env Authorization=HA_AUTH --allow-lan-http --name homeassistant --dir ha
```

This writes `ha/guard.toml` and a gate for **each** HA tool in `ha/gates/`. Each gate **blocks by default**: it demands a fact (`operator_approved`) that nobody has set.
Tools with required non-scalar parameters (arrays, objects) are not exposed, with reasons printed; optional array parameters (such as HA's `domain`)
are omitted, with an explanatory note. Tool names in `guard.toml` are lowercased (`hassturnon`); original HA names reside under `[proxy.mcp.names]`.

**Command 2 — register the proxy into Claude Desktop** (replacing direct `HA` in Claude configuration). Test against a temporary file first — leaving real configuration untouched:

<!-- guide: run expect="Wrote mcpServers['homeassistant']" expect="Quit Claude Desktop completely" -->
```bash
neuroedge proxy mcp --config ha/guard.toml --desktop-config --write --config-path ./claude_desktop_thu.json
```

Once verified, apply to your actual configuration (retaining existing entries and creating a `.bak-<timestamp>` backup):

<!-- guide: skip reason="ghi vào cấu hình Claude Desktop thật của máy; bước trên đã thử cùng lệnh ra tệp tạm" -->
```bash
neuroedge proxy mcp --config ha/guard.toml --desktop-config --write
```

Claude Desktop launches the proxy with a **minimal** environment: it will not see your shell's `HA_AUTH`. Open the configuration file and add an `env` block specifically for `homeassistant`
(the command prints a reminder and **never** writes secrets into configuration files for you):

<!-- guide: skip reason="chỉnh tay cấu hình Claude Desktop" -->
```json
"homeassistant": { "command": "…", "args": ["…"], "env": { "HA_AUTH": "Bearer <dedicated HA user token>" } }
```

Be aware of this security consideration: the token resides in **plain text** within Claude Desktop's local configuration file on this host. This is why you should use a dedicated HA account with scoped permissions for the proxy.

**Command 3 — quit completely and reopen Claude Desktop** (do not merely close its window), then ask: *"bật đèn phòng khách"* (turn on the living room light). Claude invokes the tool through the proxy and receives **BLOCK**.

If you do not have Claude Desktop or prefer running headless tests: save this minimal client as `thu.py`. It spawns the proxy exactly like Claude Desktop, invokes a tool, and prints results; the first argument specifies the trace output path.

<!-- guide: run -->
```bash
cat > thu.py <<'PY'
import asyncio, json, os, sys
from mcp import Client, StdioServerParameters

async def main(trace, tool, arguments):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "neuroedge", "proxy", "mcp", "--config", "ha/guard.toml", "--trace-out", trace],
        env={"HA_AUTH": os.environ["HA_AUTH"]},
    )
    async with Client(params) as client:
        result = await client.call_tool(tool, arguments)
        print(json.dumps(result.structured_content or result.content[0].text))

asyncio.run(main(sys.argv[1], sys.argv[2], json.loads(sys.argv[3])))
PY
```

## 2. Observing BLOCK

<!-- guide: run expect='"status": "BLOCK"' expect='"reason": "criterion_unavailable"' expect='"failed_criterion": "operator_approved"' log_lacks="HA_LOG|HassTurnOn" -->
```bash
python thu.py ha/trace-block.json hassturnon '{"name": "Living room lamp"}'
```

`BLOCK` + `criterion_unavailable` confirms the gate operates correctly: it required `operator_approved` which was never set, so **nothing reached HA** (the test verifies the double received no calls).
This is standard expected behavior, not an error — exactly what you want when an AI is manipulated into calling a physical tool.

## 3. Intentionally opening a gate and observing ALLOW

Opening a gate is a **manual human action**, performed one tool at a time. The gate for tool `hassturnon` is located at `ha/gates/hassturnon@1.0.0.yaml`; instructions are at the top of the file.
The quickest way is removing `operator_approved` from both locations (`evaluate:` and `allow_when:`) using a single command — or editing it in a text editor:

<!-- guide: run -->
```bash
f="ha/gates/hassturnon@1.0.0.yaml"
awk '/^  operator_approved:/ {skip=1; next} skip && /^    / {next} {skip=0; print}' "$f" > "$f.new" && mv "$f.new" "$f"
```

Afterwards, only the source constraint remains: `call_source: { in: [mcp] }` — allowing MCP clients upstream of the proxy to invoke this tool. Verify the gate remains valid:

<!-- guide: run expect="gate(s) resolved" -->
```bash
neuroedge gate lint ha/gates
```

<!-- guide: run expect="Turned on Living room lamp" log_has="HA_LOG|HassTurnOn" -->
```bash
python thu.py ha/trace-allow.json hassturnon '{"name": "Living room lamp"}'
```

This time the call clears the gate and **proceeds** to HA (the test verifies the double receives exactly one `HassTurnOn` command). Other tools remain blocked — try `hassturnoff`:

<!-- guide: run expect='"status": "BLOCK"' log_lacks="HA_LOG|HassTurnOff" -->
```bash
python thu.py ha/trace-other.json hassturnoff '{"name": "Living room lamp"}'
```

Open whatever tools you need, but avoid opening them blanket "for all MCP clients": write concrete conditions into gates (`neuroedge gate explain`, example gates under `gates/`) for hard-to-reverse actions like door locks.

## 4. Inspecting traces

Each proxy session writes a trace (`--trace-out`). Validate then view:

<!-- guide: run expect="VALID" -->
```bash
neuroedge trace validate ha/trace-allow.json
```

<!-- guide: run expect="gate_evaluation_result" expect="ALLOW" expect="tool_call" -->
```bash
neuroedge trace show ha/trace-allow.json
```

You will see `tool_call` (source `mcp`, tool name, **parameters**), and `gate_evaluation_result` (`ALLOW` or `BLOCK`, and rationale). The trace **contains call parameters** exactly as sent by the client
(such as device entity names) unhashed — treat it as private household data when sharing with us (see [`phan-hoi.md`](phan-hoi.md)).

## 5. Making the proxy the sole path

The proxy guards only the traffic passing **through it**. Any client calling HA directly bypasses the gate. `plugin doctor` reports detected bypasses and explicitly notes what it **cannot** check:

<!-- guide: run exit=1 expect="allow_lan_http đang bật" expect="đích còn tới được mà không qua proxy" expect="không kiểm được: plugin (TSK-I2c-11)" -->
```bash
neuroedge plugin doctor --config ha/guard.toml
```

Exit code `1` = warnings detected (here always expected: HA is reachable directly from your host). Practical hardening steps that doctor cannot automate:

- **Tokens are keys.** Only the proxy should hold the HA access token (from the dedicated HA user). Claude Desktop, agents, and custom scripts must **not** possess that token — they communicate solely with the proxy. Any client possessing the HA token constitutes a bypass.
- **Networking.** If possible, restrict network access to HA ports so only the proxy host (and necessary devices like the HA mobile app) can connect; doctor does not inspect firewalls or scan network topologies.
- **Other local applications** (Cursor, VS Code, developer scripts) might have MCP entries pointing directly to HA: audit them manually.

## 6. Lỗi thường gặp (real messages)

**Missing environment variable** — forgot `export HA_AUTH`:

<!-- guide: run exit=1 expect="environment variable(s) ['HA_AUTH'] named in guard.toml are not set" expect="export HA_AUTH=" -->
```bash
env -u HA_AUTH neuroedge guard init --mcp "$HA_MCP_URL" --header-env Authorization=HA_AUTH --allow-lan-http --dir ha-loi
```

(The message mentions "named in guard.toml" even though `guard.toml` does not exist prior to `init` — referring to the variable passed via `--header-env`.)

**Invalid or expired token** — HA responds 401; proxy does not expose HTTP status codes, reporting generically:

<!-- guide: run exit=1 expect="cannot connect to the real MCP server" expect="Server returned an error response" -->
```bash
HA_AUTH="Bearer sai-token" neuroedge guard init --mcp "$HA_MCP_URL" --header-env Authorization=HA_AUTH --allow-lan-http --dir ha-loi
```

How to verify manually: test the token directly with `curl -i -H "Authorization: $HA_AUTH" "$HA_MCP_URL"` — `401` confirms token invalidity.

**Plain http to LAN host without enabling flag**:

<!-- guide: run exit=1 expect="plain http to another machine on the LAN sends the calls and the token in clear" expect="allow_lan_http = true" -->
```bash
neuroedge guard init --mcp "http://192.168.1.10:8123/api/mcp" --header-env Authorization=HA_AUTH --dir ha-loi
```

**Plain http to non-LAN host** — the flag cannot bypass this constraint, use https:

<!-- guide: run exit=1 expect="plain http to a host outside loopback and the home LAN would send the token in clear over the internet" -->
```bash
neuroedge guard init --mcp "http://ha.example.com/api/mcp" --header-env Authorization=HA_AUTH --allow-lan-http --dir ha-loi
```

**Proxy fails to start when HA is unreachable, address is wrong, or variables are missing** — it never starts up in a "partially degraded" state:

<!-- guide: run exit=1 expect="environment variable(s) ['HA_AUTH'] named in guard.toml are not set" -->
```bash
env -u HA_AUTH neuroedge proxy mcp --config ha/guard.toml
```

**All tools evaluate to BLOCK after editing gates** — gates are loaded only during proxy initialization: quit Claude Desktop completely (it holds the previous proxy process) and reopen it.

**Tool names differ in HA** — if `guard init` prints "NOT exposed" for a desired tool, that tool has required non-scalar parameters; unsupported in this release
(note in feedback: which tool, which parameters).

## 7. Next steps

Submit feedback via [`phan-hoi.md`](phan-hoi.md) (time to first BLOCK, time to first intentional ALLOW, verbatim errors). Finished with HA? The other two guides:
[`guard-python.md`](guard-python.md) (custom Python agents), [`proxy-http.md`](proxy-http.md) (local device APIs like Tasmota).
