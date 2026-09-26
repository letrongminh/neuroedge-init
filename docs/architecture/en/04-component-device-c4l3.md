# 04 · ESP32-S3 Firmware Components (C4 L3 — Device Level)

> **Status:** C99 Walker, C99 Token Ledger, UART Trace output, and Boot Self-test are `done` (validated on Espressif QEMU in CI on every PR); complete hardware HAL and audio drivers are `in-progress / planned` (`TSK-S4-01`, awaiting physical silicon arrival).  
> **Source Directory:** `targets/esp32s3/`. Embedded review specifications: [`docs/spec/hal_mcu_review.md`](../../spec/hal_mcu_review.md) (KL-1..KL-5, RB-1..RB-4).

---

## 1. ESP32-S3 Firmware Component Diagram (C4 L3)

The microcontroller firmware is structured into modular C99 components executing atop the FreeRTOS real-time kernel within ESP-IDF 5.2.1+ / 5.4:

![E-04 · Firmware Map](../assets/svg/E-04-firmware-map.svg)
*Figure E-04 — Firmware Component Architecture and deterministic boot flow on the ESP32-S3 microcontroller.*

```mermaid
flowchart TB
    classDef host fill:#eff6ff,stroke:#2563eb,color:#1e3a8a,stroke-width:1.5px;
    classDef flash fill:#faf5ff,stroke:#9334e6,color:#6b21a8,stroke-width:1.5px;
    classDef core0 fill:#fff7ed,stroke:#ea580c,color:#7c2d12,stroke-width:1.5px;
    classDef core1 fill:#f0fdf4,stroke:#16a34a,color:#14532d,stroke-width:1.5px;
    classDef gate fill:#fef2f2,stroke:#dc2626,color:#991b1b,stroke-width:2px;
    classDef telem fill:#f1f5f9,stroke:#64748b,color:#0f172a,stroke-width:1.5px;
    classDef act fill:#fffbeb,stroke:#d97706,color:#92400e,stroke-width:1.5px;

    subgraph HostGen["Build-time Code Generation (Host Workstation)"]
        COMP["neuroedge build<br/>engine/compiler.py"]:::host
        GEN_G["scripts/gen_firmware_gates.py"]:::host
        GEN_V["scripts/gen_firmware_vectors.py"]:::host
        COMP --> GEN_G & GEN_V
        GEN_G --> H_NETR["*.netree.h<br/>Const binary array"]:::host
        GEN_V --> H_VEC["*.vectors.h<br/>Compliance test vectors"]:::host
    end

    subgraph FlashMem["16 MB SPI Flash Partition Layout"]
        BOOTLOADER["Bootloader<br/>(0x0000 · 32 KB)"]:::flash
        PART_TABLE["Partition Table<br/>(0x8000 · 4 KB)"]:::flash
        OTA_0["App Slot ota_0 (3.5 MB)<br/>Active firmware"]:::flash
        OTA_1["App Slot ota_1 (3.5 MB)<br/>Standby firmware"]:::flash
        NETREE_PART["Storage .netree (1 MB)<br/>Binary decision trees"]:::flash
        NVS_PART["NVS Partition (64 KB)<br/>WiFi credentials & Device ID"]:::flash
    end

    subgraph RuntimeTasks["ESP-IDF FreeRTOS Dual-Core Architecture"]
        subgraph Core0["Core 0 (Real-Time I/O & Networking)"]
            TASK_AUDIO["Audio I/O Task (Priority 15)<br/>I2S DMA · ES8311 Codec<br/>AEC · VAD · Opus Encoder"]:::core0
            TASK_NET["Network Task (Priority 10)<br/>WiFi STA · WebSocket Client<br/>Opus Stream to Cloud"]:::core0
        end

        subgraph Core1["Core 1 (Application Logic & Gate Safety)"]
            TASK_FSM["Voice FSM Task (Priority 12)<br/>5 conversational states<br/>Barge-in Abort Coordinator"]:::core1
            TASK_GATE["Gate Runtime Engine (Priority 14)<br/>ne_walker.c & ne_token.c<br/>Walks NETR in-place in Flash"]:::gate
            QUEUE_CMD["Actuator Command Queue<br/>Abortable command pipeline"]:::act
            DRV_GPIO["GPIO Drivers / Actuators<br/>Token-Verified Output"]:::act
        end

        TASK_AUDIO <-->|PCM Audio Frames| TASK_FSM
        TASK_FSM -->|Intent / ToolCall| TASK_GATE
        TASK_GATE -- "ALLOW + Token" --> QUEUE_CMD
        QUEUE_CMD -->|Pulses GPIO| DRV_GPIO
        TASK_FSM -.->|Barge-in Abort Signal &lt;= 20ms| QUEUE_CMD
    end

    subgraph Telemetry["Telemetry & Trace Stream (Non-blocking)"]
        TRACE_C["ne_trace.c<br/>Emits NE1 JSON-Lines"]:::telem
        UART0["UART0 / USB-CDC<br/>921600 baud -> Host PC / QEMU"]:::telem
        TRACE_C --> UART0
        TASK_GATE & QUEUE_CMD & TASK_FSM --> TRACE_C
    end

    H_NETR & H_VEC --> OTA_0
```

---

## 2. Core Firmware Components

