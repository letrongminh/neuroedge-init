# Hướng dẫn phỏng vấn — cổng nhu cầu 2026-10-25

Kiểu **The Mom Test**: hỏi về chuyện đã xảy ra và cái giá thật, không hỏi ý kiến về sản phẩm. Không
nói về NeuroEdge trước khi xong phần câu hỏi vấn đề. Mã giả thuyết dẫn về `README.md` §2 và
`cham-diem.md`.

## 0. Luật cho người phỏng vấn

| Luật | Làm | Không làm |
|:---|:---|:---|
| Quá khứ, không tương lai | "Lần gần nhất … là khi nào? Kể lại." | "Anh có dùng không?", "Anh có trả tiền không?" |
| Họ nói con số trước | Hỏi "tốn gì?", để im, chờ | Gợi ý "chắc cũng vài triệu?" |
| Đào tới cái giá | "Rồi sao nữa?" · "Ai phải xử lý?" · "Mất bao lâu?" | Dừng ở "phiền lắm" |
| Khen không phải dữ liệu | Quay lại: "Lần gần nhất chuyện đó xảy ra là khi nào?" | Ghi "khách thích" vào bản ghi |
| Không pitch | Nếu họ hỏi "các anh làm gì?": "Tôi kể ở cuối, giờ tôi muốn hiểu cách anh đang làm" | Mở demo giữa chừng |
| Tìm cam kết | Cuối buổi xin một thứ có giá: giới thiệu người, buổi thứ hai với đội, một nhật ký sự cố đã ẩn danh | Kết bằng "anh thấy ý tưởng thế nào?" |

**Người ghi** ghi nguyên văn và đánh dấu: (a) **thời điểm con số đầu tiên** xuất hiện, (b) **ai nói
trước** (người được phỏng vấn hay người hỏi). Đó là điều kiện "không gợi ý" của C1
(`docs/designs/giai-doan-1-wedge-truoc-mcu-sau.md` §Success Criteria).

Thời lượng: 45 phút. Mở đầu 5' · câu hỏi phân khúc 25' · kết 5' · demo 10' (tuỳ chọn, `demo.md`).
Không cần hỏi hết; ưu tiên các câu có dấu ★.

Quy ước cột:

- **Mã** — giả thuyết câu hỏi kiểm: `P1` (có nỗi đau có số) · `CEO-X2` (quy mô + trả theo thiết bị) ·
  `CEO-X4` (A / C / E) · `CEO-X5` (ai trả, qua đường nào) · `CEO-T1` (P3: offline, đổi chip) ·
  `CEO-T2` (chứng nhận) · `CEO-T3` (đối thủ thật) · `G-e` (chuyến đi hiện trường) · `G-d` (dùng lại
  chính sách).
- **Mạnh** / **Yếu** — tín hiệu nghe thấy.

## 1. Mở đầu chung (mọi phân khúc)

| # | Nói / hỏi | Mục đích |
|:---:|:---|:---|
| O1 | "Cảm ơn anh/chị. Tôi xin ghi âm/ghi chép để không hiểu sai; bản ghi không chia sẻ ra ngoài nhóm, khi dùng sẽ bỏ tên người và tên công ty. Anh/chị đồng ý chứ?" | Đồng ý ghi; không đồng ý thì chỉ ghi tay |
| O2 | "Hôm nay tôi không bán gì. Tôi đang tìm hiểu cách các đội xử lý khi thiết bị tự động làm một việc sai ngoài đời thật." | Khung vấn đề, không nhắc sản phẩm |
| O3 | "Công việc hằng ngày của anh/chị là gì, và phần nào dính tới thiết bị ngoài hiện trường?" | Vai trò; xác nhận đúng người (`README.md` §3) |
| O4 | "Trong 12 tháng qua, anh/chị trực tiếp xử lý hay ký tiền cho thiết bị nào?" | Sàng lọc; không có thì chuyển sang hỏi giới thiệu |

## 2. Khách sạn / nghỉ dưỡng

Người: chủ / quản lý vận hành villa, resort 10–80 căn; trưởng kỹ thuật tòa nhà.

