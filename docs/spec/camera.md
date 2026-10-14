# Camera `vision.in` — modes, virtual camera on `sim`, V4L2 on `linux`

**Trạng thái:** canonical specification (TSK-V1b-01, TSK-V1b-02). Original contract: [RFC-0012](../rfc/0012-nguyen-thuy-vision-in.md)
§3a, §3b, §3e, §3f; RFC-0013 §3f (each board replays the corpus of the primitives it carries); invariant
`CHANGELOG.md` §3.3 #7 (`sim` is no richer than the board it mirrors). Implementation: `python/neuroedge/hal/vision.py`,
`hal/v4l2.py`, `hal/sim.py` · `hal/linux.py` (`vision_in`), `python/neuroedge/sim/vision/`. The *frame → gate
facts* portion (models, windows, `vision_fact`, replay) is [`vision.md`](vision.md); this document is the *camera* portion, i.e.,
where `Frame` comes from. Keywords **MUST**, **MUST NOT** carry their meanings as in RFC 2119.

## 1. Camera is an extended primitive with its own contract

`vision.in` is an extended primitive (RFC-0013 §3a): a board may declare it or not. The board declares capabilities using
`modes` (`board.v1`, `vision_in`); an agent declares requirements under `[requires]`; `neuroedge build` matches them; a session opens the camera
**in the exact mode selected by build**. Today only `sim-rpi5` and `linux-rpi5` declare `vision_in`: `sim-default` (mirroring Box-3)
**has no camera**, so an agent requiring `vision.in` is rejected at build time there (FR-HAL-05, I2a exit criterion 7).

## 2. `[requires] "vision.in"` — matching according to RFC-0012 §3b

```toml
[requires]
"vision.in" = { min_width = 640, min_height = 480, min_fps = 10.0, pixel_formats = ["yuyv", "mjpeg"] }
```

| Key | Type | Meaning |
|:---|:---|:---|
| `min_width`, `min_height` | integer ≥ 0 | mode must be at least as wide/high |
| `min_fps` | number ≥ 0 (finite) | mode must run at least at this framerate |
| `pixel_formats` | list in `yuyv` · `mjpeg` · `rgb565` · `rgb888` · `gray8` | mode must be one of those formats |

A board satisfies this when **at least one mode exists** meeting all thresholds (`Requirement.failures`, `hal/vision.py`, one function
for both build and session). The selected mode is the **first mode matching in the order declared by the board** — deterministic. The following are
rejected, not ignored: unknown keys (a mistyped threshold is an absent threshold, so build would allow an agent requiring more than the board
has), invalid value types, formats outside the closed enum. If no mode satisfies ⇒ `BoardCapabilityError` (`NE3001`) reporting the closest
mode and the threshold it failed (`vision.in … closest mode, 640x480 @ 30 fps rgb888, misses ['min_width 1920 > 640']`).

`[vision]` implies `[requires] "vision.in"`; missing ⇒ rejected by build. Along with `[vision]`, build checks (RFC-0012 §3c, §8):
criterion type with same name matches `kind`, no gate uses `confidence_gte` on visual facts, `present`/`count` always accompany
`confidence` with same label and region, named model exists, and no visual facts are decided in place by `[sim.facts]` or `[system_one]`
(`check_vision`, `check_system_one`, `engine/compiler.py`).

## 3. HAL interface

```python
camera = hal.vision_in(mode, called_from="…", clock=session_clock)   # one mode of the board
frames = camera.read_available()   # all frames arriving since previous call, oldest first; may be empty; non-blocking
camera.close()
```

| Type (`hal/vision.py`) | Meaning |
|:---|:---|
| `Mode` | `width`, `height`, `fps` (float), `pixel_format` — exactly one entry of `vision_in.modes` |
| `CameraFrame` | `seq` (frame sequence number **of the camera**), `captured_ms` (HAL read timestamp, on session `clock` — same clock as `Fact.read_ms`), `pixels`, frame description |
| `CameraUnavailable` | camera cannot deliver: missing, stalled, sequence ended, malformed frame size. Subclass of `PerceptionUnavailableError` (`NE5001`): does not add an error code |

`vision_in` only opens a mode **declared by the board**; any other mode is rejected (`BoardCapabilityError`). The camera **never fabricates frames**.
`captured_ms` is measured against the session clock: `captured_ms` of a real camera is when *the frame is retrieved from the driver*, not when the sensor
captured it — the discrepancy is capture thread latency (a few ms) and makes frame age appear slightly **younger**, not older; the 1000 ms ceiling and
gate `max_age_ms` are sufficiently wider than that discrepancy.

