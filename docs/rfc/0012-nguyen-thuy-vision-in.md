# RFC-0012: Nguyên thủy `vision.in` và bằng chứng nhận thức thị giác

| | |
|:---|:---|
| **Mã RFC** | 0012 |
| **Tiêu đề** | `vision.in` (năng lực bo mạch), dữ kiện gõ kiểu do maker khai từ nhãn mô hình, bằng chứng trong vết ghi |
| **Hợp đồng bị ảnh hưởng** | `board.v1` *(khoá `vision_in`)* · quy ước sự kiện `perception` trong vết ghi *(không đổi `trace.v1`)* · **không** đụng `gate.v1` |
| **Yêu cầu PRD liên quan** | FR-HAL-01, FR-HAL-04, FR-CI-02, FR-MDL-04, FR-MDL-07, NFR-PRIV-01, NFR-PRIV-03 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-09-30 |
| **Trạng thái** | ⏳ Nháp — chưa mở PR |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (chạm `board.v1`, quyền riêng tư camera, ranh giới nhận thức/thẩm quyền) |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3 — sửa `schemas/board.v1.json`. Task: TSK-V1b-07 (RFC này) và
> TSK-V1b-01, TSK-V1b-02, TSK-V1b-03, TSK-V1b-04, TSK-V1b-05, TSK-V1b-06, TSK-V1b-07, TSK-V1b-08. Đây là RFC mà RFC-0002 §9.1 và §9.2 hoãn lại; đầu vào đã biết nằm ở đó. Quyết
> định nền: `neuroedge-prd.md` §15 Q-52, Q-53 (camera có mặt trên cả ba target; bo mạch ESP32-S3 có
> camera), **Q-54** (thị giác → dữ kiện do maker khai, gate khoá ngưỡng bằng tiêu chí `numeric`, **không
> có ngữ nghĩa gate riêng cho thị giác**), Q-55.

## 1. Vấn đề

`vision.in` chỉ tồn tại ở văn bản. Ba khoảng trống:

1. **Bo mạch không khai được camera.** `sensor.read` trả vô hướng rời rạc (RFC-0002 §9.1), không phải luồng khung hình. Hình dạng thử nghiệm ban đầu (`width`, `height`, `fps` nguyên, chuỗi tự do) không so khớp được với agent.
2. **Không có đường từ nhãn mô hình tới phán quyết.** `neuroedge-design-phase2.md` §2.2 giữ thị giác ở mức thông tin ngữ cảnh cho tới khi có RFC; Q-54 chốt cách: quy về dữ kiện gõ kiểu mà gate đã biết lượng giá.
3. **Không có luật vết ghi.** Camera trong không gian riêng tư là rủi ro lớn hơn micro; cần quy ước chính xác cái gì được ghi (NFR-PRIV-01, NFR-PRIV-03).

## 2. Vì sao lược đồ hiện tại không giải quyết được

- `schemas/board.v1.json`: không có khoá `vision_in`; nếu có ai thêm nó sẽ validate qua vì `capabilities` không đóng, nhưng không có kiểu để đối chiếu — và mọi sửa hình dạng sau khi phát hành là siết chặt (RFC-0002 §6).
- `gate.v1` chỉ lượng giá `bool` / `level` / `choice`; RFC-0009 thêm `numeric`. Không cần thêm gì khác cho thị giác nếu độ tin cậy được biểu diễn như một dữ kiện số. `confidence_gte` chỉ áp cho `bool` (`engine/constraints.py`, `BOOL_OPERATORS`) nên không đủ cho nhãn `level`/`choice`.
- `[requires]` của agent (`fixtures/agents/*/agent.toml`) chưa có quy tắc so khớp cho tham số số.

## 3. Thay đổi đề xuất

### 3a. Năng lực bo mạch

```toml
[capabilities.vision_in]
modes = [
  { width = 640,  height = 480, fps = 30.0,  pixel_format = "yuyv" },
  { width = 1280, height = 720, fps = 7.5,   pixel_format = "mjpeg" },
]
```

`fps` là `number` (7,5 · 29,97), không phải số nguyên; cảm biến nhiều chế độ nên `modes[]` là mảng bắt buộc (ít nhất một phần tử); `pixel_format` là **enum** để đối chiếu được (danh sách giá trị khởi đầu ở §9). Không khai bộ tăng tốc (`accelerator`) trong RFC này: mô hình và NPU thuộc cấu hình agent (TSK-V1b-03, TSK-V1b-05), không thuộc hợp đồng bo mạch.

