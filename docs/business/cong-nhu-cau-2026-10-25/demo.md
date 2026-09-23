# Kịch bản demo — cổng nhu cầu 2026-10-25

Mỗi phân khúc một kịch bản ≤ 5 phút. **Chỉ dùng lệnh chạy được hôm nay**; mọi đầu ra dưới đây là
đầu ra thật, đã cắt bớt, chạy ngày 2026-09-24 trên macOS (Darwin 23.6), Python 3.13, nhánh `main`
tại `e8a9e26`.

Luật dùng demo trong phỏng vấn (`phong-van.md`): demo **sau** phần câu hỏi vấn đề, chỉ khi người
được phỏng vấn muốn xem. Demo là để kiểm giả thuyết, không để bán. Câu hỏi sau demo ghi ở cuối mỗi
kịch bản.

## 0. Chuẩn bị máy demo

```bash
# từ gốc kho
cd python && python3 -m venv .venv && .venv/bin/python -m pip install -e '.[dev,mcp]' && cd ..
alias ne=python/.venv/bin/neuroedge
DEMO=/tmp/neuroedge-demo && mkdir -p $DEMO     # mọi tệp demo sinh ra nằm ở đây, không ở trong kho
ne gate lint                                    # kỳ vọng: ✓ 3 gate(s) resolved.
```

Checklist trước mỗi buổi:

| Kiểm | Lệnh | Kỳ vọng |
|:---|:---|:---|
| Gate mẫu phân giải | `ne gate lint` | `✓ 3 gate(s) resolved.` · mã 0 |
| Vết ghi chuẩn mực replay | `ne verify` | `Passed: all gates resolve…` · mã 0 |
| Extra MCP có | `python/.venv/bin/python -c "import mcp"` | không lỗi |
| Terminal đủ rộng | — | ≥ 100 cột, chữ to |
| Dự án demo đã dựng sẵn | §2.0, §4.0 | `ne test` trong từng dự án: mã 0 |

### 0.1 Điều **không** được nói trong bất kỳ demo nào

Nói thẳng nếu bị hỏi. Mỗi dòng dẫn nguồn trong kho.

| Không nói là đã có | Sự thật hôm nay | Nguồn |
|:---|:---|:---|
| Chạy trên phần cứng thật | Không có bo mạch ESP32-S3-BOX-3; mọi demo chạy trên `sim` (chân ảo) | `CHANGELOG.md` §3.4 (TSK-S1-10) |
| Nói bằng giọng | `sim` là **gõ chữ** (Q-15); chưa có giọng nói | `docs/user/huong-dan.md` §3 |
| LLM hiểu câu tự do | Có từ TSK-S2-11 nhưng cần `neuroedge[cloud]` + key thật; demo không khai `[system_two]`, nên chỉ câu khớp `commands.toml` chạy. CI chỉ thử LiteLLM bằng `mock_response`, chưa bằng key thật | TSK-S2-11 · `CHANGELOG.md` §3.7 |
| Gate giới hạn **giá trị** tham số (ví dụ `duration_s ≤ 60`) | Chưa; dispatcher chỉ kiểm tên và kiểu tham số | RFC-0005 · TSK-S3-25 |
| Người xác nhận khi gate hỏi lại (`ask`) | Gate trả `ask` và câu hỏi; vòng xác nhận chưa có | TSK-S3-26 · Q-26 |
| Chuyển cho lễ tân thật (`escalate`) | Chặn + ghi vết ghi + hook không làm gì | Q-17 · `TODOS.md` #20 |
| Điều khiển từ Claude Desktop và thấy trên giao diện web | `mcp serve` và `run --ui` là hai phiên riêng | TSK-S3-27 |
| Phiên tương tác trên Linux | `run --target linux` thoát mã 2; trên Linux chỉ `replay` / `verify` | `CHANGELOG.md` §2.3 |
| So thời gian giữa target | `verify` so **quyết định**, chưa so timing; chưa có `esp32s3` | TSK-S4-04 |
| Fleet OS (OTA theo đợt, dashboard, tải vết ghi từ xa) | Chưa có dòng mã nào; Khối 2 | proposal §6 · `TODOS.md` #6, #16 |
| Chứng nhận an toàn chức năng | Không có, không nhắm tới (chưa quyết) | `CEO-T2` |
| Vết ghi có chữ ký, dùng làm bằng chứng cho bên thứ ba | Không ký | `TODOS.md` #1 |
| Cài bằng `pip install neuroedge` | Chưa lên PyPI; cài từ mã nguồn | TSK-S3-14 |

