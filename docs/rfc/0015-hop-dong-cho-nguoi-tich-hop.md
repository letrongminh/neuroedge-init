# RFC-0015: Đóng băng hợp đồng cho người tích hợp — Gated Tool Profile, định danh phiên bản `board.v1`, danh mục mã lỗi `NE*`

| | |
|:---|:---|
| **Mã RFC** | 0015 |
| **Tiêu đề** | Bốn lược đồ mới vào `schemas/` (`tool-call.v1`, `tool-result.v1`, `error.v1`, `error-codes.v1`) và khoá định danh phiên bản `schema` của `board.v1` — TSK-I6-05 |
| **Hợp đồng bị ảnh hưởng** | `schemas/` *(thêm bốn tệp; `board.v1.json` thêm đúng một khoá tuỳ chọn `schema`)* · quy tắc nạp bo mạch (`python/neuroedge/hal/board.py`) · nơi duy nhất của danh mục mã lỗi (PRD Phụ lục B ↔ `python/neuroedge/errors.py`; sửa `CONTRIBUTING.md` §8.1) · **không** đụng `gate.v1`, `trace.v1`, ngữ nghĩa phân giải, `NETR`, `digests.lock`, ba vết ghi chuẩn mực |
| **Yêu cầu PRD liên quan** | FR-MDL-10, FR-GOV-01, FR-GOV-02, FR-HAL-02, FR-DX-04 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-10-03 |
| **Trạng thái** | 🟡 Đang thảo luận |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (thêm lược đồ vào `schemas/`, chạm `board.v1`, đổi nơi duy nhất của danh mục mã lỗi). **Chủ sản phẩm** cho các câu hỏi mở ở §10 có tính sản phẩm hoặc giấy phép (Q10.4, Q10.5) |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3 — sửa `schemas/*.json` (thêm lược đồ và sửa `board.v1.json`).
> Task: TSK-I6-05. Quyết định nền: `neuroedge-prd.md` §15 **Q-58** (đóng băng Gated Tool Profile trước lần công khai,
> thay mốc "có client bên ngoài" của `TODOS.md` #23), **Q-63** (mở phạm vi: thêm khoá định danh phiên bản `board.v1`
> và danh mục mã lỗi dạng máy đọc được; `agent.toml` vẫn ngoài `schemas/`), Q-45 (lược đồ theo Apache-2.0), Q-64
> (`docs/spec/python_api.md`: hợp đồng dạng tệp có phiên bản riêng, không thuộc API Python).
> Đích: tiêu chí ra I6 số 8 — *"Gated Tool Profile, định danh phiên bản `board.v1` và danh mục mã lỗi nằm trong `schemas/`
> qua RFC được chấp thuận; mọi ca của `fixtures/tool_calls/` thẩm định theo lược đồ đó."*
> Việc đưa lược đồ lên `https://schema.neuroedge.dev` là TSK-I6-02, **ngoài** RFC này (§3f chỉ ghi `$id` để khớp).
> Mọi khẳng định về mã dưới đây đã đối chiếu với kho tại `87db7c7`; chỗ lệch giữa đặc tả, corpus và mã ở §9.

## 1. Vấn đề

Q-58 muốn một dự án OSS khác (client MCP của Home Assistant, server thoại, agent framework trên máy khác) gọi được HAL và gate
qua NeuroEdge mà **không đọc mã Python**. Hôm nay ba thứ họ cần nằm ở chỗ họ không dùng được:

1. **Tool call và kết quả của nó chỉ có đặc tả bằng chữ.** `docs/spec/tool_calling.md` §1 (phong bì), §4 (kết quả), §9 (corpus) mô tả
   hình dạng; hình dạng *chạy được* nằm trong mã: `ToolCall` (`python/neuroedge/actions/tools.py`, dataclass `name`, `arguments`,
   `source`, `id`) và `result_schema()` (cùng tệp), hàm dựng một dict JSON Schema từ `Reason` và `ACTIONS` lúc chạy. Một SDK Rust
   hay Go không thể sinh kiểu từ chữ, cũng không thể chạy `result_schema()`. Corpus `fixtures/tool_calls/` (28 ca: 16 `valid/`, 12
   `invalid/`) chỉ thẩm định được bằng runtime Python (`neuroedge.testing.tool_corpus`), không bằng một lược đồ.
2. **Tệp bo mạch không mang phiên bản.** Gate mang `schema: neuroedge.gate/v1` (`schemas/gate.v1.json`, `const`); vết ghi mang `$schema`
   (`schemas/trace.v1.json`, bắt buộc, `format: uri`); `boards/*.toml` không mang gì. Hệ quả cụ thể, đã chạy thử: `board.v1.json` không
   đóng (`additionalProperties` không khai), nên `validate_board_document` nhận cả
   `{"schema": "rác", "nonsense": 1, "board": …, "capabilities": …}`, và `BoardProfile.to_document()` vứt hai khoá đó khi ghi lại. Một
   runtime cũ đọc bo mạch thuộc phiên bản chính khác sẽ **lặng lẽ bỏ qua mọi khoá nó không biết** — với bo mạch, đó là bỏ qua giới hạn phần
   cứng (RFC-0007 đặt `envelope` ở đó) chứ không phải chỉ mất tính năng.
3. **Danh mục mã lỗi nằm ở hai nơi viết tay.** PRD Phụ lục B (bảng markdown, tiếng Việt) và `python/neuroedge/errors.py` (lớp). Không
   cái nào là máy đọc được; không test nào buộc chúng khớp; `CONTRIBUTING.md` §8.1 chỉ định PRD Phụ lục B là "nơi duy nhất" nhưng lời hứa
   ở đầu Phụ lục B ("Tên lớp và mã `NE…` khớp `errors.py`") sai ở ba chỗ (§9, F4). Thiết bị cũng nói mã: `targets/esp32s3/components/ne_gate/src/ne_token.c`
   trả chuỗi `"NE1001"` / `"NE1002"`, và `actuator_command_rejected.code` của vết ghi mang chúng.

## 2. Vì sao lược đồ hiện tại không giải quyết được

- `schemas/` chỉ có ba tệp, và `python/tests/test_schemas.py::test_schemas_directory_holds_exactly_the_three_frozen_schemas` khoá đúng ba tên —
  "một lược đồ thứ tư xuất hiện mà không có RFC cũng là một phát hiện". Chưa lược đồ nào cho tool call, kết quả hay lỗi.
