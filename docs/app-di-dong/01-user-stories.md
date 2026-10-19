# Ứng dụng di động NeuroEdge ("app nhà"): user stories

> **Đã duyệt bởi Q-91 (2026-10-19); increment I2g, chờ sau cổng nhu cầu 2026-12-06.** **Thay đổi 2026-10-19:** bản nháp
> 2026-10-16 thành bản đã duyệt; ứng dụng là app gốc iOS và Android (React Native). Mọi mã `Q-N`, `TSK-*`, `FR-*`, `MS-*`,
> `BL-*` dưới đây là mã đã có, được dẫn lại để truy vết, không phải nội dung mới.
> **Tài liệu cùng bộ:** `02-brd.md` (yêu cầu kinh doanh `BR-APP-nn`), `03-srs.md` (yêu cầu phần mềm
> `AP-<nhóm>-nn`), `prototype/index.html` (tám màn hình mẫu `MH-1` … `MH-8`).

---

## 1. Cách đọc

Ứng dụng này là lớp giao diện cho người trong gia đình: họ không viết YAML, gate hay hợp đồng. Gate và
hợp đồng vẫn tồn tại bên dưới, do hộp sinh ra, và chỉ hiện sau nút "Xem chi tiết". Hai ví dụ chạy xuyên
suốt:

- **Bể cá phòng khách:** agent bể cá có sẵn (`fixtures/agents/aquarium/agent.toml`): máy sưởi, máy sục
  khí, đèn, đầu dò nhiệt độ nước.
- **Nhà bố mẹ:** cảm biến cửa, radar nhà tắm, hộp thuốc, nút SOS. Đây là **ngành dọc tương lai**: chăm
  sóc người cao tuổi bị hoãn bởi Q-72 (PRD §14) và mang rủi ro pháp lý R-19. Ứng dụng **không phát hiện
  bệnh, không phát hiện té ngã**; chỉ báo người thân về thay đổi thói quen. Các story gắn "(eldercare)"
  chỉ áp dụng khi ngành dọc đó được mở bằng một quyết định mới.

Mức ưu tiên (Must / Should / Could) là cho **increment I2g, sau cổng nhu cầu** (Q-91 (1)); các story gắn eldercare
và chuỗi leo thang hoãn cùng ngành dọc người cao tuổi (Q-91 (7)).

Mã màn hình `MH-n` trỏ tới `prototype/index.html`. Không dùng `M1` … `M8` vì `M1`–`M9` trong repo là mục
tiêu sản phẩm.

---

## 2. Người dùng

| Mã | Người dùng | Vai trò với ứng dụng |
|:---|:---|:---|
| **P1** | Người trong gia đình | Chủ hộp: duyệt thay đổi, nhận cảnh báo. Thường là người con sống xa bố mẹ. |
| **P2** | Người được chăm sóc | Bố mẹ ở nhà. Không dùng ứng dụng; có thể bấm một nút "Tôi ổn" tại chỗ (giọng nói đã bỏ, Q-77). |
| **P3** | Người nhận leo thang | Người con thứ hai hoặc hàng xóm; chỉ nhận cảnh báo khẩn. |
| **P4** | Maker | Đóng gói Blueprint; khai báo khoảng chỉnh được và luật mặc định. |

---

## 3. Các story

Mẫu mỗi story: "Là …, tôi muốn …, để …"; tiêu chí chấp nhận dạng Given/When/Then (Cho / Khi / Thì);
màn hình mẫu; mức ưu tiên. Bên dưới mỗi story, phần "Dẫn" liệt kê mã đã có mà story dựa vào.

### US-APP-01 Xem tình trạng cả nhà trên một màn hình

**Persona:** P1 · **Ưu tiên:** Must · **Màn hình:** MH-1

Là người trong gia đình, tôi muốn thấy mọi nơi trong nhà (bể cá, nhà bố mẹ) trên một màn hình với trạng
thái đọc được trong vài giây, để biết có cần làm gì không mà không phải mở từng thiết bị.

