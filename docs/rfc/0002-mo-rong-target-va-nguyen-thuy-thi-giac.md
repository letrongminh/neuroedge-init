# RFC-0002: Mở rộng danh sách target và nguyên thủy thị giác

| | |
|:---|:---|
| **Mã RFC** | 0002 |
| **Lược đồ bị ảnh hưởng** | `board.v1`, `trace.v1` — **không** đụng `gate.v1` |
| **Yêu cầu PRD liên quan** | FR-HAL-01, FR-HAL-04, FR-TGT-08, NFR-PRIV-01, NFR-PRIV-03 |
| **Người đề xuất** | V1 — Kỹ sư lõi nền tảng |
| **Ngày mở** | 2026-09-22 |
| **Trạng thái** | 🟡 Đang thảo luận |
| **Người phê duyệt** | *(xem §5 — RFC này không làm gate lỏng hơn, nhưng nới hai bất biến kiểm thử nên vẫn đề nghị kỹ thuật trưởng duyệt)* |
| **Kiểm chứng** | *(chưa có — thuộc pull request thứ hai, xem §7)* |

> **Phạm vi pull request này:** chỉ tệp RFC, **chưa sửa lược đồ**, đúng quy trình
> `docs/rfc/README.md` bước 2. Ba lược đồ trong `schemas/` giữ nguyên; bộ test
> hiện tại phải vẫn xanh sau khi hợp nhất RFC này.

---

## 1. Vấn đề

Giai đoạn 2 (`neuroedge-roadmap-phase2.md`) đưa hai thứ vào lộ trình: **perception
thị giác** và **phủ rộng phần cứng** sang Jetson, STM32, RP2350. Cả hai đều bị
chặn cứng bởi lược đồ đã đóng băng, và không có đường đi vòng.

### 1a. Danh sách target là enum đóng ở hai lược đồ

`schemas/board.v1.json`, trường `board.target`:

```json
"target": { "type": "string", "enum": ["sim", "linux", "esp32s3"] }
```

`schemas/trace.v1.json`, trường `metadata.target`:

```json
"target": {
  "type": "string",
  "enum": ["sim", "linux", "esp32s3"]
}
```

Hệ quả thực tế: một tệp `boards/jetson-orin-nano.toml` hợp lệ về mọi mặt khác
vẫn bị từ chối, và mọi vết ghi sinh ra từ bo mạch đó không thẩm định được. Không
có cờ cấu hình nào nới được — enum nằm trong tệp đóng băng.

Danh sách này còn lặp lại ở tầng Python, `python/neuroedge/hal/board.py`:

```python
SUPPORTED_TARGETS: tuple[str, ...] = ("sim", "linux", "esp32s3")
```

và ở corpus phản chứng `fixtures/traces/expected_errors.yaml`, nơi thông điệp lỗi
kỳ vọng khớp **chuỗi ký tự** sinh trực tiếp từ enum:

```yaml
unknown_target.json:
  why_contains: "is not one of ['sim', 'linux', 'esp32s3']"
```

Ba nơi này phải đổi đồng thời, nếu không bộ test đỏ. Trong đó `schemas/` và
`fixtures/traces/` đều thuộc diện **RFC bắt buộc** theo `CONTRIBUTING.md` §3.

### 1b. Tập nguyên thủy HAL đóng, không có chỗ cho khung hình

`python/neuroedge/hal/board.py` khai tập năm nguyên thủy là đóng, và thông điệp
lỗi tự nó đã chỉ ra đường hợp lệ duy nhất:

```python
PRIMITIVES: tuple[str, ...] = (
    "audio.in", "audio.out", "digital.out", "sensor.read", "display",
)
```

```
{primitive!r} is not one of the five HAL primitives; the primitives are [...]
→ the primitive set is frozen by FR-HAL-01 — express the need in terms of an
  existing primitive, or raise an RFC to extend the HAL
```

Không nguyên thủy nào diễn đạt được "luồng khung hình từ camera". `sensor.read`
trả giá trị vô hướng rời rạc, không phải luồng liên tục có băng thông hàng MB/s.

### 1c. Lược đồ vết ghi không có chỗ cho bằng chứng thị giác

Phụ lục C.1 của `neuroedge-proposal.md` định nghĩa trường `input` của sự kiện là:
*"Khung âm thanh đầu vào (hoặc mã băm hash khi bật chế độ bảo mật), dữ liệu đọc
cảm biến, tín hiệu ngắt hệ thống."* Không có khung hình. Một phiên có vision sẽ
sinh vết ghi thiếu chính cái dữ liệu dẫn tới phán quyết — phá vỡ mệnh đề tái hiện
sự cố (FR-CI-02).

