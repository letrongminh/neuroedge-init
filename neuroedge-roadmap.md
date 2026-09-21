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

---

## 1. Giả định nguồn lực

> **Đây là giả định, không phải dữ kiện.** Toàn bộ lịch trình bên dưới phụ thuộc vào nó. Nếu cấu hình đội khác đi, xem §1.3 trước khi đọc tiếp.

### 1.1 Bốn vai trò bắt buộc


| Vai trò                                   | Trách nhiệm chính                                                       | Có mặt từ                           |
| :----------------------------------------- | :----------------------------------------------------------------------- | :-----------------------------------: |
| **V1 — Kỹ sư lõi nền tảng**               | HAL, Action Contract Engine, lược đồ gate và trace, Action CI           | Tuần 0                              |
| **V2 — Kỹ sư nhúng**                      | Port `esp32s3`, runtime thoại trên MCU, OTA cấp thiết bị, tối ưu bộ nhớ | Tuần 0 *(bán thời gian tới Tuần 6)* |
| **V3 — Kỹ sư trải nghiệm lập trình viên** | Giao diện `sim`, CLI, scaffold, tài liệu, ví dụ mẫu                     | Tuần 2                              |
| **V4 — Kỹ sư hạ tầng dịch vụ**            | Gateway, Fleet OS, Registry, hệ đo lường                                | Tháng 3                             |


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
                                      └──► Port esp32s3 ────────────────┴──► verify 3 target
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
| 5   | Runtime thoại trên MCU          | 8–10 | Mắt xích rủi ro nhất; xem §9                                                                                  |


**Đòn bẩy mã nguồn mở trên đường găng:** mắt xích 2 rút ngắn nhờ Google CEL, mắt xích 4 nhờ driver XiaoZhi, mắt xích 5 nhờ Pipecat và bộ mô hình âm thanh. Chi tiết và mức rút ngắn thực tế tại §3.7.

**Không nằm trên đường găng, làm song song:** giao diện `sim`, CLI, tài liệu, ví dụ mẫu, hạ tầng CI.

### 2.3 Quy tắc đóng băng lược đồ

Từ **cuối Tuần 2**, mọi thay đổi đối với lược đồ gate hoặc lược đồ vết ghi bắt buộc:

1. Có đề xuất RFC viết ra, nêu rõ lý do và ảnh hưởng tương thích ngược
2. Được kỹ thuật trưởng phê duyệt
3. Kèm kịch bản di trú cho toàn bộ vết ghi đã tồn tại

Đây là quy tắc nghiêm ngặt nhất của toàn bộ dự án. Lược đồ trôi nổi làm sụp đổ mệnh đề trung tâm.

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

| Ràng buộc | Nội dung |
|:---|:---|
| **P-1** | Mọi lệnh tới cơ cấu chấp hành đi qua gate |
| **P-2** | Ba môi trường thực thi ngang hàng |
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
| **2** | Hosted Inference Gateway | LiteLLM Proxy | Dịch vụ backend | 6 tuần |
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
| 4 | **LiteLLM** | Lõi Hosted Gateway | Chuyển đổi I/O về một chuẩn chung · cân bằng tải · failover · hạn mức theo khóa định danh |
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

Quyết định Q-8 (§10) chọn **C/C++ trên ESP-IDF cho firmware** và **Python cho `sim` và `linux`**. Hệ quả: máy trạng thái hội thoại **buộc phải có hai hiện thực**. Không thể chia sẻ mã giữa hai bên.

Điều này va thẳng vào P-2. FR-PER-02 yêu cầu barge-in thu hồi lệnh actuator chưa thực thi — nghĩa là hành vi cắt lời rò trực tiếp vào miền hành động vật lý. Hai hiện thực barge-in khác nhau cho ra hai hành vi thu hồi khác nhau.

**Giải pháp bắt buộc: một đặc tả chuẩn tắc, hai hiện thực tuân thủ, một bộ kiểm thử tuân thủ dùng chung.**

