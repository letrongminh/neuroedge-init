# Partner pilot — NeuroEdge

> **Promise:** *đặt một gate trước mọi lệnh AI chạm vào thiết bị bạn đang có* (place a gate before every AI command that touches a device you already have) — in ≤ 15 minutes, with no new hardware to buy.

NeuroEdge places a **gate** (a human-readable YAML file) between AI and your devices: every command must pass through the gate, the gate **blocks by default**, and you **intentionally open** each capability one by one. Every decision is recorded in a
**trace** that you can inspect and replay. This pilot release is prepared exclusively for a partner team under a written evaluation agreement; the wheel is delivered directly and is **not** available on PyPI or any public package index.

## 1. Prerequisites

- **Python 3.11 or newer** (`python3 --version`).
- **A wheel package file** delivered by us, e.g. `neuroedge-0.1.0-py3-none-any.whl`.
- An existing target to protect: an MCP server (such as Home Assistant), an HTTP API of a local device, or your custom Python agent.

Install into an isolated virtual environment (do not install into system Python):

<!-- guide: skip reason="cài wheel thật của đối tác; script partner_guides_check.sh cài wheel vào một venv sạch trước khi chạy các hướng dẫn" -->
```bash
python3 -m venv neuroedge-venv
. neuroedge-venv/bin/activate
pip install './neuroedge-0.1.0-py3-none-any.whl[mcp]'
neuroedge --help
```

`[mcp]` pulls in the MCP SDK (required for `proxy mcp` and runner test examples). Once the `neuroedge` command is available, installation is complete.

## 2. Choose a guide

| What you want to protect | Read | Main command | Requirements |
|:---|:---|:---|:---|
| Home Assistant (or another MCP server) called by Claude Desktop | [`home-assistant-mcp.md`](home-assistant-mcp.md) | `guard init --mcp`, `proxy mcp` | MCP address and HA token |
| Tool calls inside **your Python agent** | [`guard-python.md`](guard-python.md) | `neuroedge.guard` | Python only — no device needed |
| HTTP API of a local device (Tasmota, Shelly, custom REST API) | [`proxy-http.md`](proxy-http.md) | `guard init --http`, `proxy http` | API address, `curl` |

Each guide provides: ≤ 3 commands to initial value, how to observe **BLOCK** followed by **ALLOW** after intentionally opening a gate, how to inspect traces, how to make the proxy the sole communication path, and common errors with real message text.
All commands in the three guides are automatically tested against the wheel (`scripts/partner_guides_check.sh`) using test doubles of Home Assistant and device HTTP APIs — meaning the commands are syntactically and functionally valid, but **not** that they have been tested against your specific real devices.

## 3. Three things to remember

1. **Blocked by default.** Generated gates block everything (`BLOCK`, `criterion_unavailable`) until you edit them. Seeing a `BLOCK` on your first attempt is expected behavior, not a failure.
2. **The proxy guards only the traffic passing through it.** Any client calling the device directly bypasses the gate. `neuroedge plugin doctor` flags detected bypass paths; closing them (tokens, firewall rules) is your responsibility.
3. **Traces contain call parameters** (such as device names) in plain text, not hashed. Inspect them before sending them to us.

## 4. Send feedback

Use [`phan-hoi.md`](phan-hoi.md): copy the template, fill it out (time to first BLOCK, time to first intentional ALLOW, verbatim error messages, confusing points), and send it via the private channel established for your team.
To share traces: attach the `trace-*.json` file after reviewing its contents.

## 5. Limitations

Read [`gioi-han.md`](gioi-han.md) before starting: the pilot release **does not yet include** `esp32s3`, on-chip voice, or NeuroEdge Lab; Home Assistant integration has only been tested against doubles; the proxy cannot block direct calls; and the license
(PolyForm Noncommercial) permits evaluation solely under the written partner agreement.
