# RFC-0011: `motion.*` Primitive — Leased Tokens, Per-Actuator Safe State

| | |
|:---|:---|
| **RFC ID** | 0011 |
| **Title** | `motion.*` (motor/servo), time-limited leased tokens, per-actuator declared safe state, extended envelope |
| **Affected Contract** | `board.v1` *(the `capabilities.motion` block and per-channel `envelope`)* · `TokenLedger`/`ne_token.c` tokens · new check in `neuroedge build` (`p95_latency_ms ≤ lease_ms / 2`, NE3001) · does **not** add fields to `NETR` (`NETR` v2 carried by RFC-0009 / TSK-W1-02) · does **not** touch `gate.v1` or resolution semantics (`gate lint`) |
| **Related PRD Requirements** | FR-HAL-01, FR-HAL-05, FR-PER-02, FR-ACE-08 |
| **Author** | — |
| **Date Opened** | 2026-09-30 |
| **Status** | ✅ Approved (2026-10-01) — lead architect signed on PR #78; amended per review 2026-10-01 (§9, Q-62); implemented in second PR |
| **Approver** | **Lead Architect — mandatory** (touches tokens, physical motion) |

> **When an RFC is required:** `CONTRIBUTING.md` §3 — modifying `schemas/board.v1.json` and C token ledger (`ne_token.c`). `NETR` v2 layout carried by RFC-0009 (TSK-W1-02).
> Tasks: TSK-W1-03 (design, this RFC), TSK-W1-04 (`motion.*` implementation), TSK-I2a-05 (implementation on reference
> boards). Foundation decisions: `neuroedge-prd.md` §15 Q-32 (`motion.*` is dedicated primitive), Q-35 (safe
> state declared per actuator, defaults to stop if undeclared), Q-37 (time-limited leased tokens ~200 ms), Q-38 (mobile
> robots require hardware e-stop button), Q-52, Q-53, Q-55. `analog.in` is **not** part of this RFC (moved to
> [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md) per Q-53).

## 1. Problem

Robots require parameterized motion: speed, angle, duration, ramp. `digital.out` cannot express this (RFC-0010 only adds PWM for simple loads), and the current token model does not fit continuous motion:

