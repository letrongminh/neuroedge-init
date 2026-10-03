# RFC-0009: Tiêu chí số `evaluate.type: numeric` trong `gate.v1`

| | |
|:---|:---|
| **Mã RFC** | 0009 |
| **Tiêu đề** | Tiêu chí `numeric` — so sánh với ngưỡng, có đơn vị, thang và tuổi số đọc bắt buộc, kế thừa chỉ thu hẹp, nút mới trong `NETR` |
| **Hợp đồng bị ảnh hưởng** | `gate.v1` (thêm giá trị enum và trường) · ngữ nghĩa phân giải · bố cục `NETR` · lý do phán quyết mới `value_out_of_range` |
| **Yêu cầu PRD liên quan** | FR-GATE-03, FR-GATE-06, FR-ACE-01, FR-HAL-01 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-09-30 |
| **Trạng thái** | ✅ Đã chấp thuận (2026-10-01) — kỹ thuật trưởng ký trên PR #76; sửa theo review 2026-10-01 (§9, Q-62) · ✅ Đã hiện thực (TSK-W1-02, 2026-10-03); nối kênh `analog.in` (TSK-I2a-04) và `state()` của PWM (RFC-0010) làm cùng các nguyên thủy đó |
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

Tiêu chí `numeric` **không được** nằm trong `on_block.confirms` của RFC-0006: `neuroedge gate lint` từ chối (`GateSchemaError`, `NE2002`). Người không thể xác nhận thay một giới hạn đo lường vật lý.

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

`unit`, `range`, `max_age_ms` nằm trong `evaluate`: con khai lại khác cha là định nghĩa lại tiêu chí kế thừa, đã bị từ chối hôm nay (`GateInheritanceError`, `NE2003`, nguyên tắc 1 — `_merge_evaluate` ở `engine/gate_resolver.py`); khai lại giống hệt cha hoặc không nhắc lại thì kế thừa nguyên vẹn. Khi ghi đè `allow_when`, nếu cha có cận mà con bỏ cận đó (ví dụ cha có cả cận dưới và cận trên, con chỉ ghi cận dưới khiến khoảng mở rộng) ⇒ nới lỏng điều kiện kế thừa vì khoảng của con không còn là tập con khoảng của cha ⇒ `GateInheritanceError` (`NE2003`, nguyên tắc 2 — `_merge_allow_when`). Nếu con không nhắc lại tiêu chí trong `allow_when`, mệnh đề của cha được kế thừa nguyên vẹn, không bị coi là bỏ cận.

### 3c. Lượng giá và fail-closed

Số đọc tới engine là `f64` kèm mốc thời gian HAL đọc. Thời điểm lượng giá là offset của sự kiện phán quyết trên cùng trục thời gian đơn điệu của phiên với mốc đọc của HAL. Tuổi `age_ms` = thời điểm lượng giá − mốc HAL đọc. Vết ghi ghi cả mốc đọc HAL lẫn `age_ms`; `replay` tính lại và so sánh. Với thị giác, tuổi của cửa sổ là tuổi của khung cũ nhất trong cửa sổ. Kiểm theo thứ tự, mọi nhánh đều BLOCK:

| Tình huống | `reason` |
|:---|:---|
| Không có số đọc (mất cảm biến, nguồn không trả lời) | `criterion_unavailable` |
| `age_ms < 0` (mốc HAL đọc sau thời điểm lượng giá) | `criterion_unavailable` |
| Tuổi (`age_ms`) > `max_age_ms` | `criterion_unavailable` |
| NaN, ±inf, hoặc ngoài `range` | `value_out_of_range` |
| Hữu hạn, trong `range`, không thoả khoảng của `allow_when` | `condition_not_met` |

Không có giá trị mặc định thay thế, không nội suy từ số đọc trước, không cắt số ra biên `range` rồi so (cùng tinh thần "độ tin cậy không phải xác suất ⇒ không khả dụng" của RFC-0003). Tách `value_out_of_range` khỏi `criterion_unavailable` để hậu kiểm phân biệt "mất cảm biến" với "cảm biến trả rác"; phán quyết không đổi (§9.1).

### 3d. `NETR` và walker C

