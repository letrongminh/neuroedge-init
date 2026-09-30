# Kịch bản demo — nói với agent qua micro laptop (I4, TSK-I4-04)

> **Chạy lại lần cuối:** 2026-09-29, macOS (Apple Silicon), nhánh `voice/integration`.
> Đường provider thật (STT, TTS, System 2 qua OpenRouter) đã chạy đầu-cuối bằng `--voice-file` với đúng cấu hình
> `voice.toml`. Đầu ra ở các màn 1–2 lấy từ lượt chạy đó. **Phiên micro thật chưa được chạy lại trên máy trình
> bày**: chạy thử theo mục 0 trước buổi demo (macOS cần cấp quyền micro cho terminal).
> **Thời lượng:** 4–5 phút. Không cần phần cứng ngoài laptop và tai nghe.

---

## 0. Chuẩn bị

```bash
# từ gốc kho
bash demo/i4-thoai-laptop/chuan-bi.sh          # cài extra cloud + audio, tạo agent 'nha' ở /tmp/neuroedge-demo-voice
export OPENROUTER_API_KEY=…                    # một key cho STT, TTS, System 2 và Jev
alias ne="$PWD/python/.venv/bin/neuroedge"
cd /tmp/neuroedge-demo-voice/nha
ne run --mic                                   # thử 1 câu, rồi Ctrl-C
```

- **Đeo tai nghe.** Laptop không khử vang: qua loa ngoài, agent nghe lại chính nó và tự "cắt lời". Buộc
  phải dùng loa ngoài thì chạy `--half-duplex` (màn 4) — khi đó không cắt lời được (Q-50).
- **Quyền micro:** lần đầu macOS hỏi quyền micro cho ứng dụng terminal. Chưa cấp quyền thì `run --mic` đứng
  ở bước mở micro — cấp quyền trong *System Settings → Privacy & Security → Microphone* rồi chạy lại.
- Banner in tên micro và loa đang dùng. Chọn thiết bị khác: `NEUROEDGE_AUDIO_IN` / `NEUROEDGE_AUDIO_OUT`.
- Không được nói: bảng ở [`docs/business/cong-nhu-cau-2026-10-25/demo.md`](../../docs/business/cong-nhu-cau-2026-10-25/demo.md) §0.1
  và [`CHANGELOG.md`](../../CHANGELOG.md) §3.7 — thoại mới có trên laptop, **chưa trên Pi hay chip ESP32-S3** (I5).

---

> **Có giao diện:** chạy `ne studio --mic` (thay cho `ne run --mic`) để cùng phiên hiện trên trang: trạng thái
> nghe/nghĩ/nói, câu nghe được, phán quyết và độ trễ từng chặng (`demo/i1-studio/`, Q-51). Nút micro trên trang chỉ tắt/mở
> tiếng micro.

## 1. Màn 1 — "Nói một câu, đèn bật qua gate"

### Nói
"Tôi nói vào micro laptop. Lời nói thành chữ ở dịch vụ nhận dạng giọng nói, rồi đi đúng con đường của một
lệnh gõ: ngữ pháp lệnh, rồi gate. Model chỉ nghe — người quyết là gate."

### Gõ
```bash
ne run --mic
# nói: "Bật đèn."
```

### Thấy
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

### Điểm nhấn
STT nghe sai dấu ("Bật đen.") mà ngữ pháp vẫn khớp `light_on` ở độ tin 0,86. Một câu nghe sai không bao giờ
tự đi tới chân: nó phải khớp ngữ pháp, rồi qua gate.

---

## 2. Màn 2 — "Hỏi một câu, agent trả lời bằng giọng"

### Nói
"Câu hỏi không phải lệnh điều khiển thì System 2 trả lời, dựa trên kho kiến thức của nhà. Câu trả lời được
đọc qua tai nghe."

### Gõ
```text
nói: "Mật khẩu wifi nhà mình là gì?"
```

### Thấy
```text
turn 1 · … s · heard: “Mật khẩu wifi nhà mình là gì?”
intent knowledge (0.81)
  says (knowledge_rag): Mật khẩu wifi được dán ở mặt dưới router.
```

### Điểm nhấn
Đo ngày 2026-09-29: STT khoảng 1,9 s, TTS Gemini khoảng 3,7 s trước khi có tiếng (`ne trace show` in độ trễ
từng chặng). Đổi `model` trong `[tts]` sang `google/gemini-3.8-flash-tts` rút còn khoảng 2,6 s — một dòng cấu
hình, không đổi mã.

---

## 3. Màn 3 — "Cắt lời" (chỉ với tai nghe)

### Nói
"Khi agent đang nói mà tôi nói chen, loa dừng ngay, và mọi lệnh chưa kịp giao tới thiết bị bị huỷ."

### Gõ
```text
nói: "Mật khẩu wifi nhà mình là gì?"  →  khi agent bắt đầu đọc, nói chen: "Thôi."
```

### Thấy
Giọng agent tắt giữa câu. Cuối phiên, dòng tổng in số lần cắt lời: `voice: … · 1 barge-in · …`
*(kiểm lại khi chạy — chưa chạy bằng micro thật)*.

### Điểm nhấn
Luật thu hồi lệnh là cùng một đặc tả với chip (`docs/spec/voice_fsm.md` §5.2): loa im dưới 300 ms sau khi người
nói, lệnh chưa giao bị huỷ, lệnh đã giao (xung chốt cửa đang chạy) chạy hết.

---

## 4. Màn 4 — "Loa ngoài: `--half-duplex`"

### Nói
"Không có tai nghe thì micro tắt trong lúc agent nói, để agent không tự nghe chính mình. Đổi lại: không cắt lời được."

### Gõ
```bash
ne run --mic --half-duplex
```

### Thấy
```text
  half-duplex: bật (tắt micro khi agent đang nói, không cắt lời được)
```

### Điểm nhấn
Đây là giới hạn của laptop, không phải của sản phẩm: thiết bị thật khử vang bằng phần cứng (Box-3) hoặc
PipeWire (Pi) — `TODOS.md` #45, Q-22.

---

## 5. Màn 5 (tuỳ chọn) — "Xem lại phiên"

```bash
ne run --mic --trace-out ../phien.json     # nói vài câu, Ctrl-C
ne trace show ../phien.json                # stt_result, gate, tts_stream_end, turn_latency từng chặng
```

Chữ người nói được băm trong vết ghi (`"text": "sha256:…"`, TSK-I1-01); `--raw` giữ nguyên văn.

---

## 6. Từ đánh thức (thử nội bộ, không đưa vào video công khai)

`voice.toml` có sẵn một khối `[wake_word]` đã comment. Mô hình dựng sẵn của openWakeWord (ví dụ `hey_jarvis`)
theo CC BY-NC-SA 4.0: chỉ dùng thử nội bộ, không commit, không quay video công khai (Q-50). Cần
`pip install 'neuroedge[wake]'` và ba tệp bạn tự tải (mô hình từ, `melspectrogram.onnx`, `embedding_model.onnx`).
Có `[wake_word]` thì một lượt chỉ mở khi nghe đúng từ khoá. Mô hình dùng được cho sản phẩm: `TODOS.md` #49.
