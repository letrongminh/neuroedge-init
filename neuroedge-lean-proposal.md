# NeuroEdge — Product Proposal

## Hợp đồng hành động có kiểu cho Physical AI

**Phiên bản:** 5.0 — Typed Action Edition
**Ngày:** 20 tháng 9, 2026
**Phạm vi tài liệu:** Định vị sản phẩm, kiến trúc, API, lộ trình, thước đo
**Ngoài phạm vi:** Giá, mô hình tài chính, kế hoạch gọi vốn

### Thay đổi so với v4.0

| # | Thay đổi | Lý do |
|----|----|----|
| 1 | Headline đổi từ *dual-brain framework* sang **hợp đồng hành động có kiểu + Action CI** | Khung cũ cột sản phẩm vào một hạng model của một thời điểm. Khung mới đúng bất kể ai lấp vào ô System 1, và ráp được bốn tài sản đang rời rạc thành một hạng mục chưa ai chiếm (§1.2) |
| 2 | `linux` lên **target hạng nhất** ngang `esp32s3` | Không có target thứ hai chạy thật thì hợp đồng năng lực chưa chứng minh được gì, và moat đa nền tảng chỉ là tuyên bố (§3.2) |
| 3 | Thêm **§4 — API sản phẩm**, có ví dụ hoàn chỉnh | Với một framework, API surface chính là sản phẩm. v4.0 không có dòng code nào ngoài `pip install` |
| 4 | §1 tái cấu trúc theo bốn **vị thế thượng nguồn** | Thay danh sách heuristic rời rạc bằng một nguyên lý tổ chức duy nhất |
| 5 | Thêm **Phụ lục C — Quyết định còn mở** | Tách bạch điều đã chốt với điều đang chờ số liệu |

---

## Mục lục

