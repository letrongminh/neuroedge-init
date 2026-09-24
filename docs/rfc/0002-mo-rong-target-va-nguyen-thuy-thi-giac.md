# RFC-0002: Mở rộng danh sách target

| | |
|:---|:---|
| **Mã RFC** | 0002 |
| **Lược đồ bị ảnh hưởng** | `board.v1`, `trace.v1` — **chỉ** enum `target`; **không** đụng `gate.v1` |
| **Yêu cầu PRD liên quan** | FR-TGT-08, FR-HAL-01, FR-HAL-04, FR-HAL-05 |
| **Người đề xuất** | V1 — Kỹ sư lõi nền tảng |
| **Ngày mở** | 2026-09-22 · thu hẹp phạm vi 2026-09-23 sau review (biên bản: [`docs/archive/rfc-0002-review-record.md`](../archive/rfc-0002-review-record.md)) |
| **Trạng thái** | 🟡 Đang thảo luận |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc.** RFC không làm gate lỏng hơn, nhưng chạm ba bất biến kiểm thử đang bảo vệ tương đương target (§5), và tiêu chí ra Khối V1a số 1 đòi chữ ký kỹ thuật trưởng (`neuroedge-roadmap-phase2.md`) |
| **Kiểm chứng** | *(chưa có — thuộc pull request thứ hai, **không hợp nhất trước Tháng 9**, xem §8)* |

> **Phạm vi pull request này:** chỉ tệp RFC, **chưa sửa lược đồ**, đúng quy trình
> `docs/rfc/README.md` bước 2. Ba lược đồ trong `schemas/` giữ nguyên; bộ test
> hiện tại phải vẫn xanh sau khi hợp nhất RFC này.

> **Thu hẹp phạm vi (2026-09-23).** Bản đầu của RFC gộp ba việc: mở enum `target`,
> thêm nguyên thủy `vision.in`, và quy ước `vision_ref` trong vết ghi. Sau review,
> RFC này **chỉ còn việc thứ nhất**, cộng thêm bậc target ở dạng máy đọc được.
> `vision.in` và bằng chứng thị giác trong vết ghi chuyển sang §9 kèm mốc kích
> hoạt. Tên tệp giữ nguyên để không vỡ các liên kết tới nó.

---

## 1. Vấn đề

Giai đoạn 2 (`neuroedge-roadmap-phase2.md`) mở rộng danh mục phần cứng sang Jetson
(bậc 2), STM32 và RP2350 (bậc 3). Phân tầng bậc đã có đủ trong văn bản — proposal
§3.2 và Phụ lục D.1, PRD FR-TGT-08 và Q-13 — nhưng lược đồ đã đóng băng không công
nhận ba target mới, và mã nguồn không biết bậc là gì.

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

### 1b. Bậc target chỉ tồn tại trong văn bản

FR-TGT-08 đòi *"Bậc được khai báo tường minh, không suy diễn"*, và ngưỡng
`verify` 100% chỉ ràng buộc bậc 1. Nhưng không dòng mã nào biết `jetson` là bậc 2
hay `rp2350` là bậc 3. Hệ quả: không test nào phân biệt được "bo mạch bậc 1 thiếu
`display`" (lỗi) với "bo mạch bậc 3 thiếu `display`" (được phép).

### 1c. Ba test đang ép một tập bo mạch cố định

`python/tests/test_boards.py` hiện khẳng định ba điều đúng cho ba bo mạch tham
chiếu, nhưng viết theo cách vỡ ngay khi danh sách target dài ra:

| Test | Khẳng định | Vỡ thế nào khi thêm target |
|:---|:---|:---|
| `test_one_profile_exists_per_supported_target` | Tập profile trong `boards/` đúng bằng `SUPPORTED_TARGETS` | Đỏ ngay: `jetson`, `stm32`, `rp2350` không có profile, mà profile thật cần phần cứng (§9.4) |
| `test_all_three_targets_share_the_same_named_pins` | Mọi profile khai cùng một tập chân | Một bo mạch bậc 3 điều khiển van công nghiệp phải khai `porch_light` giả để qua |
| `test_every_profile_declares_all_five_primitives` | Mọi profile khai đủ năm nguyên thủy | STM32 không có màn hình; RP2350 không có AEC phần cứng |

---

## 2. Vì sao lược đồ hiện tại không giải quyết được

