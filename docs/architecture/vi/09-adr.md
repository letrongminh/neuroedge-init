# 09 · Quyết định kiến trúc (ADR)

> **Phạm vi:** các quyết định định hình kiến trúc, mỗi quyết định ở dạng ADR: bối cảnh → quyết định →
> hệ quả → nơi cưỡng chế. **Nguồn:** sổ quyết định duy nhất là PRD §15 (mã `Q-N`); thay đổi hợp đồng
> đóng băng là RFC (`docs/rfc/`). Trang này **không** thay hai nguồn đó: nó chỉ ra mỗi quyết định trông
> như thế nào trong kiến trúc, và mã nào giữ nó.

Định danh ADR chính là mã `Q-N` hoặc `RFC-NNNN`, để không có hai hệ đánh số. Trạng thái đầy đủ của 46
quyết định ở PRD §15; dưới đây là những quyết định có hệ quả kiến trúc.

## 1. Thực thi và an toàn

### Q-24 · Mọi hành động là một tool call qua một đường duy nhất
- **Bối cảnh.** Hành động có thể đến từ ngữ pháp cục bộ, LLM, agent khác. Nhiều đường vào là nhiều chỗ
  để quên gate.
- **Quyết định.** Mỗi `@action` là một công cụ có schema sinh từ chữ ký hàm. Mọi nguồn gửi cùng một
  `ToolCall` qua `dispatch()` → `c.do()` → gate → token; dispatcher chèn `call_source`.
- **Hệ quả.** Một điểm cưỡng chế duy nhất; gate có thể phân biệt nguồn gọi; MCP là một adapter mỏng.
- **Cưỡng chế.** `actions/tools.py::dispatch`, `mcp_server.py`; `docs/spec/tool_calling.md`; corpus
  `fixtures/tool_calls/`.

### Q-9 · Không CEL trên vi điều khiển (phương án A)
- **Bối cảnh.** Một bộ lượng giá biểu thức trên chip là thêm một hiện thực phải giữ đồng bộ, đúng ở
  tầng an toàn.
- **Quyết định.** `neuroedge build` biên dịch gate thành cây quyết định tất định; firmware chỉ duyệt cây.
  `allow_when` hôm nay là ánh xạ toán tử; CEL là front-end tuỳ chọn về sau (TSK-S2-06, hoãn).
- **Hệ quả.** Ngữ nghĩa gate có một nguồn (engine Python); chip nhỏ và tất định; mọi toán tử mới phải
  biên dịch được xuống cùng cây.
- **Cưỡng chế.** `engine/decision_tree.py`; resolver từ chối `allow_when` dạng chuỗi.

### Q-23, RFC-0003 · Cây trên thiết bị là bố cục nhị phân cố định `NETR` v1
- **Bối cảnh.** Parser JSON trên MCU tốn flash, RAM và là bề mặt tấn công.
- **Quyết định.** Bố cục nhị phân little-endian, không con trỏ, có magic, phiên bản và CRC, link dưới
  dạng mảng `const` trong flash; `decision_tree.v1.json` chỉ là định dạng nội bộ của host.
- **Hệ quả.** Walker đọc tại chỗ, không cấp phát; đổi bố cục là việc có RFC và tăng `layout_version`.
- **Cưỡng chế.** `engine/binary_tree.py` ↔ `components/ne_gate/`; `test_c_walker.py`.

### Q-18, RFC-0004 · Gate con không được nới `budget` và `on_block`
- **Quyết định.** `p95` con ≤ cha; chuỗi đã `closed` không mở lại; con không thêm `degrade` hay đổi
  `fallback_action`.
- **Hệ quả.** Kế thừa là quan hệ chỉ-siết trên **mọi** trường có tác động an toàn, không chỉ `allow_when`.
- **Cưỡng chế.** `engine/gate_resolver.py`; corpus `fixtures/gates/invalid/`.

