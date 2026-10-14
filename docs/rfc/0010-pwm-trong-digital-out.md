# RFC-0010: PWM and State-Feedback Channel in `digital.out`

| | |
|:---|:---|
| **RFC ID** | 0010 |
| **Title** | `pwm` operation (frequency, duty cycle) and pin state readback in `digital.out` |
| **Affected Contract** | `board.v1` *(the `pwm`, `enable_pin`, and `feedback` blocks in `digital_out`)* · **does not** touch `gate.v1` |
| **Related PRD Requirements** | FR-HAL-01, FR-HAL-05, FR-ACE-08 |
| **Author** | — |
| **Date Opened** | 2026-09-30 |
| **Status** | ✅ Approved (2026-10-01) — lead architect signed on PR #77; amended per review 2026-10-01 (§9, Q-62); implemented in second PR |
| **Approver** | **Lead Architect — mandatory** (touches physical pin paths and extends the RFC-0007 envelope) |

> **When an RFC is required:** `CONTRIBUTING.md` §3 — modifying `schemas/board.v1.json`. Task: TSK-W1-01.
> Source: FOFOCA robot draft (`docs/architecture/vi/15-target-architecture.md` §4.3), now consolidated into this RFC. Foundation
> decisions: `neuroedge-prd.md` §15 Q-52 (PWM pack in MVP), Q-53 (four packs across all three tier-1 targets), Q-55, Q-57
> (§9). Dependencies: envelope and `max_continuous_ms` lock in [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md) §9.5
> (actuator flag and envelope location per §9 item 5 of that RFC), parameter constraint pattern in [RFC-0005](0005-rang-buoc-tham-so-trong-gate.md).

## 1. Problem

`digital.out` has only three operations: `pulse`, `on`, `off` (`python/neuroedge/hal/digital.py`; `SimHAL.digital_out` and `LinuxHAL.digital_out` reject any other operation). Fans, dimmers, buzzers, and RC servos require **pulse-width modulation**: a frequency and a duty cycle. There is no way to express *"run fan at 40% power"* without faking it through a sequence of short `pulse` calls — a sequence that has the wrong frequency and consumes one token every time.

In addition, there is no way to read back the **actual state** of a pin after a command: `PinAssertion` (`python/neuroedge/hal/__init__.py`) records what the HAL *receives*, not *where the pin currently is*. With PWM, "commanded 40%" differs from "currently outputting 40%".

## 2. Why the Current Schema Does Not Solve It

- `schemas/board.v1.json`, `digital_out`: only has `pins` and `backend`; nowhere to declare which pins support PWM, frequency range, resolution, or which pins can be read back.
- Computing limits in agent code (self-derived facts) is the workaround rejected by RFC-0005: limits must live in the gate and on the board, not in the agent.
- The RFC-0007 envelope counts **on-time**; with PWM, "on" is no longer binary, so that definition needs extending.

## 3. Proposed Change

### 3a. Board Declares PWM Pins and Hardware Limits

```toml
[capabilities.digital_out.pwm]
pins             = ["fan"]                 # subset of digital_out.pins; hardware PWM channels only
frequency_hz     = { min = 100, max = 25000 }
resolution_bits  = 10
max_duty         = 0.8                     # hard ceiling of the load; mandatory, no default
enable_pin       = { fan = { pin = "fan_en", enable_active = "high", pull = "down" } }

[capabilities.digital_out.feedback]
pins = ["fan"]                             # only pins with real hardware readback

[capabilities.digital_out.envelope.fan]    # envelope lock (RFC-0007 §9.5)
window_s             = 3600
max_on_ms_per_window = 1800000
min_interval_ms      = 2000
max_continuous_ms    = 600000              # ceiling of one PWM command
```

- **Hardware PWM channels only.** A board with no hardware PWM channel does not declare `pwm`; no software PWM (§3e, §9.1).
- **`duty` quantisation:** HAL quantises `duty` per `resolution_bits` and always rounds toward 0 so it never exceeds the hardware `max_duty` (§9.15).
- **`enable_pin` mandatory for every PWM channel:** each PWM channel must have a dedicated `enable_pin`, not shared with another channel (sharing ⇒ `BoardCapabilityError` at load time, §9.15). The declaration must specify both fields `enable_active = "high"` and `pull = "down"`; this version accepts only those two values (active-low or pull-up ⇒ rejected at load time, §9.14). HAL enables `enable_pin` only during a PWM command that has passed the gate; direct `digital.out` commands to `enable_pin` are rejected (§9.2). `enable_pin` is managed internally by HAL: agents cannot call it (direct `digital.out` commands to it are rejected), exempt from its own RFC-0007 envelope, and not declared in `signal_pins`.
- **All PWM pins are always actuators:** per RFC-0007 §9 item 5, all `digital_out` pins are actuators by default and must have an envelope at `[capabilities.digital_out.envelope.<name>]`; only pins declared in `signal_pins` are exempt. All `pwm.pins` are always actuators; declaring them in `signal_pins` is forbidden. Missing envelope ⇒ `BoardCapabilityError` at load time (§9.10).
- **`feedback`** declares only pins that can be read back from hardware; a board without readback does not declare it (§9.4).

