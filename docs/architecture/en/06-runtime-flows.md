# 06 · Runtime Flows

> **Status:** `done` · Standardized Real-time Runtime Execution Flows  
> **Reference Documents:** [04-component-device-c4l3.md](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/architecture/en/04-component-device-c4l3.md), [05-code-gate-hal-c4l4.md](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/architecture/en/05-code-gate-hal-c4l4.md), [E-06-trace-lifecycle](../assets/svg/E-06-trace-lifecycle.svg), [RFC-0006](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/rfcs/RFC-0006-on-block-ask-confirms.md)  
> **Normative Test Suites:** `tests/test_runtime_flows.py`, `tests/test_barge_in.py`, `tests/test_trace_replay.py`

---

## 1. Overall Interactive Session Flow (`run` session turn)

Each spoken or typed conversational turn strictly adheres to a Dual-System Router model: Short, routine commands are resolved locally via System 1 (Grammar, latency $\le 50$ ms). Open-ended, complex utterances are routed upstream to System 2 (LLM / Cloud, latency $\le 1200$ ms).

```mermaid
sequenceDiagram
    autonumber
    actor User as User (Audio / Text)
    participant VAD as Audio Frontend / VAD
    participant Router as Dual-System Router
    participant S1 as System 1 (Grammar / S1)
    participant S2 as System 2 (Cloud LLM)
    participant Gate as Gate Engine (Evaluator)
    participant Ledger as TokenLedger
    participant HAL as HAL Actuator
    participant AudioOut as TTS / Audio Output
    participant Trace as EventLog (Telemetry)

    User->>VAD: "Turn on the living room light"
    VAD->>Router: Speech Complete (Silence Detected)
    Note over Router: Mark T0: Turn Start

    Router->>S1: Match grammar patterns
    alt Command Matched System 1 (Local Pattern Match)
        S1-->>Router: ToolCall(name="light_on", args={room: "living"}, source="local_grammar")
    else Unmatched & Cloud Available
        Router->>S2: Stream prompt + Tool Definitions
        S2-->>Router: ToolCall(name="light_on", args={room: "living"}, source="system_two")
    else Offline & Unmatched
        Router->>AudioOut: Return offline_help (List available local commands)
        AudioOut-->>User: "Device is offline. You can still toggle lights..."
    end

    Note over Router,Gate: Fact resolution order: [sim.facts] -> [sim.slot_facts] -> [sim.sensor_facts]
    Router->>Gate: evaluate(tool="light_on", args, facts, deadline=p95)
    
    alt Verdict ALLOW
        Gate->>Ledger: issue(pins=[4], ttl=p95*3)
        Ledger-->>Gate: Valid Token
        Gate-->>Router: GateResult(verdict=ALLOW, token)
        Router->>HAL: digital_out(pin=4, level=HIGH, token)
        HAL->>Ledger: authorize(token, pin=4)
        Ledger-->>HAL: NE_TOKEN_AUTHORIZED
        HAL->>HAL: Drive GPIO4 (Relay Trigger)
        HAL-->>Router: Actuator Success
        Router->>AudioOut: c.say("Living room light turned on")
        AudioOut-->>User: Synthesize Audio Response
    else Verdict BLOCK (on_block: deny/ask/degrade)
        Gate-->>Router: GateResult(verdict=BLOCK, reason=CONDITION_NOT_MET)
        Router->>AudioOut: c.say("Cannot turn on light due to safety policy")
        AudioOut-->>User: Play Rejection Notice
    end

    Note over Router,Trace: Measure Turn Latency (5 stages: VAD -> STT -> Routing -> Gate -> HAL/TTS)
    Router->>Trace: emit(turn_latency, session_summary)
```

### 1.1. Fact Resolution Precedence

When `engine.evaluate()` is invoked, fact sources are aggregated in descending order of precedence:
1. `[sim.facts]` (Explicit fact overrides from test scripts or session harness).
2. `[sim.slot_facts]` (Facts extracted directly from utterance slots).
3. `[sim.sensor_facts]` (Real-time hardware sensor readings queried via HAL).
4. `[grammar]` (Default facts declared statically in grammar rules).

---

## 2. Barge-in & Actuator Abort Contract

