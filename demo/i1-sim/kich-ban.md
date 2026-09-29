# Kịch bản demo — NeuroEdge trên môi trường mô phỏng (`sim`)

> **Chạy lại lần cuối:** 2026-09-29, macOS, `main` `6a69626`.  
> **Thời lượng:** 5–7 phút (mỗi màn ≤ 1 phút). Không cần phần cứng, không cần mạng ngoài.

---

## 0. Chuẩn bị

Trước buổi demo, người thuyết trình chuẩn bị môi trường:

```bash
# 1. Chạy script tạo môi trường ảo và 3 dự án mẫu tại /tmp/neuroedge-demo
bash demo/i1-sim/chuan-bi.sh

# 2. Gán alias 'ne' từ gốc kho, rồi chuyển vào thư mục demo
alias ne="$PWD/python/.venv/bin/neuroedge"
cd /tmp/neuroedge-demo

# 3. Đảm bảo cửa sổ terminal rộng ≥ 100 cột
```

> [!IMPORTANT]
> **Điều không được nói:** Đọc kỹ bảng *"Điều không được nói trong bất kỳ demo nào"* tại [`docs/business/cong-nhu-cau-2026-10-25/demo.md` §0.1](../../docs/business/cong-nhu-cau-2026-10-25/demo.md#01-điều-không-được-nói-trong-bất-kỳ-demo-nào) và các năng lực chưa hỗ trợ tại [`CHANGELOG.md` §3.7](../../CHANGELOG.md#37-điều-hệ-thống-chưa-làm-được). Tuyệt đối không nói hệ thống đã chạy trên bo mạch thật, nhận giọng nói micro trực tiếp, hay phân tích ngôn ngữ tự do ngoài ngữ pháp lệnh.

---

## 1. Màn 1 — "Khoá cửa không mở sai phòng" (villa-concierge)

### Nói
"Lệnh mở cửa từ khách phải đi qua gate an toàn cục bộ. Đúng phòng thì chốt mở 30 giây; sai phòng hoặc thiếu dữ kiện xác thực thì chốt đứng yên và chuyển lễ tân."

### Gõ
```bash
ne run --agent villa-concierge/agent.toml -c "mở cửa phòng 101"
ne run --agent villa-concierge/agent.toml -c "mở cửa phòng 202"
ne run --agent villa-concierge/agent.toml
# trong REPL:
:set guest_authenticated false
mở cửa phòng 101
:set guest_authenticated true
:unset risk_level
mở cửa phòng 101
exit
```

### Thấy
```text
✓ ALLOW unlock_door@1.2.0 → unlock_door(guest_id='101')
│ door_lock │ PULSED 30s │        1 │
…
✗ BLOCK unlock_door@1.2.0 (reason: condition_not_met, criterion: room_matches)
  action: escalate to human_receptionist — "Yêu cầu cần được nhân viên lễ tân xác nhận trực tiếp…"
│ door_lock │ LOW   │        0 │
…
neuroedge>   guest_authenticated = false
neuroedge> intent unlock (1.00) [room=101]
✗ BLOCK unlock_door@1.2.0 (reason: condition_not_met, criterion: guest_authenticated)
…
neuroedge>   risk_level is now undecided
…
✗ BLOCK unlock_door@1.2.0 (reason: criterion_unavailable, criterion: risk_level)
```

### Điểm nhấn
Gate tự động chặn theo nguyên tắc fail-closed ngay khi một tiêu chí bị thiếu (`criterion_unavailable`) mà không cần mã ứng dụng bắt lỗi; lệnh bị BLOCK vẫn thoát mã 0.

---

## 2. Màn 2 — "Thiết bị hỏi lại trước khi làm" (home-voice)

### Nói
"Khi hành động vật lý có rủi ro (tắt đèn khi còn người trong phòng), gate chặn lại và kích hoạt câu hỏi xác nhận trực tiếp trên thiết bị; chỉ người tại chỗ mới có quyền bấm đồng ý."

### Gõ
```bash
# run --ui tự động mở trình duyệt (mặc định cổng 8765, 127.0.0.1; không có cờ --open; --no-browser để tắt)
ne run --agent home-voice/agent.toml --ui
# Thao tác trên ô lệnh web hoặc terminal REPL:
:sensor motion true
bật đèn
tắt đèn
# Hộp thoại "Thiết bị hỏi xác nhận" xuất hiện trên trang web: bấm nút "Đồng ý"
:sensor motion false
tắt đèn
wifi nhà mình là gì
exit
```

### Thấy
- **Trên giao diện web (`http://127.0.0.1:8765/`):**
  - Panel **Cảm biến** hiện `motion: true`. Khi gõ `bật đèn`, panel **Thiết bị** hiện `porch_light` sáng vàng (HIGH) và panel **Phán quyết gate** hiện `ALLOW`.
  - Khi gõ `tắt đèn`, panel **Thiết bị hỏi xác nhận** bật lên: `"Vẫn còn người trong phòng — bạn chắc muốn tắt đèn? (light_off)"` kèm 2 nút **"Đồng ý"** / **"Huỷ"** và đếm ngược 10 s. Bấm **"Đồng ý"** → đèn chuyển LOW.
  - Khi `motion = false` → gõ `tắt đèn` được ALLOW ngay; `wifi nhà mình là gì` được panel **Trợ lý nói** trả lời từ knowledge base mà không động chân vật lý.
- **Đầu ra tương ứng trên terminal:**
```text
✓ ALLOW light_on@1.0.0 → light_on()
│ porch_light │ HIGH  │        1 │
✗ BLOCK light_off@1.0.0 (reason: condition_not_met, criterion: room_empty)
  action: ask — "Vẫn còn người trong phòng — bạn chắc muốn tắt đèn?"
  ? xác nhận confirm_1: gõ có để tiếp tục, không để huỷ · còn 10 s · chỉ người trên thiết bị trả lời được
answer to the pending question (confirmed)
  ✓ ALLOW light_off@1.0.0 → light_off()
  says (confirmed): Đã xác nhận.
✓ ALLOW light_off@1.0.0 → light_off()
  says (knowledge_local): Mạng wifi là NhaMinh, mật khẩu dán ở mặt dưới router.
```

### Điểm nhấn
Cơ chế `on_block: ask` theo RFC-0006 phân biệt rõ giữa xác nhận tại chỗ của con người và lời gọi từ xa; trang web sim UI chỉ phục vụ nội bộ qua loopback `127.0.0.1`.

---

## 3. Màn 3 — "Cảm biến quyết định" (factory-monitor)

### Nói
"Cảm biến môi trường quyết định tính hợp lệ của lệnh. Ở 60 °C (nguy cấp), lệnh tắt quạt bị chặn dứt khoát và không hỏi lại; ở 45 °C máy hỏi lại; ở 30 °C được tắt báo động an toàn."

### Gõ
```bash
ne run --agent factory-monitor/agent.toml
# trong REPL:
bật quạt
:sensor temperature 60
tắt quạt
:sensor temperature 45
tắt quạt
không
:sensor temperature 30
tắt báo động
exit
```

### Thấy
```text
✓ ALLOW vent_on@1.0.0 → vent_on()
│ gate_relay  │ HIGH  │        1 │
neuroedge>   temperature = 60
✗ BLOCK vent_off@1.0.0 (reason: condition_not_met, criterion: heat_level)
  action: ask — "Phòng máy đang nóng — bạn chắc muốn tắt quạt thông gió?"
neuroedge>   temperature = 45
  ? xác nhận confirm_1: gõ có để tiếp tục, không để huỷ · còn 10 s · chỉ người trên thiết bị trả lời được
neuroedge> answer to the pending question (declined)
  says (declined): Đã huỷ.
neuroedge>   temperature = 30
✓ ALLOW alarm_off@1.0.0 → alarm_off()
```

### Điểm nhấn
Ở 60 °C, gate in `action: ask` nhưng **không mở câu hỏi xác nhận** (không có dòng `? xác nhận confirm_1`) vì điều kiện `heat_critical: false` bị vi phạm và không nằm trong danh sách `confirms: [heat_level]`; ở 45 °C câu hỏi mới mở.

---

## 4. Màn 4 — "Tái hiện sự cố trên laptop"

### Nói
"Mọi quyết định chặn đều để lại vết ghi được ẩn danh bảo vệ quyền riêng tư; vết ghi này mở được thành HTML trực quan, phát lại được trên laptop và đối chiếu tự động trong CI."

### Gõ
```bash
cd villa-concierge
ne record -c "mở cửa phòng 202"
T=$(ls -t traces/sess_*.json | head -1)     # tên phiên ngẫu nhiên mỗi lần ghi
ne trace show "$T"
ne trace view "$T" --open
ne replay "$T"
ne verify
```

### Thấy
```text
trace: traces/sess_<id>.json (9 events)
│ text_input             │ {"text": "sha256:79ec5403a912a0baa7b575468e6e5f4d6f70f7b0e76e05d34d5b1…
│ gate_facts             │ {"guest_authenticated": {"value": true…}, "room_matches": {"value": false…}}
…
✓ traces/sess_<id>.html (9 events)
…
✓ decisions match the recording
╭──────────────────────────────────────── neuroedge verify ────────────────────────────────────────╮
│ Passed: all 3 gate(s) resolve, all 3 canonical trace(s) validate… match the verdicts…            │
│ Compared: decisions only — not timing. Timing equivalence arrives with TSK-S4-04.                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Điểm nhấn
Vết ghi mặc định băm SHA-256 nội dung gõ/nói tại nguồn (`"text": "sha256:…"` theo TSK-I1-01, cờ `--raw` giữ nguyên văn) nhưng lưu đủ `gate_facts` để `replay` tái tạo 100% quyết định; `verify` trên máy tính chỉ so sánh quyết định (`sim` only), `linux` và `esp32s3` được đối chiếu trong CI.

---

## 5. Màn 5 (tuỳ chọn) — MCP với Claude Desktop

### Nói
"Khi kết nối mô hình ngôn ngữ lớn (Claude Desktop) qua Model Context Protocol (MCP), LLM chỉ đề xuất tool call; cổng an toàn của NeuroEdge vẫn là chốt chặn quyết định điều khiển thiết bị."

### Gõ
```bash
# Xem cấu hình MCP cho Claude Desktop (có hỗ trợ cờ --ui)
ne mcp desktop-config --agent home-voice/agent.toml --ui

# Chạy server MCP phục vụ Claude Desktop kèm giao diện web (cờ --open mở trình duyệt)
ne mcp serve --agent home-voice/agent.toml --ui --open
```

### Thấy
```text
(kiểm lại khi chạy)
```
- Khi người dùng bảo Claude Desktop *"bật đèn lên"*, Claude gửi tool call `light_on` qua MCP stdio.
- Server tiếp nhận, kiểm tra qua gate, đổi chân `porch_light` sang HIGH và cập nhật trực tiếp lên trang web `--ui` (`http://127.0.0.1:8765/`).

### Điểm nhấn
Tool call từ LLM bên ngoài phải tuân thủ Gated Tool Profile v0; gate là ranh giới an toàn vật lý ngăn chặn prompt injection.

---

## 6. Câu hỏi thường gặp khi demo

1. **Thiết bị thật:** *"Hệ thống đã chạy trên bo mạch thật chưa?"*  
   → Chưa có bo mạch vật lý ESP32-S3-BOX-3; toàn bộ demo hiện chạy trên target `sim` (chân ảo) hoặc QEMU UART trong CI ([`demo.md` §0.1](../../docs/business/cong-nhu-cau-2026-10-25/demo.md#01-điều-không-được-nói-trong-bất-kỳ-demo-nào) · [`CHANGELOG.md` §3.4, §3.7](../../CHANGELOG.md#37-điều-hệ-thống-chưa-làm-được)).

2. **Thoại trực tiếp:** *"Có thể nói chuyện trực tiếp qua micro thời gian thực không?"*  
   → Thoại hiện nhận từ tệp WAV (`--voice-file`), chưa có phiên micro thời gian thực trên máy tính ([`CHANGELOG.md` §3.7](../../CHANGELOG.md#37-điều-hệ-thống-chưa-làm-được) · [`demo.md` §0.1](../../docs/business/cong-nhu-cau-2026-10-25/demo.md#01-điều-không-được-nói-trong-bất-kỳ-demo-nào)).

3. **Quyền riêng tư:** *"Vết ghi có lưu lộ văn bản thô của người dùng không?"*  
   → Mặc định văn bản gõ/nói được băm SHA-256 tại nguồn (`metadata.anonymized = true`), chỉ lưu văn bản thô khi truyền cờ tường minh `--raw` (TSK-I1-01, NFR-PRIV-03 trong `neuroedge-prd.md`).

4. **Phạm vi verify:** *"`neuroedge verify` so sánh những gì giữa các target?"*  
   → So sánh phán quyết gate và lệnh chân (decisions only), chưa so thời gian thực thi (timing equivalence ở TSK-S4-04) ([`CHANGELOG.md` §3.7](../../CHANGELOG.md#37-điều-hệ-thống-chưa-làm-được) · [`demo.md` §0.1](../../docs/business/cong-nhu-cau-2026-10-25/demo.md#01-điều-không-được-nói-trong-bất-kỳ-demo-nào)).

5. **Mã thoát lệnh:** *"Lệnh `run -c` khi bị BLOCK có thoát mã lỗi khác 0 không?"*  
   → Không, BLOCK là phán quyết bảo vệ hợp lệ của gate chứ không phải lỗi thực thi; tiến trình kết thúc với mã thoát 0 ([`run.py`](../../python/neuroedge/cli/run.py)).
