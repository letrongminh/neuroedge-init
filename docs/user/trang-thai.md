<!-- SINH TỰ ĐỘNG từ neuroedge-roadmap.md §0 — đừng sửa tay.
     Chạy lại: python3 scripts/gen_user_status.py (kiểm tra: --check) -->

# Trạng thái dự án

> Sinh tự động từ [`neuroedge-roadmap.md`](../../neuroedge-roadmap.md) §0 —
> nguồn sự thật duy nhất về tiến độ. Cập nhật nguồn: **2026-09-24**.

## Điều hành

| Chỉ số | Trạng thái hiện hành |
|:---|:---|
| Pha đang thực thi | 🟡 **Khối 1a: Lõi logic & Action CI (Tuần 0 → 2026-11-15)** |
| Sprint hiện hành | 🟡 **Sprint 2: Lõi thực thi trên `sim` (≈ A1)** — mã A1 xong sớm, 2026-09-23 |
| Cột mốc tiếp theo | **M1: Time-to-first-value < 10 phút trên `sim`** |
| Trạng thái CI Lõi | ✅ **PASS 709/709 · SKIP 0** |
| Chặn ngoài tầm kỹ thuật | 🟡 **1 hạng mục chặn + 1 còn mở** |
| Lần cập nhật cuối | **2026-09-24** |

## Tiến độ các mốc

| Mốc | Sprint / Giai đoạn | Thời gian | Tiến độ | Trạng thái |
|:---:|:---|:---|:---:|:---:|
| **Khối 1a** | **Sprint 1 — Đóng băng lược đồ** | Tuần 0–2<br>2026-09-21 → 2026-09-27 | **12 / 13** | 🟡 **Chờ phần cứng** (chỉ TSK-S1-10) |
|  | **Sprint 2 — Lõi thực thi trên `sim`** *(≈ A1, wedge `sim`)* | **2026-09-28 → 2026-10-25** (Q-19) | **9 / 10** | 🟡 Mã A1 + web UI `sim` xong 2026-09-23; còn TSK-S2-11 (A2) |
|  | **Sprint 3 — Action CI & Linux** *(≈ A2)* | **2026-10-26 → 2026-11-15** (Q-19) | **12 / 17** | 🟡 Action CI + HAL `linux` xong (2026-09-23); tiêu chí ra 5/6 |
| **Khối 1b** | **Sprint 4 — HAL trên `esp32s3`** | **Từ 2026-11-16** (Q-19) · gốc Tuần 6–8 | **0%** | ⏳ Chưa bắt đầu |
|  | **Sprint 5 — Runtime thoại MCU** | Tuần 8–10 | **0%** | ⏳ Chưa bắt đầu |
|  | **Sprint 6 — OTA & Nghiệm thu v1.0** | Tuần 10–12 | **0%** | ⏳ Chưa bắt đầu |
| **Beta** | **Developer Beta** | Tuần 12–16 | **0%** | ⏳ Chưa bắt đầu |
| **Khối 2** | **Fleet OS** *(dịch vụ thương mại duy nhất)* | Tháng 4–8 | **0%** | ⏳ Chờ mốc Beta |
| **Khối 3** | **Bảy đường ray nền tảng** | Tháng 4–8 | **0%** | ⏳ Chờ mốc Beta |

Chi tiết, ghi chú và caveat về lịch: [`neuroedge-roadmap.md`](../../neuroedge-roadmap.md) §0.
