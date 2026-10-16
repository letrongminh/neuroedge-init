#!/usr/bin/env python3
"""Generate the architecture posters (docs/architecture/assets/) from a single description.

Each poster is a function below. From it the script generates **both** files:

* ``assets/excalidraw/<id>.excalidraw`` — openable and editable in Excalidraw;
* ``assets/svg/<id>.svg`` — the image the documents embed.

To change a poster, edit the function here and rerun the script; **never hand-edit** the two
generated files (if you edit in Excalidraw, copy the change back here). ``lint`` rejects
overlapping boxes, text overflowing its box, and arrows pointing at a box that does not exist.

    python3 scripts/gen_architecture_diagrams.py           # write the files
    python3 scripts/gen_architecture_diagrams.py --check   # write nothing; exit 1 if stale

CI runs --check (python/tests/test_architecture_diagrams.py). Labels inside the figures are
English (docs/architecture/README.md).
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
        1440,
    )
    # people (left column)
    d.groups.append(Group("people", 40, 100, 380, 1300, "People", "boundary"))
    people = [
        ("maker", "Maker / app developer", ("Writes agent.toml, gates, actions", "neuroedge new · run · test"), "done"),
        ("embedded", "Embedded / core engineer", ("Builds firmware, ports the HAL", "build --target esp32s3 · verify"),
         "done"),
        ("auditor", "Safety reviewer / QA", ("Reads gates and traces", "gate explain · trace view · replay"), "done"),
        ("oem", "OEM hardware partner", ("Declares a board, ports the HAL", "board.toml · compliance vectors"), "done"),
        ("operator", "Home owner", ("chats with NeuroClaw (demo)", "approves at home; phone · I2d"), "partial"),
        # Q-72: the people of rounds ② and ③
        ("installer", "Blueprint installer", ("Installs a NeuroEdge Blueprint,", "runs it, approves by chat · I2e"),
         "planned"),
        ("seller", "Blueprint seller / micro-OEM", ("Packs, shares and sells a Blueprint", "blueprint pack · I2e"),
         "planned"),
    ]
    for i, (pid, title, lines, status) in enumerate(people):
        d.boxes.append(Box(pid, 64, 140 + i * 150, 332, 118, title, lines, "person", status))
    # the system (middle)
    d.groups.append(Group("ne", 600, 230, 620, 760, "NeuroEdge system boundary", "host"))
    d.boxes.append(Box("neuroedge", 630, 280, 560, 180, "NeuroEdge",
                       ("Gated edge runtime: SDK + CLI (Python), firmware (C99)",
                        "Every command to a pin passes a typed, versioned gate",
                        "Every verdict goes into a replayable trace"), "system"))
    d.boxes.append(Box("device", 630, 540, 260, 130, "Device",
                       ("sim · linux · esp32s3", "virtual or real pins"), "device", "partial"))
    d.boxes.append(Box("files", 930, 540, 260, 130, "Project files",
                       ("agent.toml · gates/*.yaml", "board.toml · traces/*.json"), "store"))
    d.boxes.append(Box("agent", 630, 820, 560, 130, "Operating agent · Blueprint",
                       ("trusted runtime 24/7 + untrusted LLM worker · I2d (worker on cloud · I2f)",
                        "missions, detectors, chat approval records · I2d",
                        "blueprint pack / install, digest over the whole package · I2e"), "system", "planned"))
    # external systems (right column)
    d.groups.append(Group("ext", 1400, 100, 380, 1300, "External systems", "cloud"))
    ext = [
        ("llm", "LLM providers (System 2)", ("OpenAI-compatible via LiteLLM", "or a user adapter"), "done"),
        ("jev", "Jev on OpenRouter (System 1)", ("System One API, typed questions", "typesafe/jev-1.13"), "done"),
        ("speech", "Speech providers", ("STT / TTS, OpenAI audio API", "cloud or local server"), "done"),
        ("mcp", "MCP clients", ("NeuroClaw brain, Claude Desktop", "stdio, or HTTP with mTLS"), "done"),
        ("idf", "ESP-IDF v5.4 + QEMU", ("Toolchain and emulator", "Docker espressif/idf:v5.4"), "done"),
        ("fleet", "Home Assistant", ("devices of other brands", "remote actuators via plugin · I2c"), "partial"),
        ("chat", "Chat platforms", ("Telegram first · Slack · Zalo", "reports, commands, approvals · I2d"), "planned"),
        ("relay", "Relay (optional)", ("TLS pass-through by SNI, no decryption", "never on the safety path · Q-72"),
         "planned"),
        ("hub", "Blueprint Hub index", ("static index: URL + whole-package digest", "evidence unsigned · I2e"),
         "planned"),
        # Q-74 (conditional): the brain may live on an optional cloud; the safety spine stays at home
        ("cloud", "NeuroEdge Cloud (optional)", ("NeuroEdge brain per user, many homes", "no hardware rights · I2f · Q-74, Q-76"),
         "planned"),
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
        Edge("operator", "device", "chat · approvals (I2d)", dashed=True, via=((560, 799), (560, 640)), label_at=(480, 799)),
        Edge("neuroedge", "llm", "HTTPS · key from env", via=((R - 40, 300), (R - 40, 184)), label_at=(R - 40, 205)),
        Edge("neuroedge", "jev", "HTTPS", via=((R, 330), (R, 310)), label_at=(R, 330)),
        Edge("neuroedge", "speech", "HTTPS or localhost", via=((R - 40, 400), (R - 40, 436)), label_at=(R - 40, 418)),
        Edge("mcp", "neuroedge", "tools/call · stdio", via=((R, 562), (R, 440)), label_at=(R, 520)),
        Edge("neuroedge", "idf", "ESP-IDF project", via=((R - 60, 450), (R - 60, 686)), label_at=(R - 60, 610)),
        Edge("device", "fleet", "plugin (I2c)", via=((760, 720), (1340, 720), (1340, 814)),
             label_at=(1050, 720)),
        Edge("neuroedge", "device", "c.do() → gate → pin", via=((760, 460),), label_at=(760, 500)),
        Edge("neuroedge", "files", "reads · writes", via=((1060, 460),), label_at=(1060, 500)),
        # Q-72 (planned): chat, relay and the Hub index never sit on the safety path
        Edge("installer", "agent", "installs · approves", dashed=True),
        Edge("agent", "chat", "reports · approvals", dashed=True),
        Edge("agent", "relay", "outbound TLS tunnel", dashed=True, via=((1150, 1066),), label_at=(1290, 1066)),
        Edge("agent", "hub", "install: URL + digest", dashed=True, via=((1110, 1180),), label_at=(1260, 1180)),
        Edge("seller", "hub", "publishes (I2e)", dashed=True, via=((230, 1230), (1300, 1230)), label_at=(760, 1230)),
        Edge("agent", "cloud", "outbound · signed rules (I2f)", dashed=True, via=((910, 1310),), label_at=(1150, 1310)),
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
    # Q-72 (planned): the operating agent is two processes on the home machine (chapter 02 §3)
    d.boxes.append(Box("worker", B, 560, 340, 120, "NeuroEdge brain (untrusted)",
                       ("LLM worker, never approves", "self-host board · I2d, or cloud · I2f",
                        "talks to the runtime only via MCP · Q-76"), "container", "planned"))
    d.boxes.append(Box("runtime", C, 560, 300, 120, "Runtime 24/7 (systemd)",
                       ("HAL · gate · missions · scheduler", "chat adapter + approval check · egress",
                        "the only HAL holder · I2d"), "container", "planned"))
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
    d.boxes.append(Box("q72", 1510, 570, 420, 135, "Chat · relay · Hub · cloud",
                       ("Telegram first, Slack, Zalo · I2d", "relay (optional): TLS pass-through · Q-72",
                        "Blueprint Hub index: URL + digest · I2e", "NeuroEdge Cloud (optional) · I2f"), "external", "planned"))
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
        Edge("build", "fw", "idf.py build · flash", via=((1380, 440), (1380, 735), (730, 735)),
             label_at=(1000, 735)),
        Edge("fw", "cli", "UART NE1 lines → record · verify", via=((20, 905), (20, 215)), label_at=(290, 905)),
        Edge("fw", "flash", "trees read in place", label_at=(980, 905)),
        Edge("fw", "ota", "HTTP(S) GET image", via=((700, 1080), (1720, 1080)), label_at=(1180, 1080)),
        Edge("worker", "runtime", "local MCP", dashed=True),
        Edge("runtime", "q72", "outbound only", dashed=True, label_at=(1440, 610)),
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
            ("GPIO · I2C sensors · LCD", "TSK-S4-01 · I3"), "device", "planned"),
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
            ("I2S + AEC on the chip", ("dropped from v1.0 · Q-77",), "planned")]),
        ("audio.out", [
            ("TTS → speaker timeline → WAV", ("every PR, fake providers",), "done"),
            ("WAV file backend · live PipeWire", ("file every PR · live not on hardware",), "partial"),
            ("I2S codec", ("dropped from v1.0 · Q-77",), "planned")]),
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
        "Where each part runs today, once the boards arrive, and in the two deployment profiles of Q-83: Full (home machine, cloud) and One chip.",
        1800,
        1840,
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
            ("pip-audit · gitleaks · CodeQL · actionlint", "build · SBOM · attest · PyPI at I6"), "test", "partial"),
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
    # Q-72 (planned): the operating agent runs 24/7 on a machine at home; chat, relay and the Hub index
    # are outside services that never sit on the safety path (chapter 02 §6)
    d.groups.append(Group("home", 40, 920, 1180, 260,
                          "Profile A — Pi 5 / mini PC / NAS · Q-72 · Q-83", "planned"))
    d.boxes += [
        Box("worker", 70, 970, 520, 150, "NeuroClaw brain — own OS user",
            ("chat · LLM · memory · BYOK key only here", "never approves · no device groups",
             "MCP + mTLS to the runtime · I2d"), "container", "partial"),
        Box("runtime", 690, 970, 500, 170, "Runtime 24/7 — systemd service",
            ("HAL · gate · missions · detectors · scheduler", "chat adapter (bot token) · approval records",
             "egress only to declared destinations · I2d", "trace segments kept 30 days · I2d"),
            "container", "planned"),
    ]
    d.groups.append(Group("cloudq", 1280, 920, 480, 410, "Outside services — planned · Q-72", "planned"))
    d.boxes += [
        Box("chat", 1310, 960, 420, 100, "Telegram cloud (chat)", ("bot API, reached outbound · I2d",), "external",
            "planned"),
        Box("relay", 1310, 1080, 420, 100, "Relay (optional)", ("TLS pass-through by SNI, no decryption · Q-72",),
            "external", "planned"),
        Box("hub", 1310, 1200, 420, 100, "Blueprint Hub index", ("static git / HTTPS · URL + digest · I2e",),
            "external", "planned"),
    ]
    d.edges += [
        Edge("worker", "runtime", "local MCP", dashed=True, label_at=(640, 1045)),
        Edge("worker", "prov", "HTTPS · allowlisted", dashed=True, via=((540, 850), (1250, 850), (1250, 725)),
             label_at=(900, 850)),
        Edge("runtime", "chat", "bot API", dashed=True, label_at=(1250, 1015)),
        Edge("runtime", "relay", "TLS tunnel", dashed=True, label_at=(1250, 1110)),
        Edge("runtime", "hub", "install · digest", dashed=True, via=((1100, 1250),), label_at=(1200, 1250)),
    ]
    # Q-74 (conditional, I2f): the brain may move to an optional cloud; the spine stays at home, and a
    # small home box can be one ESP32-S3 for a single job
    d.groups.append(Group("q74", 40, 1370, 1720, 210,
                          "Optional cloud brain and small home box — conditional · Q-74 · I2f", "planned"))
    d.boxes += [
        Box("ncloud", 70, 1410, 520, 140, "NeuroEdge Cloud (optional)",
            ("one isolated brain instance per user", "many devices, homes and people", "no hardware rights · I2f · Q-76"),
            "external", "planned"),
        Box("espbox", 1240, 1410, 490, 140, "Small home box — ESP32-S3",
            ("ne_gate · token ledger · reflexes", "signed rules from the cloud", "approval checked on chip · I2f"),
            "device", "planned"),
    ]
    d.edges += [
        Edge("ncloud", "runtime", "outbound tunnel · signed rules", dashed=True, via=((940, 1480),),
             label_at=(820, 1480)),
        Edge("ncloud", "espbox", "outbound · signed rules", dashed=True, via=((910, 1530), (1200, 1530)),
             label_at=(1060, 1530)),
    ]
    # Q-83: Profile B — brain and gate in one ESP32-S3 image; the same contract through nc_gate calls
    d.groups.append(Group("profb", 40, 1620, 1720, 180,
                          "Profile B — one chip, risk=single_chip · Q-79 · Q-83 · I2f", "planned"))
    d.boxes += [
        Box("onechip", 70, 1660, 820, 110, "ESP32-S3 — one image",
            ("NeuroClaw-ESP ─ nc_gate ─ ne_brain_bridge ─ ne_gate ─ token ─ pins",
             "approve: board button or owner callback · I2f"), "device", "planned"),
        Box("onechipcfg", 940, 1660, 790, 110, "Built and kept by the box",
            ("neuroedge build --target esp32s3 --brain neuroclaw",
             "pinned NeuroClaw-ESP · signed OTA of the whole image · I2f"), "container", "planned"),
    ]
    return d


# English names of the increments; status, progress and forecast are read from the roadmap (§0.2),
# its only home, so this poster can never drift from it.
INCREMENTS = {
    "I0": "Contract core on sim", "I1": "Internal preview on sim", "I2": "linux on par with sim",
    "I2a": "Primitives: sim, linux", "I2b": "Kits and quick build", "I2c": "Open platform: plug-in SDK",
    "I2d": "Missions and operating agent", "I2e": "NeuroEdge Blueprint MVP",
    "I2f": "Cloud brain · one-chip profile",
    "I3": "Gate on a real Box-3",
    "I3a": "New primitives on esp32s3", "I6": "Public release", "I7": "v1.0 = MVP",
    "I8": "Developer Beta",
}
ROADMAP = ROOT / "roadmap" / "neuroedge-roadmap.md"


def _roadmap_matrix() -> list[tuple[str, str, str, str]]:
    import re

    rows = []
    for line in ROADMAP.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|[^|]*\| \*\*(I\d+[a-z]?) — [^|]*\*\* \| ([^|]*)\|[^|]*\| \*\*(\d+ / \d+)\*\* \| (\S+)", line)
        if m:
            inc, forecast, progress, glyph = m.groups()
            forecast = forecast.strip().replace("✅ ", "")
            rows.append((inc, forecast, progress.replace(" ", ""), glyph))
    got = [r[0] for r in rows]
    if got != list(INCREMENTS):
        raise SystemExit(f"neuroedge-roadmap.md §0.2 increments {got} differ from INCREMENTS — update the poster model")
    return rows


# English names of the eight user-facing release milestones (roadmap §0.5, "User-facing release
# milestones"). Which increments belong to which milestone is read from that table, never repeated here.
MILESTONES = {
    1: "Try it on a laptop", 2: "Real devices on a Raspberry Pi", 3: "The gate on a $5 chip",
    4: "Build and run by chat, share a Blueprint", 5: "Public launch: first outside users",
    6: "v1.0: ready to ship in products", 7: "Developer Beta", 8: "One chat for many devices and homes",
}


def _milestones() -> list[tuple[int, list[str]]]:
    import re

    lines = ROADMAP.read_text(encoding="utf-8").splitlines()
    start = next(n for n, line in enumerate(lines) if line.startswith("#### User-facing release milestones"))
    out = []
    for line in lines[start + 1 :]:
        if line.startswith(("#", "---")):
            break
        m = re.match(r"^\| (\d+) \|(?:[^|]*\|){3}([^|]*)\|", line)
        if m:
            out.append((int(m.group(1)), [x.strip() for x in m.group(2).split(",")]))
    if [n for n, _ in out] != list(MILESTONES):
        raise SystemExit("roadmap §0.5 milestones differ from MILESTONES — update the poster model")
    return out


def e09_evolution() -> Diagram:
    d = Diagram(
        "E-09-evolution",
        "E-09 · Evolution by release milestone",
        "Eight things a user can do, in order. Status, progress and forecast are read from roadmap §0.2.",
        1800,
        1340,
    )
    status_of = {"✅": "done", "🟡": "partial", "⏳": "planned", "⏸": "planned", "🔴": "partial"}
    rows = {r[0]: r for r in _roadmap_matrix()}
    groups = _milestones()
    if sorted(i for _, incs in groups for i in incs) != sorted(rows):
        raise SystemExit("roadmap §0.5 milestones do not cover every increment exactly once")
    w, gap, per_row, col_w = 262, 12, 3, 840
    cols = {1: 40, 2: 920}
    y_at = {1: 100, 2: 100}
    for n, incs in groups:
        col = 1 if n <= 5 else 2
        lines = (len(incs) + per_row - 1) // per_row
        h = 44 + lines * 140
        x0, y0 = cols[col], y_at[col]
        kind = "host" if n <= 7 else "planned"
        d.groups.append(Group(f"m{n}", x0, y0, col_w, h, f"{n} · {MILESTONES[n]}", kind))
        for k, inc in enumerate(incs):
            r, c = divmod(k, per_row)
            _, forecast, progress, glyph = rows[inc]
            d.boxes.append(Box(inc, x0 + 20 + c * (w + gap), y0 + 38 + r * 140, w, 122, inc,
                               (INCREMENTS[inc], f"{progress} tasks", forecast), "component",
                               status_of.get(glyph, "planned")))
        y_at[col] += h + 22
    d.height = int(max(y_at.values())) + 70  # a milestone that gains a row of increments grows the poster
    return d


def e10_horizons() -> Diagram:
    d = Diagram(
        "E-10-target-horizons",
        "E-10 · Target architecture by horizon",
        "What v1.0 and the Q-72 → Q-83 bands add on top of main; horizons 2 and 3 left the roadmap (Q-77). Chapter 15; dates: roadmap §0.2.",
        1800,
        1360,
    )
    w, gap = 326, 12
    col = [60 + c * (w + gap) for c in range(5)]
    bands = [
        ("today", "Today on main — I0 done, I1–I3 in progress", "host", [
            ("core", "Host package neuroedge", ("SDK, CLI, gate engine, sim + linux HAL", "voice from WAV, MCP, Action CI"), "container", "done"),
            ("fw", "Firmware esp32s3 on QEMU", ("NETR walker, token ledger, UART trace", "signed A/B OTA · LVGL UI on host"), "device", "partial"),
            ("contracts", "Frozen contracts", ("gate.v1 · trace.v1 · board.v1", "NETR v1 · agent.toml"), "store", "done"),
            ("ci", "Evidence loop", ("record → replay → verify", "three canonical traces, 3 targets"), "test", "done"),
        ]),
        ("h1", "Horizon 1 — v1.0 = MVP (I2a–I7) · chapter 15 §2", "device", [
            ("hal", "HAL + drivers + UI on chip", ("targets/esp32s3/hal/ · drivers/ · ne_ui", "TSK-S4-01, TSK-S4-03"), "device", "planned"),
            ("link", "Pi ↔ ESP32 link", ("heartbeat · safe_state on link loss", "generic ESP32-S3 + Arduino · I3a · Q-75"), "device", "planned"),
            ("ext", "Extension primitives", ("digital.in · I2C · analog.in · PWM", "vision.in · motion.* · I2a, I3a · Q-53"), "device", "planned"),
            ("authoring", "Mission authoring over MCP", ("propose_mission · mission_status", "any MCP client · TSK-I2d-23 · Q-88"), "component", "planned"),
            ("security", "Device security", ("Secure Boot · flash encryption", "mic switch · TSK-S6-05"), "device", "planned"),
            # I2c — the open platform (Q-67) sits in the MVP host lane, before I6
            ("sdk", "Standalone core + Extension SDK", ("neuroedge.guard · neuroedge.sdk", "six plug-in kinds · RFC-0016 · I2c"), "component", "planned"),
            ("proxies", "Proxies + remote actuators", ("proxy mcp · proxy http · plugin doctor", "Home Assistant first · RFC-0018 · I2c"), "component", "planned"),
            ("tiers", "Kits + starter gates", ("five kits · neuroedge add", "BOM and wiring · I2b"), "component", "partial"),
            ("index", "Community plug-in index", ("plugin search/install · NeuroEdge-gated", "not a Marketplace · FR-EXT-08 · I2c"), "external", "planned"),
        ]),
        # Q-72 reorders the work: this band comes before the rest of Horizon 1 (roadmap §0.2)
        ("q72", "Q-72 band — run and share, moved ahead of the v1.0 work (I2d, I2e) · chapter 15 §6", "planned", [
            ("mission", "Mission contracts", ("YAML, locked by an approved digest", "skill tier on the box in v1 · Q-87"), "component", "planned"),
            ("agent", "Operating agent", ("runtime 24/7 + NeuroClaw brain", "detectors first · wake cap · Q-83, Q-87"), "container", "planned"),
            ("chat", "Chat + approval records", ("Telegram first · paired sender only", "id · nonce · expiry · digest · I2d"), "external", "planned"),
            ("blueprint", "NeuroEdge Blueprint + Hub", ("blueprint.toml · digest of manifest + files", "nothing runs before consent · I2e · Q-86"), "component", "planned"),
            ("emul", "Emulation first, G1–G4", ("sim physics · gpio-sim (G1, G2) · I2d", "Wokwi / QEMU (G3) · ESPHome host (G4)"), "test", "planned"),
            ("safe", "Symmetric safe_state", ("default off · on needs an interlock", "sim: risk=simulated_interlock · Q-87"), "gate", "planned"),
            ("egress", "Anti-leak data flow", ("only declared destinations", "worker network allowlisted · I2d"), "gate", "planned"),
            ("segments", "Trace segments", ("chain of replayable segments", "kept 30 days · RFC planned · I2d"), "store", "planned"),
            ("relay", "Relay (optional)", ("TLS pass-through by SNI", "never on the safety path · Q-72"), "external", "planned"),
        ]),
        # Q-73 (open verification, I2d) and Q-74 (optional cloud brain, conditional I2f) · chapter 15 §6.10
        ("q74", "Q-73 / Q-74 / Q-83 — deployment profiles, open verification, one chat for many devices (I2d, I2f) · chapter 15 §6.10", "planned", [
            ("profiles", "Deployment profiles A / B", ("A: brain + box, MCP over mTLS", "B: one ESP32-S3 image · Q-83"), "container", "planned"),
            ("verify", "User-declared verification", ("spoken code · face · phone biometrics", "risk label, never AI-answered · I2d"), "gate", "planned"),
            ("ncloud", "NeuroEdge Cloud (optional)", ("profile A brain, one per user", "after the demand gate · I2f · Q-85"), "external", "planned"),
            ("homebox", "Home box: Pi / HA add-on / ESP32", ("the spine stays at home", "easy install I2e · ESP32 I2f"), "device", "planned"),
            ("network", "Multi-node, multi-home network", ("signed rules per node, scope caps", "self-lock on anomaly · I2f"), "component", "planned"),
            ("roles", "People with roles", ("who commands, who approves", "time-boxed guests · I2f"), "person", "planned"),
        ]),
    ]
    y, row_pitch, tops = 100, 140, {}
    for gid, label, kind, items in bands:
        rows = (len(items) + 4) // 5  # five boxes to a row; Horizon 1, Q-72 and Q-73/Q-74 need a second row
        gh = 200 + (rows - 1) * row_pitch
        d.groups.append(Group(gid, 40, y, 1720, gh, label, kind))
        for n, (bid, title, lines, bkind, status) in enumerate(items):
            r, c = divmod(n, 5)
            d.boxes.append(Box(bid, col[c], y + 44 + r * row_pitch, w, 124, title, lines, bkind, status))
        tops[gid] = y
        y += gh + 30
    d.height = y + 40  # a band that gains a row grows the poster
    d.edges += [
        Edge("fw", "link", "same walker + ledger", label_at=(col[1] + w / 2, 312)),
    ]
    return d


def e11_ecosystem() -> Diagram:
    d = Diagram(
        "E-11-ecosystem",
        "E-11 · Ecosystem landscape (C4 system landscape)",
        "Who takes part, what they share, and the platforms that carry it. Details and sources: chapter 16.",
        1820,
        1600,
    )
    d.groups.append(Group("parties", 40, 100, 380, 1210, "Parties (PRD §2.1)", "boundary"))
    parties = [
        ("u1", "U1 · Maker", ("builds an agent, no account", "shares gates, agents"), "done"),
        ("u2", "U2 · Embedded team lead", ("tests safety in CI", "moves boards without rewrites"), "done"),
        ("u4", "U4 · Safety reviewer / QA", ("reads gates and traces", "approves behaviour"), "done"),
        ("u5", "U5 · OEM / ODM partner", ("declares a board, ports the HAL", "compliance vectors"), "partial"),
        ("u3", "U3 · Fleet operator", ("fleet tools dropped from the roadmap", "reopen on demand · Q-77"), "planned"),
        ("u6", "U8 · Home owner", ("chats with the brain", "approves from the phone · I2d"), "planned"),
        ("u7", "U7 · Plug-in author", ("wires a product in, own repo and licence", "passes the conformance suite · I2c"), "planned"),
    ]
    for i, (pid, title, lines, status) in enumerate(parties):
        d.boxes.append(Box(pid, 64, 140 + i * 118, 332, 104, title, lines, "person", status))
    # Q-72 (planned): the people of round ③, below the bottom routes of U3 and U7
    d.boxes += [
        Box("seller", 64, 1060, 332, 104, "Blueprint seller / micro-OEM",
            ("packs and sells a NeuroEdge Blueprint", "kit + firmware + mission · I2e"), "person", "planned"),
        Box("installer", 64, 1182, 332, 104, "Blueprint installer",
            ("installs a Blueprint by URL + digest", "runs it on emulation first · I2e"), "person", "planned"),
    ]
    d.groups.append(Group("core", 600, 100, 620, 400, "Source-available core and open standards", "host"))
    d.boxes.append(Box("ne", 630, 150, 560, 140, "NeuroEdge core",
                       ("SDK + CLI + firmware — PolyForm Noncommercial (Q-45)",
                        "commercial licence for companies",
                        "public repository since 2026-09-25"), "system"))
    d.boxes.append(Box("std", 630, 330, 560, 130, "Open standards — Apache-2.0",
                       ("schemas/ · docs/spec/ · fixtures/compliance/ · compliance corpus (Q-67)",
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
    d.groups.append(Group("bpg", 600, 1030, 620, 190, "Shared asset — planned · Q-72", "planned"))
    d.boxes.append(Box("blueprint", 630, 1060, 560, 130, "NeuroEdge Blueprint",
                       ("kit + firmware + mission template + detectors", "evidence trace, unsigned before MVP · I2e"),
                       "component", "planned"))
    d.groups.append(Group("platforms", 1400, 100, 380, 1460, "Platforms (chapter 16 §4)", "cloud"))
    platforms = [
        ("repo", "Source repository", ("public · issues · RFCs",), "done"),
        ("pypi", "PyPI + public schema URLs", ("release workflow ready · I6",), "planned"),
        ("registry", "Home Assistant", ("devices of other brands · I2c",), "partial"),
        ("fleet", "NeuroClaw · MCP clients", ("brain: Go (A) · ESP32 (B) · Q-83",), "partial"),
        ("index", "Community plug-in index", ("search/install · not a Marketplace · I2c",), "planned"),
        ("aura", "Claw-family agents", ("ESP-Claw · zclaw · MimiClaw",), "planned"),
        ("market", "Blueprint Hub (paid)", ("after the 8-week gate · Q-72",), "planned"),
        ("chat", "Chat platforms", ("Telegram first · Slack · Zalo · I2d",), "planned"),
        ("hub", "Blueprint Hub index", ("static index · revenue share later · I2e",), "planned"),
        ("relay", "Relay (optional)", ("TLS pass-through · paid option · Q-72",), "planned"),
        ("kits", "Kit suppliers", ("BOM links · kit commission · Q-72",), "planned"),
        ("ncloud", "NeuroEdge Cloud (optional)", ("subscription, after the gate · I2f",), "planned"),
    ]
    for i, (pid, title, lines, status) in enumerate(platforms):
        d.boxes.append(Box(pid, 1424, 140 + i * 118, 332, 96, title, lines, "external", status))
    L, R = 510, 1310
    d.edges += [
        Edge("u1", "ne", "build · run · test", via=((L - 30, 192),), label_at=(L - 30, 175)),
        Edge("u2", "ne", "CI · build · verify", via=((L, 310), (L, 250)), label_at=(L, 290)),
        Edge("u4", "gates", "review · explain", via=((L - 30, 428), (L - 30, 520), (1055, 520)), label_at=(L - 30, 500)),
        Edge("u5", "ports", "port + prove", via=((L, 546), (L, 850)), label_at=(L, 760)),
        # round the bottom, then up the gap left of the platforms: no crossing of Fleet OS's own arrow
        Edge("u7", "index", "publish plug-ins", dashed=True,
             via=((540, 900), (540, 1016), (1392, 1016), (1392, 660)), label_at=(1150, 1016)),
        Edge("ne", "repo", "source · RFCs", via=((R, 220), (R, 188)), label_at=(R, 205)),
        Edge("std", "pypi", "schemas published", dashed=True, via=((R - 40, 395), (R - 40, 306)), label_at=(R - 40, 360)),
        Edge("gates", "registry", "guard its devices", via=((R, 665), (R, 424)), label_at=(R, 580)),
        # Q-72 (planned): the Blueprint flywheel — build, run, share, install
        Edge("seller", "blueprint", "packs · sells", dashed=True),
        Edge("installer", "blueprint", "installs", dashed=True, via=((500, 1234), (500, 1170)), label_at=(460, 1234)),
        Edge("blueprint", "hub", "listed: URL + digest", dashed=True),
        Edge("blueprint", "kits", "BOM links", dashed=True, via=((1100, 1368),), label_at=(1260, 1368)),
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
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 if a file is stale")
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
        print(f"Wrote {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
