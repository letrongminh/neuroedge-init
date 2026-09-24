# NeuroEdge — Product Requirements Document

## Nền tảng Hợp đồng Hành động Chuẩn kiểu cho Physical AI

**Phiên bản PRD:** 1.3
**Ngày phát hành:** 23 tháng 9, 2026
**Tài liệu nguồn:** `neuroedge-proposal.md` v5.4
**Trạng thái:** Bản thảo chờ phê duyệt kỹ thuật
**Thay đổi ở 1.3 (2026-09-23):** ghi các quyết định Q-14 → Q-20 và RFC-0004; cập nhật Q-4, Q-10, Q-11 · fallback lệnh cố định cục bộ lên P0 (Q-14) · đầu vào mặc định của `sim` là gõ chữ (Q-15) · FR-GATE-02/03/06 khớp RFC-0001 và RFC-0004 · FR-CLI bổ sung `gate lint`, `gate resolve`, `board` và tiêu chí nghiệm thu từng dòng · Phụ lục B khớp tên lớp lỗi trong mã · sửa ma trận truy vết Phụ lục A
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

Mọi mã và ký hiệu dùng trong tài liệu này (`FR-*`, `NFR-*`, `P0`–`P2`, `A1`–`C7`, `Q-N`, `PF-N`, `R-N`, `U`/`J`, `§x.y`…) được giải mã ở **[`docs/user/thuat-ngu.md`](docs/user/thuat-ngu.md)** — nơi duy nhất, kèm chỗ định nghĩa đầy đủ.

Từ khóa **BẮT BUỘC**, **NÊN**, **CÓ THỂ** được hiểu theo nghĩa của RFC 2119.

---

## 1. Mục tiêu sản phẩm

### 1.1 Vấn đề cần giải quyết

Chưa có công cụ nào kiểm thử được hành vi vật lý của AI agent **trước khi** thiết bị vận hành ngoài hiện trường. Khi một agent vật lý ra quyết định sai, động cơ đã quay, rơ-le đã đóng, chốt cửa đã mở — các tác động này là bất khả nghịch. Một trợ lý giọng nói trong nhà trộn cả hai loại hành vi trong một cuộc trò chuyện: câu trả lời từ knowledge base hay bản tin sai thì sửa được, còn tắt đèn khi vẫn còn người trên cầu thang thì không — sản phẩm phải tách hai đường đó ra (proposal §0.2).

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
| **P-1** | Hành động vật lý là hợp đồng chuẩn kiểu, không phải lời gọi hàm tự do | HAL từ chối mọi lệnh actuator thiếu chữ ký gate đã pass. Mọi đường từ ngôn ngữ tới hành động — giọng nói offline, LLM, client MCP — là một **tool call có kiểu** đi qua cùng gate (Q-24, `docs/spec/tool_calling.md`) |
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
| 2–4 | `neuroedge run --target sim`, gõ một lệnh (vd *"mở cửa phòng 101"*) | Không mạng, không key, tất định: bộ khớp ngữ pháp lệnh cục bộ nhận lệnh; thấy actuator ảo chuyển động và phán quyết gate. Giọng nói là tuỳ chọn — cần key STT cloud *(Q-15)* | FR-TGT-01, FR-DX-02 |
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
| **FR-HAL-01** | Hệ thống cung cấp đúng 5 nguyên thủy phần cứng: `audio.in`, `audio.out`, `digital.out`, `sensor.read`, `display`. Tập nguyên thủy **đóng cho v1.x**; mở rộng chỉ qua RFC *(nguyên thủy thị giác `vision.in`, tùy chọn theo bo mạch, dự kiến qua một RFC riêng ở Khối V1b của Giai đoạn 2 — RFC-0002 §9.1)* | P0 | Cả 5 nguyên thủy có hiện thực đầy đủ trên các môi trường bậc 1 | §3.3 |
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
| **FR-TGT-02** | Môi trường `linux` là môi trường chính thức ngang hàng, hỗ trợ RPi và x86 qua `gpiod` | P0 | Agent mẫu chạy thật trên RPi 5 và trên x86 Linux — agent mẫu cần `aec`, nên phụ thuộc Q-22 | §3.2 |
| **FR-TGT-03** | Môi trường `esp32s3` là môi trường chính thức ngang hàng, xây bằng ESP-IDF | P0 | Agent mẫu chạy thật trên bo mạch tham chiếu | §8.2 |
| **FR-TGT-04** | **Nguyên tắc tương đương:** cùng một tệp mã agent cho cùng chuỗi phán quyết trên mọi môi trường, không sửa một dòng | P0 | `neuroedge verify --targets sim,linux,esp32s3` đạt 100% | §3.2 |
| **FR-TGT-05** | Chuyển môi trường qua tham số `--target`; **cấm** rẽ nhánh logic theo target trong mã agent | P0 | Rà soát mã: không tồn tại biểu thức điều kiện theo tên target trong lớp ứng dụng | §4.1 |
| **FR-TGT-06** | `sim` cung cấp giao diện web hiển thị cảm biến ảo và trạng thái cơ cấu chấp hành | P0 | Mở được trong trình duyệt, phản ánh đúng trạng thái chân GPIO ảo theo thời gian thực; chạy không mạng (không tải CDN). Lệnh: `neuroedge run --ui` (TSK-S2-09) | §4.10 |
| **FR-TGT-07** | `sim` mô phỏng được kịch bản cảm biến và điều kiện mạng suy giảm | P1 | Khai báo được kịch bản mất mạng để kiểm thử fail-closed | §4.7 |
| **FR-TGT-08** | **Phân tầng target:** mỗi môi trường thực thi thuộc đúng một bậc cam kết — bậc 1 chính thức (`sim`, `linux`, `esp32s3`), bậc 2 mở rộng do đội lõi bảo trì, bậc 3 do cộng đồng port và tự kiểm chứng. Bậc được khai báo tường minh, không suy diễn | P0 | **Nghiệm thu ở Giai đoạn 2** — cần `TARGET_TIERS` (RFC-0002 PR2): mỗi target có bậc ghi trong tài liệu và trong bảng bậc của mã lõi (RFC-0002 §3b); `board.toml` không tự khai bậc; ngưỡng `verify` 100% chỉ ràng buộc bậc 1; bậc 3 không chặn phát hành. **Hiện tại chỉ có bậc 1** (`sim`, `linux`, `esp32s3`), kiểm chứng qua A2 | §3.2 |

**Giới hạn đã biết, phải nêu rõ trong tài liệu kỹ thuật:** `sim` không mô phỏng phản xạ âm học phòng vang, nhiễu micro, beamforming mảng micro, và phân mảnh bộ nhớ trên vi điều khiển. Các nhóm lỗi này được kiểm soát bằng kiểm thử nightly trên bo mạch thật (NFR-REL-03).

