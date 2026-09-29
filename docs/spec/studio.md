# `neuroedge studio` — ứng dụng web cục bộ cho mọi năng lực trên laptop

**Trạng thái:** đặc tả cho TSK-I1-04 (Q-51). Bố cục đã duyệt: [`wireframe/studio-v1.html`](../../wireframe/studio-v1.html).
Đây là **hợp đồng** giữa server (`python/neuroedge/studio/`) và trang (`python/neuroedge/studio/assets/`): đường dẫn,
hình dạng JSON, luật an toàn. Mã đổi hợp đồng thì sửa tệp này trong cùng PR.

## 1. Lệnh

```bash
neuroedge studio [--agent agent.toml] [--port 8765] [--no-browser] [--mic [--half-duplex]]
```

- Chỉ target `sim` (trang hiện thiết bị ảo). Mặc định agent như `run`.
- `--mic`: phiên nghe micro laptop ngay từ đầu (TSK-I4-04, Q-50); nút micro trên trang chỉ **tắt/mở tiếng** micro
  (thay khung bằng im lặng), không mở/đóng thiết bị. Không `--mic` thì màn thoại chỉ cách bật.
- Ctrl-C ⇒ mã 0, đóng micro/loa.

## 2. Luật không thương lượng

1. **Chỉ 127.0.0.1.** Không bao giờ bind địa chỉ khác.
2. **Mọi POST cùng nguồn** (`SessionServer._same_origin`), thân ≤ 4096 byte (trừ khi mục dưới ghi khác).
3. **Không tài nguyên ngoài:** CSS/JS nhúng trong trang; không CDN, không font web, không `url(`, không `@import`.
   Ảnh chỉ từ đường dẫn cùng nguồn (`/api/device/golden/…`).
4. **Chữ từ agent, vết ghi, model luôn gán bằng `textContent`**, không bao giờ `innerHTML`.
5. **Không bao giờ trả giá trị key.** Provider chỉ có `key_env` (tên biến) và `key_present` (bool).
6. **Đọc hệ thống tệp chỉ trong thư mục của agent** (vết ghi, build) và, khi chạy trong một bản checkout của kho,
   các đầu ra đã có của `demo/i3-firmware-qemu/run.sh`. Tên tệp từ URL qua danh sách trắng, không `..`.
7. **Hai ngôn ngữ:** mọi nhãn của trang ở `I18N.vi` và `I18N.en`; thuật ngữ sản phẩm giữ nguyên (gate, ALLOW, BLOCK,
   MCP, System 1/2, OTA, trace). Server trả dữ liệu, không trả nhãn.
8. Lỗi của một API là JSON `{"ok": false, "error": {"code"?, "where"?, "why", "how"?}}` (dạng `NeuroEdgeError.as_dict()`),
   HTTP 200 cho lỗi nghiệp vụ, 400 cho yêu cầu sai dạng, 404 cho đường dẫn lạ, 501 cho API chưa hiện thực.

## 3. Đường dẫn giữ nguyên từ trang sim

`GET /events` (SSE), `GET /state`, `POST /command`, `POST /confirm` — y hệt `python/neuroedge/sim/ui.py`.
`GET /` trả trang studio (không phải trang sim).

## 4. API mới

Mọi câu trả lời thành công có `"ok": true`.

