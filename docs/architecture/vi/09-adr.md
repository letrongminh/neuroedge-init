# 09 · Quyết định kiến trúc (ADR)

> **Phạm vi:** các quyết định định hình kiến trúc, mỗi quyết định ở dạng ADR: bối cảnh → quyết định →
> hệ quả → nơi cưỡng chế. **Nguồn:** sổ quyết định duy nhất là PRD §15 (mã `Q-N`); thay đổi hợp đồng
> đóng băng là RFC (`docs/rfc/`). Trang này **không** thay hai nguồn đó: nó chỉ ra mỗi quyết định trông
> như thế nào trong kiến trúc, và mã nào giữ nó.

**Đọc chương này để làm gì:** Dành cho kỹ sư hệ thống, người duyệt an toàn và QA. Chương này trả lời câu hỏi: *vì sao kiến trúc có hình dạng như hiện tại và quyết định nào định hình từng cơ chế an toàn*. Đọc sau [`00-overview.md`](00-overview.md) và [`01-context-c4l1.md`](01-context-c4l1.md); đọc trước khi đề xuất thay đổi lớn hoặc mở RFC mới tại [`docs/rfc/`](../../rfc/).

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

### Q-46 · Câu "có"/"không" nói ra chỉ trả lời câu hỏi ask của chính lượt đó
- **Bối cảnh.** Khi người dùng trả lời bằng giọng nói qua STT, nguy cơ nhận diện sai từ tiếng ồn hoặc một câu nói muộn có thể vô tình xác nhận một câu hỏi nguy hiểm ở lượt trước đó.
- **Quyết định.** Câu trả lời nói ra chỉ trả lời câu hỏi `ask` của chính lượt đó: trong lượt mà câu hỏi mở (T11), hoặc nói ngắt lời khi câu hỏi đang được đọc. TTS gặp lỗi khi đọc câu hỏi thì máy trạng thái quay về IDLE, không mở lượt trả lời (câu hỏi chưa nghe thì không thể xác nhận). Gõ chữ và nút bấm UI giữ nguyên theo RFC-0006. (PRD §15 Q-46).
- **Hệ quả.** Một ảo giác của STT trên tiếng ồn, hay một câu "có" cho câu hỏi khác, không đứng thay được một tiêu chí trong `confirms`.
- **Cưỡng chế.** `docs/spec/voice_fsm.md` §4 (T12), §5.4, §9 (V4); `perception/voice_fsm.py`, `perception/voice_session.py`, `sim/session.py`.

### Q-48 · Máy trạng thái hội thoại thuộc L2, không phải L4
- **Bối cảnh.** Sơ đồ 5 tầng ở proposal §3.1 đặt "máy trạng thái hội thoại" ở L4, trong khi proposal §3.4 và mã (`perception/` tự khai L2) đặt nó ở L2.
- **Quyết định.** Máy trạng thái lượt thoại (nghe, nghĩ, nói, cắt lời) thuộc **L2 — Perception và runtime hội thoại**; L4 là logic agent, bộ nhớ ngữ cảnh, tool call có gate (MCP), System 2 (PRD §15 Q-48).
- **Hệ quả.** Máy chạy thời gian thực trên cả chip lẫn host với một bộ vector tuân thủ; nó huỷ lệnh actuator đang chờ khi bị cắt lời nhưng không lượng giá gate và không lái chân. Không đổi mã; sơ đồ proposal §3.1 đã sửa.
- **Cưỡng chế.** `perception/voice_fsm.py`, `docs/spec/voice_fsm.md`, `fixtures/compliance/voice/`; bảng tầng của [`03`](03-component-host-c4l3.md) §2.

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

