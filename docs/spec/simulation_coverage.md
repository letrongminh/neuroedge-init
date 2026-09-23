# Phủ mô phỏng — 5 nguyên thủy × 3 target bậc 1

**Trạng thái:** đặc tả quy phạm, đi kèm Q-21 và Q-22 (PRD §15, *đề xuất*). Cập nhật 2026-09-23.
Công cụ và giấy phép: proposal Phụ lục H.4. Chiến lược theo tầng: proposal §3.2.

Tài liệu này trả lời một câu hỏi: **với mỗi nguyên thủy HAL trên mỗi target, cái gì chạy nó,
cái gì kiểm nó, và cái gì chưa kiểm được.** Mỗi ô của bảng ở §2 có một task chịu trách nhiệm;
ô nào chưa có task là một lỗ hổng.

## 1. "Phủ trọn vẹn" nghĩa là gì

Không bộ mô phỏng nào giả lập được âm học phòng, timing I2S hay áp lực bộ nhớ của ESP32-S3. Vì
vậy "trọn vẹn" không có nghĩa là mọi thứ chạy không cần phần cứng. Một ô được coi là **phủ** khi
đủ bốn điều:

1. **Backend chạy được** trên target đó, đúng hợp đồng HAL (FR-TGT-01/02/03).
2. **Sự kiện vết ghi chuẩn** cho mọi lần gọi (§3), để phiên được `record` và `replay`.
3. **Kiểm tự động** ở ít nhất một tầng: mỗi PR (không cần phần cứng), QEMU hằng đêm, hoặc bo
   mạch thật hằng đêm (TSK-S4-05).
4. **Ranh giới ghi rõ**: phần tầng đó không kiểm được được nêu ở cột "Chỉ phần cứng" và có một
   kiểm thử trên bo mạch.

## 2. Ma trận phủ

Ký hiệu: ✅ có trên `main` · 🟡 một phần · ⏳ có task, chưa làm. "PR" = chạy trên runner GitHub
mỗi PR, không cần phần cứng.

### `sim` — `sim-default` (mirror ESP32-S3-BOX-3, bất biến 7)

| Nguyên thủy | Backend | Kiểm ở | Trạng thái | Task |
|:---|:---|:---|:---:|:---|
| `digital.out` | `SimHAL`, token dùng một lần | PR | ✅ | TSK-S2-01, S2-05 |
| `audio.in` | Gõ chữ → ngữ pháp lệnh (Q-15) · tệp WAV → VAD + STT provider | PR (gõ chữ, WAV fixture) | 🟡 gõ chữ | WAV: TSK-S3-13 |
| `audio.out` | Chữ sẽ nói (`tts_stream_start`) · âm thanh TTS ra WAV | PR | 🟡 chữ | WAV: TSK-S3-13 |
| `sensor.read` | Giá trị kịch bản: `[sim.sensors]` trong `agent.toml`, `:sensor` trong REPL | PR | 🟡 HAL có, agent/REPL chưa | TSK-S3-23 |
| `display` | Khung hình trong bộ nhớ, kiểm độ phân giải; digest SHA-256 + PNG | PR | 🟡 lưu khung, chưa xuất | TSK-S3-23 |
| *Trực quan* | Terminal (có) · `trace view` HTML tĩnh · `run --ui` web cục bộ (FR-TGT-06) | PR | 🟡 terminal | TSK-S3-22, S2-09 |

### `linux` — `linux-rpi5`

