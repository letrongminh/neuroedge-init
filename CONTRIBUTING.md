# Quy ước đóng góp — NeuroEdge

> **Mã task:** TSK-S1-13 · **Yêu cầu liên quan:** FR-DX-04, FR-CI-05, §3.9

Tài liệu này nói cách nộp thay đổi, thay đổi nào cần thủ tục riêng vì chạm tầng an
toàn hoặc nghĩa vụ pháp lý, và việc phải làm khi xong một task.

---

## 1. Dựng môi trường

Lệnh dựng môi trường, bản dựng tái lập và kiểm nhanh artifact: `CHANGELOG.md`
[§2.1–§2.2](CHANGELOG.md#2-cách-vận-hành). Trước khi sửa gì, `pytest -q` phải xanh:
0 failed, 0 skipped.

## 2. Vòng đóng góp thông thường

**Giấy phép của đóng góp (Q-45).** Mã theo PolyForm Noncommercial 1.0.0; lược đồ, đặc tả và bộ kiểm
tuân thủ theo Apache-2.0 — bảng phạm vi ở [`LICENSING.md`](LICENSING.md). PR từ người ngoài cần
CLA ký trước khi merge, để NeuroEdge cấp được license thương mại cho cả phần đóng góp; chưa có CLA
thì PR được review nhưng không merge (`TODOS.md` #43).

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
toàn bộ corpus phản chứng. Mã lỗi (`NE…`) cấp ở PRD
[Phụ lục B](neuroedge-prd.md#phụ-lục-b--danh-mục-mã-lỗi-chuẩn).

### Không in kết quả mà mình chưa tính

Lệnh (hoặc `--target`) chưa có engine thoát **mã 2** và nói task nào sẽ hiện thực
nó — bất biến `CHANGELOG.md` §3.3 #10; bảng mã thoát ở §2.3.

## 3. Thay đổi cần RFC

Đây là **danh sách duy nhất** các thay đổi phải có RFC. Nơi khác (`CLAUDE.md`, mẫu RFC,
`docs/rfc/README.md`) dẫn về đây.

| Thay đổi | Thủ tục |
|:---|:---|
| Sửa `schemas/*.json` | **RFC** |
| Sửa ngữ nghĩa phân giải gate (`engine/gate_resolver.py`, `engine/constraints.py`) | **RFC** |
| Sửa ba vết ghi chuẩn mực `fixtures/traces/*.json` | **RFC** |
| Sửa hoặc xoá gate đã khoá trong `digests.lock` (`gates/`, `fixtures/gates/valid/`, `fixtures/gates/registry/`) | **RFC**, rồi `python scripts/check_digests.py --accept <tệp> --rfc NNNN`; thiếu RFC thì CI đỏ (TSK-S3-16) |
| Đổi bố cục nhị phân `NETR` v1 của cây trên thiết bị ([RFC-0003](docs/rfc/0003-bo-cuc-nhi-phan-cay.md)): `engine/binary_tree.py` ↔ walker `targets/esp32s3/components/ne_gate/` | **RFC** (tăng số phiên bản bố cục) |
| Thêm gate vào `gates/` hoặc `fixtures/gates/{valid,registry}/` | PR thường — `python scripts/check_digests.py --update` để khoá digest |
| Thêm fixture phản chứng, hoặc ca corpus tool call / thoại | PR thường — theo luật khép kín ngay dưới |
| Thêm profile bo mạch ở `boards/` | PR thường — cần phần cứng thật để điền tham số. *Hiện `test_boards.py` chỉ nhận ba profile bậc 1; bậc 2/3 chờ RFC-0002* |

Quy trình: sao `docs/rfc/0000-template.md`, mở PR **chỉ chứa tệp RFC**, thảo luận,
rồi sửa trong PR thứ hai dẫn chiếu số RFC. Thay đổi chạm `gate.v1` hoặc ngữ nghĩa
phân giải cần **kỹ thuật trưởng** phê duyệt. [RFC-0001](docs/rfc/0001-gate-schema-conditional-requirements.md)
là ví dụ mẫu đầy đủ.

Thẩm định lược đồ một mình không kết luận được gate an toàn; cổng kiểm tra là
`neuroedge gate lint` — bất biến `CHANGELOG.md` §3.3 #1.

### Thêm một fixture phản chứng

Mọi corpus là **khép kín hai chiều**: mỗi tệp có một mục đáp án, mỗi mục có một tệp.
Test cưỡng chế cả hai chiều, nên không thể thêm fixture mà không nói nó chứng minh
điều gì.

| Corpus | Tệp | Đáp án |
|:---|:---|:---|
| Gate | `fixtures/gates/invalid/` | `fixtures/gates/expected_errors.yaml` |
| Vết ghi | `fixtures/traces/invalid/` | `fixtures/traces/expected_errors.yaml` |
| Tool call | `fixtures/tool_calls/{valid,invalid}/` | `fixtures/tool_calls/expected_results.yaml` — luật ở [`docs/spec/tool_calling.md`](docs/spec/tool_calling.md) §9 |
| Máy trạng thái hội thoại | `fixtures/compliance/voice/*.json` | `fixtures/compliance/voice/expected_results.yaml` — luật ở [`docs/spec/voice_fsm.md`](docs/spec/voice_fsm.md) §9 |

```yaml
# fixtures/gates/expected_errors.yaml
ten_fixture.yaml:
  error: GateInheritanceError    # lớp lỗi
  code: NE2003                   # mã ổn định
  principle: 2                   # nguyên tắc B.5 bị vi phạm
  where_contains: "allow_when.risk_level"
  why_contains: "loosens the inherited condition"
```

Rồi `pytest -q`: thiếu một trong hai bước là đỏ. `where_contains` và `why_contains`
so khớp chuỗi con, nên diễn đạt lỗi được phép cải thiện; **lớp lỗi, mã ổn định và
nguyên tắc B.5 thì không được trôi trong im lặng**.

## 4. Port mã nguồn mở — nghĩa vụ trước khi viết dòng đầu tiên

Năm nghĩa vụ ghi nhận nguồn là **nghĩa vụ pháp lý**, không phải thủ tục giấy tờ
(đặc tả: proposal §3.9; hạn chót: roadmap §3.9). Cách làm từng việc trong kho này,
xong trước khi port:

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
# License: BSD-2-Clause (Copyright Daily). See NOTICE entry 2.
```

Giấy phép nào được vào phần phân phối: chính sách **Q-11**
([PRD §15](neuroedge-prd.md#15-sổ-quyết-định)); không copyleft mạnh là
bất biến `CHANGELOG.md` §3.3 #9. Hawkbit đã duyệt với điều kiện ở Q-11 (sửa thì công bố phần sửa); EMQX không dùng.

## 5. Test không được skip trong im lặng

Một test `skip` vì thiếu phụ thuộc trông giống một test đạt trong bản tóm tắt.
I0 đã gặp đúng chuyện này: bốn test conformance lược đồ skip vì
`jsonschema` chưa được cài, trong khi bảng tiến độ báo "PASS 100% (4/4)".

Vì vậy:

- Không dùng `pytest.importorskip` cho phụ thuộc đã khai trong `pyproject.toml`.
- Phụ thuộc cần cho conformance là phụ thuộc **bắt buộc**, không phải tùy chọn.
- CI chạy `python -m pytest -q --strict-markers --junit-xml=../junit.xml`
  (`.github/workflows/ci-sim-linux.yml`), rồi đọc `junit.xml` và **fail nếu số
  test skip khác 0 hoặc số test bằng 0**.
- `python/tests_linux/` cần gpio-sim nên nằm ngoài `testpaths` và chạy ở job riêng
  `linux-hal` — không phải skip trên máy không có gpio-sim.
- Output CLI được assert dưới dạng văn bản thuần. `tests/conftest.py` gỡ
  `FORCE_COLOR` và đặt `NO_COLOR` trước khi import CLI; đầu ra máy đọc (`--json`,
  digest) phải ghi thẳng stdout, không qua `rich`. Chữ trong ngoặc vuông ở `help=`
  phải escape (`\[mcp.servers]`), nếu không `rich` nuốt nó — `tests/test_cli_help.py`.

Khi đọc kết quả test, đọc cả cột skip.

## 6. Cấu trúc kho

Đây là **bản đồ duy nhất** của kho; nơi khác dẫn về đây.

| Đường dẫn | Nội dung | Thủ tục sửa |
|:---|:---|:---|
| `schemas/` | Ba lược đồ đã đóng băng: `gate.v1` · `trace.v1` · `board.v1` | **RFC** (§3) |
| `gates/` | Gate mẫu, phân giải được, gồm chuỗi kế thừa | Thêm: PR thường; sửa/xoá: **RFC** (§3) |
| `digests.lock` | Digest JCS của mọi gate chuẩn mực | Chỉ qua `scripts/check_digests.py` (§3) |
| `boards/` | Khai báo năng lực bo mạch (TOML) | PR thường (§3) |
| `fixtures/traces/*.json` | Ba vết ghi chuẩn mực | **RFC** |
| `fixtures/traces/invalid/`, `fixtures/gates/invalid/` | Corpus phản chứng + `expected_errors.yaml` | PR thường, khép kín (§3) |
| `fixtures/gates/valid/`, `fixtures/gates/registry/` | Gate phân giải đúng; gate cơ sở cho fixture | Thêm: PR thường; sửa/xoá: **RFC** |
| `fixtures/tool_calls/` | Corpus Gated Tool Profile + `expected_results.yaml` | PR thường, khép kín (§3) |
| `fixtures/decision_trees/` | Bảng sự thật cho walker C | Sinh bằng `scripts/generate_truth_tables.py`, không sửa tay |
| `fixtures/agents/` | Agent mẫu `villa-concierge`, `home-voice`, `driveway`, `voice-door`; `neuroedge new --template` sao hai cái đầu | PR thường |
| `fixtures/compliance/voice/` | Bộ vector tuân thủ máy trạng thái hội thoại + `expected_results.yaml`, chung cho hiện thực Python và C | PR thường, khép kín (§3) |
| `python/neuroedge/engine/` | L3 — phân giải gate, chuẩn tắc hoá, Gate Engine, cây quyết định, bố cục `NETR`, trình biên dịch `build` | **RFC** nếu đổi ngữ nghĩa phân giải hoặc bố cục `NETR` |
| `python/neuroedge/actions/` | `@action`, `c.do()`/`c.say()`, token phán quyết dùng một lần | PR thường; ranh giới ở [`threat_model.md`](docs/spec/threat_model.md) |
| `python/neuroedge/hal/` | L1 — năm nguyên thủy, mô hình bo mạch, `sim.py`, `linux.py` | PR thường; xem [rà soát MCU](docs/spec/hal_mcu_review.md) |
| `python/neuroedge/models/` | L2 — SystemOne/SystemTwo, ngữ pháp lệnh cục bộ, knowledge base, `providers/` (LiteLLM, adapter) | PR thường |
| `python/neuroedge/perception/` | L2 — máy trạng thái hội thoại (`voice_fsm.py`) và driver của nó (`voice_session.py`) | PR thường; hành vi theo [`voice_fsm.md`](docs/spec/voice_fsm.md) |
| `python/neuroedge/sim/` | `SimSession` (REPL gõ chữ), `ui.py` (trang `--ui` cục bộ) | PR thường |
| `python/neuroedge/mcp_server.py`, `mcp_host.py`, `mcp_desktop.py` | Máy chủ MCP · System 2 làm MCP host · cấu hình Claude Desktop | PR thường |
| `python/neuroedge/testing/` | Action CI — recorder, player (replay), assertions, golden, `tool_corpus`, `voice_corpus`, `uart` (vết ghi từ UART thiết bị) | PR thường |
| `python/neuroedge/viz/` | `trace view`, xuất Perfetto | PR thường |
| `python/neuroedge/templates/` | Mẫu dự án cho `neuroedge new` (`*.tmpl`, generator Python thuần) | PR thường |
| `python/neuroedge/cli/` | CLI Typer: `main.py`, `run.py` (REPL), `explain.py` | PR thường |
| `python/neuroedge/errors.py`, `trace.py`, `paths.py` | Hợp đồng lỗi 3 thành phần · thẩm định vết ghi · định vị asset (checkout, editable, wheel) | PR thường; đụng `paths.py` thì chạy `scripts/wheel_smoke.sh` |
| `python/tests/` | Bộ test chính (`testpaths`) | PR thường |
| `python/tests_linux/` | Test trên gpio-sim, job `linux-hal` | PR thường |
| `python/hatch_build.py`, `pyproject.toml`, `requirements-lock.txt`, `pip-audit-ignore.txt`, `LICENSE` | Đóng gói (asset vào `neuroedge/_data/`, README gốc vào metadata) · phụ thuộc ghim · ngoại lệ `pip-audit` đã duyệt (job `pip-audit`) · bản sao `LICENSE` gốc | PR thường; chạy `scripts/wheel_smoke.sh` |
| `targets/esp32s3/` (gốc) | Dự án ESP-IDF: `CMakeLists.txt`, `sdkconfig.defaults` (flash 16 MB, PSRAM, FreeRTOS 1000 Hz), `sdkconfig.qemu` (lớp phủ cho QEMU), `partitions.csv` (factory + OTA A/B) | PR thường; job `firmware-qemu` |
| `targets/esp32s3/main/` | Firmware ESP-IDF: `main.c`, khung đo bộ nhớ, self-test gate (ghi vết ghi `NE1`), replay vết ghi chuẩn mực (`trace_vectors.c`); `gates/` sinh bằng `scripts/gen_firmware_gates.py`, `vectors/` bằng `scripts/gen_firmware_vectors.py` | PR thường; đổi vết ghi chuẩn mực, gate hay action ⇒ sinh lại `vectors/` |
| `targets/esp32s3/components/ne_gate/` | Walker C99 và sổ token C | PR thường; bố cục `NETR`: **RFC** |
| `targets/esp32s3/components/ne_trace/` | Dòng vết ghi `NE1` trên UART — định dạng C99, không biến toàn cục ([`simulation_coverage.md`](docs/spec/simulation_coverage.md) §4) | PR thường; job `firmware-qemu` |
| `scripts/` | Công cụ CI và phát hành | PR thường |
| `.github/` | Năm workflow ở `workflows/` — danh sách job: `CHANGELOG.md` §2.5; `dependabot.yml` (ghim SHA của Actions), `actionlint.yaml` | PR thường |
| `docs/rfc/`, `docs/spec/`, `docs/reports/` | RFC, đặc tả chuẩn tắc, báo cáo đo | PR thường |
| `docs/architecture/` | Kiến trúc sản phẩm song ngữ: `README.md` · `vi/` + `en/` (14 file mỗi cây, VI là gốc) · `assets/excalidraw/` (nguồn) + `assets/svg/` (export) | PR thường — sửa `.excalidraw` thì export lại `.svg` cùng commit; nội dung dẫn mã, không chép (MECE §8.1) |
| `docs/archive/` | Lịch sử đã khép, lưu để truy nguồn, không quy phạm: kế hoạch Giai đoạn 1 đã duyệt, biên bản review Giai đoạn 1 và RFC-0002 | Chỉ thêm, không sửa nội dung |
| `docs/business/` | Bộ chuẩn bị cổng nhu cầu (Q-20); `cpo-dashboard.html` sinh từ roadmap, `TODOS.md`, PRD §15, `CHANGELOG.md` | PR thường — đổi các nguồn đó thì chạy `python3 scripts/gen_cpo_dashboard.py` |
| `wireframe/` | Wireframe HTML tham chiếu cho UI (bản chụp `ui.css`, không đóng gói) — hiện có Lab Monitor của Khối N5b | PR thường |
| `docs/user/` | Tài liệu người dùng; `thuat-ngu.md` là nơi duy nhất giải mã ký hiệu; `trang-thai.md` sinh từ roadmap §0 | PR thường — `python3 scripts/gen_user_status.py` |
| `docs/release.md` | Thủ tục phát hành: tag nội bộ trước I6, PyPI từ I6 | PR thường |
| `README.md` | Trang đầu và trang PyPI (link tuyệt đối) | PR thường — `tests/test_readme_quickstart.py` |
| `neuroedge-roadmap.md` | Roadmap duy nhất (Q-39): increment I0–I18, trạng thái task, tiêu chí ra, dự báo, phụ thuộc, thẻ phát hành, thang cắt | PR thường, theo §8; luật chống lệch R1–R12 ở roadmap §2.4 |
| `neuroedge-roadmap-phase1-5.md`, `neuroedge-roadmap-phase2.md`, `draft-ke-hoach-mo-rong-robot-fofoca.md`, `draft-rfc-node-giao-thuc-dieu-phoi.md` | Ghi chú thiết kế: NeuroBrain · thị giác và phủ phần cứng · robot phân tầng. Không lịch, không trạng thái, không tiêu chí ra; dẫn mã TSK của roadmap (R1, R8) | PR thường; merge được cả khi Beta đóng băng (R12) |
| `TODOS.md` | Việc đã xem xét và hoãn có chủ ý, kèm mốc kích hoạt | PR thường |

## 7. CI

Workflow, job và cổng: `CHANGELOG.md` §2.5. `ci-sim-linux.yml` phải xanh trước khi
hợp nhất.

## 8. Hoàn thành một task — cập nhật tài liệu, tiến độ, changelog

Đây là **nơi duy nhất** định nghĩa việc phải làm khi xong một task. Roadmap §0.4,
roadmap §11.2, `CLAUDE.md` và mẫu PR chỉ dẫn về đây.

Một task **chưa xong** cho tới khi các cập nhật dưới đây nằm **trong cùng PR** với mã.

### 8.1 Mỗi sự thật có đúng một nơi

| Sự thật | Nơi duy nhất | Nơi khác được phép |
|:---|:---|:---|
| Trạng thái task, artifact, commit | Bảng task trong mục của increment, `neuroedge-roadmap.md` §4–§8 | Dẫn mã task |
| Mục tiêu, điều kiện vào, tín hiệu đo, người của một increment | Thẻ ở đầu mục của increment đó (roadmap §4–§7) | Dẫn mã increment (`I3`) |
| Tiêu chí ra đạt hay chưa, kèm bằng chứng | Danh sách tiêu chí ra ngay dưới bảng task của increment | Dẫn mã increment + số tiêu chí (`I3 tiêu chí 2`) |
| Lịch: ngày dự báo, phụ thuộc, thẻ phát hành | Roadmap §0.2 (bảng increment) | Dẫn mã increment; không chép ngày hay tag |
| Tổng quan tiến độ, số test hiện hành, hạng mục bị chặn | Roadmap §0.1–§0.2 | Không chép con số |
| Việc tiếp theo, đang làm gì | Roadmap §0.3 (Thẻ bàn giao) | Không |
| Thang cắt phạm vi | Roadmap §9 | Dẫn bậc hoặc increment |
| Giá trị đo B1–B5 (và A1 đo đầy đủ) | Roadmap §5.5 | Ngưỡng ở PRD §11; nơi khác dẫn mã |
| Thiết kế (không lịch, không trạng thái) | Ghi chú thiết kế (`neuroedge-roadmap-phase1-5.md`, `neuroedge-roadmap-phase2.md`, `draft-*.md`) · `docs/spec/` · `docs/rfc/` | Roadmap dẫn tới; ghi chú thiết kế dẫn mã TSK, không ghi trạng thái (R1) |
| Rủi ro sản phẩm (`R-n`) | PRD §13.2 | Dẫn mã |
| Đã thay đổi gì | `CHANGELOG.md` §1 | Không |
| Cách chạy, lệnh, đầu ra kỳ vọng, workflow và job CI | `CHANGELOG.md` §2 | `README.md` gốc (cũng là trang PyPI, nên mọi link tuyệt đối): tối đa 3 lệnh bắt đầu nhanh, kèm link §2 — `tests/test_readme_quickstart.py` chạy đúng các lệnh đó |
| Bất biến không được phá | `CHANGELOG.md` §3.3 | Dẫn số bất biến |
| Thay đổi nào cần RFC | `CONTRIBUTING.md` §3 | Dẫn §3 |
| Cấu trúc kho | `CONTRIBUTING.md` §6 | Dẫn §6 |
| Quyết định | `neuroedge-prd.md` §15 (mã `Q-N`) | Dẫn mã `Q-N` |
| Chính sách giấy phép (allowlist) | `neuroedge-prd.md` §15, Q-11 | `NOTICE` ghi ma trận từng thành phần, dẫn Q-11 |
| Mã lỗi `NE…` | PRD Phụ lục B | Dẫn mã |
| Ý nghĩa của một mã / ký hiệu | `docs/user/thuat-ngu.md` | Dẫn mã |
| Yêu cầu và đặc tả | PRD (`FR-*`, `NFR-*`) · proposal (Phụ lục) · `docs/rfc/` · `docs/spec/` | Dẫn mã |
| Việc hoãn có chủ ý | `TODOS.md`, kèm mốc kích hoạt | Dẫn số mục |

Nơi khác **dẫn mã** (`TSK-S2-03`, `Q-17`, `RFC-0004`, `TODOS.md #15`), không chép
lại nội dung. Khi cần chép một câu để câu văn đọc được, đó là dấu hiệu nên dẫn mã.

### 8.2 Checklist, theo thứ tự

1. **Máy xanh.** `pytest -q` → 0 failed, 0 skipped · `ruff check .` và
   `ruff format --check .` (trong `python/`) sạch · `neuroedge gate lint` xanh. CI chạy
   thêm các cổng ở `CHANGELOG.md` §2.5 (digest, corpus nghịch đảo, giấy phép, wheel).
2. **Tiến độ, trong roadmap.**
   - Dòng task: ô trạng thái có **đúng một** glyph (R9) — ✅ xong · 🟡 đang làm hoặc xong
     một phần · ⏳ chưa bắt đầu · ⏸ hoãn · 🔴 bị chặn. Xong: `✅ Hoàn thành (YYYY-MM-DD)` +
     đường dẫn artifact + commit hoặc PR. Hoãn: `⏸ Hoãn` + lý do một dòng + mốc (và một
     mục `TODOS.md`). Bị chặn: `🔴` + thứ đang chặn.
   - Task mới: cấp mã theo họ mã ở roadmap §2.4 — việc thuộc một họ có sẵn thì dùng họ đó,
     không thì `TSK-I<n>-<nn>` với `n` là increment đầu tiên lên lịch nó. Mã không bao giờ
     đánh lại; dời task sang increment khác là dời dòng của nó.
   - Tiêu chí ra: `[x]` + **bằng chứng chạy lại được** (lệnh + kết quả, hoặc tên test).
   - §0.2: sửa cột "Tiến độ" của increment mỗi khi một task của nó đổi trạng thái (số ✅
     trên tổng số task, R10), và cột "Trạng thái" nếu cần. Cột "Dự báo" chỉ đổi **cùng PR
     với bằng chứng** làm nó đổi, và dời luôn mọi increment phụ thuộc (R5).
   - §0.1: sửa con số (số test, hạng mục bị chặn).
   - §0.3: **thay** các mục đã lỗi thời, không nối thêm. Xem §8.3.
3. **Changelog.** Một mục trong `## [Chưa phát hành]` ở đầu `CHANGELOG.md` §1,
   dưới đúng nhóm *Đã thêm / Đã đổi / Đã sửa / Đã bỏ*:

   ```markdown
   - **TSK-S2-03 — Gate Engine trả phán quyết.** `python/neuroedge/engine/gate.py`.
     Kiểm: `pytest tests/test_gate_engine.py`. (FR-GATE-03, Q-17)
   ```

   Tối đa 3 dòng, mở đầu bằng mã task (không có task thì mã `Q-N` hoặc `FR-*`); được đặt
   mã increment phía trước (`**I3 · TSK-S4-01 — …**`). Câu đầu là thay đổi **quan sát
   được**; sau đó là nơi của nó và cách kiểm. **Một tính năng một mục:** task đã có
   mục trong `[Chưa phát hành]` thì sửa mục đó cho khớp trạng thái cuối, không thêm
   mục mới. Quyết định chỉ dẫn mã `Q-N` — nội dung ở PRD §15. Lý do dài và bối cảnh
   thuộc PR hoặc RFC. Nếu lệnh hoặc đầu ra kỳ vọng đổi, sửa `CHANGELOG.md` §2. Nếu
   thêm một bất biến, sửa §3.3.
4. **Đặc tả, chỉ khi hành vi khác đặc tả.** Sửa FR/NFR hoặc Phụ lục cho khớp. Thay
   đổi nằm trong danh sách §3 thì **bắt buộc RFC**. Có quyết định mới thì cấp mã
   `Q-N` ở PRD §15.
5. **Hoãn.** Việc cắt ra khỏi task vào `TODOS.md`, kèm mốc kích hoạt — một increment, một
   mã task hoặc một sự kiện quan sát được, không phải tuần hay tháng. Mục `TODOS.md`
   mà task vừa làm xong thì **xoá**, và ghi vào changelog. Mục nào có mốc kích hoạt
   nhắc tới task vừa xong thì **đọc lại mốc đó** — mốc đã tới thì xử lý hoặc viết lại.
6. **Quét tham chiếu lỗi thời.** Với mỗi sự thật vừa đổi (trạng thái, số liệu, tên),
   `grep` mã hoặc con số cũ trong `*.md` và sửa. Một câu đúng hôm qua mà sai hôm nay
   tệ hơn không có câu nào.

### 8.3 Quy tắc viết

- **Thay, đừng nối.** Bảng trạng thái và Thẻ bàn giao mô tả *hiện tại*. Lịch sử
  thuộc `CHANGELOG.md` và git.
- **Thẻ bàn giao ngắn.** *Vừa hoàn thành* chỉ gồm mã task hoặc quyết định của
  **phiên gần nhất**, mỗi mục một dòng. *Việc tiếp theo* tối đa 5 mục, đúng thứ
  tự làm. *Lưu ý* chỉ giữ điều chưa có ở `CHANGELOG.md` §3.3, mỗi điều một dòng kèm mã.
- **Không ghi con số dễ lỗi thời ngoài nơi của nó.** Số test, số fixture, tiến độ
  chỉ nằm ở roadmap §0.1–§0.2; ngày dự báo chỉ ở §0.2. Nơi khác viết điều kiện
  (*"0 failed, 0 skipped"*, *"mọi tệp trong `invalid/` đều bị từ chối"*), không viết số.
- **Lịch bằng increment và ngày tuyệt đối.** Xếp lịch bằng mã increment (`I3`, "sau
  I8") hoặc ngày tuyệt đối (`2026-11-16`); không dùng `Tuần N`, `Tháng N`, `Sprint N`
  hay "tuần sau" cho lịch mới (R6). Khoảng thời gian tính từ lúc một increment mở
  ("2 tuần sau khi I8 mở"). Tên sprint và khối cũ chỉ dùng khi dẫn lịch sử.
- **Tham chiếu bằng mã hoặc mục**, không bằng số dòng (`tệp.md:NNN`) — R11.
- **Câu ngắn, một ý.** Bảng khi có từ ba mục cùng cấu trúc trở lên. Tiếng Việt;
  mã, lệnh, đường dẫn giữ nguyên.
