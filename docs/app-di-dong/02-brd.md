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
đọc một thẻ ngắn rồi duyệt qua hộp (trang cục bộ hoặc bot duyệt riêng của hộp, RFC-0019). Đề xuất này là một ứng dụng di động (bản đầu là web di động; cách điện thoại
tới trang của hộp chưa quyết, AP-D-12) đứng trước lõi NeuroEdge sẵn có: gate, hợp đồng nhiệm vụ, trace và bản ghi duyệt vẫn
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

Bản nháp này **không nằm trên đường tới cổng nhu cầu của Q-72** (hạn 2026-12-06). Q-85 (2) đã quyết: gia
đình là đích của trải nghiệm nhưng maker ra mắt trước, và cổng không đổi; hệ quả đã chấp nhận là trước cổng gia
đình chỉ tới sản phẩm qua Blueprint của maker. Cổng đo B6, B7, B8 (PRD §11.2); chỉ số trước cổng là K1–K5
(Q-85 (3)), một danh sách đóng. Thêm chỉ số, hoặc đưa ứng dụng vào đường tới cổng, cần một `Q-N` sửa Q-85
(AP-D-16); đến lúc đó BR-APP-10 tạm dừng.

Ba chỉ số dưới đây (BR-APP-10) **chưa thuộc K1–K5 và chưa được dùng**; chỉ giữ làm thiết kế chờ AP-D-16. Việc
ghi mốc cục bộ của TSK-I2e-07 theo FR-TEL-07 không đổi:

| Chỉ số | Đo cái gì | Vì sao |
|:---|:---|:---|
| Tỉ lệ gỡ luật mặc định | Trong các luật mặc định (do Blueprint khai), bao nhiêu bị người dùng gỡ | Nếu gỡ nhiều, mặc định sai hoặc phiền. |
| Chặn đúng / chặn oan | Trong các lần hộp chặn, bao nhiêu người dùng xác nhận là đúng, bao nhiêu là oan | Đo xem luật có làm phiền vô ích (AP-D-08 định nghĩa "oan"). |
| Tần suất chấp nhận vùng vàng | Số lần người dùng duyệt giá trị ngoài khoảng maker, trên tổng số lần chỉnh | Cho biết khoảng maker có quá chặt không, và vùng vàng có được dùng không (AP-D-01). |

**Ngưỡng đạt của các chỉ số này do chủ sản phẩm đặt.** Tài liệu này không đề xuất con số. Chỉ số không
được dùng để thưởng cho việc nới luật (xem BRD nền §0 mục 3 về lý do bỏ chỉ số đo cấu hình).

---

## 5. Phạm vi

### 5.1 Trong phạm vi (trước cổng nhu cầu)

- Ứng dụng web di động (cách tới trang của hộp: AP-D-12), năm tab: Nhà, Chat, Thiết bị, Hoạt động, Cài đặt, cộng phần cho
  maker.
- Ví dụ bể cá phòng khách: xem, chat, chỉnh bằng thanh trượt, xem trước, duyệt, nhật ký.
- Thêm thiết bị qua trình hướng dẫn **trên `sim`** (`[sim.parts]`, `neuroedge add part`, Q-84 giai đoạn B); trình
  hướng dẫn cho board thật là canvas giai đoạn C, hoãn (Q-84, TSK-I2d-31). Luật mặc định về giá trị chỉ do
  Blueprint khai (MS-CT-06, BL-IN-04); gate cho thiết bị mới do `neuroedge add part` sinh (VP-PT-07).
- Telegram là kênh báo và kênh duyệt đầu tiên (FR-CH-01; bot duyệt riêng của hộp, RFC-0019, Q-89).

### 5.2 Ngoài phạm vi

- **Ngành dọc chăm sóc người cao tuổi:** hoãn bởi Q-72, rủi ro pháp lý R-19. Các story gắn "eldercare"
  (US-APP-02 mức Must, US-APP-17) chỉ là thiết kế để không thiết kế sai; không được quảng bá hay làm
  trước khi có quyết định mới. Không có tuyên bố y tế; không phát hiện bệnh hay té ngã.
