# RFC-NNNN: <Tiêu đề ngắn, mô tả thay đổi>

| | |
|:---|:---|
| **Mã RFC** | NNNN |
| **Tiêu đề** | |
| **Lược đồ bị ảnh hưởng** | `gate.v1` / `trace.v1` / `board.v1` / *(không)* |
| **Yêu cầu PRD liên quan** | FR-… , NFR-… |
| **Người đề xuất** | |
| **Ngày mở** | YYYY-MM-DD |
| **Trạng thái** | 🟡 Đang thảo luận / ✅ Đã chấp thuận / ❌ Bị từ chối / ⏳ Hoãn |
| **Người phê duyệt** | *(bắt buộc với thay đổi phá vỡ tương thích)* |

> **Khi nào cần RFC:** mọi thay đổi trong `schemas/`, và mọi thay đổi ngữ nghĩa
> phân giải gate. Xem `CONTRIBUTING.md` §3 để biết ranh giới chính xác.

## 1. Vấn đề

*Nêu vấn đề quan sát được, không nêu giải pháp. Nếu vấn đề là một tệp không thể
thẩm định được hoặc một mệnh đề không thể diễn đạt, hãy dán tệp đó vào đây kèm
thông báo lỗi thực tế.*

## 2. Vì sao lược đồ hiện tại không giải quyết được

*Trích dẫn trường hoặc quy tắc cụ thể. Nếu đây là một mâu thuẫn nội tại của
lược đồ, chỉ rõ hai mệnh đề mâu thuẫn nhau.*

## 3. Thay đổi đề xuất

*Diff hoặc trước/sau. Với JSON Schema, dán đoạn trước và đoạn sau.*

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | |
| Tệp đang không hợp lệ có trở nên hợp lệ? | |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | |

**Quy tắc:** nếu một tệp đang hợp lệ trở thành không hợp lệ, đó là thay đổi phá
vỡ tương thích và **bắt buộc** tăng phiên bản lược đồ. Nới lỏng (tệp đang không
hợp lệ trở nên hợp lệ) có thể làm trong cùng phiên bản.

## 5. Ảnh hưởng an toàn

*Bắt buộc với `gate.v1`.* Thay đổi này có cho phép một gate trở nên **lỏng hơn**
theo bất kỳ đường nào không? Có ảnh hưởng tới năm nguyên tắc kế thừa (Phụ lục
B.5) hoặc tới mặc định fail-closed không?

Nếu câu trả lời là "có" ở bất kỳ mục nào, RFC cần người phê duyệt là kỹ thuật
trưởng.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| | |

## 7. Bằng chứng kiểm chứng

*Các test chứng minh thay đổi hoạt động, và các fixture phản chứng chứng minh
nó vẫn từ chối đúng thứ cần từ chối.*

- [ ] Ví dụ hợp lệ đã thêm vào `fixtures/`
- [ ] Ví dụ sai kèm thông báo lỗi kỳ vọng đã thêm vào `fixtures/*/invalid/` và `expected_errors.yaml`
- [ ] Test tự động đã thêm, nêu rõ tên
- [ ] `neuroedge verify` vẫn xanh

## 8. Việc phải làm khi chấp thuận

- [ ] Cập nhật `schemas/<lược đồ>.json`
- [ ] Cập nhật Phụ lục tương ứng trong `neuroedge-proposal.md`
- [ ] Cập nhật `neuroedge-prd.md` nếu có FR bị ảnh hưởng
- [ ] Cập nhật `neuroedge-roadmap.md` nếu có task hoặc tiêu chí ra bị ảnh hưởng
- [ ] Thêm/điều chỉnh fixture và test
