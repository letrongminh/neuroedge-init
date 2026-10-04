# RFC-0016: Lõi an toàn dùng độc lập và Extension SDK — điểm cắm, mô hình tin cậy, bộ test tuân thủ

| | |
|:---|:---|
| **Mã RFC** | 0016 |
| **Tiêu đề** | Lõi an toàn dùng độc lập (`neuroedge.guard`) và Extension SDK (`neuroedge.sdk`): sáu loại điểm cắm qua Python entry points, kích hoạt tường minh và nguồn gốc ghi vào vết ghi, cam kết ổn định riêng, tài sản ngoài gói (`--board <đường dẫn>`, `--template`, nhiều gốc registry gate), bộ test tuân thủ theo loại — TSK-I2c-02 |
| **Hợp đồng bị ảnh hưởng** | Hai mô-đun công khai mới `neuroedge.guard`, `neuroedge.sdk` *(`docs/spec/python_api.md` §1 thêm khái niệm "công khai theo vị trí"; §2, §6)* · khối `[plugins]` của `agent.toml` và tệp mới `guard.toml` với `[guard]`, `[registry]`, `[tools]`, `[plugins]` *(ngoài `schemas/`; kiểm ở `neuroedge build` và lúc nạp, như `[external]` của RFC-0014; `guard.toml` cũng nhận `[external]` và `[actuators]` của RFC-0014, RFC-0018)* · hợp đồng CLI *(lệnh mới `plugin list`, `plugin doctor`, `conformance`, `bridge run`; cờ `--board`, `--template` nhận tham chiếu, `--registry` lặp được — §4)* · chỗ tìm tệp của `GateRegistry` *(`engine/gate_resolver.py`: nhiều gốc; hợp nhất và kế thừa không đổi — §3f)* · `docs/spec/threat_model.md` *(mục mới §2d)* · đặc tả mới `docs/spec/extension_sdk.md` · **không** đụng `schemas/`, `gate.v1`, `trace.v1`, `board.v1`, `NETR`, `digests.lock`, ba vết ghi chuẩn mực; **không** mã lỗi mới |
| **Yêu cầu PRD liên quan** | FR-EXT-01 → FR-EXT-05, FR-EXT-09, NFR-SEC-10 *(FR-EXT-08 chỉ ở chỗ móc, §3g)* · FR-MDL-08, FR-GOV-03, A3, A13 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-10-04 |
| **Trạng thái** | ✅ Đã chấp thuận (2026-10-04) — kỹ thuật trưởng ký trên PR #99; quyết định cho câu hỏi mở ở §9 (Q-68) |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (đặt một cam kết công khai mới cho bên ngoài; mở đường cho mã của bên thứ ba vào tiến trình giữ cổng an toàn; sửa nơi tìm gate của `engine/gate_resolver.py`) |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3. RFC này **không** sửa `schemas/*.json`, ba vết ghi chuẩn mực, `digests.lock` hay `NETR`; nó chạm `engine/gate_resolver.py` (§3: chỗ tìm tệp của `GateRegistry`, hợp nhất và
> kế thừa nguyên vẹn — §3f) và đặt cam kết ổn định của `neuroedge.sdk` (D7), nên đi qua RFC như RFC-0013. Task: **TSK-I2c-02**; hiện thực: TSK-I2c-07, -08, -11, -12, -13, -18. Quyết định nền: `neuroedge-prd.md` §15
> **Q-67** — D1 (increment I2c), D4 (phần bo ngoài kho; phần enum target ở [RFC-0002](0002-mo-rong-target-va-nguyen-thuy-thi-giac.md)), D7 (`neuroedge.sdk`), D8 (giấy phép: runtime PolyForm NC, plugin theo tác giả).
> Khớp: [RFC-0014](0014-du-kien-tu-tien-trinh-ngoai.md) (dữ kiện ngoài), [RFC-0015](0015-hop-dong-cho-nguoi-tich-hop.md) (§3a `request`, §5), [RFC-0013](0013-nguyen-thuy-tuy-chon-va-nhieu-bo-tham-chieu.md) (bo tham chiếu),
> [RFC-0017](0017-nguon-goi-theo-khong-gian-ten.md) "Nguồn gọi theo không gian tên và danh tính client", [RFC-0018](0018-co-cau-chap-hanh-tu-xa.md) "Cơ cấu chấp hành từ xa và mức tự tắt" (soạn song song với RFC này; phần của mỗi RFC lấy RFC đó làm nguồn, ở đây chỉ dẫn).
> Mọi khẳng định về mã đã đối chiếu với kho tại `7a43d93`; điều chưa kiểm ghi "chưa kiểm".

## 1. Vấn đề

1. **Lõi chỉ dùng được qua mô hình agent.** Đường từ lời gọi tới chân là `dispatch(conversation, tools, call)` (`python/neuroedge/actions/tools.py:327`). `ToolSet` dựng từ `ActionSpec`, mà `ActionSpec` là hàm Python có `@action` (`actions/spec.py`), và `check_arguments` lấy
   lược đồ tham số **từ chữ ký hàm** (`tools.py:75`, `:135`). Cách có sẵn để lắp engine + sổ token + phong bì + vết ghi là `SimSession.load`, đòi `agent.toml` và `commands.toml` (`sim/session.py:864–871`). Một proxy MCP, một cầu nối Muse, một node ROS không có `@action` và không cần ngữ pháp lệnh.
2. **Không có điểm cắm.** `python/pyproject.toml` chỉ có `[project.scripts]` (`:111`), không entry point. Backend HAL chọn bằng `if target == "linux"` (`sim/session.py:917`, `:938`) và `SESSION_TARGETS` (`:621`). `--board` chỉ nhận id: `load_board_by_id` (`hal/board.py:738`) tra `boards_dir()`;
   `load_board(path)` có (`:733`) mà không cờ CLI nào dùng. `TEMPLATES` (`templates/__init__.py:31`) và `KINDS` (`templates/add.py:36`) là tuple cố định; `GateRegistry` chỉ có một gốc (`engine/gate_resolver.py:110`). Chỗ duy nhất đã mở là provider mô hình: `provider = "python:pkg.mod:factory"` (`models/providers/common.py:36`, `:324`; FR-MDL-08).
3. **Mở bằng đường `python:` thì mất bảo đảm cấu trúc.** `Conversation(engine, hal=...)` nhận HAL bất kỳ (`actions/conversation.py:72`, `hal: Any`) và `neuroedge.__all__` có `SimHAL`, `LinuxHAL`, `HardwareAbstractionLayer`, `digital`, `motion` (`__init__.py:63`): một adapter kiểu `python:` được trao nguyên HAL.
   Không có chỗ nào để nói "bridge không bao giờ chạm chân", và không có gì để bộ kiểm tuân thủ nhắm vào.
4. **Không có cam kết cho tác giả bên ngoài.** `python_api.md` §1 chỉ hứa tên trong `__all__`; mô-đun con "không được hứa"; trong `0.x`, MINOR đóng vai MAJOR (§3). Một plugin không có gì bảo đảm nó còn chạy ở bản sau.
5. **Thân `@action` gọi SDK ngoài (HTTP tới Home Assistant…) không có phong bì và không tự tắt.** Phần cơ cấu từ xa thuộc RFC-0018; RFC này chỉ chừa chỗ cắm (§3c).

## 2. Vì sao cơ chế hiện tại không giải quyết được

