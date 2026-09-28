# 01 · Bối cảnh hệ thống (C4 L1)

> **Phạm vi:** NeuroEdge nhìn từ bên ngoài — ai dùng nó, nó nói chuyện với hệ thống nào, và ranh
> giới tin cậy nằm ở đâu. **Nguồn:** `python/neuroedge/models/providers/`,
> `python/neuroedge/perception/providers/`, `python/neuroedge/mcp_server.py`, PRD §2,
> `docs/spec/threat_model.md`.

**Đọc chương này để làm gì:** Chương này mô tả NeuroEdge ở mức C4 L1 (Bối cảnh hệ thống). Tài liệu trả lời các câu hỏi: *Ai là người dùng trực tiếp của NeuroEdge? Hệ thống tích hợp với các dịch vụ bên ngoài nào (LLM, giọng nói, MCP, thiết bị nhúng, robot)? Ranh giới tin cậy nằm ở đâu và dữ liệu nào được phép rời khỏi máy?* Trước khi đọc, nên nắm tổng quan tại [`00`](00-overview.md). Sau chương này, đọc tiếp [`02`](02-container-c4l2.md) để hiểu cấu trúc các tiến trình và container chạy độc lập.

## 1. Sơ đồ bối cảnh

![E-01 · Bối cảnh hệ thống](../assets/svg/E-01-system-context.svg)
*Hình E-01 — Người dùng bên trái, hệ thống bên ngoài bên phải. Nét đứt là `planned`.*

*Cách đọc hình E-01:* Hình thể hiện ranh giới bối cảnh giữa người dùng (bên trái), hệ thống NeuroEdge (ở giữa), và các nhà cung cấp bên ngoài (bên phải). Khối nét liền là các tác nhân và kết nối đã vận hành; khối nét đứt là các bên tham gia trong quy hoạch (`planned`). Điểm cốt lõi cần nhớ: các hệ thống bên ngoài chỉ đề xuất tool call, cung cấp dữ kiện hoặc nhận văn bản/âm thanh; không hệ thống nào tự quyết một hành động vật lý — mọi tool call vẫn qua gate.

## 2. Người dùng

| Người dùng | Làm gì với NeuroEdge | Công cụ chính | Trạng thái |
|:---|:---|:---|:---|
| **Maker, lập trình viên ứng dụng** | Viết agent (`agent.toml`, gate, action), chạy và kiểm trên máy mình | `neuroedge new · run · test · record` | `done` |
| **Kỹ sư lõi và kỹ sư nhúng** | Sinh firmware cho agent, nạp lên chip, so phán quyết giữa các môi trường | `build --target esp32s3 · verify · record --port` | `done` (trên QEMU) |
| **Người duyệt an toàn, QA** | Đọc và duyệt gate mà không đọc mã; điều tra một phiên từ vết ghi | `gate explain · trace view · replay` | `done` |
| **Đối tác OEM** | Khai báo một bo mạch mới, port HAL, chứng minh tương đương | `board.toml`, vector tuân thủ | `partial` — xem [`11`](11-hal-port-guide.md) |
| **Người vận hành đội thiết bị** | Quản trị đội qua 5 năng lực: cấp phát danh tính (provisioning), cập nhật OTA theo đợt & rollback (staged OTA), giám sát sức khoẻ và sổ kiểm kê (monitoring/inventory), cập nhật cấu hình và gate từ xa (remote gate/config), thu thập trace sự cố (incident traces); cần để cập nhật, giám sát và thu vết ghi trên hàng trăm, hàng nghìn thiết bị mà không nạp lại firmware bằng tay ([`neuroedge-proposal.md`](../../../neuroedge-proposal.md) §6.2) | Fleet OS | `planned` (I9) — xem [`15`](15-target-architecture.md) §3.1 |
| **Đội tích hợp robot phân tầng** | Tích hợp hệ thống nhiều node qua bus Zenoh, bridge ROS 2 / Nav2; cần thiết để tách bạch ý định tập trung trên SBC với an toàn chấp hành cục bộ trên từng MCU node ([`neuroedge-prd.md`](../../../neuroedge-prd.md) U6, Q-32, Q-34) | Node firmware, Zenoh router, ROS 2 bridge | `planned` — xem [`15`](15-target-architecture.md) §4.3 |

