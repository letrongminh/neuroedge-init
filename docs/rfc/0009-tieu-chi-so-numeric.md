# RFC-0009: Tiêu chí số `evaluate.type: numeric` trong `gate.v1`

| | |
|:---|:---|
| **Mã RFC** | 0009 |
| **Tiêu đề** | Tiêu chí `numeric` — so sánh với ngưỡng, có đơn vị, kế thừa chỉ thu hẹp, nút mới trong `NETR` |
| **Hợp đồng bị ảnh hưởng** | `gate.v1` (thêm giá trị enum và trường tuỳ chọn) · ngữ nghĩa phân giải · bố cục `NETR` |
| **Yêu cầu PRD liên quan** | FR-GATE-03, FR-GATE-06, FR-ACE-01, FR-HAL-01 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-09-30 |
| **Trạng thái** | ⏳ Nháp — chưa mở PR · câu hỏi mở đã quyết (§9, Q-57) |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (chạm `gate.v1`, ngữ nghĩa phân giải, `NETR`) |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3 — sửa `schemas/*.json`, sửa ngữ nghĩa phân giải gate
> (`engine/gate_resolver.py`, `engine/constraints.py`), đổi bố cục `NETR`. Task: TSK-W1-02.
> Nguồn: `TODOS.md` #30; `roadmap/draft-ke-hoach-mo-rong-robot-fofoca.md` Phụ lục A.3. Bối cảnh:
> `neuroedge-prd.md` §15 Q-52, Q-54 (RFC-0012 dựa vào tiêu chí này để khoá ngưỡng độ tin cậy), Q-55.

## 1. Vấn đề

Gate không diễn đạt được ngưỡng số. Người viết gate cho máy nén khí muốn *"áp suất < 8 bar"* thì hôm nay phải thoả hiệp:

```yaml
# gate hiện tại — ngưỡng nằm ở nơi khác
evaluate:
  pressure_ok:
    type: bool
    instructions: "Áp suất dưới ngưỡng cho phép"
allow_when:
  pressure_ok: true
```

`pressure_ok` do agent tính. Cách vòng hiện có là `bands` ở `[sim.sensor_facts]` (`docs/spec/simulation_coverage.md`) đổi số đọc thành fact `level`. Nhưng **ngưỡng nằm ở agent, không ở gate**: gate chia sẻ qua registry không khoá được nó, và tác giả agent đổi `bands` là nới lỏng gate mà `neuroedge gate lint` không thấy — cùng lý do Q-25 bác `argument_facts` ở [RFC-0005](0005-rang-buoc-tham-so-trong-gate.md) §6.

## 2. Vì sao lược đồ hiện tại không giải quyết được

- `schemas/gate.v1.json`, `evaluate.*.type`: `"enum": ["bool", "level", "choice"]`, cùng `additionalProperties: false` — không có kiểu số và không có chỗ khai đơn vị hay thang.
- `RFC-0005` chỉ giới hạn **tham số của lời gọi**; số đọc từ cảm biến/camera là **dữ kiện của tiêu chí**, không phải tham số.
- `confidence_gte` (`engine/constraints.py`, `BOOL_OPERATORS`) chỉ áp cho tiêu chí `bool` và luôn nằm trong `[0, 1]`; nó nói về độ tin cậy của một dữ kiện, không phải về giá trị đo.
- Cây quyết định trên thiết bị chỉ biết chỉ số trong miền hữu hạn (`admitted_mask`, RFC-0003); không có nút so sánh số thực.

## 3. Thay đổi đề xuất

### 3a. Lược đồ

`evaluate.<tên>` nhận `type: numeric` kèm hai trường **bắt buộc**:

```yaml
evaluate:
  line_pressure:
    type: numeric
    unit: bar                       # nhãn, không quy đổi
    range: { min: 0, max: 16 }      # thang hợp lệ của số đọc
    instructions: "Áp suất đường ống sau van giảm áp"
allow_when:
  line_pressure: { lt: 8 }
```

Toán tử trong `allow_when`: `gt`, `gte`, `lt`, `lte`, kết hợp được để tạo khoảng (`{ gte: 2, lt: 8 }`). **Không có `eq`** trên số thực. Ngưỡng phải nằm trong `range`; khoảng rỗng ⇒ `GateSchemaError` (gate không bao giờ cho qua được là gate viết sai, như RFC-0005). `levels`/`options` bị cấm với `numeric`, dùng `allOf` `if/then` giống ba kiểu hiện có. Đơn vị là nhãn để người đọc, `mcp tools` và trace; engine **không đổi đơn vị**.

### 3b. Kế thừa (Phụ lục B.5, nguyên tắc 2)

Tiêu chí số admit một **khoảng**. Gate con chỉ được thu hẹp: khoảng của con phải là **tập con** khoảng của cha (biên mở/đóng được tính: cha `gte: 2` cho phép con `gt: 2` hoặc `gte: 3`, không cho `gte: 1`).

