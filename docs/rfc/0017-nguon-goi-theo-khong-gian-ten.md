# RFC-0017: Nguồn gọi theo không gian tên (`bridge:<id>`) và danh tính client

| | |
|:---|:---|
| **Mã RFC** | 0017 |
| **Tiêu đề** | `source` của `ToolCall` thành không gian tên: `bridge:<id>` do lõi gán theo bridge đã nạp, `mcp:<client>` cho client mạng đã đặt nhãn, và dữ kiện dẫn xuất `call_channel` để một gate nói "mọi bridge" — TSK-I2c-03 (mã: TSK-I2c-10) |
| **Hợp đồng bị ảnh hưởng** | `schemas/tool-call.v1.json` *(nới `$defs/source` từ `enum` năm giá trị thành `anyOf` enum ∪ mẫu, §3a)* · hợp đồng `call_source` của `docs/spec/tool_calling.md` §1, §5 và bảng §2b của `docs/spec/threat_model.md` · khối `[mcp.clients]` của `agent.toml` *(ngoài `schemas/`; kiểm ở `neuroedge build` và lúc nạp agent, §3c)* · **không** đụng `gate.v1`, ngữ nghĩa phân giải, `trace.v1`, `board.v1`, bố cục `NETR`, `digests.lock`, ba vết ghi chuẩn mực (§4) |
| **Yêu cầu PRD liên quan** | FR-ACE-09, FR-MDL-10, FR-EXT-02, FR-EXT-03, NFR-SEC-09, NFR-SEC-10 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-10-04 |
| **Trạng thái** | 🟡 Đang thảo luận *(bản nháp: ở danh mục `docs/rfc/README.md` là ⏳ Nháp tới khi mở PR RFC riêng; chấp thuận là chữ ký của kỹ thuật trưởng, quyết định nền đã có ở Q-67)* |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (sửa `schemas/tool-call.v1.json`; mở một đường danh tính vào cổng an toàn; đảo một quyết định đã ký). **Chủ sản phẩm** cho các câu hỏi mở ở §9 |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3 — sửa `schemas/*.json` (`tool-call.v1.json`). Hợp đồng `call_source` còn do `docs/spec/tool_calling.md` §5 khoá:
> *"thêm một giá trị vào danh sách nguồn … cần RFC"*. Task: **TSK-I2c-03** (RFC này), mã **TSK-I2c-10**. Quyết định nền: `neuroedge-prd.md` §15
> **Q-67 D2** — mở `source` thành không gian tên. **RFC này đảo [RFC-0015](0015-hop-dong-cho-nguoi-tich-hop.md) §10 câu 11** (*"Không dự trù giá trị `source`
> mới (như `mcp_network`) … chỉ thêm khi có nhu cầu"*): nhu cầu nay đã có và đã được chốt. Khớp với RFC-0014 (nguồn ngoài, danh tính logic), RFC-0016 (`Guard`, `Dispatcher`, bộ nạp plugin). Mọi khẳng định về mã đã đối chiếu với kho tại `7a43d93`; điều chưa kiểm ghi rõ "chưa kiểm".

## 1. Vấn đề

`source` của tool call là tập đóng năm giá trị, ở ba nơi giữ khớp nhau: `SOURCES` (`python/neuroedge/actions/tools.py:42`), `ToolCall.__post_init__` ném `ToolCallError`
NE1004 cho giá trị lạ (`tools.py:56-62`) và `enum` của `schemas/tool-call.v1.json:22-25`. Một bridge (Muse, Home Assistant, xiaozhi — Q-67) là mã của bên thứ ba dịch giao thức ngoài thành
`ToolCall`. Hôm nay nó có hai lựa chọn, cả hai đều sai:

1. **Mượn một nguồn có sẵn** — `mcp` hay, tệ hơn, `local_grammar`. Gate không phân biệt được Muse với Home Assistant với một client MCP, và một bridge nói "tôi là `local_grammar`" là đúng điều
   `tool_calling.md` §5 cấm. Giá trị chỉ do lõi gán.
2. **Chờ đội lõi thêm một giá trị cho mỗi sản phẩm** — mỗi giá trị là một RFC, một `SOURCES`, một bản phát hành. Đó chính là điều Q-67 muốn bỏ.

Client MCP qua mạng cũng cùng một lỗ: token đã xác thực mang `sub` bắt buộc và ràng buộc chứng chỉ (`mcp_http.py:332-346`), nhưng `build_app` dựng một `build_server(session)` duy nhất với nguồn
`mcp` (`mcp_http.py:432-434`, `mcp_server.py:75-100`), nên danh tính không bao giờ tới `dispatch()`. `threat_model.md` §2b (mục *"Ranh giới tin cậy của `mcp serve --http`"*) ghi đúng giới hạn này: *"Mọi lời gọi qua mạng, thiết bị nào cũng
vậy, là `call_source = mcp`; gate không cấm riêng được một thiết bị hay riêng cửa mạng …"*.

Đã chạy: `ToolCall("light_on", source="bridge:muse")` ném `ToolCallError` NE1004, *"'bridge:muse' is not a tool-call source"* (cùng loại ca của `python/tests/test_public_api.py:178`).

## 2. Vì sao hiện trạng không giải quyết được — và tiền đề của RFC-0015 §10 câu 11

RFC-0015 giữ tập đóng với lý do *"mỗi giá trị đi vào `NETR` dưới dạng chỉ số `choice`"* (§3a, §10 câu 11). Đã kiểm lại tiền đề đó; nó đúng một nửa:

| Điều kiểm | Kết quả | Nơi |
|:---|:---|:---|
| Giá trị `choice` **ngoài** `options` của gate thì sao? | `BLOCK`, `criterion_unavailable`, `failed_criterion` là chính tiêu chí. Dưới `fail: open` vẫn `BLOCK` (`known_failure` phân loại lại dữ kiện **có mặt**). Đã chạy: gate liệt kê `bridge:muse`, `call_source = bridge:other` ⇒ `BLOCK criterion_unavailable`; `mqtt:x` ⇒ cùng kết quả | `engine/decision_tree.py:260-261`, `:497-522` |
| Chỉ số trong `NETR` là chỉ số toàn cục? | **Không.** Là vị trí trong `sorted(options)` **của chính gate đó** (`_domain`); chuỗi duy nhất vào bảng chuỗi là các `options` của gate. Walker C coi `!in_domain` là `criterion_unavailable`; bảng chân trị đã có hàng "ngoài miền" cho mọi nút không phải số (`bool`, `level`, `choice`). Một nguồn mới không đổi byte nào của `NETR` cho tới khi một gate **liệt kê** nó (khi đó digest của chính gate đó đổi, như mọi sửa gate) | `decision_tree.py:42-50`, `:440`; `binary_tree.py:33-36`, `:49` (`LAYOUT_VERSION = 2`); `ne_walker.c:413`; `targets/esp32s3/components/ne_agent/ne_agent.c:39` |
| `gate.v1` có chặn một `option` như `bridge:muse` không? | Không: `items` là `string`, không `pattern`, không `maxLength`. YAML đọc `bridge:muse` thành chuỗi. Đã chạy: gate như trên qua `resolve_gate_file`, `compile_tree`, `binary_tree.encode` | `schemas/gate.v1.json:52-58` |
| Giới hạn thật của việc liệt kê nguồn trong gate? | Tối đa **32** giá trị mỗi miền (`admitted_mask` là `u32`); vượt ⇒ `GateSchemaError` NE2002 lúc build. Không liệt kê nổi "mọi bridge", và không ai biết trước id bridge lúc viết gate | `binary_tree.py:57`, `:217` |
| Đường xác nhận `ask` có giữ nguồn không? | Có: câu hỏi lưu `call_source` gốc và `confirm()` lượng giá lại với nó. Một dữ kiện dẫn xuất mới **phải** sống qua đường này, nếu không câu trả lời "có" luôn `BLOCK` | `actions/conversation.py:131-133`, `:193-196` |
| Vết ghi ràng buộc `source`? | Không: `tool_call.source` và `gate_facts.call_source.value` là chuỗi tự do trong `events[].data` | `docs/spec/tool_calling.md` §7 (đoạn sau bảng sự kiện); `schemas/trace.v1.json` không có khoá `source` |
| Gate đã khoá nào đổi? | Không: không gate nào liệt kê giá trị mới | `digests.lock` |

Vậy phần RFC-0015 đúng là *"cần RFC"* và *"đổi hợp đồng `call_source` của gate"*; phần sai là *"đi vào `NETR`"*: chi phí ở `NETR` bằng không. Luật nới `enum` không tăng `v1` đã có
(PRD §10.3, hàng "Lược đồ tool call"; RFC-0015 §3f).

## 3. Thay đổi đề xuất

### 3a. Văn phạm của `source`

| Dạng | Họ (`call_channel`) | Ai gán, từ đâu | Hôm nay |
|:---|:---|:---|:---:|
| `local_grammar` | `local_grammar` | ngữ pháp lệnh khớp `commands.toml` (`sim/session.py:1447`) | có |
| `system_one` | `system_one` | dành sẵn; ngoài corpus và test, **không nơi nào dựng** `ToolCall` với nó | có |
| `system_two` | `system_two` | kết nối MCP in-process `build_server(source="system_two")` (`mcp_host.py:207`), `parse_tool_calls` (`sim/session.py:1649`) | có |
| `mcp` | `mcp` | `neuroedge mcp serve` qua stdio; client mạng **chưa** đặt nhãn (§3c) | có |
| `mcp:<client>` | `mcp` | lõi, từ `sub` của token đã xác thực qua bảng `[mcp.clients]` (§3c) | mới |
| `bridge:<id>` | `bridge` | lõi, từ id đã khoá của bridge đã nạp (§3b) | mới |
| `test` | `test` | CI | có |

`<id>` khớp `[a-z][a-z0-9_]{0,31}` — đúng mẫu `source_id` của RFC-0014 §3c: chữ thường, số, gạch dưới; không gạch ngang, không chấm; chuỗi `source` dài tối đa 39 ký tự. Họ ngoài `bridge` và `mcp` ⇒
`ToolCallError` (NE1004) lúc dựng. **Tập dựng sẵn vẫn đóng:** thêm họ hay giá trị dựng sẵn vẫn là RFC. Lưu ý cho `TSK-N6-01` (`call_source = "trigger"`, mục TSK-N6-01 của `roadmap/neuroedge-roadmap.md`): mục đó viết rằng
không cần RFC vì `SOURCES` *"không nằm trong `schemas/`"*; sau RFC-0015 điều đó không còn đúng, `trigger` là giá trị dựng sẵn thứ sáu và sửa enum ⇒ RFC (RFC này không thêm nó).

```json
// trước — schemas/tool-call.v1.json:22-25
"source": { "description": "Where the call came from. Assigned by the runtime from the connection (tool_calling.md §5); never the caller's to state.",
            "enum": ["local_grammar", "system_one", "system_two", "mcp", "test"] }

// sau — $defs/request không đổi: vẫn không có `source`, additionalProperties: false (dòng 26-36)
"source": { "description": "Where the call came from. Assigned by the runtime — from the connection, a bridge's registration or the verified client — never the caller's to state (tool_calling.md §5). A built-in name, or `bridge:<id>` / `mcp:<client>`.",
            "type": "string",
            "anyOf": [ { "enum": ["local_grammar", "system_one", "system_two", "mcp", "test"] },
                       { "pattern": "^(bridge|mcp):[a-z][a-z0-9_]{0,31}$" } ] }
```

Đã chạy thử với `jsonschema`: `bridge:muse`, `mcp:hub` hợp lệ; `mcp_network`, `mqtt:muse`, `bridge:`, `bridge:neuroedge-muse`, `bridge:Muse`, `local_grammar:x` và id 33 ký tự không hợp lệ. **Một cạm bẫy đã gặp:** `$` của
Python khớp *trước* một `\n` cuối, nên `jsonschema` (Python) nhận `bridge:muse\n`, còn ECMA 262 thì không. Mã **phải** kiểm bằng `re.fullmatch`, không `re.search`; ca đó test ở mã, không đặt vào `fixtures/contracts/`.

Mã (`actions/tools.py`): `SOURCES` giữ năm giá trị dựng sẵn; thêm `SOURCE_ID`, `valid_source()`, `source_channel()`; `ToolCall.__post_init__` và `testing/tool_corpus.py:138` dùng `valid_source`; lời nhắc của NE1004 liệt kê
năm tên và hai không gian tên.

### 3b. Bridge: id và kênh

Hình dạng API của bridge là việc của RFC-0016 (§3b: `Dispatcher.dispatch(ToolRequest)`; `Guard` đăng ký id và dựng `ToolCall` bên trong); RFC này chỉ khoá bốn bất biến về nguồn:

1. **Id là tên entry point** trong nhóm bridge, khớp `[a-z][a-z0-9_]{0,31}` (gói `neuroedge-muse` khai entry point `muse`). Không khớp ⇒ **không khởi động**, lỗi ba phần; mã lỗi nạp do RFC-0016 cấp, RFC này không thêm mã.
2. **Trùng id ⇒ không khởi động** (hai gói cùng tên entry point, dù khác đích). Không có luật "gói sau thắng" hay "gói trước thắng": một bridge không chiếm được danh tính của bridge khác bằng thứ tự nạp.
3. **Nguồn chỉ do lõi gán.** Bridge nhận một `Dispatcher` gắn cứng id lúc nạp (RFC-0016 §3b); `ToolRequest` của nó là `tool-call.v1#/$defs/request` — **không có trường `source`** để nói. Lõi dựng `ToolCall` với `source = "bridge:<id>"` bên trong, và không có đường tới mặc định `test` (`tools.py:51`). Thông điệp từ cloud của hãng (kể cả thông điệp có trường `"source"`) chỉ là dữ liệu cho bridge dịch; không đường nào tới nguồn.
4. **`dispatch()` ném NE1004** (lỗi lập trình, không phải phán quyết — `errors.py:107-112`) với lời gọi `bridge:<id>` hay `mcp:<client>` mà id không thuộc tập id đã đăng ký của phiên; `Guard` (qua bộ nạp) điền id bridge, `[mcp.clients]` điền nhãn.
   Chặn typo và mã ngoài `Dispatcher`; không chặn mã thù địch cùng tiến trình (§5). Runner `testing/tool_corpus.py` đóng vai bộ nạp: đăng ký id nó đọc từ `call.source` của ca.

**Đồng thời.** Hôm nay `dispatch` đặt `conversation.facts` tạm rồi khôi phục (`tools.py:350-356`), nên nhiều bên gọi đồng thời trên một `Conversation` không an toàn — RFC-0016 §2 và §3b mục 5 ghi vấn đề và để `Guard` tuần tự hoá dưới một khoá cho tới khi gốc được sửa. Gốc đó **không** do RFC này giải: một bản sửa riêng (nhánh `fix/call-source-isolation`) làm `call_source` theo từng lời gọi, và TSK-I2c-10 xây trên bản sửa ấy; `call_channel` (§3d) suy ở đúng điểm theo từng lời gọi đó, không thêm một chỗ đặt trạng thái chung nào.

Id nối `tool_call` với sự kiện nạp plugin của RFC-0016 (gói, phiên bản, băm tệp — NFR-SEC-10): đọc vết ghi biết `bridge:muse` là mã nào.

### 3c. Client MCP qua mạng: `mcp:<client>`, đặt nhãn có chủ ý

**Quyết định (khuyến nghị, §9 câu 1): `mcp:<client>`, không phải một dữ kiện thứ hai `call_client`.** Nhãn là tên *logic* do người vận hành đặt, không phải `sub` thô.

```toml
[mcp.clients.hub]                        # nhãn logic; gate viết `mcp:hub`
subjects = ["device-a", "device-b"]      # `sub` của token đã qua kiểm — không phải khoá, không phải bí mật
```

- **Mặc định tắt, không đổi gì:** không có `[mcp.clients]` ⇒ mọi kết nối MCP vẫn là `mcp`; không gate nào đổi hành vi.
- **Có bảng:** `build_server` nhận nguồn là *hàm của yêu cầu*; cổng `--http` đọc `AccessToken` đã xác thực của chính yêu cầu (`sub` — `mcp_http.py:332-359`), tra bảng ⇒ `mcp:<nhãn>`. `sub` không có trong bảng ⇒ `mcp` (client đã qua mTLS và token;
  chỉ chưa được đặt nhãn). Cổng `--http` mà không có chủ thể đã xác thực ⇒ **không dispatch**, không rơi về `mcp` (ném lỗi ba phần như lỗi hợp đồng, không phải kết quả `BLOCK`). stdio không có danh tính, luôn `mcp`.
- **Nhãn chỉ đến từ token:** `sub` đã qua chữ ký, `iss`, `aud`, `exp`, ràng buộc chứng chỉ (`tool_calling.md` §8.1) — không từ tham số, header hay thân yêu cầu. Client gửi `source` hay nhãn nào trong yêu cầu thì bị bỏ qua / `REJECTED` như tham số lạ (§5).
- **Luật `AgentManifestError` (NE3002)**, lúc build và lúc nạp: nhãn khớp `[a-z][a-z0-9_]{0,31}`; `subjects` là danh sách chuỗi không rỗng; một `sub` thuộc hai nhãn ⇒ lỗi; khoá lạ ⇒ lỗi (`refuse_unknown`, như `[external]` của RFC-0014 §3c).
- **Ảnh hưởng gate hiện có khi người vận hành thêm bảng:** gate liệt kê `mcp` trơn sẽ `BLOCK` client có nhãn (`mcp:hub` ngoài `options` ⇒ `criterion_unavailable`) — hướng chặt hơn, không bao giờ lỏng hơn. Tác giả gate chuyển sang `call_channel in [mcp]` ("mọi client MCP") hoặc liệt kê nhãn.
- **Chưa kiểm:** SDK `mcp` 2.2.0 có `get_access_token()` (`mcp/server/auth/middleware/auth_context.py:13`) và `ServerRequestContext.request` (`mcp/server/context.py`), nhưng chưa kiểm đường nào tới được handler `on_call_tool` của `build_server`
  qua Streamable HTTP. Đó là test đầu tiên của mục (b) ở §8; nếu không đường nào tới, nguồn phải gắn theo phiên MCP thay vì theo yêu cầu, hoặc phần nhãn client hoãn (§9 câu 1).

Vì sao không `call_client`: (1) D2 chọn không gian tên trong **một** `call_source`; (2) `allow_when` là hội (AND) giữa các tiêu chí nên "ngữ pháp *hoặc* hub" với hai dữ kiện đòi giá trị đệm luôn có mặt (`none`, `stdio`) — với một chuỗi, `call_source: { in: [local_grammar, mcp:hub] }` đúng ngay;
(3) nhãn đưa tên logic vào gate và ràng buộc triển khai ở `agent.toml`, đúng khuôn `external_source` của RFC-0014 §3c. Mặt trái, nói thẳng: `call_client` giữ nguyên tương thích tuyệt đối không cần cờ mở; phương án này cần người vận hành bật nhãn có chủ ý.

### 3d. Gate: `call_source` đúng chuỗi, `call_channel` theo họ

`gate.v1` **không đổi** (§2). `call_source` vẫn là `choice` mà gate tự liệt kê:

```yaml
evaluate:
  call_source:
    type: choice
    options: [local_grammar, mcp, mcp:hub, bridge:muse, test]
    instructions: "Nguồn của tool call, do dispatcher đặt (Q-24)"
  call_channel:
    type: choice
    options: [local_grammar, system_one, system_two, mcp, bridge, test]
    instructions: "Họ của nguồn gọi, do dispatcher suy từ call_source"
allow_when:
  call_source:  { in: [local_grammar, bridge:muse] }     # đúng Muse; bridge khác ⇒ BLOCK
# hoặc, cho "mọi bridge đã bật":  call_channel: { in: [local_grammar, bridge] }
```

- **`call_channel` là dữ kiện dẫn xuất:** phần trước dấu `:` đầu của `call_source` (hoặc cả chuỗi). Chèn ở **một nơi** — chính điểm mà `call_source` đi vào ngữ cảnh gate của *từng lời gọi* (hôm nay `Conversation._context`, `conversation.py:143-151`; sau bản sửa `fix/call-source-isolation`, điểm theo từng lời gọi của nó), từ `call_source` của lời gọi đó, *sau* khi gộp nguồn dữ kiện — nên mọi đường
  có nó (`dispatch`, xác nhận `ask`, `c.do()` lồng, fallback `degrade` — cùng đi qua `_do`) và không `c.facts`, `[sim.facts]` hay nguồn dữ kiện nào ghi đè được. Không có `call_source` ⇒ không có `call_channel` ⇒ `criterion_unavailable`.
- **Cùng luật với `call_source`:** thêm `call_channel` vào `RUNTIME_CRITERIA` (`models/providers/config.py:121`, kiểm ở `:320`) để `[system_one]` không được nhờ mô hình phán; what-if của Studio (`studio/api_agent.py:221-222`) suy nó từ `call_source` mặc định.
- **Fail-closed, đã chạy (§2):** giá trị ngoài `options` ⇒ `BLOCK criterion_unavailable`, kể cả dưới `fail: open`. Mọi gate hiện có liệt kê năm nguồn ⇒ **mọi bridge `BLOCK` mặc định** cho tới khi một gate gọi tên nó hoặc họ của nó.
- **Vì sao một dữ kiện họ, không phải toán tử mới:** `call_channel` cho gate "mọi bridge" mà không đổi ngôn ngữ gate, ngữ nghĩa phân giải (`constraints.py`) hay walker C; miền của nó hôm nay có 6 giá trị (7 khi `trigger` của TSK-N6-01 vào), xa giới hạn 32.

### 3e. Vết ghi, replay, xác nhận

- `tool_call.source` và `gate_facts.call_source.value` mang chuỗi mới; `gate_facts.call_channel` có mặt khi gate khai. `trace.v1` không đổi; bản ghi `tool_call` vẫn hợp lệ theo `tool-call.v1#/$defs/call` (RFC-0015 §3e).
- **Replay chỉ dùng `gate_facts` đã ghi** (`tool_calling.md` §7, đoạn sau bảng sự kiện): không nạp plugin, không cần bridge có mặt. Vết ghi có `bridge:muse` replay được trên máy không cài `neuroedge-muse`.
- **Xác nhận `ask`:** `HUMAN_SOURCES = ("local_grammar", "ui")` (`actions/confirmation.py:33`, kiểm ở `:167`). `bridge:*` và `mcp:*` không trả lời được câu hỏi của thiết bị — không đổi mã, thêm test. Q-26 giữ nguyên (§9 câu 3).

### 3f. Hợp đồng, tài liệu, corpus, firmware

| Hạng mục | Thay đổi |
|:---|:---|
| `docs/spec/tool_calling.md` | §1 (bảng `source`: "một trong năm nguồn" ⇒ văn phạm §3a); §5 viết lại (đoạn *"một lời gọi qua mạng là `mcp`, không có nguồn riêng"* ⇒ nhãn có chủ ý; thêm `call_channel`, ví dụ §3d); §9 nêu corpus phủ họ |
| `docs/spec/threat_model.md` | §2b: sửa mục *"Không phân biệt thiết bị ở gate"* (mục *"Ranh giới tin cậy của `mcp serve --http`"*) — còn đúng cho thiết bị chưa đặt nhãn; thêm hàng bridge (§5) |
| `docs/spec/python_api.md` (bảng lỗi và mục MCP), `docs/user/thuat-ngu.md` (hàng `call_source`) | `ToolCall` nhận hai dạng nguồn mới; thuật ngữ `bridge:<id>`, `mcp:<client>`, `call_channel` |
| `fixtures/contracts/` | `tool-call/valid/`: `call_source_bridge.json`, `call_source_mcp_client.json`; `invalid/`: `call_source_unknown_family.json` (`mqtt:muse`), `call_source_bridge_without_an_id.json`, `call_source_bridge_id_with_a_hyphen.json`, `call_source_bridge_id_too_long.json`; đổi tên `call_source_outside_the_five.json` (`mcp_network`) thành `call_source_outside_the_grammar.json` và sửa mục của nó ở `expected_errors.yaml` (`keyword: enum` ⇒ `anyOf`; thông báo `…is not valid under any of the given schemas`) |
| `fixtures/tool_calls/` | `valid/open_gate_from_a_bridge_degrades.yaml` (agent `driveway`, `source: bridge:muse`: `BLOCK criterion_unavailable`, `failed_criterion: call_source`, `degrade` chạy `porch_light_on` — gương của `open_gate_mcp_degrades.yaml`); agent fixture nhỏ mới `bridge-lamp` (gate khai `call_source` đúng `bridge:muse` và `call_channel`) với ca `ALLOW` cho `bridge:muse`, `BLOCK` cho `bridge:other`, `ALLOW` theo họ; ca `mcp:hub`. Không đụng gate khoá trong `digests.lock` |
| Firmware / `NETR` | **Không đổi** (§2). `LAYOUT_VERSION` 2, walker C, `ne_agent` sinh lại như mọi lần gate đổi `options`. Lưu ý: thêm một `option` làm đổi thứ tự `sorted(options)`, nên chỉ số do `build` sinh đổi theo — mã C viết tay cứng chỉ số là lỗi của người viết (header chỉ số ghi rõ không dùng trong firmware) |
| `CONTRIBUTING.md` §3 (hàng `NETR`) | Gọi `NETR` là "v1" trong khi `binary_tree.py:49` là 2 — lệch có sẵn, ngoài phạm vi; người tích hợp quyết có sửa trong PR này không |

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | **Có.** Mọi `call`, gate, agent, vết ghi hiện có. Gate hiện có không đổi nghĩa: giá trị mới ngoài `options` của chúng ⇒ `BLOCK` |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có, đúng hai dạng: `source: bridge:<id>` và `mcp:<id>` ở `tool-call.v1#/$defs/call`, và `ToolCall(…, source="bridge:x")` ở mã. `mcp_network` (ví dụ của RFC-0015 §10 câu 11) **vẫn không hợp lệ**. *Bản `neuroedge` cũ hơn từ chối tài liệu mang nguồn mới* — fail-closed, không phải vỡ tương thích |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | **Không.** Nới `enum`, không đổi tên/bỏ/siết trường (PRD §10.3; RFC-0015 §3f) |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không (`trace.v1` không đổi; không vết nào có nguồn mới) |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào. Gate mẫu dùng nguồn mới (agent `bridge-lamp`) vào bằng PR thường |
| Bố cục `NETR` hoặc walker C phải đổi? | **Không** — đã kiểm ở §2 |
| Đáp án nào của corpus tool call đổi? | Không đổi đáp án nào; **thêm** ca (§3f). `fixtures/contracts/expected_errors.yaml`: một mục đổi từ khoá (`enum` ⇒ `anyOf`) |
| API Python công khai (`python_api.md`) | `ToolCall` nhận thêm hai dạng nguồn (bổ sung, MINOR); `SOURCES` không công khai và giữ năm giá trị; `valid_source`, `source_channel` nội bộ |
| Hành vi `mcp serve --http` | Không đổi cho tới khi người vận hành thêm `[mcp.clients]` (§3c) |
| CLI | Không đổi |

## 5. Ảnh hưởng an toàn

**Có đường nào làm gate lỏng hơn không? Không.** Một nguồn mới chỉ qua được một gate đã chủ động gọi tên nó hoặc họ của nó (`BLOCK` ngoài `options`, kể cả `fail: open`). Hai ngoại lệ đã có từ trước và nói rõ ở dưới: gate không đọc `call_source`,
và bảng nhãn do người vận hành viết.

| Đường tắt | Chặn bởi | Kết quả |
|:---|:---|:---|
| Thông điệp cloud của hãng mang `"source": "local_grammar"` | Bridge dịch thành `request` (không có `source`); kênh gán `bridge:<id>` (§3b.3) | Nguồn là `bridge:<id>` |
| Bridge A nói lời gọi của mình là của bridge B | `ToolRequest` không có `source` (§3b.3); chỉ lõi dựng `ToolCall`. Dựng thẳng `ToolCall` thì chỉ mã thù địch làm được (rủi ro 1) | Nguồn là `bridge:A` |
| Hai gói cùng tên entry point để chiếm danh tính | Trùng id ⇒ không khởi động (§3b.2) | Không chạy |
| Nguồn không ai đăng ký (`bridge:typo`) | `dispatch()` (§3b.4) | NE1004, không có lời gọi |
| Họ lạ (`mqtt:x`) | `ToolCall`, schema | NE1004 / không hợp lệ; tới gate bằng cách khác ⇒ `criterion_unavailable` |
| Client mạng nói nó là `mcp:hub` | Nhãn chỉ từ `sub` đã xác thực (§3c); `source` không là tham số | `REJECTED` như `caller_declares_call_source.yaml` |
| Bridge hay client mạng tự trả lời câu hỏi `ask` | `HUMAN_SOURCES` (`confirmation.py:167`) | `tool_confirm_rejected` |
| Mã agent, `[sim.facts]`, nguồn dữ kiện hay mô hình đặt `call_channel` | Chèn sau cùng, `RUNTIME_CRITERIA` (§3d) | Bị ghi đè / `[system_one]` từ chối |

**Rủi ro còn lại — nói thẳng:**

1. **Plugin là mã người vận hành tin, cùng tiến trình** (NFR-SEC-10, `threat_model.md` §3). Bridge thù địch gọi được `dispatch()` trực tiếp với nguồn của một bridge khác *đã bật*. Kiểm tập id đăng ký chống nhầm lẫn và thông điệp từ ngoài; **không** phải hộp cát. Gốc tin cậy là việc người vận hành bật plugin và nguồn gốc ghi vào vết ghi (RFC-0016).
2. **Id là tên do tác giả plugin đặt**, không chứng minh ai viết nó. Gate nói `bridge:muse` là tin vào bridge mà người vận hành đã bật dưới tên đó.
3. **Gate không đọc `call_source` nhận mọi nguồn**, kể cả bridge — đúng như với `mcp` và `system_two` hôm nay (`test_the_same_call_from_any_source_meets_the_same_gate`). Gate cho hành động không hoàn tác nên liệt kê nguồn tường minh; sinh sẵn chúng là việc của `guard init` (RFC-0016 §9.9, TSK-I2c-14).
4. **`BLOCK` vì nguồn lạ có thể chặn cả lời gọi "dừng" của chính bridge** nếu gate `stop` của maker không liệt kê nó. Phía an toàn của HAL — tự tắt, hết lease, `hal.close()`, giám sát — không phụ thuộc nguồn và không qua gate (`threat_model.md` §1, các đoạn về lệnh về phía an toàn và chuyển động có lease; Q-62), nên Q-62 không bị đụng.
5. **Nhãn client là lời của người vận hành:** gán nhầm `sub` vào nhãn quyền cao là lỗi cấu hình, thấy được ở `agent.toml` khi review. Giới hạn của cửa mạng (không thu hồi tức thì, không giới hạn tốc độ — `tool_calling.md` §8.1 "Chưa có") không đổi.

`threat_model.md` §2b: dòng *"Không phân biệt thiết bị ở gate"* được thay bằng *"phân biệt theo nhãn khi người vận hành đặt nhãn; thiết bị chưa đặt nhãn vẫn là `mcp`"*. Cần kỹ thuật trưởng duyệt vì chạm `schemas/tool-call.v1.json`, mở danh tính vào gate và đảo RFC-0015 §10 câu 11.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Giữ tập đóng; bridge dùng `mcp` | Gate không tách được hai bridge; Q-67 D2 đã chốt ngược lại |
| Bridge tự khai chuỗi nguồn rồi lõi chỉ kiểm tiền tố | Nguồn do bên gọi nói — đúng điều `tool_calling.md` §5 cấm; id thành thứ đoán được/giả được |
| Thêm một giá trị `enum` cho mỗi sản phẩm (`muse`, `homeassistant`…) | Mỗi sản phẩm một RFC và một bản phát hành: đội lõi vẫn là cổ chai |
| Toán tử tiền tố/ký tự đại diện trong gate (`call_source: { prefix: "bridge:" }`, `bridge:*` trong `options`) | Đổi ngôn ngữ gate và ngữ nghĩa phân giải (`CHOICE_OPERATORS`, `constraints.py`), walker C và `NETR` (thiết bị so chỉ số miền, không so chuỗi). `call_channel` cho cùng khả năng mà không đổi gì |
| `source` là đối tượng `{family, id}` | Phá `choice`, `NETR`, vết ghi và mọi gate; không có lợi ích hơn chuỗi có tiền tố |
| Dữ kiện thứ hai `call_client` thay cho `mcp:<client>` | Tương thích tuyệt đối, nhưng hai tiêu chí cho một ý, hội AND cần giá trị đệm để diễn đạt "A hoặc B" (§3c). Gần ngang; bác vì D2. Câu 1 ở §9 vẫn mở cho chủ sản phẩm |
| `mcp:<sub>` thô, hoặc nhãn lấy tự động từ `client_id` | Đưa id thiết bị của triển khai vào gate đã ký/phân phối; hành vi đổi theo hình dạng claim; miền không giới hạn (trần 32). Nhãn logic ở `agent.toml` giống `external_source` |
| Tự gán `mcp:<nhãn>` cho mọi token có `client_id` | Mọi gate liệt kê `mcp` trơn sẽ `BLOCK` mọi client mạng ngay khi nâng cấp; RFC 9068 §2.2 liệt `client_id` là claim bắt buộc nên gần như token thật nào cũng dính |
| Họ lạ coi như `mcp` (fail-open) | Vi phạm `CHANGELOG.md` §3.3 #2; nguồn lạ phải `BLOCK` |
| Id là tên gói (`neuroedge-muse`) thay cho tên entry point | Một gói có thể mang nhiều bridge; tên gói có gạch ngang ngoài văn phạm; entry point là đơn vị đăng ký |
| Cho bridge xác nhận `ask` thay người dùng của hãng | Q-26; §9 câu 3 |
| Đổi `NETR` để mang tiền tố | Không cần (§2) |

## 7. Bằng chứng kiểm chứng

Tên dưới đây là **đề xuất** — chưa tồn tại tới khi RFC được chấp thuận; test có sẵn ghi rõ.

- [ ] **Ví dụ hợp lệ và phản chứng** (`fixtures/contracts/`, `fixtures/tool_calls/`; luật khép kín hai chiều, `CONTRIBUTING.md` §3): đúng danh sách ở §3f
- [ ] **Văn phạm và schema** (`python/tests/test_contracts.py`, `test_tools.py`, `test_public_api.py`):
  - `test_the_tool_call_schema_and_the_dataclass_agree` *(có sẵn, sửa: `anyOf` = `SOURCES` ∪ mẫu)* · `test_the_source_pattern_of_the_schema_is_the_one_of_the_code`
  - `test_a_bridge_or_client_source_is_valid_and_a_made_up_family_is_not` (`bridge:muse`, `mcp:hub` ok; `mqtt:x`, `bridge:`, `bridge:Muse`, `bridge:a-b`, 33 ký tự, `bridge:muse:x`, `mcp_network` ⇒ NE1004) · `test_a_source_with_a_trailing_newline_is_refused`
  - `test_an_unknown_tool_call_source_is_an_ne_error_with_three_parts` *(có sẵn; lời nhắc đổi)* · `test_every_known_reason_and_every_source_appears_in_a_valid_contract_example` *(có sẵn, sửa: phủ cả hai không gian tên)* · `test_the_corpus_of_tool_calls_covers_every_family`
- [ ] **Gate và engine** (`tests/test_tool_source_namespace.py`, mới; engine ở `test_decision_tree.py`):
  - `test_a_bridge_call_meets_the_gate_with_its_own_source` · `test_a_gate_that_lists_one_bridge_blocks_another` · `test_a_source_outside_a_gates_options_blocks_with_criterion_unavailable` · `test_a_source_outside_a_gates_options_blocks_even_under_fail_open`
  - `test_call_channel_is_the_family_of_call_source` · `test_call_channel_cannot_be_set_by_facts_sim_facts_or_a_fact_source` · `test_the_confirmation_path_keeps_both_source_facts` · `test_two_concurrent_dispatches_each_see_their_own_call_channel` · `test_system_one_may_not_judge_call_channel` · `test_a_model_cannot_claim_its_own_call_channel` (cạnh `test_a_model_cannot_claim_its_own_call_source`)
  - `test_a_bridge_or_a_labelled_client_cannot_answer_an_ask_question` (thêm tham số vào `test_only_a_person_on_the_device_may_answer`) · `test_a_replayed_trace_with_a_bridge_source_needs_no_plugin`
- [ ] **Bridge và đăng ký** (cùng TSK-I2c-11/12; bộ test tuân thủ bridge của RFC-0016 dùng lại):
  - `test_a_bridge_dispatcher_assigns_its_own_source_and_a_request_has_no_source_to_state` · `test_two_bridges_with_the_same_id_refuse_to_start` · `test_a_bridge_id_outside_the_grammar_is_refused_at_load` · `test_a_call_for_a_source_nobody_registered_is_refused_by_dispatch` · `test_a_bridge_cannot_dispatch_under_another_bridges_source`
- [ ] **Client mạng** (`tests/test_mcp_http.py`, `test_compiler.py`; mTLS thật như các test sẵn có):
  - `test_without_a_clients_table_every_connection_is_plain_mcp` · `test_a_mapped_device_gets_its_label_as_the_source` · `test_an_unmapped_authenticated_device_is_plain_mcp` · `test_two_devices_with_different_labels_meet_different_verdicts`
  - `test_the_label_comes_from_the_verified_token_and_not_from_the_request` · `test_an_http_call_without_a_verified_principal_is_not_dispatched` · `test_stdio_stays_plain_mcp`
  - `test_a_clients_table_with_a_bad_label_a_shared_subject_or_an_unknown_key_is_refused` (`AgentManifestError` NE3002)
- [ ] **Firmware** (`tests/test_c_walker.py`, `test_decision_tree.py`): `test_the_c_walker_matches_the_host_engine_on_every_gate` *(có sẵn, xanh)* · `test_a_gate_with_a_bridge_option_encodes_with_the_unchanged_layout` (`LAYOUT_VERSION == 2`, chuỗi `bridge:muse` nằm trong bảng chuỗi của chính gate đó) · `test_a_source_domain_over_32_values_is_refused_at_build` (lý do của `call_channel`)
- [ ] `neuroedge gate lint`, `neuroedge verify` xanh; `pytest -q` 0 failed, 0 skipped; `scripts/wheel_smoke.sh` xanh (đường dẫn `schemas/` đi vào wheel); `ruff check .` và `ruff format --check .`

## 8. Việc phải làm khi chấp thuận

Hai nửa độc lập, làm thứ tự: **(a)** bridge, ngữ pháp và `call_channel` (không phụ thuộc cổng mạng, đi cùng TSK-I2c-11); **(b)** nhãn client mạng (chạm `mcp_http.py`, sau khi test đường token ở §3c qua).

- [ ] Cập nhật `schemas/tool-call.v1.json` (§3a); `fixtures/contracts/` và `expected_errors.yaml` (§3f)
- [ ] **TSK-I2c-10 (a):** `actions/tools.py` (`SOURCE_ID`, `valid_source`, `source_channel`, `__post_init__`, kiểm tập id ở `dispatch`), `testing/tool_corpus.py:138`, `actions/conversation.py` (điểm chèn theo từng lời gọi, tập id đăng ký), `models/providers/config.py:121`, `studio/api_agent.py:221-222`; xây trên bản sửa `fix/call-source-isolation` (`call_source` theo từng lời gọi), không giải lại; khi bản sửa đã vào, khoá tuần tự của `Guard` (RFC-0016 §3b mục 5) bỏ được — việc đó thuộc RFC-0016, không thuộc RFC này; `Dispatcher` gán nguồn và luật trùng id đặt cùng `Guard` và bộ nạp (RFC-0016, TSK-I2c-07/11)
- [ ] **TSK-I2c-10 (b):** `mcp_server.py::build_server` (nguồn là hàm của yêu cầu), `mcp_http.py::build_app`, bảng `[mcp.clients]` (đọc, kiểm NE3002, `neuroedge build`), test đường token SDK
- [ ] Corpus: ca ở §3f, agent `bridge-lamp`; thêm hàng "nhãn client" nếu `CONTRIBUTING.md` §3 cần
- [ ] `docs/spec/tool_calling.md` §1/§5/§9; `docs/spec/threat_model.md` §2b; `docs/spec/python_api.md`; `docs/user/thuat-ngu.md`; `docs/architecture/{vi,en}/07-data-contracts.md` (khối `agent.toml` mới — chưa kiểm vị trí chính xác)
- [ ] `neuroedge-prd.md`: FR-ACE-09 (nguồn gọi có không gian tên), Phụ lục B hàng `ToolCallError` (lời "không thuộc tập nguồn" ⇒ "không đúng văn phạm nguồn"), quyết định ở §9 cấp `Q-N`; `neuroedge-roadmap.md`: TSK-I2c-03/10 và ghi chú cho `TSK-N6-01` (cần RFC, §3a)
- [ ] Không đụng `digests.lock`; `docs/rfc/README.md` (dòng RFC-0017) và một mục `CHANGELOG.md` `[Chưa phát hành]`

## 9. Câu hỏi mở (Q-67 chưa quyết)

1. **Danh tính client mạng nằm trong RFC này không, và là `mcp:<client>` hay `call_client`?** *Khuyến nghị:* `mcp:<client>` với nhãn có chủ ý (§3c), làm sau nửa (a). Nếu test đường token của SDK thất bại hoặc chủ sản phẩm muốn tương thích tuyệt đối không cờ mở, tách §3c thành RFC riêng và chỉ giữ chỗ trong văn phạm; phần bridge không phụ thuộc nó.
2. **Nguồn mà `neuroedge.guard` và `neuroedge proxy mcp|http` gán — đã trả lời ở RFC-0016 §9.9** (một sự thật một nơi). Tóm tắt: chương trình dùng `Guard` nhận `bridge:<id>` theo văn phạm và luật trùng id của RFC này; proxy của lõi giữ nguồn của client phía trước (`mcp` hay `mcp:<nhãn>`).
3. **Bridge có được chuyển tiếp lời "có" của người dùng ở phía hãng (xác nhận `ask`) không?** *Khuyến nghị:* **không** trong RFC này; `bridge:*` ∉ `HUMAN_SOURCES` (Q-26). Một đường xác nhận có chứng thực người cần RFC riêng, khi có bridge thật đòi nó (tín hiệu: bài kiểm TSK-I2c-17).
4. **`neuroedge gate lint` có cảnh báo một `option` của `call_source` ngoài văn phạm (gõ nhầm `bridge:muze`) không?** Gate vẫn hợp lệ và fail-closed; cảnh báo chỉ để tác giả khỏi mất công tìm. *Khuyến nghị:* có, chỉ cảnh báo, không đổi phán quyết; nếu kỹ thuật trưởng coi lint nằm trong "ngữ nghĩa phân giải" (`gate_resolver.py`) thì hoãn.
5. **Bật một bridge có kèm danh sách tool được gọi không — đã trả lời ở RFC-0016 §9.9.** Tóm tắt: không; gate đã là nơi quyết, qua `call_source` hay `call_channel` (§3d). Rủi ro 3 ở §5 (gate không đọc `call_source`) giữ ở đây; cách giảm (`guard init`, `plugin doctor`) nằm ở RFC-0016.
