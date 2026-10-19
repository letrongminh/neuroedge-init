# Spike: an ESP32-S3-BOX-3 board in esp32sim (2026-10-19)

Follows [`esp32sim-velxio-spike-2026-10-19.md`](esp32sim-velxio-spike-2026-10-19.md) (branch
`docs/emulator-spike-esp32sim-velxio`), which found that esp32sim runs our unchanged firmware but has no
Box-3 board. Question: how much work would it take for esp32sim to emulate a Box-3 well enough to run the
screen, touch and voice checks (DP-B-18 → DP-B-22, TSK-I7-03) without a board?

**Verdict.** It costs little. A prototype `box3` board took about 2 hours: about 100 lines of Rust plus a
one-line change to the I2S receiver. On it, the Box-3 BSP's own display, touch and audio code runs
unchanged, apart from one SPI host define. Our `ne_ui` approval card renders **pixel-identical to its host
golden image**, and a scripted tap reaches LVGL at the exact coordinates. A 440 Hz tone played through the
ES8311 comes out in the WAV capture. A tone fed to the ES7210 is read back by `esp_codec_dev_read`. To turn
this into a CI check takes about **2–4 engineering days**, mostly upstream esp32sim work (table below).
Screen and touch logic can move to the emulator. Speaker and microphone can move as **data-path** checks.
Acoustics, real latency and the 24-hour soak test stay on the board (TSK-I7-03).

## What the Box-3 really carries

Source: esp-bsp `bsp/esp-box-3` v3.2.1 (`idf_component.yml`, `include/bsp/esp-box-3.h`, `esp-box-3.c`,
`esp-box-3_idf5.c`, `Kconfig`), esp-bsp at `f259a6a` (2026-10-08). Espressif's hardware pages were not
consulted. The BSP is what the firmware runs.

| Part | Chip (driver the BSP uses) | Bus and pins |
|:---|:---|:---|
| LCD 320×240 RGB565 | ILI9342C-class panel through `esp_lcd_ili9341` with a vendor init table (`C8h FF 93 42`); if a TT21100 answers at 0x24, the BSP takes the older ESP-BOX path instead (ST7789 + TT21100) | 4-wire SPI on **`SPI3_HOST`**, 40 MHz, mode 0, 8-bit command and parameter: SCLK 7, MOSI 6, CS 5, D/C 4, RST 48 (active high, shared with touch), no MISO. Backlight on LEDC, GPIO 47. Init ends with `mirror(true, true)` (MADCTL `0xC8`) |
| Touch | GT911 at 0x5D, or 0x14 as backup (TT21100 at 0x24 on the older path) | **I2C1** (`CONFIG_BSP_I2C_NUM=1`), 400 kHz: SDA 8, SCL 18; INT on GPIO 3, active low. `esp_lvgl_port` puts the input device in *event* mode when INT is wired, so a read happens only after an INT edge |
| Speaker | ES8311 DAC at 0x18, amplifier enable on GPIO 46 | **I2S1** (`CONFIG_BSP_I2S_NUM=1`), full duplex, standard Philips, 16-bit mono: MCLK 2, BCLK 17, WS 45, DOUT 15 |
| Microphones | ES7210 ADC at 0x40 (MIC1 and MIC2 enabled by `esp_codec_dev`) | same I2S1 duplex pair: DIN 16. The RX channel is created after TX, so ESP-IDF makes it the clock slave (`RX_SLAVE_MOD`) |
| Buttons | Config (GPIO 0); Mute (logic gates, GPIO 1) | — |
| Other | ICM42670 IMU, AHT30 (sensor dock), SD card (SDMMC, D0 9 …), PMOD headers | not used by our checks |

## esp32sim against each part

esp32sim `main` at `f535f3b` (2026-10-19), built as in the companion spike. Board recipe:
`docs/adding.md` § "A board".

