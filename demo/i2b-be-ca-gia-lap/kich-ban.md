# Demo script — the fish tank on simulation and emulation

> **Last re-run:** D1, D3/D5 and D4 on 2026-10-15, macOS (Apple Silicon; QEMU in Docker
> `espressif/idf:v5.4` arm64, 87 s with `chay-qemu.sh`), branch `feat/aquarium-demos`. D2 runs on CI only (OrbStack's kernel
> has no gpio-sim). CI: jobs `linux-hal` (`python/tests_linux/test_kit_aquarium.py`) and `aquarium-qemu`
> (`scripts/qemu_aquarium.py`); show their logs, or run `chay-qemu.sh` ahead of the session.
> **Duration:** 10–12 minutes for all five; each scene stands alone.
> **Agent:** [`fixtures/agents/aquarium`](../../fixtures/agents/aquarium/agent.toml): a heater, an
> air pump and a tank light on three relays, one water-temperature probe.

One story on every layer we can run without hardware: **the brain or a person asks, the box
decides, the fish stay safe.** Two rules carry it:

- the heater never comes on in warm water (from 29 °C), or when the probe reports nothing;
- for fish the safe state of the air pump is **on**: turning it off asks the owner at home, and in
  warm water (less oxygen) it is refused without asking.

| Scene | Layer | What it proves | Needs |
|:---|:---|:---|:---|
| D1 | `sim` on the laptop | A day of the tank in 25 s; every decision replays | the repo's `python/.venv` |
| D2 | `linux` on gpio-sim + an LM75 on i2c-stub | The same agent on a real kernel: real GPIO lines, the kernel's temperature driver | a Linux VM, or the CI log |
| D3 | `esp32s3` on QEMU | The same gates on the chip; the chip's decisions replay on the laptop | Docker, or the CI log |
| D4 | `sim` + NeuroClaw (Profile A) | A chat brain asks, the box decides, only the owner at home can say yes | Telegram bot, LLM key |
| D5 | one image of box and brain on QEMU (Profile B) | Brain and gate in one chip, the board's button answers, no network | as D3 |

---

## 0. Preparation

```bash
alias ne="$PWD/python/.venv/bin/neuroedge"     # from the repo root
ne gate lint fixtures/agents/aquarium/gates    # ✓ 5 gate(s) resolved
```

For D4, the chat demo's keys and `.env.txt` as in
[`../i2f-chat-den-cua/kich-ban.md`](../i2f-chat-den-cua/kich-ban.md) §0.

> [!IMPORTANT]
> **What not to say** (and the general table in
> [`docs/business/cong-nhu-cau-2026-10-25/demo.md` §0.1](../../docs/business/cong-nhu-cau-2026-10-25/demo.md)):
> - **No physics model of the tank:** the temperature is what the presenter types or what
>   `mot-ngay.txt` sets, not water warming over time (that is TSK-I2d-15).
> - **No mission contract, no Blueprint:** "trông bể cá giúp tôi" does not yet become a contract
>   (TSK-I2d-05), and the tank cannot yet be packed and installed by others (I2e).
> - **No photo to chat:** vision events carry labels, never pixels.
> - **The relays are the sample boards'** (`gate_relay`, `door_lock`, `porch_light`, renamed in
>   `agent.toml`), and those boards let a relay stay on **at most 60 s** (`max_continuous_ms`) and
>   10 minutes an hour: on `sim` the air pump turns itself off after a minute. That is the board's
>   safety envelope, written for a door lock, not the gate; a real tank kit needs its own board
>   profile (TSK-I2e-05) where the pump may run all day.
> - On QEMU the chip has no probe: `fact water_hot true` is typed in its place.

---

## 1. D1 — "A day of the tank, on a laptop" (`sim`)

### Say
"Morning: 25 °C, we turn on the light, the heater, the air pump. Afternoon sun: 29 °C, and the
heater may no longer come on, whoever asks. 31 °C: someone wants the air pump off; warm water
holds less oxygen, so the box refuses without even asking. Then the probe breaks: no reading, no
heating. Evening, 24 °C: turning the pump off asks the owner; the first time they say no, the
second yes."

### Type
```bash
bash demo/i2b-be-ca-gia-lap/chay-sim.sh          # add --ui to show the live page too
```