`board.v1` is the **hardware truth** (what the load can tolerate); the gate is the **policy** (what is permitted). Gates may be tighter; they never loosen board ceilings.

### 3b. Operations and API

- **Operations on PWM pins:** On pins belonging to `pwm.pins`, `on` and `pulse` operations are rejected (`BoardCapabilityError` NE3001, no token spent) to prevent outputting 100% duty exceeding the hardware `max_duty` ceiling; PWM pins **accept only `pwm` and `off` operations** (§9.13).
- **`pwm` operation:** `HardwareAbstractionLayer.digital_out` takes additional `operation = "pwm"` with `frequency_hz`, `duty` (0.0–1.0), and `duration_ms` — **all three mandatory**; `duration_ms` is a positive integer, with no default value or "run forever" meaning (§9.5). On the agent side (`hal/digital.py`): `digital.out("fan").pwm(frequency_hz=1000, duty=0.4, ms=5000)`, `ms` has no default value; a tool call missing mandatory parameters is already `REJECTED` (`docs/spec/tool_calling.md`).
- **Processing order and budget refund:** Processing order: `require_pin → check board limits → envelope reserve → authorize → record`. Pin not declaring `pwm` or `pwm` command missing `duration_ms`, `duty`/`frequency_hz` out of limits ⇒ `BoardCapabilityError`, no token spent. The envelope reserves upfront exactly `min(duration_ms, max_continuous_ms)` out of `max_on_ms_per_window`. If `authorize` fails after budget reservation, the entire reserved portion is refunded immediately: no token spent, no pulse sent to hardware (§9.8). Turning off early (via `off` or barge-in) refunds the unused portion.
- **Safe-direction commands are never blocked:** `digital.out` `off` commands, PWM setting `duty = 0`/releasing `enable_pin`, and all HAL autonomous commands upon expiry of `duration_ms`, expiry of `max_continuous_ms`, on barge-in, BLOCK, loss of connection, or `hal.close()` do not go through the envelope, do not require ALLOW or tokens, and do not wait for `min_interval_ms` or after-boot cooldown (§9.6). This is the sole exception to the "no command reaches hardware without ALLOW" rule, applying only to commands transitioning actuators to a safe state. Commands are still recorded in traces with their cause. `min_interval_ms` applies only to turn-on commands (§9.7).
- **Not relying solely on in-process timers:** The automatic shutoff timer at `min(duration_ms, max_continuous_ms)` must not live solely in the runtime process which can hang (§9.11). On `esp32s3`: task watchdog (TWDT) plus hardware timer; watchdog reset reboots with `enable_pin` pulled down. On `linux`: `enable_pin` and the actuator pin line are held by a separate supervisor process; the runtime sends heartbeats; missing heartbeats beyond the deadline ⇒ supervisor releases `enable_pin` and turns off the pin.
- **State readback and numeric facts for gates:** `digital.out("fan").state()` returns the pin state. For PWM pins, each quantity (`duty`, `frequency_hz`) is a separate numeric fact with `source` (§9.12). `source` is `measured` when the pin belongs to `feedback.pins` and is read back from hardware, and `commanded` (value recorded by HAL) for all other pins. A failed readback never returns `commanded` instead — raises `PerceptionUnavailableError` (NE5001). Gates may only use `measured` values as facts; a `commanded` value reaching a gate is treated as missing measurement ⇒ BLOCK `criterion_unavailable`. When an agent connects a `numeric` criterion to `feedback` readback, `neuroedge build` verifies matching `unit` and that the channel's `[min, max]` falls within the criterion's `range`; mismatch ⇒ `BoardCapabilityError` (NE3001). `numeric` criteria MUST NOT be placed in `on_block.confirms` of RFC-0006: `gate lint` rejects them (`GateSchemaError`, NE2002). `state()` requires no token (moves nothing), recorded as an event with `source` for replay. Units and scales of readbacks are fixed: `duty` has `unit = ratio`, scale `[0, max_duty]`; `frequency_hz` has `unit = Hz`, scale `[frequency_hz.min, frequency_hz.max]` of the board; `build` verifies per RFC-0009 §3f against these values.

### 3c. Parameter Constraints at the Gate (RFC-0005 Pattern)

Does not change `gate.v1`. `@action` declares `duty`, `frequency_hz`, and `duration_ms` as parameters; the gate uses the existing `arguments` block:

```yaml
arguments:
  duty:         { type: number,  minimum: 0.0, maximum: 0.6 }
  frequency_hz: { type: integer, minimum: 200, maximum: 5000 }
  duration_ms:  { type: integer, minimum: 1,   maximum: 10000 }
```

