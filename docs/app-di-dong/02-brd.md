# Tài liệu yêu cầu kinh doanh (BRD): ứng dụng di động NeuroEdge ("app nhà")

> **Bản nháp đề xuất**, 2026-10-16. **Chưa có quyết định (`Q-N`) nào cho ứng dụng này, chưa có task nào
> trong roadmap, và tài liệu này không đổi gì trong roadmap.** Mọi mã đã có (`Q-N`, `TSK-*`, `FR-*`,
> `MS-*`, `BL-*`, `R-19`) được dẫn lại, không sao chép nội dung.
> **Tài liệu cùng bộ:** `01-user-stories.md`, `03-srs.md`, `prototype/index.html` (màn hình `MH-1` …
> `MH-8`).
> **Tài liệu nền:** `docs/business/brd-ambient-intelligence.md` (BRD đã duyệt, Q-85), `docs/spec/missions.md`
> (Q-87), `docs/spec/blueprint.md` (Q-86), `roadmap/neuroedge-prd.md`.

---

## 1. Tóm tắt

Người trong gia đình không muốn viết YAML, gate hay hợp đồng. Họ muốn xem nhà ra sao, nói điều muốn đổi,
đọc một thẻ ngắn rồi duyệt bằng tay mình. Đề xuất này là một ứng dụng di động (bản đầu là web di động do
chính hộp phục vụ) đứng trước lõi NeuroEdge sẵn có: gate, hợp đồng nhiệm vụ, trace và bản ghi duyệt vẫn
nằm bên dưới, được sinh ra và chỉ hiện sau nút "Xem chi tiết".

Ứng dụng không thay lõi và không thêm quyền cho bộ não. Nó làm ba việc:

1. **Che thuật ngữ** nhưng không che sự thật: mọi thứ người chịu trách nhiệm cần đọc vẫn mở được.
2. **Gom mọi thay đổi vào một thẻ duyệt** có ba vùng màu cho các con số và một dòng "nếu áp dụng hôm qua".
3. **Làm cho cảnh báo khẩn có đường đi** (hỏi tại chỗ, nhiều kênh, xác nhận, leo thang), dùng cho ngành dọc
   chăm sóc người cao tuổi khi nó được mở sau này.

Hai ví dụ: bể cá phòng khách (agent bể cá có sẵn) và nhà bố mẹ. Ví dụ thứ hai là **ngành dọc tương lai**:
Q-72 (PRD §14) hoãn chăm sóc người cao tuổi, và R-19 ghi rủi ro pháp lý. Ứng dụng **không phát hiện bệnh,
không phát hiện té ngã; chỉ báo người thân về thay đổi thói quen**.

---

## 2. Vấn đề

**Người dùng không muốn cấu hình.** Lõi NeuroEdge đúng về an toàn nhưng nói bằng gate, digest, `board.v1`,
số chân. Người trong gia đình không đọc được những thứ đó và không nên phải đọc. Hiện có các mảnh giao
diện: `neuroedge studio` (Q-51, đang tạm dừng theo Q-72), trang trực tiếp của `run --ui` và
`mcp serve --ui`, và `neuroedge ui-link` (liên kết một lần tới trang nhà để duyệt, xem
`docs/user/chat-voi-nha.md`). Chúng viết cho người làm kỹ thuật.

**Gate và hợp đồng vô hình với người dùng nhưng cần cho người chịu trách nhiệm.** Người duyệt một thay
đổi phải biết nó sẽ làm gì, và người xem lại sau phải đọc được vì sao một lệnh bị chặn. Nếu giao diện che
hết, người duyệt duyệt mù; nếu phơi hết, người dùng bỏ đi. Đề xuất giải bằng hai tầng: câu thường ở mặc
định (thẻ ≤ 5 dòng sinh từ cấu trúc đã biên dịch, MS-AP-01), chi tiết đầy đủ sau "Xem chi tiết".

**Ba điểm đau cụ thể**, đều là giả thuyết cần kiểm chứng (mục 9):

- Muốn đổi một con số (ví dụ ngưỡng máy sưởi) nhưng không biết khoảng nào an toàn cho thiết bị của mình.
- Sợ duyệt một thay đổi mà không biết hệ quả; muốn thấy trước nó sẽ chặn hay báo bao nhiêu lần.
- Với người nhà ở xa, cảnh báo đến một kênh mà họ có thể không thấy, và không ai biết ai đã xem.

