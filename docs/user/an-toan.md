# How NeuroEdge keeps an AI from doing the wrong thing

A plain-language summary for makers, families and business readers. It summarises rules defined
elsewhere and adds none. The rules are in [`docs/spec/threat_model.md`](../spec/threat_model.md)
and [`docs/spec/deployment_profiles.md`](../spec/deployment_profiles.md); if this page and those
files ever disagree, those files are right.

## The rule in one sentence

**The AI can ask; only the box decides; only a person approves what cannot be undone.**

## Three parts, three levels of trust

| Part | What it does | Trusted? |
|:---|:---|:---|
| **The brain** (NeuroClaw, Claude or any MCP client) | Talks with you, understands requests, remembers and plans | **No.** It may misunderstand you or be tricked by text it reads |
| **The box** (NeuroEdge, on a laptop, a Raspberry Pi or an ESP32-S3 chip) | Decides whether each action may happen and drives the pins | **Yes.** It is small, follows written rules and works without the internet |
| **You** | Approve actions that cannot be undone | The only one who can say yes to them |

The brain never touches a wire. It can only ask the box to run a named action, such as
`light_on` or `front_door_unlock`, and the box checks every request the same way.

## What happens to every request

1. **The box reads the facts itself**: sensors, the clock, your settings. A value the AI puts in
   its request is never treated as a fact.
2. **The gate decides.** A gate is a short file written for each action ("unlock the door only
   for the booked room, only when the guest is verified"). There are three outcomes:
   - **ALLOW**: the action runs once. A one-time token opens exactly that pin, then closes.
   - **ASK**: the action waits for a person (see below).
   - **BLOCK**: nothing moves, and you are told why.
3. **Physical limits still apply after ALLOW.** Each pin has an envelope, such as "the lock
   stays open at most 30 seconds" or "the pump runs at most 10 minutes an hour". It can only
   refuse, never allow, so a badly written gate still cannot overheat a motor.
4. **Turning things off is always allowed.** Moving toward the safe side, such as switching
   off or stopping, never needs permission.
5. **Every decision is written down.** The trace can be replayed later
   (`neuroedge verify`) and gives the same verdict, so you can check what happened and why.

If anything is unclear, such as a missing sensor, a broken rule or a lost network, the box
**blocks**. It never guesses in favour of acting.

## Who can say yes

A question that needs approval can only be answered by a person, never by the AI or by
another program. Depending on how you run NeuroEdge, that person answers with:

- a page on the home network, or the box's own approval bot;
- a button on the board, or the owner's Telegram button;
- on the all-in-one chip, a touch on the approval card or a fixed command word such as
  "đồng ý", spoken while the card is on screen. Speech turned into text by a cloud service
  never counts as a yes.

Each question can be used once and expires.

## Labels instead of hidden risks

NeuroEdge does not stop you from choosing a riskier setup. It tells you, at every start and in
`neuroedge status`:

- `risk=single_chip`: the AI and the box share one chip. Mistakes by the AI are still caught,
  but a bug that takes over the AI's code could take over the box too.
- `risk=readable_flash`: secrets on the chip are not encrypted yet; someone holding the board
  could read them.

## What NeuroEdge does not promise

- It is **not certified for functional safety**. It is not a replacement for a hardware
  interlock on a machine that can hurt someone.
- It does not protect against someone with the board in their hands and lab tools.
- Gates are only as good as what they say. A gate that allows too much will be followed.

## Read more

| Question | Where |
|:---|:---|
| The exact path from a decision to a pin, and every threat considered | [`docs/spec/threat_model.md`](../spec/threat_model.md) |
| How the two ways to install differ (separate brain, or one chip) | [`docs/spec/deployment_profiles.md`](../spec/deployment_profiles.md) |
| How a gate is written and checked | [`huong-dan.md`](huong-dan.md) · `neuroedge gate lint` |
| What works today and what is planned | [`trang-thai.md`](trang-thai.md) |
