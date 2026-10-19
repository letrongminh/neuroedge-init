# App nhà trên điện thoại: từ user story đến prototype

> **Trạng thái:** Đã duyệt bởi Q-91 (2026-10-19); increment I2g, chờ sau cổng nhu cầu 2026-12-06.
> Q-91 (`roadmap/neuroedge-prd.md` §15) đã trả lời các câu hỏi mở `AP-D-01` → `AP-D-17`; SRS là bản đã duyệt
> cho I2g (task `TSK-I2g-01` → `TSK-I2g-13`, SRS §7). Trước cổng nhu cầu thư mục này không đổi phạm vi nào.

## Vì sao có thư mục này

Người dùng không muốn viết YAML, gate hay contract, nhưng mỗi nhà một khác nên vẫn phải cấu hình.
Thư mục này đặc tả một app gốc iOS và Android (React Native, Q-91 (2)): chat với AI, chỉnh con số bằng thanh
trượt có ba vùng màu, duyệt mọi thay đổi qua hộp (ký bằng vân tay hoặc Face ID trong nhà; ngoài nhà qua bot
duyệt riêng của hộp với bản ghi có chữ ký, RFC-0019; Q-91 (3), (5)), xem trước bằng cách chạy lại trace hôm
qua, thêm thiết bị qua trình hướng dẫn. Gate và contract vẫn ở bên dưới, không biến mất: chúng được sinh ra và chỉ hiện sau
nút "Xem chi tiết".

## Đọc theo thứ tự

| Bước | Tài liệu | Trả lời câu hỏi | Mã |
|:---|:---|:---|:---|
| 1 | [`01-user-stories.md`](01-user-stories.md) | Ai dùng, muốn gì, xong thì trông thế nào | `US-APP-nn` |
| 2 | [`02-brd.md`](02-brd.md) | Vì sao đáng làm, thị trường, phạm vi, chỉ số | `BR-APP-nn` |
| 3 | [`03-srs.md`](03-srs.md) | App phải làm gì, dựa trên phần nào đã có, kiểm chứng ra sao | `AP-xxx-nn`, `AP-D-nn` |
| 4 | [`prototype/index.html`](prototype/index.html) | Bấm thử 8 màn hình mẫu MH-1 → MH-8 (MH để không nhầm với mục tiêu sản phẩm M1–M9) | — |

Mỗi tầng truy vết về tầng trước: SRS §4 nối `BR-APP` và `US-APP` với từng yêu cầu `AP`. Ý nghĩa các
mã ở [`docs/user/thuat-ngu.md`](../user/thuat-ngu.md).

**Mở prototype:** mở thẳng file `prototype/index.html` trong trình duyệt. File tự chứa, không tải gì
từ mạng, dữ liệu là giả, không nối với hộp.

## Quan hệ với tài liệu đã duyệt

App là lớp trình bày, không đổi lõi. Những gì đã có quy định ở nơi khác thì SRS tham chiếu mã, không
chép lại:

* Contract, thẻ duyệt ≤ 5 dòng, approval record, detector, cảnh báo khẩn: [`docs/spec/missions.md`](../spec/missions.md) (Q-87).
* Cài Blueprint, tham số cài đặt: [`docs/spec/blueprint.md`](../spec/blueprint.md) (Q-86).
* Hai cách triển khai A và B: [`docs/spec/deployment_profiles.md`](../spec/deployment_profiles.md) (Q-83).
* Yêu cầu kinh doanh của trợ lý nhà: [`docs/business/brd-ambient-intelligence.md`](../business/brd-ambient-intelligence.md) (Q-85).
* Bản ghi duyệt có chữ ký, bot duyệt riêng của hộp, ghép chủ hộp: [`docs/rfc/0019-ban-ghi-duyet-co-chu-ky.md`](../rfc/0019-ban-ghi-duyet-co-chu-ky.md) (Q-89).
* Linh kiện ảo và canvas hoãn: [`docs/spec/virtual_parts.md`](../spec/virtual_parts.md) (Q-84). Đường soạn hợp đồng qua MCP: TSK-I2d-23 (Q-88).