Violation ⇒ BLOCK `argument_out_of_range` before `evaluate`; default values of `@action` are also checked; child gates only narrow (RFC-0005 §3). `duration_ms` is bounded by two layers: `arguments` of the gate and `max_continuous_ms` of the board (§3d); both enforce simultaneously, with the tighter limit winning. The C walker already reads the parameter limit table, so **no new node is needed**.

### 3d. Envelope Extension

The RFC-0007 envelope counts the time *pulses are output*. With PWM, **the entire** time with `duty > 0` is counted as "on", **not multiplied by duty** (§9.3); the board's `max_duty` ceiling enforces additionally.

- **Pre-reservation and refund:** Each PWM command requests upfront reservation of exactly `min(duration_ms, max_continuous_ms)` out of `max_on_ms_per_window`. Commands with `duration_ms > max_continuous_ms`, exceeding the window's remaining budget, or called before `min_interval_ms` has elapsed since the previous turn-on ended ⇒ envelope refuses (`EnvelopeRefusedError`, NE1003, event `envelope_refused` — RFC-0007 §9.4), no token spent. Over-limit commands are rejected outright, not truncated to run partially (no "warn and permit" mode). Early shutoff refunds unused portions. If `authorize` fails after reservation, the entire reserved portion is refunded: no token spent, no pulse (§9.8).
- **Safe commands bypass the envelope:** `min_interval_ms` applies only to turn-on commands (§9.7). `off` commands or setting `duty = 0`/releasing `enable_pin` do not go through the envelope, are not blocked by `min_interval_ms`, and require no token or ALLOW (§9.6).
- **Envelope survives restarts:** Total reserved on-time in the window is persisted write-ahead before turning on: NVS on `esp32s3`, state file on `linux`; `sim` simulates identical rules (§9.9). After reboot, lacking a reliable cross-boot clock, all recorded turn-on events are treated as having occurred immediately before boot. They occupy budget until `window_s` after boot. Unreadable, corrupt, or missing records ⇒ entire window treated as exhausted (fail-closed). The rule requiring `min_interval_ms` wait before the first turn-on after boot is retained.
- **Mandatory declaration:** Declared under `[capabilities.digital_out.envelope.<name>]`. All PWM pins are always actuators, requiring an envelope; missing envelope ⇒ `BoardCapabilityError` at load time (§9.10).

### 3e. Target-Specific Backends

- **`linux`:** **hardware PWM from kernel only** (`/sys/class/pwm`); no software PWM (bit-banging via gpiod). If board declares `pwm` but kernel lacks the corresponding channel ⇒ rejected at load time (`BoardCapabilityError`), no fallback to software PWM. CI tests run against mock sysfs tree (same as `hal/sysfs.py`); hardware evidence on nightly Pi 5 (§9.1). Auto-off timer and `enable_pin` are protected by independent supervisor process against hung runtime process (§9.11). Envelope persists write-ahead to state file (§9.9). `hal.close()` zeroes `duty`, disables channel, and drops `enable_pin`.
- **`esp32s3`:** firmware uses chip's hardware PWM channel, identical `enable_pin` and envelope rules (§8). Task watchdog (TWDT) plus hardware timer ensures boot with `enable_pin` pulled down if runtime hangs (§9.11). Envelope persists write-ahead to NVS (§9.9).
- **`sim`:** model mirrors reference board, no richer (RFC-0013); simulates identical persistence and envelope rules.

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | Yes. Per RFC-0007 §9 item 5, all `digital_out` pins default to actuators and require envelopes. Three tier-1 profiles in `boards/` must add envelopes in implementation PR, with values wide enough for canonical traces to replay unchanged (e.g. `door_lock` receives 30,000 ms pulse ⇒ `max_continuous_ms` ≥ 30000). No external profiles exist yet |
| Do currently invalid files become valid? | Yes — profiles declaring `pwm`/`feedback` with correct shapes (all PWM channels are actuators, must include dedicated `enable_pin` with `enable_active = "high"` and `pull = "down"`, and `envelope` block). Same tightening point as RFC-0007 §4 if someone used this key name before: none in repo |
| Does schema version need bumping (`v1` → `v2`)? | No, provided shape is decided before external profiles exist |
| Impact on published gate hashes / signatures? | None |
| Impact on three canonical trace files? | None — no `pwm` in their verdict sequence; added envelopes in three tier-1 profiles wide enough to replay identically |
| Which gates in `digests.lock` change digest? | None |
| Must `NETR` layout or C walker change? | No — reuses parameter limit table from RFC-0005/RFC-0003 |
| Do any answers in tool call corpus (`expected_results.yaml`) change? | Existing answers unchanged; new cases added for `duty`/`frequency_hz`/`duration_ms`, including missing `duration_ms` ⇒ `REJECTED` |
| Error codes (`neuroedge-prd.md` Appendix B) | `BoardCapabilityError` (NE3001) and `PerceptionUnavailableError` (NE5001) already exist; NE3001 applies additionally to `on`/`pulse` on PWM pins, incorrect `enable_pin` config, or feedback `unit`/scale mismatch. Add `GateSchemaError` (NE2002) when `numeric` criterion sits in `on_block.confirms`. `EnvelopeRefusedError` (**NE1003**, RFC-0007 §9.4) not yet present: on approval, Appendix B adds this line if RFC-0007 has not already. `argument_out_of_range` is existing BLOCK reason (FR-ACE-08), not an error class |

