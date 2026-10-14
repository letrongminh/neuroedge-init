Last re-run: 2026-09-29, macOS (Apple Silicon), Docker `espressif/idf:v5.4`, `main` `6a69626` — `ui`, `boot`, `agent`, `ota` all ended with ✓.

# Demo script for boardless firmware (I3 + OTA)

> **Goal:** Enables the presenter to fully demo NeuroEdge's ESP32-S3 microcontroller side without plugging in a physical board: from device UI (LVGL golden images), firmware boot on Espressif QEMU and gate self-test, device replay of canonical traces with identical verdicts as on computer (`verify --targets esp32s3`), packaging user's own agent into firmware, to A/B partition OTA updates with digital signatures and automatic rollback on failure — all running in Docker with identical images and canonical steps as CI.

---

## 0. Preparation

Before the demo session, the presenter prepares the machine (macOS Apple Silicon or Linux):

1. **Docker Desktop running:** Ensure Docker daemon is running normally (`docker info`).
2. **Pre-pull ESP-IDF Docker image:** Run the following command once before the demo:
   ```bash
   docker pull espressif/idf:v5.4
   ```
3. **Runtime:**
   - Measured 2026-09-29: first time `ui` + `boot` takes ~3.5 minutes (compiling ESP-IDF from scratch). Subsequent runs are faster thanks to `neuroedge-ccache` ccache volume and `neuroedge-demo-venv` venv. `ota` builds four firmware images, taking the longest — **run before the demo session**, only open logs during presentation.
   - Log line `E (…) octal_psram: PSRAM ID read error` is normal: QEMU does not emulate PSRAM.
4. **Environment principles:**
   - Scripts run from repository root: `./demo/i3-firmware-qemu/run.sh <command>`.
   - All compilation, QEMU simulation, and test steps run inside container `espressif/idf:v5.4` without `--privileged` permissions.
   - No files written outside repository `.gitignore` paths and configured Docker volumes.

---

## 1. Scene 1 — On-device UI, Vietnamese

### Say
"NeuroEdge supports graphical UI directly on the device's 320×240 screen in standard accented Vietnamese (Be Vietnam Pro font) and English according to agent configuration. All UI code is written in pure C99 on top of LVGL v9.6.0 open-source graphics library. The same C source code is compiled both into firmware running on real chips and on computers to compare golden images on every Pull Request (CI job `ui-golden`). Consequently, we control 66 screen states pixel-for-pixel, ensuring agent text never overflows panels or breaks layouts, regardless of length or special characters."

### Type
```bash
./demo/i3-firmware-qemu/run.sh ui
```

### See
- Tool compares 66 screen images (33 Vietnamese + 33 English) via `scripts/run_ui_golden.sh` inside `espressif/idf:v5.4` container.
- Verification success notification: `ui-golden: 66/66 passed` then `ui-golden: every screen matches its golden`.
- Final line:
  ```text
  ✓ ui: all 66 golden screenshots match (vi and en)
  ```
- Table illustrating 8 representative Vietnamese screens:

| Screen | File name | Meaning | Illustration |
|:---|:---|:---|:---:|
| Khởi động đạt (Boot passed) | `boot_passed.png` | Gate self-test passed at boot | ![`boot_passed`](../../targets/esp32s3/ui/golden/vi/boot_passed.png) |
| Lắng nghe (Listening) | `voice_listening.png` | Input audio level | ![`voice_listening`](../../targets/esp32s3/ui/golden/vi/voice_listening.png) |
| Phản hồi giọng nói (Voice speaking) | `voice_speaking.png` | Transcript and answer | ![`voice_speaking`](../../targets/esp32s3/ui/golden/vi/voice_speaking.png) |
| Hỏi xác nhận (Ask confirmation) | `confirm.png` | `on_block: ask` under RFC-0006 | ![`confirm`](../../targets/esp32s3/ui/golden/vi/confirm.png) |
| Cho phép (ALLOW) | `verdict_allow.png` | Gate approved command successfully | ![`verdict_allow`](../../targets/esp32s3/ui/golden/vi/verdict_allow.png) |
| Chặn lệnh (BLOCK) | `verdict_block_condition_not_met.png` | Gate blocked with reason code | ![`verdict_block_condition_not_met`](../../targets/esp32s3/ui/golden/vi/verdict_block_condition_not_met.png) |
| Cảm biến (Sensor) | `sensor.png` | Temperature, humidity, door contact readings | ![`sensor`](../../targets/esp32s3/ui/golden/vi/sensor.png) |
| Xác minh OTA (OTA verifying) | `ota_verifying.png` | Verifying RSA-3072 signature | ![`ota_verifying`](../../targets/esp32s3/ui/golden/vi/ota_verifying.png) |

