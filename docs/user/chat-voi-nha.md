# Chat with home using NeuroClaw

You message the **brain** via Telegram (or other chat channels), and the brain controls home devices
through the **home box**. The brain is [NeuroClaw](https://github.com/letrongminh/neuroclaw), a separate repo,
MIT. The box is `neuroedge mcp serve --http` from this repo. The box holds the gate: every command is a *request*,
the gate decides, and actions requiring owner confirmation are asked on the home page.

> Status: on one Linux machine, `neuroedge install --profile full` sets up box and brain in one command
> (Q-83 Profile A, checked on CI in job `install-full`); brain tokens live at most 7 days and nothing renews them
> on its own yet (section 1). Brain on another machine: the demo script suite. NeuroEdge Cloud is not yet open
> (Q-74). Requirements: [`deployment_profiles.md`](../spec/deployment_profiles.md); architecture:
> [`15-target-architecture.md`](../architecture/vi/15-target-architecture.md) §6.10.

## Choose how to run the brain

| Run mode | Brain location | Read |
|:---|:---|:---|
| Self-hosted | NeuroClaw (Go) on VPS, Linux board, Pi, Mac or Windows | Sections 1 → 3 below |
| Single chip | NeuroClaw-ESP on the same ESP32-S3 as the gate | [`esp32-mot-chip.md`](esp32-mot-chip.md) (awaiting board) |
| NeuroEdge Cloud | Instance operated by NeuroEdge | Not yet available — conditional after demand gate (Q-74) |

## 1. Set up the box

**Box and brain on one Linux machine (Profile A), one command,** as root, with the secrets in a file
(`TELEGRAM_BOT_TOKEN`, `TELEGRAM_OWNER_ID`, `LLM_API_KEY`, `LLM_MODEL`; never on the command line):

```bash
sudo neuroedge install --profile full --agent my-agent --env-file secrets.env   # --target sim without GPIO
```

It makes two system users (`neuroedge` for the box, `neuroclaw` for the brain, no device access), the keys in
`/var/lib/neuroedge/keys` (the brain gets only its certificate, key, token and the CA), downloads the pinned
NeuroClaw release and checks its SHA-256, writes hardened systemd units, mounts `/proc` with `hidepid=2` and ends
with `neuroedge doctor`. Add `--root /tmp/staged` to see every file it would write without running anything.
Afterwards:

| Need | Command |
|:---|:---|
| Open the home page to approve | `sudo -u neuroedge neuroedge ui-link` (a fresh one-time link; the old one stops working) |
| The brain's token is near its 7 days | `sudo neuroedge install …` again (keys kept, fresh token), or `neuroedge pair renew --dir <keys>` and copy the token to the brain |
| A brain key may have leaked | `neuroedge pair rotate --dir <keys>`: the old certificate is refused at the next connection |
| Which risky capabilities the brain has on | `sudo neuroedge status` (`risk=<name>` per line) |
| Check the brain is still kept apart | `sudo neuroedge doctor --keys /var/lib/neuroedge/keys` |

**Brain on another machine:** the box requires complete server certificates, device CA, issuer, and token signing keys; missing any one prevents
opening the port ([`tool_calling.md`](../spec/tool_calling.md) §8.1). The fastest path today is the demo
script: [`demo/i2f-chat-den-cua/kich-ban.md`](../../demo/i2f-chat-den-cua/kich-ban.md) §0.1.
It creates keys once (`tao-khoa.py`), then runs `neuroedge mcp serve --http --ui --target sim`.
The page `127.0.0.1:8765` is the home screen, where you approve actions requiring owner confirmation. Open it with the full URL
the terminal prints, including `#c=…`, within ten minutes: that one-time code gives this page alone the run's key, so no other program on the machine can approve for you.

## 2. Install NeuroClaw and connect to the box

The one-command install above already did this; this section is for a brain on another machine.

- **Install** per your environment: [NeuroClaw installation guide](https://github.com/letrongminh/neuroclaw/blob/main/docs/guides/install.md).
- **Connect to the box** using an MCP server of type `http` with a `tls` block (CA, brain certificate
  and key, token): [NeuroClaw as NeuroEdge brain](https://github.com/letrongminh/neuroclaw/blob/main/docs/guides/neuroedge.md).
- **Or use the demo script:** `chay-nao.sh` downloads the NeuroClaw release (verifying checksums), sets up
  `config.json` from [`demo/i2f-chat-den-cua/neuroclaw/config.json`](../../demo/i2f-chat-den-cua/neuroclaw/config.json)
  and runs `neuroclaw gateway`; `dung-vps.sh` performs this on a VPS
  ([`kich-ban.md`](../../demo/i2f-chat-den-cua/kich-ban.md) §0.2).

Copy to the brain machine only what it needs: CA, brain certificate and key, token. **Never**
copy the issuer key or the box key.

## 3. Choose open or bounded brain

NeuroClaw has full PicoClaw capabilities: shell, hardware bus, skill installation, commands in cron. Each active
capability logs a line `NeuroClaw risk=<name>` at startup (Q-80).

- **Brain co-located on the same machine as the box** with `risk=shell` or `risk=hardware_bus` active can bypass the gate.
  Disable them in `config.json` (the demo version has them disabled) or run the brain under a dedicated user without
  hardware permissions (TSK-I2d-24).
- **Brain on a different machine** (VPS, cloud): the gate still decides every action for home devices; the shell only reaches
  that machine itself.

Rationale: [`threat_model.md`](../spec/threat_model.md) §2k. Label list: `docs/reference/capabilities.md`
§2 of the `neuroclaw` repo.

## 4. Chat

Message the bot: "bật đèn phòng khách" (turn on living room light) executes immediately; "mở cửa" (open the door) makes the box ask you on the home page, and the brain
reports waiting for your approval. Full six-scene scenario and execution results:
[`kich-ban.md`](../../demo/i2f-chat-den-cua/kich-ban.md).
