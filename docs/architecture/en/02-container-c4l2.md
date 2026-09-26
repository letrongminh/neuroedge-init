# 02 · Containers & Process Boundaries (C4 L2)

> **Status:** `done` for Host Runtime, ESP32-S3 Firmware, and CLI / Action CI; `planned` for Fleet OS, Gate Registry, NeuroBrain, and Robotics Nodes (I8–I18). See [`00-overview.md`](00-overview.md) for full documentation map.

---

## 1. System Container Diagram (C4 L2)

The C4 Level 2 diagram decomposes the NeuroEdge platform into independent execution runtimes, operating system processes, and persistent data stores:

![E-02 · Containers](../assets/svg/E-02-containers.svg)
*Figure E-02 — Container Topology: Solid boxes are implemented (done) · Dashed boxes are roadmap items (planned).*

```mermaid
flowchart TB
    classDef primary fill:#2563eb,stroke:#1d4ed8,color:#ffffff,stroke-width:2px,font-weight:bold;
    classDef core fill:#eff6ff,stroke:#3b82f6,color:#1e3a8a,stroke-width:1.5px;
    classDef mcu fill:#f0fdf4,stroke:#16a34a,color:#14532d,stroke-width:2px,font-weight:bold;
    classDef store fill:#f1f5f9,stroke:#64748b,color:#0f172a,stroke-width:1.5px;
    classDef external fill:#fff7ed,stroke:#ea580c,color:#7c2d12,stroke-width:1.5px;
    classDef planned fill:#faf5ff,stroke:#a855f7,color:#6b21a8,stroke-dasharray: 4 3;

    subgraph DevMachine["Host Workstation &amp; CI Runner"]
        CLI["CLI &amp; Action CI Runner<br/><b>Python 3.11+ Typer / Rich / Pytest</b><br/>run · build · verify · replay · record · test"]:::primary
        HOST["Host Python Runtime<br/><b>Package neuroedge</b><br/>Engine · Actions · SimHAL · LinuxHAL · Models · MCP Host"]:::core
        SIM_UI["Local Sim Web UI<br/><b>HTTP 127.0.0.1 :8765</b><br/>Virtual Board &amp; In-Person Confirmations"]:::core
        TRACE_STORE[("Trace Storage<br/><b>Local Filesystem</b><br/>traces/*.json · fixtures/")]:::store
        
        CLI --> HOST
        HOST <--> SIM_UI
        HOST --> TRACE_STORE
        CLI --> TRACE_STORE
    end

    subgraph EmbeddedDevice["Edge Microcontroller (ESP32-S3 Box-3 / QEMU)"]
        FW["Firmware C99 Runtime<br/><b>ESP-IDF v5.1+ / FreeRTOS</b><br/>Walker C NETR · TokenLedger · Voice FSM · I2S/GPIO"]:::mcu
        FLASH_STORE[("On-Chip Flash Storage<br/><b>16MB SPI Flash</b><br/>NETR const trees · A/B Partitions · NVS")]:::store
        
        FW <--> FLASH_STORE
    end

    subgraph CloudServices["Cloud &amp; Fleet Platform (I9–I10 Planned)"]
        FLEET["Fleet OS Backend<br/><b>Hawkbit Canary OTA &amp; EMQX Broker</b><br/>mTLS :8883"]:::planned
        REGISTRY["Gate Registry<br/><b>CNCF ORAS / OCI Signed Store</b>"]:::planned
        VAULT[("Central Trace Vault<br/><b>Standard 90d · Enterprise 3yr</b>")]:::planned
        
        FLEET <--> VAULT
    end

    subgraph ExternalActors["External Ecosystem"]
        EXT_MCP["Claude Desktop / MCP Client<br/><b>External AI Desktop</b>"]:::external
        EXT_LLM["AI Cloud Providers<br/><b>OpenAI / Anthropic / LiteLLM</b>"]:::external
    end

    CLI <-->|1. Stdio JSON-RPC IPC| EXT_MCP
    HOST <-->|2. HTTPS TLS 1.3 / WebSocket| EXT_LLM
    HOST -->|3. neuroedge build (NETR binary + headers)| FW
    FW <-->|4. UART NE1 Framing (115200 8N1)| HOST
    FW -.->|5. MQTT 5.0 / mTLS :8883| FLEET
    CLI -.->|6. OCI Publish/Pull Gates| REGISTRY
    FW -.->|7. Telemetry &amp; Crash Dumps| VAULT
```

