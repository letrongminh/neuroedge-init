# 06 · Luồng lúc chạy (Dynamic views)

> **Phạm vi:** các luồng quan trọng, mỗi luồng một sơ đồ trình tự hoặc trạng thái, gọi đúng tên hàm
> trong mã. **Nguồn:** `sim/session.py`, `actions/`, `engine/gate.py`, `mcp_server.py`, `mcp_host.py`,
> `models/system.py`, `perception/`, `testing/`, `docs/spec/voice_fsm.md`, `docs/spec/tool_calling.md`.

Mọi luồng dưới đây, dù bắt đầu từ đâu, đều gặp nhau ở cùng một đoạn: `dispatch()` → `Conversation.do`
→ `ActionContractEngine.evaluate` → `TokenLedger` → HAL ([`05`](05-code-gate-hal-c4l4.md) §5). Sơ đồ
chỉ vẽ đoạn đó một lần trong §1 và gọi tên nó ở các luồng khác.

## 1. Một lượt gõ lệnh

`neuroedge run -c "mở cửa phòng 101"` trên `sim`.

```mermaid
sequenceDiagram
    autonumber
    participant CLI as cli run
    participant S as SimSession
    participant G as CommandGrammar
    participant D as dispatch()
    participant C as Conversation
    participant E as Engine
    participant H as SimHAL
    participant T as EventLog
    CLI->>S: SimSession.load() then handle(text) in a fresh event loop
    S->>H: type_text, audio_in — text_input
    S->>G: recognize(utterance)
    G-->>S: Recognition(intent, confidence, slots)
    S->>T: intent_extracted
    S->>S: ToolCall(tool, arguments, source=local_grammar)
    S->>S: gate facts = sim.facts + slot facts + sensor facts
    S->>D: dispatch(conversation, tools, call)
    D->>T: tool_call
    D->>C: do(spec, arguments) with call_source = local_grammar
    C->>E: evaluate — gate_evaluation_begin, gate_facts, gate_evaluation_result
    C->>H: token, body, digital.out — actuator_command
    D-->>S: ToolResult ALLOW or BLOCK
    S->>T: turn_latency (perception, gate, action, other)
    S-->>CLI: Turn, rendered with verdict and pins
```

Câu không khớp ngữ pháp: có `[system_two]` thì đi luồng §4; không thì `command_not_recognized` và
thiết bị nói những lệnh cục bộ còn dùng được (`offline_help`).

## 2. Hỏi lại và xác nhận (`on_block: ask`, RFC-0006)

```mermaid
sequenceDiagram
    autonumber
    participant X as any caller
    participant C as Conversation
    participant E as Engine
    participant B as ConfirmationBook
    participant P as person at the device
    X->>C: do(action)
    C->>E: evaluate
    E-->>C: BLOCK, on_block ask, confirms answerable
    C->>B: open() — tool_confirm_requested, TTL = max(p95 x 3, 10 s)
    C-->>X: BLOCK with confirmation (caller is told a person must answer)
    P->>B: yes via local_grammar (typed or spoken) or ui (POST /confirm, same origin)
    B->>B: take(id, source, current gate digest)
    alt source not local_grammar or ui, expired, used, or gate changed
        B-->>P: tool_confirm_rejected, nothing runs
    else accepted
        B-->>C: tool_confirmed
        C->>E: evaluate(confirmed=True) — only the confirms criteria are waived
        E-->>C: ALLOW or still BLOCK on the other criteria
    end
```

- System 2 và client MCP **không có công cụ xác nhận** nào; câu hỏi do chính lời gọi của System 2 tạo
  ra thì System 2 không trả lời được (Q-26).
- Câu "có" nói ra chỉ trả lời câu hỏi của **chính lượt đó** (Q-46).

## 3. Lời gọi MCP

```mermaid
sequenceDiagram
    autonumber
    participant CL as MCP client
    participant M as mcp serve (stdio)
    participant S as SimSession
    participant D as dispatch()
    participant UI as sim page (optional)
    CL->>M: tools/list
    M-->>CL: one tool per @action (inputSchema, outputSchema)
    CL->>M: tools/call name, arguments
    M->>M: ToolCall(source=mcp) under the turns lock (one call at a time)
    M->>S: call_tool(call) — utterance empty, gate facts from the session
    S->>D: dispatch — gate, token, HAL as in section 1
    D-->>M: ToolResult
    M-->>CL: CallToolResult — isError only for REJECTED, BLOCK is a normal result
    M->>UI: notify() — the page updates over SSE
```

