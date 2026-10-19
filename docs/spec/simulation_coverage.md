# Simulation Coverage — 5 Primitives × 3 Tier-1 Targets

**Status:** normative specification, accompanying Q-21 and Q-22 (*decided*) — PRD §15. This document specifies **what**
runs and tests each cell; which cells are completed is tracked in the status of the corresponding task in `neuroedge-roadmap.md`.
Tools and licenses: roadmap §3. Layered strategy: `docs/architecture/vi/00-overview.md` §5.2.

This document answers one question: **for each HAL primitive on each target, what runs it,
what tests it, and what cannot yet be tested.** Each cell in the table in §2 has a responsible task;
any cell without a task is a gap.

## 1. What "Complete Coverage" Means

No simulator can emulate room acoustics, I2S timing, or ESP32-S3 memory pressure. Therefore,
"complete" does not mean everything runs without hardware. A cell is considered **covered** when
all four conditions are met:

1. **Working backend** on that target, conforming to the HAL contract (FR-TGT-01/02/03).
2. **Standard trace events** for every call (§3), so sessions can be recorded (`record`) and replayed (`replay`).
3. **Automated testing** at least at one layer: per-PR (no hardware required), nightly QEMU, or
   nightly real board (TSK-S4-05).
4. **Explicit boundaries**: what that layer cannot test is listed in the "Hardware Only" column and has an
   on-board test.

## 2. Coverage Matrix

"PR" = runs on the GitHub runner on every PR, requiring no hardware. Status (done / partial / not started)
is not recorded here: see the task in the last column in the roadmap task table (`CONTRIBUTING.md` §8.1).

### `sim` — `sim-default` (mirror ESP32-S3-BOX-3, invariant 7)

| Primitive | Backend | Tested In | Task |
|:---|:---|:---|:---|
| `digital.out` | `SimHAL`, single-use token; in-memory per-pin envelope, session clock, pin auto-returns to off at deadline (virtual: `sim` has no timers) — same numbers as the board it mirrors (invariant 7) | PR | TSK-S2-01, S2-05, N2-01, N2-02 |
| `digital.out` — PWM *(only boards declaring `digital_out.pwm`, e.g. `sim-rpi5`)* | `pwm` operations (`frequency_hz`, `duty`, `duration_ms` — all three required) and `off`; `on`/`pulse` on PWM channels are rejected. Same board limits, envelope, and `duty` quantised to 0 as `linux`; `enable_pin` belongs to HAL (`pwm_enabled()`); `state()` returns `commanded`, or `measured` from `SimHAL.set_feedback()` when board declares `feedback.pins` (REPL `:feedback`) | PR (`tests/test_pwm.py`) | TSK-W1-01 |
| `audio.in` | Text typing → command grammar (Q-15) · 16-bit mono PCM WAV file matching the board's exact `sample_rate_hz` (`--voice-file`; board does not resample, so `sim` does not either) → 20 ms frames → energy VAD → STT provider `[stt]` (`hal/audio.py`, `perception/voice_session.py`) | PR (typing, test-generated WAV files, mock provider) | WAV: TSK-S3-13 |
| `audio.out` | Text to speak (`tts_stream_start`): knowledge base answer (RAG via System 2, local when offline), ask prompt of `on_block: ask` · TTS provider audio `[tts]` resampled to the board's `sample_rate_hz`, placed on the virtual timeline, truncated on barge-in, written to WAV (`--voice-out`) | PR (mock provider) | text: TSK-S2-11 · WAV: TSK-S3-13 |
| `sensor.read` | Scripted values: `[sim.sensors]` in `agent.toml`, `:sensor` in REPL and UI; sensor gate facts: `[sim.sensor_facts]`; `sensor.read()` in `@action` | PR | TSK-S3-23 |
| `display` | In-memory text frame or RGB565/RGB888 pixel buffer, resolution checked; SHA-256 digest; `display.show()` in `@action` | PR | TSK-S3-23 |
| `i2c` *(only boards declaring `i2c`, e.g. `sim-rpi5`)* | Scripted values `SimHAL.set_i2c()` / sequence `script_i2c()` (replay), through the exact allow-list of `linux`; no bus scan, no fabricated readings — unset value ⇒ `PerceptionUnavailableError` (NE5001); `i2c.read()` in `@action` | PR | TSK-I2a-03 |
| *Visual* | Terminal · static HTML `trace view` · local web `run --ui` and `mcp serve --ui` (FR-TGT-06) | PR | TSK-S3-22, S2-09, S3-27 |

**Sensor gate facts — `[sim.sensor_facts]`.** Each line `criterion = { sensor = "…", <rule> }`
computes a gate fact from a reading, identically on `sim` (scripted value) and `linux` (kernel reading).
Each sensor is read **once per gate fact computation** (`gate_facts`: tool calls of a single command
turn, a confirmation answer, a tool call via MCP), so two facts for the same sensor are never
computed on two different readings. Implementation: `SensorFact` and `SimSession.gate_facts` in
`python/neuroedge/sim/session.py`.

| Rule | Fact | Example |
|:---|:---|:---|
| *(none)* | The raw reading itself | `door_closed = { sensor = "door_contact" }` |
| `equals` | `bool`: reading equals value — value is bool, string, or finite number | `room_empty = { sensor = "motion", equals = false }` |
| `gte` / `lte` (one or both) | `bool`: reading ≥ / ≤ threshold — **threshold included** | `too_hot = { sensor = "temperature", gte = 30 }` |
| `bands` | `level`: band containing the reading | `heat_level = { sensor = "temperature", bands = { low = -40, normal = 25, high = 40, critical = 55 } }` |

Checked on session load — error ⇒ tripartite error (`AgentManifestError`, sensor not declared on board ⇒
`BoardCapabilityError`), **before** requesting any GPIO line:

- Exactly **one** rule per line: `bands`, `equals`, `gte`/`lte` cannot be mixed. Thresholds must be finite numbers (not
  bool, NaN, inf). The sensor must be declared by the board.
- Numeric rules (`gte`, `lte`, `bands`) require a unit declared in `[sim.sensors]`
  (`temperature = { value = 45, unit = "C" }`), so `linux` rejects readings with mismatched units instead of comparing them
  against thresholds (`linux` rule below).
- `bands`: each entry is `level = lower_threshold`, with thresholds **strictly increasing** in written order. A band starts
  **at** its threshold and stops immediately below the next entry's threshold; the final band has no upper bound. In the example
  above: 24.999 → `low`, 25 → `normal`, 54.999 → `high`, 55 → `critical`. At least one gate
  must read that criterion; every gate reading it must declare type `level`, and for each gate: levels must match those declared in
  the gate's `evaluate.<criterion>.levels`, written in **that exact order**, and the **final entry must be the gate's highest level** —
  lower or intermediate levels may be omitted, ensuring readings however high never stop below the topmost level.
- On sensors with `bands`, `gte` must **coincide with a threshold** of those `bands` (the bool fact means
  "from this band upwards", never misaligned from the bands at any reading); `lte` is rejected, because thresholds belong to the upper band
  so `lte` would misalign exactly at the boundary.
- A criterion decided by a sensor must not have a fixed value in `[sim.facts]` (or `SimSession.load(facts=)`):
  such a value would never be read. `:set` in the REPL and on the `--ui` page rejects it and redirects to `:sensor`.

At runtime — fail-closed, no guessing:

- If a reading is **unavailable** (error flags, NaN, or corrupted files on `linux`, device disappeared, `sim` has no
  value), or is rejected by **any rule of that sensor** — numeric rule on non-finite readings
  (string, bool, NaN, inf), `bands` on a reading below the first threshold (open/shorted probe), `equals` on a type
  mismatch (`0` is not `false`), or the reading itself when empty or non-finite — then **all** facts
  for that sensor in that evaluation are **undefined** (`null` in `gate_facts`), and the session logs
  `sensor_unavailable` (§3). Gates reading them block with `criterion_unavailable`; because even veto criteria
  (`heat_critical`) are undefined, a "có" ("yes") answer is not enough, so the device **does not ask**. Gates not reading
  any facts from that sensor decide normally (`vent_on` of `factory-monitor` still runs).
- Confirmation answers recompute facts: asked at 45 °C, sensor fails before the "có" ("yes") response ⇒ still blocked.
- Replay reuses recorded `gate_facts`, so sensor facts cannot be recomputed. The trace carries the digest
  of `[sim.sensor_facts]` (`metadata.sensor_facts_digest`); if rules change after recording, `replay` warns
  (`sensor_facts_changed` event in the replay trace) — the verdict then does not test the new rules, requiring
  the session to be re-recorded. This is a warning, not a decision divergence: the exit code does not change.

**ADC channel gate facts — `[sim.analog_facts]`** (`analog.in`, TSK-I2a-04; declared channels on boards:
`sim-rpi5`, `linux-rpi5`). `criterion = { channel = "adc0" }` connects a `numeric` gate criterion to an `analog.in`
channel (RFC-0007 §3c, RFC-0009 §3f); `[requires]` declares `"analog.in" = { channels = ["adc0"] }`. On `sim`,
the value is `[sim.analog] adc0 = 1.25` (channel unit), changed via `:analog adc0 1.5` / `:analogs` in
the REPL and `:analog` on the `--ui` page; on `linux` it is a kernel reading (below). Each channel is read **once
per gate fact computation**; the reading passed to the gate is a `Fact` with a reading timestamp `read_ms` taken on the session clock
**before** the HAL read, and the engine computes `age_ms` (Q-62; trace `gate_facts` records `read_offset_ms`,
`eval_offset_ms`, `age_ms`). Checked during `neuroedge build` — error ⇒ `BoardCapabilityError` (NE3001): channel must
be declared by the board **and** listed in `[requires]`; every gate reading the criterion must declare it `numeric`, with matching `unit`,
and the channel's `[min, max]` must lie within the criterion's `range`. Numeric criteria in
`on_block.confirms` are rejected by `gate lint` for **all** numeric criteria (`GateSchemaError`, NE2002), so an ADC channel
is never confirmed on behalf of a user. A criterion decided by a channel must not have a fixed value in
`[sim.facts]`, nor exist simultaneously in `[sim.sensor_facts]`; `:set` rejects it and redirects to `:analog`.
At runtime — fail-closed: corrupted reading — value not set on `sim`; on `linux` device missing, file missing or
contains garbage, `*_fault` flags, unit mismatch; or non-finite values or **outside channel `[min, max]`** (never
clamped to bounds) — is `PerceptionUnavailableError` (NE5001) ⇒ undefined fact ⇒ BLOCK
`criterion_unavailable`. Each read, including failed attempts, logs an `analog_in` event (§3). Replay reuses
recorded `gate_facts` (both value and age), reading no channel; therefore facts cannot be recomputed, and changing
`[sim.analog_facts]` after recording is **not** warned like `[sim.sensor_facts]` (no digest yet).

