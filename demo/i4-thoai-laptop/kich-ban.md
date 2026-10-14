# Demo script — speaking to agent via laptop microphone (I4, TSK-I4-04)

> **Last re-run:** 2026-09-29, macOS (Apple Silicon), branch `voice/integration`.
> The real provider path (STT, TTS, System 2 via OpenRouter) has run end-to-end using `--voice-file` with exact configuration
> in `voice.toml`. Outputs in scenes 1–2 are taken from that run. **Live microphone sessions have not yet been re-run on the presenter's machine**:
> run test per section 0 before demo session (macOS requires microphone permissions for terminal).
> **Duration:** 4–5 minutes. No hardware needed beyond laptop and headphones.

---

## 0. Preparation

```bash
# from repo root
bash demo/i4-thoai-laptop/chuan-bi.sh          # install extra cloud + audio, create agent 'nha' at /tmp/neuroedge-demo-voice
export OPENROUTER_API_KEY=…                    # single key for STT, TTS, System 2, and Jev
alias ne="$PWD/python/.venv/bin/neuroedge"
cd /tmp/neuroedge-demo-voice/nha
ne run --mic                                   # test 1 utterance, then Ctrl-C
```

- **Wear headphones.** Laptop lacks echo cancellation: through external speakers, agent hears itself and self-"barges in". If external
  speakers are mandatory, run `--half-duplex` (scene 4) — in which case barge-in is disabled (Q-50).
- **Microphone permissions:** first time macOS prompts for microphone access for terminal application. Without permission, `run --mic` hangs
  at opening microphone — grant permission under *System Settings → Privacy & Security → Microphone* then re-run.
- Banner prints active microphone and speaker names. Select different devices with `NEUROEDGE_AUDIO_IN` / `NEUROEDGE_AUDIO_OUT`.
- What not to say: table in [`docs/business/cong-nhu-cau-2026-10-25/demo.md`](../../docs/business/cong-nhu-cau-2026-10-25/demo.md) §0.1
  and [`CHANGELOG.md`](../../CHANGELOG.md) §3.7 — voice is currently available on laptop only, **not yet on Pi or ESP32-S3 chips** (I5).

---

> **With UI:** run `ne studio --mic` (instead of `ne run --mic`) to display the same session on web: listening/thinking/speaking
> states, recognized utterances, verdicts, and latency per stage (`demo/i1-studio/`, Q-51). Microphone button on page only mutes/unmutes
> microphone.

## 1. Scene 1 — "Speak an utterance, light turns on through gate"

### Say
"I speak into the laptop microphone. Speech turns into text at the speech recognition service, then travels the exact path of a
typed command: command grammar, then gate. The model only hears — the decider is the gate."

### Type
```bash
ne run --mic
# speak: "Bật đèn."
```

### See
```text
nha@0.1.0 on sim (sim-default) · live audio
  mic (input): MacBook Air Microphone
  stt: openai/whisper-large-v3-turbo at https://openrouter.ai/api/v1 (key from $OPENROUTER_API_KEY)
  tts: google/gemini-3.1-flash-tts-preview, voice Kore at https://openrouter.ai/api/v1 (key from …
turn 1 · … s · heard: “Bật đen.”
intent light_on (0.86)
  tool_call light_on() · local_grammar
✓ ALLOW light_on@1.0.0 → light_on()
```

### Highlights
STT misheard tone mark ("Bật đen.") yet grammar still matched `light_on` with 0.86 confidence. A misheard utterance never
reaches pins on its own: it must match grammar, then pass the gate.

---

## 2. Scene 2 — "Ask a question, agent answers with voice"

### Say
"Questions that are not control commands are answered by System 2, based on the home's knowledge base. The answer is
read through headphones."

### Type
```text
speak: "Mật khẩu wifi nhà mình là gì?"
```

### See
```text
turn 1 · … s · heard: “Mật khẩu wifi nhà mình là gì?”
intent knowledge (0.81)
  says (knowledge_rag): Mật khẩu wifi được dán ở mặt dưới router.
```

### Highlights
Measured 2026-09-29: STT ~1.9 s, Gemini TTS ~3.7 s before audio starts (`ne trace show` prints latency
per stage). Changing `model` in `[tts]` to `google/gemini-3.8-flash-tts` reduces to ~2.6 s — a single configuration line,
no code changes.

---

## 3. Scene 3 — "Barge-in" (headphones only)

### Say
"When the agent is speaking and I interrupt, the speaker stops immediately, and any command not yet dispatched to devices is cancelled."

### Type
```text
speak: "Mật khẩu wifi nhà mình là gì?"  →  when agent begins reading, barge in: "Thôi."
```

### See
Agent voice cuts off mid-sentence. At session end, summary line prints barge-in count: `voice: … · 1 barge-in · …`
*(verify when running — not yet tested with live microphone)*.

### Highlights
Command revocation rule follows the identical chip specification (`docs/spec/voice_fsm.md` §5.2): speaker silences under 300 ms after human
speaks, undispatched commands are cancelled, already-dispatched commands (active door pulse) run to completion.

---

## 4. Scene 4 — "External speakers: `--half-duplex`"

### Say
"Without headphones, microphone mutes while agent speaks, preventing agent from hearing itself. Tradeoff: barge-in is disabled."

### Type
```bash
ne run --mic --half-duplex
```

### See
```text
  half-duplex: on (mutes the mic while the agent speaks, no barge-in)
```

### Highlights
This is a laptop limitation, not a product limitation: real devices cancel echo via hardware (Box-3) or
PipeWire (Pi) — `TODOS.md` #45, Q-22.

---

## 5. Scene 5 (optional) — "Review session"

```bash
ne run --mic --trace-out ../phien.json     # speak a few utterances, Ctrl-C
ne trace show ../phien.json                # stt_result, gate, tts_stream_end, turn_latency per stage
```

Spoken user text is hashed in the trace (`"text": "sha256:…"`, TSK-I1-01); `--raw` preserves verbatim text.

---

## 6. Wake word (internal testing, not for public videos)

`voice.toml` includes a commented-out `[wake_word]` block. Pretrained openWakeWord models (e.g. `hey_jarvis`)
are licensed under CC BY-NC-SA 4.0: internal testing only, do not commit, do not record in public videos (Q-50). Requires
`pip install 'neuroedge[wake]'` and three self-downloaded files (word model, `melspectrogram.onnx`, `embedding_model.onnx`).
With `[wake_word]`, a turn only opens upon hearing the exact keyword. Production-ready models: `TODOS.md` #49.
