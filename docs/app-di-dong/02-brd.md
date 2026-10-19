# Tài liệu yêu cầu kinh doanh (BRD): ứng dụng di động NeuroEdge ("app nhà")

> **Đã duyệt bởi Q-91 (2026-10-19); increment I2g, chờ sau cổng nhu cầu 2026-12-06.** Q-91 trả lời
> `AP-D-01` → `AP-D-17` và mở `TSK-I2g-01` → `TSK-I2g-13` (`03-srs.md` §7). **Thay đổi 2026-10-19:** bản nháp
> 2026-10-16 thành bản đã duyệt, dạng app gốc iOS và Android. Mọi mã đã có (`Q-N`, `TSK-*`, `FR-*`,
> `MS-*`, `BL-*`, `R-19`) được dẫn lại, không sao chép nội dung.
> **Tài liệu cùng bộ:** `01-user-stories.md`, `03-srs.md`, `prototype/index.html` (màn hình `MH-1` …
> `MH-8`).
> **Tài liệu nền:** `docs/business/brd-ambient-intelligence.md` (BRD đã duyệt, Q-85), `docs/spec/missions.md`
> (Q-87), `docs/spec/blueprint.md` (Q-86), `roadmap/neuroedge-prd.md`.

---

## 1. Tóm tắt

Người trong gia đình không muốn viết YAML, gate hay hợp đồng. Họ muốn xem nhà ra sao, nói điều muốn đổi,
đọc một thẻ ngắn rồi duyệt qua hộp (ký bằng vân tay hoặc Face ID trong nhà; ngoài nhà qua bot duyệt riêng của hộp, RFC-0019). Đây là một app gốc iOS và Android
(React Native; điện thoại ghép với API của hộp trong mạng nhà, Q-91 (2), (3)) đứng trước lõi NeuroEdge sẵn có: gate, hợp đồng nhiệm vụ, trace và bản ghi duyệt vẫn
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
| mesa-core (cộng đồng Home Assistant) | Mỗi thực thể một trong bốn mức: cho phép / hỏi trước / chỉ đọc / không bao giờ; mặc định theo loại thiết bị (đèn tự do, khóa và báo động không bao giờ, còn lại hỏi); mức hạn chế nhất thắng; cài bằng `pip install`, không cấu hình. | Gần nhất với ý "luật mặc định theo loại". Khác biệt: NeuroEdge không thêm mức "cấm hẳn" mà người dùng không thấy và không đổi được (Q-73), và luật là tệp tường minh. |
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

Ứng dụng **không nằm trên đường tới cổng nhu cầu của Q-72** (hạn 2026-12-06): Q-91 (1) xếp nó là increment I2g, chờ
sau cổng, là increment đầu tiên sau cổng và trước I3 → I7 (nhánh ③ của cổng thì một `Q-N` quyết lại). Q-85 (2) và
K1–K5 trước cổng không đổi (Q-85 (3)); trước cổng gia đình chỉ tới sản phẩm qua Blueprint của maker. Cổng đo B6, B7, B8 (PRD §11.2).

Ba chỉ số dưới đây (BR-APP-10) là tiêu chí thoát của I2g, không sửa Q-85 (3); ngưỡng đặt bằng dữ liệu cổng (Q-91 (10),
AP-D-16, TSK-I2g-12). Việc ghi mốc cục bộ của TSK-I2e-07 theo FR-TEL-07 không đổi:

| Chỉ số | Đo cái gì | Vì sao |
|:---|:---|:---|
| Tỉ lệ gỡ luật mặc định | Trong các luật mặc định (do Blueprint khai), bao nhiêu bị người dùng gỡ | Nếu gỡ nhiều, mặc định sai hoặc phiền. |
| Chặn đúng / chặn oan | Trong các lần hộp chặn, bao nhiêu người dùng xác nhận là đúng, bao nhiêu là oan | Đo xem luật có làm phiền vô ích (AP-D-08 định nghĩa "oan"). |
| Tần suất chấp nhận vùng vàng | Số lần người dùng duyệt giá trị ngoài khoảng maker, trên tổng số lần chỉnh | Cho biết khoảng maker có quá chặt không, và vùng vàng có được dùng không (AP-D-01). |

**Ngưỡng đạt của các chỉ số này do chủ sản phẩm đặt.** Tài liệu này không đề xuất con số. Chỉ số không
được dùng để thưởng cho việc nới luật (xem BRD nền §0 mục 3 về lý do bỏ chỉ số đo cấu hình).

