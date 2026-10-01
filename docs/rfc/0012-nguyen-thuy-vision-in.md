# RFC-0012: Nguyên thủy `vision.in` và bằng chứng nhận thức thị giác

| | |
|:---|:---|
| **Mã RFC** | 0012 |
| **Tiêu đề** | `vision.in` (năng lực bo mạch), dữ kiện gõ kiểu do maker khai từ nhãn mô hình, bằng chứng trong vết ghi, tương đương giữa các target |
| **Hợp đồng bị ảnh hưởng** | `board.v1` *(khoá `vision_in`, gồm sai số suy luận §3f)* · khối `[vision]` của `agent.toml` *(không có lược đồ trong `schemas/`; kiểm ở `neuroedge build`)* · quy ước sự kiện `perception` thị giác và lint ngữ nghĩa vết ghi *(không đổi `trace.v1`: `events[].data` là `object` tự do, `metadata` mở — §4)* · **không** đụng `gate.v1` · `neuroedge-prd.md` Phụ lục B: nới nguyên nhân của ba dòng có sẵn, **không mã mới** (§4) |
| **Yêu cầu PRD liên quan** | FR-HAL-01, FR-HAL-04, FR-HAL-05, FR-CI-02, FR-MDL-04, FR-MDL-07, NFR-PRIV-01, NFR-PRIV-03 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-09-30 |
| **Trạng thái** | ⏳ Nháp — chưa mở PR · câu hỏi mở đã quyết và đã gộp vào §3–§8 (§9, Q-57) · còn bốn điểm phải chốt trước khi mở PR (§3g) |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (chạm `board.v1`, quyền riêng tư camera, ranh giới nhận thức/thẩm quyền) |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3 — sửa `schemas/board.v1.json`. Task: TSK-V1b-07 (RFC này) và
> TSK-V1b-01, TSK-V1b-02, TSK-V1b-03, TSK-V1b-04, TSK-V1b-05, TSK-V1b-06, TSK-V1b-08. Đây là RFC mà RFC-0002 §9.1 và §9.2 hoãn lại; đầu vào đã biết nằm ở đó. Quyết
> định nền: `neuroedge-prd.md` §15 Q-52, Q-53 (camera có mặt trên cả ba target; bo mạch ESP32-S3 có
> camera), **Q-54** (thị giác → dữ kiện do maker khai, gate khoá ngưỡng bằng tiêu chí `numeric`, **không
> có ngữ nghĩa gate riêng cho thị giác**), Q-55, Q-57 (§9).

## 1. Vấn đề

`vision.in` chỉ tồn tại ở văn bản. Bốn khoảng trống:

1. **Bo mạch không khai được camera.** `sensor.read` trả vô hướng rời rạc (RFC-0002 §9.1), không phải luồng khung hình. Hình dạng thử nghiệm ban đầu (`width`, `height`, `fps` nguyên, chuỗi tự do) không so khớp được với agent.
2. **Không có đường từ nhãn mô hình tới phán quyết.** `neuroedge-design-phase2.md` §2.2 để mở có chủ đích bài toán ngữ nghĩa gate riêng cho thị giác; ràng buộc hiện hành ở đó (Q-54) đi vòng: quy thị giác về dữ kiện gõ kiểu mà gate đã biết lượng giá, ngưỡng khoá ở gate. Chưa có cú pháp và luật cho đường đó.
3. **Không có luật vết ghi.** Camera trong không gian riêng tư là rủi ro lớn hơn micro; cần quy ước chính xác cái gì được ghi (NFR-PRIV-01, NFR-PRIV-03), và đủ để `replay` tái hiện phán quyết (FR-CI-02).
4. **Không có cách chứng minh tương đương.** Mô hình thị giác chạy trên ba target với phần cứng khác nhau; "gate quyết giống nhau" và "mô hình thấy giống nhau" là hai mệnh đề khác nhau, chưa cái nào được kiểm.

## 2. Vì sao lược đồ hiện tại không giải quyết được

