# RFC-0009: Tiêu chí số `evaluate.type: numeric` trong `gate.v1`

| | |
|:---|:---|
| **Mã RFC** | 0009 |
| **Tiêu đề** | Tiêu chí `numeric` — so sánh với ngưỡng, có đơn vị, thang và tuổi số đọc bắt buộc, kế thừa chỉ thu hẹp, nút mới trong `NETR` |
| **Hợp đồng bị ảnh hưởng** | `gate.v1` (thêm giá trị enum và trường) · ngữ nghĩa phân giải · bố cục `NETR` · lý do phán quyết mới `value_out_of_range` |
| **Yêu cầu PRD liên quan** | FR-GATE-03, FR-GATE-06, FR-ACE-01, FR-HAL-01 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-09-30 |
| **Trạng thái** | ⏳ Nháp — chưa mở PR · câu hỏi mở đã quyết và đã gộp vào §3–§8 (§9, Q-57) |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (chạm `gate.v1`, ngữ nghĩa phân giải, `NETR`) |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3 — sửa `schemas/*.json`, sửa ngữ nghĩa phân giải gate
> (`engine/gate_resolver.py`, `engine/constraints.py`), đổi bố cục `NETR`. Task: TSK-W1-02.
> Nguồn: `TODOS.md` #30; bản nháp robot FOFOCA (`roadmap/draft-ke-hoach-mo-rong-robot-fofoca.md`), nay rút về RFC này. Bối cảnh:
> `neuroedge-prd.md` §15 Q-52, Q-54 (RFC-0012 dựa vào tiêu chí này để khoá ngưỡng độ tin cậy), Q-55, Q-57.

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

`pressure_ok` do agent tính. Cách vòng hiện có là `bands` ở `[sim.sensor_facts]` (`docs/spec/simulation_coverage.md`) đổi số đọc thành fact `level`. Nhưng **ngưỡng nằm ở agent, không ở gate**: gate chia sẻ qua registry không khoá được nó, và tác giả agent đổi `bands` là nới lỏng gate mà `neuroedge gate lint` không thấy — cùng lý do Q-25 bác `argument_facts` ở [RFC-0005](0005-rang-buoc-tham-so-trong-gate.md) §6. Vì vậy thị giác không có `bands`: số đếm và độ tin cậy là tiêu chí `numeric` của gate ([RFC-0012](0012-nguyen-thuy-vision-in.md) §9.2).

## 2. Vì sao lược đồ hiện tại không giải quyết được

- `schemas/gate.v1.json`, `evaluate.*.type`: `"enum": ["bool", "level", "choice"]`, cùng `additionalProperties: false` — không có kiểu số và không có chỗ khai đơn vị, thang hay tuổi số đọc.
- `RFC-0005` chỉ giới hạn **tham số của lời gọi**; số đọc từ cảm biến/camera là **dữ kiện của tiêu chí**, không phải tham số.
- `confidence_gte` (`engine/constraints.py`, `BOOL_OPERATORS`) chỉ áp cho tiêu chí `bool` và luôn nằm trong `[0, 1]`; nó nói về độ tin cậy của một dữ kiện, không phải về giá trị đo.
- Cây quyết định trên thiết bị chỉ biết chỉ số trong miền hữu hạn (`admitted_mask`, RFC-0003); không có nút so sánh số thực.

## 3. Thay đổi đề xuất

### 3a. Lược đồ

`evaluate.<tên>` nhận `type: numeric` kèm ba trường **bắt buộc** (§9.4, §9.5):

```yaml
evaluate:
  line_pressure:
    type: numeric
    unit: bar                       # nhãn, không quy đổi
    range: { min: 0, max: 16 }      # thang hợp lệ của số đọc
    max_age_ms: 500                 # số đọc cũ hơn ⇒ BLOCK
    instructions: "Áp suất đường ống sau van giảm áp"
allow_when:
  line_pressure: { lt: 8 }
```

| Trường | Luật |
|:---|:---|
| `unit` | Bắt buộc; nhãn để người đọc, `mcp tools` và trace; engine **không đổi đơn vị** |
| `range` | Bắt buộc; `min`, `max` là `f64` hữu hạn, `min < max`; số đọc hợp lệ khi `min ≤ x ≤ max` |
| `max_age_ms` | Bắt buộc; số nguyên > 0; tuổi số đọc tính từ mốc HAL đọc (§3c) |
| `confidence` | **Không có** — độ tin cậy là một tiêu chí `numeric` khác (§9.3) |
| `levels` / `options` | Cấm với `numeric`, dùng `allOf` `if/then` giống ba kiểu hiện có |