Bản ghi tiêu chí 24 byte của RFC-0003 không đủ chỗ cho bốn số thực (`lo`, `hi`, và thang `min`, `max`) cộng cờ biên và `max_age_ms`. `layout_version` tăng **một lần** lên 2, trong **một PR** do TSK-W1-02 (RFC-0009) làm chủ. PR gồm bảng `numeric` cộng các trường của `TODOS.md` #36 (nhãn gate và chữ `on_block`). RFC-0011 **không** thêm trường nào vào `NETR`, chỉ đổi sổ token `ne_token.c`. Engine host (`engine/binary_tree.py`) và walker C đổi trong cùng PR; walker v1 từ chối cây v2 (`NE_ERR_VERSION`, RFC-0003 §4) — fail-closed (§9.2). Bố cục byte được ghim trực tiếp:

**Header — 80 byte** (offset 0–63 giữ nguyên định nghĩa của v1 trong RFC-0003, trừ `layout_version = 2` và `header_size = 80`; `crc32` ở offset 60 tính trên toàn tệp với 4 byte đó là 0):

| Offset | Kiểu | Trường | Quy định |
|---:|:---|:---|:---|
| 0 | `char[4]` | `magic` | `"NETR"` |
| 4 | `u16` | `layout_version` | `2` |
| 6 | `u16` | `header_size` | `80` |
| 8 | `u8[32]` | `gate_digest` | SHA-256 thô của gate đã phân giải |
| 40 | `u16` | `node_count` | 1..32 — tiêu chí `allow_when`, theo `criteria_order` |
| 42 | `u16` | `arg_count` | 0..16 — giới hạn tham số RFC-0005, theo thứ tự khai |
| 44 | `u16` | `enum_count` | 0..64 |
| 46 | `u8` | `on_block_action` | 0 deny · 1 escalate · 2 ask · 3 degrade |
| 47 | `u8` | `fail_open` | 0 closed · 1 open |
| 48 | `u32` | `p95_latency_ms` | > 0 |
| 52 | `u32` | `confirm_mask` | bit *i*: tiêu chí *i* người được xác nhận thay (RFC-0006) |
| 56 | `u32` | `strings_size` | 1..16384, byte cuối là NUL |
| 60 | `u32` | `crc32` | CRC-32 của toàn tệp với 4 byte này là 0 |
| 64 | `u16` | `numeric_count` | 0..32 — số lượng bản ghi trong bảng numeric |
| 66 | `u16` | `gate_name_off` | Offset tên gate trong bảng chuỗi; `0xFFFF` = không có |
| 68 | `u16` | `gate_version_off` | Offset phiên bản gate trong bảng chuỗi; `0xFFFF` = không có |
| 70 | `u16` | `on_block_to_off` | Offset đích chuyển tiếp `to` trong bảng chuỗi; `0xFFFF` = không có |
| 72 | `u16` | `on_block_message_off` | Offset thông điệp `message` trong bảng chuỗi; `0xFFFF` = không có |
| 74 | `u16` | `fallback_action_off` | Offset hành động dự phòng trong bảng chuỗi; `0xFFFF` = không có |
| 76 | `u32` | dành riêng | Bằng 0 |

**Node tiêu chí — 24 byte × `node_count`**

Với nút `kind = 3` (numeric):
- `domain_size = 0`
- `admitted_mask = 0`
- `confidence_floor = 0.0`
- `domain_off` = chỉ số trong bảng numeric (0..`numeric_count - 1`)
- Các byte còn lại bằng 0.

(Các nút `kind` 0 bool, 1 level, 2 choice giữ nguyên bố cục của RFC-0003).

**Bản ghi numeric — 48 byte × `numeric_count`**

| Offset | Kiểu | Trường | Quy định |
|---:|:---|:---|:---|
| 0 | `f64` | `lo` | Cận dưới; 0.0 nếu không có cận dưới |
| 8 | `f64` | `hi` | Cận trên; 0.0 nếu không có cận trên |
| 16 | `f64` | `range_min` | Giới hạn dưới của thang hợp lệ |
| 24 | `f64` | `range_max` | Giới hạn trên của thang hợp lệ (`range_min < range_max`) |
| 32 | `u32` | `max_age_ms` | Tuổi tối đa cho phép của số đọc (> 0) |
| 36 | `u16` | `unit_off` | Offset chuỗi đơn vị trong bảng chuỗi |
| 38 | `u8` | `flags` | Bit 0 (1): có cận dưới · Bit 1 (2): cận dưới đóng (`gte`) · Bit 2 (4): có cận trên · Bit 3 (8): cận trên đóng (`lte`) |
| 39 | `u8` | dành riêng | Bằng 0 |
| 40 | `u64` | dành riêng | Bằng 0 |