**PWM and feedback channels (RFC-0010, TSK-W1-01).** PWM is a block within `digital.out`, not a separate
primitive: agent declares `"digital.out" = { pins = ["fan"], pwm = ["fan"] }` (each `pwm` channel must be declared by the board in
`digital_out.pwm.pins` **and** included in `pins`; checked during `neuroedge build`, `BoardCapabilityError` otherwise) and
calls `digital.out("fan").pwm(frequency_hz=1000, duty=0.4, ms=5000)` — `ms` is mandatory, with no default value
or "run forever". Processing order: `require_pin` → **board limits** (`on`/`pulse` on PWM channel, `pwm` on regular
pin, missing `duration_ms`, `frequency_hz` out of range, `duty` outside `[0, max_duty]` ⇒ `BoardCapabilityError`) →
envelope (reserved in advance for `duration_ms`, **the entire** time `duty > 0` counts, `duration_ms` > `max_continuous_ms` ⇒
`EnvelopeRefusedError` reason `max_continuous_ms`, no truncation) → `authorize` → execute. `duty` is quantised towards
0 according to `resolution_bits` so it never exceeds `max_duty`; a `duty` quantised to 0 is a safe state: runs
like `off` (no token, no envelope transit, `actuator_command` `off` with `cause: duty_zero`). `off`, expiry,
`close()`, and loss of supervision de-assert `enable_pin` then `duty = 0`, never blocked. Gates limit `duty`,
`frequency_hz`, `duration_ms` using the existing `arguments` block (RFC-0005): exceeding ⇒ BLOCK `argument_out_of_range`; tool
call missing parameters ⇒ `REJECTED`. `gate.v1` is unchanged.

`digital.out("fan").state()` (HAL: `pin_state()`) returns `duty` and `frequency_hz` along with `source`: `measured` when the pin
is in `digital_out.feedback.pins` and read back from hardware (on `linux`: PWM controller registers, read
back from sysfs — not HAL memory), otherwise `commanded`. Readback failures (file missing, garbage, conflicting registers,
`duty` exceeding `max_duty`, or frequency outside board range) raise `PerceptionUnavailableError` (NE5001), never
returning `commanded` instead. Each read logs a `pin_state` event (§3); replay reloads `source` as well. **Facts for gates:**
`[sim.feedback_facts]` — `criterion = { pin = "fan", quantity = "duty" | "frequency_hz" }` connects a `numeric` criterion to
a quantity from `state()`; scale is fixed by board (`duty`: `unit: ratio`, `[0, max_duty]`; `frequency_hz`:
`unit: Hz`, channel frequency range), and `neuroedge build` checks that `unit` matches and scale fits within criterion `range`
(`BoardCapabilityError`). Each channel is read **once per gate fact computation** and facts carry a `read_ms` timestamp
like `analog.in`. **Only `measured` reaches gates**: `commanded` values, failed reads, or quantities currently without
values (frequency of a disabled channel) leave the fact undefined ⇒ BLOCK `criterion_unavailable`. Reference boards
(`sim-rpi5`, `linux-rpi5`) **do not yet declare `feedback`** (proof on real hardware is the job of nightly Pi 5 and
rig builders), so `fan` there reads `commanded` and criteria connected to it can never be decided; tests use a board
with `feedback`. `:feedback fan duty=0.3 | fail <reason> | clear` sets simulated readback values on `sim` (REPL and `--ui`).
On `linux`, kernel channels reside in `NEUROEDGE_LINUX_PWM='fan=pwmchip0/2'` (or `LinuxHAL(pwm_channels=…)`), never
guessed; session prepares only channels listed in `[requires]` `pwm` (`needs["pwm"]`): kernel missing chip/channel ⇒
`BoardCapabilityError` at agent load, no fallback to software PWM; synchronised with `preflight(pwm=…)`.

### `digital.in` — `sim-rpi5` and `linux-rpi5` (RFC-0007 §3a, TSK-I2a-02)

`digital.in` is an extension primitive (RFC-0013): only boards declaring `[capabilities.digital_in]` have it —
`sim-default` lacks it, so agents using it build with `--board sim-rpi5`.

| Target | Backend | Tested In | Hardware Only | Task |
|:---|:---|:---|:---|:---|
| `sim` | `SimHAL.set_digital_in()` — initial level `[sim.inputs]`, changed via `:input <pin> <true\|false>` in REPL and `--ui` page (`digital_in_set` event); pin with unset level ⇒ read failure, not a logic level | PR | — | TSK-I2a-02 |
| `linux` | `LinuxHAL` via libgpiod v2: lines looked up by **name** like output pins, requested as **input** (never written, no bias or edge configured), held until `close()`; session requests all lines the agent reads immediately upon setup; lines read for the first time later are requested then | PR — fake gpiod (`tests/test_digital_in_linux.py`) · `gpio-sim` (`tests_linux/test_gpio_sim.py`; levels set via `sim_gpioN/pull`) | Real voltage, noise, and circuit bias | TSK-I2a-02 |

**Input pin gate facts — `[sim.digital_facts]`.** RFC-0007 does not specify how gate criteria connect to
pins; the minimal RFC-compliant approach follows the `[sim.sensor_facts]` pattern: `criterion = { pin = "…" }` is
the raw read level (high = `true`), `{ pin = "…", equals = false }` is "pin at low level". Like
`sensor_facts`, the table lives under `[sim]` but is also used on `linux`. Each pin is read **once per gate fact computation**,
immediately before gate evaluation (no buffered values used).

Checked during `neuroedge build` and session load — error ⇒ tripartite error, **before** requesting any line:

- Pin must be in the board's `digital_in.pins` **and** in `"digital.in" = { pins = [...] }` of
  `[requires]` (`@action(requires="digital.in:<pin>")` must also be a declared pin in `[requires]`); undeclared pin ⇒
  `BoardCapabilityError` (NE3001).
- Criterion must be evaluated by at least one gate, and all evaluating gates must declare type `bool` — logic levels are
  `bool` facts (not `numeric`, `level`, `choice`).
- Single source per criterion: cannot exist simultaneously in `[sim.sensor_facts]`; no fixed value in `[sim.facts]`;
  `:set` rejects it and redirects to `:input`.

Age and fail-closed (RFC-0007 §3a, §3e, §9 item 11):

- Facts carry HAL **reading timestamp** (`read_ms`, on `EventLog` clock, taken **before** the read). Engine computes
  `age_ms` during evaluation, like `numeric` criteria (RFC-0009 §3c); `gate_facts` records `read_offset_ms`,
  `eval_offset_ms`, `age_ms`, `source: "digital.in"`. `replay` trusts only an age explainable by the trace.
- `bool` criteria have no `max_age_ms`, so the ceiling is the constant `DIGITAL_IN_MAX_AGE_MS = 100` in
  `engine/verdict.py`: unconfigurable, gates and agents cannot relax it. Negative `age_ms`, exceeding the ceiling, or missing
  usable read timestamp ⇒ `criterion_unavailable`. The ceiling catches stalled read paths; hardware inputs stuck at a logic level
  are not caught by age, so critical gates need an additional independent criterion.
- Read failures (line not found, request failed, `get_value` error, missing chip, `sim` level unset) ⇒
  `PerceptionUnavailableError` (NE5001) ⇒ `digital.in` fact **has no value** ⇒ BLOCK
  `criterion_unavailable`, **even for `fail: open` gates** (`known_failure` does not bypass missing `digital.in`
  facts, just like missing `numeric` readings). Logic levels are never guessed.
- Reading inside `@action` body: `digital.input("<pin>").level()` (no token required, reading does not move actuators);
  each read is a `digital_in` event replayed by `replay` in order; failed reads are replayed as
  failed reads, reads exceeding recorded count are also failed reads — never repeating the last level.
- `replay` never touches host lines: `LinuxHAL(replay=True)` requests no lines.

### `motion.*` — `sim-rpi5` and `linux-rpi5` (RFC-0011, TSK-I2a-05)

`motion.*` is an extension primitive (RFC-0013): only boards declaring `[capabilities.motion]` have it — `sim-default`
lacks it, so agents using it build with `--board sim-rpi5`. `[requires]` declares `"motion" = { channels = [...] }`
and each channel must be a `motor` or `servo` channel declared by the board (NE3001 at build). API in `@action` body:
`motion.motor(channel, speed=, ramp_ms=)`, `motion.servo(channel, target=, speed_max=)`, `motion.stop(channel)`.

