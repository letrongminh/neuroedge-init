# Demo script — NeuroEdge Studio (I1, TSK-I1-04)

> **Last re-run:** 2026-09-29, macOS, branch `studio/integration`: seven browser verification scenes with agent
> `home-voice` (light and dark themes, 1280 px and 390 px, VI and EN, no console errors).
> **Duration:** 7–8 minutes. No hardware needed. The voice scene requires `--mic` and headphones (see `demo/i4-thoai-laptop/`).

Studio is a **single page** for all capabilities runnable on a laptop, opened only at `127.0.0.1`, downloading nothing from the network.
Server–page contract: [`docs/spec/studio.md`](../../docs/spec/studio.md). What not to say: table in
[`docs/business/cong-nhu-cau-2026-10-25/demo.md`](../../docs/business/cong-nhu-cau-2026-10-25/demo.md) §0.1.

## 0. Preparation

```bash
bash demo/i1-sim/chuan-bi.sh                 # venv + three sample projects in /tmp/neuroedge-demo
alias ne="$PWD/python/.venv/bin/neuroedge"
cd /tmp/neuroedge-demo
ne studio --agent home-voice/agent.toml      # opens browser; Ctrl-C to stop
# with key and headphones: use agent from demo/i4-thoai-laptop and add --mic
```

The **VI | EN** button in the top right switches all labels; selection is remembered in the browser.

---

## Scene 1 — Live session: "gate decides, human confirms"

**Type into command box:** `:sensor motion true`, `bật đèn`, `tắt đèn`.

**See:**
- Device `porch_light` lit (HIGH) after `bật đèn`; sensor `motion: true`.
- Conversation column: each turn has a routing label (**Command grammar**), `intent light_on (1.00)`, a **✓ ALLOW** chip, and a latency bar broken down by stage (perception, gate, action).
- `tắt đèn` ⇒ **✗ BLOCK** `condition_not_met room_empty`, **ask confirmation** chip, and the **Device asks for confirmation** card in the right column: "Vẫn còn người trong phòng — bạn chắc muốn tắt đèn? (light_off)", countdown, default focus on **Huỷ** (Cancel).
- Click **Đồng ý** (Agree) ⇒ turn logs **confirmed**, verdict **✓ ALLOW**, light turns off. No answer within 10 s ⇒ **expired**.

**Highlights:** "Only someone on the device can answer — assistants and MCP clients cannot confirm on their behalf" (RFC-0006). Click **Explain** on a verdict to view each criterion, value, source, and which criterion failed.

## Scene 2 — Gate: "read rules, test rules"

**See:** the agent's gate table (`light_on@1.0.0`, `light_off@1.0.0`, level, `closed`, **OK**, digest). Select a gate ⇒ inheritance chain, criteria and types, `allow_when`, `on_block`, `budget`.

**Do:** **Quick test (what-if)** box: change `call_source` or unset a criterion ⇒ planned verdict changes immediately (unset ⇒ BLOCK `criterion_unavailable`, fail-closed). Does not touch the session, devices, or traces.
**Gate lint** button ⇒ `2/2`.

## Scene 3 — Traces: "reproduce incident"

**Do:** click **Save current session** ⇒ session appears in the table, text column shows **sha256** (user text is hashed when recorded — TSK-I1-01). Select session ⇒ timeline: gate lane (ALLOW/BLOCK) and `porch_light` lane (ON/OFF). Click **Replay** ⇒ verdicts match the recording. **Download JSON** downloads the exact `trace.v1` file.

## Scene 4 — Verification: "same verdict across all targets"

**Do:** click **verify** (about 1–2 s).

**See:** matrix: three gates, three canonical traces (`happy-path.json`, `network_offline.json`, `unverified_attempt.json`), and tool call corpus. The `sim` column shows **✓ this machine**; `linux` shows **CI · linux-hal** (gpio-sim), `esp32s3` shows **CI · uart-trace** (QEMU). Summary line: "Passed: all 3 gate(s) resolve, all 3 canonical trace(s) validate, every tool call of the corpus gives its recorded result, and 3 replay(s) on sim match the verdicts and pin commands they record." · "Compared: decisions only — not timing". The **test** button runs the project's `neuroedge test`.

## Scene 5 — ESP32-S3 device: "the chip, before having the chip"

**See:** banner "No board yet: everything here runs on QEMU; no pins moved yet". Real LVGL golden screenshots (VI/EN) of 33 device screens. Click **Build package** ⇒ generates ESP-IDF project for agent (38 files with `villa-concierge`). The QEMU and OTA pane shows results when the machine has run `demo/i3-firmware-qemu/run.sh boot` and `… ota` (Docker): milestones `NE_SELFTEST PASS walker=26 token=11`, `NE_TRACE DONE sessions=4`, and seven OTA phases a–g. If not run yet, the screen says so clearly.

## Scene 6 — MCP & integration: "LLM calls, gate decides"

**See:** actions turned into schematized MCP tools (`light_on`, `light_off`), Claude Desktop configuration to copy (`mcp serve --ui`), external MCP servers (`news: headlines`, "data only, never a command"), and live MCP call table (populated when running `neuroedge mcp serve --ui` alongside Claude Desktop).

## Scene 7 — Agent & configuration

**See:** agent's `requires`, capabilities of `sim-default` board, AI providers (STT, TTS, System 1, System 2) with only **variable name** and **yes/no** — key values are never shown, and four project templates.

## Frequently asked questions

- *Can it run on a local network for others to view?* No: `127.0.0.1` only (`docs/spec/studio.md` §2).
- *Are metrics prefabricated?* No: every screen reads the API of the running session; screens without data state "none yet" (`docs/spec/studio.md` §4).
- *Can we talk to it?* Yes, with `--mic` on laptop and headphones (Q-50) — script in `demo/i4-thoai-laptop/`.
