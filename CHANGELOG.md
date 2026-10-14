# Changelog — NeuroEdge

All notable changes to this project are documented here, in the spirit of
[Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/lang/vi/).

> **This file has three parts, read as needed:**
>
> | What you need | Section to read |
> |:---|:---|
> | Know what has changed | [§1 Version Log](#1-version-log) |
> | Run the system immediately | [§2 Operating Guide](#2-operating-guide) |
> | Take over to continue building | [§3 Product Context Handoff](#3-product-context-handoff) |
>
> **The source of truth for progress** remains [`neuroedge-roadmap.md`](roadmap/neuroedge-roadmap.md)
> §0 (tracking table and handoff card). This file recounts *what was built and how it runs*;
> the roadmap recounts *what remains to be built*. Precedence order in case of divergence: §3.1.

---

## 1. Version Log

Each completed task adds or edits **one** entry in `[Unreleased]`, following
`CONTRIBUTING.md` §8.2 step 3. Upon release, rename the heading to the version number and date
([`docs/release.md`](docs/release.md)).

The package has not yet released any public versions; before going public there are only internal tags (Q-39), and the first version on PyPI will be `0.6.0` at I6. Phase 1 documentation milestones are summarized at the end of this section.

### [Unreleased]

#### Added

- **Q-83 — two first-class deployment profiles, one product; SRS with test cases; the local page needs a per-run key.** Profile A (Full: NeuroClaw brain and NeuroEdge box in separate trust domains, MCP over mTLS) and Profile B (One chip: NeuroClaw-ESP and `ne_gate` in one ESP32-S3 image, `risk=single_chip`) share one contract, the tool list and `tool-result.v1`, over two transports; MCP and TLS are not run between brain and gate on one chip. `docs/spec/deployment_profiles.md` is a requirements specification in ISO/IEC/IEEE 29148 form: 36 requirements (DP-COM, DP-A, DP-B, DP-BP, DP-NF), the `nc_gate` ↔ MCP mapping, a C header sketch for `ne_brain_bridge`, and 52 test cases, each either `implemented` (naming a test) or `planned` (naming a task); `test_deployment_profiles_srs.py` keeps them closed. Fixed with it (DP-A-02): any process on the box's machine, a brain with a shell included, could POST `/confirm` with no `Origin` and be recorded as the person at home. Every POST to the `run --ui` page, the `mcp serve --ui` page and Studio now needs the server's `Origin` and `X-NeuroEdge-UI-Key`, a key made for the run and printed only after `#` in the terminal URL; refusals are traced as `ui_auth_refused` (`tool_calling.md` §7). Roadmap: TSK-I2d-08, I2d-09, I2d-11, I2d-12, I2d-24, I2d-25 and I2f-12 re-scoped; new TSK-I2d-26 (contract CI between the repositories), I2d-27 (box System 2 behind a flag), I2f-14 → I2f-17 (one image, QEMU budgets, run-time traces on the chip, Profile B+ evaluation). Architecture chapters 00, 02, 06, 15, 16, poster E-08, the threat model, the glossary and the business page follow. Test count 4908 → 4939.
- **NeuroClaw v0.2.0 → v0.2.2 and NeuroClaw-ESP close to zclaw, MimiClaw (TSK-I2d-22, TSK-I2f-11).** NeuroClaw released v0.2.0, v0.2.1, v0.2.2 ([releases](https://github.com/letrongminh/neuroclaw/releases)): archives for Linux (eight architectures), macOS, Windows, FreeBSD, NetBSD, deb/rpm packages, Android build, `ghcr.io/letrongminh/neuroclaw` image; release notes specify which file to use for which environment. The Go version adds `get_diagnostics` tool (read-only, does not leak keys), hourly and daily LLM call budgets (`agents.defaults.llm_budget`; counts every request including subagents, summarization, fallback; when exhausted, scheduled reminders still send verbatim text with a note), `neuroclaw session list|clear` and `neuroclaw heartbeat run` commands (neuroclaw PR #14). NeuroClaw-ESP adds Anthropic-style LLM per URL, Tavily, `get_diagnostics`, hourly and daily LLM call limits, serial admin console, CPU core pinning, builds for ESP32, S3, C3, C6; host tests run under ASan, UBSan and QEMU e2e in CI (PR #13). NeuroClaw documentation matches code, with installation guides by environment and guides for serving as NeuroEdge brain, in English and nine translations; default workspace and CLI help reference NeuroClaw (PR #12); v0.2.2 finishes fixing banners, CLI notices, channel titles, User-Agent, and MCP client name, retaining saved or protocol names (MQTT, credential keys, WeCom, OAuth) so existing installations do not break (PR #15). Persona, custom tools, WebSocket, web relay are not implemented: Go version already has them (skills, Pico channel, `SOUL.md`) or they are unneeded on chip. Comparison with zclaw, MimiClaw: `docs/reference/capabilities.md` §12 of that repo. Opened TSK-I2f-13: Wi-Fi setup and initial configuration for standalone chip using `wifi_provisioning` with PoP, in NeuroEdge firmware.
- **Q-80 — NeuroClaw has full PicoClaw capabilities.** Removed the hard lock from Q-78: shell, hardware buses, skill installation, commands in cron, process hooks, USB monitoring, MCP stdio are configurable like PicoClaw, defaulting to PicoClaw v0.3.1; each enabled item logs `NeuroClaw risk=<name>` at boot (per Q-73). Web console, launcher, and full multi-platform releases (goreleaser, Docker GHCR, deb/rpm, DMG, nightly) return. Demo `i2f-chat-den-cua` keeps the scoped brain using `config.json` (`test_the_demo_brain_is_configured_closed`); `threat_model.md` §2b, §2g, §2k, §3 explicitly state that an open brain requires worker isolation (TSK-I2d-24).
- **Q-79 — Standalone ESP32-S3, phase 1 (TSK-I2f-10).** The third way to run the brain: brain and gate share a single ESP32-S3, with risk labels (`threat_model.md` §2l); LLM tool calls go through `ne_gate`, never directly to GPIO. Phase 1 ported from zclaw and MimiClaw (MIT, `NOTICE` items 6, 7) four foundational components, running on QEMU: boot guard (`ne_boot`: if three consecutive boots fail to stabilize, the fourth enters safe mode, leaving only the serial console; no network, no gate runtime, does not mark OTA image valid); configuration and secrets in new NVS partition `ne_config` (`ne_config`: encrypted under new overlay `sdkconfig.secure`, does not fall back to plaintext; plaintext receives `risk=readable_flash` label); serial control console (`ne_console`: `status`, `config`, `bootguard`, `reboot`, `factory-reset`; secrets entered at hidden prompt, not echoed to UART, not saved in history); stack guard (`scripts/check_stack_usage.py`: all our functions have static frame ≤ 1024 B, main task has remaining ≥ 512 B on QEMU). Two new partitions sit after `storage`, shifting no offsets. CI `firmware-qemu` adds stack guard, six-boot scenario (`scripts/qemu_console.py`), and flash encryption overlay build. Guide: `docs/user/esp32-mot-chip.md`. The on-chip brain, **NeuroClaw-ESP**, lives in the `neuroclaw` repo (`esp32/`, MIT): shares workspace and tools with NeuroClaw Go — Telegram owner-only, `memory/MEMORY.md`, daily notes, identity files, skills, conversations preserved across reboots with `CONTEXT_SUMMARY`, `cron`, heartbeat, `web_search`, `web_fetch` (denies home network), `message` and `send_file` to owner only, fallback LLM URLs per Go version's switching rules and cooldowns — running on QEMU with dummy gate; connecting to `ne_gate` (TSK-I2f-11, I2f-12) awaits DevKitC board; `llm.fallback.*` keys of `ne_config` implemented concurrently.
- **Q-78 — NeuroClaw, the NeuroEdge brain.** Hard-forked PicoClaw v0.3.1 into NeuroClaw, separate repo [`letrongminh/neuroclaw`](https://github.com/letrongminh/neuroclaw), MIT. Three patches extracted from demo: mTLS for MCP over HTTP (removes bridge), hard-locking all command execution and hardware access paths (lifted in Q-80, replaced with risk labels), and explicitly informing LLM when the box asks the owner; `neuroclaw update` downloads NeuroClaw releases, not PicoClaw releases. Capabilities per component, risk labels, and known vulnerabilities: `docs/reference/capabilities.md` in that repo. Demo `demo/i2f-chat-den-cua/` switched to NeuroClaw (`neuroclaw/config.json`, `chay-nao.sh`); `cau-noi.py` retained for workers unable to present certificates. Real run on laptop: light ALLOW, door asks owner and brain reports waiting, shell commands rejected.
- **Internal demo: chat controls light and door via NeuroEdge Cloud** (`demo/i2f-chat-den-cua/`, TSK-I2d-22). `neuroedge mcp serve --http --ui` now works: remote brain calls tools over mTLS and tokens, while the page on 127.0.0.1 is the person at home, the sole place capable of answering `ask` questions (`tool_calling.md` §8.1). Agent `chat-den-cua`: light toggles freely, door asks owner then opens for 30 seconds; at night or over 30 seconds it blocks without asking. The demo suite includes a stripped-down PicoClaw v0.3.1 config (no shell including via cron and hooks; no i2c, spi, serial; no skill installation; one MCP server is the box), `tao-khoa.py` (CA, certificates, certificate-bound tokens), `cau-noi.py` (mTLS bridge, because PicoClaw's MCP client cannot present certificates), and three scripts to run the demo from `.env.txt`: `chay-hop.sh` (box), `chay-nao.sh` (brain, on VPS or laptop), `dung-vps.sh` (one-command VPS bring-up, copying only the brain's keys). Tests: door does not open from cloud without home approval, even if claiming `call_source` or facts; brain config has no outbound path to the world other than the box's tools; a client sending only headers goes through the bridge to the box and trace replay matches. Completed all six scenarios via Telegram on 2026-10-13, with an OrbStack machine acting as cloud: light responded in 3.0–4.7 s, door opened only after on-page approval, replay matched 18 verdicts; tests K1–K5, C1–C2 passed. Tunnel VPS and video deferred in `TODOS.md` #69.
- **Q-77 — streamlined roadmap.** Removed voice from roadmap (I4, I5), NeuroEdge Lab (I4a, I5a), opening target lists to third parties, and all increments after Beta (I9, I10, I13, I14, I16, I17, I18, Block 4, Block 5). Their tasks are reduced to one line per task in roadmap §6 with reopen criteria; existing voice code remains intact. MVP v1.0 rewritten: A6 measures without voice, A11 dropped. Release milestones reduced to eight; Appendix A (old sprint mapping) dropped. Figures E-01, E-02, E-04, E-07, E-09, E-10, E-11 redrawn.
- **Architecture streamlined from 17 down to 10 chapters (Q-77).** Context merged into `00` §9, deployment into `02` §6, porting guide into `10` §7, variation points and architectural debt into `15` §8–§9; dropped three chapters that duplicated PRD §9, PRD §15, and `python/README.md`. Chapter 15 condensed removed sections into one-line pointers. Old version: `git show f7278fc:docs/architecture/vi/<tệp>`.
- **Q-76 — NeuroEdge brain: self-hosted or NeuroEdge Cloud.** LLM worker PicoClaw-style (chat, LLM, memory, schedule; shell and hardware tools per config, with risk labels — Q-80), touching home devices only via MCP to runtime. Same software runs self-hosted on inexpensive Linux boards or on NeuroEdge Cloud, one isolated instance per user. Irreversible action approvals signed by passkey on phone, verified by box locally (FR-CH-08). Tasks: TSK-I2d-22 → I2d-24, TSK-I2f-02, TSK-I2f-07 → I2f-09; FR-AGT-12. Positioning statement deferred to planned Q-77 (`TODOS.md` #67).
- **Maximize porting from open-source code per task (roadmap §3.11).** Each uncompleted task in I2d, I2e, I2f, I3a has candidate libraries or projects to borrow, with verified licenses: PicoClaw, aiogram, APScheduler, Frigate, pi-gen, wifi-connect, copier, NATS, Firecracker/gVisor, py_webauthn, nanopb, esp-dl, C code from zclaw/MimiClaw. Excluded python-telegram-bot (LGPL) and Ultralytics (AGPL).
- **Testing positioning message with makers.** Positioning review on 2026-10-12 selected hybrid direction: NeuroEdge is the runtime for any agent controlling physical hardware, users see the outcome narrative. Three test messages ("Runtime cho AI điều khiển đồ thật" (Runtime for AI controlling physical hardware), "AI nói hay. Thiết bị phải làm đúng" (AI speaks well. Devices must act right), "Thử thiết bị AI trên giả lập trước khi nó chạm vào đời thật" (Test AI devices in simulation before they touch the real world)) added to the Maker interview kit (`phong-van.md` §5c) with selection rule `M-MSG`; finalize after the demand gate (`TODOS.md` #67). Gate tap points in ESP-Claw need verification before mentioning (`TODOS.md` #68).
- **Q-75 — field evidence "host thinks, ESP32 acts".** From two real projects (pesticide spraying robot Pi + ESP32-S3, fish farming fleet Pi + Hailo): minimal Pi ↔ ESP32 link with heartbeat and loss-of-communication reflex promoted to I3a (TSK-I3a-06, TSK-I3a-07); commodity ESP32-S3 boards and Arduino library (TSK-I3a-08, TSK-I3a-09); multi-chip project scaffolding `neuroedge new --layout host+mcu` (TSK-I2e-14); deferred fleet management until users request it (entry condition for I9).
- **Q-74 — optional cloud brain, local spinal cord at home.** Users who only need chat: LLM worker and conversation can run on NeuroEdge Cloud, while gate, reflex, and approval checks always remain in the home box (Pi, Home Assistant add-on, or ESP32-S3 for a single task). Step 1 makes the home box easy to install (TSK-I2e-12, TSK-I2e-13); step 2 opens subscription-based cloud after the demand gate if metrics require (increment I2f, conditional). Documentation follows: PRD §1.2, FR-CH-06, FR-CH-07, FR-AGT-10, FR-AGT-11, §8.4; architecture 15 §6.10, 00, 14; threat model §2k; `tool_calling.md` §6; terminology; roadmap: TSK-I2d-20, TSK-I2d-21 (Q-73), TSK-I2e-12, TSK-I2e-13, increment I2f (TSK-I2f-01…06), milestone 9 "One chat box for many devices"; figures E-01, E-02, E-08, E-09, E-10, E-11 redrawn.
- **Q-73 — open, with transparency.** Users choose verification methods (including reading code by voice) and multi-step flows; NeuroEdge does not forbid, only clearly displays the risk level. Retained three invariants: AI does not verify on behalf of humans, rules run exactly as declared, traces are recorded. RFC tracked at TSK-I2d-20.
- **Product and architecture documentation per Q-72 — complete before implementation.** PRD 1.6: NeuroEdge Blueprint positioning, maker as early adopter (U1, U5, U8, U9), requirements FR-MSN, FR-AGT, FR-CH, FR-EGR, FR-BP, FR-TRC-11…13, FR-CLI-13…15, LLM cost NFR, criteria A14–A22, demand gates B6–B8 (reversing Q-56). Roadmap adds increment I2d (TSK-I2d-01…19) and I2e (TSK-I2e-01…11). Architecture updated for 24/7 runtime, LLM worker, chat approval, symmetric `safe_state`, and 30-day trace retention.
- **Q-72 — Blueprint positioning: from a single utterance to an AI physical product.** Three-loop positioning: build (MCP), run (operator agent, cost cap, proactive chat alerts), and share/sell (Blueprint, Hub) with makers as the primary user. Approval via paired chat channel (extending Q-26), reinstated 8-week demand gate (reversing Q-56), deferred trace signing before MVP; non-`off` `safe_state` declared in `board.v1`.
- **Q-71 — NeuroEdge Lab via MCP replacing NeuroBrain (TSK-N0-01, TSK-N0-04).** MCP clients (Claude Code, Claude Desktop) draft configurations via lab tools; NeuroEdge grades (`neuroedge lab check`), enforces gate/envelope at runtime, humans approve via PR. Separation of device permissions and trusted channels per threat model §2c; planned package `neuroedge.lab`.
- **Partner testing documentation set (TSK-I2c-19, Q-70).** `docs/user/doi-tac/`: guides for Home Assistant via `proxy mcp`, `neuroedge.guard` in Python, `proxy http` in front of device APIs; `docs/business/doi-tac/`: trial agreement; automated checks via `scripts/partner_guides_check.sh`.
- **Home Assistant plugin for remote actuators (TSK-I2c-16 part B, RFC-0018 §3j).** Repo `letrongminh/neuroedge-homeassistant`: entry point `neuroedge.actuators: home_assistant`, L1 level for switch/light/input_boolean, state confirmation via polling, passes 9/9 conformance tests on mock.
- **Remote actuators — core of RFC-0018 (TSK-I2c-16 part A).** `digital.out` pins declared in `[actuators.<name>]` via `neuroedge.actuators` plugin, reachable only through `_admit`; auto-off levels L0–L3 (irreversible actions require ≥ L2); communication loss becomes `uncertain`; HAL manages shutdown debt; verified via `neuroedge conformance`.
- **`allow_lan_http` for two proxies (Q-70).** The `allow_lan_http = true` option in `[proxy.mcp]` / `[proxy.http]` allows plain HTTP to private address ranges (RFC 1918, link-local, `*.local`, `*.lan`, `*.home.arpa`) for local network devices.
- **`neuroedge proxy http` and `neuroedge guard init --http` (TSK-I2c-15, FR-EXT-06).** Place default-block gates in front of local HTTP APIs via `[[proxy.http.routes]]`; requests forwarded only after an ALLOW verdict; source `bridge:<id>`.
- **`neuroedge proxy mcp` and `neuroedge guard init --mcp` (TSK-I2c-14, FR-EXT-06).** Place default-block gates in front of existing MCP servers via stdio; `guard init --mcp` generates configurations and supports Claude Desktop configuration via `--desktop-config`.
- **`neuroedge.guard` — standalone safety core (TSK-I2c-07, RFC-0016 §3b).** Runs the gate → token → envelope → trace cycle independently without needing `agent.toml` or `SimSession`; `Guard.load("guard.toml")`; supports `TracePlayer` trace replay.
- **Namespaced call sources — TSK-I2c-10 half (a), RFC-0017.** Field `source` accepts `bridge:<id>` and `mcp:<client>`; injects derived fact `call_channel`; updates `schemas/tool-call.v1.json`.
- **Q-70 — private trial with one partner team, without waiting for boards, not on PyPI.** Field-testing the gate tool suite (`proxy mcp`, `neuroedge.guard`, `proxy http`) directly via hand-delivered wheels, satisfying five conditions in roadmap §4.3; handoff card updated with new objective.
- **Overall architecture page for non-technical stakeholders.** Added `docs/business/kien-truc-tong-the.html` describing the five-layer execution backbone, updated ADR Q-69 and CPO dashboard (`scripts/gen_cpo_dashboard.py`).
- **I6 · TSK-I6-05 — integrator contracts in `schemas/` (RFC-0015, Q-66).** Four schemas `tool-call.v1`, `tool-result.v1`, `error.v1`, `error-codes.v1` (17 `NE…` error codes); checks key `schema = "neuroedge.board/v1"`.
- **I2b · TSK-I2b-03 — initial gate library `gates/home/`.** Seven base gates (`door-lock`, `light`, `valve`, `siren`, `hvac`, `camera`, `motor`) locked in `digests.lock`, each with ≥ 3 anti-loosening counter-examples.
- **I2b · TSK-I2b-04 — `neuroedge add action|sensor|device|gate`.** Scaffolds `@action`, sensor, device, or default-block gate, with bidirectional tests and board contract verification.
- **I2b · TSK-I2b-01, TSK-I2b-02 — five hardware kits.** `villa-concierge`, `home-voice`, `factory-monitor`, `gate-camera`, `blinds`: BOM, Pi 5 and ESP32-S3 schematics, golden traces `fixtures/traces/kits/`, guides `docs/user/kit-*.md`.
- **I6 · TSK-I6-05, TSK-I6-07 — approval of RFC-0014 and RFC-0015 (Q-65, Q-66).** Approved integrator contracts in `schemas/` (RFC-0015) and digital facts from external processes on the same machine (RFC-0014).
- **I2a · TSK-V1b-04 — golden inference and board-specific `tolerance` (RFC-0012 §3f).** The `verify` command matches vision inference with golden per model sha256, label, IoU, and score tolerance; deviations raise `NE4002`.
- **I2a — `verify` replays sample agents of all four packs on `sim-rpi5` and `linux-rpi5`.** Added `fine-control` (`fan-pwm`) and `motion` (`rover`) corpora alongside `sensor-pack` and `vision` (RFC-0013 §3f).
- **I6 · TSK-P2-04 — authenticated MCP over network: `neuroedge mcp serve --http` (Q-58, Q-32).** Streamable HTTP with mTLS (TLS 1.3) and device-certificate-bound OAuth 2.1 tokens (NFR-SEC-09, FR-CLI-12).
- **I2a · TSK-I2a-06, TSK-I2a-07 — `board.v1` declares all extended primitives; `sim-rpi5`; `verify` runs per reference board.** Declares `digital_in`, `i2c`, `analog_in`, `motion`, `vision_in`, `pwm`; `verify` runs per (target, board) pair.
- **I2a · TSK-I2a-02, TSK-I2a-03, TSK-I2a-04 — sensor primitives (RFC-0007, RFC-0009).** `digital.in` logic level with reading timestamp; I2C read-only via allow-list (`/dev/i2c-N`); `analog.in` unit-aware measurement into gate via `numeric` condition, out-of-range raises `NE5001`.
- **I2a · TSK-N2-01 → TSK-N2-05 — pin-level safety envelope running live on `sim` and `linux`.** Cycle `require_pin → envelope → authorize → record`; rejection raises `NE1003`; time-based auto-off and write-ahead monitoring.
- **I2a · TSK-V1b-01, TSK-V1b-02, TSK-V1b-03, TSK-V1b-06, TSK-V1b-08 — vision pack (RFC-0012).** Pure Python V4L2 on Linux, virtual camera on `sim`, `VisionPipeline` (missing/stale frame produces BLOCK), sample gate `gates/vision/`, `vision_ref` trace replay without raw images.
- **I2a · TSK-W1-01, TSK-I2a-05 — PWM and motion (RFC-0010, RFC-0011).** PWM mandates `duration_ms`, quantum duty to 0; `motion.*` (motor/servo) managed via single-command lease, `safe_state` on lease expiration or BLOCK.
- **I2a · TSK-W1-02 — `numeric` condition and `NETR` v2 (RFC-0009).** Numeric threshold mandates `unit`, `range`, `max_age_ms`; `NETR` v2 binary structure with 80-byte header and 48-byte numeric table for C walker.
- **I1 · TSK-I1-04 — NeuroEdge Studio: `neuroedge studio` (Q-51).** Seven local web screens on 127.0.0.1: live session, gate what-if, traces, replay, verify, ESP32-S3 (LVGL, QEMU, OTA), and configuration.
- **I4 · TSK-I4-01, TSK-I4-02, TSK-I4-04 — real-time voice and models.** `run --mic` directly on laptop; local fallback wake-word and STT; `SystemOne` swappable via configuration through Jev API (Q-4).
- **I7 · TSK-S6-01…TSK-S6-04 — signed A/B OTA, automatic rollback on QEMU.** Component `ne_ota`: downloads HTTP(S) app images, verifies RSA-3072, switches A/B slots after gate self-test; errors produce `REJECTED`, automatic rollback.
- **I3 · TSK-I3-01, TSK-S4-10, TSK-S4-11 — ESP32-S3 firmware and LVGL interface.** `build --target esp32s3` generates ESP-IDF project containing component `ne_agent`; 9 LVGL v9.6.0 screens with image goldens; static RAM check ≥ 120 KB (Q-3).
- **I2 · D1, TSK-S5-09 — sensors and display on Linux.** Range `bands` in `[sim.sensor_facts]`; reads sysfs hwmon/IIO sensors and outputs framebuffer display `/dev/fbN`.
- **I1 · TSK-I1-03, TSK-W0-02…TSK-W0-04, TSK-W2-07 — tooling and supply chain.** CLI `--help` with examples; scaffolding pre-creates `traces/`; CycloneDX SBOM, `pip-audit` vulnerability scanning, `gitleaks` secrets scanning, provenance signing for wheel/sdist.
- **Foundation phase: execution core, voice FSM, MCP, HAL, and CLI.** Python voice FSM and conformance vectors (TSK-S3-10, TSK-S3-11, TSK-S2-07); `LinuxHAL` and interactive sessions on Linux (TSK-S3-05, TSK-S5-10); System 2 via LiteLLM (TSK-S2-11); Gated Tool Profile and MCP serve stdio/UI (Q-24, TSK-S3-24, TSK-S3-27, TSK-S3-28); `on_block: ask` confirmation (TSK-S3-26, Q-26); C walker for `NETR` v1 and C token ledger (TSK-S4-07, TSK-S4-02); tool suite `record`, `replay`, `test`, `verify`, `gate lint/resolve/explain` (TSK-S3-01…TSK-S3-07, TSK-S3-16…TSK-S3-22); boards `boards/` and sample agents `villa-concierge`, `home-voice`, `factory-monitor` (TSK-S2-01…TSK-S2-05, TSK-S3-08).

#### Fixed

- **Light and door chat demo downloads new NeuroClaw.** `demo/i2f-chat-den-cua/chay-nao.sh` uses goreleaser release filenames (`neuroclaw_Linux_x86_64.tar.gz`…, including macOS Intel), verifies SHA-256 against `neuroclaw_<version>_checksums.txt` before extracting, and pins NeuroClaw v0.2.2; old version pointed to v0.1.0 filename and failed to download subsequent releases.
- **Motion commands no longer incur lease delay from caller name lookup.** `hal/digital.py::_caller` looks up directly from frame (`co_filename`, `f_lineno`) instead of `inspect.stack()`, reducing latency from 28 ms to 0.1 ms, preventing 200 ms lease expiration on `blinds` kit.
- **`mcp serve` terminates boundedly after SIGTERM/SIGHUP.** Added timer thread `SIGNAL_EXIT_GRACE_S = 5 s` to close sessions (record trace, release pins) and decisively exit via `os._exit`, avoiding hung processes.
- **Call source (`call_source`) no longer leaks between overlapping invocations.** Separated fact frames of individual calls in `Conversation.do_with`, without overwriting `call_source` in shared facts.
- **Safety envelope records deterministic on-duration.** Strips microsecond jitter from monotonic clock before rounding up, ensuring consistent recorded on-duration across runs.
- **Operational security and safety.** Sim and studio pages block DNS rebinding by checking `Host` on all requests (FR-TGT-06); strips markdown syntax before feeding text to TTS (TSK-S3-13); fixed missing `ne_ui_text.c` in ESP-IDF component; rejects `NaN`/`±inf` numeric parameters in gates (RFC-0005); treats NaN sensor readings as undefined (D1); escapes Rich markup in CLI to prevent swallowing TOML table names.

#### Changed

- **CPO dashboard folded into the architecture page: progress now shows on the architecture itself.** `docs/business/cpo-dashboard.html` is gone. `scripts/gen_cpo_dashboard.py` became `scripts/gen_architecture_progress.py`, which writes only the blocks between `GENERATED` markers in `docs/business/kien-truc-tong-the.html`, from roadmap §0: a status strip under the headline (date of the figures, current milestone, days to the demand gate, tests, items waiting on a person), one progress bar per increment on the architecture layer it builds (chapter 2), and chapter 11 "Where the product is today" (the eight release milestones on a timeline and as cards, then what is waiting on a person). The rest of the page stays hand-drawn. `test_architecture_progress.py` replaces `test_cpo_dashboard.py`: the blocks must match the roadmap, every increment sits on exactly one layer, every increment belongs to exactly one release milestone. Test count 4910 → 4908.
- **Business architecture page redrawn as a visual overview, Blueprint proposal catches up with NeuroClaw (Q-76 → Q-82).** `docs/business/kien-truc-tong-the.html` is now mostly diagrams (inline SVG), written in English: the big picture with the trust boundary (brain asks, box decides), the five end-to-end layers of `00` §2.1 (code layers L0–L4 folded), the execution backbone, three outcomes of one message (ALLOW, ASK, BLOCK), where the brain runs (self-hosted, Cloud, one chip), one gate on three targets with a capability matrix from `00` §6, the evidence loop, the open platform plug points, the three product loops of Q-72 and the roadmap after Q-77. Each figure links to its E-xx engineering diagram. The page reads like a field guide: a chapter list on the left that marks where you are, serif type, one coral accent for the gate, and a Day / Dusk / automatic theme switch. `proposal-blueprint-2026-10-11.md` keeps its text and gains a status box: Lab left the roadmap (Q-77), the operator agent's LLM worker is NeuroClaw, Q-81, Q-82.
- **Q-82 — positioning: "The Physical AI that really does things, safely by design."** *Really does things*: built to drive relays, valves and door latches, not text on a screen. *Safely by design*: gate, one-time token, fail-closed and envelope, not the model behaving well. The line opens `README.md`, the PRD (header, §1.2), `docs/user/bat-dau.md` and architecture `00` §1; closes `TODOS.md` #67. Interviews still record `M-MSG` as a check.
- **Q-81 — box + NeuroClaw enters 8-week demand gate, thresholds unchanged.** Condition ① counts both a box connected to the NeuroClaw brain, controlling at least one device via chat, as an exemplar Blueprint *home assistant via chat*; ② counts when the box runs on G2 or G3 (`cham-diem.md` §4.0, PRD §11.2). Maker interviews add card D "Nhắn tin cho nhà: việc thường thì làm, việc khó thì hỏi bạn." (Texting your home: does routine tasks, asks you for tough ones) (`phong-van.md` §5c; three-card interviews recorded separately); `demo.md` §5 features a chat demo for Makers. New task TSK-I2d-25: box + NeuroClaw installer package for external users, prior to the first tester. I2f kept ⏸. Considered keeping Q-72 unchanged and pivoting to chat-first (PRD §15).
- **Documentation caught up with NeuroClaw, introductory path for newcomers.** New page `docs/user/bat-dau.md`: one diagram (you → NeuroClaw brain → NeuroEdge box → devices), two repos, what works and what is not yet here, four reading paths, five essential terms — no `Q-N`, `TSK-*` codes. `README.md` opens with the same diagram; `docs/user/README.md`, `docs/architecture/README.md` direct newcomers there first; `00-overview.md` §2 and `huong-dan.md` §1–2 include the brain; diagram E-01 labels NeuroClaw as an MCP client. `15-target-architecture.md` §6.10 describes the brain as it currently exists: NeuroClaw, three run modes (self-hosted, conditional NeuroEdge Cloud, single-chip), and the contract between the two repos — MCP toolset, MCP channel over mTLS, single-chip firmware; diagram E-11 replaces "PicoClaw · planned" box with "NeuroClaw · partial". `README.md` adds *Chat with your home* section; new guide `docs/user/chat-voi-nha.md` (bringing up box, installing and connecting NeuroClaw, choosing open vs. scoped brain); `thuat-ngu.md` updates Brain, NeuroClaw, standalone ESP32-S3.
- **Handoff card objective (roadmap §0.3): complete everything up to v1.0 that requires neither hardware nor humans (2026-10-05).** Divided into four execution lanes: host (I2c, I2d), pre-board firmware, releases, and test harness preparation.
- **Q-69 — peripheral simulation ahead of board arrival (2026-10-05).** Established three time-boxed simulation spikes: `esp-emulator` (TSK-I3-02), `esp32sim` (TSK-I3-03), and fully module-enabled kernel for `linux-hal` (TSK-I2a-08).
- **Q-68 — approval of three open-platform RFCs (2026-10-04).** Approved RFC-0016, RFC-0017, RFC-0018; decided operational constants for remote actuators (`OFF_SLACK_MS`, `max_state_age_ms`); separated Home Assistant adapter into dedicated repository.
- **Q-67 — NeuroEdge becomes open safety layer (2026-10-04).** Added increment I2c (Open Platform) comprising `neuroedge.guard`, Extension SDK, MCP/HTTP proxies, remote actuators; moved conformance corpus to Apache-2.0 (`LICENSING.md`).
- **Q-63 — platform gaps added to I6 (2026-10-02).** Added TSK-I6-06 (public Python surface), expanded TSK-I6-05, and added TSK-I6-07 (RFC on facts from external processes).
- **Q-58 → Q-62 — integration surface, licensing, and release milestones (2026-10-01).** Applied PolyForm Noncommercial 1.0.0 license to code and Apache-2.0 to standards (Q-45, Q-59); roadmap of 10 user release milestones (roadmap §0.5); approved 6 extended primitive RFCs (RFC-0007, RFC-0009…0013); chose M5Stack CoreS3 as second camera board (Q-61).
- **Q-56, Q-57 — re-estimated MVP scope and decided open RFC questions (2026-09-30).** Planned 106 MVP tasks (TSK-I2a-01); moved demand gate milestone (Q-56); resolved open questions across six RFCs following maximal safety principles (Q-57).
- **Q-52 → Q-55 — restructure MVP = full v1.0 (2026-09-30).** Roadmap divided into four phases; brought four extended primitive packs into MVP via increments I2a, I3a, I2b; brought NeuroBrain into MVP via I4a, I5a.
- **Synchronize architecture, roadmap, and operations documentation (2026-09-27 to 2026-09-28).** Consolidated into a single roadmap (Q-39); MECE documentation structure (one truth in one place); updated target architecture documentation by horizon; defaulted to hashing raw text data in traces at source (TSK-I1-01); normative traces carry `gate_digest` (RFC-0008).

#### Removed

- **Documentation minimalism: eliminated duplicate versions, kept one place for each truth.** Removed `en/` architecture tree, `docs/archive/`, old proposal v5.9, and three design notes (Phase 2, open platform, FOFOCA robot). Normative sections of the proposal (§4 API, Appendices A–C) moved to `docs/spec/core_contracts.md`; PF-1…PF-4 filter criteria moved into PRD §14; Lab note became `docs/spec/lab_mcp.md`. Roadmap, CHANGELOG, and PRD §15 compressed, preserving all task codes, decisions, and invariants. Old version: `git show 7626b62:<path>`.
- **Extra `scaffold` (`copier`).** Replaced with a pure Python template generator in `neuroedge new`, removing transitive GPL3 dependency.
- **Parameter `fail_closed` of `ActionContractEngine`.** Fail-closed rule is now determined directly from gate's `fail: open` attribute; errors always return a block verdict.

### Phase 1 Documentation Milestones

Phase 1 (2026-09-21 to 2026-09-23) froze three core schemas (`gate.v1`, `trace.v1`, `board.v1`), implemented gate resolution core (`gate_resolver.py`), safe inheritance mechanism per RFC-0001 and RFC-0004, locked foundational decisions (Q-1 to Q-20), and shifted direction to cloud-first (CR-1.0). Full process details and review minutes are preserved in git history (`git show 7626b62:CHANGELOG.md`).

---

## 2. Operating Guide

### 2.1 Environment Setup

Requires **Python 3.11+** (uses standard library `tomllib`, no external TOML dependency).

```bash
cd python
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q          # expected: 0 failed, 0 skipped
```

Reproducible build (roadmap §3.9):

```bash
.venv/bin/python -m pip install -r requirements-lock.txt
```

Optional: System 2 with real models requires `.venv/bin/python -m pip install -e '.[cloud]'`, configure `[system_two]` in `agent.toml`, and export corresponding API keys. System 1 with Jev configured via `[system_one]` and `OPENROUTER_API_KEY`.

### 2.2 Quick Verification of All Artifacts

Commands run from the **repo root** (`paths.py` self-locates monorepo root):

```bash
V=python/.venv/bin

$V/neuroedge verify                      # expected: all gates resolve, traces validate, tool corpus matches, replay matches; 0 artifacts ⇒ NE4004 (code 1)
$V/neuroedge gate lint                   # expected: ✓ all gates resolved, code 0
$V/neuroedge trace validate fixtures/traces/*.json   # expected: each file VALID
$V/neuroedge board list                  # expected: lists profiles in boards/
python3 scripts/gen_cpo_dashboard.py     # regenerates CPO dashboard (docs/business/cpo-dashboard.html) after source change
$V/python scripts/check_digests.py --check   # expected: ✓ files match digests.lock
```

Inverse assertion — negative corpus **must** continue to fail:

```bash
$V/neuroedge gate lint fixtures/gates/invalid --registry fixtures/gates/registry
# expected: all files in invalid/ failed to resolve · exit code 1
```

### 2.3 CLI Command Reference

**Exit code contract** — CI and Action CI anchor to it:

| Code | Meaning |
|:---:|:---|
| `0` | Check ran and **passed** |
| `1` | Check ran and **failed** |
| `2` | Command (or that specific `--target` of the command) **not implemented yet** |

Code `2` is distinguished from `1` so CI separates "broken" from "not yet present". Currently exiting with code 2: `run` / `mcp serve --target esp32s3` (TSK-S4-01), `run` / `mcp serve --ui --target linux`, `run` / `record --voice-file` along with `--ui`, `replay --target esp32s3` (TSK-S4-04). Unknown target is an error (code 1).

All commands loading gates accept `--registry <dir>` (`-r`), default `gates/`. `--agent` defaults to `./agent.toml` or sample agent `villa-concierge`.

| Command | Primary Function |
|:---|:---|
| `gate resolve <file\|URI>` | Resolve `extends` chain, print effective policy and digest. `--json` for machine reading |
| `gate lint [dir]` | Resolve all gates in directory (default `gates/`, `--registry`) |
| `gate publish <file>` | RFC 8785 canonicalize and print SHA-256 digest (stops at digest, not yet digitally signed) |
| `gate add <URI>` | Add gate from registry and analyze inheritance constraints |
| `gate explain <file\|URI>` | Explain gate for reviewers (criteria, tightening clauses, budget, `on_block`) |
| `trace validate <file…>` | Validate traces against `trace.v1.json` schema |
| `trace show <file>` | Print event timeline of trace |
| `trace view <file>` | Export self-contained HTML visualizing devices, sensors, verdicts, and scrubber bar |
| `trace export <file>` | Export Chrome Trace Event format for Perfetto (`--format chrome`) |
| `board list` / `board show <id>` | List or inspect board capabilities and supported primitives |
| `verify [--targets t]` | Comprehensive verification: gates, tool corpus, normative traces, and replay on each target |
| `build --target <t>` | Check agent ↔ board compatibility, compile gates to `NETR` tree, and generate ESP-IDF firmware |
| `replay <file> [--target t]` | Recompute verdicts and pin commands on real HAL and match against golden |
| `record [--target t]` | Record interactive session to validated trace; defaults to hashing raw text (`--raw` keeps verbatim) |
| `test [dir]` | Run agent's Action CI suite (pytest) |
| `run [--target t]` | Interactive CLI REPL (`-c` one-shot command, `--ui` local web, `--voice-file`, `--mic`) |
| `mcp tools` | Export schemas of `@action`s for MCP or OpenAI function-calling |
| `mcp serve` | MCP server over stdio or network (`--http` mTLS/OAuth 2.1) on `sim` or `linux` |
| `mcp desktop-config` | Generate or write connection configuration for Claude Desktop (`--write`) |
| `new <name> [--template T]` | Scaffold new project from template (`minimal`, `villa-concierge`, `home-voice`, etc.) |
| `add action\|sensor\|device\|gate` | Scaffold code component with default-block gate and bidirectional tests |

`python -m neuroedge …` is equivalent to `neuroedge …`. Detailed instructions and usage examples for each command can be found in [`docs/user/huong-dan.md`](docs/user/huong-dan.md).

### 2.4 Reading an Error Message

All errors have exactly three parts (FR-DX-04): **where** (`where`) · **why** (`why`) · **remediation** (`fix`). Inheritance errors include an additional `rule` line indicating the violated principle.

```
[NE2003] loosens-level@1.0.0 (fixtures/gates/invalid/loosens_level.yaml) -> allow_when.risk_level
  why: loosens the inherited condition: base admits {low}, this gate admits {high, low, medium}
  rule: Appendix B.5 principle 2
  fix: narrow allow_when.risk_level to a subset of the base condition (base clause: {'lte': 'low'}), …
```

List of `NE…` codes, error taxonomy, and occurrence contexts can be found in PRD [Appendix B](roadmap/neuroedge-prd.md#appendix-b--standard-error-code-catalog).

### 2.5 CI

List of workflows and jobs in the continuous integration system:

| Workflow | When | Jobs |
|:---|:---|:---|
| `ci-sim-linux.yml` | Every PR and push to `main` | `frozen-artifacts` · `tests` (Python 3.11/3.12/3.13) · `linux-hal` · `wheel-smoke` · `lint` · `licence-obligations` · `cloud-extra` · `ui-golden` (LVGL on host, TSK-S4-10) |
| `firmware-qemu.yml` | PR/push touching firmware sources (`targets/**`), generator, scripts, or nightly | `firmware-qemu` (boot ESP-IDF 5.4 on Espressif QEMU) · `firmware-size` (check flash budget, SRAM Q-3) · `ota-rollback` (phases a–g, RSA-3072) · `agent-firmware` (build and boot agent firmware) · `uart-trace` (read UART, validate and verify) |
| `release-pypi.yml` | Tag `v*.*.*` or manual dispatch | `build` · `sbom` · `smoke` · `attest` · `publish-testpypi` · `publish-pypi` · `github-release` (procedure in [`docs/release.md`](docs/release.md)) |
| `nightly-hardware.yml` | Nightly or manual dispatch | `firmware-build` (ESP-IDF 5.2.1) · `upstream-drift` · `drift-issue` · `memory-spike` · `report` |
| `security.yml` | Every PR/push, weekly, or manual dispatch | `pip-audit` · `gitleaks` (full history) · `actionlint` · `codeql` (Python, Actions) · `firmware-changed` + `codeql-c` |

Five required green CI gates before merge:
- **Skip test blocking gate:** Fails if any test is skipped (`CONTRIBUTING.md` §5).
- **Inverse assertion:** Entire negative corpus must continue to fail with exact exit code 1 (§2.2).
- **`digests.lock`:** Modifying normative gates without an RFC fails the build (`CONTRIBUTING.md` §3).
- **License gate:** `licence-obligations` checks entire core dependency tree; `cloud-extra` checks Q-11 policy.
- **Format check:** `ruff check .` and `ruff format --check .` in the `lint` job.

### 2.6 Firmware (When Hardware Boards Are Available)

Firmware flashing instructions for agents can be found in [`docs/user/nap-firmware.md`](docs/user/nap-firmware.md). Build sample `home-voice` firmware on device:

```bash
cd targets/esp32s3
idf.py set-target esp32s3
idf.py build
idf.py size --format json2 --output-file build/size.json
idf.py size-components --format json2 --output-file build/size-components.json
python ../../scripts/check_firmware_size.py build/neuroedge-esp32s3-box3.bin \
  --size-json build/size.json --components-json build/size-components.json   # Q-3 budget
idf.py -p /dev/ttyUSB0 flash monitor
```

Look for `NEUROEDGE_MEMORY_JSON` line in the monitor output to record metrics into `docs/reports/memory_spike_report.md`. When physical boards are not yet available, C walker runs on host (`make -C targets/esp32s3/components/ne_gate check-static`) and firmware boots on QEMU per `firmware-qemu.yml`.

---

## 3. Product Context Handoff

This section is for developers or AI agents taking over the project to continue development without re-reading all original documents.

### 3.1 Source of Truth Documents

Map of "what to read when" for developers or agents taking over:

| Document | Main Content | When to Read |
|:---|:---|:---|
| [`neuroedge-roadmap.md`](roadmap/neuroedge-roadmap.md) | **Sole source of truth on progress:** four phases (§0.5), increments I0–I18, task statuses, exit criteria, dependencies, handoff card (§0.3). | **Always read first** |
| [`neuroedge-prd.md`](roadmap/neuroedge-prd.md) | Requirements `FR-*` / `NFR-*`, **§15 is the sole decision log** (`Q-N`), Appendix B catalog of `NE…` error codes. | When needing to know *what must be done* and what was decided |
| [`docs/architecture/`](docs/architecture/README.md) · [`core_contracts.md`](docs/spec/core_contracts.md) | Current and target architectures; API specifications, gates (Appendix B), HAL, traces. | When needing to know *why* and *what format* |
| [`TODOS.md`](TODOS.md) | Catalog of intentionally deferred work with explicit trigger milestones. | Before proposing "missing" work |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution conventions; §3 work requiring RFCs; §6 repository structure; §8 task completion steps. | Before modifying code or structure |
| [`docs/spec/`](docs/spec/) | Normative specifications: core contracts (`core_contracts.md`), Gated Tool Profile, threat model, NeuroEdge Lab (`lab_mcp.md`), conversational FSM, simulation coverage, MCU review. | When changing behavior in corresponding layers |

Documents deleted during minimalism (old proposal, design notes, `docs/archive/`, `en/` architecture): `git show 7626b62:<path>`.

**Order of precedence on divergence:** PRD (requirements, decisions) and `schemas/` + accepted RFCs → roadmap (progress, schedule) → architecture and `docs/spec/` → source code → this file. If code diverges from contract, code is wrong. If design documents say anything about schedule, status, or exit criteria, the roadmap is authoritative (R1).

### 3.2 Architecture Map — What Lives Where

Detailed structure of the source repository can be found in `CONTRIBUTING.md` §6. Four main execution layers:
- **L0:** `python/neuroedge/sim/` — simulation session, CLI, local web UI.
- **L1:** `python/neuroedge/hal/` — hardware abstraction layer (five core and extended primitives).
- **L2:** `python/neuroedge/models/`, `perception/` — conversational FSM, intent classification, LLM/STT/TTS adapters.
- **L3:** `python/neuroedge/engine/`, `actions/` — gate evaluation, token management, contracted action execution.
- **Firmware:** `targets/esp32s3/` — C walker, C token ledger, and on-chip boot logic.

### 3.3 Ten Invariants — Do Not Break

1. **Schema validation is NOT sufficient to conclude a gate is safe.** JSON Schema checks only a single document; safety verification gate is `neuroedge gate lint` (resolves inheritance chain). Unresolved gates must not be loaded onto devices.
2. **Fail-closed is default in all directions.** Absence of `fail` → `closed`. Parent gate `fail: open` and child silent → `closed`. Cannot measure → `INCONCLUSIVE`. Actuation always fails closed; during degradation, actuators enter `safe_state` declared in `board.v1` (default `off`, Q-72).
3. **CEL string `allow_when` must not appear in the inheritance chain.** If monotonic tightening cannot be proven, it must be rejected.
4. **Gate resolution is a pure function.** No clock, network, or randomness dependencies, ensuring `neuroedge verify` produces identical results across all targets.
5. **No CEL evaluator on microcontrollers (Q-9 option A).** Host compiles gates into `NETR` binary tree (RFC-0003, RFC-0009); firmware traverses tree using C99 walker only.
6. **Default reference board for `esp32s3` is ESP32-S3-BOX-3; second reference board (with camera) is M5Stack CoreS3 (RFC-0013, Q-61).** Do not swap to DevKitC so memory verification numbers retain real-world validity.
7. **No `sim` profile may be more capable than the hardware board it mirrors (`SIM_MIRRORS`, RFC-0013).** Preserves parity between simulation and physical hardware.
8. **Trace file extension is `.json` carrying `$schema`.** Do not change to closed binary formats like `.ntrace`.
9. **No strong copyleft in distribution artifacts.** Comply with Q-11 license policy; pin `jsonschema[format-nongpl]`; `neuroedge new` uses pure Python generator (TSK-S3-07), not `copier`.
10. **CLI commands without an underlying engine must exit with code 2, never print fake "PASS".** Strictly adhere to the exit code contract (0: pass, 1: fail, 2: not implemented) to maintain truthfulness of CI and progress reporting.

### 3.4 Blocked Items — Cannot Be Closed by Engineering Effort Alone

| Item | Blocked by | Needs Whom | Unlocks What |
|:---|:---|:---|:---|
| **TSK-S1-10** (I3 criterion 1) | ESP32-S3-BOX-3 board | Hardware purchase | On-chip voice benchmarking → I3, I5 |
| **TSK-I2-01** (I2 criterion 4) | RPi 5 for nightly `linux` | Hardware purchase | Nightly on real hardware → I2 |
| **V6 — second embedded engineer** | Position vacant | Recruiting (Q-39) | Audio parallel with HAL (TSK-S5-01…07) → I5, I7 |
| **`TODOS.md` #43** (CLA) | No CLA text yet | Legal / CPO | Accept external PR contributions (Q-45) |
| **I2b criterion 2** | Needs TTFV tester | Tester (Q-60) | Close I2b acceptance criteria |
| **`TODOS.md` #59** | Needs real hardware to assemble kits | Purchase kits and assemble | Verify BOM and schematics for 5 I2b kits |
| **I6 criterion 7** | Needs two machines for network MCP test | Operator (Q-60) | Close network MCP criteria |

**TSK-S1-10 once board arrives:** vendoring `esp-sr` (AEC/AFE + VAD) and `opus` with license review, patch into `TODO(TSK-S1-10, V2)` in `main.c`, fill out report. Decided rule before measurement: failing any Q-3 threshold **does not cut voice** (Q-44) — open a `Q-N` to replan I5 and adjust v1.0 projection.

### 3.5 Next Steps

See Handoff Card in [`neuroedge-roadmap.md`](roadmap/neuroedge-roadmap.md) §0.3 — the single source tracking next steps and execution order (`CONTRIBUTING.md` §8.1).

### 3.6 Known Design Debt

| # | Design Debt | Needs Resolution At |
|:---:|:---|:---|
| 1 | Cancelling pending commands is currently only supported on `sim` and `linux`; `esp32s3` requires firmware-level cancellation (`voice_fsm.md` §5). | **TSK-S4-01** (I3) |
| 2 | `gate publish` stops at RFC 8785 SHA-256 digest, not yet cryptographically signed. | I10 (Registry) |

### 3.7 What the System Does Not Do Yet

- Interactive sessions currently support only terminal text input on `sim` and `linux` (no web GUI for Linux yet).
- Voice runs from WAV files on `sim`/`linux`; live microphone (`run --mic`) is currently available on laptops; wake-word model is user-provided.
- ESP32-S3 currently runs gate walker and self-test on QEMU, without physical GPIO actuation.
- Cloud models in CI run only via mock/dummy transports; real key invocations require manual runs.
- Target equivalence is currently at the verdict and pin command level; real-time latency is not matched yet.
- Extended primitives are tested on virtual Linux kernels in CI (`gpio-sim`, `i2c-stub`, `vivid`), not yet on physical boards.
- Not yet publicly published on PyPI (planned version `0.6.0` at I6; prior releases are internal tags and hand-delivered wheels only).
- CEL expressions in `allow_when` are not yet supported (`TODOS.md` #42).

### 3.8 Four Constraints for On-Chip HAL Port in I3

Four constraints RB-1 → RB-4 (no `malloc` in audio path, bounded static buffers in PSRAM, `digital.out` cancellable within ≤ 1 audio frame, `const` capability table in flash) defined in [`docs/spec/hal_mcu_review.md`](docs/spec/hal_mcu_review.md) §2 remain in effect.

### 3.9 Adding a Negative Fixture

Procedure and bidirectional closure principles for negative corpora (gates, traces, tool calls) are specified in [`CONTRIBUTING.md`](CONTRIBUTING.md) §3.