### Q-28 · Mốc giao lớp trừu tượng provider (FR-GW)
- **Bối cảnh.** Lớp trừu tượng provider (FR-GW) cần hỗ trợ đa nhà cung cấp và failover, nhưng việc xây dựng toàn bộ chức năng quản trị đội thiết bị tập trung quá sớm sẽ làm phình phạm vi v1.0.
- **Quyết định.** v1.0 (Khối 1a) chỉ giao FR-GW-01 ở mức tối thiểu (một bảng `[system_two]` trong `agent.toml`, khoá đọc từ biến môi trường, không lưu trong file hay mã) và FR-GW-03 (hợp đồng failover trong mã nguồn). Phần còn lại thuộc v1.1 (Khối 2, TSK-K2-01→03): khai báo nhiều provider và failover trong `agent.toml` (TSK-K2-02), một endpoint và credential dùng chung cho cả đội thiết bị, FR-GW-02/04 phía server, FR-GW-05→07 (TR-1, TR-6). (PRD §15 Q-28).
- **Hệ quả.** v1.0 chạy trên `sim`/`linux` với một provider do người dùng giữ khoá, không cần máy chủ của NeuroEdge; phần cấp đội thiết bị của lớp provider (v1.1) vẫn là lõi tự vận hành, không thương mại hoá (roadmap §6.1), và chỉ có nghĩa khi có Fleet OS.
- **Cưỡng chế.** `models/providers/config.py`, `agent.toml`; [`15`](15-target-architecture.md) §3.3.

### Q-47 · FastAPI WebSockets của Fleet OS chỉ cho kết nối và viễn trắc
- **Bối cảnh.** Proposal §6.2 từng ghi FastAPI WebSockets của Fleet OS "cho luồng âm thanh" — phần sót từ khi còn Inference Gateway thương mại; proposal §6.1, §8.4, roadmap §3.4, §6.1 và FR-GW-04 đều nói âm thanh là việc của lớp provider thuộc lõi.
- **Quyết định.** Fleet OS dùng FastAPI WebSockets (cùng broker MQTT, Q-11) **chỉ cho kết nối và viễn trắc**; âm thanh không đi qua Fleet OS (PRD §15 Q-47).
- **Hệ quả.** Luồng WebSocket âm thanh của thiết bị (khung Opus nhị phân, PRD Phụ lục D.2) kết thúc ở lớp provider tự vận hành (FR-GW-04); thiết bị nói được mà không cần tài khoản Fleet OS (P-3); kho của Fleet OS chỉ giữ quyết định (Q-6, NFR-PRIV-03); NeuroEdge không đứng giữa luồng token (N4).
- **Cưỡng chế.** Chưa có mã — `targets/esp32s3/audio/provider_client.c` (TSK-S5-06), `services/fleet/` (TSK-K2-04…09); [`15`](15-target-architecture.md) §3.1, §3.3.

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

### Q-15 · Đầu vào mặc định của sim
- **Bối cảnh.** Hành trình 10 phút đầu tiên (TTFV < 10 phút, M1) đòi hỏi lập trình viên chạy thử được ngay sau khi cài đặt, không bị gián đoạn bởi thiết lập micro, tải mô hình hay đăng ký khoá API đám mây.
- **Quyết định.** Trình mô phỏng `sim` mặc định nhận đầu vào văn bản gõ (CLI hoặc web UI) đưa vào bộ khớp ngữ pháp lệnh cục bộ của Q-14: hoàn toàn không cần mạng, không cần API key, và thực thi tất định. Giọng nói và STT đám mây chỉ là tuỳ chọn khi có khoá; mô hình nhận diện giọng nói trên chip (WakeNet/MultiNet/TFLite Micro) chỉ thuộc target `esp32s3` (FR-DX-02). (PRD §15 Q-15).
- **Hệ quả.** Lần chạy đầu tiên tất định, không mạng, không key (FR-DX-02); hành trình 10 phút bước 2–4 đổi theo (PRD §2.3).
- **Cưỡng chế.** `sim/`, `models/grammar.py`; ngữ pháp mẫu `fixtures/agents/*/commands.toml`.

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
- **Quyết định.** Một roadmap, đo bằng increment I0…I18 (thêm I2a, I2b, I3a, I4a, I5a; bỏ I12 và I15 — Q-52), mỗi increment một ngày dự báo, một tag và một tín
  hiệu đo; không phát hành ra ngoài trước I6.
- **Cưỡng chế.** `neuroedge-roadmap.md` §0.2; `test_plan_contract.py`.

