# Quy ước đóng góp — NeuroEdge

> **Mã task:** TSK-S1-13 · **Yêu cầu liên quan:** FR-DX-04, FR-CI-05, §3.9

Tài liệu này nói ba điều: cách dựng môi trường, cách nộp thay đổi, và ba loại
thay đổi cần thủ tục riêng vì chúng chạm vào tầng an toàn hoặc nghĩa vụ pháp lý.

---

## 1. Dựng môi trường

```bash
cd python
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q          # phải xanh 100% trước khi sửa gì
```

Yêu cầu **Python 3.11+** (đã chốt). Toàn bộ mã dùng `tomllib` của thư viện
chuẩn, nên không có phụ thuộc TOML bên ngoài.

Bản dựng tái lập được (§3.9 nghĩa vụ 5 — ghim phiên bản):

```bash
.venv/bin/python -m pip install -r requirements-lock.txt
```

Kiểm tra nhanh toàn bộ artifact đã đóng băng:

```bash
.venv/bin/neuroedge verify
.venv/bin/neuroedge gate lint
.venv/bin/neuroedge trace validate ../fixtures/traces/*.json
```

## 2. Vòng đóng góp thông thường

1. Nhánh từ `main`, tên `<loại>/<mã-task>-<mô-tả-ngắn>`, ví dụ
   `feat/TSK-S2-03-gate-engine`.
2. Viết test trước khi viết hiện thực, nếu thay đổi có thể quan sát được.
3. `pytest -q` xanh. **Không có test bị skip vì thiếu phụ thuộc** — xem §5.
4. Commit theo Conventional Commits, phần thân dẫn chiếu mã task:

   ```
   feat(engine): cưỡng chế năm nguyên tắc kế thừa gate

   TSK-S1-02, TSK-S1-03. Hiện thực FR-GATE-06 → FR-GATE-08.
   ```

5. Hoàn tất theo **§8**: tiến độ trong roadmap, mục changelog, đặc tả nếu hành vi
   đổi — cùng PR với mã.

### Thông báo lỗi: hợp đồng ba thành phần

FR-DX-04 bắt buộc **mọi** thông báo lỗi nêu đủ ba thành phần: **sai ở đâu**,
**vì sao**, **cách xử lý**. Đây không phải khuyến nghị — nó được cưỡng chế bằng
cấu trúc: kế thừa `NeuroEdgeError` và truyền cả ba đối số.

```python
raise GateSchemaError(
    where=f"{path} -> allow_when.{criterion}",                  # ở đâu
    why=f"operator {operator!r} is not defined for {kind!r}",    # vì sao
    how="use one of ['eq', 'gte', 'lte'] (Phụ lục B.2)",         # cách xử lý
)
```

Không dùng `raise ValueError("bad gate")`. Test
`test_invalid_fixture_diagnostic_has_all_three_parts` kiểm tra điều này trên
toàn bộ corpus phản chứng.

### Không in kết quả mà mình chưa tính

Lệnh CLI chưa có engine phải **thoát mã 2** và nói rõ task nào sẽ hiện thực nó.
Không được in bảng "PASS" giả. Lý do rất thực tế: đầu ra của CLI bị dán vào báo
cáo tiến độ như bằng chứng, và một dòng "TARGET EQUIVALENCE VERIFIED" từ một
lệnh chưa làm gì là thông tin sai cho người ra quyết định phạm vi.

Hợp đồng mã thoát: `0` kiểm tra đã chạy và đạt · `1` đã chạy và không đạt ·
`2` chưa hiện thực.

## 3. Thay đổi lược đồ — bắt buộc có RFC

Ba tệp trong `schemas/` đã **đóng băng**. Chúng là thước đo tuân thủ cho Khối 1a
và 1b, đầu vào của `neuroedge verify`, và đối tượng của chữ ký số gate.

| Thay đổi | Thủ tục |
|:---|:---|
| Sửa `schemas/*.json` | **RFC bắt buộc** — xem [`docs/rfc/`](docs/rfc/) |
| Sửa ngữ nghĩa phân giải gate (`gate_resolver.py`, `constraints.py`) | **RFC bắt buộc** |
| Sửa ba tệp vết ghi chuẩn mực ở `fixtures/traces/` | **RFC bắt buộc** |
| Thêm fixture mới (hợp lệ hoặc phản chứng) | PR thường |
| Thêm profile bo mạch ở `boards/` | PR thường — nhưng cần phần cứng thật để điền tham số. *Hiện `test_boards.py` chỉ nhận đúng ba profile bậc 1; profile bậc 2/3 chờ RFC-0002 hạ cánh (bất biến theo bậc, §5)* |
| Thêm gate mẫu ở `gates/` | PR thường |