---

## 5. Phạm vi

### 5.1 Trong phạm vi (sau cổng nhu cầu, Q-91)

- App gốc iOS và Android bằng React Native, năm tab: Nhà, Chat, Thiết bị, Hoạt động, Cài đặt; phần cho maker là Studio, trang web máy tính
  dùng chung API hộp (Q-91 (2), (4)).
- Ví dụ bể cá phòng khách: xem, chat, chỉnh bằng thanh trượt, xem trước, duyệt, nhật ký.
- Thêm thiết bị qua trình hướng dẫn trên `sim` và board thật (`neuroedge add part`, Q-91 (9), TSK-I2g-09); gate và linh kiện sinh ra
  qua `neuroedge gate lint`, khóa bằng duyệt ký sinh trắc tại nhà (cần RFC, TSK-I2g-04); canvas kéo thả vẫn hoãn (Q-84, TSK-I2d-31). Luật mặc định về giá trị chỉ do
  Blueprint khai (MS-CT-06, BL-IN-04); gate cho thiết bị mới do `neuroedge add part` sinh (VP-PT-07).
- Telegram là kênh báo và kênh duyệt ngoài nhà (FR-CH-01; bot duyệt riêng của hộp, RFC-0019, Q-89); push không nội dung qua APNs và FCM (Q-91 (7)).
- Chat với NeuroClaw qua kênh riêng của NeuroClaw (Q-91 (6)); duyệt bằng vân tay hoặc Face ID (cần RFC, Q-91 (5)).

### 5.2 Ngoài phạm vi

- **Ngành dọc chăm sóc người cao tuổi:** hoãn bởi Q-72, rủi ro pháp lý R-19. Các story gắn "eldercare"
  (US-APP-02 mức Must, US-APP-17) chỉ là thiết kế để không thiết kế sai; không được quảng bá hay làm
  trước khi có quyết định mới. Không có tuyên bố y tế; không phát hiện bệnh hay té ngã.
- **Chứng nhận an toàn chức năng:** NeuroEdge không phải chức năng an toàn được chứng nhận (Q-38).
- **Zalo Mini App, kênh Zalo (P1, FR-CH-01), chuỗi leo thang (hoãn cùng ngành dọc người cao tuổi, Q-91 (7)), relay hoặc cloud canh hộp:**
  Q-74 bước 2 (AP-D-04).
- **Giọng nói, NeuroEdge Lab, bản canvas kéo thả:** đã bỏ hoặc hoãn bởi Q-77, Q-88 (Lab) và Q-84 (canvas giai đoạn C là
  TSK-I2d-31, hoãn). Muốn thêm lại phải có `Q-N` mới.
- **Thay lõi:** không đổi ngữ nghĩa gate, `schemas/`, trace chuẩn hay `NETR` bằng đề xuất này; việc nào
  chạm vào đó cần RFC (`CONTRIBUTING.md` §3) và được đánh dấu trong SRS.

---

## 6. Yêu cầu kinh doanh

