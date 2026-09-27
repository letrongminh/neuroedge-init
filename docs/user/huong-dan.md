# Hướng dẫn sử dụng — hôm nay làm được gì

> Bản đồ tài liệu ở [`README.md`](README.md). Cú pháp lệnh và đầu ra kỳ vọng
> nằm ở [`CHANGELOG.md`](../../CHANGELOG.md) §2.3 — tệp này không chép lại.

## 1. Cài đặt

Chưa có bản phát hành ra ngoài: PyPI mở ở I6 — Công khai (`Q-39`, `TSK-S3-14`,
[`docs/release.md`](../release.md)). Trước đó, cài từ mã nguồn theo
[`python/README.md`](../../python/README.md), hoặc từ wheel nội bộ của increment gần nhất
khi đội đưa cho bạn (tag: roadmap §0.2). Từ I6, cài như [`README.md`](../../README.md) gốc.

Yêu cầu: Python 3.11+ (`Q-1`). `sim` mặc định **gõ chữ** — không cần khoá API,
không cần mạng, kết quả tất định (`Q-15`).

## 2. Hôm nay dùng được gì

Bảng dưới là từng việc làm được hôm nay; cú pháp từng lệnh ở `CHANGELOG.md` §2.3.
Thử ngay trong kho:

```bash
neuroedge run -c "mở cửa phòng 101"    # ✓ ALLOW, door_lock PULSED 30s
neuroedge run -c "mở cửa phòng 202"    # ✗ BLOCK room_matches → lễ tân
neuroedge new my-agent                 # dự án mới: build được, `neuroedge test` tự qua
neuroedge record -c "mở cửa phòng 101" # ghi phiên ra traces/<session_id>.json
neuroedge replay traces/sess_….json    # phát lại, tính lại phán quyết, so với bản ghi
```

