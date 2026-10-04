# RFC-0012: Nguyên thủy `vision.in` và bằng chứng nhận thức thị giác

| | |
|:---|:---|
| **Mã RFC** | 0012 |
| **Tiêu đề** | `vision.in` (năng lực bo mạch), dữ kiện gõ kiểu do maker khai từ nhãn mô hình, bằng chứng trong vết ghi, tương đương giữa các target |
| **Hợp đồng bị ảnh hưởng** | `board.v1` *(khoá `vision_in`, gồm sai số suy luận §3f)* · khối `[vision]` của `agent.toml` *(không có lược đồ trong `schemas/`; kiểm ở `neuroedge build`)* · quy ước sự kiện `perception` thị giác và lint ngữ nghĩa vết ghi *(không đổi `trace.v1`: `events[].data` là `object` tự do, `metadata` mở — §4)* · **không** đụng `gate.v1` · `neuroedge-prd.md` Phụ lục B: nới nguyên nhân của ba dòng có sẵn, **không mã mới** (§4) |
| **Yêu cầu PRD liên quan** | FR-HAL-01, FR-HAL-04, FR-HAL-05, FR-CI-02, FR-MDL-04, FR-MDL-07, NFR-PRIV-01, NFR-PRIV-03 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-09-30 |
| **Trạng thái** | ✅ Đã chấp thuận (2026-10-01) — kỹ thuật trưởng ký trên PR #79; sửa theo review 2026-10-01 (§9, Q-62); hiện thực trong PR thứ hai |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (chạm `board.v1`, quyền riêng tư camera, ranh giới nhận thức/thẩm quyền) |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3 — sửa `schemas/board.v1.json`. Task: TSK-V1b-07 (RFC này) và
> TSK-V1b-01, TSK-V1b-02, TSK-V1b-03, TSK-V1b-04, TSK-V1b-05, TSK-V1b-06, TSK-V1b-08, TSK-I3a-01. Đây là RFC mà RFC-0002 §9.1 và §9.2 hoãn lại; đầu vào đã biết nằm ở đó. Quyết
> định nền: `neuroedge-prd.md` §15 Q-52, Q-53 (camera có mặt trên cả ba target; bo mạch ESP32-S3 có
> camera), **Q-54** (thị giác → dữ kiện do maker khai, gate khoá ngưỡng bằng tiêu chí `numeric`, **không
> có ngữ nghĩa gate riêng cho thị giác**), Q-55, Q-57, **Q-61** (§9).

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
tolerance = { score_abs = 0.03, box_iou_min = 0.85 }
```

- `fps` là `number` (7,5 · 29,97), không phải số nguyên; cảm biến nhiều chế độ nên `modes[]` là mảng bắt buộc (ít nhất một phần tử).
- `pixel_format` là **enum đóng**: `yuyv`, `mjpeg`, `rgb565`, `rgb888`, `gray8`; thêm giá trị cần RFC (§9.1).
- `vision_in` khai thêm **sai số suy luận** cho phép so với golden trên host, dùng ở §3f (§9.6, §9.9). Trường `tolerance = { score_abs, box_iou_min }`, áp dụng một giá trị chung cho mọi mô hình của bo mạch. Lược đồ `board.v1` đặt trần cứng: `score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`. Bo mạch khai sai số vượt trần cứng bị từ chối bằng `BoardCapabilityError` (`NE3001`) lúc nạp bo mạch.
- Bo camera cho `esp32s3` đã chọn: M5Stack CoreS3 (Q-61), profile `esp32s3-cores3`. Bo gồm ESP32-S3, flash 16 MB, PSRAM 8 MB, camera GC0308 0,3 MP (VGA), 2 mic qua ES7210, loa 1 W qua ampli AW88298, màn 2" 320×240 cảm ứng, IMU BMI270, cảm biến LTR-553, cổng Grove và M5-Bus. Cảm biến GC0308 tối đa VGA nên ví dụ `modes` của bo này có 640×480. Bo mặc định của `esp32s3` vẫn là `esp32s3-box-3`. Ghi số đo SRAM/PSRAM theo Q-3 là điều kiện bắt buộc (TSK-I3a-01).
- Không khai bộ tăng tốc (`accelerator`) trong RFC này: mô hình và NPU thuộc cấu hình agent (TSK-V1b-03, TSK-V1b-05), không thuộc hợp đồng bo mạch.

### 3b. So khớp với `[requires]`

Agent khai yêu cầu tối thiểu, bo mạch thoả nếu **tồn tại ít nhất một chế độ** đủ mọi ngưỡng:

```toml
[requires]
"vision.in" = { min_width = 640, min_height = 480, min_fps = 10.0, pixel_formats = ["yuyv", "mjpeg"] }
```

Ví dụ `min_width = 640, min_height = 480` vẫn đạt trên bo `esp32s3-cores3` với camera GC0308 VGA.

`neuroedge build` (`engine/compiler.py`) từ chối bo mạch không có chế độ nào thoả bằng `BoardCapabilityError` (`NE3001`), lỗi ba phần nêu chế độ gần nhất (FR-HAL-05). So khớp tất định vì `pixel_format` là enum đóng.

### 3c. Từ nhãn mô hình tới dữ kiện gõ kiểu (Q-54, §9.2–9.3)

**Maker** khai trong `agent.toml` nhãn nào thành dữ kiện nào; **gate** khoá ngưỡng. Ví dụ — mở cổng khi có người đứng ở cổng, đóng cổng khi không còn ai:

```toml
# agent.toml — maker khai
[vision]
model = "models/person-det.tflite"

[vision.zones]
gate_area = [0.25, 0.40, 0.75, 1.00]   # [x0, y0, x1, y1] chuẩn hoá trong [0, 1], x0 < x1, y0 < y1

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
  person_at_gate:    { type: bool, instructions: "Có người trong vùng cổng" }
  people_at_gate:    { type: numeric, unit: count, range: { min: 0, max: 50 }, max_age_ms: 300,
                       instructions: "Số người trong vùng cổng" }
  person_confidence: { type: numeric, unit: ratio, range: { min: 0, max: 1 }, max_age_ms: 300,
                       instructions: "Điểm tin cậy của nhãn person trong vùng cổng" }
allow_when:
  people_at_gate: { lte: 0 }
  person_confidence: { lte: 0.10 }      # bắt buộc kèm confidence để mang max_age_ms, chống đứng hình