| # | Câu hỏi | Mã | Mạnh | Yếu |
|:---:|:---|:---|:---|:---|
| H1 | Anh/chị đang vận hành bao nhiêu căn, và mỗi căn có những thiết bị nào tự mở, đóng hay bật được (khóa, điều hòa, rèm, đèn)? | `CEO-X2` | Đếm được theo loại: "42 căn, mỗi căn khóa điện tử + 2 điều hòa" | "Cũng kha khá" |
| H2 ★ | Kể lần gần nhất một thiết bị trong phòng làm sai: khóa không mở, mở sai, điều hòa tự bật. Chuyện diễn ra thế nào? | `P1` | Ngày, căn, chuỗi sự việc cụ thể | "Thỉnh thoảng cũng bị" |
| H3 ★ | Lần đó tốn gì: tiền đền, hoàn tiền phòng, giờ nhân viên, đánh giá xấu? | `P1` · `CEO-X5` | Tự nêu số: "hoàn 1 đêm, 3 triệu", "một review 1 sao" | "Chắc không nhiều", phải gợi ý mới ra số |
| H4 | Lúc đó ai bị gọi, và họ làm gì đầu tiên? | `G-e` | Tên vai trò, thời gian phản ứng, phải tới tận nơi | "Có người lo" |
| H5 | Sau đó làm sao biết chính xác chuyện gì đã xảy ra? Có nhật ký không, ai xem? | `G-e` · `CEO-T3` | Mô tả cách tra nhật ký hiện có, và chỗ nó không đủ | "Cũng không cần biết" |
| H6 ★ | 12 tháng qua, bao nhiêu lần phải cho người tới tận căn chỉ vì thiết bị? Bao nhiêu lần hóa ra là cài đặt hay phần mềm? | `G-e` | Có số và có phân loại | Không ai đếm |
| H7 | Thiết bị do ai lắp, ai cập nhật phần mềm? Lần cập nhật gần nhất diễn ra thế nào? | `CEO-X5` · `CEO-T3` | Tên nhà cung cấp, sự cố khi cập nhật | "Nhà cung cấp lo hết" (người trả tiền có thể là nhà cung cấp) |
| H8 ★ | Hằng tháng hoặc hằng năm, anh/chị đang trả những khoản gì cho hệ thống khóa và thiết bị (phần mềm, tích hợp PMS, bảo trì)? Tính theo gì? | `CEO-X2` | Khoản cụ thể, đơn vị tính (theo phòng / thiết bị / năm) | "Mua một lần là xong" |
| H9 ★ | Lần gần nhất mua hệ thống khóa hay thiết bị phòng: ai ký, cân nhắc bao lâu, so với những lựa chọn nào? | `CEO-X5` · `CEO-T3` | Tên vai trò ký, các lựa chọn đã so | "Để tôi hỏi sếp" mà không biết là ai |
| H10 | Khi thiết bị gây sự cố cho khách, theo hợp đồng thì ai chịu trách nhiệm? Đã từng tranh chấp chưa? | `CEO-X5` · `CEO-T2` | Một lần tranh chấp thật, điều khoản cụ thể | "Chưa nghĩ tới" |
| H11 | Khách mất thẻ, về khuya, hay muốn mở cửa cho người thân: hôm nay quy trình là gì? Có lần nào quy trình đó bị làm sai không? | `CEO-X4` · `P1` | Mô tả quy trình và một lần sai | "Lễ tân tự xử" |
| H12 | Mất mạng hay mất điện đã từng ảnh hưởng tới khóa hay thiết bị phòng chưa? | `CEO-T1` | Sự cố có ngày, có hậu quả | "Chưa bao giờ" |
| H13 | Khi mở thêm căn mới, anh/chị có dùng lại cấu hình, quy trình của căn cũ, của nhà cung cấp hay của chuỗi khác không? | `G-d` | Kể một lần sao chép thật, từ ai | "Mỗi căn một kiểu" |

## 3. Fleet Operators

Người: trưởng vận hành / kỹ thuật của đơn vị đang quản lý 100–10.000 thiết bị đã lắp.

