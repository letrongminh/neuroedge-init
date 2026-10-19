# Demo catalog by increment — NeuroEdge

The `demo/` directory collects demo scenarios and prepared commands for each milestone of the NeuroEdge project. Per decision Q-49, each increment ships with a demo in `demo/<increment>/`, runnable via real commands, recording the re-run commit; this rule is verified during review before completing an increment. The documentation helps presenters showcase current NeuroEdge capabilities live to audiences outside the engineering team.

## Demos

| Increment | Directory | Status | Where to run | Last re-run |
|:---|:---|:---|:---|:---|
| I1 — **NeuroEdge Studio** (UI) | [`i1-studio/`](i1-studio/) | paused (Q-72) — seven screens verified in browser | local macOS/Linux, `neuroedge studio` | branch `studio/integration` (2026-09-29) |
| I1 — terminal | [`i1-sim/`](i1-sim/) | ready | local macOS/Linux, no hardware needed | `6a69626` (2026-09-29) |
| I3 (boardless portion) + OTA of I7 | [`i3-firmware-qemu/`](i3-firmware-qemu/) | ready | Docker `espressif/idf:v5.4` (Mac Apple Silicon or Linux) | `6a69626` (2026-09-29) |
| I4 (voice on laptop) | — | removed (Q-77), folder deleted 2026-10-16, see git history | — | — |
| I2d — **the fish tank on simulation and emulation** (TSK-I2d-28) | [`i2b-be-ca-gia-lap/`](i2b-be-ca-gia-lap/) | D1 (`sim`) and D4 (chat, `agent -m`) re-run on a Mac; D2 (`linux`) on CI only (no gpio-sim in OrbStack's kernel); D3/D5 (QEMU) re-run on a Mac in Docker (87 s) and on CI | laptop; Linux VM or CI log; Docker `espressif/idf:v5.4` or CI log | branch `feat/aquarium-demos` (2026-10-15) |
| I2d — **greenhouse on the virtual board** (TSK-I2d-33) | [`i2d-nha-kinh/`](i2d-nha-kinh/) | ready on `sim` — page checked in a browser 2026-10-16 (roof vent opens; closing refused from 35 °C) | local macOS/Linux, `neuroedge run --ui` | 2026-10-16 |
| I2d — **the full fish tank on the virtual board** (TSK-I2d-33) | [`i2d-be-ca-day-du/`](i2d-be-ca-day-du/) | ready on `sim` — page checked in a browser 2026-10-16 | local macOS/Linux, `neuroedge run --ui` | 2026-10-16 |
| I2d/I2f — **chat controlling light and door via NeuroEdge Cloud** (Q-76) | [`i2f-chat-den-cua/`](i2f-chat-den-cua/) | ran all six screens via Telegram (OrbStack as cloud); no video yet, not yet run on real VPS | laptop as box + OrbStack VM or VPS, Telegram bot, OpenRouter key | branch `feat/demo-chat-den-cua` (2026-10-13) |

## Why run locally instead of Docker

The `sim` demo runs directly on the local machine (macOS or Linux) rather than inside a Docker container because the visual UI page `--ui` binds only to the loopback address `127.0.0.1`, and Docker on macOS cannot forward the microphone and speaker directly into containers for audio tasks. Conversely, firmware demos (such as I3) run inside Docker using the same environment image as CI (`espressif/idf:v5.4`). For target `linux`, the system requires a real Linux kernel with the `gpio-sim` module (Linux VM), so this portion is proven via CI run logs (`linux-hal` job).

## What not to say in any demo

Say it plainly if asked. Every row cites its source in the repository.

| Do not claim it already… | What is true today | Source |
|:---|:---|:---|
| Runs on real hardware | No Box-3 or CoreS3 board yet: demos run on `sim` (virtual pins); the chip runs on QEMU and esp-emulator | roadmap §0.1 · Q-92 (4), (5) |
| Talks through a microphone on the device | A real microphone works only on the laptop (`run --mic`, target `sim`); on-chip voice for the all-in-one chip is planned (TSK-I2f-19); demos type text by default (Q-15) | `docs/user/huong-dan.md` §4.5 · Q-93 |
| Understands free-form sentences | Needs `neuroedge[cloud]` and a real key; without `[system_two]` only sentences matching `commands.toml` run; CI tests LiteLLM only with `mock_response` | TSK-S2-11 · `CHANGELOG.md` §3.7 |
| Hands over to a real receptionist (`escalate`) | Blocks, writes the trace, and calls a hook that does nothing | Q-17 · `TODOS.md` #20 |
| Runs on a real Raspberry Pi | `run --target linux` runs on **virtual** GPIO lines (gpio-sim) in CI, not yet on a Pi | `docs/user/huong-dan.md` §5.1 |
| Compares timing across targets | `verify` compares **decisions**, not timing | TSK-S4-04 |
| Updates firmware over a real network | Signed OTA runs only on QEMU; the Box-3 has no Wi-Fi path yet | `docs/user/nap-firmware.md` §6.5 · `TODOS.md` #50 |
| Manages a fleet (staged OTA, dashboards, remote traces) | Fleet OS was removed from the roadmap | Q-77 · roadmap §6 |
| Is certified for functional safety | Not certified and not targeted | `docs/spec/threat_model.md` §3b |
| Signs traces as evidence for third parties | Traces are not signed (approval records are, RFC-0019) | `TODOS.md` #1 |
| Installs with `pip install neuroedge` | Not on PyPI until the public launch; install from source | roadmap §4.7 (I6) |
| Packs and installs a NeuroEdge Blueprint | Planned (I2e); not the same thing as a Home Assistant blueprint | roadmap §4.3.5 |
| Sells Blueprints in a Hub | The Hub is a free static index (I2e); a paid Hub opens only when a maker asks to sell | Q-92 (10) |
| Runs an operator agent 24/7 that reports and proposes | The box's runtime process (`agent run`) is planned (I2d); NeuroClaw runs next to the box | roadmap §4.3.4 |

## Adding a demo for a new increment

When adding a demo for a new increment per decision Q-49:
- Name the subdirectory following the convention `i<N>-<slug>/` (e.g. `i1-sim/`, `i3-firmware-qemu/`).
- Create a `kich-ban.md` file containing the presenter's narrative, actual typed command blocks, and real system output blocks (truncated using `…`).
- Record the git commit and re-run environment clearly at the top of the scenario file.
- Update the corresponding row in the demo catalog table of this file.
