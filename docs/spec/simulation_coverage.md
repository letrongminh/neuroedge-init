# Phủ mô phỏng — 5 nguyên thủy × 3 target bậc 1

**Trạng thái:** đặc tả quy phạm, đi kèm Q-21 và Q-22 (*đã chốt*) — PRD §15. Tài liệu này nói **cái gì**
chạy và kiểm từng ô; ô nào đã xong là trạng thái của task tương ứng trong `neuroedge-roadmap.md`.
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

"PR" = chạy trên runner GitHub mỗi PR, không cần phần cứng. Trạng thái (xong / một phần / chưa)
không ghi ở đây: đọc task ở cột cuối trong bảng task của roadmap (`CONTRIBUTING.md` §8.1).

### `sim` — `sim-default` (mirror ESP32-S3-BOX-3, bất biến 7)

| Nguyên thủy | Backend | Kiểm ở | Task |
|:---|:---|:---|:---|
| `digital.out` | `SimHAL`, token dùng một lần | PR | TSK-S2-01, S2-05 |
| `audio.in` | Gõ chữ → ngữ pháp lệnh (Q-15) · tệp WAV → VAD + STT provider | PR (gõ chữ, WAV fixture) | WAV: TSK-S3-13 |
| `audio.out` | Chữ sẽ nói (`tts_stream_start`): câu trả lời knowledge base (RAG qua System 2, cục bộ khi mất mạng), lời hỏi lại của `on_block: ask` · âm thanh TTS ra WAV | PR | chữ: TSK-S2-11 · WAV: TSK-S3-13 |
| `sensor.read` | Giá trị kịch bản: `[sim.sensors]` trong `agent.toml`, `:sensor` trong REPL và UI; dữ kiện gate từ cảm biến: `[sim.sensor_facts]`; `sensor.read()` trong `@action` | PR | TSK-S3-23 |
| `display` | Khung chữ hoặc điểm ảnh RGB565/RGB888 trong bộ nhớ, kiểm độ phân giải; digest SHA-256; `display.show()` trong `@action` | PR | TSK-S3-23 |
| *Trực quan* | Terminal · `trace view` HTML tĩnh · `run --ui` và `mcp serve --ui` web cục bộ (FR-TGT-06) | PR | TSK-S3-22, S2-09, S3-27 |

**Dữ kiện gate từ cảm biến — `[sim.sensor_facts]`.** Mỗi dòng `tiêu_chí = { sensor = "…", <luật> }`
tính một dữ kiện gate từ số đọc, như nhau trên `sim` (giá trị kịch bản) và `linux` (số đọc kernel).
Mỗi cảm biến được đọc **một lần mỗi lần tính dữ kiện gate** (`gate_facts`: các tool call của một lượt
lệnh, một câu trả lời xác nhận, một tool call qua MCP), nên hai dữ kiện của cùng một cảm biến không bao
giờ tính trên hai số đọc khác nhau. Hiện thực: `SensorFact` và `SimSession.gate_facts` trong
`python/neuroedge/sim/session.py`.

| Luật | Dữ kiện | Ví dụ |
|:---|:---|:---|
| *(không có)* | Chính số đọc | `door_closed = { sensor = "door_contact" }` |
| `equals` | `bool`: số đọc bằng giá trị — giá trị là bool, chữ hoặc số hữu hạn | `room_empty = { sensor = "motion", equals = false }` |
| `gte` / `lte` (một hoặc cả hai) | `bool`: số đọc ≥ / ≤ ngưỡng — **tính cả ngưỡng** | `too_hot = { sensor = "temperature", gte = 30 }` |
| `bands` | `level`: dải chứa số đọc | `heat_level = { sensor = "temperature", bands = { low = -40, normal = 25, high = 40, critical = 55 } }` |

Kiểm khi nạp phiên — sai ⇒ lỗi ba phần (`AgentManifestError`, cảm biến bo mạch không có ⇒
`BoardCapabilityError`), **trước khi** xin line GPIO nào:

- Mỗi dòng **một** luật: `bands`, `equals`, `gte`/`lte` không đi chung. Ngưỡng là số hữu hạn (không
  phải bool, NaN, inf). Cảm biến phải là cảm biến bo mạch khai.