Lời gọi MCP không có lời người nói, nên `[system_one]` không gửi gì lên model: tiêu chí đó rơi về ngữ
pháp hoặc chặn. Một gate có thể từ chối riêng nguồn `mcp` qua tiêu chí `call_source`.

## 4. Lượt System 2 (LLM), kèm MCP server bên ngoài

```mermaid
sequenceDiagram
    autonumber
    participant S as SimSession
    participant TH as ToolHost
    participant LLM as SystemTwo (LiteLLM)
    participant OWN as agent's own MCP server
    participant EXT as external MCP server
    participant D as dispatch()
    S->>TH: open for this turn — in-process client to OWN, stdio to EXT (allowlist)
    loop up to mcp.max_rounds (default 4)
        S->>LLM: respond(state: utterance, tools, messages)
        LLM-->>S: text or tool_calls — system_two_call traced, no prompt, no key
        alt a device tool
            S->>TH: call(name, arguments)
            TH->>OWN: tools/call with source system_two
            OWN->>D: dispatch — gate, token, HAL
        else an information tool
            TH->>EXT: tools/call
            EXT-->>TH: result marked untrusted data, only its digest traced
        end
    end
    S->>S: say the reply, or the gate's ask message (the model may not answer it)
```

Nhà cung cấp không trả lời được ⇒ `system_two_unavailable`, thiết bị nói câu offline. Nội dung từ MCP
server bên ngoài có chèn lệnh (prompt injection) thì lời gọi nó dẫn tới vẫn phải qua gate
(`test_mcp_host.py::test_prompt_injection_in_the_news_still_meets_the_gate`).

## 5. Model của System 1 và khi mất mạng

`SystemOne` là `FactSource` của engine. Với `[system_one]`, nó hỏi model chính (Jev qua System One API)
cho các tiêu chí được giao, trong phần ngân sách còn lại trừ 50 ms dự phòng; model không dùng được thì
ngữ pháp lệnh quyết.

```mermaid
sequenceDiagram
    autonumber
    participant E as Engine gather
    participant S1 as SystemOne
    participant BR as DegradationBreaker
    participant JEV as Jev (System One API)
    participant GR as GrammarAdjudicator
    E->>S1: adjudicate(criterion, definition, state, deadline_ms)
    alt criterion not delegated, offline, or breaker open
        S1->>GR: adjudicate
    else delegated
        S1->>BR: allow_primary?
        S1->>JEV: POST /systemone — only the utterance
        alt well-formed answer, in domain, above threshold
            JEV-->>S1: Fact(value, confidence)
        else offline, timeout, HTTP error, malformed, below threshold
            S1->>BR: record_failure
            S1->>GR: adjudicate — system_one_fallback traced
        end
    end
    S1-->>E: Fact or Unavailable
    Note over E: Unavailable offline or timeout makes the verdict degraded — budget.fail applies
```

```mermaid
stateDiagram-v2
    [*] --> Closed
    Closed --> Open: failure_threshold failures in a row
    Open --> HalfOpen: after cooldown_ms
    HalfOpen --> Closed: primary answers
    HalfOpen --> Open: primary fails again
    note right of Open
        primary skipped, fallback answers
        the breaker routes, it never allows
    end note
```

Không có fallback nào chạy được cho một tiêu chí do model quyết ⇒ `BLOCK` với `gate_unreachable`
(Q-14, tiêu chí ra I4 số 3).

## 6. Thoại

### 6.1 Máy trạng thái hội thoại

Quy phạm ở `docs/spec/voice_fsm.md` §4 (T01–T14). Mọi lần đổi trạng thái ghi `voice_state_changed`.
Máy trạng thái không bao giờ lượng giá gate hay chạm chân.

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> LISTENING: T01 wake word, or speech when VAD activation is on
    LISTENING --> LISTENING: T02 speech ends, silence timer starts · T03 speech resumes, timer cancelled
    LISTENING --> THINKING: T04 end-of-turn silence elapsed, audio to STT
    LISTENING --> IDLE: T05 no speech within listen timeout
    THINKING --> IDLE: T06 empty transcript (reprompt at most max_reprompts) · T08 nothing to say
    THINKING --> SPEAKING: T07 reply starts
    THINKING --> THINKING: T09 think timeout or provider down, offline line
    THINKING --> BARGE_IN: T10 user speaks again
    SPEAKING --> LISTENING: T11 an ask question played to the end, answer turn opens
    SPEAKING --> IDLE: T12 reply done or TTS error
    SPEAKING --> BARGE_IN: T13 user speaks over the reply
    BARGE_IN --> LISTENING: T14 recall pending commands, stop speech, new turn