- `board.v1.json`: `required: ["board", "capabilities"]`, không `schema`, không `additionalProperties`. Không có chỗ để một bo mạch nói "tôi là
  v1" hay "tôi là v2", và không có luật cho bộ đọc từ chối phiên bản lạ. Gate có (`const`), vết ghi có `$schema` nhưng **không ghim**
  (`format: uri` chấp nhận mọi URI; chỉ `neuroedge.trace.TRACE_SCHEMA_ID` ghi đúng) — nên "gate và vết ghi đã có định danh phiên bản" (roadmap
  TSK-I6-05) đúng cho gate, chỉ đúng một nửa cho vết ghi (§9, F6).
- `tool_calling.md` §4 nói rõ lược đồ kết quả sinh từ mã và client MCP kiểm `structuredContent` theo nó, nhưng **đóng**: `additionalProperties:
  false`, `reason` là `enum` của `Reason` (10 giá trị, đã lớn hai lần trong mười ngày: RFC-0005 thêm `argument_out_of_range`, RFC-0009 thêm `value_out_of_range` — `git log -S` trên `engine/verdict.py`). Đóng băng nguyên dạng nghĩa là mỗi `Reason` mới là `v2` cho mọi client đang kiểm
  `outputSchema`. Cần quyết định có chủ ý (§3b), không thể "chép từ mã".
- Corpus không đủ để chứng minh một lược đồ: 28 ca chạm 3 trong 10 `reason` (`condition_not_met` ×8, `argument_out_of_range` ×5, `criterion_unavailable` ×1),
  4 trong 5 `source` (không ca nào `system_one`), cả 4 `on_block`, cả 3 `status` (§9, F2). Một lược đồ qua corpus mà chưa từng thấy
  `budget_exceeded` thì chưa được thử.

## 3. Thay đổi đề xuất

Bốn tệp mới và một khoá mới. `$id` theo PRD Phụ lục C (`https://schema.neuroedge.dev/<loại>/v<n>.json`); draft 2020-12 như ba tệp hiện có; mô tả
tiếng Anh như `gate.v1.json`.

### 3a. `schemas/tool-call.v1.json` — phong bì `ToolCall`

Rút từ `tool_calling.md` §1, `ToolCall` (`tools.py`) và `CASE_KEYS`/`CALL_KEYS` (`testing/tool_corpus.py`). Hai hình dạng, vì spec §1 nói **bên gọi không khai `source`**:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schema.neuroedge.dev/tool-call/v1.json",
  "title": "NeuroEdge Gated Tool Profile — ToolCall envelope v1",
  "$ref": "#/$defs/call",
  "$defs": {
    "id":        { "type": "string", "description": "Provider-assigned; empty or absent: the dispatcher numbers it call_1, call_2…" },
    "name":      { "type": "string", "minLength": 1 },
    "arguments": { "type": "object", "default": {} },
    "source":    { "enum": ["local_grammar", "system_one", "system_two", "mcp", "test"],
                   "description": "Assigned by the runtime from the connection (tool_calling.md §5); never the caller's to state." },
    "request": {
      "description": "What a caller sends. No `source`: a request that states one is refused at the envelope.",
      "type": "object", "required": ["name"],
      "properties": { "id": { "$ref": "#/$defs/id" }, "name": { "$ref": "#/$defs/name" }, "arguments": { "$ref": "#/$defs/arguments" } },
      "additionalProperties": false
    },
    "call": {
      "description": "The envelope the dispatcher holds, and the data of the `tool_call` trace event: a request plus the assigned source.",
      "type": "object", "required": ["name"],
      "properties": { "id": { "$ref": "#/$defs/id" }, "name": { "$ref": "#/$defs/name" },
                      "arguments": { "$ref": "#/$defs/arguments" }, "source": { "$ref": "#/$defs/source" } },
      "additionalProperties": false
    },
    "input_schema": { "…": "§3a.2" },
    "tool": { "…": "§3a.2" }
  }
}
```

Đã chạy thử: tài liệu trên là draft 2020-12 hợp lệ, và **cả 28 `call` của `fixtures/tool_calls/` hợp lệ theo `#/$defs/call`**; `{"name": "a", "source": "mcp"}` bị `#/$defs/request` từ chối, `{"name": "a"}` thì không.

- **`name`** `minLength: 1` và không `pattern`: tool lạ là `REJECTED` ở bước 2 của `dispatch()` (§2), không phải lỗi phong bì (`unknown_tool.yaml`). Một `name` rỗng
  (`parse_tool_calls` sinh `""` khi payload không có tên) vẫn đi tới `REJECTED` trong runtime; lược đồ từ chối sớm hơn — phong bì không hợp lệ ≠ lời gọi bị từ chối.
- **`arguments`** là `object` mở: kiểu từng tham số là việc của `inputSchema` **của từng tool** (§3a.2), không của phong bì. Khoá dành riêng `__unparseable__` (do
  `parse_tool_calls` chèn khi JSON của nhà cung cấp hỏng; `dispatch` ⇒ `REJECTED` "unknown argument") hiện **không có trong đặc tả** (§9, F8); RFC này đưa nó vào
  `tool_calling.md` §2 chứ không vào lược đồ.
- **`source`**: đúng năm giá trị của `SOURCES`; test buộc hai bên (§7). Tập đóng. Thêm giá trị là nới lỏng một `enum` (không phá tệp nào đang hợp lệ) nhưng đổi hợp đồng
  của `call_source` trong gate (§5 của spec; chỉ số `choice` trong `NETR`) nên vẫn cần RFC — đã là luật (`tool_calling.md` §5).
- **Mạng (§8.1 của spec) không thêm gì vào phong bì.** Một lời gọi qua `mcp serve --http` là `source = "mcp"`, như stdio; gate không phân biệt hai cửa. Từ chối xác thực xảy
  ra **trước** phong bì: HTTP 401/403, không `ToolResult`, không giá trị `status` mới; dấu vết là sự kiện `mcp_auth_refused` (§7 của spec), không thuộc lược đồ kết quả. Danh tính
  thiết bị (`sub` của token) không phải trường của phong bì. Nếu một gate muốn cấm riêng cửa mạng hay riêng một thiết bị thì cần thêm giá trị vào `source` — một thay đổi mà
  RFC này không làm và cố ý không chặn đường (§10, Q10.11). *(Lúc viết, §8.1 và `mcp_http.py` nằm trên nhánh `feat/mcp-network`, commit `baff0ae`; RFC dẫn, không chép.)*

**3a.2. Mô tả tool (`tools/list`).** `mcp_tool()` (`tools.py`) trả `{name, description, inputSchema, outputSchema}`; `input_schema()` sinh một **tập con** JSON Schema — `type` ∈ {`string`, `integer`, `number`, `boolean`},
`default`, `required`, `additionalProperties: false`, cộng `minimum`/`maximum`/`enum`/`maxLength` từ gate (RFC-0005, `engine/arguments.py::schema_hint`). `$defs.input_schema` mô tả đúng tập con đó và `$defs.tool` mô tả
bộ bốn trường, với `outputSchema` là `tool-result.v1` ghim `tool` (§3b). Đây là phần mà người hiện thực Profile cần để biết "lời gọi khớp `inputSchema`" nghĩa là gì — ranh giới `valid/` và `invalid/` của corpus (§9 của spec) đặt ở chính chỗ đó
(`testing/tool_corpus.py::_conforms`). Việc đưa phần này vào hay để ngoài là Q10.3.

