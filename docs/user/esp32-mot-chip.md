# ESP32-S3 standalone: brain and gate on a single chip

> **Decision:** Q-79 · **Tasks:** TSK-I2f-10 (stage 1, done), TSK-I2f-11, I2f-12 (awaiting board) ·
> **Risks:** [`threat_model.md`](../spec/threat_model.md) §2l. This is the **sole source** describing how
> to use the serial console, safe mode, and where secrets are stored on the chip. Flashing procedure:
> [`nap-firmware.md`](nap-firmware.md).

## 1. Three ways to run the brain, and where this fits

| Run mode | Brain location | Gate location | Isolation | Status |
|:---|:---|:---|:---|:---|
| NeuroEdge Cloud (Q-76) | dedicated instance on cloud (microVM) | home box | two machines | ⏸ I2f |
| Self-hosted (Q-76, Q-78) | NeuroClaw on cheap Linux board | home box | two processes | demo runnable |
| **Single chip (Q-79)** | **ESP32-S3** | **same chip** | **none** — label `risk=single_chip` | stage 1 |

Single chip is the cheapest: just one ESP32-S3, chatting and approving on Telegram. In exchange, the brain and gate share a single memory
space: a bug in brain code could reach the gate. Therefore every LLM tool call still passes through `ne_gate`, and
non-reversible actions require an on-board button or callback from the verified owner (stage 3).

## 2. What Stage 1 has (running on QEMU, not yet on boards)

- **Boot guard.** Each boot self-increments in NVS. If the board stays up for 30 seconds after boot, the counter resets to 0. Three
  consecutive failed boots (crash, self-reset, power loss) trigger **safe mode** on the fourth attempt.
- **Safe mode.** Only the serial console remains active: no networking, no runtime gate, no updates. Pending OTA
  images are never marked valid here, so a subsequent reset causes the bootloader to roll back to the old image.
- **Configuration and secrets** in dedicated NVS partition `ne_config`: Wi-Fi, bot token, owner ID, LLM.
- **Serial console** over USB cable, in both normal mode and safe mode.
- **Stack guard** in CI.

