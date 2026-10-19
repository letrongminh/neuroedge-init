# Memory Feasibility Spike Report — ESP32-S3-BOX-3

| | |
|:---|:---|
| **Task ID** | TSK-S1-10 (measure) · TSK-S2-10 (scope conclusion) |
| **Requirements** | NFR-RES-01, NFR-RES-02 |
| **Reference decision** | Q-3 |
| **Related risks** | R-1 (Block 1b scope exceeds limit due to memory optimization) — Level **High** |
| **Assignee** | V2 — Embedded Engineer |
| **Status** | 🟡 **Measurement framework complete · NO REAL MEASUREMENTS YET** |
| **Last updated** | 2026-09-24 — still no measurements |

> **Honest status of this report.** The measurement framework (`targets/esp32s3/main/memory_probe.c`)
> is implemented and wired into `app_main`. There is not a single real measured number yet, because
> it has not run on physical hardware. Roadmap §4.4 (I3) requires spike results to be **a
> number, not an impression** — therefore all "Measured value" cells below are left
> blank, and `neuroedge_memory_meets_q3_budget()` returns `false` /
> `INCONCLUSIVE` until the `audio_ready` checkpoint is genuinely sampled.

---

## 1. Reference thresholds (decided in Q-3)

| Metric | Q-3 threshold | Measured value | Conclusion |
|:---|:---:|:---:|:---:|
| Internal SRAM for application | **≥ 120 KB** (122 880 B) | *not measured* | ⏳ |
| PSRAM for application | **≥ 2 MB** (2 097 152 B) | *not measured* | ⏳ |
| Firmware size | **≤ 3.5 MB** (3 670 016 B) | *not measured* | ⏳ |

These three thresholds are pinned as constants in
[`targets/esp32s3/main/memory_probe.h`](../../targets/esp32s3/main/memory_probe.h)
(`NEUROEDGE_Q3_*`). **Do not modify constants to make a run pass thresholds** — changing
thresholds is a roadmap decision, not a source code modification.

The 3.5 MB firmware threshold originates from the partition table: 16 MB flash divided into two A/B
slots of `0x380000` = 3 670 016 B each (see
[`targets/esp32s3/partitions.csv`](../../targets/esp32s3/partitions.csv)).
Exceeding this threshold makes A/B OTA impossible to flash; this is a hard constraint, not
an optimization target.

## 2. Checkpoints

The probe samples at four checkpoints in strict order. Each checkpoint represents a moment where an
*unremovable* subsystem has consumed memory; only the remainder is what the agent runtime
actually gets to use.

| # | Checkpoint | Loaded components | Free internal SRAM | Free PSRAM |
|:---:|:---|:---|:---:|:---:|
| 1 | `boot` | FreeRTOS + IDF only | *not measured* | *not measured* |
| 2 | `nvs_ready` | + NVS (licensing, credentials) | *not measured* | *not measured* |
| 3 | `network_ready` | + TCP/IP and Wi-Fi stack | *not measured* | *not measured* |
| 4 | `audio_ready` | **+ AEC + VAD + Opus + ring buffer** | *not measured* | *not measured* |

**Checkpoint 4 is the decisive checkpoint.** The first three checkpoints only provide the floor; comparing Q-3 using
numbers from checkpoints 1–3 answers a different question and yields a falsely reassuring result
— precisely the failure mode warned by R-1. Therefore the comparison function reports
`INCONCLUSIVE` when checkpoint 4 has not been sampled.

## 3. Remaining work to obtain measurements

| # | Task | Dependency |
|:---:|:---|:---|
| 1 | Physical ESP32-S3-BOX-3 board available | Ordering — not yet complete |
| 2 | Vendoring `esp-sr` (AEC/AFE + VAD) and `opus`, with license review §3.9 | License matrix (`NOTICE`) |
| 3 | Load 16 kHz 2-channel AEC (ES7210), VAD, 16 kHz mono Opus encoder, PSRAM ring buffer | Tasks 1 and 2 |
| 4 | Call `neuroedge_memory_probe(NEUROEDGE_CP_AUDIO_READY, "audio_ready")` | Task 3 |
| 5 | Fill tables in §1 and §2, conclude §5 | Task 4 |

Insertion point is marked with `TODO(TSK-S1-10, V2)` in
[`targets/esp32s3/main/main.c`](../../targets/esp32s3/main/main.c).

## 4. How to collect measurements