Toán tử trong `allow_when`: `gt`, `gte`, `lt`, `lte`, kết hợp được để tạo khoảng (`{ gte: 2, lt: 8 }`). **Không có `eq`** trên số thực, **không có `confidence_gte`** trên tiêu chí `numeric` (`GateSchemaError`, `NE2002`). Ngưỡng là `f64` hữu hạn và phải nằm trong `range`; khoảng rỗng ⇒ `GateSchemaError` (gate không bao giờ cho qua được là gate viết sai, như RFC-0005).

Độ tin cậy và số đếm của thị giác đi cùng đường ([RFC-0012](0012-nguyen-thuy-vision-in.md) §9.2–9.3): `confidence` là `numeric` với `range: { min: 0, max: 1 }`, `count` là `numeric` số nguyên ≥ 0 (vẫn so như `f64`, không có kiểu nguyên riêng). Cùng ba trường bắt buộc:

```yaml
evaluate:
  person_confidence:
    type: numeric
    unit: ratio
    range: { min: 0, max: 1 }
    max_age_ms: 300
    instructions: "Điểm tin cậy của nhãn person"
allow_when:
  person_confidence: { gte: 0.85 }
```

### 3b. Kế thừa (Phụ lục B.5, nguyên tắc 2)

Tiêu chí số admit một **khoảng**. Gate con chỉ được thu hẹp: khoảng của con phải là **tập con** khoảng của cha (biên mở/đóng được tính: cha `gte: 2` cho phép con `gt: 2` hoặc `gte: 3`, không cho `gte: 1`).

| Ràng buộc | Con được phép |
|:---|:---|
| Cận dưới (`gt`/`gte`) | Tăng, hoặc cùng giá trị với biên chặt hơn |
| Cận trên (`lt`/`lte`) | Giảm, hoặc cùng giá trị với biên chặt hơn |
| `unit` | Giữ nguyên (đổi đơn vị là đổi nghĩa ngưỡng) |
| `range` | Giữ nguyên; thu hẹp `range` không thu hẹp phán quyết nên không được dùng để thu hẹp |
| `max_age_ms` | Giữ nguyên |
| Không nhắc lại tiêu chí | Kế thừa nguyên vẹn, như `allow_when` |

`unit`, `range`, `max_age_ms` nằm trong `evaluate`: con khai lại khác cha là định nghĩa lại tiêu chí kế thừa, đã bị từ chối hôm nay (`GateInheritanceError`, `NE2003`, nguyên tắc 1 — `_merge_evaluate` ở `engine/gate_resolver.py`). Cha có cận mà con bỏ cận đó ⇒ nới lỏng ⇒ `GateInheritanceError` (`NE2003`, nguyên tắc 2).

### 3c. Lượng giá và fail-closed

Số đọc tới engine là `f64` kèm mốc thời gian HAL đọc; mốc này được ghi vào vết ghi để `replay` tính lại tuổi đúng như lúc chạy (§9.5). Tuổi = thời điểm lượng giá − mốc HAL đọc. Kiểm theo thứ tự, mọi nhánh đều BLOCK:

| Tình huống | `reason` |
|:---|:---|
| Không có số đọc (mất cảm biến, nguồn không trả lời) | `criterion_unavailable` |
| Tuổi > `max_age_ms` | `criterion_unavailable` |
| NaN, ±inf, hoặc ngoài `range` | `value_out_of_range` |
| Hữu hạn, trong `range`, không thoả khoảng của `allow_when` | `condition_not_met` |

Không có giá trị mặc định thay thế, không nội suy từ số đọc trước, không cắt số ra biên `range` rồi so (cùng tinh thần "độ tin cậy không phải xác suất ⇒ không khả dụng" của RFC-0003). Tách `value_out_of_range` khỏi `criterion_unavailable` để hậu kiểm phân biệt "mất cảm biến" với "cảm biến trả rác"; phán quyết không đổi (§9.1).

### 3d. `NETR` và walker C

