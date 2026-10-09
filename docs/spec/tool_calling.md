# Gated Tool Profile v0 — đường từ ngôn ngữ tới hành động thực

**Trạng thái:** chuẩn tắc cho `sim` và `linux` từ v0; `esp32s3` theo §8. Hình dạng của phong bì và kết quả
đóng băng ở `schemas/tool-call.v1.json` và `schemas/tool-result.v1.json` (RFC-0015, §1, §4, §9). Quyết định:
Q-24, Q-25, Q-26, Q-27, Q-58, Q-66 (`neuroedge-prd.md` §15).
**Mã nguồn:** `python/neuroedge/actions/tools.py` (dispatch), `python/neuroedge/mcp_server.py`
(MCP server), `python/neuroedge/mcp_http.py` (cửa mạng của MCP server, §8.1), `python/neuroedge/mcp_host.py` (System 2 làm MCP client),
`python/neuroedge/sim/session.py` (ngữ pháp, vòng System 2).

Tài liệu này là nơi **duy nhất** định nghĩa tool call trong NeuroEdge. Tài liệu khác dẫn
tới đây, không chép lại (CONTRIBUTING §8.1). Từ khoá **PHẢI**, **KHÔNG ĐƯỢC**, **NÊN**
mang nghĩa như RFC 2119.

## 0. Vì sao là một *profile*, không phải một giao thức

Hệ sinh thái AI agent đã hội tụ vào một đường truyền: MCP (`tools/list`, `tools/call`),
function calling kiểu OpenAI, JSON Schema cho tham số. NeuroEdge **không** phát minh
đường truyền mới — một agent Claude Desktop, Cursor hay LangChain gọi được thiết bị
NeuroEdge mà không cần gì riêng.

Điều hệ sinh thái để trống là **chuyện gì xảy ra giữa tool call và hiệu ứng vật lý**.
Ở MCP và function calling, gọi tool nghĩa là *thực thi*; lỗi là chuỗi tự do; không ai
biết lời gọi từ đâu tới; mất mạng thì không có tool call. Profile này quy định phần đó:

| | Tool call thông thường | Gated Tool Profile |
|:---|:---|:---|
| Ngữ nghĩa | Thực thi | **Yêu cầu** — gate quyết định (§2) |
| Kết quả bị từ chối | Chuỗi lỗi | Ba trạng thái có cấu trúc (§4) |
| Ai gọi | Không ghi | `call_source` — dữ kiện tin cậy gate đọc được (§5) |
| Xác nhận của người | Client tự hỏi, bỏ qua được | Thiết bị cưỡng chế; mô hình không tự xác nhận (§6) |
| Mất mạng | Không có | Ngữ pháp cục bộ sinh tool call tổng hợp, cùng đường (§1) |
| Bằng chứng | Log văn bản | Vết ghi: tool call → phán quyết → lệnh chân, replay được (§7) |

MCP có **hai chiều**, và profile phủ cả hai:

| Chiều | Ai là client | Ai là server | Mục |
|:---|:---|:---|:---|
| **B — gọi vào thiết bị** | Agent bên ngoài (Claude Desktop, IDE, agent khác) | `neuroedge mcp serve` | §1–§9 |
| **A — thiết bị gọi ra** | System 2 của agent (MCP host) | Chính MCP server của agent **và** MCP server bên ngoài | §10 |

Profile là tài sản chuẩn thứ ba của NeuroEdge, cạnh lược đồ gate và lược đồ vết ghi
(`neuroedge-proposal.md` §1.5).

## 1. Phong bì `ToolCall`

Hình dạng nằm ở [`schemas/tool-call.v1.json`](../../schemas/tool-call.v1.json), không chép lại ở đây:
`#/$defs/request` là cái bên gọi gửi (`id`, `name`, `arguments`; **không** có `source`, và một lời gọi tự khai
`source` bị phong bì từ chối), `#/$defs/call` là phong bì dispatcher giữ — thêm `source` đã gán — và
cũng là `data` của sự kiện `tool_call` (§7). Phong bì **đóng** (khoá lạ bị từ chối). Phần dưới là
**nghĩa** mà lược đồ không nói được:

| Trường | Quy định |
|:---|:---|
| `name` | Tên một `@action` của agent. Mỗi `@action` là đúng một tool |
| `arguments` | Đối tượng JSON; khoá là tên tham số của `@action` |
| `source` | Một nguồn dựng sẵn hoặc `bridge:<id>` / `mcp:<client>` (bảng dưới). **Do runtime gán**, không do bên gọi khai |
| `id` | `call_1`, `call_2`… theo thứ tự trong phiên, do dispatcher gán khi rỗng. **KHÔNG ĐƯỢC** là giá trị ngẫu nhiên: vết ghi phải tất định để golden và `--anonymize` ổn định. Id do nhà cung cấp mô hình trả về được giữ nguyên |

| `source` | Nơi phát |
|:---|:---|
| `local_grammar` | Câu khớp `commands.toml` → tool call **tổng hợp** (Q-14). Chạy không mạng |
| `system_one` | Mô hình có cấu trúc (§3.6 proposal) |
| `system_two` | LLM với câu tự do; gọi tool của thiết bị qua kết nối MCP in-process tới chính agent (§10) |
| `mcp` | Client MCP qua `neuroedge mcp serve`, qua stdio hay qua mạng (§8.1) |
| `test` | Action CI |
| `bridge:<id>` | Một bridge đã nạp (Muse, Home Assistant…): lõi gán từ id đã đăng ký của bridge, bên trong `Dispatcher`; bridge không có chỗ nào để nói nguồn (RFC-0017 §3b) |
| `mcp:<client>` | Client MCP qua mạng đã được người vận hành đặt nhãn, từ `sub` của token đã xác thực (RFC-0017 §3c) — văn phạm đã nhận; nhãn client **chưa** được gán (TSK-I2c-10 nửa (b)), nên mọi client mạng hôm nay vẫn là `mcp` |