```

**Luật dữ kiện:**

| Trường | Luật |
|:---|:---|
| `[vision] model` | Một tệp mô hình; danh tính = tên + sha256 của tệp (§3d) |
| `kind` | `present` → `bool` · `count` → `numeric` (số nguyên ≥ 0) · `confidence` → `numeric` trong `[0, 1]`. Không có `level`/`choice`, không có `bands` |
| Tên dữ kiện | Trùng tên tiêu chí của gate; kiểu tiêu chí cùng tên phải khớp `kind` |
| `zone` | Phải khai ở `[vision.zones]`. Vùng là hình chữ nhật chuẩn hoá `[x0, y0, x1, y1]` trong `[0, 1]`, `x0 < x1`, `y0 < y1`. Bản này chỉ hỗ trợ hình chữ nhật, đa giác cần RFC sau |
| `min_frames` | Mặc định 3, tối thiểu 2. "Liên tiếp" tính theo số thứ tự khung của camera; mất một khung (nhảy số thứ tự) ⇒ cửa sổ bắt đầu lại. Chưa đủ khung liên tiếp ⇒ chưa quyết ⇒ BLOCK |
| Lượng giá cửa sổ | Lượng giá tiêu chí trên từng khung của cửa sổ `min_frames` rồi AND: mọi khung đều phải thoả. Tương đương dùng giá trị nhỏ nhất cho `gt`/`gte` và lớn nhất cho `lt`/`lte`, áp cho cả `confidence` lẫn `count` |
| `present` | Ngưỡng điểm để tính `present` là hằng `PRESENT_SCORE_FLOOR = 0.5` ghim trong mã nhận thức và ghi trong vết ghi, không do maker khai; ngưỡng an toàn thật vẫn là tiêu chí `confidence` đi kèm của gate. Dữ kiện `present` (hoặc `count`) của một nhãn bắt buộc phải đi kèm tiêu chí `numeric` `confidence` của cùng nhãn, cùng vùng, trong `allow_when` trong gate; thiếu ⇒ `neuroedge build` và lúc nạp agent từ chối |

**Không có ngưỡng nào trong `agent.toml`.** Mọi ngưỡng trên số đếm và độ tin cậy nằm trong tiêu chí `numeric` của gate (Q-54, RFC-0009 §1). Maker chọn *nhãn nào thành dữ kiện nào*; **maker không chọn được ngưỡng an toàn**. Không có toán tử gate riêng cho thị giác: mọi thứ đi qua `bool`/`numeric`.

**`present` và `count` không được đứng một mình.** Tiêu chí `bool` không có tuổi (`max_age_ms`). Nếu gate cho qua khi `present: false` (hoặc `people_at_gate: { lte: 0 }`, ví dụ đóng cổng khi không thấy người) mà camera bị đứng hình lặp lại khung cũ, gate sẽ cho qua sai trái. Do đó, gate dùng dữ kiện thị giác `present` (hoặc `count`) của một nhãn bắt buộc phải có kèm tiêu chí `numeric` `confidence` của cùng nhãn **và cùng vùng**, nằm trong `allow_when` của chính gate đó — tiêu chí chỉ khai ở `evaluate` mà không có trong `allow_when` thì walker không lượng giá, nên không được tính. Nhờ đó gate khoá ngưỡng và `max_age_ms`, đúng Q-54. Thiếu ⇒ `neuroedge build` và lúc nạp agent từ chối. Ngoài ra, tầng nhận thức có một trần tuổi khung cố định 1000 ms trong mã, không cấu hình được, ghi trong vết ghi: khung cũ nhất quá 1000 ms ⇒ dữ kiện chưa quyết ⇒ BLOCK. Ngưỡng điểm để tính `present` là hằng `PRESENT_SCORE_FLOOR = 0.5` ghi trong vết ghi, không do maker khai.

**Giá trị của dữ kiện thị giác trên một khung.** `confidence` = điểm cao nhất của nhãn trong vùng; không có phát hiện nào ⇒ `0.0` (vắng mặt là điểm 0, không phải "chưa quyết"). `count` = số phát hiện của nhãn trong vùng có điểm ≥ `PRESENT_SCORE_FLOOR`. `present` = `count ≥ 1`. Nhờ vậy ví dụ `close_gate` (`person_confidence: { lte: 0.10 }`) có nghĩa xác định: mọi khung trong cửa sổ đều không có phát hiện `person` nào trong vùng với điểm trên 0,10.

**Một đường cho độ tin cậy.** Gate dùng `confidence_gte` trên tiêu chí mà `agent.toml` khai là dữ kiện thị giác bị từ chối cả lúc `neuroedge build` lẫn lúc nạp agent. `gate lint` không làm được việc này: gate không biết dữ kiện nào đến từ thị giác, chỉ lúc build hoặc nạp agent mới có cả gate lẫn manifest. (`confidence_gte` trên tiêu chí `numeric` thì `gate lint` đã từ chối, RFC-0009 §3a.)

**Từ chối bằng `AgentManifestError` (`NE3002`):** `kind` ngoài ba giá trị; khoá lạ trong `[vision.facts.*]`, kể cả `bands`; `min_frames` < 2; `zone` chưa khai hoặc sai định dạng toạ độ `[x0, y0, x1, y1]`; kiểu tiêu chí cùng tên không khớp `kind`; gate dùng `confidence_gte` trên dữ kiện thị giác (từ chối cả lúc build và nạp agent); gate dùng `present` hoặc `count` mà thiếu tiêu chí `numeric` `confidence` cùng nhãn (từ chối cả lúc build và nạp agent). Gom vào `BuildFailed` (`NE3003`) như mọi vấn đề build khác.

### 3d. Vết ghi

Mỗi dữ kiện thị giác lượng giá cho một phán quyết ghi một sự kiện nhóm `perception` (Phụ lục C.1 của `neuroedge-proposal.md`; tên sự kiện ghi ở `docs/spec/simulation_coverage.md` §3 — §8):

```json
{ "offset_ms": 1840, "type": "vision_fact", "data": {
    "fact": "person_at_gate", "kind": "present", "min_frames": 3, "value": true, "age_ms": 140,
    "model": { "name": "person-det", "sha256": "…" },
    "frames": [
      { "frame_seq": 101, "vision_ref": { "sha256": "…", "size": 61440 }, "captured_ms": 1700, "labels": [{ "label": "person", "zone": "gate_area", "score": 0.93 }] },
      { "frame_seq": 102, "vision_ref": { "sha256": "…", "size": 61312 }, "captured_ms": 1767, "labels": [ … ] },
      { "frame_seq": 103, "vision_ref": { "sha256": "…", "size": 61500 }, "captured_ms": 1833, "labels": [ … ] } ] } }