Bản ghi tiêu chí 24 byte của RFC-0003 không đủ chỗ cho bốn số thực (`lo`, `hi`, và thang `min`, `max`) cộng cờ biên và `max_age_ms`. Đề xuất: `kind = 3` (numeric) và một bảng `numeric` mới (bản ghi cố định, tham chiếu từ nút), header thêm `numeric_count` ⇒ `header_size` đổi ⇒ **`layout_version` 2**. `layout_version` tăng **một lần**, trong **một PR** gồm bảng `numeric` của RFC này, các trường của RFC-0011 và `TODOS.md` #36 (nhãn gate và chữ `on_block`); engine host (`engine/binary_tree.py`) và walker C đổi trong cùng PR; walker v1 từ chối cây v2 (`NE_ERR_VERSION`, RFC-0003 §4) — fail-closed (§9.2). Fact số tới walker là `f64` kèm tuổi số đọc thay cho chỉ số trong miền; walker kiểm theo đúng thứ tự §3c và so sánh chỉ dùng `>`/`>=`/`<`/`<=` trên `f64`, không dung sai ẩn (§9.6). `ne_reason` (`ne_walker.h`) và `firmware.REASONS` thêm `value_out_of_range`. Bố cục byte chính xác được ghim ở PR thứ hai trước khi viết walker.

### 3e. Compiler, công cụ và corpus

`neuroedge build` sinh nút; `gate explain` in ngưỡng kèm đơn vị, `range` và `max_age_ms`; `input_schema()`/`mcp tools` không đổi (đây là fact, không phải tham số). Màn hình thiết bị có nhãn cho lý do mới (`ne_ui_strings.c`, `docs/spec/ui.md`). Corpus ở `fixtures/gates/` theo luật khép kín (`CONTRIBUTING.md` §3).

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — `numeric` là giá trị enum mới, ba kiểu cũ giữ nguyên |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có, đúng một loại: gate có `type: numeric` đủ `unit`, `range`, `max_age_ms` (nới lỏng lược đồ, làm được trong `v1`, như RFC-0005) |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không cho `gate.v1`. **Có** cho bố cục `NETR`: `layout_version` 2, một lần (§3d) |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không — gate không dùng `numeric` băm y như cũ |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không. `trace.v1` không đổi (`events[].data` đã mở); mốc HAL đọc của số đọc `numeric` là dữ liệu sự kiện mới, mô tả ở `docs/spec/simulation_coverage.md` §4 |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào. Gate mới có `numeric` vào `digests.lock` bằng PR thường |
| Bố cục `NETR` hoặc walker C phải đổi? | **Có** — `kind = 3`, bảng `numeric`, `layout_version` 2, `ne_reason` thêm `value_out_of_range`; `engine/binary_tree.py` ↔ `targets/esp32s3/components/ne_gate/` |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không |

Firmware đã nạp cây v1 phải được build lại cùng cây v2; theo RFC-0003 §4 walker v1 từ chối v2 nên lệch phiên bản là lỗi nạp rõ ràng, không phải phán quyết sai.

**Mã lỗi** (`neuroedge-prd.md` Phụ lục B): RFC này chỉ dùng `GateSchemaError` (`NE2002`) và `GateInheritanceError` (`NE2003`), cả hai đã có, nguyên nhân đã bao phủ. `value_out_of_range` là **lý do phán quyết**, không phải exception: thêm vào `Reason` (`engine/verdict.py`), `firmware.REASONS`/`ne_reason` và bảng lý do ở `docs/spec/ui.md` (sáu thành bảy); Phụ lục B không thêm dòng.

## 5. Ảnh hưởng an toàn