**Thứ tự các bảng và kích thước tệp:**
1. Header (80 byte)
2. Nút tiêu chí (24 byte × `node_count`)
3. Bản ghi numeric (48 byte × `numeric_count`)
4. Giới hạn tham số (32 byte × `arg_count`)
5. Enum (16 byte × `enum_count`)
6. Bảng chuỗi

Tổng kích thước = 80 + 24·n + 48·m + 32·a + 16·e + strings, **đúng bằng** độ dài tệp (như v1). `numeric_count` bằng đúng số nút `kind = 3`; mỗi nút một bản ghi riêng, không dùng chung. `confirm_mask` khác 0 chỉ khi `ask` (như v1) và không bao giờ chứa bit của nút `kind = 3`. `ne_tree_load` từ chối tệp vi phạm bất kỳ luật nào ở đây. Bảng numeric chiếm tối đa 48 byte × 32 = 1.536 byte (1,5 KB) flash.

**ABI walker C:**
Fact số tới walker là struct mang `u8 available` (0 = không có số đọc), `f64 value` và `i64 age_ms` (thay cho chỉ số trong miền hữu hạn). `available = 0` ⇒ `criterion_unavailable` trước mọi kiểm khác, nên walker không lẫn "mất cảm biến" với NaN (`value_out_of_range`). Walker kiểm theo đúng thứ tự §3c và so sánh chỉ dùng `>`/`>=`/`<`/`<=` trên `f64`, không dung sai ẩn (§9.6). `ne_reason` (`ne_walker.h`) và `firmware.REASONS` thêm `value_out_of_range`. Walker v1 từ chối cây v2 (`NE_ERR_VERSION`). Giới hạn stack của walker C giữ nguyên mức ≤ 512 byte (không đệ quy, không cấp phát động).

### 3e. Compiler, công cụ và corpus

`neuroedge build` sinh nút; `gate explain` in ngưỡng kèm đơn vị, `range` và `max_age_ms`; `input_schema()`/`mcp tools` không đổi (đây là fact, không phải tham số). Màn hình thiết bị có nhãn cho lý do mới (`ne_ui_strings.c`, `docs/spec/ui.md`). Corpus ở `fixtures/gates/` theo luật khép kín (`CONTRIBUTING.md` §3).

### 3f. Ràng buộc dữ kiện số với kênh HAL

Khi agent nối một tiêu chí `numeric` với một kênh HAL (`analog.in`, readback `feedback`; `sensor.read` hôm nay không khai `unit` và thang nên **không** nối được với tiêu chí `numeric` — nối ⇒ `BoardCapabilityError` (`NE3001`)), `neuroedge build` kiểm tra tĩnh:
1. `unit` của kênh phần cứng và `unit` của tiêu chí phải trùng nhau.
2. Thang đo `[min, max]` khai báo của kênh phải nằm hoàn toàn trong `range` của tiêu chí (`range.min ≤ channel.min` và `channel.max ≤ range.max`).

Lệch một trong hai điều kiện trên ⇒ `BoardCapabilityError` (`NE3001`).

