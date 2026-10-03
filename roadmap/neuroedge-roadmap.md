# NeuroEdge — Roadmap thực thi

## Từ lõi `sim` tới v1.0, Beta, tầng dịch vụ và các hướng mở rộng

**Phiên bản:** 2.0


**Ngày lập:** 21 tháng 9, 2026 · **Cập nhật:** 30 tháng 9, 2026 — MVP = v1.0 đầy đủ, bốn phase (Q-52 → Q-55); viết lại theo increment (Q-39) · lịch sử thay đổi: `CHANGELOG.md`


**Tài liệu nguồn:** `neuroedge-proposal.md` · `neuroedge-prd.md` · việc hoãn có chủ ý [`TODOS.md`](../TODOS.md) · kế hoạch Giai đoạn 1 đã duyệt (lịch sử, đóng băng 2026-09-23) [`docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md`](../docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md)


**Phạm vi:** mọi increment từ **I0** tới **I18** — MVP (v1.0 đầy đủ: bốn gói nguyên thủy mở rộng, kit mẫu, NeuroBrain), Developer Beta, tầng dịch vụ v1.1 và các hướng mở rộng. Bốn phase: §0.5. Đây là **nơi duy nhất** ghi trạng thái task, tiêu chí ra, phụ thuộc, thẻ phát hành và ngày dự báo (Q-39).


**Ghi chú thiết kế** — không lịch, không trạng thái; increment dẫn tới: [`neuroedge-design-neurobrain.md`](neuroedge-design-neurobrain.md) (NeuroBrain, I4a, I5a) · [`neuroedge-design-phase2.md`](neuroedge-design-phase2.md) (thị giác I2a, I3a; phủ phần cứng I11, I13, I16–I18) · [`draft-ke-hoach-mo-rong-robot-fofoca.md`](draft-ke-hoach-mo-rong-robot-fofoca.md) (nguyên thủy mới I2a, I3a; robot phân tầng I14) và [`draft-rfc-node-giao-thuc-dieu-phoi.md`](../docs/rfc/draft-rfc-node-giao-thuc-dieu-phoi.md) (I14)


**Ngoài roadmap:** Khối 4 (AURA thực địa) · Khối 5 (Marketplace) — §8.1

---

## Mục lục