| # | Thành phần | Nội dung | Sprint |
|:---:|:---|:---|:---:|
| 1 | **Đặc tả máy trạng thái** | Văn bản chuẩn tắc mô tả trạng thái, chuyển tiếp, và điều kiện thu hồi lệnh actuator. Là nguồn sự thật duy nhất, không phải mã Python | Sprint 2 |
| 2 | **Bộ vector kiểm thử tuân thủ** | Tập tệp vết ghi đầu vào kèm chuỗi phán quyết và trạng thái GPIO kỳ vọng, độc lập với ngôn ngữ | Sprint 3 |
| 3 | **Hiện thực Python** | Cho `sim` và `linux`, port thiết kế từ Pipecat | Sprint 3 |
| 4 | **Hiện thực C/C++** | Cho `esp32s3`, port driver từ XiaoZhi | Sprint 5 |
| 5 | **`neuroedge verify` chạy bộ vector trên cả ba target** | Lệch nhau sinh `TargetEquivalenceError` | Sprint 4–5 |

**Không có bước 1 và 2 thì việc port Pipecat là một rủi ro, không phải một đòn bẩy.** Đặc tả và bộ vector phải có trước khi viết hiện thực thứ hai.

#### Hệ quả tương tự với CEL

Nếu `allow_when` dùng Google CEL, thì gate phải lượng giá được **trên cả vi điều khiển**, vì gate chạy on-device và fail-closed khi mất mạng. `cel-python` không chạy trên ESP32-S3.

Ba phương án, cần chốt tại Q-9:

| Phương án | Nội dung | Đánh giá |
|:---|:---|:---|
| **A. Biên dịch gate lúc build** | Host dịch biểu thức CEL thành dạng quyết định tất định; thiết bị lượng giá dạng đã biên dịch | **Khuyến nghị** — giữ một nguồn sự thật, hai bên lượng giá cùng một artifact, và củng cố luôn câu chuyện golden |
| B. Bộ lượng giá CEL rút gọn bằng C | Tự viết evaluator cho tập con CEL | Thêm một hiện thực cần giữ đồng bộ |
| C. CEL trên host, biểu thức đơn giản trên thiết bị | Hai cú pháp khác nhau | **Bác bỏ** — phá tương đương target ở đúng tầng an toàn |

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


| Hạng mục                                                                     | Yêu cầu PRD                        | Người |
| :---------------------------------------------------------------------------- | :---------------------------------- | :-----: |
| Đặc tả 5 nguyên thủy HAL và thuộc tính đối chiếu                             | FR-HAL-01, FR-HAL-02, FR-HAL-03    | V1    |
| Lược đồ gate v1: 8 trường, 3 kiểu `evaluate`, 4 hành vi `on_block`, `budget` | FR-GATE-02, FR-GATE-03, FR-GATE-04 | V1    |
| Quy tắc kế thừa `extends`: 5 nguyên tắc an toàn                              | FR-GATE-06, FR-GATE-07, FR-GATE-08 | V1    |
| Lược đồ vết ghi v1: 6 nhóm sự kiện, khối `metadata`                          | FR-TRC-01, FR-TRC-02, FR-TRC-03    | V1    |
| Ma trận giấy phép và tệp `NOTICE` cho toàn bộ dự án sẽ port (§3.9) | — | V2 |
| **Spike khả thi bộ nhớ trên ESP32-S3**                                       | NFR-RES-01, NFR-RES-02             | V2    |
| Rà soát thiết kế HAL dưới ràng buộc MCU                                      | —                                  | V2    |
| Dựng kho mã, CI cơ bản, quy ước đóng góp                                     | —                                  | V1    |


**Đòn bẩy OSS Sprint 1:** Pydantic v2 và `rfc8785` cho chuẩn hóa lược đồ · Typer, Rich, Copier cho khung CLI ban đầu. Tiết kiệm ước tính 3 tuần công sức viết mã.

**Nội dung spike bộ nhớ:** nạp thử AEC + VAD + Opus streaming lên bo mạch tham chiếu, đo dung lượng SRAM/PSRAM còn lại sau khi trừ ngăn xếp mạng và hệ điều hành. Kết quả là **một con số**, không phải một nhận định.

**Tiêu chí ra Sprint 1:**


