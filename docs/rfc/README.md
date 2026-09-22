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
| [0002](0002-mo-rong-target-va-nguyen-thuy-thi-giac.md) | Mở rộng danh sách target và nguyên thủy thị giác | `board.v1` · `trace.v1` | 🟡 Đang thảo luận |
