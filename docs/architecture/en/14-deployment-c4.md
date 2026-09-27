# 14 · Deployment (C4 deployment)

> **Scope:** which machine each container of [`02`](02-container-c4l2.md) runs on, in what environment,
> and what connects them — today and when the boards arrive. **Sources:** `.github/workflows/`,
> `scripts/`, `boards/`, `targets/esp32s3/components/ne_ota/Kconfig`,
> `python/neuroedge/models/providers/config.py`.

## 1. The picture

![E-08 · Deployment](../assets/svg/E-08-deployment.svg)
*Figure E-08 — Three zones: the engineer's machine, GitHub's CI machine, the device. The `○ planned` blocks have no hardware yet.*

NeuroEdge has **no server-side service at all** in Phase 1: no account, no broker, no backend.
Everything runs on the user's machine or on the device. The first server-side service is Fleet OS at I9
([`13`](13-evolution-i0-i18.md) §2).

## 2. Deployment nodes

| Node | Environment | Runs | Status |
|:---|:---|:---|:---|
| **Engineer's machine** | macOS or Linux, Python 3.11+, `python/.venv` | the `neuroedge` CLI and library, `sim` target, `mcp serve`, pytest | ✅ |
| **Browser** | same machine | the `sim` page of `--ui`, served **on 127.0.0.1 only** (`sim/ui.py`) | ✅ |
| **Claude Desktop** (or another MCP client) | same machine | starts `neuroedge mcp serve` as a child process, speaks stdio | ✅ |
| **Docker `espressif/idf:v5.4`** | same machine or CI runner | builds ESP-IDF firmware, Espressif QEMU; `scripts/qemu_boot.sh`, `qemu_ota.sh`, `run_ui_golden.sh` | ✅ |
| **GitHub Actions** | `ubuntu-latest` | the five workflows in §3 | ✅ |
| **Self-hosted runner with a Box-3** | label `[self-hosted, esp32s3-box-3]` | the `memory-spike` job of `nightly-hardware.yml` | ○ no runner yet (TSK-S1-10, TSK-S4-05) |
| **Raspberry Pi 5 + I2S HAT** | Linux, profile `boards/linux-rpi5.toml` | `neuroedge --target linux`: libgpiod, hwmon, audio | ○ board has not arrived (TSK-I2-01) |
| **ESP32-S3-BOX-3** | firmware from `neuroedge build --target esp32s3` | on-chip gate, UART trace to the host, OTA | ○ board has not arrived (TSK-S4-12) — already runs on QEMU |
| **OTA image server** | any static HTTP(S) server | serves signed application images | ✅ on QEMU (`qemu_ota.sh` uses `python3 -m http.server` on 127.0.0.1) |
| **Model and speech providers** | external services over HTTPS | language model, STT, TTS, Jev | ✅ optional; no network calls by default |

## 3. CI: what each job proves

| Workflow | Trigger | Job | Proves |
|:---|:---|:---|:---|
| `ci-sim-linux.yml` | PR, push, manual | `frozen-artifacts` | the three schemas are valid; gates match `digests.lock`; every gate resolves; the broken-gate corpus stays broken; the three normative traces are valid; board profiles |
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

## 5. Connections between nodes

| From → to | Protocol | Notes |
|:---|:---|:---|
| `neuroedge` → browser | HTTP + SSE on 127.0.0.1 | does not open to the network |
| Claude Desktop → `mcp serve` | MCP over stdio | network transport deferred (`TODOS.md` #24) |
| `neuroedge` → Docker IDF | `neuroedge build --target esp32s3` generates the project; ESP-IDF builds inside the container | |
| Box-3 → host | UART, `NE1` lines | `record`/`verify --port` reads; baud and console still open (`TODOS.md` #35) |
| Box-3 → OTA server | HTTP(S) GET of the signed image | real Wi-Fi not connected yet (`TODOS.md` #50) |
| `neuroedge` → provider | HTTPS; `http://` only for a server on this same machine | per-client details: [`01`](01-context-c4l1.md) §3 |

## 6. Not deployed yet

- **No NeuroEdge server exists.** Batched OTA rollout, the broker, the trace store and device identity
  are Fleet OS (I9); the gate store is the Gate Registry (I10).
- **No real board in CI.** All chip evidence today is QEMU and C tests on host; evidence on silicon
  waits for the board and the self-hosted runner (`TODOS.md` #10).
- **Not released to PyPI yet.** The workflow exists; the real release is at I6.