### Q-38 · Không phải chức năng an toàn được chứng nhận
- **Quyết định.** Tạm thời OUT: không SIL, không PL; robot di động bắt buộc có nút dừng khẩn phần cứng.

### Q-6 · Chính sách lưu trữ vết ghi Fleet OS
- **Bối cảnh.** Vết ghi từ đội thiết bị chứa dữ liệu cá nhân (ai mở cửa lúc nào); chi phí lưu trữ không phải ràng buộc (~1,3 KB mỗi phiên).
- **Quyết định.** Fleet Standard giữ vết 90 ngày; Fleet Enterprise giữ 3 năm. Vết ghi lên kho theo FR-FLT-05 chỉ chứa quyết định, không dữ liệu thô (NFR-PRIV-03); thời hạn là mức trần, không phải mức sàn. Hạn mức theo thiết bị chỉ để chặn thiết bị chạy vòng, không là đòn bẩy giá (~23 GB/năm cho 1.000 thiết bị × 50 phiên/ngày (ước lượng); PRD §15 Q-6).
- **Hệ quả.** Kho chỉ giữ quyết định, không dữ liệu thô (NFR-PRIV-03); vì vết vẫn chứa dữ liệu cá nhân (ai mở cửa lúc nào), thời hạn là mức trần, không phải mức sàn.
- **Cưỡng chế.** Chưa có mã — kho vết ghi Fleet OS (TSK-K2-08, `services/fleet/trace_collector.py`, proposal §6.4); [`15`](15-target-architecture.md) §3.1.

## 5. Quyết định cho hướng mở rộng (chưa có mã)