### Q-25, RFC-0005 · Giới hạn tham số nằm trong gate
- **Quyết định.** Khoảng, tập, độ dài của tham số khai ở gate (không ở `agent.toml`), chỉ được thu hẹp
  khi kế thừa, kiểm trước mọi dữ kiện kể cả giá trị mặc định, và xuất hiện trong `inputSchema`.
- **Hệ quả.** Một tham số nguy hiểm (`duration_s = 3600`) bị chặn bởi gate, không phụ thuộc bên gọi.
- **Cưỡng chế.** `engine/arguments.py`; bản ghi tham số trong `NETR`.

### Q-26, RFC-0006 · Chỉ người tại thiết bị xác nhận được, và chỉ cho tiêu chí gate liệt kê
- **Quyết định.** Chỉ `local_grammar` và `ui` trả lời được câu hỏi `ask`; xác nhận **lượng giá lại** gate,
  chỉ miễn các tiêu chí trong `on_block.confirms`.
- **Hệ quả.** Một lời "có" không bao giờ vượt qua tiêu chí khác; model và client MCP không có đường
  xác nhận.
- **Cưỡng chế.** `actions/confirmation.py`; `test_tool_confirm.py`; `confirm_mask` trong `NETR`.

### Q-17 · Mọi `on_block` đều chặn hành động vật lý
- **Quyết định.** `escalate` và `ask` còn ghi vết và gọi hook (mặc định không làm gì); `degrade` chạy
  `fallback_action` **qua gate riêng của nó**.
- **Cưỡng chế.** `engine/gate.py`, `actions/conversation.py`.

### Q-14 · Mất mạng thì gate vẫn lượng giá bằng ngữ pháp lệnh cục bộ
- **Quyết định.** Chỉ chặn với `gate_unreachable` khi fallback không có hoặc không chạy được. Fallback là
  P0; mỗi target một backend trên cùng một ngữ pháp.
- **Cưỡng chế.** `models/grammar.py`, `models/system.py`; `test_offline_fallback.py`. Trên `esp32s3`:
  chưa (TSK-S5-07).

## 2. Model và nhà cung cấp

### Q-4, Q-12 · System 1 là Jev qua System One API; System 2 là LLM chuẩn OpenAI
- **Quyết định.** Chuẩn mặc định là nền tảng tương thích OpenAI (một base URL, một khoá): chat
  completions, audio, và endpoint quyết định có kiểu (`POST /systemone`). Nhà cung cấp khác đi qua
  adapter tự viết.
- **Hệ quả.** Đổi nhà cung cấp là đổi cấu hình; model chỉ trả dữ kiện (`Fact`/`Unavailable`), không bao
  giờ trả phán quyết.
- **Cưỡng chế.** `models/providers/`, `perception/providers/`.

### Q-10 · LiteLLM là thư viện, không phải proxy
- **Quyết định.** Dùng LiteLLM như SDK, luôn sau `neuroedge.models.providers`, chỉ cài qua extra `cloud`.
- **Hệ quả.** `pip install neuroedge` nhẹ và không cần khoá; không có máy chủ nào do NeuroEdge vận hành.
- **Cưỡng chế.** `pyproject.toml`; job `cloud-extra`.

### Q-27 · System 2 là một MCP host
- **Quyết định.** Công cụ thiết bị đi qua máy chủ MCP của chính agent (vẫn qua gate); MCP server bên
  ngoài chỉ để lấy thông tin, theo danh sách cho phép, kết quả là dữ liệu không tin cậy. MCU không bao
  giờ là host.
- **Cưỡng chế.** `mcp_host.py`; `test_mcp_host.py`.

### Q-7, Q-45 · Từ đánh thức: người dùng tự cấp mô hình
- **Quyết định.** openWakeWord trên host, microWakeWord trên chip (Q-7). Mô hình dựng sẵn của
  openWakeWord có giấy phép phi thương mại, không hợp Q-45 ⇒ không giao kèm, không tải.