1. **Cho** hộp đang chạy và bể cá đo được 26,8 °C trong khoảng cho phép, **khi** tôi mở tab Nhà, **thì**
   thẻ "Bể cá phòng khách" hiện nhiệt độ hiện tại, chữ "Ổn" và biểu đồ nhỏ của ngày gần nhất.
2. **Cho** một thẻ có việc cần chú ý, **khi** tôi mở tab Nhà, **thì** thẻ đó hiện chữ "Cần chú ý" kèm một
   câu lý do ngắn (ví dụ giờ dậy hôm qua), không chỉ đổi màu.
3. **Cho** có đề xuất đang chờ duyệt, **khi** tôi mở tab Nhà, **thì** có một dòng "n đề xuất chờ bạn
   duyệt" bấm vào được.
4. **Cho** dữ liệu của một thiết bị đã cũ, **khi** tôi mở tab Nhà, **thì** thẻ ghi "dữ liệu từ hh:mm"
   thay vì hiện như giá trị hiện tại.

Dẫn: BR-APP-01. Trạng thái dựa trên bộ phát hiện tất định (MS-RT-05, FR-AGT-04).

### US-APP-02 Nhận cảnh báo khẩn, bấm "Đã biết", thấy leo thang đang ở bước nào

**Persona:** P1 · **Ưu tiên:** Should (Must cho eldercare, sau này) · **Màn hình:** MH-1

Là người trong gia đình, tôi muốn nhận cảnh báo khẩn, bấm "Đã biết", và thấy chuỗi leo thang đang ở bước
nào, để biết cảnh báo đã đến ai và bao lâu nữa đến người kế.

1. **Cho** nhà bố mẹ chưa thấy hoạt động từ 7:00 và hộp đã hỏi tại chỗ mà chưa ai bấm OK, **khi** tôi mở
   ứng dụng, **thì** đầu tab Nhà có biểu ngữ khẩn nêu: đã hỏi tại chỗ, chưa ai bấm OK, đang báo bạn, và
   thời điểm báo người thứ hai.
2. **Cho** biểu ngữ khẩn, **khi** tôi bấm "Đã biết", **thì** cảnh báo được ghi nhận là đã xác nhận, kèm
   người bấm và giờ, và chuỗi leo thang dừng lại.
3. **Cho** biểu ngữ khẩn, **khi** tôi bấm "Gọi bố", **thì** điện thoại mở cuộc gọi; ứng dụng không tự
   quay số.