| Target | Backend | Tested In | Hardware Only | Task |
|:---|:---|:---|:---|:---|
| `sim` | `SimActuator` — model with ramp on virtual clock: motor speed reaches commanded value in `ramp_ms`, stop is immediate; servo reaches target at `speed_max`, `hold` maintains position while remaining powered. Displayed in REPL (`:motion`: channel, mode, setpoint, remaining lease, speed/position) and `--ui` page (from `motion_command`, `motion_safe` events) | PR (`tests/test_motion.py`) | — | TSK-I2a-05 |
| `linux` | Hardware PWM via sysfs — **same `SysfsPwm` writer from `hal/pwm.py`** used by `digital.out` PWM channels (RFC-0010) (`check`, `apply_ns`, `set_duty_ns`, `off`; a kernel channel `pwmchipN/M` has only one owner: overlapping bindings between `motion` channels and `digital.out` PWM pins are rejected when instantiating HAL) — `hal/motion_pwm.py` is motion policy only (motor 20 kHz, duty = speed; servo pulses 1000–2000 µs in 20 ms period mapped across target range) + driver **enable line**. Which channel maps to which `pwmchipN/M` is host wiring, not board configuration: `NEUROEDGE_LINUX_MOTION=wheel_left=pwmchip0/0;gripper=pwmchip0/1` or `LinuxHAL(motion_sources=…)`; unmapped channels rejected when instantiating HAL, no guessing. Enable lines managed by HAL and **held by supervisor process** (deadline = lease expiry + 250 ms), PWM written **before** enable line goes high, and reset to 0 immediately upon HAL startup (kernel retains last PWM duty) | PR — fake gpiod + fake PWM sysfs tree + real supervisor process on `tests/fake_gpiod` (`tests/test_motion_linux.py`); `gpio-sim` for enable lines, runtime SIGSTOP and SIGKILL (`tests_linux/test_gpio_motion.py`, PWM remains fake tree) | Real motors, servos, drivers cutting power when enable drops, RP1 PWM, e-stop button (Q-38), power-loss mid-command test (RFC-0011 §3f, phase B) | TSK-I2a-05 |

**Lease and run.** The verdict token of an `action` with `requires="motion:<channel>"` carries a **lease** for each
channel: the channel's `lease_ms` (200 if not declared by board; capped at 500), measured from the verdict, valid for **exactly one command**,
independent of `TTL_FACTOR`. Leases cannot be renewed other than through a new gate pass (new
command, full re-evaluation); calls that are BLOCKED do not renew and immediately return the channel to safe state.
A **run** is a sequence of consecutive leases on a channel (new lease arrives before old lease expires): the envelope reserves
`max_continuous_ms` **once at run start**, checks `min_interval_ms` **only then**, persists once
(not on every renewal), and refunds the remainder when the run finishes. All checks follow the order
`channel type correct → board limits → envelope → proof (lease) → drive → trace`; if proof fails, the
reserved envelope budget is refunded in full.

**Safe state** (`stop` if undeclared; `hold` only for servos declaring `holds_position` + `max_hold_ms`) is
dispatched, **bypassing the envelope, without tokens, and without waiting for ramps**, when: lease expires (`lease_expired`),
`max_continuous_ms` elapsed, `max_hold_ms` elapsed (`hold` ⇒ `stop`), barge-in (`barge_in`, `VoiceStateMachine` calls
`motion_barge_in` at step 1 of `docs/spec/voice_fsm.md` §5.2, in the same tick as the trigger event), BLOCK (`block`),
`motion.stop` (`stop`), `hal.close()` (`close`), supervisor drops enable line (`supervisor_heartbeat`,
`supervisor_deadline`), PWM write failure (`actuator_fault`). All causes after `close`, `max_*`, `supervisor_*`,
`actuator_fault` result in a complete stop even if the channel declares `hold`. Each triggers a `motion_safe` event with cause; channels
already in that state do not generate an event.

Dual limits, **stricter wins**: board (`speed_max`, `ramp_min_ms`, target range — HAL rejects via
`BoardCapabilityError`) and gate (RFC-0005 `arguments`, `BLOCK argument_out_of_range` before any facts).
Direction of rotation: `board.v1` does not yet allow motor channels to declare direction lines, so `direction = "reverse"` is rejected on **all**
targets (sim is no richer than the board); requires an RFC to enable.

### `linux` — `linux-rpi5`

| Primitive | Backend | Tested In | Hardware Only | Task |
|:---|:---|:---|:---|:---|
| `digital.out` | `LinuxHAL` via libgpiod v2; per-pin envelope with real auto-off timer and per-board persistent state file; supervisor process holds actuator pin lines (on by default, `hal/supervisor.py`) | PR — gpio-sim, and runtime SIGSTOP on gpio-sim (`tests_linux/test_gpio_envelope.py`) | Voltage, timing | TSK-S3-05, N2-01, N2-02 |
| `digital.out` — PWM *(only boards declaring `digital_out.pwm`, e.g. `linux-rpi5`)* | **Kernel hardware PWM only** via `/sys/class/pwm/pwmchipN/pwmM/{period,duty_cycle,enable}` — `hal/pwm.py`; no bit-banging. `enable_pin` is a HAL gpiod line, held by the supervisor process with the envelope deadline: raised after controller is programmed, lowered **before** shutting down controller | PR — fake sysfs tree + fake gpiod + mock supervisor (`tests/test_hal_linux_pwm.py`); gpio-sim for `enable` line and SIGSTOP (`tests_linux/test_gpio_pwm.py`). **No simulated PWM chip on runner** (gpio-sim only has lines; azure kernel lacks `pwm-sim`), so real controllers tested only on nightly Pi 5 | Real pulses, load, real readback | TSK-W1-01 |
| `audio.in` | **File backend**: WAV (`--voice-file`) at any rate 8–96 kHz, 1–2 channels → mono at board rate (`hal/audio.py`, `open_audio_file`) · **Live backend**: `sounddevice` (PortAudio) reads `neuroedge.ec.source` node of `module-echo-cancel` (Q-22) | PR — file backend on fake gpiod + mock `sounddevice`; `tests_linux/test_audio_file.py` on gpio-sim (**runner lacks `snd-aloop`**, so live backend runs only on hardware) | Microphone, AEC, acoustics — RPi 5 + I2S HAT, `snd-aloop` on Pi | out of roadmap (Q-77), code retained: TSK-S5-08 |
| `audio.out` | **File backend**: `Speaker` timeline records WAV at board rate (`--voice-out`) · **Live backend**: `sounddevice` plays to `neuroedge.ec.sink` node (AEC reference signal) | PR — as above | Speaker, volume | out of roadmap (Q-77), code retained: TSK-S5-08 |
| `sensor.read` | sysfs **hwmon** and **IIO** (`/sys/class/hwmon/*/temp1_input`, `/sys/bus/iio/devices/iio:device*/in_*`) — `hal/sysfs.py` | PR — `i2c-stub` + `lm75` driver → hwmon (`scripts/setup_i2c_stub.sh`, `tests_linux/`); IIO on fake sysfs tree (`tests/test_hal_linux_io.py`) | Real sensors; IIO on Pi only (`CONFIG_IIO` disabled on runner) | TSK-S5-09 |
| `analog.in` | sysfs **hwmon** (`inN_input`, mV → V per `HWMON_UNITS`) and IIO, channels located by **source** `NEUROEDGE_LINUX_ANALOG='adc0=hwmon:ads7828/in0'` / `LinuxHAL(analog_sources=…)` (like `sensor.read`, `board.v1` lacks channel-to-device mapping keys) or by `inN_label` label; converted to declared channel unit, rejected outside `[min, max]` as read errors — `hal/analog.py`, `hal/linux.py` | PR — fake sysfs tree (`tests/test_hal_linux_analog.py`); `i2c-stub` + `ads7828` driver → hwmon, code `0x800` → 1249 mV, gate decides on reading, replay (`scripts/setup_i2c_stub.sh`, `tests_linux/test_analog_in.py`) | Real ADC on Pi 5 (spike TSK-N3-03 only proved `i2c-stub` + hwmon, RFC-0007 §3c demands nightly hardware evidence before I2a exit criteria) | TSK-I2a-04 |
| `display` | Checked and frame written using exact `sim` code (`make_frame`), then → `/dev/fb*` on Pi, or in-memory only — `hal/framebuffer.py` | PR — in-memory frame + digest; `/dev/fbN` via `vfb`, or `vkms` on azure kernel (`scripts/setup_vfb.sh`) | HDMI/DSI panel | TSK-S5-09 |
| `i2c` *(only boards declaring `i2c`, e.g. `linux-rpi5`)* | `/dev/i2c-N` via `I2C_SMBUS` ioctl (`fcntl` + `ctypes` only, no added dependencies) — `hal/i2c_bus.py`, agent API `hal/i2c.py` | PR — transport on mock `ioctl`, policy on mock bus recording all transactions (`tests/test_hal_i2c.py`); `i2c-stub` with `ina219` (0x40), `ads7828` (0x4a), `lm75` (0x48) (`scripts/setup_i2c_stub.sh`, `tests_linux/test_i2c_read.py`) | Real chips, pull-ups, real timeouts | TSK-I2a-03 |

**Safety envelopes on `sim` and `linux`** (RFC-0007 §3d, TSK-N2-01, TSK-N2-02; implementation `python/neuroedge/hal/envelope.py`).
The four numbers for each actuator pin come from `board.v1`; `sim-*` has the exact numbers of the board it mirrors, no richer.

- **Atomic reservation.** Each `on` or `pulse` command reserves in advance the exact duration the pin will remain on: `min(deadline, max_continuous_ms)`,
  or `max_continuous_ms` when the command has no deadline. Check and reservation occur as a single step under a per-pin lock; two concurrent
  commands cannot both pass through remaining budget. Early turn-off refunds unused portions; failed `authorize` refunds 100% and consumes no token.
- **Active pin rejects second turn-on command** (`already_on`): no "re-triggering to extend". `min_interval_ms` is measured from when the previous turn-on
  **ended**. `off` commands and all commands toward safe state are never blocked, requiring no token (`threat_model.md` §1).
