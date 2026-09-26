# 06 · Luồng thực thi Runtime

> **Trạng thái:** `done` · Chuẩn hóa luồng hoạt động thời gian thực (Runtime Flows)  
> **Tài liệu tham chiếu:** [04-component-device-c4l3.md](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/architecture/vi/04-component-device-c4l3.md), [05-code-gate-hal-c4l4.md](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/architecture/vi/05-code-gate-hal-c4l4.md), [E-06-trace-lifecycle](../assets/svg/E-06-trace-lifecycle.svg), [RFC-0006](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/rfcs/RFC-0006-on-block-ask-confirms.md)  
> **Bộ kiểm thử chuẩn tắc:** `tests/test_runtime_flows.py`, `tests/test_barge_in.py`, `tests/test_trace_replay.py`

---

## 1. Luồng phiên tương tác tổng thể (`run` session turn)

Mỗi lượt tương tác thoại hoặc văn bản (`turn`) tuân thủ nghiêm ngặt mô hình phân tách nhận thức (Dual-System Router): Lệnh ngắn, quen thuộc được giải quyết cục bộ qua System 1 (Grammar, độ trễ $\le 50$ ms). Các câu lệnh tự do, phức tạp được định tuyến qua System 2 (LLM / Cloud, độ trễ $\le 1200$ ms).

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

    User->>VAD: "Bật đèn phòng khách"
    VAD->>Router: Speech Complete (Silence Detected)
    Note over Router: Ghi nhận T0: Bắt đầu xử lý lượt (Turn Start)

    Router->>S1: Match grammar patterns
    alt Khớp lệnh System 1 (Local Pattern Match)
        S1-->>Router: ToolCall(name="light_on", args={room: "living"}, source="local_grammar")
    else Không khớp lệnh & Mạng khả dụng (Cloud Available)
        Router->>S2: Stream prompt + Tool Definitions
        S2-->>Router: ToolCall(name="light_on", args={room: "living"}, source="system_two")
    else Offline & Không khớp
        Router->>AudioOut: Phản hồi offline_help (Liệt kê lệnh cục bộ khả dụng)
        AudioOut-->>User: "Thiết bị mất mạng, bạn chỉ có thể bật/tắt đèn..."
    end

    Note over Router,Gate: Phân giải sự thật: [sim.facts] -> [sim.slot_facts] -> [sim.sensor_facts]
    Router->>Gate: evaluate(tool="light_on", args, facts, deadline=p95)
    
    alt Phán quyết ALLOW
        Gate->>Ledger: issue(pins=[4], ttl=p95*3)
        Ledger-->>Gate: Valid Token
        Gate-->>Router: GateResult(verdict=ALLOW, token)
        Router->>HAL: digital_out(pin=4, level=HIGH, token)
        HAL->>Ledger: authorize(token, pin=4)
        Ledger-->>HAL: NE_TOKEN_AUTHORIZED
        HAL->>HAL: Kích hoạt GPIO4 (Bật Rơ-le)
        HAL-->>Router: Actuator Success
        Router->>AudioOut: c.say("Đã bật đèn phòng khách")
        AudioOut-->>User: Phát âm thanh phản hồi
    else Phán quyết BLOCK (on_block: deny/ask/degrade)
        Gate-->>Router: GateResult(verdict=BLOCK, reason=CONDITION_NOT_MET)
        Router->>AudioOut: c.say("Không thể bật đèn do điều kiện an toàn")
        AudioOut-->>User: Phát thông báo từ chối
    end

    Note over Router,Trace: Đo đạc Turn Latency (5 chặng: VAD -> STT -> Routing -> Gate -> HAL/TTS)
    Router->>Trace: emit(turn_latency, session_summary)
