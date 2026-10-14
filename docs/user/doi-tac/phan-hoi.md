# Feedback form — partner pilot

Copy the block below into a file or email sent via the private channel established for your team, fill it out, and submit it after **each** guide you run (one submission per guide). Fill out as much as possible:
a partial feedback report is far more valuable than none. **Never paste tokens, passwords, or internal addresses** — replace them with `<token>`, `<home-address>`.

Stopwatch: start timing the moment you open `README.md` in this directory. If someone is observing with you, please measure with `scripts/partner_session_timer.sh`
([`docs/business/doi-tac/buoi-do.md`](../../business/doi-tac/buoi-do.md)); otherwise record an approximation and label it "approximate".

```text
GUIDE:                  (home-assistant-mcp | guard-python | proxy-http)
DATE / SYSTEM:          (OS, Python version, `pip show neuroedge | head -2`)
TARGET PROTECTED:       (which MCP server / API / agent; real device or test double?)

TIMING
  To first working `neuroedge` command (installation complete):   ___ min
  To first BLOCK ("BLOCK đầu tiên" — see gate block):             ___ min
  To first INTENTIONAL ALLOW ("ALLOW đầu tiên CÓ CHỦ Ý" — after opening gate): ___ min
  Total time until protecting real target:                        ___ min   (or: could not protect — why?)

ERRORS ENCOUNTERED (copy verbatim / "NGUYÊN VĂN" message, three lines why/fix if any; with command typed)
  1. Command:
     Message:
     What did you do to resolve it? (or: unresolved)
  2. …

CONFUSING / TIME-CONSUMING (which sentence in guide, which terminology, which missing step)
  -

SURPRISES (good or bad)
  -

GATES YOU OPENED, AND WHY (which tool/route, condition you wrote into gate)
  -

WHAT WILL YOU PLACE GATES BEFORE NEXT (device, tool, system — specify)
  -

TRACE (optional): attach `trace-*.json` — AFTER you inspect it: it contains PARAMETERS of calls (device name, values).
  [ ] I have reviewed, and agree to send.   [ ] I do not send.
```

## Questions helping us decide messaging and pricing (`TODOS.md` #19)

This section is **not** part of technical guides; answer during a short debrief conversation after the pilot if you agree. We use an existing question set
([`docs/business/cong-nhu-cau-2026-10-25/phong-van.md`](../../business/cong-nhu-cau-2026-10-25/phong-van.md)) rather than reprinting it here — asking about what **actually happened** and real costs, not product opinions.
The questions to be asked, and their corresponding sections:

| Topic | Original question | What to record |
|:---|:---|:---|
| Most recent time a device/AI malfunctioned in reality, and what it cost | §4 S2–S3 (Smart Home), related items in §2, §3, §5 | Date, cause, figures **stated spontaneously by the respondent** |
| How dangerous AI commands are currently blocked, prior to having gates | §4 S9 | Current approach, hours spent |
| Budget currently spent on testing tools and device operations | §4 S11 | Specific amount and approver — **do not prompt prices** |
| How much this gate is worth to you, to your team | (new — pilot) | Stay silent, record the figure they say first, and who says it first |
| Who you would recommend this to | §6 E2, E4 | A specific commitment |

Your feedback goes into item #19 of the backlog (`TODOS.md`) and into decisions on messaging/pricing prior to public launch; we will never quote your name without written consent.
