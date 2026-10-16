# User guide — what NeuroEdge does and how to test it

This document is for people who want to **use** NeuroEdge: makers, embedded developers, product creators.
It answers five questions, in this exact order:

1. What NeuroEdge is (§1).
2. Where it runs, and readiness levels of each environment (§2).
3. How to install (§3).
4. What each capability group does, requirements, and current limitations (§4–§5).
5. Step-by-step walkthroughs to test hands-on (§6).

For troubleshooting, see §7.

This document describes **capabilities**, without repeating full syntax for every command. Syntax, all options, and
expected outputs reside in a single place: [`CHANGELOG.md`](../../CHANGELOG.md) §2.3. Task-by-task
progress is in [`trang-thai.md`](trang-thai.md). If you encounter an unfamiliar abbreviation (`FR-*`, `Q-N`, `TSK-*`, `I3`…),
look it up in [`thuat-ngu.md`](thuat-ngu.md).

---

## 1. What NeuroEdge is

When a chatbot gives a wrong answer, the user clicks "regenerate". When an agent controlling physical devices makes a mistake,
the door latch has already opened, the fan has already stopped, and there is no "regenerate" button. NeuroEdge addresses precisely that point.

**Gate.** Every action to hardware must pass through a *gate*: a safety policy written in YAML, named,
versioned, and inheritable from other gates. The gate reads current facts (is the guest in the correct room,
how hot is the machine room, who is issuing the command) and yields one of three verdicts:

| Verdict | Meaning | Example |
|:---|:---|:---|
| **ALLOW** | Allowed; GPIO pin is controlled | Guest in room 101 opens room 101 |
| **BLOCK** with **confirmation** | Not yet allowed; ask present person for confirmation first | Turn off fan when machine room is hot |
| **BLOCK** | Rejected; can escalate to human (front desk) | Guest in room 101 requests opening room 202 |

**Brain: NeuroClaw.** You message the NeuroClaw brain via Telegram (separate repo `letrongminh/neuroclaw`); it calls AI, remembers, reminds schedules, and requests the NeuroEdge box to take action via MCP. Connection guide: [`chat-voi-nha.md`](chat-voi-nha.md). Newcomers: [`bat-dau.md`](bat-dau.md).

**Invocations are merely requests.** An LLM, an external agent via MCP, or a spoken phrase can only *request* an action;
the gate is where decisions happen. In code, GPIO pins can only move inside `c.do()` when a valid
verdict is present, and that verdict is single-use.

**Fail-closed.** When a gate cannot be evaluated — error, timeout, network loss, missing facts —
the outcome is BLOCK, never ALLOW.

**Trace.** Every verdict is recorded into a *trace* following a fixed schema. Traces are replayable:
NeuroEdge recalculates each verdict from recorded facts and compares against the original run, without touching
hardware or invoking any models.

**One gate, three environments.** The same gate file runs on the simulator (`sim`), on Linux machines
(`linux`, e.g. Raspberry Pi 5), and on ESP32-S3 chips (`esp32s3`, ESP32-S3-BOX-3 board), without branching
logic per environment.

**Direction: three flywheels — proposed, no code yet.** Starting from Q-72 (PRD §15), NeuroEdge aims to be the place to turn intent
into AI physical products. Everything in the table below **is not yet runnable** today; the remainder of this
document describes only what currently exists. Progress: [`trang-thai.md`](trang-thai.md) (increments I2d, I2e).

| Flywheel | What user does | Grounded in existing work |
|:---|:---|:---|
| ① **Build** | Tell Claude (or another MCP client) "tôi muốn trông bể cá" ("I want to monitor the aquarium"); receive kit suggestion, generate firmware, test in `sim` before buying, flash, connect chat channel | Gate, `sim`, sample kits; NeuroEdge Lab flywheel ① (I2d, not yet available) |
| ② **Run** | Delegate a *mission contract* verbally; *operator agent* runs continuously on home machine, local reflexes, proactive trend alerts and proposals via Telegram; human approves directly in chat | Gate, envelopes, traces; user's LLM (BYOK) |
| ③ **Share, sell** | Package into a **NeuroEdge Blueprint** (kit, firmware, contract templates, detectors, traces as evidence); others install with one command | `digests.lock`, traces, and `replay` |

Terminology (operator agent, mission contract, Blueprint…): [`thuat-ngu.md`](thuat-ngu.md) §4. Full proposal:
[`proposal-blueprint-2026-10-11.md`](../business/proposal-blueprint-2026-10-11.md).

> **NeuroEdge is not a certified safety function** — it has no SIL (IEC 61508) or PL
> (ISO 13849) ratings, the two functional safety certification standards. The gate does not replace
> emergency stop buttons or hardware interlocks. The product is in internal development, not yet
> released externally.

---

## 2. Where it runs, readiness levels

The table below provides the overall picture. Details for each cell are in §4 and §5.

