# NeuroEdge — Roadmap thực thi

## Kế hoạch triển khai từ Tuần 0 đến Tháng 8

**Phiên bản:** 1.3


**Ngày lập:** 21 tháng 9, 2026 · **Cập nhật:** 23 tháng 9, 2026 (áp dụng quyết định Q-10, Q-11 phần LiteLLM, Q-14 → Q-20)


**Tài liệu nguồn:** `neuroedge-proposal.md` v5.4 · `neuroedge-prd.md` v1.2 · kế hoạch Sprint 2–3 [`docs/designs/giai-doan-1-wedge-truoc-mcu-sau.md`](docs/designs/giai-doan-1-wedge-truoc-mcu-sau.md) · việc hoãn có chủ ý [`TODOS.md`](TODOS.md)


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

Mọi mã và ký hiệu dùng trong tài liệu này (`TSK-*`, `A1`–`C7`, `TR-N`, `Q-N`, `RB-N`, `V1`–`V4`, `Tuần N` · `Tháng N`, `§x.y`…) được giải mã ở **[`docs/user/thuat-ngu.md`](docs/user/thuat-ngu.md)** — nơi duy nhất, kèm chỗ định nghĩa đầy đủ.

## 0. Bảng theo dõi tiến độ & Nhật ký bàn giao (Live Execution & Handoff Dashboard)

> **Mục đích:** Cung cấp điểm nhìn tập trung duy nhất về trạng thái thời gian thực của toàn bộ dự án. Mọi phiên làm việc (session), kỹ sư hoặc AI Agent khi nhận bàn giao chỉ cần đọc mục này là nắm được ngay: *Hệ thống đang ở đâu, vừa hoàn thành gì, ai đang làm gì, và bước hành động kế tiếp là gì.*

### 0.1 Thanh trạng thái điều hành (Executive Status Bar)