Các nhóm người dùng và hành trình gốc ở PRD §2 (`U1`…`U6`, `J1`…`J7`).

## 3. Hệ thống bên ngoài

Mọi kết nối ra ngoài đều **tuỳ chọn**: bản cài cơ bản chạy toàn bộ `sim` không cần mạng hay khoá
(Q-15). Khoá API không bao giờ nằm trong tệp: chỉ **tên** biến môi trường được ghi (`api_key_env`),
và build từ chối mọi trường trông giống khoá (`models/providers/common.py`).

| Hệ thống | Vai trò | Giao thức và định dạng | Mã đảm nhận | Trạng thái |
|:---|:---|:---|:---|:---|
| **Nhà cung cấp LLM** (System 2) | Trả lời câu tự do, đề xuất tool call | Chat completions chuẩn OpenAI qua thư viện LiteLLM (không chạy proxy — Q-10); hoặc adapter `python:` | `models/providers/litellm_provider.py`, `openai_chat.py` | `done` |
| **Jev trên OpenRouter** (System 1) | Quyết một số tiêu chí gate từ lời người nói | `POST {api_base}/systemone` (System One API), HTTPS bắt buộc trừ loopback | `models/providers/systemone_api.py` | `done` |
| **Nhà cung cấp giọng nói** | STT, TTS | `POST {base_url}/audio/transcriptions` và `/audio/speech` chuẩn OpenAI | `perception/providers/openai_audio.py` | `done` |
| **Máy chủ STT cục bộ** | STT dự phòng khi STT chính hỏng | Như trên, thường `http://localhost` | `[stt.fallback]` | `done` |
| **Client MCP** | Gọi action của agent như công cụ | JSON-RPC qua **stdio** (không qua mạng — NFR-SEC-09) | `mcp_server.py` | `done` |
| **MCP server bên ngoài** | Nguồn thông tin cho System 2 (tin tức, tra cứu) | stdio; chỉ công cụ trong danh sách cho phép | `mcp_host.py` | `done` |
| **ESP-IDF v5.4 và Espressif QEMU** | Biên dịch firmware, chạy chip ảo | Project ESP-IDF sinh bởi `build`; UART đọc qua tệp hoặc `tcp://` | `engine/firmware.py`, `testing/uart.py` | `done` |
| **Máy chủ ảnh OTA** | Phục vụ một ảnh app đã ký | HTTP(S) GET bất kỳ máy chủ tĩnh nào | `components/ne_ota/` | `partial` — trên QEMU |
| **Fleet OS, Gate Registry** | Quản trị đội thiết bị (5 năng lực) và kho gate chia sẻ; cần thiết để tự động hoá cập nhật an toàn và phân phối chính sách trên quy mô lớn | Quy hoạch: MQTT với broker giấy phép dễ dãi (Mosquitto, NanoMQ hoặc VerneMQ — **không** EMQX, Q-11); OCI qua ORAS và Harbor | chưa có mã | `planned` (I9, I10) — xem [`15`](15-target-architecture.md) §3.1, §3.2 |
| **ROS 2 / Nav2** | Hệ thống điều hướng và lập kế hoạch di chuyển; chỉ nhận lệnh vận tốc qua gate; cần thiết để tận dụng hệ sinh thái robot mà không nhượng bộ an toàn ([`neuroedge-prd.md`](../../../neuroedge-prd.md) §14, Q-34) | ROS 2 messages/actions qua bridge trên SBC Linux | Chưa có mã (ngoài lõi) | `planned` (I14) — xem [`15`](15-target-architecture.md) §4.3 |
| **Bộ định tuyến Zenoh (Zenoh router)** | Mạng truyền dẫn giữa máy chủ agent (Pi) và các node MCU; kênh "black channel" không tin cậy (IEC 61784-3 — [`draft-ke-hoach-mo-rong-robot-fofoca.md`](../../../draft-ke-hoach-mo-rong-robot-fofoca.md) §4.2); Zenoh-pico theo Q-36 | Eclipse Zenoh (`zenohd` trên host, `zenoh-pico` trên MCU, nhánh Apache-2.0) | Chưa có mã | `planned` (I14) — xem [`15`](15-target-architecture.md) §4.3 |

## 4. Ranh giới tin cậy