**Ranh giới của lược đồ — nói rõ để không ai đọc nhầm.** Lược đồ **không** biểu diễn được: ép kiểu chuỗi → số/bool (§2 bước 3 của spec: slot ngữ pháp là chữ), ràng buộc tham số của gate (kiểm **sau** schema, `BLOCK argument_out_of_range` chứ không `REJECTED`, §3 của spec),
dữ kiện `call_source`, hay việc tool có tồn tại. Một thẩm định lược đồ thành công **không** chứng minh một runtime tuân thủ Profile; bộ kiểm tuân thủ là corpus `fixtures/tool_calls/` chạy qua `dispatch()` — cùng lập luận với bất biến `CHANGELOG.md` §3.3 #1 cho gate.

### 3b. `schemas/tool-result.v1.json` — kết quả

Cố định thành tệp tĩnh đúng hình dạng mà `result_schema()` sinh hôm nay (đã in và đối chiếu), với **hai nới có chủ ý** để hợp đồng sống được qua các RFC sau mà không phải lên `v2`:

| | `result_schema()` hôm nay | `tool-result.v1.json` đề xuất | Lý do |
|:---|:---|:---|:---|
| `tool`, `status`, `gate`, `failed_criterion`, `message`, `escalated_to`, `problems`, `fallback`, `confirmation` | như ở `tools.py` | **giữ nguyên** kiểu, bắt buộc có điều kiện (`BLOCK` ⇒ `gate`, `on_block`; `REJECTED` ⇒ `problems`) | đã được corpus và `test_an_mcp_client_gets_the_same_result_and_its_sdk_accepts_it` kiểm |
| `status` | `enum` ALLOW · BLOCK · REJECTED (ở `fallback`: ALLOW · BLOCK) | **đóng**, như hôm nay | thêm một trạng thái là đổi nghĩa của kết quả cho mọi client ⇒ `v2` |
| `on_block` | `enum` `ACTIONS` (`deny`, `escalate`, `ask`, `degrade`) | **đóng**, như hôm nay; test buộc trùng `gate.v1.json` | thêm hành vi chặn đã là RFC của `gate.v1` (RFC-0004, RFC-0006) |
| `reason` | `enum` của `Reason` (10 giá trị) | `type: string`, `pattern: ^[a-z][a-z0-9_]*$`, kèm danh sách giá trị đã biết trong chú thích `x-neuroedge-known`; test buộc danh sách = `Reason` hai chiều | `Reason` đã lớn hai lần trong mười ngày; client gặp `reason` lạ dưới `status: BLOCK` **phải** coi là bị chặn (fail-closed, đã là nghĩa của `BLOCK`) chứ không phải kết quả hỏng. **Đề xuất, chờ quyết định: Q10.1** |
| Đối tượng (`additionalProperties`) | `false` ở gốc, `fallback`, `confirmation` | `true` | khớp chính sách phiên bản của PRD §10.3 cho vết ghi — "bổ sung trường tùy chọn không tăng". Test (§7) buộc **mã** chỉ phát các khoá đã khai, nên nới ở lược đồ không cho phép mã tự thêm khoá lặng lẽ. **Q10.2** |

Chiều của tính đúng đắn: nguyên tắc "chặt với cái ta nhận, rộng với cái client phải nhận". Phong bì ở §3a đóng (`additionalProperties: false` — ta từ chối khoá lạ);
kết quả mở (client không được gãy vì ta thêm một trường).

**Một nơi cho một sự thật.** `result_schema(tool)` ngừng dựng dict bằng tay: nó **đọc `schemas/tool-result.v1.json`** (qua `neuroedge.paths.schema_path`) rồi ghim `tool` (và bỏ `$id`/`$schema` khi nhúng vào `outputSchema` của MCP). `Reason` và `ACTIONS` còn là
nguồn của mã; test (§7) đóng hai chiều giữa chúng và tệp. Nội dung kết quả vẫn do `ToolResult.content()` sinh — RFC không đổi một byte của nó.

### 3c. Khoá định danh phiên bản `board.v1`

Mọi tệp `boards/*.toml` hiện có phải hợp lệ nguyên văn, và cơ chế phải độc lập với những khoá RFC-0007, RFC-0010→0013 đang thêm vào `board.v1.json` (chỉ đụng đúng một khoá mới, `schema`, ở tầng gốc).

```toml
# Tầng gốc của boards/*.toml — dòng đầu tệp
schema = "neuroedge.board/v1"

[board]
id = "esp32s3-box-3"
…
```

```jsonc
// board.v1.json — thêm vào "properties" (không thêm vào "required")
"schema": {
  "description": "Schema version identifier. Absent means neuroedge.board/v1. Frozen at neuroedge.board/v1.",
  "type": "string",
  "const": "neuroedge.board/v1"
}
```

Luật (đề xuất; hiện trạng làm nền cho chúng — lược đồ mở, `to_document()` vứt khoá lạ — đã chạy thử, §9 F7):

1. **Tên và dạng giá trị theo gate:** khoá `schema`, giá trị `neuroedge.<loại>/v<chính>` (`neuroedge.gate/v1`). `$schema` kiểu vết ghi không dùng được cho TOML (khoá trần của TOML không bắt đầu bằng `$`).
2. **Tuỳ chọn trong `v1`:** vắng ⇒ coi là `neuroedge.board/v1`. Ba profile hiện có hợp lệ không đổi; PR hiện thực **thêm** dòng này vào ba tệp để ví dụ dạy đúng, và `BoardProfile.to_document()` phát nó ra.
   Từ `v2`, lược đồ của `v2` **bắt buộc** khoá này (với `const: neuroedge.board/v2`).
3. **Bộ đọc từ chối phiên bản lạ, trước khi thẩm định lược đồ.** `load_board_document` kiểm: có `schema` mà không thuộc tập hỗ trợ (`SUPPORTED_BOARD_SCHEMAS = {"neuroedge.board/v1"}`) ⇒ `BoardCapabilityError` (NE3001), ba phần, nêu
   giá trị đọc được, tập hỗ trợ, và "nâng cấp neuroedge". Kiểm **trước** thẩm định vì `board.v1.json` mở: thẩm định lược đồ v1 không bao giờ bắt được một tệp v2 — nó sẽ nhận tệp và bỏ qua khoá nó không biết. Đây là điều khoá `schema` mua được; nó không thay cho
   việc đóng lược đồ (Q10.6 nêu phần còn lại).
