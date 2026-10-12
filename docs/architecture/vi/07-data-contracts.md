# 07 · Hợp đồng dữ liệu

> **Phạm vi:** mọi định dạng tệp và định dạng đường truyền mà các thành phần trao cho nhau, cách chúng
> được đánh phiên bản, và cái nào đóng băng. **Nguồn:** `schemas/`, `python/neuroedge/engine/`,
> `models/providers/config.py`, `perception/providers/config.py`, `sim/session.py`, `actions/tools.py`,
> `testing/uart.py`, `docs/spec/tool_calling.md`, `docs/spec/simulation_coverage.md` §4, PRD Phụ lục B–C.

## 1. Bản đồ hợp đồng

| Hợp đồng | Dạng | Ai viết | Ai đọc | Kiểm bằng | Đóng băng | Trạng thái |
|:---|:---|:---|:---|:---|:---|:---:|
| **Gate** `gate.v1` | YAML | người viết gate | resolver | `schemas/gate.v1.json` + **phân giải** (`gate lint`) | có — RFC (`CONTRIBUTING.md` §3) | `done` |
| **Vết ghi** `trace.v1` | JSON | `EventLog`, `TraceRecorder`, UART | player, golden, `trace view` | `schemas/trace.v1.json` | vỏ: có; danh mục sự kiện: không | `done` |
| **Bo mạch** `board.v1` | TOML | OEM, đội lõi | build, HAL | `schemas/board.v1.json` | có | `done` |
| **Agent** `agent.toml` | TOML | người viết agent | build, phiên | từng bảng có parser riêng | không (quy phạm trong mã) | `done` |
| **Ngữ pháp** `commands.toml` | TOML | người viết agent | `CommandGrammar` | parser | không | `done` |
| **Tri thức** `knowledge.toml` | TOML | người viết agent | `KnowledgeBase` | parser | không | `done` |
| **Tool call** `tool-call.v1` | đối tượng / JSON | bộ điều phối, LLM, client MCP | `dispatch()` | `schemas/tool-call.v1.json` (phong bì, mô tả tool); `input_schema` sinh từ chữ ký | có — RFC-0015 | `done` |
| **Kết quả tool** `tool-result.v1` | JSON | `dispatch()` | LLM, client MCP (`outputSchema`) | `schemas/tool-result.v1.json` | có — RFC-0015 | `done` |
| **Lỗi** `error.v1` · **danh mục mã** `error-codes.v1` | JSON | `NeuroEdgeError.as_dict()` · tệp danh mục | Studio, trang `sim`, SDK người tích hợp | `schemas/error.v1.json`, `schemas/error-codes.v1.json` | có — RFC-0015 | `done` |
| **Cây thiết bị** `NETR` v1 | nhị phân | `binary_tree.encode` | walker C | `ne_tree_load` (magic, phiên bản, CRC, giới hạn) | có — RFC-0003 | `done` |
| **Dòng UART** | văn bản | firmware | `testing/uart.py`, script CI | parser, regex neo `^` | quy phạm ở `simulation_coverage.md` §4 | `done` |
| **Manifest** `manifest.v1` (`schemas/manifest.v1.json`, TSK-K3-03) | JSON | người đóng gói agent / gate | Gate Registry | JSON Schema | dự kiến có — → [`15`](15-target-architecture.md) §3.2 | `planned` |
| **Khung WebSocket Opus/JSON** (và SLIP trên UART nếu cần — PRD Phụ lục D.2) | nhị phân / JSON | firmware (`provider_client.c`, TSK-S5-06) | lớp provider / nhà cung cấp cloud | chưa định | quy phạm PRD Phụ lục D.2 — → [`15`](15-target-architecture.md) §2.3 | `planned` |
| **Dây black-channel và vết ghi đa node** (`metadata.nodes[]`, `data.node_id`, Q-32) | Zenoh-pico (mã hoá ý định chưa chọn) / JSON | Pi điều phối, node MCU | node MCU, TracePlayer | RFC-node; trường tuỳ chọn, không sửa `schemas/` (TSK-W3-04) | qua RFC — → [`15`](15-target-architecture.md) §4.3 | `planned` |
| **Bảng mở rộng `agent.toml` (`[lab]`, `[nodes]`)** | TOML | người viết agent | parser `agent.toml` | parser cấu hình (TSK-N1-02, RFC-node draft) | không — → [`15`](15-target-architecture.md) §4.2, §4.3 | `planned` |
| **Hợp đồng nhiệm vụ** `mission.v1` (`planned · Q-72`, I2d) | YAML hoặc TOML, chưa chọn | LLM worker (bản nháp), trình biên dịch nhiệm vụ | runtime | lược đồ + trình biên dịch (kiểm mâu thuẫn) | RFC dự kiến — §12.1 | `planned` |
| **NeuroEdge Blueprint** `blueprint.v1` (`planned · Q-72`, I2e) | gói + manifest | người bán, maker | `blueprint install`, Hub index | lược đồ + digest toàn gói | RFC dự kiến — §12.2 | `planned` |
| **Khai báo đích dữ liệu** (`planned · Q-72`, I2d) | trong `mission.v1` và cấu hình runtime | người dùng | cửa ra egress của runtime | runtime | RFC dự kiến — §12.3 | `planned` |
| **Sự kiện chat** và **bản ghi duyệt** (`planned · Q-72`, I2d) | JSON trong runtime, sự kiện `trace.v1` | adapter chat, runtime | runtime, `replay` | runtime | RFC dự kiến (nguồn `chat:<id>`) — §12.4 | `planned` |
| **`safe_state` trong `board.v1`** (`planned · Q-72`, I2d) | TOML | OEM, maker | build, HAL | `schemas/board.v1.json` | RFC dự kiến (an toàn có điều kiện) — §4 | `planned` |
| **Đoạn vết ghi** `trace.v1` (`planned · Q-72`, I2d) | JSON | runtime 24/7 | player, `replay` | `schemas/trace.v1.json` | RFC dự kiến — §7 | `planned` |