- **Clock.** `sim`: session clock (`EventLog.clock`), pin auto-turns off at deadline without timers (lazy handling on next
  command and in `run_due()`); `linux`: real timer in `LinuxHAL`, and envelope treats pin as on until HAL confirms line release.
  Replay decides based on recorded timestamps of each command (`ReplayClock`), ensuring identical decisions at any playback speed.
- **Surviving reboots (`linux`).** On-time is recorded **before** turn-on, one JSON file per pin
  (`{"version": 1, "name": <pin>, "on_ms": [...]}`) in **a per-board directory**: `$NEUROEDGE_LINUX_ENVELOPE_STATE`, defaulting to
  `$XDG_STATE_HOME/neuroedge/envelope/<board id>` (`~/.local/state/…`). Per-board because pins belong to the hardware rig, not the agent:
  two agents on the same board share one window. After reboot, all recorded activations occupy budget up to `window_s`, and each pin waits
  `min_interval_ms` before its first turn-on. Missing, corrupted, or unwriteable files ⇒ treat entire window as exhausted (`window_unreadable`). A fresh
  rig initialises empty files via `NEUROEDGE_LINUX_ENVELOPE_INIT=1` (or `envelope_init` in `target_options`); this flag creates only **non-existent** files,
  never overwriting existing files. `sim` maintains identical rules in memory, without files or reboots.
- **Out-of-process supervision (`linux`) — ON by default.** Lines of all enveloped pins are held by a separate process
  (`hal/supervisor.py`; separate session, so SIGSTOP sent to the runtime process group does not stop it). Runtime issues commands via
  pipes and sends heartbeats; missed heartbeats exceeding `heartbeat_timeout_ms` (default 1000 ms) while lines are active, deadline overrun (reserved
  duration + 250 ms), or pipe closure (runtime crash) ⇒ supervisor drops lines. Runtime detects this on next message and logs
  `actuator_command` `off` with `cause`. **Fail-closed:** if supervisor fails to start, or communication drops mid-session
  ⇒ all turn-on commands on enveloped pins are rejected (`envelope_refused`, `reason: supervisor_unavailable`, before `authorize`
  so consuming no token), while `off` always executes; never "runs without supervision". Intentional disabling is reserved for testing and debugging:
  `LinuxHAL(supervise=False)` or `NEUROEDGE_LINUX_SUPERVISE=0`; replay is unmonitored. Status (`on` · `off` ·
  `failed`) is recorded in `metadata.supervision` of the session trace, and `failed` includes event `supervision_unavailable {reason}`, enabling
  post-auditing to see that the session ran without this safety layer. Session tests use in-process mock `gpiod` so they disable explicitly;
  `tests_linux/` keeps default (on, real gpiod).

**Sensors on `linux` are located by name, not index** (`hwmon3`, `iio:device0` shift with probe
order), just as GPIO pins are resolved by line name: channels matching board sensor names by label, or via a
machine-configured **source** — `LinuxHAL(sensor_sources=…)` or environment variable `NEUROEDGE_LINUX_SENSORS`.
Source syntax and unit table: `python/neuroedge/hal/sysfs.py`. Sources are not in `boards/*.toml`
(`board.v1` lacks fields for this — declaring I2C buses on boards is RFC-0007); their keys must be sensors
declared by the board. Safety rules:

- Every read reaches kernel; missing source, conflicting sources, unreadable file, non-finite value,
  `*_fault` flags, or channel type with unknown unit ⇒ `BoardCapabilityError`, never returning default
  values. "Reaches kernel" does not mean newer than driver update cycle (lm75 ≈ 1.5 s).
- If agent declares unit for sensor (`[sim.sensors] temperature = { value = …, unit = "C" }`), kernel readings
  in different units are rejected, not compared against thresholds written for the declared unit. Gate facts compute
  from kernel readings following the exact `[sim.sensor_facts]` rules of `sim` (above), including `bands`.
- Replay uses recorded values only: sensors missing readings in trace raise errors, without reading kernel; display
  frames render in memory.
- `door_contact` and `motion` on `linux-rpi5` are GPIO inputs, not hwmon/IIO: not yet readable on
  `linux`, agents requiring them are rejected before requesting lines.

**Read-only I2C** (RFC-0007 §3b, TSK-I2a-03). The API provides no data-writing function: the sole write is the register
pointer, directed exclusively to registers within `readable_registers` of devices on the board allow-list,
immediately before a repeated-start read (SMBus *read byte/word data*, `width` 1 or 2 bytes; 16-bit
numbers returned in wire byte order, high byte first). Devices without declared `readable_registers` accept
receive-byte only. All board checks (bus, device — by name or address —, register) execute **before**
selecting nodes or sending transactions; addresses outside the allow-list are enumerated only by `i2c_scan` (reading each
address `0x03..0x77` via read-byte, never quick-write) and all reads to them are rejected. NACK,
timeout, or byte counts differing from requested: retry **once**, then `i2c_read` records `reason` instead of
`value` and raises `PerceptionUnavailableError` (NE5001); self-recorded logs (replay) do not retry.
`i2c` does **not** enter gates as a criterion: RFC-0007 admits only `digital.in` and `analog.in` into gates; agent
reads I2C in `@action` bodies. Nodes for each board bus are host-specific, not in `boards/*.toml`:
`LinuxHAL(i2c_nodes={"i2c1": "/dev/i2c-1"})` or `NEUROEDGE_LINUX_I2C='i2c1=/dev/i2c-1'`, never guessed
(adapter numbers vary across boards and boots). Addresses are forced (`I2C_SLAVE_FORCE`) because chips with existing hwmon drivers
(`ads7828`, `lm75`) return EBUSY for normal requests. Agent declares in `[requires]`:
`"i2c" = { devices = ["i2c1/ina219"] }` — each `bus/device` must be on the board allow-list (build-time check,
`BoardCapabilityError`), and `@action(requires="i2c:i2c1/ina219")` must be declared in `[requires]`.

**I2C values on `sim` — `[sim.i2c."bus/device"]`** (TSK-I2a-03, sensor pack). I2C does not enter gates, so
this table is not a fact source: it defines what `i2c.read()` inside `@action` receives on `sim`, matching
`SimHAL.set_i2c()`. Each line is `"0x02" = 24000` (one byte) or `"0x02" = { value = 24000, width = 2 }`
(16-bit register, values in wire byte order). `neuroedge build` verifies: register must be in
`readable_registers` of device on board allow-list (`BoardCapabilityError`), device must be listed in
`[requires]` `i2c`, value must fit `width`. On `linux` chip responds and this table is unused.

**Sensor pack sample agent — `fixtures/agents/rail-gate`** (I2a exit criterion 3). A battery-powered gate:
`rail_open_gate` opens when limit switch reports gate at closed stop (`digital.in`, `bool` fact) and supply
voltage on ADC channel is at least 1.2 V (`analog.in`, `numeric` criterion with unit, scale, and `max_age_ms` locked in
gate); `rail_report` reads bus voltage of `ina219` via I2C inside action body then shows on display. Builds on
`sim-rpi5` and `linux-rpi5`; `sim-default` and Box-3 reject it, enumerating each missing primitive. Corpus
`fixtures/traces/sensor-pack/` (allowed; blocked due to rail sag and misaligned gate stop; blocked
`criterion_unavailable` due to out-of-scale ADC, stale 501 ms ADC reading, and floating limit switch) generated
by `scripts/gen_sensor_pack_traces.py`, replayed by `neuroedge verify` across **all boards declaring all three
primitives** (`sim-rpi5`, `linux-rpi5`). Boards lacking any primitive skip the corpus (`—` cell), not counted as
passing; the corpus counts separately from standard traces ("extension replays compared"), and `verify` fails if no
board can replay it. Tests: `tests/test_sensor_pack_sample.py`, `tests/test_sensor_pack_linux.py` (`linux`
session on mock gpiod, sysfs, and fake i2c-dev), `tests_linux/test_rail_gate.py` (gpio-sim + `i2c-stub`).

**The remaining two corpora of exit criteria I2a #3** (`tests/test_pack_corpora.py`): `fixtures/traces/fine-control/`
(agent `fan-pwm`: runs fan within limits, `duty`/`frequency_hz` exceeding gate limits ⇒ BLOCK
`argument_out_of_range`, second run rejected by envelope with `already_on`, `fan_load` criterion decided by `measured` duty
⇒ ALLOW or BLOCK `condition_not_met`, failed readback or `commanded` only ⇒ BLOCK
`criterion_unavailable`) generated by `scripts/gen_fine_control_traces.py`; `fixtures/traces/motion/` (agent `rover`:
lease renewed, BLOCK returns wheels to safe state `cause: block`, lease expired `cause: lease_expired`, speed exceeding
gate limits) generated by `scripts/gen_motion_traces.py`. `verify` replays fine-control on all boards declaring PWM
channels (`digital_out.pwm`; PWM is a block within `digital.out` so boards are evaluated per channel, not per primitive) and
motion on all boards declaring `motion` — `sim-rpi5`, `linux-rpi5`; otherwise `—`. Reference boards do not yet declare
`feedback`, so the two sessions requiring `measured` duty are recorded on a rig declaring it (copy of `boards/` in generator,
not changing repo) and carry `board_id: sim-rpi5`: replay does not read controllers, it reloads recorded facts. Replay
on `linux` with mock gpiod: `test_the_corpus_replays_to_what_it_recorded_on_every_board_that_declares_its_primitives`.

**Audio explicitly chosen, no guessing** (TSK-S5-08; out of roadmap per Q-77, code retained): two backends, never guessed.

- **File backend** is the default for `--voice-file` (and replay): WAV reads entire file, 16-bit PCM,
  1–2 channels, 8–96 kHz rate, converted to **mono at board `audio_in.sample_rate_hz`** using the exact
  channel mixing and resampling a TTS prompt receives (`to_mono`, `resample`); **does not open microphone**.
  `--voice-out` records `Speaker` timeline at `audio_out` rate — the board resamples,
  `sim` does not (invariant 7). Invalid file format, excessive duration (> 600 s), missing file ⇒ tripartite error,
  no events logged.