- `schemas/board.v1.json`: không có khoá `vision_in`; nếu có ai thêm nó sẽ validate qua vì `capabilities` không đóng, nhưng không có kiểu để đối chiếu — và mọi sửa hình dạng sau khi phát hành là siết chặt (RFC-0002 §6).
- `gate.v1` chỉ lượng giá `bool` / `level` / `choice`; RFC-0009 thêm `numeric`. Không cần thêm gì khác cho thị giác nếu số đếm và độ tin cậy được biểu diễn như dữ kiện số. `confidence_gte` (`engine/constraints.py`, `BOOL_OPERATORS`) là đường thứ hai cho độ tin cậy trên tiêu chí `bool`; gate không biết tiêu chí nào đến từ thị giác nên `gate lint` không chặn được đường đó — chỉ lúc build mới có cả gate lẫn manifest (§3c).
- `agent.toml` (`fixtures/agents/*/agent.toml`) không có chỗ khai nhãn → dữ kiện. Đường vòng sẵn có, `bands` ở `[sim.sensor_facts]`, đặt ngưỡng ở agent — đúng thứ Q-54 và RFC-0009 §1 bác.
- `[requires]` của agent chưa có quy tắc so khớp cho tham số số.

## 3. Thay đổi đề xuất

### 3a. Năng lực bo mạch

```toml
[capabilities.vision_in]
modes = [
  { width = 640,  height = 480, fps = 30.0,  pixel_format = "yuyv" },
  { width = 1280, height = 720, fps = 7.5,   pixel_format = "mjpeg" },
]
```

- `fps` là `number` (7,5 · 29,97), không phải số nguyên; cảm biến nhiều chế độ nên `modes[]` là mảng bắt buộc (ít nhất một phần tử).
- `pixel_format` là **enum đóng**: `yuyv`, `mjpeg`, `rgb565`, `rgb888`, `gray8`; thêm giá trị cần RFC (§9.1).
- `vision_in` khai thêm **sai số suy luận** cho phép so với golden trên host, dùng ở §3f (§9.6). Tên và hình dạng trường: §3g.
- Không khai bộ tăng tốc (`accelerator`) trong RFC này: mô hình và NPU thuộc cấu hình agent (TSK-V1b-03, TSK-V1b-05), không thuộc hợp đồng bo mạch.

### 3b. So khớp với `[requires]`

Agent khai yêu cầu tối thiểu, bo mạch thoả nếu **tồn tại ít nhất một chế độ** đủ mọi ngưỡng:

```toml
[requires]
"vision.in" = { min_width = 640, min_height = 480, min_fps = 10.0, pixel_formats = ["yuyv", "mjpeg"] }
```

`neuroedge build` (`engine/compiler.py`) từ chối bo mạch không có chế độ nào thoả bằng `BoardCapabilityError` (`NE3001`), lỗi ba phần nêu chế độ gần nhất (FR-HAL-05). So khớp tất định vì `pixel_format` là enum đóng.

### 3c. Từ nhãn mô hình tới dữ kiện gõ kiểu (Q-54, §9.2–9.3)

**Maker** khai trong `agent.toml` nhãn nào thành dữ kiện nào; **gate** khoá ngưỡng. Ví dụ — mở cổng khi có người đứng ở cổng, đóng cổng khi không còn ai:

```toml
# agent.toml — maker khai
[vision]
model = "models/person-det.tflite"

[vision.zones]
gate_area = { x = 0.25, y = 0.40, w = 0.50, h = 0.60 }   # hình dạng vùng: chưa chốt (§3g)

[vision.facts.person_at_gate]
label      = "person"
zone       = "gate_area"
kind       = "present"      # → tiêu chí bool
min_frames = 3              # mặc định 3, tối thiểu 2

[vision.facts.person_confidence]
label = "person"
zone  = "gate_area"
kind  = "confidence"        # → tiêu chí numeric, [0, 1]

[vision.facts.people_at_gate]
label = "person"
zone  = "gate_area"
kind  = "count"             # → tiêu chí numeric, số nguyên ≥ 0
```

