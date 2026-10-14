# RFC-0018: Remote Actuators and Auto-Off Levels

| | |
|:---|:---|
| **RFC Code** | 0018 |
| **Title** | Remote actuators (Home Assistant, ESPHome, Matter…) as a HAL actuator type provided by `neuroedge.actuators` plugins: declared in `agent.toml`, drivable only via `_admit` (envelope → token → trace), declaring an **auto-off level** L0–L3 with proof method; communication loss ⇒ uncertain state ⇒ reject turn-on commands; irreversible actions require ≥ L2 |
| **Affected contracts** | `agent.toml` *(new `[actuators.<name>]` section; outside `schemas/`, checked at `neuroedge build` and load time, like `[external]` of RFC-0014)* · safety contract of `neuroedge.actuators` extension point *(Protocol `Actuator` complete signature in §3c, auto-off levels in §3d)* · HAL `_admit` path *(adds a state gate for remote actuators before envelope, §3g)* · `docs/spec/threat_model.md` §1–§2 *(adds rules and rows)* · PRD Appendix B *(broadens causes for NE1003, NE3001, NE3002; no new error codes)* · trace event conventions *(no changes to `trace.v1`)* · new corpus `fixtures/actuators/` · **does not** touch `board.v1` *(alternative touching it: §6, §9 question 1)*, `gate.v1`, evaluation semantics, `NETR`, token ledger, `digests.lock`, three canonical traces |
| **Related PRD requirements** | FR-EXT-02, FR-EXT-03, FR-EXT-07, FR-HAL-01, FR-HAL-05, FR-ACE-02, NFR-SEC-10 |
| **Proposer** | — |
| **Date opened** | 2026-10-04 |
| **Status** | ✅ Approved (2026-10-04) — lead engineer signed off on PR #99; decisions for open questions in §9 (Q-68) |
| **Approvers** | **Lead Engineer — mandatory** (adds rules to path leading to actuators; opens an actuator type whose auto-off guarantee lies on devices outside core control) |

> **When an RFC is required:** `CONTRIBUTING.md` §3. This design **does not** touch any rows in that table (does not edit `schemas/`, evaluation semantics, three canonical traces, `digests.lock`, `NETR`);
> an RFC is still mandatory because Q-67 decision 5 requires it, because it adds rules to the "single valid path" of `threat_model.md` §1, and because it defines the safety portion of the extension point that `neuroedge.sdk` will freeze (FR-EXT-09).
> If §9 question 1 chose declaring in `board.v1`, this RFC would touch the first row of §3 (modifying `schemas/board.v1.json`). Task: **TSK-I2c-04** (this RFC), **TSK-I2c-16** (implementation and first Home Assistant adapter); dependencies:
> TSK-I2c-09 (readback facts), TSK-I2c-11 (plugin loader), TSK-I2c-12 (compliance test suite). Foundational decisions: `neuroedge-prd.md` §15 **Q-67** (decision 5: remote actuators have auto-off levels, "no auto-off" level forbidden for irreversible actions),
> **Q-62** (safety-direction commands never blocked; mandatory auto-off; durable envelope store; out-of-process supervisor), **Q-65** (RFC-0014: numeric facts, age measured by receiver, missing ⇒ BLOCK), Q-57 (highest safety), Q-53, Q-38.
> Closes design portion of `TODOS.md` #55. Related: RFC-0016 *Standalone Safety Core and Extension SDK* (loader, plugin enablement, compliance framework; `Actuator` signature settled in §3c here), RFC-0017 *Namespaced Call Sources and Client Identities* (unaffected by this RFC: commands to remote actuators carry no dedicated `source`, running after gate verdict like any pin command).

## 1. Problem

Today, a physical action targeting Home Assistant, ESPHome, or Matter has only one path permitted by `docs/spec/tool_calling.md` §10 rule 2: wrap it in an `@action` with a gate, and the **function body** calls MCP or HTTP of that system. The gate decides *before* the function body — and nothing more. The gap lies in the fact that tokens, envelopes, and auto-off guard only one destination type: board pins:

1. **Token.** `Conversation._do` issues a token then executes `spec.fn(**kwargs)` under `digital.grant` (`python/neuroedge/actions/conversation.py:210–224`). The token is meaningful only when someone calls `TokenLedger.authorize` (`actions/token.py:116`), and only two places call it: `HardwareAbstractionLayer._admit` (`hal/__init__.py:270`) and `MotionController._command` (`hal/motion_core.py:474`). An `httpx.post(...)` inside the function body does not traverse HAL, never touching the token ledger.
2. **Envelope and auto-off.** `SafetyEnvelope.reserve` is called only from `_admit` (`hal/__init__.py:259`) and motion's `_command` (`hal/motion_core.py:463`). Auto-off timers are `HardwareAbstractionLayer._auto_off` (`:215`) and `LinuxHAL._arm` (`hal/linux.py:863`), both bound to board pins. The supervisor process holds only **gpiod lines** (`hal/linux.py:451–466`; `hal/supervisor.py:4–20`): it cannot reach a remote device.
3. **Traces.** `actuator_command` is emitted by HAL (`hal/sim.py:443`, `hal/linux.py:753`). Commands sent from function bodies leave zero traces of physical effects, let alone true device state.

| Destination | Gate | Token | Envelope | Auto-off / Supervisor | Effect trace |
|:---|:---:|:---:|:---:|:---:|:---:|
| Board `digital.out` pin | yes | yes (`_admit`) | yes | yes (`_auto_off`, supervisor) | `actuator_command` |
| HTTP to Home Assistant in `@action` body | yes (ingress only) | **no** | **no** | **no** | **no** |

Consequence: the "single valid path" (`threat_model.md` §1) holds for pins, but **not yet** for remote devices. Row `External tool with physical effect` in §2b only states effects *must* be an `@action`, not what the body *is allowed to do*.
`TODOS.md` #55 was deferred precisely for this reason: remote devices could not guarantee "auto-off" (Q-62). Q-67 decision 5 conditionally reopened it: permitted, provided each remote actuator declares an auto-off level and the "no auto-off" level is forbidden for irreversible actions.

## 2. Why the Current Mechanism Does Not Solve This