- **Live backend** via `sounddevice` (PortAudio, extra `neuroedge[audio]`): loaded only when
  `LinuxHAL(audio="live")` or `NEUROEDGE_LINUX_AUDIO=live`; defaults to reading/writing the exact two
  AEC nodes from §6.1 — `audio.in` reads `neuroedge.ec.source` (echo-cancelled), `audio.out` plays to
  `neuroedge.ec.sink` (reference). Change nodes via `NEUROEDGE_LINUX_AUDIO_IN` /
  `NEUROEDGE_LINUX_AUDIO_OUT`. Missing device, device vanishing mid-session, or device rejecting
  board rate/channels/16-bit ⇒ tripartite error; **silence is never read as input**.
- Replay opens no devices (file backend), just as `display` draws in memory. Real-time voice
  sessions (real microphone/speaker running alongside provider) remain `TODOS.md` #45; here are the HAL primitives
  that session will use. Lacking a real session to drive it, **live input has not been tested on
  hardware**: buffer overflow (device dropped audio) logs `audio_in_overflow` then stops the
  session — timeline never shrinks in silence.
- When live backend is selected, `LinuxHAL` **opens and verifies both devices in `preflight`, before
  requesting any GPIO line** (Q-16): missing microphone/speaker ⇒ tripartite error, before holding any pin.
  `--voice-file` always forces file backend, so `NEUROEDGE_LINUX_AUDIO=live` never causes a WAV session to open devices.

**Display explicitly chosen, no guessing:** `LinuxHAL(display="memory" | "/dev/fbN")` or
`NEUROEDGE_LINUX_DISPLAY`; unselected ⇒ `display` raises error. Framebuffer reads pixel layout from
kernel (`FBIOGET_*SCREENINFO` ioctls: 16/24/32 bits, color offsets; grayscale/FOURCC/`msb_right` modes
rejected), writes line by line from top left, opening and immediately closing device per frame; text frames rejected
(no font — accepted by `memory`). Interactive sessions (`run`, `record`, `mcp serve --target linux`) check
all sensors required by agent and `[sim.sensor_facts]`, and display backend if agent needs `display`, **before**
requesting any GPIO line.

### Extension primitive `vision.in` — `sim-rpi5` and `linux-rpi5`

| Primitive | Backend | Tested In | Task |
|:---|:---|:---|:---|
| `vision.in` on `sim` (`sim-rpi5`) | Virtual camera replays recorded frame sequence (`[sim.vision]`) on session clock, matching declared board mode, driver-style queue; sequence exhaustion ⇒ camera lost; labels provided by `replay` model ([`camera.md`](camera.md) §4) | PR (`tests/test_virtual_camera.py`, `tests/test_vision_camera.py`) | TSK-V1b-02 |
| `vision.in` on `linux` (`linux-rpi5`) | V4L2 node selected by machine (`NEUROEDGE_LINUX_CAMERA`), pure Python, matching declared mode ([`camera.md`](camera.md) §5) | PR with mock driver (`tests/test_v4l2.py`); job `linux-hal` with `vivid` (`scripts/setup_vivid.sh`, `tests_linux/test_camera_v4l2.py`) | TSK-V1b-01 |
| Corpus `vision.in` | `fixtures/traces/vision/` replay across all boards declaring `vision.in` ([`camera.md`](camera.md) §8) | PR · `neuroedge verify` | TSK-V1b-02 |

`sim-default` (mirroring Box-3) has no camera: agents requesting `vision.in` rejected at build time. Hardware only: real latency of CSI/USB drivers, noise, and exposure;
cross-target inference equivalence (`tolerance`): TSK-V1b-04.

### `esp32s3` — `esp32s3-box-3`

| Primitive | Backend | Tested In | Hardware Only | Task |
|:---|:---|:---|:---|:---|
| `digital.out` | ESP-IDF `gpio` downstream of `NETR` tree walker and C token ledger | PR — walker and C token ledger compiled on host (truth table, ASan/UBSan) · QEMU (`firmware-qemu`, every PR touching `targets/**` and nightly) — boot-time gate self-test, full firmware generated for a new agent (`agent-firmware`); pin commands via UART (QEMU lacks GPIO matrix) | Real pins | walker, token ledger, self-test: TSK-S4-02, S4-07, S4-08 · agent firmware: I3-01 · pins: S4-01 · UART: S4-09 |
| `audio.in` | I2S ES7210 + ESP-SR AFE (AEC, VAD) — driver from XiaoZhi | **No** — QEMU lacks I2S; ESP-SR is a prebuilt Xtensa library, does not run on host | Entire primitive | out of roadmap (Q-77), code retained: TSK-S5-01, S5-02 |
| `audio.out` | I2S ES8311 | No | Entire primitive | out of roadmap (Q-77), code retained: TSK-S5-02 |
| `sensor.read` | ESP-IDF I2C driver | QEMU — mock driver via same HAL interface (QEMU lacks I2C) | I2C bus, sensors | TSK-S4-03 |
| `display` | `esp_lcd` + LVGL | PR — **same LVGL UI code** built on host with LVGL test display, compared against golden image ([`ui.md`](ui.md): screens, language rules, golden generation) · QEMU — `esp_lcd_qemu_rgb` | SPI lines to ILI9342C/ST7789 | TSK-S4-10 |

Each cell has a task. Three cells can only be tested on hardware (`audio.in`, `audio.out` on `esp32s3`, and
acoustics on `linux`); they belong to nightly TSK-S4-05 and the I7 exit criteria (roadmap §4.8); the `esp32s3` audio cells are out of the roadmap (Q-77).

## 3. Trace Events by Primitive

Schema `trace.v1` leaves `type` open and `data` as object, so adding event types **requires no RFC**.
Names and fields below are normative; all targets emit the same names. Which events are emitted on which targets
follows the corresponding cells in §2. The "Role during replay" column specifies what enters **decision matching**
(gate verdict + pin commands, as compared by `replay` and `verify`) — L1–L3 guarantee levels of Action CI
defined in `neuroedge-prd.md` FR-CI-LVL.

