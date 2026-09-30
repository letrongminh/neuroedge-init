# 11 · Hướng dẫn port HAL cho đối tác OEM

> **Phạm vi:** đưa NeuroEdge lên một bo mạch hoặc một chip mới — hợp đồng phải giữ, mã tái dùng được,
> mã phải viết, và cách chứng minh port đúng. **Nguồn:** `python/neuroedge/hal/`, `boards/`,
> `targets/esp32s3/components/`, `targets/esp32s3/main/`, `docs/spec/hal_mcu_review.md`, RFC-0002, Q-13.

## 1. Hôm nay port được gì

| Loại port | Làm được hôm nay? | Ghi chú |
|:---|:---|:---|
| **Bo mạch mới cho target có sẵn** (một SBC Linux khác, một bo ESP32-S3 khác) | Về kỹ thuật có; nhưng `boards/` chỉ nhận **ba profile bậc 1** cho tới RFC-0002 (`test_boards.py`), và bo mạch tham chiếu của `esp32s3` chỉ là Box-3 (bất biến 6) | Dùng để thử nghiệm nội bộ; chưa công bố được |
| **Target mới** (`stm32`, `rp2350`, `jetson`) | **Chưa**: danh sách target đóng ở `sim`, `linux`, `esp32s3` trong `schemas/` và `hal/board.py` | RFC-0002 (đang thảo luận) mở danh sách theo bậc ở I11; bộ công cụ port cộng đồng ở I13 |
| **Bậc 3 do cộng đồng tự kiểm** (Q-13) | Quy trình quy hoạch ở I13 (`TSK-P1-01…05`) | Chương này mô tả phần đã có mã và phần sẽ đổi |

Phần còn lại mô tả **hợp đồng** — nó không đổi khi danh sách target mở — và mã có thể tái dùng ngay.

## 2. Hợp đồng port

Một port đúng khi nó giữ đủ các điều sau. Mỗi điều đã có kiểm tự động trên ba target bậc 1.

| # | Hợp đồng | Nghĩa là | Kiểm bằng |
|:---:|:---|:---|:---|
| 1 | **Năm nguyên thủy của v1.x — tập đóng** | `audio.in`, `audio.out`, `digital.out`, `sensor.read`, `display` (FR-HAL-01, KL-1). Bậc 3 được thiếu một số nguyên thủy tuỳ năng lực bo mạch, nhưng không được tự ý thêm. Mọi nguyên thủy mới chỉ qua RFC (RFC-0007: `digital.in`; RFC-0010: PWM; RFC-0011: `motion.*`; RFC-0012: `vision.in`; RFC-0013: tuỳ chọn theo bo mạch — Q-53; xem [`15`](15-target-architecture.md) §4) | `board.v1`, `PRIMITIVES` |
| 2 | **Chân theo tên** | Mã agent dùng tên logic (`door_lock`); số chân vật lý chỉ nằm trong HAL (KL-2) | build đối chiếu tên |
| 3 | **Không chân nào động mà không có token** | Lệnh chân kiểm tên chân, rồi gọi hàm `authorize` được lắp vào, rồi mới lái chân. HAL chưa được lắp sổ token thì từ chối mọi lệnh | `test_hal_sim.py`, `tests_linux/test_gpio_sim.py`, self-test token trên chip |
| 4 | **Thiếu thiết bị thì báo lỗi, không giả vờ** | Không có `/dev/gpiochip*`, không có cảm biến, không mở được micro ⇒ lỗi ba phần **trước khi** giữ chân nào (Q-16); không bao giờ trả giá trị mặc định | `preflight` của `LinuxHAL` |
| 5 | **Mọi lệnh đều để lại sự kiện** | `actuator_command`, `actuator_aborted`, `sensor_read`, `display_frame`… với đúng tên và trường (`simulation_coverage.md` §3) | golden comparator |
| 6 | **Huỷ được lệnh đang chờ** | Cắt lời phải huỷ được xung chưa giao trong ≤ 1 khung âm thanh (RB-3) | `test_voice_fsm.py` |
| 7 | **Khai báo là dữ liệu** | Năng lực bo mạch là một tệp `board.toml` (trên chip: bảng `const` trong flash — RB-4), không phải mã (KL-4) | `schemas/board.v1.json` |
| 8 | **Cùng quyết định** | Phát lại ba vết ghi chuẩn mực cho đúng phán quyết và lệnh chân như golden | `neuroedge verify --targets …` |

