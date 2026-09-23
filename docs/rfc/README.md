# RFC — Đề xuất thay đổi lược đồ

Ba tệp trong `schemas/` là **lược đồ đã đóng băng** kể từ cuối Sprint 1. Chúng
là thước đo tuân thủ cho cả Khối 1a và 1b, đầu vào trực tiếp của
`neuroedge verify`, và đối tượng của chữ ký số gate. Vì vậy chúng không thay
đổi bằng một pull request thông thường.

## Quy trình

1. Sao `0000-template.md` thành `NNNN-<tên-ngắn>.md` với số kế tiếp.
2. Mở pull request **chỉ chứa tệp RFC**, chưa sửa lược đồ.
3. Thảo luận trên pull request đó. Mục 4 (tương thích) và mục 5 (an toàn) là hai
   mục không được để trống.
4. Khi được chấp thuận, sửa lược đồ trong một pull request thứ hai, dẫn chiếu
   số RFC trong thông điệp commit.

Thay đổi ảnh hưởng tới `gate.v1` hoặc tới ngữ nghĩa phân giải gate cần người
phê duyệt là **kỹ thuật trưởng**, vì đó là tầng an toàn.

## Danh mục

| RFC | Tiêu đề | Lược đồ | Trạng thái |
|:---|:---|:---|:---:|
| [0001](0001-gate-schema-conditional-requirements.md) | Yêu cầu trường có điều kiện cho gate kế thừa | `gate.v1` | ✅ Đã chấp thuận |
| [0002](0002-mo-rong-target-va-nguyen-thuy-thi-giac.md) | Mở rộng danh sách target | `board.v1` · `trace.v1` (chỉ enum `target`) | 🟡 Đang thảo luận |
| 0003 | Ghim `extends` bằng digest + đóng băng `decision_tree.v1.json` | `gate.v1` · lược đồ mới | ⏳ Đã đặt số, hoãn tới Sprint 4 (`TODOS.md` #15) |
| [0004](0004-ke-thua-budget-on-block.md) | Gate con không được nới `budget` và `on_block` | *(không — ngữ nghĩa phân giải)* | ✅ Đã chấp thuận |
| [0005](0005-rang-buoc-tham-so-trong-gate.md) | Gate tự khai ràng buộc tham số của hành động (Q-25) | `gate.v1` · ngữ nghĩa phân giải · bố cục Q-23 | ✅ Đã chấp thuận |
