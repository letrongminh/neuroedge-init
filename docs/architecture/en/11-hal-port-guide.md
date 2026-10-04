# 11 · HAL porting guide for OEM partners

> **Scope:** taking NeuroEdge onto a new board or a new chip — the contract to keep, the code that is
> reused, the code to write, and how to prove the port correct. **Sources:** `python/neuroedge/hal/`, `boards/`,
> `targets/esp32s3/components/`, `targets/esp32s3/main/`, `docs/spec/hal_mcu_review.md`, RFC-0002, Q-13.

## 1. What can be ported today

| Kind of port | Possible today? | Notes |
|:---|:---|:---|
| **A new board for an existing target** (another Linux SBC, another ESP32-S3 board) | Technically yes; but `boards/` accepts only the **three tier-1 profiles** until RFC-0002 (`test_boards.py`), and the reference board of `esp32s3` is only Box-3 (invariant 6) | Good for internal experiments; not publishable yet |
| **A new target** (`stm32`, `rp2350`, `jetson`) | **Not yet**: the target list is closed at `sim`, `linux`, `esp32s3` in `schemas/` and `hal/board.py` | RFC-0002 (under discussion) opens the list by tier at I11; the community port tool kit at I13 |
| **Tier 3, community self-checked** (Q-13) | The process is planned at I13 (`TSK-P1-01…05`) | This chapter describes the part that already has code and the part that will change |

The rest describes the **contract** — it does not change when the target list opens — and the code that
can be reused right away.

## 2. The port contract

A port is correct when it keeps all of the following. Every clause already has an automatic check on the
three tier-1 targets.

| # | Contract | Meaning | Checked by |
|:---:|:---|:---|:---|
| 1 | **The five primitives of v1.x — a closed set** | `audio.in`, `audio.out`, `digital.out`, `sensor.read`, `display` (FR-HAL-01, KL-1). Tier 3 may lack some primitives depending on board capability, but may not add any arbitrarily. Any new primitive goes only through an RFC (RFC-0007: `digital.in`; RFC-0010: PWM; RFC-0011: `motion.*`; RFC-0012: `vision.in`; RFC-0013: board-optional — Q-53; see [`15`](15-target-architecture.md) §4) | `board.v1`, `PRIMITIVES` |
| 2 | **Pins by name** | Agent code uses logical names (`door_lock`); physical pin numbers live only in the HAL (KL-2) | the build cross-checks the names |
| 3 | **No pin moves without a token** | A pin command checks the pin name, then calls the `authorize` function wired into it, and only then drives the pin. A HAL with no token ledger wired in refuses every command | `test_hal_sim.py`, `tests_linux/test_gpio_sim.py`, token boot self-test on the chip |
| 4 | **A missing device is an error, not a pretence** | No `/dev/gpiochip*`, no sensor, cannot open the microphone ⇒ three-part error **before** any pin is held (Q-16); never return a default value | `preflight` of `LinuxHAL` |
| 5 | **Every command leaves an event** | `actuator_command`, `actuator_aborted`, `sensor_read`, `display_frame`… with the exact name and fields (`simulation_coverage.md` §3) | golden comparator |
| 6 | **A pending command can be cancelled** | Barge-in must cancel a pulse not yet delivered within ≤ 1 audio frame (RB-3) | `test_voice_fsm.py` |
| 7 | **Declaration is data** | Board capability is a `board.toml` file (on chip: a `const` table in flash — RB-4), not code (KL-4) | `schemas/board.v1.json` |
| 8 | **Same decisions** | Replaying the three normative traces gives the same verdicts and pin commands as golden | `neuroedge verify --targets …` |

## 3. Board declaration

The profile of the reference board, as a template:

```toml
schema = "neuroedge.board/v1"   # optional; absent means v1, any other version is refused (RFC-0015 §3c)

[board]
id     = "esp32s3-box-3"
name   = "Espressif ESP32-S3-BOX-3"
target = "esp32s3"
mcu    = "esp32s3"

[capabilities.audio_in]
channels       = 2
sample_rate_hz = 16000
aec            = true
vad            = true

[capabilities.audio_out]
channels       = 1
sample_rate_hz = 16000

[capabilities.digital_out]
pins    = ["door_lock", "porch_light", "gate_relay"]
backend = "esp_driver_gpio"

[capabilities.sensor_read]
sensors = ["temperature", "humidity", "door_contact", "motion"]

[capabilities.display]
width  = 320
height = 240
color  = "rgb565"
```

Declare only what the HAL **can run and has measured**. For example `linux-rpi5` keeps `aec = false`
until the echo cancellation measurement on the Pi passes (`simulation_coverage.md` §6.2): declaring
`true` early is promising something not proven.

## 4. Host-side port (Python)

A host HAL is a subclass of `HardwareAbstractionLayer`. `SimHAL` and `LinuxHAL` are two complete
examples.