| #   | Tiêu chí                                                                                             |
| :---: | :---------------------------------------------------------------------------------------------------- |
| 1   | JSON Schema của gate và trace publish nội bộ, có ví dụ hợp lệ và ví dụ sai kèm thông báo lỗi kỳ vọng |
| 2   | Ba gate mẫu viết tay được công cụ phân giải đúng, gồm một trường hợp kế thừa 2 cấp                   |
| 3   | Báo cáo spike bộ nhớ có số liệu đo thực, kèm khuyến nghị phạm vi cho Khối 1b                         |
| 4   | Quyết định Q-1, Q-2, Q-4 đã chốt (§10)                                                                |


### 4.2 Sprint 2 — Lõi thực thi trên `sim` (Tuần 2–4)


| Hạng mục                                                        | Yêu cầu PRD                                | Người            |
| :--------------------------------------------------------------- | :------------------------------------------ | :----------------: |
| Hiện thực HAL cho target `sim`                                  | FR-TGT-01, FR-HAL-01                       | V1               |
| Đối chiếu năng lực lúc build, thông báo lỗi đầy đủ 3 thành phần | FR-HAL-04, FR-HAL-05, FR-DX-04             | V1               |
| Gate Engine: `evaluate`, `allow_when`, `on_block`, `budget`     | FR-GATE-03, FR-GATE-04, FR-GATE-09         | V1               |
| Cơ chế fail-closed và mạch ngắt suy giảm                        | FR-ACE-03, NFR-REL-02                      | V1               |
| Decorator `@action`, cấm gọi trực tiếp, `c.do()` và `c.say()`   | FR-ACE-02, FR-ACE-04, FR-ACE-05, FR-ACE-07 | V1               |
| Lượng giá `allow_when` trên nền Google CEL, kèm đường biên dịch gate cho thiết bị (§3.8, Q-9) | FR-GATE-03 | V1 |
| **Đặc tả chuẩn tắc máy trạng thái hội thoại** — nguồn sự thật cho cả hai hiện thực (§3.8) | FR-PER-02, FR-PER-03 | V1 |
| Interface `SystemOne` / `SystemTwo` kèm fallback                | FR-MDL-01, FR-MDL-02, FR-MDL-03            | V1               |
| Giao diện web `sim`: cảm biến ảo, trạng thái actuator           | FR-TGT-06                                  | V3               |
| Kết luận phạm vi Khối 1b dựa trên spike                         | —                                          | V2 + trưởng nhóm |


**Tiêu chí ra Sprint 2:**


| #   | Tiêu chí                                                                              |
| :---: | :------------------------------------------------------------------------------------- |
| 1   | Agent mẫu chạy trên `sim`, gate chặn đúng theo `allow_when`                           |
| 2   | Gọi trực tiếp hành động vật lý ném `ActionContractViolation`, chân GPIO ảo không kích |
| 3   | Kịch bản mất mạng → hành động bị chặn với lý do `gate_unreachable`                    |
| 4   | Gate con nới lỏng `allow_when` bị từ chối phân giải                                   |
| 5   | Quyết định Q-3, Q-7 đã chốt                                                           |


### 4.3 Sprint 3 — Action CI, `linux` và TTFV (Tuần 4–6)


| Hạng mục                                                                        | Yêu cầu PRD             | Người |
| :------------------------------------------------------------------------------- | :----------------------- | :-----: |
| Record: ghi phiên ra tệp JSON hợp lệ                                            | FR-CI-01                | V1    |
| Replay trên target bất kỳ                                                       | FR-CI-02                | V1    |
| Thư viện assert: chặn, gate nào, leo thang, chân cấm kích                       | FR-CI-03                | V1    |
| Golden Reference và so khớp chuỗi phán quyết                                    | FR-CI-04                | V1    |
| Hiện thực HAL cho target `linux` qua `gpiod`                                    | FR-TGT-02               | V1    |
| CLI đầy đủ: `new`, `run`, `build`, `test`, `record`, `replay`, `trace validate` | FR-CLI-01→04, FR-TRC-08 | V3    |
| Scaffold `neuroedge new` có sẵn action, gate, test                              | FR-DX-01                | V3    |
| Ba ví dụ mẫu chạy được, README có tài sản trực quan                             | FR-DX-05, FR-DX-06      | V3    |
| Telemetry CLI ẩn danh, có thể tắt                                               | FR-TEL-01, FR-TEL-02    | V3    |
| **Bộ vector kiểm thử tuân thủ độc lập ngôn ngữ** cho máy trạng thái hội thoại (§3.8) | FR-CI-07, FR-TGT-04 | V1 |
| Hiện thực Python của máy trạng thái hội thoại, port thiết kế từ Pipecat | FR-PER-02→05 | V1 |
| Pipeline CI mẫu chạy `sim` + `linux` trên mỗi PR                                | FR-CI-05                | V1    |


