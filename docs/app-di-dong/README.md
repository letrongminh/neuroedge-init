# App nhà trên điện thoại: từ user story đến prototype

> **Trạng thái:** bản nháp đề xuất, 16/10/2026. **Chưa có quyết định `Q-N`, chưa có task trong
> roadmap; thư mục này không đổi tiến độ hay phạm vi nào.** Muốn đưa vào làm cần một `Q-N` mới ở
> `roadmap/neuroedge-prd.md` §15, sau khi chủ sản phẩm trả lời các câu hỏi mở `AP-D-nn` của SRS §6.

## Vì sao có thư mục này

Người dùng không muốn viết YAML, gate hay contract, nhưng mỗi nhà một khác nên vẫn phải cấu hình.
Thư mục này đề xuất một app trên điện thoại: chat với AI, chỉnh con số bằng thanh trượt có ba vùng
màu, duyệt mọi thay đổi bằng vân tay, xem trước bằng cách chạy lại trace hôm qua, thêm thiết bị qua
trình hướng dẫn. Gate và contract vẫn ở bên dưới, không biến mất: chúng được sinh ra và chỉ hiện sau
nút "Xem chi tiết".

## Đọc theo thứ tự

| Bước | Tài liệu | Trả lời câu hỏi | Mã |
|:---|:---|:---|:---|
| 1 | [`01-user-stories.md`](01-user-stories.md) | Ai dùng, muốn gì, xong thì trông thế nào | `US-APP-nn` |
| 2 | [`02-brd.md`](02-brd.md) | Vì sao đáng làm, thị trường, phạm vi, chỉ số | `BR-APP-nn` |
| 3 | [`03-srs.md`](03-srs.md) | App phải làm gì, dựa trên phần nào đã có, kiểm chứng ra sao | `AP-xxx-nn`, `AP-D-nn` |
| 4 | [`prototype/index.html`](prototype/index.html) | Bấm thử 8 màn hình MH-1 → MH-8 (MH để không nhầm với mục tiêu sản phẩm M1–M9) | — |

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

Phần chăm sóc người cao tuổi ("Nhà bố mẹ") trong các tài liệu này là hướng sau cổng nhu cầu: PRD §14
đang hoãn mảng này (Q-72) và R-19 xếp rủi ro pháp lý ở mức cao. App chỉ báo người thân về thay đổi
thói quen, không chẩn đoán, không phát hiện bệnh.
