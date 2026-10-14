# NeuroEdge

**From an idea to a physical AI product: build it, run it safely, share and sell it.**
Physical AI, under contract — no contract, no action: every command to the hardware passes
the gate.

NeuroEdge is a **rules-enforcing box** standing between AI and physical devices. AI may only *request* an action; the rule
on the box (called a *gate*) decides: execute immediately, ask you first, or reject with a reason — and records
every decision for replayability. The reason: if a chatbot says something wrong, you can click retry; but once a door
opens incorrectly, you cannot undo it.

```text
📱 You message ──► 🧠 NeuroClaw (brain) ──► 🛡️ NeuroEdge Box (rules) ──► 💡 Lights, doors, sensors
```

The brain is **NeuroClaw**, a separate repo `letrongminh/neuroclaw` (MIT): chats via Telegram, invokes AI, remembers,
schedules reminders, and touches physical devices **only** through the box. It runs on Linux, cloud, Pi, macOS, Windows, or
shares a single ESP32-S3 chip with the box.

**Working today:** rules on computer with virtual devices, on Linux with emulated GPIO pins, on
emulated ESP32-S3 chip (QEMU); messaging Telegram to NeuroClaw to turn on lights, open doors with owner confirmation — already
demonstrated in live demo. **Not yet present:** physical hardware boards, long-horizon spoken delegation, shareable or sellable
packages (*Blueprints*).

**Newcomers read first:** [Start here](https://github.com/letrongminh/neuroedge-init/blob/main/docs/user/bat-dau.md) (5 minutes) · connecting brain to box:
[chat with home](https://github.com/letrongminh/neuroedge-init/blob/main/docs/user/chat-voi-nha.md).

> Alpha. NeuroEdge is **not** a certified safety function (no SIL, no PL): gates
> do not replace emergency stops or hardware interlocks. Progress in
> [project status](https://github.com/letrongminh/neuroedge-init/blob/main/docs/user/trang-thai.md).

## Quickstart (Python 3.11+)

Not yet published to PyPI: before public release, install from source per
[`python/README.md`](https://github.com/letrongminh/neuroedge-init/blob/main/python/README.md), then run the following two
commands.

```bash
pip install neuroedge    # with Claude Desktop or real LLMs: 'neuroedge[mcp,cloud]'
neuroedge new my-home --template home-voice
neuroedge run --agent my-home/agent.toml -c "bật đèn"
```

No internet needed, no API keys needed, no accounts needed: the command *"bật đèn"* (turn on the light) passes through local
command grammar, gate `light_on` returns ALLOW, and virtual light `porch_light` turns on. Continue typing commands and
inspect verdicts on the local web page: `cd my-home && neuroedge run --ui`.

To ask Claude Desktop to *"bật đèn"*: `pip install 'neuroedge[mcp]'`, then
`neuroedge mcp desktop-config --agent my-home/agent.toml --ui --write`, quit Claude
Desktop completely and reopen — verdicts appear at http://127.0.0.1:8765 (if port is busy, the real URL is
in Desktop's MCP logs).

## What a Gate Looks Like

```yaml
name:    unlock_door
version: 1.2.0
extends: neuroedge://gates/hospitality/base-access@1.0.0   # may only tighten parent gate

allow_when:
  room_matches: true
  risk_level:   { lte: low }        # parent allows up to medium — child tightens to low

on_block: { action: escalate, to: human_receptionist }
budget:   { p95_latency_ms: 120, fail: closed }   # cannot verify in time ⇒ BLOCK
```

No path to GPIO pins bypasses the gate.

## Further Reading

- [User Guide](https://github.com/letrongminh/neuroedge-init/blob/main/docs/user/README.md)
  · [five hardware kits](https://github.com/letrongminh/neuroedge-init/blob/main/docs/user/kit-phan-cung.md)
  · [all commands and expected output](https://github.com/letrongminh/neuroedge-init/blob/main/CHANGELOG.md#2-cách-vận-hành)
- [Tool calling via gates and MCP](https://github.com/letrongminh/neuroedge-init/blob/main/docs/spec/tool_calling.md)
  · [threat model](https://github.com/letrongminh/neuroedge-init/blob/main/docs/spec/threat_model.md)
- [Architecture](https://github.com/letrongminh/neuroedge-init/blob/main/docs/architecture/README.md)
  · [contributing](https://github.com/letrongminh/neuroedge-init/blob/main/CONTRIBUTING.md)
  · [licensing](https://github.com/letrongminh/neuroedge-init/blob/main/LICENSING.md)

## Licensing

Code is licensed under [PolyForm Noncommercial 1.0.0](https://github.com/letrongminh/neuroedge-init/blob/main/LICENSE):
free for noncommercial use; **commercial use requires a commercial license**. Schemas,
specifications, and conformance test suites are licensed under
[Apache-2.0](https://github.com/letrongminh/neuroedge-init/blob/main/LICENSES/Apache-2.0.txt), so anyone
can implement the standards. Scope breakdown:
[`LICENSING.md`](https://github.com/letrongminh/neuroedge-init/blob/main/LICENSING.md).