## 5. Safety Impact

- **Gates no looser:** `gate.v1` and five inheritance principles preserved; `duty`/`frequency_hz`/`duration_ms` constraints execute deterministically before `evaluate`, consuming no model budget.
- **Independent second layer:** hard ceilings in `board.v1` (`max_duty`, frequency range, `max_continuous_ms`) block even overly permissive gates. `on()` and `pulse()` operations rejected on PWM pins to prevent outputting 100% duty exceeding board's `max_duty` ceiling (§9.13). Quantisation of `duty` per `resolution_bits` always rounds toward 0 to never exceed hardware `max_duty` (§9.15).
- **No unbounded PWM:** all turn-on commands on PWM channels have finite duration: `duration_ms` always mandatory, bounded by gate and `max_continuous_ms` (§9.5). All PWM pins always actuators, cannot declare `signal_pins`, must have envelope (§9.10); envelope counts entire duration `duty > 0` (§9.3). Upfront budget reservation at `min(duration_ms, max_continuous_ms)`; early shutoff refunds unused portion; failed `authorize` after reservation refunds entire budget (no token spent, no pulse, §9.8).
- **Safe-direction commands never blocked:** `digital.out` `off` commands, PWM setting `duty = 0`/releasing `enable_pin`, and all HAL autonomous commands upon expiry of `duration_ms`, expiry of `max_continuous_ms`, barge-in, BLOCK, connection loss, or `hal.close()` do not go through envelope, need no ALLOW or token, and do not wait for `min_interval_ms` or after-boot cooldown (§9.6). This is sole exception to mandatory ALLOW rule, applying only to bringing actuators to safe state.
- **`min_interval_ms` applies only to turn-on commands:** actuators are permitted to shut off to safety immediately without delay from rate limits (§9.7).
- **Envelope survives reboot:** persisted write-ahead (NVS on `esp32s3`, state file on `linux`). Post-boot treats recorded turn-ons as occurring immediately pre-boot, occupying budget until `window_s`; corrupt or missing records treated as exhausted window (fail-closed); still awaits `min_interval_ms` before first post-boot turn-on (§9.9).
- **Not relying solely on in-process timers:** runtime process can hang (SIGSTOP) leaving kernel driver outputting pulses. On `linux`, independent supervisor process holds `enable_pin` and drops it on missing heartbeat; on `esp32s3`, task watchdog (TWDT) plus hardware timer resets to pulled-down state (§9.11). Actuator always returns to safe state within declared duration plus margin.
- **Guaranteed hardware configuration:** all PWM pins always actuators, each channel requires distinct unshared `enable_pin` (§9.15), declaration requires `enable_active = "high"` and `pull = "down"` (§9.14). Crash/SIGKILL: kernel PWM channel keeps running after process death, but supervisor process holding `enable_pin` line drops it on lost heartbeat; if supervisor itself dies, gpiod line drops and pulldown resistor disables driver (§9.2, `docs/spec/lab_mcp.md` §2.3).
- **No software PWM:** software pulses jitter and stall midway when process contends (§9.1).
- **Feedback channel and numeric fact constraints:** `state()` splits each quantity (`duty`, `frequency_hz`) into distinct numeric fact with `source` (§9.12). Only `measured` values (from pins in `feedback.pins`) accepted by gates as valid facts; `commanded` reaching gate treated as missing measurement ⇒ BLOCK `criterion_unavailable`. `build` verifies matching `unit` and `[min, max]` inside criterion `range` (`BoardCapabilityError` NE3001). Forbids numeric criteria in `on_block.confirms` (`GateSchemaError` NE2002) because humans cannot confirm in place of sensor measurements.

## 6. Alternatives Considered and Rejected

