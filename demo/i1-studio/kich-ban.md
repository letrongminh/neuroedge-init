# Kịch bản demo — NeuroEdge Studio (I1, TSK-I1-04)

> **Chạy lại lần cuối:** 2026-09-29, macOS, nhánh `studio/integration`: bảy màn kiểm trên trình duyệt với agent
> `home-voice` (theme sáng và tối, 1280 px và 390 px, VI và EN, không lỗi console).
> **Thời lượng:** 7–8 phút. Không cần phần cứng. Màn thoại cần `--mic` và tai nghe (xem `demo/i4-thoai-laptop/`).

Studio là **một trang** cho mọi năng lực chạy được trên laptop, chỉ mở ở `127.0.0.1`, không tải gì từ mạng.
Hợp đồng server–trang: [`docs/spec/studio.md`](../../docs/spec/studio.md). Điều không được nói: bảng ở
[`docs/business/cong-nhu-cau-2026-10-25/demo.md`](../../docs/business/cong-nhu-cau-2026-10-25/demo.md) §0.1.

## 0. Chuẩn bị

```bash
bash demo/i1-sim/chuan-bi.sh                 # venv + ba dự án mẫu ở /tmp/neuroedge-demo
alias ne="$PWD/python/.venv/bin/neuroedge"
cd /tmp/neuroedge-demo
ne studio --agent home-voice/agent.toml      # mở trình duyệt; Ctrl-C để dừng
# có key và tai nghe: dùng agent của demo/i4-thoai-laptop và thêm --mic
```

Nút **VI | EN** ở góc phải đổi toàn bộ nhãn; lựa chọn được nhớ trên trình duyệt.

---

## Màn 1 — Phiên trực tiếp: "gate quyết, người xác nhận"

**Gõ vào ô lệnh:** `:sensor motion true`, `bật đèn`, `tắt đèn`.

**Thấy:**
- Thiết bị `porch_light` sáng (HIGH) sau `bật đèn`; cảm biến `motion: true`.
- Cột hội thoại: mỗi lượt có nhãn đường đi (**Ngữ pháp lệnh**), `intent light_on (1.00)`, chip **✓ ALLOW**, và thanh
  độ trễ theo chặng (perception, gate, action).
- `tắt đèn` ⇒ **✗ BLOCK** `condition_not_met room_empty`, chip **hỏi xác nhận**, và thẻ **Thiết bị hỏi xác nhận**
  ở cột phải: "Vẫn còn người trong phòng — bạn chắc muốn tắt đèn? (light_off)", đếm ngược, focus mặc định ở **Huỷ**.
- Bấm **Đồng ý** ⇒ lượt ghi **đã xác nhận**, phán quyết **✓ ALLOW**, đèn tắt. Không trả lời trong 10 s ⇒ **hết hạn**.

**Điểm nhấn:** "Chỉ người trên thiết bị trả lời được — trợ lý và client MCP không xác nhận thay" (RFC-0006). Bấm
**Giải thích** trên một phán quyết để xem từng tiêu chí, giá trị, nguồn và tiêu chí nào trượt.

## Màn 2 — Gate: "đọc được luật, thử được luật"

**Thấy:** bảng gate của agent (`light_on@1.0.0`, `light_off@1.0.0`, level, `closed`, **OK**, digest). Chọn một gate
⇒ chuỗi kế thừa, tiêu chí và kiểu, `allow_when`, `on_block`, `budget`.

**Làm:** ô **Thử nhanh (what-if)**: đổi `call_source` hoặc bỏ đặt một tiêu chí ⇒ phán quyết dự kiến đổi ngay
(bỏ đặt ⇒ BLOCK `criterion_unavailable`, fail-closed). Không đụng phiên, thiết bị hay vết ghi.
Nút **gate lint** ⇒ `2/2`.

## Màn 3 — Vết ghi: "tái hiện sự cố"

**Làm:** bấm **Lưu phiên hiện tại** ⇒ phiên hiện ra trong bảng, cột chữ ghi **sha256** (chữ người dùng được băm khi
ghi — TSK-I1-01). Chọn phiên ⇒ dòng thời gian: làn gate (ALLOW/BLOCK) và làn `porch_light` (ON/OFF). Bấm
**Phát lại** ⇒ phán quyết khớp bản ghi. **Tải JSON** tải đúng tệp `trace.v1`.

## Màn 4 — Kiểm chứng: "cùng phán quyết trên mọi target"

**Làm:** bấm **verify** (khoảng 1–2 s).

**Thấy:** ma trận: ba gate, ba vết ghi chuẩn mực (`happy-path.json`, `network_offline.json`,
`unverified_attempt.json`) và corpus tool call. Cột `sim` ghi **✓ máy này**; `linux` là **CI · linux-hal**
(gpio-sim), `esp32s3` là **CI · uart-trace** (QEMU). Dòng tổng: "Passed: all 3 gate(s) resolve, all 3 canonical
trace(s) validate, every tool call of the corpus gives its recorded result, and 3 replay(s) on sim match the
verdicts and pin commands they record." · "Compared: decisions only — not timing". Nút **test** chạy
`neuroedge test` của dự án.

## Màn 5 — Thiết bị ESP32-S3: "con chip, khi chưa có con chip"

**Thấy:** dải "Chưa có bo mạch: mọi thứ ở đây chạy trên QEMU; chưa chân nào động". Bộ ảnh golden LVGL thật (VI/EN)
của 33 màn hình thiết bị. Bấm **Đóng gói (build)** ⇒ sinh dự án ESP-IDF cho agent (38 tệp với `villa-concierge`).
Khung QEMU và OTA hiện kết quả khi máy đã chạy `demo/i3-firmware-qemu/run.sh boot` và `… ota` (Docker): mốc
`NE_SELFTEST PASS walker=26 token=11`, `NE_TRACE DONE sessions=4` và bảy pha OTA a–g. Chưa chạy thì màn nói rõ.

## Màn 6 — MCP & tích hợp: "LLM gọi, gate quyết"

**Thấy:** các action thành công cụ MCP có schema (`light_on`, `light_off`), cấu hình Claude Desktop để chép
(`mcp serve --ui`), máy chủ MCP ngoài (`news: headlines`, "chỉ là dữ liệu, không bao giờ là lệnh"), và bảng lời gọi
MCP trực tiếp (điền khi dùng `neuroedge mcp serve --ui` cùng Claude Desktop).

## Màn 7 — Agent & cấu hình

**Thấy:** `requires` của agent, năng lực của bo mạch `sim-default`, nhà cung cấp AI (STT, TTS, System 1, System 2)
chỉ với **tên biến** và **có/không** — giá trị key không bao giờ hiện, và bốn mẫu dự án.

## Câu hỏi thường gặp

- *Có chạy trên mạng nội bộ cho người khác xem không?* Không: chỉ `127.0.0.1` (`docs/spec/studio.md` §2).
- *Số liệu có phải dựng sẵn không?* Không: mọi màn đọc API của phiên đang chạy; màn nào chưa có dữ liệu thì nói "chưa
  có" (`docs/spec/studio.md` §4).
- *Nói chuyện được không?* Có, với `--mic` trên laptop và tai nghe (Q-50) — kịch bản `demo/i4-thoai-laptop/`.