### 1d. Mâu thuẫn nội tại sẵn có

`neuroedge-proposal.md` §0.1 liệt kê **RP2350** là một phần của thị trường mục
tiêu: *"Các vi điều khiển tích hợp Wi-Fi/BLE và khả năng tăng tốc AI có giá chỉ
$3–$15 (ESP32-S3, RP2350, RPi Zero 2W)"*. Nhưng Phụ lục D.1 (ma trận phần cứng
tham chiếu) không có RP2350 ở bất kỳ nấc trạng thái nào. Tài liệu tự nhận một
con chip thuộc thị trường của mình rồi không cho nó đường vào.

---

## 2. Vì sao lược đồ hiện tại không giải quyết được

**Hai mệnh đề mâu thuẫn trong cùng một tệp `board.v1.json`:**

| Mệnh đề | Vị trí |
|:---|:---|
| "Bảng năng lực là tập mở — bo mạch khai gì thì có cái đó" | `capabilities` **không có** `additionalProperties: false` |
| "Bảng năng lực là tập đóng đúng năm khóa" | `capabilities.properties` liệt kê cứng đúng năm khóa |

Hệ quả cụ thể: thêm `vision_in` vào một tệp `board.toml` sẽ **validate qua**
JSON Schema, rồi bị `board.py::_normalise()` từ chối lúc chạy. Lược đồ và mã
nguồn nói hai điều khác nhau. Không thể dựa vào tính mở ngẫu nhiên đó để lách —
nếu muốn `vision.in` là hợp đồng có thật, nó phải được khai tường minh để mô tả
được tham số (độ phân giải, FPS, định dạng), y như bốn nguyên thủy kia.

Với `target`, không có mâu thuẫn nào — enum đóng ở cả hai tầng và đóng một cách
nhất quán. Đơn giản là không có đường mở nào ngoài việc sửa enum.

---

## 3. Thay đổi đề xuất

### 3a. Mở rộng enum `target` theo phân tầng ba bậc

`schemas/board.v1.json` và `schemas/trace.v1.json`, trước:

```json
"enum": ["sim", "linux", "esp32s3"]
```

sau:

```json
"enum": ["sim", "linux", "esp32s3", "jetson", "stm32", "rp2350"]
```

Enum **vẫn đóng** — đây là chủ ý, xem §6. Cái đổi là danh sách, không phải bản
chất của ràng buộc. Phân tầng cam kết (bậc 1 chính thức / bậc 2 mở rộng / bậc 3
cộng đồng) là hợp đồng **sản phẩm**, ghi ở proposal §3.2 và FR-TGT-08, không mã
hóa vào lược đồ. Lược đồ chỉ trả lời "tên target này có được công nhận không".

### 3b. Thêm nguyên thủy thứ sáu `vision.in`

`schemas/board.v1.json`, thêm vào `capabilities.properties`:

```json
"vision_in": {
  "type": "object",
  "properties": {
    "width":        { "type": "integer", "minimum": 1 },
    "height":       { "type": "integer", "minimum": 1 },
    "fps":          { "type": "integer", "minimum": 1 },
    "pixel_format": { "type": "string" },
    "accelerator":  { "type": "string" }
  }
}
```

Kèm hai ràng buộc ở tầng sản phẩm, **không** ở tầng lược đồ:

1. `vision.in` là nguyên thủy **tùy chọn theo bo mạch**. Khác với năm nguyên thủy
   hiện tại, một profile hợp lệ được phép không khai nó. Cổng kiểm tra là
   `missing_primitives()` lúc build (FR-HAL-04 đã có sẵn): một agent yêu cầu
   `vision.in` sẽ bị từ chối biên dịch trên bo mạch không khai — đúng cơ chế
   đối chiếu năng lực đang dùng cho `display`.
2. Bảng năng lực phía firmware vẫn là **mảng tĩnh định kích thước lúc biên dịch**.
   Tập nguyên thủy đi từ năm lên sáu thì mảng dài thêm một phần tử; nó vẫn đóng,
   vẫn không cần cấp phát động trong HAL. Đây là điều kiện mà `docs/spec/hal_mcu_review.md`
   KL-1 đặt ra, và nó **không bị vi phạm**.

### 3c. Mở rộng trường `input` của vết ghi cho bằng chứng thị giác