```

### 6.2 Một lượt thoại từ tệp WAV

```mermaid
sequenceDiagram
    autonumber
    participant F as WAV file
    participant V as VoiceSession (virtual clock)
    participant W as wake word or VAD
    participant STT as STT (primary, then fallback)
    participant S as SimSession
    participant TTS as TTS
    F->>V: 20 ms frames
    V->>W: detect / push
    W-->>V: wake_word_detected or audio_in_vad_start, then vad_end
    V->>STT: audio segment of the turn
    alt primary answers
        STT-->>V: stt_result
    else primary fails and stt.fallback exists
        V->>STT: fallback, with its own bounded deadline — stt_fallback
        Note over V: a late primary answer becomes voice_late_result_dropped, never a command
    end
    V->>S: handle(text, spoken=True) — the same path as a typed turn
    S-->>V: Turn with reply
    V->>TTS: synthesize(reply) — tts_stream_start, then tts_stream_end
```

**Cắt lời** (`docs/spec/voice_fsm.md` §5): người dùng nói khi thiết bị đang nghĩ hoặc đang nói ⇒ loa
dừng, mọi lệnh **chưa giao** tới chân bị huỷ (`actuator_aborted`, lý do
`ACTUATOR_ABORTED_BY_BARGE_IN`) và token của chúng bị đóng. Lệnh đã giao (một xung đang chạy) chạy hết.

**Từ đánh thức hỏng** (mô hình không nạp được, adapter ném lỗi) ⇒ `wake_word_unavailable`, không lượt
nào mở, phiên vẫn chạy.

Phiên thoại hôm nay chạy trong **thời gian ảo** từ tệp WAV; phiên thời gian thực với micro thật chưa có
(`TODOS.md` #45).

## 7. Vòng bằng chứng: ghi, phát lại, so sánh

![E-06 · Vòng bằng chứng](../assets/svg/E-06-evidence-loop.svg)
*Hình E-06 — Một phiên thành vết ghi; vết ghi được tính lại trên từng target và so với bản gốc.*

```mermaid
sequenceDiagram
    autonumber
    participant R as TraceRecorder
    participant F as trace.v1.json
    participant P as TracePlayer
    participant G as GoldenComparator
    R->>F: save() — validated against trace.v1, text hashed unless --raw
    P->>F: load, recorded_steps: facts from gate_facts, degraded reasons, actions
    P->>P: fresh EventLog, HAL for the target, Conversation
    P->>P: replay each step: conversation.do() — verdict, token, body, pins recomputed
    P->>G: compare(replayed, golden)
    G-->>P: safety view: gate sequence, reasons, on_block, pin commands
    Note over G: a difference is SafetyRegressionError NE4002, naming the first divergent event
```

- Phát lại **không gọi model và không đọc máy**: dữ kiện đã ghi được đưa vào lại, còn phán quyết, token
  và lệnh chân được **tính lại**.
- So sánh theo **quyết định** (phán quyết, lý do, `on_block`, lệnh chân), bỏ qua thời gian và chữ nói.
- `neuroedge verify --targets sim,linux,esp32s3` làm việc này cho mọi vết ghi chuẩn mực trên từng target;
  trên `esp32s3`, chính firmware phát lại ba vết ghi chuẩn mực lúc khởi động và gửi kết quả qua UART.

## 8. Từ agent tới chip

```mermaid
sequenceDiagram
    autonumber
    participant U as engineer
    participant B as neuroedge build
    participant I as idf.py (ESP-IDF v5.4)
    participant Q as QEMU or Box-3
    participant R as neuroedge record / verify
    U->>B: build --target esp32s3 --board esp32s3-box-3
    B->>B: every check, render ne_agent, NETR per gate, self-test answers from the host engine
    B-->>U: build/esp32s3 ESP-IDF project, or every problem and exit 1, nothing written
    U->>I: set-target, build (sdkconfig layers)
    I->>Q: flash or merged image
    Q->>Q: boot: self-test, canonical replay, heap line
    Q-->>R: UART NE1 lines
    R->>R: sessions to trace.v1, validate, compare with goldens