Đối với tiêu chí nối với trạng thái chân số `digital.out(...).state()`, gate chỉ nhận giá trị có `source = measured` (số đọc đo thực tế từ mạch hồi tiếp). Giá trị `commanded` (trạng thái lệnh logic của phần mềm) gửi tới gate ⇒ coi như chưa có số đọc đo lường hợp lệ ⇒ BLOCK `criterion_unavailable`.

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — `numeric` là giá trị enum mới, ba kiểu cũ giữ nguyên |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có, đúng một loại: gate có `type: numeric` đủ `unit`, `range`, `max_age_ms` (nới lỏng lược đồ, làm được trong `v1`, như RFC-0005) |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không cho `gate.v1`. **Có** cho bố cục `NETR`: `layout_version` 2, một lần (§3d) |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không — gate không dùng `numeric` băm y như cũ |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không. `trace.v1` không đổi (`events[].data` đã mở); mốc HAL đọc và `age_ms` của số đọc `numeric` là dữ liệu sự kiện mới, mô tả ở `docs/spec/simulation_coverage.md` §4 |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào. Gate mới có `numeric` vào `digests.lock` bằng PR thường |
| Bố cục `NETR` hoặc walker C phải đổi? | **Có** — `kind = 3`, bảng `numeric`, `layout_version` 2, ABI fact `u8 available` + `f64 value` + `i64 age_ms`, `ne_reason` thêm `value_out_of_range`; `engine/binary_tree.py` ↔ `targets/esp32s3/components/ne_gate/` |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không |

Firmware đã nạp cây v1 phải được build lại cùng cây v2; theo RFC-0003 §4 walker v1 từ chối v2 nên lệch phiên bản là lỗi nạp rõ ràng, không phải phán quyết sai.

**Mã lỗi** (`neuroedge-prd.md` Phụ lục B): RFC này dùng `GateSchemaError` (`NE2002`) (sai cấu trúc, hoặc chứa tiêu chí `numeric` trong `on_block.confirms`), `GateInheritanceError` (`NE2003`) (vi phạm nguyên tắc kế thừa 1 trong `_merge_evaluate` hoặc nguyên tắc 2 trong `_merge_allow_when`), và `BoardCapabilityError` (`NE3001`) (`neuroedge build` phát hiện kênh HAL lệch `unit` hoặc `[min, max]` nằm ngoài `range`). `value_out_of_range` là **lý do phán quyết**, không phải exception: thêm vào `Reason` (`engine/verdict.py`), `firmware.REASONS`/`ne_reason` và bảng lý do ở `docs/spec/ui.md` (sáu thành bảy); Phụ lục B không thêm dòng.

## 5. Ảnh hưởng an toàn

- **Lỏng hơn ở đâu?** Không có đường nào: `numeric` thêm khả năng *diễn đạt* ngưỡng, và ngữ nghĩa kế thừa chỉ thu hẹp. Phần "nới lỏng" duy nhất là nới lược đồ, không nới phán quyết.
- **Nguyên tắc 2** được mở rộng cho khoảng số; lỗi biên mở/đóng (con `gte` khi cha `gt`) là chỗ dễ sai nhất — test đột biến bắt buộc (§7).
- **Fail-closed** giữ nguyên và chặt hơn: mất cảm biến, số đọc có mốc thời gian vi phạm nhân quả (`age_ms < 0`), số đọc quá `max_age_ms`, NaN, ±inf, ngoài thang đều BLOCK, không suy diễn. `range` và `max_age_ms` bắt buộc: không có thang thì không phát hiện được giá trị vô lý; cảm biến treo trả mãi giá trị cuối cùng trông như "an toàn" (§9.4, §9.5).
- **Không xác nhận thay số đo:** `on_block.confirms` từ chối tiêu chí `numeric` (`GateSchemaError`, `NE2002`). Con người trên thiết bị không thể xác nhận thay một đo lường vật lý khách quan.
- **Khớp kênh phần cứng tại thời điểm build:** `neuroedge build` kiểm tra tĩnh `unit` và thang đo `[min, max]` so với `range` (`BoardCapabilityError`, `NE3001`), loại bỏ nguy cơ cấu hình nhầm cảm biến. Trạng thái chân số `state()` chỉ nhận `source = measured`, ngăn phần mềm dùng `commanded` để giả lập trạng thái đạt.
- **Một đường cho độ tin cậy:** tiêu chí `numeric` không mang `confidence`; độ tin cậy là tiêu chí `numeric` riêng, khoá được bằng `gate lint` (§9.3, RFC-0012).
- **Nợ được trả:** ngưỡng số hôm nay nằm ở agent (`bands`); sau RFC này nó nằm ở gate và được `gate lint` cưỡng chế. `[sim.sensor_facts]` không đổi trong RFC này, nhưng không còn là cách duy nhất; thị giác không có `bands` (RFC-0012 §9.2).
- **Số thực dấu phẩy động:** ngưỡng, `range` và số đọc là `f64` hữu hạn; so sánh tất định trên host và MCU bằng đúng bốn phép, không dung sai ẩn (§9.6). Đầu vào từ ADC/cảm biến đã đổi sang đơn vị khai trước khi tới gate (`analog.in`, [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md)).
- **Host và chip không bao giờ đọc cùng cây theo hai nghĩa:** `layout_version` 2 đổi host và walker trong cùng PR do TSK-W1-02 chủ trì (§9.2). Bố cục byte được ghim dứt điểm; walker C kiểm soát nghiêm ngặt stack ≤ 512 byte và ngân sách flash bảng numeric tối đa 1,5 KB.

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
| Cho phép `on_block.confirms` với tiêu chí `numeric` | Người không thể xác nhận thay một đo lường vật lý; vi phạm an toàn fail-closed |
| Tiêu chí nối `digital.out.state()` nhận `source = commanded` | Cho phép phần mềm tự giả lập trạng thái đạt mà không cần cảm biến hồi tiếp thực |