- **Cưỡng chế.** `perception/providers/wake.py`; `TODOS.md` #49.

## 3. Phần cứng, target, mô phỏng

### Q-2, Q-3 · Một bo mạch tham chiếu và một ngân sách bộ nhớ
- **Quyết định.** ESP32-S3-BOX-3 là bo mạch tham chiếu duy nhất (bất biến 6). Ngân sách: SRAM ≥ 120 KB
  và PSRAM ≥ 2 MB cho ứng dụng, firmware ≤ 3,5 MB để vừa A/B trên flash 16 MB.
- **Cưỡng chế.** `boards/esp32s3-box-3.toml`, `partitions.csv`, `scripts/check_firmware_size.py`.

### Q-8 · C trên ESP-IDF cho chip, Python cho host
- **Hệ quả.** Hai hiện thực của một đặc tả ⇒ đặc tả quy phạm và vector tuân thủ dùng chung là bắt buộc.
- **Cưỡng chế.** `test_c_walker.py`, `test_c_token.py`, `test_c_trace.py`; self-test lúc khởi động.

### Q-13 · Ba bậc target
- **Quyết định.** Bậc 1 (`sim`, `linux`, `esp32s3`) giữ toàn bộ cam kết; bậc 2 do đội lõi bảo trì với
  cam kết hẹp hơn; bậc 3 do cộng đồng port và tự kiểm bằng bộ tuân thủ.
- **Trạng thái.** Bảng bậc máy đọc được (`TARGET_TIERS`) mới là đề xuất trong RFC-0002; mã hôm nay có
  đúng ba target.

### Q-16, Q-21 · Mô phỏng theo tầng bằng công cụ mã nguồn mở đã kiểm chứng
- **Quyết định.** Không tự viết trình giả lập. Mỗi tầng một công cụ: `SimHAL`, gpio-sim, `i2c-stub` +
  `lm75`, framebuffer ảo, ảnh golden LVGL build trên host, C biên dịch trên host, Espressif QEMU; bo
  mạch thật cho âm thanh, màn hình, bộ nhớ. Không dùng Renode, Wokwi.
- **Cưỡng chế.** `docs/spec/simulation_coverage.md`; các job `linux-hal`, `ui-golden`, `firmware-qemu`.

### Q-22 · Khử vang bằng phần mềm trên `linux`
- **Quyết định.** `audio.in` đọc nút nguồn đã khử vang của PipeWire `module-echo-cancel`; `audio.out` phát
  vào nút sink của nó làm tín hiệu tham chiếu. `linux-rpi5` chỉ khai `aec = true` khi đo đạt.
- **Cưỡng chế.** `hal/linux.py`, `pipewire/neuroedge-echo-cancel.conf`.

## 4. Quản trị, giấy phép, lịch

### Q-11 · Danh sách giấy phép cho phép
- **Quyết định.** Cho phép MIT, BSD, Apache-2.0, ISC, PSF, CNRI-Python, MPL-2.0 (nguyên bản), Zlib,
  CC0-1.0; cấm GPL/LGPL/AGPL, SSPL, BSL. Hawkbit (EPL-2.0) được dùng nguyên bản làm dịch vụ; **EMQX
  (BSL) không dùng**.
- **Hệ quả.** `gpiod` (LGPL) chỉ là phần mở rộng tuỳ chọn; broker MQTT của Fleet OS chọn trong
  Mosquitto, NanoMQ, VerneMQ.
- **Cưỡng chế.** `scripts/check_licences.py`; jobs `cloud-extra`, `licence-obligations`.

### Q-45 · Giấy phép của NeuroEdge
- **Quyết định.** Mã theo PolyForm Noncommercial 1.0.0; `schemas/`, `docs/spec/`, `fixtures/compliance/`
  theo Apache-2.0 để ai cũng hiện thực được chuẩn.