---

## 2. Implemented Containers (Done — I0–I4)

### 2.1 Host Python Runtime (`neuroedge` Package)
* **Technology & Platform:** Python 3.11+, standard library `tomllib` (zero external TOML parser dependency). Runs natively on macOS, Linux x86-64, and Linux ARM64 (Raspberry Pi 5).
* **Core Responsibilities:**
  * Implements Gate inheritance resolution (`GateResolver`), 5-principle safety enforcement, and compiles flat binary decision trees `NETR v1` (`compiler.py`).
  * Executes the `actions` domain: Manages conversation session context (`ConversationContext`), manages single-use token lifecycles (`TokenLedger`), and provides safe tool dispatching (`dispatch()`).
  * Runs `SimHAL` and `LinuxHAL` (direct Linux kernel interface via `gpiod` v2 / `gpio-sim`).
  * Interfaces with AI models: `SystemOne` (deterministic local grammar) and `SystemTwo` (LiteLLM SDK embedded in-process, `Q-10`).
  * Serves local embedded MCP server and localhost Web UI (`sim/ui.py`).

### 2.2 ESP32-S3 Firmware (Embedded C99 / ESP-IDF)
* **Technology & Platform:** Pure C99, ESP-IDF framework (v5.2.1 for physical silicon, v5.4 for Espressif QEMU). FreeRTOS real-time operating system.
* **Core Responsibilities:**
  * **C Decision Tree Walker (`ne_gate/ne_walker.c`):** Directly walks memory-mapped `NETR v1` binary trees in Flash, zero heap allocation (0 static RAM), stack usage $\le 512$ bytes (`Q-9`, `Q-23`).
  * **C Token Ledger (`ne_gate/ne_token.c`):** Manages 4 single-use token slots on the microcontroller with monotonic wrap-safe expiration timers.
  * **UART Trace Output Module (`ne_trace`):** Formats and emits JSON-lines trace events prefixed with `NE1 ` via UART0 / USB-CDC (`TSK-S4-09`).
  * **Secure Boot Sequence (`main.c`):** Performs hardware memory probing (`memory_probe`) $\rightarrow$ executes flash-embedded Gate self-test $\rightarrow$ only initializes networking and main loop if self-test outputs `NE_SELFTEST PASS`.

### 2.3 CLI & Action CI Framework
* **Technology & Platform:** Typer, Rich, Pytest, DeepDiff.
* **Core Responsibilities:**
  * Unified developer interface: `new` (scaffold templates), `run` (interactive REPL), `build` (capability checking), `test` (runs Action CI assertion suite), `record` (session logging), `replay` (deterministic HAL replay), `verify` (multi-target equivalence checker).
  * Strict enforcement of the **Canonical Exit Code Contract**:
    * Code `0`: Test suite or CLI command passed with 100% compliance.
    * Code `1`: Syntax error, safety regression, or Gate contract violation.
    * Code `2`: Feature or target environment not yet implemented (enabling CI to distinguish between "broken" and "planned").

---

## 3. Planned Containers (Roadmap I8–I18)

The current architecture provides architectural extension points and data schema reservations for upcoming containers:

| Container | Increment | Proposed Tech Stack | Core Responsibilities | Architectural Groundwork Already in Place |
|:---|:---:|:---|:---|:---|
| **Fleet OS Backend** | **I9** | FastAPI, Eclipse Hawkbit, EMQX Broker, PostgreSQL | Orchestrates canary OTA campaigns (1% $\rightarrow$ 10% $\rightarrow$ 100%, halts on error spike); manages fleet inventory and mTLS credentials. | Trace schemas include `metadata.device_id`; A/B dual-partition contracts and RSA/ECDSA verification defined in FR-OTA. |
| **Gate Registry** | **I10** | CNCF ORAS, Harbor OCI Registry, Cosign | Stores and indexes public Gate policies, provider adapters, and verified community HAL ports. | `gate publish` computes canonical RFC 8785 JCS digests; `digests.lock` enforces immutability; URI scheme `neuroedge://<pkg>/<gate>@<semver>`. |
| **Trace Vault** | **I9** | S3-compatible Object Storage (MinIO / Ceph), ClickHouse | Centralized telemetry store archiving millions of field incident traces; enables fast query of BLOCK verdicts and latency SLAs. | Self-contained canonical `trace.v1.json` format, directly ingestible without schema transformation. |
| **NeuroBrain Copilot** | **I12** | Python package `neuroedge.brain`, LLM Hardware Assistant | Conversational assistant for board bring-up: scans I2C busses, suggests type-safe Gates and Actions (Chat Contracting). | **Invariant B-1:** `neuroedge.brain` must route actions strictly via `dispatch()` $\rightarrow$ Gate; cannot touch HAL directly. |
| **Robotics Distributed Nodes** | **I14** | Zenoh-pico, C/C++ micro-ROS runtime | Distributed mobile robot architecture: Central Brain (Linux RPi 5) coordinates MCU actuator nodes over real-time network. | Multi-node Gate partitioning; deterministic token lease mechanism (`motion.*`, `Q-37`); autonomous safe state fallback (`Q-35`). |

---

## 4. Inter-Container Communication Matrix

The table defines communication channels, wire protocols, security invariants, and latency budgets between containers:

| Source $\rightarrow$ Destination | Wire Channel | Data Payload Format | Authentication & Security | Latency Budget |
|:---|:---|:---|:---|:---|
| **CLI $\rightarrow$ Host Runtime** | In-process call | Python Objects / DTOs | Process-internal | $< 1\text{ ms}$ |
| **Host $\rightarrow$ Local Sim UI** | HTTP / WebSocket | JSON / Server-Sent Events (SSE) | Same-origin 127.0.0.1, Cross-Origin POST denied | $< 50\text{ ms}$ |
| **External MCP $\rightarrow$ Host** | Stdio (Standard I/O) | JSON-RPC 2.0 (MCP Protocol) | Tagged as `call_source = "mcp"`, verified by Gate | $< 100\text{ ms}$ |
| **Host $\rightarrow$ AI Providers** | HTTPS over WAN | JSON (OpenAI API payload) | TLS 1.3, API Key via environment variable | P95 $< 1,500\text{ ms}$ (`NFR-PERF-07`) |
| **Firmware $\rightarrow$ Host** | UART0 / USB-CDC or TCP | JSON-Lines (`NE1 ` prefix) | Baudrate 921600 (or TCP port 5555 under QEMU) | $< 20\text{ ms}$ per event line |
| **Host $\rightarrow$ Firmware (Build)** | Compiler code generation | Binary NETR v1 + C Header `.h` | CRC32 and SHA-256 verification | Build-time operation |
| **Firmware $\rightarrow$ Fleet OS** *(I9)* | MQTT 5.0 over WAN | Compressed JSON / CBOR | Mutual TLS (mTLS) with per-device X.509 cert | Asynchronous telemetry |
| **Robot Brain $\rightarrow$ Nodes** *(I14)* | Zenoh-pico Bus | CDR / Raw Binary Frames | Black channel (IEC 61784-3), Token lease | $< 10\text{ ms}$ (Real-time) |