| Phương thức, đường dẫn | Trả về | Module |
|:---|:---|:---|
| `GET /api/agent` | `{label, root, requires: {primitive: {...}}, targets: [..], board: {id, capabilities}, providers: [{role, label, key_env, key_present}], templates: [..]}` — `role` ∈ `stt`, `stt.fallback`, `tts`, `system_one`, `system_two`, `wake_word` | `api_agent` |
| `GET /api/gates` | `{gates: [{name, version, ref, digest, levels, fail, status: "OK"\|"FAIL", error?}], lint: {resolved, total}}` — các gate trong `[gates]` của agent | `api_agent` |
| `GET /api/gates/<name>` | `{name, version, chain: ["base@1.0.0", …], evaluate: {criterion: {type, levels?, options?, instructions?}}, allow_when: {...}, on_block: {...}, budget: {...}, explanation: {...}}` — `explanation` từ `engine/gate_explain.py` | `api_agent` |
| `POST /api/gates/<name>/whatif` body `{"facts": {criterion: value}}` | `{verdict: "ALLOW"\|"BLOCK", reason?, failed_criterion?, evaluations, action?}` — lượng giá thuần, **không** đụng phiên, HAL, ledger | `api_agent` |
| `GET /api/mcp` | `{tools: [{name, description, input_schema}], desktop_config: "<lệnh + JSON>", servers: [{name, tools}]}` | `api_agent` |
| `GET /api/traces` | `{traces: [{name, session_id, events, target, board, anonymized, recorded_at}]}` — `*.json` dưới `<agent>/traces/` (không gồm `golden/`) | `api_checks` |
| `GET /api/traces/<name>` | trace `trace.v1` đầy đủ | `api_checks` |
| `POST /api/traces/<name>/replay` | `{match: bool, verdicts: [...], pins: [...], detail?}` — như `neuroedge replay` trên `sim` | `api_checks` |
| `POST /api/record` | `{name, events}` — ghi phiên hiện tại vào `<agent>/traces/` (chữ băm, như `record`) | `api_checks` |
| `POST /api/lint` | `{resolved, total, gates: [...]}` — như `gate lint gates` trong thư mục agent | `api_checks` |
| `POST /api/verify` | `{passed: bool, summary: "<dòng Passed:/Failed:>", compared: "decisions only — not timing", matrix: [{item, sim, linux, esp32s3}]}` — `sim` chạy thật trên máy; `linux`/`esp32s3` là `{"source": "ci", "job": "linux-hal"\|"uart-trace"}` | `api_checks` |
| `POST /api/test` | `{passed, failed, output_tail}` — `neuroedge test` trong thư mục agent, tiến trình con, hạn 120 s | `api_checks` |
| `GET /api/device` | `{firmware: {built: bool, dir?, files?}, screens: [{name, langs: ["vi","en"]}], golden: {checked?: "66/66"}, qemu: {selftest?, trace_done?, log?} \| null, ota: {phases: [{phase, markers: [..], ok}]} \| null, hint}` | `api_device` |
| `POST /api/device/build` | `{built, dir, files, checked}` — như `build --target esp32s3 --board esp32s3-box-3` (sinh dự án ESP-IDF, không biên dịch) | `api_device` |
| `GET /api/device/golden/<lang>/<name>.png` | ảnh PNG (`image/png`); `lang` ∈ `vi`,`en`; `name` phải có trong `screens` | `api_device` |
| `GET /api/voice` | `{enabled, running, muted, half_duplex, state, counters: {turns, barge_in, stt_unavailable, cancelled}, devices: {input, output}, error?}` (`error`: chỉ có khi phiên tiếng nói dừng vì lỗi thiết bị, dạng ba phần) | `voice` |
| `POST /api/voice/mute` body `{"muted": bool}` | như `GET /api/voice` | `voice` |

## 5. Màn và nguồn dữ liệu

| Màn (wireframe) | Dữ liệu |
|:---|:---|
| Phiên trực tiếp | `/events` (SSE) + `/command`, `/confirm`; `/api/voice`; giải thích phán quyết dựng từ `gate_evaluation_result`, `gate_facts` và `/api/gates/<name>` |
| Gate | `/api/gates`, `/api/gates/<name>`, `/api/gates/<name>/whatif`, `/api/lint` |
| Vết ghi | `/api/traces`, `/api/traces/<name>`, `…/replay`, `/api/record` |
| Kiểm chứng | `/api/verify`, `/api/lint`, `/api/test` |
| Thiết bị ESP32-S3 | `/api/device`, `/api/device/build`, `/api/device/golden/…` |
| MCP & tích hợp | `/api/mcp` + sự kiện `tool_call` có `source: mcp` |
| Agent & cấu hình | `/api/agent` |