Vết ghi **không nhúng ảnh thô**. Nó ghi tham chiếu:

```json
{
  "vision_ref": {
    "sha256": "<băm khung hình>",
    "width": 640, "height": 480,
    "uri": "<tùy chọn, chỉ khi bật lưu thô tường minh>"
  }
}
```

Mặc định chỉ có `sha256` và kích thước. Đây là yêu cầu của NFR-PRIV-01 (không
lưu trữ mặc định) và NFR-PRIV-03 (vết ghi chỉ lưu quyết định, lưu thô phải bật
tường minh) — cùng cơ chế đã áp cho khung âm thanh, không phát minh gì mới.

Thay đổi này **không cần sửa `trace.v1.json`**: `events[].data` đã là
`{"type": "object"}` tự do, và `event.type` không bị enum hóa. Chỗ phải sửa là
**Phụ lục C.1 của `neuroedge-proposal.md`** (bảng mô tả trường `input`) và tài
liệu sự kiện. Ghi ở đây để mục §8 không bỏ sót.

---

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | **Có** — không có ngoại lệ nào. Mọi thay đổi ở §3 đều là nới lỏng hoặc bổ sung |
| Tệp đang không hợp lệ có trở nên hợp lệ? | **Có** — `board.toml` và vết ghi khai target bậc 2/3; `board.toml` khai `vision_in` |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | **Không** — xem lập luận dưới |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | **Không** — RFC này không đụng `gate.v1`. Băm gate tính trên tài liệu gate, không liên quan target hay bảng năng lực |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | **Không** — cả ba khai `target: "esp32s3"`, vẫn nằm trong enum mở rộng và vẫn thẩm định qua nguyên trạng |

### Đối chất với tuyên bố `v2` của RFC-0001

RFC-0001 §4 tuyên bố:

> Sau khi Sprint 1 đóng, mọi thay đổi có tính chất này bắt buộc lên `gate.v2`.

Câu này **không áp cho RFC-0002**, vì hai lý do độc lập, mỗi lý do đủ để kết luận:

1. **Phạm vi khác.** Tuyên bố đó nói về `gate.v2` và đứng trong một RFC chỉ sửa
   `gate.v1`. "Thay đổi có tính chất này" trỏ tới hai trường hợp **siết chặt**
   ở RFC-0001 mục 3c và 3d — những thay đổi làm tài liệu đang hợp lệ trở thành
   không hợp lệ. RFC-0002 không có trường hợp siết chặt nào.
2. **Bản chất khác.** Quy tắc gốc ở `0000-template.md` phân biệt rạch ròi: phá
   vỡ tương thích thì bắt buộc tăng phiên bản; *"nới lỏng (tệp đang không hợp lệ
   trở nên hợp lệ) **có thể làm trong cùng phiên bản**"*. RFC-0002 là nới lỏng
   thuần túy, không có ngoại lệ nào ở hàng thứ nhất của bảng trên.

Nói cách khác: RFC-0001 phải viện đến "Sprint 1 chưa đóng" làm lý do đặc cách vì
nó **có** siết chặt. RFC-0002 không cần lý do đặc cách nào.

Ghi thêm cho minh bạch: nếu hội đồng vẫn muốn `board.v2`/`trace.v2`, chi phí là
hai tệp lược đồ mới, hai `$id` mới, và một kịch bản di trú cho các vết ghi đã
sinh — trong khi lợi ích kỹ thuật bằng không, vì không có tài liệu nào bị vỡ.
Đề nghị giữ `v1`.

---

## 5. Ảnh hưởng an toàn

**Thay đổi này có làm một gate lỏng hơn không: không.** RFC-0002 không đụng
`gate.v1`, không đụng năm nguyên tắc kế thừa (Phụ lục B.5), không đụng mặc định
fail-closed, không đụng `gate_resolver.py`. Gate engine không biết target nào
đang chạy và không biết bo mạch có camera hay không.

Nhưng có **hai bất biến kiểm thử phải nới**, và đó mới là chỗ cần soi:

### 5a. Bất biến "mọi bo mạch dùng chung y hệt tập tên chân"

`python/tests/test_boards.py::test_all_three_targets_share_the_same_named_pins`
hiện ép cả ba profile khai đúng cùng một tập `{door_lock, porch_light, gate_relay}`.