**Văn phạm của `source`** (RFC-0017 §3a): một trong năm tên dựng sẵn ở trên, hoặc `bridge:<id>` / `mcp:<client>` với
`<id>` khớp `[a-z][a-z0-9_]{0,31}` (mẫu `SOURCE_ID` ở `actions/tools.py`; `source` dài tối đa 39 ký tự). Họ khác ⇒
`ToolCallError` NE1004 lúc dựng; **tập dựng sẵn vẫn đóng**, thêm một họ hay một tên dựng sẵn là RFC. Mã kiểm bằng
`re.fullmatch` (`valid_source`), không bằng `$`: `$` của Python khớp trước một `\n` cuối, ECMA 262 thì không
(`test_a_source_with_a_trailing_newline_is_refused`). Hình dạng trong lược đồ nằm ở
[`schemas/tool-call.v1.json`](../../schemas/tool-call.v1.json) `$defs/source`.

Câu khớp ngữ pháp **PHẢI** trở thành tool call rồi đi qua cùng đường với mọi nguồn khác —
không có nhánh "offline" riêng tới chân.

Một thẩm định lược đồ thành công **không** chứng minh một runtime tuân thủ: lược đồ không biểu diễn được
việc tool có tồn tại, phép ép chuỗi của §2, ràng buộc tham số của gate (§3, kiểm **sau** schema) hay
`call_source`. Bộ kiểm tuân thủ là corpus của §9 chạy qua `dispatch()` — cùng lập luận với gate:
cổng là `neuroedge gate lint`, không phải thẩm định lược đồ (`CHANGELOG.md` §3.3 #1).

## 2. Thứ tự dispatch

Mọi tool call, từ mọi nguồn, đi qua `dispatch()` theo đúng thứ tự:

1. Ghi sự kiện `tool_call`.
2. Tool có tồn tại — không ⇒ `REJECTED`.
3. Tham số khớp schema (§3): không có tham số lạ, đủ tham số bắt buộc, đúng kiểu. Chuỗi
   được ép sang số hoặc bool khi schema nói vậy (slot ngữ pháp là chữ); ngoài ra không
   đoán gì. Sai ⇒ `REJECTED`, ghi `tool_call_rejected`.
4. Chèn dữ kiện `call_source` và `call_channel` (§5). Một nguồn `bridge:<id>` / `mcp:<client>` mà id chưa được đăng ký
   trong phiên ⇒ lỗi lập trình NE1004, ném **trước** bước 1: không có lời gọi, không có sự kiện.
5. `c.do(action, **arguments)` → gate → token dùng một lần → thân `@action` → HAL.

Khoá `arguments` **dành riêng** `__unparseable__`: `parse_tool_calls` chèn nó khi `arguments` của nhà
cung cấp mô hình không phải JSON hợp lệ (hoặc không phải đối tượng), với giá trị là nguyên văn
phần hỏng. Không `@action` nào có tham số tên đó, nên bước 3 từ chối ("unknown argument") và lời gọi là
`REJECTED`; không gate nào nhìn thấy nó. Bên gọi **KHÔNG NÊN** tự gửi khoá này.

Bước 2–3 xảy ra **trước** gate: một lời gọi sai hình dạng không phải câu hỏi an toàn,
nên nó không tốn ngân sách gate và không có phán quyết.

Lỗi hợp đồng (`ActionContractViolation` NE1001, `TokenReplayError` NE1002) **PHẢI** được
ném ra. Dispatcher **KHÔNG ĐƯỢC** bắt chúng rồi trả `BLOCK`: đó là lỗi lập trình, không
phải phán quyết, và che nó đi là che một đường tắt qua gate.

## 3. Schema tool

Schema sinh từ chữ ký `@action` (`input_schema()`): `str` → `string`, `int` → `integer`,
`float` → `number`, `bool` → `boolean`; tham số không có mặc định là `required`;
`additionalProperties: false`. Mô tả là đoạn đầu docstring kèm câu *"Guarded by gate
`X`: the call may be blocked."*

Tập con JSON Schema mà `inputSchema` dùng, và bộ bốn trường của một tool (`name`, `description`,
`inputSchema`, `outputSchema`) mô tả ở `schemas/tool-call.v1.json` (`#/$defs/input_schema`, `#/$defs/tool`).

Cùng một schema xuất ra hai dạng: MCP `inputSchema` (`neuroedge mcp tools --json`) và
`parameters` của function calling OpenAI (`--openai`, Q-12).

Từ RFC-0005 (Q-25, TSK-S3-25), schema là **giao** của chữ ký và ràng buộc tham số
của gate: `minimum`, `maximum`, `enum`, `maxLength` từ gate đi vào `inputSchema`, để mô
hình thấy giới hạn trước khi gọi. Gate vẫn kiểm lại — schema là gợi ý cho mô hình, gate
là cưỡng chế.

## 4. Kết quả

| `status` | Nghĩa | Chân | MCP `isError` |
|:---|:---|:---|:---:|
| `ALLOW` | Gate cho qua, thân `@action` đã chạy | Có thể đổi | `false` |
| `BLOCK` | Gate chặn (mọi `on_block`, Q-17) | Không đổi — trừ chân của `fallback_action` khi `degrade` và fallback được gate của nó cho qua | `false` |
| `REJECTED` | Tool lạ hoặc tham số sai; không có phán quyết | Không đổi | `true` |

`BLOCK` **không** là lỗi giao thức: gate làm đúng việc của nó, và bên gọi cần đọc lý do
để trả lời người dùng. Chỉ `REJECTED` là lỗi — bên gọi đã gửi một lời gọi không hợp lệ.

Hình dạng của nội dung trả về (`ToolResult.content()`; MCP gửi ở cả `structuredContent` và một khối
`text` chứa cùng JSON) là [`schemas/tool-result.v1.json`](../../schemas/tool-result.v1.json), không chép
lại ở đây. Lược đồ nói trường nào bắt buộc khi nào: `tool` và `status` luôn có; `BLOCK` có `gate` và
`on_block`; `REJECTED` có `problems` (không rỗng); `fallback` (đệ quy, kết quả của `fallback_action` đã chạy qua
gate riêng của nó) và `confirmation` (§6) là của `on_block: degrade` và `ask`.

Máy chủ MCP khai chính lược đồ này ở `outputSchema` của mỗi tool, đã ghim `tool` vào tên tool và bỏ
`$id`/`$schema` (`result_schema()` trong `actions/tools.py` **đọc** tệp; nó không dựng lược đồ). Client MCP kiểm
`structuredContent` của mọi kết quả **không** lỗi theo lược đồ đó; kết quả `REJECTED`
(`isError: true`) không được SDK kiểm, nhưng vẫn khớp lược đồ (tool lạ thì khớp lược đồ không
ghim tên `tool`).

**Luật cho bên đọc kết quả (RFC-0015 §3b, Q-66):**

- **`status` quyết định. `reason` chỉ là lời giải thích — KHÔNG ĐƯỢC rẽ nhánh theo nó, và tuyệt đối không
  rẽ nhánh tới ALLOW.** `reason` là chuỗi mở: danh sách giá trị đã biết nằm ở `x-neuroedge-known` của
  lược đồ (test buộc nó bằng đúng `Reason`), và sẽ dài thêm qua các RFC. Một `reason` lạ dưới `status: BLOCK` vẫn là bị chặn
  (fail-closed), không phải kết quả hỏng.
- **Đối tượng kết quả mở:** bên đọc **PHẢI** bỏ qua khoá nó không biết. Runtime chỉ phát các khoá lược đồ đã
  khai (test `test_the_mcp_server_emits_only_documented_result_keys`); thêm một khoá tuỳ chọn không tăng `v1`.
- **`status` và `on_block` là tập đóng:** thêm giá trị là `v2`.

## 5. `call_source`

Dispatcher chèn dữ kiện `call_source = <source>` vào ngữ cảnh gate của **chính lời gọi đó**
(`Conversation.do_with`): một bản chụp `c.facts` lấy lúc lời gọi bắt đầu, `call_source` đè lên. `c.facts`
không bị ghi, cũng không phải khôi phục. Hai lời gọi chồng nhau trên một `Conversation` (một `mcp`,
một `system_two`) vì vậy không thấy nguồn của nhau; fallback `degrade` và câu hỏi `ask` của một lời
gọi mang nguồn của lời gọi đó, kể cả khi lời gọi khác đang chạy
(`tests/test_call_source_isolation.py`). Gate đọc nó như mọi tiêu chí `choice`:

```yaml
evaluate:
  call_source:
    type: choice
    options: [local_grammar, system_one, system_two, mcp, test]
    instructions: Nơi phát lời gọi — do runtime chèn, không suy từ lời nói
allow_when: call_source in ["local_grammar", "system_one"]   # MCP không mở được cửa
```

Nguồn **gắn theo kết nối**, do runtime tạo kết nối đó: `neuroedge mcp serve` là `mcp`, kể cả qua mạng (`--http`, §8.1); kết nối in-process của System 2 là `system_two` (`build_server(session, source=...)`). Một bridge nhận nguồn `bridge:<id>` từ id nó được đăng ký lúc nạp.

Một lời gọi qua mạng hôm nay là `mcp`: stdio và mạng cùng một máy chủ, cùng một đường tới gate, nên gate chưa phân biệt được hai cửa. Phân biệt theo thiết bị là nhãn `mcp:<client>` do người vận hành đặt có chủ ý (RFC-0017 §3c, nửa (b), chưa làm); thiết bị chưa đặt nhãn vẫn là `mcp`. Thêm một họ hay tên dựng sẵn cho `call_source` vẫn cần RFC (`CONTRIBUTING.md` §3).

**Đăng ký id.** `dispatch()` chỉ nhận `bridge:<id>` / `mcp:<client>` đã đăng ký trên `Conversation` của phiên
(`register_source`; nội bộ, không thuộc `neuroedge.__all__`): bộ nạp bridge và bảng `[mcp.clients]` đăng ký, runner của corpus
(§9) đóng vai bộ nạp. Id ngoài văn phạm, tên dựng sẵn hay id trùng ⇒ NE1004; id chưa đăng ký ⇒ NE1004 ở `dispatch()`. Đây là chốt chặn
gõ nhầm và mã ngoài `Dispatcher`, không phải hộp cát chống mã thù địch cùng tiến trình (`threat_model.md` §2b, §3).

**`call_channel` — họ của nguồn.** Dispatcher chèn thêm dữ kiện dẫn xuất `call_channel`: phần trước dấu `:` đầu của
`call_source` (hoặc cả tên, với năm nguồn dựng sẵn) — `bridge` cho `bridge:muse`, `mcp` cho `mcp:hub`. Chèn ở **đúng điểm** theo
từng lời gọi nơi `call_source` vào ngữ cảnh gate (`Conversation._context`), *sau* khi gộp nguồn dữ kiện, nên `c.facts`,
`[sim.facts]`, nguồn dữ kiện và mô hình không đè được; nó sống qua câu hỏi `ask` (§6), `c.do()` lồng và fallback `degrade`.
Không có `call_source` hợp lệ ⇒ không có `call_channel` ⇒ `criterion_unavailable`. Nó nằm trong `RUNTIME_CRITERIA`: `[system_one]` không được
nhờ mô hình phán nó. Gate nói "đúng bridge Muse" bằng `call_source`, hoặc "mọi bridge đã bật" bằng `call_channel`:

```yaml
evaluate:
  call_source:  { type: choice, options: [local_grammar, mcp, bridge:muse, test], instructions: "…" }
  call_channel: { type: choice, options: [local_grammar, system_one, system_two, mcp, bridge, test], instructions: "…" }
allow_when:
  call_source:  { in: [local_grammar, bridge:muse] }   # đúng Muse; bridge khác ⇒ BLOCK
# hoặc "mọi bridge":  call_channel: { in: [local_grammar, bridge] }
```

**Fail-closed.** Giá trị ngoài `options` của gate ⇒ `BLOCK`, `criterion_unavailable`, kể cả dưới `fail: open`; mọi gate hiện có
liệt kê năm nguồn nên mọi bridge `BLOCK` mặc định cho tới khi một gate gọi tên nó hoặc họ của nó. `gate.v1` và bố cục `NETR` không đổi
(`bridge:muse` là một chuỗi trong miền của chính gate đó; một miền tối đa 32 giá trị, nên "mọi bridge" cần `call_channel`).
`bridge:*` và `mcp:*` không thuộc `HUMAN_SOURCES` (§6). Replay chỉ dùng `gate_facts` đã ghi, không cần bridge có mặt (§7).

Bên gọi **KHÔNG ĐƯỢC** tự khai nguồn: `call_source` không phải tham số của tool nào, nên
một mô hình gửi `{"call_source": "local_grammar"}` bị `REJECTED` ở bước 3
(`test_a_model_cannot_claim_its_own_call_source`). Ví dụ đầy đủ:
`fixtures/agents/home-voice/gates/`, và `fixtures/agents/driveway/gates/open_gate@1.0.0.yaml`
(client MCP không mở được cổng).

## 6. Xác nhận `on_block: ask` (Q-26)

`ask` nghĩa là *hỏi lại người*. Vì vậy:

- Chỉ **người, qua kênh của thiết bị**, được xác nhận: giọng nói hoặc chữ gõ khớp ngữ
  pháp (`local_grammar`), hoặc nút trên trang của thiết bị (`ui`). Đây là tập **nguồn xác
  nhận** (`HUMAN_SOURCES`, `actions/confirmation.py`), khác năm giá trị `source` của §1: `ui`
  không phát tool call, và `call_source` không bao giờ bằng `ui`.
- Nguồn `system_two`, `mcp`, `bridge:<id>` và `mcp:<client>` **KHÔNG ĐƯỢC** phát lời xác nhận. Nếu được, một mô hình bị
  prompt injection, hoặc một agent tự động phía client, sẽ tự trả lời câu hỏi an toàn
  dành cho người.
- Gate nói trước **điều gì** người được xác nhận thay: `on_block.confirms` (RFC-0006).
  Không có `confirms` ⇒ `ask` chỉ thông báo, không có câu hỏi nào chờ.
- Câu hỏi chỉ được mở (`tool_confirm_requested`) khi một lời "có" **đủ** để cho qua — cùng
  dữ kiện, các tiêu chí trong `confirms` coi như đạt, phải ALLOW. Gate chặn vì tiêu chí
  khác, hoặc vì giới hạn tham số, thì không hỏi.
- Lời xác nhận gắn với câu hỏi (`confirm_N`) và `gate_digest` của lần bị chặn; dùng **một
  lần** (kể cả khi lượng giá lại vẫn chặn); hết hạn sau `max(p95 × 3, 10 s)`; gate đổi giữa
  chừng ⇒ vô hiệu. Nguồn khác `local_grammar` / `ui` ⇒ `tool_confirm_rejected`, câu hỏi
  vẫn chờ người.
- Chữ gõ và nút trả lời câu hỏi mới nhất còn chờ. Lời **nói** chỉ trả lời câu hỏi trong
  lượt trả lời của chính nó — luật ở `docs/spec/voice_fsm.md` §5.4 (Q-46 (D3)).
- Xác nhận không bỏ qua gate: gate được **lượng giá lại** với dữ kiện **hiện tại** và
  `call_source` của **yêu cầu gốc** (và `call_channel` suy từ nó); chỉ tiêu chí trong `confirms` coi như đạt. Mọi tiêu chí
  khác, giới hạn tham số và fail-closed khi adjudicator suy giảm vẫn áp dụng. Kết quả ghi
  `confirmed: [...]`.
- Bên gọi (System 2, client MCP) được báo trong kết quả `BLOCK`: `confirmation: {id, message,
  expires_in_ms, who}` — để nói với người dùng, không để tự trả lời. Không có tool xác nhận.

Trên `sim`: REPL — gõ `có` / `không` (hoặc `:confirm` / `:decline`); UI — banner *Thiết bị
hỏi xác nhận* với nút Đồng ý / Huỷ và thời gian còn lại (`POST /confirm`, cùng nguồn gốc).

## 7. Vết ghi

Đây là danh mục **duy nhất** của sự kiện tool call, xác nhận, MCP host, System 2, model cloud
của System 1 và đo lượt (§7.1). Sự kiện
theo nguyên thủy HAL (`actuator_command`, `sensor_read`, `display_frame`…) ở
`docs/spec/simulation_coverage.md` §3.

| Sự kiện | Dữ liệu | Có từ |
|:---|:---|:---|
| `tool_call` | `id`, `name`, `arguments`, `source` | v0 |
| `tool_call_rejected` | `id`, `name`, `problems` | v0 |
| `tool_confirm_requested` | `id`, `action`, `gate`, `message`, `confirms`, `expires_ms` (thời gian vết ghi, như `offset_ms`), `ttl_ms` | RFC-0006 |
| `tool_confirmed` · `tool_confirm_declined` | `id`, `source` | RFC-0006 |
| `tool_confirm_rejected` | `id`, `source`, `reason` | RFC-0006 |
| `tool_confirm_expired` | `id` | RFC-0006 |
| `mcp_auth_refused` | `reason`, `status`, `subject?` — một yêu cầu tới cửa mạng (§8.1) bị 401 hoặc 403, nên không có gì được chuyển tiếp. `reason`: `no_token` · `malformed_authorization` · `invalid_token` (chữ ký, định dạng, thiếu `exp` `iss` `sub`) · `expired` · `wrong_audience` · `wrong_issuer` · `not_cert_bound` · `cert_mismatch` · `insufficient_scope` (`status` 403). `subject` chỉ có khi chữ ký đã đúng (`cert_mismatch`, `not_cert_bound`, `insufficient_scope`). **Không bao giờ** có token, địa chỉ client hay chứng chỉ. Ghi tối đa 10 000 sự kiện mỗi phiên; sự kiện cuối có `last_recorded: true`. Không phải lượt (không `turn_latency`); replay bỏ qua | TSK-P2-04 |
| `mcp_tool_result` | `id`, `server`, `tool`, `status`, `sha256`, `bytes` — không lưu nội dung (§10 quy tắc 3) | Q-27 |
| `mcp_server_unavailable` | `server`, `reason` (§10 quy tắc 4) | Q-27 |
| `system_two_call` | `provider`, `model`, `task`, `latency_ms`, `status`, `prompt_tokens?`, `completion_tokens?`, `cost_usd?`, `error?` — không prompt, không key; replay bỏ qua | FR-MDL-06 |
| `system_two_unavailable` | `task`, `reason` — model không trả lời được | FR-MDL-06 |
| `system_two_rounds_exceeded` | `task`, `rounds` — quá `max_rounds` (§10 quy tắc 6) | FR-MDL-11 |
| `system_one_call` | `provider`, `model`, `criterion`, `latency_ms`, `status` (`ok` · `unavailable`), `reason?` (lý do `Unavailable`: `offline`, `timeout`, `rate_limited`, `refused`, `malformed`, `empty`), `http_status?`, `confidence?`, `served_by?` (bản model đã trả lời), `prompt_tokens?`, `completion_tokens?`, `cost_usd?` — mỗi lượt SystemOne hỏi model cloud một tiêu chí (`[system_one]`). Model chỉ nhận lời người nói (`state = {utterance}`), không bao giờ action hay tham số của bên gọi; không có lời người nói (vd lời gọi từ MCP client) hay thiếu key thì không gọi, không ghi. Sự kiện không mang state, chữ hay key; replay bỏ qua | TSK-I4-02 |

Câu thiết bị nói ghi ở `tts_stream_start` (simulation_coverage §3); nguồn của câu nằm ở
`reply_source` của lượt (vd `gate_ask`, `confirmed`, `offline_help` — §10 quy tắc 5; danh sách đủ ở
`Turn.reply_source`, `python/neuroedge/sim/session.py`).

Trường `type` của sự kiện trong `trace.v1` là chuỗi mở, nên thêm sự kiện **không** cần
RFC. Replay (`testing/player.py`) tính lại từng lần lượng giá gate từ `gate_facts` đã
ghi — kể cả `call_source` — nên một lời gọi từ LLM replay tất định mà không hỏi lại mô
hình. Lời gọi `REJECTED` không tới gate nên không có trong phán quyết replay.

### 7.1 Độ trễ từng chặng và tỷ lệ System 1 / System 2 (TSK-I4-03)

FR-ACE-06, FR-TEL-03, NFR-OBS-02. Mỗi lượt của phiên `sim` / `linux` — một dòng gõ hay một
transcript (`SimSession.handle`), câu trả lời của System 2 mà bộ điều khiển giọng nói chuyển tới
(`run_tool_calls`), câu `offline_help` khi System 2 không trả lời (`say_offline`), nút xác nhận
(`confirm` / `decline`) — kết thúc bằng **một** `turn_latency`. Vết ghi xuất từ một log có
`turn_latency` kết thúc bằng **một** `session_summary`, tính lại từ các `turn_latency` lúc xuất,
không lưu trong log. Lời gọi tool từ MCP client bên ngoài không phải lượt: không có
`turn_latency`. Hiện thực: `python/neuroedge/engine/latency.py`.

| Sự kiện | Dữ liệu |
|:---|:---|
| `turn_latency` | `turn` (1, 2, …), `path`, `stages_ms` `{perception, system_two, gate, action, other}`, `total_ms`, `reply_source?`, `usage?` `{prompt_tokens?, completion_tokens?, cost_usd?}` — cộng từ các `system_two_call` của lượt, chỉ khi provider báo (FR-TEL-03) |
| `session_summary` | `turns`, `paths` `{system_1, system_2, fallback, none}` (số lượt), `shares` (tỷ lệ trên tổng số lượt, 4 chữ số), `stages_ms` `{perception, system_two, gate, action, other, total}` — mỗi chặng `{sum, max}`, `usage?` (tổng của các lượt) |

**Chặng** — không chồng lên nhau, cộng lại đúng `total_ms` (ms, số thực 3 chữ số, không âm):

| Chặng | Đo gì |
|:---|:---|
| `perception` | Đọc đầu vào và khớp ngữ pháp lệnh (chữ gõ / transcript → lệnh); với giọng nói qua provider STT (TSK-S3-13), cả thời gian chờ STT — từ lúc gửi âm thanh của lượt (T04) tới lúc có transcript, hoặc tới lúc STT hỏng (`stt_unavailable`) |
| `system_two` | Chờ System 2: mọi `respond` / `reply` của lượt; với giọng nói, từ lúc có transcript tới lúc câu trả lời (hoặc hết giờ chờ) tới |
| `gate` | `ActionContractEngine.evaluate()` — mọi gate của lượt, cộng dồn |
| `action` | Thân các `@action` chạy sau ALLOW, cộng dồn |
| `other` | Phần còn lại: lời nói, điều phối, đường ống tool |

Chặng mở bên trong một chặng khác (một `@action` gọi lại `c.do()`) tính cho chặng ngoài.
Đồng hồ là đồng hồ của `offset_ms` (tiêm được, ảo trong test), nên số đo trong test tất định.

**`path`** — ai phục vụ lượt:

| `path` | Khi nào |
|:---|:---|
| `system_1` | Ngữ pháp lệnh / System 1 của thiết bị phục vụ, System 2 không được hỏi — kể cả câu "có" / "không" nói với câu hỏi `ask` của thiết bị |
| `system_2` | System 2 trả lời (có ít nhất một câu trả lời trong lượt) |
| `fallback` | System 2 được hỏi mà không trả lời được, thiết bị tự trả lời (Q-14): `reply_source` là `offline`, `offline_help` hoặc `knowledge_local` — cả khi một vòng trước của System 2 đã trả lời. Agent không có System 2 thì những câu trả lời đó là `system_1` hoặc `none`, theo việc lệnh có được nhận ra |
| `none` | Không mô hình nào phục vụ: không nhận ra lệnh và không có System 2, hoặc người bấm nút xác nhận, hoặc STT hỏng và thiết bị nói câu offline (`offline_help`, System 2 không được hỏi — `docs/spec/voice_fsm.md` §7) |

`system_one_fallback` (System 1 chính → ngữ pháp cục bộ, FR-MDL-03) vẫn là sự kiện riêng, không
đổi `path`. Hai sự kiện này **không mang chữ** — chế độ ẩn danh không cần băm gì thêm — và **không
vào so khớp quyết định**: replay và golden bỏ qua chúng, nên vết ghi cũ không có chúng vẫn replay,
và vết ghi mới replay trên bản cũ. `neuroedge trace show` in tỷ lệ và chặng, tính lại từ
`turn_latency`.

## 8. Theo target

| Target | Tool call | Máy chủ MCP |
|:---|:---|:---|
| `sim` | Đầy đủ (§1–§7) | `neuroedge mcp serve` qua stdio; `--ui` phục vụ thêm trang web của **cùng phiên** trên 127.0.0.1: lời gọi MCP, lệnh gõ trên trang (kể cả `:sensor`) và nút xác nhận (§6) chạy lần lượt dưới một khóa, nên người trên trang đổi được cảm biến và trả lời câu hỏi `ask` mà lời gọi MCP mở ra |
| `linux` | Đầy đủ | Như `sim`, trên máy thiết bị |
| `esp32s3` | Gate: walker C99 đọc cây `NETR` v1 do `neuroedge build` sinh (Q-23, RFC-0003). Giới hạn tham số (RFC-0005) và `confirms` (RFC-0006) nằm **trong** bố cục đó; `call_source` là một dữ kiện `choice` như mọi tiêu chí, chỉ số của nó do `neuroedge build` sinh (`<gate>.netree.h`). Ngữ pháp → tool call tổng hợp trong C: chưa có (TSK-S5-07) | **Không** chạy trên MCU. MCP cho thiết bị đi qua gateway hoặc một máy `linux` (FR-GW), và thiết bị vẫn tự lượng giá gate. MCU **không làm MCP host**: host (§10) đặt ở nơi System 2 chạy |

Transport MCP mặc định là **stdio**: bên có quyền chạy tiến trình chính là người vận
hành. Transport mạng (Streamable HTTP) có từ TSK-P2-04 (Q-58, NFR-SEC-09), **mặc định tắt**, và chỉ
bật bằng `neuroedge mcp serve --http` kèm đủ cấu hình xác thực (§8.1). Mục cấu hình cho
Claude Desktop do `neuroedge mcp desktop-config` sinh — đường dẫn tuyệt đối, vì Desktop khởi
động server từ `/` với `PATH` tối giản; nó chỉ sinh mục stdio.

Hai quy tắc giữ cho `mcp serve` qua stdio sống sót khi client bỏ rơi nó (`--http` không có chúng: nó nghe cổng, không giữ stdin). Claude Desktop có thể bỏ một tiến
trình trước `initialize` mà vẫn giữ stdin của nó, nên tiến trình không bao giờ nhận được EOF.

- Không có `initialize` sau `--init-timeout` giây (mặc định 30) thì tiến trình thoát 0 và nhả
  cổng. Phiên đã `initialize` không bị giới hạn thời gian.
- Trang `--ui` không bao giờ làm sập MCP. Cổng bận, kể cả `--port` ghi rõ, thì trang chạy ở cổng
  trống và URL thật được in ra stderr.

### 8.1 MCP qua mạng: `mcp serve --http` (TSK-P2-04, Q-58, Q-32)

Cùng một máy chủ, cùng một đường tới phần cứng như stdio: `SimSession.load`, `build_server`, gate,
token phán quyết dùng một lần, HAL, vết ghi (băm theo mặc định). Chỉ **cửa** khác (`mcp_http.py`);
không có cờ nào tắt gate, và `call_source` vẫn là `mcp` (§5). MCP SDK cấp ứng dụng Streamable HTTP,
lớp kiểm bearer và metadata tài nguyên được bảo vệ (RFC 9728, `/.well-known/oauth-protected-resource`);
`mcp_http.py` cấp ngữ cảnh TLS, bộ kiểm token và lớp gác quanh chúng.

**Khởi động đóng.** `--http` đòi **cả sáu**: `--tls-cert` và `--tls-key` (chứng chỉ máy chủ), `--client-ca`
(CA ký chứng chỉ thiết bị — mTLS), `--issuer` (URL https của máy chủ cấp quyền), `--audience` (URL https
của chính MCP server, là `aud` của mọi token; đường dẫn của nó là đường dẫn của endpoint, mặc định `/mcp`),
`--jwks` (khoá công khai ký token của issuer). Thiếu bất kỳ cái nào, hoặc tệp không đọc được (chứng chỉ
không khớp khoá, CA rỗng, JWKS không có khoá ký), thì **thoát mã 1 với lỗi ba phần, trước khi dựng phiên và trước
khi mở bất kỳ socket nào**. Bind vào địa chỉ không phải loopback (`--host`) không đòi thêm gì — vì cấu hình
đủ đã là điều kiện cho mọi địa chỉ. Mặc định nghe `127.0.0.1`, cổng 8443 (`--port 0` chọn cổng trống).
`--http` không đi cùng `--ui` (mã 2: trang chung phiên và trả lời câu hỏi `ask` như người trên thiết bị),
và các cờ mạng không có `--http` bị từ chối (mã 1), không bị lờ đi. `--required-scope` (mặc định `neuroedge:call`)
là cờ duy nhất có mặc định.

**Lớp 1 — mTLS, TLS 1.3 trở lên (NFR-SEC-04).** Chứng chỉ client **bắt buộc** và phải do `--client-ca` ký;
client không có (hoặc do CA lạ ký, hoặc chỉ nói TLS 1.2) không qua được bắt tay, nên không có byte HTTP nào
tới ứng dụng. Việc này xảy ra ở tầng TLS, trước mọi mã của ứng dụng nên **không có sự kiện vết ghi**; nhật ký
của uvicorn trên stderr là dấu vết duy nhất.

**Lớp 2 — một token bearer cho mỗi thiết bị.** Máy chủ là *resource server* OAuth 2.1; việc cấp token là của
`--issuer` (ngoài phạm vi), và máy chủ chỉ kiểm, không gọi mạng nào để kiểm. Token là JWT (RFC 9068); mọi
điều kiện sau phải đúng, nếu không thì **401** (kèm `WWW-Authenticate: Bearer`, trỏ tới metadata tài nguyên) và
không gì được chuyển tiếp tới MCP:

| Kiểm | Chi tiết |
|:---|:---|
| Chữ ký | Chỉ thuật toán bất đối xứng (`RS*`, `PS*`, `ES*`, `EdDSA`) với khoá của `--jwks`, chọn theo `kid` (không `kid` thì chỉ khi có đúng một khoá). `none` và `HS*` không bao giờ được nhận. JWKS có khoá riêng (`d`), khoá đối xứng (`oct`) hoặc không có khoá ký thì **không khởi động**: một resource server giữ được khoá ký là một resource server tự làm giả được token của mình |
| `iss`, `aud`, `exp`, `sub` | Đều bắt buộc. `iss` bằng `--issuer`; `aud` chứa `--audience` (RFC 8707); `exp` chưa qua, không dung sai; `sub` là mã thiết bị |
| Ràng buộc chứng chỉ (RFC 8705) | `cnf.x5t#S256` bắt buộc và phải bằng SHA-256 của chứng chỉ client đang kết nối. Token cấp cho thiết bị A trình bằng chứng chỉ của B là 401; token không ràng buộc cũng là 401. Cả hai cùng bị đánh cắp mới dùng được |
| Phạm vi | Token mang `--required-scope` trong `scope` (chuỗi cách nhau bằng khoảng trắng) hoặc `scp`; thiếu thì **403** (`insufficient_scope`) |

Phiên MCP gắn với người cấp (issuer, `client_id`, `sub`) của token tạo ra nó: thiết bị khác, dù đã xác thực đủ,
không dùng lại được phiên (404; `test_a_session_belongs_to_the_device_that_opened_it`). Mọi 401/403 ghi `mcp_auth_refused` (§7) — chỉ `reason` là chữ cố định, không bao giờ có
token.

**Một đường tới gate.** Một lời gọi đã qua hai lớp là một `tools/call` như của stdio: `ToolCall` có
`source = "mcp"`, schema, `c.do()`, gate, token, HAL; kết quả `BLOCK` vẫn là kết quả, không phải lỗi giao thức (§4).
Lặp một lời gọi bị chặn không đổi được phán quyết: gate tất định, mỗi lần là một `BLOCK` và một chuỗi sự kiện
vết ghi (`tests/test_mcp_http.py`, `TODOS.md` #29; `docs/spec/threat_model.md` §2b). Lời gọi chạy lần lượt (`build_server`), như stdio.

**Chưa có, nói rõ.** Không có danh sách thu hồi: token chết khi hết hạn (nên cấp ngắn hạn) hoặc khi issuer
đổi khoá — `--jwks` đọc **một lần lúc khởi động**, đổi khoá thì khởi động lại; chứng chỉ client bị thu hồi chỉ
hết hiệu lực khi đổi `--client-ca` (không kiểm CRL/OCSP). Token chỉ kiểm lúc **nhận yêu cầu**, nên một luồng
SSE đang mở sống tiếp tới khi đóng dù token trong đó đã hết hạn. Không giới hạn tốc độ ở tầng ứng dụng.
Metadata tài nguyên được bảo vệ phục vụ không cần token (RFC 9728 đòi vậy) — nhưng chỉ sau mTLS.
Chưa có API Python công khai cho cửa mạng (`serve_mcp` vẫn chỉ stdio); chưa có cầu MCP cho MCU (TSK-P2-05, I14).
Chưa kiểm trên hai máy thật: test chạy trong một tiến trình trên 127.0.0.1 với CA tạm.

## 9. Tuân thủ

Một runtime được gọi là **NeuroEdge-gated** khi nó qua corpus
`fixtures/tool_calls/{valid,invalid}/` với `expected_results.yaml` — khép kín hai chiều
như corpus gate: mỗi tệp có một mục, mỗi mục có một tệp (TSK-S3-24).

- **Tệp ca** nêu đầu vào: `agent` (một thư mục của `fixtures/agents/`), `call`
  (`name`, `arguments`, `source` — nguồn do runtime gán như một kết nối), `facts` (ghi đè
  `[sim.facts]`), `sensors` (số đọc giả lập trước lời gọi) và `board` (id một bo mạch của `boards/`, mặc
  định là bo tham chiếu của target — vd. `sim-rpi5` cho agent cần PWM hoặc `motion.*`, RFC-0010, RFC-0011).
- **`expected_results.yaml`** nêu đáp án theo từng tệp: `status`, các trường của §4 (`reason`,
  `failed_criterion`, `on_block`, `escalated_to` phải khớp đúng; `problems` so chuỗi con;
  `confirmation`, `fallback` có/không phải khớp), `pins` — mọi lệnh chân, đúng thứ tự (một
  lệnh `pwm` ghi thêm `frequency_hz` và `duty` — `duty` là giá trị HAL đã lượng tử hoá, RFC-0010 §9.15) —
  và `motion` — mọi lệnh chuyển động và lệnh về trạng thái an toàn của kênh, đúng thứ tự (`command:
  {channel, kind, speed|target, run}`, `safe: {channel, state, cause}`).
- **`valid/`** là lời gọi khớp `inputSchema` tool khai ra (sau phép ép chuỗi của §2): gate quyết
  định, `ALLOW` hoặc `BLOCK`. **`invalid/`** là lời gọi không khớp: tool lạ, tham số lạ, sai kiểu,
  thiếu tham số bắt buộc, tự khai `call_source` ⇒ `REJECTED`; giá trị ngoài giới hạn tham số
  (`minimum`, `maximum`, `enum`, `maxLength` — RFC-0005) ⇒ gate chặn, `BLOCK`
  `argument_out_of_range` (§3). Không lời gọi `invalid/` nào được `ALLOW`. Runner kiểm cả
  phép chia này, nên một ca không nằm nhầm nửa được.

Corpus phủ cả hai không gian tên: agent `bridge-lamp` (gate nói đúng `bridge:muse`, hoặc cả họ `bridge` bằng `call_channel`) và
`open_gate_from_a_bridge_degrades.yaml` của `driveway` (`test_the_corpus_of_tool_calls_covers_every_family`). Runner đóng vai bộ nạp: nó
đăng ký id nó đọc từ `call.source` của ca (§5).

Runner `neuroedge.testing.tool_corpus` chạy mỗi ca qua `dispatch()` thật của một `SimSession`
mới — đúng đường của client MCP và System 2 — rồi so với đáp án. `neuroedge verify` chạy cả
corpus; `pytest tests/test_tool_corpus.py` chạy thêm từng ca qua một client MCP thật và kiểm kết
quả khớp `outputSchema` (§4). Wheel mang corpus (`neuroedge/_data/fixtures/tool_calls/`), nên
bản đã cài cũng tự kiểm được.

Lược đồ phong bì (`tool-call.v1.json`, gồm mô tả tool) và kết quả (`tool-result.v1.json`) đã đóng băng
trong `schemas/` bằng [RFC-0015](../rfc/0015-hop-dong-cho-nguoi-tich-hop.md) (TSK-I6-05, Q-58, Q-66), cùng hình dạng một
lỗi (`error.v1.json`) và danh mục mã lỗi `NE*` dạng máy đọc được (`error-codes.v1.json`, Q-63), để OSS khác hiện
thực profile mà không đọc mã Python. Mỗi ca của corpus thẩm định theo chúng (`python/tests/test_contracts.py`:
`test_every_tool_call_corpus_case_validates_against_the_tool_call_schema`,
`test_every_tool_call_corpus_result_validates_against_the_tool_result_schema`); `fixtures/contracts/` là corpus phản chứng của
các lược đồ đó, khép kín hai chiều. Từ đây profile là **v1** ở phần hình dạng; đổi hình dạng là RFC (`CONTRIBUTING.md` §3).
Giấy phép của corpus tuân thủ chưa thuộc phần Apache-2.0: `TODOS.md` #57.

## 10. NeuroEdge làm MCP client (Q-27)

System 2 là một **MCP host**: mọi tool nó dùng đều đi qua một MCP client
(`ToolHost`, `python/neuroedge/mcp_host.py`), tới hai loại server.

```text
                  ┌─────────────────────── ToolHost ───────────────────────┐
System 2 ─tool──► │ agent: in-process → build_server(source="system_two")   │─► dispatch() → gate → HAL
 ▲ (≤ max_rounds) │ news:  stdio → [mcp.servers.news], chỉ tool trong allowlist │─► dữ liệu không tin cậy
 └── kết quả ◄─── └────────────────────────────────────────────────────────┘
```

Sáu quy tắc:

1. **Tool của thiết bị chỉ đến được qua MCP server của chính agent.** Mọi lời gọi vẫn qua
   §2. `call_source = system_two` gắn theo kết nối (§5). Lỗi hợp đồng ném ra nguyên vẹn
   qua kết nối in-process, không thành kết quả MCP. Bản cài lõi không có extra `mcp`:
   kết nối này thành lời gọi trực tiếp — cùng nguồn, cùng `dispatch()`; server bên ngoài
   bị bỏ qua kèm lý do.
2. **MCP server bên ngoài chỉ để lấy thông tin.** `agent.toml` liệt kê tường minh tool
   được dùng (`tools = [...]`) — tác giả agent khẳng định chúng không có hiệu ứng vật lý.
   Tool ngoài allowlist bị ẩn khỏi mô hình và gọi tới thì `REJECTED`. Annotation
   `readOnlyHint` do server tự khai **không** được tin. Tool của bên thứ ba có hiệu ứng
   vật lý (ví dụ Home Assistant) **PHẢI** được bọc thành `@action` có gate; thân hàm gọi
   MCP đó và chỉ chạy được trong `c.do()`. Tên `server__tool` trùng tên `@action` ⇒
   `neuroedge build` báo lỗi.
3. **Kết quả tool bên ngoài là dữ liệu không tin cậy.** Nó chỉ trả lại mô hình, đánh dấu
   `"trust": "untrusted data …"`, không bao giờ được phân tích thành lệnh. Vết ghi lưu
   `mcp_tool_result` (trường ở §7) — không lưu nội dung. Mô
   hình "nghe lời" một nội dung bị cài lệnh thì lời gọi của nó vẫn qua gate
   (`test_prompt_injection_in_the_news_still_meets_the_gate`).
4. **Server không kết nối được thì bỏ qua, và nói ra**: ghi `mcp_server_unavailable` (§7); tool của thiết bị vẫn chạy. Mô hình được báo trong `instructions` nguồn nào
   đang tắt và vì sao (kể cả thiếu SDK `mcp`), để nói với người dùng là *tạm thời không lấy
   được* — không nói "không có công cụ", không bịa. REPL in cảnh báo; banner của `run` liệt
   kê server và trạng thái. Mất mạng hẳn ⇒ không có System 2 ⇒ host không mở; ngữ pháp cục
   bộ dispatch thẳng (§1, Q-14).
5. **Dự phòng cục bộ cho hành động**: System 2 không trả lời được một câu tự do ⇒ thiết bị
   **nói các lệnh cục bộ vẫn dùng được** (một câu mẫu mỗi lệnh có `tool` trong
   `commands.toml`, `reply_source = offline_help`). Không bao giờ đoán hành động từ một câu
   gần giống — đoán sai là hành động vật lý sai; người nói lại lệnh và lệnh đó đi qua gate
   như mọi lần.
6. **Vòng có giới hạn** (FR-MDL-11): kết quả mỗi tool quay lại mô hình trong
   `state["messages"]`, tối đa `max_rounds` vòng (mặc định 4, 1..16); quá ⇒
   `system_two_rounds_exceeded`. Gate trả `ask` ⇒ dừng vòng và thiết bị nói `message` của
   gate; câu hỏi chỉ được mở khi §6 cho phép (có `confirms` và một lời "có" là đủ). Mô hình
   không được trả lời thay người (§6).

Cấu hình (`agent.toml`, không thuộc `schemas/`):

```toml
[mcp]
max_rounds = 4

[mcp.servers.news]                # tool của nó đưa cho mô hình là news__<tool>
command = "python"                # "python" / "python3" = trình thông dịch đang chạy
args    = ["mcp/news_server.py"]  # tương đối với thư mục agent
tools   = ["headlines"]           # allowlist — chỉ công cụ thông tin
# env = { NEWS_FILE = "..." } · timeout_s = 10
```

Model đứng sau System 2 khai ở bảng `[system_two]` của `agent.toml` (LiteLLM hoặc adapter tự viết,
TSK-S2-11, `python/neuroedge/models/providers/`): `tools` và các vòng `state["messages"]` được gửi
đúng dạng function calling OpenAI; tham số tool không phải JSON được chuyển nguyên cho dispatch, nên
lời gọi đó `REJECTED` (§2) — không đoán. Model không trả lời được ⇒ `system_two_unavailable`.

Ví dụ chạy được: `fixtures/agents/home-voice/mcp/news_server.py`. Kết nối mở theo từng
lượt; kết nối bền giữa các lượt và transport HTTP tới server bên ngoài là việc hoãn
(`TODOS.md` #25).