- `__all__` hứa theo **tên**, không có khái niệm "bề mặt cho plugin" với phiên bản riêng (`python_api.md` §1, §3). D7 đòi một mô-đun có cam kết khác `__all__`.
- Adapter `python:` là một hàm nhà máy trả đối tượng: không giao thức, không phiên bản, không nhóm. `load_adapter` chỉ `import_module` (`common.py:324`); không `plugin list`, không đối chiếu phiên bản, không nguồn gốc vào vết ghi.
- **`dispatch` không an toàn cho nhiều bên gọi đồng thời trên một `Conversation`.** Nó đặt `conversation.facts` tạm rồi khôi phục (`tools.py:351–356`). Đã chạy thử trên `fixtures/agents/home-voice`: hai `dispatch` đồng thời (`mcp` rồi `system_two`), mỗi `evaluate` thấy đúng
  `call_source` của mình, nhưng khi cả hai xong `conversation.facts["call_source"]` vẫn là `"mcp"` (lời gọi sau khôi phục ảnh chụp của lời gọi trước). `Conversation._do` còn đọc `self.facts` sau một `await` để ghi nguồn của câu hỏi `ask` (`conversation.py:195`; đường này **chưa chạy thử**).
  Một Guard phục vụ nhiều bridge phải xử lý điều này (§3b mục 5).
- Entry points: `importlib.metadata` là thư viện chuẩn, `requires-python >= 3.11` (`pyproject.toml:11`), không thêm phụ thuộc (`:36`). Đã chạy thử trên Python 3.13.6: liệt kê entry point **không import** gói nào; `Distribution.locate_file` trả đường dẫn không import; với bản cài editable
  (`direct_url.json` có `dir_info.editable`), `files` của chính `neuroedge` chỉ liệt kê tệp `.pth` và `dist-info`, **không** liệt kê mã nguồn (nên không băm được, §3d). Python 3.11 và 3.12: chưa kiểm.

## 3. Thay đổi đề xuất

### 3a. Phạm vi

