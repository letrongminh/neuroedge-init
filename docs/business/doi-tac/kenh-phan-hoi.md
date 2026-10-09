# Kênh phản hồi riêng và quy trình tiếp nhận lỗi (điều kiện đối tác 4)

> Việc của người: mở kênh, mời đúng người, giữ nhịp. Danh sách dưới đây là việc phải làm và quy ước nên dùng; **công cụ cụ thể (chat, thư, issue tracker) do chủ sản phẩm chọn** — chúng tôi không đề xuất nhà cung cấp.

## 1. Mở kênh (làm một lần)

- [ ] **Một kênh riêng cho đúng đội đối tác** (không dùng kênh công khai, không dùng chung với đối tác khác): có thể xoá được, và chỉ những người được liệt kê vào được.
- [ ] Danh sách thành viên hai phía ghi ở một chỗ: đầu mối kỹ thuật phía đối tác, người trực phía chúng tôi (có người thay thế).
- [ ] Ghim ở đầu kênh: (1) liên kết [`README.md`](../../user/doi-tac/README.md), [`gioi-han.md`](../../user/doi-tac/gioi-han.md), [`phan-hoi.md`](../../user/doi-tac/phan-hoi.md); (2) quy tắc §2; (3) giờ hỗ trợ và thời gian phản hồi mục tiêu **như đã ghi trong thoả thuận** ([`thoa-thuan.md`](thoa-thuan.md) §2.5).
- [ ] **Kênh riêng cho báo lỗ hổng bảo mật** (một địa chỉ thư riêng hoặc tương đương), tách khỏi kênh chung.
- [ ] Một nơi **ghi lỗi** mà chỉ phía chúng tôi (và đối tác nếu họ muốn) xem được: mỗi lỗi một mục, có người nhận, có trạng thái.
- [ ] Thử một vòng: đối tác gửi tin thử, người trực trả lời, mục thử được tạo và đóng.

## 2. Quy tắc trong kênh

- **Không dán token, mật khẩu, khoá, địa chỉ nội bộ.** Thay bằng `<token>`. Ai lỡ dán: xoá tin, đổi khoá, ghi lại.
- **Không gửi vết ghi chưa đọc.** Vết ghi chứa tham số của lời gọi (tên thiết bị, giá trị) — không băm. Gửi sau khi đã đọc và đồng ý ([`phan-hoi.md`](../../user/doi-tac/phan-hoi.md)). Mặc định: gửi **mô tả và thông báo lỗi nguyên văn** trước, vết ghi sau nếu cần.
- **Sự cố an toàn** (thiết bị làm điều gì đó ngoài ý muốn): đối tác dừng proxy/agent trước, báo sau. Người trực xác nhận đã nhận trong thời gian ngắn nhất có thể, và không đoán nguyên nhân qua chat — xin vết ghi.

## 3. Tiếp nhận lỗi

Mỗi báo cáo được hỏi đủ các mục sau (mẫu để chép vào kênh khi thiếu):

```text
PHIÊN BẢN:     `neuroedge --help | head -3`, `pip show neuroedge | head -2`, Python, hệ điều hành
HƯỚNG DẪN/BƯỚC: tên hướng dẫn và lệnh đã gõ
THÔNG BÁO:     nguyên văn (kèm ba dòng why/fix)
MONG ĐỢI:      …
THỰC TẾ:       …
LẶP LẠI ĐƯỢC KHÔNG: luôn / đôi khi / một lần
VẾT GHI:       (tuỳ chọn; đã đọc chưa)
```

Phân loại, theo thứ tự ưu tiên:

1. **An toàn:** một lời gọi **lẽ ra bị gate chặn mà lọt** (hoặc thiết bị bị chạm mà gate không cho). Ưu tiên cao nhất, mọi thứ khác dừng. Cần vết ghi và gate để tái hiện.
2. **Chặn đối tác:** không cài/không chạy được một hướng dẫn. Trả lời trong ngày làm việc kế tiếp.
3. **Khó hiểu / thông báo lỗi tệ:** sửa hướng dẫn hoặc thông báo (ghi vào `phan-hoi`).
4. **Mong muốn tính năng:** ghi lại, không hứa.

Mỗi lỗi: người nhận, mức, hạn mục tiêu, trạng thái (mới / đang xử lý / chờ đối tác / xong), và liên kết tới sửa. Báo lại đối tác khi xong.

## 4. Nhịp

- [ ] Sau ngày đầu: người trực hỏi "đã tới BLOCK đầu chưa?".
- [ ] Hằng tuần trong thời hạn đợt thử: tóm tắt lỗi mở và điều đã học (hai dòng), gửi đối tác.
- [ ] Cuối đợt thử: gom phản hồi vào `TODOS.md` #19 (ẩn danh), tổng hợp điều dạy về điều khoản (#44), đóng kênh theo thoả thuận (xoá dữ liệu đã hẹn xoá).