```yaml
# gates/open_gate — thẩm quyền
evaluate:
  person_at_gate:    { type: bool, instructions: "Có người trong vùng cổng" }
  person_confidence: { type: numeric, unit: ratio, range: { min: 0, max: 1 }, max_age_ms: 300,
                       instructions: "Điểm tin cậy của nhãn person trong vùng cổng" }
allow_when:
  person_at_gate: true
  person_confidence: { gte: 0.85 }      # khoá ở gate, kế thừa chỉ thu hẹp (RFC-0009)

# gates/close_gate
evaluate:
  people_at_gate: { type: numeric, unit: count, range: { min: 0, max: 50 }, max_age_ms: 300,
                    instructions: "Số người trong vùng cổng" }
allow_when:
  people_at_gate: { lte: 0 }
```

**Luật dữ kiện:**

| Trường | Luật |
|:---|:---|
| `[vision] model` | Một tệp mô hình; danh tính = tên + sha256 của tệp (§3d) |
| `kind` | `present` → `bool` · `count` → `numeric` (số nguyên ≥ 0) · `confidence` → `numeric` trong `[0, 1]`. Không có `level`/`choice`, không có `bands` |
| Tên dữ kiện | Trùng tên tiêu chí của gate; kiểu tiêu chí cùng tên phải khớp `kind` |
| `zone` | Phải khai ở `[vision.zones]` |
| `min_frames` | Mặc định 3, tối thiểu 2. `present` chỉ được quyết khi cùng một giá trị giữ qua `min_frames` khung **liên tiếp**; chưa đủ ⇒ chưa quyết ⇒ BLOCK |
| `confidence` | **Giá trị nhỏ nhất** trong cửa sổ `min_frames` khung |

**Không có ngưỡng nào trong `agent.toml`.** Mọi ngưỡng trên số đếm và độ tin cậy nằm trong tiêu chí `numeric` của gate (Q-54, RFC-0009 §1). Maker chọn *nhãn nào thành dữ kiện nào*; **maker không chọn được ngưỡng an toàn**. Không có toán tử gate riêng cho thị giác: mọi thứ đi qua `bool`/`numeric`.

**Một đường cho độ tin cậy.** Gate dùng `confidence_gte` trên tiêu chí mà `agent.toml` khai là dữ kiện thị giác bị `neuroedge build` từ chối. `gate lint` không làm được việc này: gate không biết dữ kiện nào đến từ thị giác, chỉ lúc build mới có cả gate lẫn manifest. (`confidence_gte` trên tiêu chí `numeric` thì `gate lint` đã từ chối, RFC-0009 §3a.)

**`neuroedge build` từ chối bằng `AgentManifestError` (`NE3002`):** `kind` ngoài ba giá trị; khoá lạ trong `[vision.facts.*]`, kể cả `bands`; `min_frames` < 2; `zone` chưa khai; kiểu tiêu chí cùng tên không khớp `kind`; gate dùng `confidence_gte` trên dữ kiện thị giác. Gom vào `BuildFailed` (`NE3003`) như mọi vấn đề build khác.

### 3d. Vết ghi

Mỗi dữ kiện thị giác lượng giá cho một phán quyết ghi một sự kiện nhóm `perception` (Phụ lục C.1 của `neuroedge-proposal.md`; tên sự kiện ghi ở `docs/spec/simulation_coverage.md` §3 — §8):

```json
{ "offset_ms": 1840, "type": "vision_fact", "data": {
    "fact": "person_at_gate", "kind": "present", "min_frames": 3, "value": true,
    "model": { "name": "person-det", "sha256": "…" },
    "frames": [
      { "vision_ref": { "sha256": "…", "size": 61440 }, "captured_ms": 1700, "labels": [{ "label": "person", "zone": "gate_area", "score": 0.93 }] },
      { "vision_ref": { "sha256": "…", "size": 61312 }, "captured_ms": 1767, "labels": [ … ] },
      { "vision_ref": { "sha256": "…", "size": 61500 }, "captured_ms": 1833, "labels": [ … ] } ] } }
```

