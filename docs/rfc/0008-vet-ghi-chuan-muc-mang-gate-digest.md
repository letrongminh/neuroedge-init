# RFC-0008: Ba vết ghi chuẩn mực mang `gate_digest` — phát lại kiểm nó

| | |
|:---|:---|
| **Mã RFC** | 0008 |
| **Tiêu đề** | Ba vết ghi chuẩn mực mang `gate_digest` trong `gate_evaluation_begin`; `verify` và `replay` kiểm nó |
| **Hợp đồng bị ảnh hưởng** | `trace.v1` *(chỉ nội dung `data` của ba vết ghi chuẩn mực — tệp lược đồ không đổi)* · ngữ nghĩa phát lại |
| **Yêu cầu PRD liên quan** | FR-CI-02, FR-CI-04, FR-CI-07, FR-TRC-04 |
| **Người đề xuất** | V1 — Kỹ sư lõi nền tảng |
| **Ngày mở** | 2026-09-27 |
| **Trạng thái** | ✅ Đã chấp thuận · ✅ Đã hiện thực (PR này) |
| **Người phê duyệt** | Chủ sản phẩm (product owner), 2026-09-27 |
| **Kiểm chứng** | §7 — `python/tests/test_player.py`, `python/tests/test_cli.py`, `python/tests/test_trace_vectors.py` |

> **Khi nào cần RFC:** sửa ba vết ghi chuẩn mực là một mục của `CONTRIBUTING.md` §3.

## 1. Vấn đề

Engine hôm nay ghi `gate_evaluation_begin {gate, gate_digest}` (`engine/gate.py`), và thiết bị ghi
cũng vậy (`simulation_coverage.md` §4). Nhưng ba vết ghi chuẩn mực trong `fixtures/traces/`
(`happy-path.json`, `unverified_attempt.json`, `network_offline.json`) ra đời trước trường này:
`gate_evaluation_begin` của chúng chỉ mang `{"gate": "unlock_door@1.2.0"}`. Ai hiện thực `trace.v1`
từ ba ví dụ chuẩn mực sẽ không bao giờ thấy trường đó, dù nó là thứ khiến một phán quyết trên
thiết bị truy ngược được tới đúng chính sách đã ký (ENG-T2, RFC-0003 §3).

## 2. Vì sao hiện trạng không giải quyết được

- `neuroedge verify` so vết ghi chuẩn mực với golden của chính nó trên cả ba target, nhưng trên
  `sim`/`linux` không có phép kiểm nào bảo đảm vết ghi được quyết bởi **chính gate nó đã được ghi
  cùng** — thiết bị có kiểm (`_device_replay`), host thì không.
- `neuroedge replay` trên vết ghi của người dùng không hề hay biết gate đã đổi từ lúc ghi: người
  siết gate rồi phát lại (quickstart, giờ 3) không được nói rằng phán quyết đang được tính bằng
  gate mới.
- Vết ghi không mang `gate_digest` thì không thể kiểm cả hai điều trên — vì vậy phải sửa ba vết
  ghi chuẩn mực, tức phải có RFC.

## 3. Thay đổi đề xuất

Mỗi `gate_evaluation_begin` của ba vết ghi chuẩn mực nhận đúng giá trị mà checkout biên dịch ra
hôm nay cho `unlock_door@1.2.0` (`compile_tree(resolve_gate_file("gates/unlock_door@1.2.0.yaml"))`):

```diff
     {
       "offset_ms": 550,
       "type": "gate_evaluation_begin",
-      "data": { "gate": "unlock_door@1.2.0" }
+      "data": {
+        "gate": "unlock_door@1.2.0",
+        "gate_digest": "sha256:2c20dc42616dbf9a3bf16b7967c3b01faa579e1186f55b928a85070a318a9ab5"
+      }
     }
```

Không gì khác trong ba tệp đổi: lệch JCS ⇒ `digest()` của tệp đổi ⇒ vector firmware sinh lại
(`scripts/gen_firmware_vectors.py` nhúng `digest(trace)` vào `device_info.trace_digest`).

**Hai luật phát lại, so sánh nằm trong một hàm** (`testing/player.gate_digest_changes`, dùng bởi
cả host lẫn thiết bị):

| Lệnh | Vết ghi | `gate_digest` đã ghi khác checkout biên dịch ra |
|:---|:---|:---|
| `neuroedge verify` | chuẩn mực (gate đóng băng) | **Lỗi** (`ReplayError`, NE4003) — vết ghi chuẩn mực phải được quyết bởi đúng gate nó được ghi cùng, như thiết bị |
| `neuroedge replay` | của người dùng | **Không lỗi** — gate có thể được siết có chủ ý (quickstart giờ 3); phát lại vẫn tính lại phán quyết và báo `SAFETY REGRESSION` như cũ, thêm một cảnh báo nói gate nào đã đổi (digest cũ → digest mới) |