## 7. Bằng chứng kiểm chứng

- [x] Ví dụ hợp lệ trong `fixtures/gates/valid/`: gate `numeric` đủ `unit`/`range`/`max_age_ms`, gate con thu hẹp cận dưới/trên/biên mở, gate độ tin cậy `range: { min: 0, max: 1 }`
- [x] Phản chứng trong `fixtures/gates/invalid/` + `expected_errors.yaml`: thiếu `unit`, thiếu `range`, thiếu `max_age_ms`, `max_age_ms` ≤ 0, `range` có `min ≥ max` hoặc không hữu hạn, ngưỡng không hữu hạn, ngưỡng ngoài `range`, khoảng rỗng, `eq`, `confidence_gte` trên `numeric`, trường `confidence`, `levels`/`options` đi kèm `numeric`, tiêu chí `numeric` nằm trong `on_block.confirms` (`GateSchemaError`, `NE2002`); kế thừa: nới cận, bỏ cận cha khi ghi đè, đổi `unit`, đổi `range`, đổi `max_age_ms` (`GateInheritanceError`, `NE2003`)
- [ ] *(cùng TSK-I2a-04 và RFC-0010; phần `sensor.read` ⇒ `NE3001` và `commanded` ⇒ BLOCK đã có; **phần `analog.in` đạt** ở TSK-I2a-04: `tests/test_analog_in.py`, nối bằng `[sim.analog_facts]`; còn readback `feedback` của RFC-0010)* Ràng buộc kênh HAL: `neuroedge build` kiểm tra khớp `unit` và `[min, max]` của kênh HAL nằm trong `range` của tiêu chí `numeric`; phản chứng lệch `unit` hoặc `[min, max]` vượt `range` bị từ chối với `BoardCapabilityError` (`NE3001`); test tiêu chí nối `digital.out(...).state()` nhận `source = commanded` ⇒ BLOCK `criterion_unavailable`, chỉ cho qua khi `source = measured`
- [x] Engine: không có số đọc ⇒ BLOCK `criterion_unavailable`; `age_ms < 0` (mốc HAL đọc sau thời điểm lượng giá) ⇒ BLOCK `criterion_unavailable`; tuổi > `max_age_ms` ⇒ BLOCK `criterion_unavailable` (ca biên tuổi đúng bằng `max_age_ms` cho qua); NaN, ±inf, ngoài `range` ⇒ BLOCK `value_out_of_range`; thứ tự kiểm theo §3c
- [x] Replay: vết ghi mang cả mốc HAL đọc và `age_ms`; `replay` tính lại tuổi và so khớp; thị giác lượng giá tuổi của cửa sổ theo khung cũ nhất
- [x] Walker C khớp engine host trên mọi gate (mở rộng `python/tests/test_c_walker.py`), gồm test C cho mọi biên: đóng/mở (`gt`, `gte`, `lt`, `lte`), NaN, ±inf, đúng biên `range` (`min`, `max`), `age_ms = max_age_ms`, `age_ms = max_age_ms + 1`, `age_ms < 0`; kiểm tra ABI fact `f64 value` + `i64 age_ms`; kiểm tra đột biến (đảo `<`/`<=`, bỏ kiểm NaN, bỏ kiểm `range`, bỏ kiểm tuổi); kiểm tra stack walker C ≤ 512 byte; kiểm tra ngân sách flash bảng numeric (48 byte × tối đa 32 mục = 1.536 byte)
- [x] Walker v1 từ chối cây v2 (`NE_ERR_VERSION`); `test_ui_assets.py` giữ `ne_reason` và `firmware.REASONS` khớp nhau sau khi thêm `value_out_of_range`
- [x] `neuroedge gate lint` và `neuroedge verify` vẫn xanh; `scripts/check_digests.py` không đổi digest gate đã khoá