| | |
|:---|:---|
| **Vì sao bất biến này tồn tại** | Nó là cách rẻ nhất để bảo đảm cùng một agent chạy được trên cả ba target mà không rẽ nhánh — P-2 |
| **Vì sao nó không còn đúng** | Nó nhầm *tập tên chân của một lớp usecase* với *hợp đồng toàn cục*. Ba cái tên đó đến từ usecase khóa cửa villa, không phải từ kiến trúc. Một bo mạch STM32 điều khiển van công nghiệp không có `porch_light`, và việc bắt nó khai một chân giả để qua test là **tệ hơn** cho an toàn |
| **Nới thế nào mà không lỏng** | Tập tên chân trở thành hợp đồng **theo lớp usecase**, khai trong agent (`agent.toml`) và đối chiếu lúc build. Bất biến mới: *mọi bo mạch được một agent nhắm tới phải khai đủ tập chân mà agent đó yêu cầu* — mạnh hơn bất biến cũ, vì nó kiểm đúng thứ cần kiểm thay vì kiểm một hằng số. Cơ chế đã có: FR-HAL-04, FR-HAL-05, `missing_primitives()` |

### 5b. Bất biến "mọi profile khai đủ năm nguyên thủy"

`python/tests/test_boards.py::test_every_profile_declares_all_five_primitives`.

| | |
|:---|:---|
| **Vì sao bất biến này tồn tại** | Với đúng ba bo mạch tham chiếu do đội lõi chọn, nó bắt được lỗi quên khai |
| **Vì sao nó không còn đúng** | Nó biến *năng lực* thành *nghĩa vụ*. STM32 không có màn hình; RP2350 không có AEC phần cứng. Ép khai đủ năm nghĩa là hoặc khai gian, hoặc loại vĩnh viễn mọi bo mạch nhỏ — tức đóng cửa chính Giai đoạn 2 |
| **Nới thế nào mà không lỏng** | Nguyên thủy trở thành **khai báo có/không**. Cổng an toàn chuyển từ "bo mạch phải có đủ" sang "agent yêu cầu gì thì bo mạch phải có cái đó, kiểm lúc build". Đây chính là điều FR-HAL-04 đã đặc tả và `missing_primitives()` đã hiện thực — bất biến cũ chỉ là một lớp bảo hiểm thừa đặt sai chỗ. Bất biến mới vẫn giữ nguyên yêu cầu **đủ năm** cho ba bo mạch **bậc 1** |

### 5c. Rủi ro thật của RFC này

Không nằm ở lược đồ mà ở **cam kết**. Enum sáu target tạo ấn tượng đội lõi bảo
đảm chất lượng cho cả sáu. Không phải vậy, và tài liệu phải nói rõ:

- **Bậc 1** (`sim`, `linux`, `esp32s3`): `neuroedge verify` 100%, nightly hardware, đội lõi bảo trì.
- **Bậc 2** (`jetson`): đội lõi bảo trì, verify trên miền phán quyết.
- **Bậc 3** (`stm32`, `rp2350`): cộng đồng tự port, tự kiểm chứng qua Bộ kiểm thử
  tuân thủ (proposal §3.8 trụ cột 2). **Đội lõi không cam kết.**

Nếu phân tầng này không được ghi vào proposal §3.2, PRD FR-TGT-08 và KPI §12.1
**trước khi** sửa lược đồ, thì RFC-0002 tạo ra một lời hứa mà đội không giữ được.
Đó là lý do §8 xếp thứ tự tài liệu trước, lược đồ sau.

---

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Tạo `board.v2` và `trace.v2` | Phá tương thích không cần thiết. Không tài liệu nào đang hợp lệ bị vỡ (§4), nên chi phí di trú đổi lấy lợi ích bằng không |
| Bỏ enum `target`, để `"type": "string"` | Mất cổng chặn lỗi chính tả. Một vết ghi khai `target: "esp32s2"` sẽ lặng lẽ qua, và `neuroedge verify` mất khả năng phát hiện. Corpus phản chứng `unknown_target.json` mất ý nghĩa |
| Dùng `pattern` thay `enum` (ví dụ `^[a-z0-9]+$`) | Cùng vấn đề trên, chỉ khác mức độ. Không diễn đạt được phân tầng bậc |
| Dựa vào việc `capabilities` không có `additionalProperties: false` để thêm `vision_in` mà không sửa lược đồ | Lách chứ không giải. Mất khả năng mô tả tham số (độ phân giải, FPS, accelerator), và để lại mâu thuẫn §2 nguyên vẹn cho người sau |
| Diễn đạt vision qua `sensor.read` | `sensor.read` trả vô hướng rời rạc. Ép luồng khung hình vào đó làm hỏng ngữ nghĩa của chính nguyên thủy đang dùng tốt |
| Nhúng khung hình thô vào vết ghi | Vi phạm NFR-PRIV-01 và NFR-PRIV-03. Kích thước vết ghi tăng ba bậc độ lớn, phá `neuroedge replay` trên máy cá nhân |