---

## 3. Thị trường và đối thủ

Mục này chỉ dùng các **nguồn thứ cấp** liệt kê ở phụ lục; đội chưa kiểm chứng độc lập. Phần đối thủ đầy
đủ của sản phẩm nằm ở `docs/business/brd-ambient-intelligence.md` §2.2, không lặp lại ở đây.

| Tín hiệu | Nội dung (nguồn thứ cấp) | Ý nghĩa với đề xuất |
|:---|:---|:---|
| Google Home MCP | Early access từ 2026-09-16, chỉ gói Premium Advanced ở Mỹ; có giới hạn tần suất và chặn hành động nhạy cảm như mở khóa cửa. | Nền tảng lớn cũng đặt lớp chặn giữa agent và thiết bị. |
| mesa-core (cộng đồng Home Assistant) | Mỗi thực thể một trong bốn mức: cho phép / hỏi trước / chỉ đọc / không bao giờ; mặc định theo loại thiết bị (đèn tự do, khóa và báo động không bao giờ, còn lại hỏi); mức hạn chế nhất thắng; cài bằng `pip install`, không cấu hình. | Gần nhất với ý "luật mặc định theo loại". Khác biệt: NeuroEdge không đặt mức "cấm hẳn" mặc định (Q-73) và sinh luật thành tệp tường minh. |
| Home Assistant MCP server chính thức | Chỉ các thực thể đã mở cho Assist. | Cách tiếp cận danh sách cho phép thô. |
| Espressif ESP-Claw | Apache-2.0, khoảng 2.245 sao GitHub ngày 2026-10-16; LLM quyết định, luật Lua cục bộ chạy tất định ngoại tuyến; ESP32-S3. | Cùng ý "LLM nghĩ, luật cục bộ chạy"; không thấy lớp duyệt cho người dùng cuối trong nguồn. |
| Vốn cho an ninh agent 2026 | Arcade 72 triệu USD tổng, AIR 50 triệu USD vòng seed, Runta 20 triệu USD vòng seed. Đây là agent phần mềm, không phải vật lý. | Thị trường đang trả tiền cho "cổng và nhật ký cho agent"; chưa nói gì về nhà vật lý. |
| Dân số Việt Nam | Khoảng 16,5 triệu người từ 60 tuổi trở lên (khoảng 16%), vào giai đoạn "dân số già" từ 2036 (dự báo GSO); khoảng 76% người cao tuổi không có lương hưu (UNFPA, qua báo chí). | Lý do ngành dọc người cao tuổi đáng đo, không phải bằng chứng cầu của sản phẩm này. |
| Nhật Bản | Dịch vụ canh chừng của quận Nerima: 990 yên mỗi tháng với cảm biến và cuộc gọi hỏi thăm. | Có dịch vụ trả tiền cho "báo người thân thay đổi thói quen"; giá chỉ là điểm tham chiếu, không là giá đề xuất. |
| Thu hồi Hero | Máy phát thuốc, FDA loại 2 (2021): phần mềm ghi liều đã phát là chưa phát và nhắc phát lại. | Ví dụ về rủi ro khi thiết bị sai trạng thái trong chăm sóc sức khỏe; củng cố việc không đưa ra tuyên bố y tế. |
| NaviCare (Việt Nam) | Đồng hồ 4G, cảnh báo ngã tự động, SOS, GPS. | Có sản phẩm tại chỗ nói đến phát hiện ngã; NeuroEdge không làm việc đó. |
| Zalo | Gia đình ở Việt Nam dùng Zalo; kênh chat của hộp hiện là Telegram (FR-CH-01). | **Nhận định sản phẩm của đội, không phải số liệu**; xem AP-D-05. |

Kết luận có giới hạn: lớp "chặn và hỏi" giữa agent và thiết bị là điều thị trường đã bắt đầu làm; chưa
thấy trong các nguồn trên sản phẩm nào cho người dùng cuối xem trước hệ quả bằng cách chạy lại dữ liệu thật
của chính nhà họ. Đó là giả thuyết, không phải kết luận khảo sát.