4. **Không phải số hiệu bản của một bo mạch.** `board.id` đã mang hậu tố của bo (`villa-panel-v2`, PRD Phụ lục C); `schema` là phiên bản của *định dạng khai báo*, không của phần cứng.
5. **`board.v1.json` thêm đúng khoá này.** Đã có một worker thêm khoá RFC-0007/0010→0013 vào cùng tệp; hai thay đổi chạm hai khoá khác nhau và hợp nhất được. Thứ tự hiện thực ở §8.

### 3d. Danh mục mã lỗi `NE*` dạng máy đọc được

Hai tệp, một nguồn sự thật.

**`schemas/error.v1.json`** — hình dạng của lỗi đã tuần tự hoá (`NeuroEdgeError.as_dict()`, `errors.py`; Studio và trang `sim` trả nó dưới `"error"`, `studio/server.py`, `sim/ui.py`). Đây là hình dạng **đầy đủ**; dạng lỏng hơn của `docs/spec/studio.md` (mục 8: `{"code"?, "where"?, "why", "how"?}`, và stub 501 chỉ có `why`) là hợp đồng riêng của API Studio, không thuộc lược đồ này (F12):

```json
{
  "$id": "https://schema.neuroedge.dev/error/v1.json",
  "type": "object",
  "required": ["code", "where", "why", "how"],
  "properties": {
    "code":  { "type": "string", "pattern": "^NE[0-9]{4}$" },
    "where": { "type": "string", "minLength": 1 },
    "why":   { "type": "string", "minLength": 1 },
    "how":   { "type": "string", "minLength": 1 },
    "principle": { "type": "string", "pattern": "^[1-5]$" },
    "reason":    { "type": "string" }
  },
  "allOf": [
    { "if": { "properties": { "code": { "const": "NE2003" } }, "required": ["code"] }, "then": { "required": ["principle"] } },
    { "if": { "properties": { "code": { "const": "NE1002" } }, "required": ["code"] }, "then": { "required": ["reason"] } }
  ],
  "$defs": { "catalog": { "…": "hình dạng của error-codes.v1.json, §bên dưới" } }
}
```

`code` là `pattern`, **không** `enum`: thêm một mã không đổi lược đồ này. `where`/`why`/`how` không rỗng là FR-DX-04; hôm nay `NeuroEdgeError.__init__` không cưỡng chế — PR hiện thực quét và sửa chỗ nào phát chuỗi rỗng (nếu có) trước khi
đóng băng. `principle` là **chuỗi** vì `GateInheritanceError.as_dict()` trả `str(self.principle)` dù thuộc tính là `int` (§9, F5): đóng băng cái đang chạy, không đổi.

**`schemas/error-codes.v1.json`** — danh mục, một tài liệu dữ liệu tự khai `"schema": "neuroedge.error-codes/v1"` và thẩm định theo `error.v1.json#/$defs/catalog`. Mỗi mục:

```json
{ "code": "NE1002", "name": "TokenReplayError", "parent": "ActionContractViolation", "status": "stable",
  "fields": ["reason"], "also_a": [], "aliases": [], "rfc": null, "since": "0.1" }
{ "code": "NE1003", "name": "EnvelopeRefusedError", "parent": "ActionContractViolation", "status": "reserved", "rfc": "RFC-0007" }
{ "code": "NE5001", "name": "PerceptionUnavailableError", "parent": "NeuroEdgeError", "status": "stable",
  "aliases": ["ProviderUnavailable", "MalformedResponse", "SpeechUnavailable"] }
{ "code": "NE0000", "name": "NeuroEdgeError", "parent": null, "status": "stable", "general": true }
```

Trường: `code` (duy nhất, **không bao giờ tái dùng**), `name` (lớp công khai trong `errors.py`), `parent`, `status` (`stable` · `reserved` — mã giữ chỗ cho lớp chưa có, như NE1003 của RFC-0007), `fields` (khoá thêm ngoài bốn khoá chung trong `as_dict()`),
`also_a` (lớp Python khác nó kế thừa — `ToolCallError` cũng là `ValueError`; chỉ SDK Python cần), `aliases` (lớp con dùng chung mã, `NE5001`), `general` (mã "không phân loại" — NE0000, NE2000: người nhận **không được** rẽ nhánh theo nó), `rfc`, `since`.
Hôm nay: 19 mục `stable` (NE0000, NE1001, NE1002, NE1004, NE2000→NE2003, NE3001→NE3003, NE4001→NE4004, NE5001) và 1 `reserved` (NE1003).

**Nguồn sự thật — quyết định đề xuất.** `schemas/error-codes.v1.json` là nơi **duy nhất** nói *mã nào tồn tại, tên lớp, quan hệ cha con, trạng thái*. Hai nơi kia được **kiểm** theo nó, không tự khai lại:

| Nơi | Giữ gì | Kiểm bằng |
|:---|:---|:---|
| `schemas/error-codes.v1.json` | định danh và cấu trúc: mã, lớp, cha, trạng thái, khoá thêm | *(là nguồn)* + tự thẩm định theo `error.v1.json#/$defs/catalog` |
| `python/neuroedge/errors.py` (và lớp con dùng chung mã) | hiện thực Python | test đóng hai chiều: mọi lớp `NeuroEdgeError` của gói ↔ một mục (hoặc `aliases`); `code`, `parent`, `fields` khớp; mục `reserved` không có lớp; mọi tên `name` nằm trong `neuroedge.__all__` (đã có `test_every_error_class_of_the_package_is_public`) |
| PRD Phụ lục B | **lời** (thời điểm, nguyên nhân, hành vi hệ thống — tiếng Việt, FR-DX-04) | test đóng hai chiều trên cặp (lớp, mã) của bảng ↔ danh mục; lời giữ nguyên ở PRD, không chép sang JSON |
| `targets/esp32s3/components/ne_gate/` | hai chuỗi `NE1001`, `NE1002` | test: mọi `NE\d{4}` trong `targets/` ⊂ danh mục |

Vì sao không để PRD hay `errors.py` làm nguồn: PRD là markdown tiếng Việt cho người đọc — dựng một dữ liệu công khai Apache-2.0 bằng cách phân tích bảng đó là mong manh, và nó không có cột cha/trạng thái; `errors.py` là mã PolyForm NC (`LICENSING.md`) nên một SDK Rust không được/không nên
sinh mã từ nó. Chi phí: `CONTRIBUTING.md` §8.1 hàng "Mã lỗi `NE…`" đổi nơi duy nhất từ PRD Phụ lục B sang danh mục này (PRD vẫn là nơi duy nhất của *lời*), và quy tắc 4 của mỗi slice ("lớp lỗi mới có mã ở PRD Phụ lục B và `errors.py`") thêm "và ở danh mục".