A dedicated on-chip brain already exists: **NeuroClaw-ESP**, in the [`neuroclaw`](https://github.com/letrongminh/neuroclaw)
repository under the `esp32/` directory (MIT). Same workspace and same tools as NeuroClaw on Linux or cloud: Telegram chat exclusively
with the owner, memory in `memory/MEMORY.md`, daily notes, `USER.md`/`SOUL.md` files, skills, conversations persisting across
reboots with summaries of older context, `cron` schedule reminders, heartbeat, web search and page reading (without touching local network),
proactive messaging or sending files to the owner, and a fallback LLM when the primary LLM fails.
It already runs on QEMU with an emulated gate; comparison table with the Go version is at `esp32/README.md` in that repo.

**With the brain in the image** (`neuroedge build --target esp32s3 --brain neuroclaw`, Q-83 Profile B,
[`deployment_profiles.md`](../spec/deployment_profiles.md)): NeuroClaw-ESP starts on the bridge from the keys below, the image
connects Wi-Fi from `wifi.ssid` / `wifi.pass` (the brain never starts it itself), prints `risk=single_chip` at boot and in
`status`, and refuses an update whose bridge does not answer. Checked on QEMU in CI (`firmware-qemu.yml` job `brain-firmware`);
not yet on a board (TSK-S4-01: GPIO numbers and sensors; until then pins print `NE_PIN` lines).

## 3. Serial console

Open using `idf.py monitor` (or `screen /dev/ttyUSB0 115200`). The prompt is `neuroedge>`, or
`neuroedge(safe)>` in safe mode.

| Command | Action |
|:---|:---|
| `status` | Mode, boot count, storage type, free heap, remaining stack |
| `config list` | All keys; secrets shown as `<secret>`, unset keys shown as `<unset>` |
| `config get <key>` | Single key |
| `config set <key> <value>` | Set standard key |
| `config set <secret key>` | Prompt value at **hidden prompt**: no characters displayed, omitted from command history |
| `config unset <key>` | Unset a key |
| `config ack readable_flash` | Without flash encryption: say you know secrets can be read back from the chip; until then `config set <secret key>` is refused (`reason=risk_not_acknowledged`, DP-B-17) |
| `bootguard` · `bootguard clear` | View counter · reset (then `reboot` to exit safe mode) |
| `reboot` | Reboot |
| `factory-reset confirm` | Erase all configuration and secrets, reset counter, reboot |
| `help` | List commands |

Without the brain, no command toggles pins or invokes tools. With it, the same console also holds:

| Command | Action |
|:---|:---|
| `button <action> [key=value …]` | A board button bound to an action: decided by the gate like any call, with or without Wi-Fi (DP-B-16) |
| `button <confirm_N> yes\|no` | The board's answer to the question it shows (DP-B-07) |
| `tasks` | Each task's lowest free stack (`NE_STACK` lines) |
| `fact <name> <value>` | QEMU builds only: stands in for the board's sensors |
| `memory_read`, `diag`, `llm_limit`, … | NeuroClaw-ESP's own commands |

**Keys:**

| Key | Secret | Rules |
|:---|:---:|:---|
| `wifi.ssid` | | 1–32 bytes |
| `wifi.pass` | ✓ | 8–64 bytes |
| `telegram.token` | ✓ | `<number>:<string>` as provided by @BotFather |
| `telegram.owner` | | Telegram user ID, digits only (obtained from @userinfobot) |
| `llm.url` | | `https://…` (or `http://…`, with label `risk=cleartext_url`: key sent in cleartext) |
| `llm.key` | ✓ | no spaces |
| `llm.model` | | no spaces |
| `llm.fallback_url` | | as `llm.url`; used when the first endpoint fails (one-chip brain, DP-B-10) |
| `llm.fallback_key` | ✓ | no spaces |
| `llm.fallback_model` | | no spaces |
| `search.key` | ✓ | web search API key for the brain, no spaces |
| `tz` | | POSIX time zone, e.g. `ICT-7` |

Typing secrets directly on the command line is rejected (`reason=inline_secret`): typed text displays on screen and enters command
history. Example setting a token:

```text
neuroedge> config set telegram.token
telegram.token (hidden, Enter to finish):
NE_CONFIG SET key=telegram.token storage=plaintext risk=readable_flash
```

## 4. How secrets are stored

| Firmware built with | `ne_config` partition | Label |
|:---|:---|:---|
| `sdkconfig.defaults` (default) | cleartext: anyone holding the board can read tokens and keys | `risk=readable_flash` |
| `sdkconfig.defaults;sdkconfig.secure` | encrypted (key in `nvs_keys` partition, encrypted flash); if encryption fails, nothing is saved | — |

`sdkconfig.secure` enables **flash encryption: first boot burns eFuses, irreversible**. Development mode
can still be reflashed using `idf.py encrypted-flash monitor`. Only enable when you are ready to dedicate that board to this purpose:

```bash
cd targets/esp32s3
idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.secure" set-target esp32s3 build
idf.py flash monitor   # first time: bootloader encrypts flash then reboots
```

CI builds this layer only, without testing on chip.

## 5. Safe mode: what it looks like, how to exit

```text
NE_BOOT count=4 max=4 mode=safe reason=panic
NE_CONSOLE READY mode=safe
SAFE MODE: too many boots in a row did not stay up. ...
neuroedge(safe)> bootguard clear
NE_BOOT CLEARED
neuroedge(safe)> reboot
```

`reason=` is the reset cause of the chip (`poweron`, `sw`, `panic`, `task_wdt`, `brownout`…), indicating why it looped.
If the underlying cause persists, safe mode will trigger again after three attempts. Boot limit can be modified via `CONFIG_NEUROEDGE_BOOT_GUARD_MAX`
(default 4, following zclaw).

## 6. Testing on QEMU

```bash
. $IDF_PATH/export.sh
cd targets/esp32s3
idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.qemu" set-target esp32s3 build
cd ../.. && python3 scripts/qemu_console.py targets/esp32s3/build
```

The script boots six times on the same flash image: three failed boots, the fourth enters safe mode and inputs configuration via
the console, the fifth boots normally with configuration intact, followed by factory reset. Individual logs are located at
`targets/esp32s3/build/console-test/`.

With the brain: build `fixtures/agents/chat-den-cua` with `--brain neuroclaw`, the project's `build/` with the same two
sdkconfig layers, then `python3 scripts/qemu_brain.py <project>/build` (labels, one console, offline buttons, every setting,
the brain starting; logs in `<project>/build/brain-test/`) and
`NEUROEDGE_OTA_PROJECT=<project> NEUROEDGE_OTA_BRAIN=1 scripts/qemu_ota.sh` (the update path, the bridge self-check,
the downgrade refused).

## 7. Sources

Boot guard, NVS encryption mechanism, and stack guard concept ported from [zclaw](https://github.com/tnm/zclaw) (MIT); console
framework adapted from [MimiClaw](https://github.com/memovai/mimiclaw) (MIT). Attributions: [`NOTICE`](../../NOTICE)
items 6, 7.