### 2.1 C Binary Decision Tree Walker (`ne_gate/ne_walker.c`)
* **Role:** Evaluates Gate policies natively on the microcontroller with 100% mathematical determinism matching the Python host engine.
* **Technical Constraints & Characteristics:**
  * **Pure C99:** Non-recursive, zero dynamic memory allocation (`malloc`/`calloc`), zero shared global static state (fully reentrant & thread-safe).
  * **Zero Heap RAM:** The `NETR v1` binary tree is mapped directly from Flash (Memory-Mapped Flash over SPI MMU). Pointers walk directly across the Flash bus.
  * **Stack Budget:** Maximum stack depth $\le 512$ bytes, ensuring safe execution on constrained FreeRTOS tasks.
  * **Fact Handling:** Facts passed into the walker are **domain integer indices** (`0..N` for bool/level/choice), eliminating on-chip string parsing or string comparisons.

### 2.2 Single-Use Token Ledger (`ne_gate/ne_token.c`)
* **Role:** Enforces the core invariant: No GPIO pin can pulse without an authorized, unconsumed token issued by the Gate.
* **Technical Characteristics:**
  * **4 Fixed Memory Slots:** Static 4-slot array (`NE_TOKEN_SLOTS = 4`). When all 4 slots are occupied, the ledger rejects further allocations $\rightarrow$ **Fail-Closed by Default** (`NE_TOKEN_ERR_FULL`).
  * **Wrap-Safe Monotonic Clock:** Uses `esp_timer_get_time() / 1000` (monotonic milliseconds) to compute expiration `TTL = p95_latency * 3`.
  * **Tamper Resistance:** Validates random nonces and a hardware-seeded `boot_id`. Any tampered token or second invocation attempt is rejected with `NE_TOKEN_REPLAYED`.

### 2.3 UART Trace Serializer (`ne_gate/ne_trace.c`)
* **Role:** Streams on-device execution events back to the workstation for automated Action CI verification (`TSK-S4-09`).
* **Data Protocol:**
  * Emits each lifecycle event as a **standalone JSON line over UART0/USB-CDC**, prefixed with `NE1 ` followed by compacted JSON:
    ```text
    NE1 {"offset_ms":120,"type":"gate_evaluation_result","data":{"gate":"light_on","verdict":"ALLOW","reason":0}}
    ```
  * Uses a static stack buffer $\le 512$ bytes without heap allocation, cleanly separated from standard ESP-IDF system logging (`ESP_LOGI`).

---

## 3. Deterministic Boot Sequence Timeline

Upon power-on or hardware reset, the ESP32-S3 firmware must pass through 5 deterministic checkpoints:

```mermaid
sequenceDiagram
    autonumber
    participant HW as Hardware Bootloader
    participant M as memory_probe.c
    participant G as gate_selftest.c
    participant N as Network & WiFi
    participant A as Audio Pipeline

    HW->>M: System Boot (Checkpoint: BOOT)
    Note over M: Probe initial free SRAM
    HW->>M: Initialize NVS Flash (Checkpoint: NVS_READY)
    
    HW->>G: Run Gate Self-Test in Flash
    Note over G: Walker evaluates light_on & light_off<br/>Validates C99 single-use token ledger
    alt Self-test fails (FAIL)
        G-->>HW: Print NE_SELFTEST FAIL
        Note over HW: HALT SYSTEM EXECUTION (Safety Lockout)
    else Self-test succeeds (PASS)
        G-->>HW: Print NE_SELFTEST PASS walker=6 token=7
    end

    HW->>N: Initialize TCP/IP & WiFi (Checkpoint: NETWORK_READY)
    Note over M: Probe static network stack footprint
    
    HW->>A: Initialize I2S Codec & AEC (Checkpoint: AUDIO_READY)
    Note over M: Verify Q-3 budget: SRAM >= 120KB, PSRAM >= 2MB
    
    HW->>HW: Enter Application Main Loop & Voice FSM
```

* **Absolute Safety Invariant:** If `gate_selftest` detects any verdict discrepancy between the C walker and reference decisions $\rightarrow$ the system halts immediately, refusing to bring up network interfaces or drive GPIO pins. An unverified runtime is never permitted to control physical actuators.

---

## 4. Hardware Memory Budgets (Q-2, Q-3)

Based on Technical Decision `Q-3` locked on the reference **ESP32-S3-BOX-3** board (16 MB Quad Flash, 512 KB Internal SRAM, 8 MB Octal PSRAM):

| Resource Domain | Budget Threshold (Q-3) | Expected Allocation | Architectural Enforcement Tactic |
|:---|:---:|:---|:---|
| **Free Application SRAM** | $\ge 120\text{ KB}$ | Networking: ~60 KB · FreeRTOS OS: ~40 KB · DMA Buffers: ~30 KB $\rightarrow$ Free headroom $\ge 140\text{ KB}$ | All large buffers (audio, ring buffers) must reside in external PSRAM; C walker consumes 0 bytes of static SRAM (`RB-1`, `RB-2`). |
| **External PSRAM** | $\ge 2\text{ MB}$ | AEC/VAD Audio Buffers: ~512 KB · WebSocket stream buffer: ~256 KB $\rightarrow$ Free headroom $\ge 6\text{ MB}$ | Static pre-allocation at boot time; dynamic `malloc` is strictly forbidden in real-time audio loops (`RB-4`). |
| **Flash Image Size** | $\le 3.5\text{ MB}$ | Compressed Binary: ~2.8 MB (including mbedTLS, WiFi, Opus, ESP-SR) | Fits within symmetrical A/B dual partition slots ($3.5\text{ MB}$ each on a $16\text{ MB}$ Flash) for zero-downtime OTA rollouts (`FR-OTA-01`). |