| Environment | What it is | Running today | Not yet available |
|:---|:---|:---|:---|
| **`sim`** — simulator | Virtual devices on your computer: virtual door locks, lights, fans, sensors, display, mic, and speaker | **Complete**: gates, CLI commands, web monitor, traces, voice from WAV files, real AI models, MCP | — |
| **`linux`** — Linux machine | Kernel real GPIO lines, hwmon/IIO sensors, framebuffer, mic/speaker via PipeWire | CLI commands, voice from WAV files, MCP, sensor reads, display rendering — **verified on virtual hardware** (gpio-sim, `i2c-stub` + `lm75`, `vkms`) in CI | Not yet run on real Raspberry Pi 5 (boards awaiting shipment); real mic and speaker unverified on hardware; no web monitor |
| **`esp32s3`** — chip | ESP-IDF firmware for ESP32-S3-BOX-3 | Agent gates run and self-check at boot, traces via UART, verdict comparison with host, signed OTA updates — **verified on QEMU** (Espressif virtual machine) | No board in hand; no GPIO pins move yet; no audio, no real Wi-Fi, no real display |
| **NeuroClaw brain** — chat | Separate repo `letrongminh/neuroclaw`: chat, AI, memory, schedules; calls into box via MCP | Message Telegram to turn on lights, open door with owner confirmation — **ran in demo** (laptop, VM acting as cloud); on-chip version runs on QEMU | Distribution package for outsiders; NeuroEdge Cloud |

No real boards are yet in team hands: Box-3 and Raspberry Pi 5 are awaiting delivery (progress in
[`trang-thai.md`](trang-thai.md)). Items marked "verified on virtual hardware" or "on QEMU" mean that
logic has been proven, while electrical aspects (real pins, real audio, real network) remain unverified.

---

## 3. Installation

**No external release available yet.** PyPI opens at increment I6 (public release). Today there are two paths:

- From source, following [`python/README.md`](../../python/README.md): create a venv in `python/` and run
  `pip install -e '.[dev]'`. The `neuroedge` executable is located at `python/.venv/bin/`.
- From an internal wheel for an increment, when provided by the team.

Requirements: **Python 3.11 or higher**. The base installation runs all of `sim` without network or keys.
Capabilities requiring additional libraries are split into extras, installed as needed:

| Extension | Purpose | Section |
|:---|:---|:---|
| `neuroedge[mcp]` | MCP server, Claude Desktop, external MCP servers for System 2 | §4.6, §4.4 |
| `neuroedge[cloud]` | Real LLMs for System 2 (LiteLLM) | §4.4 |
| `neuroedge[linux]` | Real GPIO pins on Linux (libgpiod) | §5.1 |
| `neuroedge[audio]` | Real microphone and speaker on Linux (sounddevice) — voice was removed from the roadmap (Q-77, roadmap §6); the host code still ships | §5.1 |
| `neuroedge[wake]` | Wake-word via openWakeWord (your model) | §4.5 |
| `neuroedge[serial]` | Read traces over board serial port | §5.2 |

Example: `pip install -e '.[mcp,cloud]'`.

---

## 4. Core capabilities — hardware-free

All capabilities here run on `sim`, meaning on your computer; capabilities that also run on `linux`
or `esp32s3` are noted explicitly. Each section covers: what it does · requirements · limitations. Sections requiring additional extras note
the extra name (`neuroedge[mcp]`…); list of extras is in §3.

### 4.0 NeuroEdge Studio: all capabilities on one page

> Studio is paused (Q-72, TSK-I1-04); the command still works.

`neuroedge studio` launches a local web application (`127.0.0.1` only, no network required) with seven screens: live session (typing,
and speaking via microphone with `--mic`), gates and quick scratchpad, traces and replay, verification (`verify`), ESP32-S3 device
(screen screenshots, QEMU, OTA), MCP, and agent configuration. Bilingual Vietnamese/English. Contract: `docs/spec/studio.md`;
demo scenario: `demo/i1-studio/`.

### 4.1 Writing and linting gates

**Capabilities**

- Write gates in YAML following frozen schemas; child gates **inherit** parent gates and may only **narrow**,
  never loosen. Loosening is an error, rejected during linting.
- Lint entire gate directories for resolvability (`neuroedge gate lint`). This check determines whether
  a gate is safe — schema validation alone is **insufficient**.
- Inspect effective policy after merging inheritance chain (`gate resolve`), and read gates in human language for
  reviewers: which tier criteria originate from, which clauses were narrowed, time budgets (`gate explain`).
- Print SHA-256 digest of gate to pin versions (`gate publish`), and preview what inheriting a repository gate
  imposes (`gate add`).
- Gates validate command **arguments**: for example door hold-open duration must not exceed 30 seconds
  (`fixtures/gates/valid/narrows_arguments.yaml`); exceeding limits blocks before command execution.
- Gates can **ask confirmation** from present persons before allowing (declared via `confirms`): if that person answers "có" ("yes"),
  the gate re-evaluates; models or other agents cannot answer on their behalf.