- `board.v1` is closed: `capabilities` and `digital_out` both have `additionalProperties: false` (`schemas/board.v1.json`), leaving nowhere to declare a remote entity; and boards declare **hardware**, not software peers or deployment configuration (same reasoning as RFC-0014 §6). Reference boards are shared across all deployments, whereas Home Assistant URLs and entities are site-specific.
- The primitive set is deliberately closed (FR-HAL-01), and extended primitives must exist across all three targets (Q-53; same reasoning as RFC-0014 §6); `esp32s3` has no plugin loader. A new `remote.out` primitive would violate both rules and fragment the API away from `digital.out`, preventing reuse of existing `@action`s, gates, and `commands.toml` (§6).
- HAL selects backends via `if target == "linux"` (`sim/session.py:917–942`), lacking a registry; RFC-0016 opens extension points, but does not define what an **actuator** extension point must do to maintain safety promises. That is the responsibility of this RFC.
- Existing building blocks are reusable: envelopes locked by **name** (`SafetyEnvelope.__init__(limits: Mapping[str, EnvelopeLimits])`, `hal/envelope.py:272–294`; `reserve(..., primitive=...)`, `:394–403`); tokens locked by pin name from `requires="digital.out:<name>"` (`actions/spec.py:63–64`); `ended(at=…)` (`hal/envelope.py:539`) for an on-cycle terminating at a known timestamp; the `Actuator` Protocol of motion (`hal/motion_core.py:149`) sets precedent for pluggable backends. Missing: a **declaration**, a **driver contract**, a testable **auto-off guarantee model**, and an **uncertain state model**.

## 3. Proposed Changes

### 3a. Scope and Boundaries

A **remote actuator** is an entity controlled by NeuroEdge over a path outside the board (hub, network, external bus), driven by a plugin in group `neuroedge.actuators` (RFC-0016).
To an agent, it is **a named `digital.out` pin** — `digital.out("porch_light").pulse(seconds=…)` — leaving `@action`s, gates, `commands.toml`, and tool checkers unchanged. Scope limits for this release, each with clear rationale:

| Limitation | Rationale |
|:---|:---|
| Only `on`, `off`, `pulse`; **no** `pwm`, `motion.*`, brightness, analog levels | Each requires a dedicated "what blocks it upon communication loss" contract (§9 question 4); conflating them here dilutes the precise meaning of auto-off levels |
| Targets `sim` and `linux` only; `esp32s3` ⇒ `neuroedge build` rejects (`BoardCapabilityError`, NE3001) | No plugin loader on MCU; same reasoning as RFC-0014 §3i. Gateway path belongs to I14 |
| `sim` always uses plugin's **device double**, never touching real devices | A simulation session must never drive a real valve; real device testing belongs on target `linux` |
| NeuroEdge is **not** the exclusive controller of the device | Humans, hub automations, and wall switches independently alter state; NeuroEdge guarantees only what **it** turned on (§3g, "off-debt") |
| Plugins are operator-trusted in-process code (NFR-SEC-10, `threat_model.md` §3) | This RFC guards against **mistakes and hangs**, not deliberate malicious plugin code |

### 3b. Declaration: `[actuators.<name>]` in `agent.toml`; `board.v1` Unchanged

```toml
[requires]
"digital.out" = { pins = ["porch_light"] }     # remote actuator name sits alongside board pins (if any)

[actuators.porch_light]
plugin     = "home_assistant"       # entry point name in group neuroedge.actuators; package must be in [plugins] enable (RFC-0016 §3d)
safe_off   = "L1"                   # level deployer relies upon: L0 | L1 | L2 | L3. Absent ⇒ build rejected
reversible = true                   # absent ⇒ false (irreversible), §3f
[actuators.porch_light.envelope]    # four keys of RFC-0007 §3d, all mandatory
window_s = 3600
max_on_ms_per_window = 1800000
min_interval_ms = 2000
max_continuous_ms = 600000
[actuators.porch_light.config]      # passed verbatim to plugin factory (§3c); construction without I/O
url = "http://homeassistant.local:8123"
entity_id = "switch.porch_light"
token_env = "NE_HA_TOKEN"           # environment variable name, never raw value
```

| Rule (`AgentManifestError`, NE3002, aggregated into `BuildFailed`, NE3003) | Rationale |
|:---|:---|
| Name matches `^[a-z][a-z0-9_]{0,31}$`; no collision with board pins, `enable_pin`, `motion` channels, or other actuators | One name, one destination; colliding with board pins would inadvertently drive physical pins |
| `plugin`, `safe_off`, `envelope` (all four keys, conforming to `$defs/envelope` in `schemas/board.v1.json`, reusing definition) mandatory; `reversible` is `bool`, default `false` | Every remote actuator is an enveloped actuator (RFC-0007 §3d: default is actuator); absent ⇒ assume worst case |
| **Bidirectional:** each `[actuators.X]` must appear in `[requires] "digital.out".pins`; converse (name not on board lacking `[actuators.X]`) triggers existing NE3001 in `check_capabilities` | No extraneous declarations, no dangling pins (same pattern as RFC-0014 §3c) |
| Unknown keys; literal secret fields (`token`, `key`, `secret`, `password`); malformed `*_env` variable names | Reuses `refuse_unknown`, `secret_fields`, `ENV_NAME` from `models/providers/common.py:38,91,117`; `agent.toml` is committed |

Plugin-related rules (`safe_off` exceeding `safe_off_level`, `readback`, `esp32s3`) trigger NE3001 in §3f. Declaration is **a data structure with a single validation function**: `agent.toml` is only one source; any other source constructing it from code (e.g. `neuroedge.guard` API in RFC-0016) **must** call the same function at load time.
Rules are not bypassed when `agent.toml` is absent. Public names for data structure and validator function determined by TSK-I2c-16, pinned in `docs/spec/python_api.md` and `tests/test_public_api.py` (like RFC-0014 §3g).

**Why `agent.toml` rather than `board.v1`:** URLs, entities, auto-off levels, and irreversibility belong to *deployment*, not hardware; editing `board.v1` modifies a frozen schema (RFC-0015) and forces reference boards to carry site-specific configurations. The trade-off: remote actuator envelopes live in `agent.toml` rather than boards as in RFC-0007. They remain **independent of gates and action code** — what RFC-0007 §3d required ("hardware limits must hold even when gates are loosely written"); they are not independent of the `agent.toml` author, who is also the person plugging in the plugin. Decided in §9 question 1.

### 3c. Single Path: `_admit`; Protocol `Actuator`

Remote actuators follow the **exact** pin path, in strict sequence `require_pin → state gate (§3g) → envelope → authorize → record → driver`:

- `digital_out` in `sim` (`hal/sim.py:402`) and `linux` (`hal/linux.py:691`) branches at function entry: remote actuator name ⇒ calls a **shared** base class function (no additional `if target` branching), routing through `_admit` (`hal/__init__.py:231`), then to the plugin. `require_pin` accepts remote actuator names like board pins; `esp32s3` lacks this path entirely.
- **Plugins hold no handles.** Core constructs plugins from declarations; only HAL holds references and calls `apply`/`safe_off`/`read_state`, with `apply` called strictly after `_admit`. Plugins receive no HAL, token ledger, or envelope; agent code receives no plugin (no `digital.out` returns a plugin). Structurally verifiable (§7), fulfilling FR-EXT-03: *actuators are driven by HAL only after tokens and envelopes*.
- **Tokens unchanged.** Turn-on commands spend that pin's token exactly once (`token.py:160–177`); `off` requires no token (RFC-0007 §3d). `ActionSpec.pins` already extracts names from `requires="digital.out:<name>"` (`actions/spec.py:63`), so `VerdictToken` requires no changes.
- **Safety-direction commands.** `off` to remote actuators is always **attempted**, bypassing envelopes, requiring no token, without waiting for `min_interval_ms` (the sole exception of `threat_model.md` §1, now covering this target). State gate §3g only blocks turn-*on* commands.

**Protocol `Actuator` — Single Source of Signature** (`neuroedge.sdk` merely re-exports; RFC-0016 links here). Entry point value is `module:factory(config: Mapping[str, Any]) -> Actuator`, called once, **zero I/O**; invalid `config` ⇒ `ValueError(reason)` which core converts to 3-part NE3002. All methods are **synchronous**, blocking for at most `command_timeout_ms`, and HAL may call them from timer threads ⇒ plugins ensure thread safety internally.

| Member | Signature | I/O | Meaning |
|:---|:---|:---:|:---|
| `safe_off_level` · `readback` | `Literal["L0","L1","L2","L3"]` · `Literal["push","poll","none"]` | no | Highest provable level **for that `config`** (§3d); readback mode (§3e). Declared at construction |
| `tolerance_ms` · `command_timeout_ms` · `max_lease_ms` | `int ≥ 0` · `int > 0` · `int \| None` | no | Maximum deadline-to-off delta; command timeout; lease ceiling (`None` outside L3) (§3d) |
| `apply` | `apply(command: Command) -> None`, `Command(id: str, operation: "on" \| "renew", duration_ms: int \| None, lease_ms: int \| None)` | yes | Called only by HAL, after `_admit`. L2: `duration_ms` always present; L3: `lease_ms`, `renew` = extend; L0/L1: absent. Return = hub/device **acknowledged**, not that it turned on. Errors: `NotSent` · `Rejected` · `Ambiguous` |
| `safe_off` | `safe_off() -> None` | yes | Safety-direction command: **no token, no envelope**, runs even when ledger rejects all, **idempotent** (already off is not an error). Same three errors |
| `read_state` | `read_state() -> tuple[bool, int]` = `(is_on, observed_age_ms ≥ 0)` | `poll`: yes | `push`: returns latest cached value. Age **adds only**, receiver timestamps baseline (RFC-0014 §3f). Not called when `readback = none`. Error: `ReadFailed` |
| `probe` | `probe() -> DeviceDouble` | no | Device double on virtual clock, running through **exact** code paths of above three methods; provides `state() -> bool`, `cut_link()`, `heal_link()`, `advance(ms: int)` (§3e) |
| Errors | `NotSent` (definitely did not reach device) · `Rejected` (hub explicitly refused) · `Ambiguous` (timed out or severed post-send) · `ReadFailed` | | Subclasses of `ActuatorError` in `neuroedge.sdk`; not `NE…` codes, no new error codes added (§3k) |

**What this RFC cannot prevent, stated honestly:** `@action` bodies can still call arbitrary SDKs in Python (same privilege tier as runtime, `threat_model.md` §3). This RFC makes the correct path **cheaper** than the wrong path (declaring three TOML items instead of writing clients) and adds a build warning: an `@action` module importing popular network clients (`httpx`, `requests`, `aiohttp`, `urllib.request`, `socket`) triggers a warning (non-blocking; heuristic, incomplete) recommending remote actuators. This warning is not a bypass prevention mechanism (§5, risk 5).

### 3d. Auto-Off Levels

A level is a promise about **who** returns the actuator to `off` when NeuroEdge can no longer help. Ordering L0 < L1 < L2 < L3; `D = min(command duration, max_continuous_ms)` (as in RFC-0007 §3d; `on()` without duration uses `max_continuous_ms`).

| Level | Who holds timer | `on` carries | **Testable** guarantee | Link loss / NeuroEdge hangs |
|:---|:---|:---|:---|:---|
| **L0** `none` | Nobody | No duration | None. HAL only guarantees no overlapping on-cycles (`already_on`) until turn-off is *confirmed*, and envelope accrues actual on-time up to that point | Device retains state indefinitely |
| **L1** `host` | NeuroEdge process (like `LinuxHAL._arm`) | No duration; HAL schedules `off` at `D` | If runtime survives **and** communication holds: `off` is *sent* within ≤ `D + OFF_SLACK_MS`, retried every `OFF_RETRY_MS` until confirmed. A guarantee of **effort**, not physical effect | Zero guarantees: device may stay on indefinitely |
| **L2** `device_timer` | **Device** | `on` with `duration_ms = D`, **never absent** | Once device receives command, it turns `off` automatically after ≤ `D + tolerance_ms` without requiring further messages | Preserved: even if NeuroEdge hangs, dies, or network drops |
| **L3** `device_lease` | **Device** (lease) | `on` with `lease_ms`; HAL renews every `lease_ms / 3` and **stops renewing** at `start + D − lease_ms` (`D ≤ lease_ms`: single lease lasting `D`, no renewal) | Device turns `off` ≤ `lease_ms + tolerance_ms` after last received renewal ⇒ absolute deadline `start + D + tolerance_ms` | Runtime hangs ⇒ renewal ceases ⇒ turns off, requiring zero "off" messages |

- L2 and L3 **do not discard** L1: HAL still sends `off` upon deadline (§3g) as a defense-in-depth fallback *after* device guarantees, ensuring guarantees are exercised on every execution (§3e).
- L3 lease renewal **is not** the authority renewal of RFC-0011 §3c: it never exceeds `D` reserved by the envelope. Running longer requires another gate pass, blocked by `already_on` until the current cycle finishes.
- `safe_off` in `agent.toml` is the level the deployer **relies upon**, and must not exceed plugin's `safe_off_level` (§3c); exceeding ⇒ NE3001, so a plugin downgrade turns builds red rather than failing silently. Levels are **never guessed or escalated at runtime** (spirit of Q-35: undeclared assumes worst case). `tolerance_ms` is maximum deviation between deadline from HAL send time and actual device turn-off (device timer drift, delivery latency — including `command_timeout_ms` — and readback latency).
- Constants `OFF_SLACK_MS`, `OFF_RETRY_MS`, `max_state_age_ms` decided in §9 question 5 (Q-68).

### 3e. How a Level Is Proven

Two complementary proofs. `neuroedge build` **does not** run P1 (P1 is an RFC-0016 badge prerequisite, and operators select plugins); build checks declarations only. P2 runs at runtime, on every command.