**Tiêu chí ra Sprint 3 — cổng kết thúc Khối 1a:**


| #   | Tiêu chí                                                                | Tham chiếu                 |
| :---: | :----------------------------------------------------------------------- | :--------------------------: |
| 1   | TTFV đo thử nội bộ trên **3 người ngoài đội** đạt trung vị dưới 10 phút | A1 *(đo đầy đủ ở Tuần 12)* |
| 2   | `neuroedge verify --targets sim,linux` đạt 100%                         | A2 *(một phần)*            |
| 3   | Không tồn tại đường tắt kích hoạt GPIO bỏ qua gate                      | A3                         |
| 4   | 100% kịch bản suy giảm đều chặn hành động                               | A4                         |
| 5   | Bộ kiểm thử kế thừa gate đạt 100%                                       | A5                         |
| 6   | 100% phiên sinh vết ghi qua được `neuroedge trace validate`             | A7                         |


---

## 5. Khối 1b — Vi điều khiển biên (Tuần 6–12)

**Mục tiêu khối:** chứng minh nguyên tắc tương đương môi trường trên vi điều khiển $5, với độ ổn định sản xuất.

### 5.1 Sprint 4 — HAL trên `esp32s3` (Tuần 6–8)

Sprint này **cố tình chưa làm thoại**. Mục đích là chứng minh tương đương target trên miền quyết định trước, khi biến số còn ít.


| Hạng mục                                                     | Yêu cầu PRD          | Người   |
| :------------------------------------------------------------ | :-------------------- | :-------: |
| Port 5 nguyên thủy HAL lên ESP-IDF                           | FR-TGT-03, FR-HAL-01 | V2      |
| Gate Engine chạy trên MCU                                    | FR-ACE-01, FR-ACE-03 | V2 + V1 |
| Đường dẫn `digital.out` và `sensor.read` trên phần cứng thật | FR-HAL-06, FR-HAL-07 | V2      |
| Lệnh `neuroedge verify` cho cả 3 target                      | FR-CI-07, FR-TGT-04  | V1      |
| Runner kiểm thử nightly trên bo mạch thật                    | FR-CI-06, NFR-REL-03 | V3      |


**Đòn bẩy OSS Sprint 4:** ESP-IDF làm toolchain · port driver bo mạch từ XiaoZhi vào `targets/esp32s3/drivers/` (codec I2S ES8311/ES7210, chân I2C/SPI của Box-3, LCD ST7789) · LVGL cho hiển thị trạng thái. Tiết kiệm ước tính 7 tuần, trong đó 2–3 tuần nằm trên đường găng.

**Tiêu chí ra Sprint 4:**


| #   | Tiêu chí                                                                                                                    |
| :---: | :--------------------------------------------------------------------------------------------------------------------------- |
| 1   | `neuroedge verify --targets sim,linux,esp32s3` đạt 100% trên kịch bản **không dùng audio** → **A2 đạt cho miền phán quyết** |
| 2   | Sai lệch phán quyết giữa các target sinh `TargetEquivalenceError` chỉ rõ sự kiện lệch đầu tiên                              |
| 3   | Nightly runner chạy tự động và gửi báo cáo                                                                                  |


### 5.2 Sprint 5 — Runtime thoại trên MCU (Tuần 8–10)

**Đây là sprint rủi ro nhất của toàn dự án.**


