# RFC-0013: Nguyên thủy mở rộng tuỳ chọn theo bo mạch và nhiều bo mạch tham chiếu mỗi target

| | |
|:---|:---|
| **Mã RFC** | 0013 |
| **Tiêu đề** | Nguyên thủy mở rộng là tuỳ chọn theo bo mạch; nhiều bo mạch tham chiếu bậc 1 mỗi target; một profile `sim` cho mỗi bo mạch tham chiếu |
| **Hợp đồng bị ảnh hưởng** | *(không trong `schemas/`)* — tập nguyên thủy và bất biến kiểm thử ở `python/neuroedge/hal/board.py`, `python/tests/test_boards.py` |
| **Yêu cầu PRD liên quan** | FR-HAL-01, FR-HAL-04, FR-TGT-01, FR-TGT-06, FR-TGT-08 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-09-30 |
| **Trạng thái** | ⏳ Nháp — chưa mở PR |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (sửa các bất biến kiểm thử bảo vệ tương đương target, RFC-0002 §5) |

> **Khi nào cần RFC:** RFC này không sửa `schemas/`, nhưng đổi ba bất biến mà RFC-0002 §5a–§5c đã đặt
> ra sau review; đổi chúng lặng lẽ là điều RFC-0002 §5 cảnh báo. Task: TSK-I2a-06, TSK-I2a-07, TSK-I3a-01.
> Quyết định nền: `neuroedge-prd.md` §15 Q-52, **Q-53** (bốn gói nguyên thủy bắt buộc trên cả ba target bậc 1;
> bo mạch ESP32-S3 có camera; `sim-rpi5`; `analog.in` chuyển sang RFC-0007), Q-54, Q-55.
> Phụ thuộc: [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md), [RFC-0010](0010-pwm-trong-digital-out.md),
> [RFC-0011](0011-nguyen-thuy-motion.md), [RFC-0012](0012-nguyen-thuy-vision-in.md).

## 1. Vấn đề

Bốn RFC trước thêm nguyên thủy mới (`digital.in`, I2C, `analog.in`, PWM, `motion.*`, `vision.in`). Ba điều trong mã và test hiện tại chặn việc đó:

### 1a. Tập nguyên thủy là năm, bắt buộc với mọi bo mạch

`python/neuroedge/hal/board.py`:

```python
PRIMITIVES: tuple[str, ...] = ("audio.in", "audio.out", "digital.out", "sensor.read", "display")
```

`python/tests/test_boards.py::test_every_profile_declares_all_five_primitives` bắt mọi profile khai đủ năm. Nếu sáu nguyên thủy mới cũng vào `PRIMITIVES`, mọi bo mạch phải khai cả camera lẫn motor — sai với phần cứng thật.

### 1b. Mỗi target đúng một bo mạch tham chiếu

`REFERENCE_BOARD = {"sim": "sim-default", "linux": "linux-rpi5", "esp32s3": "esp32s3-box-3"}` (`board.py`), dùng làm mặc định ở `cli/main.py` và `sim/session.py`. `test_reference_board_is_the_box_3_not_a_devkit` ghim `esp32s3` vào Box-3, và RFC-0002 §5c đề xuất "mỗi target bậc 1 có **đúng một** profile". Nhưng **Box-3 không có camera**, mà Q-53 đòi `vision.in` có mặt trên `esp32s3`. Một bo mạch không thể vừa là Box-3 vừa có camera.

### 1c. `sim` phải sao đúng một bo mạch

`sim-default` mirror Box-3 (chú thích trong `boards/sim-default.toml`); `test_sim_offers_no_pin_the_reference_board_lacks` và `…_sensor_…` kiểm quan hệ này. `TODOS.md` #14 đã nêu: `sim-default` không được khai camera vì Box-3 không có, nên agent thị giác không chạy được trên `sim` — Action CI cho khung hình không có đường `sim`.

## 2. Vì sao cấu trúc hiện tại không giải quyết được

