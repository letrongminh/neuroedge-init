# 06 · Runtime flows (Dynamic views)

> **Scope:** the important flows, each with a sequence or state diagram, calling functions by their
> exact names in the code. **Source:** `sim/session.py`, `actions/`, `engine/gate.py`, `mcp_server.py`,
> `mcp_host.py`, `models/system.py`, `perception/`, `testing/`, `docs/spec/voice_fsm.md`,
> `docs/spec/tool_calling.md`.

Every flow below, wherever it starts, meets at the same segment: `dispatch()` → `Conversation.do`
→ `ActionContractEngine.evaluate` → `TokenLedger` → HAL ([`05`](05-code-gate-hal-c4l4.md) §5). The
diagrams draw that segment once in §1 and call it by name in the other flows.

## 1. A typed command turn

`neuroedge run -c "mở cửa phòng 101"` on `sim`.

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

A sentence that does not match the grammar: with `[system_two]` it goes to the flow in §4; otherwise
`command_not_recognized` and the device speaks the local commands that still work (`offline_help`).

## 2. Ask and confirmation (`on_block: ask`, RFC-0006)

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

- System 2 and the MCP client have **no confirmation tool**; a question created by System 2's own call
  cannot be answered by System 2 (Q-26).
- A spoken "yes" only answers the question of **that very turn** (Q-46).

## 3. MCP calls

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

An MCP call has no spoken words, so `[system_one]` sends nothing to the model: that criterion falls
back to grammar or blocks. A gate can refuse the `mcp` source specifically through the `call_source`
criterion.

## 4. A System 2 (LLM) turn, with an external MCP server

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

The provider cannot answer ⇒ `system_two_unavailable`, the device speaks an offline line. If content
from an external MCP server contains an injected command (prompt injection), the call it leads to still
has to pass the gate (`test_mcp_host.py::test_prompt_injection_in_the_news_still_meets_the_gate`).

## 5. The System 1 model and when offline

`SystemOne` is the engine's `FactSource`. With `[system_one]`, it asks the primary model (Jev via the
System One API) for the delegated criteria, within the remaining budget minus 50 ms of reserve; if the
model is not usable, the command grammar decides.

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

No fallback can run for a model-decided criterion ⇒ `BLOCK` with `gate_unreachable` (Q-14, the third
I4 exit criterion).

## 6. Voice

### 6.1 The conversation state machine

Normative in `docs/spec/voice_fsm.md` §4 (T01–T14). Every state change writes `voice_state_changed`.
The state machine never evaluates a gate or touches a pin.

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

### 6.2 One voice turn from a WAV file

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

**Barge-in** (`docs/spec/voice_fsm.md` §5): the user speaks while the device is thinking or speaking ⇒
the speaker stops, every command **not yet delivered** to a pin is aborted (`actuator_aborted`, reason
`ACTUATOR_ABORTED_BY_BARGE_IN`) and its token is closed. A delivered command (a pulse already running)
runs to the end.

**A broken wake word** (model fails to load, adapter throws) ⇒ `wake_word_unavailable`, no turn opens,
the session keeps running.