| ID | Yêu cầu | Vì sao | Story |
|:---|:---|:---|:---|
| **BR-APP-01** | Mặc định không dùng thuật ngữ kỹ thuật; chi tiết nằm sau "Xem chi tiết". | Người dùng không đọc được gate, digest, số chân; người chịu trách nhiệm vẫn cần mở được chi tiết. | US-APP-01, 08, 11 |
| **BR-APP-02** | Mọi thay đổi đi qua một thẻ duyệt chung. | Một cách duyệt duy nhất thì người dùng học một lần, và hộp chỉ kiểm một đường (MS-AP-04). | US-APP-04, 05, 09, 15 |
| **BR-APP-03** | Con số có ba vùng: xanh (khoảng maker khai), vàng (ngoài khoảng maker, trong giới hạn giá trị của `board.v1`, sau chấp nhận rõ ràng; cần RFC), khóa (giới hạn `board.v1` khai, kể cả giới hạn giá trị do RFC thêm; Q-91 (8)). | Cho người dùng biết mình đang ở đâu; vùng khóa không bao giờ chỉnh được từ ứng dụng. | US-APP-05, 16 |
| **BR-APP-04** | Người duyệt; AI không bao giờ duyệt. | Bất biến của Q-73 (a) và FR-CH-05: LLM, ứng dụng MCP và nguồn tự động không trả lời bước cần người. | US-APP-06 |
| **BR-APP-05** | Xem trước bằng cách chạy lại trên trace thật của nhà. | Người duyệt thấy hệ quả bằng dữ liệu của mình, trước khi khóa. | US-APP-07 |
| **BR-APP-06** | Thêm và gỡ thiết bị không cần viết cấu hình. | Rào cản lớn nhất của người không làm kỹ thuật. | US-APP-09, 10 |
| **BR-APP-07** | Cảnh báo chắc chắn đến nơi: hỏi tại chỗ, nhiều kênh, xác nhận, leo thang. | Cảnh báo không ai xác nhận thì chưa phải cảnh báo; cần cho ngành dọc người cao tuổi sau này. | US-APP-02, 12, 13, 17, 18 |
| **BR-APP-08** | Minh bạch: nhật ký, rủi ro đang bật, ngân sách AI. | Q-73: nhãn rủi ro thay cho cấm đoán; người dùng thấy cái mình đã chấp nhận. | US-APP-11, 14 |
| **BR-APP-09** | Maker quyết định khoảng an toàn của Blueprint. | Maker hiểu thiết bị; người cài chỉ chỉnh trong khoảng đã kiểm chứng. | US-APP-16 |
| **BR-APP-10** | Đo tỉ lệ gỡ luật mặc định, chặn đúng/chặn oan, tần suất chấp nhận vùng vàng; ngưỡng từ dữ liệu cổng (Q-91 (10)). | Tiêu chí thoát của I2g; không sửa Q-85 (3), K1–K5 trước cổng không đổi. | (chỉ số sản phẩm; không gắn story riêng) |

---

## 7. Ràng buộc

1. **Q-73, ba bất biến:** (a) LLM, ứng dụng MCP và nguồn tự động không trả lời bước xác minh hay hỏi lại
   dành cho người; (b) luật đã khai chạy đúng như đã khai, không đường vòng ẩn; (c) mọi bước xác minh và
   phán quyết đều ghi vào trace (không ghi bí mật). Ngoài ba điều đó, Q-73 là "minh bạch thay vì cấm": ứng
   dụng không chặn lựa chọn của người dùng mà gắn nhãn rủi ro. Vì vậy ứng dụng không thêm mức "cấm hẳn" ngầm mà người dùng không thấy và không đổi được (Q-73 (3) nói về phương thức xác minh; luật đã khai như `heater_on` của bể cá vẫn chạy đúng như đã khai).
2. **Q-38:** không là chức năng an toàn được chứng nhận; ứng dụng không dùng câu "an toàn tuyệt đối".
3. **Q-72 và R-19:** ngành dọc người cao tuổi hoãn; không tuyên bố y tế.
4. **MS-\* (Missions, Q-87):** thẻ duyệt, chat duyệt, trace theo đoạn, đích gửi dữ liệu; chỉ dẫn, không
   viết lại (`docs/spec/missions.md`). Các MS cốt lõi cho ứng dụng: MS-AP-01 … 05, MS-CH-02 … 05,
   MS-CT-04, MS-CT-06, MS-CP-02, MS-RT-07, MS-EG-01, MS-TS-01, MS-TS-02.
5. **BL-\* (Blueprint, Q-86):** BL-IN-04: tham số cài đặt chỉ đi vào dữ kiện, luật cảm biến hoặc linh
   kiện, không bao giờ vào gate; BL-IN-05: không có gì của gói chạy trước khi người duyệt.
6. **Luật mặc định chỉ do Blueprint khai** (MS-CT-06, FR-MSN-13, BL-IN-04) và là tệp tường minh; gate cho thiết
   bị mới do `neuroedge add part` sinh (VP-PT-07). Không có mặc định ngầm trong runtime: nó sẽ đổi ngữ nghĩa
   gate và cần RFC (`CONTRIBUTING.md` §3).
7. **Bộ não không tin cậy** (Q-78, Q-80, Q-83): ứng dụng nói chuyện với hộp; bộ não chỉ soạn và không duyệt.
8. **Tài nguyên:** `neuroedge studio` bị Q-72 tạm dừng và chỉ nghe 127.0.0.1 (`docs/spec/studio.md` §2); Q-91 (4) mở lại làm trang web
   máy tính cho maker, dùng chung API hộp với ứng dụng (TSK-I2g-05). Task của I2g: `03-srs.md` §7.