---

## 4. Mục tiêu và chỉ số

Mục tiêu của đề xuất là **đạt cổng nhu cầu của Q-72** (hạn 2026-12-06) theo cách mà người trong gia đình
tự dùng được, không phải thêm một đường doanh thu. Cổng đo B6 (người ngoài tự cài một Blueprint), B7 (có
người chạy liên tục hai tuần) và B8 (có maker muốn bán Blueprint); định nghĩa ở PRD §11.2.

Chỉ số riêng của ứng dụng (BR-APP-10), mở rộng việc ghi mốc cục bộ của TSK-I2e-07 (chỉ gửi đi khi bật):

| Chỉ số | Đo cái gì | Vì sao |
|:---|:---|:---|
| Tỉ lệ gỡ luật mặc định | Trong các luật mặc định theo loại thiết bị, bao nhiêu bị người dùng gỡ | Nếu gỡ nhiều, mặc định sai hoặc phiền. |
| Chặn đúng / chặn oan | Trong các lần hộp chặn, bao nhiêu người dùng xác nhận là đúng, bao nhiêu là oan | Đo xem luật có làm phiền vô ích (AP-D-08 định nghĩa "oan"). |
| Tần suất chấp nhận vùng vàng | Số lần người dùng duyệt giá trị ngoài khoảng maker, trên tổng số lần chỉnh | Cho biết khoảng maker có quá chặt không, và vùng vàng có được dùng không (AP-D-01). |

**Ngưỡng đạt của các chỉ số này do chủ sản phẩm đặt.** Tài liệu này không đề xuất con số. Chỉ số không
được dùng để thưởng cho việc nới luật (xem BRD nền §0 mục 3 về lý do bỏ chỉ số đo cấu hình).

---

## 5. Phạm vi

### 5.1 Trong phạm vi (trước cổng nhu cầu)

- Ứng dụng web di động do hộp phục vụ, năm tab: Nhà, Chat, Thiết bị, Hoạt động, Cài đặt, cộng phần cho
  maker.
- Ví dụ bể cá phòng khách: xem, chat, chỉnh bằng thanh trượt, xem trước, duyệt, nhật ký.
- Thêm thiết bị đấu dây qua trình hướng dẫn; luật mặc định theo loại thiết bị sinh thành tệp tường minh.
- Telegram là kênh báo đầu tiên (FR-CH-01).

### 5.2 Ngoài phạm vi

- **Ngành dọc chăm sóc người cao tuổi:** hoãn bởi Q-72, rủi ro pháp lý R-19. Các story gắn "eldercare"
  (US-APP-02 mức Must, US-APP-17) chỉ là thiết kế để không thiết kế sai; không được quảng bá hay làm
  trước khi có quyết định mới. Không có tuyên bố y tế; không phát hiện bệnh hay té ngã.
- **Chứng nhận an toàn chức năng:** NeuroEdge không phải chức năng an toàn được chứng nhận (Q-38).
- **Ứng dụng gốc (native), Zalo Mini App, đẩy thông báo màn hình khóa, truy cập từ ngoài nhà:** chờ cổng
  nhu cầu và Q-74 (AP-D-03, AP-D-04).
- **Giọng nói, NeuroEdge Lab, bản canvas kéo thả:** đã bỏ hoặc hoãn bởi Q-77 và Q-84 (canvas giai đoạn C là
  TSK-I2d-31, hoãn). Muốn thêm lại phải có `Q-N` mới.
- **Thay lõi:** không đổi ngữ nghĩa gate, `schemas/`, trace chuẩn hay `NETR` bằng đề xuất này; việc nào
  chạm vào đó cần RFC (`CONTRIBUTING.md` §3) và được đánh dấu trong SRS.

---

## 6. Yêu cầu kinh doanh

