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
| `BLOCK` | Gate chặn (mọi `on_block`, Q-17) | Không đổi | `false` |
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
| `fallback` | `BLOCK` với `on_block: degrade` — kết quả của `fallback_action` *(chưa có — TSK-S3-24)* |

Máy chủ MCP **NÊN** khai lược đồ này ở `outputSchema` của mỗi tool *(chưa có —
TSK-S3-24)*.

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
`fixtures/agents/home-voice/gates/`.

## 6. Xác nhận `on_block: ask` (Q-26)

`ask` nghĩa là *hỏi lại người*. Vì vậy:

- Chỉ **người, qua kênh của thiết bị**, được xác nhận: giọng nói hoặc chữ gõ khớp ngữ
  pháp (`local_grammar`), hoặc nút trên UI của thiết bị.
- Nguồn `system_two` và `mcp` **KHÔNG ĐƯỢC** phát lời xác nhận. Nếu được, một mô hình bị
  prompt injection, hoặc một agent tự động phía client, sẽ tự trả lời câu hỏi an toàn
  dành cho người.
- Lời xác nhận gắn với `call_id` và `gate_digest` của lần bị chặn, dùng **một lần**, và
  hết hạn sau TTL (mặc định bằng TTL của token, `p95 × 3`, tối thiểu 10 giây — con số chốt
  ở TSK-S3-26).
- Xác nhận không bỏ qua gate: nó thêm dữ kiện `human_confirmed = true` rồi **lượng giá
  lại** chính gate đó. Gate phải tự khai `human_confirmed` trong `allow_when` thì xác nhận
  mới có tác dụng — gate không khai thì `ask` chỉ còn là thông báo.

Hôm nay (v0): `ask` chặn, nói `message`, ghi sự kiện (Q-17); vòng xác nhận là TSK-S3-26.

## 7. Vết ghi

| Sự kiện | Dữ liệu | Có từ |
|:---|:---|:---|
| `tool_call` | `id`, `name`, `arguments`, `source` | v0 |
| `tool_call_rejected` | `id`, `name`, `problems` | v0 |
| `tool_confirm_requested` | `id`, `gate`, `message`, `expires_ms` | TSK-S3-26 |
| `tool_confirmed` | `id`, `source` | TSK-S3-26 |

Trường `type` của sự kiện trong `trace.v1` là chuỗi mở, nên thêm sự kiện **không** cần
RFC. Replay (`testing/player.py`) tính lại từng lần lượng giá gate từ `gate_facts` đã
ghi — kể cả `call_source` — nên một lời gọi từ LLM replay tất định mà không hỏi lại mô
hình. Lời gọi `REJECTED` không tới gate nên không có trong phán quyết replay.

## 8. Theo target

| Target | Tool call | Máy chủ MCP |
|:---|:---|:---|
| `sim` | Đầy đủ (§1–§7) | `neuroedge mcp serve` qua stdio; `--ui` phục vụ thêm trang web của **cùng phiên** trên 127.0.0.1, lời gọi MCP và lệnh gõ trên trang chạy lần lượt dưới một khóa |
| `linux` | Đầy đủ | Như `sim`, trên máy thiết bị |
| `esp32s3` | Ngữ pháp → tool call tổng hợp trong C; tham số kiểm bằng bảng do `neuroedge build` sinh cạnh cây quyết định (Q-23); `call_source` là một byte trong ngữ cảnh walker | **Không** chạy trên MCU. MCP cho thiết bị đi qua gateway hoặc một máy `linux` (FR-GW), và thiết bị vẫn tự lượng giá gate. MCU **không làm MCP host**: host (§10) đặt ở nơi System 2 chạy |

Transport MCP ở v1.0 chỉ là **stdio**: bên có quyền chạy tiến trình chính là người vận
hành. Transport HTTP cần xác thực và là việc hoãn (`TODOS.md` #24). Mục cấu hình cho
Claude Desktop do `neuroedge mcp desktop-config` sinh — đường dẫn tuyệt đối, vì Desktop khởi
động server từ `/` với `PATH` tối giản.

## 9. Tuân thủ

Một runtime được gọi là **NeuroEdge-gated** khi nó qua corpus
`fixtures/tool_calls/{valid,invalid}/` với `expected_results.yaml` — khép kín hai chiều
như corpus gate: mỗi tệp có một mục, mỗi mục có một tệp (TSK-S3-24). Mỗi mục nêu tool
call, dữ kiện, và kết quả mong đợi (`status`, `failed_criterion`, lệnh chân).

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

Năm quy tắc:

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
   `mcp_tool_result{id, server, tool, status, sha256, bytes}` — không lưu nội dung. Mô
   hình "nghe lời" một nội dung bị cài lệnh thì lời gọi của nó vẫn qua gate
   (`test_prompt_injection_in_the_news_still_meets_the_gate`).
4. **Server không kết nối được thì bỏ qua**, ghi `mcp_server_unavailable{server, reason}`;
   tool của thiết bị vẫn chạy. Mất mạng hẳn ⇒ không có System 2 ⇒ host không mở; ngữ
   pháp cục bộ dispatch thẳng (§1, Q-14).
5. **Vòng có giới hạn** (FR-MDL-11): kết quả mỗi tool quay lại mô hình trong
   `state["messages"]`, tối đa `max_rounds` vòng (mặc định 4, 1..16); quá ⇒
   `system_two_rounds_exceeded`. Gate trả `ask` ⇒ dừng vòng, thiết bị nói câu hỏi — mô
   hình không được trả lời thay người (§6).

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

Ví dụ chạy được: `fixtures/agents/home-voice/mcp/news_server.py`. Kết nối mở theo từng
lượt; kết nối bền giữa các lượt và transport HTTP tới server bên ngoài là việc hoãn
(`TODOS.md` #25).
