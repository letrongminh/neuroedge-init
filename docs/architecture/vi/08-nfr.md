# 08 · Yêu cầu phi chức năng → chiến thuật → bằng chứng

> **Phạm vi:** mỗi nhóm NFR của PRD §9 được kiến trúc đáp ứng bằng chiến thuật nào, và bằng chứng nằm
> ở đâu hôm nay. **Nguồn:** PRD §9 (yêu cầu, ngưỡng), PRD §11.1 (A1–A12), test trong `python/tests/`,
> job CI trong `.github/workflows/` (danh sách duy nhất: `CHANGELOG.md` §2.5).

Nhãn bằng chứng: **đã kiểm** — có test hoặc job CI chạy mỗi PR · **một phần** — có công cụ đo hoặc
kiểm một phần · **chưa đo** — chưa có bằng chứng.

## 1. Tổng quan

| Nhóm | Câu hỏi | Chiến thuật kiến trúc chính | Trạng thái |
|:---|:---|:---|:---|
| An ninh (SEC) | Có đường nào tới chân mà không qua gate? | Một đường duy nhất; HAL không sổ token thì từ chối; bên gọi không tin cậy | đã kiểm (SEC-01, 09); thiết bị: chưa |
| Độ tin cậy (REL) | Khi một phần hỏng thì sao? | Fail-closed mặc định; bộ ngắt mạch; vết ghi chuẩn mực đóng băng | đã kiểm (REL-02); REL-01, 03: chưa |
| Tài nguyên (RES) | Có vừa chip không? Có chạy khi mất mạng? | `NETR` nhị phân, walker không cấp phát; fallback cục bộ | một phần |
| Hiệu năng (PERF) | Có đủ nhanh? | Ngân sách thời gian mỗi gate, cưỡng chế fail-closed; đo từng chặng | công cụ có; ngưỡng **chưa đo** |
| Riêng tư (PRIV) | Dữ liệu nào được lưu? | Không lưu âm thanh; băm tại nguồn mặc định | đã kiểm (PRIV-02, 03, 04); PRIV-01: chưa có test riêng |
| Quan sát (OBS) | Có hiểu được điều đã xảy ra? | Một vết ghi mỗi phiên; độ trễ từng chặng; tỷ lệ System 1/2 | đã kiểm |
| Tương thích (COMP) | Có mở và thay được? | Lược đồ mở qua RFC; provider thay được; Python 3.11+ | một phần (ARM64 chưa) |

## 2. An ninh — NFR-SEC

| NFR | Chiến thuật | Bằng chứng | Trạng thái |
|:---|:---|:---|:---|
| SEC-01 Không đường tắt tới actuator | `c.do()` là đường duy nhất; token dùng một lần; HAL mặc định từ chối; gọi thẳng `@action` ⇒ `NE1001` | Bảng đường tắt ở `docs/spec/threat_model.md` §2, mỗi dòng một test; `tests_linux/test_gpio_sim.py` chứng minh line kernel không đổi khi bị chặn | đã kiểm; chưa có kiểm thử xâm nhập |
| SEC-02, 03 Secure Boot, mã hoá flash, TPM, công tắc micro | — | TSK-S6-05, TSK-W2-03 (trạng thái: roadmap) | chưa |
| SEC-04, 05 mTLS thiết bị ↔ cloud, chứng chỉ riêng mỗi thiết bị | — | Gắn với Fleet OS (I9); mTLS hoặc PSK giữa Pi và node được quy hoạch riêng (TSK-W2-01, I14, không cần Fleet OS) → [`15`](15-target-architecture.md) §4.3 | chưa |
| SEC-06 Firmware có ký, kiểm trên chip | RSA-3072 kiểm trên mọi ảnh OTA; sai hoặc không ký ⇒ từ chối, xoá khe; mốc nước cao chặn hạ cấp | job `ota-rollback` (pha a–g), `test_c_ota_policy.py` | một phần — trên QEMU; thiếu Secure Boot, eFuse |
| SEC-07 Sandbox mã bên thứ ba giới hạn quyền truy cập chân actuator nhạy cảm (P0 v1.1, PRD §9.4) | Sandbox phân quyền của Registry (TSK-K3-05, → [`15`](15-target-architecture.md) §3.2) | — | chưa |
| SEC-08 TLS tới nhà cung cấp, ghi nhà cung cấp vào vết ghi | Tên nhà cung cấp và model trong `system_one_call`, `system_two_call`; không ghi prompt, không ghi khoá | `test_providers.py::test_each_model_call_is_traced_without_prompt_or_key` | một phần — TLS 1.3 chưa có test |
| SEC-09 MCP chỉ stdio; LLM và client MCP không tin cậy | `dispatch()`: kiểm schema, `call_source` do runtime gán, không công cụ xác nhận | Bảng §2b của threat model; corpus `fixtures/tool_calls/` | đã kiểm |

## 3. Độ tin cậy — NFR-REL

