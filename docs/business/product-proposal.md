# NeuroEdge: product proposal

**Status:** current as of Q-92 (2026-10-19). **Owner of this page:** the product owner. This is a
synthesis for a partner, investor or new team member; it is read in about 15 minutes. It **references**
the documents that own each truth and does not copy them (`CONTRIBUTING.md` §8.1): requirements live in
the SRS, dates and progress in `roadmap/neuroedge-roadmap.md` §0.2, business requirements and KPIs in
the BRD, decisions in `roadmap/neuroedge-prd.md` §15 (`Q-N`). Where this page and a source differ, the
source wins; the newest decision wins over an older one. Symbols are decoded in `docs/user/thuat-ngu.md`.

It replaces the historical proposal `docs/business/proposal-blueprint-2026-10-11.md` (Q-72), kept only as
a record of the reasoning at the time (Q-90).

---

## 1. Summary

NeuroEdge is **one product in two halves**: **NeuroClaw**, the brain (an open-source, MIT-licensed chat
agent in its own repository that understands, remembers and talks), and the **NeuroEdge box**, a
rules-enforcing gate that stands between that brain and the physical devices. The brain may only *ask*
for an action; the box decides to execute, to ask a person first, or to refuse, and records every
decision so it can be replayed (`README.md`; Q-83 (6)).

The line (Q-82): **"The Physical AI that really does things, safely by design."** Safety is a property of
the architecture, not of the model behaving well: no verdict token, no action; when in doubt, block.

The experience we are building is a **calm home assistant**: the home looks after itself (a fish tank, a
greenhouse, the air), asks a person only when a rule says so, and is run through chat, with no
configuration (BRD §1, §4). Makers launch first by packaging a device with its rules and brain settings
as a **Blueprint**; families receive the experience through those Blueprints (Q-72, Q-85 (2)).

> Alpha. NeuroEdge is not a certified safety function (no SIL, no PL); gates do not replace emergency
> stops or hardware interlocks (`README.md`). Claims stay honest: most hardware is emulated today, so
> say "built to" until real boards run (Q-82).

## 2. Problem and evidence level

The BRD lists five pains P-1 to P-5 (alert fatigue, context blindness, hand-built schedules, fear of an
LLM driving devices, makers unable to turn DIY devices into products), with the evidence found by the
2026-10-15 market research (BRD §2.1).

**All of them are hypotheses of the team.** No interview has confirmed any pain yet (BRD §2.1, premise P1
of `docs/business/cong-nhu-cau-2026-10-25/README.md`). Only P-4 carries a "high" confidence, because the
market itself has seen the problem; P-5 (makers will pay) is "low". There is no demand gate (Q-92 (1)):
the first adoption signal is the launch's anonymous telemetry (§9; BRD §11 risk 1).

## 3. Customers and launch order

| Segment | Role | Order | Source |
|:---|:---|:---|:---|
| **Families** with several smart devices and no time to configure scenes | Target of the experience | Second, through a maker's Blueprint | BRD §4; Q-85 (2) |
| **Makers and micro-OEMs** of niche devices (fish tanks, incubators, mushroom houses, produce dryers) | Build and sell Blueprints to families | **First**; the launch and, later, a maker asking to sell (§7) show this group's interest | Q-72; Q-85 (2) |
| Smart-glasses users | - | Deferred (BRD Appendix A) | Q-85 (4) |

Consequence accepted in Q-85 and kept by Q-92: families reach the product through makers' Blueprints,
and a family cannot yet install without a command line (BRD §11 risk 10). The Home Assistant add-on, the
Pi SD-card image with QR pairing and the affiliate BOM page were cut from I2e (Q-92 (2), archived in
`roadmap/archive/removed-tasks.md`); installing the box uses the CLI until the home web exists.

