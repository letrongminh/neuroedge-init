# Thoả thuận thử nghiệm với đối tác — danh sách việc (điều kiện đối tác 3)

> **Đây không phải văn bản pháp lý.** Đây là danh sách *điều thoả thuận bằng văn bản phải bao phủ*, để người soạn không bỏ sót. **Một luật sư rà và soạn lời văn trước khi ký.**
> Việc này là **bước của người** (chủ sản phẩm); không script nào làm thay. Đầu vào: `TODOS.md` #44 (điều khoản license thương mại; PolyForm Noncommercial không có điều khoản dùng thử),
> `LICENSING.md`, Q-70 (`roadmap/neuroedge-prd.md` §15), điều kiện đối tác 3 (`roadmap/neuroedge-roadmap.md` §4.3.3).

## 1. Phải xong trước khi giao wheel

- [ ] Luật sư đã rà bản thoả thuận (tên, ngày).
- [ ] Hai bên đã ký; mỗi bên giữ một bản; ngày hiệu lực ghi rõ.
- [ ] Người ký phía đối tác có thẩm quyền ký cho đội/công ty đó.
- [ ] Bản đối chiếu với `LICENSING.md` (giấy phép của mã) đã làm: thoả thuận **cho phép đánh giá** mà PolyForm Noncommercial không tự cho một công ty — hoặc ghi rõ cách khác (xem §2.1).

## 2. Thoả thuận phải nói rõ

### 2.1 Phạm vi và giấy phép
- [ ] **Mục đích:** *đánh giá* NeuroEdge trên thiết bị đối tác đang có; không phải triển khai sản xuất, không phải dùng thương mại.
- [ ] Quan hệ với PolyForm Noncommercial 1.0.0: đợt thử là một cấp quyền *đánh giá* bằng văn bản; mọi dùng thương mại sau đó cần thoả thuận khác (đầu vào: `TODOS.md` #44 — phạm vi, giá, hỗ trợ).
- [ ] Ai được dùng (tên đội/những người), ở đâu (những máy nào), bao nhiêu thiết bị.
- [ ] Không phân phối lại wheel; không đưa wheel lên index; không tạo sản phẩm dẫn xuất để bán.
- [ ] Gate, `guard.toml`, mã agent do đối tác viết **thuộc đối tác** (ghi rõ), không bị cấp ngược cho chúng tôi trừ phần phản hồi (§2.4).

### 2.2 An toàn
- [ ] **Không dùng cho thứ an toàn-tính-mạng, an ninh vật lý có hậu quả không hoàn tác, hay thiết bị y tế** trong đợt thử; hoặc đối tác tự chịu rủi ro bằng văn bản cho từng thiết bị đã nêu.
- [ ] Đối tác hiểu và xác nhận các giới hạn ở [`docs/user/doi-tac/gioi-han.md`](../../user/doi-tac/gioi-han.md) (proxy không chặn lời gọi thẳng; không xác thực ở front `proxy http`; http thuần trên LAN khi bật `allow_lan_http`; `linux` trên Pi thử nghiệm; Home Assistant mới kiểm trên bản giả).
- [ ] Không bảo hành, không cam kết "an toàn": phần mềm đánh giá, "as is"; trách nhiệm hữu hạn theo lời luật sư.
- [ ] Quy trình dừng: đối tác được và nên dừng dùng ngay khi thấy hành vi bất thường; đầu mối báo sự cố an toàn (xem [`kenh-phan-hoi.md`](kenh-phan-hoi.md)).

### 2.3 Bảo mật và dữ liệu
- [ ] **Bảo mật hai chiều** phần mềm chưa phát hành và thông tin kỹ thuật bên kia (thời hạn, ngoại lệ).
- [ ] **Vết ghi:** chứa *tham số của lời gọi* (tên thiết bị, giá trị), không băm. Đối tác tự chọn gửi hay không, sau khi đọc; chúng tôi không tự thu. Ghi rõ điều này và cách xoá (thời hạn giữ, ai giữ, ở đâu).
- [ ] Đối tác không gửi token, mật khẩu, khoá; nếu lỡ gửi, chúng tôi xoá và đối tác đổi khoá.
- [ ] Báo lỗ hổng: kênh riêng, thời hạn phản hồi, không công bố trước khi vá (xem `SECURITY.md` nếu có).
- [ ] Dữ liệu cá nhân của người trong nhà/khách (nếu vết ghi hay tham số có): đối tác chịu trách nhiệm về cơ sở pháp lý khi gửi; hai bên cùng nêu xử lý.

### 2.4 Phản hồi
- [ ] Đối tác đồng ý dùng [`phan-hoi.md`](../../user/doi-tac/phan-hoi.md) và dự một buổi đo ≤ 15 phút ([`buoi-do.md`](buoi-do.md)).
- [ ] Quyền của chúng tôi dùng phản hồi để cải tiến sản phẩm (không kèm quyền dùng dữ liệu mật hay mã của đối tác).
- [ ] Quyền nêu tên đối tác: **mặc định không**; chỉ khi có đồng ý bằng văn bản riêng (và nội dung được duyệt).
- [ ] Phản hồi có thể vào tài liệu nội bộ (`TODOS.md` #19) ở dạng ẩn danh.

### 2.5 Hỗ trợ, thời hạn, sau đợt thử
- [ ] Mức hỗ trợ: **nỗ lực tốt nhất**, giờ làm việc nào, đầu mối nào, thời gian phản hồi mục tiêu — *không* là cam kết dịch vụ.
- [ ] Thời hạn (ngày bắt đầu, ngày kết thúc) và cách gia hạn.
- [ ] Chấm dứt: mỗi bên có quyền chấm dứt, đối tác xoá wheel và vết ghi chúng tôi gửi, trong bao lâu.
- [ ] Sau đợt thử: không có nghĩa vụ mua/cấp phép; nếu hai bên muốn đi tiếp, đàm phán điều khoản thương mại riêng.

## 3. Việc của chủ sản phẩm quanh thoả thuận (không phải điều khoản)

- [ ] Chốt **đội đối tác** và **thiết bị họ sẽ che** (điều kiện bắt đầu, Q-70) — ghi vào biên bản đợt thử.
- [ ] Gửi wheel (dựng từ job `build` + `smoke` của `release-pypi.yml` chạy tay; không publish) **sau** khi thoả thuận ký.
- [ ] Mở kênh phản hồi riêng ([`kenh-phan-hoi.md`](kenh-phan-hoi.md)) và lên lịch buổi đo ([`buoi-do.md`](buoi-do.md)).
- [ ] Ghi vào `TODOS.md` #44 điều gì đợt thử dạy về điều khoản thương mại (sau đợt thử).
