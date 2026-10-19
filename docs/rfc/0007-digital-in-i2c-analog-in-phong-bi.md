# RFC-0007: `digital.in`, Read-Only I2C Bus, `analog.in`, and Per-Pin Safety Envelope

| | |
|:---|:---|
| **RFC ID** | 0007 |
| **Title** | Three new input primitives (`digital.in`, read-only I2C, `analog.in`) and safety envelope declared in `board.v1` |
| **Affected Contract** | `board.v1` *(adds keys `digital_in`, `i2c`, `analog_in`, and `envelope` block)* · error code catalog `neuroedge-prd.md` Appendix B *(adds NE1003, expands NE5001 scope — §4)* · does **not** touch `gate.v1`, `trace.v1` |
| **Related PRD Requirements** | FR-HAL-01, FR-HAL-04, FR-HAL-05 |
| **Author** | — |
| **Date Opened** | 2026-09-30 |
| **Status** | ✅ Approved (2026-10-01) — lead architect signed on PR #75; amended per review 2026-10-01 (§9, Q-62); implemented in second PR |
| **Approver** | **Lead Architect — mandatory.** Envelope touches the path to physical pins (§5), and §4 identifies a schema tightening requiring signature |

> **When an RFC is required:** `CONTRIBUTING.md` §3 — modifying `schemas/*.json`. This RFC modifies `schemas/board.v1.json`.
> Underlying decisions: `neuroedge-prd.md` §15 Q-52 (MVP is full v1.0 comprising four primitive packages, single release,
> slip schedule rather than cut), Q-53 (four packages mandatory across all three Tier 1 targets; **`analog.in` moved from RFC-motion
> to this RFC**), Q-55 (NeuroBrain — now NeuroEdge Lab, Q-71 — in MVP). Sources: FOFOCA robot draft (`docs/architecture/15-target-architecture.md` §4.3),
> now consolidated into this RFC, and `docs/spec/lab_mcp.md` §7, §8. Tasks: TSK-N0-03 (draft this RFC), TSK-N2-01
> (envelope hook), TSK-N2-02 (atomic check-and-reserve), TSK-N3-03 (ADC spike).

## 1. Problem

HAL has five primitives (`PRIMITIVES` in `python/neuroedge/hal/board.py`). Three real needs cannot be expressed:

1. **Reading logic levels** — push buttons, limit switches, door contacts. `digital.out` is write-only.
2. **Observing what is attached to the I2C bus** — board bring-up requires scanning the bus and reading unknown devices without writing drivers in advance.
3. **Reading analog voltages** (ADC) — pressure, current, battery.

And an omitted safety invariant: outputs are only bounded by single-use tokens, not by **cumulative physical consequences**. A `digital.out("porch_light").on()` repeating through a valid gate every second keeps the load energized continuously. Time accumulation cannot live inside gates (pure gates, invariant 4), so it must be declared and enforced elsewhere.

## 2. Why the Current Schema Does Not Solve It

- `schemas/board.v1.json` only specifies five `capabilities` keys (`audio_in`, `audio_out`, `digital_out`, `sensor_read`, `display`). Other keys **pass validation** because `capabilities` lacks `additionalProperties: false`, but have no schema shape to reconcile against agent `[requires]` (FR-HAL-04).
- `digital_out` declares only `pins` and `backend`; there is no place to declare on-time duration limits or frequency limits.
- **Why not expand `sensor.read`** (TSK-N0-03 requires justification):
  - `sensor.read` is a contract for *"reading a named scalar value"*: `BoardProfile.require_sensor` rejects names outside `sensor_read.sensors`, and `sensor_read` is recorded as a `sensor_read` event for replay reloading (`docs/spec/simulation_coverage.md`). Bus scans return **sets of unnamed devices**, bus operations carry side effects, and lack names for replay.
  - Stuffing bus/address details into `sensor.read` blurs `[requires]`: an agent declaring `"sensor.read" = { sensors = ["motion"] }` (see `fixtures/agents/home-voice/agent.toml`) means *"requires this exact sensor"*; if `sensor.read` also implies *"permission to access raw bus"*, a board with a valid sensor that disallows scanning still "matches".
  - `digital.in` is an instantaneous dimensionless logic level; `analog.in` is a scaled numeric value with units. Both require distinct declarations (pins, channels, scales) that `sensors: string[]` cannot carry.
  - FR-HAL-01 deliberately closed the primitive set (firmware capability table is a static array). Expanding an existing primitive with hidden semantics is worse than adding a named primitive: the `missing_primitives()` check path cannot detect it.

## 3. Proposed Change

### 3a. `digital.in`

```toml
[capabilities.digital_in]
pins    = ["button_boot", "door_contact_raw"]
backend = "esp_driver_gpio"        # same role as digital_out's `backend` field
```

Naming: primitive `digital.in` in `[requires]`, board key `capabilities.digital_in`; HAL adds `HardwareAbstractionLayer.digital_in(pin, called_from=...) -> bool` alongside `digital_out`; agent API is `digital.input("door_contact").level()` (avoiding Python keyword `in`; pin name is logical name, FR-HAL-06). Pin must be present in `digital_in.pins`: undeclared pin ⇒ three-part `BoardCapabilityError` (NE3001) at load, and also rejected at call time. Reading **moves nothing** so requires no token (like `sensor.read`), and is recorded as a `digital_in` event for replay reloading; `sim` replays recorded values (pin equivalent of `set_sensor`), no richer than reference boards. Read failure ⇒ `PerceptionUnavailableError` (§3e).