| # | Câu hỏi | Mã | Mạnh | Yếu |
|:---:|:---|:---|:---|:---|
| F1 ★ | Đội thiết bị của anh/chị: bao nhiêu máy, loại gì, bao nhiêu máy có rơ-le, khóa hay motor? Ở bao nhiêu điểm? | `CEO-X2` | Con số có tách loại: "3.200 tủ, 2.900 có khóa điện" | "Vài nghìn" không tách |
| F2 ★ | Kể sự cố gần nhất khi thiết bị làm một hành động vật lý sai, hoặc không làm được. | `P1` | Ngày, số máy bị ảnh hưởng, nguyên nhân gốc | "Lỗi vặt thôi" |
| F3 ★ | Sự cố đó tốn bao nhiêu: chuyến đi, giờ kỹ sư, tiền đền, thiết bị hỏng? | `P1` · `G-e` | Tự nêu số | Không có số hoặc phải gợi ý |
| F4 ★ | Tháng trước có bao nhiêu chuyến ra hiện trường? Có ai phân loại nguyên nhân không? Bao nhiêu phần là phần mềm hay cấu hình? | `G-e` | Có phiếu, có thống kê | Không đếm |
| F5 | Lần cập nhật firmware hay cấu hình gần nhất cho cả đội: làm thế nào, có chia đợt không, có máy nào hỏng không? | `CEO-X2` · `CEO-X4` | Quy trình cụ thể, số máy hỏng | "Bấm cập nhật là xong" |
| F6 ★ | Hôm nay các anh dùng công cụ gì cho cập nhật, giám sát, nhật ký? Tự viết hay mua? Mỗi tháng tốn bao nhiêu, tính theo gì? | `CEO-X2` · `CEO-T3` | Tên công cụ, hóa đơn, đơn vị tính (thiết bị / tháng) | "Có hệ thống riêng" không rõ chi phí |
| F7 | Nếu tự viết: bao nhiêu người, mất bao lâu, ai bảo trì bây giờ? | `CEO-T3` | Số người × số tháng | "Làm tranh thủ" |
| F8 | Khi một máy lỗi, kỹ sư biết chuyện gì đã xảy ra bằng cách nào? Tái hiện lỗi mất bao lâu? | `G-e` · `CEO-X4` | Mô tả cách làm và thời gian | "Xem log là biết" không kể được lần nào |
| F9 ★ | Trước khi đổi một ngưỡng hay quy tắc điều khiển trên cả đội, các anh kiểm bằng gì? Đã lần nào đổi xong phải quay lui chưa? | `CEO-X4` | Một lần quay lui có hậu quả | "Chưa phải đổi" |
| F10 | Mất kết nối thì thiết bị làm gì? Lệnh đang chờ thì sao? Đã có chuyện gì vì thế chưa? | `CEO-T1` | Sự cố cụ thể | "Luôn có mạng" |
| F11 | Dùng chip / bo mạch nào? Đã đổi lần nào chưa, đổi mất bao lâu? | `CEO-T1` · `CEO-T3` | Một lần đổi, thời gian, phần phải viết lại | "Không bao giờ đổi" |
| F12 ★ | Ai giữ ngân sách cho công cụ vận hành? Lần mua gần nhất là gì, từ lúc đề xuất tới lúc ký mất bao lâu? | `CEO-X5` | Tên vai trò, một lần mua thật | Không biết ai |
| F13 | Khách hàng của các anh có đòi bằng chứng hay nhật ký khi có sự cố không? Đã phải nộp lần nào chưa? | `CEO-X5` | Một lần nộp thật, định dạng | "Không ai hỏi" |
| F14 | Hợp đồng với khách của các anh tính theo thiết bị, theo điểm, hay theo dự án? | `CEO-X2` | Đơn vị tính rõ | — (câu phân loại) |

## 4. Smart Home

Người: trưởng nhóm sản phẩm / nhúng của hãng thiết bị nhà; đơn vị tích hợp nhà thông minh.