- **Danh tính mô hình** (tên + sha256 của tệp mô hình) nằm ở **mỗi** sự kiện `perception` thị giác, kèm danh sách mọi mô hình đã dùng trong phiên ở `metadata` (§9.4). Mô hình đổi giữa phiên vẫn truy được từng phán quyết.
- **`vision_ref` = `{ sha256, size }`** ghi cho **mọi khung trong cửa sổ** đã sinh ra dữ kiện của phán quyết, không ghi khung ngoài cửa sổ (§9.5). **Không nhúng ảnh thô.** Mốc `captured_ms` của từng khung được ghi để `replay` tính lại tuổi khung đúng như lúc chạy (RFC-0009 §3c).
- Nhãn, vùng và điểm của từng khung trong cửa sổ được ghi; đó là thứ `replay` dùng để tái hiện phán quyết (FR-CI-02). Một mã băm khung hình không replay được.
- `trace.v1` **không đổi** (§4). Lint ngữ nghĩa ở `python/neuroedge/trace.py` (TSK-V1b-08), vi phạm ⇒ `TraceValidationError` (`NE4001`):
  - `sha256` (của `vision_ref` và của `model`) khớp `^[0-9a-f]{64}$`;
  - `uri` chỉ khi `metadata.raw_capture == true`; từ chối blob base64 trong `data`;
  - sự kiện `perception` thị giác thiếu `model.name`/`model.sha256`, hoặc sha256 mô hình không có trong danh sách ở `metadata`;
  - số phần tử `frames` khác `min_frames` của sự kiện (thiếu khung trong cửa sổ, hay thừa khung ngoài cửa sổ).

### 3e. Fail-closed (§9.7)

Kiểm theo thứ tự, mọi nhánh đều BLOCK, **không nội suy từ khung trước**, không có giá trị mặc định "không thấy người":

| Tình huống | `reason` |
|:---|:---|
| Mất camera, mất mô hình, mô hình không trả lời | `criterion_unavailable` |
| Khung quá cũ (tuổi > `max_age_ms` của tiêu chí, RFC-0009 §3c) | `criterion_unavailable` |
| `present` chưa giữ cùng giá trị qua `min_frames` khung liên tiếp; kết quả rác bị tầng nhận thức loại trước khi tới gate (nhãn ngoài tập nhãn của mô hình, `count` âm hoặc không nguyên) | `criterion_unavailable` |
| Điểm hoặc số đếm NaN, ±inf, ngoài `range` của tiêu chí `numeric` | `value_out_of_range` (RFC-0009 §9.1) |

### 3f. Tương đương giữa các target (§9.6)

Hai mệnh đề, kiểm riêng, cả hai đều phải chứng minh:

1. **Gate quyết giống nhau.** Camera ảo trong `sim` (TSK-V1b-02) phát lại chuỗi khung đã ghi **và** kết quả `perception` đã ghi; `neuroedge verify` so phán quyết giữa các target từ cùng sự kiện `perception`. Lệch ⇒ `SafetyRegressionError` (`NE4002`).
2. **Mô hình thấy giống nhau.** Với mỗi sha256 mô hình, kết quả suy luận trên từng target phải khớp kết quả golden trên host trong sai số khai ở `vision_in` của bo mạch (§3a). Vượt sai số ⇒ `SafetyRegressionError` (`NE4002`). Golden suy luận và Action CI cho khung hình: TSK-V1b-04.

### 3g. Điểm phải chốt trước khi mở PR

§9 không quyết bốn điểm dưới; RFC này không tự quyết thay. Kỹ thuật trưởng chốt trước khi mở PR, vì hình dạng `board.v1` phải đúng ngay lần đầu (§4):

1. **Hình dạng vùng** trong `[vision.zones]` (§9.2 chỉ nêu tên). Ví dụ ở §3c dùng hình chữ nhật chuẩn hoá `[0, 1]` chỉ để minh hoạ.
2. **Tên và hình dạng trường sai số suy luận** trong `vision_in` (§9.6): áp lên điểm, lên hộp, hay cả hai; một giá trị cho mọi mô hình hay theo sha256.
3. **Cách gộp `count` qua cửa sổ.** §9.2 quyết `present` (liên tiếp) và `confidence` (giá trị nhỏ nhất), không quyết `count`.
4. **Tuổi khung cho dữ kiện `present`.** §9.7 dẫn `max_age_ms` của RFC-0009, nhưng trường đó chỉ có ở tiêu chí `numeric`; tiêu chí `bool` trong `gate.v1` không có tuổi. Cần chốt mốc tuổi nào áp cho `present` mà không thêm ngữ nghĩa thị giác vào gate (Q-54).