### 4.3 Trừu tượng hóa mô hình AI (FR-MDL)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-MDL-01** | Mọi truy cập mô hình đi qua interface `SystemOne` hoặc `SystemTwo`; giao diện kết nối mặc định tuân chuẩn OpenAI API | P0 | Không tồn tại lời gọi trực tiếp SDK nhà cung cấp trong lõi | §3.6 |
| **FR-MDL-02** | `SystemOne` hỗ trợ đúng 3 kiểu nguyên thủy: `bool`, `level`, `choice` | P0 | Ba kiểu chạy được và ánh xạ trực tiếp vào khối `evaluate` của gate | §3.6, Phụ lục B.2 |
| **FR-MDL-03** | Cả hai interface bắt buộc khai báo được đường dẫn dự phòng (`fallback`). Với `SystemOne`, fallback cục bộ là **bộ nhận diện lệnh cố định** (ngữ pháp lệnh → intent kèm độ tin cậy) và là P0 *(Q-14)* | P0 | Ngắt nhà cung cấp chính → hệ thống tự chuyển fallback, ghi sự kiện vào vết; mất mạng → `SystemOne` lượng giá bằng ngữ pháp lệnh cục bộ *(Q-14)* | §3.6 |
| **FR-MDL-04** | Thay nhà cung cấp mô hình không yêu cầu sửa mã agent hay sửa gate | P0 | Đổi `SystemOne` sang mô hình cục bộ chỉ bằng thay đổi cấu hình | §3.6 |
| **FR-MDL-05** | Chính sách định tuyến System 1 / System 2 là cấu hình khai báo, không viết cứng | P1 | Đổi ngưỡng tự tin leo thang bằng cấu hình, không biên dịch lại | §3.5 |
| **FR-MDL-06** | Hệ thống ghi nhận tỷ lệ sử dụng System 1 / System 2 và chi phí từng lượt | P0 *(System 2: mỗi lượt gọi model một sự kiện `system_two_call` — provider, model, độ trễ, token, `cost_usd`; không prompt, không key — TSK-S2-11. Tỷ lệ S1/S2 đọc từ `intent_extracted` và `system_two_call`, chưa có tổng hợp)* | Số liệu xuất hiện trong tệp vết ghi của mỗi phiên | §12.1 |
| **FR-MDL-07** | **Provider pluggable:** LLM, ASR và TTS kết nối qua chuẩn OpenAI API hoặc adapter do người dùng tự viết | P0 *(LLM của System 2 đạt: bảng `[system_two]`, LiteLLM, `api_base` cho endpoint tương thích OpenAI — TSK-S2-11; ASR/TTS: TSK-S3-13)* | Thêm một provider tương thích OpenAI chỉ bằng cấu hình endpoint và khóa, không sửa mã | §3.6, §6.1 |
| **FR-MDL-08** | **Adapter tùy chỉnh:** người dùng viết được logic kết nối riêng cho provider chưa hỗ trợ chuẩn OpenAI | P0 *(LLM đạt: `provider = "python:pkg.mod:factory"`, hợp đồng `neuroedge/models/providers/base.py` — TSK-S2-11)* | Một adapter mẫu do bên ngoài viết chạy được mà không sửa lõi NeuroEdge | §3.6 |
| **FR-MDL-10** | **Hành động là tool call (Q-24):** mọi `@action` là một tool có schema sinh từ chữ ký; `SystemOne`, `SystemTwo`, ngữ pháp lệnh cục bộ và client MCP gọi hành động bằng cùng một `ToolCall`, qua cùng một gate — theo `docs/spec/tool_calling.md` | P0 | Tool lạ hoặc tham số lạ/sai kiểu ⇒ `REJECTED`, không chân nào đổi; cùng một lời gọi từ nguồn khác nhau nhận cùng phán quyết trừ khi gate đọc `call_source`; mất mạng thì câu khớp ngữ pháp vẫn thành tool call | §3.6, Q-24 |
| **FR-MDL-12** | **System 2 là MCP host (Q-27):** gọi tool của thiết bị qua MCP server của chính agent (vẫn qua gate) và tool **thông tin** của MCP server bên ngoài khai trong `[mcp.servers]` (allowlist); kết quả bên ngoài là dữ liệu không tin cậy | P0 | Tool ngoài allowlist ⇒ `REJECTED`; server không chạy ⇒ `mcp_server_unavailable`, tool thiết bị vẫn chạy; nội dung bên ngoài bị cài lệnh không vượt được gate; vết ghi chỉ có digest | `docs/spec/tool_calling.md` §10 |
| **FR-MDL-11** | **Vòng tool của System 2:** kết quả mỗi tool call (kể cả BLOCK và lý do) trả lại cho System 2 để trả lời người dùng; số vòng có giới hạn khai báo | P0 *(có trên `sim` — TSK-S3-28; với provider thật — TSK-S2-11)* | Gate chặn ⇒ System 2 nói lý do thay vì lặp lại lời gọi; quá giới hạn vòng ⇒ dừng, ghi sự kiện | `docs/spec/tool_calling.md` §4 |
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
| **FR-PER-06** | Runtime giọng nói trên `esp32s3` tối ưu bộ nhớ, gồm thu/phát âm thanh, WebRTC AEC, VAD libfvad *(khớp proposal §3.4)*, Opus streaming, máy trạng thái hội thoại, thẩm định gate và bộ nhận diện lệnh cố định cục bộ *(ESP-SR MultiNet hoặc TFLite Micro / ESP-NN, chọn ở Khối 1b — Q-14)*. **Không bắt buộc chạy STT/TTS trên thiết bị** | P0 | Chạy ổn định liên tục 24 giờ trên bo mạch tham chiếu với pipeline thu/phát + máy trạng thái + gate, không tràn bộ nhớ | §8.2 |
| **FR-PER-07** | **Cloud-first voice:** STT và TTS mặc định chạy trên cloud qua provider; vi điều khiển chỉ truyền luồng âm thanh lên và nhận luồng âm thanh về | P0 | Vòng lặp thoại chạy end-to-end trên bo mạch tham chiếu với STT/TTS đặt ở provider cloud | §3.4, §6.1 |

---

## 5. Yêu cầu chức năng — An toàn hành động

### 5.1 Động cơ hợp đồng hành động (FR-ACE)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-ACE-01** | Mọi lệnh tới cơ cấu chấp hành **bắt buộc** đi qua gate tương ứng; không tồn tại đường tắt | P0 | Kiểm thử thâm nhập: không có API công khai nào kích hoạt GPIO mà bỏ qua gate | §3.5 |
| **FR-ACE-02** | Hành động vật lý chỉ gọi được qua `c.do()`; gọi trực tiếp sinh `ActionContractViolation` | P0 | Test khẳng định ngoại lệ được ném và chân GPIO không bị kích | §4.4 |
| **FR-ACE-03** | **Fail-closed mặc định:** timeout, hoặc mô hình trả dữ liệu không hợp lệ → chặn hành động. **Mất mạng** → gate vẫn lượng giá bằng bộ nhận diện lệnh cố định cục bộ; chỉ chặn với `gate_unreachable` khi fallback không có hoặc không chạy được *(Q-14)* | P0 | Kịch bản `network=offline` → gate lượng giá bằng ngữ pháp lệnh cục bộ: câu khớp đủ độ tin cậy được phán quyết theo `allow_when`, câu không khớp hoặc dưới ngưỡng bị BLOCK theo tiêu chí bình thường. Kịch bản `network=offline` + fallback không có/không chạy → hành động bị chặn với lý do `gate_unreachable` | §3.5 |
| **FR-ACE-04** | Decorator `@action` ràng buộc `requires` tham gia đối chiếu năng lực lúc build | P0 | Thiếu năng lực → build dừng, chỉ rõ dòng mã gọi | §4.4 |
| **FR-ACE-05** | Decorator `@action` bắt buộc trỏ tới một gate đã khai báo trong `agent.toml` | P0 | Thiếu khai báo gate → build dừng | §4.4 |
| **FR-ACE-06** | Mỗi phiên tương tác sinh một tệp vết ghi JSON đầy đủ | P0 | Tệp chứa độ trễ từng chặng, kết quả đánh giá gate, lệnh actuator | §3.5 |
| **FR-ACE-08** | **Ràng buộc tham số trong gate (Q-25):** gate khai khoảng/tập giá trị cho tham số của hành động; kế thừa chỉ thu hẹp | P0 *(✅ TSK-S3-25)* | Tool call với tham số ngoài khoảng ⇒ BLOCK `argument_out_of_range`, chân không đổi; gate con nới khoảng ⇒ `GateInheritanceError` | RFC-0005 |
| **FR-ACE-09** | **Nguồn gọi là dữ kiện tin cậy:** dispatcher chèn `call_source`; bên gọi không tự khai được | P0 | Tool call mang tham số `call_source` ⇒ `REJECTED`; gate giới hạn được nguồn gọi | `docs/spec/tool_calling.md` §5 |
| **FR-ACE-10** | **Chỉ người xác nhận `ask` (Q-26):** lời xác nhận đến từ kênh thiết bị, gắn với lần bị chặn, dùng một lần, có hạn | P0 *(✅ TSK-S3-26)* | Xác nhận từ `system_two` hoặc `mcp` bị từ chối; xác nhận quá hạn hoặc dùng lại ⇒ không có tác dụng; xác nhận hợp lệ ⇒ gate lượng giá lại, chỉ thay tiêu chí trong `confirms` (RFC-0006) | `docs/spec/tool_calling.md` §6 |
| **FR-ACE-07** | Tách biệt kiểu giữa hành vi phát ngôn (`c.say()`) và hành vi vật lý (`c.do()`) | P0 | `c.say()` không đi qua gate; `c.do()` luôn đi qua gate | §4.6 |