0. [Bảng theo dõi tiến độ & Nhật ký bàn giao](#0-bảng-theo-dõi-tiến-độ--nhật-ký-bàn-giao-live-execution--handoff-dashboard)
1. [Giả định nguồn lực](#1-giả-định-nguồn-lực)
2. [Đường găng, phụ thuộc và luật chống lệch](#2-đường-găng-phụ-thuộc-và-luật-chống-lệch)
3. [Chiến lược tái sử dụng mã nguồn mở](#3-chiến-lược-tái-sử-dụng-mã-nguồn-mở)
4. [Increment tới v1.0 = MVP (I0–I7)](#4-increment-tới-v10--mvp-i0i7)
5. [Developer Beta và điểm rẽ (I8)](#5-developer-beta-và-điểm-rẽ-i8)
6. [Tầng dịch vụ v1.1 (I9–I10)](#6-tầng-dịch-vụ-v11-i9i10)
7. [Hướng mở rộng sau Beta (I11, I13, I14, I16–I18)](#7-hướng-mở-rộng-sau-beta-i11-i13-i14-i16i18)
8. [Ngoài roadmap](#8-ngoài-roadmap)
9. [Thang cắt phạm vi](#9-thang-cắt-phạm-vi)
10. [Lịch chốt quyết định](#10-lịch-chốt-quyết-định)
11. [Nhịp vận hành](#11-nhịp-vận-hành)
12. [Chỉ báo sớm và ngưỡng can thiệp](#12-chỉ-báo-sớm-và-ngưỡng-can-thiệp)

**Phụ lục**

- [A — Ánh xạ sprint, khối và chặng cũ sang increment](#phụ-lục-a--ánh-xạ-sprint-khối-và-chặng-cũ-sang-increment)
- [B — Danh mục mua sắm và hạ tầng](#phụ-lục-b--danh-mục-mua-sắm-và-hạ-tầng)
- [C — Bố cục kho mã nguồn](#phụ-lục-c--bố-cục-kho-mã-nguồn)
- [D — Giao thức truyền dẫn](#phụ-lục-d--giao-thức-truyền-dẫn)

---

## Quy ước tài liệu

Mọi mã và ký hiệu dùng trong tài liệu này (`I0`–`I18`, `TSK-*`, `A1`–`C8`, `TR-N`, `Q-N`, `RB-N`, `V1`–`V7`, `§x.y`…) được giải mã ở **[`docs/user/thuat-ngu.md`](../docs/user/thuat-ngu.md)** — nơi duy nhất, kèm chỗ định nghĩa đầy đủ. Thời gian đo bằng increment và ngày tuyệt đối; tên sprint (Sprint 1–6) và khối (Khối 1a, 1b, 2, 3) chỉ còn là tên lịch sử (Q-39).

## 0. Bảng theo dõi tiến độ & Nhật ký bàn giao (Live Execution & Handoff Dashboard)

> **Mục đích:** Cung cấp điểm nhìn tập trung duy nhất về trạng thái thời gian thực của toàn bộ dự án. Mọi phiên làm việc (session), kỹ sư hoặc AI Agent khi nhận bàn giao chỉ cần đọc mục này là nắm được ngay: *Hệ thống đang ở đâu, vừa hoàn thành gì, ai đang làm gì, và bước hành động kế tiếp là gì.*

### 0.1 Thanh trạng thái điều hành (Executive Status Bar)

| Chỉ số | Trạng thái hiện hành | Ghi chú & Liên kết |
|:---|:---|:---|
| **Pha đang thực thi** | 🟡 **Phase MVP (§0.5)** — I1 đang mở; I2, I2a (sáu RFC), phần không cần bo mạch của I3 và I4 làm song song | Increment và ngày dự báo: §0.2 |
| **Increment đang mở** | 🟡 **I1** — còn I1-02 (tạm hoãn: phát triển nội bộ) | I0 đã xong 42 / 42 · chi tiết §0.2 |
| **Cột mốc tiếp theo** | **I1 — Preview nội bộ: TTFV < 10 phút trên 3 người ngoài đội (M1)** | Ngày dự báo ở §0.2 · chưa phát hành ra ngoài (Q-39) |
| **Lần cập nhật cuối** | **2026-10-04** | Phiên gần nhất: chặng A, phần host — nguyên thủy mở rộng (`digital.in`, I2C, `analog.in`, PWM, `motion.*`, `vision.in`), phong bì an toàn, `board.v1` khai đủ, MCP qua mạng có xác thực; RFC-0014, RFC-0015 soạn; job `linux-hal` xanh lần đầu cho phần mới (CI run 37153005998, PR #91) · trước đó: TSK-W1-02 — tiêu chí `numeric` và `NETR` v2; Q-63 khoảng hở nền tảng · sáu RFC nguyên thủy mở rộng chấp thuận (PR #75 → #80, Q-62); Q-61 bo camera M5Stack CoreS3; Q-58 → Q-60 — MCP qua mạng và Gated Tool Profile đóng băng vào I6, giữ PolyForm NC qua v1.0, mô hình một người + AI agent · trước đó: Q-52 → Q-57 (MVP = v1.0 đầy đủ, bốn gói nguyên thủy mở rộng, NeuroBrain vào MVP) · chi tiết `CHANGELOG.md` `[Chưa phát hành]` |
| **Trạng thái CI Lõi** | ✅ **PASS 3796/3796 · SKIP 0** | `python/tests/` — 119 bộ test; `verify` quét 0 artifact ⇒ mã 1; gate chuẩn mực khoá ở `digests.lock` (job Frozen artifacts); wheel đã cài chạy cả hành trình (job `wheel-smoke`); cổng CI chặn mọi test bị skip · `tests_linux/` 90/90 trên gpio-sim + i2c-stub (lm75, ina219, ads7828) + vkms + vivid, rồi `verify --targets sim,linux` (job `linux-hal`, CI run 37153005998) · `ui-golden` 66 ảnh, `ota-rollback` pha a–g · `security.yml`: pip-audit, gitleaks toàn lịch sử, CodeQL · extra `cloud` trên litellm thật + giấy phép Q-11 (job `cloud-extra`) |
| **Chặn ngoài tầm kỹ thuật** | 🟡 **3 hạng mục chặn** | 🔴 Box-3 và RPi 5 chưa về (TSK-S1-10 → I3; TSK-I2-01) · bo camera đã chọn là M5Stack CoreS3 nhưng chưa đặt (Q-61, TSK-I3a-01) · RFC-0014, RFC-0015 chờ chữ ký (TSK-I6-07, TSK-I6-05) |
| **Hoãn có chủ ý** | 📋 [`TODOS.md`](../TODOS.md) | Mỗi mục kèm mốc kích hoạt · câu hỏi kinh doanh mở (`TODOS.md` #19) rà lại trước I6 — luật cổng nhu cầu đã bỏ (Q-56) |

---

### 0.2 Bảng increment (Increment Matrix)

Mỗi dòng là một increment: một năng lực người dùng thấy được, kết thúc bằng một thẻ phát hành và một tín hiệu đo (Q-39). **Dự báo** là ngày duy nhất của increment; nó chỉ đổi trong cùng PR với bằng chứng làm nó đổi, và kéo theo mọi increment phụ thuộc (§2.4, R5). **Phụ thuộc** chỉ trỏ về increment số nhỏ hơn. Trước I6, mọi bản phát hành là nội bộ.

| Mốc | Increment | Dự báo | Năng lực | Tiến độ | Trạng thái | Phụ thuộc | Phát hành |
|:---:|:---|:---:|:---|:---:|:---|:---|:---|
| **0.x nội bộ** | **I0 — Lõi hợp đồng trên `sim`** | ✅ 2026-09-24 | Gate có kiểu và phiên bản (lint, resolve, kế thừa, tham số, `confirms`), `sim` + web UI, Action CI, MCP, System 2 qua LiteLLM, `linux` replay trên gpio-sim; walker C, sổ token và vết ghi UART trên QEMU | **42 / 42** | ✅ Xong | — | lịch sử |
|  | **I1 — Preview nội bộ trên `sim`** | 2026-11-15 | Người ngoài đội cài từ wheel nội bộ và chạy agent có gate trong dưới 10 phút, không cần phần cứng | **4 / 6** | 🟡 Đang làm — TSK-I1-02 tạm hoãn (phát triển nội bộ) | I0 | tag `v0.1.0` (nội bộ) |
|  | **I2 — `linux` ngang `sim`** | 2026-11-29 | `run`, `record`, `mcp serve --target linux`; cảm biến và màn hình trên `linux`; nightly trên RPi 5 | **3 / 4** | 🟡 Phiên tương tác, cảm biến, màn hình xong trên gpio-sim + i2c-stub; nightly RPi 5 còn lại | I1 | tag `v0.2.0` (nội bộ) |
|  | **I2a — Nguyên thủy mở rộng trên `sim` và `linux`** | 2026-12-06 | Bốn gói: cảm biến (`digital.in`, I2C chỉ đọc, `analog.in`, gate so ngưỡng số), điều khiển mịn (PWM), thị giác (`vision.in`), chuyển động (`motion.*`); sáu RFC; `sim-rpi5` | **21 / 26** | 🟡 Sáu RFC đã chấp thuận; tiêu chí số và `NETR` v2; `board.v1` khai đủ nguyên thủy mở rộng, `sim-rpi5`; phong bì an toàn, `digital.in`, I2C chỉ đọc, `analog.in`, thị giác (camera ảo, V4L2, mô hình, vết ghi, gate mẫu) xong trên `sim` và trên kernel (job `linux-hal`, CI run 37153005998: gpio-sim, `i2c-stub`, `vivid`; `verify --targets sim,linux` replay corpus cảm biến và thị giác); PWM và `motion.*` xong trên `sim`, dây `enable` xanh trên gpio-sim. **Còn:** `verify` chưa phát lại agent `fan-pwm` và `rover` (I2a tiêu chí 3); camera mất giữa phiên trên kernel (tiêu chí 5); kênh PWM và cơ cấu thật; golden suy luận thị giác; ô `esp32s3` của bảng phủ (TSK-I3a-01) | I2 | tag `v0.2.1` (nội bộ) |
|  | **I2b — Kit mẫu và dựng nhanh** | 2026-12-20 | Năm kit phần cứng (BOM, sơ đồ đấu dây, gate khoá), thư viện gate khởi đầu, `neuroedge add` | **0 / 4** | ⏳ Chưa bắt đầu | I2a | tag `v0.2.2` (nội bộ) |
|  | **I3 — Gate trên Box-3 thật** | 2026-12-13 | Gate chạy trên chip, điều khiển chân thật; người dùng tự nạp agent; `verify` ba target bậc 1 cho miền phán quyết | **6 / 14** | 🟡 Phần không cần bo mạch đã xong (kể cả firmware sinh cho agent trên QEMU, giao diện LVGL có ảnh golden); chờ bo mạch | I1 | tag `v0.3.0` + firmware (nội bộ) |
|  | **I3a — Nguyên thủy mở rộng trên `esp32s3`** | 2027-01-10 | Bốn gói trên chip: Box-3 và M5Stack CoreS3 có camera (Q-53, Q-61) | **0 / 7** | ⏳ Chưa bắt đầu | I2a, I3 | tag `v0.3.1` + firmware (nội bộ) |
|  | **I4 — Thoại trên host** | 2026-12-13 | Nói chuyện với agent trên `sim` và `linux`: wake-word, cắt lời, STT/TTS qua provider cloud, fallback lệnh cục bộ | **5 / 9** | 🟡 Đặc tả, vector, FSM Python, độ trễ, SystemOne qua Jev xong; STT/TTS trên `sim`, wake-word + STT dự phòng, âm thanh `linux` xong phần mã trên host; phiên micro trên laptop (`run --mic`, TSK-I4-04) xong phần mã; còn mô hình wake-word thật, Pi + HAT | I2 | tag `v0.4.0` (nội bộ) |
|  | **I4a — NeuroBrain trên host** | 2027-01-03 | Dựng bằng hội thoại có hợp đồng trên `sim` và `linux`, phủ bốn gói (Q-55) | **0 / 33** | ⏳ Chưa bắt đầu | I2a, I4 | tag `v0.4.1` + extra `[lab]` (nội bộ) |
|  | **I5 — Thoại trên Box-3** | 2027-01-03 | Demo "nói chuyện với con chip $5": thoại trên ESP32-S3, gate trên chip, cùng vết ghi replay trong CI | **0 / 7** | ⏳ Chưa bắt đầu | I3, I4 | tag `v0.5.0` + firmware (nội bộ) |
|  | **I5a — NeuroBrain trên chip** | 2027-01-24 | Lab action, gate và phong bì của NeuroBrain chạy trên Box-3 và bo camera | **0 / 2** | ⏳ Chưa bắt đầu | I3a, I4a, I5 | tag `v0.5.1` + firmware (nội bộ) |
| **Công khai** | **I6 — Công khai** | 2027-01-31 | Repo công khai, `pip install neuroedge` từ PyPI, lược đồ ở URL công khai, video demo thoại và bốn gói trên `sim`, `linux` và `esp32s3`; MCP qua mạng có xác thực, hợp đồng cho người tích hợp đóng băng, bề mặt Python công khai (Q-58, Q-63) | **5 / 12** | 🟡 Quét bí mật, SBOM, API Python công khai, MCP qua mạng có xác thực xong; RFC-0014 và RFC-0015 chờ chữ ký; chờ I5a | I2b, I5a | PyPI `v0.6.0` — lần phát hành ra ngoài đầu tiên |
| **v1.0 = MVP** | **I7 — v1.0** | 2027-02-21 | Lần ra mắt MVP (Q-52): OTA A/B có ký, bảo mật thiết bị, ổn định 24 giờ trên chip; đủ A1–A12 | **4 / 12** | 🟡 Ghim Actions, attestation xong; OTA A/B có ký + rollback xong trên QEMU; chờ I6 | I6 | `v1.0.0` |
| **Beta** | **I8 — Developer Beta** | 2027-03-21 | 50–100 lập trình viên ngoài trên dòng `1.0.x`; đo B1–B5, chọn nhánh | **0 / 1** | ⏳ Chưa bắt đầu | I7 | `1.0.x` (chỉ bản vá) |
| **v1.1** | **I9 — Lớp provider v1.1 và Fleet OS** | sau I8 (nhánh A) | Một endpoint và credential cho cả đội, failover khai trong cấu hình, cấp phát, OTA canary, tải vết ghi sự cố | **0 / 9** | ⏳ Chờ nhánh A | I8 | `1.1.0` + dịch vụ |
|  | **I10 — Registry và các đường ray** | sau I8 (nhánh A, Q-5) | `gate add` từ registry có ký, định danh ổn định, đo lường, sandbox | **0 / 8** | ⏳ Chờ nhánh A | I8 | `1.2.0` + registry |
| **Mở rộng** | **I11 — Mở danh sách target** | sau I8 | RFC-0002 PR2: enum `target` theo bậc, `TARGET_TIERS` trong mã lõi, `board validate` | **0 / 6** | ⏳ Chưa bắt đầu | I8 | 1.x minor |
|  | **I13 — Bộ port cộng đồng** | sau I11 | Tài liệu, bộ vector tuân thủ và khung port để người ngoài tự port bậc 3 | **0 / 5** | ⏳ Chưa bắt đầu | I7, I11 | bộ port |
|  | **I14 — Robot phân tầng** | sau I13 | Pi 5 + nhiều node MCU, mỗi node tự lượng giá gate; mất liên lạc về trạng thái an toàn; ROS 2/Nav2 có gate | **0 / 11** | ⏳ Chưa bắt đầu | I4, I7, I11, I13 | 1.x + firmware node RP2350 |
|  | **I16 — Thị giác trên `jetson`** | sau I11 | `jetson` bậc 2, thị giác thời gian thực | **0 / 4** | ⏳ Chưa bắt đầu | I11 | 1.x |
|  | **I17 — Đa phương thức** | sau I16 | Thoại và thị giác trong một máy trạng thái; gate đa phương thức | **0 / 4** | ⏳ Chưa bắt đầu | I16 | 1.x |
|  | **I18 — Hệ sinh thái thiết bị** | sau I13 | SDK đa thiết bị, kho HAL port, chứng nhận miễn phí tự kiểm chứng | **0 / 4** | ⏳ Chưa bắt đầu | I9, I10, I13 | dịch vụ |
| **Ngoài roadmap** | **Khối 4 — AURA thực địa** | sau I8 | Ứng dụng khách sạn/villa; chỉ dùng API công khai (proposal §8.6) | — | ⏳ Ngoài roadmap | I8 | — |
|  | **Khối 5 — Marketplace** | khi đạt G1–G4 | Sàn trao đổi tài sản có thu phí — Chặn (PRD §14) | — | ⏸ Chặn | — | — |

**Giả định của các ngày dự báo (Q-39, Q-52):** bo mạch Box-3 về trước 2026-11-01; một người + AI agent, việc cần phần cứng hoặc người ngoài có người trong vòng (Q-60, §1.1); thoại trên host (I4) và OTA trên QEMU (TSK-S6-01, S6-02, S6-04) làm song song với I3. Ngày của I2a → I8 đặt lại bằng TSK-I2a-01 ([`docs/reports/uoc-luong-mvp-2026-09-30.md`](../docs/reports/uoc-luong-mvp-2026-09-30.md), giả định G1 → G6): bo camera chọn trước 2026-10-09, sáu RFC chấp thuận trước 2026-10-09; ngày của I1 → I5 giữ nguyên. MVP trượt thì dời ngày, không cắt phạm vi (Q-52). Không còn cổng nhu cầu chặn increment nào (Q-56).

---

### 0.3 Thẻ Bàn giao Hiện tại (Active Session Handoff Card)

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ THẺ BÀN GIAO PHIÊN LÀM VIỆC (LIVING HANDOFF CARD)                 Cập nhật: 2026-10-04 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 0. MỤC TIÊU — hoàn thành mọi lớp nền tảng trên ba target bậc 1 (chốt 2026-10-03)       │
│    Lớp nền tảng: hợp đồng, nguyên thủy HAL (5 lõi + 4 gói), phong bì, thoại, tích      │
│    hợp (MCP qua mạng, API Python), tin cậy. NeuroBrain (I4a, I5a) là lớp ứng dụng:     │
│    mục tiêu kế tiếp, xếp sau, không cắt (Q-55)                                         │
│    • Chặng A — `sim` + `linux`, làm ngay. Xong khi đạt: I2a tiêu chí 1–9,              │
│      N2.1–N2.3, I4 tiêu chí 2, I6 tiêu chí 7–10                                        │
│    • Chặng B — `esp32s3` + phần cứng thật, mở khi bo về. Xong khi đạt: tiêu chí ra     │
│      I3, I3a, I5; I2 tiêu chí 4; I4 tiêu chí 4; TSK-S6-03, S6-05, V1b-05               │
│                                                                                        │
│ 1. VỪA HOÀN THÀNH — chặng A: phần host, rồi bằng chứng trên kernel (PR #91)            │
│    • `linux-hal`, CI run 37154951261: `tests_linux` 90 passed; `verify --targets       │
│      sim,linux` Passed — bốn corpus gói replay trên `linux-rpi5` (I2a tiêu chí 3)      │
│    • Cảm biến + phong bì: TSK-I2a-02/03/04, N2-01→05 — chạy trên gpio-sim, `i2c-stub`  │
│    • Thị giác TSK-V1b-01 trên `vivid` (lỗi số khung bắt được, sửa `6bbfb43`), V1b-02→08│
│    • `board.v1` khai đủ; `sim-rpi5` (I2a-06); agent `rail-gate`, `gate-watch`          │
│    • PWM (W1-01), `motion.*` (I2a-05): dây `enable` xanh trên gpio-sim; PWM thật chưa  │
│    • TSK-P2-04: MCP qua mạng, mTLS + OAuth 2.1; RFC-0014, RFC-0015 đã soạn (nháp)      │
│                                                                                        │
│ 2. ĐANG THỰC HIỆN                                                                      │
│    • TSK-S1-10 (V2) — chờ bo mạch; đo thêm MultiNet (+ WakeNet) theo Q-14              │
│    • Chờ người: chữ ký RFC-0014, RFC-0015                                              │
│                                                                                        │
│ 3. VIỆC TIẾP THEO — đúng thứ tự                                                        │
│    1. Đóng nốt chặng A: golden suy luận + sai số `tolerance` (TSK-V1b-04, đang làm);   │
│       I2a 5 còn `safe_state` trên PWM/motor thật — cần Pi 5 (TSK-I2-01)                │
│    2. Chữ ký RFC-0014, RFC-0015 → TSK-I6-05 (PR mã: lược đồ), TSK-I6-07                │
│    3. Đặt 2 Box-3 + 1 RPi 5 + 2 M5Stack CoreS3 (Phụ lục B, Q-61) — mở chặng B          │
│    4. Chặng B: TSK-I3a-01 (`esp32s3-cores3`, đo Q-3), HAL C bốn gói, nightly mỗi bo    │
│    5. I4 tiêu chí 2: phiên thoại sống trên `linux` (Pi + HAT) và micro laptop (I4-04)  │
│                                                                                        │
│ 4. LƯU Ý — bất biến ở CHANGELOG.md §3.3; dưới đây chỉ điều chưa có ở đó                │
│    • Chỉ c.do() điều khiển được chân: HAL chưa gắn ledger từ chối mọi lệnh             │
│    • Nguyên thủy mở rộng chỉ có mã sau khi RFC của nó được chấp thuận                  │
│    • Replay tính lại phán quyết từ dữ kiện đã ghi; không gọi model, không đọc máy      │
│    • Model cloud (Jev, STT, thị giác) là đầu vào không tin cậy: miền, ngưỡng, rồi gate │
│    • tests_linux/ chỉ chạy trên CI (job linux-hal): gpio-sim, i2c-stub, vkms, vivid    │
│    • Giám sát line linux bật mặc định, fail-closed: mất giám sát ⇒ từ chối lệnh bật    │
│    • Task cần phần cứng/người: agent soạn script + checklist, người làm (Q-60)         │
│    • Chạy ruff check + ruff format --check trước khi commit (CI chặn)                  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 0.4 Quy ước Cập nhật & Bàn giao (Handoff Protocol)

Khi xong một task: làm theo [`CONTRIBUTING.md` §8](../CONTRIBUTING.md#8-hoàn-thành-một-task--cập-nhật-tài-liệu-tiến-độ-changelog) —
nơi duy nhất định nghĩa việc cập nhật trạng thái task, tiêu chí ra, §0.1–§0.3 và changelog.

---

---

### 0.5 Bốn phase (Q-52)

Phase gom increment theo năng lực người dùng thấy được; ngày và phụ thuộc vẫn chỉ ở §0.2.

| Phase | Người dùng làm được gì | Increment | Kết thúc bằng |
|:---|:---|:---|:---|
| **P0 — Dọn nền** | — | *(không có increment; PR tài liệu 2026-09-30)* | Tài liệu sản phẩm ở `roadmap/`, roadmap theo MVP |
| **MVP = v1.0** | Chọn một kit, chạy trên `sim` dưới 10 phút, dựng thiết bị thật trong một ngày trên `linux` hoặc `esp32s3`; đủ năm nguyên thủy lõi và bốn gói mở rộng; tuỳ biến bằng hội thoại (NeuroBrain) hoặc lệnh sinh mã; mọi lệnh ra phần cứng qua gate | I0 → I7 (gồm I2a, I2b, I3a, I4a, I5a) | `v1.0.0` — đủ A1–A12; **một lần ra mắt, trượt thì dời ngày, không cắt** |
| **Beta và thương mại** | 50–100 lập trình viên ngoài; doanh nghiệp mua license và Fleet OS theo điểm rẽ | I8 → I9, I10 | `1.0.x`, rồi `1.1.0` theo §5.6 |
| **Mở rộng** | Bộ port cộng đồng, robot nhiều node, Jetson, đa phương thức, hệ sinh thái thiết bị | I11, I13, I14, I16, I17, I18 | 1.x theo nhu cầu đo được |

#### Mười mốc phát hành theo người dùng

Phase là cách đội lập kế hoạch; **mốc phát hành** là cách người dùng thấy sản phẩm. Mỗi mốc là một việc người dùng làm được, kết thúc khi mọi increment của nó xong. Bảng này không ghi ngày: ngày của một mốc là ngày dự báo muộn nhất trong các increment của nó ở §0.2. CPO Dashboard (`docs/business/cpo-dashboard.html`), poster E-09 và chương kiến trúc 13 đọc từ bảng này. Mỗi increment thuộc đúng một mốc.

| # | Mốc | Người dùng làm được gì | Vì sao quan trọng | Increment | Ai dùng được |
|:---:|:---|:---|:---|:---|:---|
| 1 | **Thử trên laptop** | Cài một gói, chạy một agent có gate trên trình mô phỏng trong dưới 10 phút; không cần phần cứng, tài khoản hay khoá API | Cửa vào của sản phẩm: ai cũng thử được mà không tốn tiền phần cứng | I0, I1 | Đội và người thử nội bộ |
| 2 | **Thiết bị thật trên Raspberry Pi** | Đấu một kit (đèn, cửa, quạt, cảm biến, camera, motor) vào Pi 5; cùng agent, cùng gate như trên laptop | Lần đầu một lệnh AI chạm phần cứng thật mà vẫn qua hợp đồng | I2, I2a, I2b | Đội và người thử nội bộ |
| 3 | **Gate chạy trên chip $5** | Nạp agent lên ESP32-S3 (Box-3, M5Stack CoreS3); gate quyết ngay trên chip, mất mạng vẫn chặn đúng | An toàn không phụ thuộc cloud; cùng một hợp đồng từ laptop tới vi điều khiển | I3, I3a | Đội và người thử nội bộ |
| 4 | **Nói chuyện với thiết bị** | Ra lệnh bằng giọng nói trên laptop, Pi và chip; cắt lời thì lệnh chưa chạy bị huỷ | Giọng nói là giao diện tự nhiên nhất của thiết bị trong nhà; cắt lời phải an toàn | I4, I5 | Đội và người thử nội bộ |
| 5 | **Dựng bằng hội thoại** | Mô tả thiết bị bằng lời; NeuroBrain sinh action, gate và phong bì; người duyệt rồi mới khoá | Rút từ một ngày xuống vài phút để dựng một thiết bị có hợp đồng | I4a, I5a | Đội và người thử nội bộ |
| 6 | **Ra mắt công khai** | Ai cũng `pip install neuroedge`; gọi thiết bị từ Claude, Home Assistant hay agent framework qua MCP có xác thực | **Lần đầu người ngoài dùng được** | I6 | Mọi người (phi thương mại miễn phí) |
| 7 | **v1.0 — đưa vào sản phẩm** | Cập nhật firmware có ký, khoá thiết bị, chạy ổn định 24 giờ; đủ tiêu chí nghiệm thu A1–A12 | Đủ tin cậy để đội sản phẩm đưa vào thiết bị bán ra | I7 | Mọi người; doanh nghiệp qua license thương mại |
| 8 | **Developer Beta** | 50–100 lập trình viên ngoài dùng thật trên dòng `1.0.x` | Số đo thật quyết hướng thương mại (điểm rẽ §5.6) | I8 | Lập trình viên được mời |
| 9 | **Vận hành đội thiết bị (v1.1)** | Cập nhật hàng nghìn thiết bị theo đợt, kéo vết ghi sự cố từ xa, dùng chung gate qua registry có ký | Nguồn doanh thu chính: Fleet OS và license (P-3) | I9, I10 | Doanh nghiệp |
| 10 | **Mở rộng hệ sinh thái** | Cộng đồng tự port bo mạch mới; robot nhiều MCU; Jetson; thoại cùng thị giác | NeuroEdge thành chuẩn chung, không phải sản phẩm của một đội | I11, I13, I14, I16, I17, I18 | Cộng đồng, OEM, đội robot |

---

## 1. Giả định nguồn lực

> **Đây là giả định, không phải dữ kiện.** Toàn bộ ngày dự báo ở §0.2 phụ thuộc vào nó. Nếu cấu hình đội khác đi, xem §1.3 trước khi đọc tiếp.

### 1.1 Vai trò

| Vai trò | Trách nhiệm chính | Có mặt từ |
| :--- | :--- | :---: |
| **V1 — Kỹ sư lõi nền tảng** | HAL, Action Contract Engine, lược đồ gate và trace, Action CI, thoại trên host | I0 |
| **V2 — Kỹ sư nhúng** | Port `esp32s3`, HAL trên chip, tối ưu bộ nhớ, node RP2350 | I0 *(bán thời gian tới khi bo mạch về)* |
| **V3 — Kỹ sư trải nghiệm lập trình viên** | Giao diện `sim`, CLI, scaffold, tài liệu, ví dụ mẫu, phát hành | I0 |
| **V4 — Kỹ sư hạ tầng dịch vụ** | Fleet OS, Registry, hệ đo lường, hoàn thiện lớp provider tự vận hành | trước I9 một tháng |
| **V5 — Kỹ sư thị giác** | HAL thị giác, mô hình, NPU | trước I2a *(Q-52)* |
| **V7 — Kỹ sư NeuroBrain** | Lab action, Chat Contracting, Lab Monitor, trigger — cùng V2 | trước I4a *(Q-52)* |
| **V6 — Kỹ sư nhúng thứ hai** | Pipeline âm thanh trên chip (TSK-S5-01, S5-02, S5-06, S5-07), OTA và bảo mật thiết bị — song song với HAL của V2 (Q-39) | 2026-11-16 |

**Mô hình vận hành từ Q-60 (thay phần nhân sự của Q-52): một người + AI agent.** Bảng trên là **làn việc**, không phải người. AI agent làm làn host (mã, test, tài liệu, CI, mô phỏng). Task cần phần cứng, người ngoài hoặc chữ ký có **người trong vòng**: agent soạn script, checklist và quy tắc quyết định trước, người thao tác hoặc ký, agent ghi bằng chứng. Độ nhạy theo cấu hình: §1.3. Trước Q-52, cấu hình tối thiểu khả thi là 3 người cho I0–I4 và V6 là đòn bẩy kéo v1.0 sớm (Q-39).

### 1.2 Vì sao V2 phải có mặt từ đầu

Rủi ro **R-1** của PRD (tối ưu bộ nhớ MCU làm trượt thoại trên chip) được đánh giá mức **Cao** lúc lập kế hoạch, nay **Trung bình** nhờ cloud-first (PRD §13.2). Cách giảm thiểu hiệu quả không phải là theo dõi muộn, mà là **chạy spike khả thi bộ nhớ ngay khi bo mạch về** (TSK-S1-10), khi vẫn còn đủ thời gian để lập lại kế hoạch I5 (Q-44).

V2 làm phần firmware không cần bo mạch trước (walker C, sổ token, vết ghi UART trên QEMU — Q-21) và rà thiết kế HAL dưới góc nhìn ràng buộc MCU. Một HAL thiết kế mà không có tiếng nói của kỹ sư nhúng sẽ phải viết lại ở I3.

### 1.3 Độ nhạy theo quy mô đội

| Cấu hình | Tác động lên ngày dự báo |
| :--- | :--- |
| **2 người** | I1–I4 giãn gần gấp đôi; I3 → I7 nối tiếp trên một người. Không còn bậc cắt 5 (Q-44), nên v1.0 dời theo |
| **3 người, không có V6** | I5 và I7 nối tiếp trên V2: v1.0 lùi khoảng 4–5 tuần so với §0.2 |
| **3 người + V6** *(giả định cơ sở của Q-39, trước khi phạm vi MVP mở rộng)* | Ngày của I1 → I5 ở §0.2 |
| **Một người + AI agent, người trong vòng cho task phần cứng** *(hiện trạng, Q-60)* | Làn host giữ ngày ở §0.2: tốc độ của TSK-I2a-01 đo trên chính cấu hình này. Làn chip (I3, I3a, I5, I5a, phần phần cứng của I7) do một người làm nối tiếp, song song với việc review làn host; chưa có số đo tốc độ đó — đối chiếu khi bo mạch về ([`docs/reports/uoc-luong-mvp-2026-09-30.md`](../docs/reports/uoc-luong-mvp-2026-09-30.md) §5), dời ngày cùng PR có bằng chứng (R5). V6 vào thì làn âm thanh trên chip tách khỏi HAL |
| **Đủ người cho V1 → V7** *(giả định của Q-52, thay bởi Q-60)* | Ngày ở §0.2 — cách tính: [`docs/reports/uoc-luong-mvp-2026-09-30.md`](../docs/reports/uoc-luong-mvp-2026-09-30.md) |
| **4–5 người** | I1, I2 và I4 song song hơn; đường găng vẫn là chuỗi phần cứng I3 → I5 → I7 |

---

## 2. Đường găng, phụ thuộc và luật chống lệch

### 2.1 Đồ thị phụ thuộc

Đọc `A ◄ B, C`: A phụ thuộc B và C. Nguồn là cột Phụ thuộc của §0.2.

```text
MVP · host    I1 ◄ I0 · I2 ◄ I1 · I2a ◄ I2 · I2b ◄ I2a · I4 ◄ I2 · I4a ◄ I2a, I4
MVP · chip    [bo mạch] ► TSK-S1-10 ► I3 ◄ I1 · I3a ◄ I2a, I3 · I5 ◄ I3, I4 · I5a ◄ I3a, I4a, I5
Ra mắt        I6 công khai ◄ I2b, I5a · I7 v1.0 = MVP ◄ I6 · I8 Beta ◄ I7
Sau Beta      I9, I10 ◄ I8 (nhánh A) · I11 ◄ I8 · I13 ◄ I7, I11 · I14 ◄ I4, I7, I11, I13
              I16 ◄ I11 · I17 ◄ I16 · I18 ◄ I9, I10, I13

Chuỗi dài nhất  [bo mạch] ► TSK-S1-10 ► I3 ► I3a ► I5 ► I5a ► I6 ► I7
                (I3a còn chờ nhánh: sáu RFC ► I2a)

```

### 2.2 Đường găng

| # | Mắt xích | Vì sao nằm trên đường găng |
| :---: | :--- | :--- |
| 0 | ✅ Sáu RFC của I2a được chấp thuận (2026-10-01, PR #75 → #80) | Không có RFC thì không có mã cho nguyên thủy mở rộng (§2.3); kỹ thuật trưởng duyệt |
| 1 | Bo mạch Box-3 về → TSK-S1-10 | Không có số đo bộ nhớ thì không chốt được kế hoạch thoại trên chip (Q-44) — và giờ cả ngân sách cho bốn gói (TSK-I3a-01) |
| 2 | I3 → I3a — HAL, gate và nguyên thủy mở rộng trên chip | Không có target thứ ba trên phần cứng thật thì không chứng minh được tương đương; thị giác còn cần bo camera |
| 3 | I5 — thoại trên chip | Vẫn là mắt xích khó nhất; rủi ro đã giảm từ CR-1.0 (STT/TTS ở provider cloud). V6 làm âm thanh song song với HAL của V2 |
| 4 | I6 — công khai | A1 đo chính thức và A9 cần người ngoài, nên v1.0 không đạt khi repo còn kín |
| 5 | I7 — OTA, ổn định 24 giờ, A1–A12 | OTA làm trước trên QEMU; còn lại phần cần bo mạch và phép chạy 24 giờ |
| 6 | I3a → I5a | Hai mắt xích MVP thêm vào làn chip (bốn tuần và hai tuần, [`docs/reports/uoc-luong-mvp-2026-09-30.md`](../docs/reports/uoc-luong-mvp-2026-09-30.md) §4); v1.0 lùi bốn tuần so với trước Q-52 |

**Chuỗi con người:** kỹ thuật trưởng cho sáu RFC của I2a và RFC-0002 · CPO cho điều khoản license thương mại (`TODOS.md` #44) trước I6 · chủ sản phẩm làm mọi task cần phần cứng hoặc người ngoài, AI agent chuẩn bị (Q-60).

**Đòn bẩy mã nguồn mở trên đường găng:** mắt xích 2 rút ngắn nhờ driver XiaoZhi, mắt xích 3 nhờ Pipecat và bộ mô hình âm thanh. Chi tiết và mức rút ngắn thực tế tại §3.7.

**Không nằm trên đường găng, làm song song:** I1, I2, I4, phần `sim` + `linux` của I2a, I2b, I4a, giao diện `sim`, tài liệu, hạ tầng CI.

### 2.3 Quy tắc đóng băng lược đồ

Từ khi I0 đóng băng lược đồ (2026-09-27), mọi thay đổi đối với lược đồ gate hoặc lược đồ vết ghi bắt buộc:

1. Có đề xuất RFC viết ra, nêu rõ lý do và ảnh hưởng tương thích ngược
2. Được kỹ thuật trưởng phê duyệt
3. Kèm kịch bản di trú cho toàn bộ vết ghi đã tồn tại

Đây là quy tắc nghiêm ngặt nhất của toàn bộ dự án. Lược đồ trôi nổi làm sụp đổ mệnh đề trung tâm.

**RFC đang mở:** [RFC-0002](../docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md) đề xuất mở rộng enum `target` ở `board.v1` và `trace.v1`, và đưa bậc target vào mã lõi (`TARGET_TIERS`). Nguyên thủy `vision.in` đã tách khỏi RFC này, sang RFC-0012 ở I2a (RFC-0002 §9.1, Q-53). RFC ở trạng thái *đang thảo luận*; **lược đồ chưa đổi và không được đổi cho tới khi RFC được phê duyệt**. PR thực thi của nó là I11 (Q-40); I0–I10 không phụ thuộc kết quả RFC đó. RFC-0013 (I2a) sửa hai bất biến §5b, §5c của nó cho nhiều bo tham chiếu trên một target (Q-53).

### 2.4 Luật chống lệch

Mười hai luật giữ cho roadmap không lệch trước lệch sau (Q-39). Luật có ghi *test* được `python/tests/test_plan_contract.py` kiểm trên mọi PR.

| # | Luật | Kiểm bằng |
|:---:|:---|:---:|
| **R1** | Trạng thái task, tiêu chí ra, dự báo, phụ thuộc, thẻ phát hành và thang cắt chỉ nằm trong tài liệu này; ghi chú thiết kế không có chúng | test |
| **R2** | Mã increment duy nhất và tăng dần; chỉ thêm, không đánh số lại; chèn giữa dùng hậu tố (`I3a`) | test |
| **R3** | Cột "Phụ thuộc" ở §0.2 chỉ trỏ về increment có số nhỏ hơn | test |
| **R4** | Mỗi increment đúng một ngày dự báo, chỉ ở §0.2; increment có điều kiện ghi "sau Ix" | test |
| **R5** | Dự báo chỉ đổi trong cùng PR với bằng chứng làm nó đổi, và dời luôn các increment phụ thuộc | review |
| **R6** | Không dùng nhãn tuần hay tháng đánh số để xếp lịch; khoảng thời gian tính từ lúc một increment mở | test |
| **R7** | Quyết định chỉ là `Q-N` (PRD §15); ngoài phạm vi chỉ ở PRD §14; tài liệu này dẫn mã, không chép nội dung | review |
| **R8** | Mỗi mã TSK có đúng một dòng task trong tài liệu này; mọi mã được dẫn trong mã nguồn, CI và ghi chú thiết kế đều tồn tại ở đây | test |
| **R9** | Mỗi ô trạng thái có đúng một glyph trong ✅ 🟡 ⏳ ⏸ 🔴 | test |
| **R10** | "Tiến độ" ở §0.2 bằng số task ✅ trên tổng số task trong bảng của increment đó | test |
| **R11** | Tham chiếu chéo dùng mã hoặc mục ổn định, không dùng số dòng (`tệp.md:NNN`) | test |
| **R12** | Đóng băng Beta áp cho dòng `1.0.x` trong I8: chỉ lỗi chặn hành trình 10 phút và lỗi an toàn; RFC, đặc tả, ghi chú thiết kế và CI không đổi hành vi sản phẩm vẫn được merge | review |

**Họ mã task.** Mã cho biết task từ đâu ra; increment cho biết khi nào làm. Mã không bao giờ đánh lại — dời một task sang increment khác là dời dòng của nó.

| Họ | Nguồn |
|:---|:---|
| `TSK-S1-*` … `TSK-S6-*` | Sprint 1–6 của kế hoạch gốc (tên lịch sử). `TSK-S4-06` chưa từng được cấp |
| `TSK-K2-*`, `TSK-K3-*` | Khối 2 (Fleet OS) và Khối 3 (đường ray) |
| `TSK-N*-*` | NeuroBrain (Giai đoạn 1.5) |
| `TSK-V1a-*` … `TSK-V3-*`, `TSK-P1-*`, `TSK-P2-*` | Giai đoạn 2 |
| `TSK-W<chặng>-<nn>` | Robot phân tầng; số giữ theo chỉ mục của ghi chú thiết kế (W3-1 → `TSK-W3-01`), mục đã gộp để lại khoảng trống |
| `TSK-I<n>-<nn>` | Việc mới không thuộc họ nào; `n` là increment đầu tiên lên lịch nó |

---
## 3. Chiến lược tái sử dụng mã nguồn mở

**Nguyên tắc bao trùm: xây thứ tạo khác biệt, mượn thứ đã là hàng hóa.**

Mục tiêu là rút ngắn tối đa thời gian ra thị trường bằng cách tái sử dụng và port các dự án mã nguồn mở hàng đầu vào mọi khâu — đồng thời bảo vệ tuyệt đối phần tài sản trí tuệ lõi.

### 3.1 Ranh giới bất di bất dịch

Ranh giới *tài sản lõi — tự xây 100%* / *hàng hóa — mượn tối đa* nằm ở **proposal §3.9** (nơi duy nhất). Nó quyết định mọi mục còn lại: thành phần thuộc tài sản lõi thì dù có thư viện sẵn cũng không dùng; thuộc hàng hóa thì dù viết được cũng không viết.

### 3.2 Phép thử quyết định

> **Phụ thuộc vào nó có buộc ta vi phạm P-1, P-2 ([PRD §1.5](neuroedge-prd.md#15-năm-nguyên-tắc-thiết-kế-bất-biến)), hoặc ba quyết định kiến trúc đầu tiên — `sim` là target thật · gate là artifact có phiên bản · trace là công dân hạng nhất — không?**

**Có** → chỉ liên thông hoặc tham khảo thiết kế. **Không** → tái sử dụng tối đa.

### 3.3 Kỷ luật giấy phép

Năm quy tắc giấy phép: **proposal §3.9**. Ma trận phụ thuộc và trạng thái xác minh: **proposal Phụ lục H**. Hawkbit (EPL-2.0) đã duyệt, EMQX (BSL) không dùng — Q-11, chốt 2026-09-25. LiteLLM đã duyệt (Q-11) và dùng như SDK qua extra `neuroedge[cloud]` (Q-10). Giấy phép của chính NeuroEdge — lõi và chuẩn mở: [`LICENSING.md`](../LICENSING.md) (Q-45).

### 3.4 Ma trận tích hợp theo khối

| Khối | Hạng mục kỹ thuật | Dự án tái sử dụng | Hình thức | Tiết kiệm |
|:---|:---|:---|:---|:---:|
| **1a** | CLI `new` / `run` / `test` | Typer · Rich · generator mẫu Python (không Copier — TSK-S3-07) | Thư viện Python | 2 tuần |
| **1a** | `allow_when` dạng chuỗi CEL *(tùy chọn, ⏸ TSK-S2-06)* | Google CEL (`cel-python`) — chỉ phân tích cú pháp trên máy tính | Front-end của trình biên dịch cây | — *(chưa dùng)* |
| **1a** | Giao diện web môi trường `sim` | Wokwi Elements *(đã cân nhắc, chưa dùng — TSK-S2-09 giao trang tự viết, không CDN)* | Web components | — |
| **1a** | Khung kiểm thử Action CI | Pytest · DeepDiff | Helper `neuroedge.testing` *(plugin `pytest-neuroedge` dự kiến)* | 2 tuần |
| **1a** | Chuẩn hóa lược đồ gate và trace | Pydantic v2 · `rfc8785` canonical JSON | Thư viện chuẩn hóa | 1 tuần |
| **1b** | Bo mạch tham chiếu ESP32-S3 | XiaoZhi ESP32 | **Port trực tiếp driver** | 5 tuần |
| **1b** | Barge-in, VAD, xử lý khung âm thanh | Pipecat · microWakeWord · libfvad | **Port mô hình pipeline** | 4 tuần |
| **1b** | OTA cấp thiết bị | ESP-IDF `esp_https_ota`, `esp_ota_ops` | Tận dụng SDK chuẩn | 2 tuần |
| **1b** | Hiển thị trạng thái trên màn hình | LVGL v8/v9 | Thư viện đồ họa nhúng | 2 tuần |
| **1a** | Lớp trừu tượng nhà cung cấp (OpenAI-compatible + adapter) | LiteLLM | **Thư viện trong lõi** | 6 tuần |
| **2** | Điều phối OTA canary | Eclipse Hawkbit | Backend điều phối | 5 tuần |
| **2** | Kết nối thiết bị và viễn trắc | Broker MQTT giấy phép dễ dãi (Mosquitto EDL-1.0 · NanoMQ · VerneMQ — Q-11) · FastAPI WebSockets | Hạ tầng kết nối | 3 tuần |
| **3** | Kho Gate Registry công khai | CNCF ORAS · Harbor | Chuẩn lưu trữ OCI | 4 tuần |
| **3** | Hệ đo lường sử dụng | OpenMeter | Hạ tầng metering | 4 tuần |
| **4** | Điều khiển phòng cho AURA | Home Assistant Core API | Integration adapter | 4 tuần |

**Cách đọc cột "Tiết kiệm":** đây là công sức *viết mã* tránh được, không phải thời gian lịch rút ngắn. Xem §3.7 để biết phần nào thật sự chạm vào đường găng.

### 3.5 Năm dự án port trực tiếp

Năm dự án này không dừng ở `pip install`. Chúng cần trích xuất mã hoặc kiến trúc và đưa thẳng vào codebase.

| # | Dự án | Đích đến | Phần trích xuất |
|:---:|:---|:---|:---|
| 1 | **XiaoZhi ESP32** | `targets/esp32s3/drivers/` | Khởi tạo codec I2S (ES8311, ES7210) · cấu hình chân I2C/SPI của ESP32-S3-Box-3 · driver LCD ST7789 · vòng lặp streaming WebSocket nhị phân |
| 2 | **Pipecat** | `neuroedge/perception/pipeline/` | Frame processor theo khung âm thanh · thuật toán khoảng lặng động · **cơ chế barge-in**: ngắt hàng đợi phát và phát tín hiệu hủy lệnh actuator chưa hoàn tất |
| 3 | **Wokwi Elements** *(chưa dùng)* | `neuroedge/sim/web/` *(dự kiến)* | `<wokwi-led>` · `<wokwi-pushbutton>` · `<wokwi-servo>` · `<wokwi-lcd1602>`; không có `solenoid-lock` (proposal Phụ lục H.1). TSK-S2-09 giao trang tự viết, không phụ thuộc |
| 4 | **LiteLLM** | `neuroedge/models/providers/` | Chuyển đổi I/O về một chuẩn chung · failover — gọi như SDK trong tiến trình, không chạy proxy (Q-10); hạn mức theo thiết bị do NeuroEdge tự làm (proposal §6.1). **Từ CR-1.0: thư viện trong lõi phân phối kèm sản phẩm**, không phải lõi của một dịch vụ do NeuroEdge vận hành — xem Q-11 |
| 5 | **OpenMeter** | Lõi metering Khối 3 | Engine gom cụm sự kiện · đối soát số lượt gọi agent và lượt thẩm định gate |

**Giá trị lớn nhất nằm ở mục 1 và 2** vì chúng nằm trên đường găng: loại bỏ rủi ro kẹt thanh ghi, lỗi clock I2S, méo tiếng, và toàn bộ vòng thử sai của các ca biên hội thoại.

### 3.6 Ba dự án chỉ liên thông, không phụ thuộc

ESP-Claw (liên thông qua MCP), LiveKit Agents và TEN Framework (chỉ tham khảo thiết kế) — quyết định và lý do: **proposal Phụ lục H.3**.

Riêng **XiaoZhi tuyệt đối không fork toàn bộ**: đó là một ứng dụng firmware, logic hội thoại gắn thẳng vào lệnh phần cứng, không có HAL và không có khái niệm hợp đồng hành động. Chỉ port tầng driver theo §3.5, phần còn lại không đụng tới.

**Điểm chiến lược:** cộng đồng XiaoZhi là kênh phân phối. Tương thích với bo mạch XiaoZhi phổ biến có giá trị cao hơn nhiều so với dùng lại mã — người dùng đã có sẵn phần cứng, cắm vào chạy được ngay là đòn bẩy trực tiếp cho chỉ tiêu B2.

### 3.7 Tác động thật lên đường găng

Tổng tiết kiệm công sức viết mã khoảng 50 tuần-người. **Nhưng phần lớn không nằm trên đường găng.**

| Mắt xích đường găng | Có đòn bẩy OSS không | Mức rút ngắn thực tế |
|:---|:---|:---|
| Đóng băng lược đồ gate và trace | Một phần — Pydantic và canonical JSON | Không đáng kể, vì đây là công việc thiết kế |
| Gate Engine với fail-closed | Không — ánh xạ toán tử và cây quyết định là mã NeuroEdge; CEL hoãn (TSK-S2-06) | 0 |
| Record và replay | Một phần — DeepDiff cho so khớp golden | Dưới 1 tuần |
| **Port HAL lên `esp32s3`** | **Có — driver XiaoZhi** | **2–3 tuần** |
| **Runtime thoại trên MCU** | **Có — Pipecat, microWakeWord, libfvad** | **2–3 tuần** |

**Kết luận thực tế:** đòn bẩy OSS rút ngắn Khối 1b nhiều hơn Khối 1a, và quan trọng hơn cả là nó **hạ rủi ro R-1 từ mức Cao xuống Trung bình**. Tuy vậy chi phí tích hợp, rà soát giấy phép và ghim phiên bản là chi phí mới phát sinh. Lịch trình trong tài liệu này **giữ nguyên**; phần tiết kiệm được chuyển thành vùng đệm cho I5, nơi rủi ro tập trung.

### 3.8 Bảo toàn tương đương target khi có hai ngôn ngữ

Đây là hệ quả nghiêm trọng nhất của việc port, và cần xử lý tường minh.

Quyết định **Q-8 đã chốt**: C/C++ trên ESP-IDF cho firmware, Python cho `sim` và `linux`. Hệ quả: máy trạng thái hội thoại **buộc phải có hai hiện thực**. Không thể chia sẻ mã giữa hai bên.

Điều này va thẳng vào P-2. FR-PER-02 yêu cầu barge-in thu hồi lệnh actuator chưa thực thi — nghĩa là hành vi cắt lời rò trực tiếp vào miền hành động vật lý. Hai hiện thực barge-in khác nhau cho ra hai hành vi thu hồi khác nhau.

**Giải pháp bắt buộc: một đặc tả chuẩn tắc, hai hiện thực tuân thủ, một bộ kiểm thử tuân thủ dùng chung.**

| # | Thành phần | Nội dung | Increment |
|:---:|:---|:---|:---:|
| 1 | **Đặc tả máy trạng thái** | Năm trạng thái và hợp đồng thu hồi lệnh: [`docs/spec/voice_fsm.md`](../docs/spec/voice_fsm.md). Là nguồn sự thật duy nhất, không phải mã Python | I4 (TSK-S2-07) ✅ |
| 2 | **Bộ vector kiểm thử tuân thủ** | Kịch bản thoại ở `voice_fsm.md` §9, tại `fixtures/compliance/voice/`; miền quyết định dùng ba vết ghi chuẩn mực (bên dưới). Độc lập với ngôn ngữ | I4 (TSK-S3-10) |
| 3 | **Hiện thực Python** | Cho `sim` và `linux`, port thiết kế từ Pipecat | I4 (TSK-S3-11) |
| 4 | **Hiện thực C/C++** | Cho `esp32s3`, port driver từ XiaoZhi | I5 (TSK-S5-03) |
| 5 | **`neuroedge verify` chạy bộ vector trên mọi target bậc 1** | Lệch nhau sinh `SafetyRegressionError` (NE4002) | I3–I5 |

**Không có bước 1 và 2 thì việc port Pipecat là một rủi ro, không phải một đòn bẩy.** Đặc tả và bộ vector phải có trước khi viết hiện thực thứ hai.

#### Đặc tả chuẩn tắc: năm trạng thái

Năm trạng thái, bảng chuyển trạng thái, **hợp đồng thu hồi lệnh vật lý** (Actuator Abort Contract) và
kịch bản tuân thủ: [`docs/spec/voice_fsm.md`](../docs/spec/voice_fsm.md) (TSK-S2-07). Đó là mệnh đề mà cả
hai hiện thực phải thoả, và là mệnh đề bộ vector tuân thủ kiểm tra trực tiếp.

#### Hệ quả tương tự với tầng lượng giá gate

Gate chạy on-device và phải fail-closed đúng cách khi mất mạng, nên phán quyết phải lượng giá được **trên cả vi điều khiển**, từ cùng một artifact với host. Cách làm đã chốt ở **Q-9 (phương án A) và Q-23** — nội dung, lý do và phương án bị bác ở PRD §15: `neuroedge build` biên dịch gate thành cây quyết định; firmware duyệt bố cục nhị phân `NETR` v1 bằng walker C99 (TSK-S4-02, RFC-0003).

**Ranh giới tài sản lõi:** trình biên dịch sang cây quyết định và bộ duyệt cây trên thiết bị là **mã của NeuroEdge** — ngữ nghĩa an toàn, thuộc nhóm không nhận phụ thuộc (§3.1). `cel-python`, nếu dùng, chỉ phân tích cú pháp chuỗi CEL trên máy tính; front-end CEL đang hoãn (TSK-S2-06).

#### Ba tệp vết ghi chuẩn mực

Bộ vector tuân thủ khởi đầu bằng đúng ba kịch bản, cố định tại `fixtures/traces/`:

| Tệp | Kịch bản | Kết quả kỳ vọng |
|:---|:---|:---|
| `happy-path.json` | Khách đã xác thực yêu cầu mở cửa | Gate `ALLOW` · chân `door_lock` nhận xung 30.000 ms |
| `unverified_attempt.json` | Người chưa xác thực yêu cầu mở cửa | Gate `BLOCK` · `escalate` tới lễ tân · chân `door_lock` **không bao giờ** nhận xung |
| `network_offline.json` | Mất kết nối khi đang thẩm định gate | Fail-closed kích hoạt · hành động bị từ chối · lý do `gate_unreachable` |

Ba tệp này là thước đo tuân thủ cho mọi target bậc 1 (I0–I7), và là đầu vào trực tiếp của `neuroedge verify`.

### 3.9 Nghĩa vụ ghi nhận nguồn

**Hạn chót: hoàn tất trước khi port bất kỳ dòng mã nào** — đã đạt ở I0.

Năm nghĩa vụ — (1) ma trận giấy phép, (2) tệp `NOTICE` ở gốc kho, (3) ghi nhận tại chỗ trong mã, (4) mục ghi nhận trong tài liệu công khai, (5) ghim phiên bản cho mọi phụ thuộc — đặc tả ở **proposal §3.9**.

Đây là nghĩa vụ pháp lý. Một vi phạm phát hiện sau khi phát hành công khai tốn kém hơn nhiều so với vài ngày rà soát trước.

### 3.10 Rủi ro khi làm ngược

| Nếu | Hậu quả |
|:---|:---|
| Fork toàn bộ XiaoZhi làm nền | Kế thừa kiến trúc không có HAL; phải gỡ để chèn gate; gánh nhánh fork vĩnh viễn |
| Xây trên ESP-Claw | `linux` thành hạng hai → mất bằng chứng hợp đồng năng lực → mất luận điểm đánh sườn |
| Port Pipecat mà không có đặc tả và bộ vector tuân thủ | Hai hiện thực barge-in phân kỳ → tương đương target vỡ ở miền thu hồi lệnh actuator |
| Dùng CEL trên host nhưng cú pháp khác trên thiết bị | Gate cho phán quyết khác nhau giữa hai target ở đúng tầng an toàn |
| Nhúng mã GPLv3 vào phần phân phối | Lây nhiễm bản quyền sang lõi — xung đột với giấy phép của lõi (Q-45) — và sang dự án của khách hàng |
| Port mã trước khi rà soát giấy phép | Rủi ro pháp lý phát hiện sau khi công khai, chi phí khắc phục rất cao |
| Tự viết AEC, VAD, codec, rule engine | Đốt I0 và I5 vào bài toán đã có lời giải tốt, trễ mốc mà không tạo khác biệt |

---

---

## 4. Increment tới v1.0 = MVP (I0–I7)

Từ Q-52, MVP là v1.0 đầy đủ: các increment có hậu tố (I2a, I2b, I3a, I4a, I5a) nằm cạnh increment mà chúng mở rộng.

Mỗi increment có: thẻ (mục tiêu, điều kiện vào ngoài các increment phụ thuộc, tín hiệu đo, người), bảng task, và tiêu chí ra. Increment chỉ được phát hành khi đạt mọi tiêu chí ra của nó, và kèm một demo trong `demo/` (§11.1, Q-49).

### 4.1 I0 — Lõi hợp đồng trên `sim`

| | |
|:---|:---|
| **Mục tiêu** | Lõi hợp đồng: gate có kiểu và phiên bản, `sim` là target thật, Action CI trên host, MCP và System 2 (U1/J1 gõ chữ, U4/J6 → A3, A4, A5, A7) |
| **Điều kiện vào** | — |
| **Tín hiệu đo** | CI lõi (số test ở §0.1) |
| **Người** | V1, V2, V3 |

Đóng 2026-09-24 với đủ task. Ba bảng dưới giữ theo sprint gốc để truy vết; task của Sprint 1–3 chưa xong đã dời sang I1, I3, I4, I6 và I10 (Phụ lục A).

#### Nguồn: Sprint 1 — Đóng băng lược đồ

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S1-01** | Đặc tả 5 nguyên thủy HAL và thuộc tính đối chiếu | FR-HAL-01, FR-HAL-02, FR-HAL-03 | V1 | ✅ Hoàn thành | [`schemas/board.v1.json`](../schemas/board.v1.json) |
| **TSK-S1-02** | Lược đồ gate v1: 8 trường, 3 kiểu `evaluate`, 4 hành vi `on_block`, `budget` | FR-GATE-02, FR-GATE-03, FR-GATE-04 | V1 | ✅ Hoàn thành | [`schemas/gate.v1.json`](../schemas/gate.v1.json) · sửa theo [RFC-0001](../docs/rfc/0001-gate-schema-conditional-requirements.md) (bắt buộc có điều kiện) |
| **TSK-S1-03** | Quy tắc kế thừa `extends`: 5 nguyên tắc an toàn | FR-GATE-06, FR-GATE-07, FR-GATE-08 | V1 | ✅ Hoàn thành | **Đã cưỡng chế bằng mã:** [`gate_resolver.py`](../python/neuroedge/engine/gate_resolver.py), [`constraints.py`](../python/neuroedge/engine/constraints.py) · test tại [`test_gate_resolver.py`](../python/tests/test_gate_resolver.py) |
| **TSK-S1-04** | Lược đồ vết ghi v1: 6 nhóm sự kiện, khối `metadata` | FR-TRC-01, FR-TRC-02, FR-TRC-03 | V1 | ✅ Hoàn thành | [`schemas/trace.v1.json`](../schemas/trace.v1.json) |
| **TSK-S1-05** | Ma trận giấy phép và tệp `NOTICE` cho toàn bộ dự án sẽ port (§3.9) | — | V2 | ✅ Hoàn thành | [`NOTICE`](../NOTICE) 4 mục A–D · cổng CI chặn copyleft mạnh · [`requirements-lock.txt`](../python/requirements-lock.txt) (nghĩa vụ 5) |
| **TSK-S1-06** | **Dựng bộ khung monorepo** theo [`CONTRIBUTING.md` §6](../CONTRIBUTING.md#6-cấu-trúc-kho): `schemas/` · `python/` · `targets/` · `fixtures/` | — | V1 | ✅ Hoàn thành | [`schemas/`](../schemas/), [`python/`](../python/), [`targets/`](../targets/), [`fixtures/`](../fixtures/) |
| **TSK-S1-07** | **Ba tệp lược đồ chính thức** trong `schemas/`: `trace.v1.json` · `gate.v1.json` · `board.v1.json` | FR-TRC-01, FR-GATE-02, FR-HAL-02 | V1 | ✅ Hoàn thành | JSON Schema draft 2020-12 · CI thẩm định `$id` và `check_schema` · test tại [`test_schemas.py`](../python/tests/test_schemas.py) |
| **TSK-S1-08** | **Ba tệp vết ghi chuẩn mực** tại `fixtures/traces/` (`happy-path`, `unverified_attempt`, `network_offline`) | FR-CI-01, FR-CI-02 | V1 | ✅ Hoàn thành | [`fixtures/traces/`](../fixtures/traces/) + [fixture phản chứng](../fixtures/traces/invalid/) kèm [`expected_errors.yaml`](../fixtures/traces/expected_errors.yaml) · thẩm định cả `format: date-time` |
| **TSK-S1-09** | Khung Python SDK, CLI và Action CI ban đầu (`replay`, `scenario`) | FR-CLI-01, FR-CI-01 | V1 | ✅ Hoàn thành | [`python/neuroedge/`](../python/neuroedge/) · CLI thực thi `gate resolve/lint/publish`, `trace validate/show`, `board list/show`, `verify` · lệnh chưa có engine thoát mã 2 |
| **TSK-S1-11** | Rà soát thiết kế HAL dưới ràng buộc MCU | — | V2 | ✅ Hoàn thành | [`docs/spec/hal_mcu_review.md`](../docs/spec/hal_mcu_review.md) (5 kết luận + 4 ràng buộc cho Sprint 4) · hiện thực tại [`hal/board.py`](../python/neuroedge/hal/board.py) + [`boards/`](../boards/) 3 target |
| **TSK-S1-12** | Hai workflow CI: `ci-sim-linux.yml` và `nightly-hardware.yml` | FR-CI-05, FR-CI-06 | V1 | ✅ Hoàn thành | [`ci-sim-linux.yml`](../.github/workflows/ci-sim-linux.yml) (lược đồ · phân giải gate · vết ghi · test 3 bản Python · lint · cổng giấy phép · **cổng chặn test skip**) · [`nightly-hardware.yml`](../.github/workflows/nightly-hardware.yml) (dựng IDF · ngân sách flash Q-3 · thu số đo · trôi phụ thuộc) · *Job `memory-spike` chỉ chạy tay trên runner có bo mạch và chưa chạy lần nào — TSK-S1-10, TSK-S4-05* |
| **TSK-S1-13** | Quy ước đóng góp và mẫu RFC đổi lược đồ | — | V1 | ✅ Hoàn thành | [`CONTRIBUTING.md`](../CONTRIBUTING.md) · [`docs/rfc/`](../docs/rfc/): [quy trình](../docs/rfc/README.md), [mẫu](../docs/rfc/0000-template.md), [RFC-0001](../docs/rfc/0001-gate-schema-conditional-requirements.md) |

**Đòn bẩy OSS:** Pydantic v2 và `rfc8785` cho chuẩn hóa lược đồ · Typer, Rich cho khung CLI ban đầu (Copier dùng lúc dựng khung, bỏ hẳn ở TSK-S3-07 vì GPL3 bắc cầu).

- [x] **Tiêu chí 1:** JSON Schema của gate và trace publish nội bộ, có ví dụ hợp lệ và ví dụ sai kèm thông báo lỗi kỳ vọng.
  *Bằng chứng:* [`schemas/`](../schemas/) 3 tệp · hợp lệ: [`gates/`](../gates/) + [`fixtures/gates/valid/`](../fixtures/gates/valid/) · **sai kèm lỗi kỳ vọng:** [`fixtures/gates/invalid/`](../fixtures/gates/invalid/) + [`expected_errors.yaml`](../fixtures/gates/expected_errors.yaml), [`fixtures/traces/invalid/`](../fixtures/traces/invalid/) + [`expected_errors.yaml`](../fixtures/traces/expected_errors.yaml). Test cưỡng chế corpus khép kín cả hai chiều (mỗi tệp có một mục, mỗi mục có một tệp) và mọi lỗi đủ 3 thành phần FR-DX-04.
- [x] **Tiêu chí 2:** Ba gate mẫu viết tay được công cụ phân giải đúng, gồm một trường hợp kế thừa 2 cấp.
  *Bằng chứng:* chuỗi `base-access@1.0.0` → `unlock_door@1.2.0` → `unlock_door_night@1.0.0` (đúng 3 cấp, tức **kế thừa 2 cấp**). `neuroedge gate lint` xanh. [`test_sample_gates.py`](../python/tests/test_sample_gates.py) kiểm tra từng nguyên tắc trên corpus thật, gồm mệnh đề **điều kiện chỉ siết chặt đơn điệu xuống chuỗi**.
- [x] **Tiêu chí 4:** Bộ khung monorepo dựng xong; `schemas/` chứa đủ ba tệp lược đồ và được CI kiểm tra tính hợp lệ.
  *Bằng chứng:* job `frozen-artifacts` của [`ci-sim-linux.yml`](../.github/workflows/ci-sim-linux.yml) chạy `check_schema` draft 2020-12, đối chiếu `$id`, và **khẳng định nghịch đảo**: corpus phản chứng phải tiếp tục thất bại, nếu phân giải được thì job đỏ.
- [x] **Tiêu chí 5:** Ba tệp vết ghi chuẩn mực tại `fixtures/traces/` đã viết tay và phân giải đúng.
  *Bằng chứng:* `neuroedge trace validate fixtures/traces/*.json` → 3/3 VALID. [`test_trace_fixtures.py`](../python/tests/test_trace_fixtures.py) kiểm tra **nội dung kịch bản**, không chỉ tính hợp lệ lược đồ (happy-path cấp xung 30 000 ms; hai kịch bản còn lại **không sinh lệnh actuator nào**).
- [x] **Tiêu chí 6:** Quyết định Q-11 đã chốt (§10.2) — điều kiện để bắt đầu port bất kỳ dòng mã nào.
  **ĐẠT cho phạm vi Giai đoạn 1 (2026-09-23).** Phần LiteLLM của Q-11 đã duyệt: `litellm==1.102.0` là MIT, wheel không chứa `enterprise/`, mọi phụ thuộc bắc cầu đạt chính sách phụ thuộc bắc cầu của Q-11 (PRD §15), cưỡng chế bằng CI (job `cloud-extra`). **Phần Hawkbit EPL-2.0 / EMQX BSL** chốt 2026-09-25 (Hawkbit duyệt, EMQX không dùng) — chưa có dòng mã nào của chúng được port; phần D của [`NOTICE`](../NOTICE) ghi rõ phạm vi phơi nhiễm. Phát hiện phát sinh trong Sprint 1: `copier` kéo theo `jinja2-ansible-filters` **GPL3** — đã chuyển sang extra `scaffold` để lõi không bị lây nhiễm, và cổng CI giấy phép chặn tái diễn; TSK-S3-07 thay `copier` bằng generator Python thuần và bỏ hẳn extra đó.

#### Nguồn: Sprint 2 — Lõi thực thi trên `sim`

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S2-01** | Hiện thực HAL cho target `sim` | FR-TGT-01, FR-HAL-01 | **V2** *(ENG-T3)* | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/hal/sim.py` · `tests/test_hal_sim.py` |
| **TSK-S2-02** | Đối chiếu năng lực lúc build, thông báo lỗi đầy đủ 3 thành phần | FR-HAL-04, FR-HAL-05, FR-DX-04 | V1 | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/engine/compiler.py` · lệnh `neuroedge build` · agent mẫu `fixtures/agents/villa-concierge/` · `tests/test_compiler.py` |
| **TSK-S2-03** | Gate Engine: `evaluate`, `allow_when`, `on_block`, `budget`. `on_block` v1.0 theo **Q-17**: mọi hành vi đều chặn hành động vật lý; `escalate`/`ask` ghi sự kiện + gọi hook (mặc định no-op); `degrade` chạy `fallback_action` qua gate của chính nó; xác nhận `ask` là TSK-S3-26 (Q-26). ✅ khi xong phạm vi đã đặc tả | FR-GATE-03, FR-GATE-04, FR-GATE-09 | V1 | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/engine/gate.py` · `engine/trace_sink.py` (`EventLog`) · `tests/test_gate_engine.py` |
| **TSK-S2-04** | Cơ chế fail-closed và mạch ngắt suy giảm | FR-ACE-03, NFR-REL-02 | V1 | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/engine/circuit_breaker.py` · `tests/test_fail_closed.py` |
| **TSK-S2-05** | Decorator `@action`, cấm gọi trực tiếp, `c.do()` và `c.say()`, **token phán quyết dùng một lần** | FR-ACE-02, FR-ACE-04, FR-ACE-05, FR-ACE-07 | V1 | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/actions/` (`spec.py`, `conversation.py`, `token.py`) · `python/neuroedge/hal/digital.py` · `docs/spec/threat_model.md` · `tests/test_actions.py` |
| **TSK-S2-08** | Interface `SystemOne` / `SystemTwo` + trường độ tin cậy + test double tất định + **fallback cục bộ = bộ nhận diện lệnh cố định** (ngữ pháp lệnh → intent + độ tin cậy) chạy trên chữ gõ ở `sim` (**Q-14**, Q-15). Connector cloud thật đi cùng TSK-S2-11. Q-17: ✅ khi xong phạm vi đã đặc tả | FR-MDL-01, FR-MDL-02, FR-MDL-03, FR-ACE-03 | V1 | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/models/` (`system.py`, `grammar.py`, `doubles.py`) · ngữ pháp mẫu `fixtures/agents/villa-concierge/commands.toml` · `tests/test_models.py` |
| **TSK-S2-09** | Giao diện web `sim`: cảm biến ảo, trạng thái actuator — `neuroedge run --ui` | FR-TGT-06 | V3 | ✅ Hoàn thành (2026-09-23) | [`sim/ui.py`](../python/neuroedge/sim/ui.py) — `run --ui`: trang cục bộ 127.0.0.1, SSE, không mạng, từ chối POST khác nguồn; commit `8a023f3` · `pytest tests/test_sim_ui.py` |
| **TSK-S2-11** | **Lớp trừu tượng nhà cung cấp** (CR-1.0): hợp đồng OpenAI-compatible + adapter tùy chỉnh sau `neuroedge.models.providers`; LiteLLM làm SDK qua extra `neuroedge[cloud]` (Q-10); kiểm giấy phép bắc cầu trong CI (Q-11); vòng tool của System 2 với provider thật (FR-MDL-11, `docs/spec/tool_calling.md`; vòng và MCP host trên `sim`: TSK-S3-28). **Phạm vi giao: LLM của System 2** (Q-28). Hoãn: ASR/TTS (TSK-S3-13, S5-06), provider cloud cho SystemOne và failover khai trong `agent.toml` ([`TODOS.md`](../TODOS.md) #27; failover khai trong cấu hình: TSK-K2-02) | FR-MDL-06, FR-MDL-07, FR-MDL-08, FR-MDL-11, FR-GW-01, FR-GW-03 | V1 | ✅ Hoàn thành (2026-09-24) | `python/neuroedge/models/providers/` (`LiteLLMProvider`, adapter `python:pkg.mod:factory`, bảng `[system_two]`) · `python/pyproject.toml` (extra `cloud = litellm==1.102.0`) · job CI `cloud-extra` (`scripts/check_licences.py`, `scripts/cloud_smoke.py` trên litellm thật) · `scripts/live_llm_smoke.py` (chạy tay) · `pytest tests/test_providers.py` · PR `feat/litellm-provider` |
| **TSK-S2-12** | **Đặc tả ngữ nghĩa quyết định:** trình biên dịch phía host `import parse_constraint` (không sửa `constraints.py`, không RFC) → cây quyết định mang `criteria_order` + `gate_digest`; `evaluate()` đi cây, trả phán quyết + `reason`. **Định dạng nội bộ, chưa đóng băng** — đóng băng ở RFC-0003 (Sprint 4) | FR-GATE-03, FR-ACE-01, FR-TGT-04 | V1 | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/engine/decision_tree.py` · `decision_tree.v1.json` (nội bộ) · bảng sự thật `fixtures/decision_trees/*.truth.json` (sinh bằng `scripts/generate_truth_tables.py`) · `tests/test_decision_tree.py` |
| **TSK-S2-13** | **Kế thừa `budget`/`on_block`** (RFC-0004, **Q-18**): `p95_latency_ms` của con ≤ cha · chuỗi đã `closed` thì con không khai `fail: open` · con không tự đưa vào `degrade`/`fallback_action` mới. Vi phạm ⇒ `GateInheritanceError`. Đóng lỗ `lax-night` (ENG-A2) | FR-GATE-06, FR-GATE-07, FR-GATE-09 | V1 | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/engine/gate_resolver.py` · fixture phản chứng tại `fixtures/gates/invalid/` + `expected_errors.yaml` · test `test_rfc0004_*` · commit `87890c8` |

- [x] **Tiêu chí 1:** Agent mẫu chạy trên `sim`, gate chặn đúng theo `allow_when`.
  *Bằng chứng:* `pytest tests/test_compiler.py -k sample_agent_runs` — agent `fixtures/agents/villa-concierge/` qua `c.do()` trên `SimHAL`: ALLOW ⇒ `door_lock` kích 30 000 ms, `risk_level: high` ⇒ `never_pulsed()`.
- [x] **Tiêu chí 2:** Gọi trực tiếp hành động vật lý ném `ActionContractViolation`, chân GPIO ảo không kích.
  *Bằng chứng:* `pytest tests/test_actions.py -k direct` — `test_a_direct_call_is_a_contract_violation_naming_the_caller` (NE1001 nêu `file:line` nơi gọi, `never_pulsed()`).
- [x] **Tiêu chí 3 (Q-14):** Kịch bản mất mạng → gate **vẫn lượng giá** bằng bộ nhận diện lệnh cố định cục bộ; câu không khớp ngữ pháp hoặc độ tin cậy dưới ngưỡng → BLOCK theo tiêu chí bình thường; fallback không có / không chạy được → hành động bị chặn với lý do `gate_unreachable`.
  *Bằng chứng:* `pytest tests/test_models.py -k offline` — `test_offline_a_known_command_is_still_adjudicated`, `test_offline_an_unknown_command_blocks_by_normal_criteria`, `test_offline_without_a_fallback_is_gate_unreachable`, `test_a_fallback_that_fails_at_run_time_is_gate_unreachable`; chạy khi socket bị chặn (`test_the_offline_path_opens_no_socket`).
- [x] **Tiêu chí 4:** Gate con nới lỏng `allow_when` bị từ chối phân giải.
  *Bằng chứng (ĐÃ ĐÓNG ở Sprint 1):* [`test_gate_resolver.py`](../python/tests/test_gate_resolver.py) + fixture nới `allow_when` (`loosens_choice`, `loosens_confidence`, `loosens_level`, `loosens_via_not_in`) tại [`fixtures/gates/invalid/`](../fixtures/gates/invalid/).
- [x] **Tiêu chí 5:** Quyết định Q-3, Q-7 đã chốt.
  *Bằng chứng (ĐÃ THOẢ SẴN):* Q-3 và Q-7 tại §10.1 của tài liệu này và `neuroedge-prd.md` §15.
- [x] **Tiêu chí 6:** Đổi nhà cung cấp mô hình chỉ bằng thay đổi cấu hình, không sửa mã agent và không sửa gate; một adapter tùy chỉnh mẫu chạy được mà không sửa lõi.
  *Bằng chứng (2026-09-24):* agent `home-voice` không đổi mã hay gate, chỉ thêm `[system_two]` — `pytest tests/test_providers.py -k "light_on_through_the_gate or custom_adapter"`: LiteLLM (`anthropic/claude-sonnet-5`) gọi `light_on` → ALLOW → chân bật; adapter viết ngoài lõi (`provider = "python:my_llm.echo:make_provider"`) trả lời mà không import gì từ NeuroEdge. Trên litellm 1.102.0 thật: job CI `cloud-extra` (`python scripts/cloud_smoke.py`). Phạm vi là System 2; SystemOne vẫn chạy ngữ pháp cục bộ (`TODOS.md` #27).

#### Nguồn: Sprint 3 — Action CI và `linux`

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S3-01** | Record: ghi phiên ra tệp JSON hợp lệ | FR-CI-01 | V1 | ✅ Hoàn thành (2026-09-23) | [`testing/recorder.py`](../python/neuroedge/testing/recorder.py) · `neuroedge record`; commit `f4f104e`, PR #13 |
| **TSK-S3-02** | Replay trên `sim` và `linux` *(`esp32s3`: TSK-S4-04)* | FR-CI-02 | V1 | ✅ Hoàn thành (2026-09-23) | [`testing/player.py`](../python/neuroedge/testing/player.py) · `neuroedge replay` thực thi; commit `38a5db5`, PR #13 |
| **TSK-S3-03** | Thư viện assert: chặn, gate nào, leo thang, chân cấm kích | FR-CI-03 | V1 | ✅ Hoàn thành (2026-09-23) | [`testing/assertions.py`](../python/neuroedge/testing/assertions.py) · `neuroedge test`; commit `89b5bd4`, PR #13 |
| **TSK-S3-04** | Golden Reference và so khớp chuỗi phán quyết | FR-CI-04 | V1 | ✅ Hoàn thành (2026-09-23) | [`testing/golden.py`](../python/neuroedge/testing/golden.py) — so quyết định, bỏ qua timing; commit `cb4fe26`, PR #13 |
| **TSK-S3-05** | Hiện thực HAL cho target `linux` qua `gpiod`; CI dùng **`gpio-sim`** (kernel ≥ 5.19, configfs), **1 RPi 5** làm nightly phần cứng và phương án B; **ném lỗi** khi không có `/dev/gpiochip*`, không no-op (Q-16) — **chỉ `digital.out`**; `sensor.read`/`display`: TSK-S5-09; âm thanh: TSK-S5-08 | FR-TGT-02 | **V2** *(ENG-T3)* | ✅ Hoàn thành (2026-09-23) | [`hal/linux.py`](../python/neuroedge/hal/linux.py) · [`scripts/setup_gpio_sim.sh`](../scripts/setup_gpio_sim.sh) · job CI `linux-hal` (gpio-sim trên runner GitHub, kernel 6.17 azure + `linux-modules-extra`); PR #13 |
| **TSK-S3-06** | Vỏ CLI + `--help` + **hợp đồng mã thoát** cho `new`, `run`, `build`, `test`, `record`, `replay`, `trace validate`; nối engine theo từng tuần khi A1/A2 xong | FR-CLI-01→04, FR-CLI-06, FR-TRC-08 | V3 | ✅ Hoàn thành (2026-09-23) | Cả 7 lệnh có engine: `run` (commit `190b241`), `record` / `replay` / `test` (PR #13). Phiên tương tác trên `linux` có từ TSK-S5-10 (2026-09-25) |
| **TSK-S3-07** | Scaffold `neuroedge new` có sẵn action, gate, test — **không dùng `copier`** (tránh GPL3 `jinja2-ansible-filters`) | FR-DX-01 | V3 | ✅ Hoàn thành (2026-09-23) | [`python/neuroedge/templates/`](../python/neuroedge/templates/) — mẫu `minimal`, `villa-concierge`; commit `e03e206` · `pytest tests/test_cli_new.py` |
| **TSK-S3-12** | Pipeline CI mẫu chạy `sim` + `linux` trên mỗi PR | FR-CI-05 | V1 | ✅ Hoàn thành (2026-09-23) | [`ci-sim-linux.yml`](../.github/workflows/ci-sim-linux.yml): job `linux-hal` dựng gpio-sim, chạy `tests_linux/` và `verify --targets sim,linux`; PR #13 |
| **TSK-S3-16** | **Cổng CI `digests.lock`:** khoá digest của `gates/**` + `fixtures/gates/valid/**` + `fixtures/gates/registry/**`; phân biệt *digest mới* với *digest đổi* (cần RFC) | FR-GATE-01, FR-GOV-02, FR-CI-05 | **V3** *(ENG-T3)* | ✅ Hoàn thành (2026-09-24) | [`digests.lock`](../digests.lock) (digest JCS của YAML đã parse) · [`scripts/check_digests.py`](../scripts/check_digests.py) `--check` trong job CI Frozen artifacts · `pytest tests/test_digests_lock.py` (mới / đổi / xoá, `--accept` thiếu RFC bị từ chối, đổi định dạng không tính) · PR `feat/ci-gates` |
| **TSK-S3-17** | **Đóng gói asset vào wheel:** lược đồ, bo mạch, gate, vết ghi chuẩn mực, agent mẫu; `paths.py` đọc từ gói; `repo_root()` ném lỗi 3 thành phần nêu `NEUROEDGE_ROOT`. *Mở rộng 2026-09-23: đo được wheel cài từ pip gãy ở `build`/`run`/`test`* | FR-DX-02, FR-DX-04 | **V3** *(ENG-T3)* | ✅ Hoàn thành (2026-09-23) | [`python/hatch_build.py`](../python/hatch_build.py) — wheel mang `schemas/`, `boards/`, `gates/`, `fixtures/traces/`, `fixtures/agents/` trong `neuroedge/_data/` (cả khi build từ sdist); [`paths.py`](../python/neuroedge/paths.py) báo lỗi 3 thành phần thay vì đoán; job CI `wheel-smoke` chạy cả hành trình trên bản đã cài ([`scripts/wheel_smoke.sh`](../scripts/wheel_smoke.sh)); commit `6e2d5f9` |
| **TSK-S3-18** | **`neuroedge gate explain`:** giải thích gate đã phân giải cho người duyệt không đọc mã (J6) | FR-GATE-01, FR-CLI-05 | **V3** *(ENG-T3)* | ✅ Hoàn thành (2026-09-23) | [`engine/gate_explain.py`](../python/neuroedge/engine/gate_explain.py) + [`cli/explain.py`](../python/neuroedge/cli/explain.py); commit `d80964e` · `pytest tests/test_cli_explain.py` |
| **TSK-S3-19** | **`verify` đếm artifact, ném khi = 0** (lỗi 3 thành phần) + test phản chứng cây rỗng | FR-CI-07, FR-CLI-06, FR-DX-04 | **V3** *(ENG-T3)* | ✅ Hoàn thành (2026-09-24) | `verify` in số gate / vết ghi / replay; loại nào bằng 0 hoặc thiếu thư mục ⇒ `VerificationError` (NE4004), mã 1 · `pytest tests/test_cli.py -k verify` (cây rỗng, có gate mà không có vết ghi, không target) · PR `feat/ci-gates` |
| **TSK-S3-20** | **`README.md` gốc** một màn hình, thành trang PyPI; liên kết tuyệt đối, không hướng dẫn cài editable | FR-DX-02, FR-DX-05 | **V3** *(ENG-T3)* | ✅ Hoàn thành (2026-09-24) | [`README.md`](../README.md) — ba lệnh cài → `new --template home-voice` → `mcp desktop-config --write`, link tuyệt đối; là trang PyPI qua `ReadmeHook` trong [`hatch_build.py`](../python/hatch_build.py) · `pytest tests/test_readme_quickstart.py tests/test_packaging.py` · `wheel_smoke.sh` chạy các lệnh đó trên wheel đã cài |
| **TSK-S3-22** | **`neuroedge trace view`** — một tệp HTML tĩnh: dòng thời gian, phán quyết + lý do, chân, cảm biến, khung màn hình; mở không cần mạng. Kèm `trace export --format chrome` cho Perfetto *(Q-21)* | FR-CLI-04, FR-DX-04 | V3 | ✅ Hoàn thành (2026-09-23) | [`viz/`](../python/neuroedge/viz/) — `trace view` (HTML tự chứa, thanh tua thời gian), `trace export --format chrome`; commit `650a517` · `pytest tests/test_trace_view.py` |
| **TSK-S3-23** | **`sensor.read` và `display` trên `sim` đủ đường:** `[sim.sensors]` trong `agent.toml`, `:sensor` trong REPL, sự kiện `sensor_read` / `display_frame` (digest + PNG), replay cấp lại giá trị cảm biến đã ghi *(Q-21)* | FR-TGT-01, FR-TGT-06, FR-CI-02 | V3 | ✅ Hoàn thành (2026-09-23) | `hal/sim.py`, `hal/sensor.py`, `hal/display.py`, `sim/session.py`; commit `b3c118e` · `pytest tests/test_sim_sensors_display.py` |
| **TSK-S3-24** | **Corpus tuân thủ Gated Tool Profile:** `fixtures/tool_calls/{valid,invalid}/` + `expected_results.yaml` khép kín hai chiều; `outputSchema` cho mỗi tool MCP; trường `fallback` trong kết quả `degrade` | FR-MDL-10, FR-ACE-09 | V1 | ✅ Hoàn thành (2026-09-24) | `fixtures/tool_calls/` (`valid/`, `invalid/`; agent mới `fixtures/agents/driveway/`) · runner [`testing/tool_corpus.py`](../python/neuroedge/testing/tool_corpus.py), chạy trong `neuroedge verify` · `result_schema()` là `outputSchema` (`actions/tools.py`) · `pytest tests/test_tool_corpus.py` (mỗi ca cả qua client MCP thật) · `docs/spec/tool_calling.md` §4, §9 |
| **TSK-S3-25** | **Hiện thực RFC-0005** — khối `arguments:` trong gate: resolver (kế thừa chỉ thu hẹp), `gate lint`, compiler (nút tham số), giới hạn đi vào `inputSchema`. **Phải xong trước TSK-S4-02** | FR-ACE-08, FR-GATE-06 | V1 | ✅ Hoàn thành (2026-09-24) | `python/neuroedge/engine/arguments.py` · `pytest tests/test_gate_arguments.py` · corpus `fixtures/gates/invalid/` (mục mới) |
| **TSK-S3-26** | **Vòng xác nhận `ask` (Q-26) trên `sim`:** REPL và UI hỏi lại, sự kiện `tool_confirm_requested` / `tool_confirmed`, TTL, dùng một lần; gate lượng giá lại, chỉ thay tiêu chí trong `on_block.confirms` (RFC-0006) | FR-ACE-10 | V3 | ✅ Hoàn thành (2026-09-24) | `python/neuroedge/actions/confirmation.py` · `pytest tests/test_tool_confirm.py` · RFC-0006 |
| **TSK-S3-27** | **`neuroedge mcp serve --ui`:** máy chủ MCP và giao diện web `sim` chung một phiên — điều khiển từ Claude Desktop, thấy đèn/chốt ảo đổi và gate chặn | FR-CLI-12, FR-DX-04 | V3 | ✅ Hoàn thành (2026-09-24) | `python/neuroedge/mcp_server.py` (móc `lock`/`on_change`), `sim/ui.py`, `viz/` · `pytest tests/test_mcp_serve_ui.py` · cấu hình Desktop: `neuroedge mcp desktop-config` (`mcp_desktop.py`), khởi động như Desktop — `cwd=/`, `PATH` tối giản — ở `pytest tests/test_mcp_desktop.py`; lỗi tiến trình mồ côi giữ cổng lộ ra ở lần thử đầu: `CHANGELOG.md` *Đã sửa* · **Desktop thật: ✅ 2026-09-24** (macOS, Claude Desktop 2.7032.0, mục do `mcp desktop-config --ui --write` ghi, mã ở `5b8bc11`): gõ "bật đèn lên" ⇒ Desktop gọi `light_on` ⇒ `{"tool":"light_on","status":"ALLOW"}`; `/state` của cùng phiên có `tool_call {light_on, source: mcp}` rồi `actuator_command {porch_light, on}`; các tiến trình Desktop mở thêm ghi `warning: sim UI port 8765 is taken` rồi vẫn phục vụ ở cổng trống, không còn tiến trình mồ côi |
| **TSK-S3-28** | **System 2 làm MCP host (Q-27):** `ToolHost` — tool thiết bị qua MCP server của chính agent, MCP server bên ngoài từ `[mcp.servers]` (allowlist, digest trong vết ghi), vòng ReAct `max_rounds`; `mcp tools --external`; tin tức home-voice qua `mcp/news_server.py` | FR-MDL-11, FR-MDL-12 | V1 | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/mcp_host.py` · `pytest tests/test_mcp_host.py` |

- [x] **Tiêu chí 2 (A2):** `neuroedge verify --targets sim,linux` đạt 100%.
  *Bằng chứng:* job CI `linux-hal` (PR #13) — ba vết ghi chuẩn mực replay trên `SimHAL` và `LinuxHAL` (gpio-sim) cho cùng phán quyết (ALLOW · BLOCK · BLOCK) và cùng lệnh chân, khớp golden; `tests_linux/test_gpio_sim.py` xanh. So quyết định, chưa so timing (TSK-S4-04).
- [x] **Tiêu chí 3 (A3):** Không tồn tại đường tắt kích hoạt GPIO bỏ qua gate.
  *Bằng chứng:* `docs/spec/threat_model.md` §2 liệt kê mọi đường tắt và test chặn nó — `test_no_path_reaches_a_pin_without_a_valid_token`, `test_a_hal_without_a_ledger_refuses_every_command`, các test `token_replayed` / `token_expired` trong `tests/test_actions.py`.
- [x] **Tiêu chí 4 (A4):** 100% kịch bản suy giảm đều chặn hành động.
  *Bằng chứng:* `pytest tests/test_fail_closed.py` — ma trận kịch bản suy giảm × gate mẫu + thiếu độ tin cậy + gate không tồn tại: mọi ô BLOCK và `never_pulsed()`; mất mạng có fallback chạy được thì lượng giá bình thường (Q-14).
- [x] **Tiêu chí 5 (A5):** Bộ kiểm thử kế thừa gate đạt 100%.
  *Bằng chứng (ĐÃ ĐÓNG ở Sprint 1):* [`test_gate_resolver.py`](../python/tests/test_gate_resolver.py) + [`test_sample_gates.py`](../python/tests/test_sample_gates.py) + corpus `fixtures/gates/invalid/`; `neuroedge gate lint` xanh. TSK-S2-13 mở rộng bộ này cho `budget`/`on_block` (Q-18) và phải giữ 100%.
- [x] **Tiêu chí 6 (A7):** 100% phiên sinh vết ghi qua được `neuroedge trace validate`.
  *Bằng chứng:* mọi đường ghi (`record`, `run --trace-out`, `replay --trace-out`) thẩm định theo `trace.v1` **trước** khi ghi và từ chối ghi tệp sai — `test_a_trace_that_fails_the_schema_is_never_written`; `test_recorder.py`, `test_cli_run.py` đọc lại tệp bằng `load_trace`.

### 4.2 I1 — Preview nội bộ trên `sim`

| | |
|:---|:---|
| **Mục tiêu** | Một lập trình viên ngoài đội, cài từ wheel nội bộ, chạy được agent có gate trong dưới 10 phút, không cần phần cứng (U1/J1 → M1; đo A1 sớm) |
| **Điều kiện vào** | — |
| **Tín hiệu đo** | TTFV trung vị trên 3 người ngoài đội, đo tại chỗ — chưa phát hành ra ngoài (Q-39) |
| **Người** | V3 (chủ trì), V1 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S3-08** | Ba ví dụ mẫu chạy được, README có tài sản trực quan | FR-DX-05, FR-DX-06 | V3 | ✅ Hoàn thành (2026-09-25) | `villa-concierge`, `home-voice` ([`fixtures/agents/home-voice/`](../fixtures/agents/home-voice/): RAG knowledge base, tin tức, đèn qua gate) và `factory-monitor` ([`fixtures/agents/factory-monitor/`](../fixtures/agents/factory-monitor/): quạt, báo động qua gate đọc fact `level` — không cần tiêu chí số, `TODOS.md` #30) chạy được qua `neuroedge new --template`, có test (`tests/test_factory_monitor.py`) và nằm trong `wheel-smoke`. Tài sản trực quan cho README chuyển sang TSK-I6-03 |
| **TSK-S3-15** | **RFC golden reference:** ba vết ghi chuẩn mực khai `"target": "esp32s3"` nhưng replay ở Tiêu chí 4 chạy trên `sim`/`linux` thật; `fixtures/traces/` là RFC-gated | FR-CI-04, FR-TRC-05 | V1 | ✅ Hoàn thành (2026-09-25) — không cần RFC | TSK-S3-04 so **quyết định**, không so `metadata.target`: ba vết ghi chuẩn mực làm golden nguyên trạng trên `sim` và `linux`, không sửa `fixtures/traces/`. **Xác nhận 2026-09-25:** golden là ba vết ghi chuẩn mực nguyên trạng, so quyết định trên `sim`, `linux` và `esp32s3`; không sửa `fixtures/traces/`, không cần RFC |
| **TSK-I1-01** | **PII trong vết ghi trước khi có người ngoài dùng:** vết ghi mặc định băm chữ người dùng gõ/nói tại nguồn (`metadata.anonymized = true`); `--raw` giữ nguyên văn, bật tường minh | FR-TRC-06, FR-TRC-07, NFR-PRIV-03 | V1 | ✅ Hoàn thành (2026-09-27) — quyết định: "dữ liệu thô" của NFR-PRIV-03 gồm cả chữ | `python/neuroedge/testing/recorder.py` (`DEFAULT_ANONYMIZE`) · `cli/main.py` (`--raw` trên `record`, `run`, `replay`, `mcp serve`, `mcp desktop-config`) · *Bằng chứng:* `pytest tests/test_recorder.py tests/test_uart_trace.py tests/test_voice_cli.py tests/test_cli_run.py tests/test_golden.py` |
| **TSK-I1-02** | **Bộ đo TTFV tại chỗ:** kịch bản buổi đo, wheel nội bộ, biểu mẫu mốc thời gian từng bước; 3 người ngoài đội cho M1, 10 người cho A1 (TSK-I7-02) | FR-DX-01 | V3 | ⏸ Tạm hoãn (2026-09-26) — cùng lý do với TSK-I1-01 | `docs/reports/` — biên bản đo, không ghi danh tính người đo |
| **TSK-I1-03** | **`--help` có ví dụ cho mọi lệnh; scaffold tạo sẵn `traces/`** | FR-CLI-07, FR-TRC-09 | V3 | ✅ Hoàn thành (2026-09-26) | [`cli/examples.py`](../python/neuroedge/cli/examples.py): mỗi lệnh có mục `Examples:`, mọi ví dụ phân tích bằng parser thật và chạy trong dự án vừa tạo · [`templates/_common/traces/`](../python/neuroedge/templates/_common/traces/) · kiểm: `pytest tests/test_cli_examples.py tests/test_cli_new.py`, `scripts/wheel_smoke.sh` |
| **TSK-I1-04** | **NeuroEdge Studio:** `neuroedge studio` — ứng dụng web cục bộ (127.0.0.1, không CDN, song ngữ Việt/Anh) thể hiện mọi năng lực trên laptop: phiên trực tiếp gõ và nói, gate + thử nhanh, vết ghi + replay, verify, thiết bị ESP32-S3 (LVGL, QEMU, OTA), MCP, cấu hình agent (Q-51) | FR-TGT-06, FR-DX-06 | V3 | 🟡 Xong phần mã (2026-09-29): 17 API của `docs/spec/studio.md`, bảy màn song ngữ, kiểm trên trình duyệt (sáng/tối, 1280/390 px, VI/EN); `--mic` qua `StudioVoice`, kiểm bằng nguồn giả. **Còn:** chạy `studio --mic` với micro thật trên máy trình bày | [`python/neuroedge/studio/`](../python/neuroedge/studio/) · [`demo/i1-studio/`](../demo/i1-studio/) · kiểm: `pytest tests/test_studio_server.py tests/test_studio_api_agent.py tests/test_studio_api_checks.py tests/test_studio_api_device.py tests/test_studio_voice.py tests/test_studio_page.py` |

**Tiêu chí ra I1:**

- [ ] **Tiêu chí 1 (M1):** TTFV đo tại chỗ trên **3 người ngoài đội**, cài từ wheel của tag `v0.1.0`, đạt trung vị dưới 10 phút; biên bản ở `docs/reports/`. A1 đầy đủ (10 người, cài từ PyPI) đo ở I7 (TSK-I7-02).
- [x] **Tiêu chí 2:** Mẫu thứ ba chạy được qua `neuroedge new --template`, có test và nằm trong `wheel-smoke` (TSK-S3-08).
- [x] **Tiêu chí 3:** TSK-S3-15 đóng: golden là ba vết ghi chuẩn mực, hoặc một RFC được mở.
  *Bằng chứng:* xác nhận 2026-09-25 — golden là ba vết ghi chuẩn mực nguyên trạng, không cần RFC (dòng TSK-S3-15); `pytest tests/test_trace_vectors.py -k golden` và job `linux-hal` so quyết định trên ba target.
- [x] **Tiêu chí 4:** Vết ghi của buổi đo không chứa chữ thô của người dùng khi chưa bật tường minh (TSK-I1-01).
  *Bằng chứng:* mặc định băm tại nguồn từ 2026-09-27; `pytest tests/test_recorder.py -k default`.
- [ ] **Tiêu chí 5:** Tag `v0.1.0` có GitHub Release nội bộ kèm wheel; `scripts/wheel_smoke.sh --wheel` xanh trên đúng wheel đó.

### 4.3 I2 — `linux` ngang `sim`

| | |
|:---|:---|
| **Mục tiêu** | Cùng agent chạy tương tác trên `linux` như trên `sim`: REPL, `record`, `mcp serve`; cảm biến và màn hình; hồ sơ `linux-rpi5` chỉ khai những gì HAL chạy được (U2/J3 → A2 một phần) |
| **Điều kiện vào** | 1 RPi 5 cho nightly (Phụ lục B) |
| **Tín hiệu đo** | Phiên tương tác trên gpio-sim; nightly RPi 5 xanh |
| **Người** | V3 (TSK-S5-10), V1 (TSK-S5-09, TSK-I2-01) |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S5-09** | **`sensor.read` và `display` trên `linux`:** cảm biến qua sysfs hwmon + IIO; CI dùng `i2c-stub` + `lm75` (IIO chỉ trên Pi); màn hình ghi `/dev/fb*` trên Pi, khung trong bộ nhớ + digest trong CI | FR-TGT-02, FR-HAL-01 | V1 | ✅ Hoàn thành (2026-09-26) — IIO chỉ kiểm trên cây sysfs giả; Pi thật chưa chạy | [`hal/sysfs.py`](../python/neuroedge/hal/sysfs.py) · [`hal/framebuffer.py`](../python/neuroedge/hal/framebuffer.py) · [`hal/linux.py`](../python/neuroedge/hal/linux.py) · [`setup_i2c_stub.sh`](../scripts/setup_i2c_stub.sh) · [`setup_vfb.sh`](../scripts/setup_vfb.sh) · kiểm: `pytest tests/test_hal_linux_io.py`; `tests_linux/test_sensor_display.py` (job `linux-hal`) |
| **TSK-S5-10** | **Phiên tương tác trên `linux`:** `run` (REPL và `-c`), `record` và `mcp serve --target linux` trên `LinuxHAL` (gpio-sim trong CI, RPi 5 hằng đêm), cùng hợp đồng mã thoát như `sim`; thoại trên `linux` là TSK-S5-08 (I4) | FR-CLI-02, FR-TGT-02 | V3 | ✅ Hoàn thành (2026-09-25) — `tests_linux/` 13/13 và `verify --targets sim,linux` xanh trên gpio-sim (job `linux-hal`) | `TypedLinuxHAL` ([`hal/linux.py`](../python/neuroedge/hal/linux.py)) · `SimSession.load(target=)` · [`cli/main.py`](../python/neuroedge/cli/main.py) · [`test_session_linux.py`](../python/tests/test_session_linux.py) · `tests_linux/` (gpio-sim, job `linux-hal`). Agent chỉ được cần `digital.out` (`audio.*`: TSK-S5-08, `sensor.read`/`display`: TSK-S5-09); `--ui` trên `linux` ⇒ mã 2; RPi 5 hằng đêm chưa chạy |
| **TSK-I2-01** | **Nightly `linux` trên RPi 5** (Q-16): `tests_linux/` và `verify --targets linux` trên phần cứng thật | FR-CI-06, FR-TGT-02 | V1 | ⏳ Chưa bắt đầu | `.github/workflows/nightly-hardware.yml` · runner tự quản |
| **TSK-W0-04** | **Trôi phụ thuộc hằng đêm tự mở issue, không chặn build** (Q-32) | — | V3 | ✅ Hoàn thành (2026-09-26) | [`nightly-hardware.yml`](../.github/workflows/nightly-hardware.yml) (`upstream-drift`, `drift-issue`; nhãn `dependency-drift`, issue #54) |

**Tiêu chí ra I2:**

- [x] **Tiêu chí 1:** `run --target linux` (REPL và `-c`), `record --target linux` và `mcp serve --target linux` chạy trên gpio-sim trong CI, cùng hợp đồng mã thoát như `sim`.
- [ ] **Tiêu chí 2:** `sensor.read` và `display` trên `linux` có test trong `tests_linux/`; mọi nguyên thủy mà `boards/linux-rpi5.toml` khai đều chạy được trên HAL, hoặc bị gỡ khỏi hồ sơ cho tới task hiện thực nó.
- [x] **Tiêu chí 3:** `neuroedge verify --targets sim,linux` vẫn đạt 100%.
- [ ] **Tiêu chí 4:** Nightly trên RPi 5 chạy `tests_linux/` và `verify --targets linux` trên phần cứng thật (TSK-I2-01).

### 4.3.1 I2a — Nguyên thủy mở rộng trên `sim` và `linux`

| | |
|:---|:---|
| **Mục tiêu** | Đủ bốn gói nguyên thủy mở rộng — cảm biến, điều khiển mịn, thị giác, chuyển động — chạy trên `sim` và `linux`, với ngữ nghĩa gate chạy được trên cả ba target (Q-52, Q-53) |
| **Điều kiện vào** | — (RFC mở ngay; mã của từng gói chờ RFC của gói đó được chấp thuận, §2.3) |
| **Tín hiệu đo** | Tiêu chí ra bên dưới |
| **Người** | V1 (chủ trì), V5 (thị giác), V2 (RFC-motion), kỹ thuật trưởng (sáu RFC) |
| **Thiết kế** | [`neuroedge-design-phase2.md`](neuroedge-design-phase2.md) §6 (thị giác) · [`draft-ke-hoach-mo-rong-robot-fofoca.md`](draft-ke-hoach-mo-rong-robot-fofoca.md) §7 (PWM, `numeric`, `motion.*`) · [`neuroedge-design-neurobrain.md`](neuroedge-design-neurobrain.md) §7–§8 (phong bì, I2C) · RFC-0007, RFC-0009 → RFC-0013 |

#### Quản trị và RFC

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I2a-01** | **Ước lượng lại phạm vi MVP (Q-52):** đếm lại task I2a → I7, đặt ngày dự báo cho I2a, I2b, I3a, I4a, I5a, I6, I7 và I8 kèm bằng chứng (R5); cập nhật §1.3 và §2.2 | — | trưởng nhóm + kỹ thuật trưởng | ✅ Hoàn thành (2026-09-30) — v1.0 dự báo 2027-02-21 | [`docs/reports/uoc-luong-mvp-2026-09-30.md`](../docs/reports/uoc-luong-mvp-2026-09-30.md) · §0.2 |
| **TSK-N0-02** | Sửa đổi FR-HAL-01: nguyên thủy mở rộng (`digital.in`, bus I2C, `analog.in`, PWM, `motion.*`, `vision.in`) là **tuỳ chọn theo bo mạch** (RFC-0013, Q-53); sửa FR-CLI-12 cho `mcp desktop-config --lab` | FR-HAL-01, FR-CLI-12 | V2 | ✅ Hoàn thành (2026-10-03) — FR-HAL-01 tách lõi/mở rộng theo RFC-0013 §3a; `--lab` vào FR-CLI-12 (hiện thực ở TSK-N1-05). | `neuroedge-prd.md` FR-HAL-01, FR-CLI-12 |
| **TSK-N0-03** | RFC-0007: `digital.in`; bus I2C chỉ đọc; `analog.in` (ADC theo spike TSK-N3-03 — chuyển từ RFC-motion sang, Q-53); trường bus/địa chỉ và khai báo phong bì trong `board.v1`. Phải lý giải vì sao không mở rộng `sensor.read`. `gate.v1` không đổi | FR-HAL-01 | V2 | ✅ Hoàn thành (2026-10-01) — RFC-0007 chấp thuận, PR #75 | `docs/rfc/0007-digital-in-i2c-analog-in-phong-bi.md` |
| **TSK-I2a-07** | **RFC-0013:** nguyên thủy mở rộng tuỳ chọn theo bo mạch; nhiều bo tham chiếu cho một target bậc 1; mỗi nguyên thủy mở rộng có ít nhất một bo tham chiếu trên **mỗi** target bậc 1 (Q-53) | FR-HAL-01, FR-TGT-08 | V1 + kỹ thuật trưởng | 🟡 RFC-0013 chấp thuận (2026-10-01, PR #80); phần host đã hiện thực (2026-10-04): `REFERENCE_BOARDS`, `EXTENSION_REFERENCE_BOARDS`, `SIM_MIRRORS`; `build` không `--board` nêu các bo hợp; `verify` một cột mỗi (target, bo). **Còn:** các ô `esp32s3` của bảng phủ (`esp32s3-cores3` và nguyên thủy mở rộng trên Box-3 cần số liệu phần cứng — TSK-I3a-01) và một job nightly mỗi bo thật | `docs/rfc/0013-nguyen-thuy-tuy-chon-va-nhieu-bo-tham-chieu.md` · [`hal/board.py`](../python/neuroedge/hal/board.py) · [`cli/main.py`](../python/neuroedge/cli/main.py) (`build`, `verify`) · commit `33b6523`, `0b239d2` · kiểm: `pytest tests/test_boards.py tests/test_cli.py -k "tier1 or reference_board"` (`test_every_extension_primitive_on_every_tier1_target` ghim đúng khoảng trống `esp32s3`: nó đỏ ngày một ô được lấp) |
| **TSK-I2a-06** | **Profile `sim-rpi5`** soi đúng `linux-rpi5` (có đủ nguyên thủy mở rộng, kể cả camera); phát biểu lại bất biến "`sim` không giàu hơn bo tham chiếu" theo từng bo (đóng `TODOS.md` #14) | FR-TGT-01, FR-TGT-06 | V1 | ✅ Hoàn thành (2026-10-04) — `boards/sim-rpi5.toml` soi `linux-rpi5` (có đủ nguyên thủy mở rộng, kể cả camera); bất biến "`sim` không giàu hơn bo nó soi" kiểm theo từng bo qua `SIM_MIRRORS`; đóng `TODOS.md` #14 | `boards/sim-rpi5.toml` · [`hal/board.py`](../python/neuroedge/hal/board.py) (`SIM_MIRRORS`) · commit `33b6523` · kiểm: `pytest tests/test_boards.py tests/test_board_fixtures.py` (`test_a_sim_profile_is_never_richer_than_the_board_it_mirrors`, `test_the_mirror_invariant_is_red_when_a_sim_profile_is_richer`; corpus `fixtures/boards/`, 74 tệp, đóng hai chiều) |

#### Gói cảm biến

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-W1-02** | **Tiêu chí `numeric`** cho `sensor.read` kiểu số: `gate.v1`, nút `NETR`, walker C, corpus (`TODOS.md` #30) | FR-GATE-03, FR-HAL-01 | V1 | ✅ Hoàn thành (2026-10-03) — ngôn ngữ, engine, vết ghi, replay, `NETR` v2, walker C; nối với kênh `analog.in` / `feedback` thuộc TSK-I2a-04 và RFC-0010 | [`engine/constraints.py`](../python/neuroedge/engine/constraints.py) · [`ne_walker.c`](../targets/esp32s3/components/ne_gate/src/ne_walker.c) · kiểm: `pytest tests/test_numeric_*.py tests/test_c_walker.py` |
| **TSK-I2a-02** | **`digital.in` trên `sim` và `linux`** (sau RFC-0007): `LinuxHAL` đọc line qua gpiod (gpio-sim trong CI), `SimHAL` đổi mức trong REPL và trang `--ui`; mức logic vào gate như dữ kiện, có vết ghi | FR-HAL-01 | V1 | ✅ Hoàn thành (2026-10-04) — `sim`; `linux` với gpiod giả; và trên kernel (gpio-sim): mức đặt qua điện trở kéo là dữ kiện gate (ALLOW rồi BLOCK theo mức), line được xin là đầu vào và không bao giờ bị lái, đọc hỏng ⇒ BLOCK `criterion_unavailable`, chân bo mạch không khai là đầu vào bị từ chối trước khi chạm line. Bằng chứng: CI run 37153005998 (job `linux-hal`): `pytest tests_linux` 90 passed; `neuroedge verify --targets sim,linux` | [`hal/__init__.py`](../python/neuroedge/hal/__init__.py) (`digital_in`) · `hal/sim.py` · `hal/linux.py` · `engine/compiler.py` (`[requires] "digital.in"`) · `sim/session.py` (`[sim.digital_facts]`) · commit `f67885c`, `83635e2` · kiểm: `pytest tests/test_digital_in.py tests/test_digital_in_linux.py` (`test_an_input_nobody_set_is_a_failed_read_not_a_level`) · `tests_linux/test_gpio_sim.py` (job `linux-hal`: `test_a_level_set_through_gpio_sim_is_a_gate_fact_that_allows_and_blocks`, `test_an_input_line_reads_the_level_the_kernel_holds`, `test_an_input_line_is_requested_as_an_input_and_never_driven`, `test_an_input_line_that_cannot_be_read_blocks_criterion_unavailable`, `test_a_pin_the_board_does_not_declare_as_an_input_is_refused_and_no_line_is_touched`) |
| **TSK-I2a-03** | **Bus I2C chỉ đọc cho agent** (sau RFC-0007): `linux` đọc thanh ghi của thiết bị trong allow-list của bo mạch, không ghi; `sim` chỉ phát lại từ vết ghi; test trên `i2c-stub` | FR-HAL-01 | V1 | ✅ Hoàn thành (2026-10-04) — `sim` (phát lại từ `[sim.i2c]`); `linux` với `/dev/i2c-N` giả; và trên `i2c-stub` của kernel: đọc thanh ghi khai trả đúng giá trị chip giữ, quét chỉ liệt kê chip ngoài allow-list (`lm75` 0x48) và đọc nó bị từ chối, thanh ghi không khai không phát giao dịch (con trỏ thanh ghi của chip không dời), thiết bị không trả lời hoặc nút bus mất ⇒ `NE5001` (một lần thử lại), không bao giờ là giá trị mặc định. Bằng chứng: CI run 37153005998 (job `linux-hal`): `pytest tests_linux` 90 passed; `neuroedge verify --targets sim,linux` | [`hal/i2c_bus.py`](../python/neuroedge/hal/i2c_bus.py) · `hal/sim.py` · `hal/linux.py` · `engine/compiler.py` (`[requires] "i2c"`) · commit `cd1f4e4`, `ede75bc`, `a3062a6`, `3d803c2` · kiểm: `pytest tests/test_hal_i2c.py` (`test_an_undeclared_register_is_refused_with_no_transaction`) · `tests_linux/test_i2c_read.py` (job `linux-hal`: `test_a_declared_register_reads_back_what_the_chip_holds`, `test_a_device_with_no_declared_registers_answers_a_receive_byte`, `test_an_undeclared_register_sends_nothing_to_the_chip`, `test_a_scan_lists_the_unlisted_chip_and_a_read_of_it_is_refused`, `test_a_device_that_does_not_answer_is_perception_unavailable_after_one_retry`, `test_a_missing_node_is_perception_unavailable_not_a_default`) |
| **TSK-N3-03** | **Spike ADC** trên runner `ubuntu-latest`: chip ADC I2C có driver hwmon (`ads7828` hoặc `ina2xx`) trên `i2c-stub`, đọc lại `in0_input` | — | — | ✅ Hoàn thành (2026-10-03) — đạt cả hai: `ads7828` `in0_input` = 1249 mV, `ina219` `in1_input` = 12000 mV, đúng công thức datasheet; kernel `6.17.0-1022-azure` không có `CONFIG_IIO`, có `ads7828` và `ina2xx` dạng module. Chọn `ads7828` cho `analog.in` ở TSK-I2a-04; job `adc-spike` đã gỡ (2026-10-04) vì `linux-hal` khẳng định cùng số đọc qua mã sản phẩm | báo cáo spike trong PR #87 · `scripts/setup_i2c_stub.sh` (nạp `ads7828` và `ina219`) · `tests_linux/test_analog_in.py` (đọc lại 0x800 → 1249 mV qua `LinuxHAL`) |
| **TSK-I2a-04** | **`analog.in` (ADC) trên `sim` và `linux`** theo kết quả spike TSK-N3-03: giá trị có đơn vị, vào gate qua tiêu chí số (RFC-0009) | FR-HAL-01 | V1 | ✅ Hoàn thành (2026-10-04) — `sim`; `linux` với cây sysfs giả; và trên kernel (`i2c-stub` + `ads7828`): kênh có đơn vị và thang, hwmon đọc ra 1,249 V (giá trị spike), thiết bị tìm theo tên; đọc hỏng/ngoài thang/khác đơn vị/ADC vắng ⇒ `NE5001` ⇒ BLOCK `criterion_unavailable`; điện áp của kernel quyết gate và replay khớp. Bằng chứng: CI run 37153005998 (job `linux-hal`): `pytest tests_linux` 90 passed; `neuroedge verify --targets sim,linux` | [`hal/__init__.py`](../python/neuroedge/hal/__init__.py) (`analog_in`) · `hal/sim.py` · `hal/linux.py` (hwmon) · `engine/compiler.py` (`check_analog_facts`) · `sim/session.py` (`[sim.analog]`, `[sim.analog_facts]`) · commit `a9ca295`, `0f7e95a` · kiểm: `pytest tests/test_analog_in.py tests/test_hal_linux_analog.py` · `tests_linux/test_analog_in.py` (job `linux-hal`: `test_the_hal_reads_the_ads7828_through_hwmon_in_volts`, `test_the_spike_value_reads_as_1_249_volts`, `test_the_kernel_voltage_decides_the_gate_and_replays`, `test_an_adc_that_is_not_there_blocks_criterion_unavailable`, `test_a_channel_the_chip_does_not_have_is_unavailable`) · `tests_linux/test_rail_gate.py` (agent `rail-gate`) |

#### Gói điều khiển mịn

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-W1-01** | **PWM** (tần số, độ rộng xung) và kênh phản hồi trạng thái trong `digital.out` (RFC-0010) — trên `sim` và `linux`; HAL C ở TSK-I3a-03 | FR-HAL-01 | V1 + V2 | 🟡 Xong trên `sim` và trên `linux` với cây `/sys/class/pwm` giả (2026-10-04): `pwm` với `duration_ms` bắt buộc, `duty` lượng tử về 0, từ chối `on`/`pulse` trên kênh PWM trước mọi token, `state()` tách `measured` khỏi `commanded`, dây `enable` giữ bởi tiến trình giám sát. Trên kernel (gpio-sim; CI run 37153005998, job `linux-hal`): dây `enable` lên khi có lệnh PWM và xuống khi hết, `off`/`close` thả dây, runtime bị SIGSTOP hay SIGKILL mất dây. **Còn:** kênh PWM thật (CI không có bộ điều khiển PWM: `/sys/class/pwm` là cây giả; nightly Pi 5); agent mẫu `fan-pwm` chưa nằm trong corpus của `verify`; HAL C trên chip (TSK-I3a-03) | `docs/rfc/0010-pwm-trong-digital-out.md` · `hal/pwm.py` · `hal/__init__.py` · `hal/linux.py` · `engine/compiler.py` (`[requires]` pwm, `[sim.feedback_facts]`) · agent mẫu `fixtures/agents/fan-pwm/` · nhánh `feat/pwm`: commit `52731be`, `00fbae5`, `e6c3f50` · kiểm: `pytest tests/test_pwm.py tests/test_hal_linux_pwm.py` · `tests_linux/test_gpio_pwm.py` (job `linux-hal`: `test_the_enable_line_is_up_while_a_pwm_command_runs_and_down_when_it_ends`, `test_off_and_close_drop_the_enable_line`, `test_a_runtime_stopped_with_sigstop_while_the_fan_runs_loses_the_enable_line`, `test_a_runtime_that_is_killed_while_the_fan_runs_loses_the_enable_line`) |

#### Gói thị giác

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-V1b-07** | RFC nguyên thủy `vision.in`: hình dạng tham số có bằng chứng phần cứng (`fps` số thực, `modes[]`, enum `pixel_format`) và quy tắc so khớp với `[requires]` (RFC-0002 §9.1). Cần TSK-S2-02 | FR-HAL-01, FR-HAL-04 | V1 | ✅ Hoàn thành (2026-10-01) — RFC-0012 chấp thuận, PR #79 | `docs/rfc/0012-nguyen-thuy-vision-in.md` · `schemas/board.v1.json` |
| **TSK-V1b-01** | Hiện thực `vision.in` cho `linux`: luồng khung hình, độ phân giải, FPS. Cần TSK-V1b-07 | FR-HAL-01 | V5 | ✅ Hoàn thành (2026-10-04) — V4L2 bằng Python thuần (không phụ thuộc mới), chế độ khai phải là chế độ driver chạy, mất/đứng/treo ⇒ `CameraUnavailable`; giao thức kiểm bằng driver giả và trên driver `vivid` của kernel: node đúng, đúng chế độ khai (640x480 rgb888, 1280x720 yuyv; số khung của driver tăng), chế độ driver làm tròn bị từ chối, phiên `linux` đọc camera rồi gate quyết. Lần chạy đầu trên kernel bắt được lỗi số khung (đọc `sequence` sau `QBUF`; sửa ở `6bbfb43`, driver giả nay mô phỏng `QBUF` ghi đè). Bằng chứng: CI run 37153005998 (job `linux-hal`): `pytest tests_linux` 90 passed; `neuroedge verify --targets sim,linux`. Chưa thử trên camera thật (nightly Pi 5, TSK-I2-01) | [`hal/vision.py`](../python/neuroedge/hal/vision.py) · [`hal/v4l2.py`](../python/neuroedge/hal/v4l2.py) · `hal/linux.py` (`vision_in`, `NEUROEDGE_LINUX_CAMERA`) · commit `83df0dd`, `f26f426` · kiểm: `pytest tests/test_v4l2.py tests/test_vision_camera.py` · `tests_linux/test_camera_v4l2.py` (job `linux-hal`: `test_the_kernel_names_the_virtual_capture_device`, `test_the_camera_runs_exactly_the_mode_the_board_declares`, `test_a_mode_the_driver_will_round_is_refused_not_taken_as_close_enough`, `test_a_session_on_linux_reads_the_camera_and_the_gate_decides`, `test_the_camera_can_be_closed_and_opened_again`) · [`docs/spec/camera.md`](../docs/spec/camera.md) |
| **TSK-V1b-02** | Camera ảo trong `sim`: phát lại chuỗi ảnh, giữ tương đương với phần cứng thật | FR-TGT-01, FR-TGT-06 | V5 | ✅ Hoàn thành (2026-10-04) — camera ảo phát lại chuỗi khung trên đồng hồ phiên, đúng chế độ bo mạch khai, không giàu hơn bo `sim-rpi5`; hết chuỗi ⇒ mất camera; `[sim.vision]`; corpus `fixtures/traces/vision/` replay trên mọi bo khai `vision.in`; agent mẫu bị từ chối lúc build trên `sim-default` | [`sim/vision/`](../python/neuroedge/sim/vision/) · `fixtures/agents/gate-watch/` · `fixtures/traces/vision/` (`scripts/gen_vision_traces.py`) · commit `fa15b35`, `f26f426` · kiểm: `pytest tests/test_virtual_camera.py tests/test_vision_camera.py`; `neuroedge verify --targets sim` |
| **TSK-V1b-03** | Giao diện trừu tượng mô hình thị giác, đổi model bằng cấu hình | FR-MDL-04, FR-MDL-07 | V5 | ✅ Hoàn thành (2026-10-04) — `VisionModel` (khung vào, phát hiện ra, không tin cậy), mô hình `replay` tất định, `VisionPipeline` biến phát hiện thành dữ kiện gõ kiểu: từng khung rồi AND, fail-closed khi mô hình lỗi, quá hạn, rác, mất hoặc đứng khung; đổi mô hình chỉ bằng `[vision] provider` | [`perception/vision/`](../python/neuroedge/perception/vision/) · [`docs/spec/vision.md`](../docs/spec/vision.md) · commit `aed1e60` · kiểm: `pytest tests/test_vision_model.py tests/test_vision_facts.py` (`test_switching_the_model_is_a_configuration_change_only`) |
| **TSK-V1b-04** | Action CI cho khung hình: record, replay, assert trên chuỗi phán quyết | FR-CI-01→04 | V1 | 🟡 Xong Action CI cho khung hình (2026-10-04): record, replay, assert trên chuỗi phán quyết, sáu cảnh. **Còn:** golden suy luận theo sha256 mô hình và kiểm sai số `tolerance` giữa các target (RFC-0012 §3f mệnh đề 2) — cần mô hình thật (TSK-V1b-05) | [`testing/vision.py`](../python/neuroedge/testing/vision.py) · `fixtures/vision/` (`expected_results.yaml`, đóng hai chiều) · commit `c7efafc` · kiểm: `pytest tests/test_vision_scenes.py` |
| **TSK-V1b-05** | Tích hợp NPU rời (Hailo-8, Coral) sau giao diện trừu tượng | FR-MDL-04 | V5 | ⏳ Chưa bắt đầu | `python/neuroedge/perception/vision/accel/` |
| **TSK-V1b-06** | Ba gate mẫu có yếu tố thị giác, dữ kiện do maker khai từ nhãn của model, ngưỡng tin cậy khoá trong gate bằng tiêu chí số (Q-54) | FR-GATE-03 | V1 + V5 | ✅ Hoàn thành (2026-10-04) — ba gate mẫu `entry-no-stranger`, `zone-clear`, `package-notify`: ngưỡng độ tin cậy và số đếm là tiêu chí `numeric` khoá ở gate, mọi tiêu chí hiện diện đi cùng `confidence` có `max_age_ms`; tám gate con nới lỏng bị `gate lint` từ chối, ba gate con chỉ siết; digest khoá ở `digests.lock` | [`gates/vision/`](../gates/vision/) · `fixtures/gates/vision/` · commit `6c09f78` · kiểm: `pytest tests/test_vision_gates.py tests/test_sample_gates.py tests/test_digests_lock.py` |
| **TSK-V1b-08** | Bằng chứng thị giác trong vết ghi: kết quả nhận diện qua sự kiện nhóm `perception`; `vision_ref` (băm + kích thước) chỉ là danh tính; lint `uri` chỉ khi `metadata.raw_capture` (RFC-0002 §9.2) | FR-CI-02, NFR-PRIV-01, NFR-PRIV-03 | V1 | ✅ Hoàn thành (2026-10-04) — `lint_vision` trong `validate_trace` (`vision_ref` chỉ là băm và kích thước, `uri` chỉ khi `metadata.raw_capture`, không ảnh nhúng, mô hình có tên và có trong `metadata`, cửa sổ đúng `min_frames` khung liên tiếp, `age_ms` khớp); `neuroedge replay` tính lại dữ kiện từ nhãn đã ghi, không mô hình, không khung hình; 15 vết ghi phản chứng đóng hai chiều | [`trace.py`](../python/neuroedge/trace.py) (`lint_vision`) · `testing/player.py` · `fixtures/traces/invalid/vision_*.json` · commit `419a145`, `a3e5642` · kiểm: `pytest tests/test_vision_trace.py tests/test_trace_fixtures.py` |

#### Gói chuyển động

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-W1-03** | **RFC-motion (RFC-0011):** `motion.*` (`analog.in` chuyển sang RFC-0007, Q-53); phong bì N2 sang `motion.*`; token thuê có hạn (Q-37); trạng thái an toàn theo từng cơ cấu (Q-35); gộp `TODOS.md` #36, #39 | FR-HAL-01 | V1 + V2 | ✅ Hoàn thành (2026-10-01) — RFC-0011 chấp thuận, PR #78 | `docs/rfc/0011-nguyen-thuy-motion.md` |
| **TSK-I2a-05** | **`motion.*` trên `sim` và `linux`** (sau RFC-0011): kênh, đích, tốc độ, ramp; token thuê có hạn (Q-37); trạng thái an toàn khai theo từng cơ cấu (Q-35); phong bì của khối N2 | FR-HAL-01, FR-PER-02 | V1 + V2 | 🟡 Xong trên `sim` và trên `linux` với PWM sysfs giả (2026-10-04): kênh `motor`/`servo`, mỗi lease một lệnh, lần chạy qua phong bì, `safe_state` gửi khi hết lease/BLOCK/cắt lời/đóng không cần token, `neuroedge build` từ chối gate có `p95_latency_ms > lease_ms / 2`. Trên kernel (gpio-sim; CI run 37153005998, job `linux-hal`): lệnh nâng dây `enable` và lease hạ nó, giữ servo tới `max_hold_ms`, cắt lời hạ dây ngay và `close` để mọi driver xuống, dây `enable` không phải chân `digital_out` mà agent với tới, runtime bị SIGSTOP hay chết mất driver. **Còn:** PWM thật và `safe_state` trên kênh PWM thật (CI chỉ thấy dây `enable`; kênh PWM là cây giả), crash-safe trên hai bo thật; agent mẫu `rover` chưa nằm trong corpus của `verify`; HAL C (TSK-W1-04) | `docs/rfc/0011-nguyen-thuy-motion.md` · `hal/motion_core.py` · `hal/motion.py` · `hal/motion_pwm.py` · agent mẫu `fixtures/agents/rover/` · nhánh `feat/motion`: commit `6676f50`, `2b89a44`, `5f8bba7` · kiểm: `pytest tests/test_motion.py tests/test_motion_linux.py` · `tests_linux/test_gpio_motion.py` (job `linux-hal`: `test_a_command_raises_the_enable_line_and_the_lease_drops_it`, `test_the_servos_hold_keeps_its_enable_line_up_until_max_hold_ms`, `test_a_barge_in_drops_the_line_at_once_and_close_leaves_every_driver_down`, `test_the_enable_line_is_not_a_digital_out_pin_an_agent_can_reach`, `test_a_runtime_stopped_with_sigstop_while_a_motor_runs_loses_its_driver`, `test_a_runtime_that_dies_loses_its_driver_because_the_pipe_closes`) |

#### Khối N2 — Phong bì an toàn vật lý (dùng chung cho mọi actuator, chuyển từ NeuroBrain — Q-53)

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-N2-01** | Hook phong bì trong `HardwareAbstractionLayer.digital_out`, được tiêm vào như `authorize`. Thứ tự `require_pin → envelope → authorize → record`. Bị từ chối thì **token không bị tiêu** | FR-HAL-* | — | ✅ Hoàn thành (2026-10-04) — `HardwareAbstractionLayer._admit`: `require_pin → envelope → authorize → record`; lệnh bị từ chối không tiêu token, `authorize` hỏng hoàn 100% phần đã giữ; `off` và tự tắt của HAL không qua phong bì | [`hal/__init__.py`](../python/neuroedge/hal/__init__.py) · [`hal/envelope.py`](../python/neuroedge/hal/envelope.py) · commit `35af305` · kiểm: `pytest tests/test_envelope.py tests/test_safety_regressions.py` |
| **TSK-N2-02** | Chính sách phong bì (`hal/envelope.py`, không ở `brain/` — ranh giới B-1): check-và-reserve **nguyên tử** dưới khoá theo chân; `time.monotonic` được tiêm vào; trace ghi sự kiện `envelope_refused` | — | — | ✅ Hoàn thành (2026-10-04) — chính sách đặt ở `hal/envelope.py`, không ở `brain/` (ranh giới B-1: `brain/` không chạm HAL): kiểm-và-giữ nguyên tử dưới khoá theo chân, đồng hồ tiêm vào, `EnvelopeRefusedError` (`NE1003`) và sự kiện `envelope_refused`; `sim` tự tắt theo đồng hồ phiên, `linux` tự tắt bằng hẹn giờ thật, ghi bền write-ahead, tiến trình giám sát (`hal/supervisor.py`) **bật mặc định** và fail-closed; replay quyết theo thời gian đã ghi (`envelope_restored`) | [`hal/envelope.py`](../python/neuroedge/hal/envelope.py) · `hal/supervisor.py` · `hal/linux.py` · commit `35af305`, `02df9b5`, `8a69f0c` · kiểm: `pytest tests/test_envelope.py tests/test_hal_linux_envelope.py tests/test_supervisor.py` (`test_two_concurrent_commands_on_one_pin_give_exactly_one_envelope_refused`) · phần trên gpio-sim: `tests_linux/test_gpio_envelope.py` (xem tiêu chí N2.2; xanh ở CI run 37153005998, job `linux-hal`) |
| **TSK-N2-03** | Móc tắt an toàn cho `mcp serve`: `close()` gọi `hal.close()`, bắt SIGTERM, `on_no_initialize` dọn dẹp trước `os._exit` | — | — | ✅ Hoàn thành (2026-10-04) — `mcp serve` ra bằng đường dọn dẹp khi SIGTERM/SIGHUP, kể cả trên `sim` khi có `--trace-out` (trước đó SIGTERM làm mất vết ghi): `hal.close()`, ghi vết, mã 143; `on_no_initialize` dọn trước `os._exit` | [`sim/serve.py`](../python/neuroedge/sim/serve.py) · [`cli/main.py`](../python/neuroedge/cli/main.py) · commit `41cc668` · kiểm: `pytest tests/test_mcp_serve_ui.py tests/test_public_api.py` (run_stdio ghi vết và gọi `hal.close()` khi stdin đóng, Ctrl-C, SIGTERM, không có `initialize`; lệnh thật thoát 143) |
| **TSK-N2-04** | Hợp đồng hồi quy — năm khẳng định (`neuroedge-design-neurobrain.md` §7.1) | — | — | ✅ Hoàn thành (2026-10-04) — năm khẳng định của hợp đồng hồi quy: (1) không phong bì thì `digital_out` như cũ, gõ sai chân không tiêu token; (2) corpus `fixtures/tool_calls/` ra đúng đáp án; (3) mọi profile `boards/` nạp được và chặn phong bì mọi chân actuator; (4) ba vết ghi chuẩn mực giữ chuỗi phán quyết và lệnh chân; (5) `mcp serve` ra qua `hal.close()` và ghi vết | [`tests/test_safety_regressions.py`](../python/tests/test_safety_regressions.py) · `tests/test_mcp_serve_ui.py` · commit `00bfeec`, `41cc668` · kiểm: `pytest tests/test_safety_regressions.py tests/test_mcp_serve_ui.py` |
| **TSK-N2-05** | Cập nhật sơ đồ ở đầu `mcp_server.py` thêm bước phong bì | — | — | ✅ Hoàn thành (2026-10-04) — sơ đồ ở đầu `mcp_server.py` có bước phong bì; `threat_model.md` §1 ghi ngoại lệ duy nhất (lệnh về phía an toàn) và bước phong bì | [`mcp_server.py`](../python/neuroedge/mcp_server.py) · [`docs/spec/threat_model.md`](../docs/spec/threat_model.md) §1–§2 · commit `7b8f54b` |

- [x] **Tiêu chí N2.1:** Hai lệnh đồng thời cùng chân, chạy cả hai thứ tự bằng điểm dừng điều khiển được, cho đúng một `envelope_refused`.
  *Bằng chứng:* `pytest tests/test_envelope.py -k two_concurrent_commands_on_one_pin`.
- [x] **Tiêu chí N2.2:** Test SIGTERM giữa xung trên gpio-sim đưa line về 0 (sau TSK-S5-10). Phần unit của TSK-N2-03 chạy ngay.
  *Bằng chứng:* CI run 37153005998 (job `linux-hal`): `pytest tests_linux` 90 passed — `tests_linux/test_gpio_envelope.py::test_sigterm_in_the_middle_of_a_pulse_drops_the_line` (phiên `linux` ra mã 143 và line `door_lock` của gpio-sim về 0), cùng tệp: `test_a_runtime_stopped_with_sigstop_while_an_actuator_is_on_loses_the_line`, `test_a_runtime_that_is_killed_loses_its_lines_with_the_pipe`, `test_a_second_session_after_a_restart_waits_out_min_interval_before_it_turns_a_pin_on`, `test_the_hal_turns_an_on_off_at_max_continuous_ms_on_a_real_line`; `tests_linux/test_gpio_sim.py::test_sigterm_ends_a_linux_session_with_every_line_dropped`, `test_sigterm_ends_mcp_serve_on_linux_even_with_stdin_still_open`. Phần unit: `pytest tests/test_mcp_serve_ui.py` (ra bằng `hal.close()`, mã 143).
- [x] **Tiêu chí N2.3:** Năm khẳng định của hợp đồng hồi quy (`neuroedge-design-neurobrain.md` §7.1) đều xanh.
  *Bằng chứng:* `pytest tests/test_safety_regressions.py tests/test_mcp_serve_ui.py` (TSK-N2-04: không phong bì thì như cũ, corpus tool call, mọi profile `boards/` chặn phong bì, ba vết ghi chuẩn mực, `mcp serve` ra qua `hal.close()`).

**Tiêu chí ra I2a:**

- [x] **Tiêu chí 1:** Sáu RFC (0007, 0009, 0010, 0011, 0012, 0013) ở trạng thái ✅ Đã chấp thuận, có chữ ký kỹ thuật trưởng; `schemas/` chỉ đổi trong phạm vi các RFC đó, kèm kịch bản di trú (§2.3).
  *Bằng chứng:* `docs/rfc/README.md` (sáu dòng ✅ Đã chấp thuận; chữ ký ở đầu từng RFC); `git log --oneline -- schemas/` từ lúc chấp thuận chỉ có commit của RFC-0009 (`gate.v1`: `a8b2b26`, `48628ff`) và `33b6523` (`board.v1`: RFC-0007, 0010, 0011, 0012); mọi tệp đang hợp lệ vẫn hợp lệ (mục 4 của mỗi RFC): `pytest tests/test_boards.py tests/test_board_fixtures.py tests/test_digests_lock.py tests/test_trace_fixtures.py`.
- [x] **Tiêu chí 2:** RFC-0007 không đổi byte nào của `schemas/gate.v1.json` — thay đổi `gate.v1` chỉ đi qua RFC-0009.
  *Bằng chứng:* `git log --oneline -- schemas/gate.v1.json` — sau RFC-0006 chỉ còn `a8b2b26` và `48628ff` (TSK-W1-02, RFC-0009); không commit nào của RFC-0007.
- [x] **Tiêu chí 3:** Mỗi gói có một agent mẫu chạy trên `sim` (profile `sim-rpi5`) và `linux` (gpio-sim, `i2c-stub`, camera ảo trong CI); `neuroedge verify --targets sim,linux` đạt 100%.
  *Bằng chứng:* CI run 37154951261 (job `linux-hal`, PR #91): `neuroedge verify --targets sim,linux` Passed — ba vết ghi chuẩn mực cùng bốn corpus `sensor-pack` (`rail-gate`, 3), `vision` (`gate-watch`, 3), `fine-control` (`fan-pwm`, 5), `motion` (`rover`, 4) replay khớp trên `sim/sim-rpi5` và `linux/linux-rpi5`; `pytest tests/test_pack_corpora.py`; phần cứng ảo của các gói chạy ở `tests_linux` (90 passed). PWM, motor, servo, camera thật: TSK-I2-01.
- [x] **Tiêu chí 4:** Gate so ngưỡng số: corpus hợp lệ và phản chứng khép kín hai chiều; walker C khớp engine host trên host (ASan/UBSan) — `esp32s3` phải đọc được cùng cây.
  *Bằng chứng:* TSK-W1-02: `pytest tests/test_numeric_*.py tests/test_c_walker.py tests/test_gate_fixtures.py` — walker C biên dịch với `-fsanitize=address,undefined`, khớp engine trên mọi gate và cây `NETR` v2.
- [ ] **Tiêu chí 5:** Mất nguồn dữ liệu (camera, cảm biến, bus, model) giữa phiên ⇒ hành động bị chặn với lý do fail-closed, không treo; cơ cấu chuyển động về trạng thái an toàn đã khai. — *đạt trên kernel* (CI run 37153005998, job `linux-hal`): cảm biến `lm75` mất giữa phiên chỉ làm dữ kiện của nó chưa quyết (`tests_linux/test_sensor_display.py::test_a_sensor_that_goes_away_mid_session_leaves_only_its_facts_undecided`); ADC vắng ⇒ BLOCK `criterion_unavailable` (`tests_linux/test_analog_in.py::test_an_adc_that_is_not_there_blocks_criterion_unavailable`, `tests_linux/test_rail_gate.py` cùng tên); bus: thiết bị không trả lời hoặc nút mất ⇒ `NE5001` (`tests_linux/test_i2c_read.py`); line vào không đọc được ⇒ BLOCK (`tests_linux/test_gpio_sim.py::test_an_input_line_that_cannot_be_read_blocks_criterion_unavailable`); dây `enable` của PWM và `motion.*` về thấp khi runtime bị SIGSTOP, SIGKILL hoặc cắt lời (`tests_linux/test_gpio_pwm.py`, `test_gpio_motion.py`). Phần host: camera `pytest tests/test_vision_camera.py -k camera_that_ends`, mô hình `tests/test_vision_model.py`, `safe_state` `tests/test_motion.py`. Camera mất giữa phiên trên kernel (CI run 37155915232): `vivid` bị gỡ khỏi driver giữa phiên ⇒ BLOCK `criterion_unavailable` trong giới hạn đứng hình, không treo, vết ghi phát lại khớp trên `sim` và `linux` (`tests_linux/test_camera_v4l2.py::test_a_camera_that_disappears_mid_session_blocks_fail_closed_and_does_not_hang`). *còn:* `safe_state` của cơ cấu trên kênh PWM thật (CI chỉ thấy dây `enable`; kênh PWM là cây giả) — cần Pi 5 và motor/servo (TSK-I2-01).
- [x] **Tiêu chí 6:** Đổi mô hình thị giác chỉ bằng cấu hình, không sửa mã agent; vết ghi thị giác mặc định không chứa ảnh thô, `vision_ref` qua lint và `neuroedge replay` tái hiện phán quyết từ sự kiện `perception`.
  *Bằng chứng:* `pytest tests/test_vision_model.py -k switching_the_model` (đổi `[vision] provider`); `pytest tests/test_vision_trace.py tests/test_trace_fixtures.py` (lint `vision_ref`, 15 vết ghi phản chứng; replay từ nhãn đã ghi, mô hình bị cấm gọi); `pytest tests/test_vision_camera.py -k never_pixels` (vết ghi của camera ảo không có điểm ảnh).
- [x] **Tiêu chí 7:** Agent yêu cầu một nguyên thủy mở rộng bị **từ chối lúc build** trên bo mạch không khai nó, thông báo nêu đủ ba thành phần (FR-HAL-05).
  *Bằng chứng:* `pytest tests/test_vision_camera.py tests/test_sensor_pack_sample.py -k "refused_at_build or refuses_the_sample"` — `gate-watch` và `rail-gate` bị từ chối trên `sim-default`, mỗi nguyên thủy thiếu có một dòng `where`/`why`/`how`; `build` không `--board` nêu bo hợp (`sim-rpi5`).
- [x] **Tiêu chí 8:** Kết quả spike ADC được ghi lại, và quyết định ADC đã áp dụng.
  *Bằng chứng:* kết quả ghi ở TSK-N3-03 (PR #87: `ads7828` 1249 mV, `ina219` 12000 mV trên `i2c-stub`); quyết định áp dụng ở TSK-I2a-04: `analog.in` đọc hwmon `ads7828` (`hal/linux.py`, `pytest tests/test_hal_linux_analog.py`). Lần đọc trên kernel: `tests_linux/test_analog_in.py::test_the_spike_value_reads_as_1_249_volts` và `test_the_hal_reads_the_ads7828_through_hwmon_in_volts` (CI run 37153005998, job `linux-hal`).
- [ ] **Tiêu chí 9:** Năm nguyên thủy lõi và ba vết ghi chuẩn mực giữ nguyên chuỗi phán quyết; TTFV của luồng gõ chữ và thoại vẫn dưới 10 phút; `pytest` xanh, 0 skipped; `scripts/wheel_smoke.sh` đạt. — *còn:* TTFV đo trên người (A1). Đã đạt: ba vết ghi chuẩn mực giữ chuỗi phán quyết trên mọi bo (`pytest tests/test_safety_regressions.py -k canonical_traces`, `neuroedge verify --targets sim`), `pytest` 0 skipped, `scripts/wheel_smoke.sh`.

### 4.3.2 I2b — Kit mẫu và dựng nhanh

| | |
|:---|:---|
| **Mục tiêu** | Người dùng chọn một kit, chạy trên `sim` dưới 10 phút, rồi dựng thiết bị thật từ BOM và sơ đồ đấu dây trong một ngày; tuỳ biến bằng lệnh sinh mã, không sửa tay lược đồ (Q-52) |
| **Điều kiện vào** | — |
| **Tín hiệu đo** | Tiêu chí ra bên dưới; A12 đo ở I7 |
| **Người** | V3 (chủ trì), V1, V5 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I2b-01** | **Ba kit phần cứng từ ba template có sẵn** (`villa-concierge` khoá cửa, `home-voice`, `factory-monitor`): BOM cho Pi 5 và ESP32-S3, sơ đồ đấu dây, profile bo mạch, gate đã khoá, vết ghi golden, hướng dẫn "từ hộp tới chạy thật"; thống nhất tên và cơ cấu của mẫu thứ ba với proposal §1.6 (van xả hay quạt) | FR-DX-05, FR-DX-06 | V3 | ⏳ Chưa bắt đầu | `python/neuroedge/templates/` · `fixtures/agents/` · `docs/user/` |
| **TSK-I2b-02** | **Hai kit cho gói mới:** camera cổng (thị giác: người lạ trong vùng ⇒ bật đèn, khoá cổng) và rèm hoặc cửa cuốn (`motion.*` có phong bì), cùng cấu trúc với TSK-I2b-01 | FR-DX-05 | V3 + V5 | ⏳ Chưa bắt đầu | `python/neuroedge/templates/` · `fixtures/agents/` |
| **TSK-I2b-03** | **Thư viện gate khởi đầu** để `extends`: cửa, đèn, quạt hoặc van, còi, điều hoà, camera, động cơ — mỗi gate có corpus và mục trong `digests.lock` sau review | FR-GATE-05 | V1 | ⏳ Chưa bắt đầu | `gates/` · `digests.lock` |
| **TSK-I2b-04** | **Lệnh dựng nhanh `neuroedge add`** (lệnh con `action`, `gate`, `sensor`, `device`): sinh `@action` + gate + test hai chiều + khai `[requires]` từ template có sẵn (`templates.scaffold`); không ghi đè tệp đã có | FR-DX-01, FR-DX-08 | V3 | ⏳ Chưa bắt đầu | `python/neuroedge/cli/main.py` · `python/neuroedge/templates/` |

**Tiêu chí ra I2b:**

- [ ] **Tiêu chí 1:** Năm kit chạy qua `neuroedge new --template <kit>` trên `sim`, có test và nằm trong `wheel-smoke`; bản `linux` chạy trong job `linux-hal`.
- [ ] **Tiêu chí 2:** TTFV trên `sim` của mọi kit vẫn dưới 10 phút (M1).
- [ ] **Tiêu chí 3:** `neuroedge add` sinh được action + gate + test cho mỗi nguyên thủy; `gate lint` sạch, test hai chiều xanh; chạy lại không ghi đè tệp đã có.
- [ ] **Tiêu chí 4:** Mọi gate cha trong thư viện khởi đầu có ca phản chứng: gate con nới lỏng bị `gate lint` từ chối (A5).

### 4.4 I3 — Gate trên Box-3 thật

| | |
|:---|:---|
| **Mục tiêu** | Gate chạy trên ESP32-S3-Box-3 thật và điều khiển chân thật; người dùng tự nạp agent của mình; `verify` ba target bậc 1 cho miền phán quyết (U2/J3 → M3, A2) |
| **Điều kiện vào** | Box-3 trong tay |
| **Tín hiệu đo** | `verify --targets sim,linux,esp32s3` trên bo mạch; thời gian từ `build` tới chân kích trên bo mạch |
| **Người** | V2 (chủ trì), V6, V1 (TSK-S4-04), V3 (TSK-S4-05) |

Increment này **cố tình chưa làm thoại**: chứng minh tương đương target trên miền quyết định trước, khi biến số còn ít. Phần không cần bo mạch đã làm trước trên host và QEMU (TSK-S4-02, S4-07, S4-08, S4-09; Q-21); TSK-S4-11 cũng làm được trước khi bo mạch về.

**Nội dung spike bộ nhớ:** nạp thử AEC + VAD + Opus streaming **+ ESP-SR MultiNet** (bộ nhận diện lệnh cố định làm fallback cục bộ, Q-14; thêm WakeNet nếu cân nhắc thay microWakeWord) lên ESP32-S3-Box-3, đo dung lượng SRAM và PSRAM còn lại sau khi trừ ngăn xếp mạng và hệ điều hành. Kết quả là **một con số**, không phải một nhận định.

Ngưỡng đối chiếu đã chốt tại Q-3: **SRAM cho ứng dụng ≥ 120 KB · PSRAM ≥ 2 MB · firmware ≤ 3,5 MB**. Trượt một ngưỡng thì **không cắt thoại** (Q-44): mở ngay một `Q-N` lập lại kế hoạch I5 (TSK-S5-05, TSK-S5-07) và dời dự báo v1.0.

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S1-10** | **Spike khả thi bộ nhớ trên ESP32-S3-Box-3** | NFR-RES-01, NFR-RES-02 | V2 | 🔴 **Chờ bo mạch** | Khung đo xong: [`memory_probe.c`](../targets/esp32s3/main/memory_probe.c) (4 checkpoint, dòng JSON máy đọc), [`check_firmware_size.py`](../scripts/check_firmware_size.py) · **chưa có số đo thực** → [báo cáo](../docs/reports/memory_spike_report.md) · danh sách đo **thêm ESP-SR MultiNet** (và WakeNet nếu cân nhắc thay microWakeWord của Q-7) theo **Q-14** |
| **TSK-S2-10** | Kết luận kế hoạch thoại trên chip (I5) dựa trên spike — trượt ngưỡng thì lập lại kế hoạch, không cắt thoại (Q-44) | — | V2 + trưởng nhóm | ⏳ Chờ số đo TSK-S1-10 | Chặn bởi bo mạch (TSK-S1-10). `docs/reports/memory_spike_report.md` |
| **TSK-S4-01** | Port 5 nguyên thủy HAL lên ESP-IDF | FR-TGT-03, FR-HAL-01 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/hal/` |
| **TSK-S4-02** | Gate Engine chạy trên MCU: walker C99 duyệt **bố cục nhị phân `NETR` v1** do `neuroedge build` sinh (Q-23, RFC-0003), kể cả giới hạn tham số (RFC-0005) và `confirms` (RFC-0006); token dùng một lần | FR-ACE-01, FR-ACE-03, FR-ACE-08 | V2 + V1 | ✅ Hoàn thành (2026-09-24) — trên host và QEMU; bo mạch thật ở TSK-S4-03 | `targets/esp32s3/components/ne_gate/` (walker + `ne_token.c`) · `targets/esp32s3/main/gate_selftest.c` · `python/neuroedge/engine/binary_tree.py` · RFC-0003 · `pytest tests/test_c_walker.py tests/test_c_token.py` · PR #27, #29 |
| **TSK-S4-03** | Đường dẫn `digital.out` và `sensor.read` trên phần cứng thật | FR-HAL-06, FR-HAL-07 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/drivers/` |
| **TSK-S4-04** | Lệnh `neuroedge verify` cho cả 3 target bậc 1 | FR-CI-07, FR-TGT-04 | V1 | 🟡 **`esp32s3` trên QEMU chạy được** (2026-09-25, qua TSK-S4-09): `verify --targets sim,linux,esp32s3 --port` so quyết định. **Còn:** trên bo mạch; `replay --target esp32s3` cho vết ghi tuỳ ý (gửi dữ kiện xuống thiết bị); so timing | `python/neuroedge/cli/main.py` (`verify`) |
| **TSK-S4-05** | Runner kiểm thử nightly trên bo mạch thật | FR-CI-06, NFR-REL-03 | V3 | ⏳ Chưa bắt đầu | `.github/workflows/nightly-hardware.yml` |
| **TSK-S4-07** | **Walker C biên dịch trên host** (gcc/clang, ASan + UBSan) chạy trên mỗi PR: khớp engine host trên mọi gate + bảng sự thật `fixtures/decision_trees/`, fuzz tệp cây, RAM tĩnh 0, stack ≤ 512 B — kiểm TSK-S4-02 **không cần bo mạch** *(Q-21)* | FR-ACE-01, FR-CI-07 | V2 | ✅ Hoàn thành (2026-09-24) | `python/tests/test_c_walker.py` · `targets/esp32s3/components/ne_gate/Makefile` |
| **TSK-S4-08** | **Smoke test firmware trên Espressif QEMU** (ESP-IDF 5.4, `sdkconfig.qemu`): boot, UART, flash, self-test gate lúc khởi động (walker + sổ token trên gate home-voice, dòng `NE_SELFTEST PASS`); mỗi PR đụng `targets/**` và hằng đêm. Không phủ I2S, Wi-Fi (`NEUROEDGE_SKIP_NETWORK`), PSRAM octal (QEMU không có; `SPIRAM_IGNORE_NOTFOUND`), LCD SPI, GPIO thường *(Q-21)* | FR-CI-06, FR-TGT-03 | V2 | ✅ Hoàn thành (2026-09-24) | `.github/workflows/firmware-qemu.yml` · PR #29 |
| **TSK-S4-09** | **Vết ghi từ firmware qua UART** (JSON-lines, tiền tố `NE1 `) + `neuroedge record --target esp32s3 --port`; chạy cả trên QEMU ⇒ `verify --targets esp32s3` trên miền quyết định trước khi bo mạch về *(Q-21)* | FR-CI-01, FR-TGT-04, FR-CLI-04 | V2 + V1 | ✅ Hoàn thành (2026-09-25) — trên host và QEMU; bo mạch ở TSK-S4-04 | [`components/ne_trace/`](../targets/esp32s3/components/ne_trace/) (dòng `NE1`) · [`main/trace_vectors.c`](../targets/esp32s3/main/trace_vectors.c) + `main/vectors/` (`scripts/gen_firmware_vectors.py`) · `ne_decide` (đường suy giảm C) trong `ne_gate/` · [`testing/uart.py`](../python/neuroedge/testing/uart.py) · job `uart-trace` (`firmware-qemu.yml`) · đặc tả [`simulation_coverage.md`](../docs/spec/simulation_coverage.md) §4 · `pytest tests/test_c_trace.py tests/test_uart_trace.py tests/test_trace_vectors.py` |
| **TSK-S4-10** | **Ảnh golden cho giao diện LVGL:** cùng mã màn hình của firmware build trên host, `lv_test_display` + `lv_test_screenshot_compare`, mỗi PR *(Q-21)* | FR-HAL-01, FR-CI-05 | V2 | ✅ Hoàn thành (2026-09-26) — trên host; nối vào firmware đang chạy cùng driver màn hình (TSK-S4-01) | [`targets/esp32s3/ui/`](../targets/esp32s3/ui/) (9 màn hình, `vi`/`en`, phông Be Vietnam Pro) · [`docs/spec/ui.md`](../docs/spec/ui.md) (quy tắc ngôn ngữ §2) · [`run_ui_golden.sh`](../scripts/run_ui_golden.sh): 66 ảnh golden RGB565, ASan/UBSan · job `ui-golden` · kiểm: `pytest tests/test_ui_language.py tests/test_ui_assets.py tests/test_ui_text.py` |
| **TSK-S4-11** | **Ngân sách RAM tĩnh trên mỗi PR:** `idf.py size` của firmware có link ESP-SR AFE; fail khi `.bss`/`.data` làm SRAM còn lại dưới Q-3 (≥ 120 KB). QEMU in heap trong còn trống lúc boot (QEMU không giả lập PSRAM octal của Box-3, TSK-S4-08). Phần áp lực lúc chạy âm thanh vẫn chờ TSK-S1-10 | NFR-RES-01, NFR-RES-02 | V2 | 🟡 Xong một phần (2026-09-26): RAM tĩnh + heap QEMU kiểm mỗi PR, đều trên sàn 120 KB — số đo ở [`memory_spike_report.md`](../docs/reports/memory_spike_report.md) §4.1. **Còn:** link ESP-SR AFE (chờ giấy phép, `TODOS.md` #17) rồi bật `--require-esp-sr` | [`check_firmware_size.py`](../scripts/check_firmware_size.py) · job `firmware-size` của [`firmware-qemu.yml`](../.github/workflows/firmware-qemu.yml) |
| **TSK-S4-12** | **Bài kiểm ngày đầu có bo mạch:** codec ES8311/ES7210 port nguyên văn từ XiaoZhi; vòng loa → micro so tín hiệu mẫu, GPIO `door_lock` đo bằng đầu dò; chạy trong ngày Box-3 về | FR-PER-06, FR-HAL-06 | V2 | ⏳ Khi bo mạch về | `targets/esp32s3/tests/bringup/` |
| **TSK-I3-01** | **Đường nạp firmware cho agent của người dùng:** `build --target esp32s3` sinh project ESP-IDF từ agent — thay các header sinh tay của `scripts/gen_firmware_gates.py` — rồi nạp theo tài liệu; CI kiểm trên QEMU | FR-CLI-02, FR-TGT-03 | V2 | ✅ Hoàn thành (2026-09-26) — trên QEMU; nạp lên Box-3 chờ bo mạch | [`engine/firmware.py`](../python/neuroedge/engine/firmware.py) · [`components/ne_agent/`](../targets/esp32s3/components/ne_agent/) · [`nap-firmware.md`](../docs/user/nap-firmware.md) · job `agent-firmware` |

*Mã TSK-S4-06 chưa từng được cấp; các mã còn lại giữ nguyên để không vỡ truy vết.*

**Đòn bẩy OSS:** ESP-IDF làm toolchain · port driver bo mạch từ XiaoZhi vào `targets/esp32s3/drivers/` (codec I2S ES8311/ES7210, chân I2C/SPI của Box-3, LCD ST7789) · LVGL cho hiển thị trạng thái · gcc trên host và Espressif QEMU để kiểm logic firmware trước khi có bo mạch (TSK-S4-07, S4-08; Q-21). XiaoZhi kéo theo ESP-SR — giấy phép chỉ cho chip Espressif, nên chỉ nằm trong `targets/esp32s3/` (proposal Phụ lục H.1). Tiết kiệm ước tính 7 tuần, trong đó 2–3 tuần nằm trên đường găng.

**Tiêu chí ra I3:**

- [ ] 🔴 **Tiêu chí 1:** Báo cáo spike bộ nhớ có số liệu đo thực, đối chiếu trực tiếp với ngưỡng Q-3 (SRAM ≥ 120 KB, PSRAM ≥ 2 MB, flash ≤ 3,5 MB).
  **CHƯA ĐẠT — chặn bởi phần cứng vật lý, không thể xử lý bằng công việc trên máy tính.** Khung đo đã xong và ngưỡng Q-3 đã ghim thành hằng số; [báo cáo](../docs/reports/memory_spike_report.md) nêu rõ 5 việc còn lại. Hàm đối chiếu trả `INCONCLUSIVE` khi checkpoint `audio_ready` chưa được lấy, để số đo sàn không bị đọc thành một kết quả đạt.
- [ ] **Tiêu chí 2 (A2):** `neuroedge verify --targets sim,linux,esp32s3` đạt 100% trên kịch bản **không dùng audio** → **A2 đạt cho miền phán quyết**. Trên QEMU (TSK-S4-09, `device_id = "qemu"`) chạy được trước khi bo mạch về; tiêu chí chỉ đóng khi cũng đạt trên bo mạch.
  *Tiến độ (2026-09-25):* trên QEMU đã chạy — job `uart-trace` (`verify --targets esp32s3 --port uart.log`); trên host: `pytest tests/test_trace_vectors.py -k golden`. Operation/duration của lệnh chân còn lấy từ bảng hành động dựng trên host (TSK-S4-01).
- [x] **Tiêu chí 3:** Sai lệch phán quyết giữa các target sinh `SafetyRegressionError` (NE4002) chỉ rõ sự kiện lệch đầu tiên — cơ chế đã có từ TSK-S3-04; tiêu chí đạt khi áp cho `esp32s3`.
  *Bằng chứng (2026-09-25, trên host và QEMU):* `pytest tests/test_trace_vectors.py -k deliberate` — firmware có lỗi cố ý (fail-closed thành ALLOW; chân kích trên BLOCK) ⇒ `verify --targets esp32s3` mã 1, `SAFETY REGRESSION` nêu sự kiện lệch đầu tiên; token thiếu chân ⇒ lệnh chân lệch golden.
- [ ] **Tiêu chí 4:** Nightly runner chạy tự động và gửi báo cáo.
- [ ] **Tiêu chí 5:** Trong một buổi đo tại chỗ, một người ngoài đội tự build và nạp agent của mình lên Box-3 chỉ theo tài liệu (`build --target esp32s3` → nạp); chân kích khi ALLOW và không bao giờ kích khi BLOCK (TSK-I3-01).

### 4.4.1 I3a — Nguyên thủy mở rộng trên `esp32s3`

| | |
|:---|:---|
| **Mục tiêu** | Bốn gói nguyên thủy mở rộng chạy trên chip: Box-3 cho cảm biến, PWM và chuyển động; M5Stack CoreS3 cho thị giác (Q-53, Q-61) |
| **Điều kiện vào** | Box-3 và bo camera đã về (Phụ lục B) |
| **Tín hiệu đo** | Tiêu chí ra bên dưới |
| **Người** | V2 (chủ trì), V6, V5 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I3a-01** | **Bo ESP32-S3 có camera làm bo tham chiếu thứ hai của `esp32s3`** (RFC-0013, Q-53): khảo sát và chọn bo, đặt mua (Phụ lục B), profile `esp32s3-cores3`, đo ngân sách SRAM và PSRAM theo Q-3 | FR-HAL-02, NFR-RES-02 | V2 | 🟡 Đã chọn M5Stack CoreS3 (Q-61, 2026-10-01); còn đặt mua, profile, đo Q-3 | `boards/` · `docs/reports/` |
| **TSK-I3a-02** | **HAL C: `digital.in`, bus I2C chỉ đọc, `analog.in`** trên ESP-IDF, khớp hợp đồng RFC-0007 | FR-HAL-01, FR-TGT-03 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/hal/` |
| **TSK-I3a-03** | **HAL C: PWM** (LEDC) trong `digital.out` theo RFC-0010 | FR-HAL-01 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/hal/` |
| **TSK-N7-02** | Cưỡng chế phong bì trong firmware C. Firmware chưa có phong bì thì action gắn phong bì bị **từ chối trên chip** (fail-closed) | — | — | ⏳ Chưa bắt đầu | `targets/esp32s3/components/` |
| **TSK-W1-04** | **Hiện thực `motion.*` trên `esp32s3`** (bản host: TSK-I2a-05) + test crash-safe trên bo mạch thật + sửa `voice_fsm.md` §5 (dừng do mất liên lạc) | FR-HAL-01, FR-PER-02 | V2 | ⏳ Chưa bắt đầu | `targets/` · `docs/spec/voice_fsm.md` |
| **TSK-I3a-04** | **`vision.in` trên bo camera ESP32-S3** theo RFC-0012: khung hình, dữ kiện thị giác vào gate, fail-closed khi mất camera hoặc model; vết ghi chỉ mang `vision_ref` | FR-HAL-01 | V5 + V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/` |
| **TSK-I3a-05** | **`verify --targets sim,linux,esp32s3` cho agent mẫu của bốn gói** trên Box-3 và bo camera, nối vào nightly (TSK-S4-05) | FR-CI-07 | V1 + V2 | ⏳ Chưa bắt đầu | `python/neuroedge/cli/main.py` · `.github/workflows/nightly-hardware.yml` |

**Tiêu chí ra I3a:**

- [ ] **Tiêu chí 1:** `neuroedge verify --targets sim,linux,esp32s3` đạt 100% cho agent mẫu của mỗi gói, trên Box-3 và bo camera.
- [ ] **Tiêu chí 2:** Firmware bật đủ nguyên thủy mở rộng cùng thoại vẫn giữ SRAM trống ≥ 120 KB (Q-3); trượt thì mở một `Q-N` lập lại kế hoạch và dời ngày, không cắt (Q-52).
- [ ] **Tiêu chí 3:** Mất điện hoặc reset giữa một lệnh `motion.*` trên bo thật: cơ cấu về trạng thái an toàn đã khai (Q-35).
- [ ] **Tiêu chí 4:** Phong bì được cưỡng chế trong firmware; action có phong bì bị từ chối trên firmware chưa hiện thực phong bì (fail-closed).

### 4.5 I4 — Thoại trên host

| | |
|:---|:---|
| **Mục tiêu** | Nói chuyện với agent trên `sim` và `linux`: thu/phát âm thanh, wake-word, cắt lời, STT/TTS qua provider cloud, fallback lệnh cục bộ khi mất mạng — cùng đặc tả FSM với chip (U1/J1 bằng giọng nói) |
| **Điều kiện vào** | — (vector và FSM Python bắt đầu ngay, Q-39) |
| **Tín hiệu đo** | Bộ vector tuân thủ xanh trên Python; tỷ lệ phiên thoại so với gõ chữ trong buổi đo |
| **Người** | V1 (chủ trì), V2 (TSK-S5-08) |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S2-07** | **Đặc tả chuẩn tắc máy trạng thái hội thoại** — nguồn sự thật cho cả hai hiện thực (§3.8) | FR-PER-02, FR-PER-03 | V1 | ✅ Hoàn thành (2026-09-25) — chỉ đặc tả; hiện thực ở TSK-S3-11, TSK-S5-03 | [`docs/spec/voice_fsm.md`](../docs/spec/voice_fsm.md): năm trạng thái, bảng chuyển trạng thái, hợp đồng thu hồi lệnh (§5: chỉ lệnh chưa giao, ≤ 20 ms, đóng token; lệnh đã giao chạy hết), sự kiện (§8), kịch bản tuân thủ cho TSK-S3-10 (§9). Chỉ tài liệu |
| **TSK-S3-10** | **Bộ vector kiểm thử tuân thủ độc lập ngôn ngữ** cho máy trạng thái hội thoại (§3.8) | FR-CI-07, FR-TGT-04 | V1 | ✅ Hoàn thành (2026-09-25) | [`fixtures/compliance/voice/`](../fixtures/compliance/voice/): mỗi ca một tệp JSON, phủ V1–V7 và mọi dòng T01–T14 của `voice_fsm.md` §4, đáp án `expected_results.yaml` khép kín hai chiều; agent `fixtures/agents/voice-door/`; quy ước ở `voice_fsm.md` §9.1. Kiểm: `pytest tests/test_voice_corpus.py` |
| **TSK-S3-11** | Hiện thực Python của máy trạng thái hội thoại, port thiết kế từ Pipecat | FR-PER-02→05 | V1 | ✅ Hoàn thành (2026-09-25) — thoại trên `sim`; `linux` chưa có lệnh hẹn giờ (`voice_fsm.md` §10) | `python/neuroedge/perception/` (`voice_fsm.py`, `voice_session.py`): vượt 100% bộ vector TSK-S3-10; lệnh hẹn giờ `pulse(after_ms=…)` trên `SimHAL`, hủy khi cắt lời và đóng token (§5.2). Kiểm: `pytest tests/test_voice_corpus.py tests/test_voice_fsm.py` |
| **TSK-S3-13** | **Tích hợp ASR/TTS qua provider cloud** cho `sim` và `linux`, kèm tùy chọn mô hình cục bộ (CR-1.0) — **chuyển từ Sprint 3** (wedge `sim` gõ chữ không cần, Q-15); dùng lại hợp đồng provider của TSK-S2-11, làm cùng TSK-S5-06. Âm thanh `linux` là TSK-S5-08 | FR-MDL-09, FR-PER-07 | V1 | 🟡 Xong trên `sim` (2026-09-26); `--voice-file --target linux` chạy qua backend tệp của TSK-S5-08. **Còn:** phiên micro thời gian thực — TSK-I4-04 (Q-50) | [`perception/providers/`](../python/neuroedge/perception/providers/) · [`hal/audio.py`](../python/neuroedge/hal/audio.py) · [`cli/voice.py`](../python/neuroedge/cli/voice.py) · ca `v6_stt_unavailable_says_offline_line.json` · kiểm: `pytest tests/test_voice_speech.py tests/test_speech_providers.py` |
| **TSK-S5-08** | **`audio.in` / `audio.out` trên `linux`:** `sounddevice` (PortAudio, MIT); AEC phần mềm PipeWire `module-echo-cancel` (Q-22): `audio.in` đọc nút `source` đã khử vang, `audio.out` phát vào nút `sink` của module; cấu hình drop-in `pipewire.conf.d/neuroedge-echo-cancel.conf` giao kèm; `linux-rpi5` khai `aec = true` **chỉ** khi đạt tiêu chí đo `simulation_coverage.md` §6 ⇒ agent mẫu build được cho `linux`. CI: backend tệp/PCM (runner không có `snd-aloop`); Pi: `snd-aloop` + HAT I2S hằng đêm | FR-TGT-02, FR-PER-01 | V2 | 🟡 Xong trên host (2026-09-26): backend tệp + live `sounddevice`, cấu hình PipeWire giao kèm. **Còn:** kiểm trên Pi + HAT I2S (tên nút PipeWire ↔ ALSA chưa xác minh), đo AEC rồi mới khai `aec = true` (tiêu chí 4) | [`hal/linux.py`](../python/neuroedge/hal/linux.py) · [`pipewire/neuroedge-echo-cancel.conf`](../pipewire/neuroedge-echo-cancel.conf) · [`simulation_coverage.md`](../docs/spec/simulation_coverage.md) §6.1 · kiểm: `pytest tests/test_hal_linux_audio.py tests/test_voice_linux.py`, `tests_linux/test_audio_file.py` |
| **TSK-I4-01** | **Fallback lệnh cục bộ và wake-word trên host:** openWakeWord trên `linux` (Q-7), cùng ngữ pháp lệnh với `sim` (Q-14) | FR-PER-01, FR-MDL-03 | V1 | 🟡 Xong phần mã (2026-09-26): `[wake_word]` (adapter openWakeWord, người dùng tự cấp mô hình) + `[stt.fallback]`. **Còn:** chạy với một mô hình wake-word thật — CI dùng module giả; kho không có mô hình dùng được (`TODOS.md` #49) | [`perception/providers/wake.py`](../python/neuroedge/perception/providers/wake.py) · [`voice_fsm.md`](../docs/spec/voice_fsm.md) §1, §6, §8 · ca `i4_*` trong `fixtures/compliance/voice/` · kiểm: `pytest tests/test_wake_word.py tests/test_stt_fallback.py` |
| **TSK-I4-02** | **`SystemOne` đổi được bằng cấu hình** (một phần `TODOS.md` #27) | FR-MDL-04 | V1 | ✅ Hoàn thành (2026-09-26) | [`models/providers/systemone_api.py`](../python/neuroedge/models/providers/systemone_api.py) (Jev `typesafe/jev-1.13` qua System One API; `[system_one]`: `criteria`, `threshold`, `timeout_ms`; ngữ pháp là fallback) · kiểm: `pytest tests/test_system_one_cloud.py` · [`scripts/live_jev_smoke.py`](../scripts/live_jev_smoke.py) chạy tay — chưa chạy, chưa có key |
| **TSK-I4-03** | **Độ trễ từng chặng và tỷ lệ System 1 / System 2 trong vết ghi** | FR-ACE-06, FR-TEL-03, NFR-OBS-02 | V1 | ✅ Hoàn thành (2026-09-26) | [`engine/latency.py`](../python/neuroedge/engine/latency.py) (`turn_latency`, `session_summary` — [`tool_calling.md`](../docs/spec/tool_calling.md) §7.1) · kiểm: `pytest tests/test_turn_latency.py` |
| **TSK-I4-04** | **Phiên thoại thời gian thực trên laptop** (`sim`): `neuroedge run --mic [--half-duplex]` — micro và loa thật, cùng `VoiceSession` với `--voice-file`, đồng hồ là đồng hồ mẫu của micro; kéo `TODOS.md` #45 lên cho host (Q-50) | FR-PER-01, FR-PER-02, FR-PER-07 | V1 | 🟡 Xong phần mã (2026-09-29): `SimHAL(audio="live")`, luồng thu vào hàng đợi có giới hạn (đầy ⇒ dừng, không bỏ âm thanh), `play_live` tương đương từng sự kiện với `play()`; provider thật qua OpenRouter chạy đầu-cuối bằng `--voice-file`. **Còn:** chạy micro thật trên máy người trình bày (cần quyền micro của macOS), `--mic --ui` | [`hal/audio_live.py`](../python/neuroedge/hal/audio_live.py) · [`perception/live.py`](../python/neuroedge/perception/live.py) · `VoiceSession.play_live` · [`cli/voice.py`](../python/neuroedge/cli/voice.py) · [`demo/i4-thoai-laptop/`](../demo/i4-thoai-laptop/) · kiểm: `pytest tests/test_voice_live.py tests/test_hal_sim_live_audio.py` |

**Tiêu chí ra I4:**

- [x] **Tiêu chí 1:** Bộ vector tuân thủ `fixtures/compliance/voice/` (TSK-S3-10) xanh trên hiện thực Python (TSK-S3-11).
- [ ] **Tiêu chí 2:** Vòng thoại end-to-end trên `sim` và `linux`, STT/TTS qua provider cloud (TSK-S3-13); cắt lời giữa câu: TTS dừng dưới 300 ms, không lệnh actuator chưa giao nào rò (`voice_fsm.md` §5). — *còn:* `sim` và `--voice-file --target linux` xong (`pytest tests/test_voice_corpus.py tests/test_voice_linux.py`); phiên micro sống trên `linux` (Pi + HAT I2S, AEC PipeWire — TSK-S5-08) và micro thật trên laptop (TSK-I4-04) cần phần cứng và người.
- [x] **Tiêu chí 3 (Q-14):** Mất provider giữa phiên → fallback lệnh cục bộ lượng giá; fallback không có hoặc không chạy → hành động bị chặn với lý do `gate_unreachable`.
  *Bằng chứng:* `pytest tests/test_system_one_cloud.py -k "model_is_down or without_the_key"` (Jev mất giữa phiên ⇒ ngữ pháp quyết, vết ghi có `system_one_fallback`) · `pytest tests/test_models.py -k gate_unreachable` (fallback không có hoặc hỏng lúc chạy ⇒ `gate_unreachable`).
- [ ] **Tiêu chí 4:** `linux-rpi5` khai `aec = true` chỉ khi đạt tiêu chí đo `docs/spec/simulation_coverage.md` §6 (TSK-S5-08).
- [x] **Tiêu chí 5:** Vết ghi có độ trễ từng chặng và tỷ lệ System 1 / System 2 (TSK-I4-03).
  *Bằng chứng:* `pytest tests/test_turn_latency.py`; `neuroedge trace show <vết ghi>` in tỷ lệ và chặng.

### 4.5.1 I4a — NeuroBrain trên host

| | |
|:---|:---|
| **Mục tiêu** | Dựng Physical AI bằng hội thoại, có hợp đồng (Q-31), trên `sim` và `linux`, phủ đủ bốn gói nguyên thủy (Q-55): lab action có gate, I2C chỉ đọc, sổ bàn làm việc, Chat Contracting, Lab Monitor, trigger |
| **Điều kiện vào** | — (lab action chờ RFC-0007 của I2a) |
| **Tín hiệu đo** | Tỷ lệ BLOCK; số bản nháp gate được khoá |
| **Người** | V2, V7 |
| **Thiết kế** | [`neuroedge-design-neurobrain.md`](neuroedge-design-neurobrain.md) |

#### Khối N0 — Quản trị

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-N0-01** | Hai mục `Q-N`: "Lab Mode / NeuroBrain" và "Giai đoạn 1.5", chuyển các quyết định ở `neuroedge-design-neurobrain.md` Phụ lục B vào PRD §15 | — | V2 | ⏳ Chưa bắt đầu | `neuroedge-prd.md` §15 |
| **TSK-N0-04** | Cập nhật threat model §2b: lab action, nguồn `trigger`, `/confirm`, cờ `[lab] enabled` | NFR-SEC-09 | V2 | ⏳ Chưa bắt đầu | `docs/spec/threat_model.md` |
| **TSK-N0-05** | Quy trình duyệt gate nháp: `-draft` → PR có người review → `gate lint` sạch → bỏ hậu tố → `check_digests.py --update` | FR-GATE-* | V2 | ⏳ Chưa bắt đầu | `CONTRIBUTING.md` §3 |
| **TSK-N0-06** | Đề xuất mở rộng Q-11 cho OFL-1.1 (**chỉ với font**) và mục `NOTICE` cho IBM Plex; thêm mục `NOTICE` Section A cho ESP-Claw (`neuroedge-design-neurobrain.md` Phụ lục A) | — | V2 | ⏳ Chưa bắt đầu | `neuroedge-prd.md` Q-11 · `NOTICE` |

- [ ] **Tiêu chí N0.1:** Hai mục `Q-N` có trạng thái ĐÃ CHỐT, có chữ ký kỹ thuật trưởng.
- [ ] **Tiêu chí N0.3:** Mọi tài liệu khác dẫn mã `Q-N`, không chép lại nội dung (CONTRIBUTING §8.1).

#### Khối N1 — Gated claw lõi

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-N1-01** | `lab_pulse` là `@action` mẫu + gate `gates/lab/lab_pulse@1.0.0`, với `arguments.duration_ms ≤ 2000` (RFC-0005). Gate không có pin enum: chân giới hạn bằng allow-list của board; dự án muốn hẹp hơn thì viết gate con thu hẹp `pin` | FR-MDL-10 | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` · `gates/lab/` |
| **TSK-N1-02** | Cờ `[lab] enabled` trong `agent.toml`, mặc định **tắt**; tắt thì lab tool không được đăng ký | — | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |
| **TSK-N1-03** | `neuroedge build --release` từ chối khi `[lab] enabled`, lỗi nêu tên cờ và cách tắt; build thường ghi `lab_enabled: true` trong báo cáo | FR-CLI-02 | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/cli/main.py` · `engine/compiler.py` · `docs/release.md` |
| **TSK-N1-04** | Kết quả lab call kèm `gate explain`, để LLM tự sửa lệnh sai | FR-MDL-10 | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |
| **TSK-N1-05** | `mcp desktop-config --lab`: cấu hình Claude Desktop cho agent lab trong một bước, vẫn đúng một mục `mcpServers` | FR-CLI-12 | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/mcp_desktop.py` |
| **TSK-N1-06** | `board show --lab`: chân trong allow-list, giới hạn phong bì từng chân, lý do chân khác bị cấm | FR-HAL-05 | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/cli/main.py` |
| **TSK-N1-07** | Test ranh giới **B-1**: quét AST/import của `neuroedge.brain`, fail nếu có gọi phương thức HAL hoặc import `hal.linux` / `hal.sim` | — | V2 | ⏳ Chưa bắt đầu | `python/tests/test_brain_boundary.py` |
| **TSK-N1-08** | `lab_read` trên primitive `digital.in` (sau RFC-0007) | FR-HAL-01 | — | ⏳ Chưa bắt đầu — `digital.in` đã có (TSK-I2a-02) | `python/neuroedge/brain/` · `hal/` |

- [ ] **Tiêu chí N1.1:** Trên `sim`, Claude Desktop gọi `lab_pulse(pin, 300)`. Có trace ALLOW và chân về 0.
- [ ] **Tiêu chí N1.2:** Gọi `lab_pulse(pin, 2500)` ra `argument_out_of_range`, kèm lý do `gate explain`.
- [ ] **Tiêu chí N1.3:** Cờ tắt thì `mcp tools` không liệt kê `lab_pulse`. `build --release` với cờ bật thoát mã khác 0.
- [ ] **Tiêu chí N1.4:** Test B-1 fail khi thêm thử một lệnh `hal.digital_out` vào `brain/`.
- [ ] **Tiêu chí N1.5:** `pytest` xanh, 0 skipped; `gate lint gates/lab/` sạch; `scripts/wheel_smoke.sh` đạt.

#### Khối N3 — Bus I2C chỉ đọc

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-N3-01** | Quét bus bằng **read-byte**, không bằng quick-write; đọc chip ID; không nhận diện được thì ghi "không nhận diện", không đoán | FR-HAL-01 | — | ⏳ Chưa bắt đầu — RFC-0007 đã chấp thuận; bề mặt quét của HAL (`i2c_scan`, đọc read-byte, địa chỉ ngoài allow-list chỉ được liệt kê) đã có ở TSK-I2a-03; còn nhận diện chip và phần của `brain/` | `python/neuroedge/hal/` · `brain/` |
| **TSK-N3-02** | Test trên `i2c-stub` + `lm75`: có thiết bị, bus trống, NACK, timeout (tối đa 1 lần thử lại) | FR-TGT-02 | — | 🟡 Đã viết và chạy xanh (2026-10-04) trong `tests_linux/test_i2c_read.py`: thiết bị có mặt (đọc thanh ghi khai, byte nhận), địa chỉ không trả lời ⇒ `NE5001` sau đúng một lần thử lại, nút bus không tồn tại ⇒ `NE5001`, địa chỉ ngoài allow-list chỉ được liệt kê (CI run 37153005998, job `linux-hal`: `pytest tests_linux` 90 passed). **Còn:** ca bus trống đúng nghĩa — quét một bus không có chip nào (bus của `i2c-stub` ở CI luôn mang ba chip), nên chưa có test báo danh sách rỗng | `python/tests_linux/test_i2c_read.py` · `scripts/setup_i2c_stub.sh` (`lm75` 0x48, `ina219` 0x40, `ads7828` 0x4a) |

- [ ] **Tiêu chí N3.1:** `tests_linux` phát hiện `0x48` (`lm75`) và báo đúng bus trống. — *đạt nửa đầu* (CI run 37153005998, job `linux-hal`): `tests_linux/test_i2c_read.py::test_a_scan_lists_the_unlisted_chip_and_a_read_of_it_is_refused` liệt kê `0x48` và từ chối đọc nó; *còn:* báo đúng bus trống — chưa test nào quét một bus không có chip (xem TSK-N3-02).

#### Khối N4 — Sổ bàn làm việc

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-N4-01** | Ghi sự thật phát hiện được, mỗi mục kèm trace nguồn: vai chân, chip ID. Hai vai mâu thuẫn trên cùng chân thì báo lỗi có kiểu, để người quyết | — | — | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |
| **TSK-N4-02** | Sinh profile board **mới** dạng nháp qua mã đọc/ghi `BoardProfile`, không ghi TOML bằng chuỗi. **Không sửa** ba profile tier-1 | FR-HAL-05 | — | ⏳ Chưa bắt đầu | `python/neuroedge/hal/board.py` |
| **TSK-N4-03** | Cảnh báo chân đặc biệt theo MCU. ESP32-S3: strapping 0, 3, 45, 46; flash/PSRAM 26–32 (33–37 khi dùng PSRAM octal); chân đã bị ngoại vi chiếm (dữ liệu port từ ESP-Claw, `neuroedge-design-neurobrain.md` Phụ lục A). Đây là cảnh báo, không phải blacklist | — | — | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |

#### Khối N5 — Chat Contracting

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-N5-01** | Từ trace sinh `@action` + gate `0.1.0-draft` + test replay, bằng `templates.scaffold`/`_render` có sẵn. Chỉ ghi vào thư mục agent của người dùng | FR-DX-01 | — | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |
| **TSK-N5-02** | Test **hai chiều** bắt buộc: ít nhất một ALLOW và một BLOCK/`argument_out_of_range`. Bản nháp chỉ có ALLOW thì bị từ chối | FR-CI-* | — | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |
| **TSK-N5-03** | Ba lỗi LLM riêng biệt (malformed, empty, refusal), không ghi tệp rác. Chân không truy được về trace thì từ chối sinh. Tên action trùng thì không ghi đè | — | — | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` · corpus `expected_results.yaml` |
| **TSK-N5-04** | PR của bản nháp in `gate explain` bằng lời, cùng diff chính sách và các test ALLOW/BLOCK | — | — | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |
| **TSK-N5-05** | `trace export --report`: báo cáo bring-up Markdown (chân đã thử, kết quả, thiết bị bus, bản nháp đã sinh) | FR-TRC-* | — | ⏳ Chưa bắt đầu | `python/neuroedge/cli/main.py` |

#### Khối N5b — Lab Monitor

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-N5b-01** | Xếp hàng ask "1/3", ask cũ nhất trước (hôm nay `stateAt` chỉ giữ ask mới nhất). Focus mặc định ở "Huỷ"; phím chỉ tác dụng khi thẻ có focus; không cướp focus khi người đang gõ lệnh | — | — | ⏳ Chưa bắt đầu | `viz/assets/ui.js` · `tests/test_sim_ui.py` |
| **TSK-N5b-02** | Mất kết nối SSE: banner vàng, làm mờ thiết bị và hàng live, khoá nút ask; gỡ banner khi có tin đầu tiên | — | — | ⏳ Chưa bắt đầu | `viz/__init__.py` · `ui.js` · `ui.css` |
| **TSK-N5b-03** | Hàng "đang bật" có thời gian còn lại; làn timeline theo chân với vùng bấm ≥24×24 px, mỗi xung là `<button>` có `aria-label`, mũi tên trái/phải để di chuyển | — | — | ⏳ Chưa bắt đầu | `ui.js` · `ui.css` |
| **TSK-N5b-04** | Thước phong bì ghi rõ cửa sổ lấy từ `board.v1`: xanh dưới 80%, vàng từ 80%, đầy thì đỏ kèm "khoá tới HH:MM:SS". Trạng thái rỗng: bo chưa khai chân → thông điệp trỏ tới `board show --lab`; thiếu phong bì → nhãn vàng | — | — | ⏳ Chưa bắt đầu | `ui.js` · `sim/ui.py` |
| **TSK-N5b-05** | Thẻ phán quyết: huy hiệu bốn màu theo nghĩa (ALLOW xanh, BLOCK đỏ, ENVELOPE vàng, REJECTED xám, luôn kèm chữ); nhãn "người: Đồng ý/Huỷ/hết hạn"; gộp lặp "×N"; bấm xung thì mở thẻ tương ứng kèm `gate explain` | — | — | ⏳ Chưa bắt đầu | `ui.js` · `ui.css` |
| **TSK-N5b-06** | Tiêu đề tab "(1) Cần xác nhận" + favicon vàng; công tắc âm báo mặc định tắt. Khi tua lại, ask và hàng live **luôn là hiện tại**. Nhãn bus: "phát lại từ trace `<tệp>` lúc HH:MM:SS" | — | — | ⏳ Chưa bắt đầu | `ui.js` · `sim/ui.py` |
| **TSK-N5b-07** | Restyle **cả trang sim**: bỏ viền trái trên thẻ phán quyết, thay bằng huy hiệu; nhúng IBM Plex Sans 400/600 + Plex Mono 400 (woff2, subset Latin + tiếng Việt); luật hệ thiết kế ghi ở khối chú thích đầu `ui.css`. **Chặn bởi TSK-N0-06** | — | — | ⏳ Chặn bởi Q-11 | `ui.css` · `NOTICE` |

- [ ] **Tiêu chí N5b.1:** Ba ask cùng lúc: không ask nào bị che rồi tự hết hạn.
- [ ] **Tiêu chí N5b.2:** Nhấn Enter trong ô lệnh không bao giờ kích "Đồng ý".
- [ ] **Tiêu chí N5b.3:** `trace view` vẫn là một tệp tự chứa, chạy offline (FR-DX-02).
- [ ] **Tiêu chí N5b.4:** Đi hết luồng xác nhận chỉ bằng bàn phím và VoiceOver.

#### Khối N6 — Trigger theo sự kiện

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-N6-01** | Giá trị `call_source` mới `trigger`. `SOURCES` là mã, không nằm trong `schemas/`, nên chỉ cần mục `Q-N` + cập nhật `docs/spec/tool_calling.md`, không cần RFC. Thêm fixture và `expected_results.yaml` | FR-MDL-10 | — | ⏳ Chưa bắt đầu | `actions/tools.py` · `fixtures/tool_calls/` |
| **TSK-N6-02** | `trigger ∉ HUMAN_SOURCES`; có test khẳng định trigger không trả lời được `ask` | Q-26 | — | ⏳ Chưa bắt đầu | `actions/confirmation.py` |
| **TSK-N6-03** | Debounce + trần tần suất trigger; action bị BLOCK không được thử lại vô hạn; trigger bị chặn liên tục thì hiện trên N5b | — | — | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |

#### Phủ bốn gói

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I4a-01** | **NeuroBrain phủ bốn gói (Q-55):** lab action và Chat Contracting sinh hợp đồng cho `digital.in`, bus I2C, `analog.in`, PWM, `vision.in` (dữ kiện + ngưỡng tin cậy, Q-54) và `motion.*`; bản nháp cho `motion.*` phải khai phong bì và trạng thái an toàn, thiếu thì từ chối sinh | FR-MDL-10, FR-DX-01 | V2 + V7 | ⏳ Chưa bắt đầu | `python/neuroedge/brain/` |

- [ ] **Tiêu chí I4a:** Mỗi gói có ít nhất một bản nháp do Chat Contracting sinh, qua `gate lint`, test hai chiều và người duyệt, rồi chạy trên `sim` và `linux`. Tiêu chí ra của N4, N5 và N6 được viết và duyệt khi I4a mở.

### 4.6 I5 — Thoại trên Box-3

| | |
|:---|:---|
| **Mục tiêu** | Demo "nói chuyện với con chip $5": thoại trên ESP32-S3-Box-3, gate trên chip, cùng vết ghi replay trong CI — tiền đề của A6 và điều kiện công khai (Q-39) |
| **Điều kiện vào** | `TODOS.md` #17 (giấy phép ESP-SR) giải trước TSK-S5-07; V6 đã vào |
| **Tín hiệu đo** | Bộ nhớ còn lại sau 4 giờ; độ trễ thoại trọn vòng |
| **Người** | V6 (TSK-S5-01, S5-02, S5-06, S5-07), V2 (TSK-S5-03, S5-04, S5-05), V1 |

**Đây vẫn là increment khó nhất của toàn dự án, nhưng rủi ro đã giảm một bậc kể từ CR-1.0.** Kiến trúc cloud-first đưa STT, TTS và suy luận ngôn ngữ ra khỏi vi điều khiển; `esp32s3` chỉ còn thu/phát âm thanh, AEC/VAD, máy trạng thái hội thoại và thẩm định gate. Áp lực bộ nhớ SRAM/PSRAM giảm đáng kể, và rủi ro R-1 của PRD hạ từ Cao xuống Trung bình.

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S5-01** | Tích hợp WebRTC AEC, libfvad (VAD), Opus streaming | FR-PER-06 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/audio/` |
| **TSK-S5-02** | Port đường dẫn audio thu/phát theo §3.5, tuân thủ nghĩa vụ ghi nhận nguồn §3.9. **Không hiện thực STT/TTS trên thiết bị** | FR-PER-01 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/drivers/audio_path.c` |
| **TSK-S5-03** | **Hiện thực C/C++ của máy trạng thái hội thoại** theo [`voice_fsm.md`](../docs/spec/voice_fsm.md) (TSK-S2-07), phải vượt bộ vector tuân thủ TSK-S3-10 (§3.8) | FR-PER-02, FR-PER-03, FR-PER-05 | V1 + V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/fsm/voice_fsm.c` |
| **TSK-S5-04** | Thu hồi lệnh actuator chưa thực thi khi bị cắt lời — hợp đồng ở [`voice_fsm.md`](../docs/spec/voice_fsm.md) §5 | FR-PER-02 | V1 + V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/fsm/actuator_abort.c` |
| **TSK-S5-05** | Tối ưu bộ nhớ theo ngân sách đã chốt ở Q-3 | NFR-RES-01, NFR-RES-02 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/sdkconfig.defaults` |
| **TSK-S5-06** | **Client streaming âm thanh lên provider cloud**: đẩy khung Opus lên STT, nhận luồng TTS về, tái dùng hợp đồng kết nối của TSK-S2-11 (CR-1.0) | FR-PER-07, FR-GW-04 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/audio/provider_client.c` |
| **TSK-S5-07** | **Fallback cục bộ trên `esp32s3`** (Q-14): bộ nhận diện lệnh cố định dùng **cùng ngữ pháp lệnh** với `sim` (TSK-S2-08). Backend chọn ở I5 giữa **ESP-SR MultiNet** (lệnh offline, vài chục–vài trăm câu) và **TFLite Micro / ESP-NN** (KWS tự train < 500 KB). **Điều kiện trước Sprint 5:** xác minh giấy phép ESP-SR (theo hiểu biết: chỉ cho dùng trên SoC Espressif), ghi vào `NOTICE`, không lọt vào gói Python ([`TODOS.md`](../TODOS.md) #17); giấy phép không hợp ⇒ dùng TFLite Micro / ESP-NN (Apache-2.0). Số đo bộ nhớ lấy từ spike TSK-S1-10 | FR-MDL-03, FR-ACE-03, NFR-RES-01 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/fallback/` |

**Ràng buộc kiến trúc bắt buộc:** máy trạng thái hội thoại có **một đặc tả chuẩn tắc** (TSK-S2-07) và **hai hiện thực** — Python cho `sim`/`linux` (TSK-S3-11), C/C++ cho `esp32s3` (TSK-S5-03) — cùng vượt **một bộ vector tuân thủ** (TSK-S3-10, §3.8). Hiện thực C/C++ là bản thứ hai của cùng đặc tả, không phải thiết kế độc lập, và chỉ được nghiệm thu khi vượt toàn bộ bộ vector. Hai bản mà phân kỳ thì hành vi thu hồi lệnh actuator khi cắt lời sẽ khác nhau giữa các target, phá vỡ tương đương ở đúng miền nguy hiểm nhất.

**Đòn bẩy OSS:** microWakeWord trên MCU và openWakeWord trên Linux · Silero VAD và libfvad · WebRTC AEC3 · Opus · port mô hình frame processor và barge-in từ Pipecat. Không còn hạng mục STT/TTS trên thiết bị. Tiết kiệm ước tính 4 tuần, phần lớn nằm trên đường găng.

**Tiêu chí ra I5:**

- [ ] **Tiêu chí 1:** Vòng lặp thoại chạy end-to-end trên bo mạch tham chiếu với STT, TTS và suy luận ngôn ngữ đặt ở provider cloud.
- [ ] **Tiêu chí 2:** Cắt lời giữa câu: TTS dừng dưới 300 ms, không có lệnh actuator nào rò rỉ.
- [ ] **Tiêu chí 3:** Bơm 20 khung nhiễu liên tiếp: máy trạng thái vẫn phản hồi đúng.
- [ ] **Tiêu chí 4:** Bộ nhớ còn lại sau 4 giờ chạy nằm trong ngân sách Q-3.
- [ ] **Tiêu chí 5 (Q-14):** Mất kết nối tới provider giữa phiên → gate lượng giá bằng fallback cục bộ của TSK-S5-07; fallback không có / không chạy được → hành động vật lý bị chặn với lý do `gate_unreachable`; thiết bị không treo và phục hồi được khi có mạng trở lại.

### 4.6.1 I5a — NeuroBrain trên chip

| | |
|:---|:---|
| **Mục tiêu** | Lab action, gate và bản nháp đã khoá của I4a chạy trên Box-3 và bo camera; phong bì cưỡng chế trên chip (Q-55) |
| **Điều kiện vào** | — |
| **Tín hiệu đo** | Tiêu chí ra bên dưới |
| **Người** | V2, V7 |
| **Thiết kế** | [`neuroedge-design-neurobrain.md`](neuroedge-design-neurobrain.md) §13 |

#### Khối N7 — NeuroBrain trên ESP32-S3

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-N7-01** | Lab action + gate trên chip, dùng walker C và sổ token có sẵn | — | — | ⏳ Chưa bắt đầu | `targets/esp32s3/` |
| **TSK-N7-03** | Port chọn lọc từ ESP-Claw (`neuroedge-design-neurobrain.md` Phụ lục A). MCP trên chip chỉ làm sau TSK-P2-04 (MCP qua mạng có xác thực, đã xong trên host), hoặc đi qua UART | — | — | ⏳ Chưa bắt đầu | `targets/esp32s3/` · `NOTICE` |

- [ ] **Tiêu chí N7:** được viết và duyệt khi I5a mở.
- [ ] **Tiêu chí I5a:** `neuroedge verify --targets sim,linux,esp32s3` đạt 100% cho một hợp đồng do NeuroBrain sinh ở mỗi gói.

### 4.7 I6 — Công khai

| | |
|:---|:---|
| **Mục tiêu** | Lần đầu người ngoài dùng được sản phẩm: repo công khai, `pip install neuroedge` từ PyPI, lược đồ ở URL công khai, video demo thoại và bốn gói trên `sim`, `linux` và `esp32s3` (Q-39, Q-52). Đây là bản ứng viên của MVP: A1 và A9 cần người ngoài cài từ PyPI trước khi v1.0 được công bố |
| **Điều kiện vào** | Điều khoản license thương mại, kể cả quyền dùng thử cho doanh nghiệp (`TODOS.md` #44) |
| **Tín hiệu đo** | Lượt cài đầu tiên từ PyPI; người ngoài đầu tiên chạy agent (B1 bắt đầu đếm) |
| **Người** | V3 (chủ trì), trưởng nhóm, V2 (video trên chip), V1 (bề mặt tích hợp, Q-58) |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S3-14** | **Workflow release lên PyPI**; nghiệm thu `pip install neuroedge==<tag>` rồi **chạy** `gate lint` + `trace validate` từ bản cài | FR-DX-02, FR-GOV-01 | V3 | 🟡 **Workflow sẵn; go-live khi công khai** (Q-39) | [`release-pypi.yml`](../.github/workflows/release-pypi.yml): `build` (sdist → wheel từ sdist, `twine check --strict`, tag = `version`) → `smoke` (runner sạch, `wheel_smoke.sh --wheel` trên đúng wheel sẽ phát hành) → `publish-testpypi` / `publish-pypi` (OIDC, không token; chỉ khi có tag **và** `PUBLISH_ENABLED == 'true'`); [`LICENSE`](../LICENSE) MIT trong wheel/sdist. **Còn (ở I6):** người sở hữu repo làm [`docs/release.md`](../docs/release.md) (public repo, trusted publisher, environment, biến, tag `v0.6.0rc1` rồi `v0.6.0`), rồi nghiệm thu `pip install neuroedge==0.6.0` |
| **TSK-S3-09** | Telemetry CLI ẩn danh, có thể tắt | FR-TEL-01, FR-TEL-02 | V3 | ⏳ Chưa bắt đầu | Cần trước khi công khai: đo B1, B4, B5 (thêm sự kiện đo B4 — Q-41); có thông báo lần đầu và tài liệu quyền riêng tư (FR-TEL-02) |
| **TSK-W0-02** | **SBOM** (CycloneDX/SPDX) từ `requirements-lock.txt`, gắn vào mỗi bản phát hành | — | V3 | ✅ Hoàn thành (2026-09-26) | [`scripts/sbom.sh`](../scripts/sbom.sh) · job `sbom` của [`release-pypi.yml`](../.github/workflows/release-pypi.yml) (artifact `sbom`; `github-release` đính kèm) |
| **TSK-W0-03** | **Quét lỗ hổng và bí mật:** `pip-audit`, gitleaks trên **toàn lịch sử** trước khi công khai, CodeQL cho Python và C firmware | — | V3 | ✅ Hoàn thành (2026-09-26) | [`security.yml`](../.github/workflows/security.yml) (`pip-audit`, `gitleaks`, `actionlint`, `codeql`, `codeql-c`) · [`pip-audit-ignore.txt`](../python/pip-audit-ignore.txt) |
| **TSK-I6-01** | **Kho công khai:** toàn bộ kho public từ 2026-09-25 (chốt `TODOS.md` #41 — Q-45); README và CONTRIBUTING trỏ đúng kho | FR-GOV-01 | trưởng nhóm + V3 | ✅ Hoàn thành (2026-09-25) | https://github.com/letrongminh/neuroedge-init — public |
| **TSK-I6-02** | **Lược đồ ở URL công khai `schema.neuroedge.dev`** và bộ kiểm tuân thủ tải được — điều kiện của A9 | FR-GOV-01, FR-GOV-02 | V3 | ⏳ Chưa bắt đầu | tên miền · `schemas/` |
| **TSK-I6-03** | **Video demo thoại trên `sim`, `linux` và Box-3:** cùng agent, cùng gate, cùng vết ghi replay trong CI — tài sản trực quan của A8 | FR-DX-06 | V3 + V2 | ⏳ Chưa bắt đầu | `README.md` |
| **TSK-I6-04** | **Kênh cộng đồng** (Discord hoặc GitHub Discussions) và quy trình tiếp nhận lỗi | — | V3 | ⏳ Chưa bắt đầu | — |
| **TSK-P2-04** | **MCP qua mạng có xác thực** (Streamable HTTP + OAuth 2.1 theo Q-32, token theo thiết bị, mTLS như NFR-SEC-04); mặc định tắt, stdio vẫn là mặc định; thiếu cấu hình xác thực thì không khởi động; kèm ca "lặp lời gọi bị chặn tới khi lọt" (`TODOS.md` #29) và mục mới trong threat model — dời từ I14 (Q-58) | NFR-SEC-09, FR-CLI-12 | V1 | ✅ Hoàn thành (2026-10-04) — `neuroedge mcp serve --http`: Streamable HTTP qua mTLS (TLS 1.3, bắt buộc chứng chỉ client), token OAuth 2.1 theo thiết bị ràng buộc chứng chỉ (RFC 8705); mặc định tắt, stdio vẫn là mặc định; thiếu một mảnh cấu hình ⇒ mã 1 trước khi dựng phiên hay mở cổng; thiếu hoặc sai token ⇒ 401, không gì được chuyển tiếp, `mcp_auth_refused` trong vết ghi; N lần lặp cùng dữ kiện ⇒ N `BLOCK` (đóng `TODOS.md` #29, #24). **Chưa:** thử trên hai máy thật (xem tiêu chí 7 của I6) | [`mcp_http.py`](../python/neuroedge/mcp_http.py) · [`docs/spec/tool_calling.md`](../docs/spec/tool_calling.md) §8.1 · [`docs/spec/threat_model.md`](../docs/spec/threat_model.md) §2b · nhánh `feat/mcp-network`: commit `5df990c`, `baff0ae` · kiểm: `pytest tests/test_mcp_http.py` (`test_the_network_transport_refuses_to_start_without_the_whole_configuration`, `test_a_request_without_a_valid_token_is_refused_and_nothing_is_dispatched`, `test_a_client_without_a_trusted_certificate_never_reaches_http`, `test_an_authenticated_client_lists_and_calls_the_gated_tools`, `test_repeating_a_blocked_call_over_the_network_never_slips_through`) |
| **TSK-I6-05** | **Đóng băng hợp đồng cho người tích hợp vào `schemas/`** (Q-58, mở phạm vi ở Q-63): một RFC rồi PR mã (`CONTRIBUTING.md` §3) cho (1) lược đồ phong bì `ToolCall` và kết quả của Gated Tool Profile, rút từ corpus `fixtures/tool_calls/` (TSK-S3-24); (2) khoá định danh phiên bản lược đồ của `board.v1` (gate và vết ghi đã có `schema`/`$schema`, bo mạch chưa — RFC quyết cách thêm mà tệp `boards/*.toml` hiện có vẫn hợp lệ); (3) danh mục mã lỗi `NE*` ở dạng máy đọc được, để SDK ngôn ngữ khác sinh mã từ đó. Corpus thẩm định theo lược đồ mới; lược đồ lên `schema.neuroedge.dev` cùng TSK-I6-02. `agent.toml` vẫn không thuộc `schemas/` (`tool_calling.md` §9) | FR-MDL-10, FR-GOV-01, FR-GOV-02, FR-HAL-02 | V1 | 🟡 RFC-0015 đã soạn (2026-10-04), trạng thái Đang thảo luận — phong bì `ToolCall` và kết quả, khoá `schema` của `board.v1`, danh mục mã lỗi `NE*` dạng máy đọc; 13 câu hỏi mở cho chủ sản phẩm và kỹ thuật trưởng. **Còn:** chữ ký chấp thuận (người), rồi hai PR mã (lược đồ mới; khoá `schema` của `board.v1`) và corpus thẩm định theo lược đồ đó | `docs/rfc/0015-hop-dong-cho-nguoi-tich-hop.md` (nhánh `docs/rfc-integrator-contracts`, commit `a61b984`) · `schemas/` · `docs/spec/tool_calling.md` §9 |
| **TSK-I6-06** | **Bề mặt Python công khai** (Q-63): đặc tả `docs/spec/python_api.md` nói điều gì là công khai, chính sách SemVer và quy tắc ngừng hỗ trợ (PRD §9 hứa SemVer cho "API công khai" nhưng chưa định nghĩa); `neuroedge.__all__` đủ cho người tích hợp (`SimHAL`, `LinuxHAL`, `ToolCall`, `dispatch`, `TraceRecorder`, biên dịch và duyệt cây, các lỗi còn thiếu); hàm khởi động MCP server gọi được từ mã Python (hôm nay chỉ có lệnh CLI); lớp gốc `HardwareAbstractionLayer` khai chữ ký audio; `ToolCall` báo nguồn sai bằng lỗi `NE*` thay cho `ValueError`; test ghim `__all__` để đổi bề mặt là CI báo | FR-DX-02, FR-GOV-03 | V1 | ✅ Hoàn thành (2026-10-03) — `__all__` đủ cho người tích hợp, ghim bằng test; `neuroedge.serve_mcp` dùng chung vòng phục vụ với `mcp serve`; `ToolCallError` (NE1004); `SimSession`, `Turn` công khai; hợp đồng CLI ghim bằng `test_cli_contract.py`; quyết định ở Q-64 | [`docs/spec/python_api.md`](../docs/spec/python_api.md) · [`__init__.py`](../python/neuroedge/__init__.py) · [`sim/serve.py`](../python/neuroedge/sim/serve.py) · kiểm: `pytest tests/test_public_api.py tests/test_cli_contract.py` |
| **TSK-I6-07** | **RFC dữ kiện từ tiến trình ngoài** (Q-63; chỉ RFC, mã sau v1.0 — `TODOS.md` #56): cách một tiến trình khác (Frigate, OpenCV, bộ cảm biến, tích hợp Home Assistant) đưa quan sát vào gate mà không có model hay thư viện thị giác trong lõi — nguồn khai trong gate, danh tính nguồn ghi vào vết ghi, `age_ms` theo định nghĩa chung (Q-62), nguồn rớt ⇒ `criterion_unavailable`, không bao giờ cấp ALLOW; khớp RFC-0012 (§9.2: nhãn model → dữ kiện gõ kiểu) | FR-MDL-04, FR-MDL-10 | V1 | 🟡 RFC-0014 đã soạn (2026-10-04), trạng thái Đang thảo luận — dữ kiện số từ tiến trình ngoài qua khoá `evaluate.<tên>.external_source` của `gate.v1`. **Còn:** chữ ký chấp thuận (người); mã hiện thực sau v1.0 (`TODOS.md` #56) | `docs/rfc/0014-du-kien-tu-tien-trinh-ngoai.md` (nhánh `docs/rfc-external-facts`, commit `41d9d7b`) · `docs/spec/tool_calling.md` |

**Tiêu chí ra I6:**

- [x] **Tiêu chí 1:** gitleaks quét toàn lịch sử của repo sẽ công khai, 0 phát hiện (TSK-W0-03).
  *Bằng chứng:* job `gitleaks` của `security.yml` (2026-09-26): 205 commit trên 57 ref, kể cả đầu mọi PR — "no leaks found"; chạy lại mỗi tuần.
- [x] **Tiêu chí 2:** Repo công khai; README và CONTRIBUTING trỏ đúng repo (TSK-I6-01).
  *Bằng chứng:* kho public từ 2026-09-25, toàn bộ kho (Q-45); `pytest tests/test_readme_quickstart.py -k link` kiểm mọi link GitHub trong README trỏ tới tệp có thật.
- [ ] **Tiêu chí 3:** `pip install neuroedge==<tag>` từ PyPI, rồi `gate lint` và `trace validate` chạy từ bản cài (TSK-S3-14).
- [ ] **Tiêu chí 4:** `schema.neuroedge.dev` phục vụ mọi lược đồ trong `schemas/` và bộ kiểm tuân thủ (TSK-I6-02).
- [ ] **Tiêu chí 5:** README có video demo thoại trên ba target (TSK-I6-03).
- [ ] **Tiêu chí 6:** Telemetry opt-in chạy, có thông báo lần đầu và tài liệu quyền riêng tư; đo được B1, B4, B5 (TSK-S3-09).
- [ ] **Tiêu chí 7:** Một client MCP trên máy khác gọi `@action` qua Streamable HTTP + OAuth 2.1 + mTLS, mọi lời gọi qua gate và vào vết ghi; thiếu xác thực ⇒ từ chối; bật cổng mạng mà thiếu cấu hình xác thực ⇒ không khởi động; N lần lặp cùng dữ kiện ⇒ N `BLOCK` (TSK-P2-04). — *còn:* bốn hành vi và vòng gọi đầy đủ đã có bằng test trên loopback với CA tạm (`pytest tests/test_mcp_http.py`, nhánh `feat/mcp-network`); một lần chạy trên **hai máy thật** chưa làm (người).
- [ ] **Tiêu chí 8:** Gated Tool Profile, định danh phiên bản `board.v1` và danh mục mã lỗi nằm trong `schemas/` qua RFC được chấp thuận; mọi ca của `fixtures/tool_calls/` thẩm định theo lược đồ đó (TSK-I6-05). — *còn:* RFC-0015 đã soạn, chưa chấp thuận (người); chưa có lược đồ nào trong `schemas/`.
- [x] **Tiêu chí 9:** `docs/spec/python_api.md` có thật; một dự án ngoài chỉ `import neuroedge` (không đường dẫn nội bộ) dựng được HAL, nạp gate, gọi `dispatch` và khởi động MCP server; test ghim `__all__` xanh (TSK-I6-06).
  *Bằng chứng:* `pytest tests/test_public_api.py -k external_project` — dự án ở thư mục tạm ngoài kho, chạy `python -I`, chỉ `import neuroedge`: dựng `SimHAL`, nạp gate, `dispatch` cho ALLOW và BLOCK, `serve_mcp` qua stdio thật (`initialize`, `tools/list`, `tools/call`); `pytest tests/test_public_api.py tests/test_cli_contract.py` (ghim `__all__` và CLI).
- [ ] **Tiêu chí 10:** RFC dữ kiện từ tiến trình ngoài được chấp thuận; mã hiện thực không thuộc I6 (TSK-I6-07). — *còn:* RFC-0014 đã soạn, chưa chấp thuận (người).

### 4.8 I7 — v1.0

| | |
|:---|:---|
| **Mục tiêu** | v1.0 = lần ra mắt MVP (Q-52): đủ A1–A12 (PRD §11.1) |
| **Điều kiện vào** | — |
| **Tín hiệu đo** | A1–A12 |
| **Người** | V2, V6 (OTA, bảo mật thiết bị), V1, V3 |

**OTA làm trước trên QEMU (Q-39):** TSK-S6-01, S6-02 và S6-04 kiểm được trên QEMU trước khi có bo mạch; phần tải qua mạng thật, Secure Boot và phép chạy 24 giờ cần bo mạch.

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S6-01** | OTA cấp thiết bị: phân vùng kép A/B | FR-OTA-01 | V2 | ✅ Hoàn thành (2026-09-26) — trên QEMU; Box-3 chưa có Wi-Fi thật (`TODOS.md` #50) | [`components/ne_ota/`](../targets/esp32s3/components/ne_ota/) · lớp `sdkconfig.ota` · [`nap-firmware.md`](../docs/user/nap-firmware.md) §6 · [`qemu_ota.sh`](../scripts/qemu_ota.sh) pha a–g, job `ota-rollback` |
| **TSK-S6-02** | Tự động rollback khi phát hiện vòng lặp khởi động | FR-OTA-02 | V2 | ✅ Hoàn thành (2026-09-26) — trên QEMU: reset trước xác nhận và self-test hỏng đều quay về; ảnh treo chỉ quay về ở lần bật nguồn sau (watchdog không panic) | `ne_ota.c` (`ne_ota_boot_*`) · pha d, e của `qemu_ota.sh` · `simulation_coverage.md` §4.1 |
| **TSK-S6-03** | Xác minh chữ ký firmware trên chip | FR-OTA-03 | V2 | 🟡 Xong phần cập nhật (2026-09-26, QEMU): RSA-3072 kiểm trên mọi ảnh OTA, sai khóa hay không ký ⇒ từ chối, xoá khe; hạ cấp chặn bằng mốc NVS. **Còn:** Secure Boot + anti-rollback eFuse (TSK-S6-05) — không có chúng, ai nạp bằng cáp vẫn đổi được firmware | `SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT` trong `sdkconfig.ota` · pha c, f, g · kiểm: `pytest tests/test_c_ota_policy.py` |
| **TSK-S6-04** | Nạp firmware từ HTTP endpoint mở bất kỳ | FR-OTA-04 | V2 | ✅ Hoàn thành (2026-09-26) — trên QEMU qua HTTP (`open_eth`); HTTPS dùng CA bundle, chưa kiểm end-to-end | `esp_https_ota` trong `ne_ota.c` · URL qua Kconfig hoặc NVS (`nap-firmware.md` §6.1) · hạn chót tải, từ chối chuyển hướng |
| **TSK-S6-05** | Secure boot, mã hóa flash, nút ngắt micro vật lý | NFR-SEC-02, NFR-SEC-03 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/security/` |
| **TSK-S6-06** | Kiểm thử chịu tải 24 giờ | NFR-RES-01, A6 | V3 | ⏳ Chưa bắt đầu | `tests/stress/` |
| **TSK-S6-07** | Publish JSON Schema công khai và bộ kiểm thử tuân thủ | FR-GOV-01, FR-GOV-03, FR-TRC-10, A9 | V1 | ⏳ Chưa bắt đầu | `schemas/`, `fixtures/compliance/` (thoại: [`voice_fsm.md`](../docs/spec/voice_fsm.md) §9) |
| **TSK-S6-08** | Hoàn thiện tài liệu, ví dụ, video minh họa | FR-DX-05, FR-DX-06, A8 | V3 | ⏳ Chưa bắt đầu | `docs/`, `examples/` |
| **TSK-W0-01** | **Tiêu chí nghiệm thu cho NFR-SEC-02→06, 08**; rà NFR-SEC-09 | NFR-SEC | V1 | ⏳ Chưa bắt đầu | `neuroedge-prd.md` Phụ lục A.3 |
| **TSK-W2-07** | **SBOM kèm phát hành, attestation bản build, ghim GitHub Actions theo SHA** | — | V3 | ✅ Hoàn thành (2026-09-26) — còn SBOM firmware | mọi workflow ghim SHA · [`dependabot.yml`](../.github/dependabot.yml) · job `attest` của [`release-pypi.yml`](../.github/workflows/release-pypi.yml) |
| **TSK-I7-01** | **Các FR v1.0 chưa có task** (rà soát MECE, trước ghi ở `TODOS.md` #31 — đã xoá): lint cấm rẽ nhánh theo target, FR-DX-07, FR-CLI-08 — phạm vi đã xác nhận 2026-09-25 | FR-TGT-05, FR-TGT-07, FR-DX-07, FR-CLI-08 | V1 + V3 | ⏳ Chưa bắt đầu | — |
| **TSK-I7-02** | **Đo A1 chính thức** (10 lập trình viên độc lập, cài từ PyPI) và **A9** (bên thứ ba chạy bộ kiểm tuân thủ) | FR-DX-01, FR-GOV-01 | V3 | ⏳ Chưa bắt đầu | `docs/reports/` |

**Đòn bẩy OSS:** `esp_https_ota` và `esp_ota_ops` của ESP-IDF cho cập nhật phân vùng kép A/B và rollback cục bộ. Tiết kiệm ước tính 2 tuần.

**Tiêu chí ra I7 — cổng phát hành v1.0:**
Đạt **toàn bộ A1 đến A12** — ngưỡng và phương pháp kiểm chứng ở [PRD §11.1](neuroedge-prd.md#111-nghiệm-thu-v10--lõi) (không chấp nhận đạt một phần):

- [ ] **A1** — Time-to-first-value
- [ ] **A2** — Tương đương môi trường (`verify --targets sim,linux,esp32s3`)
- [ ] **A3** — Không có đường tắt tới actuator
- [ ] **A4** — Fail-closed *(mất mạng: lượng giá qua fallback cục bộ, Q-14)*
- [ ] **A5** — Kế thừa gate an toàn
- [ ] **A6** — Độ ổn định trên vi điều khiển
- [ ] **A7** — Vết ghi hợp lệ
- [ ] **A8** — Tài liệu
- [ ] **A9** — Lược đồ công khai
- [ ] **A10** — Đủ nguyên thủy trên ba target *(bốn gói mở rộng, Q-53)*
- [ ] **A11** — Dựng bằng hội thoại có hợp đồng *(NeuroBrain, Q-55)*
- [ ] **A12** — Kit mẫu dựng được trong một ngày

---

## 5. Developer Beta và điểm rẽ (I8)

### 5.1 I8 — Developer Beta

| | |
|:---|:---|
| **Mục tiêu** | 50–100 lập trình viên ngoài dùng dòng `1.0.x`; đo B1–B5 (PRD §11.2) và chọn nhánh |
| **Điều kiện vào** | — |
| **Tín hiệu đo** | B1–B5 (§5.5) |
| **Người** | Cả đội |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I8-01** | **Báo cáo B1–B5 và khuyến nghị nhánh** (§5.6) | FR-TEL-01 | trưởng nhóm | ⏳ Chưa bắt đầu | một `Q-N` chọn nhánh |

**Tiêu chí ra I8:**

- [ ] **Tiêu chí 1:** B1–B5 được đo và ghi ở §5.5.
- [ ] **Tiêu chí 2:** Một `Q-N` ghi nhánh đã chọn theo §5.6.

### 5.2 Nguyên tắc vận hành

> **Đóng băng tính năng mới trên dòng `1.0.x`** (R12, Q-39). Ngoại lệ: lỗi chặn người dùng hoàn thành hành trình 10 phút, và lỗi an toàn. RFC, đặc tả, ghi chú thiết kế và CI không đổi hành vi sản phẩm vẫn được merge.

### 5.3 Phân bổ công sức

| Trọng tâm                                  | Tỷ lệ công sức | Người             |
| :------------------------------------------ | :--------------: | :-----------------: |
| Hỗ trợ 1:1 qua Discord và GitHub           | 50%            | Cả đội luân phiên |
| Hoàn thiện tài liệu theo vướng mắc thực tế | 25%            | V3                |
| Sửa lỗi chặn                               | 20%            | V1, V2            |
| Đo đạc và tổng hợp chỉ số                  | 5%             | Trưởng nhóm       |

### 5.4 Mục tiêu tuyển người dùng

| Kể từ khi I8 mở | Mục tiêu tích lũy | Kênh |
| :---: | :--- | :--- |
| ngay khi mở | 10 lập trình viên | Mạng lưới cá nhân, cộng đồng nhúng địa phương, người đã dùng từ I6 |
| +1 tuần | 25 | Bài viết kỹ thuật kèm video demo |
| +2 tuần | 50 | Diễn đàn ESP32, cộng đồng maker |
| +4 tuần | 50–100 | Tích lũy tự nhiên |

### 5.5 Chỉ số phải đo trong Beta

Ngưỡng ở [PRD §11.2](neuroedge-prd.md#112-nghiệm-thu-developer-beta) (B1–B5) và §11.1 (A1); mục này chỉ theo dõi trạng thái và là nơi duy nhất ghi giá trị đo.

| Mã | Chỉ số | Trạng thái | Nguồn đo |
|:---:|:---|:---:|:---|
| **B1** | Lập trình viên ngoài chạy thành công agent trên `sim` | ⏳ Chưa bắt đầu | FR-TEL-01 (TSK-S3-09) |
| **B2** | Lập trình viên ngoài nạp thành công phần cứng thật | ⏳ Chưa bắt đầu | FR-TEL-01 (TSK-S3-09) |
| **B3** | Gate do cộng đồng tự viết và đóng góp — đo, không là điều kiện mở v1.1 (Q-41) | ⏳ Chưa bắt đầu | Đếm tay trên repo công khai |
| **B4** | Tỷ lệ giữ lại và mở rộng test gate mặc định | ⏳ Chưa bắt đầu | Sự kiện telemetry của TSK-S3-09 (Q-41) |
| **B5** | Tỷ lệ chuyển đổi `sim` → phần cứng trong 30 ngày | ⏳ Chưa bắt đầu | FR-TEL-01 (TSK-S3-09) |
| **A1** | TTFV đo đầy đủ trên 10 người độc lập | ⏳ Chưa bắt đầu | Biên bản đo (TSK-I7-02) |

### 5.6 Điểm rẽ

Kết thúc Beta, dự án đi theo đúng một trong ba nhánh. **Quyết định dựa trên số liệu B1–B5, không dựa trên cảm nhận về đà phát triển.**

| Nhánh                               | Điều kiện                                                | Hành động                                                                                                               |
| :----------------------------------- | :-------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------- |
| **Nhánh A — Khởi động Khối 2**      | Đạt đồng thời B1, B2 (Q-41)                              | Tuyển V4, bắt đầu **Fleet OS** (thương mại) theo §8; song song hoàn thiện lớp provider tự vận hành |
| **Nhánh B — Kéo dài Beta 4–6 tuần** | Đạt 1 trên 2 tiêu chí, tiêu chí còn lại đạt ≥ 60% ngưỡng | Giữ đóng băng tính năng, tập trung vào tiêu chí yếu nhất, đánh giá lại sau 6 tuần kể từ lúc kéo dài |
| **Nhánh C — Xem xét lại luận điểm** | Không đạt tiêu chí nào, hoặc đạt 1 mà tiêu chí kia < 60% | Dừng lộ trình thương mại. Phỏng vấn sâu 20 người dùng đã thử và bỏ. Xác định luận điểm sai ở đâu trước khi viết thêm mã |


**Chỉ báo quan trọng nhất là B2** (10 người ngoài nạp được phần cứng thật). B1 đo sự tò mò; B2 đo cam kết. Một dự án có B1 cao nhưng B2 thấp là một dự án mà simulator hấp dẫn còn đường lên phần cứng bị nghẽn — khi đó việc cần làm là sửa đường lên phần cứng, không phải xây Fleet OS.

---

## 6. Tầng dịch vụ v1.1 (I9–I10)

Khởi động **chỉ khi** đi nhánh A (B1 và B2, Q-41). Hai increment chạy song song.

### 6.1 I9 — Lớp provider v1.1 và Fleet OS

| | |
|:---|:---|
| **Mục tiêu** | Fleet OS — dịch vụ thương mại duy nhất — và phần v1.1 của lớp provider tự vận hành (U3/J4, J5 → M4, M5) |
| **Điều kiện vào** | Nhánh A; V4 đã tuyển; broker MQTT chọn bằng đo tải (Q-11) |
| **Tín hiệu đo** | G-a và G-c, 90 ngày sau khi phát hành (Q-43); C1 |
| **Người** | V4, V1 |

Ba task đầu (TSK-K2-01→03) là phần **hoàn thiện lớp trừu tượng provider tự vận hành** đã dựng từ I0 — giữ nguyên mã task để không vỡ truy vết, nhưng không thương mại hóa.

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-K2-01** | Lớp provider tự vận hành: gom một endpoint, một credential, xoay khóa do người dùng tự quản lý | FR-GW-01, FR-GW-02 | V4 | ⏳ Chờ nhánh A của I8 | `python/neuroedge/models/providers/auth.py` · Nghiệm thu: Một cấu hình phục vụ nhiều provider; xoay khóa không nạp lại firmware |
| **TSK-K2-02** | Lớp provider tự vận hành: định tuyến đa nhà cung cấp, failover (kể cả khai trong `agent.toml`, Q-28), hạn mức theo thiết bị *(tùy chọn)* | FR-GW-03, FR-GW-05, FR-TEL-06 | V4 | ⏳ Chờ nhánh A của I8 | `python/neuroedge/models/providers/routing.py` · Nghiệm thu: Ngắt nhà cung cấp chính, thiết bị không gián đoạn |
| **TSK-K2-03** | Lớp provider tự vận hành: giao thức tối ưu edge, xuất vết ghi đồng nhất định dạng | FR-GW-04, FR-GW-06, FR-GW-07 | V4 | ⏳ Chờ nhánh A của I8 | `python/neuroedge/models/providers/traces.py` · Nghiệm thu: Vết ghi từ lớp provider replay được trên máy cá nhân |
| **TSK-K2-04** | Fleet: cấp phát danh tính và chứng chỉ thiết bị | FR-FLT-01 | V4 | ⏳ Chờ nhánh A của I8 | `services/fleet/provisioning.py` · Nghiệm thu: Claim tự động trên lô 100 thiết bị |
| **TSK-K2-05** | Fleet: sổ kiểm kê, giám sát sức khỏe, dashboard hữu ích ở n = 1 | FR-FLT-03, FR-FLT-06 | V4 | ⏳ Chờ nhánh A của I8 | `services/fleet/inventory.py` · Nghiệm thu: Trạng thái phản ánh đúng trong 60 giây |
| **TSK-K2-06** | Fleet: cập nhật cấu hình, bí mật và gate từ xa | FR-FLT-04 | V4 | ⏳ Chờ nhánh A của I8 | `services/fleet/config_sync.py` · Nghiệm thu: Đổi ngưỡng gate toàn đội, không nạp lại firmware |
| **TSK-K2-07** | Fleet: điều phối OTA canary 1% → 10% → 100%, tự dừng khi vượt ngưỡng lỗi | FR-FLT-02 | V4 | ⏳ Chờ nhánh A của I8 | `services/fleet/canary.py` · Nghiệm thu: **1.000 thiết bị / 0 brick** |
| **TSK-K2-08** | Fleet: tự động tải vết ghi sự cố về kho tập trung | FR-FLT-05 | V4 | ⏳ Chờ nhánh A của I8 | `services/fleet/trace_collector.py` · Nghiệm thu: Sự cố xuất hiện trong kho dưới 5 phút |
| **TSK-K2-09** | **Thu hồi chứng chỉ thiết bị** | NFR-SEC-05 | V4 | ⏳ Chờ nhánh A của I8 | `services/fleet/` |

**Đòn bẩy OSS:** Eclipse Hawkbit cho điều phối chiến dịch OTA canary · broker MQTT giấy phép dễ dãi (Q-11) hoặc FastAPI WebSockets cho kết nối và viễn trắc. **LiteLLM không còn là lõi của một gateway do NeuroEdge vận hành** — nó là thư viện của lớp trừu tượng provider self-host, đã dùng từ I0 và nay thuộc phần phân phối kèm sản phẩm (proposal Phụ lục H.1). Tiết kiệm ước tính 14 tuần. Xem ngoại lệ giấy phép tại §3.3.

**Tiêu chí ra I9:**

- [ ] **Tiêu chí 1:** TR-1, TR-2, TR-3, TR-6 và TR-7 đạt (§6.3).

### 6.2 I10 — Registry và các đường ray

| | |
|:---|:---|
| **Mục tiêu** | `gate add` từ một registry có ký; định danh ổn định, đo lường và sandbox — ba đường ray không bổ sung sau được (U2/J7 → C5) |
| **Điều kiện vào** | Nhánh A; Q-5 đã chốt |
| **Tín hiệu đo** | C5; G-d, 12 tháng sau khi phát hành (Q-43) |
| **Người** | V4, V1, V3 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-K3-01** | Định danh ổn định cho thiết bị, agent, gate | FR-REG-05 | V4 | ⏳ Chờ nhánh A của I8 | `services/registry/identity.py` |
| **TSK-K3-02** | Hệ đo lường theo lượt gọi agent và lượt thẩm định gate | FR-REG-06, FR-TEL-04 | V4 | ⏳ Chờ nhánh A của I8 | `services/metering/engine.py` |
| **TSK-K3-03** | Manifest và chuẩn phiên bản SemVer | FR-REG-02, FR-GATE-10 | V4 | ⏳ Chờ nhánh A của I8 | `schemas/manifest.v1.json` |
| **TSK-K3-04** | Kho Gate công khai miễn phí | FR-REG-01 | V4 | ⏳ Chờ nhánh A của I8 | `services/registry/oci_store.py` |
| **TSK-K3-05** | Cơ chế phân quyền và sandbox | FR-REG-07 | V4 | ⏳ Chờ nhánh A của I8 | `services/registry/sandbox.py` |
| **TSK-K3-06** | Kho chia sẻ adapter kết nối provider do cộng đồng đóng góp, dùng chung hạ tầng Registry của TSK-K3-04 (CR-1.0) | FR-REG-08 | V4 | ⏳ Chờ nhánh A của I8 | `services/registry/adapters.py` |
| **TSK-S3-21** | **Ghim `extends` bằng digest** (`@<ver>#sha256:…`) + `digests.lock` thành lock của `extends` + kiểm danh tính `URI ↔ name/version` | FR-GATE-05, FR-GATE-06 | V1 | ⏳ Chưa bắt đầu | Cần một RFC riêng — RFC-0003 đã chấp thuận không gồm việc này (`TODOS.md` #15); làm trước khi Registry nhận gate bên ngoài (`TODOS.md` #11) |
| **TSK-W2-04** | **Ký gate và kiểm chữ ký trên thiết bị** (OCI/ORAS); ký vết ghi (`TODOS.md` #1) | FR-REG-04 | V4 | ⏳ Chờ nhánh A của I8 | `services/registry/` · firmware |

**Thứ tự này không tùy tiện.** FR-REG-05, FR-REG-06 và FR-REG-07 phải đi trước vì không bổ sung sau được: thiếu định danh ổn định và đo lường thì Registry không quy kết được ai dùng gì; thiếu sandbox thì không dám cho mã người lạ chạy trên thiết bị có cơ cấu chấp hành.

**Đòn bẩy OSS:** CNCF ORAS và Harbor cho kho Gate Registry theo chuẩn OCI · OpenMeter cho hệ đo lường tương thích Stripe Billing. Tiết kiệm ước tính 8 tuần.

**Tiêu chí ra I10:**

- [ ] **Tiêu chí 1:** TR-4 và TR-5 đạt (§6.3).
- [ ] **Tiêu chí 2:** `extends` ghim được bằng digest trước khi registry nhận gate bên ngoài (TSK-S3-21).

### 6.3 Tiêu chí ra v1.1 cấp thực thi (TR-1 → TR-7)

Bảy tiêu chí **TR-1 đến TR-7** dưới đây là tiêu chí ra **cấp thực thi** của I9 và I10. Chúng là một bộ **khác** với bộ nghiệm thu phát hành **C1–C8** của PRD §11.3: TR đo *việc đã làm xong chưa*, C đo *sản phẩm đã đủ điều kiện phát hành chưa*. Cột cuối chỉ rõ mỗi TR phục vụ tiêu chí C nào; TR nào không có C tương ứng là tiêu chí nội bộ của roadmap.

| Mã | Tiêu chí ra I9 và I10 | Phục vụ tiêu chí nghiệm thu PRD |
|:---|:---|:---:|
| **TR-1** | Provider Layer Self-Host | — *(nội bộ)* |
| **TR-2** | Zero-Brick Fleet OTA | **C1** |
| **TR-3** | Incident MTTR dưới 10 phút | — *(nội bộ)* |
| **TR-4** | Registry Verified Gates | Tiền đề của **C5** |
| **TR-5** | Usage Attribution | — *(nội bộ)* |
| **TR-6** | Failover Resiliency | — *(nội bộ; hiện thực hóa FR-GW-03)* |
| **TR-7** | Fleet Remote Config | — *(nội bộ)* |

*Tiêu chí PRD **C2, C3, C4, C6, C7, C8** không có TR tương ứng vì chúng được đo ở mức sản phẩm sau khi I9 và I10 hoàn tất, không đo được trong lúc thực thi. C6 là chỉ số theo dõi, không là điều kiện phát hành (Q-42).*

- **TR-1 (Provider Layer Self-Host):** Lớp trừu tượng provider chạy tự vận hành trên hạ tầng của người dùng; thiết bị biên không nhúng cứng API key của từng nhà cung cấp, và khóa xoay được mà không nạp lại firmware.
- **TR-2 (Zero-Brick Fleet OTA):** Triển khai thử nghiệm 1.000 thiết bị ảo/thật qua canary; tỷ lệ brick là 0%.
- **TR-3 (Incident MTTR < 10m):** Vết ghi sự cố từ thiết bị được tải về dashboard trung tâm trong dưới 5 phút; kỹ sư tái hiện lỗi bằng `replay` trong dưới 5 phút tiếp theo.
- **TR-4 (Registry Verified Gates):** Ít nhất 10 gate mã nguồn mở được publish lên Gate Registry có kiểm định tự động.
- **TR-5 (Usage Attribution):** Hệ đo lường OpenMeter đối soát chính xác 100% số lượt gọi mô hình và phán quyết gate tới cấp thiết bị *(phục vụ vận hành và đối soát nội bộ — NeuroEdge không thu phí trên lượt gọi mô hình)*.
- **TR-6 (Failover Resiliency):** Giả lập ngắt kết nối nhà cung cấp LLM chính; lớp trừu tượng provider tự động chuyển sang nhà cung cấp dự phòng trong dưới 2 giây.
- **TR-7 (Fleet Remote Config):** Đổi chính sách gate từ dashboard điều khiển từ xa có hiệu lực trên toàn đội dưới 30 giây mà không cần khởi động lại firmware.

---

## 7. Hướng mở rộng sau Beta (I11, I13, I14, I16–I18)

Thứ tự theo phụ thuộc (Q-40); NeuroBrain và thị giác trên `linux` đã gộp vào MVP (Q-53, Q-55) — §7.2, §7.5. Thiết kế chi tiết nằm ở ghi chú thiết kế; mục này chỉ giữ task, tiêu chí ra và điều kiện vào.

### 7.1 I11 — Mở danh sách target

| | |
|:---|:---|
| **Mục tiêu** | Mở enum `target` theo phân tầng bậc; bậc máy đọc được trong mã lõi — điều kiện của I13, I14 (node RP2350) và I16 (Jetson). Không viết driver, không đụng TTFV |
| **Điều kiện vào** | RFC-0002 được chấp thuận (kỹ thuật trưởng) |
| **Tín hiệu đo** | Số profile bậc 3 gửi tới |
| **Người** | V1 |
| **Thiết kế** | [`neuroedge-design-phase2.md`](neuroedge-design-phase2.md) §5 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-V1a-01** | Hoàn thiện và bảo vệ RFC-0002 qua thảo luận | FR-TGT-08, FR-HAL-01 | V1 | ⏳ Chưa bắt đầu | `docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md` |
| **TSK-V1a-02** | Mở enum `target` ở hai lược đồ | FR-TGT-08 | V1 | ⏳ Chưa bắt đầu | `schemas/board.v1.json` · `schemas/trace.v1.json` |
| **TSK-V1a-03** | Bậc máy đọc được `TARGET_TIERS` do lõi sở hữu; kiểm khoá capability lạ lúc nạp | FR-TGT-08, FR-HAL-05 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/hal/board.py` |
| **TSK-V1a-04** | Thu hẹp ba bất biến kiểm thử theo bậc, **không bỏ khẳng định** (RFC-0002 §5) | FR-HAL-04, FR-TGT-08 | V1 | ⏳ Chưa bắt đầu | `python/tests/test_boards.py` · `python/tests/test_schemas.py` |
| **TSK-V1a-05** | CLI: `board validate <path>`, `board show` theo danh sách nguyên thủy, kiểm tên mọi cờ `--target` | FR-HAL-05 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/cli/main.py` · `python/tests/test_cli.py` |
| **TSK-V1a-06** | Cập nhật corpus phản chứng: sửa `why_contains` của `unknown_target.json`; giữ `rp2040` (lỗi gõ thật, vẫn ngoài enum mới) | FR-TRC-08 | V1 | ⏳ Chưa bắt đầu | `fixtures/traces/expected_errors.yaml` |

**Tiêu chí ra I11:**

- [ ] **Tiêu chí 1:** RFC-0002 ở trạng thái ✅ Đã chấp thuận, có chữ ký kỹ thuật trưởng.
- [ ] **Tiêu chí 2:** Một `board.toml` khai `target = "jetson"` thẩm định qua, đồng thời một tệp khai target bịa đặt vẫn bị từ chối kèm thông báo liệt kê target theo bậc.
- [ ] **Tiêu chí 3:** Ba bo mạch bậc 1 vẫn khai đủ năm nguyên thủy; `neuroedge verify --targets sim,linux,esp32s3` vẫn đạt 100%.
- [ ] **Tiêu chí 4:** `neuroedge board validate` trên một profile tổng hợp `target = "rp2350"` không có `display` thoát 0 và in "bậc 3"; cùng profile đó khai `target = "linux"` thì bị từ chối vì bậc 1 phải đủ năm nguyên thủy.
- [ ] **Tiêu chí 5:** `boards/` vẫn chỉ chứa ba profile bậc 1; `pytest` xanh, 0 skipped.

### 7.2 NeuroBrain — đã gộp vào MVP

NeuroBrain không còn là increment sau Beta (Q-55 thay phần thứ tự NeuroBrain của Q-40): task của nó nằm ở **I4a** (host: N0, N1, N3–N6, N5b) và **I5a** (chip: N7); phong bì N2, RFC-0007 (TSK-N0-03) và spike ADC (TSK-N3-03) nằm ở **I2a**, cưỡng chế phong bì trong firmware (TSK-N7-02) ở **I3a**. Mã task giữ nguyên.

### 7.3 I13 — Bộ port cộng đồng

| | |
|:---|:---|
| **Mục tiêu** | Người ngoài tự port NeuroEdge lên bo bậc 3 chỉ bằng tài liệu công khai (U5 → V-G5). Đội lõi xuất bản bộ công cụ, không tự port — ngoại lệ RP2350 làm node robot (Q-33, I14) |
| **Điều kiện vào** | — |
| **Tín hiệu đo** | Bản port bậc 3 đầu tiên của người ngoài; thời gian hỗ trợ của đội lõi |
| **Người** | V3, V1 |
| **Thiết kế** | [`neuroedge-design-phase2.md`](neuroedge-design-phase2.md) §9.1 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-P1-01** | Bộ vector tuân thủ độc lập ngôn ngữ, đóng gói chạy được ngoài repo | FR-GOV-03 | V1 | ⏳ Chưa bắt đầu | `fixtures/compliance/portable/` |
| **TSK-P1-02** | Hướng dẫn port HAL: hợp đồng tối thiểu, cạm bẫy, cách tự kiểm chứng | FR-TGT-08, FR-GOV-03 | V3 | ⏳ Chưa bắt đầu | `docs/porting/` |
| **TSK-P1-03** | Khung port mẫu cho một vi điều khiển không phải ESP32 | FR-TGT-08 | V3 | ⏳ Chưa bắt đầu | `targets/_template/` |
| **TSK-P1-04** | Quy trình công nhận bậc 3: bên đóng góp tự chạy và công bố kết quả | FR-TGT-08 | V3 | ⏳ Chưa bắt đầu | `docs/porting/tier3.md` |
| **TSK-P1-05** | **`neuroedge board check <tệp>`** — đạt/thiếu so với bậc, chạy bộ vector tuân thủ trên profile bậc 3 | FR-TGT-08 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/cli/` |

**Tiêu chí ra I13:**

- [ ] **Tiêu chí 1:** Một kỹ sư ngoài đội hoàn thành một bản port bậc 3 **chỉ dựa vào tài liệu công khai**, không hỏi đội lõi.
- [ ] **Tiêu chí 2:** Bản port đó vượt bộ vector tuân thủ, kết quả kiểm chứng lại được bởi bên thứ ba.
- [ ] **Tiêu chí 3:** Thời gian đội lõi bỏ ra hỗ trợ bản port đầu tiên dưới 8 giờ.

### 7.4 I14 — Robot phân tầng

| | |
|:---|:---|
| **Mục tiêu** | Một robot Pi 5 + nhiều node MCU; mỗi node tự lượng giá gate; mất liên lạc thì về trạng thái an toàn; ROS 2/Nav2 có gate (Q-32 → Q-38). PWM, tiêu chí số và `motion.*` (khối W1) đã vào MVP ở I2a, I3a (Q-53) |
| **Điều kiện vào** | Nhu cầu hoặc đối tác thật (PF-3); `TODOS.md` #40 trả lời trước TSK-W4-01 và W4-07; nút dừng khẩn phần cứng bắt buộc cho robot di động (Q-38) |
| **Tín hiệu đo** | DoD-1, DoD-2, DoD-3, DoD-5 của ghi chú thiết kế robot §1 |
| **Người** | V2, V1 |
| **Thiết kế** | [`draft-ke-hoach-mo-rong-robot-fofoca.md`](draft-ke-hoach-mo-rong-robot-fofoca.md) · [`draft-rfc-node-giao-thuc-dieu-phoi.md`](../docs/rfc/draft-rfc-node-giao-thuc-dieu-phoi.md) |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-W2-01** | **mTLS hoặc PSK giữa Pi và node** — không cần Fleet OS | NFR-SEC-04 | V2 | ⏳ Chưa bắt đầu | firmware · `python/` |
| **TSK-W2-03** | **TPM cho Pi (`linux`)** — bổ sung cho Secure Boot của TSK-S6-05 | NFR-SEC-02, NFR-SEC-03 | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/hal/linux.py` |
| **TSK-W3-01** | **Spike Zenoh-pico ↔ Pi** trên ESP32-S3 và RP2350: phép thử loại theo ba ngưỡng của Q-36; trượt thì đo micro-ROS cùng điều kiện | — | V2 | ⏳ Chưa bắt đầu | `docs/reports/` |
| **TSK-W3-02** | **RFC-node:** mô hình node, ý định trên wire, black channel, heartbeat → trạng thái an toàn, vết ghi đa node | FR-TGT-08 | V1 | ⏳ Chưa bắt đầu | `docs/rfc/` (từ `draft-rfc-node-giao-thuc-dieu-phoi.md`) |
| **TSK-W3-03** | **Lớp black channel:** wrapper + watchdog + chống phát lại | NFR-SEC-09 | V1 + V2 | ⏳ Chưa bắt đầu | `python/` + firmware |
| **TSK-W3-04** | **Vết ghi hợp nhất đa node** theo phương án A (Q-32): trường tùy chọn trong `metadata`, không sửa `schemas/` | FR-TRC-05 | V1 | ⏳ Chưa bắt đầu | `docs/spec/simulation_coverage.md` · `fixtures/compliance/multinode/` |
| **TSK-W3-06** | **`verify` cho cụm node** — tương đương miền phán quyết; lệch → NE4002 | FR-CI-07 | V1 | ⏳ Chưa bắt đầu | CLI + CI |
| **TSK-W3-07** | **Port RP2350 làm node thứ hai** (Q-33): HAL C trên Pico SDK (`digital.out`, `sensor.read`), walker + sổ token C99 cho ARM, profile bo mạch, runner trên mạch thật | FR-TGT-08 | V2 | ⏳ Chưa bắt đầu | `targets/rp2350/` |
| **TSK-P2-05** | **MCP cho thiết bị MCU qua gateway:** gateway đưa tool của `esp32s3` ra MCP, chuyển tool call xuống thiết bị; **thiết bị vẫn tự lượng giá gate**, gateway không cấp token | FR-GW-01, FR-MDL-10 | V1 + V2 | ⏳ Chưa bắt đầu | `docs/spec/tool_calling.md` §8 |
| **TSK-W4-01** | **Cầu ROS 2 tại ranh giới gate** (chỉ `linux`) + Nav2 tích hợp nguyên bản, gate xét mọi lệnh tốc độ (Q-34) | FR-MDL-10 | V1 | ⏳ Chưa bắt đầu | `python/` |
| **TSK-W4-07** | **RFC an toàn robot di động** (giới hạn tốc độ, vùng cấm, gate 10–20 lần/giây) và câu C6 với người mua robot (`TODOS.md` #40) | — | V1 + trưởng nhóm | ⏳ Chưa bắt đầu | `docs/rfc/` |

**Tiêu chí ra I14:**

- [ ] **Tiêu chí 1:** DoD-1 — Pi 5 và ít nhất hai node MCU (ESP32-S3, RP2350) chạy HAL và gate cục bộ, liên lạc qua black channel.
- [ ] **Tiêu chí 2:** DoD-2 — fault injection (drop, delay, replay, tamper): không ALLOW nào lọt; mất liên lạc thì node về trạng thái an toàn theo từng cơ cấu (Q-35).
- [ ] **Tiêu chí 3:** DoD-3 — vết ghi hợp nhất đa node replay được trong CI (TSK-W3-04, W3-06).
- [ ] **Tiêu chí 4:** DoD-5 — OTA có ký và mTLS/PSK giữa Pi và node demo được (TSK-W2-01).

### 7.5 Thị giác trên `linux` — đã gộp vào MVP

Thị giác không còn chờ nhu cầu camera sau Beta (Q-53): TSK-V1b-01 → V1b-08 nằm ở **I2a** (`sim` + `linux`), `vision.in` trên chip ở **I3a** (TSK-I3a-04). Kết quả thị giác vào gate dưới dạng dữ kiện do maker khai, ngưỡng tin cậy khoá bằng tiêu chí số (Q-54). Mã task giữ nguyên.

### 7.6 I16 — Thị giác trên `jetson`

| | |
|:---|:---|
| **Mục tiêu** | Nâng `jetson` lên target bậc 2: đội lõi bảo trì, kiểm chứng trên miền phán quyết, không cam kết nightly |
| **Điều kiện vào** | Chỉ mua Jetson sau khi tiêu chí thị giác của I2a đạt (tiêu chí 6) |
| **Tín hiệu đo** | Tiêu chí ra bên dưới |
| **Người** | V5 |
| **Thiết kế** | [`neuroedge-design-phase2.md`](neuroedge-design-phase2.md) §7 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-V2-01** | Port HAL lên Jetson Orin qua JetPack | FR-TGT-08, FR-HAL-01 | V5 | ⏳ Chưa bắt đầu | `targets/jetson/hal/` |
| **TSK-V2-02** | Đường dẫn thị giác tăng tốc GPU, giữ nguyên giao diện trừu tượng | FR-MDL-04 | V5 | ⏳ Chưa bắt đầu | `targets/jetson/vision/` |
| **TSK-V2-03** | `neuroedge verify` cho `jetson` trên miền phán quyết | FR-CI-07, FR-TGT-08 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/cli/main.py` (`verify`) |
| **TSK-V2-04** | Profile bo mạch `jetson-orin-nano` | FR-HAL-02 | V5 | ⏳ Chưa bắt đầu | `boards/jetson-orin-nano.toml` |

**Phạm vi bị loại tường minh:** tự phát triển SLAM, tránh vật cản, dẫn đường tự hành, drone (PRD §14). Ngoại lệ Q-34: tích hợp nguyên bản ROS 2/Nav2 có gate xét mọi lệnh tốc độ, trong I14.

**Tiêu chí ra I16:**

- [ ] **Tiêu chí 1:** Cùng một agent thị giác chạy không sửa trên `linux` và `jetson`.
- [ ] **Tiêu chí 2:** `neuroedge verify` đạt 100% trên miền phán quyết giữa `linux` và `jetson`.
- [ ] **Tiêu chí 3:** Ngưỡng chất lượng của target bậc 1 **không suy giảm** — kiểm thử hằng đêm trên `esp32s3` vẫn xanh suốt khối.

### 7.7 I17 — Đa phương thức

| | |
|:---|:---|
| **Mục tiêu** | Hợp nhất thoại và thị giác trong một máy trạng thái; gate đa phương thức |
| **Điều kiện vào** | TSK-V3-04 (RFC ngữ nghĩa gate cho bằng chứng thị giác) được chấp thuận trước phần gate đa phương thức |
| **Tín hiệu đo** | Tiêu chí ra bên dưới |
| **Người** | V1, V5 |
| **Thiết kế** | [`neuroedge-design-phase2.md`](neuroedge-design-phase2.md) §8 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-V3-01** | Hợp nhất thoại, thị giác và cảm biến vào một máy trạng thái | FR-PER-01→05 | V1 + V5 | ⏳ Chưa bắt đầu | `python/neuroedge/perception/fusion/` |
| **TSK-V3-02** | Mở rộng bộ vector tuân thủ cho luồng đa phương thức | FR-CI-07 | V1 | ⏳ Chưa bắt đầu | `fixtures/compliance/multimodal/` |
| **TSK-V3-03** | Gate đa phương thức *(phụ thuộc RFC ngữ nghĩa gate thị giác)* | FR-GATE-03 | V1 | ⏳ Chưa bắt đầu | `schemas/gate.v2.json` *(nếu RFC yêu cầu tăng phiên bản)* |
| **TSK-V3-04** | **RFC ngữ nghĩa gate cho bằng chứng thị giác** — điều kiện của gate đa phương thức | FR-GATE-03 | V1 | ⏳ Chưa bắt đầu | `docs/rfc/` |

**Tiêu chí ra I17:**

- [ ] **Tiêu chí 1:** Một agent phản ứng đúng khi lời nói và hình ảnh mâu thuẫn nhau, hành vi được đặc tả trước chứ không phát sinh.
- [ ] **Tiêu chí 2:** Mất một trong hai phương thức → suy giảm có kiểm soát, không chặn toàn bộ và không hành động sai.
- [ ] **Tiêu chí 3:** Máy trạng thái hợp nhất vượt toàn bộ bộ vector tuân thủ cũ, không hồi quy luồng thoại.

### 7.8 I18 — Hệ sinh thái thiết bị

| | |
|:---|:---|
| **Mục tiêu** | SDK đa thiết bị, kho HAL port, chứng nhận miễn phí tự kiểm chứng (U5 → V-G3, V-G5) |
| **Điều kiện vào** | Ít nhất 3 bản port bậc 3 do cộng đồng hoàn thành (PRD §14) |
| **Tín hiệu đo** | V-G5 |
| **Người** | V3 |
| **Thiết kế** | [`neuroedge-design-phase2.md`](neuroedge-design-phase2.md) §9.2 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-P2-01** | Kho adapter và HAL port do cộng đồng đóng góp, dùng chung hạ tầng Registry | FR-TGT-08 | V3 | ⏳ Chưa bắt đầu | `services/registry/ports.py` |
| **TSK-P2-02** | Hiển thị trạng thái tuân thủ của adapter đang chạy trên Fleet Dashboard | FR-FLT-03 | V3 | ⏳ Chưa bắt đầu | `services/fleet/compliance_view.py` |
| **TSK-P2-03** | Chứng nhận phần cứng **miễn phí, tự kiểm chứng** — công bố kết quả, không bảo chứng | FR-GOV-03 | V3 | ⏳ Chưa bắt đầu | `docs/porting/certification.md` |
| **TSK-P2-06** | **Chứng nhận tự kiểm "NeuroEdge-gated"** cho runtime/MCP server bên thứ ba: chạy corpus `fixtures/tool_calls/`, công bố kết quả — cùng nguyên tắc với TSK-P2-03 | FR-GOV-03 | V3 | ⏳ Chưa bắt đầu | `docs/spec/tool_calling.md` §9 |

**Hai ranh giới của P2:**

- **Không làm marketplace riêng.** Việc thương mại hóa trao đổi tài sản thuộc **Khối 5** (proposal §8.8) và chỉ kích hoạt sau cột mốc G1–G4. P2 chỉ làm phần miễn phí.
- **Chứng nhận không thu phí và không bảo chứng.** Chương trình chứng nhận **có thu phí** vẫn ở trạng thái Chặn tại PRD §14. NeuroEdge công bố kết quả bộ kiểm thử do bên đóng góp tự chạy, không đứng ra bảo đảm chất lượng bo mạch bên thứ ba — tránh nghĩa vụ pháp lý mà tổ chức chưa đủ quy trình để gánh.

**Tiêu chí ra I18:**

- [ ] **Tiêu chí 1** *(đề xuất, duyệt khi I18 mở)*: ít nhất 3 bản port bậc 3 được niêm yết kèm kết quả tự kiểm chứng công khai.

---

## 8. Ngoài roadmap

### 8.1 Phụ thuộc ngoài

| Hạng mục | Điều kiện | Vì sao roadmap cần biết |
|:---|:---|:---|
| **Khối 4 — AURA thực địa** | Sau I8; API ổn định và một đối tác ngoài thành công trên phần cứng thật (proposal §8.6) | Là nguồn dữ liệu cho G-e (Q-43); nhu cầu camera không còn chặn thị giác (Q-53) |
| **Khối 5 — Marketplace** | Đạt G1–G4; Chặn ở PRD §14 | I18 chỉ làm phần miễn phí |

### 8.2 Task hoãn, chưa thuộc increment nào

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S2-06** | Lượng giá `allow_when` trên nền Google CEL, kèm đường biên dịch gate cho thiết bị (§3.8, Q-9) | FR-GATE-03 | V1 | ⏸ **Hoãn** — chưa thuộc increment nào (`TODOS.md` #42) | Dạng mapping đủ cho wedge; CEL là front-end biên dịch xuống *cùng* cây quyết định của TSK-S2-12 (Q-9 phương án A) |

---

## 9. Thang cắt phạm vi

**MVP không có thang cắt (Q-52).** Mọi increment của MVP (I0 → I7, gồm I2a, I2b, I3a, I4a, I5a) trượt thì dời
ngày cùng PR có bằng chứng (R5), không cắt phạm vi. Thang cắt chỉ còn cho các increment mở rộng sau Beta (§9.3).

### 9.1 Tuyệt đối không cắt


| Hạng mục                              | Lý do                                                           |
| :------------------------------------- | :--------------------------------------------------------------- |
| Hợp đồng năng lực HAL                 | Là nền của tương đương target                                   |
| Gate Engine và fail-closed            | Là mệnh đề trung tâm của sản phẩm                               |
| Lược đồ vết ghi và record/replay      | Không retrofit được                                             |
| Golden Reference                      | Không có nó thì Action CI chỉ là một thư viện test thông thường |
| `sim` là target thật, không phải mock | Cắt cái này là cắt toàn bộ luận điểm                            |
| Nguyên tắc kế thừa gate an toàn       | Thiếu nó, `extends` là rủi ro chứ không phải tính năng          |
| Phạm vi MVP (Q-52): bốn gói nguyên thủy mở rộng trên ba target, kit mẫu, NeuroBrain | Quyết định của chủ sản phẩm: MVP trượt thì dời ngày cùng PR có bằng chứng (R5), không cắt |


### 9.2 Không còn bậc 5

Bậc 5 cũ (tách thoại khỏi MCU) đã bị bỏ (Q-44): thoại trên ESP32-S3 là bắt buộc cho v1.0, vì A6 đo trên
pipeline âm thanh và vì demo thoại trên chip là điều kiện công khai (Q-39). Rủi ro **R-1** vì vậy không còn lối
thoát bằng cắt phạm vi: trượt ngân sách bộ nhớ thì mở một `Q-N` lập lại kế hoạch I5 và dời dự báo v1.0.

---

### 9.3 Thang cắt trong từng increment

Chỉ cho increment sau Beta (Q-52). Cắt từ trái sang phải khi increment đó trượt; không cắt cột cuối.

| Increment | Cắt theo thứ tự | Tuyệt đối không cắt |
|:---|:---|:---|
| **I16–I18** | I17 → I16 → I18 | I11 — rẻ nhất (một RFC nới lỏng) và là điều kiện của I13, I14, I16. Cắt I13 thì I14 port RP2350 không có khung mẫu |

---

## 10. Lịch chốt quyết định

**Sổ quyết định là PRD §15** — nội dung, lý do và phương án đã cân nhắc của mọi `Q-N` chỉ nằm ở đó. Mục này chỉ theo dõi ngày chốt, hạn chốt, người quyết và task áp dụng; nó không định nghĩa quyết định mới. Khi hai tài liệu lệch nhau, PRD §15 đúng.

### 10.1 Các quyết định đã chốt

| Mã | Tên ngắn | Chốt | Task / nơi áp dụng |
|:---:|:---|:---:|:---|
| **Q-1** | Python tối thiểu 3.11 | — | NFR-COMP-05 |
| **Q-2** | Bo mạch tham chiếu ESP32-S3-Box-3 | — | Phụ lục B |
| **Q-3** | Ngân sách bộ nhớ và firmware | — | TSK-S1-10, S4-11, S5-05 |
| **Q-4** | Nhà cung cấp System 1 / System 2 ở v1.0 | sửa 2026-09-23 | TSK-S2-08, S2-11 · `TODOS.md` #27 |
| **Q-7** | Wake-word mặc định *"Hey Neuro"* | — | I4, I5 |
| **Q-8** | C/C++ cho firmware, Python cho `sim`/`linux` | — | §3.8 |
| **Q-9** | Biên dịch gate lúc build (phương án A) | — | TSK-S2-12, S4-02 |
| **Q-10** | LiteLLM dạng SDK, extra `neuroedge[cloud]` | 2026-09-23 | TSK-S2-11 |
| **Q-12** | Chuẩn OpenAI API + adapter tự viết | CR-1.0 | TSK-S2-11 |
| **Q-13** | Phân tầng ba bậc target | CR-1.0 | RFC-0002, Giai đoạn 2 |
| **Q-14** | Mất mạng + fallback lệnh cố định cục bộ | 2026-09-23 | TSK-S2-08, S5-07, S1-10 |
| **Q-15** | Đầu vào mặc định của `sim` là gõ chữ | 2026-09-23 | TSK-S2-08, S3-06 |
| **Q-16** | `gpio-sim` cho `linux` trong CI | 2026-09-23 | TSK-S3-05, Phụ lục B |
| **Q-17** | Hành vi `on_block` ở v1.0 | 2026-09-23 | TSK-S2-03, §11.3 |
| **Q-18** | Kế thừa `budget`/`on_block` (RFC-0004) | 2026-09-23 | TSK-S2-13 |
| **Q-19** | Lịch Sprint 2–3 theo ngày tuyệt đối | 2026-09-23 | lịch sử (Q-39) |
| **Q-20** | Cổng nhu cầu mềm 2026-10-25 — **đã bỏ bởi Q-56** | 2026-09-23 | `TODOS.md` #19 |
| **Q-21** | Mô phỏng theo tầng bằng OSS | 2026-09-23 | TSK-S4-07, S4-08, S4-10, S5-08, S5-09 |
| **Q-22** | AEC phần mềm PipeWire trên `linux` | 2026-09-23 | TSK-S5-08 |
| **Q-23** | Cây quyết định trên MCU: bố cục nhị phân | 2026-09-23 | TSK-S4-02, RFC-0003 |
| **Q-24** | Hành động là tool call · MCP | 2026-09-23 | TSK-S3-24, FR-CLI-12 |
| **Q-25** | Ràng buộc tham số trong gate (RFC-0005, 2026-09-24) | 2026-09-23 | TSK-S3-25 |
| **Q-26** | Chỉ người xác nhận `ask` (RFC-0006, 2026-09-24) | 2026-09-23 | TSK-S3-26 |
| **Q-27** | System 2 làm MCP host | 2026-09-23 | TSK-S3-28 |
| **Q-28** | Mốc giao FR-GW: 01, 03 tối thiểu ở v1.0 | 2026-09-24 | TSK-S2-11, K2-01→03 |
| **Q-29** | Định vị trước MHS: theo dõi, adapter cộng đồng khi chuẩn mở | 2026-09-24 | `TODOS.md` #32–#33, Phụ lục H.3 |
| **Q-30** | Định vị "Hợp đồng vào Physical AI" (engine-first) | 2026-09-24 | PRD §15; `TODOS.md` #32, #34; phase1-5 §1 |
| **Q-11** | Hawkbit duyệt, EMQX thay bằng broker giấy phép dễ dãi (phần còn lại) | 2026-09-25 | Khối 2 |
| **Q-31** | NeuroBrain — "Build Physical AI by conversation, under contract" | 2026-09-25 | phase1-5 §1 |
| **Q-32** | Nhận hướng robot phân tầng, sau Developer Beta (+ trace `v1`, `motion.*`, MCP OAuth 2.1, drift mở issue) | 2026-09-25 | `draft-ke-hoach-mo-rong-robot-fofoca.md` |
| **Q-33** | RP2350 do đội lõi port làm node thứ hai | 2026-09-25 | Chặng W3 |
| **Q-34** | ROS 2 / Nav2 tích hợp, gate mọi lệnh tốc độ (cần RFC + C6 từ người mua robot) | 2026-09-25 | W4-1 |
| **Q-35** | Mất liên lạc: trạng thái an toàn theo từng cơ cấu, mặc định dừng | 2026-09-25 | RFC-node |
| **Q-6** | Lưu vết Fleet OS: Standard 90 ngày, Enterprise 3 năm | 2026-09-25 | Khối 2 |
| **Q-36** | Wire node: Zenoh-pico mặc định, spike W3-1 là phép thử loại (p99 ≤ 20 ms, SRAM ≤ 40 KB, nối lại ≤ 2 s) | 2026-09-25 | RFC-node, W3-1 |
| **Q-45** | PolyForm Noncommercial cho mã, Apache-2.0 cho chuẩn; kho công khai | 2026-09-25 | `LICENSING.md`, `TODOS.md` #43, #44 |
| **Q-46** | Câu có/không chỉ trả lời câu hỏi `ask` của chính lượt đó | 2026-09-26 | `docs/spec/voice_fsm.md` |
| **Q-47** | WebSocket trong Fleet OS chỉ cho kết nối và viễn trắc | 2026-09-28 | Khối 2 |
| **Q-48** | Máy trạng thái hội thoại thuộc L2 | 2026-09-28 | `docs/architecture/` |
| **Q-49** | Mỗi increment ra kèm một demo | 2026-09-29 | §11.1, `demo/` |
| **Q-50** | Phiên thoại thời gian thực trên laptop (`run --mic`) | 2026-09-29 | TSK-I4-04 |
| **Q-51** | NeuroEdge Studio | 2026-09-29 | TSK-I1-04 |
| **Q-52** | MVP = v1.0 đầy đủ, bốn phase, một lần ra mắt, trượt thì dời ngày; giả định đủ người | 2026-09-30 | §0.5, §1.1, TSK-I2a-01 |
| **Q-53** | Bốn gói nguyên thủy mở rộng bắt buộc trên ba target; bo ESP32-S3 có camera; `sim-rpi5` | 2026-09-30 | I2a, I3a, RFC-0007, RFC-0009 → RFC-0013 |
| **Q-54** | Thị giác → dữ kiện do maker khai; gate khoá ngưỡng tin cậy bằng tiêu chí số | 2026-09-30 | TSK-V1b-06, RFC-0012 |
| **Q-55** | NeuroBrain vào MVP, phủ bốn gói trên ba target (thay phần thứ tự NeuroBrain của Q-40) | 2026-09-30 | I4a, I5a |
| **Q-56** | Bỏ luật cổng nhu cầu: không còn Go / Adjust / Stop; phỏng vấn chỉ là đầu vào thông tin | 2026-09-30 | §0.2, `TODOS.md` #19 |
| **Q-57** | Quyết định cho câu hỏi mở của sáu RFC nguyên thủy mở rộng, theo hướng an toàn cao nhất | 2026-09-30 | RFC-0007, RFC-0009 → RFC-0013 §9 |
| **Q-58** | Bề mặt tích hợp vào MVP: MCP qua mạng có xác thực, Gated Tool Profile đóng băng | 2026-10-01 | TSK-P2-04, TSK-I6-05 (I6) |
| **Q-59** | Giữ PolyForm NC qua v1.0, mở sau; CLA cho tái cấp phép | 2026-10-01 | `TODOS.md` #43, #51 |
| **Q-60** | Một người + AI agent; người trong vòng cho task phần cứng, người ngoài, chữ ký (thay phần nhân sự của Q-52) | 2026-10-01 | §1.1, §1.3 |
| **Q-61** | Bo camera của `esp32s3`: M5Stack CoreS3 | 2026-10-01 | TSK-I3a-01, RFC-0013 §9.1, Phụ lục B |
| **Q-62** | Sửa sáu RFC theo review độc lập: lệnh an toàn không bị chặn, tự tắt, phong bì ghi bền, `NETR` v2 ghim byte | 2026-10-01 | RFC-0007, RFC-0009 → RFC-0013 §9 |
| **Q-63** | Khoảng hở nền tảng cho người tích hợp: bề mặt Python công khai, mở phạm vi RFC hợp đồng, RFC dữ kiện từ tiến trình ngoài | 2026-10-02 | TSK-I6-05, TSK-I6-06, TSK-I6-07, `TODOS.md` #52 → #56 |
| **Q-64** | Quy tắc ngừng hỗ trợ của API Python và CLI; `0.x` không phá vỡ ở bản PATCH; `SimSession` công khai; hợp đồng CLI | 2026-10-03 | TSK-I6-06, `docs/spec/python_api.md` §5 |
| **Q-37** | Token `motion.*` thuê có hạn, mỗi lệnh qua gate gia hạn | 2026-09-25 | RFC-motion |
| **Q-38** | Chứng nhận an toàn: OUT tạm thời, dừng khẩn phần cứng bắt buộc cho robot di động | 2026-09-25 | Câu C6 của bộ phỏng vấn (Q-56), `TODOS.md` #40 |
| **Q-39** | Roadmap theo increment; không phát hành ra ngoài tới khi công khai (I6: demo thoại trên `sim`, `linux`, Box-3); thêm một kỹ sư nhúng | 2026-09-25 | Toàn roadmap |
| **Q-40** | NeuroBrain và các hướng mở rộng xếp sau Beta, theo phụ thuộc — phần NeuroBrain thay bởi Q-55, thị giác bởi Q-53 | 2026-09-25 | I11, I13, I14, I16–I18 |
| **Q-41** | v1.1 mở khi Beta đạt B1 và B2; B3 đo nhưng không là điều kiện | 2026-09-25 | §7 |
| **Q-42** | C6 là chỉ số theo dõi, không là điều kiện phát hành v1.1 | 2026-09-25 | §8.3 |
| **Q-43** | Giả định G-a..G-e neo theo increment | 2026-09-25 | PRD §13.3 |
| **Q-44** | Bỏ bậc cắt 5: thoại trên MCU bắt buộc cho v1.0 | 2026-09-25 | §9 |

**Hệ quả trực tiếp lên I0:** Q-1, Q-2 và Q-3 chốt từ đầu nên đội đặt được bo mạch, dựng kho mã và bắt đầu spike mà không chờ quyết định nào.

**Một điều chỉnh so với đề xuất gốc:** Q-4 ghi Claude Sonnet 5 thay vì Sonnet 3.5. Thế hệ 3.5 đã bị thay thế; chốt một định danh mô hình lỗi thời vào tài liệu nền sẽ tạo nợ ngay từ ngày đầu.

### 10.2 Quyết định và RFC còn mở

| Hạn | Mã | Quyết định | Vì sao hạn đó | Người quyết | Trạng thái |
|:---:|:---:|:---|:---|:---:|:---:|
| **Trước khi I10 mở** | Q-5 | Xác thực và chống lạm dụng cho Registry công khai | Cần trước khi thiết kế hạ tầng Khối 3 | Kỹ thuật nền tảng | ⏳ Đang mở |
| **Trước khi I11 mở** | **RFC-0002** | Mở rộng enum `target` và đưa bậc target vào mã lõi (`TARGET_TIERS`); `vision.in` tách sang RFC riêng ở V1b | Không chặn roadmap này. Chặn I11 và mọi board profile mới | Kỹ thuật trưởng | ⏳ Đang mở |

**Chính sách phụ thuộc bắc cầu** là một phần của Q-11: nguyên văn ở PRD §15, cưỡng chế bằng `scripts/check_licences.py` (job `cloud-extra`) và `pip-licenses --fail-on` (job `licence-obligations`). *(Ngoại lệ LGPL qua liên kết động của `libgpiod` — proposal §3.9 quy tắc 3 — là thư viện hệ thống C, không phải phụ thuộc Python bắc cầu.)*

#### Phát hiện giấy phép trong I0 (đã xử lý, ghi lại để không tái diễn)

Khi dựng cổng giấy phép cho CI (TSK-S1-12), rà soát phụ thuộc phát hiện **hai đường lây nhiễm copyleft mạnh vào lõi** — cả hai đều là phụ thuộc bắc cầu, không ai chủ ý thêm:

| Đường lây nhiễm | Giấy phép | Cách xử lý |
|:---|:---|:---|
| `neuroedge` → `copier` → `jinja2-ansible-filters` | **GPL3** | `copier` rời tập phụ thuộc lõi; TSK-S3-07 hiện thực `neuroedge new` bằng generator Python thuần nên bỏ hẳn extra `scaffold` |
| `neuroedge` → `jsonschema[format]` → `rfc3987` | **GPL** | Ghim extra `[format-nongpl]`, dùng `rfc3987-syntax` (MIT). Extra này là **bắt buộc**, không phải tùy chọn: thiếu bộ kiểm tra format thì `format: date-time` trong `trace.v1.json` chỉ là chú thích, và một vết ghi có mốc thời gian không phân tích được vẫn thẩm định đạt |

Cả hai đều trực tiếp hiện thực hóa rủi ro mà §3.10 của tài liệu này nêu: *"Nhúng mã GPLv3 vào phần phân phối → Lây nhiễm bản quyền sang lõi — xung đột với giấy phép của lõi (Q-45) — và sang dự án của khách hàng."* Điều đáng chú ý là **không ai thêm một phụ thuộc GPL nào một cách chủ ý** — cả hai đến qua phụ thuộc bắc cầu của một thư viện hoàn toàn permissive. Rà soát giấy phép bằng mắt ở tầng phụ thuộc trực tiếp sẽ bỏ sót cả hai.

Vì vậy job `licence-obligations` trong [`ci-sim-linux.yml`](../.github/workflows/ci-sim-linux.yml) chạy `pip-licenses --fail-on` trên **toàn bộ cây phụ thuộc** ở mỗi pull request, và lưu bảng giấy phép đầy đủ làm artifact. Đây là nghĩa vụ 1 và 5 của §3.9 được tự động hóa, thay cho một lần rà soát thủ công.

**Hệ quả cho Q-11 (đã thực hiện 2026-09-23):** quyết định Q-11 bao gồm luôn chính sách phụ thuộc bắc cầu ở trên, không chỉ phê duyệt các thành phần đã nêu tên.

---
## 11. Nhịp vận hành

### 11.1 Nhịp định kỳ

| Tần suất | Hoạt động | Từ |
| :--- | :--- | :---: |
| Hằng ngày | Đồng bộ ngắn 15 phút | I0 |
| Hằng tuần | Demo chạy thật — **trên phần cứng thật từ khi bo mạch về** | I0 |
| Hằng tuần | Rà soát chỉ báo sớm §12 | I0 |
| Hằng đêm | Kiểm thử tự động trên bo mạch thật | I3 |
| Mỗi increment | Nghiệm thu theo tiêu chí ra, không theo cảm nhận; một thẻ phát hành, một tín hiệu đo (Q-39) | I0 |
| Mỗi increment | **Một demo chạy được, có giao diện** trong `demo/<increment>/` — lời dẫn, lệnh, đầu ra thật, commit đã chạy lại; năng lực nào chạy trên laptop thì demo qua `neuroedge studio` (Q-51); tiêu chí ra chỉ đánh `[x]` trong PR có demo; người review chạy lại kịch bản (Q-49). Danh mục: [`demo/README.md`](../demo/README.md) | I1 |

### 11.2 Định nghĩa hoàn thành

Một hạng mục chỉ được coi là hoàn thành khi đủ **cả năm** điều kiện:


| #   | Điều kiện                                                                      |
| :---: | :------------------------------------------------------------------------------ |
| 1   | Mã đã review và hợp nhất                                                       |
| 2   | Có kiểm thử tự động chạy trong CI, bao gồm ít nhất một ca thất bại             |
| 3   | Tiêu chí nghiệm thu của yêu cầu PRD tương ứng đã đạt và ghi nhận               |
| 4   | `--help` cập nhật; tài liệu, tiến độ, changelog cập nhật theo `CONTRIBUTING.md` §8 |
| 5   | Thông báo lỗi liên quan nêu đủ ba thành phần: sai ở đâu, vì sao, xử lý thế nào |
### 11.3 Quy tắc bảo vệ đường găng


| Quy tắc                              | Nội dung                                                                         |
| :------------------------------------ | :-------------------------------------------------------------------------------- |
| **Đóng băng lược đồ**                | Từ khi I0 đóng băng lược đồ, mọi thay đổi lược đồ cần RFC, phê duyệt và kịch bản di trú |
| **Không nợ kỹ thuật ở tầng an toàn** | Gate Engine và HAL không được hợp nhất kèm ghi chú "sẽ sửa sau". **Làm rõ (Q-17):** một hành vi **đã đặc tả, fail-closed và được test đầy đủ** — ví dụ `on_block` ở v1.0, nơi mọi hành vi đều chặn hành động vật lý còn bề mặt tương tác thật (người nhận escalate, UI hỏi lại) để sau — **không phải** nợ "sẽ sửa sau" và không cần waiver. Nợ là hành vi chưa đặc tả, fail-open, hoặc chưa có test |
| **Sai lệch tương đương là lỗi chặn** | `SafetyRegressionError` (NE4002) giữa các target trong nightly dừng mọi việc khác cho tới khi xử lý xong |
| **Đóng băng tính năng trong Beta**   | Dòng `1.0.x` trong I8: chỉ lỗi chặn hành trình 10 phút và lỗi an toàn (R12) |

---

## 12. Chỉ báo sớm và ngưỡng can thiệp


| #     | Chỉ báo                              | Ngưỡng vàng                              | Ngưỡng đỏ                           | Hành động khi đỏ                                                          |
| :-----: | :------------------------------------ | :---------------------------------------- | :----------------------------------- | :------------------------------------------------------------------------- |
| **1** | *(đã qua ở I0 — đóng băng lược đồ)* | — | — | — |
| **2** | Kết quả spike bộ nhớ                 | Còn dư dưới 30% ngân sách                | **Không đủ chỗ cho voice pipeline** | Mở ngay một `Q-N` lập lại kế hoạch I5 và dời dự báo v1.0 — không cắt thoại (Q-44) |
| **3** | Sai lệch `neuroedge verify`          | 1 ca lệch                                | Từ 3 ca lệch trở lên                | Dừng phát triển tính năng, truy nguyên gốc kiến trúc                      |
| **4** | Tiến độ thoại trên MCU (I5)          | 2 tuần sau khi I3 phát hành chưa có vòng lặp thoại hoàn chỉnh | 3 tuần sau vẫn chưa có | Mở `Q-N` lập lại kế hoạch I5 (Q-44) |
| **5** | Số người dùng Beta ngoài đội         | 2 tuần sau khi I8 mở dưới 25 người       | 2 tuần sau khi I8 mở dưới 10 người  | Dừng tuyển thêm, phỏng vấn sâu 10 người đã thử để tìm điểm nghẽn          |
| **6** | Tỷ lệ B2 — nạp phần cứng thật        | Dưới 20% của B1                          | Dưới 10% của B1                     | Điều tra đường lên phần cứng; đây là chỉ báo sớm của nhánh C              |
| **7** | Tỷ lệ áp dụng Action CI              | Dưới 40%                                 | Dưới 25%                            | Xem lại scaffold và tài liệu: Action CI chưa được đặt làm trung tâm       |


**Nguyên tắc đọc bảng:** ngưỡng vàng kích hoạt thảo luận trong buổi rà soát tuần. Ngưỡng đỏ kích hoạt hành động đã ghi sẵn, không thảo luận lại.

---
# Phụ lục

## Phụ lục A — Ánh xạ sprint, khối và chặng cũ sang increment

Không có ngày; ngày chỉ ở §0.2.

| Tên cũ | Increment |
|:---|:---|
| Sprint 1, 2, 3 — các task đã xong | I0 |
| Sprint 3: TSK-S3-08, S3-15 | I1 |
| Sprint 3: TSK-S3-14, S3-09 | I6 |
| Sprint 3: TSK-S3-10, S3-11, S3-13 · Sprint 2: TSK-S2-07 · Sprint 5: TSK-S5-08 | I4 |
| Sprint 3: TSK-S3-21 | I10 |
| Sprint 1: TSK-S1-10 · Sprint 2: TSK-S2-10 · Sprint 4 | I3 |
| Sprint 5: TSK-S5-01 → S5-07 | I5 |
| Sprint 5: TSK-S5-09, S5-10 | I2 |
| Sprint 6 | I7 |
| Developer Beta · Điểm rẽ | I8 |
| Khối 2 · Khối 3 | I9 · I10 |
| Giai đoạn 1.5 (NeuroBrain, N0–N7) | I4a (N0, N1, N3 → N6, N5b) · I5a (N7) · N2, TSK-N0-02, N0-03, N3-03 ở I2a · TSK-N7-02 ở I3a (Q-55) |
| Giai đoạn 2: V1a · V1b · V2 · V3 | I11 · I2a (Q-53) · I16 · I17 |
| Giai đoạn 2: P1 · P2-01, P2-02, P2-03, P2-06 · P2-04 · P2-05 | I13 · I18 · I6 (Q-58) · I14 |
| Robot W0-1 · W0-2, W0-3 · W0-4 | TSK-W0-01 (I7) · TSK-W0-02, W0-03 (I6) · TSK-W0-04 (I2) |
| Robot W1 (PWM, `numeric`, RFC-motion, `motion.*`) | I2a · I3a (TSK-W1-04) — Q-53 |
| Robot W2–W4 còn lại | I14 |
| TSK-S2-06 (CEL) | ngoài increment (§8.2, `TODOS.md` #42) |

**Mục robot đã gộp vào task có sẵn** (không cấp mã mới): W1A-3 → TSK-V1a-03 · W1B-RFC-1 → TSK-V1a-01…06, TSK-N0-03, TSK-W1-02 · W1B-RFC-3 → TSK-V1b-07 · W2-2 → TSK-S6-01…04 · W2-3 → TSK-S6-05 + TSK-W2-03 · W2-5 → TSK-K3-05 · W2-6 → TSK-P2-04 · W3-5 → TSK-P2-05 · W4-2 → TSK-P1-01…04 · W4-3 → TSK-K3-04 + TSK-S3-21 · W4-4 → TSK-P2-01. **Bỏ:** W0-5 (mục TODOS đã giao task), W4-5 (giữ ở `TODOS.md` #33), W4-6 (đã chốt ở Q-11).

## Phụ lục B — Danh mục mua sắm và hạ tầng

| Hạng mục | Số lượng | Cần trước | Ghi chú |
| :--- | :---: | :---: | :--- |
| **ESP32-S3-Box-3** (bo mạch tham chiếu chính thức) — **đợt 1** | **2** | **ĐẶT NGAY** | Chặn TSK-S1-10 (spike bộ nhớ, đo cả MultiNet theo Q-14) và I3. Ngày dự báo ở §0.2 giả định bo mạch về trước 2026-11-01 |
| **ESP32-S3-Box-3** — đợt 2 | 3–6 | I3 phát hành | Chốt tại Q-2. Đã tích hợp LCD, dual-mic và loa nên không cần mua rời. Tổng 5–8; dư ra cho nightly runner và bo mạch hỏng |
| **Raspberry Pi 5** — cho nightly `linux` (Q-16) | **1** | **ĐẶT NGAY** | TSK-I2-01. CI chạy `gpio-sim` trên runner GitHub từ 2026-09-23 |
| ESP32-S3-DevKitC (bo mạch thứ cấp) | 2 | I3 | Kiểm chứng tính di động của HAL ngoài Box-3; hỗ trợ ở mức cộng đồng |
| Raspberry Pi 5 | 2 | I2 | Target `linux` trên ARM64 *(ngoài chiếc cho nightly ở trên)* |
| Máy Linux x86-64 | 1 | I2 | Target `linux` trên x86, có thể dùng máy ảo |
| Mạch nạp và cáp JTAG | 2 bộ | I3 | Gỡ lỗi cấp thanh ghi |
| Runner CI tự quản có gắn bo mạch thật | 1 | I3 | Bắt buộc cho TSK-S4-05 |
| Tên miền và hạ tầng cho `schema.neuroedge.dev` | — | I6 | Phục vụ FR-GOV-01 và A9 (TSK-I6-02) |
| Kênh cộng đồng và repo công khai | — | I6 | TSK-I6-01, TSK-I6-04 |
| Camera USB và CSI | 4 | I2a | Nguồn khung hình cho `vision.in`; hai loại để kiểm chứng tính di động |
| NPU Hailo-8 hoặc Hailo-8L | 2 | I2a | Gắn ngoài cho Raspberry Pi 5 |
| Google Coral Edge TPU | 2 | I2a | Phương án NPU chi phí thấp hơn |
| Jetson Orin Nano | 2 | I16 | Target `jetson` bậc 2. **Chỉ mua sau khi tiêu chí thị giác của I2a đạt** |
| **M5Stack CoreS3** (bo tham chiếu `esp32s3` thứ hai, có camera — Q-53, Q-61) | 2 | **ĐẶT NGAY** | Chọn ở TSK-I3a-01; Box-3 không có camera. Cần về trước 2026-11-01 (G1 của TSK-I2a-01) |
| Servo, driver motor và nguồn riêng | 2 bộ | I2a | Kiểm `motion.*` trên Pi và Box-3, kể cả test mất điện giữa lệnh (TSK-W1-04) |
| Bo mạch STM32 và RP2350 | 2 mỗi loại | I13 · I14 | STM32 cho khung port mẫu của I13; RP2350 cho khung port mẫu và làm node robot do đội lõi port (Q-33) |

## Phụ lục C — Bố cục kho mã nguồn

Cây thư mục và thủ tục sửa từng thư mục: **[`CONTRIBUTING.md` §6](../CONTRIBUTING.md#6-cấu-trúc-kho)** — nơi duy nhất. Bốn quy ước dưới đây là ràng buộc kiến trúc cho cây đó.

**Bốn quy ước bắt buộc:**

| # | Quy ước | Lý do |
|:---:|:---|:---|
| 1 | `schemas/` là nguồn sự thật duy nhất; mã Python và firmware C đều sinh hoặc kiểm tra theo nó, không định nghĩa lại | Chống trôi lược đồ giữa hai ngôn ngữ |
| 2 | `fixtures/traces/` dùng chung cho mọi target, không có bản riêng theo ngôn ngữ | Là cơ sở của `neuroedge verify` |
| 3 | `targets/` chỉ chứa hiện thực HAL, không chứa logic nghiệp vụ hay chính sách an toàn | Giữ ranh giới tài sản lõi tại §3.1 |
| 4 | Lớp kết nối nhà cung cấp nằm trong `python/neuroedge/models/providers/`, **không** nằm trong `services/` | Nó thuộc lõi phân phối kèm sản phẩm, không phải dịch vụ do NeuroEdge vận hành (CR-1.0) |

---
## Phụ lục D — Giao thức truyền dẫn

Kênh truyền (Wi-Fi/LAN, UART) và định dạng âm thanh chuẩn cho `record`, `replay` và luồng thoại thời gian thực: **[PRD Phụ lục D.2](neuroedge-prd.md#d2-giao-thức-truyền-dẫn--định-dạng-vết-ghi-wire-protocol)** — nơi duy nhất.

---
*Hết tài liệu*