## 3. Khai báo bo mạch

Profile của bo mạch tham chiếu, làm mẫu:

```toml
[board]
id     = "esp32s3-box-3"
name   = "Espressif ESP32-S3-BOX-3"
target = "esp32s3"
mcu    = "esp32s3"

[capabilities.audio_in]
channels       = 2
sample_rate_hz = 16000
aec            = true
vad            = true

[capabilities.audio_out]
channels       = 1
sample_rate_hz = 16000

[capabilities.digital_out]
pins    = ["door_lock", "porch_light", "gate_relay"]
backend = "esp_driver_gpio"

[capabilities.sensor_read]
sensors = ["temperature", "humidity", "door_contact", "motion"]

[capabilities.display]
width  = 320
height = 240
color  = "rgb565"
```

Chỉ khai những gì HAL **chạy được và đã đo**. Ví dụ `linux-rpi5` giữ `aec = false` cho tới khi phép đo
khử vang trên Pi đạt (`simulation_coverage.md` §6.2): khai `true` sớm là hứa điều chưa chứng minh.

## 4. Port phía host (Python)

Một HAL host là một lớp con của `HardwareAbstractionLayer`. `SimHAL` và `LinuxHAL` là hai mẫu hoàn
chỉnh.

```python
from neuroedge.hal import HardwareAbstractionLayer
from neuroedge.hal.board import BoardProfile

class MyBoardHAL(HardwareAbstractionLayer):
    def __init__(self, board: BoardProfile, *, events, authorize, **options) -> None:
        super().__init__(target="linux", board=board, authorize=authorize)
        self.events = events
        # open nothing yet: devices are checked in preflight(), before any line is held

    def preflight(self, sensors=(), display=False, audio=(), where="") -> None:
        ...  # open or probe every device the agent needs; raise BoardCapabilityError on the first gap

    def digital_out(self, pin, operation, duration_ms=0, signature="", called_from="<unknown>"):
        super().digital_out(pin, operation, duration_ms, signature, called_from)  # name check, authorize, record
        ...  # drive the physical line only after the base call returned
        self.events.emit("actuator_command", {"pin": pin, "operation": operation, "duration_ms": duration_ms})

    def sensor_read(self, sensor, called_from="<unknown>", use=None):
        ...  # read the device every time; raise, never return a default reading

    def close(self) -> None:
        ...  # every line back to inactive and released, on every exit path
```

Luật khi viết:
- **Gọi `super().digital_out` trước** khi lái chân: nó kiểm tên chân (gõ sai không tốn token) và gọi
  `authorize`. Đừng tự kiểm token.
- **Không import `engine`, `actions`, `models`** từ HAL: `hal` là lá của đồ thị phụ thuộc
  (`test_architecture_layers.py::test_the_hal_is_a_leaf`).
- **Thư viện ngoài import muộn** trong hàm cần nó, kèm lỗi ba phần chỉ ra phần mở rộng cần cài
  (mẫu: `hal/linux.py::_import_gpiod`). Thư viện copyleft chỉ được là phần mở rộng tuỳ chọn (Q-11).
- **Thả mọi tài nguyên ở mọi lối ra**, kể cả SIGTERM và SIGHUP.

## 5. Port phía chip (C)

Phần lõi của firmware đã là **C99 thuần, không phụ thuộc ESP-IDF**, nên dùng lại nguyên trên chip khác:

| Mã | Phụ thuộc | Tái dùng |
|:---|:---|:---|
| `components/ne_gate/` (walker `NETR`, sổ token) | không có | nguyên văn |
| `components/ne_trace/` (định dạng dòng `NE1`) | `ne_gate` | nguyên văn |
| `components/ne_agent/` (sinh cho từng agent) | `ne_gate`, `ne_trace` | sinh lại bằng `neuroedge build` |
| `main/gate_selftest.c`, `main/trace_vectors.c` | không có ESP-IDF | nguyên văn |
| `components/ne_ota/src/ne_ota_policy.c` | không có | nguyên văn; `ne_ota.c` là phần ESP-IDF phải viết lại |
| `main/main.c`, `main/memory_probe.c` | ESP-IDF | viết lại cho nền tảng mới |

