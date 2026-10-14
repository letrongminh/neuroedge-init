<!-- SINH TỰ ĐỘNG từ neuroedge-roadmap.md §0 — đừng sửa tay.
     Chạy lại: python3 scripts/gen_user_status.py (kiểm tra: --check) -->

# Trạng thái dự án

> Sinh tự động từ [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) §0 —
> nguồn sự thật duy nhất về tiến độ. Cập nhật nguồn: **2026-10-14**.

## Điều hành

| Chỉ số | Trạng thái hiện hành |
|:---|:---|
| Pha đang thực thi | 🟡 **Phase MVP (§0.5)**, thứ tự theo Q-72 — I2d rồi I2e (NeuroEdge Blueprint bể cá đi trọn ba vòng trên giả lập) trước cổng nhu cầu 8 tuần; phần còn lại của I1, I2a, I2c làm xen; đợt thử đối tác (Q-70) song song; thoại (I4, I5) và Studio tạm dừng, không cắt |
| Increment đang mở | 🟡 **I2d — Nhiệm vụ và agent vận hành** (Q-72) — task bắt đầu khi Bước 0 (đồng bộ tài liệu theo Q-72) xong |
| Cột mốc tiếp theo | **Cổng nhu cầu 8 tuần (Q-72, B6–B8)** — ≥ 3 người ngoài tự cài Blueprint và chạy được, ≥ 1 người chạy liên tục 2 tuần trên G2 hoặc G3, ≥ 1 maker muốn bán (PRD §11.2) |
| Trạng thái CI Lõi | ✅ **PASS 4910/4910 · SKIP 0** |
| Chặn ngoài tầm kỹ thuật | 🟡 **2 hạng mục chặn** |
| Lần cập nhật cuối | **2026-10-14** |

## Increment

| Mốc | Increment | Dự báo | Tiến độ | Trạng thái | Phát hành |
|:---:|:---|:---|:---:|:---|:---|
| **0.x nội bộ** | **I0 — Lõi hợp đồng trên `sim`** | ✅ 2026-09-24 | **42 / 42** | ✅ Xong | lịch sử |
|  | **I1 — Preview nội bộ trên `sim`** | 2026-11-15 | **4 / 6** | 🟡 Đang làm — TSK-I1-02 tạm hoãn (phát triển nội bộ) | tag `v0.1.0` (nội bộ) |
|  | **I2 — `linux` ngang `sim`** | 2026-11-29 | **3 / 4** | 🟡 Phiên tương tác, cảm biến, màn hình xong trên gpio-sim + i2c-stub; nightly RPi 5 còn lại | tag `v0.2.0` (nội bộ) |
|  | **I2a — Nguyên thủy mở rộng trên `sim` và `linux`** | 2026-12-06 | **22 / 27** | 🟡 Sáu RFC đã chấp thuận; tiêu chí số và `NETR` v2; `board.v1` khai đủ nguyên thủy mở rộng, `sim-rpi5`; phong bì an toàn, `digital.in`, I2C chỉ đọc, `analog.in`, thị giác (camera ảo, V4L2, mô hình, vết ghi, gate mẫu) xong trên `sim` và trên kernel (job `linux-hal`, CI run 37153005998: gpio-sim, `i2c-stub`, `vivid`; `verify --targets sim,linux` replay corpus cảm biến và thị giác); PWM và `motion.*` xong trên `sim`, dây `enable` xanh trên gpio-sim. **Còn:** `verify` chưa phát lại agent `fan-pwm` và `rover` (I2a tiêu chí 3); camera mất giữa phiên trên kernel (tiêu chí 5); kênh PWM và cơ cấu thật; golden suy luận thị giác; ô `esp32s3` của bảng phủ (TSK-I3a-01) | tag `v0.2.1` (nội bộ) |
|  | **I2b — Kit mẫu và dựng nhanh** | 2026-12-20 | **4 / 4** | 🟡 Năm kit, thư viện gate, `neuroedge add` xong (tiêu chí 1, 3, 4); còn đo TTFV trên người (tiêu chí 2) và dựng kit trên phần cứng thật | tag `v0.2.2` (nội bộ) |
|  | **I2c — Nền tảng mở** | 2026-12-27 | **11 / 20** | 🟡 Q-67, thiết kế, giấy phép corpus xong; RFC-0002, RFC-0016 → RFC-0018 đã ký (Q-68); `neuroedge.guard` (TSK-I2c-07), `proxy mcp` + `guard init --mcp` (TSK-I2c-14), `proxy http` (TSK-I2c-15), cơ cấu từ xa + plugin Home Assistant (TSK-I2c-16), bộ tài liệu đợt thử đối tác (TSK-I2c-19) và nửa (a) của RFC-0017 xong; đợt thử với đối tác đi ra từ đây (Q-70) ; mở danh sách target và hai task tạm dừng đã bỏ theo Q-77 (§6) | tag `v0.2.3` (nội bộ) · wheel cho một đội đối tác — thử riêng, không chờ bo mạch (Q-70) |
|  | **I2d — Nhiệm vụ và agent vận hành** | 2026-11-11 | **0 / 39** | 🟡 Mở — Bước 0 (đồng bộ tài liệu theo Q-72) đang làm, task bắt đầu khi xong; năm RFC dự kiến và RFC của `TODOS.md` #58 chờ chữ ký kỹ thuật trưởng | tag `v0.2.4` (nội bộ) |
|  | **I2e — NeuroEdge Blueprint tối thiểu** | 2026-11-25 | **0 / 15** | ⏳ Chưa bắt đầu | tag `v0.2.5` (nội bộ) · wheel giao trực tiếp cho người thử ngoài, không index nào (như Q-70); PyPI vẫn ở I6 (Q-39) |
|  | **I2f — NeuroEdge Cloud và hộp tại nhà ESP32** | sau cổng 8 tuần (nhánh) | **1 / 13** | ⏸ Chờ kết quả cổng nhu cầu 2026-12-06 (Q-74); ngoại lệ Q-79: TSK-I2f-10 xong, I2f-11 → I2f-13 chờ bo | dịch vụ tuỳ chọn + firmware hộp ESP32 |
|  | **I3 — Gate trên Box-3 thật** | sau I2e | **6 / 16** | 🟡 Phần không cần bo mạch đã xong (kể cả firmware sinh cho agent trên QEMU, giao diện LVGL có ảnh golden); chờ bo mạch | tag `v0.3.0` + firmware (nội bộ) |
|  | **I3a — Nguyên thủy mở rộng trên `esp32s3`** | sau I2e | **0 / 11** | ⏳ Chưa bắt đầu | tag `v0.3.1` + firmware (nội bộ) |
| **Công khai** | **I6 — Công khai** | sau I2e | **7 / 11** | 🟡 Quét bí mật, SBOM, API Python công khai, MCP qua mạng có xác thực, hợp đồng cho người tích hợp trong `schemas/` (RFC-0015) xong; RFC-0014 chấp thuận (Q-65); chờ I3a | PyPI `v0.6.0` — lần phát hành ra ngoài đầu tiên |
| **v1.0 = MVP** | **I7 — v1.0** | sau I2e | **4 / 12** | 🟡 Ghim Actions, attestation xong; OTA A/B có ký + rollback xong trên QEMU; chờ I6 | `v1.0.0` |
| **Beta** | **I8 — Developer Beta** | sau I2e | **0 / 1** | ⏳ Chưa bắt đầu | `1.0.x` (chỉ bản vá) |

Năng lực, phụ thuộc và giả định của các ngày dự báo: [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) §0.