```

### 1.1. Thứ tự ưu tiên nạp sự thật (Fact Resolution Precedence)

Khi `engine.evaluate()` được triệu gọi, các nguồn dữ kiện được tổng hợp theo thứ tự ưu tiên giảm dần:
1. `[sim.facts]` (Sự thật ghi đè từ kịch bản kiểm thử hoặc phiên chạy hiện tại).
2. `[sim.slot_facts]` (Dữ kiện trích xuất trực tiếp từ các slot của câu lệnh người dùng).
3. `[sim.sensor_facts]` (Dữ kiện đo đạc thời gian thực từ cảm biến phần cứng qua HAL).
4. `[grammar]` (Dữ kiện mặc định khai báo trong quy tắc ngữ pháp).

---

## 2. Hợp đồng ngắt lời & thu hồi chấp hành (Barge-in Abort Contract)

Barge-in là tình huống người dùng lên tiếng ngắt lời khi thiết bị đang xử lý (`THINKING`) hoặc đang phát âm thanh (`SPEAKING`). Hệ thống bắt buộc phải thu hồi quyền điều khiển phần cứng ngay lập tức.

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

    Note over FSM,Speaker: Trạng thái: SPEAKING (Đang trả lời câu trước)
    HAL->>HAL: Đang thực thi động cơ rèm (PWM Active)

    User->>Mic: "Dừng lại ngay!" (Nói chen)
    Mic->>FSM: Audio Event: barge_in_detected (VAD Speech Energy Trigger)
    
    rect rgb(255, 235, 235)
        Note over FSM,HAL: HỢP ĐỒNG THU HỒI CƠ CẤU CHẤP HÀNH (THỜI GIAN <= 20 ms)
        FSM->>FSM: Chuyển trạng thái: SPEAKING -> BARGE_IN (T13)
        FSM->>Dispatcher: Signal: ACTUATOR_ABORTED_BY_BARGE_IN
        Dispatcher->>Ledger: ne_token_close(active_tokens)
        Note over Ledger: Mọi Token đang phát hành bị thu hồi lập tức (NE_SLOT_CLOSED)
        Dispatcher->>HAL: hal_emergency_stop() (Chuyển PWM/Step về mức an toàn)
        HAL->>HAL: Động cơ dừng quay trong <= 1 khung âm thanh (20 ms)
    end

    FSM->>Speaker: Audio Pipeline Abort (Xóa sạch DMA RingBuffer)
    Speaker->>Speaker: Loa im lặng hoàn toàn trong < 300 ms

    Note over FSM: Lọc kết quả muộn (Late Result Drop Filter)
    opt Nếu LLM/STT của lượt trước trả về kết quả sau khi barge-in
        Dispatcher->>Dispatcher: Drop kết quả muộn (Ghi log voice_late_result_dropped)
        Note over Dispatcher: CẤM TUYỆT ĐỐI gọi c.do() hoặc phát loa từ kết quả cũ!
    end

    FSM->>FSM: Chuyển trạng thái: BARGE_IN -> LISTENING (T14)
    Note over FSM,Mic: Bắt đầu thu âm câu mới của người dùng
```

### 2.1. Quy tắc thu hồi Barge-in (Four Invariants of Barge-in)

1. **Hủy lệnh chưa giao ($\le 20$ ms):** Lệnh chưa hoàn thành phải bị hủy tức thì (`ACTUATOR_ABORTED_BY_BARGE_IN`). Lệnh đã hoàn tất vật lý không đảo ngược được nhưng không được gửi tiếp chuỗi lệnh phụ thuộc.
2. **Thu hồi Token:** Token đã cấp cho lệnh bị hủy lập tức bị đóng (`closed`). Mọi nỗ lực điều khiển tiếp theo bằng token này sẽ bị từ chối với lỗi `NE_TOKEN_EXPIRED` hoặc `NE_TOKEN_REPLAYED`.
3. **Câm loa tức thì ($< 300$ ms):** Kênh phát âm thanh phải câm hoàn toàn trong vòng dưới 300 ms (bao gồm thời gian nhận biết năng lượng giọng nói VAD và xả hàng đợi I2S DMA).
4. **Vứt bỏ kết quả muộn (Late Result Drop):** Các phản hồi từ Cloud LLM hoặc STT của lượt cũ đến muộn sau khi ngắt lời sẽ bị tiêu hủy âm thầm (`voice_late_result_dropped`), không được chuyển tới `@action` hay gọi loa.

---

## 3. Điều phối Tool & Xác nhận người tại chỗ (In-Person Confirmation)

Khi một hành động nguy hiểm bị chặn bởi chính sách an toàn nhưng có cấu hình `on_block: ask` kèm thuộc tính `confirms` (theo [RFC-0006](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/rfcs/RFC-0006-on-block-ask-confirms.md)), hệ thống kích hoạt cơ chế xác thực vật lý từ con người:

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
    
    Gate->>Gate: walk(tree) -> BLOCK (Thiếu authenticated)
    Note over Gate: on_block: ask, confirms=["authenticated"]
    
    Gate-->>Engine: GateResult(verdict=BLOCK, action=ask, confirm_mask=0x01)
    
    Engine->>Device: Open PendingConfirmation(action="unlock_door", timeout=10s)
    Device->>User: "Bạn có chắc chắn muốn mở cửa? Bấm nút trên thiết bị để xác nhận."
    
    alt Người dùng bấm nút vật lý trên thiết bị trong vòng 10s
        User->>Device: Bấm nút vật lý (GPIO Input Interrupt)
        Device->>Engine: ConfirmationEvent(criterion="authenticated", confirmed=true)
        Engine->>Gate: re_evaluate("unlock_door", confirmed_mask=0x01)
        Note over Gate: Bit 0 khớp confirm_mask -> Coi như authenticated ĐẠT
        Gate->>Ledger: issue(pins=[12], ttl=p95*3)
        Ledger-->>Gate: Valid Token
        Gate-->>Engine: GateResult(verdict=ALLOW, token)
        Engine->>HAL: digital_out(pin=12, level=HIGH, token)
        HAL->>Ledger: authorize(token, pin=12)
        Ledger-->>HAL: NE_TOKEN_AUTHORIZED
        HAL->>HAL: Mở khóa cửa vật lý
        HAL-->>Engine: Success
        Engine->>User: "Đã mở khóa cửa."
    else Hết thời gian chờ (Timeout > 10s) hoặc Người bấm hủy
        Device-->>Engine: ConfirmationExpiredEvent (NE2004)
        Engine->>User: "Đã hủy lệnh mở khóa do không nhận được xác nhận."
    end