**Luật phiên bản của danh mục.** Thêm mã, hoặc thêm khoá `fields`/`aliases` ⇒ nới lỏng, cùng `v1`. Đổi nghĩa, đổi tên lớp, bỏ hay tái dùng một mã ⇒ phá vỡ, `v2`. Mã `reserved` chuyển thành `stable` khi lớp có mặt — không phải thay đổi phá vỡ.

### 3e. Thẩm định corpus theo lược đồ mới (tiêu chí ra 8)

- Mỗi `call` của 28 ca `fixtures/tool_calls/{valid,invalid}/` (thêm `id` rỗng) hợp lệ theo `tool-call.v1.json#/$defs/call`. Cả ca `invalid/`: *"không hợp lệ"* ở corpus nghĩa là không khớp `inputSchema` **của tool**, không phải hỏng phong bì (§3a) — một ca hỏng phong bì không còn là ca của corpus này mà là ca của `fixtures/contracts/`.
- `ToolResult.content()` của mỗi ca (kết quả thật, chạy qua `dispatch()` trên một `SimSession` mới, kể cả `fallback` lồng) hợp lệ theo `tool-result.v1.json`.
- `outputSchema` mà `neuroedge mcp serve` công bố cho mọi tool **bằng** `tool-result.v1.json` ghim `tool` (so từng tool của mọi agent trong `fixtures/agents/`).
- Bản ghi `tool_call` của vết ghi (`dispatch`) hợp lệ theo `#/$defs/call` — mà **không** sửa `trace.v1.json`.
- Vì corpus chỉ phủ 3/10 `reason` và 4/5 `source` (§2), phần phủ enum đến từ một corpus mới, **`fixtures/contracts/`** (§7): tài liệu nhỏ hợp lệ và không hợp lệ cho từng lược đồ (`tool-call`, `tool-result`, `error`, `board`), mỗi tệp một mục trong `expected_errors.yaml`, đóng hai chiều như mọi corpus khác
  (`CONTRIBUTING.md` §3). Test buộc các tệp `valid/` cùng nhau phủ **mọi** giá trị `status`, `on_block`, `source`, `reason` đã biết và mọi mã trong danh mục.
- PR hiện thực thêm vào `fixtures/tool_calls/` một ca `source: system_one` (PR thường, theo luật khép kín) để corpus phủ đủ năm nguồn.

### 3f. Phiên bản, đường dẫn, công bố

| Tệp | `$id` | Quy tắc |
|:---|:---|:---|
| `tool-call.v1.json` | `https://schema.neuroedge.dev/tool-call/v1.json` | PRD §10.3 / FR-GOV-02: đường dẫn `/v1`; thêm trường tuỳ chọn hoặc nới `enum` không tăng; đổi tên, bỏ, hoặc siết thì `v2` kèm thời gian chuyển tiếp (proposal §3.8 trụ cột 3) |
| `tool-result.v1.json` | `…/tool-result/v1.json` | như trên |
| `error.v1.json`, `error-codes.v1.json` | `…/error/v1.json`, `…/error-codes/v1.json` | như trên; luật riêng của danh mục ở §3d |
| `board.v1.json` | không đổi | khoá `schema` ở §3c |

PR hiện thực thêm bốn dòng vào ma trận PRD §10.3. `$id` khớp để TSK-I6-02 chỉ còn phục vụ tệp; RFC không làm việc đó. Giấy phép: `schemas/` là Apache-2.0 (`LICENSING.md`); bốn tệp mới thuộc về đó. **Corpus** thì chưa (§9, F3, Q10.4).

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | **Có**, kể cả ba `boards/*.toml` (khoá `schema` tuỳ chọn) và mọi gate, vết ghi. Một tệp bo mạch có khoá `schema` mang giá trị khác `neuroedge.board/v1` — hôm nay hợp lệ vì lược đồ mở — **sẽ không hợp lệ**: đây là siết lỏng về hình thức. Không có trong kho (`grep '^schema' boards/` rỗng) và khoá không được tài liệu hoá ở đâu, nên coi là chấp nhận được; **cần kỹ thuật trưởng ký rõ điều này** (Q10.5) |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Kết quả của tool: `reason` ngoài `Reason` hiện tại và khoá thừa trước đây vi phạm `outputSchema` đóng, nay hợp lệ (§3b) — nới lỏng, chủ ý. Phần còn lại không có |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | **Không.** Bốn lược đồ mới sinh ra ở `v1`; `board.v1` chỉ thêm một khoá tuỳ chọn |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không: `trace.v1.json` và `fixtures/traces/` không đổi |
| Gate nào trong `digests.lock` đổi digest? | Không |
| Bố cục `NETR` hoặc walker C phải đổi? | Không |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không đổi đáp án nào; **thêm** một ca `system_one` và một mục (§3e) |
| `python/tests/test_schemas.py` | Đổi: tập tên đúng ba tệp ⇒ đúng bảy tệp (`SCHEMA_IDS` thêm bốn); mạnh hơn, không yếu hơn — vẫn khoá tập tên, vẫn kiểm `$id` và `$schema` |
| API Python công khai (`python_api.md`) | `result_schema` không phải tên công khai; `ToolCall`, `ToolResult` không đổi hình dạng. `BoardProfile.to_document()` thêm một khoá; `load_board*` ném `NE3001` thêm cho phiên bản lạ (bổ sung, MINOR theo `python_api.md` §3) |
| CLI | Không đổi |

## 5. Ảnh hưởng an toàn

RFC không đụng `gate.v1`, ngữ nghĩa phân giải hay đường tới HAL; không gate nào trở nên lỏng hơn, không nguyên tắc B.5 hay mặc định fail-closed bị đổi. Bốn điểm cần soi:

1. **Phong bì đóng, nguồn do runtime.** `$defs/request` không có `source` và `additionalProperties: false`, nên một bộ thẩm định đặt ở cửa nhận (`#/$defs/request`) **từ chối** lời gọi tự khai `source` ở mức phong bì, cùng hướng với `REJECTED` hôm nay
   (`caller_declares_call_source.yaml` là ca tham số, không phải ca phong bì — hai tầng bảo vệ). `source` chỉ có ở `#/$defs/call`, phong bì đã gán.
