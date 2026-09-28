#!/usr/bin/env python3
"""Sinh các poster kiến trúc (docs/architecture/assets/) từ một mô tả duy nhất.

Mỗi poster là một hàm dưới đây. Từ đó sinh ra **cả hai** tệp:

* ``assets/excalidraw/<id>.excalidraw`` — mở và sửa được bằng Excalidraw;
* ``assets/svg/<id>.svg`` — ảnh mà tài liệu nhúng.

Sửa poster = sửa hàm ở đây rồi chạy lại script; **đừng sửa tay** hai tệp sinh ra
(sửa tay trong Excalidraw thì chép thay đổi về đây). ``lint`` từ chối hộp chồng
nhau, chữ tràn hộp, mũi tên trỏ tới hộp không có.

    python3 scripts/gen_architecture_diagrams.py           # ghi tệp
    python3 scripts/gen_architecture_diagrams.py --check   # không ghi; thoát 1 nếu lệch

CI chạy --check (python/tests/test_architecture_diagrams.py). Nhãn trong hình là
tiếng Anh để một bộ hình dùng chung cho hai cây vi/ và en/ (docs/architecture/README.md).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from archdiag import Box, Diagram, Edge, Group, lint, render_excalidraw, render_svg  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "architecture" / "assets"


def e01_context() -> Diagram:
    d = Diagram(
        "E-01-system-context",
        "E-01 · System context (C4 L1)",
        "Who uses NeuroEdge and which outside systems it talks to. Every physical action passes a gate first.",
        1820,
        940,
    )
    # people (left column)
    d.groups.append(Group("people", 40, 100, 380, 800, "People", "boundary"))
    people = [
        ("maker", "Maker / app developer", ("Writes agent.toml, gates, actions", "neuroedge new · run · test")),
        ("embedded", "Embedded / core engineer", ("Builds firmware, ports the HAL", "build --target esp32s3 · verify")),
        ("auditor", "Safety reviewer / QA", ("Reads gates and traces", "gate explain · trace view · replay")),
        ("oem", "OEM hardware partner", ("Declares a board, ports the HAL", "board.toml · compliance vectors")),
        ("operator", "Fleet operator", ("Rolls out updates, pulls traces", "Fleet OS (I9)")),
    ]
    for i, (pid, title, lines) in enumerate(people):
        d.boxes.append(Box(pid, 64, 140 + i * 150, 332, 118, title, lines, "person",
                           "planned" if pid == "operator" else "done"))
    # the system (middle)
    d.groups.append(Group("ne", 600, 230, 620, 470, "NeuroEdge system boundary", "host"))
    d.boxes.append(Box("neuroedge", 630, 280, 560, 180, "NeuroEdge",
                       ("Gated edge runtime: SDK + CLI (Python), firmware (C99)",
                        "Every command to a pin passes a typed, versioned gate",
                        "Every verdict goes into a replayable trace"), "system"))
    d.boxes.append(Box("device", 630, 540, 260, 130, "Device",
                       ("sim · linux · esp32s3", "virtual or real pins"), "device", "partial"))
    d.boxes.append(Box("files", 930, 540, 260, 130, "Project files",
                       ("agent.toml · gates/*.yaml", "board.toml · traces/*.json"), "store"))
    # external systems (right column)
    d.groups.append(Group("ext", 1400, 100, 380, 800, "External systems", "cloud"))
    ext = [
        ("llm", "LLM providers (System 2)", ("OpenAI-compatible via LiteLLM", "or a user adapter"), "done"),
        ("jev", "Jev on OpenRouter (System 1)", ("System One API, typed questions", "typesafe/jev-1.13"), "done"),
        ("speech", "Speech providers", ("STT / TTS, OpenAI audio API", "cloud or local server"), "done"),
        ("mcp", "MCP clients", ("Claude Desktop, other agents", "stdio JSON-RPC"), "done"),
        ("idf", "ESP-IDF v5.4 + QEMU", ("Toolchain and emulator", "Docker espressif/idf:v5.4"), "done"),
        ("fleet", "Fleet OS · Gate Registry", ("Rollouts, incident traces", "I9 · I10"), "planned"),
    ]
    for i, (eid, title, lines, status) in enumerate(ext):
        d.boxes.append(Box(eid, 1424, 132 + i * 126, 332, 104, title, lines, "external", status))
    L = 510  # left corridor x
    R = 1310  # right corridor x
    d.edges += [
        Edge("maker", "neuroedge", "write · run · test", via=((L - 30, 199), (L - 30, 320)), label_at=(L - 30, 240)),
        Edge("embedded", "neuroedge", "build · flash · verify", via=((L, 349), (L, 370)), label_at=(L, 349)),
        Edge("auditor", "neuroedge", "explain · replay", via=((L - 30, 499), (L - 30, 420)), label_at=(L - 30, 470)),
        Edge("oem", "device", "board + HAL port", via=((L, 649), (L, 605)), label_at=(L, 649)),
        Edge("operator", "device", "OTA · traces (I9)", dashed=True, via=((760, 799),), label_at=(560, 799)),
        Edge("neuroedge", "llm", "HTTPS · key from env", via=((R - 40, 300), (R - 40, 184)), label_at=(R - 40, 205)),
        Edge("neuroedge", "jev", "HTTPS", via=((R, 330), (R, 310)), label_at=(R, 330)),
        Edge("neuroedge", "speech", "HTTPS or localhost", via=((R - 40, 400), (R - 40, 436)), label_at=(R - 40, 418)),
        Edge("mcp", "neuroedge", "tools/call · stdio", via=((R, 562), (R, 440)), label_at=(R, 520)),
        Edge("neuroedge", "idf", "ESP-IDF project", via=((R - 60, 450), (R - 60, 686)), label_at=(R - 60, 610)),
        Edge("device", "fleet", "MQTT (planned)", dashed=True, via=((760, 860), (1590, 860)), label_at=(1180, 860)),
        Edge("neuroedge", "device", "c.do() → gate → pin", via=((760, 460),), label_at=(760, 500)),
        Edge("neuroedge", "files", "reads · writes", via=((1060, 460),), label_at=(1060, 500)),
    ]
    return d


def e02_containers() -> Diagram:
    d = Diagram(
        "E-02-containers",
        "E-02 · Containers (C4 L2)",
        "The processes, the library, the firmware image and the files — and how each pair talks.",
        2000,
        1130,
    )
    A, B, C = 80, 560, 1060  # column x
    d.groups.append(Group("host", 40, 100, 1360, 600,
                          "Developer machine · CI runner · Linux device — Python 3.11+", "host"))
    d.boxes.append(Box("cli", A, 150, 300, 130, "CLI  neuroedge",
                       ("one process per command", "new · build · run · record · replay", "verify · test · trace · board"),
                       "container"))
    d.boxes.append(Box("lib", B, 150, 340, 130, "neuroedge library",
                       ("engine · actions · hal · models", "perception · sim · testing · viz", "imported in-process"),
                       "container"))
    d.boxes.append(Box("ui", C, 150, 300, 130, "Sim web UI",
                       ("http.server on 127.0.0.1", "GET /events (SSE) · POST /command", "POST /confirm, same origin"),
                       "container"))
    d.boxes.append(Box("mcpsrv", A, 380, 300, 120, "MCP server",
                       ("neuroedge mcp serve", "JSON-RPC over stdio", "every tools/call passes a gate"), "container"))
    d.boxes.append(Box("files", B, 380, 340, 120, "Files",
                       ("project: agent.toml · gates/ · actions/", "repo: schemas/ · boards/ · fixtures/",
                        "traces/*.json · digests.lock"), "store"))
    d.boxes.append(Box("build", C, 380, 300, 120, "Build output",
                       ("build/gates/*.netree · *.netree.h", "build/esp32s3/  ESP-IDF project"), "store"))
    d.boxes.append(Box("kernel", A, 560, 300, 110, "Linux kernel devices",
                       ("/dev/gpiochipN · hwmon · IIO", "/dev/fbN · PipeWire nodes"), "device", "partial"))
    d.groups.append(Group("dev", 40, 770, 1360, 260, "ESP32-S3-BOX-3 · Espressif QEMU — C99 on ESP-IDF v5.4",
                          "device"))
    d.boxes.append(Box("fw", B, 820, 340, 170, "Firmware image",
                       ("ne_gate: NETR walker, token ledger", "ne_agent: the agent's tables", "ne_trace: NE1 lines on UART",
                        "ne_ota: signed A/B update"), "device", "partial"))
    d.boxes.append(Box("flash", C, 820, 300, 170, "Flash (16 MB)",
                       ("factory · ota_0 · ota_1 (3.5 MB)", "nvs · otadata · phy_init", "storage (spiffs)"), "store"))
    d.groups.append(Group("ext", 1480, 100, 480, 930, "External systems", "cloud"))
    d.boxes.append(Box("llm", 1510, 150, 420, 100, "LLM providers · Jev",
                       ("OpenAI-compatible · System One API",), "external"))
    d.boxes.append(Box("speech", 1510, 290, 420, 100, "Speech providers", ("STT · TTS, cloud or localhost",), "external"))
    d.boxes.append(Box("client", 1510, 430, 420, 100, "MCP client", ("Claude Desktop starts mcp serve",), "external"))
    d.boxes.append(Box("fleet", 1510, 590, 420, 120, "Fleet OS · Gate Registry",
                       ("rollouts · trace vault · shared gates", "I9 · I10"), "external", "planned"))
    d.boxes.append(Box("ota", 1510, 850, 420, 110, "OTA image server",
                       ("any static HTTP(S) server", "one signed app image"), "external"))
    d.edges += [
        Edge("cli", "lib", "imports", label_at=(470, 215)),
        Edge("lib", "ui", "HTTP · SSE", both=True, label_at=(980, 215)),
        Edge("mcpsrv", "lib", "tools/call → dispatch", via=((470, 440), (470, 250)), label_at=(470, 340)),
        Edge("lib", "files", "load · write", label_at=(730, 330)),
        Edge("lib", "build", "neuroedge build", via=((980, 250), (980, 440)), label_at=(980, 340)),
        Edge("lib", "kernel", "LinuxHAL", via=((515, 265), (515, 615)), label_at=(515, 580)),
        Edge("lib", "llm", "HTTPS · key from env", via=((860, 122), (1445, 122), (1445, 200)),
             label_at=(1150, 122)),
        Edge("lib", "speech", "HTTPS", via=((790, 136), (1455, 136), (1455, 340)), label_at=(1455, 300)),
        Edge("client", "mcpsrv", "stdio · child process", via=((1465, 480), (1465, 535), (230, 535)),
             label_at=(760, 535)),
        Edge("build", "fw", "idf.py build · flash", via=((1210, 735), (730, 735)), label_at=(1000, 735)),
        Edge("fw", "cli", "UART NE1 lines → record · verify", via=((20, 905), (20, 215)), label_at=(290, 905)),
        Edge("fw", "flash", "trees read in place", label_at=(980, 905)),
        Edge("fw", "ota", "HTTP(S) GET image", via=((700, 1080), (1720, 1080)), label_at=(1180, 1080)),
        Edge("fw", "fleet", "MQTT (planned)", dashed=True, via=((800, 752), (1440, 752), (1440, 650)),
             label_at=(1300, 752)),
    ]
    return d


def e03_host() -> Diagram:
    d = Diagram(
        "E-03-host-components",
        "E-03 · Host components (C4 L3)",
        "The subpackages of python/neuroedge/, higher ones depend on lower ones, never the reverse "
        "(locked by test_architecture_layers.py).",
        1800,
        1260,
        legend=("done",),
    )
    W = 820
    d.boxes += [
        Box("cli", 60, 110, 1680, 90, "cli/ — Typer commands",
            ("new · build · run · record · replay · verify · test · gate · trace · board · mcp",), "container"),
        Box("testing", 60, 250, W, 120, "testing/ — Action CI",
            ("TraceRecorder · TracePlayer · GoldenComparator", "assertions · uart (NE1 reader) · tool and voice corpora"),
            "test"),
        Box("perception", 920, 250, W, 120, "perception/ — voice",
            ("VoiceStateMachine (5 states) · VoiceSession", "STT · TTS · wake word providers"), "component"),
        Box("sim", 60, 420, W, 130, "sim/ — runtime assembly point",
            ("SimSession.load · handle() · call_tool() · confirm()", "ui.py: SessionServer, SSE, same-origin POST"),
            "component"),
        Box("mcp", 920, 420, 400, 130, "mcp_server · mcp_host",
            ("stdio MCP server", "System 2 as MCP host"), "component"),
        Box("viz", 1340, 420, 400, 130, "viz/", ("trace view HTML page", "Perfetto export"), "component"),
        Box("models", 60, 600, W, 130, "models/ — System 1, System 2",
            ("SystemOne (a FactSource) · SystemTwo · DegradationBreaker", "CommandGrammar · KnowledgeBase",
             "providers/: LiteLLM · System One API (Jev) · adapters"), "component"),
        Box("actions", 920, 600, W, 130, "actions/ — the only bridge to pins",
            ("@action · Conversation.do() · c.say()", "TokenLedger · dispatch() · ConfirmationBook"), "gate"),
        Box("engine", 60, 780, 1100, 150, "engine/ — pure core",
            ("gate.py evaluate · gate_resolver · constraints · arguments",
             "decision_tree walk · binary_tree (NETR v1) · canonical (JCS SHA-256)",
             "verdict · trace_sink (EventLog) · latency · circuit_breaker"), "gate"),
        Box("build", 1200, 780, 540, 150, "engine/ — build time",
            ("compiler.py: neuroedge build, agent vs board", "firmware.py: ESP-IDF project generator"), "component"),
        Box("hal", 60, 980, 1680, 110, "hal/ — L1, a leaf",
            ("HardwareAbstractionLayer (name check, then authorize) · board profiles",
             "SimHAL · LinuxHAL (libgpiod, sysfs, framebuffer, PipeWire) · audio (WAV, VAD)"), "device"),
        Box("fdn", 60, 1140, 1680, 80, "foundation",
            ("errors (NE codes, where · why · how) · paths · net (stdlib HTTP) · trace (trace.v1 validation)",), "component"),
    ]
    d.edges += [
        Edge("perception", "sim", "handle(spoken=True)", via=((1000, 395), (470, 395)), label_at=(740, 395)),
        Edge("sim", "actions", "dispatch()", via=((900, 500), (900, 640)), label_at=(900, 575)),
        Edge("mcp", "actions", "tools/call → dispatch", label_at=(1120, 575)),
        Edge("models", "engine", "implements FactSource", label_at=(470, 755)),
        Edge("actions", "engine", "evaluate()", label_at=(1040, 755)),
        Edge("actions", "hal", "grant · authorize", via=((1180, 730), (1180, 980)), label_at=(1180, 955)),
        Edge("build", "hal", "board check at build", label_at=(1470, 955)),
    ]
    return d


def e04_firmware() -> Diagram:
    d = Diagram(
        "E-04-firmware",
        "E-04 · Firmware components (C4 L3)",
        "What neuroedge build generates, what runs in app_main, and what the chip talks to. "
        "No FreeRTOS tasks, no GPIO, no audio yet.",
        1800,
        900,
    )
    d.groups.append(Group("gen", 40, 100, 400, 520, "Generated on the host", "host"))
    d.boxes += [
        Box("buildcmd", 70, 150, 340, 110, "neuroedge build --target esp32s3",
            ("every check, then render", "build/esp32s3/ ESP-IDF project"), "container"),
        Box("agent", 70, 330, 340, 130, "components/ne_agent",
            ("NETR tree per gate", "gate · pin · action tables", "self-test checks, host answers"), "component"),
        Box("ui", 70, 500, 340, 100, "ui/ — LVGL screens",
            ("not linked yet · host goldens",), "component", "partial"),
    ]
    d.groups.append(Group("fw", 480, 100, 860, 610, "Firmware image — C99 on ESP-IDF v5.4", "device"))
    d.boxes += [
        Box("main", 510, 150, 780, 150, "main/ — app_main, one task, sequential boot",
            ("memory_probe · gate_selftest · trace_vectors", "self-test fails ⇒ halt: no gate runtime, no network",
             "NE_SELFTEST · NE_TRACE DONE · NEUROEDGE_HEAP_JSON"), "device"),
        Box("gate", 510, 360, 240, 140, "ne_gate", ("NETR walker", "token ledger, 4 slots", "no heap, stack ≤ 512 B"), "gate"),
        Box("trace", 790, 360, 240, 140, "ne_trace", ("NE1 JSON lines", "≤ 512 bytes each", "format only"), "component"),
        Box("ota", 1070, 360, 220, 140, "ne_ota", ("signed A/B update", "rollback · high-water", "QEMU only"), "component",
            "partial"),
        Box("halc", 800, 560, 490, 120, "on-chip HAL",
            ("GPIO · I2S audio · I2C sensors · LCD", "TSK-S4-01 · I5"), "device", "planned"),
    ]
    d.groups.append(Group("flashg", 480, 750, 860, 120, "Flash 16 MB — partitions.csv", "device"))
    d.boxes.append(Box("flash", 510, 790, 800, 70, "factory · ota_0 · ota_1 (3.5 MB each) · nvs · otadata · storage",
                       (), "store"))
    d.groups.append(Group("out", 1400, 100, 360, 520, "Outside the chip", "cloud"))
    d.boxes += [
        Box("uart", 1430, 150, 300, 110, "neuroedge record · verify", ("UART NE1 lines → trace.v1",), "container"),
        Box("otasrv", 1430, 360, 300, 110, "OTA image server", ("any static HTTP(S) server",), "external"),
    ]
    d.edges += [
        Edge("buildcmd", "agent", "renders"),
        Edge("agent", "main", "linked in", via=((460, 395), (460, 225)), label_at=(460, 310)),
        Edge("main", "gate", "self-test · replay", label_at=(630, 330)),
        Edge("main", "trace", "session lines", label_at=(910, 330)),
        Edge("main", "ota", "boot · confirm · run", label_at=(1180, 330)),
        Edge("main", "uart", "UART", label_at=(1345, 225)),
        Edge("ota", "otasrv", "GET", label_at=(1345, 420)),
        Edge("gate", "flash", "trees read in place", via=((740, 500), (740, 790)), label_at=(660, 620)),
    ]
    return d


def e05_spine() -> Diagram:
    d = Diagram(
        "E-05-gate-spine",
        "E-05 · The gate spine (C4 L4)",
        "One policy from YAML to pin: resolved and compiled at build time, evaluated with the same semantics "
        "on the host and on the chip.",
        1900,
        900,
    )
    d.groups.append(Group("buildl", 40, 100, 1300, 210, "Build time — neuroedge build, gate lint, session load", "host"))
    d.groups.append(Group("hostl", 40, 340, 1820, 300, "Run time on the host — Python", "host"))
    d.groups.append(Group("chipl", 40, 680, 1820, 190, "Run time on the chip — C99", "device"))
    X = [60, 320, 580, 840, 1100, 1360, 1620]
    bw = 200
    d.boxes += [
        Box("yaml", X[0], 150, bw, 130, "Gate files", ("gates/*.yaml", "extends chain ≤ 3"), "store"),
        Box("resolve", X[1], 150, bw, 130, "Resolve", ("5 principles", "RFC-0004 · 0005 · 0006", "pure function"), "gate"),
        Box("resolved", X[2], 150, bw, 130, "ResolvedGate", ("to_artifact()", "gate_digest", "JCS + SHA-256"), "component"),
        Box("compile", X[3], 150, bw, 130, "compile_tree", ("criteria_order", "domains · admitted", "confidence floors"),
            "component"),
        Box("netr", X[4], 150, bw, 130, "NETR v1", ("binary · CRC", "frozen by RFC-0003", "const array in flash"), "store"),
    ]
    d.boxes += [
        Box("toolcall", X[0], 380, bw, 120, "ToolCall", ("name · arguments", "source"), "component"),
        Box("dispatch", X[1], 380, bw, 120, "dispatch()", ("schema check", "call_source fact"), "component"),
        Box("do", X[2], 380, bw, 120, "Conversation.do", ("the only bridge", "gate → token → body"), "gate"),
        Box("evaluate", X[3], 380, bw, 120, "evaluate · walk", ("facts within p95 budget", "first failure wins"), "gate"),
        Box("issue", X[4], 380, bw, 120, "TokenLedger.issue", ("one-time token", "TTL = p95 × 3"), "gate"),
        Box("authorize", X[5], 380, bw, 120, "HAL · authorize", ("pin name first", "then six token checks"), "device"),
        Box("pin", X[6], 380, bw, 120, "Pin", ("actuator_command", "SimHAL · LinuxHAL"), "device"),
        Box("onblock", X[3], 530, bw, 96, "on_block", ("deny · ask", "escalate · degrade"), "component"),
    ]
    d.boxes += [
        Box("facts", X[2], 720, bw, 120, "Facts", ("ne_fact[]", "domain index, no strings"), "component"),
        Box("decide", X[3], 720, bw, 120, "C walker", ("ne_evaluate · ne_decide", "same order as walk"), "gate"),
        Box("cissue", X[4], 720, bw, 120, "ne_token_issue", ("4 slots · nonce 16 B", "full ⇒ refuse"), "gate"),
        Box("cauth", X[5], 720, bw, 120, "ne_token_authorize", ("boot_id · slot · pin", "replay · TTL"), "gate"),
        Box("cpin", X[6], 720, bw, 120, "Pin driver", ("TSK-S4-01",), "device", "planned"),
    ]
    d.edges += [
        Edge("yaml", "resolve", ""), Edge("resolve", "resolved", ""), Edge("resolved", "compile", ""),
        Edge("compile", "netr", "encode"),
        Edge("compile", "evaluate", "tree JSON", label_at=(940, 325)),
        Edge("netr", "decide", "NETR in flash", via=((1330, 215), (1330, 660), (940, 660)), label_at=(1130, 660)),
        Edge("toolcall", "dispatch", ""), Edge("dispatch", "do", ""), Edge("do", "evaluate", ""),
        Edge("evaluate", "issue", "ALLOW"), Edge("issue", "authorize", "token"), Edge("authorize", "pin", ""),
        Edge("evaluate", "onblock", "BLOCK"),
        Edge("facts", "decide", ""), Edge("decide", "cissue", "ALLOW"), Edge("cissue", "cauth", "token"),
        Edge("cauth", "cpin", "", dashed=True),
    ]
    return d


def e06_evidence() -> Diagram:
    d = Diagram(
        "E-06-evidence-loop",
        "E-06 · The evidence loop",
        "Every session becomes a trace; a trace is recomputed on each target and compared by decisions, "
        "never by timing or words.",
        1800,
        760,
    )
    d.boxes += [
        Box("sess", 60, 150, 300, 120, "Session", ("sim or linux", "run · record · mcp serve"), "container"),
        Box("device", 60, 440, 300, 130, "Device", ("esp32s3 on QEMU", "boot replays the 3", "canonical traces"), "device",
            "partial"),
        Box("rec", 440, 150, 300, 120, "TraceRecorder", ("validates on save", "hashes text unless --raw"), "test"),
        Box("uart", 440, 440, 300, 130, "UART reader", ("record --target esp32s3", "NE1 sessions → trace.v1"), "test"),
        Box("trace", 820, 290, 300, 130, "trace.v1.json", ("facts · verdicts · pins", "one file per session"), "store"),
        Box("canon", 820, 560, 300, 120, "Canonical traces", ("happy-path · unverified", "network_offline — frozen"),
             "store"),
        Box("player", 1200, 150, 260, 130, "TracePlayer", ("replay on sim or linux", "verdicts, tokens, pins", "recomputed"),
            "test"),
        Box("golden", 1200, 440, 260, 130, "GoldenComparator", ("decision view:", "gates · reasons · on_block", "pin commands"),
            "gate"),
        Box("ok", 1540, 150, 220, 110, "Match", ("exit 0",), "component"),
        Box("bad", 1540, 460, 220, 110, "NE4002", ("SAFETY REGRESSION", "first divergence"), "gate"),
    ]
    d.edges += [
        Edge("sess", "rec", "events"),
        Edge("rec", "trace", "save", via=((970, 210),)),
        Edge("device", "uart", "NE1 lines"),
        Edge("uart", "trace", "sessions", via=((970, 505),)),
        Edge("canon", "device", "gen_firmware_vectors", via=((970, 720), (210, 720)), label_at=(590, 720)),
        Edge("trace", "player", "replay", via=((1150, 355), (1150, 215)), label_at=(1150, 290)),
        Edge("player", "golden", "compare"),
        Edge("trace", "golden", "device result", via=((1330, 400),), label_at=(1250, 400)),
        Edge("golden", "ok", "same", via=((1500, 470), (1500, 205)), label_at=(1500, 330)),
        Edge("golden", "bad", "differs"),
    ]
    return d


def e07_targets() -> Diagram:
    d = Diagram(
        "E-07-target-matrix",
        "E-07 · Five primitives × three targets",
        "Each cell: the backend that runs it, where it is tested automatically. One agent, one gate, "
        "no branching on target.",
        1800,
        1080,
    )
    cols = [("sim", "sim · sim-default"), ("linux", "linux · linux-rpi5"), ("esp", "esp32s3 · esp32s3-box-3")]
    X = [380, 850, 1320]
    CW = 440
    d.boxes += [Box(f"h-{k}", X[i], 110, CW, 60, t, (), "system") for i, (k, t) in enumerate(cols)]
    rows = [
        ("digital.out", [
            ("SimHAL, one-time token", ("tested every PR",), "done"),
            ("libgpiod v2, lines by name", ("every PR on gpio-sim",), "done"),
            ("C walker + token ledger", ("host C and QEMU · real pins: TSK-S4-01",), "partial")]),
        ("audio.in", [
            ("typed text · WAV → VAD → STT", ("every PR, fake providers",), "done"),
            ("WAV file backend · live PipeWire", ("file every PR · live not on hardware",), "partial"),
            ("I2S + AEC on the chip", ("I5",), "planned")]),
        ("audio.out", [
            ("TTS → speaker timeline → WAV", ("every PR, fake providers",), "done"),
            ("WAV file backend · live PipeWire", ("file every PR · live not on hardware",), "partial"),
            ("I2S codec", ("I5",), "planned")]),
        ("sensor.read", [
            ("scripted readings", ("every PR",), "done"),
            ("sysfs hwmon and IIO, by name", ("every PR on i2c-stub + lm75",), "done"),
            ("I2C driver", ("TSK-S4-03",), "planned")]),
        ("display", [
            ("frame in memory, digest", ("every PR",), "done"),
            ("framebuffer /dev/fbN", ("every PR on vfb / vkms",), "done"),
            ("LVGL on the panel", ("golden images on host every PR · panel: TSK-S4-01",), "partial")]),
    ]
    for r, (prim, cells) in enumerate(rows):
        y = 200 + r * 170
        d.boxes.append(Box(f"p-{r}", 60, y, 280, 140, prim, (), "container"))
        for c, (title, lines, status) in enumerate(cells):
            kind = "device" if status != "planned" else "device"
            d.boxes.append(Box(f"c-{r}-{c}", X[c], y, CW, 140, title, lines, kind, status))
    return d


def e08_deployment() -> Diagram:
    d = Diagram(
        "E-08-deployment",
        "E-08 · Deployment (C4)",
        "Where each part runs today, and where it will run once the boards arrive.",
        1800,
        1000,
    )
    d.groups.append(Group("dev", 40, 100, 560, 520, "Developer machine — macOS or Linux", "host"))
    d.boxes += [
        Box("venv", 70, 150, 500, 120, "python/.venv — neuroedge", ("CLI, library, pytest", "sim target, MCP server"),
            "container"),
        Box("browser", 70, 300, 240, 110, "Browser", ("sim page, 127.0.0.1",), "container"),
        Box("desktop", 330, 300, 240, 110, "Claude Desktop", ("starts mcp serve",), "external"),
        Box("docker", 70, 440, 500, 150, "Docker espressif/idf:v5.4",
            ("ESP-IDF build · Espressif QEMU", "qemu_boot.sh · qemu_ota.sh · run_ui_golden.sh", "ccache volume"),
            "container"),
    ]
    d.groups.append(Group("gh", 660, 100, 560, 700, "GitHub Actions — ubuntu-latest", "test"))
    d.boxes += [
        Box("cisim", 690, 150, 500, 130, "ci-sim-linux.yml",
            ("tests on Python 3.11 · 3.12 · 3.13", "linux-hal: gpio-sim · i2c-stub + lm75 · vkms", "wheel-smoke · lint · ui-golden"),
            "test"),
        Box("cifw", 690, 320, 500, 130, "firmware-qemu.yml",
            ("container espressif/idf:v5.4", "firmware-qemu · firmware-size · ota-rollback", "agent-firmware · uart-trace"),
            "test"),
        Box("cisec", 690, 490, 500, 110, "security.yml · release-pypi.yml",
            ("pip-audit · gitleaks · CodeQL · actionlint", "build · SBOM · attest · PyPI at I6"), "test"),
        Box("selfhost", 690, 640, 500, 120, "Self-hosted runner with a Box-3",
            ("nightly-hardware: memory-spike", "TSK-S4-05"), "test", "planned"),
    ]
    d.groups.append(Group("field", 1280, 100, 480, 700, "Devices", "device"))
    d.boxes += [
        Box("pi", 1310, 150, 420, 150, "Raspberry Pi 5 + I2S HAT",
            ("neuroedge --target linux", "libgpiod · hwmon · PipeWire AEC", "TSK-I2-01 · board not arrived"), "device",
            "planned"),
        Box("box3", 1310, 340, 420, 150, "ESP32-S3-BOX-3",
            ("firmware from build --target esp32s3", "UART to the host · OTA over Wi-Fi", "TSK-S4-12 · board not arrived"),
            "device", "planned"),
        Box("otasrv", 1310, 530, 420, 110, "OTA image server", ("any static HTTP(S) server",), "external"),
        Box("prov", 1310, 670, 420, 110, "Model and speech providers", ("HTTPS, keys from environment",), "external"),
    ]
    d.edges += [
        Edge("venv", "browser", "HTTP · SSE", via=((190, 285),), label_at=(190, 285)),
        Edge("desktop", "venv", "stdio", via=((450, 285),), label_at=(450, 285)),
        Edge("venv", "docker", "build/esp32s3", via=((620, 210), (620, 515)), label_at=(620, 440)),
        Edge("box3", "otasrv", "GET image", label_at=(1520, 510)),
        Edge("venv", "prov", "HTTPS", via=((630, 170), (630, 880), (1520, 880)), label_at=(1080, 880)),
    ]
    return d


# English names of the increments; status, progress and forecast are read from the roadmap (§0.2),
# its only home, so this poster can never drift from it.
INCREMENTS = {
    "I0": "Contract core on sim", "I1": "Internal preview on sim", "I2": "linux on par with sim",
    "I3": "Gate on a real Box-3", "I4": "Voice on the host", "I5": "Voice on Box-3", "I6": "Public release",
    "I7": "v1.0", "I8": "Developer Beta", "I9": "Providers v1.1 · Fleet OS", "I10": "Registry and rails",
    "I11": "Open the target list", "I12": "NeuroBrain", "I13": "Community port kit", "I14": "Tiered robotics",
    "I15": "Vision on linux", "I16": "Vision on jetson", "I17": "Multimodal", "I18": "Device ecosystem",
}
ROADMAP = ROOT / "neuroedge-roadmap.md"


def _roadmap_matrix() -> list[tuple[str, str, str, str]]:
    import re

    rows = []
    for line in ROADMAP.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|[^|]*\| \*\*(I\d+) — [^|]*\*\* \| ([^|]*)\|[^|]*\| \*\*(\d+ / \d+)\*\* \| (\S+)", line)
        if m:
            inc, forecast, progress, glyph = m.groups()
            forecast = forecast.strip().replace("✅ ", "")
            for vi, en in (("nhu cầu camera", "camera demand"), ("nhánh", "branch"), ("sau ", "after ")):
                forecast = forecast.replace(vi, en)
            rows.append((inc, forecast, progress.replace(" ", ""), glyph))
    got = [r[0] for r in rows]
    if got != list(INCREMENTS):
        raise SystemExit(f"neuroedge-roadmap.md §0.2 increments {got} differ from INCREMENTS — update the poster model")
    return rows


def e09_evolution() -> Diagram:
    d = Diagram(
        "E-09-evolution",
        "E-09 · Evolution I0–I18",
        "Status, progress and forecast are read from neuroedge-roadmap.md §0.2 when this poster is generated.",
        1800,
        1170,
    )
    status_of = {"✅": "done", "🟡": "partial", "⏳": "planned", "⏸": "planned", "🔴": "partial"}
    bands = [
        ("internal", "0.x internal — I0 to I5", ["I0", "I1", "I2", "I3", "I4", "I5"]),
        ("v1", "Public · v1.0 · Beta — I6 to I8", ["I6", "I7", "I8"]),
        ("v11", "v1.1 services — I9 · I10", ["I9", "I10"]),
        ("exp", "Expansion — I11 to I18", ["I11", "I12", "I13", "I14", "I15", "I16", "I17", "I18"]),
    ]
    rows = {r[0]: r for r in _roadmap_matrix()}
    y = 100
    for gid, label, incs in bands:
        per_row = 5
        lines = (len(incs) + per_row - 1) // per_row
        h = 40 + lines * 130
        d.groups.append(Group(gid, 40, y, 1720, h, label, "planned" if gid in ("v11", "exp") else "host"))
        for i, inc in enumerate(incs):
            r, c = divmod(i, per_row)
            w = 326
            x = 60 + c * (w + 12)
            _, forecast, progress, glyph = rows[inc]
            d.boxes.append(Box(inc, x, y + 36 + r * 130, w, 112, f"{inc} · {INCREMENTS[inc]}",
                               (f"{progress} tasks", f"forecast {forecast}"), "component", status_of.get(glyph, "planned")))
        y += h + 24
    return d


def e10_horizons() -> Diagram:
    d = Diagram(
        "E-10-target-horizons",
        "E-10 · Target architecture by horizon",
        "What each horizon adds on top of main. Details and sources: chapter 15; order and dates: roadmap §0.2.",
        1800,
        1060,
    )
    w, gap = 326, 12
    col = [60 + c * (w + gap) for c in range(5)]
    bands = [
        ("today", "Today on main — I0 done, I1–I4 in progress", "host", [
            ("core", "Host package neuroedge", ("SDK, CLI, gate engine, sim + linux HAL", "voice from WAV, MCP, Action CI"), "container", "done"),
            ("fw", "Firmware esp32s3 on QEMU", ("NETR walker, token ledger, UART trace", "signed A/B OTA · LVGL UI on host"), "device", "partial"),
            ("contracts", "Frozen contracts", ("gate.v1 · trace.v1 · board.v1", "NETR v1 · agent.toml"), "store", "done"),
            ("ci", "Evidence loop", ("record → replay → verify", "three canonical traces, 3 targets"), "test", "done"),
        ]),
        ("h1", "Horizon 1 — v1.0 on the device (I3–I7) · chapter 15 §2", "device", [
            ("hal", "HAL + drivers on chip", ("targets/esp32s3/hal/ · drivers/", "TSK-S4-01, TSK-S4-03"), "device", "planned"),
            ("voice", "Voice path on chip", ("AEC · VAD · Opus · voice FSM in C", "TSK-S5-01…S5-06"), "device", "planned"),
            ("fallback", "Local offline fallback", ("fixed command recognizer", "TSK-S5-07 · Q-14"), "device", "planned"),
            ("security", "Device security", ("Secure Boot · flash encryption", "mic switch · TSK-S6-05"), "device", "planned"),
            ("ui", "UI on the real display", ("ne_ui wired to the display driver", "TSK-S4-01"), "device", "planned"),
        ]),
        ("h2", "Horizon 2 — service tier v1.1 (I9–I10) · chapter 15 §3", "cloud", [
            ("fleet", "Fleet OS", ("provisioning · inventory · config sync", "canary OTA · incident traces · TSK-K2-04…09"), "external", "planned"),
            ("registry", "Gate Registry and rails", ("OCI store · identity · metering", "sandbox · manifest.v1 · TSK-K3-*"), "external", "planned"),
            ("provider", "Self-hosted provider layer", ("one endpoint · failover · quotas", "TSK-K2-01…03 · Q-28"), "container", "planned"),
            ("signed", "Signed gates on the device", ("verify signature before loading", "TSK-W2-04"), "gate", "planned"),
            ("boundary", "Core ↔ commercial boundary", ("safety never behind a paid tier", "proposal §6.4 · PRD P-3"), "note", "done"),
        ]),
        ("h3", "Horizon 3 — extensions after Beta (I11–I18) · chapter 15 §4", "planned", [
            ("tiers", "Target tiers + port kit", ("tier 1 · 2 · 3, compliance vectors", "I11 · I13 · Q-13 · RFC-0002"), "component", "planned"),
            ("brain", "NeuroBrain", ("brain/ only via dispatch() (B-1)", "envelope hook in HAL · I12 · RFC-0007"), "component", "planned"),
            ("robot", "Layered robot", ("Pi 5 brain + MCU nodes, gate per node", "black channel · lease tokens · I14"), "component", "planned"),
            ("vision", "Vision", ("L2 input reduced by a SystemOne", "never L3 authority · I15–I17"), "component", "planned"),
            ("eco", "Ecosystem", ("adapter + HAL-port store on Registry", "I18 · chapter 16"), "component", "planned"),
        ]),
    ]
    y = 100
    for gid, label, kind, items in bands:
        d.groups.append(Group(gid, 40, y, 1720, 200, label, kind))
        for c, (bid, title, lines, bkind, status) in enumerate(items):
            d.boxes.append(Box(bid, col[c], y + 44, w, 124, title, lines, bkind, status))
        y += 230
    d.edges += [
        Edge("fw", "voice", "same walker + ledger", label_at=(col[1] + w / 2, 312)),
        Edge("security", "signed", "verify on chip", label_at=(col[3] + w / 2, 542)),
        Edge("registry", "brain", "gates, lab actions", label_at=(col[1] + w / 2, 772)),
        Edge("boundary", "eco", "no paid safety", label_at=(col[4] + w / 2, 772)),
    ]
    return d


def e11_ecosystem() -> Diagram:
    d = Diagram(
        "E-11-ecosystem",
        "E-11 · Ecosystem landscape (C4 system landscape)",
        "Who takes part, what they share, and the platforms that carry it. Details and sources: chapter 16.",
        1820,
        1020,
    )
    d.groups.append(Group("parties", 40, 100, 380, 880, "Parties (PRD §2.1)", "boundary"))
    parties = [
        ("u1", "U1 · Maker", ("builds an agent, no account", "shares gates, agents"), "done"),
        ("u2", "U2 · Embedded team lead", ("tests safety in CI", "moves boards without rewrites"), "done"),
        ("u4", "U4 · Safety reviewer / QA", ("reads gates and traces", "approves behaviour"), "done"),
        ("u5", "U5 · OEM / ODM partner", ("declares a board, ports the HAL", "compliance vectors"), "partial"),
        ("u3", "U3 · Fleet operator", ("rolls out updates, pulls traces", "from v1.1"), "planned"),
        ("u6", "U6 · Robot integrator", ("Pi 5 brain + MCU nodes", "ROS 2 / Nav2 · I14"), "planned"),
    ]
    for i, (pid, title, lines, status) in enumerate(parties):
        d.boxes.append(Box(pid, 64, 140 + i * 138, 332, 110, title, lines, "person", status))
    d.groups.append(Group("core", 600, 100, 620, 400, "Source-available core and open standards", "host"))
    d.boxes.append(Box("ne", 630, 150, 560, 140, "NeuroEdge core",
                       ("SDK + CLI + firmware — PolyForm Noncommercial (Q-45)",
                        "commercial licence for companies",
                        "public repository since 2026-09-25"), "system"))
    d.boxes.append(Box("std", 630, 330, 560, 130, "Open standards — Apache-2.0",
                       ("schemas/ · docs/spec/ · fixtures/compliance/",
                        "changed only by RFC (CONTRIBUTING §3)"), "store"))
    d.groups.append(Group("assets", 600, 540, 620, 440, "Shared assets (chapter 16 §3)", "test"))
    assets = [
        ("adapters", "Provider adapters", ("python:pkg.mod:factory", "OpenAI-compatible first")),
        ("gates", "Gates", ("versioned YAML, neuroedge://", "inherit only to tighten")),
        ("ports", "HAL ports + board.toml", ("five primitives of v1", "proved by compliance vectors")),
        ("agents", "Agents and traces", ("agent.toml + actions + gates", "trace.v1 replays anywhere")),
    ]
    for i, (aid, title, lines) in enumerate(assets):
        r, c = divmod(i, 2)
        d.boxes.append(Box(aid, 630 + c * 290, 590 + r * 190, 270, 150, title, lines, "component"))
    d.groups.append(Group("platforms", 1400, 100, 380, 880, "Platforms (chapter 16 §4)", "cloud"))
    platforms = [
        ("repo", "Source repository", ("public · issues · RFCs",), "done"),
        ("pypi", "PyPI + public schema URLs", ("release workflow ready · I6",), "planned"),
        ("registry", "Gate Registry", ("OCI · identity · metering · I10",), "planned"),
        ("fleet", "Fleet OS", ("the one commercial service · I9",), "planned"),
        ("aura", "AURA vertical app", ("Khối 4 · outside the roadmap",), "planned"),
        ("market", "Marketplace", ("Khối 5 · only after G1–G4",), "planned"),
    ]
    for i, (pid, title, lines, status) in enumerate(platforms):
        d.boxes.append(Box(pid, 1424, 140 + i * 138, 332, 96, title, lines, "external", status))
    L, R = 510, 1310
    d.edges += [
        Edge("u1", "ne", "build · run · test", via=((L - 30, 195), (L - 30, 190)), label_at=(L - 30, 175)),
        Edge("u2", "ne", "CI · build · verify", via=((L, 333), (L, 250)), label_at=(L, 300)),
        Edge("u4", "gates", "review · explain", via=((L - 30, 471), (L - 30, 520), (1055, 520)), label_at=(L - 30, 500)),
        Edge("u5", "ports", "port + prove", via=((L, 609), (L, 850)), label_at=(L, 760)),
        Edge("u3", "fleet", "rollouts · traces", dashed=True, via=((560, 747), (560, 996), (1380, 996), (1380, 602)),
             label_at=(980, 996)),
        Edge("ne", "repo", "source · RFCs", via=((R, 220), (R, 188)), label_at=(R, 205)),
        Edge("std", "pypi", "schemas published", dashed=True, via=((R - 40, 395), (R - 40, 326)), label_at=(R - 40, 360)),
        Edge("gates", "registry", "share (planned)", dashed=True, via=((R, 665), (R, 464)), label_at=(R, 580)),
    ]
    return d


DIAGRAMS = [
    e01_context,
    e02_containers,
    e03_host,
    e04_firmware,
    e05_spine,
    e06_evidence,
    e07_targets,
    e08_deployment,
    e09_evolution,
    e10_horizons,
    e11_ecosystem,
]


def outputs() -> dict[Path, str]:
    files: dict[Path, str] = {}
    problems: list[str] = []
    for make in DIAGRAMS:
        d = make()
        problems += lint(d)
        files[ASSETS / "svg" / f"{d.id}.svg"] = render_svg(d)
        files[ASSETS / "excalidraw" / f"{d.id}.excalidraw"] = render_excalidraw(d)
    if problems:
        raise SystemExit("diagram lint failed:\n  " + "\n  ".join(problems))
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="không ghi; thoát 1 nếu tệp đã cũ")
    args = parser.parse_args()
    files = outputs()
    stale = [p for p, text in files.items() if not p.is_file() or p.read_text(encoding="utf-8") != text]
    if args.check:
        for p in stale:
            print(f"cũ: {p.relative_to(ROOT)}")
        return 1 if stale else 0
    for p in stale:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(files[p], encoding="utf-8")
        print(f"Đã ghi {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
