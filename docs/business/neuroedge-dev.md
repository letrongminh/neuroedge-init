# `neuroedge dev`: build smart AI things on ESP32 before the board arrives

**Status:** approved design of the Q-94 experiment (2026-10-19, office hours and CEO review). **Owner:** the
product owner. Decisions live in `roadmap/neuroedge-prd.md` §15 (Q-94); tasks, status and exit criteria in
`roadmap/neuroedge-roadmap.md` §4.4.2 (I3b); deferred work in `TODOS.md` #71. This page explains the design and
copies none of those (`CONTRIBUTING.md` §8.1).

## 1. Problem

A maker has an idea for a smart object on an ESP32 and stalls for weeks: the board has to be bought, the firmware
is hard to write and flash, and once a demo works there is no path to keep the AI running as the toy grows into a
system. The founder, who is the first user, stalled on exactly this.

| Need | Today | What is missing |
|:---|:---|:---|
| Try before buying a board | Wokwi, Velxio, Cirkit (browser simulators; some add AI that writes code) | No AI agent runs *in* the simulated device, and no path from the simulation to a real board that keeps running |
| An AI agent on the chip | ESP-Claw, xiaozhi-esp32, MimiClaw | None found starts from a simulator |
| Keep it running | Hand-rolled OTA, watchdogs, Home Assistant | No tool covers simulation → board → long-running operation |

Interest is real (xiaozhi-esp32 has about 28k GitHub stars; Espressif ships ESP-Claw). Demand for this product is
not yet shown; the checkpoint of Q-94 (7) measures it.

## 2. User and wedge

- **User:** a maker who wants an AI-driven object on ESP32 and has no board or no firmware skills yet.
- **Wedge, Sim-to-Silicon:** build and run the idea in simulation, then put the *same* firmware on the real board.
  Running 24/7 and growing into a system is stage 2.
- **One board:** the ESP32-S3-BOX-3 (Q-2). Simulation needs no board; reaching silicon means buying that kit. Other
  boards come after stage 1, one model at a time.

## 3. Stage 1: Sim-to-Silicon

"`neuroedge dev`" names the lifecycle, not a command.

| Step | Command | Behaviour |
|:---|:---|:---|
| 1 | `neuroedge new` | Pick a Blueprint (`--template`) or choose parts from the list below; writes `board.toml` and `agent.toml`. A part the pre-built image has no driver for is refused with a pointer to `neuroedge build`. A supported part with no virtual model is marked "hardware only" and stubbed in simulation |
| 2 | `neuroedge sim` | Runs the pre-built Box-3 image in a pinned esp32sim, configured at run time from the two TOML files and the secret store. No Docker and no ESP-IDF on the user's machine. Studio shows pins and the screen |
| 3 | `neuroedge flash` | Flashes the same image and configuration to a real Box-3 over USB, then reads the boot line and `NE_SELFTEST PASS` over serial |

**Parts of the pre-built image:** digital output (relay, LED), digital input (button, reed switch), PWM output
(dimmer, servo), analog input (ADC sensor), and the Box-3's own screen, touch, speaker and microphones. A part that
needs a bus driver outside the image (I2C, SPI or UART) goes through `neuroedge build`.

**Brain and network.** The brain is NeuroClaw-ESP, the only one that already emits NE1 traces and calls the gate; it
calls a cloud LLM. esp32sim documents a virtual access point and a NAT mode, but joining the AP, DHCP, DNS and TLS
are unverified. If NAT fails, a host bridge exposes the simulated device's console and MCP on a local socket and the
LLM call runs on the host; parity between simulation and board then covers the gate, pins and screen, not the
device's Wi-Fi, TLS and memory pressure.

**Input and output in simulation.** Pins, screen (pixel-exact against the host goldens), touch and speaker work in
the Box-3 board prototype. Stage 1 also builds the simulator's microphone path (full-duplex I2S, WAV input) as
tooling; the firmware voice channel is TSK-I2f-19 on Q-93's track, so stage 1 users talk to the agent by chat.

