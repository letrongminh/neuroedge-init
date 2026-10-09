<!-- SINH TỰ ĐỘNG từ neuroedge-roadmap.md §0 — đừng sửa tay.
     Chạy lại: python3 scripts/gen_user_status.py (kiểm tra: --check) -->

# Trạng thái dự án

> Sinh tự động từ [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) §0 —
> nguồn sự thật duy nhất về tiến độ. Cập nhật nguồn: **2026-10-09**.

## Điều hành

| Chỉ số | Trạng thái hiện hành |
|:---|:---|
| Pha đang thực thi | 🟡 **Phase MVP (§0.5)** — I1 đang mở; I2, I2a (sáu RFC), phần không cần bo mạch của I3 và I4 làm song song |
| Increment đang mở | 🟡 **I1** — còn I1-02 (tạm hoãn: phát triển nội bộ) |
| Cột mốc tiếp theo | **I1 — Preview nội bộ: TTFV < 10 phút trên 3 người ngoài đội (M1)** |
| Trạng thái CI Lõi | ✅ **PASS 4543/4543 · SKIP 0** |
| Chặn ngoài tầm kỹ thuật | 🟡 **2 hạng mục chặn** |
| Lần cập nhật cuối | **2026-10-09** |

## Increment

| Mốc | Increment | Dự báo | Tiến độ | Trạng thái | Phát hành |
|:---:|:---|:---|:---:|:---|:---|
| **0.x nội bộ** | **I0 — Lõi hợp đồng trên `sim`** | ✅ 2026-09-24 | **42 / 42** | ✅ Xong | lịch sử |
|  | **I1 — Preview nội bộ trên `sim`** | 2026-11-15 | **4 / 6** | 🟡 Đang làm — TSK-I1-02 tạm hoãn (phát triển nội bộ) | tag `v0.1.0` (nội bộ) |
|  | **I2 — `linux` ngang `sim`** | 2026-11-29 | **3 / 4** | 🟡 Phiên tương tác, cảm biến, màn hình xong trên gpio-sim + i2c-stub; nightly RPi 5 còn lại | tag `v0.2.0` (nội bộ) |
|  | **I2a — Nguyên thủy mở rộng trên `sim` và `linux`** | 2026-12-06 | **22 / 27** | 🟡 Sáu RFC đã chấp thuận; tiêu chí số và `NETR` v2; `board.v1` khai đủ nguyên thủy mở rộng, `sim-rpi5`; phong bì an toàn, `digital.in`, I2C chỉ đọc, `analog.in`, thị giác (camera ảo, V4L2, mô hình, vết ghi, gate mẫu) xong trên `sim` và trên kernel (job `linux-hal`, CI run 37153005998: gpio-sim, `i2c-stub`, `vivid`; `verify --targets sim,linux` replay corpus cảm biến và thị giác); PWM và `motion.*` xong trên `sim`, dây `enable` xanh trên gpio-sim. **Còn:** `verify` chưa phát lại agent `fan-pwm` và `rover` (I2a tiêu chí 3); camera mất giữa phiên trên kernel (tiêu chí 5); kênh PWM và cơ cấu thật; golden suy luận thị giác; ô `esp32s3` của bảng phủ (TSK-I3a-01) | tag `v0.2.1` (nội bộ) |
|  | **I2b — Kit mẫu và dựng nhanh** | 2026-12-20 | **4 / 4** | 🟡 Năm kit, thư viện gate, `neuroedge add` xong (tiêu chí 1, 3, 4); còn đo TTFV trên người (tiêu chí 2) và dựng kit trên phần cứng thật | tag `v0.2.2` (nội bộ) |
|  | **I2c — Nền tảng mở** | 2026-12-27 | **8 / 27** | 🟡 Q-67, thiết kế, giấy phép corpus xong; RFC-0002, RFC-0016 → RFC-0018 đã ký (Q-68); `neuroedge.guard` (TSK-I2c-07), `proxy mcp` + `guard init --mcp` (TSK-I2c-14) và nửa (a) của RFC-0017 xong; đợt thử với đối tác đi ra từ đây (Q-70) | tag `v0.2.3` (nội bộ) · wheel cho một đội đối tác — thử riêng, không chờ bo mạch (Q-70) |
|  | **I3 — Gate trên Box-3 thật** | 2026-12-13 | **6 / 16** | 🟡 Phần không cần bo mạch đã xong (kể cả firmware sinh cho agent trên QEMU, giao diện LVGL có ảnh golden); chờ bo mạch | tag `v0.3.0` + firmware (nội bộ) |
|  | **I3a — Nguyên thủy mở rộng trên `esp32s3`** | 2027-01-10 | **0 / 7** | ⏳ Chưa bắt đầu | tag `v0.3.1` + firmware (nội bộ) |
|  | **I4 — Thoại trên host** | 2026-12-13 | **5 / 9** | 🟡 Đặc tả, vector, FSM Python, độ trễ, SystemOne qua Jev xong; STT/TTS trên `sim`, wake-word + STT dự phòng, âm thanh `linux` xong phần mã trên host; phiên micro trên laptop (`run --mic`, TSK-I4-04) xong phần mã; còn mô hình wake-word thật, Pi + HAT | tag `v0.4.0` (nội bộ) |
|  | **I4a — NeuroBrain trên host** | 2027-01-03 | **0 / 33** | ⏳ Chưa bắt đầu | tag `v0.4.1` + extra `[lab]` (nội bộ) |
|  | **I5 — Thoại trên Box-3** | 2027-01-03 | **0 / 7** | ⏳ Chưa bắt đầu | tag `v0.5.0` + firmware (nội bộ) |
|  | **I5a — NeuroBrain trên chip** | 2027-01-24 | **0 / 2** | ⏳ Chưa bắt đầu | tag `v0.5.1` + firmware (nội bộ) |
| **Công khai** | **I6 — Công khai** | 2027-01-31 | **7 / 12** | 🟡 Quét bí mật, SBOM, API Python công khai, MCP qua mạng có xác thực, hợp đồng cho người tích hợp trong `schemas/` (RFC-0015) xong; RFC-0014 chấp thuận (Q-65); chờ I5a | PyPI `v0.6.0` — lần phát hành ra ngoài đầu tiên |
| **v1.0 = MVP** | **I7 — v1.0** | 2027-02-21 | **4 / 12** | 🟡 Ghim Actions, attestation xong; OTA A/B có ký + rollback xong trên QEMU; chờ I6 | `v1.0.0` |
| **Beta** | **I8 — Developer Beta** | 2027-03-21 | **0 / 1** | ⏳ Chưa bắt đầu | `1.0.x` (chỉ bản vá) |
| **v1.1** | **I9 — Lớp provider v1.1 và Fleet OS** | sau I8 (nhánh A) | **0 / 9** | ⏳ Chờ nhánh A | `1.1.0` + dịch vụ |
|  | **I10 — Registry và các đường ray** | sau I8 (nhánh A, Q-5) | **0 / 7** | ⏳ Chờ nhánh A | `1.2.0` + registry |
| **Mở rộng** | **I13 — Bộ port cộng đồng** | sau I8 | **0 / 5** | ⏳ Chưa bắt đầu | bộ port |
|  | **I14 — Robot phân tầng** | sau I13 | **0 / 11** | ⏳ Chưa bắt đầu | 1.x + firmware node RP2350 |
|  | **I16 — Thị giác trên `jetson`** | sau I8 | **0 / 4** | ⏳ Chưa bắt đầu | 1.x |
|  | **I17 — Đa phương thức** | sau I16 | **0 / 4** | ⏳ Chưa bắt đầu | 1.x |
|  | **I18 — Hệ sinh thái thiết bị** | sau I13 | **0 / 3** | ⏳ Chưa bắt đầu | dịch vụ |
| **Ngoài roadmap** | **Khối 4 — AURA thực địa** | sau I8 | — | ⏳ Ngoài roadmap | — |
|  | **Khối 5 — Marketplace** | khi đạt G1–G4 | — | ⏸ Chặn | — |

Năng lực, phụ thuộc và giả định của các ngày dự báo: [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) §0.