| Alternative | Reason for Rejection |
|:---|:---|
| Separate `pwm.out` primitive | PWM is a control mode for *a digital pin*; splitting doubles pin tables, `require_pin`, and envelopes. FOFOCA draft also grouped PWM under extensions across the five primitives |
| Pseudo-PWM using `pulse` series | Wrong frequency, each pulse costs one token, envelope miscalculates |
| Software PWM (bit-banging via gpiod) on `linux` | Jitter, stalls midway during process contention (§9.1) |
| No `enable_pin`, relying on `hal.close()` | Kernel PWM channel continues running after crash/SIGKILL; only pulled-down gpiod line disables driver (§9.2) |
| Envelope calculating `duty × time` | Depends on load energy model; not conservative (§9.3) |
| `state()` returning value without source label | Sent command mistaken for measured state (§9.4) |
| PWM without `duration_ms`, running to `max_continuous_ms` then stopping | Is "run forever" PWM with ceiling; continuing requires calling again through gate (§9.5) |
| Adding `duty`/`frequency_hz` to `gate.v1` as dedicated fields | `arguments` is sufficient (RFC-0005); adding fields unnecessarily expands gate schema |
| Letting `motion.*` (RFC-0011) handle PWM as well | Motor/servo has channels, targets, ramps, leases; fan/light does not. Two different contracts |

## 7. Verification Evidence