Với `target`, enum đóng ở cả hai lược đồ và ở Python, đóng một cách nhất quán.
Không có đường mở nào ngoài việc sửa enum.

Ghi thêm một lệch pha liên quan, được sửa ở tầng mã (§3c) chứ không ở lược đồ:
`capabilities` trong `board.v1.json` không có `additionalProperties: false`, nên
một khoá gõ sai như `vison_in` **validate qua**. `board.py::board_from_document()`
giữ nguyên mọi khoá lúc nạp; `_normalise()` chỉ từ chối khi có người **truy vấn**
nguyên thủy đó. Khoá lạ vì vậy được nhận lặng lẽ.

---

## 3. Thay đổi đề xuất

### 3a. Mở rộng enum `target`

`schemas/board.v1.json` và `schemas/trace.v1.json`, trước:

```json
"enum": ["sim", "linux", "esp32s3"]
```

sau:

```json
"enum": ["sim", "linux", "esp32s3", "jetson", "stm32", "rp2350"]
```

kèm `$comment` dẫn chiếu RFC-0002 tại hai chỗ enum, theo tiền lệ RFC-0001.

Enum **vẫn đóng** — đây là chủ ý, xem §6. Cái đổi là danh sách, không phải bản
chất của ràng buộc. Lược đồ chỉ trả lời "tên target này có được công nhận không";
nó không mang bậc.

### 3b. Bậc target máy đọc được, do lõi sở hữu

`python/neuroedge/hal/board.py`:

```python
# FR-TGT-08: bậc cam kết của đội lõi cho từng target. Lõi sở hữu bảng này;
# board.toml không tự khai bậc — một bản port cộng đồng không thể tự nhận bậc 1.
TARGET_TIERS: dict[str, int] = {
    "sim": 1, "linux": 1, "esp32s3": 1,
    "jetson": 2,
    "stm32": 3, "rp2350": 3,
}
SUPPORTED_TARGETS: tuple[str, ...] = tuple(TARGET_TIERS)
```

Bậc là **thuộc tính của target**, không phải của từng bo mạch, và là **lời hứa của
đội lõi**. Nếu để trong `board.toml`, một bo mạch cộng đồng có thể tự khai `tier = 1`
và mượn danh cam kết chất lượng mà đội lõi không đưa ra. Vì vậy tiêu chí chấp nhận
của FR-TGT-08 đổi chữ *"trong `board.toml`"* thành *"trong bảng bậc của mã lõi
(`TARGET_TIERS`); `board.toml` không tự khai bậc"* (§8).

### 3c. Mã đi kèm (không phải lược đồ)

1. **Không ghim cứng "năm".** Thông điệp ở `board.py::_normalise()` và docstring
   sinh từ danh sách nguyên thủy, không viết chữ "five". Tập nguyên thủy **vẫn là
   năm** trong RFC này (FR-HAL-01 không đổi); việc này chỉ để RFC thị giác về sau
   thêm một phần tử mà không phải sửa chữ ở bảy nơi.
2. **Khoá capability lạ bị từ chối lúc nạp.** `board_from_document()` từ chối khoá
   ngoài tập hợp lệ bằng `BoardCapabilityError` ba phần (FR-HAL-05), gợi ý khoá gần
   nhất (`vison_in` → `vision_in` khi khoá đó tồn tại; hôm nay → danh sách năm khoá).
   Làm ở mã chứ không đóng `capabilities` trong lược đồ, vì đóng là siết chặt (§6).
3. **Lỗi target lạ chỉ đường.** Khi lược đồ từ chối `board.target`, phần `how` liệt
   kê target được công nhận theo bậc và trỏ tới RFC này.
4. **CLI.** `neuroedge board show` lặp theo danh sách nguyên thủy thay vì một bộ năm
   tên ghim ở `cli/main.py`. Lệnh mới `neuroedge board validate <path>` nạp một tệp
   TOML bất kỳ và in target, bậc, nguyên thủy có/thiếu. Mọi cờ `--target` / `--targets`
   (`verify`, `run`, `build`, `record`, `replay`) kiểm tên với `SUPPORTED_TARGETS`
   qua một hàm dùng chung; hôm nay `verify --targets esp32s2` thoát 0 lặng lẽ.