## 2. Gate — `gate.v1`

Một gate thật trong kho, cấp 2 của chuỗi ba cấp:

```yaml
schema:  neuroedge.gate/v1
name:    unlock_door
version: 1.2.0
extends: neuroedge://gates/hospitality/base-access@1.0.0

evaluate:
  room_matches:
    type: bool
    instructions: "Số phòng yêu cầu trùng khớp hoàn toàn với hồ sơ đặt phòng của khách"

allow_when:
  room_matches: true
  risk_level:   { lte: low }    # siết chặt: medium → low

on_block:
  action:  escalate
  to:      human_receptionist
  message: "Yêu cầu cần được nhân viên lễ tân xác nhận trực tiếp trước khi mở khóa."

budget:
  p95_latency_ms: 120
  fail:           closed
```

| Trường | Ràng buộc |
|:---|:---|
| `schema`, `name`, `version` | Luôn bắt buộc. `name` khớp `^[a-z0-9_-]+$`; `version` là SemVer 2.0 |
| `extends` | `neuroedge://gates/<đường-dẫn>@MAJOR.MINOR.PATCH`. Gate gốc (không `extends`) phải khai đủ `evaluate`, `allow_when`, `on_block`, `budget` (RFC-0001) |
| `evaluate.<tiêu chí>` | `type` ∈ `bool`, `level` (cần `levels`, xếp từ thấp tới cao), `choice` (cần `options`); `instructions` không rỗng |
| `arguments.<tham số>` (RFC-0005) | `type` ∈ `string`, `integer`, `number`, `boolean`; tuỳ chọn `minimum`, `maximum`, `enum`, `max_length` |
| `allow_when` | Mỗi mệnh đề một toán tử trên một tiêu chí đã khai; toán tử theo kiểu ở [`05`](05-code-gate-hal-c4l4.md) §2. Dạng chuỗi CEL bị từ chối hôm nay |
| `on_block.action` | `deny` · `escalate` (cần `to`) · `ask` (cần `message`, tuỳ chọn `confirms`) · `degrade` (cần `fallback_action`) |
| `budget` | `p95_latency_ms` ≥ 1; `fail` ∈ `closed` (mặc định) · `open` |

