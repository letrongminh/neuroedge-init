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
| Liệt kê / xem profile bo mạch | `neuroedge board list` · `neuroedge board show` | ✅ |
| Đối chiếu năng lực agent ↔ bo mạch, biên dịch gate (cả cây nhị phân `.netree` cho thiết bị, RFC-0003) | `neuroedge build` | ✅ |
| Chạy agent có gate trên `sim` từ mã Python (`c.do()` trên `SimHAL`) | — (thư viện) | ✅ |
| Chạy agent có gate trên `sim` từ dòng lệnh (gõ chữ, không mạng) | `neuroedge run` | ✅ |
| Xem phiên `sim` trực tiếp trên trình duyệt: chốt cửa, đèn, cảm biến, màn hình | `neuroedge run --ui` | ✅ |
| Mở một vết ghi thành trang HTML để xem lại, tua thời gian, gửi đồng nghiệp | `neuroedge trace view` | ✅ |
| Xuất vết ghi để phân tích thời gian trong Perfetto | `neuroedge trace export --format chrome` | ✅ |
| Giả lập cảm biến và màn hình trên `sim` | `[sim.sensors]` · `:sensor` · `display.show()` | ✅ |
| Đọc một gate bằng lời: tiêu chí từ đâu, điều gì bị siết chặt | `neuroedge gate explain` | ✅ |
| Tạo dự án agent mới có sẵn gate, action, test | `neuroedge new` | ✅ |
| Thử một trợ lý giọng nói: hỏi đáp knowledge base, tin tức, bật/tắt đèn qua gate | `neuroedge new nha --template home-voice` | ✅ |
| Xem các `@action` dưới dạng tool (schema cho LLM / MCP) | `neuroedge mcp tools` | ✅ |
| Cho Claude Desktop hoặc agent khác gọi thiết bị qua MCP — vẫn qua gate | `neuroedge mcp serve` (cấu hình Claude Desktop: dòng dưới, `desktop-config`) | ✅ cần `neuroedge[mcp]` |
| Ghi cấu hình Claude Desktop cho `mcp serve` (đường dẫn tuyệt đối, có sao lưu) | `neuroedge mcp desktop-config --agent … [--ui] --write` | ✅ cần `neuroedge[mcp]` |
| Điều khiển từ Claude Desktop và thấy đèn/chốt ảo đổi trên trình duyệt — cùng một phiên | `neuroedge mcp serve --ui` (trang ở http://127.0.0.1:8765) | ✅ cần `neuroedge[mcp]` |
| Cho System 2 dùng MCP server bên ngoài (tin tức, tra cứu) — chỉ lấy thông tin | `[mcp.servers]` trong `agent.toml` · `neuroedge mcp tools --external` | ✅ cần `neuroedge[mcp]` |
| Dùng LLM thật cho System 2 (Claude, GPT, DeepSeek qua OpenRouter…): câu tự do thành tool call, vẫn qua gate | `[system_two]` trong `agent.toml` · key ở biến môi trường (`api_key_env`), **không** ghi vào tệp | ✅ cần `neuroedge[cloud]` |
| Mất mạng hoặc System 2 không trả lời: thiết bị nói các lệnh cục bộ còn dùng được (`offline_help`) | — (tự động) | ✅ |
| Nối model chưa theo chuẩn OpenAI bằng adapter tự viết | `provider = "python:pkg.mod:factory"` trong `[system_two]` | ✅ |
| Người xác nhận khi gate hỏi lại (`ask`): gõ `có` / `không`, hoặc nút Đồng ý / Huỷ trên `run --ui` | `neuroedge run` · `neuroedge run --ui` | ✅ gate phải khai `confirms` |
| Ghi một phiên ra vết ghi (có chế độ ẩn danh) | `neuroedge record` | ✅ |
| Phát lại vết ghi trên `sim` / `linux`, so golden | `neuroedge replay` | ✅ |
| Chạy test an toàn của agent (Action CI) | `neuroedge test` | ✅ |
| Kiểm cả kho: gate, vết ghi chuẩn mực, corpus tool call, replay | `neuroedge verify` | ✅ |
| Kiểm cùng quyết định trên `sim` và `linux` (A2) | `neuroedge verify --targets sim,linux` | ✅ cần line GPIO |
| Ghi vết ghi từ firmware `esp32s3` qua UART | `neuroedge record --target esp32s3 --port <log · tcp://… · /dev/tty…>` | ✅ trên QEMU · bo mạch ⏳ |
| Kiểm cùng quyết định trên `esp32s3`: firmware replay các vết ghi chuẩn mực | `neuroedge verify --targets esp32s3 --port …` | ✅ trên QEMU · bo mạch ⏳ |
| Phiên gõ chữ tương tác trên `linux`: chân là line GPIO thật | `neuroedge run` / `record` / `mcp serve --target linux` | ✅ cần line GPIO + `neuroedge[linux]`; agent được cần `digital.out`, `sensor.read`, `display` (chưa âm thanh) |
| Đọc cảm biến thật trên `linux` (hwmon, IIO) và vẽ lên màn hình (`/dev/fb*`, hoặc trong bộ nhớ) | `NEUROEDGE_LINUX_SENSORS="temperature=hwmon:lm75/temp1"` · `NEUROEDGE_LINUX_DISPLAY=/dev/fb0` (hoặc `memory`) — [`simulation_coverage.md`](../spec/simulation_coverage.md) §2 (`linux`) | ✅ trên hwmon ảo (`i2c-stub` + `lm75`) và `vfb` trong CI · Pi ⏳ |
| Hành trình 10 phút (TTFV) | — | ⏳ I1 |

Kiểm tra nhanh toàn bộ artifact trong kho: `CHANGELOG.md` §2.2.

## 3. Chưa dùng được gì

Nói thẳng để bạn không mất thời gian:

- `neuroedge run` / `record` / `mcp serve` mới gõ chữ trên terminal. Trên `linux` agent chưa được cần
  âm thanh (lệnh báo lỗi, mã 1) và chưa có trang `--ui` (**thoát mã 2**). Không có "PASS" giả
  (bất biến 10, `CHANGELOG.md` §3.3).
- `--target linux` cần line GPIO thật hoặc ảo (`scripts/setup_gpio_sim.sh`) và
  `pip install 'neuroedge[linux]'`; thiếu thì lệnh báo lỗi, không giả vờ chạy.
- Trên `linux` có `digital.out`, `sensor.read`, `display`; âm thanh chưa hiện thực. Cảm biến đọc bằng
  độ (°C), không bằng "dải" như `[sim.sensors]` của `factory-monitor` (`high`, `critical`): gate so
  dải thì chặn (fail-closed) cho tới khi có `evaluate.type: numeric` (`TODOS.md` #30). Màn hình
  `/dev/fb*` chỉ nhận khung điểm ảnh; khung chữ cần `display = memory`. `:sensor` trong REPL không
  đổi được cảm biến thật.
- Chưa có bo mạch `esp32s3`: firmware (walker gate, sổ token C, replay vết ghi chuẩn mực) mới chạy
  trên máy tính và QEMU. Trên `esp32s3`, operation/duration của lệnh chân lấy từ bảng hành động dựng
  trên host; `replay --target esp32s3` cho vết ghi tuỳ ý **thoát mã 2**.
- Tương đương target mới so **quyết định** (phán quyết + lệnh chân), chưa so timing.
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