- Luật số (`gte`, `lte`, `bands`) cần đơn vị khai ở `[sim.sensors]`
  (`temperature = { value = 45, unit = "C" }`), để `linux` từ chối số đọc khác đơn vị thay vì đem so
  với ngưỡng (luật `linux` dưới đây).
- `bands`: mỗi mục là `mức = ngưỡng dưới`, ngưỡng **tăng ngặt** theo thứ tự viết. Một dải bắt đầu
  **tại** ngưỡng của nó và dừng ngay dưới ngưỡng của mục kế tiếp; dải cuối không có cận trên. Ví dụ
  trên: 24,999 → `low`, 25 → `normal`, 54,999 → `high`, 55 → `critical`. Phải có ít nhất một gate
  đọc tiêu chí đó; mọi gate đọc nó khai kiểu `level`, và với từng gate: mức là mức gate khai ở
  `evaluate.<tiêu_chí>.levels`, viết **đúng thứ tự** đó, và **mục cuối là mức cao nhất** của gate —
  chỉ được bỏ mức thấp hoặc mức giữa, để số đọc cao tới đâu cũng không dừng dưới mức trên cùng.
- Trên cảm biến có `bands`, `gte` phải **trùng một ngưỡng** của các `bands` đó (dữ kiện bool là
  "từ dải này trở lên", không lệch khỏi dải ở số đọc nào); `lte` bị từ chối, vì ngưỡng thuộc dải
  phía trên nên `lte` sẽ lệch đúng tại ngưỡng.
- Tiêu chí do cảm biến quyết không được có giá trị cố định ở `[sim.facts]` (hay `SimSession.load(facts=)`):
  giá trị đó không bao giờ được đọc. `:set` trong REPL và trang `--ui` từ chối nó và chỉ sang `:sensor`.

Lúc chạy — fail-closed, không đoán:

- Một số đọc **không lấy được** (cờ lỗi, NaN hay tệp hỏng trên `linux`, thiết bị biến mất, `sim` chưa có
  giá trị), hoặc bị **một luật bất kỳ của cảm biến đó** từ chối — luật số trên số đọc không phải số hữu
  hạn (chữ, bool, NaN, inf), `bands` trên số đọc dưới ngưỡng đầu tiên (đầu dò hở/chập), `equals` trên số
  đọc khác kiểu (`0` không phải `false`), chính số đọc khi nó rỗng hay không hữu hạn — thì **mọi** dữ kiện
  của cảm biến đó trong lần tính ấy là **chưa xác định** (`null` trong `gate_facts`), và phiên ghi
  `sensor_unavailable` (§3). Gate đọc chúng chặn với `criterion_unavailable`; vì cả tiêu chí phủ quyết
  (`heat_critical`) cũng chưa xác định, một lời "có" không đủ nên thiết bị **không hỏi**. Gate không đọc
  dữ kiện nào của cảm biến đó quyết như thường (`vent_on` của `factory-monitor` vẫn chạy).
- Câu trả lời xác nhận tính lại dữ kiện: hỏi lúc 45 °C, cảm biến hỏng trước lời "có" ⇒ vẫn chặn.
- Replay dùng lại `gate_facts` đã ghi, nên không tính lại được dữ kiện cảm biến. Vết ghi mang digest
  của `[sim.sensor_facts]` (`metadata.sensor_facts_digest`); luật đổi sau khi ghi thì `replay` cảnh báo
  (sự kiện `sensor_facts_changed` trong vết ghi phát lại) — phán quyết khi đó không kiểm luật mới, cần
  ghi lại phiên. Đây là cảnh báo, không phải khác biệt quyết định: mã thoát không đổi.

### `linux` — `linux-rpi5`

