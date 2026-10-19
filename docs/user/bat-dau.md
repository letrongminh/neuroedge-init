# Start here

**NeuroEdge: the Physical AI that really does things, safely by design.**

This page is for newcomers: what the system consists of, what runs today, and what to read next.
It takes five minutes to read. Codes like `Q-72` or `TSK-I2d-25` in other documents are decision codes and task
codes; on first read they can be skipped.

## 1. The system in one picture

```text
  📱 You            🧠 Brain                  🛡️ NeuroEdge box              💡 Devices
  message   ──►  NeuroClaw: understands  ──►  holds rules: allow,       ──►  lights, doors, fans…
                 words, remembers,            ask you, or reject;
                 reminds schedule             records every decision
```

- **Brain (NeuroClaw)** talks to you via Telegram and other chat channels, calls AI, remembers tasks,
  reminds schedules. It does **not** touch devices directly: to turn on a light, it must request the box.
- **NeuroEdge box** holds the **rules** (called *gate*). For each command, the rule yields one of three outcomes: execute
  immediately; ask you first; or reject with a reason. Every decision is recorded and replayable.
- **Devices** are lights, doors, sensors. Today most are virtual devices on a computer; real boards
  have not yet arrived.

Why separate the brain from the box: AI can misunderstand or be tricked. If a chatbot speaks wrong, you click ask again; if a door
has opened by mistake, you cannot click undo. Therefore AI can only *request*, while rules on the box *decide*.

## 2. Two repositories

| Repo | What it is | Written in |
|:---|:---|:---|
| `neuroedge-init` (this repo) | Box: rules, device simulator, firmware for ESP32-S3 chip, server for the brain to call into | Python, C |
| [`letrongminh/neuroclaw`](https://github.com/letrongminh/neuroclaw) | Brain: chat, AI, memory, schedule; releases available for Linux, macOS, Windows, Pi, Android, Docker, and ESP32 chip | Go, C |

The brain can run on a separate machine (VPS, Pi, laptop), or share a single ESP32-S3 chip with the box.
A version hosted by NeuroEdge on the cloud is planned, not yet opened.

## 3. What runs today

| Running today | Not yet available |
|:---|:---|
| Rules on computer, with virtual lights, doors, sensors; viewable on web page | Real boards (awaiting shipment) |
| Same rules on Linux (emulated GPIO pins) and on emulated ESP32-S3 chip | Long-term verbal mission delegation ("trông bể cá giúp tôi" [watch the aquarium for me]) |
| Record and replay every decision | Product package to share or sell (called *Blueprint*) |
| Message Telegram to NeuroClaw to turn on lights, open doors (with ask/confirmation); ran in demo | Installer package for outsiders to self-build box + brain (in progress) |
| NeuroClaw for chip running on emulated chip | NeuroEdge Cloud |

This is not yet a certified safety product: rules do not replace emergency stop buttons or hardware interlocks.

## 4. What you want to do

| Goal | Read |
|:---|:---|
| Try rules on a laptop in a few minutes | [`python/README.md`](../../python/README.md), then [`huong-dan.md`](huong-dan.md) §6 |
| Message to control home using NeuroClaw | [`chat-voi-nha.md`](chat-voi-nha.md) |
| Flash onto ESP32-S3 chip | [`nap-firmware.md`](nap-firmware.md); brain and box on one chip: [`esp32-mot-chip.md`](esp32-mot-chip.md) |
| Understand architecture | [`00-overview.md`](../architecture/00-overview.md) |
| View progress | [`trang-thai.md`](trang-thai.md) |

## 5. Five terms to know

| Term | Meaning |
|:---|:---|
| **Gate** (rules) | Safety policy written in YAML; decides whether a command is allowed, must ask, or is rejected |
| **Trace** | Record of every decision; replayable for verification |
| **`sim`** | Device simulator on computer |
| **Brain** | Chat and AI component; the version used is NeuroClaw |
| **MCP** | How the brain (or Claude Desktop, or other agents) calls into the box to request actions |

All other terms and codes: [`thuat-ngu.md`](thuat-ngu.md).