| RFC này chốt | Dẫn sang, không làm ở đây |
|:---|:---|
| `neuroedge.guard` (§3b) · `neuroedge.sdk`: Protocol, bất biến cấu trúc, ổn định (§3c, §3e) · kích hoạt, tin cậy, nguồn gốc (§3d) · tài sản ngoài gói (§3f) · khung tuân thủ và danh sách phép kiểm (§3g) | Dây dữ kiện ngoài và bộ nhận: RFC-0014 (mã: TSK-I2c-09) · văn phạm `source`, id bridge, danh tính client: RFC-0017 (TSK-I2c-03, -10) · chữ ký hàm của `Actuator`, mức tự tắt L0–L3, khai báo `[actuators]`, vector tuân thủ actuator: RFC-0018 (TSK-I2c-04, -16) · enum target, `TARGET_TIERS`, `board validate`: RFC-0002 (TSK-I2c-05) · ghim `extends` bằng digest, gate từ git/OCI: TSK-S3-21 (`TODOS.md` #15) · `proxy mcp/http`, `guard init`: TSK-I2c-14, -15 · index, `plugin search/install`, huy hiệu: TSK-I2c-18 · ký plugin: I10 |

### 3b. `neuroedge.guard` — lõi dùng độc lập

Một chương trình bất kỳ (proxy MCP, cầu nối, node ROS) có gate → token → phong bì → vết ghi mà không cần `agent.toml`, `@action`, `SimSession`:

```python
from neuroedge.guard import Guard, Tool
from neuroedge.sdk import ToolRequest

guard = Guard.load("guard.toml")        # hoặc Guard(tools=[Tool(...)], gates=[...], board=None): không cần agent.toml
async with guard:                       # thoát ⇒ thả chân, như SimSession.close()
    ros = guard.dispatcher("ros_node")  # đăng ký id (văn phạm RFC-0017 §3a); nguồn luôn là "bridge:ros_node", không nêu khác được
    guard.set_fact("badge_ok", True)    # ngữ cảnh gate do chương trình chủ đặt, như `c.facts`
    outcome = await ros.dispatch(ToolRequest("unlock_door", {"duration_s": 5}))   # `request` của tool-call.v1 (RFC-0015 §3a): không có `source`
    outcome.status      # "ALLOW" | "BLOCK" | "REJECTED" — `ToolResult.status` (tools.py:248)
    outcome.content     # đúng `ToolResult.content()` (tools.py:256), hợp lệ theo tool-result.v1
    trace = guard.trace()   # trace.v1 đã thẩm định, như `SimSession.trace()` (sim/session.py:1793)
```

```toml
# guard.toml — tập con của agent.toml; khoá lạ và trường mang tên bí mật viết thẳng ⇒ từ chối, như [external] của RFC-0014 §3c
[guard]
name = "door-proxy"                 # ⇒ metadata.agent_version = "guard:door-proxy@<version>"
board = "esp32s3-box-3"             # <id> | đường dẫn .toml | pkg:… (§3f); vắng ⇒ không HAL, chỉ phán quyết
[registry]
roots = ["gates", "vendor/gates"]   # §3f
[tools.unlock_door]
gate = "neuroedge://gates/hospitality/unlock@1.0.0"
requires = ["digital.out:door_lock"]            # như @action(requires=…); cần board
drive = [{ pin = "door_lock", operation = "pulse", seconds_from = "duration_s" }]   # thân khai báo (cú pháp ở extension_sdk.md): Guard dựng thành `digital.out(pin).pulse(…)` dưới token
[tools.unlock_door.parameters.duration_s]       # tập con JSON Schema của tool-call.v1 §3a.2; tham số không khai ⇒ REJECTED (tools.py:150)
type = "integer"
default = 5
[plugins]
enable = ["neuroedge-muse"]         # §3d; cơ cấu từ xa: thêm [actuators.<tên>] của RFC-0018 §3b, cùng hàm kiểm với agent.toml
```

1. **Dựng từ lớp có sẵn; đúng một đường tới chân.** `Guard` dựng `ActionContractEngine` (`engine/gate.py:148`), `TokenLedger` (`actions/token.py:70`), HAL của bo cùng `SafetyEnvelope` qua `ensure_envelope` (`hal/__init__.py:737`), một `EventLog` (hoặc `TraceRecorder` truyền qua `events=`,
   `testing/recorder.py:70`) và một `Conversation` nội bộ (nhận `registry=` riêng, `conversation.py:81`, không đụng `REGISTRY` toàn cục của `@action`), rồi gọi **đúng** `dispatch()` (`tools.py:327`). Mỗi `Tool` thành một `ActionSpec` khai bằng dữ liệu. Không có đường mã thứ hai tới chân nên `threat_model.md` §1–§2b áp nguyên (§5).
   HAL của `linux` và `sim` dựng bằng cùng hàm với `SimSession` (TSK-I2c-07 tách khối `sim/session.py:917–942` thành một hàm dựng, `test_architecture_layers.py` cập nhật cùng lúc); `esp32s3` không có Guard Python (MCU dùng `ne_gate` + `NETR`, RFC-0003).
2. **ALLOW là phán quyết; nếu `Tool` có `run` thì là một lần chạy dưới token.** Sau ALLOW, `Conversation._do` cấp token một lần (`conversation.py:210`), chạy `run` trong `digital.grant` (`:221`), đóng token (`:233`); HAL kiểm `require_pin → phong bì → authorize → record` (`hal/__init__.py:231`).
   `run` là cách **duy nhất** để một `Tool` tới chân hay tới server thật: proxy chuyển lời gọi xuôi dòng **trong** `run`, nên không có đoạn "nếu ALLOW thì chuyển tiếp" nào để viết sai. Không có bo ⇒ không HAL: `Tool` có `requires` bị từ chối lúc nạp (`BoardCapabilityError`) và mọi token không có chân nên `authorize` từ chối lệnh chân (`token.py:148`).
   `run` là hàm Python (`Tool(run=…)`) hoặc, trong `guard.toml`, `drive` khai báo — không mã của tác giả; mọi `pin` trong `drive` phải nằm trong `requires` (chân không khai bị HAL từ chối như `@action`, `token.py:148`). Cơ cấu từ xa là chân `digital.out` có tên (RFC-0018 §3a): `requires = ["digital.out:porch_light"]` đi cùng đường `_admit`.
3. **Gate phân giải lúc nạp, không chỉ thẩm định lược đồ.** `Guard.load` gọi `register_gate` (`gate.py:170`) cho từng `Tool` — phân giải đủ (bất biến `CHANGELOG.md` §3.3 #1); gate không phân giải được ⇒ không nạp; gate vắng lúc chạy ⇒ `BLOCK gate_not_found` (`gate.py:206`). Không có công tắc fail-open.
4. **`source` và `facts`.** Người gọi **không** nêu `source`: chương trình chủ xin `guard.dispatcher(id)`; Guard đăng ký `id` (mẫu `[a-z][a-z0-9_]{0,31}`, trùng ⇒ lỗi, RFC-0017 §3a, §3b) và dựng `ToolCall` với `source = "bridge:<id>"` bên trong. Không có đường tới mặc định `test` (`tools.py:51`; F9 của RFC-0015) trừ `Guard(..., testing=True)`.
   `neuroedge proxy mcp|http` (lõi) giữ nguồn của client phía trước (`mcp`, `mcp:<nhãn>`) qua một đường nội bộ không công khai: câu hỏi RFC-0017 §9.2, RFC này chốt phía Guard (§9.9). `facts` do `set_fact` là ngữ cảnh người vận hành tin như `c.facts`; bị bỏ qua với tiêu chí có `external_source` (RFC-0014 §3c). Bridge **không** chạm `facts` (§3c).
5. **Tuần tự hoá.** Một Guard phục vụ nhiều bridge nên `dispatch` của mọi `Dispatcher` chạy dưới một khoá `asyncio`. Sửa gốc — truyền `call_source` theo từng lời gọi thay vì qua `conversation.facts` — là việc của TSK-I2c-10 (RFC-0017 đổi đúng chỗ chèn này, `tools.py:350`); khi đó có thể bỏ khoá.
6. **Vết ghi và replay.** `guard.trace()` = `EventLog.to_trace()` (`trace_sink.py:91`) + `validate_trace`; `metadata` mang `target`, `board_id`, `agent_version` và các khoá mở ở §3d, §3f (`trace.v1.json` có `metadata.additionalProperties: true` ⇒ lược đồ giữ nguyên); mỗi plugin lúc nạp còn phát một sự kiện `plugin_loaded` (§3d mục 4).
   `TracePlayer` hôm nay cần `agent.toml` (`testing/player.py:588`): TSK-I2c-07 thêm `TracePlayer(trace, guard="guard.toml")` dùng bảng `Tool`. Câu hỏi §9.3.
7. **Một Guard một tiến trình.** Sổ token trong bộ nhớ, gắn `PROCESS_INSTANCE_ID` (`token.py:37`); trên `linux`, tiến trình giám sát thả chân khi runtime chết hay treo như với `SimSession` (`threat_model.md` §2).

**Guard cố ý không làm:** không sandbox và không chặn mạng — nó canh con đường đi qua nó, không ngăn ai gọi thẳng đích (§5, rủi ro 3) · không `agent.toml`, `@action` bắt buộc, ngữ pháp lệnh, mô hình `SystemOne`/`SystemTwo`, thoại, UI hay MCP server (các lệnh `proxy` ở TSK-I2c-14, -15 xây trên Guard) ·
không công tắc fail-open; chỉ gate nạp từ tệp hay URI, không nhận `ResolvedGate` dựng tay · không đường xác nhận bằng người (`Conversation.confirm` cần người trên thiết bị, `tool_calling.md` §6): `on_block: ask` ở Guard hiện ra như chặn kèm câu hỏi trong `outcome.content` · không chống kẻ cùng tiến trình (`threat_model.md` §3) · không ký, không phân phối.

### 3c. `neuroedge.sdk` — sáu loại điểm cắm và bất biến cấu trúc

Mỗi loại là một nhóm entry point. Loại **mã** (bridge, fact source, actuator, exporter) có `typing.Protocol` trong `neuroedge.sdk`; loại **dữ liệu** (board, template) **không có Protocol** — không một dòng mã của tác giả chạy khi dùng chúng.

| Nhóm entry point | SDK | Plugin nhận | Plugin **không bao giờ** nhận hay làm | Hợp đồng |
|:---|:---|:---|:---|:---|
| `neuroedge.bridges` | `Bridge`: `serve(dispatcher, context)`, `probe()` | `Dispatcher` — một phương thức `dispatch(ToolRequest) -> Outcome`; lõi dựng `ToolCall` với `source = bridge:<tên entry point>` bên trong (RFC-0017 §3b). `BridgeContext(id, config)` | HAL, `Guard`, `Conversation`, sổ token, `GateResult`, tham số `facts`, `source` (kiểu `ToolRequest` không có trường nào trong số đó). `Outcome` là dữ liệu (`status`, `content`), không mang `ActionResult.value` | RFC-0016, RFC-0017 |
| `neuroedge.fact_sources` | `FactProducer`: `run(sink)`, `probe()` | `FactSink.push(facts: Mapping[str, int \| float], *, observed_age_ms: int = 0)`. Lõi đo `recv_ms`, gán `seq` và `connection`, đi qua **cùng bộ nhận** của RFC-0014 (§3d lớp 4, §3e, §3g; như nguồn ảo của `sim`, §3h) | `read_ms`, `age_ms`, `seq` (không có tham số); chuỗi, `bool`; tên chưa khai ở `[external.sources.<id>.facts.*]`; tiêu chí không có `external_source`; hỏi ngược engine. `run` kết thúc hay lỗi ⇒ lõi bỏ mọi dữ kiện của nguồn (RFC-0014 §3g, §3i) | RFC-0014, RFC-0016 |
| `neuroedge.actuators` | Protocol `Actuator` — chữ ký ở RFC-0018 §3c (`apply`, `safe_off`, `read_state`, `probe`, `safe_off_level`, `readback`, `tolerance_ms`, `command_timeout_ms`, `max_lease_ms`; factory `module:factory(config) -> Actuator`, không I/O khi dựng); `neuroedge.sdk` xuất lại, test ghim | Lõi dựng plugin từ khai báo `[actuators.<tên>] plugin = …`; chỉ HAL giữ tham chiếu và gọi nó, `apply` chỉ **sau** `_admit` (`hal/__init__.py:231`). `safe_off` đi đường về an toàn (`_auto_off` `:215`, `close()`), không qua phong bì và token (`threat_model.md` §1) | Lệnh không qua token và phong bì; nhận HAL, sổ token hay phong bì; bị gọi bởi ai ngoài HAL. Mức tự tắt L0–L3, "không tự tắt" bị cấm cho không hoàn tác, mất liên lạc: RFC-0018 | RFC-0016, RFC-0018 |
| `neuroedge.boards` | *dữ liệu*: giá trị entry point là `<gói>:<thư mục>` | Thư mục `<id>.toml` theo `board.v1`, đọc bằng `Distribution.locate_file` **không import gói**, qua `validate_board_document` (`board.py:666`) như tệp bất kỳ | Bậc, `mirrors` (`board.py:382`), tư cách bo tham chiếu; trùng id bo tham chiếu hay bo kèm kho (§3f) | RFC-0002, RFC-0016 |
| `neuroedge.templates` | *dữ liệu* | Thư mục `*.tmpl` chỉ có `{{name}}` (`templates/__init__.py:39`); `scaffold` chỉ `write_text` (`:123`) | Chạy mã lúc cài hay lúc `new`; mạng; ghi ngoài thư mục dự án; ghi đè tệp có sẵn; gate trùng URI gate chuẩn hay gate đã khoá | RFC-0016 |
| `neuroedge.exporters` | `Exporter`: `export(events)` | Bản sao sâu của sự kiện **đã ẩn danh** như vết ghi, qua hàng đợi có chặn, ngoài đường quyết định; lỗi cô lập (tiền lệ `_call_hook`, `gate.py:440`: "a hook can never change a verdict") | Tham chiếu tới phiên, `Guard` hay HAL; đổi phán quyết; văn bản gốc chưa ẩn danh; làm chậm quyết định | RFC-0016 |

- **Hình dạng.** Giá trị entry point của loại mã là `module:factory`, gọi một lần với `config` (một `Mapping`) và trả đối tượng đúng Protocol; loader kiểm cả chữ ký bằng `inspect.signature`, không chỉ `isinstance`. Tên entry point loại mã khớp `^[a-z][a-z0-9_]{0,31}$` (mẫu id của RFC-0017 §3a, cùng `source_id` của RFC-0014 §3c); loại dữ liệu khớp `NAME`
  của template (`templates/__init__.py:40`).
- **`Dispatcher`** do lõi dựng, mỗi bridge một cái, buộc vào id đã khoá; chuyển tới đường `dispatch()` (`tools.py:327`) của `Guard` hoặc của một phiên (`neuroedge bridge run <id> --guard|--agent`): cùng một đường như `mcp serve` (`python_api.md` §4). PRD FR-EXT-03 viết `dispatch(ToolCall)`; ở đây tham số là `ToolRequest` =
  `ToolCall` bỏ `source` (RFC-0015 §3a `request`). RFC-0017 §3b.3 cho phép API nhận `ToolCall` rồi dựng lại; chọn `ToolRequest` thì "bridge đặt `source` khác kênh" không biểu diễn được ngay ở kiểu dữ liệu.
- **`probe()`** là cửa vào trong bộ nhớ qua đường mã thật của plugin, để bộ kiểm (§3g) bơm tình huống (với actuator, `probe()` trả `DeviceDouble`, RFC-0018 §3c) — một lời gọi, một quan sát chụp trước `D` ms, đứt kết nối, mất liên lạc — mà không cần giao thức thật của hệ sinh thái. Thiếu `probe()` ⇒ phép kiểm động báo `unverifiable`, không huy hiệu.

### 3d. Kích hoạt, tin cậy, nguồn gốc

1. **Phát hiện không import.** `neuroedge plugin list` đọc `importlib.metadata.entry_points(group=…)`: tên, gói, phiên bản — **không import** gói nào (đã kiểm, §2).
2. **Loại mã chỉ nạp khi bật rõ.** `[plugins] enable = ["neuroedge-muse", "neuroedge-ros2==0.4.1"]` trong `agent.toml` hay `guard.toml`: tên **bản phân phối** (chuẩn hoá PEP 503), tuỳ chọn ghim phiên bản. Cài bằng `pip` không bật gì; phụ thuộc bắc cầu mang thêm entry point cũng không. **Không có cờ dòng lệnh nào bật plugin vào một phiên**
   (tiền lệ RFC-0014 §9 câu 9): việc bật nằm trong tệp được commit; riêng `conformance <bản phân phối>` (§3g) nạp đúng bản phân phối được gõ, chỉ để kiểm. Cấu hình của plugin ở `[plugins.config.<tên entry point>]`, cùng luật bí mật với `[external]` (chỉ tên biến môi trường `*_env`, dùng lại `SECRET`, `ENV_NAME` của `common.py:40`, `:38`). Chỗ khác nêu một plugin theo tên (`plugin = "home_assistant"` ở `[actuators.<tên>]` của RFC-0018, `plugin = …` ở `[external.sources.<id>]`) chỉ tra trong các bản phân phối **đã bật**; tên không có ở đó ⇒ `NE3002`.
   Loại **dữ liệu** không cần danh sách: không mã nào chạy; việc gõ tham chiếu `pkg:<bản phân phối>:<tên>` trên dòng lệnh (§3f) là hành vi tường minh.
3. **Hỏng ⇒ không khởi động, không bỏ qua lặng lẽ.** Không cài; không import được; nhà máy ném; trả đối tượng sai Protocol hay chữ ký; `sdk_requires` không tương thích (§3e); ghim phiên bản lệch; hai bản phân phối đã bật cùng cấp một tên entry point trong một nhóm (RFC-0017 §3b.2: id bridge trùng) ⇒ `AgentManifestError` (`NE3002`, ba phần, thoát mã 1)
   và **chưa gate lệnh nào**: mọi plugin phân giải xong trước lượt lượng giá đầu tiên. Tiền lệ: `load_adapter` và `call_adapter` cũng ném `NE3002` (`common.py:324`, `:359`). Khác server MCP ngoài không chạy được bị bỏ qua (`threat_model.md` §2b): ở đó chỉ bớt tool; plugin đổi thứ gì tới được gate hay HAL.
4. **Nguồn gốc.** Mỗi plugin đã bật, và mỗi tài sản ngoài gói đã dùng, in ra stderr lúc khởi động và ghi vào `metadata.plugins` của mọi vết ghi, đồng thời phát một sự kiện `plugin_loaded` (tên vào `tool_calling.md` §7 khi hiện thực; nối `bridge:<id>` ở `tool_call` với mã nào, RFC-0017 §3b): `{kind, name, distribution, version, files_sha256}`. `files_sha256` băm **byte trên đĩa** của các tệp `dist.files` thuộc gói của entry point (không lấy từ `RECORD`: chính nó sửa được).
   Bản cài editable (`direct_url.json`) không liệt kê mã nguồn ⇒ vắng `files_sha256`, `editable: true`; `plugin doctor` cảnh báo và huy hiệu từ chối (§3g).
5. **Plugin trong tiến trình là mã người vận hành tin.** Cùng vị thế với adapter `python:` và thân `@action`; `threat_model.md` §3 vẫn ngoài phạm vi. RFC này **không** tuyên bố chống plugin độc hại: không sandbox, plugin vẫn `import gpiod` hay mở `/dev/gpiochip` được. SDK cho bảo đảm **cấu trúc** (API không có handle), bộ kiểm bắt lỗi vô ý và lười, nguồn gốc làm lựa chọn kiểm toán được.
   Ký plugin: TSK-I2c-18 và I10, không ở đây. `plugin install` (TSK-I2c-18) nên chỉ nhận bánh xe dựng sẵn (`--only-binary :all:`) để không chạy mã dựng của tác giả — chưa kiểm hành vi.
6. **`neuroedge plugin doctor [--config=]`** nạp đúng tập đã bật theo các luật trên và in từng việc nó **không** kiểm được ("không kiểm được: …", không bao giờ "OK" suông); cho proxy, dòng "đích còn tới được mà không qua proxy" do TSK-I2c-14 cấp phép kiểm (§5, rủi ro 3).

### 3e. Ổn định của `neuroedge.sdk` và quan hệ với `__all__`

- **Phiên bản riêng:** `neuroedge.sdk.SDK_VERSION = (1, 0)`, độc lập với `__version__` (`__init__.py:9`, `0.1.0`). Plugin khai `sdk_requires = (1, 0)`: tương thích ⇔ cùng MAJOR và MINOR đã cài ≥ MINOR đòi hỏi. Là bộ số nguyên nên lõi không cần `packaging`. Loader import mô-đun **sau khi** người vận hành bật, đọc `sdk_requires`, rồi mới gọi nhà máy.
- **Chặt hơn `0.x` của gói (D7).** SemVer đầy đủ từ SDK 1.0, **không** theo cách đọc "MINOR đóng vai MAJOR" (`python_api.md` §3): chỉ bản MAJOR mới bỏ, đổi tên, đổi chữ ký hay đổi hành vi đã mô tả. Ngừng hỗ trợ: đánh dấu ở MINOR, còn chạy ít nhất hai bản MINOR của SDK (§5 của `python_api.md` đòi một; §9.4).
  Bề mặt ghim bằng test như `test_public_api.py` ghim `__all__` (§7). Lõi bên dưới `0.x` đổi tự do; mọi chỗ SDK chạm lõi nằm ở một mô-đun cầu nối, nên đổi lõi không làm gãy SDK.
- **Ngoại lệ an toàn, nói thẳng:** thay đổi đóng một đường tắt qua gate được phép ở MINOR/PATCH của SDK dù có plugin sống nhờ nó, ghi ở `CHANGELOG.md` (`python_api.md` §3 ý đầu, §5 mục 4; `CHANGELOG.md` §3.3 #2). Phép kiểm tuân thủ mới chỉ thêm ở MINOR nếu đóng một đường tắt an toàn; còn lại ở MAJOR.
- **Công khai theo vị trí.** `python_api.md` §1 thêm đúng hai mô-đun được hứa theo đường dẫn: `neuroedge.sdk` (cam kết trên) và `neuroedge.guard` (cùng mức `__all__`, §9.1). Mỗi mô-đun có `__all__` riêng. `neuroedge.__all__` **không đổi** (§9.2). SDK không re-export tên nào của `neuroedge.__all__` và không chứa tên HAL; plugin loại bridge, fact source, exporter
  chỉ được import `neuroedge.sdk` (bộ kiểm, §3g).
- **Giấy phép (D8).** `neuroedge.sdk` và `neuroedge.guard` nằm trong gói PolyForm NC (Q-45); plugin chỉ *nhập* chúng khi chạy cùng lõi, giấy phép của plugin là của tác giả (`LICENSING.md` thêm điều khoản, TSK-I2c-06). Corpus tuân thủ của plugin ở `fixtures/compliance/<nhóm>/` (§3g) — thuộc hàng Apache-2.0 sẵn có của `fixtures/compliance/`.

### 3f. Tài sản từ ngoài gói

Một cú pháp tham chiếu cho cả ba: **id/tên** như hôm nay · **đường dẫn** (có `/` hoặc `\`, hoặc đuôi `.toml`) · **`pkg:<bản phân phối>:<tên>`** (đọc bằng `Distribution.locate_file`, không import).

| Tài sản | Quy tắc |
|:---|:---|
| **Bo** `--board <tham chiếu>` | Một hàm `resolve_board(ref)` cạnh `load_board` (`board.py:733`) thay mọi chỗ gọi `load_board_by_id(board_id)` ở `engine/compiler.py:1659`, `sim/session.py:897`, `testing/player.py:611`, `cli/main.py`. Bo ngoài kho là **bo cộng đồng**: bo tham chiếu ⇔ id thuộc `REFERENCE_BOARDS` (`board.py:98`) **và** `source` là tệp kèm kho. Hồ sơ ngoài kho mượn id của bo tham chiếu hay của `boards/` ⇒ `BoardCapabilityError` (NE3001). `verify` chỉ duyệt `REFERENCE_BOARDS` (`cli/main.py:1123`) và không có `--board` (`test_cli_contract.py`), nên bo cộng đồng **không bao giờ** vào cột tương đương bậc 1. Bậc lấy từ **target** theo `TARGET_TIERS` (RFC-0002 §3b; chưa có mã, TSK-I2c-05), không từ hồ sơ. Mọi lệnh nhận `--board` (`build`, `run`, `mcp serve`, `record`, `replay`) và `board validate <đường dẫn>` in nhãn **"cộng đồng, tự chứng nhận"** ở dòng đầu; vết ghi mang `metadata.board_origin = "community"` và `metadata.board_digest` (sha256 JSON chuẩn tắc của tài liệu bo). `replay` với bo cộng đồng đòi `--board` và so digest: lệch hay thiếu ⇒ `ReplayError` (NE4003), cùng tinh thần RFC-0008. An toàn: `board validate` đã từ chối chân cơ cấu không có phong bì (`_check_actuator_envelopes`, `board.py:536`) và khoá capability lạ (`:392`); **con số** trong phong bì là lời của tác giả bo, `board validate` in bảng phong bì để người vận hành đọc |
| **Template** `--template <tham chiếu>` | Thêm dạng `git+<URL>@<sha>` (sha 40 hex đầy đủ; nhánh và tag bị từ chối vì không ghim; không chạy hook, không submodule; lệnh `git` cụ thể do TSK-I2c-08). Bố cục như `templates/<tên>/`; từ chối liên kết tượng trưng, đường dẫn tuyệt đối, `..`; không ghi đè tệp có sẵn; chỉ `write_text` — **không mã nào chạy**. In nguồn gốc (đường dẫn hoặc sha, hoặc bản phân phối + phiên bản) ra stderr |
| **Gốc registry gate** | `GateRegistry(root)` (`gate_resolver.py:110`) nhận một hay nhiều gốc; `--registry\|-r` lặp được (`gate lint`, `gate resolve`, `build`, …) và `[registry] roots` ở `guard.toml`; mỗi gốc là đường dẫn hay `pkg:<bản phân phối>:<thư mục>`. `gates/` kèm kho luôn được tra. **Một URI có ở hơn một gốc ⇒ `GateNotFoundError` (NE2001) "không duy nhất"**, trừ khi hai tệp trùng từng byte — không có "gốc nào thắng", nên gate của gói không che được `neuroedge://gates/hospitality/…` đã kèm kho. Phân giải vẫn thuần (`CHANGELOG.md` §3.3 #4). Ghim `extends` bằng digest và gate từ git/OCI: TSK-S3-21, RFC riêng |

### 3g. Bộ test tuân thủ theo loại

`neuroedge conformance <bản phân phối> [--kind=] [--json]`: nạp **chỉ** bản phân phối đó (gõ tên là hành vi bật tường minh) và chạy phép kiểm của mọi entry point NeuroEdge của nó. Kết quả mỗi phép kiểm: `pass` · `fail` · `unverifiable` (thiếu `probe()`) · `self_attested` (chỉ với tuyên bố phần cứng của bo). Thoát `0` khi không có `fail`
và `unverifiable`; `1` nếu có; `2` với loại chưa hiện thực (`CHANGELOG.md` §2.3). Bản phân phối không có entry point NeuroEdge nào ⇒ `1`, không phải `0` ("quét 0 không bao giờ là đạt", RFC-0013 §3f). Báo cáo JSON máy đọc: bản phân phối, phiên bản, `files_sha256`, `sdk`, phiên bản lõi, phiên bản bộ kiểm, danh sách (entry point, phép kiểm, kết quả,
chi tiết) — đặc tả ở `docs/spec/extension_sdk.md`, **chưa** vào `schemas/` (đóng băng khi đã có người dùng, cùng lập luận Q-65 câu 5). Huy hiệu (TSK-I2c-18) chỉ khi mọi phép kiểm `pass` (bo: `self_attested` ở tuyên bố phần cứng), không editable, `sdk_requires` hợp lệ; huy hiệu **không** nói plugin an toàn (§5, rủi ro 4).

| Loại | Phép kiểm (`<loại>.<tên>`) |
|:---|:---|
| Chung | `plugin.loads` (nhà máy, Protocol, chữ ký) · `plugin.sdk_range` · `plugin.name_pattern` · `plugin.not_editable` (chỉ huy hiệu) |
| `bridge` | `imports_only_sdk` (quét tĩnh AST: từ `neuroedge` chỉ `neuroedge.sdk`; chặn `gpiod` và tương tự — danh sách ở đặc tả, đoán tĩnh nên lách được) · `block_is_not_success` (chạy corpus `fixtures/tool_calls/` qua `probe()`: phía ngoài chỉ thấy thành công khi `status = ALLOW`) · `source_not_claimable` (lời gọi mang `call_source` trong tham số ⇒ `REJECTED`, nguồn ghi vẫn `bridge:<id>`) · `one_call_one_dispatch` (một lời gọi vào ⇒ đúng một `dispatch`, không thử tool khác khi bị chặn, không lệnh thô như `system.run`) · `core_down_is_failure` (đóng Guard hay `dispatch` ném ⇒ thất bại có hạn thời gian, không thực thi tại chỗ, **không xếp hàng chạy lại** khi lõi sống) |
| `fact_source` | `numbers_only` (mọi giá trị đẩy ra là `int`/`float`, không `bool`) · `age_from_capture` (quan sát giả lập chụp `D` ms trước ⇒ `observed_age_ms ≥ D − 10`; RFC-0014 §5 rủi ro 1) · `drops_on_disconnect` (probe cắt nguồn ⇒ `run` kết thúc, không đẩy lại giá trị cũ với tuổi mới) · `declared_names_only` · `rate_limit` (≤ 100 `push`/s, RFC-0014 §9 câu 10) |
| `actuator` | Do RFC-0018 §3e: `actuator.level_proven` (vector L0–L3 trên `DeviceDouble` của `probe()`, mỗi vector một ca phản chứng) · `off_is_idempotent` · `off_is_unconditional` · `builds_without_io` · `classifies_errors` · `receives_no_handles`. RFC này chỉ nối chúng vào `neuroedge conformance` và vào báo cáo |
| `board` | `validates` (`board validate`, gồm phong bì) · `not_reference` (id không thuộc `REFERENCE_BOARDS`, `SIM_MIRRORS` hay `boards/`) · `no_tier_or_mirror_claim` · `target_known` (RFC-0002) · `hardware_claims` ⇒ luôn `self_attested` |
| `template` | `new_works` (`new` vào thư mục tạm) · `lint_clean` (`gate lint`) · `own_tests_green` (≥ 1 ca ALLOW và 1 ca BLOCK, FR-DX-08) · `no_code_at_install` (đo bằng `sys.addaudithook`, PEP 578, trong tiến trình con: không `subprocess`, mạng, ghi ngoài thư mục tạm — **chưa kiểm khả thi**, bước đầu của TSK-I2c-12 là spike) · `no_gate_shadow` |
| `exporter` | `copies_only` (vết ghi và phán quyết của phiên bằng nhau có và không exporter) · `error_isolated` (exporter ném hay treo ⇒ phán quyết không đổi) · `off_decision_path` (độ trễ quyết định không tăng) · `anonymised_only` |

Mỗi phép kiểm có một ca phản chứng ở `fixtures/compliance/<nhóm>/{valid,invalid}/` (`bridges`, `fact_sources`, `boards`, `templates`, `exporters`; `actuators` theo RFC-0018 §3e) kèm `expected_results.yaml`, khép kín hai chiều (`CONTRIBUTING.md` §3; FR-EXT-04). Corpus đi vào bánh xe để `conformance` chạy được từ bản cài.

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có. Không đổi lược đồ nào. `agent.toml` không có `[plugins]` chạy như cũ; `--board <id>`, `--template <tên>`, một `--registry` chạy như cũ |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có, hẹp: `--board ./x.toml` (hôm nay lỗi "không có hồ sơ"), `--template <đường dẫn>`, nhiều `--registry`. Nới, không siết |
| Cần tăng phiên bản lược đồ? | Không. `trace.v1`: `metadata` mở (`metadata.plugins`, `board_origin`, `board_digest`); vết ghi cũ hợp lệ. `board.v1`, `gate.v1`: không đổi |
| Mã băm / chữ ký gate, `digests.lock`, ba vết ghi chuẩn mực, `NETR`, đáp án corpus tool call | Không đổi; thêm corpus `fixtures/compliance/<nhóm>/` |
| Ngữ nghĩa phân giải gate | Hợp nhất và kế thừa **không đổi**; đổi chỗ tìm tệp (một gốc → nhiều gốc) và thêm đường từ chối khi URI không duy nhất. Vì `gate_resolver.py` nằm ở `CONTRIBUTING.md` §3, RFC này là chỗ ký việc đó |
| API Python (`python_api.md`) | MINOR: thêm hai mô-đun công khai theo vị trí (§1, §2); `neuroedge.__all__` giữ nguyên, `test_public_api.py` giữ nguyên; thêm `tests/test_sdk_api.py` |
| CLI (`python_api.md` §6, `test_cli_contract.py`) | MINOR: thêm `plugin list`, `plugin doctor` (`--config=`, `--json`), `conformance` (`<bản phân phối> --json --kind=`), `bridge run` (`<id> --agent\|-a= --guard= --registry\|-r=*`); `--registry\|-r=` thành lặp (`=*`; mọi lời gọi cũ còn đúng); `--board`, `--template` vẫn nhận một giá trị. Bản chụp và §6 đổi cùng PR |
| Kiến trúc | Ba đơn vị mới `guard`, `sdk`, `plugins` (bộ nạp): cạnh vào `tests/test_architecture_layers.py` (`ALLOWED`, `:19`) và `docs/architecture/vi/03-component-host-c4l3.md` trong cùng thay đổi |
| Mã lỗi | Không mã mới. `AgentManifestError` (NE3002) nới *Nguyên nhân*: `[plugins]`, nạp plugin, lệch SDK, `guard.toml`; `BoardCapabilityError` (NE3001): tham chiếu bo sai, mượn id bo tham chiếu; `GateNotFoundError` (NE2001): URI không duy nhất; `ReplayError` (NE4003): digest bo lệch |
| Gói | Không phụ thuộc mới (`importlib.metadata`, `pyproject.toml:36` giữ nguyên). `scripts/wheel_smoke.sh` chạy thêm `conformance` trên một plugin mẫu cài từ bánh xe |
| RFC-0014 | Không đổi chữ nào. Thêm song song `token_env`: nguồn khai `plugin = "<tên entry point>"` ở `[external.sources.<id>]`; hai khoá loại trừ; mọi luật hai chiều gate ↔ agent (§3c của RFC-0014) áp nguyên; khối `[external]` không cần `socket` khi không nguồn nào dùng ổ cắm. Câu hỏi §9.6 |

## 5. Ảnh hưởng an toàn

**Gate không lỏng hơn và không đường nào tới chân bị mở thêm.** Ngữ nghĩa phán quyết, năm nguyên tắc kế thừa, mặc định fail-closed không đổi; Guard đi cùng `dispatch`, cùng sổ token và phong bì (§3b mục 1). Mục mới cho `threat_model.md` — "§2d. Trong phạm vi: plugin của bên thứ ba" (viết khi hiện thực; §2c dành cho RFC-0014):

| Đường tắt | Chặn bởi | Kết quả |
|:---|:---|:---|
| Bridge tự khai `source` hay `call_source` | `ToolRequest` không có trường `source`; `call_source` trong tham số là tham số lạ | `REJECTED`; nguồn ghi vẫn `bridge:<id>` |
| Bridge chạm HAL | API không có handle; bộ kiểm `imports_only_sdk` | Không có đường trong API; lách bằng nhập trực tiếp là rủi ro 1 |
| Fact source tự khai tuổi / cấp cho tiêu chí không khai nguồn | `push` không có tham số tuổi; `observed_age_ms` chỉ cộng thêm (RFC-0014 §3f); tiêu chí không có `external_source` bỏ qua | Dữ kiện bị bỏ ⇒ `criterion_unavailable` ⇒ BLOCK |
| Actuator nhận lệnh không qua HAL | Chỉ HAL giữ tham chiếu; lệnh bật qua `_admit` | Từ chối; `safe_off` vẫn chạy không token |
| `pip install` tự bật một plugin | Danh sách bật ở tệp được commit; phát hiện không import; không cờ CLI | Không nạp |
| Plugin hỏng, lệch SDK, trùng tên bị bỏ qua lặng lẽ | Không khởi động (§3d mục 3) | `NE3002`, thoát 1 |
| Bo ngoài kho nhận danh bo tham chiếu; vào cột tương đương bậc 1 | Mượn id bị từ chối; `verify` chỉ duyệt `REFERENCE_BOARDS` | `NE3001`; không có cột |
| Gói gate che gate chuẩn kèm kho | URI không duy nhất bị từ chối | `NE2001` |
| Template chạy mã / ghi đè | Chỉ `write_text`, không ghi đè | Từ chối |
| Exporter đổi phán quyết hay làm chậm | Bản sao, hàng đợi có chặn, lỗi cô lập | Phán quyết không đổi |

**Phải không lùi (test ở §7):** A3 còn 0 lối tắt khi chạy qua Guard (chạy lại bộ test A3 trên Guard); lệnh về phía an toàn không bao giờ bị chặn (Q-62): lỗi, trễ hay treo của plugin không cản `close()`, tự tắt, `safe_off`; không công tắc fail-open; thiếu plugin ≠ thiếu kiểm soát.

**Rủi ro còn lại — nói thẳng:**
1. **Plugin độc hại hoặc lỗi trong tiến trình** (`import gpiod`, luồng riêng, đọc bộ nhớ sổ token): `threat_model.md` §3, ngoài phạm vi. Giảm bằng bật tường minh, ghim phiên bản, `files_sha256` trong vết ghi, bộ kiểm quét tĩnh. Nếu tiến trình chết, trên `linux` chân vẫn thả (tiến trình giám sát, `threat_model.md` §2).
2. **Chuỗi cung ứng:** gói bị chiếm quyền hay giả tên. Ghim phiên bản và `files_sha256` bắt **thay đổi sau khi duyệt**, không bắt lần cài đầu; ký là I10; bản editable không có hash.
3. **Proxy bị vòng:** Guard chỉ canh đường đi qua nó. Server MCP, Home Assistant hay thiết bị còn nghe trực tiếp thì gate chỉ để trang trí. **Proxy phải là đường duy nhất**; `plugin doctor` in cảnh báo hoặc "không kiểm được" (TSK-I2c-14 cấp phép kiểm), và tài liệu nói rõ — không thể bảo đảm ở lõi.
4. **Bộ kiểm không chứng minh được sự vắng mặt:** quét tĩnh lách được; phép kiểm động tin `probe()` do chính plugin viết. "NeuroEdge-gated" là bằng chứng đã qua phép kiểm, không phải chứng nhận an toàn (PRD §14, Q-38).
5. **Bridge nói dối phía ngoài:** hiệu ứng vật lý vẫn do gate quyết, nhưng bên ngoài có thể tin "đã bật" khi lõi nói BLOCK. Phép kiểm `block_is_not_success` bắt lỗi vô ý, không bắt cố ý.
6. **Bo cộng đồng khai phong bì lỏng:** phong bì là chốt thứ hai do tác giả bo đặt số. Nhãn, bảng in ra và `metadata.board_origin` làm điều đó thấy được, không sửa được.
7. **`facts` do chương trình chủ đặt bằng `set_fact`** là điều người vận hành tin, như `c.facts` hôm nay.
8. **Gate không đọc `call_source` nhận mọi nguồn**, kể cả `bridge:<id>` vừa bật (RFC-0017 §5 rủi ro 3). `guard init` sinh gate liệt kê nguồn tường minh; `plugin doctor` cảnh báo mỗi tool có gate không đọc `call_source` khi có bridge được bật.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Plugin chạy ngoài tiến trình qua IPC (mỗi plugin một tiến trình) | Cách ly mạnh hơn, nhưng cần một giao thức *lệnh* thứ hai bên cạnh RFC-0014 (chỉ dữ kiện, một chiều, số) và mở lại câu hỏi "cái gì trên ổ cắm là đường lệnh"; thêm độ trễ vào đường quyết định và vòng đời tiến trình. Không loại vĩnh viễn: `Dispatcher` là dữ liệu vào – dữ liệu ra nên một lớp vỏ ngoài tiến trình hiện thực được cùng Protocol; xem lại khi có ký plugin (I10) |
| Sandbox WASM ngay | Chưa đánh giá độ chín cho plugin Python có truy cập phần cứng; thêm môi trường chạy phải qua Q-11. Hoãn tới khi có plugin thật cần |
| Giữ fork-and-PR (không đổi lõi) | Trái Q-67: bên thứ ba không được chờ đội lõi |
| Mở rộng `provider = "python:…"` cho mọi thứ | Không phát hiện (`plugin list`), không phiên bản, không bất biến cấu trúc (nhà máy nhận bất cứ gì, import bất cứ gì), không mục tiêu cho bộ kiểm, không nguồn gốc kiểm toán được (§1 mục 3, §2). Giữ nguyên cho provider mô hình |
| Nạp mọi entry point đã cài | `pip install` thành bật; một phụ thuộc bắc cầu đổi đường tới gate. Trái tiền lệ RFC-0014 §9 câu 9 |
| Bỏ qua plugin hỏng và chạy tiếp | Mất lặng lẽ một thành phần của đường an toàn; trái `CHANGELOG.md` §3.3 #2 |
| `neuroedge.sdk` re-export `neuroedge.__all__` | Trao `SimHAL`, `LinuxHAL`, `digital`, `motion` cho bridge (§1 mục 3) và buộc cam kết SDK vào `0.x` |
| Trao `Guard` hay `Conversation` cho bridge | Cả hai giữ HAL và sổ token (`conversation.py:84–92`) |
| Khai bậc hay "tham chiếu" trong hồ sơ bo; đếm bo cộng đồng vào `verify` bằng một cờ | Bậc là lời hứa của đội lõi (RFC-0002 §3b, §6); `verify` 100% bậc 1 chỉ có nghĩa với bo đội lõi cam kết |
| "Gốc đầu tiên thắng" khi nhiều gốc gate | Gói che được gate chuẩn; thay bằng từ chối khi không duy nhất |
| Đưa báo cáo tuân thủ vào `schemas/` ngay | Đóng băng trước khi có người dùng thì mọi sửa là `v2` (Q-65 câu 5); để ở `docs/spec/extension_sdk.md` |
| Nhóm entry point thứ bảy cho gói gate | Đã chốt sáu loại; `pkg:<bản phân phối>:<thư mục>` đủ và không chạy mã |

## 7. Bằng chứng kiểm chứng

Test dưới đây là **tên đề xuất**, chưa tồn tại tới khi RFC được chấp thuận. Corpus theo luật khép kín hai chiều (`CONTRIBUTING.md` §3; thêm dòng cho `fixtures/compliance/<nhóm>/` vào bảng ở đó).

- [ ] **Guard** (`python/tests/test_guard.py`): `test_a_guard_gates_an_action_without_agent_toml_action_or_session` (tiêu chí FR-EXT-01) · `test_a_guard_trace_validates_and_names_its_guard` · `test_the_a3_suite_holds_on_a_guard` (chạy lại `test_no_path_reaches_a_pin_without_a_valid_token` và các ca cạnh nó) · `test_a_guard_without_a_board_refuses_a_tool_that_requires_a_pin` · `test_a_declarative_drive_moves_a_pin_only_after_allow_and_through_token_and_envelope` · `test_a_guard_hands_out_a_dispatcher_only_for_a_unique_valid_id_and_test_is_unreachable` ·
  `test_a_guard_has_no_fail_open_switch` · `test_a_gate_that_does_not_resolve_stops_the_load` · `test_a_missing_gate_blocks_with_gate_not_found` · `test_the_same_facts_give_the_same_verdict_on_a_guard_and_a_session` · `test_two_concurrent_dispatches_never_share_a_call_source` (ghim lỗi §2) · `test_a_guard_trace_replays_to_the_same_verdicts` (§9.3)
- [ ] **SDK** (`tests/test_sdk_api.py`): `test_the_sdk_surface_is_pinned` (tên, thành viên Protocol, chữ ký) · `test_the_sdk_version_is_not_the_package_version` · `test_the_sdk_exports_no_hal_name_and_no_name_of_all` · `test_a_plugin_for_another_sdk_major_or_a_newer_minor_is_refused` · cập nhật `test_architecture_layers.py` cho `guard`, `sdk`, `plugins`
- [ ] **Bộ nạp** (`tests/test_plugins.py`): `test_listing_plugins_imports_nothing` (gói có entry point ném lúc import vẫn liệt kê được) · `test_an_installed_plugin_that_is_not_enabled_never_loads` · `test_a_plugin_that_fails_to_import_refuses_start_and_starts_nothing` · `test_an_sdk_mismatch_refuses_start` ·
  `test_a_factory_of_the_wrong_shape_refuses_start` · `test_two_enabled_distributions_with_one_entry_point_name_refuse_start` · `test_a_version_pin_that_does_not_match_refuses_start` · `test_provenance_is_printed_and_recorded_in_the_trace_metadata` · `test_an_editable_install_has_no_file_hash_and_doctor_warns` ·
  `test_no_cli_flag_enables_a_plugin` · `test_a_plugin_config_with_a_literal_secret_is_refused` · `test_board_and_template_plugins_load_without_importing_the_package` · `test_doctor_says_what_it_cannot_check`
- [ ] **Bất biến cấu trúc**: `test_a_bridge_receives_a_dispatcher_and_nothing_else` · `test_the_dispatcher_stamps_the_source_and_a_request_cannot_carry_one` · `test_a_fact_source_cannot_state_read_ms_age_or_seq` · `test_a_fact_for_a_criterion_without_external_source_is_dropped` · `test_an_actuator_is_reachable_only_through_the_hal` ·
  `test_safe_off_needs_no_token_and_no_envelope` · `test_an_exporter_gets_copies_and_cannot_change_a_verdict` · `test_a_raising_exporter_leaves_the_verdict_alone` · `test_exporters_see_anonymised_events`
- [ ] **Tài sản** (`test_boards.py`, `test_templates.py`, `test_gate_registry.py`): `test_a_board_path_loads_and_is_labelled_community` · `test_an_out_of_tree_board_cannot_take_a_reference_board_id` · `test_verify_never_replays_a_community_board` · `test_the_trace_of_a_community_board_records_origin_and_digest` · `test_replay_refuses_a_board_whose_digest_changed_or_is_missing` ·
  `test_a_template_from_a_path_copies_files_and_runs_nothing` · `test_a_template_refuses_symlinks_dotdot_and_absolute_paths` · `test_a_git_template_needs_a_full_commit_sha` · `test_a_template_never_overwrites_a_file` · `test_a_uri_in_two_gate_roots_is_refused_unless_identical` · `test_a_third_party_root_cannot_shadow_a_shipped_gate` ·
  `test_the_shipped_gates_root_is_always_searched` · `test_one_registry_flag_behaves_as_before`
- [ ] **Tuân thủ** (`tests/test_conformance.py`): `test_every_plugin_example_has_an_expectation_and_every_expectation_an_example` · `test_every_check_of_every_kind_catches_a_counter_example` · `test_a_distribution_with_no_neuroedge_entry_point_fails` · `test_conformance_exit_codes` · `test_the_report_names_sdk_core_and_file_hash` · `test_an_editable_install_is_refused_a_badge`
- [ ] **Hợp đồng**: `test_cli_contract.py` (các dòng mới của §4) · `scripts/wheel_smoke.sh` xanh trên bản cài · `neuroedge gate lint`, `neuroedge verify` xanh · `pytest -q` 0 failed, 0 skipped

## 8. Việc phải làm khi chấp thuận

- [ ] **TSK-I2c-07** — `neuroedge.guard` (§3b), hàm dựng HAL dùng chung, khoá `dispatch`, đường replay bằng `guard.toml`; `python_api.md` §1, §2; `test_architecture_layers.py`, `03-component-host-c4l3.md`
- [ ] **TSK-I2c-08** — `resolve_board`, `--template` đường dẫn / `pkg:` / `git+URL@sha`, nhiều gốc `GateRegistry` và `--registry` lặp (§3f); `board validate` cùng TSK-I2c-05 (RFC-0002)
- [ ] **TSK-I2c-11** — `neuroedge.sdk` (Protocol, `SDK_VERSION`), bộ nạp entry point, `[plugins]`, `plugin list`, `plugin doctor`, `bridge run`, nguồn gốc vào `metadata.plugins` và sự kiện `plugin_loaded`; `threat_model.md` §2d; khoá `plugin` ở `[external.sources.<id>]` cùng TSK-I2c-09
- [ ] **TSK-I2c-12** — phép kiểm theo loại (§3g), `fixtures/compliance/<nhóm>/` (cùng vector actuator của RFC-0018), `neuroedge conformance`, `docs/spec/extension_sdk.md`; spike `sys.addaudithook` trước
- [ ] **TSK-I2c-13** — template plugin cho từng loại và hướng dẫn "viết plugin trong 30 phút" (có thể sinh bằng chính cơ chế `--template`: chọn ở TSK)
- [ ] **TSK-I2c-18** — index và huy hiệu đọc báo cáo §3g; `plugin install` chỉ nhận bánh xe dựng sẵn
- [ ] `python_api.md` §3 (cam kết SDK), §6; `CONTRIBUTING.md` §3 (dòng corpus mới); `LICENSING.md` (điều khoản plugin, TSK-I2c-06); `docs/user/thuat-ngu.md` (plugin, bridge, SDK, bo cộng đồng); `neuroedge-prd.md` (FR-EXT-01 → 05, 09, NFR-SEC-10 tick); `neuroedge-roadmap.md`; `docs/rfc/README.md` (dòng RFC-0016); `CHANGELOG.md` `[Chưa phát hành]`

## 9. Quyết định cho các câu hỏi mở (Q-68, 2026-10-04)

Q-67 chốt tám quyết định, không chốt các điểm sau. Kỹ thuật trưởng **chấp nhận khuyến nghị của mọi câu dưới đây**, theo nguyên tắc an toàn cao nhất của Q-57; mỗi khuyến nghị là quyết định (Q-68, 2026-10-04). Mục này là hồ sơ quyết định: §3–§8 lệch với nó thì sửa §3–§8.

1. **Mức ổn định của `neuroedge.guard`.** Khuyến nghị: cùng mức `__all__` (`0.x`, MINOR đóng vai MAJOR) — D7 chỉ nói `neuroedge.sdk`; xem lại khi gói đạt `v1.0` (lúc đó §3 của `python_api.md` có hiệu lực đầy đủ).
2. **Có thêm `Guard` vào `neuroedge.__all__` không.** Khuyến nghị: không; dùng `from neuroedge.guard import Guard`. Mỗi tên thêm vào `__all__` là một quyết định (`python_api.md` §3), thêm sau là MINOR.
3. **Replay vết ghi của Guard có nằm trong I2c không.** Khuyến nghị: có, ở TSK-I2c-07 — "lõi" gồm replay (ghi chú thiết kế §3), và không có nó `verify` và Action CI không chạm được vết của Guard. Nếu chi phí vượt lịch: tách thành việc ngay sau I2c, vết Guard vẫn `trace validate/show/view/export`.
4. **Thời hạn ngừng hỗ trợ của SDK.** Khuyến nghị: hai bản MINOR của SDK (§3e), tính theo `SDK_VERSION`, không theo ngày.
5. **Cho ghim băm tệp trong danh sách bật** (`"neuroedge-muse==0.4.1#sha256=…"`). Khuyến nghị: cho, tuỳ chọn, không bắt buộc; ghim bắt buộc đi cùng ký plugin (I10).
6. **Sửa nhẹ RFC-0014** (khoá `plugin` ở `[external.sources.<id>]`, `socket` tuỳ chọn khi không nguồn nào dùng ổ cắm, §4). Khuyến nghị: chấp nhận — fact source trong tiến trình (TSK-I2c-09) cần một chỗ khai không qua ổ cắm; luật hai chiều gate ↔ agent giữ nguyên.
7. **Tách một bản phân phối Apache-2.0 `neuroedge-sdk` chỉ chứa Protocol** để tác giả plugin không phụ thuộc gói PolyForm NC lúc dựng. Khuyến nghị: chưa; D8 đã chốt hệ quả giấy phép, và Protocol gắn với lõi. Xem lại ở điểm rẽ Beta (Q-59, `TODOS.md` #51).
8. **`git+URL@sha` cho `--board` và `--registry` như template.** Khuyến nghị: chưa — gate và bo từ git cần ghim digest (TSK-S3-21) trước; người dùng tự lấy tệp về rồi dùng đường dẫn.
9. **Hai câu RFC-0017 đẩy sang đây** (§9.2: `Guard` và proxy gán nguồn nào; §9.5: một bridge có kèm danh sách tool được gọi không). Khuyến nghị: (a) chương trình dùng `Guard` khai id và nhận `bridge:<id>`, proxy của lõi giữ nguồn của client phía trước (§3b mục 4); (b) **không** có danh sách tool theo bridge — gate đã là nơi quyết, qua `call_source` hay `call_channel` (RFC-0017 §3d), `guard init` sinh gate liệt kê nguồn và `plugin doctor` cảnh báo gate không đọc nó (§5, rủi ro 8).