| NFR | Chiến thuật | Bằng chứng | Trạng thái |
|:---|:---|:---|:---|
| REL-01 OTA ở quy mô đội | Cập nhật A/B, xác nhận sau self-test, rollback | job `ota-rollback` trên QEMU; quy mô cần Fleet OS | chưa (tiền đề trên QEMU) |
| REL-02 Mặc định khi suy giảm là chặn | `budget.fail` mặc định `closed`; `fail: open` không kế thừa, vẫn chặn trên "không" đã biết; bộ ngắt mạch chỉ định tuyến | Ma trận A4: `test_fail_closed.py`; `test_safety_regressions.py` | đã kiểm |
| REL-03 Chạy hằng đêm trên bo mạch thật | Workflow `nightly-hardware.yml`; job `memory-spike` cần runner có Box-3 và **nói rõ là bỏ qua** khi không có | Chưa có runner | chưa |
| REL-04 Vết ghi cũ vẫn phát lại được sau nâng cấp nhỏ | Vỏ `trace.v1` đóng băng; ba vết ghi chuẩn mực đóng băng; firmware từ chối (không so) vết ghi cũ hơn nó | `test_golden.py`, `test_trace_vectors.py` | một phần — chưa có bản phát hành nhỏ nào để so chéo |

## 4. Tài nguyên — NFR-RES

| NFR | Chiến thuật | Bằng chứng | Trạng thái |
|:---|:---|:---|:---|
| RES-01 Ổn định 24 giờ trên bo mạch | Không cấp phát trên đường âm thanh (RB-1…RB-4, `docs/spec/hal_mcu_review.md`) | TSK-S6-06 (trạng thái: roadmap) | chưa |
| RES-02 SRAM, PSRAM còn trống (Q-3) | Walker, sổ token, bộ vết ghi không dùng RAM tĩnh; trạng thái do ứng dụng cấp phát | jobs `firmware-size`, `firmware-qemu`; số đo ở `memory_spike_report.md` §4.1 | một phần — sàn tĩnh và heap QEMU; PSRAM chưa đo |
| RES-03 Kích thước firmware ≤ khe A/B | Cây nhị phân thay JSON; không CEL trên chip | jobs `firmware-size`, `ota-rollback`, `nightly-hardware` | đã kiểm |
| RES-04 Chức năng an toàn chạy khi mất mạng | Ngữ pháp lệnh cục bộ là fallback của mọi model; không có fallback ⇒ `gate_unreachable` | `test_fail_closed.py`, `test_offline_fallback.py`, vết ghi `network_offline.json` | đã kiểm trên `sim`/`linux`; `esp32s3` chưa (TSK-S5-07) |

## 5. Hiệu năng — NFR-PERF

Kiến trúc đo được mọi ngưỡng hiệu năng — mỗi lượt ghi `turn_latency` với các chặng `perception`,
`system_two`, `gate`, `action`, `other`, và mỗi lời gọi model ghi độ trễ, token, chi phí. Nhưng **chưa
ngưỡng độ trễ hay chi phí nào được đo** so với PRD §9.1, vì chưa có phiên thoại thời gian thực và CI
không gọi model thật.

| NFR | Chiến thuật | Bằng chứng hôm nay |
|:---|:---|:---|
| PERF-01, 07 Độ trễ thoại đầu cuối | Luồng thoại tách chặng; STT/TTS chạy ở cloud hoặc host | Công cụ đo: `test_turn_latency.py`; ngưỡng: chưa đo |
| PERF-02 Lượng giá gate cục bộ | Cây quyết định biên dịch trước; duyệt O(số nút) | Ngân sách được cưỡng chế và fail-closed (`test_gate_engine.py`); P95: chưa đo |
| PERF-03, 04 Lượng giá cần dữ kiện cloud; quyết định có cấu trúc | Hạn chót model bị giới hạn bởi ngân sách còn lại của gate | `test_system_one_cloud.py`; P95: chưa đo |
| PERF-05 Tiết kiệm nhờ định tuyến hai model | Ngữ pháp và System 1 trả lời trước, System 2 chỉ khi cần | Tỷ lệ và chi phí mỗi phiên trong `session_summary`; mức tiết kiệm: chưa đo |
| PERF-06 Thời gian chạy Action CI mẫu | Test của agent chạy trên `sim`, không mạng | Test mẫu chạy; chưa có khẳng định thời gian |

## 6. Riêng tư — NFR-PRIV