| Part | esp32sim before this spike | Prototype (this spike) | Work left for a CI-grade model |
|:---|:---|:---|:---|
| SPI3 (LCD bus) | **Not mounted on the S3.** Only GP-SPI2 exists (`periph.rs` block `0x24`). With the unchanged BSP, the first LCD command spins forever on `SPI3+0x000` USR (`--log-periph`) | Worked around in the firmware: `BSP_LCD_SPI_NUM` set to `SPI2_HOST`. SPI3 on the S3 has no IO_MUX pins, so the BSP already runs it through the GPIO matrix, and SPI2 through the matrix takes the same path on the real board | **1–2 days upstream**: a second `GpSpi` at block `0x25` with its interrupt source and GDMA peripheral 1. Also generalise the ~15 SPI2-only sites in `esp32s3/src/bus.rs` and `bus/dma.rs` (DMA pump, wire timing, abort paths) and the SPI3 signal numbers in `bus/pins.rs`, then add tests. **Or 0 days**: our display driver (TSK-S4-01, TSK-I2f-18) picks `SPI2_HOST` |
| ILI9342C panel | `DcsPanel` (`esp-soc/src/devices/dcs_panel.rs`) handles window, RAMWR, MADCTL and COLMOD for the ST77xx family, and ignores vendor commands | `DcsPanel::new(320, 240)` fed from `spi_tx`, D/C from GPIO 4, reset on GPIO 48 high. The glass is GRAM turned 180°, which the BSP's MX\|MY compensates | None for our checks. Gamma, voltage and timing commands are accepted and ignored |
| GT911 touch | `Gt911` (`esp32s3/src/i2c.rs`) on the LCD-4B board at 0x14, I2C0; no INT line | Same model at **0x5D on I2C1**, plus an INT pulse on GPIO 3 (100 µs low) for each press and each release, so event-mode LVGL reads the point | Upstream as part of the board; ~0.5 day for an INT pulse train while a finger is held (real GT911 reports every ~10 ms) if a test needs drag gestures |
| ES8311 speaker | `Reg8Device` stub (chip ID only); I2S TX captured from GDMA (`--wav`) | Same stub at 0x18 on I2C1; PA level on GPIO 46 tracked | None for a data-path check. Codec volume, mute and PA gain are not applied to the capture |
| ES7210 microphones | `Reg8Device` stub; **I2S RX is modelled** (`docs/cli.md` "I2S microphone input": 16/24/32-bit, mono or stereo, `--i2s-tone`, a Rust push API). The companion spike's "I2S TX only" was wrong at this commit | Same stub at 0x40. **One-line change** in `esp-periph/src/i2s/rx.rs`: accept `RX_SLAVE_MOD` while the same controller's TX runs (IDF full duplex). Without it, every read times out (`rx_conf=0x8822c`, bit 3 set, rejected) | **~0.5 day**: the duplex fix with tests. **~0.5 day**: a CLI input from a WAV file (`--i2s-wav PORT:FILE`, through the existing `i2s_input(port).push`). Recorded speech for the wake word and command words needs it, because `--i2s-tone` is only a sine. **~1 day, only if** our audio front end reads the ES7210 as TDM with more than two slots (mics plus echo reference): esp32sim lists "more than two slots" as unsupported. The echo reference on the real board is the speaker's sound picked up by the mics; in the emulator it is whatever we inject |
| Backlight | LEDC model; not tied to a board | Not wired. IDF also warns `GPIO 47 is not usable` under the emulator (cause not traced; harmless) | ~1 h if a check needs "backlight on" |
| Buttons | GPIO input and `press` in scripts | `press config 150`, `press mute 150` | None |
| IMU, AHT30, SD | — | not modelled; nothing probes them in our path | None for our checks |
| PSRAM, Wi-Fi, gate trace | Covered by the companion spike (8 MB with `--psram-mb 8`, station start-up, 93 events identical to QEMU) | unchanged | None |

## Runs

The scratch clone held a `box3` board (`esp32s3/src/board/box3.rs`, `make_board` arms `box3` and
`esp-box-3`). Every run used the companion spike's command with `--board box3`.

| # | Firmware | Result |
|:---|:---|:---|
| 1 | esp-bsp `examples/display`, unchanged (SPI3) on `--board none` | Boots to `bsp_display_start`, then hangs: the SPI3 transaction never completes ❌ (expected: no SPI3) |
| 2 | Same example with `SPI2_HOST`, `--board box3`, devices on I2C0 | Panel initialised, then `Touch not found` → abort: the BSP uses I2C1. Fixed in the board |
| 3 | Same, devices on I2C1 | `GT911: TouchPad_ID:0x39,0x31,0x31`, LVGL animation runs at 22 FPS. `--tft-png` shows the Espressif logo, colours right, upright after the 180° glass fix ✅ |
| 4 | Run 3's app plus a touch logger and a speaker and microphone round trip, `--script` (touch 30,210 at 3.0–3.2 s), `--wav`, `--i2s-tone 1:1000:0.5` | `SPIKE TOUCH PRESSED x=30 y=210` / `RELEASED` ✅. WAV: 0.5 s of 440 Hz (44 zero crossings per 0.1 s), peak 12 000 as written ✅. Microphone: `esp_codec_dev_read` → −1 (timeout) ❌ |
| 5 | Run 4 with the duplex RX change | Microphone reads return 0 with RMS 11 585 = a half-scale sine (0.5 × 32 768 / √2) ✅ |
| 6 | `targets/esp32s3/ui` (`ne_ui`) copied into the app, LVGL 9.6.0, `ne_ui_init` + `ne_ui_show_confirm` with the host case `confirm` (English) | `--tft-png` against `ui/golden/en/confirm.png`: **0 of 76 800 pixels differ at RGB565** (3 394 differ by 1 in an 8-bit channel, from 565→888 rounding) ✅. Taps on the yes and no chips reach LVGL at (75,217) and (205,217). Both land on the screen root, because the chips have no touch handler yet (TSK-I2f-18) |