| Hạng mục                                                                            | Yêu cầu PRD                     | Người   |
| :----------------------------------------------------------------------------------- | :------------------------------- | :-------: |
| Tích hợp WebRTC AEC, Silero VAD, Opus streaming                                     | FR-PER-06                       | V2      |
| Port đường dẫn audio theo §3.5, tuân thủ nghĩa vụ ghi nhận nguồn §3.9 | FR-PER-01 | V2 |
| **Hiện thực C/C++ của máy trạng thái hội thoại** theo đặc tả Sprint 2, phải vượt bộ vector tuân thủ Sprint 3 (§3.8) | FR-PER-02, FR-PER-03, FR-PER-05 | V1 + V2 |
| Thu hồi lệnh actuator chưa thực thi khi bị cắt lời                                  | FR-PER-02                       | V1 + V2 |
| Tối ưu bộ nhớ theo ngân sách đã chốt ở Q-3                                          | NFR-RES-01, NFR-RES-02          | V2      |


**Ràng buộc kiến trúc bắt buộc:** máy trạng thái hội thoại chỉ có **một hiện thực duy nhất**, portable xuống MCU. Không được dùng một máy trạng thái cho `linux` và một máy trạng thái khác cho `esp32s3` — hai bản sẽ phân kỳ, và hành vi thu hồi lệnh actuator khi cắt lời sẽ khác nhau giữa các target, phá vỡ tương đương ở đúng miền nguy hiểm nhất.

**Đòn bẩy OSS Sprint 5:** microWakeWord trên MCU và openWakeWord trên Linux · Silero VAD và libfvad · WebRTC AEC3 · Opus · port mô hình frame processor và barge-in từ Pipecat. Tiết kiệm ước tính 4 tuần, phần lớn nằm trên đường găng.

**Ràng buộc bắt buộc:** hiện thực C/C++ này là bản thứ hai của cùng một đặc tả, không phải một thiết kế độc lập. Nó chỉ được nghiệm thu khi vượt toàn bộ bộ vector tuân thủ chung (§3.8).

**Tiêu chí ra Sprint 5:**


| #   | Tiêu chí                                                                 |
| :---: | :------------------------------------------------------------------------ |
| 1   | Vòng lặp thoại đầy đủ chạy trên bo mạch tham chiếu                       |
| 2   | Cắt lời giữa câu: TTS dừng dưới 300 ms, không có lệnh actuator nào rò rỉ |
| 3   | Bơm 20 khung nhiễu liên tiếp: máy trạng thái vẫn phản hồi đúng           |
| 4   | Bộ nhớ còn lại sau 4 giờ chạy nằm trong ngân sách Q-3                    |


### 5.3 Sprint 6 — OTA, ổn định hóa, nghiệm thu (Tuần 10–12)


| Hạng mục                                              | Yêu cầu PRD              | Người |
| :----------------------------------------------------- | :------------------------ | :-----: |
| OTA cấp thiết bị: phân vùng kép A/B                   | FR-OTA-01                | V2    |
| Tự động rollback khi phát hiện vòng lặp khởi động     | FR-OTA-02                | V2    |
| Xác minh chữ ký firmware trên chip                    | FR-OTA-03                | V2    |
| Nạp firmware từ HTTP endpoint mở bất kỳ               | FR-OTA-04                | V2    |
| Secure boot, mã hóa flash, nút ngắt micro vật lý      | NFR-SEC-02, NFR-SEC-03   | V2    |
| Kiểm thử chịu tải 24 giờ                              | NFR-RES-01, A6           | V3    |
| Publish JSON Schema công khai và bộ kiểm thử tuân thủ | FR-GOV-01, FR-GOV-03, A9 | V1    |
| Hoàn thiện tài liệu, ví dụ, video minh họa            | FR-DX-05, FR-DX-06, A8   | V3    |


**Đòn bẩy OSS Sprint 6:** `esp_https_ota` và `esp_ota_ops` của ESP-IDF cho cập nhật phân vùng kép A/B và rollback cục bộ. Tiết kiệm ước tính 2 tuần.

**Tiêu chí ra Sprint 6 — cổng phát hành v1.0:** đạt **toàn bộ A1 đến A9** của PRD §11.1. Không chấp nhận đạt một phần.

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


