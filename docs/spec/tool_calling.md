# Gated Tool Profile v0 — đường từ ngôn ngữ tới hành động thực

**Trạng thái:** chuẩn tắc cho `sim` và `linux` từ v0; `esp32s3` theo §8. Quyết định:
Q-24, Q-25, Q-26, Q-27 (`neuroedge-prd.md` §15).
**Mã nguồn:** `python/neuroedge/actions/tools.py` (dispatch), `python/neuroedge/mcp_server.py`
(MCP server), `python/neuroedge/mcp_host.py` (System 2 làm MCP client),
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

```
ToolCall { id: string, name: string, arguments: object, source: string }
```

| Trường | Quy định |
|:---|:---|
| `name` | Tên một `@action` của agent. Mỗi `@action` là đúng một tool |
| `arguments` | Đối tượng JSON; khoá là tên tham số của `@action` |
| `source` | Một trong năm nguồn dưới đây. **Do runtime gán**, không do bên gọi khai |
| `id` | `call_1`, `call_2`… theo thứ tự trong phiên, do dispatcher gán khi rỗng. **KHÔNG ĐƯỢC** là giá trị ngẫu nhiên: vết ghi phải tất định để golden và `--anonymize` ổn định. Id do nhà cung cấp mô hình trả về được giữ nguyên |

| `source` | Nơi phát |
|:---|:---|
| `local_grammar` | Câu khớp `commands.toml` → tool call **tổng hợp** (Q-14). Chạy không mạng |
| `system_one` | Mô hình có cấu trúc (§3.6 proposal) |
| `system_two` | LLM với câu tự do; gọi tool của thiết bị qua kết nối MCP in-process tới chính agent (§10) |
| `mcp` | Client MCP qua `neuroedge mcp serve` |
| `test` | Action CI |

Câu khớp ngữ pháp **PHẢI** trở thành tool call rồi đi qua cùng đường với mọi nguồn khác —
không có nhánh "offline" riêng tới chân.

## 2. Thứ tự dispatch

Mọi tool call, từ mọi nguồn, đi qua `dispatch()` theo đúng thứ tự:

1. Ghi sự kiện `tool_call`.
2. Tool có tồn tại — không ⇒ `REJECTED`.
3. Tham số khớp schema (§3): không có tham số lạ, đủ tham số bắt buộc, đúng kiểu. Chuỗi
   được ép sang số hoặc bool khi schema nói vậy (slot ngữ pháp là chữ); ngoài ra không
   đoán gì. Sai ⇒ `REJECTED`, ghi `tool_call_rejected`.
4. Chèn dữ kiện `call_source` (§5).
5. `c.do(action, **arguments)` → gate → token dùng một lần → thân `@action` → HAL.

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

Nội dung trả về (`ToolResult.content()`; MCP gửi ở cả `structuredContent` và một khối
`text` chứa cùng JSON):

| Trường | Khi nào |
|:---|:---|
| `tool`, `status` | Luôn có |
| `problems` | `REJECTED` — danh sách lý do, mỗi lý do một câu |
| `gate`, `reason`, `failed_criterion`, `on_block`, `message`, `escalated_to` | `BLOCK` — các trường có giá trị |
| `fallback` | `BLOCK` với `on_block: degrade` — kết quả của `fallback_action` đã chạy qua gate riêng của nó: `{tool, status}` và, nếu nó cũng bị chặn, các trường `BLOCK` của nó (đệ quy) |
| `confirmation` | `BLOCK` với `on_block: ask` khi có câu hỏi chờ người (§6) |

Máy chủ MCP khai lược đồ này ở `outputSchema` của mỗi tool (`result_schema()` trong
`actions/tools.py`; `neuroedge mcp tools --json` in ra cùng `inputSchema`). Client MCP kiểm
`structuredContent` của mọi kết quả **không** lỗi theo lược đồ đó; kết quả `REJECTED`
(`isError: true`) không được SDK kiểm, nhưng vẫn khớp lược đồ (tool lạ thì khớp lược đồ không
ghim tên `tool`).

## 5. `call_source`

Dispatcher chèn dữ kiện `call_source = <source>` vào ngữ cảnh gate trong lúc `c.do()`
chạy, rồi trả lại dữ kiện cũ. Gate đọc nó như mọi tiêu chí `choice`:

```yaml
evaluate:
  call_source:
    type: choice
    options: [local_grammar, system_one, system_two, mcp, test]
    instructions: Nơi phát lời gọi — do runtime chèn, không suy từ lời nói
allow_when: call_source in ["local_grammar", "system_one"]   # MCP không mở được cửa
```