### See
```text
✓ ALLOW light@1.0.0 → tank_light_on()
✓ ALLOW heater_on@1.0.0 → tank_heater_on()
✓ ALLOW aerator_on@1.0.0 → tank_aerator_on()
neuroedge>   temperature = 29
✗ BLOCK heater_on@1.0.0 (reason: condition_not_met, criterion: water_hot)
✓ ALLOW heater_off@1.0.0 → tank_heater_off()
neuroedge>   temperature = 31
✗ BLOCK aerator_off@1.0.0 (reason: condition_not_met, criterion: water_hot)
neuroedge>   temperature = lỗi
✗ BLOCK heater_on@1.0.0 (reason: criterion_unavailable, criterion: water_hot)
neuroedge>   temperature = 24
✓ ALLOW heater_on@1.0.0 → tank_heater_on()
✗ BLOCK aerator_off@1.0.0 (reason: condition_not_met, criterion: owner_confirmed)
  ? confirm confirm_1: type có to continue, không to cancel · 10 s left · only a person on the device can answer
neuroedge> answer to the pending question (declined)
…
neuroedge> answer to the pending question (confirmed)
  ✓ ALLOW aerator_off@1.0.0 → tank_aerator_off()
…
--- replay of …/be-ca-mot-ngay.json: the same facts in, the same decisions and pin commands out
│  6 │ aerator_off@1.0.0 │ BLOCK    │ BLOCK    │ condition_not_met     │
│  7 │ heater_on@1.0.0   │ BLOCK    │ BLOCK    │ criterion_unavailable │
…
✓ decisions match the recording
```

### Highlights
- No BLOCK moved a pin: the pin table under each line shows it.
- At 31 °C the gate's message is shown but **no question opens** (no `? confirm` line): a yes
  could stand in for `owner_confirmed` only, and `water_hot` fails too.
- A broken probe is not "cool water": the heater stays off (`criterion_unavailable`).
- The whole day replays from its trace to the same verdicts and pin commands.

---

## 2. D2 — "The same tank on a real Linux kernel" (`linux`, gpio-sim + i2c-stub)

### Say
"Now the same agent, unchanged, on a Linux kernel: the relays are real GPIO lines, and the
temperature comes from the kernel's LM75 driver, the chip a Pi would read. We write the
temperature into the chip's register and the gate sees it through the driver."

### Type (a Linux VM whose kernel has `gpio-sim`, `i2c-stub` and `lm75`; OrbStack's has none of them, so on a Mac show the CI log instead)
```bash
bash scripts/setup_gpio_sim.sh && bash scripts/setup_i2c_stub.sh   # as CI does; export the NEUROEDGE_* lines they print
cd python && python -m pytest -q tests_linux/test_kit_aquarium.py
```
CI: job `linux-hal` of `.github/workflows/ci-sim-linux.yml`, step "LinuxHAL against the kernel lines".

### See
```text
tests_linux/test_kit_aquarium.py ..                                       [100%]
```

### Highlights
- `gate_relay`, `door_lock`, `porch_light` are read back from sysfs by the test, independently of
  the process that drives them: warm water leaves the pump's line at 1.
- A pulled probe (a device the kernel does not have) keeps the heater off and the pump on.

---

## 3. D3 — "The gate on a $5 chip" (`esp32s3` on QEMU)

### Say
"The same five gates, compiled into the firmware of an ESP32-S3, running in an emulator. There is
no water probe in the emulator, so I type the reading the probe would give. Everything the chip
decides is written to its serial port, and the laptop replays it to the same decisions."

### Type
```bash
bash demo/i2b-be-ca-gia-lap/chay-qemu.sh --console    # or open the CI job aquarium-qemu
# on the chip's console:
fact water_hot true
button tank_heater_on
button tank_aerator_off
fact water_hot -
button tank_heater_on
```

### See (from `scripts/qemu_aquarium.py`)
```text
The fish tank on one chip, on QEMU: every step passed
  cool water: heater, air pump and light on
  warm water: heater refused, air pump kept on, nothing asked
  no reading: heater refused (criterion_unavailable)
  cool water: the button's yes turned the air pump off; heater off
NE_BUTTON {"tool":"tank_heater_on","status":"BLOCK","gate":"heater_on@1.0.0","reason":"condition_not_met","failed_criterion":"water_hot",…}
  ok  9 run-time sessions replay to the same verdicts and pins
```

### Highlights
- The chip and the laptop give the same result object for the same facts
  (`python/tests/test_aquarium.py::test_the_chip_decides_as_the_box_does`).