| Nguyên thủy | Backend | Kiểm ở | Chỉ phần cứng | Task |
|:---|:---|:---|:---|:---|
| `digital.out` | `LinuxHAL` qua libgpiod v2 | PR — gpio-sim | Điện áp, timing | TSK-S3-05 |
| `audio.in` | `sounddevice` (PortAudio) · AEC phần mềm PipeWire `module-echo-cancel` (Q-22) | PR — backend tệp/PCM không cần kernel; **runner không có `snd-aloop`** | Micro, AEC, âm học — RPi 5 + HAT I2S, `snd-aloop` trên Pi | TSK-S5-08 |
| `audio.out` | `sounddevice` | PR — như trên | Loa, âm lượng | TSK-S5-08 |
| `sensor.read` | sysfs **hwmon** và **IIO** (`/sys/class/hwmon/*/temp1_input`, `/sys/bus/iio/devices/iio:device*/in_*`) — `hal/sysfs.py` | PR — `i2c-stub` + driver `lm75` → hwmon (`scripts/setup_i2c_stub.sh`, `tests_linux/`); IIO trên cây sysfs giả (`tests/test_hal_linux_io.py`) | Cảm biến thật; IIO chỉ trên Pi (`CONFIG_IIO` tắt trên runner) | TSK-S5-09 |
| `display` | Kiểm và ghi khung bằng đúng mã của `sim` (`make_frame`), rồi → `/dev/fb*` trên Pi, hoặc chỉ trong bộ nhớ — `hal/framebuffer.py` | PR — khung trong bộ nhớ + digest; `/dev/fbN` của `vfb`, hoặc `vkms` trên kernel azure (`scripts/setup_vfb.sh`) | Panel HDMI/DSI | TSK-S5-09 |

**Cảm biến trên `linux` tìm theo tên, không theo số thứ tự** (`hwmon3`, `iio:device0` đổi theo thứ
tự probe), như chân GPIO tìm theo tên line: kênh có nhãn trùng tên cảm biến của bo mạch, hoặc một
**nguồn** đặt theo máy — `LinuxHAL(sensor_sources=…)` hoặc biến môi trường `NEUROEDGE_LINUX_SENSORS`.
Cú pháp nguồn và bảng đơn vị: `python/neuroedge/hal/sysfs.py`. Nguồn không nằm trong `boards/*.toml`
(`board.v1` chưa có trường cho nó — khai bus I2C trong bo mạch là RFC-0007); khoá của nó phải là cảm
biến bo mạch khai. Luật an toàn:

- Mỗi lần đọc đi tới kernel; không nguồn, hai nguồn, tệp không đọc được, giá trị không phải số hữu
  hạn, cờ `*_fault`, hay loại kênh không rõ đơn vị ⇒ `BoardCapabilityError`, không bao giờ trả giá
  trị mặc định. "Tới kernel" không có nghĩa là mới hơn chu kỳ cập nhật của driver (lm75 ≈ 1,5 s).
- Agent khai đơn vị cho cảm biến (`[sim.sensors] temperature = { value = …, unit = "C" }`) thì số đọc
  của kernel khác đơn vị đó bị từ chối, không đem so với ngưỡng viết cho đơn vị kia. Dữ kiện gate tính
  từ số đọc kernel bằng đúng luật `[sim.sensor_facts]` của `sim` (trên), gồm `bands`.
- Replay chỉ dùng giá trị đã ghi: cảm biến vết ghi không có số đọc thì báo lỗi, không đọc kernel; khung
  hình vẽ trong bộ nhớ.
- `door_contact` và `motion` của `linux-rpi5` là đầu vào GPIO, không phải hwmon/IIO: chưa đọc được trên
  `linux`, agent cần chúng bị từ chối trước khi xin line.

**Màn hình chọn rõ, không đoán:** `LinuxHAL(display="memory" | "/dev/fbN")` hoặc
`NEUROEDGE_LINUX_DISPLAY`; không chọn thì `display` báo lỗi. Framebuffer đọc bố cục điểm ảnh từ
kernel (ioctl `FBIOGET_*SCREENINFO`: 16/24/32 bit, vị trí màu; chế độ grayscale/FOURCC/`msb_right` bị
từ chối), ghi từng hàng từ góc trên trái, mở thiết bị mỗi khung rồi đóng ngay; khung chữ bị từ chối
(không có font — `memory` nhận). Phiên tương tác (`run`, `record`, `mcp serve --target linux`) kiểm
mọi cảm biến agent và `[sim.sensor_facts]` cần, và backend màn hình nếu agent cần `display`, **trước
khi** xin line GPIO nào.

### `esp32s3` — `esp32s3-box-3`

