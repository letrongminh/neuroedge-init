# NeuroEdge — Roadmap thực thi

## Kế hoạch triển khai từ Tuần 0 đến Tháng 8

**Phiên bản:** 1.2


**Ngày lập:** 21 tháng 9, 2026


**Tài liệu nguồn:** `neuroedge-proposal.md` v5.4 · `neuroedge-prd.md` v1.2


**Phạm vi:** Khối 1a · Khối 1b · Developer Beta · Khối 2 và 3


**Ngoài phạm vi:** Khối 4 (AURA thực địa) · Khối 5 (Marketplace) · **Giai đoạn 2** (thị giác, phủ rộng phần cứng) — xem [`neuroedge-roadmap-phase2.md`](neuroedge-roadmap-phase2.md)

---

## Mục lục

0. [Bảng theo dõi tiến độ & Nhật ký bàn giao](#0-bảng-theo-dõi-tiến-độ--nhật-ký-bàn-giao-live-execution--handoff-dashboard)
1. [Giả định nguồn lực](#1-giả-định-nguồn-lực)
2. [Đường găng và phụ thuộc](#2-đường-găng-và-phụ-thuộc)
3. [Chiến lược tái sử dụng mã nguồn mở](#3-chiến-lược-tái-sử-dụng-mã-nguồn-mở)
4. [Khối 1a — Lõi và Action CI (Tuần 0–6)](#4-khối-1a--lõi-và-action-ci-tuần-06)
5. [Khối 1b — Vi điều khiển biên (Tuần 6–12)](#5-khối-1b--vi-điều-khiển-biên-tuần-612)
6. [Developer Beta (Tuần 12–16)](#6-developer-beta-tuần-1216)
7. [Điểm rẽ quyết định Tuần 16](#7-điểm-rẽ-quyết-định-tuần-16)
8. [Khối 2 và 3 — Tầng dịch vụ (Tháng 4–8)](#8-khối-2-và-3--tầng-dịch-vụ-tháng-48)
9. [Thang cắt phạm vi](#9-thang-cắt-phạm-vi)
10. [Lịch chốt quyết định](#10-lịch-chốt-quyết-định)
11. [Nhịp vận hành](#11-nhịp-vận-hành)
12. [Chỉ báo sớm và ngưỡng can thiệp](#12-chỉ-báo-sớm-và-ngưỡng-can-thiệp)

**Phụ lục**

- [A — Bảng mốc tổng hợp](#phụ-lục-a--bảng-mốc-tổng-hợp)
- [B — Danh mục mua sắm và hạ tầng](#phụ-lục-b--danh-mục-mua-sắm-và-hạ-tầng)
- [C — Bố cục kho mã nguồn](#phụ-lục-c--bố-cục-kho-mã-nguồn)
- [D — Giao thức truyền dẫn](#phụ-lục-d--giao-thức-truyền-dẫn)

---

## Quy ước tài liệu

| Ký hiệu | Ý nghĩa | Nguồn định nghĩa |
|:---|:---|:---|
| **§x.y** | Mục trong `neuroedge-proposal.md` | proposal |
| **§x.y của tài liệu này** | Mục nội bộ của tài liệu này | — |
| **FR-… · NFR-…** | Yêu cầu chức năng và phi chức năng | `neuroedge-prd.md` §4–§9 |
| **A1–A9 · B1–B5 · C1–C7** | Tiêu chí **nghiệm thu phát hành** theo mốc v1.0 / Beta / v1.1 | `neuroedge-prd.md` §11 |
| **TR-1…TR-7** | Tiêu chí **ra cấp thực thi** của Khối 2 và 3 — bộ khác với C1–C7, xem §8.3 của tài liệu này | tài liệu này |
| **Q-1…Q-13** | Quyết định kỹ thuật. Sổ quyết định là `neuroedge-prd.md` §15; §10 của tài liệu này chỉ theo dõi trạng thái | `neuroedge-prd.md` §15 |
| **PF-1…PF-4** | Bộ lọc ưu tiên tính năng | proposal §2 |
| **TSK-…** | Mã hạng mục công việc, cấp phát trong tài liệu này | tài liệu này |
| **RB-1…RB-4** | Ràng buộc kỹ thuật chuyển giao giữa các sprint | `docs/spec/hal_mcu_review.md` |

## 0. Bảng theo dõi tiến độ & Nhật ký bàn giao (Live Execution & Handoff Dashboard)

> **Mục đích:** Cung cấp điểm nhìn tập trung duy nhất về trạng thái thời gian thực của toàn bộ dự án. Mọi phiên làm việc (session), kỹ sư hoặc AI Agent khi nhận bàn giao chỉ cần đọc mục này là nắm được ngay: *Hệ thống đang ở đâu, vừa hoàn thành gì, ai đang làm gì, và bước hành động kế tiếp là gì.*

### 0.1 Thanh trạng thái điều hành (Executive Status Bar)

| Chỉ số | Trạng thái hiện hành | Ghi chú & Liên kết |
|:---|:---|:---|
| **Pha đang thực thi** | 🟡 **Khối 1a: Lõi logic & Action CI (Tuần 0–6)** | Đạt ~55% khối lượng toàn khối |
| **Sprint hiện hành** | 🟡 **Sprint 1: Đóng băng Lược đồ & Monorepo (Tuần 0–2)** | **92% hoàn thành** (12 / 13 tasks hoàn tất; TSK-S1-10 chờ bo mạch) |
| **Cột mốc tiếp theo** | **M1: Time-to-first-value < 10 phút trên `sim`** | Hạn chót: Cuối Sprint 3 (Tuần 6) |
| **Lần cập nhật cuối** | **2026-09-21 23:30 UTC+7** | Áp dụng CR-1.0 cloud-first vào proposal v5.3 · PRD v1.1 · roadmap v1.1 |
| **Trạng thái CI Lõi** | ✅ **PASS 210/210 · SKIP 0** | `python/tests/` — 9 bộ test; cổng CI chặn mọi test bị skip |
| **Chặn ngoài tầm kỹ thuật** | 🔴 **2 hạng mục** | TSK-S1-10 chờ bo mạch vật lý · Tiêu chí ra 6 chờ quyết định **Q-11** |

---

### 0.2 Bảng tổng quan tiến độ các Sprint (Sprint Matrix Overview)

| Mốc | Sprint / Giai đoạn | Thời gian | Trọng tâm kỹ thuật | Tiến độ | Trạng thái |
|:---:|:---|:---:|:---|:---:|:---:|
| **Khối 1a** | **Sprint 1 — Đóng băng lược đồ** | Tuần 0–2 | Schemas, Monorepo, Test fixtures, Memory spike | **92%** | 🟡 **Chờ phần cứng** |
| | **Sprint 2 — Lõi thực thi trên `sim`** | Tuần 2–4 | HAL sim, Gate Engine CEL, Fail-closed, Lớp provider (LiteLLM), Web UI | **0%** | ⏳ Chưa bắt đầu |
| | **Sprint 3 — Action CI & Linux** | Tuần 4–6 | HAL linux, Replay/Assert, Barge-in, ASR/TTS qua provider, TTFV < 10' | **0%** | ⏳ Chưa bắt đầu |
| **Khối 1b** | **Sprint 4 — HAL trên `esp32s3`** | Tuần 6–8 | Port driver XiaoZhi, verify target bậc 1 không audio | **0%** | ⏳ Chưa bắt đầu |
| | **Sprint 5 — Runtime thoại MCU** | Tuần 8–10 | Thu/phát âm thanh, AEC/VAD, C/C++ state machine, stream lên provider | **0%** | ⏳ Chưa bắt đầu |
| | **Sprint 6 — OTA & Nghiệm thu v1.0** | Tuần 10–12 | A/B OTA, secure boot, tiêu chí A1–A9 | **0%** | ⏳ Chưa bắt đầu |
| **Beta** | **Developer Beta** | Tuần 12–16 | Hỗ trợ 50–100 lập trình viên, chỉ số B1–B5 | **0%** | ⏳ Chưa bắt đầu |
| **Khối 2** | **Fleet OS** *(dịch vụ thương mại duy nhất)* | Tháng 4–8 | Hawkbit Canary OTA, EMQX Broker, Provisioning | **0%** | ⏳ Chờ mốc Beta |
| **Khối 3** | **Bảy đường ray nền tảng** | Tháng 4–8 | OCI/ORAS Registry, OpenMeter usage billing | **0%** | ⏳ Chờ mốc Beta |

---

### 0.3 Thẻ Bàn giao Hiện tại (Active Session Handoff Card)

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ THẺ BÀN GIAO PHIÊN LÀM VIỆC (LIVING HANDOFF CARD)              Cập nhật: 2026-09-21    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. VỪA HOÀN THÀNH (DONE):                                                              │
│    • [RFC-0001] Đóng băng lược đồ gate: bắt buộc trường có điều kiện theo `extends`,   │
│      `budget.fail` thành tùy chọn (vắng = closed), tham số `on_block` theo hành vi      │
│    • [TSK-S1-03] Cưỡng chế ĐẦY ĐỦ 5 nguyên tắc kế thừa B.5 trong gate_resolver.py      │
│      — nguyên tắc 2 quyết định được nhờ chuẩn hóa allow_when thành tập giá trị          │
│    • [Tiêu chí 2] 3 gate mẫu viết tay + chuỗi kế thừa 2 cấp phân giải đúng              │
│    • [Tiêu chí 1] 15 fixture gate sai + 6 fixture trace sai, kèm thông báo lỗi kỳ vọng │
│    • [TSK-S1-11] Rà soát HAL dưới ràng buộc MCU: 5 kết luận + 4 ràng buộc cho Sprint 4 │
│    • [TSK-S1-12] 2 workflow CI: ci-sim-linux.yml (4 job) + nightly-hardware.yml (4 job)│
│    • [TSK-S1-13] CONTRIBUTING.md + quy trình RFC + mẫu RFC + RFC-0001                  │
│    • [TSK-S1-10] Khung đo bộ nhớ (memory_probe.c) + scripts/check_firmware_size.py     │
│    • Chuẩn tắc hóa RFC 8785 + băm SHA-256 cho gate; CLI: gate/trace/board đã thực thi  │
│    • Test: 208 PASS / 0 SKIP (trước đó 4 test conformance lược đồ bị skip trong im lặng)│
│                                                                                        │
│ 2. ĐANG THỰC HIỆN (IN-PROGRESS):                                                       │
│    • [TSK-S1-10] V2: CHỜ BO MẠCH. Khung đo xong, chưa có số đo thực. Vị trí chèn đã     │
│      đánh dấu TODO trong targets/esp32s3/main/main.c (nạp AEC + VAD + Opus)             │
│                                                                                        │
│ 3. VIỆC TIẾP THEO CẦN LÀM NGAY (NEXT IMMEDIATE ACTIONS):                               │
│    • 🔴 CHỐT Q-11 (ngoại lệ giấy phép Hawkbit/EMQX/LiteLLM) — chặn Tiêu chí ra 6        │
│    • 🔴 Đặt bo mạch ESP32-S3-BOX-3 — chặn TSK-S1-10 và Tiêu chí ra 3                   │
│    • Đồng bộ Phụ lục B.1/B.3/B.4 của proposal theo RFC-0001 §9                         │
│    • Mở Sprint 2: [TSK-S2-01] HAL cho `sim`, [TSK-S2-07] đặc tả chuẩn tắc FSM thoại    │
│    • [MỚI] [TSK-S2-11] Lớp trừu tượng provider (OpenAI-compatible + adapter) —         │
│      hạng mục phát sinh từ CR-1.0 cloud-first, nằm trong Khối 1a chứ không phải Khối 2  │
│                                                                                        │
│ 4. LƯU Ý KỸ THUẬT QUAN TRỌNG CHO NGƯỜI TIẾP QUẢN (CONTEXT & GUARDRAILS):               │
│    • [CR-1.0] Kiến trúc nay là CLOUD-FIRST: STT/TTS/LLM chạy trên provider cloud,      │
│      `esp32s3` chỉ thu/phát âm thanh + AEC/VAD + FSM + thẩm định gate. Sprint 5 giảm    │
│      phạm vi tương ứng; R-1 hạ từ Cao xuống Trung bình.                                 │
│    • [CR-1.0] KHÔNG có doanh thu inference. Gateway thương mại bị bỏ; lớp provider là   │
│      OSS self-host. Fleet OS là dịch vụ thương mại duy nhất.                            │
│    • [CR-1.0] Fail-closed KHÔNG đổi: gate và FSM chạy hoàn toàn trên thiết bị, mất      │
│      mạng vẫn chặn hành động vật lý (NFR-RES-04 giữ nguyên 100%).                       │
│    • [CR-1.0] LiteLLM chuyển từ dịch vụ máy chủ sang thư viện PHÂN PHỐI KÈM sản phẩm    │
│      (proposal Phụ lục H.1) → Q-11 phải xét lại nghĩa vụ giấy phép ở phạm vi mới.       │
│    • Không sửa đuôi trace thành .ntrace (chuẩn duy nhất là .json mang $schema).        │
│    • Bộ lượng giá CEL trên ESP32-S3 dùng Phương án A (Host biên dịch sang Decision     │
│      Tree JSON phẳng; ESP32-S3 chỉ duyệt cây bằng hàm C đơn giản, không nhúng CEL VM).  │
│    • Bo mạch tham chiếu duy nhất là ESP32-S3-Box-3 (không đổi sang DevKitC).           │
│    • THẨM ĐỊNH LƯỢC ĐỒ KHÔNG ĐỦ để kết luận gate an toàn. Nguyên tắc 2 là mệnh đề về   │
│      HAI tài liệu, nằm ngoài khả năng của JSON Schema → cổng kiểm tra là                │
│      `neuroedge gate lint` (phân giải), không phải thẩm định lược đồ.                  │
│    • `allow_when` dạng chuỗi CEL bị TỪ CHỐI trong chuỗi kế thừa: không chứng minh được  │
│      phép siết chặt cho biểu thức đục → fail-closed thay vì xấp xỉ.                     │
│    • `copier` ĐÃ CHUYỂN sang extra `scaffold`: nó kéo theo jinja2-ansible-filters GPL3, │
│      không được phép nằm trong phần phân phối của lõi MIT (§3.10 roadmap).              │
│    • jsonschema phải ghim extra `[format-nongpl]` (extra `[format]` kéo rfc3987 GPL).   │
│    • Lệnh CLI chưa có engine PHẢI thoát mã 2, không in bảng "PASS" giả.                │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 0.4 Quy ước Cập nhật & Bàn giao (Handoff Protocol)

Để bảo đảm mọi thành viên trong đội ngũ và các phiên làm việc của AI kế tiếp nhau không bị đứt đoạn:
1. **Quy tắc cập nhật Task:** Khi bắt đầu làm một task, chuyển trạng thái từ `⏳ Chưa bắt đầu` sang `🟡 Đang thực hiện`. Khi hoàn thành mã nguồn và test pass, chuyển sang `✅ Hoàn thành` kèm đường dẫn tệp sản phẩm (artifact) và mã commit.
2. **Quy tắc cập nhật Exit Criteria:** Khi một tiêu chí nghiệm thu thỏa mãn, đánh dấu `[x]` kèm bằng chứng kiểm chứng (test log, command output, link code).
3. **Cập nhật Thẻ Bàn giao:** Trước khi kết thúc phiên làm việc, cập nhật lại phần *Vừa hoàn thành*, *Đang thực hiện*, và *Việc tiếp theo* tại Mục 0.3.

---

## 1. Giả định nguồn lực

> **Đây là giả định, không phải dữ kiện.** Toàn bộ lịch trình bên dưới phụ thuộc vào nó. Nếu cấu hình đội khác đi, xem §1.3 trước khi đọc tiếp.

### 1.1 Bốn vai trò bắt buộc


| Vai trò                                   | Trách nhiệm chính                                                       | Có mặt từ                           |
| :----------------------------------------- | :----------------------------------------------------------------------- | :-----------------------------------: |
| **V1 — Kỹ sư lõi nền tảng**               | HAL, Action Contract Engine, lược đồ gate và trace, Action CI           | Tuần 0                              |
| **V2 — Kỹ sư nhúng**                      | Port `esp32s3`, runtime thoại trên MCU, OTA cấp thiết bị, tối ưu bộ nhớ | Tuần 0 *(bán thời gian tới Tuần 6)* |
| **V3 — Kỹ sư trải nghiệm lập trình viên** | Giao diện `sim`, CLI, scaffold, tài liệu, ví dụ mẫu                     | Tuần 2                              |
| **V4 — Kỹ sư hạ tầng dịch vụ**            | Fleet OS, Registry, hệ đo lường, hoàn thiện lớp provider OSS            | Tháng 3                             |


**Cấu hình tối thiểu khả thi: 3 người cho Khối 1**, trong đó một người kiêm vai trò kỹ thuật trưởng và vẫn viết mã. Vai trò V4 tuyển trước Khối 2 một tháng để có thời gian làm quen kiến trúc.

### 1.2 Vì sao V2 phải có mặt từ Tuần 0

Rủi ro **R-1** của PRD (phạm vi Khối 1b vượt hạn do tối ưu bộ nhớ MCU) được đánh giá mức **Cao**. Cách giảm thiểu hiệu quả không phải là giám sát ở Tuần 9, mà là **chạy spike khả thi bộ nhớ ngay Tuần 2**, khi vẫn còn đủ thời gian để đổi phạm vi.

V2 làm bán thời gian trong Khối 1a: một phần cho spike, phần còn lại rà soát thiết kế HAL dưới góc nhìn ràng buộc MCU. Một HAL thiết kế mà không có tiếng nói của kỹ sư nhúng sẽ phải viết lại ở Tuần 6.

### 1.3 Độ nhạy theo quy mô đội


| Cấu hình                       | Tác động lên lịch trình                                                                                                             |
| :------------------------------ | :----------------------------------------------------------------------------------------------------------------------------------- |
| **2 người**                    | Khối 1a giãn sang 8–9 tuần; Khối 1b sang 14–16 tuần. Bắt buộc áp dụng bậc 5 của thang cắt phạm vi (§9) ngay từ đầu                  |
| **3 người** *(giả định cơ sở)* | Lịch trình như tài liệu này                                                                                                         |
| **4–5 người**                  | Khối 1a rút còn 5 tuần; Khối 1b song song hóa nhiều hơn. Không rút được dưới 4 tuần vì đường găng là chuỗi thiết kế lược đồ tuần tự |


Thêm người **không** rút ngắn được Sprint 1: đóng băng lược đồ là công việc thiết kế tuần tự, không chia nhỏ song song được.

---

## 2. Đường găng và phụ thuộc

### 2.1 Đồ thị phụ thuộc

```text
Tuần 0 ──► LƯỢC ĐỒ GATE v1 ──┐
           LƯỢC ĐỒ TRACE v1 ─┼──► ĐÓNG BĂNG (Tuần 2)
           HỢP ĐỒNG HAL     ─┘        │
                                      ├──► Gate Engine ──► Action CI ──┐
                                      │    (fail-closed)   (record/     │
                                      │                     replay)     │
                                      ├──► Target sim ─────────────────┤──► TTFV < 10'
                                      │         │                       │    (Tuần 6)
                                      │         └──► Target linux ──────┤
                                      │                                 │
                                      └──► Port esp32s3 ────────────────┴──► verify bậc 1  
                                           (Tuần 6–8)                        (Tuần 8)
                                                │
                                                └──► Runtime thoại MCU ──► OTA ──► v1.0
                                                     (Tuần 8–10)         (Tuần 10–12)

    ⟂ Song song từ Tuần 2:  SPIKE BỘ NHỚ ESP32-S3  ──► quyết định phạm vi 1b (Tuần 4)
```

### 2.2 Đường găng


| #   | Mắt xích                        | Tuần | Vì sao nằm trên đường găng                                                                                    |
| :---: | :------------------------------- | :----: | :------------------------------------------------------------------------------------------------------------- |
| 1   | Đóng băng lược đồ gate và trace | 0–2  | FR-TRC-05 yêu cầu định dạng ổn định giữa các phiên bản. Mọi vết ghi đã tạo sẽ hỏng nếu đổi lược đồ sau Tuần 6 |
| 2   | Gate Engine với fail-closed     | 2–4  | Mọi thành phần khác gọi vào nó                                                                                |
| 3   | Record và replay                | 4–5  | Là điều kiện để có assert và golden                                                                           |
| 4   | Port HAL lên `esp32s3`          | 6–8  | Không có target thứ ba thì không chứng minh được tương đương                                                  |
| 5   | Runtime thoại trên MCU          | 8–10 | Vẫn là mắt xích khó nhất nhưng **rủi ro đã giảm** từ CR-1.0: STT/TTS chuyển lên provider cloud, MCU chỉ thu/phát + FSM + gate; xem §9 |


**Đòn bẩy mã nguồn mở trên đường găng:** mắt xích 2 rút ngắn nhờ Google CEL, mắt xích 4 nhờ driver XiaoZhi, mắt xích 5 nhờ Pipecat và bộ mô hình âm thanh. Chi tiết và mức rút ngắn thực tế tại §3.7.

**Phụ thuộc mới từ CR-1.0:** lớp trừu tượng provider (TSK-S2-11) là điều kiện tiên quyết cho ASR/TTS qua cloud ở Sprint 3 (TSK-S3-13) và cho vòng lặp thoại ở Sprint 5 (TSK-S5-06). Nó **không** nằm trên đường găng của mắt xích 2 và 3 nên làm song song được, nhưng phải xong trước Tuần 6.

**Không nằm trên đường găng, làm song song:** giao diện `sim`, CLI, tài liệu, ví dụ mẫu, hạ tầng CI.

### 2.3 Quy tắc đóng băng lược đồ

Từ **cuối Tuần 2**, mọi thay đổi đối với lược đồ gate hoặc lược đồ vết ghi bắt buộc:

1. Có đề xuất RFC viết ra, nêu rõ lý do và ảnh hưởng tương thích ngược
2. Được kỹ thuật trưởng phê duyệt
3. Kèm kịch bản di trú cho toàn bộ vết ghi đã tồn tại

Đây là quy tắc nghiêm ngặt nhất của toàn bộ dự án. Lược đồ trôi nổi làm sụp đổ mệnh đề trung tâm.

**RFC đang mở:** [RFC-0002](docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md) đề xuất mở rộng enum `target` ở `board.v1` và `trace.v1`, và đưa bậc target vào mã lõi (`TARGET_TIERS`) — phục vụ Giai đoạn 2. Nguyên thủy `vision.in` đã tách khỏi RFC này, sang một RFC riêng ở Khối V1b (RFC-0002 §9.1). RFC ở trạng thái *đang thảo luận*; **lược đồ chưa đổi và không được đổi cho tới khi RFC được phê duyệt**. Roadmap này không phụ thuộc vào kết quả RFC đó.

---
## 3. Chiến lược tái sử dụng mã nguồn mở

**Nguyên tắc bao trùm: xây thứ tạo khác biệt, mượn thứ đã là hàng hóa.**

Mục tiêu là rút ngắn tối đa thời gian ra thị trường bằng cách tái sử dụng và port các dự án mã nguồn mở hàng đầu vào mọi khâu — đồng thời bảo vệ tuyệt đối phần tài sản trí tuệ lõi.

### 3.1 Ranh giới bất di bất dịch

| Nhóm | Thành phần | Chính sách |
|:---|:---|:---|
| **Tài sản lõi — tự xây 100%** | Hợp đồng hành động · Lược đồ gate có phiên bản · Mạch ngắt fail-closed · Trục Action CI · Lược đồ vết ghi JSON mở · Đối chiếu năng lực lúc biên dịch | **Không nhận bất kỳ phụ thuộc kiến trúc nào** |
| **Hàng hóa — mượn tối đa** | Driver bo mạch · Codec âm thanh · VAD/AEC · Wake-word · Parser CLI · Web component mô phỏng · Rule engine biểu thức · Proxy định tuyến LLM · Metering · Hạ tầng OTA | **Tái sử dụng hoặc port, không tự viết** |

Ranh giới này quyết định mọi mục còn lại. Một thành phần nằm ở nhóm trên thì dù có thư viện sẵn cũng không dùng; nằm ở nhóm dưới thì dù viết được cũng không viết.

### 3.2 Phép thử quyết định

> **Phụ thuộc vào nó có buộc ta vi phạm P-1, P-2, hoặc ba quyết định kiến trúc tuần 1 không?**

| Ràng buộc | Nội dung *(diễn giải rút gọn — nguyên văn tại `neuroedge-prd.md` §1.5)* |
|:---|:---|
| **P-1** | Mọi lệnh tới cơ cấu chấp hành đi qua gate |
| **P-2** | Các môi trường thực thi ngang hàng |
| **Tuần 1** | `sim` là target thật · gate là artifact có phiên bản · trace là công dân hạng nhất |

**Có** → chỉ liên thông hoặc tham khảo thiết kế. **Không** → tái sử dụng tối đa.

### 3.3 Kỷ luật giấy phép

| # | Quy tắc | Nội dung |
|:---:|:---|:---|
| 1 | **Danh sách cho phép** | MIT · Apache-2.0 · BSD-2-Clause · BSD-3-Clause · ISC |
| 2 | **Vùng cách ly GPL** | Tuyệt đối không nhúng hoặc sao chép mã GPLv3 vào phần phân phối của NeuroEdge, để tránh lây nhiễm sang lõi MIT và sang dự án của khách hàng |
| 3 | **LGPL chỉ qua liên kết động** | `libgpiod` (LGPL-2.1) gọi qua dynamic link ở không gian người dùng, không tĩnh hóa, không sao chép mã |
| 4 | **Giấy phép ngoài danh sách cần phê duyệt** | EPL-2.0, MPL-2.0, BSL và tương tự chỉ dùng cho **dịch vụ phía máy chủ không phân phối**, và phải có quyết định ghi thành văn bản |
| 5 | **Xác minh tại nguồn** | Đọc tệp giấy phép trong kho gốc, ghi lại phiên bản và ngày kiểm tra. Không suy đoán theo thông lệ |

**Hai ngoại lệ đã biết cần quyết định trước khi dùng — xem Q-11 tại §10:**

| Dự án | Giấy phép dự kiến | Vấn đề |
|:---|:---|:---|
| Eclipse Hawkbit | EPL-2.0 | Nằm ngoài danh sách cho phép. Chấp nhận được cho dịch vụ máy chủ không phân phối, nhưng phải ghi rõ ranh giới triển khai |
| EMQX | Apache-2.0 với phần thương mại theo BSL | Phải xác định chính xác tính năng nào thuộc phần Apache trước khi thiết kế phụ thuộc |
| LiteLLM | MIT với phần enterprise riêng | Chỉ dùng phần MIT; middleware xác thực thiết bị viết riêng |

### 3.4 Ma trận tích hợp theo khối

| Khối | Hạng mục kỹ thuật | Dự án tái sử dụng | Hình thức | Tiết kiệm |
|:---|:---|:---|:---|:---:|
| **1a** | CLI `new` / `run` / `test` | Typer · Rich · Copier | Thư viện Python | 2 tuần |
| **1a** | Lượng giá biểu thức `allow_when` | Google CEL (`cel-python`) | Rule engine lõi | 3 tuần |
| **1a** | Giao diện web môi trường `sim` | Wokwi Elements | Web components | 3 tuần |
| **1a** | Khung kiểm thử Action CI | Pytest · DeepDiff | Plugin `pytest-neuroedge` | 2 tuần |
| **1a** | Chuẩn hóa lược đồ gate và trace | Pydantic v2 · `rfc8785` canonical JSON | Thư viện chuẩn hóa | 1 tuần |
| **1b** | Bo mạch tham chiếu ESP32-S3 | XiaoZhi ESP32 | **Port trực tiếp driver** | 5 tuần |
| **1b** | Barge-in, VAD, xử lý khung âm thanh | Pipecat · microWakeWord · libfvad | **Port mô hình pipeline** | 4 tuần |
| **1b** | OTA cấp thiết bị | ESP-IDF `esp_https_ota`, `esp_ota_ops` | Tận dụng SDK chuẩn | 2 tuần |
| **1b** | Hiển thị trạng thái trên màn hình | LVGL v8/v9 | Thư viện đồ họa nhúng | 2 tuần |
| **1a** | Lớp trừu tượng nhà cung cấp (OpenAI-compatible + adapter) | LiteLLM | **Thư viện trong lõi MIT** | 6 tuần |
| **2** | Điều phối OTA canary | Eclipse Hawkbit | Backend điều phối | 5 tuần |
| **2** | Kết nối thiết bị và viễn trắc | EMQX · FastAPI WebSockets | Hạ tầng kết nối | 3 tuần |
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
| 3 | **Wokwi Elements** | `neuroedge/sim/web/` | `<wokwi-led>` · `<wokwi-pushbutton>` · `<wokwi-solenoid-lock>` · `<wokwi-servo>` · `<wokwi-lcd1602>` |
| 4 | **LiteLLM** | `neuroedge/models/providers/` | Chuyển đổi I/O về một chuẩn chung · cân bằng tải · failover · hạn mức theo khóa định danh. **Từ CR-1.0: thư viện trong lõi MIT phân phối kèm sản phẩm**, không phải lõi của một dịch vụ do NeuroEdge vận hành — xem Q-11 |
| 5 | **OpenMeter** | Lõi metering Khối 3 | Engine gom cụm sự kiện · đối soát số lượt gọi agent và lượt thẩm định gate |

**Giá trị lớn nhất nằm ở mục 1 và 2** vì chúng nằm trên đường găng: loại bỏ rủi ro kẹt thanh ghi, lỗi clock I2S, méo tiếng, và toàn bộ vòng thử sai của các ca biên hội thoại.

### 3.6 Ba dự án chỉ liên thông, không phụ thuộc

| Dự án | Quyết định | Lý do |
|:---|:---|:---|
| **ESP-Claw** | Liên thông qua MCP | Một SDK chính hãng về cấu trúc không thể coi chip đối thủ là ngang hàng. Phụ thuộc vào nó biến `linux` thành công dân hạng hai và làm sụp luận điểm đánh sườn (proposal §1.4) |
| **LiveKit Agents** | Tham khảo thiết kế | Lấy cloud làm trung tâm; mô hình hạ tầng mâu thuẫn với yêu cầu chạy đầy đủ khi offline |
| **TEN Framework** | Tham khảo thiết kế | Như trên |

Riêng **XiaoZhi tuyệt đối không fork toàn bộ**: đó là một ứng dụng firmware, logic hội thoại gắn thẳng vào lệnh phần cứng, không có HAL và không có khái niệm hợp đồng hành động. Chỉ port tầng driver theo §3.5, phần còn lại không đụng tới.

**Điểm chiến lược:** cộng đồng XiaoZhi là kênh phân phối. Tương thích với bo mạch XiaoZhi phổ biến có giá trị cao hơn nhiều so với dùng lại mã — người dùng đã có sẵn phần cứng, cắm vào chạy được ngay là đòn bẩy trực tiếp cho chỉ tiêu B2.

### 3.7 Tác động thật lên đường găng

Tổng tiết kiệm công sức viết mã khoảng 50 tuần-người. **Nhưng phần lớn không nằm trên đường găng.**

| Mắt xích đường găng | Có đòn bẩy OSS không | Mức rút ngắn thực tế |
|:---|:---|:---|
| Đóng băng lược đồ gate và trace | Một phần — Pydantic và canonical JSON | Không đáng kể, vì đây là công việc thiết kế |
| Gate Engine với fail-closed | **Có — CEL thay cho tự viết bộ lượng giá** | Khoảng 1–2 tuần |
| Record và replay | Một phần — DeepDiff cho so khớp golden | Dưới 1 tuần |
| **Port HAL lên `esp32s3`** | **Có — driver XiaoZhi** | **2–3 tuần** |
| **Runtime thoại trên MCU** | **Có — Pipecat, microWakeWord, libfvad** | **2–3 tuần** |

**Kết luận thực tế:** đòn bẩy OSS rút ngắn Khối 1b nhiều hơn Khối 1a, và quan trọng hơn cả là nó **hạ rủi ro R-1 từ mức Cao xuống Trung bình**. Tuy vậy chi phí tích hợp, rà soát giấy phép và ghim phiên bản là chi phí mới phát sinh. Lịch trình trong tài liệu này **giữ nguyên**; phần tiết kiệm được chuyển thành vùng đệm cho Sprint 5, nơi rủi ro tập trung.

### 3.8 Bảo toàn tương đương target khi có hai ngôn ngữ

Đây là hệ quả nghiêm trọng nhất của việc port, và cần xử lý tường minh.

Quyết định **Q-8 đã chốt**: C/C++ trên ESP-IDF cho firmware, Python cho `sim` và `linux`. Hệ quả: máy trạng thái hội thoại **buộc phải có hai hiện thực**. Không thể chia sẻ mã giữa hai bên.

Điều này va thẳng vào P-2. FR-PER-02 yêu cầu barge-in thu hồi lệnh actuator chưa thực thi — nghĩa là hành vi cắt lời rò trực tiếp vào miền hành động vật lý. Hai hiện thực barge-in khác nhau cho ra hai hành vi thu hồi khác nhau.

**Giải pháp bắt buộc: một đặc tả chuẩn tắc, hai hiện thực tuân thủ, một bộ kiểm thử tuân thủ dùng chung.**

| # | Thành phần | Nội dung | Sprint |
|:---:|:---|:---|:---:|
| 1 | **Đặc tả máy trạng thái** | Năm trạng thái và hợp đồng thu hồi lệnh, đặc tả bên dưới. Là nguồn sự thật duy nhất, không phải mã Python | Sprint 2 |
| 2 | **Bộ vector kiểm thử tuân thủ** | Ba tệp vết ghi chuẩn tại `fixtures/traces/`, kèm chuỗi phán quyết và trạng thái GPIO kỳ vọng, độc lập với ngôn ngữ | Sprint 3 |
| 3 | **Hiện thực Python** | Cho `sim` và `linux`, port thiết kế từ Pipecat | Sprint 3 |
| 4 | **Hiện thực C/C++** | Cho `esp32s3`, port driver từ XiaoZhi | Sprint 5 |
| 5 | **`neuroedge verify` chạy bộ vector trên mọi target bậc 1** | Lệch nhau sinh `TargetEquivalenceError` | Sprint 4–5 |

**Không có bước 1 và 2 thì việc port Pipecat là một rủi ro, không phải một đòn bẩy.** Đặc tả và bộ vector phải có trước khi viết hiện thực thứ hai.

#### Đặc tả chuẩn tắc: năm trạng thái

```text
                    ┌──────────┐
         ┌─────────►│   IDLE   │◄─────────┐
         │          └────┬─────┘          │
         │               │ wake-word hoặc │ phát xong
         │               │ VAD kích hoạt  │
         │               ▼                │
         │          ┌───────────┐         │
         │          │ LISTENING │         │
         │          └────┬──────┘         │
         │               │ kết thúc câu   │
         │               │ (khoảng lặng)  │
         │               ▼                │
         │          ┌──────────┐          │
         │          │ THINKING │          │
         │          └────┬─────┘          │
         │               │ token đầu tiên │
         │               ▼                │
         │          ┌──────────┐          │
         │          │ SPEAKING ├──────────┘
         │          └────┬─────┘
         │               │ phát hiện người dùng nói
         │               ▼
         │       ┌────────────────┐
         │       │    BARGE_IN    │
         │       │ 1. xả đệm DAC  │
         │       │ 2. huỷ actuator│
         │       │    đang chờ    │
         │       │ 3. ghi sự kiện │
         │       └───────┬────────┘
         │               │ thu câu nói mới
         └───────────────┘  →  LISTENING
```

**Hợp đồng thu hồi lệnh vật lý (Actuator Abort Contract).** Mọi lệnh actuator có độ trễ thực thi — ví dụ `pulse` chốt cửa sau 1.000 ms — nếu gặp sự kiện `barge_in` trong lúc đang chờ cấp xung thì **HAL bắt buộc huỷ lệnh ngay lập tức** và ghi mã trạng thái `ACTUATOR_ABORTED_BY_BARGE_IN` vào tệp vết ghi.

Đây là mệnh đề mà cả hai hiện thực phải thoả, và là mệnh đề mà bộ vector tuân thủ kiểm tra trực tiếp.

#### Hệ quả tương tự với CEL

Nếu `allow_when` dùng Google CEL, thì gate phải lượng giá được **trên cả vi điều khiển**, vì gate chạy on-device và fail-closed khi mất mạng. `cel-python` không chạy trên ESP32-S3.

**Q-9 đã chốt: phương án A.**

| Phương án | Nội dung | Đánh giá |
|:---|:---|:---|
| **A. Biên dịch gate lúc build** | `neuroedge build` trên máy tính dịch biểu thức CEL thành cây quyết định tất định dạng JSON phẳng; firmware chỉ cần một hàm C khoảng 100 dòng để duyệt cây | **ĐÃ CHỐT** — một nguồn sự thật, hai bên lượng giá cùng một artifact, không tốn RAM vi điều khiển, củng cố luôn câu chuyện golden |
| B. Bộ lượng giá CEL rút gọn bằng C | Tự viết evaluator cho tập con CEL | Bác bỏ — thêm một hiện thực cần giữ đồng bộ |
| C. CEL trên host, biểu thức đơn giản trên thiết bị | Hai cú pháp khác nhau | Bác bỏ — phá tương đương target ở đúng tầng an toàn |

**Ranh giới tài sản lõi trong phương án A:** `cel-python` chỉ làm nhiệm vụ **phân tích cú pháp** trên máy tính. **Trình biên dịch sang cây quyết định và bộ duyệt cây trên thiết bị là mã của NeuroEdge** — đây là ngữ nghĩa an toàn, thuộc nhóm không nhận phụ thuộc tại §3.1.

#### Ba tệp vết ghi chuẩn mực

Bộ vector tuân thủ khởi đầu bằng đúng ba kịch bản, cố định tại `fixtures/traces/`:

| Tệp | Kịch bản | Kết quả kỳ vọng |
|:---|:---|:---|
| `happy-path.json` | Khách đã xác thực yêu cầu mở cửa | Gate `ALLOW` · chân `door_lock` nhận xung 30.000 ms |
| `unverified_attempt.json` | Người chưa xác thực yêu cầu mở cửa | Gate `BLOCK` · `escalate` tới lễ tân · chân `door_lock` **không bao giờ** nhận xung |
| `network_offline.json` | Mất kết nối khi đang thẩm định gate | Fail-closed kích hoạt · hành động bị từ chối · lý do `gate_unreachable` |

Ba tệp này là thước đo tuân thủ cho cả Khối 1a và 1b, và là đầu vào trực tiếp của `neuroedge verify`.

### 3.9 Nghĩa vụ ghi nhận nguồn

**Hạn chót: hoàn tất trước khi port bất kỳ dòng mã nào — chậm nhất cuối Tuần 2.**

| # | Nghĩa vụ | Nội dung |
|:---:|:---|:---|
| 1 | Ma trận giấy phép | Bảng đầy đủ: dự án, phiên bản, giấy phép, ngày xác minh, phạm vi sử dụng, trạng thái phê duyệt |
| 2 | Tệp `NOTICE` ở gốc kho | Liệt kê từng thành phần, tác giả và giấy phép |
| 3 | Ghi nhận tại chỗ trong mã | Chú thích nêu rõ tệp gốc và commit tham chiếu, đặt ngay đầu tệp đã port |
| 4 | Mục ghi nhận trong tài liệu công khai | Không giấu trong mã nguồn |
| 5 | Ghim phiên bản cho mọi phụ thuộc | Nightly phát hiện sớm thay đổi phá vỡ tương thích ở thượng nguồn |

Đây là nghĩa vụ pháp lý. Một vi phạm phát hiện sau khi phát hành công khai tốn kém hơn nhiều so với vài ngày rà soát trước.

### 3.10 Rủi ro khi làm ngược

| Nếu | Hậu quả |
|:---|:---|
| Fork toàn bộ XiaoZhi làm nền | Kế thừa kiến trúc không có HAL; phải gỡ để chèn gate; gánh nhánh fork vĩnh viễn |
| Xây trên ESP-Claw | `linux` thành hạng hai → mất bằng chứng hợp đồng năng lực → mất luận điểm đánh sườn |
| Port Pipecat mà không có đặc tả và bộ vector tuân thủ | Hai hiện thực barge-in phân kỳ → tương đương target vỡ ở miền thu hồi lệnh actuator |
| Dùng CEL trên host nhưng cú pháp khác trên thiết bị | Gate cho phán quyết khác nhau giữa hai target ở đúng tầng an toàn |
| Nhúng mã GPLv3 vào phần phân phối | Lây nhiễm bản quyền sang lõi MIT và sang dự án của khách hàng |
| Port mã trước khi rà soát giấy phép | Rủi ro pháp lý phát hiện sau khi công khai, chi phí khắc phục rất cao |
| Tự viết AEC, VAD, codec, rule engine | Đốt Sprint 2 và 5 vào bài toán đã có lời giải tốt, trễ mốc mà không tạo khác biệt |

---

## 4. Khối 1a — Lõi và Action CI (Tuần 0–6)

**Mục tiêu khối:** một lập trình viên lạ chạy được agent có gate trong dưới 10 phút, không cần mua phần cứng.

### 4.1 Sprint 1 — Đóng băng lược đồ (Tuần 0–2)


| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S1-01** | Đặc tả 5 nguyên thủy HAL và thuộc tính đối chiếu | FR-HAL-01, FR-HAL-02, FR-HAL-03 | V1 | ✅ Hoàn thành | [`schemas/board.v1.json`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/schemas/board.v1.json) |
| **TSK-S1-02** | Lược đồ gate v1: 8 trường, 3 kiểu `evaluate`, 4 hành vi `on_block`, `budget` | FR-GATE-02, FR-GATE-03, FR-GATE-04 | V1 | ✅ Hoàn thành | [`schemas/gate.v1.json`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/schemas/gate.v1.json) · sửa theo [RFC-0001](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/rfc/0001-gate-schema-conditional-requirements.md) (bắt buộc có điều kiện) |
| **TSK-S1-03** | Quy tắc kế thừa `extends`: 5 nguyên tắc an toàn | FR-GATE-06, FR-GATE-07, FR-GATE-08 | V1 | ✅ Hoàn thành | **Đã cưỡng chế bằng mã:** [`gate_resolver.py`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/python/neuroedge/engine/gate_resolver.py), [`constraints.py`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/python/neuroedge/engine/constraints.py) · 35 test tại [`test_gate_resolver.py`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/python/tests/test_gate_resolver.py) |
| **TSK-S1-04** | Lược đồ vết ghi v1: 6 nhóm sự kiện, khối `metadata` | FR-TRC-01, FR-TRC-02, FR-TRC-03 | V1 | ✅ Hoàn thành | [`schemas/trace.v1.json`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/schemas/trace.v1.json) |
| **TSK-S1-05** | Ma trận giấy phép và tệp `NOTICE` cho toàn bộ dự án sẽ port (§3.9) | — | V2 | ✅ Hoàn thành | [`NOTICE`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/NOTICE) 4 mục A–D · cổng CI chặn copyleft mạnh · [`requirements-lock.txt`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/python/requirements-lock.txt) (nghĩa vụ 5) |
| **TSK-S1-06** | **Dựng bộ khung monorepo** theo Phụ lục D: `schemas/` · `python/` · `targets/` · `fixtures/` | — | V1 | ✅ Hoàn thành | [`schemas/`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/schemas/), [`python/`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/python/), [`targets/`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/targets/), [`fixtures/`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/fixtures/) |
| **TSK-S1-07** | **Ba tệp lược đồ chính thức** trong `schemas/`: `trace.v1.json` · `gate.v1.json` · `board.v1.json` | FR-TRC-01, FR-GATE-02, FR-HAL-02 | V1 | ✅ Hoàn thành | JSON Schema draft 2020-12 · CI thẩm định `$id` và `check_schema` · 18 test tại [`test_schemas.py`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/python/tests/test_schemas.py) |
| **TSK-S1-08** | **Ba tệp vết ghi chuẩn mực** tại `fixtures/traces/` (`happy-path`, `unverified_attempt`, `network_offline`) | FR-CI-01, FR-CI-02 | V1 | ✅ Hoàn thành | [`fixtures/traces/`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/fixtures/traces/) + [6 fixture phản chứng](file:///Users/minhlt/Downloads/Projects/neuroedge-init/fixtures/traces/invalid/) kèm [`expected_errors.yaml`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/fixtures/traces/expected_errors.yaml) · thẩm định cả `format: date-time` |
| **TSK-S1-09** | Khung Python SDK, CLI và Action CI ban đầu (`replay`, `scenario`) | FR-CLI-01, FR-CI-01 | V1 | ✅ Hoàn thành | [`python/neuroedge/`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/python/neuroedge/) · CLI thực thi `gate resolve/lint/publish`, `trace validate/show`, `board list/show`, `verify` · lệnh chưa có engine thoát mã 2 |
| **TSK-S1-10** | **Spike khả thi bộ nhớ trên ESP32-S3-Box-3** | NFR-RES-01, NFR-RES-02 | V2 | 🔴 **Chờ bo mạch** | Khung đo xong: [`memory_probe.c`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/targets/esp32s3/main/memory_probe.c) (4 checkpoint, dòng JSON máy đọc), [`check_firmware_size.py`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/scripts/check_firmware_size.py) · **chưa có số đo thực** → [báo cáo](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/reports/memory_spike_report.md) |
| **TSK-S1-11** | Rà soát thiết kế HAL dưới ràng buộc MCU | — | V2 | ✅ Hoàn thành | [`docs/spec/hal_mcu_review.md`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/spec/hal_mcu_review.md) (5 kết luận + 4 ràng buộc cho Sprint 4) · hiện thực tại [`hal/board.py`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/python/neuroedge/hal/board.py) + [`boards/`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/boards/) 3 target |
| **TSK-S1-12** | Hai workflow CI: `ci-sim-linux.yml` và `nightly-hardware.yml` | FR-CI-05, FR-CI-06 | V1 | ✅ Hoàn thành | [`ci-sim-linux.yml`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/.github/workflows/ci-sim-linux.yml) (lược đồ · phân giải gate · vết ghi · test 3 bản Python · lint · cổng giấy phép · **cổng chặn test skip**) · [`nightly-hardware.yml`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/.github/workflows/nightly-hardware.yml) (dựng IDF · ngân sách flash Q-3 · thu số đo · trôi phụ thuộc) |
| **TSK-S1-13** | Quy ước đóng góp và mẫu RFC đổi lược đồ | — | V1 | ✅ Hoàn thành | [`CONTRIBUTING.md`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/CONTRIBUTING.md) (7 mục) · [`docs/rfc/`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/rfc/): [quy trình](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/rfc/README.md), [mẫu](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/rfc/0000-template.md), [RFC-0001](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/rfc/0001-gate-schema-conditional-requirements.md) |

**Đòn bẩy OSS Sprint 1:** Pydantic v2 và `rfc8785` cho chuẩn hóa lược đồ · Typer, Rich, Copier cho khung CLI ban đầu. Tiết kiệm ước tính 3 tuần công sức viết mã.

**Nội dung spike bộ nhớ:** nạp thử AEC + VAD + Opus streaming lên ESP32-S3-Box-3, đo dung lượng SRAM và PSRAM còn lại sau khi trừ ngăn xếp mạng và hệ điều hành. Kết quả là **một con số**, không phải một nhận định.

Ngưỡng đối chiếu đã chốt tại Q-3: **SRAM cho ứng dụng ≥ 120 KB · PSRAM ≥ 2 MB · firmware ≤ 3,5 MB**. Không đạt ngưỡng nào thì kích hoạt bậc 5 của thang cắt phạm vi (§9) ngay, không chờ Tuần 9.

**Tiêu chí ra Sprint 1 (Exit Criteria):** — **4 / 6 đạt · 2 bị chặn ngoài tầm kỹ thuật**

- [x] **Tiêu chí 1:** JSON Schema của gate và trace publish nội bộ, có ví dụ hợp lệ và ví dụ sai kèm thông báo lỗi kỳ vọng.
  *Bằng chứng:* [`schemas/`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/schemas/) 3 tệp · hợp lệ: [`gates/`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/gates/) 3 gate + [`fixtures/gates/valid/`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/fixtures/gates/valid/) 5 tệp · **sai kèm lỗi kỳ vọng:** [`fixtures/gates/invalid/`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/fixtures/gates/invalid/) 15 tệp + [`expected_errors.yaml`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/fixtures/gates/expected_errors.yaml), [`fixtures/traces/invalid/`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/fixtures/traces/invalid/) 6 tệp + [`expected_errors.yaml`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/fixtures/traces/expected_errors.yaml). Test cưỡng chế corpus khép kín cả hai chiều (mỗi tệp có một mục, mỗi mục có một tệp) và mọi lỗi đủ 3 thành phần FR-DX-04.
- [x] **Tiêu chí 2:** Ba gate mẫu viết tay được công cụ phân giải đúng, gồm một trường hợp kế thừa 2 cấp.
  *Bằng chứng:* chuỗi `base-access@1.0.0` → `unlock_door@1.2.0` → `unlock_door_night@1.0.0` (đúng 3 cấp, tức **kế thừa 2 cấp**). `neuroedge gate lint` → *✓ 3 gate(s) resolved*. 26 test tại [`test_sample_gates.py`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/python/tests/test_sample_gates.py) kiểm tra từng nguyên tắc trên corpus thật, gồm mệnh đề **điều kiện chỉ siết chặt đơn điệu xuống chuỗi**.
- [ ] 🔴 **Tiêu chí 3:** Báo cáo spike bộ nhớ có số liệu đo thực, đối chiếu trực tiếp với ngưỡng Q-3 (SRAM ≥ 120 KB, PSRAM ≥ 2 MB, flash ≤ 3,5 MB).
  **CHƯA ĐẠT — chặn bởi phần cứng vật lý, không thể xử lý bằng công việc trên máy tính.** Khung đo đã xong và ngưỡng Q-3 đã ghim thành hằng số; [báo cáo](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/reports/memory_spike_report.md) nêu rõ 5 việc còn lại. Hàm đối chiếu trả `INCONCLUSIVE` khi checkpoint `audio_ready` chưa được lấy, để số đo sàn không bị đọc thành một kết quả đạt.
- [x] **Tiêu chí 4:** Bộ khung monorepo dựng xong; `schemas/` chứa đủ ba tệp lược đồ và được CI kiểm tra tính hợp lệ.
  *Bằng chứng:* job `frozen-artifacts` của [`ci-sim-linux.yml`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/.github/workflows/ci-sim-linux.yml) chạy `check_schema` draft 2020-12, đối chiếu `$id`, và **khẳng định nghịch đảo**: corpus phản chứng phải tiếp tục thất bại, nếu phân giải được thì job đỏ.
- [x] **Tiêu chí 5:** Ba tệp vết ghi chuẩn mực tại `fixtures/traces/` đã viết tay và phân giải đúng.
  *Bằng chứng:* `neuroedge trace validate fixtures/traces/*.json` → 3/3 VALID. 19 test tại [`test_trace_fixtures.py`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/python/tests/test_trace_fixtures.py) kiểm tra **nội dung kịch bản**, không chỉ tính hợp lệ lược đồ (happy-path cấp xung 30 000 ms; hai kịch bản còn lại **không sinh lệnh actuator nào**).
- [ ] 🔴 **Tiêu chí 6:** Quyết định Q-11 đã chốt (§10.2) — điều kiện để bắt đầu port bất kỳ dòng mã nào.
  **CHƯA ĐẠT — chặn bởi quyết định quản trị, chủ trì: kỹ thuật trưởng.** Không có dòng mã nào từ Hawkbit/EMQX/LiteLLM được port; phần D của [`NOTICE`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/NOTICE) ghi rõ phạm vi phơi nhiễm. Phát hiện phát sinh trong Sprint 1: `copier` kéo theo `jinja2-ansible-filters` **GPL3** — đã chuyển sang extra `scaffold` để lõi MIT không bị lây nhiễm, và cổng CI giấy phép chặn tái diễn.

**Ghi chú về phạm vi đã đóng:** toàn bộ khối lượng Sprint 1 **không phụ thuộc phần cứng hay quyết định quản trị** đã hoàn tất (12/13 task). Hai hạng mục còn lại không thể đóng bằng nỗ lực kỹ thuật thêm nữa.


### 4.2 Sprint 2 — Lõi thực thi trên `sim` (Tuần 2–4)


| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S2-01** | Hiện thực HAL cho target `sim` | FR-TGT-01, FR-HAL-01 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/hal/sim.py` |
| **TSK-S2-02** | Đối chiếu năng lực lúc build, thông báo lỗi đầy đủ 3 thành phần | FR-HAL-04, FR-HAL-05, FR-DX-04 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/engine/compiler.py` |
| **TSK-S2-03** | Gate Engine: `evaluate`, `allow_when`, `on_block`, `budget` | FR-GATE-03, FR-GATE-04, FR-GATE-09 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/engine/gate.py` |
| **TSK-S2-04** | Cơ chế fail-closed và mạch ngắt suy giảm | FR-ACE-03, NFR-REL-02 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/engine/circuit_breaker.py` |
| **TSK-S2-05** | Decorator `@action`, cấm gọi trực tiếp, `c.do()` và `c.say()` | FR-ACE-02, FR-ACE-04, FR-ACE-05, FR-ACE-07 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/actions/` |
| **TSK-S2-06** | Lượng giá `allow_when` trên nền Google CEL, kèm đường biên dịch gate cho thiết bị (§3.8, Q-9) | FR-GATE-03 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/engine/cel_compiler.py` |
| **TSK-S2-07** | **Đặc tả chuẩn tắc máy trạng thái hội thoại** — nguồn sự thật cho cả hai hiện thực (§3.8) | FR-PER-02, FR-PER-03 | V1 | ⏳ Chưa bắt đầu | `docs/spec/voice_fsm.md` |
| **TSK-S2-08** | Interface `SystemOne` / `SystemTwo` kèm fallback, giao diện kết nối mặc định tuân chuẩn OpenAI API | FR-MDL-01, FR-MDL-02, FR-MDL-03 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/models/` |
| **TSK-S2-09** | Giao diện web `sim`: cảm biến ảo, trạng thái actuator | FR-TGT-06 | V3 | ⏳ Chưa bắt đầu | `python/neuroedge/sim/web/` |
| **TSK-S2-10** | Kết luận phạm vi Khối 1b dựa trên spike | — | V2 + trưởng nhóm | ⏳ Chưa bắt đầu | `docs/reports/memory_spike_report.md` |
| **TSK-S2-11** | **Lớp trừu tượng nhà cung cấp**: hợp đồng kết nối OpenAI-compatible + cơ chế adapter tùy chỉnh, áp dụng chung cho LLM/ASR/TTS (CR-1.0) | FR-MDL-07, FR-MDL-08, FR-GW-01, FR-GW-03 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/models/providers/` |

**Tiêu chí ra Sprint 2 (Exit Criteria):**

- [ ] **Tiêu chí 1:** Agent mẫu chạy trên `sim`, gate chặn đúng theo `allow_when`.
- [ ] **Tiêu chí 2:** Gọi trực tiếp hành động vật lý ném `ActionContractViolation`, chân GPIO ảo không kích.
- [ ] **Tiêu chí 3:** Kịch bản mất mạng → hành động bị chặn với lý do `gate_unreachable`.
- [ ] **Tiêu chí 4:** Gate con nới lỏng `allow_when` bị từ chối phân giải.
- [ ] **Tiêu chí 5:** Quyết định Q-3, Q-7 đã chốt.
- [ ] **Tiêu chí 6:** Đổi nhà cung cấp mô hình chỉ bằng thay đổi cấu hình, không sửa mã agent và không sửa gate; một adapter tùy chỉnh mẫu chạy được mà không sửa lõi.


### 4.3 Sprint 3 — Action CI, `linux` và TTFV (Tuần 4–6)


| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S3-01** | Record: ghi phiên ra tệp JSON hợp lệ | FR-CI-01 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/testing/recorder.py` |
| **TSK-S3-02** | Replay trên target bất kỳ | FR-CI-02 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/testing/player.py` |
| **TSK-S3-03** | Thư viện assert: chặn, gate nào, leo thang, chân cấm kích | FR-CI-03 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/testing/assertions.py` |
| **TSK-S3-04** | Golden Reference và so khớp chuỗi phán quyết | FR-CI-04 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/testing/golden.py` |
| **TSK-S3-05** | Hiện thực HAL cho target `linux` qua `gpiod` | FR-TGT-02 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/hal/linux.py` |
| **TSK-S3-06** | CLI đầy đủ: `new`, `run`, `build`, `test`, `record`, `replay`, `trace validate` | FR-CLI-01→04, FR-TRC-08 | V3 | ⏳ Chưa bắt đầu | `python/neuroedge/cli/` |
| **TSK-S3-07** | Scaffold `neuroedge new` có sẵn action, gate, test | FR-DX-01 | V3 | ⏳ Chưa bắt đầu | `python/neuroedge/templates/` |
| **TSK-S3-08** | Ba ví dụ mẫu chạy được, README có tài sản trực quan | FR-DX-05, FR-DX-06 | V3 | ⏳ Chưa bắt đầu | `examples/` |
| **TSK-S3-09** | Telemetry CLI ẩn danh, có thể tắt | FR-TEL-01, FR-TEL-02 | V3 | ⏳ Chưa bắt đầu | `python/neuroedge/telemetry/` |
| **TSK-S3-10** | **Bộ vector kiểm thử tuân thủ độc lập ngôn ngữ** cho máy trạng thái hội thoại (§3.8) | FR-CI-07, FR-TGT-04 | V1 | ⏳ Chưa bắt đầu | `fixtures/compliance/` |
| **TSK-S3-11** | Hiện thực Python của máy trạng thái hội thoại, port thiết kế từ Pipecat | FR-PER-02→05 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/perception/fsm.py` |
| **TSK-S3-12** | Pipeline CI mẫu chạy `sim` + `linux` trên mỗi PR | FR-CI-05 | V1 | ⏳ Chưa bắt đầu | `.github/workflows/ci-sim-linux.yml` |
| **TSK-S3-13** | **Tích hợp ASR/TTS qua provider cloud** cho `sim` và `linux`, kèm tùy chọn mô hình cục bộ (CR-1.0) | FR-MDL-09, FR-PER-07 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/perception/providers/` |

**Tiêu chí ra Sprint 3 — cổng kết thúc Khối 1a (Exit Criteria):**

- [ ] **Tiêu chí 1 (A1):** TTFV đo thử nội bộ trên **3 người ngoài đội** đạt trung vị dưới 10 phút *(đo đầy đủ ở Tuần 12)*.
- [ ] **Tiêu chí 2 (A2):** `neuroedge verify --targets sim,linux` đạt 100% *(một phần)*.
- [ ] **Tiêu chí 3 (A3):** Không tồn tại đường tắt kích hoạt GPIO bỏ qua gate.
- [ ] **Tiêu chí 4 (A4):** 100% kịch bản suy giảm đều chặn hành động.
- [ ] **Tiêu chí 5 (A5):** Bộ kiểm thử kế thừa gate đạt 100%.
- [ ] **Tiêu chí 6 (A7):** 100% phiên sinh vết ghi qua được `neuroedge trace validate`.


---

## 5. Khối 1b — Vi điều khiển biên (Tuần 6–12)

**Mục tiêu khối:** chứng minh nguyên tắc tương đương môi trường trên vi điều khiển $5, với độ ổn định sản xuất.

### 5.1 Sprint 4 — HAL trên `esp32s3` (Tuần 6–8)

Sprint này **cố tình chưa làm thoại**. Mục đích là chứng minh tương đương target trên miền quyết định trước, khi biến số còn ít.


| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S4-01** | Port 5 nguyên thủy HAL lên ESP-IDF | FR-TGT-03, FR-HAL-01 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/hal/` |
| **TSK-S4-02** | Gate Engine chạy trên MCU (duyệt cây quyết định JSON) | FR-ACE-01, FR-ACE-03 | V2 + V1 | ⏳ Chưa bắt đầu | `targets/esp32s3/gate/` |
| **TSK-S4-03** | Đường dẫn `digital.out` và `sensor.read` trên phần cứng thật | FR-HAL-06, FR-HAL-07 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/drivers/` |
| **TSK-S4-04** | Lệnh `neuroedge verify` cho cả 3 target bậc 1 | FR-CI-07, FR-TGT-04 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/cli/verify.py` |
| **TSK-S4-05** | Runner kiểm thử nightly trên bo mạch thật | FR-CI-06, NFR-REL-03 | V3 | ⏳ Chưa bắt đầu | `.github/workflows/nightly-hardware.yml` |


**Đòn bẩy OSS Sprint 4:** ESP-IDF làm toolchain · port driver bo mạch từ XiaoZhi vào `targets/esp32s3/drivers/` (codec I2S ES8311/ES7210, chân I2C/SPI của Box-3, LCD ST7789) · LVGL cho hiển thị trạng thái. Tiết kiệm ước tính 7 tuần, trong đó 2–3 tuần nằm trên đường găng.

**Tiêu chí ra Sprint 4 (Exit Criteria):**

- [ ] **Tiêu chí 1 (A2):** `neuroedge verify --targets sim,linux,esp32s3` đạt 100% trên kịch bản **không dùng audio** → **A2 đạt cho miền phán quyết**.
- [ ] **Tiêu chí 2:** Sai lệch phán quyết giữa các target sinh `TargetEquivalenceError` chỉ rõ sự kiện lệch đầu tiên.
- [ ] **Tiêu chí 3:** Nightly runner chạy tự động và gửi báo cáo.


### 5.2 Sprint 5 — Runtime thoại trên MCU (Tuần 8–10)

**Đây vẫn là sprint khó nhất của toàn dự án, nhưng rủi ro đã giảm một bậc kể từ CR-1.0.** Kiến trúc cloud-first đưa STT, TTS và suy luận ngôn ngữ ra khỏi vi điều khiển; `esp32s3` chỉ còn thu/phát âm thanh, AEC/VAD, máy trạng thái hội thoại và thẩm định gate. Áp lực bộ nhớ SRAM/PSRAM giảm đáng kể, và rủi ro R-1 của PRD hạ từ Cao xuống Trung bình.


| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S5-01** | Tích hợp WebRTC AEC, Silero VAD, Opus streaming | FR-PER-06 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/audio/` |
| **TSK-S5-02** | Port đường dẫn audio thu/phát theo §3.5, tuân thủ nghĩa vụ ghi nhận nguồn §3.9. **Không hiện thực STT/TTS trên thiết bị** | FR-PER-01 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/drivers/audio_path.c` |
| **TSK-S5-03** | **Hiện thực C/C++ của máy trạng thái hội thoại** theo đặc tả Sprint 2, phải vượt bộ vector tuân thủ Sprint 3 (§3.8) | FR-PER-02, FR-PER-03, FR-PER-05 | V1 + V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/fsm/voice_fsm.c` |
| **TSK-S5-04** | Thu hồi lệnh actuator chưa thực thi khi bị cắt lời | FR-PER-02 | V1 + V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/fsm/actuator_abort.c` |
| **TSK-S5-05** | Tối ưu bộ nhớ theo ngân sách đã chốt ở Q-3 | NFR-RES-01, NFR-RES-02 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/sdkconfig.defaults` |
| **TSK-S5-06** | **Client streaming âm thanh lên provider cloud**: đẩy khung Opus lên STT, nhận luồng TTS về, tái dùng hợp đồng kết nối của TSK-S2-11 (CR-1.0) | FR-PER-07, FR-GW-04 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/audio/provider_client.c` |

**Ràng buộc kiến trúc bắt buộc:** máy trạng thái hội thoại chỉ có **một hiện thực duy nhất**, portable xuống MCU. Không được dùng một máy trạng thái cho `linux` và một máy trạng thái khác cho `esp32s3` — hai bản sẽ phân kỳ, và hành vi thu hồi lệnh actuator khi cắt lời sẽ khác nhau giữa các target, phá vỡ tương đương ở đúng miền nguy hiểm nhất.

**Đòn bẩy OSS Sprint 5:** microWakeWord trên MCU và openWakeWord trên Linux · Silero VAD và libfvad · WebRTC AEC3 · Opus · port mô hình frame processor và barge-in từ Pipecat. Không còn hạng mục STT/TTS trên thiết bị. Tiết kiệm ước tính 4 tuần, phần lớn nằm trên đường găng.

**Ràng buộc bắt buộc:** hiện thực C/C++ này là bản thứ hai của cùng một đặc tả, không phải một thiết kế độc lập. Nó chỉ được nghiệm thu khi vượt toàn bộ bộ vector tuân thủ chung (§3.8).

**Tiêu chí ra Sprint 5 (Exit Criteria):**

- [ ] **Tiêu chí 1:** Vòng lặp thoại chạy end-to-end trên bo mạch tham chiếu với STT, TTS và suy luận ngôn ngữ đặt ở provider cloud.
- [ ] **Tiêu chí 2:** Cắt lời giữa câu: TTS dừng dưới 300 ms, không có lệnh actuator nào rò rỉ.
- [ ] **Tiêu chí 3:** Bơm 20 khung nhiễu liên tiếp: máy trạng thái vẫn phản hồi đúng.
- [ ] **Tiêu chí 4:** Bộ nhớ còn lại sau 4 giờ chạy nằm trong ngân sách Q-3.
- [ ] **Tiêu chí 5:** Mất kết nối tới provider giữa phiên → hành động vật lý bị chặn với lý do fail-closed, thiết bị không treo và phục hồi được khi có mạng trở lại.


### 5.3 Sprint 6 — OTA, ổn định hóa, nghiệm thu (Tuần 10–12)


| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S6-01** | OTA cấp thiết bị: phân vùng kép A/B | FR-OTA-01 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/ota/` |
| **TSK-S6-02** | Tự động rollback khi phát hiện vòng lặp khởi động | FR-OTA-02 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/ota/rollback.c` |
| **TSK-S6-03** | Xác minh chữ ký firmware trên chip | FR-OTA-03 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/security/signature.c` |
| **TSK-S6-04** | Nạp firmware từ HTTP endpoint mở bất kỳ | FR-OTA-04 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/ota/http_ota.c` |
| **TSK-S6-05** | Secure boot, mã hóa flash, nút ngắt micro vật lý | NFR-SEC-02, NFR-SEC-03 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/security/` |
| **TSK-S6-06** | Kiểm thử chịu tải 24 giờ | NFR-RES-01, A6 | V3 | ⏳ Chưa bắt đầu | `tests/stress/` |
| **TSK-S6-07** | Publish JSON Schema công khai và bộ kiểm thử tuân thủ | FR-GOV-01, FR-GOV-03, A9 | V1 | ⏳ Chưa bắt đầu | `schemas/`, `tests/compliance/` |
| **TSK-S6-08** | Hoàn thiện tài liệu, ví dụ, video minh họa | FR-DX-05, FR-DX-06, A8 | V3 | ⏳ Chưa bắt đầu | `docs/`, `examples/` |


**Đòn bẩy OSS Sprint 6:** `esp_https_ota` và `esp_ota_ops` của ESP-IDF cho cập nhật phân vùng kép A/B và rollback cục bộ. Tiết kiệm ước tính 2 tuần.

**Tiêu chí ra Sprint 6 — cổng phát hành v1.0 (Exit Criteria):**
Đạt **toàn bộ A1 đến A9** của PRD §11.1 (không chấp nhận đạt một phần):

- [ ] **A1 (TTFV):** Trung vị dưới 10 phút trên **10 lập trình viên độc lập** chạy xong agent có gate trên `sim` *(ngưỡng nguyên văn của PRD A1)*.
- [ ] **A2 (Target Equivalence):** `neuroedge verify --targets sim,linux,esp32s3` đạt 100% khớp chuỗi sự kiện.
- [ ] **A3 (Safe by Construction):** Không có đường dẫn nào trong mã sinh lệnh actuator bỏ qua gate.
- [ ] **A4 (Fail-Closed Reliability):** 100% kịch bản suy giảm (mất mạng, timeout LLM, lỗi gate) đều chặn hành động.
- [ ] **A5 (Gate Inheritance Invariance):** Mọi vi phạm 5 nguyên tắc an toàn khi `extends` đều bị từ chối lúc compile.
- [ ] **A6 (Edge Resource Stability):** Chạy liên tục 24 giờ trên ESP32-S3 không vượt ngân sách RAM/Flash.
- [ ] **A7 (Trace Fidelity):** 100% vết ghi sinh ra đều hợp lệ với `schemas/trace.v1.json` và replay được.
- [ ] **A8 (Developer Experience):** CLI trực quan, tài liệu đầy đủ, 3 dự án mẫu hoạt động trơn tru.
- [ ] **A9 (Open Standard Governance):** JSON Schema và test harness phát hành công khai.

---

## 6. Developer Beta (Tuần 12–16)

### 6.1 Nguyên tắc vận hành

> **Đóng băng hoàn toàn việc phát triển tính năng mới.** Mọi đề xuất tính năng trong giai đoạn này được ghi vào danh mục chờ, không đưa vào mã nguồn.

Ngoại lệ duy nhất: lỗi chặn người dùng hoàn thành hành trình 10 phút.

### 6.2 Phân bổ công sức


| Trọng tâm                                  | Tỷ lệ công sức | Người             |
| :------------------------------------------ | :--------------: | :-----------------: |
| Hỗ trợ 1:1 qua Discord và GitHub           | 50%            | Cả đội luân phiên |
| Hoàn thiện tài liệu theo vướng mắc thực tế | 25%            | V3                |
| Sửa lỗi chặn                               | 20%            | V1, V2            |
| Đo đạc và tổng hợp chỉ số                  | 5%             | Trưởng nhóm       |


### 6.3 Mục tiêu tuyển người dùng


| Tuần | Mục tiêu tích lũy | Kênh                                          |
| :----: | :----------------- | :--------------------------------------------- |
| 12   | 10 lập trình viên | Mạng lưới cá nhân, cộng đồng nhúng địa phương |
| 13   | 25                | Bài viết kỹ thuật kèm video demo              |
| 14   | 50                | Diễn đàn ESP32, cộng đồng maker               |
| 16   | 50–100            | Tích lũy tự nhiên                             |


### 6.4 Chỉ số phải đo trong Beta


| Mã | Chỉ số | Ngưỡng | Trạng thái | Nguồn |
|:---:|:---|:---:|:---:|:---|
| **B1** | Lập trình viên ngoài chạy thành công agent trên `sim` | ≥ 50 | ⏳ Chưa bắt đầu | FR-TEL-01 |
| **B2** | Lập trình viên ngoài nạp thành công phần cứng thật | ≥ 10 | ⏳ Chưa bắt đầu | FR-TEL-01 |
| **B3** | Gate do cộng đồng tự viết và đóng góp | ≥ 3 | ⏳ Chưa bắt đầu | Registry |
| **B4** | Tỷ lệ giữ lại và mở rộng test gate mặc định | ≥ 50% | ⏳ Chưa bắt đầu | FR-TEL-01 |
| **B5** | Tỷ lệ chuyển đổi `sim` → phần cứng trong 30 ngày | ≥ 15% | ⏳ Chưa bắt đầu | FR-TEL-01 |
| **A1** | TTFV đo đầy đủ trên 10 người độc lập | Trung vị < 10 phút | ⏳ Chưa bắt đầu | Biên bản đo |


---

## 7. Điểm rẽ quyết định Tuần 16

Kết thúc Beta, dự án đi theo đúng một trong ba nhánh. **Quyết định dựa trên số liệu B1–B5, không dựa trên cảm nhận về đà phát triển.**


| Nhánh                               | Điều kiện                                                | Hành động                                                                                                               |
| :----------------------------------- | :-------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------- |
| **Nhánh A — Khởi động Khối 2**      | Đạt đồng thời B1, B2, B3                                 | Tuyển V4, bắt đầu **Fleet OS** (thương mại) theo §8; song song hoàn thiện lớp provider OSS                                                                           |
| **Nhánh B — Kéo dài Beta 4–6 tuần** | Đạt 2 trên 3 tiêu chí, tiêu chí còn lại đạt ≥ 60% ngưỡng | Giữ đóng băng tính năng, tập trung vào tiêu chí yếu nhất, đánh giá lại ở Tuần 22                                        |
| **Nhánh C — Xem xét lại luận điểm** | Không đạt hoặc chỉ đạt 1 trên 3                          | Dừng lộ trình thương mại. Phỏng vấn sâu 20 người dùng đã thử và bỏ. Xác định luận điểm sai ở đâu trước khi viết thêm mã |


**Chỉ báo quan trọng nhất là B2** (10 người ngoài nạp được phần cứng thật). B1 đo sự tò mò; B2 đo cam kết. Một dự án có B1 cao nhưng B2 thấp là một dự án mà simulator hấp dẫn còn đường lên phần cứng bị nghẽn — khi đó việc cần làm là sửa đường lên phần cứng, không phải xây Fleet OS.

---

## 8. Khối 2 và 3 — Tầng dịch vụ (Tháng 4–8)

Khởi động **chỉ khi** đi nhánh A. Hai khối chạy song song.

### 8.1 Trình tự Khối 2 — Fleet OS

Khối 2 chỉ còn **một dịch vụ thương mại: Fleet OS**. Ba hạng mục đầu (TSK-K2-01→03) là phần **hoàn thiện lớp trừu tượng provider OSS** đã dựng từ Khối 1a — giữ nguyên mã task để không vỡ truy vết, nhưng không thương mại hóa.


| Mã Task | Tháng | Trọng tâm công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) | Tiêu chí nghiệm thu |
|:---:|:---:|:---|:---|:---:|:---:|:---|:---|
| **TSK-K2-01** | **4** | Lớp provider OSS: gom một endpoint, một credential, xoay khóa do người dùng tự quản lý | FR-GW-01, FR-GW-02 | V4 | ⏳ Chờ mốc Beta | `python/neuroedge/models/providers/auth.py` | Một cấu hình phục vụ nhiều provider; xoay khóa không nạp lại firmware |
| **TSK-K2-02** | **5** | Lớp provider OSS: định tuyến đa nhà cung cấp, failover, hạn mức theo thiết bị *(tùy chọn)* | FR-GW-03, FR-GW-05 | V4 | ⏳ Chờ mốc Beta | `python/neuroedge/models/providers/routing.py` | Ngắt nhà cung cấp chính, thiết bị không gián đoạn |
| **TSK-K2-03** | **5–6** | Lớp provider OSS: giao thức tối ưu edge, xuất vết ghi đồng nhất định dạng | FR-GW-04, FR-GW-07 | V4 | ⏳ Chờ mốc Beta | `python/neuroedge/models/providers/traces.py` | Vết ghi từ lớp provider replay được trên máy cá nhân |
| **TSK-K2-04** | **6** | Fleet: cấp phát danh tính và chứng chỉ thiết bị | FR-FLT-01 | V4 | ⏳ Chờ mốc Beta | `services/fleet/provisioning.py` | Claim tự động trên lô 100 thiết bị |
| **TSK-K2-05** | **6–7** | Fleet: sổ kiểm kê, giám sát sức khỏe, dashboard hữu ích ở n = 1 | FR-FLT-03, FR-FLT-06 | V4 | ⏳ Chờ mốc Beta | `services/fleet/inventory.py` | Trạng thái phản ánh đúng trong 60 giây |
| **TSK-K2-06** | **7** | Fleet: cập nhật cấu hình, bí mật và gate từ xa | FR-FLT-04 | V4 | ⏳ Chờ mốc Beta | `services/fleet/config_sync.py` | Đổi ngưỡng gate toàn đội, không nạp lại firmware |
| **TSK-K2-07** | **7–8** | Fleet: điều phối OTA canary 1% → 10% → 100%, tự dừng khi vượt ngưỡng lỗi | FR-FLT-02 | V4 | ⏳ Chờ mốc Beta | `services/fleet/canary.py` | **1.000 thiết bị / 0 brick** |
| **TSK-K2-08** | **8** | Fleet: tự động tải vết ghi sự cố về kho tập trung | FR-FLT-05 | V4 | ⏳ Chờ mốc Beta | `services/fleet/trace_collector.py` | Sự cố xuất hiện trong kho dưới 5 phút |


**Đòn bẩy OSS Khối 2:** Eclipse Hawkbit cho điều phối chiến dịch OTA canary · EMQX hoặc FastAPI WebSockets cho kết nối và viễn trắc. **LiteLLM không còn là lõi của một gateway do NeuroEdge vận hành** — nó là thư viện của lớp trừu tượng provider self-host, đã dùng từ Sprint 2 và nay thuộc phần phân phối kèm sản phẩm (proposal Phụ lục H.1). Tiết kiệm ước tính 14 tuần. Xem ngoại lệ giấy phép tại §3.3.

### 8.2 Trình tự Khối 3 — Đường ray hạ tầng


| Mã Task | Tháng | Thành phần kỹ thuật | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---:|:---|:---|:---:|:---:|:---|
| **TSK-K3-01** | **4** | Định danh ổn định cho thiết bị, agent, gate | FR-REG-05 | V4 | ⏳ Chờ mốc Beta | `services/registry/identity.py` |
| **TSK-K3-02** | **4–5** | Hệ đo lường theo lượt gọi agent và lượt thẩm định gate | FR-REG-06, FR-TEL-04 | V4 | ⏳ Chờ mốc Beta | `services/metering/engine.py` |
| **TSK-K3-03** | **5** | Manifest và chuẩn phiên bản SemVer | FR-REG-02 | V4 | ⏳ Chờ mốc Beta | `schemas/manifest.v1.json` |
| **TSK-K3-04** | **5–6** | Kho Gate công khai miễn phí | FR-REG-01 | V4 | ⏳ Chờ mốc Beta | `services/registry/oci_store.py` |
| **TSK-K3-05** | **6–7** | Cơ chế phân quyền và sandbox | FR-REG-07 | V4 | ⏳ Chờ mốc Beta | `services/registry/sandbox.py` |


**Thứ tự này không tùy tiện.** FR-REG-05, FR-REG-06 và FR-REG-07 phải đi trước vì không bổ sung sau được: thiếu định danh ổn định và đo lường thì Registry không quy kết được ai dùng gì; thiếu sandbox thì không dám cho mã người lạ chạy trên thiết bị có cơ cấu chấp hành.

| **TSK-K3-06** | **6–7** | Kho chia sẻ adapter kết nối provider do cộng đồng đóng góp, dùng chung hạ tầng Registry của TSK-K3-04 (CR-1.0) | FR-REG-08 | V4 | ⏳ Chờ mốc Beta | `services/registry/adapters.py` |

**Đòn bẩy OSS Khối 3:** CNCF ORAS và Harbor cho kho Gate Registry theo chuẩn OCI · OpenMeter cho hệ đo lường tương thích Stripe Billing. Tiết kiệm ước tính 8 tuần.

### 8.3 Tiêu chí ra Khối 2 và 3 (Exit Criteria)

Bảy tiêu chí **TR-1 đến TR-7** dưới đây là tiêu chí ra **cấp thực thi** của Khối 2 và 3. Chúng là một bộ **khác** với bộ nghiệm thu phát hành **C1–C7** của PRD §11.3: TR đo *việc đã làm xong chưa*, C đo *sản phẩm đã đủ điều kiện phát hành chưa*. Cột cuối chỉ rõ mỗi TR phục vụ tiêu chí C nào; TR nào không có C tương ứng là tiêu chí nội bộ của roadmap.

| Mã | Tiêu chí ra Khối 2 và 3 | Phục vụ tiêu chí nghiệm thu PRD |
|:---|:---|:---:|
| **TR-1** | Provider Layer Self-Host | — *(nội bộ)* |
| **TR-2** | Zero-Brick Fleet OTA | **C1** |
| **TR-3** | Incident MTTR dưới 10 phút | — *(nội bộ)* |
| **TR-4** | Registry Verified Gates | Tiền đề của **C5** |
| **TR-5** | Usage Attribution | — *(nội bộ)* |
| **TR-6** | Failover Resiliency | — *(nội bộ; hiện thực hóa FR-GW-03)* |
| **TR-7** | Fleet Remote Config | — *(nội bộ)* |

*Tiêu chí PRD **C2, C3, C4, C6, C7** không có TR tương ứng vì chúng được đo ở mức sản phẩm sau khi Khối 2 và 3 hoàn tất, không đo được trong lúc thực thi.*

- [ ] **TR-1 (Provider Layer Self-Host):** Lớp trừu tượng provider chạy tự vận hành trên hạ tầng của người dùng; thiết bị biên không nhúng cứng API key của từng nhà cung cấp, và khóa xoay được mà không nạp lại firmware.
- [ ] **TR-2 (Zero-Brick Fleet OTA):** Triển khai thử nghiệm 1.000 thiết bị ảo/thật qua canary; tỷ lệ brick là 0%.
- [ ] **TR-3 (Incident MTTR < 10m):** Vết ghi sự cố từ thiết bị được tải về dashboard trung tâm trong dưới 5 phút; kỹ sư tái hiện lỗi bằng `replay` trong dưới 5 phút tiếp theo.
- [ ] **TR-4 (Registry Verified Gates):** Ít nhất 10 gate mã nguồn mở được publish lên Gate Registry có kiểm định tự động.
- [ ] **TR-5 (Usage Attribution):** Hệ đo lường OpenMeter đối soát chính xác 100% số lượt gọi mô hình và phán quyết gate tới cấp thiết bị *(phục vụ vận hành và đối soát nội bộ — NeuroEdge không thu phí trên lượt gọi mô hình)*.
- [ ] **TR-6 (Failover Resiliency):** Giả lập ngắt kết nối nhà cung cấp LLM chính; lớp trừu tượng provider tự động chuyển sang nhà cung cấp dự phòng trong dưới 2 giây.
- [ ] **TR-7 (Fleet Remote Config):** Đổi chính sách gate từ dashboard điều khiển từ xa có hiệu lực trên toàn đội dưới 30 giây mà không cần khởi động lại firmware.

---

## 9. Thang cắt phạm vi

Khi tiến độ trượt, cắt theo đúng thứ tự sau. **Không cắt nhảy bậc, không cắt tùy hứng.**


| Bậc   | Hạng mục cắt                                                                       | Mất gì                                                                          | Yêu cầu bị ảnh hưởng |
| :-----: | :---------------------------------------------------------------------------------- | :------------------------------------------------------------------------------- | :-------------------- |
| **1** | Ví dụ mẫu thứ 2 và 3, giữ lại 1                                                    | Tài liệu mỏng hơn                                                               | FR-DX-05             |
| **2** | Chính sách định tuyến khai báo được → viết cứng `fast_first`                       | Mất tính linh hoạt cấu hình                                                     | FR-MDL-05 *(P1)*     |
| **3** | Client MCP                                                                         | Hoãn ván cược về chuẩn giao tiếp công cụ                                        | —                    |
| **4** | Phản hồi dòng từng phần                                                            | Độ trễ cảm nhận tăng                                                            | FR-PER-04 *(P1)*     |
| **5** | **Tách Khối 1b:** `esp32s3` chỉ chạy gate và GPIO; runtime thoại đẩy sang sau Beta | Chứng minh tương đương target trên miền quyết định nhưng chưa có thoại trên MCU | FR-PER-06            |


### 9.1 Tuyệt đối không cắt


| Hạng mục                              | Lý do                                                           |
| :------------------------------------- | :--------------------------------------------------------------- |
| Hợp đồng năng lực HAL                 | Là nền của tương đương target                                   |
| Gate Engine và fail-closed            | Là mệnh đề trung tâm của sản phẩm                               |
| Lược đồ vết ghi và record/replay      | Không retrofit được                                             |
| Golden Reference                      | Không có nó thì Action CI chỉ là một thư viện test thông thường |
| `sim` là target thật, không phải mock | Cắt cái này là cắt toàn bộ luận điểm                            |
| Nguyên tắc kế thừa gate an toàn       | Thiếu nó, `extends` là rủi ro chứ không phải tính năng          |


### 9.2 Ghi chú về bậc 5

Bậc 5 là bậc nặng nhất và cũng là phương án ứng phó chính cho rủi ro **R-1**. Nó giữ được luận điểm tương đương target — vốn được chứng minh trên phán quyết gate và trạng thái GPIO, không phải trên chất lượng thoại — đồng thời giữ được mốc phát hành. Cái mất là sức thuyết phục của bản demo, vì video "nói chuyện với con chip $5" là tài sản phân phối mạnh nhất (§1.5 của proposal).

**Quyết định áp dụng bậc 5 phải đưa ra chậm nhất ở Tuần 9.** Muộn hơn thì vừa mất thoại vừa mất mốc.

---

## 10. Lịch chốt quyết định

**Sổ quyết định là PRD §15**, nơi định nghĩa đầy đủ mười ba quyết định Q-1 đến Q-13. Mục này **không định nghĩa quyết định mới** — nó chỉ theo dõi hạn chốt, người quyết và trạng thái thực thi. Khi hai tài liệu lệch nhau, PRD §15 đúng.

### 10.1 Chín quyết định đã chốt

| Mã | Quyết định | Giá trị chốt | Cơ sở |
|:---:|:---|:---|:---|
| **Q-1** | Phiên bản Python tối thiểu | **Python 3.11+** | `tomllib` có sẵn trong thư viện chuẩn nên không cần `tomli` · `TaskGroup` và `ExceptionGroup` trong `asyncio` · bytecode nhanh hơn khoảng 25% so với 3.10 |
| **Q-2** | Bo mạch tham chiếu chính thức | **ESP32-S3-Box-3** | Tích hợp sẵn LCD ST7789, dual-mic ES7210, loa ES8311, dock GPIO. Loại bỏ hoàn toàn việc câu dây thủ công vốn gây nhiễu clock I2S trên DevKitC. DevKitC hạ xuống bo mạch thứ cấp do cộng đồng hỗ trợ |
| **Q-3** | Ngân sách bộ nhớ và firmware | **SRAM cho ứng dụng ≥ 120 KB · PSRAM ≥ 2 MB · firmware ≤ 3,5 MB** | Bảo đảm nạp vừa phân vùng kép A/B trên flash 16 MB của Box-3. PSRAM dành cho ring buffer âm thanh, VAD và wake-word |
| **Q-4** | Nhà cung cấp mô hình ở v1.0 | **System 1:** Jev qua đám mây + bộ trích xuất intent cục bộ trên Sherpa-ONNX làm fallback<br>**System 2:** Claude Sonnet 5 và GPT-4o-mini qua LiteLLM | Bảo đảm nguyên tắc fallback cục bộ khi mất mạng thực sự khả thi, không chỉ là tuyên bố kiến trúc |
| **Q-8** | Ngôn ngữ lõi firmware | **C/C++ trên ESP-IDF** cho `esp32s3`; Python cho `sim` và `linux` | Thừa hưởng trọn vẹn driver XiaoZhi và hệ sinh thái ESP-IDF. Kéo theo nghĩa vụ đặc tả chuẩn tắc và bộ vector tuân thủ tại §3.8 |
| **Q-9** | Lượng giá CEL trên vi điều khiển | **Phương án A — biên dịch gate lúc build** | `neuroedge build` dịch CEL thành cây quyết định JSON phẳng; firmware duyệt cây bằng một hàm C khoảng 100 dòng. Phán quyết đồng nhất trên mọi target, không tốn RAM |
| **Q-12** | Chuẩn kết nối nhà cung cấp AI | **OpenAI API là chuẩn mặc định**; provider chưa tương thích đi qua **adapter do người dùng tự viết**. Áp dụng chung cho LLM, ASR và TTS | Chốt theo CR-1.0 (PRD §15, FR-MDL-07→09). Tận dụng hệ sinh thái đã quen chuẩn OpenAI thay vì phát minh hợp đồng riêng; adapter giữ đường thoát khi chuẩn bên ngoài thay đổi |
| **Q-7** | Từ khóa kích hoạt mặc định v1.0 | ***"Hey Neuro"*** qua `microWakeWord` trên Box-3 và `openWakeWord` trên `linux`/`sim` | Chốt sớm để Sprint 5 chọn được mô hình wake-word mà không phải chờ. Tiêu chí ra Sprint 2 đã yêu cầu quyết định này |
| **Q-13** | Phân tầng cam kết theo bậc target | **Ba bậc:** bậc 1 giữ toàn bộ cam kết chất lượng; bậc 2 đội lõi bảo trì với cam kết hẹp hơn; bậc 3 cộng đồng tự kiểm chứng | Cho phép mở rộng phần cứng ở Giai đoạn 2 mà không pha loãng chất lượng bậc 1 (FR-TGT-08) |

**Hệ quả trực tiếp lên Sprint 1:** Q-1, Q-2 và Q-3 đã chốt nghĩa là đội có thể đặt bo mạch, dựng kho mã và bắt đầu spike ngay Tuần 0 mà không chờ quyết định nào.

**Một điều chỉnh so với đề xuất gốc:** Q-4 ghi Claude Sonnet 5 thay vì Sonnet 3.5. Thế hệ 3.5 đã bị thay thế; chốt một định danh mô hình lỗi thời vào tài liệu nền sẽ tạo nợ ngay từ ngày đầu.

### 10.2 Bốn quyết định còn mở

| Tuần | Mã | Quyết định | Vì sao hạn đó | Người quyết | Trạng thái |
|:---:|:---:|:---|:---|:---:|:---:|
| **2** | **Q-11** | Phê duyệt ngoại lệ giấy phép: Hawkbit EPL-2.0, EMQX BSL, LiteLLM enterprise | Chặn việc thiết kế phụ thuộc cho Khối 2. Phải xong trước khi port bất kỳ dòng nào (§3.3). **CR-1.0 làm phần LiteLLM gấp hơn:** nó chuyển từ dịch vụ máy chủ sang thư viện **phân phối kèm sản phẩm** trong lõi MIT, nên nghĩa vụ giấy phép phải xét lại ở phạm vi phân phối, và cần xong trước Sprint 2 chứ không phải trước Khối 2 | Kỹ thuật trưởng | ⏳ Đang mở |
| **2** | **Q-10** | Mức độ phụ thuộc vào LiteLLM: dùng như thư viện định tuyến hay tích hợp sâu | **Hạn đẩy sớm từ Tháng 3 lên Tuần 2 theo CR-1.0:** lớp provider nay thuộc lõi OSS và làm ngay ở Sprint 2 (TSK-S2-11), không còn chờ Khối 2 | Kỹ thuật nền tảng | ⏳ Đang mở |
| **Tháng 3** | Q-5 | Xác thực và chống lạm dụng cho Registry công khai | Cần trước khi thiết kế hạ tầng Khối 3 | Kỹ thuật nền tảng | ⏳ Đang mở |
| **Tháng 6** | **RFC-0002** | Mở rộng enum `target` và đưa bậc target vào mã lõi (`TARGET_TIERS`) cho Giai đoạn 2; `vision.in` tách sang RFC riêng ở V1b | Không chặn roadmap này. Chặn Khối V1a của Giai đoạn 2, và phải xong trước khi viết bất kỳ board profile mới nào | Kỹ thuật trưởng | ⏳ Đang mở |
| **Tháng 3** | Q-6 | Chính sách lưu trữ vết ghi: thời hạn và hạn mức | Ảnh hưởng chi phí vận hành và cam kết SLA | Sản phẩm | ⏳ Đang mở |

**Q-11 là quyết định gấp nhất trong nhóm còn mở.** Ba thành phần của Khối 2 đều nằm ngoài danh sách giấy phép cho phép, và việc thiết kế phụ thuộc không nên bắt đầu trước khi có phê duyệt bằng văn bản. Q-11 cũng là **Tiêu chí ra số 6 của Sprint 1**, nên nó đang chặn việc đóng Sprint 1 chứ không chỉ chặn Khối 2. Sau CR-1.0, phần LiteLLM của Q-11 còn chặn thêm **TSK-S2-11 ở Sprint 2**: không được viết một dòng nào của lớp provider trước khi ranh giới giấy phép ở phạm vi phân phối được phê duyệt.

#### Phát hiện giấy phép trong Sprint 1 (đã xử lý, ghi lại để không tái diễn)

Khi dựng cổng giấy phép cho CI (TSK-S1-12), rà soát phụ thuộc phát hiện **hai đường lây nhiễm copyleft mạnh vào lõi MIT** — cả hai đều là phụ thuộc bắc cầu, không ai chủ ý thêm:

| Đường lây nhiễm | Giấy phép | Cách xử lý |
|:---|:---|:---|
| `neuroedge` → `copier` → `jinja2-ansible-filters` | **GPL3** | `copier` chuyển khỏi tập phụ thuộc lõi sang extra `scaffold`. Nó chỉ cần cho `neuroedge new` (TSK-S3-07), chưa hiện thực, nên không mất gì |
| `neuroedge` → `jsonschema[format]` → `rfc3987` | **GPL** | Ghim extra `[format-nongpl]`, dùng `rfc3987-syntax` (MIT). Extra này là **bắt buộc**, không phải tùy chọn: thiếu bộ kiểm tra format thì `format: date-time` trong `trace.v1.json` chỉ là chú thích, và một vết ghi có mốc thời gian không phân tích được vẫn thẩm định đạt |

Cả hai đều trực tiếp hiện thực hóa rủi ro mà §3.10 của tài liệu này nêu: *"Nhúng mã GPLv3 vào phần phân phối → Lây nhiễm bản quyền sang lõi MIT và sang dự án của khách hàng."* Điều đáng chú ý là **không ai thêm một phụ thuộc GPL nào một cách chủ ý** — cả hai đến qua phụ thuộc bắc cầu của một thư viện hoàn toàn permissive. Rà soát giấy phép bằng mắt ở tầng phụ thuộc trực tiếp sẽ bỏ sót cả hai.

Vì vậy job `licence-obligations` trong [`ci-sim-linux.yml`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/.github/workflows/ci-sim-linux.yml) chạy `pip-licenses --fail-on` trên **toàn bộ cây phụ thuộc** ở mỗi pull request, và lưu bảng giấy phép đầy đủ làm artifact. Đây là nghĩa vụ 1 và 5 của §3.9 được tự động hóa, thay cho một lần rà soát thủ công.

**Hệ quả cho Q-11:** quyết định Q-11 nên bao gồm luôn một chính sách rõ ràng cho phụ thuộc bắc cầu, không chỉ phê duyệt ba thành phần đã nêu tên.

---

## 11. Nhịp vận hành

### 11.1 Nhịp định kỳ


| Tần suất        | Hoạt động                                                   | Từ tuần |
| :--------------- | :----------------------------------------------------------- | :-------: |
| Hằng ngày       | Đồng bộ ngắn 15 phút                                        | 0       |
| Hằng tuần       | Demo chạy thật — **trên phần cứng thật từ Tuần 6**          | 2       |
| Hằng tuần       | Rà soát chỉ báo sớm §12                                     | 2       |
| Hằng đêm        | Kiểm thử tự động trên bo mạch thật                          | 8       |
| Cuối mỗi sprint | Nghiệm thu theo tiêu chí ra, không nghiệm thu theo cảm nhận | 2       |


### 11.2 Định nghĩa hoàn thành

Một hạng mục chỉ được coi là hoàn thành khi đủ **cả năm** điều kiện:


| #   | Điều kiện                                                                      |
| :---: | :------------------------------------------------------------------------------ |
| 1   | Mã đã review và hợp nhất                                                       |
| 2   | Có kiểm thử tự động chạy trong CI, bao gồm ít nhất một ca thất bại             |
| 3   | Tiêu chí nghiệm thu của yêu cầu PRD tương ứng đã đạt và ghi nhận               |
| 4   | Tài liệu và `--help` cập nhật                                                  |
| 5   | Thông báo lỗi liên quan nêu đủ ba thành phần: sai ở đâu, vì sao, xử lý thế nào |


### 11.3 Quy tắc bảo vệ đường găng


| Quy tắc                              | Nội dung                                                                         |
| :------------------------------------ | :-------------------------------------------------------------------------------- |
| **Đóng băng lược đồ**                | Sau Tuần 2, mọi thay đổi lược đồ cần RFC, phê duyệt và kịch bản di trú           |
| **Không nợ kỹ thuật ở tầng an toàn** | Gate Engine và HAL không được hợp nhất kèm ghi chú "sẽ sửa sau"                  |
| **Sai lệch tương đương là lỗi chặn** | `TargetEquivalenceError` trong nightly dừng mọi việc khác cho tới khi xử lý xong |
| **Đóng băng tính năng trong Beta**   | Không ngoại lệ ngoài lỗi chặn hành trình 10 phút                                 |


---

## 12. Chỉ báo sớm và ngưỡng can thiệp


| #     | Chỉ báo                              | Ngưỡng vàng                              | Ngưỡng đỏ                           | Hành động khi đỏ                                                          |
| :-----: | :------------------------------------ | :---------------------------------------- | :----------------------------------- | :------------------------------------------------------------------------- |
| **1** | Tiến độ Sprint 1 — đóng băng lược đồ | Chậm 3 ngày                              | Chậm 1 tuần                         | Cắt phạm vi lược đồ về mức tối thiểu chạy được; hoãn `choice` sang bản vá |
| **2** | Kết quả spike bộ nhớ                 | Còn dư dưới 30% ngân sách                | **Không đủ chỗ cho voice pipeline** | Kích hoạt bậc 5 thang cắt ngay, không chờ Tuần 9                          |
| **3** | Sai lệch `neuroedge verify`          | 1 ca lệch                                | Từ 3 ca lệch trở lên                | Dừng phát triển tính năng, truy nguyên gốc kiến trúc                      |
| **4** | Tiến độ Sprint 5 — thoại trên MCU    | Tuần 9 chưa có vòng lặp thoại hoàn chỉnh | Tuần 10 chưa có                     | Kích hoạt bậc 5                                                           |
| **5** | Số người dùng Beta ngoài đội         | Tuần 14 dưới 25 người                    | Tuần 14 dưới 10 người               | Dừng tuyển thêm, phỏng vấn sâu 10 người đã thử để tìm điểm nghẽn          |
| **6** | Tỷ lệ B2 — nạp phần cứng thật        | Dưới 20% của B1                          | Dưới 10% của B1                     | Điều tra đường lên phần cứng; đây là chỉ báo sớm của nhánh C              |
| **7** | Tỷ lệ áp dụng Action CI              | Dưới 40%                                 | Dưới 25%                            | Xem lại scaffold và tài liệu: Action CI chưa được đặt làm trung tâm       |


**Nguyên tắc đọc bảng:** ngưỡng vàng kích hoạt thảo luận trong buổi rà soát tuần. Ngưỡng đỏ kích hoạt hành động đã ghi sẵn, không thảo luận lại.

---

# Phụ lục

## Phụ lục A — Bảng mốc tổng hợp


| Mốc                  | Thời điểm   | Nội dung                                | Cổng nghiệm thu                        |
| :-------------------- | :-----------: | :--------------------------------------- | :-------------------------------------- |
| Đóng băng lược đồ    | Tuần 2      | Gate v1, trace v1, hợp đồng HAL         | Tiêu chí ra Sprint 1                   |
| Lõi chạy trên `sim`  | Tuần 4      | Gate Engine, fail-closed, `@action`     | Tiêu chí ra Sprint 2                   |
| **Kết thúc Khối 1a** | **Tuần 6**  | Action CI, `linux`, CLI, TTFV           | A1 nội bộ, A2 một phần, A3, A4, A5, A7 |
| Tương đương bậc 1    | Tuần 8      | `esp32s3` chạy gate và GPIO             | **A2 đầy đủ** trên miền phán quyết     |
| Thoại trên MCU       | Tuần 10     | Thu/phát + gate trên MCU, STT/TTS cloud | Tiêu chí ra Sprint 5                   |
| **Phát hành v1.0**   | **Tuần 12** | OTA, bảo mật thiết bị, tài liệu         | **Toàn bộ A1–A9**                      |
| Kết thúc Beta        | Tuần 16     | 50–100 lập trình viên ngoài             | B1–B5                                  |
| **Điểm rẽ**          | **Tuần 16** | Chọn nhánh A, B hoặc C                  | §7                                     |
| Lớp provider OSS xong| Tháng 6     | Định tuyến, failover, vết ghi đồng nhất | TR-6                                   |
| **Phát hành v1.1**   | **Tháng 8** | Fleet OS, OTA canary, Registry          | **TR-1→TR-7** + PRD **C1–C7**          |


## Phụ lục B — Danh mục mua sắm và hạ tầng

Cần chuẩn bị trước Tuần 1 để không chặn đường găng.


| Hạng mục                                       | Số lượng | Cần trước  | Ghi chú                                              |
| :---------------------------------------------- | :--------: | :----------: | :---------------------------------------------------- |
| **ESP32-S3-Box-3** (bo mạch tham chiếu chính thức) | 5–8 | **Tuần 1** | Chốt tại Q-2. Đã tích hợp LCD, dual-mic và loa nên không cần mua rời. Dư ra cho nightly runner và bo mạch hỏng |
| ESP32-S3-DevKitC (bo mạch thứ cấp) | 2 | Tuần 3 | Kiểm chứng tính di động của HAL ngoài Box-3; hỗ trợ ở mức cộng đồng |
| Raspberry Pi 5                                 | 2        | Tuần 3     | Target `linux` trên ARM64                            |
| Máy Linux x86-64                               | 1        | Tuần 3     | Target `linux` trên x86, có thể dùng máy ảo          |
| Mạch nạp và cáp JTAG                           | 2 bộ     | Tuần 1     | Gỡ lỗi cấp thanh ghi                                 |
| Runner CI tự quản có gắn bo mạch thật          | 1        | **Tuần 6** | Bắt buộc cho nightly từ Tuần 8                       |
| Tên miền và hạ tầng cho `schema.neuroedge.dev` | —        | Tuần 10    | Phục vụ FR-GOV-01 và A9                              |
| Máy chủ Discord và kho GitHub công khai        | —        | Tuần 10    | Phục vụ giai đoạn Beta                               |
| *Giai đoạn 2:* Jetson Orin Nano                | 2        | Tháng 12   | Target `jetson` bậc 2 — chỉ mua sau khi RFC-0002 duyệt |
| *Giai đoạn 2:* Camera USB/CSI + NPU Hailo-8 hoặc Coral | 2 bộ | Tháng 9 | Nguyên thủy `vision.in` trên `linux` — xem `neuroedge-roadmap-phase2.md` |


---

## Phụ lục C — Bố cục kho mã nguồn

Cấu trúc monorepo chính thức, dựng trong Sprint 1. Mọi đường dẫn nêu trong tài liệu này và trong PRD đều tham chiếu tới cây thư mục dưới đây.

```text
neuroedge/
├── .github/workflows/
│   ├── ci-sim-linux.yml        # Action CI trên sim và linux, chạy mỗi pull request
│   └── nightly-hardware.yml    # Kiểm thử hằng đêm trên bo mạch Box-3 thật
├── schemas/                    # NGUỒN SỰ THẬT DUY NHẤT
│   ├── trace.v1.json           # JSON Schema draft 2020-12 cho tệp vết ghi
│   ├── gate.v1.json            # JSON Schema cho cổng an toàn
│   └── board.v1.json           # JSON Schema đối chiếu năng lực bo mạch
├── python/                     # Gói phân phối qua PyPI
│   ├── pyproject.toml          # Python 3.11+
│   ├── neuroedge/
│   │   ├── cli/                # Typer · Rich · Copier
│   │   ├── hal/                # 5 nguyên thủy và bộ đối chiếu năng lực lúc build
│   │   ├── engine/             # Action Contract Engine · trình biên dịch CEL sang cây quyết định
│   │   ├── models/             # SystemOne/SystemTwo · lớp provider (OpenAI-compatible + adapter)
│   │   ├── perception/         # Voice pipeline · VAD · barge-in · provider ASR/TTS
│   │   ├── testing/            # Action CI: pytest-neuroedge · replay · assert
│   │   └── sim/                # Máy chủ mô phỏng web · Wokwi Elements
│   └── tests/
├── targets/                    # Hiện thực HAL cho từng môi trường
│   ├── sim/                    # Backend mô phỏng trong bộ nhớ (Python)
│   ├── linux/                  # gpiod v2 · ALSA (Python)
│   └── esp32s3/                # Firmware ESP-IDF (C/C++)
│       ├── CMakeLists.txt
│       ├── sdkconfig.defaults  # PSRAM · FreeRTOS 1000 Hz · I2S
│       ├── partitions.csv      # Phân vùng kép A/B trên flash 16 MB
│       ├── main/               # Vòng lặp FreeRTOS · action dispatcher
│       └── components/         # Codec ES8311/ES7210 · LCD ST7789 · OTA agent
├── fixtures/traces/            # Bộ vector tuân thủ dùng chung
│   ├── happy-path.json
│   ├── unverified_attempt.json
│   └── network_offline.json
├── examples/villa-concierge/   # Dự án mẫu sinh bởi `neuroedge new`
└── NOTICE                      # Ghi nhận bản quyền các dự án đã port
```

**Ba quy ước bắt buộc:**

| # | Quy ước | Lý do |
|:---:|:---|:---|
| 1 | `schemas/` là nguồn sự thật duy nhất; mã Python và firmware C đều sinh hoặc kiểm tra theo nó, không định nghĩa lại | Chống trôi lược đồ giữa hai ngôn ngữ |
| 2 | `fixtures/traces/` dùng chung cho mọi target, không có bản riêng theo ngôn ngữ | Là cơ sở của `neuroedge verify` |
| 3 | `targets/` chỉ chứa hiện thực HAL, không chứa logic nghiệp vụ hay chính sách an toàn | Giữ ranh giới tài sản lõi tại §3.1 |
| 4 | Lớp kết nối nhà cung cấp nằm trong `python/neuroedge/models/providers/`, **không** nằm trong `services/` | Nó thuộc lõi mã nguồn mở phân phối kèm sản phẩm, không phải dịch vụ do NeuroEdge vận hành (CR-1.0) |

---

## Phụ lục D — Giao thức truyền dẫn

Chuẩn trao đổi dữ liệu giữa thiết bị và máy tính phát triển, cần thiết cho `record`, `replay` và luồng thoại thời gian thực.

### D.1 Kênh truyền

| Kênh | Giao thức | Nội dung truyền |
|:---|:---|:---|
| **Wi-Fi / LAN** | WebSocket trên TLS | Khung nhị phân cho luồng âm thanh Opus · khung văn bản cho sự kiện vết ghi JSON |
| **Cáp nạp / UART** | SLIP đóng khung nhị phân, hoặc JSON Lines phân cách bằng ký tự xuống dòng | Tốc độ 921600 baud để tránh nghẽn băng thông |

### D.2 Định dạng âm thanh

| Tham số | Giá trị |
|:---|:---|
| Bộ mã hóa | Opus, chế độ voice |
| Băng thông | 16 kbps |
| Tần số lấy mẫu | 16 kHz, một kênh |
| Kích thước khung | 20 ms, tương đương 320 mẫu |

Cùng một định dạng dùng cho mọi target. Môi trường `sim` phát lại tệp WAV qua đúng đường dẫn mã hóa này để giữ tương đương với phần cứng thật.

---

*Hết tài liệu*