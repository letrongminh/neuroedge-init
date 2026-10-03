# Thị giác — từ khung hình tới dữ kiện gate và bằng chứng trong vết ghi

**Trạng thái:** đặc tả chuẩn tắc (TSK-V1b-03, TSK-V1b-08). Hợp đồng gốc: [RFC-0012](../rfc/0012-nguyen-thuy-vision-in.md)
§3c–§3e, §9; quyết định Q-54 (thị giác quy về dữ kiện gõ kiểu, ngưỡng khoá ở gate), Q-62; yêu cầu
FR-MDL-04, FR-MDL-07, FR-CI-02, NFR-PRIV-01, NFR-PRIV-03. Hiện thực: `python/neuroedge/perception/vision/`,
lint ở `python/neuroedge/trace.py`, phát lại ở `python/neuroedge/testing/player.py`. Từ khoá **PHẢI**,
**KHÔNG ĐƯỢC** mang nghĩa như RFC 2119.

Tài liệu này là nơi **duy nhất** định nghĩa đường đi từ khung hình camera tới dữ kiện gate, hợp đồng của
mô hình thị giác và dạng sự kiện `vision_fact`. RFC-0012 giữ lý do; ở đây giữ chỗ lắp (§2) cho
`vision.in` (TSK-V1b-01, V1b-02) và cho Action CI khung hình (TSK-V1b-04).

## 1. Nguyên tắc

1. **Mô hình chỉ cấp dữ kiện, không có thẩm quyền.** Đầu ra của mô hình là đầu vào **không tin cậy**:
   kiểm miền (§3.2), rồi ngưỡng, rồi gate. Ngưỡng độ tin cậy và số đếm là tiêu chí `numeric` khoá ở gate
   (Q-54, RFC-0009); tầng nhận thức không có ngưỡng nào ngoài hai hằng ghim trong mã (§4.1).
