# Hướng dẫn sử dụng — hôm nay làm được gì

> Bản đồ tài liệu ở [`README.md`](README.md). Cú pháp lệnh và đầu ra kỳ vọng
> nằm ở [`CHANGELOG.md`](../../CHANGELOG.md) §2.3 — tệp này không chép lại.

## 1. Cài đặt

Chưa có bản phát hành trên PyPI (`TSK-S3-14`). Cài từ mã nguồn theo
[`python/README.md`](../../python/README.md).

Yêu cầu: Python 3.11+ (`Q-1`). `sim` mặc định **gõ chữ** — không cần khoá API,
không cần mạng, kết quả tất định (`Q-15`).

## 2. Hôm nay dùng được gì

Phần **chính sách gate**, **lõi thực thi trên `sim`**, **vòng lặp gõ chữ** và **Action CI**
(ghi → phát lại → khẳng định → so golden) đã có.
Cú pháp từng lệnh: `CHANGELOG.md` §2.3. Thử ngay trong kho:

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
| Đối chiếu năng lực agent ↔ bo mạch, biên dịch gate | `neuroedge build` | ✅ |
| Chạy agent có gate trên `sim` từ mã Python (`c.do()` trên `SimHAL`) | — (thư viện) | ✅ |
| Chạy agent có gate trên `sim` từ dòng lệnh (gõ chữ, không mạng) | `neuroedge run` | ✅ |
| Xem phiên `sim` trực tiếp trên trình duyệt: chốt cửa, đèn, cảm biến, màn hình | `neuroedge run --ui` | ✅ |
| Mở một vết ghi thành trang HTML để xem lại, tua thời gian, gửi đồng nghiệp | `neuroedge trace view` | ✅ |
| Giả lập cảm biến và màn hình trên `sim` | `[sim.sensors]` · `:sensor` · `display.show()` | ✅ |
| Đọc một gate bằng lời: tiêu chí từ đâu, điều gì bị siết chặt | `neuroedge gate explain` | ✅ |
| Tạo dự án agent mới có sẵn gate, action, test | `neuroedge new` | ✅ |
| Thử một trợ lý giọng nói: hỏi đáp knowledge base, tin tức, bật/tắt đèn qua gate | `neuroedge new nha --template home-voice` | ✅ |
| Xem các `@action` dưới dạng tool (schema cho LLM / MCP) | `neuroedge mcp tools` | ✅ |
| Cho Claude Desktop hoặc agent khác gọi thiết bị qua MCP — vẫn qua gate | `neuroedge mcp serve` (cấu hình mẫu ở `README.md`) | ✅ cần `neuroedge[mcp]` |
| Ghi cấu hình Claude Desktop cho `mcp serve` (đường dẫn tuyệt đối, có sao lưu) | `neuroedge mcp desktop-config --agent … [--ui] --write` | ✅ cần `neuroedge[mcp]` |
| Điều khiển từ Claude Desktop và thấy đèn/chốt ảo đổi trên trình duyệt — cùng một phiên | `neuroedge mcp serve --ui` (trang ở http://127.0.0.1:8765) | ✅ cần `neuroedge[mcp]` |
| Cho System 2 dùng MCP server bên ngoài (tin tức, tra cứu) — chỉ lấy thông tin | `[mcp.servers]` trong `agent.toml` · `neuroedge mcp tools --external` | ✅ cần `neuroedge[mcp]` |
| Người xác nhận khi gate hỏi lại (`ask`) | — | ⏳ TSK-S3-26 |
| Ghi một phiên ra vết ghi (có chế độ ẩn danh) | `neuroedge record` | ✅ |
| Phát lại vết ghi trên `sim` / `linux`, so golden | `neuroedge replay` | ✅ |
| Chạy test an toàn của agent (Action CI) | `neuroedge test` | ✅ |
| Kiểm cùng quyết định trên `sim` và `linux` (A2) | `neuroedge verify --targets sim,linux` | ✅ cần line GPIO |
| Phiên gõ chữ tương tác trên `linux` | `neuroedge run --target linux` | ⏳ |
| Hành trình 10 phút (TTFV) | — | ⏳ mốc M1 |

Kiểm tra nhanh toàn bộ artifact trong kho: `CHANGELOG.md` §2.2.

## 3. Chưa dùng được gì

Nói thẳng để bạn không mất thời gian:

- `neuroedge run` / `record` mới chạy trên `sim`, gõ chữ trên terminal; `--target linux`
  **thoát mã 2** — trên `linux` dùng `replay`. Không có "PASS" giả (bất biến 10, `CHANGELOG.md` §3.3).
- `--target linux` cần line GPIO thật hoặc ảo (`scripts/setup_gpio_sim.sh`) và
  `pip install 'neuroedge[linux]'`; thiếu thì lệnh báo lỗi, không giả vờ chạy.
- Tương đương target mới so **quyết định** (phán quyết + lệnh chân), chưa so timing.
- Danh sách đầy đủ: `CHANGELOG.md` §3.7.

## 4. Khi gặp lỗi

Mọi thông báo lỗi đủ **3 thành phần** (ở đâu · vì sao · cách xử lý) — cách đọc
một thông báo lỗi: `CHANGELOG.md` §2.4.

**Claude Desktop và `mcp serve --ui`.** Desktop có thể khởi động server vài lần liền và bỏ lại
một tiến trình cũ. Tiến trình không nhận `initialize` sau 30 giây sẽ tự thoát và nhả cổng
(`--init-timeout`). Nếu cổng 8765 vẫn bận, trang chuyển sang cổng trống, còn MCP vẫn chạy.
URL thật của trang nằm ở dòng `sim UI at http://127.0.0.1:…` trong log của Desktop, trên macOS là
`~/Library/Logs/Claude/mcp-server-<tên>.log`.

## 5. Tiếp theo

- Việc đang làm và thứ tự tiếp theo: thẻ bàn giao `neuroedge-roadmap.md` §0.3.
- Trạng thái đầy đủ: [`trang-thai.md`](trang-thai.md).
- Muốn tài liệu này có thêm mục gì: mở issue hoặc PR theo
  [`CONTRIBUTING.md`](../../CONTRIBUTING.md).