Barge-in occurs when a user begins speaking while the device is processing (`THINKING`) or speaking (`SPEAKING`). The system must instantly revoke hardware execution authority.

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant Mic as Audio Task (Core 0)
    participant FSM as Voice FSM (Core 1)
    participant Dispatcher as Action Dispatcher
    participant Ledger as ne_ledger (Token Ledger)
    participant HAL as Stepper / PWM Motor Driver
    participant Speaker as I2S Audio Out (Core 0)

    Note over FSM,Speaker: State: SPEAKING (Playing previous reply)
    HAL->>HAL: Executing curtain motor motion (PWM Active)

    User->>Mic: "Stop right now!" (Barge-in speech)
    Mic->>FSM: Audio Event: barge_in_detected (VAD Energy Trigger)
    
    rect rgb(255, 235, 235)
        Note over FSM,HAL: ACTUATOR ABORT CONTRACT (LATENCY <= 20 ms)
        FSM->>FSM: State Transition: SPEAKING -> BARGE_IN (T13)
        FSM->>Dispatcher: Signal: ACTUATOR_ABORTED_BY_BARGE_IN
        Dispatcher->>Ledger: ne_token_close(active_tokens)
        Note over Ledger: All active tokens immediately revoked (NE_SLOT_CLOSED)
        Dispatcher->>HAL: hal_emergency_stop() (Force PWM/Steps to safe state)
        HAL->>HAL: Motor halted within <= 1 audio frame (20 ms)
    end

    FSM->>Speaker: Abort Audio Pipeline (Flush DMA RingBuffer)
    Speaker->>Speaker: Speaker silent in < 300 ms

    Note over FSM: Late Result Drop Filter
    opt Previous turn LLM/STT arrives after barge-in
        Dispatcher->>Dispatcher: Drop late result (Log voice_late_result_dropped)
        Note over Dispatcher: STRICTLY PROHIBITED to call c.do() or speak stale output!
    end

    FSM->>FSM: State Transition: BARGE_IN -> LISTENING (T14)
    Note over FSM,Mic: Begin capturing user's new utterance
```

### 2.1. Four Invariants of Barge-in

1. **Abort Undelivered Actuation ($\le 20$ ms):** Any incomplete actuator command must be halted immediately (`ACTUATOR_ABORTED_BY_BARGE_IN`). Irreversible physical actions already completed cannot be undone, but dependent chains are severed.
2. **Revoke Active Tokens:** Issued tokens associated with aborted actions are transitioned to `closed`. Subsequent authorization attempts are rejected with `NE_TOKEN_EXPIRED` or `NE_TOKEN_REPLAYED`.
3. **Immediate Speaker Silence ($< 300$ ms):** Audio playback must fall silent in $< 300$ ms (accounting for VAD energy detection latency and I2S DMA FIFO drain).
4. **Drop Late Turn Results:** Upstream LLM or STT responses belonging to the interrupted turn that arrive late are dropped silently (`voice_late_result_dropped`), preventing delayed actuation or stale audio playback.

---

## 3. Tool Dispatch & In-Person Confirmation

When a safety policy blocks an action but specifies `on_block: ask` with `confirms` attributes (per [RFC-0006](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/rfcs/RFC-0006-on-block-ask-confirms.md)), the system triggers in-person physical verification:

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant Engine as Engine Dispatcher
    participant Gate as Gate Evaluator
    participant Device as Physical Device (Button / Mic)
    participant Ledger as Token Ledger
    participant HAL as Smart Lock Driver

    User->>Engine: ToolCall(name="unlock_door", source="system_two")
    Engine->>Gate: evaluate("unlock_door", facts={authenticated: false})
    
    Gate->>Gate: walk(tree) -> BLOCK (Missing authenticated)
    Note over Gate: on_block: ask, confirms=["authenticated"]
    
    Gate-->>Engine: GateResult(verdict=BLOCK, action=ask, confirm_mask=0x01)
    
    Engine->>Device: Open PendingConfirmation(action="unlock_door", timeout=10s)
    Device->>User: "Are you sure you want to unlock? Press device button to confirm."
    
    alt User presses physical button within 10s
        User->>Device: Press physical button (GPIO Interrupt)
        Device->>Engine: ConfirmationEvent(criterion="authenticated", confirmed=true)
        Engine->>Gate: re_evaluate("unlock_door", confirmed_mask=0x01)
        Note over Gate: Bit 0 matches confirm_mask -> Treat authenticated as PASS
        Gate->>Ledger: issue(pins=[12], ttl=p95*3)
        Ledger-->>Gate: Valid Token
        Gate-->>Engine: GateResult(verdict=ALLOW, token)
        Engine->>HAL: digital_out(pin=12, level=HIGH, token)
        HAL->>Ledger: authorize(token, pin=12)
        Ledger-->>HAL: NE_TOKEN_AUTHORIZED
        HAL->>HAL: Drive physical latch
        HAL-->>Engine: Success
        Engine->>User: "Door unlocked."
    else Timeout (> 10s) or User Cancellation
        Device-->>Engine: ConfirmationExpiredEvent (NE2004)
        Engine->>User: "Unlock request cancelled due to confirmation timeout."
    end
```

> **In-Person Confirmation Safety Invariants:**
> - Confirmation is strictly **single-use** for a single action invocation.
> - Confirmation must originate from a **physical on-device interface** (hardware push button, biometric sensor, or local microphone). Remote confirmations via unauthenticated network APIs are forbidden.
> - If the Gate configuration changes (hash `gate_digest` updates) while awaiting confirmation, the `PendingConfirmation` is immediately invalidated.

---

## 4. Fail-Closed Offline Fallback

