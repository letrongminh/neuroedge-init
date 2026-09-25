<!-- SINH TỰ ĐỘNG từ neuroedge-roadmap.md §0 — đừng sửa tay.
     Chạy lại: python3 scripts/gen_user_status.py (kiểm tra: --check) -->

# Trạng thái dự án

> Sinh tự động từ [`neuroedge-roadmap.md`](../../neuroedge-roadmap.md) §0 —
> nguồn sự thật duy nhất về tiến độ. Cập nhật nguồn: **2026-09-25**.

## Điều hành

| Chỉ số | Trạng thái hiện hành |
|:---|:---|
| Pha đang thực thi | 🟡 **I1 — Preview nội bộ trên `sim`** (I2, I3 phần không cần bo mạch và I4 làm song song) |
| Increment đang mở | 🟡 **I1** — còn TSK-S3-08, S3-15, I1-01, I1-02, I1-03 |
| Cột mốc tiếp theo | **I1 — Preview nội bộ: TTFV < 10 phút trên 3 người ngoài đội (M1)** |
| Trạng thái CI Lõi | ✅ **PASS 1036/1036 · SKIP 0** |
| Chặn ngoài tầm kỹ thuật | 🟡 **3 hạng mục chặn** |
| Lần cập nhật cuối | **2026-09-25** |

## Increment

| Mốc | Increment | Dự báo | Tiến độ | Trạng thái | Phát hành |
|:---:|:---|:---|:---:|:---|:---|
| **0.x nội bộ** | **I0 — Lõi hợp đồng trên `sim`** | ✅ 2026-09-24 | **42 / 42** | ✅ Xong | lịch sử |
|  | **Cổng nhu cầu (Q-20)** | 2026-10-25 | — | ⏳ Đang phỏng vấn | — |
|  | **I1 — Preview nội bộ trên `sim`** | 2026-11-15 | **0 / 5** | 🟡 Đang làm | tag `v0.1.0` (nội bộ) |
|  | **I2 — `linux` ngang `sim`** | 2026-11-29 | **0 / 4** | ⏳ Chưa bắt đầu | tag `v0.2.0` (nội bộ) |
|  | **I3 — Gate trên Box-3 thật** | 2026-12-13 | **4 / 14** | 🟡 Phần không cần bo mạch đã xong; chờ bo mạch | tag `v0.3.0` + firmware (nội bộ) |
|  | **I4 — Thoại trên host** | 2026-12-13 | **1 / 8** | 🟡 Đặc tả xong; vector và FSM Python làm song song (Q-39) | tag `v0.4.0` (nội bộ) |
|  | **I5 — Thoại trên Box-3** | 2027-01-03 | **0 / 7** | ⏳ Chưa bắt đầu | tag `v0.5.0` + firmware (nội bộ) |
| **Công khai** | **I6 — Công khai** | 2027-01-10 | **0 / 8** | ⏳ Chưa bắt đầu | PyPI `v0.6.0` — lần phát hành ra ngoài đầu tiên |
| **v1.0** | **I7 — v1.0** | 2027-01-24 | **0 / 12** | ⏳ Chưa bắt đầu | `v1.0.0` |
| **Beta** | **I8 — Developer Beta** | 2027-02-21 | **0 / 1** | ⏳ Chưa bắt đầu | `1.0.x` (chỉ bản vá) |
| **v1.1** | **I9 — Lớp provider v1.1 và Fleet OS** | sau I8 (nhánh A) | **0 / 9** | ⏳ Chờ nhánh A | `1.1.0` + dịch vụ |
|  | **I10 — Registry và các đường ray** | sau I8 (nhánh A, Q-5) | **0 / 8** | ⏳ Chờ nhánh A | `1.2.0` + registry |
| **Mở rộng** | **I11 — Mở danh sách target** | sau I8 | **0 / 6** | ⏳ Chưa bắt đầu | 1.x minor |
|  | **I12 — NeuroBrain** | sau I11 | **0 / 43** | ⏳ Chưa bắt đầu | 1.x + extra `[lab]` |
|  | **I13 — Bộ port cộng đồng** | sau I11 | **0 / 5** | ⏳ Chưa bắt đầu | bộ port |
|  | **I14 — Robot phân tầng** | sau I13 | **0 / 16** | ⏳ Chưa bắt đầu | 1.x + firmware node RP2350 |
|  | **I15 — Thị giác trên `linux`** | sau I8 + nhu cầu camera | **0 / 8** | ⏳ Chưa bắt đầu | 1.x (extra tùy chọn) |
|  | **I16 — Thị giác trên `jetson`** | sau I15 | **0 / 4** | ⏳ Chưa bắt đầu | 1.x |
|  | **I17 — Đa phương thức** | sau I16 | **0 / 4** | ⏳ Chưa bắt đầu | 1.x |
|  | **I18 — Hệ sinh thái thiết bị** | sau I13 | **0 / 4** | ⏳ Chưa bắt đầu | dịch vụ |
| **Ngoài roadmap** | **Khối 4 — AURA thực địa** | sau I8 | — | ⏳ Ngoài roadmap | — |
|  | **Khối 5 — Marketplace** | khi đạt G1–G4 | — | ⏸ Chặn | — |

Năng lực, phụ thuộc và giả định của các ngày dự báo: [`neuroedge-roadmap.md`](../../neuroedge-roadmap.md) §0.