Phần chăm sóc người cao tuổi ("Nhà bố mẹ") trong các tài liệu này là hướng sau cổng nhu cầu: PRD §14
đang hoãn mảng này (Q-72) và R-19 xếp rủi ro pháp lý ở mức cao. App chỉ báo người thân về thay đổi
thói quen, không chẩn đoán, không phát hiện bệnh.

## Thay đổi 2026-10-17

Q-90 (6) yêu cầu bản nháp khớp Q-84, Q-85, Q-86, Q-88, Q-89 và RFC-0019; bản nháp vẫn không có `Q-N` riêng
và không có task. Đã sửa:

* Duyệt hành động vật lý đi qua hộp: trang cục bộ hoặc bot duyệt riêng của hộp với bản ghi có chữ ký
  (DP-A-05, DP-A-06, RFC-0019). Vân tay là phương thức sau (FR-CH-08, TSK-I2f-08), không phải tiền đề.
* Ghép chủ hộp theo Q-89 (mã dùng một lần hiện trên hộp); trần duyệt từ xa, nhãn `risk=remote_approval`
  và thu hồi được thêm vào SRS.
* Cài Blueprint theo BL-IN-01 → BL-IN-06; bằng chứng ghi "unsigned" (BL-EV-03); bỏ câu "đã qua Action CI".
* Trang cục bộ hiện chỉ nghe 127.0.0.1: việc phục vụ cho điện thoại là câu hỏi mở (AP-D-12), không phải điều
  đã có. Vùng khóa chỉ lấy từ những gì `board.v1` khai (AP-D-13).
* Gia đình tới sản phẩm qua Blueprint của maker trước cổng nhu cầu, chỉ số trước cổng là K1–K5 (Q-85):
  BR-APP-10 tạm dừng (AP-D-16). Trình hướng dẫn thiết bị chỉ trên `sim`; board thật là canvas giai đoạn C,
  hoãn (Q-84).
* Câu hỏi mở `AP-D-nn`: các câu đã có quyết định được đánh dấu kèm mã, phần còn lại giữ mở; thêm
  AP-D-12 → AP-D-17. SRS §7 liệt kê thêm các task đã có trong roadmap.

## Thay đổi 2026-10-19

Q-91 chuyển bản nháp thành SRS đã duyệt cho increment I2g (Home app), chờ sau cổng nhu cầu 2026-12-06; K1–K5
trước cổng không đổi (Q-85). Đã sửa:

* Trạng thái ở cả bốn tài liệu; mười bảy câu hỏi `AP-D-01` → `AP-D-17` đều ghi "Đã quyết (Q-91 (n))".
* Dạng app là app gốc iOS và Android bằng React Native (Q-91 (2)); không còn "web di động". Hộp phục vụ API
  có xác thực trong mạng nhà, điện thoại ghép một lần bằng mã dùng một lần hiện trên hộp; ngoài nhà duyệt qua
  bot của hộp (Q-91 (3)). Studio mở lại làm trang web máy tính cho maker, dùng chung API hộp với app (Q-91 (4)).
* Duyệt bằng vân tay hoặc Face ID là nguồn người mới, sớm hơn FR-CH-08, chờ RFC (Q-91 (5)). Chat với bộ não qua
  kênh riêng của NeuroClaw (Q-91 (6)). Báo qua push không nội dung (APNs, FCM) và bot Telegram; Zalo P1; chuỗi
  leo thang hoãn cùng ngành dọc người cao tuổi (Q-91 (7)).
* Vùng vàng được phép khi chấp nhận rõ ràng và có nhãn rủi ro, trong giới hạn giá trị của `board.v1`; hai điều
  này chờ RFC. Thẻ duyệt ≤ 5 dòng, phần bổ sung bên dưới không tính. Gia đình đổi được tham số hợp đồng và gate,
  linh kiện do trình hướng dẫn sinh (qua `neuroedge gate lint`, khóa bằng duyệt ký sinh trắc tại nhà, chờ RFC);
  chỉ số của app và ngưỡng hiệu năng là tiêu chí thoát của I2g (Q-91 (8)–(10)).
* SRS §7 liệt kê `TSK-I2g-01` → `TSK-I2g-13`. Prototype chỉ sửa vài chuỗi cho khớp (Zalo, thông báo không nội dung).