**P1 — Compliance suite against device double** (`neuroedge conformance`, TSK-I2c-12; vectors in `fixtures/compliance/actuators/`). Plugins provide a device **double**, constructed via `probe()` (§3c) and executed on a virtual clock; missing `probe()` ⇒ `unverifiable`, no badge (RFC-0016). Check `actuator.level_proven` executes vectors for declared level (`safe_off_level`) **and** must catch lying doubles (each check has a counter-example):

| Level | Vector (double severs link / freezes runtime) | Counter-example caught |
|:---|:---|:---|
| L0 | Plugin declares no level higher than actual; `on` carries no duration | Plugin claiming L2 whose `on` omits `duration_ms` |
| L1 | Sever link exactly at deadline ⇒ HAL **does not** claim off, enters `uncertain`, retries every `OFF_RETRY_MS` | Plugin reporting "off" before receiving confirmation |
| L2 | (a) `on` always carries `duration_ms ≤ D`; (b) sever link immediately post-delivery ⇒ at `D + tolerance_ms` double is `off`; (c) sever before delivery ⇒ double does not run beyond `D` | Double **ignoring** timer ⇒ vector (b) fails |
| L3 | (a) freeze runtime (no messages) ⇒ `off` ≤ `lease_ms + tolerance_ms`; (b) duplicate or reordered renewals do not push deadline past `start + D + tolerance_ms`; (c) `lease_ms` does not exceed plugin ceiling | Double ignoring lease ⇒ (a) fails |
| All levels | `off_is_idempotent` (calls `safe_off` ≥ 2 times); `off_is_unconditional` (runs when ledger rejects all); `builds_without_io` (socket interceptor); `classifies_errors` (`NotSent` / `Rejected` / `Ambiguous`, §3g); `receives_no_handles` (receives no HAL, ledger, envelope — checks factory signature) | `safe_off` requiring token; plugin retaining HAL reference |

P1 proves **how the plugin constructs commands** conforms to device protocol; it **does not** prove real hardware firmware respects commands.

**P2 — State readback into facts on every run.** For L2 and L3, HAL **does not send its own `off` prior to** `deadline + tolerance_ms` (L2) or `start + D + tolerance_ms` (L3); at that point it reads back state: already `off` ⇒ device auto-turned off as declared (evidence recorded in `remote_state`); still `on` ⇒ device **violated its declared level**: HAL sends `off` (safety direction), transitions to `quarantined`, records `remote_level_violated`. Every command is thus an empirical test of the guarantee, free of manual overhead; maximum exposure window is `tolerance_ms` plus one retry. Without readback (`readback = none`), P2 cannot run: HAL sends `off` at deadline like L1 and **L2/L3 levels rest solely on P1** ⇒ forbidden for irreversible actions (§3f).

Readback state is an RFC-0014 fact: numeric `0`/`1` with `range: { min: 0, max: 1 }`, read timestamp measured by **receiver** on session timeline (plugin adds only `observed_age_ms ≥ 0`, never self-declaring age). In-process plugins bypass sockets and authentication from RFC-0014 §3d; all age and *missing ⇒ BLOCK* rules of §3f–§3i apply fully.
Actuators with `readback` also function as an in-process fact source (TSK-I2c-09) with a 0/1 fact, available for gates via `external_source`. `uncertain` and `quarantined` **never** become numeric values: they represent *missing* facts ⇒ `criterion_unavailable` ⇒ BLOCK.

### 3f. Decision D5: Forbid "No Auto-Off" for Irreversible Actions

**Definition.** `reversible = true` is deployer declaration that *leaving the actuator on until a human notices causes no harm* (heat, water, electricity, mechanics, security, dosage) *and `off` restores prior state* — "reversible and low-risk" is **one** declaration. Everything else, including undeclared, is **irreversible**.
An `@action` is irreversible if its `requires` contains an irreversible remote actuator. Class is declared **once, at the actuator**, not per `@action` (§6).

| `reversible` | Minimum level | Additional condition | Violation |
|:---|:---|:---|:---|
| `true` | L0 or higher (L0 warns at build) | — | — |
| `false` (default) | **L2** (FR-EXT-07: device auto-offs even on link loss) | `readback ≠ none` (otherwise P2 unavailable, §3e) | Lower `safe_off` ⇒ **NE3002**; plugin's `safe_off_level` lower or `readback = none` ⇒ **NE3001** |

Three-part error example:

```
NE3002 AgentManifestError
  where: agent.toml -> [actuators.garage_valve] safe_off
  why:   the actuator is irreversible (reversible is not true) and declares safe_off = "L1": this runtime sends the off, so a lost link or a frozen runtime leaves the valve open
  how:   use a plugin and device kind that reach L2 or L3 and set safe_off to it, or — only if leaving it on harms nothing — set reversible = true (RFC-0018 §3f)
```

Checked in **two places**: `neuroedge build` (`engine/compiler.py`, alongside `check_motion_leases`) and load time (same validator as §3b), ensuring no ingress to HAL bypasses rules. NE3001 also applies when `[actuators]` is present with `--target esp32s3`.

### 3g. State, Communication Loss, and Pre-Envelope Gate

HAL maintains an internal HAL state (not device state) for each remote actuator: `off` (confirmed), `on` (active NeuroEdge on-cycle), `uncertain`, `quarantined`.

- **Turn-on gate.** Commands `on`/`pulse` pass only when state is `off` with read timestamp no older than `max_state_age_ms` (for `readback = none`: see below). Otherwise ⇒ `EnvelopeRefusedError` (NE1003) **prior to envelope and `authorize`** (like `supervisor_unavailable`, `hal/linux.py:720–734`): no reservation, no token spent, records `envelope_refused` with new `reason`s:
  `actuator_state_unknown` (`uncertain` or stale timestamp), `actuator_quarantined`, or `already_on` (readback reports `on` without active NeuroEdge command: avoid overlapping external controller commands).
- **Entering `uncertain`:** command send exceeds `command_timeout_ms`; readback channel severed; read timestamp stale; restart (all knowledge wiped). **Exiting `uncertain`:** **only** via a fresh readback of `off` *after* link recovery — never by timer, never by "waiting long enough", because timers cannot know physical reality.
  Without `readback` (write-only devices; allowed only with `reversible = true`, §3f): `off` is latest confirmed `off`, without age limit. Unexpected `on` readback (late command delivery) ⇒ HAL sends `off` immediately.