2. **Nới kết quả không nới quyền.** `tool-result` mô tả đầu ra; một client coi `reason` lạ dưới `BLOCK` là bị chặn không thể biến `BLOCK` thành `ALLOW`. Luật của client được ghi ở `tool_calling.md` §4 khi hiện thực: *"`status` quyết định; `reason` chỉ là lời giải thích — không bao giờ rẽ nhánh ALLOW theo `reason`"*.
3. **Bộ đọc bo mạch từ chối phiên bản lạ (fail-closed).** Hôm nay một runtime cũ đọc bo mạch mới bỏ qua mọi khoá nó không biết. Khoá `schema` chỉ cứu được qua ranh giới **phiên bản chính**; khoá thêm *trong* `v1` (như `envelope` của RFC-0007) mà bộ đọc cũ không hiểu vẫn bị bỏ qua. Đó là lỗ hổng có thật nằm ngoài RFC này — Q10.6.
4. **Danh mục mã lỗi.** Mã `reserved` ngăn một SDK dùng lại NE1003. Không đổi hành vi lỗi nào. Thiết bị chỉ phát `NE1001`/`NE1002`; test `targets/` ⊂ danh mục giữ điều đó.

Câu trả lời cho "có đường nào làm gate lỏng hơn?": **không**. Phê duyệt kỹ thuật trưởng vì phạm vi `schemas/` và `board.v1`, không vì an toàn gate.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Một tệp `tool-profile.v1.json` chứa cả phong bì lẫn kết quả | Hai bên đọc khác nhau (runtime nhận phong bì, client kiểm kết quả — và SDK MCP đã kiểm `outputSchema` theo từng tool); hai `$id` cho phép `$ref` độc lập và tăng phiên bản độc lập. Không phải ý kiến mạnh: Q10.7 |
| Chép nguyên `result_schema()` (kết quả đóng, `reason` là `enum`) | Mỗi `Reason` hay trường mới là `v2` cho mọi client; `Reason` đã lớn hai lần trong mười ngày. Bị bác ở §3b, nhưng là quyết định sản phẩm — Q10.1, Q10.2 |
| Định danh phiên bản bo mạch bắt buộc ngay ở `v1` | Phá ba tệp hiện có và mọi bo mạch người dùng tự viết (số này không biết): vi phạm quy tắc "tệp đang hợp lệ phải còn hợp lệ" của mẫu RFC |
| Khoá `$schema` (URL) như vết ghi, hoặc `[board] schema`/`version` | `$schema` không là khoá trần của TOML; lồng vào `[board]` khiến bộ đọc phải đọc một bảng trước khi biết phiên bản. Gốc + dạng `neuroedge.<loại>/v<n>` theo gate nhất quán nhất |
| Đóng `board.v1.json` (`additionalProperties: false`) để bắt khoá lạ | Siết lỏng: tệp có khoá lạ hôm nay hợp lệ sẽ gãy ⇒ `v2`. Ngoài phạm vi "khoá định danh"; Q10.6 |
| Danh mục mã lỗi sinh **từ `errors.py`** (mã là nguồn) | `errors.py` mang giấy phép PolyForm NC và không có cột trạng thái (`reserved`), cha-con của lớp dùng chung mã, `general`. Mất "nơi duy nhất" khi một SDK Rust muốn đóng góp mã |
| Danh mục **trích từ bảng PRD Phụ lục B** (PRD là nguồn) | PRD là hợp đồng dạng chữ, không có cấu trúc; phân tích markdown để sinh dữ liệu công khai là mong manh và buộc mọi thay đổi định dạng bảng thành thay đổi hợp đồng. PRD giữ **lời**, danh mục giữ **cấu trúc** |
| Nhét danh mục vào `error.v1.json` (một tệp, `oneOf` theo mã) | SDK muốn một mảng để lặp; `oneOf` 20 nhánh khó sinh mã và trộn hai mục đích (thẩm định một lỗi ↔ liệt kê mã). Hai tệp, một nguồn |
| `code` của `error.v1.json` là `enum` các mã | Mỗi mã mới là sửa lược đồ. `pattern` + danh mục tách bạch hai việc |
| Đưa `agent.toml` và `fixtures/tool_calls/expected_results.yaml` vào `schemas/` | `agent.toml` ngoài `schemas/` đã chốt (`tool_calling.md` §9, Q-63). Định dạng ca và đáp án của corpus: hoãn cùng TSK-I6-02 — Q10.4 |
| Đóng băng cả schema JSON của cây quyết định | Đã loại ở Q-63: hợp đồng thật là bố cục byte `NETR` (RFC-0003, RFC-0009) |

## 7. Bằng chứng kiểm chứng

Test dưới đây là **tên đề xuất** — chưa tồn tại tới khi RFC được chấp thuận. Cột "có sẵn" là test hiện hành sẽ còn xanh.

- [ ] Ví dụ hợp lệ đã thêm vào `fixtures/`: `fixtures/contracts/<tool-call|tool-result|error|board>/valid/` — phủ mọi `status`, `on_block`, `source`, `reason` đã biết, `fallback` lồng hai tầng, mọi mã trong danh mục; một ca `source: system_one` ở `fixtures/tool_calls/valid/`
- [ ] Ví dụ sai kèm đáp án (`fixtures/contracts/expected_errors.yaml`, khép kín hai chiều): phong bì có `source` ở `request`; `name` rỗng; `arguments` là mảng; `source` ngoài năm giá trị; kết quả `BLOCK` thiếu `gate`; `REJECTED` thiếu `problems`; `status` ngoài ba giá trị; lỗi `NE2003` thiếu `principle`; `code` sai dạng; bo mạch có `schema: neuroedge.board/v2`
- [ ] Test tự động:
  - `test_every_tool_call_corpus_case_validates_against_the_tool_call_schema` *(tiêu chí ra 8)*
  - `test_every_tool_call_corpus_result_validates_against_the_tool_result_schema`
  - `test_the_published_output_schema_of_every_tool_is_the_frozen_result_schema_pinned_to_its_name`
  - `test_a_recorded_tool_call_event_validates_against_the_envelope_schema`
  - `test_the_tool_call_schema_and_the_dataclass_agree` (`ToolCall` fields, `SOURCES`, `CASE_KEYS`/`CALL_KEYS` của `tool_corpus.py`)
  - `test_the_known_reasons_of_the_schema_are_exactly_the_Reason_enum` · `test_the_on_block_enum_is_the_gate_schemas`
  - `test_the_mcp_server_emits_only_documented_result_keys` (khoá chặn lỗi "nới ở lược đồ cho phép mã tự thêm khoá")
  - `test_the_error_catalog_and_errors_py_agree_both_ways` · `test_every_error_class_of_the_package_has_a_catalog_entry` · `test_the_prd_error_table_and_the_catalog_agree_on_class_and_code` · `test_every_error_code_in_targets_is_in_the_catalog` · `test_a_reserved_code_has_no_class`
  - `test_every_serialised_error_validates_against_the_error_schema` (chạy mọi lớp lỗi với dữ liệu mẫu; bắt chuỗi rỗng)
  - `test_a_board_with_a_schema_key_of_another_version_is_refused_before_validation` · `test_a_board_without_a_schema_key_is_read_as_v1` · `test_every_shipped_board_declares_its_schema` · `test_board_to_document_round_trips_the_schema_key`
  - `test_schemas_directory_holds_exactly_the_seven_frozen_schemas` (đổi từ "ba")
