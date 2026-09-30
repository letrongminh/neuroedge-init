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
| [0007](0007-digital-in-i2c-analog-in-phong-bi.md) | `digital.in`, bus I2C chỉ đọc, `analog.in` và phong bì an toàn trong `board.v1` — TSK-N0-03 (Q-53) | `board.v1` (`gate.v1` không đổi) | ⏳ Nháp |
| [0008](0008-vet-ghi-chuan-muc-mang-gate-digest.md) | Ba vết ghi chuẩn mực mang `gate_digest` — phát lại kiểm nó | `trace.v1` *(chỉ `data` của ba vết ghi; tệp lược đồ không đổi)* | ✅ Đã chấp thuận |
| [0009](0009-tieu-chi-so-numeric.md) | Tiêu chí số `evaluate.type: numeric` — TSK-W1-02 (Q-53, Q-54) | `gate.v1` · ngữ nghĩa phân giải · `NETR` | ⏳ Nháp |
| [0010](0010-pwm-trong-digital-out.md) | PWM trong `digital.out` — TSK-W1-01 (Q-53) | `board.v1` | ⏳ Nháp |
| [0011](0011-nguyen-thuy-motion.md) | Nguyên thủy `motion.*`, token thuê có hạn, trạng thái an toàn theo cơ cấu — TSK-W1-03 (Q-53) | `board.v1` · sổ token · `NETR` | ⏳ Nháp |
| [0012](0012-nguyen-thuy-vision-in.md) | Nguyên thủy `vision.in`; kết quả thị giác vào gate dưới dạng dữ kiện — TSK-V1b-07 (Q-53, Q-54) | `board.v1` *(`trace.v1` không đổi)* | ⏳ Nháp |
| [0013](0013-nguyen-thuy-tuy-chon-va-nhieu-bo-tham-chieu.md) | Nguyên thủy mở rộng tuỳ chọn theo bo mạch; nhiều bo tham chiếu mỗi target; `sim-rpi5` — TSK-I2a-07 (Q-53) | *(không — bất biến kiểm thử, sửa RFC-0002 §5b, §5c)* | ⏳ Nháp |

**Bản nháp chưa cấp số** (ngoài thư mục này; nhận số kế tiếp khi mở PR RFC):
[`draft-rfc-node-giao-thuc-dieu-phoi.md`](../../roadmap/draft-rfc-node-giao-thuc-dieu-phoi.md) — giao thức điều phối
node cho robot phân tầng; các RFC tạm tên còn lại ở §2.2 của
[`draft-ke-hoach-mo-rong-robot-fofoca.md`](../../roadmap/draft-ke-hoach-mo-rong-robot-fofoca.md) (RFC-numeric và RFC-motion đã thành RFC-0009 và RFC-0011).