9. **Duyệt hành động vật lý đi qua hộp** (DP-A-05, DP-A-06, RFC-0019, Q-89): trang cục bộ, hoặc nút trên bot duyệt
   riêng của hộp với bản ghi do hộp ký; chủ hộp ghép bằng mã dùng một lần hiện trên hộp; lời duyệt từ xa bị chặn
   bởi `[approvals] remote_per_hour` (mặc định 10, tối đa 30) và mang nhãn `risk=remote_approval`. Trong nhà, ứng dụng ký lời duyệt bằng vân tay hoặc Face ID,
   một nguồn người mới cần RFC sửa RFC-0006 và RFC-0019 (Q-91 (5), TSK-I2g-01); ngoài các đường này ứng dụng không có đường duyệt nào.

---

## 8. Rủi ro

| Rủi ro | Mức | Giảm thiểu đề xuất |
|:---|:---:|:---|
| **Hiểu nhầm là chức năng an toàn được chứng nhận** (R-19, Q-38): màu xanh làm người dùng tin quá mức. | Cao | Chữ trên ứng dụng không dùng lời tuyệt đối; hiển thị câu Q-38 ở Cài đặt, ở tóm tắt duyệt và ở thẻ Blueprint (R-19); vùng xanh ghi "trong khoảng maker cho phép", không ghi "an toàn". |
| **Duyệt từ xa dựa vào chat của hộp:** tài khoản chat bị chiếm có thể duyệt tới mức trần mỗi giờ và có thể thu hồi chủ (chỉ gây từ chối dịch vụ, Q-89). Push dùng dịch vụ của Apple và Google nên chỉ mang tín hiệu không nội dung. | Cao | Duyệt bằng bản ghi có chữ ký qua bot duyệt riêng của hộp (RFC-0019, Q-89), có trần, TTL và nhãn `risk=remote_approval`; trong nhà ký bằng vân tay hoặc Face ID (cần RFC, TSK-I2g-01); push không nội dung (Q-91 (7)). |
| **Vùng vàng sửa BL-IN-04** (giá trị ngoài khoảng đã khai bị hỏi lại hoặc từ chối; hợp đồng chỉ siết, MS-CP-02; Q-73 bất biến (b)). | Trung bình | Q-91 (8) cho phép với chấp nhận rõ ràng, nhãn rủi ro và giới hạn giá trị của `board.v1`; hai RFC (TSK-I2g-02, TSK-I2g-03) trước khi triển khai. |
| **Luật mặc định theo loại sai hoặc phiền**, người dùng gỡ hết. | Trung bình | Đo tỉ lệ gỡ (BR-APP-10, TSK-I2g-12); mặc định hiển thị thành câu, gỡ qua thẻ duyệt. |
| **Mệt vì cảnh báo** (P-1 của BRD nền). | Trung bình | Cảnh báo khẩn từ mẫu cố định, không gộp (MS-RT-07); thông báo thường theo ngân sách tin nhắn (NFR-COST-02). |
| **Truy cập trực tiếp từ ngoài nhà cần relay/cloud** (Q-74), chưa có. | Trung bình | Ngoài nhà duyệt qua bot của hộp (Q-91 (3)); ghi rõ giới hạn ở màn hình. Q-74 bước 2 chỉ mở sau cổng và chỉ nếu số đo cho thấy người thử kẹt. Trong nhà, API của hộp cần RFC và mục `threat_model.md` (TSK-I2g-01). |
| **Kênh cảnh báo thiếu** (Zalo chưa có; FR-CH-01 xếp P1). | Trung bình | Telegram và push không nội dung trước; Zalo giữ P1 (Q-91 (7)). |
| **Chạy lại trên trace** có thể cần engine mới. | Trung bình | Chạy chỉ đọc không cần RFC (AP-D-09); sự kiện trace mới cần RFC (TSK-I2d-13). |
| **Người không chuyên duyệt gate do ứng dụng sinh** (Q-91 (9)). | Cao | Giới hạn bởi `neuroedge gate lint`, giới hạn giá trị `board.v1` và duyệt ký sinh trắc tại nhà (cần RFC, TSK-I2g-04). |

---

## 9. Giả định cần kiểm chứng

Mọi mục dưới đây là giả thuyết của đội; chưa có kiểm chứng nào.

