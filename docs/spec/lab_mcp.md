# NeuroEdge Lab — sections still cited

> **Historical design note, trimmed.** NeuroEdge Lab was removed from the roadmap by Q-77, and Q-88 moved
> its live parts into I2d; the standard MCP tool set (TSK-I2d-23) replaces it. Only the four sections that
> live specifications, RFCs and tests still cite are kept, under their original numbers: §2 (boundary with
> the safety tier), §7 and §7.1 (physical safety envelopes and their regression contract), §8 (read-only
> I2C bus) and §12 (event-based triggers). The full note is in git history.
>
> This file carries no schedules, statuses or exit criteria: tasks live only in
> [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md). Codes are defined in
> [`docs/user/thuat-ngu.md`](../user/thuat-ngu.md).

---

## 2. Boundary with safety tier

### 2.1 Three things NeuroEdge Lab must not touch

| Item | Why |
|:---|:---|
| `schemas/gate.v1.json` | Envelopes declared in `board.v1`, not in gates. Gates preserve purity (invariant #4) |
| Gate resolution semantics (`gate_resolver.py`, `constraints.py`) | Lab gates are standard gates; no new inheritance rules |
| Locked gates in `digests.lock` | Draft gates do not enter `digests.lock` until approved. Modifying locked gates still requires an RFC (CONTRIBUTING §3) |

`extends` rejects pre-release versions, preventing gates from extending drafts. This is
intended behavior.

### 2.2 Human confirmation

- Q-26: `mcp` and `system_two` cannot confirm `ask`. Neither can source `trigger`.
- Humans present beside boards confirm via `POST /confirm` on Lab Monitor (same-origin).
- Lacking device channels, lab gates use `deny`, not `ask`.

### 2.3 Software limitations upon shutdown

Libgpiod releases lines on process exit, and *"it should not be assumed that a line will retain its state"* ([gpioset](https://libgpiod.readthedocs.io/en/latest/gpioset.html)).

| Shutdown mode | Restores pins to safe state? |
|:---|:---|
| Normal exit, SIGINT, SIGTERM | **Yes**, via `hal.close()` (TSK-N2-03) |
| Crash, SIGKILL | **Cannot be guaranteed by software.** Lab README must explicitly state requirement for pull-down resistors or hardware watchdogs |

### 2.4 Clients with shell (Q-71)

Claude Desktop only calls tools. Claude Code — and any client capable of running commands — can additionally write
files and execute `gpioset`, `i2cset`, and `git`. NeuroEdge cannot prevent those processes; safety
resides in two boundaries clients cannot bypass via software:

| Boundary | Enforcement | If absent |
|:---|:---|:---|
| **Device privileges separated from client** | Only `mcp serve` process holds `gpio`/`i2c` privileges. Primary path for shell-capable clients: **stdio over SSH** to board host, with forced command key `restrict,command="neuroedge mcp serve …"` in `authorized_keys` (`restrict` disables port, agent, and pty forwarding — `command=` alone is insufficient). Two other paths: `mcp serve` under dedicated user on same host, client user not in `gpio`/`i2c` groups; or `mcp serve --http` — only when client presents mTLS client certificates and cert-bound tokens (`threat_model.md` §2b), unverified with Claude Code (TSK-N0-08). Unneeded on `sim` lacking physical devices | Client runs `gpioset` directly — gates become decorative. `neuroedge lab doctor` warns when running user can access devices (TSK-N0-08); cannot detect `sudo` or alternate users available to client |
| **Policies loaded from approved tree** | `mcp serve` on real board loads gates, board profiles (including envelopes), and `agent.toml` from approved checkout **unwritable** by client user. `-draft` drafts and draft board profiles not loaded on real boards prior to locking; on real boards, lab actions run under locked gates and envelopes | Client edits policy enforced by `mcp serve` — rendering device privilege separation meaningless. Envelopes "blocked by HAL" are only trustworthy when profiles are not client-written |
| **Locking exclusively via humans** | Main branch protected, PR requires human approval; `CODEOWNERS` and required workflows running from base branch for `.github/`, `scripts/check_digests.py`, `digests.lock`, `gates/`, and `lab check` code — since clients with shell can edit those exact files in PR to make CI green (TSK-N0-05) | Client self-drops `-draft`, modifies checks, and merges. A loose gate matching schema with bidirectional tests can only be caught by human reviewers |

**Residual risk, explicitly stated:** clients with shell can edit drafts *in local agent directories*
and run them on `sim` or on boards where they possess privileges. `[lab]` and `build --release` (TSK-N1-03)
keep drafts out of release builds, not off user machines. Details:
`docs/spec/threat_model.md` §2c.

---

## 7. Block N2 — Physical safety envelopes

Envelopes include per-pin total duration and frequency bounds declared in `board.v1` (RFC-0007).
Enforcement does not reside in clients: clients propose limits in draft profiles, but on physical boards HAL blocks
per **locked** profiles loaded from trees unwritable by clients (§2.4) — not per draft profiles.

→ Envelope hooks and check order (TSK-N2-01), atomic check-and-reserve policies (TSK-N2-02), safe shutdown hooks (TSK-N2-03), and exit criteria: [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) I2a (§4.3.1), Block N2.

### 7.1 Regression contract

1. No envelope configuration ⇒ `digital_out` identical to before: same error order, invalid pins consume no tokens.
2. Corpus `fixtures/tool_calls/` produces identical results.
3. All profiles in `boards/` valid against `board.v1` with new fields.
4. `verify` preserves verdict sequences of three canonical traces.
5. `mcp serve` upon exit still records traces and calls `hal.close()`.

---

## 8. Block N3 — Read-only I2C bus

**Removed (Q-77).** The read-only I2C bus itself shipped in I2a (RFC-0007, TSK-I2a-03); the Lab additions below (`lab_scan`, chip detection) are not planned.

N3 builds upon `sensor.read` over `i2c-stub` from TSK-S5-09. HAL scanning surfaces already exist
(TSK-I2a-03); N3 adds chip detection and tool `lab_scan`.

**ADC.** Spike TSK-N3-03 passed (`ads7828`, `ina219` on `i2c-stub`), so `analog.in` reads hwmon
(TSK-I2a-04). `sim` only replays recorded values, without live I2C scanning.

→ Bus scanning (TSK-N3-01), tests on `i2c-stub` (TSK-N3-02): [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) §6.

---

## 12. Block N6 — Event-based triggers

"When X then Y" rules are **agent configuration**, not gate extensions. Each trigger invokes a
**locked** `@action` with gates; lab actions reject source `trigger`. Clients author draft
trigger declarations; `lab_trigger_check` grades them; runtime executes them — even without active client
sessions, so debounce and rate ceilings reside in runtime, not in clients.

Since Q-88 these rules serve the operator runtime's scheduler and detectors, not Lab: the runtime's non-human source is `schedule` (`docs/spec/missions.md` MS-RT-03), and trigger declarations are part of a locked mission contract rather than graded by a Lab tool.

→ Tasks: [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) I2d (§4.3.4), TSK-N6-01 → N6-03 (Q-88); `lab_trigger_check` (TSK-N6-04) in §6.