| Chỉ số | Trạng thái hiện hành | Ghi chú & Liên kết |
|:---|:---|:---|
| **Pha đang thực thi** | 🟡 **Khối 1a: Lõi logic & Action CI (Tuần 0 → 2026-11-15)** | Tiến độ theo sprint: §0.2 · kế hoạch Sprint 2–3: [`docs/designs/giai-doan-1-wedge-truoc-mcu-sau.md`](docs/designs/giai-doan-1-wedge-truoc-mcu-sau.md) |
| **Sprint hiện hành** | 🟡 **Sprint 2: Lõi thực thi trên `sim` (≈ A1)** — mã A1 xong sớm, 2026-09-23 | **9 / 10 task trong phạm vi xong** (còn TSK-S2-11, chạy ở A2; TSK-S2-09 kéo lên và xong) · **5 / 6 tiêu chí ra đạt** (còn #6, cùng TSK-S2-11) · Sprint 1 còn TSK-S1-10 chờ bo mạch |
| **Cột mốc tiếp theo** | **M1: Time-to-first-value < 10 phút trên `sim`** | Hạn chót: cuối Sprint 3 = **2026-11-15** — trễ ~2 tuần so với bản gốc (Tuần 6 gốc = 2026-11-02) (Q-19) |
| **Lần cập nhật cuối** | **2026-09-23** | TSK-S3-17 (wheel tự chạy được, CI `wheel-smoke`); Q-21, Q-23 chốt; kéo firmware không cần bo mạch lên A2 — chi tiết `CHANGELOG.md` `[Chưa phát hành]` |
| **Trạng thái CI Lõi** | ✅ **PASS 614/614 · SKIP 0** | `python/tests/` — 33 bộ test; wheel đã cài chạy cả hành trình (job `wheel-smoke`); cổng CI chặn mọi test bị skip · `tests_linux/` 8/8 trên gpio-sim (job `linux-hal`) |
| **Chặn ngoài tầm kỹ thuật** | 🟡 **1 hạng mục chặn + 1 còn mở** | 🔴 TSK-S1-10 chờ bo mạch vật lý · 🟡 Q-11 phần còn lại (Hawkbit EPL-2.0 / EMQX BSL) — **không chặn cho tới khi mở Khối 2** |
| **Hoãn có chủ ý** | 📋 [`TODOS.md`](TODOS.md) | Mỗi mục kèm mốc kích hoạt · gồm câu hỏi kinh doanh mở rà lại tại cổng nhu cầu **2026-10-25** (Q-20) |

---

### 0.2 Bảng tổng quan tiến độ các Sprint (Sprint Matrix Overview)

| Mốc | Sprint / Giai đoạn | Thời gian | Trọng tâm kỹ thuật | Tiến độ | Trạng thái |
|:---:|:---|:---:|:---|:---:|:---:|
| **Khối 1a** | **Sprint 1 — Đóng băng lược đồ** | Tuần 0–2<br>2026-09-21 → 2026-09-27 | Schemas, Monorepo, Test fixtures, Memory spike | **12 / 13** | 🟡 **Chờ phần cứng** (chỉ TSK-S1-10) |
| | **Sprint 2 — Lõi thực thi trên `sim`** *(≈ A1, wedge `sim`)* | **2026-09-28 → 2026-10-25** (Q-19) | Gate Engine, cây quyết định host, HAL sim, fail-closed + fallback ngữ pháp lệnh (Q-14), `@action` + token, kế thừa `budget`/`on_block` (Q-18) | **9 / 10** | 🟡 Mã A1 + web UI `sim` xong 2026-09-23; còn TSK-S2-11 (A2) |
| | **Sprint 3 — Action CI & Linux** *(≈ A2)* | **2026-10-26 → 2026-11-15** (Q-19) | HAL linux (`gpio-sim`, Q-16), Record/Replay/Assert/Golden, lớp provider LiteLLM, release PyPI, TTFV < 10' | **12 / 17** | 🟡 Action CI + HAL `linux` xong (2026-09-23); tiêu chí ra 5/6 |
| **Khối 1b** | **Sprint 4 — HAL trên `esp32s3`** | **Từ 2026-11-16** (Q-19) · gốc Tuần 6–8 | Port driver XiaoZhi, verify target bậc 1 không audio, ghim `extends` (RFC-0003) | **0%** | ⏳ Chưa bắt đầu |
| | **Sprint 5 — Runtime thoại MCU** | Tuần 8–10 | Thu/phát âm thanh, AEC/VAD, C/C++ state machine, stream lên provider | **0%** | ⏳ Chưa bắt đầu |
| | **Sprint 6 — OTA & Nghiệm thu v1.0** | Tuần 10–12 | A/B OTA, secure boot, tiêu chí A1–A9 | **0%** | ⏳ Chưa bắt đầu |
| **Beta** | **Developer Beta** | Tuần 12–16 | Hỗ trợ 50–100 lập trình viên, chỉ số B1–B5 | **0%** | ⏳ Chưa bắt đầu |
| **Khối 2** | **Fleet OS** *(dịch vụ thương mại duy nhất)* | Tháng 4–8 | Hawkbit Canary OTA, EMQX Broker, Provisioning | **0%** | ⏳ Chờ mốc Beta |
| **Khối 3** | **Bảy đường ray nền tảng** | Tháng 4–8 | OCI/ORAS Registry, OpenMeter usage billing | **0%** | ⏳ Chờ mốc Beta |

**Lịch theo ngày tuyệt đối (Q-19).** Sprint 2 và 3 ghi bằng ngày, thay cho quy ước cũ *"Tuần N ở kế hoạch = Tuần N+1 roadmap"* (đã bỏ). M1 trễ **~2 tuần** so với roadmap gốc (Tuần 6 gốc = 2026-11-02), và **Khối 1b cùng mọi mốc sau nó (Sprint 5, Sprint 6, Beta, Điểm rẽ Tuần 16) lùi tương ứng**; cột "Thời gian" của các dòng đó vẫn ghi tuần của lịch gốc cho tới khi ngày tuyệt đối được chốt lúc mở Sprint 4. Ước lượng V1 ~6,6–7,1 tuần-người trong 7 tuần — sát, không có đệm lớn.

---

### 0.3 Thẻ Bàn giao Hiện tại (Active Session Handoff Card)

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ THẺ BÀN GIAO PHIÊN LÀM VIỆC (LIVING HANDOFF CARD)                 Cập nhật: 2026-09-23 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. VỪA HOÀN THÀNH — phiên gần nhất (chi tiết: CHANGELOG.md [Chưa phát hành])           │
│    • TSK-S3-17 ✅ wheel tự chạy được; CI wheel-smoke kiểm bản đã cài                    │
│    • Q-21, Q-23 chốt; firmware không cần bo mạch kéo lên A2 (§4.3)                     │
│                                                                                        │
│ 2. ĐANG THỰC HIỆN                                                                      │
│    • TSK-S1-10 (V2) — chờ bo mạch; đo thêm MultiNet (+ WakeNet) theo Q-14              │
│                                                                                        │
│ 3. VIỆC TIẾP THEO — đúng thứ tự                                                        │
│    1. Đặt 2 Box-3 + 1 RPi 5 nightly (Phụ lục B, Q-16)                                  │
│    2. V3: TSK-S3-14 (PyPI, TestPyPI trước) · S3-16 · S3-19 · S3-20 → đo TTFV           │
│    3. A2 V2: TSK-S4-02 + S4-07 (walker C, Q-23) → S4-08, S4-09 (QEMU) · S4-11          │
│    4. A2 V1: TSK-S2-11 (LiteLLM) → TSK-S2-07 (đặc tả FSM thoại)                        │
│    5. Kỹ thuật trưởng xác nhận TSK-S3-15 (golden = vết ghi chuẩn mực)                  │
│                                                                                        │
│ 4. LƯU Ý — bất biến ở CHANGELOG.md §3.3; dưới đây chỉ điều chưa có ở đó                │
│    • Chỉ c.do() điều khiển được chân: HAL chưa gắn ledger từ chối mọi lệnh             │
│    • Replay tính lại phán quyết từ dữ kiện đã ghi; golden chỉ so quyết định            │
│    • Wheel mang asset ở neuroedge/_data/; paths.py: checkout → gói → lỗi               │
│    • tests_linux/ chỉ chạy trên gpio-sim (job linux-hal); gpiod là extra [linux]       │
│    • Chạy ruff check + ruff format --check trước khi commit (CI chặn)                  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 0.4 Quy ước Cập nhật & Bàn giao (Handoff Protocol)

Khi xong một task: làm theo [`CONTRIBUTING.md` §8](CONTRIBUTING.md#8-hoàn-thành-một-task--cập-nhật-tài-liệu-tiến-độ-changelog) —
nơi duy nhất định nghĩa việc cập nhật trạng thái task, tiêu chí ra, §0.1–§0.3 và changelog.

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

**Phụ thuộc mới từ CR-1.0:** lớp trừu tượng provider (TSK-S2-11) là điều kiện tiên quyết cho ASR/TTS qua cloud (TSK-S3-13, nay hoãn sang Sprint 5) và cho vòng lặp thoại ở Sprint 5 (TSK-S5-06). Nó **không** nằm trên đường găng của mắt xích 2 và 3 nên làm song song được, chạy trong A2 và **hạn 2026-11-15** (Q-19; thay cho "trước Tuần 6"). Q-11 phần LiteLLM đã duyệt 2026-09-23 nên TSK-S2-11 không còn bị chặn.

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
| LiteLLM | MIT với phần enterprise riêng | Chỉ dùng phần MIT; middleware xác thực thiết bị viết riêng. **✅ Đã duyệt 2026-09-23** (Q-11): `litellm==1.102.0`, wheel không chứa `enterprise/`; dùng như SDK qua extra `neuroedge[cloud]` (Q-10) |

### 3.4 Ma trận tích hợp theo khối

| Khối | Hạng mục kỹ thuật | Dự án tái sử dụng | Hình thức | Tiết kiệm |
|:---|:---|:---|:---|:---:|
| **1a** | CLI `new` / `run` / `test` | Typer · Rich · generator mẫu Python (không Copier — TSK-S3-07) | Thư viện Python | 2 tuần |
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

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> LISTENING: wake-word hoặc VAD kích hoạt
    LISTENING --> THINKING: kết thúc câu (khoảng lặng)
    THINKING --> SPEAKING: token đầu tiên
    SPEAKING --> IDLE: phát xong
    SPEAKING --> BARGE_IN: phát hiện người dùng nói
    BARGE_IN --> LISTENING: thu câu nói mới
    note right of BARGE_IN
        1. xả đệm DAC
        2. huỷ actuator đang chờ
        3. ghi sự kiện
    end note
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
| **TSK-S1-10** | **Spike khả thi bộ nhớ trên ESP32-S3-Box-3** | NFR-RES-01, NFR-RES-02 | V2 | 🔴 **Chờ bo mạch** | Khung đo xong: [`memory_probe.c`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/targets/esp32s3/main/memory_probe.c) (4 checkpoint, dòng JSON máy đọc), [`check_firmware_size.py`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/scripts/check_firmware_size.py) · **chưa có số đo thực** → [báo cáo](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/reports/memory_spike_report.md) · danh sách đo **thêm ESP-SR MultiNet** (và WakeNet nếu cân nhắc thay microWakeWord của Q-7) theo **Q-14** |
| **TSK-S1-11** | Rà soát thiết kế HAL dưới ràng buộc MCU | — | V2 | ✅ Hoàn thành | [`docs/spec/hal_mcu_review.md`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/spec/hal_mcu_review.md) (5 kết luận + 4 ràng buộc cho Sprint 4) · hiện thực tại [`hal/board.py`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/python/neuroedge/hal/board.py) + [`boards/`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/boards/) 3 target |
| **TSK-S1-12** | Hai workflow CI: `ci-sim-linux.yml` và `nightly-hardware.yml` | FR-CI-05, FR-CI-06 | V1 | ✅ Hoàn thành | [`ci-sim-linux.yml`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/.github/workflows/ci-sim-linux.yml) (lược đồ · phân giải gate · vết ghi · test 3 bản Python · lint · cổng giấy phép · **cổng chặn test skip**) · [`nightly-hardware.yml`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/.github/workflows/nightly-hardware.yml) (dựng IDF · ngân sách flash Q-3 · thu số đo · trôi phụ thuộc) |
| **TSK-S1-13** | Quy ước đóng góp và mẫu RFC đổi lược đồ | — | V1 | ✅ Hoàn thành | [`CONTRIBUTING.md`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/CONTRIBUTING.md) (7 mục) · [`docs/rfc/`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/rfc/): [quy trình](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/rfc/README.md), [mẫu](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/rfc/0000-template.md), [RFC-0001](file:///Users/minhlt/Downloads/Projects/neuroedge-init/docs/rfc/0001-gate-schema-conditional-requirements.md) |

**Đòn bẩy OSS Sprint 1:** Pydantic v2 và `rfc8785` cho chuẩn hóa lược đồ · Typer, Rich cho khung CLI ban đầu (Copier dùng lúc dựng khung, bỏ hẳn ở TSK-S3-07 vì GPL3 bắc cầu). Tiết kiệm ước tính 3 tuần công sức viết mã.

**Nội dung spike bộ nhớ:** nạp thử AEC + VAD + Opus streaming **+ ESP-SR MultiNet** (bộ nhận diện lệnh cố định làm fallback cục bộ, Q-14; thêm WakeNet nếu cân nhắc thay microWakeWord) lên ESP32-S3-Box-3, đo dung lượng SRAM và PSRAM còn lại sau khi trừ ngăn xếp mạng và hệ điều hành. Kết quả là **một con số**, không phải một nhận định.

Ngưỡng đối chiếu đã chốt tại Q-3: **SRAM cho ứng dụng ≥ 120 KB · PSRAM ≥ 2 MB · firmware ≤ 3,5 MB**. Không đạt ngưỡng nào thì kích hoạt bậc 5 của thang cắt phạm vi (§9) ngay, không chờ Tuần 9.

**Tiêu chí ra Sprint 1 (Exit Criteria):** — **5 / 6 đạt · 1 bị chặn bởi phần cứng**

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
- [x] **Tiêu chí 6:** Quyết định Q-11 đã chốt (§10.2) — điều kiện để bắt đầu port bất kỳ dòng mã nào.
  **ĐẠT cho phạm vi Giai đoạn 1 (2026-09-23).** Phần LiteLLM của Q-11 đã duyệt: `litellm==1.102.0` là MIT, wheel không chứa `enterprise/`, 55 phụ thuộc bắc cầu đều MIT/BSD/Apache-2.0/PSF + MPL-2.0; kèm chính sách phụ thuộc bắc cầu cưỡng chế bằng CI (làm cùng TSK-S2-11). **Phần Hawkbit EPL-2.0 / EMQX BSL chuyển thành cổng mở Khối 2** ([`TODOS.md`](TODOS.md) #16) — chưa có dòng mã nào của chúng được port; phần D của [`NOTICE`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/NOTICE) ghi rõ phạm vi phơi nhiễm. Phát hiện phát sinh trong Sprint 1: `copier` kéo theo `jinja2-ansible-filters` **GPL3** — đã chuyển sang extra `scaffold` để lõi MIT không bị lây nhiễm, và cổng CI giấy phép chặn tái diễn; TSK-S3-07 thay `copier` bằng generator Python thuần và bỏ hẳn extra đó.

**Ghi chú về phạm vi đã đóng:** toàn bộ khối lượng Sprint 1 **không phụ thuộc phần cứng** đã hoàn tất (12/13 task, 5/6 tiêu chí ra). Hạng mục còn lại (TSK-S1-10, Tiêu chí 3) không thể đóng bằng nỗ lực kỹ thuật thêm nữa — nó chờ bo mạch.


### 4.2 Sprint 2 — Lõi thực thi trên `sim` (≈ A1 · 2026-09-28 → 2026-10-25, Q-19)

Phạm vi và thứ tự chạy theo kế hoạch [`docs/designs/giai-doan-1-wedge-truoc-mcu-sau.md`](docs/designs/giai-doan-1-wedge-truoc-mcu-sau.md) (wedge `sim`). **Thứ tự bắt buộc:** TSK-S2-03 → S2-08 → S2-01 → S2-04 → S2-05 → S2-02; TSK-S2-12 và S2-13 chạy kèm. Việc hoãn ghi `⏸ Hoãn` kèm lý do và đích đến; mốc kích hoạt ở [`TODOS.md`](TODOS.md).

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S2-01** | Hiện thực HAL cho target `sim` | FR-TGT-01, FR-HAL-01 | **V2** *(ENG-T3)* | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/hal/sim.py` · `tests/test_hal_sim.py` |
| **TSK-S2-02** | Đối chiếu năng lực lúc build, thông báo lỗi đầy đủ 3 thành phần | FR-HAL-04, FR-HAL-05, FR-DX-04 | V1 | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/engine/compiler.py` · lệnh `neuroedge build` · agent mẫu `fixtures/agents/villa-concierge/` · `tests/test_compiler.py` |
| **TSK-S2-03** | Gate Engine: `evaluate`, `allow_when`, `on_block`, `budget`. `on_block` v1.0 theo **Q-17**: mọi hành vi đều chặn hành động vật lý; `escalate`/`ask` ghi sự kiện + gọi hook (mặc định no-op); `degrade` chạy `fallback_action` qua gate của chính nó. ✅ khi xong phạm vi đã đặc tả | FR-GATE-03, FR-GATE-04, FR-GATE-09 | V1 | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/engine/gate.py` · `engine/trace_sink.py` (`EventLog`) · `tests/test_gate_engine.py` |
| **TSK-S2-04** | Cơ chế fail-closed và mạch ngắt suy giảm | FR-ACE-03, NFR-REL-02 | V1 | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/engine/circuit_breaker.py` · `tests/test_fail_closed.py` |
| **TSK-S2-05** | Decorator `@action`, cấm gọi trực tiếp, `c.do()` và `c.say()`, **token phán quyết dùng một lần** | FR-ACE-02, FR-ACE-04, FR-ACE-05, FR-ACE-07 | V1 | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/actions/` (`spec.py`, `conversation.py`, `token.py`) · `python/neuroedge/hal/digital.py` · `docs/spec/threat_model.md` · `tests/test_actions.py` |
| **TSK-S2-06** | Lượng giá `allow_when` trên nền Google CEL, kèm đường biên dịch gate cho thiết bị (§3.8, Q-9) | FR-GATE-03 | V1 | ⏸ **Hoãn → Sprint 5** | Dạng mapping đủ cho wedge; CEL là front-end biên dịch xuống *cùng* cây quyết định của TSK-S2-12 (Q-9 phương án A) |
| **TSK-S2-07** | **Đặc tả chuẩn tắc máy trạng thái hội thoại** — nguồn sự thật cho cả hai hiện thực (§3.8) | FR-PER-02, FR-PER-03 | V1 | ⏳ **Kéo lên A2 (V1)** — sau TSK-S2-11 | Hoãn **cùng** TSK-S3-10, S3-11 để giữ thứ tự §3.10: nằm trên đường găng Sprint 2 nhưng không trên đường găng wedge — wedge không chạm âm thanh. Phải xong trước TSK-S5-03 |
| **TSK-S2-08** | Interface `SystemOne` / `SystemTwo` + trường độ tin cậy + test double tất định + **fallback cục bộ = bộ nhận diện lệnh cố định** (ngữ pháp lệnh → intent + độ tin cậy) chạy trên chữ gõ ở `sim` (**Q-14**, Q-15). Connector cloud thật đi cùng TSK-S2-11. Q-17: ✅ khi xong phạm vi đã đặc tả | FR-MDL-01, FR-MDL-02, FR-MDL-03, FR-ACE-03 | V1 | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/models/` (`system.py`, `grammar.py`, `doubles.py`) · ngữ pháp mẫu `fixtures/agents/villa-concierge/commands.toml` · `tests/test_models.py` |
| **TSK-S2-09** | Giao diện web `sim`: cảm biến ảo, trạng thái actuator — `neuroedge run --ui` | FR-TGT-06 | V3 | ✅ Hoàn thành (2026-09-23) | [`sim/ui.py`](python/neuroedge/sim/ui.py) — `run --ui`: trang cục bộ 127.0.0.1, SSE, không mạng, từ chối POST khác nguồn; commit `8a023f3` · `pytest tests/test_sim_ui.py` |
| **TSK-S2-10** | Kết luận phạm vi Khối 1b dựa trên spike | — | V2 + trưởng nhóm | ⏸ **Hoãn → Sprint 5** *(hoặc sớm hơn khi bo mạch về)* | Chặn bởi bo mạch (TSK-S1-10). `docs/reports/memory_spike_report.md` |
| **TSK-S2-11** | **Lớp trừu tượng nhà cung cấp**: hợp đồng kết nối OpenAI-compatible + adapter tùy chỉnh, áp dụng chung cho LLM/ASR/TTS (CR-1.0). **LiteLLM làm thư viện định tuyến (SDK)** sau `neuroedge.models.providers`, cài qua extra **`neuroedge[cloud]`** (Q-10) · **bước kiểm giấy phép phụ thuộc bắc cầu trong CI** (Q-11). **Không còn bị chặn** — chạy trong A2, hạn **2026-11-15** (Q-19) | FR-MDL-07, FR-MDL-08, FR-GW-01, FR-GW-03 | V1 | ⏳ Chưa bắt đầu *(A2)* | `python/neuroedge/models/providers/` · `python/pyproject.toml` (extra `cloud`) · `.github/workflows/ci-sim-linux.yml` (job giấy phép) |
| **TSK-S2-12** | **Đặc tả ngữ nghĩa quyết định:** trình biên dịch phía host `import parse_constraint` (không sửa `constraints.py`, không RFC) → cây quyết định mang `criteria_order` + `gate_digest`; `evaluate()` đi cây, trả phán quyết + `reason`. **Định dạng nội bộ, chưa đóng băng** — đóng băng ở RFC-0003 (Sprint 4) | FR-GATE-03, FR-ACE-01, FR-TGT-04 | V1 | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/engine/decision_tree.py` · `decision_tree.v1.json` (nội bộ) · bảng sự thật `fixtures/decision_trees/*.truth.json` (sinh bằng `scripts/generate_truth_tables.py`) · `tests/test_decision_tree.py` |
| **TSK-S2-13** | **Kế thừa `budget`/`on_block`** (RFC-0004, **Q-18**): `p95_latency_ms` của con ≤ cha · chuỗi đã `closed` thì con không khai `fail: open` · con không tự đưa vào `degrade`/`fallback_action` mới. Vi phạm ⇒ `GateInheritanceError`. Đóng lỗ `lax-night` (ENG-A2) | FR-GATE-06, FR-GATE-07, FR-GATE-09 | V1 | ✅ Hoàn thành (2026-09-23) | `python/neuroedge/engine/gate_resolver.py` · 4 fixture phản chứng tại `fixtures/gates/invalid/` + `expected_errors.yaml` · 10 test `test_rfc0004_*` · commit `87890c8` |

**Tiêu chí ra Sprint 2 (Exit Criteria):** — **5 / 6 đã đạt** *(còn #6, đóng cùng TSK-S2-11 trong A2)*

- [x] **Tiêu chí 1:** Agent mẫu chạy trên `sim`, gate chặn đúng theo `allow_when`.
  *Bằng chứng:* `pytest tests/test_compiler.py -k sample_agent_runs` — agent `fixtures/agents/villa-concierge/` qua `c.do()` trên `SimHAL`: ALLOW ⇒ `door_lock` kích 30 000 ms, `risk_level: high` ⇒ `never_pulsed()`.
- [x] **Tiêu chí 2:** Gọi trực tiếp hành động vật lý ném `ActionContractViolation`, chân GPIO ảo không kích.
  *Bằng chứng:* `pytest tests/test_actions.py -k direct` — `test_a_direct_call_is_a_contract_violation_naming_the_caller` (NE1001 nêu `file:line` nơi gọi, `never_pulsed()`).
- [x] **Tiêu chí 3 (Q-14):** Kịch bản mất mạng → gate **vẫn lượng giá** bằng bộ nhận diện lệnh cố định cục bộ; câu không khớp ngữ pháp hoặc độ tin cậy dưới ngưỡng → BLOCK theo tiêu chí bình thường; fallback không có / không chạy được → hành động bị chặn với lý do `gate_unreachable`.
  *Bằng chứng:* `pytest tests/test_models.py -k offline` — `test_offline_a_known_command_is_still_adjudicated`, `test_offline_an_unknown_command_blocks_by_normal_criteria`, `test_offline_without_a_fallback_is_gate_unreachable`, `test_a_fallback_that_fails_at_run_time_is_gate_unreachable`; chạy khi socket bị chặn (`test_the_offline_path_opens_no_socket`).
- [x] **Tiêu chí 4:** Gate con nới lỏng `allow_when` bị từ chối phân giải.
  *Bằng chứng (ĐÃ ĐÓNG ở Sprint 1):* [`test_gate_resolver.py`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/python/tests/test_gate_resolver.py) + 4 fixture nới `allow_when` (`loosens_choice`, `loosens_confidence`, `loosens_level`, `loosens_via_not_in`) tại [`fixtures/gates/invalid/`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/fixtures/gates/invalid/).
- [x] **Tiêu chí 5:** Quyết định Q-3, Q-7 đã chốt.
  *Bằng chứng (ĐÃ THOẢ SẴN):* Q-3 và Q-7 tại §10.1 của tài liệu này và `neuroedge-prd.md` §15.
- [ ] **Tiêu chí 6:** Đổi nhà cung cấp mô hình chỉ bằng thay đổi cấu hình, không sửa mã agent và không sửa gate; một adapter tùy chỉnh mẫu chạy được mà không sửa lõi. **Nay đạt được** — Q-11 phần LiteLLM đã duyệt 2026-09-23, TSK-S2-11 hết bị chặn; đóng trong A2, hạn 2026-11-15 (Q-19).


### 4.3 Sprint 3 — Action CI, `linux` và TTFV (≈ A2 · 2026-10-26 → 2026-11-15, Q-19)

**Điều kiện mở A2:** thí nghiệm `gpio-sim` 2 giờ trên runner GitHub Ubuntu đã chạy (Q-16). V3 chạy từ **2026-10-05 → 2026-11-15**, song song A1 và A2.

**Kéo lên A2 (kế hoạch lấp khoảng trống kỹ thuật, 2026-09-23):** V2 chờ bo mạch nên làm phần firmware **không cần bo mạch** trong A2 — TSK-S4-02 (walker C, Q-23), S4-07 (walker trên host, mỗi PR), S4-08 (QEMU), S4-09 (vết ghi qua UART), S4-11 (ngân sách RAM tĩnh). V1 làm TSK-S2-07 (đặc tả FSM thoại) ngay sau TSK-S2-11, để Sprint 5 mở với đặc tả sẵn. Phần cần phần cứng thật ở lại Sprint 4: TSK-S4-01, S4-03, S4-05, S4-12.

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S3-01** | Record: ghi phiên ra tệp JSON hợp lệ | FR-CI-01 | V1 | ✅ Hoàn thành (2026-09-23) | [`testing/recorder.py`](python/neuroedge/testing/recorder.py) · `neuroedge record`; commit `f4f104e`, PR #13 |
| **TSK-S3-02** | Replay trên target bất kỳ | FR-CI-02 | V1 | ✅ Hoàn thành (2026-09-23) | [`testing/player.py`](python/neuroedge/testing/player.py) · `neuroedge replay` thực thi; commit `38a5db5`, PR #13 |
| **TSK-S3-03** | Thư viện assert: chặn, gate nào, leo thang, chân cấm kích | FR-CI-03 | V1 | ✅ Hoàn thành (2026-09-23) | [`testing/assertions.py`](python/neuroedge/testing/assertions.py) · `neuroedge test`; commit `89b5bd4`, PR #13 |
| **TSK-S3-04** | Golden Reference và so khớp chuỗi phán quyết | FR-CI-04 | V1 | ✅ Hoàn thành (2026-09-23) | [`testing/golden.py`](python/neuroedge/testing/golden.py) — so quyết định, bỏ qua timing; commit `cb4fe26`, PR #13 |
| **TSK-S3-05** | Hiện thực HAL cho target `linux` qua `gpiod`; CI dùng **`gpio-sim`** (kernel ≥ 5.19, configfs), **1 RPi 5** làm nightly phần cứng và phương án B; **ném lỗi** khi không có `/dev/gpiochip*`, không no-op (Q-16) | FR-TGT-02 | **V2** *(ENG-T3)* | ✅ Hoàn thành (2026-09-23) | [`hal/linux.py`](python/neuroedge/hal/linux.py) · [`scripts/setup_gpio_sim.sh`](scripts/setup_gpio_sim.sh) · job CI `linux-hal` (gpio-sim trên runner GitHub, kernel 6.17 azure + `linux-modules-extra`); PR #13 |
| **TSK-S3-06** | Vỏ CLI + `--help` + **hợp đồng mã thoát** cho `new`, `run`, `build`, `test`, `record`, `replay`, `trace validate`; nối engine theo từng tuần khi A1/A2 xong | FR-CLI-01→04, FR-CLI-06, FR-TRC-08 | V3 | ✅ Hoàn thành (2026-09-23) | Cả 7 lệnh có engine: `run` (commit `190b241`), `record` / `replay` / `test` (PR #13). Phiên tương tác trên `linux` chưa có — `run --target linux` thoát mã 2, `replay --target linux` chạy được |
| **TSK-S3-07** | Scaffold `neuroedge new` có sẵn action, gate, test — **không dùng `copier`** (tránh GPL3 `jinja2-ansible-filters`) | FR-DX-01 | V3 | ✅ Hoàn thành (2026-09-23) | [`python/neuroedge/templates/`](python/neuroedge/templates/) — mẫu `minimal`, `villa-concierge`; commit `e03e206` · `pytest tests/test_cli_new.py` |
| **TSK-S3-08** | Ba ví dụ mẫu chạy được, README có tài sản trực quan | FR-DX-05, FR-DX-06 | V3 | 🟡 **2 / 3 mẫu** (2026-09-23) | `villa-concierge` và `home-voice` ([`fixtures/agents/home-voice/`](fixtures/agents/home-voice/): RAG knowledge base, tin tức, đèn qua gate) chạy được qua `neuroedge new --template`, có test và nằm trong `wheel-smoke`. Còn: mẫu giám sát môi trường công nghiệp, tài sản trực quan cho README (Sprint 5) |
| **TSK-S3-09** | Telemetry CLI ẩn danh, có thể tắt | FR-TEL-01, FR-TEL-02 | V3 | ⏸ **Hoãn → Sprint 5** | Không đo wedge; cần trước Beta (B1–B5) |
| **TSK-S3-10** | **Bộ vector kiểm thử tuân thủ độc lập ngôn ngữ** cho máy trạng thái hội thoại (§3.8) | FR-CI-07, FR-TGT-04 | V1 | ⏸ **Hoãn → Sprint 5** | Hoãn cùng TSK-S2-07 (thứ tự §3.10); phải có trước TSK-S5-03 |
| **TSK-S3-11** | Hiện thực Python của máy trạng thái hội thoại, port thiết kế từ Pipecat | FR-PER-02→05 | V1 | ⏸ **Hoãn → Sprint 5** | Hoãn cùng TSK-S2-07; wedge không chạm âm thanh |
| **TSK-S3-12** | Pipeline CI mẫu chạy `sim` + `linux` trên mỗi PR | FR-CI-05 | V1 | ✅ Hoàn thành (2026-09-23) | [`ci-sim-linux.yml`](.github/workflows/ci-sim-linux.yml): 5 job, 7 lượt chạy; job `linux-hal` dựng gpio-sim, chạy `tests_linux/` và `verify --targets sim,linux`; PR #13 |
| **TSK-S3-13** | **Tích hợp ASR/TTS qua provider cloud** cho `sim` và `linux`, kèm tùy chọn mô hình cục bộ (CR-1.0) | FR-MDL-09, FR-PER-07 | V1 | ⏸ **Hoãn → Sprint 5** | Wedge `sim` gõ chữ không cần (Q-15); làm cùng TSK-S5-06, xem §5.2. Âm thanh `linux` là TSK-S5-08 |
| **TSK-S3-14** | **Workflow release lên PyPI**; nghiệm thu `pip install neuroedge==<tag>` rồi **chạy** `gate lint` + `trace validate` từ bản cài | FR-DX-02, FR-GOV-01 | V3 | ⏳ Chưa bắt đầu | `.github/workflows/release-pypi.yml` |
| **TSK-S3-15** | **RFC golden reference:** ba vết ghi chuẩn mực khai `"target": "esp32s3"` nhưng replay ở Tiêu chí 4 chạy trên `sim`/`linux` thật; `fixtures/traces/` là RFC-gated | FR-CI-04, FR-TRC-05 | V1 | 🟡 **Chờ kỹ thuật trưởng** | TSK-S3-04 so **quyết định**, không so `metadata.target`: ba vết ghi chuẩn mực làm golden nguyên trạng trên `sim` và `linux`, không sửa `fixtures/traces/`. Nếu kỹ thuật trưởng đồng ý thì RFC không còn cần — đóng task |
| **TSK-S3-16** | **Cổng CI `digests.lock`:** khoá digest của `gates/**` + `fixtures/gates/valid/**` + `fixtures/gates/registry/**`; phân biệt *digest mới* với *digest đổi* (cần RFC) | FR-GATE-01, FR-GOV-02, FR-CI-05 | **V3** *(ENG-T3)* | ⏳ Chưa bắt đầu | `digests.lock` · `.github/workflows/ci-sim-linux.yml` |
| **TSK-S3-17** | **Đóng gói asset vào wheel:** lược đồ, bo mạch, gate, vết ghi chuẩn mực, agent mẫu; `paths.py` đọc từ gói; `repo_root()` ném lỗi 3 thành phần nêu `NEUROEDGE_ROOT`. *Mở rộng 2026-09-23: đo được wheel cài từ pip gãy ở `build`/`run`/`test`* | FR-DX-02, FR-DX-04 | **V3** *(ENG-T3)* | ✅ Hoàn thành (2026-09-23) | [`python/hatch_build.py`](python/hatch_build.py) — wheel mang `schemas/`, `boards/`, `gates/`, `fixtures/traces/`, `fixtures/agents/` trong `neuroedge/_data/` (cả khi build từ sdist); [`paths.py`](python/neuroedge/paths.py) báo lỗi 3 thành phần thay vì đoán; job CI `wheel-smoke` chạy cả hành trình trên bản đã cài ([`scripts/wheel_smoke.sh`](scripts/wheel_smoke.sh)); commit `6e2d5f9` |
| **TSK-S3-18** | **`neuroedge gate explain`:** giải thích gate đã phân giải cho người duyệt không đọc mã (J6) | FR-GATE-01, FR-CLI-05 | **V3** *(ENG-T3)* | ✅ Hoàn thành (2026-09-23) | [`engine/gate_explain.py`](python/neuroedge/engine/gate_explain.py) + [`cli/explain.py`](python/neuroedge/cli/explain.py); commit `d80964e` · `pytest tests/test_cli_explain.py` |
| **TSK-S3-19** | **`verify` đếm artifact, ném khi = 0** (lỗi 3 thành phần) + test phản chứng cây rỗng | FR-CI-07, FR-CLI-06, FR-DX-04 | **V3** *(ENG-T3)* | ⏳ Chưa bắt đầu | `python/neuroedge/cli/` · `python/tests/` |
| **TSK-S3-20** | **`README.md` gốc** một màn hình, thành trang PyPI; liên kết tuyệt đối, không hướng dẫn cài editable | FR-DX-02, FR-DX-05 | **V3** *(ENG-T3)* | ⏳ Chưa bắt đầu | `README.md` |
| **TSK-S3-21** | **Ghim `extends` bằng digest** (`@<ver>#sha256:…`) + `digests.lock` thành lock của `extends` + kiểm danh tính `URI ↔ name/version` | FR-GATE-05, FR-GATE-06 | V1 | ⏸ **Hoãn → Sprint 4** | Cần RFC-0003 (đổi `pattern` của `gate.v1.json`, đóng băng `decision_tree.v1.json`); chỉ cần khi firmware C đọc cây hoặc có registry ([`TODOS.md`](TODOS.md) #15) |
| **TSK-S3-22** | **`neuroedge trace view`** — một tệp HTML tĩnh: dòng thời gian, phán quyết + lý do, chân, cảm biến, khung màn hình; mở không cần mạng. Kèm `trace export --format chrome` cho Perfetto *(Q-21)* | FR-CLI-04, FR-DX-04 | V3 | ✅ Hoàn thành (2026-09-23) | [`viz/`](python/neuroedge/viz/) — `trace view` (HTML tự chứa, thanh tua thời gian), `trace export --format chrome`; commit `650a517` · `pytest tests/test_trace_view.py` |
| **TSK-S3-23** | **`sensor.read` và `display` trên `sim` đủ đường:** `[sim.sensors]` trong `agent.toml`, `:sensor` trong REPL, sự kiện `sensor_read` / `display_frame` (digest + PNG), replay cấp lại giá trị cảm biến đã ghi *(Q-21)* | FR-TGT-01, FR-TGT-06, FR-CI-02 | V3 | ✅ Hoàn thành (2026-09-23) | `hal/sim.py`, `hal/sensor.py`, `hal/display.py`, `sim/session.py`; commit `b3c118e` · `pytest tests/test_sim_sensors_display.py` |

**Tiêu chí ra Sprint 3 — cổng kết thúc Khối 1a (Exit Criteria):** — **5 / 6 đã đạt**

- [ ] **Tiêu chí 1 (A1):** TTFV đo thử nội bộ trên **3 người ngoài đội** đạt trung vị dưới 10 phút *(đo đầy đủ ở Tuần 12)*. Scaffold TSK-S3-07 đã có (2026-09-23); còn cần TSK-S3-14 publish, rồi mới có thời gian đo.
- [x] **Tiêu chí 2 (A2):** `neuroedge verify --targets sim,linux` đạt 100%.
  *Bằng chứng:* job CI `linux-hal` (PR #13) — ba vết ghi chuẩn mực replay trên `SimHAL` và `LinuxHAL` (gpio-sim) cho cùng phán quyết (ALLOW · BLOCK · BLOCK) và cùng lệnh chân, khớp golden; `tests_linux/test_gpio_sim.py` 8/8. So quyết định, chưa so timing (TSK-S4-04).
- [x] **Tiêu chí 3 (A3):** Không tồn tại đường tắt kích hoạt GPIO bỏ qua gate.
  *Bằng chứng:* `docs/spec/threat_model.md` §2 liệt kê mọi đường tắt và test chặn nó — `test_no_path_reaches_a_pin_without_a_valid_token`, `test_a_hal_without_a_ledger_refuses_every_command`, các test `token_replayed` / `token_expired` trong `tests/test_actions.py`.
- [x] **Tiêu chí 4 (A4):** 100% kịch bản suy giảm đều chặn hành động.
  *Bằng chứng:* `pytest tests/test_fail_closed.py` — ma trận 8 kịch bản suy giảm × 3 gate mẫu + thiếu độ tin cậy + gate không tồn tại: mọi ô BLOCK và `never_pulsed()`; mất mạng có fallback chạy được thì lượng giá bình thường (Q-14).
- [x] **Tiêu chí 5 (A5):** Bộ kiểm thử kế thừa gate đạt 100%.
  *Bằng chứng (ĐÃ ĐÓNG ở Sprint 1):* 35 test tại [`test_gate_resolver.py`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/python/tests/test_gate_resolver.py) + 26 test tại [`test_sample_gates.py`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/python/tests/test_sample_gates.py); `neuroedge gate lint` → *✓ 3 gate(s) resolved*. TSK-S2-13 mở rộng bộ này cho `budget`/`on_block` (Q-18) và phải giữ 100%.
- [x] **Tiêu chí 6 (A7):** 100% phiên sinh vết ghi qua được `neuroedge trace validate`.
  *Bằng chứng:* mọi đường ghi (`record`, `run --trace-out`, `replay --trace-out`) thẩm định theo `trace.v1` **trước** khi ghi và từ chối ghi tệp sai — `test_a_trace_that_fails_the_schema_is_never_written`; `test_recorder.py`, `test_cli_run.py` đọc lại tệp bằng `load_trace`.


---

## 5. Khối 1b — Vi điều khiển biên (Tuần 6–12)

**Mục tiêu khối:** chứng minh nguyên tắc tương đương môi trường trên vi điều khiển $5, với độ ổn định sản xuất.

### 5.1 Sprint 4 — HAL trên `esp32s3` (Tuần 6–8)

Sprint này **cố tình chưa làm thoại**. Mục đích là chứng minh tương đương target trên miền quyết định trước, khi biến số còn ít.


| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S4-01** | Port 5 nguyên thủy HAL lên ESP-IDF | FR-TGT-03, FR-HAL-01 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/hal/` |
| **TSK-S4-02** | Gate Engine chạy trên MCU: walker C99 duyệt **bố cục nhị phân** do `neuroedge build` sinh (Q-23), token dùng một lần | FR-ACE-01, FR-ACE-03 | V2 + V1 | ⏳ **Kéo lên A2 (V2)** *(2026-10-26 → 11-15)* | `targets/esp32s3/gate/` |
| **TSK-S4-03** | Đường dẫn `digital.out` và `sensor.read` trên phần cứng thật | FR-HAL-06, FR-HAL-07 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/drivers/` |
| **TSK-S4-04** | Lệnh `neuroedge verify` cho cả 3 target bậc 1 | FR-CI-07, FR-TGT-04 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/cli/verify.py` |
| **TSK-S4-05** | Runner kiểm thử nightly trên bo mạch thật | FR-CI-06, NFR-REL-03 | V3 | ⏳ Chưa bắt đầu | `.github/workflows/nightly-hardware.yml` |
| **TSK-S4-07** | **Walker C biên dịch trên host** (gcc) chạy bảng sự thật `fixtures/decision_trees/` trên mỗi PR — kiểm TSK-S4-02 **không cần bo mạch** *(Q-21)* | FR-ACE-01, FR-CI-07 | V2 | ⏳ **Kéo lên A2 (V2)** *(2026-10-26 → 11-15)* | `targets/esp32s3/gate/` · `.github/workflows/ci-sim-linux.yml` |
| **TSK-S4-08** | **Smoke test firmware trên Espressif QEMU** (`idf.py qemu`, ESP-IDF ≥ 5.4): boot, UART, flash/PSRAM, gate walker; hằng đêm. Không phủ I2S, Wi-Fi, LCD SPI, GPIO thường *(Q-21)* | FR-CI-06, FR-TGT-03 | V2 | ⏳ **Kéo lên A2 (V2)** *(2026-10-26 → 11-15)* | `.github/workflows/nightly-hardware.yml` |
| **TSK-S4-09** | **Vết ghi từ firmware qua UART** (JSON-lines, tiền tố `NE1 `) + `neuroedge record --target esp32s3 --port`; chạy cả trên QEMU ⇒ `verify --targets esp32s3` trên miền quyết định trước khi bo mạch về *(Q-21)* | FR-CI-01, FR-TGT-04, FR-CLI-04 | V2 + V1 | ⏳ **Kéo lên A2 (V2)** *(2026-10-26 → 11-15)* | `targets/esp32s3/trace/` · `python/neuroedge/testing/` |
| **TSK-S4-10** | **Ảnh golden cho giao diện LVGL:** cùng mã màn hình của firmware build trên host, `lv_test_display` + `lv_test_screenshot_compare`, mỗi PR *(Q-21)* | FR-HAL-01, FR-CI-05 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/ui/` · `.github/workflows/ci-sim-linux.yml` |
| **TSK-S4-11** | **Ngân sách RAM tĩnh trên mỗi PR:** `idf.py size` của firmware có link ESP-SR AFE; fail khi `.bss`/`.data` làm SRAM còn lại dưới Q-3 (≥ 120 KB). QEMU (có PSRAM) in heap trống lúc boot. Phần áp lực lúc chạy âm thanh vẫn chờ TSK-S1-10 | NFR-RES-01, NFR-RES-02 | V2 | ⏳ **Kéo lên A2 (V2)** *(2026-10-26 → 11-15)* | `scripts/check_firmware_size.py` · `.github/workflows/` |
| **TSK-S4-12** | **Bài kiểm ngày đầu có bo mạch:** codec ES8311/ES7210 port nguyên văn từ XiaoZhi; vòng loa → micro so tín hiệu mẫu, GPIO `door_lock` đo bằng đầu dò; chạy trong ngày Box-3 về | FR-PER-06, FR-HAL-06 | V2 | ⏳ Khi bo mạch về | `targets/esp32s3/tests/bringup/` |


**Đòn bẩy OSS Sprint 4:** ESP-IDF làm toolchain · port driver bo mạch từ XiaoZhi vào `targets/esp32s3/drivers/` (codec I2S ES8311/ES7210, chân I2C/SPI của Box-3, LCD ST7789) · LVGL cho hiển thị trạng thái · gcc trên host và Espressif QEMU để kiểm logic firmware trước khi có bo mạch (TSK-S4-07, S4-08; Q-21). XiaoZhi kéo theo ESP-SR — giấy phép chỉ cho chip Espressif, nên chỉ nằm trong `targets/esp32s3/` (proposal Phụ lục H.1). Tiết kiệm ước tính 7 tuần, trong đó 2–3 tuần nằm trên đường găng.

**Tiêu chí ra Sprint 4 (Exit Criteria):**

- [ ] **Tiêu chí 1 (A2):** `neuroedge verify --targets sim,linux,esp32s3` đạt 100% trên kịch bản **không dùng audio** → **A2 đạt cho miền phán quyết**. Trên QEMU (TSK-S4-09, `device_id = "qemu"`) chạy được trước khi bo mạch về; tiêu chí chỉ đóng khi cũng đạt trên bo mạch.
- [ ] **Tiêu chí 2:** Sai lệch phán quyết giữa các target sinh `SafetyRegressionError` (NE4002) chỉ rõ sự kiện lệch đầu tiên — cơ chế đã có từ TSK-S3-04; tiêu chí đạt khi áp cho `esp32s3`.
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
| **TSK-S5-07** | **Fallback cục bộ trên `esp32s3`** (Q-14): bộ nhận diện lệnh cố định dùng **cùng ngữ pháp lệnh** với `sim` (TSK-S2-08). Backend chọn ở Khối 1b giữa **ESP-SR MultiNet** (lệnh offline, vài chục–vài trăm câu) và **TFLite Micro / ESP-NN** (KWS tự train < 500 KB). **Điều kiện trước Sprint 5:** xác minh giấy phép ESP-SR (theo hiểu biết: chỉ cho dùng trên SoC Espressif), ghi vào `NOTICE`, không lọt vào gói Python ([`TODOS.md`](TODOS.md) #17); giấy phép không hợp ⇒ dùng TFLite Micro / ESP-NN (Apache-2.0). Số đo bộ nhớ lấy từ spike TSK-S1-10 | FR-MDL-03, FR-ACE-03, NFR-RES-01 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/fallback/` |
| **TSK-S5-08** | **`audio.in` / `audio.out` trên `linux`:** `sounddevice` (PortAudio, MIT); AEC phần mềm PipeWire `module-echo-cancel` (Q-22): `audio.in` đọc nút `source` đã khử vang, `audio.out` phát vào nút `sink` của module; cấu hình drop-in `pipewire.conf.d/neuroedge-echo-cancel.conf` giao kèm; `linux-rpi5` khai `aec = true` **chỉ** khi đạt tiêu chí đo `simulation_coverage.md` §6 ⇒ agent mẫu build được cho `linux`. CI: backend tệp/PCM (runner không có `snd-aloop`); Pi: `snd-aloop` + HAT I2S hằng đêm | FR-TGT-02, FR-PER-01 | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/hal/linux.py` · `boards/linux-rpi5.toml` |
| **TSK-S5-09** | **`sensor.read` và `display` trên `linux`:** cảm biến qua sysfs hwmon + IIO; CI dùng `i2c-stub` + `lm75` (IIO chỉ trên Pi); màn hình ghi `/dev/fb*` trên Pi, khung trong bộ nhớ + digest trong CI | FR-TGT-02, FR-HAL-01 | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/hal/linux.py` · `scripts/` |
| **TSK-S3-13** | **Tích hợp ASR/TTS qua provider cloud** cho `sim` và `linux` — **chuyển từ Sprint 3** (wedge `sim` gõ chữ không cần, Q-15), làm cùng TSK-S5-06 | FR-MDL-09, FR-PER-07 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/perception/providers/` |

**Việc hoãn từ Sprint 2–3 đổ về Sprint 5:** TSK-S2-06 (CEL), TSK-S2-07 + TSK-S3-10 + TSK-S3-11 (đặc tả FSM thoại · vector tuân thủ · FSM Python — phải xong **trước** TSK-S5-03), TSK-S2-10 (kết luận phạm vi 1b, sớm hơn nếu bo mạch về), TSK-S3-08 (ví dụ mẫu), TSK-S3-09 (telemetry), TSK-S3-13 (bảng trên). Lý do từng task ở §4.2 và §4.3. Đây là tải thật của Khối 1b — phải tính vào khi chốt ngày tuyệt đối cho Sprint 5 (Q-19).

**Ràng buộc kiến trúc bắt buộc:** máy trạng thái hội thoại chỉ có **một hiện thực duy nhất**, portable xuống MCU. Không được dùng một máy trạng thái cho `linux` và một máy trạng thái khác cho `esp32s3` — hai bản sẽ phân kỳ, và hành vi thu hồi lệnh actuator khi cắt lời sẽ khác nhau giữa các target, phá vỡ tương đương ở đúng miền nguy hiểm nhất.

**Đòn bẩy OSS Sprint 5:** microWakeWord trên MCU và openWakeWord trên Linux · Silero VAD và libfvad · WebRTC AEC3 · Opus · port mô hình frame processor và barge-in từ Pipecat. Không còn hạng mục STT/TTS trên thiết bị. Tiết kiệm ước tính 4 tuần, phần lớn nằm trên đường găng.

**Ràng buộc bắt buộc:** hiện thực C/C++ này là bản thứ hai của cùng một đặc tả, không phải một thiết kế độc lập. Nó chỉ được nghiệm thu khi vượt toàn bộ bộ vector tuân thủ chung (§3.8).

**Tiêu chí ra Sprint 5 (Exit Criteria):**

- [ ] **Tiêu chí 1:** Vòng lặp thoại chạy end-to-end trên bo mạch tham chiếu với STT, TTS và suy luận ngôn ngữ đặt ở provider cloud.
- [ ] **Tiêu chí 2:** Cắt lời giữa câu: TTS dừng dưới 300 ms, không có lệnh actuator nào rò rỉ.
- [ ] **Tiêu chí 3:** Bơm 20 khung nhiễu liên tiếp: máy trạng thái vẫn phản hồi đúng.
- [ ] **Tiêu chí 4:** Bộ nhớ còn lại sau 4 giờ chạy nằm trong ngân sách Q-3.
- [ ] **Tiêu chí 5 (Q-14):** Mất kết nối tới provider giữa phiên → gate lượng giá bằng fallback cục bộ của TSK-S5-07; fallback không có / không chạy được → hành động vật lý bị chặn với lý do `gate_unreachable`; thiết bị không treo và phục hồi được khi có mạng trở lại.


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

**Sổ quyết định là PRD §15**, nơi định nghĩa đầy đủ các quyết định Q-1 đến Q-20. Mục này **không định nghĩa quyết định mới** — nó chỉ theo dõi hạn chốt, người quyết và trạng thái thực thi. Khi hai tài liệu lệch nhau, PRD §15 đúng.

### 10.1 Mười bảy quyết định đã chốt

| Mã | Quyết định | Giá trị chốt | Cơ sở |
|:---:|:---|:---|:---|
| **Q-1** | Phiên bản Python tối thiểu | **Python 3.11+** | `tomllib` có sẵn trong thư viện chuẩn nên không cần `tomli` · `TaskGroup` và `ExceptionGroup` trong `asyncio` · bytecode nhanh hơn khoảng 25% so với 3.10 |
| **Q-2** | Bo mạch tham chiếu chính thức | **ESP32-S3-Box-3** | Tích hợp sẵn LCD ST7789, dual-mic ES7210, loa ES8311, dock GPIO. Loại bỏ hoàn toàn việc câu dây thủ công vốn gây nhiễu clock I2S trên DevKitC. DevKitC hạ xuống bo mạch thứ cấp do cộng đồng hỗ trợ |
| **Q-3** | Ngân sách bộ nhớ và firmware | **SRAM cho ứng dụng ≥ 120 KB · PSRAM ≥ 2 MB · firmware ≤ 3,5 MB** | Bảo đảm nạp vừa phân vùng kép A/B trên flash 16 MB của Box-3. PSRAM dành cho ring buffer âm thanh, VAD và wake-word |
| **Q-4** | Nhà cung cấp mô hình ở v1.0 *(sửa 2026-09-23)* | **System 1:** Jev qua đám mây + **fallback cục bộ = bộ nhận diện lệnh cố định** theo Q-14 (thay Sherpa-ONNX)<br>**System 2:** `claude-sonnet-5` và GPT-4o-mini **qua LiteLLM** (Q-10) | Bảo đảm nguyên tắc fallback cục bộ khi mất mạng thực sự khả thi, không chỉ là tuyên bố kiến trúc |
| **Q-8** | Ngôn ngữ lõi firmware | **C/C++ trên ESP-IDF** cho `esp32s3`; Python cho `sim` và `linux` | Thừa hưởng trọn vẹn driver XiaoZhi và hệ sinh thái ESP-IDF. Kéo theo nghĩa vụ đặc tả chuẩn tắc và bộ vector tuân thủ tại §3.8 |
| **Q-9** | Lượng giá CEL trên vi điều khiển | **Phương án A — biên dịch gate lúc build** | `neuroedge build` dịch CEL thành cây quyết định JSON phẳng; firmware duyệt cây bằng một hàm C khoảng 100 dòng. Phán quyết đồng nhất trên mọi target, không tốn RAM |
| **Q-12** | Chuẩn kết nối nhà cung cấp AI | **OpenAI API là chuẩn mặc định**; provider chưa tương thích đi qua **adapter do người dùng tự viết**. Áp dụng chung cho LLM, ASR và TTS | Chốt theo CR-1.0 (PRD §15, FR-MDL-07→09). Tận dụng hệ sinh thái đã quen chuẩn OpenAI thay vì phát minh hợp đồng riêng; adapter giữ đường thoát khi chuẩn bên ngoài thay đổi |
| **Q-7** | Từ khóa kích hoạt mặc định v1.0 | ***"Hey Neuro"*** qua `microWakeWord` trên Box-3 và `openWakeWord` trên `linux`/`sim` | Chốt sớm để Sprint 5 chọn được mô hình wake-word mà không phải chờ. Tiêu chí ra Sprint 2 đã yêu cầu quyết định này |
| **Q-13** | Phân tầng cam kết theo bậc target | **Ba bậc:** bậc 1 giữ toàn bộ cam kết chất lượng; bậc 2 đội lõi bảo trì với cam kết hẹp hơn; bậc 3 cộng đồng tự kiểm chứng | Cho phép mở rộng phần cứng ở Giai đoạn 2 mà không pha loãng chất lượng bậc 1 (FR-TGT-08) |
| **Q-10** | Mức độ phụ thuộc vào LiteLLM · ✅ **2026-09-23** | **Thư viện định tuyến (SDK)**, không chạy LiteLLM proxy server, luôn sau `neuroedge.models.providers`; cài qua extra **`neuroedge[cloud]`** | `pip install neuroedge` không kéo LiteLLM (wheel ~120 MB do boto3, huggingface_hub) → FR-DX-02 nhẹ và keyless. Adapter Q-12 vẫn là đường thoát |
| **Q-14** | Mất mạng + fallback cục bộ · ✅ **2026-09-23** | Offline ⇒ gate **vẫn lượng giá** bằng bộ nhận diện **lệnh cố định**; BLOCK `gate_unreachable` chỉ khi fallback không chạy được. Fallback lên **P0**. Backend theo target, cùng ngữ pháp: `sim` khớp chữ gõ · `esp32s3` ESP-SR MultiNet hoặc TFLite Micro/ESP-NN · `linux` TFLite/KWS | Giải CEO-X1. Thay Sherpa-ONNX. Kéo theo: TSK-S2-08, TSK-S5-07, spike TSK-S1-10 đo MultiNet, xác minh giấy phép ESP-SR trước Sprint 5 |
| **Q-15** | Đầu vào mặc định của `sim` · ✅ **2026-09-23** | **Gõ chữ** (CLI/UI) → bộ khớp ngữ pháp lệnh Q-14: không mạng, không key, tất định. Giọng nói tùy chọn (STT cloud khi có key) | FR-DX-02. Hành trình 10 phút bước 2–4: `neuroedge run --target sim`, gõ một lệnh, thấy actuator ảo và phán quyết gate |
| **Q-16** | GPIO cho `linux` · ✅ **2026-09-23** | CI dùng **`gpio-sim`** (kernel ≥ 5.19, configfs); thí nghiệm **đạt 2026-09-23** (job `linux-hal`, PR #13); **mua 1 RPi 5** làm nightly phần cứng; HAL `linux` ném lỗi khi không có `/dev/gpiochip*` | Giải F1. Xem TSK-S3-05, Phụ lục B |
| **Q-17** | Hành vi `on_block` ở v1.0 · ✅ **2026-09-23** | Mọi `on_block` chặn hành động vật lý; `escalate`/`ask` ghi sự kiện + gọi hook (mặc định no-op); `degrade` chạy `fallback_action` qua gate của chính nó | Hành vi đặc tả, fail-closed, test 100% ⇒ **không phải nợ, không cần waiver** (§11.3). Bề mặt tương tác thật thuộc TSK-S2-07/S2-09/Sprint 5 |
| **Q-18** | Kế thừa `budget`/`on_block` · ✅ **2026-09-23** | `p95` con ≤ cha · chuỗi `closed` thì con không khai `fail: open` · con không tự đưa vào `degrade`/`fallback_action` mới; vi phạm ⇒ `GateInheritanceError` | RFC-0004, sửa ngữ nghĩa phân giải; đóng lỗ `lax-night` (ENG-A2). Task: TSK-S2-13. Mở rộng FR-GATE-06 và Phụ lục B.5 |
| **Q-19** | Lịch Sprint 2–3 theo ngày tuyệt đối · ✅ **2026-09-23** | A1 **2026-09-28 → 2026-10-25** · A2 **2026-10-26 → 2026-11-15** · Sprint 4 mở **2026-11-16** | Bỏ quy ước "Tuần N ở đây = Tuần N+1". M1 trễ ~2 tuần; Khối 1b lùi tương ứng. V1 ~6,6–7,1 tuần-người trong 7 tuần |
| **Q-20** | Cổng nhu cầu mềm · ✅ **2026-09-23** | Cổng **2026-10-25** (cuối A1), **không chặn A2** | CEO-X2..X5 và CEO-T1..T4 thành câu hỏi kinh doanh mở, trưởng nhóm chủ trì ([`TODOS.md`](TODOS.md) #19) |
| **Q-21** | Mô phỏng theo tầng bằng OSS · ✅ **2026-09-23** | SimHAL · gpio-sim · âm thanh tệp/PCM (runner không có `snd-aloop`) · i2c-stub + lm75 · khung hình + digest · C và LVGL build trên host · Espressif QEMU · bo mạch thật; không Renode, không Wokwi | Walker C (TSK-S4-02) kiểm được trên mỗi PR trước khi bo mạch về — thêm TSK-S4-07, S4-08. Proposal §3.2 |
| **Q-22** | AEC phần mềm trên `linux` · ✅ **2026-09-23** (phương án A) | PipeWire `module-echo-cancel` (`aec/libspa-aec-webrtc`); `audio.in` đọc nút `source`, `audio.out` phát vào nút `sink`; `linux-rpi5` khai `aec = true` chỉ khi đo đạt | Đóng khoảng FR-TGT-02 ở TSK-S5-08. Tiêu chí đo: `simulation_coverage.md` §6 |
| **Q-23** | Định dạng cây quyết định trên MCU · ✅ **2026-09-23** | Bố cục nhị phân cố định (struct C) do `neuroedge build` sinh; v1.0 link vào firmware, sau này đặt ở phân vùng flash riêng (`esp_partition_mmap`) để đổi gate không nạp lại firmware | Không có parser JSON trên MCU, cây nằm trong flash (RB-4). RFC-0003 thu hẹp — `TODOS.md` #15 |
| **Q-24** | Hành động là tool call · MCP · ✅ **2026-09-23** | Mỗi `@action` là một tool; ngữ pháp cục bộ, System 1/2 và MCP gửi cùng `ToolCall` → kiểm schema → `c.do()` → gate; dữ kiện `call_source` do dispatcher chèn | Hết ánh xạ cứng câu → hàm; mất mạng vẫn chạy bằng tool call tổng hợp (Q-14). `neuroedge mcp serve` (FR-CLI-10). PRD §15 |

**Hệ quả trực tiếp lên Sprint 1:** Q-1, Q-2 và Q-3 đã chốt nghĩa là đội có thể đặt bo mạch, dựng kho mã và bắt đầu spike ngay Tuần 0 mà không chờ quyết định nào.

**Một điều chỉnh so với đề xuất gốc:** Q-4 ghi Claude Sonnet 5 thay vì Sonnet 3.5. Thế hệ 3.5 đã bị thay thế; chốt một định danh mô hình lỗi thời vào tài liệu nền sẽ tạo nợ ngay từ ngày đầu.

### 10.2 Ba quyết định còn mở và một RFC

| Hạn | Mã | Quyết định | Vì sao hạn đó | Người quyết | Trạng thái |
|:---:|:---:|:---|:---|:---:|:---:|
| **Trước Khối 2** | **Q-11** | Phê duyệt ngoại lệ giấy phép: Hawkbit EPL-2.0, EMQX BSL, LiteLLM | **Phần LiteLLM ✅ ĐÃ DUYỆT 2026-09-23:** `litellm==1.102.0` MIT, wheel không có `enterprise/`, 55 phụ thuộc bắc cầu đều MIT/BSD/Apache-2.0/PSF + MPL-2.0 (`certifi`, `tqdm`), kèm chính sách phụ thuộc bắc cầu (dưới bảng). **Phần Hawkbit / EMQX còn mở**, chỉ Khối 2 dùng — không viết thiết kế phụ thuộc nào của Fleet OS trước khi có phê duyệt bằng văn bản ([`TODOS.md`](TODOS.md) #16) | Kỹ thuật trưởng | 🟡 **Một phần** |
| **Tháng 3** | Q-5 | Xác thực và chống lạm dụng cho Registry công khai | Cần trước khi thiết kế hạ tầng Khối 3 | Kỹ thuật nền tảng | ⏳ Đang mở |
| **Tháng 6** | **RFC-0002** | Mở rộng enum `target` và đưa bậc target vào mã lõi (`TARGET_TIERS`) cho Giai đoạn 2; `vision.in` tách sang RFC riêng ở V1b | Không chặn roadmap này. Chặn Khối V1a của Giai đoạn 2, và phải xong trước khi viết bất kỳ board profile mới nào | Kỹ thuật trưởng | ⏳ Đang mở |
| **Tháng 3** | Q-6 | Chính sách lưu trữ vết ghi: thời hạn và hạn mức | Ảnh hưởng chi phí vận hành và cam kết SLA | Sản phẩm | ⏳ Đang mở |

**Q-11 không còn chặn Giai đoạn 1.** Phần LiteLLM — phần duy nhất Giai đoạn 1 phân phối kèm sản phẩm sau CR-1.0 — đã duyệt 2026-09-23, nên Tiêu chí ra 6 của Sprint 1 thoả và **TSK-S2-11 hết bị chặn** (chạy trong A2, hạn 2026-11-15). Phần còn lại (Hawkbit, EMQX) chỉ Khối 2 dùng; hạn chốt là **trước khi mở Khối 2**.

**Chính sách phụ thuộc bắc cầu (Q-11):** cho phép MIT, BSD-2/3-Clause, Apache-2.0, ISC, PSF, MPL-2.0 (MPL chỉ dùng nguyên bản, không sửa); cấm GPL/LGPL/AGPL, SSPL, BSL, giấy phép thương mại hoặc không xác định. Cưỡng chế bằng bước kiểm giấy phép trong CI, làm cùng TSK-S2-11. *(Ngoại lệ LGPL qua liên kết động của `libgpiod` tại §3.3 quy tắc 3 là thư viện hệ thống C, không phải phụ thuộc Python bắc cầu.)*

#### Phát hiện giấy phép trong Sprint 1 (đã xử lý, ghi lại để không tái diễn)

Khi dựng cổng giấy phép cho CI (TSK-S1-12), rà soát phụ thuộc phát hiện **hai đường lây nhiễm copyleft mạnh vào lõi MIT** — cả hai đều là phụ thuộc bắc cầu, không ai chủ ý thêm:

| Đường lây nhiễm | Giấy phép | Cách xử lý |
|:---|:---|:---|
| `neuroedge` → `copier` → `jinja2-ansible-filters` | **GPL3** | `copier` rời tập phụ thuộc lõi; TSK-S3-07 hiện thực `neuroedge new` bằng generator Python thuần nên bỏ hẳn extra `scaffold` |
| `neuroedge` → `jsonschema[format]` → `rfc3987` | **GPL** | Ghim extra `[format-nongpl]`, dùng `rfc3987-syntax` (MIT). Extra này là **bắt buộc**, không phải tùy chọn: thiếu bộ kiểm tra format thì `format: date-time` trong `trace.v1.json` chỉ là chú thích, và một vết ghi có mốc thời gian không phân tích được vẫn thẩm định đạt |

Cả hai đều trực tiếp hiện thực hóa rủi ro mà §3.10 của tài liệu này nêu: *"Nhúng mã GPLv3 vào phần phân phối → Lây nhiễm bản quyền sang lõi MIT và sang dự án của khách hàng."* Điều đáng chú ý là **không ai thêm một phụ thuộc GPL nào một cách chủ ý** — cả hai đến qua phụ thuộc bắc cầu của một thư viện hoàn toàn permissive. Rà soát giấy phép bằng mắt ở tầng phụ thuộc trực tiếp sẽ bỏ sót cả hai.

Vì vậy job `licence-obligations` trong [`ci-sim-linux.yml`](file:///Users/minhlt/Downloads/Projects/neuroedge-init/.github/workflows/ci-sim-linux.yml) chạy `pip-licenses --fail-on` trên **toàn bộ cây phụ thuộc** ở mỗi pull request, và lưu bảng giấy phép đầy đủ làm artifact. Đây là nghĩa vụ 1 và 5 của §3.9 được tự động hóa, thay cho một lần rà soát thủ công.

**Hệ quả cho Q-11 (đã thực hiện 2026-09-23):** quyết định Q-11 bao gồm luôn chính sách phụ thuộc bắc cầu ở trên, không chỉ phê duyệt các thành phần đã nêu tên.

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
| 4   | `--help` cập nhật; tài liệu, tiến độ, changelog cập nhật theo `CONTRIBUTING.md` §8 |
| 5   | Thông báo lỗi liên quan nêu đủ ba thành phần: sai ở đâu, vì sao, xử lý thế nào |


### 11.3 Quy tắc bảo vệ đường găng


| Quy tắc                              | Nội dung                                                                         |
| :------------------------------------ | :-------------------------------------------------------------------------------- |
| **Đóng băng lược đồ**                | Sau Tuần 2, mọi thay đổi lược đồ cần RFC, phê duyệt và kịch bản di trú           |
| **Không nợ kỹ thuật ở tầng an toàn** | Gate Engine và HAL không được hợp nhất kèm ghi chú "sẽ sửa sau". **Làm rõ (Q-17):** một hành vi **đã đặc tả, fail-closed và được test đầy đủ** — ví dụ `on_block` ở v1.0, nơi mọi hành vi đều chặn hành động vật lý còn bề mặt tương tác thật (người nhận escalate, UI hỏi lại) để sau — **không phải** nợ "sẽ sửa sau" và không cần waiver. Nợ là hành vi chưa đặc tả, fail-open, hoặc chưa có test |
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
| **ESP32-S3-Box-3** (bo mạch tham chiếu chính thức) — **đợt 1** | **2** | **ĐẶT NGAY** (2026-09-23) | Chặn TSK-S1-10 (spike bộ nhớ, đo cả MultiNet theo Q-14) và Tiêu chí ra Sprint 1 #3. Giá và lead time còn mở (design doc Open Q4) |
| **ESP32-S3-Box-3** — đợt 2 | 3–6 | Sprint 4 (từ 2026-11-16) | Chốt tại Q-2. Đã tích hợp LCD, dual-mic và loa nên không cần mua rời. Tổng 5–8; dư ra cho nightly runner và bo mạch hỏng |
| **Raspberry Pi 5** — cho `gpio-sim` / nightly (Q-16) | **1** | **ĐẶT NGAY**, về trước A2 (2026-10-26) | Nightly phần cứng cho HAL `linux` (TSK-S3-05). Phương án B không cần nữa: runner GitHub chạy được `gpio-sim` (2026-09-23) |
| ESP32-S3-DevKitC (bo mạch thứ cấp) | 2 | Tuần 3 | Kiểm chứng tính di động của HAL ngoài Box-3; hỗ trợ ở mức cộng đồng |
| Raspberry Pi 5                                 | 2        | Tuần 3     | Target `linux` trên ARM64 *(ngoài chiếc của Q-16 ở trên)* |
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
│   │   ├── cli/                # Typer · Rich · run/explain; mẫu dự án: templates/
│   │   ├── hal/                # 5 nguyên thủy và bộ đối chiếu năng lực lúc build
│   │   ├── engine/             # Action Contract Engine · trình biên dịch CEL sang cây quyết định
│   │   ├── models/             # SystemOne/SystemTwo · lớp provider (OpenAI-compatible + adapter)
│   │   ├── perception/         # Voice pipeline · VAD · barge-in · provider ASR/TTS
│   │   ├── testing/            # Action CI: pytest-neuroedge · replay · assert
│   │   └── sim/                # SimSession (gõ chữ) · web UI: TSK-S2-09
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