**Phần I — Luận điểm**
1. [Luận điểm chiến lược](#1-luận-điểm-chiến-lược)
2. [Nguyên tắc quyết định](#2-nguyên-tắc-quyết-định)

**Phần II — Sản phẩm**

3. [Kiến trúc sản phẩm](#3-kiến-trúc-sản-phẩm)
4. [API sản phẩm](#4-api-sản-phẩm)

**Phần III — Thực thi**

5. [Lộ trình sản phẩm](#5-lộ-trình-sản-phẩm)
6. [Ranh giới sản phẩm](#6-ranh-giới-sản-phẩm)

**Phần IV — Kiểm chứng**

7. [Định vị cạnh tranh](#7-định-vị-cạnh-tranh)
8. [Rủi ro và giảm thiểu](#8-rủi-ro-và-giảm-thiểu)
9. [Thước đo thành công](#9-thước-đo-thành-công)

**Phụ lục**

- [A — Đối chiếu "Making Startups Powerful"](#phụ-lục-a--đối-chiếu-making-startups-powerful)
- [B — Từ điển thuật ngữ](#phụ-lục-b--từ-điển-thuật-ngữ)
- [C — Quyết định còn mở](#phụ-lục-c--quyết-định-còn-mở)

---

## 0. Tóm tắt điều hành

### Bối cảnh

Physical AI đang ở điểm hội tụ của ba lực: phần cứng biên đã rẻ tới mức phổ cập, SLM đã chạy được trên thiết bị, và MCP đang trở thành chuẩn kết nối AI với công cụ. Một dev muốn làm voice agent cơ bản vẫn phải tự ghép sáu năng lực rời rạc qua các SDK không tương thích.

### Vấn đề

Cách mô tả khoảng trống đó là "thiếu một framework" thì đúng nhưng nông. Đây là khoảng trống mà **bốn đối thủ đều có thể lấp bằng cách thêm tính năng** — và ba trong bốn có nhiều nguồn lực hơn.

Khoảng trống thật sâu hơn một tầng: **không ai kiểm thử được hành động vật lý trước khi nó xảy ra ngoài hiện trường.** Một agent chatbot trả lời sai thì người dùng đọc lại. Một agent vật lý quyết định sai thì servo đã quay, khoá đã mở, motor đã chạy. Toàn ngành phần mềm có unit test, integration test, CI. Physical AI có: cắm board vào, nói thử, hy vọng.

### Câu hỏi

Cấu phần nào trong thế giới hoàn hảo của người xây agent vật lý mà NeuroEdge có thể tự biến mình thành?

### Trả lời

> **NeuroEdge làm cho mọi hành động vật lý của agent trở nên có kiểu, có version, kiểm thử được trong CI, và chạy y hệt nhau trên ba target — từ laptop tới thiết bị biên.**

Bốn thành phần lõi mở mã (MIT), một mặt phẳng thương mại duy nhất, một cổng định lượng chặn mọi thứ còn lại.

| | Nội dung |
|----|----|
| **Lõi mở mã (MIT)** | HAL hợp đồng năng lực · Action Contract Engine · Voice pipeline · Ba target ngang hàng (`sim` · `linux` · `esp32s3`) |
| **Mặt phẳng thương mại duy nhất** | Hosted gateway + Device fleet management |
| **Hoãn sau cổng liquidity** | Marketplace · Pay · Certification |

### Năm quyết định định hình toàn bộ tài liệu

| # | Quyết định | Hệ quả |
|----|----|----|
| 1 | **Hành động vật lý là hợp đồng có kiểu, không phải lời gọi hàm.** Mọi lệnh tới actuator đi qua một gate có version, khai báo được, chia sẻ được | §3.5, §4.5 |
| 2 | **Ba target ngang hàng.** `sim`, `linux`, `esp32s3` là ba implementation của cùng một HAL. Không có target nào là "phụ" | §3.2 |
| 3 | **Bán fleet, không bán token.** Bán lại inference là biên mỏng và là cuộc đua không thắng được với model vendor | §5.2 |
| 4 | **Model là thành phần thay thế được, không phải luận điểm.** Jev nằm sau interface `SystemOne` từ tuần 1 | §3.6, §8.1 |
| 5 | **Marketplace hoãn phần thương mại, giữ nguyên phần nền.** Registry, manifest, metering, permission model ship sớm vì rẻ, hữu ích ngay, và không retrofit được | §5.3 |

---

# Phần I — Luận điểm

## 1. Luận điểm chiến lược

### 1.1 Chạy ngược ràng buộc: thế giới hoàn hảo của khách hàng

Paul Graham đặt một ràng buộc cứng lên mọi chiến lược tăng quyền lực — chúng *chỉ* hợp lệ khi kết quả tốt hơn cho khách hàng — rồi chỉ ra rằng ràng buộc này chạy ngược được để sinh ý tưởng:

> *"What would the perfect world look like, from the customer's point of view? If there's a component of that world that the startup could transform itself into, it probably should."*

Thế giới hoàn hảo của người xây agent vật lý:

| # | Trong thế giới hoàn hảo | Hôm nay |
|----|----|----|
| 1 | Viết agent, chạy thử ngay, không cần mua gì | Chặn bởi việc chờ board về |
| 2 | Biết chắc agent không làm điều nguy hiểm — **trước khi** nạp firmware | Biết sau khi thiết bị đã ở nhà khách hàng |
| 3 | Đổi prompt, đổi model, chạy lại toàn bộ kịch bản an toàn trong 30 giây | Thử tay vài ca, cầu trời |
| 4 | Cùng một file agent chạy trên laptop, trên RPi, trên con chip $5 | Ba codebase |
| 5 | Sửa một thiết bị lỗi ngoài hiện trường từ máy của mình | Lái xe tới nơi |

Cấu phần NeuroEdge tự biến mình thành là **số 2 và số 3** — hai dòng duy nhất mà không đối thủ nào đang phục vụ. Số 1 và số 4 là điều kiện cần để số 2 và số 3 tồn tại. Số 5 là nơi có doanh thu.

### 1.2 Vì sao đổi khung từ "dual-brain"

Bản v4.0 đặt *dual-brain router* làm IP cốt lõi. Khung đó có ba điểm yếu cấu trúc:

| # | Điểm yếu | Hệ quả |
|----|----|----|
| 1 | **Cột vào một hạng model của một thời điểm.** Nếu constrained decoding đủ nhanh và đủ rẻ trở thành tính năng chuẩn của model lớn, "hai bộ não" tụt xuống thành chi tiết triển khai | Mất cả định vị lẫn moat cùng lúc |
| 2 | **Mô tả cơ chế, không mô tả lợi ích.** Khách hàng không mua "định tuyến giữa hai model". Họ mua "con servo không đập vào mặt người" | Pitch không tự bán được |
| 3 | **Bỏ phí bốn tài sản đã có.** Schema có version, record/replay, trace đầy đủ, permission model — nằm rải rác ở bốn mục khác nhau, chưa ai ráp lại | Không ai thấy hạng mục mới |

Khung mới giữ nguyên toàn bộ kiến trúc, chỉ đổi mệnh đề trung tâm:

> Không phải **"hai bộ não"** (kiến trúc của thời điểm) mà **"mọi hành động vật lý đều đi qua một hợp đồng có kiểu, kiểm thử được"** (đúng bất kể ai lấp vào ô System 1).

Ráp bốn tài sản lại cho ra một thứ chưa tồn tại:

```
Schema gate có version          ─┐
Record phiên thật trên board    ─┤
Replay trong sim, bit-for-bit   ─┼─→  ACTION CI
Trace đầy đủ mỗi quyết định     ─┘    Kiểm thử hành động vật lý
                                       trong pipeline, mỗi commit
```

Đây là thứ không sao chép được bằng cách thêm tính năng, vì nó đòi hỏi đúng ba quyết định kiến trúc ở tuần 1: sim là target thật, gate là artifact có version, trace là công dân hạng nhất. Ai đã ship xong mà không có chúng thì phải viết lại.

### 1.3 Bốn vị thế thượng nguồn

> *"Upstream is almost always good, whether it's with money or user relationship or customer stage or data."*

Đây là nguyên lý tổ chức duy nhất của chiến lược này. Bốn vị thế, loại trừ lẫn nhau, bao phủ đủ:

| Thượng nguồn | NeuroEdge chiếm bằng cách | Ship ở |
|----|----|----|
| **Quan hệ khách hàng** | Gateway đứng giữa dev và mọi nhà cung cấp model. Dev đổi model mà không đổi code, không nạp lại firmware | Khối 2 |
| **Dòng tiền** | Mọi lượt gọi model đi qua một endpoint, một credential, một hoá đơn | Khối 2 |
| **Giai đoạn khách hàng** | Bắt đầu từ indie maker ở thiết bị thứ nhất, không phải doanh nghiệp ở thiết bị thứ 500. Doanh thu tăng theo số thiết bị họ ship | Khối 1 |
| **Dữ liệu** | Mẫu Rippling: đi tới nơi **vòng đời dữ liệu bắt đầu**. Với agent vật lý, đó là lần đầu một hành động bị đề xuất trong simulator | Khối 1 |

Vị thế thứ tư là vị thế bị đánh giá thấp nhất. Rippling viết phần mềm onboarding không phải vì thị trường onboarding hấp dẫn, mà vì đó là nơi dữ liệu nhân sự sinh ra — và vì có nhiều thứ đặt cược hơn là thị trường onboarding, họ làm nó **tốt hơn mức cần thiết rất nhiều**, nên nó lan nhanh.

Tương đương ở đây: **simulator và trace format phải tốt hơn mức cần thiết rất nhiều.** Không phải vì simulator là thị trường, mà vì mọi quyết định của mọi agent trên mọi thiết bị đều đi qua đó trước tiên. Ai sở hữu định dạng trace sẽ sở hữu câu hỏi "agent nào đang làm gì, và có an toàn không".

### 1.4 Đánh từ bên sườn, không đánh trực diện

Bản v4.0 xử lý SDK của nhà sản xuất chip bằng một câu phòng thủ: "không cạnh tranh ở độ sâu một-chip". Đúng nhưng chưa đủ. Tiểu luận đưa ra công thức chính xác hơn:

> *"You'd have to do it by coming in from the side — by somehow making them irrelevant, rather than by frontal attack. Then you wouldn't depend on beating them to succeed; it would be an ancillary benefit of winning in another dimension."*

Chiều khác đó là gì? **Tính kiểm thử được của hành động, cắt ngang mọi loại phần cứng.**

Một SDK chính hãng về cấu trúc không thể đi vào chiều này, vì nó đòi hỏi coi chip của hãng chỉ là một trong nhiều target ngang hàng. Không hãng chip nào làm điều đó. Đây là lý do `linux` phải ở hạng nhất ngay từ đầu chứ không phải "sau tháng 12": **target thứ hai chạy thật chính là bằng chứng rằng chiều này tồn tại.** Không có nó, NeuroEdge chỉ là một framework một-board, đánh trực diện SDK chính hãng ngay trên sân của họ — mặt trận đã thua từ đầu.

### 1.5 Vì sao mở mã là kênh phân phối duy nhất khả thi

Mã nguồn mở chỉ hoạt động như kênh phân phối khi **người pull repo về chính là người ra quyết định mua**. Bốn thuộc tính:

| Thuộc tính | Biểu hiện |
|----|----|
| Đúng tầng | Hạ tầng, không phải ứng dụng nghiệp vụ |
| Chưa có chuẩn | Physical AI chưa có framework chuẩn hóa — và theo chú thích [2] của tiểu luận, trong lĩnh vực chưa có chuẩn, đề xuất đầu tiên thường thắng bất kể ai đề xuất |
| Demo lan truyền được | Video nói chuyện với con chip và servo quay |
| Người cài = người mua | Dev quyết định trong vài phút — cài được ngay bây giờ, không qua chu trình mua sắm |

**Chuẩn mà NeuroEdge đề xuất không phải framework, mà là định dạng gate và trace.** Framework thì ai cũng viết được cái khác. Định dạng mà mọi người dùng để mô tả "hành động này an toàn khi nào" thì chỉ có một cái thắng.

### 1.6 Vòng lặp giá trị

```
Chạy agent trong sim sau 10 phút, không mua gì
        ↓
Viết gate đầu tiên — agent từ chối làm điều nguy hiểm
        ↓
Ghi phiên thật trên board, replay trong CI mỗi commit
        ↓
Deploy 10 → 100 → 1.000 thiết bị, OTA không làm chết thiết bị nào
        ↓
Trả tiền cho fleet management (không phải cho token)
        ↓
Chia sẻ gate đã tune cho người khác dùng lại
        ↓
Registry ghi nhận gate nào được dùng lại nhiều nhất
        ↓
Dữ liệu này quyết định marketplace sẽ bán gì — thay vì đoán
```

Hai khác biệt so với v4.0:

1. Bước 2 và 3 là mới — đây là chỗ sản phẩm tạo ra giá trị mà không ai thay thế được.
2. Bước 6 là **hiệu ứng mạng khả dụng trước marketplace**. Tiểu luận nói rõ: bản deluxe của hiệu ứng mạng là app store, nhưng nếu chưa có cách trực tiếp, *"you can often induce network effects by letting your users share something"*. Gate là thứ để chia sẻ. Nó miễn phí, không mở bề mặt pháp lý, và làm sản phẩm tốt hơn cho cả người cho lẫn người nhận.

### 1.7 Giúp người dùng kiếm tiền

> *"Few things make you more powerful than that... they're (a) quick to adopt your product and (b) will pay a lot for it."*

Bản v4.0 không có dòng nào về điều này. Với NeuroEdge, đường dẫn là trực tiếp và đếm được:

| Chi phí thật của người ship phần cứng | NeuroEdge cắt bằng |
|----|----|
| Thu hồi lô hàng vì lỗi logic phát hiện muộn | Action CI bắt lỗi trước khi build firmware |
| Cử người tới hiện trường sửa một thiết bị | Log từ xa + config từ xa (§5.2) |
| Firmware hỏng làm chết cả đợt rollout | OTA theo đợt, tự rollback |
| Ba tháng bring-up cho board thứ hai | Cùng agent code, đổi một cờ `--target` |

Đây là bốn dòng đưa vào README, không phải bốn dòng đưa vào tài liệu nội bộ.

---

## 2. Nguyên tắc quyết định

Bốn quy tắc, áp dụng cho mọi đề xuất tính năng. Loại trừ lẫn nhau, bao phủ đủ.

| # | Quy tắc | Câu hỏi kiểm tra |
|----|----|----|
| **R1** | Phục vụ time-to-first-value | Có rút ngắn đường từ `pip install` đến câu trả lời đầu tiên không? |
| **R2** | Không thể thêm vào sau | Nếu bỏ qua bây giờ, 12 tháng nữa có retrofit được không? Nếu không → làm ngay |
| **R3** | Có người dùng thật đang chờ | Đã có ai yêu cầu, hay chỉ là suy diễn về nhu cầu tương lai? |
| **R4** | Không mở bề mặt pháp lý | Có kéo theo giấy phép, tuân thủ, hoặc trách nhiệm tài chính không? |

**Cách dùng:** R1 hoặc R2 đúng → làm. R3 sai → hoãn. R4 đúng → chặn tuyệt đối cho tới sau cổng liquidity.

Ví dụ áp dụng:

| Đề xuất | Phán quyết |
|----|----|
| Gate là artifact có version, không phải code | R2 đúng — đổi sau là đổi kiến trúc → **làm ngay** |
| Metering theo lượt gọi agent | R2 đúng → **làm ngay** dù chưa ai cần |
| `linux` là target hạng nhất | R1 và R2 đều đúng — là môi trường dev, và là bằng chứng của hợp đồng năng lực → **làm ngay** |
| Dashboard BI tùy biến | R1 sai, R3 sai → **hoãn vô thời hạn** |
| Agent-to-agent pay | R4 đúng → **chặn** |

---

# Phần II — Sản phẩm

## 3. Kiến trúc sản phẩm

### 3.1 Sơ đồ lớp

```
┌────────────────────────────────────────────────────────┐
│  L4  AGENT                                             │
│      Máy trạng thái hội thoại · MCP tool-calling        │
├────────────────────────────────────────────────────────┤
│  L3  ACTION CONTRACT ENGINE          ← IP cốt lõi      │
│      Gate có version · định tuyến model · trace         │
├────────────────────────────────────────────────────────┤
│  L2  PERCEPTION & ACTION                               │
│      Wake-word · VAD · AEC · STT · TTS · actuator       │
├────────────────────────────────────────────────────────┤
│  L1  HAL — HỢP ĐỒNG NĂNG LỰC                           │
│      5 nguyên thủy, kiểm tra lúc build                  │
├────────────────────────────────────────────────────────┤
│  L0  TARGET — ba implementation ngang hàng              │
│      sim  ·  linux  ·  esp32s3                          │
└────────────────────────────────────────────────────────┘
         ▲
         └── ACTION CI cắt ngang L0–L3: record trên bất kỳ
             target nào, replay trên bất kỳ target nào
```

Năm lớp trên là mã nguồn mở MIT. Không có lớp cloud nào trong sơ đồ — gateway và fleet là dịch vụ nằm ngoài, gọi qua interface thay thế được.

### 3.2 L0 — Ba target ngang hàng

**Định luật tương đương target:** ba target là ba implementation của cùng một HAL. Cùng một file agent chạy trên cả ba, không sửa một dòng. Vi phạm định luật này làm hỏng toàn bộ luận điểm Action CI.

| | `sim` | `linux` | `esp32s3` |
|----|----|----|----|
| **Hạng** | Hạng nhất | Hạng nhất | Hạng nhất |
| **Vai trò** | Vòng lặp dev, CI mỗi commit | Sản xuất trên RPi / x86 / gateway tại chỗ | Sản xuất trên thiết bị biên |
| **Chạy trong CI** | Mọi PR | Mọi PR | Nightly trên board thật |
| **Mô phỏng được** | Cảm biến giả, servo ảo, mạng chập chờn | Phần cứng thật, tài nguyên rộng | Phần cứng thật, tài nguyên chật |
| **Không mô phỏng được** | AEC phòng vang, beamforming mic array, áp lực bộ nhớ | Ràng buộc bộ nhớ của MCU | — |

#### Vì sao `linux` phải ở hạng nhất ngay từ Khối 1

| # | Lý do | Quy tắc |
|----|----|----|
| 1 | **Đây là bằng chứng của hợp đồng năng lực.** Một HAL với đúng một target thật là một API, không phải một hợp đồng. Moat đa nền tảng (§7.2) không tồn tại cho tới khi có target thứ hai chạy thật | R2 |
| 2 | **Đây là chiều "đánh từ bên sườn" (§1.4).** SDK chính hãng về cấu trúc không thể coi chip của hãng là một trong nhiều target ngang hàng | R2 |
| 3 | **Chi phí biên gần bằng không.** Linux đã là môi trường dev và môi trường CI. Phần lớn code đường dẫn `sim` dùng lại nguyên vẹn | R1 |
| 4 | **Phần lớn dự án Physical AI thật hiện nay chạy ở lớp RPi**, không phải MCU — đây là nơi người dùng thật đang chờ | R3 |
| 5 | **Là đường thoát khi ESP32-S3 chật.** Nếu bộ nhớ không đủ, `linux` gánh mà không cần đổi kiến trúc | R2 |

**Ba target, không bốn.** Jetson, Matter, HomeKit vẫn hoãn (§6). Ba là số nhỏ nhất chứng minh được định luật tương đương: một ảo, một rộng, một chật.

### 3.3 L1 — HAL, hợp đồng năng lực

**Nguyên tắc thiết kế:** HAL không phải mẫu số chung nhỏ nhất giữa các loại phần cứng. Nó là hợp đồng hai chiều — thiết bị khai báo năng lực, agent khai báo yêu cầu, và lệch nhau bị phát hiện **lúc build**.

Năm nguyên thủy, đủ cho một voice agent và không hơn:

| Nguyên thủy | Vai trò |
|----|----|
| `audio.in` | Mic, luồng khung PCM |
| `audio.out` | Loa |
| `digital.out` | GPIO, servo, relay |
| `sensor.read` | Nhiệt độ, chuyển động, chạm, IMU |
| `display` | Màn hình, đèn báo trạng thái |

Cụ thể hoá bằng code ở §4.2–§4.3, và bằng thông báo lỗi lúc build ở §4.9.

### 3.4 L2 — Perception & action

**Nguyên tắc:** bọc lại, không tự viết. Wake-word, VAD, AEC, STT, TTS đều đã có bản mã nguồn mở đủ tốt.

Giá trị thật nằm ở **máy trạng thái hội thoại** — phần ai cũng làm sai:

- Barge-in (người dùng ngắt lời giữa chừng)
- Xử lý im lặng và kết thúc lượt nói
- Phát partial trước khi câu hoàn chỉnh
- Phục hồi khi STT trả về rỗng hoặc nhiễu

Bốn ca này là lý do máy trạng thái hội thoại tốn ba tuần để làm đúng, và là lý do nó nằm trong lõi thay vì để dev tự ghép.

### 3.5 L3 — Action Contract Engine

Đây là IP cốt lõi. Bốn trách nhiệm, loại trừ lẫn nhau:

| # | Trách nhiệm | Nội dung |
|----|----|----|
| 1 | **Thi hành hợp đồng** | Mọi lệnh tới actuator đi qua gate tương ứng. Không có đường vòng — HAL từ chối lệnh không kèm gate đã pass |
| 2 | **Định tuyến model** | Chính sách khai báo được: truy vấn nào xuống System 1, ngưỡng confidence nào leo lên System 2 |
| 3 | **Xử lý suy giảm** | Timeout, fallback provider, chế độ local-only. Mặc định của mọi gate là `fail: closed` |
| 4 | **Phát trace** | Mỗi lượt sinh một trace đầy đủ, định dạng ổn định, replay được: độ trễ và chi phí từng chặng, mọi quyết định gate |

**Vì sao gate là artifact chứ không phải code.** Nếu gate là hàm Python, nó không chia sẻ được, không version được, không review được bởi người không đọc code, và không bán được. Nếu gate là file có schema, có version, có `extends` — nó trở thành:

| Vai trò | Ở đâu |
|----|----|
| Đơn vị kiểm thử | Action CI (§4.7) |
| Đơn vị chia sẻ → hiệu ứng mạng trước marketplace | §1.6 |
| Đơn vị review an toàn cho người không phải dev | Khách hàng doanh nghiệp về sau |
| Ứng viên hàng hoá của marketplace | §5.6 |

Một quyết định định dạng, bốn lợi ích. Đây là mẫu R2 điển hình: gần như miễn phí ở tuần 1, gần như không thể retrofit ở tháng 12.

### 3.6 Lớp trừu tượng model

**Quyết định kiến trúc bắt buộc từ tuần 1.** Jev nằm sau interface `SystemOne`; model suy luận nằm sau `SystemTwo`. Cả hai đều có đường dẫn cục bộ khai báo được.

| | |
|----|----|
| **Rủi ro** | Nếu luận điểm sản phẩm dựa vào một model đóng của một vendor vừa ra đời, vendor đó nắm số phận sản phẩm |
| **Kịch bản xấu** | Đổi giá, đổi điều kiện truy cập, hoặc vendor tự ship framework cạnh tranh |
| **Chi phí phòng ngừa** | *Interface*: một ngày. *Fallback cục bộ đã tune*: vài tuần |
| **Quyết định** | Ship interface ở tuần 1 (R2). Fallback cục bộ ship khi chỉ báo sớm ở §8.1 bật — xem Phụ lục C |

Dưới khung mới, đây không còn là rủi ro tồn vong. Sản phẩm là hợp đồng hành động; model chỉ là thứ điền vào ô đánh giá của gate. Đổi model không đổi định vị.

### 3.7 Trục xuyên lớp — Action CI

**Nguyên tắc thiết kế quan trọng nhất: simulator là một target thật, không phải mock.**

Nếu sim là một đường code riêng, nó sẽ lệch khỏi phần cứng trong khoảng sáu tuần và trở thành đồ chơi. Sim là implementation của đúng HAL đó, chạy đúng agent code đó.

Đó là điều kiện cần. Điều kiện đủ là bốn thành phần ráp lại:

| Thành phần | Nội dung |
|----|----|
| **Record** | Ghi phiên thật trên board ra file `.ntrace`: audio vào, đọc cảm biến, mọi đánh giá gate, mọi lệnh actuator, kèm mốc thời gian |
| **Replay** | Phát lại `.ntrace` trên bất kỳ target nào. Cùng đầu vào → cùng chuỗi quyết định, so được từng bit |
| **Assert** | Thư viện test khẳng định về hành động: *bị chặn*, *chặn bởi gate nào*, *leo thang tới đâu*, *chân nào không bao giờ được kích* |
| **Golden** | Chuỗi quyết định tham chiếu. Đổi prompt hoặc đổi model làm lệch golden → CI đỏ |

Ba câu hỏi mà hôm nay không framework nào trả lời được, và Action CI trả lời trong 30 giây:

1. Đổi prompt xong, agent còn từ chối mở khoá cho người chưa xác thực không?
2. Đổi từ model A sang model B, có kịch bản an toàn nào hồi quy không?
3. Ba target có cho cùng một quyết định trên cùng một đầu vào không?

**Khoảng cách với thực tế phải nói thẳng trong docs:** sim không mô phỏng AEC trong phòng vang, beamforming của mic array, wifi chập chờn, và áp lực bộ nhớ trên thiết bị biên. Đổi lại, `--target esp32s3` cách đúng một lệnh, và mọi thứ *quyết định được* đều kiểm thử được.

---

## 4. API sản phẩm

Với một framework, API surface chính là sản phẩm. Mục này định nghĩa nó.

### 4.1 Năm nguyên tắc thiết kế API

| # | Nguyên tắc | Hệ quả |
|----|----|----|
| 1 | **Năng lực là khai báo, không phải mệnh lệnh** | Board và agent cùng khai báo; công cụ đối chiếu lúc build |
| 2 | **Hành động vật lý không gọi trực tiếp được** | Chỉ tới actuator qua `c.do()`, luôn đi qua gate |
| 3 | **Gate là dữ liệu, không phải code** | Version được, chia sẻ được, review được, bán được |
| 4 | **Cùng một file agent trên mọi target** | Target là cờ dòng lệnh, không phải nhánh code |
| 5 | **Mặc định là fail-closed** | Gate không chạy được → hành động bị chặn, không phải được phép |

### 4.2 Thiết bị khai báo năng lực

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
channels = 1

[capabilities."display"]
width  = 320
height = 240

[capabilities."digital.out"]
pins = ["door_lock", "lamp"]
```

Cùng một board định nghĩa cho `linux` khác đúng hai dòng:

```toml
# boards/villa-gateway.board.toml
[board]
id     = "villa-gateway"
target = "linux"          # ← khác ở đây

[capabilities."digital.out"]
pins    = ["door_lock", "lamp"]
backend = "gpiod"         # ← và ở đây
# phần còn lại giống hệt
```

### 4.3 Agent khai báo yêu cầu

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
unlock_door = "neuroedge://gates/physical-access@1.2.0"
order_food  = "./gates/order_food@0.1.0.yaml"

[targets]
supported = ["sim", "linux", "esp32s3"]
```

Dòng `neuroedge://` là toàn bộ luận điểm hiệu ứng mạng trong một dòng: gate của người khác, có version, kéo về bằng tên.

### 4.4 Hành động có kiểu

```python
# actions/unlock_door.py
from neuroedge import action
from neuroedge.hal import digital

@action(requires="digital.out:door_lock", gate="unlock_door")
def unlock_door(guest_id: str, duration_s: int = 30) -> None:
    """Mở khoá cửa phòng cho khách đã xác thực."""
    digital.out("door_lock").pulse(seconds=duration_s)
```

Ba điều decorator `@action` áp đặt:

1. Hàm này **không gọi trực tiếp được** từ code agent. Gọi thẳng → `ActionContractError`.
2. `requires` tham gia đối chiếu năng lực lúc build (§4.9).
3. `gate` phải trỏ tới một gate đã khai báo. Thiếu gate → build dừng.

### 4.5 Gate là artifact có version

```yaml
# gates/unlock_door@1.2.0.yaml
schema:  neuroedge.gate/v1
name:    unlock_door
version: 1.2.0
extends: neuroedge://gates/physical-access@1.2.0

evaluate:
  guest_authenticated:
    type: bool
    instructions: "Khách đã xác thực danh tính trong phiên hiện tại"
  room_matches:
    type: bool
    instructions: "Phòng được yêu cầu trùng với phòng đã đặt của khách"
  risk:
    type: level
    levels: [low, medium, high]
    instructions: "Mức rủi ro của việc mở khoá tại thời điểm này"

allow_when:
  guest_authenticated: true
  room_matches:        true
  risk:                { lte: low }

on_block:
  action:  escalate
  to:      human
  message: "Cần nhân viên xác nhận trước khi mở khoá."

budget:
  p95_latency_ms: 150
  fail:           closed      # không đánh giá được → chặn
```

Năm thuộc tính mà định dạng này mở ra, và code Python không mở ra:

| Thuộc tính | Vì sao quan trọng |
|----|----|
| `version` + `extends` | Kế thừa gate cơ sở của cộng đồng, override phần riêng |
| `evaluate` tách khỏi `allow_when` | Đổi model không đổi chính sách; đổi chính sách không đụng code |
| `budget.fail: closed` | Hành vi khi mất mạng là một dòng khai báo, không phải một nhánh `try/except` bị quên |
| Đọc được bởi người không phải dev | Quản lý vận hành review được điều kiện mở khoá |
| Là file | Diff được, review trong PR, publish lên registry |

### 4.6 Agent hoàn chỉnh

```python
# agent.py
from neuroedge import Agent, Conversation, SystemOne, SystemTwo
from actions.unlock_door import unlock_door
from actions.order_food import order_food

agent = Agent.from_toml("agent.toml")

agent.mind(
    fast  = SystemOne("jev-latest",      fallback="local/intent-distil-8m"),
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

    elif intent.top == "faq" and intent.confidence > 0.8:
        await c.say(c.recall_answer())          # không gọi System 2

    else:
        await c.say(await c.slow.reply())
```

Đây là toàn bộ agent. Ba quan sát:

- Không có `if target == ...` ở đâu cả. Cùng file này chạy trên `sim`, `linux`, `esp32s3`.
- `c.do()` là cổng duy nhất tới thế giới vật lý. Không có đường vòng.
- `c.say()` và `c.do()` tách biệt về kiểu: nói là rẻ và hoàn tác được, làm thì không.

### 4.7 Action CI

```python
# tests/test_gates.py
from neuroedge.testing import replay, scenario


def test_khong_mo_khoa_khi_khach_chua_xac_thuc():
    s = replay("traces/2026-09-14T22-10-unverified.ntrace")
    assert s.action("unlock_door").blocked
    assert s.blocked_by == "unlock_door@1.2.0"
    assert s.escalated_to == "human"
    assert s.pin("door_lock").never_pulsed()


def test_gate_fail_closed_khi_mat_mang():
    s = scenario("traces/happy-path.ntrace", network="offline")
    assert s.action("unlock_door").blocked
    assert s.reason == "gate_unreachable"


def test_doi_model_khong_lam_hoi_quy_an_toan():
    s = replay("traces/happy-path.ntrace", fast="local/intent-distil-8m")
    assert s.decisions == s.golden("traces/happy-path.golden")


@scenario.parametrize(target=["sim", "linux", "esp32s3"])
def test_ba_target_cho_cung_mot_quyet_dinh(target):
    s = replay("traces/happy-path.ntrace", target=target)
    assert s.decisions == s.golden("traces/happy-path.golden")
```

Test cuối là **định luật tương đương target (§3.2) ở dạng khẳng định chạy được**. Nó không phải một lời hứa trong tài liệu; nó là một dòng CI đỏ khi bị vi phạm.

### 4.8 Bề mặt CLI

```bash
neuroedge new villa-concierge          # scaffold: agent.toml, 1 action, 1 gate, 1 test

neuroedge run   --target sim           # vòng lặp dev, mở UI trình duyệt
neuroedge run   --target linux         # chạy thật trên RPi / x86
neuroedge build --target esp32s3 --board villa-panel

neuroedge test                         # Action CI trên sim + linux
neuroedge verify --targets sim,linux,esp32s3   # kiểm tra tương đương target

neuroedge record --target esp32s3 --out traces/     # ghi phiên thật
neuroedge replay traces/x.ntrace --target sim       # điều tra sự cố hiện trường

neuroedge gate publish gates/unlock_door@1.2.0.yaml # lên registry công khai
neuroedge gate add neuroedge://gates/robot-arm@2.0.0
```

Hai lệnh `record` / `replay` là cầu nối giữa hiện trường và máy dev. Một thiết bị lỗi ở villa khách hàng trở thành một test case trên laptop trong một lệnh.

### 4.9 Hợp đồng năng lực lúc build

```
$ neuroedge build --target esp32s3 --board villa-panel

✗ CAPABILITY MISMATCH — dừng build, không nạp firmware

  agent  villa-concierge@0.3.1   yêu cầu   sensor.read:motion
  board  villa-panel-v2          cung cấp  audio.in, audio.out, display,
                                           digital.out:[door_lock, lamp]

  thiếu  sensor.read:motion      dùng tại  actions/auto_light.py:14

  → Thêm cảm biến vào board.toml, hoặc bỏ yêu cầu khỏi agent.toml.

  Lỗi này trước đây chỉ lộ ra khi thiết bị đã nằm ngoài hiện trường.
```

Dòng cuối là toàn bộ luận điểm của §3.3 trong một câu, và nó nằm trong terminal của người dùng chứ không nằm trong tài liệu này.

---

# Phần III — Thực thi

## 5. Lộ trình sản phẩm

Bốn khối công việc, một cổng định lượng. Mũi tên giữa các khối là mũi tên **cho phép**, không phải mũi tên thời gian.

### 5.1 Khối 1 — Lõi mở mã (Tháng 0–2)

**Mục tiêu duy nhất:** một người lạ, không có phần cứng, chạy được một agent có gate trong 10 phút.

```
pip install neuroedge
neuroedge new my-agent
neuroedge run --target sim
```

**Phạm vi:** HAL (§3.3) · Action Contract Engine (§3.5) · Interface `SystemOne`/`SystemTwo` (§3.6) · Voice pipeline (§3.4) · Ba target `sim`/`linux`/`esp32s3` (§3.2) · Action CI: record, replay, assert (§3.7) · MCP client mỏng.

**Về MCP:** giữ ở mức tối thiểu. Rẻ, và là ván cược về chuẩn giao tiếp.

**Không làm trong khối này:** vision · cloud · auth · tài khoản · registry · Jetson · Matter/HomeKit · fine-tune · fallback model cục bộ đã tune · hỗ trợ nhiều biến thể board.

> **Cảnh báo phạm vi.** Nâng `linux` lên hạng nhất và thêm Action CI làm tăng phạm vi Khối 1 so với v4.0, trong khi thời hạn giữ nguyên 2 tháng. Máy trạng thái hội thoại một mình đã tốn ba tuần (§3.4). Xem Phụ lục C.1 — đây là quyết định còn mở, không phải giả định đã chốt.

### 5.2 Khối 2 — Commercial plane (Tháng 2–6)

Mặt phẳng thương mại duy nhất của toàn bộ kế hoạch.

**Quyết định đặt giá định hình sản phẩm:** inference bán gần giá vốn như công cụ thu hút; fleet management là nơi có markup.

> Tiểu luận ủng hộ chiến lược này — *"sell as cheaply as they need to at first; get all the users, then worry about your margins"* — nhưng chú thích [4] kèm một cảnh báo phải tuân: bán quá rẻ thì **mất tín hiệu mà khách hàng gửi bằng việc trả tiền**. Vì vậy inference bán *gần* giá vốn, không bán *miễn phí*. Con số phải đủ để việc ai trả và ai không trả vẫn nói lên điều gì đó.

#### Inference plane — 6 năng lực

| # | Năng lực | Vì sao dev trả tiền |
|----|----|----|
| 1 | Một endpoint, một credential | Thiết bị không giữ key bên thứ ba; xoay key không cần nạp lại firmware |
| 2 | Routing đa nhà cung cấp + fallback | Thiết bị không bao giờ thấy sự cố của một nhà cung cấp |
| 3 | Giao thức hợp với edge | WebSocket giữ liên tục, khung audio nhị phân, partial theo luồng |
| 4 | Hạn mức cứng theo thiết bị | Một thiết bị lỗi không đốt sạch hoá đơn |
| 5 | Cache ngữ nghĩa + đếm tỉ lệ System 1/System 2 | Vừa là nguồn biên, vừa là bằng chứng cho luận điểm định tuyến |
| 6 | Một trace cho mỗi lượt | Cùng định dạng `.ntrace` dùng trong Action CI — hiện trường và CI nói chung một ngôn ngữ |

Năng lực 3 là rào cản kỹ thuật thật: thiết bị biên không kham nổi bắt tay TLS cho từng request HTTP. Hiện không ai terminate audio stream cho lớp phần cứng này.

Năng lực 6 là chỗ Khối 2 khoá vào Khối 1: trace sinh ra trên gateway replay được trên laptop, không cần chuyển đổi.

#### Fleet plane — 5 năng lực

| # | Năng lực | Vì sao dev trả tiền |
|----|----|----|
| 1 | Định danh & provisioning | Cert riêng từng thiết bị, luồng claim ở lần boot đầu |
| 2 | OTA rollout theo đợt, tự rollback | Lý do số một khiến dân phần cứng trả tiền cho platform |
| 3 | Sổ kiểm kê + sức khoẻ fleet | Online/offline, phiên bản firmware, RSSI, vòng lặp reboot |
| 4 | Config, secret và **gate** từ xa | Đổi wake-word, prompt, ngưỡng gate mà không nạp lại firmware |
| 5 | Log và trace từ xa cho một thiết bị | Kéo `.ntrace` từ hiện trường về, replay trong sim |

**Liên tục với Khối 1:** thiết bị ảo trong simulator hiện lên trong fleet console ngay. Đường từ `pip install` đến "tôi đang nhìn thiết bị của mình trên dashboard" phải liền một mạch — **fleet console phải hữu ích ở n=1**, không phải ở n=100. Đây là thành phần sản phẩm duy nhất đưa người dùng từ 1 thiết bị lên 100; không có nó, vòng lặp §1.6 đứt ở giữa.

### 5.3 Khối 3 — Rails (Tháng 2–6, song song Khối 2)

Bảy thứ rẻ, hữu ích ngay ngày đầu, và là hạ tầng bắt buộc cho marketplace sau này. Không thứ nào mang tính thương mại.

| # | Rail | Giá trị ngày đầu | Vai trò về sau |
|----|----|----|----|
| 1 | Registry công khai, miễn phí | `neuroedge gate add <uri>` | Dữ liệu về gate nào thật sự được dùng lại |
| 2 | Manifest + semver cho agent và gate | Quản lý phụ thuộc | Đơn vị phân phối của marketplace |
| 3 | Khai báo capability | Bắt lỗi lúc build (§4.9) | Kiểm tra tương thích trước khi cài |
| 4 | **Gate có version, `extends` được** | Dùng lại gate an toàn của cộng đồng | Ứng viên hàng hoá số một |
| 5 | Stable ID cho thiết bị, agent, gate | Debug, hỗ trợ | Quy kết doanh thu |
| 6 | Metering theo lượt gọi agent và lượt đánh giá gate | Phân tích sử dụng | Cơ sở chia doanh thu |
| 7 | Permission / sandbox model | An toàn khi thử agent lạ | Điều kiện để chạy mã bên thứ ba |

Rail 5, 6, 7 **không thể** thêm vào sau: thiếu chúng thì marketplace tương lai không quy kết được doanh thu và không dám cho mã người lạ chạy trên thiết bị có actuator.

Rail 4 là hiệu ứng mạng khả dụng trước marketplace (§1.6). Nó miễn phí, không mở bề mặt pháp lý, và làm sản phẩm tốt hơn cho cả người chia sẻ lẫn người dùng lại — thoả ràng buộc cứng của tiểu luận.

### 5.4 Khối 4 — AURA full-stack (Tháng 6–12)

Đi full-stack vào một thị trường dọc hẹp bằng chính framework của mình.

| Vai trò | Nội dung |
|----|----|
| Bằng chứng sản xuất | Framework chạy ngoài đời, không chỉ trong demo |
| Dòng tiền sớm | Kéo dài đường băng mà không phụ thuộc gateway |
| Nguồn tín hiệu | Lần đầu nhìn thấy dev và khách hàng thật muốn mua gì |
| Nguồn gate thật | Những gate đầu tiên trên registry đến từ đây, đã tune bằng dữ liệu thật |

**Ràng buộc kỷ luật:** AURA dùng đúng framework công khai, không nhánh nội bộ, không API đặc quyền. Khoảnh khắc AURA cần một tính năng framework không có, đó là tín hiệu framework thiếu tính năng đó — không phải lý do để fork.

> Tiểu luận mô tả một biến thể của full-stack đáng nhắm tới: *"eat your way gradually through the customer by doing all their hardest work for them."* Với người vận hành villa, việc khó nhất không phải mua thiết bị mà là **chịu trách nhiệm khi thiết bị làm sai**. Gate đã review, đã kiểm thử, có log — chính là thứ gánh việc đó.

### 5.5 Cổng liquidity

**Đây không phải hạng mục công việc. Nó là một phép đo.** Bốn ngưỡng phải đạt đủ, không phải ba trên bốn.

| # | Ngưỡng | Đo cái gì |
|----|----|----|
| 1 | ≥ 10.000 thiết bị hoạt động hàng tháng | Quy mô cầu |
| 2 | ≥ 50 gate hoặc agent tự publish, mỗi cái ≥ 5 lượt cài | Quy mô cung |
| 3 | **> 30% thiết bị chạy gate hoặc agent mà chủ thiết bị không tự viết** | Liquidity thật |
| 4 | Có bằng chứng giao dịch tự phát ngoài nền tảng | Nhu cầu trả tiền thật |

Ngưỡng 3 quan trọng nhất. Ngưỡng 1 và 2 đạt được mà vẫn không có thị trường — chúng đo hoạt động, không đo trao đổi.

Ngưỡng 4 áp dụng trực tiếp chỉ dẫn về việc lắng nghe khi người dùng "dùng sai" sản phẩm: *"don't be annoyed that your users are using your product wrong; listen for the message they're sending."* Nếu người ta đang tự giao dịch với nhau qua kênh khác, đó là thông điệp về sản phẩm thật.

**Ghi ngưỡng từ hôm nay** để sáu tháng nữa quyết định bằng số liệu chứ không bằng cảm tính.

### 5.6 Khối 5 — Marketplace và Pay (Tháng 18+)

Chỉ mở khi đủ cả bốn ngưỡng. Khi đó marketplace không còn là canh bạc; nó là việc thu dọn một thị trường đã tự hình thành.

**Món hàng chưa được quyết định, và đó là chủ ý.** Bản v3.0 khoá chặt vào "agent trọn gói". Các ứng viên hợp lý ngang nhau:

| Ứng viên | Luận điểm |
|----|----|
| **Gate đã tune** | Một safety gate cho cánh tay robot, đã chạy qua 10.000 giờ hiện trường, có giá trị cao hơn nhiều một agent trọn gói — và đây là ứng viên được §3.5 chuẩn bị sẵn hạ tầng |
| Wake-word đã train | Cho một ngôn ngữ hoặc một tên thương hiệu riêng |
| Board đã chứng nhận | Qua kênh phân phối phần cứng |
| Dịch vụ người thật | Cấu hình, tích hợp, triển khai tại chỗ |

Registry miễn phí ở Khối 3 trả lời hộ câu hỏi này trong 12 tháng, gần như miễn phí.

**Về Pay:** khi tiền đã chảy qua gateway, đã có billing account, ledger và quan hệ thanh toán với dev. Thêm "trả tiền cho bên thứ ba từ dòng tiền này" là bước ngắn. Xây pay rails song song với gateway là xây hai lần cùng một thứ.

---

## 6. Ranh giới sản phẩm

Danh sách loại trừ tường minh, theo lý do. Đây là phần quan trọng nhất của tài liệu: một đề xuất không có ranh giới rõ ràng thì không có phạm vi.

| Hạng mục | Trạng thái | Lý do (§2) |
|----|----|----|
| Marketplace thương mại, chia hoa hồng | Chặn tới sau cổng | R3 — chưa có liquidity |
| Agent-to-agent pay, escrow, KYC | Chặn tới sau cổng | R4 — bề mặt pháp lý |
| Chương trình chứng nhận, phí badge | Chặn tới sau cổng | R3 |
| Vision (camera, nhận diện) | Hoãn sau tháng 12 | R1 sai — không phục vụ TTFV |
| Jetson, Matter, HomeKit | Hoãn sau tháng 12 | R3 — ba target đã đủ chứng minh định luật tương đương |
| SSO/SAML, SOC 2, RBAC nhiều tầng | Hoãn sau tháng 12 | R3 — nhu cầu doanh nghiệp, chưa có doanh nghiệp |
| Multi-region, on-prem | Hoãn sau tháng 12 | R3 |
| Fallback model cục bộ đã tune | Hoãn tới khi chỉ báo §8.1 bật | R3 — interface đã đủ phòng ngừa; xem Phụ lục C.2 |
| Engine cảnh báo, BI, dashboard tuỳ biến | Hoãn vô thời hạn | R1 và R3 đều sai; phạm vi vô hạn |
| Kubernetes | Hoãn vô thời hạn | Một Postgres, một Redis, một hàng đợi là đủ ở quy mô mục tiêu |
| Fine-tune model | Hoãn vô thời hạn | R3 |
| Hỗ trợ rộng biến thể board | Hoãn vô thời hạn | R1 sai — ba target, mỗi target một board tham chiếu |

---

# Phần IV — Kiểm chứng

## 7. Định vị cạnh tranh

### 7.1 Bản đồ đối thủ

Gọi tên cụ thể. Không thể suy luận về một đối thủ mà mình không chịu gọi tên.

| Đối thủ | Thế mạnh | Vì sao không lấp được khoảng trống này |
|----|----|----|
| **ESP-Claw** (Espressif) | Hỗ trợ chính hãng, MCP-native, sâu về ESP32 | Một dòng chip. Về cấu trúc không thể coi chip của hãng là một trong nhiều target ngang hàng |
| **XiaoZhi** | Pipeline thoại hoàn chỉnh, cộng đồng lớn | Không có điều phối agent, không có HAL đa nền tảng, không có khái niệm hợp đồng hành động |
| **LiveKit Agents / Pipecat / TEN** | Hạ tầng A/V thời gian thực mạnh | Lấy cloud làm trung tâm. Offline-first phá mô hình hạ tầng của chính họ |
| **LangChain và tương đương** | Hệ sinh thái lớn | Thuần phần mềm, không có trừu tượng phần cứng, không có actuator để bảo vệ |

### 7.2 Ba khác biệt có thể bảo vệ

| # | Khác biệt | Vì sao khó sao chép |
|----|----|----|
| 1 | **Hợp đồng hành động có kiểu + Action CI** | Đòi hỏi ba quyết định kiến trúc ở tuần 1 cùng lúc: sim là target thật, gate là artifact có version, trace là công dân hạng nhất. Ai đã ship mà thiếu chúng thì phải viết lại, không phải thêm vào |
| 2 | **Hợp đồng năng lực HAL trên ba target ngang hàng** | SDK một-chip không cần khái niệm này nên không có. Thêm vào sau là thay đổi kiến trúc, và mâu thuẫn với động cơ bán silicon |
| 3 | **Định dạng gate và trace** | Theo chú thích [2] của tiểu luận: trong lĩnh vực chưa có chuẩn, đề xuất đầu tiên thường thắng bất kể ai đề xuất. Định dạng thắng rồi thì framework thắng theo |

Lưu ý về điều **không** nằm trong bảng: simulator một mình. Nó là đòn bẩy TTFV xuất sắc, nhưng một đối thủ khởi động mới sẽ chọn đúng kiến trúc đó miễn phí sau khi thấy nó hiệu quả. Simulator là điều kiện cần của khác biệt số 1, không phải khác biệt tự thân.

### 7.3 Điểm không cạnh tranh

NeuroEdge không cạnh tranh về giá inference, không cạnh tranh về độ phủ phần cứng, không cạnh tranh với SDK chính hãng ở độ sâu của một dòng chip. Ba mặt trận này thua từ đầu — và theo §1.4, thắng chúng chỉ nên là **lợi ích phụ** của việc thắng ở chiều khác, không bao giờ là mục tiêu.

---

## 8. Rủi ro và giảm thiểu

Bốn rủi ro theo nguồn gốc. Loại trừ lẫn nhau.

### 8.1 Rủi ro phụ thuộc vendor

| | |
|----|----|
| **Nội dung** | Luận điểm sản phẩm dựa vào một model đóng của một vendor mới |
| **Kịch bản** | Đổi giá, đổi điều kiện truy cập, hoặc vendor tự ship framework |
| **Giảm thiểu cấu trúc** | Khung v5.0 đã hạ rủi ro này một bậc: sản phẩm là hợp đồng hành động, model chỉ điền vào ô đánh giá. Đổi model không đổi định vị |
| **Giảm thiểu kỹ thuật** | Interface `SystemOne`/`SystemTwo` từ tuần 1 (§3.6). Fallback cục bộ đã tune ship khi chỉ báo bật |
| **Chỉ báo sớm** | Thay đổi điều khoản API · vendor tuyển kỹ sư framework · vendor công bố SDK thiết bị |

### 8.2 Rủi ro nền tảng phần cứng

| | |
|----|----|
| **Nội dung** | Nhà sản xuất chip phát SDK miễn phí vĩnh viễn để bán silicon |
| **Vì sao không thể đua** | Không thể rẻ hơn miễn phí; họ có động cơ cấu trúc để giữ như vậy |
| **Giảm thiểu** | Đánh từ bên sườn (§1.4): thắng ở chiều kiểm thử được và đa target. Ba target ngang hàng từ Khối 1 là bằng chứng của chiều này |
| **Chỉ báo sớm** | SDK chính hãng thêm lớp điều phối agent · hoặc bắt đầu hỗ trợ chip đối thủ |

### 8.3 Rủi ro biên lợi nhuận

| | |
|----|----|
| **Nội dung** | Bán lại inference là biên mỏng; model vendor có thể nuốt cả mình lẫn khách của mình (chú thích [1] của tiểu luận) |
| **Giảm thiểu** | Trọng tâm doanh thu ở fleet management (§5.2). Inference gần giá vốn — nhưng không miễn phí, để giữ tín hiệu trả tiền |
| **Chỉ báo sớm** | Tỉ trọng doanh thu từ inference vượt fleet |

### 8.4 Rủi ro sao nhãng phạm vi

| | |
|----|----|
| **Nội dung** | Áp lực xây marketplace sớm, hoặc chiều theo yêu cầu doanh nghiệp đầu tiên |
| **Giảm thiểu** | Bốn quy tắc §2 và cổng định lượng §5.5, ghi thành văn bản **trước khi** áp lực xuất hiện |
| **Chỉ báo sớm** | Xuất hiện đề xuất không thuộc R1 hay R2 nhưng vẫn được ưu tiên |

---

## 9. Thước đo thành công

Đo bằng kết quả, không đếm tính năng. Sao GitHub không có trong bảng nào — nó đo người xem, không đo người dùng.

### 9.1 Khối 1 (tháng 2)

| Thước đo | Ngưỡng |
|----|----|
| Time-to-first-value, đo trên 10 người lạ thật | Trung vị dưới 10 phút |
| **Tương đương target** | Cùng một file agent chạy trên `sim`, `linux`, `esp32s3` không sửa dòng nào — khẳng định bằng `neuroedge verify` trong CI |
| **Áp dụng Action CI** | ≥ 50% dự án dùng `neuroedge new` giữ lại và mở rộng test gate mặc định |
| **Chuyển đổi sim → phần cứng** | *[cần chốt ngưỡng]* Tỉ lệ người chạy sim rồi build lên board thật trong 30 ngày. Nếu con số này thấp, cả phễu §1.6 đứt ở bước đầu |
| Khả năng quan sát | Trace hiển thị tỉ lệ System 1/System 2, chi phí từng lượt, mọi quyết định gate |
| Tài sản phân phối | 3 ví dụ chạy được, 1 GIF 15 giây trong README |

GIF không phải hạng mục marketing phụ. Với một dự án OSS phần cứng, nó là kênh phân phối.

### 9.2 Khối 2 và 3 (tháng 6)

| Thước đo | Ngưỡng |
|----|----|
| Độ tin cậy OTA | Một lần đẩy thành công cho > 1.000 thiết bị, 0 thiết bị chết |
| **Ngân sách độ trễ thoại** | *[cần chốt số công khai]* p95 round-trip. Đối thủ đều công bố số; từ chối nêu là né cam kết khó nhất. Xem Phụ lục C.3 |
| Độ trễ gate | p95 dưới `budget.p95_latency_ms` khai báo, trên cả ba target |
| Hiệu quả định tuyến | Tỉ lệ System 1/System 2 đo được và chứng minh cắt chi phí thật |
| **Chia sẻ gate** | Số gate được publish lên registry và được cài bởi người không phải tác giả |
| Doanh thu đầu tiên | Đến từ đơn vị tính fleet, không phải từ inference |

Thước đo cuối quan trọng hơn năm thước đo trên. Nó phân biệt một dự án mã nguồn mở nhiều sao với một công ty.

### 9.3 Khối 4 (tháng 12)

| Thước đo | Ngưỡng |
|----|----|
| Tính toàn vẹn của framework | AURA chạy trên nhánh công khai, không API đặc quyền |
| Bằng chứng dùng lại | Số gate và agent do bên thứ ba publish |
| Tín hiệu liquidity | Tiến độ trên bốn ngưỡng của cổng (§5.5) |
| Giúp người dùng kiếm tiền | Có case study đo được: giảm chuyến đi hiện trường, giảm lô hàng thu hồi, hoặc rút ngắn bring-up board thứ hai (§1.7) |

---

## Phụ lục A — Đối chiếu "Making Startups Powerful"

Tiểu luận (Paul Graham, tháng 9 năm 2026) là **bộ heuristic để sinh ý tưởng**, không phải checklist triển khai. Tác giả nói rõ các phép biến đổi này thường không cho ra gì, và mọi thứ phải phục tùng một ràng buộc duy nhất:

> *"They all have to make things better for the customer. You can't add network effects or make the money flow through you or go full stack just because you'd like to. You can only do these things when the result is better for the customer. Otherwise you won't have any uptake."*

Bảng dưới phân loại theo trạng thái áp dụng — không gán hệ số nhân, vì hệ số nhân là thứ không đo được và tạo cảm giác chắc chắn giả.

| Heuristic | Trạng thái | NeuroEdge làm gì | Tốt hơn cho khách hàng ở chỗ nào |
|----|----|----|----|
| Sở hữu quan hệ khách hàng | **Ngay** | Gateway đứng giữa dev và mọi nhà cung cấp model | Đổi model không phải nạp lại firmware |
| Để tiền chảy qua mình | **Một phần** | Qua gateway, nhưng biên đến từ fleet | Một hoá đơn thay vì năm |
| **Lấy dữ liệu sớm (mẫu Rippling)** | **Ngay** | Đi tới nơi vòng đời dữ liệu bắt đầu: lần đầu một hành động bị đề xuất trong sim | Trace và replay là thứ họ cần dù có NeuroEdge hay không |
| Bán cho khách giai đoạn sớm | **Ngay** | Indie maker ở thiết bị thứ nhất, không phải doanh nghiệp ở thiết bị thứ 500 | Cài được ngay, không qua chu trình mua sắm |
| Có API | **Ngay** | Mọi thứ gọi được qua API và CLI; gate là dữ liệu chứ không phải code | Không bị khoá vào cách dùng mà mình nghĩ ra |
| Hào phóng | **Ngay** | Lõi MIT, registry miễn phí, gate cơ sở miễn phí | Không trả tiền để an toàn |
| **Định nghĩa chuẩn (chú thích [2])** | **Ngay** | Đề xuất định dạng gate và trace cho một lĩnh vực chưa có chuẩn | Mô tả "an toàn khi nào" theo một cách duy nhất |
| Hiệu ứng mạng qua chia sẻ | **Ngay** | Chia sẻ gate — bản khả dụng trước khi có app store | Dùng lại gate người khác đã tune bằng giờ hiện trường thật |
| **Giúp người dùng kiếm tiền** | **Ngay** | Cắt chuyến đi hiện trường, lô hàng thu hồi, thời gian bring-up (§1.7) | Đây là tiền mặt, không phải tiện ích |
| Chơi ván dài | **Xuyên suốt** | Rails xây trước khi có nhu cầu thương mại | Hạ tầng sẵn khi họ cần |
| **Đánh từ bên sườn** | **Xuyên suốt** | Không đánh trực diện SDK chính hãng; thắng ở chiều kiểm thử được | — |
| Đi full-stack | **Khối 4** | AURA, sau khi framework ổn định | Gánh phần khó nhất: trách nhiệm khi thiết bị làm sai |
| Lắng nghe khi người dùng dùng sai | **Là cơ chế đo** | Ngưỡng 4 của cổng liquidity | — |
| App store | **Sau cổng** | Nền xây trước; phần thương mại bị chặn | Store rỗng làm tệ hơn cho người dùng → vi phạm ràng buộc |
| Agent trả tiền cho agent | **Sau cổng** | Bề mặt pháp lý vượt năng lực hấp thụ hiện tại | — |

**Hai điều tiểu luận cảnh báo mà tài liệu này tuân theo:**

1. **Chú thích [1] — dòng token.** Khi token chảy qua mình, câu hỏi là các công ty model có dễ nuốt chửng mình hoặc khách của mình đến mức nào. Đây là lý do trọng tâm doanh thu ở fleet, không ở inference.
2. **Chú thích [4] — bán quá rẻ.** *"If your product is a $10 bill that you sell for $5, your growth rate isn't telling you anything useful."* Inference bán gần giá vốn, không miễn phí.

**Và một chẩn đoán tự áp dụng.** Tiểu luận mô tả dạng thất bại mà bản v3.0 mắc phải:

> *"One way startups' ideas get twisted into knots is by evolving from something else... But with very early stage startups especially, the reason the idea is complicated is often fear. The company is unconsciously cowering by doing something less ambitious than they could. Just y is often, in effect, just stand up straight."*

Bản v3.0 xây sáu thứ cùng lúc. Bản v4.0 cắt xuống còn ba. Bản v5.0 này đi xa hơn một bước: không chỉ cắt, mà **đứng thẳng** — tuyên bố một mệnh đề mà chưa ai tuyên bố, thay vì tuyên bố một phiên bản gọn hơn của mệnh đề mà bốn đối thủ đều đã tuyên bố.

---

## Phụ lục B — Từ điển thuật ngữ

| Thuật ngữ | Định nghĩa |
|----|----|
| **Hợp đồng hành động** | Ràng buộc bắt buộc giữa một hành động vật lý và gate của nó; hành động không chạy nếu gate không pass |
| **Gate** | Artifact có schema, có version, khai báo điều kiện cho phép một hành động vật lý. Là dữ liệu, không phải code |
| **Action CI** | Record phiên thật, replay trên target bất kỳ, khẳng định về hành động — chạy trong pipeline mỗi commit |
| **`.ntrace`** | Định dạng trace: đầu vào, mọi đánh giá gate, mọi lệnh actuator, kèm mốc thời gian. Replay được |
| **Golden** | Chuỗi quyết định tham chiếu cho một trace. Lệch golden → CI đỏ |
| **Fail-closed** | Gate không đánh giá được → hành động bị chặn. Mặc định của mọi gate |
| **HAL** | Lớp trừu tượng phần cứng; ở đây là hợp đồng năng lực hai chiều |
| **Hợp đồng năng lực** | Thiết bị khai báo năng lực, agent khai báo yêu cầu, lệch nhau báo lỗi lúc build |
| **Định luật tương đương target** | Cùng một file agent chạy trên `sim`, `linux`, `esp32s3` không sửa dòng nào |
| **System 1 / System 2** | Model quyết định có cấu trúc, nhanh / model suy luận, chậm. Cả hai sau interface thay thế được |
| **TTFV** | Time-to-first-value — từ khi cài đến kết quả hữu ích đầu tiên |
| **Rails** | Hạ tầng nền xây sớm, chưa mang tính thương mại |
| **Cổng liquidity** | Bốn ngưỡng định lượng chặn việc mở marketplace và pay |
| **Fleet plane** | Nhóm năng lực quản lý đội thiết bị ngoài hiện trường |
| **MCP** | Model Context Protocol — chuẩn kết nối AI với công cụ |

---

## Phụ lục C — Quyết định còn mở

Bốn điều tài liệu này **chưa** chốt. Ghi ra để không bị nhầm thành giả định đã quyết.

### C.1 Phạm vi Khối 1 so với thời hạn 2 tháng

Nâng `linux` lên hạng nhất và thêm Action CI làm tăng phạm vi Khối 1 so với v4.0. Ba lựa chọn:

| Lựa chọn | Đánh đổi |
|----|----|
| Giữ 2 tháng, cắt bớt | Ứng viên cắt: chính sách định tuyến khai báo được (hard-code `fast_first`), MCP client, ví dụ thứ 2 và 3 |
| Giãn sang 3–4 tháng | Mọi khối sau trượt theo, vì mũi tên là mũi tên cho phép |
| Tách Khối 1 thành 1a (sim + linux + gate + CI) và 1b (esp32s3 + voice đầy đủ) | Giữ nhịp phát hành, nhưng `esp32s3` chậm làm yếu luận điểm tương đương target |

**Khuyến nghị:** lựa chọn thứ ba. Định luật tương đương chứng minh được bằng hai target trước, target thứ ba củng cố.

### C.2 Thời điểm ship fallback model cục bộ

Interface ở tuần 1 là đã chốt (R2, chi phí một ngày). Fallback cục bộ *đã tune* tốn vài tuần và là bảo hiểm cho rủi ro mà chỉ báo sớm ở §8.1 chưa bật. Đề xuất: giữ ở §6 cho tới khi một chỉ báo bật, rồi ship trong 2 tuần.

### C.3 Ngân sách độ trễ công khai

§9.2 để trống. Cần chốt trước khi phát hành Khối 1, vì nó là spec sản phẩm chứ không phải chỉ số nội bộ. Ba con số cần chốt: p95 wake→phản hồi đầu tiên, p95 đánh giá gate, p95 round-trip trọn lượt — mỗi con số trên cả ba target.

### C.4 Ngưỡng chuyển đổi sim → phần cứng

§9.1 để trống. Đây là con số quyết định xem phễu §1.6 có hoạt động không. Chưa có cơ sở để đặt ngưỡng trước khi có 100 người dùng thật; đề xuất đo từ ngày đầu, đặt ngưỡng ở tháng 3.

---

*Hết tài liệu*
