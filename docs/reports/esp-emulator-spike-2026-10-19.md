# esp-emulator Spike — Our ESP32-S3 Firmware Without a Board

| | |
|:---|:---|
| **Task ID** | TSK-I3-02 |
| **Requirements** | FR-CI-06, FR-TGT-03 |
| **Reference decisions** | Q-21, Q-69, Q-92 (4), (5) |
| **Assignee** | V2 — Embedded Engineer |
| **Status** | ✅ The firmware boots and passes the gate self-test; esp-emulator becomes the `esp32s3` release target of the public launch (Q-92) |
| **Date** | 2026-10-19 |

## 1. Question

Q-92 lets the public launch (I6) verify `esp32s3` on Espressif's esp-emulator instead of a board. Before
the roadmap moves onto that, this spike answers one question: does our firmware, built as CI builds it, boot
on esp-emulator and make the same gate decisions as on QEMU?

## 2. Setup

| Item | Value |
|:---|:---|
| Emulator | esp-emulator **0.49.0** (`esp-emu`, release asset `aarch64-apple-darwin`, SHA-256 checked against the release's `SHA256SUMS`) |
| Toolchain | Docker image `espressif/idf:v5.4`, the same image as `.github/workflows/firmware-qemu.yml` |
| Source | branch `docs/q91-phone-app` at `198b93f`, `targets/esp32s3/` unchanged |
| Images | (a) **QEMU configuration** `sdkconfig.defaults;sdkconfig.qemu`, app 346 720 B; (b) **board configuration** `sdkconfig.defaults` (Wi-Fi linked, as the `firmware-size` job), app 826 464 B |
| Flash | `esptool.py merge_bin --fill-flash-size 16MB @flash_args`, as `scripts/qemu_boot.sh` |
| Run | `esp-emu --chip esp32s3 --firmware flash.bin --elf <app>.elf --timeout 120s` |
| Reference | UART of the `firmware-qemu` job, run 39165528565 on `main` (artifact `firmware-qemu-uart`) |

## 3. Results

| # | Check | QEMU (CI) | esp-emulator | Verdict |
|:---:|:---|:---|:---|:---:|
| 1 | Gate self-test line | `NE_SELFTEST PASS walker=26 token=11` | `NE_SELFTEST PASS walker=26 token=11` | ✅ same |
| 2 | Trace sessions | `NE_TRACE DONE sessions=4` | `NE_TRACE DONE sessions=4` | ✅ same |
| 3 | `NE1` trace events, offsets and `boot_id` ignored | 93 events | 93 events, **identical**: 16 `ALLOW`, 13 `BLOCK`, same gates, digests, facts and reasons | ✅ same |
| 4 | Board image: boot guard, config, console | not run on QEMU | `NE_BOOT count=1 max=4 mode=normal`, `NE_CONFIG STORAGE plaintext risk=readable_flash`, `NE_CONSOLE READY`, `NE_BOOT STABLE after_ms=30000` | ✅ |
| 5 | Board image: Wi-Fi | QEMU uses openeth, not Wi-Fi | Wi-Fi driver starts, station mode, MAC `24:0a:c4:00:00:01` | ✅ starts (no access point was offered) |
| 6 | PSRAM | QEMU: `PSRAM chip not found` | octal PSRAM 64 Mbit found; 8 383 976 B free | ✅ esp-emulator models more than QEMU |
| 7 | Internal SRAM after network (Q-3: ≥ 122 880 B) | — | 270 247 B free, largest block 176 128 B | ✅ above the floor (an emulator figure; the binary's heap layout is real) |
| 8 | Main task stack (Q-79: ≥ 512 B free) | 1 368 B free | 1 296 B free | ✅ |

Both images ran in well under the 120 s budget. The QEMU-configuration image stopped on `NE_TRACE DONE`;
the board image ran to the 90 s timeout and stayed stable.

## 4. Limits

- **Pins are not observable.** esp-emulator 0.49.0 documents UART, a TCP control channel (`reset`,
  `erase-flash`, `ping`) and the browser build's GPIO view, but no native API to read or drive a pin. The
  gate's decisions are proven through the self-test and the trace (rows 1–3), not by watching a pin change.
- **Peripherals not listed:** camera (DVP), I2S and ADC. `vision.in` (TSK-I3a-04) and `analog.in` on the chip
  need a board; Q-92 (5) keeps them in v1.0.
- **What only silicon proves:** secure boot and flash encryption (eFuses), RF, power loss and timing under
  load. Q-92 (5) keeps them in v1.0 (I7).
- **Beta software:** the README makes no equivalence claim; a version pin and the QEMU job stay as the
  cross-check.

## 5. Conclusion and follow-up

esp-emulator runs our unchanged firmware and reaches the same gate verdicts as QEMU, and it models PSRAM and
Wi-Fi start-up, which QEMU does not. It can serve as the `esp32s3` target of the public launch (Q-92 (4)).
Follow-up, all in the roadmap: a CI job that boots both images on a pinned esp-emulator and compares the
trace with QEMU's (TSK-I3-04); the real-board checks moved to I7 (TSK-S1-10, TSK-S4-03, TSK-S4-05,
TSK-S4-12, TSK-I3a-01, TSK-I3a-04).