`digital.in` values enter gates as `bool` facts, accompanied by a HAL read timestamp on the session's monotonic timeline. Read timestamp is used to compute `age_ms`: evaluation instant is the verdict event offset on the same monotonic timeline; traces record both read timestamp and `age_ms`; `replay` recomputes and compares; `age_ms < 0` (read timestamp after evaluation instant) ⇒ BLOCK `criterion_unavailable`. HAL reads `digital.in` **at evaluation instant**, without using cached values; age exceeding fixed code ceiling `DIGITAL_IN_MAX_AGE_MS = 100` ⇒ BLOCK `criterion_unavailable` (`bool` criteria lack `max_age_ms`). This ceiling catches hung read paths; hardware-stuck input levels cannot be detected by age, so critical gates should incorporate an additional independent criterion.

### 3b. Read-Only I2C Bus

```toml
[capabilities.i2c]
buses = [{ id = "i2c0", devices = [{ name = "ads1015", address = 0x48, readable_registers = [0x00, 0x01] }] }]
```

"Read-only" means **no data write path**; the sole write the API emits is the register pointer byte below.

- **Scanning via read-byte** (TSK-N3-01): probing addresses via read operations only; **never** quick-write.
- **Addresses outside allowlist** (not in `devices`) are only **reported as present** during scan: beyond that probing read-byte, they are **never read or written**.
- **Allowlisted devices** readable via receive-byte (no register address). **Register reading** (writing register pointer then repeated-start reading) is permitted only when register is in `readable_registers` declared by board for that device; undeclared registers rejected like undeclared pins (`BoardCapabilityError`), emitting no transaction onto the bus. Reason for strictness: some chips interpret any write as a command.
- No data write function exists in the API. Each read records an `i2c_read` event; bus NACK or timeout ⇒ `PerceptionUnavailableError` (§3e). NeuroEdge Lab's `lab_read` tool (formerly NeuroBrain, Q-71) (`docs/spec/lab_mcp.md` §6) reads pins via `digital.in` of this RFC; `[lab]` flag defaults off and never relaxes allowlist.
- On `linux`, tests run on `i2c-stub` (Block N3, roadmap); `sim` only replays recorded values without physical scanning.

### 3c. `analog.in`

```toml
[capabilities.analog_in]
channels = [{ name = "supply_v", unit = "V", min = 0.0, max = 5.0, resolution_bits = 12 }]
```

Returns number with declared unit and scale; values outside `[min, max]` are read errors, not silently clamped. Safety thresholds on this value reside **not** in the primitive but in gate `numeric` criteria ([RFC-0009](0009-tieu-chi-so-numeric.md)). `analog.in` values enter gates as `numeric` criteria, accompanied by HAL read timestamp on the session's monotonic timeline; read timestamp computes `age_ms`; `age_ms < 0` ⇒ BLOCK `criterion_unavailable`. Channel-to-criterion binding: when an agent binds a `numeric` criterion to an `analog.in` channel, `neuroedge build` verifies matching `unit` and that channel `[min, max]` fits within criterion `range`; mismatch ⇒ `BoardCapabilityError` (NE3001) at build. A `numeric` criterion bound to `analog.in` cannot appear in `on_block.confirms` of RFC-0006: `gate lint` rejects (`GateSchemaError`, NE2002). **Conditional**: `linux` test path depends on spike TSK-N3-03 (I2C ADC chip with hwmon driver on `i2c-stub`, runner disabling `CONFIG_IIO`). Spike failure does not drop `analog.in` (Q-52, Q-53 require presence across all three targets): `analog.in` is tested nightly on a self-hosted runner with real ADC hardware (Pi 5 + I2C ADC), and **blocks I2a exit criteria** until that evidence exists — unverified primitives on hardware cannot be released. Each read records an `analog_in` event; sensor missing or timeout ⇒ `PerceptionUnavailableError` (§3e).

### 3d. Per-Pin Safety Envelope — Declared in `board.v1`

```toml
[capabilities.digital_out]
pins        = ["porch_light", "status_led"]
signal_pins = ["status_led"]    # signal-only pin, no load attached

[capabilities.digital_out.envelope.porch_light]
window_s              = 3600      # sliding window
max_on_ms_per_window  = 1800000   # max total on-time in window
min_interval_ms       = 2000      # min interval before next on command
max_continuous_ms     = 600000    # single on-time ceiling, independent of gate `arguments`
```

These four keys are shared with RFC-0010, RFC-0011. Declare envelope at `[capabilities.digital_out.envelope.<name>]` with `<name>` as the pin name.

**Actuators and `signal_pins`:** Actuator flags avoid per-pin `actuator = true` because `digital_out.pins` is a string array. Instead, **all `digital_out` pins default to actuators, requiring envelopes**. Exception: `enable_pin` in RFC-0010, RFC-0011 managed internally by HAL, inaccessible to agents, exempt from dedicated envelope (its on-time is bounded by the envelope of the channel it serves). Pins that are signal-only (no load attached) are declared in `[capabilities.digital_out] signal_pins = [...]` (subset of `pins`, disjoint with `pwm.pins`). Pins in `signal_pins` do not require envelopes. Missing envelope on pins outside `signal_pins` ⇒ `BoardCapabilityError` (NE3001) at profile load. Reason: hardware limits must withstand even lax gates.