| Nguyên thủy | Backend | Kiểm ở | Chỉ phần cứng | Task |
|:---|:---|:---|:---|:---|
| `digital.out` | ESP-IDF `gpio` sau walker cây `NETR` và sổ token C | PR — walker và sổ token C biên dịch trên host (bảng sự thật, ASan/UBSan) · QEMU (`firmware-qemu`, mỗi PR đụng `targets/**` và hằng đêm) — self-test gate lúc boot; lệnh chân qua UART (QEMU không có GPIO matrix) | Chân thật | walker, sổ token, self-test: TSK-S4-02, S4-07, S4-08 · chân: S4-01 · UART: S4-09 |
| `audio.in` | I2S ES7210 + ESP-SR AFE (AEC, VAD) — driver từ XiaoZhi | **Không** — QEMU không có I2S; ESP-SR là thư viện Xtensa dựng sẵn, không chạy trên host | Toàn bộ | TSK-S5-01, S5-02 |
| `audio.out` | I2S ES8311 | Không | Toàn bộ | TSK-S5-02 |
| `sensor.read` | Driver I2C của ESP-IDF | QEMU — driver giả qua cùng giao diện HAL (QEMU không có I2C) | Bus I2C, cảm biến | TSK-S4-03 |
| `display` | `esp_lcd` + LVGL | PR — **cùng mã giao diện LVGL** build trên host với màn hình test LVGL, so ảnh golden · QEMU — `esp_lcd_qemu_rgb` | Đường SPI tới ILI9342C/ST7789 | TSK-S4-10 |

Mỗi ô có task. Ba ô chỉ kiểm được trên bo mạch (`audio.in`, `audio.out` của `esp32s3`, và
phần âm học của `linux`); chúng nằm ở nightly TSK-S4-05 và tiêu chí Sprint 5–6.

## 3. Sự kiện vết ghi theo nguyên thủy

Lược đồ `trace.v1` để `type` tự do và `data` là object, nên thêm loại sự kiện **không cần RFC**.
Tên và trường dưới đây là quy phạm; mọi target phát cùng tên. Sự kiện nào đã được phát trên target
nào đi theo ô tương ứng ở §2. Cột "Vai trò khi replay" nói phần nào vào **so khớp quyết định**
(phán quyết gate + lệnh chân, như `replay` và `verify` so) — các cấp đảm bảo L1–L3 của Action CI
định nghĩa ở `neuroedge-prd.md` FR-CI-LVL.

| Nguyên thủy | Sự kiện | `data` | Vai trò khi replay |
|:---|:---|:---|:---|
| `audio.in` | `text_input` · `audio_in_vad_start` · `audio_in_segment` | `{text}` · `{energy_db}` · `{sha256, duration_ms, sample_rate_hz}` | **Đầu vào.** Replay bắt đầu từ kết quả nhận thức đã ghi (`intent_extracted`), không chạy lại âm thanh |
| `audio.out` | `tts_stream_start` · `tts_stream_end` · `knowledge_retrieved` | `{text}` · `{duration_ms, sha256?, reason?}` (`reason`: `docs/spec/voice_fsm.md` §8) · `{entries: [{id, score}]}` | **Đầu ra** — chữ không vào so khớp quyết định; `knowledge_retrieved` cho biết câu trả lời dựa trên tri thức nào |
| `digital.out` | `actuator_command` · `actuator_aborted` | `{pin, operation, duration_ms}` · `{pin, reason}` | **Quyết định** — so golden ở mọi lần `replay` / `verify` |
| `sensor.read` | `sensor_read` · `sensor_set` · `sensor_unavailable` | `{sensor, value, unit?, use?, non_finite?}` · `{sensor, value, non_finite?}` · `{sensor, reason}` | **Đầu vào** — replay cấp lại đúng giá trị đã ghi; lần đọc `use: fact` (tính dữ kiện gate) không cấp lại vì kết quả đã ở `gate_facts`. `sensor_set` ghi việc người dùng đổi giá trị trong REPL/UI. `sensor_unavailable`: một lần tính dữ kiện gate không lấy được số đọc, hoặc một luật của cảm biến từ chối nó (§2), nên mọi dữ kiện của cảm biến đó là `null`; chỉ để đọc, replay dùng `gate_facts` |
| `display` | `display_frame` | `{width, height, format, sha256, text?}` (`text` khi `format = "text"`) | **Đầu ra** — so digest khi golden có ghi, không chặn tương đương quyết định |

