# 03 · Thành phần Host Python (C4 L3 — Component Level)

> **Trạng thái:** `done` (I0–I4). Mã nguồn nằm tại `python/neuroedge/`. Xem bản đồ cấu trúc thư mục chi tiết tại [`CONTRIBUTING.md` §6](../../CONTRIBUTING.md#6-cấu-trúc-kho).

---

## 1. Sơ đồ Phân tầng Thành phần Host (C4 L3 Component Diagram)

Hệ thống Host Python được tổ chức thành 8 phân tầng (layers) với chiều phụ thuộc một chiều nghiêm ngặt (tầng trên phụ thuộc tầng dưới, cấm import ngược và cấm phụ thuộc vòng):

![E-03 · Các layer host](../assets/svg/E-03-host-layers.svg)
*Hình E-03 — Kiến trúc phân tầng Host: Chiều mũi tên thể hiện phụ thuộc cho phép (tầng trên gọi tầng dưới).*

```mermaid
flowchart TB
    classDef l0 fill:#fffbeb,stroke:#d97706,color:#92400e,stroke-width:1.5px;
    classDef l3s fill:#eff6ff,stroke:#2563eb,color:#1e3a8a,stroke-width:1.5px;
    classDef l3c fill:#fef2f2,stroke:#dc2626,color:#991b1b,stroke-width:2px;
    classDef l2 fill:#faf5ff,stroke:#9334e6,color:#6b21a8,stroke-width:1.5px;
    classDef l1 fill:#f0fdf4,stroke:#16a34a,color:#14532d,stroke-width:1.5px;
    classDef obs fill:#fff7ed,stroke:#ea580c,color:#7c2d12,stroke-width:1.5px;
    classDef fdn fill:#f1f5f9,stroke:#64748b,color:#0f172a,stroke-width:1.5px;

    subgraph L0["Layer 0 · Entry Points &amp; Hub Assemblers"]
        CLI["cli/<br/>main.py · run.py · build.py"]:::l0
        SIM_SESS["sim/session.py<br/>Sole Assembler Hub"]:::l0
        SIM_UI["sim/ui.py<br/>Local Web UI (SSE / POST)"]:::l0
        MCP_SRV["mcp_server.py &amp; mcp_host.py<br/>Stdio JSON-RPC IPC"]:::l0
    end

    subgraph L3_Surface["Layer 3 Surface · Action Interface Domain"]
        CONV["actions/conversation.py<br/>ConversationContext &amp; c.do()"]:::l3s
        ACT_SPEC["actions/spec.py<br/>@action Decorator &amp; GatedAction"]:::l3s
        TL["actions/token.py<br/>TokenLedger &amp; Ephemeral Token"]:::l3s
        TOOLS["actions/tools.py<br/>GatedTool &amp; dispatch()"]:::l3s
        CONF["actions/confirmation.py<br/>PendingConfirmation (on_block: ask)"]:::l3s
    end

    subgraph L3_Core["Layer 3 Core · Policy &amp; Safety Gate Engine"]
        RESOLV["engine/gate_resolver.py<br/>Extends merger &amp; P1/P2 invariants"]:::l3c
        CONST["engine/constraints.py<br/>RFC-0005 parameter limits"]:::l3c
        GATE["engine/gate.py<br/>ActionContractEngine (evaluate)"]:::l3c
        TREE["engine/decision_tree.py<br/>Criteria compiler &amp; domain index"]:::l3c
        COMP["engine/compiler.py<br/>Capability negotiation"]:::l3c
        BIN["engine/binary_tree.py<br/>NETR v1 encoder (RFC-0003)"]:::l3c
        CB["engine/circuit_breaker.py<br/>Degrade loop circuit breaker"]:::l3c
    end

    subgraph L2["Layer 2 · Models, Perception &amp; Voice FSM"]
        MOD_SYS["models/system.py<br/>SystemOne &amp; SystemTwo Protocols"]:::l2
        GRAMMAR["models/grammar.py<br/>CommandGrammar (commands.toml)"]:::l2
        PROV["models/providers/<br/>LiteLLMProvider &amp; Adapter Factory"]:::l2
        VFSM["perception/voice_fsm.py<br/>VoiceFSM (14 canonical states)"]:::l2
    end

    subgraph L1["Layer 1 · Closed Hardware Abstraction (HAL)"]
        HAL_BASE["hal/base.py<br/>5 Closed HAL Primitives"]:::l1
        HAL_BOARD["hal/board.py<br/>BoardProfile (board.toml DATA-01)"]:::l1
        HAL_DIG["hal/digital.py<br/>DigitalOutPin (Token Guarded)"]:::l1
        HAL_SIM["hal/sim.py<br/>SimHAL (In-Memory Mock)"]:::l1
        HAL_LINUX["hal/linux.py<br/>LinuxHAL (gpiod v2 &amp; sysfs)"]:::l1
    end

    subgraph Obs["Observability &amp; Testing Subsystem"]
        SINK["engine/trace_sink.py<br/>EventLog Bus"]:::obs
        REC["testing/recorder.py<br/>TraceRecorder (trace.v1.json)"]:::obs
        PLAYER["testing/player.py<br/>TracePlayer (Deterministic Replay)"]:::obs
        GOLD["testing/golden.py<br/>GoldenComparator (Regression Check)"]:::obs
        VIZ["viz/<br/>trace_view.py &amp; Perfetto Export"]:::obs
    end

    subgraph Foundation["Foundation Layer (Zero Outgoing Dependencies)"]
        ERR["errors.py<br/>NE1001-NE5001 3-Part Diagnostics"]:::fdn
        PATHS["paths.py<br/>Repo Root &amp; Data File Locators"]:::fdn
        TRC_VAL["trace.py<br/>trace.v1.json Schema Validator"]:::fdn
    end

    CLI &amp; SIM_SESS --> CONV &amp; TOOLS
    MCP_SRV --> TOOLS
    CONV --> GATE &amp; TL &amp; HAL_DIG
    TOOLS --> CONV
    GATE --> RESOLV &amp; CONST &amp; CB
    COMP --> TREE &amp; BIN &amp; HAL_BOARD
    GATE -.->|FactSource protocol| MOD_SYS
    MOD_SYS --> GRAMMAR &amp; PROV
    VFSM -.->|Barge-in abort &lt;= 20ms| CONV
    HAL_DIG --> HAL_BASE
    HAL_SIM &amp; HAL_LINUX --> HAL_BASE

    GATE &amp; CONV &amp; HAL_BASE &amp; VFSM --> SINK
    SINK --> REC
    REC &amp; PLAYER &amp; GOLD &amp; VIZ --> TRC_VAL
```

---

## 2. Ma trận Trách nhiệm & Ranh giới Import (Responsibility Matrix)

Bảng dưới đây quy định ranh giới trách nhiệm và quyền `import` của từng phân tầng để bảo đảm hệ thống không bị phân mảnh hay phá vỡ tính tất định:

| Phân tầng | Tệp chính | Trách nhiệm cốt lõi | Được import bởi | TUYỆT ĐỐI KHÔNG được import |
|:---|:---|:---|:---|:---|
| **Foundation** | `errors.py`, `paths.py`, `trace.py` | Lớp cơ sở: Chuẩn hóa phân cấp lỗi 3 thành phần (`NE*`), tìm đường dẫn thư mục/wheel, thẩm định JSON Schema `trace.v1`. | Mọi tầng khác | Không được import bất kỳ module nội bộ nào của NeuroEdge. |
| **L3 Core Engine** | `gate_resolver.py`, `constraints.py`, `gate.py`, `compiler.py`, `binary_tree.py`, `circuit_breaker.py` | Động cơ Gate thuần: Phân giải chuỗi `extends`, cưỡng chế 5 nguyên tắc kế thừa, lượng giá Gate (`evaluate()`), biên dịch cấu trúc nhị phân `NETR v1`, bảo vệ mạch ngắt. | `actions`, `sim`, `cli`, `testing` | Không import `hal`, `actions`, `sim`, `models` (ngoại lệ duy nhất: `compiler` đọc `hal/board.py` để đối chiếu năng lực lúc build). |
| **L3 Actions** | `spec.py`, `conversation.py`, `token.py`, `tools.py`, `confirmation.py` | Hợp đồng hành động: Quản lý `@action`, cấp phát và tiêu hủy token dùng 1 lần (`TokenLedger`), điều phối `c.do()` và `dispatch()`, quản lý xác nhận `on_block: ask`. | `sim`, `cli`, `testing`, `mcp_*` | Không import `sim`, `cli`. |
| **L1 HAL** | `base.py`, `board.py`, `digital.py`, `sim.py`, `linux.py`, `sensor.py`, `display.py` | Trừu tượng hóa 5 nguyên thủy: Khai báo năng lực bo mạch (`BoardProfile`), cưỡng chế kiểm tra token trước khi cấp xung GPIO, từ chối mọi lệnh sai chân. | `actions` (qua cấp quyền `digital.grant`), `sim`, `testing` | Không import `engine`, `actions`, `models`. |
| **L2 Models** | `system.py`, `grammar.py`, `knowledge.py`, `providers/` | Trừu tượng hóa AI: Cung cấp dữ kiện có cấu trúc `SystemOne` và suy luận mở `SystemTwo` (LiteLLM SDK / Custom adapter). | `engine` (chỉ qua giao thức `FactSource`), `sim` | Không import các SDK bên ngoài trực tiếp vào lõi (phải bọc sau `providers/`). |
| **L2 Perception** | `voice_fsm.py`, `voice_session.py` | Máy trạng thái thoại: Điều phối 5 trạng thái thoại, tính thời gian ngắt lời (`barge-in`), phát tín hiệu thu hồi lệnh actuator đang chờ. | `sim` | Không gọi thẳng HAL (chỉ thông qua danh sách `pending_commands` được tiêm vào). |
| **L0 Sim & CLI** | `sim/session.py`, `sim/ui.py`, `cli/main.py`, `run.py`, `build.py` | **Hub lắp ráp duy nhất (The Assembly Hub):** Nơi duy nhất được phép khởi tạo và kết nối toàn bộ HAL, Engine, Actions, Models thành một phiên chạy thực thi. | Không có (đây là tầng đỉnh) | Không được chứa logic phán quyết an toàn (mọi phán quyết phải đẩy xuống Engine). |
| **Observability** | `trace_sink.py`, `recorder.py`, `player.py`, `golden.py`, `viz/` | Quan sát & Kiểm chứng: Thu thập sự kiện qua bus `EventLog`, ghi vết JSON, phát lại vết ghi trên HAL thật, so khớp ảnh chuẩn golden. | `cli`, `sim` | Không can thiệp vào logic điều khiển hoặc sửa đổi phán quyết của Gate. |

---

## 3. Các Giao diện Giao thức Cốt lõi (Core Protocols & Contracts)

### 3.1 Giao thức Nguồn Dữ kiện (`FactSource` Protocol)
Nằm tại `models/system.py`, đây là giao thức lỏng giúp `GateEngine` thẩm định điều kiện mà không cần phụ thuộc vào mô hình AI cụ thể:

```python
from typing import Protocol, Any

class FactSource(Protocol):
    """Giao thức cung cấp dữ kiện cho Gate Engine thẩm định."""
    def get_fact(self, criterion_name: str, deadline_ms: float) -> tuple[Any, float]:
        """
        Trả về (giá trị_dữ_kiện, độ_tin_cậy_0_đến_1).
        Nếu hết deadline hoặc không có dữ kiện, trả về (None, 0.0).
        """
        ...
```

### 3.2 Hợp đồng Sổ Token Dùng Một Lần (`TokenLedger` Contract)
Nằm tại `actions/token.py`, đảm bảo không thể kích hoạt chân vật lý hai lần bằng cùng một phán quyết:

```python
class Token:
    digest: str      # Mã băm SHA-256 của Gate đã cấp phép
    nonce: int       # Số ngẫu nhiên duy nhất của phiên
    granted_pins: set[str]  # Danh sách chân logic được phép kích hoạt
    expires_at_ms: float   # Thời điểm hết hạn (TTL = p95 * 3)

class TokenLedger:
    def issue(self, gate_digest: str, pins: set[str], ttl_ms: float) -> Token: ...
    def authorize(self, token: Token, pin_name: str) -> bool: ...
    def close(self, token: Token) -> None: ...
```

### 3.3 Giao thức Bus Sự kiện Chung (`EventLog` Protocol)
Nằm tại `engine/trace_sink.py`, mọi thành phần trong hệ thống đều bắn sự kiện qua một bus duy nhất để tạo thành tệp `trace.v1.json`:

```python
class EventLog(Protocol):
    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Ghi nhận một sự kiện vào dòng thời gian của phiên chạy."""
        ...
```

---

## 4. Năm Điều Luật Bất biến Về Phụ thuộc Kiến trúc

Để bảo vệ tính toàn vẹn và ngăn chặn suy thoái an toàn:

1. **Luật 1 (`engine` cô lập tuyệt đối):** `engine` không bao giờ biết `hal`, `actions`, hay `sim` tồn tại. Nó chỉ nhận dữ kiện qua `FactSource` và xuất phán quyết `ALLOW` hoặc `BLOCK`.
2. **Luật 2 (`hal` không chứa logic nghiệp vụ):** `hal` không bao giờ biết `engine` là gì. Nó chỉ biết nhận một lệnh chân kèm một `Token`. Nếu token hợp lệ và chưa dùng $\rightarrow$ cho phép kích chân; ngược lại $\rightarrow$ từ chối ngay lập tức.
3. **Luật 3 (Chiếc cầu duy nhất `actions/conversation.py`):** Cầu nối duy nhất giữa `engine` và `hal` là lớp `ConversationContext` thông qua phương thức `c.do()`.
4. **Luật 4 (Một hub lắp ráp duy nhất):** `sim/session.py` (hoặc `main.c` trên firmware) là nơi duy nhất được quyền tạo các đối tượng và ráp nối các layer với nhau.
5. **Luật 5 (Hợp đồng lỗi 3 thành phần):** Mọi exception văng ra phải kế thừa từ `NeuroEdgeError(where=..., why=..., how=...)` để đảm bảo trải nghiệm lập trình viên nhất quán.
