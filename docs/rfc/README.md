# RFC — Đề xuất thay đổi hợp đồng đã đóng băng

Lược đồ trong `schemas/`, ngữ nghĩa phân giải gate, ba vết ghi chuẩn mực, gate đã khoá
trong `digests.lock` và bố cục nhị phân `NETR` là thước đo tuân thủ và đối tượng của chữ
ký số gate, nên chúng không thay đổi bằng một pull request thông thường. Danh sách chính
xác những gì cần RFC: [`CONTRIBUTING.md` §3](../../CONTRIBUTING.md#3-thay-đổi-cần-rfc).

## Quy trình

1. Sao `0000-template.md` thành `NNNN-<tên-ngắn>.md` với số kế tiếp.
2. Mở pull request **chỉ chứa tệp RFC**, chưa sửa hợp đồng.
3. Thảo luận trên pull request đó. Mục 4 (tương thích) và mục 5 (an toàn) là hai
   mục không được để trống.
4. Khi được chấp thuận, sửa trong một pull request thứ hai, dẫn chiếu số RFC trong
   thông điệp commit, và cập nhật dòng của RFC trong danh mục dưới đây.

Người phê duyệt: `CONTRIBUTING.md` §3.

## Danh mục

| RFC | Tiêu đề | Lược đồ | Trạng thái |
|:---|:---|:---|:---:|
| [0001](0001-gate-schema-conditional-requirements.md) | Yêu cầu trường có điều kiện cho gate kế thừa | `gate.v1` | ✅ Đã chấp thuận |
| [0002](0002-mo-rong-target-va-nguyen-thuy-thi-giac.md) | Mở rộng danh sách target | `board.v1` · `trace.v1` (chỉ enum `target`) | 🟡 Đang thảo luận |
| [0003](0003-bo-cuc-nhi-phan-cay.md) | Bố cục nhị phân `NETR` v1 của cây trên thiết bị (Q-23) — thu hẹp; ghim `extends` vẫn hoãn (`TODOS.md` #15) | *(định dạng mới, ngoài `schemas/`)* | ✅ Đã chấp thuận |
| [0004](0004-ke-thua-budget-on-block.md) | Gate con không được nới `budget` và `on_block` | *(không — ngữ nghĩa phân giải)* | ✅ Đã chấp thuận |
| [0005](0005-rang-buoc-tham-so-trong-gate.md) | Gate tự khai ràng buộc tham số của hành động (Q-25) | `gate.v1` · ngữ nghĩa phân giải · bố cục Q-23 | ✅ Đã chấp thuận |
| [0006](0006-xac-nhan-ask-confirms.md) | `on_block.confirms` — tiêu chí người trên thiết bị được xác nhận thay (Q-26) | `gate.v1` · ngữ nghĩa phân giải · lượng giá | ✅ Đã chấp thuận |