**Safe-direction commands are never blocked:**
- Safe-direction commands include: `digital.out` `off`; all autonomous HAL commands upon expiration of `duration_ms`, `max_continuous_ms`, barge-in, BLOCK, loss of communication, `hal.close()`.
- These commands **are never blocked**: they bypass envelopes, require no ALLOW or token, and do not wait for `min_interval_ms` or post-boot delay. This is the **sole exception** to the "no command reaches hardware without ALLOW" rule. Commands still record trace events with causes.
- `min_interval_ms` **applies only to on commands**, i.e. commands transitioning mechanisms from safe state to active state, measured from when the previous on command **ended** (pin returned to safe state). An `off` command immediately following `on` is never rejected by `min_interval_ms`.

**Mandatory auto-off and reservation refunds:**
- Every on command on enveloped pins has a finite duration. At turn-on, HAL and firmware schedule auto-off at `min(command duration, max_continuous_ms)`. Durationless `on()` ⇒ duration = `max_continuous_ms`.
- The envelope reserves exactly that duration from `max_on_ms_per_window`. Early turn-off refunds unused duration.
- Failed `authorize` after reservation refunds 100% of reserved duration: zero token consumed, zero pulse emitted to pin.

**Hooks and firmware enforcement (TSK-N2-01, RB-4):**
- Hook lives in `HardwareAbstractionLayer.digital_out` (`python/neuroedge/hal/__init__.py`), injected alongside `authorize`. Ordering: `require_pin → envelope → authorize → record`. Envelope precedes `authorize` so rejected commands consume no tokens; rejected commands raise `EnvelopeRefusedError` (§3e) and record `envelope_refused` events.
- Check-and-reserve is an atomic step (TSK-N2-02) so concurrent commands do not slip past remaining budget together.
- Envelope hook is not Python-only: `esp32s3` firmware enforces identical rules; envelope table is a `const` table generated at build from `board.v1` in flash (RB-4 of `docs/spec/hal_mcu_review.md`).

**Out-of-process independent supervision:**
- Auto-off timers and `duration_ms` must not reside solely inside a runtime process that can hang.
- On `esp32s3`: task watchdog (TWDT) plus hardware timer; watchdog reset boots with pins in safe pull-down state.
- On `linux`: actuator pin lines held by a dedicated supervisor process; runtime sends heartbeats; missed heartbeats past deadline ⇒ supervisor releases line and de-energizes pin.

**Envelopes survive reboots:**
- Cumulative on-time reserved in window is persisted before turn-on (write-ahead): NVS on `esp32s3`, state file on `linux`; `sim` emulates identical rules.
- Reboots lack trusted cross-reboot clocks, so all recorded on-times are treated as occurring immediately prior to boot, consuming budget for `window_s` post-boot. Unreadable, corrupt, or missing records ⇒ treat entire window as spent (fail-closed).
- Post-boot, each enveloped pin still waits `min_interval_ms` before its first turn-on. Pins in `signal_pins` lacking `envelope` ⇒ unchanged behavior.

### 3e. Accompanying Code

`PRIMITIVES` split into core and extended, `_CAPABILITY_KEYS` adds three keys: details in [RFC-0013](0013-nguyen-thuy-tuy-chon-va-nhieu-bo-tham-chieu.md).

Errors (`python/neuroedge/errors.py`) — each failure kind has a distinct code for post-audit, none leading to ALLOW:

| Scenario | Error | Trace |
|:---|:---|:---|
| Envelope rejected | New class `EnvelopeRefusedError` (**NE1003**, subclass of `ActionContractViolation`); token is not consumed | `envelope_refused` |
| Read failure (bus NACK, timeout, sensor missing) | `PerceptionUnavailableError` (NE5001) ⇒ undecided criterion ⇒ BLOCK `criterion_unavailable` (as in RFC-0009) | `digital_in` / `i2c_read` / `analog_in` |
| Undeclared pin, channel, device, or register | `BoardCapabilityError` (NE3001) at load; calls to undeclared names are also rejected without touching bus or pins | — |