- **Off-debt.** HAL sends `off` only when holding *off-debt*: an active turn-on command **issued by NeuroEdge** unconfirmed as off. It never turns off devices it did not turn on, and **does not** send `off` on boot unless durable log (§3h, with `off_owed` flag) records outstanding debt under L0/L1. `off` (via `safe_off()`) is always attempted (including in `close()`), retried every `OFF_RETRY_MS`, never rejected, requiring no token; send failures **do not** raise exceptions to callers (safety-direction commands cannot be trapped behind exceptions), recording `remote_command_failed`.
- **Send failures classified by plugin (§3c), HAL does not guess.** `NotSent` and `Rejected` ⇒ refund reservation (`envelope.refund`) with state unchanged. `Ambiguous` ⇒ **no refund**, enters `uncertain`, reservation remains held: command may have arrived (safe side of uncertainty principle, `hal/linux.py:772–774`, `:821`).
  Turn-*on* commands are never automatically retried (repeating commands without deduplication keys risks double activation); only `off` is retried.
- **`quarantined`** (device violates declared level, §3e): rejects all turn-on commands until operator explicitly clears state log (same location as envelope log, RFC-0007 §3d); no automatic recovery. Unreadable log ⇒ treated as `quarantined`.

### 3h. Envelopes and Supervision

Same four keys and same `SafetyEnvelope` (keyed by name), same `_admit` sequence; `envelope.py` modifies one place: remote actuators are always terminated by **HAL** (`virtual = False` by name, across both `sim` and `linux`), ensuring identical behavior across targets.

| Key | Meaning for remote actuators |
|:---|:---|
| `max_continuous_ms` | Ceiling of `D` (L2 sends `duration_ms = D`; L1 schedules `off` at `D`; L3 halts renewal at `start + D − lease_ms`). Physical ceiling is `D + tolerance_ms` — plugin-declared margin **counted against window**; `neuroedge build` requires `max_continuous_ms > tolerance_ms` (NE3001) |
| `max_on_ms_per_window` | Reservation is `D`; HAL calls `ended(at=…)` at **timestamp it confirms** actuator is off (readback), or at guaranteed deadline (`deadline + tolerance_ms`) for L2/L3 without readback — never earlier. L0 and `uncertain`: cycle *continues accruing* (`_settle`, `hal/envelope.py:610–611`: over-limit on-times extend to current time) — can only reject more, never less |
| `min_interval_ms` | Measured from end of prior cycle per above definition; applies only to turn-on commands |
| `window_s` | As in RFC-0007 |

- **Write-ahead durable logging** as in RFC-0007 §3d (`FileEnvelopeStore`, keyed by actuator name); post-reboot, all remote actuators are `uncertain` until first readback, even with clean logs.
- **Out-of-process supervision (RFC-0007 §3d, Q-62) inapplicable:** supervisor process holds only gpiod lines (`hal/linux.py:451–466`); remote actuator names are **not** in `_supervised`, so `supervisor_unavailable` does not apply. Substitutes by level: **L0, L1 — nothing out-of-process** (L1 timer dies with runtime; why L1 is insufficient for irreversible actions);
  **L2 — on-device timer**; **L3 — on-device lease, where heartbeat is renewal** (hung runtime ⇒ renewal halts). P1 proves runtime freeze scenarios on doubles (§3e).

### 3i. Traces and Replay

`trace.v1` unchanged (open `type`, arbitrary `data`); events added to `docs/spec/simulation_coverage.md` §3 upon implementation:

| Event | Data |
|:---|:---|
| `actuator_command` *(existing, **shape unchanged**)* | `{pin, operation, duration_ms}` — emitted upon command receipt like any pin; `testing/player.py:173` recognizes command points |
| `remote_command_sent` | `{actuator, command_id, operation, duration_ms?, lease_ms?, level, plugin}` |
| `remote_command_acked` · `remote_command_failed` | `{actuator, command_id, latency_ms}` · `{actuator, command_id, kind}`, `kind` ∈ `not_sent` · `ambiguous` · `rejected` |
| `remote_state` | `{actuator, state, via, read_offset_ms}`, `state` ∈ `on` · `off`, `via` ∈ `push` · `poll`; age measured by receiver |
| `remote_state_unknown` · `remote_state_confirmed` | `{actuator, why, since_offset_ms}`, `why` ∈ `command_timeout` · `link_lost` · `stale` · `restart` · `readback_failed` · `{actuator, state, unknown_ms}` |
| `remote_level_violated` | `{actuator, level, expected_off_ms, observed}` |

Semantic lint in `python/neuroedge/trace.py` (like `lint_vision`; violation ⇒ `TraceValidationError`, NE4001): `remote_command_sent` with `operation ≠ off` lacking an immediate preceding `actuator_command` for the same pin in the same step — meaning a remote turn-on command lacking proof of traversing §3c — is an invalid trace.
**Replay relies solely on recorded events:** `ReplaySession` does not construct plugins, read key-bearing environment variables, or open network connections (tested by socket blocking); replay HAL derives state from recorded `remote_state` (`script_remote_state`, mirroring `script_digital_in` / `script_pin_state`, `hal/__init__.py:552`, `:626`), so a turn-on rejected by `actuator_state_unknown` at record time is rejected identically on replay. Events `remote_*` are informational, excluded from verdict matching. Three canonical traces contain no remote actuators, remaining unchanged.

### 3j. First Adapter: Home Assistant (TSK-I2c-16)

**What Home Assistant Provides** (reviewed from `home-assistant.io` and `developers.home-assistant.io` documentation as of 2026-10-04; unread items marked "unverified"):

| Item | Details |
|:---|:---|
| REST | All calls include `Authorization: Bearer <Long-Lived Access Token>`; `GET /api/states/<entity_id>` returns current state; `POST /api/services/<domain>/<service>` returns "states changed **while** service ran" — **not** an effect guarantee on device; status 200/201 and 400/401/404/405; API timeouts: unverified |
| WebSocket | Handshake `auth_required` → `auth` (`access_token`) → `auth_ok` / `auth_invalid`; commands `call_service`, `subscribe_events` (filtering `event_type`), `get_states`; `ping`/`pong` keepalive. Entity state change event name: unverified on reviewed page |
| `switch` service | `switch.turn_on`, `switch.turn_off`, `switch.toggle`; documentation states **no** duration or auto-off parameters |
| `script` | Supports `delay` action and `single`/`restart`/… modes; timer runs **inside Home Assistant**, not on device; behavior across HA reboot: unverified |
| Underlying devices | Matter: command `OnWithTimedOff` (0x42) carries `OnTime` (1/10s units), part of Lighting (LT) feature of On/Off cluster so not universal — third-party cluster docs, **unverified** against official Matter spec. ESPHome: `api.reboot_timeout` (default 15m) reboots when "no client connects to the API" — uncoupled from NeuroEdge renewal so **not** our lease; whether `on_turn_on` action with `delay` executes on-device: unverified |