### 5.2 Định dạng cổng an toàn (FR-GATE)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-GATE-01** | Gate là tệp YAML có schema `neuroedge.gate/v1`, **không phải mã nguồn** | P0 | Gate đọc, diff và review được trong pull request | §3.5 |
| **FR-GATE-02** | Gate có 8 trường cấp cao: `schema`, `name`, `version`, `extends`, `evaluate`, `allow_when`, `on_block`, `budget`. Chỉ `schema`, `name`, `version` **luôn bắt buộc**; `evaluate`, `allow_when`, `on_block`, `budget` bắt buộc khi gate **không có** `extends` *(RFC-0001)*. `budget.fail` tuỳ chọn — vắng mặt nghĩa là `closed` | P0 | Thiếu trường bắt buộc theo điều kiện trên → `GateSchemaError`; gate có `extends` lược bốn trường kế thừa vẫn hợp lệ | Phụ lục B.1, RFC-0001 |
| **FR-GATE-03** | Khối `evaluate` hỗ trợ 3 kiểu: `bool`, `level`, `choice`, kèm toán tử điều kiện tương ứng. `allow_when` **dạng ánh xạ toán tử là dạng v1**; dạng chuỗi CEL chỉ được phép ở gate không có `extends` — trong chuỗi kế thừa bị từ chối, fail-closed, vì không chứng minh được con chặt hơn cha. *Cho tới khi trình biên dịch CEL xong (TSK-S2-06, đang hoãn), `gate lint` từ chối cả CEL ở gate độc lập (`GateSchemaError`) — fail-closed, không phải lượng giá thiếu* | P0 | Ba kiểu chạy đúng với toán tử `eq`, `lte`, `gte`, `in`, `not_in`, `confidence_gte`; `allow_when` dạng chuỗi trong chuỗi `extends` → `GateInheritanceError` | Phụ lục B.2, Q-9 |
| **FR-GATE-04** | Khối `on_block` hỗ trợ 4 hành vi: `escalate`, `deny`, `ask`, `degrade`. Ở v1.0, **mọi** `on_block` đều chặn hành động vật lý; `escalate`/`ask` ghi sự kiện + gọi hook (mặc định no-op); `degrade` chạy `fallback_action` qua gate của chính nó *(Q-17)* | P0 | Bốn hành vi chạy đúng và được ghi vào vết | Phụ lục B.3 |
| **FR-GATE-05** | Gate kế thừa được qua `extends` từ URI gate cơ sở | P0 | Kéo gate cộng đồng về, ghi đè phần riêng, chạy đúng | Phụ lục B.5 |
| **FR-GATE-06** | **Gate con chỉ được siết chặt, tuyệt đối không được nới lỏng** (B.5 nguyên tắc 2) — với `allow_when`, và từ RFC-0004 cả với `budget`/`on_block` *(Q-18)*: `p95_latency_ms` của con ≤ của cha; con không được tự đưa vào `degrade`/`fallback_action` mới (chỉ giữ nguyên của cha), được đổi sang `deny`/`escalate`/`ask` và đổi `to`/`message` | P0 | Gate con nới lỏng `allow_when`, `budget` hoặc `on_block` của cha → `GateInheritanceError` (NE2003, nguyên tắc 2), từ chối phân giải *(phần `budget`/`on_block`: TSK-S2-13)* | Phụ lục B.5, RFC-0004 |
| **FR-GATE-07** | `fail: open` **không kế thừa**; phải khai báo tường minh tại từng cấp (B.5 nguyên tắc 4). Từ RFC-0004: chuỗi đã phân giải thành `closed` (khai hoặc mặc định) thì gate con **không được** mở lại bằng `fail: open` *(Q-18)* | P0 | Gate cha `fail: open`, gate con không khai báo → gate con là `closed`; chuỗi đã `closed`, con khai `fail: open` → `GateInheritanceError` (NE2003, nguyên tắc 4) | Phụ lục B.5, RFC-0004 |
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
| **FR-DX-02** | Cài đặt và chạy `sim` **không yêu cầu** tài khoản, API key hay thẻ thanh toán. Đầu vào mặc định của `sim` là **gõ chữ** → bộ khớp ngữ pháp lệnh; giọng nói là tuỳ chọn *(Q-15)* | P0 | Máy sạch, không mạng nội bộ đặc biệt, không key: hoàn thành hành trình 10 phút bằng lệnh gõ chữ. `pip install neuroedge` không kéo LiteLLM — phụ thuộc cloud nằm ở extra `neuroedge[cloud]` *(Q-10)* | §4.10 |
| **FR-DX-03** | Time-to-first-value trung vị dưới 10 phút, đo trên 10 lập trình viên độc lập | P0 | Biên bản đo có mốc thời gian từng bước của 10 người | §12.1 |
| **FR-DX-04** | Mọi thông báo lỗi nêu rõ: cái gì sai, ở đâu, và cách xử lý | P0 | Rà soát toàn bộ mã lỗi tại Phụ lục B đạt đủ 3 thành phần | §4.9 |
| **FR-DX-05** | Tài liệu có ít nhất 3 ứng dụng mẫu hoàn chỉnh chạy được | P0 | Ba mẫu chạy thành công trên máy sạch theo hướng dẫn. Hiện có: `villa-concierge` (chốt cửa), `home-voice` (trợ lý giọng nói: RAG, tin tức, đèn) | §12.1 |
| **FR-DX-06** | Tài liệu có ít nhất 1 video hoặc ảnh động minh họa trực quan trong README | P0 | Có tài sản trực quan dưới 30 giây thể hiện vòng lặp giá trị | §12.1 |
| **FR-DX-07** | Công cụ lint của dự án mẫu chặn khẳng định so khớp văn bản do System 2 sinh ra | P1 | Test vi phạm FR-CI-L3 bị lint báo lỗi | §3.7 |

### 7.2 Giao diện dòng lệnh (FR-CLI)

**Hợp đồng mã thoát** *(`CHANGELOG.md` §2.3 — CI và Action CI neo vào nó)*: `0` phép kiểm tra đã chạy và **đạt** · `1` đã chạy và **không đạt** · `2` lệnh **chưa được hiện thực** (hoặc sai cú pháp lệnh). Lệnh chưa hiện thực **KHÔNG ĐƯỢC** thoát mã 0.

| Mã | Nhóm lệnh | Lệnh bắt buộc | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---|:---:|:---|:---:|
| **FR-CLI-01** | Khởi tạo | `neuroedge new <tên>` | P0 | Dự án sinh ra chạy `neuroedge test` thoát mã 0 ngay, không sửa gì (FR-DX-01) | §4.8 |
| **FR-CLI-02** | Phát triển | `neuroedge run --target sim` · `neuroedge run --target linux` · `neuroedge build --target esp32s3 --board <id>` | P0 | `run --target sim` nhận lệnh gõ chữ không cần key *(Q-15)*, kiểm năng lực agent ↔ bo mạch trước khi chạy (không hợp → mã 1); `run -c "<lệnh>"` chạy một lệnh rồi thoát mã 0 kể cả khi gate chặn; `build` gặp bất tương thích năng lực → mã 1, không sinh firmware (FR-HAL-04) | §4.8 |
| **FR-CLI-03** | Kiểm thử | `neuroedge test` · `neuroedge verify --targets sim,linux,esp32s3` | P0 | `test` thoát 0 khi mọi khẳng định đạt, 1 khi có khẳng định sai; `verify` lệch giữa các target → mã 1, chỉ rõ sự kiện lệch đầu tiên (FR-CI-07); quét được 0 artifact (gate, vết ghi chuẩn mực hoặc lượt replay) → `VerificationError` (NE4004), mã 1, không thoát 0 (TSK-S3-19) | §4.8 |
| **FR-CLI-04** | Chẩn đoán | `neuroedge record --target <t> --out <thư-mục>` · `neuroedge trace validate <tệp>` · `neuroedge replay <tệp> --target <t>` · `neuroedge trace view <tệp>` · `neuroedge trace export --format chrome <tệp>` | P0 · `view`/`export`: P1 | `record` sinh tệp qua được `trace validate`; `trace validate` có một tệp sai → cả lệnh mã 1 kèm `TraceValidationError`; `replay` cho cùng chuỗi phán quyết (FR-CI-02); `record --target esp32s3 --port <cổng>` đọc vết ghi từ UART (cả trên QEMU); `trace view` sinh một tệp HTML tĩnh mở không cần mạng | §4.8 |
| **FR-CLI-05** | Hệ sinh thái gate | `neuroedge gate publish <tệp>` · `neuroedge gate add <uri>` · `neuroedge gate explain <tệp\|uri>` | P1 | `publish` in mã băm SHA-256 của JSON chuẩn tắc RFC 8785, hai lần chạy cho cùng mã băm; `add` phân giải gate từ registry và nêu ràng buộc kế thừa sẽ áp đặt; `explain` nêu mỗi tiêu chí do cấp nào đưa vào, mệnh đề nào con siết chặt so với cha, ngân sách và `on_block` — gate phân giải lỗi → mã 1 kèm lỗi 3 thành phần | §4.8 |
| **FR-CLI-10** | Tích hợp tool | `neuroedge mcp tools [--json\|--openai] [--external]` · `neuroedge mcp serve [--agent a.toml] [--ui]` · `neuroedge mcp desktop-config [--agent a.toml] [--ui] [--write]` | P1 | `tools` in schema mỗi `@action`; `serve` là máy chủ MCP qua stdio (`--ui`: cùng phiên với giao diện web `sim`), mỗi `tools/call` đi qua `dispatch()` và gate (Q-24); `desktop-config` in (hoặc ghi, có sao lưu, chỉ đúng một mục `mcpServers`) cấu hình Claude Desktop bằng đường dẫn tuyệt đối; thiếu extra `mcp` ⇒ mã 1 kèm cách cài | §4.8 |
| **FR-CLI-09** | Cổng an toàn gate | `neuroedge gate lint [thư-mục] [--registry <dir>]` | P0 | **Đây là cổng kiểm tra an toàn**, không phải thẩm định lược đồ: phân giải toàn bộ chuỗi `extends` của mọi gate và cưỡng chế các nguyên tắc Phụ lục B.5 (kể cả phần mở rộng Q-18). Vi phạm → mã 1 kèm `GateInheritanceError` hoặc `GateSchemaError`; corpus phản chứng `fixtures/gates/invalid/` BẮT BUỘC thoát **đúng** mã 1 trong CI. Thẩm định lược đồ đơn lẻ không đủ để kết luận gate an toàn | Phụ lục B.5 |
| **FR-CLI-10** | Phân giải gate | `neuroedge gate resolve <tệp\|URI> [--json] [--registry <dir>]` | P0 | In chính sách hiệu dụng và mã băm; chuỗi vi phạm → mã 1 với cùng lỗi như `gate lint`; cùng đầu vào cho cùng mã băm | Phụ lục B.5 |
| **FR-CLI-11** | Bo mạch | `neuroedge board list` · `neuroedge board show <id>` · `neuroedge board validate <path>` *(RFC-0002 PR2, Giai đoạn 2)* | P0 · `validate`: Giai đoạn 2 | `board show` in năng lực theo 5 nguyên thủy (FR-HAL-01); `board validate` tệp sai lược đồ → mã 1 kèm `BoardCapabilityError`; trước RFC-0002 PR2, `board validate` thoát mã 2 | §4.2, RFC-0002 |