## 4. Virtual camera on `sim` (TSK-V1b-02)

`sim` reads no actual camera. It **replays** a sequence of recorded frames on the session clock, in one mode of the board, and it
is constructed to be **no better than the hardware it replaces**:

* only runs in a mode declared by the board, at the `fps` of that mode — the *k*-th frame is ready after *k + 1* periods of `1000 / fps` ms of
  the session clock, no faster;
* raw modes (`yuyv`, `rgb565`, `rgb888`, `gray8`) deliver frames of exact `width × height × bytes/pixel` bytes; frames of incorrect size are not
  frames of this camera and the camera raises `CameraUnavailable` (compressed mode `mjpeg` accepts any size);
* has a **driver-style queue** of `depth` frames (default 4). A late reader sees the `depth` latest frames and a **jump in frame
  sequence numbers** for overwritten frames — exactly what a real driver does, and what restarts the window (RFC-0012 §9.9) — not
  old frames presented as new;
* **when sequence ends, the camera is lost**: delivers the remaining frames it already captured, then raises `CameraUnavailable` (`loop = true`
  repeats; repeating a single frame is a frozen camera, which perception rejects).

Model labels detected within frames are separate, replayed from a script (`provider = "replay"`, `vision.md` §3.5); camera only provides frames.

```toml
[sim.vision]
source = "synthetic"      # or directory of frames, relative to agent.toml
frames = 90               # synthetic only: how many frames long is the sequence
loop   = false            # loop the sequence
depth  = 4                # queue: how many frames a late reader still sees
drop   = [7, 8]           # frame numbers camera drops (skipped frame numbers)
```

`synthetic` generates deterministic frames, matching mode dimensions, **each frame distinct**. Frame directory: each regular file is a frame, sorted
in natural order of filenames (`2` before `10`); file extensions are ignored. Missing `[sim.vision]` in an agent declaring `[vision]` ⇒ session **fails
to start** (`CameraUnavailable`): a simulation that produces frames out of thin air would make every vision agent artificially succeed.

## 5. `linux`: Dependency-free Video4Linux2 (TSK-V1b-01)

`LinuxHAL.vision_in` reads a V4L2 capture node (`/dev/videoN`) using pure Python — `ctypes` for structures, `fcntl.ioctl` for calls,
`mmap` for buffers (`hal/v4l2.py`). **No external dependencies added** (no OpenCV, GStreamer, `av`): `import neuroedge` never requires
them, and anyone needing a heavier pipeline writes it as a `VisionModel` adapter where it simply receives frame bytes. Structures follow the LP64 layout of
UAPI (`sizeof(v4l2_buffer) == 88`; `hal/v4l2.py::LAYOUT`) — valid for `linux-rpi5` (aarch64) and x86_64 runners; 32-bit userspace is rejected
(`layout_problem`), avoiding passing wrong-sized structures to the kernel.

**Node is a machine-level choice, not guessed.** A Pi has dozens of `/dev/video*` nodes, most of which are not cameras: `NEUROEDGE_LINUX_CAMERA=/dev/video0`
(or `LinuxHAL(camera=…)`). If not specified ⇒ `CameraUnavailable` explains how to specify it. Replay does not inspect hardware, so it does not open the camera.

**Protocol** (`V4L2Camera`): `QUERYCAP` (node must be capture and streaming-capable) → `S_FMT` and `S_PARM` requesting **the exact declared mode** → four `mmap`
buffers → `STREAMON`. The driver's response **MUST be that exact mode**: drivers rounding dimensions, choosing a different format, or running at a different
speed (diverging by > 2%) are rejected with a three-part error — the board declared a mode, the agent built according to it, and target parity
(RFC-0012 §3f) does not accept "approximate". A capture thread retrieves every frame as soon as ready, stamps the session clock, and keeps the 64 newest frames
for the session to retrieve via `read_available()`; frame sequence number is the driver's `sequence`, so kernel-dropped frames appear as a jump visible to perception.

**Fail-closed.** Device disappears, read error occurs, or **no frame arrives within `stall_ms` (default 1000 ms)** ⇒ `read_available()` raises
`CameraUnavailable`. Frames flagged with `V4L2_BUF_FLAG_ERROR` by driver are discarded rather than repaired; raw frames of incorrect size terminate the camera. `close()` stops the thread,
issues `STREAMOFF`, releases buffers and node; idempotent, and called by `LinuxHAL.close()`.

