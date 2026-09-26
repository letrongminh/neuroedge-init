# 03 · Host Python Components (C4 L3)

> **Status:** `done` (I0–I4). Implementation source is located at `python/neuroedge/`. See full repository layout in [`CONTRIBUTING.md` §6](../../CONTRIBUTING.md#6-cấu-trúc-kho).

---

## 1. Host Component Layering Diagram (C4 L3)

The Host Python Runtime is organized into 8 distinct architectural layers with strict unidirectional dependency flow (upper layers depend on lower layers; reverse imports and cyclic dependencies are strictly prohibited):

![E-03 · Host Layers](../assets/svg/E-03-host-layers.svg)
*Figure E-03 — Host Layer Architecture: Directed arrows indicate permissible dependency directions (top invokes bottom).*

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

## 2. Component Responsibility & Import Boundaries

The table governs import permissions and boundaries across layers to preserve architectural determinism:

| Layer | Primary Files | Core Responsibilities | Imported By | STRICTLY FORBIDDEN from Importing |
|:---|:---|:---|:---|:---|
| **Foundation** | `errors.py`, `paths.py`, `trace.py` | Low-level utilities: 3-part structured errors (`NE*`), package path resolution, JSON Schema validation for `trace.v1`. | All layers | Must not import any internal NeuroEdge module. |
| **L3 Core Engine** | `gate_resolver.py`, `constraints.py`, `gate.py`, `compiler.py`, `binary_tree.py`, `circuit_breaker.py` | Pure Gate rule engine: Resolves `extends` chains, enforces 5 inheritance safety principles, evaluates Gates (`evaluate()`), compiles binary `NETR v1`, circuit breaker. | `actions`, `sim`, `cli`, `testing` | Must not import `hal`, `actions`, `sim`, `models` (sole exception: `compiler` reads `hal/board.py` for build-time capability checking). |
| **L3 Actions** | `spec.py`, `conversation.py`, `token.py`, `tools.py`, `confirmation.py` | Action contract surface: `@action` enforcement, single-use token lifecycle (`TokenLedger`), execution dispatching (`dispatch()`), human confirmation management (`on_block: ask`). | `sim`, `cli`, `testing`, `mcp_*` | Must not import `sim`, `cli`. |
| **L1 HAL** | `base.py`, `board.py`, `digital.py`, `sim.py`, `linux.py`, `sensor.py`, `display.py` | 5-primitive hardware abstraction: `BoardProfile` capability definitions, token verification before GPIO pulse, refusal of unknown pins. | `actions` (via `digital.grant`), `sim`, `testing` | Must not import `engine`, `actions`, `models`. |
| **L2 Models** | `system.py`, `grammar.py`, `knowledge.py`, `providers/` | AI abstraction: Supplies structured facts via `SystemOne` and open reasoning via `SystemTwo` (LiteLLM SDK / Custom adapter). | `engine` (via `FactSource` protocol only), `sim` | Must not import external vendor SDKs directly into core (must be encapsulated behind `providers/`). |
| **L2 Perception** | `voice_fsm.py`, `voice_session.py` | Conversational FSM: Coordinates 5 voice states, tracks barge-in timing, emits abort signals for queued actuator commands. | `sim` | Must not touch HAL directly (only interacts via injected `pending_commands`). |
| **L0 Sim & CLI** | `sim/session.py`, `sim/ui.py`, `cli/main.py`, `run.py`, `build.py` | **Sole System Assembly Hub:** The only place authorized to instantiate and wire HAL, Engine, Actions, and Models into an executable session. | None (Top layer) | Must not contain embedded safety adjudication logic (all safety decisions must delegate down to Engine). |
| **Observability** | `trace_sink.py`, `recorder.py`, `player.py`, `golden.py`, `viz/` | Action CI & Telemetry: Aggregates events via `EventLog` bus, serializes JSON traces, replays sessions on live HAL, golden diff checks. | `cli`, `sim` | Must not interfere with execution decisions or alter Gate verdicts. |

---

## 3. Core Protocols & Contracts

### 3.1 Fact Source Protocol (`FactSource`)
Defined in `models/system.py`, this structural protocol decouples `GateEngine` from specific AI models:

```python
from typing import Protocol, Any

class FactSource(Protocol):
    """Supplies factual truth values for Gate adjudication."""
    def get_fact(self, criterion_name: str, deadline_ms: float) -> tuple[Any, float]:
        """
        Returns (fact_value, confidence_score_0_to_1).
        Returns (None, 0.0) if unavailable or deadline expires.
        """
        ...
```

### 3.2 Single-Use Token Ledger Contract (`TokenLedger`)
Defined in `actions/token.py`, guarantees physical pins cannot be re-triggered by an expired or reused verdict:

```python
class Token:
    digest: str      # SHA-256 hash of the authorising Gate
    nonce: int       # Unique random session nonce
    granted_pins: set[str]  # Logical pin names authorized for actuation
    expires_at_ms: float   # Monotonic expiration timestamp (TTL = p95 * 3)

class TokenLedger:
    def issue(self, gate_digest: str, pins: set[str], ttl_ms: float) -> Token: ...
    def authorize(self, token: Token, pin_name: str) -> bool: ...
    def close(self, token: Token) -> None: ...
```

### 3.3 Universal Event Bus Protocol (`EventLog`)
Defined in `engine/trace_sink.py`, all components emit lifecycle telemetry into a unified bus to build canonical `trace.v1.json` artifacts:

```python
class EventLog(Protocol):
    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Emits an event into the session timeline."""
        ...
```

---

## 4. The Five Invariant Architecture Rules

To guarantee system determinism and prevent architectural drift:

1. **Rule 1 (`engine` absolute isolation):** `engine` never imports `hal`, `actions`, or `sim`. It accepts facts strictly via `FactSource` and outputs deterministic `ALLOW` or `BLOCK` verdicts.
2. **Rule 2 (`hal` zero-business-logic):** `hal` never knows what a Gate is. It merely receives a pin command with an attached `Token`. If the token is authentic and unconsumed $\rightarrow$ pulse physical pin; otherwise $\rightarrow$ refuse command immediately.
3. **Rule 3 (The Sole Bridge `actions/conversation.py`):** The only bridge linking `engine` and `hal` is `ConversationContext` via the `c.do()` entrypoint.
4. **Rule 4 (Single Assembly Hub):** `sim/session.py` (or `main.c` on firmware) is the sole orchestrator permitted to wire dependencies together.
5. **Rule 5 (Three-Part Error Hierarchy):** All raised exceptions must inherit from `NeuroEdgeError(where=..., why=..., how=...)` to guarantee actionable developer feedback.