*(See all 33 Vietnamese images in directory [`targets/esp32s3/ui/golden/vi/`](../../targets/esp32s3/ui/golden/vi/) and 33 English images in [`targets/esp32s3/ui/golden/en/`](../../targets/esp32s3/ui/golden/en/)).*

### Highlights
- **UI speaks agent language:** Language is selected automatically from `[agent] language` in `agent.toml` (defaults to `"vi"` if unspecified), details in [`docs/spec/ui.md`](../../docs/spec/ui.md) §2.
- **Absolute determinism:** No random animations, no unconstrained scrolling when rendering sample images. Long text is always truncated at UTF-8 code point boundaries with an ellipsis `…`, never overlapping other labels.

---

## 2. Scene 2 — Chip boot and gate self-test

### Say
"Now we boot baseline firmware on Espressif QEMU simulator. At boot time, the chip runs a gate self-test procedure: the C walker and on-chip single-use token log verify the entire NETR decision tree stored in flash and agent test cases. If the chip's verdict deviates by even a single condition from the host-side engine, firmware immediately reports `NE_SELFTEST FAIL` and halts (fail-closed). After self-test passes, the chip replays 3 canonical system traces over UART. The `neuroedge verify --targets esp32s3` command reads this UART stream and proves chip verdicts match golden reference 100%."

### Type
```bash
./demo/i3-firmware-qemu/run.sh boot
```

### See
Presenter points out milestones printed at column 0 in the UART log:
1. Gate self-test passed line:
   ```text
   NE_SELFTEST PASS walker=26 token=11
   ```
2. Lines replaying canonical traces formatted as `NE1 ` JSON structures:
   ```text
   NE1 {"offset_ms":0,"type":"device_info","data":{"board_id":"esp32s3-box-3","agent_version":"home-voice@0.1.0","device_id":"qemu",…
   ```
3. Line notifying completion of trace sessions:
   ```text
   NE_TRACE DONE sessions=4
   ```
4. CLI target equivalence verification result:
   ```text
   ✓ VALID /tmp/demo-boot-traces/sess_…00.json — 78 event(s), target esp32s3
   │ Passed: all 3 gate(s) resolve, all 3 canonical trace(s) validate, every tool │
   ```
5. Final line:
   ```text
   ✓ boot: firmware boot thành công trên QEMU, self-test đạt và verify khớp 3 vết ghi chuẩn mực
   ```

### Highlights
- **C walker traverses NETR tree:** No heavyweight CEL interpreter on the microcontroller; binary decision tree is traversed cleanly in pure C99 (invariant 5 in [`CHANGELOG.md`](../../CHANGELOG.md) §3.3).
- **Target Equivalence:** Virtual chip verdicts on QEMU are completely equivalent to host/workstation engine.

---

## 3. Scene 3 — Your own agent into firmware

### Say
"A non-embedded developer can fully deploy their agent onto an ESP32-S3 chip. With just one command `neuroedge build --target esp32s3 --board esp32s3-box-3`, the system automatically transforms agent declarations into a standard ESP-IDF project: compiling gates into NETR trees, generating component `ne_agent.c` containing self-test checks with precomputed verdicts, and linking firmware source code. Now we will create a new agent from scratch, generate firmware, boot on QEMU, and witness that agent's own gate pass self-test on the chip."

### Type
```bash
./demo/i3-firmware-qemu/run.sh agent
```

### See
- Stages executed automatically in scratch directory:
  1. Create agent: `neuroedge new demo-agent`
  2. Generate firmware code: `neuroedge build --target esp32s3 --board esp32s3-box-3`
  3. Compile generated ESP-IDF project with `sdkconfig.qemu` configuration
  4. Boot agent firmware on QEMU
  5. Read self-test verdict line at column 0:
     ```text
     NE_SELFTEST PASS walker=8 token=6
     ```
  6. Record trace with `neuroedge record` and validate session with `neuroedge trace validate`
- Final line:
  ```text
  ✓ agent: agent demo-agent được sinh firmware, boot trên QEMU và vượt qua self-test
  ```

### Highlights
- **Same agent, multiple platforms:** Identical agent source code runs in simulation (`sim`), on Linux (`linux`), or compiles into C firmware (`esp32s3`).
- **Build-time rejection on incompatibility:** If an agent requires GPIO pins or capabilities unsupported by the board (FR-HAL-04), the `build` command rejects immediately with exit code 1 without writing any files to disk ([`docs/user/nap-firmware.md`](../../docs/user/nap-firmware.md) §3).

---