- `fact` exists only in the QEMU build; on a board a fact the HAL does not read is absent, and the
  gate fails closed.

---

## 4. D4 — "Chat with the tank" (`sim` + NeuroClaw, Profile A)

### Say
"A chat brain on another machine, or on this one, talks to the box over MCP with mutual TLS. It can
ask for anything; the box decides. When it asks to turn the air pump off, the box tells it a
question is waiting, and only the person at home, on the box's page, can answer."

### Type
```bash
python/.venv/bin/python demo/i2f-chat-den-cua/tao-khoa.py --out ~/neuroedge-demo-khoa --renew-token
                                                        # tokens live 7 days now (DP-A-04): renew first
NEUROEDGE_DEMO_AGENT=fixtures/agents/aquarium/agent.toml \
  bash demo/i2f-chat-den-cua/chay-hop.sh --local       # the box; open the printed #c=… link
bash demo/i2f-chat-den-cua/chay-nao.sh localhost:8443   # the brain (NeuroClaw), on Telegram
bash demo/i2f-chat-den-cua/chay-nao.sh localhost:8443 agent -m "…"   # or one sentence, no Telegram
```
Then: "Bể cá đang 25 độ. Bật máy sưởi giúp tôi." · on the page, `:sensor temperature 31` ·
"Tắt máy sục khí của bể cá đi." · on the page, `:sensor temperature 24` · "Nước đã nguội rồi, tắt
máy sục khí giúp tôi.", then **Đồng ý** on the page.

### See (re-run 2026-10-15 on this laptop, `agent -m`, OpenRouter model of the demo config)
```text
🦞 ✅ **Máy sưởi đã bật thành công!**
🦞 ❌ **Không thể tắt máy sục khí lúc này.**
Hệ thống từ chối vì lý do an toàn:
- **Nước quá nóng**: … Khi nước nóng, việc tắt sục khí sẽ làm cá thiếu oxy, gây nguy hiểm.
🦞 ⏳ **Đang chờ xác nhận từ chủ nhà...**
… chỉ **chủ nhà mới có thể xác nhận trực tiếp tại trang điều khiển NeuroEdge tại nhà**.
Tôi không thể xác nhận thay bạn được, ngay cả khi bạn nói "có" ở đây.
```
The box's trace of that run (`neuroedge replay` → `✓ decisions match the recording`):
`tank_heater_on` ALLOW · `tank_aerator_off` BLOCK at 31 °C, no question opened · at 24 °C BLOCK,
`tool_confirm_requested confirm_1` · `tool_confirmed source=ui` → ALLOW, `door_lock` off.

### Highlights
- The brain never answers the question (Q-26); the page needs the per-run key (DP-A-02).
- The brain's words vary with the model; the decisions do not. At 31 °C it said "29°C", the
  threshold in the gate's message, not the reading: the brain never sees the probe.

---

## 5. D5 — "Brain and gate in one chip" (Profile B on QEMU)

### Say
"The cheapest form: one ESP32-S3 holds both the chat brain and the gate. The emulator has no
network, so no chat here, but the board's own button still goes through the gate, and the
question about the air pump is answered on the board, not by the brain."

### Type
The image of D3 is already this one (`--brain neuroclaw`): `NE_BRAIN SELFTEST PASS tools=6` at
boot, then `button tank_aerator_off` with `fact water_hot false`, and `button confirm_N yes`.

### See
```text
NE_RISK risk=single_chip
NE_BRAIN SELFTEST PASS tools=6
NE_BUTTON {"tool":"tank_aerator_off","status":"BLOCK",…,"on_block":"ask","confirmation":{"id":"confirm_1",…}}
NE_PIN pin=door_lock level=0
NE_BUTTON {"tool":"tank_aerator_off","status":"ALLOW"}
```

### Highlights
- `risk=single_chip` is printed at boot: brain and gate share one chip, a labelled trade-off (Q-79).
- Updates of this image over OTA, rollback included, are shown with the chat demo's image in the
  CI job `brain-firmware`.

---

## FAQ

- **Why not 30 days of water in a few seconds?** That needs a physics model of the tank (TSK-I2d-15);
  today the readings are typed or scripted.
- **Why does the air pump turn itself off after a minute on `sim`?** The sample board's envelope for
  that relay; see "What not to say".
- **Can the brain lie about the temperature?** No: a value inside a call never becomes a fact
  (DP-B-05); the gate reads the probe (or, on QEMU, the console).