---

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | **Có** với lược đồ — không có ngoại lệ nào. Thay đổi lược đồ ở §3a là nới lỏng thuần túy. Riêng bộ nạp Python (§3c.2) từ chối khoá capability lạ mà lược đồ vẫn nhận; không tệp nào trong kho có khoá lạ |
| Tệp đang không hợp lệ có trở nên hợp lệ? | **Có** — `board.toml` và vết ghi khai target bậc 2/3 |
| Tương thích xuôi | **Không có.** Công cụ `neuroedge` bản cũ sẽ từ chối `board.toml` và vết ghi khai `jetson`, `stm32`, `rp2350`, với lỗi enum rõ ràng. Không vết ghi nào ngoài kho phụ thuộc target mới |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | **Không** — xem lập luận dưới |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | **Không** — RFC này không đụng `gate.v1`. Băm gate tính trên tài liệu gate, không liên quan target |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | **Không** — cả ba khai `target: "esp32s3"`, vẫn nằm trong enum mở rộng và vẫn thẩm định qua nguyên trạng |

### Đối chất với tuyên bố `v2` của RFC-0001

RFC-0001 §4 tuyên bố:

> Sau khi Sprint 1 đóng, mọi thay đổi có tính chất này bắt buộc lên `gate.v2`.

Câu này **không áp cho RFC-0002**, vì hai lý do độc lập, mỗi lý do đủ để kết luận:

1. **Phạm vi khác.** Tuyên bố đó nói về `gate.v2` và đứng trong một RFC chỉ sửa
   `gate.v1`. "Thay đổi có tính chất này" trỏ tới hai trường hợp **siết chặt**
   ở RFC-0001 mục 3c và 3d — những thay đổi làm tài liệu đang hợp lệ trở thành
   không hợp lệ. RFC-0002 không có trường hợp siết chặt nào trong lược đồ.
2. **Bản chất khác.** Quy tắc gốc ở `0000-template.md` phân biệt rạch ròi: phá
   vỡ tương thích thì bắt buộc tăng phiên bản; *"nới lỏng (tệp đang không hợp lệ
   trở nên hợp lệ) **có thể làm trong cùng phiên bản**"*. §3a là nới lỏng thuần túy.

Nói cách khác: RFC-0001 phải viện đến "Sprint 1 chưa đóng" làm lý do đặc cách vì
nó **có** siết chặt. RFC-0002 không cần lý do đặc cách nào.

Hệ quả cùng lập luận đó: vì là nới lỏng, thay đổi này **làm được vào bất kỳ lúc
nào** trong `v1` mà không vỡ tài liệu nào. Không có "chi phí viết lại" nào buộc phải
làm sớm — đó là lý do §8 cho phép chờ tới Tháng 9.

Ghi thêm cho minh bạch: nếu hội đồng vẫn muốn `board.v2`/`trace.v2`, chi phí là
hai tệp lược đồ mới, hai `$id` mới, và một kịch bản di trú cho các vết ghi đã
sinh — trong khi lợi ích kỹ thuật bằng không, vì không có tài liệu nào bị vỡ.
Đề nghị giữ `v1`.

---

## 5. Ảnh hưởng an toàn

**Thay đổi này có làm một gate lỏng hơn không: không.** RFC-0002 không đụng
`gate.v1`, không đụng năm nguyên tắc kế thừa (Phụ lục B.5), không đụng mặc định
fail-closed, không đụng `gate_resolver.py`. Gate engine không biết target nào
đang chạy.

Chỗ cần soi là **ba bất biến kiểm thử** ở §1c. Nguyên tắc chung: **thu hẹp phạm vi
theo bậc, không bỏ khẳng định.** Cổng thay thế mà bản đầu của RFC viện dẫn — đối
chiếu `[requires]` của `agent.toml` với bo mạch lúc build (FR-HAL-04) — **chưa tồn
tại**: `neuroedge build` còn là stub (`cli/main.py`, TSK-S2-02), chưa có bộ phân tích
`agent.toml`, và `missing_primitives()` chưa có người gọi nào ngoài test. Bỏ bất biến
trước khi cổng đó tồn tại là để một khoảng không ai canh.

> **Cập nhật 2026-09-24 — tiền đề đã đổi.** Cổng đó nay đã có: `neuroedge build` đối
> chiếu `[requires]` của `agent.toml` với bo mạch (TSK-S2-02, `engine/compiler.py`). Đoạn
> trên giữ nguyên để thấy lập luận lúc review; trước khi duyệt RFC này, rà lại §5a–§5c
> theo cổng hiện có thay vì theo "cổng chưa tồn tại".