| # | Câu hỏi | Mã | Mạnh | Yếu |
|:---:|:---|:---|:---|:---|
| S1 | Sản phẩm hay dự án hiện tại điều khiển những gì? 12 tháng qua bán hoặc lắp bao nhiêu đơn vị? | `CEO-X2` | Số đơn vị | "Đang làm mẫu" (ghi: chưa có thiết bị ngoài đời) |
| S2 ★ | Kể lần gần nhất sản phẩm làm một việc vật lý sai (tắt đèn, mở cổng, mở khóa) vì hiểu nhầm lệnh, lỗi logic, cập nhật, hay mất mạng. | `P1` · `CEO-T1` | Ngày, nguyên nhân, số khách bị ảnh hưởng | "Về lý thuyết có thể" |
| S3 ★ | Lần đó phát hiện thế nào (khách báo, review, bảo hành)? Tốn gì? | `P1` | Tự nêu số: giờ, tiền bảo hành, lượng trả hàng | Không có số |
| S4 ★ | Khi đổi logic điều khiển hoặc đổi mô hình giọng nói / AI, trước khi phát hành các anh kiểm những gì? Mỗi lần mất bao lâu? | `CEO-X4` | Quy trình thủ công cụ thể, số giờ | "QA test" không kể được |
| S5 ★ | Đã lần nào một bản cập nhật làm hỏng một hành vi đã chạy tốt trước đó chưa? | `CEO-X4` · `P1` | Một lần thật, phát hiện muộn | "Chưa" |
| S6 | Hôm nay dùng SDK hay nền tảng gì (của hãng chip, nền tảng nhà thông minh, tự viết)? Vì sao chọn nó? | `CEO-T3` | Tên cụ thể và lý do đã cân nhắc | — |
| S7 | Đã đổi chip hay bo mạch lần nào chưa? Phải viết lại những phần nào, mất bao lâu? | `CEO-T1` | Số tuần, phần viết lại | "Chưa bao giờ đổi" |
| S8 | Sản phẩm có phải chạy khi mất internet không? Khách đã phàn nàn chuyện đó chưa? | `CEO-T1` | Phàn nàn thật, yêu cầu trong hợp đồng | "Chắc cần" |
| S9 | Có cho LLM hoặc agent bên ngoài điều khiển thiết bị không (tích hợp trợ lý, MCP, function calling)? Chặn lệnh nguy hiểm bằng cách nào? | `CEO-X4` · `CEO-T3` | Có tích hợp, mô tả cách chặn hiện tại và chỗ hở | "Đang tìm hiểu" |
| S10 | Đội bao nhiêu người; bao nhiêu làm firmware, bao nhiêu làm AI hay giọng nói? | `CEO-X5` | Số người theo vai trò | — (câu phân loại) |
| S11 ★ | Năm ngoái tiền cho công cụ phát triển, kiểm thử, quản lý thiết bị chi vào những gì? Bao nhiêu? Ai duyệt? | `CEO-X2` · `CEO-X5` | Khoản cụ thể, người duyệt | "Toàn đồ miễn phí" |
| S12 | Sau khi bán, ai vận hành thiết bị: các anh, đối tác lắp đặt, hay chủ nhà? Có phí dịch vụ hằng tháng không, ai trả? | `CEO-X5` | Mô hình phí có thật | "Bán đứt" |
| S13 | Có tiêu chuẩn hay chứng nhận nào bắt buộc để bán sản phẩm này không? | `CEO-T2` | Tên tiêu chuẩn họ tự nêu, chi phí | — (câu phân loại) |
| S14 | Có lần nào dùng lại logic, kịch bản hay cấu hình từ cộng đồng hay từ hãng khác không? | `G-d` | Một lần thật | "Không tin đồ người khác" (ghi lại: tín hiệu ngược với G-d) |

## 5. Industrial IoT

Người: kỹ sư tự động hóa, trưởng bảo trì, người phụ trách an toàn.

