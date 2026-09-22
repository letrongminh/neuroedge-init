# NeuroEdge — Product Requirements Document

## Nền tảng Hợp đồng Hành động Chuẩn kiểu cho Physical AI

**Phiên bản PRD:** 1.2
**Ngày phát hành:** 21 tháng 9, 2026
**Tài liệu nguồn:** `neuroedge-proposal.md` v5.4
**Trạng thái:** Bản thảo chờ phê duyệt kỹ thuật
**Đối tượng sử dụng:** Kỹ sư phát triển · Quản lý kỹ thuật · QA · Kỹ thuật viên tài liệu · Đối tác OEM

**Phạm vi tài liệu:** Yêu cầu chức năng và phi chức năng · Tiêu chí nghiệm thu · Đặc tả giao diện dữ liệu · Kế hoạch phát hành theo cột mốc · Hệ chỉ số và yêu cầu đo đạc
**Ngoài phạm vi:** Luận điểm chiến lược · Phân tích cạnh tranh · Mô hình tài chính (xem tài liệu nguồn)

---

## Mục lục

1. [Mục tiêu sản phẩm](#1-mục-tiêu-sản-phẩm)
2. [Người dùng và bối cảnh sử dụng](#2-người-dùng-và-bối-cảnh-sử-dụng)
3. [Phạm vi phát hành](#3-phạm-vi-phát-hành)
4. [Yêu cầu chức năng — Lõi thực thi](#4-yêu-cầu-chức-năng--lõi-thực-thi)
5. [Yêu cầu chức năng — An toàn hành động](#5-yêu-cầu-chức-năng--an-toàn-hành-động)
6. [Yêu cầu chức năng — Kiểm thử Action CI](#6-yêu-cầu-chức-năng--kiểm-thử-action-ci)
7. [Yêu cầu chức năng — Trải nghiệm lập trình viên](#7-yêu-cầu-chức-năng--trải-nghiệm-lập-trình-viên)
8. [Yêu cầu chức năng — Tầng dịch vụ thương mại](#8-yêu-cầu-chức-năng--tầng-dịch-vụ-thương-mại)
9. [Yêu cầu phi chức năng](#9-yêu-cầu-phi-chức-năng)
10. [Đặc tả giao diện dữ liệu](#10-đặc-tả-giao-diện-dữ-liệu)
11. [Tiêu chí nghiệm thu phát hành](#11-tiêu-chí-nghiệm-thu-phát-hành)
12. [Hệ chỉ số và yêu cầu đo đạc](#12-hệ-chỉ-số-và-yêu-cầu-đo-đạc)
13. [Phụ thuộc, rủi ro và giả định](#13-phụ-thuộc-rủi-ro-và-giả-định)
14. [Ngoài phạm vi](#14-ngoài-phạm-vi)
15. [Quyết định kỹ thuật đã chốt](#15-quyết-định-kỹ-thuật-đã-chốt)

**Phụ lục**

- [A — Ma trận truy vết yêu cầu](#phụ-lục-a--ma-trận-truy-vết-yêu-cầu)
- [B — Danh mục mã lỗi chuẩn](#phụ-lục-b--danh-mục-mã-lỗi-chuẩn)
- [C — Quy ước định danh và phiên bản](#phụ-lục-c--quy-ước-định-danh-và-phiên-bản)
- [D — Cấu trúc Monorepo và Giao thức Truyền dẫn](#phụ-lục-d--cấu-trúc-monorepo-và-giao-thức-truyền-dẫn)

---

## Quy ước tài liệu

| Ký hiệu | Ý nghĩa |
|:---|:---|
| **FR-xxx-nn** | Yêu cầu chức năng (Functional Requirement) |
| **NFR-xxx-nn** | Yêu cầu phi chức năng (Non-Functional Requirement) |
| **P0** | Bắt buộc — không đạt thì không phát hành |
| **P1** | Quan trọng — được phép trượt sang bản vá kế tiếp, phải có phương án tạm thời |
| **P2** | Mong muốn — thực hiện nếu còn nguồn lực |
| **§x.y** | Tham chiếu tới mục tương ứng trong `neuroedge-proposal.md` v5.4 |
| **§x.y của tài liệu này** | Tham chiếu nội bộ trong PRD — luôn viết kèm cụm *"của tài liệu này"* để không nhầm với tham chiếu proposal |
| **PF-1…PF-4** | Bộ lọc ưu tiên tính năng (`neuroedge-proposal.md` §2). **Khác** hệ mã rủi ro `R-n` |
| **R-1…R-7** | Rủi ro sản phẩm (§13.2 của tài liệu này). **Khác** bộ lọc `PF-n` |
| **A / B / C** | Tiêu chí nghiệm thu theo mốc: A = v1.0, B = Developer Beta, C = v1.1 (§11 của tài liệu này) |
| **Q-1…Q-13** | Sổ quyết định kỹ thuật (§15 của tài liệu này) — nguồn duy nhất; roadmap chỉ theo dõi trạng thái |

Từ khóa **BẮT BUỘC**, **NÊN**, **CÓ THỂ** được hiểu theo nghĩa của RFC 2119.

---

## 1. Mục tiêu sản phẩm

### 1.1 Vấn đề cần giải quyết

Chưa có công cụ nào kiểm thử được hành vi vật lý của AI agent **trước khi** thiết bị vận hành ngoài hiện trường. Khi một agent vật lý ra quyết định sai, động cơ đã quay, rơ-le đã đóng, chốt cửa đã mở — các tác động này là bất khả nghịch.

Ba câu hỏi mà công cụ hiện tại không trả lời được:

| # | Câu hỏi | Yêu cầu đáp ứng |
|:---:|:---|:---|
| 1 | Sau khi đổi prompt, agent còn từ chối mở khóa cho người chưa xác thực không? | §6 — Action CI với mẫu chuẩn Golden Reference |
| 2 | Khi đổi mô hình AI, phán quyết gate và tín hiệu GPIO có bị hồi quy không? | §6 — Assert trên phán quyết gate, không assert trên văn bản LLM |
| 3 | Cùng đầu vào, các môi trường có cho cùng phán quyết không? | §4 — Nguyên tắc tương đương môi trường |

### 1.2 Tuyên ngôn sản phẩm

> NeuroEdge chuẩn hóa mọi tác vụ vật lý của AI agent thành hợp đồng có kiểu, có phiên bản, kiểm thử tự động trong CI, và thực thi nhất quán trên mọi môi trường — từ laptop lập trình viên tới vi điều khiển biên $5.

### 1.3 Mục tiêu sản phẩm

| # | Mục tiêu | Chỉ số nghiệm thu |
|:---:|:---|:---|
| **M1** | Lập trình viên lạ chạy được agent có gate mà không cần mua phần cứng | TTFV trung vị < 10 phút trên 10 người dùng độc lập |
| **M2** | Mọi hành động vật lý đều đi qua một hợp đồng kiểm thử được | 100% lệnh actuator bị chặn nếu thiếu gate hợp lệ |
| **M3** | Cùng một mã nguồn agent chạy nhất quán trên mọi môi trường | `neuroedge verify` đạt 100% trên các target bậc 1: `sim`, `linux`, `esp32s3` |
| **M4** | Sự cố hiện trường tái hiện được trên máy lập trình viên | Tải vết ghi và replay thành công bằng một lệnh |
| **M5** | Đội vận hành cập nhật firmware quy mô lớn không mất thiết bị | 1.000 thiết bị / 0 sự cố brick |

### 1.4 Phi mục tiêu

| # | Phi mục tiêu | Lý do |
|:---:|:---|:---|
| **N1** | Không trở thành nhà cung cấp mô hình AI | Mô hình là thành phần thay thế được (§0.4 nguyên tắc 4) |
| **N2** | Không cạnh tranh độ sâu driver một dòng chip | Nhường cho SDK chính hãng (§10.3) |
| **N3** | Không theo đuổi độ phủ phần cứng rộng ở giai đoạn đầu | Ba môi trường bậc 1 đủ chứng minh tương đương. Từ Giai đoạn 2, độ phủ mở rộng qua phân tầng bậc (FR-TGT-08) chứ không qua việc đội lõi ôm thêm bo mạch (§9) |
| **N4** | Không bán lại token suy luận như nguồn biên lợi nhuận chính | Biên mỏng, cạnh tranh trực tiếp với model vendor (§0.4 nguyên tắc 3) |

### 1.5 Năm nguyên tắc thiết kế bất biến

Mọi yêu cầu trong tài liệu này phải tuân thủ năm nguyên tắc sau. Xung đột với bất kỳ nguyên tắc nào là căn cứ bác bỏ yêu cầu.

| # | Nguyên tắc | Hệ quả kỹ thuật ràng buộc |
|:---:|:---|:---|
| **P-1** | Hành động vật lý là hợp đồng chuẩn kiểu, không phải lời gọi hàm tự do | HAL từ chối mọi lệnh actuator thiếu chữ ký gate đã pass |
| **P-2** | Các môi trường thực thi ngang hàng | Không được rẽ nhánh logic theo target trong mã nguồn agent. Mức cam kết kiểm chứng phân theo ba bậc target (FR-TGT-08); hệ quả kỹ thuật này áp dụng như nhau ở mọi bậc |
| **P-3** | Giá trị tập trung ở quản trị đội thiết bị | Tính năng an toàn cốt lõi không được khóa sau tài khoản trả phí |
| **P-4** | Mô hình AI là thành phần thay thế được — cloud-first, provider-pluggable | Mọi truy cập mô hình đi qua interface `SystemOne` / `SystemTwo`; chuẩn kết nối mặc định là OpenAI API, provider không tương thích đi qua adapter tự viết; ASR và TTS cũng là provider thay thế được. Phần nặng xử lý ngôn ngữ chạy trên cloud/host, `esp32s3` chỉ thu/phát âm thanh và thẩm định gate |
| **P-5** | Hiệu ứng mạng từ chia sẻ chính sách an toàn và thành phần mở rộng | Gate là tệp dữ liệu có phiên bản, chia sẻ và kế thừa được. Adapter kết nối nhà cung cấp và bản port HAL là loại tài sản chia sẻ thứ hai; chúng là mã thực thi nên đi kèm cổng kiểm soát riêng — Bộ kiểm thử tuân thủ, sandbox phân quyền và đối chiếu năng lực lúc build |

---

## 2. Người dùng và bối cảnh sử dụng

### 2.1 Nhóm người dùng mục tiêu

| Mã | Nhóm | Bối cảnh | Nhu cầu cốt lõi | Ưu tiên |
|:---:|:---|:---|:---|:---:|
| **U1** | **Kỹ sư sáng chế độc lập (Maker)** | Làm thiết bị đầu tiên, chưa có phần cứng trong tay | Chạy thử ngay, không rào cản, không tài khoản | Chính |
| **U2** | **Trưởng nhóm kỹ thuật nhúng** | Đội 3–10 người, chuẩn bị đưa sản phẩm vào sản xuất | Kiểm thử an toàn tự động, chuyển board không viết lại mã | Chính |
| **U3** | **Kỹ sư vận hành đội thiết bị (Fleet Ops)** | Quản lý 100–10.000 thiết bị đã lắp đặt | Cập nhật an toàn, chẩn đoán từ xa, không mất thiết bị | Chính (từ v1.1) |
| **U4** | **Chuyên gia an toàn & QA** | Chịu trách nhiệm phê duyệt hành vi thiết bị | Điều kiện an toàn đọc được, nhật ký đối soát được | Phụ |
| **U5** | **Đối tác sản xuất phần cứng (OEM/ODM)** | Bán bo mạch, muốn kèm lớp agent | Tích hợp không khóa khách vào một dòng chip | Phụ |

### 2.2 Nhiệm vụ cần hoàn thành (Jobs To Be Done)

| Mã | Nhóm | Nhiệm vụ | Đáp ứng bởi |
|:---:|:---:|:---|:---|
| **J1** | U1 | "Tôi muốn thử một agent giọng nói ngay tối nay mà chưa có board" | FR-TGT-01, FR-DX-01 |
| **J2** | U2 | "Tôi cần chắc chắn bản cập nhật prompt không làm chốt cửa mở sai" | FR-CI-03, FR-CI-04 |
| **J3** | U2 | "Tôi cần chuyển từ RPi sang ESP32-S3 mà không viết lại logic" | FR-TGT-02, FR-HAL-01 |
| **J4** | U3 | "Một thiết bị ở villa lỗi, tôi cần biết chuyện gì đã xảy ra mà không phải tới nơi" | FR-CI-01, FR-FLT-05 |
| **J5** | U3 | "Tôi cần cập nhật 1.000 thiết bị mà không có nguy cơ hỏng hàng loạt" | FR-OTA-01, FR-FLT-02 |
| **J6** | U4 | "Tôi cần duyệt điều kiện mở khóa mà không đọc mã nguồn Python" | FR-GATE-01, FR-GATE-02 |
| **J7** | U2 | "Tôi muốn dùng lại chính sách an toàn người khác đã tinh chỉnh" | FR-GATE-05, FR-REG-01 |

### 2.3 Ba hành trình người dùng chính

#### Hành trình 1 — Mười phút đầu tiên (U1)

| Phút | Hành động | Phản hồi hệ thống kỳ vọng | Yêu cầu |
|:---:|:---|:---|:---|
| 0–1 | `pip install neuroedge` | Cài xong, không hỏi tài khoản, không hỏi API key | FR-DX-02 |
| 1–2 | `neuroedge new my-agent` | Sinh dự án mẫu có sẵn 1 action, 1 gate, 1 test | FR-DX-01 |
| 2–4 | `neuroedge run --target sim` | Mở UI web; nói vào mic laptop, thấy actuator ảo chuyển động | FR-TGT-01 |
| 4–6 | Sửa `allow_when` trong gate | Agent từ chối hành động, hiển thị nguyên nhân trong vết ghi | FR-ACE-02 |
| 6–8 | `neuroedge test` | CI xanh; phá điều kiện → CI đỏ, chỉ đích danh gate vi phạm | FR-CI-03 |
| 8–10 | `neuroedge run --target linux` | Cùng mã nguồn, chạy trên phần cứng thật | FR-TGT-02 |

**Ràng buộc bắt buộc:** trong toàn bộ hành trình này, hệ thống **KHÔNG ĐƯỢC** yêu cầu mua phần cứng, tạo tài khoản, hay nhập thông tin thanh toán.

#### Hành trình 2 — Từ sự cố hiện trường về máy lập trình viên (U3 → U2)

```text
Thiết bị tại hiện trường phát sinh cảnh báo
        │
        ▼
Fleet OS tự động tải tệp vết ghi JSON về kho tập trung      ← FR-FLT-05
        │
        ▼
Kỹ sư tải tệp về máy cá nhân
        │
        ▼
neuroedge trace validate traces/incidents/<session>.json     ← FR-CLI-04
        │
        ▼
neuroedge replay traces/incidents/<session>.json --target sim ← FR-CI-02
        │
        ▼
Tái hiện chính xác chuỗi phán quyết gate và tín hiệu GPIO
        │
        ▼
Bổ sung tệp vết ghi thành kịch bản hồi quy vĩnh viễn         ← FR-CI-03
```

#### Hành trình 3 — Mở rộng từ 1 lên 1.000 thiết bị (U2 → U3)

| Giai đoạn | Hành động | Yêu cầu chi phối |
|:---|:---|:---|
| 1 thiết bị | Nạp firmware thủ công, thiết bị ảo `sim` hiện trên Fleet Dashboard | FR-FLT-03 |
| 10 thiết bị | Cấp chứng chỉ tự động ở lần khởi động đầu | FR-FLT-01 |
| 100 thiết bị | Cập nhật gate và cấu hình từ xa, không nạp lại firmware | FR-FLT-04 |
| 1.000 thiết bị | Cập nhật OTA theo đợt canary 1% → 10% → 100%, tự dừng khi vượt ngưỡng lỗi | FR-FLT-02 |

---

## 3. Phạm vi phát hành

### 3.1 Ba mốc phát hành

| Mốc | Tên | Thời gian | Nội dung | Điều kiện khởi động |
|:---|:---|:---:|:---|:---|
| **v1.0** | Lõi mã nguồn mở | Tuần 0–12 | Khối 1a + Khối 1b | Không điều kiện |
| **v1.0-beta** | Developer Beta | Tuần 12–16 | Đóng băng tính năng, hỗ trợ 50–100 lập trình viên | v1.0 đạt toàn bộ tiêu chí §11.1 của tài liệu này |
| **v1.1** | Tầng dịch vụ thương mại | Tháng 4–8 | Khối 2 + Khối 3 | **Cột mốc định lượng** — xem §3.3 |
| **v2.0** | Giai đoạn 2 — thị giác và phủ rộng phần cứng | Tháng 9–24 | Khối V1a/V1b/V2/V3 + P1/P2 *(proposal §8.9)* | **2a:** RFC-0002 được phê duyệt · **2b:** nhu cầu camera đo được từ khách hàng AURA thật |

Khối 4 (AURA thực địa, tháng 8–14) và Khối 5 (Marketplace, tháng 18+) nằm ngoài phạm vi PRD này; chúng được đặc tả trong tài liệu sản phẩm riêng khi tới mốc. Giai đoạn 2 chạy **song song** Khối 4 và có kế hoạch thực thi riêng tại `neuroedge-roadmap-phase2.md`; PRD này chỉ đặc tả các hợp đồng mà Giai đoạn 2 phải tuân thủ (FR-TGT-08, FR-HAL-01), không đặc tả yêu cầu chi tiết của nó.

### 3.2 Nội dung từng mốc

| Nhóm yêu cầu | v1.0 Khối 1a<br>(Tuần 0–6) | v1.0 Khối 1b<br>(Tuần 6–12) | v1.1<br>(Tháng 4–8) |
|:---|:---:|:---:|:---:|
| HAL hợp đồng năng lực (FR-HAL) | ● | ● | — |
| Môi trường `sim` + `linux` (FR-TGT) | ● | — | — |
| Môi trường `esp32s3` (FR-TGT) | — | ● | — |
| Action Contract Engine (FR-ACE) | ● | — | — |
| Định dạng gate (FR-GATE) | ● | — | ◐ registry |
| Trừu tượng hóa mô hình (FR-MDL) | ● | — | — |
| Runtime nhận thức & hội thoại (FR-PER) | ◐ cơ bản | ● thu/phát + gate | — |
| Action CI (FR-CI) | ● | ◐ `verify` môi trường bậc 1 | — |
| Lược đồ vết ghi (FR-TRC) | ● | — | — |
| CLI (FR-CLI) | ● | ◐ bổ sung | — |
| Trải nghiệm lập trình viên (FR-DX) | ● | — | — |
| OTA cấp thiết bị (FR-OTA) | — | ● | — |
| Lớp trừu tượng provider (FR-GW) | ● | — | ◐ tối ưu |
| Fleet Management OS (FR-FLT) | — | — | ● |
| Đường ray hạ tầng (FR-REG) | — | — | ● |

**Chú thích:** ● hoàn thành trong mốc · ◐ hoàn thành một phần · — không thuộc mốc

### 3.3 Điều kiện kích hoạt v1.1

v1.1 **KHÔNG ĐƯỢC** khởi động theo lịch cố định. Chỉ khởi động khi giai đoạn Developer Beta đạt **đồng thời** cả ba tiêu chí:

| # | Tiêu chí | Ngưỡng |
|:---:|:---|:---|
| **B1** | Lập trình viên bên ngoài chạy thành công agent trên `sim` | ≥ 50 người |
| **B2** | Lập trình viên bên ngoài nạp và điều khiển thành công phần cứng thật | ≥ 10 người |
| **B3** | Gate an toàn do cộng đồng bên ngoài tự viết và đóng góp | ≥ 3 gate |

### 3.4 Đóng băng phạm vi Khối 1b

Các hạng mục sau **BẮT BUỘC** bị loại khỏi Khối 1b để bảo đảm độ ổn định bộ nhớ trên vi điều khiển. Đây là ràng buộc của **mốc v1.0**, không phải ràng buộc vĩnh viễn — trạng thái dài hạn của từng hạng mục xem §14 của tài liệu này.

| Hạng mục | Trạng thái trong v1.0 |
|:---|:---|
| Huấn luyện wake-word tùy biến | Không hỗ trợ — chỉ dùng wake-word pre-trained *"Hey Neuro"* |
| Độ phủ bo mạch | Duy nhất **một bo mạch tham chiếu chính thức**: **ESP32-S3-Box-3** (tích hợp sẵn màn hình LCD ST7789, dual-mic ES7210, loa ES8311, dock I/O; DevKitC chuyển thành bo mạch thứ cấp do cộng đồng duy trì) |
| Thị giác máy tính | Không thuộc phạm vi |
| Kết nối tới provider AI trên đám mây (LLM · ASR · TTS) | **Thuộc phạm vi v1.0** — là kiến trúc mặc định theo P-4 |
| Dịch vụ đám mây do NeuroEdge vận hành, hệ thống tài khoản NeuroEdge | Không thuộc phạm vi — người dùng tự vận hành lớp provider và tự giữ khóa |
| Jetson, Matter, HomeKit | Không thuộc phạm vi |
| Tinh chỉnh mô hình AI | Không thuộc phạm vi |

---

## 4. Yêu cầu chức năng — Lõi thực thi

### 4.1 Lớp trừu tượng phần cứng (FR-HAL)

HAL là hợp đồng kiểm tra hai chiều: bo mạch khai báo năng lực cung cấp, agent khai báo tài nguyên cần dùng, mọi điểm không tương thích bị phát hiện **tại thời điểm biên dịch**.

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-HAL-01** | Hệ thống cung cấp đúng 5 nguyên thủy phần cứng: `audio.in`, `audio.out`, `digital.out`, `sensor.read`, `display`. Tập nguyên thủy **đóng cho v1.x**; mở rộng chỉ qua RFC *(RFC-0002 đề xuất `vision.in` là nguyên thủy tùy chọn theo bo mạch cho Giai đoạn 2)* | P0 | Cả 5 nguyên thủy có hiện thực đầy đủ trên các môi trường bậc 1 | §3.3 |
| **FR-HAL-02** | Bo mạch khai báo năng lực qua tệp `board.toml` theo schema chuẩn | P0 | Tệp sai schema bị từ chối kèm thông báo chỉ rõ trường lỗi | §4.2 |
| **FR-HAL-03** | Agent khai báo yêu cầu năng lực qua khối `[requires]` trong `agent.toml` | P0 | Thiếu khối `[requires]` khi agent có hành động vật lý → build dừng | §4.3 |
| **FR-HAL-04** | Công cụ đối chiếu năng lực chạy **lúc build**, không lúc chạy | P0 | Bất tương thích làm `neuroedge build` thoát với mã lỗi khác 0, không sinh firmware | §4.9 |
| **FR-HAL-05** | Thông báo lỗi đối chiếu nêu rõ: năng lực thiếu, bo mạch cung cấp gì, vị trí mã nguồn gọi | P0 | Thông báo chứa đủ 3 thành phần và gợi ý cách xử lý | §4.9 |
| **FR-HAL-06** | Chân GPIO và cảm biến định danh bằng **tên logic**, không bằng số chân vật lý | P0 | Đổi bo mạch chỉ cần sửa `board.toml`, không sửa mã agent | Phụ lục A.2 |
| **FR-HAL-07** | HAL từ chối mọi lệnh `digital.out` không kèm chữ ký gate đã pass | P0 | Gọi trực tiếp sinh ngoại lệ `ActionContractViolation` | Phụ lục A.2 |

### 4.2 Môi trường thực thi (FR-TGT)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-TGT-01** | Môi trường `sim` là môi trường thực thi chính thức, hiện thực đúng hợp đồng HAL — không phải bản mock | P0 | `sim` chạy cùng tệp mã agent như phần cứng thật, không có nhánh mã riêng | §3.7 |
| **FR-TGT-02** | Môi trường `linux` là môi trường chính thức ngang hàng, hỗ trợ RPi và x86 qua `gpiod` | P0 | Agent mẫu chạy thật trên RPi 5 và trên x86 Linux | §3.2 |
| **FR-TGT-03** | Môi trường `esp32s3` là môi trường chính thức ngang hàng, xây bằng ESP-IDF | P0 | Agent mẫu chạy thật trên bo mạch tham chiếu | §8.2 |
| **FR-TGT-04** | **Nguyên tắc tương đương:** cùng một tệp mã agent cho cùng chuỗi phán quyết trên mọi môi trường, không sửa một dòng | P0 | `neuroedge verify --targets sim,linux,esp32s3` đạt 100% | §3.2 |
| **FR-TGT-05** | Chuyển môi trường qua tham số `--target`; **cấm** rẽ nhánh logic theo target trong mã agent | P0 | Rà soát mã: không tồn tại biểu thức điều kiện theo tên target trong lớp ứng dụng | §4.1 |
| **FR-TGT-06** | `sim` cung cấp giao diện web hiển thị cảm biến ảo và trạng thái cơ cấu chấp hành | P0 | Mở được trong trình duyệt, phản ánh đúng trạng thái chân GPIO ảo theo thời gian thực | §4.10 |
| **FR-TGT-07** | `sim` mô phỏng được kịch bản cảm biến và điều kiện mạng suy giảm | P1 | Khai báo được kịch bản mất mạng để kiểm thử fail-closed | §4.7 |
| **FR-TGT-08** | **Phân tầng target:** mỗi môi trường thực thi thuộc đúng một bậc cam kết — bậc 1 chính thức (`sim`, `linux`, `esp32s3`), bậc 2 mở rộng do đội lõi bảo trì, bậc 3 do cộng đồng port và tự kiểm chứng. Bậc được khai báo tường minh, không suy diễn | P0 | Mỗi target có bậc ghi trong tài liệu và trong `board.toml`; ngưỡng `verify` 100% chỉ ràng buộc bậc 1; bậc 3 không chặn phát hành | §3.2 |

**Giới hạn đã biết, phải nêu rõ trong tài liệu kỹ thuật:** `sim` không mô phỏng phản xạ âm học phòng vang, nhiễu micro, beamforming mảng micro, và phân mảnh bộ nhớ trên vi điều khiển. Các nhóm lỗi này được kiểm soát bằng kiểm thử nightly trên bo mạch thật (NFR-REL-03).

### 4.3 Trừu tượng hóa mô hình AI (FR-MDL)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-MDL-01** | Mọi truy cập mô hình đi qua interface `SystemOne` hoặc `SystemTwo`; giao diện kết nối mặc định tuân chuẩn OpenAI API | P0 | Không tồn tại lời gọi trực tiếp SDK nhà cung cấp trong lõi | §3.6 |
| **FR-MDL-02** | `SystemOne` hỗ trợ đúng 3 kiểu nguyên thủy: `bool`, `level`, `choice` | P0 | Ba kiểu chạy được và ánh xạ trực tiếp vào khối `evaluate` của gate | §3.6, Phụ lục B.2 |
| **FR-MDL-03** | Cả hai interface bắt buộc khai báo được đường dẫn dự phòng (`fallback`) | P0 | Ngắt nhà cung cấp chính → hệ thống tự chuyển fallback, ghi sự kiện vào vết | §3.6 |
| **FR-MDL-04** | Thay nhà cung cấp mô hình không yêu cầu sửa mã agent hay sửa gate | P0 | Đổi `SystemOne` sang mô hình cục bộ chỉ bằng thay đổi cấu hình | §3.6 |
| **FR-MDL-05** | Chính sách định tuyến System 1 / System 2 là cấu hình khai báo, không viết cứng | P1 | Đổi ngưỡng tự tin leo thang bằng cấu hình, không biên dịch lại | §3.5 |
| **FR-MDL-06** | Hệ thống ghi nhận tỷ lệ sử dụng System 1 / System 2 và chi phí từng lượt | P0 | Số liệu xuất hiện trong tệp vết ghi của mỗi phiên | §12.1 |
| **FR-MDL-07** | **Provider pluggable:** LLM, ASR và TTS kết nối qua chuẩn OpenAI API hoặc adapter do người dùng tự viết | P0 | Thêm một provider tương thích OpenAI chỉ bằng cấu hình endpoint và khóa, không sửa mã | §3.6, §6.1 |
| **FR-MDL-08** | **Adapter tùy chỉnh:** người dùng viết được logic kết nối riêng cho provider chưa hỗ trợ chuẩn OpenAI | P0 | Một adapter mẫu do bên ngoài viết chạy được mà không sửa lõi NeuroEdge | §3.6 |
| **FR-MDL-09** | **ASR/TTS là provider:** STT và TTS không gắn cứng vào một thư viện, thay thế được qua cấu hình | P0 | Đổi nhà cung cấp STT và TTS chỉ bằng cấu hình; agent và gate không đổi | §3.4, §3.6 |

### 4.4 Tầng nhận thức và runtime hội thoại (FR-PER)

Nguyên tắc: **tích hợp thư viện mã nguồn mở tốt nhất, không tự viết lại thuật toán xử lý tín hiệu cơ bản.**

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-PER-01** | Tích hợp sẵn chuỗi xử lý giọng nói theo hai tầng: **(a) trên thiết bị** — wake-word, VAD, AEC, thu/phát âm thanh, máy trạng thái hội thoại; **(b) trên cloud** — STT, TTS và suy luận ngôn ngữ qua provider | P0 | Agent mẫu hoạt động end-to-end chỉ với cấu hình provider, không cần cấu hình thêm thư viện | §3.4 |
| **FR-PER-02** | **Cắt lời (barge-in):** ngắt TTS ngay khi người dùng bắt đầu nói, đồng thời thu hồi lệnh actuator chưa thực thi | P0 | Kịch bản kiểm thử: cắt lời giữa câu → TTS dừng < 300 ms, không có lệnh actuator nào rò rỉ | §3.4 |
| **FR-PER-03** | **Khoảng lặng động:** phân biệt dừng để suy nghĩ với kết thúc lượt nói | P0 | Người nói chậm không bị cắt lời trong bộ kịch bản kiểm thử chuẩn | §3.4 |
| **FR-PER-04** | **Phản hồi dòng từng phần:** phát âm thanh từ token đầu tiên, rút lại an toàn khi mô hình đổi kết luận | P1 | Rút lại không gây phát trùng hoặc mất đoạn | §3.4 |
| **FR-PER-05** | **Tự phục hồi lỗi STT:** chuỗi rỗng hoặc nhiễu không làm treo máy trạng thái, không lặp câu hỏi vô hạn | P0 | Bơm 20 khung nhiễu liên tiếp → máy trạng thái vẫn phản hồi đúng | §3.4 |
| **FR-PER-06** | Runtime giọng nói trên `esp32s3` tối ưu bộ nhớ, gồm thu/phát âm thanh, WebRTC AEC, Silero VAD, Opus streaming, máy trạng thái hội thoại và thẩm định gate. **Không bắt buộc chạy STT/TTS trên thiết bị** | P0 | Chạy ổn định liên tục 24 giờ trên bo mạch tham chiếu với pipeline thu/phát + máy trạng thái + gate, không tràn bộ nhớ | §8.2 |
| **FR-PER-07** | **Cloud-first voice:** STT và TTS mặc định chạy trên cloud qua provider; vi điều khiển chỉ truyền luồng âm thanh lên và nhận luồng âm thanh về | P0 | Vòng lặp thoại chạy end-to-end trên bo mạch tham chiếu với STT/TTS đặt ở provider cloud | §3.4, §6.1 |

---

## 5. Yêu cầu chức năng — An toàn hành động

### 5.1 Động cơ hợp đồng hành động (FR-ACE)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-ACE-01** | Mọi lệnh tới cơ cấu chấp hành **bắt buộc** đi qua gate tương ứng; không tồn tại đường tắt | P0 | Kiểm thử thâm nhập: không có API công khai nào kích hoạt GPIO mà bỏ qua gate | §3.5 |
| **FR-ACE-02** | Hành động vật lý chỉ gọi được qua `c.do()`; gọi trực tiếp sinh `ActionContractViolation` | P0 | Test khẳng định ngoại lệ được ném và chân GPIO không bị kích | §4.4 |
| **FR-ACE-03** | **Fail-closed mặc định:** mất mạng, timeout, hoặc mô hình trả dữ liệu không hợp lệ → chặn hành động | P0 | Kịch bản `network=offline` → hành động bị chặn với lý do `gate_unreachable` | §3.5 |
| **FR-ACE-04** | Decorator `@action` ràng buộc `requires` tham gia đối chiếu năng lực lúc build | P0 | Thiếu năng lực → build dừng, chỉ rõ dòng mã gọi | §4.4 |
| **FR-ACE-05** | Decorator `@action` bắt buộc trỏ tới một gate đã khai báo trong `agent.toml` | P0 | Thiếu khai báo gate → build dừng | §4.4 |
| **FR-ACE-06** | Mỗi phiên tương tác sinh một tệp vết ghi JSON đầy đủ | P0 | Tệp chứa độ trễ từng chặng, kết quả đánh giá gate, lệnh actuator | §3.5 |
| **FR-ACE-07** | Tách biệt kiểu giữa hành vi phát ngôn (`c.say()`) và hành vi vật lý (`c.do()`) | P0 | `c.say()` không đi qua gate; `c.do()` luôn đi qua gate | §4.6 |

### 5.2 Định dạng cổng an toàn (FR-GATE)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-GATE-01** | Gate là tệp YAML có schema `neuroedge.gate/v1`, **không phải mã nguồn** | P0 | Gate đọc, diff và review được trong pull request | §3.5 |
| **FR-GATE-02** | Gate có đủ 8 trường cấp cao: `schema`, `name`, `version`, `extends`, `evaluate`, `allow_when`, `on_block`, `budget` | P0 | Thiếu trường bắt buộc → công cụ báo lỗi schema | Phụ lục B.1 |
| **FR-GATE-03** | Khối `evaluate` hỗ trợ 3 kiểu: `bool`, `level`, `choice`, kèm toán tử điều kiện tương ứng | P0 | Ba kiểu chạy đúng với toán tử `eq`, `lte`, `gte`, `in`, `not_in`, `confidence_gte` | Phụ lục B.2 |
| **FR-GATE-04** | Khối `on_block` hỗ trợ 4 hành vi: `escalate`, `deny`, `ask`, `degrade` | P0 | Bốn hành vi chạy đúng và được ghi vào vết | Phụ lục B.3 |
| **FR-GATE-05** | Gate kế thừa được qua `extends` từ URI gate cơ sở | P0 | Kéo gate cộng đồng về, ghi đè phần riêng, chạy đúng | Phụ lục B.5 |
| **FR-GATE-06** | **Gate con chỉ được siết chặt `allow_when`, tuyệt đối không được nới lỏng** | P0 | Gate con nới lỏng điều kiện cha → công cụ từ chối phân giải | Phụ lục B.5 |
| **FR-GATE-07** | `fail: open` **không kế thừa**; phải khai báo tường minh tại từng cấp | P0 | Gate cha `fail: open`, gate con không khai báo → gate con là `closed` | Phụ lục B.5 |
| **FR-GATE-08** | Độ sâu kế thừa tối đa 3 cấp; vòng lặp phụ thuộc bị chặn khi phân giải | P0 | Chuỗi 4 cấp hoặc vòng lặp → lỗi phân giải rõ ràng | Phụ lục B.5 |
| **FR-GATE-09** | `budget.p95_latency_ms` vượt ngưỡng được xử lý như một trường hợp lỗi | P0 | Vượt ngân sách → áp dụng chính sách `fail` đã khai báo | Phụ lục B.4 |
| **FR-GATE-10** | Thay đổi `allow_when` được coi là thay đổi phá vỡ tương thích, bắt buộc tăng phiên bản chính | P1 | Công cụ cảnh báo khi sửa `allow_when` mà không tăng major version | Phụ lục B.1 |

**Lý do nghiệp vụ của FR-GATE-06 và FR-GATE-07:** hai nguyên tắc này là điều kiện để việc tái sử dụng gate cộng đồng an toàn. Thiếu chúng, `extends` trở thành một rủi ro thay vì một tính năng.

### 5.3 Cập nhật firmware cấp thiết bị (FR-OTA)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-OTA-01** | Thiết bị hỗ trợ nạp firmware phân vùng kép A/B | P0 | Cập nhật thất bại không làm mất phân vùng đang chạy | §6.4 |
| **FR-OTA-02** | Thiết bị tự động rollback cục bộ khi phát hiện vòng lặp khởi động | P0 | Nạp firmware lỗi cố ý → thiết bị tự quay về bản cũ, không cần can thiệp | §6.4 |
| **FR-OTA-03** | Thiết bị xác minh chữ ký mật mã (RSA hoặc ECDSA) của firmware trước khi áp dụng | P0 | Firmware không chữ ký hoặc sai chữ ký bị từ chối | §6.4 |
| **FR-OTA-04** | Thiết bị nạp được firmware từ một HTTP endpoint mở bất kỳ, **không bắt buộc dùng dịch vụ của NeuroEdge** | P0 | Tự dựng máy chủ firmware và cập nhật thành công mà không có tài khoản | §6.4 |

**Ràng buộc nguyên tắc P-3:** FR-OTA-01 đến FR-OTA-04 thuộc lõi mã nguồn mở. Phần thương mại hóa chỉ là điều phối chiến dịch quy mô lớn (FR-FLT-02).

---

## 6. Yêu cầu chức năng — Kiểm thử Action CI

### 6.1 Bốn thành phần Action CI (FR-CI)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-CI-01** | **Record:** ghi toàn bộ chuỗi sự kiện của một phiên chạy thực tế ra tệp JSON | P0 | `neuroedge record --target esp32s3` sinh tệp hợp lệ theo schema | §3.7 |
| **FR-CI-02** | **Replay:** tái hiện chuỗi sự kiện đó trên bất kỳ môi trường nào | P0 | Cùng tệp vết ghi cho cùng chuỗi phán quyết trên mọi môi trường | §3.7 |
| **FR-CI-03** | **Assert:** thư viện khẳng định hành vi — hành động bị chặn, chặn bởi gate nào, leo thang tới đâu, chân nào không được kích | P0 | Bốn nhóm khẳng định chạy được trong pytest | §4.7 |
| **FR-CI-04** | **Golden Reference:** cố định chuỗi phán quyết chuẩn; lệch mẫu chuẩn làm CI báo đỏ | P0 | Đổi prompt gây lệch phán quyết → CI thất bại, chỉ rõ điểm lệch | §3.7 |
| **FR-CI-05** | Action CI chạy tự động trên `sim` và `linux` với mỗi pull request | P0 | Pipeline CI mẫu có sẵn trong dự án scaffold | §3.2 |
| **FR-CI-06** | Action CI chạy tự động hàng đêm trên bo mạch `esp32s3` thật | P0 | Có cấu hình runner nightly và báo cáo kết quả | §3.2 |
| **FR-CI-07** | Lệnh `neuroedge verify` kiểm tra tính nhất quán phán quyết gate và trạng thái GPIO giữa các môi trường bậc 1 | P0 | Sai lệch sinh `TargetEquivalenceError` chỉ rõ sự kiện lệch đầu tiên | §8.2 |

### 6.2 Ba cấp độ đảm bảo (FR-CI-LVL)

Đây là ranh giới kỹ thuật quan trọng nhất của sản phẩm: **Action CI không giả định mô hình ngôn ngữ là hàm tất định.**

| Mã | Cấp độ | Tính xác định | Action CI khẳng định điều gì | Ưu tiên |
|:---|:---|:---:|:---|:---:|
| **FR-CI-L1** | Thẩm định gate (rule engine): biểu thức `allow_when`, so sánh giá trị, ngân sách độ trễ | 100% xác định | Replay chuẩn xác từng bit; phán quyết đối chiếu tuyệt đối với Golden Reference | P0 |
| **FR-CI-L2** | Quyết định System 1 có cấu trúc: phân loại intent, trích xuất thực thể, schema cố định | Gần như xác định | Kiểm tra khớp schema JSON và xác thực `confidence >= threshold` | P0 |
| **FR-CI-L3** | Suy luận mở System 2 (LLM): sinh văn bản tự do | Phi xác định | **KHÔNG assert trên chuỗi văn bản sinh ra.** Chỉ assert trên **phán quyết gate (ALLOW/BLOCK)** và **trạng thái chân GPIO** | P0 |

**Hệ quả nghiệm thu:** một bài kiểm thử Action CI hợp lệ **KHÔNG ĐƯỢC** chứa khẳng định so khớp chuỗi văn bản do System 2 sinh ra. Quy tắc này phải được kiểm tra tự động trong công cụ lint của dự án mẫu.

### 6.3 Lược đồ vết ghi (FR-TRC)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-TRC-01** | Vết ghi là JSON theo JSON Schema draft 2020-12, xuất bản công khai tại `https://schema.neuroedge.dev/trace/v1.json` | P0 | URL truy cập được, schema hợp lệ | §3.7 |
| **FR-TRC-02** | Vết ghi chứa khối `metadata` đủ: `session_id`, `timestamp_utc`, `target`, `board_id`, `agent_version` | P0 | Thiếu bất kỳ trường nào → `neuroedge trace validate` báo lỗi | §3.7 |
| **FR-TRC-03** | Vết ghi bao phủ 6 nhóm sự kiện: đầu vào, nhận thức, quyết định mô hình, thẩm định gate, lệnh actuator, đầu ra | P0 | Phiên mẫu sinh đủ 6 nhóm | Phụ lục C.1 |
| **FR-TRC-04** | Vết ghi **replay được trên mọi môi trường** | P0 | FR-CI-02 đạt | Phụ lục C.2 |
| **FR-TRC-05** | Định dạng **ổn định giữa các phiên bản**: vết ghi cũ replay được sau nâng cấp phụ | P0 | Bộ vết ghi hồi quy từ phiên bản trước vẫn chạy | Phụ lục C.2 |
| **FR-TRC-06** | Vết ghi **đọc được bởi người**, không cần công cụ chuyên dụng | P0 | Mở bằng trình soạn thảo văn bản và hiểu được trình tự | Phụ lục C.2 |
| **FR-TRC-07** | Chế độ **ẩn danh tại nguồn:** một cờ cấu hình thay nội dung thô bằng hash, giữ nguyên chuỗi quyết định | P0 | Bật cờ → không còn dữ liệu âm thanh hay văn bản thô, replay vẫn đúng | Phụ lục C.2 |
| **FR-TRC-08** | Lệnh `neuroedge trace validate <tệp>` xác thực tệp theo JSON Schema | P0 | Tệp sai cấu trúc bị bắt lỗi trước khi commit | §3.7 |
| **FR-TRC-09** | Tuân thủ quy ước đường dẫn: `traces/`, `traces/incidents/<session_id>.json`, `traces/golden/<kịch-bản>.json` | P1 | Dự án scaffold tạo sẵn ba thư mục | §3.7 |
| **FR-TRC-10** | Schema được đăng ký lên SchemaStore công cộng để IDE tự nhận diện | P1 | VS Code gợi ý tự động khi mở tệp vết ghi mà không cần cài công cụ NeuroEdge | §3.7 |

### 6.4 Quản trị lược đồ mở (FR-GOV)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-GOV-01** | Lược đồ gate và vết ghi xuất bản công khai theo giấy phép MIT hoặc Apache-2.0 | P0 | Kho lược đồ công khai, có tệp giấy phép | §3.8 |
| **FR-GOV-02** | Phiên bản lược đồ quản lý theo đường dẫn URL (`/v1`, `/v2`); thay đổi phá vỡ tương thích bắt buộc tăng phiên bản chính | P0 | Có văn bản chính sách phiên bản kèm kho lược đồ | §3.8 |
| **FR-GOV-03** | **Bộ kiểm thử tuân thủ:** công bố tập vết ghi mẫu kèm kết quả replay kỳ vọng để bên thứ ba tự kiểm chứng | P0 | Bên thứ ba chạy được bộ kiểm thử mà không cần chứng nhận độc quyền | §3.8 |
| **FR-GOV-04** | Mọi thay đổi lược đồ đi qua quy trình RFC công khai trên GitHub | P1 | Có mẫu RFC và ít nhất một RFC đã qua quy trình | §3.8 |

---

## 7. Yêu cầu chức năng — Trải nghiệm lập trình viên

### 7.1 Khởi tạo và vòng lặp phát triển (FR-DX)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-DX-01** | `neuroedge new <tên>` sinh dự án mẫu có sẵn: `agent.toml`, 1 action, 1 gate, 1 kịch bản test CI | P0 | Dự án mới chạy `neuroedge test` thành công ngay, không sửa gì | §4.8 |
| **FR-DX-02** | Cài đặt và chạy `sim` **không yêu cầu** tài khoản, API key hay thẻ thanh toán | P0 | Máy sạch, không mạng nội bộ đặc biệt: hoàn thành hành trình 10 phút | §4.10 |
| **FR-DX-03** | Time-to-first-value trung vị dưới 10 phút, đo trên 10 lập trình viên độc lập | P0 | Biên bản đo có mốc thời gian từng bước của 10 người | §12.1 |
| **FR-DX-04** | Mọi thông báo lỗi nêu rõ: cái gì sai, ở đâu, và cách xử lý | P0 | Rà soát toàn bộ mã lỗi tại Phụ lục B đạt đủ 3 thành phần | §4.9 |
| **FR-DX-05** | Tài liệu có ít nhất 3 ứng dụng mẫu hoàn chỉnh chạy được | P0 | Ba mẫu chạy thành công trên máy sạch theo hướng dẫn | §12.1 |
| **FR-DX-06** | Tài liệu có ít nhất 1 video hoặc ảnh động minh họa trực quan trong README | P0 | Có tài sản trực quan dưới 30 giây thể hiện vòng lặp giá trị | §12.1 |
| **FR-DX-07** | Công cụ lint của dự án mẫu chặn khẳng định so khớp văn bản do System 2 sinh ra | P1 | Test vi phạm FR-CI-L3 bị lint báo lỗi | §3.7 |

### 7.2 Giao diện dòng lệnh (FR-CLI)

| Mã | Nhóm lệnh | Lệnh bắt buộc | Ưu tiên | Nguồn |
|:---|:---|:---|:---:|:---:|
| **FR-CLI-01** | Khởi tạo | `neuroedge new <tên>` | P0 | §4.8 |
| **FR-CLI-02** | Phát triển | `neuroedge run --target sim` · `neuroedge run --target linux` · `neuroedge build --target esp32s3 --board <id>` | P0 | §4.8 |
| **FR-CLI-03** | Kiểm thử | `neuroedge test` · `neuroedge verify --targets sim,linux,esp32s3` | P0 | §4.8 |
| **FR-CLI-04** | Chẩn đoán | `neuroedge record --target <t> --out <thư-mục>` · `neuroedge trace validate <tệp>` · `neuroedge replay <tệp> --target <t>` | P0 | §4.8 |
| **FR-CLI-05** | Hệ sinh thái gate | `neuroedge gate publish <tệp>` · `neuroedge gate add <uri>` | P1 | §4.8 |

**Yêu cầu chung cho toàn bộ CLI:**

| Mã | Yêu cầu | Ưu tiên |
|:---|:---|:---:|
| **FR-CLI-06** | Mọi lệnh trả mã thoát khác 0 khi thất bại, phục vụ tích hợp CI | P0 |
| **FR-CLI-07** | Mọi lệnh có `--help` mô tả đủ tham số và ví dụ sử dụng | P0 |
| **FR-CLI-08** | Lệnh chạy lâu hiển thị tiến trình; lệnh phá hủy dữ liệu yêu cầu xác nhận | P1 |

---

## 8. Yêu cầu chức năng — Tầng dịch vụ thương mại

**§8.1 (FR-GW) là lõi mã nguồn mở thuộc mốc v1.0** — lớp trừu tượng nhà cung cấp do người dùng tự vận hành, không thu phí. **§8.2 (FR-FLT) và §8.3 (FR-REG) thuộc mốc v1.1**, chỉ khởi động khi đạt điều kiện §3.3. Fleet OS là dịch vụ thương mại duy nhất.

### 8.1 Lớp trừu tượng nhà cung cấp (FR-GW)

Nhóm FR-GW chuyển từ dịch vụ thương mại mốc v1.1 sang **lõi mã nguồn mở mốc v1.0** (xem §3.2). Người dùng tự chạy lớp này, tự cấu hình provider và tự giữ khóa; NeuroEdge không vận hành cổng trung gian và không bán lại token.

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-GW-01** | Lớp trừu tượng self-host cung cấp một điểm kết nối và một thông tin xác thực duy nhất cho mọi nhà cung cấp mô hình | P0 | Một cấu hình duy nhất phục vụ nhiều provider; thiết bị không nhúng cứng khóa của từng nhà cung cấp | §6.1 |
| **FR-GW-02** | Khóa bảo mật do người dùng tự quản lý trong lớp self-host, xoay vòng được mà không cần nạp lại firmware | P0 | Xoay khóa trên 10 thiết bị đang chạy, không gián đoạn dịch vụ | §6.1 |
| **FR-GW-03** | Định tuyến đa nhà cung cấp kèm chuyển đổi dự phòng tự động — tính năng thuộc lõi OSS | P0 | Ngắt nhà cung cấp chính → thiết bị không thấy gián đoạn | §6.1 |
| **FR-GW-04** | Giao thức tối ưu cho thiết bị biên: WebSocket liên tục, khung âm thanh nhị phân, phản hồi theo luồng — tính năng OSS, không phải dịch vụ trả phí | P0 | Vi điều khiển không phải bắt tay TLS cho từng yêu cầu | §6.1 |
| **FR-GW-05** | Hạn mức sử dụng cứng theo từng thiết bị — tùy chọn trong lớp self-host | P1 | Thiết bị lỗi lặp vòng bị chặn khi chạm hạn mức, có cảnh báo | §6.1 |
| **FR-GW-06** | Bộ nhớ đệm ngữ nghĩa và thống kê tỷ lệ System 1 / System 2 — tùy chọn OSS | P1 | Báo cáo tỷ lệ và mức tiết kiệm chi phí theo nhóm tác vụ | §6.1 |
| **FR-GW-07** | Lớp trừu tượng xuất tệp vết ghi JSON **cùng định dạng** với Action CI cho mỗi phiên | P0 | Vết ghi từ lớp provider replay được trên máy cá nhân, không cần chuyển đổi | §6.1 |

### 8.2 Hệ điều hành quản trị đội thiết bị (FR-FLT)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-FLT-01** | Cấp phát danh tính và chứng chỉ mật mã riêng cho từng thiết bị ở lần khởi động đầu | P0 | Quy trình claim tự động thành công trên lô 100 thiết bị | §6.2 |
| **FR-FLT-02** | Điều phối cập nhật OTA theo đợt canary 1% → 10% → 100%, tự dừng và khôi phục khi tỷ lệ lỗi vượt ngưỡng | P0 | Chiến dịch 1.000 thiết bị, 0 thiết bị brick | §6.2, §12.2 |
| **FR-FLT-03** | Sổ kiểm kê và giám sát sức khỏe: online/offline, phiên bản firmware, RSSI, nhiệt độ chip, cảnh báo lặp khởi động | P0 | Dashboard phản ánh đúng trạng thái trong vòng 60 giây | §6.2 |
| **FR-FLT-04** | Cập nhật cấu hình, bí mật và **gate** từ xa mà không nạp lại firmware | P0 | Đổi ngưỡng gate trên toàn đội, có hiệu lực không cần khởi động lại | §6.2 |
| **FR-FLT-05** | Tự động tải tệp vết ghi JSON về kho tập trung khi thiết bị phát sinh cảnh báo | P0 | Sự cố hiện trường xuất hiện trong kho trong vòng 5 phút | §6.2 |
| **FR-FLT-06** | Thiết bị ảo trong `sim` xuất hiện ngay trên Fleet Dashboard | P0 | Dashboard hữu ích ở quy mô n = 1, không yêu cầu phần cứng thật | §6.2 |

### 8.3 Đường ray hạ tầng nền tảng (FR-REG)

Tám thành phần rẻ ở giai đoạn đầu nhưng **không thể bổ sung sau**.

| Mã | Thành phần | Giá trị ngày đầu | Vai trò dài hạn | Ưu tiên |
|:---|:---|:---|:---|:---:|
| **FR-REG-01** | Kho Gate công khai miễn phí | `neuroedge gate add <uri>` | Dữ liệu về chính sách được tái sử dụng nhiều nhất | P0 |
| **FR-REG-02** | Manifest và chuẩn phiên bản SemVer | Quản lý phụ thuộc minh bạch | Đơn vị phân phối của Marketplace | P0 |
| **FR-REG-03** | Khai báo năng lực phần cứng | Chặn lỗi bất tương thích khi build | Kiểm tra tương thích trước khi cài | P0 |
| **FR-REG-04** | Gate có phiên bản, hỗ trợ `extends` | Tái sử dụng chính sách an toàn | Tài sản trao đổi giá trị cao nhất | P0 |
| **FR-REG-05** | Định danh ổn định cho thiết bị, agent, gate | Gỡ lỗi và tra cứu chính xác | Quy kết trách nhiệm và doanh thu | P0 |
| **FR-REG-06** | Hệ thống đo lường theo lượt gọi agent và lượt thẩm định gate | Thống kê sử dụng | Cơ sở phân chia doanh thu | P0 |
| **FR-REG-07** | Cơ chế phân quyền và sandbox | An toàn khi thử agent lạ | Điều kiện chạy mã bên thứ ba trên thiết bị có actuator | P0 |
| **FR-REG-08** | Kho chia sẻ adapter kết nối provider | Người dùng tải về adapter sẵn có thay vì tự viết lại | Đòn bẩy hiệu ứng mạng dễ hình thành hơn gate vì nhu cầu kết nối provider là tức thời | P1 |

**Cảnh báo kiến trúc:** FR-REG-05, FR-REG-06 và FR-REG-07 phải được thiết kế ngay ở v1.1. Thiếu chúng, hệ thống sau này không thể đối soát doanh thu và không thể cho phép mã nguồn bên thứ ba chạy trên thiết bị có cơ cấu chấp hành.

---

## 9. Yêu cầu phi chức năng

### 9.1 Hiệu năng và độ trễ (NFR-PERF)

| Mã | Chỉ tiêu | Ngưỡng cam kết | Điều kiện đo | Ưu tiên |
|:---|:---|:---|:---|:---:|
| **NFR-PERF-01** | Độ trễ phản hồi thoại trọn vòng — provider hỗ trợ streaming | **P95 < 850 ms** | Kết nối Wi-Fi, provider STT/LLM/TTS hỗ trợ streaming, từ lúc dứt lời tới khi loa phát tiếng | P0 |
| **NFR-PERF-02** | Độ trễ thẩm định gate — xử lý cục bộ | **P95 < 120 ms** | Trên các môi trường bậc 1 | P0 |
| **NFR-PERF-03** | Độ trễ thẩm định gate — khi cần dữ liệu từ provider cloud | **P95 < 450 ms** | Mạng ổn định | P0 |
| **NFR-PERF-04** | Quyết định `SystemOne` có cấu trúc | **< 100 ms** | Mô hình cục bộ hoặc mô hình nhanh qua lớp trừu tượng provider | P0 |
| **NFR-PERF-05** | Hiệu quả định tuyến hai mô hình | Tiết kiệm **≥ 60%** chi phí token so với chuyển toàn bộ lên System 2 | Đo trên lưu lượng thực, tách theo nhóm tác vụ | P0 |
| **NFR-PERF-06** | Thời gian chạy bộ Action CI của dự án mẫu | **< 30 giây** trên `sim` | Máy phát triển thông thường | P1 |
| **NFR-PERF-07** | Độ trễ phản hồi thoại trọn vòng — provider request-response | **P95 < 1.500 ms** | Kết nối Wi-Fi, provider không hỗ trợ streaming, từ lúc dứt lời tới khi loa phát tiếng | P1 |

### 9.2 Tài nguyên và ràng buộc phần cứng (NFR-RES)

| Mã | Chỉ tiêu | Yêu cầu | Ưu tiên |
|:---|:---|:---|:---:|
| **NFR-RES-01** | Runtime trên `esp32s3` chạy ổn định trên bo mạch tham chiếu với pipeline thu/phát âm thanh, máy trạng thái hội thoại và thẩm định gate *(STT/TTS đặt ở provider cloud)* | Không tràn bộ nhớ trong 24 giờ chạy liên tục | P0 |
| **NFR-RES-02** | Ngân sách SRAM/PSRAM tối thiểu còn tự do cho runtime | SRAM ≥ 120 KB · PSRAM ≥ 2 MB *(đã chốt tại §15 của tài liệu này, Q-3; dễ đạt hơn từ v1.1 nhờ cloud-first)* | P0 |
| **NFR-RES-03** | Kích thước firmware tối đa cho bo mạch tham chiếu | ≤ 3,5 MB *(đã chốt tại §15 của tài liệu này, Q-3 — vừa phân vùng kép A/B trên 16 MB Flash)* | P1 |
| **NFR-RES-04** | Hệ thống hoạt động đầy đủ khi mất kết nối Internet trên lõi mã nguồn mở | 100% tính năng an toàn hoạt động offline | P0 |

### 9.3 Độ tin cậy (NFR-REL)

| Mã | Chỉ tiêu | Ngưỡng cam kết | Ưu tiên |
|:---|:---|:---|:---:|
| **NFR-REL-01** | Độ tin cậy cập nhật OTA quy mô lớn | **1.000 thiết bị / 0 sự cố brick** | P0 |
| **NFR-REL-02** | Hành vi mặc định khi mọi thành phần suy giảm | `fail: closed` — chặn hành động vật lý | P0 |
| **NFR-REL-03** | Kiểm thử nightly trên bo mạch thật | Chạy hằng đêm, có báo cáo kết quả và xu hướng | P0 |
| **NFR-REL-04** | Vết ghi cũ replay được sau nâng cấp phiên bản phụ | 100% bộ vết ghi hồi quy vẫn chạy | P0 |

### 9.4 Bảo mật (NFR-SEC)

Sáu lớp phòng thủ, hoạt động theo chế độ mặc định.

| Mã | Lớp | Yêu cầu | Ưu tiên |
|:---|:---|:---|:---:|
| **NFR-SEC-01** | Hành động vật lý | Không có đường tắt tới cơ cấu chấp hành ngoài gate; mọi đánh giá gate được ghi vết | P0 |
| **NFR-SEC-02** | Thiết bị | Kích hoạt Secure Boot và mã hóa flash trên ESP32-S3; hỗ trợ TPM trên Linux | P0 |
| **NFR-SEC-03** | Thiết bị | Bo mạch tham chiếu có nút ngắt micro vật lý | P0 |
| **NFR-SEC-04** | Mạng | TLS 1.3 toàn tuyến; mTLS hai chiều thiết bị ↔ đám mây; certificate pinning | P0 |
| **NFR-SEC-05** | Mạng | Mỗi thiết bị có chứng chỉ mật mã riêng, thu hồi được | P0 |
| **NFR-SEC-06** | Cập nhật | Firmware ký số; xác minh chữ ký trên chip trước khi áp dụng | P0 |
| **NFR-SEC-07** | Mã bên thứ ba | Sandbox giới hạn quyền truy cập chân actuator nhạy cảm | P0 (v1.1) |
| **NFR-SEC-08** | Nhà cung cấp bên ngoài | Dữ liệu âm thanh và văn bản gửi tới provider cloud phải đi qua kênh mã hóa TLS 1.3; hệ thống ghi nhận provider đang dùng trong vết ghi. Việc chọn provider tuân thủ quy định là trách nhiệm của người dùng | P0 |

### 9.5 Quyền riêng tư (NFR-PRIV)

| Mã | Yêu cầu | Ưu tiên |
|:---|:---|:---:|
| **NFR-PRIV-01** | Luồng âm thanh xử lý trực tiếp, **không lưu trữ mặc định** | P0 |
| **NFR-PRIV-02** | Xử lý ngôn ngữ mặc định theo kiến trúc cloud-first; ưu tiên on-device khi năng lực phần cứng cho phép. Người dùng tự chọn provider và cấu hình mức độ riêng tư tương ứng | P0 |
| **NFR-PRIV-03** | Vết ghi mặc định chỉ lưu quyết định, không lưu dữ liệu thô; lưu thô phải bật tường minh | P0 |
| **NFR-PRIV-04** | Chế độ ẩn danh tại nguồn thay nội dung thô bằng hash mà không phá vỡ khả năng replay | P0 |

### 9.6 Khả năng quan sát (NFR-OBS)

| Mã | Yêu cầu | Ưu tiên |
|:---|:---|:---:|
| **NFR-OBS-01** | Mỗi phiên tương tác sinh đúng một tệp vết ghi hoàn chỉnh | P0 |
| **NFR-OBS-02** | Vết ghi hiển thị tỷ lệ System 1 / System 2, chi phí từng lượt và toàn bộ kết quả thẩm định gate | P0 |
| **NFR-OBS-03** | Vết ghi ghi độ trễ từng chặng đủ để đối chiếu với ngân sách `budget.p95_latency_ms` | P0 |

### 9.7 Tương thích và chuẩn mở (NFR-COMP)

| Mã | Yêu cầu | Ưu tiên |
|:---|:---|:---:|
| **NFR-COMP-01** | Lõi phát hành theo giấy phép MIT | P0 |
| **NFR-COMP-02** | Không tính năng an toàn cốt lõi nào bị khóa sau tài khoản trả phí | P0 |
| **NFR-COMP-03** | Mọi dịch vụ đám mây truy cập qua interface thay thế được (pluggable backend) | P0 |
| **NFR-COMP-04** | Lược đồ gate và vết ghi là chuẩn mở, quản trị theo quy trình RFC công khai | P0 |
| **NFR-COMP-05** | Phiên bản Python hỗ trợ tối thiểu: **Python 3.11+** (tận dụng `tomllib` tích hợp, `asyncio.TaskGroup` và tối ưu tốc độ bytecode) | P0 |
| **NFR-COMP-06** | Hệ điều hành hỗ trợ cho môi trường `linux`: Debian/Ubuntu trên ARM64 và x86-64 | P0 |

---

## 10. Đặc tả giao diện dữ liệu

Bốn tệp định dạng tạo thành toàn bộ bề mặt dữ liệu của sản phẩm. Đặc tả trường chi tiết nằm ở Phụ lục A, B, C của tài liệu nguồn; mục này quy định **ràng buộc bắt buộc** đối với hiện thực.

### 10.1 Bốn tệp định dạng

| Tệp | Định dạng | Vai trò | Đặc tả chi tiết |
|:---|:---|:---|:---|
| `board.toml` | TOML | Bo mạch khai báo năng lực cung cấp | §4.2, Phụ lục A |
| `agent.toml` | TOML | Agent khai báo năng lực cần dùng, gate và môi trường hỗ trợ | §4.3 |
| `<gate>@<version>.yaml` | YAML | Điều kiện cho phép một hành động vật lý | §4.5, Phụ lục B |
| `<phiên>.json` | JSON | Vết ghi chuỗi sự kiện của một phiên tương tác | §3.7, Phụ lục C |

### 10.2 Ràng buộc bắt buộc đối với hiện thực

| Mã | Ràng buộc | Lý do |
|:---|:---|:---|
| **DATA-01** | Chân và cảm biến định danh bằng tên logic trong cả `board.toml` và `agent.toml` | Bảo toàn nguyên tắc tương đương môi trường |
| **DATA-02** | Đối chiếu năng lực thực hiện lúc build, kết quả là chặn hoặc cho phép, không có trạng thái cảnh báo mềm | Lỗi cấu hình không được lọt ra hiện trường |
| **DATA-03** | Gate là tệp độc lập với mã nguồn, có phiên bản SemVer riêng | Chia sẻ, kiểm toán và thương mại hóa được |
| **DATA-04** | Khối `evaluate` của gate ánh xạ một-một với ba nguyên thủy của `SystemOne` | Đổi nhà cung cấp mô hình không phải viết lại gate |
| **DATA-05** | Vết ghi là nguồn sự thật duy nhất cho cả chẩn đoán hiện trường và kiểm thử CI | Hiện trường và CI dùng chung một ngôn ngữ |
| **DATA-06** | Golden Reference là tập con của vết ghi, loại bỏ mốc thời gian và nội dung thô | Chịu được việc đổi mô hình, đổi prompt và đổi môi trường |

### 10.3 Ma trận tương thích phiên bản

| Thành phần | Quy tắc phiên bản | Thay đổi phá vỡ tương thích |
|:---|:---|:---|
| Lược đồ vết ghi | URL `/v1`, `/v2` | Tăng phiên bản chính; bổ sung trường tùy chọn không tăng |
| Lược đồ gate | `neuroedge.gate/v1` | Tăng phiên bản chính |
| Tệp gate cụ thể | SemVer | Mọi thay đổi trong `allow_when` |
| Gói `neuroedge` | SemVer | Thay đổi bề mặt API công khai hoặc CLI |

---

## 11. Tiêu chí nghiệm thu phát hành

Mỗi mốc chỉ được công bố khi đạt **toàn bộ** tiêu chí tương ứng. Không chấp nhận đạt một phần hoặc lấy giá trị trung bình.

### 11.1 Nghiệm thu v1.0 — Lõi mã nguồn mở

| # | Tiêu chí | Ngưỡng | Phương pháp kiểm chứng |
|:---:|:---|:---|:---|
| **A1** | Time-to-first-value | Trung vị **< 10 phút** trên 10 lập trình viên độc lập | Biên bản đo có mốc thời gian từng bước |
| **A2** | Tương đương môi trường | `neuroedge verify` đạt **100%** trên các target bậc 1: `sim`, `linux`, `esp32s3` | Chạy trong CI, lưu nhật ký |
| **A3** | Không có đường tắt tới actuator | **0** lối đi kích hoạt GPIO bỏ qua gate | Rà soát mã và kiểm thử thâm nhập |
| **A4** | Fail-closed | **100%** kịch bản suy giảm đều chặn hành động | Bộ kịch bản: mất mạng, timeout, dữ liệu mô hình không hợp lệ |
| **A5** | Kế thừa gate an toàn | Gate con nới lỏng `allow_when` bị từ chối trong **100%** trường hợp | Bộ kiểm thử phân giải kế thừa |
| **A6** | Độ ổn định trên vi điều khiển | **24 giờ** chạy liên tục không tràn bộ nhớ, với pipeline thu/phát âm thanh + máy trạng thái hội thoại + thẩm định gate *(STT/TTS đặt ở provider cloud)* | Kiểm thử chịu tải trên bo mạch tham chiếu |
| **A7** | Vết ghi hợp lệ | **100%** phiên sinh tệp qua được `neuroedge trace validate` | Chạy tự động trong CI |
| **A8** | Tài liệu | 3 ứng dụng mẫu chạy được + 1 tài sản trực quan trong README | Kiểm chứng trên máy sạch |
| **A9** | Lược đồ công khai | JSON Schema truy cập được tại URL công bố, kèm bộ kiểm thử tuân thủ | Bên thứ ba chạy thử thành công |

### 11.2 Nghiệm thu Developer Beta

| # | Tiêu chí | Ngưỡng |
|:---:|:---|:---|
| **B1** | Lập trình viên bên ngoài chạy thành công agent trên `sim` | ≥ 50 người |
| **B2** | Lập trình viên bên ngoài nạp và điều khiển thành công phần cứng thật | ≥ 10 người |
| **B3** | Gate an toàn do cộng đồng bên ngoài tự viết và đóng góp | ≥ 3 gate |
| **B4** | Tỷ lệ áp dụng Action CI | ≥ 50% dự án khởi tạo giữ lại và mở rộng kịch bản test gate |
| **B5** | Tỷ lệ chuyển đổi sang phần cứng thật | ≥ 15% người chạy `sim` nạp lên bo mạch trong 30 ngày |

**Nguyên tắc vận hành giai đoạn Beta:** đóng băng hoàn toàn việc phát triển tính năng mới. Toàn bộ nguồn lực dành cho hỗ trợ kỹ thuật trực tiếp, hoàn thiện tài liệu và làm mượt trải nghiệm.

### 11.3 Nghiệm thu v1.1 — Tầng dịch vụ thương mại

| # | Tiêu chí | Ngưỡng |
|:---:|:---|:---|
| **C1** | Độ tin cậy OTA | 1.000 thiết bị / 0 sự cố brick |
| **C2** | Độ trễ thoại *(đo trọn vòng qua provider cloud)* | P95 < 850 ms với provider streaming · P95 < 1.500 ms với provider request-response, qua Wi-Fi |
| **C3** | Độ trễ thẩm định gate | P95 < 120 ms cục bộ · < 450 ms khi cần dữ liệu từ provider cloud |
| **C4** | Hiệu quả định tuyến | Tiết kiệm ≥ 60% chi phí token |
| **C5** | Chia sẻ gate cộng đồng | ≥ 20 gate đạt từ 5 lượt cài đặt bởi người dùng độc lập |
| **C6** | Cơ cấu doanh thu | Doanh thu Fleet đạt ngưỡng hòa vốn theo mô hình chỉ-Fleet *(NeuroEdge không còn doanh thu inference)* |
| **C7** | Đồng nhất định dạng vết ghi | Vết ghi từ lớp trừu tượng provider replay được trên máy cá nhân, không chuyển đổi |

---

## 12. Hệ chỉ số và yêu cầu đo đạc

Nguyên tắc: **mọi chỉ số trong mục này phải có một yêu cầu đo đạc tương ứng.** Chỉ số không đo được không phải chỉ số.

### 12.1 Yêu cầu đo đạc bắt buộc (FR-TEL)

| Mã | Yêu cầu | Phục vụ chỉ số | Ưu tiên |
|:---|:---|:---|:---:|
| **FR-TEL-01** | CLI thu thập số liệu **ẩn danh, có thể tắt (opt-out)** về các mốc: cài đặt, khởi tạo dự án, lần chạy `sim` đầu tiên, lần build phần cứng đầu tiên | TTFV, tỷ lệ chuyển đổi sim → phần cứng | P0 |
| **FR-TEL-02** | Chính sách thu thập số liệu công bố rõ ràng; lệnh tắt nêu ngay trong lần chạy đầu | Niềm tin cộng đồng | P0 |
| **FR-TEL-03** | Vết ghi ghi nhận tỷ lệ System 1 / System 2 và chi phí từng lượt | Hiệu quả định tuyến | P0 |
| **FR-TEL-04** | Registry ghi nhận số lượt tải và lượt kế thừa từng gate, phân biệt tác giả và người dùng khác | Chia sẻ gate cộng đồng, chỉ số G2/G3 | P0 (v1.1) |
| **FR-TEL-05** | Fleet OS ghi nhận kết quả từng chiến dịch OTA: số thiết bị, tỷ lệ lỗi, số ca rollback | Độ tin cậy OTA | P0 (v1.1) |
| **FR-TEL-06** | Lớp trừu tượng provider ghi nhận độ trễ từng chặng đủ để tính P95 theo từng nhóm tác vụ | SLA độ trễ | P0 |

### 12.2 Bảng chỉ số theo mốc

| Chỉ số | Mốc | Ngưỡng | Nguồn dữ liệu |
|:---|:---:|:---|:---|
| Time-to-first-value | v1.0 | Trung vị < 10 phút | Biên bản đo trực tiếp 10 người |
| Tương đương môi trường | v1.0 | 100% pass `neuroedge verify` | Nhật ký CI |
| Tỷ lệ áp dụng Action CI | Beta | ≥ 50% dự án | FR-TEL-01 |
| Tỷ lệ chuyển đổi sang phần cứng | Beta | ≥ 15% trong 30 ngày | FR-TEL-01 |
| Độ tin cậy OTA | v1.1 | 1.000 / 0 brick | FR-TEL-05 |
| Độ trễ thoại P95 | v1.1 | < 850 ms *(provider streaming)* · < 1.500 ms *(provider request-response)* | FR-TEL-06 |
| Độ trễ gate P95 | v1.1 | < 120 ms cục bộ · < 450 ms cloud | FR-TEL-06 |
| Tiết kiệm chi phí token | v1.1 | ≥ 60% | FR-TEL-03 |
| Chia sẻ gate cộng đồng | v1.1 | ≥ 20 gate có ≥ 5 lượt cài | FR-TEL-04 |
| Cơ cấu doanh thu | v1.1 | Fleet đạt ngưỡng hòa vốn theo mô hình chỉ-Fleet | Hệ thống hóa đơn |

**Chỉ số bị loại bỏ có chủ ý:** số sao GitHub, lượt tải trang, lượt xem tài liệu. Các chỉ số này đo sự chú ý, không đo giá trị sử dụng.

---

## 13. Phụ thuộc, rủi ro và giả định

### 13.1 Phụ thuộc kỹ thuật bên ngoài

| Thành phần | Vai trò | Rủi ro phụ thuộc | Phương án giảm thiểu |
|:---|:---|:---|:---|
| ESP-IDF | Toolchain cho `esp32s3` | Thay đổi API giữa các bản lớn | Ghim phiên bản; kiểm thử nightly phát hiện sớm |
| Sherpa-ONNX, Silero VAD, WebRTC AEC, Opus | Chuỗi xử lý tín hiệu | Ngừng bảo trì thượng nguồn | Bọc sau interface nội bộ, thay thế được từng thành phần |
| `gpiod` | Truy cập GPIO trên Linux | Khác biệt giữa các bản phân phối | Giới hạn hỗ trợ ở Debian/Ubuntu (NFR-COMP-06) |
| Nhà cung cấp `SystemOne` | Quyết định có cấu trúc | Đổi giá, siết truy cập, tự ship framework | Interface từ ngày đầu (FR-MDL-01); fallback cục bộ khi có cảnh báo |
| Nhà cung cấp `SystemTwo` | Suy luận mở | Tương tự | Định tuyến đa nhà cung cấp (FR-GW-03) |
| SchemaStore | Nhận diện schema trong IDE | Quy trình duyệt chậm | Không chặn phát hành; là yêu cầu P1 |

### 13.2 Rủi ro sản phẩm

Mục này ghi rủi ro **sản phẩm và thực thi**. Rủi ro **chiến lược** (cạnh tranh, mô hình kinh doanh, phân mảnh phạm vi) nằm ở `neuroedge-proposal.md` §11 với hệ đánh số `#1–#6`. Ba cặp giao nhau giữa hai sổ: **R-4 ↔ §11 #1** (phụ thuộc nhà cung cấp mô hình) · **R-6 ↔ §11 #5** (mất kết nối đám mây) · **R-7 ↔ §11 #6** (phủ rộng phần cứng). Các rủi ro còn lại thuộc đúng một sổ.


| # | Rủi ro | Mức độ | Dấu hiệu cảnh báo sớm | Phương án ứng phó |
|:---:|:---|:---:|:---|:---|
| **R-1** | Phạm vi Khối 1b vượt thời hạn do tối ưu bộ nhớ vi điều khiển | Trung bình *(hạ từ Cao ở v1.1)* | Tuần 9 chưa chạy được vòng lặp thu/phát âm thanh trên bo mạch | Kiến trúc cloud-first đã đưa STT/TTS ra khỏi vi điều khiển, giảm đáng kể áp lực bộ nhớ (P-4, FR-PER-07). Nếu vẫn trượt: cắt phạm vi theo §3.4, giữ `esp32s3` ở mức phán quyết gate |
| **R-2** | Môi trường `sim` lệch khỏi phần cứng theo thời gian | Cao | `neuroedge verify` bắt đầu có sai lệch lẻ tẻ | Nightly trên bo mạch thật (NFR-REL-03); coi mọi sai lệch là lỗi chặn phát hành |
| **R-3** | Lập trình viên bỏ qua Action CI, chỉ dùng framework như thư viện thoại | Trung bình | Tỷ lệ áp dụng Action CI dưới 50% ở Beta | Đưa test gate vào scaffold mặc định; tài liệu lấy Action CI làm trung tâm |
| **R-4** | Nhà cung cấp mô hình thay đổi điều kiện truy cập | Trung bình | Thay đổi điều khoản API, vendor công bố SDK thiết bị | Kích hoạt đầu tư fallback cục bộ |
| **R-5** | Hiệu ứng mạng chia sẻ gate không hình thành | Trung bình | Dưới 3 gate cộng đồng ở cuối Beta | Chuyển trọng tâm sang giá trị đơn lẻ (Action CI + Fleet), hoãn Marketplace vô thời hạn |
| **R-6** | Phụ thuộc provider cloud khi mất kết nối | Trung bình | Tỷ lệ phiên kết thúc với lý do `gate_unreachable` tăng bất thường · Gián đoạn tích lũy của provider vượt cam kết | Fail-closed đã chặn mọi hành động vật lý khi không thẩm định được gate (NFR-RES-04, A4); gate và máy trạng thái chạy hoàn toàn trên thiết bị. Bổ sung tùy chọn fallback cục bộ (SLM/STT on-device) cho khách hàng yêu cầu vận hành ngoại tuyến |
| **R-7** | Phủ rộng phần cứng ở Giai đoạn 2 làm loãng chất lượng bậc 1 | Trung bình | Thời gian sửa lỗi trên bo mạch bậc 1 kéo dài · Kiểm thử hằng đêm thất bại thường xuyên hơn · Hỗ trợ bậc 3 chiếm quá 10% thời gian đội lõi | Phân tầng FR-TGT-08: đội lõi chỉ cam kết bậc 1 và bậc 2; bậc 3 do cộng đồng tự port và tự kiểm chứng. Mọi ngưỡng trong §9 và §11 vẫn neo vào bậc 1. Mỗi khối Giai đoạn 2 chỉ thêm tối đa một bo mạch tham chiếu |

### 13.3 Giả định cần kiểm chứng

Kế thừa từ Phụ lục G của tài liệu nguồn. Mỗi giả định có phương pháp đo và mốc đánh giá.

| # | Giả định | Phương pháp kiểm chứng | Mốc |
|:---:|:---|:---|:---:|
| **G-a** | Đơn giá quản trị fleet $1/thiết bị/tháng là mức thị trường chấp nhận | Thử nghiệm gói nâng cao với 5 khách hàng đầu; đo mức sẵn sàng chi trả thêm | Tháng 6 |
| **G-b** | Tỷ lệ chuyển đổi `sim` → phần cứng ≥ 15% | Số liệu ẩn danh từ CLI (FR-TEL-01); rà soát ở mốc 100 lập trình viên | Tháng 3 |
| **G-c** | Định tuyến hai mô hình tiết kiệm ≥ 60% chi phí token | Đo trên lưu lượng thực qua lớp trừu tượng provider, tách theo nhóm tác vụ | Tháng 6 |
| **G-d** | Cộng đồng thực sự muốn chia sẻ và tái sử dụng gate | Tần suất tải và kế thừa trên Registry miễn phí trong 12 tháng | Tháng 12 |
| **G-e** | Tái hiện vết ghi giảm 70% chuyến đi hiện trường | Dữ liệu bảo hành thực tế từ 3 khách hàng AURA đầu tiên, phân loại nguyên nhân sự cố | Tháng 9 |

---

## 14. Ngoài phạm vi

Danh mục loại trừ tường minh. Mọi đề xuất thuộc danh mục này bị bác bỏ trừ khi có quyết định thay đổi phạm vi chính thức.

| Hạng mục | Trạng thái | Tiêu chí | Điều kiện xem xét lại |
|:---|:---|:---:|:---|
| Marketplace thương mại có thu phí | Chặn | PF-3 | Đạt toàn bộ cột mốc G1–G4 |
| Thanh toán tự động giữa agent | Chặn | PF-4 | Đạt cột mốc và có đánh giá pháp lý riêng |
| Chương trình chứng nhận phần cứng có thu phí | Chặn | PF-3 | Đạt cột mốc và có quy trình kiểm chuẩn độc lập |
| Thị giác máy tính (camera, NPU) | **Đưa vào Giai đoạn 2**, tách hai bước | PF-1, PF-2 | **2a đặt chỗ kiến trúc:** RFC-0002 được phê duyệt · **2b hiện thực:** nhu cầu camera đo được từ khách hàng thật, TTFV thoại vẫn < 10 phút |
| Jetson | **Đưa vào Giai đoạn 2** ở bậc 2 (FR-TGT-08) | PF-3 | RFC-0002 được phê duyệt và có nhu cầu đo được từ khách hàng thật |
| Matter, HomeKit | Hoãn sau 12 tháng | PF-3 | Có nhu cầu đo được từ khách hàng thật |
| SSO/SAML, chứng chỉ SOC 2 | Hoãn sau 12 tháng | PF-3 | Có hợp đồng doanh nghiệp yêu cầu cụ thể |
| Multi-region, on-premise | Hoãn sau 12 tháng | PF-3 | Có ràng buộc chủ quyền dữ liệu từ khách hàng thật |
| Mô hình dự phòng cục bộ đã tinh chỉnh | Hoãn có điều kiện | PF-3 | Xuất hiện dấu hiệu cảnh báo R-4 hoặc R-6 |
| Dashboard BI tùy biến, engine cảnh báo phức tạp | Hoãn vô thời hạn | PF-1, PF-3 | Không có |
| Kiến trúc Kubernetes | Hoãn vô thời hạn | PF-1 | Vượt quy mô 50.000 thiết bị |
| Tự huấn luyện tinh chỉnh mô hình | Hoãn vô thời hạn | PF-3 | Không có |
| Huấn luyện wake-word tùy biến | Hoãn sau v1.0 | PF-1 | Sau khi runtime `esp32s3` ổn định |
| Đội lõi tự port thêm biến thể bo mạch ngoài bậc 1 và bậc 2 | Hoãn vô thời hạn | PF-1 | Không có — độ phủ phần cứng mở rộng qua **bậc 3 do cộng đồng port** (FR-TGT-08), không qua đội lõi |
| Chương trình chứng nhận phần cứng **miễn phí, tự kiểm chứng** | **Đưa vào Giai đoạn 2** | PF-2, PF-3 | ≥ 3 bản port bậc 3 vượt Bộ kiểm thử tuân thủ *(phân biệt với dòng chứng nhận **có thu phí** phía trên, vẫn ở trạng thái Chặn)* |

---

## 15. Quyết định kỹ thuật đã chốt

Các quyết định nền tảng đã được chốt chính thức làm cơ sở bắt đầu hiện thực.

**Đây là sổ quyết định duy nhất của dự án.** Mọi quyết định kỹ thuật, kể cả quyết định phát sinh trong lúc thực thi, đều được cấp mã và ghi tại đây. `neuroedge-roadmap.md` §10 không định nghĩa quyết định mới — nó chỉ theo dõi **hạn chốt, người quyết và trạng thái** của cùng bộ mã này.

| # | Hạng mục | Trạng thái | Nội dung đã chốt chính thức |
|:---:|:---|:---:|:---|
| **Q-1** | Phiên bản Python tối thiểu | **ĐÃ CHỐT** | **Python 3.11+** (NFR-COMP-05: tích hợp sẵn `tomllib`, TaskGroup/ExceptionGroup, tốc độ bytecode nhanh hơn 25%). |
| **Q-2** | Bo mạch tham chiếu chính thức | **ĐÃ CHỐT** | **ESP32-S3-Box-3** (§3.4: tích hợp sẵn LCD ST7789, dual-mic ES7210, loa ES8311, dock GPIO; tránh nhiễu clock I2S do câu dây). |
| **Q-3** | Ngân sách SRAM/PSRAM & firmware | **ĐÃ CHỐT** | **SRAM tự do ≥ 120 KB**, **PSRAM ≥ 2 MB** (ringbuffer + VAD/wake-word), **Firmware ≤ 3,5 MB** (vừa phân vùng kép A/B 16MB Flash). |
| **Q-4** | Nhà cung cấp System 1/2 ở v1.0 | **ĐÃ CHỐT** | **System 1:** Jev (cloud) & Local SLM fallback (Sherpa-ONNX intent extractor); **System 2:** Claude Sonnet 3.5 & GPT-4o-mini. Kết nối **qua lớp trừu tượng provider OSS (OpenAI-compatible)**, không ràng buộc vào một proxy cụ thể. |
| **Q-5** | Xác thực & chống lạm dụng Registry | Chờ v1.1 | Thiết kế trước Tháng 4 theo chuẩn CNCF ORAS và GitHub token. |
| **Q-6** | Chính sách lưu trữ vết ghi Fleet OS | Chờ v1.1 | Quyết định trước Tháng 4 theo các gói dịch vụ Fleet Standard / Enterprise. |
| **Q-7** | Từ khóa kích hoạt mặc định v1.0 | **ĐÃ CHỐT** | *"Hey Neuro"* (tiếng Anh) qua mô hình `microWakeWord` (tối ưu cho Box-3) và `openWakeWord` (Linux/Sim). |
| **Q-8** | Ngôn ngữ lõi firmware | **ĐÃ CHỐT** | **C/C++ trên ESP-IDF** cho `esp32s3`; Python cho `sim` và `linux`. Kéo theo nghĩa vụ đặc tả chuẩn tắc và bộ vector tuân thủ dùng chung cho hai hiện thực. |
| **Q-9** | Lượng giá CEL trên vi điều khiển | **ĐÃ CHỐT** | **Phương án A** — `neuroedge build` biên dịch CEL thành cây quyết định JSON phẳng; firmware chỉ duyệt cây. Không nhúng CEL VM trên thiết bị. |
| **Q-10** | Mức độ phụ thuộc vào LiteLLM | Chờ Tuần 2 | Dùng như thư viện định tuyến hay tích hợp sâu. Hạn đẩy sớm theo CR-1.0 vì lớp provider nay thuộc lõi OSS. |
| **Q-11** | Ngoại lệ giấy phép: Hawkbit EPL-2.0, EMQX BSL, LiteLLM | Chờ Tuần 2 | Chặn thiết kế phụ thuộc Khối 2 **và** `TSK-S2-11` ở Sprint 2. Phải bao gồm chính sách cho phụ thuộc bắc cầu. |
| **Q-12** | Chuẩn kết nối nhà cung cấp AI | **ĐÃ CHỐT** | Chuẩn mặc định là **OpenAI API**; provider chưa tương thích kết nối qua **adapter do người dùng tự viết**. Áp dụng đồng nhất cho LLM, ASR và TTS (FR-MDL-07→09). |
| **Q-13** | Phân tầng cam kết theo bậc target | **ĐÃ CHỐT** | Ba bậc: **bậc 1** (`sim`, `linux`, `esp32s3`) giữ toàn bộ cam kết chất lượng hiện hành; **bậc 2** do đội lõi bảo trì với cam kết hẹp hơn; **bậc 3** do cộng đồng port và tự kiểm chứng qua Bộ kiểm thử tuân thủ. Nguyên tắc P-2 giữ nguyên hệ quả kỹ thuật ở mọi bậc (FR-TGT-08). |

---

# Phụ lục

## Phụ lục A — Ma trận truy vết yêu cầu

Đối chiếu từ mục tiêu sản phẩm tới yêu cầu và tiêu chí nghiệm thu.

| Mục tiêu | Yêu cầu chi phối | Chỉ số | Tiêu chí nghiệm thu |
|:---|:---|:---|:---|
| **M1** — TTFV dưới 10 phút | FR-DX-01, FR-DX-02, FR-TGT-01, FR-TGT-06, FR-CLI-01 | TTFV trung vị | A1 |
| **M2** — Mọi hành động qua hợp đồng | FR-ACE-01→07, FR-GATE-01→10, FR-HAL-07 | Số đường tắt tới actuator | A3, A4, A5 |
| **M3** — Nhất quán các môi trường bậc 1 | FR-TGT-01→05, FR-CI-07, FR-HAL-06 | Kết quả `neuroedge verify` | A2 |
| **M4** — Tái hiện sự cố hiện trường | FR-CI-01, FR-CI-02, FR-TRC-01→08, FR-FLT-05 | Thời gian từ sự cố tới tái hiện | A7, C7 |
| **M5** — Cập nhật quy mô lớn an toàn | FR-OTA-01→04, FR-FLT-02 | Số thiết bị brick | C1 |

### Đối chiếu nguyên tắc bất biến

| Nguyên tắc | Yêu cầu hiện thực hóa | Yêu cầu kiểm chứng |
|:---|:---|:---|
| **P-1** Hợp đồng chuẩn kiểu | FR-ACE-01, FR-ACE-02, FR-HAL-07 | A3 |
| **P-2** Các môi trường ngang hàng | FR-TGT-01→05, FR-TGT-08 | A2 *(ràng buộc ở bậc 1)* |
| **P-3** Giá trị ở quản trị fleet | FR-OTA-04, NFR-COMP-02, NFR-COMP-03 | Rà soát ranh giới §6.4 tài liệu nguồn |
| **P-4** Mô hình thay thế được — cloud-first, provider-pluggable | FR-MDL-01→04, FR-MDL-07→09, FR-PER-07, FR-GW-01→07 | Bài kiểm thử đổi mô hình và đổi provider STT/TTS chỉ bằng cấu hình, không sửa mã agent |
| **P-5** Hiệu ứng mạng từ chia sẻ gate và thành phần mở rộng | FR-GATE-05→08, FR-REG-01, FR-REG-04, FR-REG-08 | B3, C5 |

### A.3 Đối chiếu yêu cầu phi chức năng

Yêu cầu phi chức năng **không được truy vết qua task roadmap** mà qua tiêu chí nghiệm thu và rà soát định kỳ — vì chúng là thuộc tính xuyên suốt của hệ thống, không phải hạng mục công việc rời. Bảng này là đường nối duy nhất giữa NFR và bằng chứng kiểm chứng.

| Nhóm | Yêu cầu | Cách kiểm chứng | Tiêu chí nghiệm thu |
|:---|:---|:---|:---:|
| **NFR-PERF** | 01→05, 07 | Đo trên lưu lượng thực, tách theo nhóm tác vụ | C2, C3, C4 |
| **NFR-PERF** | 06 | Đo thời gian chạy bộ Action CI của dự án mẫu trong CI | — *(chỉ số nội bộ)* |
| **NFR-RES** | 01 | Kiểm thử chịu tải 24 giờ trên bo mạch tham chiếu | A6 |
| **NFR-RES** | 02, 03 | Đo bộ nhớ và kích thước firmware trong CI; ngưỡng chốt tại Q-3 | A6 |
| **NFR-RES** | 04 | Bộ kịch bản suy giảm: mất mạng, timeout, dữ liệu mô hình không hợp lệ | A4 |
| **NFR-REL** | 01 | Chiến dịch OTA canary trên 1.000 thiết bị | C1 |
| **NFR-REL** | 02 | Bộ kịch bản suy giảm — trùng cơ chế với NFR-RES-04 | A4 |
| **NFR-REL** | 03 | Nhật ký kiểm thử hằng đêm trên bo mạch thật | A2 |
| **NFR-REL** | 04 | Chạy lại bộ vết ghi hồi quy sau mỗi lần nâng phiên bản phụ | A7 |
| **NFR-SEC** | 01 | Rà soát mã và kiểm thử thâm nhập tìm đường tắt tới actuator | A3 |
| **NFR-SEC** | 02, 03, 06 | Rà soát cấu hình thiết bị và quy trình nạp firmware trên bo mạch tham chiếu | A6 |
| **NFR-SEC** | 04, 05, 08 | Rà soát cấu hình mạng và kênh truyền tới provider | C7 |
| **NFR-SEC** | 07 | Kiểm thử sandbox với mã bên thứ ba | — *(v1.1, gắn FR-REG-07)* |
| **NFR-PRIV** | 01, 03, 04 | Rà soát nội dung tệp vết ghi sinh ra ở chế độ mặc định | A7 |
| **NFR-PRIV** | 02 | Rà soát ranh giới xử lý on-device và cloud theo P-4 | — *(rà soát kiến trúc)* |
| **NFR-OBS** | 01→03 | Thẩm định tệp vết ghi bằng `neuroedge trace validate` | A7 |
| **NFR-COMP** | 01→04 | Rà soát ranh giới mã nguồn mở và thương mại (proposal §6.4) | A9 |
| **NFR-COMP** | 05, 06 | Ma trận nền tảng chạy trong CI | A2 |

### A.4 Đối chiếu các nhóm yêu cầu chức năng còn lại

A.1 truy vết theo **mục tiêu sản phẩm**, A.2 theo **nguyên tắc bất biến**. Một số nhóm yêu cầu chức năng không rơi vào hai trục đó nhưng vẫn phải có đường kiểm chứng; bảng này đóng phần còn lại.

| Nhóm | Yêu cầu | Vai trò | Tiêu chí nghiệm thu |
|:---|:---|:---|:---:|
| **FR-HAL** | 01→05 | Hợp đồng năng lực và đối chiếu lúc build | A2, A3 |
| **FR-PER** | 01→06 | Chuỗi xử lý giọng nói và máy trạng thái hội thoại | A6, C2 |
| **FR-CI** | 03→06 | Thư viện assert, mẫu chuẩn, chạy trong CI, nightly | A2, A7 |
| **FR-TRC** | 09, 10 | Lệnh thẩm định và quy ước đường dẫn vết ghi | A7 |
| **FR-GOV** | 01→04 | Quản trị lược đồ mở và quy trình RFC | A9 |
| **FR-CLI** | 02→08 | Bề mặt dòng lệnh | A1, A8 |
| **FR-DX** | 03→07 | Khuôn mẫu dự án, ví dụ mẫu, thông báo lỗi | A1, A8 |
| **FR-TGT** | 07 | Mô phỏng kịch bản suy giảm trong `sim` | A4 |
| **FR-MDL** | 05, 06 | Định tuyến khai báo và ghi nhận tỷ lệ S1/S2 | C4 |
| **FR-FLT** | 01, 03, 04, 06 | Provisioning, giám sát, cấu hình từ xa, thiết bị ảo | C1, roadmap TR-7 |
| **FR-REG** | 02, 03, 05, 06 | Manifest, khai báo năng lực, định danh, đo lường | C5, roadmap TR-4, TR-5 |
| **FR-TEL** | 01→06 | Viễn trắc và đo đạc | B4, B5, §12.2 của tài liệu này |

**Độ phủ truy vết:** sau A.1 đến A.4, **mọi yêu cầu FR và NFR trong tài liệu này đều có ít nhất một đường kiểm chứng**. Ba phụ lục sau A.1 tồn tại vì ba trục truy vết khác nhau — mục tiêu, nguyên tắc, và thuộc tính hệ thống — và một yêu cầu có thể xuất hiện ở nhiều trục. Không có yêu cầu nào đứng ngoài cả bốn.

---

## Phụ lục B — Danh mục mã lỗi chuẩn

Mọi mã lỗi **BẮT BUỘC** nêu đủ ba thành phần: sai ở đâu, vì sao, và cách xử lý (FR-DX-04).

| Mã lỗi | Thời điểm phát sinh | Nguyên nhân | Hành vi hệ thống |
|:---|:---|:---|:---|
| `CapabilityMismatchError` | Build | Agent yêu cầu năng lực bo mạch không khai báo | Dừng build, không sinh firmware, chỉ rõ dòng mã gọi |
| `ActionContractViolation` | Chạy | Gọi hành động vật lý không qua `c.do()` | Ném ngoại lệ, chân GPIO không được kích |
| `GateFailClosedException` | Chạy | Gate không thẩm định được trong ngân sách và `fail: closed` | Chặn hành động, ghi lý do vào vết ghi |
| `GateResolutionError` | Build hoặc chạy | Gate con nới lỏng `allow_when`, vượt 3 cấp kế thừa, hoặc có vòng lặp | Từ chối phân giải, nêu chuỗi kế thừa gây lỗi |
| `TargetEquivalenceError` | `neuroedge verify` | Phán quyết gate hoặc trạng thái GPIO lệch giữa các môi trường | Báo lỗi, chỉ rõ sự kiện lệch đầu tiên |
| `TraceSchemaError` | `neuroedge trace validate` | Tệp vết ghi không hợp lệ theo JSON Schema | Báo lỗi kèm đường dẫn trường sai |
| `ModelUnavailableError` | Chạy | Nhà cung cấp chính và fallback đều không phản hồi | Áp dụng chính sách `fail` của gate liên quan |

## Phụ lục C — Quy ước định danh và phiên bản

| Đối tượng | Quy ước | Ví dụ |
|:---|:---|:---|
| Agent | `<tên>@<semver>` | `villa-concierge@0.3.1` |
| Gate | `<tên>@<semver>.yaml` | `unlock_door@1.2.0.yaml` |
| Gate trên Registry | `neuroedge://gates/<nhóm>/<tên>@<semver>` | `neuroedge://gates/hospitality/dual-auth-lock@1.0.0` |
| Bo mạch | `<tên>-<phiên-bản>` | `villa-panel-v2` |
| Phiên tương tác | `sess_<8 ký tự hex>` | `sess_8f9a2b1c` |
| Vết ghi thường | `traces/<mô-tả>.json` | `traces/happy-path.json` |
| Vết ghi sự cố | `traces/incidents/<session_id>.json` | `traces/incidents/sess_8f9a2b1c.json` |
| Golden Reference | `traces/golden/<kịch-bản>.json` | `traces/golden/unlock-denied.json` |
| Lược đồ công khai | `https://schema.neuroedge.dev/<loại>/v<n>.json` | `https://schema.neuroedge.dev/trace/v1.json` |

## Phụ lục D — Cấu trúc Monorepo và Giao thức Truyền dẫn

### D.1 Bố cục Monorepo tiêu chuẩn

```text
neuroedge/
├── schemas/                     # Nguồn sự thật duy nhất (Single Source of Truth)
│   ├── trace.v1.json            # JSON Schema draft 2020-12 cho tệp Vết ghi
│   ├── gate.v1.json             # JSON Schema cho Cổng an toàn (Gate)
│   └── board.v1.json            # JSON Schema đối chiếu năng lực bo mạch HAL
├── python/                      # Gói mã nguồn mở PyPI (pip install neuroedge)
│   ├── pyproject.toml           # Cấu hình Python 3.11+, Hatchling/Poetry
│   ├── neuroedge/
│   │   ├── cli/                 # CLI Surface: Typer + Rich + Copier
│   │   ├── hal/                 # 5 nguyên thủy HAL & Capability Matcher
│   │   ├── engine/              # Action Contract Engine & Google CEL Compiler
│   │   ├── perception/          # Voice pipeline, VAD (Silero), Barge-in (Pipecat)
│   │   ├── testing/             # Action CI Engine (pytest-neuroedge, replay)
│   │   └── sim/                 # Web Simulator Server + Wokwi Elements UI
│   └── tests/                   # Test suite cho Python SDK
├── targets/                     # Hiện thực HAL cho từng môi trường
│   ├── sim/                     # Backend mô phỏng ảo trong bộ nhớ (Python)
│   ├── linux/                   # Backend Linux: gpiod v2 + ALSA (Python)
│   └── esp32s3/                 # Firmware ESP-IDF (C/C++, port driver XiaoZhi)
│       ├── sdkconfig.defaults   # Cấu hình tối ưu PSRAM, I2S, FreeRTOS 1000Hz
│       ├── partitions.csv       # Phân vùng nạp kép A/B OTA 16MB Flash
│       └── components/          # Audio codec ES8311/ES7210, LCD ST7789, OTA agent
├── fixtures/                    # Dữ liệu kiểm thử mẫu dùng chung (Test Vectors)
│   └── traces/                  # happy-path.json, unverified_attempt.json, ...
└── NOTICE                       # Ghi nhận bản quyền các dự án OSS đã port
```

### D.2 Giao thức Truyền dẫn & Định dạng Vết ghi (Wire Protocol)

1. **Giao thức mạng Wi-Fi / LAN:** `WebSocket` bảo mật truyền luồng âm thanh Opus (Binary Frame) và sự kiện vết ghi JSON (Text Frame).
2. **Giao thức cổng nối tiếp UART:** Đóng gói khung nhị phân chuẩn `SLIP` hoặc dòng văn bản phân cách bằng ký tự xuống dòng (JSON Lines) ở tốc độ baud 921600.
3. **Định dạng âm thanh nén:** Opus Voice Mode (16 kbps, 16 kHz mono, kích thước khung 20 ms = 320 mẫu).

---

*Hết tài liệu*
