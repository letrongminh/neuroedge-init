# Nhật ký thay đổi — NeuroEdge

Toàn bộ thay đổi đáng kể của dự án được ghi tại đây, theo tinh thần
[Keep a Changelog](https://keepachangelog.com/) và
[Semantic Versioning](https://semver.org/lang/vi/).

> **Tệp này có ba phần, đọc theo nhu cầu:**
>
> | Bạn cần gì | Đọc mục |
> |:---|:---|
> | Biết đã thay đổi những gì | [§1 Nhật ký phiên bản](#1-nhật-ký-phiên-bản) |
> | Chạy được hệ thống ngay | [§2 Cách vận hành](#2-cách-vận-hành) |
> | Tiếp quản để build tiếp | [§3 Bàn giao ngữ cảnh sản phẩm](#3-bàn-giao-ngữ-cảnh-sản-phẩm) |
>
> **Nguồn sự thật về tiến độ** vẫn là [`neuroedge-roadmap.md`](neuroedge-roadmap.md)
> §0 (bảng theo dõi và thẻ bàn giao). Tệp này kể *đã xây gì và chạy thế nào*;
> roadmap kể *còn gì phải xây*. Khi hai tệp lệch nhau, roadmap đúng.

---

## 1. Nhật ký phiên bản

### [0.1.0] — 2026-09-21 — Sprint 1: Đóng băng lược đồ (Khối 1a)

Sprint đầu tiên đóng băng ba lược đồ lõi và hiện thực hóa ngữ nghĩa kế thừa
gate. Mốc này **chưa chạy được tác tử nào**; nó thiết lập các hợp đồng mà
Sprint 2 và 3 sẽ hiện thực. Xem [§3.7](#37-điều-hệ-thống-chưa-làm-được) để
biết chính xác điều gì chưa tồn tại.

**Phạm vi đã đóng:** 12/13 task · 4/6 tiêu chí ra · 2 hạng mục bị chặn ngoài
tầm kỹ thuật (phần cứng và một quyết định quản trị).

#### Đã thêm — Lõi phân giải gate

- **`python/neuroedge/engine/gate_resolver.py`** — làm phẳng chuỗi `extends`
  thành một `ResolvedGate`, cưỡng chế **đủ năm nguyên tắc kế thừa an toàn**
  (Proposal Phụ lục B.5 · FR-GATE-06 → FR-GATE-08):

  | # | Nguyên tắc | Cưỡng chế bởi |
  |:---:|:---|:---|
  | 1 | Gate con kế thừa toàn bộ `evaluate` | `_merge_evaluate()` — và **từ chối** việc định nghĩa lại một tiêu chí đã kế thừa |
  | 2 | Gate con chỉ được siết chặt `allow_when` | `_merge_allow_when()` + `Constraint.is_at_least_as_strict_as()` |
  | 3 | Gate con được bổ sung `evaluate` mới | `_merge_evaluate()` |
  | 4 | `fail: open` không kế thừa | `_resolve_budget()` — chỉ tài liệu của chính cấp đó đặt được `open` |
  | 5 | Tối đa 3 cấp, chặn vòng lặp | `_load_chain()` |

- **`python/neuroedge/engine/constraints.py`** — điểm mấu chốt khiến nguyên tắc 2
  *quyết định được*. Mỗi mệnh đề `allow_when` được chuẩn hóa thành **tập giá trị
  kết quả mà nó chấp nhận**, nên "siết chặt" có nghĩa chính xác: tập con, và sàn
  tin cậy không thấp hơn. Nhờ đó `not_in: [phone]` bị phát hiện là một phép
  *nới lỏng* so với `in: [in_person, app]` dù toán tử khác nhau.
  Chỉ nhận đúng bộ toán tử Phụ lục B.2; toán tử lạ là lỗi, không phải mặc định cho qua.

- **`python/neuroedge/engine/canonical.py`** — chuẩn tắc hóa **RFC 8785 (JCS)**
  và băm SHA-256 trên *gate đã phân giải*. Bảo đảm sửa YAML mang tính hình thức
  (thụt lề, thứ tự khóa, kiểu trích dẫn) không làm đổi mã băm, nên chữ ký gate
  không bị vô hiệu mỗi lần định dạng lại tệp.

- **`python/neuroedge/errors.py`** — phân cấp lỗi **cưỡng chế hợp đồng ba thành
  phần** của FR-DX-04 *bằng cấu trúc*: `NeuroEdgeError(where=, why=, how=)`
  không thể khởi tạo mà thiếu một thành phần. Mã lỗi ổn định để test và viễn trắc
  neo vào: `NE1001` `NE2001` `NE2002` `NE2003` `NE3001` `NE4001`.

- **`python/neuroedge/trace.py`** — thẩm định vết ghi, dùng chung một đường mã
  cho CLI và test. Bật `format_checker`, nên `format: date-time` và `format: uri`
  được kiểm thật.

- **`python/neuroedge/hal/board.py`** + **`boards/`** (3 profile) — mô hình năng
  lực bo mạch cho cả ba target `sim` · `linux` · `esp32s3`.

- **`python/neuroedge/paths.py`** — định vị gốc monorepo (`schemas/`, `gates/`,
  `fixtures/`, `boards/`) từ source checkout, editable install hay wheel; ghi đè
  bằng biến môi trường `NEUROEDGE_ROOT`.

#### Đã thêm — Corpus kiểm chứng

| Đường dẫn | Số tệp | Vai trò |
|:---|:---:|:---|
| `gates/` | 3 | Gate mẫu viết tay, gồm **chuỗi kế thừa 2 cấp** (Tiêu chí ra 2) |
| `fixtures/gates/valid/` | 5 | Hành vi phân giải đúng, đặc biệt nguyên tắc 4 theo cả hai chiều |
| `fixtures/gates/invalid/` | 15 | Phản chứng — mỗi nguyên tắc đều có ca chứng minh bị từ chối |
| `fixtures/gates/registry/` | 6 | Gate cơ sở cho fixture (gồm chuỗi 3 cấp và cặp vòng lặp) |
| `fixtures/traces/invalid/` | 6 | Phản chứng cho `trace.v1.json` |
| `fixtures/gates/expected_errors.yaml` · `fixtures/traces/expected_errors.yaml` | 2 | **Thông báo lỗi kỳ vọng** cho từng phản chứng |

Corpus phản chứng **khép kín hai chiều**: mỗi tệp phải có một mục trong
`expected_errors.yaml`, và mỗi mục phải có một tệp. Không thể thêm fixture mà
không nói nó chứng minh điều gì.

#### Đã thêm — CLI vận hành được

`gate resolve` · `gate lint` · `gate publish` · `gate add` ·
`trace validate` · `trace show` · `board list` · `board show` · `verify` · `replay`

Chi tiết và hợp đồng mã thoát: [§2.3](#23-tham-chiếu-lệnh-cli).

#### Đã thêm — CI, quy trình, tài liệu

- **`.github/workflows/ci-sim-linux.yml`** (TSK-S1-12, FR-CI-05) — 4 job:
  `frozen-artifacts` · `tests` (3 bản Python) · `lint` · `licence-obligations`.
- **`.github/workflows/nightly-hardware.yml`** (TSK-S1-12, FR-CI-06) — 4 job:
  `firmware-build` · `upstream-drift` · `memory-spike` · `report`.
- **`CONTRIBUTING.md`** (TSK-S1-13) — 7 mục, gồm ranh giới chính xác của việc gì
  cần RFC.
- **`docs/rfc/`** (TSK-S1-13) — quy trình, mẫu, và
  [RFC-0001](docs/rfc/0001-gate-schema-conditional-requirements.md).
- **`docs/spec/hal_mcu_review.md`** (TSK-S1-11) — 5 kết luận rà soát + 4 ràng
  buộc chuyển tiếp sang Sprint 4.
- **`docs/reports/memory_spike_report.md`** (TSK-S1-10) — khung báo cáo, **các ô
  số đo để trống** vì chưa chạy trên bo mạch.
- **`scripts/check_firmware_size.py`** — đối chiếu ngân sách flash Q-3, đọc kích
  thước khe A/B từ chính `partitions.csv` thay vì ghim cứng.
- **`python/requirements-lock.txt`** — §3.9 nghĩa vụ 5 (ghim phiên bản).
- **`python/README.md`**, **`CHANGELOG.md`** (tệp này).

#### Đã thêm — Khung đo bộ nhớ trên thiết bị

- **`targets/esp32s3/main/memory_probe.{c,h}`** — 4 checkpoint (`boot`,
  `nvs_ready`, `network_ready`, `audio_ready`), bảng cho người đọc, và **một
  dòng JSON máy đọc được** (`NEUROEDGE_MEMORY_JSON`) để CI thu số đo mà không ai
  phải chép tay. Ngưỡng Q-3 ghim thành hằng số `NEUROEDGE_Q3_*`.
- **`targets/esp32s3/main/main.c`** — khởi tạo NVS và ngăn xếp mạng (đo *sau*
  khi đã trừ phần không thể loại bỏ), rồi báo cáo. Vị trí nạp AEC + VAD + Opus
  đánh dấu `TODO(TSK-S1-10, V2)`.

#### Đã đổi

- **`schemas/gate.v1.json` — sửa theo [RFC-0001](docs/rfc/0001-gate-schema-conditional-requirements.md).**
  Bốn thay đổi, chi tiết lập luận trong RFC:
  1. Trường bắt buộc thành **có điều kiện** theo sự có mặt của `extends`. Gate
     gốc vẫn phải khai báo hợp đồng đầy đủ; gate dẫn xuất được phép kế thừa.
  2. `budget.fail` thành **tùy chọn**, vắng mặt nghĩa là `closed`.
  3. Tham số `on_block` bắt buộc **theo từng hành vi** (`escalate`→`to`,
     `ask`→`message`, `degrade`→`fallback_action`).
  4. Siết chặt: `extends` có `pattern` URI; `level` bắt buộc có `levels`;
     `choice` bắt buộc có `options`; `evaluate` cần ít nhất một tiêu chí.
- **Phụ thuộc chuẩn tắc hóa:** `canonicaljson` → **`rfc8785`**. Phụ lục B.4 nói
  rõ RFC 8785 (JCS); `canonicaljson` là một chuẩn tắc hóa khác (dòng Matrix).
- **`python/pyproject.toml`:** `readme` trỏ tệp ngoài thư mục dự án khiến
  **gói không cài được**; thêm `pyyaml`; thêm cấu hình `ruff`.
- **CLI:** lệnh chưa có engine giờ **thoát mã 2** kèm mã task sẽ hiện thực nó,
  thay vì in bảng kết quả giả. `verify` chỉ báo phần nó thật sự kiểm và nói rõ
  phần nào của tiêu chí A2 chưa được phủ.
- **`NOTICE`:** viết lại thành ma trận giấy phép 4 mục A–D (§3.9 nghĩa vụ 1, 2, 4).
- **Chuẩn hóa mã:** `typing.Dict/Optional` → generic sẵn có; `GateVerdict` →
  `StrEnum`; toàn bộ `python/` sạch `ruff check` và `ruff format`.

#### Đã sửa

- **`pyproject.toml` khiến gói không cài được.** `readme = "../neuroedge-proposal.md"`
  nằm ngoài thư mục dự án; hatchling từ chối. `pip install -e .` thất bại, nên
  CI không thể cài được gói.
- **4 test conformance lược đồ skip trong im lặng.** Chúng dùng
  `pytest.importorskip("jsonschema")`, mà `jsonschema` không được cài, nên tình
  trạng thật là *4 passed, 4 skipped* trong khi bảng tiến độ báo
  "PASS 100% (4/4 tests passed)". Khẳng định về conformance lược đồ đang dựa
  trên những test chưa từng chạy. Đã bỏ `importorskip`, và thêm **cổng CI chặn
  mọi test bị skip**.
- **`format: date-time` và `format: uri` không được kiểm.** JSON Schema coi
  `format` là chú thích trừ khi có format checker. Một vết ghi với
  `timestamp_utc: "21/09/2026 08:00"` vẫn thẩm định đạt — và một vết ghi không
  phân tích được mốc thời gian thì không phát lại được, tức là mất đúng mục đích
  của tệp.
- **`neuroedge verify` in "TARGET EQUIVALENCE VERIFIED — 0 discrepancies" mà
  không kiểm gì.** `neuroedge test` in bảng "3 passed" cố định. Đầu ra CLI bị
  dán vào báo cáo tiến độ như bằng chứng, nên một dòng như vậy là thông tin sai
  cho người ra quyết định phạm vi.
- **Chẩn đoán thiếu ngữ cảnh tệp.** Lỗi toán tử `allow_when` chỉ nêu
  `allow_when.risk_level` mà không nêu tệp nào; vết chuỗi kế thừa in sai thứ tự.
- **Khẳng định nghịch đảo trong CI có thể đạt vì lý do sai.** Bước kiểm
  "corpus phản chứng phải tiếp tục thất bại" viết dạng `if ! <lệnh>`, nên nó coi
  *mọi* mã thoát khác 0 là bằng chứng bị từ chối — kể cả mã 2 (lỗi cú pháp lệnh).
  Mà lệnh khi đó **thật sự sai cú pháp**: `gate lint` chưa có tùy chọn
  `--registry`. Bước kiểm sẽ mãi mãi xanh mà **không bao giờ chạy phép kiểm tra
  nào**, kể cả khi ngữ nghĩa kế thừa hồi quy hoàn toàn. Đã thêm `--registry` cho
  `gate lint`, và bước CI giờ **so khớp chính xác mã thoát 1** ("đã chạy và
  không đạt"), thất bại rõ ràng nếu nhận mã khác. Hai test neo lại lỗ này.

#### An toàn và giấy phép

- **Hai đường lây nhiễm copyleft mạnh vào lõi MIT — cả hai là phụ thuộc bắc cầu,
  không ai chủ ý thêm:**

  | Đường | Giấy phép | Xử lý |
  |:---|:---|:---|
  | `neuroedge` → `copier` → `jinja2-ansible-filters` | **GPL3** | `copier` rời tập phụ thuộc lõi sang extra `scaffold` |
  | `neuroedge` → `jsonschema[format]` → `rfc3987` | **GPL** | Ghim `jsonschema[format-nongpl]`, dùng `rfc3987-syntax` (MIT) |

  Đây đúng là rủi ro §3.10 đã nêu. Điều đáng chú ý: rà soát bằng mắt ở tầng phụ
  thuộc **trực tiếp** sẽ bỏ sót cả hai. Vì vậy job `licence-obligations` chạy
  `pip-licenses --fail-on` trên **toàn bộ cây phụ thuộc** ở mỗi pull request.

- **`allow_when` dạng chuỗi CEL bị từ chối trong chuỗi kế thừa.** Nguyên tắc 2
  yêu cầu *chứng minh* gate con không lỏng hơn gate cha; với hai biểu thức bất
  kỳ, đó là bài toán không quyết định được. Phân giải **fail-closed** thay vì
  xấp xỉ một phép kiểm tra an toàn.

- **Mặc định fail-closed ở mọi hướng:** vắng `fail` → `closed`; gate cha
  `fail: open` mà gate con im lặng → `closed`; chưa lấy checkpoint `audio_ready`
  → `INCONCLUSIVE`, không phải "đạt".

#### Kiểm chứng

```
210 test PASS · 0 SKIP · ruff check sạch · ruff format sạch
```

| Bộ test | Số test | Kiểm điều gì |
|:---|:---:|:---|
| `test_gate_fixtures.py` | 40 | Corpus phản chứng khớp đúng lỗi đã ghi; mọi lỗi đủ 3 thành phần |
| `test_gate_resolver.py` | 35 | Năm nguyên tắc B.5, từng nguyên tắc độc lập, dựng tài liệu trong bộ nhớ |
| `test_cli.py` | 32 | Hành vi CLI, **neo chặt mã thoát** |
| `test_sample_gates.py` | 26 | Ba gate mẫu và chuỗi 2 cấp trên corpus thật |
| `test_boards.py` | 22 | Khai báo bo mạch; **parity giữa `sim` và bo mạch tham chiếu** |
| `test_trace_fixtures.py` | 19 | Vết ghi hợp lệ/không hợp lệ, và **nội dung kịch bản** |
| `test_schemas.py` | 18 | Conformance cấu trúc của ba lược đồ |
| `test_canonical.py` | 14 | Tính tất định của RFC 8785 và mã băm |
| `test_testing.py` | 4 | Action CI `replay()` / `scenario()` (có từ trước) |

---

## 2. Cách vận hành

### 2.1 Dựng môi trường

```bash
cd python
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q          # kỳ vọng: 210 passed, 0 skipped
```

Yêu cầu **Python 3.11+**. Bản dựng tái lập được:

```bash
.venv/bin/python -m pip install -r requirements-lock.txt
```

> **Đừng cài extra `scaffold`** trừ khi bạn thực sự cần `copier`: nó kéo
> `jinja2-ansible-filters` (GPL3) vào môi trường. Xem `NOTICE` mục B.

### 2.2 Kiểm tra nhanh toàn bộ artifact

Chạy từ **gốc kho** (mọi lệnh đều cần thấy `schemas/`, `gates/`, `fixtures/`):

```bash
V=python/.venv/bin

$V/neuroedge verify                      # phân giải mọi gate + thẩm định mọi vết ghi
$V/neuroedge gate lint                   # kỳ vọng: ✓ 3 gate(s) resolved
$V/neuroedge trace validate fixtures/traces/*.json   # kỳ vọng: 3 × VALID
$V/neuroedge board list                  # kỳ vọng: 3 profile
```

Khẳng định nghịch đảo — corpus phản chứng **phải** tiếp tục thất bại:

```bash
$V/neuroedge gate lint fixtures/gates/invalid --registry fixtures/gates/registry
# kỳ vọng: 15 of 15 gate(s) failed to resolve · mã thoát 1
```

Nếu lệnh trên **thành công**, các phép kiểm tra an toàn kế thừa đã hồi quy, và
một pipeline xanh lúc đó là thông tin sai. CI có đúng một bước cho việc này.

### 2.3 Tham chiếu lệnh CLI

**Hợp đồng mã thoát** — CI và Action CI đều neo vào nó:

| Mã | Nghĩa |
|:---:|:---|
| `0` | Phép kiểm tra đã chạy và **đạt** |
| `1` | Phép kiểm tra đã chạy và **không đạt** |
| `2` | Lệnh **chưa được hiện thực** |

Mã `2` tách biệt với `1` là có chủ ý: CI phân biệt được "hỏng" và "chưa có".

#### Lệnh đã hiện thực

| Lệnh | Chức năng |
|:---|:---|
| `gate resolve <tệp\|URI>` | Phân giải chuỗi `extends`, in chính sách hiệu dụng và mã băm. `--json` cho đầu ra máy đọc; `--registry <dir>` đổi nơi tra `neuroedge://` |
| `gate lint [dir]` | Phân giải mọi gate trong thư mục (mặc định `gates/`). `--registry <dir>` đổi nơi tra `neuroedge://`; nếu không truyền, lệnh tự nhận thư mục `registry/` kế bên |
| `gate publish <tệp>` | Biên dịch sang JSON chuẩn tắc RFC 8785, in mã băm SHA-256. `--out` ghi ra tệp |
| `gate add <URI>` | Phân giải một gate từ registry và cho biết việc kế thừa nó sẽ áp đặt gì |
| `trace validate <tệp…>` | Thẩm định theo `trace.v1.json`. Một tệp sai làm cả lệnh thất bại |
| `trace show <tệp>` | In dòng thời gian sự kiện |
| `board list` / `board show <id>` | Liệt kê / xem năng lực bo mạch theo 5 nguyên thủy |
| `verify` | Quét toàn bộ artifact đã đóng băng |
| `replay <tệp>` | Đọc và thẩm định vết ghi rồi in dòng thời gian |

> `gate publish` **không ký số**. Nó dừng ở mã băm, vì ký cần khóa của Gate
> Registry (Khối 3). `replay` **không thực thi** vết ghi trên target. Cả hai
> lệnh tự nói rõ điều đó trong đầu ra — đừng đọc chúng như đã làm nhiều hơn.

#### Lệnh chưa hiện thực (thoát mã 2)

| Lệnh | Sẽ có ở |
|:---|:---|
| `run` | TSK-S2-01 |
| `build` | TSK-S2-02, TSK-S2-06 |
| `test` | TSK-S3-03 — hiện dùng `pytest` trong `python/` |
| `record` | TSK-S3-01 |
| `new` | TSK-S3-07 |

### 2.4 Đọc một thông báo lỗi

Mọi lỗi có đúng ba phần (FR-DX-04): **ở đâu** · **vì sao** · **cách xử lý**.
Lỗi kế thừa có thêm dòng `rule` chỉ ra nguyên tắc B.5 bị vi phạm.

```
[NE2003] loosens-level@1.0.0 (fixtures/gates/invalid/loosens_level.yaml) -> allow_when.risk_level
  why: loosens the inherited condition: base admits {low}, this gate admits {high, low, medium}
  rule: Appendix B.5 principle 2
  fix: narrow allow_when.risk_level to a subset of the base condition (base clause: {'lte': 'low'}), …
```

| Mã | Lớp lỗi | Nghĩa |
|:---:|:---|:---|
| `NE1001` | `ActionContractViolation` | Lệnh actuator không mang chữ ký gate |
| `NE2001` | `GateNotFoundError` | Không tìm thấy gate theo URI hoặc đường dẫn |
| `NE2002` | `GateSchemaError` | Vi phạm `gate.v1.json` hoặc bộ toán tử Phụ lục B.2 |
| `NE2003` | `GateInheritanceError` | Vi phạm một trong năm nguyên tắc B.5 |
| `NE3001` | `BoardCapabilityError` | Khai báo bo mạch sai, hoặc thiếu năng lực được yêu cầu |
| `NE4001` | `TraceValidationError` | Vi phạm `trace.v1.json` |

### 2.5 CI

| Workflow | Khi nào | Job |
|:---|:---|:---|
| `ci-sim-linux.yml` | Mỗi PR và push | `frozen-artifacts` · `tests` (Python 3.11/3.12/3.13) · `lint` · `licence-obligations` |
| `nightly-hardware.yml` | 01:00 UTC+7 hằng đêm | `firmware-build` · `upstream-drift` · `memory-spike` · `report` |

`ci-sim-linux.yml` phải xanh trước khi hợp nhất. Ba cổng đáng chú ý:

- **Cổng chặn test skip** — đọc `junit.xml`, thất bại nếu có bất kỳ test nào
  skip. Lý do ở [§1 mục Đã sửa](#đã-sửa).
- **Khẳng định nghịch đảo** — corpus phản chứng phải tiếp tục thất bại.
- **Cổng giấy phép** — `pip-licenses --fail-on` trên toàn bộ cây phụ thuộc.

Job `memory-spike` cần runner tự quản gắn nhãn `esp32s3-box-3`. Khi chưa có,
nó **bị bỏ qua và nói rõ là bỏ qua** trong phần summary, không bao giờ báo đạt.

### 2.6 Firmware (khi đã có bo mạch)

```bash
cd targets/esp32s3
idf.py set-target esp32s3
idf.py build
python ../../scripts/check_firmware_size.py build/*.bin   # ngân sách flash Q-3
idf.py -p /dev/ttyUSB0 flash monitor
```

Tìm dòng `NEUROEDGE_MEMORY_JSON` trong đầu ra monitor — đó là số đo. Điền vào
[`docs/reports/memory_spike_report.md`](docs/reports/memory_spike_report.md).

---

## 3. Bàn giao ngữ cảnh sản phẩm

Mục này dành cho người (hoặc phiên làm việc) tiếp quản. Đọc hết mục này là đủ
để build tiếp mà không phải đọc lại ba tài liệu gốc.

### 3.1 Bốn tài liệu là nguồn sự thật

| Tệp | Vai trò | Khi nào đọc |
|:---|:---|:---|
| [`neuroedge-roadmap.md`](neuroedge-roadmap.md) | **Tiến độ, task, tiêu chí ra, quyết định.** §0 là bảng điều khiển | **Luôn đọc trước** |
| [`neuroedge-prd.md`](neuroedge-prd.md) | Yêu cầu chức năng `FR-*` / `NFR-*` | Khi cần biết *phải* làm gì |
| [`neuroedge-proposal.md`](neuroedge-proposal.md) | Kiến trúc và các Phụ lục. **Phụ lục B là đặc tả gate** | Khi cần biết *tại sao* |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Quy ước, và việc gì cần RFC | Trước khi sửa `schemas/` |

**Thứ tự ưu tiên khi lệch nhau:** PRD/Proposal (hợp đồng) → roadmap (tiến độ) →
mã nguồn → tệp này. Nếu mã lệch hợp đồng, mã sai.

### 3.2 Bản đồ kiến trúc — cái gì ở đâu

```
neuroedge-init/
├── schemas/              ⚠️  ĐÃ ĐÓNG BĂNG — sửa phải có RFC
│   ├── gate.v1.json          Hợp đồng gate (Phụ lục B)
│   ├── trace.v1.json         Hợp đồng vết ghi (Phụ lục C)
│   └── board.v1.json         Hợp đồng năng lực bo mạch
├── gates/                3 gate mẫu, gồm chuỗi kế thừa 2 cấp
├── boards/               3 profile: sim-default · esp32s3-box-3 · linux-rpi5
├── fixtures/
│   ├── traces/           ⚠️  3 vết ghi chuẩn mực — sửa phải có RFC
│   │   ├── invalid/          6 phản chứng
│   │   └── expected_errors.yaml
│   └── gates/            valid/ (5) · invalid/ (15) · registry/ (6)
│       └── expected_errors.yaml
├── python/neuroedge/
│   ├── engine/           L3 — phân giải gate, ràng buộc, chuẩn tắc hóa
│   ├── hal/              L1 — 5 nguyên thủy, mô hình bo mạch
│   ├── perception/       L2 — khung, chưa hiện thực
│   ├── testing/          Action CI — replay(), scenario()
│   ├── cli/              CLI Typer
│   ├── errors.py         Hợp đồng lỗi 3 thành phần
│   ├── trace.py          Thẩm định vết ghi
│   └── paths.py          Định vị gốc monorepo
├── targets/esp32s3/      Firmware ESP-IDF + khung đo bộ nhớ
├── docs/rfc/ spec/ reports/
├── scripts/              Công cụ CI
└── .github/workflows/    2 pipeline
```

### 3.3 Mười điều bất biến — đừng phá

Đây là các mệnh đề mà phần còn lại của hệ thống dựa vào. Vi phạm một trong số
này sẽ làm hỏng những thứ trông không liên quan.

1. **Thẩm định lược đồ KHÔNG đủ để kết luận một gate an toàn.** Nguyên tắc 2 là
   mệnh đề về **hai** tài liệu; JSON Schema thẩm định **một**. Cổng kiểm tra là
   `neuroedge gate lint` (phân giải), không phải thẩm định lược đồ.
2. **Fail-closed là mặc định ở mọi hướng.** Vắng `fail` → `closed`. Gate cha
   `fail: open` + gate con im lặng → `closed`. Không đo được → `INCONCLUSIVE`.
3. **`allow_when` dạng chuỗi CEL không được xuất hiện trong chuỗi kế thừa.**
   Không chứng minh được phép siết chặt → từ chối.
4. **Phân giải gate là hàm thuần khiết** — không đồng hồ, không mạng, không ngẫu
   nhiên. Đó là điều cho phép `neuroedge verify` chứng minh cùng một chuỗi phân
   giải như nhau trên cả ba target.
5. **Không có bộ lượng giá CEL nào trên vi điều khiển** (Q-9 phương án A). Máy
   tính biên dịch sang cây quyết định phẳng; firmware chỉ duyệt cây.
6. **Bo mạch tham chiếu duy nhất là ESP32-S3-BOX-3.** Không đổi sang DevKitC —
   số đo spike sẽ vô nghĩa.
7. **`sim` không được giàu năng lực hơn bo mạch tham chiếu.** Nếu giàu hơn, lời
   hứa "TTFV dưới 10 phút" thành cái bẫy: rút ngắn 10 phút đầu, thêm hai ngày gỡ lỗi.
8. **Đuôi vết ghi là `.json` mang `$schema`.** Không đổi sang `.ntrace`.
9. **Không copyleft mạnh trong phần phân phối.** Ghim
   `jsonschema[format-nongpl]`; giữ `copier` ở extra `scaffold`.
10. **Lệnh CLI chưa có engine phải thoát mã 2, không in "PASS" giả.** Đầu ra CLI
    bị dán vào báo cáo như bằng chứng.

### 3.4 Hai hạng mục bị chặn — không đóng được bằng nỗ lực kỹ thuật

| Hạng mục | Chặn bởi | Cần ai | Mở ra điều gì |
|:---|:---|:---|:---|
| **TSK-S1-10** · Tiêu chí ra 3 | **Bo mạch ESP32-S3-BOX-3 vật lý** | Đặt hàng | Kết luận phạm vi Khối 1b (TSK-S2-10) |
| **Tiêu chí ra 6** · Q-11 | **Quyết định quản trị** | Kỹ thuật trưởng | Bắt đầu port mã Khối 2 |

**TSK-S1-10 — việc còn lại sau khi có bo mạch:** vendoring `esp-sr` (AEC/AFE +
VAD) và `opus` kèm rà soát giấy phép §3.9, nạp chúng tại `TODO(TSK-S1-10, V2)`
trong `main.c`, gọi checkpoint `audio_ready`, điền báo cáo. Quy tắc quyết định
đã chốt **trước khi đo** để kết quả không bị giải thích lại: trượt bất kỳ một
ngưỡng Q-3 → kích hoạt **bậc 5 thang cắt phạm vi (§9) ngay**, không chờ Tuần 9.

**Q-11 — nên bao gồm chính sách phụ thuộc bắc cầu,** không chỉ phê duyệt ba
thành phần đã nêu tên. Hai phát hiện GPL trong Sprint 1 đều đến qua bắc cầu.

### 3.5 Việc tiếp theo — thứ tự đề xuất

1. 🔴 **Chốt Q-11** và **đặt bo mạch** — hai việc này chặn, và không ai trong
   đội kỹ thuật tự mở được.
2. **Đồng bộ Phụ lục B.1 / B.3 / B.4 của proposal** theo RFC-0001 §9. Lược đồ và
   mã đã đúng; văn bản đề xuất còn ghi bốn trường là bắt buộc vô điều kiện. Đây
   là sửa văn bản, không sửa mã.
3. **Mở Sprint 2** — đường găng là **TSK-S2-07** (đặc tả chuẩn tắc máy trạng thái
   hội thoại). Roadmap §3.10 nói rõ: port Pipecat *trước khi* có đặc tả và bộ
   vector tuân thủ là **rủi ro, không phải đòn bẩy**. Làm TSK-S2-07 trước
   TSK-S3-11, không ngược lại.
4. **TSK-S2-01** (HAL `sim`) và **TSK-S2-06** (biên dịch CEL → cây quyết định).
   TSK-S2-06 mở khóa việc dùng `allow_when` dạng biểu thức cho gate độc lập.

### 3.6 Nợ thiết kế đã biết

| # | Nợ | Phải giải quyết ở |
|:---:|:---|:---|
| 1 | **`digital_out()` chưa hủy được lệnh đang chờ.** Hợp đồng thu hồi lệnh vật lý (§3.8) yêu cầu `barge_in` hủy xung chốt cửa đang chờ trong ≤ 1 khung âm thanh. Chữ ký hiện tại nhận `duration_ms` và ghi trạng thái ngay — đủ cho `sim`, không đủ cho `esp32s3` | **TSK-S4-01**, cùng lúc với hợp đồng thu hồi — không phải sau |
| 2 | `ReplaySession._parse_events()` suy luận `blocked_by` theo lối tạm, ghim cứng tên hành động `unlock_door` | TSK-S3-02 / TSK-S3-03 |
| 3 | `gate publish` dừng ở mã băm, chưa ký số | Khối 3 (Gate Registry) |
| 4 | `perception/` và `sim/` chỉ là khung | TSK-S3-11 / TSK-S2-09 |

### 3.7 Điều hệ thống chưa làm được

Nói rõ để không ai đọc mốc 0.1.0 quá lên:

- ❌ **Chưa chạy được tác tử nào.** Không có HAL cho target nào; `run` thoát mã 2.
- ❌ **Chưa lượng giá gate.** Phân giải xong chính sách, nhưng chưa có engine
  nhận ngữ cảnh và trả phán quyết (TSK-S2-03).
- ❌ **Chưa có tương đương target.** `verify` kiểm ở mức lược đồ. Phát lại trên
  target thật và so khớp chuỗi phán quyết là TSK-S3-02 / TSK-S4-03.
- ❌ **Chưa có `@action`.** Việc cấm gọi trực tiếp hành động vật lý (FR-ACE-02)
  là TSK-S2-05. Hiện `digital_out()` chỉ từ chối khi thiếu chữ ký.
- ❌ **Chưa có CEL.** `allow_when` chỉ nhận dạng mapping toán tử.
- ❌ **Chưa có số đo bộ nhớ.** Xem §3.4.

### 3.8 Bốn ràng buộc chuyển cho Sprint 4 (từ rà soát HAL)

Ghi lại ở đây để Sprint 4 không phải suy luận lại. Đầy đủ tại
[`docs/spec/hal_mcu_review.md`](docs/spec/hal_mcu_review.md) §2.

| # | Ràng buộc | Lý do |
|:---:|:---|:---|
| RB-1 | Không `malloc` trong đường dẫn âm thanh sau khởi tạo | Phân mảnh heap gây rớt khung; Tiêu chí 4 Sprint 5 đo bộ nhớ sau 4 giờ chạy |
| RB-2 | Đệm âm thanh cấp phát tĩnh trong PSRAM, đặt tên và **đo được** | Q-3 dành ≥ 2 MB PSRAM; không đo được thì không đối chiếu được |
| RB-3 | `digital.out` hủy được lệnh đang chờ trong ≤ 1 khung âm thanh | Hợp đồng thu hồi lệnh vật lý — xem nợ thiết kế #1 |
| RB-4 | Bảng năng lực là `const` trong flash | Tiết kiệm SRAM, và loại bỏ đường tắt vòng qua gate (A3) |

### 3.9 Thêm một fixture phản chứng

Việc thường gặp nhất khi build tiếp, nên ghi rõ quy trình:

1. Thêm tệp vào `fixtures/gates/invalid/` (hoặc `fixtures/traces/invalid/`).
2. Thêm mục tương ứng vào `expected_errors.yaml` cùng cấp:

   ```yaml
   ten_fixture.yaml:
     error: GateInheritanceError    # lớp lỗi
     code: NE2003                   # mã ổn định
     principle: 2                   # nguyên tắc B.5 bị vi phạm
     where_contains: "allow_when.risk_level"
     why_contains: "loosens the inherited condition"
   ```

3. Chạy `pytest -q`. Test cưỡng chế corpus khép kín **hai chiều**, nên thiếu một
   trong hai bước sẽ đỏ.

`where_contains` và `why_contains` là so khớp chuỗi con, nên có thể cải thiện
cách diễn đạt lỗi mà không phải sửa tệp này — nhưng **lớp lỗi, mã ổn định và
nguyên tắc B.5 thì không được trôi trong im lặng**.

---

[0.1.0]: https://github.com/letrongminh/neuroedge-init/releases/tag/v0.1.0