---

## 1. Khách sạn / nghỉ dưỡng — "khóa cửa không mở sai phòng"

**Cho thấy:** một lệnh mở cửa đi qua gate có phiên bản; sai phòng, chưa xác thực, rủi ro cao ⇒
chốt không nhúc nhích và yêu cầu chuyển lễ tân; gate con cho ca đêm chỉ được **siết**, không được
nới; agent bên ngoài gọi qua MCP cũng bị cùng gate chặn.

**Hỗ trợ giả thuyết:** `CEO-X5` (người vận hành villa có trả tiền vì trách nhiệm khi thiết bị sai —
proposal §7.3) · `CEO-X4` (họ muốn runtime trên thiết bị hay chỉ muốn một bên chịu trách nhiệm) ·
C1 (có sự cố khóa/điều khiển phòng thật không).

| Phút | Làm | Nói (một câu) |
|:---:|:---|:---|
| 0:00 | Mở `gates/unlock_door@1.2.0.yaml` | "Đây là điều kiện mở cửa, viết thành tệp đọc được, không phải mã." |
| 0:30 | `ne run -c "mở cửa phòng 101"` | "Đúng phòng đã đặt: chốt kích 30 giây." |
| 1:00 | `ne run -c "mở cửa phòng 202"` | "Sai phòng: không có gì chạy, yêu cầu chuyển lễ tân." |
| 1:30 | REPL: `:set guest_authenticated false` · `:set risk_level medium` | "Hai điều kiện khác, cùng một kết quả: chốt đứng yên." |
| 2:30 | `ne gate explain gates/unlock_door_night@1.0.0.yaml` | "Ca đêm thêm điều kiện nhân viên đồng phê duyệt. Gate con chỉ được siết." |
| 3:15 | `ne gate resolve fixtures/gates/invalid/loosens_level.yaml --registry fixtures/gates/registry` | "Ai đó thử nới gate con cho rủi ro cao — bị từ chối trước khi chạy." |
| 4:00 | MCP: agent ngoài gọi `unlock_door` | "Agent khác gọi được thiết bị, nhưng lời gọi chỉ là yêu cầu." |
| 4:30 | `ne record --out $DEMO/traces -c "mở cửa phòng 202"` rồi `ne trace view … -o $DEMO/sess.html` | "Mỗi lần chặn để lại một tệp mở được trên trình duyệt, gửi cho chủ villa." |

Đầu ra thật:

```text
$ ne run -c "mở cửa phòng 101"
intent unlock (1.00) [room=101]
  tool_call unlock_door(guest_id='101') · local_grammar
✓ ALLOW unlock_door@1.2.0 → unlock_door(guest_id='101')
│ door_lock │ PULSED 30s │        1 │
[exit 0]

$ ne run -c "mở cửa phòng 202"
intent unlock (1.00) [room=202]
  tool_call unlock_door(guest_id='202') · local_grammar
✗ BLOCK unlock_door@1.2.0 (reason: condition_not_met, criterion: room_matches)
  action: escalate to human_receptionist — "Yêu cầu cần được nhân viên lễ tân
xác nhận trực tiếp trước khi mở khóa."
│ door_lock │ LOW   │        0 │
[exit 0]

$ ne run            # REPL, gõ lần lượt
neuroedge> :set guest_authenticated false
neuroedge> mở cửa phòng 101
✗ BLOCK unlock_door@1.2.0 (reason: condition_not_met, criterion: guest_authenticated)
neuroedge> :set guest_authenticated true
neuroedge> :set risk_level medium
neuroedge> mở cửa phòng 101
✗ BLOCK unlock_door@1.2.0 (reason: condition_not_met, criterion: risk_level)

$ ne gate explain gates/unlock_door_night@1.0.0.yaml
│ Kế thừa từ: neuroedge://gates/unlock_door@1.2.0                              │
│ Phân cấp: 3 cấp (base-access@1.0.0 → unlock_door@1.2.0 → unlock_door_night@1.0.0)
2. Điều kiện cho phép (allow_when) — phải đạt TẤT CẢ:
  ✓ guest_authenticated ∈ {true}, confidence >= 0.95 (cha cho phép {true} — con đã siết chặt)
  ✓ request_channel ∈ {app, in_person} (mới ở gate này)
  ✓ staff_co_authorized ∈ {true} (mới ở gate này)
  • Ngân sách thời gian (p95): 90 ms (kế thừa và siết chặt từ cha 120 ms)
  • Hành vi on_block: escalate → night_duty_manager

$ ne gate resolve fixtures/gates/invalid/loosens_level.yaml --registry fixtures/gates/registry
✗ NE2003 loosens-level@1.0.0 (fixtures/gates/invalid/loosens_level.yaml) -> allow_when.risk_level
  why: loosens the inherited condition: base admits {low}, this gate admits {high, low, medium}
  rule: Proposal Appendix B.5 principle 2
[exit 1]

$ ne record --out $DEMO/traces -c "mở cửa phòng 202"
✗ BLOCK unlock_door@1.2.0 (reason: condition_not_met, criterion: room_matches)
trace: $DEMO/traces/sess_6c00a243.json (7 events)
$ ne trace view $DEMO/traces/sess_6c00a243.json -o $DEMO/sess.html
✓ $DEMO/sess.html (7 events)
```

