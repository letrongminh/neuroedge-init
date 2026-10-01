# RFC-0013: Nguyên thủy mở rộng tuỳ chọn theo bo mạch và nhiều bo mạch tham chiếu mỗi target

| | |
|:---|:---|
| **Mã RFC** | 0013 |
| **Tiêu đề** | Nguyên thủy mở rộng là tuỳ chọn theo bo mạch; nhiều bo mạch tham chiếu bậc 1 mỗi target; mỗi profile `sim` soi đúng một bo mạch tham chiếu |
| **Hợp đồng bị ảnh hưởng** | *(không trong `schemas/`)* — tập nguyên thủy, bảng bo tham chiếu và bất biến kiểm thử ở `python/neuroedge/hal/board.py`, `python/tests/test_boards.py`; cách `neuroedge build` và `neuroedge verify` chọn bo (`python/neuroedge/cli/main.py`) |
| **Yêu cầu PRD liên quan** | FR-HAL-01, FR-HAL-04, FR-HAL-05, FR-HAL-08, FR-TGT-01, FR-TGT-06, FR-TGT-08 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-09-30 |
| **Trạng thái** | ⏳ Nháp — chưa mở PR · câu hỏi mở đã quyết (§9, Q-57) và đã gộp vào §3–§8 |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (sửa các bất biến kiểm thử bảo vệ tương đương target, RFC-0002 §5) |

> **Khi nào cần RFC:** RFC này không sửa `schemas/`, nhưng đổi ba bất biến mà RFC-0002 §5a–§5c đề xuất
> sau review; đổi chúng lặng lẽ là điều RFC-0002 §5 cảnh báo. RFC này chấp thuận **trước** RFC-0002 (§9 mục 6).
> Task: TSK-I2a-06, TSK-I2a-07, TSK-I3a-01.
> Quyết định nền: `neuroedge-prd.md` §15 Q-52, **Q-53** (bốn gói nguyên thủy bắt buộc trên cả ba target bậc 1;
> bo mạch ESP32-S3 có camera; `sim-rpi5`; `analog.in` chuyển sang RFC-0007), Q-54, Q-55, **Q-57** (§9).
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

`REFERENCE_BOARD = {"sim": "sim-default", "linux": "linux-rpi5", "esp32s3": "esp32s3-box-3"}` (`board.py`), dùng làm mặc định ở `cli/main.py` và `sim/session.py`. `test_reference_board_is_the_box_3_not_a_devkit` ghim `esp32s3` vào Box-3, và RFC-0002 §5c đề xuất "mỗi target bậc 1 có **đúng một** profile". Nhưng **Box-3 không có camera sẵn**, mà Q-53 đòi `vision.in` có mặt trên `esp32s3`. Với đúng một bo mỗi target, `esp32s3` chỉ có camera nếu chính Box-3 mang camera.

### 1c. `sim` phải sao đúng một bo mạch

`sim-default` mirror Box-3 (chú thích trong `boards/sim-default.toml`); `test_sim_offers_no_pin_the_reference_board_lacks` và `…_sensor_…` kiểm quan hệ này. `TODOS.md` #14 đã nêu: `sim-default` không được khai camera vì Box-3 không có, nên agent thị giác không chạy được trên `sim` — Action CI cho khung hình không có đường `sim`.

## 2. Vì sao cấu trúc hiện tại không giải quyết được

- `board.v1.json` đã coi mọi khoá capability là tuỳ chọn (chỉ `board` và `capabilities` là bắt buộc); nghĩa vụ "đủ năm" nằm **hoàn toàn ở mã và test**, nên sửa được không cần lược đồ.
- `REFERENCE_BOARD` là ánh xạ 1-1 `target → id`; không diễn đạt được hai bo mạch tham chiếu.
- Không có bảng nào nói `sim-*` mirror bo mạch nào; quan hệ nằm cứng trong tên test.
- Quy tắc phủ (mỗi nguyên thủy mở rộng phải có trên cả ba target) chưa có chỗ nào cưỡng chế, nên Q-53 có thể bị vi phạm lặng lẽ.
- `neuroedge verify` và nightly chỉ biết một bo mỗi target, nên bo tham chiếu thứ hai sẽ không bao giờ được replay.

## 3. Thay đổi đề xuất

### 3a. Nguyên thủy lõi và nguyên thủy mở rộng

