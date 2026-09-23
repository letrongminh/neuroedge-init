# RFC-0002: Mở rộng danh sách target

| | |
|:---|:---|
| **Mã RFC** | 0002 |
| **Lược đồ bị ảnh hưởng** | `board.v1`, `trace.v1` — **chỉ** enum `target`; **không** đụng `gate.v1` |
| **Yêu cầu PRD liên quan** | FR-TGT-08, FR-HAL-01, FR-HAL-04, FR-HAL-05 |
| **Người đề xuất** | V1 — Kỹ sư lõi nền tảng |
| **Ngày mở** | 2026-09-22 · thu hẹp phạm vi 2026-09-23 sau review (xem *Review record*) |
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
trình, theo quyết định ở `docs/designs/giai-doan-1-wedge-truoc-mcu-sau.md` (kéo lên
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
   (TSK-S2-02) đã tồn tại. Đầu vào đã biết cho RFC đó:
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

## Review record

> **Cách review này đã chạy (2026-09-23).** `/autoplan` bị chặn ở cửa Phase 1: hook
> `phase-publication-hook` của gstack từ chối mọi lần đọc tệp phase vì Claude Code ghi
> một bản ghi `attachment` trước tin nhắn đầu tiên, nên `claude-public-transcript.ts:182`
> không tìm được gốc phiên. Người dùng chọn **D1 → B**: chạy thủ công phương pháp của
> `plan-ceo-review`, `plan-devex-review`, `plan-eng-review` (đọc từ đĩa, đủ các mục),
> auto-decide theo 6 nguyên tắc của autoplan. Mất các cổng tự động của autoplan
> (snapshot từng phase, packet close). **Outside voice Codex: unavailable** — token hết
> hạn (`401 invalid_refresh_token`; sửa: `codex login`). Fallback: một reviewer Claude
> độc lập (ngữ cảnh mới, cùng harness, *không* tính là outside coverage).
>
> Baseline trước review: `cd python && .venv/bin/python -m pytest -q` → **210 passed**.
> Phạm vi UI: không (0 khớp). Phạm vi DX: có (7 khớp "agent"; sản phẩm là công cụ
> cho lập trình viên).

### Phase 1 — CEO review (SELECTIVE EXPANSION)

#### Kiểm hệ thống trước review

- Nhánh `docs/rfc-0002-autoplan` trùng `main` (`8b21ed1`); RFC-0002 đã có trên `main`.
- Quyết định đang hiệu lực (sổ quyết định gstack, 2026-09-22): **Giai đoạn 1 chạy
  Phương án A** — Sprint 2–3 (`sim` + `linux` + Action CI, ~4 tuần) rồi dừng để đưa
  cho 3 U2 có tên. Roadmap §0: Sprint 1 ở 92 %, Sprint 2 ở 0 %.
- `neuroedge-roadmap-phase2.md:152–171`: Khối V1a (chính là RFC-0002) xếp ở
  **Tháng 9–11** của chương trình, kích hoạt bởi "RFC-0002 được phê duyệt".
- `docs/designs/giai-doan-1-wedge-truoc-mcu-sau.md:1499–1523` đã **giữ số** RFC-0003
  (ghim `extends` bằng `#sha256`, cây quyết định chạy xuống silicon) và RFC-0004
  (kế thừa `budget`/`on_block` — lỗ `lax-night` đã chứng minh bằng chạy thật).
  Chưa RFC nào trong hai cái đó được viết.

#### 0A. Thách thức tiền đề

| # | Tiền đề trong RFC / tài liệu | Đánh giá | Bằng chứng |
|:---:|:---|:---|:---|
| P1 | "Phải đặt chỗ trong lược đồ **bây giờ**, nếu không bổ sung muộn sẽ phải viết lại" (proposal:1297, phase2:154 "trước khi chi phí thay đổi trở nên quá đắt") | **Sai, theo chính lập luận của RFC.** §4 chứng minh mọi thay đổi là *nới lỏng thuần túy*, được làm **trong cùng `v1` vào bất kỳ lúc nào** (`0000-template.md`). Một thay đổi làm muộn được mà không vỡ tài liệu nào thì không có chi phí viết lại để phòng. Chi phí không làm gì trong Giai đoạn 1: **bằng không** — không task nào của Sprint 2–3 cần `jetson`/`stm32`/`rp2350` hay `vision.in` | RFC §4 hàng 1–3; `0000-template.md`; roadmap §0 |
| P2 | "Nới 5a/5b không làm lỏng, vì đối chiếu năng lực lúc build (FR-HAL-04) đã là cổng thật" | **Sai ở hiện tại.** `neuroedge build` là stub (`cli/main.py:522` `_not_yet("build")`, TSK-S2-02); không có `agent.toml`, không có bộ phân tích `[requires]`; `missing_primitives()` không có người gọi nào ngoài test. Bỏ bất biến test trước khi cổng build tồn tại là mở một khe không có gì canh | `cli/main.py:517–522`; `board.py:161`; `grep -rn agent.toml` chỉ khớp một `description` trong `gate.v1.json:15` |
| P3 | "Phân tầng bậc là hợp đồng sản phẩm, **không** mã hoá vào lược đồ" (§3a) | **Mâu thuẫn với PRD** — nguồn sự thật ưu tiên cao hơn. FR-TGT-08 (`prd:276`) đặt tiêu chí chấp nhận *"Mỗi target có bậc ghi trong tài liệu **và trong `board.toml`**"*. Một trong hai phải đổi | `neuroedge-prd.md:276` |
| P4 | "Vết ghi thiếu khung hình phá mệnh đề tái hiện sự cố FR-CI-02" (§1c) → giải bằng `vision_ref` chỉ có băm | **Lời giải không khớp vấn đề.** Không replay được từ một mã băm. Thứ replay cần là *kết quả nhận thức* (nhãn, hộp, độ tin cậy, mã mô hình), và Phụ lục C.1 đã có sẵn nhóm sự kiện `perception` cho đúng việc đó (`proposal:1521`). Băm chỉ cho *danh tính* khung hình để đối soát | `neuroedge-proposal.md:1518–1523` |
| P5 | Thứ tự ưu tiên ngầm: RFC-0002 là RFC tiếp theo cần kỹ thuật trưởng duyệt | **Sai thứ tự.** Hai RFC đang giữ số (0003, 0004) vá lỗ an toàn **đã chứng minh** trên `gate.v1` và nằm trên đường găng Giai đoạn 1; RFC-0002 không chạm an toàn và không nằm trên đường găng. Băng thông kỹ thuật trưởng là tài nguyên khan hiếm nhất | design doc:1419, 1499, 1523 |

**Vấn đề thật:** Giai đoạn 2 cần lược đồ công nhận thêm target và năng lực camera.
**Kết quả mục tiêu:** tiêu chí ra Khối V1a (`phase2:169–175`). **Kế hoạch giải trực
tiếp** phần target; phần `vision_ref` hiện giải một *proxy* (danh tính khung hình)
thay cho vấn đề đã nêu (tái hiện).

#### 0B. Mã sẵn có tận dụng được

| Bài toán con | Đã có | Tận dụng? |
|:---|:---|:---|
| Từ chối tên target lạ | `enum` ở hai lược đồ + corpus `unknown_target.json` | Có — chỉ đổi danh sách |
| "Bo mạch có năng lực X không" | `BoardProfile.supports()` / `missing_primitives()` (`board.py:103,161`) | Có — nhưng chưa ai gọi lúc build |
| Thông báo lỗi ba phần | `BoardCapabilityError` + FR-HAL-05 (`board.py:66–76`) | Có — cần sửa chữ "five" |
| Kết quả nhận thức trong vết ghi | Nhóm sự kiện `perception` (Phụ lục C.1) | **Chưa** — RFC phát minh `vision_ref` trong `input` thay vì dùng `perception` |
| Trường metadata mở | `metadata.additionalProperties: true` (TODOS #1) | Có — cờ `raw_capture` thêm được không cần RFC |
| Phân tầng bậc trong văn bản | proposal §3.2 (:388–398), D.1 (:1555–1567), KPI (:1385), PRD FR-TGT-08, Q-13 | **Đã xong** ở `eddfc59` — ba mục đầu của §8 thực ra đã làm |

#### 0C. Trạng thái mơ ước

```
  HIỆN TẠI                         RFC-0002 (như viết)                 LÝ TƯỞNG 12 THÁNG
  3 target, enum đóng        --->  6 target trong enum; vision_in  --->  Bậc là dữ liệu máy đọc được, do lõi
  5 nguyên thủy, bắt buộc          khai hình dạng; 2 bất biến test        sở hữu; cổng build đối chiếu năng lực
  build = stub                     bị nới trước khi build tồn tại         theo agent.toml; vision_in chốt hình
  tier chỉ ở văn bản               tier vẫn chỉ ở văn bản                 dạng SAU khi có camera thật; vết ghi
                                                                          replay được kết quả nhận thức
```

Kế hoạch **đi đúng hướng** ở phần target, **đi trước quá sớm** ở phần `vision_in`
(chốt hợp đồng tham số khi chưa có một camera, một agent thị giác hay một bộ đối
chiếu `[requires]` nào), và **đi lệch** ở phần `vision_ref` (P4).

#### 0D. Phương án

| | A — RFC như viết (một gói, PR thứ hai sửa cả ba) | B — Tách: phần target duyệt nay, `vision_in` + `vision_ref` hoãn tới cổng V1b | C — Hoãn toàn bộ RFC tới Tháng 9 |
|:---|:---|:---|:---|
| Công sức | S (PR2: ~10 tệp) | S (PR2: ~7 tệp) + một bản sửa RFC về sau | S (không việc) |
| Rủi ro | Trung bình: chốt hình dạng `vision_in` không bằng chứng; nới bất biến trước cổng build | Thấp | Thấp, nhưng cộng đồng port bậc 3 bị chặn tới Tháng 9 |
| Nguyên tắc | — | P3 (thực dụng), P5 (tường minh), P1 cho phần target | P6 ngược (trì hoãn) |

**Auto-decide:** không đổi hướng của người dùng ở phase này. Phương án B **đổi
hướng người dùng đã nêu** (một RFC ba phần) nên thuộc loại *User Challenge / Taste*
— **đưa lên cổng cuối, không tự quyết** (xem Decision Audit Trail #3). Mọi phân
tích bên dưới review gói A **kèm** các sửa lỗi cần thiết, để cổng cuối chọn được cả
hai đường.

#### 0E. Chế độ

Đếm tệp PR2 dự kiến: 2 lược đồ, `board.py`, `hal/__init__.py`, `cli/main.py`,
`test_boards.py`, `test_schemas.py`, `test_cli.py`, `fixtures/traces/expected_errors.yaml`,
`proposal` C.1, `docs/spec/hal_mcu_review.md` KL-1 ≈ **11 tệp**, không có lớp mới.
Là thêm năng lực vào sản phẩm có sẵn → **SELECTIVE EXPANSION** (mặc định của
autoplan cho CEO). Auto-decided.

#### 0F/0G. Kiểm HOLD + ứng viên mở rộng

HOLD: (1) 11 tệp > 8 → thách độ phức tạp: phương án B cắt còn ~7. (2) Tối thiểu cho
mục tiêu *target*: enum + `SUPPORTED_TARGETS` + corpus + test. (3) Bất biến phải giữ:
`CHANGELOG.md` §3.3 #7 (`sim` không giàu hơn bo mạch tham chiếu), FR-HAL-05, KL-1
bảng tĩnh.

10x: một người ngoài port NeuroEdge lên RP2350 **không cần hỏi đội lõi** — khai
`boards/rp2350-x.toml`, chạy một lệnh, biết ngay mình đạt/thiếu gì so với bậc 3.
RFC này mới mở cánh cửa lược đồ; con đường đó là Khối P1.

| # | Ứng viên | Công sức | Quyết định | Lý do |
|:---:|:---|:---:|:---|:---|
| E1 | `verify --targets` kiểm tên target với `SUPPORTED_TARGETS`, lỗi ba phần | S | **ACCEPTED** (P2: trong bán kính, < 1 ngày) | `cli/main.py:419` nhận mọi chuỗi; `--targets esp32s2` in dấu chấm lặng lẽ. RFC §6 dựa vào "bắt lỗi chính tả" nên phải bắt ở cả CLI |
| E2 | `board show` lặp theo `PRIMITIVES` thay vì bộ năm hằng | S | **ACCEPTED** (P4 DRY, bắt buộc) | `cli/main.py:398` ghim cứng năm tên → `vision.in` sẽ không bao giờ hiện |
| E3 | Thông báo lỗi target lạ có "how" chỉ đường (danh sách + bậc + RFC) | S | **ACCEPTED** (P1) | Hôm nay người port chỉ thấy `'rp2040' is not one of [...]` từ jsonschema |
| E4 | Lệnh `neuroedge board check <file>` báo đạt/thiếu so với bậc | M | **DEFERRED** → TODOS (Khối P1) | Cần bộ vector tuân thủ, chưa có |
| E5 | Kiểm `vision_ref.uri` chỉ khi `metadata.raw_capture: true` | S | **ACCEPTED nếu giữ `vision_ref`** (P1, NFR-PRIV-03) | Hôm nay không gì cưỡng chế lời hứa riêng tư |

#### 0I. Hỏi theo thời gian (cho người làm PR2)

```
  GIỜ 1   Biết: tách PRIMITIVES thành CORE (5, bắt buộc bậc 1) + OPTIONAL (vision.in).
  GIỜ 2-3 Sẽ vấp: test_one_profile_exists_per_supported_target đỏ ngay khi thêm target;
          "five HAL primitives" ghim ở board.py:70 và test_boards.py:60.
  GIỜ 4-5 Bất ngờ: board show ghim 5 tên (cli/main.py:398); test_cli.py:174 ghim 5 tên.
  GIỜ 6+  Ước gì đã tính: tier đặt ở đâu (PRD nói board.toml); sim-parity vs camera ảo.
```
Công sức PR2 (gói A + sửa): human ~1,5 ngày / CC ~30 phút.

#### Mục 1 — Kiến trúc

```
                  (host, workstation)                                   (thiết bị)
  boards/*.toml ──► load_board ──► validate(board.v1) ──► BoardProfile ──► [build: TSK-S2-02 ⛔ stub]
       │                                   │                    │               │
       │                        enum target (3→6)        supports()/missing_primitives()
       │                        capabilities (+vision_in)        │               ▼
       ▼                                                          └──(chưa ai gọi)  bảng năng lực const
  agent.toml [requires] ⛔ chưa tồn tại ─────────────────────────────►  (RB-4, 5→6 phần tử)

  traces/*.json ──► load_trace ──► validate(trace.v1) ──► ReplaySession
                                   enum metadata.target (3→6)
                                   events[].data tự do  ◄── vision_ref (không được kiểm)
```

- **CRITICAL GAP (A1):** hai mũi tên ⛔ là chính cổng an toàn mà §5a/§5b viện dẫn.
  Nới bất biến test trước khi chúng tồn tại = không có gì canh trong khoảng giữa.
- Coupling mới: `SUPPORTED_TARGETS` (Python) ↔ enum (hai lược đồ) ↔ chuỗi
  `why_contains` (corpus) — ba bản sao của cùng một danh sách. Đã có từ trước; RFC
  không làm tệ hơn nhưng nên thêm test "Python == lược đồ" (xem Eng).
- Rollback: PR2 là thay đổi dữ liệu + test, revert một commit, < 5 phút. Không có
  vết ghi nào ngoài kho phụ thuộc target mới.

#### Mục 2 — Bản đồ lỗi & cứu

| Năng lực / đường mã | Cái gì hỏng | Lớp lỗi | Cứu? | Người dùng thấy |
|:---|:---|:---|:---:|:---|
| `validate_board_document` với target lạ | enum từ chối | `BoardCapabilityError` (NE3001) | Có | `'x' is not one of [...]` — **thiếu hướng dẫn** (E3) |
| `load_board` với `vison_in` (gõ sai) | lược đồ mở, nhận lặng lẽ | — | **Không ← GAP** | Im lặng; agent cần camera sẽ thấy "not provided" mà không biết vì sao |
| `BoardProfile.supports("vision.in")` trước PR2 | `_normalise` từ chối | `BoardCapabilityError` | Có | Thông báo nói "five", chỉ đường RFC — đúng |
| `load_trace` có `vision_ref.uri` khi không bật lưu thô | không kiểm | — | **Không ← GAP** | Im lặng; vi phạm NFR-PRIV-03 không ai thấy |
| `verify --targets esp32s2` | không kiểm tên | — | **Không ← GAP** | Dấu `·` mờ, exit 0 |

#### Mục 3 — Bảo mật & mô hình đe doạ

| Mối đe doạ | Khả năng | Tác động | Kế hoạch giảm? |
|:---|:---:|:---:|:---|
| Bo mạch cộng đồng **tự khai bậc 1** nếu `tier` nằm trong `board.toml` (theo chữ FR-TGT-08) | Trung bình | Cao — lời hứa chất lượng của đội lõi bị mạo danh | **Không** — cần quyết định (Taste #1) |
| `vision_ref.uri` trỏ ra URL ngoài → rò ảnh người trong nhà qua vết ghi dán vào issue | Thấp | Cao (PII hình ảnh) | Không — E5 |
| Khung hình băm SHA-256 không muối: ảnh phổ biến / khung hình tĩnh có thể dò lại qua băm | Thấp | Trung bình | Không — ghi chú là "danh tính, không phải bí mật" |
| Nới bất biến tập chân → một agent gọi `porch_light` chạy qua trên bo mạch không có chân đó | Trung bình (khi có bo mạch bậc 2/3) | Trung bình — hỏng lúc chạy, không lúc build | Không, cho tới TSK-S2-02 (A1) |

Không có endpoint mới, bí mật mới hay phụ thuộc mới.

#### Mục 4 — Luồng dữ liệu & biên

```
  board.toml ──► TOML parse ──► schema ──► BoardProfile ──► (build match ⛔)
     nil: tệp không có → NE3001 "does not exist" ✓
     rỗng: [capabilities] trống → hợp lệ, "không năng lực gì" ✓ (đúng ngữ nghĩa có/không)
     sai kiểu: fps = "30" → schema từ chối ✓ ; fps = 29.97 → schema từ chối ✗ (camera NTSC thật)
     khoá lạ: vison_in → nhận lặng lẽ ✗ GAP
  frame ──► sha256 ──► event.data.vision_ref ──► trace ──► replay
     30 fps × mỗi khung = 108.000 sự kiện/giờ → vượt mốc streaming TODOS #3 trong ~55 phút ✗
```

#### Mục 5 — Chất lượng mã

- `PRIMITIVES` đang mang hai nghĩa ("tập hợp lệ" và "tập bắt buộc"). Thêm
  `vision.in` vào mà không tách sẽ hoặc bắt mọi bo mạch có camera, hoặc làm bất
  biến bậc 1 vô nghĩa. Tách `CORE_PRIMITIVES` / `OPTIONAL_PRIMITIVES`.
- Chuỗi "five" ở `board.py:15–19, 40, 70`, `cli/main.py:377`, `test_boards.py:60`,
  `test_cli.py:174`, `hal_mcu_review.md` KL-1 "đúng năm", PRD FR-HAL-01 "đúng 5".
- DRY: `cli/main.py:398` lặp lại danh sách nguyên thủy.

#### Mục 6 — Test

Chi tiết ở Phase 3. Điểm CEO: bốn test hiện có đỏ/sai nghĩa khi PR2 hợp nhất
(`test_one_profile_exists_per_supported_target`, `test_every_profile_declares_all_five_primitives`,
`test_unknown_primitive_is_refused`, `test_board_schema_enumerates_exactly_the_three_targets`,
`test_board_show_lists_all_five_primitives`) — §8 chỉ nêu hai.

#### Mục 7 — Hiệu năng

Bảng năng lực +1 phần tử, tĩnh: không đáng kể. Rủi ro thật là **dung lượng vết ghi**:
`vision_ref` ~120 byte/sự kiện; ghi mọi khung ở 30 fps ≈ 13 MB/giờ và 100.000 sự kiện
sau ~55 phút (mốc TODOS #3). Cần quy tắc "chỉ ghi khung dẫn tới quyết định".

#### Mục 8 — Quan sát được

Vết ghi là nền quan sát (TODOS #6). Gap: vết ghi không nói phiên có bật lưu thô
hay không → người hậu kiểm không phân biệt được "không có uri vì tắt" với "bị mất".
`metadata.raw_capture` (mở sẵn) giải được.

#### Mục 9 — Triển khai

Không migration, không cờ tính năng. Thứ tự đúng: **tài liệu → lược đồ** (RFC tự nói),
và thêm: **cổng build (TSK-S2-02) → nới bất biến**. Rủi ro cửa sổ: công cụ `neuroedge`
cũ sẽ từ chối vết ghi `target: "jetson"` — tương thích **xuôi** không có, §4 chưa ghi.

#### Mục 10 — Quỹ đạo dài hạn

- Khả năng đảo ngược: **4/5** cho target (bỏ một giá trị enum sau này là *siết chặt*
  → phải `v2`, nên thêm là dễ, bớt là khó); **2/5** cho hình dạng `vision_in` (sửa kiểu
  `fps` hay thêm `required` về sau đều là siết chặt → `board.v2`).
- Nợ: ba bản sao danh sách target; "five" rải 7 chỗ.
- Nền tảng: mở đường cho P1 (bộ công cụ port). Không chặn gì.

#### Mục 11 — Thiết kế & UX

SKIPPED (no UI scope).

<!-- autoplan-accepted:ceo -->
- PR2 (thực thi RFC-0002) KHÔNG nới `test_all_three_targets_share_the_same_named_pins` và `test_every_profile_declares_all_five_primitives` cho tới khi `neuroedge build` đối chiếu năng lực thật (TSK-S2-02) tồn tại; trước mốc đó chỉ được *thu hẹp phạm vi* hai bất biến về các bo mạch bậc 1, giữ nguyên khẳng định. Kiểm: hai test vẫn chạy trên `sim-default`, `linux-rpi5`, `esp32s3-box-3` và vẫn xanh.
- §8 của RFC đánh dấu ba mục đầu là đã xong ở `eddfc59`, kèm dẫn chiếu dòng. Kiểm: `grep -n "bậc" neuroedge-proposal.md` khớp :388–398, :1385, :1555–1567; `prd:276`.
- §9.1 đổi "RFC-0003" thành "một RFC riêng (số cấp khi mở)", vì 0003/0004 đã được giữ cho `gate.v1` ở design doc Giai đoạn 1. Kiểm: `grep -n "RFC-0003" docs/rfc/0002-*.md` không còn trong §9.
- E1: `neuroedge verify --targets` từ chối tên ngoài `SUPPORTED_TARGETS` với lỗi ba phần, exit 1. Kiểm: test CLI mới với `--targets esp32s2`.
- E2: `neuroedge board show` lặp theo `PRIMITIVES`. Kiểm: `test_board_show_lists_all_five_primitives` đổi thành lặp theo `PRIMITIVES` và vẫn xanh.
- E3: lỗi target lạ ở `board.toml` có phần `how` liệt kê target hợp lệ và trỏ RFC-0002. Kiểm: `test_unsupported_target_is_reported` khẳng định thêm `how`.
- §4 thêm một hàng: công cụ `neuroedge` bản cũ từ chối tệp khai target mới (không có tương thích xuôi).
<!-- /autoplan-accepted:ceo -->

**Ghi chú:** E5 và các sửa `vision_ref`/`vision_in` phụ thuộc lựa chọn ở cổng cuối
(giữ gói A hay tách B), nên chưa vào khối accepted.

#### NOT in scope (CEO)

- E4 `neuroedge board check` — **deferred** tới Khối P1 (cần bộ vector tuân thủ).
- Ngữ nghĩa gate trên bằng chứng thị giác — RFC tự để ngoài (§9.1), đồng ý.
- Ba board profile phần cứng thật trong `boards/` — chờ phần cứng (§9.3), đồng ý.

#### What already exists (CEO)

Xem bảng 0B. Điểm chính: phân tầng bậc đã có đủ trong văn bản; nhóm sự kiện
`perception` đã có cho kết quả nhận thức; `metadata` đã mở cho cờ `raw_capture`.

#### Dream state delta

Sau RFC này (gói A + sửa): lược đồ công nhận 6 target, bậc vẫn chỉ ở văn bản, cổng
build vẫn là stub. Còn thiếu so với lý tưởng: bậc máy đọc được, cổng `[requires]`,
hình dạng `vision_in` có bằng chứng phần cứng, vết ghi replay được kết quả nhận thức.

#### Failure Modes Registry (CEO)

```
  CODEPATH                        | FAILURE MODE                         | RESCUED? | TEST? | USER SEES?          | LOGGED?
  --------------------------------|--------------------------------------|----------|-------|---------------------|--------
  board load, khoá capability lạ  | vison_in gõ sai được nhận            | N        | N     | Silent              | N   ← CRITICAL GAP
  trace load, vision_ref.uri      | lưu thô khi chưa bật                 | N        | N     | Silent              | N   ← CRITICAL GAP (nếu giữ vision_ref)
  verify --targets                | tên target sai                       | N        | N     | Silent (exit 0)     | N   ← CRITICAL GAP → E1 vá
  bất biến tập chân bị nới        | agent gọi chân bo mạch không có      | N        | N     | Lỗi lúc chạy        | —   (A1: không nới trước TSK-S2-02)
  enum target mới                 | công cụ cũ từ chối vết ghi mới       | Y        | N     | Lỗi rõ (enum)       | Y
```

#### CEO Completion Summary

```
  +====================================================================+
  |            MEGA PLAN REVIEW — COMPLETION SUMMARY                   |
  +====================================================================+
  | Mode selected        | SELECTIVE EXPANSION                         |
  | System Audit         | RFC-0003/0004 đã giữ số; build là stub;     |
  |                      | §8 mục 1-3 đã xong; baseline 210 passed     |
  | Step 0               | 5 tiền đề bị thách (P1,P2,P4,P5 sai; P3 lệch |
  |                      | PRD); tách RFC → cổng cuối                  |
  | Section 1  (Arch)    | 2 issues (A1 critical, coupling 3 bản sao)  |
  | Section 2  (Errors)  | 5 đường lỗi, 3 GAPS                         |
  | Section 3  (Security)| 4 issues, 2 High                            |
  | Section 4  (Data/UX) | 7 biên, 3 unhandled                         |
  | Section 5  (Quality) | 3 issues                                    |
  | Section 6  (Tests)   | 5 test đỏ/sai nghĩa, §8 nêu 2               |
  | Section 7  (Perf)    | 1 issue (dung lượng vết ghi)                |
  | Section 8  (Observ)  | 1 gap (raw_capture)                         |
  | Section 9  (Deploy)  | 2 risks (thứ tự cổng build; tương thích xuôi)|
  | Section 10 (Future)  | Reversibility: 4/5 target, 2/5 vision_in    |
  | Section 11 (Design)  | SKIPPED (no UI scope)                       |
  +--------------------------------------------------------------------+
  | NOT in scope         | written (3 items)                           |
  | What already exists  | written                                     |
  | Dream state delta    | written                                     |
  | Error/rescue registry| 5 rows, 3 CRITICAL GAPS                     |
  | Failure modes        | 5 total, 3 CRITICAL GAPS                    |
  | TODOS.md updates     | 1 item proposed (E4)                        |
  | Scope proposals      | 5 proposed, 3 accepted, 1 conditional, 1 deferred |
  | CEO plan             | skipped (chạy thủ công; ghi trong tệp này)  |
  | Outside voice        | codex unavailable (401); Claude subagent    |
  | Lake Score           | N/A (auto-decide, không câu hỏi coverage)   |
  | Diagrams produced    | 3 (dream state, kiến trúc, luồng dữ liệu)   |
  | Stale diagrams found | 1 (board.py docstring "five primitives")    |
  | Unresolved decisions | 2 (tách RFC; chỗ đặt tier) → cổng cuối      |
  +====================================================================+
```

#### Outside voice — Phase 1

- **Codex:** unavailable. `codex exec` thoát 1 sau 5 lần kết nối lại:
  `401 Unauthorized … invalid_refresh_token`. Sửa: `codex login`. Không có CROSS-MODEL.
- **Fallback:** một reviewer Claude độc lập (ngữ cảnh mới, cùng harness; *không* tính
  là outside coverage), chạy một lần cho cả chiến lược lẫn kỹ thuật. 12 phát hiện,
  verdict: *"reject as written; resubmit split"*.

Đối chất (mỗi phát hiện đã kiểm lại trong mã trước khi nhận):

| # | Reviewer nói | Kiểm lại | Xử lý |
|:---:|:---|:---|:---|
| R1 | Không có đối chiếu lúc build; §5a/§5b đổi cổng thật lấy khoảng trống | Đúng — `cli/main.py:522`; `missing_primitives` chỉ test gọi | Trùng A1 → accepted CEO |
| R2 | Thêm `vision.in` vào `PRIMITIVES` làm đỏ cả ba bo mạch bậc 1 | Đúng — `test_boards.py:41` so với `PRIMITIVES`; §9.2 cấm `vision_in` trên esp32s3 | Tách hằng → accepted Eng |
| R3 | Tiền đề PF-2 tự mâu thuẫn; design doc Giai đoạn 1 **đã chủ động giữ RFC-0002 ở Tháng 9** | Đúng — `giai-doan-1-wedge-truoc-mcu-sau.md:359–361`: *"kéo lên Tuần 4 sẽ nạp thêm cho đường găng đúng lúc A2 đang chạy. Giữ Tháng 9."* | Củng cố P1; PR2 không hợp nhất trước Tháng 9 → **User Challenge** ở cổng cuối cùng với việc tách |
| R4 | Danh sách vỡ đầy đủ | Đúng, thêm được `_CAPABILITY_KEYS` (`board.py:50–56`), `--target` của `run/build/record/replay` không kiểm | Gộp vào Eng |
| R5 | Bậc vừa "không ở lược đồ" vừa "ở `board.toml`" | Đúng — trùng P3 | Taste #1 ở cổng cuối |
| R6 | Vision không test được trên `sim` nếu giữ bất biến #7 | Đúng — KL-3 + §9.2 | Ghi vào §9 → TODOS |
| R7 | §7 ↔ §9.3 | Đúng | Eng: profile tổng hợp trong `tmp_path` |
| R8 | §1d và §8 cũ | Đúng — D.1 đã có RP2350 (`proposal:1557`) | Accepted CEO (§8) + sửa §1d |
| R9 | `_normalise` chỉ chạy lúc hỏi, không lúc nạp; §2 chẩn đoán sai | Đúng — `board_from_document` (`board.py:221–230`) giữ mọi khoá | Eng: kiểm khoá lạ lúc nạp |
| R10 | Hình dạng `vision_in` kém (`fps` nguyên, không `modes[]`, chuỗi tự do) | Đúng | Củng cố tách B |
| R11 | `vision_ref` không cưỡng chế được và không khôi phục replay; `input` là nhóm sự kiện, không phải trường | Đúng — trùng P4 | Củng cố tách B / lint |
| R12 | Người duyệt không rõ; tiêu chí V1a 4–5 phụ thuộc stub | Đúng — `phase2:171` đòi chữ ký kỹ thuật trưởng; header RFC chỉ "đề nghị" | Accepted Eng |

**Bảng đồng thuận CEO** (Claude chính × reviewer Claude độc lập; Codex N/A):

| Chiều | Claude chính | Reviewer độc lập | Codex | Đồng thuận |
|:---|:---:|:---:|:---:|:---:|
| Tiền đề đúng? | Không (P1, P2, P4, P5) | Không | N/A | CÙNG (cùng harness) |
| Đúng vấn đề để làm bây giờ? | Không — Tháng 9 | Không — Tháng 9 | N/A | CÙNG |
| Nên tách RFC? | Nên (B) | Nên (a/b/c) | N/A | CÙNG |
| Phần target an toàn? | Có | Có | N/A | CÙNG |
| Nới bất biến trước TSK-S2-02? | Không | Không | N/A | CÙNG |
| Rủi ro 6 tháng | Chốt `vision_in` sai → `board.v2` | Như trái | N/A | CÙNG |

Hai góc nhìn cùng mô hình đồng ý ≠ xác nhận độc lập. Đó là lý do việc tách RFC
**không** được tự quyết.

### Phase 2 — Design review

Skipped — không phát hiện phạm vi UI (0 lần khớp các từ component/screen/form/…).
Không phải một review đã hoàn tất.

### Phase 2.5 — DX review (DX POLISH)

**Loại sản phẩm:** CLI Tool + hợp đồng dữ liệu (lược đồ). Chế độ: **DX POLISH**
(nâng cấp sản phẩm có sẵn; auto-decided).

#### 0A. Chân dung lập trình viên mục tiêu

```
TARGET DEVELOPER PERSONA
========================
Who:       Kỹ sư nhúng cộng đồng muốn port NeuroEdge lên RP2350 (bậc 3) — đúng người
           mà RFC mở cửa cho (proposal §3.2, :396; V-G5 ≥ 3 bản port bậc 3).
Context:   Đã có Pico 2 W trên bàn, đọc README/proposal, muốn biết "bo mạch của tôi
           có được công nhận không, và tôi thiếu gì".
Tolerance: ~15 phút tới tín hiệu đầu tiên "profile của tôi hợp lệ". Không đọc 1.700
           dòng proposal.
Expects:   Một tệp mẫu để sao, một lệnh kiểm, lỗi nói rõ sửa gì, một trang hướng dẫn port.
```
Chân dung phụ: V1 (người viết PR2) — cần danh sách vỡ đầy đủ và thứ tự làm.

#### 0B. Câu chuyện thấu cảm (hôm nay, sau khi RFC-0002 hợp nhất như viết)

> Tôi clone kho, thấy `boards/esp32s3-box-3.toml`, sao thành `boards/rp2350-pico2w.toml`,
> sửa `target = "rp2350"`, bỏ `display` vì Pico không có màn hình. Chạy
> `neuroedge board show rp2350-pico2w` — ổn, bảng hiện `display: not provided`. Tốt.
> Tôi chạy `pytest` như CONTRIBUTING bảo và **đỏ hai chỗ**: `test_one_profile_exists_per_supported_target`
> nói tập profile phải đúng ba cái, còn `test_all_three_targets_share_the_same_named_pins`
> nói chân của tôi phải là `door_lock, porch_light, gate_relay`. CONTRIBUTING:93 bảo
> *"Thêm profile bo mạch ở `boards/` — PR thường"*, nhưng không PR thường nào qua được CI.
> Tôi không biết bậc 3 nghĩa là gì trong mã, không có lệnh nào nói "profile của bạn đạt
> yêu cầu bậc 3", và không có hướng dẫn port. Tôi mở issue.

*(Quan sát: bước `board show`, hai test đỏ, CONTRIBUTING:93 — kiểm trong mã. Dự đoán:
cảm xúc và việc mở issue.)*

#### 0C. So sánh DX

| Công cụ | Bắt đầu → kết quả | Thời gian + loại bằng chứng | Lựa chọn DX | Nguồn |
|:---|:---|:---|:---|:---|
| Zephyr (thêm board) | sao board mẫu → `west build -b <board>` | ước lượng 30–60 phút, tài liệu "Board Porting Guide" | hướng dẫn port chính thức + board mẫu | kiến thức sẵn có (không tra web) |
| ESPHome (thêm board) | khai `board:` trong YAML → `esphome config` | ước lượng < 5 phút, lệnh `config` kiểm tĩnh | lệnh validate không cần phần cứng | kiến thức sẵn có |
| **NeuroEdge sau RFC (như viết)** | sao TOML → `board show` → `pytest` | ~5 phút tới `board show`; **không bao giờ xanh** ở `pytest` | không có lệnh validate tệp ngoài kho; test ép tập cố định | quan sát trong kho |

Tra cứu web: không chạy (Aside không kiểm; auto-decide dùng kiến thức sẵn có). Thời
gian là ước lượng, không đo.

**Mục tiêu TTHW (auto-decided, recommended):** *Competitive (2–5 phút)* tới "profile
bậc 3 của tôi hợp lệ và CI xanh", với điều kiện PR2 làm các sửa dưới.

#### 0D. Khoảnh khắc "à, thật này"

Người port chạy `neuroedge board validate boards/rp2350-pico2w.toml` và thấy:
target `rp2350` · **bậc 3 (cộng đồng)** · 4/5 nguyên thủy lõi (thiếu `display`, được
phép ở bậc 3) · `vision.in`: không khai. Vehicle: lệnh `board validate <path>` dùng
`load_board()` sẵn có (`board.py:233`) + bảng bậc. Auto-decided (P2: trong bán kính,
< 1 ngày, 2 tệp).

#### 0F. Hành trình

```
STAGE           | DEVELOPER DOES                              | FRICTION POINTS                                  | STATUS
----------------|---------------------------------------------|--------------------------------------------------|---------
1. Discover     | đọc proposal §3.2 bậc 3                     | không có trang "port lên bậc 3" ngắn             | deferred (Khối P1)
2. Install      | clone + `.venv` theo CHANGELOG §2.1         | —                                                | ok
3. Hello World  | sao TOML, sửa target, `board show`          | chỉ tìm trong `boards/` của kho                  | fixed (board validate <path>)
4. Real Usage   | `pytest`                                    | 2 test ép tập profile/tập chân cố định → đỏ      | fixed (bất biến theo bậc, xem Eng)
5. Debug        | đọc lỗi `'rp2040' is not one of [...]`      | không nói target nào hợp lệ theo bậc, không trỏ RFC | fixed (E3)
6. Upgrade      | lên bản neuroedge mới / cũ                  | bản cũ từ chối vết ghi target mới, không báo     | fixed (ghi vào §4)
```

#### 0G. Báo cáo người mới

```
FIRST-TIME DEVELOPER REPORT
============================
Persona: kỹ sư port RP2350
Attempting: khai profile bậc 3
CONFUSION LOG:
T+0:00  Sao boards/esp32s3-box-3.toml. Không biết trường nào bắt buộc cho bậc 3.
T+2:00  `board show rp2350-pico2w` chạy. "display: not provided" — có sao không? Không ai nói.
T+4:00  `pytest` đỏ ở test_boards.py:27 và :87. Thông báo in dict các tập chân.
T+8:00  Đọc CONTRIBUTING:93 "PR thường". Mâu thuẫn với CI.
T+12:00 Bỏ cuộc, mở issue.
```
Các điểm T+2, T+4, T+8 được vá bởi: bảng bậc + `board validate`, bất biến theo bậc,
và sửa CONTRIBUTING:93 (xem checklist).

#### 8 lượt chấm điểm

| # | Chiều | Trước | Sau (nếu làm checklist) | Khoảng cách tới 10 |
|:---:|:---|:---:|:---:|:---|
| 1 | Getting Started (người port) | 2 | 7 | Thiếu hướng dẫn port + bộ vector (Khối P1) |
| 2 | CLI/API | 5 | 7 | `--target` của `run/build/record/replay` không kiểm tên; `board show` ghim 5 tên |
| 3 | Thông báo lỗi | 5 | 8 | Lỗi enum thô từ jsonschema; "five" sai sau PR2 |
| 4 | Tài liệu | 4 | 6 | §1d/§8 cũ; CONTRIBUTING:93 sai; KL-1 "đúng năm" |
| 5 | Nâng cấp | 6 | 8 | §4 thiếu tương thích xuôi; hình dạng `vision_in` khó đổi về sau |
| 6 | Môi trường dev | 6 | 7 | Không validate được tệp ngoài kho |
| 7 | Cộng đồng | 3 | 5 | Bậc 3 hứa "tự kiểm chứng qua Bộ kiểm thử tuân thủ" nhưng bộ đó chưa có |
| 8 | Đo lường DX | 2 | 3 | Không đo TTHW port; chấp nhận — chưa có người port nào |

Ba lỗi được lần theo:

1. Target lạ ở `board.toml` — **thấy:** `why: 'rp2040' is not one of ['sim', 'linux', 'esp32s3']`,
   `how: correct the field against schemas/board.v1.json`. **Nên thấy:** thêm "các
   target được công nhận: sim, linux, esp32s3 (bậc 1) · jetson (bậc 2) · stm32, rp2350
   (bậc 3); thêm target mới cần RFC — xem docs/rfc/0002".
2. Nguyên thủy lạ — `board.py:70` nói "five HAL primitives"; sau PR2 phải nói sáu,
   tách lõi/tùy chọn.
3. Bo mạch bậc 3 không có `display` — hôm nay test coi là lỗi; sau PR2 phải là "được
   phép ở bậc 3", còn ở bậc 1 vẫn là lỗi.

```
+====================================================================+
|              DX PLAN REVIEW — SCORECARD                             |
+====================================================================+
| Dimension            | Score  | Prior  | Trend  |
|----------------------|--------|--------|--------|
| Getting Started      |  7/10  |  2/10  |  ↑     |
| API/CLI/SDK          |  7/10  |  5/10  |  ↑     |
| Error Messages       |  8/10  |  5/10  |  ↑     |
| Documentation        |  6/10  |  4/10  |  ↑     |
| Upgrade Path         |  8/10  |  6/10  |  ↑     |
| Dev Environment      |  7/10  |  6/10  |  ↑     |
| Community            |  5/10  |  3/10  |  ↑     |
| DX Measurement       |  3/10  |  2/10  |  ↑     |
+--------------------------------------------------------------------+
| TTHW (người port)    | ~5 min | ∞      |  ↑     |
| Competitive Rank     | Competitive (ước lượng, chưa đo)             |
| Magical Moment       | designed via `neuroedge board validate`      |
| Product Type         | CLI Tool + hợp đồng dữ liệu                  |
| Mode                 | POLISH                                       |
| Overall DX           |  6/10  |  4/10  |  ↑     |
+====================================================================+
```
Cảnh báo: Community (5) và DX Measurement (3) dưới 6 — nợ DX có thật, nhưng thuộc
Khối P1, không thuộc RFC này.

<!-- autoplan-accepted:dx -->
- `neuroedge board validate <path>` nạp một tệp TOML bất kỳ qua `load_board()`, in target, bậc, nguyên thủy lõi có/thiếu, nguyên thủy tùy chọn; exit 1 khi lược đồ từ chối, kèm lỗi ba phần. Kiểm: test CLI với một profile tổng hợp `target = "rp2350"` trong `tmp_path` (exit 0, in "bậc 3") và một tệp target bịa (exit 1, `how` liệt kê target hợp lệ).
- `CONTRIBUTING.md:93` sửa để nói rõ: profile bậc 1 cần PR thường; profile bậc 2/3 cần phần cứng thật và đi qua bất biến theo bậc. Kiểm: đọc lại dòng.
- `--target` của `run`, `build`, `record`, `replay` và `--targets` của `verify` dùng chung một hàm kiểm tên với `SUPPORTED_TARGETS`. Kiểm: test CLI tham số hoá theo lệnh với `esp32s2` → exit 1 (riêng các lệnh stub vẫn giữ exit 2 khi tên hợp lệ).
<!-- /autoplan-accepted:dx -->

```
DX IMPLEMENTATION CHECKLIST (áp cho PR2)
============================
[ ] Người port: profile bậc 3 hợp lệ trong < 5 phút (ước lượng; chưa đo)
[x] Cài đặt không đổi (CHANGELOG §2.1)
[ ] `board validate <path>` in target + bậc + nguyên thủy có/thiếu
[ ] Mọi lỗi target/nguyên thủy/khoá lạ có đủ where + why + how (FR-HAL-05)
[ ] Tên target được kiểm ở mọi cờ --target(s)
[ ] Không còn chữ "five" ghim cứng trong thông báo
[ ] CONTRIBUTING:93 nói đúng chuyện profile bậc 2/3
[ ] §4 ghi tương thích xuôi (công cụ cũ từ chối target mới)
[ ] CHANGELOG ghi RFC-0002 khi PR2 hợp nhất
[—] Hướng dẫn port + bộ vector tuân thủ: Khối P1 (TODOS #13)
```

#### NOT in scope (DX)

- Hướng dẫn port bậc 3 và bộ vector tuân thủ — Khối P1.
- Đo TTHW người port — chưa có người port thật.

#### What already exists (DX)

`BoardCapabilityError` ba phần (FR-HAL-05); `board list`/`board show`; `load_board(path)`
nạp được mọi đường dẫn; `NEUROEDGE_ROOT` để đổi gốc kho.

**Bảng đồng thuận DX:** reviewer độc lập không chấm DX riêng; các phát hiện R4
(`--target` không kiểm), R7 (profile cần phần cứng) trùng lượt 2 và lượt 1. Codex N/A.

### Phase 3 — Eng review (FULL_REVIEW, chạy cuối, review bản đã sửa ở Phase 1 + 2.5)

#### Step 0 — Thách phạm vi

1. **Mã sẵn có:** enum + corpus (`unknown_target.json`), `supports()`/`missing_primitives()`,
   `BoardCapabilityError`, nhóm sự kiện `perception`, `metadata.additionalProperties: true`.
   Không cần lớp hay dịch vụ mới.
2. **Tối thiểu cho mục tiêu target:** 2 lược đồ, `board.py`, 3 tệp test, corpus. Phần
   `vision_in` + `vision_ref` hoãn được mà không chặn phần target (phương án B).
3. **Độ phức tạp:** gói A + sửa + E1/E2/E3 + DX ≈ **13 tệp**, 0 lớp mới → vượt ngưỡng 8.
   Câu hỏi cấu trúc: *Original arrangement* (một PR2, 13 tệp) vs *Smaller arrangement*
   (PR2a target + bậc + CLI ≈ 9 tệp; PR2b `vision_in` ≈ 4 tệp khi có camera). Cả hai giữ
   nguyên mọi sửa lỗi đã nhận. Auto-decide theo P5 → *Smaller arrangement*, **nhưng**
   đây chính là việc tách RFC ở CEO nên đưa lên cổng cuối, không áp.
   `feature answers: CEO accepted block + DX accepted block; structure: B (pending tại cổng cuối); accepted scope: như hai khối accepted; pending remedies: ENG-6, ENG-7`.
4. **Tra cứu:** không có mẫu kiến trúc mới. [Layer 1] enum JSON Schema; [Layer 1]
   tách hằng bắt buộc/tùy chọn. Tra web không chạy.
5. **TODOS:** không mục nào chặn. #3 (streaming) liên quan tới dung lượng `vision_ref`.
6. **Đầy đủ:** chọn bản đủ test cho mọi đường vỡ (chi phí CC vài phút).
7. **Phân phối:** không có artifact mới.

Phát hiện Step 0: (S1, high, conf 9) PR2 như viết đỏ ngay ở `test_boards.py:27` vì
`EXPECTED_PROFILES` phải bằng `set(SUPPORTED_TARGETS)` mà profile bậc 2/3 cần phần
cứng (§9.3) → **PR2 bị chặn bởi lịch mua sắm**. Accepted (sửa: xem ENG-3).

#### 1. Kiến trúc

```
                         ┌──────────────── nguồn sự thật danh sách target ─────────────────┐
                         │  schemas/board.v1.json  board.target.enum        (6)            │
                         │  schemas/trace.v1.json  metadata.target.enum     (6)            │
                         │  hal/board.py           SUPPORTED_TARGETS        (6)  ◄─ test đồng bộ (mới)
                         │  hal/board.py           TARGET_TIERS {target: 1|2|3} (mới, lõi sở hữu)
                         └──────────────────────────────────────────────────────────────────┘
                                           │                               │
  boards/*.toml ─► load_board_document ─► validate ─► board_from_document ─┤
  (chỉ bậc 1)        │ TOML lỗi → NE3001   │ enum → NE3001 + how (E3)       │ khoá capability lạ → NE3001 (mới, ENG-5)
                     ▼                     ▼                                ▼
               BoardProfile.supports / capability / missing_primitives ◄── CORE_PRIMITIVES (5)
                                                                        ◄── OPTIONAL_PRIMITIVES (vision.in) [gói A]
                     │
                     ├─► CLI board show / board validate <path> (mới) / verify --targets (kiểm tên)
                     └─► [build: TSK-S2-02] ⛔  ← cổng mà bất biến theo agent sẽ đứng lên, CHƯA có

  test_boards.py: bất biến theo BẬC
     bậc 1 (sim, linux, esp32s3): đủ CORE_PRIMITIVES · cùng tập chân · sim ⊆ box-3   (giữ nguyên khẳng định)
     mọi profile: target ∈ SUPPORTED_TARGETS · tên tệp == id · qua lược đồ
     mỗi target bậc 1 có đúng một profile trong boards/
```

Kịch bản hỏng thật: (a) ai đó thêm `rp2350` vào lược đồ mà quên `SUPPORTED_TARGETS` →
lược đồ nhận, Python từ chối ở chỗ khác; test đồng bộ mới bắt. (b) bo mạch cộng đồng
khai `tier = 1` trong `board.toml` → nếu bậc nằm trong tệp bo mạch thì lời hứa bị mạo
danh; `TARGET_TIERS` do lõi sở hữu chặn được.

**Taste #1 — bậc đặt ở đâu.** PRD FR-TGT-08 (`prd:276`) nói "trong `board.toml`".
Khuyến nghị: `TARGET_TIERS` trong `board.py` (lõi sở hữu, không tự khai được), và sửa
chữ tiêu chí FR-TGT-08 thành "trong tài liệu và trong bảng bậc của mã lõi; `board.toml`
không tự khai bậc". Phương án khác: thêm `board.tier` (enum 1/2/3) vào lược đồ + lint
bắt buộc bằng `TARGET_TIERS[target]` — thoả chữ PRD nhưng hai bản sao phải khớp.
Nguyên tắc: P5 + P4. Đưa lên cổng cuối vì sửa chữ PRD là sửa nguồn sự thật cao nhất.

#### 2. Chất lượng mã

| ID | Mức | Phát hiện | Sửa |
|:---|:---:|:---|:---|
| ENG-1 | critical | `PRIMITIVES` mang hai nghĩa; thêm `vision.in` làm đỏ `test_boards.py:41` trên cả ba bo mạch | `CORE_PRIMITIVES` (5) + `OPTIONAL_PRIMITIVES` + `PRIMITIVES = CORE + OPTIONAL`; test bậc 1 dùng `CORE_PRIMITIVES`; `_CAPABILITY_KEYS` thêm `"vision.in": "vision_in"` |
| ENG-2 | high | Chuỗi "five" ở `board.py:15–19,40,70`, `cli/main.py:377`, `test_boards.py:60`, `test_cli.py:174–178`, `hal/__init__.py` docstring | Sinh chữ từ `len(CORE_PRIMITIVES)`/danh sách; test khẳng định theo hằng, không theo chữ "five" |
| ENG-3 | high | `test_one_profile_exists_per_supported_target` ép `EXPECTED_PROFILES == set(SUPPORTED_TARGETS)` | Đổi thành: mỗi target bậc 1 có đúng một profile; mọi profile có target ∈ `SUPPORTED_TARGETS` |
| ENG-4 | high | `test_all_three_targets_share_the_same_named_pins` (`:81–87`) là cổng KL-2 duy nhất | Thu hẹp về bậc 1, giữ khẳng định; **không** thay bằng bất biến theo `agent.toml` cho tới TSK-S2-02 |
| ENG-5 | medium | Khoá capability lạ được nhận lặng lẽ (`board_from_document`, `:221–230`); §2 chẩn đoán sai là "bị từ chối lúc chạy" | Kiểm khoá lạ lúc nạp trong `board_from_document`, lỗi ba phần gợi ý khoá gần nhất; sửa câu §2. Không siết lược đồ (tránh `v2`) |
| ENG-6 | medium | Hình dạng `vision_in`: `fps` nguyên, không `modes[]`, `pixel_format`/`accelerator` chuỗi tự do, không `required`, không quy tắc so với `[requires]` | Gói A: đổi `fps` sang `number`, thêm `modes[]`, enum `pixel_format`, và đặc tả quy tắc so khớp **trước khi** chốt. Gói B: hoãn nguyên khối tới V1b |
| ENG-7 | medium | `vision_ref` chỉ có băm → không replay được (FR-CI-02); `uri` không cưỡng chế; "trường `input`" không tồn tại trong lược đồ (là nhóm sự kiện C.1) | Kết quả thị giác đi vào sự kiện nhóm `perception` (nhãn, hộp, độ tin cậy, `model_id`) — thứ replay dùng; `vision_ref` chỉ là danh tính. Lint ngữ nghĩa trong `trace.py`: `sha256` khớp `^[0-9a-f]{64}$`; `uri` chỉ khi `metadata.raw_capture == true`; từ chối blob base64 trong `data` |
| ENG-8 | low | `unknown_target.json` dùng `rp2040`: §7 nói "phải đổi" — sai | Giữ `rp2040` (lỗi gõ thật, gần `rp2350`); chỉ sửa `why_contains` ở `expected_errors.yaml:17` |

#### 3. Test

```
CODE PATHS (PR2)                                              TRẠNG THÁI
[+] schemas/board.v1.json · trace.v1.json — enum 6
  ├── [★★ TESTED→SỬA] test_board_schema_enumerates_exactly_the_three_targets (test_schemas.py:106) → "the_supported_targets", so với SUPPORTED_TARGETS
  ├── [GAP]           trace enum == board enum == SUPPORTED_TARGETS            → test_target_lists_agree (mới)
  ├── [★★★ TESTED]    target bịa bị từ chối (corpus unknown_target.json)      → chỉ sửa why_contains
  └── [GAP]           mỗi target mới được nhận ở cả hai lược đồ               → parametrize 6 target, tài liệu tổng hợp trong bộ nhớ
[+] hal/board.py
  ├── CORE/OPTIONAL_PRIMITIVES
  │   ├── [GAP] bậc 1 đủ CORE                                                 → sửa test_every_profile_declares_all_five_primitives
  │   ├── [GAP] vision.in là tùy chọn: profile tổng hợp không khai vẫn hợp lệ  → test_vision_in_is_optional_per_board (RFC §7)
  │   └── [GAP] "network.out" vẫn bị từ chối, thông báo liệt kê sáu            → sửa test_unknown_primitive_is_refused
  ├── TARGET_TIERS
  │   ├── [GAP] mọi target có đúng một bậc, bậc 1 == {sim, linux, esp32s3}    → test_target_tiers_are_declared (RFC §7)
  │   └── [GAP] khoá của TARGET_TIERS == SUPPORTED_TARGETS                    → cùng test
  ├── board_from_document — khoá capability lạ
  │   ├── [GAP] "vison_in" → NE3001, how gợi ý "vision_in"                    → test mới + fixture tmp_path
  │   └── [GAP] khoá hợp lệ đủ sáu → nhận                                     → test mới
  └── lỗi target lạ có how liệt kê target theo bậc (E3)
      └── [★★→★★★] test_unsupported_target_is_reported khẳng định thêm how
[+] tests/test_boards.py — bất biến theo bậc
  ├── [GAP] test_one_profile_exists_per_supported_target → "per_tier1_target"
  └── [GAP] tập chân chung chỉ trên bậc 1 (giữ khẳng định cũ)
[+] cli/main.py
  ├── [GAP] board show lặp theo PRIMITIVES (E2)                              → test_cli.py:174 lặp theo PRIMITIVES
  ├── [GAP] board validate <path>: hợp lệ → exit 0 + in bậc; target bịa → exit 1 (DX)
  └── [GAP] kiểm tên target cho verify/run/build/record/replay (E1/DX)       → parametrize, esp32s2 → exit 1
[+] trace.py — chỉ gói A
  ├── [GAP] vision_ref.sha256 sai dạng → lỗi
  ├── [GAP] vision_ref.uri khi không raw_capture → lỗi (NFR-PRIV-03)
  └── [GAP] fixtures/traces/invalid/vision_ref_uri_without_opt_in.json + mục expected_errors (khép kín hai chiều)

COVERAGE hôm nay cho đường PR2: 2/22 (9%) | GAPS: 20, 0 E2E, 0 eval
REGRESSION (CRITICAL): khẳng định bậc 1 của hai bất biến cũ phải giữ nguyên nghĩa — xem ENG-4
```

Luật kho: không skip, corpus khép kín hai chiều — mọi fixture `invalid/` mới cần mục
trong `expected_errors.yaml`. Kỳ vọng sau PR2: 210 + số test mới, 0 skipped.

Test plan artifact: `~/.gstack/projects/letrongminh-neuroedge-init/minhlt-docs-rfc-0002-autoplan-eng-review-test-plan-*.md`.

#### 4. Hiệu năng

- Thẩm định lược đồ: enum dài hơn 3 phần tử, không đáng kể.
- Bảng năng lực MCU: +1 phần tử `const` trong flash (RB-4), không chạm SRAM.
- **Dung lượng vết ghi (gói A):** quy định `vision_ref` chỉ ghi cho khung dẫn tới một
  sự kiện `perception` được dùng trong quyết định, không phải mọi khung; kèm test giới
  hạn số sự kiện `vision_ref` trên fixture mẫu.

#### Outside voice — Phase 3

Codex: unavailable (cùng lỗi 401). Reviewer Claude độc lập đã phủ kỹ thuật ở lượt
Phase 1 (R1, R2, R4, R7, R9–R12) — mọi phát hiện kỹ thuật của nó đã có trong ENG-1…8
ở trên. Không chạy lại một reviewer thứ hai (không có bằng chứng mới cần mở lại).

**Bảng đồng thuận Eng:**

| Chiều | Claude chính | Reviewer độc lập | Codex | Đồng thuận |
|:---|:---:|:---:|:---:|:---:|
| Kiến trúc đúng? | Đúng cho target; bậc thiếu dạng máy đọc | Như trái | N/A | CÙNG |
| Test đủ? | Không — 20 gap | Không | N/A | CÙNG |
| Bất biến an toàn giữ? | Chỉ khi thu hẹp theo bậc, không bỏ | Như trái | N/A | CÙNG |
| `vision_in` sẵn sàng chốt? | Không | Không | N/A | CÙNG |
| `vision_ref` đúng thiết kế? | Không — dùng `perception` | Không | N/A | CÙNG |

<!-- autoplan-accepted:eng -->
- ENG-1: tách `CORE_PRIMITIVES` (5) / `OPTIONAL_PRIMITIVES` / `PRIMITIVES = CORE + OPTIONAL` trong `board.py`, xuất qua `hal/__init__.py`; `_CAPABILITY_KEYS` phủ mọi phần tử của `PRIMITIVES`. Kiểm: test bậc 1 dùng `CORE_PRIMITIVES` và xanh trên ba profile hiện có.
- ENG-2: không còn chữ "five" ghim cứng trong mã/test; thông báo sinh từ hằng. Kiểm: `grep -rn "five" python/neuroedge/hal python/neuroedge/cli` chỉ còn trong chú thích lịch sử có ngày.
- ENG-3: `test_one_profile_exists_per_supported_target` → mỗi target bậc 1 có đúng một profile trong `boards/`, và mọi profile có target ∈ `SUPPORTED_TARGETS`. Kiểm: xanh với ba profile hiện có, không cần profile bậc 2/3.
- ENG-4: bất biến tập chân chung chỉ áp cho bậc 1, khẳng định giữ nguyên; bất biến theo `agent.toml` chỉ thay vào khi TSK-S2-02 có test riêng. Kiểm: test chạy trên đúng ba profile bậc 1.
- ENG-5: `board_from_document` từ chối khoá capability ngoài `_CAPABILITY_KEYS.values()` bằng `BoardCapabilityError` ba phần, gợi ý khoá gần nhất; câu §2 "bị từ chối lúc chạy" sửa thành "được nhận lúc nạp và chỉ bị từ chối khi truy vấn". Kiểm: test `vison_in` → NE3001 có "vision_in" trong `how`.
- ENG-8: giữ `rp2040` trong `unknown_target.json`; sửa `why_contains` ở `expected_errors.yaml`; sửa câu §7 tương ứng. Kiểm: `test_trace_fixtures` xanh.
- Test đồng bộ: enum `board.v1` == enum `trace.v1` == `SUPPORTED_TARGETS`, và `test_board_schema_enumerates_exactly_the_three_targets` đổi sang so với `SUPPORTED_TARGETS`. Kiểm: đổi một phía làm test đỏ.
- Profile bậc 2/3 dùng làm bằng chứng PR2 là tài liệu tổng hợp trong `tmp_path`/bộ nhớ, **không** thêm vào `boards/` (§7 sửa cho khớp §9.3). Kiểm: `ls boards/` vẫn đúng ba tệp.
- Người phê duyệt bắt buộc là **kỹ thuật trưởng** (header RFC), khớp tiêu chí ra V1a số 1 (`phase2:171`); tiêu chí 4–5 ghi rõ phụ thuộc TSK-S2-02 / TSK-S3-02. Kiểm: đọc header và `phase2:174–175`.
- Mọi đường vỡ trong sơ đồ test ở trên được liệt kê trong §8 của RFC. Kiểm: đối chiếu §8 với sơ đồ.
<!-- /autoplan-accepted:eng -->

**Pending (phụ thuộc cổng cuối):** ENG-6 (hình dạng `vision_in`) và ENG-7 (`vision_ref`
qua `perception` + lint) — áp nếu giữ gói A; nếu chọn tách B thì hai mục này chuyển
thành đầu vào của RFC thị giác về sau.

#### Failure modes (Eng)

```
  CODEPATH                          | FAILURE                               | TEST? | HANDLED? | USER SEES        | CRITICAL?
  ----------------------------------|---------------------------------------|-------|----------|------------------|----------
  lược đồ ↔ SUPPORTED_TARGETS       | hai danh sách lệch                    | N→Y   | N        | lỗi ở chỗ khác   | có (đã có task)
  board_from_document khoá lạ       | vison_in nhận lặng lẽ                 | N→Y   | N→Y      | Silent → NE3001  | có (ENG-5)
  test bậc 1 dùng PRIMITIVES        | cả ba bo mạch đỏ                      | Y     | —        | CI đỏ            | không (to tiếng)
  bất biến chân bị bỏ               | agent gọi chân không tồn tại          | N     | N        | lỗi lúc chạy     | có → ENG-4 không bỏ
  vision_ref.uri không opt-in       | lưu ảnh khi chưa bật                  | N     | N        | Silent           | có (ENG-7, gói A)
  verify --targets sai tên          | exit 0 giả                            | N→Y   | N→Y      | Silent → exit 1  | có (E1)
```

#### NOT in scope (Eng)

- Bộ đối chiếu `[requires]` lúc build — là TSK-S2-02, không thuộc RFC này.
- Profile phần cứng thật cho bậc 2/3 — chờ phần cứng.
- Siết `capabilities` bằng `additionalProperties: false` — là siết chặt, cần `board.v2`; thay bằng kiểm lúc nạp (ENG-5).

#### What already exists (Eng)

`missing_primitives()` (tái dùng cho `board validate`), `BoardCapabilityError`,
`load_board(path)`, corpus `unknown_target.json`, nhóm sự kiện `perception`,
`metadata` mở. Kế hoạch tái dùng hết, không dựng lại.

#### Song song hoá

Sequential implementation, no parallelization opportunity — mọi thay đổi xoay quanh
`hal/board.py` và hai lược đồ; CLI phụ thuộc hằng mới.

#### Implementation Tasks (Eng)

- [ ] **T1 (P1, human: ~2h / CC: ~10min)** — hal — Tách `CORE_PRIMITIVES`/`OPTIONAL_PRIMITIVES`, thêm `TARGET_TIERS`, mở `SUPPORTED_TARGETS` ra 6
  - Surfaced by: ENG-1, Taste #1
  - Files: `python/neuroedge/hal/board.py`, `python/neuroedge/hal/__init__.py`
  - Verify: `cd python && .venv/bin/python -m pytest -q tests/test_boards.py`
- [ ] **T2 (P1, human: ~1h / CC: ~5min)** — schemas — Mở enum ở hai lược đồ + `$comment` RFC-0002; sửa `why_contains`
  - Surfaced by: RFC §3a, ENG-8
  - Files: `schemas/board.v1.json`, `schemas/trace.v1.json`, `fixtures/traces/expected_errors.yaml`
  - Verify: `pytest -q tests/test_schemas.py tests/test_trace_fixtures.py`
- [ ] **T3 (P1, human: ~3h / CC: ~15min)** — tests — Bất biến theo bậc (ENG-3, ENG-4), test đồng bộ danh sách, test bậc, test tùy chọn `vision.in`
  - Surfaced by: ENG-3, ENG-4, S1, sơ đồ test
  - Files: `python/tests/test_boards.py`, `python/tests/test_schemas.py`
  - Verify: `pytest -q` → 0 skipped, số test tăng
- [ ] **T4 (P1, human: ~1h / CC: ~10min)** — hal — Kiểm khoá capability lạ lúc nạp
  - Surfaced by: ENG-5
  - Files: `python/neuroedge/hal/board.py`, `python/tests/test_boards.py`
  - Verify: test `vison_in` → NE3001
- [ ] **T5 (P2, human: ~2h / CC: ~15min)** — cli — `board show` theo `PRIMITIVES`; `board validate <path>`; kiểm tên target cho mọi `--target(s)`; `how` cho target lạ
  - Surfaced by: E1, E2, E3, DX
  - Files: `python/neuroedge/cli/main.py`, `python/tests/test_cli.py`
  - Verify: `pytest -q tests/test_cli.py`
- [ ] **T6 (P2, human: ~1h / CC: ~10min)** — docs — Sửa RFC §1d, §2, §7, §8, §9.1, header người duyệt, §4 tương thích xuôi; `CONTRIBUTING.md:93`; `hal_mcu_review.md` KL-1; PRD FR-HAL-01 "đúng 5"
  - Surfaced by: CEO accepted, R8, R12, DX
  - Files: `docs/rfc/0002-*.md`, `CONTRIBUTING.md`, `docs/spec/hal_mcu_review.md`, `neuroedge-prd.md`
  - Verify: đọc lại; `grep -n "RFC-0003" docs/rfc/0002-*.md`
- [ ] **T7 (P2, chỉ gói A, human: ~3h / CC: ~20min)** — trace — `vision_ref` qua `perception` + lint ngữ nghĩa + fixture phản chứng
  - Surfaced by: ENG-7
  - Files: `python/neuroedge/trace.py`, `fixtures/traces/invalid/`, `fixtures/traces/expected_errors.yaml`, `neuroedge-proposal.md` C.1
  - Verify: `pytest -q tests/test_trace_fixtures.py`

Giả định tỉ lệ: test ~50x, tính năng ~30x, tài liệu ~6x.

**Thứ tự:** T6 (tài liệu) → T1 → T2 → T3 → T4 → T5 → (T7). T1–T5 hợp nhất **không trước
Tháng 9** và **không trước TSK-S2-02** nếu có bất kỳ thay đổi nào vào bất biến ngoài bậc 1.

#### Eng Completion summary

- Step 0: Scope Challenge — 13 tệp, gợi ý cắt còn ~9 (tách B) → cổng cuối
- Architecture Review: 2 issues (bậc máy đọc được; ba bản sao danh sách)
- Code Quality Review: 8 issues (ENG-1…8)
- Test Review: diagram produced, 20 gaps identified
- Performance Review: 1 issue (dung lượng vết ghi, gói A)
- NOT in scope: written
- What already exists: written
- TODOS.md updates: 2 items (xem dưới)
- Failure modes: 5 critical gaps flagged (tất cả đã có task hoặc accepted obligation)
- Unresolved decisions: 2 (tách RFC; bậc đặt ở đâu) → cổng cuối
- Outside voice: codex unavailable (401 invalid_refresh_token); Claude subagent completed (native, không tính coverage)
- Parallelization: 1 lane, 0 parallel / 7 sequential
- Lake Score: N/A

<!-- AUTONOMOUS DECISION LOG -->
## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|-----------|-----------|----------|----------|
| 1 | 0 | Chạy thủ công ba review (D1 → B) | Người dùng chọn | — | Hook autoplan chặn mọi phiên (attachment trước user record) | Vá gstack; dừng |
| 2 | CEO | Chế độ SELECTIVE EXPANSION | Mechanical | mặc định autoplan | Thêm năng lực vào sản phẩm có sẵn | HOLD, EXPANSION |
| 3 | CEO | Tách RFC và hoãn PR2 tới Tháng 9 — **người dùng chốt D3 → A** | User Challenge → chấp nhận | — | Đổi hướng người dùng đã nêu; Codex vắng nên chỉ một mô hình; người dùng duyệt ở cổng cuối | Giữ một gói (C); merge target ngay (B) |
| 4 | CEO | Không nới hai bất biến trước TSK-S2-02 | Mechanical | P1 | Cổng thay thế chưa tồn tại (`cli/main.py:522`) | Nới như §5a/§5b |
| 5 | CEO | §8 đánh dấu 3 mục đã xong | Mechanical | P5 | Đã làm ở `eddfc59` | Giữ nguyên |
| 6 | CEO | §9.1 bỏ số "RFC-0003" | Mechanical | P5 | 0003/0004 đã được giữ ở design doc | Đổi số khác |
| 7 | CEO | E1 kiểm tên `verify --targets` | Mechanical | P2 | Trong bán kính, < 1 ngày | Bỏ qua |
| 8 | CEO | E2 `board show` theo `PRIMITIVES` | Mechanical | P4 | DRY; nếu không `vision.in` không bao giờ hiện | Giữ hằng |
| 9 | CEO | E3 `how` cho target lạ | Mechanical | P1 | Lỗi enum thô không chỉ đường | Giữ lỗi thô |
| 10 | CEO | E4 `board check` → TODOS | Mechanical | P6 | Cần bộ vector tuân thủ (Khối P1) | Làm ngay |
| 11 | CEO | E5 lint `uri`/`raw_capture` — chỉ nếu giữ `vision_ref` | Taste (phụ thuộc #3) | P1 | NFR-PRIV-03 cần điểm cưỡng chế | Không lint |
| 12 | CEO | §4 thêm hàng tương thích xuôi | Mechanical | P5 | Công cụ cũ từ chối vết ghi mới | Bỏ qua |
| 13 | DX | Chế độ DX POLISH | Mechanical | mặc định | Nâng cấp sản phẩm có sẵn | EXPANSION |
| 14 | DX | Persona: người port bậc 3 | Mechanical | P1 | Đúng người RFC mở cửa cho | U1 maker |
| 15 | DX | TTHW mục tiêu Competitive (2–5 phút) | Mechanical | recommended | Khả thi với `board validate` | Champion |
| 16 | DX | `neuroedge board validate <path>` | Mechanical | P2 | 2 tệp, tái dùng `load_board` | Chờ Khối P1 |
| 17 | DX | Sửa `CONTRIBUTING.md:93` | Mechanical | P5 | Hứa "PR thường" mà CI đỏ | Giữ |
| 18 | DX | Kiểm tên `--target` cho mọi lệnh | Mechanical | P4 | Một hàm dùng chung | Chỉ `verify` |
| 19 | Eng | Cấu trúc PR2 = *Smaller arrangement* (chỉ target + bậc) | Theo #3 (D3 → A) | P5 | Trùng quyết định tách RFC | Original arrangement |
| 20 | Eng | ENG-1 tách hằng nguyên thủy | Mechanical | P5 | Không tách thì bậc 1 đỏ | Một hằng |
| 21 | Eng | ENG-3/ENG-4 bất biến theo bậc | Mechanical | P1 | Giữ khẳng định, không phụ thuộc mua sắm | Bỏ bất biến |
| 22 | Eng | ENG-5 kiểm khoá lạ lúc nạp, không siết lược đồ | Mechanical | P3 | Tránh `board.v2` | `additionalProperties: false` |
| 23 | Eng | ENG-8 giữ `rp2040` | Mechanical | P3 | Lỗi gõ thật; chỉ đổi chuỗi | Đổi fixture |
| 24 | Eng | Profile bậc 2/3 chỉ ở `tmp_path` | Mechanical | P5 | Khớp §9.3 | Thêm vào `boards/` |
| 25 | Eng | Kỹ thuật trưởng là người duyệt bắt buộc | Mechanical | P5 | `phase2:171` | "đề nghị" |
| 26 | Eng | Bậc đặt ở `TARGET_TIERS` của lõi, sửa chữ FR-TGT-08 — **người dùng chốt D4 → A** | Taste → chấp nhận | P5 + P4 | Chống tự khai bậc | `board.tier` trong lược đồ |
| 29 | Gate | D4 → A: duyệt | Người dùng chọn | — | — | `board.tier`; interrogate |
| 30 | Sau cổng | T6: viết lại thân RFC theo phạm vi thu hẹp (§1–§9), dọn đầu tệp; đồng bộ roadmap Giai đoạn 2 (V1a → "Mở danh sách target", thị giác sang TSK-V1b-07/08, tiêu chí V1b 7–8), proposal §8.9, PRD FR-HAL-01/FR-TGT-08, `CONTRIBUTING.md`, danh mục RFC. `CHANGELOG.md` 0.3.0 giữ nguyên vì là lịch sử | Người dùng yêu cầu | P5 | Thực thi các khối accepted | — |
| 27 | Eng | ENG-6 → đầu vào RFC `vision.in` ở V1b; ENG-7 + E5 → luật lint + sự kiện `perception` khi có vết ghi thị giác đầu tiên | Theo #3 (D3 → A) | P6 | Không chốt hợp đồng khi chưa có phần cứng | Áp trong PR2 |
| 28 | Gate | D2 → B2 (giải User Challenge trước) | Người dùng chọn | — | — | Approve as-is |

### Cổng cuối — vòng 1 (2026-09-23)

- **D2 → B2:** giải User Challenge trước khi duyệt.
- **D3 → A (Tách + hoãn):** người dùng chấp nhận Challenge 1.

<!-- autoplan-accepted:gate -->
- RFC-0002 thu hẹp còn **mở enum `target` + bậc máy đọc được**. `vision.in` (§3b) rời khỏi RFC này, thành một RFC riêng mở ở Khối V1b khi đã có camera và bộ đối chiếu `[requires]` (TSK-S2-02). ENG-6 là đầu vào của RFC đó. Kiểm: §3b và các mục `vision_in` ở §7/§8 được chuyển sang §9 "Việc còn treo" kèm mốc kích hoạt.
- `vision_ref` (§3c) không cần RFC lược đồ: nó thành luật lint trong `trace.py` (`sha256` đúng dạng; `uri` chỉ khi `metadata.raw_capture == true`; không blob base64), còn kết quả thị giác đi qua sự kiện nhóm `perception` (Phụ lục C.1). Làm khi có vết ghi thị giác đầu tiên. Kiểm: §3c chuyển sang §9 kèm mốc kích hoạt đó.
- PR2 (phần target) **không hợp nhất trước Tháng 9** của chương trình, theo `docs/designs/giai-doan-1-wedge-truoc-mcu-sau.md:359–361`, hoặc sớm hơn chỉ khi có một profile bậc 2/3 thật đang được viết. Kiểm: §8 ghi mốc này.
- Tiêu chí ra Khối V1a số 2, 4, 5 (`neuroedge-roadmap-phase2.md:172–175`) viết lại theo phạm vi mới: số 2 chỉ còn `target = "jetson"`; số 4 và 5 chuyển sang RFC `vision.in` / khối V1b. Kiểm: đọc lại `phase2:169–175`.
- Mọi khối accepted của CEO, DX, Eng ở trên vẫn giữ nguyên, trừ các mục chỉ áp cho gói A (E5, T7), nay chuyển theo hai gạch đầu dòng trên.
<!-- /autoplan-accepted:gate -->

#### Eng chạy lại trên hướng mới (gọn)

- **Phạm vi PR2 mới:** `board.py`, `hal/__init__.py`, hai lược đồ, `expected_errors.yaml`,
  `test_boards.py`, `test_schemas.py`, `cli/main.py`, `test_cli.py` ≈ **9 tệp**, 0 lớp mới.
  Vẫn trên ngưỡng 8 một chút, nhưng mỗi tệp là một thay đổi nhỏ liền mạch; không có cách
  xếp nhỏ hơn mà giữ được các sửa đã nhận.
- **Còn cần `OPTIONAL_PRIMITIVES` không?** Không cho PR2 — chưa có nguyên thủy tùy chọn
  nào. Vẫn đổi tên thành `CORE_PRIMITIVES` (hoặc giữ `PRIMITIVES` và thêm chú thích) để
  RFC `vision.in` về sau chỉ việc thêm một hằng. ENG-1 thu lại: *không thêm `vision.in`,
  nhưng bỏ chữ "five" ghim cứng* (ENG-2 giữ nguyên).
- **T7 bị gỡ khỏi PR2.** T1 bỏ phần `OPTIONAL_PRIMITIVES`. Mọi task khác giữ nguyên.
- **Sơ đồ test:** các nhánh `vision.in` tùy chọn và `trace.py — vision_ref` rời PR2;
  còn **15 gap**, vẫn đủ cho mọi đường của phần target.
- **Không có rủi ro mới.** Bất biến bậc 1 (ENG-3, ENG-4) và TSK-S2-02 vẫn là cổng.
- **Taste #1 (bậc đặt ở đâu)** vẫn mở, khuyến nghị giữ: `TARGET_TIERS` của lõi.

### Cổng cuối — vòng 2 (2026-09-23)

**D4 → A: APPROVED.** Bậc target nằm ở `TARGET_TIERS` trong `board.py`, do lõi sở hữu.

<!-- autoplan-accepted:gate-2 -->
- `TARGET_TIERS: dict[str, int]` trong `python/neuroedge/hal/board.py` là nguồn máy đọc được duy nhất của bậc; `board.toml` không tự khai bậc. Kiểm: test khoá `TARGET_TIERS` == `SUPPORTED_TARGETS`, và bậc 1 == `{sim, linux, esp32s3}`.
- Tiêu chí chấp nhận FR-TGT-08 (`neuroedge-prd.md:276`) sửa chữ "trong `board.toml`" thành "trong bảng bậc của mã lõi (`TARGET_TIERS`); `board.toml` không tự khai bậc". Kiểm: đọc lại `prd:276`.
<!-- /autoplan-accepted:gate-2 -->

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` (via /autoplan, chạy thủ công) | Scope & strategy | 1 | ISSUES OPEN | 5 proposals, 3 accepted, 1 deferred, 1 → lint sau; 3 critical gaps, đều có task |
| Outside Review | codex (plan review) | Independent 2nd opinion | 1 | unavailable | `401 invalid_refresh_token` — no completed external review; native Claude subagent: 12 findings, 12 resolved |
| Eng Review | `/plan-eng-review` (via /autoplan, chạy thủ công) | Architecture & tests (required) | 1 | ISSUES OPEN | 8 issues, 5 critical gaps (đều có task hoặc accepted obligation) |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | SKIPPED | không có phạm vi UI |
| DX Review | `/plan-devex-review` (via /autoplan, chạy thủ công) | Developer experience gaps | 1 | ISSUES OPEN | score: 4/10 → 6/10, TTHW: ∞ → ~5 min (ước lượng) |

- **OUTSIDE COVERAGE:** codex · CEO/DX/Eng · unavailable (401, chưa `codex login`) · không có phát hiện ngoài mô hình. Fallback native (reviewer Claude độc lập, cùng harness): completed, 12 phát hiện, cả 12 đã xử lý — không tính là outside coverage.
- **VERDICT:** Đã duyệt (D4 → A) với phạm vi thu hẹp: chỉ mở enum target + `TARGET_TIERS`, PR2 ~9 tệp, merge không trước Tháng 9. Chưa review nào CLEAR, vì critical gap chỉ đóng khi PR2 hạ cánh — eng review required (chạy lại trên PR2 bằng `/review`). Pipeline có guard của autoplan không chạy (hook chặn); đây là review thủ công theo cùng phương pháp.

NO UNRESOLVED DECISIONS