### 5a. Tập tên chân chung

| | |
|:---|:---|
| **Vì sao bất biến này tồn tại** | Cách rẻ nhất để bảo đảm cùng một agent chạy được trên các target mà không rẽ nhánh — nguyên tắc P-2 (PRD §1.5), KL-2 của `docs/spec/hal_mcu_review.md` |
| **Vì sao dạng hiện tại không còn đúng** | Nó nhầm *tập tên chân của một lớp usecase* (khóa cửa villa) với *hợp đồng toàn cục*. Bắt một bo mạch STM32 khai `porch_light` giả để qua test là **tệ hơn** cho an toàn |
| **Đổi thành** | Khẳng định giữ nguyên, **áp cho các bo mạch bậc 1**. Bất biến theo agent (*mọi bo mạch được một agent nhắm tới phải khai đủ tập chân mà agent yêu cầu*) chỉ thay vào khi TSK-S2-02 hạ cánh kèm test riêng — không sớm hơn |

### 5b. Đủ năm nguyên thủy

| | |
|:---|:---|
| **Vì sao bất biến này tồn tại** | Với ba bo mạch tham chiếu do đội lõi chọn, nó bắt được lỗi quên khai |
| **Vì sao dạng hiện tại không còn đúng** | Nó biến *năng lực* thành *nghĩa vụ* cho mọi bậc. Ép bo mạch nhỏ khai đủ năm nghĩa là khai gian hoặc loại vĩnh viễn |
| **Đổi thành** | Bậc 1 vẫn phải khai **đủ năm**. Bậc 2/3: nguyên thủy là khai báo có/không. Bo mạch bậc 2/3 không có đường nào chạy agent trước TSK-S2-02, vì `build` và `run` còn là stub, nên không có khoảng nào chạy mà không được canh |

### 5c. Một profile cho mỗi target

`test_one_profile_exists_per_supported_target` đổi thành hai khẳng định: **mỗi
target bậc 1 có đúng một profile** trong `boards/`, và **mọi profile** có target nằm
trong `SUPPORTED_TARGETS`. `boards/` vẫn chỉ chứa profile bậc 1 cho tới khi có phần
cứng thật (§9.4).

### 5d. Rủi ro thật của RFC này

Không nằm ở lược đồ mà ở **cam kết**. Enum sáu target tạo ấn tượng đội lõi bảo
đảm chất lượng cho cả sáu. Không phải vậy:

- **Bậc 1** (`sim`, `linux`, `esp32s3`): `neuroedge verify` 100%, nightly hardware, đội lõi bảo trì.
- **Bậc 2** (`jetson`): đội lõi bảo trì, verify trên miền phán quyết.
- **Bậc 3** (`stm32`, `rp2350`): cộng đồng tự port, tự kiểm chứng qua Bộ kiểm thử
  tuân thủ (proposal §3.8 trụ cột 2). **Đội lõi không cam kết.**

Phân tầng này **đã được ghi** vào proposal §3.2, Phụ lục D.1, KPI và PRD FR-TGT-08
(commit `eddfc59`), nên điều kiện "tài liệu trước, lược đồ sau" đã thỏa. `TARGET_TIERS`
(§3b) đưa đúng bảng đó vào mã.

---

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Tạo `board.v2` và `trace.v2` | Phá tương thích không cần thiết. Không tài liệu nào đang hợp lệ bị vỡ (§4), nên chi phí di trú đổi lấy lợi ích bằng không |
| Bỏ enum `target`, để `"type": "string"` | Mất cổng chặn lỗi chính tả. Một vết ghi khai `target: "esp32s2"` sẽ lặng lẽ qua. Corpus phản chứng `unknown_target.json` mất ý nghĩa |
| Dùng `pattern` thay `enum` (ví dụ `^[a-z0-9]+$`) | Cùng vấn đề trên, chỉ khác mức độ |
| Khai bậc trong `board.toml` (trường `board.tier` trong lược đồ) | Bậc là lời hứa của đội lõi về một target, không phải thuộc tính một bo mạch tự khai. Để trong tệp bo mạch thì một bản port cộng đồng tự nhận được bậc 1; muốn chặn lại phải đối chiếu với bảng lõi, tức hai bản sao phải khớp |
| Đóng `capabilities` bằng `additionalProperties: false` | Là siết chặt — tệp đang hợp lệ có thể trở nên không hợp lệ — nên phải lên `board.v2`. Kiểm khoá lạ ở bộ nạp (§3c.2) đạt cùng mục tiêu |
| Nới hai bất biến theo agent ngay trong RFC này | Cổng build để bất biến mới đứng lên chưa tồn tại (§5) |
| Giữ `vision.in` và `vision_ref` trong RFC này | Chốt hợp đồng tham số camera khi chưa có một camera, một agent thị giác hay bộ đối chiếu `[requires]` nào; mọi sửa sau đó (kiểu `fps`, thêm `required`) là siết chặt, phải lên `board.v2`. Vì mở enum là nới lỏng làm được bất kỳ lúc nào, tách ra không tốn gì. Xem §9.1–9.2 |

