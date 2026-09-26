# 04 · Thành phần Firmware ESP32-S3 (C4 L3 — Device Level)

> **Trạng thái:** Walker C99, Sổ token C99, Vết ghi UART và Self-test boot `done` (chạy trên Espressif QEMU trong CI mỗi PR); HAL firmware và driver âm thanh đầy đủ `in-progress / planned` (`TSK-S4-01`, chờ bo mạch vật lý).  
> **Nguồn mã nguồn:** `targets/esp32s3/`. Đặc tả ràng buộc nhúng: [`docs/spec/hal_mcu_review.md`](../../spec/hal_mcu_review.md) (KL-1..KL-5, RB-1..RB-4).

---

## 1. Sơ đồ Thành phần Firmware ESP32-S3 (C4 L3 Device Diagram)

Firmware vi điều khiển được tổ chức thành các thành phần C99 độc lập, chạy trên nền FreeRTOS của ESP-IDF 5.2.1+ / 5.4:

![E-04 · Bản đồ firmware](../assets/svg/E-04-firmware-map.svg)
*Hình E-04 — Cấu trúc thành phần Firmware và luồng khởi động an toàn trên vi điều khiển ESP32-S3.*

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

## 2. Chi tiết Các Thành phần Lõi Firmware

### 2.1 Bộ Duyệt Cây Quyết định Nhị phân (`ne_gate/ne_walker.c`)
* **Vai trò:** Hiện thực engine đánh giá chính sách Gate trực tiếp trên vi điều khiển, đảm bảo tính tất định 100% giống hệt host engine.
* **Đặc tính kỹ thuật & Ràng buộc nhúng:**
  * **C99 thuần túy:** Tuyệt đối không dùng đệ quy (non-recursive), không cấp phát bộ nhớ động (`malloc`/`calloc`), không biến tĩnh dùng chung (reentrant & thread-safe).
  * **Zero Heap RAM:** Toàn bộ cấu trúc cây `NETR v1` được ánh xạ trực tiếp từ Flash (Memory-Mapped Flash qua SPI MMU). Con trỏ duyệt trực tiếp trên Flash bus.
  * **Ngân sách Stack:** Kích thước stack tiêu thụ tối đa $\le 512$ bytes, an toàn tuyệt đối cho các tác vụ FreeRTOS có stack nhỏ.
  * **Xử lý Fact:** Fact truyền vào walker là **index số nguyên trong domain** (`0..N` cho bool/level/choice), không so sánh chuỗi ký tự trên chip.

### 2.2 Sổ Quản lý Token Dùng Một Lần (`ne_gate/ne_token.c`)
* **Vai trò:** Cưỡng chế nguyên tắc an toàn: Không một chân GPIO nào có thể kích hoạt mà không có token phán quyết hợp lệ từ Gate.
* **Đặc tính kỹ thuật:**
  * **4 Slot Bộ nhớ Cố định:** Cấu trúc mảng tĩnh 4 slot token (`NE_TOKEN_SLOTS = 4`). Khi cả 4 slot đang bận, sổ từ chối cấp thêm token mới $\rightarrow$ **Mặc định an toàn Fail-Closed** (`NE_TOKEN_ERR_FULL`).
  * **Đồng hồ Đơn điệu Wrap-Safe:** Sử dụng `esp_timer_get_time() / 1000` (mili-giây đơn điệu) để kiểm tra thời hạn sống `TTL = p95_latency * 3`.
  * **Bảo vệ Bộ nhớ:** Kiểm tra nonce ngẫu nhiên và `boot_id` được sinh lúc khởi động thiết bị. Token bị can thiệp bộ nhớ hoặc bị phát lại lần thứ hai sẽ lập tức bị từ chối với mã `NE_TOKEN_REPLAYED`.

### 2.3 Bộ Định dạng Vết ghi UART (`ne_gate/ne_trace.c`)
* **Vai trò:** Đưa toàn bộ sự kiện diễn ra trên vi điều khiển về máy tính cá nhân để Action CI có thể đối soát và thẩm định (`TSK-S4-09`).
* **Định dạng dữ liệu:**
  * Mỗi sự kiện xuất thành **một dòng văn bản độc lập trên UART0/USB-CDC**, bắt đầu bằng tiền tố `NE1 ` theo sau là chuỗi JSON nén tối giản:
    ```text
    NE1 {"offset_ms":120,"type":"gate_evaluation_result","data":{"gate":"light_on","verdict":"ALLOW","reason":0}}
    ```
  * Bộ đệm xuất dòng tĩnh $\le 512$ bytes, không cấp phát heap, tách bạch hoàn toàn với log hệ thống của ESP-IDF (`ESP_LOGI`).

