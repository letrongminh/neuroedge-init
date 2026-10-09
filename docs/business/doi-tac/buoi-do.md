# Buổi đo ≤ 15 phút với đối tác (điều kiện đối tác 5)

> Điều kiện (roadmap §4.3.3, Q-60): *đội đối tác cài wheel trên máy của họ, chạy ba hướng dẫn và che được một MCP server hoặc API thiết bị thật của họ trong ≤ 15 phút.*
> Buổi này đo đúng điều đó. Nó là **bước của người**; script duy nhất là đồng hồ ([`scripts/partner_session_timer.sh`](../../../scripts/partner_session_timer.sh)).
> Hướng dẫn người tham gia đọc: [`docs/user/doi-tac/`](../../user/doi-tac/README.md). Đã có script chạy mọi lệnh của hướng dẫn trên bản giả
> ([`scripts/partner_guides_check.sh`](../../../scripts/partner_guides_check.sh)) — buổi này đo điều script không đo được: **người thật, máy thật, thiết bị thật**.

## 1. Vai

| Vai | Ai | Việc |
|:---|:---|:---|
| **Người tham gia** | Một kỹ sư của đội đối tác, trên **máy của họ** | Làm theo hướng dẫn một mình, nói to điều đang nghĩ |
| **Người quan sát** | Một người của chúng tôi | Bấm đồng hồ, ghi lời nguyên văn, đếm gợi ý. **Không chỉ trỏ, không gõ hộ** |
| **Người hỗ trợ** (tuỳ chọn) | Người của chúng tôi, có thể là người quan sát | Chỉ trả lời khi người tham gia đã mắc **hai phút** hoặc hỏi thẳng; mỗi lần là **một gợi ý** và ghi lại |

## 2. Trước buổi (người quan sát)

- [ ] Thoả thuận đã ký ([`thoa-thuan.md`](thoa-thuan.md)); kênh phản hồi đã mở ([`kenh-phan-hoi.md`](kenh-phan-hoi.md)).
- [ ] Người tham gia đã nhận wheel và biết sẽ làm gì, **chưa** được đọc hướng dẫn.
- [ ] Máy của họ có Python 3.11+ và mạng; **thiết bị/MCP server thật** đã bật, họ biết địa chỉ, và token đã sẵn ở một chỗ lấy được (không dán vào chat).
- [ ] Đã chọn **một** hướng dẫn phù hợp thiết bị (README của thư mục hướng dẫn có bảng chọn). Mục tiêu: ALLOW có chủ ý trên thứ thật.
- [ ] Người tham gia đồng ý để quan sát và ghi chép (ghi hình màn hình là tuỳ chọn, cần đồng ý riêng).
- [ ] Mở sẵn `scripts/partner_session_timer.sh` ở một cửa sổ của người quan sát; chuẩn bị [`phan-hoi.md`](../../user/doi-tac/phan-hoi.md) in hoặc mở sẵn.

## 3. Kịch bản từng phút

Đồng hồ chạy từ lúc người tham gia **mở `README.md`** (S0). Các mốc là *mục tiêu* — đồng hồ ghi thực tế, không ép người tham gia theo.

| Phút | Mã | Người tham gia làm | Người quan sát |
|:---:|:---:|:---|:---|
| 0:00 | **S0** | Mở `README.md` của thư mục hướng dẫn, chọn hướng dẫn | Bấm S0. Chỉ nói: "làm theo tài liệu, nói to điều bạn nghĩ" |
| 0:00–2:00 | **S1** | Tạo venv, cài wheel với `[mcp]`, gõ `neuroedge --help` | Bấm S1 khi lệnh chạy được. Ghi lỗi cài nguyên văn |
| 2:00–5:00 | **S2** | Chạy lệnh đầu của hướng dẫn (`guard init …` hoặc viết gate) với địa chỉ thật | Bấm S2 khi lệnh xong. Ghi mọi chỗ khựng |
| 5:00–7:00 | **S3** | Gọi thử qua proxy/agent; **thấy BLOCK** | Bấm S3. Hỏi: "BLOCK này nghĩa là gì, theo bạn?" — ghi câu trả lời nguyên văn |
| 7:00–10:00 | **S4** | Mở gate **bằng tay** (xoá `operator_approved` hoặc điều kiện riêng) | Bấm S4 khi họ lưu gate. Ghi họ đã sửa gì và vì sao |
| 10:00–12:00 | **S5** | Chạy lại và **thấy ALLOW** trên thiết bị/MCP server thật | Bấm S5: **mốc đạt/không đạt (§5)**. Ghi: thiết bị có thật sự động không |
| 12:00–13:30 | **S6** | `neuroedge trace show …`; chỉ ra lời gọi vừa rồi | Bấm S6. Hỏi: "tìm giúp tôi lời gọi bị BLOCK lúc nãy" |
| 13:30–15:00 | **S7** | `neuroedge plugin doctor …`; giải thích một cảnh báo | Bấm S7 khi họ nói được vì sao nó cảnh báo (kể cả "tôi cần chặn tường lửa") |
| 15:00 | **S8** | Dừng | Bấm S8. Dù xong hay chưa, **dừng ở 15:00 hoặc khi họ bỏ**; không kéo dài |