| ID | Yêu cầu | Vì sao | Story |
|:---|:---|:---|:---|
| **BR-APP-01** | Mặc định không dùng thuật ngữ kỹ thuật; chi tiết nằm sau "Xem chi tiết". | Người dùng không đọc được gate, digest, số chân; người chịu trách nhiệm vẫn cần mở được chi tiết. | US-APP-01, 08, 11 |
| **BR-APP-02** | Mọi thay đổi đi qua một thẻ duyệt chung. | Một cách duyệt duy nhất thì người dùng học một lần, và hộp chỉ kiểm một đường (MS-AP-04). | US-APP-04, 05, 09, 15 |
| **BR-APP-03** | Con số có ba vùng: xanh (khoảng maker khai), vàng (ngoài khoảng maker), khóa (giới hạn phần cứng). | Cho người dùng biết mình đang ở đâu; vùng khóa không bao giờ chỉnh được từ ứng dụng. | US-APP-05, 16 |
| **BR-APP-04** | Người duyệt; AI không bao giờ duyệt. | Bất biến của Q-73 (a) và FR-CH-05: LLM, ứng dụng MCP và nguồn tự động không trả lời bước cần người. | US-APP-06 |
| **BR-APP-05** | Xem trước bằng cách chạy lại trên trace thật của nhà. | Người duyệt thấy hệ quả bằng dữ liệu của mình, trước khi khóa. | US-APP-07 |
| **BR-APP-06** | Thêm và gỡ thiết bị không cần viết cấu hình. | Rào cản lớn nhất của người không làm kỹ thuật. | US-APP-09, 10 |
| **BR-APP-07** | Cảnh báo chắc chắn đến nơi: hỏi tại chỗ, nhiều kênh, xác nhận, leo thang. | Cảnh báo không ai xác nhận thì chưa phải cảnh báo; cần cho ngành dọc người cao tuổi sau này. | US-APP-02, 12, 13, 17, 18 |
| **BR-APP-08** | Minh bạch: nhật ký, rủi ro đang bật, ngân sách AI. | Q-73: nhãn rủi ro thay cho cấm đoán; người dùng thấy cái mình đã chấp nhận. | US-APP-11, 14 |
| **BR-APP-09** | Maker quyết định khoảng an toàn của Blueprint. | Maker hiểu thiết bị; người cài chỉ chỉnh trong khoảng đã kiểm chứng. | US-APP-16 |
| **BR-APP-10** | Đo được cho cổng nhu cầu: tỉ lệ gỡ luật mặc định, chặn đúng/chặn oan, tần suất chấp nhận vùng vàng. | Cổng nhu cầu của Q-72 cần số đo; không thêm ngưỡng mới. | (chỉ số sản phẩm; không gắn story riêng) |

---

## 7. Ràng buộc

1. **Q-73, ba bất biến:** (a) LLM, ứng dụng MCP và nguồn tự động không trả lời bước xác minh hay hỏi lại
   dành cho người; (b) luật đã khai chạy đúng như đã khai, không đường vòng ẩn; (c) mọi bước xác minh và
   phán quyết đều ghi vào trace (không ghi bí mật). Ngoài ba điều đó, Q-73 là "minh bạch thay vì cấm": ứng
   dụng không chặn lựa chọn của người dùng mà gắn nhãn rủi ro. Vì vậy mặc định không có mức "cấm hẳn".
2. **Q-38:** không là chức năng an toàn được chứng nhận; ứng dụng không dùng câu "an toàn tuyệt đối".
3. **Q-72 và R-19:** ngành dọc người cao tuổi hoãn; không tuyên bố y tế.
4. **MS-\* (Missions, Q-87):** thẻ duyệt, chat duyệt, trace theo đoạn, đích gửi dữ liệu; chỉ dẫn, không
   viết lại (`docs/spec/missions.md`). Các MS cốt lõi cho ứng dụng: MS-AP-01 … 05, MS-CH-02 … 05,
   MS-CT-04, MS-CT-06, MS-CP-02, MS-RT-07, MS-EG-01, MS-TS-01, MS-TS-02.
5. **BL-\* (Blueprint, Q-86):** BL-IN-04: tham số cài đặt chỉ đi vào dữ kiện, luật cảm biến hoặc linh
   kiện, không bao giờ vào gate; BL-IN-05: không có gì của gói chạy trước khi người duyệt.
6. **Luật mặc định theo loại là tệp tường minh**, không phải mặc định ngầm trong runtime: mặc định ngầm
   sẽ đổi ngữ nghĩa gate và cần RFC (`CONTRIBUTING.md` §3).