```bash
cd targets/esp32s3
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

The human-readable table is printed with tag `neuroedge_mem`. In addition to the human-readable table, firmware
prints **a machine-readable line** so no one has to manually copy data:

```
NEUROEDGE_MEMORY_JSON {"schema":"neuroedge.memory_spike/v1","board":"esp32s3-box-3", ...}
```

Workflow [`nightly-hardware.yml`](../../.github/workflows/nightly-hardware.yml)
greps this exact prefix, saves payload as an artifact, and verifies firmware size
using
[`scripts/check_firmware_size.py`](../../scripts/check_firmware_size.py).

### 4.1 Why QEMU cannot replace this measurement

Firmware boots on Espressif QEMU (TSK-S4-08), but QEMU does not emulate I2S, AFE, or octal PSRAM
of Box-3 (Q-21), so the `audio_ready` checkpoint cannot be obtained there. Instead CI verifies two **floors**
(TSK-S4-11, `scripts/check_firmware_size.py`, workflow `firmware-qemu.yml`) — necessary conditions, which do **not**
replace measurements of this report:

- **Static RAM** (job `firmware-size`, board configuration, with Wi-Fi): remaining internal SRAM after `.data`,
  `.bss` and IRAM code must be ≥ 120 KB — heap cannot exceed this number before any task runs.
- **Boot heap on QEMU** (line `NEUROEDGE_HEAP_JSON` immediately before `NE_TRACE DONE`, after gate
  self-test, before network and audio, no PSRAM): free internal heap must be ≥ 120 KB.

ESP-SR **is not yet linked** (`TODOS.md` #17), so both are floors **without** AFE. When vendoring
`esp-sr`, job `firmware-size` adds `--require-esp-sr`: builds silently missing AFE will fail.

| Floor (not Q-3 verdict) | Measured | Threshold | Source |
|:---|:---:|:---:|:---|
| Remaining internal SRAM after static allocation — board configuration | 231 556 B | ≥ 122 880 B | `.data` 20 300 · `.bss` 16 432 · IRAM code 73 435 out of DIRAM 341 760 |
| Free internal heap at boot — QEMU, no network, no PSRAM | 383 664 B | ≥ 122 880 B | checkpoint `gate_runtime_ready` |
| Signed OTA image — QEMU (open_eth, no Wi-Fi) | 724 992 B | ≤ 3 670 016 B | `scripts/qemu_ota.sh`, RSA-3072 image |
| Signed OTA image — board configuration (Wi-Fi, CA bundle for HTTPS) | 987 136 B | ≤ 3 670 016 B | `scripts/qemu_ota.sh` + `scripts/check_firmware_size.py` |
| Remaining internal SRAM after static allocation — board OTA build | 229 312 B | ≥ 122 880 B | `.data` 20 624 · `.bss` 18 096 · IRAM code 73 607 out of DIRAM 341 760 |

*The two OTA rows were measured on 2026-09-26 with `sdkconfig.ota` layer (TSK-S6-01/02/04); script reprints on each run of
`firmware-qemu.yml` job `ota-rollback`. These are static sizes of signed images, not Q-3 verdicts.*

Another measurement of the OTA path, not a Q-3 threshold: default `CONFIG_ESP_MAIN_TASK_STACK_SIZE`
**of 3584 B is insufficient**. `esp_https_ota` writes and verifies images on the calling task's stack, and `main` stack
overflows when verifying single-segment mapped images (measured 2026-09-26, ESP-IDF v5.4); the `sdkconfig.ota` layer sets
8192 B. A comment next to that constant in
[`targets/esp32s3/sdkconfig.ota`](../../targets/esp32s3/sdkconfig.ota) references this.

*Measured 2026-09-26, ESP-IDF v5.4, firmware of sample agent `home-voice`; CI reprints these numbers on each run.*

## 5. Conclusions and scope implications

> **Cannot conclude yet.** This section is only filled after measurements at checkpoint
> `audio_ready` are obtained.

Decision rules were decided prior to measurement, ensuring results are not reinterpreted
favorably:

| Measurement result | Mandatory action |
|:---|:---|
| Passes all three Q-3 thresholds | Keep Block 1b scope unchanged. Record measurements as baseline for Sprint 5 Criterion 4 (memory remaining after 4 hours runtime) |
| Fails any **single** threshold | **Do not cut voice** (Q-44): immediately open a `Q-N` to re-plan on-chip voice (TSK-I2f-19 memory budget with TSK-I2f-20, Box-3 checks in TSK-I7-03; Q-93) and postpone v1.0 forecast |

Rule decided prior to measurement (Q-44): failing a single threshold triggers immediate re-planning without delay. The value of
running an early spike is having sufficient time to adapt plans; delaying decisions eliminates that value completely.

## 6. Impact on Sprint 1 Exit Criteria

Criterion 3 of Sprint 1 — *"Memory spike report contains real measurement data, directly compared
against Q-3 thresholds"* — **is not yet satisfied** and cannot be satisfied through computer-based
work alone. This is the only item in Sprint 1 blocked by physical hardware.