---

## 7. Bằng chứng kiểm chứng

*Toàn bộ mục này thuộc **pull request thứ hai**, sau khi RFC được chấp thuận.
Để trống có chủ đích, đúng quy trình `docs/rfc/README.md` bước 2 và 4.*

- [ ] Ví dụ hợp lệ đã thêm vào `fixtures/`: ba `boards/*.toml` mới (jetson, stm32, rp2350) và một vết ghi khai `target: "jetson"`
- [ ] Ví dụ sai kèm thông báo lỗi kỳ vọng đã thêm vào `fixtures/*/invalid/` và `expected_errors.yaml`: cập nhật `unknown_target.json` sang một chuỗi vẫn nằm ngoài enum mới *(hiện dùng `rp2040` — sẽ gây nhầm khi `rp2350` được thêm, phải đổi)*
- [ ] Test tự động đã thêm: `test_target_tiers_are_declared`, `test_vision_in_is_optional_per_board`, và bản sửa của `test_board_schema_enumerates_exactly_the_three_targets`
- [ ] `neuroedge verify` vẫn xanh trên target bậc 1

---

## 8. Việc phải làm khi chấp thuận

**Thứ tự bắt buộc: tài liệu trước, lược đồ sau** — theo lập luận §5c.

- [ ] Ghi phân tầng ba bậc vào `neuroedge-proposal.md` §3.2 và Phụ lục D.1
- [ ] Thêm FR-TGT-08 vào `neuroedge-prd.md` §4.2
- [ ] Sửa KPI §12.1 của proposal để ngưỡng `verify` 100% chỉ áp cho bậc 1
- [ ] Cập nhật Phụ lục C.1 của `neuroedge-proposal.md` cho trường `input` mang `vision_ref`
- [ ] Cập nhật `schemas/board.v1.json` (enum `target`, `capabilities.vision_in`)
- [ ] Cập nhật `schemas/trace.v1.json` (enum `metadata.target`)
- [ ] Cập nhật `SUPPORTED_TARGETS` và `PRIMITIVES` tại `python/neuroedge/hal/board.py`
- [ ] Cập nhật `fixtures/traces/expected_errors.yaml` và `fixtures/traces/invalid/unknown_target.json`
- [ ] Nới hai bất biến ở `python/tests/test_boards.py` theo §5a và §5b
- [ ] Ghi `$comment` dẫn chiếu RFC-0002 tại hai chỗ enum, theo tiền lệ RFC-0001

---

## 9. Việc còn treo

Ba hạng mục cố ý để ngoài phạm vi RFC này, ghi lại để không ai phải suy luận lại:

1. **Ngữ nghĩa gate cho bằng chứng thị giác.** RFC-0002 mở đường cho vision *đi
   vào* hệ thống (nguyên thủy HAL, trường vết ghi) nhưng **không** định nghĩa
   cách một gate lượng giá trên kết quả thị giác. CEL hiện lượng giá giá trị cảm
   biến rời rạc; mệnh đề "camera thấy người trong vùng cấm" chưa có cách diễn đạt.
   Đây là bài toán riêng, chạm `gate.v1` và cần kỹ thuật trưởng duyệt — thuộc một
   RFC-0003 về sau. **Cho tới khi có RFC đó, vision chỉ được dùng làm đầu vào
   thông tin, không được làm căn cứ trực tiếp cho phán quyết actuator.**
2. **Ngân sách bộ nhớ cho nguyên thủy thứ sáu trên vi điều khiển.** Q-3 chốt SRAM
   tự do ≥ 120 KB. Bảng năng lực dài thêm một phần tử là chi phí nhỏ và tĩnh,
   nhưng con số thật phải đo trên bo mạch — chưa có bo mạch tại thời điểm viết
   RFC này. Không chặn RFC, nhưng chặn việc khai `vision_in` cho `esp32s3`.
3. **Ba board profile mới.** Viết `boards/jetson-orin-nano.toml`,
   `boards/stm32-*.toml`, `boards/rp2350-*.toml` cần phần cứng thật để điền đúng
   tham số. Thuộc pull request thứ hai và phụ thuộc lịch mua sắm.