**Yêu cầu chung cho toàn bộ CLI:**

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu |
|:---|:---|:---:|:---|
| **FR-CLI-06** | Mọi lệnh trả mã thoát theo hợp đồng `0`/`1`/`2` ở trên, phục vụ tích hợp CI | P0 | Test CLI neo chặt mã thoát của từng lệnh; bước CI kiểm corpus phản chứng so khớp chính xác mã 1 |
| **FR-CLI-07** | Mọi lệnh có `--help` mô tả đủ tham số và ví dụ sử dụng | P0 | `--help` của mỗi lệnh thoát mã 0 và có ít nhất một ví dụ; test tự động duyệt toàn bộ lệnh |
| **FR-CLI-08** | Lệnh chạy lâu hiển thị tiến trình; lệnh phá hủy dữ liệu yêu cầu xác nhận | P1 | `build`, `verify`, `record` hiển thị tiến trình; lệnh xoá hoặc ghi đè dữ liệu không chạy khi chưa xác nhận và thoát khác 0 |

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

Bảy đường ray (FR-REG-01→07, khớp proposal §8.5) rẻ ở giai đoạn đầu nhưng **không thể bổ sung sau**. FR-REG-08 là phần mở rộng của đường ray 1 (kho Registry), không phải đường ray thứ tám.

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
| **NFR-RES-02** | Ngân sách SRAM/PSRAM tối thiểu còn tự do cho runtime | SRAM ≥ 120 KB · PSRAM ≥ 2 MB *(đã chốt tại §15 của tài liệu này, Q-3; dễ đạt hơn từ v1.0 nhờ cloud-first theo CR-1.0 — Change Request 1.0, 2026-09-21: chuyển sang cloud-first, provider-pluggable; bản ghi đầy đủ ở `CHANGELOG.md`)* | P0 |
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

Năm lớp phòng thủ theo proposal §5 — hành động vật lý, thiết bị, mạng, quyền riêng tư *(đặc tả riêng ở §9.5 của tài liệu này)*, cập nhật — hoạt động theo chế độ mặc định. Bảng dưới thêm hai nhóm yêu cầu ngoài năm lớp đó: mã bên thứ ba (đường ray 7, proposal §8.5) và nhà cung cấp bên ngoài (hệ quả của P-4).