Bước MCP (phút 4:00) dùng client MCP ở Phụ lục A, đóng vai Claude Desktop:

```text
$ python/.venv/bin/python mcp_client.py villa $DEMO/mcp-villa.json
neuroedge MCP server · villa-concierge@0.1.0 · 1 tool(s) · stdio
call unlock_door({'guest_id': '101'}) -> is_error=False
    {"status": "BLOCK", "reason": "criterion_unavailable", "failed_criterion": "room_matches",
     "on_block": "escalate", "escalated_to": "human_receptionist"}
call unlock_door({'guest_id': '101', 'duration_s': 'forever'}) -> is_error=True
    {"status": "REJECTED", "problems": ["argument 'duration_s' must be integer, got 'forever'"]}
call unlock_door({'guest_id': '101', 'override': True}) -> is_error=True
    {"status": "REJECTED", "problems": ["unknown argument 'override'; unlock_door takes ['duration_s', 'guest_id']"]}
```

Giải thích dòng đầu cho đúng: qua MCP, cửa **không bao giờ mở** trong mẫu này, vì `room_matches`
chỉ được suy từ câu lệnh cục bộ (`[sim.slot_facts]`), không từ tham số mà agent ngoài tự khai. Đó là
fail-closed, không phải lỗi; nhưng đừng nói "agent ngoài mở được cửa khi hợp lệ".

**Không tuyên bố:** tất cả §0.1, thêm: AURA chưa được xây (roadmap ghi ngoài phạm vi, `CEO-X5`);
không có Zalo OA; câu hỏi FAQ (`mấy giờ trả phòng`) trả lời `no physical action for this intent;
spoken replies need System 2 ([system_two] in agent.toml)` — đừng gõ nó trong demo nếu không định nói điều này.

**Hỏi sau demo:** "Lần gần nhất khóa hay thiết bị trong phòng làm sai, ai chịu trách nhiệm, và chuyện
đó tốn bao nhiêu?" · "Tệp `sess.html` này, anh/chị sẽ gửi cho ai?"

---

## 2. Fleet Operators — "sự cố ngoài hiện trường, tái hiện trên laptop, và CI bắt thay đổi sai"