```python
from neuroedge import BoardProfile, HardwareAbstractionLayer

class MyBoardHAL(HardwareAbstractionLayer):
    def __init__(self, board: BoardProfile, *, events, authorize, **options) -> None:
        super().__init__(target="linux", board=board, authorize=authorize)
        self.events = events
        # open nothing yet: devices are checked in preflight(), before any line is held

    def preflight(self, sensors=(), display=False, audio=(), where="") -> None:
        ...  # open or probe every device the agent needs; raise BoardCapabilityError on the first gap

    def digital_out(self, pin, operation, duration_ms=0, signature="", called_from="<unknown>"):
        super().digital_out(pin, operation, duration_ms, signature, called_from)  # name check, authorize, record
        ...  # drive the physical line only after the base call returned
        self.events.emit("actuator_command", {"pin": pin, "operation": operation, "duration_ms": duration_ms})

    def sensor_read(self, sensor, called_from="<unknown>", use=None):
        ...  # read the device every time; raise, never return a default reading

    def close(self) -> None:
        ...  # every line back to inactive and released, on every exit path
```

Rules when writing:
- **Call `super().digital_out` first** before driving the pin: it checks the pin name (a typo costs no
  token) and calls `authorize`. Do not check the token yourself.
- **Do not import `engine`, `actions`, `models`** from the HAL: `hal` is a leaf of the dependency graph
  (`test_architecture_layers.py::test_the_hal_is_a_leaf`).
- **Third-party libraries are imported late** in the function that needs them, with a three-part error
  naming the extra to install (example: `hal/linux.py::_import_gpiod`). Copyleft libraries may only be
  an optional extra (Q-11).
- **Release every resource on every exit path**, including SIGTERM and SIGHUP.

## 5. Chip-side port (C)

The firmware core is already **plain C99, with no ESP-IDF dependency**, so it is reused as is on another
chip:

| Code | Dependency | Reuse |
|:---|:---|:---|
| `components/ne_gate/` (walker `NETR`, token ledger) | none | verbatim |
| `components/ne_trace/` (`NE1` line format) | `ne_gate` | verbatim |
| `components/ne_agent/` (generated per agent) | `ne_gate`, `ne_trace` | regenerated by `neuroedge build` |
| `main/gate_selftest.c`, `main/trace_vectors.c` | no ESP-IDF | verbatim |
| `components/ne_ota/src/ne_ota_policy.c` | none | verbatim; `ne_ota.c` is the ESP-IDF part to rewrite |
| `main/main.c`, `main/memory_probe.c` | ESP-IDF | rewritten for the new platform |

A new platform need only provide **four connection points** — that is the whole surface the C core
demands:

```c
/* 1. entropy for token nonces — the shape of esp_fill_random */
typedef void (*ne_random_fn)(void *buf, size_t len);

/* 2 and 3. where trace lines go, and the device clock in milliseconds */
typedef struct {
    void (*emit)(void *ctx, const char *line);   /* one line to the UART, no newline */
    uint32_t (*now_ms)(void *ctx);
    void *ctx;
    char *buf;                                   /* at least NE_TRACE_LINE_MAX + 1 bytes */
    size_t cap;
    uint32_t t0_ms;
    uint32_t lines;
    uint32_t dropped;
} ne_trace_sink;

/* 4. run the boot self-test against the linked agent before anything else */
int neuroedge_gate_selftest(const ne_agent *agent, ne_random_fn fill_random, uint32_t boot_id,
                            uint32_t now_ms, char *line, size_t cap, ne_trace_sink *sink);
```

The boot sequence must stay as on `esp32s3` ([`04`](04-component-device-c4l3.md) §4): boot self-test
**before** everything else, and on failure it stops — no runtime gate, no action, no network.

**Not there yet:** a C interface for driving pins, reading sensors, audio (the on-chip HAL is
TSK-S4-01). When it exists, it must call `ne_token_authorize` before driving a pin, exactly as the host
HAL calls `authorize`. The mandatory memory constraints for it: RB-1…RB-4
(`docs/spec/hal_mcu_review.md` §2) — no allocation on the audio path, measured static buffers, command
cancellation within ≤ 1 frame, a `const` capability table.

## 6. Proving the port correct

| Step | Command | Passes when |
|:---:|:---|:---|
| 1 | `neuroedge board show <id>` and `neuroedge build --target <t> --board <id>` with each sample agent | the agent that fits the board builds; an agent demanding something the board lacks is rejected with `NE3001` |
| 2 | C tests of the core on host: `make -C targets/esp32s3/components/ne_gate` and `make … check-static` | every test passes under ASan/UBSan; no `.data`/`.bss`; per-function stack ≤ 512 bytes |
| 3 | Firmware boot | the line `NE_SELFTEST PASS walker=<n> token=<n>` at column 0 on the UART |
| 4 | `neuroedge record --target <t> --port <nguồn>` then `neuroedge trace validate` | every `NE1` session becomes a valid `trace.v1` |
| 5 | `neuroedge verify --targets <t> --port <nguồn>` (chip) or `neuroedge verify --targets sim,<t>` (host) | the three normative traces give the same decisions; a difference ⇒ `NE4002` |
| 6 | Tool-call and voice corpus on the new HAL | matches `expected_results.yaml` |

The tool that packages the vector suite to run **outside** the repo, and the `board check` command, are
I13 work (`TSK-P1-01`, `TSK-P1-05`).

## 7. Assets and licence of a port

- An OEM partner's HAL driver is **the partner's own**; it only has to keep the contract in §2.
- Every dependency, model and font shipped along must be on the allowlist of Q-11 and recorded in
  `NOTICE`. Nothing non-commercial may ship along (Q-45).
- The standards — `schemas/`, `docs/spec/`, `fixtures/compliance/` — are Apache-2.0 so that anyone can
  implement them; NeuroEdge code is PolyForm Noncommercial (`LICENSING.md`).