```

## 9. Vòng đời một phiên `linux`

1. `SimSession.load(target="linux")` dựng `TypedLinuxHAL` và gọi `preflight`: mọi cảm biến, màn hình,
   thiết bị âm thanh agent cần được kiểm **trước khi** giữ line GPIO nào. Thiếu thứ gì ⇒ lỗi ba phần,
   mã 1, không line nào bị giữ.
2. Lệnh chân tới line của kernel qua libgpiod v2, tìm theo tên. Xung có thời lượng được thả bằng một
   bộ hẹn giờ; `run -c` chờ xung chạy hết trước khi thoát.
3. Thoát — bình thường, Ctrl-D, SIGTERM (client MCP dừng máy chủ), SIGHUP (đóng terminal) — ⇒ mọi line
   về trạng thái nghỉ và được thả. SIGKILL thì không bắt được: đó là lý do an toàn phần cứng vẫn cần
   (`docs/spec/threat_model.md` §3b).

## 10. Luồng quy hoạch

| Luồng | Increment | Kiến trúc đích |
|:---|:---|:---|
| Lượt thoại trên chip | I5 | [`15`](15-target-architecture.md) §2.2 |
| Từ chối do phong bì an toàn vật lý | I2a | [`15`](15-target-architecture.md) §4.2 |
| Nguồn gọi kích hoạt từ sự kiện (`call_source = "trigger"`, TSK-N6-*) | I2d (dời từ I4a theo Q-72) | [`15`](15-target-architecture.md) §4.2 |
| Ý định đa node và mất liên lạc | I14 | [`15`](15-target-architecture.md) §4.3 |
| Dữ kiện thị giác | I2a, I3a | [`15`](15-target-architecture.md) §4.4 |
| Vòng đời hợp đồng nhiệm vụ, báo chủ động, lệnh và lời duyệt qua chat (`planned · Q-72`) | I2d | §11 dưới đây; [`15`](15-target-architecture.md) |
| Cài một NeuroEdge Blueprint (`planned · Q-72`) | I2e | §11.5 dưới đây; [`15`](15-target-architecture.md) |

## 11. Luồng quy hoạch theo Q-72 (`planned · Q-72`)

Chưa có mã cho luồng nào trong mục này. Chúng ghi thiết kế đích của [Q-72](../../../roadmap/neuroedge-prd.md#15-sổ-quyết-định)
cho increment I2d (nhiệm vụ và agent vận hành) và I2e (NeuroEdge Blueprint tối thiểu); tiến độ ở
roadmap §0.2. Phần nào cần RFC thì ghi "chờ RFC".

Hai tiến trình trên máy nhà ([`02`](02-container-c4l2.md)):

- **runtime tin cậy** (24/7, systemd): HAL, gate, thực thi hợp đồng nhiệm vụ, lập lịch, bộ phát hiện
  tất định, adapter kênh chat và kiểm lời duyệt, cửa ra egress;
- **LLM worker không tin cậy**: giữ key LLM của người dùng (BYOK), gọi runtime qua MCP cục bộ như mọi
  client MCP, nguồn do runtime gán, **không bao giờ duyệt** — cùng ranh giới với client MCP ở Q-71.

Mọi lệnh tới chân, dù sinh từ chat, lập lịch hay bộ phát hiện, vẫn đi đúng một đoạn của §1:
`dispatch()` → `Conversation.do` → gate → token → HAL. Adapter chat chỉ gọi tới `dispatch()`, không
import `hal`. Thời lượng, hạn duyệt, watchdog và phản xạ dùng **đồng hồ đơn điệu**; dữ kiện giờ tường
mang trạng thái `unsynced` khi máy chưa đồng bộ giờ, và điều khoản khung giờ coi `unsynced` là thiếu
dữ kiện (fail-closed).

### 11.1 Vòng đời một hợp đồng nhiệm vụ (I2d)

```mermaid
sequenceDiagram
    autonumber
    participant P as person (chat or local UI)
    participant RT as runtime (trusted)
    participant W as LLM worker (untrusted, BYOK)
    participant MC as mission compiler (in runtime)
    participant T as trace segment
    P->>RT: utterance "keep the tank stable, tell me if something is wrong"
    RT->>W: utterance + the fields the user allowed this destination to see
    W->>RT: mission draft via local MCP (source assigned by the runtime)
    alt draft misses a value (threshold, window, device)
        RT->>P: clarifying question written by the worker
        P->>RT: answer, back to the worker
    end
    RT->>MC: compile(draft)
    MC->>MC: lower each clause to the lowest tier that enforces it (reflex, skill, thinking)
    alt contradiction or a clause no tier can enforce
        MC-->>RT: refused, names the clashing clauses
        RT->>P: what clashes, nothing is locked
    else compiled
        MC-->>RT: structured diff + summary of at most 5 lines, built deterministically from the diff
        RT->>P: approval request (section 11.4), never text written by the worker
        P->>RT: approval aimed at that request id
        RT->>RT: lock the mission, digest of the compiled contract
        RT->>T: mission_locked with digest and approver source
    end