Nguồn **gắn theo kết nối**, do runtime tạo kết nối đó: `neuroedge mcp serve` là `mcp`; kết nối in-process của System 2 là `system_two` (`build_server(session, source=...)`).

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
- Nguồn `system_two` và `mcp` **KHÔNG ĐƯỢC** phát lời xác nhận. Nếu được, một mô hình bị
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
- Xác nhận không bỏ qua gate: gate được **lượng giá lại** với dữ kiện **hiện tại** và
  `call_source` của **yêu cầu gốc**; chỉ tiêu chí trong `confirms` coi như đạt. Mọi tiêu chí
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
| `mcp_tool_result` | `id`, `server`, `tool`, `status`, `sha256`, `bytes` — không lưu nội dung (§10 quy tắc 3) | Q-27 |
| `mcp_server_unavailable` | `server`, `reason` (§10 quy tắc 4) | Q-27 |
| `system_two_call` | `provider`, `model`, `task`, `latency_ms`, `status`, `prompt_tokens?`, `completion_tokens?`, `cost_usd?`, `error?` — không prompt, không key; replay bỏ qua | FR-MDL-06 |
| `system_two_unavailable` | `task`, `reason` — model không trả lời được | FR-MDL-06 |
| `system_two_rounds_exceeded` | `task`, `rounds` — quá `max_rounds` (§10 quy tắc 6) | FR-MDL-11 |
| `system_one_call` | `provider`, `model`, `criterion`, `latency_ms`, `status` (`ok` · `unavailable`), `reason?` (lý do `Unavailable`: `offline`, `timeout`, `rate_limited`, `refused`, `malformed`, `empty`), `http_status?`, `confidence?`, `served_by?` (bản model đã trả lời), `prompt_tokens?`, `completion_tokens?`, `cost_usd?` — mỗi lượt SystemOne hỏi model cloud một tiêu chí (`[system_one]`); không state, không chữ, không key; thiếu key thì không gọi, không ghi; replay bỏ qua | TSK-I4-02 |

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

Transport MCP ở v1.0 chỉ là **stdio**: bên có quyền chạy tiến trình chính là người vận
hành. Transport HTTP cần xác thực và là việc hoãn (`TODOS.md` #24). Mục cấu hình cho
Claude Desktop do `neuroedge mcp desktop-config` sinh — đường dẫn tuyệt đối, vì Desktop khởi
động server từ `/` với `PATH` tối giản.

Hai quy tắc giữ cho `mcp serve` sống sót khi client bỏ rơi nó. Claude Desktop có thể bỏ một tiến
trình trước `initialize` mà vẫn giữ stdin của nó, nên tiến trình không bao giờ nhận được EOF.

- Không có `initialize` sau `--init-timeout` giây (mặc định 30) thì tiến trình thoát 0 và nhả
  cổng. Phiên đã `initialize` không bị giới hạn thời gian.
- Trang `--ui` không bao giờ làm sập MCP. Cổng bận, kể cả `--port` ghi rõ, thì trang chạy ở cổng
  trống và URL thật được in ra stderr.

## 9. Tuân thủ

Một runtime được gọi là **NeuroEdge-gated** khi nó qua corpus
`fixtures/tool_calls/{valid,invalid}/` với `expected_results.yaml` — khép kín hai chiều
như corpus gate: mỗi tệp có một mục, mỗi mục có một tệp (TSK-S3-24).

- **Tệp ca** nêu đầu vào: `agent` (một thư mục của `fixtures/agents/`), `call`
  (`name`, `arguments`, `source` — nguồn do runtime gán như một kết nối), `facts` (ghi đè
  `[sim.facts]`) và `sensors` (số đọc giả lập trước lời gọi).
- **`expected_results.yaml`** nêu đáp án theo từng tệp: `status`, các trường của §4 (`reason`,
  `failed_criterion`, `on_block`, `escalated_to` phải khớp đúng; `problems` so chuỗi con;
  `confirmation`, `fallback` có/không phải khớp) và `pins` — mọi lệnh chân, đúng thứ tự.
- **`valid/`** là lời gọi khớp `inputSchema` tool khai ra (sau phép ép chuỗi của §2): gate quyết
  định, `ALLOW` hoặc `BLOCK`. **`invalid/`** là lời gọi không khớp: tool lạ, tham số lạ, sai kiểu,
  thiếu tham số bắt buộc, tự khai `call_source` ⇒ `REJECTED`; giá trị ngoài giới hạn tham số
  (`minimum`, `maximum`, `enum`, `maxLength` — RFC-0005) ⇒ gate chặn, `BLOCK`
  `argument_out_of_range` (§3). Không lời gọi `invalid/` nào được `ALLOW`. Runner kiểm cả
  phép chia này, nên một ca không nằm nhầm nửa được.

Runner `neuroedge.testing.tool_corpus` chạy mỗi ca qua `dispatch()` thật của một `SimSession`
mới — đúng đường của client MCP và System 2 — rồi so với đáp án. `neuroedge verify` chạy cả
corpus; `pytest tests/test_tool_corpus.py` chạy thêm từng ca qua một client MCP thật và kiểm kết
quả khớp `outputSchema` (§4). Wheel mang corpus (`neuroedge/_data/fixtures/tool_calls/`), nên
bản đã cài cũng tự kiểm được.

Lược đồ phong bì và kết quả sẽ đóng băng thành `schemas/` khi corpus ổn định và có một
client bên ngoài dùng (`TODOS.md` #23). Cho tới lúc đó, profile là **v0** và đổi được
bằng PR thường kèm cập nhật tài liệu này.

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