| Mã | Lớp | Yêu cầu | Ưu tiên |
|:---|:---|:---|:---:|
| **NFR-SEC-01** | Hành động vật lý | Không có đường tắt tới cơ cấu chấp hành ngoài gate; mọi đánh giá gate được ghi vết | P0 |
| **NFR-SEC-02** | Thiết bị | Kích hoạt Secure Boot và mã hóa flash trên ESP32-S3; hỗ trợ TPM trên Linux | P0 |
| **NFR-SEC-03** | Thiết bị | Bo mạch tham chiếu có nút ngắt micro vật lý | P0 |
| **NFR-SEC-04** | Mạng | TLS 1.3 toàn tuyến; mTLS hai chiều thiết bị ↔ đám mây; certificate pinning | P0 |
| **NFR-SEC-05** | Mạng | Mỗi thiết bị có chứng chỉ mật mã riêng, thu hồi được | P0 |
| **NFR-SEC-06** | Cập nhật | Firmware ký số; xác minh chữ ký trên chip trước khi áp dụng | P0 |
| **NFR-SEC-07** | Mã bên thứ ba | Sandbox giới hạn quyền truy cập chân actuator nhạy cảm | P0 (v1.1) |
| **NFR-SEC-09** | Bên gọi tool | MCP ở v1.0 chỉ qua **stdio** (bên chạy tiến trình là người vận hành); transport mạng cần xác thực và là việc hoãn (`TODOS.md` #24). LLM và client MCP là bên gọi **không tin cậy** — `docs/spec/threat_model.md` §2b | P0 |
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
| **A4** | Fail-closed | **100%** kịch bản suy giảm đều chặn hành động — riêng mất mạng: lượng giá qua fallback lệnh cục bộ, chặn khi fallback không chạy *(Q-14)* | Bộ kịch bản: mất mạng (có và không có fallback), timeout, dữ liệu mô hình không hợp lệ |
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
| **C8** | Độ trễ quyết định `SystemOne` có cấu trúc | < 100 ms (NFR-PERF-04), đo trên lưu lượng thực qua FR-TEL-06 |

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
| Độ trễ quyết định `SystemOne` | v1.1 | < 100 ms | FR-TEL-06 |
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
| libfvad, Silero VAD, WebRTC AEC, Opus | Chuỗi xử lý tín hiệu | Ngừng bảo trì thượng nguồn | Bọc sau interface nội bộ, thay thế được từng thành phần |
| ESP-SR MultiNet hoặc TFLite Micro / ESP-NN | Bộ nhận diện lệnh cố định cục bộ trên `esp32s3` *(Q-14, thay Sherpa-ONNX)* | Giấy phép ESP-SR (theo hiểu biết: chỉ cho dùng trên SoC Espressif); bộ nhớ | Xác minh giấy phép trước Sprint 5; spike TSK-S1-10 đo thêm MultiNet; cùng một ngữ pháp lệnh cho mọi backend |
| `gpiod` | Truy cập GPIO trên Linux | Khác biệt giữa các bản phân phối | Giới hạn hỗ trợ ở Debian/Ubuntu (NFR-COMP-06) |
| Nhà cung cấp `SystemOne` | Quyết định có cấu trúc | Đổi giá, siết truy cập, tự ship framework | Interface từ ngày đầu (FR-MDL-01); fallback lệnh cố định cục bộ là P0 *(Q-14)* |
| Nhà cung cấp `SystemTwo` | Suy luận mở | Tương tự | Định tuyến đa nhà cung cấp (FR-GW-03) |
| SchemaStore | Nhận diện schema trong IDE | Quy trình duyệt chậm | Không chặn phát hành; là yêu cầu P1 |

### 13.2 Rủi ro sản phẩm

Mục này ghi rủi ro **sản phẩm và thực thi**. Rủi ro **chiến lược** (cạnh tranh, mô hình kinh doanh, phân mảnh phạm vi) nằm ở `neuroedge-proposal.md` §11 với hệ đánh số `#1–#6`. Ba cặp giao nhau giữa hai sổ: **R-4 ↔ §11 #1** (phụ thuộc nhà cung cấp mô hình) · **R-6 ↔ §11 #5** (mất kết nối đám mây) · **R-7 ↔ §11 #6** (phủ rộng phần cứng). Các rủi ro còn lại thuộc đúng một sổ.


| # | Rủi ro | Mức độ | Dấu hiệu cảnh báo sớm | Phương án ứng phó |
|:---:|:---|:---:|:---|:---|
| **R-1** | Phạm vi Khối 1b vượt thời hạn do tối ưu bộ nhớ vi điều khiển | Trung bình *(hạ từ Cao ở v1.1)* | Tuần 9 chưa chạy được vòng lặp thu/phát âm thanh trên bo mạch | Kiến trúc cloud-first đã đưa STT/TTS ra khỏi vi điều khiển, giảm đáng kể áp lực bộ nhớ (P-4, FR-PER-07). Nếu vẫn trượt: cắt phạm vi theo §3.4, giữ `esp32s3` ở mức phán quyết gate |
| **R-2** | Môi trường `sim` lệch khỏi phần cứng theo thời gian | Cao | `neuroedge verify` bắt đầu có sai lệch lẻ tẻ | Nightly trên bo mạch thật (NFR-REL-03); coi mọi sai lệch là lỗi chặn phát hành |
| **R-3** | Lập trình viên bỏ qua Action CI, chỉ dùng framework như thư viện thoại | Trung bình | Tỷ lệ áp dụng Action CI dưới 50% ở Beta | Đưa test gate vào scaffold mặc định; tài liệu lấy Action CI làm trung tâm |
| **R-4** | Nhà cung cấp mô hình thay đổi điều kiện truy cập | Trung bình | Thay đổi điều khoản API, vendor công bố SDK thiết bị | Mở rộng fallback cục bộ vượt ngữ pháp lệnh cố định của Q-14 |
| **R-5** | Hiệu ứng mạng chia sẻ gate không hình thành | Trung bình | Dưới 3 gate cộng đồng ở cuối Beta | Chuyển trọng tâm sang giá trị đơn lẻ (Action CI + Fleet), hoãn Marketplace vô thời hạn |
| **R-6** | Phụ thuộc provider cloud khi mất kết nối | Trung bình | Tỷ lệ phiên kết thúc với lý do `gate_unreachable` tăng bất thường · Gián đoạn tích lũy của provider vượt cam kết | Fail-closed đã chặn mọi hành động vật lý khi không thẩm định được gate (NFR-RES-04, A4); gate và máy trạng thái chạy hoàn toàn trên thiết bị. **Fallback cục bộ là P0** *(Q-14)*: bộ nhận diện lệnh cố định giữ gate lượng giá được khi mất mạng; `gate_unreachable` chỉ khi fallback không có hoặc không chạy được |
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
| Thị giác máy tính (camera, NPU) | **Đưa vào Giai đoạn 2**, tách hai bước | PF-1, PF-3 | **2a mở danh sách target:** RFC-0002 được phê duyệt · **2b hiện thực** (gồm RFC nguyên thủy `vision.in`): nhu cầu camera đo được từ khách hàng thật, TTFV thoại vẫn < 10 phút |
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
| **Q-4** | Nhà cung cấp System 1/2 ở v1.0 | **ĐÃ CHỐT** *(sửa 2026-09-23)* | **System 1:** Jev (cloud) + **fallback cục bộ = bộ nhận diện lệnh cố định** theo Q-14 (thay Sherpa-ONNX intent extractor); **System 2:** **`claude-sonnet-5`** & GPT-4o-mini, **qua LiteLLM** (Q-10). Kết nối qua lớp trừu tượng provider OSS (OpenAI-compatible, Q-12). |
| **Q-5** | Xác thực & chống lạm dụng Registry | Chờ v1.1 | Thiết kế trước Tháng 4 theo chuẩn CNCF ORAS và GitHub token. |
| **Q-6** | Chính sách lưu trữ vết ghi Fleet OS | Chờ v1.1 | Quyết định trước Tháng 4 theo các gói dịch vụ Fleet Standard / Enterprise. |
| **Q-7** | Từ khóa kích hoạt mặc định v1.0 | **ĐÃ CHỐT** | *"Hey Neuro"* (tiếng Anh) qua mô hình `microWakeWord` (tối ưu cho Box-3) và `openWakeWord` (Linux/Sim). |
| **Q-8** | Ngôn ngữ lõi firmware | **ĐÃ CHỐT** | **C/C++ trên ESP-IDF** cho `esp32s3`; Python cho `sim` và `linux`. Kéo theo nghĩa vụ đặc tả chuẩn tắc và bộ vector tuân thủ dùng chung cho hai hiện thực. |
| **Q-9** | Lượng giá CEL trên vi điều khiển | **ĐÃ CHỐT** | **Phương án A** — `neuroedge build` biên dịch CEL thành cây quyết định JSON phẳng; firmware chỉ duyệt cây. Không nhúng CEL VM trên thiết bị. |
| **Q-10** | Mức độ phụ thuộc vào LiteLLM | **ĐÃ CHỐT** *(2026-09-23)* | LiteLLM dùng như **thư viện định tuyến (SDK)**, không chạy LiteLLM proxy server; luôn nằm sau giao diện nội bộ `neuroedge.models.providers` (adapter Q-12 vẫn là đường thoát). Cài qua **extra `neuroedge[cloud]`** — `pip install neuroedge` không kéo LiteLLM (wheel cài ra ~120 MB do boto3, huggingface_hub), giữ FR-DX-02 nhẹ và keyless. |
| **Q-11** | Ngoại lệ giấy phép: Hawkbit EPL-2.0, EMQX BSL, LiteLLM | **MỘT PHẦN** | **LiteLLM: ĐÃ DUYỆT** (2026-09-23) — `litellm==1.102.0` giấy phép MIT, wheel không chứa thư mục `enterprise/`, 55 phụ thuộc bắc cầu đều MIT/BSD/Apache-2.0/PSF + MPL-2.0 (`certifi`, `tqdm`) + CNRI-Python (`regex`). **Chính sách phụ thuộc bắc cầu:** cho phép MIT, BSD-2/3-Clause, Apache-2.0, ISC, PSF, CNRI-Python, MPL-2.0 (chỉ dùng nguyên bản, không sửa); *CNRI-Python ghi thêm 2026-09-24:* giấy phép lịch sử của Python 1.6, OSI duyệt, không copyleft, chỉ buộc giữ thông báo bản quyền — đến qua `regex` (litellm → tiktoken → regex), pip tự cài, không đóng gói lại nên không phát sinh nghĩa vụ; cấm GPL/LGPL/AGPL, SSPL, BSL, giấy phép thương mại hoặc không xác định; cưỡng chế bằng bước kiểm giấy phép trong CI (cùng TSK-S2-11). Tiêu chí ra 6 của Sprint 1 nay thoả cho phạm vi Giai đoạn 1; `TSK-S2-11` **không còn bị chặn**. **Hawkbit EPL-2.0 / EMQX BSL: vẫn MỞ**, hạn trước khi mở Khối 2. |
| **Q-12** | Chuẩn kết nối nhà cung cấp AI | **ĐÃ CHỐT** | Chuẩn mặc định là **OpenAI API**; provider chưa tương thích kết nối qua **adapter do người dùng tự viết**. Áp dụng đồng nhất cho LLM, ASR và TTS (FR-MDL-07→09). |
| **Q-13** | Phân tầng cam kết theo bậc target | **ĐÃ CHỐT** | Ba bậc: **bậc 1** (`sim`, `linux`, `esp32s3`) giữ toàn bộ cam kết chất lượng hiện hành; **bậc 2** do đội lõi bảo trì với cam kết hẹp hơn; **bậc 3** do cộng đồng port và tự kiểm chứng qua Bộ kiểm thử tuân thủ. Nguyên tắc P-2 giữ nguyên hệ quả kỹ thuật ở mọi bậc (FR-TGT-08). |
| **Q-14** | Hành vi khi mất mạng + fallback cục bộ | **ĐÃ CHỐT** *(2026-09-23)* | Offline ⇒ gate **vẫn lượng giá** bằng bộ nhận diện **lệnh cố định** cục bộ (ngữ pháp lệnh: danh sách câu lệnh → intent, kèm độ tin cậy). Chỉ BLOCK với `gate_unreachable` khi fallback không có / không chạy được; câu không khớp hoặc dưới ngưỡng ⇒ BLOCK theo tiêu chí bình thường. Fallback **lên P0** (FR-ACE-03, FR-MDL-03, R-6). Backend theo target, cùng một ngữ pháp: `sim` = khớp trên chữ gõ (A1, TSK-S2-08); `esp32s3` = ESP-SR MultiNet hoặc TFLite Micro / ESP-NN (KWS tự train < 500 KB), chọn ở Khối 1b; `linux` = TFLite / KWS tương đương (Khối 1b). Thay Sherpa-ONNX. Phải xác minh giấy phép ESP-SR trước Sprint 5; spike TSK-S1-10 đo thêm MultiNet (và WakeNet nếu cân nhắc thay microWakeWord). Q-7 giữ nguyên. |
| **Q-15** | Đầu vào mặc định của `sim` | **ĐÃ CHỐT** *(2026-09-23)* | Mặc định **gõ chữ** (CLI/UI) → bộ khớp ngữ pháp lệnh của Q-14: không mạng, không key, tất định. Giọng nói là tuỳ chọn (STT cloud khi có key). WakeNet/MultiNet/TFLite Micro chỉ chạy trên chip Espressif ⇒ thuộc `esp32s3`. Hành trình 10 phút bước 2–4 đổi theo (§2.3 của tài liệu này, FR-DX-02). |
| **Q-16** | GPIO cho `linux` trong CI | **ĐÃ CHỐT** *(2026-09-23)* | CI dùng **`gpio-sim`** (kernel ≥ 5.19, configfs); thí nghiệm 2 giờ trên runner GitHub Ubuntu **trước khi mở A2**. **Mua 1 RPi 5** làm nightly phần cứng và phương án B nếu runner không có `gpio-sim`. HAL `linux` phải ném lỗi khi không có `/dev/gpiochip*`. **Kết quả 2026-09-23:** thí nghiệm đạt — runner GitHub (kernel 6.17 azure) nạp `gpio-sim` từ `linux-modules-extra`; job CI `linux-hal` (TSK-S3-05). Phương án B không cần; RPi 5 chỉ còn cho nightly. |
| **Q-17** | Hành vi `on_block` ở v1.0 | **ĐÃ CHỐT** *(2026-09-23)* | Với **mọi** `on_block`, hành động vật lý bị chặn. `deny`: chặn. `escalate`/`ask`: chặn + ghi sự kiện vào vết + gọi hook (`on_escalate`/`on_ask`, mặc định no-op). `degrade`: chặn hành động gốc, chạy `fallback_action` **qua gate của chính nó**. Hành vi đặc tả, fail-closed, test 100% ⇒ không phải nợ kỹ thuật, **không cần waiver** (thay waiver roadmap §11.3). Bề mặt tương tác thật thuộc TSK-S2-07 / TSK-S2-09 / Sprint 5. |
| **Q-18** | Kế thừa `budget`/`on_block` | **ĐÃ CHỐT** *(2026-09-23, RFC-0004)* | Sửa ngữ nghĩa phân giải: (1) `p95_latency_ms` của con ≤ của cha; (2) chuỗi đã `closed` (khai hoặc mặc định) thì con không được khai `fail: open`; (3) con không được tự đưa vào `degrade`/`fallback_action` mới (chỉ giữ nguyên của cha), được đổi sang `deny`/`escalate`/`ask`, được đổi `to`/`message`. Vi phạm ⇒ `GateInheritanceError`. Đóng lỗ `lax-night`. Task TSK-S2-13. Mở rộng nguyên tắc 2 (mục 1, 3) và nguyên tắc 4 (mục 2) của Phụ lục B.5 proposal — **vẫn năm nguyên tắc**, không thêm nguyên tắc thứ sáu; sửa FR-GATE-06/07. Hồ sơ: `docs/rfc/0004-ke-thua-budget-on-block.md`. |
| **Q-19** | Lịch Sprint 2–3 | **ĐÃ CHỐT** *(2026-09-23)* | A1 (wedge `sim`, ≈ Sprint 2) **2026-09-28 → 2026-10-25**; A2 (`linux` + Action CI, ≈ Sprint 3) **2026-10-26 → 2026-11-15**; Sprint 4 mở **2026-11-16**. M1 (TTFV < 10') trễ ~2 tuần so với roadmap gốc; Khối 1b lùi tương ứng. Bỏ quy ước "Tuần N ở đây = Tuần N+1 roadmap". Ước lượng V1 ~6,6–7,1 tuần-người trong 7 tuần — sát, không đệm lớn. |
| **Q-20** | Cổng nhu cầu mềm | **ĐÃ CHỐT** *(2026-09-23)* | Cổng ngày **2026-10-25** (cuối A1), **không chặn A2**. Các thách thức kinh doanh CEO-X2..X5 và TASTE CEO-T1..T4 ghi thành câu hỏi kinh doanh mở, chủ trì trưởng nhóm, rà lại tại cổng (`TODOS.md`). |
| **Q-21** | Mô phỏng theo tầng bằng OSS đã kiểm chứng | **ĐÃ CHỐT** *(2026-09-23, cùng kế hoạch lấp khoảng trống kỹ thuật)* | Không tự viết emulator. Mỗi tầng kiểm thử một công cụ mở: `SimHAL` (logic, mỗi commit) · `gpio-sim` (GPIO `linux`, mỗi PR — đang dùng) · `sounddevice` với backend tệp/PCM (âm thanh `linux` trong CI — runner GitHub không có `snd-aloop`; `snd-aloop` chỉ trên Pi) · `i2c-stub` + `lm75` (cảm biến `linux`) · LVGL build trên host so ảnh (màn hình `esp32s3`) · khung hình trong bộ nhớ + digest (`display`) · **mã C thuần của firmware biên dịch trên host** và chạy bảng sự thật mỗi PR (TSK-S4-07) · **Espressif QEMU** cho boot/logic `esp32s3` hằng đêm (TSK-S4-08) · bo mạch thật cho âm thanh, màn hình, bộ nhớ. **Không dùng:** Renode (không có ESP32-S3), trình mô phỏng Wokwi (mã đóng, token, không I2S), `iio_simple_dummy`. Lý do: kiểm được walker C trước khi bo mạch về, không thêm phụ thuộc vào lõi MIT (công cụ chạy riêng, Phụ lục H.4 của proposal). Không thay được spike bộ nhớ TSK-S1-10 (QEMU không giả lập I2S/AFE). Chi tiết: proposal §3.2 *Mô phỏng theo tầng*; từng ô nguyên thủy × target: `docs/spec/simulation_coverage.md`. |
| **Q-22** | AEC phần mềm trên `linux` | **ĐÃ CHỐT** *(2026-09-23, phương án A)* | `LinuxHAL` lấy `audio.in` đã khử vang qua PipeWire `libpipewire-module-echo-cancel` với `library.name = "aec/libspa-aec-webrtc"` (webrtc-audio-processing, BSD-3 — dịch vụ hệ điều hành, NeuroEdge không đóng gói). Module tạo 4 nút: `capture` (micro) → **`source` — `audio.in` đọc ở đây**; **`sink` — `audio.out` phát vào đây**, làm tín hiệu tham chiếu → `playback` (loa). Phát ra ngoài `sink` thì AEC không có tham chiếu và không khử gì, trừ khi bật `monitor.mode`. `boards/linux-rpi5.toml` **chỉ** khai `aec = true` khi nightly trên Pi đạt tiêu chí đo ở `docs/spec/simulation_coverage.md` §6; chưa đạt thì giữ `false` và `build` vẫn từ chối agent cần AEC. Nguồn: tài liệu PipeWire `page_module_echo_cancel`; mẫu cấu hình tham khảo gist `fathonix/05de5398…` (chỉ định micro bằng `capture.props.target.object`, `node.autoconnect = false`). Đã cân nhắc: B giữ `aec = false` (vi phạm FR-TGT-02), C HAT có AEC phần cứng (tốn tiền, đổi bo tham chiếu), D tách nghĩa `aec` ba mức (cần RFC sửa `board.v1.json`). |
| **Q-23** | Định dạng cây quyết định trên MCU | **ĐÃ CHỐT** *(2026-09-23)* | `neuroedge build` sinh cây thành **bố cục nhị phân cố định** mô tả bằng struct C (có magic và số phiên bản); firmware duyệt trực tiếp, **không có parser JSON trên MCU**. v1.0: link vào firmware dưới dạng mảng `const` (nằm trong flash, RB-4) — đơn giản cho walker trên host (TSK-S4-07) và QEMU. Khi cần đổi gate mà không nạp lại firmware: cùng bố cục đặt ở một phân vùng flash riêng, map bằng `esp_partition_mmap` — giữ nguyên tắc gate là dữ liệu có phiên bản độc lập. Hệ quả: `decision_tree.v1.json` vẫn là định dạng nội bộ phía host; RFC-0003 thu hẹp còn ghim `extends` bằng digest + đóng băng bố cục nhị phân khi có cập nhật qua phân vùng (`TODOS.md` #15). Đã cân nhắc: JSON + cJSON trên thiết bị (tốn SRAM và mã parse, lỗi parse lúc chạy phải fail-closed). Bố cục đóng băng ở **RFC-0003 (`NETR` v1, 2026-09-24)**; walker C99 `targets/esp32s3/components/ne_gate/`. |
| **Q-24** | Hành động là tool call · MCP | **ĐÃ CHỐT** *(2026-09-23)* | Mỗi `@action` là một **tool**; schema sinh từ chữ ký hàm (MCP `inputSchema` và dạng function-calling OpenAI, Q-12). Mọi nguồn gửi cùng một `ToolCall{name, arguments, source}`: `local_grammar` (câu khớp `commands.toml` thành tool call tổng hợp — chạy được khi mất mạng, Q-14), `system_one`, `system_two` (câu tự do, System 2 được đưa danh sách tool), `mcp` (`neuroedge mcp serve`). Một đường duy nhất tới chân: `dispatch()` → kiểm tham số theo schema (tool lạ, tham số lạ hoặc sai kiểu ⇒ `REJECTED`, không chạy gì) → `c.do()` → gate → token. Dispatcher chèn dữ kiện tin cậy `call_source` để gate giới hạn được nguồn gọi; mô hình không tự khai được. SDK MCP chính thức (`mcp`, MIT) qua extra `neuroedge[mcp]`. Không đổi `schemas/`. Chuẩn giao tiếp là **Gated Tool Profile** trên MCP — đường truyền giữ đúng MCP/OpenAI, ngữ nghĩa phán quyết là tài sản riêng: `docs/spec/tool_calling.md`. |
| **Q-25** | Ràng buộc tham số của tool call | **ĐÃ CHỐT** *(2026-09-23; RFC-0005 chấp thuận 2026-09-24, không có `arguments_closed` ở v1)* | Ràng buộc tham số (khoảng, tập giá trị, độ dài) nằm **trong gate**, không trong `agent.toml`: đi cùng gate khi chia sẻ qua registry, kế thừa chỉ thu hẹp, `gate lint` chứng minh được, và đi vào `inputSchema` để mô hình thấy trước. Làm **trước** walker C (TSK-S4-02) để bố cục nhị phân Q-23 có nút tham số ngay từ bản đầu. Bác bỏ `argument_facts` ở agent: tác giả agent nới lỏng được mà lint không thấy. |
| **Q-26** | Ai xác nhận `on_block: ask` | **ĐÃ CHỐT** *(2026-09-23)* | Chỉ **người, qua kênh thiết bị** (giọng nói/chữ khớp ngữ pháp, nút UI). Nguồn `system_two` và `mcp` không phát được lời xác nhận. Xác nhận gắn câu hỏi + `gate_digest`, dùng một lần, có TTL, và làm gate **lượng giá lại**; chỉ tiêu chí gate tự khai trong `on_block.confirms` được thay (RFC-0006, chấp thuận 2026-09-24) — không bỏ qua gate. Đóng một phần `TODOS.md` #20. `docs/spec/tool_calling.md` §6 |
| **Q-27** | NeuroEdge làm MCP client | **ĐÃ CHỐT** *(2026-09-23)* | System 2 là **MCP host**: gọi tool của thiết bị qua MCP server của **chính agent** (kết nối in-process, `call_source = system_two` gắn theo kết nối, vẫn qua gate) và gọi MCP server bên ngoài **chỉ để lấy thông tin** — `agent.toml` liệt kê allowlist; kết quả bên ngoài là dữ liệu không tin cậy, vết ghi chỉ lưu digest. Tool bên thứ ba có hiệu ứng vật lý phải bọc thành `@action` có gate. Vòng ReAct có giới hạn `max_rounds`. MCU không làm host. `docs/spec/tool_calling.md` §10 |

---

# Phụ lục

## Phụ lục A — Ma trận truy vết yêu cầu

Đối chiếu từ mục tiêu sản phẩm tới yêu cầu và tiêu chí nghiệm thu.

| Mục tiêu | Yêu cầu chi phối | Chỉ số | Tiêu chí nghiệm thu |
|:---|:---|:---|:---|
| **M1** — TTFV dưới 10 phút | FR-DX-01, FR-DX-02, FR-TGT-01, FR-TGT-06, FR-CLI-01 | TTFV trung vị | A1 |
| **M2** — Mọi hành động qua hợp đồng | FR-ACE-01→10, FR-MDL-10, FR-GATE-01→10, FR-HAL-07 | Số đường tắt tới actuator | A3, A4, A5 |
| **M3** — Nhất quán các môi trường bậc 1 | FR-TGT-01→05, FR-CI-07, FR-HAL-06 | Kết quả `neuroedge verify` | A2 |
| **M4** — Tái hiện sự cố hiện trường | FR-CI-01, FR-CI-02, FR-TRC-01→08, FR-FLT-05 | Thời gian từ sự cố tới tái hiện | A7, C7 |
| **M5** — Cập nhật quy mô lớn an toàn | FR-OTA-01→04, FR-FLT-02 | Số thiết bị brick | C1 |

### Đối chiếu nguyên tắc bất biến

| Nguyên tắc | Yêu cầu hiện thực hóa | Yêu cầu kiểm chứng |
|:---|:---|:---|
| **P-1** Hợp đồng chuẩn kiểu | FR-ACE-01, FR-ACE-02, FR-ACE-08→10, FR-MDL-10, FR-HAL-07 | A3 |
| **P-2** Các môi trường ngang hàng | FR-TGT-01→05, FR-TGT-08 | A2 *(ràng buộc ở bậc 1)* |
| **P-3** Giá trị ở quản trị fleet | FR-OTA-04, NFR-COMP-02, NFR-COMP-03 | Rà soát ranh giới §6.4 tài liệu nguồn |
| **P-4** Mô hình thay thế được — cloud-first, provider-pluggable | FR-MDL-01→04, FR-MDL-07→09, FR-PER-07, FR-GW-01→07 | Bài kiểm thử đổi mô hình và đổi provider STT/TTS chỉ bằng cấu hình, không sửa mã agent |
| **P-5** Hiệu ứng mạng từ chia sẻ gate và thành phần mở rộng | FR-GATE-05→08, FR-REG-01, FR-REG-04, FR-REG-08 | B3, C5 |

### A.3 Đối chiếu yêu cầu phi chức năng

Yêu cầu phi chức năng **không được truy vết qua task roadmap** mà qua tiêu chí nghiệm thu và rà soát định kỳ — vì chúng là thuộc tính xuyên suốt của hệ thống, không phải hạng mục công việc rời. Bảng này là đường nối duy nhất giữa NFR và bằng chứng kiểm chứng.

| Nhóm | Yêu cầu | Cách kiểm chứng | Tiêu chí nghiệm thu |
|:---|:---|:---|:---:|
| **NFR-PERF** | 01→03, 05, 07 | Đo trên lưu lượng thực, tách theo nhóm tác vụ | C2, C3, C4 |
| **NFR-PERF** | 04 | Đo độ trễ quyết định `SystemOne` qua FR-TEL-06 | C8 |
| **NFR-PERF** | 06 | Đo thời gian chạy bộ Action CI của dự án mẫu trong CI | — *(chỉ số nội bộ)* |
| **NFR-RES** | 01 | Kiểm thử chịu tải 24 giờ trên bo mạch tham chiếu | A6 |
| **NFR-RES** | 02, 03 | Đo bộ nhớ và kích thước firmware trong CI; ngưỡng chốt tại Q-3 | A6 |
| **NFR-RES** | 04 | Bộ kịch bản suy giảm: mất mạng, timeout, dữ liệu mô hình không hợp lệ | A4 |
| **NFR-REL** | 01 | Chiến dịch OTA canary trên 1.000 thiết bị | C1 |
| **NFR-REL** | 02 | Bộ kịch bản suy giảm — trùng cơ chế với NFR-RES-04 | A4 |
| **NFR-REL** | 03 | Nhật ký kiểm thử hằng đêm trên bo mạch thật | A2 |
| **NFR-REL** | 04 | Chạy lại bộ vết ghi hồi quy sau mỗi lần nâng phiên bản phụ | A7 |
| **NFR-SEC** | 01 | Rà soát mã và kiểm thử thâm nhập tìm đường tắt tới actuator | A3 |
| **NFR-SEC** | 02, 03 | Rà soát cấu hình Secure Boot, mã hóa flash, TPM và nút ngắt micro trên bo mạch tham chiếu | **cần tiêu chí** *(chưa có tiêu chí mốc A/C nào đo được)* |
| **NFR-SEC** | 06 | Nạp firmware không chữ ký hoặc sai chữ ký → bị từ chối | Tiêu chí của FR-OTA-03 · **cần tiêu chí mốc** |
| **NFR-SEC** | 04, 05 | Rà soát TLS 1.3, mTLS, certificate pinning và chứng chỉ riêng từng thiết bị (gắn FR-FLT-01, v1.1) | **cần tiêu chí** |
| **NFR-SEC** | 08 | Rà soát kênh TLS 1.3 tới provider; kiểm provider được ghi trong vết ghi | **cần tiêu chí** *(`trace.v1.json` hiện chưa có trường provider)* |
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
| **FR-CI-LVL** | L1→L3 | Ba cấp độ đảm bảo: L1 replay chuẩn xác, L2 khớp schema + `confidence`, L3 chỉ assert phán quyết gate và GPIO | A2 *(L1, L2)* · lint FR-DX-07 *(L3)* |
| **FR-TRC** | 09, 10 | Lệnh thẩm định và quy ước đường dẫn vết ghi | A7 |
| **FR-GOV** | 01→04 | Quản trị lược đồ mở và quy trình RFC | A9 |
| **FR-CLI** | 02→08 | Bề mặt dòng lệnh | A1, A8 |
| **FR-CLI** | 09→11 | `gate lint`, `gate resolve`, `board` | A5 *(09, 10)* · A2 *(11)* |
| **FR-DX** | 03→07 | Khuôn mẫu dự án, ví dụ mẫu, thông báo lỗi | A1, A8 |
| **FR-TGT** | 07 | Mô phỏng kịch bản suy giảm trong `sim` | A4 |
| **FR-MDL** | 05, 06 | Định tuyến khai báo và ghi nhận tỷ lệ S1/S2 | C4 |
| **FR-FLT** | 01, 03, 04, 06 | Provisioning, giám sát, cấu hình từ xa, thiết bị ảo | C1, roadmap TR-7 |
| **FR-REG** | 02, 03, 05, 06 | Manifest, khai báo năng lực, định danh, đo lường | C5, roadmap TR-4, TR-5 |
| **FR-TEL** | 01→06 | Viễn trắc và đo đạc | B4, B5, §12.2 của tài liệu này |

**Độ phủ truy vết:** sau A.1 đến A.4, mọi yêu cầu FR và NFR trong tài liệu này đều có ít nhất một đường kiểm chứng, **trừ các dòng ghi "cần tiêu chí"** (NFR-SEC-02→06, 08) — nợ truy vết đã biết, phải bổ sung tiêu chí trước khi đóng v1.0. Ba phụ lục sau A.1 tồn tại vì ba trục truy vết khác nhau — mục tiêu, nguyên tắc, và thuộc tính hệ thống — và một yêu cầu có thể xuất hiện ở nhiều trục.

---

## Phụ lục B — Danh mục mã lỗi chuẩn

Mọi mã lỗi **BẮT BUỘC** nêu đủ ba thành phần: sai ở đâu, vì sao, và cách xử lý (FR-DX-04).

Tên lớp và mã `NE…` khớp `python/neuroedge/errors.py`; mọi lớp kế thừa `NeuroEdgeError`. Dòng ghi *(dự kiến)* chưa có trong mã.

| Mã lỗi | Mã | Thời điểm phát sinh | Nguyên nhân | Hành vi hệ thống |
|:---|:---:|:---|:---|:---|
| `ActionContractViolation` | NE1001 | Chạy | Gọi hành động vật lý không qua `c.do()` / thiếu chữ ký gate hợp lệ | Ném ngoại lệ, chân GPIO không được kích |
| `TokenReplayError` | NE1002 | Chạy | Token phán quyết bị dùng lại (`token_replayed`), quá TTL = p95 × 3 hoặc do tiến trình khác phát hành (`token_expired`) | Ném ngoại lệ (vi phạm hợp đồng, không thử lại), chân GPIO không được kích, ghi `actuator_command_rejected` (TSK-S2-05) |
| `GateNotFoundError` | NE2001 | Build hoặc chạy | URI hoặc đường dẫn gate không phân giải được thành tài liệu gate | Từ chối phân giải, nêu URI/đường dẫn |
| `GateSchemaError` | NE2002 | Build, `gate lint`, `gate resolve` | Gate vi phạm `schemas/gate.v1.json` hoặc tập toán tử Phụ lục B | Từ chối, nêu trường sai |
| `GateInheritanceError` | NE2003 | Build, `gate lint`, `gate resolve` | Chuỗi `extends` vi phạm nguyên tắc B.5: nới lỏng `allow_when`/`budget`/`on_block` (Q-18), `allow_when` dạng chuỗi trong chuỗi kế thừa, vượt 3 cấp, hoặc vòng lặp | Từ chối phân giải, nêu chuỗi kế thừa và dòng `rule` chỉ nguyên tắc B.5 bị vi phạm |
| `BoardCapabilityError` | NE3001 | Build | Khai báo bo mạch sai, hoặc agent yêu cầu năng lực bo mạch không cung cấp | Dừng build, không sinh firmware, chỉ rõ dòng mã gọi |
| `AgentManifestError` | NE3002 | Build | `agent.toml` sai cấu trúc, thiếu `[requires]`, hoặc một `@action` cần năng lực / gate mà manifest không khai | Dừng build, nêu `file:line` của hành động (TSK-S2-02) |
| `BuildFailed` | NE3003 | Build | `neuroedge build` gặp ≥ 1 vấn đề | Gom **mọi** vấn đề, in từng cái đủ 3 thành phần, thoát mã 1, không ghi artifact nào |
| `TraceValidationError` | NE4001 | `neuroedge trace validate` | Tệp vết ghi không hợp lệ theo `schemas/trace.v1.json` | Báo lỗi kèm đường dẫn trường sai |
| *(không phải exception — phán quyết)* | — | Chạy | Gate không thẩm định được trong ngân sách hoặc bộ thẩm định không tới được, và `fail: closed` | `BLOCK` với `reason: budget_exceeded` / `gate_unreachable`, `action: deny`, ghi vào vết ghi (TSK-S2-03). Fail-closed là phán quyết để phát lại được, không phải lỗi |
| `SafetyRegressionError` | NE4002 | `neuroedge replay`, `verify`, `assert_matches_golden` | Phán quyết gate hoặc lệnh chân của phiên replay lệch golden — kể cả lệch giữa các target (thay `TargetEquivalenceError` dự kiến) | Mã 1, chỉ rõ sự kiện và trường lệch đầu tiên; gắn nhãn *SAFETY REGRESSION* khi BLOCK thành ALLOW hoặc có lệnh chân mới (TSK-S3-04). Cũng là `AssertionError` để pytest báo test trượt |
| `ReplayError` | NE4003 | `neuroedge replay` | Vết ghi không replay được với agent này: không biết action nào sau một gate, hoặc target không có HAL | Mã 1, lỗi 3 thành phần (TSK-S3-02) |
| `VerificationError` | NE4004 | `neuroedge verify` | Một loại artifact quét được 0 — không gate nào phân giải, không vết ghi chuẩn mực nào thẩm định, không lượt replay nào — hoặc thư mục không tồn tại | Mã 1, lỗi 3 thành phần nêu thư mục và `NEUROEDGE_ROOT`; quét 0 artifact không bao giờ là đạt (FR-CLI-03, TSK-S3-19) |
| `PerceptionUnavailableError` | NE5001 | Nạp / build | Thành phần nhận thức không dựng được: tệp ngữ pháp lệnh thiếu hoặc sai, fallback không xác định | Báo lỗi 3 thành phần. Lúc chạy, nhà cung cấp chính và fallback đều không trả lời được **không** ném lỗi: là phán quyết `Unavailable` → `gate_unreachable` / `criterion_unavailable`, áp `fail` của gate (TSK-S2-08) |

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
│   │   ├── cli/                 # CLI Surface: Typer + Rich (mẫu dự án: templates/)
│   │   ├── hal/                 # 5 nguyên thủy HAL & Capability Matcher
│   │   ├── engine/              # Action Contract Engine & Google CEL Compiler
│   │   ├── perception/          # Voice pipeline, VAD (Silero), Barge-in (Pipecat)
│   │   ├── testing/             # Action CI Engine (pytest-neuroedge, replay)
│   │   └── sim/                 # SimSession (gõ chữ trên terminal) · web UI: TSK-S2-09
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