| NFR | Chiến thuật | Bằng chứng | Trạng thái |
|:---|:---|:---|:---|
| PRIV-01 Âm thanh không lưu mặc định | Sự kiện âm thanh chỉ mang siêu dữ liệu (năng lượng, thời lượng, digest) | Không có trường PCM nào trong mã | theo thiết kế, chưa có test riêng |
| PRIV-02 Cloud-first, người dùng chọn nhà cung cấp | Mọi model sau giao thức; adapter tự viết | `test_providers.py` | đã kiểm |
| PRIV-03 Vết ghi mặc định lưu quyết định, không lưu dữ liệu thô | Mặc định băm tại nguồn; `--raw` là cách bật tường minh giữ nguyên văn, vết ghi đó mang `metadata.anonymized = false` | `test_recorder.py::test_the_default_hashes_raw_text_and_keeps_every_decision`, `test_cli_run.py::test_trace_out_writes_a_valid_trace_of_the_session`, `test_uart_trace.py::test_anonymize_hashes_raw_text_at_the_source` | đã kiểm |
| PRIV-04 Băm tại nguồn không phá vỡ khả năng replay | `TraceRecorder` băm `text`, `utterance`, `transcript` | `test_recorder.py` (kể cả `test_record_replay_matches_between_the_default_and_a_raw_trace`), `test_voice_speech.py`, `test_uart_trace.py` | đã kiểm |

## 7. Quan sát — NFR-OBS

| NFR | Chiến thuật | Bằng chứng | Trạng thái |
|:---|:---|:---|:---|
| OBS-01 Một phiên, một vết ghi đầy đủ | `EventLog` của phiên; `session_summary` tính khi xuất, đúng một lần | `test_turn_latency.py`, bước CI "ba vết ghi chuẩn mực hợp lệ" | đã kiểm |
| OBS-02 Tỷ lệ System 1/2, chi phí, mọi kết quả gate | `turn_latency.path`, `system_two_usage` | `test_turn_latency.py` | đã kiểm |
| OBS-03 Độ trễ từng chặng so được với `p95_latency_ms` | `TurnMeter.stage` lồng nhau không đếm hai lần | `test_turn_latency.py` | đã kiểm |

## 8. Tương thích — NFR-COMP

| NFR | Chiến thuật | Bằng chứng | Trạng thái |
|:---|:---|:---|:---|
| COMP-01 Giấy phép lõi và chuẩn (Q-45) | Mã PolyForm Noncommercial; `schemas/`, `docs/spec/`, `fixtures/compliance/` Apache-2.0 | `test_packaging.py` | đã kiểm |
| COMP-02 Không khoá chức năng an toàn sau tài khoản trả phí | Lõi an toàn nằm trọn trong gói | Rà ranh giới, không có test | theo thiết kế |
| COMP-03 Mọi dịch vụ cloud qua giao diện thay được | `models/providers/`, `perception/providers/` | `test_providers.py` | đã kiểm |
| COMP-04 Lược đồ mở, quản trị qua RFC | `docs/rfc/`, `digests.lock`, job `frozen-artifacts` | `test_schemas.py`, `test_digests_lock.py` | đã kiểm; URL công khai ở I6 |
| COMP-05 Python 3.11+ | `requires-python >= 3.11` | ma trận CI 3.11 / 3.12 / 3.13 | đã kiểm |
| COMP-06 `linux` trên ARM64 và x86-64 | — | Mọi job chạy x86-64; chưa có job ARM64 | một phần |

## 9. Tiêu chí nghiệm thu v1.0 (A1–A12)

| # | Tiêu chí | NFR liên quan | Bằng chứng hôm nay |
|:---:|:---|:---|:---|
| A1 | TTFV dưới 10 phút | — | chưa đo; chỉ có proxy (`test_readme_quickstart.py`, `wheel-smoke`) |
| A2 | `verify` 100 % trên ba target | REL-03, COMP-05/06 | `sim` + `linux` đạt; `esp32s3` trên QEMU, mức quyết định |
| A3 | Không đường tắt tới actuator | SEC-01, 09 | bảng test của threat model; chưa kiểm thử xâm nhập |
| A4 | Fail-closed 100 % | RES-04, REL-02 | `test_fail_closed.py`, `test_safety_regressions.py` |
| A5 | Kế thừa gate an toàn | — | corpus `fixtures/gates/invalid/`, `gate lint` trong CI |
| A6 | Ổn định 24 giờ trên chip | RES-01/02/03 | chưa đo |
| A7 | Vết ghi hợp lệ 100 % | REL-04, PRIV, OBS | thẩm định trong CI, cả vết ghi UART |
| A8 | Tài liệu, ba mẫu chạy được | — | ba mẫu có test; chưa kiểm trên máy sạch bởi bên thứ ba |
| A9 | Lược đồ công khai kèm bộ tuân thủ | COMP-01→04 | `$id` đã khẳng định; `fixtures/compliance/` hôm nay chỉ có `voice/`; URL công khai ở I6 |
| A10 | Đủ nguyên thủy mở rộng trên ba target (FR-HAL-08, Q-53) | REL-03, COMP-05/06 | chưa bắt đầu; cần RFC-0007, RFC-0009 → RFC-0013 (I2a, I3a) |
| A11 | Dựng bằng hội thoại có hợp đồng (NeuroBrain, Q-55) | SEC-01 | chưa bắt đầu (I4a, I5a) |
| A12 | Kit mẫu dựng được trong một ngày (Q-52) | — | chưa đo (I2b) |