### 3b. So khớp với `[requires]`

Agent khai yêu cầu tối thiểu, bo mạch thoả nếu **tồn tại ít nhất một chế độ** đủ mọi ngưỡng:

```toml
[requires]
"vision.in" = { min_width = 640, min_height = 480, min_fps = 10.0, pixel_formats = ["yuyv", "mjpeg"] }
```

`neuroedge build` (`engine/compiler.py`) từ chối bo mạch không có chế độ nào thoả, bằng lỗi ba phần nêu chế độ gần nhất (FR-HAL-05).

### 3c. Từ nhãn mô hình tới dữ kiện gõ kiểu (Q-54)

**Maker** khai trong cấu hình agent cách nhãn mô hình thành dữ kiện; **gate** khoá ngưỡng. Ví dụ ý tưởng:

```toml
# agent.toml — maker khai (cú pháp cuối cùng: §9)
[perception.vision.facts.person_present]
kind = "bool"
label = "person"
[perception.vision.facts.person_confidence]
kind = "numeric"     # điểm tin cậy của nhãn, [0, 1]
label = "person"
```

```yaml
# gate — thẩm quyền
evaluate:
  person_present:    { type: bool, instructions: "Có người trong khung" }
  person_confidence: { type: numeric, unit: ratio, range: { min: 0, max: 1 }, instructions: "Điểm tin cậy của nhãn person" }
allow_when:
  person_present: false
  person_confidence: { gte: 0.85 }     # khoá ở gate, kế thừa chỉ thu hẹp (RFC-0009)
```

Maker chọn *nhãn nào thành dữ kiện nào*; **maker không chọn được ngưỡng an toàn**. Không có toán tử gate riêng cho thị giác: mọi thứ đi qua `bool`/`level`/`choice`/`numeric`.

### 3d. Vết ghi

- Kết quả nhận diện đi vào sự kiện nhóm `perception` (Phụ lục C.1 của `neuroedge-proposal.md`): nhãn, dữ kiện đã suy ra, điểm, và **danh tính mô hình** (mã và băm trọng số), đủ để `replay` tái hiện phán quyết (FR-CI-02).
- Khung hình chỉ để lại `vision_ref = { sha256, size }`; **không nhúng ảnh thô**. Chỉ ghi cho khung dẫn tới một quyết định.
- `trace.v1` **không đổi** (`events[].data` và `metadata` đã mở, RFC-0002 §9.2). Lint ngữ nghĩa ở `python/neuroedge/trace.py`: `sha256` khớp `^[0-9a-f]{64}$`; `uri` chỉ khi `metadata.raw_capture == true`; từ chối blob base64 trong `data` (TSK-V1b-08).

### 3e. Fail-closed

Mất camera, mất mô hình, mô hình trả kết quả rác (điểm NaN, ngoài `[0,1]`, nhãn lạ) ⇒ dữ kiện không khả dụng ⇒ `criterion_unavailable` ⇒ BLOCK. Không có giá trị mặc định "không thấy người".

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — không profile nào trong `boards/` khai `vision_in` |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có — profile khai `vision_in` đúng hình dạng. Cùng điểm siết chặt khoá `capabilities` như RFC-0007 §4: hình dạng phải đúng ngay lần đầu |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không — chúng không có sự kiện thị giác |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào; ba gate mẫu thị giác (TSK-V1b-06) vào `digests.lock` bằng PR thường |
| Bố cục `NETR` hoặc walker C phải đổi? | Không riêng RFC này; dùng nút `numeric` của RFC-0009 |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không |

## 5. Ảnh hưởng an toàn