| Primitive | Event | `data` | Role During Replay |
|:---|:---|:---|:---|
| `audio.in` | `text_input` · `audio_in_vad_start` · `audio_in_segment` · `audio_in_overflow` | `{text}` · `{energy_db}` · `{sha256, duration_ms, sample_rate_hz}` · `{}` | **Input.** Replay starts from recorded perception outputs (`intent_extracted`), without rerunning audio. `audio_in_overflow`: live device dropped captured audio (reader fell behind) — session **stops** rather than feeding a timeline shrunk into silence (Q-21) |
| `audio.out` | `tts_stream_start` · `tts_stream_end` · `knowledge_retrieved` | `{text}` · `{duration_ms, sha256?, reason?}` (`reason`: `docs/spec/voice_fsm.md` §8) · `{entries: [{id, score}]}` | **Output** — text does not enter decision matching; `knowledge_retrieved` indicates what knowledge grounded the answer |
| `digital.out` | `actuator_command` · `actuator_aborted` | `{pin, operation, duration_ms, frequency_hz?, duty?, cause?}` · `{pin, reason}` — `frequency_hz` and `duty` (quantised) present only for `operation: pwm` (RFC-0010), entering golden `safety_view`; `cause` present only when **HAL** autonomously resets pin to safe state, not from agent command: `max_continuous_ms` (envelope truncates command without deadline or exceeding ceiling) · `duty_zero` (`pwm` command with `duty` quantised to 0 runs as `off`) · `supervisor_heartbeat` · `supervisor_deadline` (supervisor process drops lines, §2 `linux` section). Commands ending by their own `duration_ms` do not emit a second event | **Decision** — compared against golden on every `replay` / `verify` |
| `digital.out` (PWM) | `pin_state` · `feedback_set` | `{pin, source, duty?, frequency_hz?, use?}` or `{pin, reason, use?}` on readback failure · `{pin, duty?, frequency_hz?, fail?, clear?}` | **Input** (RFC-0010 §3b, §9.4) — one event per `state()` (`use: fact` when read to compute gate facts); `source` is `measured` or `commanded`, `frequency_hz` omitted when channel off. Readback failures record `reason` (NE5001), never recording `commanded` instead. Replay feeds back exact recorded `source` and values; `use: fact` reads not replayed as results already reside in `gate_facts`. `feedback_set`: user modifies channel readback in REPL/UI (`sim` only) |
| `digital.out` (envelope) | `envelope_refused` | `{pin, operation, reason, limit_ms?, used_ms?, requested_ms?, wait_ms?, remaining_ms?}` — `reason`: `window_budget` (`limit_ms` = `max_on_ms_per_window`, `used_ms` reserved in window, `requested_ms` additional requested) · `min_interval_ms` (`limit_ms`, `wait_ms` remaining wait) · `already_on` (pin currently active or command pending; `remaining_ms` until active command deadline) · `window_unreadable` (on-time log missing, corrupted, or unwriteable) · `supervisor_unavailable` (`linux`: supervisor process not running, §2 `linux` section) · `max_continuous_ms` (for `pwm`, RFC-0010 §3d: command with `duration_ms` exceeding ceiling rejected outright, `limit_ms` = ceiling, `requested_ms` = requested duration; `digital.out` auto-shuts off at ceiling, not rejected) | **Decision** — envelope rejects turn-on command before `authorize` (RFC-0007 §3d, `EnvelopeRefusedError` NE1003); no companion `actuator_command` and token unconsumed. Commands toward safe state never emit this event. Compared against golden alongside `actuator_command` (`safety_view`: `{pin, operation, refused}`). Replay decides using **recorded timestamps** of commands (`ReplayClock`): commands rejected in recording must be rejected again with identical `pin`, `operation`, `reason`, and permitted commands must not be rejected — divergence is `Divergence` |
| `digital.out` (envelope, reboot) | `envelope_restored` | `{boot_ms, pins: {<pin>: {carried_ms: [ms values…]} or {unreadable: reason}}}}` — `boot_ms` is boot timestamp on trace timeline; recorded only when `linux` session starts with on-time logs from prior runs (fresh rig initialised with `NEUROEDGE_LINUX_ENVELOPE_INIT=1` omits this event) | **Replay input** — replay does not read machine state files: it seeds envelopes from this event (each `carried_ms` reserves budget up to `window_s` after `boot_ms`, pin waits `min_interval_ms` from `boot_ms`), ensuring commands rejected due to carry-over from prior sessions are rejected again with identical `reason`. Seeding less than recorded (tampered trace) ⇒ command no longer rejected ⇒ `Divergence`; unreadable entries ⇒ treat entire window as exhausted. Traces lacking this event (all canonical traces) replay from empty state |
| `digital.out` (remote actuator, RFC-0018 §3i) | `remote_command_sent` · `remote_command_acked` · `remote_command_failed` · `remote_state` · `remote_state_unknown` · `remote_state_confirmed` · `remote_level_violated` | `{actuator, command_id, operation, duration_ms?, lease_ms?, level, plugin}` (`operation` ∈ `on` · `renew` · `off`; `level` is plugin level) · `{actuator, command_id, latency_ms}` · `{actuator, command_id, kind}` (`kind` ∈ `not_sent` · `ambiguous` · `rejected`) · `{actuator, state, via, read_offset_ms}` (`state` ∈ `on` · `off`, `via` ∈ `push` · `poll`; timestamp measured by receiver: call time minus added plugin age) · `{actuator, why, since_offset_ms}` (`why` ∈ `command_timeout` · `link_lost` · `stale` · `restart` · `readback_failed`) · `{actuator, state, unknown_ms}` · `{actuator, level, expected_off_ms, observed}`. Turn-on commands still emit pin `actuator_command` (unaltered shape) **before** `remote_command_sent`; HAL auto-`off` at deadline emits `actuator_command` with `cause` like `_auto_off`. State latch rejection ⇒ `envelope_refused` with `reason` `actuator_state_unknown` · `actuator_quarantined` · `already_on` **and** `state` field (HAL state) | **Informational** — does not enter decision matching; NE4001 lint (`trace.py::lint_remote`): `remote_command_sent` `on` must immediately follow `actuator_command` on same pin within same step, `renew` only within acknowledged run not yet turned `off`. Replay does not instantiate plugins: each turn-on receives recorded state latch decision (from `envelope_refused` with `state` and `actuator_command`), envelope re-decides on recorded timestamps |
| `digital.in` | `digital_in` · `digital_in_set` | `{pin, value, use?}` or `{pin, reason, use?}` (failed read, no `value`) · `{pin, value}` | **Input** (RFC-0007 §3a) — replay re-feeds reads inside `@action` body in order, failed reads remaining failed reads. Reads with `use: fact` (gate fact computation) not re-fed as results already reside in `gate_facts`, which records **reading timestamp and age**: `read_offset_ms`, `eval_offset_ms`, `age_ms`, `source: "digital.in"`; replay recomputes `age_ms` then compares, and `age_ms < 0` or exceeding `DIGITAL_IN_MAX_AGE_MS` ⇒ BLOCK `criterion_unavailable`. Event reading timestamp is its own `offset_ms`. `digital_in_set` records user changing level in REPL/UI (`:input`) |
| `motion.*` | `motion_command` · `motion_safe` | `{channel, kind, speed, direction, ramp_ms, lease_ms, run}` (motor) or `{channel, kind, target, speed_max?, lease_ms, run}` (servo), `run` ∈ {`new`, `renewed`} · `{channel, state, cause}`, `state` ∈ {`stop`, `hold`} | **Decision** (RFC-0011) — compared against golden: `replay` reruns actions on recorded clock, so lease expiries, envelopes, and barge-ins produce identical `motion_command`/`motion_safe` sequences (except `motion_safe` with cause `close`: end of session, not a decision). Envelope rejecting a run logs `envelope_refused` with `pin` set to **channel name**; reused or expired leases log `actuator_command_rejected {pin: channel, reason: lease_used \| lease_expired, code}` |
| `i2c` | `i2c_read` | `{bus, device, address, register?, value?, reason?}` — `register` present only on register reads | **Input** (RFC-0007 §3b) — `sim` replays recorded values only, without bus scanning. Each read logs an event; bus NACK or timeout logs `reason` instead of `value` (`PerceptionUnavailableError` NE5001). No data-writing events: API has no write path |
| `analog.in` | `analog_in` · `analog_set` | `{channel, value, unit, use?, non_finite?}` or `{channel, error, use?}` on read failure · `{channel, value, non_finite?}` | **Input** (RFC-0007 §3c) — one event per read (`use: fact` when read to compute gate facts); values outside channel `[min, max]`, missing device, or garbage are read errors (`error`, `PerceptionUnavailableError` NE5001), unclamped. Reading timestamp `read_offset_ms` and `age_ms` reside in evaluation `gate_facts` (RFC-0009 §3c): replay re-feeds recorded `value` and age, `age_ms < 0` or exceeding `max_age_ms` ⇒ BLOCK `criterion_unavailable`. `analog_set`: user modifies channel value in REPL/UI (`sim` only) |
| `sensor.read` | `sensor_read` · `sensor_set` · `sensor_unavailable` | `{sensor, value, unit?, use?, non_finite?}` · `{sensor, value, non_finite?}` · `{sensor, reason}` | **Input** — replay re-feeds exact recorded values; `use: fact` reads (gate fact computation) not re-fed as results already reside in `gate_facts`. `sensor_set` records user changing value in REPL/UI. `sensor_unavailable`: gate fact computation failed to obtain reading, or sensor rule rejected it (§2), making all facts for that sensor `null`; read-only, replay uses `gate_facts` |
| `display` | `display_frame` | `{width, height, format, sha256, text?}` (`text` when `format = "text"`) | **Output** — digest compared when golden specifies one, not blocking decision equivalence |
| `vision.in` | `vision_fact` | `{fact, kind, label, zone, min_frames, value, values, unavailable?, age_ms, max_frame_age_ms, present_score_floor, model: {name, sha256}, frames: [{frame_seq, vision_ref: {sha256, size}, captured_ms, labels, rejected?}]}` — each vision fact of a verdict, before `gate_evaluation_begin`; details and lint in [`vision.md`](vision.md) §5 | **Perception input.** Replay **recomputes** facts from recorded labels, calling no models and requiring no image frames; events mismatching their labels ⇒ undecided fact ⇒ BLOCK `criterion_unavailable`. No raw images: `vision_ref` is identity |
| `vision.in` | `camera_unavailable` | `{reason}` — camera unable to deliver in this evaluation; window cleared | **Perception input** ([`camera.md`](camera.md) §7). Replay ignores: companion verdict `criterion_unavailable` recomputed from undecided `vision_fact` |

Redaction mode (FR-TRC-07) hashes `text`; `audio_in_segment`, `display_frame`, and `vision_fact` naturally carry only digests or labels, not images.

**No NaN or Infinity in JSON.** JSON does not support these numbers (bare `NaN` breaks browser
`JSON.parse`, and the `--ui` page crashes). Non-finite readings are recorded as strings `"nan"`, `"inf"`, `"-inf"`
with `non_finite: true`, and replay parses them back to floats. All other events, metadata, `--ui` page, and
`trace view` also never carry non-finite numbers (`json_safe` in `python/neuroedge/trace.py`);
`trace validate` rejects files with bare `NaN`/`Infinity`. Metadata `sensor_facts_digest` and event
`sensor_facts_changed` (replay traces only): §2, `[sim.sensor_facts]` rules.

Events outside primitives (tool call, confirmation, MCP host, `system_two_*`, turn measurement `turn_latency` /
`session_summary`) in single catalog `docs/spec/tool_calling.md` §7; conversation state machine events (`voice_state_changed`,
`wake_word_detected`, `audio_in_vad_end`, `stt_result`, `stt_unavailable`, `stt_fallback`) in `docs/spec/voice_fsm.md` §8. Replay skips `system_two_call`: System 2 does not change verdicts, so
sessions recorded online replay without models or keys.

## 4. Traces from `esp32s3` to Host

Firmware records each event as **one line on UART0 / USB-CDC**: prefix `NE1 ` followed by exactly one
`trace.v1` event, matching names and fields in §3 and `docs/spec/tool_calling.md` §7. This is the specification for
TSK-S4-09 (status in roadmap); C formatting in `targets/esp32s3/components/ne_trace/`, reader in
`python/neuroedge/testing/uart.py`.

```text
I (312) boot: ESP-IDF v5.4 2nd stage bootloader           ← normal log: ignored
NE1 {"offset_ms":0,"type":"device_info","data":{"board_id":"esp32s3-box-3","agent_version":"home-voice@0.1.0","device_id":"qemu","boot_id":"9f2c01aa"}}
NE1 {"offset_ms":3,"type":"gate_evaluation_begin","data":{"gate":"light_on@1.0.0","gate_digest":"sha256:4cc8…"}}
NE1 {"offset_ms":6,"type":"gate_facts","data":{"call_source":{"value":"local_grammar","confidence":null,"source":"context"}}}
NE1 {"offset_ms":9,"type":"gate_evaluation_result","data":{"verdict":"ALLOW","evaluations":{"call_source":"local_grammar"}}}
NE1 {"offset_ms":57,"type":"trace_end","data":{"events":4}}
NE_SELFTEST PASS walker=<n> token=<n>
NE_TRACE DONE sessions=1
```

