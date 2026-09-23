# RFC-0005: Gate tự khai ràng buộc tham số của hành động

| | |
|:---|:---|
| **Mã RFC** | 0005 |
| **Tiêu đề** | Khối `arguments:` trong gate — ràng buộc tham số tool call, kế thừa chỉ thu hẹp |
| **Lược đồ bị ảnh hưởng** | `gate.v1` (thêm trường tuỳ chọn) · ngữ nghĩa phân giải · bố cục nhị phân Q-23 |
| **Yêu cầu PRD liên quan** | FR-ACE-08, FR-GATE-06, FR-MDL-10 |
| **Người đề xuất** | V1 — Kỹ sư lõi nền tảng *(theo quyết định Q-25)* |
| **Ngày mở** | 2026-09-23 |
| **Trạng thái** | 🟡 Đang thảo luận — hướng đã chốt ở Q-25, chi tiết chờ duyệt |
| **Người phê duyệt** | *(kỹ thuật trưởng — thay đổi `gate.v1` và ngữ nghĩa phân giải)* |

> **Khi nào cần RFC:** mọi thay đổi trong `schemas/`, và mọi thay đổi ngữ nghĩa
> phân giải gate. Xem `CONTRIBUTING.md` §3 để biết ranh giới chính xác.

## 1. Vấn đề

Từ Q-24, hành động đến từ LLM và client MCP, không chỉ từ câu lệnh đã soạn sẵn. Mô
hình chọn **cả tham số**. Gate hôm nay không thấy tham số:

```python
# System 2 bị prompt injection, hoặc đơn giản là nhầm
ToolCall("unlock_door", {"guest_id": "101", "duration_s": 3600}, source="system_two")
```

Gate `unlock_door@1.2.0` kiểm khách đã xác thực, phòng khớp — và cho qua. Cửa mở một
giờ. Không có cách nào viết *"không quá 60 giây"* trong gate.

## 2. Vì sao lược đồ hiện tại không giải quyết được

- `evaluate` chỉ có ba kiểu `bool` / `level` / `choice` (Phụ lục B.2), và mỗi tiêu chí là
  một **dữ kiện** do System 1 hoặc session cấp — không phải tham số của lời gọi.
- `gate.v1.json` đặt `additionalProperties: false` ở cấp cao, nên không có chỗ khai.
- Cách vòng qua là tính dữ kiện ở agent (`duration_ok = duration_s ≤ 60` trong
  `agent.toml`). Nhưng khi đó **ý nghĩa** của `duration_ok` nằm ngoài gate: tác giả agent
  viết `duration_ok = duration_s ≤ 3600` là nới lỏng một gate chia sẻ mà `gate lint`
  không thấy — trái với lời hứa trung tâm của `extends` (B.5). Q-25 bác bỏ cách này.

## 3. Thay đổi đề xuất

Thêm trường cấp cao tuỳ chọn `arguments`:

```yaml
schema:  neuroedge.gate/v1
name:    unlock_door
version: 1.3.0
arguments:                      # mới — ràng buộc trên tham số của @action
  duration_s: { type: integer, minimum: 1, maximum: 60 }
  guest_id:   { type: string, max_length: 16 }
evaluate: { ... }               # không đổi
allow_when: ...                 # không đổi
```

```json
"arguments": {
  "type": "object",
  "additionalProperties": {
    "type": "object",
    "required": ["type"],
    "properties": {
      "type":       { "enum": ["string", "integer", "number", "boolean"] },
      "minimum":    { "type": "number" },
      "maximum":    { "type": "number" },
      "enum":       { "type": "array", "minItems": 1 },
      "max_length": { "type": "integer", "minimum": 0 }
    },
    "additionalProperties": false
  }
}
```

**Lượng giá.** Ràng buộc tham số chạy **trước** `evaluate`, tất định, không tốn ngân
sách mô hình. Vi phạm ⇒ `BLOCK`, `reason = argument_out_of_range`,
`failed_criterion = <tên tham số>`, rồi `on_block` như mọi lần chặn. Tham số có trong
`arguments` mà `@action` không có ⇒ `neuroedge build` báo lỗi (gate và hành động lệch
nhau).

**Kế thừa (B.5).** Gate con chỉ được thu hẹp:

| Ràng buộc | Con được phép |
|:---|:---|
| `minimum` / `maximum` | Tăng / giảm (khoảng hiệu dụng là **giao** với cha) |
| `enum` | Tập con của cha |
| `max_length` | Nhỏ hơn hoặc bằng |
| `type` | Giữ nguyên |
| Bỏ ràng buộc cha đã khai | **Không** — `GateInheritanceError` |

Khoảng rỗng sau khi giao (`minimum > maximum`) ⇒ `GateSchemaError`: gate không bao giờ
cho qua được là gate viết sai.

**Compiler và MCU.** `neuroedge build` sinh các nút so sánh tham số đứng trước cây quyết
định. Bố cục nhị phân Q-23 thêm một loại nút (`ARG_CMP`: chỉ số tham số, phép so sánh,
hằng) và **tăng số phiên bản bố cục** — trước khi TSK-S4-02 viết walker C, nên không
thiết bị nào phải nạp lại.

**Tool schema.** `mcp tools` và `openai` đưa ràng buộc vào `inputSchema`
(`minimum`, `maximum`, `enum`, `maxLength`), để mô hình thấy giới hạn trước khi gọi
(`docs/spec/tool_calling.md` §3).

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — `arguments` là tuỳ chọn |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có, đúng một loại: gate có khối `arguments` (hôm nay bị `additionalProperties: false` từ chối). Là nới lỏng lược đồ, làm được trong `v1` |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không — gate không có `arguments` băm ra y như cũ |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không |

## 5. Ảnh hưởng an toàn

Thay đổi này chỉ thêm cách **chặn**; không có đường nào làm một gate lỏng hơn:

- Gate không có `arguments` giữ nguyên ngữ nghĩa.
- Kế thừa chỉ thu hẹp, và bỏ ràng buộc là lỗi — cùng hình dạng với Q-18 cho `budget`.
- Ràng buộc chạy tất định trước mô hình, nên không có lý do suy giảm mới
  (`gate_unreachable` / `budget_exceeded` không áp dụng).

Một điểm cần duyệt: tham số **không** khai trong `arguments` thì không bị giới hạn ngoài
kiểu của chữ ký. Có nên có chế độ `arguments_closed: true` buộc mọi tham số phải khai?
Đề xuất: **không** ở v1 — thêm sau nếu gate chia sẻ đầu tiên cần.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| `argument_facts` trong `agent.toml` (dữ kiện bool tính từ tham số) | Ý nghĩa an toàn nằm ngoài gate: tác giả agent nới lỏng được mà `lint` không thấy; gate chia sẻ qua registry không mang theo giới hạn (Q-25) |
| Biểu thức CEL trên tham số trong `allow_when` (`arguments.temp <= 30`) | Kế thừa không so sánh được hai biểu thức tuỳ ý để chứng minh "con chặt hơn"; MCU không có CEL (Q-9) |
| Chỉ dựa vào JSON Schema của tool | Là gợi ý cho mô hình, không phải cưỡng chế; client MCP bỏ qua được |

## 7. Bằng chứng kiểm chứng

- [ ] Ví dụ hợp lệ: `gates/unlock_door@1.3.0.yaml` có `duration_s ≤ 60`
- [ ] Phản chứng trong `fixtures/gates/invalid/` + `expected_errors.yaml`: con nới `maximum`, con bỏ ràng buộc, khoảng rỗng, enum không phải tập con
- [ ] Test: `ToolCall` với `duration_s = 3600` từ `system_two` ⇒ BLOCK `argument_out_of_range`, chân không đổi
- [ ] `neuroedge verify` vẫn xanh; ba vết ghi chuẩn mực không đổi

## 8. Việc phải làm khi chấp thuận

- [ ] Cập nhật `schemas/gate.v1.json`
- [ ] Phụ lục B.6 trong `neuroedge-proposal.md` từ "đề xuất" thành chuẩn tắc
- [ ] `neuroedge-prd.md` FR-ACE-08 từ P1 chờ RFC thành P0 nếu cần cho A2
- [ ] `neuroedge-roadmap.md` TSK-S3-25 · TSK-S4-02 (loại nút `ARG_CMP`)
- [ ] Resolver, lint, compiler, `input_schema()`; fixture và test