Chế độ ẩn danh (FR-TRC-07) băm `text`; `audio_in_segment` và `display_frame` vốn chỉ mang digest.

**Không có NaN hay vô cực trong JSON.** JSON không có các số đó (`NaN` trần làm `JSON.parse` của trình
duyệt dừng, và trang `--ui` dừng theo). Số đọc không hữu hạn ghi thành chuỗi `"nan"`, `"inf"`, `"-inf"`
kèm `non_finite: true`, và replay đọc lại thành số thực. Mọi sự kiện khác, siêu dữ liệu, trang `--ui` và
`trace view` cũng không bao giờ mang số không hữu hạn (`json_safe` trong `python/neuroedge/trace.py`);
`trace validate` từ chối tệp có `NaN`/`Infinity` trần. Siêu dữ liệu `sensor_facts_digest` và sự kiện
`sensor_facts_changed` (chỉ ở vết ghi phát lại): §2, luật `[sim.sensor_facts]`.

Sự kiện ngoài nguyên thủy (tool call, xác nhận, MCP host, `system_two_*`, đo lượt `turn_latency` /
`session_summary`) ở danh mục duy nhất `docs/spec/tool_calling.md` §7; sự kiện của máy trạng thái hội thoại (`voice_state_changed`,
`wake_word_detected`, `audio_in_vad_end`, `stt_result`) ở `docs/spec/voice_fsm.md` §8. Replay bỏ qua `system_two_call`: System 2 không đổi phán quyết, nên
phiên ghi online replay được mà không cần model hay key.

## 4. Vết ghi từ `esp32s3` về máy tính

Firmware ghi mỗi sự kiện thành **một dòng trên UART0 / USB-CDC**: tiền tố `NE1 ` rồi đúng một sự
kiện `trace.v1`, cùng tên và trường ở §3 và ở `docs/spec/tool_calling.md` §7. Đây là đặc tả của
TSK-S4-09 (trạng thái ở roadmap); định dạng C ở `targets/esp32s3/components/ne_trace/`, bộ đọc ở
`python/neuroedge/testing/uart.py`.

```text
I (312) boot: ESP-IDF v5.4 2nd stage bootloader           ← log thường: bỏ qua
NE1 {"offset_ms":0,"type":"device_info","data":{"board_id":"esp32s3-box-3","agent_version":"home-voice@0.1.0","device_id":"qemu","boot_id":"9f2c01aa"}}
NE1 {"offset_ms":3,"type":"gate_evaluation_begin","data":{"gate":"light_on@1.0.0","gate_digest":"sha256:4cc8…"}}
NE1 {"offset_ms":6,"type":"gate_facts","data":{"call_source":{"value":"local_grammar","confidence":null,"source":"context"}}}
NE1 {"offset_ms":9,"type":"gate_evaluation_result","data":{"verdict":"ALLOW","evaluations":{"call_source":"local_grammar"}}}
NE1 {"offset_ms":57,"type":"trace_end","data":{"events":4}}
NE_SELFTEST PASS walker=6 token=6
NE_TRACE DONE sessions=1
```

**Dòng.** `NE1 ` ở cột 0, rồi một object JSON có đúng ba khoá `offset_ms` (số nguyên ≥ 0, đồng hồ
thiết bị tính từ `device_info`), `type`, `data` — không khoá nào khác (lược đồ cấm). UTF-8, tối đa
**512 byte** kể cả tiền tố, kết thúc bằng `\n` (host nhận cả `\r\n`). Chuỗi escape theo JSON. Dòng
không vừa thì thiết bị **không** ghi nửa dòng: nó bỏ dòng và vẫn đếm (xem `trace_end`). Nonce của
token không bao giờ có trong dòng nào.

**Khung phiên.** Mỗi phiên mở bằng `device_info` ở `offset_ms` 0 và đóng bằng `trace_end`; sau phiên
cuối, thiết bị in `NE_TRACE DONE sessions=<n>` — dòng log thường, không phải sự kiện — để người đọc
biết nó không còn gì để nói.