**Home Assistant Achievable Level.** Across generic `switch.turn_on` / `switch.turn_off`, plugin `home_assistant` declares **L1** for all entities: turn-on carries no duration (unsupported by `switch` service) and timers belong to NeuroEdge. A `script` with `delay` is a hub timer: surviving NeuroEdge crashes but failing on hub crashes or hub-device link loss — **not L2** (L2 requires on-device timers), excluded from D5.
L2/L3 requires device-level protocol duration or lease support (e.g. Matter `OnWithTimedOff`, ESPHome firmware-level timers — both unverified), isolated in dedicated adapter branches **with dedicated P1 vectors**; initial adapter declares neither. Consequence: under Home Assistant, **irreversible actions are rejected at build** (NE3002; NE3001 if claiming L2) — fulfilling FR-EXT-07, not a defect.

Implementation: drives via REST (`POST /api/services/...`) or WebSocket (`call_service`); reads back via `GET /api/states/<id>` polling (`poll`) or `subscribe_events` (`push`); `token_env` as in §3b; service calls returning 200 **do not** flip state to `off` — readback only. Home Assistant state reflects **hub's belief** about the device (potentially optimistic, unverified), so readback cannot catch devices misreporting to hub (§5, risk 2).
Tested via **Home Assistant test double** (minimal REST and WebSocket) executing L0–L1 vectors of §3e; live Home Assistant testing is human gate (roadmap TSK-I2c-16). Reverse path — Home Assistant calling NeuroEdge — is handled by authenticated MCP (Q-58), outside this RFC.

### 3k. Error Codes