```

- Chỉ thiết bị có `ne_gate` mới có tầng phản xạ; thiết bị Home Assistant dừng ở tầng host và bản duyệt
  nói rõ điều đó.
- Bản duyệt là đầu ra của trình biên dịch, không phải chữ của LLM: worker bị lừa không viết được dòng
  nào trong tin duyệt.

### 11.2 Trigger, bộ phát hiện và báo chủ động (I2d)

Mở rộng luồng trigger của Khối N6 (I2d, dời từ I4a theo Q-72; [`15`](15-target-architecture.md) §4.2: chạy không cần phiên
client, `call_source = "trigger"`, `trigger ∉ HUMAN_SOURCES`, debounce, trần tần suất), không phải một
đường song song: lập lịch và bộ phát hiện của hợp đồng nhiệm vụ là nguồn kích hoạt mới của cùng đường đó.

```mermaid
sequenceDiagram
    autonumber
    participant S as scheduler or detector (deterministic)
    participant RT as runtime trigger path
    participant D as dispatch()
    participant B as llm_budget and message budget
    participant W as LLM worker
    participant Q as outbound queue (egress)
    participant CH as paired chat
    S->>RT: event (reading crossed a band, deadline of an obligation) — monotonic clock
    RT->>RT: debounce, rate cap
    opt the mission maps the event to an action
        RT->>D: ToolCall(source=trigger) — gate, token, HAL as in section 1
    end
    RT->>B: may the worker explain this event?
    alt budget left
        B-->>RT: yes
        RT->>W: event + allowed fields
        W-->>RT: explanation or proposal (a proposal is a mission change, section 11.1)
    else budget exhausted
        B-->>RT: no — hard-template alert instead
    end
    RT->>Q: message to a declared destination, batched under the message budget
    Q->>CH: report
```

Bộ phát hiện chạy trước, LLM chỉ được gọi sau khi có sự kiện: phản xạ và cảnh báo mẫu cứng không phụ
thuộc LLM. Bộ phát hiện đọc cảm biến theo chu kỳ trong runtime 24/7 làm `TODOS.md` #48 (đọc cảm biến
chặn event loop) thành rủi ro thật ([`02`](02-container-c4l2.md)).

### 11.3 Lệnh vào từ chat (I2d)

```mermaid
sequenceDiagram
    autonumber
    participant CH as chat platform (Telegram first)
    participant A as chat adapter (in runtime)
    participant W as LLM worker
    participant D as dispatch()
    CH->>A: message from a chat id
    A->>A: paired sender, not a group, inside the message budget
    alt unknown sender or group
        A-->>CH: nothing runs, chat_message_refused traced
    else paired
        A->>W: text as untrusted data
        W->>D: tools/call via local MCP — source assigned by the runtime, never a human source
        D-->>W: ToolResult ALLOW, BLOCK or REJECTED
        W-->>A: reply
        A->>CH: reply through egress
    end