- [ ] `neuroedge gate lint` và `neuroedge verify` vẫn xanh; `scripts/wheel_smoke.sh` chạy trên bản cài (`schemas/` đã đi vào wheel nguyên thư mục qua `hatch_build.py`, thêm `schemas/tool-result.v1.json` vào danh sách tệp nó kiểm)
- Có sẵn, vẫn xanh: `test_tool_corpus.py::test_an_mcp_client_gets_the_same_result_and_its_sdk_accepts_it`, `test_every_case_has_an_expectation_and_every_expectation_a_case`, `test_public_api.py::test_every_error_class_of_the_package_is_public`

## 8. Việc phải làm khi chấp thuận

Thứ tự đề xuất — hai PR hiện thực vì `board.v1.json` đang bị một worker khác sửa và roadmap xếp TSK-I6-05 sau I2a (§0.3 mục 5: "`board.v1` đóng băng khi đủ khoá"):

**PR A — phần không đụng `board.v1.json` (làm được ngay sau chấp thuận):**

- [ ] Thêm `schemas/tool-call.v1.json`, `tool-result.v1.json`, `error.v1.json`, `error-codes.v1.json`; sửa `test_schemas.py`
- [ ] `actions/tools.py::result_schema` đọc tệp tĩnh; thêm ca `system_one`; `fixtures/contracts/` và `expected_errors.yaml`; các test ở §7
- [ ] Cập nhật `docs/spec/tool_calling.md`: §1 và §4 dẫn lược đồ (không chép lại); §2 thêm khoá `__unparseable__`; §4 luật "không rẽ nhánh theo `reason`"; §9 đoạn cuối ("đóng băng thành `schemas/` bằng một RFC…") thành hiện thực; đóng `TODOS.md` #23
- [ ] Cập nhật `neuroedge-prd.md`: ma trận §10.3 (thêm bốn lược đồ và khoá `schema` của bo); đầu Phụ lục B (nêu danh mục là nguồn của cấu trúc; PRD giữ lời; thêm dòng NE0000, NE2000 và ghi chú lớp con của NE5001, NE1003 `reserved`); quyết định mới nếu có thì cấp `Q-N`
- [ ] Cập nhật `CONTRIBUTING.md` §8.1 hàng "Mã lỗi `NE…`" và §3 (thêm bốn lược đồ vào dòng "Sửa `schemas/*.json`" nếu cần); `docs/spec/python_api.md` §1 (hợp đồng dạng tệp: thêm bốn lược đồ)
- [ ] `docs/architecture/{vi,en}/07-data-contracts.md`: danh mục lược đồ; nếu `error-codes` đọc từ mã Python thì kiểm cạnh phụ thuộc ở `tests/test_architecture_layers.py` và `03-component-host-c4l3.md` (không có cạnh mới nếu chỉ test đọc tệp)

**PR B — `board.v1.json` (sau khi RFC-0007, 0010→0013 hiện thực xong phần khoá của chúng):**

- [ ] Thêm khoá `schema` vào `schemas/board.v1.json`; `SUPPORTED_BOARD_SCHEMAS` và kiểm trước thẩm định ở `hal/board.py`; dòng `schema = "neuroedge.board/v1"` vào ba `boards/*.toml`; `to_document()`; các test board ở §7

**Chung:**

- [ ] Một mục `CHANGELOG.md` `[Chưa phát hành]` cho mỗi PR; tiến độ ở roadmap TSK-I6-05 (một mình PR A không đóng task); tiêu chí ra 8 chỉ tick khi cả hai PR xong
- [ ] Cập nhật dòng RFC-0015 trong `docs/rfc/README.md`
- [ ] Không đụng `digests.lock` (không gate nào đổi)

## 9. Phát hiện khi đối chiếu đặc tả, corpus và mã

Đã kiểm bằng cách chạy mã hoặc đọc đúng dòng; không phải suy đoán.

| # | Phát hiện | Nơi |
|:---:|:---|:---|
| F1 | Lược đồ kết quả hôm nay **đóng** (`additionalProperties: false`, `reason` là `enum`) và SDK MCP phía client kiểm nó; đóng băng nguyên dạng làm mỗi `Reason` mới thành `v2`. `Reason` đã lớn qua RFC-0005 (`argument_out_of_range`, 2026-09-24) và RFC-0009 (`value_out_of_range`, 2026-10-02) | `actions/tools.py::result_schema`, `engine/verdict.py::Reason`; §3b |
| F2 | Corpus 28 ca chỉ phủ 3/10 `reason` và 4/5 `source` (không `system_one`) — "corpus thẩm định theo lược đồ" chưa chứng minh phần enum | `fixtures/tool_calls/`; §3e |
| F3 | **Giấy phép:** `fixtures/tool_calls/` (và `fixtures/traces/`) không nằm ở hàng Apache-2.0 của `LICENSING.md` (chỉ `schemas/`, `docs/spec/`, `fixtures/compliance/` — nơi chỉ có `voice/`), trong khi `tool_calling.md` §9 gọi corpus này là chuẩn tuân thủ và Q-58 đòi bề mặt tích hợp "nằm ở phần Apache-2.0 (lược đồ, đặc tả, bộ kiểm tuân thủ)". Hôm nay một OSS khác chạy corpus là dùng mã/tệp PolyForm NC | `LICENSING.md`; Q10.4 |
| F4 | PRD Phụ lục B nói tên lớp và mã "khớp `errors.py`; mọi lớp kế thừa `NeuroEdgeError`", nhưng `errors.py` có `NE0000` (lớp gốc) và `NE2000` (`GateError`) không có hàng ở PRD; ba lớp con dùng chung `NE5001` (`ProviderUnavailable`, `MalformedResponse`, `SpeechUnavailable`) không có hàng; NE1003 được nhắc nhưng chưa lớp nào (RFC-0007 đã chấp thuận, chưa hiện thực). **36 chỗ** dựng trực tiếp `NeuroEdgeError(...)` và phát `NE0000` (`grep` ngoài `errors.py`, bỏ dòng chú thích: `cli/` 17, `studio/` 9, gốc 4, `engine/` 2, `sim/` 2, `testing/` 2), cộng lớp riêng `engine/firmware.py::_Refused` cũng mang `NE0000` — mã "chung", không rẽ nhánh được | `errors.py`, PRD Phụ lục B; §3d |
| F5 | `GateInheritanceError.as_dict()["principle"]` là **chuỗi** (`str(self.principle)`) dù thuộc tính là `int` và corpus gate ghi `principle: 2` (số) | `errors.py`; §3d |
| F6 | `trace.v1.json` có `$schema` bắt buộc nhưng chỉ `format: uri`, **không ghim** — định danh phiên bản của vết ghi do mã ghi, không do lược đồ cưỡng chế (gate thì `const`) | `schemas/trace.v1.json`; Q10.10 |
| F7 | `board.v1.json` mở ở cả gốc lẫn `board`/`capabilities`; chạy thử: tài liệu có `schema: "rác"` và `nonsense: 1` hợp lệ, và `to_document()` vứt hai khoá đó | `hal/board.py`; §1, §3c |
| F8 | `parse_tool_calls` chèn khoá `__unparseable__` vào `arguments` khi JSON của nhà cung cấp hỏng; hành vi có test (`test_tools.py`, `test_providers.py`) nhưng **không có trong `tool_calling.md`** | `actions/tools.py`; §3a |
| F9 | `ToolCall.source` có mặc định `"test"` trong dataclass, trong khi §1 của spec nói `source` "do runtime gán": một người gọi Python quên `source` nhận `test` thay vì lỗi. (Gate nào không liệt kê `test` thì chặn — an toàn, nhưng spec không nói mặc định này) | `actions/tools.py`; §3a |
| F10 | `tool_calling.md` §8/§8.1 (mạng) chỉ có trên nhánh `feat/mcp-network`; nền của RFC này (`87db7c7`) chưa có | §3a |
| F11 | `test_schemas_directory_holds_exactly_the_three_frozen_schemas` phải đổi; không ai quên được vì nó đỏ | `tests/test_schemas.py`; §4 |
| F12 | `docs/spec/studio.md` (mục 8) cho phép lỗi API Studio chỉ có `why` (`code`, `where`, `how` tuỳ chọn) và `studio/server.py` trả `{"why": "not implemented yet"}` cho stub 501 — hai hình dạng "lỗi" cùng gọi là `as_dict()`-shaped; `error.v1` chỉ nhận hình dạng đầy đủ | `docs/spec/studio.md`, `studio/server.py`; §3d |