```python
PRIMITIVES = ("audio.in", "audio.out", "digital.out", "sensor.read", "display")   # lõi
EXTENSION_PRIMITIVES = ("digital.in", "i2c", "analog.in", "motion", "vision.in")  # tuỳ chọn (PWM là khối trong digital.out)
ALL_PRIMITIVES = PRIMITIVES + EXTENSION_PRIMITIVES
```

- **Năm nguyên thủy lõi bắt buộc với mọi bo tham chiếu bậc 1 ngoài `EXTENSION_REFERENCE_BOARDS`** (§3b), và luôn bắt buộc với bo mặc định của mỗi target. Bậc 2/3: có/không, như RFC-0002.
- Nguyên thủy mở rộng **tuỳ chọn theo bo mạch**; `BoardProfile.supports()` / `missing_primitives()` nhận cả hai tập; thông điệp `_normalise()` sinh từ danh sách, không ghim "năm" (RFC-0002 §3c.1).
- Khoá mở rộng gõ sai bị từ chối lúc nạp (RFC-0002 §3c.2), giờ dựa trên `ALL_PRIMITIVES`.
- **Không bao giờ khai năng lực phần cứng không có**, lõi lẫn mở rộng: bo thiếu thì vắng khoá, không khai giả để qua test (§9 mục 1).

### 3b. Nhiều bo mạch tham chiếu mỗi target

```python
REFERENCE_BOARDS: dict[str, tuple[str, ...]] = {
    "sim":     ("sim-default", "sim-rpi5"),
    "linux":   ("linux-rpi5",),
    "esp32s3": ("esp32s3-box-3", "<id bo camera>"),  # phương án (a) hoặc (c); phương án (b): ("esp32s3-box-3",)
}
EXTENSION_REFERENCE_BOARDS: frozenset[str] = frozenset()  # chỉ có phần tử khi bo camera theo phương án (c)
```

Phần tử đầu là **mặc định** khi không có `--board` (giữ hành vi hiện tại của `cli/main.py`, `sim/session.py`); Box-3 vẫn là mặc định của `esp32s3`. `REFERENCE_BOARD` cũ giữ làm bí danh của phần tử đầu để không vỡ mã gọi. `EXTENSION_REFERENCE_BOARDS` là bảng lõi, không tự khai trong `board.toml`, cùng lý do `SIM_MIRRORS` (§3d).

**Chọn bo camera** (TSK-I3a-01, §9 mục 1) — xét theo thứ tự, dừng ở phương án đầu tiên đạt:

| Phương án | Điều kiện | Hệ quả |
|:---|:---|:---|
| (a) | Một bo ESP32-S3 có camera khai **đủ năm nguyên thủy lõi** và tập tên chân chung (RFC-0002 §5a); ứng viên đầu tiên: ESP32-S3-EYE của Espressif | Bo tham chiếu thứ hai đầy đủ của `esp32s3`, đứng sau Box-3 |
| (b) | Không có (a); gắn module camera vào Box-3 mà ngân sách bộ nhớ Q-3 vẫn đạt | `esp32s3` giữ một bo; Box-3 gắn module khai `vision_in` |
| (c) | Không có (a) lẫn (b) | **Bo tham chiếu mở rộng**: id vào `EXTENSION_REFERENCE_BOARDS`, chỉ khai đúng những gì phần cứng có, **không bao giờ** là phần tử đầu của target |

**Thay RFC-0002 §5c:** "mỗi target bậc 1 có **ít nhất một** profile tham chiếu, và mọi profile có target thuộc `SUPPORTED_TARGETS`". **Thay §5b:** lõi bắt buộc với mọi bo tham chiếu bậc 1 ngoài `EXTENSION_REFERENCE_BOARDS` và với bo mặc định; nguyên thủy mở rộng chỉ khai khi bo mạch thật có. **§5a** (tập tên chân chung) áp cho cùng tập bo đó. Vì RFC này chấp thuận trước, RFC-0002 §5b/§5c dẫn RFC này thay vì viết lại (§9 mục 6).

### 3c. Quy tắc phủ (Q-53)

**Mỗi nguyên thủy mở rộng phải có trên ít nhất một bo mạch tham chiếu bậc 1 của MỖI target bậc 1** (`sim`, `linux`, `esp32s3`). Test `test_every_extension_primitive_on_every_tier1_target` duyệt `REFERENCE_BOARDS` và `available_boards()`; thiếu ở target nào ⇒ đỏ, kèm gợi ý bo mạch cần thêm.