| Mã     | Chỉ số                                                | Ngưỡng                | Nguồn       |
| :------: | :----------------------------------------------------- | :--------------------- | :----------- |
| **B1** | Lập trình viên ngoài chạy thành công agent trên `sim` | ≥ 50                  | FR-TEL-01   |
| **B2** | Lập trình viên ngoài nạp thành công phần cứng thật    | ≥ 10                  | FR-TEL-01   |
| **B3** | Gate do cộng đồng tự viết và đóng góp                 | ≥ 3                   | Registry    |
| **B4** | Tỷ lệ giữ lại và mở rộng test gate mặc định           | ≥ 50%                 | FR-TEL-01   |
| **B5** | Tỷ lệ chuyển đổi `sim` → phần cứng trong 30 ngày      | ≥ 15%                 | FR-TEL-01   |
| **A1** | TTFV đo đầy đủ trên 10 người độc lập                  | Trung vị &lt; 10 phút | Biên bản đo |


---

## 7. Điểm rẽ quyết định Tuần 16

Kết thúc Beta, dự án đi theo đúng một trong ba nhánh. **Quyết định dựa trên số liệu B1–B5, không dựa trên cảm nhận về đà phát triển.**


| Nhánh                               | Điều kiện                                                | Hành động                                                                                                               |
| :----------------------------------- | :-------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------- |
| **Nhánh A — Khởi động Khối 2**      | Đạt đồng thời B1, B2, B3                                 | Tuyển V4, bắt đầu Gateway và Fleet OS theo §8                                                                           |
| **Nhánh B — Kéo dài Beta 4–6 tuần** | Đạt 2 trên 3 tiêu chí, tiêu chí còn lại đạt ≥ 60% ngưỡng | Giữ đóng băng tính năng, tập trung vào tiêu chí yếu nhất, đánh giá lại ở Tuần 22                                        |
| **Nhánh C — Xem xét lại luận điểm** | Không đạt hoặc chỉ đạt 1 trên 3                          | Dừng lộ trình thương mại. Phỏng vấn sâu 20 người dùng đã thử và bỏ. Xác định luận điểm sai ở đâu trước khi viết thêm mã |


**Chỉ báo quan trọng nhất là B2** (10 người ngoài nạp được phần cứng thật). B1 đo sự tò mò; B2 đo cam kết. Một dự án có B1 cao nhưng B2 thấp là một dự án mà simulator hấp dẫn còn đường lên phần cứng bị nghẽn — khi đó việc cần làm là sửa đường lên phần cứng, không phải xây Gateway.

---

## 8. Khối 2 và 3 — Tầng dịch vụ (Tháng 4–8)

Khởi động **chỉ khi** đi nhánh A. Hai khối chạy song song.

### 8.1 Trình tự Khối 2 — Gateway và Fleet OS


| Tháng   | Trọng tâm                                                                | Yêu cầu PRD          | Tiêu chí ra                                       |
| :-------: | :------------------------------------------------------------------------ | :-------------------- | :------------------------------------------------- |
| **4**   | Gateway: một endpoint, một credential, xoay khóa từ xa                   | FR-GW-01, FR-GW-02   | Thiết bị không lưu API key bên thứ ba             |
| **5**   | Gateway: định tuyến đa nhà cung cấp, failover, hạn mức theo thiết bị     | FR-GW-03, FR-GW-05   | Ngắt nhà cung cấp chính, thiết bị không gián đoạn |
| **5–6** | Gateway: giao thức tối ưu edge, xuất vết ghi đồng nhất định dạng         | FR-GW-04, FR-GW-07   | Vết ghi từ Gateway replay được trên máy cá nhân   |
| **6**   | Fleet: cấp phát danh tính và chứng chỉ thiết bị                          | FR-FLT-01            | Claim tự động trên lô 100 thiết bị                |
| **6–7** | Fleet: sổ kiểm kê, giám sát sức khỏe, dashboard hữu ích ở n = 1          | FR-FLT-03, FR-FLT-06 | Trạng thái phản ánh đúng trong 60 giây            |
| **7**   | Fleet: cập nhật cấu hình, bí mật và gate từ xa                           | FR-FLT-04            | Đổi ngưỡng gate toàn đội, không nạp lại firmware  |
| **7–8** | Fleet: điều phối OTA canary 1% → 10% → 100%, tự dừng khi vượt ngưỡng lỗi | FR-FLT-02            | **1.000 thiết bị / 0 brick**                      |
| **8**   | Fleet: tự động tải vết ghi sự cố về kho tập trung                        | FR-FLT-05            | Sự cố xuất hiện trong kho dưới 5 phút             |


