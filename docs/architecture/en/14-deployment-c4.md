# 14 · Deployment (C4 deployment)

> **Scope:** which machine each container of [`02`](02-container-c4l2.md) runs on, in what environment,
> and what connects them — today and when the boards arrive. **Sources:** `.github/workflows/`,
> `scripts/`, `boards/`, `targets/esp32s3/components/ne_ota/Kconfig`,
> `python/neuroedge/models/providers/config.py`.

## 1. The picture

![E-08 · Deployment](../assets/svg/E-08-deployment.svg)
*Figure E-08 — Three zones: the engineer's machine, GitHub's CI machine, the device; plus a dashed "home machine" zone (Pi, mini PC or NAS) running the operating agent, together with chat platforms, the relay and the Hub index — `planned · Q-72`. The `○ planned` blocks have no hardware or no code yet.*

NeuroEdge has **no server-side service at all** before the v1.1 service tier (I0–I8): no account, no broker, no
backend. Everything runs on the user's machine or on the device. The first server-side service is Fleet
OS at I9 ([`13`](13-evolution-i0-i18.md) §3, milestone 9).

`planned · Q-72` ([Q-72](../../../roadmap/neuroedge-prd.md#15-sổ-quyết-định)): the Blueprint positioning adds a **home machine** node running 24/7 and two
things off the user's machine, both optional and **never on the safety path**: the Hub index (a static git repository,
not a service, I2e) and the relay (the only service NeuroEdge operates before v1.1, which only forwards TLS packets
and does not decrypt). Design: [`15`](15-target-architecture.md) §6.

## 2. Deployment nodes

| Node | Environment | Runs | Status |
|:---|:---|:---|:---|
| **Engineer's machine** | macOS or Linux, Python 3.11+, `python/.venv` | the `neuroedge` CLI and library, `sim` target, `mcp serve`, pytest | ✅ |
| **Browser** | same machine | the `sim` page of `--ui`, served **on 127.0.0.1 only** (`sim/ui.py`) | ✅ |
| **Claude Desktop** (or another MCP client) | same machine | starts `neuroedge mcp serve` as a child process, speaks stdio | ✅ |
| **Docker `espressif/idf:v5.4`** | same machine or CI runner | builds ESP-IDF firmware, Espressif QEMU; `scripts/qemu_boot.sh`, `qemu_ota.sh`, `run_ui_golden.sh` | ✅ |
| **GitHub Actions** | `ubuntu-latest` | the five workflows in §3 | ✅ |
| **Self-hosted runner with a Box-3** | label `[self-hosted, esp32s3-box-3]` | the `memory-spike` job of `nightly-hardware.yml` | ○ planned (TSK-S1-10, TSK-S4-05) |
| **Raspberry Pi 5 + I2S HAT** | Linux, profile `boards/linux-rpi5.toml` | `neuroedge --target linux`: libgpiod, hwmon, audio | ○ planned (TSK-I2-01) |
| **ESP32-S3-BOX-3** | firmware from `neuroedge build --target esp32s3` | on-chip gate, UART trace to the host, OTA | ○ planned (TSK-S4-12) — already runs on QEMU |
| **OTA image server** | any static HTTP(S) server | serves signed application images | ✅ on QEMU (`qemu_ota.sh` uses `python3 -m http.server` on 127.0.0.1) |
| **Model and speech providers** | external services over HTTPS | language model, STT, TTS, Jev | ✅ optional; no network calls by default |
| **Home machine** (Pi, mini PC or NAS) | Linux, systemd; runs simulation G1 `sim` or G2 `linux` on `gpio-sim` before real hardware exists | **trusted 24/7 runtime** (systemd service, restarted when it dies): HAL, gate, mission contract execution, scheduling, deterministic detectors, chat channel adapters and approval record checks, egress, segmented traces | ○ planned · Q-72 · I2d |
| **LLM worker** | same home machine, **its own operating-system user**, not in the `gpio`/`i2c` groups; firewall allows outbound only to the declared provider endpoint | holds the BYOK key, calls the runtime over local MCP as an MCP client (source assigned by the runtime); never approves | ○ planned · Q-72 · I2d |
| **Chat platforms** (Telegram first; Slack, Zalo later) | third-party cloud | receives proactive reports and approval requests, sends commands and approval replies back to the runtime | ○ planned · Q-72 · I2d |
| **Relay** (optional) | server operated by NeuroEdge | TLS pass-through pipe that picks the destination by SNI, without decrypting (Nabu Casa's SniTun pattern); holds trace backup blobs encrypted on the home machine | ○ planned · Q-72 (outside I2d, I2e) |
| **Hub index** | static git repository, read over HTTPS | lists the URL, whole-package digest and "unsigned" evidence of each NeuroEdge Blueprint; packages live in the seller's repository | ○ planned · Q-72 · I2e |

What blocks these today is in roadmap §0.1 ("Chặn ngoài tầm kỹ thuật").

## 3. CI: what each job proves

| Workflow | Trigger | Job | Proves |
|:---|:---|:---|:---|
| `ci-sim-linux.yml` | PR, push, manual | `frozen-artifacts` | the seven schemas are valid; gates match `digests.lock`; every gate resolves; the broken-gate corpus stays broken; the three normative traces are valid; board profiles |
| | | `tests` | pytest on Python 3.11, 3.12, 3.13; **fails if any test is skipped** |
| | | `linux-hal` | `LinuxHAL` on a virtual GPIO line (gpio-sim), hwmon sensors (i2c-stub + lm75), a virtual framebuffer (vfb or vkms — GitHub runners have only vkms); `verify --targets sim,linux` |
| | | `wheel-smoke` | the wheel install works, not only the editable install |
| | | `lint` | `ruff check`, `ruff format --check` |
| | | `licence-obligations` | licence obligations (`CHANGELOG.md` §3.9) |
| | | `cloud-extra` | the `neuroedge[cloud]` extra (real LiteLLM) keeps to the Q-11 licence policy; the adapter runs on real returned objects without calling the network |
| | | `ui-golden` | every screen × language of the LVGL UI built on host matches its golden PNG |
| `firmware-qemu.yml` | PR and push touching firmware or engine, nightly, manual | `firmware-qemu` | the firmware boots on QEMU and the gate boot self-test passes; boot heap above the Q-3 floor |
| | | `firmware-size` | the Q-3 static budget: image ≤ 3.5 MB, ≥ 120 KB SRAM free |
| | | `ota-rollback` | signed update, wrong-key refusal, rollback — on QEMU |
| | | `agent-firmware` | a user's new agent builds into firmware and boots on QEMU; an agent the board cannot serve produces no firmware (exit code 1) |
| | | `uart-trace` | the UART trace becomes a valid `trace.v1`, and `verify --targets esp32s3` passes |
| `security.yml` | PR, push, weekly, manual | `pip-audit`, `gitleaks`, `actionlint`, `codeql`, `codeql-c` | known vulnerabilities in the pinned dependency set; no secrets in git history; clean workflows; static analysis of Python and C |
| `release-pypi.yml` | tag `v*.*.*`, PR touching packaging, manual | `build` → `sbom` → `smoke` → `attest` → `publish-*` → `github-release` | sdist and wheel; CycloneDX SBOM; Sigstore provenance; real PyPI at I6 |
| `nightly-hardware.yml` | nightly, manual | `firmware-build`, `upstream-drift`, `drift-issue`, `memory-spike`, `report` | the image fits the OTA slot; upstream dependency drift (never fails the build, Q-32); memory measured on the board when a runner exists |

The concrete steps: the workflow files themselves. Current green/red status: roadmap §0.1.

## 4. Configuration and secrets at deployment

| Thing | Where | Rule |
|:---|:---|:---|
| Provider API keys | environment variables; `agent.toml` records only the variable **name** (`api_key_env`) | a key never lives in an agent file, a trace or the repo |
| OTA server address | `CONFIG_NEUROEDGE_OTA_URL` at build; NVS (namespace `ne_ota`, key `url`) overrides at run time | empty turns the check off; plain HTTP is allowed because the image signature is an integrity check — it gives no confidentiality |
| OTA signing keys | outside the repo; the image carries its signature, and the device checks it with the key that signed the running app | a wrong key ⇒ the image is refused (`ota-rollback`) |
| Target and board choice | `--target`, `--board`, `boards/*.toml` profiles | a profile declares what has been measured, no more ([`11`](11-hal-port-guide.md) §3) |
| Firmware config layers | `sdkconfig.defaults` + `sdkconfig.qemu` / `sdkconfig.ota` | QEMU and the board differ in config layers, not in code |
| The user's LLM key (BYOK) — `planned · Q-72` · I2d | **only** in the LLM worker's environment | the runtime does not hold it and never writes it to the trace; the worker reaches the network only toward the declared provider endpoint |
| Chat bot token — `planned · Q-72` · I2d | in the trusted runtime, not in the worker | the worker cannot read it; if the token leaks, an attacker can send messages but cannot approve, because an approval must also match the paired sender, `nonce`, expiry and digest |
| Relay TLS certificate and key — `planned · Q-72` | on the home machine | the relay never holds the key, so it cannot decrypt; trace backups are encrypted before leaving the machine |
| Traces of the 24/7 runtime — `planned · Q-72` · I2d | the home machine's disk (SD card or SSD) | chain of segments per day or when a size is exceeded; keep **30 days** locally, older segments compressed then deleted or exported through the relay encrypted; flushed on a timer (about 10 seconds, configurable) and **immediately** on a blocking verdict or an approval; a power loss loses at most the tail of ordinary events, and `replay` reports a truncated segment; the 30-day size is measured on G1 `sim` before it is written into the NFRs |

## 5. Connections between nodes

| From → to | Protocol | Notes |
|:---|:---|:---|
| `neuroedge` → browser | HTTP + SSE on 127.0.0.1 | does not open to the network |
| Claude Desktop → `mcp serve` | MCP over stdio | network transport: `--http` (TSK-P2-04), other machines over mTLS, not Claude Desktop |
| `neuroedge` → Docker IDF | `neuroedge build --target esp32s3` generates the project; ESP-IDF builds inside the container | |
| Box-3 → host | UART, `NE1` lines | `record`/`verify --port` reads; baud and console still open (`TODOS.md` #35) |
| Box-3 → OTA server | HTTP(S) GET of the signed image | real Wi-Fi not connected yet (`TODOS.md` #50) |
| `neuroedge` → provider | HTTPS; `http://` only for a server on this same machine | per-client details: [`01`](01-context-c4l1.md) §3 |
| LLM worker → runtime — `planned · Q-72` · I2d | local MCP (stdio or Unix socket) | source assigned by the runtime per connection; every call goes through the gate like `mcp` |
| LLM worker → LLM provider — `planned · Q-72` · I2d | HTTPS, only to the declared endpoint (blocked at the operating-system level) | undeclared destinations are blocked and traced |
| Runtime ↔ chat platform — `planned · Q-72` · I2d | HTTPS to the platform's API (long polling or webhook) | API failure ⇒ bounded queue + local alert on the UI |
| Home machine → relay — `planned · Q-72` | outbound TLS opened by the home machine; the relay forwards by SNI | no port opened on the home network; approvals do not go through the relay, and a remotely opened page may not answer `ask` until the relay RFC settles authentication ([`15`](15-target-architecture.md) §6.5); if the relay is lost, the safety part keeps running |
| CLI → Hub index — `planned · Q-72` · I2e | HTTPS (git) to the package URL, whole-package digest checked at install | digest mismatch ⇒ install refused |

## 6. Not deployed yet

- **No NeuroEdge servers before v1.1** — except the optional Q-72 relay (`planned`, a bounded exception to Q-10: no decryption, not on the safety path). Batched OTA rollout (Hawkbit), MQTT broker, incident trace store, device identity are Fleet OS (I9); gate storage and distribution is Gate Registry (I10) — server deployment structure details: [`15`](15-target-architecture.md) §3.1/§3.2.
- **Layered robotics clusters not deployed yet.** Layered structure comprising Raspberry Pi 5 as the brain connecting to dedicated microcontroller nodes ESP32-S3 and RP2350 via Zenoh-pico communication bus (I14, Q-32, Q-33, Q-36) — network node layout details: [`15`](15-target-architecture.md) §4.3.
- **Jetson vision inference node not deployed yet.** Target `jetson` (tier 2, I16) (tier 2 per FR-TGT-08, Q-13) runs vision via JetPack and TensorRT (`neuroedge-design-phase2.md` §7, TSK-V2-01) — hardware deployment details: [`15`](15-target-architecture.md) §4.4.
- **Lab mode over MCP not deployed yet (I4a, Q-71).** When it is, the MCP client (Claude Code, Claude Desktop) and the `mcp serve` process that holds the device must be permission-separated: the client is not in the `gpio`/`i2c` groups — the main path is stdio over SSH with a `restrict,command=…` key, or `mcp serve` as its own user (`mcp serve --http` only when the client can present an mTLS client certificate); `mcp serve` loads policy from a reviewed checkout the client cannot write; gates are locked only through a PR on a protected branch — details: [`15`](15-target-architecture.md) §4.2, `docs/spec/threat_model.md` §2c.
- **24/7 home machine not deployed yet (`planned · Q-72`, I2d, I2e).** Today no background process runs forever ([`02`](02-container-c4l2.md) §3). The 24/7 runtime, LLM worker, chat platforms, Hub index and relay above are design: [`15`](15-target-architecture.md) §6. Simulation runs first (G1 `sim`, G2 `linux` on `gpio-sim`, G3 ESP32 firmware on Espressif QEMU — Wokwi, Velxio pending a re-check against Q-21, Q-69, G4 ESPHome host); real hardware is bought later.
- **No real board in CI.** All chip evidence today is QEMU and C tests on host; evidence on silicon waits for the board and the self-hosted runner (`TODOS.md` #10).
- **Not released to PyPI yet.** The workflow exists; the real release is at I6.