## 8. Việc phải làm khi chấp thuận

- [x] Cập nhật `schemas/gate.v1.json` (enum `type`, `unit`, `range`, `max_age_ms` bắt buộc, nhánh `if/then`)
- [x] Cập nhật Phụ lục B.2/B.5 trong `neuroedge-proposal.md`; FR-GATE-03 ở `neuroedge-prd.md`; ghi chấp thuận vào Q-57 (`neuroedge-prd.md` §15)
- [x] Cập nhật `neuroedge-roadmap.md` (TSK-W1-02) và đóng `TODOS.md` #30
- [x] `engine/constraints.py`, `engine/gate_resolver.py`, `engine/verdict.py` (`value_out_of_range`), `engine/binary_tree.py`, `engine/firmware.py` (`REASONS`), walker C (`ne_walker.h`), `gate explain`
- [x] Cập nhật `neuroedge gate lint` từ chối tiêu chí `numeric` trong `on_block.confirms` (`GateSchemaError`, `NE2002`)
- [ ] *(cùng TSK-I2a-04 và RFC-0010; **phần `analog.in` đạt**: `check_analog_facts` ở `engine/compiler.py` kiểm `unit` và `range`; còn `source = measured` của readback `digital.out`)* Cập nhật `neuroedge build` kiểm tra ràng buộc kênh HAL với tiêu chí `numeric` (`unit`, `range`, `source = measured`) (`BoardCapabilityError`, `NE3001`)
- [x] Ghi cả mốc HAL đọc lẫn `age_ms` vào vết ghi; cập nhật `replay` tính lại và so sánh; xử lý `age_ms < 0` ⇒ BLOCK `criterion_unavailable`; cập nhật `docs/spec/simulation_coverage.md` §4 và bảng lý do ở `docs/spec/ui.md` (nhãn trong `ne_ui_strings.c`)
- [x] Một PR duy nhất nâng `layout_version` lên 2 do TSK-W1-02 chủ trì gồm bảng `numeric` và các trường `TODOS.md` #36 (RFC-0011 không thêm trường vào `NETR`); ABI walker C nhận `f64 value` + `i64 age_ms`, kiểm tra stack ≤ 512 byte và ngân sách flash bảng numeric 48 byte × 32 (§3d)
- [x] Thêm fixture và test; cập nhật `docs/rfc/README.md` và `CHANGELOG.md`

## 9. Quyết định cho các câu hỏi mở (Q-57, 2026-09-30; Q-62, 2026-10-01)

Chủ sản phẩm uỷ quyền quyết các câu hỏi mở theo nguyên tắc **an toàn cao nhất**: giữa hai phương án, chọn phương án fail-closed và khó dùng sai hơn, kể cả khi nó tốn công hơn. Các quyết định dưới đây **đã được gộp vào §3–§8**; mục này giữ lại làm hồ sơ quyết định (Q-57). Chấp thuận RFC vẫn cần chữ ký kỹ thuật trưởng (`CONTRIBUTING.md` §3).