Quy trình RFC: sao `docs/rfc/0000-template.md`, mở PR **chỉ chứa tệp RFC**,
thảo luận, rồi sửa lược đồ trong PR thứ hai dẫn chiếu số RFC. Thay đổi chạm
`gate.v1` hoặc ngữ nghĩa phân giải cần **kỹ thuật trưởng** phê duyệt.

[RFC-0001](docs/rfc/0001-gate-schema-conditional-requirements.md) là ví dụ mẫu
đầy đủ.

### Điều cần hiểu rõ về giới hạn của lược đồ

> **Thẩm định lược đồ một mình không kết luận được một gate là an toàn.**

JSON Schema thẩm định **một** tài liệu. Nguyên tắc kế thừa số 2 — *gate con chỉ
được siết chặt `allow_when`* — là mệnh đề về **hai** tài liệu, nên nằm ngoài
khả năng diễn đạt của lược đồ. Nó được cưỡng chế bởi bộ phân giải.

Hệ quả thực hành: `neuroedge gate lint` (phân giải) là cổng kiểm tra, không phải
thẩm định lược đồ. CI chạy lint, và một gate chưa phân giải được thì chưa được
nạp lên thiết bị.

### Thêm một fixture phản chứng

Corpus phản chứng là khép kín: mỗi tệp trong `invalid/` phải có một mục trong
`expected_errors.yaml`, và mỗi mục phải có một tệp. Test cưỡng chế cả hai chiều,
nên không thể thêm fixture mà không nói nó chứng minh điều gì.

```yaml
# fixtures/gates/expected_errors.yaml
ten_fixture.yaml:
  error: GateInheritanceError    # lớp lỗi
  code: NE2003                   # mã ổn định
  principle: 2                   # nguyên tắc B.5 bị vi phạm
  where_contains: "allow_when.risk_level"
  why_contains: "loosens the inherited condition"
```

## 4. Port mã nguồn mở — nghĩa vụ trước khi viết dòng đầu tiên

§3.9 của roadmap là **nghĩa vụ pháp lý**, không phải thủ tục giấy tờ. Năm việc,
làm xong trước khi port:

| # | Nghĩa vụ | Cách làm trong kho này |
|:---:|:---|:---|
| 1 | Ma trận giấy phép | Cập nhật [`NOTICE`](NOTICE): dự án, phiên bản, giấy phép, ngày xác minh, phạm vi dùng |
| 2 | Tệp `NOTICE` ở gốc | Một mục cho mỗi thành phần |
| 3 | Ghi nhận tại chỗ trong mã | Chú thích đầu tệp đã port, nêu **tệp gốc và commit tham chiếu** |
| 4 | Ghi nhận trong tài liệu công khai | Không giấu trong mã nguồn |
| 5 | Ghim phiên bản mọi phụ thuộc | `requirements-lock.txt`; nightly phát hiện thay đổi phá vỡ ở thượng nguồn |

Mẫu ghi nhận tại chỗ:

```python
# Ported from Pipecat (https://github.com/pipecat-ai/pipecat)
# Source file: src/pipecat/processors/frame_processor.py @ commit <sha>
# License: MIT. See NOTICE entry 2.
```

**Giấy phép copyleft mạnh (GPLv3, AGPL) không được vào phần phân phối.** Lõi là
MIT và lây nhiễm bản quyền sẽ lan sang dự án của khách hàng (§3.10). Đây là lý
do phụ thuộc `jsonschema` được ghim ở extra `[format-nongpl]`: extra `[format]`
mặc định kéo theo `rfc3987` có giấy phép GPL.

Quyết định **Q-11** (ngoại lệ giấy phép cho Hawkbit EPL-2.0, EMQX BSL, LiteLLM
enterprise) **vẫn đang mở**. Không port dòng nào từ ba dự án đó cho tới khi có
phê duyệt bằng văn bản.

## 5. Test không được skip trong im lặng

Một test `skip` vì thiếu phụ thuộc trông giống một test đạt trong bản tóm tắt.
Sprint 1 đã gặp đúng chuyện này: bốn test conformance lược đồ skip vì
`jsonschema` chưa được cài, trong khi bảng tiến độ báo "PASS 100% (4/4)".

Vì vậy:

- Không dùng `pytest.importorskip` cho phụ thuộc đã khai trong `pyproject.toml`.
- Phụ thuộc cần cho conformance là phụ thuộc **bắt buộc**, không phải tùy chọn.
- CI chạy `python -m pytest -q --strict-markers --junit-xml=../junit.xml`
  (`.github/workflows/ci-sim-linux.yml`), rồi đọc `junit.xml` và **fail nếu số
  test skip khác 0 hoặc số test bằng 0**.
- Output CLI được assert dưới dạng văn bản thuần. `tests/conftest.py` gỡ
  `FORCE_COLOR` và đặt `NO_COLOR` trước khi import CLI; đầu ra máy đọc (`--json`,
  digest) phải ghi thẳng stdout, không qua `rich`.