```mermaid
flowchart LR
    subgraph Untrusted["Untrusted: may propose, never decide"]
        LLM["System 2 LLM"]
        JEV["System 1 model (Jev)"]
        MCPC["MCP client"]
        EXT["External MCP server"]
    end
    subgraph Contract["Contract boundary: deterministic"]
        DISP["dispatch()<br/>schema · call_source"]
        GATE["Gate engine<br/>domain · threshold · budget"]
        LEDGER["TokenLedger<br/>one-time · TTL"]
    end
    subgraph Local["Trusted: on the device"]
        PERSON["Person at the device<br/>REPL or same-origin page"]
        HAL["HAL"]
        PIN(["Pins"])
    end
    LLM -- "ToolCall" --> DISP
    MCPC -- "ToolCall" --> DISP
    EXT -- "data only" --> LLM
    JEV -- "Fact or Unavailable" --> GATE
    DISP --> GATE
    GATE -- "ALLOW" --> LEDGER --> HAL --> PIN
    PERSON -- "confirm (local_grammar, ui)" --> GATE
```

Bốn luật định ranh giới, mỗi luật có test ở `docs/spec/threat_model.md` §2b:

1. **Model và client chỉ đề xuất.** LLM và client MCP chỉ gửi được `ToolCall` qua `dispatch()`.
   Công cụ không tồn tại hay tham số sai kiểu ⇒ `REJECTED`, không phán quyết nào được tính.
2. **Nguồn gọi do runtime gán, không do bên gọi khai.** `call_source` được dispatcher chèn vào như
   một dữ kiện tin cậy; một gate có thể từ chối một hành động cho riêng nguồn `mcp` hay
   `system_two`.
3. **Câu trả lời của model là dữ kiện, không phải phán quyết.** Jev trả `Fact` hoặc `Unavailable`,
   rồi bị kiểm miền giá trị và ngưỡng tin cậy trước khi vào gate. Model không bao giờ trả `ALLOW`.
   Nội dung từ MCP server bên ngoài được đánh dấu "dữ liệu không tin cậy"; lời gọi nó dẫn tới vẫn
   phải qua gate.
4. **Chỉ người có mặt tại thiết bị mới xác nhận được.** Khi gate hỏi lại (`on_block: ask`), chỉ hai
   kênh `local_grammar` (gõ hoặc nói "có") và `ui` (nút trên trang cùng nguồn gốc 127.0.0.1) được
   trả lời (Q-26). System 2 và client MCP không có cách nào xác nhận thay.

Ngoài phạm vi, nói rõ: MCP qua mạng (chỉ stdio ở v1.0), kẻ tấn công trong cùng tiến trình, và an
toàn chức năng được chứng nhận (`docs/spec/threat_model.md` §3, §3b).

## 5. Dữ liệu rời khỏi máy

| Tới | Dữ liệu gửi đi | Không bao giờ gửi |
|:---|:---|:---|
| LLM (System 2) | Câu người dùng, danh sách công cụ, lịch sử lượt | Khoá API (chỉ đọc từ biến môi trường), token phán quyết |
| Jev (System 1) | **Chỉ lời người nói** và câu hỏi có kiểu cho từng tiêu chí | Tên action, tham số, dữ kiện phiên; lời gọi MCP không ai nói thì không gửi gì |
| STT | Đoạn âm thanh của một lượt | — |
| TTS | Câu trả lời cần đọc | — |
| Camera / thị giác *(planned)* | Tới model thị giác và một `SystemOne`, trả về `bool`/`level`/`choice` cho gate (`neuroedge-design-phase2.md` §2.2) | Vết ghi không nhúng khung hình thô: mặc định chỉ lưu băm SHA-256 và kích thước; lưu ảnh thô phải bật tường minh (`metadata.raw_capture`, phase2 §2.3, TSK-V1b-08) — xem [`15`](15-target-architecture.md) §4.4 |

Vết ghi mặc định chỉ lưu quyết định: chữ thô (câu gõ, bản chép lời) được băm tại nguồn (NFR-PRIV-03);
`--raw` là cách bật tường minh giữ nguyên văn, vết ghi đó mang `metadata.anonymized = false` (NFR-PRIV-04).
Âm thanh không bao giờ được lưu vào vết ghi.