---

## 7. Bằng chứng kiểm chứng

*Toàn bộ mục này thuộc **pull request thứ hai**, sau khi RFC được chấp thuận.
Để trống có chủ đích, đúng quy trình `docs/rfc/README.md` bước 2 và 4.*

- [ ] **Không** thêm profile nào vào `boards/`. Profile bậc 2/3 dùng làm bằng chứng là tài liệu tổng hợp trong `tmp_path` / bộ nhớ trong test; vết ghi khai `target: "jetson"` cũng vậy
- [ ] Corpus: giữ `unknown_target.json` với `rp2040` — một lỗi gõ thật, nằm sát `rp2350`, vẫn ngoài enum mới. Chỉ sửa `why_contains` ở `expected_errors.yaml`
- [ ] Test tự động: `test_target_lists_agree` (enum `board.v1` == enum `trace.v1` == `SUPPORTED_TARGETS`), `test_target_tiers_are_declared` (khoá `TARGET_TIERS` == `SUPPORTED_TARGETS`, bậc 1 == `{sim, linux, esp32s3}`), `test_board_schema_enumerates_the_supported_targets` (thay `…_exactly_the_three_targets`), ba bất biến theo bậc ở §5, test khoá capability lạ, test CLI cho `board validate`, `board show` và kiểm tên `--target`
- [ ] `cd python && .venv/bin/python -m pytest -q` xanh, **0 skipped**; `ls boards/` vẫn đúng ba tệp
- [ ] `neuroedge verify` vẫn xanh trên target bậc 1

---

## 8. Việc phải làm khi chấp thuận

**Thời điểm:** pull request thứ hai **không hợp nhất trước Tháng 9** của chương
trình, theo quyết định ở `docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md` (kéo lên
sớm sẽ nạp thêm việc cho đường găng Sprint 2–3). Ngoại lệ duy nhất: sớm hơn khi có
một profile bậc 2/3 **thật** đang được viết.

**Thứ tự: tài liệu trước, mã sau.**

Đã xong trước RFC này (commit `eddfc59`):

- [x] Phân tầng ba bậc ở `neuroedge-proposal.md` §3.2 và Phụ lục D.1
- [x] FR-TGT-08 ở `neuroedge-prd.md` §4.2; Q-13
- [x] KPI của proposal: ngưỡng `verify` 100% chỉ áp cho bậc 1

Tài liệu (cùng pull request với RFC này):

- [x] Sửa chữ tiêu chí chấp nhận FR-TGT-08: bậc nằm trong `TARGET_TIERS` của mã lõi, `board.toml` không tự khai bậc
- [x] `neuroedge-roadmap-phase2.md` Khối V1a: bỏ `vision_in` và `vision_ref` khỏi task và tiêu chí ra; chuyển sang V1b
- [x] `CONTRIBUTING.md`: profile bậc 2/3 cần phần cứng thật

Pull request thứ hai:

- [ ] `schemas/board.v1.json`, `schemas/trace.v1.json`: enum `target` + `$comment` RFC-0002
- [ ] `python/neuroedge/hal/board.py`: `TARGET_TIERS`, `SUPPORTED_TARGETS`, bỏ chữ "five" ghim cứng, kiểm khoá capability lạ lúc nạp, `how` cho target lạ; xuất `TARGET_TIERS` qua `hal/__init__.py`
- [ ] `python/neuroedge/cli/main.py`: `board show` lặp theo danh sách nguyên thủy, `board validate <path>`, hàm kiểm tên target dùng chung
- [ ] `fixtures/traces/expected_errors.yaml`: `why_contains` của `unknown_target.json`
- [ ] `python/tests/test_boards.py`, `test_schemas.py`, `test_cli.py`: theo §5 và §7
- [ ] `CHANGELOG.md`: ghi RFC-0002