## 10. Câu hỏi mở cho chủ sản phẩm và kỹ thuật trưởng

RFC này **không** quyết các câu này; mỗi câu kèm khuyến nghị để người quyết có điểm xuất phát.

| # | Câu hỏi | Khuyến nghị |
|:---:|:---|:---|
| Q10.1 | `reason` của kết quả: `enum` đóng (mỗi `Reason` mới = `v2`) hay chuỗi mở kèm danh sách đã biết và luật "`status` quyết định, không rẽ nhánh ALLOW theo `reason`"? | Mở (§3b). Chi phí: validator không bắt được lỗi gõ ở phía ta — test hai chiều với `Reason` bù |
| Q10.2 | Đối tượng kết quả (gốc, `fallback`, `confirmation`) `additionalProperties` mở hay đóng? | Mở, kèm test mã chỉ phát khoá đã khai |
| Q10.3 | Đưa `inputSchema` (tập con JSON Schema) và mô tả tool (`tools/list`) vào `tool-call.v1.json`, hay chỉ phong bì và kết quả theo chữ của roadmap? | Đưa vào — người hiện thực Profile cần nó để biết "khớp `inputSchema`" (ranh giới `valid/` – `invalid/`) |
| Q10.4 | **Giấy phép corpus (F3):** đưa `fixtures/tool_calls/` (và `fixtures/agents/` nó dùng, `fixtures/traces/`) vào hàng Apache-2.0 của `LICENSING.md` / chuyển sang `fixtures/compliance/`? Có đưa định dạng ca (`CASE_KEYS`) và `expected_results.yaml` thành lược đồ không (hoãn cùng TSK-I6-02)? | Việc của chủ sản phẩm + người giữ giấy phép (Q-45, Q-59); không phải việc kỹ thuật. RFC này không đổi giấy phép |
| Q10.5 | Khoá `schema` của bo mạch: tuỳ chọn ở `v1` (đề xuất) hay bắt buộc? Và chấp nhận siết hình thức "bo mạch mang `schema` khác `v1` giờ bị từ chối" (§4)? | Tuỳ chọn; kỹ thuật trưởng ký điểm siết |
| Q10.6 | Khoá thêm *trong* `v1` mà bộ đọc cũ không hiểu (vd `envelope`, RFC-0007) vẫn bị bỏ qua lặng lẽ (§5.3). Có cần cơ chế "khoá bắt buộc hiểu" cho bo mạch (vd `requires = ["envelope"]`) và/hoặc đóng `board.v1.json`? | RFC riêng, vì chạm an toàn phần cứng và siết lược đồ; không chặn RFC này |
| Q10.7 | Một tệp `tool-profile` hay hai (`tool-call`, `tool-result`)? Có thêm `tool` ở tệp thứ ba? | Hai tệp (§6) |
| Q10.8 | Danh mục mã lỗi là nguồn của *cấu trúc*, PRD giữ *lời* (§3d) — đồng ý đổi `CONTRIBUTING.md` §8.1? | Đồng ý |
| Q10.9 | `NE0000`/`NE2000` là mã "chung" và 36 chỗ dựng `NE0000` (F4): cấp mã riêng cho các lỗi đó **trước** khi đóng băng (SDK khác rẽ nhánh được), hay đóng băng `general` và để sau? | Để sau; RFC này chỉ ghi `general: true` và hứa không rẽ nhánh |
| Q10.10 | Ghim `$schema` của `trace.v1.json` bằng `const` (F6)? Là siết lỏng (tệp có `$schema` khác hôm nay hợp lệ) — thuộc RFC riêng về `trace.v1` | RFC riêng, nếu muốn |
| Q10.11 | Sau này một gate có thể cần cấm riêng cửa mạng hay một thiết bị. Có dự trù giá trị `source` mới (vd `mcp_network`) trong `v1` để khỏi RFC phá vỡ? | Không dự trù; làm khi có nhu cầu, vì mỗi giá trị đi vào `NETR` (chỉ số `choice`) |
| Q10.12 | Lỗi hợp đồng (NE1001/NE1002) đi qua MCP là lỗi JSON-RPC; có đưa đối tượng `error.v1` vào `error.data` cho client mạng không? | Ngoài phạm vi; ghi nhận. Cần RFC về hành vi MCP |
| Q10.13 | Thứ tự: chấp thuận RFC này trước khi RFC-0007, 0010→0013 hiện thực xong, hay đợi (§8 PR B phụ thuộc chúng)? | Chấp thuận sớm, tách hai PR hiện thực |
