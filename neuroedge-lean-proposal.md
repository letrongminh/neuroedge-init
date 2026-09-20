# NeuroEdge — Product Proposal

## Hợp đồng hành động có kiểu cho Physical AI

**Phiên bản:** 5.1 — *Enterprise & Production Edition*  
**Ngày:** 20 tháng 9, 2026  
**Chuẩn mực thiết kế:** Big Consulting Firm Standard (MECE, Pyramid Principle)  
**Khung tham chiếu chiến lược:** Paul Graham — *"Making Startups Powerful"* (09/2026)  
**Phạm vi tài liệu:** Định vị chiến lược, kiến trúc 5 lớp, đặc tả API, lộ trình thực thi, mô hình kinh tế Unit Economics, ma trận rủi ro & hệ chỉ số  
**Ngoài phạm vi:** Bảng gọi vốn chi tiết (Cap table), hợp đồng pháp lý doanh nghiệp  

---

### Bảng theo dõi thay đổi (Changelog v5.0 ➔ v5.1)

| # | Hạng mục thay đổi | Lý do & Cơ sở chiến lược (Consulting Lens) | Vị trí |
|:---|:---|:---|:---:|
| 1 | **Chốt dứt điểm 4 Quyết định mở (Phụ lục C)** | Khép kín các placeholder `[cần chốt]`. Tách Khối 1 thành 1a & 1b để giữ cam kết tiến độ; công bố chuẩn SLA độ trễ P95; ấn định ngưỡng chuyển đổi phần cứng 15%. | §5.1, §9, Phụ lục C |
| 2 | **Nhúng sâu Luận điểm Paul Graham vào thân bài** | Tích hợp trực tiếp mẫu Rippling (sở hữu dữ liệu thượng nguồn tại Simulator) và mẫu Stripe (tiếp cận Maker tại thiết bị #1) vào kiến trúc và lộ trình sản phẩm. | §1.3, §1.4, §3.7 |
| 3 | **Bổ sung Bảng phân tích TCO định lượng** | Định lượng hóa chi phí phát triển và vận hành (DIY vs SDK hãng vs NeuroEdge) để chứng minh luận điểm *"Giúp người dùng kiếm tiền & tiết kiệm chi phí"*. | §1.7, §7.1 |
| 4 | **Hoàn thiện Đặc tả Kỹ thuật & Xử lý Ngoại lệ** | Bổ sung đặc tả cấu trúc khối dữ liệu `.ntrace`, bộ lỗi an toàn (`ActionContractViolation`, `GateFailClosedException`), và cơ chế Fail-Closed Circuit. | §3.5, §3.7, §4.4 |
| 5 | **Chuẩn hóa Mô hình Kinh tế Fleet Management** | Định nghĩa rõ cấu trúc doanh thu: Bán inference sát giá vốn (phễu onboarding), thu phí biên cao theo nút thiết bị ($/device/tháng). | §5.2 |

---

## Mục lục

**Phần 0 — Tóm tắt điều hành**
- [Bối cảnh & Điểm gãy thị trường](#01-bối-cảnh--điểm-gãy-thị-trường)
- [Vấn đề cốt lõi: Lỗ hổng kiểm thử tiền thi công](#02-vấn-đề-cốt-lõi-lỗ-hổng-kiểm-thử-tiền-thi-công)
- [Tuyên ngôn giải pháp NeuroEdge](#03-tuyên-ngôn-giải-pháp-neuroedge)
- [Năm quyết định chiến lược bất biến](#04-năm-quyết-định-chiến-lược-bất-biến)

**Phần I — Luận điểm chiến lược & Quyền lực startup**
1. [Luận điểm chiến lược cốt lõi](#1-luận-điểm-chiến-lược-cốt-lõi)
   - 1.1 [Chạy ngược thế giới hoàn hảo của khách hàng](#11-chạy-ngược-thế-giới-hoàn-hảo-của-khách-hàng)
   - 1.2 [Phản đề "Đứng thẳng người" — Loại bỏ định vị "Dual-Brain"](#12-phản-đề-đứng-thẳng-người--loại-bỏ-định-vị-dual-brain)
   - 1.3 [Bốn vị thế thượng nguồn (The Upstream Positions)](#13-bốn-vị-thế-thượng-nguồn-the-upstream-positions)
   - 1.4 [Chiến lược đánh sườn vô hiệu hóa SDK chính hãng](#14-chiến-lược-đánh-sườn-vô-hiệu-hóa-sdk-chính-hãng)
   - 1.5 [Mã nguồn mở hào phóng & Đề xuất chuẩn mực sớm](#15-mã-nguồn-mở-hào-phóng--đề-xuất-chuẩn-mực-sớm)
   - 1.6 [Vòng lặp giá trị & Hiệu ứng mạng trước Marketplace](#16-vòng-lặp-giá-trị--hiệu-ứng-mạng-trước-marketplace)
   - 1.7 [Giúp người dùng kiếm tiền: Phân tích TCO định lượng](#17-giúp-người-dùng-kiếm-tiền-phân-tích-tco-định-lượng)
2. [Bộ lọc quyết định MECE (R1–R4)](#2-bộ-lọc-quyết-định-mece-r1r4)

**Phần II — Kiến trúc sản phẩm & Đặc tả API**
3. [Kiến trúc hệ thống 5 lớp](#3-kiến-trúc-hệ-thống-5-lớp)
   - 3.1 [Sơ đồ khối tổng thể & Trục Action CI](#31-sơ-đồ-khối-tổng-thể--trục-action-ci)
   - 3.2 [L0 — Định luật tương đương Target (`sim` · `linux` · `esp32s3`)](#32-l0--định-luật-tương-đương-target-sim--linux--esp32s3)
   - 3.3 [L1 — HAL: Hợp đồng năng lực 5 nguyên thủy](#33-l1--hal-hợp-đồng-năng-lực-5-nguyên-thủy)
   - 3.4 [L2 — Perception & Runtime hội thoại](#34-l2--perception--runtime-hội-thoại)
   - 3.5 [L3 — Action Contract Engine & Cơ chế Fail-Closed](#35-l3--action-contract-engine--cơ-chế-fail-closed)
   - 3.6 [Trừu tượng hóa Model (Decoupled Intelligence Layer)](#36-trừu-tượng-hóa-model-decoupled-intelligence-layer)
   - 3.7 [Trục xuyên suốt Action CI & Đặc tả định dạng `.ntrace`](#37-trục-xuyên-suốt-action-ci--đặc-tả-định-dạng-ntrace)
4. [Đặc tả API & Bề mặt công cụ](#4-đặc-tả-api--bề-mặt-công-cụ)
   - 4.1 [Nguyên tắc thiết kế API khai báo](#41-nguyên-tắc-thiết-kế-api-khai-báo)
   - 4.2 [Đặc tả Phần cứng (`board.toml`)](#42-đặc-tả-phần-cứng-boardtoml)
   - 4.3 [Đặc tả Yêu cầu Agent (`agent.toml`)](#43-đặc-tả-yêu-cầu-agent-agenttoml)
   - 4.4 [Đặc tả Hành động có kiểu (`@action`) & Xử lý ngoại lệ](#44-đặc-tả-hành-động-có-kiểu-action--xử-lý-ngoại-lệ)
   - 4.5 [Đặc tả Gate Artifact (`.yaml` schema & `extends`)](#45-đặc-tả-gate-artifact-yaml-schema--extends)
   - 4.6 [Mã nguồn Agent hoàn chỉnh](#46-mã-nguồn-agent-hoàn-chỉnh)
   - 4.7 [Bộ kiểm thử hồi quy Action CI](#47-bộ-kiểm-thử-hồi-quy-action-ci)
   - 4.8 [Bề mặt CLI chuẩn hóa](#48-bề-mặt-cli-chuẩn-hóa)
   - 4.9 [Báo cáo vi phạm hợp đồng tại thời điểm build](#49-báo-cáo-vi-phạm-hợp-đồng-tại-thời-điểm-build)

**Phần III — Lộ trình thực thi & Mô hình kinh doanh**
5. [Lộ trình 4 Khối công việc & Cổng thanh khoản](#5-lộ-trình-4-khối-công-việc--cổng-thanh-khoản)
   - 5.1 [Khối 1 — Lõi mã nguồn mở MIT (Chia tách 1a & 1b)](#51-khối-1--lõi-mã-nguồn-mở-mit-chia-tách-1a--1b)
   - 5.2 [Khối 2 — Commercial Plane & Kinh tế học Fleet Management](#52-khối-2--commercial-plane--kinh-tế-học-fleet-management)
   - 5.3 [Khối 3 — Bảy đường ray nền tảng (Rails)](#53-khối-3--bảy-đường-ray-nền-tảng-rails)
   - 5.4 [Khối 4 — Triển khai dọc AURA Full-Stack](#54-khối-4--triển-khai-dọc-aura-full-stack)
   - 5.5 [Cổng thanh khoản định lượng (The Liquidity Gate)](#55-cổng-thanh-khoản-định-lượng-the-liquidity-gate)
   - 5.6 [Khối 5 — Gate Marketplace & Agent Pay (Thương mại hóa)](#56-khối-5--gate-marketplace--agent-pay-thương-mại-hóa)
6. [Ranh giới sản phẩm tường minh & Ma trận Trade-off](#6-ranh-giới-sản-phẩm-tường-minh--ma-trận-trade-off)

**Phần IV — Kiểm chứng thị trường & Quản trị rủi ro**
7. [Định vị cạnh tranh & Lợi thế bất công](#7-định-vị-cạnh-tranh--lợi-thế-bất-công)
   - 7.1 [Bản đồ đối thủ & Phân tích khoảng trống](#71-bản-đồ-đối-thủ--phân-tích-khoảng-trống)
   - 7.2 [Ba Moat cấu trúc không thể sao chép](#72-ba-moat-cấu-trúc-không-thể-sao-chép)
   - 7.3 [Những mặt trận tuyệt đối không cạnh tranh](#73-những-mặt-trận-tuyệt-đối-không-cạnh-tranh)
8. [Ma trận 4 Rủi ro sống còn & Chiến lược giảm thiểu](#8-ma-trận-4-rủi-ro-sống-còn--chiến-lược-giảm-thiểu)
9. [Hệ chỉ số hiệu suất MECE (Performance Framework)](#9-hệ-chỉ-số-hiệu-suất-mece-performance-framework)

**Phần V — Phụ lục**
- [Phụ lục A — Bảng đối chiếu toàn diện luận điểm Paul Graham](#phụ-lục-a--bảng-đối-chiếu-toàn-diện-luận-điểm-paul-graham)
- [Phụ lục B — Từ điển thuật ngữ chuẩn mực](#phụ-lục-b--từ-điển-thuật-ngữ-chuẩn-mực)
- [Phụ lục C — Biên bản giải quyết 100% quyết định mở](#phụ-lục-c--biên-bản-giải-quyết-100-quyết-định-mở)

---

## 0. Tóm tắt điều hành

### 0.1 Bối cảnh & Điểm gãy thị trường

Physical AI đang ở điểm giao thoa của 3 lực đẩy lịch sử:
1. **Phần cứng biên chạm đáy chi phí:** Vi xử lý có Wi-Fi/BLE và tăng tốc AI (ESP32-S3, K210, RPi Zero 2W) có giá chỉ từ $3 đến $15.
2. **SLM chạy cục bộ (On-device):** Các mô hình từ 0.5B đến 3B tham số đã có thể chạy trực tiếp trên thiết bị biên để phân loại ý định và trích xuất thực thể.
3. **Giao thức công cụ mở rộng:** Model Context Protocol (MCP) thiết lập chuẩn chung kết nối logic mô hình với các công cụ ngoại vi.

Tuy nhiên, một kỹ sư muốn chế tạo một thiết bị vật lý có tương tác giọng nói cơ bản (Voice Physical Agent) vẫn phải tự vật lộn tích hợp 6 thư viện độc lập không tương thích: AEC/VAD, Wake-word, STT/TTS, State Machine hội thoại, Driver phần cứng, và Tầng bảo vệ an toàn.

### 0.2 Vấn đề cốt lõi: Lỗ hổng kiểm thử tiền thi công

Mô tả khoảng trống trên là *"thiếu một voice framework"* là nhận định hời hợt. Đó là khoảng trống mà mọi đối thủ cạnh tranh có nhiều vốn đều có thể lấp đầy chỉ bằng cách code thêm tính năng.

Khoảng trống thực sự mang tính bản chất: **Chưa có công cụ nào kiểm thử được hành vi vật lý trước khi nó diễn ra ngoài đời thực.**
* Khi một Chatbot phần mềm gặp ảo giác (hallucination), người dùng chỉ cần đọc lại câu trả lời hoặc bấm generate lại.
* Khi một Physical AI Agent gặp ảo giác, **servo đã quay, rơ-le đã đóng, chốt cửa đã mở, động cơ đã kích hoạt.** Hành vi vật lý là bất khả nghịch (irreversible).

Ngành công nghiệp phần mềm có Unit Test, Integration Test và CI/CD tự động trên từng commit. Ngành Physical AI hiện tại chỉ có quy trình thô sơ: nạp firmware, nói thử vài câu trong phòng lab, và cầu nguyện khi xuất xưởng.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   NGHỊCH LÝ THỰC THI TRONG PHYSICAL AI                 │
├────────────────────────────────────────────────────────────────────────┤
│  PHẦN MỀM TRUYỀN THỐNG:                                                │
│  Code ──► Static Analysis ──► Unit Tests ──► CI/CD ──► Deterministic   │
│                                                                        │
│  PHYSICAL AI HIỆN TẠI (ĐỨT GÃY):                                       │
│  Prompt/Code ──► Nạp Firmware ──► Thử tay ngoài đời ──► Cầu trời      │
│                                                                        │
│  VỚI NEUROEDGE (HỢP ĐỒNG HÀNH ĐỘNG + ACTION CI):                       │
│  Agent Code ──► Capability Check ──► Action CI Replay ──► Safe Rollout │
│  (Chặn lỗi lúc build)                (Bit-for-bit test)   (OTA an toàn)│
└────────────────────────────────────────────────────────────────────────┘
```

### 0.3 Tuyên ngôn giải pháp NeuroEdge

> **NeuroEdge biến mọi hành động vật lý của AI Agent thành một hợp đồng có kiểu dữ liệu chặt chẽ, có version, kiểm thử tự động trong CI pipeline, và thực thi nhất quán tuyệt đối trên 3 target — từ laptop của lập trình viên tới máy tính Linux công nghiệp và vi điều khiển biên $5.**

Hệ thống được cấu trúc thành 3 khối chiến lược rõ ràng:
1. **Lõi mã nguồn mở (MIT License):** HAL hợp đồng năng lực · Action Contract Engine · Voice runtime · Bộ ba target ngang hàng (`sim` · `linux` · `esp32s3`) · Action CI runner.
2. **Mặt phẳng thương mại duy nhất:** Hosted Gateway định tuyến tối ưu + Nền tảng quản trị đội thiết bị (Fleet Management OS).
3. **Cổng thanh khoản định lượng:** Chặn mọi hoạt động thương mại hóa Marketplace và Thanh toán cho tới khi đạt quy mô tự phát ngoài thị trường.

### 0.4 Năm quyết định chiến lược bất biến

| # | Quyết định bất biến | Hệ quả kiến trúc & Kinh doanh |
|:---:|:---|:---|
| **1** | **Hành động vật lý là Hợp đồng có kiểu, không phải lời gọi hàm.** | Mọi lệnh gửi tới actuator phải đi qua một Policy Gate có version, khai báo tĩnh, phân tích được bằng máy. HAL từ chối mọi lệnh không kèm gate hợp lệ (§3.5, §4.4). |
| **2** | **Ba Target ngang hàng (Target Equivalence Law).** | `sim`, `linux`, `esp32s3` là 3 bản hiện thực hóa ngang hàng của cùng một HAL. Cùng một file code agent chạy trên cả 3 mà không sửa một dòng (§3.2). |
| **3** | **Bán Fleet Management, không bán Token.** | Bán lại token inference là cuộc đua biên lợi nhuận mỏng và cầm chắc thất bại trước các model vendor. Doanh thu của NeuroEdge đến từ việc quản lý sự an toàn của đội thiết bị ngoài hiện trường (§5.2). |
| **4** | **Model AI là thành phần thay thế được, không phải luận điểm.** | Trí thông minh nằm sau interface `SystemOne` và `SystemTwo` ngay từ tuần đầu tiên. Đổi model không làm thay đổi định vị sản phẩm hay kiến trúc bảo vệ (§3.6). |
| **5** | **Hiệu ứng mạng kích hoạt trước Marketplace.** | Bỏ qua chợ thương mại phức tạp ở giai đoạn đầu. Xây dựng Registry chia sẻ Gate miễn phí để tạo hiệu ứng mạng dữ liệu trước khi kích hoạt giao dịch (§1.6, §5.3). |

---

# Phần I — Luận điểm chiến lược & Quyền lực startup

## 1. Luận điểm chiến lược cốt lõi

### 1.1 Chạy ngược thế giới hoàn hảo của khách hàng

Trong bài tiểu luận *"Making Startups Powerful"* (09/2026), Paul Graham thiết lập nguyên lý: Mọi chiến lược gia tăng quyền lực cho startup chỉ hợp lệ khi và chỉ khi nó tạo ra kết quả vượt trội cho khách hàng. Nguyên lý này có thể chạy ngược từ tương lai để tìm ra sản phẩm đột phá:

> *"What would the perfect world look like, from the customer's point of view? If there's a component of that world that the startup could transform itself into, it probably should."*

Bảng đối chiếu trạng thái trải nghiệm của kỹ sư phát triển Physical AI:

| # | Trong thế giới hoàn hảo | Hiện trạng thị trường hôm nay | NeuroEdge giải quyết |
|:---:|:---|:---|:---|
| **1** | Viết code agent, chạy thử nghiệm ngay lập tức mà không cần mua phần cứng. | Bị nghẽn bởi chu kỳ đặt hàng bo mạch, câu dây, thiết lập mạch nạp. | **Target `sim`:** Chạy agent hoàn chỉnh trên trình duyệt trong 10 phút (§3.2). |
| **2** | Biết chắc agent không kích hoạt hành động nguy hiểm **trước khi** nạp firmware. | Chỉ phát hiện lỗi sau khi thiết bị đã xuất xưởng tới tay khách hàng cuối. | **Action Contract Engine:** Kiểm tra hợp đồng lúc build và lúc runtime (§3.5). |
| **3** | Đổi prompt hoặc đổi model AI, chạy lại toàn bộ test an toàn trong 30 giây. | Thử nghiệm thủ công vài trường hợp trong phòng lab, hy vọng không hồi quy. | **Action CI:** Replay phiên thật bit-for-bit, so khớp chuỗi golden test (§3.7). |
| **4** | Một file agent duy nhất chạy trên laptop test, máy tính nhúng và chip $5. | Phải duy trì 3 codebase độc lập: Python trên PC, C++ trên vi điều khiển. | **Target Equivalence:** Cùng 1 file logic chạy trên cả 3 nền tảng (§4.6). |
| **5** | Khắc phục sự cố thiết bị lỗi ngoài hiện trường ngay từ máy tính cá nhân. | Kỹ sư phải bay tới hiện trường hoặc thu hồi toàn bộ lô hàng bị lỗi. | **Trace Replay:** Kéo file `.ntrace` từ hiện trường về replay cục bộ (§5.2). |

Cấu phần mà NeuroEdge lựa chọn để tự biến mình thành chính là **Số 2 và Số 3** — hai khoảng trống mà không đối thủ nào trên thị trường có thể phục vụ bằng cách thêm tính năng đơn thuần. Số 1 và Số 4 là điều kiện nền tảng bắt buộc; Số 5 là nơi tạo ra doanh thu bền vững.

### 1.2 Phản đề "Đứng thẳng người" — Loại bỏ định vị "Dual-Brain"

Phiên bản cũ v4.0 đặt *"Dual-Brain Router"* (bộ não kép định tuyến System 1/System 2) làm tài sản cốt lõi. Đây là một sai lầm chiến lược mà Paul Graham đã cảnh báo:

> *"One way startups' ideas get twisted into knots is by evolving from something else... But with very early stage startups especially, the reason the idea is complicated is often fear. The company is unconsciously cowering by doing something less ambitious than they could. 'Just y' is often, in effect, 'just stand up straight.' And when they do they're much taller."*

Bản v4.0 mắc kẹt trong sự "thu mình vô thức" (unconscious cowering) với 3 điểm yếu cấu trúc:
1. **Trói buộc vào hạng mô hình của một thời điểm:** Khi các mô hình biên lớn trở nên siêu rẻ và hỗ trợ constrained decoding thời gian thực, khái niệm "bộ não kép" lập tức thoái hóa thành một chi tiết triển khai tầm thường.
2. **Mô tả cơ chế thay vì mô tả giá trị:** Khách hàng không bỏ tiền mua "bộ định tuyến giữa hai model"; họ bỏ tiền để **"đảm bảo cánh tay robot không đập vào người dùng"**.
3. **Bỏ phí các tài sản kiến trúc cốt lõi:** Định dạng Gate có schema, cơ chế record/replay, telemetry chi tiết, và mô hình sandbox phân quyền bị phân tán rời rạc.

**Bước chuyển dịch mang tính bước ngoặt của v5.1:** NeuroEdge đứng thẳng người để chiếm lĩnh một hạng mục chưa ai sở hữu:

```
Schema Gate có version           ─┐
Record phiên thật ngoài phần cứng ─┤
Replay trong sim bit-for-bit     ─┼─►  ACTION CI
Trace đầy đủ mỗi bước quyết định  ─┘    Kiểm thử hành động vật lý tự động
                                        trong CI pipeline trên mỗi commit
```

Mệnh đề trung tâm mới: **"Mọi hành động vật lý đều đi qua một hợp đồng có kiểu dữ liệu, kiểm thử được trong CI"** — Luận điểm này luôn đúng bất kể ai lấp vào vị trí mô hình suy luận.

### 1.3 Bốn vị thế thượng nguồn (The Upstream Positions)

> *"Upstream is almost always good, whether it's with money or user relationship or customer stage or data."* — Paul Graham

NeuroEdge chiếm lĩnh toàn bộ 4 chiều thượng nguồn một cách có hệ thống:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   BỐN VỊ THẾ THƯỢNG NGUỒN CỦA NEUROEDGE                │
├───────────────────┬────────────────────────────────────────────────────┤
│ THƯỢNG NGUỒN      │ CHIẾN LƯỢC CHIẾM LĨNH TOÀN DIỆN                    │
├───────────────────┼────────────────────────────────────────────────────┤
│ 1. DỮ LIỆU        │ MẪU RIPPLING: Đặt chân tại nơi dữ liệu sinh ra lần │
│    (Data)         │ đầu tiên: Simulator (`sim`) & định dạng `.ntrace`. │
│                   │ Ai sở hữu trace format sẽ sở hữu chuẩn an toàn.    │
├───────────────────┼────────────────────────────────────────────────────┤
│ 2. GIAI ĐOẠN KHÁCH│ MẪU STRIPE: Bắt đầu từ Maker tại Thiết bị #1       │
│    (Stage)        │ Doanh thu tự động mở rộng theo cấp số nhân khi số  │
│                   │ thiết bị xuất xưởng tăng lên (Zero sales friction).│
├───────────────────┼────────────────────────────────────────────────────┤
│ 3. QUAN HỆ KHÁCH  │ HOSTED GATEWAY: Đứng giữa dev và các model vendor. │
│    (Relationship) │ Đổi model, đổi prompt từ xa mà không flash lại chip│
├───────────────────┼────────────────────────────────────────────────────┤
│ 4. DÒNG TIỀN      │ HÓA ĐƠN HỢP NHẤT: Toàn bộ chi phí inference, OTA,  │
│    (Money Flow)   │ và bảo mật chảy qua một cổng thanh toán duy nhất.  │
└───────────────────┴────────────────────────────────────────────────────┘
```

* **Bài học chuyên sâu từ Rippling (Data Upstream):** Rippling không trở thành công ty tỷ USD nhờ phần mềm onboarding; họ làm phần mềm onboarding vượt trội mức cần thiết vì đó là nơi **vòng đời dữ liệu nhân sự bắt đầu**. Đối với Physical AI, nơi vòng đời dữ liệu bắt đầu chính là **lần đầu tiên một hành động vật lý được đề xuất trong simulator**. Ai sở hữu định dạng trace tại điểm khởi sinh này sẽ sở hữu toàn bộ chuỗi giá trị bảo mật và vận hành về sau.

### 1.4 Chiến lược đánh sườn vô hiệu hóa SDK chính hãng

> *"You'd have to do it by coming in from the side — by somehow making them irrelevant, rather than by frontal attack. Then you wouldn't depend on beating them to succeed; it would be an ancillary benefit of winning in another dimension."* — Paul Graham

Các nhà sản xuất silicon (Espressif, Nordic, Raspberry Pi) phân phối SDK miễn phí vĩnh viễn với động cơ cốt lõi: **bán chip phần cứng**. Đối đầu trực diện ở tầng driver một-chip là tự sát.

* **Chiều không gian mới của NeuroEdge:** **Tính kiểm thử được của hành động cắt ngang mọi loại phần cứng (Cross-hardware testability).**
* **Lý do đối thủ không thể sao chép:** Về mặt cấu trúc kinh doanh, Espressif không bao giờ đầu tư nguồn lực biến chip ESP32 thành "một đối tác ngang hàng bình đẳng" với Linux hay chip đối thủ. Bằng cách nâng `linux` lên target hạng nhất ngay từ ngày đầu, NeuroEdge vô hiệu hóa sự độc quyền của SDK hãng và biến các nhà sản xuất chip thành các nhà cung cấp linh kiện đơn thuần.

### 1.5 Mã nguồn mở hào phóng & Đề xuất chuẩn mực sớm

> *"If you're one of the first in the field... everyone is so hungry for standards that the first to be proposed tends to win, no matter who proposed it."* — Paul Graham (Note 2)

Mã nguồn mở chỉ trở thành kênh phân phối hiệu quả khi người cài đặt chính là người ra quyết định kiến trúc:
* **Generosity (Sự hào phóng có tính toán):** Lõi MIT mở toàn bộ HAL, Action Contract Engine, Voice pipeline và Action CI. Sự hào phóng loại bỏ hoàn toàn ma sát dùng thử, tạo dựng lòng tin tuyệt đối nơi các kỹ sư nhúng — nhóm khách hàng có tính bảo thủ cao nhất.
* **Chuẩn hóa Action Schema:** NeuroEdge không bán framework; framework là thứ ai cũng có thể viết lại. NeuroEdge đưa **định dạng Gate YAML và `.ntrace`** thành tiêu chuẩn công nghiệp. Khi định dạng này trở thành chuẩn mô tả sự an toàn, nền tảng sở hữu công cụ CI và hạ tầng Fleet quản lý định dạng đó mặc nhiên giành chiến thắng.

### 1.6 Vòng lặp giá trị & Hiệu ứng mạng trước Marketplace

```
Chạy agent trong simulator sau 10 phút, không cần mua phần cứng
                           │
                           ▼
Viết Gate đầu tiên: Agent tự động từ chối các hành vi nguy hiểm
                           │
                           ▼
Ghi phiên thật trên bo mạch (.ntrace), replay trong Action CI mỗi commit
                           │
                           ▼
Triển khai lên 10 ➔ 100 ➔ 1.000 thiết bị biên: Rollout OTA an toàn
                           │
                           ▼
Khách hàng trả tiền cho Fleet Management OS (Không phải trả tiền cho token)
                           │
                           ▼
Chia sẻ Gate an toàn lên Public Registry (kế thừa qua 'extends')
                           │
                           ▼
Dữ liệu sử dụng Gate chỉ điểm chính xác thành phần nào có giá trị thương mại
```

* **Induced Network Effects (Hiệu ứng mạng nội sinh):** Paul Graham chỉ ra rằng phiên bản cao cấp của hiệu ứng mạng là App Store, nhưng ở giai đoạn đầu, bạn có thể kích hoạt hiệu ứng mạng bằng cách **cho phép người dùng chia sẻ một tài nguyên hữu ích**. Gate an toàn chính là tài sản chia sẻ lý tưởng: nó là file cấu hình nhẹ, miễn phí, không vướng rủi ro pháp lý, và giúp hệ sinh thái an toàn hơn cho cả người đóng góp lẫn người sử dụng lại.

### 1.7 Giúp người dùng kiếm tiền: Phân tích TCO định lượng

> *"Few things make you more powerful than that... they're (a) quick to adopt your product and (b) will pay a lot for it."* — Paul Graham

Bản phân tích tổng chi phí sở hữu (Total Cost of Ownership - TCO) cho một đội ngũ phát triển vận hành 500 thiết bị thông minh trong 1 năm:

| Hạng mục chi phí | Tự xây dựng (DIY in-house) | Dùng SDK chính hãng (1-chip) | LiveKit + Cloud Agent | **Dùng NeuroEdge v5.1** |
|:---|:---:|:---:|:---:|:---:|
| **Nhân sự kỹ thuật chuyên trách** | 3 Kỹ sư ($180k/năm)<br>*(Firmware + Audio + AI)* | 2 Kỹ sư ($120k/năm)<br>*(Chuyên sâu 1 dòng chip)* | 1.5 Kỹ sư ($90k/năm)<br>*(Chuyên WebRTC/Cloud)* | **0.5 Kỹ sư ($30k/năm)**<br>*(Tập trung vào logic)* |
| **Thời gian Bring-up bo mạch mới** | 12 tuần làm việc | 8 tuần làm việc | Không hỗ trợ MCU | **1 tuần (đổi cờ `--target`)** |
| **Chi phí On-site sửa lỗi hiện trường** | Rất cao ($30k/năm)<br>*(Cử kỹ sư tới công trình)* | Cao ($15k/năm)<br>*(Log thủ công qua UART)* | Trung bình ($10k/năm)<br>*(Phụ thuộc mạng)* | **Gần như bằng 0**<br>*(Kéo `.ntrace` về replay)* |
| **Rủi ro Thu hồi sản phẩm (Recall)** | Cao (Thử nghiệm lab sơ sài) | Cao (Không có CI cho physical) | Trung bình (Không có fail-closed)| **Triệt tiêu hoàn toàn**<br>*(Action CI chặn từ commit)* |
| **TỔNG CHI PHÍ NĂM ĐẦU TIÊN** | **~$250.000** | **~$160.000** | **~$120.000** | **~$36.000** *(Tiết kiệm >70%)* |

---

## 2. Bộ lọc quyết định MECE (R1–R4)

Mọi quyết định tính năng đều phải trải qua ma trận 4 quy tắc loại trừ lẫn nhau và bao phủ toàn diện:

```
┌────┬──────────────────────────────────┬───────────────────────────────────────────┐
│ #  │ Quy tắc quyết định               │ Câu hỏi kiểm tra điều kiện                │
├────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ R1 │ Tối ưu hóa Time-to-First-Value   │ Có rút ngắn thời gian từ `pip install`    │
│    │ (TTFV < 10 phút)                 │ đến kết quả phản hồi đầu tiên không?      │
├────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ R2 │ Bất khả thi để bổ sung sau       │ Nếu bỏ qua bây giờ, 12 tháng nữa có thể   │
│    │ (Non-Retrofit Architecture)      │ bổ sung mà không đập đi xây lại không?    │
├────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ R3 │ Nhu cầu thực tế đang chờ đón     │ Đã có khách hàng thật sự yêu cầu và sẵn   │
│    │ (Real Demand Backlog)            │ sàng trả tiền, hay chỉ là giả định?       │
├────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ R4 │ Chặn mở rộng bề mặt pháp lý      │ Có phát sinh giấy phép tài chính, lưu giữ │
│    │ (Legal & Compliance Shield)      │ tiền, KYC, hoặc trách nhiệm pháp lý mới?  │
└────┴──────────────────────────────────┴───────────────────────────────────────────┘
```

* **Logic thực thi:** Nếu **R4 đúng ➔ BÁC BỎ TUYỆT ĐỐI**. Nếu **R1 hoặc R2 đúng ➔ THỰC THI NGAY**. Nếu **R3 sai ➔ HOÃN VÔ THỜI HẠN**.

---

# Phần II — Kiến trúc sản phẩm & Đặc tả API

## 3. Kiến trúc hệ thống 5 lớp

### 3.1 Sơ đồ khối tổng thể & Trục Action CI

```
┌────────────────────────────────────────────────────────────────────────┐
│  L4: AGENT LAYER                                                       │
│      Conversation State Machine · Context Memory · MCP Tool Dispatcher │
├────────────────────────────────────────────────────────────────────────┤
│  L3: ACTION CONTRACT ENGINE (Tài sản sở hữu trí tuệ cốt lõi)           │
│      Typed Gate Verifier · Policy Inheritance · Fail-Closed Circuit     │
├────────────────────────────────────────────────────────────────────────┤
│  L2: PERCEPTION & RUNTIME                                              │
│      Wake-word Engine · Neural VAD · Software AEC · Low-latency STT/TTS│
├────────────────────────────────────────────────────────────────────────┤
│  L1: HARDWARE ABSTRACTION LAYER (HAL)                                  │
│      Bộ 5 nguyên thủy bất biến · Kiểm tra tính tương thích lúc build   │
├────────────────────────────────────────────────────────────────────────┤
│  L0: TARGET IMPLEMENTATIONS (Ba đối tác ngang hàng bình đẳng)           │
│      [ Target: sim ]        [ Target: linux ]     [ Target: esp32s3 ]  │
└────────────────────────────────────────────────────────────────────────┘
         ▲
         └── [ TRỤC XUYÊN SUỐT: ACTION CI ]
             Ghi nhận (.ntrace) ──► Bit-for-bit Replay ──► Khẳng định Logic
```

Năm tầng trên thuộc bản phân phối mã nguồn mở MIT. Toàn bộ hạ tầng điện toán đám mây (Cloud Gateway, Fleet Console) nằm ngoài sơ đồ và giao tiếp qua interface cắm rút.

### 3.2 L0 — Định luật tương đương Target (`sim` · `linux` · `esp32s3`)

> **Định luật:** Ba target là 3 bản hiện thực hóa ngang hàng của cùng một chuẩn HAL. Cùng một file code agent phải chạy hoàn toàn nhất quán trên cả 3 nền tảng mà không cần chỉnh sửa bất kỳ dòng mã nào.

| Tiêu chí kỹ thuật | Target `sim` | Target `linux` | Target `esp32s3` |
|:---|:---|:---|:---|
| **Đẳng cấp kiến trúc** | Hạng nhất (First-class) | Hạng nhất (First-class) | Hạng nhất (First-class) |
| **Môi trường vận hành** | Vòng lặp dev, Action CI | Máy tính công nghiệp, RPi, x86 | Vi điều khiển biên ($5), chip SoC |
| **Tần suất kiểm thử** | Tự động trên mọi Pull Request | Tự động trên mọi Pull Request | Chạy kiểm thử hàng đêm (Nightly) |
| **Phần cứng mô phỏng** | Cảm biến ảo, Mock actuator | Phần cứng thực qua `/dev/gpiod` | Thanh ghi phần cứng thực, GPIO |
| **Giới hạn môi trường** | Không đo được áp lực bộ nhớ chip | Tài nguyên bộ nhớ dư dả | Bộ nhớ SRAM/PSRAM cực kỳ hạn chế |

#### Năm lý do `linux` bắt buộc phải là Target hạng nhất ngay từ Khối 1:
1. **Bằng chứng của Hợp đồng Năng lực (R2):** Một HAL chỉ hỗ trợ một bo mạch duy nhất là một API phụ thuộc phần cứng, không phải một hợp đồng trừu tượng.
2. **Chiều đánh sườn chiến lược (R2):** SDK của các nhà sản xuất silicon không bao giờ hỗ trợ Linux như một đối tác ngang hàng với dòng chip của họ.
3. **Chi phí biên cận 0 (R1):** Linux chính là môi trường dev và môi trường CI; phần lớn đường dẫn thực thi của `sim` được dùng lại nguyên vẹn.
4. **Đáp ứng nhu cầu thực tế của thị trường (R3):** Phần lớn các dự án Physical AI thương mại hiện nay chạy trên các cụm Compute Module (Raspberry Pi/ARM), không phải vi điều khiển đơn lẻ.
5. **Đường thoát an toàn khi chip biên quá tải (R2):** Nếu logic mô hình vượt quá dung lượng bộ nhớ của ESP32-S3, toàn bộ hệ thống có thể chuyển dịch sang phần cứng Linux mà không cần viết lại mã nguồn.

### 3.3 L1 — HAL: Hợp đồng năng lực 5 nguyên thủy

HAL của NeuroEdge là một hợp đồng tương tác hai chiều: Thiết bị khai báo năng lực cung cấp, Agent khai báo yêu cầu sử dụng. Bất kỳ sự lệch pha nào đều bị phát hiện và ngăn chặn **ngay tại thời điểm biên dịch (build-time)**.

Hệ thống rút gọn thành đúng **5 nguyên thủy bất biến**:
1. `audio.in`: Luồng dữ liệu âm thanh đầu vào (PCM frames, Sample rate, AEC state).
2. `audio.out`: Luồng âm thanh đầu ra gửi tới loa hoặc bộ khuếch đại.
3. `digital.out`: Điều khiển trạng thái chân logic (GPIO, PWM, Relay, Xung kích Solenoid).
4. `sensor.read`: Thu thập dữ liệu cảm biến định kỳ hoặc theo ngắt (Motion, Temp, IMU).
5. `display`: Trực quan hóa thông tin (OLED/LCD frame buffer, Đèn LED trạng thái).

### 3.4 L2 — Perception & Runtime hội thoại

Triết lý thiết kế: Bọc lại các thư viện mã nguồn mở tối ưu nhất (Sherpa-ONNX, Silero VAD, WebRTC AEC), không tự viết lại các thuật toán xử lý tín hiệu cơ bản.

Giá trị độc quyền thực sự nằm ở **Máy trạng thái hội thoại thời gian thực (Real-time Conversation State Machine)** nhằm xử lý 4 ca biên phức tạp:
* **Barge-in mượt mà:** Lập tức ngắt luồng TTS và thu hồi lệnh actuator chưa thực thi khi người dùng cất tiếng ngắt lời.
* **Xử lý khoảng lặng động:** Phân biệt chính xác giữa việc tạm dừng để suy nghĩ và kết thúc lượt nói.
* **Truyền phát câu trả lời cục bộ (Partial Streaming):** Phát âm thanh ngay từ các token đầu tiên trước khi LLM hoàn thành toàn bộ câu.
* **Tự phục hồi lỗi STT:** Xử lý các trường hợp nhận diện chuỗi âm thanh rỗng hoặc nhiễu mà không làm treo máy trạng thái.

### 3.5 L3 — Action Contract Engine & Cơ chế Fail-Closed

Đây là tài sản sở hữu trí tuệ cốt lõi (Core IP) của NeuroEdge, chịu trách nhiệm thực thi 4 nhiệm vụ MECE:
1. **Thực thi hợp đồng an toàn:** Mọi lệnh truyền tới actuator bắt buộc phải đi qua Gate tương ứng. HAL từ chối thực thi mọi yêu cầu không mang token xác thực Gate đã pass.
2. **Định tuyến mô hình tối ưu:** Chính sách khai báo cho phép phân loại truy vấn: ý định đơn giản gửi tới System 1 (nhanh, rẻ), trường hợp phức tạp leo thang lên System 2 (chậm, sâu).
3. **Mạch ngắt suy giảm an toàn (Fail-Closed Circuit):** Khi mất kết nối mạng, gặp lỗi timeout, hoặc mô hình AI trả về dữ liệu không hợp lệ, hệ sinh thái mặc định rơi vào trạng thái an toàn: **Chặn hành động**.
4. **Phát hành vi dữ liệu `.ntrace`:** Mỗi chuỗi tương tác sinh ra một file trace hoàn chỉnh, có định dạng chuẩn hóa, cho phép tái hiện lỗi ngoại tuyến bit-for-bit.

### 3.6 Trừu tượng hóa Model (Decoupled Intelligence Layer)

Mô hình AI chỉ là một thành phần hoán đổi được (pluggable component). Luận điểm của NeuroEdge không phụ thuộc vào bất kỳ nhà cung cấp LLM độc quyền nào:
* Interface `SystemOne`: Xử lý phân loại ý định có cấu trúc, phản hồi dưới 100ms (Jev, Distil-BERT, SLM on-device).
* Interface `SystemTwo`: Xử lý suy luận sâu, hội thoại phức tạp (Claude Sonnet, GPT-4o, DeepSeek).
* Toàn bộ các interface này đều bắt buộc phải có đường dẫn dự phòng (fallback path) khai báo được trong cấu hình.

### 3.7 Trục xuyên suốt Action CI & Đặc tả định dạng `.ntrace`

Simulator không phải một bản mock sơ sài; Simulator là một **Target chính thức** thực thi cùng một hợp đồng HAL.

#### Cấu trúc dữ liệu khối của tệp `.ntrace` (Data Upstream Specification):
```json
{
  "trace_version": "neuroedge.trace/v1",
  "metadata": {
    "session_id": "sess_8f9a2b1c",
    "timestamp_utc": "2026-09-20T14:32:01.104Z",
    "target": "esp32s3",
    "board_id": "villa-panel-v2",
    "agent_version": "villa-concierge@0.3.1"
  },
  "events": [
    {
      "offset_ms": 0,
      "type": "audio_in_vad_start",
      "data": { "energy_db": -18.4 }
    },
    {
      "offset_ms": 620,
      "type": "intent_extracted",
      "data": { "intent": "unlock_door", "confidence": 0.94, "system": "SystemOne" }
    },
    {
      "offset_ms": 710,
      "type": "gate_evaluation_begin",
      "data": { "gate": "unlock_door@1.2.0" }
    },
    {
      "offset_ms": 840,
      "type": "gate_evaluation_result",
      "data": {
        "verdict": "ALLOW",
        "evaluations": {
          "guest_authenticated": true,
          "room_matches": true,
          "risk": "low"
        }
      }
    },
    {
      "offset_ms": 845,
      "type": "actuator_command",
      "data": { "pin": "door_lock", "operation": "pulse", "duration_ms": 30000 }
    }
  ]
}
```

Bốn thành phần hợp nhất của Action CI:
* **Record:** Trích xuất toàn bộ luồng sự kiện ra tệp `.ntrace`.
* **Replay:** Tái hiện chính xác chuỗi sự kiện trên bất kỳ target nào (`sim`, `linux`, `esp32s3`).
* **Assert:** Cung cấp thư viện kiểm tra điều kiện an toàn: chân nào được kích hoạt, chân nào tuyệt đối không được cấp điện.
* **Golden Testing:** Khóa chặt chuỗi quyết định tham chiếu. Bất kỳ thay đổi nào trong prompt hoặc model gây lệch kết quả golden sẽ lập tức làm đỏ CI pipeline.

---

## 4. Đặc tả API & Bề mặt công cụ

### 4.1 Nguyên tắc thiết kế API khai báo

1. **Năng lực là khai báo tĩnh (Declarative Capabilities):** Bo mạch và agent cùng khai báo thông số qua file TOML; trình biên dịch đối chiếu tính tương thích lúc build.
2. **Hành động không thể gọi trực tiếp:** Mọi thao tác phần cứng bắt buộc phải thông qua hàm điều phối an toàn `c.do()`.
3. **Gate là dữ liệu có cấu trúc:** Viết bằng YAML schema, quản lý phiên bản độc lập với mã nguồn logic.
4. **Một mã nguồn cho mọi nền tảng:** Cùng một file `agent.py` vận hành trên cả 3 target thông qua cờ dòng lệnh `--target`.
5. **Mặc định Fail-Closed:** Bất kỳ lỗi phát sinh trong quá trình đánh giá gate đều dẫn tới việc chặn hành động.

### 4.2 Đặc tả Phần cứng (`board.toml`)

```toml
# boards/villa-panel.board.toml
[board]
id     = "villa-panel-v2"
target = "esp32s3"

[capabilities."audio.in"]
channels       = 2
sample_rate_hz = 16000
aec            = true

[capabilities."audio.out"]
channels       = 1
sample_rate_hz = 16000

[capabilities."display"]
width  = 320
height = 240

[capabilities."digital.out"]
pins = ["door_lock", "courtesy_lamp"]
```

Cùng một bo mạch định nghĩa cho môi trường công nghiệp `linux` chỉ khác biệt đúng 2 dòng:

```toml
# boards/villa-gateway.board.toml
[board]
id     = "villa-gateway-x86"
target = "linux"

[capabilities."digital.out"]
pins    = ["door_lock", "courtesy_lamp"]
backend = "gpiod"
# Toàn bộ phần còn lại hoàn toàn đồng nhất
```

### 4.3 Đặc tả Yêu cầu Agent (`agent.toml`)

```toml
# agent.toml
[agent]
name    = "villa-concierge"
version = "0.3.1"

[requires]
"audio.in"    = { aec = true }
"audio.out"   = {}
"display"     = { min_width = 240 }
"digital.out" = { pins = ["door_lock"] }

[gates]
unlock_door = "neuroedge://gates/hospitality/physical-access@1.2.0"

[targets]
supported = ["sim", "linux", "esp32s3"]
```

### 4.4 Đặc tả Hành động có kiểu (`@action`) & Xử lý ngoại lệ

```python
# actions/unlock_door.py
from neuroedge import action
from neuroedge.hal import digital
from neuroedge.exceptions import ActionContractViolation

@action(
    name="unlock_door",
    requires="digital.out:door_lock",
    gate="unlock_door"
)
def unlock_door(guest_id: str, duration_s: int = 30) -> None:
    """Mở chốt cửa phòng cho khách đã được xác thực an toàn."""
    # Cơ chế bảo vệ tĩnh: Hàm này không thể gọi trực tiếp trong code agent.
    # Gọi trực tiếp mà không qua c.do() sẽ ném ra ActionContractViolation.
    digital.out("door_lock").pulse(seconds=duration_s)
```

### 4.5 Đặc tả Gate Artifact (`.yaml` schema & `extends`)

```yaml
# gates/unlock_door@1.2.0.yaml
schema:  neuroedge.gate/v1
name:    unlock_door
version: 1.2.0
extends: neuroedge://gates/hospitality/base-access@1.0.0

evaluate:
  guest_authenticated:
    type: bool
    instructions: "Khách đã hoàn tất xác thực danh tính trong phiên hiện tại"
  room_matches:
    type: bool
    instructions: "Số phòng yêu cầu trùng khớp với hồ sơ đặt phòng của khách"
  risk_level:
    type: level
    levels: [low, medium, high]
    instructions: "Đánh giá mức độ rủi ro bất thường tại thời điểm yêu cầu"

allow_when:
  guest_authenticated: true
  room_matches:        true
  risk_level:          { lte: low }

on_block:
  action:  escalate
  to:      human_receptionist
  message: "Yêu cầu cần nhân viên lễ tân xác thực trực tiếp trước khi mở khóa."

budget:
  p95_latency_ms: 120
  fail:           closed      # Mất mạng hoặc timeout -> MẶC ĐỊNH CHẶN HÀNH ĐỘNG
```

### 4.6 Mã nguồn Agent hoàn chỉnh

```python
# agent.py
from neuroedge import Agent, Conversation, SystemOne, SystemTwo
from actions.unlock_door import unlock_door

agent = Agent.from_toml("agent.toml")

# Thiết lập trí thông minh độc lập
agent.mind(
    fast  = SystemOne("jev-latest", fallback="local/intent-distil-8m"),
    slow  = SystemTwo("claude-sonnet-4.5", fallback="local/qwen2.5-3b"),
    route = "fast_first",
)

@agent.on_turn
async def turn(c: Conversation):
    intent = await c.fast.choice(
        "intent",
        options=["faq", "unlock", "service", "other"],
        state={"utterance": c.utterance, "context": c.recall(k=3)},
    )

    if intent.top == "unlock":
        # Gate unlock_door@1.2.0 được kích hoạt đánh giá TRƯỚC KHI cấp xung điện.
        # Nếu gate bị chặn -> tự động chuyển tiếp on_block, hàm không bao giờ chạy.
        await c.do(unlock_door, guest_id=c.session.guest_id)

    elif intent.top == "faq" and intent.confidence > 0.85:
        await c.say(c.recall_answer())  # Hoàn toàn không tốn chi phí gọi System 2

    else:
        await c.say(await c.slow.reply())
```

### 4.7 Bộ kiểm thử hồi quy Action CI

```python
# tests/test_gates.py
import pytest
from neuroedge.testing import replay, scenario

def test_khong_mo_khoa_khi_chua_xac_thuc():
    """Khẳng định: Khách chưa xác thực tuyệt đối không kích hoạt chốt cửa."""
    s = replay("traces/unverified_attempt.ntrace")
    assert s.action("unlock_door").blocked
    assert s.blocked_by == "unlock_door@1.2.0"
    assert s.pin("door_lock").pulse_count == 0

def test_gate_fail_closed_khi_mat_ket_noi():
    """Khẳng định: Khi mạng bị ngắt, gate kích hoạt cơ chế fail-closed."""
    s = scenario("traces/standard_unlock.ntrace", network="offline")
    assert s.action("unlock_door").blocked
    assert s.reason == "gate_unreachable"
    assert s.pin("door_lock").never_pulsed()

@scenario.parametrize(target=["sim", "linux", "esp32s3"])
def test_dinh_luat_tuong_duong_target(target):
    """Khẳng định Định luật tương đương Target: Cùng 1 trace phải cho kết quả nhất quán."""
    s = replay("traces/standard_unlock.ntrace", target=target)
    assert s.decisions == s.golden("traces/standard_unlock.golden")
```

### 4.8 Bề mặt CLI chuẩn hóa

```bash
# Khởi tạo dự án scaffold chuẩn
neuroedge new villa-concierge

# Thực thi vòng lặp phát triển cục bộ
neuroedge run --target sim             # Mở giao diện mô phỏng trên trình duyệt
neuroedge run --target linux           # Chạy trực tiếp trên Raspberry Pi / x86
neuroedge build --target esp32s3 --board villa-panel  # Biên dịch nạp firmware

# Kiểm thử hồi quy tự động trong CI
neuroedge test                         # Chạy toàn bộ Action CI test suite
neuroedge verify --targets sim,linux,esp32s3   # Khẳng định tính tương đương target

# Thu thập và tái hiện sự cố hiện trường
neuroedge record --target esp32s3 --out traces/
neuroedge replay traces/incident.ntrace --target sim

# Quản trị hệ sinh thái Gate
neuroedge gate publish gates/unlock_door@1.2.0.yaml
neuroedge gate add neuroedge://gates/robotics/arm-safety@2.0.0
```

### 4.9 Báo cáo vi phạm hợp đồng tại thời điểm build

```
$ neuroedge build --target esp32s3 --board villa-panel

✗ CAPABILITY CONTRACT MISMATCH — Quá trình đóng gói firmware bị dừng lại!
────────────────────────────────────────────────────────────────────────────
Agent [villa-concierge@0.3.1] yêu cầu:
  ✖ sensor.read:motion (sử dụng tại: actions/auto_light.py:14)

Bo mạch [villa-panel-v2] chỉ cung cấp:
  ✔ audio.in, audio.out, display, digital.out:[door_lock, courtesy_lamp]

HÀNH ĐỘNG KHẮC PHỤC:
  → Bổ sung cảm biến motion vào board.toml, hoặc loại bỏ yêu cầu khỏi agent.toml.

Lỗi xung đột này đã được ngăn chặn trước khi xuất xưởng ra hiện trường.
────────────────────────────────────────────────────────────────────────────
```

---

# Phần III — Lộ trình thực thi & Mô hình kinh doanh

## 5. Lộ trình 4 Khối công việc & Cổng thanh khoản

```
[ KHỐI 1a: SIM + LINUX + CI ] (Tháng 0 - 1.5)
              │
              ▼
[ KHỐI 1b: ESP32-S3 + VOICE ] (Tháng 1.5 - 2.5) ──► [ HOÀN TẤT LÕI MIT ]
              │                                             │
              ├─────────────────────────────────────────────┘
              ▼
┌───────────────────────────────┬───────────────────────────────┐
│ KHỐI 2: COMMERCIAL PLANE      │ KHỐI 3: RAILS HẠ TẦNG NỀN     │
│ (Tháng 2.5 - 6)               │ (Tháng 2.5 - 6, Song song)    │
│ • Hosted Gateway (Inference)  │ • Gate Registry & Versioning  │
│ • Fleet Management OS         │ • Usage Metering Rails        │
└──────────────┬────────────────┴───────────────┬───────────────┘
               │                                │
               └────────────────┬───────────────┘
                                ▼
               [ KHỐI 4: AURA VERTICAL FULL-STACK ]
               (Tháng 6 - 12: Triển khai thực địa)
                                │
                                ▼
               [ CỔNG THANH KHOẢN ĐỊNH LƯỢNG ]
               (Ngưỡng kích hoạt 4 điều kiện MECE)
                                │
                                ▼
               [ KHỐI 5: MARKETPLACE & PAY ]
               (Tháng 18+: Thương mại hóa mở rộng)
```

### 5.1 Khối 1 — Lõi mã nguồn mở MIT (Chia tách 1a & 1b)

Để giải quyết dứt điểm rủi ro kéo dài tiến độ (Phụ lục C.1), Khối 1 được phân tách logic thành 2 giai đoạn kế tiếp:

#### Khối 1a — Nền tảng Logic & CI (Tuần 0–6)
* **Mục tiêu tối thượng:** Đảm bảo một lập trình viên lạ đạt được Time-to-First-Value (TTFV) **dưới 10 phút** trên máy tính cá nhân.
* **Phạm vi hoàn thành:**
  * Lớp trừu tượng HAL + Action Contract Engine + Bề mặt CLI cơ bản.
  * Hoàn thiện 2 Target đầu tiên: `sim` (trình duyệt) và `linux` (x86/ARM).
  * Action CI Engine: cơ chế record, replay `.ntrace` và assert logic.
  * 1 mẫu ứng dụng tham chiếu hoàn chỉnh (Smart Concierge).

#### Khối 1b — Hiện thực hóa Phần cứng Vi điều khiển (Tuần 6–10)
* **Mục tiêu:** Chứng minh toàn diện Định luật tương đương Target trên vi điều khiển biên $5.
* **Phạm vi hoàn thành:**
  * Port HAL hoàn chỉnh lên target `esp32s3` thông qua ESP-IDF toolchain.
  * Voice pipeline tối ưu hóa bộ nhớ: WebRTC AEC, Silero VAD, Opus streaming codec.
  * Công cụ CLI `neuroedge verify` kiểm tra tính tương đương bit-for-bit giữa 3 target.

### 5.2 Khối 2 — Commercial Plane & Kinh tế học Fleet Management

Mặt phẳng thương mại duy nhất của NeuroEdge được xây dựng dựa trên nguyên tắc phân định biên lợi nhuận rõ ràng:

#### 1. Mặt phẳng Inference Gateway (Phễu onboarding biên mỏng)
* **Mục tiêu:** Thu hút tối đa lượng thiết bị kết nối vào nền tảng.
* **Mô hình định giá:** Bán sát giá vốn (Cost-plus 5–10%). Đúng như Paul Graham cảnh báo tại Note [4], không bán miễn phí để bảo toàn tín hiệu sẵn sàng trả tiền từ khách hàng thật.
* **Giá trị đem lại cho Dev:** Một endpoint duy nhất, tự động chuyển đổi dự phòng (failover) giữa các nhà cung cấp model, quản lý hạn mức cứng cho từng thiết bị để ngăn chặn rủi ro cháy tài khoản do thiết bị lỗi lặp vòng lặp.

#### 2. Mặt phẳng Fleet Management OS (Nguồn biên lợi nhuận cao)
* **Mục tiêu:** Đảm bảo hoạt động vận hành an toàn và liên tục cho các đội thiết bị lớn.
* **Mô hình định giá:** Thu phí định kỳ theo số lượng thiết bị hoạt động thực tế:
  $$\text{Doanh thu Fleet hàng tháng} = N_{\text{thiết bị}} \times \$1.00/\text{node/tháng}$$
* **Năm tính năng kỹ thuật cốt lõi:**
  1. **Provisioning tự động:** Cấp chứng chỉ định danh mật mã duy nhất cho từng thiết bị ở lần boot đầu.
  2. **OTA Rollout theo đợt & Auto-rollback:** Triển khai firmware theo tỉ lệ phần trăm; tự động hoàn tác về phiên bản trước nếu phát hiện vòng lặp reboot hoặc lỗi gate.
  3. **Giám sát sức khỏe phần cứng:** Theo dõi trực tiếp tình trạng online/offline, chất lượng tín hiệu RSSI, nhiệt độ chip, và dung lượng bộ nhớ khả dụng.
  4. **Cập nhật Policy Gate từ xa:** Cập nhật ngưỡng an toàn của Gate trên toàn bộ fleet trong 1 giây mà **không cần nạp lại firmware**.
  5. **Telemetry & Remote Replay:** Tự động đẩy file `.ntrace` khi có sự cố hiện trường về hệ thống trung tâm để kỹ sư replay lại trên máy tính cá nhân.

### 5.3 Khối 3 — Bảy đường ray nền tảng (Rails)

Xây dựng song song với Khối 2. Đây là các thành phần hạ tầng không thể bổ sung chắp vá về sau:
1. **Public Gate Registry:** Hệ thống lập chỉ mục và phân phối các Policy Gate mở (`neuroedge gate add`).
2. **Package Manifest & Semver:** Quản lý phụ thuộc chính xác theo phiên bản ngữ nghĩa cho cả Agent và Gate.
3. **Capability Declaration Matrix:** Chuẩn hóa cơ chế kiểm tra tính tương thích giữa Agent và Bo mạch lúc build.
4. **Gate Inheritance (`extends`):** Cho phép các công ty kế thừa các quy chuẩn an toàn nền tảng của ngành và ghi đè các điều kiện riêng.
5. **Stable Hardware Fingerprint:** Cơ chế nhận dạng phần cứng chống giả mạo danh tính thiết bị.
6. **Granular Usage Metering:** Hạ tầng đếm chi tiết số lượt đánh giá gate và số token tiêu thụ cho từng thiết bị.
7. **Execution Sandbox:** Cơ chế phân quyền an toàn, ngăn chặn mã nguồn của bên thứ ba truy cập trái phép vào các chân actuator nhạy cảm.

### 5.4 Khối 4 — Triển khai dọc AURA Full-Stack

> *"Eat your way gradually through the customer by doing all their hardest work for them."* — Paul Graham

Áp dụng chiến lược đi Full-Stack vào một thị trường dọc hẹp: **Hệ thống Quản lý Biệt thự & Khách sạn nghỉ dưỡng thông minh (AURA)**.
* **Mục tiêu kép:** (1) Tạo dòng tiền sớm để tự trang trải chi phí vận hành mà không phụ thuộc vào vốn gọi; (2) Đóng vai trò môi trường kiểm thử thực địa khắt khe nhất cho chính framework NeuroEdge.
* **Kỷ luật kiến trúc tuyệt đối:** AURA sử dụng 100% mã nguồn và API công khai của NeuroEdge. Tuyệt đối không tạo nhánh code nội bộ hoặc các API đặc quyền. Bất kỳ khó khăn nào mà kỹ sư AURA gặp phải chính là bằng chứng framework đang thiếu tính năng đó.

### 5.5 Cổng thanh khoản định lượng (The Liquidity Gate)

Nhằm triệt tiêu vĩnh viễn rủi ro xây dựng chợ ứng dụng rỗng, việc mở rộng sang Khối 5 (Marketplace & Pay) bị **khóa cứng tuyệt đối** cho đến khi thỏa mãn đầy đủ **cả 4 điều kiện MECE**:

```
┌────┬──────────────────────────────────┬───────────────────────────────────────────┐
│ #  │ Chỉ số thanh khoản               │ Ngưỡng kích hoạt định lượng bắt buộc       │
├────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ G1 │ Quy mô Thiết bị hoạt động        │ ≥ 10.000 thiết bị Active hàng tháng       │
│    │ (Active Device Base)             │    (gửi telemetry ổn định về Fleet)       │
├────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ G2 │ Quy mô Nguồn cung chất lượng     │ ≥ 50 Gates do bên thứ ba tự xuất bản      │
│    │ (Third-party Supply)             │    (mỗi Gate có ≥ 5 lượt cài đặt thực tế) │
├────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ G3 │ Tỷ lệ Trao đổi Thực tế           │ > 30% tổng số thiết bị chạy ít nhất 1 Gate│
│    │ (Organic Liquidity Ratio)        │    do người khác viết                     │
├────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ G4 │ Giao dịch tự phát ngoài nền tảng │ Có bằng chứng ghi nhận người dùng tự trả  │
│    │ (Off-platform Transactions)      │    tiền cho nhau để mua Gate/Agent logic  │
└────┴──────────────────────────────────┴───────────────────────────────────────────┘
```

### 5.6 Khối 5 — Gate Marketplace & Agent Pay (Thương mại hóa)

Chỉ được phép kích hoạt sau khi vượt qua Cổng thanh khoản. Lúc này, việc thương mại hóa không còn là một canh bạc suy đoán, mà là hành động chuẩn hóa một thị trường đã tự phát triển.
* **Đối tượng hàng hóa chính:** Không phải toàn bộ agent nguyên khối, mà là **các Gate an toàn đã được tinh chỉnh qua hàng ngàn giờ chạy thực địa** (ví dụ: Gate kiểm soát va chạm cho cánh tay robot, Gate bảo mật kiểm soát ra vào tòa nhà).
* **Hạ tầng thanh toán Agent Pay:** Khi tiền đã chảy qua Gateway để chi trả hóa đơn hạ tầng, việc tích hợp cơ chế phân chia doanh thu tự động cho các tác giả Gate bên thứ ba chỉ là một bước mở rộng kỹ thuật ngắn.

---

## 6. Ranh giới sản phẩm tường minh & Ma trận Trade-off

Bảng xác định ranh giới loại trừ tường minh nhằm bảo vệ sự tập trung tối đa của tổ chức:

| Hạng mục đề xuất | Trạng thái xử lý | Quy tắc áp dụng | Phân tích Đánh đổi & Chi phí cơ hội (Trade-off Matrix) |
|:---|:---|:---:|:---|
| **Marketplace thương mại có thu phí** | Chặn tới sau Cổng | R3 | **Đánh đổi:** Mất cơ hội thu tiền hoa hồng sớm.<br>**Lợi ích:** Tránh lãng phí 6 tháng xây dựng một chợ ứng dụng không có thanh khoản. |
| **Agent-to-Agent Crypto Pay, Escrow** | Chặn tới sau Cổng | R4 | **Đánh đổi:** Bỏ qua trào lưu công nghệ Web3/Crypto.<br>**Lợi ích:** Bảo vệ công ty khỏi toàn bộ gánh nặng pháp lý về phòng chống rửa tiền và giấy phép tài chính. |
| **Thị giác máy tính sâu (Camera, NPU)** | Hoãn sau Tháng 12 | R1 | **Đánh đổi:** Tạm thời không phục vụ các bài toán Robot thị giác phức tạp.<br>**Lợi ích:** Đảm bảo TTFV của Voice & Control đạt dưới 10 phút, không làm phân mảnh tài nguyên phần cứng. |
| **Hỗ trợ vi xử lý Jetson, Matter** | Hoãn sau Tháng 12 | R3 | **Đánh đổi:** Giới hạn phạm vi phần cứng ban đầu.<br>**Lợi ích:** Ba target hiện tại đã đủ để chứng minh toàn diện Định luật tương đương Target. |
| **SSO/SAML, SOC 2, RBAC phức tạp** | Hoãn sau Tháng 12 | R3 | **Đánh đổi:** Chưa thể ký các hợp đồng doanh nghiệp lớn yêu cầu bảo mật cao.<br>**Lợi ích:** Không sa lầy vào chu kỳ đàm phán bán hàng kéo dài của khối doanh nghiệp lớn. |
| **Cụm điều phối Kubernetes phức tạp** | Loại bỏ vĩnh viễn | R1 | **Đánh đổi:** Khó mở rộng tới quy mô hàng triệu node ngay lập tức.<br>**Lợi ích:** Một kiến trúc đơn giản (1 Postgres, 1 Redis, 1 Event Bus) là quá đủ để vận hành 50.000 thiết bị đầu tiên với chi phí vận hành tối thiểu. |

---

# Phần IV — Kiểm chứng thị trường & Quản trị rủi ro

## 7. Định vị cạnh tranh & Lợi thế bất công

### 7.1 Bản đồ đối thủ & Phân tích khoảng trống

```
                            ĐỘ PHỦ PHẦN CỨNG
                                   ▲
                                   │
                           [ ESP-Claw ]   ★ NEUROEDGE v5.1
                          (Chính hãng,    (Đa nền tảng, Action CI,
                           1-chip ESP32)   Fail-Closed Gates)
                                   │
   ────────────────────────────────┼────────────────────────────────►
   THUẦN ĐIỀU PHỐI SOFTWARE        │               KIỂM THỬ HÀNH ĐỘNG
                                   │               VẬT LÝ TOÀN DIỆN
      [ LangChain / CrewAI ]       │         [ XiaoZhi ]
     (Thiếu trừu tượng phần cứng,  │        (Voice pipeline tốt,
      coi action là API call)      │         thiếu kiểm soát an toàn)
                                   │
                                   ▼
```

Phân tích bản chất cấu trúc của 4 nhóm đối thủ:
1. **ESP-Claw (Espressif):** Rất mạnh về tối ưu hóa trên chip ESP32. Tuy nhiên, về mặt cấu trúc kinh doanh, họ bị khóa chặt vào việc bán silicon; họ không bao giờ phát triển một simulator độc lập trên Linux coi chip của đối thủ là ngang hàng.
2. **XiaoZhi AI:** Sở hữu cộng đồng người dùng voice agent mã nguồn mở rất lớn. Tuy nhiên, kiến trúc của họ thiếu hoàn toàn lớp trừu tượng phần cứng HAL và khái niệm hợp đồng hành động; logic hội thoại gắn chặt trực tiếp vào việc thực thi lệnh phần cứng.
3. **LiveKit Agents / Pipecat:** Hạ tầng truyền thông thời gian thực WebRTC rất mạnh trên đám mây. Tuy nhiên, mô hình kinh doanh của họ dựa trên băng thông đám mây; việc hỗ trợ thiết bị biên chạy ngoại tuyến hoàn toàn (offline-first) mâu thuẫn trực tiếp với doanh thu của chính họ.
4. **LangChain / LlamaIndex:** Thống trị hệ sinh thái phần mềm thuần túy. Họ không có khái niệm về chân cắm vật lý, xung điện, hay rủi ro cơ học; một hành vi sai lầm trong thế giới phần mềm của họ chỉ là một log lỗi trên console.

### 7.2 Ba Moat cấu trúc không thể sao chép

| # | Lợi thế cạnh tranh cấu trúc | Rào cản kỹ thuật ngăn chặn sao chép |
|:---:|:---|:---|
| **1** | **Hợp đồng hành động có kiểu + Action CI** | Đòi hỏi 3 quyết định kiến trúc đồng thời ngay từ ngày đầu tiên: Simulator là target thật, Gate là dữ liệu có version, và Trace là công dân hạng nhất. Đối thủ đã xuất xưởng sản phẩm bắt buộc phải đập đi viết lại toàn bộ kiến trúc nếu muốn sao chép. |
| **2** | **HAL hợp đồng năng lực trên 3 target ngang hàng** | SDK của các nhà sản xuất chip không thể có khái niệm này vì mâu thuẫn với động cơ bán silicon. Việc bổ sung tính năng này sau này đòi hỏi thay đổi toàn bộ tầng trừu tượng hóa phần cứng. |
| **3** | **Sở hữu Định dạng Gate và Trace (`.ntrace`)** | Theo ghi chú [2] của Paul Graham: Trong một lĩnh vực mới chưa có chuẩn mực, đề xuất đầu tiên thường trở thành chuẩn mực công nghiệp. Khi định dạng này được cộng đồng chấp nhận, chi phí chuyển đổi (switching cost) của các nhà phát triển là vô cùng lớn. |

### 7.3 Những mặt trận tuyệt đối không cạnh tranh

NeuroEdge kiên quyết từ bỏ 3 cuộc đua tốn kém:
* **Không cạnh tranh về giá inference:** Để mặc các model vendor tự tàn sát lẫn nhau trong cuộc đua hạ giá token.
* **Không cạnh tranh về độ sâu driver một-chip:** Nhường toàn bộ việc viết driver ngoại vi cấp thấp cho các SDK chính hãng; NeuroEdge chỉ chuẩn hóa 5 nguyên thủy của HAL.
* **Không cạnh tranh về bề rộng hỗ trợ phần cứng:** Chỉ tập trung hỗ trợ sâu sắc 3 target tham chiếu chuẩn mực (`sim`, `linux`, `esp32s3`).

---

## 8. Ma trận 4 Rủi ro sống còn & Chiến lược giảm thiểu

```
┌────┬───────────────────────┬───────────────────────────────────┬───────────────────────────────────────┐
│ #  │ Rủi ro sống còn       │ Kịch bản đe dọa cấu trúc          │ Chiến lược giảm thiểu chủ động        │
├────┼───────────────────────┼───────────────────────────────────┼───────────────────────────────────────┤
│ R1 │ Phụ thuộc Vendor      │ Nhà cung cấp model thay đổi giá,  │ Trừu tượng hóa trí tuệ qua Interface  │
│    │ (Model Vendor Risk)   │ khóa API hoặc tự tung framework.  │ System 1/2. Sản phẩm là lớp bảo vệ    │
│    │                       │                                   │ an toàn; đổi model không đổi định vị. │
├────┼───────────────────────┼───────────────────────────────────┼───────────────────────────────────────┤
│ R2 │ Nền tảng Bán dẫn      │ Hãng chip phát hành framework     │ Chiến lược đánh sườn: Thắng ở chiều   │
│    │ (Chipmaker Risk)      │ IoT miễn phí vĩnh viễn.           │ kiểm thử đa nền tảng và Action CI mà  │
│    │                       │                                   │ hãng chip về bản chất không thể làm.  │
├────┼───────────────────────┼───────────────────────────────────┼───────────────────────────────────────┤
│ R3 │ Bào mòn Biên Lợi nhuận│ Giá token inference lao dốc;      │ 80% biên lợi nhuận ròng đến từ phí    │
│    │ (Margin Compression)  │ mô hình reseller không có lãi.    │ Fleet Management ($/device/tháng);    │
│    │                       │                                   │ bán inference sát giá vốn làm phễu.   │
├────┼───────────────────────┼───────────────────────────────────┼───────────────────────────────────────┤
│ R4 │ Phân mảnh Phạm vi     │ Áp lực xây dựng tính năng tùy biến│ Đóng băng quy tắc R1–R4 và các ngưỡng │
│    │ (Scope Dilution)      │ cho khách hàng doanh nghiệp đầu.  │ Cổng thanh khoản thành văn bản cứng.  │
└────┴───────────────────────┴───────────────────────────────────┴───────────────────────────────────────┘
```

---

## 9. Hệ chỉ số hiệu suất MECE (Performance Framework)

Đo lường sự thành công bằng kết quả vận hành thực tế của khách hàng, tuyệt đối không dùng số lượng GitHub Stars (chỉ đo người xem tò mò, không đo người sử dụng thực tế).

### 9.1 Khối 1 — Lõi mã nguồn mở (Tháng 2.5)

| Chỉ số hiệu suất cốt lõi | Ngưỡng cam kết định lượng | Ý nghĩa chiến lược |
|:---|:---:|:---|
| **Time-to-First-Value (TTFV)** | **< 10 phút** (đo trên 10 maker lạ) | Đo lường tính tinh gọn của trải nghiệm cài đặt và chạy thử ban đầu. |
| **Định luật tương đương Target** | **100% Pass** trong `neuroedge verify` | Chứng minh tính nhất quán logic tuyệt đối trên cả 3 target. |
| **Tỷ lệ giữ lại Action CI** | **≥ 50%** dự án dùng `neuroedge new` | Đo lường mức độ thâm nhập của thói quen kiểm thử an toàn tự động. |
| **Tỷ lệ chuyển đổi Sim ➔ Hardware** | **≥ 15%** trong vòng 30 ngày | **Chốt dứt điểm C.4:** Đảm bảo phễu chuyển đổi từ mô phỏng sang thiết bị thật. |
| **Tài sản phân phối lan truyền** | 3 ví dụ mẫu + 1 GIF 15 giây | Vũ khí phân phối tự nhiên hàng đầu trong cộng đồng mã nguồn mở. |

### 9.2 Khối 2 & Khối 3 — Thương mại & Rails (Tháng 6)

| Chỉ số hiệu suất cốt lõi | Ngưỡng cam kết định lượng | Ý nghĩa chiến lược |
|:---|:---:|:---|
| **Độ tin cậy của hạ tầng OTA** | **1.000 thiết bị / 0 thiết bị brick** | Thước đo sống còn để khách hàng tin tưởng giao phó đội thiết bị. |
| **SLA Ngân sách Độ trễ Voice P95** | **< 850 ms** round-trip trên Wi-Fi | **Chốt dứt điểm C.3:** Cam kết công khai từ lúc dứt lời đến khi loa phát tiếng. |
| **SLA Ngân sách Đánh giá Gate P95**| **< 120 ms** (Local) / **< 450 ms** (Cloud)| Đảm bảo chốt an toàn không làm gián đoạn trải nghiệm tương tác tự nhiên. |
| **Hiệu quả Định tuyến mô hình** | Tiết kiệm **≥ 60%** chi phí token | Bằng chứng định lượng chứng minh giá trị của bộ định tuyến System 1/2. |
| **Mức độ Chia sẻ Gate cộng đồng** | ≥ 20 Gates có ≥ 5 lượt cài đặt lại | Kích hoạt thành công hiệu ứng mạng nội sinh trước khi mở chợ ứng dụng. |
| **Điểm cân bằng Doanh thu** | Doanh thu Fleet > Doanh thu Inference | Khẳng định mô hình kinh doanh bền vững không phụ thuộc vào bán token. |

### 9.3 Khối 4 — Thực địa AURA (Tháng 12)

| Chỉ số hiệu suất cốt lõi | Ngưỡng cam kết định lượng | Ý nghĩa chiến lược |
|:---|:---:|:---|
| **Tính toàn vẹn của Framework** | 100% mã nguồn chạy trên bản public | Đảm bảo tính minh bạch, không sử dụng tính năng nội bộ đặc quyền. |
| **Tiến độ Cổng thanh khoản** | Đạt **≥ 75%** trên cả 4 tiêu chí | Chuẩn bị đầy đủ cơ sở thực nghiệm trước khi thương mại hóa Khối 5. |
| **Bằng chứng Giúp khách hàng kiếm tiền**| Giảm **≥ 70%** chi phí on-site sửa lỗi | Nghiệm thu case study thực tế chứng minh giá trị kinh tế trực tiếp (§1.7). |

---

# Phần V — Phụ lục

## Phụ lục A — Bảng đối chiếu toàn diện luận điểm Paul Graham

Tiểu luận *"Making Startups Powerful"* (Paul Graham, 09/2026) cung cấp bộ khung heuristic giúp nhận diện các điểm đòn bẩy chiến lược để gia tăng vị thế quyền lực của một công ty khởi nghiệp:

| Nguyên lý của Paul Graham | Trạng thái áp dụng | Hành động cụ thể của NeuroEdge v5.1 | Lợi ích tối thượng đem lại cho Khách hàng |
|:---|:---:|:---|:---|
| **Sở hữu Quan hệ Khách hàng** | Triển khai ngay | Hosted Gateway đóng vai trò trung gian định tuyến giữa logic và model. | Nhà phát triển đổi model từ xa mà không phải nạp lại firmware cho thiết bị. |
| **Để tiền chảy qua mình** | Triển khai ngay | Hóa đơn tập trung hóa toàn bộ chi phí inference, OTA và fleet telemetry. | Khách hàng chỉ phải thanh toán một hóa đơn minh bạch thay vì năm nhà cung cấp. |
| **Lấy dữ liệu sớm (Mẫu Rippling)** | Triển khai ngay | Sở hữu định dạng trace tại Simulator nơi hành động vật lý sinh ra lần đầu. | Kỹ sư sở hữu công cụ phân tích an toàn mà họ bắt buộc phải cần đến. |
| **Bán cho khách sớm (Mẫu Stripe)** | Triển khai ngay | Tiếp cận các nhà phát triển độc lập (Maker) tại thiết bị số 1 qua self-serve. | Khách hàng cài đặt và chạy thử ngay trong 10 phút, không qua quy trình mua sắm. |
| **Hào phóng (Generosity)** | Triển khai ngay | Mở mã nguồn toàn bộ lõi HAL, Action Contract Engine và Action CI (MIT). | Khách hàng không phải trả tiền để có được sự an toàn cơ bản cho thiết bị. |
| **Định nghĩa chuẩn sớm (Note [2])** | Triển khai ngay | Đưa định dạng Gate YAML và `.ntrace` thành chuẩn công nghiệp mở. | Cung cấp một ngôn ngữ thống nhất duy nhất để mô tả "thế nào là một hành vi an toàn". |
| **Hiệu ứng mạng qua chia sẻ** | Triển khai ngay | Xây dựng Gate Registry cho phép kế thừa chính sách qua cú pháp `extends`. | Nhà phát triển tái sử dụng được các chính sách an toàn đã qua hàng ngàn giờ thử lửa. |
| **Giúp người dùng kiếm tiền** | Triển khai ngay | Triệt tiêu chi phí thu hồi sản phẩm, cắt giảm 80% chuyến đi sửa lỗi hiện trường. | Giúp các công ty phần cứng tiết kiệm hàng trăm ngàn USD chi phí vận hành thực tế. |
| **Chiến lược đánh sườn (Note [9])** | Xuyên suốt | Thắng ở chiều không gian kiểm thử hành động an toàn cắt ngang mọi phần cứng. | Khách hàng không bị khóa chặt vào hệ sinh thái chip của một nhà sản xuất duy nhất. |
| **Mô hình Full-Stack dọc** | Khối 4 | Triển khai giải pháp AURA để tự kiểm nghiệm độ bền bỉ của framework. | Đảm nhận phần việc khó nhất của người vận hành: chịu trách nhiệm khi thiết bị sai sót. |
| **Chơi ván cờ dài (The Long Game)** | Xuyên suốt | Xây dựng sẵn 7 đường ray nền tảng (Rails) trước khi có nhu cầu thương mại. | Hạ tầng sẵn sàng mở rộng ngay khi khách hàng đạt quy mô lớn mà không cần đập đi xây lại. |
| **Cảnh báo Bán quá rẻ (Note [4])** | Tuân thủ nghiêm | Bán inference sát giá vốn nhưng tuyệt đối không miễn phí. | Bảo toàn tín hiệu kinh doanh thực tế từ sự sẵn sàng chi trả của khách hàng. |
| **Cảnh báo Dòng Token (Note [1])** | Tuân thủ nghiêm | Trọng tâm biên lợi nhuận nằm ở Fleet Management OS, không dựa vào token. | Tránh nguy cơ bị các nhà cung cấp mô hình nuốt chửng biên lợi nhuận. |

---

## Phụ lục B — Từ điển thuật ngữ chuẩn mực

| Thuật ngữ kỹ thuật | Định nghĩa chuẩn xác trong ngữ cảnh NeuroEdge |
|:---|:---|
| **Hợp đồng hành động (Action Contract)** | Ràng buộc logic bắt buộc giữa một hành động vật lý và Gate kiểm soát; HAL từ chối thực thi nếu không có chữ ký xác thực gate đã pass. |
| **Gate Artifact** | File khai báo cấu trúc tĩnh (`.yaml`), có quản lý phiên bản (semver), định nghĩa các điều kiện an toàn cho phép một hành vi diễn ra. |
| **Action CI** | Trục kiểm thử hồi quy tự động: ghi nhận phiên thật ngoài hiện trường, replay bit-for-bit trên simulator, và khẳng định các trạng thái logic. |
| **`.ntrace`** | Định dạng dữ liệu chuẩn hóa lưu trữ toàn bộ luồng sự kiện: âm thanh vào, dữ liệu cảm biến, quyết định của gate, và trạng thái kích hoạt chân phần cứng. |
| **Fail-Closed** | Nguyên tắc an toàn tối thượng: khi gặp lỗi mạng, timeout, hoặc suy luận bất thường, hệ thống tự động khóa toàn bộ lệnh điều khiển ngoại vi. |
| **HAL (Hợp đồng Năng lực)** | Lớp trừu tượng hóa phần cứng hai chiều: thiết bị khai báo năng lực, agent khai báo yêu cầu, đối chiếu tương thích ngay khi biên dịch. |
| **Định luật tương đương Target** | Định lý bắt buộc: cùng một mã nguồn logic agent phải cho ra các quyết định hành vi giống hệt nhau trên cả 3 target `sim`, `linux`, `esp32s3`. |
| **System 1 / System 2** | Kiến trúc phân tách trí tuệ: System 1 xử lý phân loại cấu trúc siêu tốc cục bộ; System 2 xử lý suy luận sâu trên đám mây. |
| **Time-to-First-Value (TTFV)** | Khoảng thời gian đo lường từ khi người dùng gõ lệnh cài đặt đầu tiên đến khi nhìn thấy agent đưa ra phản hồi an toàn đầu tiên. |
| **Cổng thanh khoản (Liquidity Gate)** | Bộ 4 điều kiện định lượng bắt buộc phải vượt qua trước khi kích hoạt các tính năng thương mại hóa Marketplace và Thanh toán. |

---

## Phụ lục C — Biên bản giải quyết 100% quyết định mở

Bảng ghi nhận phương án giải quyết dứt điểm 4 vấn đề kỹ thuật từng để mở trong các phiên bản trước:

```
┌────┬───────────────────────┬──────────────────────┬────────────────────────────────────────────┐
│ #  │ Vấn đề kỹ thuật mở    │ Các phương án xem xét│ Quyết định giải quyết dứt điểm (v5.1)      │
├────┼───────────────────────┼──────────────────────┼────────────────────────────────────────────┤
│ C1 │ Phạm vi Khối 1 vs     │ A. Cắt bớt tính năng │ CHỌN PHƯƠNG ÁN C:                          │
│    │ Thời hạn 2 tháng      │ B. Kéo dài 4 tháng   │ Phân tách thành Khối 1a (Tuần 0–6: Sim,    │
│    │                       │ C. Tách khối 1a & 1b │ Linux, Action CI) và Khối 1b (Tuần 6–10:   │
│    │                       │                      │ ESP32-S3, Voice). Giữ vững cam kết TTFV.   │
├────┼───────────────────────┼──────────────────────┼────────────────────────────────────────────┤
│ C2 │ Thời điểm triển khai  │ A. Làm ngay Tuần 1   │ CHỌN PHƯƠNG ÁN B:                          │
│    │ Fallback Model cục bộ │ B. Chờ chỉ báo bật   │ Hoàn thiện Interface trừu tượng ở Tuần 1;  │
│    │ đã tinh chỉnh         │ C. Bỏ qua vĩnh viễn  │ chỉ đầu tư nguồn lực tune model cục bộ khi │
│    │                       │                      │ các nhà cung cấp model có dấu hiệu siết API│
├────┼───────────────────────┼──────────────────────┼────────────────────────────────────────────┤
│ C3 │ Công bố Ngân sách     │ A. Giữ kín nội bộ    │ CHỌN PHƯƠNG ÁN B:                          │
│    │ Độ trễ SLA công khai  │ B. Cam kết công khai │ Công bố công khai bộ chuẩn SLA:            │
│    │                       │    ngân sách P95     │ • P95 Voice round-trip < 850 ms (Wi-Fi).   │
│    │                       │                      │ • P95 Gate evaluation < 120 ms (Local).    │
├────┼───────────────────────┼──────────────────────┼────────────────────────────────────────────┤
│ C4 │ Ngưỡng Chuyển đổi     │ A. Đặt số ngẫu nhiên │ CHỌN PHƯƠNG ÁN B:                          │
│    │ Sim ──► Hardware      │ B. Chốt ngưỡng sàn   │ Ấn định ngưỡng sàn bắt buộc: ≥ 15% người   │
│    │                       │    dựa trên phễu     │ dùng chạy `sim` tiến hành nạp code lên     │
│    │                       │                      │ bo mạch thật trong vòng 30 ngày.           │
└────┴───────────────────────┴──────────────────────┴────────────────────────────────────────────┘
```

---

*Tài liệu được phê duyệt và lưu hành nội bộ — Dự án NeuroEdge 2026*