- **Lỏng hơn ở đâu?** Không có đường nào: `numeric` thêm khả năng *diễn đạt* ngưỡng, và ngữ nghĩa kế thừa chỉ thu hẹp. Phần "nới lỏng" duy nhất là nới lược đồ, không nới phán quyết.
- **Nguyên tắc 2** được mở rộng cho khoảng số; lỗi biên mở/đóng (con `gte` khi cha `gt`) là chỗ dễ sai nhất — test đột biến bắt buộc (§7).
- **Fail-closed** giữ nguyên và chặt hơn: mất cảm biến, số đọc quá `max_age_ms`, NaN, ±inf, ngoài thang đều BLOCK, không suy diễn. `range` và `max_age_ms` bắt buộc: không có thang thì không phát hiện được giá trị vô lý; cảm biến treo trả mãi giá trị cuối cùng trông như "an toàn" (§9.4, §9.5).
- **Một đường cho độ tin cậy:** tiêu chí `numeric` không mang `confidence`; độ tin cậy là tiêu chí `numeric` riêng, khoá được bằng `gate lint` (§9.3, RFC-0012).
- **Nợ được trả:** ngưỡng số hôm nay nằm ở agent (`bands`); sau RFC này nó nằm ở gate và được `gate lint` cưỡng chế. `[sim.sensor_facts]` không đổi trong RFC này, nhưng không còn là cách duy nhất; thị giác không có `bands` (RFC-0012 §9.2).
- **Số thực dấu phẩy động:** ngưỡng, `range` và số đọc là `f64` hữu hạn; so sánh tất định trên host và MCU bằng đúng bốn phép, không dung sai ẩn (§9.6). Đầu vào từ ADC/cảm biến đã đổi sang đơn vị khai trước khi tới gate (`analog.in`, [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md)).
- **Host và chip không bao giờ đọc cùng cây theo hai nghĩa:** `layout_version` 2 đổi host và walker trong cùng PR (§9.2).

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Giữ `bands` ở agent | Ngưỡng ngoài gate, tác giả agent nới được mà `lint` không thấy (§1) |
| Biểu thức CEL trên số đọc | Không chứng minh được "con chặt hơn" giữa hai biểu thức; MCU không có CEL (Q-9) |
| `eq` trên số thực | So sánh bằng phẳng trên `f64` không có nghĩa đo lường; dùng khoảng hẹp |
| So sánh có dung sai (epsilon) | Dung sai ẩn làm biên khác nhau giữa host và MCU; chỉ bốn phép `>`/`>=`/`<`/`<=` (§9.6) |
| Chỉ `level` với dải cố định | Không mang đơn vị, ngưỡng thành nhãn; vẫn là `bands` |
| `range` tuỳ chọn | Không có thang thì không phát hiện được giá trị vô lý (§9.4) |
| Không giới hạn tuổi số đọc / `max_age_ms` tuỳ chọn | Cảm biến treo trả mãi giá trị cuối trông như "an toàn" (§9.5) |
| Ngoài `range`/NaN báo `criterion_unavailable` | Hậu kiểm không phân biệt được mất cảm biến với cảm biến trả rác (§9.1) |
| Trường `confidence` trên tiêu chí `numeric` | Hai đường cho độ tin cậy thì một đường sẽ bị quên khoá (§9.3) |
| Tăng `layout_version` riêng cho từng RFC | Nhiều lần vỡ tương thích firmware; có giai đoạn host và chip đọc cây khác nghĩa (§9.2) |
| Đẩy sang `gate.v2` | Không có tệp hợp lệ nào vỡ; `v2` vô ích (cùng lập luận RFC-0002 §4) |

## 7. Bằng chứng kiểm chứng

- [ ] Ví dụ hợp lệ trong `fixtures/gates/valid/`: gate `numeric` đủ `unit`/`range`/`max_age_ms`, gate con thu hẹp cận dưới/trên/biên mở, gate độ tin cậy `range: { min: 0, max: 1 }`
- [ ] Phản chứng trong `fixtures/gates/invalid/` + `expected_errors.yaml`: thiếu `unit`, thiếu `range`, thiếu `max_age_ms`, `max_age_ms` ≤ 0, `range` có `min ≥ max` hoặc không hữu hạn, ngưỡng không hữu hạn, ngưỡng ngoài `range`, khoảng rỗng, `eq`, `confidence_gte` trên `numeric`, trường `confidence`, `levels`/`options` đi kèm `numeric`; kế thừa: nới cận, bỏ cận cha, đổi `unit`, đổi `range`, đổi `max_age_ms`
- [ ] Engine: không có số đọc ⇒ BLOCK `criterion_unavailable`; tuổi > `max_age_ms` ⇒ BLOCK `criterion_unavailable` (ca biên tuổi đúng bằng `max_age_ms` cho qua); NaN, ±inf, ngoài `range` ⇒ BLOCK `value_out_of_range`; thứ tự kiểm theo §3c
- [ ] Replay: tuổi tính lại từ mốc HAL đọc trong vết ghi cho cùng phán quyết với lúc chạy
- [ ] Walker C khớp engine host trên mọi gate (mở rộng `python/tests/test_c_walker.py`), gồm ca đúng bằng ở mọi biên (ngưỡng, `range.min`, `range.max`, `max_age_ms`); kiểm tra đột biến (đảo `<`/`<=`, bỏ kiểm NaN, bỏ kiểm `range`, bỏ kiểm tuổi)
- [ ] Walker v1 từ chối cây v2 (`NE_ERR_VERSION`); `test_ui_assets.py` giữ `ne_reason` và `firmware.REASONS` khớp nhau sau khi thêm `value_out_of_range`
- [ ] `neuroedge gate lint` và `neuroedge verify` vẫn xanh; `scripts/check_digests.py` không đổi digest gate đã khoá