NE5001 is currently defined only at load/build (`neuroedge-prd.md` Appendix B); this RFC **expands its scope** to runtime for failed HAL reads — §4.

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | Three Tier 1 profiles in `boards/` must add envelopes (or declare `signal_pins`) in implementation PR, with values wide enough so three canonical traces replay identically (e.g. `door_lock` receives 30,000 ms pulse ⇒ `max_continuous_ms` ≥ 30000); no external profiles exist. **Tightening point:** `digital_in`, `i2c`, `analog_in` currently accepted in *any* shape because `capabilities` is not closed; after RFC they have mandatory shapes. All `digital_out` pins default to actuators requiring envelopes unless listed in `signal_pins`. Lead architect must confirm this does not require `board.v2` (RFC-0002 §9.1 warned of same trap: modifying shape after release is tightening) |
| Do currently invalid files become valid? | Yes — profiles declaring three new keys with correct shapes and `envelope` block |
| Is a schema version bump required (`v1` → `v2`)? | Proposed **no**, provided shapes in §3 are frozen **before** external profiles use them |
| Impact on hashes / digital signatures of published gates? | None — `gate.v1` unchanged |
| Impact on the three canonical trace files? | None — three Tier 1 profiles configured with sufficiently wide envelopes in implementation PR so three canonical traces replay identically (e.g. `max_continuous_ms` ≥ 30000 for `door_lock`). Four new event types (`digital_in`, `i2c_read`, `analog_in`, `envelope_refused`) do not alter `trace.v1` because `type` is open string; they add rows to event table in `docs/spec/simulation_coverage.md` |
| Error code catalog (`neuroedge-prd.md` Appendix B)? | Yes, upon approval: add row `EnvelopeRefusedError` NE1003 (Runtime · envelope rejected · raises exception, pin not actuated, token not consumed, records `envelope_refused`); NE5001 row expands timing column to *Runtime (HAL read)* with BLOCK `criterion_unavailable` behavior |
| Which gates in `digests.lock` change digest? | No gates |
| Does the `NETR` layout or C walker need to change? | No |
| Which answers in the tool-call corpus (`expected_results.yaml`) change? | None — without envelope, `digital_out` retains same error ordering (regression contract `docs/spec/lab_mcp.md` §7.1). Envelope rejections add new cases in dedicated corpus |

## 5. Safety Impact

- **Gates are not more lax in any way**: `gate.v1`, resolution semantics, and the five inheritance principles (Appendix B.5) remain unchanged. Envelopes are an **independent, secondary check layer**, adding rejection capabilities only.
- **Gates remain pure (invariant 4):** accumulation of on-time and frequency lives in HAL, not in gates. This is why it is declared in `board.v1` rather than adding fields to gates.
- **Safe-direction commands are never blocked:** `digital.out` `off` and autonomous HAL commands upon expiration, `max_continuous_ms`, BLOCK, barge-in, communication loss, `hal.close()` bypass envelopes, require no ALLOW or token, and do not wait for `min_interval_ms` or post-boot delay. This is the sole exception to the "no command reaches hardware without ALLOW" rule. Commands still record trace events with causes.
- **Fail-closed default:** commands exceeding envelopes are rejected prior to `authorize`; there is no "warn and allow" mode. `[lab]` flag is never used as an envelope exception. All `digital_out` pins default to actuators requiring envelopes (except pins declaring `signal_pins`). Mandatory auto-off at `min(command duration, max_continuous_ms)`. Failed `authorize` refunds 100% of reserved duration.
- **Envelopes survive reboots:** cumulative on-time reserved is persisted before turn-on (write-ahead: NVS on `esp32s3`, state file on `linux`). Post-boot, all recorded on-times are treated as occurring immediately prior to boot, consuming budget for `window_s`; corrupt or missing records ⇒ treat entire window as spent; wait `min_interval_ms` before first post-boot turn-on.
- **Out-of-process supervision:** auto-off timers do not live only in a runtime process that can hang; TWDT and hardware timer on `esp32s3` (watchdog reset boots with pin pulled down to safe state); supervisor process holds line and runtime heartbeats on `linux` (missed heartbeat releases line de-energizing pin); SIGSTOP on runtime process causes actuators to autonomously return to safe state within declared duration plus margin.
- **Fail-closed inputs and timing invariants:** failed reads or read timestamp after evaluation instant (`age_ms < 0`) ⇒ `PerceptionUnavailableError` ⇒ BLOCK `criterion_unavailable`, never ALLOW (§3e). `numeric` criteria bound to `analog.in` strictly validate scale and units at build, forbidding user confirmation replacement (`on_block.confirms`).
- **Inputs have no data write privileges:** `digital.in`, `analog.in` do not move pins. I2C has no data write path; sole write is a pointer to a register in `readable_registers` of allowlisted devices, and addresses outside allowlist are never read or written beyond probing read-byte (§3b). Residual risk: *information disclosure via read* (mitigated by allowlist), and a chip interpreting pointer writes as commands — responsibility of board when declaring `readable_registers`.
- Requires lead architect approval due to touching physical pin paths (`digital_out`).

## 6. Alternatives Considered and Rejected

| Alternative | Reason for Rejection |
|:---|:---|
| Expand `sensor.read` (bus scan, logic level, ADC) | See §2: named scalar vs. unnamed set; blurs `[requires]`; ADC needs scale and unit |
| Declare envelope in `gate.v1` | Time accumulation is state, destroys gate purity (invariant 4); gates shared via registry do not know hardware |
| Check envelope **after** `authorize` | Rejected commands already consumed tokens; fixing bug later wastes a token pointlessly |
| I2C allows arbitrary data writes (even with register allowlist) | Opens path to mutate device state outside all gates; reserved for dedicated RFC if real need arises. Narrow form accepted (§3b): only write pointer of register declared in `readable_registers`, immediately before repeated-start read — narrowest path that still reads real sensors |
| Read arbitrary registers on allowlisted devices | Some chips treat any write (even pointer write) as command; only registers declared by board may be pointed to |
| Optional envelope for all pins | Actuator pins must have hardware limits standing even when gates are lax. All `digital_out` pins default to actuators requiring envelopes; only pins declared in `signal_pins` are signal-only without load; dropped `actuator = true` flag because `pins` is a string array |
| Rely only on soft timers in runtime process | Process can hang (SIGSTOP) or crash; must have hardware watchdog on MCU and independent supervisor process on Linux to restore pins to safe state |
| Apply `min_interval_ms` to off commands (`off`) | Violates §9 item 7: commands restoring mechanisms to safe state are never blocked, `off` immediately following `on` must not be refused |
| ADC spike failure ⇒ move `analog.in` to `TODOS.md` | Q-53 mandates `analog.in` presence; unverified primitives on hardware cannot be released — tested on self-hosted runner and blocks I2a exit criteria (§3c) |
| Keep `analog.in` in RFC-motion | Q-53: `analog.in` is an input package independent of `motion.*`; constraints on readings use `numeric` criteria, requiring no motion |