The system adheres to safe disconnection principles: When cloud connectivity drops or AI providers exceed their $p95$ budget, offline degradation logic executes deterministically without freezing the device.

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant Router as Session Router
    participant S2 as Cloud System 2
    participant S1 as Local Grammar (System 1)
    participant Gate as Gate Engine
    participant Trace as EventLog

    User->>Router: "Check temperature and turn on the water heater"
    Router->>S2: Dispatch cloud request (Timeout deadline = 1000 ms)
    
    alt Network Disconnection or Timeout (p95 Exceeded)
        S2--xRouter: Network Timeout / DNS Error
        Router->>Trace: emit(source_degraded, reason=GATE_UNREACHABLE)
        
        Router->>S1: match_local_grammar("Check temperature and turn on the water heater")
        alt Command matches local grammar
            S1-->>Router: ToolCall(name="water_heater_on", source="local_grammar")
            Router->>Gate: evaluate("water_heater_on", degraded=UNREACHABLE)
            
            alt Gate configured `fail: closed` (Default)
                Gate-->>Router: GateResult(verdict=BLOCK, reason=GATE_UNREACHABLE)
                Router->>User: "Cannot activate water heater while offline (Safety Policy)."
            else Gate configured `fail: open`
                Note over Gate: Only missing facts are excused; explicit NO still blocks
                Gate-->>Router: GateResult(verdict=ALLOW, degraded=OPEN)
                Router->>User: "Water heater activated in offline mode."
            end
        else No local grammar match
            Router->>User: "Connection lost. Available commands: light on, light off..."
        end
    end
```

---

## 5. Trace Lifecycle & Target Verification

Audit traces (`trace.json`) serve as mathematical evidence guaranteeing system integrity and target equivalence between the Simulator, Linux, and actual hardware (ESP32-S3).

```mermaid
flowchart TD
    classDef rec fill:#eff6ff,stroke:#2563eb,color:#1e3a8a,stroke-width:1.5px;
    classDef val fill:#faf5ff,stroke:#9334e6,color:#6b21a8,stroke-width:1.5px;
    classDef rep fill:#fff7ed,stroke:#ea580c,color:#7c2d12,stroke-width:1.5px;
    classDef gold fill:#f0fdf4,stroke:#16a34a,color:#14532d,stroke-width:1.5px;
    classDef pass fill:#f0fdf4,stroke:#16a34a,color:#14532d,stroke-width:2px;
    classDef fail fill:#fef2f2,stroke:#dc2626,color:#991b1b,stroke-width:2px;

    subgraph RunPhase["1. Record Execution (Run &amp; Record)"]
        S["Sim / Host / Hardware Run"]:::rec -->|Every emit event| EL["EventLog Bus"]:::rec
        EL -->|Anonymize Hash PII| TR["Trace Collector"]:::rec
        TR -->|Serialize JSON RFC 8785| TF["trace.json / UART NE1 Stream"]:::rec
    end

    subgraph ValidatePhase["2. Validate Schema (Trace Validate)"]
        TF -->|Schema Check| TV["trace.v1.json Schema Validator"]:::val
        TV -->|NE3001 Check| CK1["Span Structure &amp; Monotonic Timestamps"]:::val
        TV -->|NE3002 Check| CK2["Token &amp; Gate Digest Hash Integrity"]:::val
    end

    subgraph ReplayPhase["3. Audit Replay (Trace Replay)"]
        TF -->|Replay Engine| RP["trace replay --target sim/linux"]:::rep
        RP -->|Recompute verdicts from facts| GW["Gate Walker &amp; Token Ledger"]:::rep
        GW -->|Drive actuator commands| SH["Simulated / Hardware Pins"]:::rep
        SH -->|Emit fresh execution trace| RF["replayed_trace.json"]:::rep
    end

    subgraph GoldenPhase["4. Verify Equivalence (Golden Equivalence)"]
        TF -->|Extract Verdicts &amp; Pins| GD["Golden Extractor"]:::gold
        RF -->|Extract Verdicts &amp; Pins| GD
        GD --> DIFF{"Diff Verdicts &amp; Pin Commands"}:::gold
        DIFF -->|Identical 100% Match| PASS["VERIFICATION PASSED"]:::pass
        DIFF -->|Any bit divergence| REG["NE4002: SAFETY REGRESSION DETECTED"]:::fail
    end
```

### 5.1. Trace Replay Principles

- **No Result Trust:** `neuroedge trace replay` **recomputes all decisions from scratch** using the binary decision tree and recorded raw facts.
- **Ignore Non-Safety Data:** Golden diffing strips real-time wall-clock timing (`timestamp_ms`, network transit jitter) and unconstrained LLM phrasing, focusing strictly on:
  1. **Gate Verdict Sequences:** `ALLOW` or `BLOCK`.
  2. **HAL Pin Transition Sequences:** Target GPIO pin numbers, logic levels (HIGH/LOW), and relative ordering.
- **Safety Regression Detection (NE4002):** If hardware execution yields an `ALLOW` where the golden trace specifies `BLOCK`, CI immediately fails with a **Fatal Safety Regression**.