- `VerdictToken` (`python/neuroedge/actions/token.py`) carries a **pin set** (`pins: frozenset[str]`), used **once per pin**, lives for `ttl_ms = p95_ms * TTL_FACTOR`, and closes when `c.do()` returns. There are no channels, no amplitudes, no "where does the actuator go when expired".
- A door-latch pulse running to completion is correct (`docs/spec/voice_fsm.md` §5.3); a motor spinning when the user shouts "dừng" (stop) must **not** continue running. Today there is no way to distinguish them (`TODOS.md` #39).
- Crash-safe tests for motion cannot run on QEMU: QEMU does not simulate GPIO (`TODOS.md` #21).

## 2. Why the Current Schema Does Not Solve It

- `schemas/board.v1.json` has no motion primitive, no *safe state* field per actuator (Q-35 requires an RFC for this field).
- `gate.v1` does not accept unknown fields (stated in RFC-0005 §2); placing an "abort even when running" flag per #39 in the gate would modify `gate.v1`.
- A once-per-pin token cannot express *"allow rotation at speed ≤ X on this channel for another 200 ms"*.
- The `NETR` v1 layout (RFC-0003) does not carry gate labels or `on_block` text (`TODOS.md` #36).

## 3. Proposed Change

### 3a. Board Declares Motion Channels

Two separate capability shapes, `motor` and `servo` (§9.4), one record per channel:

```toml
[capabilities.motion]
motor = [
  { name = "wheel_left", speed_max = 0.6, ramp_min_ms = 200, enable_pin = "motor_en",
    safe_state = "stop", lease_ms = 200 },
]
servo = [
  { name = "gripper", target_min = 0, target_max = 90, unit = "deg", enable_pin = "servo_en",
    safe_state = "hold", holds_position = true, max_hold_ms = 2000, lease_ms = 200 },
]

[capabilities.motion.envelope.wheel_left]
window_s = 60
max_on_ms_per_window = 30000
min_interval_ms = 2000
max_continuous_ms = 10000

[capabilities.motion.envelope.gripper]
window_s = 60
max_on_ms_per_window = 10000
min_interval_ms = 1000
max_continuous_ms = 3000
```

- **`safe_state` ∈ {`stop`, `hold`}**, **undeclared ⇒ `stop`** (Q-35, fail-closed). `hold` is valid only when the channel declares `holds_position = true` along with `max_hold_ms`; when `max_hold_ms` expires, it transitions to `stop`. There is no `home` or any state that moves autonomously (§9.3). Within that set, the safe state is decided per actuator (Q-35).
- **`lease_ms`** defaults to 200, ceiling 500; schema rejects values ≤ 0 or > 500 (§9.2).
- **`enable_pin`** mandatory, following the PWM rule ([RFC-0010](0010-pwm-trong-digital-out.md) §9.2): a `digital.out` line with an on-board pull-down resistor, so if the process dies the driver is disabled (§9.5).
- **Channel envelope:** Declared at `[capabilities.motion.envelope.<channel>]` with the common keys from [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md) §9.5 (`window_s`, `max_on_ms_per_window`, `min_interval_ms`, `max_continuous_ms`). All `motion.*` channels are always actuators, cannot be declared in `signal_pins`. Missing envelope ⇒ `BoardCapabilityError` (NE3001) at load time. The channel's `enable_pin` is managed internally by HAL: agents cannot call it (direct `digital.out` commands to it are rejected), exempt from its own RFC-0007 envelope, and not declared in `signal_pins`.

### 3b. API and Envelope

Split in two (§9.4): `motion.motor(channel, speed, direction, ramp_ms)` and `motion.servo(channel, target, speed_max)`. Calling `motion.servo` on a `motor` channel (and vice versa) is rejected as an unknown channel. Both traverse the same HAL path: `require_channel → check board limits → envelope → authorize → record`.

Enforcement rules for envelopes and `motion.*` runs:

- **Run definition:** A `motion.*` run is a continuous sequence of leases on the same channel, where each new lease is granted before the previous lease expires. Each lease is used for exactly one command; the next command is a new invocation through the gate. Repeating commands within the same lease is forbidden.
- **HAL ordering and `min_interval_ms`:** `min_interval_ms` applies only to turn-on commands, i.e., at the start of a run transitioning the actuator from safe state to operating state, measured from when the previous run ended. Lease renewals within the same run are not blocked by `min_interval_ms`.
- **Continuous run duration:** `max_continuous_ms` applies to the entire run, measured from the start of the run.
- **Mandatory auto-off and budget pre-reservation:** All turn-on commands have finite duration. At the start of a run, the envelope pre-reserves `max_continuous_ms` out of `max_on_ms_per_window`. When the run ends, HAL refunds the unused portion. If `authorize` fails after pre-reservation, the entire reserved portion is refunded: no token spent, no pulse sent.
- **Envelope survives restarts (write-ahead):** Total reserved on-time in the window is persisted before turning on: NVS on `esp32s3`, state file on `linux`; `sim` simulates identical rules. For `motion.*`, written once per run (at start), not on every renewal to prevent flash wear. After reboot, all recorded turn-ons are treated as occurring immediately pre-boot, occupying budget until `window_s` after boot. Unreadable, corrupt, or missing records ⇒ entire window treated as exhausted. The rule requiring `min_interval_ms` wait before the first turn-on after reboot is retained.

Limits in two places, **both enforced simultaneously, tighter limit wins** (§9.5):

- **Board:** channel hardware limits (declared in `board.v1`) generate firmware tables, checked at boot; failed self-test ⇒ reject all `motion.*` commands except `safe_state`.
- **Gate:** parameter constraints (speed, target) are gate `arguments` per RFC-0005, residing in `NETR`; the C walker already reads them.

### 3c. Time-Limited Leased Tokens (Q-37)

A **lease** carries: channel, maximum amplitude (speed, angle), channel expiry `lease_ms` (default 200, ceiling 500 declared on board). `gate.v1` does **not** carry `lease_ms`, so the gate has no way to raise or lower the lease beyond the board value (§9.2). Each lease serves exactly one command. Renewal occurs **only** through a new call through the gate with full re-evaluation; strictly checks amplitude; no further commands ⇒ lease expires ⇒ actuator returns to `safe_state`. A BLOCK verdict does not renew the lease. The lease is decoupled from `TTL_FACTOR` of verdict tokens (§9.2).

The gate's `budget.p95_latency_ms` must be ≤ `lease_ms / 2`, otherwise **`neuroedge build`** rejects (`BoardCapabilityError`, NE3001). Only at build time are both the gate and the board's `lease_ms` available; `gate lint` and resolution semantics remain unchanged (§9.2).

Timeout mechanism and independent supervisor outside process: The auto-off timer and lease must not live solely in the runtime process because the process can hang.
- On `esp32s3`: Task Watchdog (TWDT) plus hardware timer; watchdog reset reboots with `enable_pin` pulled down.
- On `linux`: `enable_pin` (and actuator pin line) held by a separate supervisor process; runtime sends heartbeats; missing heartbeats beyond the deadline ⇒ supervisor releases `enable_pin` and disables channel.

Changes: `VerdictToken`, `TokenLedger.issue/authorize` (host) and `ne_token.c`/`ne_token.h` (device) change together; expired leases or wrong channels cannot be reused. Gates remain pure.

### 3d. Barge-In — Closing `TODOS.md` #39 for Motion

For `motion.*`: barge-in, BLOCK, or loss of communication ⇒ **immediately send `safe_state` command** and stop renewing lease; there is no flag allowing motion to "run to completion once delivered" (§9.1). The immediate stop command is the primary layer; lease expiration is the fallback layer (communication loss where neither side can send commands still leads to `safe_state`, similar to ROS `cmd_vel` timeout). **No flag is added to `gate.v1`.** `digital.out` pulses (door latch) retain the "run to completion" rule of `docs/spec/voice_fsm.md` §5.3; if future `digital.out` actuators require "abort even when running", #39 remains deferred for that part.

**Safe-direction commands are never blocked:** Includes `motion.*` sending `safe_state` (`stop`/`hold`) and all HAL autonomous commands upon expiry of `duration_ms`, expiry of `max_continuous_ms`, expiry of lease, on barge-in, BLOCK, connection loss, `hal.close()`. These commands bypass the envelope, require no ALLOW or token, and do not wait for `ramp_min_ms`, `min_interval_ms`, or post-boot cooldown. This is the **sole exception** to the "no command reaches hardware without ALLOW" rule. It applies only to commands transitioning actuators to the declared board safe state. Commands are still recorded in traces with their cause. This exception must be recorded in `docs/spec/threat_model.md` §1 upon implementation (recorded in §8).

### 3e. `NETR` (`TODOS.md` #36)

`motion.*` itself **adds no fields to `NETR`**. Speed/target limits use the RFC-0005 parameter table. The hardware limit table in §3b is a firmware table generated from `board.v1`, **not** part of `NETR`. Bumping `layout_version` = 2 belongs to [RFC-0009](0009-tieu-chi-so-numeric.md) (TSK-W1-02), carrying the `numeric` table, gate labels, and `on_block` text (#36). This RFC only modifies the token ledger `ne_token.c` and host `TokenLedger` to manage leases.

### 3f. Testing on Physical Boards and Mechanical Safety

Boards carrying `motion` (§9.6): `linux-rpi5` (hardware PWM + driver with `enable_pin`) and `esp32s3-box-3` (LEDC via dock pins, verified in TSK-I3a-01; if dock lacks sufficient pins then `esp32s3-cores3` (M5Stack CoreS3, Q-61) via Grove/M5-Bus port). If CoreS3 carries it, only `sim-rpi5` mirrors `motion`, `sim-default` does not mirror `motion` because `sim-default` mirrors Box-3 ("sim is no richer than board" invariant).

Crash-safe and hung-process tests: Crash-safe tests (process SIGKILL/crash, network pull, watchdog reset, mid-command power loss) and **hung process tests (SIGSTOP)** **run on both physical boards** (TSK-W1-04, TSK-I2a-05), not QEMU/Wokwi (#21). Acceptance criterion: hung process (SIGSTOP) during turn-on ⇒ actuator transitions to safety within declared duration plus margin. Mobile robots require a hardware e-stop button cutting motor power independently of software (Q-38).

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | Yes — the `motion` block is optional. Within the block, `enable_pin` and envelope at `[capabilities.motion.envelope.<channel>]` are mandatory; `safe_state` accepts only `stop`/`hold` (§3a). `motion` channels cannot declare `signal_pins`. Three tier-1 profiles in `boards/` must add envelopes in implementation PR, with values wide enough for canonical traces to replay unchanged (e.g. `door_lock` receives 30,000 ms pulse ⇒ `max_continuous_ms` ≥ 30000); no external profiles exist |
| Do currently invalid files become valid? | Yes — profiles declaring `motion` with correct shape and channel envelopes (same tightening point for previously meaningless `capabilities` keys as RFC-0007 §4) |
| Does schema version need bumping (`v1` → `v2`)? | Not for `board.v1`. **Not** for `NETR` in this RFC: `layout_version = 2` is carried by RFC-0009 (TSK-W1-02); this RFC adds no fields to `NETR` |
| Impact on published gate hashes / signatures? | None — `gate.v1`, `gate lint`, and resolution semantics unchanged. Checking `p95_latency_ms ≤ lease_ms / 2` is a new check in `neuroedge build` on gate + board pairs; touches only agents using `motion.*`, none exist yet |
| Impact on three canonical trace files? | None; new `motion.*` events (including `safe_state` commands) sit alongside `actuator_command`/`actuator_aborted` (`docs/spec/simulation_coverage.md` §3) |
| Which gates in `digests.lock` change digest? | None |
| Must `NETR` layout or C walker change? | **No** change to `NETR` layout or C walker in this RFC. Only changes token ledger `TokenLedger` (host) and `ne_token.c` (device) to manage leases. Firmware adds channel limit table generated from `board.v1` and boot-time self-test (§3b) |
| Do any answers in tool call corpus (`expected_results.yaml`) change? | Existing answers unchanged; new `motion.motor`/`motion.servo` cases added. `digital.out` tokens keep one-time semantics |
| Error code catalog (`neuroedge-prd.md` Appendix B) | No new classes or codes added. `BoardCapabilityError` (NE3001) row broadens reasons: gate has `p95_latency_ms > lease_ms / 2` for a motion channel used by agent, or board declares `motion` channel without envelope block `[capabilities.motion.envelope.<channel>]` |

## 5. Safety Impact

- **Gates no looser:** `gate.v1`, resolution semantics, and five inheritance principles unchanged. All motion commands still go through gates; leases only **shorten** the validity window of a verdict, and each renewal requires full re-evaluation. Each lease serves exactly one command.
- **Deeper fail-closed:** undeclared `safe_state` ⇒ `stop`; barge-in, BLOCK, loss of connection, lease expiry, expiry of `max_continuous_ms` ⇒ immediately send `safe_state`; `hold` past `max_hold_ms` ⇒ `stop`; no safe state moves autonomously; unknown channel, wrong channel type, amplitude exceeding lease, expired lease ⇒ rejected, cannot be reused; failed boot-time limit self-test ⇒ reject all `motion.*` commands except `safe_state`. `safe_state` command is the sole exception never blocked, ensuring actuators always reach safety on fault.
- **Runtime fail-safe layer when `p95_latency_ms` is vacuous:** `budget.p95_latency_ms` is declared by gate authors, so build-time checks could be vacuous if declared optimistically. Enforcing lease expiration in HAL/runtime during actual execution remains the core fail-safe defense, independent of gate declarations.
- **Two independent limiting layers:** permissive gates cannot exceed hardware limit tables, misconfigured boards cannot exceed gates; tighter limit wins.
- **Leases do not replace crash-safety:** when a process is killed with SIGKILL or hung (SIGSTOP), runtime software cannot autonomously send `safe_state`. On `esp32s3`, Task Watchdog (TWDT) plus hardware timer guarantees reset and boot with `enable_pin` pulled down. On `linux`, independent supervisor process holds `enable_pin` via heartbeats; lost heartbeats due to crash or SIGSTOP automatically release `enable_pin` and disable channel. Crash-safe and hung-process tests on physical boards are acceptance criteria. Consequence: on crash/hang, `enable_pin` disables driver regardless of whether `safe_state` declares `hold`.
- **Envelope survives reboot (write-ahead):** Total on-time is persisted to NVS/state file once per run; after reboot, recorded budget occupies `window_s` window, preventing limit bypass via device reboots.
- **NeuroEdge is not a certified safety function** (Q-38): This RFC makes no SIL/PL claims. Mobile robots require hardware e-stop buttons outside software scope.
- **Token change risk:** `ne_token.c` is device code; changing one-time semantics to leased tokens can introduce replay paths. Mandatory fuzzing and mutation testing per RFC-0003 §7.
- **Gates at 10–20 times/second** for mobile robots (Q-34): renewals must arrive before lease expires, so `neuroedge build` requires `p95_latency_ms ≤ lease_ms / 2` (§3c).

## 6. Alternatives Considered and Rejected

| Alternative | Reason for Rejection |
|:---|:---|
| Stuffing motors into `digital.out` | Q-32: clearer contract with dedicated primitive; `digital.out` lacks channels/ramps/leases |
| Unified `motion.drive(...)` API for motors and servos | Limits of the two types are fundamentally different; combining them weakens constraints (§9.4) |
| Longer one-time token (large TTL), or lease derived from `TTL_FACTOR` | Actuator runs until TTL expires after communication loss; exactly what Q-37 avoids. Leases have dedicated default and ceiling (§9.2) |
| Barge-in only ceases renewals, waiting for lease to expire | Motor still spins for up to `lease_ms` after user objects; immediate `safe_state` command is primary layer (§9.1) |
| "Abort even when running" flag in `gate.v1` (#39) | Modifies `gate.v1`, entailing inheritance semantics; immediate `safe_state` plus lease achieves this for motion without altering gates |
| Extended `safe_state` (`release`, `finish_pulse`, `home`…) | Without supervision, no actuator may move autonomously; only `stop`/`hold` (§9.3). Running pulses to completion is `digital.out` rule, not `motion.*` |
| Allowing gate to adjust `lease_ms` (raise or lower) | Modifies `gate.v1`; current gates carry no lease field. Leases are decided entirely by board (§9.2) |
| Checking `p95_latency_ms ≤ lease_ms / 2` in `gate lint` | Gates do not carry `lease_ms`; adding field modifies `gate.v1`. Only `build` has both (§9.2) |
| Gate tracking cumulative runtime | Violates purity (invariant #4) |
| Separate `NETR` v2 bump for each RFC | Frequent version bumps; firmware must track every revision (§3e) |

## 7. Verification Evidence

- [ ] `boards/` profiles declaring `motion` on `linux-rpi5`, `esp32s3-box-3` (or `esp32s3-cores3` via Grove/M5-Bus port if Box-3 dock lacks pins, §9.6); when CoreS3 carries it, only `sim-rpi5` mirrors `motion`, `sim-default` does not mirror `motion` ("sim is no richer than board" invariant). Negative tests: `motion` channel missing envelope `[capabilities.motion.envelope.<channel>]` ⇒ `BoardCapabilityError` (NE3001) at load time; `motion` channel declaring `signal_pins` rejected; `safe_state` outside {`stop`, `hold`} (`home`, `release`); `hold` missing `holds_position = true` or `max_hold_ms`; missing `enable_pin`; `lease_ms` ≤ 0 or > 500; servo keys on `motor` record and vice versa; `speed_max` outside (0, 1]. Three tier-1 profiles add envelopes wide enough for canonical traces to replay identically
- [x] Host tests — safe-direction commands never blocked: `safe_state` (`stop`/`hold`) command sent on barge-in, BLOCK, connection loss, lease expiry, `max_continuous_ms` expiry, or `hal.close()` requires no token/ALLOW, bypasses envelope, does not wait for `ramp_min_ms` or `min_interval_ms`, does not wait after reboot; trace fully recorded with cause — *met (TSK-I2a-05): `test_stop_needs_no_token_no_envelope_and_does_not_wait_for_a_ramp`, `test_close_stops_every_channel_whatever_it_declares_and_records_why`, `test_a_blocked_call_does_not_renew_it_and_sends_the_channel_safe`, `test_a_late_tick_still_stops_the_model_at_the_leases_end`, `test_an_unreadable_record_refuses_a_run_but_never_the_stop` (`tests/test_motion.py`)*
- [x] Host tests — lease sequence and run through envelope: continuous lease renewals every ~100 ms on same channel not blocked by `min_interval_ms` (even if `min_interval_ms = 2000`); `min_interval_ms` checked only at start of new run; `max_continuous_ms` applies to entire run, expiry of `max_continuous_ms` ⇒ HAL automatically issues `safe_state` command — *met: `test_renewals_every_100ms_are_not_held_up_by_min_interval_ms`, `test_min_interval_ms_is_checked_only_when_a_run_starts`, `test_max_continuous_ms_covers_the_whole_run_and_the_hal_sends_safe_at_its_end` (`tests/test_motion.py`); on `linux` `test_the_envelope_gates_a_run_on_linux_too` (`tests/test_motion_linux.py`)*
- [x] Host tests — one command per lease: each lease used for exactly one command; sending second command or repeating command on same lease rejected by HAL — *met: `test_a_lease_carries_exactly_one_command` (`tests/test_motion.py`)*
- [x] Host tests — pre-reservation and budget refund: start of run pre-reserves `max_continuous_ms` in `max_on_ms_per_window`; early end of run ⇒ HAL refunds remaining time to window budget; if `authorize` fails after reservation ⇒ refunds entire reserved portion, no token spent, no pulse sent — *met: `test_a_run_reserves_max_continuous_ms_and_gives_back_the_unused_part`, `test_an_over_budget_run_is_refused_and_nothing_moves`, `test_a_proof_the_hal_refuses_gives_the_whole_reservation_back` (`tests/test_motion.py`)*
- [ ] Host tests — envelope survives reboot: total on-time persisted (write-ahead) to NVS (`esp32s3`) or state file (`linux`) once per run (not on every renewal); after reboot, recorded budget occupies `window_s` window; corrupt or missing records ⇒ entire window treated as exhausted; mandatory `min_interval_ms` wait before first turn-on after reboot — *state file portion (`linux`) met: `test_a_run_writes_its_on_time_once_at_its_start_and_not_for_every_renewal`, `test_after_a_restart_the_recorded_run_holds_budget_and_the_channel_waits`, `test_an_unreadable_record_refuses_a_run_but_never_the_stop`; `esp32s3` NVS under firmware (TSK-W1-04), pending*
- [x] Host tests — leases (§9.2): missing `lease_ms` ⇒ 200; expired lease ⇒ `safe_state` and replayable event; wrong-channel/expired lease rejected; no renewal path other than new call through gate (BLOCK calls do not renew); changing `TTL_FACTOR` does not alter lease — *met: `test_a_missing_lease_ms_is_200`, `test_a_channel_nobody_commands_goes_to_its_safe_state_when_the_lease_ends`, `test_a_session_with_leases_replays_the_same_decisions`, `test_a_lease_that_ran_out_before_the_command_is_refused`, `test_a_lease_for_one_channel_is_no_proof_for_another`, `test_a_blocked_call_does_not_renew_it_and_sends_the_channel_safe`, `test_the_lease_is_the_boards_and_not_the_gates_or_the_ttl`*
- [x] Host tests — barge-in (§9.1): barge-in, BLOCK, connection loss ⇒ `safe_state` command recorded at same virtual clock tick as triggering event, **before** lease expires, no further renewals; already-delivered `digital.out` pulses still run to completion (`voice_fsm.md` §5.3) — *met: `test_a_barge_in_sends_safe_in_the_same_tick_and_before_the_lease_ends`, `test_a_barge_in_does_not_cut_a_delivered_digital_pulse`, `test_the_voice_session_wires_barge_in_to_motion`*
- [x] Host tests — `safe_state` (§9.3): undeclared ⇒ `stop`; `hold` past `max_hold_ms` ⇒ `stop` — *met: `test_a_missing_lease_ms_is_200` (undeclared ⇒ `stop`), `test_a_servo_that_declares_hold_holds_when_its_lease_ends_then_stops_after_max_hold_ms`, `test_a_hold_never_outlives_the_runs_max_continuous_ms`*
- [x] Host tests — API (§9.4): `motion.motor` on `servo` channel and vice versa rejected; new cases in `fixtures/tool_calls/`, bidirectional closure in `expected_results.yaml` — *met: `test_a_command_of_the_wrong_kind_is_refused_like_an_unknown_channel`; cases `fixtures/tool_calls/{valid,invalid}/motion_*.yaml` bidirectional closure (`tests/test_tool_corpus.py`)*
- [ ] Limit tests (§9.5): gate looser than board ⇒ board limits win; board looser than gate ⇒ gate wins; boot-time self-test failure ⇒ all `motion.*` commands except `safe_state` rejected — *host portion met: `test_a_gate_looser_than_the_board_leaves_the_board_in_force`, `test_the_gate_narrows_the_board_and_the_tighter_limit_wins`, `test_the_board_limits_a_motor_command`; firmware boot-time limit self-test pending (TSK-W1-04)*
- [x] `neuroedge build` tests (§9.2): gate with `p95_latency_ms > lease_ms / 2` ⇒ `BoardCapabilityError` (NE3001), no firmware generated; at exact threshold passes. `neuroedge gate lint` unchanged on same gate — *met: `test_a_gate_slower_than_half_the_lease_is_refused_at_build_and_the_boundary_passes`, `test_the_lease_check_is_the_builds_and_gate_lint_does_not_change`, `test_a_failed_lease_check_writes_no_firmware_or_artifact`*
- [ ] C walker/`ne_token.c` matches host `TokenLedger` (extend `python/tests/test_c_token.py`), ASan/UBSan fuzzing; verify `NETR` has no new fields from RFC-0011 — *pending: firmware outside TSK-I2a-05 scope (TSK-W1-04); host `TokenLedger` already supports leases*
- [ ] **Crash-safe and hung-process tests on both physical boards** (§9.6): kill -9 process (SIGKILL), pull WiFi, mid-command power loss, and hung process (SIGSTOP) ⇒ on `linux` independent supervisor process releases `enable_pin` and disables channel; on `esp32s3` TWDT/hardware timer resets and boots with `enable_pin` pulled down; actuator reaches `safe_state` within declared duration plus margin; measurement results attached to PR — *CI portion met: runtime SIGSTOP and SIGKILL bring enable line down within heartbeat + margin (`tests/test_motion_linux.py`, `tests_linux/test_gpio_motion.py` on gpio-sim, green in CI run 37153005998); physical motor/servo/driver and `esp32s3` pending — stage B*
- [x] `sim` models leases via virtual clock, no richer than reference boards; `neuroedge verify` and `neuroedge gate lint` green — *`SimActuator` + `MotionController` on virtual clock, `test_a_session_with_leases_replays_the_same_decisions`; `neuroedge verify` and `gate lint` green*

## 8. Post-Approval Tasks

- [x] Update `schemas/board.v1.json` (`motion.motor`, `motion.servo`, `safe_state`, `lease_ms`, `enable_pin`, `holds_position`, `max_hold_ms`, and mandatory envelope `[capabilities.motion.envelope.<channel>]`, reject `signal_pins` on `motion` channels); three tier-1 profiles in `boards/` add envelopes wide enough for canonical traces to replay identically — *met: `motion.motor`/`servo`, `safe_state`, `lease_ms`, `enable_pin`, `holds_position`, `max_hold_ms`, mandatory envelopes, rejects `signal_pins` — `tests/test_board_fixtures.py`; three tier-1 profiles have envelopes*
- [ ] Pin `NETR` v2 layout in RFC-0009 (TSK-W1-02, closing #36); RFC-0011 adds no fields to `NETR`. Close #39 for `motion.*`, retain deferred status for `digital.out`
- [x] Record sole exception to "no command reaches hardware without ALLOW" rule in `docs/spec/threat_model.md` §1 for commands transitioning actuators to `safe_state` — *met: `docs/spec/threat_model.md` §1 ("Motion with leases" section)*
- [x] Amend `docs/spec/voice_fsm.md` §5: §5.3 includes exception for `motion.*` (barge-in ⇒ immediately send `safe_state`); stop due to communication loss is shutdown-style stop — TSK-W1-04 — *met: §5.2 step 1 and §5.5 (TSK-I2a-05)*
- [ ] `neuroedge-prd.md` FR-HAL-01 and `BoardCapabilityError` (NE3001) row in Appendix B (§4); assign `Q-N` to new decisions; `neuroedge-roadmap.md` (TSK-W1-03, TSK-W1-04, TSK-I2a-05, TSK-I3a-01 verify `esp32s3-box-3` dock / `esp32s3-cores3`) — *NE3001 and NE1002 rows in Appendix B updated (TSK-I2a-05)*
- [ ] `python/neuroedge/actions/token.py`, `python/neuroedge/hal/` (run definition, `min_interval_ms` checks, pre-reservation/refund, NVS/file persistence, independent supervisor process on `linux`), `p95_latency_ms ≤ lease_ms / 2` check in `neuroedge build`, update token ledger in `ne_token.c`, `esp32s3` firmware (TWDT + hardware timer, NVS write-ahead), firmware limit table and boot-time self-test — *host met (TSK-I2a-05): leases in `actions/token.py`, `hal/motion_core.py` (runs, pre-reserve/refund, safe state), `hal/motion_pwm.py` (`linux`), `p95 ≤ lease_ms / 2` check in `neuroedge build`; `ne_token.c`, firmware, NVS, limit table and boot self-test pending (TSK-W1-04)*
- [ ] Fixtures/tests (including hung process SIGSTOP test on both physical boards); update `docs/rfc/README.md` and `CHANGELOG.md` — *fixture `fixtures/agents/rover` + corpus cases + `tests/test_motion*.py` + `tests_linux/test_gpio_motion.py` (green in CI run 37153005998); SIGSTOP on physical boards pending*

## 9. Decisions on Open Questions (Q-57, 2026-09-30; Q-62, 2026-10-01)

Product owner delegated decision on open questions under the **maximum safety** principle: between two alternatives, choose the one that is fail-closed and harder to misuse, even if it requires more effort. The decisions below have been **incorporated** into §3–§8; this section is preserved as a decision log (Q-57). RFC approval still requires lead architect signature (`CONTRIBUTING.md` §3).

1. **Barge-in (`TODOS.md` #39).** For `motion.*`: barge-in, BLOCK, or loss of communication ⇒ **immediately send `safe_state` command** and stop renewing lease; there is no flag allowing motion to "run to completion once delivered". `digital.out` pulses retain current rules (`docs/spec/voice_fsm.md` §5.3). *Why:* a motor spinning when the user objects is dangerous; the lease is a fallback layer, the immediate stop command is the primary layer. Closes #39 for motion.
2. **Leases.** `lease_ms` defaults to 200, ceiling 500 (decided entirely by the board in `board.v1`; gates do not carry `lease_ms`, so there is no way to raise or lower it). Renewal occurs only via a new call through the gate with full re-evaluation. Gate's `budget.p95_latency_ms` must be ≤ `lease_ms / 2`, otherwise `neuroedge build` rejects (`BoardCapabilityError`, NE3001): only at build time are both the gate and the board's `lease_ms` available — gates carry no `lease_ms` so `gate lint` cannot check it. Leases are decoupled from `TTL_FACTOR` of verdict tokens. *Why:* renewals must arrive before the lease expires, and each renewal gives the gate another opportunity to decide.
3. **`safe_state` ∈ {`stop`, `hold`}**, default `stop`. `hold` can only be declared when the board declares `holds_position = true` along with `max_hold_ms`; when `max_hold_ms` expires, it transitions to `stop`. There is no `home` or any state that moves autonomously. *Why:* without supervision, no actuator may move autonomously.
4. **Split API:** `motion.motor` (speed, direction, ramp) and `motion.servo` (target angle, maximum speed), two distinct capability shapes. *Why:* limits of the two types are fundamentally different; combining them weakens constraints.
5. **Location of limits.** Hardware channel limits (declared in `board.v1`) generate firmware tables, checked at boot (failed self-test ⇒ reject all `motion.*` commands except `safe_state`); gate constraints reside in `NETR`. Both enforce simultaneously, tighter limit wins. Motion channels also require `enable_pin` like PWM (RFC-0010 §9). *Why:* loose gates cannot override hardware, misconfigured hardware cannot override gates.
6. **Boards carrying `motion`:** `linux-rpi5` (hardware PWM + driver with `enable_pin`) and `esp32s3-box-3` (LEDC via dock pins, verified in TSK-I3a-01; if dock lacks sufficient pins then `esp32s3-cores3` (M5Stack CoreS3, Q-61) via Grove/M5-Bus port). If CoreS3 carries it, only `sim-rpi5` mirrors `motion` (not `sim-default`, because `sim-default` mirrors Box-3 — "sim is no richer than board" invariant). Mid-command power loss and hung process tests run on both physical boards (TSK-W1-04).
7. **Safe-direction commands are the sole exception** (review 2026-10-01, Q-62). `safe_state` (`stop`/`hold`) command and all HAL autonomous commands upon expiry, barge-in, BLOCK, loss of connection, or `hal.close()` are never blocked: bypass envelopes, require no token/ALLOW, do not wait for `ramp_min_ms`, `min_interval_ms`, or post-boot cooldown; this is the sole exception to the rule prohibiting commands reaching hardware without ALLOW. *Why:* human and mechanical safety is paramount; no secondary safety mechanism may block a command bringing an actuator to safety.
8. **Run definition and lease renewal through envelopes** (review 2026-10-01, Q-62). A `motion.*` run is a continuous sequence of leases on the same channel; `min_interval_ms` applies only at the start of a run; `max_continuous_ms` applies to the entire run; each lease serves exactly one command. *Why:* eliminates renewal rejection when `min_interval_ms` exceeds lease duration (~100 ms), while preventing command repetition or queuing within a single lease.
9. **Mandatory auto-off and envelope budget pre-reservation** (review 2026-10-01, Q-62). All turn-on commands have finite duration; at start of run, envelope pre-reserves `max_continuous_ms` out of `max_on_ms_per_window`, refunding remaining portion when run ends; failed `authorize` after reservation refunds entire held portion. *Why:* ensures actuators always shut off on lost control and preserves runtime limits when commands fail.
10. **Envelope survives reboot** (review 2026-10-01, Q-62). Total held on-time is persisted before turning on (write-ahead to NVS on `esp32s3`, state file on `linux`); for `motion.*`, written once per run (not on every renewal to prevent flash wear); post-boot treats it as having occurred immediately pre-boot, occupying budget until `window_s`. *Why:* prevents rebooting to clear envelope limits while protecting flash endurance.
11. **Mandatory envelope for motion channels** (review 2026-10-01, Q-62). All `motion.*` channels are always actuators, must declare envelope at `[capabilities.motion.envelope.<channel>]`, cannot declare `signal_pins`; missing envelope rejected at board load time. *Why:* physical motion always carries load and collision risks, requiring envelopes to bound active duration and duty cycles.
12. **Independent supervisor outside process** (review 2026-10-01, Q-62). Lease and auto-off timers do not live solely in runtime process: `esp32s3` uses TWDT plus hardware timer; `linux` uses independent supervisor process holding `enable_pin` via heartbeats; if runtime process hangs (SIGSTOP), actuator still reaches safety within declared duration plus margin. *Why:* runtime process can hang or contend; safety shutdown must rely on hardware or independent processes.
13. **No change to `NETR` layout in this RFC** (review 2026-10-01, Q-62). This RFC adds no fields to `NETR`; `layout_version = 2` is carried by RFC-0009 (TSK-W1-02); this RFC only updates token ledger `ne_token.c`/`TokenLedger` to manage leases. *Why:* consolidates `NETR` version bump in one place, avoiding binary format fragmentation and keeping the C walker pure.
14. **`safe_state` on self-test failure, `enable_pin`, `min_interval_ms` baseline** (review 2026-10-01, Q-62). Boot-time limit self-test failure ⇒ reject all `motion.*` commands **except** `safe_state`. `enable_pin` cannot be called from agent, exempt from dedicated envelope. `min_interval_ms` measured from when previous run ended. *Why:* no error state may block a stop command; end timestamp is the conservative baseline.