Two scratch-only shims made `ne_ui` build in an ESP-IDF app. Both are findings for TSK-I2f-18:
`#include "lvgl/lvgl.h"` had to become `#include "lvgl.h"` (the managed `lvgl/lvgl` component does not
export that path), and `CONFIG_LV_USE_FONT_COMPRESSED=y` must be in `sdkconfig.defaults`.

Wall time: 8 s of guest time with the LVGL animation, audio and touch took 1.8 s wall. The `ne_ui` card
run took under 1 s.

## Which board-only checks could move

| Check (requirement, task) | To the emulator? | Cost | What stays on the board |
|:---|:---|:---|:---|
| **Screen**: approval card drawn from the pending table (DP-B-18, TC-B-18-1) | **Yes**, as a pixel compare against the host goldens at RGB565 | 0 days with `SPI2_HOST` in our driver, 1–2 days for SPI3 upstream; ~0.5 day for the CI job (`--tft-png` + compare) | Glass, viewing angle, backlight brightness |
| **Touch** answers through `ne_bridge_answer_touch` (DP-B-19) | **Yes**: scripted `touch x y 1/0` at an emulated time, GT911 + INT → LVGL → bridge | in the board (done); ~0.5 day for held-finger reports if needed | Capacitive feel, touch-to-screen latency |
| **Speaker**: text-to-speech and prompts reach the codec | **Yes, data path**: PCM captured to WAV, checked for level, length and frequency | none beyond the board | Loudness, distortion, amplifier, echo in a real room |
| **Microphone**: wake word, command words answer an `ask` only while it is on screen (DP-B-20, DP-B-21) | **Yes, data path** once WAV input exists: feed recorded utterances, assert the recognizer's verdict and the bridge call | ~0.5 day duplex fix + ~0.5 day WAV input; ~1 day more if TDM > 2 slots | Real microphones and noise, echo cancellation against real echo, false-accept rate in a room |
| Image size and memory with screen and voice (DP-B-22, TSK-I2f-20) | Partly: heap and PSRAM figures are the firmware's own and are meaningful | none | Timing-dependent figures |
| Voice latency (NFR-PERF-01, NFR-PERF-07), 24-hour soak | **No**: esp32sim timing is approximate, not cycle-accurate | — | All of it (TSK-I7-03) |

Upstream work (one PR or several to esp32sim, MIT): the `box3` board, the duplex RX fix, WAV input, and
SPI3 if we keep the BSP's host. If upstream is slow, the same patches can be carried as a pinned fork,
because the CI job builds esp32sim from source anyway (no releases).

## Reproduce

Scratch files are not kept in the repository. The prototype diff against esp32sim `f535f3b` (`box3.rs`,
`board/mod.rs`, `i2s/rx.rs`; 103 lines added, 1 changed) and the two screenshots are in this session
group's shared notes folder. Firmware: esp-bsp `f259a6a`, `examples/display` with
`main/idf_component.yml` pointing at `bsp/esp-box-3` by `override_path`, and `sdkconfig.bsp.esp-box-3`
plus `CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y` as `sdkconfig.defaults`. Built in `espressif/idf:v5.4` and
merged with `esptool.py merge_bin --fill-flash-size 16MB @flash_args`. For runs 2–6,
`include/bsp/esp-box-3.h` has `#define BSP_LCD_SPI_NUM (SPI2_HOST)`. Run: the companion spike's
command with `--board box3`, plus `--tft-png`, `--script`, `--wav` and `--i2s-tone 1:1000:0.5` as listed
under Runs.
