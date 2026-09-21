# NeuroEdge

## Hợp đồng hành động có kiểu cho Physical AI

**Phiên bản:** 5.0
**Ngày:** 20 tháng 9, 2026
**Đối tượng đọc:** Đội ngũ sản phẩm · Đối tác phần cứng · Nhà phát triển nền tảng
**Phạm vi tài liệu:** Định vị sản phẩm · Kiến trúc · API · Lộ trình · Ranh giới · Thước đo
**Ngoài phạm vi:** Bảng giá · Mô hình tài chính · Kế hoạch gọi vốn

---

## Mục lục

**Phần I — Luận điểm**

1. [Bối cảnh và thời điểm](#1-bối-cảnh-và-thời-điểm)
2. [Vấn đề](#2-vấn-đề)
3. [Luận điểm sản phẩm](#3-luận-điểm-sản-phẩm)
4. [Nguyên tắc quyết định](#4-nguyên-tắc-quyết-định)

**Phần II — Sản phẩm**

5. [Kiến trúc sản phẩm](#5-kiến-trúc-sản-phẩm)
6. [API sản phẩm](#6-api-sản-phẩm)
7. [An toàn và bảo mật mặc định](#7-an-toàn-và-bảo-mật-mặc-định)
8. [Mặt phẳng thương mại](#8-mặt-phẳng-thương-mại)
9. [AURA — sản phẩm tham chiếu](#9-aura--sản-phẩm-tham-chiếu)

**Phần III — Thực thi**

10. [Lộ trình sản phẩm](#10-lộ-trình-sản-phẩm)
11. [Ranh giới sản phẩm](#11-ranh-giới-sản-phẩm)

**Phần IV — Kiểm chứng**

12. [Định vị cạnh tranh](#12-định-vị-cạnh-tranh)
13. [Rủi ro và giảm thiểu](#13-rủi-ro-và-giảm-thiểu)
14. [Thước đo thành công](#14-thước-đo-thành-công)

**Phụ lục**

- [A — Đặc tả hợp đồng năng lực HAL](#phụ-lục-a--đặc-tả-hợp-đồng-năng-lực-hal)
- [B — Đặc tả định dạng gate v1](#phụ-lục-b--đặc-tả-định-dạng-gate-v1)
- [C — Đặc tả định dạng `.ntrace`](#phụ-lục-c--đặc-tả-định-dạng-ntrace)
- [D — Nền tảng phần cứng, model và tích hợp](#phụ-lục-d--nền-tảng-phần-cứng-model-và-tích-hợp)
- [E — Đối chiếu "Making Startups Powerful"](#phụ-lục-e--đối-chiếu-making-startups-powerful)
- [F — Từ điển thuật ngữ](#phụ-lục-f--từ-điển-thuật-ngữ)
- [G — Quyết định còn mở](#phụ-lục-g--quyết-định-còn-mở)

---

## 0. Tóm tắt điều hành

### Bối cảnh

Physical AI đang ở điểm hội tụ của ba lực: phần cứng biên đã rẻ tới mức phổ cập, SLM đã chạy được trên thiết bị, và MCP đang trở thành chuẩn kết nối AI với công cụ. Một nhà phát triển muốn dựng một voice agent cơ bản vẫn phải tự ghép sáu năng lực rời rạc qua các SDK không tương thích, mất từ hai đến bốn tuần chỉ để có bản chạy thử đầu tiên.

### Vấn đề

Mô tả khoảng trống đó là "thiếu một framework" thì đúng nhưng nông. Đó là khoảng trống mà **bốn đối thủ đều có thể lấp bằng cách thêm tính năng** — và ba trong bốn có nhiều nguồn lực hơn.

Khoảng trống thật nằm sâu hơn một tầng: **không ai kiểm thử được hành động vật lý trước khi nó xảy ra ngoài hiện trường.** Một agent chatbot trả lời sai thì người dùng đọc lại. Một agent vật lý quyết định sai thì servo đã quay, khoá đã mở, motor đã chạy. Toàn ngành phần mềm có unit test, integration test, CI. Physical AI có: cắm board vào, nói thử, hy vọng.

### Câu hỏi

Cấu phần nào trong thế giới hoàn hảo của người xây agent vật lý mà NeuroEdge có thể tự biến mình thành?

### Trả lời

> **NeuroEdge làm cho mọi hành động vật lý của agent trở nên có kiểu, có version, kiểm thử được trong CI, và chạy y hệt nhau trên ba target — từ laptop tới thiết bị biên.**

Bốn thành phần lõi mở mã (MIT), một mặt phẳng thương mại duy nhất, một cổng định lượng chặn mọi thứ còn lại.


|                                   | Nội dung                                                                                                             |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Lõi mở mã (MIT)**               | HAL hợp đồng năng lực · Action Contract Engine · Voice pipeline · Ba target ngang hàng (`sim` · `linux` · `esp32s3`) |
| **Mặt phẳng thương mại duy nhất** | Hosted gateway (inference plane) + Device fleet management (fleet plane)                                             |
| **Hoãn sau cổng liquidity**       | Marketplace · Pay · Certification                                                                                    |


### Năm quyết định định hình toàn bộ sản phẩm


| #   | Quyết định                                                                                                                                                     | Hệ quả                                      | Mục          |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- | ------------ |
| 1   | **Hành động vật lý là hợp đồng có kiểu, không phải lời gọi hàm.** Mọi lệnh tới actuator đi qua một gate có version, khai báo được, chia sẻ được                | Không có đường vòng tới thế giới vật lý     | §5.5, §6.5   |
| 2   | **Ba target ngang hàng.** `sim`, `linux`, `esp32s3` là ba implementation của cùng một HAL — không target nào là "phụ"                                          | Cùng một file agent chạy trên cả ba         | §5.2         |
| 3   | **Bán fleet, không bán token.** Bán lại inference là biên mỏng và là cuộc đua không thắng được với model vendor                                                | Trọng tâm sản phẩm thương mại ở fleet plane | §8           |
| 4   | **Model là thành phần thay thế được, không phải luận điểm.** System One và System Two nằm sau interface từ tuần 1                                              | Đổi model không đổi định vị                 | §5.6, §13.1  |
| 5   | **Marketplace hoãn phần thương mại, giữ nguyên phần nền.** Registry, manifest, metering, permission model ship sớm vì rẻ, hữu ích ngay, và không retrofit được | Hiệu ứng mạng khả dụng trước khi có store   | §10.3, §10.5 |


### Một câu cho mỗi nhóm người đọc


| Người đọc                          | Câu                                                                                                      |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **Nhà phát triển**                 | Viết agent trên laptop, kiểm thử hành động vật lý trong CI, deploy lên con chip $5 mà không sửa một dòng |
| **Người vận hành fleet**           | Biết thiết bị nào đang làm gì, sửa từ xa, cập nhật theo đợt mà không làm chết thiết bị nào               |
| **Đối tác phần cứng**              | Một lớp agent chạy trên board của bạn mà không khoá khách hàng vào một dòng chip                         |
| **Người chịu trách nhiệm an toàn** | Mỗi hành động vật lý có một điều kiện cho phép đọc được, review được, và có log chứng minh nó đã chạy    |


---

# Phần I — Luận điểm

## 1. Bối cảnh và thời điểm

### 1.1 Ba lực hội tụ


| Lực                             | Bằng chứng                                                                                         | Hệ quả với sản phẩm                                         |
| ------------------------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| **Phần cứng biên phổ cập**      | ESP32-S3 \~$5 · Raspberry Pi 5 ~$80 · Jetson Orin Nano \~$150–500, đều có silicon đủ cho tác vụ AI | Số điểm cuối tiềm năng tính bằng tỉ, nhưng cực kỳ phân mảnh |
| **SLM chạy được trên thiết bị** | Qwen 2.5-3B, Phi-3 Mini, Llama 3.2 suy luận được ở biên                                            | Bỏ được phụ thuộc cloud cho lớp quyết định nhanh            |
| **Chuẩn kết nối công cụ**       | MCP trở thành chuẩn de-facto cho AI gọi công cụ                                                    | Agent liên thông được với nhau và với hệ thống sẵn có       |


### 1.2 Quy mô cơ hội

```
TAM — Tổng thị trường có thể phục vụ
├─ Nền tảng AIoT toàn cầu
├─ Phần mềm robotics / Physical AI
└─ Công cụ cho nhà phát triển Edge AI

SAM — Phần phục vụ được bằng sản phẩm này
├─ Công cụ phát triển và dịch vụ vận hành fleet
└─ Phân phối lại năng lực an toàn (gate, agent) giữa các đội

SOM — Phần chiếm được trong 5 năm
└─ Đội ngũ ship phần cứng có agent, quy mô 10–10.000 thiết bị mỗi đội
```

**Cách đọc bảng trên:** quy mô thị trường không phải luận điểm của tài liệu này. Nó chỉ xác nhận rằng lớp hạ tầng đang bàn tới đủ lớn để nuôi một sản phẩm độc lập. Luận điểm nằm ở §2 và §3.

### 1.3 Vì sao là bây giờ


| #   | Điều kiện                                                                                     | Trạng thái                                                      |
| --- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| 1   | Có một hạng model quyết định có cấu trúc, nhanh và rẻ, đủ để đặt vào đường dẫn thời gian thực | Đã có, và đang có thêm nhà cung cấp                             |
| 2   | Lĩnh vực chưa có chuẩn cho việc mô tả "hành động này an toàn khi nào"                         | Chưa ai đề xuất                                                 |
| 3   | Các SDK hiện có đã đủ trưởng thành để bọc lại, không cần viết lại                             | Wake-word, VAD, AEC, STT, TTS đều có bản mã nguồn mở đủ tốt     |
| 4   | Đội ngũ phần cứng đang trả tiền thật cho OTA và quản lý fleet                                 | Đây là hành vi chi tiêu đã tồn tại, không phải nhu cầu suy diễn |


Trong một lĩnh vực chưa có chuẩn, **đề xuất đầu tiên thường thắng bất kể ai đề xuất.** Cửa sổ này đóng khi một bên khác công bố định dạng của họ trước.

---

## 2. Vấn đề

### 2.1 Bốn mặt phân mảnh


| #   | Mặt                        | Biểu hiện                                                                                            | Chi phí thực tế                           |
| --- | -------------------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| 1   | **Đa dạng phần cứng**      | Hàng chục biến thể board, mỗi hãng một SDK riêng, không có lớp trừu tượng dùng chung                 | Mỗi board mới là một đợt bring-up từ đầu  |
| 2   | **Chiều sâu tích hợp**     | Một voice agent chạm vào sáu chuyên môn: nhúng, audio, speech, model ngôn ngữ, TTS, quản lý thiết bị | Không kỹ sư nào thạo cả sáu               |
| 3   | **Độ trễ ra thị trường**   | 2–4 tuần cho bản prototype, 3–6 tháng cho bản sản xuất                                               | Cửa sổ thị trường đóng trước khi kịp ship |
| 4   | **Phụ thuộc nhà cung cấp** | SDK cloud khoá chặt, chi phí chuyển đổi sau khi đã deploy rất cao                                    | Quyết định hôm nay khoá luôn ba năm sau   |


Bốn mặt này là thật. Nhưng chúng là **vấn đề ai cũng nhìn thấy**, và vì thế là vấn đề mà bốn đối thủ ở §12.1 đều đang tiến tới lấp bằng cách thêm tính năng.

### 2.2 Khoảng trống thật: hành động vật lý không kiểm thử được

Đây là khoảng trống chưa ai chiếm.


|                                                  | Phần mềm thuần             | Physical AI hôm nay                            |
| ------------------------------------------------ | -------------------------- | ---------------------------------------------- |
| Kiểm thử đơn vị                                  | Có                         | Chỉ cho phần logic không chạm phần cứng        |
| Kiểm thử tích hợp                                | Có                         | Không — cần board thật, người thật, phòng thật |
| Chạy trong CI mỗi commit                         | Có                         | Không                                          |
| Tái hiện một sự cố hiện trường                   | Có — log, replay, debugger | Không — kỹ sư lái xe tới nơi                   |
| Biết một thay đổi prompt có phá vỡ an toàn không | —                          | Không có cách nào ngoài thử tay                |


Ba câu hỏi mà hôm nay không công cụ nào trả lời được:

1. Đổi prompt xong, agent còn từ chối mở khoá cho người chưa xác thực không?
2. Đổi từ model A sang model B, có kịch bản an toàn nào hồi quy không?
3. Ba target có cho cùng một quyết định trên cùng một đầu vào không?

**Hệ quả kinh doanh của việc không trả lời được:** lô hàng bị thu hồi vì lỗi logic phát hiện muộn, chuyến đi hiện trường để sửa một thiết bị, đợt OTA làm chết cả lô, và ba tháng bring-up cho board thứ hai.

### 2.3 Tín hiệu từ thị trường


| Tín hiệu                                                            | Diễn giải                                                              |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Các dự án voice agent trên ESP32 thu hút hàng chục nghìn sao GitHub | Nhu cầu của nhà phát triển là thật và đang không được phục vụ đủ       |
| Hãng chip tự phát hành framework agent                              | Ngành đã thừa nhận cần một lớp framework                               |
| Các thiết bị AI hệ sinh thái đóng lần lượt dừng lại                 | Hệ sinh thái nhà phát triển là yếu tố quyết định, không phải phần cứng |
| Đội ngũ phần cứng đã trả tiền cho nền tảng OTA                      | Có sẵn hành vi chi tiêu để bám vào                                     |


---

## 3. Luận điểm sản phẩm

### 3.1 Chạy ngược ràng buộc: thế giới hoàn hảo của khách hàng

> *"What would the perfect world look like, from the customer's point of view? If there's a component of that world that the startup could transform itself into, it probably should."*

Thế giới hoàn hảo của người xây agent vật lý:


| #   | Trong thế giới hoàn hảo                                                | Hôm nay                                   |
| --- | ---------------------------------------------------------------------- | ----------------------------------------- |
| 1   | Viết agent, chạy thử ngay, không cần mua gì                            | Chặn bởi việc chờ board về                |
| 2   | Biết chắc agent không làm điều nguy hiểm — **trước khi** nạp firmware  | Biết sau khi thiết bị đã ở nhà khách hàng |
| 3   | Đổi prompt, đổi model, chạy lại toàn bộ kịch bản an toàn trong 30 giây | Thử tay vài ca, cầu trời                  |
| 4   | Cùng một file agent chạy trên laptop, trên RPi, trên con chip $5       | Ba codebase                               |
| 5   | Sửa một thiết bị lỗi ngoài hiện trường từ máy của mình                 | Lái xe tới nơi                            |


Cấu phần NeuroEdge tự biến mình thành là **số 2 và số 3** — hai dòng duy nhất mà không đối thủ nào đang phục vụ. Số 1 và số 4 là điều kiện cần để số 2 và số 3 tồn tại. Số 5 là nơi có doanh thu.

### 3.2 Mệnh đề trung tâm

Bốn tài sản kỹ thuật, khi ráp lại, cho ra một hạng mục chưa tồn tại:

```
Schema gate có version          ─┐
Record phiên thật trên board    ─┤
Replay trong sim, bit-for-bit   ─┼─→  ACTION CI
Trace đầy đủ mỗi quyết định     ─┘    Kiểm thử hành động vật lý
                                       trong pipeline, mỗi commit
```

Mệnh đề không phải **"hai bộ não"** — đó là kiến trúc của một thời điểm, và sẽ tụt xuống thành chi tiết triển khai nếu decoding có ràng buộc trở thành tính năng chuẩn của model lớn.

Mệnh đề là: **mọi hành động vật lý đều đi qua một hợp đồng có kiểu, kiểm thử được** — đúng bất kể ai lấp vào ô System 1.

Đây là thứ không sao chép được bằng cách thêm tính năng, vì nó đòi hỏi đúng ba quyết định kiến trúc ở tuần 1: **sim là target thật, gate là artifact có version, trace là công dân hạng nhất.** Ai đã ship xong mà không có chúng thì phải viết lại.

### 3.3 Bốn vị thế thượng nguồn

> *"Upstream is almost always good, whether it's with money or user relationship or customer stage or data."*

Đây là nguyên lý tổ chức duy nhất của chiến lược sản phẩm. Bốn vị thế, loại trừ lẫn nhau, bao phủ đủ:


| Thượng nguồn             | NeuroEdge chiếm bằng cách                                                                                                       | Ship ở |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------- | ------ |
| **Quan hệ khách hàng**   | Gateway đứng giữa nhà phát triển và mọi nhà cung cấp model. Đổi model mà không đổi code, không nạp lại firmware                 | Khối 2 |
| **Dòng tiền**            | Mọi lượt gọi model đi qua một endpoint, một credential, một hoá đơn                                                             | Khối 2 |
| **Giai đoạn khách hàng** | Bắt đầu từ indie maker ở thiết bị thứ nhất, không phải doanh nghiệp ở thiết bị thứ 500. Doanh thu tăng theo số thiết bị họ ship | Khối 1 |
| **Dữ liệu**              | Đi tới nơi **vòng đời dữ liệu bắt đầu** — với agent vật lý, đó là lần đầu một hành động bị đề xuất trong simulator              | Khối 1 |


Vị thế thứ tư bị đánh giá thấp nhất. Rippling viết phần mềm onboarding không phải vì thị trường onboarding hấp dẫn, mà vì đó là nơi dữ liệu nhân sự sinh ra — và vì có nhiều thứ đặt cược hơn là thị trường onboarding, họ làm nó **tốt hơn mức cần thiết rất nhiều**, nên nó lan nhanh.

Tương đương ở đây: **simulator và định dạng trace phải tốt hơn mức cần thiết rất nhiều.** Không phải vì simulator là thị trường, mà vì mọi quyết định của mọi agent trên mọi thiết bị đều đi qua đó trước tiên. Ai sở hữu định dạng trace sẽ sở hữu câu hỏi "agent nào đang làm gì, và có an toàn không".

### 3.4 Đánh từ bên sườn, không đánh trực diện

> *"You'd have to do it by coming in from the side — by somehow making them irrelevant, rather than by frontal attack. Then you wouldn't depend on beating them to succeed; it would be an ancillary benefit of winning in another dimension."*

Chiều khác đó là **tính kiểm thử được của hành động, cắt ngang mọi loại phần cứng.**

Một SDK chính hãng về cấu trúc không thể đi vào chiều này, vì nó đòi hỏi coi chip của hãng chỉ là một trong nhiều target ngang hàng. Không hãng chip nào làm điều đó.

Đây là lý do `linux` phải ở hạng nhất ngay từ đầu: **target thứ hai chạy thật chính là bằng chứng rằng chiều này tồn tại.** Không có nó, sản phẩm chỉ là một framework một-board, đánh trực diện SDK chính hãng ngay trên sân của họ — mặt trận đã thua từ đầu.

### 3.5 Vì sao mở mã là kênh phân phối duy nhất khả thi

Mã nguồn mở chỉ hoạt động như kênh phân phối khi **người pull repo về chính là người ra quyết định mua**. Bốn thuộc tính:


| Thuộc tính            | Biểu hiện                                                              |
| --------------------- | ---------------------------------------------------------------------- |
| Đúng tầng             | Hạ tầng, không phải ứng dụng nghiệp vụ                                 |
| Chưa có chuẩn         | Physical AI chưa có framework chuẩn hoá; đề xuất đầu tiên thường thắng |
| Demo lan truyền được  | Video nói chuyện với con chip và servo quay                            |
| Người cài = người mua | Nhà phát triển quyết định trong vài phút, không qua chu trình mua sắm  |


**Chuẩn mà NeuroEdge đề xuất không phải framework, mà là định dạng gate và trace.** Framework thì ai cũng viết được cái khác. Định dạng mà mọi người dùng để mô tả "hành động này an toàn khi nào" thì chỉ có một cái thắng.

### 3.6 Vòng lặp giá trị

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

Hai mắt xích quan trọng nhất:

1. **Bước 2 và 3** là nơi sản phẩm tạo ra giá trị mà không ai thay thế được.
2. **Bước 6** là hiệu ứng mạng khả dụng *trước* marketplace. Bản deluxe của hiệu ứng mạng là app store, nhưng khi chưa có cách trực tiếp, *"you can often induce network effects by letting your users share something"*. Gate là thứ để chia sẻ: miễn phí, không mở bề mặt pháp lý, và làm sản phẩm tốt hơn cho cả người cho lẫn người nhận.

### 3.7 Giúp người dùng kiếm tiền

> *"Few things make you more powerful than that... they're (a) quick to adopt your product and (b) will pay a lot for it."*

Đường dẫn ở đây là trực tiếp và đếm được:


| Chi phí thật của người ship phần cứng       | NeuroEdge cắt bằng                         |
| ------------------------------------------- | ------------------------------------------ |
| Thu hồi lô hàng vì lỗi logic phát hiện muộn | Action CI bắt lỗi trước khi build firmware |
| Cử người tới hiện trường sửa một thiết bị   | Log từ xa + config từ xa (§8.2)            |
| Firmware hỏng làm chết cả đợt rollout       | OTA theo đợt, tự rollback                  |
| Ba tháng bring-up cho board thứ hai         | Cùng agent code, đổi một cờ `--target`     |


Đây là bốn dòng đưa vào README, không phải bốn dòng đưa vào tài liệu nội bộ.

---

## 4. Nguyên tắc quyết định

Bốn quy tắc, áp dụng cho mọi đề xuất tính năng. Loại trừ lẫn nhau, bao phủ đủ.


| #      | Quy tắc                     | Câu hỏi kiểm tra                                                              |
| ------ | --------------------------- | ----------------------------------------------------------------------------- |
| **R1** | Phục vụ time-to-first-value | Có rút ngắn đường từ `pip install` đến câu trả lời đầu tiên không?            |
| **R2** | Không thể thêm vào sau      | Nếu bỏ qua bây giờ, 12 tháng nữa có retrofit được không? Nếu không → làm ngay |
| **R3** | Có người dùng thật đang chờ | Đã có ai yêu cầu, hay chỉ là suy diễn về nhu cầu tương lai?                   |
| **R4** | Không mở bề mặt pháp lý     | Có kéo theo giấy phép, tuân thủ, hoặc trách nhiệm tài chính không?            |


**Cách dùng:** R1 hoặc R2 đúng → làm. R3 sai → hoãn. R4 đúng → chặn tuyệt đối cho tới sau cổng liquidity (§10.5).

Ví dụ áp dụng:


| Đề xuất                                      | Phán quyết                                                                                   |
| -------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Gate là artifact có version, không phải code | R2 đúng — đổi sau là đổi kiến trúc → **làm ngay**                                            |
| Metering theo lượt gọi agent                 | R2 đúng → **làm ngay** dù chưa ai cần                                                        |
| `linux` là target hạng nhất                  | R1 và R2 đều đúng — là môi trường dev, và là bằng chứng của hợp đồng năng lực → **làm ngay** |
| Dashboard BI tuỳ biến                        | R1 sai, R3 sai → **hoãn vô thời hạn**                                                        |
| Agent-to-agent pay                           | R4 đúng → **chặn**                                                                           |


---

# Phần II — Sản phẩm

## 5. Kiến trúc sản phẩm

### 5.1 Sơ đồ lớp

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

Năm lớp trên là mã nguồn mở MIT. **Không có lớp cloud nào trong sơ đồ** — gateway và fleet là dịch vụ nằm ngoài, gọi qua interface thay thế được. Một agent NeuroEdge chạy trọn vẹn khi không có mạng và không có tài khoản.

### 5.2 L0 — Ba target ngang hàng

**Định luật tương đương target:** ba target là ba implementation của cùng một HAL. Cùng một file agent chạy trên cả ba, không sửa một dòng. Vi phạm định luật này làm hỏng toàn bộ luận điểm Action CI.


|                         | `sim`                                                | `linux`                                   | `esp32s3`                       |
| ----------------------- | ---------------------------------------------------- | ----------------------------------------- | ------------------------------- |
| **Hạng**                | Hạng nhất                                            | Hạng nhất                                 | Hạng nhất                       |
| **Vai trò**             | Vòng lặp dev, CI mỗi commit                          | Sản xuất trên RPi / x86 / gateway tại chỗ | Sản xuất trên thiết bị biên     |
| **Chạy trong CI**       | Mọi PR                                               | Mọi PR                                    | Nightly trên board thật         |
| **Mô phỏng được**       | Cảm biến giả, servo ảo, mạng chập chờn               | Phần cứng thật, tài nguyên rộng           | Phần cứng thật, tài nguyên chật |
| **Không mô phỏng được** | AEC phòng vang, beamforming mic array, áp lực bộ nhớ | Ràng buộc bộ nhớ của MCU                  | —                               |


#### Vì sao `linux` phải ở hạng nhất ngay từ Khối 1


| #   | Lý do                                                                                                                                                                                             | Quy tắc |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| 1   | **Đây là bằng chứng của hợp đồng năng lực.** Một HAL với đúng một target thật là một API, không phải một hợp đồng. Moat đa nền tảng (§12.2) không tồn tại cho tới khi có target thứ hai chạy thật | R2      |
| 2   | **Đây là chiều "đánh từ bên sườn" (§3.4).** SDK chính hãng về cấu trúc không thể coi chip của hãng là một trong nhiều target ngang hàng                                                           | R2      |
| 3   | **Chi phí biên gần bằng không.** Linux đã là môi trường dev và môi trường CI; phần lớn code đường dẫn `sim` dùng lại nguyên vẹn                                                                   | R1      |
| 4   | **Phần lớn dự án Physical AI thật hiện nay chạy ở lớp RPi**, không phải MCU — đây là nơi người dùng thật đang chờ                                                                                 | R3      |
| 5   | **Là đường thoát khi ESP32-S3 chật.** Nếu bộ nhớ không đủ, `linux` gánh mà không cần đổi kiến trúc                                                                                                | R2      |


**Ba target, không bốn.** Jetson, Matter, HomeKit vẫn hoãn (§11). Ba là số nhỏ nhất chứng minh được định luật tương đương: một ảo, một rộng, một chật.

### 5.3 L1 — HAL, hợp đồng năng lực

**Nguyên tắc thiết kế:** HAL không phải mẫu số chung nhỏ nhất giữa các loại phần cứng. Nó là hợp đồng hai chiều — thiết bị khai báo năng lực, agent khai báo yêu cầu, và lệch nhau bị phát hiện **lúc build**.

Năm nguyên thủy, đủ cho một voice agent và không hơn:


| Nguyên thủy   | Vai trò                          | Ví dụ phần cứng                            |
| ------------- | -------------------------------- | ------------------------------------------ |
| `audio.in`    | Mic, luồng khung PCM             | Mic array I2S, USB mic, file WAV trong sim |
| `audio.out`   | Loa                              | I2S DAC, ALSA, thiết bị null trong sim     |
| `digital.out` | GPIO, servo, relay               | Chân khoá cửa, đèn, motor                  |
| `sensor.read` | Nhiệt độ, chuyển động, chạm, IMU | I2C/SPI sensor, giá trị kịch bản trong sim |
| `display`     | Màn hình, đèn báo trạng thái     | SPI LCD, HDMI, khung ảo trong sim          |


Đặc tả đầy đủ ở Phụ lục A. Cụ thể hoá bằng code ở §6.2–§6.3, và bằng thông báo lỗi lúc build ở §6.9.

### 5.4 L2 — Perception &amp; action

**Nguyên tắc:** bọc lại, không tự viết. Wake-word, VAD, AEC, STT, TTS đều đã có bản mã nguồn mở đủ tốt.

Giá trị thật nằm ở **máy trạng thái hội thoại** — phần ai cũng làm sai:


| Ca khó                                    | Vì sao khó                                                                |
| ----------------------------------------- | ------------------------------------------------------------------------- |
| Barge-in — người dùng ngắt lời giữa chừng | Phải dừng TTS, huỷ generation đang chạy, và không mất ngữ cảnh lượt trước |
| Xử lý im lặng và kết thúc lượt nói        | Ngưỡng cố định thì hoặc cắt lời người nói chậm, hoặc chờ quá lâu          |
| Phát partial trước khi câu hoàn chỉnh     | Giảm độ trễ cảm nhận, nhưng phải rút lại được khi model đổi ý             |
| Phục hồi khi STT trả về rỗng hoặc nhiễu   | Không được im lặng, không được hỏi lại vô hạn                             |


Bốn ca này là lý do máy trạng thái hội thoại tốn ba tuần để làm đúng, và là lý do nó nằm trong lõi thay vì để mỗi người tự ghép lại một lần nữa.

### 5.5 L3 — Action Contract Engine

Đây là IP cốt lõi. Bốn trách nhiệm, loại trừ lẫn nhau:


| #   | Trách nhiệm           | Nội dung                                                                                                          |
| --- | --------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 1   | **Thi hành hợp đồng** | Mọi lệnh tới actuator đi qua gate tương ứng. Không có đường vòng — HAL từ chối lệnh không kèm gate đã pass        |
| 2   | **Định tuyến model**  | Chính sách khai báo được: truy vấn nào xuống System 1, ngưỡng confidence nào leo lên System 2                     |
| 3   | **Xử lý suy giảm**    | Timeout, fallback provider, chế độ local-only. Mặc định của mọi gate là `fail: closed`                            |
| 4   | **Phát trace**        | Mỗi lượt sinh một trace đầy đủ, định dạng ổn định, replay được: độ trễ và chi phí từng chặng, mọi quyết định gate |


#### Vì sao gate là artifact chứ không phải code

Nếu gate là hàm Python, nó không chia sẻ được, không version được, không review được bởi người không đọc code, và không bán được. Nếu gate là file có schema, có version, có `extends` — nó trở thành:


| Vai trò                                          | Ở đâu                          |
| ------------------------------------------------ | ------------------------------ |
| Đơn vị kiểm thử                                  | Action CI (§6.7)               |
| Đơn vị chia sẻ → hiệu ứng mạng trước marketplace | §3.6                           |
| Đơn vị review an toàn cho người không phải dev   | Khách hàng doanh nghiệp về sau |
| Ứng viên hàng hoá của marketplace                | §10.6                          |


Một quyết định định dạng, bốn lợi ích. Đây là mẫu R2 điển hình: gần như miễn phí ở tuần 1, gần như không thể retrofit ở tháng 12.

### 5.6 Lớp trừu tượng model

**Quyết định kiến trúc bắt buộc từ tuần 1.** Model quyết định có cấu trúc nằm sau interface `SystemOne`; model suy luận nằm sau `SystemTwo`. Cả hai đều có đường dẫn cục bộ khai báo được.


|                        |                                                                                                          |
| ---------------------- | -------------------------------------------------------------------------------------------------------- |
| **Rủi ro**             | Nếu luận điểm sản phẩm dựa vào một model đóng của một nhà cung cấp, nhà cung cấp đó nắm số phận sản phẩm |
| **Kịch bản xấu**       | Đổi giá, đổi điều kiện truy cập, hoặc nhà cung cấp tự ship framework cạnh tranh                          |
| **Chi phí phòng ngừa** | *Interface*: một ngày. *Fallback cục bộ đã tune*: vài tuần                                               |
| **Quyết định**         | Ship interface ở tuần 1 (R2). Fallback cục bộ ship khi chỉ báo sớm ở §13.1 bật — xem Phụ lục G.2         |


Dưới khung hợp đồng hành động, đây không phải rủi ro tồn vong. Sản phẩm là hợp đồng; model chỉ là thứ điền vào ô đánh giá của gate. **Đổi model không đổi định vị.**

#### Hai nguyên thủy mà lớp `SystemOne` yêu cầu


| Nguyên thủy | Trả về                                                  | Dùng trong gate             |
| ----------- | ------------------------------------------------------- | --------------------------- |
| `bool`      | Xác suất mệnh đề đúng, kèm confidence                   | `guest_authenticated: true` |
| `level`     | Điểm trên thang có thứ tự, kèm phân phối                | `risk: { lte: low }`        |
| `choice`    | Lựa chọn trong tập đã khai báo, kèm xác suất từng nhánh | định tuyến intent           |


Bất kỳ nhà cung cấp nào hiện thực được ba nguyên thủy này đều cắm vào được. Đây là ranh giới thay thế được, và nó nằm ở đúng một chỗ.

### 5.7 Trục xuyên lớp — Action CI

**Nguyên tắc thiết kế quan trọng nhất: simulator là một target thật, không phải mock.**

Nếu sim là một đường code riêng, nó sẽ lệch khỏi phần cứng trong khoảng sáu tuần và trở thành đồ chơi. Sim là implementation của đúng HAL đó, chạy đúng agent code đó.

Đó là điều kiện cần. Điều kiện đủ là bốn thành phần ráp lại:


| Thành phần | Nội dung                                                                                                                       |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Record** | Ghi phiên thật trên board ra file `.ntrace`: audio vào, đọc cảm biến, mọi đánh giá gate, mọi lệnh actuator, kèm mốc thời gian  |
| **Replay** | Phát lại `.ntrace` trên bất kỳ target nào. Cùng đầu vào → cùng chuỗi quyết định, so được từng bit                              |
| **Assert** | Thư viện test khẳng định về hành động: *bị chặn*, *chặn bởi gate nào*, *leo thang tới đâu*, *chân nào không bao giờ được kích* |
| **Golden** | Chuỗi quyết định tham chiếu. Đổi prompt hoặc đổi model làm lệch golden → CI đỏ                                                 |


Ba câu hỏi ở §2.2 được trả lời trong 30 giây, trên máy của nhà phát triển, không cần chạm vào phần cứng.

**Khoảng cách với thực tế phải nói thẳng trong docs:** sim không mô phỏng AEC trong phòng vang, beamforming của mic array, wifi chập chờn, và áp lực bộ nhớ trên thiết bị biên. Đổi lại, `--target esp32s3` cách đúng một lệnh, và mọi thứ *quyết định được* đều kiểm thử được.

---

## 6. API sản phẩm

Với một framework, API surface chính là sản phẩm. Mục này định nghĩa nó.

### 6.1 Năm nguyên tắc thiết kế API


| #   | Nguyên tắc                                     | Hệ quả                                                         |
| --- | ---------------------------------------------- | -------------------------------------------------------------- |
| 1   | **Năng lực là khai báo, không phải mệnh lệnh** | Board và agent cùng khai báo; công cụ đối chiếu lúc build      |
| 2   | **Hành động vật lý không gọi trực tiếp được**  | Chỉ tới actuator qua `c.do()`, luôn đi qua gate                |
| 3   | **Gate là dữ liệu, không phải code**           | Version được, chia sẻ được, review được, bán được              |
| 4   | **Cùng một file agent trên mọi target**        | Target là cờ dòng lệnh, không phải nhánh code                  |
| 5   | **Mặc định là fail-closed**                    | Gate không chạy được → hành động bị chặn, không phải được phép |


### 6.2 Thiết bị khai báo năng lực

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

### 6.3 Agent khai báo yêu cầu

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

### 6.4 Hành động có kiểu

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
2. `requires` tham gia đối chiếu năng lực lúc build (§6.9).
3. `gate` phải trỏ tới một gate đã khai báo. Thiếu gate → build dừng.

### 6.5 Gate là artifact có version

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


| Thuộc tính                        | Vì sao quan trọng                                                                    |
| --------------------------------- | ------------------------------------------------------------------------------------ |
| `version` + `extends`             | Kế thừa gate cơ sở của cộng đồng, override phần riêng                                |
| `evaluate` tách khỏi `allow_when` | Đổi model không đổi chính sách; đổi chính sách không đụng code                       |
| `budget.fail: closed`             | Hành vi khi mất mạng là một dòng khai báo, không phải một nhánh `try/except` bị quên |
| Đọc được bởi người không phải dev | Quản lý vận hành review được điều kiện mở khoá                                       |
| Là file                           | Diff được, review trong PR, publish lên registry                                     |


Đặc tả đầy đủ các trường ở Phụ lục B.

### 6.6 Agent hoàn chỉnh

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

### 6.7 Action CI

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

Test cuối là **định luật tương đương target (§5.2) ở dạng khẳng định chạy được**. Nó không phải một lời hứa trong tài liệu; nó là một dòng CI đỏ khi bị vi phạm.

### 6.8 Bề mặt CLI

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

### 6.9 Hợp đồng năng lực lúc build

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

Dòng cuối là toàn bộ luận điểm của §5.3 trong một câu, và nó nằm trong terminal của người dùng chứ không nằm trong tài liệu này.

### 6.10 Chặng đường 10 phút đầu tiên


| Phút | Người dùng làm gì              | Sản phẩm trả lại gì                                        |
| ---- | ------------------------------ | ---------------------------------------------------------- |
| 0–1  | `pip install neuroedge`        | Không cần tài khoản, không cần key                         |
| 1–2  | `neuroedge new my-agent`       | Scaffold có sẵn 1 action, 1 gate, 1 test chạy được         |
| 2–4  | `neuroedge run --target sim`   | UI trình duyệt: nói vào mic laptop, thấy servo ảo quay     |
| 4–6  | Sửa `allow_when` trong gate    | Agent từ chối hành động — thấy ngay lý do trong trace      |
| 6–8  | `neuroedge test`               | CI xanh; thử phá một điều kiện → CI đỏ với tên gate cụ thể |
| 8–10 | `neuroedge run --target linux` | Cùng file agent, chạy trên phần cứng thật                  |


**Ràng buộc thiết kế:** không bước nào trong mười phút này yêu cầu mua phần cứng, tạo tài khoản, hay nhập thẻ.

---

## 7. An toàn và bảo mật mặc định

Bốn lớp, loại trừ lẫn nhau. Tất cả đều là mặc định, không phải tuỳ chọn.


| Lớp           | Thành phần               | Nội dung                                                                                                                                                    |
| ------------- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Hành động** | Action Contract          | Không có đường tới actuator ngoài gate · mặc định `fail: closed` · mọi đánh giá gate vào trace                                                              |
| **Thiết bị**  | Firmware &amp; phần cứng | Secure boot và flash encryption trên ESP32-S3 · công tắc tắt mic vật lý trên board tham chiếu · TPM khi nền tảng có                                         |
| **Mạng**      | Truyền dẫn               | TLS 1.3 toàn tuyến · mTLS thiết bị ↔ cloud · certificate pinning · cert riêng từng thiết bị                                                                 |
| **Dữ liệu**   | Quyền riêng tư           | Audio xử lý theo luồng, không lưu mặc định · xử lý cục bộ khi năng lực thiết bị cho phép · trace ghi quyết định, không ghi nội dung thô trừ khi bật rõ ràng |
| **Cập nhật**  | OTA                      | Firmware ký số · rollout theo đợt · tự rollback khi tỉ lệ lỗi vượt ngưỡng                                                                                   |


**Nguyên tắc bao trùm:** an toàn là một artifact đọc được, không phải một lời hứa. Với mỗi hành động vật lý, luôn tồn tại một file trả lời được câu hỏi "cái này được phép khi nào" — và một trace chứng minh nó đã được đánh giá.

---

## 8. Mặt phẳng thương mại

Một mặt phẳng duy nhất, hai nhóm năng lực. Đây là phần không mở mã, và là nơi sản phẩm tạo doanh thu.

**Quyết định định hình sản phẩm:** inference là công cụ thu hút, fleet management là nơi có giá trị gia tăng. Bán lại token là biên mỏng và là cuộc đua không thắng được với nhà cung cấp model.

> Cảnh báo phải tuân: bán quá rẻ thì **mất tín hiệu mà khách hàng gửi bằng việc trả tiền**. Vì vậy inference đặt *gần* giá vốn, không *miễn phí* — con số phải đủ để việc ai trả và ai không trả vẫn nói lên điều gì đó.

### 8.1 Inference plane — sáu năng lực


| #   | Năng lực                                      | Vì sao nhà phát triển trả tiền                                                           |
| --- | --------------------------------------------- | ---------------------------------------------------------------------------------------- |
| 1   | Một endpoint, một credential                  | Thiết bị không giữ key bên thứ ba; xoay key không cần nạp lại firmware                   |
| 2   | Routing đa nhà cung cấp + fallback            | Thiết bị không bao giờ thấy sự cố của một nhà cung cấp                                   |
| 3   | Giao thức hợp với edge                        | WebSocket giữ liên tục, khung audio nhị phân, partial theo luồng                         |
| 4   | Hạn mức cứng theo thiết bị                    | Một thiết bị lỗi không đốt sạch hoá đơn                                                  |
| 5   | Cache ngữ nghĩa + đếm tỉ lệ System 1/System 2 | Vừa là nguồn biên, vừa là bằng chứng cho luận điểm định tuyến                            |
| 6   | Một trace cho mỗi lượt                        | Cùng định dạng `.ntrace` dùng trong Action CI — hiện trường và CI nói chung một ngôn ngữ |


Năng lực 3 là rào cản kỹ thuật thật: thiết bị biên không kham nổi bắt tay TLS cho từng request HTTP. Hiện không ai terminate audio stream cho lớp phần cứng này.

Năng lực 6 là chỗ mặt phẳng thương mại khoá vào lõi mở mã: trace sinh ra trên gateway replay được trên laptop, không cần chuyển đổi.

### 8.2 Fleet plane — năm năng lực


| #   | Năng lực                            | Vì sao nhà phát triển trả tiền                               |
| --- | ----------------------------------- | ------------------------------------------------------------ |
| 1   | Định danh &amp; provisioning        | Cert riêng từng thiết bị, luồng claim ở lần boot đầu         |
| 2   | OTA rollout theo đợt, tự rollback   | Lý do số một khiến dân phần cứng trả tiền cho platform       |
| 3   | Sổ kiểm kê + sức khoẻ fleet         | Online/offline, phiên bản firmware, RSSI, vòng lặp reboot    |
| 4   | Config, secret và **gate** từ xa    | Đổi wake-word, prompt, ngưỡng gate mà không nạp lại firmware |
| 5   | Log và trace từ xa cho một thiết bị | Kéo `.ntrace` từ hiện trường về, replay trong sim            |


**Liên tục với lõi mở mã:** thiết bị ảo trong simulator hiện lên trong fleet console ngay. Đường từ `pip install` đến "tôi đang nhìn thiết bị của mình trên dashboard" phải liền một mạch — **fleet console phải hữu ích ở n = 1**, không phải ở n = 100. Đây là thành phần duy nhất đưa người dùng từ 1 thiết bị lên 100; không có nó, vòng lặp §3.6 đứt ở giữa.

### 8.3 Ranh giới giữa lõi mở và mặt phẳng thương mại


|                                 | Lõi mở mã (MIT)          | Mặt phẳng thương mại             |
| ------------------------------- | ------------------------ | -------------------------------- |
| Chạy được khi offline           | Có, đầy đủ               | Không áp dụng                    |
| Cần tài khoản                   | Không                    | Có                               |
| Thay thế được bằng hàng tự dựng | Có — interface công khai | —                                |
| Chứa gate và trace format       | Có                       | Dùng lại, không định nghĩa riêng |


**Cam kết:** không có tính năng nào của lõi bị khoá sau tài khoản. Mặt phẳng thương mại bán vận hành ở quy mô, không bán quyền dùng.

---

## 9. AURA — sản phẩm tham chiếu

Đi full-stack vào một thị trường dọc hẹp bằng chính framework của mình.

### 9.1 Sản phẩm


| Thuộc tính         | Nội dung                                                                                                 |
| ------------------ | -------------------------------------------------------------------------------------------------------- |
| **Là gì**          | Trợ lý đa phương thức tại phòng cho villa và khách sạn boutique                                          |
| **Phần cứng**      | ESP32-S3 · mic array 2 kênh có AEC · màn hình 3.5" · vỏ nhôm · BOM khoảng $75/máy                        |
| **Khách hàng**     | Đơn vị quản lý bất động sản cho thuê, quy mô 10–80 căn, tại Việt Nam và Đông Nam Á                       |
| **Năng lực**       | Hỏi đáp về villa, đặt món, gọi dịch vụ, đặt tour, điều khiển thiết bị trong phòng, chuyển tiếp nhân viên |
| **Kênh**           | Thiết bị tại phòng + Zalo OA cho khách đã check-in                                                       |
| **Gate tiêu biểu** | `unlock_door`, `order_food`, `call_staff`, `control_ac` — tất cả publish được lên registry               |


### 9.2 Bốn vai trò trong danh mục sản phẩm


| Vai trò                 | Nội dung                                                                                                         |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Bằng chứng sản xuất** | Framework chạy ngoài đời, trong môi trường có tiếng ồn, mạng chập chờn và người dùng thật — không chỉ trong demo |
| **Dòng tiền sớm**       | Kéo dài đường băng mà không phụ thuộc vào gateway                                                                |
| **Nguồn tín hiệu**      | Lần đầu nhìn thấy nhà phát triển và khách hàng thật muốn mua gì                                                  |
| **Nguồn gate thật**     | Những gate đầu tiên trên registry đến từ đây, đã tune bằng dữ liệu hiện trường                                   |


### 9.3 Ràng buộc kỷ luật

**AURA dùng đúng framework công khai, không nhánh nội bộ, không API đặc quyền.**

Khoảnh khắc AURA cần một tính năng framework không có, đó là tín hiệu framework thiếu tính năng đó — không phải lý do để fork. Ràng buộc này được kiểm tra bằng một thước đo ở §14.3, không bằng lời hứa.

> Có một biến thể của chiến lược full-stack đáng nhắm tới: *"eat your way gradually through the customer by doing all their hardest work for them."* Với người vận hành villa, việc khó nhất không phải mua thiết bị mà là **chịu trách nhiệm khi thiết bị làm sai**. Gate đã review, đã kiểm thử, có log — chính là thứ gánh việc đó.

---

# Phần III — Thực thi

## 10. Lộ trình sản phẩm

Năm khối công việc, một cổng định lượng. Mũi tên giữa các khối là mũi tên **cho phép**, không phải mũi tên thời gian.

```
Khối 1 — Lõi mở mã          ──┬──→  Khối 2 — Commercial plane  ──┐
(tháng 0–2)                   │      (tháng 2–6)                 │
                              │                                  ├──→  Cổng liquidity  ──→  Khối 5
                              └──→  Khối 3 — Rails          ─────┤      (phép đo)            Marketplace + Pay
                                     (tháng 2–6, song song)      │                            (tháng 18+)
                                                                 │
                                     Khối 4 — AURA full-stack  ──┘
                                     (tháng 6–12)
```

### 10.1 Khối 1 — Lõi mở mã (tháng 0–2)

**Mục tiêu duy nhất:** một người lạ, không có phần cứng, chạy được một agent có gate trong 10 phút.

```
pip install neuroedge
neuroedge new my-agent
neuroedge run --target sim
```

**Phạm vi:**


| Thành phần                                | Mục  |
| ----------------------------------------- | ---- |
| HAL hợp đồng năng lực, 5 nguyên thủy      | §5.3 |
| Action Contract Engine, gate có version   | §5.5 |
| Interface `SystemOne` / `SystemTwo`       | §5.6 |
| Voice pipeline + máy trạng thái hội thoại | §5.4 |
| Ba target `sim` / `linux` / `esp32s3`     | §5.2 |
| Action CI: record, replay, assert, golden | §5.7 |
| MCP client mỏng                           | —    |


**Về MCP:** giữ ở mức tối thiểu. Rẻ, và là ván cược về chuẩn giao tiếp.

**Không làm trong khối này:** vision · cloud · auth · tài khoản · registry · Jetson · Matter/HomeKit · fine-tune · fallback model cục bộ đã tune · hỗ trợ nhiều biến thể board.

> **Cảnh báo phạm vi.** Ba target hạng nhất cộng Action CI là phạm vi lớn cho hai tháng; riêng máy trạng thái hội thoại đã tốn ba tuần (§5.4). Xem Phụ lục G.1 — đây là quyết định còn mở, không phải giả định đã chốt.

### 10.2 Khối 2 — Commercial plane (tháng 2–6)

Inference plane và fleet plane, đặc tả đầy đủ ở §8. Điều kiện cho phép: Khối 1 có người dùng thật đang chạy agent trên `linux` hoặc `esp32s3`.

### 10.3 Khối 3 — Rails (tháng 2–6, song song Khối 2)

Bảy thứ rẻ, hữu ích ngay ngày đầu, và là hạ tầng bắt buộc cho marketplace sau này. Không thứ nào mang tính thương mại.


| #   | Rail                                               | Giá trị ngày đầu                    | Vai trò về sau                            |
| --- | -------------------------------------------------- | ----------------------------------- | ----------------------------------------- |
| 1   | Registry công khai, miễn phí                       | `neuroedge gate add <uri>`          | Dữ liệu về gate nào thật sự được dùng lại |
| 2   | Manifest + semver cho agent và gate                | Quản lý phụ thuộc                   | Đơn vị phân phối của marketplace          |
| 3   | Khai báo capability                                | Bắt lỗi lúc build (§6.9)            | Kiểm tra tương thích trước khi cài        |
| 4   | **Gate có version, `extends` được**                | Dùng lại gate an toàn của cộng đồng | Ứng viên hàng hoá số một                  |
| 5   | Stable ID cho thiết bị, agent, gate                | Debug, hỗ trợ                       | Quy kết doanh thu                         |
| 6   | Metering theo lượt gọi agent và lượt đánh giá gate | Phân tích sử dụng                   | Cơ sở chia doanh thu                      |
| 7   | Permission / sandbox model                         | An toàn khi thử agent lạ            | Điều kiện để chạy mã bên thứ ba           |


Rail 5, 6, 7 **không thể** thêm vào sau: thiếu chúng thì marketplace tương lai không quy kết được doanh thu và không dám cho mã người lạ chạy trên thiết bị có actuator.

Rail 4 là hiệu ứng mạng khả dụng trước marketplace (§3.6). Nó miễn phí, không mở bề mặt pháp lý, và làm sản phẩm tốt hơn cho cả người chia sẻ lẫn người dùng lại.

### 10.4 Khối 4 — AURA full-stack (tháng 6–12)

Đặc tả ở §9. Điều kiện cho phép: framework đã ổn định về API, đã có người ngoài đội ship thiết bị thật.

### 10.5 Cổng liquidity

**Đây không phải hạng mục công việc. Nó là một phép đo.** Bốn ngưỡng phải đạt đủ, không phải ba trên bốn.


| #   | Ngưỡng                                                                   | Đo cái gì             |
| --- | ------------------------------------------------------------------------ | --------------------- |
| 1   | ≥ 10.000 thiết bị hoạt động hàng tháng                                   | Quy mô cầu            |
| 2   | ≥ 50 gate hoặc agent tự publish, mỗi cái ≥ 5 lượt cài                    | Quy mô cung           |
| 3   | **&gt; 30% thiết bị chạy gate hoặc agent mà chủ thiết bị không tự viết** | Liquidity thật        |
| 4   | Có bằng chứng giao dịch tự phát ngoài nền tảng                           | Nhu cầu trả tiền thật |


Ngưỡng 3 quan trọng nhất. Ngưỡng 1 và 2 đạt được mà vẫn không có thị trường — chúng đo hoạt động, không đo trao đổi.

Ngưỡng 4 áp dụng trực tiếp chỉ dẫn về việc lắng nghe khi người dùng "dùng sai" sản phẩm: *"don't be annoyed that your users are using your product wrong; listen for the message they're sending."* Nếu người ta đang tự giao dịch với nhau qua kênh khác, đó là thông điệp về sản phẩm thật.

**Ghi ngưỡng từ hôm nay** để sáu tháng nữa quyết định bằng số liệu chứ không bằng cảm tính.

### 10.6 Khối 5 — Marketplace và Pay (tháng 18+)

Chỉ mở khi đủ cả bốn ngưỡng. Khi đó marketplace không còn là canh bạc; nó là việc thu dọn một thị trường đã tự hình thành.

**Món hàng chưa được quyết định, và đó là chủ ý.** Các ứng viên hợp lý ngang nhau:


| Ứng viên            | Luận điểm                                                                                                                                                               |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Gate đã tune**    | Một safety gate cho cánh tay robot, đã chạy qua 10.000 giờ hiện trường, có giá trị cao hơn nhiều một agent trọn gói — và đây là ứng viên được §5.5 chuẩn bị sẵn hạ tầng |
| Wake-word đã train  | Cho một ngôn ngữ hoặc một tên thương hiệu riêng                                                                                                                         |
| Board đã chứng nhận | Qua kênh phân phối phần cứng                                                                                                                                            |
| Dịch vụ người thật  | Cấu hình, tích hợp, triển khai tại chỗ                                                                                                                                  |


Registry miễn phí ở Khối 3 trả lời hộ câu hỏi này trong 12 tháng, gần như miễn phí.

**Về Pay:** khi tiền đã chảy qua gateway, đã có billing account, ledger và quan hệ thanh toán với nhà phát triển. Thêm "trả tiền cho bên thứ ba từ dòng tiền này" là bước ngắn. Xây pay rails song song với gateway là xây hai lần cùng một thứ.

---

## 11. Ranh giới sản phẩm

Danh sách loại trừ tường minh, theo lý do. Đây là phần quan trọng nhất của tài liệu: một đề xuất không có ranh giới rõ ràng thì không có phạm vi.


| Hạng mục                                | Trạng thái                     | Lý do (§4)                                                    |
| --------------------------------------- | ------------------------------ | ------------------------------------------------------------- |
| Marketplace thương mại, chia hoa hồng   | Chặn tới sau cổng              | R3 — chưa có liquidity                                        |
| Agent-to-agent pay, escrow, KYC         | Chặn tới sau cổng              | R4 — bề mặt pháp lý                                           |
| Chương trình chứng nhận, phí badge      | Chặn tới sau cổng              | R3                                                            |
| Vision (camera, nhận diện)              | Hoãn sau tháng 12              | R1 sai — không phục vụ TTFV                                   |
| Jetson, Matter, HomeKit                 | Hoãn sau tháng 12              | R3 — ba target đã đủ chứng minh định luật tương đương         |
| SSO/SAML, SOC 2, RBAC nhiều tầng        | Hoãn sau tháng 12              | R3 — nhu cầu doanh nghiệp, chưa có doanh nghiệp               |
| Multi-region, on-prem                   | Hoãn sau tháng 12              | R3                                                            |
| Fallback model cục bộ đã tune           | Hoãn tới khi chỉ báo §13.1 bật | R3 — interface đã đủ phòng ngừa; xem Phụ lục G.2              |
| Engine cảnh báo, BI, dashboard tuỳ biến | Hoãn vô thời hạn               | R1 và R3 đều sai; phạm vi vô hạn                              |
| Kubernetes                              | Hoãn vô thời hạn               | Một Postgres, một Redis, một hàng đợi là đủ ở quy mô mục tiêu |
| Fine-tune model                         | Hoãn vô thời hạn               | R3                                                            |
| Hỗ trợ rộng biến thể board              | Hoãn vô thời hạn               | R1 sai — ba target, mỗi target một board tham chiếu           |


---

# Phần IV — Kiểm chứng

## 12. Định vị cạnh tranh

### 12.1 Bản đồ đối thủ

Gọi tên cụ thể. Không thể suy luận về một đối thủ mà mình không chịu gọi tên.


| Đối thủ                            | Thế mạnh                                                  | Vì sao không lấp được khoảng trống này                                                      |
| ---------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| **ESP-Claw** (Espressif)           | Hỗ trợ chính hãng, MCP-native, sâu về ESP32               | Một dòng chip. Về cấu trúc không thể coi chip của hãng là một trong nhiều target ngang hàng |
| **XiaoZhi**                        | Pipeline thoại hoàn chỉnh, cộng đồng lớn nhất ở lớp ESP32 | Không có điều phối agent, không có HAL đa nền tảng, không có khái niệm hợp đồng hành động   |
| **LiveKit Agents · Pipecat · TEN** | Hạ tầng A/V thời gian thực mạnh, cộng đồng tốt            | Lấy cloud làm trung tâm. Offline-first phá mô hình hạ tầng của chính họ                     |
| **LangChain và tương đương**       | Hệ sinh thái lớn nhất cho agent phần mềm                  | Thuần phần mềm, không có trừu tượng phần cứng, không có actuator để bảo vệ                  |


### 12.2 Ba khác biệt có thể bảo vệ


| #   | Khác biệt                                           | Vì sao khó sao chép                                                                                                                                                                               |
| --- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Hợp đồng hành động có kiểu + Action CI**          | Đòi hỏi ba quyết định kiến trúc ở tuần 1 cùng lúc: sim là target thật, gate là artifact có version, trace là công dân hạng nhất. Ai đã ship mà thiếu chúng thì phải viết lại, không phải thêm vào |
| 2   | **Hợp đồng năng lực HAL trên ba target ngang hàng** | SDK một-chip không cần khái niệm này nên không có. Thêm vào sau là thay đổi kiến trúc, và mâu thuẫn với động cơ bán silicon                                                                       |
| 3   | **Định dạng gate và trace**                         | Trong lĩnh vực chưa có chuẩn, đề xuất đầu tiên thường thắng bất kể ai đề xuất. Định dạng thắng rồi thì framework thắng theo                                                                       |


Lưu ý về điều **không** nằm trong bảng: simulator một mình. Nó là đòn bẩy TTFV xuất sắc, nhưng một đối thủ khởi động mới sẽ chọn đúng kiến trúc đó miễn phí sau khi thấy nó hiệu quả. Simulator là điều kiện cần của khác biệt số 1, không phải khác biệt tự thân.

### 12.3 Điểm không cạnh tranh

NeuroEdge không cạnh tranh về giá inference, không cạnh tranh về độ phủ phần cứng, không cạnh tranh với SDK chính hãng ở độ sâu của một dòng chip.

Ba mặt trận này thua từ đầu — và theo §3.4, thắng chúng chỉ nên là **lợi ích phụ** của việc thắng ở chiều khác, không bao giờ là mục tiêu.

---

## 13. Rủi ro và giảm thiểu

Bốn rủi ro theo nguồn gốc. Loại trừ lẫn nhau.

### 13.1 Rủi ro phụ thuộc nhà cung cấp model


|                         |                                                                                                     |
| ----------------------- | --------------------------------------------------------------------------------------------------- |
| **Nội dung**            | Luận điểm sản phẩm dựa vào một model đóng của một nhà cung cấp mới                                  |
| **Kịch bản**            | Đổi giá, đổi điều kiện truy cập, hoặc nhà cung cấp tự ship framework                                |
| **Giảm thiểu cấu trúc** | Sản phẩm là hợp đồng hành động; model chỉ điền vào ô đánh giá của gate. Đổi model không đổi định vị |
| **Giảm thiểu kỹ thuật** | Interface `SystemOne` / `SystemTwo` từ tuần 1 (§5.6). Fallback cục bộ đã tune ship khi chỉ báo bật  |
| **Chỉ báo sớm**         | Thay đổi điều khoản API · nhà cung cấp tuyển kỹ sư framework · nhà cung cấp công bố SDK thiết bị    |


### 13.2 Rủi ro nền tảng phần cứng


|                          |                                                                                                                               |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| **Nội dung**             | Nhà sản xuất chip phát SDK miễn phí vĩnh viễn để bán silicon                                                                  |
| **Vì sao không thể đua** | Không thể rẻ hơn miễn phí; họ có động cơ cấu trúc để giữ như vậy                                                              |
| **Giảm thiểu**           | Đánh từ bên sườn (§3.4): thắng ở chiều kiểm thử được và đa target. Ba target ngang hàng từ Khối 1 là bằng chứng của chiều này |
| **Chỉ báo sớm**          | SDK chính hãng thêm lớp điều phối agent · hoặc bắt đầu hỗ trợ chip đối thủ                                                    |


### 13.3 Rủi ro biên lợi nhuận


|                 |                                                                                                                       |
| --------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Nội dung**    | Bán lại inference là biên mỏng; nhà cung cấp model có thể nuốt cả mình lẫn khách của mình                             |
| **Giảm thiểu**  | Trọng tâm doanh thu ở fleet management (§8.2). Inference gần giá vốn — nhưng không miễn phí, để giữ tín hiệu trả tiền |
| **Chỉ báo sớm** | Tỉ trọng doanh thu từ inference vượt fleet                                                                            |


### 13.4 Rủi ro sao nhãng phạm vi


|                 |                                                                                           |
| --------------- | ----------------------------------------------------------------------------------------- |
| **Nội dung**    | Áp lực xây marketplace sớm, hoặc chiều theo yêu cầu doanh nghiệp đầu tiên                 |
| **Giảm thiểu**  | Bốn quy tắc §4 và cổng định lượng §10.5, ghi thành văn bản **trước khi** áp lực xuất hiện |
| **Chỉ báo sớm** | Xuất hiện đề xuất không thuộc R1 hay R2 nhưng vẫn được ưu tiên                            |


---

## 14. Thước đo thành công

Đo bằng kết quả, không đếm tính năng. Sao GitHub không có trong bảng nào — nó đo người xem, không đo người dùng.

### 14.1 Khối 1 (tháng 2)


| Thước đo                                      | Ngưỡng                                                                                                                                                |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Time-to-first-value, đo trên 10 người lạ thật | Trung vị dưới 10 phút                                                                                                                                 |
| **Tương đương target**                        | Cùng một file agent chạy trên `sim`, `linux`, `esp32s3` không sửa dòng nào — khẳng định bằng `neuroedge verify` trong CI                              |
| **Áp dụng Action CI**                         | ≥ 50% dự án dùng `neuroedge new` giữ lại và mở rộng test gate mặc định                                                                                |
| **Chuyển đổi sim → phần cứng**                | *\[cần chốt ngưỡng\]* Tỉ lệ người chạy sim rồi build lên board thật trong 30 ngày. Nếu con số này thấp, cả phễu §3.6 đứt ở bước đầu — xem Phụ lục G.4 |
| Khả năng quan sát                             | Trace hiển thị tỉ lệ System 1/System 2, chi phí từng lượt, mọi quyết định gate                                                                        |
| Tài sản phân phối                             | 3 ví dụ chạy được, 1 GIF 15 giây trong README                                                                                                         |


GIF không phải hạng mục marketing phụ. Với một dự án mã nguồn mở về phần cứng, nó là kênh phân phối.

### 14.2 Khối 2 và 3 (tháng 6)


| Thước đo                   | Ngưỡng                                                                                                                   |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Độ tin cậy OTA             | Một lần đẩy thành công cho &gt; 1.000 thiết bị, 0 thiết bị chết                                                          |
| **Ngân sách độ trễ thoại** | *\[cần chốt số công khai\]* p95 round-trip. Đối thủ đều công bố số; từ chối nêu là né cam kết khó nhất — xem Phụ lục G.3 |
| Độ trễ gate                | p95 dưới `budget.p95_latency_ms` khai báo, trên cả ba target                                                             |
| Hiệu quả định tuyến        | Tỉ lệ System 1/System 2 đo được và chứng minh cắt chi phí thật                                                           |
| **Chia sẻ gate**           | Số gate được publish lên registry và được cài bởi người không phải tác giả                                               |
| Doanh thu đầu tiên         | Đến từ đơn vị tính fleet, không phải từ inference                                                                        |


Thước đo cuối quan trọng hơn năm thước đo trên. Nó phân biệt một dự án mã nguồn mở nhiều sao với một công ty.

### 14.3 Khối 4 (tháng 12)


| Thước đo                    | Ngưỡng                                                                                                               |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Tính toàn vẹn của framework | AURA chạy trên nhánh công khai, không API đặc quyền                                                                  |
| Bằng chứng dùng lại         | Số gate và agent do bên thứ ba publish                                                                               |
| Tín hiệu liquidity          | Tiến độ trên bốn ngưỡng của cổng (§10.5)                                                                             |
| Giúp người dùng kiếm tiền   | Có case study đo được: giảm chuyến đi hiện trường, giảm lô hàng thu hồi, hoặc rút ngắn bring-up board thứ hai (§3.7) |


---

# Phụ lục

## Phụ lục A — Đặc tả hợp đồng năng lực HAL

### A.1 Năm nguyên thủy và thuộc tính thương lượng được


| Nguyên thủy   | Thuộc tính board khai báo                      | Thuộc tính agent yêu cầu                | Quy tắc đối chiếu                              |
| ------------- | ---------------------------------------------- | --------------------------------------- | ---------------------------------------------- |
| `audio.in`    | `channels`, `sample_rate_hz`, `aec`, `vad`     | `aec`, `min_channels`, `sample_rate_hz` | Board phải đáp ứng bằng hoặc hơn               |
| `audio.out`   | `channels`, `sample_rate_hz`                   | `channels`                              | Board phải đáp ứng bằng hoặc hơn               |
| `digital.out` | `pins[]` (tên logic), `backend`                | `pins[]`                                | Mọi pin agent yêu cầu phải tồn tại theo tên    |
| `sensor.read` | `sensors[]` (`motion`, `temp`, `touch`, `imu`) | `sensors[]`                             | Mọi sensor agent yêu cầu phải tồn tại theo tên |
| `display`     | `width`, `height`, `color`                     | `min_width`, `min_height`               | Board phải đáp ứng bằng hoặc hơn               |


### A.2 Ba quy tắc bất biến


| #   | Quy tắc                                                        | Hệ quả khi vi phạm                                           |
| --- | -------------------------------------------------------------- | ------------------------------------------------------------ |
| 1   | **Pin và sensor định danh bằng tên logic, không bằng số chân** | Agent gắn chặt vào một layout board → mất tương đương target |
| 2   | **Mọi lệnh `digital.out` phải đi kèm gate đã pass**            | HAL trả `ActionContractError`, không thực thi                |
| 3   | **Đối chiếu chạy lúc build, không lúc runtime**                | Lỗi cấu hình lộ ra khi thiết bị đã ở hiện trường             |


### A.3 Ba implementation của cùng một hợp đồng


| Nguyên thủy   | `sim`                           | `linux`              | `esp32s3`           |
| ------------- | ------------------------------- | -------------------- | ------------------- |
| `audio.in`    | File WAV hoặc mic laptop        | ALSA / PulseAudio    | I2S + AEC phần cứng |
| `audio.out`   | Loa laptop hoặc thiết bị null   | ALSA                 | I2S DAC             |
| `digital.out` | Servo ảo trên UI, ghi vào trace | `gpiod`              | GPIO driver         |
| `sensor.read` | Giá trị theo kịch bản           | I2C/SPI qua sysfs    | I2C/SPI driver      |
| `display`     | Khung ảo trong trình duyệt      | Cửa sổ / framebuffer | SPI LCD             |


---

## Phụ lục B — Đặc tả định dạng gate v1

### B.1 Các trường cấp cao nhất


| Trường       | Bắt buộc | Nội dung                                                          |
| ------------ | -------- | ----------------------------------------------------------------- |
| `schema`     | Có       | Luôn là `neuroedge.gate/v1`                                       |
| `name`       | Có       | Tên logic, trùng với khoá trong `agent.toml`                      |
| `version`    | Có       | Semver. Đổi `allow_when` là breaking change                       |
| `extends`    | Không    | URI gate cơ sở. Kế thừa `evaluate`, có thể siết thêm `allow_when` |
| `evaluate`   | Có       | Các đại lượng cần đánh giá trước khi cho phép hành động           |
| `allow_when` | Có       | Điều kiện cho phép. Mọi mệnh đề phải đúng                         |
| `on_block`   | Có       | Hành vi khi bị chặn                                               |
| `budget`     | Có       | Ngân sách độ trễ và hành vi khi không đánh giá được               |


### B.2 Ba kiểu trong `evaluate`


| Kiểu     | Khai báo                             | Trả về                         | Toán tử dùng được trong `allow_when`     |
| -------- | ------------------------------------ | ------------------------------ | ---------------------------------------- |
| `bool`   | `instructions`                       | Xác suất + confidence          | `true`, `false`, `{ confidence_gte: x }` |
| `level`  | `levels[]` có thứ tự, `instructions` | Mức + phân phối                | `eq`, `lte`, `gte`                       |
| `choice` | `options[]`, `instructions`          | Lựa chọn + xác suất từng nhánh | `in`, `not_in`, `eq`                     |


### B.3 `on_block` — bốn hành vi


| `action`   | Nội dung                                                               |
| ---------- | ---------------------------------------------------------------------- |
| `escalate` | Chuyển cho `to:` (`human`, `slow`, hoặc một agent khác), kèm `message` |
| `deny`     | Từ chối im lặng, chỉ ghi trace                                         |
| `ask`      | Hỏi lại người dùng một câu xác nhận đã khai báo trước                  |
| `degrade`  | Chạy một hành động thay thế đã khai báo, an toàn hơn                   |


### B.4 `budget` — hai trường


| Trường           | Nội dung                                                                                                             |
| ---------------- | -------------------------------------------------------------------------------------------------------------------- |
| `p95_latency_ms` | Ngân sách đánh giá. Vượt ngân sách xử lý như `fail`                                                                  |
| `fail`           | `closed` (mặc định, chặn) hoặc `open` (cho phép — chỉ dùng cho hành động hoàn tác được, và phải khai báo tường minh) |


### B.5 Quy tắc kế thừa


| #   | Quy tắc                                                                     |
| --- | --------------------------------------------------------------------------- |
| 1   | Gate con **kế thừa toàn bộ** `evaluate` của gate cha                        |
| 2   | Gate con **chỉ được siết chặt** `allow_when`, không được nới lỏng           |
| 3   | Gate con **có thể** thêm mục `evaluate` mới                                 |
| 4   | `fail: open` không kế thừa được qua `extends` — phải khai báo lại ở mỗi cấp |


Quy tắc 2 và 4 là lý do gate cộng đồng an toàn khi dùng lại: kéo một gate của người khác về không bao giờ nới lỏng chính sách của mình.

---

## Phụ lục C — Đặc tả định dạng `.ntrace`

### C.1 Nội dung một trace


| Nhóm sự kiện | Ghi gì                                                                                      |
| ------------ | ------------------------------------------------------------------------------------------- |
| `input`      | Khung audio (hoặc hash khi bật chế độ ẩn danh), đọc cảm biến, sự kiện hệ thống              |
| `perception` | Kết quả wake-word, VAD, STT, kèm độ trễ từng chặng                                          |
| `decision`   | Mọi lượt gọi System 1 / System 2: đầu vào, đầu ra, confidence, độ trễ, chi phí              |
| `gate`       | Mọi đánh giá gate: tên, version, từng mục `evaluate`, kết quả `allow_when`, quyết định cuối |
| `action`     | Mọi lệnh tới actuator: hành động, tham số, gate cho phép, thời điểm                         |
| `output`     | Nội dung TTS, nội dung hiển thị                                                             |


### C.2 Bốn thuộc tính bắt buộc của định dạng


| #   | Thuộc tính                      | Vì sao                                                                            |
| --- | ------------------------------- | --------------------------------------------------------------------------------- |
| 1   | **Replay được trên mọi target** | Là nền của định luật tương đương target (§5.2)                                    |
| 2   | **Ổn định giữa các phiên bản**  | Trace ghi hôm nay replay được sau 12 tháng; đây là tài sản dài hạn của người dùng |
| 3   | **Đọc được bởi người**          | Điều tra sự cố không cần công cụ riêng                                            |
| 4   | **Ẩn danh được tại nguồn**      | Bật một cờ để thay nội dung thô bằng hash, giữ nguyên chuỗi quyết định            |


### C.3 Golden — chuỗi quyết định tham chiếu

Golden là phần `decision` + `gate` + `action` của một trace, bỏ hết mốc thời gian và nội dung thô. So sánh golden trả lời đúng một câu hỏi: **với cùng đầu vào, agent có ra cùng chuỗi quyết định không.**

Đây là đơn vị kiểm thử duy nhất chịu được việc đổi model, đổi prompt, và đổi target.

---

## Phụ lục D — Nền tảng phần cứng, model và tích hợp

### D.1 Nền tảng phần cứng


| Nền tảng             | Chip             | Giá tham khảo | Trạng thái                     |
| -------------------- | ---------------- | ------------- | ------------------------------ |
| `sim`                | —                | —             | Hạng nhất                      |
| Raspberry Pi 5 / x86 | BCM2712 / x86-64 | \~$80         | Hạng nhất (`linux`)            |
| ESP32-S3             | Xtensa LX7       | \~$5          | Hạng nhất (`esp32s3`)          |
| M5Stack CoreS3       | ESP32-S3         | \~$50         | Board tham chiếu của `esp32s3` |
| Seeed XIAO ESP32S3   | ESP32-S3         | \~$8          | Cộng đồng                      |
| NVIDIA Jetson Orin   | Cortex-A78AE     | \~$150–500    | Hoãn (§11)                     |


### D.2 Model


| Vai trò                                 | Ứng viên                                                              |
| --------------------------------------- | --------------------------------------------------------------------- |
| **System One** — quyết định có cấu trúc | Model quyết định có kiểu qua API · model intent chưng cất chạy cục bộ |
| **System Two** — suy luận mở            | Claude Sonnet 5 · Qwen 2.5 (3B/7B/72B) · Llama 3.2 · Phi-3 Mini       |
| **STT**                                 | Whisper (large-v3 / medium / small) · Deepgram Nova-2                 |
| **TTS**                                 | Kokoro · Edge-TTS · ElevenLabs                                        |
| **Wake-word**                           | openWakeWord · microWakeWord (trên MCU)                               |


Mọi mục trong bảng đều nằm sau interface. Danh sách này là cấu hình mặc định, không phải cam kết kiến trúc.

### D.3 Tích hợp


| Nhóm                                         | Đối tác                                                 |
| -------------------------------------------- | ------------------------------------------------------- |
| Nhà thông minh                               | Home Assistant · Matter *(hoãn)* · HomeKit *(hoãn)*     |
| Kênh nhắn tin                                | Zalo OA · Telegram · Slack · Discord                    |
| Thanh toán (chỉ ở lớp ứng dụng, không ở lõi) | VietQR · Stripe · MoMo                                  |
| Hạ tầng                                      | AWS · GCP · Azure — không phụ thuộc nhà cung cấp cụ thể |


---

## Phụ lục E — Đối chiếu "Making Startups Powerful"

Tiểu luận (Paul Graham, tháng 9 năm 2026) là **bộ heuristic để sinh ý tưởng**, không phải checklist triển khai. Tác giả nói rõ các phép biến đổi này thường không cho ra gì, và mọi thứ phải phục tùng một ràng buộc duy nhất:

> *"They all have to make things better for the customer. You can't add network effects or make the money flow through you or go full stack just because you'd like to. You can only do these things when the result is better for the customer. Otherwise you won't have any uptake."*

Bảng dưới phân loại theo trạng thái áp dụng — không gán hệ số nhân, vì hệ số nhân là thứ không đo được và tạo cảm giác chắc chắn giả.


| Heuristic                         | Trạng thái       | NeuroEdge làm gì                                                                | Tốt hơn cho khách hàng ở chỗ nào                           |
| --------------------------------- | ---------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Sở hữu quan hệ khách hàng         | **Ngay**         | Gateway đứng giữa nhà phát triển và mọi nhà cung cấp model                      | Đổi model không phải nạp lại firmware                      |
| Để tiền chảy qua mình             | **Một phần**     | Qua gateway, nhưng biên đến từ fleet                                            | Một hoá đơn thay vì năm                                    |
| **Lấy dữ liệu sớm**               | **Ngay**         | Đi tới nơi vòng đời dữ liệu bắt đầu: lần đầu một hành động bị đề xuất trong sim | Trace và replay là thứ họ cần dù có NeuroEdge hay không    |
| Bán cho khách giai đoạn sớm       | **Ngay**         | Indie maker ở thiết bị thứ nhất, không phải doanh nghiệp ở thiết bị thứ 500     | Cài được ngay, không qua chu trình mua sắm                 |
| Có API                            | **Ngay**         | Mọi thứ gọi được qua API và CLI; gate là dữ liệu chứ không phải code            | Không bị khoá vào cách dùng mà mình nghĩ ra                |
| Hào phóng                         | **Ngay**         | Lõi MIT, registry miễn phí, gate cơ sở miễn phí                                 | Không trả tiền để an toàn                                  |
| **Định nghĩa chuẩn**              | **Ngay**         | Đề xuất định dạng gate và trace cho một lĩnh vực chưa có chuẩn                  | Mô tả "an toàn khi nào" theo một cách duy nhất             |
| Hiệu ứng mạng qua chia sẻ         | **Ngay**         | Chia sẻ gate — bản khả dụng trước khi có app store                              | Dùng lại gate người khác đã tune bằng giờ hiện trường thật |
| **Giúp người dùng kiếm tiền**     | **Ngay**         | Cắt chuyến đi hiện trường, lô hàng thu hồi, thời gian bring-up (§3.7)           | Đây là tiền mặt, không phải tiện ích                       |
| Chơi ván dài                      | **Xuyên suốt**   | Rails xây trước khi có nhu cầu thương mại                                       | Hạ tầng sẵn khi họ cần                                     |
| **Đánh từ bên sườn**              | **Xuyên suốt**   | Không đánh trực diện SDK chính hãng; thắng ở chiều kiểm thử được                | —                                                          |
| Đi full-stack                     | **Khối 4**       | AURA, sau khi framework ổn định                                                 | Gánh phần khó nhất: trách nhiệm khi thiết bị làm sai       |
| Lắng nghe khi người dùng dùng sai | **Là cơ chế đo** | Ngưỡng 4 của cổng liquidity                                                     | —                                                          |
| App store                         | **Sau cổng**     | Nền xây trước; phần thương mại bị chặn                                          | Store rỗng làm tệ hơn cho người dùng → vi phạm ràng buộc   |
| Agent trả tiền cho agent          | **Sau cổng**     | Bề mặt pháp lý vượt năng lực hấp thụ hiện tại                                   | —                                                          |


**Hai cảnh báo mà tài liệu này tuân theo:**

1. **Dòng token.** Khi token chảy qua mình, câu hỏi là các công ty model có dễ nuốt chửng mình hoặc khách của mình đến mức nào. Đây là lý do trọng tâm doanh thu ở fleet, không ở inference.
2. **Bán quá rẻ.** *"If your product is a* $10 bill that you sell for$*5, your growth rate isn't telling you anything useful."* Inference bán gần giá vốn, không miễn phí.

**Và một nguyên tắc về độ phức tạp:**

> *"The company is unconsciously cowering by doing something less ambitious than they could. Just y is often, in effect, just stand up straight."*

Tài liệu này tuyên bố một mệnh đề duy nhất mà chưa ai tuyên bố, thay vì tuyên bố một phiên bản gọn hơn của mệnh đề mà bốn đối thủ đều đã tuyên bố.

---

## Phụ lục F — Từ điển thuật ngữ


| Thuật ngữ                        | Định nghĩa                                                                                                    |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| **Hợp đồng hành động**           | Ràng buộc bắt buộc giữa một hành động vật lý và gate của nó; hành động không chạy nếu gate không pass         |
| **Gate**                         | Artifact có schema, có version, khai báo điều kiện cho phép một hành động vật lý. Là dữ liệu, không phải code |
| **Action CI**                    | Record phiên thật, replay trên target bất kỳ, khẳng định về hành động — chạy trong pipeline mỗi commit        |
| **`.ntrace`**                    | Định dạng trace: đầu vào, mọi đánh giá gate, mọi lệnh actuator, kèm mốc thời gian. Replay được                |
| **Golden**                       | Chuỗi quyết định tham chiếu cho một trace. Lệch golden → CI đỏ                                                |
| **Fail-closed**                  | Gate không đánh giá được → hành động bị chặn. Mặc định của mọi gate                                           |
| **HAL**                          | Lớp trừu tượng phần cứng; ở đây là hợp đồng năng lực hai chiều                                                |
| **Hợp đồng năng lực**            | Thiết bị khai báo năng lực, agent khai báo yêu cầu, lệch nhau báo lỗi lúc build                               |
| **Định luật tương đương target** | Cùng một file agent chạy trên `sim`, `linux`, `esp32s3` không sửa dòng nào                                    |
| **System 1 / System 2**          | Model quyết định có cấu trúc, nhanh / model suy luận, chậm. Cả hai sau interface thay thế được                |
| **TTFV**                         | Time-to-first-value — từ khi cài đến kết quả hữu ích đầu tiên                                                 |
| **Rails**                        | Hạ tầng nền xây sớm, chưa mang tính thương mại                                                                |
| **Cổng liquidity**               | Bốn ngưỡng định lượng chặn việc mở marketplace và pay                                                         |
| **Inference plane**              | Nhóm năng lực gateway đứng giữa thiết bị và nhà cung cấp model                                                |
| **Fleet plane**                  | Nhóm năng lực quản lý đội thiết bị ngoài hiện trường                                                          |
| **MCP**                          | Model Context Protocol — chuẩn kết nối AI với công cụ                                                         |


---

## Phụ lục G — Quyết định còn mở

Bốn điều tài liệu này **chưa** chốt. Ghi ra để không bị nhầm thành giả định đã quyết.

### G.1 Phạm vi Khối 1 so với thời hạn 2 tháng

Ba target hạng nhất cộng Action CI là phạm vi lớn cho hai tháng. Ba lựa chọn:


| Lựa chọn                                                                            | Đánh đổi                                                                                                 |
| ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Giữ 2 tháng, cắt bớt                                                                | Ứng viên cắt: chính sách định tuyến khai báo được (hard-code `fast_first`), MCP client, ví dụ thứ 2 và 3 |
| Giãn sang 3–4 tháng                                                                 | Mọi khối sau trượt theo, vì mũi tên là mũi tên cho phép                                                  |
| Tách Khối 1 thành 1a (`sim` + `linux` + gate + CI) và 1b (`esp32s3` + voice đầy đủ) | Giữ nhịp phát hành, nhưng `esp32s3` chậm làm yếu luận điểm tương đương target                            |


**Khuyến nghị:** lựa chọn thứ ba. Định luật tương đương chứng minh được bằng hai target trước, target thứ ba củng cố.

### G.2 Thời điểm ship fallback model cục bộ

Interface ở tuần 1 là đã chốt (R2, chi phí một ngày). Fallback cục bộ *đã tune* tốn vài tuần và là bảo hiểm cho rủi ro mà chỉ báo sớm ở §13.1 chưa bật.

**Đề xuất:** giữ ở §11 cho tới khi một chỉ báo bật, rồi ship trong 2 tuần.

### G.3 Ngân sách độ trễ công khai

§14.2 để trống. Cần chốt trước khi phát hành Khối 1, vì nó là spec sản phẩm chứ không phải chỉ số nội bộ. Ba con số cần chốt, mỗi con số trên cả ba target:

1. p95 từ wake-word tới phản hồi đầu tiên
2. p95 đánh giá một gate
3. p95 round-trip trọn một lượt

### G.4 Ngưỡng chuyển đổi sim → phần cứng

§14.1 để trống. Đây là con số quyết định xem phễu §3.6 có hoạt động không. Chưa có cơ sở để đặt ngưỡng trước khi có 100 người dùng thật.

**Đề xuất:** đo từ ngày đầu, đặt ngưỡng ở tháng 3.

---

## Kết

Sản phẩm này đặt cược vào một mệnh đề đơn lẻ:

> **Hành động vật lý phải kiểm thử được trước khi nó xảy ra.**

Mọi quyết định trong tài liệu — ba target ngang hàng, gate là artifact chứ không phải code, sim là target thật chứ không phải mock, trace là công dân hạng nhất, marketplace hoãn sau một cổng định lượng — đều là hệ quả của mệnh đề đó.

Nếu mệnh đề đúng, NeuroEdge định nghĩa định dạng mà cả lĩnh vực dùng để mô tả "hành động này an toàn khi nào", và framework thắng theo. Nếu mệnh đề sai, nó sai sớm và rẻ — trong ba tháng đầu, đo bằng bốn thước đo ở §14.1, chứ không sau ba năm.

---

*Hết tài liệu*