| Ràng buộc | Con được phép |
|:---|:---|
| Cận dưới (`gt`/`gte`) | Tăng, hoặc cùng giá trị với biên chặt hơn |
| Cận trên (`lt`/`lte`) | Giảm, hoặc cùng giá trị với biên chặt hơn |
| `unit` | Giữ nguyên (đổi đơn vị là đổi nghĩa ngưỡng) |
| `range` | Giữ nguyên; thu hẹp `range` không thu hẹp phán quyết nên không được dùng để thu hẹp |
| Không nhắc lại tiêu chí | Kế thừa nguyên vẹn, như `allow_when` |

Cha có cận mà con bỏ cận đó ⇒ nới lỏng ⇒ `GateInheritanceError` (`NE2003`, nguyên tắc 2).

### 3c. Lượng giá và fail-closed

Số đọc tới engine là số hữu hạn kèm mốc thời gian. **Thiếu, NaN, ±inf, hoặc ngoài `range`** ⇒ tiêu chí không khả dụng ⇒ `criterion_unavailable` ⇒ BLOCK (cùng lý do như "độ tin cậy không phải xác suất" trong RFC-0003). Không có giá trị mặc định thay thế. Không cắt số ra biên `range` rồi so.

### 3d. `NETR` và walker C

Bản ghi tiêu chí 24 byte của RFC-0003 không đủ chỗ cho bốn số thực (`lo`, `hi`, và thang `min`, `max`) cộng cờ biên. Đề xuất: `kind = 3` (numeric) và một bảng `numeric` mới (bản ghi cố định, tham chiếu từ nút), header thêm `numeric_count` ⇒ `header_size` đổi ⇒ **`layout_version` 2**. Walker v1 từ chối v2 (`NE_ERR_VERSION`, RFC-0003 §4), nên phải chọn thời điểm bump **một lần**: gộp với `TODOS.md` #36 (nhãn gate và chữ `on_block`) và các thay đổi bố cục của RFC-0011. Fact số tới walker là `f64` thay cho chỉ số trong miền; so sánh chỉ dùng `>`/`>=`/`<`/`<=` trên `f64` sau khi kiểm hữu hạn và trong `range`. Bố cục byte chính xác được ghim ở PR thứ hai trước khi viết walker.

### 3e. Compiler, công cụ và corpus

`neuroedge build` sinh nút; `gate explain` in ngưỡng kèm đơn vị; `input_schema()`/`mcp tools` không đổi (đây là fact, không phải tham số). Corpus ở `fixtures/gates/` theo luật khép kín (`CONTRIBUTING.md` §3).

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — `numeric` là giá trị enum mới, ba kiểu cũ giữ nguyên |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có, đúng một loại: gate có `type: numeric` (nới lỏng lược đồ, làm được trong `v1`, như RFC-0005) |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không cho `gate.v1`. **Có** cho bố cục `NETR`: `layout_version` 2 (§3d) |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không — gate không dùng `numeric` băm y như cũ |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào. Gate mới có `numeric` vào `digests.lock` bằng PR thường |
| Bố cục `NETR` hoặc walker C phải đổi? | **Có** — `kind = 3`, bảng `numeric`, `layout_version` 2; `engine/binary_tree.py` ↔ `targets/esp32s3/components/ne_gate/` |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không |

Firmware đã nạp cây v1 phải được build lại cùng cây v2; theo RFC-0003 §4 walker v1 từ chối v2 nên lệch phiên bản là lỗi nạp rõ ràng, không phải phán quyết sai.

## 5. Ảnh hưởng an toàn

- **Lỏng hơn ở đâu?** Không có đường nào: `numeric` thêm khả năng *diễn đạt* ngưỡng, và ngữ nghĩa kế thừa chỉ thu hẹp. Phần "nới lỏng" duy nhất là nới lược đồ, không nới phán quyết.
- **Nguyên tắc 2** được mở rộng cho khoảng số; lỗi biên mở/đóng (con `gte` khi cha `gt`) là chỗ dễ sai nhất — test đột biến bắt buộc (§7).
- **Fail-closed** giữ nguyên: mất cảm biến, NaN, ngoài thang đều BLOCK, không suy diễn.
- **Nợ được trả:** ngưỡng số hôm nay nằm ở agent (`bands`); sau RFC này nó nằm ở gate và được `gate lint` cưỡng chế. `[sim.sensor_facts]` vẫn dùng được nhưng không còn là cách duy nhất.
- Số thực dấu phẩy động: so sánh `f64` tất định trên host và MCU; không dùng dung sai ẩn. Đầu vào từ ADC/cảm biến đã đổi sang đơn vị khai trước khi tới gate (`analog.in`, [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md)).

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Giữ `bands` ở agent | Ngưỡng ngoài gate, tác giả agent nới được mà `lint` không thấy (§1) |
| Biểu thức CEL trên số đọc | Không chứng minh được "con chặt hơn" giữa hai biểu thức; MCU không có CEL (Q-9) |
| `eq` trên số thực | So sánh bằng phẳng trên `f64` không có nghĩa đo lường; dùng khoảng hẹp |
| Chỉ `level` với dải cố định | Không mang đơn vị, ngưỡng thành nhãn; vẫn là `bands` |
| Đẩy sang `gate.v2` | Không có tệp hợp lệ nào vỡ; `v2` vô ích (cùng lập luận RFC-0002 §4) |