4. **Cho** nội dung cảnh báo, **khi** tôi đọc, **thì** câu chữ chỉ nói về thay đổi thói quen ("chưa thấy
   hoạt động"), không nói bệnh hay té ngã.

Dẫn: BR-APP-07; MS-RT-07, FR-AGT-06 (mẫu cố định, không LLM); Q-72, R-19, Q-38. Chuỗi leo thang và "Đã biết" chưa
có đặc tả đã duyệt (MS-RT-07 không có xác nhận); hoãn cùng ngành dọc người cao tuổi (Q-91 (7)), xem `03-srs.md` AP-AL-02, AP-AL-03.
Tín hiệu đẩy tới điện thoại không mang nội dung (AP-AL-11).

### US-APP-03 Hỏi AI về nhà, câu trả lời dựa trên số liệu thật

**Persona:** P1 · **Ưu tiên:** Must · **Màn hình:** MH-2

Là người trong gia đình, tôi muốn hỏi bằng lời thường ("Hôm nay bể thế nào?") và nhận câu trả lời nêu số
liệu thật của nhà, để không phải đọc biểu đồ.

1. **Cho** hộp có dữ liệu cảm biến hôm nay, **khi** tôi hỏi "Hôm nay bể thế nào?", **thì** câu trả lời
   nêu các giá trị cụ thể kèm giờ (ví dụ lúc 14:10 hộp không cho bật sưởi vì nước 29,1 °C).
2. **Cho** một con số trong câu trả lời, **khi** tôi bấm vào nó, **thì** tôi thấy sự kiện gốc trong nhật ký
   mà con số lấy từ đó.
3. **Cho** bộ não không chạy, **khi** tôi mở tab Chat, **thì** có thông báo "phân tích tạm ngưng" và các
   tab khác vẫn dùng được.

Dẫn: BR-APP-01, BR-APP-08; MS-RT-02.

### US-APP-04 Nói điều muốn đổi, nhận thẻ đề xuất

**Persona:** P1 · **Ưu tiên:** Must · **Màn hình:** MH-2

Là người trong gia đình, tôi muốn nói điều muốn đổi ("Giữ tầm 26–28 thôi") và nhận một thẻ đề xuất ngắn,
để quyết định mà không viết cấu hình.

1. **Cho** tôi nhắn "Giữ tầm 26–28 thôi", **khi** bộ não soạn xong, **thì** tôi nhận một thẻ nêu thay đổi
   bằng một câu ("Không bật sưởi khi nước từ 28 °C", hiện là 29 °C) với nút Chỉnh và Duyệt.
2. **Cho** thẻ đề xuất, **khi** tôi chưa duyệt, **thì** không có gì thay đổi trên thiết bị hay luật.
3. **Cho** tôi gõ "Có" hay "Đồng ý" vào khung chat, **khi** không có thẻ nào đang chờ trả lời, **thì**
   không có gì được duyệt.
4. **Cho** thẻ đề xuất quá dài để đọc trên chat, **khi** nó hiện ra, **thì** thẻ ghi phải duyệt tại nhà.

Dẫn: BR-APP-02; MS-AP-01, MS-AP-02, MS-AP-04, MS-CH-02.

### US-APP-05 Chỉnh con số bằng thanh trượt có ba vùng màu

**Persona:** P1 · **Ưu tiên:** Must · **Màn hình:** MH-4 (thanh trượt mở từ biểu tượng sửa của một luật)

Là người trong gia đình, tôi muốn kéo thanh trượt để đổi một con số và thấy ngay vùng nào là trong khoảng
maker cho phép, vùng nào không, để chỉnh mà không sợ.

1. **Cho** thanh trượt ngưỡng máy sưởi từ 24 đến 34 °C, bước 0,5, **khi** tôi kéo trong khoảng 25–29,
   **thì** thanh ở vùng xanh, ghi "Trong khoảng maker cho phép", nút là "Duyệt".
2. **Cho** thanh trượt đó, **khi** tôi kéo ra ngoài 25–29 nhưng còn trong thanh, **thì** thanh ở vùng vàng,
   ghi "Ngoài khoảng maker, có nhãn rủi ro" và nút đổi thành "Duyệt, chấp nhận rủi ro" (Q-91 (8); cần RFC, TSK-I2g-03).
3. **Cho** một con số mà `board.v1` đã khai giới hạn (ví dụ tần suất bật/tắt, `min_interval_ms`), **khi** tôi
   kéo quá giới hạn đó, **thì** thanh ở vùng khóa, ghi "Vượt giới hạn phần cứng" và tôi không áp dụng được.
   Giới hạn theo giá trị cảm biến (như 32 °C) do một RFC thêm vào `board.v1` (Q-91 (8), TSK-I2g-02).
4. **Cho** tôi không phân biệt được màu, **khi** nhìn thanh trượt, **thì** vùng vẫn đọc được qua chữ và
   biểu tượng.

Dẫn: BR-APP-02, BR-APP-03; BL-IN-04, TC-IN-04-1 (vùng xanh: ngoài khoảng đã khai bị hỏi lại hoặc từ chối),
MS-CT-06 (tham số `ask` có kiểu và khoảng); MS-CT-04, MS-CP-02, FR-ACE-03 (vùng khóa theo `board.v1`).
Vùng vàng đã quyết ở Q-91 (8) và chờ RFC (`03-srs.md` AP-D-01).

### US-APP-06 Duyệt qua hộp; AI không duyệt thay được

**Persona:** P1 · **Ưu tiên:** Must · **Màn hình:** MH-2, MH-8

Là người trong gia đình, tôi muốn duyệt mọi thay đổi bằng chính tay mình, qua hộp (ký bằng vân tay hoặc Face ID
trong app khi ở nhà; nút trên bot duyệt riêng của hộp khi ở ngoài), và chắc chắn AI không duyệt thay được, để người duy nhất quyết định là tôi.

1. **Cho** một thẻ đề xuất, **khi** tôi duyệt trong app bằng vân tay hoặc Face ID (ở nhà), hoặc bấm nút của bot duyệt của hộp (ngoài nhà), **thì** hộp
   kiểm bản ghi (ký bởi khóa thiết bị, hoặc do chính hộp ký cho bot) (đúng chủ, đúng digest, chưa hết hạn, chưa dùng, còn trong trần duyệt từ xa);
   thay đổi được khóa và có hiệu lực, và nhật ký ghi người duyệt, kênh và giờ.
2. **Cho** bộ não hoặc một ứng dụng MCP gửi một bản ghi duyệt giả, **khi** hộp nhận, **thì** hộp từ chối
   và ghi vào trace.
3. **Cho** điện thoại chưa ghép, **khi** tôi cần ghép, **thì** hộp hiện một mã dùng một lần (8 ký tự, 10 phút)
   chỉ trên máy nhà, tôi nhập mã vào app một lần để ghép với API của hộp trong mạng nhà, và gửi `/pair <mã>` cho bot duyệt từ cuộc chat riêng để duyệt ngoài nhà.
4. **Cho** một thẻ đã hết hạn, **khi** tôi bấm Duyệt, **thì** hộp coi là không duyệt.
5. **Cho** tôi đã duyệt từ xa tới trần mỗi giờ, **khi** tôi bấm Duyệt nữa, **thì** hộp từ chối và tôi phải
   duyệt tại nhà.
6. **Cho** tôi mất điện thoại, **khi** tôi chạy `neuroedge pair owner --revoke` trên hộp, **thì** tài khoản
   chat đó không còn duyệt được.

Dẫn: BR-APP-04; FR-CH-05, MS-CH-03, MS-CH-05, MS-AP-05; DP-A-05, DP-A-06; RFC-0019, Q-89; Q-91 (3), (5). Duyệt ký sinh trắc là
nguồn người mới, sớm hơn FR-CH-08 (TSK-I2f-08), cần RFC sửa RFC-0006 và RFC-0019 (TSK-I2g-01; `03-srs.md` AP-AV-04).

### US-APP-07 Xem "nếu áp dụng hôm qua" trước khi duyệt

**Persona:** P1 · **Ưu tiên:** Must · **Màn hình:** MH-2, MH-5

Là người trong gia đình, tôi muốn thấy luật mới sẽ làm gì nếu áp dụng cho ngày hôm qua, để biết trước nó
sẽ chặn hay báo bao nhiêu lần.

1. **Cho** một thẻ đề xuất đổi ngưỡng, **khi** thẻ hiện ra, **thì** thẻ có dòng như "Nếu áp dụng hôm qua:
   chặn thêm 1 lần", tính từ trace 24 giờ gần nhất của chính nhà này.
2. **Cho** kết quả chạy lại, **khi** tôi bấm vào, **thì** tôi thấy các thời điểm cụ thể (hh:mm) sẽ bị chặn
   hoặc báo.
3. **Cho** một cảm biến mới chưa có lịch sử, **khi** thẻ hiện ra, **thì** thẻ dùng kịch bản mẫu của
   Blueprint và nói rõ điều đó, hoặc ghi "xem lại sau 24 giờ".
4. **Cho** việc chạy lại, **khi** nó chạy, **thì** không thiết bị nào nhận lệnh và không luật nào đổi.

Dẫn: BR-APP-05; MS-TS-01, MS-TS-02 (trace chia đoạn, chạy lại từng đoạn).

### US-APP-08 Bấm bật/tắt thiết bị, thấy lý do khi hộp từ chối

**Persona:** P1 · **Ưu tiên:** Must · **Màn hình:** MH-3, MH-4

Là người trong gia đình, tôi muốn bấm bật hoặc tắt một thiết bị, và nếu hộp từ chối thì đọc được lý do
bằng lời thường, để hiểu chứ không bực.

1. **Cho** nước bể 29,1 °C, **khi** tôi bấm "Bật" máy sưởi, **thì** hộp từ chối và ứng dụng ghi lý do
   bằng câu thường ("nước đã 29,1 °C"), không hiện mã lỗi.
2. **Cho** máy sục khí luôn giữ bật, **khi** tôi nhìn tab Thiết bị, **thì** máy sục khí có biểu tượng khóa
   và ghi tắt thì hỏi tôi.
3. **Cho** một lệnh bị từ chối, **khi** tôi bấm "Xem chi tiết", **thì** tôi mới thấy tên gate và điều kiện
   kỹ thuật.

Dẫn: BR-APP-01; fixture bể cá (`fixtures/agents/aquarium/agent.toml`), MS-SF-06, MS-CP-06.

### US-APP-09 Thêm thiết bị qua trình hướng dẫn, không viết cấu hình

**Persona:** P1 · **Ưu tiên:** Should (đường có dây là Must) · **Màn hình:** MH-6

Là người trong gia đình, tôi muốn thêm một thiết bị qua các bước có hướng dẫn, và thử trực tiếp trước khi
hộp ghi nhận, để không phải viết cấu hình.

1. **Cho** tôi đang ở bước "Thử trực tiếp", **khi** tôi mở rồi đóng cửa nhà tắm một lần, **thì** ứng dụng
   hiện đã thấy mở lúc nào, đóng lúc nào.
2. **Cho** thiết bị đấu dây, **khi** ở bước đấu dây, **thì** ứng dụng nói dạng "dây đỏ vào chân số 3" và
   chỉ ở bước này mới hiện số chân.
3. **Cho** cảm biến không dây (ví dụ Zigbee), **khi** tôi chọn, **thì** ứng dụng nói rõ đường này chờ code của
   RFC-0014 (đã duyệt, code hoãn sau v1.0), chưa dùng được; cơ cấu chấp hành từ xa qua Home Assistant
   (RFC-0018) đã có.
4. **Cho** kết thúc trình hướng dẫn, **khi** tôi bấm xong, **thì** thay đổi hiện thành một thẻ duyệt, chưa
   có hiệu lực cho đến khi tôi duyệt; gate sinh ra đã qua `neuroedge gate lint` và chỉ được khóa bằng lời duyệt ký bằng vân tay hoặc Face ID tại nhà (Q-91 (9), cần RFC, TSK-I2g-04).

Dẫn: BR-APP-02, BR-APP-06; danh mục `python/neuroedge/hal/parts.toml`, `neuroedge add part`,
`python/neuroedge/hal/pin_map.py` (TSK-I2d-32). Trình hướng dẫn chạy trên `sim` và board thật (Q-91 (9), TSK-I2g-09);
canvas kéo thả vẫn hoãn (Q-84, TSK-I2d-31): xem `03-srs.md` AP-DV-06.

### US-APP-10 Gỡ thiết bị an toàn

**Persona:** P1 · **Ưu tiên:** Should · **Màn hình:** chưa có màn hình

Là người trong gia đình, tôi muốn gỡ một thiết bị mà không để nó kẹt ở trạng thái nguy hiểm hay làm hỏng
luật đang dùng nó, để dọn nhà an tâm.

1. **Cho** máy sưởi đang bật, **khi** tôi gỡ nó, **thì** hộp đưa nó về trạng thái an toàn trước rồi mới
   gỡ.
2. **Cho** một luật đang dùng thiết bị, **khi** tôi gỡ, **thì** ứng dụng liệt kê luật đó và cảnh báo trước
   khi tôi duyệt.
3. **Cho** thiết bị đã gỡ, **khi** tôi mở nhật ký, **thì** lịch sử trước đó vẫn đọc được.

Dẫn: BR-APP-06; `python/neuroedge/hal/remote.py` (RFC-0018, TSK-I2c-16: "off debt", tắt về an toàn không
bị từ chối).

### US-APP-11 Đọc hoạt động như nhật ký, lọc bị chặn / cảnh báo / đã duyệt

**Persona:** P1 · **Ưu tiên:** Must · **Màn hình:** MH-5

Là người trong gia đình, tôi muốn đọc những gì đã xảy ra như một cuốn nhật ký và lọc theo loại, để biết
hộp đã làm gì thay tôi.

1. **Cho** tab Hoạt động, **khi** tôi mở, **thì** các mục xếp theo thời gian giảm dần, mỗi mục một câu
   thường.
2. **Cho** các bộ lọc Tất cả / Bị chặn / Cảnh báo / Đã duyệt, **khi** tôi chọn "Bị chặn", **thì** chỉ còn
   các mục bị chặn, mỗi mục nêu lý do và giá trị lúc đó.
3. **Cho** một mục đã duyệt, **khi** tôi đọc, **thì** mục ghi ai duyệt, bằng cách nào (vân tay hoặc Face ID trong app, bot duyệt của hộp,
   trang cục bộ) và lúc nào.
4. **Cho** nút "Chạy lại hôm qua với luật hiện tại", **khi** tôi bấm, **thì** tôi nhận kết quả như
   US-APP-07, ở chế độ chỉ đọc.

Dẫn: BR-APP-01, BR-APP-08; MS-TS-03 (giữ 30 ngày trên hộp).

### US-APP-12 Quản lý người trong gia đình, vai trò, thứ tự leo thang

**Persona:** P1 · **Ưu tiên:** Could · **Màn hình:** MH-7

Là người trong gia đình, tôi muốn đặt ai duyệt, ai chỉ nhận cảnh báo khẩn và ai được báo sau bao lâu, để
cảnh báo đi đúng người.

1. **Cho** danh sách "Bạn: duyệt + khẩn cấp; Con thứ hai: khẩn cấp; Hàng xóm: sau 10 phút", **khi** tôi mở
   Cài đặt, **thì** tôi thấy đúng danh sách và thứ tự đó.
2. **Cho** một người chỉ có vai trò khẩn cấp, **khi** họ cố duyệt một thay đổi, **thì** hộp từ chối.
3. **Cho** tôi đổi thứ tự hoặc vai trò, **khi** tôi lưu, **thì** thay đổi đi qua thẻ duyệt.

Dẫn: BR-APP-07; FR-CH-07 (nhiều người dùng và vai trò, dự kiến, TSK-I2f-05). Trước đó chỉ có một chủ hộp được
ghép (Q-89). Thứ tự leo thang hoãn cùng ngành dọc người cao tuổi (Q-91 (7)).

### US-APP-13 Chọn kênh báo: Zalo, SMS qua 4G, gọi tự động, Telegram

**Persona:** P1 · **Ưu tiên:** Could (Telegram là Must) · **Màn hình:** MH-7

Là người trong gia đình, tôi muốn chọn cảnh báo đến qua kênh nào, để cảnh báo khẩn không lọt vì tôi không
dùng kênh đó.

1. **Cho** Telegram là kênh của hộp, **khi** tôi ghép kênh, **thì** cảnh báo và thẻ duyệt đến
   qua Telegram, và điện thoại nhận thêm một thông báo đẩy qua APNs hoặc FCM chỉ nói "có việc cần bạn", không kèm nội dung (Q-91 (7)).
2. **Cho** tôi bật thêm Zalo (P1), SMS qua 4G hoặc gọi tự động, **khi** tôi lưu, **thì** mỗi kênh mới là một
   đích khai báo và chỉ được thêm khi tôi duyệt tại nhà.
3. **Cho** kênh chat đang sập, **khi** có cảnh báo, **thì** cảnh báo hiện trên trang cục bộ và nằm trong
   hàng đợi với giờ gốc.

Dẫn: BR-APP-07; FR-CH-01 (Telegram trước, Zalo sau), Q-91 (7), TSK-I2d-12, TSK-I2g-10; MS-EG-01, MS-AP-04; MS-RT-08.

### US-APP-14 Thấy rủi ro đang bật và ngân sách AI

**Persona:** P1 · **Ưu tiên:** Should · **Màn hình:** MH-7

Là người trong gia đình, tôi muốn thấy những rủi ro tôi đã chọn chấp nhận và AI đã dùng bao nhiêu ngân
sách, để biết mình đang ở đâu.

1. **Cho** sục khí tắt được từ xa, **khi** tôi mở Cài đặt, **thì** danh sách rủi ro đang bật ghi điều đó.
2. **Cho** ngân sách AI của kỳ, **khi** tôi mở Cài đặt, **thì** tôi thấy đã dùng bao nhiêu trên trần bao
   nhiêu.
3. **Cho** ngân sách đã hết, **khi** tôi mở Chat, **thì** tôi được báo hết ngân sách phân tích kỳ này;
   thiết bị và cảnh báo khẩn vẫn chạy.

Dẫn: BR-APP-08; Q-73 (nhãn rủi ro), MS-CT-05, MS-RT-06, NFR-COST-01. Nhãn do tài liệu đã duyệt định nghĩa
(`risk=remote_approval` của RFC-0019, DP-COM-06); số tiền ngân sách do bộ não báo, hộp không thấy hóa đơn LLM
(Q-87).

### US-APP-15 Cài Blueprint, đọc tóm tắt trước khi duyệt

**Persona:** P1 · **Ưu tiên:** Should · **Màn hình:** MH-8

Là người trong gia đình, tôi muốn cài một Blueprint và đọc ba câu nó sẽ làm trước khi duyệt, để cài mà không
phải mở máy tính.

1. **Cho** tôi mở một Blueprint (tên trong chỉ mục hoặc địa chỉ, BL-IN-01) trong ứng dụng, **khi** hộp tạo tóm
   tắt, **thì** thẻ "Hộp bể cá sẽ:" nêu ba câu thường (không bật sưởi khi nước từ 29 °C; luôn giữ sục khí, tắt
   thì hỏi bạn; báo khi sưởi bật mà không ấm).
2. **Cho** thẻ cài, **khi** tôi đọc, **thì** thẻ có đủ phần tóm tắt của BL-IN-03, mỗi bằng chứng ghi "unsigned"
   (BL-EV-03), và cho biết digest được đối chiếu với đâu hoặc xin tôi xác nhận (BL-IN-02); thẻ không ghi
   "đã qua Action CI".
3. **Cho** tôi chưa duyệt, **khi** thẻ còn mở, **thì** không tệp nào của gói chạy.
4. **Cho** nút Từ chối, **khi** tôi bấm, **thì** không có gì được cài.
5. **Cho** tôi duyệt, **khi** hộp cài, **thì** gói được ghi vào một thư mục mới, không bao giờ vào thư mục có
   sẵn không rỗng (BL-IN-06).
6. **Cho** gói khai đích mạng, **khi** tôi định duyệt trên điện thoại, **thì** thẻ ghi phải duyệt tại nhà.

Dẫn: BR-APP-02; BL-IN-01 → BL-IN-03, BL-IN-05, BL-IN-06, BL-EV-03; FR-MSN-14; TSK-I2e-03. Không có cơ chế đã
duyệt để một Blueprint tự yêu cầu được cài; thông báo trên màn hình khóa không mang nội dung (Q-91 (7)), thẻ cài hiện
trong app sau khi mở (MH-8, TSK-I2g-07; `03-srs.md` AP-CD-09, AP-AL-11).

### US-APP-16 Khai báo khoảng chỉnh được và luật mặc định cho Blueprint

**Persona:** P4 · **Ưu tiên:** Must · **Màn hình:** chưa có màn hình

Là maker, tôi muốn khai báo khoảng người dùng được chỉnh cho từng con số và luật mặc định theo loại thiết
bị trong Blueprint của mình, để người cài chỉ chỉnh trong khoảng tôi đã kiểm chứng.

1. **Cho** một tham số có kiểu và khoảng, **khi** tôi đóng gói Blueprint, **thì** khoảng đó là vùng xanh
   của thanh trượt trong ứng dụng.
2. **Cho** một khoảng rộng hơn giới hạn phần cứng của board, **khi** tôi đóng gói, **thì** gói bị từ chối
   và nêu tham số nào.
3. **Cho** một tham số nhắm vào tệp gate, **khi** tôi đóng gói, **thì** gói không hợp lệ.

Dẫn: BR-APP-03, BR-APP-09; MS-CT-06, BL-IN-04, MS-CP-02.

### US-APP-17 Bấm "Tôi ổn" tại chỗ khi hộp hỏi

**Persona:** P2 · **Ưu tiên:** Could (eldercare) · **Màn hình:** chưa có màn hình

Là người được chăm sóc, tôi muốn bấm một nút "Tôi ổn" khi hộp hỏi tại chỗ, để người nhà không bị báo vô
ích và tôi không cần dùng điện thoại.

1. **Cho** hộp hỏi tại chỗ trên nút bấm, **khi** tôi bấm "Tôi ổn" trong thời gian chờ, **thì**
   cảnh báo dừng và việc bấm được ghi vào nhật ký.
2. **Cho** tôi không bấm trong thời gian chờ, **khi** hết giờ, **thì** chuỗi leo thang chuyển sang bước
   báo người thân.
3. **Cho** bộ não hay một ứng dụng MCP gửi tín hiệu "Tôi ổn", **khi** hộp nhận, **thì** hộp coi là không
   hợp lệ.

Dẫn: BR-APP-07; MS-CH-07, FR-CH-05; Q-72, R-19; Q-91 (7) (hoãn cùng ngành dọc người cao tuổi). Giọng nói đã bỏ (Q-77); bước xác minh cần TSK-I2d-20,
TSK-I2d-21 (MS-CH-06, MS-CH-07).

### US-APP-18 Biết khi hộp mất liên lạc (relay canh hộp)

**Persona:** P1 / P3 · **Ưu tiên:** Could · **Màn hình:** MH-7

Là người trong gia đình hoặc người nhận leo thang, tôi muốn được báo khi hộp ở nhà im lặng, để biết hộp
hỏng hay mất mạng thay vì tưởng nhà bình thường.

1. **Cho** relay đặt ngoài nhà nhận tín hiệu từ hộp, **khi** tôi mở Cài đặt, **thì** tôi thấy "tín hiệu
   30 giây trước" (giá trị mẫu).
2. **Cho** hộp im lặng quá ngưỡng đã đặt, **khi** relay không nhận tín hiệu, **thì** người nhận được báo
   hộp mất liên lạc kèm giờ tín hiệu cuối.
3. **Cho** chưa có relay, **khi** tôi mở Cài đặt, **thì** mục này ghi chưa bật và nêu lý do (cần relay
   hoặc cloud, Q-74).

Dẫn: BR-APP-07; FR-EGR-05 (relay tùy chọn), Q-74 (bước 2, sau cổng nhu cầu), Q-91 (7) (hoãn cùng ngành dọc người cao tuổi).

---

## 4. Bản đồ story theo tab

| Tab | Story |
|:---|:---|
| **Nhà** | US-APP-01, US-APP-02 |
| **Chat** | US-APP-03, US-APP-04, US-APP-06, US-APP-07 |
| **Thiết bị** | US-APP-05, US-APP-08, US-APP-09, US-APP-10, US-APP-17 |
| **Hoạt động** | US-APP-11 |
| **Cài đặt** | US-APP-12, US-APP-13, US-APP-14, US-APP-18 |
| **Maker** | US-APP-16 |
| **Ngoài tab (thông báo đẩy không nội dung, rồi mở thẻ trong app)** | US-APP-15 |

Ghi chú: US-APP-05 và US-APP-06 xuất hiện ở nhiều chỗ vì thanh trượt và việc duyệt dùng chung một thẻ
(`BR-APP-02`); bảng trên đặt theo màn hình chính. US-APP-17 chạy trên thiết bị cục bộ, không phải màn
hình của ứng dụng; US-APP-10 và US-APP-16 chưa có màn hình mẫu.