**Đòn bẩy OSS Khối 2:** LiteLLM Proxy làm lõi Hosted Gateway (chỉ dùng phần MIT, bọc middleware xác thực thiết bị viết riêng) · Eclipse Hawkbit cho điều phối chiến dịch OTA canary · EMQX hoặc FastAPI WebSockets cho kết nối và viễn trắc. Tiết kiệm ước tính 14 tuần. Xem ngoại lệ giấy phép tại §3.3.

### 8.2 Trình tự Khối 3 — Đường ray hạ tầng


| Tháng   | Thành phần                                             | Yêu cầu PRD          |
| :-------: | :------------------------------------------------------ | :-------------------- |
| **4**   | Định danh ổn định cho thiết bị, agent, gate            | FR-REG-05            |
| **4–5** | Hệ đo lường theo lượt gọi agent và lượt thẩm định gate | FR-REG-06, FR-TEL-04 |
| **5**   | Manifest và chuẩn phiên bản SemVer                     | FR-REG-02            |
| **5–6** | Kho Gate công khai miễn phí                            | FR-REG-01            |
| **6–7** | Cơ chế phân quyền và sandbox                           | FR-REG-07            |


**Thứ tự này không tùy tiện.** FR-REG-05, FR-REG-06 và FR-REG-07 phải đi trước vì không bổ sung sau được: thiếu định danh ổn định và đo lường thì Registry không quy kết được ai dùng gì; thiếu sandbox thì không dám cho mã người lạ chạy trên thiết bị có cơ cấu chấp hành.

**Đòn bẩy OSS Khối 3:** CNCF ORAS và Harbor cho kho Gate Registry theo chuẩn OCI · OpenMeter cho hệ đo lường tương thích Stripe Billing. Tiết kiệm ước tính 8 tuần.

### 8.3 Tiêu chí ra Khối 2 và 3

Toàn bộ C1 đến C7 của PRD §11.3.

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

Bảy quyết định mở của PRD §15, cộng bốn quyết định phát sinh từ chiến lược tái sử dụng mã nguồn mở (§3), xếp theo thời điểm bắt buộc phải chốt.


| Tuần        | Mã      | Quyết định                                        | Vì sao hạn đó                                                                            | Người quyết       |
| :-----------: | :-------: | :------------------------------------------------- | :---------------------------------------------------------------------------------------- | :----------------- |
| **1**       | **Q-2** | Bo mạch tham chiếu chính thức                     | **Phải đặt hàng ngay** — thời gian giao hàng có thể 2–4 tuần, chặn cả spike lẫn Sprint 4 | Kỹ thuật trưởng   |
| **1**       | Q-1     | Phiên bản Python tối thiểu                        | Quyết định cú pháp và thư viện dùng được, ảnh hưởng ngay dòng mã đầu tiên                | Kỹ thuật trưởng   |
| **2**       | Q-4     | Danh sách nhà cung cấp `SystemOne` hỗ trợ ở v1.0  | Cần trước khi viết interface và bộ kiểm thử                                              | Sản phẩm          |
| **4**       | Q-3     | Ngân sách SRAM/PSRAM và kích thước firmware       | Chốt **sau** khi có số liệu spike, trước khi lập phạm vi Sprint 5                        | Kỹ sư nhúng       |
| **5**       | Q-7     | Từ khóa kích hoạt mặc định và ngôn ngữ hỗ trợ     | Cần trước khi chọn mô hình wake-word cho Sprint 5                                        | Sản phẩm          |
| **1** | **Q-8** | Ngôn ngữ lõi firmware ESP32-S3 | Quyết định có hay không hai hiện thực máy trạng thái (§3.8). Khuyến nghị C/C++ trên ESP-IDF để thừa hưởng trọn vẹn driver XiaoZhi | Kỹ thuật trưởng |
| **2** | **Q-11** | Phê duyệt ngoại lệ giấy phép: Hawkbit EPL-2.0, EMQX BSL, LiteLLM enterprise | Chặn việc thiết kế phụ thuộc cho Khối 2. Phải xong trước khi port bất kỳ dòng nào (§3.3) | Kỹ thuật trưởng |
| **3** | **Q-9** | Cách lượng giá CEL trên vi điều khiển: biên dịch gate lúc build, evaluator C rút gọn, hay hai cú pháp | Quyết định kiến trúc Gate Engine. Khuyến nghị phương án A — biên dịch lúc build (§3.8) | Kỹ thuật trưởng |
| **Tháng 3** | **Q-10** | Mức độ phụ thuộc vào LiteLLM: proxy container nguyên bản hay tích hợp sâu | Ảnh hưởng khả năng thay thế và bề mặt bảo trì của Gateway | Kỹ thuật nền tảng |
| **Tháng 3** | Q-5     | Xác thực và chống lạm dụng cho Registry công khai | Cần trước khi thiết kế hạ tầng Khối 3                                                    | Kỹ thuật nền tảng |
| **Tháng 3** | Q-6     | Chính sách lưu trữ vết ghi: thời hạn và hạn mức   | Ảnh hưởng chi phí vận hành và cam kết SLA                                                | Sản phẩm          |


