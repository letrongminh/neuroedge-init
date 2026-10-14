# Demo script — NeuroEdge in simulation environment (`sim`)

> **Last re-run:** 2026-09-29, macOS, `main` `6a69626`.  
> **Duration:** 5–7 minutes (each scene ≤ 1 minute). No hardware needed, no external network needed.

---

## 0. Preparation

Before the demo session, the presenter prepares the environment:

```bash
# 1. Run script to create virtual environment and 3 sample projects at /tmp/neuroedge-demo
bash demo/i1-sim/chuan-bi.sh

# 2. Set alias 'ne' from repo root, then change directory to demo folder
alias ne="$PWD/python/.venv/bin/neuroedge"
cd /tmp/neuroedge-demo

# 3. Ensure terminal window width is ≥ 100 columns
```

> [!IMPORTANT]
> **What not to say:** Read carefully the table *"What not to say in any demo"* in [`docs/business/cong-nhu-cau-2026-10-25/demo.md` §0.1](../../docs/business/cong-nhu-cau-2026-10-25/demo.md#01-điều-không-được-nói-trong-bất-kỳ-demo-nào) and unsupported capabilities in [`CHANGELOG.md` §3.7](../../CHANGELOG.md#37-điều-hệ-thống-chưa-làm-được). Absolutely do not say that the system already runs on a real board, receives live microphone voice directly, or parses free-form language outside the command grammar.

---

## 1. Scene 1 — "Door lock does not open the wrong room" (villa-concierge)

### Say
"Door unlock commands from guests must go through the local safety gate. For the correct room, the latch unlocks for 30 seconds; for the wrong room or missing authentication facts, the latch stays still and escalates to the receptionist."

### Type
```bash
ne run --agent villa-concierge/agent.toml -c "mở cửa phòng 101"
ne run --agent villa-concierge/agent.toml -c "mở cửa phòng 202"
ne run --agent villa-concierge/agent.toml
# in REPL:
:set guest_authenticated false
mở cửa phòng 101
:set guest_authenticated true
:unset risk_level
mở cửa phòng 101
exit
```

### See
```text
✓ ALLOW unlock_door@1.2.0 → unlock_door(guest_id='101')
│ door_lock │ PULSED 30s │        1 │
…
✗ BLOCK unlock_door@1.2.0 (reason: condition_not_met, criterion: room_matches)
  action: escalate to human_receptionist — "Yêu cầu cần được nhân viên lễ tân xác nhận trực tiếp…"
│ door_lock │ LOW   │        0 │
…
neuroedge>   guest_authenticated = false
neuroedge> intent unlock (1.00) [room=101]
✗ BLOCK unlock_door@1.2.0 (reason: condition_not_met, criterion: guest_authenticated)
…
neuroedge>   risk_level is now undecided
…
✗ BLOCK unlock_door@1.2.0 (reason: criterion_unavailable, criterion: risk_level)
```

### Highlights
The gate blocks automatically under the fail-closed principle as soon as a criterion is missing (`criterion_unavailable`) without requiring application code to catch errors; BLOCKed commands still exit with code 0.

---

## 2. Scene 2 — "Device asks before acting" (home-voice)

### Say
"When a physical action carries risk (turning off lights while people are still in the room), the gate blocks and triggers a direct confirmation question on the device; only someone on site has the right to press agree."

### Type
```bash
# run --ui automatically opens the browser (default port 8765, 127.0.0.1; no --open flag; --no-browser to disable)
ne run --agent home-voice/agent.toml --ui
# Actions in web command box or terminal REPL:
:sensor motion true
bật đèn
tắt đèn
# Dialog "Thiết bị hỏi xác nhận" (Device asks for confirmation) appears on web page: click button "Đồng ý"
:sensor motion false
tắt đèn
wifi nhà mình là gì
exit
```

### See
- **On the web interface (`http://127.0.0.1:8765/`):**
  - The **Sensors** panel shows `motion: true`. When typing `bật đèn` ("turn on light"), the **Devices** panel shows `porch_light` lit yellow (HIGH) and the **Gate verdict** panel shows `ALLOW`.
  - When typing `tắt đèn` ("turn off light"), the **Device asks for confirmation** panel pops up: `"Vẫn còn người trong phòng — bạn chắc muốn tắt đèn? (light_off)"` accompanied by 2 buttons **"Đồng ý"** (Agree) / **"Huỷ"** (Cancel) and a 10 s countdown. Clicking **"Đồng ý"** → light switches to LOW.
  - When `motion = false` → typing `tắt đèn` is immediately ALLOWed; `wifi nhà mình là gì` ("what is our wifi") is answered by the **Assistant speaks** panel from the knowledge base without touching physical pins.
- **Corresponding output on terminal:**
```text
✓ ALLOW light_on@1.0.0 → light_on()
│ porch_light │ HIGH  │        1 │
✗ BLOCK light_off@1.0.0 (reason: condition_not_met, criterion: room_empty)
  action: ask — "Vẫn còn người trong phòng — bạn chắc muốn tắt đèn?"
  ? xác nhận confirm_1: gõ có để tiếp tục, không để huỷ · còn 10 s · chỉ người trên thiết bị trả lời được
answer to the pending question (confirmed)
  ✓ ALLOW light_off@1.0.0 → light_off()
  says (confirmed): Đã xác nhận.
✓ ALLOW light_off@1.0.0 → light_off()
  says (knowledge_local): Mạng wifi là NhaMinh, mật khẩu dán ở mặt dưới router.
```

### Highlights
The `on_block: ask` mechanism under RFC-0006 clearly distinguishes between human on-site confirmation and remote calls; the sim UI web page is served internally via loopback `127.0.0.1` only.

---

## 3. Scene 3 — "Sensors decide" (factory-monitor)

### Say
"Environmental sensors decide command validity. At 60 °C (critical), the command to turn off the fan is decisively blocked without asking; at 45 °C the device asks; at 30 °C the alarm can be turned off safely."

### Type
```bash
ne run --agent factory-monitor/agent.toml
# in REPL:
bật quạt
:sensor temperature 60
tắt quạt
:sensor temperature 45
tắt quạt
không
:sensor temperature 30
tắt báo động
exit
```

### See
```text
✓ ALLOW vent_on@1.0.0 → vent_on()
│ gate_relay  │ HIGH  │        1 │
neuroedge>   temperature = 60
✗ BLOCK vent_off@1.0.0 (reason: condition_not_met, criterion: heat_level)
  action: ask — "Phòng máy đang nóng — bạn chắc muốn tắt quạt thông gió?"
neuroedge>   temperature = 45
  ? xác nhận confirm_1: gõ có để tiếp tục, không để huỷ · còn 10 s · chỉ người trên thiết bị trả lời được
neuroedge> answer to the pending question (declined)
  says (declined): Đã huỷ.
neuroedge>   temperature = 30
✓ ALLOW alarm_off@1.0.0 → alarm_off()
```

### Highlights
At 60 °C, the gate prints `action: ask` but **does not open a confirmation question** (no `? xác nhận confirm_1` line) because condition `heat_critical: false` is violated and is not in the `confirms: [heat_level]` list; at 45 °C the question opens.

---

## 4. Scene 4 — "Reproduce incident on laptop"

### Say
"Every blocking decision leaves a privacy-preserving anonymized trace; this trace can be opened as visual HTML, replayed on a laptop, and verified automatically in CI."

### Type
```bash
cd villa-concierge
ne record -c "mở cửa phòng 202"
T=$(ls -t traces/sess_*.json | head -1)     # random session name on each recording
ne trace show "$T"
ne trace view "$T" --open
ne replay "$T"
ne verify
```

### See
```text
trace: traces/sess_<id>.json (9 events)
│ text_input             │ {"text": "sha256:79ec5403a912a0baa7b575468e6e5f4d6f70f7b0e76e05d34d5b1…
│ gate_facts             │ {"guest_authenticated": {"value": true…}, "room_matches": {"value": false…}}
…
✓ traces/sess_<id>.html (9 events)
…
✓ decisions match the recording
╭──────────────────────────────────────── neuroedge verify ────────────────────────────────────────╮
│ Passed: all 3 gate(s) resolve, all 3 canonical trace(s) validate… match the verdicts…            │
│ Compared: decisions only — not timing. Timing equivalence arrives with TSK-S4-04.                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Highlights
Traces by default SHA-256 hash typed/spoken text at source (`"text": "sha256:…"` per TSK-I1-01, `--raw` flag keeps verbatim text) but store sufficient `gate_facts` for `replay` to reproduce 100% of decisions; `verify` on a computer only compares decisions (`sim` only), `linux` and `esp32s3` are verified in CI.

---

## 5. Scene 5 (optional) — MCP with Claude Desktop

### Say
"When connecting a large language model (Claude Desktop) via Model Context Protocol (MCP), the LLM only proposes tool calls; the NeuroEdge safety gate remains the decisive checkpoint controlling devices."

### Type
```bash
# View MCP config for Claude Desktop (--ui flag supported)
ne mcp desktop-config --agent home-voice/agent.toml --ui

# Run MCP server serving Claude Desktop with web interface (--open flag opens browser)
ne mcp serve --agent home-voice/agent.toml --ui --open
```

### See
```text
(check again when running)
```
- When user tells Claude Desktop *"bật đèn lên"*, Claude sends tool call `light_on` via MCP stdio.
- The server receives it, checks via the gate, switches pin `porch_light` to HIGH and updates directly on the `--ui` web page (`http://127.0.0.1:8765/`).

### Highlights
Tool calls from an external LLM must comply with Gated Tool Profile v0; the gate is the physical safety boundary preventing prompt injection.

---

## 6. Frequently asked questions during demo

1. **Real hardware:** *"Does the system already run on real boards?"*  
   → No physical ESP32-S3-BOX-3 board yet; the entire demo currently runs on the `sim` target (virtual pins) or QEMU UART in CI ([`demo.md` §0.1](../../docs/business/cong-nhu-cau-2026-10-25/demo.md#01-điều-không-được-nói-trong-bất-kỳ-demo-nào) · [`CHANGELOG.md` §3.4, §3.7](../../CHANGELOG.md#37-điều-hệ-thống-chưa-làm-được)).

2. **Live voice:** *"Can we speak directly via real-time microphone?"*  
   → Voice is currently received from WAV files (`--voice-file`), no real-time microphone session on computer yet ([`CHANGELOG.md` §3.7](../../CHANGELOG.md#37-điều-hệ-thống-chưa-làm-được) · [`demo.md` §0.1](../../docs/business/cong-nhu-cau-2026-10-25/demo.md#01-điều-không-được-nói-trong-bất-kỳ-demo-nào)).

3. **Privacy:** *"Does the trace expose raw user text?"*  
   → By default typed/spoken text is SHA-256 hashed at source (`metadata.anonymized = true`), raw text is only stored when passing explicit `--raw` flag (TSK-I1-01, NFR-PRIV-03 in `neuroedge-prd.md`).

4. **Verify scope:** *"What does `neuroedge verify` compare across targets?"*  
   → Compares gate verdicts and pin commands (decisions only), not execution timing (timing equivalence in TSK-S4-04) ([`CHANGELOG.md` §3.7](../../CHANGELOG.md#37-điều-hệ-thống-chưa-làm-được) · [`demo.md` §0.1](../../docs/business/cong-nhu-cau-2026-10-25/demo.md#01-điều-không-được-nói-trong-bất-kỳ-demo-nào)).

5. **Command exit code:** *"Does `run -c` exit with a non-zero exit code when BLOCKed?"*  
   → No, BLOCK is a valid safety verdict of the gate, not an execution error; the process terminates with exit code 0 ([`run.py`](../../python/neuroedge/cli/run.py)).