- **Chứng nhận an toàn chức năng:** NeuroEdge không phải chức năng an toàn được chứng nhận (Q-38).
- **Ứng dụng gốc (native), Zalo Mini App, đẩy thông báo màn hình khóa, truy cập từ ngoài nhà:** chờ cổng
  nhu cầu và Q-74 (AP-D-03, AP-D-04).
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
| **BR-APP-03** | Con số có ba vùng: xanh (khoảng maker khai), vàng (ngoài khoảng maker), khóa (giới hạn `board.v1` khai, AP-D-13). | Cho người dùng biết mình đang ở đâu; vùng khóa không bao giờ chỉnh được từ ứng dụng. | US-APP-05, 16 |
| **BR-APP-04** | Người duyệt; AI không bao giờ duyệt. | Bất biến của Q-73 (a) và FR-CH-05: LLM, ứng dụng MCP và nguồn tự động không trả lời bước cần người. | US-APP-06 |
| **BR-APP-05** | Xem trước bằng cách chạy lại trên trace thật của nhà. | Người duyệt thấy hệ quả bằng dữ liệu của mình, trước khi khóa. | US-APP-07 |
| **BR-APP-06** | Thêm và gỡ thiết bị không cần viết cấu hình. | Rào cản lớn nhất của người không làm kỹ thuật. | US-APP-09, 10 |
| **BR-APP-07** | Cảnh báo chắc chắn đến nơi: hỏi tại chỗ, nhiều kênh, xác nhận, leo thang. | Cảnh báo không ai xác nhận thì chưa phải cảnh báo; cần cho ngành dọc người cao tuổi sau này. | US-APP-02, 12, 13, 17, 18 |
| **BR-APP-08** | Minh bạch: nhật ký, rủi ro đang bật, ngân sách AI. | Q-73: nhãn rủi ro thay cho cấm đoán; người dùng thấy cái mình đã chấp nhận. | US-APP-11, 14 |
| **BR-APP-09** | Maker quyết định khoảng an toàn của Blueprint. | Maker hiểu thiết bị; người cài chỉ chỉnh trong khoảng đã kiểm chứng. | US-APP-16 |
| **BR-APP-10** | **Tạm dừng, chờ `Q-N` sửa Q-85 (3).** Đo tỉ lệ gỡ luật mặc định, chặn đúng/chặn oan, tần suất chấp nhận vùng vàng. | Không thuộc K1–K5, danh sách chỉ số duy nhất trước cổng (Q-85 (3)); không thêm ngưỡng mới. | (chỉ số sản phẩm; không gắn story riêng) |

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
8. **Tài nguyên:** `neuroedge studio` đang tạm dừng (Q-72) và chỉ nghe 127.0.0.1 (`docs/spec/studio.md` §2); mọi việc tái dùng nó cần chủ sản phẩm quyết
   định (AP-D-10). Không thêm task vào roadmap bởi tài liệu này.
9. **Duyệt hành động vật lý đi qua hộp** (DP-A-05, DP-A-06, RFC-0019, Q-89): trang cục bộ, hoặc nút trên bot duyệt
   riêng của hộp với bản ghi do hộp ký; chủ hộp ghép bằng mã dùng một lần hiện trên hộp; lời duyệt từ xa bị chặn
   bởi `[approvals] remote_per_hour` (mặc định 10, tối đa 30) và mang nhãn `risk=remote_approval`. Ứng dụng
   không có đường duyệt riêng nào ngoài các đường này cho tới khi có quyết định mới (AP-D-12).

---

## 8. Rủi ro