No new error codes added. NE1003 `EnvelopeRefusedError` adds `reason`s: `actuator_state_unknown`, `actuator_quarantined` (reusing existing `already_on`); NE3001 `BoardCapabilityError`: `safe_off` exceeding plugin's `safe_off_level`, `readback = none` for irreversible, `max_continuous_ms ≤ tolerance_ms`, `[actuators]` under `esp32s3`, `pwm` or `motion` targeting remote actuator names; NE3002 `AgentManifestError`: §3b and D5 violations (§3f); NE4001 `TraceValidationError`: lint in §3i.
`reason` is excluded from `schemas/error-codes.v1.json` (declares only `fields: ["reason"]`), updating only prose in PRD Appendix B and docstring of `EnvelopeRefusedError` (`errors.py:76`).

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | Yes — `[actuators]` is optional; no existing `agent.toml`, board, gate, or trace in repo contains it. `board.v1` unchanged |
| Do currently invalid files become valid? | Yes, exactly one type: `agent.toml` containing `[actuators.<name>]` conforming to §3b. `agent.toml` has no schema in `schemas/`. *Older `neuroedge` versions reading it ignore the unknown section, but actuator name is absent on board so `[requires]` is rejected (NE3001)* — fail-closed, not breaking |
| Does it require bumping schema version (`v1` → `v2`)? | No. `trace.v1` unchanged (open `type`); `board.v1` unchanged; `error-codes.v1` unchanged |
| Impact on issued gate hashes / signatures? | None — does not touch `gate.v1` |
| Impact on three canonical trace files? | None — no remote actuators; `actuator_command` shape unchanged |
| Does any gate in `digests.lock` change digest? | No gates change |
| Must `NETR` layout or C walker change? | No — `esp32s3` lacks remote actuators (NE3001) |
| Does any expected answer in tool call corpus change? | No — `@action` and tools unchanged; adds corpus `fixtures/actuators/` (valid/invalid + `expected_errors.yaml`, bidirectionally closed; add row to table in `CONTRIBUTING.md` §3) |
| Error codes (PRD Appendix B) | No new codes; broadens causes for NE1003, NE3001, NE3002 (§3k) |
| Public Python API | New public names (declaration, validator function, driver contracts) in `neuroedge.sdk` per RFC-0016, pinned in `docs/spec/python_api.md` and `tests/test_public_api.py`; existing `neuroedge.__all__` unchanged |
| Invariant `sim` no richer than board (`CHANGELOG.md` §3.3 #7) | Inapplicable: remote actuators are not board capabilities; but `sim` doubles must not promise higher levels than plugin's `safe_off_level` (P1) |

## 5. Safety Impact

- **Gates do not become looser, no new paths to actuators:** remote actuators reachable only via `_admit` (§3c); plugins hold no handles; envelopes only reject; tokens unchanged. `gate.v1` and five inheritance principles unchanged.
- **Fail-closed in every direction (`CHANGELOG.md` §3.3 #2):** undeclared `reversible` ⇒ irreversible; undeclared `safe_off` ⇒ build rejected; missing `readback` ⇒ irreversible forbidden; uncertain state ⇒ turn-on rejected; ambiguous send failure ⇒ reservation retained; corrupt logs ⇒ quarantined; level violation ⇒ quarantined. The only relaxed operation is `off`.
- **Safety-direction commands never blocked (Q-62):** `off` to remote actuators is always attempted, requiring no envelope and no token. Gate §3g rejects only turn-*on* commands. The sole exception in `threat_model.md` §1 expands to cover this destination, **without** adding other exceptions (no `[lab]` flags or gate bypass tests).
- **Not certified functional safety (Q-38, `threat_model.md` §3b):** a remote actuator is never an emergency stop button; devices capable of harming humans still require software-independent hardware disconnects.
- **Residual risks — uneliminable in core:**
  1. **Network partitions.** L0/L1: actuators can remain on indefinitely — hence forbidden for irreversible actions and blocked by `uncertain`. L2/L3: turns off within `D + tolerance_ms` on-device; NeuroEdge cannot confirm state until communication recovers.
  2. **Firmware misreporting or hub inaccuracies.** `readback` reflects device/hub assertions. P2 catches devices *contradicting* declared levels; cannot catch devices reporting `off` while physically running. Mitigations: irreversible actuators require independent hardware disconnects; gates combine with core-trusted criteria (RFC-0014 §5 risk 1).
  3. **Clocks.** All sent durations are **relative intervals** (`duration_ms`, `lease_ms`), never absolute wall-clock timestamps: core depends neither on device clocks nor system wall clocks; device timer drift is bounded by `tolerance_ms` (declared by plugin, verified on double by P1 — unverified on real hardware). Stuck commands delivered late: bounded by `command_timeout_ms`; if delivered, subsequent readback seeing unexpected `on` triggers `off` (§3g).
  4. **Co-controllers.** Humans, hub automations, and wall switches independently alter device state; NeuroEdge is responsible only for turning off what it turned on, never shutting down unmanaged actions.
  5. **`@action` body bypasses.** Python cannot prevent network clients called directly inside function bodies; build warnings (§3c) are heuristic only. Same-privilege adversaries are out of scope (`threat_model.md` §3).
  6. **Misdeclared `reversible = true`.** Machine-unverifiable claim; default is `false`, declaration resides in committed `agent.toml` and traces record declared level.
  7. **Malicious or buggy plugins** running in-process (NFR-SEC-10): P1 verifies command construction only, not malicious payloads, and build does not run P1 — non-compliant plugins can load if operator enables them (provenance recorded in traces, RFC-0016 §3d).
- Lead engineer approval required because RFC introduces rules governing paths to physical actuators.

## 6. Alternatives Considered and Rejected

| Alternative | Rejection rationale |
|:---|:---|
| Status quo: remote commands as regular `@action` bodies | §1: no token, no envelope, no auto-off, no effect trace; exactly why `TODOS.md` #55 deferred it |
| Mandating **L3 everywhere** | Commodity devices (bulbs, smart plugs via hubs) cannot achieve it; impractical rules encourage worse `@action` body bypasses. D5 restricts auto-off mandate to irreversible actions |
| New `remote.out` primitive in HAL | FR-HAL-01 closes set; Q-53 mandates three targets; API fragmentation prevents reuse of `@action`, gate, `commands.toml`; RFC-0014 §6 rejected identical argument for `external.in` |
| Declaring in `board.v1` (`capabilities.remote_out`) | Modifies frozen schema; boards represent hardware, not deployment config; reference boards cannot store site URLs/entities; community boards (`--board <path>`) self-attest safety limits. Retained in §9 question 1 |
| Declaring irreversibility **per `@action`** (decorator parameter) | Two actions driving same actuator with different classes allows weaker class to win; declaration in code uncheckable at build time; property belongs to actuator |
| Declaring auto-off level or irreversibility **in gates** | `gate.v1` does not know which actuator it binds to (RFC-0014 §9.8); changes `gate.v1` and digest |
| Trusting declared levels without proof | Turns levels into cosmetic labels; authors/deployers claim higher levels. Requires P1 (command construction) and P2 (runtime empirical readback) |
| Expanding supervisor process to send pre-built `off` commands on lost heartbeat ("supervised L1") | Supervisor is intentionally minimal (gpiod only, `supervisor.py:4–20`); bundling HTTP/TLS clients and credentials compromises core design; still lacks on-device guarantee. Future RFC if needed |
| Refunding reservations on any send error | Ambiguous errors may have delivered command; refunding permits overlapping second activation while first is active |
| Treating hub HTTP 200 as "off/on confirmed" | REST docs: response reflects states changed *while* service ran, not device effect |
| `uncertain` expiring on a timer | Timers cannot know device state; only fresh readbacks confirm reality |
| Sending `off` to all actuators on boot | Turns off devices triggered by humans or other controllers; pays off only self-incurred "off-debt" |
| Plugin auto-detecting or escalating level at runtime | Levels must be declared and proven, not guessed (Q-35: undeclared assumes worst case) |
| `sim` connecting to real hardware via flag | Simulation sessions must not actuate real valves; hardware testing belongs on `linux` or human gates |

## 7. Verification Evidence

All items are **implementation requirements** (TSK-I2c-16); unticked because RFC contains no code yet. All corpora bidirectionally closed (`CONTRIBUTING.md` §3).

- [x] **Declaration corpus** (`fixtures/actuators/{valid,invalid}/` + `expected_errors.yaml`): valid declarations per level; absent `safe_off`, invalid levels, missing envelope keys, name collision with board pins, missing bidirectional references (§3b), unknown keys, literal secrets ⇒ NE3002; `safe_off` exceeding `safe_off_level`, `readback = none` for irreversible, `max_continuous_ms ≤ tolerance_ms`, `esp32s3`, `pwm`/`motion` targeting remote names ⇒ NE3001
- [x] **Decision D5** (`python/tests/test_remote_actuator_build.py`): `test_an_irreversible_actuator_below_l2_is_refused_at_build`, `test_the_same_declaration_is_refused_at_load_without_agent_toml`, `test_reversible_is_false_when_not_declared`, `test_l0_builds_only_for_a_reversible_actuator_and_warns`, `test_an_irreversible_actuator_without_readback_is_refused`, `test_the_home_assistant_plugin_cannot_declare_an_irreversible_actuator`
- [x] **Single path** (`python/tests/test_remote_actuator.py`): `test_no_path_reaches_a_remote_actuator_without_a_valid_token`, `test_a_remote_actuator_plugin_receives_no_hal_no_ledger_and_no_envelope`, `test_the_order_is_require_pin_state_guard_envelope_authorize_record_apply`, `test_a_refused_remote_on_spends_no_token_and_holds_no_envelope`, `test_off_to_a_remote_actuator_needs_no_token_and_is_never_refused`
- [x] **State and communication loss:** `test_an_ambiguous_send_failure_holds_the_reservation_and_marks_the_actuator_uncertain`, `test_a_not_sent_failure_refunds_the_reservation`, `test_an_uncertain_actuator_refuses_on_but_still_sends_off`, `test_uncertain_ends_only_on_a_fresh_off_readback_never_on_a_timer`, `test_a_reading_of_on_nobody_commanded_is_already_on_not_a_command_to_turn_off`, `test_the_hal_turns_off_only_what_it_turned_on`, `test_a_restart_leaves_every_remote_actuator_uncertain`, `test_a_late_delivered_on_is_seen_by_readback_and_turned_off`
- [x] **Envelope** (`python/tests/test_remote_actuator_envelope.py`): `test_the_remote_envelope_keys_have_the_meaning_of_rfc_0007`, `test_the_window_counts_until_the_hal_knows_the_actuator_is_off`, `test_the_physical_ceiling_is_max_continuous_plus_tolerance_and_is_counted`, `test_sim_and_linux_end_a_remote_on_the_same_way`, `test_the_remote_on_time_is_written_before_the_command_is_sent`, `test_a_corrupt_record_makes_a_remote_actuator_quarantined`
- [x] **Auto-off levels on doubles** (`fixtures/compliance/actuators/` + `neuroedge conformance`): check `actuator.level_proven` for L0–L3 in §3e, one counter-example per vector (`test_a_double_that_ignores_the_timer_fails_l2`, `test_a_double_that_ignores_the_lease_fails_l3`, `test_a_plugin_claiming_l2_without_duration_fails_l0_check`); `test_l2_sends_a_duration_on_every_on_never_none`, `test_l3_stops_renewing_before_the_ceiling_and_a_frozen_runtime_loses_the_device`
- [x] **P2:** `test_a_device_that_turns_itself_off_is_recorded_as_evidence`, `test_a_device_still_on_after_its_guarantee_is_commanded_off_and_quarantined`, `test_a_quarantined_actuator_refuses_every_on_until_the_record_is_cleared`, `test_uncertain_and_quarantined_are_absent_facts_so_a_gate_blocks`, `test_the_state_fact_age_is_measured_by_the_receiver`
- [x] **Traces and replay:** `test_every_remote_command_sent_follows_an_actuator_command` (lint ⇒ NE4001 on omission), `test_replay_never_builds_the_plugin_opens_a_socket_or_reads_the_key`, `test_replay_refuses_the_same_on_it_refused_when_recorded`, `test_the_canonical_traces_do_not_change`
- [x] **Home Assistant** (HA double, `tests/`): `test_the_home_assistant_plugin_passes_the_l0_and_l1_vectors`, `test_a_200_from_a_service_call_is_not_a_confirmed_state`, `test_the_plugin_declares_l1_for_a_switch_and_nothing_higher`, `test_the_websocket_dropping_makes_the_actuator_uncertain`
- [x] **Boundaries:** `test_esp32s3_refuses_an_agent_with_remote_actuators`, `test_build_warns_on_a_network_client_import_in_an_action_module`, `test_sim_never_uses_the_real_plugin`
- [x] **Public contracts:** `tests/test_public_api.py` pins new names, `test_the_actuator_protocol_signature_is_pinned` (signature in §3c, four error classes); `docs/spec/python_api.md` updated
- [x] `neuroedge gate lint` and `neuroedge verify` green; `pytest -q` 0 failed, 0 skipped

## 8. Implementation Steps Upon Approval

- [x] `engine/compiler.py`: parse `[actuators]`, validate §3b and D5 (§3f), wire into `check_capabilities` (actuator names as valid declared pins), warn on network client imports; shared validator used at load time (TSK-I2c-16)
- [x] `hal/__init__.py` and new module `hal/remote.py`: shared path §3c, state §3g, `off` timers/lease renewals; `hal/sim.py`, `hal/linux.py` branch at entry of `digital_out`; `script_remote_state`; `hal/envelope.py`: HAL-driven termination (`virtual = False`) and merge remote actuator limits into `SafetyEnvelope`; `sim/session.py` (`:917–942`, `_linux_envelope` `:645`): attach plugin (`linux`) or double (`sim`), reject `esp32s3`
- [x] `python/neuroedge/trace.py`: lint §3i; `testing/player.py`: replay without touching plugins
- [x] `Actuator` Protocol, `Command`, `DeviceDouble`, `ActuatorError`, and four error classes into `neuroedge.sdk` (TSK-I2c-11); compliance test suite for `neuroedge.actuators` (TSK-I2c-12), Home Assistant double and `home_assistant` plugin (TSK-I2c-16), readback facts via in-process fact source (TSK-I2c-09)
- [x] `docs/spec/threat_model.md`: §1 adds remote actuators to "single valid path" and safety-direction command exception; §2 adds rows for bypass paths in §3g (turning on when `uncertain`, improper reservation refund, turning off unmanaged devices); §5 adds risks 1–7. `docs/spec/tool_calling.md` §10 rule 2: add "or a remote actuator" for physical effects
- [x] `docs/spec/simulation_coverage.md` §3: six events in §3i; `docs/user/thuat-ngu.md`: auto-off levels L0–L3, remote actuator, off-debt, irreversible
- [x] `neuroedge-prd.md`: Appendix B (broaden causes for NE1003, NE3001, NE3002); FR-EXT-07 text unchanged; new decisions in §9 assigned `Q-N` in §15
- [x] `CONTRIBUTING.md` §3: add corpus `fixtures/actuators/` to table "Adding a counter-example fixture"; `neuroedge-roadmap.md`: TSK-I2c-04 completed; `TODOS.md` #55: design portion closed, Zenoh/unreliable channel portion retained
- [ ] `docs/rfc/README.md` (RFC-0018 row) and `CHANGELOG.md` `[Unreleased]`

## 9. Decisions for Open Questions (Q-68, 2026-10-04)

Q-67 left the following points open; RFC was written according to recommendations. Lead Engineer **accepts recommendations for all questions below**, under the highest-safety principle of Q-57; each recommendation is a decision (Q-68, 2026-10-04). This section is the decision record: if §3–§8 conflict with it, fix §3–§8.

1. **Declare remote actuators in `agent.toml` or in `board.v1`?** *Recommendation: `agent.toml`* (§3b): deployment configuration does not belong in hardware profiles, and avoids editing frozen schemas. Trade-off: envelopes live in deployer file rather than board profile. Choosing `board.v1` requires editing `schemas/board.v1.json` (RFC, top row of `CONTRIBUTING.md` §3), adding new `capabilities` keys and determining how `sim-*` boards mirror it (invariant #7).
2. **Mandatory readback for irreversible actions?** FR-EXT-07 required on-device auto-off levels (L2/L3); this RFC adds `readback ≠ none`, because without it P2 cannot run and levels remain unverified claims. *Recommendation: mandatory.* Trade-off: write-only devices cannot be used for irreversible actions.
3. **Home Assistant adapter location** (roadmap TSK-I2c-16: "plugin in `python/neuroedge/` or separate repo")? *Recommendation: separate repo, license chosen by author (preferably Apache-2.0)* (Q-67 decision 8) — acts as proof that SDK suffices for third parties without private core paths; conversely, in-tree inclusion binds it to PolyForm Noncommercial (Q-45) and forces core team to maintain an integration it does not own.
4. **`pwm`, brightness, `motion.*` for remote actuators** (Home Assistant dimmable lights, remote servos): each requires defining dedicated "what blocks it upon communication loss" semantics. *Recommendation: defer, separate RFC when measurable need arises*; this release rejects with NE3001 to prevent unguaranteed ad-hoc usage.
5. **Constants for §3d, §3g** — `OFF_SLACK_MS`, `OFF_RETRY_MS`, `max_state_age_ms`, plugin ceilings for `command_timeout_ms` and `tolerance_ms`. *Recommendation: Lead Engineer settles upon approval, like RFC-0014 §9 question 10*; altering constants later changes specifications; relaxing safety limits requires an RFC. **Settled (Q-68):** `OFF_SLACK_MS` = 100 ms · `OFF_RETRY_MS` = 500 ms · `max_state_age_ms` = 2000 ms · plugin-declared `command_timeout_ms` ≤ 5000 ms · plugin-declared `tolerance_ms` ≤ 2000 ms (exceeding ⇒ NE3002). Conservative defaults chosen prior to real device measurements; tighten based on TSK-I2c-16 empirical metrics.
6. **Network client import warning in `@action` modules** (§3c): *warn, do not block* (recommendation). Blocking yields false positives (HTTP data fetching is valid) and remains non-exhaustive; serves as reminder, not barrier.