## 8. Việc phải làm khi chấp thuận

- [ ] Cập nhật `schemas/gate.v1.json` (enum `type`, `unit`, `range`, `max_age_ms` bắt buộc, nhánh `if/then`)
- [ ] Cập nhật Phụ lục B.2/B.5 trong `neuroedge-proposal.md`; FR-GATE-03 ở `neuroedge-prd.md`; ghi chấp thuận vào Q-57 (`neuroedge-prd.md` §15)
- [ ] Cập nhật `neuroedge-roadmap.md` (TSK-W1-02) và đóng `TODOS.md` #30
- [ ] `engine/constraints.py`, `engine/gate_resolver.py`, `engine/verdict.py` (`value_out_of_range`), `engine/binary_tree.py`, `engine/firmware.py` (`REASONS`), walker C (`ne_walker.h`), `gate explain`
- [ ] Ghi mốc HAL đọc vào vết ghi; cập nhật `docs/spec/simulation_coverage.md` §4 và bảng lý do ở `docs/spec/ui.md` (nhãn trong `ne_ui_strings.c`)
- [ ] Một PR duy nhất cho `layout_version` 2 cùng RFC-0011 và `TODOS.md` #36 (§3d)
- [ ] Thêm fixture và test; cập nhật `docs/rfc/README.md` và `CHANGELOG.md`

## 9. Quyết định cho các câu hỏi mở (Q-57, 2026-09-30)

Chủ sản phẩm uỷ quyền quyết các câu hỏi mở theo nguyên tắc **an toàn cao nhất**: giữa hai phương án, chọn phương án fail-closed và khó dùng sai hơn, kể cả khi nó tốn công hơn. Các quyết định dưới đây **đã được gộp vào §3–§8**; mục này giữ lại làm hồ sơ quyết định (Q-57). Chấp thuận RFC vẫn cần chữ ký kỹ thuật trưởng (`CONTRIBUTING.md` §3).

1. **Lý do lỗi.** Thêm lý do riêng `value_out_of_range` (số đọc ngoài `range`, NaN, ±inf); `criterion_unavailable` giữ cho trường hợp không có số đọc. Cả hai đều BLOCK. *Vì sao:* hậu kiểm phân biệt được "mất cảm biến" với "cảm biến trả rác", phán quyết không đổi.
2. **Bố cục `NETR`.** Tăng `layout_version` lên 2 **một lần**, trong một PR gồm bảng `numeric` của RFC này, các trường của RFC-0011 và `TODOS.md` #36; engine host và walker C đổi trong cùng PR; walker v1 từ chối cây v2 (fail-closed). *Vì sao:* không bao giờ có giai đoạn host và chip đọc cùng cây theo hai nghĩa.
3. **Độ tin cậy.** Tiêu chí `numeric` không có trường `confidence`; độ tin cậy, khi cần, là **một tiêu chí `numeric` khác** (đường của RFC-0012). *Vì sao:* một đường duy nhất, khoá được bằng `gate lint`.
4. **`range` bắt buộc.** *Vì sao:* không có thang thì không phát hiện được giá trị vô lý, fail-closed mất cạnh.
5. **Tuổi số đọc (thêm mới).** `max_age_ms` **bắt buộc** với mọi tiêu chí `numeric`; số đọc cũ hơn ⇒ `criterion_unavailable` ⇒ BLOCK. Mốc thời gian lấy từ lúc HAL đọc, được ghi vào vết ghi để `replay` tính lại đúng như lúc chạy. *Vì sao:* một cảm biến treo trả mãi giá trị cuối cùng trông như "an toàn"; gate phải từ chối số đọc đã cũ.
6. **So sánh số thực.** Ngưỡng, `range` và số đọc là `f64` hữu hạn; host và walker C dùng đúng bốn phép `>`, `>=`, `<`, `<=`, không dung sai ẩn; vector tuân thủ có ca đúng bằng ngưỡng ở mọi biên.