---

## 3. Trình tự Khởi động An toàn (Boot Sequence Timeline)

Mỗi lần cấp nguồn hoặc khởi động lại, firmware ESP32-S3 bắt buộc phải đi qua 5 checkpoint đo kiểm nghiêm ngặt:

```mermaid
sequenceDiagram
    autonumber
    participant HW as Hardware Bootloader
    participant M as memory_probe.c
    participant G as gate_selftest.c
    participant N as Network & WiFi
    participant A as Audio Pipeline

    HW->>M: Khởi động hệ thống (Checkpoint: BOOT)
    Note over M: Đo SRAM tự do ban đầu
    HW->>M: Khởi tạo NVS Flash (Checkpoint: NVS_READY)
    
    HW->>G: Chạy Gate Self-Test trong Flash
    Note over G: Walker duyệt cây light_on & light_off<br/>Kiểm tra sổ token C99
    alt Self-test thất bại (FAIL)
        G-->>HW: In NE_SELFTEST FAIL
        Note over HW: DỪNG TOÀN BỘ HỆ THỐNG (Khóa an toàn)
    else Self-test thành công (PASS)
        G-->>HW: In NE_SELFTEST PASS walker=6 token=7
    end

    HW->>N: Khởi tạo TCP/IP Stack & WiFi (Checkpoint: NETWORK_READY)
    Note over M: Đo footprint tĩnh của ngăn xếp mạng
    
    HW->>A: Khởi tạo Codec I2S & Khử nhiễu AEC (Checkpoint: AUDIO_READY)
    Note over M: Kiểm tra ngân sách Q-3: SRAM >= 120KB, PSRAM >= 2MB
    
    HW->>HW: Bắt đầu Vòng lặp Ứng dụng & Voice FSM
```

* **Quy tắc An toàn Tuyệt đối:** Nếu `gate_selftest` phát hiện bất kỳ sai lệch nào giữa phán quyết của C walker so với bản chuẩn $\rightarrow$ thiết bị dừng boot ngay lập tức, từ chối mở mạng, từ chối cấp xung GPIO. Không bao giờ cho phép một runtime không đáng tin cậy điều khiển phần cứng.

---

## 4. Ngân sách Bộ nhớ Phần cứng đã Chốt (Q-2, Q-3 Hardware Budgets)

Dựa trên Quyết định kỹ thuật `Q-3` trên bo mạch tham chiếu duy nhất **ESP32-S3-BOX-3** (16 MB Quad Flash, 512 KB Internal SRAM, 8 MB Octal PSRAM):

| Vùng tài nguyên | Ngưỡng cam kết (Q-3) | Phân bổ thực tế dự kiến | Chiến thuật kiểm soát kiến trúc |
|:---|:---:|:---|:---|
| **SRAM Ứng dụng** | $\ge 120\text{ KB}$ | Ngăn xếp mạng: ~60 KB · OS/FreeRTOS: ~40 KB · DMA Buffers: ~30 KB $\rightarrow$ Còn dư $\ge 140\text{ KB}$ | Toàn bộ buffer lớn (âm thanh, ring buffer) bắt buộc đẩy sang PSRAM; walker C dùng 0 bytes SRAM tĩnh (`RB-1`, `RB-2`). |
| **PSRAM Ngoài** | $\ge 2\text{ MB}$ | Đệm âm thanh AEC/VAD: ~512 KB · WebSocket stream buffer: ~256 KB $\rightarrow$ Còn dư $\ge 6\text{ MB}$ | Cấp phát tĩnh một lần lúc boot (Static allocation at init), cấm `malloc` trong vòng lặp thời gian thực (`RB-4`). |
| **Dung lượng Flash** | $\le 3,5\text{ MB}$ | Ứng dụng nén: ~2.8 MB (bao gồm mbedTLS, WiFi, Opus, ESP-SR) | Phù hợp với khe phân vùng A/B kép (khe $3.5\text{ MB}$ trên Flash $16\text{ MB}$) phục vụ cập nhật OTA an toàn (`FR-OTA-01`). |