```

Adapter chat không import `hal` và không gọi thẳng `Conversation.do`: mọi lệnh có tác động vật lý đi
qua `dispatch()` như lời gọi MCP ở §3. Một lời gọi bị gate chặn với `on_block: ask` không được worker
trả lời; nó thành yêu cầu duyệt ở §11.4.

### 11.4 Yêu cầu và trả lời duyệt qua chat (I2d, chờ RFC nguồn `chat:<id>`)

Mở rộng §2: hôm nay chỉ `local_grammar` và `ui` trả lời được câu hỏi `ask` (Q-26). Q-72 thêm một đường
qua chat bằng **bản ghi duyệt**, không bằng một tên nguồn mới trong `HUMAN_SOURCES` cho tin "có" tự do.

```mermaid
sequenceDiagram
    autonumber
    participant RT as runtime
    participant A as chat adapter
    participant CH as paired chat
    participant B as ConfirmationBook
    participant T as trace segment
    RT->>RT: approval record {id, nonce, expiry (monotonic), digest of the change, summary of at most 5 lines}
    RT->>T: approval_requested (flushed now)
    A->>CH: request with buttons or a code aimed at id
    CH->>A: answer aimed at id
    A->>A: paired sender? not a group? nonce unused? not expired? digest still matches?
    alt any check fails
        A-->>CH: refused, nothing changes
        A->>T: approval_refused with the failed check (flushed now)
    else all pass
        A->>B: confirmation path with source chat:ID
        B->>RT: gate re-evaluated, only the confirms criteria waived — or the mission change locked
        RT->>T: approval_accepted with sender, request id, summary (flushed now)
    end
    Note over RT,CH: the LLM worker never answers a request, relays never carry approvals
```

Ghép đôi làm tại chỗ; thu hồi, hạn ghép đôi và trần số lời duyệt còn hoãn (`TODOS.md` #62).

### 11.5 Cài một NeuroEdge Blueprint (I2e)

```mermaid
sequenceDiagram
    autonumber
    participant U as installer
    participant CLI as neuroedge blueprint install
    participant IDX as Hub index (static git repository)
    participant SRC as package URL (git or HTTPS)
    participant RT as runtime
    U->>CLI: install by name or by URL
    opt by name
        CLI->>IDX: look up URL, digest, evidence (marked unsigned)
    end
    CLI->>SRC: fetch the whole package
    CLI->>CLI: digest over the whole package: kit, firmware, mission templates, detectors, evidence traces
    alt digest does not match
        CLI-->>U: three-part error (where, why, how), nothing installed
    else match
        CLI->>CLI: validate blueprint.v1, board check, safe_state other than off only from board.v1
        CLI-->>U: install summary; missions start as drafts that still need approval (section 11.1)
        U->>CLI: replay the evidence traces locally (optional)
        CLI->>RT: load the approved missions
    end
```

NeuroEdge Blueprint chỉ khai báo, không mang mã chạy trong runtime. Nó khác Home Assistant Blueprint
(mẫu automation của HA), và có thể mang kèm một HA blueprint.

### 11.6 Nhánh lỗi

| Đường | Lỗi | Xử lý trong thiết kế | Người dùng thấy |
|:---|:---|:---|:---|
| Runtime ↔ LLM worker | worker chết hoặc treo | runtime vẫn chạy phản xạ, bộ phát hiện, cảnh báo mẫu cứng; khởi động lại worker | tin "phân tích tạm ngưng"; cảnh báo vẫn tới |
| Runtime → kênh chat | API của nền tảng chat lỗi | hàng đợi có hạn + cảnh báo tại chỗ trên UI | cảnh báo trên UI; tin tới trễ, có dấu thời gian |
| LLM provider | hết `llm_budget` | phản xạ + cảnh báo mẫu cứng | tin "đã hết ngân sách phân tích" |
| Duyệt qua chat | yêu cầu hết hạn | không duyệt, ghi vết | tin "yêu cầu đã hết hạn" |
| Duyệt qua chat | trả lời từ tài khoản lạ hoặc nhóm | từ chối, ghi vết | không có gì thay đổi |
| Relay (`planned · Q-72`, ngoài I2d/I2e) | relay sập | không ảnh hưởng an toàn; mất truy cập từ xa | không mở được trang từ xa |
| Đồng hồ | mất điện, chưa có NTP/RTC | dữ kiện giờ `unsynced` ⇒ điều khoản khung giờ thiếu dữ kiện ⇒ chặn | bản duyệt, UI báo đồng hồ chưa đồng bộ |
| Vết ghi | mất điện giữa một đoạn | mất tối đa phần đuôi sự kiện thường; chặn và duyệt đã flush | `replay` báo đoạn cụt |
| Cài NeuroEdge Blueprint | digest không khớp | từ chối cài | lỗi ba phần |