## 4. Scene 4 — Signed OTA updates, automatic rollback on failure

### Say
"NeuroEdge's over-the-air (OTA) update mechanism is built to industrial safety standards: dual A/B partitions, mandatory RSA-3072 signature verification before switching boot slots, and automatic rollback if an update is corrupted or fails gate self-test. No intermediate cloud service required: the device pulls updates directly from an HTTP endpoint. QEMU simulator executes the complete 7-phase scenario (a to g) proving all safety scenarios."

### Type
```bash
./demo/i3-firmware-qemu/run.sh ota
```

### See
Execution of script `scripts/qemu_ota.sh` goes through all 7 phases:
- **Phase a:** Factory 0.1.0 boots, self-test passes, server is running same version so it skips (`NE_OTA SKIP reason=same_version version=0.1.0`) — running slot is never lost.
- **Phase b:** Build 0.2.0 signed with correct key downloads, verifies signature, switches boot slot (`SWITCH partition=ota_0`) and is marked valid (`NE_OTA VALID`) after passing its own self-test (NVS high-water mark raised to 0.2.0).
- **Phase c:** Update signed with unknown key (differing from running build's key) is rejected before booting (`NE_OTA REJECTED reason=signature`): no slot change, no reboot, device remains on 0.2.0 and newly written slot has its first sector erased (`NE_OTA ERASED`).
- **Phase d:** Build signed correctly but corrupted (resets/crashes before confirming) (`NE_OTA TEST BOOTLOOP`) is automatically rolled back by bootloader (`NE_OTA ROLLBACK from=ota_1 to=ota_0`); device reboots into 0.2.0 and does not re-download corrupted build (`NE_OTA SKIP reason=rolled_back version=0.3.0`).
- **Phase e:** Update with failed gate self-test marks itself invalid (`NE_OTA INVALID partition=ota_1`) and reboots; bootloader rolls back to previous build (`NE_OTA ROLLBACK from=ota_1 to=ota_0`), then skips that build (`NE_OTA SKIP reason=rolled_back version=0.3.1`).
- **Phase f:** Unsigned update (missing signature block) is rejected (`NE_OTA REJECTED reason=signature`) and newly written slot is erased (`NE_OTA ERASED`).
- **Phase g:** Build signed correctly but with lower version number (0.1.0 compared to high-water mark 0.2.0) is rejected as a downgrade (`NE_OTA SKIP reason=downgrade version=0.1.0`) by NVS high-water mark.
- Script summary: `OTA on QEMU: all phases passed`.
- Final line:
  ```text
  ✓ ota: toàn bộ các pha cập nhật OTA và rollback (a–g) đạt yêu cầu trên QEMU
  ```

### Highlights
- **Self-test before Valid:** Newly downloaded build is only considered valid after gate self-test succeeds on chip.
- **Never bricked:** All incidents from wrong keys, corrupted code, to failed self-tests are automatically recovered to the last working slot by bootloader and partition policy.

---

## 5. What not to say in demo

When presenting to partners, customers, or during demand interviews, the presenter must strictly comply with the "What not to say" catalog in [`docs/business/cong-nhu-cau-2026-10-25/demo.md`](../../docs/business/cong-nhu-cau-2026-10-25/demo.md) §0.1 and limitation catalog in [`CHANGELOG.md`](../../CHANGELOG.md) §3.7. Specifically, do not state or claim the following three things:

1. **Do not say GPIO pins already control real equipment:** Currently the microcontroller HAL is TSK-S4-01; QEMU simulation only proves flash partition logic, C walker, token log, and signatures (Source: [`docs/spec/simulation_coverage.md`](../../docs/spec/simulation_coverage.md) §4, [`docs/user/nap-firmware.md`](../../docs/user/nap-firmware.md) §1).
2. **Do not say Box-3 has connected to real Wi-Fi in the wild:** QEMU connects to the network via `open_eth` virtual NIC; on physical ESP32-S3-BOX-3 board, Wi-Fi is only initialized at STA interface level without calling connect or network configuration provisioning (Source: [`docs/spec/simulation_coverage.md`](../../docs/spec/simulation_coverage.md) §4.1, [`docs/user/nap-firmware.md`](../../docs/user/nap-firmware.md) §6.5, `TODOS.md` #50).
3. **Do not say hardware Secure Boot or anti-rollback eFuses exist:** The verification public key resides inside the running firmware image (TSK-S6-05); anyone with a direct flash cable can still replace firmware or swap keys; downgrade prevention is currently implemented in software based on the NVS high-water mark (Source: TSK-S6-05, [`docs/user/nap-firmware.md`](../../docs/user/nap-firmware.md) §1, §6).