Bảng bo mang từng nguyên thủy là §9 mục 5; **mỗi ô là một khẳng định riêng** của test phủ (bo trong ô khai nguyên thủy đó), không chỉ "có ở đâu đó trên target". Phần cứng thật không cho phép một ô ⇒ mở `Q-N` và dời ngày, không bỏ ô (Q-52). Ô `motion.*` × `esp32s3` theo RFC-0011 §9 mục 6, kể cả phương án dự phòng ở đó (bo camera mang nếu dock Box-3 không đủ chân); đổi bo của một ô là sửa §9 mục 5 kèm `Q-N`, không đổi lặng lẽ trong test.

### 3d. Mỗi profile `sim` soi đúng một bo mạch tham chiếu

Thêm `boards/sim-rpi5.toml` sao `linux-rpi5` (kể cả camera khi `linux-rpi5` có), như `sim-default` sao Box-3. Quan hệ soi là **một bảng trong mã lõi**, không phải trường của `board.toml`: một profile không được tự khai mình soi bo nào (cùng lý do `TARGET_TIERS`, RFC-0002 §3b; §9 mục 4). Bộ nạp từ chối profile khai `mirrors`.

```python
SIM_MIRRORS = {"sim-default": "esp32s3-box-3", "sim-rpi5": "linux-rpi5"}
```