Sau 15:00 (tối đa 15 phút, ngoài đồng hồ): hỏi *"điều gì khó hiểu nhất?"*, *"bạn sẽ đặt gate trước thứ gì tiếp theo?"*, rồi để họ điền [`phan-hoi.md`](../../user/doi-tac/phan-hoi.md) (hoặc điền cùng họ).
Câu hỏi giá và thông điệp (`TODOS.md` #19) **không** hỏi trong buổi này — dành cho buổi nói chuyện sau (xem `phan-hoi.md`).

## 4. Đo gì

Đồng hồ ghi, mỗi bước: giờ, số giây từ S0, số **gợi ý** và ghi chú. Ngoài đồng hồ, người quan sát ghi:

- **Gợi ý:** mỗi lần người hỗ trợ nói điều gì giúp người tham gia tiến lên là một gợi ý (chép nội dung). Chỉ đọc lại thông báo lỗi cho họ **không** tính; chỉ họ cách làm thì tính.
- **Lỗi nguyên văn** (ba dòng `why`/`fix`) và lệnh gây ra.
- **Chỗ hiểu sai:** thuật ngữ hay câu trong hướng dẫn họ đọc lại hai lần; điều họ đoán sai.
- **Điều họ làm mà hướng dẫn không nói** (lối tắt, công cụ khác).
- Thiết bị/MCP server **thật** hay bản giả; có thật sự động ở S5 không; token xử lý ra sao (có dán vào chỗ không nên?).

## 5. Quy tắc đạt

Buổi **đạt** khi **tất cả** đúng:

1. **S5 đạt trong ≤ 15:00** từ S0, trên một MCP server hoặc API thiết bị **thật** của họ (không phải bản giả của chúng tôi), trên **máy của họ**, từ wheel chúng tôi giao.
2. Số gợi ý tổng cộng **≤ 3**, và không gợi ý nào là sửa hộ gate hay gõ hộ lệnh.
3. **BLOCK thật sự đứng trước ALLOW** (S3 trước S5): người tham gia thấy gate chặn rồi mới tự mở. Nếu họ mở gate trước khi thấy BLOCK, buổi không đạt điều kiện này.
4. Không có lời gọi nào tới thiết bị/MCP server thật mà gate đáng lẽ chặn (kiểm nhật ký của thiết bị/server nếu có).

**Không đạt** vẫn là kết quả có giá trị: ghi bước nào, vì sao (lỗi, hướng dẫn thiếu, hạn chế của sản phẩm — gồm cả điều cần đưa vào [`gioi-han.md`](../../user/doi-tac/gioi-han.md)). Lặp lại sau khi sửa hướng dẫn, với một người tham gia khác nếu có.
Một lỗi an toàn (lời gọi lọt gate) dừng mọi thứ và đi theo quy trình ở [`kenh-phan-hoi.md`](kenh-phan-hoi.md) §3.

## 6. Bảng kết quả (chép cho mỗi buổi)

| | |
|:---|:---|
| Ngày · người tham gia (mã ẩn danh) · người quan sát | |
| Hướng dẫn đã dùng · thiết bị/MCP server (thật?) | |
| Phiên bản (`pip show neuroedge`) · hệ điều hành · Python | |

| Mã | Mục tiêu | Thực tế (mm:ss) | Gợi ý | Ghi chú |
|:---:|:---:|:---:|:---:|:---|
| S1 cài xong | ≤ 2:00 | | | |
| S2 lệnh đầu xong | ≤ 5:00 | | | |
| S3 thấy BLOCK | ≤ 7:00 | | | |
| S4 tự mở gate | ≤ 10:00 | | | |
| **S5 ALLOW trên thứ thật** | **≤ 15:00** | | | |
| S6 đọc vết ghi | ≤ 13:30 | | | |
| S7 doctor | ≤ 15:00 | | | |

| Điều kiện đạt (§5) | Có / không | Bằng chứng |
|:---|:---:|:---|
| 1. S5 ≤ 15:00 trên thứ thật, máy của họ | | |
| 2. Gợi ý ≤ 3, không sửa/gõ hộ | | |
| 3. BLOCK trước ALLOW | | |
| 4. Không lời gọi nào lọt gate | | |
| **Kết luận: ĐẠT / KHÔNG ĐẠT** | | |

Lỗi nguyên văn · chỗ hiểu sai · điều họ làm ngoài hướng dẫn · việc sẽ sửa (hướng dẫn / thông báo / sản phẩm):

(điền)

## 7. Sau buổi

- [ ] Gộp CSV của đồng hồ và bảng trên vào một biên bản (ẩn danh) — "biên bản đợt thử" của TSK-I2c-19.
- [ ] Mọi lỗi vào nơi ghi lỗi ([`kenh-phan-hoi.md`](kenh-phan-hoi.md) §3); mọi chỗ hiểu sai thành một sửa hướng dẫn hoặc thông báo.
- [ ] Nếu đạt: đánh dấu điều kiện đối tác 5 ở roadmap §4.3.3 (người có thẩm quyền). Nếu không: ghi vì sao, và lặp lại sau khi sửa.