- Gates have **time budgets**: failing to evaluate within deadline triggers a block.
- A **starter gate library** is provided in `gates/home/` to `extends` rather than writing from scratch: `door-lock`,
  `light`, `valve` (water/gas valve), `siren`, `hvac` (air conditioning), `camera` (recording, based on
  vision facts), and `motor` (motor `motion.motor`). All gates fail closed (`fail: closed`) with
  conservative safety thresholds; physical measurements represent voltage (V) of an `analog.in` channel (pressure, temperature, motor current), conversion scales
  documented in the header of each gate; child gates can only narrow, loosening thresholds, reading validity, or budgets is
  rejected by `gate lint` (counterexamples: `fixtures/gates/home/invalid/`). Gates with `arguments` (`door-lock`,
  `valve`, `siren`: `duration_s`) require your `@action` to have an integer argument with that name.

**Requirements:** NeuroEdge only.

**Limitations**

- `gate publish` stops at hash digests, **no digital signatures yet** (signing requires key-managed gate repository — later).
- Gates can compare numbers against thresholds (`pressure: { lt: 8 }`, `numeric` criterion — RFC-0009), but no hardware
  channel supplies unit-bearing readings to it yet: `sensor.read` declares no unit and cannot connect, `analog.in`
  arrives in TSK-I2a-04. Until then, map readings into discrete levels using `bands` (§4.2).