| Nguyên thủy | Backend | Kiểm ở | Chỉ phần cứng | Trạng thái | Task |
|:---|:---|:---|:---|:---:|:---|
| `digital.out` | `LinuxHAL` qua libgpiod v2 | PR — gpio-sim | Điện áp, timing | ✅ | TSK-S3-05 |
| `audio.in` | `sounddevice` (PortAudio) · AEC phần mềm PipeWire `module-echo-cancel` (Q-22) | PR — backend tệp/PCM không cần kernel; **runner không có `snd-aloop`** | Micro, AEC, âm học — RPi 5 + HAT I2S, `snd-aloop` trên Pi | ⏳ | TSK-S5-08 |
| `audio.out` | `sounddevice` | PR — như trên | Loa, âm lượng | ⏳ | TSK-S5-08 |
| `sensor.read` | sysfs **hwmon** và **IIO** (`/sys/class/hwmon/*/temp1_input`, `/sys/bus/iio/devices/iio:device*/in_*`) | PR — `i2c-stub` + driver `lm75` → hwmon (module có trên runner) | Cảm biến thật; IIO chỉ trên Pi (`CONFIG_IIO` tắt trên runner) | ⏳ | TSK-S5-09 |
| `display` | Khung hình → `/dev/fb*` trên Pi; trong bộ nhớ khi không có | PR — khung trong bộ nhớ + digest | Panel HDMI/DSI | ⏳ | TSK-S5-09 |

### `esp32s3` — `esp32s3-box-3`

| Nguyên thủy | Backend | Kiểm ở | Chỉ phần cứng | Trạng thái | Task |
|:---|:---|:---|:---|:---:|:---|
| `digital.out` | ESP-IDF `gpio` sau walker cây quyết định | PR — walker C trên host (bảng sự thật) · QEMU hằng đêm — lệnh ghi qua UART (QEMU không có GPIO matrix) | Chân thật | ⏳ | TSK-S4-01, S4-02, S4-07, S4-08, S4-09 |
| `audio.in` | I2S ES7210 + ESP-SR AFE (AEC, VAD) — driver từ XiaoZhi | **Không** — QEMU không có I2S; ESP-SR là thư viện Xtensa dựng sẵn, không chạy trên host | Toàn bộ | ⏳ | TSK-S5-01, S5-02 |
| `audio.out` | I2S ES8311 | Không | Toàn bộ | ⏳ | TSK-S5-02 |
| `sensor.read` | Driver I2C của ESP-IDF | QEMU — driver giả qua cùng giao diện HAL (QEMU không có I2C) | Bus I2C, cảm biến | ⏳ | TSK-S4-03 |
| `display` | `esp_lcd` + LVGL | PR — **cùng mã giao diện LVGL** build trên host với màn hình test LVGL, so ảnh golden · QEMU — `esp_lcd_qemu_rgb` | Đường SPI tới ILI9342C/ST7789 | ⏳ | TSK-S4-10 |

**Tổng:** 15 ô — 2 ✅, 4 🟡, 9 ⏳ — mỗi ô có task. Ba ô chỉ kiểm được trên bo mạch (`audio.in`,
`audio.out` của `esp32s3`, và phần âm học của `linux`); chúng nằm ở nightly TSK-S4-05 và tiêu chí
Sprint 5–6.

## 3. Sự kiện vết ghi theo nguyên thủy

Lược đồ `trace.v1` để `type` tự do và `data` là object, nên thêm loại sự kiện **không cần RFC**.
Tên và trường dưới đây là quy phạm; mọi target phát cùng tên.

| Nguyên thủy | Sự kiện | `data` | Vai trò khi replay |
|:---|:---|:---|:---|
| `audio.in` | `text_input` *(có)* · `audio_in_vad_start` *(có)* · `audio_in_segment` | `{text}` · `{energy_db}` · `{sha256, duration_ms, sample_rate_hz}` | **Đầu vào.** Replay bắt đầu từ kết quả nhận thức đã ghi (`intent_extracted`), không chạy lại âm thanh (L2) |
| `audio.out` | `tts_stream_start` *(có)* · `tts_stream_end` | `{text}` · `{duration_ms, sha256?}` | **Đầu ra L3** — không so |
| `digital.out` | `actuator_command` *(có)* · `actuator_aborted` *(có)* | `{pin, operation, duration_ms}` · `{pin, reason}` | **Quyết định** — so golden (L1) |
| `sensor.read` | `sensor_read` | `{sensor, value, unit}` | **Đầu vào** — replay cấp lại đúng giá trị đã ghi |
| `display` | `display_frame` | `{width, height, format, sha256}` | **Đầu ra** — so digest khi golden có ghi (L2), không chặn tương đương quyết định |