Lược đồ không đủ để kết luận một gate an toàn — nguyên tắc 2 là mệnh đề về **hai** tài liệu, còn JSON
Schema chỉ thấy một. Cổng kiểm là `neuroedge gate lint` (bất biến 1). Mọi thay đổi `allow_when` là thay
đổi phá vỡ, cần tăng số MAJOR.

## 3. Agent — `agent.toml`

Mỗi bảng có một parser riêng; code không từ chối bảng cấp cao lạ, nhưng các bảng nhà cung cấp từ chối
khoá lạ. Cú pháp dòng lệnh dùng các bảng này: `CHANGELOG.md` §2.3.

| Bảng | Parser | Khoá chính và luật |
|:---|:---|:---|
| `[agent]` | `compiler.load_agent_manifest` | `name`, `version` (bắt buộc; trên `esp32s3` phải là `MAJOR.MINOR.PATCH`), `language` (đúng 2 chữ thường) |
| `[requires]` | `compiler.check_capabilities` | Khoá là nguyên thủy dạng chấm (`"digital.out"`…); `pins`, `sensors`, `channels` (`analog.in`, mỗi kênh phải do bo mạch khai), `sample_rate_hz`, `aec`, `min_width`… phải có trên bo mạch |
| `[gates]` | `compiler.resolve_gates` | `khoá = "neuroedge://…"` hoặc đường dẫn tương đối; mỗi `@action(gate=…)` phải trỏ tới một khoá. Trên `esp32s3` khoá phải là định danh C |
| `[targets]` | `compiler` | `supported = [...]` |
| `[sim.facts]`, `[sim.slot_facts]` | `sim/session.py` | Dữ kiện cố định của phiên; dữ kiện lấy từ khe của câu lệnh |
| `[sim.sensors]`, `[sim.sensor_facts]` | `sim/session.py` | Số đọc giả lập; đổi số đọc thành dữ kiện: `equals`, `gte`/`lte`, hoặc `bands` (dải tăng dần, dải cuối là mức cao nhất của gate); quy tắc số cần đơn vị |
| `[system_two]` | `models/providers/config.py` | `provider` (`litellm` hoặc `python:…`), `model`, `api_key_env`, `api_base`, `timeout_s` (≤ 120), `max_tokens`, `temperature`, `options` |
| `[system_one]` | như trên | `provider` (`systemone` hoặc `python:…`), `model`, `criteria` (không rỗng, không có `call_source`), `threshold` [0,5; 1], `timeout_ms` (≤ 10 000, và cộng 50 ms dự phòng phải ≤ `p95` của gate) |
| `[stt]`, `[stt.fallback]`, `[tts]` | `perception/providers/config.py` | `provider` (`openai` hoặc `python:…`), `base_url`, `model`, `voice` (TTS), `language` (STT), `timeout_s`, `api_key_env`; `[stt]` cần `audio.in`, `[tts]` cần `audio.out` |
| `[wake_word]` | như trên | `provider` (`openwakeword` hoặc `python:…`), ba tệp mô hình `model`, `melspectrogram`, `embedding` (của người dùng), `word`, `threshold`; bị từ chối trên `esp32s3` |
| `[mcp]`, `[mcp.servers.<tên>]` | `mcp_host.load_mcp_config` | `max_rounds` (1–16); mỗi server: `command`, `tools` (danh sách cho phép, bắt buộc), `args`, `env`, `timeout_s` |
| `[lab]` | `lab/` (TSK-N1-02, planned) | Cờ `enabled`, mặc định tắt; tắt thì lab tool (tool tác động lẫn tool dựng, Q-71) không được đăng ký; không tool nào bật được cờ; `build --release` từ chối khi bật (TSK-N1-03) — → [`15`](15-target-architecture.md) §4.2 |
| `[nodes]` | RFC-node (đề xuất) | Cấu hình node MCU cho robot phân tầng; hình dạng chưa chốt (câu hỏi mở 3 của RFC-node nháp) — → [`15`](15-target-architecture.md) §4.3 |