The family's way in comes after the public launch (`docs/app-di-dong/`, Q-91, Q-92 (8)): first the **box
API and a home web** in a browser on the home network (increment I2g: device views, approval cards signed
with a passkey, replay; the same web serves makers as Studio), then a **native iOS and Android app**
(React Native, increment I2h) on the same box API, with approval cards signed with Face ID or a
fingerprint and a device wizard (roadmap §4.3.7, §4.3.8).

## 4. What the product does: three loops

The three loops come from Q-72 and are restated here only as a map.

| Loop | In one line | Owner of the detail |
|:---|:---|:---|
| **Build** | Any MCP client (or the brain) suggests a kit, drafts a mission contract, tries it on `sim`. The standard MCP tool set `propose_mission`, `mission_status`, `explain_block` is the only authoring route; NeuroEdge grades, **a person locks** | TSK-I2d-23, Q-88; `docs/spec/missions.md` |
| **Run** | A 24/7 runtime on the box executes a mission contract: permitted and prohibited actions, time windows, a bounded watchdog, declared data flows, `safe_state` on failure, expiry. Deterministic detectors run first and the LLM is woken only when something happens | Q-87; `docs/spec/missions.md` |
| **Share** | A **Blueprint** packs a device, its rules and brain settings, and replayable evidence into one package with one digest, installed by one command and run on simulation | Q-86; `docs/spec/blueprint.md` |

**Asking a person is a per-action choice, decided by the box.** Each action takes one of three
treatments: *ask first* (`on_block` `ask`, RFC-0006), *act and tell* (a mission obligation `notify`) or
*silent* (the default). The brain only words the message (BR-3, Q-85 (1), Q-90 (4)); this needs no schema
change (Q-90 (4)). Message budgets keep the home from nagging (BRD P-1, NFR-COST-02).

Things the loops deliberately do not do today, each stated by its owner:

- Version 1 enforces mission terms at **skill tier on the box**; the **reflex tier on the chip** waits for
  an RFC changing the `NETR` layout, and the approval card says "reflex on the device: not yet" (Q-87 (2),
  MS-CP-04).
- A Blueprint v1 ships a kit and firmware for **reference boards** and reaches real boards through a pin
  map; from the launch it may carry mission contracts and detectors (BL-FMT-05 amended through the
  `blueprint.v1` RFC, TSK-I2e-01), and the installer approves and locks a contract before anything runs
  (Q-92 (7)).
- The LLM budget is held twice: the box limits how often it wakes the brain, and NeuroClaw keeps its own
  `llm_budget` (Q-87 (1)).

## 5. Architecture in one picture

```mermaid
flowchart LR
    You["You (chat)"] --> Brain
    subgraph Brain["NeuroClaw: thinks, talks, remembers (untrusted)"]
        B1["LLM loop, memory, channels"]
    end
    subgraph Box["NeuroEdge box: decides, acts, proves (trusted)"]
        G["Gate: verdict token, ask / allow / block"]
        M["Mission runtime and detectors"]
        A["Approvals: signed records, own bot"]
        T["Trace and replay"]
    end
    Brain -->|"Profile A: MCP over mutual TLS; Profile B: nc_gate calls"| G
    G --> HAL["Devices through HAL"]
    A -.->|"never through the brain"| You
```

- **Brain versus box (Q-83 (4)).** The box decides, acts and proves (gate, tokens, confirmation, HAL,
  traces, grammar, System 1). The brain thinks, talks and remembers (LLM loop, memory, retrieval,
  channels, reminders, LLM budget). The brain touches the world only through the box (Q-76).
- **Two deployment profiles, one contract (Q-83).** **Profile A, full:** brain and box in separate trust
  domains (one machine under separate OS users, two machines, or the brain on a future cloud), MCP over
  HTTPS with mutual TLS. **Profile B, one chip:** brain and `ne_gate` share one ESP32-S3 image, labelled
  `risk=single_chip` because one chip has no isolation boundary (Q-79). The tool list and `tool-result.v1`
  are identical; only the transport differs. Specification: `docs/spec/deployment_profiles.md`.