1. Người trong gia đình thà đọc một thẻ ≤ 5 dòng rồi duyệt hơn là nhờ một maker chỉnh hộ.
2. Dòng "nếu áp dụng hôm qua" làm người dùng duyệt tự tin hơn, không phải chỉ thêm một con số khó hiểu.
3. Ba vùng màu đọc được mà không cần giải thích; người dùng không coi vùng xanh là bảo đảm an toàn.
4. Maker chịu khai khoảng chỉnh được và luật mặc định cho từng thiết bị (liên quan B8).
5. Một app gốc bằng React Native chạy đủ nhanh trên điện thoại thật của hai bản hệ điều hành mới nhất (ngưỡng đặt trong I2g, Q-91 (2)).
6. Gia đình ở Việt Nam muốn Zalo hơn Telegram (nhận định sản phẩm, chưa đo).
7. Người dùng chịu được việc ngoài nhà chỉ duyệt qua bot của hộp, chưa có truy cập trực tiếp.

---

## 10. Thứ tự làm

Không có ngày; thứ tự theo phụ thuộc và theo cổng nhu cầu (Q-72, 2026-12-06). Ứng dụng là increment I2g, đầu tiên sau cổng
(Q-91 (1)).

**Trước cổng nhu cầu**, không làm gì của ứng dụng; chỉ những nền đã có trong roadmap mà I2g dựa vào:

1. Thẻ duyệt (TSK-I2d-04 → TSK-I2d-06) và việc duyệt (TSK-I2d-11, TSK-I2d-12; RFC-0019, Q-89).
2. Chạy lại trên trace (TSK-I2d-13, TSK-I2d-14; AP-D-09), Blueprint (TSK-I2e-01, TSK-I2e-03), nền chạy liên tục và kiểm cảm biến:
   TSK-I2d-05, TSK-I2d-08, TSK-I2d-16, TSK-I2d-25; `neuroedge lab doctor` TSK-I2d-17 (Q-88 (3)).

**I2g, sau cổng nhu cầu** (task ở `03-srs.md` §7):

1. Bốn RFC trước: ghép điện thoại, API hộp và duyệt ký sinh trắc (TSK-I2g-01); giới hạn giá trị `board.v1` (TSK-I2g-02); vùng vàng
   `blueprint.v1` (TSK-I2g-03); khóa gate do ứng dụng sinh (TSK-I2g-04).
2. API hộp dùng chung và Studio cho maker (TSK-I2g-05); vỏ ứng dụng (TSK-I2g-06); thẻ duyệt (TSK-I2g-07); hoạt động và chạy lại
   (TSK-I2g-08); trình hướng dẫn thiết bị (TSK-I2g-09).
3. Push không nội dung (TSK-I2g-10); kênh ứng dụng trong NeuroClaw (TSK-I2g-11).
4. Chỉ số và ngưỡng từ dữ liệu cổng (TSK-I2g-12); bản thử TestFlight và Google Play internal testing (TSK-I2g-13).

**Hoãn tiếp**, mỗi mục cần một quyết định riêng:

- Chăm sóc người cao tuổi: chuỗi leo thang, nút "Tôi ổn", relay canh hộp (pháp lý R-19; Q-91 (7); cần RFC sự kiện trace, mở rộng TSK-I2d-13).
- Vai trò nhiều người (FR-CH-07, TSK-I2f-05); passkey FR-CH-08 (TSK-I2f-08), mà duyệt sinh trắc của I2g đi trước.
- Zalo (P1), SMS qua 4G, gọi tự động; Zalo Mini App; truy cập trực tiếp từ ngoài nhà (Q-74).
- Cảm biến không dây (RFC-0014 đã duyệt, code hoãn sau v1.0); cơ cấu chấp hành từ xa đã có qua Home Assistant
  (RFC-0018, TSK-I2c-16).

---

## 11. Câu hỏi chờ chủ sản phẩm

**Đã duyệt bởi Q-91 (2026-10-19); increment I2g, chờ sau cổng nhu cầu 2026-12-06.** Cả mười bảy câu đều đã quyết; chi tiết ở
`03-srs.md` §6 (`AP-D-nn`). Tóm tắt:

| Mã | Câu hỏi và quyết định |
|:---|:---|
| AP-D-01 | Vùng vàng có tồn tại không? **Đã quyết (Q-91 (8)):** có, sau chấp nhận rõ ràng và có nhãn rủi ro, trong giới hạn giá trị `board.v1`; sửa BL-IN-04 qua RFC. |
| AP-D-02 | Passkey (vân tay) có cần sớm hơn TSK-I2f-08 không? **Đã quyết (Q-91 (5)):** có; ký bằng Face ID hoặc vân tay, nguồn người mới, cần RFC sửa RFC-0006 và RFC-0019. |
| AP-D-03 | Dạng ứng dụng và thay thế đẩy thông báo? **Đã quyết (Q-91 (2), (7)):** app gốc iOS và Android bằng React Native; push không nội dung qua APNs và FCM cùng bot Telegram. |
| AP-D-04 | Truy cập từ ngoài nhà cần relay hoặc cloud (Q-74): làm trước hay sau cổng? **Đã quyết (Q-74), xác nhận ở Q-91 (11):** sau cổng nhu cầu 2026-12-06 và chỉ nếu số đo cho thấy người thử kẹt; phê duyệt không đi qua relay (FR-EGR-05). Ngoài nhà duyệt qua bot của hộp (Q-91 (3)). |
| AP-D-05 | Zalo hay Telegram trước? **Đã quyết (Q-91 (7)):** Telegram và push trước; Zalo giữ P1 (FR-CH-01); duyệt qua Zalo cần mở rộng bot duyệt (sửa RFC). |
| AP-D-06 | Luật mặc định theo loại là tệp sinh ra, có cần RFC không? **Đã quyết (`CONTRIBUTING.md` §3), xác nhận ở Q-91 (11):** không cần RFC; gate do `neuroedge add part` sinh (VP-PT-07), mặc định về giá trị chỉ do Blueprint khai (MS-CT-06); mặc định ngầm trong runtime vẫn cần RFC. |
| AP-D-07 | Thời gian chờ của chuỗi leo thang và ngưỡng hộp im lặng? **Đã quyết (Q-91 (7)):** hoãn cùng ngành dọc người cao tuổi. |
| AP-D-08 | Định nghĩa "chặn oan" và ngưỡng đạt? **Đã quyết (Q-91 (10)):** tiêu chí thoát của I2g, đặt bằng dữ liệu cổng; Q-85 (3) không sửa. |
| AP-D-09 | Chạy lại trên trace có cần RFC không? **Đã quyết (`CONTRIBUTING.md` §3), xác nhận ở Q-91 (11):** chạy chỉ đọc không cần RFC; sự kiện trace mới cho đoạn trace thì cần RFC (TSK-I2d-13). |
| AP-D-10 | Studio tạm dừng: tái dùng hay xây trang riêng? **Đã quyết (Q-91 (4)):** Studio mở lại làm trang web máy tính cho maker; ứng dụng và Studio dùng chung API hộp. |
| AP-D-11 | Trình duyệt hỗ trợ và ngưỡng hiệu năng? **Đã quyết (Q-91 (2)):** hai bản chính mới nhất của iOS và Android; ngưỡng đặt trong thiết kế I2g, đo trên điện thoại thật. |
| AP-D-12 | Điện thoại tới hộp bằng cách nào; một lần chạm mang nguồn duyệt nào? **Đã quyết (Q-91 (3), (5)):** API có xác thực trong mạng nhà, ghép bằng mã dùng một lần; ký sinh trắc là nguồn mới (RFC). |
| AP-D-13 | Giới hạn theo giá trị cảm biến lấy từ đâu? **Đã quyết (Q-91 (8)):** RFC thêm giới hạn giá trị vào `board.v1`. |
| AP-D-14 | Chat của ứng dụng tới bộ não bằng đường nào? **Đã quyết (Q-91 (6)):** kênh riêng của NeuroClaw; duyệt không đi qua đó. |
| AP-D-15 | Một lần duyệt của gia đình khóa gì? **Đã quyết (Q-91 (9)):** tham số hợp đồng, gate và linh kiện do trình hướng dẫn sinh (qua `gate lint`, khóa bằng duyệt ký sinh trắc tại nhà; cần RFC). |
| AP-D-16 | Có sửa Q-85 (3) để thêm chỉ số của ứng dụng không? **Đã quyết (Q-91 (10)):** không sửa; chỉ số là tiêu chí thoát của I2g. |
| AP-D-17 | Các dòng thêm vào thẻ tính vào 5 dòng thế nào? **Đã quyết (Q-91 (8)):** thẻ ≤ 5 dòng; phần bổ sung bên dưới không tính. |

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