| Sự kiện | `data` | Ý nghĩa |
|:---|:---|:---|
| `device_info` | `{board_id, agent_version, device_id, boot_id, replay_of?, trace_digest?}` | Thiết bị tự khai. `device_id = "qemu"` khi build với `sdkconfig.qemu` (`CONFIG_NEUROEDGE_QEMU`), còn trên chip là `esp32s3-<MAC>` — bằng chứng giả lập không bao giờ đọc thành bằng chứng bo mạch. `boot_id` là 8 chữ số hex ngẫu nhiên mỗi lần khởi động. `replay_of` / `trace_digest`: phiên replay một vết ghi chuẩn mực |
| `trace_end` | `{events}` | Số dòng của phiên trước nó, kể cả `device_info` và kể cả dòng thiết bị không ghi được. Host đếm lệch ⇒ lỗi |

**Firmware chỉ ghi cái nó tự tính.** Hôm nay: `gate_evaluation_begin {gate, gate_digest}`, `gate_facts`
(đầu vào của phán quyết, như host), `gate_evaluation_result` với đúng khoá của host
(`GateResult.to_event_data()`). Hai chỗ chưa như host, đều đọc lại được đúng khi replay: giá trị ngoài
miền, và độ tin cậy NaN, ghi là `null` (thiết bị chỉ biết "không đọc được"). Nhãn gate
(`light_on@1.0.0`) và chữ `on_block` (`to`, `message`, `fallback_action`) không có trong NETR v1 nên đi
kèm firmware, sinh từ cùng gate đã phân giải (`scripts/gen_firmware_gates.py`,
`scripts/gen_firmware_vectors.py`). Phiên self-test không có lệnh chân; lệnh chân chỉ có trong phiên
replay dưới đây, và chưa có `actuator_aborted`: chưa có HAL firmware (TSK-S4-01).

**Host.** `neuroedge record --target esp32s3 --port <nguồn>` giữ các dòng `NE1 `, bỏ mọi dòng khác
(kể cả `NE1001…`, `NE_SELFTEST`, `NEUROEDGE_MEMORY_JSON`), kiểm khung, rồi ghi **mỗi phiên một tệp**
qua `TraceRecorder` (TSK-S3-01), thẩm định trước khi ghi. Sự kiện là của thiết bị, nguyên văn và đúng
`offset_ms`. Host chỉ dựng `metadata`:

- `session_id = sess_<boot_id><số thứ tự phiên trong lần khởi động>`;
- `target = esp32s3`;
- `board_id`, `agent_version`, `device_id` lấy từ `device_info`;
- `timestamp_utc` là giờ host đọc được `device_info` — với tệp log là giờ đọc tệp, không phải giờ
  chạy.

Dòng `NE1` hỏng, khoá thừa, `trace_end` đếm lệch, phiên chưa đóng khi nguồn hết, hoặc phiên mới mở
khi phiên cũ chưa đóng (thiết bị khởi động lại) ⇒ `TraceValidationError` (NE4001) nêu `nguồn:dòng`.
Không bao giờ đọc một vết ghi ngắn hơn như thể nó là sự thật.

| `--port` | Nguồn | Dừng khi |
|:---|:---|:---|
| đường dẫn tệp, hoặc `file:<đường dẫn>` | log QEMU `-serial file:uart.log`, hoặc bản chụp đã lưu | `NE_TRACE DONE` hoặc hết tệp |
| `tcp://host:port` | QEMU `-serial tcp::5555,server` (QEMU chờ người đọc rồi mới boot, không mất dòng đầu) | `NE_TRACE DONE` hoặc `--timeout` |
| `/dev/tty…`, `COMn`, URL pyserial (`loop://`, `rfc2217://`…) | bo mạch, qua extra `neuroedge[serial]` | `NE_TRACE DONE` hoặc `--timeout` |

`--baud` mặc định 921600 (PRD Phụ lục D.2); USB-CDC bỏ qua baud.