Nền tảng mới chỉ cần cấp **bốn điểm nối** — đó là toàn bộ bề mặt mà lõi C đòi:

```c
/* 1. entropy for token nonces — the shape of esp_fill_random */
typedef void (*ne_random_fn)(void *buf, size_t len);

/* 2 and 3. where trace lines go, and the device clock in milliseconds */
typedef struct {
    void (*emit)(void *ctx, const char *line);   /* one line to the UART, no newline */
    uint32_t (*now_ms)(void *ctx);
    void *ctx;
    char *buf;                                   /* at least NE_TRACE_LINE_MAX + 1 bytes */
    size_t cap;
    uint32_t t0_ms;
    uint32_t lines;
    uint32_t dropped;
} ne_trace_sink;

/* 4. run the boot self-test against the linked agent before anything else */
int neuroedge_gate_selftest(const ne_agent *agent, ne_random_fn fill_random, uint32_t boot_id,
                            uint32_t now_ms, char *line, size_t cap, ne_trace_sink *sink);
```

Trình tự khởi động phải giữ như `esp32s3` ([`04`](04-component-device-c4l3.md) §4): self-test **trước**
mọi thứ khác, và thất bại thì dừng — không runtime gate, không action, không mạng.

**Chưa có:** giao diện C cho việc lái chân, đọc cảm biến, âm thanh (HAL trên chip là TSK-S4-01). Khi nó
có, nó phải gọi `ne_token_authorize` trước khi lái chân, đúng như HAL host gọi `authorize`. Ràng buộc bộ
nhớ bắt buộc cho nó: RB-1…RB-4 (`docs/spec/hal_mcu_review.md` §2) — không cấp phát trên đường âm thanh,
đệm tĩnh đo được, huỷ lệnh trong ≤ 1 khung, bảng năng lực `const`.

## 6. Chứng minh port đúng

| Bước | Lệnh | Đạt khi |
|:---:|:---|:---|
| 1 | `neuroedge board show <id>` và `neuroedge build --target <t> --board <id>` với từng agent mẫu | agent hợp bo mạch build được; agent đòi thứ bo mạch thiếu bị từ chối với `NE3001` |
| 2 | Test C của lõi trên host: `make -C targets/esp32s3/components/ne_gate` và `make … check-static` | mọi test đạt dưới ASan/UBSan; không có `.data`/`.bss`; stack mỗi hàm ≤ 512 byte |
| 3 | Khởi động firmware | dòng `NE_SELFTEST PASS walker=<n> token=<n>` ở cột 0 trên UART |
| 4 | `neuroedge record --target <t> --port <nguồn>` rồi `neuroedge trace validate` | mọi phiên `NE1` thành `trace.v1` hợp lệ |
| 5 | `neuroedge verify --targets <t> --port <nguồn>` (chip) hoặc `neuroedge verify --targets sim,<t>` (host) | ba vết ghi chuẩn mực cho cùng quyết định; lệch ⇒ `NE4002` |
| 6 | Corpus tool call và thoại trên HAL mới | khớp `expected_results.yaml` |

Công cụ đóng gói bộ vector để chạy **ngoài** kho, và lệnh `board check`, là việc của I13 (`TSK-P1-01`,
`TSK-P1-05`).

## 7. Tài sản và giấy phép của một port

- Driver HAL của đối tác là **của đối tác**; nó chỉ cần giữ hợp đồng ở §2.
- Mọi phụ thuộc, mô hình, phông chữ đi kèm phải nằm trong danh sách cho phép của Q-11 và được ghi ở
  `NOTICE`. Không gì phi thương mại được đi kèm (Q-45).
- Chuẩn — `schemas/`, `docs/spec/`, `fixtures/compliance/` — theo Apache-2.0 để ai cũng hiện thực được;
  mã của NeuroEdge theo PolyForm Noncommercial (`LICENSING.md`).