- [ ] Valid example: `boards/` profile declaring `pwm`, `enable_pin` (with `enable_active = "high"` and `pull = "down"`), `feedback`, and `envelope` (reference board per RFC-0013)
- [ ] Board configuration negative tests: `pwm` pin not in `pins`, `min > max`, missing `max_duty`, `max_duty` outside (0, 1], frequency out of range; `pwm` channel missing `enable_pin`, `enable_pin` invalid fields or has `enable_active != "high"` or `pull != "down"` (§9.14); two PWM channels sharing one `enable_pin` (§9.15); PWM pin declared in `signal_pins` or missing `envelope` (§9.10); `enable_pin` not in `digital_out.pins` or overlaps `pwm` channel ⇒ `BoardCapabilityError` at load time
- [x] Operations and constraints negative tests: calling `on()` or `pulse()` on pin in `pwm.pins` ⇒ rejected before `authorize` (`BoardCapabilityError`), no token spent (§9.13); `numeric` criterion connected to `feedback` readback with mismatched `unit` or outside `[min, max]` ⇒ `BoardCapabilityError` (NE3001) at build time (§9.12); `numeric` criterion in `on_block.confirms` ⇒ `GateSchemaError` (NE2002) at `gate lint` (§9.12) — *met: `on`/`pulse` ⇒ `test_on_and_pulse_on_a_pwm_channel_are_refused_with_no_token_spent`, `test_on_and_pulse_are_refused_on_linux_too_before_anything_moves` (`tests/test_pwm.py`, `tests/test_hal_linux_pwm.py`); mismatched `unit` / outside `[min, max]` ⇒ NE3001 at build: `test_build_checks_the_unit_and_the_range_of_a_read_back_criterion`, `test_build_refuses_a_criterion_range_narrower_than_the_channels_scale`; `confirms` ⇒ NE2002: `test_a_read_back_criterion_cannot_be_waived_by_a_person`*
- [x] Parameter tests: `duty` exceeding gate's `maximum` ⇒ BLOCK `argument_out_of_range`, pin unchanged; `duty` exceeding board's `max_duty` ⇒ rejected in HAL, **no token spent**; quantisation of `duty` per `resolution_bits` rounding toward 0 never exceeds `max_duty` (§9.15); default values checked too — *met: `test_a_value_outside_the_gates_limits_is_blocked_and_the_fan_does_not_move`, `test_a_pwm_command_outside_the_boards_limits_is_refused_with_no_token_spent`, `test_a_quantised_duty_never_exceeds_the_checked_one_or_max_duty`, `test_the_boards_ceiling_is_max_duty_and_the_message_says_so`, `test_the_default_of_an_action_parameter_is_checked_too` (`tests/test_pwm.py`)*
- [x] `duration_ms` and auto-off tests (§9.5): `pwm` command missing `duration_ms` ⇒ HAL rejects before `authorize`, no token spent; tool call missing `duration_ms` ⇒ `REJECTED`; exceeding `arguments` ⇒ BLOCK `argument_out_of_range`; exceeding `max_continuous_ms` ⇒ `EnvelopeRefusedError`, no token spent; expiry of `min(duration_ms, max_continuous_ms)` ⇒ `duty = 0` and `enable_pin` released; early shutoff refunds unused portion; failed `authorize` after reservation refunds entire budget (§9.8) — *met: `test_a_pwm_command_outside_the_boards_limits_is_refused_with_no_token_spent` (missing `duration_ms`), `test_a_call_that_leaves_out_the_duration_is_rejected` and case `fan_run_missing_duration.yaml`, `test_a_command_over_max_continuous_ms_is_refused_whole_with_no_token_spent`, `test_the_channel_goes_off_by_itself_when_the_time_is_up`, `test_off_early_gives_back_the_unused_time`, `test_an_authorize_that_fails_gives_back_everything_it_held`; on `linux`: `test_the_channel_goes_off_when_the_time_is_up_enable_line_first`, `test_off_gives_the_unused_on_time_back` (`tests/test_pwm.py`, `tests/test_hal_linux_pwm.py`, `fixtures/tool_calls/`)*
- [x] Safe command tests: `off` command and setting `duty = 0`/releasing `enable_pin` (including upon expiry or `hal.close()`) do not go through envelope, need no ALLOW or token, do not wait for `min_interval_ms` or post-boot, still recorded in traces with cause (§9.6); `min_interval_ms` applies only to turn-on commands, calling `off` immediately after `pwm` command is not blocked (§9.7) — *met: `test_off_is_never_blocked_even_inside_min_interval_ms`, `test_a_duty_that_quantises_to_nothing_is_the_safe_state_and_needs_no_token`; on `linux`: `test_off_never_needs_a_token_and_drops_the_enable_line`, `test_close_brings_the_controller_and_the_line_down`*
- [x] Envelope and restart tests (§9.3): one command `duty = 0.1` for 1000 ms deducts full 1000 ms from `max_on_ms_per_window`; persists write-ahead to NVS (`esp32s3`) or state file (`linux`) before turning on; after reboot treats recorded turn-ons as occurring immediately pre-boot and occupying budget until `window_s`; first turn-on within `min_interval_ms` after reboot rejected; corrupt/missing records ⇒ entire window treated as exhausted (§9.9) — *met (`sim`): `test_the_whole_time_with_duty_above_zero_counts_not_duty_times_time`, `test_a_pwm_command_is_written_ahead_and_a_restart_keeps_its_time`; `esp32s3` NVS portion under TSK-I3a-03*
- [ ] `enable_pin` and anti-hang tests (§9.2): `enable_pin` turns on only during gate-passed PWM command; direct `digital.out` command to `enable_pin` rejected; on gpio-sim (`python/tests_linux/`), SIGKILL on process mid-command ⇒ `enable_pin` line returns to pull-down; runtime acceptance test receives SIGSTOP during turn-on ⇒ independent supervisor process (`linux`) or TWDT / hardware timer (`esp32s3`) releases `enable_pin` and disables channel within declared deadline plus margin (§9.11) — *`linux` portion met (CI run 37153005998, job `linux-hal`): `tests_linux/test_gpio_pwm.py::test_the_enable_line_is_up_while_a_pwm_command_runs_and_down_when_it_ends`, `test_off_and_close_drop_the_enable_line`, `test_a_runtime_that_is_killed_while_the_fan_runs_loses_the_enable_line`, `test_a_runtime_stopped_with_sigstop_while_the_fan_runs_loses_the_enable_line`; blocking direct `digital.out` to `enable_pin` in `tests/test_pwm.py`; `esp32s3` (TWDT) pending*
- [x] `state()` and numeric feedback tests (§9.4): `state()` splits `duty` and `frequency_hz` into distinct numeric facts with `source`; pin in `feedback.pins` ⇒ `source: measured`; other pins ⇒ `commanded`; failed readback raises `PerceptionUnavailableError` and does not return `commanded`; `commanded` value reaching gate ⇒ BLOCK `criterion_unavailable`; only `measured` accepted by gate as fact; replay reloads `source` as well (§9.12) — *met: `test_the_state_of_a_pin_with_no_read_back_is_what_was_commanded`, `test_a_pin_the_board_gives_a_read_back_is_measured_not_commanded`, `test_a_read_back_that_fails_is_ne5001_and_never_the_commanded_value`, `test_a_commanded_duty_never_reaches_the_gate`, `test_a_measured_duty_decides_the_gate_and_a_failed_read_back_blocks_it`, `test_replay_feeds_back_a_measured_state_with_its_source`; `linux`: `test_a_declared_read_back_comes_from_the_controller_not_from_memory`, `test_a_read_back_that_is_not_believable_is_ne5001_never_the_commanded_value`*
- [ ] Backend tests (§9.1): `linux` goes only through `/sys/class/pwm` (mock sysfs tree); board declaring `pwm` without kernel channel ⇒ rejected at load time; after `hal.close()` `duty = 0`, channel disabled, `enable_pin` released; hardware evidence on nightly Pi 5
- [x] New cases in `fixtures/tool_calls/` for PWM parameters (including missing `duration_ms`), bidirectional closure in `expected_results.yaml` — *met: `fixtures/tool_calls/{valid,invalid}/fan_*.yaml` (board `sim-rpi5`, new `board` key in case file), bidirectional closure — `tests/test_tool_corpus.py`*
- [ ] `sim` does not declare PWM where reference board lacks it; `neuroedge gate lint` and `neuroedge verify` green

## 8. Post-Approval Tasks