**Thiết bị replay vết ghi chuẩn mực.** Sau self-test, firmware replay từng vết ghi ở
`fixtures/traces/` (`main/trace_vectors.c`, `CONFIG_NEUROEDGE_REPLAY_VECTORS`), mỗi vết ghi một phiên
có `replay_of` và `trace_digest` (digest JCS của tệp). Mỗi bước nhận đúng đầu vào mà `replay` cấp lại
cho engine host — dữ kiện đã ghi, lần thu thập suy giảm đã ghi, xác nhận của người —, sinh vào
`main/vectors/` bằng `scripts/gen_firmware_vectors.py`. Phần còn lại là của thiết bị:

| Trong phiên replay | Ai tính |
|:---|:---|
| Phán quyết, lý do, `fail_mode` (kể cả `gate_unreachable` / `budget_exceeded` theo `fail` của gate) | Thiết bị — walker C `ne_decide`, cùng ngữ nghĩa `engine/gate.py` (TSK-S4-07 kiểm trên mọi gate) |
| Có phát lệnh chân không, và chân nào | Thiết bị — sổ token C: token cấp cho chân của action, `ne_token_authorize` cho từng lệnh |
| `operation`, `duration_ms` của lệnh | **Host** — bảng hành động: chạy @action một lần trên `SimHAL` sau engine luôn-ALLOW, lúc sinh vector |

`actuator_command` trong phiên replay nghĩa là sổ token cho phép chân đó; **không chân GPIO nào
động**. Cách action thật sự chạy trên MCU thay bảng hành động ở TSK-S4-01. Script từ chối, không
đoán, những gì firmware chưa replay được: tham số có giới hạn, `degrade` + `fallback_action`, số đọc
cảm biến, độ tin cậy không phải số.

`neuroedge verify --targets esp32s3 --port <nguồn>` đọc các phiên đó và, cho mỗi vết ghi chuẩn mực, so
phiên có `replay_of` tương ứng với chính vết ghi đó làm golden — như `sim` và `linux` (TSK-S3-04;
lệch ⇒ NE4002). Trước khi so, nó từ chối (NE4003, "firmware cũ") phiên có `trace_digest` khác tệp
trong checkout, hoặc `gate_digest` khác gate checkout biên dịch ra: đó sẽ là kết quả về một thứ khác.
Thiếu `--port` ⇒ mã 1; thiếu phiên cho một vết ghi ⇒ ✗. Kết quả in rõ phần nào do thiết bị tính.

Firmware trên QEMU chạy mỗi PR đụng `targets/**` hoặc `fixtures/traces/`, và job `uart-trace` của
`firmware-qemu.yml` chạy `record` rồi `verify --targets esp32s3` trên log UART của nó. Bo mạch, replay
một vết ghi tuỳ ý trên thiết bị (gửi dữ kiện xuống) và so timing là phần còn lại của TSK-S4-04;
`replay --target esp32s3` vẫn thoát mã 2.

## 5. Trực quan hoá

Năm bề mặt, cùng một bộ thành phần SVG tự vẽ (chốt cửa, đèn, relay, đồng hồ cảm biến, khung màn
hình). Không phụ thuộc CDN: `sim` phải chạy không mạng (FR-DX-02).

| Bề mặt | Dùng khi | Đáp ứng | Task |
|:---|:---|:---|:---|
| Terminal (`run`, `replay`, `gate explain`) | Hằng ngày, CI | Có | TSK-S3-06, S3-18 |
| `neuroedge trace view <tệp>` → một tệp HTML tĩnh | Xem lại, gửi đồng nghiệp, debug sự cố | Dòng thời gian, phán quyết + lý do, chân, cảm biến, khung màn hình; mở không cần server | TSK-S3-22 |
| `neuroedge run --ui` → trang web cục bộ, cập nhật trực tiếp | Demo, hành trình 10 phút | FR-TGT-06: trạng thái chân ảo theo thời gian thực; gõ lệnh, đặt cảm biến, nút xác nhận `ask` | TSK-S2-09, S3-26 |
| `neuroedge mcp serve --ui` → cùng trang, cho phiên MCP | Claude Desktop hoặc agent khác gọi thiết bị, người xem và can thiệp trên trang | Như trên, trong **cùng phiên** với client MCP (`tool_calling.md` §8) | TSK-S3-27 |
| `neuroedge trace export --format chrome` → Perfetto | Phân tích timing | Mở trong Perfetto UI (Apache-2.0) | TSK-S3-22 |