Đọc `present` ở §3c ("**cùng một giá trị**" giữ qua `min_frames` khung, áp cho cả `true` lẫn `false`) là cách đọc fail-closed của §9.2: gate cho qua khi `false` (ví dụ `close_gate` viết bằng `present`) cũng không được mở khoá bởi một khung nhiễu. Kỹ thuật trưởng xác nhận cùng bốn điểm trên.

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — không profile nào trong `boards/` khai `vision_in`, không agent nào trong `fixtures/agents/` có khối `[vision]` |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có — profile khai `vision_in` đúng hình dạng (`modes[]`, enum `pixel_format`, sai số suy luận). Cùng điểm siết chặt khoá `capabilities` như RFC-0007 §4: hình dạng phải đúng ngay lần đầu, nên §3g phải chốt trước PR |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không. `trace.v1` không đổi: `events[].data` chỉ ràng buộc `"type": "object"` và `metadata` có `additionalProperties: true`, nên `model`, `frames`, `vision_ref` và danh sách mô hình ở `metadata` validate qua; luật của §3d là lint ngữ nghĩa ở `trace.py`, không phải lược đồ (RFC-0002 §9.2) |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không — chúng không có sự kiện thị giác, nên lint mới không chạm chúng |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào; ba gate mẫu thị giác (TSK-V1b-06) vào `digests.lock` bằng PR thường |
| Bố cục `NETR` hoặc walker C phải đổi? | Không riêng RFC này; dùng nút `numeric` của RFC-0009 |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không |

**Mã lỗi** (`neuroedge-prd.md` Phụ lục B): RFC này không thêm mã. Mọi lớp dùng đã có trong `python/neuroedge/errors.py`; khi chấp thuận, cột *Nguyên nhân* của ba dòng được nới:

| Lớp | Nguyên nhân thêm |
|:---|:---|
| `AgentManifestError` (`NE3002`) | Khối `[vision]` sai (§3c), hoặc gate dùng `confidence_gte` trên dữ kiện thị giác |
| `TraceValidationError` (`NE4001`) | Lint ngữ nghĩa thị giác (§3d) — dòng hiện chỉ nêu lược đồ và dòng UART |
| `SafetyRegressionError` (`NE4002`) | Suy luận mô hình trên một target lệch golden host quá sai số khai ở bo mạch (§3f) |

`BoardCapabilityError` (`NE3001`) không đổi: "agent yêu cầu năng lực bo mạch không cung cấp" đã bao phủ §3b. `criterion_unavailable` và `value_out_of_range` là lý do phán quyết (RFC-0009), không phải exception.

## 5. Ảnh hưởng an toàn