| Việc | Lệnh | Trạng thái |
|:---|:---|:---:|
| Kiểm cả kho gate phân giải được | `neuroedge gate lint` | ✅ |
| Xem gate đã phân giải, kiểm tra kế thừa | `neuroedge gate resolve` | ✅ |
| In digest để ghim phiên bản gate | `neuroedge gate publish` | ✅ |
| Thẩm định vết ghi theo `trace.v1` | `neuroedge trace validate` | ✅ |
| Xem nội dung một vết ghi | `neuroedge trace show` | ✅ |
| Xem độ trễ từng chặng và tỷ lệ System 1 / System 2 của một phiên | `neuroedge trace show` (sự kiện `turn_latency`, `session_summary`) | ✅ |
| Liệt kê / xem profile bo mạch | `neuroedge board list` · `neuroedge board show` | ✅ |
| Đối chiếu năng lực agent ↔ bo mạch, biên dịch gate (cả cây nhị phân `.netree` cho thiết bị, RFC-0003) | `neuroedge build` | ✅ |
| Sinh firmware ESP-IDF cho agent của mình rồi nạp lên Box-3 — gate chạy và tự kiểm trên chip | `neuroedge build --target esp32s3` → `idf.py flash` ([`nap-firmware.md`](nap-firmware.md)) | ✅ trên QEMU · bo mạch ⏳ · chưa chân GPIO nào động (TSK-S4-01) |
| Chạy agent có gate trên `sim` từ mã Python (`c.do()` trên `SimHAL`) | — (thư viện) | ✅ |
| Chạy agent có gate trên `sim` từ dòng lệnh (gõ chữ, không mạng) | `neuroedge run` | ✅ |
| Xem phiên `sim` trực tiếp trên trình duyệt: chốt cửa, đèn, cảm biến, màn hình | `neuroedge run --ui` | ✅ |
| Mở một vết ghi thành trang HTML để xem lại, tua thời gian, gửi đồng nghiệp | `neuroedge trace view` | ✅ |
| Xuất vết ghi để phân tích thời gian trong Perfetto | `neuroedge trace export --format chrome` | ✅ |
| Giả lập cảm biến và màn hình trên `sim` | `[sim.sensors]` · `:sensor` · `display.show()` | ✅ |
| Đổi số đọc cảm biến thành dữ kiện gate: so ngưỡng, hoặc dải cho tiêu chí `level` (25 °C → `normal`) — trên `sim` và `linux` | `[sim.sensor_facts]`: `gte` / `lte` · `bands` — luật ở [`simulation_coverage.md`](../spec/simulation_coverage.md) §2 | ✅ |
| Đọc một gate bằng lời: tiêu chí từ đâu, điều gì bị siết chặt | `neuroedge gate explain` | ✅ |
| Tạo dự án agent mới có sẵn gate, action, test, và cây `traces/` (`incidents/`, `golden/` — FR-TRC-09) | `neuroedge new` | ✅ |
| Xem ví dụ chạy được của một lệnh | `neuroedge <lệnh> --help` (mục `Examples:`) | ✅ |
| Thử một trợ lý giọng nói: hỏi đáp knowledge base, tin tức, bật/tắt đèn qua gate | `neuroedge new nha --template home-voice` | ✅ |
| Xem các `@action` dưới dạng tool (schema cho LLM / MCP) | `neuroedge mcp tools` | ✅ |
| Cho Claude Desktop hoặc agent khác gọi thiết bị qua MCP — vẫn qua gate | `neuroedge mcp serve` (cấu hình Claude Desktop: dòng dưới, `desktop-config`) | ✅ cần `neuroedge[mcp]` |
| Ghi cấu hình Claude Desktop cho `mcp serve` (đường dẫn tuyệt đối, có sao lưu) | `neuroedge mcp desktop-config --agent … [--ui] --write` | ✅ cần `neuroedge[mcp]` |
| Điều khiển từ Claude Desktop và thấy đèn/chốt ảo đổi trên trình duyệt — cùng một phiên | `neuroedge mcp serve --ui` (trang ở http://127.0.0.1:8765) | ✅ cần `neuroedge[mcp]` |
| Cho System 2 dùng MCP server bên ngoài (tin tức, tra cứu) — chỉ lấy thông tin | `[mcp.servers]` trong `agent.toml` · `neuroedge mcp tools --external` | ✅ cần `neuroedge[mcp]` |
| Dùng LLM thật cho System 2 (Claude, GPT, DeepSeek qua OpenRouter…): câu tự do thành tool call, vẫn qua gate | `[system_two]` trong `agent.toml` · key ở biến môi trường (`api_key_env`), **không** ghi vào tệp | ✅ cần `neuroedge[cloud]` |
| Mất mạng hoặc System 2 không trả lời: thiết bị nói các lệnh cục bộ còn dùng được (`offline_help`) | — (tự động) | ✅ |
| Cho model cloud của System 1 — Jev (`typesafe/jev-1.13` qua OpenRouter, Q-4) — quyết định một tiêu chí gate từ **lời người nói**. Chỉ các tiêu chí bạn liệt kê, và chỉ tiêu chí mà lời nói tự nó xác lập được (vd người dùng muốn gì). **Không bao giờ** giao tiêu chí danh tính, quyền hay đặt phòng (`guest_authenticated`, `staff_co_authorized`, `room_matches`): đó là dữ kiện phiên từ hệ thống quản lý; dữ kiện trong ngữ cảnh luôn thắng model, còn một dữ kiện vắng mặt sẽ bị quyết từ lời người nói. Model không trả lời được (mất mạng, hết giờ, trả sai hợp đồng, dưới ngưỡng) thì ngữ pháp lệnh quyết như cũ, vết ghi có `system_one_fallback` | `[system_one]` trong `agent.toml`: `model = "typesafe/jev-1.13"`, `api_key_env = "OPENROUTER_API_KEY"`, `criteria = ["…"]`, tuỳ chọn `threshold` (0.8, tối thiểu 0.5), `timeout_ms` (1500), `api_base` (https, hoặc máy này) · thử với key thật: `python scripts/live_jev_smoke.py` | ✅ không cần extra. Build từ chối: tiêu chí agent tự tính (`[sim.facts]`, `[sim.slot_facts]`, `[sim.sensor_facts]`), tiêu chí System One API không hỏi được, và gate có `budget.p95_latency_ms` < `timeout_ms` + 50 |
| Nói với agent trên `sim` bằng tệp WAV (16 kHz mono): STT/TTS qua provider chuẩn OpenAI audio — OpenAI, Groq, faster-whisper, Kokoro… đổi bằng `base_url`; bản chép lời qua gate như lệnh gõ, nói chen thì loa dừng và lệnh chưa giao bị hủy | `[stt]` / `[tts]` trong `agent.toml` (key ở biến môi trường, `api_key_env`) · `neuroedge run --voice-file x.wav [--voice-out tra-loi.wav]` · `record --voice-file … --anonymize` | ✅ cần key STT hoặc server cục bộ; thử không key: provider giả `python:neuroedge.perception.providers.fake:stt` |
| Nói với agent trên `linux` bằng tệp WAV — chân là line GPIO thật, tệp được đưa về rate của bo mạch (48 kHz), không cần micro và không cần `sounddevice` | `neuroedge run --voice-file x.wav --target linux` · `record --voice-file x.wav --target linux --out traces/voice.json` (WAV: 16-bit PCM, 1–2 kênh, 8–96 kHz) | ✅ cần line GPIO + `neuroedge[linux]`; chạy trên gpio-sim trong CI (job `linux-hal`) |
| Đánh thức thiết bị bằng **từ khoá của bạn** thay vì để VAD mở lượt theo mọi tiếng nói: cắm mô hình wake-word của bạn (NeuroEdge **không giao và không tải mô hình nào**; giấy phép mô hình của openWakeWord chưa được xác lập/không thương mại, Q-45) | `[wake_word]` trong `agent.toml`: `model`, `melspectrogram`, `embedding` — **cả ba tệp .onnx là của bạn** (đường dẫn tương đối tính từ thư mục agent; build chỉ kiểm hình dạng bảng, phiên thoại kiểm tệp trước khi giữ line nào), `threshold` (0,5), `word` (tuỳ chọn) · `pip install 'neuroedge[wake]'` cho `provider = "openwakeword"` (cần openwakeword ≥ 0.6.0 + onnxruntime), hoặc adapter `python:pkg.mod:factory` | ✅ chạy trên `sim`/`linux` với tệp WAV; mô hình do bạn huấn luyện/được phép dùng và bạn chịu trách nhiệm giấy phép; bộ phát hiện lỗi ⇒ `wake_word_unavailable`, không lượt nào mở, phiên vẫn chạy |
| STT chính hỏng thì đổi sang endpoint cục bộ (faster-whisper / speaches trên máy) — bản chép lời của fallback đi đúng đường lệnh cũ, vết ghi có `stt_fallback`; chỉ cả hai hỏng mới có câu offline (Q-14) | `[stt.fallback]` cạnh `[stt]`: `base_url = "http://localhost:8000/v1"`, `model`, `timeout_s` (không cần key với server cục bộ) · `neuroedge run --voice-file x.wav` | ✅ cần server cục bộ chạy; endpoint khác máy qua `http://` mà có key bị build từ chối |
| Micro và loa thật trên `linux` qua PipeWire đã khử vang (Q-22): `audio.in` đọc nút `neuroedge.ec.source`, `audio.out` phát vào `neuroedge.ec.sink` | `pip install 'neuroedge[audio]'` · `NEUROEDGE_LINUX_AUDIO=live` · sao chép `pipewire/neuroedge-echo-cancel.conf` (trong wheel: `neuroedge.paths.echo_cancel_conf()`) vào `~/.config/pipewire/pipewire.conf.d/` rồi `systemctl restart --user pipewire.service`; ghim micro HAT bằng dòng `target.object` duy nhất trong tệp — [`simulation_coverage.md`](../spec/simulation_coverage.md) §6.1 | 🟡 nguyên thủy HAL đã có, chạy thử được; **chưa kiểm trên phần cứng** (PortAudio/ALSA ↔ tên nút PipeWire, micro/loa HAT: nightly TSK-S4-05); phiên thoại thời gian thực: `TODOS.md` #45 |
| Nối model chưa theo chuẩn OpenAI bằng adapter tự viết | `provider = "python:pkg.mod:factory"` trong `[system_two]` (trả provider) hoặc `[system_one]` (trả `FactSource`, câu trả lời vẫn bị kiểm miền giá trị và ngưỡng) | ✅ |
| Người xác nhận khi gate hỏi lại (`ask`): gõ `có` / `không`, hoặc nút Đồng ý / Huỷ trên `run --ui` | `neuroedge run` · `neuroedge run --ui` | ✅ gate phải khai `confirms` |
| Ghi một phiên ra vết ghi (có chế độ ẩn danh) | `neuroedge record` | ✅ |
| Phát lại vết ghi trên `sim` / `linux`, so golden | `neuroedge replay` | ✅ |
| Chạy test an toàn của agent (Action CI) | `neuroedge test` | ✅ |
| Kiểm cả kho: gate, vết ghi chuẩn mực, corpus tool call, replay | `neuroedge verify` | ✅ |
| Kiểm cùng quyết định trên `sim` và `linux` (A2) | `neuroedge verify --targets sim,linux` | ✅ cần line GPIO |
| Ghi vết ghi từ firmware `esp32s3` qua UART | `neuroedge record --target esp32s3 --port <log · tcp://… · /dev/tty…>` | ✅ trên QEMU · bo mạch ⏳ |
| Kiểm cùng quyết định trên `esp32s3`: firmware replay các vết ghi chuẩn mực | `neuroedge verify --targets esp32s3 --port …` | ✅ trên QEMU · bo mạch ⏳ |
| Phiên gõ chữ tương tác trên `linux`: chân là line GPIO thật | `neuroedge run` / `record` / `mcp serve --target linux` | ✅ cần line GPIO + `neuroedge[linux]`; agent được cần cả năm nguyên thủy, gồm `audio.in` / `audio.out` (âm thanh: hai hàng dưới) |
| Đọc cảm biến thật trên `linux` (hwmon, IIO) và vẽ lên màn hình (`/dev/fb*`, hoặc trong bộ nhớ) | `NEUROEDGE_LINUX_SENSORS="temperature=hwmon:lm75/temp1"` · `NEUROEDGE_LINUX_DISPLAY=/dev/fb0` (hoặc `memory`) — [`simulation_coverage.md`](../spec/simulation_coverage.md) §2 (`linux`) | ✅ trên hwmon ảo (`i2c-stub` + `lm75`) và framebuffer ảo (`vfb`, `vkms`) trong CI · Pi ⏳ |
| Cập nhật firmware `esp32s3` qua mạng: ảnh ký RSA-3072 bằng khóa của bạn, khe A/B, chỉ xác nhận sau self-test, hỏng thì tự quay về, không nhận bản cũ hơn | lớp `sdkconfig.ota` khi build; URL ở Kconfig hoặc NVS — [`nap-firmware.md`](nap-firmware.md) §6 | ✅ trên QEMU · Box-3 ⏳ (chưa có Wi-Fi thật) |
| Màn hình thiết bị nói ngôn ngữ của agent (`vi`, `en`): `[agent] language`, không có thì `[stt] language` | `agent.toml` — [`ui.md`](../spec/ui.md) §2 | 🟡 luật ngôn ngữ kiểm lúc build; giao diện chỉ build trên host để so ảnh golden, chưa nối vào firmware (driver màn hình ⏳) |
| Hành trình 10 phút (TTFV) | — | ⏳ I1 |

Kiểm tra nhanh toàn bộ artifact trong kho: `CHANGELOG.md` §2.2.

## 3. Chưa dùng được gì

Nói thẳng để bạn không mất thời gian:

- `neuroedge run` / `record` / `mcp serve` mới gõ chữ trên terminal; trên `sim` và `linux`, `run` /
  `record` nhận thêm tệp WAV (`--voice-file`). Không có `[wake_word]` thì một lượt mở bằng VAD; có
  `[wake_word]` thì mở bằng từ khoá — nhưng **mô hình là của bạn**: không mô hình nào được giao kèm
  hay tải về (Q-45). `--voice-file` với `--ui` **thoát mã 2**. Micro và loa thật trên `linux` mới ở
  mức nguyên thủy HAL (chưa có phiên thoại thời gian thực chạy song song provider — `TODOS.md` #45),
  và **chưa chạy trên Pi thật** (nightly TSK-S4-05). Trên `linux` chưa có trang `--ui` (**thoát mã 2**).
  Không có "PASS" giả (bất biến 10, `CHANGELOG.md` §3.3).
- `--target linux` cần line GPIO thật hoặc ảo (`scripts/setup_gpio_sim.sh`) và
  `pip install 'neuroedge[linux]'`; micro/loa thật cần thêm `pip install 'neuroedge[audio]'` và
  `NEUROEDGE_LINUX_AUDIO=live`. Thiếu thì lệnh báo lỗi, không giả vờ chạy.
- Trên `linux` đủ năm nguyên thủy: `digital.out`, `sensor.read`, `display`, `audio.in`, `audio.out`.
  Agent cần `motion`/`door_contact` của `linux-rpi5` vẫn bị từ chối trước khi xin line — chúng là đầu
  vào GPIO, không phải hwmon/IIO. Gate chưa so trực
  tiếp được số đọc (`evaluate.type: numeric`, `TODOS.md` #30): agent đổi số đọc thành dữ kiện gate ở
  `[sim.sensor_facts]` — ngưỡng `gte`/`lte`, hoặc dải `bands` như `factory-monitor` — như nhau trên
  `sim` và `linux`. Màn hình `/dev/fb*` chỉ nhận khung điểm ảnh; khung chữ cần `display = memory`.
  `:sensor` trong REPL không đổi được cảm biến thật.
- Chưa có bo mạch `esp32s3`: firmware (walker gate, sổ token C, replay vết ghi chuẩn mực, firmware
  sinh cho agent của bạn) mới chạy trên máy tính và QEMU, và chưa động chân GPIO nào (TSK-S4-01). Trên `esp32s3`, operation/duration của lệnh chân lấy từ bảng hành động dựng
  trên host; `replay --target esp32s3` cho vết ghi tuỳ ý **thoát mã 2**.
- Tương đương target mới so **quyết định** (phán quyết + lệnh chân), chưa so timing.
- `[system_one]` gửi lời người nói lên OpenRouter — chỉ lời nói, không action hay tham số (`--anonymize`
  chỉ băm vết ghi). Jev đọc tiếng Anh tốt nhất; độ tin cậy trên câu tiếng Việt chưa đo (`TODOS.md` #27),
  nên đặt `threshold` và `confidence_gte` thận trọng. Chỉ giao cho model tiêu chí mà lời nói tự nó
  xác lập được — danh tính, đặt phòng vẫn là dữ kiện phiên; `call_source` thì build từ chối.
- Danh sách đầy đủ: `CHANGELOG.md` §3.7.

## 4. Khi gặp lỗi

Mọi thông báo lỗi đủ **3 thành phần** (ở đâu · vì sao · cách xử lý) — cách đọc
một thông báo lỗi: `CHANGELOG.md` §2.4.

**Claude Desktop và `mcp serve --ui`: trang không đổi khi gọi từ Desktop.** Desktop thường chạy
vài tiến trình server cùng lúc, mỗi tiến trình có trang riêng, và chỉ một giữ cổng 8765 (quy tắc:
`docs/spec/tool_calling.md` §8). Cách tìm đúng trang:

1. Mở log của Desktop — trên macOS là `~/Library/Logs/Claude/mcp-server-<tên>.log`.
2. Tìm các dòng `sim UI at http://127.0.0.1:…` và `warning: sim UI port 8765 is taken … the page is at …`.
3. Mở từng URL trong các dòng đó; trang của cuộc trò chuyện là trang đổi khi bạn gọi.

## 5. Tiếp theo

- Việc đang làm và thứ tự tiếp theo: thẻ bàn giao `neuroedge-roadmap.md` §0.3.
- Trạng thái đầy đủ: [`trang-thai.md`](trang-thai.md).
- Muốn tài liệu này có thêm mục gì: mở issue hoặc PR theo
  [`CONTRIBUTING.md`](../../CONTRIBUTING.md).