7. **Bộ não không tin cậy** (Q-78, Q-80, Q-83): ứng dụng nói chuyện với hộp; bộ não chỉ soạn và không duyệt.
8. **Tài nguyên:** `neuroedge studio` đang tạm dừng (Q-72); mọi việc tái dùng nó cần chủ sản phẩm quyết
   định (AP-D-10). Không thêm task vào roadmap bởi tài liệu này.

---

## 8. Rủi ro

| Rủi ro | Mức | Giảm thiểu đề xuất |
|:---|:---:|:---|
| **Hiểu nhầm là chức năng an toàn được chứng nhận** (R-19, Q-38): màu xanh làm người dùng tin quá mức. | Cao | Chữ trên ứng dụng không dùng lời tuyệt đối; hiển thị câu Q-38 ở Cài đặt; vùng xanh ghi "trong khoảng maker cho phép", không ghi "an toàn". |
| **Vân tay trên web khó** (đặc biệt iOS); đẩy thông báo màn hình khóa tương tự. | Cao | Giai đoạn đầu duyệt tại trang cục bộ hoặc bản ghi duyệt qua chat (MS-CH-03); AP-D-02, AP-D-03. |
| **Vùng vàng mâu thuẫn MS-CT-06** (giá trị ngoài khoảng đang là không hợp lệ). | Trung bình | Chủ sản phẩm quyết định (AP-D-01); đến lúc đó vùng vàng không được triển khai. |
| **Luật mặc định theo loại sai hoặc phiền**, người dùng gỡ hết. | Trung bình | Đo tỉ lệ gỡ (BR-APP-10); mặc định hiển thị thành câu, gỡ qua thẻ duyệt. |
| **Mệt vì cảnh báo** (P-1 của BRD nền). | Trung bình | Cảnh báo khẩn từ mẫu cố định, không gộp (MS-RT-07); thông báo thường theo ngân sách tin nhắn (NFR-COST-02). |
| **Truy cập từ ngoài nhà cần relay/cloud** (Q-74), chưa có. | Trung bình | Bản đầu chỉ trong mạng nhà; ghi rõ giới hạn ở màn hình (AP-D-04). |
| **Kênh cảnh báo thiếu** (Zalo chưa có; FR-CH-01 xếp P1). | Trung bình | Telegram trước; ưu tiên Zalo do chủ sản phẩm quyết (AP-D-05). |
| **Chạy lại trên trace** có thể cần engine mới. | Trung bình | Làm rõ có cần RFC không trước khi hứa (AP-D-09). |
| **Tạm dừng Studio** làm không có nền để tái dùng. | Thấp | AP-D-10. |

---

## 9. Giả định cần kiểm chứng

Mọi mục dưới đây là giả thuyết của đội; chưa có kiểm chứng nào.

1. Người trong gia đình thà đọc một thẻ ≤ 5 dòng rồi duyệt hơn là nhờ một maker chỉnh hộ.
2. Dòng "nếu áp dụng hôm qua" làm người dùng duyệt tự tin hơn, không phải chỉ thêm một con số khó hiểu.
3. Ba vùng màu đọc được mà không cần giải thích; người dùng không coi vùng xanh là bảo đảm an toàn.
4. Maker chịu khai khoảng chỉnh được và luật mặc định cho từng thiết bị (liên quan B8).
5. Một ứng dụng web di động là đủ cho giai đoạn đầu; người dùng không đòi ứng dụng gốc ngay.
6. Gia đình ở Việt Nam muốn Zalo hơn Telegram (nhận định sản phẩm, chưa đo).
7. Người dùng chịu được việc chưa có truy cập từ ngoài nhà trong bản đầu.

---

## 10. Thứ tự làm

Không có ngày; thứ tự theo phụ thuộc và theo cổng nhu cầu (Q-72, 2026-12-06).

**Trước cổng nhu cầu**, phần ứng dụng sống được với những gì đã có hoặc đã lên lịch trong roadmap:

1. Thẻ duyệt và việc duyệt (TSK-I2d-06, TSK-I2d-11, TSK-I2d-12) cho bể cá.
2. Trang nhà: tab Nhà, Chat, Thiết bị, Hoạt động cho bể cá, dựa trên agent bể cá và trace.
3. Ba vùng, chạy lại trên trace (chờ AP-D-01, AP-D-09), thêm thiết bị đấu dây, luật mặc định theo loại.
4. Khai báo của maker (BR-APP-09) cùng Blueprint (TSK-I2e-01, TSK-I2e-03).
5. Chỉ số của BR-APP-10 (mở rộng TSK-I2e-07).