Vết ghi không mang trường (ghi trước RFC-0008) phát lại đúng như trước — không có gì để so.

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — `trace.v1` để `data` tự do; thêm khoá vào `data` không cần đổi lược đồ |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Không |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không — `schemas/trace.v1.json` không đổi |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không — `digests.lock` chỉ khoá gate; gate không đổi |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | **Có — chính là thay đổi này** (RFC); `digest()` của mỗi tệp đổi, vector firmware sinh lại |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào |
| Bố cục `NETR` hoặc walker C phải đổi? | Không — thiết bị đã ghi `gate_digest` từ trước (`ne_trace.c`) |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không |

Vết ghi cũ không mang trường vẫn phát lại được (mục 3); `verify` trên thiết bị từ chối firmware
cũ như cũ.

## 5. Ảnh hưởng an toàn

Thay đổi này **không có đường nào làm một phán quyết lỏng hơn**:

- Phép kiểm chỉ **thêm** một điều kiện từ chối, không bỏ điều kiện nào: golden so quyết định như
  cũ, `SAFETY REGRESSION` (NE4002) như cũ, fail-closed như cũ.
- Trên `verify`, vết ghi chuẩn mực bị quyết bằng gate khác gate nó được ghi cùng là lỗi, chứ
  không bao giờ được so cho qua — một kết quả "đạt" về một thứ khác là kết quả không có nghĩa.
- Trên `replay`, cảnh báo không thay phép so: người dùng siết gate mà làm yếu an toàn vẫn thoát
  mã 1 với `SAFETY REGRESSION`. Cảnh báo chỉ nói sự thật "phán quyết này được tính bằng gate mới"
  — cùng kiểu với cảnh báo `[sim.sensor_facts]` đã có (`_sensor_rules_changed`).
- Vết ghi không mang trường không được so (không có gì để so): đây là đường **giữ nguyên hành vi
  cũ**, không phải đường bỏ qua một kiểm có sẵn.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Đổi `schemas/trace.v1.json` để bắt buộc `gate_digest` trong `gate_evaluation_begin` | Lược đồ là RFC riêng; vết ghi ghi trước RFC-0008 sẽ thành không hợp lệ — phá vỡ tương thích không cần thiết |
| `verify` chỉ cảnh báo như `replay` | Vết ghi chuẩn mực và gate của nó đóng băng cùng nhau; "đạt" trên gate khác là kết quả về một thứ khác |
| `replay` cũng lỗi khi gate khác | Phát lại sau khi siết gate là workflow có chủ ý (quickstart giờ 3); lỗi sẽ giết đúng việc phát lại cần kiểm |

## 7. Bằng chứng kiểm chứng

- [x] Ba vết ghi chuẩn mực mang trường, đúng giá trị checkout biên dịch ra —
  `python/tests/test_player.py::test_canonical_traces_carry_the_compiled_gate_digest`
- [x] `verify` lỗi rõ ràng khi digest của một vết ghi chuẩn mực bị sửa (bản sao tmp, fixture
  nguyên vẹn) — `python/tests/test_cli.py::test_verify_refuses_a_canonical_trace_decided_by_another_gate`
- [x] `replay` vết ghi ghi trước khi siết gate: cảnh báo nói gate cũ → gate mới, phán quyết vẫn
  so như cũ — `python/tests/test_player.py::test_replay_reports_a_gate_that_changed_since_the_recording`
- [x] Vết ghi không mang trường phát lại đúng như trước —
  `python/tests/test_player.py::test_a_trace_without_gate_digest_replays_unchanged`
- [x] Vector firmware sinh lại, `--check` xanh — `python/tests/test_trace_vectors.py`
  (thiết bị tự kiểm digest: `test_a_firmware_deciding_an_older_gate_is_refused_not_compared`)
- [x] `neuroedge verify` vẫn xanh; không test nào bị skip

## 8. Việc phải làm khi chấp thuận

- [x] Sửa ba vết ghi chuẩn mực; sinh lại `targets/esp32s3/main/vectors/` bằng
  `scripts/gen_firmware_vectors.py`
- [x] `testing/player.py`: một hàm so sánh, cảnh báo cho `replay`, tuỳ chọn cưỡng chế cho `verify`;
  `_device_replay` dẫn cùng hàm
- [x] `docs/spec/simulation_coverage.md` §4; `docs/architecture/{vi,en}/07-data-contracts.md`;
  `docs/architecture/{vi,en}/10-target-equivalence.md` — mỗi sự thật một nơi, dẫn RFC-0008
- [x] Dòng của RFC trong `docs/rfc/README.md`
- [x] Phụ lục `neuroedge-proposal.md` không đổi — hợp đồng sự kiện nằm ở
  `docs/spec/simulation_coverage.md` §3; lược đồ không đổi