**Secrets.** The Wi-Fi password and LLM key never enter `board.toml`, `agent.toml` or a Blueprint. `neuroedge` keeps
them in the OS keychain (fallback: a git-ignored `.neuroedge/secrets` with mode 0600), writes them to the simulated
NVS and, on `flash`, to the board's `ne_config` partition. That partition is plaintext today and the firmware labels
it `risk=readable_flash`; NVS encryption is stage 2.

**Flashing.** The Box-3 uses the ESP32-S3's native USB: no vendor driver on macOS or Windows; on Linux the user must
be in `dialout` (or have a udev rule), which `flash` checks. With no port found, `flash` explains download mode
(hold BOOT, press RESET); with several, it lists them or takes `--port`. Our partition table
(`targets/esp32s3/partitions.csv`) overwrites the Box-3's factory demo, and `flash` says so before writing. A failed
write is recovered from ROM download mode, which cannot be overwritten.

**Gate.** Today's semantics, unchanged: every action goes dispatch → gate → token → HAL. Blueprints ship ALLOW gates
for their harmless parts, so a Blueprint user normally sees no prompt. Hiding the gate by default (an output that
can cause real harm, or is unclassified, is gated; the user opts out explicitly) changes gate resolution semantics,
so it is an RFC written in stage 1 and built in stage 2.

**What "same firmware" is checked against.** The built-in normative trace sessions (`NE_TRACE`, deterministic, no
network) must give the same NE1 trace on the board and in simulation, with `offset_ms`, `boot_id` and `device_id`
masked. A live run with a cloud LLM is not deterministic and is not compared. On 2026-10-19 esp32sim matched QEMU's
93 events (`docs/reports/esp32sim-velxio-spike-2026-10-19.md`); the board comparison is still to be done.

## 4. Stage 2: run and grow

`neuroedge run` keeps the device running (OTA through `ne_ota`, missions), Studio shows health and history, the
hidden-gate default if its RFC passes, NVS encryption, more brains and more boards. A brain other than NeuroClaw-ESP
must emit NE1 traces, route every action through the gate, take its configuration from `agent.toml` and support
`ne_ota`. Stage 2 is planned only if the checkpoint adopts the positioning (`TODOS.md` #71).

## 5. Distribution

- `neuroedge` on PyPI (existing `release-pypi.yml`).
- The pre-built Box-3 image and a pinned esp32sim binary per platform as GitHub Release assets, downloaded on the
  first `neuroedge sim` and checked against a pinned checksum.
- esp32sim has no releases upstream and is MIT-licensed, so we keep a fork with the Box-3 board, the duplex I2S fix,
  WAV input and a non-zero exit on a panic loop. Replacing QEMU in the repository's own CI is out of scope.

## 6. Approaches considered

| Approach | Outcome |
|:---|:---|
| A. Browser playground: esp32sim in WebAssembly, pre-built firmware, one-click WebSerial flashing | Not chosen: the founder wants one tool from idea to a long-running device, inside the CLI and Studio |
| **B. `neuroedge dev`, a lifecycle in the CLI** | **Chosen** |
| C. A Blueprint library as the product | Not chosen: it needs good Blueprints before there are users |
| Host `sim` plus a cloud build plus WebSerial (outside voice) | Not chosen: it breaks "the same firmware in simulation and on the board" |

## 7. Risks the design accepts

| Risk | Where it is handled |
|:---|:---|
| esp32sim exits 0 in a panic loop, so a frozen simulation looks healthy | Fork fix in stage 1; `sim` exits non-zero |
| Networking from esp32sim is unverified | Spike first; host bridge as fallback, with its parity stated |
| Run-time configuration of the image is larger than it looks (pins, PWM, ADC, conflicts, fail-closed) | Re-estimated with a one-PWM, one-ADC spike before building |
| The Box-3 is an enclosed kit, and Profile B's roadmap board is the DevKitC N16R8 | Box-3 kept for its screen, touch and audio; the kit's breadboard dock is checked before buying |
| Hiding the gate weakens what makes NeuroEdge trustworthy | Not in stage 1; an RFC must keep the `neuroedge gate lint` invariants |
| Stage 1 costs about three weeks of agent time before any signal | Accepted; the checkpoint closes the experiment if neither signal appears |