2. **Thiếu thì chặn.** Mất mô hình, mô hình trả quá hạn, kết quả rác, mất khung, camera đứng hình, khung
   quá cũ ⇒ dữ kiện **chưa quyết** ⇒ gate chặn `criterion_unavailable`. Không nội suy từ khung trước,
   không có giá trị mặc định "không thấy người" (bất biến #2).
3. **Vết ghi không chứa ảnh.** Chỉ `vision_ref` (băm + kích thước) và nhãn/điểm của các khung trong cửa sổ.
   `uri` chỉ khi `metadata.raw_capture` là `true`.
4. **Replay không gọi mô hình.** Phán quyết được tính lại từ nhãn đã ghi (§6).

## 2. Chỗ lắp cho camera — khung hình vào, dữ kiện ra

```text
 vision.in (HAL: linux / sim)            perception/vision/                       engine
 ───────────────────────────             ─────────────────────────────            ─────────────────
 Frame(seq, captured_ms, pixels)  ──►    VisionPipeline.push(frame)
                                            model.detect(frame)   (không tin cậy)
                                            sanitize → vùng → bộ đệm cửa sổ
                                         VisionPipeline.facts_for(engine.tree(key))
                                            vision_fact × mỗi dữ kiện   ──►  EventLog
                                            {tiêu_chí: Fact}            ──►  engine.evaluate(key, facts)
```

Hợp đồng cho phía camera (TSK-V1b-01 trên `linux`, TSK-V1b-02 camera ảo trên `sim`):

| Trường `Frame` | Ý nghĩa |
|:---|:---|
| `seq` | Số thứ tự khung **của camera**: số nguyên, tăng 1 mỗi khung. Nhảy số (mất khung) hay lặp số làm cửa sổ **bắt đầu lại** |
| `captured_ms` | Mốc đọc HAL, trên **đồng hồ của `EventLog`** của phiên (cùng đồng hồ với `Fact.read_ms`). Số hữu hạn; `Frame` từ chối giá trị khác |
| `pixels` | Byte ảnh. Chỉ ở trong bộ nhớ; không bao giờ vào vết ghi. `vision_ref.sha256` là SHA-256 của chính các byte này |
| `width`, `height`, `pixel_format` | Mô tả khung; tầng nhận thức không dùng để quyết |

Thứ tự gọi trong phiên: `push` mọi khung ngay khi HAL trao; **ngay trước** `engine.evaluate`, gọi
`facts_for(engine.tree(key))` rồi truyền kết quả làm `context` của `evaluate`. `facts_for` ghi sự kiện
`vision_fact` ở offset của thời điểm lượng giá, nên chúng đứng trước `gate_evaluation_begin` của cùng
phán quyết. Dữ kiện không đọc được thì **vắng mặt** trong kết quả; engine chặn `criterion_unavailable`.

Camera ảo trong `sim` (V1b-02) phát lại chuỗi khung đã ghi **và** — để `verify` so quyết định giữa target
— kết quả `perception` đã ghi (RFC-0012 §3f); đó là việc của slice đó, cùng `Frame` này.

## 3. Mô hình thị giác

### 3.1 Giao diện (FR-MDL-04, FR-MDL-07)

Một phương thức: **khung vào, phát hiện ra**.

```python
class VisionModel(Protocol):
    identity: ModelIdentity            # tên + sha256 của tệp mô hình
    labels: Collection[str]            # tập nhãn ĐÓNG mà mô hình nói được
    def detect(self, frame: Frame) -> Sequence[Detection] | Inference: ...
```

- `Detection(label, score, box)`: `box` là `(x0, y0, x1, y1)` chuẩn hoá trong `[0, 1]`, `x0 < x1`, `y0 < y1`.
- `Inference(detections, latency_ms)`: trả về thay cho dãy trần khi mô hình mô phỏng muốn nói nó tốn bao lâu
  (thời gian ảo của phiên; bản giả không bao giờ ngủ). Không có `latency_ms` thì tầng nhận thức tự đo.
- `detect` là **đồng bộ**. Adapter bất đồng bộ (cloud) tự bọc lời gọi; `detect` trả về awaitable bị coi là
  `model_error`, không bao giờ được `await` ngầm.

### 3.2 Mọi thứ mô hình nói đều không tin cậy

`sanitize` kiểm miền. **Cả khung bị từ chối** (`rejected: garbage`, mọi dữ kiện trên khung đó chưa quyết) khi:
kết quả không phải list/tuple; quá `MAX_DETECTIONS` (1000) phát hiện; một phần tử không phải `Detection`;
nhãn ngoài `labels` của mô hình; `score` không phải số (chuỗi, `bool`, `None`); `box` thiếu, sai hình hay
ngoài `[0, 1]`. (Phát hiện không có `box` bị từ chối: không đặt được vào vùng, mà bỏ nó đi là báo thiếu người.)

Điểm là **số nhưng không hợp lệ** (NaN, ±inf, ngoài `[0, 1]`) thì **được giữ**: dữ kiện `confidence`/`count`
của khung đó là NaN, nên gate trả `value_out_of_range` bất kể `range` nó khai; dữ kiện `present` (kiểu bool
không có khoảng) chưa quyết (`garbage`). Cả hai đều BLOCK (RFC-0012 §3e, dòng cuối).

### 3.3 Lỗi của mô hình

| Chuyện xảy ra | Khung bị từ chối với | Ghi ở |
|:---|:---|:---|
| `detect` ném `VisionUnavailable` (mất mô hình, mất kết nối) | `model_unavailable` | `frames[].rejected` |
| `detect` ném lỗi khác | `model_error` | như trên |
| Trả lời sau `timeout_ms` (mặc định 200; `[vision] timeout_ms`), hay `latency_ms` không phải số hữu hạn ≥ 0 | `timeout` | như trên |
| Kết quả rác (§3.2) | `garbage` | như trên |

`latency_ms` do mô hình tự báo chỉ được tin theo chiều tăng: thời gian đo thật của lời gọi không bao giờ bị bớt đi.

`push` **không bao giờ ném** vì lỗi của mô hình. Khung bị từ chối vẫn vào cửa sổ: mọi dữ kiện trên cửa sổ chứa
nó chưa quyết cho tới khi nó trôi ra (`min_frames` khung sau). `VisionUnavailable` là lớp con của
`PerceptionUnavailableError` (`NE5001`): không thêm mã lỗi.

### 3.4 Chọn mô hình bằng cấu hình (khối `[vision]`)

```toml
[vision]
provider   = "replay"                        # hoặc "python:pkg.mod:factory"
model      = "models/person-det.tflite"      # tệp CỦA BẠN; NeuroEdge không giao kèm, không tải về
timeout_ms = 200

[vision.options]                             # cho adapter của bạn
```

Đổi mô hình = đổi dòng `provider` (và `[vision.options]`); camera, dữ kiện, gate không đổi. Giống `[stt]`/`[tts]`
(`perception/providers/`): `registry.make_vision_model(config, root)`; adapter tự viết là
`factory(config) -> VisionModel`, bị kiểm (có `identity`, `labels` không rỗng gồm chuỗi, `detect`).
`provider` vắng ⇒ bảng hợp lệ nhưng `make_vision_model` từ chối (không có mặc định thật). Có sẵn: `replay`.
Mô hình thật (ONNX, cloud, NPU sau `accel/`: TSK-V1b-05) là adapter; không phụ thuộc nặng nào được thêm.

`parse_vision` kiểm bảng (cú pháp RFC-0012 §3c): `kind` ∈ {`present`, `count`, `confidence`}; khoá lạ trong
`[vision.facts.*]` (gồm `bands`, mọi ngưỡng) bị từ chối; `min_frames` nguyên 2–64 (mặc định 3); `zone` phải khai;
vùng là hình chữ nhật chuẩn hoá `[x0, y0, x1, y1]` (đa giác bị từ chối); khoá API bị từ chối, không lặp lại giá trị.
Lỗi là `AgentManifestError` (`NE3002`). **Móc vào `neuroedge build`** (kiểm kiểu tiêu chí cùng tên, `confidence_gte`
trên dữ kiện thị giác, `present` thiếu `confidence` ở lúc build/nạp agent) chưa làm ở slice này (§8).

### 3.5 Mô hình giả để thử (`provider = "replay"`)

`ScriptedVisionModel` (`fake.py`): không ML, không mạng, tất định, dùng cho test, `sim` và Action CI khung hình.
`script` cho biết mô hình thấy gì ở khung có số thứ tự đó; **khung ngoài script không phải "không có ai"**:
mô hình chưa sẵn sàng cho khung đó (`model_unavailable`) trừ khi `default = []` nói rõ cảnh rỗng. `fail` liệt kê số
khung mà nó ném lỗi. Danh tính khi không có tệp: SHA-256 của chính script và tập nhãn.

## 4. Dữ kiện

Mỗi `[vision.facts.<tên>]` thành một tiêu chí gate trùng tên: `present` → `bool`; `count`, `confidence` → `numeric`.

### 4.1 Giá trị trên một khung

Từ điểm của các phát hiện **cùng nhãn, trong vùng** của dữ kiện (phát hiện thuộc vùng khi **tâm** hộp của nó nằm trong
hình chữ nhật, biên tính):

| `kind` | Giá trị |
|:---|:---|
| `confidence` | điểm cao nhất; **không có phát hiện ⇒ `0.0`** (vắng mặt là điểm 0, không phải chưa quyết) |
| `count` | số phát hiện điểm ≥ `PRESENT_SCORE_FLOOR` (**0.5**, hằng ghim trong mã) |
| `present` | `count ≥ 1` |

Hai hằng ghim trong mã, không cấu hình được, ghi vào mỗi `vision_fact` để replay kiểm: `PRESENT_SCORE_FLOOR = 0.5`
và `MAX_FRAME_AGE_MS = 1000`. Ngưỡng an toàn thật là tiêu chí `numeric` `confidence` của gate.

### 4.2 Cửa sổ và phép AND

Cửa sổ là `min_frames` khung **liên tiếp** mới nhất. Gate lượng giá tiêu chí **trên từng khung rồi AND**: một khung
nhiễu không mở được gì, một khung xấu luôn chặn — đúng cho cả `gte`/`gt` lẫn `lte`/`lt`
(`count lte 0` với `[0, 1, 0]` ⇒ BLOCK, `[0, 0, 0]` ⇒ ALLOW; `confidence gte 0.85` với `[0.90, 0.80, 0.90]` ⇒ BLOCK).
Cách hiện thực mà **không đổi ngữ nghĩa gate**: `engine_fact` duyệt các khung của cửa sổ qua chính `walk` của
cây quyết định và đưa cho engine **một** `Fact` — giá trị của khung đầu tiên tiêu chí từ chối, nếu không thì khung
cuối. Engine duyệt cây như thường và ghi đúng phán quyết AND, cùng `reason` của khung xấu đầu tiên.

### 4.3 Khi nào dữ kiện chưa quyết

`FactReading.unavailable` thuộc `UNAVAILABLE`; gate chặn `criterion_unavailable`:

| Lý do | Khi |
|:---|:---|
| `model_unavailable`, `model_error`, `timeout`, `garbage` | một khung của cửa sổ bị từ chối (§3.3), hoặc `present` trên điểm không hợp lệ |
| `window_size` | chưa đủ `min_frames` khung (khởi động, hay vừa **bắt đầu lại** vì mất khung) |
| `frame_gap` | `frame_seq` trong cửa sổ không liên tiếp (chỉ replay thấy: đường sống đã bắt đầu lại cửa sổ) |
| `frozen` | hai khung liền nhau có cùng `vision_ref.sha256`, kể cả khi driver gắn mốc giờ mới (RFC-0012 §9.12) |
| `future` | một khung được đọc sau thời điểm lượng giá (`age_ms < 0`) |
| `stale` | khung cũ nhất già hơn `MAX_FRAME_AGE_MS` = 1000 ms, dù `max_age_ms` của gate đặt lớn hơn |
| `unpaired` | gate dùng `present`/`count` mà **không** có tiêu chí `numeric` `confidence` cùng nhãn, cùng vùng trong `allow_when` (§9.10). `bool` không có `max_age_ms`: không có đôi này, camera đứng hình lặp "không có người" sẽ qua `present: false`. Build từ chối gate như vậy; đây là cùng luật lúc chạy và lúc replay |
| `mismatch` | chỉ ở replay: sự kiện đã ghi không khớp nhãn của chính nó (§6) |

Tuổi: `age_ms = offset_ms − min(captured_ms)` — của khung **cũ nhất**, đo tới offset của chính sự kiện
`vision_fact`. Tiêu chí `numeric` đi kèm còn kiểm `max_age_ms` của nó trên cùng tuổi này (RFC-0009 §3c). Đổi mô hình
giữa phiên (`set_model`) **bắt đầu lại cửa sổ**: không cửa sổ nào trộn kết quả của hai mô hình.

## 5. Sự kiện `vision_fact` (nhóm `perception`)

`trace.v1` không đổi (`type` mở, `data` là object). Mỗi dữ kiện thị giác lượng giá cho một phán quyết ghi một sự
kiện, ở offset thời điểm lượng giá, trước `gate_evaluation_begin`:

| Trường `data` | Ý nghĩa |
|:---|:---|
| `fact`, `kind`, `label`, `zone`, `min_frames` | dữ kiện và cấu hình của nó |
| `value` | giá trị khung **mới nhất**; `null` khi dữ kiện chưa quyết. NaN ghi `"nan"` |
| `values` | giá trị trên từng khung của cửa sổ, cùng thứ tự `frames` |
| `unavailable` | có mặt **khi và chỉ khi** `value` là `null`: một giá trị của `UNAVAILABLE` |
| `age_ms` | tuổi khung cũ nhất (§4.3); `null` khi không có khung nào |
| `max_frame_age_ms`, `present_score_floor` | hai hằng ghim (§4.1) |
| `model` | `{name, sha256}` của mô hình đã đọc các khung (RFC-0012 §9.4) |
| `frames[]` | `{frame_seq, vision_ref: {sha256, size}, captured_ms, labels: [{label, zone, score}], rejected?}` |

`labels` chỉ giữ phát hiện cùng nhãn và vùng của dữ kiện này — đủ để tính lại, không hơn. `metadata.vision_models`
liệt kê mọi mô hình của phiên (`[{name, sha256}]`); `metadata.raw_capture` là `true` chỉ khi cố ý lưu ảnh thô.

### Lint ngữ nghĩa (`lint_vision`, `validate_trace`, `NE4001`)

Mọi vi phạm có một tệp phản chứng ở `fixtures/traces/invalid/` (khép kín hai chiều với `expected_errors.yaml`):

| Luật | Tệp |
|:---|:---|
| `uri` chỉ khi `metadata.raw_capture == true` | `vision_uri_without_raw_capture` |
| `sha256` của `vision_ref` đúng `^[0-9a-f]{64}$` | `vision_ref_bad_sha256` |
| `sha256` mô hình đúng dạng · có `model` · có trong `metadata.vision_models` | `vision_model_bad_sha256`, `vision_model_missing`, `vision_model_not_listed` |
| số `frames` = `min_frames` khi dữ kiện đã đọc (không thiếu, không thừa) | `vision_frames_too_few`, `vision_frames_too_many` |
| `frame_seq` liên tiếp | `vision_frame_seq_gap` |
| `age_ms` = `offset_ms` − `captured_ms` cũ nhất; không khung nào đọc sau thời điểm lượng giá khi dữ kiện đã đọc | `vision_age_mismatch`, `vision_age_negative` |
| không ảnh nhúng (base64, `data:`) và không trường lạ | `vision_base64_blob`, `vision_image_field` |
| `value` và `unavailable` loại trừ nhau | `vision_value_with_unavailable` |
| nhãn đã ghi cùng nhãn/vùng của dữ kiện | `vision_foreign_label` |
| `metadata.raw_capture` là boolean | `vision_raw_capture_not_boolean` |

Cửa sổ bị tầng nhận thức từ chối (`unavailable`) **hợp lệ** dù ngắn hơn `min_frames` hay có khung ở tương lai (tuổi âm):
đó chính là ghi nhận một phán quyết BLOCK. Các kiểm tra còn lại vẫn áp dụng. Ba vết ghi chuẩn mực không có sự kiện
thị giác nên lint không chạm chúng.

## 6. Replay (FR-CI-02)

`neuroedge replay` tính lại phán quyết từ các sự kiện `perception`, **không gọi mô hình và không cần khung hình**.
Với mỗi phán quyết, `testing/player.py` lấy các `vision_fact` đứng trước nó, gọi `reading_from_event` — tính lại giá trị từng
khung từ nhãn đã ghi, kiểm tính liên tiếp, đứng hình, tuổi — rồi dùng `facts_for_tree` (cùng hàm đường sống dùng) và đưa
cho engine **thay** cho `gate_facts` đã ghi của các tiêu chí đó. Sự kiện được ghi lại trên dòng thời gian của replay (tuổi
giữ nguyên) nên vết ghi phát lại cũng replay được.

Sự kiện không khớp chính nhãn của nó (giá trị, `values`, `age_ms`, `unavailable`, hai hằng ghim) ⇒ `mismatch`: dữ kiện
vắng, gate chặn `criterion_unavailable`, replay cảnh báo và ghi `vision_fact_problem`. Vết ghi bị sửa chỉ có thể chặn
nhiều hơn, không bao giờ cho phép nhiều hơn. Cùng sự kiện `perception` cho cùng phán quyết trên mọi target: đó là mệnh đề
"gate quyết giống nhau" của RFC-0012 §3f (phần `verify` và camera ảo: V1b-02, V1b-04).

## 7. Quyết định diễn giải khi hiện thực

RFC-0012 chưa nêu rõ các điểm sau; bản này chọn phương án an toàn hơn:

1. **Vùng chứa phát hiện khi tâm hộp nằm trong, biên tính.** Phát hiện không có hộp bị từ chối (§3.2).
2. **`value` của sự kiện là khung mới nhất**; giá trị từng khung ở `values`.
3. **Tuổi đo tới offset của `vision_fact`**, ngay trước lúc gate lượng giá; `gate_facts` ghi thêm tuổi theo mốc của engine.
4. **`labels` ghi theo từng dữ kiện** (chỉ nhãn và vùng của nó), không ghi cả khung: ít lộ hơn, vẫn tính lại được.
5. **`unpaired` kiểm cả lúc chạy** ngoài lúc build, để gate lọt qua build không thoát được.
6. **Điểm NaN/±inf/ngoài `[0, 1]`** là điểm hợp lệ về kiểu nhưng không về miền: dữ kiện số thành NaN ⇒ `value_out_of_range`.

## 8. Chưa làm ở bản này

- `vision.in` trên `linux` (V1b-01), camera ảo `sim` và phát lại cả `perception` đã ghi (V1b-02), Action CI khung hình và golden suy luận (V1b-04), NPU (V1b-05), ba gate mẫu (V1b-06): các slice đó cắm khung vào `VisionPipeline.push`.
- Móc `parse_vision` vào `neuroedge build` và nạp agent: kiểu tiêu chí cùng tên, `confidence_gte` trên dữ kiện thị giác, `present`/`count` thiếu `confidence` — RFC-0012 §8 (`engine/compiler.py`).
- Hằng `MAX_FRAME_AGE_MS`, `PRESENT_SCORE_FLOOR` sống ở `perception/vision/model.py`; `trace.py` không import chúng (tầng) và `replay` đối chiếu giá trị đã ghi với chúng.