- **Gate không lỏng hơn và không có ngữ nghĩa thị giác mới** (Q-54): `gate.v1`, phân giải, năm nguyên tắc không đổi. Ràng buộc của `neuroedge-design-phase2.md` §2.2 — thị giác quy về các kiểu dữ kiện gate đã biết lượng giá, ngưỡng tin cậy khoá bằng `numeric` — được giữ nguyên.
- **Nhận thức không thành thẩm quyền:** mô hình chỉ cấp dữ kiện; mọi ngưỡng trên số đếm và độ tin cậy do gate khoá và chỉ thu hẹp được khi kế thừa. Maker nới ngưỡng bằng `agent.toml` **không được** vì ngưỡng không nằm ở đó (`bands` bị từ chối).
- **Một đường cho độ tin cậy:** `confidence_gte` trên dữ kiện thị giác bị build từ chối, nên không có đường thứ hai để quên khoá (§3c).
- **Một khung nhiễu không mở khoá được:** `present` cần `min_frames` khung liên tiếp (mặc định 3, tối thiểu 2); `confidence` lấy giá trị nhỏ nhất trong cửa sổ — bảo thủ.
- **Không nội suy:** mất camera, mất mô hình, khung quá cũ ⇒ BLOCK (§3e).
- **Riêng tư:** không khung thô trong vết ghi theo mặc định; lưu ảnh thô phải bật tường minh (`metadata.raw_capture`). Chỉ khung trong cửa sổ để lại `vision_ref`. Quy tắc chặt hơn micro, không lỏng hơn.
- **Danh tính mô hình ở mỗi sự kiện:** đổi mô hình là đổi hành vi; vết ghi phải cho biết mô hình nào ra kết luận nào, kể cả khi mô hình đổi giữa phiên.
- **Tương đương hai tầng** (§3f): "gate quyết giống nhau" không chứng minh "mô hình thấy giống nhau"; cả hai đều được kiểm.
- **Rủi ro còn lại:** mô hình sai với điểm cao (nhãn sai tự tin). Giảm bằng ngưỡng số ở gate, cửa sổ nhiều khung, và — với hành động không hoàn tác — `on_block: ask`; không loại được hoàn toàn. Bốn điểm §3g là khoảng hở cho tới khi chốt.
- **Ngân sách bộ nhớ `esp32s3`:** camera trên MCU tốn SRAM/PSRAM; số đo trên bo mạch thật (Q-3) là điều kiện, không phải giả định.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Ngữ nghĩa gate riêng cho bằng chứng thị giác (vùng cấm, đếm người) | Q-54: phá tính xác định của rule engine, cần RFC `gate.v1` lớn; quy về dữ kiện gõ kiểu đủ cho ca sử dụng ưu tiên |
| Maker tự đặt ngưỡng trong `agent.toml` (kể cả `bands` cho `count`) | Ý nghĩa an toàn ngoài gate, `gate lint` không thấy; cùng lý do RFC-0005 §6 và RFC-0009 §1 |
| Cho phép `confidence_gte` song song với tiêu chí `numeric` | Hai đường thì một đường sẽ bị quên khoá (§9.3) |
| Kiểm `confidence_gte` trên dữ kiện thị giác ở `gate lint` | Gate không biết dữ kiện nào đến từ thị giác; chỉ build có cả gate lẫn manifest |
| `present` quyết từ một khung; `confidence` lấy trung bình hoặc khung cuối | Một khung nhiễu mở khoá cửa; trung bình che khung yếu (§9.2) |
| `fps` nguyên, `pixel_format` chuỗi tự do | Không biểu diễn 7,5 fps; không so khớp tất định (RFC-0002 §9.1; §9.1) |
| Mở rộng `sensor.read` | Không mang luồng khung; xem lập luận ở RFC-0007 §2 |
| Ghi mọi khung vào vết ghi | Vi phạm NFR-PRIV-01, NFR-PRIV-03; 30 fps ≈ 13 MB/giờ chỉ riêng băm và siêu dữ liệu |
| Chỉ ghi `vision_ref` của khung cuối | Không hậu kiểm được luật `min_frames` và giá trị nhỏ nhất (§9.5) |
| Danh tính mô hình chỉ ở `metadata` | Mô hình đổi giữa phiên thì không truy được phán quyết nào do mô hình nào (§9.4) |
| Nội suy từ khung trước khi mất camera hay khung quá cũ | Camera treo trông như "không có gì thay đổi" (§9.7, RFC-0009 §9.5) |
| `verify` chỉ so phán quyết | Không chứng minh mô hình cho cùng kết quả trên mọi target (§9.6) |

## 7. Bằng chứng kiểm chứng

Mỗi dòng nêu quyết định §9 nó phủ. Corpus theo luật khép kín hai chiều (`CONTRIBUTING.md` §3).