Bất biến **"`sim` không giàu hơn bo mạch tham chiếu"** (`TODOS.md` #14) phát biểu lại **theo từng cặp**: với mỗi `sim-*`, tập nguyên thủy, chân, cảm biến, chế độ camera ⊆ của bo mạch nó sao. Hai test hiện có (`test_sim_offers_no_pin…`, `…_sensor…`) chuyển thành tham số hoá theo `SIM_MIRRORS`. Không phải bo tham chiếu nào cũng có `sim-*` soi: bo camera `esp32s3` không có; `vision.in` trên `sim` chỉ ở `sim-rpi5` (§9 mục 5). Agent thị giác chạy trên `sim-rpi5`; Action CI khung hình có đường `sim` (TSK-V1b-02). `TODOS.md` #14 đóng khi bo mạch camera tham chiếu và `sim-rpi5` có mặt.

### 3e. Chọn bo mạch khi build

`neuroedge build` đối chiếu `[requires]` với bo mạch (FR-HAL-04), quy tắc ở §9 mục 3:

- Có `--board`: dùng đúng bo đó.
- Không có `--board`: dùng bo mặc định nếu nó thoả `[requires]`. Không thoả ⇒ `BoardCapabilityError` (NE3001, gom trong `BuildFailed` NE3003), mã 1, không ghi artifact nào; thông điệp ba phần (FR-HAL-05) nêu năng lực thiếu, bo mặc định cung cấp gì, và **liệt kê các bo tham chiếu của target thoả `[requires]`** (gợi ý `--board <id>`), hoặc nói rõ không bo nào thoả.
- **Không tự chọn bo khác**: người dùng phải biết chính xác mình nạp lên bo nào.

### 3f. `verify` và nightly chạy mọi bo tham chiếu

Quy tắc ở §9 mục 2: tương đương chỉ có nghĩa khi đã chạy trên đúng bo sẽ giao cho người dùng.

- `neuroedge verify --targets <t,…>` replay vết ghi chuẩn mực trên **từng** bo trong `REFERENCE_BOARDS[t]`, không chỉ phần tử đầu, và báo kết quả theo cặp (target, bo).
- `sim`, `linux`: host lặp qua các bo. `esp32s3`: mỗi bo tham chiếu cần phiên replay của chính nó (`--port` cho từng bo; thiết bị tự khai `board_id`, `testing/uart.py`). Thiếu lượt replay của một bo ⇒ không đạt, mã 1, `VerificationError` (NE4004) — cùng nguyên tắc "quét 0 không bao giờ là đạt"; không bo nào bị bỏ qua lặng lẽ.
- Nightly hardware (`.github/workflows/nightly-hardware.yml`) có một job cho mỗi bo tham chiếu phần cứng; test đối chiếu ma trận job với `REFERENCE_BOARDS`.

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — không đổi `schemas/`; ba profile hiện có nguyên vẹn (phương án (b) của §3b thêm `vision_in` vào profile Box-3, không bỏ khoá nào) |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có, ở tầng bộ nạp: khoá mở rộng trước đây nhận lặng lẽ nay là khoá hợp lệ; profile thứ hai mỗi target được `test_boards.py` chấp nhận. Ngược lại, profile khai `mirrors` nay bị bộ nạp từ chối (§3d) |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không đổi tệp — cả ba vẫn khai `target: "esp32s3"`, `board_id: "esp32s3-box-3"`; `verify` replay chúng trên **mọi** bo tham chiếu của mỗi target được yêu cầu (§3f), không chỉ bo mặc định |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào |
| Bố cục `NETR` hoặc walker C phải đổi? | Không |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không |
| Mã lỗi (`neuroedge-prd.md` Phụ lục B) | Không thêm lớp hay mã mới: `BoardCapabilityError` (NE3001), `BuildFailed` (NE3003), `VerificationError` (NE4004) đã có. Khi chấp thuận: dòng NE3001 thêm hành vi "không có `--board` mà bo mặc định không thoả ⇒ liệt kê bo tham chiếu thoả" (§3e); dòng NE4004 thêm nguyên nhân "một bo tham chiếu của target được yêu cầu không có lượt replay" (§3f) |

Hành vi CLI: `build` không `--board` không đổi khi bo mặc định thoả, và vẫn mã 1 khi không thoả — chỉ thông điệp thêm danh sách bo; `verify` chạy thêm bo nên chậm hơn và có thể đỏ ở bo mới — đó là mục đích.

Test cần sửa: `test_one_profile_exists_per_supported_target` (→ "ít nhất một mỗi target bậc 1"), `test_all_three_targets_share_the_same_named_pins` và `test_every_profile_declares_all_five_primitives` (→ mọi bo tham chiếu bậc 1 ngoài `EXTENSION_REFERENCE_BOARDS`, và mọi bo mặc định), `test_reference_board_is_the_box_3_not_a_devkit` (giữ, áp cho phần tử đầu của `esp32s3`). `REFERENCE_BOARD` cũ được giữ nên `cli/main.py` và `sim/session.py` không vỡ.

## 5. Ảnh hưởng an toàn

RFC này không đụng `gate.v1`, phân giải, năm nguyên tắc kế thừa hay fail-closed. Rủi ro nằm ở **bất biến kiểm thử** và ở **việc chọn bo**:

- **Không bỏ khẳng định nào, chỉ đổi phạm vi**: lõi và tập tên chân chung vẫn bắt buộc với mọi bo tham chiếu bậc 1 đầy đủ và luôn với bo mặc định; "sim không giàu hơn" **chặt hơn** (theo cặp thay vì một profile). Ngoại lệ duy nhất là bo tham chiếu mở rộng (§3b phương án (c)), không bao giờ là bo mặc định.
- **Cổng thay thế đã tồn tại:** `neuroedge build` đối chiếu `[requires]` với bo mạch (TSK-S2-02, `engine/compiler.py`), nên một agent cần `vision.in` bị từ chối ở bo mạch thiếu nó — không mở khoảng nào không ai canh.
- **Ma trận kiểm thử nhân đôi — đã chấp nhận:** `verify` và nightly chạy mọi bo tham chiếu (§3f), vì agent thị giác qua trên `sim-rpi5` chưa chứng minh gì trên bo camera `esp32s3`. Chi phí: thời gian CI và một runner tự quản cho mỗi bo phần cứng.
- **Không chọn bo lặng lẽ:** `build` không bao giờ tự chuyển sang bo khác (§3e).
- **`sim` giàu hơn bo mạch tham chiếu là lỗi an toàn:** agent qua mô phỏng nhưng không build được trên phần cứng. Test theo cặp là cổng chặn.
- **Khai năng lực không có là lỗi an toàn:** test phủ đỏ thì mở `Q-N` và dời ngày (§3c), không khai giả.
- Cần kỹ thuật trưởng duyệt vì RFC-0002 §5 yêu cầu chữ ký khi đổi các bất biến này.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Đưa mọi nguyên thủy mới vào `PRIMITIVES` bắt buộc | Bắt bo mạch khai gian; RFC-0002 §5b đã chỉ ra điều tương tự cho bậc 2/3 |
| Gắn camera vào Box-3 làm lựa chọn đầu | Box-3 là bo mạch đã đo ngân sách bộ nhớ (Q-1, Q-2, Q-3); thêm camera có thể vô hiệu số đo spike. Chỉ giữ làm phương án (b) của §3b, khi ngân sách Q-3 vẫn đạt |
| Bo camera thiếu nguyên thủy lõi làm bo mặc định của `esp32s3` | Agent thoại không `--board` sẽ không build được; luật đủ năm lõi áp cho bo mặc định (§9 mục 1) |
| Chỉ `linux` có camera | Q-53 đòi mọi nguyên thủy mở rộng trên cả ba target |
| `sim` khai camera mà không mirror bo mạch nào | Phá bất biến "sim không giàu hơn" — chính `TODOS.md` #14 |
| Khai `mirrors` trong `board.toml` | Một profile, kể cả bo cộng đồng, tự khai được mình soi bo nào; bảng lõi `SIM_MIRRORS` (§9 mục 4) |
| `verify` và nightly chỉ chạy bo mặc định | Agent qua trên bo mặc định chưa chứng minh gì trên bo tham chiếu khác của cùng target (§9 mục 2) |
| `build` không `--board` tự chọn bo tham chiếu thoả `[requires]` | Người dùng không biết mình nạp lên bo nào (§9 mục 3) |

## 7. Bằng chứng kiểm chứng

- [ ] `boards/sim-rpi5.toml` hợp lệ theo `board.v1`; profile bo camera theo phương án chọn ở TSK-I3a-01 (§3b), tham số lấy từ phần cứng thật (`CONTRIBUTING.md` §3); phương án (b) kèm báo cáo ngân sách Q-3 trong `docs/reports/`
- [ ] Test bảng bo (§3a, §3b): lõi đủ năm và tập tên chân chung trên mọi bo tham chiếu bậc 1 ngoài `EXTENSION_REFERENCE_BOARDS`; phần tử đầu của mọi `REFERENCE_BOARDS[t]` khai đủ năm lõi và không thuộc `EXTENSION_REFERENCE_BOARDS`; mọi id trong hai bảng có profile trong `boards/` với target khớp; khoá mở rộng lạ bị từ chối lúc nạp
- [ ] Test phủ (§3c): `test_every_extension_primitive_on_every_tier1_target`, và **từng ô** của §9 mục 5 (bo trong ô khai nguyên thủy đó); phản chứng: bỏ một khoá khỏi bo trong ô ⇒ đỏ kèm gợi ý
- [ ] Test soi (§3d): `sim-*` ⊆ bo mạch được soi (tham số hoá theo `SIM_MIRRORS`); mọi `sim-*` trong `boards/` có mục trong `SIM_MIRRORS` và ngược lại; profile khai `mirrors` bị từ chối lúc nạp; phản chứng: profile `sim` khai `vision_in` mà bo được soi thiếu ⇒ đỏ
- [ ] Test build (§3e): không `--board`, bo mặc định thoả ⇒ build trên bo mặc định; không thoả ⇒ mã 1, `BoardCapabilityError` liệt kê bo tham chiếu thoả, không ghi artifact, không build trên bo khác; `--board <id>` ⇒ dùng đúng bo đó
- [ ] Test verify (§3f): `verify --targets sim` replay trên cả `sim-default` và `sim-rpi5`; `verify --targets esp32s3` thiếu phiên của một bo tham chiếu ⇒ mã 1 (`VerificationError`); ma trận nightly khớp `REFERENCE_BOARDS`
- [ ] `cd python && .venv/bin/python -m pytest -q` xanh, 0 skipped; `neuroedge verify --targets sim,linux,esp32s3` xanh trên mọi bo tham chiếu bậc 1, trong CI và nightly (A10)

## 8. Việc phải làm khi chấp thuận

- [ ] Thứ tự (§9 mục 6): chấp thuận RFC này trước RFC-0002; ghi chú ở RFC-0002 §5b/§5c dẫn RFC này, và khi RFC-0002 được chấp thuận, §5b/§5c của nó dẫn RFC này thay vì viết lại
- [ ] `python/neuroedge/hal/board.py` (`EXTENSION_PRIMITIVES`, `REFERENCE_BOARDS`, `EXTENSION_REFERENCE_BOARDS`, `SIM_MIRRORS`), `python/neuroedge/hal/__init__.py`, `python/neuroedge/cli/main.py` (`build` §3e, `verify` §3f), `python/neuroedge/sim/session.py`
- [ ] `.github/workflows/nightly-hardware.yml`: một job cho mỗi bo tham chiếu phần cứng
- [ ] Thêm `boards/sim-rpi5.toml` và profile bo camera (TSK-I3a-01); cập nhật `python/tests/test_boards.py`
- [ ] `neuroedge-prd.md` FR-HAL-01, FR-TGT-08, Phụ lục B dòng NE3001 và NE4004 (§4); `neuroedge-roadmap.md` (TSK-I2a-06, TSK-I2a-07, TSK-I3a-01); đóng `TODOS.md` #14
- [ ] `CONTRIBUTING.md` §3 (dòng profile bo mạch); cập nhật `docs/rfc/README.md` và `CHANGELOG.md`

## 9. Quyết định cho các câu hỏi mở (Q-57, 2026-09-30)

Chủ sản phẩm uỷ quyền quyết các câu hỏi mở theo nguyên tắc **an toàn cao nhất**: giữa hai phương án, chọn phương án fail-closed và khó dùng sai hơn, kể cả khi nó tốn công hơn. Các quyết định dưới đây **đã được gộp vào §3–§8**; mục này giữ làm hồ sơ quyết định (Q-57) — §3–§8 lệch với mục này thì sửa §3–§8. Chấp thuận RFC vẫn cần chữ ký kỹ thuật trưởng (`CONTRIBUTING.md` §3).

1. **Bo camera.** Tiêu chí chọn, theo thứ tự: (a) một bo ESP32-S3 có camera khai **đủ năm nguyên thủy lõi** và tập tên chân chung §5a của RFC-0002 — ứng viên đầu tiên để TSK-I3a-01 xác minh là ESP32-S3-EYE của Espressif; (b) nếu không có, gắn module camera vào Box-3 khi ngân sách bộ nhớ Q-3 vẫn đạt; (c) nếu vẫn không, bo camera là **bo tham chiếu mở rộng**: chỉ khai đúng những gì phần cứng có, không được làm bo mặc định của target, và luật "đủ năm nguyên thủy lõi" áp cho bo mặc định. Không bao giờ khai năng lực phần cứng không có.
2. **`verify` và nightly chạy mọi bo tham chiếu** của mọi target bậc 1, không chỉ bo mặc định. *Vì sao:* tương đương chỉ có nghĩa khi đã chạy trên đúng bo sẽ giao cho người dùng.
3. **`build` không `--board`:** dùng bo mặc định nếu nó thoả `[requires]`; không thoả thì báo lỗi ba phần (FR-HAL-05) liệt kê các bo tham chiếu thoả. Không tự chọn bo khác. *Vì sao:* người dùng phải biết chính xác mình nạp lên bo nào.
4. **`SIM_MIRRORS` là bảng trong mã lõi**, không phải trường của `board.toml`. *Vì sao:* một profile không được tự khai mình soi bo nào (cùng lý do `TARGET_TIERS`).
5. **Bo mang từng nguyên thủy mở rộng:**

   | Nguyên thủy | `sim` | `linux` | `esp32s3` |
   |:---|:---|:---|:---|
   | `digital.in`, I2C chỉ đọc, PWM | `sim-default`, `sim-rpi5` | `linux-rpi5` | `esp32s3-box-3` |
   | `analog.in` | `sim-default`, `sim-rpi5` | `linux-rpi5` + ADC I2C trên mạch | `esp32s3-box-3` (ADC của chip, xác minh ở TSK-I3a-01) |
   | `motion.*` | `sim-default`, `sim-rpi5` | `linux-rpi5` + driver có `enable_pin` | `esp32s3-box-3` qua chân dock; dock không đủ chân thì bo camera (mục 1) mang — RFC-0011 §9.6, xác minh ở TSK-I3a-01 |
   | `vision.in` | `sim-rpi5` | `linux-rpi5` + camera | bo camera (mục 1) |

   Mỗi ô là một cam kết kiểm được bằng test phủ của §3c; phần cứng thật không cho phép một ô thì mở `Q-N` và dời ngày, không bỏ ô (Q-52).
6. **Thứ tự chấp thuận:** RFC này chấp thuận **trước** RFC-0002, vì I2a cần nó còn RFC-0002 chỉ cần cho I11; khi RFC-0002 được chấp thuận, §5b và §5c của nó dẫn RFC này thay vì viết lại.