Chế độ ẩn danh (FR-TRC-07) băm `text`; `audio_in_segment` và `display_frame` vốn chỉ mang digest.

## 4. Vết ghi từ `esp32s3` về máy tính

Firmware ghi mỗi sự kiện thành **một dòng JSON trên UART0 / USB-CDC**, tiền tố `NE1 `, cùng
tên sự kiện ở §3:

```text
NE1 {"offset_ms":590,"type":"gate_evaluation_result","data":{"verdict":"ALLOW",...}}
```

`neuroedge record --target esp32s3 --port /dev/ttyACM0` đọc các dòng đó, bỏ dòng log khác, dựng
`trace.v1` và thẩm định trước khi ghi — cùng `TraceRecorder` của TSK-S3-01. Trong QEMU, UART0 ra
stdio hoặc socket (`-serial tcp::5555,server,nowait`), nên **cùng lệnh chạy trên QEMU** và
`metadata.device_id = "qemu"` phân biệt bằng chứng giả lập với bằng chứng bo mạch. Nhờ vậy
`verify --targets esp32s3` kiểm được **miền quyết định** hằng đêm trên QEMU trước khi bo mạch về,
và trên bo mạch sau đó (TSK-S4-09).

## 5. Trực quan hoá

Bốn bề mặt, cùng một bộ thành phần SVG tự vẽ (chốt cửa, đèn, relay, đồng hồ cảm biến, khung màn
hình). Không phụ thuộc CDN: `sim` phải chạy không mạng (FR-DX-02).

| Bề mặt | Dùng khi | Đáp ứng | Task |
|:---|:---|:---|:---|
| Terminal (`run`, `replay`, `gate explain`) | Hằng ngày, CI | Có | TSK-S3-06, S3-18 |
| `neuroedge trace view <tệp>` → một tệp HTML tĩnh | Xem lại, gửi đồng nghiệp, debug sự cố | Dòng thời gian, phán quyết + lý do, chân, cảm biến, khung màn hình; mở không cần server | TSK-S3-22 |
| `neuroedge run --ui` → trang web cục bộ, cập nhật trực tiếp | Demo, hành trình 10 phút | FR-TGT-06: trạng thái chân ảo theo thời gian thực; gõ lệnh, đặt cảm biến | TSK-S2-09 |
| `neuroedge trace export --format chrome` → Perfetto | Phân tích timing | Mở trong Perfetto UI (Apache-2.0) | TSK-S3-22 |

Wokwi Elements (MIT) có thể thay phần hiển thị đèn, servo, relay, màn hình `ili9341` nếu đóng gói
kèm (không tải CDN); không có sẵn chốt cửa.

## 6. Ba thiết bị chạy cùng agent mẫu

FR-TGT-02 và FR-TGT-03 đòi **agent mẫu chạy thật** trên RPi 5 và Box-3. Hôm nay agent mẫu
`villa-concierge` khai `audio.in aec = true`, và `linux-rpi5` khai `aec = false`, nên `build
--target linux` từ chối nó — agent mẫu chỉ phủ 2/3 thiết bị. Q-22 (đề xuất) đóng khoảng này:
`LinuxHAL` cung cấp AEC bằng PipeWire `module-echo-cancel` (webrtc-audio-processing, BSD-3), và
`linux-rpi5` khai `aec = true` khi TSK-S5-08 xong. Cho tới khi đó, kịch bản tương đương ba thiết bị
dùng agent chỉ cần `digital.out` (mẫu `minimal` của `neuroedge new`).

## 7. Điều tài liệu này không hứa

- Tương đương **timing** giữa target (TSK-S4-04 mới so quyết định).
- Chất lượng âm thanh, AEC, VAD dưới âm học thật — chỉ đo trên thiết bị (A6, Sprint 6).
- Target bậc 2–3 (`jetson`, `stm32`, `rp2350`) — RFC-0002.