---

## 9. Việc còn treo

Các hạng mục cố ý để ngoài phạm vi RFC này, kèm mốc kích hoạt, để không ai phải
suy luận lại:

1. **Nguyên thủy thị giác `vision.in`** — một RFC riêng, mở ở **Khối V1b**, khi đủ
   ba điều kiện: V1b được kích hoạt (≥ 2 khách hàng AURA nêu nhu cầu camera cụ thể),
   có một bo mạch có camera trên bàn, và bộ đối chiếu `[requires]` lúc build
   (TSK-S2-02) đã tồn tại — điều kiện này đã đạt từ 2026-09-23. Đầu vào đã biết cho RFC đó:
   - `sensor.read` không diễn đạt được luồng khung hình (trả vô hướng rời rạc).
   - Hình dạng bản đầu (`width`, `height`, `fps` nguyên, `pixel_format` và
     `accelerator` là chuỗi tự do) không đủ: `fps` phải là `number` (7,5 · 29,97);
     cảm biến có nhiều chế độ nên cần `modes[]`; `pixel_format` cần enum để đối
     chiếu được; và quy tắc so khớp với `[requires]` của agent phải đặc tả **trước**
     khi chốt.
   - Nguyên thủy **tùy chọn theo bo mạch**, bảng năng lực firmware vẫn là mảng tĩnh
     (KL-1, RB-4); ngân sách SRAM đo trên bo mạch thật (Q-3).
   - Bất biến "`sim` không giàu hơn bo mạch tham chiếu" phải được phát biểu lại theo
     từng bo mạch tham chiếu, nếu không agent thị giác không chạy được trên `sim`
     (`TODOS.md` #14).
2. **Bằng chứng thị giác trong vết ghi** — **không cần RFC lược đồ**: `events[].data`
   đã tự do và `metadata` đã mở. Làm khi có **vết ghi thị giác đầu tiên**:
   - Kết quả thị giác (nhãn, hộp, độ tin cậy, mã mô hình) đi vào sự kiện nhóm
     `perception` của Phụ lục C.1 — đó là thứ `replay` dùng để tái hiện phán quyết
     (FR-CI-02). Một mã băm khung hình không replay được.
   - Khung hình chỉ để lại danh tính: `vision_ref` gồm `sha256` và kích thước, không
     nhúng ảnh thô (NFR-PRIV-01, NFR-PRIV-03); chỉ ghi cho khung dẫn tới một quyết
     định, không phải mọi khung (30 fps ≈ 13 MB/giờ vết ghi).
   - Lint ngữ nghĩa trong `trace.py`: `sha256` khớp `^[0-9a-f]{64}$`; `uri` chỉ được
     có khi `metadata.raw_capture == true`; từ chối blob base64 trong `data`. Kèm
     fixture phản chứng trong `fixtures/traces/invalid/` và mục tương ứng trong
     `expected_errors.yaml` — PR thường (`CONTRIBUTING.md` §3 chỉ đòi RFC cho ba vết
     ghi chuẩn mực).
3. **Ngữ nghĩa gate cho bằng chứng thị giác** — bài toán riêng, chạm `gate.v1`, cần
   kỹ thuật trưởng duyệt, thuộc **một RFC riêng (số cấp khi mở)**; hai số RFC kế tiếp
   đã được giữ cho hai thay đổi `gate.v1` ở design doc Giai đoạn 1. **Cho
   tới khi có RFC đó, thị giác chỉ được dùng làm đầu vào thông tin, không được làm
   căn cứ trực tiếp cho phán quyết actuator.**
4. **Profile phần cứng thật cho bậc 2/3** — `boards/jetson-orin-nano.toml`,
   `boards/stm32-*.toml`, `boards/rp2350-*.toml` cần phần cứng thật để điền đúng
   tham số. Phụ thuộc lịch mua sắm; không thuộc pull request thứ hai.

---

## Biên bản review

Biên bản review 2026-09-23 (Review record, Decision Audit Trail, GSTACK REVIEW REPORT) đã chuyển sang [`docs/archive/rfc-0002-review-record.md`](../archive/rfc-0002-review-record.md).