1. **Lý do lỗi.** Thêm lý do riêng `value_out_of_range` (số đọc ngoài `range`, NaN, ±inf); `criterion_unavailable` giữ cho trường hợp không có số đọc. Cả hai đều BLOCK. *Vì sao:* hậu kiểm phân biệt được "mất cảm biến" với "cảm biến trả rác", phán quyết không đổi.
2. **Bố cục `NETR`.** Tăng `layout_version` lên 2 **một lần**, trong một PR do TSK-W1-02 chủ trì gồm bảng `numeric` của RFC này và các trường của `TODOS.md` #36 (RFC-0011 không thêm trường vào `NETR`); ghim bố cục byte ngay trong RFC-0009; engine host và walker C đổi trong cùng PR; walker v1 từ chối cây v2 (`NE_ERR_VERSION`, fail-closed). *Vì sao:* không bao giờ có giai đoạn host và chip đọc cùng cây theo hai nghĩa; định dạng nhị phân được đóng băng dứt điểm.
3. **Độ tin cậy.** Tiêu chí `numeric` không có trường `confidence`; độ tin cậy, khi cần, là **một tiêu chí `numeric` khác** (đường của RFC-0012). *Vì sao:* một đường duy nhất, khoá được bằng `gate lint`.
4. **`range` bắt buộc.** *Vì sao:* không có thang thì không phát hiện được giá trị vô lý, fail-closed mất cạnh.
5. **Tuổi số đọc.** `max_age_ms` **bắt buộc** với mọi tiêu chí `numeric`; số đọc cũ hơn ⇒ `criterion_unavailable` ⇒ BLOCK. Mốc HAL đọc và `age_ms` được ghi vào vết ghi để `replay` tính lại và so; `age_ms < 0` (mốc đọc sau thời điểm lượng giá) ⇒ BLOCK `criterion_unavailable`. *Vì sao:* một cảm biến treo trả mãi giá trị cuối cùng trông như "an toàn"; gate phải từ chối số đọc đã cũ hoặc vi phạm trật tự nhân quả.
6. **So sánh số thực.** Ngưỡng, `range` và số đọc là `f64` hữu hạn; host và walker C dùng đúng bốn phép `>`, `>=`, `<`, `<=`, không dung sai ẩn; vector tuân thủ có ca đúng bằng ngưỡng ở mọi biên.
7. **Ràng buộc kênh HAL và cấm xác nhận số** (review 2026-10-01, Q-62). Agent nối tiêu chí `numeric` với kênh HAL (`analog.in`, readback `feedback`; `sensor.read` hôm nay không khai `unit` và thang nên **không** nối được với tiêu chí `numeric` — nối ⇒ `BoardCapabilityError` (`NE3001`)) phải trùng `unit` và `[min, max]` của kênh phải nằm trong `range` của tiêu chí, lệch ⇒ `BoardCapabilityError` (`NE3001`); `digital.out(...).state()` chỉ nhận giá trị có `source = measured` (nhận `commanded` ⇒ `criterion_unavailable`); tiêu chí `numeric` bị cấm tuyệt đối trong `on_block.confirms` (`GateSchemaError`, `NE2002`). *Vì sao:* người không thể xác nhận thay một giới hạn đo vật lý; ngăn ngừa việc dùng trạng thái logic commanded hoặc cảm biến sai lệch thang đo để vượt qua gate.
8. **Định nghĩa tuổi dữ kiện và lượng giá replay** (review 2026-10-01, Q-62). Thời điểm lượng giá là offset của sự kiện phán quyết trên cùng trục thời gian đơn điệu của phiên với mốc đọc của HAL; tuổi = thời điểm lượng giá − mốc HAL đọc; vết ghi ghi cả mốc đọc lẫn `age_ms`; `replay` tính lại và so sánh; `age_ms < 0` ⇒ BLOCK `criterion_unavailable`. Với thị giác, tuổi của cửa sổ là tuổi của khung cũ nhất trong cửa sổ. *Vì sao:* bảo đảm tính tất định khi replay và triệt tiêu rủi ro sai lệch đồng hồ hoặc mốc đọc nằm ở tương lai so với phán quyết.
9. **Đóng băng bố cục `NETR` v2 và ABI walker** (review 2026-10-01, Q-62). Ghim trực tiếp bố cục byte header 80 byte và bảng `numeric` 48 byte trong RFC-0009; ABI fact numeric tới walker C nhận `f64 value` và `i64 age_ms`; giới hạn stack walker C ≤ 512 byte; ngân sách flash cho bảng `numeric` là 48 byte × tối đa 32 mục (tối đa 1.536 byte). *Vì sao:* loại bỏ mâu thuẫn hoãn ghim byte sang PR thứ hai; cố định ABI và kiểm soát chặt chẽ tài nguyên flash và stack của firmware trên MCU.
