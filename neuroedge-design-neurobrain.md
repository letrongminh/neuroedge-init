# NeuroEdge — Ghi chú thiết kế NeuroBrain (Giai đoạn 1.5)

## NeuroBrain: bring-up phần cứng có hợp đồng

> **Ghi chú thiết kế.** Tệp này giữ định vị, nguyên tắc, ranh giới với tầng an toàn và
> thiết kế từng khối N0–N7. Nó **không** có lịch, trạng thái, tiêu chí ra hay thang cắt:
> task, tiêu chí ra, phụ thuộc và thang cắt chỉ nằm ở [`neuroedge-roadmap.md`](neuroedge-roadmap.md)
> increment **I12** (§7.2; thang cắt §9.3). Quyết định chỉ nằm ở `neuroedge-prd.md` §15:
> **Q-31** (tên và định vị), **Q-40** (NeuroBrain sau Developer Beta). Quyết định còn chờ mã
> `Q-N`: Phụ lục B.

**Cập nhật:** 2026-09-25 · lịch sử thay đổi: `CHANGELOG.md`

**Tài liệu nguồn:**
- `neuroedge-prd.md` §1.5 (P-1), §15 (Q-24, Q-26, Q-27, Q-11, Q-21)
- `neuroedge-proposal.md` Phụ lục B (B.4 ngân sách, B.5 kế thừa, B.6 `arguments`)
- `docs/spec/threat_model.md`, `docs/spec/simulation_coverage.md`
- `docs/rfc/0005-rang-buoc-tham-so-trong-gate.md`, `docs/rfc/0006-xac-nhan-ask-confirms.md`

**Phạm vi:** Khối N0 · N1 · N2 · N3 · N4 · N5 · N5b · N6 · N7