**Line.** `NE1 ` at column 0, followed by a JSON object with exactly three keys: `offset_ms` (integer
≥ 0, device clock measured from `device_info`), `type`, `data` — no other keys (schema prohibits). UTF-8, maximum
**512 bytes** including prefix, terminated by `\n` (host also accepts `\r\n`). Strings escaped per JSON. If a line
does not fit, the device does **not** write a partial line: it drops the line while still counting it (see `trace_end`). Token
nonces are never included in any line.

**Session envelope.** Each session opens with `device_info` at `offset_ms` 0 and closes with `trace_end`; after the final
session, the device prints `NE_TRACE DONE sessions=<n>` — a regular log line, not an event — signaling to readers
that output is complete.

| Event | `data` | Meaning |
|:---|:---|:---|
| `device_info` | `{board_id, agent_version, device_id, boot_id, replay_of?, trace_digest?}` | Device self-declaration. `device_id = "qemu"` when built with `sdkconfig.qemu` (`CONFIG_NEUROEDGE_QEMU`), versus `esp32s3-<MAC>` on physical chips — simulation evidence is never misread as board evidence. `boot_id` is 8 random hex characters per boot. `replay_of` / `trace_digest`: session replaying a canonical trace |
| `trace_end` | `{events}` | Line count of the session preceding it, including `device_info` and dropped lines. Host count mismatch ⇒ error |

**Firmware records only what it computes itself.** Today: `gate_evaluation_begin {gate, gate_digest}`, `gate_facts`
(verdict inputs, identical to host), `gate_evaluation_result` with exact host keys
(`GateResult.to_event_data()`). Two areas not yet matching host, both correctly re-read during replay: out-of-domain
values and NaN confidences are written as `null` (device only knows "unreadable"). Gate labels
(`light_on@1.0.0`) and `on_block` text (`to`, `message`, `fallback_action`) are now present in `NETR` v2 (`ne_gate_name`…), but tables still accompany
firmware until `ne_trace` reads from the tree, generated from identical resolved gates (`ne_agent` component of `neuroedge build --target esp32s3`,
TSK-I3-01; `scripts/gen_firmware_vectors.py`). Self-test sessions consist of checks for the linked agent, each check
being one gate evaluation, with identical facts and verdicts computed by the host engine at build time; no pin commands; pin commands appear only in the replay
sessions below, and lack `actuator_aborted`: firmware HAL not yet present (TSK-S4-01).

**Numeric criteria in `gate_facts` and replay rules (RFC-0009 §4, §5).** Each `numeric` fact carries three additional integer keys on the trace timeline: `read_offset_ms` (HAL sensor read timestamp), `eval_offset_ms` (gate evaluation start timestamp), and `age_ms` (reading age, `eval_offset_ms - read_offset_ms`, may be negative if causality violated). During playback (`replay`), the player recomputes age `eval_offset_ms - read_offset_ms` and compares against recorded `age_ms`; on mismatch (trace altered), replay warns and re-traverses the tree with the recomputed age. A `numeric` entry missing any of the three keys is always treated as `criterion_unavailable`, never as passing.

**Host.** `neuroedge record --target esp32s3 --port <source>` retains `NE1 ` lines, discarding all other lines
(including `NE1001…`, `NE_SELFTEST`, `NEUROEDGE_MEMORY_JSON`), checks framing, then writes **one file per session**
via `TraceRecorder` (TSK-S3-01), validated prior to writing. Events belong to the device, verbatim and with exact
`offset_ms`. Host constructs only `metadata`:

- `session_id = sess_<boot_id><session sequence number within boot>`;
- `target = esp32s3`;
- `board_id`, `agent_version`, `device_id` obtained from `device_info`;
- `timestamp_utc` is the time host read `device_info` — for log files this is file read time, not runtime.

Corrupted `NE1` lines, excess keys, `trace_end` count mismatches, unclosed sessions at stream end, or new sessions opening
before prior sessions close (device rebooted) ⇒ `TraceValidationError` (NE4001) specifying `source:line`.
Never interpret a truncated trace as truth.

| `--port` | Source | Stops When |
|:---|:---|:---|
| file path, or `file:<path>` | QEMU log `-serial file:uart.log`, or saved capture | `NE_TRACE DONE` or EOF |
| `tcp://host:port` | QEMU `-serial tcp::5555,server` (QEMU waits for reader before booting, preserving initial lines) | `NE_TRACE DONE` or `--timeout` |
| `/dev/tty…`, `COMn`, pyserial URL (`loop://`, `rfc2217://`…) | board, via extra `neuroedge[serial]` | `NE_TRACE DONE` or `--timeout` |

Default `--baud` is 921600 (PRD Appendix D.2); USB-CDC ignores baud.

**Device replaying canonical traces.** Following self-test, firmware replays each trace in
`fixtures/traces/` (`main/trace_vectors.c`, `CONFIG_NEUROEDGE_REPLAY_VECTORS`), each trace as a session
carrying `replay_of` and `trace_digest` (file JCS digest). Each step receives the exact inputs `replay` provides
to host engine — recorded facts, recorded degraded captures, human confirmations —, generated into
`main/vectors/` by `scripts/gen_firmware_vectors.py`. The remainder is computed by the device:

| In Replay Session | Who Computes |
|:---|:---|
| Verdict, reason, `fail_mode` (including `gate_unreachable` / `budget_exceeded` per gate `fail`) | Device — C walker `ne_decide`, identical semantics to `engine/gate.py` (TSK-S4-07 tests across all gates) |
| Whether pin commands issued, and which pins | Device — C token ledger: token issued for action pins, `ne_token_authorize` per command |
| Command `operation`, `duration_ms` | **Host** — action table: executes @action once on `SimHAL` downstream of always-ALLOW engine, during vector generation |

`actuator_command` in replay sessions signifies token ledger authorisation for that pin; **no GPIO pins
move**. How actions physically execute on MCU replaces action table in TSK-S4-01. Script rejects, without
guessing, whatever firmware cannot yet replay: bounded arguments, `degrade` + `fallback_action`, sensor readings,
non-numeric confidence.

`neuroedge verify --targets esp32s3 --port <source>` reads those sessions and, for each canonical trace, compares the
session with corresponding `replay_of` against that trace as golden — matching `sim` and `linux` (TSK-S3-04;
divergence ⇒ NE4002). Prior to comparison, it rejects (NE4003, "stale firmware") sessions whose `trace_digest` differs from files
in checkout, or `gate_digest` differs from gates compiled from checkout: that would be a verdict on something else.
The `gate_digest` check is from RFC-0008 (three canonical traces carry it in
`gate_evaluation_begin`): host `verify` enforces it across all targets, whereas `replay` on user traces
only warns, since gates may be tightened intentionally — detailed rules in
[`10-target-equivalence.md`](../architecture/vi/10-target-equivalence.md) §5.
Missing `--port` ⇒ code 1; missing session for a trace ⇒ ✗. Output clearly attributes which portions were computed by device.

Firmware on QEMU runs on every PR touching `targets/**` or `fixtures/traces/`, and the `uart-trace` job in
`firmware-qemu.yml` runs `record` then `verify --targets esp32s3` on its UART log. Hardware boards, replaying
arbitrary traces on device (streaming facts down) and timing comparisons comprise the remainder of TSK-S4-04;
`replay --target esp32s3` still exits with code 2.

### 4.1 OTA on QEMU (TSK-S6-01/02/04, FR-OTA-01…04)

`scripts/qemu_ota.sh` (job `ota-rollback`) builds factory, new, wrong-key, unsigned, and corrupted images (phases a–g),
signed with single-use RSA-3072 keys, served via HTTP and reading UART. The app descriptor version —
what OTA compares against — for a user-built project originates from `version.txt` written by `neuroedge build
--target esp32s3` (`[agent] version`; setting and incrementing: `docs/user/nap-firmware.md` §6.6);
QEMU script overrides `PROJECT_VER` to build new image 0.2.0. QEMU **proves**:

- A/B slots: factory image continues running, new image flashes then boots, and failed updates do
  not corrupt the active slot;
- signatures: wrong-key images trigger `NE_OTA REJECTED reason=signature`, without `SWITCH`, device stays on
  old version, freshly written slot is erased (`NE_OTA ERASED`); unsigned images rejected identically; this is the same
  `esp_ota_end` verification path used on hardware;
- confirmation post-self-test: new image marks `NE_OTA VALID` only after gate self-test passes;
- local rollback: corrupted images (self-resetting prior to confirmation, or self-test failure ⇒
  `NE_OTA INVALID`) rolled back by bootloader to previous image on subsequent boot, and rolled-back version
  is blocked (`NE_OTA SKIP reason=rolled_back`). Decision whether to install is pure C function
  `ne_ota_should_install` (`ne_ota_policy.c`) — QEMU runs exact board code, including anti-downgrade
  against NVS version high-water mark (phase g: valid signature but lower than high-water mark ⇒
  `SKIP reason=downgrade`). The high-water mark is software-only protection; timeouts, download failures, redirects, unreadable
  versions, and re-advancing the mark at boot are tested only via host tests
  (`test_ota_policy_host.c`), with no QEMU phase.

QEMU **cannot** prove, requiring hardware boards:

- Real Wi-Fi and networking: QEMU lacks Wi-Fi (Q-21), so script uses `open_eth` NIC (slirp). On
  Box-3, `main.c` (`init_network_stack`) only configures STA (`esp_wifi_set_mode(WIFI_MODE_STA)` +
  `esp_wifi_start()`) without yet calling `esp_wifi_connect()` or implementing provisioning: today only
  QEMU `open_eth` runs.
- Power cuts during writes or validity marking; voltage fluctuations, flash write timing. Images **hanging**
  prior to self-test also belong here: task watchdog does not panic by default
  (`CONFIG_ESP_TASK_WDT_PANIC=n`), so device does not auto-reset — rollback happens only on subsequent reboot.