| # | Câu hỏi | Mã | Mạnh | Yếu |
|:---:|:---|:---|:---|:---|
| I1 | Máy hay hệ thống anh/chị phụ trách có những cơ cấu chấp hành nào, bao nhiêu điểm? | `CEO-X2` | Đếm được | — |
| I2 ★ | Kể lần gần nhất một lệnh điều khiển chạy khi không nên chạy, hoặc không chạy khi cần. | `P1` | Ngày, máy, nguyên nhân | "Hệ thống an toàn rồi" |
| I3 ★ | Lần đó thiệt hại gì: dừng dây chuyền bao lâu, hỏng gì, có ai bị nguy hiểm không? | `P1` | Tự nêu số: giờ dừng, chi phí | Không số |
| I4 ★ | Điều kiện khóa liên động hôm nay nằm ở đâu: PLC, rơ-le an toàn, SCADA, firmware? Ai được sửa? | `CEO-T1` · `CEO-T3` | Mô tả cụ thể, số người được sửa | — |
| I5 ★ | Lần sửa khóa liên động hay ngưỡng gần nhất: duyệt thế nào, kiểm thử thế nào, mất bao lâu? | `CEO-X4` · `CEO-T1` | Quy trình, số ngày, chỗ đau | "Nhà thầu làm" |
| I6 ★ | Hệ thống phải theo tiêu chuẩn an toàn nào? Chứng nhận do ai làm, tốn bao lâu, bao nhiêu? | `CEO-T2` | Họ **tự nêu** tên tiêu chuẩn và chi phí | Không biết (ghi: người sai vai trò?) |
| I7 ★ | Một phần mềm không có chứng nhận có được phép quyết định chạy hay dừng máy không? Ở đâu thì được (giám sát, cảnh báo, lớp phía trên PLC), ở đâu thì không? | `CEO-T2` | Ranh giới rõ, có ví dụ đang dùng | — (câu phân loại) |
| I8 | Có đang hoặc định cho AI hay hệ thống bên ngoài ra lệnh cho thiết bị không? Ai phản đối, vì sao? | `CEO-X4` · `CEO-T2` | Dự án có thật, lý do phản đối cụ thể | "Chắc sau này" |
| I9 | Khi có sự cố, điều tra bằng dữ liệu gì? Có tái hiện lại được không? | `G-e` | Mô tả dữ liệu và chỗ thiếu | — |
| I10 | Mất kết nối mạng thì thiết bị làm gì? Đã từng có chuyện gì vì thế chưa? | `CEO-T1` | Sự cố cụ thể | "Mạng nội bộ không mất" |
| I11 ★ | Lần gần nhất mua công cụ hay phần mềm cho vận hành: mua gì, bao nhiêu, ai ký, mất bao lâu? | `CEO-X5` · `CEO-X2` | Một lần mua thật | Không biết |
| I12 | Nhà cung cấp phần điều khiển hiện tại là ai, hợp đồng tính theo gì? | `CEO-T3` · `CEO-X2` | Tên, đơn vị tính | — |
| I13 | Các site khác trong công ty có dùng lại cấu hình an toàn của nhau không? Ai giữ bản chuẩn? | `G-d` | Kể một lần dùng lại | "Mỗi site tự làm" |

## 6. Kết chung (mọi phân khúc)

| # | Hỏi | Mã | Mạnh | Yếu |
|:---:|:---|:---|:---|:---|
| E1 | "Có điều gì tôi nên hỏi mà chưa hỏi không?" | — | Họ tự mở một vấn đề mới | — |
| E2 ★ | "Ai khác tôi nên nói chuyện, trong hoặc ngoài công ty anh/chị?" | cam kết | Giới thiệu tên và nhắn luôn | "Để tôi nghĩ" |
| E3 | "Tôi có một thứ 5 phút liên quan tới chuyện anh/chị vừa kể. Anh/chị muốn xem không?" → `demo.md` phân khúc tương ứng | — | Muốn xem, hỏi tiếp chi tiết kỹ thuật | Lịch sự đồng ý rồi nhìn đồng hồ |
| E4 ★ | Sau demo, xin **một** cam kết: buổi thứ hai với người kỹ thuật của họ · một nhật ký sự cố đã ẩn danh · thử trên 1 thiết bị của họ · giới thiệu người ký tiền | cam kết | Đồng ý có ngày, có người | "Gửi tài liệu cho tôi" |
| E5 | "Tôi có thể liên hệ lại khi có bản chạy trên thiết bị thật không?" | — | Có, và cho kênh liên hệ trực tiếp | — |

Sau demo, **không** hỏi "anh thấy thế nào?" hay "anh có mua không?". Chỉ hỏi hai câu cuối của kịch bản
demo tương ứng (`demo.md`, mục "Hỏi sau demo") và E4.

## 7. Sau mỗi cuộc (trong 24 giờ)

1. Người ghi làm sạch bản ghi: trích nguyên văn mọi câu có số, ghi thời điểm và ai nói trước.
2. Trưởng nhóm chấm sơ bộ theo `cham-diem.md` §2; người chấm thứ hai chấm độc lập trước 10-22.
3. Điền một dòng vào bảng tổng hợp (mã ẩn danh `HS-01`, `FL-01`, `SH-01`, `IN-01`…), **không** tên
   người, không tên công ty.
4. Nếu người đó điền khảo sát, nối mã khảo sát với mã phỏng vấn trong bảng tiếp cận (ngoài kho).