Không có Fleet OS để demo. Kịch bản nói về thứ **đã có** và là nền của Fleet OS (proposal §6.2 #5,
§1.1 #5): vết ghi một phiên, xem lại, phát lại ra đúng quyết định, và phát lại bắt được một thay đổi
chính sách làm thiết bị hành động sai.

### 2.0 Dựng sẵn (trước buổi, 1 phút)

```bash
cd $DEMO && ne new tu-khoa && cd tu-khoa     # mẫu minimal: chốt door_lock, gate custom_lock
ne test                                       # 4 passed · mã 0
```

**Cho thấy:** một lệnh bị chặn trên thiết bị được ghi thành vết ghi (có chế độ ẩn danh); vết ghi mở
thành HTML; `replay` tính lại phán quyết từ dữ kiện đã ghi; một người sửa gate "cho nhanh" ⇒ `replay`
và `test` cùng đỏ với `SAFETY REGRESSION`; `build` đối chiếu agent với bo mạch trước khi nạp.

**Hỗ trợ giả thuyết:** G-e (chuyến đi hiện trường do lỗi phần mềm/cấu hình) · `CEO-X2` (họ đang trả
cho công cụ nào để biết chuyện gì đã xảy ra) · `CEO-X4` (họ cần runtime, hay chỉ cần CI trên stack
của họ = Approach C).

| Phút | Làm | Nói |
|:---:|:---|:---|
| 0:00 | `ne record --out traces --anonymize` rồi trong REPL `:set user_verified false`, `mở khoá`, `exit` | "Thiết bị từ chối một lệnh. Lời người dùng được băm tại nguồn." |
| 0:45 | `ne trace view traces/sess_….json -o sess.html` và mở tệp | "Đây là thứ kỹ thuật viên nhận thay vì bay tới nơi." |
| 1:30 | `ne replay traces/sess_….json --agent agent.toml` | "Phát lại trên laptop: cùng dữ kiện, cùng quyết định." |
| 2:15 | Xoá dòng `user_verified: true` trong `gates/custom_lock@1.0.0.yaml` | "Ai đó nới chính sách cho đỡ báo lỗi." |
| 2:45 | `ne replay …` lần nữa · `ne test` | "Phiên cũ giờ ra ALLOW và chân kích: CI đỏ, mã 1." |
| 3:45 | Trả gate về · `ne build --target linux --board linux-rpi5` · `ne board list` | "Trước khi nạp, agent được đối chiếu với năng lực của bo mạch." |
| 4:30 | `ne verify` | "Ba vết ghi chuẩn mực, phát lại mỗi commit." |

Đầu ra thật:

```text
$ ne record --out traces --anonymize      # REPL: :set user_verified false · mở khoá · exit
neuroedge> trace: traces/sess_70899937.json (9 events)
[exit 0]

$ ne trace view traces/sess_70899937.json -o sess.html
✓ sess.html (9 events)

$ ne replay traces/sess_70899937.json --agent agent.toml
│ 1 │ custom_lock@1.0.0 │ BLOCK    │ BLOCK    │ condition_not_met │
  no pin was driven
✓ decisions match the recording
[exit 0]

# sau khi xoá dòng user_verified: true khỏi allow_when
$ ne replay traces/sess_70899937.json --agent agent.toml
│ 1 │ custom_lock@1.0.0 │ BLOCK    │ ALLOW    │ —      │
  pin door_lock: pulse 5000 ms
✗ NE4002 5 difference(s) from the golden reference — SAFETY REGRESSION
  SAFETY REGRESSION: gate evaluation #1 (custom_lock@1.0.0).verdict: golden 'BLOCK', actual 'ALLOW'
  SAFETY REGRESSION: actuator command #1: golden None, actual {'pin': 'door_lock', 'operation': 'pulse', 'duration_ms': 5000}
[exit 1]

$ ne test
FAILED tests/test_agent.py::test_an_unverified_user_never_moves_the_pin - AssertionError
1 failed, 3 passed in 0.59s
[exit 1]

$ ne build --target linux --board linux-rpi5      # sau khi trả gate về
✓ tu-khoa@0.1.0 builds for linux on linux-rpi5
  checked: 1 requirement(s), 1 action(s), 1 gate(s)

$ ne board list
│ esp32s3-box-3 │ esp32s3 │ esp32s3 │ door_lock, porch_light, gate_relay │
│ linux-rpi5    │ linux   │ bcm2712 │ door_lock, porch_light, gate_relay │
│ sim-default   │ sim     │ none    │ door_lock, porch_light, gate_relay │

$ ne verify
│ happy-path.json         │ ✓ ALLOW │
│ network_offline.json    │ ✓ BLOCK │
│ unverified_attempt.json │ ✓ BLOCK │
│ Compared: decisions only — not timing. Timing equivalence and the esp32s3    │
│ target arrive with Sprint 4 (TSK-S4-04).                                     │
[exit 0]
```

Hai chỗ phải nói đúng:

- `ne gate lint gates` **vẫn xanh** sau khi nới gate gốc (`✓ 1 gate(s) resolved.`). Lint chỉ chứng
  minh kế thừa không nới cha; bắt thay đổi của một gate gốc là việc của `replay` / `test`. Đừng nói
  "lint chặn mọi thay đổi nguy hiểm".
- `--anonymize` băm **chữ người dùng nói**; tham số tool call vẫn ở dạng thô (ở mẫu villa,
  `guest_id: "101"` còn nguyên trong vết ghi). Đừng nói "vết ghi không có dữ liệu cá nhân".

Nếu máy demo là Linux có `gpio-sim` (`scripts/setup_gpio_sim.sh`) và `pip install 'neuroedge[linux]'`,
thêm `ne verify --targets sim,linux` (cùng quyết định trên hai HAL). **Trên macOS lệnh này trượt**, đã
thử:

```text
$ ne verify --targets sim,linux
  ✗ happy-path.json on linux: [NE3001] the libgpiod v2 Python bindings (`gpiod`) are not installed
    fix: pip install 'neuroedge[linux]' (LGPL-2.1, optional; see NOTICE §B)
3 problem(s) found.
[exit 1]
```

**Không tuyên bố:** tất cả §0.1, nhất là Fleet OS. Vết ghi `network_offline.json` ghi target
`esp32s3`, nhưng đó là **vết ghi chuẩn mực viết tay** (`fixtures/traces/`), không phải bản ghi từ bo
mạch thật.

**Hỏi sau demo:** "Tháng trước có bao nhiêu chuyến ra hiện trường, bao nhiêu chuyến hóa ra là lỗi
phần mềm hoặc cấu hình?" · "Hôm nay khi đổi cấu hình cho cả đội thiết bị, anh/chị kiểm bằng gì?"

---

## 3. Smart Home — "tắt đèn khi còn người trên cầu thang"

**Cho thấy:** một trợ lý có ba loại hành vi với ba hợp đồng: trả lời từ knowledge base (lời nói, không
gate), tin tức cần mạng (mất mạng thì nói rõ, không bịa), bật/tắt đèn (hành động vật lý, qua gate có
cảm biến chuyển động). Cùng một gate áp cho lệnh cục bộ và cho agent ngoài gọi qua MCP.

**Hỗ trợ giả thuyết:** `CEO-T1` (họ có cần chạy được khi mất mạng không, đã từng trả giá vì nó chưa) ·
`CEO-T3` (hôm nay họ dùng gì: SDK của hãng chip, nền tảng nhà thông minh, tự viết) · `CEO-X4`.

| Phút | Làm | Nói |
|:---:|:---|:---|
| 0:00 | `ne run --agent fixtures/agents/home-voice/agent.toml` | "Không mạng, không khóa API." |
| 0:15 | `bật đèn` | "Hành động rủi ro thấp vẫn qua gate." |
| 0:45 | `:sensor motion true` · `tắt đèn` | "Còn người: không tắt, hỏi lại." |
| 1:30 | `:sensor motion false` · `tắt đèn` | "Hết người: tắt." |
| 2:00 | `mật khẩu wifi` · `đọc tin tức` | "Câu trả lời lấy tại chỗ. Tin tức cần mạng: nói thẳng là chưa lấy được." |
| 2:45 | `ne mcp tools --agent fixtures/agents/home-voice/agent.toml --external` | "Tool thiết bị đi qua gate; tool bên ngoài chỉ lấy thông tin." |
| 3:30 | MCP client gọi `light_off` khi có người (Phụ lục A, với bản sao agent có `motion = true`) | "Một LLM quyết định tắt đèn cũng bị từ chối y như vậy." |
| 4:30 | (tuỳ chọn) `ne run --agent … --ui` | Giao diện web: đèn, cảm biến, phán quyết trực tiếp |

Đầu ra thật:

```text
$ ne run --agent fixtures/agents/home-voice/agent.toml
home-voice@0.1.0 on sim (sim-default) · offline, typed text (Q-15)
neuroedge> bật đèn
✓ ALLOW light_on@1.0.0 → light_on()
│ porch_light │ HIGH  │        1 │
neuroedge> :sensor motion true
neuroedge> tắt đèn
✗ BLOCK light_off@1.0.0 (reason: condition_not_met, criterion: room_empty)
  action: ask — "Vẫn còn người trong phòng — bạn chắc muốn tắt đèn?"
│ porch_light │ HIGH  │        1 │
neuroedge> :sensor motion false
neuroedge> tắt đèn
✓ ALLOW light_off@1.0.0 → light_off()
│ porch_light │ LOW   │        2 │
neuroedge> mật khẩu wifi
  says (knowledge_local): Mạng wifi là NhaMinh, mật khẩu dán ở mặt dưới router.
neuroedge> đọc tin tức
  says (offline): Hiện không có mạng, mình chưa lấy được tin tức.

$ ne mcp tools --agent fixtures/agents/home-voice/agent.toml --external
│ light_on        │ this agent's MCP server · gate     │ —         │
│ light_off       │ this agent's MCP server · gate     │ —         │
│ news__headlines │ external `news` · information only │ topic     │

# MCP, agent là bản sao `ne new nha --template home-voice` trong $DEMO, sửa [sim.sensors] motion = true
$ python/.venv/bin/python mcp_client.py home $DEMO/mcp-nha.json $DEMO/nha/agent.toml
call light_on({}) -> is_error=False
    {"tool": "light_on", "status": "ALLOW"}
call light_off({}) -> is_error=False
    {"tool": "light_off", "status": "BLOCK", "gate": "light_off@1.0.0", "reason": "condition_not_met",
     "failed_criterion": "room_empty", "on_block": "ask", "message": "Vẫn còn người trong phòng — bạn chắc muốn tắt đèn?"}
```

Vết ghi của phiên MCP ghi nguồn gọi: `"source": "mcp"` ở `tool_call`, và `call_source = mcp` là dữ
kiện gate đọc (đã kiểm bằng `ne trace show $DEMO/mcp-home.json`). `ne run --ui` đã kiểm: trang
`http://127.0.0.1:<port>/` trả HTTP 200; phần nhìn trên trình duyệt chưa được kiểm trong phiên này.

**Không tuyên bố:** tất cả §0.1, thêm: "đọc tin tức" trong demo **không** gọi MCP server tin tức,
vì demo không khai `[system_two]` (TSK-S2-11 cần extra `cloud` và key) — nó nói câu offline. Server tin tức mẫu đọc
`mcp/news.json` cục bộ, không lên internet. Qua MCP, cảm biến lấy từ `[sim.sensors]` trong
`agent.toml`, không đổi được giữa chừng (vì `mcp serve` và `--ui` là hai phiên, TSK-S3-27). Cấu hình
Claude Desktop trong `README.md` **chưa được chạy** trong phiên kiểm này; client ở Phụ lục A đóng vai.

**Hỏi sau demo:** "Sản phẩm của anh/chị đã có lần nào làm một việc vật lý sai vì hiểu nhầm lệnh
hoặc mất mạng chưa? Chuyện gì xảy ra sau đó?" · "Nếu đổi chip, phần nào phải viết lại?"

---

## 4. Industrial IoT — "bơm không chạy khi nắp che mở hoặc quá nhiệt"

Kho **không có** agent công nghiệp mẫu (proposal §1.6 #3 "Industrial Environmental Watcher" chưa
làm). Kịch bản dựng một agent nhỏ từ mẫu `minimal` bằng 5 tệp ở §4.0. Mọi lệnh là lệnh có sẵn; chỉ
nội dung agent là của demo. Nói rõ điều đó với người xem.

### 4.0 Dựng sẵn (trước buổi, 3 phút)

```bash
cd $DEMO && ne new bom && cd bom
rm gates/custom_lock@1.0.0.yaml actions/operate_hardware.py
# rồi ghi 5 tệp dưới đây
ne build --target sim --board sim-default && ne test      # 2 passed · mã 0
```

`agent.toml`

```toml
[agent]
name    = "bom"
version = "0.1.0"

[requires]
"digital.out" = { pins = ["gate_relay"] }
"sensor.read" = { sensors = ["temperature", "door_contact"] }

[gates]
start_pump = "gates/start_pump@1.0.0.yaml"

[targets]
supported = ["sim", "linux", "esp32s3"]

[sim.facts]
operator_verified = true

[sim.sensors]
temperature  = 45
door_contact = true

[sim.sensor_facts]
guard_closed = { sensor = "door_contact", equals = true }
temp_ok      = { sensor = "temperature", lte = 70 }
```

`commands.toml`

```toml
[grammar]
version   = 1
threshold = 0.80

[[command]]
intent   = "start_pump"
patterns = ["chạy bơm", "khởi động bơm", "start the pump"]
tool     = "start_pump"
```

`gates/start_pump@1.0.0.yaml`

```yaml
schema:  neuroedge.gate/v1
name:    start_pump
version: 1.0.0

evaluate:
  operator_verified: { type: bool, instructions: "Người vận hành đã đăng nhập ca" }
  guard_closed:      { type: bool, instructions: "Nắp che bơm đang đóng (cảm biến door_contact)" }
  temp_ok:           { type: bool, instructions: "Nhiệt độ bơm không quá 70 độ C" }

allow_when:
  operator_verified: true
  guard_closed:      true
  temp_ok:           true

on_block: { action: deny }
budget:   { p95_latency_ms: 150, fail: closed }
```

`actions/pump.py`

```python
from neuroedge import action
from neuroedge.hal import digital


@action(name="start_pump", requires="digital.out:gate_relay", gate="start_pump")
def start_pump(duration_s: int = 10) -> None:
    """Chạy bơm `duration_s` giây, chỉ sau khi gate cho phép."""
    digital.out("gate_relay").pulse(seconds=duration_s)
```

`tests/test_agent.py`

```python
import asyncio
from pathlib import Path

from neuroedge.sim import SimSession

AGENT = Path(__file__).resolve().parents[1] / "agent.toml"


def handle(text, **facts):
    session = SimSession.load(AGENT, facts=facts)
    return session, asyncio.run(session.handle(text))


def test_pump_starts_when_everything_is_safe():
    session, turn = handle("chạy bơm")
    assert turn.allowed
    assert session.hal.pin("gate_relay").pulsed_once(duration_ms=10000)


def test_unverified_operator_never_moves_the_relay():
    session, turn = handle("chạy bơm", operator_verified=False)
    assert turn.result.blocked
    assert session.hal.pin("gate_relay").never_pulsed()
```

(Bản đã chạy viết `evaluate` dạng khối nhiều dòng. Dạng rút gọn ở trên cho cùng digest:
`ne gate publish` trên cả hai ra `sha256:ba94a85a…fe64276`.)

**Cho thấy:** điều kiện khoá liên động (interlock) viết thành dữ liệu có phiên bản, đọc được bằng lời;
cảm biến đổi ⇒ phán quyết đổi, rơ-le không nhúc nhích; cùng agent build được cho `linux-rpi5`; nới
một điều kiện ⇒ phát lại phiên cũ đỏ.

**Hỗ trợ giả thuyết:** `CEO-T2` (chứng nhận có là điều kiện mua không — đây là câu then chốt của phân
khúc này) · `CEO-T1` (chính sách như dữ liệu có phiên bản thay cho interlock viết cứng, có đáng tiền
không) · `CEO-T3` (họ đang dùng PLC / rơ-le an toàn / tự viết).

| Phút | Làm | Nói |
|:---:|:---|:---|
| 0:00 | `ne gate explain gates/start_pump@1.0.0.yaml` | "Điều kiện chạy bơm, đọc bằng lời, không đọc mã." |
| 0:45 | `ne run` · `chạy bơm` | "Đủ điều kiện: rơ-le kích 10 giây." |
| 1:15 | `:sensor temperature 85` · `chạy bơm` | "Quá nhiệt: không chạy." |
| 1:45 | `:sensor temperature 45` · `:sensor door_contact false` · `chạy bơm` | "Nắp mở: không chạy." |
| 2:30 | `ne build --target linux --board linux-rpi5` | "Cùng agent, bo mạch Linux: đối chiếu đạt." |
| 3:00 | `ne record --out traces` (nắp mở, `chạy bơm`) → xoá `guard_closed: true` → `ne replay … --agent agent.toml` | "Ai đó bỏ điều kiện nắp che: phiên cũ phát lại thành ALLOW, CI đỏ." |
| 4:30 | Trả gate về, `ne test` | "Xanh lại." |

Đầu ra thật:

```text
$ ne gate explain gates/start_pump@1.0.0.yaml
│ Gate gốc — không kế thừa gate nào                                            │
│ Phân cấp: 1 cấp (start_pump@1.0.0) · Chính sách khi lỗi: fail-closed (lỗi hoặc quá hạn → CHẶN)
2. Điều kiện cho phép (allow_when) — phải đạt TẤT CẢ:
  ✓ guard_closed ∈ {true}
  ✓ operator_verified ∈ {true}
  ✓ temp_ok ∈ {true}
  Tiêu chí không xác định được (mất mạng, không nhận ra lệnh) → CHẶN.

$ ne run
neuroedge> chạy bơm
✓ ALLOW start_pump@1.0.0 → start_pump()
│ gate_relay │ PULSED 10s │        1 │
neuroedge> :sensor temperature 85
neuroedge> chạy bơm
✗ BLOCK start_pump@1.0.0 (reason: condition_not_met, criterion: temp_ok)
  action: deny
neuroedge> :sensor temperature 45
neuroedge> :sensor door_contact false
neuroedge> chạy bơm
✗ BLOCK start_pump@1.0.0 (reason: condition_not_met, criterion: guard_closed)
  action: deny
│ gate_relay │ PULSED 10s │        1 │      # vẫn 1 lệnh: hai lần chặn không kích gì

$ ne build --target linux --board linux-rpi5
✓ bom@0.1.0 builds for linux on linux-rpi5
  checked: 2 requirement(s), 1 action(s), 1 gate(s)

$ ne record --out traces            # REPL: :sensor door_contact false · chạy bơm · exit
✗ BLOCK start_pump@1.0.0 (reason: condition_not_met, criterion: guard_closed)
neuroedge> trace: traces/sess_f3e9744d.json (10 events)

# sau khi xoá dòng guard_closed: true
$ ne replay traces/sess_f3e9744d.json --agent agent.toml
│ 1 │ start_pump@1.0.0 │ BLOCK    │ ALLOW    │ —      │
  pin gate_relay: pulse 10000 ms
✗ NE4002 5 difference(s) from the golden reference — SAFETY REGRESSION
[exit 1]

$ ne test          # sau khi trả gate về
2 passed in 0.57s
[exit 0]
```

`ne replay` **cần** `--agent agent.toml` với dự án ngoài kho; thiếu nó, lệnh báo `NE3002 … no sample
agent named 'bom'` (xem báo cáo, mục lệch tài liệu).

**Không tuyên bố:** tất cả §0.1, thêm: đây **không** phải PLC an toàn và không thay rơ-le an toàn
có chứng nhận; `LinuxHAL` mới có `digital.out` — `sensor.read` trên Linux **chưa** hiện thực
(`CHANGELOG.md` §3.7), nên `build` cho `linux-rpi5` đạt là đối chiếu năng lực khai trong profile, không
phải đọc cảm biến thật; chưa có CEL, `allow_when` chỉ nhận dạng mapping toán tử; ngưỡng 70 °C nằm ở
`agent.toml` (`[sim.sensor_facts]`), là cách của `sim`, không phải của gate — gate chỉ thấy `temp_ok`.

**Hỏi sau demo:** "Hôm nay điều kiện khoá liên động của máy này nằm ở đâu, ai được sửa, và lần sửa gần
nhất được kiểm thế nào?" · "Nếu không có chứng nhận [tiêu chuẩn họ nêu], có ai trong công ty ký mua
không?"

---

## Phụ lục A — client MCP dùng trong demo

Đóng vai Claude Desktop (không có trong kho; đặt ở `$DEMO/mcp_client.py`). Dùng SDK `mcp` đã cài qua
extra `neuroedge[mcp]`. Ghi chú: SDK đang cài dùng tên thuộc tính `is_error` / `structured_content`.

```python
import asyncio, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = "<đường dẫn gốc kho>"
NE = f"{REPO}/python/.venv/bin/neuroedge"

async def main(agent, calls):
    params = StdioServerParameters(command=NE, cwd=REPO,
        args=["mcp", "serve", "--agent", agent, "--trace-out", sys.argv[2]])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for name, args in calls:
                r = await session.call_tool(name, args)
                print(f"call {name}({args}) -> is_error={r.is_error}")
                print("   ", " ".join(getattr(c, "text", "") for c in r.content))

if sys.argv[1] == "villa":
    agent = f"{REPO}/fixtures/agents/villa-concierge/agent.toml"
    calls = [("unlock_door", {"guest_id": "101"}),
             ("unlock_door", {"guest_id": "101", "duration_s": "forever"}),
             ("unlock_door", {"guest_id": "101", "override": True})]
else:
    agent = sys.argv[3] if len(sys.argv) > 3 else f"{REPO}/fixtures/agents/home-voice/agent.toml"
    calls = [("light_on", {}), ("light_off", {})]
asyncio.run(main(agent, calls))
```

## Phụ lục B — lệnh đã kiểm trong phiên soạn

| Lệnh | Kết quả |
|:---|:---|
| `gate lint` · `gate lint fixtures/gates/invalid --registry fixtures/gates/registry` | mã 0 · mã 1 (19/19 FAIL, đúng kỳ vọng) |
| `gate explain` (2 gate) · `gate resolve` (gate nới) | mã 0 · mã 1 `NE2003` |
| `run -c` (villa ×3, `--board linux-rpi5`) · REPL villa, home-voice, bom | mã 0 · `--board linux-rpi5` mã 1 `NE3003` |
| `record --out` (± `--anonymize`) · `trace validate` · `trace show` · `trace view -o` | mã 0 |
| `replay` (khớp · lệch) | mã 0 · mã 1 `NE4002` |
| `new` (`minimal`, `villa-concierge`, `home-voice`) · `test` trong 4 dự án | mã 0 (và mã 1 khi gate bị nới) |
| `build --target sim` · `build --target linux --board linux-rpi5` | mã 0 |
| `board list` · `verify` · `gate publish` | mã 0 |
| `verify --targets sim,linux` | mã 1 trên macOS (thiếu `gpiod`) |
| `mcp tools --external` · `mcp serve` qua client Phụ lục A | mã 0 |
| `run --ui --no-browser --port 8765` | HTTP 200 |