Khi đọc kết quả test, đọc cả cột skip.

## 6. Cấu trúc kho

| Đường dẫn | Nội dung | Thủ tục sửa |
|:---|:---|:---|
| `schemas/` | Ba lược đồ đã đóng băng | **RFC** |
| `gates/` | Gate mẫu, phân giải được | PR thường |
| `boards/` | Khai báo năng lực bo mạch (TOML) | PR thường |
| `fixtures/traces/` | Ba vết ghi chuẩn mực | **RFC** |
| `fixtures/traces/invalid/`, `fixtures/gates/` | Corpus phản chứng | PR thường |
| `python/neuroedge/engine/` | Phân giải gate, chuẩn tắc hóa | **RFC** nếu đổi ngữ nghĩa |
| `python/neuroedge/hal/` | HAL và model bo mạch | PR thường; xem [rà soát MCU](docs/spec/hal_mcu_review.md) |
| `targets/esp32s3/` | Firmware ESP-IDF | PR thường |
| `docs/rfc/`, `docs/spec/`, `docs/reports/`, `docs/designs/` | RFC, đặc tả chuẩn tắc, báo cáo đo, kế hoạch thiết kế | PR thường |
| `docs/archive/` | Biên bản review đã khép — lưu để truy nguồn, không quy phạm | Chỉ thêm, không sửa nội dung |
| `docs/user/` | Tài liệu người dùng; `thuat-ngu.md` là nơi duy nhất giải mã ký hiệu | PR thường; `trang-thai.md` do máy sinh |
| `docs/user/` | Tài liệu cho người dùng; `trang-thai.md` sinh tự động từ roadmap §0 | PR thường — chạy `python3 scripts/gen_user_status.py` |
| `TODOS.md` | Việc đã xem xét và hoãn có chủ ý, kèm mốc kích hoạt | PR thường |
| `scripts/` | Công cụ CI | PR thường |

## 7. CI

| Workflow | Khi nào chạy | Nội dung |
|:---|:---|:---|
| [`ci-sim-linux.yml`](.github/workflows/ci-sim-linux.yml) | Mỗi PR và push | Lược đồ, phân giải gate, vết ghi, test, lint, kiểm tra skip · job `linux-hal`: dựng gpio-sim, chạy `python/tests_linux/`, `verify --targets sim,linux` · job `wheel-smoke`: build sdist → wheel, cài vào venv sạch, chạy cả hành trình ngoài kho (`scripts/wheel_smoke.sh`) |
| [`nightly-hardware.yml`](.github/workflows/nightly-hardware.yml) | Hằng đêm | Dựng ESP-IDF, kiểm tra dung lượng firmware theo Q-3, thu số đo bộ nhớ |

`ci-sim-linux.yml` phải xanh trước khi hợp nhất. `nightly-hardware.yml` có phần
chạy trên runner tự quản có bo mạch thật; phần đó bỏ qua khi chưa có runner, và
nói rõ là đã bỏ qua thay vì báo đạt.

## 8. Hoàn thành một task — cập nhật tài liệu, tiến độ, changelog

Đây là **nơi duy nhất** định nghĩa việc phải làm khi xong một task. Roadmap §0.4,
roadmap §11.2, `CLAUDE.md` và mẫu PR chỉ dẫn về đây.

Một task **chưa xong** cho tới khi các cập nhật dưới đây nằm **trong cùng PR** với mã.

### 8.1 Mỗi sự thật có đúng một nơi

| Sự thật | Nơi duy nhất | Nơi khác được phép |
|:---|:---|:---|
| Trạng thái task, artifact, commit | Bảng task của sprint trong `neuroedge-roadmap.md` §4–§8 | Dẫn mã task |
| Tiêu chí ra đạt hay chưa, kèm bằng chứng | Danh sách tiêu chí ra ngay dưới bảng task của sprint | Dẫn mã sprint + số tiêu chí |
| Tổng quan tiến độ, số test hiện hành, hạng mục bị chặn | Roadmap §0.1–§0.2 | Không chép con số |
| Việc tiếp theo, đang làm gì | Roadmap §0.3 (Thẻ bàn giao) | Không |
| Đã thay đổi gì | `CHANGELOG.md` §1 | Không |
| Cách chạy, lệnh, đầu ra kỳ vọng | `CHANGELOG.md` §2 | `README.md` gốc (cũng là trang PyPI, nên mọi link tuyệt đối): tối đa 3 lệnh bắt đầu nhanh, kèm link §2 — `tests/test_readme_quickstart.py` chạy đúng các lệnh đó |
| Bất biến không được phá | `CHANGELOG.md` §3.3 | Dẫn số bất biến |
| Quyết định | `neuroedge-prd.md` §15 (mã `Q-N`) | Dẫn mã `Q-N` |
| Ý nghĩa của một mã / ký hiệu | `docs/user/thuat-ngu.md` | Dẫn mã |
| Yêu cầu và đặc tả | PRD (`FR-*`, `NFR-*`) · proposal (Phụ lục) · `docs/rfc/` | Dẫn mã |
| Việc hoãn có chủ ý | `TODOS.md`, kèm mốc kích hoạt | Dẫn số mục |

