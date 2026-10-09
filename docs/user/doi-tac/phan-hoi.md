# Mẫu phản hồi — đợt thử với đối tác

Chép khối bên dưới vào một tệp hoặc thư gửi theo kênh riêng chúng tôi đã mở cho đội bạn, điền, và gửi sau **mỗi** hướng dẫn bạn chạy (một bản cho mỗi hướng dẫn). Điền được đến đâu hay đến đó:
một phản hồi dở dang vẫn có giá trị hơn không có. **Đừng dán token, mật khẩu hay địa chỉ nội bộ** — thay bằng `<token>`, `<địa-chỉ-nhà>`.

Đồng hồ: bấm giờ từ lúc bạn mở `README.md` của thư mục này. Đo giúp bằng `scripts/partner_session_timer.sh` nếu có người ngồi cùng
([`docs/business/doi-tac/buoi-do.md`](../../business/doi-tac/buoi-do.md)); không có thì ghi xấp xỉ, ghi rõ "xấp xỉ".

```text
HƯỚNG DẪN:            (home-assistant-mcp | guard-python | proxy-http)
NGÀY / MÁY:           (hệ điều hành, phiên bản Python, `pip show neuroedge | head -2`)
CHE CÁI GÌ:           (MCP server / API / agent nào; thiết bị thật hay bản thử?)

THỜI GIAN
  Tới lệnh `neuroedge` chạy được (cài xong):          ___ phút
  Tới BLOCK đầu tiên (thấy gate chặn):                 ___ phút
  Tới ALLOW đầu tiên CÓ CHỦ Ý (sau khi bạn mở gate):   ___ phút
  Tổng thời gian tới khi bạn che được thứ thật:        ___ phút   (hay: chưa che được — vì sao?)

LỖI GẶP PHẢI (chép NGUYÊN VĂN thông báo, ba dòng why/fix nếu có; kèm lệnh đã gõ)
  1. Lệnh:
     Thông báo:
     Bạn đã làm gì để qua? (hay: chưa qua)
  2. …

ĐIỀU KHÓ HIỂU / MẤT THỜI GIAN (câu nào trong hướng dẫn, thuật ngữ nào, bước nào thiếu)
  -

ĐIỀU BẤT NGỜ (tốt hoặc xấu)
  -

GATE BẠN ĐÃ MỞ, VÀ VÌ SAO (tool/route nào, điều kiện bạn viết vào gate)
  -

BẠN SẼ ĐẶT GATE TRƯỚC THỨ GÌ TIẾP THEO (thiết bị, tool, hệ thống — nêu cụ thể)
  -

VẾT GHI (tuỳ chọn): đính kèm `trace-*.json` — SAU KHI bạn đã đọc nó: nó chứa THAM SỐ của lời gọi (tên thiết bị, giá trị).
  [ ] Tôi đã đọc, và đồng ý gửi.   [ ] Tôi không gửi.
```

## Câu hỏi giúp chúng tôi quyết thông điệp và giá (`TODOS.md` #19)

Phần này **không** thuộc hướng dẫn kỹ thuật; trả lời trong một buổi nói chuyện ngắn sau đợt thử nếu bạn đồng ý. Chúng tôi dùng bộ câu hỏi đã có
([`docs/business/cong-nhu-cau-2026-10-25/phong-van.md`](../../business/cong-nhu-cau-2026-10-25/phong-van.md)) thay vì chép lại ở đây — hỏi về chuyện **đã xảy ra** và cái giá thật, không hỏi ý kiến về sản phẩm.
Những câu sẽ được hỏi, và mục tương ứng:

| Chủ đề | Câu hỏi gốc | Ghi gì |
|:---|:---|:---|
| Lần gần nhất một thiết bị/AI làm sai ngoài đời, và nó tốn gì | §4 S2–S3 (Smart Home), các mục cùng chủ đề ở §2, §3, §5 | Ngày, nguyên nhân, con số **người trả lời tự nêu** |
| Hiện chặn lệnh nguy hiểm của AI bằng cách nào, trước khi có gate | §4 S9 | Cách làm hiện tại, tốn bao nhiêu giờ |
| Tiền đang chi cho công cụ kiểm thử, vận hành thiết bị | §4 S11 | Khoản cụ thể và người duyệt — **không gợi giá** |
| Gate này đáng giá bao nhiêu với bạn, với đội bạn | (mới — đợt thử) | Để im, ghi con số họ nói trước, ai nói trước |
| Bạn sẽ giới thiệu cho ai | §6 E2, E4 | Một cam kết cụ thể |

Lời của bạn đi vào mục #19 của sổ hoãn (`TODOS.md`) và vào quyết định thông điệp/giá trước khi công khai; chúng tôi không dẫn tên bạn khi chưa có sự đồng ý bằng văn bản.
