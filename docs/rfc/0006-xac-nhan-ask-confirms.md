# RFC-0006: Gate khai tiêu chí người được xác nhận thay — `on_block.confirms`

| | |
|:---|:---|
| **Mã RFC** | 0006 |
| **Tiêu đề** | `on_block: ask` có `confirms`: tiêu chí mà lời xác nhận của người trên thiết bị được thay |
| **Lược đồ bị ảnh hưởng** | `gate.v1` (thêm trường tuỳ chọn trong `on_block`) · ngữ nghĩa phân giải · lượng giá |
| **Yêu cầu PRD liên quan** | FR-ACE-10, FR-GATE-06, NFR-SEC-09 |
| **Người đề xuất** | V1 — Kỹ sư lõi nền tảng *(theo TSK-S3-26)* |
| **Ngày mở** | 2026-09-24 |
| **Trạng thái** | ✅ Đã chấp thuận — hiện thực ở TSK-S3-26 |
| **Người phê duyệt** | minhlt (kỹ thuật trưởng), 2026-09-24 — chọn "gate ghi rõ" (phương án A) trong ba phương án ở §6 |

> **Khi nào cần RFC:** mọi thay đổi trong `schemas/`, và mọi thay đổi ngữ nghĩa
> phân giải gate. Xem `CONTRIBUTING.md` §3 để biết ranh giới chính xác.

## 1. Vấn đề

Q-26 chốt: khi gate trả `on_block: ask`, **chỉ người, qua kênh thiết bị**, được xác nhận,
và xác nhận làm gate **lượng giá lại** chứ không bỏ qua gate. Nhưng `allow_when` là
**VÀ** của mọi mệnh đề:

```yaml
# fixtures/agents/home-voice/gates/light_off@1.0.0.yaml (trước RFC)
allow_when:
  call_source: { in: [local_grammar, system_one, system_two, mcp] }
  room_empty:  true
on_block: { action: ask, message: "Vẫn còn người trong phòng — bạn chắc muốn tắt đèn?" }
```

Phòng còn người ⇒ `room_empty = false` ⇒ BLOCK ⇒ hỏi. Người trả lời "có". Thêm dữ kiện
`human_confirmed = true` rồi lượng giá lại: `room_empty` **vẫn** false, gate **vẫn** chặn.
Lời xác nhận không bao giờ có tác dụng — `docs/spec/tool_calling.md` §6 bản v0 mắc đúng lỗi
này.

## 2. Vì sao lược đồ hiện tại không giải quyết được

- `allow_when` dạng cấu trúc chỉ có VÀ (Phụ lục B.2); dạng chuỗi CEL (có HOẶC) bị cấm trong
  chuỗi kế thừa (RFC-0001) và chưa được resolver nhận.
- `on_block` đặt `additionalProperties: false`: không có chỗ nói "điều gì người được thay".

## 3. Thay đổi đề xuất

```yaml
on_block:
  action:   ask
  message:  "Vẫn còn người trong phòng — bạn chắc muốn tắt đèn?"
  confirms: [room_empty]        # mới: tiêu chí lời xác nhận của người được thay
```

```json
"confirms": {
  "type": "array", "items": { "type": "string", "minLength": 1 },
  "minItems": 1, "uniqueItems": true
}
// và trong allOf của on_block: nếu có confirms thì action phải là "ask"
```

**Ngữ nghĩa.**

1. Mỗi phần tử của `confirms` là một tiêu chí của `allow_when` (resolver kiểm, sai ⇒
   `GateSchemaError`). Chỉ hợp lệ với `action: ask` (lược đồ kiểm).
2. Khi gate chặn, câu hỏi chỉ được **mở** (`tool_confirm_requested`) nếu lời "có" **đủ**
   để cho qua: cùng dữ kiện, với các tiêu chí trong `confirms` coi như đạt, phải ALLOW. Nếu
   gate chặn vì tiêu chí không nằm trong `confirms`, hoặc vì giới hạn tham số (RFC-0005),
   thì không hỏi người điều họ không thể thay.