**Testing.** `tests/test_v4l2.py` exercises the complete protocol against a mock driver (structure sizes, ioctl counts, call sequence, mode rejection, sequence numbers,
frame errors, device death, stall, close). On a real kernel: CI job `linux-hal` loads `vivid` (`scripts/setup_vivid.sh`: kernel virtual video
driver, identical ioctls and `mmap` buffers to a real camera, timestamped test pattern so no two frames are identical) and runs
`python/tests_linux/test_camera_v4l2.py`. That file runs in the `linux-hal` job on the runner kernel (CI run 37153005998: 90 passed); it caught a bug reading `sequence` after `VIDIOC_QBUF` (`hal/v4l2.py`, `6bbfb43`). Not yet tested on physical camera hardware.

## 6. From camera to gate

For an agent with `[vision]`, `SimSession` constructs a `VisionFeed` (`sim/vision/feed.py`): camera of the chosen build mode, `VisionPipeline` from
`vision.md`, and registers the `facts(tree)` function into `Conversation.fact_sources`. Immediately **before each gate evaluation** containing visual criteria:

1. all frames delivered by the camera since the last run enter `VisionPipeline.push`, in order; a jump in frame sequence numbers restarts the window;
2. the pipeline writes a `vision_fact` for each fact the tree requires and returns readable facts;
3. any visual criterion of the tree that **cannot be read** is passed to the engine as `None` — "fact unavailable", the engine blocks with `criterion_unavailable`
   rather than querying other sources (System One would otherwise be queried, and might answer from human utterances what only the camera is authorized to assert).

Gates with no visual criteria do not run the model. Visual facts take precedence over `[sim.facts]` of the same name, so the session refuses to load if there is a conflict.
The session opens the camera **at load time**, after requesting GPIO lines: if camera fails to open (no node, driver rejects mode, no recorded sequence on `sim`)
⇒ three-part error, lines released, session does not exist — an agent requiring eyes must not start blind.

## 7. Camera loss ⇒ block (RFC-0012 §3e)

| Situation | What happens |
|:---|:---|
| Camera raises `CameraUnavailable` (missing, stalled, sequence ended, frame malformed) | `camera_unavailable {reason}` event, **window cleared**, facts unresolved (`window_size`), gate blocks with `criterion_unavailable` — does not wait for old frames to age out |
| Camera is silent but has not exceeded `stall_ms` | old frames age out: `stale` (1000 ms ceiling) or `max_age_ms` of `numeric` criterion ⇒ block |
| Identical frames despite driver attaching new timestamps | `frozen` ⇒ block (perception, `vision.md` §4.3) |
| Frame drop (frame sequence jump) | window restarts; fewer than `min_frames` ⇒ `window_size` ⇒ block |
| Insufficient frames at startup | `window_size` ⇒ block |

No branch yields ALLOW, no interpolation from previous frames, no default "no person seen" value.

## 8. Traces, privacy, corpus

* `camera_unavailable` `{reason}` (`perception` group, `vision.in`): camera failed to deliver at this evaluation. Replay ignores it — accompanying
  `criterion_unavailable` verdict is recomputed from unresolved `vision_fact`.
* Traces carry **`vision_ref` (hash + size) and labels**, never pixels; `metadata.raw_capture` is enabled only deliberately (`vision.md` §1.3).
* **Corpus** (RFC-0013 §3f item 7): `fixtures/traces/vision/*.json` — three sessions of sample agent `fixtures/agents/gate-watch` on `sim-rpi5` (allow,
  block, camera lost), generated by `scripts/gen_vision_traces.py` (`--check` is what tests run). `neuroedge verify` replays them across **all** reference
  boards declaring `vision.in` (`sim/sim-rpi5`, `linux/linux-rpi5`), from recorded labels, without camera or model; undeclared boards (`sim-default`)
  skip rather than fail, as this is not a canonical trace. Replay across both targets must produce identical verdicts and pin commands.

## 9. Not yet implemented

* Golden inference per model sha256 and cross-target error `tolerance` check (TSK-V1b-04) — the "models see the same" proposition of RFC-0012 §3f.
* `mjpeg` decoding: camera delivers raw compressed bytes; model adapter decodes if needed.
* Camera on `esp32s3` (TSK-I3a-04): no HAL; device replay only executes canonical traces.
* Multiple cameras per session, multi-planar (`V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE`), CSI via libcamera: node must be single-planar capture.