- **Cưỡng chế.** `LICENSE`, `LICENSING.md`, `test_packaging.py`.

### Q-39 · Roadmap theo increment
- **Quyết định.** Một roadmap, đo bằng increment I0…I18, mỗi increment một ngày dự báo, một tag và một tín
  hiệu đo; không phát hành ra ngoài trước I6.
- **Cưỡng chế.** `neuroedge-roadmap.md` §0.2; `test_plan_contract.py`.

### Q-38 · Không phải chức năng an toàn được chứng nhận
- **Quyết định.** Tạm thời OUT: không SIL, không PL; robot di động bắt buộc có nút dừng khẩn phần cứng.

## 5. Quyết định cho hướng mở rộng (chưa có mã)

| Mã | Quyết định | Hệ quả khi hiện thực |
|:---|:---|:---|
| Q-32 | Robot phân tầng sau Developer Beta; vết ghi nhiều node mở rộng `trace.v1` bằng trường tuỳ chọn | Không cần `trace.v2` |
| Q-35 | Mỗi cơ cấu chấp hành tự khai trạng thái an toàn khi mất liên lạc; không khai thì dừng | Cần RFC cho trường khai báo |
| Q-36 | Zenoh-pico trên MCU, `zenohd` trên Pi; spike với ngưỡng đạt/trượt, micro-ROS là phương án B | Bản nháp RFC node |
| Q-37 | Token thuê có hạn cho `motion.*` (kênh, biên độ tối đa, TTL ngắn), gia hạn qua mỗi lệnh có gate | Khác token dùng-một-lần hôm nay; cần RFC-motion |

## 6. RFC

| RFC | Hợp đồng | Trạng thái | Hiện thực |
|:---|:---|:---|:---|
| [0001](../../rfc/0001-gate-schema-conditional-requirements.md) | `gate.v1`: trường bắt buộc có điều kiện cho gate kế thừa | Chấp nhận, đã hiện thực | `schemas/gate.v1.json` |
| [0002](../../rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md) | Mở danh sách target theo bậc | **Đang thảo luận**; thuộc I11 | chưa |
| [0003](../../rfc/0003-bo-cuc-nhi-phan-cay.md) | Bố cục nhị phân `NETR` v1 | Chấp nhận, đã hiện thực | `binary_tree.py`, `ne_gate/` |
| [0004](../../rfc/0004-ke-thua-budget-on-block.md) | Không nới `budget`, `on_block` khi kế thừa | Chấp nhận, đã hiện thực | `gate_resolver.py` |
| [0005](../../rfc/0005-rang-buoc-tham-so-trong-gate.md) | Giới hạn tham số trong gate | Chấp nhận, đã hiện thực | `arguments.py`, bản ghi tham số `NETR` |
| [0006](../../rfc/0006-xac-nhan-ask-confirms.md) | `on_block.confirms` | Chấp nhận, đã hiện thực | `confirmation.py`, `confirm_mask` |

## 7. Ra một quyết định kiến trúc mới

1. **Quyết định** được ghi ở PRD §15 với mã `Q-N` mới — nơi duy nhất.
2. Nếu nó đổi một thứ trong danh sách `CONTRIBUTING.md` §3 (lược đồ, ngữ nghĩa phân giải, vết ghi chuẩn
   mực, gate khoá, bố cục `NETR`) thì cần **RFC**: PR đầu chỉ chứa tệp RFC; PR sau dẫn số RFC.
3. Nếu nó có hệ quả kiến trúc, thêm một mục ADR vào trang này (bối cảnh, quyết định, hệ quả, cưỡng chế),
   dẫn mã `Q-N` — không chép lại nội dung quyết định.
4. Nếu nó đổi đồ thị phụ thuộc giữa các gói, sửa `ALLOWED` trong `python/tests/test_architecture_layers.py`
   và bảng ở [`03`](03-component-host-c4l3.md) §2 trong cùng thay đổi.