- [x] Update `schemas/board.v1.json` (`pwm`, `enable_pin` requiring `enable_active = "high"` and `pull = "down"`, forbid sharing `enable_pin`, `feedback`, `signal_pins` and mandatory envelope rule for all actuator pins per RFC-0007 §9 item 5) — *met: `pwm`, `enable_pin` (`high`/`down`, unshared), `feedback`, `signal_pins`, mandatory envelopes — `tests/test_board_fixtures.py`*
- [x] Record safe-direction command exception (no ALLOW required, no envelope, no `min_interval_ms` wait) in `docs/spec/threat_model.md` §1 — *met: `docs/spec/threat_model.md` §1 (RFC-0007 §8; `duty = 0` and releasing `enable_pin` on PWM channels added in TSK-W1-01)*
- [x] Add envelope blocks for three tier-1 profiles in `boards/` in implementation PR with values wide enough for canonical traces to replay identically — *met — `test_the_envelopes_are_wide_enough_for_the_canonical_traces`*
- [ ] Update corresponding Appendix in `docs/spec/core_contracts.md`; FR-HAL-01 in `neuroedge-prd.md`; PRD Appendix B adds `EnvelopeRefusedError` (NE1003) line if RFC-0007 has not already
- [ ] Update `neuroedge-roadmap.md` (TSK-W1-01)
- [x] Implement `python/neuroedge/hal/` (`__init__.py`, `digital.py`, `sim.py`, `linux.py` with `/sys/class/pwm` backend): reject `on`/`pulse` on PWM pins, quantise `duty` rounding toward 0, refund envelope budget on early shutoff or failed authorize, persist envelope write-ahead, and independent supervisor process outside runtime on `linux` — *met on `sim` and `linux` (TSK-W1-01): `hal/pwm.py` (`check_pwm`, `quantize_duty`, `SysfsPwm`), `hal/__init__.py` (`_pwm_prepare`, `pin_state`), `hal/sim.py`, `hal/linux.py` (`_turn_on_pwm`, `_pwm_down`, enable line held by supervisor process), `hal/envelope.py` (`max_continuous_ms` reason); `tests/test_pwm.py`, `tests/test_hal_linux_pwm.py`*
- [ ] Implement `esp32s3` firmware: hardware PWM, TWDT plus hardware timer boot pull-down `enable_pin`, persist envelope write-ahead to NVS
- [x] Implement splitting `state()` on PWM pins into distinct numeric facts for `duty` and `frequency_hz` with `source`; update `neuroedge build` to check matching `unit`/scale (NE3001) and `gate lint` to reject numeric criteria in `on_block.confirms` (NE2002) — *met: `[sim.feedback_facts]` (`engine/compiler.py::check_feedback_facts`, `sim/session.py::_feedback_facts`); `gate lint` rejects numeric in `confirms` for all numeric criteria — `test_a_read_back_criterion_cannot_be_waived_by_a_person`*
- [ ] Add fixtures/tests (including `python/tests_linux/` on gpio-sim, hung process SIGSTOP test, and nightly Pi 5); update `docs/rfc/README.md` and `CHANGELOG.md`

## 9. Decisions on Open Questions (Q-57, 2026-09-30; Q-62, 2026-10-01)

Product owner delegated decision on open questions under the **maximum safety** principle: between two alternatives, choose the one that is fail-closed and harder to misuse, even if it requires more effort. The decisions below have been **incorporated into §3–§8**; this section is preserved as a decision log (Q-57). RFC approval still requires lead architect signature (`CONTRIBUTING.md` §3).