**Ngoài phạm vi:**
- Tool MCP điều khiển chân thô, không qua gate.
- Blacklist chân.
- Runtime Lua kiểu ESP-Claw.
- MCP qua mạng (xem `TODOS.md` #24).
- Kênh IM (Telegram, Zalo).
- Sinh ràng buộc gate từ datasheet.

---

## Mục lục

1. [Định vị và nguyên tắc](#1-định-vị-và-nguyên-tắc)
2. [Ranh giới với tầng an toàn](#2-ranh-giới-với-tầng-an-toàn)
3. [Giả định nguồn lực](#3-giả-định-nguồn-lực)
4. [Đường găng và phụ thuộc](#4-đường-găng-và-phụ-thuộc)
5. [Khối N0 — Quản trị](#5-khối-n0--quản-trị)
6. [Khối N1 — Gated claw lõi](#6-khối-n1--gated-claw-lõi)
7. [Khối N2 — Phong bì an toàn vật lý](#7-khối-n2--phong-bì-an-toàn-vật-lý)
8. [Khối N3 — Bus I2C chỉ đọc](#8-khối-n3--bus-i2c-chỉ-đọc)
9. [Khối N4 — Sổ bàn làm việc](#9-khối-n4--sổ-bàn-làm-việc)
10. [Khối N5 — Chat Contracting](#10-khối-n5--chat-contracting)
11. [Khối N5b — Lab Monitor](#11-khối-n5b--lab-monitor)
12. [Khối N6 — Trigger theo sự kiện](#12-khối-n6--trigger-theo-sự-kiện)
13. [Khối N7 — NeuroBrain trên ESP32-S3](#13-khối-n7--neurobrain-trên-esp32-s3)
14. [Cổng nhu cầu và cột mốc](#14-cổng-nhu-cầu-và-cột-mốc)
15. [Rủi ro và giảm thiểu](#15-rủi-ro-và-giảm-thiểu)
16. [Cắt phạm vi](#16-cắt-phạm-vi)

**Phụ lục**
- [A — Tái dùng có chọn lọc từ ESP-Claw](#phụ-lục-a--tái-dùng-có-chọn-lọc-từ-esp-claw)
- [B — Quyết định chờ cấp mã `Q-N`](#phụ-lục-b--quyết-định-chờ-cấp-mã-q-n)

---

## Quy ước tài liệu

Mọi mã và ký hiệu (`TSK-N*`, `N0`–`N7`, `§x.y`…) được giải mã ở
**[`docs/user/thuat-ngu.md`](docs/user/thuat-ngu.md)**.

---

## 1. Định vị và nguyên tắc

### Định vị (đã chốt — Q-31, 2026-09-25)

> **NeuroBrain — Build Physical AI by conversation, under contract.**
> *Dựng Physical AI bằng hội thoại — có hợp đồng: quét bus, sinh mã, chứng minh an toàn trong CI rồi mới cho chạy trên bo mạch. Không C, không hàn.*

*"Copilot" đã bỏ (họ nhãn Microsoft/GitHub; va chạm: navigate.ai, Bench Copilot).*

**NeuroBrain là "ESP-Claw có hợp đồng".**

- [ESP-Claw](https://github.com/espressif/esp-claw) làm theo chuỗi: nói chuyện → LLM viết Lua → Lua chạy ngay trên chip.
- NeuroBrain làm theo chuỗi:
  1. Nói chuyện.
  2. LLM đề xuất một **hợp đồng**: `@action` + gate + test replay.
  3. Action CI chứng minh hợp đồng.
  4. Người duyệt.
  5. Cùng một gate chạy y hệt trên `sim`, `linux` rồi chip.

Tên gọi là *Chat Contracting*, không phải *Chat Coding*.

**Khác biệt với ESP-Claw.** Riêng phần "LLM chọc GPIO qua MCP" thì chính Espressif đã phát hành miễn phí ([esp-gpio-tool](https://github.com/espressif/esp-gpio-tool), `cap_mcp_server` của ESP-Claw). NeuroBrain không cạnh tranh ở phần đó. Khác biệt nằm ở hai chỗ:
- mọi thao tác vật lý đều có gate, trace và fail-closed;
- mọi hành vi sinh ra đều thành gate có phiên bản, có test hồi quy.

### Bảy nguyên tắc

| # | Nguyên tắc | Hệ quả |
|:---:|:---|:---|
| 1 | **Không tool chân thô** | Đường duy nhất tới chân là `dispatch()` → `c.do()` → gate → token → HAL (P-1, Q-24) |
| 2 | **B-1: `brain/` không gọi HAL** | Gói `python/neuroedge/brain/` chỉ đi qua `dispatch()`. Có một test quét AST và import để canh |
| 3 | **Allow-list, không blacklist** | Chân không khai trong profile board thì bị từ chối (`BoardProfile.require_pin`) |
| 4 | **Gate thuần** | Trạng thái tích luỹ (phong bì) nằm ở HAL/runtime; gate không đọc đồng hồ. `gate.v1` không đổi |
| 5 | **LLM không tự khoá chính sách** | Mọi thứ sinh ra đều là bản nháp (`0.1.0-draft`), phải qua `gate lint`, PR và người duyệt |
| 6 | **`sim` không mạnh hơn bo tham chiếu** | Không tự viết emulator (Q-16, Q-21). Dữ liệu bus trên `sim` chỉ phát lại từ trace |
| 7 | **Quản trị trước, mã sau** | Mục `Q-N`, threat model và RFC đi trước mã của khối tương ứng |

---

## 2. Ranh giới với tầng an toàn

### 2.1 Ba thứ Giai đoạn 1.5 không được đụng

| Thứ | Vì sao |
|:---|:---|
| `schemas/gate.v1.json` | Phong bì khai ở `board.v1`, không ở gate. Gate giữ tính thuần (bất biến #4) |
| Ngữ nghĩa phân giải gate (`gate_resolver.py`, `constraints.py`) | Gate lab là gate thường; không có luật kế thừa mới |
| Gate đã khoá trong `digests.lock` | Gate nháp không vào `digests.lock` cho tới khi được duyệt. Sửa gate đã khoá vẫn cần RFC (CONTRIBUTING §3) |

### 2.2 Xác nhận của con người

- Q-26: `mcp` và `system_two` không xác nhận được `ask`. Nguồn `trigger` mới cũng không.
- Người đứng cạnh bo xác nhận qua `POST /confirm` của trang sim (same-origin).
- Không có kênh thiết bị thì lab gate dùng `deny`, không dùng `ask`.

### 2.3 Giới hạn phần mềm khi tắt

Libgpiod thả line khi tiến trình thoát, và *"it should not be assumed that a line will retain its state"* ([gpioset](https://libgpiod.readthedocs.io/en/latest/gpioset.html)).

| Kiểu tắt | Có đưa chân về mức an toàn? |
|:---|:---|
| Thoát bình thường, SIGINT, SIGTERM | **Có**, qua `hal.close()` (TSK-N2-03) |
| Crash, SIGKILL | **Không bảo đảm được bằng phần mềm.** README lab bắt buộc ghi rõ cần điện trở kéo xuống hoặc watchdog phần cứng |

---

## 3. Giả định nguồn lực

→ Người và điều kiện vào của I12: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) §1.1 và §7.2.

---

## 4. Đường găng và phụ thuộc

→ Phụ thuộc của I12 và của từng task: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) §0.2 và §7.2.

---

## 5. Khối N0 — Quản trị

Chỉ có tài liệu, không có mã (nguyên tắc 7, §1).

→ Task và tiêu chí ra: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) I12 (§7.2), Khối N0.

---

## 6. Khối N1 — Gated claw lõi

`lab_pulse` chạy trên `sim`. `lab_read` cần primitive `digital.in` của RFC-0007. Lab qua MCP trên bo `linux` thật cần phiên tương tác `linux` (TSK-S5-10).

**`call_source` của lab action:**
- **Nhận:** `mcp`, `test`, cùng các nguồn người là `local_grammar` và `ui`.
- **Từ chối:** `trigger` và `system_two`. Lab là dụng cụ bàn thí nghiệm, không phải hành vi tự động.

→ Task và tiêu chí ra: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) I12 (§7.2), Khối N1.

---

## 7. Khối N2 — Phong bì an toàn vật lý

Phong bì gồm giới hạn tổng thời gian bật và tần suất theo chân, khai ở `board.v1` (RFC-0007).

→ Hook phong bì và thứ tự kiểm (TSK-N2-01), chính sách check-và-reserve nguyên tử (TSK-N2-02), móc tắt an toàn (TSK-N2-03) và tiêu chí ra: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) I12 (§7.2), Khối N2.

### 7.1 Hợp đồng hồi quy

1. Không cấu hình phong bì ⇒ `digital_out` y hệt cũ: cùng thứ tự lỗi, sai chân không tiêu token.
2. Corpus `fixtures/tool_calls/` cho cùng kết quả.
3. Mọi profile trong `boards/` hợp lệ với `board.v1` có trường mới.
4. `verify` giữ nguyên chuỗi phán quyết của ba trace chuẩn mực.
5. `mcp serve` khi thoát vẫn ghi trace, và có gọi `hal.close()`.

---

## 8. Khối N3 — Bus I2C chỉ đọc

N3 dựng trên `sensor.read` qua `i2c-stub` của TSK-S5-09.

**ADC có điều kiện.**
- Runner tắt `CONFIG_IIO` (`docs/spec/simulation_coverage.md`), nên `iio_dummy` và `ti-ads1015` bị loại.
- **Spike đạt:** ADC nằm trong N3.
- **Spike không đạt:** ADC vào `TODOS.md`, mốc kích hoạt là khi có runner tự host gắn ADC thật.
- `sim` chỉ phát lại giá trị đã ghi, không có quét I2C thật.

→ Quét bus (TSK-N3-01), test trên `i2c-stub` (TSK-N3-02), spike ADC (TSK-N3-03) và tiêu chí ra: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) I12 (§7.2), Khối N3.

---

## 9. Khối N4 — Sổ bàn làm việc

Nếu profile mới cần qua `test_boards.py`, nó phụ thuộc RFC-0002.

→ Sổ sự thật (TSK-N4-01), profile board nháp (TSK-N4-02), cảnh báo chân đặc biệt (TSK-N4-03): [`neuroedge-roadmap.md`](neuroedge-roadmap.md) I12 (§7.2), Khối N4.

---

## 10. Khối N5 — Chat Contracting

`extends` từ chối version pre-release, nên không gate nào extends được một bản nháp. Đây là hành vi mong muốn.

→ Task: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) I12 (§7.2), Khối N5.

---

## 11. Khối N5b — Lab Monitor

Là một panel trong trang sim hiện có (`python/neuroedge/viz/assets/ui.js`, `ui.css`), **không có tab riêng**. Panel chỉ hiện khi `[lab] enabled`. Wireframe tham chiếu: [`wireframe/lab-monitor-v2.html`](wireframe/lab-monitor-v2.html).

**Thứ bậc:**
- Cột phải: thẻ xác nhận → hàng "đang bật" → timeline xung → phán quyết.
- Cột trái: thiết bị → bus I2C.
- Header: huy hiệu LAB MODE.

→ Task và tiêu chí ra: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) I12 (§7.2), Khối N5b.

---

## 12. Khối N6 — Trigger theo sự kiện

Luật "khi X thì Y" là **cấu hình agent**, không phải mở rộng gate. Mỗi trigger gọi một `@action` có gate.

→ Task: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) I12 (§7.2), Khối N6.

---

## 13. Khối N7 — NeuroBrain trên ESP32-S3

N7 đưa lab action, gate và phong bì của N1–N6 xuống chip, nên cần bo Box-3 và HAL `esp32s3`.

→ Task: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) I12 (§7.2), Khối N7.

---

## 14. Cổng nhu cầu và cột mốc

→ Q-40 bỏ luật cổng nhu cầu riêng của NeuroBrain. Tín hiệu đo của I12: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) §7.2.

---

## 15. Rủi ro và giảm thiểu

| # | Rủi ro | Mức độ | Dấu hiệu sớm | Phương án ứng phó |
|:---:|:---|:---:|:---|:---|
| **1** | NeuroBrain kéo người khỏi đường găng v1.0 | Cao | Việc của v1.0 bị gán cho N0/N1 | Q-40 xếp I12 sau Developer Beta; không increment nào trước I12 phụ thuộc NeuroBrain |
| **2** | LLM sinh gate nới lỏng hơn ý người nói | Cao | Bản nháp chỉ có test ALLOW | Test hai chiều (TSK-N5-02), `gate explain` trong PR (TSK-N5-04), người duyệt (TSK-N0-05) |
| **3** | Chân kẹt HIGH khi tiến trình chết | Trung bình | Relay nóng hoặc kêu sau crash | §2.3: phần mềm không cứu được. README lab và runbook bắt buộc ghi rõ cần điện trở kéo xuống |
| **4** | Lab lọt vào bản phát hành | Trung bình | Báo cáo build ghi `lab_enabled: true` | Cờ mặc định tắt, `build --release` chặn (TSK-N1-03) |
| **5** | Không có thêm người cho I12 | Cao | Chưa có ứng viên khi I12 sắp mở | Điều kiện vào của I12 (`neuroedge-roadmap.md` §7.2): chưa có người thì I12 chưa mở |
| **6** | RFC-0007 hoặc mở rộng Q-11 bị bác | Trung bình | Phản biện tập trung vào primitive mới | `lab_read`/N3 dừng, `lab_pulse` không bị ảnh hưởng. Restyle giữ font hệ thống, chỉ bỏ viền trái |

---

## 16. Cắt phạm vi

→ Thang cắt của I12 và phần tuyệt đối không cắt: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) §9.3.

---

# Phụ lục

## Phụ lục A — Tái dùng có chọn lọc từ ESP-Claw

Nguồn: [espressif/esp-claw](https://github.com/espressif/esp-claw), Apache-2.0 (nằm trong allowlist Q-11). Theo khuôn XiaoZhi (`NOTICE` Section A mục 1):
- clone **ngoài kho** để đọc, ghim commit;
- mỗi tệp port ghi tệp và commit gốc ở đầu tệp (CONTRIBUTING §4).

| Lấy | Dùng cho |
|:---|:---|
| `application/edge_agent/boards/*/board_peripherals.yaml` (có `esp_box_3`) | Dữ liệu "chân đã bị ngoại vi chiếm" cho TSK-N4-03 |
| Lớp ESP-IDF bên dưới binding Lua của `lua_driver_{i2c,adc,gpio}` | N3/N7 firmware |
| `components/claw_modules/claw_event_router` | Tham khảo thiết kế N6/N7 |

**Không lấy:**
- `cap_lua`, `lua_module_*`: Lua tự do phá P-1.
- `claw_core`, `cap_im_*`, `cap_web_search`.
- MCP HTTP + mDNS của `cap_mcp_server` trước khi có `TODOS.md` #24 (NFR-SEC-09 chỉ cho stdio).

## Phụ lục B — Quyết định chờ cấp mã `Q-N`

Các quyết định dưới đây chốt ở ba vòng review ngày 2026-09-24. TSK-N0-01 chuyển chúng vào `neuroedge-prd.md` §15. Sau đó mục này chỉ còn dẫn mã.

| # | Quyết định |
|:---:|:---|
| 1 | Xây NeuroBrain kiểu ESP-Claw nhưng secure by design; không tool chân thô |
| 2 | *Đã thay:* thời điểm và thứ tự của NeuroBrain là Q-40 (sau Developer Beta, increment I12) |
| 3 | Phạm vi N0–N7 như tệp này; N7 làm cuối |
| 4 | Gói `brain/` với bất biến B-1; phong bì là hook trong HAL, kiểm trước `authorize` |
| 5 | Thêm `digital.in` vào RFC-0007 cùng bus I2C; ADC có điều kiện theo spike |
| 6 | Cờ `[lab] enabled` mặc định tắt; `build --release` chặn |
| 7 | Lab qua MCP trên `linux` thật dùng phiên tương tác `linux` của TSK-S5-10 |
| 8 | Port chọn lọc từ ESP-Claw theo Phụ lục A |
| 9 | Restyle trang sim với IBM Plex; mở rộng Q-11 cho OFL-1.1, chỉ với font |
| 10 | *Đã bỏ:* luật cổng nhu cầu riêng của NeuroBrain (Q-40); người cho I12: `neuroedge-roadmap.md` §1.1 |