## 7. Verification Evidence

- [ ] Valid example: `boards/` profiles declaring `digital_in`, `i2c`, `analog_in`, `signal_pins`, and `envelope` (reference boards, RFC-0013); three Tier 1 profiles in `boards/` supplemented with sufficiently wide envelope declarations (`door_lock` has `max_continuous_ms` ≥ 30000) replay three canonical traces identically
- [ ] Counterexamples: malformed keys (`pins` not an array), `address` outside 0x03..0x77, `min > max`, `window_s` <= 0, `max_continuous_ms` <= 0; `digital_out` pins outside `signal_pins` missing envelopes ⇒ `BoardCapabilityError` (NE3001); `signal_pins` containing pin names absent from `pins` ⇒ `BoardCapabilityError`
- [x] Safe command tests: `digital.out` `off` command is never blocked, executing successfully even within `min_interval_ms` immediately after `on`, bypassing envelopes, requiring no ALLOW or token, without post-boot delay; `min_interval_ms` only rejects subsequent on commands — *passed (`sim`, `linux`): `test_off_needs_no_envelope_no_proof_and_no_waiting`, `test_min_interval_refuses_only_the_next_on_and_runs_from_the_end_of_the_previous_on`, `test_an_off_on_a_pin_with_an_unreadable_record_still_works`, `test_an_off_straight_after_a_restart_does_not_wait_for_min_interval` (`tests/test_envelope.py`)*
- [x] Mandatory auto-off and reservation refund tests: durationless `on()` auto-offs at `max_continuous_ms`; timed command auto-offs at `min(command duration, max_continuous_ms)`; envelope reserves exact duration; early off refunds unused excess; failed `authorize` refunds 100% of reserved time, consuming zero tokens, emitting zero pulse to pin — *passed: `test_an_on_without_a_duration_turns_off_at_max_continuous_ms`, `test_the_reservation_is_min_of_the_duration_and_max_continuous_ms`, `test_the_budget_holds_exactly_the_reserved_time_and_an_early_off_refunds_the_rest`, `test_a_command_authorize_refuses_gives_back_every_millisecond_it_reserved`, `test_a_refused_command_does_not_consume_the_verdict_token`; on `linux`: `test_an_on_with_no_duration_is_turned_off_by_the_hal_at_max_continuous_ms` (`tests/test_hal_linux_envelope.py`), `tests_linux/test_gpio_envelope.py`*
- [ ] Reboot survival tests: on-time persisted before turn-on (write-ahead: NVS on `esp32s3`, state file on `linux`); post-reboot, recorded time consumes budget in `window_s`; corrupt or missing records ⇒ reject turn-on (treat entire window as spent); first turn-on post-boot within `min_interval_ms` rejected; all rejections raise `EnvelopeRefusedError` (NE1003) with `envelope_refused` event; concurrent commands do not slip past budget together (TSK-N2-02) — *passed on `sim` and `linux`: `test_the_on_time_is_written_before_the_pin_is_turned_on`, `test_after_a_restart_what_was_recorded_counts_against_the_window_and_the_pin_waits`, `test_a_corrupt_record_makes_the_pin_refuse_every_on`, `test_a_missing_record_is_refused_unless_this_is_declared_a_new_rig`, `test_a_record_that_cannot_be_written_refuses_the_command_and_holds_nothing`, `test_two_concurrent_commands_on_one_pin_give_exactly_one_envelope_refused`, `tests_linux/test_gpio_envelope.py::test_a_second_session_after_a_restart_waits_out_min_interval_before_it_turns_a_pin_on` (CI run 37153005998); NVS on `esp32s3`: pending, belongs to TSK-N7-02*
- [ ] Out-of-process supervision tests: runtime process suspended (SIGSTOP) while actuator pin is on ⇒ actuator autonomously returns to safe state within duration plus margin (watchdog reset boots pulling pin down on `esp32s3`, supervisor disconnects line upon heartbeat loss on `linux`) — *passed on `linux`: `tests/test_supervisor.py::test_a_runtime_stopped_with_sigstop_while_a_line_is_on_loses_the_line` (real process, mock gpiod), `tests_linux/test_gpio_envelope.py::test_a_runtime_stopped_with_sigstop_while_an_actuator_is_on_loses_the_line` (gpio-sim, CI run 37153005998); watchdog `esp32s3`: pending, belongs to TSK-N7-02*
- [ ] Host ↔ C equivalence tests (RB-4): `esp32s3` firmware enforces identical envelope rules from `const` table in flash; host Python ↔ firmware C equivalence test suite for envelopes and `digital.in`, I2C, ADC drivers
- [x] Fact age tests: `digital.in` and `analog.in` read timestamps recorded in traces with `age_ms`; `replay` recomputes and compares; `age_ms < 0` (read timestamp after evaluation instant) ⇒ BLOCK `criterion_unavailable` — *`analog.in` passed (TSK-I2a-04): `test_a_reading_older_than_max_age_is_unavailable_and_exactly_that_old_is_valid`, `test_a_read_mark_after_the_evaluation_instant_is_unavailable`, `test_replay_reproduces_every_verdict_from_the_recorded_readings`, `test_replay_distrusts_a_trace_whose_age_was_altered` (`tests/test_analog_in.py`); `digital.in` passed (TSK-I2a-02): `test_a_level_exactly_as_old_as_the_ceiling_passes_and_one_ms_older_does_not`, `test_a_level_read_after_the_verdict_is_unavailable`, `test_the_fact_carries_its_source_and_read_marks_into_the_trace`, `test_replay_does_not_trust_an_age_the_trace_cannot_account_for` (`tests/test_digital_in.py`)*
- [x] Test `analog.in` channel binding to `numeric` criteria: `neuroedge build` verifies matching `unit` and channel `[min, max]` fits within criterion `[range_min, range_max]`; mismatch ⇒ `BoardCapabilityError` (NE3001); `numeric` criteria bound to `analog.in` in `on_block.confirms` ⇒ `gate lint` rejects (`GateSchemaError`, NE2002) — *passed (TSK-I2a-04): `test_a_criterion_range_that_contains_the_channel_range_builds`, `test_a_criterion_range_the_channel_can_leave_is_refused_at_build`, `test_a_criterion_in_another_unit_than_the_channel_is_refused_at_build`, `test_a_numeric_criterion_bound_to_a_channel_cannot_be_in_confirms`, `test_gate_lint_refuses_the_same_gate` (`tests/test_analog_in.py`)*
- [x] Scan on `i2c-stub`: addresses outside allowlist only listed; all read calls to them rejected and `i2c-stub` observes zero transactions beyond probing read-byte — *passed (CI run 37153005998): `tests_linux/test_i2c_read.py::test_a_scan_lists_the_unlisted_chip_and_a_read_of_it_is_refused` (`lm75` 0x48 listed, read rejected), `test_an_undeclared_register_sends_nothing_to_the_chip` (chip register pointer unmoved)*
- [x] I2C on `i2c-stub`: reading registers in `readable_registers` succeeds (pointer write then repeated-start read); undeclared registers rejected, emitting no transaction; API contains zero data write functions — *passed on kernel (CI run 37153005998): `tests_linux/test_i2c_read.py::test_a_declared_register_reads_back_what_the_chip_holds`, `test_an_undeclared_register_sends_nothing_to_the_chip`; API lacks write function: `tests/test_hal_i2c.py::test_the_i2c_api_has_no_data_write_anywhere`*
- [x] Failed reads (NACK, timeout, sensor missing) on `digital.in`, I2C, `analog.in` ⇒ `PerceptionUnavailableError` ⇒ BLOCK `criterion_unavailable`, never ALLOW — *`analog.in` passed (TSK-I2a-04): `test_a_reading_the_channel_cannot_give_blocks_criterion_unavailable`, `test_a_read_that_fails_is_unavailable_and_recorded`, `test_an_adc_that_fails_mid_session_blocks_criterion_unavailable` (`tests/`); `tests_linux/test_analog_in.py::test_an_adc_that_is_not_there_blocks_criterion_unavailable` on `i2c-stub` (CI run 37153005998); `digital.in` passed (TSK-I2a-02): `test_any_failed_read_blocks_even_a_gate_that_fails_open`, `test_an_input_nobody_set_blocks_criterion_unavailable`, `test_a_line_that_fails_to_read_blocks_criterion_unavailable_on_linux` (`tests/test_digital_in.py`, `tests/test_digital_in_linux.py`), `tests_linux/test_gpio_sim.py::test_an_input_line_that_cannot_be_read_blocks_criterion_unavailable` (gpio-sim); I2C (TSK-I2a-03): `tests_linux/test_i2c_read.py::test_a_device_that_does_not_answer_is_perception_unavailable_after_one_retry`, `test_a_missing_node_is_perception_unavailable_not_a_default` (`i2c-stub`)*
- [x] `analog.in` on `linux`: spike TSK-N3-03 passed on `i2c-stub`, or nightly evidence from self-hosted runner with real ADC before I2a exit criteria — *passed on `i2c-stub` 2026-10-03 (`ads7828`, `ina219`; PR #87)*
- [ ] `neuroedge gate lint` and `neuroedge verify` remain green; three canonical traces unchanged

## 8. Tasks upon Approval

- [x] Update `schemas/board.v1.json`: add `digital_in`, `i2c`, `analog_in`, `signal_pins`, and schema for `envelope` block; mandate envelopes for all `digital_out` pins outside `signal_pins` — *passed: `digital_in`, `i2c`, `analog_in`, `signal_pins`, `envelope`; missing envelope ⇒ NE3001 — `tests/test_board_fixtures.py`*
- [x] Supplement envelope blocks for three Tier 1 profiles in `boards/` wide enough (`door_lock` has `max_continuous_ms` ≥ 30000) so three canonical traces replay identically — *passed: three Tier 1 profiles and `sim-rpi5` — `test_the_envelopes_are_wide_enough_for_the_canonical_traces`; `neuroedge verify --targets sim` green*
- [x] Document the sole exception to the "no command reaches hardware without ALLOW" rule for safe-direction commands (`digital.out` `off`, autonomous HAL cutoff) in `docs/spec/threat_model.md` §1 upon implementation — *passed: `docs/spec/threat_model.md` §1*
- [ ] Update corresponding Appendix in `docs/spec/core_contracts.md` and FR-HAL-01 in `neuroedge-prd.md`; assign `Q-N` in §15 for new decisions
- [x] `neuroedge-prd.md` Appendix B: add row `EnvelopeRefusedError` NE1003, expand NE5001 scope to runtime (§4); `python/neuroedge/errors.py` add class and update docstring `PerceptionUnavailableError` — *passed: NE1003 and NE5001 in Appendix B, `EnvelopeRefusedError` class and docstring `PerceptionUnavailableError` in `errors.py`, `__all__`, `docs/spec/python_api.md`*
- [x] `docs/spec/simulation_coverage.md`: add events `digital_in`, `i2c_read`, `analog_in`, `envelope_refused` to event table — *passed: `digital_in`, `i2c_read`, `analog_in`, `envelope_refused` in §3*
- [ ] `docs/spec/lab_mcp.md` §8: "spike failed" branch per §3c (self-hosted runner, blocking I2a exit criteria), replacing moving ADC to `TODOS.md`
- [x] Update `neuroedge-roadmap.md` (TSK-N0-03 done; TSK-N2-01, TSK-N2-02, TSK-N3-03; I2a exit criteria requires hardware ADC evidence) *(Completed 2026-10-04: rows TSK-N0-03, N2-01 → N2-05, N3-03 and I2a exit criteria 8 in roadmap)*
- [x] Implementation in `python/neuroedge/hal/` (`board.py`, `__init__.py`, `sim.py`, `linux.py`): per-pin envelope, mandatory auto-off, reservation refund on early off or authorize failure, write-ahead persistent state file on linux, supervisor process holding lines and runtime heartbeats; `sim` model no richer than reference boards — *passed: `hal/envelope.py` (envelope, auto-off, reservation refund, write-ahead state file), `hal/supervisor.py` (supervisor process and heartbeats), wired into `hal/__init__.py`, `sim.py`, `linux.py`; `sim` matches numbers of mirrored board (`test_a_sim_board_has_exactly_the_envelope_numbers_of_the_board_it_mirrors`). Supervision defaults **enabled** on `linux`, fail-closed (`supervisor_unavailable`), explicitly disabled via `supervise=False` / `NEUROEDGE_LINUX_SUPERVISE=0` and recorded in `metadata.supervision`*
- [ ] Implementation in C firmware (`esp32s3`): `const` envelope table generated from `board.v1` in flash (RB-4 of `docs/spec/hal_mcu_review.md`), write-ahead persistence in NVS, auto-off via TWDT and hardware timer, drivers for `digital.in`, read-only I2C, ADC
- [x] Implement `analog.in` channel binding validation with `numeric` criteria and forbid in `on_block.confirms` in `neuroedge build` / `gate lint`; record read timestamp and compute `age_ms` — *passed for `analog.in` (TSK-I2a-04): `check_analog_facts` in `engine/compiler.py` (bound via `[sim.analog_facts]`), forbidden `confirms` already enforced by gate resolver for all `numeric` criteria, read timestamp `Fact.read_ms` in `SimSession._analog_facts`; read timestamp and `age_ms` for `digital.in` passed (TSK-I2a-02, `engine/gate.py`, `engine/decision_tree.py`)*
- [ ] Add/adjust fixtures and tests: host Python ↔ firmware C equivalence test suite for envelope and drivers (RB-4); SIGSTOP out-of-process supervision test — *SIGSTOP passed (as above); host Python ↔ firmware C equivalence test suite: pending, belongs to TSK-N7-02*
- [ ] Update the RFC's row in `docs/rfc/README.md` and an entry in `CHANGELOG.md` `[Chưa phát hành]`

## 9. Decisions on Open Questions (Q-57, 2026-09-30; Q-62, 2026-10-01)

Product owner delegated resolving open questions under the **maximum safety** principle: between two alternatives, choose the fail-closed and harder-to-misuse option, even when more costly. The decisions below **have been incorporated into §3–§8**; this section is retained as the decision log (Q-57), and in case of any discrepancy this section prevails. RFC approval still requires lead architect signature (`CONTRIBUTING.md` §3).

1. **API naming.** Primitive named `digital.in` in `[requires]`; board key `capabilities.digital_in`; HAL method `digital_in(pin)` alongside `digital_out`; agent API is `digital.input("door_contact").level()`. *Why:* matches pattern of `digital.out`, avoids Python keyword `in`; pin names remain logical names (FR-HAL-06).
2. **I2C register reading.** Permitting address-based register reads (writing pointer then repeated-start reading) **only** for devices on board allowlist **and** registers in declared `readable_registers` for that device; otherwise allowlisted devices only support receive-byte. Addresses outside allowlist **are never read or written** — reported as present only via probing read-byte during scan. Zero data write path exists. Bus scanning via read-byte only (TSK-N3-01). *Why:* some chips treat any write as a command; restricting the sole write to pointers of declared registers is the narrowest path that still reads real sensors.
3. **If ADC spike (TSK-N3-03) fails:** `analog.in` is tested on a self-hosted runner with real ADC hardware (Pi 5 + I2C ADC) nightly, and **blocks I2a exit criteria** until that evidence exists. *Why:* Q-53 mandates `analog.in` presence; unverified primitives on hardware cannot be released.
4. **Errors and traces.** Envelope rejected ⇒ new class `EnvelopeRefusedError` (**NE1003**, subclass of `ActionContractViolation`), trace event `envelope_refused`, token is not consumed. Read failure (bus NACK, timeout, sensor missing) ⇒ `PerceptionUnavailableError` (NE5001) ⇒ undecided criterion ⇒ BLOCK. Undeclared pin or device ⇒ `BoardCapabilityError` (NE3001) at load. Trace events: `digital_in`, `i2c_read`, `analog_in`. *Why:* each failure kind has a distinct code for post-audit, and none leads to ALLOW.
5. **Envelope keys and actuator flags** (amended in 2026-10-01 review). `window_s`, `max_on_ms_per_window`, `min_interval_ms`, and `max_continuous_ms` (shared with RFC-0010, RFC-0011). Declared at `[capabilities.digital_out.envelope.<pin_name>]`. All `digital_out` pins default to actuators, requiring envelopes. Signal-only pins (no load attached) declared in array `signal_pins = [...]`. Dropped `actuator = true`. Three Tier 1 profiles in `boards/` must add sufficiently wide envelopes in implementation PR. *Why:* `digital_out.pins` is a string array leaving no place to attach `actuator` properties; defaulting to actuators maximizes safety, missing zero physical loads.
6. **Envelopes survive reboots** (amended in 2026-10-01 review). Cumulative on-time reserved in window is persisted before turn-on (write-ahead): NVS on `esp32s3`, state file on `linux`; `sim` emulates identical rules. Post-reboot, all recorded on-times treated as occurring immediately prior to boot, consuming budget for `window_s`; corrupt or missing records treat entire window as spent; still wait `min_interval_ms` before first post-boot turn-on. Dropped "window counters live in memory". *Why:* in-memory counters reset during rapid reboot loops; write-ahead persistence and worst-case assumptions ensure envelopes are not bypassed across reboots.
7. **Safe-direction commands are never blocked and `min_interval_ms` applies only to on commands** (review 2026-10-01, Q-62). `digital.out` `off` and autonomous HAL commands upon expiration of `duration_ms`, `max_continuous_ms`, BLOCK, barge-in, communication loss, `hal.close()` are never blocked, bypass envelopes, require no ALLOW or token, and do not wait for `min_interval_ms` or post-boot delay; `min_interval_ms` applies only to on commands transitioning mechanisms from safe state to active state. *Why:* commands restoring mechanisms to safe state must always execute immediately, never impeded by any control mechanism.
8. **Mandatory auto-off and reservation refunds** (review 2026-10-01, Q-62). Every on command on enveloped pins has a finite duration: HAL and firmware schedule auto-off at `min(command duration, max_continuous_ms)` (durationless `on()` takes `max_continuous_ms`); envelope reserves this duration from `max_on_ms_per_window`, early turn-off refunds unused excess; failed `authorize` refunds 100% of reserved time. *Why:* eliminates permanent uncontrolled turn-on and avoids draining budget when commands are not authorized.
9. **Hardware enforcement and out-of-process supervision** (review 2026-10-01, Q-62). `esp32s3` firmware enforces identical envelope rules from `const` table in flash (RB-4); auto-off timers do not live only in processes that can hang: `esp32s3` uses TWDT + hardware timer (reset boots pulling pin to safe state), `linux` uses dedicated supervisor process holding line and runtime heartbeats; SIGSTOP on runtime process causes actuators to autonomously return to safe state within duration plus margin. *Why:* ensures hardware safety independent of runtime software process hangs or crashes (RB-4).
10. **Binding `digital.in` and `analog.in` facts to gates** (review 2026-10-01, Q-62). `digital.in` enters gates as `bool` facts, `analog.in` as `numeric` criteria ([RFC-0009](0009-tieu-chi-so-numeric.md)), accompanied by read timestamp to compute `age_ms`; `neuroedge build` verifies matching `unit` and channel `[min, max]` fits within criterion `range`; `age_ms < 0` ⇒ BLOCK `criterion_unavailable`. *Why:* standardizes fact interface to walker, catches configuration mismatches early at build, and rejects facts with incorrect timestamps.
11. **`digital.in` age and `min_interval_ms` reference point** (review 2026-10-01, Q-62). `digital.in` read at evaluation instant, fixed age ceiling `DIGITAL_IN_MAX_AGE_MS = 100` ⇒ exceeding ceiling is `criterion_unavailable`. `min_interval_ms` measured from when previous turn-on ended. `enable_pin` in RFC-0010, RFC-0011 exempt from dedicated envelope and uncallable by agents. *Why:* `bool` criteria lack `max_age_ms`, requiring a code ceiling so hung read paths cannot allow; measuring from completion is more conservative than measuring from start.