- Bootloader: OTA never writes bootloader (`esp_https_ota` switches app slots only), so rollback-capable bootloaders must be
  flashed **once over wire**; QEMU does not test initial flashing.
- Missing configuration: OTA compiles only when signature-on-update and rollback are enabled (Kconfig
  rejects `CONFIG_NEUROEDGE_OTA` otherwise); QEMU runs full `sdkconfig.ota` profile only, proving
  nothing about incomplete builds.
- Secure Boot / eFuse keys (TSK-S6-05, out of scope here): verification keys reside in running
  image, so wired access permits firmware modification; anti-rollback eFuses accompany Secure Boot.
- Two QEMU 9.0 limitations bypassed by script: flash model corrupts state upon warm reset
  immediately after flash writes during updates, and panic handlers hang rather than printing and
  resetting. Hence script runs **each boot in a separate QEMU process** (halting immediately after
  device `rst:` line) and corrupted images use reset (`esp_restart`) instead of panic; on hardware,
  identical otadata logic executes within a single update cycle.

## 5. Visualisation

Five surfaces, sharing self-rendered SVG components (door lock, light, relay, sensor gauge, display
frame). No CDN dependencies: `sim` must operate offline (FR-DX-02).

| Surface | Used When | Responsive | Task |
|:---|:---|:---|:---|
| Terminal (`run`, `replay`, `gate explain`) | Daily use, CI | Yes | TSK-S3-06, S3-18 |
| `neuroedge trace view <file>` → single static HTML file | Review, sharing with teammates, debugging incidents | Timeline, verdict + reason, pins, sensors, display frame; opens without server | TSK-S3-22 |
| `neuroedge run --ui` → local web page, live updates | Demo, 10-minute journey | FR-TGT-06: real-time virtual pin status; command input, sensor controls, `ask` confirmation buttons | TSK-S2-09, S3-26 |
| `neuroedge mcp serve --ui` → same page, for MCP sessions | Claude Desktop or external agents calling device, human observers monitoring and intervening | As above, in **same session** as MCP client (`tool_calling.md` §8) | TSK-S3-27 |
| `neuroedge trace export --format chrome` → Perfetto | Timing analysis | Opens in Perfetto UI (Apache-2.0) | TSK-S3-22 |

A local page serves until Ctrl-C, SIGTERM or SIGHUP (all three write the trace and remove
`ui.json`); it never reads stdin, so a closed stdin does not stop it. A page a script or check starts
in the background passes `run --ui --exit-with-parent` (stop once the starting process is gone, or if
started under PID 1) and/or `--idle-timeout <s>` (stop after that long with no HTTP request; the open
`/events` stream does not count). `scripts/kill-ui.sh` stops leftovers.

Wokwi Elements (MIT) can replace renderings for lights, servos, relays, `ili9341` screens if bundled
(no CDN loading); door locks not provided out of box.

### 5.1 One page, the same sections for every agent

`run --ui`, `mcp serve --ui` and `trace view` render one page (`neuroedge/viz/assets/ui.js`). It is
laid out for someone testing an agent who did not write it; nothing in it is specific to a sample:

| Section | Shows | Comes from |
|:---|:---|:---|
| Header + "Trang này là gì?" | Agent, live or recorded, a four-step guide | trace metadata |
| 1 · Thiết bị | One card per pin: name, pin code, ON/OFF, a button per command that drives it | `[requires]`, `@action` pins, `commands.toml` |
| 2 · Cảm biến và dữ kiện | Readings with unit, the fact each derives (`water_hot: ≥ 29`), set / lose-signal controls (live); facts | `[sim.sensors]`, `[sim.sensor_facts]`, `[sim.facts]` |
| Thiết bị hỏi xác nhận | The open question, why it was asked, time left, yes / no | RFC-0006 confirmation events |
| 3 · Ra lệnh (live) | Free text plus one button per command pattern | `commands.toml` (first pattern) |
| Hội thoại | Commands, MCP calls, verdict lines, sensor changes, what the assistant said | trace events |
| 4 · Quyết định của gate | Per call: verdict word, action, who asked, each criterion ✓ / ✗ / ✓* (waived by a yes), outcome: pins moved, or why it blocked and whether a person could have unblocked it | `gate_evaluation_result`, the gate's `evaluate.*.instructions` and `on_block.confirms` |
| Chi tiết kỹ thuật (collapsed) | The raw event stream | trace events |

Names are the agent's own: `[ui.labels]` in agent.toml maps a pin, sensor or fact to the words the
page shows (`gate_relay = "Máy sưởi"`); without it the page shows the identifier. Labels are words
for people only: no gate, build or replay reads them, and they are not part of any schema or digest.
`trace view` has no agent loaded, so it shows identifiers and no command controls. Parts the
board lacks, a catalogue of part kinds and a drag-and-drop canvas: `virtual_parts.md` (Q-84).

## 6. Three Devices Running the Same Sample Agent

FR-TGT-02 and FR-TGT-03 require **sample agents running on real hardware** on RPi 5 and Box-3. Sample agent
`villa-concierge` declares `audio.in aec = true`, and `linux-rpi5` declares `aec = false`, so `build
--target linux` rejects it — sample agent covers only 2/3 devices. **Q-22 (decided, option A)** closes
this gap using PipeWire software AEC: TSK-S5-08 delivered live backends (out of roadmap per Q-77, code retained), drop-in configs, and
WAV file paths; `linux-rpi5` **retains `aec = false`** until nightly Pi runs pass both measurements
in §6.2, so `build` continues rejecting agents requiring AEC — no mechanism permits declaring unverified
capabilities. Three-target equivalence tests use agents requiring only `digital.out` (`minimal` template from
`neuroedge new`) or agents requiring audio without AEC (`--voice-file` on `linux`).

### 6.1 Wiring

`libpipewire-module-echo-cancel` creates four nodes (PipeWire documentation, `page_module_echo_cancel`):

```text
microphone ─► capture ─►┌─────────────┐─► source   ─► LinuxHAL.audio_in   (echo-cancelled)
                        │ echo-cancel │
LinuxHAL.audio_out ─► sink ─────►└─────────────┘─► playback ─► speaker
```

`audio.out` **must** play into the `sink` node: this is the reference signal subtracted from the microphone. Playing
directly to speaker deprives AEC of subtraction reference. Alternative is `monitor.mode = true`, sampling reference from
default sink monitor — used when external processes also play through speaker.

Bundled configuration delivered by TSK-S5-08 (out of roadmap per Q-77, code retained) at `pipewire/neuroedge-echo-cancel.conf` (in wheel:
`neuroedge/_data/pipewire/`, located via `neuroedge.paths.echo_cancel_conf()`), **copy** to
`~/.config/pipewire/pipewire.conf.d/` (user) or `/etc/pipewire/pipewire.conf.d/` (system), then
`systemctl restart --user pipewire.service`: `LinuxHAL` reads/writes the two nodes
`neuroedge.ec.source` / `neuroedge.ec.sink` here when live backend is selected:

```text
# neuroedge-echo-cancel.conf — bundled version, ready to use
context.modules = [
{   name = libpipewire-module-echo-cancel
    args = {
        library.name = "aec/libspa-aec-webrtc"
        node.description = "NeuroEdge Echo Cancel"
        capture.props  = { node.name = "neuroedge.ec.capture" }
        # target.object = "<I2S HAT microphone node name, from `pw-cli ls Node`>"   ← ONLY line that must be edited
        source.props   = { node.name = "neuroedge.ec.source" }      # audio.in reads here
        sink.props     = { node.name = "neuroedge.ec.sink" }        # audio.out plays here
        playback.props = { node.name = "neuroedge.ec.playback"
                           node.autoconnect = true }
    }
}
]
```

Bundled version **contains no placeholders**: omits `target.object`, module defaults to system microphone
source. To pin HAT microphone, uncomment and edit **exactly one line** `target.object` with node
name printed by `pw-cli ls Node` (pattern drawn from reference configuration, gist `fathonix/05de5398…`).

**What PortAudio sees — unverified on hardware.** Live `audio.in`/`audio.out` reads/writes devices
via `sounddevice` → PortAudio, whose default Linux host API is **ALSA**: it enumerates ALSA PCMs,
whereas `neuroedge.ec.source` / `neuroedge.ec.sink` are **PipeWire node names**. Those names reach
PortAudio only through bridging: `pipewire-alsa` plugin (usually bundled with PipeWire) exposes nodes to ALSA, and
the reliable approach is adding a PCM alias in `~/.asoundrc` / `/etc/asound.conf` targeting the node, or
passing exact device name/index printed by `python -c "import sounddevice; print(sounddevice.query_devices())"`
on that host (via `NEUROEDGE_LINUX_AUDIO_IN`/`_OUT`). **None of these steps has been verified on Pi** — resolving
names/aliases belongs to nightly TSK-S4-05; `LinuxHAL` "no input/output device named …" errors always
point readers to this section.

### 6.2 When `linux-rpi5` May Declare `aec = true`

Only when nightly runs on RPi 5 (TSK-S4-05) pass both criteria, on the reference board's exact HAT and speaker:

1. **No self-hearing:** play a fixed TTS utterance 20 times via `audio.out` with no one speaking —
   VAD on `audio.in` triggers zero times (0/20).
2. **Echo cancellation level:** ERLE (raw microphone energy relative to residual after cancellation, during identical playback segment) ≥ 20 dB.

Until passed, `aec = false` remains and `build` continues rejecting agents requiring AEC — no mechanism permits
declaring unverified capabilities. CI runners have no audio (`CONFIG_SOUND` disabled), so
these measurements run on Pi only.

## 7. What This Document Does Not Promise

- Cross-target **timing** equivalence (TSK-S4-04 compares decisions only).
- Audio quality, AEC, VAD under real acoustics — measured on hardware only (A6, I7 — roadmap §4.8).
- Tier 2–3 targets (`jetson`, `stm32`, `rp2350`) — RFC-0002.