- `board.v1.json` đã coi mọi khoá capability là tuỳ chọn (chỉ `board` và `capabilities` là bắt buộc); nghĩa vụ "đủ năm" nằm **hoàn toàn ở mã và test**, nên sửa được không cần lược đồ.
- `REFERENCE_BOARD` là ánh xạ 1-1 `target → id`; không diễn đạt được hai bo mạch tham chiếu.
- Không có bảng nào nói `sim-*` mirror bo mạch nào; quan hệ nằm cứng trong tên test.
- Quy tắc phủ (mỗi nguyên thủy mở rộng phải có trên cả ba target) chưa có chỗ nào cưỡng chế, nên Q-53 có thể bị vi phạm lặng lẽ.

## 3. Thay đổi đề xuất

### 3a. Nguyên thủy lõi và nguyên thủy mở rộng

```python
PRIMITIVES = ("audio.in", "audio.out", "digital.out", "sensor.read", "display")   # lõi
EXTENSION_PRIMITIVES = ("digital.in", "i2c", "analog.in", "motion", "vision.in")  # tuỳ chọn (PWM là khối trong digital.out)
ALL_PRIMITIVES = PRIMITIVES + EXTENSION_PRIMITIVES
```

- **Năm nguyên thủy lõi vẫn bắt buộc với mọi bo mạch bậc 1** (RFC-0002 §5b không đổi phần này). Bậc 2/3: có/không, như RFC-0002.
- Nguyên thủy mở rộng **tuỳ chọn theo bo mạch**; `BoardProfile.supports()` / `missing_primitives()` nhận cả hai tập; thông điệp `_normalise()` sinh từ danh sách, không ghim "năm" (RFC-0002 §3c.1).
- Khoá mở rộng gõ sai bị từ chối lúc nạp (RFC-0002 §3c.2), giờ dựa trên `ALL_PRIMITIVES`.

### 3b. Nhiều bo mạch tham chiếu mỗi target

```python
REFERENCE_BOARDS: dict[str, tuple[str, ...]] = {
    "sim":     ("sim-default", "sim-rpi5"),
    "linux":   ("linux-rpi5",),
    "esp32s3": ("esp32s3-box-3", "<bo mạch ESP32-S3 có camera>"),
}
```

Phần tử đầu là **mặc định** khi không có `--board` (giữ hành vi hiện tại của `cli/main.py`, `sim/session.py`). Box-3 tiếp tục lo thoại/màn hình; một bo mạch ESP32-S3 có camera lo `vision.in` (id và phần cứng cụ thể: §9). `REFERENCE_BOARD` cũ giữ làm bí danh của phần tử đầu để không vỡ mã gọi.

**Sửa RFC-0002 §5c:** "mỗi target bậc 1 có **ít nhất một** profile tham chiếu, và mọi profile có target thuộc `SUPPORTED_TARGETS`". **Sửa §5b:** không đổi (lõi bắt buộc), thêm "nguyên thủy mở rộng chỉ khai khi bo mạch thật có". §5a (tập tên chân chung) giữ cho mọi bo mạch bậc 1 — xem §9 nếu phần cứng không cho phép.

### 3c. Quy tắc phủ (Q-53)

**Mỗi nguyên thủy mở rộng phải có trên ít nhất một bo mạch tham chiếu bậc 1 của MỖI target bậc 1** (`sim`, `linux`, `esp32s3`). Test `test_every_extension_primitive_on_every_tier1_target` duyệt `REFERENCE_BOARDS` và `available_boards()`; thiếu ở target nào ⇒ đỏ, kèm gợi ý bo mạch cần thêm. Đây là điều kiện để "bốn gói trên ba target" không chỉ là lời hứa.

### 3d. Một profile `sim` cho mỗi bo mạch tham chiếu