- **Approvals never pass through the brain (Q-83 (5), Q-89).** In Profile A the box has its own approval
  bot and signs a record the owner answers; a reply that is not tied to the exact request id confirms
  nothing. Pairing is by a one-time code shown only on the home machine; remote approvals are capped per
  hour and carry `risk=remote_approval` (Q-89). Design: `docs/rfc/0019-ban-ghi-duyet-co-chu-ky.md`.
- **Simulation first (Q-72, Q-84).** Four tiers G1 to G4 (a physical model on `sim`, `linux` with simulated
  peripherals, ESP32 firmware on QEMU or esp-emulator, a Home Assistant route) let the three loops run before buying
  hardware (PRD §4.2, tier table). `sim-virtual` derives a virtual board from what the agent declares, with
  a catalogue of virtual parts and a pin map that carries pin names to a real board, labelled
  `risk=virtual_board` (Q-84 phases A and B; `docs/spec/virtual_parts.md`). The drag-and-drop canvas
  (phase C) is deferred and reopens only with launch data.
- **Open with transparency (Q-73).** The product labels a risk instead of blocking a flow the user chose
  (for example `risk=single_chip`, `risk=virtual_board`, `risk=remote_approval`).

Further reading: `docs/architecture/README.md`, `docs/architecture/vi/00-overview.md`.

## 6. Why it is hard to copy

| Edge | Why it matters |
|:---|:---|
| **The rule runs on a $5 chip** and the gate is deterministic | A platform-side list of forbidden actions is coarse and cloud-bound; this is conditional on sensor facts and works offline (BRD §2.2) |
| **Replayable traces** | Every verdict can be re-run on `sim`, `linux` and the chip and must agree (`neuroedge record`, `replay`, `verify`) |
| **Blueprint with evidence** | A maker packs rules and replayable proof, not just a configuration; nothing from a package runs before the person approves its summary (Q-86 (1)) |
| **Asks a person only when the rule says so** | Not every time; this answers alert fatigue (BRD P-1) |

Honest competitive picture (BRD §2.2, not copied here): Alexa+, Gemini for Home and Google Home MCP add
context and platform-side limits; Home Assistant with LLMs is experimental and has no conditional gate;
**Spatial OS is the closest competitor** on the thesis (typed actions, simulation before action, deterministic
safety layer on Home Assistant). NeuroEdge intends to travel *with* Home Assistant (RFC-0018, the route in tier G4), not replace it; the
add-on itself was cut from the pre-launch scope (Q-92 (2)). Q-85 records head-on competition with Alexa+ and Gemini for Home as a
**very high** risk. None of this edge is proven with users yet (§2).

## 7. Business model: hypotheses

No price is stated before launch data (BRD §9). Each revenue line opens on a recorded condition:

| Hypothesis | Opens when | Constraint |
|:---|:---|:---|
| **H1** kit commission (affiliate BOM) | Cut from I2e (Q-92 (2)); returns only by a new `Q-N` | FR-BP-07; would sit on a separate page outside the kit |
| **H2** paid Blueprint Hub | When a maker asks to sell (Q-92 (10), FR-BP-10) | A free static index comes first (FR-BP-05); signed evidence (`TODOS.md` #1) before the Hub takes money |
| **H3** NeuroEdge Cloud (brain run for people who do not want to operate it) | On launch data showing people stuck installing the box (Q-74 step 2, Q-92 (8)) | Gate, approvals and trace always stay at home; keys never leave the box |
| **H4** commercial licence for companies embedding the core | When the first business asks (Q-92 (10), `TODOS.md` #44) | The core stays **PolyForm Noncommercial 1.0.0** (Q-45); the launch is free for non-commercial use; selling Blueprints or devices is commercial use and needs a licence. Specs and schemas are Apache-2.0 (`LICENSING.md`) |

**Tokens (Q-90 (5)).** Bring-your-own-key is the default. NeuroEdge Cloud may bundle tokens only if Q-74
step 2 opens **and** a new `Q-N` amends N4; until then nothing in this proposal resells tokens.
**Deferred (Q-85 (4), Q-92):** wearables, the paid Hub, NeuroEdge Cloud, commercial licence terms; each
opens on the trigger in its row. No revenue line sits on the safety path (Q-72).

## 8. What exists today and what is planned

What works is listed in `README.md` ("Working today") and, in the words of a person using it, in
`docs/architecture/vi/00-overview.md` §6.1. In short: rules on a laptop with virtual devices, on Linux
with emulated pins and on an emulated ESP32-S3 (QEMU); chat through Telegram to NeuroClaw to switch a
light or open a door with owner confirmation, shown in a live demo; a virtual board with a pin map and
two extra demo scenarios (a greenhouse and a fuller fish tank) on `sim-virtual`.

**Planned, not done:** the mission core and 24/7 runtime (I2d), the trimmed Blueprint and its install
flow (I2e), the box API and home web (I2g), the native app (I2h), the code of signed approval records and the box's own approval bot (TSK-I2d-12; design approved in RFC-0019),
real hardware boards (v1.0, I7), and everything in §10. Status and dates per increment are in
`roadmap/neuroedge-roadmap.md` §0.2 and are not repeated here. The fish tank Blueprint is the first
target and can already be shown on `sim`, `linux`, QEMU and esp-emulator (roadmap §0.3, TSK-I2d-28; spike
`docs/reports/esp-emulator-spike-2026-10-19.md`).

I2e starts without waiting for I2d's mission core: it needs the `blueprint.v1` RFC (TSK-I2e-01) and the
fish tank agent (TSK-I2d-28); the I2d mission core is part of the public launch, not a prerequisite of I2e
(Q-90 (1), Q-92 (4)).

## 9. Launch path and adoption signal

**There is no demand gate** (Q-92 (1)). The 2026-12-06 milestone and the conditions B6, B7 and B8 were
deleted, and the BRD's K1 to K3 went with them. What replaces it:

- **Public launch (I6, PyPI 0.6)** needs I2d with its mission core, the trimmed I2e, and I3 and I3a
  verified on Espressif's **esp-emulator** in place of a board. It does not wait for boards or licence
  terms (Q-92 (4)). Before launch the runtime runs 3 days continuously without error plus a stress test on
  simulation (Q-92 (6)). Firmware of the 0.6 line is labelled "verified on esp-emulator" and has no secure
  boot (Q-92 consequences).
- **v1.0 (I7)** keeps the real-board checks an emulator cannot prove: secure boot, flash encryption, the
  24-hour and two-week runs, the camera, physical pins and power loss (Q-92 (5)).
- **First adoption signal** is the launch's anonymous telemetry, on by default with a first-run notice and
  a one-command opt-out (FR-TEL-01; Q-92 (1)).
- **KPIs kept:** **K4**, LLM cost under 2 USD for a 30-day fish tank scenario (NFR-COST-01), and **K5**,
  non-urgent messages inside the budget and no action reaching a device without the gate (NFR-COST-02).
- **Accepted consequences:** no demand signal before the launch; hardware demand cannot be measured until
  boards exist (Q-92).

The positioning line is a check, not a gate: if fewer than 3 of 5 maker interviews retell it in their own
words, it is revisited (Q-82); interviews are handled outside the roadmap.

## 10. Out of scope and removed

Removed from the roadmap by Q-77 (voice code on the host stays): **voice** (I4, I5), **NeuroEdge Lab**
(I4a, I5a; replaced by the MCP tool set, Q-88), opening the target list to third parties, **Fleet OS** and
self-hosted provider (I9, I10), robots (I14), **Jetson** (I16), multimodal and the device ecosystem, and all
post-Beta increments. Deferred (Q-85 (4), Q-84, Q-92): **wearables**, the **paid Hub**,
**NeuroEdge Cloud** and the ESP32 cloud tier (I2f, with exceptions Q-79 and Q-83), commercial licence
terms, and the virtual-parts **canvas**, each on its trigger (§7). Cut from I2e by Q-92 (2): the affiliate
BOM page, the Home Assistant add-on, the Pi SD image and the Pi + ESP32 scaffold. The home web (I2g) and
the native app (I2h) follow the public launch (§3).

**Each of these reopens only by a new `Q-N` with data** (Q-77; roadmap §6; PRD §14). Studio (TSK-I1-04)
remains paused, not removed.

## 11. Top risks

Full registers: `roadmap/neuroedge-prd.md` §13.2 and `docs/business/brd-ambient-intelligence.md` §11.

| # | Risk | Where recorded |
|:---:|:---|:---|
| 1 | **Demand unproven**: no interview has confirmed a pain, and no gate tests it before launch (Q-92) | BRD §11 #1; PRD R-5, R-10 |
| 2 | **Big platforms add safety layers themselves** (Alexa+, Gemini for Home, Google Home MCP); rated very high | BRD §11 #2; Q-85 |
| 3 | **Spreading thin** for one person and AI: three loops becoming three products | PRD R-8; BRD §11 #9 |
| 4 | **Families cannot install yet**: the product needs a command line until the home web (I2g) | BRD §11 #10 |
| 5 | **Unreviewed seller code and users approving without reading** (activation runs seller `@action` code after consent; approval card is at most 5 lines) | PRD R-14, R-15; Q-86 (1) |

Also recorded: the name "Blueprint" collides with Home Assistant Blueprints (BRD §11 #4); evidence is
unsigned in the MVP (PRD R-17); and the brain rests on an early upstream project, which is why NeuroClaw
is a hard fork with its own CI (BRD §11 #8, Q-78).

## 12. Open decisions

| Decision | Where it stands |
|:---|:---|
| **Name "Blueprint"**: keep or rename | Kept through I2e; decided before the Hub is published, on maker feedback (Q-85 (5)) |
| **Reflex tier on the chip** | Needs an RFC on the `NETR` layout; until then skill tier only (Q-87 (2)) |
| **Conditional safety for shipped boards** | An RFC (TSK-I2d-02) must define `safe_state` and interlocks before a Blueprint may carry a board profile (Q-86 (2)) |
| **Home web and app** | Decided (Q-91, Q-92): I2g (box API and home web) after the launch, then I2h (native app); four RFCs to write (pairing and biometric approval source, `board.v1` value limits, the yellow zone, locking app-generated gates) |
| **Local-only approval gates** | Wait for TSK-I2d-20; today every `ask` may be answered remotely within the cap (Q-89 (3)) |
| **Cloud, paid Hub, licence terms, wearables** | On the triggers in §7, by a new `Q-N` where one is needed (Q-85 (4), Q-92) |
| **Positioning line** | A check against interviews, not a gate (Q-82) |

## 13. Sources

| Topic | Owner |
|:---|:---|
| Decisions, requirements, risks, out of scope | `roadmap/neuroedge-prd.md` §15 (Q-72 to Q-92), §11.2, §13, §14 |
| Progress, dates, increments | `roadmap/neuroedge-roadmap.md` §0.2, §0.3, §6 |
| Business requirements, competitors, KPIs, hypotheses | `docs/business/brd-ambient-intelligence.md` |
| Missions | `docs/spec/missions.md` |
| Blueprint | `docs/spec/blueprint.md` |
| Two deployment profiles | `docs/spec/deployment_profiles.md` |
| Virtual parts and pin map | `docs/spec/virtual_parts.md` |
| Signed approval records | `docs/rfc/0019-ban-ghi-duyet-co-chu-ky.md` |
| What works today | `README.md`; `docs/architecture/vi/00-overview.md` §6.1 |
| Licence | `LICENSING.md`, Q-45 |
| Home web and app (Q-91, Q-92; I2g, I2h) | `docs/app-di-dong/README.md` |
| Historical proposal (superseded) | `docs/business/proposal-blueprint-2026-10-11.md` |