- **Gate không lỏng hơn và không có ngữ nghĩa thị giác mới** (Q-54): `gate.v1`, phân giải, năm nguyên tắc không đổi. Ràng buộc của `neuroedge-design-phase2.md` §2.2 — thị giác chỉ tới actuator qua các kiểu dữ kiện gate biết lượng giá — được giữ nguyên.
- **Nhận thức không thành thẩm quyền:** mô hình chỉ cấp dữ kiện; ngưỡng do gate khoá và chỉ thu hẹp được khi kế thừa. Maker nới ngưỡng bằng cấu hình agent **không được** vì ngưỡng không nằm ở đó.
- **Riêng tư:** không khung thô trong vết ghi theo mặc định; lưu ảnh thô phải bật tường minh (`metadata.raw_capture`). Quy tắc chặt hơn micro, không lỏng hơn.
- **Danh tính mô hình trong vết ghi:** đổi mô hình là đổi hành vi; vết ghi phải cho biết mô hình nào ra kết luận nào.
- **Rủi ro còn lại:** mô hình sai với điểm cao (nhãn sai tự tin). Giảm bằng ngưỡng số ở gate và, với hành động không hoàn tác, `on_block: ask`; không loại được hoàn toàn.
- **Ngân sách bộ nhớ `esp32s3`:** camera trên MCU tốn SRAM/PSRAM; số đo trên bo mạch thật (Q-3) là điều kiện, không phải giả định.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Ngữ nghĩa gate riêng cho bằng chứng thị giác (vùng cấm, đếm người) | Q-54: phá tính xác định của rule engine, cần RFC `gate.v1` lớn; quy về dữ kiện gõ kiểu đủ cho ca sử dụng ưu tiên |
| Maker tự đặt ngưỡng trong `agent.toml` | Ý nghĩa an toàn ngoài gate; cùng lý do RFC-0005 §6 và RFC-0009 §1 |
| `fps` nguyên, `pixel_format` chuỗi tự do | Không biểu diễn 7,5 fps; không so khớp được (RFC-0002 §9.1) |
| Mở rộng `sensor.read` | Không mang luồng khung; xem lập luận ở RFC-0007 §2 |
| Ghi khung hình vào vết ghi | Vi phạm NFR-PRIV-01, NFR-PRIV-03; 30 fps ≈ 13 MB/giờ chỉ riêng băm và siêu dữ liệu |

## 7. Bằng chứng kiểm chứng

- [ ] Ví dụ hợp lệ: profile `linux` và bo mạch `esp32s3` có camera khai `vision_in` (RFC-0013); agent mẫu có `[requires] "vision.in"`
- [ ] Phản chứng: `fps` chuỗi, `modes` rỗng, `pixel_format` ngoài enum; bo mạch không có chế độ thoả `[requires]` ⇒ lỗi build
- [ ] Trace: `fixtures/traces/invalid/` cho `sha256` sai dạng, `uri` khi không `raw_capture`, base64 trong `data` — kèm `expected_errors.yaml`, khép kín hai chiều
- [ ] Gate: `numeric` cho điểm tin cậy; mất camera/mô hình/điểm NaN ⇒ BLOCK `criterion_unavailable` (corpus ở TSK-V1b-06 và Action CI TSK-V1b-04)
- [ ] `replay` tái hiện phán quyết từ sự kiện `perception`, không cần khung hình; danh tính mô hình có trong vết ghi
- [ ] `neuroedge gate lint` và `neuroedge verify` xanh

## 8. Việc phải làm khi chấp thuận

- [ ] Cập nhật `schemas/board.v1.json`
- [ ] Cập nhật Phụ lục C.1 trong `neuroedge-proposal.md`; FR-HAL-01 ở `neuroedge-prd.md`; `TODOS.md` #14 (cách sửa nằm ở RFC-0013)
- [ ] `neuroedge-roadmap.md`: TSK-V1b-07 xong; mở TSK-V1b-01, TSK-V1b-02, TSK-V1b-03, TSK-V1b-04, TSK-V1b-05, TSK-V1b-06, TSK-V1b-08
- [ ] `python/neuroedge/hal/` (`linux.py`, `sim.py`), `python/neuroedge/trace.py`, `perception/vision/`, camera ảo trong `sim`
- [ ] Fixture/test; cập nhật `docs/rfc/README.md` và `CHANGELOG.md`

## 9. Câu hỏi còn mở

1. Danh sách giá trị enum `pixel_format` (đề xuất khởi đầu: `yuyv`, `mjpeg`, `rgb565`, `rgb888`, `gray8`) — chốt theo phần cứng thật.
2. Cú pháp khai dữ kiện trong `agent.toml` (§3c chỉ là ví dụ ý tưởng) và cách gắn dữ kiện với tên tiêu chí của gate.
3. Điểm tin cậy: luôn là tiêu chí `numeric` riêng, hay cho phép `bool` dùng `confidence_gte` sẵn có khi nhãn là bool? Q-54 chọn `numeric`; cần xác nhận không tạo hai đường.
4. Danh tính mô hình nằm ở `metadata` (một lần/phiên) hay mỗi sự kiện `perception`.
5. Chính sách lấy mẫu khung hình được ghi `vision_ref`: chỉ khung dẫn tới quyết định, hay cả khung ngay trước/sau.
6. Camera ảo trong `sim` phát lại chuỗi ảnh nào và làm sao chứng minh tương đương với phần cứng (TSK-V1b-02).