- No CEL syntax for `allow_when` yet; only operator mapping is supported (`TODOS.md` #42).

### 4.2 Creating and running an agent

**Capabilities**

- Scaffold a new agent project from a template (`neuroedge new <name> --template …`). The project includes gates, actions, test
  suite, command grammar, and trace directory; `neuroedge test` passes immediately. Six templates:

  | Template | What it is | What you see |
  |:---|:---|:---|
  | `minimal` | Empty skeleton | Starting point for your agent |
  | `villa-concierge` | Hotel room door lock | ALLOW for correct room, BLOCK and route to front desk when incorrect |
  | `home-voice` | In-home voice assistant: lights, Q&A, news | Turn lights on/off via gate; freeform questions to LLM |
  | `factory-monitor` | Machine room ventilation fan and alarm siren based on temperature | Ask confirmation before turning off fan when hot; reject disabling alarm while hot |
  | `gate-camera` | Gate camera: stranger in zone ⇒ turn on lights, lock gate (requires `--board sim-rpi5`) | Block when no stranger, low confidence, camera offline, or person in privacy zone |
  | `blinds` | Servo-controlled window blinds, with lease and envelope (requires `--board sim-rpi5`) | Unrenewed lease ⇒ `safe_state`; pinch hazard or emergency stop ⇒ block |

- **Add an action to an existing project** (`neuroedge add`): each command generates `@action`, fail-closed default gate,
  bidirectional test suite (ALLOW and BLOCK cases), declares `[requires]`, `[gates]`, and `[sim.*]` tables
  feeding the gate, then runs a dry-run build before writing. Never overwrites: existing files or names ⇒ rejected,
  writes nothing.

  | Command | Primitive | Example |
  |:---|:---|:---|
  | `add action <name>` | `digital.out` (default), `motion`, `display`, `audio.out` | `neuroedge add action open-gate --pin gate_relay` |
  | `add sensor <name>` | `sensor.read` (default), `digital.in`, `analog.in`, `vision.in`, `audio.in` | `neuroedge add sensor heat-guard --source temperature --pin porch_light` |
  | `add device <name>` | `i2c` | `neuroedge add device read-supply --device i2c1/ina219 --register 0x02` |
  | `add gate <name>` | none: a standalone gate | `neuroedge add gate night-lock --fact user_verified --fact door_closed` |

  Extended primitives (`digital.in`, `analog.in`, `i2c`, `motion`, `vision.in`) exist only on board
  `sim-rpi5`: `add` prints the correct board build command, and changes `BOARD = "sim-default"` in
  `tests/test_agent.py` of `minimal` template to `sim-rpi5`. Then: `neuroedge gate lint gates`,
  `neuroedge test`.

- **Match agent against board** before execution (`neuroedge build --target … --board …`): pins,
  sensors, or microphones required by the agent must be present on the board; missing any component ⇒ build halts, prints each issue,
  writes nothing. Check board capabilities: `neuroedge board list`, `neuroedge board show <name>`.
- Run agent by **typing commands** (`neuroedge run`): typed text matching local command grammar triggers an action
  call, passes the gate, and controls virtual pins. No network required, no API keys, deterministic output.
- Run single command and exit (`run -c "…"`), or enter interactive REPL with helper commands to inspect and modify facts,
  pins, sensors, screen (`:facts`, `:set`, `:pins`, `:sensor`, `:screen`, `:confirm`…).
- Open session **web monitor** (`run --ui`, local machine only, 127.0.0.1): virtual door latch, lights, sensors,
  virtual display, verdict stream, and command input box; click Confirm / Cancel when gate asks confirmation.
- Emulate **sensors** and **displays** on `sim`, and transform sensor readings into gate facts: threshold comparison
  (`gte`/`lte`) or banding (`bands`, e.g. 25 °C → `normal`). Same rules run on `linux` with real
  sensors.
- Write and execute **safety tests** for agents (`neuroedge test`, pytest-based): verifies dangerous commands are
  blocked and valid commands allowed.
- Invoke agent from Python code (library): `c.do()` on virtual HAL `SimHAL`.

**Requirements:** NeuroEdge only.

**Limitations**

- Journey "unknown developer installs and runs within 10 minutes" not yet measured with external testers (increment I1).
- Timed commands (`pulse(after_ms=…)`) available only on `sim`.

### 4.3 Traces: record, view, replay, compare

**Capabilities**

- Record session to validated trace (`neuroedge record`), including voice sessions. Traces store decisions
  only: raw text (commands, transcripts, answers) is hashed at source, verdicts preserved
  (NFR-PRIV-03). To retain verbatim text, pass `--raw` during recording — such traces carry `metadata.anonymized = false`.
- Validate traces against schemas (`trace validate`) and display event timelines (`trace show`), including latency
  breakdowns per phase and proportion of turns handled by System 1 vs System 2 (§4.4).
- Render trace as **self-contained HTML file** for review, scrubbing, sharing with colleagues — opens offline
  (`trace view`).
- Export traces to Perfetto format — browser-based timeline visualization tool
  (`ui.perfetto.dev`) — for latency analysis (`trace export --format chrome`).
- **Replay** (`neuroedge replay`): recorded facts are fed back, verdicts and pin commands recomputed,
  then compared against the recording. Mismatches ⇒ reports first diverging line, exit code 1. Replay invokes no models
  and reads no hardware.
- **Verify entire repository** with one command (`neuroedge verify`): all gates resolve, all canonical traces validate and
  replay to expected decisions, all tool call cases yield expected answers — across selected environments
  (`--targets sim,linux,esp32s3`).

**Requirements:** NeuroEdge only (replay on `linux` requires GPIO lines, §5.1; comparison on `esp32s3` requires running
firmware, §5.2).

**Limitations**

- Cross-environment comparisons currently compare **decisions** (verdicts and pin commands), not timing. On
  `esp32s3`, pin operation and duration are still supplied from host-built tables rather than on-chip
  execution (`TODOS.md` #37).
- Traces are not yet digitally signed (`TODOS.md` #1).

### 4.4 AI models: System 1, System 2, and network loss

NeuroEdge separates two comprehension tiers. **System 1** is the fast, local tier: fixed command grammar (list of
phrases → intent), always available, networkless. **System 2** is the slow, intelligent tier: an LLM handling freeform text.
Both merely propose action invocations; gates make decisions.

**Capabilities**

- **Real LLMs for System 2** (Claude, GPT, DeepSeek, models via OpenRouter…): freeform text translates to tool calls,
  still gated. Declared in `[system_two]` in `agent.toml`; API keys reside solely in environment variables, never
  written to files.
- **Cloud model for System 1 — Jev** (`typesafe/jev-1.13` via OpenRouter): evaluates selected gate criteria from
  **speaker utterances** (e.g. "what the user wants"). Restricted to criteria listed in `[system_one]`, and
  answers are checked against value domains and confidence thresholds before reaching gates.
- **On network loss**: when model fails to answer (network loss, timeout, contract violation, below threshold), local command
  grammar decides as before, transition logged in trace; device informs user of functional offline commands.
  If a model-evaluated criterion lacks functional local fallback, action blocks with
  reason `gate_unreachable`.
- **Local knowledge Q&A** (`knowledge.toml`, as in `home-voice` template): questions matching knowledge items
  are answered deterministically from that entry; with System 2 available, the model formulates answers based on retrieved entries; during
  network outages, device recites entry verbatim.
- **Custom adapters** for non-OpenAI standard models (`provider = "python:pkg.mod:func"`).
- System 2 can utilize **external MCP servers** for information retrieval (news, lookups) — retrieval only,
  no device control (`[mcp.servers]`, requires `neuroedge[mcp]`).

**Requirements:** System 2 requires `neuroedge[cloud]` and provider API key; Jev requires OpenRouter key
(`OPENROUTER_API_KEY`), no extra package needed.

**Limitations**

- **Never** assign models criteria concerning identity, permissions, or reservations (`guest_authenticated`,
  `room_matches`…): these are management system facts. Build rejects agent-computed criteria and
  caller source criteria (`call_source`).
- `[system_one]` sends **speaker utterances** to OpenRouter (does not send actions or arguments). Source hashing
  applies only to traces, without preventing transmission.
- Jev operates best in English; reliability on Vietnamese utterances is **unmeasured** — set conservative thresholds
  (`TODOS.md` #27).
- CI invokes no real models; live calls using real keys are tested manually (`scripts/live_llm_smoke.py`,
  `scripts/live_jev_smoke.py`).

### 4.5 Voice: speaking to the agent

> Voice was removed from the roadmap (Q-77, roadmap §6); the host code still ships.

**Capabilities**

- **Speaking via WAV file** (`run --voice-file cau-noi.wav`, or `record --voice-file …`): audio passes voice
  activity detection (VAD), routes to speech-to-text (STT), transcript traverses identical path as typed commands to
  gate, response routes to text-to-speech (TTS) and writes to file (`--voice-out tra-loi.wav`). Runs
  on `sim` and `linux`.
- **Speaking via laptop microphone, real-time** (`run --mic`, `sim` only, requires `neuroedge[audio]`): wear headphones to
  support barge-in; using external speakers requires `--half-duplex` (microphone muted while agent speaks, disabling barge-in). First run on
  macOS requests terminal microphone permissions. The scenario folder was removed (Q-77, see git history).
- **STT/TTS via all OpenAI audio compliant providers** — OpenAI, Groq, OpenRouter, faster-whisper, Kokoro… — configured
  via `base_url` in `[stt]` / `[tts]`; servers returning raw PCM (OpenRouter) declare `format = "pcm"` and `sample_rate_hz`. Built-in fake providers allow keyless testing (§6.6).
- **Barge-in**: user speaks while speaker is active ⇒ speaker stops, and all commands not yet dispatched to pins are cancelled.
  Dispatched commands (an active door latch pulse) run to completion.
- **Wake-word** (`[wake_word]`): turns open only upon detecting specific keyword, replacing generic speech activation.
  Uses openWakeWord (`neuroedge[wake]`) or your adapter. **Models are your own**: NeuroEdge does not bundle
  or download models, as stock openWakeWord models carry noncommercial licenses. Detector
  error ⇒ no turn opens, session continues.
- **Local fallback STT** (`[stt.fallback]`): when primary STT fails, an on-device endpoint (faster-whisper,
  speaches…) handles the turn with independent timeout. Late results from primary STT are discarded, never controlling
  pins. Only when both fail does the device emit an offline message.

**Requirements:** agent declares `audio.in` (and `audio.out` if using `--voice-out`) in `[requires]`; an STT
provider (API key, on-device server, or fake provider).

**Limitations**

- **Real microphones supported only on laptop, target `sim`** (Q-50). Not yet available on `linux`/Pi (requires PipeWire AEC,
  `TODOS.md` #45) and no web monitor for microphone sessions (`--mic --ui` ⇒ exit code 2).
- No compliant, open-licensed wake-word models available (`TODOS.md` #49); CI tests using fake models.
- WAV files with web monitor (`--voice-file` alongside `--ui`) not supported (exit code 2).
- Voice on ESP32-S3 chip is increment I5, not yet started.

### 4.6 Claude Desktop and other agents via MCP

MCP (Model Context Protocol) is the open standard for AI applications to invoke external tools. NeuroEdge turns each
agent action into an MCP tool, with all calls routed through gates.

**Capabilities**

- Inspect actions as tools — schemas for MCP or OpenAI function calling (`mcp tools`).
- Run agent as an **MCP server** over stdio (`mcp serve`) on `sim` or `linux`: all calls pass schema validation
  then gates.
- **Generate Claude Desktop configuration** (`mcp desktop-config --write`): absolute paths, backups of
  existing configuration, preserves all other entries.
- Ask Claude Desktop to "bật đèn" (turn on the light) and **watch virtual light toggle in browser**, sharing one session (`mcp serve --ui`,
  page at `http://127.0.0.1:8765`).

**Requirements:** `neuroedge[mcp]`; Claude Desktop for Desktop integration.

**Limitations**

- MCP defaults to stdio; network MCP available via `mcp serve --http` (mTLS + OAuth 2.1, TSK-P2-04), adding `--ui` allows home users to approve on web UI (chat lights and door demo, `demo/i2f-chat-den-cua/`); tested between VM and host on single laptop, not yet across two physical machines; no persistent outbound MCP server connections (`TODOS.md` #25).
- Web monitor available only on `sim`.

---

## 5. Deploying agents to devices

### 5.1 Linux machines (`--target linux`)

**Capabilities**

- `run`, `record`, and `mcp serve` with `--target linux`: pins map to **real kernel GPIO lines**, sharing identical verdict
  ledger with `sim`. Exiting session ⇒ all lines return to idle, even when terminated via signals.
- Complete set of five hardware primitives (HAL): `digital.out` (output pins), `sensor.read` (hwmon/IIO sensors, resolved by
  **name**), `display` (framebuffer — kernel display device `/dev/fbN` — or in-memory),
  `audio.in`, and `audio.out`.
- **Extended primitives**, declared per board (`board show <id>` lists them): `digital.in` (input lines read by **name**, never written),
  read-only I2C via `/dev/i2c-N` (board-allowed registers only), `analog.in` (hwmon channel, `NEUROEDGE_LINUX_ANALOG`), and `vision.in`
  (system-selected V4L2 camera: `NEUROEDGE_LINUX_CAMERA=/dev/video0`; missing camera or driver mismatching board declaration ⇒ session fails to
  start). Read failures on any primitive ⇒ gate blocks `criterion_unavailable`, never allowing passage.
- **Audio from WAV files**: `run` / `record --voice-file` on `linux` resamples files to board sample
  rate, requiring no microphone or speakers.
- **Wired real microphone and speaker** via PipeWire with AEC (`NEUROEDGE_LINUX_AUDIO=live`, `neuroedge[audio]`;
  PipeWire configuration bundled): session acquires both microphone and speaker **before** asserting any GPIO pins, halting
  immediately if devices are missing. Currently halts at device opening — see Limitations.
- **No Linux machine with hardware attached?** Create virtual GPIO lines using gpio-sim (`scripts/setup_gpio_sim.sh`, kernel
  ≥ 5.19). CI runs entire `linux` suite on gpio-sim, `i2c-stub` + `lm75` virtual sensors, and virtual display.
- Verify decision parity across `sim` and `linux` (`verify --targets sim,linux`).
- **Per-pin safety envelope** (RFC-0007): each load-bearing pin enforces board limits — cumulative on-time in a sliding
  window, minimum spacing between activations, single-pulse ceiling. Pins always turn off when command duration expires or
  ceiling is reached; `off` commands are never blocked. Turn-on commands exceeding limits or issued while pin is already active are rejected
  (`NE1003`) without burning tokens. Active durations are persisted to a board-specific directory
  (`$NEUROEDGE_LINUX_ENVELOPE_STATE`, default `~/.local/state/neuroedge/envelope/<board>`) **before** activation,
  ensuring reboots do not reset counters. **On a fresh hardware testbench**, absence of state records causes turn-on commands to be
  rejected: run session with `NEUROEDGE_LINUX_ENVELOPE_INIT=1` to initialize state (creates missing records only).
  Pin lines are managed by a dedicated supervisor process, releasing lines if runtime hangs or terminates; supervisor is **enabled by default** — initialization failure rejects turn-on commands while `off` commands function (`NEUROEDGE_LINUX_SUPERVISE=0` is for testing/debugging only, recorded in trace).

**Requirements:** Linux system; `neuroedge[linux]` (libgpiod); real or virtual GPIO lines. Real audio requires
additionally `neuroedge[audio]` and PipeWire.

**Limitations**

- **Not yet executed on real Raspberry Pi 5**; nightly automated runs on Pi do not yet exist.
- **No live microphone sessions yet.** Live mic/speaker path only opens devices at session start; no
  session currently records and plays live audio (`TODOS.md` #45). Voice sessions on `linux` currently read WAV files.
- Real microphone and speaker **unverified on hardware**: whether PipeWire node names are accessible via PortAudio/ALSA on Pi
  remains unverified. `linux-rpi5` does not yet declare certified echo cancellation.
- Gate facts not originating from sensors but declared statically in `[sim.facts]` (e.g. "guest is authenticated") remain
  **static values** on `linux`, as no external subsystem supplies them; `run` prints warnings when gates
  decide based on them.
- GPIO input sensors (`motion`, `door_contact`) are unreadable; agents requiring them are rejected before
  acquiring pins.
- No web monitor (`--ui` ⇒ exit code 2). Framebuffer accepts pixel buffers only.

### 5.2 ESP32-S3 chip (`--target esp32s3`)

Complete procedure — generation, build, flashing, QEMU, OTA — in a single place: [`nap-firmware.md`](nap-firmware.md).
Below are capabilities.

**Capabilities (verified on QEMU)**

- **Generate firmware for your agent** (`neuroedge build --target esp32s3`): a complete ESP-IDF project.
  Gates run on chip as binary decision trees in flash, C walker, and single-use verdict
  ledgers.
- **Boot self-test**: firmware re-evaluates agent checks and must match **exact** verdicts computed by the host
  at build time. Any mismatch ⇒ `NE_SELFTEST FAIL` and firmware halts, no action executes.
- **Traces via UART**: record device sessions into host traces
  (`record --target esp32s3 --port …`), then compare chip verdicts against host
  (`verify --targets esp32s3 --port …`).
- **Signed OTA updates** — optional, enabled via `sdkconfig.ota` configuration overlay at build time (default builds lack
  download paths): two A/B firmware slots; update images must be RSA-3072 signed with your key; new images
  are confirmed only after passing self-test, failure causes bootloader rollback to previous image; images older
  than confirmed version are rejected. Download from any HTTP(S) server. If new image **hangs** without rebooting,
  rollback occurs on next power cycle (`nap-firmware.md` §6.3).
- **Agent-aligned UI language**: device screen speaks agent language (Vietnamese or English),
  derived from `[agent] language`, falling back to `[stt] language`, then Vietnamese. Nine LVGL
  screens exist and undergo golden screenshot comparison on every PR.

**Requirements:** ESP-IDF v5.4 (or Docker `espressif/idf:v5.4`); Box-3 once boards arrive, QEMU today.

**Limitations**

- **No hardware in hand; no GPIO pins move yet** (on-chip HAL not implemented).
- No on-chip audio yet (I5); ESP-SR library not linked due to unverified licensing
  (`TODOS.md` #17).
- **OTA not tested on real networks**: QEMU uses virtual Ethernet NIC; Box-3 lacks Wi-Fi connection and
  network credential provisioning (`TODOS.md` #50).
- **No Secure Boot or eFuse downgrade prevention**: anyone with cable access can flash any signed image.
- UI currently built on host for golden screenshot comparison; **not yet linked into firmware** (awaiting display driver).
  UI supports Vietnamese and English only; other languages rejected by build.
- Arbitrary trace replay on chip not supported (`replay --target esp32s3` ⇒ exit code 2).

---

## 6. Step-by-step walkthroughs

Each scenario details prerequisites, commands, and expected observations. Following in order proceeds from simplest
to most advanced. All commands assume `neuroedge` is in `PATH` (§3).

### 6.1 Gate allow and gate block — 2 minutes, zero setup

In repo root (default sample agent is hotel door latch `villa-concierge`):

```bash
neuroedge run -c "mở cửa phòng 101"
neuroedge run -c "mở cửa phòng 202"
```

The first command yields `✓ ALLOW unlock_door@1.2.0` and pin `door_lock` becomes `PULSED 30s`. The second command yields
`✗ BLOCK … criterion: room_matches` and transfers to front desk: guest is not booked in room 202.

### 6.2 Confirmation and denial — factory agent

```bash
neuroedge new nhamay --template factory-monitor && cd nhamay
neuroedge run -c "bật quạt"        # ✓ ALLOW: adding airflow is always safe
neuroedge run -c "tắt quạt"        # ✗ BLOCK with confirmation: "Phòng máy đang nóng — bạn chắc muốn tắt quạt thông gió?" (Machine room is hot — are you sure you want to turn off the exhaust fan?)
neuroedge run -c "tắt báo động"    # ✗ BLOCK, action deny: no one turns off the siren while the room is still hot
neuroedge test                     # agent safety test suite: all tests pass
```

The virtual machine room starts at 45 °C (`high` band). Enter interactive REPL (`neuroedge run`), type
`:sensor temperature 30` to drop temperature into `normal` band, then type "tắt quạt" again: this time it is allowed. Type
`:help` to view all helper commands.

### 6.3 Viewing in browser

Inside `nhamay` directory:

```bash
neuroedge run --ui
```

Browser opens `http://127.0.0.1:…` (address printed to terminal) displaying fan, siren, temperature sensor,
and verdict stream. Type commands into **"Gõ lệnh cho agent"** (Type a command for the agent) box on page: "tắt quạt" prompts the page to display the question
with two buttons Đồng ý / Huỷ (Confirm / Cancel); `:sensor temperature 30` lowers temperature directly on the page. Stop with Ctrl-C in
terminal.

### 6.4 Record, inspect, replay

```bash
neuroedge record -c "tắt báo động"                  # prints: trace: traces/sess_….json
neuroedge trace view traces/sess_….json -o xem.html # open xem.html in browser, offline
neuroedge replay traces/sess_….json
```

`replay` recalculates verdicts from recorded facts and prints `✓ decisions match the recording`. Try modifying gate
`alarm_off` to be more permissive and replay again: replay reports mismatch and exits with code 1 — demonstrating how NeuroEdge catches
weakened safety constraints.

### 6.5 Controlling virtual devices with Claude Desktop

Requires `pip install 'neuroedge[mcp]'` and Claude Desktop.

```bash
neuroedge mcp desktop-config --agent agent.toml --ui --write
```

Fully quit Claude Desktop and restart, ask it to "bật quạt" (turn on the fan). Verdict appears at `http://127.0.0.1:8765`. If page
does not update, see §7.

### 6.6 Speaking to agent via WAV file — keyless

> Voice was removed from the roadmap (Q-77, roadmap §6); the host code still ships.

Create `home-voice` agent, then add two configurations to `agent.toml`:

1. Under `[requires]`, add line `"audio.in" = { sample_rate_hz = 16000 }`.
2. At end of file, declare fake providers (they "hear" your specified sentence):

   ```toml
   [stt]
   provider = "python:neuroedge.perception.providers.fake:stt"
   [stt.options]
   transcripts = ["bật đèn"]

   [tts]
   provider = "python:neuroedge.perception.providers.fake:tts"
   ```

Prepare a 16 kHz, mono, 16-bit WAV file with audio (speech or a beep, as fake
providers do not analyze audio). Then:

```bash
neuroedge run --voice-file cau-noi.wav --voice-out tra-loi.wav
```

You will see `turn 1 · … · heard: “bật đèn”`, `✓ ALLOW light_on@1.0.0`, and summary line `voice: …`.
For real speech: replace `[stt]` / `[tts]` with real providers (`base_url`, `model`, `api_key_env`) — configuration
details in `CHANGELOG.md` §2.3 (`run` command).

### 6.7 Real LLMs for freeform queries

Requires `pip install 'neuroedge[cloud]'` and API keys. Agent `home-voice` includes commented `[system_two]` sample
in `agent.toml`: uncomment, set environment variable containing key, then run `neuroedge run`. Commands outside grammar
(such as questions) are handled by the model; commands controlling lights still pass through gates. Disconnect network and retry: device speaks
offline message and lists remaining functional local commands.

### 6.8 Real Linux GPIO pins — on a Linux machine

Requires Linux kernel ≥ 5.19, `sudo` privileges, and `pip install 'neuroedge[linux]'`.

```bash
bash scripts/setup_gpio_sim.sh     # creates virtual GPIO lines named door_lock, porch_light, gate_relay (calls sudo)
neuroedge run --target linux --agent fixtures/agents/driveway/agent.toml -c "bật đèn hiên"
neuroedge verify --targets sim,linux
```

The `run` command toggles the real kernel line `porch_light` (`driveway` sample agent: porch light and gate). The
`verify` command replays all canonical traces on both `sim` and `linux`, asserting identical decisions.
Agent `villa-concierge` is rejected on `linux`: it requires hardware echo-cancelling microphone,
which `linux-rpi5` does not declare — demonstrating NeuroEdge blocking incompatible agent/board pairings.

### 6.9 Agent firmware on QEMU

Requires Docker and image `espressif/idf:v5.4`. Inside a `home-voice` project:

```bash
neuroedge build --target esp32s3     # prints: firmware: build/esp32s3 — ESP-IDF project, …
```

Build and execute on QEMU following [`nap-firmware.md`](nap-firmware.md) §5. In output, line
`NE_SELFTEST PASS walker=… token=…` proves agent gates run properly on virtual chip: `walker` indicates passed
gate tree walker checks, `token` indicates passed verdict ledger checks.

### 6.10 OTA updates on QEMU

Requires Docker. In repo root:

```bash
docker run --rm -v "$PWD":/work -w /work espressif/idf:v5.4 \
  bash -lc '. $IDF_PATH/export.sh >/dev/null 2>&1; bash scripts/qemu_ota.sh'
```

Script spins up update server, signs image with single-use key, and executes seven phases: valid new image is fetched
and confirmed; wrong-key image is rejected; unsigned image is rejected; two defective images automatically roll back; older versions are
skipped. Finishes with `OTA on QEMU: all phases passed`. Meaning of each `NE_OTA …` line:
[`nap-firmware.md`](nap-firmware.md) §6.4.

### 6.11 Viewing device UI

Zero setup required: open PNG images in `targets/esp32s3/ui/golden/vi/` (Vietnamese) and
`targets/esp32s3/ui/golden/en/` (English). These display exact pixel renderings of the nine screens on Box-3's
320×240 panel, including truncated text with `…`. Re-render and compare: `bash scripts/run_ui_golden.sh`
(requires cmake or Docker).

---

## 7. Troubleshooting

**All error messages contain three parts**: location · cause · remediation. Reading error messages and meanings
of each `NE…` code: `CHANGELOG.md` §2.4.

**Exit codes** across all commands adhere to a contract: `0` verified and passed · `1` verified and failed · `2` feature
not yet implemented. Exit code `2` honestly conveys that a feature does not exist — NeuroEdge never fakes passing.

**Claude Desktop and `mcp serve --ui`: web page does not change when called from Desktop.** Desktop often runs multiple
server processes concurrently, each with its own page, and only one can hold port 8765
(`docs/spec/tool_calling.md` §8). Locating the active page:

1. Open Desktop log — on macOS at `~/Library/Logs/Claude/mcp-server-<name>.log`.
2. Find lines `sim UI at http://127.0.0.1:…` and `warning: sim UI port 8765 is taken … the page is at …`.
3. Open each URL; the active conversation page is the one updating upon tool calls.

Firmware and OTA troubleshooting table: [`nap-firmware.md`](nap-firmware.md) §7.

---

## 8. Further reading

| Goal | Read |
|:---|:---|
| Complete syntax for all commands | [`CHANGELOG.md`](../../CHANGELOG.md) §2.3 |
| Progress by task and increment | [`trang-thai.md`](trang-thai.md) |
| Firmware flashing, QEMU, OTA | [`nap-firmware.md`](nap-firmware.md) |
| How each hardware primitive runs across environments | [`simulation_coverage.md`](../spec/simulation_coverage.md) |
| Blocked bypass paths around gate | [`threat_model.md`](../spec/threat_model.md) |
| All other documentation | [`README.md`](README.md) (documentation map) |

To propose additions to this document: open an issue or PR following [`CONTRIBUTING.md`](../../CONTRIBUTING.md).
