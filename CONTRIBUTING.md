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

5. Cập nhật `neuroedge-roadmap.md` theo §0.4 của chính tài liệu đó: chuyển trạng
   thái task, đánh dấu tiêu chí ra kèm **bằng chứng kiểm chứng**, và cập nhật
   Thẻ Bàn giao ở §0.3.

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
| Thêm profile bo mạch ở `boards/` | PR thường |
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
- CI chạy `pytest -q -p no:randomly --strict-markers` và **kiểm tra số test
  skip bằng 0**.

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
| `TODOS.md` | Việc đã xem xét và hoãn có chủ ý, kèm mốc kích hoạt | PR thường |
| `scripts/` | Công cụ CI | PR thường |

## 7. CI

| Workflow | Khi nào chạy | Nội dung |
|:---|:---|:---|
| [`ci-sim-linux.yml`](.github/workflows/ci-sim-linux.yml) | Mỗi PR và push | Lược đồ, phân giải gate, vết ghi, test, lint, kiểm tra skip |
| [`nightly-hardware.yml`](.github/workflows/nightly-hardware.yml) | Hằng đêm | Dựng ESP-IDF, kiểm tra dung lượng firmware theo Q-3, thu số đo bộ nhớ |

`ci-sim-linux.yml` phải xanh trước khi hợp nhất. `nightly-hardware.yml` có phần
chạy trên runner tự quản có bo mạch thật; phần đó bỏ qua khi chưa có runner, và
nói rõ là đã bỏ qua thay vì báo đạt.