Voice sessions today run in **virtual time** from a WAV file; a real-time session with a real
microphone does not exist yet (`TODOS.md` #45).

## 7. The evidence loop: record, replay, compare

![E-06 · Evidence loop](../assets/svg/E-06-evidence-loop.svg)
*Figure E-06 — A session becomes a trace; the trace is recomputed on each target and compared with the original.*

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

- Replay **calls no model and reads no machine**: the recorded facts are fed back in, while verdicts,
  tokens and pin commands are **recomputed**.
- Comparison is by **decision** (verdict, reason, `on_block`, pin commands), ignoring time and spoken
  words.
- `neuroedge verify --targets sim,linux,esp32s3` does this for every canonical trace on each target; on
  `esp32s3`, the firmware itself replays the three canonical traces at boot and sends the results over
  UART.

## 8. From agent to chip

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

## 9. Lifecycle of a `linux` session

1. `SimSession.load(target="linux")` builds `TypedLinuxHAL` and calls `preflight`: every sensor,
    display and audio device the agent needs is checked **before** any GPIO line is held. Anything
    missing ⇒ three-part error, exit code 1, no line held.
2. Pin commands reach the kernel line through libgpiod v2, looked up by name. A pulse with a duration
    is released by a timer; `run -c` waits for the pulse to finish before exiting.
3. Exit — normal, Ctrl-D, SIGTERM (MCP client stops the server), SIGHUP (terminal closed) — ⇒ every
    line returns to the idle state and is released. SIGKILL cannot be caught: that is why hardware
    safety is still needed (`docs/spec/threat_model.md` §3b).

## 10. Planned flows

| Flow | Increment | Target architecture |
|:---|:---|:---|
| On-chip voice turn | I5 | [`15`](15-target-architecture.md) §2.2 |
| Rejection by physical safety envelope | I2a | [`15`](15-target-architecture.md) §4.2 |
| Event trigger call source (`call_source = "trigger"`, TSK-N6-*) | I2d (moved from I4a by Q-72) | [`15`](15-target-architecture.md) §4.2 |
| Multi-node intent and communication loss | I14 | [`15`](15-target-architecture.md) §4.3 |
| Vision facts | I2a, I3a | [`15`](15-target-architecture.md) §4.4 |
| Mission contract lifecycle, proactive reports, commands and approvals over chat (`planned · Q-72`) | I2d | §11 below; [`15`](15-target-architecture.md) |
| Installing a NeuroEdge Blueprint (`planned · Q-72`) | I2e | §11.5 below; [`15`](15-target-architecture.md) |

## 11. Planned flows under Q-72 (`planned · Q-72`)

No flow in this section has code yet. They record the target design of [Q-72](../../../roadmap/neuroedge-prd.md#15-sổ-quyết-định) for increment I2d (missions and the operating agent) and I2e (minimal NeuroEdge Blueprint); progress is in roadmap §0.2. Parts that need an RFC are marked "pending RFC".

Two processes on the home machine ([`02`](02-container-c4l2.md)):

- **trusted runtime** (24/7, systemd): HAL, gate, mission contract execution, scheduling, deterministic detectors, chat channel adapters and approval checks, egress;
- **untrusted LLM worker**: holds the user's LLM key (BYOK), calls the runtime over local MCP like any MCP client, source assigned by the runtime, **never approves** — the same boundary as the MCP client in Q-71.

Every command to a pin, whether it comes from chat, the scheduler or a detector, still goes through exactly the one segment of §1: `dispatch()` → `Conversation.do` → gate → token → HAL. The chat adapter only calls into `dispatch()` and does not import `hal`. Durations, approval expiry, the watchdog and reflexes use the **monotonic clock**; wall-clock facts carry the `unsynced` state while the machine has not synchronized its time, and time-window clauses treat `unsynced` as a missing fact (fail-closed).

### 11.1 Lifecycle of a mission contract (I2d)

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

- Only devices with `ne_gate` have a reflex tier; Home Assistant devices stop at the host tier and the approval summary says so.
- The approval summary is compiler output, not LLM text: a tricked worker cannot write a single line of the approval message.

### 11.2 Triggers, detectors and proactive reports (I2d)

This extends the Block N6 trigger flow (I2d, moved from I4a by Q-72; [`15`](15-target-architecture.md) §4.2: runs without a client session, `call_source = "trigger"`, `trigger ∉ HUMAN_SOURCES`, debounce, rate cap), not a parallel path: the mission contract's scheduler and detectors are new activation sources of that same path.

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

Detectors run first, and the LLM is called only after an event: reflexes and hard-template alerts do not depend on the LLM. Detectors reading sensors periodically inside the 24/7 runtime turn `TODOS.md` #48 (sensor reads blocking the event loop) into a real risk ([`02`](02-container-c4l2.md)).

### 11.3 Commands arriving from chat (I2d)

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

The chat adapter does not import `hal` and does not call `Conversation.do` directly: every command with a physical effect goes through `dispatch()` like the MCP calls in §3. A call the gate blocks with `on_block: ask` is not answered by the worker; it becomes an approval request in §11.4.

### 11.4 Approval requests and replies over chat (I2d, pending the RFC for the `chat:<id>` source)

This extends §2: today only `local_grammar` and `ui` can answer an `ask` question (Q-26). Q-72 adds a path over chat through an **approval record**, not through a new source name in `HUMAN_SOURCES` for a free-form "yes" message.

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

Pairing is done locally; revocation, pairing expiry and the cap on the number of approvals are still deferred (`TODOS.md` #62).

### 11.5 Installing a NeuroEdge Blueprint (I2e)

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

A NeuroEdge Blueprint only declares; it carries no code that runs in the runtime. It is different from a Home Assistant Blueprint (HA's automation template), and it may carry an HA blueprint.

### 11.6 Failure branches

| Path | Failure | Handling in the design | What the user sees |
|:---|:---|:---|:---|
| Runtime ↔ LLM worker | worker dies or hangs | the runtime keeps running reflexes, detectors, hard-template alerts; restarts the worker | an "analysis paused" message; alerts still arrive |
| Runtime → chat channel | the chat platform's API fails | bounded queue + local alert on the UI | alert on the UI; messages arrive late, with timestamps |
| LLM provider | `llm_budget` exhausted | reflexes + hard-template alerts | an "analysis budget exhausted" message |
| Approval over chat | request expired | not approved, traced | a "request expired" message |
| Approval over chat | reply from an unknown account or a group | refused, traced | nothing changes |
| Relay (`planned · Q-72`, outside I2d/I2e) | relay down | no effect on safety; remote access lost | the page cannot be opened remotely |
| Clock | power loss, no NTP/RTC yet | wall-clock fact `unsynced` ⇒ time-window clause lacks a fact ⇒ block | the approval summary and the UI report the clock is not synchronized |
| Trace | power loss in the middle of a segment | at most the tail of ordinary events is lost; blocks and approvals were already flushed | `replay` reports a truncated segment |
| NeuroEdge Blueprint install | digest does not match | install refused | three-part error |