- [ ] **Bo mạch (§9.1):** ví dụ hợp lệ — profile `linux` và bo mạch `esp32s3` có camera khai `vision_in` (RFC-0013), có sai số suy luận; phản chứng — `fps` chuỗi, `modes` rỗng, `pixel_format` ngoài năm giá trị enum, thiếu sai số suy luận
- [ ] **`[requires]` (§3b):** agent mẫu có `[requires] "vision.in"`; bo mạch không có chế độ thoả ⇒ `BoardCapabilityError` nêu chế độ gần nhất
- [ ] **Cú pháp dữ kiện (§9.2)** — `python/tests/test_compiler.py`: agent mẫu có `[vision]` hợp lệ build được; mỗi lỗi sau ⇒ `AgentManifestError`: `kind` lạ, `bands`, `min_frames = 1`, `zone` chưa khai, `present` ghép với tiêu chí `numeric`, `count`/`confidence` ghép với tiêu chí `bool`
- [ ] **`min_frames` (§9.2):** mặc định 3 — 2 khung liên tiếp chưa quyết ⇒ BLOCK, 3 khung quyết; `min_frames = 2` quyết sau 2 khung; một khung nhiễu giữa cửa sổ ⇒ chưa quyết ⇒ BLOCK, cho cả gate cho qua khi `true` lẫn khi `false`
- [ ] **Giá trị nhỏ nhất (§9.2):** điểm `[0.95, 0.80, 0.95]`, gate `gte: 0.85` ⇒ BLOCK; `[0.90, 0.86, 0.92]` ⇒ ALLOW
- [ ] **`count` (§9.2):** gate `lte: 0` chặn khi đếm 1, cho qua khi đếm 0; mô hình hỏng trả số đếm âm hoặc không nguyên ⇒ BLOCK `criterion_unavailable`
- [ ] **Một đường (§9.3):** gate dùng `confidence_gte` trên dữ kiện thị giác **qua** `gate lint` nhưng `neuroedge build` từ chối bằng `AgentManifestError` (`NE3002`) — ghim ranh giới lint/build
- [ ] **Danh tính mô hình (§9.4)** — `fixtures/traces/invalid/` + `expected_errors.yaml`: sự kiện `perception` thị giác thiếu `model`, sha256 mô hình không có trong `metadata`; phiên đổi mô hình giữa chừng ⇒ mỗi phán quyết truy được mô hình của nó
- [ ] **`vision_ref` (§9.5)** — `fixtures/traces/invalid/`: `frames` ít hơn và nhiều hơn `min_frames`; `sha256` sai dạng; `uri` khi không `raw_capture`; base64 trong `data`
- [ ] **Tương đương (§9.6):** `verify` cho cùng phán quyết trên `sim`, `linux`, `esp32s3` từ cùng sự kiện `perception`; suy luận lệch golden trong sai số ⇒ xanh, vượt sai số ⇒ `SafetyRegressionError` (`NE4002`)
- [ ] **Fail-closed (§9.7):** mất camera, mất mô hình ⇒ BLOCK `criterion_unavailable`; khung tuổi > `max_age_ms` ⇒ BLOCK `criterion_unavailable` dù khung trước đó tốt (không nội suy); ca biên tuổi đúng bằng `max_age_ms` cho qua; điểm NaN hoặc ngoài `[0, 1]` ⇒ BLOCK `value_out_of_range` (corpus ở TSK-V1b-06 và Action CI TSK-V1b-04)
- [ ] `replay` tái hiện phán quyết từ sự kiện `perception`, không cần khung hình, kể cả tuổi khung từ `captured_ms`
- [ ] `neuroedge gate lint` và `neuroedge verify` xanh
- [ ] Bốn điểm §3g đã chốt và có test tương ứng trước khi đổi trạng thái sang chấp thuận

## 8. Việc phải làm khi chấp thuận

- [ ] Cập nhật `schemas/board.v1.json` (`vision_in`: `modes[]`, enum `pixel_format`, sai số suy luận)
- [ ] Cập nhật Phụ lục C.1 trong `neuroedge-proposal.md`; FR-HAL-01 ở `neuroedge-prd.md`; Phụ lục B của `neuroedge-prd.md` — nới nguyên nhân ba dòng ở §4; `TODOS.md` #14 (cách sửa nằm ở RFC-0013)
- [ ] `docs/spec/simulation_coverage.md`: tên sự kiện `perception` thị giác ở §3, dòng `vision.in` ở ma trận §2
- [ ] `neuroedge-roadmap.md`: TSK-V1b-07 xong; mở TSK-V1b-01, TSK-V1b-02, TSK-V1b-03, TSK-V1b-04, TSK-V1b-05, TSK-V1b-06, TSK-V1b-08
- [ ] `engine/compiler.py` (khối `[vision]`, `confidence_gte` trên dữ kiện thị giác, so khớp `modes[]`), `python/neuroedge/hal/` (`linux.py`, `sim.py`), `python/neuroedge/trace.py` (lint §3d), `perception/vision/` (cửa sổ `min_frames`, giá trị nhỏ nhất), camera ảo trong `sim`, golden suy luận theo sha256 mô hình và kiểm sai số trong `verify`
- [ ] Fixture/test; cập nhật `docs/rfc/README.md` và `CHANGELOG.md`