3. Khi người xác nhận (chỉ `local_grammar` hoặc `ui`, Q-26), gate được lượng giá **lại** với
   dữ kiện hiện tại và nguồn gọi của yêu cầu gốc; tiêu chí trong `confirms` coi như đạt,
   **mọi tiêu chí khác, giới hạn tham số và fail-closed vẫn áp dụng**. Kết quả ghi
   `confirmed: [...]` trong `gate_evaluation_result`.
4. Adjudicator suy giảm (`gate_unreachable`, `budget_exceeded`) vẫn chặn theo `budget.fail`
   — xác nhận không thay được một câu hỏi chưa ai trả lời được.

**Kế thừa (B.5, nguyên tắc 2).** Gate con chỉ được **bớt** phần tử của `confirms`: thêm một
tiêu chí, hoặc chuyển từ `deny`/`escalate` sang `ask` có `confirms`, là nới lỏng ⇒
`GateInheritanceError`. Gate con khai `on_block` không có `confirms` là siết chặt — được.

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — `confirms` là tuỳ chọn |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có, đúng một loại: `on_block` có `confirms` với `ask`. Nới lỏng lược đồ, làm được trong `v1` |
| Cần tăng phiên bản lược đồ? | Không |
| Ảnh hưởng tới mã băm gate đã phát hành? | Không — gate không có `confirms` băm như cũ |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không |

## 5. Ảnh hưởng an toàn

- Không gate nào lỏng hơn nếu không tự khai `confirms`: mặc định `ask` chỉ thông báo.
- Người viết gate quyết định **trước** điều gì được xác nhận; người dùng không thể xác nhận
  vượt `call_source`, xác thực, hay giới hạn tham số trừ khi gate liệt kê chúng.
- Mô hình và client MCP không có đường nào xác nhận: không có tool xác nhận, và
  `ConfirmationBook` từ chối mọi nguồn ngoài `HUMAN_SOURCES` (có test).
- Kế thừa chỉ thu hẹp `confirms` (có corpus phản chứng).

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Xác nhận thay đúng tiêu chí vừa chặn (không đổi lược đồ) | Một lời "có" vượt được bất kỳ tiêu chí nào, kể cả "khách chưa xác thực" — điều người viết gate không hề cho phép |
| Thêm HOẶC (`any_of`) vào `allow_when` | Phải viết lại chứng minh "con chặt hơn cha" cho biểu thức có HOẶC, walker C phức tạp hơn; lớn hơn nhu cầu |
| Dữ kiện `human_confirmed` + `allow_when` hiện tại | Không diễn đạt được (§1) |

## 7. Bằng chứng kiểm chứng

- [x] Hợp lệ: `fixtures/gates/valid/narrows_confirms.yaml` (thu hẹp `fixtures/gates/registry/ask-base@1.0.0.yaml`)
- [x] Phản chứng + `expected_errors.yaml`: `widens_confirms`, `introduces_confirms`, `confirms_without_ask`, `confirms_unknown_criterion`
- [x] `python/tests/test_tool_confirm.py`: xác nhận thật tắt đèn qua gate; chỉ `local_grammar`/`ui`; dùng một lần; hết hạn; gate đổi ⇒ vô hiệu; chỉ thay tiêu chí được khai; không hỏi khi "có" không đủ; adjudicator suy giảm vẫn chặn; replay ra cùng phán quyết
- [x] `neuroedge verify` vẫn xanh; ba vết ghi chuẩn mực không đổi

## 8. Việc phải làm khi chấp thuận

- [x] `schemas/gate.v1.json`
- [x] Phụ lục B.3 trong `neuroedge-proposal.md`; `docs/spec/tool_calling.md` §6
- [x] `neuroedge-prd.md` Q-26, FR-ACE-10 · `neuroedge-roadmap.md` TSK-S3-26
- [x] Resolver, walker Python (`waived`), engine (`confirmed`), `c.do()`/`c.confirm()`, REPL, UI, `gate explain`, replay
- [ ] Walker C (TSK-S4-02) nhận tập tiêu chí được thay — bố cục nhị phân RFC-0003 mang `confirms`