```

> **Bất biến An toàn về Xác nhận Người:**
> - Xác nhận chỉ có giá trị **dùng một lần** cho một phiên duy nhất.
> - Xác nhận chỉ được chấp nhận nếu bắt nguồn từ **giao diện cục bộ trên thiết bị vật lý** (nút bấm cứng, nhận diện vân tay, hoặc micro tại chỗ). Tuyệt đối cấm xác nhận từ xa qua API không tin cậy.
> - Nếu cấu hình Gate bị thay đổi (băm `gate_digest` đổi) trong lúc đang chờ xác nhận, `PendingConfirmation` lập tức bị hủy bỏ.

---

## 4. Xử lý sự cố mạng & Hạ cấp an toàn (Fail-Closed Offline Fallback)

Hệ thống thiết kế theo nguyên lý ngắt kết nối an toàn: Khi mất kết nối Cloud hoặc AI Provider quá hạn $p95$, hệ thống tự động kích hoạt logic phân giải ngoại tuyến mà không gây treo hệ thống.

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant Router as Session Router
    participant S2 as Cloud System 2
    participant S1 as Local Grammar (System 1)
    participant Gate as Gate Engine
    participant Trace as EventLog

    User->>Router: "Kiểm tra nhiệt độ và bật bình nước nóng"
    Router->>S2: Gửi truy vấn đám mây (Timeout deadline = 1000 ms)
    
    alt Kết nối mạng đứt hoặc Quá thời gian chờ (p95 Exceeded)
        S2--xRouter: Network Timeout / DNS Error
        Router->>Trace: emit(source_degraded, reason=GATE_UNREACHABLE)
        
        Router->>S1: match_local_grammar("Kiểm tra nhiệt độ và bật bình nước nóng")
        alt Lệnh có hỗ trợ mẫu cục bộ
            S1-->>Router: ToolCall(name="water_heater_on", source="local_grammar")
            Router->>Gate: evaluate("water_heater_on", degraded=UNREACHABLE)
            
            alt Gate cấu hình `fail: closed` (Mặc định)
                Gate-->>Router: GateResult(verdict=BLOCK, reason=GATE_UNREACHABLE)
                Router->>User: "Không thể bật bình nóng lạnh khi mất mạng (Chính sách an toàn)."
            else Gate cấu hình `fail: open`
                Note over Gate: Chỉ bỏ qua tiêu chí bị thiếu, không bỏ qua tiêu chí từ chối
                Gate-->>Router: GateResult(verdict=ALLOW, degraded=OPEN)
                Router->>User: "Đã bật bình nước nóng ở chế độ ngoại tuyến."
            end
        else Không hỗ trợ mẫu cục bộ
            Router->>User: "Mất kết nối mạng. Bạn có thể sử dụng các lệnh: bật đèn, tắt đèn..."
        end
    end
```

---

## 5. Vòng đời vết ghi & Kiểm thử tương đương mục tiêu (Trace Lifecycle & Verification)

Vết ghi kiểm toán (`trace.json`) là bằng chứng toán học bảo đảm tính toàn vẹn hệ thống và tương đương mục tiêu giữa Máy mô phỏng (Sim), Linux và Chip thật (ESP32-S3).

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

### 5.1. Cơ chế Tái hiện Kiểm toán (Trace Replay Principles)

- **Không sao chép kết quả cũ:** Lệnh `neuroedge trace replay` **tính toán lại từ đầu** mọi phán quyết dựa trên cây quyết định nhị phân và dữ kiện ghi trong trace.
- **Bỏ qua dữ liệu không mang tính an toàn:** Quá trình so sánh Golden Diff loại bỏ thông tin thời gian thực tế (`timestamp_ms`, độ trễ mạng) và câu chữ tự do của LLM, chỉ tập trung tuyệt đối vào:
  1. **Chuỗi phán quyết Gate:** `ALLOW` hay `BLOCK`.
  2. **Chuỗi lệnh kích hoạt chân HAL:** Chân GPIO, mức logic (HIGH/LOW), thời điểm kích hoạt tương đối.
- **Bắt lỗi suy thoái an toàn (NE4002):** Nếu một phiên chạy trên chip thật trả về `ALLOW` trong khi vết ghi chuẩn (Golden) quy định `BLOCK`, hệ thống CI lập tức dừng quy trình build và gắn nhãn **Fatal Safety Regression**.
