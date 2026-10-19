# Spike: esp32sim and Velxio with our ESP32-S3 firmware (2026-10-19)

Companion to [`esp-emulator-spike-2026-10-19.md`](esp-emulator-spike-2026-10-19.md). Question: do
**esp32sim** and **Velxio** run our unchanged firmware, reach the same gate verdicts as QEMU, and add
what esp-emulator lacks (pins, screen, touch, audio)? License was not a criterion for this spike.

## Setup

| Item | Value |
|:---|:---|
| Images | The two images of the esp-emulator spike, unchanged: (a) QEMU configuration, (b) board configuration (Wi-Fi linked, PSRAM required). Both 16 MB merged `flash.bin` |
| Reference | QEMU UART of CI run 39165528565 (`firmware-qemu-uart`), 93 `NE1` events with `offset_ms` and `boot_id` masked |
| esp32sim | `mikroverk/esp32sim` at `main` (shallow clone), built with `cargo build --release` in `rust:1-bookworm` (25 s); ROM `esp32s3_rev0_rom.elf` from `espressif/idf:v5.4` |
| esp32sim run | `esp32sim --chip esp32s3 --board none --boot rom --rom <rom.elf> --console uart0 --flash-image flash.bin --elf <app>.elf --elf <bootloader>.elf --flash-mb 16 --psram-mb 8 --no-reboot --max-seconds 60` |
| Velxio | Image `ghcr.io/davidmonterocrespo24/velxio:master` (arm64, 4.95 GB), lcgamboa `libqemu-xtensa.so`, machine `esp32s3-picsimlab` |
| Velxio run | No CLI exists. A 40-line Python driver feeds `{"lib_path","firmware_b64","machine"}` to the backend's `app/services/esp32_worker.py` on stdin and collects its `uart_tx` / `gpio_change` JSON events; no web page involved |
| Pin test | A 20-line ESP-IDF app (`gpio_set_level` on GPIO10, reads a button on GPIO0), because our firmware does not drive a pin yet: `ne_pin_writer` is declared in `ne_hal.h` but no target code calls `gpio_set_level` |

## Results

| # | Check | QEMU (CI) | esp-emulator | esp32sim | Velxio |
|:---|:---|:---|:---|:---|:---|
| 1 | Boot, self-test (QEMU image) | `NE_SELFTEST PASS walker=26 token=11` | same | same ✅ | same ✅ |
| 2 | Normative trace | `NE_TRACE DONE sessions=4` | same | same ✅ | same ✅ |
| 3 | 93 `NE1` events, masked | reference | identical | **identical** ✅ | **identical** ✅ |
| 4 | PSRAM 8 MB | not found | found, 8.38 MB free | found with `--psram-mb 8`, 8 386 148 B free ✅ (default size is smaller: without the flag the app panics at `0x3c250000`) | **not modelled**: `PSRAM ID read error` ❌ |
| 5 | Board image (needs PSRAM) | not run | boots, console ready, stable 30 s | boots, `NE_CONSOLE READY`, trace identical except `device_id` ✅ | **aborts in a reboot loop**: `Failed to init external RAM!` ❌ |
| 6 | Wi-Fi | openeth | driver starts, station mode | driver starts, station mode; virtual AP (`--wifi ssid=…`) offered, not joined because the image has no stored credentials | S3 machine has no radio (worker source: `esp32s3.c` never attaches a NIC) ❌ |
| 7 | Pin output | no | no | GPIO10 edges in `--vcd` ✅ | `gpio_change` events for GPIO10 ✅ |
| 8 | Pin input (button) | no | no | `--script` `gpio 0 0` at 0.15 s read back by the app ✅ | `set_pin` command exists; not exercised |
| 9 | Screen | no | no | RGB/LCD_CAM and SPI panels on its own boards; **no Box-3 (ILI9342) model** | ILI9341 drawn by the web canvas only, not headless |
| 10 | Microphone (I2S RX) | no | no | no (I2S TX only) | no |
| 11 | Wall time to `NE_TRACE DONE` | not measured here | well under 120 s | ~3 s for 30+ s of guest time | ~4 s |
| 12 | Failure signal | exit code + grep | exit code | exit code is 0 even in a panic loop; grep the UART | no exit code; the driver must decide |

## What this means

- **Gate equivalence holds on all four.** The 93 events are byte-identical after masking, so any of them can
  run the `firmware-qemu` trace check.
- **esp32sim is the only one that does everything esp-emulator does and adds pins.** PSRAM, the board image
  and Wi-Fi start-up match esp-emulator; output edges are recorded and inputs can be scripted. It is fast.
  Gaps: no Box-3 screen model, no microphone, no releases (build from source), exit code 0 on a panic.
- **Velxio is not usable for our board image.** Its ESP32-S3 is a QEMU machine without PSRAM and without
  Wi-Fi, so the image that ships aborts at start. It only runs the QEMU-configuration image, which QEMU
  already covers, and it has no CLI: driving it means calling an internal worker of its web backend.
- **Pins cannot be tested on our firmware yet**, on any emulator, because nothing calls the pin writer. The
  pin test above proves the tools, not our HAL.
- **Screen and microphone stay a board check (I7, D9)** whichever emulator is chosen.

## Reproduce

Scratch files are not kept in the repository. The commands are in the Setup table; the masking is
`sed -E 's/"offset_ms":[0-9]+/"offset_ms":T/; s/"boot_id":[^,}]+/"boot_id":X/'` on lines starting `NE1 `,
with `\r` removed.
