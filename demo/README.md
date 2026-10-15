# Demo catalog by increment — NeuroEdge

The `demo/` directory collects demo scenarios and prepared commands for each milestone of the NeuroEdge project. Per decision Q-49, each increment ships with a demo in `demo/<increment>/`, runnable via real commands, recording the re-run commit; this rule is verified during review before completing an increment. The documentation helps presenters showcase current NeuroEdge capabilities live to audiences outside the engineering team.

## Demos

| Increment | Directory | Status | Where to run | Last re-run |
|:---|:---|:---|:---|:---|
| I1 — **NeuroEdge Studio** (UI) | [`i1-studio/`](i1-studio/) | ready — seven screens verified in browser | local macOS/Linux, `neuroedge studio` | branch `studio/integration` (2026-09-29) |
| I1 — terminal | [`i1-sim/`](i1-sim/) | ready | local macOS/Linux, no hardware needed | `6a69626` (2026-09-29) |
| I3 (boardless portion) + OTA of I7 | [`i3-firmware-qemu/`](i3-firmware-qemu/) | ready | Docker `espressif/idf:v5.4` (Mac Apple Silicon or Linux) | `6a69626` (2026-09-29) |
| I4 (voice on laptop) | [`i4-thoai-laptop/`](i4-thoai-laptop/) | ready — provider path tested live; microphone: tested on presenter machine | local macOS, headphones, `OPENROUTER_API_KEY` | branch `voice/integration` (2026-09-29) |
| I2d — **the fish tank on simulation and emulation** (TSK-I2d-28) | [`i2b-be-ca-gia-lap/`](i2b-be-ca-gia-lap/) | D1 (`sim`) and D4 (chat, `agent -m`) re-run on a Mac; D2 (`linux`) on CI only (no gpio-sim in OrbStack's kernel); D3/D5 (QEMU) re-run on a Mac in Docker (87 s) and on CI | laptop; Linux VM or CI log; Docker `espressif/idf:v5.4` or CI log | branch `feat/aquarium-demos` (2026-10-15) |
| I2d/I2f — **chat controlling light and door via NeuroEdge Cloud** (Q-76) | [`i2f-chat-den-cua/`](i2f-chat-den-cua/) | ran all six screens via Telegram (OrbStack as cloud); no video yet, not yet run on real VPS | laptop as box + OrbStack VM or VPS, Telegram bot, OpenRouter key | branch `feat/demo-chat-den-cua` (2026-10-13) |

## Why run locally instead of Docker

The `sim` demo runs directly on the local machine (macOS or Linux) rather than inside a Docker container because the visual UI page `--ui` binds only to the loopback address `127.0.0.1`, and Docker on macOS cannot forward the microphone and speaker directly into containers for audio tasks. Conversely, firmware demos (such as I3) run inside Docker using the same environment image as CI (`espressif/idf:v5.4`). For target `linux`, the system requires a real Linux kernel with the `gpio-sim` module (Linux VM), so this portion is proven via CI run logs (`linux-hal` job).

## Customer interview demos

In addition to technical demos for each increment in this directory, interview demo scenario documents tailored to customer demand segments (≤ 5 minutes per segment, used to validate business hypotheses) are stored at [`docs/business/cong-nhu-cau-2026-10-25/demo.md`](../docs/business/cong-nhu-cau-2026-10-25/demo.md).

## Adding a demo for a new increment

When adding a demo for a new increment per decision Q-49:
- Name the subdirectory following the convention `i<N>-<slug>/` (e.g. `i1-sim/`, `i3-firmware-qemu/`).
- Create a `kich-ban.md` file containing the presenter's narrative, actual typed command blocks, and real system output blocks (truncated using `…`).
- Record the git commit and re-run environment clearly at the top of the scenario file.
- Update the corresponding row in the demo catalog table of this file.
