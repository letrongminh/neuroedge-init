# Hướng dẫn sử dụng — hôm nay làm được gì

> Bản đồ tài liệu ở [`README.md`](README.md). Cú pháp lệnh và đầu ra kỳ vọng
> nằm ở [`CHANGELOG.md`](../../CHANGELOG.md) §2.3 — tệp này không chép lại.

## 1. Cài đặt

Chưa có bản phát hành trên PyPI (`TSK-S3-14`). Cài từ mã nguồn theo
[`python/README.md`](../../python/README.md).

Yêu cầu: Python 3.11+ (`Q-1`). `sim` mặc định **gõ chữ** — không cần khoá API,
không cần mạng, kết quả tất định (`Q-15`).

## 2. Hôm nay dùng được gì

Phần **chính sách gate** và **lõi thực thi trên `sim`** đã có (mã A1, 2026-09-23);
vòng lặp gõ chữ `neuroedge run` là việc còn lại. Cú pháp từng lệnh: `CHANGELOG.md` §2.3.

| Việc | Lệnh | Trạng thái |
|:---|:---|:---:|
| Kiểm cả kho gate phân giải được | `neuroedge gate lint` | ✅ |
| Xem gate đã phân giải, kiểm tra kế thừa | `neuroedge gate resolve` | ✅ |
| In digest để ghim phiên bản gate | `neuroedge gate publish` | ✅ |
| Thẩm định vết ghi theo `trace.v1` | `neuroedge trace validate` | ✅ |
| Xem nội dung một vết ghi | `neuroedge trace show` | ✅ |
| Liệt kê / xem profile bo mạch | `neuroedge board list` · `neuroedge board show` | ✅ |
| Đối chiếu năng lực agent ↔ bo mạch, biên dịch gate | `neuroedge build` | ✅ |
| Chạy agent có gate trên `sim` từ mã Python (`c.do()` trên `SimHAL`) | — (thư viện) | ✅ |
| Chạy agent có gate trên `sim` từ dòng lệnh | `neuroedge run` | ⏳ TSK-S3-06 |
| Hành trình 10 phút (TTFV) | — | ⏳ mốc M1 |

Kiểm tra nhanh toàn bộ artifact trong kho: `CHANGELOG.md` §2.2.

## 3. Chưa dùng được gì

Nói thẳng để bạn không mất thời gian:

- `neuroedge run` **thoát mã 2** — engine và HAL `sim` đã có, vòng lặp gõ chữ trên CLI
  là `TSK-S3-06`. Không có "PASS" giả (bất biến 10, `CHANGELOG.md` §3.3).
- Chưa có tương đương target: `neuroedge verify` mới kiểm ở mức lược đồ.
- Danh sách đầy đủ: `CHANGELOG.md` §3.7.

## 4. Khi gặp lỗi

Mọi thông báo lỗi đủ **3 thành phần** (ở đâu · vì sao · cách xử lý) — cách đọc
một thông báo lỗi: `CHANGELOG.md` §2.4.

## 5. Tiếp theo

- Việc đang làm và thứ tự tiếp theo: thẻ bàn giao `neuroedge-roadmap.md` §0.3.
- Trạng thái đầy đủ: [`trang-thai.md`](trang-thai.md).
- Muốn tài liệu này có thêm mục gì: mở issue hoặc PR theo
  [`CONTRIBUTING.md`](../../CONTRIBUTING.md).