Wokwi Elements (MIT) có thể thay phần hiển thị đèn, servo, relay, màn hình `ili9341` nếu đóng gói
kèm (không tải CDN); không có sẵn chốt cửa.

## 6. Ba thiết bị chạy cùng agent mẫu

FR-TGT-02 và FR-TGT-03 đòi **agent mẫu chạy thật** trên RPi 5 và Box-3. Hôm nay agent mẫu
`villa-concierge` khai `audio.in aec = true`, và `linux-rpi5` khai `aec = false`, nên `build
--target linux` từ chối nó — agent mẫu chỉ phủ 2/3 thiết bị. **Q-22 (đã chốt, phương án A)** đóng
khoảng này bằng AEC phần mềm của PipeWire, làm ở TSK-S5-08. Cho tới khi đó, kịch bản tương đương
ba thiết bị dùng agent chỉ cần `digital.out` (mẫu `minimal` của `neuroedge new`).

### 6.1 Cách nối

`libpipewire-module-echo-cancel` tạo bốn nút (tài liệu PipeWire, `page_module_echo_cancel`):

```text
micro ─► capture ─►┌─────────────┐─► source   ─► LinuxHAL.audio_in   (đã khử vang)
                   │ echo-cancel │
LinuxHAL.audio_out ─► sink ─────►└─────────────┘─► playback ─► loa
```

`audio.out` **phải** phát vào nút `sink`: đó là tín hiệu tham chiếu được trừ khỏi micro. Phát
thẳng ra loa thì AEC không có gì để trừ. Cách khác là `monitor.mode = true`, lấy tham chiếu từ
monitor của sink mặc định — dùng khi một tiến trình khác cũng phát ra loa.

Cấu hình giao kèm TSK-S5-08, đặt ở `~/.config/pipewire/pipewire.conf.d/` (người dùng) hoặc
`/etc/pipewire/pipewire.conf.d/` (hệ thống), rồi `systemctl restart --user pipewire.service`:

```text
# neuroedge-echo-cancel.conf
context.modules = [
{   name = libpipewire-module-echo-cancel
    args = {
        library.name = "aec/libspa-aec-webrtc"
        node.description = "NeuroEdge Echo Cancel"
        capture.props  = { node.name = "neuroedge.ec.capture"
                           target.object = "<micro của HAT I2S>" }  # chỉ định micro
        source.props   = { node.name = "neuroedge.ec.source" }      # audio.in đọc ở đây
        sink.props     = { node.name = "neuroedge.ec.sink" }        # audio.out phát vào đây
        playback.props = { node.name = "neuroedge.ec.playback"
                           node.autoconnect = true }
    }
}
]
```

Chỉ định micro bằng `capture.props.target.object` và tắt tự nối ở những nút không được nối tự do
là mẫu lấy từ cấu hình tham khảo (gist `fathonix/05de5398…`, micro Android qua ROC). Tên nút của
micro HAT và việc Raspberry Pi OS có chạy PipeWire mặc định hay không phải kiểm trên Pi khi làm
TSK-S5-08.

### 6.2 Khi nào `linux-rpi5` được khai `aec = true`

Chỉ khi nightly trên RPi 5 (TSK-S4-05) đạt cả hai, trên cùng HAT và loa của bo tham chiếu:

1. **Không tự nghe mình:** phát 20 lần một câu TTS cố định qua `audio.out` khi không ai nói —
   VAD trên `audio.in` không kích hoạt lần nào (0/20).
2. **Mức khử vang:** ERLE (năng lượng micro thô so với sau khử vang, cùng đoạn phát) ≥ 20 dB.

Chưa đạt thì `aec = false` giữ nguyên và `build` tiếp tục từ chối agent cần AEC — không có đường
nào để khai một năng lực chưa đo. Runner CI không có âm thanh (`CONFIG_SOUND` tắt), nên
hai phép đo này chỉ chạy trên Pi.

## 7. Điều tài liệu này không hứa

- Tương đương **timing** giữa target (TSK-S4-04 mới so quyết định).
- Chất lượng âm thanh, AEC, VAD dưới âm học thật — chỉ đo trên thiết bị (A6, Sprint 6).
- Target bậc 2–3 (`jetson`, `stm32`, `rp2350`) — RFC-0002.