## 7. Bằng chứng kiểm chứng

- [ ] Ví dụ hợp lệ trong `fixtures/gates/valid/`: gate `numeric`, gate con thu hẹp cận dưới/trên/biên mở
- [ ] Phản chứng trong `fixtures/gates/invalid/` + `expected_errors.yaml`: nới cận, đổi `unit`, bỏ cận cha, khoảng rỗng, ngưỡng ngoài `range`, `eq`, `levels` đi kèm `numeric`
- [ ] Trace/engine: số đọc NaN, thiếu, ngoài `range` ⇒ BLOCK `criterion_unavailable`
- [ ] Walker C khớp engine host trên mọi gate (mở rộng `python/tests/test_c_walker.py`), gồm ca biên `x == ngưỡng`; kiểm tra đột biến (đảo `<`/`<=`, bỏ kiểm NaN, bỏ kiểm `range`)
- [ ] `neuroedge gate lint` và `neuroedge verify` vẫn xanh; `scripts/check_digests.py` không đổi digest gate đã khoá

## 8. Việc phải làm khi chấp thuận

- [ ] Cập nhật `schemas/gate.v1.json` (enum `type`, `unit`, `range`, nhánh `if/then`)
- [ ] Cập nhật Phụ lục B.2/B.5 trong `neuroedge-proposal.md`; FR-GATE-03 ở `neuroedge-prd.md`; quyết định mới cấp `Q-N`
- [ ] Cập nhật `neuroedge-roadmap.md` (TSK-W1-02) và đóng `TODOS.md` #30
- [ ] `engine/constraints.py`, `engine/gate_resolver.py`, `engine/binary_tree.py`, walker C, `gate explain`
- [ ] Điều phối với RFC-0011 và `TODOS.md` #36 để `layout_version` chỉ tăng một lần
- [ ] Thêm fixture và test; cập nhật `docs/rfc/README.md` và `CHANGELOG.md`

## 9. Quyết định cho các câu hỏi mở (Q-57, 2026-09-30)

Chủ sản phẩm uỷ quyền quyết các câu hỏi mở theo nguyên tắc **an toàn cao nhất**: giữa hai phương án, chọn phương án fail-closed và khó dùng sai hơn, kể cả khi nó tốn công hơn. Mục này **thay** mọi đoạn đề xuất trái với nó ở §3; khi mở PR RFC, gộp nội dung vào §3. Chấp thuận RFC vẫn cần chữ ký kỹ thuật trưởng (`CONTRIBUTING.md` §3).

1. **Lý do lỗi.** Thêm lý do riêng `value_out_of_range` (số đọc ngoài `range`, NaN, ±inf); `criterion_unavailable` giữ cho trường hợp không có số đọc. Cả hai đều BLOCK. *Vì sao:* hậu kiểm phân biệt được "mất cảm biến" với "cảm biến trả rác", phán quyết không đổi.
2. **Bố cục `NETR`.** Tăng `layout_version` lên 2 **một lần**, trong một PR gồm bảng `numeric` của RFC này, các trường của RFC-0011 và `TODOS.md` #36; engine host và walker C đổi trong cùng PR; walker v1 từ chối cây v2 (fail-closed). *Vì sao:* không bao giờ có giai đoạn host và chip đọc cùng cây theo hai nghĩa.
3. **Độ tin cậy.** Tiêu chí `numeric` không có trường `confidence`; độ tin cậy, khi cần, là **một tiêu chí `numeric` khác** (đường của RFC-0012). *Vì sao:* một đường duy nhất, khoá được bằng `gate lint`.
4. **`range` bắt buộc.** *Vì sao:* không có thang thì không phát hiện được giá trị vô lý, fail-closed mất cạnh.
5. **Tuổi số đọc (thêm mới).** `max_age_ms` **bắt buộc** với mọi tiêu chí `numeric`; số đọc cũ hơn ⇒ `criterion_unavailable` ⇒ BLOCK. Mốc thời gian lấy từ lúc HAL đọc, được ghi vào vết ghi để `replay` tính lại đúng như lúc chạy. *Vì sao:* một cảm biến treo trả mãi giá trị cuối cùng trông như "an toàn"; gate phải từ chối số đọc đã cũ.
6. **So sánh số thực.** Ngưỡng, `range` và số đọc là `f64` hữu hạn; host và walker C dùng đúng bốn phép `>`, `>=`, `<`, `<=`, không dung sai ẩn; vector tuân thủ có ca đúng bằng ngưỡng ở mọi biên.