**Sau cổng nhu cầu**, mỗi mục cần một quyết định riêng nếu cổng đạt:

- Chăm sóc người cao tuổi: chuỗi cảnh báo, nút "Tôi ổn", relay canh hộp (cần pháp lý, R-19).
- Vân tay bằng passkey (FR-CH-08, TSK-I2f-08), vai trò nhiều người (FR-CH-07, TSK-I2f-05).
- Zalo, SMS qua 4G, gọi tự động; ứng dụng gốc hoặc Zalo Mini App; truy cập từ ngoài nhà (Q-74).
- Thiết bị không dây (RFC-0014, code hoãn sau v1.0).

---

## 11. Câu hỏi chờ chủ sản phẩm

Danh sách đầy đủ và chi tiết ở `03-srs.md` §6 (`AP-D-nn`). Tóm tắt:

| Mã | Câu hỏi |
|:---|:---|
| AP-D-01 | Vùng vàng có tồn tại không (giá trị ngoài khoảng maker, có nhãn rủi ro), hay giá trị ngoài khoảng bị từ chối như MS-CT-06 hiện nay? |
| AP-D-02 | Passkey (vân tay) có cần sớm hơn TSK-I2f-08 không? |
| AP-D-03 | Dạng ứng dụng: web di động, ứng dụng gốc, hay Zalo Mini App; và cách thay cho đẩy thông báo trên màn hình khóa? |
| AP-D-04 | Truy cập từ ngoài nhà cần relay hoặc cloud (Q-74): làm trước hay sau cổng? |
| AP-D-05 | Thứ tự ưu tiên kênh Zalo so với Telegram. |
| AP-D-06 | Xác nhận luật mặc định theo loại là tệp sinh ra, và có cần RFC không. |
| AP-D-07 | Thời gian chờ mặc định trong chuỗi leo thang. |
| AP-D-08 | Định nghĩa "chặn oan" và ngưỡng đạt của các chỉ số. |
| AP-D-09 | Chạy lại trên trace với cấu hình đề xuất có cần RFC không. |
| AP-D-10 | Studio đang tạm dừng: tái dùng hay xây trang riêng. |
| AP-D-11 | Trình duyệt hỗ trợ và ngưỡng hiệu năng. |

---

## Phụ lục. Nguồn (thứ cấp)

Truy cập theo thông tin của người soạn brief ngày 2026-10-16; đội chưa kiểm chứng độc lập.

- Google Home MCP: https://thenextweb.com/news/google-home-mcp-third-party-ai-agents-claude-openclaw
- mesa-core: https://community.home-assistant.io/t/mesa-core-a-semantic-safety-layer-for-ai-agents-controlling-home-assistant/1015280
- Home Assistant MCP server: https://raspberry.tips/en/smart-home/home-assistant-mcp-server-ai-setup
- ESP-Claw: https://github.com/espressif/esp-claw/
- Arcade: https://www.hpcwire.com/aiwire/2026/06/16/arcade-secures-60m-to-scale-authorization-and-governance-for-ai-agents/
- AIR: https://www.newswire.com/news/air-emerges-from-stealth-with-50m-to-build-a-firewall-for-agents-22853509
- Runta: https://cryptobriefing.com/runta-raises-20m-andreessen-horowitz-ai-agents/
- Dân số Việt Nam: https://tuoitre.vn/viet-nam-buoc-vao-thoi-ky-dan-so-gia-trong-it-nam-toi-20260126171300799.htm ·
  https://nguoiquansat.vn/bao-ngoai-viet-nam-chi-mat-20-nam-de-di-chang-duong-ma-phap-mat-115-nam-mo-ra-thi-truong-gan-5-ty-usd-319956.html
- Nerima (Nhật Bản): https://www.city.nerima.tokyo.jp/hokenfukushi/koreisha/nichijo/mimamoriict.files/ictshoukai.pdf
- Thu hồi Hero (FDA): https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRES/res.cfm?id=188593
- NaviCare: https://navicare.vn/