```

- **Danh tính mô hình** (tên + sha256 của tệp mô hình) nằm ở **mỗi** sự kiện `perception` thị giác, kèm danh sách mọi mô hình đã dùng trong phiên ở `metadata` (§9.4). Mô hình đổi giữa phiên vẫn truy được từng phán quyết.
- **`vision_ref` = `{ sha256, size }`** ghi cho **mọi khung trong cửa sổ** đã sinh ra dữ kiện của phán quyết, không ghi khung ngoài cửa sổ (§9.5). **Không nhúng ảnh thô.** Mốc `captured_ms` và `frame_seq` (số thứ tự khung camera) của từng khung được ghi để `replay` tính lại tuổi khung và kiểm tra tính liên tiếp đúng như lúc chạy (RFC-0009 §3c).
- Nhãn, vùng và điểm của từng khung trong cửa sổ được ghi; đó là thứ `replay` dùng để tái hiện phán quyết (FR-CI-02). Một mã băm khung hình không replay được.
- **Tuổi dữ kiện thị giác:** Thời điểm lượng giá = offset của sự kiện phán quyết trên cùng trục thời gian đơn điệu của phiên với mốc đọc của HAL. Vết ghi ghi cả mốc đọc HAL, `captured_ms` lẫn `age_ms`; `replay` tính lại và so sánh. `age_ms < 0` (mốc đọc sau thời điểm lượng giá) ⇒ BLOCK `criterion_unavailable`. Với thị giác, tuổi của cửa sổ là tuổi của khung cũ nhất trong cửa sổ: `age_ms = offset_ms - captured_ms_oldest`.
- **Trần tuổi cố định và ngưỡng điểm:** Tầng nhận thức có trần tuổi khung cố định trong mã là 1000 ms, không cấu hình được, ghi trong vết ghi; khung cũ nhất quá 1000 ms ⇒ dữ kiện chưa quyết ⇒ BLOCK. Ngưỡng điểm để tính `present` là hằng `PRESENT_SCORE_FLOOR = 0.5` ghi trong vết ghi, không do maker khai. **Khung lặp:** hai khung liền nhau trong cửa sổ có cùng `vision_ref.sha256` ⇒ coi camera đứng hình ⇒ dữ kiện chưa quyết ⇒ BLOCK, kể cả khi driver gắn mốc `captured_ms` mới cho khung lặp.
- `trace.v1` **không đổi** (§4). Lint ngữ nghĩa ở `python/neuroedge/trace.py` (TSK-V1b-08), vi phạm ⇒ `TraceValidationError` (`NE4001`):
  - `sha256` (của `vision_ref` và của `model`) khớp `^[0-9a-f]{64}$`;
  - `uri` chỉ khi `metadata.raw_capture == true`; từ chối blob base64 trong `data`;
  - sự kiện `perception` thị giác thiếu `model.name`/`model.sha256`, hoặc sha256 mô hình không có trong danh sách ở `metadata`;
  - số phần tử `frames` khác `min_frames` của sự kiện (thiếu khung trong cửa sổ, hay thừa khung ngoài cửa sổ);
  - `frame_seq` không liên tiếp (nhảy số thứ tự khung của camera);
  - `age_ms` âm hoặc không khớp với mốc đọc HAL và khung cũ nhất.

### 3e. Fail-closed (§9.7)

Kiểm theo thứ tự, mọi nhánh đều BLOCK, **không nội suy từ khung trước**, không có giá trị mặc định "không thấy người":

| Tình huống | `reason` |
|:---|:---|
| Mất camera, mất mô hình, mô hình không trả lời | `criterion_unavailable` |
| Hai khung liền nhau trong cửa sổ có cùng `vision_ref.sha256` (camera đứng hình, driver vẫn gắn mốc mới) | `criterion_unavailable` |
| Khung quá cũ: tuổi của khung cũ nhất trong cửa sổ > `max_age_ms` của tiêu chí `numeric` đi kèm (RFC-0009 §3c) hoặc > trần 1000 ms cố định của tầng nhận thức; mốc đọc sau thời điểm lượng giá (`age_ms < 0`) | `criterion_unavailable` |
| Cửa sổ chưa đủ `min_frames` khung liên tiếp: mất khung (nhảy số thứ tự `frame_seq` camera); kết quả rác bị tầng nhận thức loại trước khi tới gate (nhãn ngoài tập nhãn của mô hình, `count` âm hoặc không nguyên); thiếu tiêu chí `confidence` đi kèm cho `present`/`count` | `criterion_unavailable` |
| Đủ khung, mọi khung có dữ kiện, nhưng ít nhất một khung không thoả khoảng của `allow_when` (lượng giá từng khung rồi AND) | `condition_not_met` |
| Điểm hoặc số đếm NaN, ±inf, ngoài `range` của tiêu chí `numeric` | `value_out_of_range` (RFC-0009 §9.1) |

Nhờ bắt buộc tiêu chí `numeric` `confidence` đi kèm `present` và tính tuổi theo khung cũ nhất, tình huống camera đứng hình lặp lại khung "không có người" sẽ bị chặn: `age_ms` của khung cũ nhất vượt quá `max_age_ms` (hoặc trần 1000 ms), dẫn đến BLOCK `criterion_unavailable`, không thể gây ALLOW sai trái cho các lệnh nguy hiểm (như đóng cổng).

### 3f. Tương đương giữa các target (§9.6)

Hai mệnh đề, kiểm riêng, cả hai đều phải chứng minh:

1. **Gate quyết giống nhau.** Camera ảo trong `sim` (TSK-V1b-02) phát lại chuỗi khung đã ghi **và** kết quả `perception` đã ghi; `neuroedge verify` so phán quyết giữa các target từ cùng sự kiện `perception`. Lệch ⇒ `SafetyRegressionError` (`NE4002`).
2. **Mô hình thấy giống nhau.** Với mỗi sha256 mô hình, kết quả suy luận trên từng target phải khớp kết quả golden trên host trong sai số khai ở `vision_in` của bo mạch (`tolerance = { score_abs, box_iou_min }`, §3a). Lược đồ `board.v1` đặt trần cứng: `score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`, ngăn việc bo mạch khai sai số khống làm rỗng phép kiểm tương đương. Vượt sai số ⇒ `SafetyRegressionError` (`NE4002`). Golden suy luận và Action CI cho khung hình: TSK-V1b-04.

### 3g. Điểm đã chốt ở review 2026-10-01

Bốn điểm mở trước đây do chủ sản phẩm chốt theo nguyên tắc an toàn cao nhất (Q-57, Q-62, §9); kỹ thuật trưởng xác nhận khi ký RFC:

1. **Hình dạng vùng:** Hình chữ nhật chuẩn hoá `[x0, y0, x1, y1]` trong `[0, 1]`, thoả `x0 < x1`, `y0 < y1`. Chỉ hỗ trợ hình chữ nhật ở bản này; vùng đa giác cần RFC sau.
2. **Sai số suy luận:** Khai ở `vision_in` dưới trường `tolerance = { score_abs, box_iou_min }`, áp dụng một giá trị chung cho mọi mô hình của bo mạch. Lược đồ `board.v1` đặt trần cứng: `score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`. Bo mạch khai vượt trần cứng bị từ chối lúc nạp bo mạch bằng `BoardCapabilityError` (`NE3001`).
3. **Cách gộp `count` và dữ kiện qua cửa sổ:** Lượng giá trên từng khung của cửa sổ rồi AND (mọi khung đều phải thoả tiêu chí gate). Tương đương với việc dùng giá trị lớn nhất cho `lte`/`lt` và giá trị nhỏ nhất cho `gte`/`gt`, áp cho cả `count` lẫn `confidence`. Rớt khung (nhảy số thứ tự khung của camera) làm cửa sổ bắt đầu lại từ đầu.
4. **Tuổi khung và an toàn cho dữ kiện `present`:** Dữ kiện `present` (hoặc `count`) bắt buộc phải đi kèm tiêu chí `numeric` `confidence` của cùng nhãn, cùng vùng, trong `allow_when` trong gate (khoá ngưỡng và `max_age_ms`, Q-54). Tuổi của cửa sổ thị giác là tuổi của khung cũ nhất trong cửa sổ. Tầng nhận thức đặt thêm trần tuổi cố định 1000 ms trong mã. Ngưỡng điểm để tính `present` là hằng số cố định ghi trong vết ghi.

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — không profile nào trong `boards/` khai `vision_in`, không agent nào trong `fixtures/agents/` có khối `[vision]` |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có — profile khai `vision_in` đúng hình dạng (`modes[]`, enum `pixel_format`, `tolerance = { score_abs, box_iou_min }` trong trần cứng). Bốn điểm mở đã chốt (§3g), `board.v1` sẵn sàng đóng băng. Profile camera cho `esp32s3` là M5Stack CoreS3 (`esp32s3-cores3`, Q-61) |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không. `trace.v1` không đổi: `events[].data` chỉ ràng buộc `"type": "object"` và `metadata` có `additionalProperties: true`, nên `model`, `frames`, `vision_ref` và danh sách mô hình ở `metadata` validate qua; luật của §3d là lint ngữ nghĩa ở `trace.py`, không phải lược đồ (RFC-0002 §9.2) |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không — chúng không có sự kiện thị giác, nên lint mới không chạm chúng |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào; ba gate mẫu thị giác (TSK-V1b-06) vào `digests.lock` bằng PR thường |
| Bố cục `NETR` hoặc walker C phải đổi? | Không riêng RFC này; dùng nút `numeric` của RFC-0009 |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không |

**Mã lỗi** (`neuroedge-prd.md` Phụ lục B): RFC này không thêm mã. Mọi lớp dùng đã có trong `python/neuroedge/errors.py`; khi chấp thuận, cột *Nguyên nhân* của ba dòng được nới:

| Lớp | Nguyên nhân thêm |
|:---|:---|
| `AgentManifestError` (`NE3002`) | Khối `[vision]` sai (§3c), gate dùng `confidence_gte` trên dữ kiện thị giác (từ chối cả lúc build và nạp agent), hoặc gate dùng `present`/`count` mà thiếu tiêu chí `numeric` `confidence` cùng nhãn (từ chối cả lúc build và nạp agent) |
| `TraceValidationError` (`NE4001`) | Lint ngữ nghĩa thị giác (§3d) — dòng hiện chỉ nêu lược đồ và dòng UART; kiểm tra `frame_seq` liên tiếp, tuổi khung cũ nhất khớp `age_ms` không âm |
| `SafetyRegressionError` (`NE4002`) | Suy luận mô hình trên một target lệch golden host quá sai số khai ở bo mạch (§3f) |

`BoardCapabilityError` (`NE3001`): Nới thêm nguyên nhân khai `tolerance` vượt trần cứng (`score_abs > 0.05` hoặc `box_iou_min < 0.8`) bên cạnh yêu cầu năng lực bo mạch không cung cấp (§3b). `criterion_unavailable` và `value_out_of_range` là lý do phán quyết (RFC-0009), không phải exception.

## 5. Ảnh hưởng an toàn

- **Gate không lỏng hơn và không có ngữ nghĩa thị giác mới** (Q-54): `gate.v1`, phân giải, năm nguyên tắc không đổi. Ràng buộc của `neuroedge-design-phase2.md` §2.2 — thị giác quy về các kiểu dữ kiện gate đã biết lượng giá, ngưỡng tin cậy khoá bằng `numeric` — được giữ nguyên.
- **Nhận thức không thành thẩm quyền:** mô hình chỉ cấp dữ kiện; mọi ngưỡng trên số đếm và độ tin cậy do gate khoá và chỉ thu hẹp được khi kế thừa. Maker nới ngưỡng bằng `agent.toml` **không được** vì ngưỡng không nằm ở đó (`bands` bị từ chối).
- **Một đường cho độ tin cậy:** `confidence_gte` trên dữ kiện thị giác bị từ chối cả lúc `neuroedge build` lẫn lúc nạp agent, nên không có đường thứ hai để quên khoá (§3c).
- **`present` và `count` không đứng một mình:** Gate dùng `present` hoặc `count` bắt buộc phải kèm tiêu chí `numeric` `confidence` cùng nhãn, cùng vùng, trong `allow_when` mang `max_age_ms`. Nhờ đó loại bỏ rủi ro camera đứng hình lặp "không có người" cho phép qua cổng `close_gate` viết bằng `present: false`.
- **Lượng giá từng khung rồi AND:** Tiêu chí được lượng giá trên từng khung trong cửa sổ `min_frames` rồi AND: bảo thủ đúng hướng cho cả `gte`/`gt` và `lte`/`lt`, áp dụng cho cả `confidence` và `count`. Mất khung (nhảy số thứ tự camera) làm cửa sổ bắt đầu lại.
- **Không nội suy và kiểm tuổi thống nhất:** Mất camera, mất mô hình, khung quá cũ ⇒ BLOCK (§3e). Tuổi cửa sổ tính theo khung cũ nhất trong cửa sổ, kết hợp trần tuổi cứng 1000 ms của tầng nhận thức. Mốc đọc sau thời điểm lượng giá (`age_ms < 0`) ⇒ BLOCK.
- **Riêng tư:** không khung thô trong vết ghi theo mặc định; lưu ảnh thô phải bật tường minh (`metadata.raw_capture`). Chỉ khung trong cửa sổ để lại `vision_ref`. Quy tắc chặt hơn micro, không lỏng hơn.
- **Danh tính mô hình ở mỗi sự kiện:** đổi mô hình là đổi hành vi; vết ghi phải cho biết mô hình nào ra kết luận nào, kể cả khi mô hình đổi giữa phiên.
- **Tương đương hai tầng và trần sai số (§3f):** "Gate quyết giống nhau" không chứng minh "mô hình thấy giống nhau"; cả hai đều được kiểm. Lược đồ `board.v1` khống chế trần cứng sai số suy luận (`score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`), ngăn việc bo mạch khai sai số khống làm rỗng phép kiểm tương đương.
- **Rủi ro còn lại:** mô hình sai với điểm cao (nhãn sai tự tin). Giảm bằng ngưỡng số ở gate, cửa sổ nhiều khung, và — với hành động không hoàn tác — `on_block: ask`; không loại được hoàn toàn. Bốn điểm mở trước đây đã chốt dứt điểm ở §3g (review 2026-10-01, Q-62).
- **Ngân sách bộ nhớ `esp32s3`:** Bo camera đã chọn là M5Stack CoreS3 (`esp32s3-cores3`, Q-61) với 16 MB flash, 8 MB PSRAM, camera GC0308 VGA 640×480. Đo đạc SRAM/PSRAM trên bo mạch thật theo Q-3 là điều kiện bắt buộc (TSK-I3a-01).

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Ngữ nghĩa gate riêng cho bằng chứng thị giác (vùng cấm, đếm người) | Q-54: phá tính xác định của rule engine, cần RFC `gate.v1` lớn; quy về dữ kiện gõ kiểu đủ cho ca sử dụng ưu tiên |
| Maker tự đặt ngưỡng trong `agent.toml` (kể cả `bands` cho `count`) | Ý nghĩa an toàn ngoài gate, `gate lint` không thấy; cùng lý do RFC-0005 §6 và RFC-0009 §1 |
| Cho phép `confidence_gte` song song với tiêu chí `numeric` | Hai đường thì một đường sẽ bị quên khoá (§9.3) |
| Chỉ từ chối `confidence_gte` trên dữ kiện thị giác lúc build mà bỏ qua lúc nạp agent | Agent nạp động hoặc phân phối ngoài có thể lách qua; phải từ chối cả lúc build và lúc nạp agent |
| Kiểm `confidence_gte` trên dữ kiện thị giác ở `gate lint` | Gate không biết dữ kiện nào đến từ thị giác; chỉ build hoặc nạp agent có cả gate lẫn manifest |
| Quy tắc gộp "confidence = min", "count = min" qua cửa sổ | Phụ thuộc hướng (min đúng cho `gte`, sai cho `lte`, ví dụ `count lte 0`); thay bằng "lượng giá từng khung rồi AND" (§9.2) |
| `present` hoặc `count` đứng một mình không kèm tiêu chí `confidence` | Tiêu chí `bool` không có `max_age_ms`; camera đứng hình lặp "không có người" cho phép ALLOW `close_gate` nguy hiểm; bác bỏ (§3c) |
| `present` quyết từ một khung; `confidence` lấy trung bình hoặc khung cuối | Một khung nhiễu mở khoá cửa; trung bình che khung yếu (§9.2) |
| Cho phép bo mạch tự do khai sai số suy luận không có trần cứng | Bo mạch có thể khai sai số quá rộng làm phép kiểm tương đương target trở nên rỗng; bác bỏ (§3a) |
| `fps` nguyên, `pixel_format` chuỗi tự do | Không biểu diễn 7,5 fps; không so khớp tất định (RFC-0002 §9.1; §9.1) |
| Mở rộng `sensor.read` | Không mang luồng khung; xem lập luận ở RFC-0007 §2 |
| Ghi mọi khung vào vết ghi | Vi phạm NFR-PRIV-01, NFR-PRIV-03; 30 fps ≈ 13 MB/giờ chỉ riêng băm và siêu dữ liệu |
| Chỉ ghi `vision_ref` của khung cuối | Không hậu kiểm được luật `min_frames` và lượng giá từng khung (§9.5) |
| Danh tính mô hình chỉ ở `metadata` | Mô hình đổi giữa phiên thì không truy được phán quyết nào do mô hình nào (§9.4) |
| Nội suy từ khung trước khi mất camera hay khung quá cũ | Camera treo trông như "không có gì thay đổi" (§9.7, RFC-0009 §9.5) |
| `verify` chỉ so phán quyết | Không chứng minh mô hình cho cùng kết quả trên mọi target (§9.6) |

## 7. Bằng chứng kiểm chứng

Mỗi dòng nêu quyết định §9 nó phủ. Corpus theo luật khép kín hai chiều (`CONTRIBUTING.md` §3).

- [ ] **Bo mạch (§9.1, §9.9, §9.11):** ví dụ hợp lệ — profile `linux` và profile bo mạch `esp32s3-cores3` (M5Stack CoreS3, GC0308 VGA 640×480) khai `vision_in` có `modes` và `tolerance` hợp lệ; phản chứng — `fps` chuỗi, `modes` rỗng, `pixel_format` ngoài năm giá trị enum, thiếu `tolerance`, `tolerance.score_abs > 0.05` hoặc `tolerance.box_iou_min < 0.8` ⇒ `BoardCapabilityError` (`NE3001`)
- [ ] **Đo đạc bộ nhớ M5Stack CoreS3 (TSK-I3a-01, Q-3, §9.11):** chạy mô hình trên `esp32s3-cores3` với camera GC0308 (VGA 640×480), ghi nhận số đo SRAM và PSRAM còn lại, đảm bảo không tràn heap
- [ ] **`[requires]` (§3b, §9.11):** agent mẫu có `[requires] "vision.in"` với `min_width = 640, min_height = 480` so khớp thành công với `esp32s3-cores3`; bo mạch không có chế độ thoả (đòi 1280×720) ⇒ `BoardCapabilityError` nêu chế độ gần nhất
- [ ] **Cú pháp dữ kiện và vùng (§9.2, §9.9)** — `python/tests/test_compiler.py`: agent mẫu có `[vision]` hợp lệ build được; vùng chữ nhật chuẩn hoá `[x0, y0, x1, y1]`; mỗi lỗi sau ⇒ `AgentManifestError` (`NE3002`): `kind` lạ, `bands`, `min_frames = 1`, `zone` chưa khai, toạ độ ngoài `[0, 1]`, `x0 >= x1`, `y0 >= y1`, vùng dạng đa giác
- [ ] **Ràng buộc tiêu chí đi kèm (§9.10):** gate dùng dữ kiện `present` hoặc `count` mà thiếu tiêu chí `numeric` `confidence` cùng nhãn ⇒ `neuroedge build` và lúc nạp agent từ chối bằng `AgentManifestError` (`NE3002`)
- [ ] **Một đường cho độ tin cậy (§9.3):** gate dùng `confidence_gte` trên dữ kiện thị giác **qua** `gate lint` nhưng bị từ chối cả lúc `neuroedge build` lẫn lúc nạp agent bằng `AgentManifestError` (`NE3002`) — ghim ranh giới lint/build/load
- [x] **Gộp theo khung và rớt khung (§9.2, §9.9):** cửa sổ `min_frames = 3`: 3 khung liên tiếp thoả mãn ⇒ ALLOW. Nhảy số thứ tự khung camera (`frame_seq`) ⇒ cửa sổ reset ⇒ BLOCK `criterion_unavailable`. Lượng giá từng khung rồi AND: với `count` gate `lte: 0`, chuỗi `[0, 1, 0]` ⇒ BLOCK, chuỗi `[0, 0, 0]` ⇒ ALLOW; với `confidence` gate `gte: 0.85`, chuỗi `[0.90, 0.80, 0.90]` ⇒ BLOCK, chuỗi `[0.86, 0.90, 0.88]` ⇒ ALLOW *(Đã làm: `python/tests/test_vision_facts.py`: `test_three_good_frames_allow_the_open_gate`, `test_confidence_gte_is_judged_on_every_frame`, `test_count_lte_zero_is_judged_on_every_frame`, `test_a_lost_frame_restarts_the_window`)*
- [x] **Tuổi khung và camera đứng hình (§9.7, §9.8, §9.10):** tuổi cửa sổ tính theo khung cũ nhất. Khung cũ nhất có `age_ms > max_age_ms` của `confidence` đi kèm ⇒ BLOCK `criterion_unavailable`. Khung cũ nhất > 1000 ms (trần nhận thức) ⇒ BLOCK `criterion_unavailable` dù `max_age_ms` của gate đặt lớn hơn. Mốc đọc HAL sau thời điểm lượng giá (`age_ms < 0`) ⇒ BLOCK `criterion_unavailable`. Camera đứng hình lặp "không có người" (`people_at_gate: { lte: 0 }` hoặc `person_at_gate: false`) ⇒ `confidence` đi kèm quá tuổi ⇒ BLOCK `criterion_unavailable`, không mở khoá sai. Hai khung liền nhau trong cửa sổ có cùng `vision_ref.sha256` (driver gắn `captured_ms` mới) ⇒ BLOCK `criterion_unavailable`. *(Đã làm: `test_vision_facts.py`: `test_a_window_older_than_the_ceiling_blocks_even_when_the_gate_allows_longer`, `test_a_window_older_than_the_gates_max_age_blocks_even_inside_the_ceiling`, `test_a_frame_read_after_the_instant_it_is_judged_blocks`, `test_a_camera_that_repeats_a_frame_is_frozen_whatever_time_it_stamps`, `test_a_frozen_camera_cannot_close_the_gate`; tuổi âm tới vết ghi: `test_vision_trace.py::test_a_refused_window_is_recorded_and_valid_even_short_or_in_the_future`)*
- [x] **Danh tính mô hình (§9.4)** — `fixtures/traces/invalid/` + `expected_errors.yaml`: sự kiện `perception` thị giác thiếu `model`, sha256 mô hình không có trong `metadata`; phiên đổi mô hình giữa chừng ⇒ mỗi phán quyết truy được mô hình của nó *(Đã làm: `fixtures/traces/invalid/vision_model_missing.json`, `vision_model_not_listed.json`, `vision_model_bad_sha256.json`; đổi mô hình giữa phiên: `test_vision_trace.py::test_a_model_swap_mid_session_leaves_every_verdict_traceable_to_its_model`)*
- [x] **`vision_ref` và tính liên tiếp (§9.5)** — `fixtures/traces/invalid/`: `frames` ít hơn và nhiều hơn `min_frames`; `sha256` sai dạng; `uri` khi không `raw_capture`; base64 trong `data`; `frame_seq` không liên tiếp; `age_ms` âm hoặc không khớp với mốc đọc HAL và khung cũ nhất *(Đã làm: `fixtures/traces/invalid/vision_frames_too_few.json`, `vision_frames_too_many.json`, `vision_ref_bad_sha256.json`, `vision_uri_without_raw_capture.json`, `vision_base64_blob.json`, `vision_image_field.json`, `vision_frame_seq_gap.json`, `vision_age_mismatch.json`, `vision_age_negative.json`; luật ở `docs/spec/vision.md` §5)*
- [ ] **Tương đương và trần sai số (§9.6, §9.9):** `verify` cho cùng phán quyết trên `sim`, `linux`, `esp32s3` từ cùng sự kiện `perception`. Suy luận lệch golden host trong sai số khai ở bo mạch (`score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`) ⇒ xanh; vượt sai số ⇒ `SafetyRegressionError` (`NE4002`) *(Một phần: nửa suy luận đã làm trên host — `python/tests/test_vision_golden.py`: suy luận giống hệt và lệch trong sai số ⇒ xanh; vượt `score_abs`, IoU dưới `box_iou_min`, thiếu/thừa phát hiện, golden của mô hình khác ⇒ từ chối; `neuroedge verify` chạy mọi golden `fixtures/vision/golden/` trên mọi bo mạch khai `vision_in` với sai số của bo đó. Còn mở: suy luận của mô hình thật trên NPU/`esp32s3` và so phán quyết trên `esp32s3` từ cùng sự kiện `perception`.)*
- [x] `replay` tái hiện phán quyết từ sự kiện `perception`, không cần khung hình, kiểm tra tuổi khung từ `captured_ms` và `age_ms` *(Đã làm: `test_vision_trace.py`: `test_replay_reproduces_an_allow_from_the_perception_events`, `test_replay_reproduces_a_block_and_its_reason`, `test_replay_reproduces_a_fail_closed_block`, `test_the_verdict_comes_from_the_recorded_labels_not_the_recorded_gate_fact` — mô hình bị cấm gọi trong lúc replay)*
- [ ] `neuroedge gate lint` và `neuroedge verify` xanh
- [ ] Bốn điểm mở của §3g đã chốt hoàn toàn theo review 2026-10-01 và có test tương ứng trước khi phê duyệt

## 8. Việc phải làm khi chấp thuận

- [x] Cập nhật `schemas/board.v1.json` (`vision_in`: `modes[]`, enum `pixel_format`, trường `tolerance = { score_abs, box_iou_min }` với trần cứng `score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`) — *đạt: `modes[]`, enum `pixel_format`, `tolerance` bắt buộc với trần cứng — `tests/test_board_fixtures.py` (`vision_*`)*
- [ ] Thêm profile bo mạch `esp32s3-cores3` (M5Stack CoreS3) cho ESP32-S3 có camera GC0308 VGA 640×480 (Q-61); tiến hành đo đạc SRAM/PSRAM theo Q-3 (TSK-I3a-01)
- [ ] Cập nhật Phụ lục C.1 trong `neuroedge-proposal.md`; FR-HAL-01 ở `neuroedge-prd.md`; Phụ lục B của `neuroedge-prd.md` — nới nguyên nhân ba dòng ở §4; `TODOS.md` #14 (cách sửa nằm ở RFC-0013)
- [x] `docs/spec/simulation_coverage.md`: tên sự kiện `perception` thị giác ở §3, dòng `vision.in` ở ma trận §2 *(Đã làm: `camera_unavailable` ở §3, mục `vision.in` ở ma trận §2; `docs/spec/camera.md`)*
- [x] `neuroedge-roadmap.md`: TSK-V1b-07 xong; mở TSK-V1b-01, TSK-V1b-02, TSK-V1b-03, TSK-V1b-04, TSK-V1b-05, TSK-V1b-06, TSK-V1b-08 *(Đã làm 2026-10-04: sáu dòng V1b-01 → V1b-08 trong roadmap; V1b-01 và V1b-04 còn 🟡, V1b-05 ⏳)*
- [x] `engine/compiler.py` và runtime nạp agent: khối `[vision]`, vùng hình chữ nhật `[x0, y0, x1, y1]`, từ chối `confidence_gte` trên dữ kiện thị giác cả lúc build và nạp agent, bắt buộc tiêu chí `numeric` `confidence` đi kèm `present`/`count`, so khớp `modes[]` *(Đã làm: `check_vision` và `_check_vision_in` trong `engine/compiler.py`; `[requires] "vision.in"` so khớp `modes[]` ở `hal/vision.py::Requirement`; phiên từ chối nạp khi camera không mở được — `tests/test_vision_camera.py`: `test_a_bound_no_mode_meets_is_refused_naming_the_closest_mode`, `test_confidence_gte_on_a_vision_fact_is_refused_one_road_for_confidence`, `test_present_without_its_confidence_pair_is_refused_a_bool_has_no_age`)*
- [x] `perception/vision/`: logic lượng giá từng khung rồi AND, kiểm tra `frame_seq` liên tiếp và reset cửa sổ khi rớt khung, tính tuổi cửa sổ theo khung cũ nhất, áp trần tuổi cố định 1000 ms của tầng nhận thức, ghim hằng số ngưỡng điểm `present` vào vết ghi *(Đã làm: `python/neuroedge/perception/vision/` (`facts.py`, `pipeline.py`); đặc tả `docs/spec/vision.md`)*
- [x] `python/neuroedge/trace.py`: lint ngữ nghĩa §3d (kiểm tra `frame_seq`, kiểm tra tuổi khung cũ nhất và `age_ms` không âm) *(Đã làm: `lint_vision` trong `python/neuroedge/trace.py`, 15 tệp phản chứng `fixtures/traces/invalid/vision_*.json`)*
- [ ] `python/neuroedge/hal/` (`linux.py`, `sim.py`), camera ảo trong `sim` (TSK-V1b-02), golden suy luận theo sha256 mô hình và kiểm sai số trong `verify` (TSK-V1b-04) *(Một phần — đã làm: `LinuxHAL.vision_in` qua V4L2 (`hal/v4l2.py`), `SimHAL.vision_in` + camera ảo `sim/vision/`, corpus `fixtures/traces/vision/` replay trên mọi bo khai `vision.in` (`neuroedge verify`). Chưa làm: golden suy luận và kiểm sai số (TSK-V1b-04); camera trên chip. Đã chạy trên kernel: `tests_linux/test_camera_v4l2.py` trên `vivid` (CI run 37153005998))*
- [ ] Fixture/test; cập nhật `docs/rfc/README.md` và `CHANGELOG.md`

## 9. Quyết định cho các câu hỏi mở (Q-57, 2026-09-30; Q-62, 2026-10-01)

Chủ sản phẩm uỷ quyền quyết các câu hỏi mở theo nguyên tắc **an toàn cao nhất**: giữa hai phương án, chọn phương án fail-closed và khó dùng sai hơn, kể cả khi nó tốn công hơn. Các quyết định dưới đây **đã được gộp vào §3–§8**; mục này giữ lại làm hồ sơ quyết định (Q-57). Chấp thuận RFC vẫn cần chữ ký kỹ thuật trưởng (`CONTRIBUTING.md` §3).

1. **`pixel_format`** là enum đóng: `yuyv`, `mjpeg`, `rgb565`, `rgb888`, `gray8`; thêm giá trị cần RFC. *Vì sao:* so khớp `[requires]` phải tất định.
2. **Cú pháp dữ kiện** trong `agent.toml`: `[vision] model = "<tệp>"` và mỗi dữ kiện là `[vision.facts.<tên>]` với `label`, `zone` (khai ở `[vision.zones]`), `kind` ∈ {`present` → `bool`, `count` → `numeric` (số nguyên ≥ 0), `confidence` → `numeric` trong [0, 1]} và `min_frames`. Không có `bands`: mọi ngưỡng trên số đếm và độ tin cậy nằm trong tiêu chí `numeric` của gate (Q-54, RFC-0009 §1). Tên dữ kiện trùng tên tiêu chí của gate. `present` cần `min_frames` khung liên tiếp (mặc định 3, tối thiểu 2). Gộp qua cửa sổ: lượng giá tiêu chí trên từng khung của cửa sổ `min_frames` rồi AND (mọi khung đều phải thoả); tương đương min cho `gte`/`gt` và max cho `lte`/`lt`, áp cho cả `confidence` lẫn `count`. "Liên tiếp" tính theo số thứ tự khung của camera, rớt khung ⇒ reset cửa sổ. *Vì sao:* quy tắc min chỉ đúng cho `gte`, sai cho `lte` (ví dụ `count lte 0`); AND từng khung là bảo thủ và đúng cho mọi chiều so sánh.
3. **Một đường cho độ tin cậy:** chỉ tiêu chí `numeric` (RFC-0009). `neuroedge build` và lúc nạp agent từ chối (`AgentManifestError`, NE3002) gate dùng `confidence_gte` trên tiêu chí mà `agent.toml` khai là dữ kiện thị giác — gate không biết dữ kiện nào đến từ thị giác, chỉ lúc build hoặc nạp agent mới có cả gate lẫn manifest. *Vì sao:* hai đường thì một đường sẽ bị quên khoá.
4. **Danh tính mô hình** (tên + sha256 của tệp mô hình) nằm ở **mỗi** sự kiện `perception`, kèm danh sách ở `metadata`. *Vì sao:* mô hình đổi giữa phiên vẫn truy được từng phán quyết.
5. **`vision_ref`** ghi cho **mọi khung trong cửa sổ** đã sinh ra dữ kiện của một phán quyết, không ghi khung ngoài cửa sổ. *Vì sao:* đủ để hậu kiểm, không phình vết ghi.
6. **Tương đương.** Camera ảo trong `sim` phát lại chuỗi khung đã ghi **và** kết quả `perception` đã ghi; `verify` so phán quyết giữa các target từ cùng sự kiện `perception`. Suy luận của mô hình được kiểm riêng: với mỗi sha256 mô hình, kết quả trên từng target phải khớp kết quả golden trên host trong sai số khai ở bo mạch (`tolerance = { score_abs, box_iou_min }`, trần cứng `score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`); vượt sai số ⇒ `SafetyRegressionError` (NE4002). *Vì sao:* tách "gate quyết giống nhau" khỏi "model thấy giống nhau", cả hai đều phải chứng minh.
7. **Mất camera hoặc mô hình, khung quá cũ** (quá `max_age_ms` của RFC-0009, tính theo khung cũ nhất trong cửa sổ) ⇒ dữ kiện chưa quyết ⇒ BLOCK; không nội suy từ khung trước.
8. **Tuổi dữ kiện thị giác** (review 2026-10-01, Q-62). Mốc đọc HAL so với thời điểm lượng giá (offset phán quyết); `age_ms < 0` ⇒ BLOCK `criterion_unavailable`. Tuổi của cửa sổ thị giác là tuổi của khung cũ nhất trong cửa sổ. Tầng nhận thức có trần tuổi cố định 1000 ms, ghi trong vết ghi; quá trần ⇒ BLOCK. *Vì sao:* thống nhất định nghĩa tuổi dữ kiện, tránh camera lag hoặc khung cũ lọt qua phán quyết.
9. **Gộp theo khung và trần sai số** (review 2026-10-01, Q-62). Lượng giá trên từng khung rồi AND; mất khung (nhảy số thứ tự camera) ⇒ bắt đầu lại cửa sổ. Vùng là hình chữ nhật chuẩn hoá `[x0, y0, x1, y1]` trong `[0, 1]`, `x0 < x1`, `y0 < y1`. Sai số suy luận ở `vision_in` là `tolerance = { score_abs, box_iou_min }` với trần cứng trong lược đồ `score_abs ≤ 0.05`, `box_iou_min ≥ 0.8`. *Vì sao:* chốt dứt điểm các điểm mở của §3g; chặn việc bo mạch khai khống sai số làm rỗng phép kiểm tương đương.
10. **`present` không đứng một mình** (review 2026-10-01, Q-62). Gate dùng `present` (hoặc `count`) của một nhãn bắt buộc phải kèm tiêu chí `numeric` `confidence` của cùng nhãn, cùng vùng, trong `allow_when` mang `max_age_ms`; thiếu ⇒ `neuroedge build` và lúc nạp agent từ chối. Ngưỡng điểm để tính `present` là hằng `PRESENT_SCORE_FLOOR = 0.5` ghi trong vết ghi, không do maker khai. *Vì sao:* tiêu chí `bool` không có `max_age_ms`; nếu `present: false` đứng một mình khi camera đứng hình sẽ cho ALLOW nguy hiểm (ví dụ `close_gate`). Bắt buộc kèm `confidence` để gate khoá ngưỡng và trần tuổi theo Q-54.
11. **Bo camera ESP32-S3** (review 2026-10-01, Q-62). Chọn bo M5Stack CoreS3 (Q-61), profile `esp32s3-cores3`. Camera GC0308 0,3 MP (VGA 640×480), flash 16 MB, PSRAM 8 MB. Đo đạc SRAM/PSRAM theo Q-3 là điều kiện bắt buộc (TSK-I3a-01). Bo mặc định của `esp32s3` vẫn là `esp32s3-box-3`. *Vì sao:* M5Stack CoreS3 đạt tiêu chí đủ năm nguyên thủy lõi cộng camera; GC0308 VGA đáp ứng độ phân giải 640×480 của các mô hình cơ sở.
12. **Khung lặp và ngưỡng `present`** (review 2026-10-01, Q-62). Hai khung liền nhau trong cửa sổ có cùng `vision_ref.sha256` ⇒ camera đứng hình ⇒ BLOCK `criterion_unavailable`. `PRESENT_SCORE_FLOOR = 0.5` ghim trong mã nhận thức, ghi trong vết ghi. *Vì sao:* tuổi khung không bắt được driver gắn mốc giờ mới cho cùng một ảnh; cảm biến thật luôn có nhiễu nên hai khung giống từng byte là dấu hiệu đứng hình. Ngưỡng `present` phải là một số cụ thể để replay tái hiện được; ngưỡng an toàn nằm ở tiêu chí `confidence` của gate.
13. **Giá trị dữ kiện thị giác và tiêu chí đi kèm** (review 2026-10-01, Q-62). Trên mỗi khung: `confidence` = điểm cao nhất của nhãn trong vùng, không có phát hiện ⇒ `0.0`; `count` = số phát hiện có điểm ≥ `PRESENT_SCORE_FLOOR`; `present` = `count ≥ 1`. Tiêu chí `confidence` đi kèm `present`/`count` phải cùng nhãn, cùng vùng và nằm trong `allow_when`. Một khung không thoả khoảng của `allow_when` ⇒ `condition_not_met`, không phải `criterion_unavailable` (RFC-0009 §3c). *Vì sao:* tiêu chí chỉ khai ở `evaluate` không được walker lượng giá nên không mang được tuổi; giá trị không xác định khi vắng phát hiện thì ví dụ đóng cổng không có nghĩa.