Thêm `boards/sim-rpi5.toml` sao `linux-rpi5` (kể cả camera khi `linux-rpi5` có), như `sim-default` sao Box-3. Một bảng thuộc lõi, không tự khai trong `board.toml` (cùng lý do `TARGET_TIERS`, RFC-0002 §3b):

```python
SIM_MIRRORS = {"sim-default": "esp32s3-box-3", "sim-rpi5": "linux-rpi5"}
```

Bất biến **"`sim` không giàu hơn bo mạch tham chiếu"** (`TODOS.md` #14) phát biểu lại **theo từng cặp**: với mỗi `sim-*`, tập nguyên thủy, chân, cảm biến, chế độ camera ⊆ của bo mạch nó sao. Hai test hiện có (`test_sim_offers_no_pin…`, `…_sensor…`) chuyển thành tham số hoá theo `SIM_MIRRORS`. Agent thị giác chạy trên `sim-rpi5`; Action CI khung hình có đường `sim` (TSK-V1b-02). `TODOS.md` #14 đóng khi bo mạch camera tham chiếu và `sim-rpi5` có mặt.

### 3e. Chọn bo mạch khi build

`neuroedge build` đối chiếu `[requires]` với bo mạch (FR-HAL-04). Với nhiều bo mạch mỗi target, lệnh dùng `--board` nếu có; nếu không, dùng mặc định của target và báo lỗi ba phần gợi ý bo mạch tham chiếu thoả `[requires]` khi mặc định không thoả. Không tự chuyển bo mạch lặng lẽ (§9).

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — không đổi `schemas/`; ba profile hiện có nguyên vẹn |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có, ở tầng bộ nạp: khoá mở rộng trước đây nhận lặng lẽ nay là khoá hợp lệ; profile thứ hai mỗi target được `test_boards.py` chấp nhận |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không — cả ba khai `target: "esp32s3"`, `verify` vẫn chạy trên bo mạch mặc định |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào |
| Bố cục `NETR` hoặc walker C phải đổi? | Không |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không |

Test cần sửa: `test_one_profile_exists_per_supported_target` (→ "ít nhất một mỗi target bậc 1"), `test_all_three_targets_share_the_same_named_pins`, `test_every_profile_declares_all_five_primitives` (→ "lõi bắt buộc"), `test_reference_board_is_the_box_3_not_a_devkit` (giữ, áp cho Box-3 cụ thể). `REFERENCE_BOARD` cũ được giữ nên `cli/main.py` và `sim/session.py` không vỡ.

## 5. Ảnh hưởng an toàn

RFC này không đụng `gate.v1`, phân giải, năm nguyên tắc kế thừa hay fail-closed. Rủi ro nằm ở **bất biến kiểm thử**:

- **Không bỏ khẳng định nào, chỉ đổi phạm vi**: lõi vẫn bắt buộc bậc 1; tập tên chân chung vẫn áp cho bậc 1; "sim không giàu hơn" **chặt hơn** (theo cặp thay vì một profile).
- **Cổng thay thế đã tồn tại:** `neuroedge build` đối chiếu `[requires]` với bo mạch (TSK-S2-02, `engine/compiler.py`), nên một agent cần `vision.in` bị từ chối ở bo mạch thiếu nó — không mở khoảng nào không ai canh.
- **Rủi ro thật:** hai bo mạch mỗi target nhân đôi ma trận kiểm thử `verify` và nightly hardware. Nếu `verify` chỉ chạy bo mạch mặc định, agent thị giác có thể qua trên `sim-rpi5` mà chưa chạy trên bo mạch camera `esp32s3` — xem §9.
- **`sim` giàu hơn bo mạch tham chiếu là lỗi an toàn:** agent qua mô phỏng nhưng không build được trên phần cứng. Test theo cặp là cổng chặn.
- Cần kỹ thuật trưởng duyệt vì RFC-0002 §5 yêu cầu chữ ký khi đổi các bất biến này.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Đưa mọi nguyên thủy mới vào `PRIMITIVES` bắt buộc | Bắt bo mạch khai gian; RFC-0002 §5b đã chỉ ra điều tương tự cho bậc 2/3 |
| Gắn camera vào Box-3 bằng module ngoài, giữ một bo mạch | Box-3 là bo mạch đã đo ngân sách bộ nhớ (Q-1, Q-2, Q-3); đổi nó là vô hiệu spike; Q-53 chọn bo mạch camera riêng |
| Chỉ `linux` có camera | Q-53 đòi mọi nguyên thủy mở rộng trên cả ba target |
| `sim` khai camera mà không mirror bo mạch nào | Phá bất biến "sim không giàu hơn" — chính `TODOS.md` #14 |
| Khai `mirrors` trong `board.toml` | Bo mạch cộng đồng tự khai được quan hệ; bảng lõi (`SIM_MIRRORS`) an toàn hơn — quyết định còn mở, §9 |

## 7. Bằng chứng kiểm chứng

- [ ] `boards/sim-rpi5.toml` hợp lệ theo `board.v1`; profile bo mạch ESP32-S3 có camera (khi có phần cứng thật: `CONTRIBUTING.md` §3 đòi phần cứng thật để điền tham số)
- [ ] Test: `test_every_extension_primitive_on_every_tier1_target`; `sim-*` ⊆ bo mạch mirror (tham số hoá theo `SIM_MIRRORS`); lõi bắt buộc bậc 1; khoá mở rộng lạ bị từ chối lúc nạp
- [ ] Phản chứng: profile `sim` khai `vision_in` mà bo mạch mirror thiếu ⇒ đỏ; target thiếu một nguyên thủy mở rộng ⇒ đỏ kèm gợi ý
- [ ] `cd python && .venv/bin/python -m pytest -q` xanh, 0 skipped; `neuroedge verify` xanh trên mọi bo mạch tham chiếu bậc 1

## 8. Việc phải làm khi chấp thuận

- [ ] Sửa RFC-0002 §5b/§5c (hoặc ghi RFC này thay thế phần đó nếu RFC-0002 đã chấp thuận)
- [ ] `python/neuroedge/hal/board.py`, `python/neuroedge/hal/__init__.py`, `python/neuroedge/cli/main.py`, `python/neuroedge/sim/session.py`
- [ ] Thêm `boards/sim-rpi5.toml` và profile ESP32-S3 camera; cập nhật `python/tests/test_boards.py`
- [ ] `neuroedge-prd.md` FR-HAL-01, FR-TGT-08; `neuroedge-roadmap.md` (TSK-I2a-06, TSK-I2a-07, TSK-I3a-01); đóng `TODOS.md` #14
- [ ] `CONTRIBUTING.md` §3 (dòng profile bo mạch); cập nhật `docs/rfc/README.md` và `CHANGELOG.md`

## 9. Câu hỏi còn mở

1. Bo mạch ESP32-S3 có camera cụ thể nào, id, và nó có khai đủ tập tên chân chung §5a không (nếu không, §5a cần ngoại lệ có căn cứ).
2. `verify` và nightly chạy bo mạch nào: chỉ mặc định, mọi bo mạch tham chiếu, hay mọi bo mạch thoả `[requires]` của agent?
3. `build` không `--board`: chỉ báo lỗi kèm gợi ý, hay chọn bo mạch tham chiếu đầu tiên thoả `[requires]`?
4. Quan hệ `sim-* → bo mạch mirror`: bảng trong mã (`SIM_MIRRORS`) hay trường trong `board.toml`.
5. Bo mạch tham chiếu nào mang từng nguyên thủy mở rộng ở mỗi target (cần cho §3c), đặc biệt `motion` và `analog.in` trên `esp32s3` và `sim`.
6. Thứ tự chấp thuận với RFC-0002: RFC-0002 đang thảo luận; RFC này sửa §5b/§5c của nó nên hai RFC nên chấp thuận cùng lượt hoặc RFC-0002 trước.
