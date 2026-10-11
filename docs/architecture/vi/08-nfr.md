# 08 · Yêu cầu phi chức năng → chiến thuật → bằng chứng

> **Phạm vi:** mỗi nhóm NFR của PRD §9 được kiến trúc đáp ứng bằng chiến thuật nào, và bằng chứng nằm
> ở đâu hôm nay. **Nguồn:** PRD §9 (yêu cầu, ngưỡng), PRD §11.1 (A1–A13), test trong `python/tests/`,
> job CI trong `.github/workflows/` (danh sách duy nhất: `CHANGELOG.md` §2.5).

Nhãn bằng chứng: **đã kiểm** — có test hoặc job CI chạy mỗi PR · **một phần** — có công cụ đo hoặc
kiểm một phần · **chưa đo** — chưa có bằng chứng · **`planned · Q-72`** — yêu cầu mới của [Q-72](../../../roadmap/neuroedge-prd.md#15-sổ-quyết-định) cho
agent vận hành, kênh chat và NeuroEdge Blueprint (I2d, I2e); chưa có mã, nên chưa có bằng chứng. Các
dòng này chưa mang mã số NFR: mã cấp ở PRD §9, nơi duy nhất ghi ngưỡng.

## 1. Tổng quan

| Nhóm | Câu hỏi | Chiến thuật kiến trúc chính | Trạng thái |
|:---|:---|:---|:---|
| An ninh (SEC) | Có đường nào tới chân mà không qua gate? | Một đường duy nhất; HAL không sổ token thì từ chối; bên gọi không tin cậy | đã kiểm (SEC-01, 09); thiết bị: chưa |
| Độ tin cậy (REL) | Khi một phần hỏng thì sao? | Fail-closed mặc định; bộ ngắt mạch; vết ghi chuẩn mực đóng băng | đã kiểm (REL-02); REL-01, 03: chưa |
| Tài nguyên (RES) | Có vừa chip không? Có chạy khi mất mạng? | `NETR` nhị phân, walker không cấp phát; fallback cục bộ | một phần |
| Hiệu năng (PERF) | Có đủ nhanh? | Ngân sách thời gian mỗi gate, cưỡng chế fail-closed; đo từng chặng | công cụ có; ngưỡng **chưa đo** |
| Riêng tư (PRIV) | Dữ liệu nào được lưu? | Không lưu âm thanh; băm tại nguồn mặc định | đã kiểm (PRIV-02, 03, 04); PRIV-01: chưa có test riêng |
| Quan sát (OBS) | Có hiểu được điều đã xảy ra? | Một vết ghi mỗi phiên (runtime 24/7 của Q-72: một chuỗi đoạn, mỗi đoạn replay được — `planned`, I2d); độ trễ từng chặng; tỷ lệ System 1/2 | đã kiểm |
| Tương thích (COMP) | Có mở và thay được? | Lược đồ mở qua RFC; provider thay được; Python 3.11+ | một phần (ARM64 chưa) |
| Agent vận hành, chat, NeuroEdge Blueprint (`planned · Q-72`) | Chạy 24/7 có an toàn không, tốn bao nhiêu, dữ liệu có rò không? | Hai tiến trình (runtime tin cậy, LLM worker không tin cậy); phản xạ không cần LLM; cửa ra egress; bản ghi duyệt; vết ghi theo đoạn | chưa — I2d, I2e |

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
| SEC-10 Plugin của bên thứ ba (Q-67) | Plugin chạy trong tiến trình là mã người vận hành tin (`docs/spec/threat_model.md` §3): chỉ nạp khi được bật rõ; nguồn gốc (gói, phiên bản, băm tệp) in ra và ghi vào vết ghi; không API nào của `neuroedge.sdk` trao handle phần cứng cho bridge hay fact source (FR-EXT-02, FR-EXT-03) | Bộ nạp plugin và bộ test tuân thủ theo loại (TSK-I2c-11, TSK-I2c-12; RFC-0016 còn là bản nháp) | chưa — I2c |
| Chống rò rỉ dữ liệu (`planned · Q-72`, I2d) | Runtime là nơi quyết định LLM worker *thấy* gì và chỉ gửi ra đích người dùng đã khai (nhà cung cấp LLM, kênh chat, relay, webhook); mạng của LLM worker bị chặn ở mức hệ điều hành chỉ tới endpoint provider đã khai; gửi tới đích không khai bị chặn và ghi vết. Mục tiêu là chống hack, prompt injection, đánh cắp — không hạn chế luồng người dùng tự dựng. Rủi ro còn lại: worker bị lừa vẫn gửi được dữ liệu đã cho phép tới đích đã cho phép | Hợp đồng: [`07`](07-data-contracts.md) §12.3; test khi làm mã | chưa |
| Lời duyệt qua chat (`planned · Q-72`, I2d, chờ RFC nguồn `chat:<id>`) | Bản ghi duyệt `{id, nonce, hạn, digest thay đổi, bản duyệt ≤ 5 dòng}`; runtime kiểm người gửi đã ghép đôi tại chỗ, không phải nhóm, nonce chưa dùng, còn hạn theo đồng hồ đơn điệu, digest khớp; LLM worker không bao giờ duyệt; lời duyệt không đi qua relay. Thu hồi, hạn ghép đôi, trần lời duyệt: hoãn (`TODOS.md` #62) | Luồng: [`06`](06-runtime-flows.md) §11.4 | chưa |
| Key BYOK và token bot (`planned · Q-72`, I2d) | Key LLM của người dùng chỉ nằm trong tiến trình LLM worker; token bot chat chỉ trong runtime; không cái nào vào vết ghi; tiến trình giữ HAL không giữ key LLM | — | chưa |
| Cài NeuroEdge Blueprint kiểm digest (`planned · Q-72`, I2e) | Digest phủ toàn gói (kit, firmware, hợp đồng mẫu, bộ phát hiện, vết ghi bằng chứng), kiểm khi cài; lệch ⇒ từ chối với lỗi ba phần; gói chỉ khai báo; `safe_state` khác `off` chỉ từ `board.v1` có khoá liên động; bằng chứng ghi "chưa ký" | Hợp đồng: [`07`](07-data-contracts.md) §12.2 | chưa |

## 3. Độ tin cậy — NFR-REL

| NFR | Chiến thuật | Bằng chứng | Trạng thái |
|:---|:---|:---|:---|
| REL-01 OTA ở quy mô đội | Cập nhật A/B, xác nhận sau self-test, rollback | job `ota-rollback` trên QEMU; quy mô cần Fleet OS | chưa (tiền đề trên QEMU) |
| REL-02 Mặc định khi suy giảm là chặn | `budget.fail` mặc định `closed`; `fail: open` không kế thừa, vẫn chặn trên "không" đã biết; bộ ngắt mạch chỉ định tuyến. *Sẽ đổi theo Q-72 (`planned`, chờ RFC an toàn có điều kiện):* với **lệnh**, vẫn "không chắc thì chặn"; thêm: cơ cấu suy giảm thì trở về `safe_state` đã khai trong `board.v1` (mặc định `off`, nên mọi profile hiện có giữ nguyên hành vi) | Ma trận A4: `test_fail_closed.py`; `test_safety_regressions.py` | đã kiểm (phần lệnh); phần `safe_state`: chưa |
| REL-03 Chạy hằng đêm trên bo mạch thật | Workflow `nightly-hardware.yml`; job `memory-spike` cần runner có Box-3 và **nói rõ là bỏ qua** khi không có | Chưa có runner | chưa |
| REL-04 Vết ghi cũ vẫn phát lại được sau nâng cấp nhỏ | Vỏ `trace.v1` đóng băng; ba vết ghi chuẩn mực đóng băng; firmware từ chối (không so) vết ghi cũ hơn nó | `test_golden.py`, `test_trace_vectors.py` | một phần — chưa có bản phát hành nhỏ nào để so chéo |
| Runtime sống 24/7 (`planned · Q-72`, I2d) | Runtime chạy dưới systemd, tự khởi động lại; LLM worker chết hay treo thì runtime vẫn chạy phản xạ, bộ phát hiện, cảnh báo mẫu cứng và khởi động lại worker; thời lượng, hạn duyệt, watchdog dùng đồng hồ đơn điệu | Nhánh lỗi: [`06`](06-runtime-flows.md) §11.6 | chưa |
| Phản xạ khi mất mạng hoặc mất LLM (`planned · Q-72`, I2d) | Trình biên dịch nhiệm vụ hạ điều khoản xuống tầng thấp nhất (phản xạ trên MCU có `ne_gate`, kỹ năng trên host); mất mạng, mất LLM hay relay sập không đụng tới phần an toàn; kênh chat sập ⇒ hàng đợi có hạn + cảnh báo tại chỗ trên UI. Dữ kiện giờ tường `unsynced` ⇒ điều khoản khung giờ coi là thiếu dữ kiện (fail-closed) | Kiểm trên giả lập G1 `sim`, G2 `linux` trên gpio-sim, G3 firmware ESP32 (Q-72) | chưa |

## 4. Tài nguyên — NFR-RES

| NFR | Chiến thuật | Bằng chứng | Trạng thái |
|:---|:---|:---|:---|
| RES-01 Ổn định 24 giờ trên bo mạch | Không cấp phát trên đường âm thanh (RB-1…RB-4, `docs/spec/hal_mcu_review.md`) | TSK-S6-06 (trạng thái: roadmap) | chưa |
| RES-02 SRAM, PSRAM còn trống (Q-3) | Walker, sổ token, bộ vết ghi không dùng RAM tĩnh; trạng thái do ứng dụng cấp phát | jobs `firmware-size`, `firmware-qemu`; số đo ở `memory_spike_report.md` §4.1 | một phần — sàn tĩnh và heap QEMU; PSRAM chưa đo |
| RES-03 Kích thước firmware ≤ khe A/B | Cây nhị phân thay JSON; không CEL trên chip | jobs `firmware-size`, `ota-rollback`, `nightly-hardware` | đã kiểm |
| RES-04 Chức năng an toàn chạy khi mất mạng | Ngữ pháp lệnh cục bộ là fallback của mọi model; không có fallback ⇒ `gate_unreachable` | `test_fail_closed.py`, `test_offline_fallback.py`, vết ghi `network_offline.json` | đã kiểm trên `sim`/`linux`; `esp32s3` chưa (TSK-S5-07) |
| Trần chi phí LLM (`planned · Q-72`, I2d) | `llm_budget` khai trong hợp đồng nhiệm vụ; bộ phát hiện tất định chạy trước, chỉ gọi LLM khi có sự kiện; hết trần ⇒ phản xạ và cảnh báo mẫu cứng vẫn chạy, chỉ mất phần phân tích | — | chưa |
| Ngân sách tin nhắn (`planned · Q-72`, I2d) | Tin báo chủ động của agent được gom và giới hạn theo một ngân sách tin nhắn khai được, để kênh chat không thành nguồn nhiễu; chi tiết thuộc FR-AGT (PRD) | — | chưa |

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
| OBS-01 Một phiên, một vết ghi đầy đủ | `EventLog` của phiên; `session_summary` tính khi xuất, đúng một lần. *Sẽ đổi theo Q-72 (`planned`, chờ RFC `trace.v1`):* runtime 24/7 ghi một chuỗi đoạn, mỗi đoạn replay được ([`07`](07-data-contracts.md) §7) | `test_turn_latency.py`, bước CI "ba vết ghi chuẩn mực hợp lệ" | đã kiểm (phiên lệnh); chuỗi đoạn: chưa |
| OBS-02 Tỷ lệ System 1/2, chi phí, mọi kết quả gate | `turn_latency.path`, `system_two_usage` | `test_turn_latency.py` | đã kiểm |
| OBS-03 Độ trễ từng chặng so được với `p95_latency_ms` | `TurnMeter.stage` lồng nhau không đếm hai lần | `test_turn_latency.py` | đã kiểm |
| Hạn giữ và nhịp ghi vết ghi trên máy nhà (`planned · Q-72`, I2d) | Giữ 30 ngày tại chỗ; đoạn cũ hơn nén rồi xoá, hoặc xuất qua relay đã mã hoá phía máy nhà; flush theo thời gian (khoảng 10 giây, khai được) và **ngay** khi có phán quyết chặn hay lời duyệt; mất điện mất tối đa phần đuôi sự kiện thường, `replay` báo đoạn cụt | Đo cỡ vết ghi 30 ngày trên G1 `sim` (tua nhanh) rồi ghi số vào PRD §9 | chưa đo |

## 8. Tương thích — NFR-COMP

| NFR | Chiến thuật | Bằng chứng | Trạng thái |
|:---|:---|:---|:---|
| COMP-01 Giấy phép lõi và chuẩn (Q-45) | Mã PolyForm Noncommercial; `schemas/`, `docs/spec/`, `fixtures/compliance/` Apache-2.0 | `test_packaging.py` | đã kiểm |
| COMP-02 Không khoá chức năng an toàn sau tài khoản trả phí | Lõi an toàn nằm trọn trong gói | Rà ranh giới, không có test | theo thiết kế |
| COMP-03 Mọi dịch vụ cloud qua giao diện thay được | `models/providers/`, `perception/providers/` | `test_providers.py` | đã kiểm |
| COMP-04 Lược đồ mở, quản trị qua RFC | `docs/rfc/`, `digests.lock`, job `frozen-artifacts` | `test_schemas.py`, `test_digests_lock.py` | đã kiểm; URL công khai ở I6 |
| COMP-05 Python 3.11+ | `requires-python >= 3.11` | ma trận CI 3.11 / 3.12 / 3.13 | đã kiểm |
| COMP-06 `linux` trên ARM64 và x86-64 | — | Mọi job chạy x86-64; chưa có job ARM64 | một phần |

## 9. Tiêu chí nghiệm thu v1.0 (A1–A13)

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
| A9 | Lược đồ công khai kèm bộ tuân thủ | COMP-01→04 | một phần — bảy lược đồ trong `schemas/`, `$id` đã khẳng định (`test_schemas.py`); corpus tuân thủ có sẵn: `fixtures/compliance/voice/` (thoại), `fixtures/tool_calls/` (Gated Tool Profile) và `fixtures/contracts/` (bo, lỗi, tool-call, tool-result; `test_contracts.py`), theo Apache-2.0 (Q-67); chưa phục vụ ở URL công khai (TSK-I6-02, I6) và chưa có bằng chứng bên thứ ba đã chạy thử |
| A10 | Đủ nguyên thủy mở rộng trên ba target (FR-HAL-08, Q-53) | REL-03, COMP-05/06 | một phần — RFC-0007, RFC-0009 → RFC-0013 đã chấp thuận; `digital.in`, I2C chỉ đọc, `analog.in`, thị giác và phong bì xong trên `sim` và `linux` (job `linux-hal`), PWM và `motion.*` xong trên `sim` (I2a); `verify` chưa phát lại agent `fan-pwm` và `rover`; `esp32s3` chưa bắt đầu (I3a) |
| A11 | Dựng bằng hội thoại có hợp đồng (NeuroEdge Lab qua MCP, Q-55, Q-71; đo trên hai client) | SEC-01 | chưa bắt đầu (I4a, I5a) |
| A12 | Kit mẫu dựng được trong một ngày (Q-52) | — | một phần — năm kit có BOM, sơ đồ, vết golden và test trên `sim`, `linux` (I2b); chưa dựng trên phần cứng thật (`TODOS.md` #59), TTFV chưa đo trên người; A12 đo ở I7 |
| A13 | Nền tảng mở: bên thứ ba tự nối một hệ sinh thái mới ≤ 1 ngày, che một MCP server ≤ 3 lệnh (Q-67) | SEC-10 | chưa bắt đầu — I2c; sẽ đo bằng bài kiểm `neuroedge-muse` (TSK-I2c-17) và test CI cài plugin ngoài kho |