| Mã | Quyết định | Hệ quả khi hiện thực |
|:---|:---|:---|
| Q-32 | Robot phân tầng sau Developer Beta; vết ghi nhiều node mở rộng `trace.v1` bằng trường tuỳ chọn | Không cần `trace.v2` |
| Q-33 | **Bối cảnh:** Robot phân tầng cần node phụ trách cơ cấu chấp hành/tay máy độc lập. **Quyết định:** RP2350 là node tham chiếu thứ hai do đội lõi port: HAL C trên Pico SDK (`digital.out`, `sensor.read`), walker và sổ token C99 biên dịch cho ARM, profile bo mạch và runner test bo thật. | Đội lõi gánh thêm một target bảo trì lâu dài; ngoại lệ có chủ đích cho danh mục loại trừ ở PRD §14; bo mạch tham chiếu v1.0 vẫn là Box-3 (Q-2); [`15`](15-target-architecture.md) §4.3 |
| Q-34 | **Bối cảnh:** Robot di động cần dẫn đường và tránh vật cản, nhưng NeuroEdge không tự phát triển lại SLAM/navigation. **Quyết định:** Tích hợp nguyên bản ROS 2 và Nav2 qua adapter tại ranh giới gate; gate xét duyệt mọi lệnh tốc độ (`cmd_vel`), kể cả khi Nav2 đang tự động dẫn đường. | Thiết lập tầng an toàn robot di động mới (gate chu kỳ 10–20 Hz, vùng cấm); cần RFC an toàn robot di động và khảo sát câu hỏi C6 từ người mua robot (Q-38, `TODOS.md` #40); [`15`](15-target-architecture.md) §4.3 |
| Q-35 | Mỗi cơ cấu chấp hành tự khai trạng thái an toàn khi mất liên lạc; không khai thì dừng | Cần RFC cho trường khai báo |
| Q-36 | Zenoh-pico trên MCU, `zenohd` trên Pi; spike với ngưỡng đạt/trượt, micro-ROS là phương án B | Bản nháp RFC node |
| Q-37 | Token thuê có hạn cho `motion.*` (kênh, biên độ tối đa, TTL ngắn), gia hạn qua mỗi lệnh có gate | Khác token dùng-một-lần hôm nay; cần RFC-0011 |
| Q-40 | **Bối cảnh:** Nhiều hướng mở rộng sau Beta (NeuroBrain, robot phân tầng, thị giác, port cộng đồng) có nguy cơ làm loãng nguồn lực đội lõi nếu không có thứ tự ưu tiên. **Quyết định:** Thứ tự mở rộng sau Beta neo theo phụ thuộc: mở danh sách target (trước là I11, nay gộp vào I2c — Q-67) → bộ port cộng đồng (I13) → robot phân tầng (I14); hệ sinh thái (I18) sau I13 và Registry. *(Sửa 2026-09-30: phần NeuroBrain thay bằng Q-55 — vào MVP ở I4a, I5a; thị giác cơ bản thay bằng Q-53 — vào MVP ở I2a, I3a; I12 và I15 không còn là increment.)* *(Sửa 2026-10-04: I11 gộp vào I2c theo Q-67, làm trước NeuroBrain trong MVP.)* | Bảo vệ đường găng v1.0 và công của V2 (R-7) — nay theo Q-52 bằng cách dời ngày thay vì cắt phạm vi; [`15`](15-target-architecture.md) §4 |
| Q-52 | **MVP = v1.0 đầy đủ**, một lần ra mắt; trượt thì dời ngày, không cắt phạm vi; bốn phase P0 → MVP → Beta và thương mại → mở rộng (`neuroedge-prd.md` §15) | Roadmap thêm I2a, I2b, I3a, I4a, I5a; nghiệm thu A1–A12 (nay A1–A13, A13 thêm bởi Q-67); giả định đủ người V1–V7 |
| Q-53 | Bốn gói nguyên thủy mở rộng (cảm biến, PWM, thị giác, chuyển động) bắt buộc trên cả ba target bậc 1, tuỳ chọn theo bo mạch | Sáu RFC (RFC-0007, RFC-0009 → RFC-0013); thêm bo ESP32-S3 có camera và profile `sim-rpi5` |
| Q-54 | Thị giác vào gate qua dữ kiện do maker khai; gate khoá ngưỡng tin cậy bằng tiêu chí `numeric` | Không có ngữ nghĩa gate riêng cho thị giác; vết ghi không chứa ảnh thô |
| Q-55 | NeuroBrain vào MVP trên cả ba target, phủ bốn gói nguyên thủy | I4a (host) và I5a (chip); thay phần thứ tự NeuroBrain của Q-40 |
| Q-67 | **Nền tảng mở:** bên thứ ba tự nối NeuroEdge với sản phẩm mới mà không sửa lõi — lõi dùng độc lập, Extension SDK sáu loại điểm cắm, proxy, cơ cấu từ xa, index cộng đồng; bất biến an toàn không đổi (`neuroedge-prd.md` §15; thiết kế `neuroedge-design-open-platform.md`) | Increment I2c làm trước NeuroBrain, I11 gộp vào; RFC-0002 ký, mã RFC-0014 kéo lên, RFC-0016 → RFC-0018 là bản nháp; `source` của tool call thành không gian tên (đảo RFC-0015 §10 câu 11); corpus tuân thủ sang Apache-2.0; nghiệm thu A13; lịch MVP dài thêm (Q-52); [`13`](13-evolution-i0-i18.md), [`16`](16-ecosystem-landscape.md) |

## 6. RFC

| RFC | Hợp đồng | Trạng thái | Hiện thực |
|:---|:---|:---|:---|
| [0001](../../rfc/0001-gate-schema-conditional-requirements.md) | `gate.v1`: trường bắt buộc có điều kiện cho gate kế thừa | Chấp nhận, đã hiện thực | `schemas/gate.v1.json` |
| [0002](../../rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md) | Mở danh sách target theo bậc | Chấp nhận (2026-10-04, Q-67); phần mã chuyển vào I2c (trước là I11) | chưa — TSK-V1a-02 → V1a-06, TSK-I2c-05 |
| [0003](../../rfc/0003-bo-cuc-nhi-phan-cay.md) | Bố cục nhị phân `NETR` v1 | Chấp nhận, đã hiện thực | `binary_tree.py`, `ne_gate/` |
| [0004](../../rfc/0004-ke-thua-budget-on-block.md) | Không nới `budget`, `on_block` khi kế thừa | Chấp nhận, đã hiện thực | `gate_resolver.py` |
| [0005](../../rfc/0005-rang-buoc-tham-so-trong-gate.md) | Giới hạn tham số trong gate | Chấp nhận, đã hiện thực | `arguments.py`, bản ghi tham số `NETR` |
| [0006](../../rfc/0006-xac-nhan-ask-confirms.md) | `on_block.confirms` | Chấp nhận, đã hiện thực | `confirmation.py`, `confirm_mask` |
| [0007](../../rfc/0007-digital-in-i2c-analog-in-phong-bi.md) | `digital.in`, bus I2C chỉ đọc, `analog.in`, khai báo phong bì trong `board.v1` (TSK-N0-03). Đọc mức logic và quét bus lab mà không đổi `gate.v1` | Chấp nhận (2026-10-01); hiện thực phần host: `digital.in`, I2C, `analog.in`, phong bì; còn `esp32s3` | `hal/envelope.py`, `hal/i2c_bus.py`, `hal/__init__.py`, `board.v1` |
| [0008](../../rfc/0008-vet-ghi-chuan-muc-mang-gate-digest.md) | Ba vết ghi chuẩn mực mang `gate_digest` trong `trace.v1` — phát lại kiểm tra. Ngăn chặn phát lại vết ghi trên gate đã đổi ngữ nghĩa an toàn mà không phát hiện được | Chấp nhận, đã hiện thực | `fixtures/traces/`, `verify`, `replay` |
| [0009](../../rfc/0009-tieu-chi-so-numeric.md) | Tiêu chí `numeric`: `evaluate.type: numeric` trong `gate.v1`, nút so sánh số trong `NETR` và walker C; cho phép gate kiểm tra ngưỡng số liên tục (áp suất, nhiệt độ) thay vì chỉ enum `bool`/`level`/`choice` (TSK-W1-02, `TODOS.md` #30) | Chấp nhận (2026-10-01), đã hiện thực | `engine/constraints.py`, `NETR` v2, `ne_walker.c` |
| [0010](../../rfc/0010-pwm-trong-digital-out.md) | PWM (tần số, độ rộng xung) và kênh phản hồi trạng thái trong `digital.out` (TSK-W1-01) | Chấp nhận (2026-10-01); hiện thực phần host (nhánh `feat/pwm`); còn `esp32s3` | `hal/pwm.py` |
| [0011](../../rfc/0011-nguyen-thuy-motion.md) | Nguyên thủy `motion.*` (motor/servo), mở rộng phong bì an toàn vật lý, token thuê có hạn (Q-37) và trạng thái an toàn riêng cho từng cơ cấu khi mất liên lạc (Q-35) (TSK-W1-03) | Chấp nhận (2026-10-01); hiện thực phần host (nhánh `feat/motion`); còn `esp32s3` | `hal/motion_core.py` |
| [0012](../../rfc/0012-nguyen-thuy-vision-in.md) | Nguyên thủy `vision.in` với tham số phần cứng (`fps`, `modes[]`, enum `pixel_format`), quy tắc đối chiếu `[requires]` (RFC-0002 §9.1) và luật riêng tư của vết ghi (TSK-V1b-07) | Chấp nhận (2026-10-01); hiện thực phần host: mô hình, vết ghi, camera ảo, V4L2; còn golden suy luận và `esp32s3` | `perception/vision/`, `sim/vision/`, `hal/v4l2.py` |
| [0013](../../rfc/0013-nguyen-thuy-tuy-chon-va-nhieu-bo-tham-chieu.md) | Nguyên thủy mở rộng tuỳ chọn theo bo mạch; nhiều bo tham chiếu cho một target bậc 1 (TSK-I2a-07) | Chấp nhận (2026-10-01); hiện thực phần host; còn các ô `esp32s3` (TSK-I3a-01) | `hal/board.py` (`REFERENCE_BOARDS`, `SIM_MIRRORS`), `verify` |
| [0014](../../rfc/0014-du-kien-tu-tien-trinh-ngoai.md) | Dữ kiện số từ tiến trình ngoài: nguồn khai trong gate, danh tính nguồn ghi vào vết ghi, nguồn rớt ⇒ BLOCK (TSK-I6-07, Q-65) | Chấp nhận (2026-10-04); mã kéo lên I2c (TSK-I2c-09, Q-67) | chưa |
| [0015](../../rfc/0015-hop-dong-cho-nguoi-tich-hop.md) | Hợp đồng cho người tích hợp: Gated Tool Profile (`tool-call.v1`, `tool-result.v1`), khoá `schema` của `board.v1`, danh mục mã lỗi `NE*` (`error.v1`, `error-codes.v1`) (TSK-I6-05, Q-58, Q-63) | Chấp nhận, đã hiện thực | `schemas/` (bảy lược đồ) |
| RFC-0016 | Lõi an toàn dùng độc lập và Extension SDK: điểm cắm, mô hình tin cậy, bộ test tuân thủ (TSK-I2c-02, Q-67) | Đang thảo luận (bản nháp chờ chữ ký) | chưa |
| RFC-0017 | Nguồn gọi theo không gian tên (`bridge:<id>`) và danh tính client (TSK-I2c-03, Q-67) | Đang thảo luận (bản nháp chờ chữ ký) | chưa |
| RFC-0018 | Cơ cấu chấp hành từ xa và mức tự tắt (TSK-I2c-04, Q-67) | Đang thảo luận (bản nháp chờ chữ ký) | chưa |

### Các RFC dự kiến chưa cấp số (planned RFCs)

Mỗi RFC dưới đây giải quyết một điểm nghẽn kiến trúc cho các chặng mở rộng, được mở bởi một task cụ thể:

| RFC dự kiến | Năng lực và mục đích kiến trúc (Tại sao cần) | Task mở | Thuộc chặng |
|:---|:---|:---|:---|
| **RFC-node** | Đặc tả giao thức điều phối đa node trên wire (Zenoh-pico, Q-36), cấu trúc black channel, nhịp tim (heartbeat) kích hoạt an toàn khi đứt kết nối (Q-35), và hợp nhất vết ghi đa node trong `trace.v1` (Q-32) | TSK-W3-02 | I14 |
| **RFC-pin-extends** | Cho phép ghim kế thừa gate theo băm nội dung `@<ver>#sha256:…` trong `gate.v1`, nâng cấp `digests.lock` thành lockfile cho chuỗi kế thừa; chống tấn công thay thế gate trên Registry công cộng (`TODOS.md` #11, #15) | TSK-S3-21 (I2c, Q-67) | I2c |
| **RFC visual-evidence gate semantics** | Định nghĩa ngữ nghĩa gate riêng cho bằng chứng thị giác; tới khi có RFC này, thị giác vào gate qua dữ kiện do maker khai và ngưỡng khoá bằng tiêu chí `numeric` (Q-54, `neuroedge-design-phase2.md` §2.2); điều kiện tiên quyết cho gate đa phương thức | TSK-V3-04 | I17 |
| **RFC mobile-robot safety** | Khung an toàn cho robot di động: giới hạn tốc độ tối đa, vùng cấm di chuyển, chu kỳ gate thời gian thực 10–20 Hz, tích hợp luồng điều khiển ROS 2 / Nav2 (Q-34) và câu hỏi C6 từ người mua robot (Q-38, `TODOS.md` #40) | TSK-W4-07 | I14 |

## 7. Ra một quyết định kiến trúc mới

1. **Quyết định** được ghi ở PRD §15 với mã `Q-N` mới — nơi duy nhất.
2. Nếu nó đổi một thứ trong danh sách `CONTRIBUTING.md` §3 (lược đồ, ngữ nghĩa phân giải, vết ghi chuẩn
   mực, gate khoá, bố cục `NETR`) thì cần **RFC**: PR đầu chỉ chứa tệp RFC; PR sau dẫn số RFC.
3. Nếu nó có hệ quả kiến trúc, thêm một mục ADR vào trang này (bối cảnh, quyết định, hệ quả, cưỡng chế),
   dẫn mã `Q-N` — không chép lại nội dung quyết định.
4. Nếu nó đổi đồ thị phụ thuộc giữa các gói, sửa `ALLOWED` trong `python/tests/test_architecture_layers.py`
   và bảng ở [`03`](03-component-host-c4l3.md) §2 trong cùng thay đổi.