1. **PWM backend on `linux`:** **hardware PWM from kernel only** (`/sys/class/pwm`). No software PWM; boards without hardware PWM channels do not declare `pwm`. CI tests run against mock sysfs tree (same as `hal/sysfs.py`), hardware evidence on nightly Pi 5. *Why:* software pulses jitter and stall midway during process contention.
2. **Enable pin (added).** PWM channels connected to actuators **must** declare `enable_pin` — a `digital.out` line with on-board pull-down resistor; HAL enables `enable_pin` only during a gate-passed PWM command. *Why:* kernel PWM channels **continue running after process death**; gpiod lines are released when process exits, so pull-down disables driver even during crashes (`docs/spec/lab_mcp.md` §2.3).
3. **Envelope counts on-time** as entire duration with duty > 0, not multiplied by duty. *Why:* conservative, does not depend on load energy models.
4. **`state()`** returns `{value, source}` where `source` is `measured` (read back from hardware) or `commanded` (commanded value recorded); gates may only use `measured` values as facts, and boards without readback do not declare `feedback`. *Why:* never present sent commands as measured state.
5. **`duration_ms` is always mandatory**, bounded by gate `arguments` and board `max_continuous_ms` (RFC-0007). *Why:* no "run forever" PWM; continuing requires calling again through gate.
6. **Safe-direction commands are never blocked** (review 2026-10-01, Q-62). Commands returning actuators to a safe state (`digital.out` `off`, PWM setting `duty = 0`/releasing `enable_pin`, HAL autonomous commands upon expiry of `duration_ms`, expiry of `max_continuous_ms`, barge-in, BLOCK, connection loss, `hal.close()`) are never blocked; do not go through envelope, need no ALLOW or token, do not wait for `min_interval_ms` or post-boot; still recorded in traces with cause. *Why:* ensures actuators are immediately brought to safety under all emergency conditions; sole exception to mandatory ALLOW rule.
7. **`min_interval_ms` applies only to turn-on commands** (review 2026-10-01, Q-62). Minimum interval between commands applies only to commands transitioning actuators from safe state to operating state; does not apply to turn-off or safe-state commands. *Why:* commands shutting off actuators must never be delayed by rate limiting.
8. **Mandatory auto-off and envelope budget refund** (review 2026-10-01, Q-62). All turn-on commands on enveloped pins have finite duration `min(duration_ms, max_continuous_ms)`. Envelope reserves upfront that exact duration from `max_on_ms_per_window`; early shutoff refunds unused portion; failed `authorize` after reservation refunds entire held portion (no token spent, no pulse). *Why:* eliminates on-time budget leaks and prevents hardware pulsing when a command is rejected by gate.
9. **Envelope survives reboot** (review 2026-10-01, Q-62). Total held on-time is persisted write-ahead before turn-on to NVS on `esp32s3` or state file on `linux`; post-boot treats all recorded turn-ons as occurring immediately pre-boot, occupying budget until `window_s`; corrupt or missing records treated as entire window exhausted; still awaits `min_interval_ms` before first turn-on after reboot. *Why:* prevents repeated reboots to clear envelope limits in absence of reliable cross-boot clock.
10. **Mandatory envelope and removal of per-pin `actuator` flag** (review 2026-10-01, Q-62). All `digital_out` pins default to actuators, requiring envelope at `[capabilities.digital_out.envelope.<name>]`; only pins declared in `signal_pins` are exempt; all `pwm.pins` are always actuators, forbidden in `signal_pins`. Three tier-1 profiles in `boards/` must add envelopes wide enough for canonical traces to replay identically. *Why:* eliminates scattered `actuator = true` configurations, establishing safe fail-closed default for all load-controlling pins.
11. **Independent supervisor outside runtime process** (review 2026-10-01, Q-62). Auto-off timer and `duration_ms` must not live solely in runtime process which can hang; on `linux` uses dedicated supervisor process holding `enable_pin` and dropping on lost heartbeat; on `esp32s3` uses task watchdog (TWDT) and hardware timer booting to pull-down `enable_pin`. *Why:* prevents hung runtime process (SIGSTOP) leaving kernel driver outputting pulses past safe deadline.
12. **Numeric fact constraints from `feedback`** (review 2026-10-01, Q-62). `digital.out(...).state()` splits each quantity (`duty`, `frequency_hz`) into separate numeric fact with `source`; gate accepts only `source = measured` (from pins in `feedback.pins`), `commanded` reaching gate treated as missing measurement ⇒ BLOCK `criterion_unavailable`; `build` checks matching `unit` and scale (`BoardCapabilityError`, NE3001); forbids numeric criteria in `on_block.confirms` (`GateSchemaError`, NE2002). *Why:* preserves integrity of evaluation facts, prevents humans from confirming in place of sensor measurements, and prevents mistaking sent commands for actual state.
13. **Rejecting `on()` and `pulse()` on PWM pins** (review 2026-10-01, Q-62). Pins in `pwm.pins` reject `on` and `pulse` operations (`BoardCapabilityError`, no token spent); accept only `pwm` and `off` operations. *Why:* prevents accidentally outputting 100% duty burning loads beyond board's `max_duty` ceiling.
14. **`enable_pin` configuration constraint** (review 2026-10-01, Q-62). Every `enable_pin` declaration must explicitly specify `enable_active = "high"` and `pull = "down"`; other values rejected at load time (`BoardCapabilityError`). *Why:* verifies deterministically against schema that board hardware has safe pull-down mechanism on loss of control.
15. **Duty quantisation and forbidding shared `enable_pin`** (review 2026-10-01, Q-62). `duty` is quantised per `resolution_bits` and always rounds toward 0; each PWM channel must have distinct `enable_pin`, not shared with another channel (shared ⇒ rejected at load time `BoardCapabilityError`). *Why:* rounding toward 0 guarantees never exceeding `max_duty` due to quantisation error; distinct `enable_pin` isolates faults across actuators.
16. **`max_duty` mandatory, readbacks have units, `enable_pin` managed by HAL** (review 2026-10-01, Q-62). `max_duty` has no default, missing ⇒ `BoardCapabilityError`. Readback `duty` is `ratio` on `[0, max_duty]`, `frequency_hz` is `Hz` on board scale. `enable_pin` cannot be called from agent and is exempt from its own envelope. `min_interval_ms` measured from end of previous turn-on. *Why:* 1.0 default was only remaining permissive default; `build` requires unit and scale to verify RFC-0009 constraints.