Nơi khác **dẫn mã** (`TSK-S2-03`, `Q-17`, `RFC-0004`, `TODOS.md #15`), không chép
lại nội dung. Khi cần chép một câu để câu văn đọc được, đó là dấu hiệu nên dẫn mã.

### 8.2 Checklist, theo thứ tự

1. **Máy xanh.** `pytest -q` → 0 failed, 0 skipped · `ruff check .` và
   `ruff format --check .` (trong `python/`) sạch · `neuroedge gate lint` xanh.
   Đây là đúng những gì CI chạy (§7).
2. **Tiến độ, trong roadmap.**
   - Dòng task: `✅ Hoàn thành (YYYY-MM-DD)` + đường dẫn artifact + commit hoặc PR.
     Làm dở thì `🟡`. Hoãn thì `⏸ Hoãn` + lý do một dòng + mốc (và một mục `TODOS.md`).
   - Tiêu chí ra: `[x]` + **bằng chứng chạy lại được** (lệnh + kết quả, hoặc tên test).
   - §0.1–§0.2: sửa con số (tỷ lệ sprint, số test, hạng mục bị chặn).
   - §0.3: **thay** các mục đã lỗi thời, không nối thêm. Xem §8.3.
3. **Changelog.** Thêm một mục vào `## [Chưa phát hành]` ở đầu `CHANGELOG.md` §1,
   dưới đúng nhóm *Đã thêm / Đã đổi / Đã sửa / Đã bỏ*:

   ```markdown
   - **TSK-S2-03 — Gate Engine trả phán quyết.** `python/neuroedge/engine/gate.py`.
     Kiểm: `pytest tests/test_gate_engine.py`. (FR-GATE-03, Q-17)
   ```

   Tối đa 3 dòng. Câu đầu là thay đổi **quan sát được**; sau đó là nơi của nó và
   cách kiểm. Lý do dài và bối cảnh thuộc PR hoặc RFC, không thuộc changelog.
   Nếu lệnh hoặc đầu ra kỳ vọng đổi, sửa `CHANGELOG.md` §2. Nếu thêm một bất biến,
   sửa §3.3.
4. **Đặc tả, chỉ khi hành vi khác đặc tả.** Sửa FR/NFR hoặc Phụ lục cho khớp. Sửa
   `schemas/`, ngữ nghĩa phân giải gate, hoặc ba vết ghi chuẩn mực thì **bắt buộc RFC**
   (§3). Có quyết định mới thì cấp mã `Q-N` ở PRD §15.
5. **Hoãn.** Việc cắt ra khỏi task vào `TODOS.md`, kèm mốc kích hoạt. Mục `TODOS.md`
   mà task vừa làm xong thì **xoá**, và ghi vào changelog.
6. **Quét tham chiếu lỗi thời.** Với mỗi sự thật vừa đổi (trạng thái, số liệu, tên),
   `grep` mã hoặc con số cũ trong `*.md` và sửa. Một câu đúng hôm qua mà sai hôm nay
   tệ hơn không có câu nào.

### 8.3 Quy tắc viết

- **Thay, đừng nối.** Bảng trạng thái và Thẻ bàn giao mô tả *hiện tại*. Lịch sử
  thuộc `CHANGELOG.md` và git.
- **Thẻ bàn giao ngắn.** *Vừa hoàn thành* chỉ gồm mã task hoặc quyết định của
  **phiên gần nhất**, mỗi mục một dòng. *Việc tiếp theo* tối đa 5 mục, đúng thứ
  tự làm. *Lưu ý* chỉ giữ điều chưa có ở `CHANGELOG.md` §3.3, mỗi điều một dòng kèm mã.
- **Không ghi con số dễ lỗi thời ngoài nơi của nó.** Số test, số fixture, phần trăm
  tiến độ chỉ nằm ở roadmap §0.1. Nơi khác viết điều kiện (*"0 failed, 0 skipped"*,
  *"mọi tệp trong `invalid/` đều bị từ chối"*), không viết số.
- **Ngày tuyệt đối** (`2026-09-28`), không viết "tuần sau" hay "Tuần N ở đây".
- **Câu ngắn, một ý.** Bảng khi có từ ba mục cùng cấu trúc trở lên. Tiếng Việt;
  mã, lệnh, đường dẫn giữ nguyên.