**Q-8 và Q-9 là hai quyết định nặng nhất.** Q-8 quyết định có tồn tại hai hiện thực máy trạng thái hay không; nếu có, đặc tả chuẩn tắc và bộ vector tuân thủ (§3.8) trở thành hạng mục bắt buộc của Sprint 2 và Sprint 3. Q-9 quyết định kiến trúc lượng giá của Gate Engine — tầng an toàn cốt lõi — nên không được để trôi quá Tuần 3.

**Q-2 được đẩy lên Tuần 1** so với PRD (vốn ghi "trước Tuần 6"). Lý do thuần túy vận hành: bo mạch phải có trong tay trước khi spike bắt đầu, và thời gian mua sắm không nằm dưới quyền kiểm soát của đội.

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
| Tương đương 3 target | Tuần 8      | `esp32s3` chạy gate và GPIO             | **A2 đầy đủ** trên miền phán quyết     |
| Thoại trên MCU       | Tuần 10     | Voice runtime tối ưu bộ nhớ             | Tiêu chí ra Sprint 5                   |
| **Phát hành v1.0**   | **Tuần 12** | OTA, bảo mật thiết bị, tài liệu         | **Toàn bộ A1–A9**                      |
| Kết thúc Beta        | Tuần 16     | 50–100 lập trình viên ngoài             | B1–B5                                  |
| **Điểm rẽ**          | **Tuần 16** | Chọn nhánh A, B hoặc C                  | §7                                     |
| Gateway hoàn chỉnh   | Tháng 6     | Định tuyến, failover, vết ghi đồng nhất | C7                                     |
| **Phát hành v1.1**   | **Tháng 8** | Fleet OS, OTA canary, Registry          | **Toàn bộ C1–C7**                      |


## Phụ lục B — Danh mục mua sắm và hạ tầng

Cần chuẩn bị trước Tuần 1 để không chặn đường găng.


| Hạng mục                                       | Số lượng | Cần trước  | Ghi chú                                              |
| :---------------------------------------------- | :--------: | :----------: | :---------------------------------------------------- |
| Bo mạch tham chiếu ESP32-S3                    | 5–8      | **Tuần 1** | Chốt ở Q-2; dư ra cho nightly runner và bo mạch hỏng |
| Mảng micro 2 kênh có AEC                       | 3        | Tuần 1     | Phục vụ spike và Sprint 5                            |
| Raspberry Pi 5                                 | 2        | Tuần 3     | Target `linux` trên ARM64                            |
| Máy Linux x86-64                               | 1        | Tuần 3     | Target `linux` trên x86, có thể dùng máy ảo          |
| Mạch nạp và cáp JTAG                           | 2 bộ     | Tuần 1     | Gỡ lỗi cấp thanh ghi                                 |
| Runner CI tự quản có gắn bo mạch thật          | 1        | **Tuần 6** | Bắt buộc cho nightly từ Tuần 8                       |
| Tên miền và hạ tầng cho `schema.neuroedge.dev` | —        | Tuần 10    | Phục vụ FR-GOV-01 và A9                              |
| Máy chủ Discord và kho GitHub công khai        | —        | Tuần 10    | Phục vụ giai đoạn Beta                               |


---

*Hết tài liệu*