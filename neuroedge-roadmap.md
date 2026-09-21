# NeuroEdge — Roadmap thực thi

## Kế hoạch triển khai từ Tuần 0 đến Tháng 8

**Phiên bản:** 1.0
**Ngày lập:** 21 tháng 9, 2026
**Tài liệu nguồn:** `neuroedge-proposal.md` v5.2 · `neuroedge-prd.md` v1.0
**Phạm vi:** Khối 1a · Khối 1b · Developer Beta · Khối 2 và 3
**Ngoài phạm vi:** Khối 4 (AURA thực địa) · Khối 5 (Marketplace) — lập kế hoạch riêng khi tới mốc

---

## Mục lục

1. [Giả định nguồn lực](#1-giả-định-nguồn-lực)
2. [Đường găng và phụ thuộc](#2-đường-găng-và-phụ-thuộc)
3. [Khối 1a — Lõi và Action CI (Tuần 0–6)](#3-khối-1a--lõi-và-action-ci-tuần-06)
4. [Khối 1b — Vi điều khiển biên (Tuần 6–12)](#4-khối-1b--vi-điều-khiển-biên-tuần-612)
5. [Developer Beta (Tuần 12–16)](#5-developer-beta-tuần-1216)
6. [Điểm rẽ quyết định Tuần 16](#6-điểm-rẽ-quyết-định-tuần-16)
7. [Khối 2 và 3 — Tầng dịch vụ (Tháng 4–8)](#7-khối-2-và-3--tầng-dịch-vụ-tháng-48)
8. [Thang cắt phạm vi](#8-thang-cắt-phạm-vi)
9. [Lịch chốt quyết định](#9-lịch-chốt-quyết-định)
10. [Nhịp vận hành](#10-nhịp-vận-hành)
11. [Chỉ báo sớm và ngưỡng can thiệp](#11-chỉ-báo-sớm-và-ngưỡng-can-thiệp)

**Phụ lục**

- [A — Bảng mốc tổng hợp](#phụ-lục-a--bảng-mốc-tổng-hợp)
- [B — Danh mục mua sắm và hạ tầng](#phụ-lục-b--danh-mục-mua-sắm-và-hạ-tầng)

---

## 1. Giả định nguồn lực

> **Đây là giả định, không phải dữ kiện.** Toàn bộ lịch trình bên dưới phụ thuộc vào nó. Nếu cấu hình đội khác đi, xem §1.3 trước khi đọc tiếp.

### 1.1 Bốn vai trò bắt buộc

| Vai trò | Trách nhiệm chính | Có mặt từ |
|:---|:---|:---:|
| **V1 — Kỹ sư lõi nền tảng** | HAL, Action Contract Engine, lược đồ gate và trace, Action CI | Tuần 0 |
| **V2 — Kỹ sư nhúng** | Port `esp32s3`, runtime thoại trên MCU, OTA cấp thiết bị, tối ưu bộ nhớ | Tuần 0 *(bán thời gian tới Tuần 6)* |
| **V3 — Kỹ sư trải nghiệm lập trình viên** | Giao diện `sim`, CLI, scaffold, tài liệu, ví dụ mẫu | Tuần 2 |
| **V4 — Kỹ sư hạ tầng dịch vụ** | Gateway, Fleet OS, Registry, hệ đo lường | Tháng 3 |

**Cấu hình tối thiểu khả thi: 3 người cho Khối 1**, trong đó một người kiêm vai trò kỹ thuật trưởng và vẫn viết mã. Vai trò V4 tuyển trước Khối 2 một tháng để có thời gian làm quen kiến trúc.

### 1.2 Vì sao V2 phải có mặt từ Tuần 0

Rủi ro **R-1** của PRD (phạm vi Khối 1b vượt hạn do tối ưu bộ nhớ MCU) được đánh giá mức **Cao**. Cách giảm thiểu hiệu quả không phải là giám sát ở Tuần 9, mà là **chạy spike khả thi bộ nhớ ngay Tuần 2**, khi vẫn còn đủ thời gian để đổi phạm vi.

V2 làm bán thời gian trong Khối 1a: một phần cho spike, phần còn lại rà soát thiết kế HAL dưới góc nhìn ràng buộc MCU. Một HAL thiết kế mà không có tiếng nói của kỹ sư nhúng sẽ phải viết lại ở Tuần 6.

### 1.3 Độ nhạy theo quy mô đội

| Cấu hình | Tác động lên lịch trình |
|:---|:---|
| **2 người** | Khối 1a giãn sang 8–9 tuần; Khối 1b sang 14–16 tuần. Bắt buộc áp dụng bậc 5 của thang cắt phạm vi (§8) ngay từ đầu |
| **3 người** *(giả định cơ sở)* | Lịch trình như tài liệu này |
| **4–5 người** | Khối 1a rút còn 5 tuần; Khối 1b song song hóa nhiều hơn. Không rút được dưới 4 tuần vì đường găng là chuỗi thiết kế lược đồ tuần tự |

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
                                      └──► Port esp32s3 ────────────────┴──► verify 3 target
                                           (Tuần 6–8)                        (Tuần 8)
                                                │
                                                └──► Runtime thoại MCU ──► OTA ──► v1.0
                                                     (Tuần 8–10)         (Tuần 10–12)

    ⟂ Song song từ Tuần 2:  SPIKE BỘ NHỚ ESP32-S3  ──► quyết định phạm vi 1b (Tuần 4)
```

### 2.2 Đường găng

| # | Mắt xích | Tuần | Vì sao nằm trên đường găng |
|:---:|:---|:---:|:---|
| 1 | Đóng băng lược đồ gate và trace | 0–2 | FR-TRC-05 yêu cầu định dạng ổn định giữa các phiên bản. Mọi vết ghi đã tạo sẽ hỏng nếu đổi lược đồ sau Tuần 6 |
| 2 | Gate Engine với fail-closed | 2–4 | Mọi thành phần khác gọi vào nó |
| 3 | Record và replay | 4–5 | Là điều kiện để có assert và golden |
| 4 | Port HAL lên `esp32s3` | 6–8 | Không có target thứ ba thì không chứng minh được tương đương |
| 5 | Runtime thoại trên MCU | 8–10 | Mắt xích rủi ro nhất; xem §8 |

**Không nằm trên đường găng, làm song song:** giao diện `sim`, CLI, tài liệu, ví dụ mẫu, hạ tầng CI.

### 2.3 Quy tắc đóng băng lược đồ

Từ **cuối Tuần 2**, mọi thay đổi đối với lược đồ gate hoặc lược đồ vết ghi bắt buộc:

1. Có đề xuất RFC viết ra, nêu rõ lý do và ảnh hưởng tương thích ngược
2. Được kỹ thuật trưởng phê duyệt
3. Kèm kịch bản di trú cho toàn bộ vết ghi đã tồn tại

Đây là quy tắc nghiêm ngặt nhất của toàn bộ dự án. Lược đồ trôi nổi làm sụp đổ mệnh đề trung tâm.

---

## 3. Khối 1a — Lõi và Action CI (Tuần 0–6)

**Mục tiêu khối:** một lập trình viên lạ chạy được agent có gate trong dưới 10 phút, không cần mua phần cứng.

### 3.1 Sprint 1 — Đóng băng lược đồ (Tuần 0–2)

| Hạng mục | Yêu cầu PRD | Người |
|:---|:---|:---:|
| Đặc tả 5 nguyên thủy HAL và thuộc tính đối chiếu | FR-HAL-01, FR-HAL-02, FR-HAL-03 | V1 |
| Lược đồ gate v1: 8 trường, 3 kiểu `evaluate`, 4 hành vi `on_block`, `budget` | FR-GATE-02, FR-GATE-03, FR-GATE-04 | V1 |
| Quy tắc kế thừa `extends`: 5 nguyên tắc an toàn | FR-GATE-06, FR-GATE-07, FR-GATE-08 | V1 |
| Lược đồ vết ghi v1: 6 nhóm sự kiện, khối `metadata` | FR-TRC-01, FR-TRC-02, FR-TRC-03 | V1 |
| **Spike khả thi bộ nhớ trên ESP32-S3** | NFR-RES-01, NFR-RES-02 | V2 |
| Rà soát thiết kế HAL dưới ràng buộc MCU | — | V2 |
| Dựng kho mã, CI cơ bản, quy ước đóng góp | — | V1 |

**Nội dung spike bộ nhớ:** nạp thử AEC + VAD + Opus streaming lên bo mạch tham chiếu, đo dung lượng SRAM/PSRAM còn lại sau khi trừ ngăn xếp mạng và hệ điều hành. Kết quả là **một con số**, không phải một nhận định.

**Tiêu chí ra Sprint 1:**

| # | Tiêu chí |
|:---:|:---|
| 1 | JSON Schema của gate và trace publish nội bộ, có ví dụ hợp lệ và ví dụ sai kèm thông báo lỗi kỳ vọng |
| 2 | Ba gate mẫu viết tay được công cụ phân giải đúng, gồm một trường hợp kế thừa 2 cấp |
| 3 | Báo cáo spike bộ nhớ có số liệu đo thực, kèm khuyến nghị phạm vi cho Khối 1b |
| 4 | Quyết định Q-1, Q-2, Q-4 đã chốt (§9) |

### 3.2 Sprint 2 — Lõi thực thi trên `sim` (Tuần 2–4)

| Hạng mục | Yêu cầu PRD | Người |
|:---|:---|:---:|
| Hiện thực HAL cho target `sim` | FR-TGT-01, FR-HAL-01 | V1 |
| Đối chiếu năng lực lúc build, thông báo lỗi đầy đủ 3 thành phần | FR-HAL-04, FR-HAL-05, FR-DX-04 | V1 |
| Gate Engine: `evaluate`, `allow_when`, `on_block`, `budget` | FR-GATE-03, FR-GATE-04, FR-GATE-09 | V1 |
| Cơ chế fail-closed và mạch ngắt suy giảm | FR-ACE-03, NFR-REL-02 | V1 |
| Decorator `@action`, cấm gọi trực tiếp, `c.do()` và `c.say()` | FR-ACE-02, FR-ACE-04, FR-ACE-05, FR-ACE-07 | V1 |
| Interface `SystemOne` / `SystemTwo` kèm fallback | FR-MDL-01, FR-MDL-02, FR-MDL-03 | V1 |
| Giao diện web `sim`: cảm biến ảo, trạng thái actuator | FR-TGT-06 | V3 |
| Kết luận phạm vi Khối 1b dựa trên spike | — | V2 + trưởng nhóm |

**Tiêu chí ra Sprint 2:**

| # | Tiêu chí |
|:---:|:---|
| 1 | Agent mẫu chạy trên `sim`, gate chặn đúng theo `allow_when` |
| 2 | Gọi trực tiếp hành động vật lý ném `ActionContractViolation`, chân GPIO ảo không kích |
| 3 | Kịch bản mất mạng → hành động bị chặn với lý do `gate_unreachable` |
| 4 | Gate con nới lỏng `allow_when` bị từ chối phân giải |
| 5 | Quyết định Q-3, Q-7 đã chốt |

### 3.3 Sprint 3 — Action CI, `linux` và TTFV (Tuần 4–6)

| Hạng mục | Yêu cầu PRD | Người |
|:---|:---|:---:|
| Record: ghi phiên ra tệp JSON hợp lệ | FR-CI-01 | V1 |
| Replay trên target bất kỳ | FR-CI-02 | V1 |
| Thư viện assert: chặn, gate nào, leo thang, chân cấm kích | FR-CI-03 | V1 |
| Golden Reference và so khớp chuỗi phán quyết | FR-CI-04 | V1 |
| Hiện thực HAL cho target `linux` qua `gpiod` | FR-TGT-02 | V1 |
| CLI đầy đủ: `new`, `run`, `build`, `test`, `record`, `replay`, `trace validate` | FR-CLI-01→04, FR-TRC-08 | V3 |
| Scaffold `neuroedge new` có sẵn action, gate, test | FR-DX-01 | V3 |
| Ba ví dụ mẫu chạy được, README có tài sản trực quan | FR-DX-05, FR-DX-06 | V3 |
| Telemetry CLI ẩn danh, có thể tắt | FR-TEL-01, FR-TEL-02 | V3 |
| Pipeline CI mẫu chạy `sim` + `linux` trên mỗi PR | FR-CI-05 | V1 |

**Tiêu chí ra Sprint 3 — cổng kết thúc Khối 1a:**

| # | Tiêu chí | Tham chiếu |
|:---:|:---|:---:|
| 1 | TTFV đo thử nội bộ trên **3 người ngoài đội** đạt trung vị dưới 10 phút | A1 *(đo đầy đủ ở Tuần 12)* |
| 2 | `neuroedge verify --targets sim,linux` đạt 100% | A2 *(một phần)* |
| 3 | Không tồn tại đường tắt kích hoạt GPIO bỏ qua gate | A3 |
| 4 | 100% kịch bản suy giảm đều chặn hành động | A4 |
| 5 | Bộ kiểm thử kế thừa gate đạt 100% | A5 |
| 6 | 100% phiên sinh vết ghi qua được `neuroedge trace validate` | A7 |

---

## 4. Khối 1b — Vi điều khiển biên (Tuần 6–12)

**Mục tiêu khối:** chứng minh nguyên tắc tương đương môi trường trên vi điều khiển $5, với độ ổn định sản xuất.

### 4.1 Sprint 4 — HAL trên `esp32s3` (Tuần 6–8)

Sprint này **cố tình chưa làm thoại**. Mục đích là chứng minh tương đương target trên miền quyết định trước, khi biến số còn ít.

| Hạng mục | Yêu cầu PRD | Người |
|:---|:---|:---:|
| Port 5 nguyên thủy HAL lên ESP-IDF | FR-TGT-03, FR-HAL-01 | V2 |
| Gate Engine chạy trên MCU | FR-ACE-01, FR-ACE-03 | V2 + V1 |
| Đường dẫn `digital.out` và `sensor.read` trên phần cứng thật | FR-HAL-06, FR-HAL-07 | V2 |
| Lệnh `neuroedge verify` cho cả 3 target | FR-CI-07, FR-TGT-04 | V1 |
| Runner kiểm thử nightly trên bo mạch thật | FR-CI-06, NFR-REL-03 | V3 |

**Tiêu chí ra Sprint 4:**

| # | Tiêu chí |
|:---:|:---|
| 1 | `neuroedge verify --targets sim,linux,esp32s3` đạt 100% trên kịch bản **không dùng audio** → **A2 đạt cho miền phán quyết** |
| 2 | Sai lệch phán quyết giữa các target sinh `TargetEquivalenceError` chỉ rõ sự kiện lệch đầu tiên |
| 3 | Nightly runner chạy tự động và gửi báo cáo |

### 4.2 Sprint 5 — Runtime thoại trên MCU (Tuần 8–10)

**Đây là sprint rủi ro nhất của toàn dự án.**

| Hạng mục | Yêu cầu PRD | Người |
|:---|:---|:---:|
| Tích hợp WebRTC AEC, Silero VAD, Opus streaming | FR-PER-06 | V2 |
| Port có chọn lọc đường dẫn audio tham khảo, kèm ghi nhận nguồn và rà soát giấy phép | FR-PER-01 | V2 |
| Máy trạng thái hội thoại: barge-in, khoảng lặng động, tự phục hồi STT | FR-PER-02, FR-PER-03, FR-PER-05 | V1 |
| Thu hồi lệnh actuator chưa thực thi khi bị cắt lời | FR-PER-02 | V1 + V2 |
| Tối ưu bộ nhớ theo ngân sách đã chốt ở Q-3 | NFR-RES-01, NFR-RES-02 | V2 |

**Ràng buộc kiến trúc bắt buộc:** máy trạng thái hội thoại chỉ có **một hiện thực duy nhất**, portable xuống MCU. Không được dùng một máy trạng thái cho `linux` và một máy trạng thái khác cho `esp32s3` — hai bản sẽ phân kỳ, và hành vi thu hồi lệnh actuator khi cắt lời sẽ khác nhau giữa các target, phá vỡ tương đương ở đúng miền nguy hiểm nhất.

**Tiêu chí ra Sprint 5:**

| # | Tiêu chí |
|:---:|:---|
| 1 | Vòng lặp thoại đầy đủ chạy trên bo mạch tham chiếu |
| 2 | Cắt lời giữa câu: TTS dừng dưới 300 ms, không có lệnh actuator nào rò rỉ |
| 3 | Bơm 20 khung nhiễu liên tiếp: máy trạng thái vẫn phản hồi đúng |
| 4 | Bộ nhớ còn lại sau 4 giờ chạy nằm trong ngân sách Q-3 |

### 4.3 Sprint 6 — OTA, ổn định hóa, nghiệm thu (Tuần 10–12)

| Hạng mục | Yêu cầu PRD | Người |
|:---|:---|:---:|
| OTA cấp thiết bị: phân vùng kép A/B | FR-OTA-01 | V2 |
| Tự động rollback khi phát hiện vòng lặp khởi động | FR-OTA-02 | V2 |
| Xác minh chữ ký firmware trên chip | FR-OTA-03 | V2 |
| Nạp firmware từ HTTP endpoint mở bất kỳ | FR-OTA-04 | V2 |
| Secure boot, mã hóa flash, nút ngắt micro vật lý | NFR-SEC-02, NFR-SEC-03 | V2 |
| Kiểm thử chịu tải 24 giờ | NFR-RES-01, A6 | V3 |
| Publish JSON Schema công khai và bộ kiểm thử tuân thủ | FR-GOV-01, FR-GOV-03, A9 | V1 |
| Hoàn thiện tài liệu, ví dụ, video minh họa | FR-DX-05, FR-DX-06, A8 | V3 |

**Tiêu chí ra Sprint 6 — cổng phát hành v1.0:** đạt **toàn bộ A1 đến A9** của PRD §11.1. Không chấp nhận đạt một phần.

---

## 5. Developer Beta (Tuần 12–16)

### 5.1 Nguyên tắc vận hành

> **Đóng băng hoàn toàn việc phát triển tính năng mới.** Mọi đề xuất tính năng trong giai đoạn này được ghi vào danh mục chờ, không đưa vào mã nguồn.

Ngoại lệ duy nhất: lỗi chặn người dùng hoàn thành hành trình 10 phút.

### 5.2 Phân bổ công sức

| Trọng tâm | Tỷ lệ công sức | Người |
|:---|:---:|:---:|
| Hỗ trợ 1:1 qua Discord và GitHub | 50% | Cả đội luân phiên |
| Hoàn thiện tài liệu theo vướng mắc thực tế | 25% | V3 |
| Sửa lỗi chặn | 20% | V1, V2 |
| Đo đạc và tổng hợp chỉ số | 5% | Trưởng nhóm |

### 5.3 Mục tiêu tuyển người dùng

| Tuần | Mục tiêu tích lũy | Kênh |
|:---:|:---|:---|
| 12 | 10 lập trình viên | Mạng lưới cá nhân, cộng đồng nhúng địa phương |
| 13 | 25 | Bài viết kỹ thuật kèm video demo |
| 14 | 50 | Diễn đàn ESP32, cộng đồng maker |
| 16 | 50–100 | Tích lũy tự nhiên |

### 5.4 Chỉ số phải đo trong Beta

| Mã | Chỉ số | Ngưỡng | Nguồn |
|:---:|:---|:---|:---|
| **B1** | Lập trình viên ngoài chạy thành công agent trên `sim` | ≥ 50 | FR-TEL-01 |
| **B2** | Lập trình viên ngoài nạp thành công phần cứng thật | ≥ 10 | FR-TEL-01 |
| **B3** | Gate do cộng đồng tự viết và đóng góp | ≥ 3 | Registry |
| **B4** | Tỷ lệ giữ lại và mở rộng test gate mặc định | ≥ 50% | FR-TEL-01 |
| **B5** | Tỷ lệ chuyển đổi `sim` → phần cứng trong 30 ngày | ≥ 15% | FR-TEL-01 |
| **A1** | TTFV đo đầy đủ trên 10 người độc lập | Trung vị < 10 phút | Biên bản đo |

---

## 6. Điểm rẽ quyết định Tuần 16

Kết thúc Beta, dự án đi theo đúng một trong ba nhánh. **Quyết định dựa trên số liệu B1–B5, không dựa trên cảm nhận về đà phát triển.**

| Nhánh | Điều kiện | Hành động |
|:---|:---|:---|
| **Nhánh A — Khởi động Khối 2** | Đạt đồng thời B1, B2, B3 | Tuyển V4, bắt đầu Gateway và Fleet OS theo §7 |
| **Nhánh B — Kéo dài Beta 4–6 tuần** | Đạt 2 trên 3 tiêu chí, tiêu chí còn lại đạt ≥ 60% ngưỡng | Giữ đóng băng tính năng, tập trung vào tiêu chí yếu nhất, đánh giá lại ở Tuần 22 |
| **Nhánh C — Xem xét lại luận điểm** | Không đạt hoặc chỉ đạt 1 trên 3 | Dừng lộ trình thương mại. Phỏng vấn sâu 20 người dùng đã thử và bỏ. Xác định luận điểm sai ở đâu trước khi viết thêm mã |

**Chỉ báo quan trọng nhất là B2** (10 người ngoài nạp được phần cứng thật). B1 đo sự tò mò; B2 đo cam kết. Một dự án có B1 cao nhưng B2 thấp là một dự án mà simulator hấp dẫn còn đường lên phần cứng bị nghẽn — khi đó việc cần làm là sửa đường lên phần cứng, không phải xây Gateway.

---

## 7. Khối 2 và 3 — Tầng dịch vụ (Tháng 4–8)

Khởi động **chỉ khi** đi nhánh A. Hai khối chạy song song.

### 7.1 Trình tự Khối 2 — Gateway và Fleet OS

| Tháng | Trọng tâm | Yêu cầu PRD | Tiêu chí ra |
|:---:|:---|:---|:---|
| **4** | Gateway: một endpoint, một credential, xoay khóa từ xa | FR-GW-01, FR-GW-02 | Thiết bị không lưu API key bên thứ ba |
| **5** | Gateway: định tuyến đa nhà cung cấp, failover, hạn mức theo thiết bị | FR-GW-03, FR-GW-05 | Ngắt nhà cung cấp chính, thiết bị không gián đoạn |
| **5–6** | Gateway: giao thức tối ưu edge, xuất vết ghi đồng nhất định dạng | FR-GW-04, FR-GW-07 | Vết ghi từ Gateway replay được trên máy cá nhân |
| **6** | Fleet: cấp phát danh tính và chứng chỉ thiết bị | FR-FLT-01 | Claim tự động trên lô 100 thiết bị |
| **6–7** | Fleet: sổ kiểm kê, giám sát sức khỏe, dashboard hữu ích ở n = 1 | FR-FLT-03, FR-FLT-06 | Trạng thái phản ánh đúng trong 60 giây |
| **7** | Fleet: cập nhật cấu hình, bí mật và gate từ xa | FR-FLT-04 | Đổi ngưỡng gate toàn đội, không nạp lại firmware |
| **7–8** | Fleet: điều phối OTA canary 1% → 10% → 100%, tự dừng khi vượt ngưỡng lỗi | FR-FLT-02 | **1.000 thiết bị / 0 brick** |
| **8** | Fleet: tự động tải vết ghi sự cố về kho tập trung | FR-FLT-05 | Sự cố xuất hiện trong kho dưới 5 phút |

### 7.2 Trình tự Khối 3 — Đường ray hạ tầng

| Tháng | Thành phần | Yêu cầu PRD |
|:---:|:---|:---|
| **4** | Định danh ổn định cho thiết bị, agent, gate | FR-REG-05 |
| **4–5** | Hệ đo lường theo lượt gọi agent và lượt thẩm định gate | FR-REG-06, FR-TEL-04 |
| **5** | Manifest và chuẩn phiên bản SemVer | FR-REG-02 |
| **5–6** | Kho Gate công khai miễn phí | FR-REG-01 |
| **6–7** | Cơ chế phân quyền và sandbox | FR-REG-07 |

**Thứ tự này không tùy tiện.** FR-REG-05, FR-REG-06 và FR-REG-07 phải đi trước vì không bổ sung sau được: thiếu định danh ổn định và đo lường thì Registry không quy kết được ai dùng gì; thiếu sandbox thì không dám cho mã người lạ chạy trên thiết bị có cơ cấu chấp hành.

### 7.3 Tiêu chí ra Khối 2 và 3

Toàn bộ C1 đến C7 của PRD §11.3.

---

## 8. Thang cắt phạm vi

Khi tiến độ trượt, cắt theo đúng thứ tự sau. **Không cắt nhảy bậc, không cắt tùy hứng.**

| Bậc | Hạng mục cắt | Mất gì | Yêu cầu bị ảnh hưởng |
|:---:|:---|:---|:---|
| **1** | Ví dụ mẫu thứ 2 và 3, giữ lại 1 | Tài liệu mỏng hơn | FR-DX-05 |
| **2** | Chính sách định tuyến khai báo được → viết cứng `fast_first` | Mất tính linh hoạt cấu hình | FR-MDL-05 *(P1)* |
| **3** | Client MCP | Hoãn ván cược về chuẩn giao tiếp công cụ | — |
| **4** | Phản hồi dòng từng phần | Độ trễ cảm nhận tăng | FR-PER-04 *(P1)* |
| **5** | **Tách Khối 1b:** `esp32s3` chỉ chạy gate và GPIO; runtime thoại đẩy sang sau Beta | Chứng minh tương đương target trên miền quyết định nhưng chưa có thoại trên MCU | FR-PER-06 |

### 8.1 Tuyệt đối không cắt

| Hạng mục | Lý do |
|:---|:---|
| Hợp đồng năng lực HAL | Là nền của tương đương target |
| Gate Engine và fail-closed | Là mệnh đề trung tâm của sản phẩm |
| Lược đồ vết ghi và record/replay | Không retrofit được |
| Golden Reference | Không có nó thì Action CI chỉ là một thư viện test thông thường |
| `sim` là target thật, không phải mock | Cắt cái này là cắt toàn bộ luận điểm |
| Nguyên tắc kế thừa gate an toàn | Thiếu nó, `extends` là rủi ro chứ không phải tính năng |

### 8.2 Ghi chú về bậc 5

Bậc 5 là bậc nặng nhất và cũng là phương án ứng phó chính cho rủi ro **R-1**. Nó giữ được luận điểm tương đương target — vốn được chứng minh trên phán quyết gate và trạng thái GPIO, không phải trên chất lượng thoại — đồng thời giữ được mốc phát hành. Cái mất là sức thuyết phục của bản demo, vì video "nói chuyện với con chip $5" là tài sản phân phối mạnh nhất (§1.5 của proposal).

**Quyết định áp dụng bậc 5 phải đưa ra chậm nhất ở Tuần 9.** Muộn hơn thì vừa mất thoại vừa mất mốc.

---

## 9. Lịch chốt quyết định

Bảy quyết định mở của PRD §15, xếp theo thời điểm bắt buộc phải chốt.

| Tuần | Mã | Quyết định | Vì sao hạn đó | Người quyết |
|:---:|:---:|:---|:---|:---|
| **1** | **Q-2** | Bo mạch tham chiếu chính thức | **Phải đặt hàng ngay** — thời gian giao hàng có thể 2–4 tuần, chặn cả spike lẫn Sprint 4 | Kỹ thuật trưởng |
| **1** | Q-1 | Phiên bản Python tối thiểu | Quyết định cú pháp và thư viện dùng được, ảnh hưởng ngay dòng mã đầu tiên | Kỹ thuật trưởng |
| **2** | Q-4 | Danh sách nhà cung cấp `SystemOne` hỗ trợ ở v1.0 | Cần trước khi viết interface và bộ kiểm thử | Sản phẩm |
| **4** | Q-3 | Ngân sách SRAM/PSRAM và kích thước firmware | Chốt **sau** khi có số liệu spike, trước khi lập phạm vi Sprint 5 | Kỹ sư nhúng |
| **5** | Q-7 | Từ khóa kích hoạt mặc định và ngôn ngữ hỗ trợ | Cần trước khi chọn mô hình wake-word cho Sprint 5 | Sản phẩm |
| **Tháng 3** | Q-5 | Xác thực và chống lạm dụng cho Registry công khai | Cần trước khi thiết kế hạ tầng Khối 3 | Kỹ thuật nền tảng |
| **Tháng 3** | Q-6 | Chính sách lưu trữ vết ghi: thời hạn và hạn mức | Ảnh hưởng chi phí vận hành và cam kết SLA | Sản phẩm |

**Q-2 được đẩy lên Tuần 1** so với PRD (vốn ghi "trước Tuần 6"). Lý do thuần túy vận hành: bo mạch phải có trong tay trước khi spike bắt đầu, và thời gian mua sắm không nằm dưới quyền kiểm soát của đội.

---

## 10. Nhịp vận hành

### 10.1 Nhịp định kỳ

| Tần suất | Hoạt động | Từ tuần |
|:---|:---|:---:|
| Hằng ngày | Đồng bộ ngắn 15 phút | 0 |
| Hằng tuần | Demo chạy thật — **trên phần cứng thật từ Tuần 6** | 2 |
| Hằng tuần | Rà soát chỉ báo sớm §11 | 2 |
| Hằng đêm | Kiểm thử tự động trên bo mạch thật | 8 |
| Cuối mỗi sprint | Nghiệm thu theo tiêu chí ra, không nghiệm thu theo cảm nhận | 2 |

### 10.2 Định nghĩa hoàn thành

Một hạng mục chỉ được coi là hoàn thành khi đủ **cả năm** điều kiện:

| # | Điều kiện |
|:---:|:---|
| 1 | Mã đã review và hợp nhất |
| 2 | Có kiểm thử tự động chạy trong CI, bao gồm ít nhất một ca thất bại |
| 3 | Tiêu chí nghiệm thu của yêu cầu PRD tương ứng đã đạt và ghi nhận |
| 4 | Tài liệu và `--help` cập nhật |
| 5 | Thông báo lỗi liên quan nêu đủ ba thành phần: sai ở đâu, vì sao, xử lý thế nào |

### 10.3 Quy tắc bảo vệ đường găng

| Quy tắc | Nội dung |
|:---|:---|
| **Đóng băng lược đồ** | Sau Tuần 2, mọi thay đổi lược đồ cần RFC, phê duyệt và kịch bản di trú |
| **Không nợ kỹ thuật ở tầng an toàn** | Gate Engine và HAL không được hợp nhất kèm ghi chú "sẽ sửa sau" |
| **Sai lệch tương đương là lỗi chặn** | `TargetEquivalenceError` trong nightly dừng mọi việc khác cho tới khi xử lý xong |
| **Đóng băng tính năng trong Beta** | Không ngoại lệ ngoài lỗi chặn hành trình 10 phút |

---

## 11. Chỉ báo sớm và ngưỡng can thiệp

| # | Chỉ báo | Ngưỡng vàng | Ngưỡng đỏ | Hành động khi đỏ |
|:---:|:---|:---|:---|:---|
| **1** | Tiến độ Sprint 1 — đóng băng lược đồ | Chậm 3 ngày | Chậm 1 tuần | Cắt phạm vi lược đồ về mức tối thiểu chạy được; hoãn `choice` sang bản vá |
| **2** | Kết quả spike bộ nhớ | Còn dư dưới 30% ngân sách | **Không đủ chỗ cho voice pipeline** | Kích hoạt bậc 5 thang cắt ngay, không chờ Tuần 9 |
| **3** | Sai lệch `neuroedge verify` | 1 ca lệch | Từ 3 ca lệch trở lên | Dừng phát triển tính năng, truy nguyên gốc kiến trúc |
| **4** | Tiến độ Sprint 5 — thoại trên MCU | Tuần 9 chưa có vòng lặp thoại hoàn chỉnh | Tuần 10 chưa có | Kích hoạt bậc 5 |
| **5** | Số người dùng Beta ngoài đội | Tuần 14 dưới 25 người | Tuần 14 dưới 10 người | Dừng tuyển thêm, phỏng vấn sâu 10 người đã thử để tìm điểm nghẽn |
| **6** | Tỷ lệ B2 — nạp phần cứng thật | Dưới 20% của B1 | Dưới 10% của B1 | Điều tra đường lên phần cứng; đây là chỉ báo sớm của nhánh C |
| **7** | Tỷ lệ áp dụng Action CI | Dưới 40% | Dưới 25% | Xem lại scaffold và tài liệu: Action CI chưa được đặt làm trung tâm |

**Nguyên tắc đọc bảng:** ngưỡng vàng kích hoạt thảo luận trong buổi rà soát tuần. Ngưỡng đỏ kích hoạt hành động đã ghi sẵn, không thảo luận lại.

---

# Phụ lục

## Phụ lục A — Bảng mốc tổng hợp

| Mốc | Thời điểm | Nội dung | Cổng nghiệm thu |
|:---|:---:|:---|:---|
| Đóng băng lược đồ | Tuần 2 | Gate v1, trace v1, hợp đồng HAL | Tiêu chí ra Sprint 1 |
| Lõi chạy trên `sim` | Tuần 4 | Gate Engine, fail-closed, `@action` | Tiêu chí ra Sprint 2 |
| **Kết thúc Khối 1a** | **Tuần 6** | Action CI, `linux`, CLI, TTFV | A1 nội bộ, A2 một phần, A3, A4, A5, A7 |
| Tương đương 3 target | Tuần 8 | `esp32s3` chạy gate và GPIO | **A2 đầy đủ** trên miền phán quyết |
| Thoại trên MCU | Tuần 10 | Voice runtime tối ưu bộ nhớ | Tiêu chí ra Sprint 5 |
| **Phát hành v1.0** | **Tuần 12** | OTA, bảo mật thiết bị, tài liệu | **Toàn bộ A1–A9** |
| Kết thúc Beta | Tuần 16 | 50–100 lập trình viên ngoài | B1–B5 |
| **Điểm rẽ** | **Tuần 16** | Chọn nhánh A, B hoặc C | §6 |
| Gateway hoàn chỉnh | Tháng 6 | Định tuyến, failover, vết ghi đồng nhất | C7 |
| **Phát hành v1.1** | **Tháng 8** | Fleet OS, OTA canary, Registry | **Toàn bộ C1–C7** |

## Phụ lục B — Danh mục mua sắm và hạ tầng

Cần chuẩn bị trước Tuần 1 để không chặn đường găng.

| Hạng mục | Số lượng | Cần trước | Ghi chú |
|:---|:---:|:---:|:---|
| Bo mạch tham chiếu ESP32-S3 | 5–8 | **Tuần 1** | Chốt ở Q-2; dư ra cho nightly runner và bo mạch hỏng |
| Mảng micro 2 kênh có AEC | 3 | Tuần 1 | Phục vụ spike và Sprint 5 |
| Raspberry Pi 5 | 2 | Tuần 3 | Target `linux` trên ARM64 |
| Máy Linux x86-64 | 1 | Tuần 3 | Target `linux` trên x86, có thể dùng máy ảo |
| Mạch nạp và cáp JTAG | 2 bộ | Tuần 1 | Gỡ lỗi cấp thanh ghi |
| Runner CI tự quản có gắn bo mạch thật | 1 | **Tuần 6** | Bắt buộc cho nightly từ Tuần 8 |
| Tên miền và hạ tầng cho `schema.neuroedge.dev` | — | Tuần 10 | Phục vụ FR-GOV-01 và A9 |
| Máy chủ Discord và kho GitHub công khai | — | Tuần 10 | Phục vụ giai đoạn Beta |

---

*Hết tài liệu*
