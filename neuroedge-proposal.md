# NeuroEdge

## Hợp đồng hành động có kiểu cho Physical AI

**Phiên bản:** 5.2
**Ngày:** 21 tháng 9, 2026
**Đối tượng đọc:** Đội ngũ sản phẩm · Đối tác phần cứng · Nhà phát triển nền tảng · Khách hàng vận hành đội thiết bị
**Phạm vi tài liệu:** Định vị sản phẩm · Kiến trúc 5 lớp · Đặc tả API và định dạng · Mô hình thương mại · Lộ trình · Ranh giới · Hệ chỉ số
**Ngoài phạm vi:** Cấu trúc sở hữu · Kế hoạch gọi vốn · Hợp đồng pháp lý

---

## Mục lục

**Phần 0 — Tóm tắt điều hành**

- [0.1 Bối cảnh](#01-bối-cảnh)
- [0.2 Vấn đề cốt lõi](#02-vấn-đề-cốt-lõi)
- [0.3 Tuyên ngôn sản phẩm](#03-tuyên-ngôn-sản-phẩm)
- [0.4 Năm quyết định bất biến](#04-năm-quyết-định-bất-biến)
- [0.5 Một câu cho mỗi nhóm người đọc](#05-một-câu-cho-mỗi-nhóm-người-đọc)

**Phần I — Luận điểm**

1. [Luận điểm chiến lược](#1-luận-điểm-chiến-lược)
2. [Bộ lọc quyết định R1–R4](#2-bộ-lọc-quyết-định-r1r4)

**Phần II — Sản phẩm**

3. [Kiến trúc hệ thống 5 lớp](#3-kiến-trúc-hệ-thống-5-lớp)
4. [Đặc tả API và bề mặt công cụ](#4-đặc-tả-api-và-bề-mặt-công-cụ)
5. [An toàn và bảo mật mặc định](#5-an-toàn-và-bảo-mật-mặc-định)

**Phần III — Thương mại và thực thi**

6. [Mặt phẳng thương mại](#6-mặt-phẳng-thương-mại)
7. [AURA — triển khai dọc](#7-aura--triển-khai-dọc)
8. [Lộ trình sản phẩm](#8-lộ-trình-sản-phẩm)
9. [Ranh giới sản phẩm và ma trận đánh đổi](#9-ranh-giới-sản-phẩm-và-ma-trận-đánh-đổi)

**Phần IV — Kiểm chứng**

10. [Định vị cạnh tranh](#10-định-vị-cạnh-tranh)
11. [Ma trận rủi ro](#11-ma-trận-rủi-ro)
12. [Hệ chỉ số hiệu suất](#12-hệ-chỉ-số-hiệu-suất)

**Phụ lục**

- [A — Đặc tả hợp đồng năng lực HAL](#phụ-lục-a--đặc-tả-hợp-đồng-năng-lực-hal)
- [B — Đặc tả định dạng gate v1](#phụ-lục-b--đặc-tả-định-dạng-gate-v1)
- [C — Đặc tả định dạng `.ntrace`](#phụ-lục-c--đặc-tả-định-dạng-ntrace)
- [D — Phần cứng, model và tích hợp](#phụ-lục-d--phần-cứng-model-và-tích-hợp)
- [E — Đối chiếu "Making Startups Powerful"](#phụ-lục-e--đối-chiếu-making-startups-powerful)
- [F — Từ điển thuật ngữ](#phụ-lục-f--từ-điển-thuật-ngữ)
- [G — Giả định cần kiểm chứng](#phụ-lục-g--giả-định-cần-kiểm-chứng)

---

# Phần 0 — Tóm tắt điều hành

## 0.1 Bối cảnh

Physical AI đang ở điểm hội tụ của ba lực:

| # | Lực | Biểu hiện |
|:---:|:---|:---|
| 1 | **Phần cứng biên chạm đáy chi phí** | Vi xử lý có Wi-Fi/BLE và năng lực AI ở mức $3–15 (ESP32-S3, RP2350, RPi Zero 2W); lớp compute module ở mức $80 |
| 2 | **SLM chạy được trên thiết bị** | Model 0,5B–3B tham số phân loại ý định và trích xuất thực thể ngay trên biên, không cần mạng |
| 3 | **Chuẩn kết nối công cụ** | Model Context Protocol (MCP) thiết lập chuẩn chung nối logic model với công cụ ngoại vi |

Dù vậy, một kỹ sư muốn chế tạo thiết bị vật lý có tương tác giọng nói vẫn phải tự tích hợp sáu thư viện độc lập không tương thích: AEC/VAD, wake-word, STT/TTS, máy trạng thái hội thoại, driver phần cứng, và tầng bảo vệ an toàn. Chu kỳ điển hình: 2–4 tuần cho bản prototype, 3–6 tháng cho bản sản xuất.

## 0.2 Vấn đề cốt lõi

Mô tả khoảng trống trên là *"thiếu một voice framework"* là nhận định nông. Đó là khoảng trống mà mọi đối thủ có nhiều vốn hơn đều lấp được bằng cách viết thêm tính năng.

Khoảng trống thật nằm sâu hơn một tầng: **chưa có công cụ nào kiểm thử được hành vi vật lý trước khi nó diễn ra ngoài hiện trường.**

- Khi một chatbot phần mềm trả lời sai, người dùng đọc lại hoặc bấm tạo lại.
- Khi một agent vật lý quyết định sai, **servo đã quay, rơ-le đã đóng, chốt cửa đã mở.** Hành vi vật lý là bất khả nghịch.

```
┌────────────────────────────────────────────────────────────────────────┐
│                  NGHỊCH LÝ THỰC THI TRONG PHYSICAL AI                  │
├────────────────────────────────────────────────────────────────────────┤
│  PHẦN MỀM TRUYỀN THỐNG                                                 │
│  Code ──► Static analysis ──► Unit test ──► CI/CD ──► Tất định         │
│                                                                        │
│  PHYSICAL AI HIỆN TẠI                                                  │
│  Prompt/Code ──► Nạp firmware ──► Thử tay ngoài đời ──► Cầu trời       │
│                                                                        │
│  VỚI NEUROEDGE                                                         │
│  Agent code ──► Capability check ──► Action CI replay ──► Safe rollout │
│                 (chặn lúc build)     (bit-for-bit)       (OTA theo đợt)│
└────────────────────────────────────────────────────────────────────────┘
```

Ba câu hỏi mà hôm nay không công cụ nào trả lời được:

1. Đổi prompt xong, agent còn từ chối mở khoá cho người chưa xác thực không?
2. Đổi từ model A sang model B, có kịch bản an toàn nào hồi quy không?
3. Ba target có cho cùng một quyết định trên cùng một đầu vào không?

## 0.3 Tuyên ngôn sản phẩm

> **NeuroEdge biến mọi hành động vật lý của AI agent thành một hợp đồng có kiểu, có version, kiểm thử tự động trong CI pipeline, và thực thi nhất quán trên ba target — từ laptop của lập trình viên tới máy tính Linux công nghiệp và vi điều khiển biên $5.**

Hệ thống có ba khối cấu trúc:

| Khối | Nội dung |
|:---|:---|
| **Lõi mã nguồn mở (MIT)** | HAL hợp đồng năng lực · Action Contract Engine · Voice runtime · Ba target ngang hàng (`sim` · `linux` · `esp32s3`) · Action CI runner |
| **Mặt phẳng thương mại duy nhất** | Hosted Gateway (inference plane) + Fleet Management OS (fleet plane) |
| **Cổng thanh khoản định lượng** | Khoá mọi hoạt động thương mại hoá Marketplace và Pay cho tới khi đạt bốn ngưỡng đo được |

## 0.4 Năm quyết định bất biến

| # | Quyết định | Hệ quả kiến trúc và kinh doanh | Mục |
|:---:|:---|:---|:---:|
| **1** | **Hành động vật lý là hợp đồng có kiểu, không phải lời gọi hàm** | Mọi lệnh tới actuator đi qua một gate có version, khai báo tĩnh, phân tích được bằng máy. HAL từ chối mọi lệnh không kèm gate đã pass | §3.5, §4.4 |
| **2** | **Ba target ngang hàng** | `sim`, `linux`, `esp32s3` là ba bản hiện thực của cùng một HAL. Cùng một file agent chạy trên cả ba, không sửa một dòng | §3.2 |
| **3** | **Bán fleet, không bán token** | Bán lại inference là biên mỏng và là cuộc đua không thắng được trước model vendor. Doanh thu đến từ việc quản lý an toàn của đội thiết bị ngoài hiện trường | §6 |
| **4** | **Model là thành phần thay thế được, không phải luận điểm** | Trí tuệ nằm sau interface `SystemOne` và `SystemTwo` từ tuần đầu. Đổi model không đổi định vị sản phẩm | §3.6 |
| **5** | **Hiệu ứng mạng kích hoạt trước marketplace** | Registry chia sẻ gate miễn phí chạy trước; phần thương mại bị khoá sau cổng thanh khoản | §1.6, §8.4 |

## 0.5 Một câu cho mỗi nhóm người đọc

| Người đọc | Câu |
|:---|:---|
| **Nhà phát triển** | Viết agent trên laptop, kiểm thử hành động vật lý trong CI, deploy lên chip $5 mà không sửa một dòng |
| **Người vận hành fleet** | Biết thiết bị nào đang làm gì, sửa từ xa, cập nhật theo đợt mà không làm chết thiết bị nào |
| **Đối tác phần cứng** | Một lớp agent chạy trên board của bạn mà không khoá khách hàng vào một dòng chip |
| **Người chịu trách nhiệm an toàn** | Mỗi hành động vật lý có một điều kiện cho phép đọc được, review được, và có log chứng minh nó đã được đánh giá |

---

# Phần I — Luận điểm

## 1. Luận điểm chiến lược

### 1.1 Chạy ngược thế giới hoàn hảo của khách hàng

Nguyên lý: mọi chiến lược gia tăng quyền lực chỉ hợp lệ khi nó tạo ra kết quả tốt hơn cho khách hàng. Nguyên lý này chạy ngược được để sinh ý tưởng sản phẩm.

> *"What would the perfect world look like, from the customer's point of view? If there's a component of that world that the startup could transform itself into, it probably should."*

| # | Trong thế giới hoàn hảo | Hiện trạng hôm nay | NeuroEdge giải quyết bằng |
|:---:|:---|:---|:---|
| **1** | Viết agent, chạy thử ngay, không cần mua phần cứng | Nghẽn ở chu kỳ đặt board, câu dây, thiết lập mạch nạp | **Target `sim`** — agent hoàn chỉnh chạy trong trình duyệt sau 10 phút (§3.2) |
| **2** | Biết chắc agent không làm điều nguy hiểm **trước khi** nạp firmware | Chỉ phát hiện sau khi thiết bị đã tới tay khách hàng cuối | **Action Contract Engine** — kiểm tra hợp đồng lúc build và lúc chạy (§3.5) |
| **3** | Đổi prompt hoặc model, chạy lại toàn bộ kịch bản an toàn trong 30 giây | Thử tay vài ca trong phòng lab, hy vọng không hồi quy | **Action CI** — replay phiên thật bit-for-bit, so khớp golden (§3.7) |
| **4** | Một file agent chạy trên laptop, máy nhúng và chip $5 | Ba codebase độc lập: Python trên PC, C++ trên MCU | **Định luật tương đương target** (§3.2, §4.6) |
| **5** | Sửa thiết bị lỗi ngoài hiện trường ngay từ máy cá nhân | Kỹ sư bay tới nơi, hoặc thu hồi cả lô | **Remote trace replay** — kéo `.ntrace` về replay cục bộ (§6.2) |

Cấu phần NeuroEdge tự biến mình thành là **số 2 và số 3** — hai dòng duy nhất không đối thủ nào phục vụ được bằng cách thêm tính năng. Số 1 và số 4 là điều kiện nền tảng bắt buộc. Số 5 là nơi tạo ra doanh thu.

### 1.2 Mệnh đề trung tâm

Bốn tài sản kỹ thuật, khi ráp lại, tạo ra một hạng mục chưa tồn tại:

```
Schema gate có version            ─┐
Record phiên thật trên phần cứng  ─┤
Replay trong sim, bit-for-bit     ─┼─►  ACTION CI
Trace đầy đủ mỗi bước quyết định  ─┘    Kiểm thử hành động vật lý tự động
                                        trong CI pipeline, trên mỗi commit
```

Mệnh đề không phải *"hai bộ não"*. Một kiến trúc định tuyến giữa hai hạng model là đặc điểm của một thời điểm: khi model biên đủ rẻ và hỗ trợ constrained decoding thời gian thực, nó thoái hoá thành chi tiết triển khai. Và nó mô tả cơ chế chứ không mô tả giá trị — khách hàng không mua "bộ định tuyến giữa hai model", họ mua **"cánh tay robot không đập vào người dùng"**.

Mệnh đề là:

> **Mọi hành động vật lý đều đi qua một hợp đồng có kiểu, kiểm thử được trong CI** — đúng bất kể ai lấp vào vị trí model suy luận.

Mệnh đề này không sao chép được bằng cách thêm tính năng, vì nó đòi hỏi ba quyết định kiến trúc đồng thời ngay từ tuần đầu: **simulator là target thật, gate là artifact có version, trace là công dân hạng nhất.** Sản phẩm nào đã xuất xưởng mà thiếu ba thứ đó thì phải viết lại, không phải bổ sung.

### 1.3 Bốn vị thế thượng nguồn

> *"Upstream is almost always good, whether it's with money or user relationship or customer stage or data."*

Đây là nguyên lý tổ chức duy nhất của chiến lược sản phẩm. Bốn vị thế, loại trừ lẫn nhau, bao phủ đủ:

| # | Thượng nguồn | Chiến lược chiếm lĩnh | Ship ở |
|:---:|:---|:---|:---:|
| **1** | **Dữ liệu** | Đặt chân tại nơi vòng đời dữ liệu bắt đầu: simulator và định dạng `.ntrace`. Ai sở hữu định dạng trace sẽ sở hữu câu hỏi "agent nào đang làm gì, và có an toàn không" | Khối 1 |
| **2** | **Giai đoạn khách hàng** | Bắt đầu từ maker ở thiết bị số 1, không phải doanh nghiệp ở thiết bị số 500. Doanh thu tự mở rộng theo số thiết bị họ xuất xưởng, không cần lực bán hàng | Khối 1 |
| **3** | **Quan hệ khách hàng** | Hosted Gateway đứng giữa nhà phát triển và mọi model vendor. Đổi model, đổi prompt từ xa mà không nạp lại firmware | Khối 2 |
| **4** | **Dòng tiền** | Toàn bộ chi phí inference, OTA và telemetry chảy qua một endpoint, một credential, một hoá đơn | Khối 2 |

**Vị thế thứ nhất bị đánh giá thấp nhất.** Rippling không trở thành công ty tỉ đô nhờ phần mềm onboarding; họ làm phần mềm onboarding tốt hơn mức cần thiết rất nhiều vì đó là nơi **vòng đời dữ liệu nhân sự bắt đầu**. Với agent vật lý, nơi vòng đời dữ liệu bắt đầu là **lần đầu tiên một hành động được đề xuất trong simulator**.

Hệ quả thiết kế: **simulator và định dạng trace phải tốt hơn mức cần thiết rất nhiều.** Không phải vì simulator là thị trường, mà vì mọi quyết định của mọi agent trên mọi thiết bị đều đi qua đó trước tiên.

### 1.4 Đánh từ bên sườn

> *"You'd have to do it by coming in from the side — by somehow making them irrelevant, rather than by frontal attack. Then you wouldn't depend on beating them to succeed; it would be an ancillary benefit of winning in another dimension."*

Các nhà sản xuất silicon phát hành SDK miễn phí vĩnh viễn với một động cơ duy nhất: **bán chip**. Đối đầu trực diện ở tầng driver một-chip là mặt trận thua từ đầu.

**Chiều không gian khác: tính kiểm thử được của hành động, cắt ngang mọi loại phần cứng.**

Một SDK chính hãng về cấu trúc không thể đi vào chiều này, vì nó đòi hỏi coi chip của hãng chỉ là một trong nhiều target ngang hàng. Không hãng chip nào làm điều đó.

Đây là lý do `linux` phải ở hạng nhất ngay từ đầu chứ không phải "sau tháng 12": **target thứ hai chạy thật chính là bằng chứng rằng chiều này tồn tại.** Không có nó, sản phẩm chỉ là một framework một-board, đánh trực diện SDK chính hãng ngay trên sân của họ.

### 1.5 Mã nguồn mở là kênh phân phối, định dạng là chuẩn mực

> *"If you're one of the first in the field... everyone is so hungry for standards that the first to be proposed tends to win, no matter who proposed it."*

Mã nguồn mở chỉ hoạt động như kênh phân phối khi **người pull repo về chính là người ra quyết định kiến trúc**. Bốn thuộc tính cần có đồng thời:

| Thuộc tính | Biểu hiện ở NeuroEdge |
|:---|:---|
| Đúng tầng | Hạ tầng, không phải ứng dụng nghiệp vụ |
| Lĩnh vực chưa có chuẩn | Physical AI chưa có chuẩn mô tả "hành động này an toàn khi nào" |
| Demo lan truyền được | Video nói chuyện với con chip và servo quay |
| Người cài = người quyết định | Nhà phát triển quyết trong vài phút, không qua chu trình mua sắm |

**Chuẩn mà NeuroEdge đề xuất không phải framework, mà là định dạng gate và `.ntrace`.** Framework thì ai cũng viết được cái khác. Định dạng mà cả lĩnh vực dùng để mô tả sự an toàn thì chỉ có một cái thắng — và nền tảng sở hữu công cụ CI cùng hạ tầng fleet quản lý định dạng đó thắng theo.

**Hào phóng có tính toán:** lõi MIT mở toàn bộ HAL, Action Contract Engine, voice pipeline và Action CI. Sự hào phóng loại bỏ ma sát dùng thử ở nhóm khách hàng bảo thủ nhất — kỹ sư nhúng.

### 1.6 Vòng lặp giá trị và hiệu ứng mạng trước marketplace

```
Chạy agent trong simulator sau 10 phút, không cần mua phần cứng
                              │
                              ▼
Viết gate đầu tiên — agent tự động từ chối hành vi nguy hiểm
                              │
                              ▼
Ghi phiên thật trên board (.ntrace), replay trong CI mỗi commit
                              │
                              ▼
Triển khai 10 ➔ 100 ➔ 1.000 thiết bị, OTA theo đợt, không brick
                              │
                              ▼
Trả tiền cho Fleet Management OS — không phải trả tiền cho token
                              │
                              ▼
Chia sẻ gate đã tune lên Public Registry (kế thừa qua `extends`)
                              │
                              ▼
Dữ liệu dùng lại gate chỉ điểm chính xác thành phần nào có giá trị thương mại
```

Hai mắt xích quyết định:

1. **Bước 2 và 3** là nơi sản phẩm tạo ra giá trị mà không ai thay thế được.
2. **Bước 6 là hiệu ứng mạng khả dụng *trước* marketplace.** Bản cao cấp của hiệu ứng mạng là app store, nhưng khi chưa có cách trực tiếp, *"you can often induce network effects by letting your users share something"*. Gate là tài sản chia sẻ lý tưởng: file cấu hình nhẹ, miễn phí, không mở bề mặt pháp lý, và làm hệ sinh thái an toàn hơn cho cả người đóng góp lẫn người dùng lại.

### 1.7 Kinh tế học của khách hàng

> *"Few things make you more powerful than that... they're (a) quick to adopt your product and (b) will pay a lot for it."*

Tổng chi phí sở hữu (TCO) cho một đội phát triển vận hành **500 thiết bị trong 1 năm**:

| Hạng mục chi phí | Tự xây dựng | SDK chính hãng | Cloud agent stack | **NeuroEdge** |
|:---|:---:|:---:|:---:|:---:|
| **Nhân sự kỹ thuật chuyên trách** | 3 kỹ sư — $180k<br>*(firmware + audio + AI)* | 2 kỹ sư — $120k<br>*(chuyên sâu 1 dòng chip)* | 1,5 kỹ sư — $90k<br>*(WebRTC/cloud)* | **0,5 kỹ sư — $30k**<br>*(tập trung logic nghiệp vụ)* |
| **Bring-up bo mạch thứ hai** | 12 tuần | 8 tuần | Không hỗ trợ MCU | **1 tuần** *(đổi cờ `--target`)* |
| **Sửa lỗi hiện trường** | ~$30k<br>*(cử kỹ sư tới nơi)* | ~$15k<br>*(log thủ công qua UART)* | ~$10k<br>*(phụ thuộc mạng)* | **~$0**<br>*(kéo `.ntrace` về replay)* |
| **Chi phí nền tảng** | $0 | $0 | ~$8k | **$6k** *($1/thiết bị/tháng)* |
| **Rủi ro thu hồi lô hàng** | Cao — không có CI cho hành vi vật lý | Cao — không có CI cho hành vi vật lý | Trung bình — không có fail-closed | **Thấp** — mọi lỗi *quyết định được* bị chặn từ commit |
| **TỔNG NĂM ĐẦU** | **~$250k** | **~$160k** | **~$120k** | **~$36k** |

**Giả định của bảng TCO:**

| Tham số | Giá trị |
|:---|:---|
| Quy mô | 500 thiết bị, 1 dòng board, 1 ngôn ngữ, 12 tháng |
| Chi phí nhân sự | $60k/kỹ sư/năm, đã gồm chi phí gián tiếp |
| Chi phí nền tảng NeuroEdge | Fleet $1/thiết bị/tháng + inference bán sát giá vốn |
| Chi phí on-site | $500/chuyến; số chuyến ước lượng theo khả năng chẩn đoán từ xa |
| Không tính | BOM phần cứng (giống nhau ở cả bốn cột) |

**Phạm vi của dòng "rủi ro thu hồi".** Action CI chặn được mọi lỗi *quyết định được*: gate sai điều kiện, prompt gây hồi quy an toàn, lệch quyết định giữa các target. Nó **không** thay thế kiểm thử trên phần cứng thật cho lỗi âm học trong phòng vang, beamforming mic array, và áp lực bộ nhớ trên MCU — ba nhóm này bắt bằng kiểm thử nightly trên board thật (§3.2). Tuyên bố đúng là "giảm mạnh, có giới hạn nêu rõ", không phải "triệt tiêu".

---

## 2. Bộ lọc quyết định R1–R4

Bốn quy tắc, loại trừ lẫn nhau và bao phủ đủ. Áp dụng cho mọi đề xuất tính năng.

| # | Quy tắc | Câu hỏi kiểm tra |
|:---:|:---|:---|
| **R1** | **Phục vụ time-to-first-value** | Có rút ngắn đường từ `pip install` đến phản hồi đầu tiên không? |
| **R2** | **Không thể bổ sung sau** | Nếu bỏ qua bây giờ, 12 tháng nữa có retrofit được không, hay phải viết lại? |
| **R3** | **Có nhu cầu thật đang chờ** | Đã có người yêu cầu, hay chỉ là suy diễn về nhu cầu tương lai? |
| **R4** | **Không mở bề mặt pháp lý** | Có phát sinh giấy phép tài chính, lưu giữ tiền, KYC, hoặc trách nhiệm pháp lý mới? |

**Thứ tự áp dụng:** R4 đúng → **bác bỏ tuyệt đối**. R1 hoặc R2 đúng → **làm ngay**. R3 sai → **hoãn**.

| Đề xuất | Phán quyết |
|:---|:---|
| Gate là artifact có version, không phải code | R2 đúng — đổi sau là đổi kiến trúc → **làm ngay** |
| Metering theo lượt gọi agent và lượt đánh giá gate | R2 đúng → **làm ngay** dù chưa ai yêu cầu |
| `linux` là target hạng nhất | R1 và R2 đều đúng → **làm ngay** |
| Dashboard BI tuỳ biến | R1 sai, R3 sai → **hoãn vô thời hạn** |
| Agent-to-agent pay | R4 đúng → **chặn tới sau cổng thanh khoản** |

---

# Phần II — Sản phẩm

## 3. Kiến trúc hệ thống 5 lớp

### 3.1 Sơ đồ khối tổng thể và trục Action CI

```
┌────────────────────────────────────────────────────────────────────────┐
│  L4: AGENT LAYER                                                       │
│      Conversation state machine · Context memory · MCP tool dispatcher │
├────────────────────────────────────────────────────────────────────────┤
│  L3: ACTION CONTRACT ENGINE                        ← IP cốt lõi        │
│      Typed gate verifier · Policy inheritance · Fail-closed circuit    │
├────────────────────────────────────────────────────────────────────────┤
│  L2: PERCEPTION & RUNTIME                                              │
│      Wake-word · Neural VAD · AEC · STT/TTS độ trễ thấp                │
├────────────────────────────────────────────────────────────────────────┤
│  L1: HARDWARE ABSTRACTION LAYER — HỢP ĐỒNG NĂNG LỰC                    │
│      5 nguyên thủy bất biến · đối chiếu tương thích lúc build          │
├────────────────────────────────────────────────────────────────────────┤
│  L0: TARGET IMPLEMENTATIONS — ba đối tác ngang hàng                    │
│      [ sim ]              [ linux ]              [ esp32s3 ]           │
└────────────────────────────────────────────────────────────────────────┘
         ▲
         └── TRỤC XUYÊN SUỐT: ACTION CI
             Record (.ntrace) ──► Bit-for-bit replay ──► Assert hành động
```

Năm tầng trên thuộc bản phân phối mã nguồn mở MIT. Toàn bộ hạ tầng đám mây (Gateway, Fleet Console) nằm **ngoài** sơ đồ và giao tiếp qua interface cắm rút được. Một agent NeuroEdge chạy trọn vẹn khi không có mạng và không có tài khoản.

### 3.2 L0 — Định luật tương đương target

> **Định luật:** ba target là ba bản hiện thực ngang hàng của cùng một chuẩn HAL. Cùng một file agent phải cho ra cùng một chuỗi quyết định trên cả ba, không sửa một dòng mã.

| Tiêu chí | `sim` | `linux` | `esp32s3` |
|:---|:---|:---|:---|
| **Đẳng cấp kiến trúc** | Hạng nhất | Hạng nhất | Hạng nhất |
| **Môi trường vận hành** | Vòng lặp dev, Action CI | Máy công nghiệp, RPi, x86 | Vi điều khiển biên $5 |
| **Tần suất kiểm thử** | Mọi pull request | Mọi pull request | Nightly trên board thật |
| **Phần cứng** | Cảm biến ảo, actuator mô phỏng | Phần cứng thật qua `gpiod` | Thanh ghi và GPIO thật |
| **Giới hạn môi trường** | Không đo được áp lực bộ nhớ, AEC phòng vang, beamforming | Tài nguyên dư dả | SRAM/PSRAM rất hạn chế |

#### Năm lý do `linux` phải là target hạng nhất ngay từ Khối 1

| # | Lý do | Quy tắc |
|:---:|:---|:---:|
| 1 | **Bằng chứng của hợp đồng năng lực.** Một HAL chỉ có một target thật là một API phụ thuộc phần cứng, không phải một hợp đồng trừu tượng | R2 |
| 2 | **Chiều đánh sườn.** SDK của nhà sản xuất silicon không bao giờ coi Linux là đối tác ngang hàng với dòng chip của họ | R2 |
| 3 | **Chi phí biên cận 0.** Linux đã là môi trường dev và CI; phần lớn đường dẫn thực thi của `sim` dùng lại nguyên vẹn | R1 |
| 4 | **Nhu cầu thật đang chờ.** Phần lớn dự án Physical AI thương mại hiện chạy trên compute module ARM, không phải MCU đơn lẻ | R3 |
| 5 | **Đường thoát khi chip biên quá tải.** Nếu logic vượt dung lượng ESP32-S3, hệ thống dịch sang Linux mà không viết lại | R2 |

**Ba target, không bốn.** Ba là số nhỏ nhất chứng minh được định luật tương đương: một ảo, một rộng, một chật. Jetson, Matter, HomeKit nằm ngoài phạm vi (§9).

### 3.3 L1 — HAL: hợp đồng năng lực

HAL của NeuroEdge không phải mẫu số chung nhỏ nhất giữa các loại phần cứng. Nó là **hợp đồng hai chiều**: thiết bị khai báo năng lực cung cấp, agent khai báo yêu cầu sử dụng, và mọi lệch pha bị chặn **tại thời điểm build**.

Hệ thống rút gọn thành đúng năm nguyên thủy bất biến:

| Nguyên thủy | Vai trò | Hiện thực điển hình |
|:---|:---|:---|
| `audio.in` | Luồng PCM đầu vào, sample rate, trạng thái AEC | Mic array I2S · USB mic · file WAV trong sim |
| `audio.out` | Luồng âm thanh tới loa hoặc bộ khuếch đại | I2S DAC · ALSA · thiết bị null |
| `digital.out` | Trạng thái chân logic: GPIO, PWM, relay, solenoid | Chốt cửa · đèn · motor |
| `sensor.read` | Đọc cảm biến định kỳ hoặc theo ngắt | I2C/SPI · giá trị kịch bản trong sim |
| `display` | Frame buffer màn hình, đèn báo trạng thái | SPI LCD · HDMI · khung ảo trong trình duyệt |

Đặc tả đầy đủ thuộc tính thương lượng và quy tắc đối chiếu: **Phụ lục A**.

### 3.4 L2 — Perception và runtime hội thoại

**Triết lý:** bọc lại các thư viện mã nguồn mở tốt nhất (Sherpa-ONNX, Silero VAD, WebRTC AEC, Opus), không tự viết lại thuật toán xử lý tín hiệu cơ bản.

Giá trị độc quyền nằm ở **máy trạng thái hội thoại thời gian thực**, xử lý bốn ca biên mà mọi triển khai đều làm sai:

| Ca biên | Yêu cầu kỹ thuật |
|:---|:---|
| **Barge-in** | Ngắt luồng TTS tức thì và thu hồi lệnh actuator chưa thực thi khi người dùng cất tiếng |
| **Khoảng lặng động** | Phân biệt tạm dừng để suy nghĩ với kết thúc lượt nói; ngưỡng cố định thì hoặc cắt lời người nói chậm, hoặc chờ quá lâu |
| **Partial streaming** | Phát âm thanh từ những token đầu tiên, nhưng rút lại được khi model đổi kết luận |
| **Tự phục hồi lỗi STT** | Chuỗi rỗng hoặc nhiễu không được làm treo máy trạng thái, không được hỏi lại vô hạn |

Bốn ca này là lý do máy trạng thái hội thoại tốn ba tuần để làm đúng, và là lý do nó nằm trong lõi thay vì để mỗi đội tự ghép lại một lần nữa.

### 3.5 L3 — Action Contract Engine và cơ chế fail-closed

Đây là tài sản kỹ thuật cốt lõi. Bốn trách nhiệm loại trừ lẫn nhau:

| # | Trách nhiệm | Nội dung |
|:---:|:---|:---|
| 1 | **Thi hành hợp đồng** | Mọi lệnh tới actuator đi qua gate tương ứng. HAL từ chối mọi yêu cầu không mang chữ ký gate đã pass |
| 2 | **Định tuyến model** | Chính sách khai báo được: ý định đơn giản xuống System 1; ngưỡng confidence thấp leo lên System 2 |
| 3 | **Mạch ngắt suy giảm** | Mất mạng, timeout, hoặc model trả dữ liệu không hợp lệ → **chặn hành động**. Mặc định của mọi gate là `fail: closed` |
| 4 | **Phát trace** | Mỗi lượt sinh một `.ntrace` hoàn chỉnh: độ trễ và chi phí từng chặng, mọi đánh giá gate, mọi lệnh actuator |

#### Vì sao gate là artifact chứ không phải code

Nếu gate là hàm Python, nó không chia sẻ được, không version được, không review được bởi người không đọc code, và không bán được. Khi gate là file có schema, có version, có `extends`, nó đồng thời là:

| Vai trò | Ở đâu |
|:---|:---|
| Đơn vị kiểm thử | Action CI (§4.7) |
| Đơn vị chia sẻ → hiệu ứng mạng trước marketplace | §1.6 |
| Đơn vị review an toàn cho người không phải kỹ sư | Khách hàng doanh nghiệp |
| Ứng viên hàng hoá của marketplace | §8.7 |

Một quyết định định dạng, bốn lợi ích. Gần như miễn phí ở tuần 1, gần như không thể retrofit ở tháng 12.

### 3.6 Trừu tượng hoá model

Model AI là thành phần hoán đổi được. Luận điểm sản phẩm không phụ thuộc vào bất kỳ nhà cung cấp nào.

| Interface | Vai trò | Ứng viên |
|:---|:---|:---|
| `SystemOne` | Quyết định có cấu trúc, phản hồi dưới 100 ms | Jev · model intent chưng cất chạy cục bộ · SLM on-device |
| `SystemTwo` | Suy luận mở, hội thoại phức tạp | Claude Sonnet 5 · Qwen 2.5 · Llama 3.2 |

Cả hai interface **bắt buộc** có đường dẫn dự phòng khai báo được trong cấu hình.

#### Hợp đồng tối thiểu của một nhà cung cấp `SystemOne`

Ba nguyên thủy. Bất kỳ ai hiện thực được ba nguyên thủy này đều cắm vào được — đây là ranh giới thay thế được, và nó nằm ở đúng một chỗ.

| Nguyên thủy | Trả về | Dùng trong gate |
|:---|:---|:---|
| `bool` | Xác suất mệnh đề đúng, kèm confidence | `guest_authenticated: true` |
| `level` | Điểm trên thang có thứ tự, kèm phân phối | `risk: { lte: low }` |
| `choice` | Lựa chọn trong tập khai báo, kèm xác suất từng nhánh | Định tuyến intent |

#### Quản trị rủi ro nhà cung cấp

| | |
|:---|:---|
| **Rủi ro** | Nếu luận điểm dựa vào một model đóng, nhà cung cấp đó nắm số phận sản phẩm |
| **Chi phí phòng ngừa** | Interface: một ngày. Fallback cục bộ đã tinh chỉnh: vài tuần |
| **Quyết định** | Ship interface ở tuần 1 (R2). Đầu tư tune fallback cục bộ khi chỉ báo sớm ở §11 bật |
| **Giảm thiểu cấu trúc** | Sản phẩm là hợp đồng hành động; model chỉ điền vào ô đánh giá của gate. Đổi model không đổi định vị |

### 3.7 Trục Action CI và định dạng `.ntrace`

**Nguyên tắc thiết kế quan trọng nhất: simulator là một target chính thức, không phải mock.** Nếu sim là một đường code riêng, nó lệch khỏi phần cứng trong khoảng sáu tuần và trở thành đồ chơi. Sim thực thi đúng hợp đồng HAL đó, chạy đúng agent code đó.

#### Cấu trúc khối dữ liệu `.ntrace`

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
          "risk_level": "low"
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

Đặc tả đầy đủ nhóm sự kiện và thuộc tính bắt buộc: **Phụ lục C**.

#### Bốn thành phần hợp nhất của Action CI

| Thành phần | Nội dung |
|:---|:---|
| **Record** | Trích xuất toàn bộ luồng sự kiện của một phiên thật ra tệp `.ntrace` |
| **Replay** | Tái hiện chính xác chuỗi sự kiện đó trên bất kỳ target nào |
| **Assert** | Thư viện khẳng định về hành động: bị chặn, chặn bởi gate nào, leo thang tới đâu, chân nào tuyệt đối không được kích |
| **Golden** | Khoá chuỗi quyết định tham chiếu. Đổi prompt hoặc model làm lệch golden → CI đỏ |

#### Giới hạn phải nêu rõ trong tài liệu kỹ thuật

Sim **không** mô phỏng AEC trong phòng vang, beamforming mic array, wifi chập chờn, và áp lực bộ nhớ trên MCU. Đổi lại, `--target esp32s3` cách đúng một lệnh, và mọi thứ *quyết định được* đều kiểm thử được trên mỗi commit.

---

## 4. Đặc tả API và bề mặt công cụ

Với một framework, API surface chính là sản phẩm. Mục này định nghĩa nó.

### 4.1 Năm nguyên tắc thiết kế API

| # | Nguyên tắc | Hệ quả |
|:---:|:---|:---|
| 1 | **Năng lực là khai báo tĩnh** | Board và agent cùng khai báo qua TOML; công cụ đối chiếu lúc build |
| 2 | **Hành động vật lý không gọi trực tiếp được** | Chỉ tới actuator qua `c.do()`, luôn đi qua gate |
| 3 | **Gate là dữ liệu có cấu trúc** | YAML có schema, version độc lập với mã nguồn logic |
| 4 | **Một mã nguồn cho mọi nền tảng** | Target là cờ dòng lệnh, không phải nhánh code |
| 5 | **Mặc định fail-closed** | Bất kỳ lỗi nào khi đánh giá gate đều dẫn tới chặn hành động |

### 4.2 Đặc tả phần cứng — `board.toml`

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

Cùng một bo mạch định nghĩa cho môi trường công nghiệp `linux` khác đúng hai dòng:

```toml
# boards/villa-gateway.board.toml
[board]
id     = "villa-gateway-x86"
target = "linux"          # ← khác ở đây

[capabilities."digital.out"]
pins    = ["door_lock", "courtesy_lamp"]
backend = "gpiod"         # ← và ở đây
# Toàn bộ phần còn lại hoàn toàn đồng nhất
```

### 4.3 Đặc tả yêu cầu agent — `agent.toml`

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
order_food  = "./gates/order_food@0.1.0.yaml"

[targets]
supported = ["sim", "linux", "esp32s3"]
```

Dòng `neuroedge://` là toàn bộ luận điểm hiệu ứng mạng trong một dòng: gate của người khác, có version, kéo về bằng tên.

### 4.4 Hành động có kiểu và xử lý ngoại lệ — `@action`

```python
# actions/unlock_door.py
from neuroedge import action
from neuroedge.hal import digital

@action(
    name     = "unlock_door",
    requires = "digital.out:door_lock",
    gate     = "unlock_door",
)
def unlock_door(guest_id: str, duration_s: int = 30) -> None:
    """Mở chốt cửa phòng cho khách đã được xác thực."""
    digital.out("door_lock").pulse(seconds=duration_s)
```

Ba ràng buộc mà decorator `@action` áp đặt:

| # | Ràng buộc | Vi phạm dẫn tới |
|:---:|:---|:---|
| 1 | Hàm không gọi trực tiếp được từ code agent — chỉ qua `c.do()` | `ActionContractViolation` lúc chạy |
| 2 | `requires` tham gia đối chiếu năng lực lúc build | Build dừng, không nạp firmware (§4.9) |
| 3 | `gate` phải trỏ tới một gate đã khai báo trong `agent.toml` | Build dừng |

Bộ ngoại lệ an toàn:

| Ngoại lệ | Khi nào |
|:---|:---|
| `ActionContractViolation` | Gọi hành động vật lý không qua `c.do()` |
| `GateFailClosedException` | Gate không đánh giá được trong ngân sách và `fail: closed` |
| `CapabilityMismatchError` | Agent yêu cầu năng lực board không khai báo |
| `TargetEquivalenceError` | `neuroedge verify` phát hiện lệch quyết định giữa các target |

### 4.5 Gate artifact — schema và `extends`

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
    instructions: "Mức độ rủi ro bất thường tại thời điểm yêu cầu"

allow_when:
  guest_authenticated: true
  room_matches:        true
  risk_level:          { lte: low }

on_block:
  action:  escalate
  to:      human_receptionist
  message: "Yêu cầu cần nhân viên lễ tân xác thực trực tiếp trước khi mở khoá."

budget:
  p95_latency_ms: 120
  fail:           closed      # Mất mạng hoặc timeout → CHẶN HÀNH ĐỘNG
```

Năm thuộc tính mà định dạng này mở ra và code Python không mở ra:

| Thuộc tính | Vì sao quan trọng |
|:---|:---|
| `version` + `extends` | Kế thừa chuẩn an toàn của ngành, ghi đè phần riêng |
| `evaluate` tách khỏi `allow_when` | Đổi model không đổi chính sách; đổi chính sách không đụng code |
| `budget.fail: closed` | Hành vi khi mất mạng là một dòng khai báo, không phải một nhánh `try/except` bị quên |
| Đọc được bởi người không phải kỹ sư | Quản lý vận hành review được điều kiện mở khoá |
| Là file | Diff được, review trong PR, publish lên registry |

Đặc tả đầy đủ trường, toán tử và **quy tắc kế thừa**: **Phụ lục B**.

### 4.6 Mã nguồn agent hoàn chỉnh

```python
# agent.py
from neuroedge import Agent, Conversation, SystemOne, SystemTwo
from actions.unlock_door import unlock_door
from actions.order_food import order_food

agent = Agent.from_toml("agent.toml")

agent.mind(
    fast  = SystemOne("jev-latest",     fallback="local/intent-distil-8m"),
    slow  = SystemTwo("claude-sonnet-5", fallback="local/qwen2.5-3b"),
    route = "fast_first",
)

agent.memory.ingest("./villa_docs/")


@agent.on_turn
async def turn(c: Conversation):
    intent = await c.fast.choice(
        "intent",
        options = ["faq", "unlock", "order", "other"],
        state   = {"utterance": c.utterance, "context": c.recall(k=3)},
    )

    if intent.top == "unlock":
        # Gate unlock_door@1.2.0 chạy TRƯỚC khi chân door_lock nhận lệnh.
        # Bị chặn → leo thang theo on_block, hàm không bao giờ chạy.
        await c.do(unlock_door, guest_id=c.session.guest_id)

    elif intent.top == "order":
        await c.do(order_food, dish=await c.slow.extract("dish_name"))

    elif intent.top == "faq" and intent.confidence > 0.85:
        await c.say(c.recall_answer())          # không tốn chi phí System 2

    else:
        await c.say(await c.slow.reply())
```

Đây là toàn bộ agent. Ba quan sát:

- Không có `if target == ...` ở bất kỳ đâu. Cùng file này chạy trên `sim`, `linux`, `esp32s3`.
- `c.do()` là cổng duy nhất tới thế giới vật lý. Không có đường vòng.
- `c.say()` và `c.do()` tách biệt về kiểu: nói là rẻ và hoàn tác được, làm thì không.

### 4.7 Bộ kiểm thử hồi quy Action CI

```python
# tests/test_gates.py
from neuroedge.testing import replay, scenario


def test_khong_mo_khoa_khi_chua_xac_thuc():
    """Khách chưa xác thực tuyệt đối không kích hoạt chốt cửa."""
    s = replay("traces/unverified_attempt.ntrace")
    assert s.action("unlock_door").blocked
    assert s.blocked_by   == "unlock_door@1.2.0"
    assert s.escalated_to == "human_receptionist"
    assert s.pin("door_lock").never_pulsed()


def test_gate_fail_closed_khi_mat_mang():
    """Mất kết nối không được biến thành cho phép."""
    s = scenario("traces/happy-path.ntrace", network="offline")
    assert s.action("unlock_door").blocked
    assert s.reason == "gate_unreachable"


def test_doi_model_khong_lam_hoi_quy_an_toan():
    """Thay System 1 bằng model cục bộ không được đổi chuỗi quyết định."""
    s = replay("traces/happy-path.ntrace", fast="local/intent-distil-8m")
    assert s.decisions == s.golden("traces/happy-path.golden")


@scenario.parametrize(target=["sim", "linux", "esp32s3"])
def test_ba_target_cho_cung_mot_quyet_dinh(target):
    """Định luật tương đương target, ở dạng khẳng định chạy được."""
    s = replay("traces/happy-path.ntrace", target=target)
    assert s.decisions == s.golden("traces/happy-path.golden")
```

Test cuối là định luật §3.2 ở dạng khẳng định chạy được. Nó không phải một lời hứa trong tài liệu; nó là một dòng CI đỏ khi bị vi phạm.

### 4.8 Bề mặt CLI

```bash
# Khởi tạo dự án
neuroedge new villa-concierge        # scaffold: agent.toml, 1 action, 1 gate, 1 test

# Vòng lặp phát triển
neuroedge run   --target sim         # mở UI trình duyệt, mic laptop, servo ảo
neuroedge run   --target linux       # chạy thật trên RPi / x86
neuroedge build --target esp32s3 --board villa-panel

# Kiểm thử tự động
neuroedge test                               # Action CI trên sim + linux
neuroedge verify --targets sim,linux,esp32s3 # kiểm tra tương đương target

# Hiện trường ↔ máy dev
neuroedge record --target esp32s3 --out traces/
neuroedge replay traces/incident.ntrace --target sim

# Hệ sinh thái gate
neuroedge gate publish gates/unlock_door@1.2.0.yaml
neuroedge gate add     neuroedge://gates/robotics/arm-collision@2.0.0
```

Hai lệnh `record` / `replay` là cầu nối giữa hiện trường và máy dev: một thiết bị lỗi ở villa khách hàng trở thành một test case trên laptop trong một lệnh.

### 4.9 Báo cáo vi phạm hợp đồng lúc build

```
$ neuroedge build --target esp32s3 --board villa-panel

✗ CAPABILITY MISMATCH — dừng build, không nạp firmware

  agent  villa-concierge@0.3.1   yêu cầu   sensor.read:motion
  board  villa-panel-v2          cung cấp  audio.in, audio.out, display,
                                           digital.out:[door_lock, courtesy_lamp]

  thiếu  sensor.read:motion      dùng tại  actions/auto_light.py:14

  → Thêm cảm biến vào board.toml, hoặc bỏ yêu cầu khỏi agent.toml.

  Lỗi này trước đây chỉ lộ ra khi thiết bị đã nằm ngoài hiện trường.
```

Dòng cuối là toàn bộ luận điểm của §3.3 trong một câu, và nó nằm trong terminal của người dùng chứ không nằm trong tài liệu này.

### 4.10 Chặng đường mười phút đầu tiên

| Phút | Người dùng làm gì | Sản phẩm trả lại gì |
|:---:|:---|:---|
| 0–1 | `pip install neuroedge` | Không cần tài khoản, không cần API key |
| 1–2 | `neuroedge new my-agent` | Scaffold có sẵn 1 action, 1 gate, 1 test chạy được |
| 2–4 | `neuroedge run --target sim` | UI trình duyệt: nói vào mic laptop, thấy servo ảo quay |
| 4–6 | Sửa `allow_when` trong gate | Agent từ chối hành động, hiển thị ngay lý do trong trace |
| 6–8 | `neuroedge test` | CI xanh; phá một điều kiện → CI đỏ kèm tên gate cụ thể |
| 8–10 | `neuroedge run --target linux` | Cùng file agent, chạy trên phần cứng thật |

**Ràng buộc thiết kế:** không bước nào trong mười phút này yêu cầu mua phần cứng, tạo tài khoản, hay nhập thẻ.

---

## 5. An toàn và bảo mật mặc định

Năm lớp, loại trừ lẫn nhau. Tất cả là mặc định, không phải tuỳ chọn cấu hình.

| Lớp | Thành phần | Nội dung |
|:---|:---|:---|
| **Hành động** | Action Contract | Không có đường tới actuator ngoài gate · mặc định `fail: closed` · mọi đánh giá gate đi vào trace |
| **Thiết bị** | Firmware và phần cứng | Secure boot và flash encryption trên ESP32-S3 · công tắc tắt mic vật lý trên board tham chiếu · TPM khi nền tảng có |
| **Mạng** | Truyền dẫn | TLS 1.3 toàn tuyến · mTLS thiết bị ↔ cloud · certificate pinning · chứng chỉ riêng từng thiết bị |
| **Dữ liệu** | Quyền riêng tư | Audio xử lý theo luồng, không lưu mặc định · xử lý cục bộ khi năng lực thiết bị cho phép · trace ghi quyết định, không ghi nội dung thô trừ khi bật tường minh |
| **Cập nhật** | OTA | Firmware ký số · rollout theo đợt · tự rollback khi tỉ lệ lỗi hoặc vòng lặp reboot vượt ngưỡng |

**Nguyên tắc bao trùm:** an toàn là một artifact đọc được, không phải một lời hứa. Với mỗi hành động vật lý luôn tồn tại một file trả lời được câu hỏi "cái này được phép khi nào", và một trace chứng minh nó đã được đánh giá.

---

# Phần III — Thương mại và thực thi

## 6. Mặt phẳng thương mại

Một mặt phẳng duy nhất, hai nhóm năng lực, một nguyên tắc phân định biên lợi nhuận: **inference là phễu, fleet là nơi có giá trị gia tăng.**

> Bán quá rẻ thì mất tín hiệu mà khách hàng gửi bằng việc trả tiền. Vì vậy inference đặt **sát giá vốn (cost-plus 5–10%)**, không miễn phí — con số phải đủ để việc ai trả và ai không trả vẫn nói lên điều gì đó.

### 6.1 Inference plane — sáu năng lực

| # | Năng lực | Vì sao khách hàng trả tiền |
|:---:|:---|:---|
| 1 | Một endpoint, một credential | Thiết bị không giữ key bên thứ ba; xoay key không cần nạp lại firmware |
| 2 | Routing đa nhà cung cấp và failover | Thiết bị không bao giờ thấy sự cố của một nhà cung cấp |
| 3 | Giao thức hợp với edge | WebSocket giữ liên tục, khung audio nhị phân, partial theo luồng |
| 4 | Hạn mức cứng theo thiết bị | Một thiết bị lỗi lặp vòng không đốt sạch hoá đơn |
| 5 | Cache ngữ nghĩa và đếm tỉ lệ System 1/System 2 | Vừa là nguồn biên, vừa là bằng chứng định lượng cho luận điểm định tuyến |
| 6 | Một `.ntrace` cho mỗi lượt | Cùng định dạng dùng trong Action CI — hiện trường và CI nói chung một ngôn ngữ |

Năng lực 3 là rào cản kỹ thuật thật: thiết bị biên không kham nổi bắt tay TLS cho từng request HTTP. Hiện chưa có nhà cung cấp nào terminate audio stream cho lớp phần cứng này.

Năng lực 6 là chỗ mặt phẳng thương mại khoá vào lõi mở mã: trace sinh ra trên gateway replay được trên laptop, không cần chuyển đổi định dạng.

### 6.2 Fleet plane — năm năng lực

| # | Năng lực | Vì sao khách hàng trả tiền |
|:---:|:---|:---|
| 1 | Định danh và provisioning | Chứng chỉ mật mã riêng từng thiết bị, luồng claim ở lần boot đầu |
| 2 | OTA rollout theo đợt, tự rollback | Lý do số một khiến đội phần cứng trả tiền cho một nền tảng |
| 3 | Sổ kiểm kê và sức khoẻ fleet | Online/offline, phiên bản firmware, RSSI, nhiệt độ chip, vòng lặp reboot |
| 4 | Cập nhật config, secret và **gate** từ xa | Đổi wake-word, prompt, ngưỡng gate trên toàn fleet mà không nạp lại firmware |
| 5 | Log và trace từ xa cho một thiết bị | Tự đẩy `.ntrace` khi có sự cố; kỹ sư replay trên máy cá nhân |

**Liên tục với lõi mở mã:** thiết bị ảo trong simulator hiện lên trong fleet console ngay lập tức. Đường từ `pip install` đến "tôi đang nhìn thiết bị của mình trên dashboard" phải liền một mạch — **fleet console phải hữu ích ở n = 1**, không phải ở n = 100. Đây là thành phần duy nhất đưa người dùng từ 1 thiết bị lên 100; không có nó, vòng lặp §1.6 đứt ở giữa.

### 6.3 Cấu trúc doanh thu và ngưỡng quy mô

| Dòng | Cơ chế | Vai trò |
|:---|:---|:---|
| **Inference** | Cost-plus 5–10% trên lượt gọi model | Phễu onboarding, không phải nguồn biên |
| **Fleet** | $1 / thiết bị hoạt động / tháng | Nguồn biên chính |
| **Fleet bậc vận hành** | Phụ phí cho SLA cam kết, nhật ký kiểm toán gate, lưu trữ trace dài hạn | Đòn bẩy biên ở khách hàng lớn |

Doanh thu fleet theo quy mô, ở mức giá cơ sở $1:

| Thiết bị hoạt động | Doanh thu fleet / năm |
|:---:|:---:|
| 1.000 | $12.000 |
| 10.000 *(ngưỡng G1 của cổng thanh khoản)* | $120.000 |
| 50.000 | $600.000 |
| 250.000 | $3.000.000 |

**Đọc bảng này một cách thẳng thắn:** ở mức giá cơ sở, fleet plane chỉ tự nuôi được tổ chức từ quy mô vài chục nghìn thiết bị trở lên. Đó là lý do lộ trình có hai van điều tiết: **AURA (§7) tạo dòng tiền sớm**, và **bậc vận hành** là đòn bẩy biên cần kiểm chứng sớm với nhóm khách hàng đầu tiên. Đơn giá fleet là giả định nhạy cảm nhất của toàn bộ mô hình — xem Phụ lục G.

### 6.4 Ranh giới lõi mở và mặt phẳng thương mại

| | Lõi mã nguồn mở (MIT) | Mặt phẳng thương mại |
|:---|:---|:---|
| Chạy đầy đủ khi offline | Có | Không áp dụng |
| Cần tài khoản | Không | Có |
| Thay thế được bằng hạ tầng tự dựng | Có — interface công khai | — |
| Sở hữu định dạng gate và `.ntrace` | Có — định nghĩa tại đây | Dùng lại, không định nghĩa riêng |

**Cam kết sản phẩm:** không có tính năng nào của lõi bị khoá sau tài khoản. Mặt phẳng thương mại bán vận hành ở quy mô, không bán quyền sử dụng.

---

## 7. AURA — triển khai dọc

> *"Eat your way gradually through the customer by doing all their hardest work for them."*

Áp dụng chiến lược full-stack vào một thị trường dọc hẹp bằng chính framework công khai.

### 7.1 Sản phẩm

| Thuộc tính | Nội dung |
|:---|:---|
| **Là gì** | Trợ lý đa phương thức tại phòng cho villa và khách sạn nghỉ dưỡng |
| **Phần cứng** | ESP32-S3 · mic array 2 kênh có AEC · màn hình 3,5" · vỏ nhôm · BOM khoảng $75/máy |
| **Khách hàng** | Đơn vị quản lý bất động sản cho thuê quy mô 10–80 căn tại Việt Nam và Đông Nam Á |
| **Năng lực** | Hỏi đáp về villa · đặt món · gọi dịch vụ · đặt tour · điều khiển thiết bị trong phòng · chuyển tiếp nhân viên |
| **Kênh** | Thiết bị tại phòng + Zalo OA cho khách đã nhận phòng |
| **Gate tiêu biểu** | `unlock_door` · `order_food` · `call_staff` · `control_ac` — tất cả publish được lên registry |

### 7.2 Bốn vai trò trong danh mục sản phẩm

| Vai trò | Nội dung |
|:---|:---|
| **Bằng chứng sản xuất** | Framework chạy trong môi trường có tiếng ồn, mạng chập chờn và người dùng thật — không chỉ trong demo |
| **Dòng tiền sớm** | Tự trang trải chi phí vận hành, không phụ thuộc vào tiến độ của gateway |
| **Nguồn tín hiệu** | Lần đầu nhìn thấy nhà phát triển và khách hàng thật muốn mua gì |
| **Nguồn gate thật** | Những gate đầu tiên trên registry đến từ đây, đã tinh chỉnh bằng dữ liệu hiện trường |

### 7.3 Kỷ luật kiến trúc

**AURA dùng 100% mã nguồn và API công khai. Không nhánh nội bộ, không API đặc quyền.**

Bất kỳ khó khăn nào kỹ sư AURA gặp phải chính là bằng chứng framework đang thiếu tính năng đó — không phải lý do để fork. Ràng buộc này được nghiệm thu bằng một chỉ số ở §12.3, không bằng lời cam kết.

Với người vận hành villa, việc khó nhất không phải mua thiết bị mà là **chịu trách nhiệm khi thiết bị làm sai**. Gate đã review, đã kiểm thử, có log — chính là thứ gánh việc đó.

---

## 8. Lộ trình sản phẩm

Năm khối công việc, một cổng định lượng. Mũi tên giữa các khối là mũi tên **cho phép**, không phải mũi tên thời gian.

```
[ KHỐI 1a: SIM + LINUX + ACTION CI ]  Tuần 0–6
              │
              ▼
[ KHỐI 1b: ESP32-S3 + VOICE ]  Tuần 6–10  ──►  [ HOÀN TẤT LÕI MIT ]
              │                                          │
              ├──────────────────────────────────────────┘
              ▼
┌───────────────────────────────┬───────────────────────────────┐
│ KHỐI 2: COMMERCIAL PLANE      │ KHỐI 3: RAILS NỀN TẢNG        │
│ Tháng 2,5–6                   │ Tháng 2,5–6, song song        │
│ • Hosted Gateway              │ • Gate Registry & Versioning  │
│ • Fleet Management OS         │ • Metering, ID, Sandbox       │
└──────────────┬────────────────┴───────────────┬───────────────┘
               └────────────────┬───────────────┘
                                ▼
               [ KHỐI 4: AURA VERTICAL FULL-STACK ]  Tháng 6–12
                                │
                                ▼
               [ CỔNG THANH KHOẢN ĐỊNH LƯỢNG ]  — phép đo, không phải hạng mục
                                │
                                ▼
               [ KHỐI 5: MARKETPLACE & PAY ]  Tháng 18+
```

### 8.1 Khối 1a — Nền tảng logic và CI (tuần 0–6)

**Mục tiêu duy nhất:** một lập trình viên lạ đạt time-to-first-value **dưới 10 phút** trên máy cá nhân, không mua gì.

```
pip install neuroedge
neuroedge new my-agent
neuroedge run --target sim
```

| Phạm vi | Mục |
|:---|:---:|
| HAL hợp đồng năng lực, 5 nguyên thủy | §3.3 |
| Action Contract Engine, gate có version, fail-closed | §3.5 |
| Interface `SystemOne` / `SystemTwo` | §3.6 |
| Hai target đầu tiên: `sim` và `linux` | §3.2 |
| Action CI: record, replay, assert, golden | §3.7 |
| Bề mặt CLI cơ bản | §4.8 |
| 1 ứng dụng tham chiếu hoàn chỉnh | §7 |

### 8.2 Khối 1b — Hiện thực hoá vi điều khiển (tuần 6–10)

**Mục tiêu:** chứng minh định luật tương đương target trên vi điều khiển biên $5.

| Phạm vi | Nội dung |
|:---|:---|
| Port HAL lên `esp32s3` | Qua ESP-IDF toolchain |
| Voice pipeline tối ưu bộ nhớ | WebRTC AEC · Silero VAD · Opus streaming codec |
| `neuroedge verify` | Kiểm tra tương đương bit-for-bit giữa ba target |
| MCP client mỏng | Giữ ở mức tối thiểu — rẻ, và là ván cược về chuẩn giao tiếp |

**Không làm trong Khối 1:** vision · cloud · auth · tài khoản · registry · Jetson · Matter/HomeKit · fine-tune · fallback model cục bộ đã tinh chỉnh · hỗ trợ rộng biến thể board.

### 8.3 Khối 2 — Commercial plane (tháng 2,5–6)

Inference plane và fleet plane, đặc tả đầy đủ ở §6. Điều kiện cho phép: Khối 1 đã có người dùng ngoài đội chạy agent thật trên `linux` hoặc `esp32s3`.

### 8.4 Khối 3 — Bảy đường ray nền tảng (tháng 2,5–6, song song)

Bảy thành phần rẻ, hữu ích ngay ngày đầu, và là hạ tầng bắt buộc cho marketplace sau này. Không thành phần nào mang tính thương mại.

| # | Rail | Giá trị ngày đầu | Vai trò về sau |
|:---:|:---|:---|:---|
| 1 | Public Gate Registry | `neuroedge gate add <uri>` | Dữ liệu về gate nào thật sự được dùng lại |
| 2 | Manifest và semver cho agent, gate | Quản lý phụ thuộc | Đơn vị phân phối của marketplace |
| 3 | Capability declaration | Bắt lỗi lúc build (§4.9) | Kiểm tra tương thích trước khi cài |
| 4 | **Gate có version, `extends` được** | Dùng lại chuẩn an toàn của cộng đồng | Ứng viên hàng hoá số một |
| 5 | Stable ID cho thiết bị, agent, gate | Debug và hỗ trợ | Quy kết doanh thu |
| 6 | Metering theo lượt gọi agent và lượt đánh giá gate | Phân tích sử dụng | Cơ sở chia doanh thu |
| 7 | Permission và sandbox model | An toàn khi thử agent lạ | Điều kiện để chạy mã bên thứ ba |

Rail 5, 6, 7 **không thể** bổ sung sau: thiếu chúng thì marketplace tương lai không quy kết được doanh thu và không dám cho mã người lạ chạy trên thiết bị có actuator.

### 8.5 Khối 4 — AURA full-stack (tháng 6–12)

Đặc tả ở §7. Điều kiện cho phép: API framework đã ổn định và đã có bên ngoài đội ship thiết bị thật.

### 8.6 Cổng thanh khoản định lượng

**Đây không phải hạng mục công việc, mà là một phép đo.** Việc mở Khối 5 bị khoá cho tới khi thoả mãn **đủ cả bốn** ngưỡng — không phải ba trên bốn, và không tính trung bình.

| # | Chỉ số | Ngưỡng bắt buộc | Đo cái gì |
|:---:|:---|:---|:---|
| **G1** | Quy mô thiết bị hoạt động | ≥ 10.000 thiết bị active hàng tháng, gửi telemetry ổn định | Quy mô cầu |
| **G2** | Quy mô nguồn cung | ≥ 50 gate hoặc agent do bên thứ ba tự publish, mỗi cái ≥ 5 lượt cài | Quy mô cung |
| **G3** | Tỉ lệ trao đổi thực | **> 30% thiết bị chạy ít nhất một gate hoặc agent do người khác viết** | Thanh khoản thật |
| **G4** | Giao dịch tự phát ngoài nền tảng | Có bằng chứng người dùng tự trả tiền cho nhau để mua gate hoặc agent logic | Nhu cầu trả tiền thật |

**G3 là ngưỡng quan trọng nhất.** G1 và G2 có thể đạt mà vẫn không có thị trường — chúng đo hoạt động, không đo trao đổi.

**G4 là cơ chế lắng nghe.** Nếu người dùng đang tự giao dịch với nhau qua kênh khác, đó là thông điệp về sản phẩm thật: *"don't be annoyed that your users are using your product wrong; listen for the message they're sending."*

### 8.7 Khối 5 — Marketplace và Pay (tháng 18+)

Chỉ kích hoạt sau khi vượt cổng. Khi đó thương mại hoá không còn là canh bạc suy đoán, mà là việc chuẩn hoá một thị trường đã tự hình thành.

**Món hàng chính không phải agent nguyên khối, mà là gate đã tinh chỉnh qua hàng nghìn giờ chạy thực địa** — ví dụ gate kiểm soát va chạm cho cánh tay robot, gate kiểm soát ra vào toà nhà. Registry miễn phí ở Khối 3 trả lời hộ câu hỏi "bán gì" trong 12 tháng, gần như miễn phí.

Các ứng viên hàng hoá khác, xếp theo mức độ chuẩn bị sẵn của hạ tầng:

| Ứng viên | Luận điểm |
|:---|:---|
| **Gate đã tune** | Hạ tầng đã sẵn từ §3.5; giá trị tỉ lệ thuận với số giờ hiện trường đã trải qua |
| Wake-word đã train | Cho một ngôn ngữ hoặc một tên thương hiệu riêng |
| Board đã chứng nhận | Qua kênh phân phối phần cứng |
| Dịch vụ người thật | Cấu hình, tích hợp, triển khai tại chỗ |

**Về Pay:** khi tiền đã chảy qua gateway, đã có billing account, ledger và quan hệ thanh toán với nhà phát triển. Thêm cơ chế chia doanh thu cho tác giả gate bên thứ ba là bước mở rộng ngắn. Xây pay rails song song với gateway là xây hai lần cùng một thứ.

---

## 9. Ranh giới sản phẩm và ma trận đánh đổi

Danh sách loại trừ tường minh. Đây là phần quan trọng nhất của tài liệu: một đề xuất không có ranh giới rõ ràng thì không có phạm vi.

| Hạng mục | Trạng thái | Quy tắc | Đánh đổi và lợi ích |
|:---|:---|:---:|:---|
| **Marketplace thương mại có thu phí** | Chặn tới sau cổng | R3 | **Mất:** cơ hội thu hoa hồng sớm.<br>**Được:** không lãng phí 6 tháng xây một chợ không có thanh khoản |
| **Agent-to-agent pay, escrow, KYC** | Chặn tới sau cổng | R4 | **Mất:** bỏ qua một hướng công nghệ đang nóng.<br>**Được:** không gánh nghĩa vụ giấy phép tài chính và phòng chống rửa tiền |
| **Chương trình chứng nhận, phí badge** | Chặn tới sau cổng | R3 | **Mất:** một dòng doanh thu nhỏ.<br>**Được:** không tạo nghĩa vụ bảo chứng chất lượng khi chưa đủ năng lực kiểm định |
| **Thị giác máy tính (camera, NPU)** | Hoãn sau tháng 12 | R1 | **Mất:** tạm chưa phục vụ bài toán robot thị giác.<br>**Được:** giữ TTFV của voice và control dưới 10 phút |
| **Jetson, Matter, HomeKit** | Hoãn sau tháng 12 | R3 | **Mất:** giới hạn phạm vi phần cứng ban đầu.<br>**Được:** ba target đã đủ chứng minh định luật tương đương |
| **SSO/SAML, SOC 2, RBAC nhiều tầng** | Hoãn sau tháng 12 | R3 | **Mất:** chưa ký được hợp đồng doanh nghiệp lớn.<br>**Được:** không sa vào chu kỳ đàm phán dài trước khi sản phẩm ổn định |
| **Multi-region, on-premise** | Hoãn sau tháng 12 | R3 | **Mất:** một số khách hàng có ràng buộc chủ quyền dữ liệu.<br>**Được:** giữ một kiến trúc vận hành duy nhất |
| **Fallback model cục bộ đã tinh chỉnh** | Hoãn tới khi chỉ báo §11 bật | R3 | **Mất:** chưa có bảo hiểm hoàn chỉnh trước rủi ro nhà cung cấp.<br>**Được:** interface đã đủ phòng ngừa với chi phí một ngày |
| **Engine cảnh báo, BI, dashboard tuỳ biến** | Hoãn vô thời hạn | R1, R3 | **Mất:** một mục thường thấy trong RFP.<br>**Được:** tránh một phạm vi vô hạn |
| **Kubernetes** | Hoãn vô thời hạn | R1 | **Mất:** khó nhảy lên quy mô hàng triệu node tức thì.<br>**Được:** một Postgres, một Redis, một event bus đủ cho 50.000 thiết bị đầu tiên |
| **Fine-tune model** | Hoãn vô thời hạn | R3 | **Mất:** không tối ưu được model cho từng khách.<br>**Được:** giữ model là thành phần thay thế được |
| **Hỗ trợ rộng biến thể board** | Hoãn vô thời hạn | R1 | **Mất:** độ phủ phần cứng hẹp.<br>**Được:** ba target, mỗi target một board tham chiếu, chất lượng sâu |

---

# Phần IV — Kiểm chứng

## 10. Định vị cạnh tranh

### 10.1 Bản đồ đối thủ

```
                            ĐỘ PHỦ PHẦN CỨNG
                                   ▲
                                   │
                        [ ESP-Claw ]        ★ NEUROEDGE
                        (chính hãng,        (đa nền tảng, Action CI,
                         một dòng chip)      fail-closed gates)
                                   │
   ────────────────────────────────┼────────────────────────────────►
   THUẦN ĐIỀU PHỐI PHẦN MỀM        │        KIỂM THỬ HÀNH ĐỘNG VẬT LÝ
                                   │
      [ LangChain / CrewAI ]       │        [ XiaoZhi ]
      (không có trừu tượng          │        (voice pipeline tốt,
       phần cứng; action = API)     │         không có kiểm soát an toàn)
                                   │
                                   ▼
```

Bản chất cấu trúc của bốn nhóm đối thủ:

| Đối thủ | Thế mạnh | Vì sao không lấp được khoảng trống này |
|:---|:---|:---|
| **ESP-Claw** (Espressif) | Tối ưu sâu trên ESP32, MCP-native, hỗ trợ chính hãng | Bị khoá vào động cơ bán silicon. Sẽ không bao giờ phát triển một simulator độc lập trên Linux coi chip đối thủ là ngang hàng |
| **XiaoZhi** | Cộng đồng voice agent mã nguồn mở lớn nhất ở lớp ESP32 | Thiếu hoàn toàn HAL và khái niệm hợp đồng hành động; logic hội thoại gắn trực tiếp vào lệnh phần cứng |
| **LiveKit Agents · Pipecat · TEN** | Hạ tầng WebRTC thời gian thực rất mạnh | Mô hình kinh doanh dựa trên băng thông đám mây; hỗ trợ offline-first mâu thuẫn trực tiếp với doanh thu của chính họ |
| **LangChain · LlamaIndex** | Thống trị hệ sinh thái agent phần mềm | Không có khái niệm chân cắm, xung điện hay rủi ro cơ học; một hành vi sai chỉ là một dòng log |

### 10.2 Ba khác biệt có thể bảo vệ

| # | Khác biệt | Rào cản sao chép |
|:---:|:---|:---|
| **1** | **Hợp đồng hành động có kiểu + Action CI** | Đòi hỏi ba quyết định kiến trúc đồng thời ngay từ tuần đầu: sim là target thật, gate là dữ liệu có version, trace là công dân hạng nhất. Đối thủ đã xuất xưởng phải viết lại kiến trúc, không phải thêm tính năng |
| **2** | **Hợp đồng năng lực HAL trên ba target ngang hàng** | SDK một-chip không thể có khái niệm này vì mâu thuẫn với động cơ bán silicon. Bổ sung sau đòi hỏi thay toàn bộ tầng trừu tượng phần cứng |
| **3** | **Sở hữu định dạng gate và `.ntrace`** | Trong lĩnh vực chưa có chuẩn, đề xuất đầu tiên thường thắng bất kể ai đề xuất. Khi định dạng được chấp nhận, chi phí chuyển đổi của nhà phát triển rất lớn |

**Điều không nằm trong bảng: simulator một mình.** Nó là đòn bẩy TTFV xuất sắc, nhưng một đối thủ khởi động mới sẽ chọn đúng kiến trúc đó miễn phí sau khi thấy nó hiệu quả. Simulator là điều kiện cần của khác biệt số 1, không phải khác biệt tự thân.

### 10.3 Những mặt trận không cạnh tranh

| Mặt trận | Lập trường |
|:---|:---|
| **Giá inference** | Không tham gia cuộc đua hạ giá token giữa các model vendor |
| **Độ sâu driver một-chip** | Nhường driver ngoại vi cấp thấp cho SDK chính hãng; NeuroEdge chỉ chuẩn hoá 5 nguyên thủy HAL |
| **Bề rộng hỗ trợ phần cứng** | Chỉ hỗ trợ sâu ba target tham chiếu |

Ba mặt trận này thua từ đầu. Theo §1.4, thắng chúng chỉ nên là **lợi ích phụ** của việc thắng ở chiều khác, không bao giờ là mục tiêu.

---

## 11. Ma trận rủi ro

Bốn rủi ro theo nguồn gốc, loại trừ lẫn nhau.

| # | Rủi ro | Kịch bản đe doạ | Chiến lược giảm thiểu | Chỉ báo sớm |
|:---:|:---|:---|:---|:---|
| **1** | **Phụ thuộc nhà cung cấp model** | Đổi giá, siết điều kiện truy cập, hoặc tự ship framework cạnh tranh | Interface `SystemOne`/`SystemTwo` từ tuần 1. Sản phẩm là lớp hợp đồng an toàn; đổi model không đổi định vị (§3.6) | Thay đổi điều khoản API · vendor tuyển kỹ sư framework · vendor công bố SDK thiết bị |
| **2** | **Nền tảng bán dẫn** | Hãng chip phát hành framework IoT miễn phí vĩnh viễn | Đánh từ bên sườn (§1.4): thắng ở chiều kiểm thử đa nền tảng mà hãng chip về cấu trúc không thể làm. Ba target ngang hàng từ Khối 1 là bằng chứng | SDK chính hãng thêm lớp điều phối agent · hoặc bắt đầu hỗ trợ chip đối thủ |
| **3** | **Bào mòn biên lợi nhuận** | Giá token lao dốc; mô hình bán lại inference không có lãi | Trọng tâm biên ở fleet plane (§6.3). Inference sát giá vốn nhưng không miễn phí, để giữ tín hiệu trả tiền | Tỉ trọng doanh thu từ inference vượt fleet |
| **4** | **Phân mảnh phạm vi** | Áp lực xây marketplace sớm, hoặc chiều theo yêu cầu riêng của khách hàng doanh nghiệp đầu tiên | Đóng băng bộ lọc R1–R4 (§2) và bốn ngưỡng cổng thanh khoản (§8.6) thành văn bản **trước khi** áp lực xuất hiện | Xuất hiện đề xuất không thuộc R1 hay R2 nhưng vẫn được ưu tiên |

---

## 12. Hệ chỉ số hiệu suất

Đo bằng kết quả vận hành của khách hàng. **Số sao GitHub không xuất hiện trong bảng nào** — nó đo người xem, không đo người dùng.

### 12.1 Khối 1 — Lõi mã nguồn mở (tháng 2,5)

| Chỉ số | Ngưỡng cam kết | Ý nghĩa |
|:---|:---:|:---|
| **Time-to-first-value** | **< 10 phút**, đo trên 10 maker lạ | Tính tinh gọn của trải nghiệm cài đặt và chạy thử đầu tiên |
| **Định luật tương đương target** | **100% pass** trong `neuroedge verify` | Nhất quán logic tuyệt đối trên cả ba target |
| **Tỉ lệ giữ lại Action CI** | **≥ 50%** dự án dùng `neuroedge new` giữ và mở rộng test gate mặc định | Mức độ thâm nhập của thói quen kiểm thử an toàn |
| **Chuyển đổi sim → phần cứng** | **≥ 15%** người chạy sim nạp lên board thật trong 30 ngày | Phễu §1.6 có hoạt động hay không |
| **Khả năng quan sát** | Trace hiển thị tỉ lệ System 1/System 2, chi phí từng lượt, mọi quyết định gate | Điều kiện để khách hàng tin vào lớp an toàn |
| **Tài sản phân phối** | 3 ví dụ chạy được + 1 GIF 15 giây trong README | Kênh phân phối tự nhiên của một dự án OSS phần cứng |

### 12.2 Khối 2 và 3 — Thương mại và rails (tháng 6)

| Chỉ số | Ngưỡng cam kết | Ý nghĩa |
|:---|:---:|:---|
| **Độ tin cậy OTA** | **1.000 thiết bị / 0 thiết bị brick** | Thước đo sống còn để khách hàng giao phó đội thiết bị |
| **SLA độ trễ thoại P95** | **< 850 ms** round-trip trên Wi-Fi | Cam kết công khai từ lúc dứt lời tới khi loa phát tiếng |
| **SLA đánh giá gate P95** | **< 120 ms** cục bộ · **< 450 ms** qua cloud | Chốt an toàn không được làm gián đoạn tương tác tự nhiên |
| **Hiệu quả định tuyến** | Tiết kiệm **≥ 60%** chi phí token so với chỉ dùng System 2 | Bằng chứng định lượng cho luận điểm định tuyến |
| **Chia sẻ gate** | **≥ 20 gate** có ≥ 5 lượt cài bởi người không phải tác giả | Hiệu ứng mạng nội sinh đã kích hoạt trước khi mở chợ |
| **Điểm cân bằng doanh thu** | Doanh thu fleet **>** doanh thu inference | Phân biệt một dự án OSS nhiều sao với một công ty |

Chỉ số cuối quan trọng hơn năm chỉ số trên.

### 12.3 Khối 4 — Thực địa AURA (tháng 12)

| Chỉ số | Ngưỡng cam kết | Ý nghĩa |
|:---|:---:|:---|
| **Tính toàn vẹn của framework** | 100% AURA chạy trên nhánh công khai, 0 API đặc quyền | Nghiệm thu kỷ luật kiến trúc §7.3 |
| **Bằng chứng dùng lại** | Số gate và agent do bên thứ ba publish, tăng đều theo tháng | Registry có sức sống hay không |
| **Tiến độ cổng thanh khoản** | Báo cáo **từng ngưỡng G1–G4 riêng biệt**, không tính trung bình | Chuẩn bị cơ sở thực nghiệm cho Khối 5 |
| **Giúp khách hàng kiếm tiền** | Ít nhất 1 case study đo được: giảm chuyến đi hiện trường, giảm lô hàng thu hồi, hoặc rút ngắn bring-up board thứ hai | Nghiệm thu luận điểm §1.7 bằng số liệu khách hàng |

---

# Phụ lục

## Phụ lục A — Đặc tả hợp đồng năng lực HAL

### A.1 Năm nguyên thủy và thuộc tính thương lượng

| Nguyên thủy | Board khai báo | Agent yêu cầu | Quy tắc đối chiếu |
|:---|:---|:---|:---|
| `audio.in` | `channels`, `sample_rate_hz`, `aec`, `vad` | `aec`, `min_channels`, `sample_rate_hz` | Board phải đáp ứng bằng hoặc hơn |
| `audio.out` | `channels`, `sample_rate_hz` | `channels` | Board phải đáp ứng bằng hoặc hơn |
| `digital.out` | `pins[]` theo tên logic, `backend` | `pins[]` | Mọi pin agent yêu cầu phải tồn tại theo tên |
| `sensor.read` | `sensors[]` (`motion`, `temp`, `touch`, `imu`) | `sensors[]` | Mọi sensor agent yêu cầu phải tồn tại theo tên |
| `display` | `width`, `height`, `color` | `min_width`, `min_height` | Board phải đáp ứng bằng hoặc hơn |

### A.2 Ba quy tắc bất biến

| # | Quy tắc | Hệ quả khi vi phạm |
|:---:|:---|:---|
| 1 | **Pin và sensor định danh bằng tên logic, không bằng số chân** | Agent gắn chặt vào một layout board → mất tương đương target |
| 2 | **Mọi lệnh `digital.out` phải kèm gate đã pass** | HAL ném `ActionContractViolation`, không thực thi |
| 3 | **Đối chiếu chạy lúc build, không lúc runtime** | Lỗi cấu hình chỉ lộ ra khi thiết bị đã ở hiện trường |

### A.3 Ba bản hiện thực của cùng một hợp đồng

| Nguyên thủy | `sim` | `linux` | `esp32s3` |
|:---|:---|:---|:---|
| `audio.in` | File WAV hoặc mic laptop | ALSA / PulseAudio | I2S + AEC phần cứng |
| `audio.out` | Loa laptop hoặc thiết bị null | ALSA | I2S DAC |
| `digital.out` | Servo ảo trên UI, ghi vào trace | `gpiod` | GPIO driver |
| `sensor.read` | Giá trị theo kịch bản | I2C/SPI qua sysfs | I2C/SPI driver |
| `display` | Khung ảo trong trình duyệt | Cửa sổ hoặc framebuffer | SPI LCD |

---

## Phụ lục B — Đặc tả định dạng gate v1

### B.1 Các trường cấp cao nhất

| Trường | Bắt buộc | Nội dung |
|:---|:---:|:---|
| `schema` | Có | Luôn là `neuroedge.gate/v1` |
| `name` | Có | Tên logic, trùng với khoá trong `agent.toml` |
| `version` | Có | Semver. Đổi `allow_when` là breaking change |
| `extends` | Không | URI gate cơ sở. Kế thừa `evaluate`, được phép siết thêm `allow_when` |
| `evaluate` | Có | Các đại lượng cần đánh giá trước khi cho phép hành động |
| `allow_when` | Có | Điều kiện cho phép. Mọi mệnh đề phải đúng đồng thời |
| `on_block` | Có | Hành vi khi bị chặn |
| `budget` | Có | Ngân sách độ trễ và hành vi khi không đánh giá được |

### B.2 Ba kiểu trong `evaluate`

| Kiểu | Khai báo | Trả về | Toán tử trong `allow_when` |
|:---|:---|:---|:---|
| `bool` | `instructions` | Xác suất + confidence | `true`, `false`, `{ confidence_gte: x }` |
| `level` | `levels[]` có thứ tự, `instructions` | Mức + phân phối | `eq`, `lte`, `gte` |
| `choice` | `options[]`, `instructions` | Lựa chọn + xác suất từng nhánh | `in`, `not_in`, `eq` |

Ba kiểu này ánh xạ một-một vào hợp đồng tối thiểu của nhà cung cấp `SystemOne` (§3.6).

### B.3 `on_block` — bốn hành vi

| `action` | Nội dung |
|:---|:---|
| `escalate` | Chuyển cho `to:` (`human`, `slow`, hoặc một agent khác), kèm `message` |
| `deny` | Từ chối im lặng, chỉ ghi trace |
| `ask` | Hỏi lại người dùng một câu xác nhận đã khai báo trước |
| `degrade` | Chạy một hành động thay thế đã khai báo, an toàn hơn |

### B.4 `budget` — hai trường

| Trường | Nội dung |
|:---|:---|
| `p95_latency_ms` | Ngân sách đánh giá. Vượt ngân sách xử lý như `fail` |
| `fail` | `closed` (mặc định — chặn) hoặc `open` (cho phép; chỉ dùng cho hành động hoàn tác được và phải khai báo tường minh) |

### B.5 Năm quy tắc kế thừa

| # | Quy tắc |
|:---:|:---|
| 1 | Gate con **kế thừa toàn bộ** `evaluate` của gate cha |
| 2 | Gate con **chỉ được siết chặt** `allow_when`, không được nới lỏng |
| 3 | Gate con **được phép** bổ sung mục `evaluate` mới |
| 4 | `fail: open` **không kế thừa** qua `extends` — phải khai báo lại ở mỗi cấp |
| 5 | Chuỗi `extends` tối đa 3 cấp; vòng lặp kế thừa bị chặn lúc resolve |

**Quy tắc 2 và 4 là cơ sở khiến gate cộng đồng an toàn khi dùng lại:** kéo gate của người khác về không bao giờ làm chính sách của mình lỏng hơn. Không có hai quy tắc này, `extends` là một rủi ro chứ không phải một tính năng.

---

## Phụ lục C — Đặc tả định dạng `.ntrace`

### C.1 Sáu nhóm sự kiện

| Nhóm | Ghi gì |
|:---|:---|
| `input` | Khung audio (hoặc hash khi bật chế độ ẩn danh), đọc cảm biến, sự kiện hệ thống |
| `perception` | Kết quả wake-word, VAD, STT, kèm độ trễ từng chặng |
| `decision` | Mọi lượt gọi System 1 / System 2: đầu vào, đầu ra, confidence, độ trễ, chi phí |
| `gate` | Mọi đánh giá gate: tên, version, từng mục `evaluate`, kết quả `allow_when`, verdict |
| `action` | Mọi lệnh tới actuator: hành động, tham số, gate cho phép, mốc thời gian |
| `output` | Nội dung TTS, nội dung hiển thị |

### C.2 Bốn thuộc tính bắt buộc

| # | Thuộc tính | Vì sao |
|:---:|:---|:---|
| 1 | **Replay được trên mọi target** | Là nền của định luật tương đương target (§3.2) |
| 2 | **Ổn định giữa các phiên bản** | Trace ghi hôm nay phải replay được sau 12 tháng; đây là tài sản dài hạn của khách hàng |
| 3 | **Đọc được bởi người** | Điều tra sự cố không cần công cụ chuyên dụng |
| 4 | **Ẩn danh được tại nguồn** | Một cờ để thay nội dung thô bằng hash, giữ nguyên chuỗi quyết định |

### C.3 Golden — chuỗi quyết định tham chiếu

Golden là phần `decision` + `gate` + `action` của một trace, đã bỏ mốc thời gian và nội dung thô. So sánh golden trả lời đúng một câu hỏi: **với cùng đầu vào, agent có ra cùng chuỗi quyết định không.**

Đây là đơn vị kiểm thử duy nhất chịu được đồng thời việc đổi model, đổi prompt, và đổi target.

---

## Phụ lục D — Phần cứng, model và tích hợp

### D.1 Nền tảng phần cứng

| Nền tảng | Chip | Giá tham khảo | Trạng thái |
|:---|:---|:---:|:---|
| `sim` | — | — | Hạng nhất |
| Raspberry Pi 5 / x86 | BCM2712 / x86-64 | ~$80 | Hạng nhất (`linux`) |
| ESP32-S3 | Xtensa LX7 | ~$5 | Hạng nhất (`esp32s3`) |
| M5Stack CoreS3 | ESP32-S3 | ~$50 | Board tham chiếu của `esp32s3` |
| Seeed XIAO ESP32S3 | ESP32-S3 | ~$8 | Cộng đồng |
| NVIDIA Jetson Orin | Cortex-A78AE | ~$150–500 | Ngoài phạm vi (§9) |

### D.2 Model

| Vai trò | Ứng viên |
|:---|:---|
| **System One** — quyết định có cấu trúc | Jev · model intent chưng cất chạy cục bộ · SLM on-device |
| **System Two** — suy luận mở | Claude Sonnet 5 · Qwen 2.5 (3B/7B/72B) · Llama 3.2 · Phi-3 Mini |
| **STT** | Whisper (large-v3 / medium / small) · Deepgram Nova-2 · Sherpa-ONNX |
| **TTS** | Kokoro · Edge-TTS · ElevenLabs |
| **Wake-word** | openWakeWord · microWakeWord (trên MCU) |
| **VAD / AEC** | Silero VAD · WebRTC AEC |

Mọi mục trong bảng nằm sau interface. Danh sách này là cấu hình mặc định, không phải cam kết kiến trúc.

### D.3 Tích hợp

| Nhóm | Đối tác |
|:---|:---|
| Nhà thông minh | Home Assistant · Matter *(ngoài phạm vi)* · HomeKit *(ngoài phạm vi)* |
| Kênh nhắn tin | Zalo OA · Telegram · Slack · Discord |
| Thanh toán — chỉ ở lớp ứng dụng, không ở lõi | VietQR · Stripe · MoMo |
| Hạ tầng | AWS · GCP · Azure — không phụ thuộc nhà cung cấp cụ thể |

---

## Phụ lục E — Đối chiếu "Making Startups Powerful"

Tiểu luận của Paul Graham (tháng 9 năm 2026) là **bộ heuristic để sinh ý tưởng**, không phải checklist triển khai. Tác giả nói rõ các phép biến đổi này thường không cho ra gì, và mọi thứ phải phục tùng một ràng buộc duy nhất:

> *"They all have to make things better for the customer. You can't add network effects or make the money flow through you or go full stack just because you'd like to. You can only do these things when the result is better for the customer. Otherwise you won't have any uptake."*

Bảng phân loại theo trạng thái áp dụng. Không gán hệ số nhân, vì hệ số nhân không đo được và tạo cảm giác chắc chắn giả.

| Heuristic | Trạng thái | NeuroEdge làm gì | Tốt hơn cho khách hàng ở chỗ nào |
|:---|:---:|:---|:---|
| Sở hữu quan hệ khách hàng | Ngay | Hosted Gateway đứng giữa nhà phát triển và mọi model vendor | Đổi model từ xa, không nạp lại firmware |
| Để tiền chảy qua mình | Một phần | Qua gateway, nhưng biên đến từ fleet | Một hoá đơn thay vì năm |
| **Lấy dữ liệu sớm (mẫu Rippling)** | Ngay | Sở hữu định dạng trace tại nơi hành động vật lý sinh ra lần đầu | Trace và replay là thứ họ cần dù có NeuroEdge hay không |
| **Bán cho khách giai đoạn sớm** | Ngay | Maker ở thiết bị số 1, self-serve, không qua chu trình mua sắm | Cài và chạy trong 10 phút |
| Có API | Ngay | Mọi thứ gọi được qua API và CLI; gate là dữ liệu chứ không phải code | Không bị khoá vào cách dùng mà nhà cung cấp nghĩ ra |
| Hào phóng | Ngay | Lõi MIT: HAL, Action Contract Engine, voice pipeline, Action CI; registry miễn phí | Không phải trả tiền để có an toàn cơ bản |
| **Định nghĩa chuẩn sớm** | Ngay | Đề xuất định dạng gate và `.ntrace` cho lĩnh vực chưa có chuẩn | Một ngôn ngữ duy nhất để mô tả "thế nào là hành vi an toàn" |
| Hiệu ứng mạng qua chia sẻ | Ngay | Gate Registry với kế thừa `extends` | Dùng lại chính sách đã qua hàng nghìn giờ thử lửa |
| **Giúp người dùng kiếm tiền** | Ngay | Cắt chuyến đi hiện trường, giảm rủi ro thu hồi, rút ngắn bring-up (§1.7) | Đây là tiền mặt, không phải tiện ích |
| Chơi ván dài | Xuyên suốt | Bảy rails xây trước khi có nhu cầu thương mại | Hạ tầng sẵn sàng khi họ đạt quy mô |
| **Đánh từ bên sườn** | Xuyên suốt | Không đánh trực diện SDK chính hãng; thắng ở chiều kiểm thử được | Không bị khoá vào hệ sinh thái của một hãng chip |
| Đi full-stack | Khối 4 | AURA, sau khi framework ổn định | Gánh phần khó nhất: trách nhiệm khi thiết bị làm sai |
| Lắng nghe khi người dùng dùng sai | Là cơ chế đo | Ngưỡng G4 của cổng thanh khoản | — |
| App store | Sau cổng | Nền xây trước; phần thương mại bị khoá | Một store rỗng làm sản phẩm tệ hơn → vi phạm ràng buộc |
| Agent trả tiền cho agent | Sau cổng | Bề mặt pháp lý vượt năng lực hấp thụ hiện tại | — |

**Hai cảnh báo mà tài liệu này tuân thủ:**

| Cảnh báo | Tuân thủ bằng |
|:---|:---|
| **Dòng token.** Khi token chảy qua mình, câu hỏi là các công ty model có dễ nuốt chửng mình hoặc khách của mình đến mức nào | Trọng tâm biên lợi nhuận đặt ở fleet plane, không ở inference (§6.3) |
| **Bán quá rẻ.** *"If your product is a $10 bill that you sell for $5, your growth rate isn't telling you anything useful."* | Inference bán sát giá vốn nhưng **không** miễn phí, để bảo toàn tín hiệu sẵn sàng chi trả |

**Và một nguyên tắc về độ phức tạp:**

> *"The company is unconsciously cowering by doing something less ambitious than they could. 'Just y' is often, in effect, 'just stand up straight.'"*

Tài liệu này tuyên bố một mệnh đề duy nhất mà chưa ai tuyên bố, thay vì một phiên bản gọn hơn của mệnh đề mà bốn đối thủ đều đã tuyên bố.

---

## Phụ lục F — Từ điển thuật ngữ

| Thuật ngữ | Định nghĩa |
|:---|:---|
| **Hợp đồng hành động** | Ràng buộc bắt buộc giữa một hành động vật lý và gate của nó; HAL từ chối thực thi nếu không có chữ ký gate đã pass |
| **Gate** | Artifact có schema, có version (`.yaml`), khai báo điều kiện cho phép một hành động vật lý. Là dữ liệu, không phải code |
| **Action CI** | Trục kiểm thử hồi quy: record phiên thật, replay bit-for-bit trên target bất kỳ, assert về hành động — chạy mỗi commit |
| **`.ntrace`** | Định dạng trace: đầu vào, mọi đánh giá gate, mọi lệnh actuator, kèm mốc thời gian. Replay được |
| **Golden** | Chuỗi quyết định tham chiếu cho một trace. Lệch golden → CI đỏ |
| **Fail-closed** | Gate không đánh giá được → hành động bị chặn. Mặc định của mọi gate |
| **HAL / Hợp đồng năng lực** | Lớp trừu tượng phần cứng hai chiều: thiết bị khai báo năng lực, agent khai báo yêu cầu, đối chiếu lúc build |
| **Định luật tương đương target** | Cùng một file agent cho cùng một chuỗi quyết định trên `sim`, `linux`, `esp32s3`, không sửa một dòng |
| **System 1 / System 2** | Model quyết định có cấu trúc, nhanh / model suy luận, chậm. Cả hai sau interface thay thế được |
| **TTFV** | Time-to-first-value — từ lệnh cài đặt đến phản hồi hữu ích đầu tiên |
| **Rails** | Bảy thành phần hạ tầng nền xây sớm, chưa mang tính thương mại |
| **Cổng thanh khoản** | Bốn ngưỡng định lượng khoá việc mở Marketplace và Pay |
| **Inference plane** | Nhóm năng lực gateway đứng giữa thiết bị và nhà cung cấp model |
| **Fleet plane** | Nhóm năng lực quản trị đội thiết bị ngoài hiện trường |
| **MCP** | Model Context Protocol — chuẩn kết nối AI với công cụ |

---

## Phụ lục G — Giả định cần kiểm chứng

Bốn giả định mà toàn bộ mô hình dựa vào, xếp theo mức độ nhạy cảm. Ghi ra để đo, không để mặc định là đúng.

| # | Giả định | Vì sao nhạy cảm | Cách kiểm chứng | Mốc |
|:---:|:---|:---|:---|:---:|
| **G-a** | **Đơn giá fleet $1/thiết bị/tháng** | Quyết định trực tiếp quy mô thiết bị cần đạt để tự nuôi tổ chức (§6.3) | Thử nghiệm bậc vận hành có SLA và nhật ký kiểm toán với 5 khách hàng đầu; đo mức sẵn sàng trả thêm | Tháng 6 |
| **G-b** | **Tỉ lệ chuyển đổi sim → phần cứng ≥ 15%** | Nếu thấp hơn, phễu §1.6 đứt ngay bước đầu và simulator chỉ là đồ chơi | Đo từ ngày đầu qua telemetry ẩn danh của CLI; rà lại ngưỡng khi đủ 100 người dùng thật | Tháng 3 |
| **G-c** | **Tiết kiệm token ≥ 60% nhờ định tuyến** | Là bằng chứng định lượng duy nhất cho luận điểm System 1/System 2 | Đo trên lưu lượng gateway thật, tách theo loại tác vụ | Tháng 6 |
| **G-d** | **Gate là đơn vị chia sẻ mà người dùng thật sự muốn** | Toàn bộ luận điểm hiệu ứng mạng trước marketplace dựa vào đây | Registry miễn phí ở Khối 3 trả lời trong 12 tháng, gần như miễn phí | Tháng 12 |

**Nguyên tắc:** mỗi giả định có một mốc và một cách đo. Giả định không có cách đo thì không phải giả định — nó là niềm tin.

---

*Hết tài liệu*
