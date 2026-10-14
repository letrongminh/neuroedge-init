# Partner pilot — limitations and pending items

This page states plainly what the pilot release **does not** do or **has not verified**. If any item here blocks you, report it through the [feedback form](phan-hoi.md): that is the exact information we need.

## Not included in the pilot

| Item | Status |
|:---|:---|
| `esp32s3` (running gates on ESP32-S3-Box-3 chip) | **Out of pilot scope.** No hardware boards in hand yet; no firmware ready for delivery |
| On-chip voice ("thoại trên chip": microphone, speaker, on-device wake-word) | **Out of pilot scope** |
| NeuroEdge Lab — authoring new hardware contracts using Claude Code or Claude Desktop via lab tools (Q-71; formerly called NeuroBrain) | **Out of pilot scope** |
| `linux` on real Raspberry Pi ("Raspberry Pi thật": physical GPIO pins) | **Experimental**, not yet automatically verified on real Pi; do not use for hazardous hardware without prior manual testing |
| Remote actuators (network device control using virtual pins with envelopes) | Present in core (`[actuators.<name>]`, [`extension_sdk.md`](../../spec/extension_sdk.md) §7) and an **L1-tier** Home Assistant plugin (`switch`, `light`, `input_boolean`) delivered separately as a `neuroedge-homeassistant` wheel if needed by the pilot. L1 means NeuroEdge autonomously issues turn-off commands upon timeout; upon communication loss, devices might remain powered on indefinitely, so **irreversible** actions (valves, locks, heaters) are rejected by `neuroedge build` with this plugin. Verified only on Home Assistant double, **chưa kiểm trên Home Assistant thật** (not verified on real Home Assistant; TSK-I2c-16). |
| Third-party plugins (bridges, fact sources…) | Plugin loader not implemented yet (TSK-I2c-11); `plugin doctor` prints "không kiểm được: plugin" |
| Public releases (PyPI, package index) | None: wheel is delivered directly |
| NeuroEdge Blueprint (packaging, installing, and selling bundled kits + firmware + contracts; distinct from Home Assistant Blueprints) | **Out of pilot scope.** Architecture decided in Q-72, no code yet |
| Operator agent (running 24/7, autonomously reporting trends and proposals, mission contracts) | **Out of pilot scope.** Q-72, no code yet; currently only a user on device can answer `ask` questions |
| Telegram or other chat channels (alerts, approvals via chat) | **Out of pilot scope.** Q-72, no chat adapters yet |

## Not verified on real devices

- **Home Assistant:** the guide [`home-assistant-mcp.md`](home-assistant-mcp.md) currently runs against a **test double** built per public documentation of MCP Server integration ([`fixtures/ha_mcp_double/`](../../../fixtures/ha_mcp_double/server.py)). Addresses (`/api/mcp`), tool names, and parameters on a real HA may differ; **chưa kiểm trên Home Assistant thật** (not verified on real Home Assistant).
- **Device APIs:** [`proxy-http.md`](proxy-http.md) runs against a test double (`GET /cm?cmnd=…`, `POST /api/{cmd}`). Real devices may require different authentication, formats, or responses. Tasmota with web passwords (`user`/`password` query parameters) is **not yet supported** out of the box: the proxy only forwards parameters you declare.

## Security limits — understand before using

- **The proxy cannot block direct calls ("không chặn được lời gọi thẳng").** It only guards traffic passing through it. Any client still able to reach the original device or MCP server directly (holding a token, or residing on the same network) can make direct calls, rendering the gate ornamental. `neuroedge plugin doctor` reports detected bypasses and states what it cannot check; isolating devices behind firewalls/ACLs and ensuring tokens are known only to the proxy is your responsibility ([`threat_model.md`](../../spec/threat_model.md) §2b).
- **`proxy http` has no authentication in front ("không có xác thực ở phía trước")**, so it listens exclusively on loopback (`127.0.0.1`, `::1`) and refuses to start if `listen` is bound to any other address. Other machines on your local network cannot access its front; anyone with access to this host has access to the proxy.
- **Plain http on home LAN** is only permitted when explicitly enabled via `allow_lan_http = true` (or the `--allow-lan-http` flag of `guard init`) and only directed to private IPs or hostnames matching `*.local`, `*.lan`, `*.home.arpa`. When enabled, requests and **tokens travel unencrypted across the LAN**: anyone sniffing local traffic can read and replay tokens, calling devices directly. Use `https` whenever supported by the device. `plugin doctor` always warns when this flag is enabled.
- **Tokens in Claude Desktop configuration** (`env` block added manually) reside in plain text within Claude Desktop config files. Use a dedicated user/token with minimal privileges for the proxy.
- **Traces may contain call parameters ("tham số của lời gọi")** (device names, argument values) — unhashed. Inspect traces before submitting them to us.
- **The proxy and `Guard` are not sandboxes**: they do not isolate against code running in the same process or on the same host with matching privileges.
- **Opening gates wider is your responsibility.** Generated gates block everything; gates you open are only as safe as the conditions you write into them. Do not open gates "for all clients" on hard-to-reverse physical actions (door locks, mains power).

## Licensing and data

- Source code is licensed under **PolyForm Noncommercial 1.0.0** ([`LICENSING.md`](../../../LICENSING.md)): strictly for non-commercial use. The pilot is an *evaluation* conducted under the **written testing agreement** between both parties; commercial deployment requires a separate agreement. Nothing herein overrides that agreement.
- Wheel is delivered directly, **not** distributed via PyPI. We do not automatically collect your traces: you choose what to submit through your private channel.
