# Device Integration Market for AI Agents — 2026-10-04

Landscape report serving as basis for **Q-67** (open platform, `roadmap/neuroedge-prd.md` §15) and design note
`docs/architecture/vi/16-ecosystem-landscape.md` §4. Core questions: how existing and newly emerging
AI-hardware ecosystems connect devices, where safety gates can be placed, and what they still lack.

**Methodology:** reviewing official documentation and repositories as of 2026-10-04. Entries marked *(secondary)* rely solely on press sources;
*(unverified)* indicates points unconfirmed by primary sources. Market moves fast — this report is a point-in-time snapshot, not
continually updated; future surveys will be in new files.

## 1. Individual ecosystems

| Ecosystem | Integration approach | Execution location | Capability declaration | Built-in safety | Source |
|:---|:---|:---|:---|:---|:---|
| **Meta Muse Gadgets** (released 2026-10-02, Apache-2.0) | ESP32 SDK (C, ESP-IDF) and Linux service; gadget opens outbound connection to Muse and maintains it | On gadget; agent runs on Muse side | Commands declared in `COMMAND_SPECS` (description, parameters, timeout); community skills are Markdown | Pairing confirmed on app; commands run under non-root account. Linux SDK bundles `system.run`, `file.write`. No allowlist or per-command confirmation observed | [muse-gadget-sdk](https://github.com/facebookincubator/muse-gadget-sdk) · [`linux/AGENTS.md`](https://raw.githubusercontent.com/facebookincubator/muse-gadget-sdk/main/linux/AGENTS.md) |
| **Muse Home Link** | USB-C device on home network, calls local HTTP APIs (TVs, speakers…) | Local network | Markdown skill | Not described | [unite.ai](https://www.unite.ai/meta-open-sources-muse-gadget-sdks-for-diy-ai-hardware-devices/) *(secondary)* |
| **MCP** (spec 2026-07-28) | JSON-RPC over Streamable HTTP or stdio | Where MCP server runs | `tools/list`, `inputSchema`/`outputSchema` JSON Schema 2020-12 | OAuth 2.1 is **optional**; human approval is only SHOULD; tool annotations "MUST be considered untrusted" | [spec — tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) · [roadmap](https://blog.modelcontextprotocol.io/posts/mcp-roadmap/) |
| **Anthropic MHS** (Model Hardware Standard) | Edge driver, called via MCP, CLI, or code API | In driver | Manifest: sensed quantities, controlled quantities, bounds | Limits, interlocks, approvals reside **within vendor's driver**. Preview (announced 2026-08-27); open source "planned", no repo or license yet | [modelhardwarestandard.com](https://modelhardwarestandard.com) |
| **Home Assistant** | `/api/mcp` (MCP server, Streamable HTTP); HA also acts as MCP client; Wyoming voice-only | Local hub | "Exposed" entities | Exposed by **entity**, not by value; no per-action confirmation observed | [mcp_server](https://www.home-assistant.io/integrations/mcp_server) · [expose](https://www.home-assistant.io/voice_control/voice_remote_expose_devices/) |
| **ESPHome** | Native TCP + protobuf API, Noise encryption with PSK | On chip | `api.proto`; YAML actions turned into services | HA authorizes action execution per device | [esphome API](https://esphome.io/components/api/) |
| **Matter 1.6** | Clusters over IP (Wi-Fi, Thread, Ethernet) | On device; controller issues commands | Cluster and attribute model | Device attestation, commissioning; ACL cannot express **value bounds** | [Matter](https://en.wikipedia.org/wiki/Matter_(standard)) *(secondary)* |
| **Amazon Alexa+** | MCP Toolkit: add-on connects to your MCP server | Your MCP server | Standard MCP tools | Account linking; confirmation flows not described | [MCP Toolkit](https://developer.amazon.com/docs/alexaplus/add-ons/mcp-toolkit-overview.html) |
| **Google Home APIs / Gemini for Home** | Android/iOS SDK, Matter, cloud-to-cloud | Unspecified whether local or cloud | Matter device types | Not described | [Google Developers Blog](https://developers.googleblog.com/en/empowering-service-providers-and-hardware-partners-with-gemini-for-home) |
| **Apple** (iOS 27) | App Intents is only route Siri calls into apps | Device or Private Cloud Compute | `@AppIntent` | Siri confirms intents with side effects; no agent API for accessories observed | [WWDC26 343](https://developer.apple.com/videos/play/wwdc2026/343/) |
| **ESP-Claw** (Espressif, Apache-2.0) | Cloud LLM writes Lua executing on chip; MCP server and client | On chip (Lua) | MCP + Lua modules | Sandbox or confirmation not described | [esp-claw](https://github.com/espressif/esp-claw) |
| **xiaozhi-esp32** (MIT) | MCP (JSON-RPC) wrapped in WebSocket or MQTT+UDP to cloud | On chip; LLM in cloud | `AddTool` + `inputSchema`; `AddUserOnlyTool` hides tools from AI | User-tool tier only | [mcp-protocol.md](https://raw.githubusercontent.com/78/xiaozhi-esp32/main/docs/mcp-protocol.md) |
| **ROS 2 + ROSA**, LeRobot | LangChain tools wrapping ROS; Python robotics layers | Robot computer | `@tool` with docstrings | ROSA: node/topic blocklist, actuation tools omitted by default | [nasa-jpl/rosa](https://github.com/nasa-jpl/rosa) |
| **Safety layers for physical agents** | `safety-harness` (reference, Python, fail-closed default); Safe Hands (Cedar gates for LeRobot arms, unmaintained) | — | — | Only two niche projects have gates; no shared trace format | [safety-harness](https://github.com/arkonahomerobotics/safety-harness) |

## 2. Four integration forms and gate placement

| # | Form | Examples | Where to place gate so no command reaches hardware without passing through it |
|:---:|:---|:---|:---|
| 1 | Agent calls tools via MCP | Home Assistant, Alexa+, ESP-Claw, xiaozhi, MHS | **MCP proxy** fronting real server; real server only listens on routes reachable by proxy |
| 2 | Device calls out to vendor cloud | Muse Gadgets, xiaozhi | **On-device dispatcher** between transport and driver; strip raw commands (`system.run`) |
| 3 | Local hub / HTTP, pub/sub | Home Assistant, ESPHome, Muse Home Link, Matter, MQTT | **Reverse proxy** in front of API, or **bridge acting as controller** that replays only gated commands |
| 4 | Robotics middleware | ROS 2, LeRobot | **Interception node** between planner and controller |

LLM-generated code executing on devices (ESP-Claw, Muse's `system.run`) is a special case: tool boundary is
already too late; gate must reside at HAL layer invoked by that code.

## 3. What no ecosystem possesses

- **Value-based bounds, directly on-device.** Muse skills are Markdown; `system.run` is arbitrary shell; Home Assistant
  exposes by entity; Matter lacks value bounds; MHS leaves bounds inside vendor drivers.
- **Mandatory confirmation.** MCP only states SHOULD; Apple confirms in Siri; ESP-Claw lacks it.
- **Fail-closed on error by default.** Only `safety-harness` (reference project, no users).
- **Replayable traces under a common format.** MCP only advises clients to log; no shared format.
- **Identity separated from permissions.** Muse token "is an identifier, not a password"; ESPHome PSK is shared.

## 4. Risks for a standalone safety layer

- **MHS may become industry standard for bounds.** Recommended direction: import MHS manifests as source for bounds and facts,
  positioned at gate and trace layer above drivers — complementary, not competing (`TODOS.md` #33).
- **Closed or cloud-hosted stacks** (Google, Alexa cloud-to-cloud, Apple): gates can only be inserted if user
  maintains hub or firmware.
- **Rapid protocol changes** (MCP 2026-07-28 dropping sessions and SSE): adapters must remain thin, tracking `tools/call` semantics.
- **Platform-side confirmation deemed "sufficient"** for consumer goods, despite being client-side and bypassable.
- **MCUs cannot run Python gates:** core requires C (already implemented as `ne_gate`).

## 5. Implications for NeuroEdge

Four universal adapters — MCP proxy, on-device dispatcher (bridge), reverse proxy/bridge, robotics node — cover
most of the market; each new ecosystem requires only a thin plugin on one of the four forms. What NeuroEdge
sells is the **unmet capabilities** in §3: value-based gates, fail-closed, shared traces — provided the core remains
independently usable with open attachment points. Decision: Q-67; architecture: `docs/architecture/vi/16-ecosystem-landscape.md` §4.