**Luật chung của mọi bảng nhà cung cấp** (`models/providers/common.py`): trường có tên như khoá
(`api_key`, `token`, `secret`…) bị từ chối; giá trị trông như khoá bị từ chối và không bao giờ được in
lại; endpoint không được mang thông tin đăng nhập, query hay fragment; `http://` tới máy khác mà có khoá
bị từ chối, và với `[system_one]` thì `http://` tới máy khác bị từ chối trong mọi trường hợp.

## 4. Bo mạch — `board.v1`

| Phần | Nội dung |
|:---|:---|
| `[board]` | `id`, `target` (`sim` · `linux` · `esp32s3`), `mcu`, `name` |
| `[capabilities.audio_in]` | `channels`, `sample_rate_hz`, `aec`, `vad` |
| `[capabilities.audio_out]` | `channels`, `sample_rate_hz` |
| `[capabilities.digital_out]` | `pins` (tên logic), `backend` |
| `[capabilities.sensor_read]` | `sensors` |
| `[capabilities.display]` | `width`, `height`, `color` |

Năm nguyên thủy lõi là tập đóng cho v1.x (FR-HAL-01); nguyên thủy mới chỉ qua RFC, và bốn gói mở rộng tuỳ chọn theo bo mạch (FR-HAL-08, Q-53) vào v1.0 ở I2a và I3a: RFC-0007 (`digital.in`, I2C chỉ đọc, `analog.in`), RFC-0009 (tiêu chí `numeric`), RFC-0010 (PWM), RFC-0011 (`motion.*`), RFC-0012 (`vision.in`), RFC-0013 (tuỳ chọn theo bo mạch). Hôm nay có đúng ba profile bậc 1 (Q-53 thêm `sim-rpi5` và một bo ESP32-S3 có camera): `sim-default` (sao đúng Box-3, không
bao giờ giàu hơn — bất biến 7), `linux-rpi5` (`aec = false` tới khi đo đạt), `esp32s3-box-3`. Mã ứng dụng
chỉ dùng **tên** chân; số GPIO thuộc về HAL.

