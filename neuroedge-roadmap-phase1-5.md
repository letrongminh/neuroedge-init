# NeuroEdge — Roadmap Giai đoạn 1.5

## NeuroBrain: bring-up phần cứng có hợp đồng (song song Khối 1b, tới Developer Beta)

**Phiên bản:** 0.1 (bản nháp, chờ mục `Q-N` ở TSK-N0-01)

**Ngày lập:** 24 tháng 9, 2026 · lịch sử thay đổi: `CHANGELOG.md`

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

Giai đoạn 1.5 chạy **song song** Khối 1b, không thay thế nó.

> **Trạng thái quản trị.** Hướng đi và phạm vi dưới đây đã qua ba vòng review
> (CEO, eng, design) ngày 2026-09-24. Chúng **chưa** là quyết định của kho cho tới
> khi TSK-N0-01 ghi mục `Q-N` vào `neuroedge-prd.md` §15, nơi duy nhất giữ quyết
> định. Cho tới lúc đó, tệp này là kế hoạch đề xuất.

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
16. [Thang cắt phạm vi](#16-thang-cắt-phạm-vi)

**Phụ lục**
- [A — Tái dùng có chọn lọc từ ESP-Claw](#phụ-lục-a--tái-dùng-có-chọn-lọc-từ-esp-claw)
- [B — Quyết định chờ cấp mã `Q-N`](#phụ-lục-b--quyết-định-chờ-cấp-mã-q-n)

---

## Quy ước tài liệu

Mọi mã và ký hiệu (`TSK-N*`, `N0`–`N7`, `§x.y`…) được giải mã ở
**[`docs/user/thuat-ngu.md`](docs/user/thuat-ngu.md)**. Mọi mốc ghi bằng **ngày tuyệt đối**.

---

## 1. Định vị và nguyên tắc

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

- **Trước 2026-10-25:** V2 chủ trì N0 và `lab_pulse`. V2 đang nhẹ việc vì bo Box-3 chưa về (TSK-S1-10). Kỹ thuật trưởng duyệt RFC-0007 và mục `Q-N`, không tự viết. Không việc nào của M1 bị lùi.
- **Từ 2026-11-16:** cần **thêm 1 người**, hoặc tuyển V4 sớm.
- **Nếu tới 2026-11-16 vẫn chưa có người:** N2–N7 lùi sang sau Developer Beta. Khi đó ghi một mục `TODOS.md` kèm mốc kích hoạt. N1 và N5b không lùi. v1.0 và Beta không bị NeuroBrain làm trễ.
- **Nếu bo Box-3 về sớm:** TSK-S1-10 (spike bộ nhớ) xếp trước `lab_pulse`.

---

## 4. Đường găng và phụ thuộc

```
2026-10-25 trước  N0 (tài liệu) ─┬─▶ TSK-N1-01 lab_pulse trên sim ─▶ demo cổng nhu cầu
                                 │
2026-10-25        Cổng nhu cầu (§14) ─▶ ≥2: toàn bộ · 1: N0–N2 + N5b · 0: TODOS, mốc Beta
                                 │
2026-11-16        kiểm nguồn lực (§3) ─▶ RFC-0007 chấp thuận ─▶ lab_read + digital.in
Sprint 4          N2 phong bì ─▶ N5 Chat Contracting ─▶ N5b Lab Monitor
Sprint 5          TSK-S5-10 (phiên tương tác linux) ─▶ lab qua MCP trên bo linux thật
                  TSK-S5-09 (i2c-stub) ─▶ N3 bus I2C (+ ADC nếu spike đạt) ─▶ N4
Sprint 6 → Beta   N6 trigger ─▶ N7 chip (cần Box-3 + HAL Sprint 4)
```

| Phụ thuộc | Chặn | Nguồn |
|:---|:---|:---|
| **TSK-S5-10** — phiên `run --target linux` | Lab qua MCP trên bo linux thật. Hôm nay `mcp serve` chỉ chạy trên `sim` (`cli/main.py`, `_start_session` thoát mã 2 khi `target != "sim"`) | `neuroedge-roadmap.md` Sprint 5 |
| **TSK-S5-09** — `sensor.read` trên linux qua `i2c-stub` | N3 | `neuroedge-roadmap.md` Sprint 5 |
| **HAL `esp32s3` Sprint 4** + bo Box-3 (TSK-S1-10) | N7 | `neuroedge-roadmap.md` Sprint 4 |
| **RFC-0007** | `lab_read`, N2 (khai phong bì), N3 | TSK-N0-03 |
| **Q-11 mở rộng cho OFL-1.1** | Restyle trang sim với IBM Plex (TSK-N5b-07) | TSK-N0-06 |

---

## 5. Khối N0 — Quản trị

**Trước 2026-10-25. Chủ trì: V2.** Chỉ có tài liệu, không có mã.

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-N0-01** | Hai mục `Q-N`: "Lab Mode / NeuroBrain" và "Giai đoạn 1.5", chuyển các quyết định ở Phụ lục B vào PRD §15 | — | V2 | ⏳ Chưa bắt đầu | `neuroedge-prd.md` §15 |
| **TSK-N0-02** | Sửa đổi FR-HAL-01: primitive mới (`digital.in`, bus I2C) là **tuỳ chọn theo board**, như RFC-0002 làm với `vision.in`; sửa FR-CLI-10 cho `mcp desktop-config --lab` | FR-HAL-01, FR-CLI-10 | V2 | ⏳ Chưa bắt đầu | `neuroedge-prd.md` |
| **TSK-N0-03** | Nháp RFC-0007: `digital.in`; bus I2C chỉ đọc; chỗ cho ADC; trường bus/địa chỉ và khai báo phong bì trong `board.v1`. Phải lý giải vì sao không mở rộng `sensor.read`. `gate.v1` không đổi | FR-HAL-01 | V2 | ⏳ Chưa bắt đầu | `docs/rfc/0007-*.md` |
| **TSK-N0-04** | Cập nhật threat model §2b: lab action, nguồn `trigger`, `/confirm`, cờ `[lab] enabled` | NFR-SEC-09 | V2 | ⏳ Chưa bắt đầu | `docs/spec/threat_model.md` |
| **TSK-N0-05** | Quy trình duyệt gate nháp: `-draft` → PR có người review → `gate lint` sạch → bỏ hậu tố → `check_digests.py --update` | FR-GATE-* | V2 | ⏳ Chưa bắt đầu | `CONTRIBUTING.md` §3 |
| **TSK-N0-06** | Đề xuất mở rộng Q-11 cho OFL-1.1 (**chỉ với font**) và mục `NOTICE` cho IBM Plex; thêm mục `NOTICE` Section A cho ESP-Claw (Phụ lục A) | — | V2 | ⏳ Chưa bắt đầu | `neuroedge-prd.md` Q-11 · `NOTICE` |

**Tiêu chí ra Khối N0:**

- [ ] **Tiêu chí 1:** Hai mục `Q-N` có trạng thái ĐÃ CHỐT, có chữ ký kỹ thuật trưởng.
- [ ] **Tiêu chí 2:** RFC-0007 ở trạng thái thảo luận, `schemas/gate.v1.json` không đổi byte nào.
- [ ] **Tiêu chí 3:** Mọi tài liệu khác dẫn mã `Q-N`, không chép lại nội dung (CONTRIBUTING §8.1).

---

## 6. Khối N1 — Gated claw lõi

**`lab_pulse` trước 2026-10-25, trên `sim`.** `lab_read` ra sau khi RFC-0007 được chấp thuận. Lab qua MCP trên bo linux thật chờ TSK-S5-10.

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-N1-01** | `lab_pulse` là `@action` mẫu + gate `gates/lab/lab_pulse@1.0.0`, với `arguments.duration_ms ≤ 2000` (RFC-0005). Gate không có pin enum: chân giới hạn bằng allow-list của board; dự án muốn hẹp hơn thì viết gate con thu hẹp `pin` | FR-MDL-10 | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` · `gates/lab/` |
| **TSK-N1-02** | Cờ `[lab] enabled` trong `agent.toml`, mặc định **tắt**; tắt thì lab tool không được đăng ký | — | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |
| **TSK-N1-03** | `neuroedge build --release` từ chối khi `[lab] enabled`, lỗi nêu tên cờ và cách tắt; build thường ghi `lab_enabled: true` trong báo cáo | FR-CLI-02 | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/cli/main.py` · `engine/compiler.py` · `docs/release.md` |
| **TSK-N1-04** | Kết quả lab call kèm `gate explain`, để LLM tự sửa lệnh sai | FR-MDL-10 | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |
| **TSK-N1-05** | `mcp desktop-config --lab`: cấu hình Claude Desktop cho agent lab trong một bước, vẫn đúng một mục `mcpServers` | FR-CLI-10 | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/mcp_desktop.py` |
| **TSK-N1-06** | `board show --lab`: chân trong allow-list, giới hạn phong bì từng chân, lý do chân khác bị cấm | FR-HAL-05 | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/cli/main.py` |
| **TSK-N1-07** | Test ranh giới **B-1**: quét AST/import của `neuroedge.brain`, fail nếu có gọi phương thức HAL hoặc import `hal.linux` / `hal.sim` | — | V2 | ⏳ Chưa bắt đầu | `python/tests/test_brain_boundary.py` |
| **TSK-N1-08** | `lab_read` trên primitive `digital.in` (sau RFC-0007) | FR-HAL-01 | — | ⏳ Chờ RFC-0007 | `python/neuroedge/brain/` · `hal/` |

**`call_source` của lab action:**
- **Nhận:** `mcp`, `test`, cùng các nguồn người là `local_grammar` và `ui`.
- **Từ chối:** `trigger` và `system_two`. Lab là dụng cụ bàn thí nghiệm, không phải hành vi tự động.

**Tiêu chí ra Khối N1:**

- [ ] **Tiêu chí 1:** Trên `sim`, Claude Desktop gọi `lab_pulse(pin, 300)`. Có trace ALLOW và chân về 0.
- [ ] **Tiêu chí 2:** Gọi `lab_pulse(pin, 2500)` ra `argument_out_of_range`, kèm lý do `gate explain`.
- [ ] **Tiêu chí 3:** Cờ tắt thì `mcp tools` không liệt kê `lab_pulse`. `build --release` với cờ bật thoát mã khác 0.
- [ ] **Tiêu chí 4:** Test B-1 fail khi thêm thử một lệnh `hal.digital_out` vào `brain/`.
- [ ] **Tiêu chí 5:** `pytest` xanh, 0 skipped; `gate lint gates/lab/` sạch; `scripts/wheel_smoke.sh` đạt.

---

## 7. Khối N2 — Phong bì an toàn vật lý

**Từ 2026-11-16.** Phong bì gồm giới hạn tổng thời gian bật và tần suất theo chân, khai ở `board.v1` (RFC-0007).

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-N2-01** | Hook phong bì trong `HardwareAbstractionLayer.digital_out`, được tiêm vào như `authorize`. Thứ tự `require_pin → envelope → authorize → record`. Bị từ chối thì **token không bị tiêu** | FR-HAL-* | — | ⏳ Chưa bắt đầu | `python/neuroedge/hal/__init__.py` |
| **TSK-N2-02** | Chính sách phong bì trong `brain/`: check-và-reserve **nguyên tử** dưới khoá theo chân; `time.monotonic` được tiêm vào; trace ghi sự kiện `envelope_refused` | — | — | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |
| **TSK-N2-03** | Móc tắt an toàn cho `mcp serve`: `close()` gọi `hal.close()`, bắt SIGTERM, `on_no_initialize` dọn dẹp trước `os._exit` | — | — | ⏳ Chưa bắt đầu | `python/neuroedge/cli/main.py` |
| **TSK-N2-04** | Hợp đồng hồi quy — năm khẳng định (§7.1) | — | — | ⏳ Chưa bắt đầu | `python/tests/test_hal_*.py` · `test_safety_regressions.py` · `test_mcp_serve_ui.py` |
| **TSK-N2-05** | Cập nhật sơ đồ ở đầu `mcp_server.py` thêm bước phong bì | — | — | ⏳ Chưa bắt đầu | `python/neuroedge/mcp_server.py` |

### 7.1 Hợp đồng hồi quy

1. Không cấu hình phong bì ⇒ `digital_out` y hệt cũ: cùng thứ tự lỗi, sai chân không tiêu token.
2. Corpus `fixtures/tool_calls/` cho cùng kết quả.
3. Mọi profile trong `boards/` hợp lệ với `board.v1` có trường mới.
4. `verify` giữ nguyên chuỗi phán quyết của ba trace chuẩn mực.
5. `mcp serve` khi thoát vẫn ghi trace, và có gọi `hal.close()`.

**Tiêu chí ra Khối N2:**

- [ ] **Tiêu chí 1:** Hai lệnh đồng thời cùng chân, chạy cả hai thứ tự bằng điểm dừng điều khiển được, cho đúng một `envelope_refused`.
- [ ] **Tiêu chí 2:** Test SIGTERM giữa xung trên gpio-sim đưa line về 0 (sau TSK-S5-10). Phần unit của TSK-N2-03 chạy ngay.
- [ ] **Tiêu chí 3:** Năm khẳng định §7.1 đều xanh.

---

## 8. Khối N3 — Bus I2C chỉ đọc

**Sprint 5, cùng TSK-S5-09.**

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-N3-01** | Quét bus bằng **read-byte**, không bằng quick-write; đọc chip ID; không nhận diện được thì ghi "không nhận diện", không đoán | FR-HAL-01 | — | ⏳ Chờ RFC-0007 | `python/neuroedge/hal/` · `brain/` |
| **TSK-N3-02** | Test trên `i2c-stub` + `lm75`: có thiết bị, bus trống, NACK, timeout (tối đa 1 lần thử lại) | FR-TGT-02 | — | ⏳ Chưa bắt đầu | `python/tests_linux/` |
| **TSK-N3-03** | **Spike ADC** trên runner `ubuntu-latest`: chip ADC I2C có driver hwmon (`ads7828` hoặc `ina2xx`) trên `i2c-stub`, đọc lại `in0_input` | — | — | ⏳ Chưa bắt đầu | báo cáo spike trong PR |

**ADC có điều kiện.**
- Runner tắt `CONFIG_IIO` (`docs/spec/simulation_coverage.md`), nên `iio_dummy` và `ti-ads1015` bị loại.
- **Spike đạt:** ADC nằm trong N3.
- **Spike không đạt:** ADC vào `TODOS.md`, mốc kích hoạt là khi có runner tự host gắn ADC thật.
- `sim` chỉ phát lại giá trị đã ghi, không có quét I2C thật.

**Tiêu chí ra Khối N3:**

- [ ] **Tiêu chí 1:** `tests_linux` phát hiện `0x48` (`lm75`) và báo đúng bus trống.
- [ ] **Tiêu chí 2:** Kết quả spike ADC được ghi lại, và quyết định ADC đã áp dụng.

---

## 9. Khối N4 — Sổ bàn làm việc

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-N4-01** | Ghi sự thật phát hiện được, mỗi mục kèm trace nguồn: vai chân, chip ID. Hai vai mâu thuẫn trên cùng chân thì báo lỗi có kiểu, để người quyết | — | — | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |
| **TSK-N4-02** | Sinh profile board **mới** dạng nháp qua mã đọc/ghi `BoardProfile`, không ghi TOML bằng chuỗi. **Không sửa** ba profile tier-1 | FR-HAL-05 | — | ⏳ Chưa bắt đầu | `python/neuroedge/hal/board.py` |
| **TSK-N4-03** | Cảnh báo chân đặc biệt theo MCU. ESP32-S3: strapping 0, 3, 45, 46; flash/PSRAM 26–32 (33–37 khi dùng PSRAM octal); chân đã bị ngoại vi chiếm (dữ liệu port từ ESP-Claw, Phụ lục A). Đây là cảnh báo, không phải blacklist | — | — | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |

Nếu profile mới cần qua `test_boards.py`, nó phụ thuộc RFC-0002.

---

## 10. Khối N5 — Chat Contracting

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-N5-01** | Từ trace sinh `@action` + gate `0.1.0-draft` + test replay, bằng `templates.scaffold`/`_render` có sẵn. Chỉ ghi vào thư mục agent của người dùng | FR-DX-01 | — | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |
| **TSK-N5-02** | Test **hai chiều** bắt buộc: ít nhất một ALLOW và một BLOCK/`argument_out_of_range`. Bản nháp chỉ có ALLOW thì bị từ chối | FR-CI-* | — | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |
| **TSK-N5-03** | Ba lỗi LLM riêng biệt (malformed, empty, refusal), không ghi tệp rác. Chân không truy được về trace thì từ chối sinh. Tên action trùng thì không ghi đè | — | — | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` · corpus `expected_results.yaml` |
| **TSK-N5-04** | PR của bản nháp in `gate explain` bằng lời, cùng diff chính sách và các test ALLOW/BLOCK | — | — | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |
| **TSK-N5-05** | `trace export --report`: báo cáo bring-up Markdown (chân đã thử, kết quả, thiết bị bus, bản nháp đã sinh) | FR-TRC-* | — | ⏳ Chưa bắt đầu | `python/neuroedge/cli/main.py` |

`extends` từ chối version pre-release, nên không gate nào extends được một bản nháp. Đây là hành vi mong muốn.

---

## 11. Khối N5b — Lab Monitor

Là một panel trong trang sim hiện có (`python/neuroedge/viz/assets/ui.js`, `ui.css`), **không có tab riêng**. Panel chỉ hiện khi `[lab] enabled`. Wireframe tham chiếu: [`wireframe/lab-monitor-v2.html`](wireframe/lab-monitor-v2.html).

**Thứ bậc:**
- Cột phải: thẻ xác nhận → hàng "đang bật" → timeline xung → phán quyết.
- Cột trái: thiết bị → bus I2C.
- Header: huy hiệu LAB MODE.

| Mã Task | Hạng mục công việc | Người | Trạng thái | Sản phẩm bàn giao |
|:---:|:---|:---:|:---:|:---|
| **TSK-N5b-01** | Xếp hàng ask "1/3", ask cũ nhất trước (hôm nay `stateAt` chỉ giữ ask mới nhất). Focus mặc định ở "Huỷ"; phím chỉ tác dụng khi thẻ có focus; không cướp focus khi người đang gõ lệnh | — | ⏳ Chưa bắt đầu | `viz/assets/ui.js` · `tests/test_sim_ui.py` |
| **TSK-N5b-02** | Mất kết nối SSE: banner vàng, làm mờ thiết bị và hàng live, khoá nút ask; gỡ banner khi có tin đầu tiên | — | ⏳ Chưa bắt đầu | `viz/__init__.py` · `ui.js` · `ui.css` |
| **TSK-N5b-03** | Hàng "đang bật" có thời gian còn lại; làn timeline theo chân với vùng bấm ≥24×24 px, mỗi xung là `<button>` có `aria-label`, mũi tên trái/phải để di chuyển | — | ⏳ Chưa bắt đầu | `ui.js` · `ui.css` |
| **TSK-N5b-04** | Thước phong bì ghi rõ cửa sổ lấy từ `board.v1`: xanh dưới 80%, vàng từ 80%, đầy thì đỏ kèm "khoá tới HH:MM:SS". Trạng thái rỗng: bo chưa khai chân → thông điệp trỏ tới `board show --lab`; thiếu phong bì → nhãn vàng | — | ⏳ Chưa bắt đầu | `ui.js` · `sim/ui.py` |
| **TSK-N5b-05** | Thẻ phán quyết: huy hiệu bốn màu theo nghĩa (ALLOW xanh, BLOCK đỏ, ENVELOPE vàng, REJECTED xám, luôn kèm chữ); nhãn "người: Đồng ý/Huỷ/hết hạn"; gộp lặp "×N"; bấm xung thì mở thẻ tương ứng kèm `gate explain` | — | ⏳ Chưa bắt đầu | `ui.js` · `ui.css` |
| **TSK-N5b-06** | Tiêu đề tab "(1) Cần xác nhận" + favicon vàng; công tắc âm báo mặc định tắt. Khi tua lại, ask và hàng live **luôn là hiện tại**. Nhãn bus: "phát lại từ trace `<tệp>` lúc HH:MM:SS" | — | ⏳ Chưa bắt đầu | `ui.js` · `sim/ui.py` |
| **TSK-N5b-07** | Restyle **cả trang sim**: bỏ viền trái trên thẻ phán quyết, thay bằng huy hiệu; nhúng IBM Plex Sans 400/600 + Plex Mono 400 (woff2, subset Latin + tiếng Việt); luật hệ thiết kế ghi ở khối chú thích đầu `ui.css`. **Chặn bởi TSK-N0-06** | — | ⏳ Chặn bởi Q-11 | `ui.css` · `NOTICE` |

**Tiêu chí ra Khối N5b:**

- [ ] **Tiêu chí 1:** Ba ask cùng lúc: không ask nào bị che rồi tự hết hạn.
- [ ] **Tiêu chí 2:** Nhấn Enter trong ô lệnh không bao giờ kích "Đồng ý".
- [ ] **Tiêu chí 3:** `trace view` vẫn là một tệp tự chứa, chạy offline (FR-DX-02).
- [ ] **Tiêu chí 4:** Đi hết luồng xác nhận chỉ bằng bàn phím và VoiceOver.

---

## 12. Khối N6 — Trigger theo sự kiện

Luật "khi X thì Y" là **cấu hình agent**, không phải mở rộng gate. Mỗi trigger gọi một `@action` có gate.

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-N6-01** | Giá trị `call_source` mới `trigger`. `SOURCES` là mã, không nằm trong `schemas/`, nên chỉ cần mục `Q-N` + cập nhật `docs/spec/tool_calling.md`, không cần RFC. Thêm fixture và `expected_results.yaml` | FR-MDL-10 | — | ⏳ Chưa bắt đầu | `actions/tools.py` · `fixtures/tool_calls/` |
| **TSK-N6-02** | `trigger ∉ HUMAN_SOURCES`; có test khẳng định trigger không trả lời được `ask` | Q-26 | — | ⏳ Chưa bắt đầu | `actions/confirmation.py` |
| **TSK-N6-03** | Debounce + trần tần suất trigger; action bị BLOCK không được thử lại vô hạn; trigger bị chặn liên tục thì hiện trên N5b | — | — | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |

---

## 13. Khối N7 — NeuroBrain trên ESP32-S3

**Làm cuối.** Chỉ bắt đầu khi N1–N6 xong, bo Box-3 đã về và HAL Sprint 4 đã xong.

| Mã Task | Hạng mục công việc | Người | Trạng thái | Sản phẩm bàn giao |
|:---:|:---|:---:|:---:|:---|
| **TSK-N7-01** | Lab action + gate trên chip, dùng walker C và sổ token có sẵn | — | ⏳ Chưa bắt đầu | `targets/esp32s3/` |
| **TSK-N7-02** | Cưỡng chế phong bì trong firmware C. Firmware chưa có phong bì thì action gắn phong bì bị **từ chối trên chip** (fail-closed) | — | ⏳ Chưa bắt đầu | `targets/esp32s3/components/` |
| **TSK-N7-03** | Port chọn lọc từ ESP-Claw (Phụ lục A). MCP trên chip chỉ làm sau `TODOS.md` #24, hoặc đi qua UART | — | ⏳ Chưa bắt đầu | `targets/esp32s3/` · `NOTICE` |

---

## 14. Cổng nhu cầu và cột mốc

**Cổng nhu cầu 2026-10-25** (theo khuôn Q-20, `docs/business/cong-nhu-cau-2026-10-25/`). Demo `lab_pulse` trên `sim` + UI cho người dùng U2, rồi đếm số người tự hỏi *"dùng thử trên bo của tôi được không"*.

| Kết quả | Hành động |
|:---|:---|
| **≥ 2 người** | Làm tiếp toàn bộ Giai đoạn 1.5 |
| **Đúng 1 người** | Chỉ làm N0–N2 và N5b; gọi thêm 5 cuộc |
| **0 người** | Đưa Giai đoạn 1.5 vào `TODOS.md`, mốc kích hoạt là Developer Beta |
| **Dưới 3 buổi demo có bản ghi** | Cổng hoãn 1 tuần. N0 và N1 vẫn tiếp tục; từ N2 trở đi chưa mở |

**Ghép luật.** Luật cổng và luật nguồn lực (§3) **cùng áp dụng**, luật chặt hơn thắng.

**Chỉ số cho Developer Beta:**
- số lab call, tỉ lệ BLOCK, số `envelope_refused`;
- **số bản nháp sinh ra so với số bản nháp được khoá**. Đây là chỉ số nhu cầu chính.

---

## 15. Rủi ro và giảm thiểu

| # | Rủi ro | Mức độ | Dấu hiệu sớm | Phương án ứng phó |
|:---:|:---|:---:|:---|:---|
| **1** | NeuroBrain kéo V1 khỏi đường găng M1 | Cao | Việc của V1 bị gán cho N0/N1 | N0/N1 do V2 làm (§3). Không task nào của M1 phụ thuộc Giai đoạn 1.5 |
| **2** | LLM sinh gate nới lỏng hơn ý người nói | Cao | Bản nháp chỉ có test ALLOW | Test hai chiều (TSK-N5-02), `gate explain` trong PR (TSK-N5-04), người duyệt (TSK-N0-05) |
| **3** | Chân kẹt HIGH khi tiến trình chết | Trung bình | Relay nóng hoặc kêu sau crash | §2.3: phần mềm không cứu được. README lab và runbook bắt buộc ghi rõ cần điện trở kéo xuống |
| **4** | Lab lọt vào bản phát hành | Trung bình | Báo cáo build ghi `lab_enabled: true` | Cờ mặc định tắt, `build --release` chặn (TSK-N1-03) |
| **5** | Không có thêm người từ 2026-11-16 | Cao | Chưa có ứng viên trước 2026-11-01 | §3: N2–N7 lùi sau Beta |
| **6** | RFC-0007 hoặc mở rộng Q-11 bị bác | Trung bình | Phản biện tập trung vào primitive mới | `lab_read`/N3 dừng, `lab_pulse` không bị ảnh hưởng. Restyle giữ font hệ thống, chỉ bỏ viền trái |

---

## 16. Thang cắt phạm vi

Cắt theo thứ tự này khi trượt tiến độ. Bậc càng cao cắt càng sớm.

| Bậc | Hạng mục cắt | Hệ quả chấp nhận được |
|:---:|:---|:---|
| **1** | N7 trên chip | NeuroBrain chạy trên host; gate vẫn tương đương xuống chip ở phần sản phẩm |
| **2** | N6 trigger | Bring-up vẫn đủ; hành vi tự động làm sau |
| **3** | N4 sổ bàn làm việc | Sự thật chỉ nằm trong trace thô |
| **4** | N3 bus I2C | Chỉ có `digital.out`/`digital.in` |
| **5** | N5b restyle (TSK-N5b-07) | Panel lab vẫn có, trang giữ phong cách cũ |

**Tuyệt đối không cắt:** N1 cùng cờ lab và test B-1; N2 phong bì. Không có hai khối này thì "secure by design" không đứng được.

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
| 2 | Giai đoạn 1.5 song song Khối 1b tới Developer Beta; N0 + `lab_pulse` trước 2026-10-25, V2 chủ trì |
| 3 | Phạm vi N1–N7 như tệp này; N7 làm cuối |
| 4 | Gói `brain/` với bất biến B-1; phong bì là hook trong HAL, kiểm trước `authorize` |
| 5 | Thêm `digital.in` vào RFC-0007 cùng bus I2C; ADC có điều kiện theo spike |
| 6 | Cờ `[lab] enabled` mặc định tắt; `build --release` chặn |
| 7 | Lab qua MCP trên linux thật chờ TSK-S5-10 |
| 8 | Port chọn lọc từ ESP-Claw theo Phụ lục A |
| 9 | Restyle trang sim với IBM Plex; mở rộng Q-11 cho OFL-1.1, chỉ với font |
| 10 | Luật cổng nhu cầu và nguồn lực ở §3 và §14 |