## 9. Quyết định cho các câu hỏi mở (Q-57, 2026-09-30)

Chủ sản phẩm uỷ quyền quyết các câu hỏi mở theo nguyên tắc **an toàn cao nhất**: giữa hai phương án, chọn phương án fail-closed và khó dùng sai hơn, kể cả khi nó tốn công hơn. Các quyết định dưới đây **đã được gộp vào §3–§8**; mục này giữ lại làm hồ sơ quyết định (Q-57). Chấp thuận RFC vẫn cần chữ ký kỹ thuật trưởng (`CONTRIBUTING.md` §3).

1. **`pixel_format`** là enum đóng: `yuyv`, `mjpeg`, `rgb565`, `rgb888`, `gray8`; thêm giá trị cần RFC. *Vì sao:* so khớp `[requires]` phải tất định.
2. **Cú pháp dữ kiện** trong `agent.toml`: `[vision] model = "<tệp>"` và mỗi dữ kiện là `[vision.facts.<tên>]` với `label`, `zone` (khai ở `[vision.zones]`), `kind` ∈ {`present` → `bool`, `count` → `numeric` (số nguyên ≥ 0), `confidence` → `numeric` trong [0, 1]} và `min_frames`. Không có `bands`: mọi ngưỡng trên số đếm và độ tin cậy nằm trong tiêu chí `numeric` của gate (Q-54, RFC-0009 §1). Tên dữ kiện trùng tên tiêu chí của gate. `present` cần `min_frames` khung liên tiếp (mặc định 3, tối thiểu 2); `confidence` lấy **giá trị nhỏ nhất** trong cửa sổ. *Vì sao:* một khung nhiễu không được mở khoá cửa; lấy min là bảo thủ.
3. **Một đường cho độ tin cậy:** chỉ tiêu chí `numeric` (RFC-0009). `neuroedge build` từ chối (`AgentManifestError`, NE3002) gate dùng `confidence_gte` trên tiêu chí mà `agent.toml` khai là dữ kiện thị giác — gate không biết dữ kiện nào đến từ thị giác, chỉ lúc build mới có cả gate lẫn manifest. *Vì sao:* hai đường thì một đường sẽ bị quên khoá.
4. **Danh tính mô hình** (tên + sha256 của tệp mô hình) nằm ở **mỗi** sự kiện `perception`, kèm danh sách ở `metadata`. *Vì sao:* mô hình đổi giữa phiên vẫn truy được từng phán quyết.
5. **`vision_ref`** ghi cho **mọi khung trong cửa sổ** đã sinh ra dữ kiện của một phán quyết, không ghi khung ngoài cửa sổ. *Vì sao:* đủ để hậu kiểm, không phình vết ghi.
6. **Tương đương.** Camera ảo trong `sim` phát lại chuỗi khung đã ghi **và** kết quả `perception` đã ghi; `verify` so phán quyết giữa các target từ cùng sự kiện `perception`. Suy luận của mô hình được kiểm riêng: với mỗi sha256 mô hình, kết quả trên từng target phải khớp kết quả golden trên host trong sai số khai ở bo mạch; vượt sai số ⇒ `SafetyRegressionError` (NE4002). *Vì sao:* tách "gate quyết giống nhau" khỏi "model thấy giống nhau", cả hai đều phải chứng minh.
7. **Mất camera hoặc mô hình, khung quá cũ** (quá `max_age_ms` của RFC-0009) ⇒ dữ kiện chưa quyết ⇒ BLOCK; không nội suy từ khung trước.