| Rủi ro | Mức | Giảm thiểu đề xuất |
|:---|:---:|:---|
| **Hiểu nhầm là chức năng an toàn được chứng nhận** (R-19, Q-38): màu xanh làm người dùng tin quá mức. | Cao | Chữ trên ứng dụng không dùng lời tuyệt đối; hiển thị câu Q-38 ở Cài đặt, ở tóm tắt duyệt và ở thẻ Blueprint (R-19); vùng xanh ghi "trong khoảng maker cho phép", không ghi "an toàn". |
| **Duyệt từ xa dựa vào chat của hộp:** tài khoản chat bị chiếm có thể duyệt tới mức trần mỗi giờ và có thể thu hồi chủ (chỉ gây từ chối dịch vụ, Q-89). Vân tay trên web khó (đặc biệt iOS); đẩy thông báo màn hình khóa tương tự. | Cao | Duyệt tại trang cục bộ hoặc bằng bản ghi có chữ ký qua bot duyệt riêng của hộp (RFC-0019, Q-89), có trần, TTL và nhãn `risk=remote_approval`; vân tay là phương thức sau (FR-CH-08, TSK-I2f-08); AP-D-02, AP-D-03. |
| **Vùng vàng mâu thuẫn BL-IN-04 và MS-CP-02** (giá trị ngoài khoảng đã khai bị hỏi lại hoặc từ chối; hợp đồng chỉ siết; Q-73 bất biến (b)). | Trung bình | Chủ sản phẩm quyết định (AP-D-01); đến lúc đó vùng vàng không được triển khai. |
| **Luật mặc định theo loại sai hoặc phiền**, người dùng gỡ hết. | Trung bình | Đo tỉ lệ gỡ (BR-APP-10, tạm dừng chờ AP-D-16); mặc định hiển thị thành câu, gỡ qua thẻ duyệt. |
| **Mệt vì cảnh báo** (P-1 của BRD nền). | Trung bình | Cảnh báo khẩn từ mẫu cố định, không gộp (MS-RT-07); thông báo thường theo ngân sách tin nhắn (NFR-COST-02). |
| **Truy cập từ ngoài nhà cần relay/cloud** (Q-74), chưa có. | Trung bình | Chưa có relay; ghi rõ giới hạn ở màn hình. Q-74 bước 2 chỉ mở sau cổng và chỉ nếu số đo cho thấy người thử kẹt (AP-D-04 đã trả lời). Trang cục bộ hiện chỉ nghe 127.0.0.1 nên điện thoại trong mạng nhà cũng chưa tới được (AP-D-12). |
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

1. Thẻ duyệt (TSK-I2d-04 → TSK-I2d-06) và việc duyệt (TSK-I2d-11, TSK-I2d-12; RFC-0019, Q-89) cho bể cá.
2. Trang nhà: tab Nhà, Chat, Thiết bị, Hoạt động cho bể cá, dựa trên agent bể cá và trace.
3. Ba vùng (chờ AP-D-01, AP-D-13), chạy lại trên trace (cần TSK-I2d-13, TSK-I2d-14; AP-D-09 đã trả lời), thêm thiết bị trên `sim` (Q-84 giai đoạn B); board thật là canvas giai đoạn C, hoãn.
4. Khai báo của maker (BR-APP-09) cùng Blueprint (TSK-I2e-01, TSK-I2e-03).
5. Chỉ số của BR-APP-10: tạm dừng, cần `Q-N` sửa Q-85 (3) (AP-D-16); trước cổng chỉ có K1–K5.
6. Nền chạy liên tục và kiểm cảm biến: TSK-I2d-05, TSK-I2d-08, TSK-I2d-16, TSK-I2d-25; `neuroedge lab doctor` TSK-I2d-17 (Q-88 (3)).

**Sau cổng nhu cầu**, mỗi mục cần một quyết định riêng nếu cổng đạt:

- Chăm sóc người cao tuổi: chuỗi cảnh báo, nút "Tôi ổn", relay canh hộp (cần pháp lý, R-19; chưa có đặc tả đã
  duyệt, cần RFC sự kiện trace, mở rộng TSK-I2d-13).
- Vân tay bằng passkey (FR-CH-08, TSK-I2f-08), vai trò nhiều người (FR-CH-07, TSK-I2f-05).
- Zalo, SMS qua 4G, gọi tự động; ứng dụng gốc hoặc Zalo Mini App; truy cập từ ngoài nhà (Q-74).
- Cảm biến không dây (RFC-0014 đã duyệt, code hoãn sau v1.0); cơ cấu chấp hành từ xa đã có qua Home Assistant
  (RFC-0018, TSK-I2c-16).

---

## 11. Câu hỏi chờ chủ sản phẩm

Danh sách đầy đủ và chi tiết ở `03-srs.md` §6 (`AP-D-nn`). Tóm tắt, kèm trạng thái sau Q-90:

| Mã | Câu hỏi |
|:---|:---|
| AP-D-01 | Vùng vàng có tồn tại không (giá trị ngoài khoảng maker, có nhãn rủi ro), hay giá trị ngoài khoảng bị từ chối như BL-IN-04 hiện nay? **Còn mở**; căn cứ đúng là BL-IN-04 và MS-CP-02 (không phải MS-CT-06). |
| AP-D-02 | Passkey (vân tay) có cần sớm hơn TSK-I2f-08 không? **Đã trả lời một phần:** Q-89 và RFC-0019 cho duyệt từ xa qua bot của hộp mà không cần passkey; RFC-0019 giữ passkey là phương thức sau. Còn mở: ứng dụng có cần nó sớm hơn không. |
| AP-D-03 | Dạng ứng dụng: web di động, ứng dụng gốc, hay Zalo Mini App; và cách thay cho đẩy thông báo trên màn hình khóa? **Còn mở, có ràng buộc:** nút của bot duyệt nằm ngay trong cuộc chat (RFC-0019), nên duyệt bằng bot không cần liên kết tới thẻ; trang cục bộ chỉ nghe 127.0.0.1 (AP-D-12). |
| AP-D-04 | Truy cập từ ngoài nhà cần relay hoặc cloud (Q-74): làm trước hay sau cổng? **Đã trả lời (Q-74):** sau cổng nhu cầu 2026-12-06 và chỉ nếu số đo cho thấy người thử kẹt ở cài đặt, khóa API hay tự lưu trữ; phê duyệt không đi qua relay (FR-EGR-05). |
| AP-D-05 | Thứ tự ưu tiên kênh Zalo so với Telegram. **Đã trả lời một phần:** lời duyệt gắn với `chat:telegram:<id>` (RFC-0019, Q-89); duyệt qua Zalo cần mở rộng bot duyệt (sửa RFC); FR-CH-01 xếp Zalo P1. Còn mở: thứ tự cho cảnh báo. |
| AP-D-06 | Xác nhận luật mặc định theo loại là tệp sinh ra, và có cần RFC không. **Đã trả lời:** không cần RFC; gate cho thiết bị mới do `neuroedge add part` sinh (VP-PT-07), thêm gate vào `gates/` là PR thường (`CONTRIBUTING.md` §3), mặc định về giá trị chỉ do Blueprint khai (MS-CT-06). Mặc định ngầm trong runtime vẫn cần RFC. |
| AP-D-07 | Thời gian chờ mặc định trong chuỗi leo thang. **Còn mở** (chưa có đặc tả đã duyệt cho chuỗi leo thang, MS-RT-07). |
| AP-D-08 | Định nghĩa "chặn oan" và ngưỡng đạt của các chỉ số. **Còn mở, bị giới hạn:** trước cổng chỉ có K1–K5 (Q-85 (3)); xem AP-D-16. |
| AP-D-09 | Chạy lại trên trace với cấu hình đề xuất có cần RFC không. **Đã trả lời:** chạy chỉ đọc không nằm trong danh sách RFC của `CONTRIBUTING.md` §3; sự kiện trace mới cho đoạn trace thì cần RFC (TSK-I2d-13). Studio đã có `POST /api/gates/<name>/whatif` và `POST /api/traces/<name>/replay` (`docs/spec/studio.md`). |
| AP-D-10 | Studio đang tạm dừng: tái dùng hay xây trang riêng. **Còn mở, có ràng buộc:** Studio chỉ nghe 127.0.0.1 và đang tạm dừng (`docs/spec/studio.md`); xem AP-D-12. |
| AP-D-11 | Trình duyệt hỗ trợ và ngưỡng hiệu năng. **Còn mở.** |
| AP-D-12 | Điện thoại tới được một trang có xác thực của hộp bằng cách nào, và một lần chạm trong ứng dụng mang nguồn duyệt nào? (mới) |
| AP-D-13 | Giới hạn theo giá trị cảm biến (vùng khóa) lấy từ đâu, khi `board.v1` chưa có? (mới) |
| AP-D-14 | Chat của ứng dụng đi tới bộ não bằng đường nào? (mới) |
| AP-D-15 | Một lần duyệt của gia đình khóa gì với `agent.toml`, linh kiện và gate? (mới) |
| AP-D-16 | Có mở một `Q-N` sửa Q-85 (3) để thêm chỉ số của ứng dụng không? (mới) |
| AP-D-17 | Các dòng ứng dụng thêm vào thẻ tính vào giới hạn 5 dòng thế nào? (mới) |

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