**`safe_state` đối xứng (`planned · Q-72`, I2d, chờ RFC an toàn có điều kiện).** Hôm nay `safe_state`
chỉ có ở kênh `motion.*` (`stop` hoặc `hold`, RFC-0011, `hal/board.py`). Theo [Q-72](../../../roadmap/neuroedge-prd.md#15-sổ-quyết-định) mọi cơ cấu chấp
hành sẽ có `safe_state` khai trong `board.v1`, mặc định `off`; thời lượng, `max_continuous_ms`, lease,
mức L0–L3 (RFC-0018) và miễn gate của Q-62 đều nói về "trở về `safe_state`", còn hướng *rời*
`safe_state` là hướng bị gate và giới hạn. `safe_state` khác `off` chỉ được khai ở đây — không ở hợp
đồng nhiệm vụ, gate hay NeuroEdge Blueprint — và `safe_state: on` hiện thực bằng đấu dây mặc định bật
(rơ-le thường đóng) khai làm khoá liên động phần cứng. Profile hiện có (`off`; `motion.*` `stop`/`hold`)
giữ nguyên hành vi. Điều kiện trước: `TODOS.md` #58 (bộ đọc cũ bỏ qua khoá lạ trong `board.v1`) phải
sửa trước, để một khoá an toàn mới không bị lặng lẽ bỏ qua.

## 5. Ngữ pháp và tri thức

```toml
# commands.toml
[grammar]
version   = 1
threshold = 0.80

[[command]]
intent    = "unlock"
patterns  = ["mở cửa phòng {room}", "mở cửa"]
tool      = "unlock_door"
arguments = { guest_id = "room" }
```

Mỗi lệnh làm đúng một việc: gọi một `tool`, nói một câu cố định (`say`), hoặc giao cho System 2 (`ask`,
kèm `offline_say`). Khớp: chuẩn hoá (NFC, chữ thường, bỏ dấu câu, giữ dấu tiếng Việt), khớp mẫu chính
xác được 1,0, còn lại dùng tỉ lệ `difflib` so với `threshold`. `knowledge.toml` là các mục `questions` →
`answer`, trở thành lệnh `ask = "knowledge"`; vết ghi chỉ lưu `id` và điểm của mục được truy xuất.

## 6. Tool call và kết quả

Hình dạng nằm ở `schemas/tool-call.v1.json` (phong bì `ToolCall { id, name, arguments, source }`, `source` ∈ năm nguồn; mô tả tool) và `schemas/tool-result.v1.json` (`ToolResult`, `status` ∈ ALLOW · BLOCK · REJECTED); không chép lại ở đây.

| `status` | Nghĩa | Chân | MCP `isError` |
|:---|:---|:---|:---|
| `ALLOW` | Gate cho phép, thân hàm đã chạy | có thể đổi | false |
| `BLOCK` | Gate chặn (mọi `on_block`) | không đổi, trừ chân của fallback `degrade` nếu gate riêng của nó cho | false |
| `REJECTED` | Công cụ lạ hoặc tham số sai; không có phán quyết | không đổi | true |

`id` rỗng được gán `call_1`, `call_2`… theo phiên. `source` do runtime gán theo kết nối, không do bên
gọi khai. Bên đọc kết quả không rẽ nhánh theo `reason` (chuỗi mở): `status` quyết định. Quy phạm
đầy đủ: [`docs/spec/tool_calling.md`](../../spec/tool_calling.md).

## 7. Vết ghi — `trace.v1`

```json
{ "$schema": "https://schema.neuroedge.dev/trace/v1.json",
  "metadata": { "session_id": "sess_…", "timestamp_utc": "…", "target": "sim",
                "board_id": "sim-default", "agent_version": "home-voice@0.1.0" },
  "events": [ { "offset_ms": 0, "type": "text_input", "data": { "text": "bật đèn" } } ] }
```

Vỏ đóng băng: `metadata` bắt buộc năm trường (và nhận thêm trường khác), mỗi sự kiện có đúng
`offset_ms`, `type`, `data`. `type` là **chuỗi tự do**, nên thêm một loại sự kiện không cần RFC. NaN và
vô cực bị từ chối khi đọc và được ghi thành chuỗi.

Sự kiện theo vai trò trong phát lại:

| Vai trò | Sự kiện | Khi phát lại |
|:---|:---|:---|
| **Đầu vào** | `text_input`, `audio_in_*`, `wake_word_detected`, `stt_result`, `stt_unavailable`, `sensor_read`, `sensor_set`, `sensor_unavailable`, `intent_extracted` | đưa vào lại |
| **Quyết định** | `gate_evaluation_begin`, `gate_facts`, `gate_evaluation_result`, `argument_out_of_range`, `actuator_command`, `actuator_aborted`, `actuator_command_rejected` | tính lại và so với golden |
| **Điều phối** | `tool_call`, `tool_call_rejected`, `mcp_auth_refused`, `tool_confirm_*`, `action_requested`, `fallback_skipped`, `voice_state_changed`, `voice_reprompt`, `voice_late_result_dropped`, `stt_fallback` | ghi lại, không so |
| **Đầu ra** | `tts_stream_start`, `tts_stream_end`, `tts_unavailable`, `display_frame` (chỉ digest), `knowledge_retrieved` | không so |
| **Đo đạc** | `system_one_call`, `system_one_fallback`, `system_two_call`, `system_two_unavailable`, `circuit_breaker`, `mcp_tool_result`, `turn_latency`, `session_summary` | bỏ qua |
| **Chỉ từ thiết bị** | `device_info`, `trace_end` | khung phiên UART |

`session_summary` không bao giờ được ghi trong phiên: `EventLog.to_trace()` tính và nối nó khi xuất.
Mặc định, vết ghi băm `text`, `utterance`, `transcript` tại nguồn và mang `metadata.anonymized = true`;
`--raw` giữ nguyên văn, vết ghi đó mang `metadata.anonymized = false` (NFR-PRIV-03). Ba vết ghi chuẩn mực
(`fixtures/traces/happy-path.json`, `unverified_attempt.json`, `network_offline.json`) đóng băng bằng
RFC; RFC-0008 thêm `gate_digest` — digest của gate đã quyết từng phán quyết — vào mỗi
`gate_evaluation_begin` của chúng.

**Đoạn vết ghi của runtime 24/7 (`planned · Q-72`, I2d, chờ RFC `trace.v1`).** Một phiên hôm nay là
một tiến trình lệnh và ghi một tệp khi đóng. Runtime chạy nhiều tháng sẽ ghi một **chuỗi đoạn** theo thời
gian (mỗi ngày hoặc khi vượt cỡ): mỗi đoạn mang trạng thái đầu đoạn (gate digest, sổ token, bộ đếm phong
bì, lease đang chạy) và digest của đoạn trước. Bất biến "một phiên một vết ghi" đọc lại thành "một phiên
một chuỗi vết ghi, mỗi đoạn replay được"; đoạn thiếu lộ ra vì chuỗi digest đứt. Ghi nối tiếp, flush theo
thời gian (khoảng 10 giây, khai được) và ngay khi có phán quyết chặn hay lời duyệt; mất điện mất tối đa
phần đuôi sự kiện thường, `replay` báo đoạn cụt. Hạn giữ và cỡ: [PRD §9](../../../roadmap/neuroedge-prd.md#9-yêu-cầu-phi-chức-năng) Đổi vỏ vết ghi
chuẩn mực là thay đổi cần RFC (`CONTRIBUTING.md` §3).

## 8. Định dạng trên UART

```text
NE1 {"offset_ms":0,"type":"device_info","data":{"board_id":"esp32s3-box-3","agent_version":"home-voice@0.1.0","device_id":"qemu","boot_id":"9f2c01aa"}}
NE1 {"offset_ms":3,"type":"gate_evaluation_begin","data":{"gate":"light_on@1.0.0","gate_digest":"sha256:4cc8…"}}
NE1 {"offset_ms":9,"type":"gate_evaluation_result","data":{"verdict":"ALLOW","evaluations":{"call_source":"local_grammar"}}}
NE1 {"offset_ms":57,"type":"trace_end","data":{"events":4}}
NE_SELFTEST PASS walker=26 token=11
NE_TRACE DONE sessions=4
```

- Dòng `NE1 ` ở cột 0, tiếp theo là một đối tượng JSON với **đúng** ba khoá; ≤ 512 byte kể cả tiền tố.
  Dòng không vừa bị bỏ nguyên dòng nhưng vẫn được đếm.
- Mỗi phiên mở bằng `device_info` ở offset 0 và đóng bằng `trace_end {events: N}`; N đếm mọi dòng của
  phiên. Host từ chối (`NE4001`, chỉ ra `nguồn:dòng`) dòng không phải JSON, khoá thừa, sự kiện trước
  `device_info`, khởi động lại giữa phiên, đếm lệch, phiên chưa đóng.
- Các dòng khác: `NE_SELFTEST PASS|FAIL`, `NE_TRACE DONE`, `NEUROEDGE_HEAP_JSON {…}`,
  `NEUROEDGE_MEMORY_JSON {…}`, và `NE_OTA <sự kiện> …` — danh sách và nghĩa ở
  [`docs/user/nap-firmware.md`](../../user/nap-firmware.md) §6.4; định dạng từng dòng do
  `components/ne_ota/src/ne_ota_policy.c` định nghĩa.

## 9. Corpus khép kín hai chiều

Mỗi tệp có đúng một mục đáp án và mỗi mục có đúng một tệp; test cưỡng chế cả hai chiều.

| Corpus | Tệp | Đáp án |
|:---|:---|:---|
| Gate phản chứng | `fixtures/gates/invalid/*.yaml` (và `valid/`, `registry/` phải phân giải) | `fixtures/gates/expected_errors.yaml`: lớp lỗi, mã, nguyên tắc, chuỗi con của nơi và lý do |
| Vết ghi phản chứng | `fixtures/traces/invalid/*.json` | `fixtures/traces/expected_errors.yaml` |
| Tool call | `fixtures/tool_calls/{valid,invalid}/*.yaml` | `fixtures/tool_calls/expected_results.yaml`: trạng thái, lệnh chân, lý do… |
| Hợp đồng người tích hợp | `fixtures/contracts/{tool-call,tool-result,error}/{valid,invalid}/*.json` | `fixtures/contracts/expected_errors.yaml`: lược đồ (`against`) của mỗi tệp; tệp `invalid/` kèm lỗi (`keyword`, `path`, chuỗi con của thông điệp) |
| Máy trạng thái thoại | `fixtures/compliance/voice/*.json` | `fixtures/compliance/voice/expected_results.yaml`: danh sách sự kiện đầy đủ, đúng offset |
| Bảng sự thật cây | `fixtures/decision_trees/*.truth.json` | chính tệp đó; walker C phải khớp mọi dòng |

## 10. Phiên bản, định danh, digest

| Đối tượng | Quy ước |
|:---|:---|
| Agent | `<tên>@<semver>` |
| Tệp gate | `<tên>@<semver>.yaml` |
| Gate trong registry | `neuroedge://gates/<nhóm>/<tên>@<semver>` → `<gates>/<nhóm>/<tên>@<semver>.yaml` |
| Phiên | `sess_<hex>` |
| Lược đồ công khai | `https://schema.neuroedge.dev/<loại>/v<n>.json` (phục vụ từ I6) |
| Digest | `"sha256:" + SHA-256(JCS RFC 8785)` |

**Đóng băng nghĩa là** đổi cần RFC và CI cưỡng chế: bảy lược đồ (tập tệp, `$id`, siêu lược đồ hợp lệ);
gate trong `digests.lock`; ba vết ghi chuẩn mực; bố cục `NETR` v1. Không đóng băng: cây JSON nội bộ,
danh mục sự kiện vết ghi.

## 11. Mã lỗi

Mọi lỗi có ba phần: **ở đâu · vì sao · cách xử lý** (FR-DX-04). Họ mã (`schemas/error-codes.v1.json` là nguồn của cấu trúc: mã, lớp, cha, trạng thái; PRD Phụ lục B giữ lời):

| Họ | Nghĩa | Ví dụ |
|:---|:---|:---|
| `NE1xxx` | Hợp đồng hành động lúc chạy | `NE1001` gọi ngoài `c.do()`, token sai · `NE1002` token dùng lại, hết hạn |
| `NE2xxx` | Gate lúc build, lint, phân giải | `NE2001` không tìm thấy · `NE2002` sai lược đồ hoặc giới hạn · `NE2003` vi phạm kế thừa |
| `NE3xxx` | Build | `NE3001` bo mạch thiếu năng lực · `NE3002` `agent.toml` sai · `NE3003` gom mọi vấn đề, không ghi gì |
| `NE4xxx` | Vết ghi, phát lại, verify | `NE4001` vết ghi hoặc khung UART sai · `NE4002` hồi quy an toàn · `NE4003` không phát lại được hoặc firmware cũ · `NE4004` quét được 0 artifact |
| `NE5xxx` | Nhận thức | `NE5001` ngữ pháp, tri thức hoặc fallback thiếu hay sai |

Chặn vì quá hạn hay mất nguồn dữ kiện **không phải lỗi**: đó là một phán quyết `BLOCK` với
`budget_exceeded` hoặc `gate_unreachable`.

## 12. Hợp đồng quy hoạch theo Q-72 (`planned · Q-72`)

Chưa có lược đồ hay mã nào trong mục này. Thiết kế đích theo [Q-72](../../../roadmap/neuroedge-prd.md#15-sổ-quyết-định); mỗi hợp đồng là một **RFC dự kiến**
(chưa cấp số, danh sách ở [PRD §15](../../../roadmap/neuroedge-prd.md#15-sổ-quyết-định)), vì đưa một lược đồ mới vào `schemas/` hay đổi `trace.v1`,
`board.v1` là thay đổi cần RFC (`CONTRIBUTING.md` §3).

### 12.1 Hợp đồng nhiệm vụ — `mission.v1` (I2d)

Đơn vị luật cho một chuỗi hành động trên nhiều thiết bị: được và cấm, tần suất, khung giờ, nghĩa vụ
(chỉ dạng watchdog có cận), luồng dữ liệu (§12.3), khi hỏng, hết hạn, và `llm_budget` (trần chi phí LLM).
Trình biên dịch nhiệm vụ hạ mỗi điều khoản xuống tầng thấp nhất cưỡng chế được — phản xạ (MCU có
`ne_gate`), kỹ năng (host), suy nghĩ (LLM) — từ chối hợp đồng mâu thuẫn và chỉ rõ chỗ đụng, rồi sinh
**bản duyệt ≤ 5 dòng** tất định từ diff có cấu trúc. Gate vẫn là hàm thuần; hợp đồng nhiệm vụ không mang
`safe_state` khác `off` (§4). Điều khoản khung giờ đọc dữ kiện giờ tường; dữ kiện đó mang `unsynced` khi
máy chưa đồng bộ giờ và khi đó được coi là thiếu dữ kiện. Luồng: [`06`](06-runtime-flows.md) §11.1.

### 12.2 NeuroEdge Blueprint — `blueprint.v1` (I2e), so với `manifest.v1`

| | `blueprint.v1` (MVP, I2e) | `manifest.v1` (H2, TSK-K3-03) |
|:---|:---|:---|
| Đóng gói | kit (BOM liên kết), firmware, hợp đồng nhiệm vụ mẫu, bộ phát hiện, vết ghi làm bằng chứng | agent hoặc gate |
| Phân phối | URL (git hoặc HTTPS) + digest; Hub là **kho index tĩnh** liệt kê URL, digest, bằng chứng (kiểu index plugin I2c) | OCI Registry (ORAS) |
| Digest | phủ **toàn gói**, kiểm khi cài; lệch ⇒ từ chối | ghim digest artifact |
| Bằng chứng | vết ghi ghi rõ "chưa ký" (ký hoãn, `TODOS.md` #1) | ký ở Registry |
| Máy chủ NeuroEdge vận hành | không (index là kho git tĩnh) | có |

Khi Hub thu tiền cho người bán, NeuroEdge Blueprint chuyển sang OCI Registry của chân trời 2 — quan hệ
giữa hai manifest chốt trong RFC `blueprint.v1`. NeuroEdge Blueprint chỉ khai báo, không mang mã chạy
trong runtime. Nó khác Home Assistant Blueprint (mẫu automation) và có thể mang kèm một HA blueprint.

### 12.3 Khai báo đích dữ liệu (I2d)

Luật luồng dữ liệu nhằm **chống rò rỉ** (hack, prompt injection, đánh cắp), không hạn chế luồng người
dùng tự dựng. Mỗi đích người dùng khai — nhà cung cấp LLM, kênh chat, relay, webhook — kèm trường được
phép gửi tới nó, kể cả ảnh tới LLM nếu người dùng cho phép. Runtime quyết định LLM worker *thấy* gì và
chỉ gửi ra đích đã khai; gửi tới đích không khai bị chặn và ghi vết. Luật nội dung (ví dụ "ảnh không rời
nhà") là tuỳ chọn người dùng bật trong hợp đồng, không phải mặc định. Cưỡng chế ở mức mạng:
[PRD §9](../../../roadmap/neuroedge-prd.md#9-yêu-cầu-phi-chức-năng)

### 12.4 Sự kiện chat và bản ghi duyệt (I2d)

- **Sự kiện chat:** tin vào và ra của adapter chat, ghi vào vết ghi với id chat (đã ghép hay chưa, có phải
  nhóm), không bao giờ mang khoá hay token bot. Nội dung tin vào là dữ liệu không tin cậy.
- **Bản ghi duyệt:** `{id, nonce, hạn, digest thay đổi, bản duyệt ≤ 5 dòng}`. Hạn tính bằng đồng hồ đơn
  điệu. Trả lời phải nhắm đúng `id`; runtime kiểm người gửi đã ghép đôi, không phải nhóm, nonce chưa
  dùng, còn hạn, digest khớp, rồi mới đưa vào đường xác nhận với nguồn `chat:<id>` (cùng văn phạm nguồn
  theo không gian tên của RFC-0017). Mỗi yêu cầu, lời duyệt và lời từ chối ghi vào `trace.v1` và flush
  ngay. Luồng: [`06`](06-runtime-flows.md) §11.4.
