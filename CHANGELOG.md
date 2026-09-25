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
> roadmap kể *còn gì phải xây*. Thứ tự ưu tiên khi lệch nhau: §3.1.

---

## 1. Nhật ký phiên bản

Mỗi task xong thêm hoặc sửa **một** mục trong `[Chưa phát hành]`, theo
`CONTRIBUTING.md` §8.2 bước 3. Khi phát hành, đổi tiêu đề thành số phiên bản và ngày
(`docs/release.md`).

Gói chưa phát hành phiên bản nào ra ngoài; trước khi công khai chỉ có tag nội bộ (Q-39), và phiên bản đầu tiên trên PyPI sẽ là `0.6.0` ở I6. Các mục
**Mốc …** dưới `[Chưa phát hành]` là mốc tài liệu của Giai đoạn 1, không phải phiên
bản gói.

### [Chưa phát hành]

#### Đã thêm

- **Q-39 → Q-44 — roadmap theo increment (2026-09-25).** Một roadmap, thời gian đo bằng increment `I0…`, không phát hành
  ra ngoài tới khi công khai ở I6 (demo thoại trên `sim`, `linux`, Box-3), thêm một kỹ sư nhúng (Q-39); mở rộng sau Beta
  (Q-40); v1.1 mở trên B1 và B2 (Q-41); C6 thành chỉ số theo dõi (Q-42); G-* neo theo increment (Q-43); bỏ bậc cắt 5 (Q-44).
- **Q-6, Q-36 → Q-38 — CPO chốt 4 quyết định (2026-09-25).** Lưu vết Fleet Standard 90 ngày, Enterprise 3 năm (Q-6); wire
  node Zenoh-pico, spike W3-1 là phép thử loại (Q-36); token `motion.*` thuê có hạn (Q-37); chứng nhận an toàn OUT tạm thời,
  miễn trừ ở `README.md` và `threat_model.md` §3b (Q-38, `TODOS.md` #40). Q-5 hoãn tới trước Tháng 4. PRD §14/§15, roadmap §10.
- **Q-11, Q-31 → Q-35 — CPO chốt 9 quyết định (2026-09-25).** Hawkbit duyệt, EMQX thay (Q-11); tagline NeuroBrain bỏ
  "Copilot" (Q-31); nhận hướng robot phân tầng sau Beta (Q-32), RP2350 do đội lõi port (Q-33), ROS 2/Nav2 gate mọi lệnh
  tốc độ (Q-34), trạng thái an toàn theo từng cơ cấu (Q-35). PRD §14/§15, roadmap §10, phase 2; `TODOS.md` #16 đã đóng.
- **Dashboard sản phẩm cho CPO.** `docs/business/cpo-dashboard.html` — một trang tự chứa (mở thẳng bằng trình duyệt):
  tiến độ sprint, mốc, việc chờ người, quyết định còn mở, TODOS, thay đổi gần đây; sinh từ roadmap/TODOS/PRD/CHANGELOG
  bằng `python3 scripts/gen_cpo_dashboard.py`. Kiểm: `pytest tests/test_cpo_dashboard.py`.
- **Mở rộng cho robot phân tầng FOFOCA (bản nháp, chờ `Q-N`).** `draft-ke-hoach-mo-rong-robot-fofoca.md` (chặng W0–W4:
  nguyên thủy HAL mới, multi-node với gate từng node qua black channel) + `draft-rfc-node-giao-thuc-dieu-phoi.md` (RFC chưa
  cấp số); điểm lệch với đặc tả và phạm vi hiện hành chờ quyết ở Phụ lục C. Chỉ tài liệu, chưa có mã.
- **TSK-S4-09 — `verify --targets esp32s3` chạy trên QEMU; vết ghi firmware qua UART.** Firmware ghi sự kiện thành dòng
  `NE1 ` (`ne_trace`) và replay 3 vết ghi chuẩn mực bằng walker C (`ne_decide`, có đường suy giảm) + sổ token C; `record`
  / `verify --port` đọc tệp log, `tcp://` hoặc serial (`neuroedge[serial]`); job `uart-trace`. Đặc tả `simulation_coverage.md`
  §4. Kiểm: `pytest tests/test_c_trace.py tests/test_uart_trace.py tests/test_trace_vectors.py`. (FR-CI-01, FR-CLI-03/04)
- **TSK-S2-07 — đặc tả chuẩn tắc máy trạng thái hội thoại.** `docs/spec/voice_fsm.md`: năm trạng thái, bảng chuyển
  trạng thái, hợp đồng thu hồi lệnh (chỉ lệnh chưa giao tới chân, ≤ 20 ms, đóng token; lệnh đã giao chạy hết), sự kiện,
  kịch bản tuân thủ cho TSK-S3-10. Chỉ tài liệu. (FR-PER-02→05)
- **Giai đoạn 1.5 — kế hoạch NeuroBrain (bản nháp, chờ `Q-N`).** `neuroedge-roadmap-phase1-5.md`: khối N0–N7,
  bring-up phần cứng có gate, song song Khối 1b tới Developer Beta; wireframe Lab Monitor ở `wireframe/`. Chỉ tài liệu,
  chưa có mã. Quyết định chuyển vào PRD §15 ở TSK-N0-01.
- **TSK-S3-14 — workflow phát hành PyPI, chưa đẩy lên index nào.** `release-pypi.yml`: sdist → wheel từ sdist →
  `twine check --strict` → smoke trên đúng wheel đó → trusted publishing (OIDC), chỉ với tag **và** `PUBLISH_ENABLED`.
  `LICENSE` (MIT) nằm trong wheel/sdist. Go-live: `docs/release.md`.
- **TSK-S3-20 — `README.md` gốc là trang PyPI.** Một màn hình, link tuyệt đối, ba lệnh `pip install` → `new --template
  home-voice` → `mcp desktop-config --write`; `hatch_build.py` đọc nó vào metadata. Kiểm: `pytest
  tests/test_readme_quickstart.py tests/test_packaging.py` · `scripts/wheel_smoke.sh`. (FR-DX-02)
- **TSK-S3-24 — corpus tuân thủ Gated Tool Profile.** `fixtures/tool_calls/{valid,invalid}/` + `expected_results.yaml`,
  chạy qua `dispatch()` thật và qua client MCP; `verify` chạy cả corpus; mỗi tool MCP khai `outputSchema`. Agent mẫu
  `fixtures/agents/driveway/`. Kiểm: `pytest tests/test_tool_corpus.py`. (FR-MDL-10, FR-ACE-09)
- **TSK-S3-19 — `neuroedge verify` quét được 0 artifact thì thất bại.** Loại artifact nào bằng 0 ⇒ `VerificationError`
  (NE4004), mã 1. Kiểm: `pytest tests/test_cli.py -k verify`. (FR-CLI-03)
- **TSK-S3-16 — `digests.lock` khoá gate chuẩn mực.** Digest JCS của YAML đã parse; `scripts/check_digests.py --check`
  trong CI; tệp mới ⇒ `--update`, đổi hoặc xoá ⇒ RFC (`CONTRIBUTING.md` §3). Kiểm: `pytest tests/test_digests_lock.py`.
- **TSK-S2-11 — System 2 trên model thật qua LiteLLM (extra `neuroedge[cloud]`, Q-10, Q-11, Q-12).** `[system_two]` trong
  `agent.toml`; key chỉ qua biến môi trường; thiếu key, mất mạng, hết giờ ⇒ câu offline và lệnh cục bộ. Mỗi lượt ghi
  `system_two_call`. Kiểm: `pytest tests/test_providers.py tests/test_offline_fallback.py` · job `cloud-extra`.
- **TSK-S3-27 — `neuroedge mcp serve --ui` và `neuroedge mcp desktop-config`.** Một tiến trình phục vụ MCP qua stdio và
  trang `sim` của cùng phiên; `desktop-config --write` ghi mục Claude Desktop bằng đường dẫn tuyệt đối. Đã chạy trên
  Desktop thật. Kiểm: `pytest tests/test_mcp_serve_ui.py tests/test_mcp_desktop.py`. (FR-CLI-12)
- **TSK-S4-07 — walker C99 cho bố cục `NETR` v1 (RFC-0003, Q-23).** `build` ghi `<gate>.netree` + `.netree.h`; walker
  `targets/esp32s3/components/ne_gate/` khớp engine host trên mọi gate, mỗi PR, dưới ASan/UBSan. Kiểm: `pytest
  tests/test_c_walker.py`.
- **TSK-S4-02 + TSK-S4-08 — sổ token C và self-test gate trên QEMU.** `ne_token.c` cùng hợp đồng với `TokenLedger`;
  firmware in `NE_SELFTEST PASS` trước mạng; workflow `firmware-qemu` boot nó trên Espressif QEMU. Kiểm: `pytest
  tests/test_c_token.py`.
- **TSK-S3-26 — xác nhận `on_block: ask` (Q-26, RFC-0006).** `on_block.confirms` khai tiêu chí người trên thiết bị được
  thay; "có" làm gate lượng giá lại. REPL `:confirm`/`:decline`, UI `POST /confirm`. Kiểm: `pytest
  tests/test_tool_confirm.py`. (FR-ACE-10)
- **TSK-S3-25 — gate chặn theo giá trị tham số (RFC-0005, Q-25).** Khối `arguments:` trong gate ⇒ `BLOCK
  argument_out_of_range` trước mọi dữ kiện; con chỉ thu hẹp; giới hạn đi vào `inputSchema`. Kiểm: `pytest
  tests/test_gate_arguments.py`. (FR-ACE-08)
- **TSK-S3-28 — System 2 làm MCP host (Q-27).** Tool thiết bị qua MCP server của chính agent (vẫn qua gate); MCP server
  ngoài ở `[mcp.servers]` chỉ lấy thông tin; `neuroedge mcp tools --external`. Kiểm: `pytest tests/test_mcp_host.py`.
  (FR-MDL-11, FR-MDL-12)
- **Q-24 — hành động là tool call; Gated Tool Profile v0.** Mỗi `@action` là một tool; ngữ pháp cục bộ, System 2 và MCP
  gửi cùng `ToolCall` → kiểm schema → `c.do()` → gate; `mcp tools`, `mcp serve`, extra `neuroedge[mcp]`. Đặc tả:
  `docs/spec/tool_calling.md`. Kiểm: `pytest tests/test_tools.py`. (FR-MDL-10, FR-CLI-12)
- **Q-28 — mốc giao FR-GW; TSK-S5-10 nhận `run --target linux`.** FR-GW-01/03 ở dạng tối thiểu trong v1.0 (đúng như
  TSK-S2-11 đã giao), phần còn lại v1.1 (K2-01→03); phiên tương tác linux có chủ ở Sprint 5. PRD §15, roadmap §5.2.
  (FR-GW-01, FR-GW-03, FR-CLI-02)
- **FR-DX-05 — mẫu `home-voice`.** Trợ lý giọng nói trong nhà: hỏi đáp knowledge base, tin tức qua System 2, đèn qua gate
  có cảm biến; `neuroedge new --template home-voice`. Kiểm: `pytest tests/test_home_voice.py`.
- **TSK-S3-17 — wheel tự chạy được.** `neuroedge/_data/` mang `boards/`, `schemas/`, `gates/`, fixture, cả khi build từ
  sdist; `paths.py` báo lỗi thay vì đoán. Kiểm: `pytest tests/test_paths.py` · job `wheel-smoke`. (FR-DX-02)
- **TSK-S2-09 — `neuroedge run --ui`.** Phiên `sim` trực tiếp trên trình duyệt, chỉ 127.0.0.1. `sim/ui.py`. Kiểm:
  `pytest tests/test_sim_ui.py`. (FR-TGT-06)
- **TSK-S3-22 — `neuroedge trace view` + `trace export --format chrome`.** HTML tự chứa có thanh tua; Perfetto cho
  timing. `viz/`. Kiểm: `pytest tests/test_trace_view.py`. (FR-CLI-04)
- **TSK-S3-23 — `sensor.read` và `display` trên `sim`.** `[sim.sensors]`, `[sim.sensor_facts]`, sự kiện `sensor_read` /
  `display_frame`, replay cấp lại số đọc. Kiểm: `pytest tests/test_sim_sensors_display.py`. (FR-TGT-01)
- **Q-21, Q-22 — đặc tả phủ mô phỏng** `docs/spec/simulation_coverage.md`: 5 nguyên thủy × 3 target, công cụ mở từng
  tầng, AEC PipeWire trên `linux` (§6). Task mới TSK-S3-22, S3-23, S4-07 → S4-12, S5-08, S5-09.
- **TSK-S3-01 — `TraceRecorder` + `neuroedge record`.** Ghi phiên ra `trace.v1` đã thẩm định, kèm `gate_facts` để
  replay; `--anonymize` băm chữ thô tại nguồn. Kiểm: `pytest tests/test_recorder.py`. (FR-CI-01, FR-TRC-07)
- **TSK-S3-02 — replay thật trên HAL.** Phán quyết gate và lệnh chân **tính lại** trên `SimHAL`/`LinuxHAL`.
  `testing/player.py`. Kiểm: `pytest tests/test_player.py`. (FR-CI-02)
- **TSK-S3-03 — thư viện assert + `neuroedge test`.** `assert_gate_blocked`, `assert_never_pulsed`… đọc phán quyết và
  chân; `test` thoát 0/1. Kiểm: `pytest tests/test_assertions.py`. (FR-CI-03, FR-CLI-03)
- **TSK-S3-04 — so khớp Golden Reference.** So phán quyết + lệnh chân, bỏ qua timing; lệch ⇒ NE4002, `replay` mã 1.
  Kiểm: `pytest tests/test_golden.py`. (FR-CI-04)
- **TSK-S3-05 — `LinuxHAL` + gpio-sim trong CI; `verify --targets sim,linux` (A2).** Extra `[linux]` (libgpiod v2);
  job `linux-hal`. Kiểm: `pytest tests/test_hal_linux.py` · `tests_linux/`. (FR-TGT-02, Q-16)
- **TSK-S3-18 — `neuroedge gate explain`.** Tiêu chí từ cấp nào, con siết gì, p95 và `on_block` so với cha, cho người
  duyệt (J6). Kiểm: `pytest tests/test_cli_explain.py`. (FR-CLI-05)
- **TSK-S3-07 — `neuroedge new`.** Dự án build được, chạy được trên `sim`, test tự qua; generator Python thuần, không
  `copier`. Kiểm: `pytest tests/test_cli_new.py`. (FR-DX-01)
- **TSK-S3-06 — `neuroedge run --target sim`.** REPL gõ chữ: `commands.toml` → `c.do()` → phán quyết + chân ảo; `-c`
  cho CI, `--trace-out`; `[sim.facts]` không bao giờ suy từ chữ gõ. Kiểm: `pytest tests/test_cli_run.py`. (FR-CLI-02, Q-15)
- **TSK-S2-12 — cây quyết định phía host.** `engine/decision_tree.py`; bảng sự thật cho walker C ở
  `fixtures/decision_trees/`. Kiểm: `pytest tests/test_decision_tree.py`.
- **TSK-S2-03 — Gate Engine trả phán quyết.** `engine/gate.py`: dữ kiện trong ngân sách `p95`, đi cây, `on_block` theo
  Q-17; tái tạo 3 vết ghi chuẩn mực. Kiểm: `pytest tests/test_gate_engine.py`. (FR-GATE-03/04/09)
- **TSK-S2-08 — SystemOne/SystemTwo + ngữ pháp lệnh cố định.** Mất mạng thì hỏi `CommandGrammar` (`commands.toml`);
  không có fallback ⇒ `gate_unreachable`. Kiểm: `pytest tests/test_models.py`. (Q-14, Q-15, FR-MDL-01/02/03)
- **TSK-S2-01 — HAL `sim`.** `SimHAL` phủ 5 nguyên thủy trên `sim-default`; `digital_out` trả
  `PendingCommand.cancel()` (RB-3). Kiểm: `pytest tests/test_hal_sim.py`. (FR-TGT-01, FR-HAL-01)
- **TSK-S2-04 — mạch ngắt suy giảm.** Lỗi liên tiếp ⇒ mở, đi thẳng fallback; không bao giờ sinh ALLOW. Kiểm: `pytest
  tests/test_fail_closed.py`. (FR-ACE-03, NFR-REL-02)
- **TSK-S2-05 — `@action`, `c.do()`/`c.say()`, token phán quyết dùng một lần.** Chỉ `c.do()` chạy được hành động; mỗi
  chân tiêu token một lần (NE1002). Kiểm: `pytest tests/test_actions.py`; ranh giới: `docs/spec/threat_model.md`.
- **TSK-S2-02 — `neuroedge build`.** Đối chiếu `agent.toml` + `@action` với bo mạch, báo **mọi** vấn đề một lần, ghi cây
  quyết định. Kiểm: `pytest tests/test_compiler.py`. (FR-HAL-04/05)
- **Tài liệu dẫn đường.** `docs/user/` (hướng dẫn, trạng thái sinh từ roadmap §0 — `scripts/gen_user_status.py`);
  `docs/user/thuat-ngu.md` giải mã mọi ký hiệu; sơ đồ Mermaid tại chỗ (luồng `c.do()`, cây kế thừa, FSM hội thoại);
  `CONTRIBUTING.md` §8. Kiểm: `pytest tests/test_user_status_fresh.py`.
- **Q-20 — bộ chuẩn bị cổng nhu cầu 2026-10-25** (`TODOS.md` #19): `docs/business/cong-nhu-cau-2026-10-25/` —
  câu hỏi cổng, demo ≤ 5 phút chỉ bằng lệnh đã chạy thật, bộ phỏng vấn, thang chấm, trang ghi phiếu.

#### Đã đổi

- **Roadmap viết lại theo increment I0–I18 (Q-39, Q-40).** Một roadmap: bảng increment §0.2 (dự báo, phụ thuộc,
  phát hành); 171 mã task giữ nguyên, 38 mã mới; phase1-5, phase2 và bản nháp robot thành ghi chú thiết kế. Luật R1–R12
  (§2.4) kiểm bằng `tests/test_plan_contract.py`. `TODOS.md`: bỏ #4, #13, #18, #28, #31 (đã thành task), thêm #42.
- **Q-30 — định vị "Hợp đồng vào Physical AI" / "Physical AI, under contract" (engine-first không đổi).** Contract là
  lớp bảo vệ gần nhất trên 5 nguyên thủy HAL; `neuroedge-prd.md` §1.2/§15 + masthead, `neuroedge-proposal.md`
  §0.3 + masthead, `README.md` hero EN-first; định vị NeuroBrain đề xuất ở `neuroedge-roadmap-phase1-5.md` §1
  (chờ Q-31); lưu vết `docs/archive/tai-dinh-vi-messaging-review.md`; theo dõi `TODOS.md` #32, #34. Không đổi mã; không cần RFC.
- **Q-29 — định vị trước MHS + bối cảnh cạnh tranh MHS/DCP.** `neuroedge-proposal.md`
  §10.1–§10.2 (hai cột + hai hàng MHS/DCP, kèm nguồn), Phụ lục H.3; quyết định ở
  `neuroedge-prd.md` §15; theo dõi `TODOS.md` #32–#33. Không đổi mã; không cần RFC
  (`CONTRIBUTING.md` §3).
- **Rà soát tài liệu MECE — mỗi sự thật một nơi.** Chủ sở hữu mới: danh sách cần RFC và cấu trúc kho ở
  `CONTRIBUTING.md` §3, §6; lệnh và job CI ở §2 tệp này; mã lỗi ở PRD Phụ lục B; allowlist giấy phép ở Q-11. Các mốc
  `[0.1.0]`–`[0.4.0]` đổi tên thành mốc tài liệu; `TODOS.md` xếp theo chủ đề, số mục giữ nguyên. PRD sở hữu nguyên tắc,
  tiêu chí A/B/C, ngưỡng NFR, giả định, ngoài phạm vi, giao thức; roadmap §10.1 chỉ còn mã | tên | ngày | task; proposal
  chỉ giữ "vì sao"; thuật ngữ về `docs/user/thuat-ngu.md`; FR-CLI MCP đổi mã thành FR-CLI-12.
- **Q-21 — kế hoạch lấp khoảng trống kỹ thuật.** Firmware không cần bo mạch (TSK-S4-02, S4-07 → S4-09, S4-11) kéo lên
  A2; TSK-S2-07 lên A2; TSK-S2-09 từ Sprint 5 lên Sprint 3; thêm TSK-S4-12. CI âm thanh dùng backend tệp/PCM vì runner
  GitHub không có `snd-aloop`. Roadmap §4.3.
- **Proposal Phụ lục H.1 xác minh giấy phép tại nguồn**, thêm ESP-SR/ESP-ADF (chỉ chip Espressif, chỉ trong firmware);
  sửa hai nhận định sai: Wokwi Elements không có chốt cửa, Renode không chạy ESP32-S3.
- **TSK-S3-02 — `verify` replay ba vết ghi chuẩn mực trên từng target** thay vì chỉ thẩm định lược đồ; mặc định
  `--targets sim`. Sprint 4 tiêu chí 2 dùng `SafetyRegressionError` (NE4002).
- **A3 — HAL chưa gắn `Conversation` từ chối mọi lệnh**, và kiểm tên chân trước khi tiêu bằng chứng; `hal.pin()` ném
  lỗi với tên chân không có trên bo mạch (CEO-S5-2).
- **Design doc Giai đoạn 1 tách biên bản review** sang `docs/archive/giai-doan-1-review-log.md` (lưu trữ, không quy
  phạm); thẻ bàn giao roadmap §0.3 rút gọn theo `CONTRIBUTING.md` §8.3.

#### Đã sửa

- **`run`/`record --target` nêu sai task và mã thoát.** `linux` nay chỉ TSK-S5-10, `esp32s3` chỉ TSK-S4-01 (trước in
  TSK-S3-05, task đã xong); target lạ thoát mã 1 kèm `NE3001`, không còn mã 2. Thông điệp bỏ tên sprint, chỉ giữ mã task.
  Kiểm: `pytest tests/test_cli_run.py tests/test_recorder.py -k target`.
- **Proposal §3.2 và dòng TSK-S6-07 lệch với kho.** QEMU chạy bằng `qemu-system-xtensa` (cài qua
  `idf_tools.py`), không phải `idf.py qemu`; bộ vector tuân thủ ở `fixtures/compliance/`, không phải `tests/compliance/`.
- **Giấy phép Pipecat ghi sai là MIT** ở `NOTICE` và mẫu ghi nhận `CONTRIBUTING.md` §4. Xác minh tại nguồn
  2026-09-25: BSD 2-Clause (Copyright Daily), khớp proposal Phụ lục H.1.
- **`replay --target esp32s3` thoát mã 2**, không phải 1: target đã biết nhưng chưa replay được vết ghi tuỳ ý
  (TSK-S4-04) là "chưa hiện thực". `verify --targets esp32s3` nay chạy (TSK-S4-09). Kiểm: `pytest tests/test_cli.py -k esp32s3`.
- **`mcp tools --help` mất chữ `[mcp.servers]`** vì `rich` đọc nó là thẻ markup. Escape trong `help=`; mọi `--help`
  được kiểm không nuốt chữ trong ngoặc vuông. Kiểm: `pytest tests/test_cli_help.py`.
- **TSK-S3-26 — REPL in lời "có" như một lượt đã xác nhận.** Trước: in "System 2 handled free phrasing", không có
  dòng ALLOW và bảng chân, dù vết ghi có `tool_confirmed` + ALLOW. Nay in phán quyết lần hai và chân. Kiểm: `pytest
  tests/test_cli_run.py -k confirmed_answer`.
- **`neuroedge build --target sim` không có `--board` chọn nhầm `esp32s3-box-3`** và fail NE3003. Bo mạch mặc định
  nay theo target (`sim` → `sim-default`, `linux` → `linux-rpi5`). Kiểm: `pytest tests/test_compiler.py -k reference_board`.
- **TSK-S3-27 — `mcp serve` bị client bỏ rơi không còn giữ cổng.** Không có `initialize` trong `--init-timeout` giây ⇒
  nhả cổng, thoát 0; cổng `--ui` bận ⇒ trang sang cổng trống, MCP vẫn chạy. Kiểm: `pytest tests/test_mcp_desktop.py`.
- **Hai dự án cùng tên agent dùng chung một module `actions/` đã import.** `load_actions` đặt tên module theo cả thư
  mục dự án. Kiểm: `pytest tests/test_cli_new.py`.
- **Sáu lỗ an toàn từ review đối kháng mã A1**, hai trong số đó kích được chân GPIO: độ tin cậy `NaN`/ngoài `[0, 1]`,
  `fail: open` tha dữ kiện đã biết là "không", provider ném lỗi hoặc treo, `fallback_action` cần tham số, lịch sử chân,
  task sinh trong hành động. Kiểm: `pytest tests/test_safety_regressions.py`.
- **CLI nuốt tên bảng TOML trong chẩn đoán** (`[requires]` bị `rich` hiểu là markup). Mọi `where`/`why`/`how` được
  escape. Kiểm: `test_cli_build_fails_with_exit_1_and_every_problem`.
- **Tham chiếu Copier/Wokwi còn sót** ở roadmap §3, PRD Phụ lục D và proposal §4.3 — nay ghi generator Python thuần và
  REPL gõ chữ.

#### Đã bỏ

- **Extra `scaffold` (`copier`).** `neuroedge new` không cần nó, nên không đường cài nào kéo `jinja2-ansible-filters`
  (GPL3). `NOTICE` §B, `requirements-lock.txt` cập nhật.
- **Tham số `fail_closed` của `ActionContractEngine`.** Gate chỉ fail-open khi chính tài liệu của nó khai `fail: open`;
  fail-closed là phán quyết, không phải exception (PRD Phụ lục B).

### Mốc gỡ chặn Sprint 2 — 2026-09-23 — chốt 9 quyết định, đồng bộ tài liệu

Rà soát toàn bộ tài liệu ngày 2026-09-23 kết luận **chưa triển khai được**: bốn
quyết định Tuần 1 chưa ai chốt, roadmap chưa nhận kế hoạch đã duyệt ở
`docs/designs/`, hai RFC bắt buộc chưa có, và PRD/proposal mâu thuẫn ở ba điểm
P0. Phiên này chốt quyết định với người phụ trách (minhlt) và đồng bộ lại.

#### Quyết định — ghi ở `neuroedge-prd.md` §15

| Mã | Quyết định | Gỡ chặn gì |
|:---|:---|:---|
| **Q-10** | LiteLLM là **thư viện định tuyến (SDK)** sau `neuroedge.models.providers`, cài qua extra `neuroedge[cloud]`; không chạy proxy | `TSK-S2-11` |
| **Q-11** *(một phần)* | **LiteLLM đã duyệt** + chính sách phụ thuộc bắc cầu (allowlist giấy phép, kiểm trong CI). Allowlist ghi tên **CNRI-Python** (2026-09-24, của `regex` qua tiktoken); test giữ script và Q-11 khớp nhau. Hawkbit/EMQX vẫn mở tới trước Khối 2 | Tiêu chí ra 6 Sprint 1, `TSK-S2-11` |
| **Q-14** | Mất mạng ⇒ gate **vẫn lượng giá** bằng bộ nhận diện **lệnh cố định** cục bộ; chỉ `gate_unreachable` khi fallback không chạy. Backend theo target, chung một ngữ pháp lệnh (`sim`: chữ gõ · `esp32s3`: ESP-SR MultiNet hoặc TFLite Micro/ESP-NN) | `CEO-X1` (FR-ACE-03 ↔ FR-MDL-03) |
| **Q-15** | `sim` mặc định **gõ chữ**, không mạng, không key; giọng nói là tuỳ chọn | FR-DX-02 ↔ FR-PER-07 |
| **Q-16** | GPIO `linux`: `gpio-sim` trong CI + mua 1 RPi 5 dự phòng | F1, `TSK-S3-05` |
| **Q-17** | `on_block` v1.0 được **đặc tả** (luôn chặn; `escalate`/`ask` ghi vết ghi + hook; `degrade` chạy `fallback_action` qua gate riêng) ⇒ **không cần waiver §11.3** | Cổng merge A1 |
| **Q-18** | Kế thừa `budget`/`on_block`: `p95` chỉ giảm · chuỗi `closed` không khai `open` · con không tự đưa vào `degrade` ([RFC-0004](docs/rfc/0004-ke-thua-budget-on-block.md)) | Lỗ `lax-night` (`ENG-A2`), `TSK-S2-13` |
| **Q-19** | Lịch bằng ngày tuyệt đối: A1 2026-09-28 → 10-25 · A2 10-26 → 11-15 · Sprint 4 mở 2026-11-16 | Mâu thuẫn 5 ↔ 6,5 tuần |
| **Q-20** | Cổng nhu cầu 2026-10-25 là **cổng mềm**; câu hỏi kinh doanh `CEO-X2..X5`, `CEO-T1..T4` vào `TODOS.md` | `CEO-X3` |

Tự chốt kèm theo, ghi để người đọc biết: RFC-0003 (ghim `extends` + đóng băng
`decision_tree.v1.json`) và `TSK-S3-21` hoãn tới Sprint 4; `TSK-S2-07`/`S3-10`/`S3-11`
hoãn cùng nhau; `TSK-S3-13` sang Sprint 5; đổi chủ trì theo `ENG-T3`.

#### Đã sửa

- **Bộ test phụ thuộc môi trường.** Shell có `FORCE_COLOR` làm 7 test CLI fail,
  và `gate resolve --json` in ra **không phải JSON**. `--json` và dòng digest của
  `gate publish` nay ghi thẳng stdout; `tests/conftest.py` gỡ `FORCE_COLOR` trước
  khi import CLI. Bộ test xanh ở cả hai môi trường.
- **Tài liệu:** PRD 1.3 (FR-ACE-03, FR-DX-02, FR-GATE-02/03/06, FR-CLI thêm
  `gate lint`/`gate resolve`, danh mục lỗi theo tên trong mã), proposal Phụ lục B
  theo RFC-0001 §9 + Q-17/Q-18, roadmap 1.3 (34 task, chủ trì mới, ngày tuyệt đối),
  `CONTRIBUTING.md` §5 ghi đúng lệnh CI.

#### Đã thêm — RFC-0004 + `TSK-S2-13`

[`docs/rfc/0004-ke-thua-budget-on-block.md`](docs/rfc/0004-ke-thua-budget-on-block.md)
(✅ chấp thuận, Q-18) và hiện thực trong `engine/gate_resolver.py`: `p95` của con ≤
cha (nguyên tắc 2), chuỗi `closed` không mở lại (nguyên tắc 4), con không tự đưa vào
`degrade` (nguyên tắc 2). Vẫn **năm** nguyên tắc. Corpus phản chứng: +4 invalid,
+1 valid, +1 registry. Test **210 → 229**, 0 skip.

### Mốc tài liệu Giai đoạn 2 — 2026-09-22 — thị giác, phủ rộng phần cứng, nền tảng cho maker

Thay đổi **chỉ ở tầng tài liệu**. Ba lược đồ trong `schemas/` **chưa đổi** và
không được đổi cho tới khi RFC-0002 được phê duyệt; bộ test vẫn 210/210 xanh.

#### Đã thêm — RFC-0002 *(trạng thái: đang thảo luận)*

[`docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md`](docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md)
*(Ghi chú 2026-09-23: RFC-0002 đã **thu hẹp** chỉ còn mở enum `target` +
`TARGET_TIERS`; `vision.in` chuyển sang V1b. Đoạn dưới giữ nguyên như bản gốc.)*
đề xuất mở enum `target` ở `board.v1` và `trace.v1`, thêm nguyên thủy tùy chọn
`vision.in`, và mở trường vết ghi cho bằng chứng thị giác.

**Phát hiện dẫn tới RFC này:** thêm một target **không phải hạng mục roadmap** mà
là thay đổi lược đồ đã đóng băng. Danh sách `["sim", "linux", "esp32s3"]` bị lặp
ở bốn nơi — hai lược đồ, `hal/board.py`, và chuỗi thông điệp lỗi trong
`fixtures/traces/expected_errors.yaml` — trong đó `schemas/` và `fixtures/traces/`
đều thuộc diện RFC bắt buộc theo `CONTRIBUTING.md` §3.

RFC-0002 cũng phải nới hai bất biến kiểm thử: mọi bo mạch dùng chung tập tên chân,
và mọi profile khai đủ năm nguyên thủy. §5 của RFC nêu rõ nới thế nào mà không
làm hệ thống lỏng hơn.

#### Đã thêm — Tài liệu Giai đoạn 2

[`neuroedge-roadmap-phase2.md`](neuroedge-roadmap-phase2.md) — sáu khối V1a, V1b,
V2, V3, P1, P2 từ Tháng 9 đến Tháng 24, chạy **song song** Khối 4 AURA chứ không
nối tiếp. AURA là nguồn dữ liệu R3 cho chính thị giác.

#### Đã đổi — Nguyên tắc P-2 bỏ số đếm

*"Ba môi trường thực thi ngang hàng"* → *"Các môi trường thực thi ngang hàng"* ở
proposal §0.4 và PRD §1.5. **Hệ quả kỹ thuật giữ nguyên nguyên văn** — "không rẽ
nhánh logic theo target trong mã nguồn agent" không hề bị phá khi thêm target;
chỉ con số bị phá. Khoảng 42 chỗ viết cứng "3 môi trường" trên ba tài liệu được
sửa theo cùng một mẫu.

#### Đã thêm — Phân tầng cam kết theo bậc target

| Bậc | Target | Cam kết của đội lõi |
|:---:|:---|:---|
| **1 — Chính thức** | `sim` · `linux` · `esp32s3` | `verify` 100%, kiểm thử hằng đêm |
| **2 — Mở rộng** | `jetson` | Bảo trì, verify trên miền phán quyết |
| **3 — Cộng đồng** | `stm32` · `rp2350` | Không cam kết; cộng đồng tự kiểm chứng qua Bộ kiểm thử tuân thủ |

Mọi ngưỡng chất lượng trong proposal §12 và PRD §11 nay neo tường minh vào **bậc 1**.
Ghi nhận bằng `FR-TGT-08` và `Q-13`; rủi ro pha loãng chất lượng ghi ở `R-7` (PRD)
và rủi ro #6 (proposal §11).

#### Đã đổi — Mở khóa vision và Jetson khỏi danh mục hoãn

proposal §9 và PRD §14: ba dòng chặn vision, Jetson và độ phủ bo mạch chuyển sang
*"Đưa vào Giai đoạn 2"*. Cột lý do phải **viết lại**, không chỉ đổi trạng thái —
hai dòng cũ viện dẫn chính con số *"ba môi trường đã đủ"* làm lập luận, nên giữ
nguyên sẽ khiến tài liệu tự mâu thuẫn.

**Vision trượt bộ lọc R1** (không rút ngắn TTFV) nhưng **thắng R2** (không bổ sung
muộn được mà không viết lại kiến trúc). Theo proposal §2, thỏa R1 *hoặc* R2 là đủ.
Vì vậy Giai đoạn 2 tách **V1a đặt chỗ kiến trúc** — chỉ chốt chỗ trong hợp đồng,
không viết driver, không đụng TTFV — khỏi **V1b hiện thực**, mở khóa khi có nhu
cầu đo được từ khách hàng AURA thật.

#### Đã thêm — Chính sách cho tài sản do bên thứ ba sở hữu

proposal §6.4 có thêm hàng cho **adapter và HAL port**: tác giả giữ bản quyền, mã
nằm ở kho riêng, NeuroEdge chỉ lập chỉ mục. §1.7 bổ sung lập luận an toàn riêng
cho loại tài sản này — lập luận biện minh cho việc chia sẻ gate (*"nhẹ, minh bạch,
không rủi ro pháp lý"*) **không chuyển sang được** cho mã thực thi chạy gần cơ cấu
chấp hành. Ba cổng kiểm soát: Bộ kiểm thử tuân thủ, sandbox phân quyền, đối chiếu
năng lực lúc build.

#### Đã thêm — KPI Giai đoạn 2 (§12.4) và mở rộng G2/G3

§12 trước đây kết thúc ở mốc 12 tháng, để lại vùng trắng cho Giai đoạn 2. Bổ sung
V-G1 đến V-G5 ở mốc 24 tháng. G2 và G3 mở rộng để **đếm cả adapter và HAL port**,
không chỉ gate và agent.

**V-G1 được chỉnh so với đề xuất ban đầu** để nối được vào doanh thu: ngoài ngưỡng
5.000 thiết bị vision, thêm ngưỡng **≥ 500 thiết bị thuộc đội có gói Fleet trả phí**.
Lý do: usecase consumer thu hút người dùng nhưng người dùng cuối không trả tiền, và
sau khi bỏ doanh thu inference ở v5.3, Fleet là dòng thu duy nhất và tính theo đội
thiết bị doanh nghiệp.

#### Đã đổi — Chuẩn hóa hệ ký hiệu và ma trận truy vết

Một đợt rà soát toàn bộ bộ tài liệu tìm ra năm lỗi cascade. Tất cả đã sửa.

| # | Lỗi | Cách sửa |
|:---:|:---|:---|
| 1 | **Hai bộ `C1–C7` khác nhau dùng chung nhãn** — PRD §11.3 (nghiệm thu phát hành) và roadmap §8.3 (tiêu chí ra Khối 2/3). Không phải chi tiết hóa của nhau: roadmap C2 = PRD C1, roadmap C4 (≥10 gate) lệch PRD C5 (≥20 gate), năm tiêu chí còn lại không có cặp | Bộ của roadmap đổi thành **TR-1…TR-7** kèm bảng chỉ rõ mỗi TR phục vụ tiêu chí C nào; TR nào không có C tương ứng được đánh dấu *(nội bộ)* |
| 2 | **Ký hiệu `R` mang hai nghĩa** — `R1–R4` là bộ lọc ưu tiên (proposal §2), `R-1…R-7` là rủi ro sản phẩm (PRD §13.2). Cả hai xuất hiện trong cùng một hàng bảng ở PRD §14 | Bộ lọc đổi thành **PF-1…PF-4**. Hệ mã rủi ro `R-n` giữ nguyên |
| 3 | **Sổ quyết định bị chẻ đôi** — PRD có Q-1…Q-7, Q-12, Q-13; roadmap có Q-1…Q-12. Không tài liệu nào giữ đủ bộ, và **Q-7 được ghi ĐÃ CHỐT ở PRD nhưng đang mở ở roadmap** | PRD §15 thành sổ duy nhất với đủ **Q-1…Q-13**; roadmap §10 chuyển thành bản theo dõi trạng thái và đã khớp hoàn toàn |
| 4 | **Hai sổ rủi ro chồng lấn không khai báo ranh giới**, và cả hai đánh số sai thứ tự | Khai báo ranh giới: proposal §11 = rủi ro *chiến lược*, PRD §13.2 = rủi ro *sản phẩm và thực thi*. Ba cặp giao nhau được ánh xạ tường minh. Cả hai sổ sắp lại đúng thứ tự |
| 5 | **Ký hiệu `§` mang hai nghĩa** — bảng Quy ước PRD nói `§x.y` trỏ proposal, nhưng nhiều chỗ tự trỏ chính nó; roadmap và phase2 không có bảng quy ước nào | Thêm quy ước `§x.y của tài liệu này` cho tham chiếu nội bộ và áp dụng nhất quán. Roadmap và phase2 có bảng **Quy ước tài liệu** riêng |

**Ma trận truy vết PRD mở rộng từ 44% lên 100%.** Phụ lục A trước đây chỉ truy vết theo mục tiêu (A.1) và nguyên tắc (A.2), bỏ trống 85/151 yêu cầu — trong đó có **toàn bộ NFR**. Bổ sung **A.3** (đối chiếu yêu cầu phi chức năng: cách kiểm chứng và tiêu chí nghiệm thu) và **A.4** (các nhóm yêu cầu chức năng không rơi vào trục mục tiêu hay nguyên tắc: HAL, PER, CI, GOV, CLI, DX, TEL…). Mọi hàng ghi rõ tên nhóm để truy vết kiểm được bằng máy.

Ngoài ra: tiêu chí **A1** trong roadmap có hai phát biểu lệch nhau (ngưỡng cá nhân vs trung vị trên 10 người) — đã đồng bộ về nguyên văn PRD.

#### Cần chú ý — Hai bài toán để mở có chủ đích

1. **Ngữ nghĩa gate lượng giá trên bằng chứng thị giác chưa được giải.** Cho tới
   khi có RFC riêng, kết quả thị giác chỉ được dùng làm thông tin ngữ cảnh; agent
   muốn hành động dựa trên camera phải quy về `bool` / `level` / `choice` qua
   `SystemOne`. Rule engine giữ nguyên 100% xác định.
2. **Ngân sách bộ nhớ cho nguyên thủy thứ sáu trên vi điều khiển** chưa đo được vì
   chưa có bo mạch. Không chặn RFC, nhưng chặn việc khai `vision_in` cho `esp32s3`.

### Mốc CR-1.0 — 2026-09-21 — chuyển định hướng cloud-first

Thay đổi **chỉ ở tầng tài liệu**, không đụng một dòng mã nguồn nào và không đụng
ba lược đồ đã đóng băng trong `schemas/`. Nguồn thay đổi là yêu cầu tinh chỉnh
tài liệu **CR-1.0 — chuyển định hướng cloud-first** (hồ sơ lưu ngoài kho mã), đã
áp dụng vào proposal v5.3 · PRD v1.1 · roadmap v1.1.

#### Đã đổi — Định hướng kiến trúc

- **Cloud-first, provider-pluggable.** Toàn bộ tầng AI (LLM, ASR, TTS) trở thành
  nhà cung cấp thay thế được, kết nối qua **chuẩn OpenAI API** hoặc **adapter do
  người dùng tự viết**. Phần nặng về xử lý ngôn ngữ chạy trên cloud hoặc host;
  `esp32s3` chỉ còn thu/phát âm thanh, AEC/VAD, máy trạng thái hội thoại và thẩm
  định gate.
- Ghi nhận bằng cách **mở rộng nguyên tắc P-4** (proposal §0.4 nguyên tắc 4 ·
  PRD §1.5) thay vì thêm nguyên tắc thứ sáu — số nguyên tắc bất biến vẫn là năm.
- **Fail-closed không đổi.** Gate và máy trạng thái chạy hoàn toàn trên thiết bị;
  `NFR-RES-04` (100% tính năng an toàn hoạt động ngoại tuyến) giữ nguyên tuyệt đối.

#### Đã đổi — Mô hình thương mại

- **Bỏ hoàn toàn doanh thu inference.** Mô hình cost-plus 5–10% trên token bị xóa
  khỏi proposal §6.3. **Fleet OS là dòng doanh thu duy nhất.**
- **Inference Gateway → Lớp trừu tượng nhà cung cấp (Provider Abstraction Layer).**
  Chuyển từ dịch vụ thương mại sang **lõi mã nguồn mở MIT tự vận hành**
  (proposal §6.1, §6.4). Người dùng tự chạy, tự giữ khóa, tự trả phí cho nhà
  cung cấp. Đánh số mục §6.1–§6.4 giữ nguyên nên mọi tham chiếu chéo còn đúng.
- Nhóm **FR-GW-01→07** của PRD chuyển từ mốc v1.1 (thương mại) sang **lõi OSS
  v1.0**; FR-GW-05 hạ từ P0 xuống P1.

#### Đã thêm — Yêu cầu mới trong PRD

| Mã | Nội dung | Ưu tiên |
|:---|:---|:---:|
| `FR-MDL-07` | Provider pluggable cho LLM, ASR và TTS | P0 |
| `FR-MDL-08` | Adapter kết nối do người dùng tự viết | P0 |
| `FR-MDL-09` | ASR/TTS thay thế được qua cấu hình | P0 |
| `FR-PER-07` | Cloud-first voice — MCU chỉ stream âm thanh | P0 |
| `FR-REG-08` | Kho chia sẻ adapter kết nối provider | P1 |
| `NFR-SEC-08` | TLS 1.3 cho dữ liệu gửi tới provider cloud | P0 |
| `NFR-PERF-07` | Độ trễ thoại với provider request-response: P95 < 1.500 ms | P1 |
| `R-6` | Rủi ro phụ thuộc provider cloud khi mất kết nối | — |
| `Q-12` | Chuẩn kết nối mặc định là OpenAI API *(ĐÃ CHỐT)* | — |

#### Đã đổi — Phạm vi thực thi

- **Sprint 2** nhận thêm `TSK-S2-11` (lớp trừu tượng provider) và **Sprint 3**
  nhận `TSK-S3-13` (ASR/TTS qua provider cloud) — lớp provider dựng ở **Khối 1a**
  chứ không chờ Khối 2.
- **Sprint 5 giảm phạm vi:** không hiện thực STT/TTS trên thiết bị; thêm
  `TSK-S5-06` (client streaming lên provider). Rủi ro **R-1 hạ từ Cao xuống
  Trung bình**. Bốn ràng buộc RB-1→RB-4 cho Sprint 4 **vẫn giữ nguyên hiệu lực**
  vì đường dẫn âm thanh thu/phát không đổi.
- **Khối 2** chỉ còn Fleet OS. `TSK-K2-01→03` đổi từ dịch vụ Gateway sang hoàn
  thiện lớp provider OSS, giữ nguyên mã task để không vỡ truy vết.

#### Cần chú ý — Hệ quả giấy phép

**LiteLLM chuyển từ H.2 (dịch vụ máy chủ, không phân phối) sang H.1 (phân phối
kèm sản phẩm)** trong proposal Phụ lục H. Nghĩa vụ giấy phép đổi theo phạm vi
phân phối, nên **Q-11 phải được xét lại và chốt trước khi bắt đầu `TSK-S2-11`**,
không phải trước Khối 2 như trước đây. Hạn của **Q-10** cũng đẩy từ Tháng 3 lên
Tuần 2 vì cùng lý do.

#### Đã sửa — Lỗi tồn đọng phát hiện khi rà soát

- PRD: `NFR-RES-02/03` vẫn ghi *"Cần chốt — xem §15, Q-3"* trong khi Q-3 đã chốt
  — nay điền số liệu thật.
- PRD: mục lục ghi *"15. Quyết định cần chốt"* lệch với tiêu đề thật
  *"15. Quyết định kỹ thuật đã chốt"*; typo *"Quyước"* ở Phụ lục C; Q-3 dùng cú
  pháp LaTeX lẫn trong Markdown.
- Proposal: rủi ro #4 tham chiếu §8.6 trong khi cột mốc G1–G4 nằm ở §8.7; đoạn
  *"Nền tảng hiện thực"* của §6.1 thiếu dòng trống nên bị nuốt vào bảng.
- Proposal: `Phụ lục D.2` và bảng Voice Pipeline `§3.4` lệch nhau về danh mục
  STT/TTS — nay đồng bộ.

### Mốc Sprint 1 — 2026-09-21 — đóng băng lược đồ (Khối 1a)

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

Yêu cầu **Python 3.11+**. Toàn bộ mã dùng `tomllib` của thư viện chuẩn, nên không có
phụ thuộc TOML bên ngoài.

```bash
cd python
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q          # kỳ vọng: 0 failed, 0 skipped
```

Bản dựng tái lập được (roadmap §3.9, nghĩa vụ 5 — ghim phiên bản):

```bash
.venv/bin/python -m pip install -r requirements-lock.txt
```

System 2 trên model thật (tùy chọn, không cần cho test): `.venv/bin/python -m pip install -e '.[cloud]'`,
thêm `[system_two]` vào `agent.toml` (mẫu có sẵn, đã comment, trong `fixtures/agents/home-voice/agent.toml`) và
export key. Thử với key thật: `python scripts/live_llm_smoke.py` (tốn vài cent, không chạy trong CI).

### 2.2 Kiểm tra nhanh toàn bộ artifact

Các lệnh dưới viết cho **gốc kho**. `paths.py` tự tìm gốc từ checkout, editable install
hay wheel (ghi đè bằng `NEUROEDGE_ROOT`), nên `verify` và `gate lint` chạy được cả từ
`python/`.

```bash
V=python/.venv/bin

$V/neuroedge verify                      # kỳ vọng: mọi gate phân giải · mọi vết ghi chuẩn mực thẩm định · corpus tool call khớp · mọi replay khớp; quét được 0 ⇒ NE4004, mã 1
$V/neuroedge gate lint                   # kỳ vọng: ✓ mọi gate resolved, mã 0
$V/neuroedge trace validate fixtures/traces/*.json   # kỳ vọng: mỗi tệp VALID
$V/neuroedge board list                  # kỳ vọng: mỗi profile trong boards/
python3 scripts/gen_cpo_dashboard.py     # sinh lại dashboard CPO (docs/business/cpo-dashboard.html) sau khi đổi roadmap/TODOS/PRD/CHANGELOG
$V/python scripts/check_digests.py --check   # kỳ vọng: ✓ … tệp khớp digests.lock
```

Khẳng định nghịch đảo — corpus phản chứng **phải** tiếp tục thất bại:

```bash
$V/neuroedge gate lint fixtures/gates/invalid --registry fixtures/gates/registry
# kỳ vọng: mọi tệp trong invalid/ đều failed to resolve · mã thoát 1
```

Nếu lệnh trên **thành công**, các phép kiểm tra an toàn kế thừa đã hồi quy, và
một pipeline xanh lúc đó là thông tin sai. CI có đúng một bước cho việc này.

### 2.3 Tham chiếu lệnh CLI

**Hợp đồng mã thoát** — CI và Action CI đều neo vào nó:

| Mã | Nghĩa |
|:---:|:---|
| `0` | Phép kiểm tra đã chạy và **đạt** |
| `1` | Phép kiểm tra đã chạy và **không đạt** |
| `2` | Lệnh (hoặc `--target` đó của lệnh) **chưa được hiện thực** |

Mã `2` tách biệt với `1` là có chủ ý: CI phân biệt được "hỏng" và "chưa có". Hôm nay
thoát mã 2: `run --target linux|esp32s3`, `record --target linux`, `replay --target esp32s3`
(TSK-S4-04). Target lạ (không phải `sim`, `linux`,
`esp32s3`) là lỗi, mã 1.

Mọi lệnh nạp gate nhận `--registry <dir>` (`-r`): nơi tra `neuroedge://`, mặc định `gates/`.
`--agent` mặc định là `./agent.toml`, không có thì agent mẫu `villa-concierge` của checkout.

#### Lệnh đã hiện thực

| Lệnh | Chức năng |
|:---|:---|
| `gate resolve <tệp\|URI>` | Phân giải chuỗi `extends`, in chính sách hiệu dụng và mã băm. `--json` cho đầu ra máy đọc |
| `gate lint [dir]` | Phân giải mọi gate trong thư mục (mặc định `gates/`). Không có `--registry` thì lệnh tìm `registry/` trong `dir` rồi cạnh `dir`, cuối cùng `gates/` |
| `gate publish <tệp>` | Biên dịch sang JSON chuẩn tắc RFC 8785, in mã băm SHA-256. `--out` ghi ra tệp |
| `gate add <URI>` | Phân giải một gate từ registry và cho biết việc kế thừa nó sẽ áp đặt gì |
| `gate explain <tệp\|URI>` | Giải thích gate cho người duyệt: tiêu chí từ cấp nào, mệnh đề nào bị siết chặt, ngân sách và `on_block` so với cha. Gate sai ⇒ mã 1, lỗi 3 thành phần |
| `trace validate <tệp…>` | Thẩm định theo `trace.v1.json`. Một tệp sai làm cả lệnh thất bại |
| `trace show <tệp>` | In dòng thời gian sự kiện |
| `trace view <tệp> [-o x.html] [--open]` | Ghi một tệp HTML tự chứa: thiết bị, cảm biến, màn hình, phán quyết, dòng sự kiện, thanh tua thời gian. Mở không cần mạng |
| `trace export <tệp> --format chrome [-o]` | Chrome Trace Event JSON cho Perfetto (`ui.perfetto.dev`) — gate và xung thành slice |
| `board list` / `board show <id>` | Liệt kê / xem năng lực bo mạch theo 5 nguyên thủy |
| `verify [--targets sim,linux,esp32s3] [--port <nguồn>]` | Mọi gate phân giải, mọi ca của corpus tool call (`fixtures/tool_calls/`, trên `sim`) ra đúng đáp án, mọi vết ghi chuẩn mực thẩm định **và** replay trên từng target ra đúng quyết định nó ghi (A2). Mặc định `sim`; `linux` cần line GPIO (bo mạch hoặc `scripts/setup_gpio_sim.sh`); `esp32s3` cần `--port <nguồn>` (như `record`): firmware replay các vết ghi chuẩn mực, lệch ⇒ `NE4002`; firmware replay vết ghi hay gate cũ hơn checkout ⇒ `NE4003`, không so; thiếu `--port` ⇒ mã 1. So quyết định, chưa so timing. Loại artifact nào quét được 0 ⇒ `NE4004`, mã 1 |
| `build --target <t> [--board id]` | Đối chiếu năng lực agent ↔ bo mạch, phân giải và biên dịch gate (ghi cả `<gate>.netree`/`.netree.h`); kiểm `[mcp]` và `[system_two]` (API key ghi trong `agent.toml` ⇒ lỗi, không in lại key). `--agent` (mặc định `agent.toml`), `--board` (mặc định bo mạch tham chiếu của target: `sim-default`, `linux-rpi5`, `esp32s3-box-3`), `--out` (mặc định `build/`). Hỏng ⇒ in mọi vấn đề, mã 1, không ghi gì |
| `replay <tệp> [--target sim\|linux]` | Replay trên HAL thật: dữ kiện đã ghi vào lại, phán quyết gate và lệnh chân **tính lại**, rồi so với golden (`--golden <tệp>`, mặc định chính vết ghi). Khớp ⇒ mã 0; lệch ⇒ mã 1, `NE4002`, dòng lệch đầu tiên; `--target esp32s3` ⇒ mã 2. `--agent`, `--board`, `--trace-out` |
| `record [--out traces/] [-c "<lệnh>"] [--anonymize]` | Như `run`, và ghi phiên ra `traces/<session_id>.json` đã thẩm định. `--anonymize` băm chữ thô tại nguồn (`sha256:`), phán quyết giữ nguyên (FR-TRC-07) |
| `record --target esp32s3 --port <nguồn> [--out traces/] [--timeout 30] [--baud 921600]` | Thiết bị ghi, host đọc UART: mỗi phiên `NE1` thành một tệp `<session_id>.json` đã thẩm định (`--out x.json` khi chỉ có một phiên). `<nguồn>`: tệp log (QEMU `-serial file:uart.log`), `tcp://host:port` (QEMU `-serial tcp::5555,server`), `/dev/tty…` (cần `neuroedge[serial]`). Dòng hỏng, thiếu khung, đếm lệch ⇒ `NE4001` nêu `nguồn:dòng`, mã 1, không ghi gì. Định dạng: `docs/spec/simulation_coverage.md` §4 |
| `test [thư-mục] [--pytest-arg A]` | Chạy bộ Action CI (pytest) của agent, mặc định `tests/`. Mọi test đạt ⇒ mã 0; có test trượt hoặc không thu được test nào ⇒ mã 1 |
| `run [--agent a.toml] [--board id]` | REPL gõ chữ trên `sim` (Q-15): lệnh khớp `commands.toml` → `c.do()` → phán quyết + chân ảo. `:facts`, `:set k v`, `:unset k`, `:pins`, `:sensors`, `:sensor n v`, `:screen`, `:confirm`, `:decline`, `:help`; `--ui` mở cùng phiên trên trình duyệt (127.0.0.1, `--port`, `--no-browser`); `exit` / Ctrl-D ⇒ mã 0. `-c "<lệnh>"` chạy một lệnh rồi thoát (BLOCK vẫn là mã 0); `--trace-out <tệp>` ghi vết ghi `trace.v1`. Agent không hợp bo mạch ⇒ mọi vấn đề, mã 1. `--target linux` ⇒ mã 2: trên `linux` hôm nay dùng `replay`. Có `[system_two]` ⇒ câu ngoài ngữ pháp do model thật trả lời (banner có dòng `system 2: <provider> <model> (key from $BIẾN…)`); không trả lời được ⇒ câu offline |
| `mcp tools [--json\|--openai] [--external]` | Schema của mỗi `@action` — dạng MCP hoặc function-calling OpenAI (Q-24). `--external`: thêm tool thông tin của `[mcp.servers]` mà System 2 được đưa (Q-27) |
| `mcp serve [--agent a.toml] [--board id] [--trace-out t.json] [--ui [--port 8765] [--open]] [--init-timeout 30]` | Máy chủ MCP qua stdio trên `sim`; mọi `tools/call` qua kiểm schema và gate. `--ui`: cùng phiên trên trang web 127.0.0.1 (`--port 0` chọn cổng trống; chỉ mở trình duyệt khi có `--open`); URL in ra stderr, stdout chỉ là kênh JSON-RPC. Cổng bận ⇒ cảnh báo stderr, trang sang cổng trống (URL thật ở dòng `sim UI at …`), MCP vẫn chạy. Không có `initialize` sau `--init-timeout` giây ⇒ thoát 0 (`0` = chờ mãi). Cần extra `neuroedge[mcp]` |
| `mcp desktop-config [--agent a.toml] [--ui [--port 8765]] [--trace-out t.json] [--name N] [--write [--config-path P]]` | In mục `mcpServers` cho Claude Desktop, toàn đường dẫn tuyệt đối (trình thông dịch hiện tại, `-m neuroedge mcp serve`). `--write`: đặt đúng mục đó trong `claude_desktop_config.json` của Desktop (macOS `~/Library/Application Support/Claude/`, Windows `%APPDATA%\Claude\`), sao lưu `.bak-<giờ>`, giữ mọi khoá khác; JSON hỏng ⇒ mã 1, không ghi gì. Sau đó thoát hẳn Desktop rồi mở lại. Cần extra `neuroedge[mcp]` |
| `new <tên> [--template minimal\|villa-concierge\|home-voice]` | Sinh dự án: `agent.toml`, `commands.toml`, `gates/`, `actions/`, `tests/`, `README.md`. Thư mục đã có nội dung ⇒ mã 1, không ghi gì. `villa-concierge` (chốt cửa) và `home-voice` (trợ lý giọng nói, có `knowledge.toml`) sao agent mẫu (có trong wheel) |

`python -m neuroedge …` tương đương `neuroedge …`.

> `gate publish` **không ký số**. Nó dừng ở mã băm, vì ký cần khóa của Gate
> Registry (Khối 3). Lệnh tự nói rõ điều đó trong đầu ra — đừng đọc nó như đã làm nhiều hơn.

### 2.4 Đọc một thông báo lỗi

Mọi lỗi có đúng ba phần (FR-DX-04): **ở đâu** · **vì sao** · **cách xử lý**.
Lỗi kế thừa có thêm dòng `rule` chỉ ra nguyên tắc B.5 bị vi phạm.

```
[NE2003] loosens-level@1.0.0 (fixtures/gates/invalid/loosens_level.yaml) -> allow_when.risk_level
  why: loosens the inherited condition: base admits {low}, this gate admits {high, low, medium}
  rule: Appendix B.5 principle 2
  fix: narrow allow_when.risk_level to a subset of the base condition (base clause: {'lte': 'low'}), …
```

Nghĩa của từng mã `NE…`, lớp lỗi và lúc nó xuất hiện: PRD
[Phụ lục B](neuroedge-prd.md#phụ-lục-b--danh-mục-mã-lỗi-chuẩn).

### 2.5 CI

Đây là **danh sách duy nhất** của workflow và job.

| Workflow | Khi nào | Job |
|:---|:---|:---|
| `ci-sim-linux.yml` | Mỗi PR và push lên `main` | `frozen-artifacts` · `tests` (Python 3.11/3.12/3.13, gồm walker và sổ token C biên dịch trên host) · `linux-hal` · `wheel-smoke` · `lint` · `licence-obligations` · `cloud-extra` |
| `firmware-qemu.yml` | PR và push đụng `targets/**`, `fixtures/traces/`, `engine/binary_tree.py` hoặc `testing/uart.py` · 01:30 UTC+7 hằng đêm · chạy tay | `firmware-qemu`: build `esp32s3` với `sdkconfig.qemu` (ESP-IDF 5.4), boot trên Espressif QEMU, đòi `NE_SELFTEST PASS` rồi `NE_TRACE DONE` trên UART · `uart-trace`: bằng CLI đã cài, `record --target esp32s3 --port uart.log` + `trace validate` (đòi `device_id = qemu`), rồi `verify --targets esp32s3 --port uart.log` |
| `release-pypi.yml` | Tag `v*.*.*` · PR đổi tệp đóng gói · chạy tay | `build` · `smoke` (Python 3.11/3.13) · `publish-testpypi` · `publish-pypi` — hai job cuối chỉ chạy với tag **và** `PUBLISH_ENABLED == 'true'` ([`docs/release.md`](docs/release.md)) |
| `nightly-hardware.yml` | 01:00 UTC+7 hằng đêm · chạy tay | `firmware-build` (ESP-IDF 5.2.1, ngân sách flash Q-3) · `upstream-drift` · `memory-spike` · `report` |

`ci-sim-linux.yml` phải xanh trước khi hợp nhất. Năm cổng đáng chú ý:

- **Cổng chặn test skip** — đọc `junit.xml`, thất bại nếu có bất kỳ test nào
  skip hoặc không có test nào. Lý do ở `CONTRIBUTING.md` §5.
- **Khẳng định nghịch đảo** — corpus phản chứng phải tiếp tục thất bại, đúng mã 1 (§2.2).
- **`digests.lock`** — sửa hay xoá một gate chuẩn mực mà không có RFC ⇒ đỏ
  (`scripts/check_digests.py --check`; thủ tục ở `CONTRIBUTING.md` §3).
- **Cổng giấy phép** — `licence-obligations`: `pip-licenses --fail-on` trên toàn bộ cây phụ thuộc lõi; `cloud-extra`:
  chính sách Q-11 cho extra `cloud` (`scripts/check_licences.py`: giấy phép lạ hoặc không rõ ⇒ đỏ).
- **`ruff check .` và `ruff format --check .`** — job `lint`.

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
Chưa có bo mạch: walker C chạy trên host với `make -C targets/esp32s3/components/ne_gate
check-static` (dòng vết ghi: `…/ne_trace check-static`), và firmware boot trên QEMU theo
`firmware-qemu.yml`. Vết ghi của phiên: `neuroedge record --target esp32s3 --port build/uart.log`; so với
golden: `neuroedge verify --targets esp32s3 --port build/uart.log`. Đổi vết ghi chuẩn mực, gate hay action
thì sinh lại `main/vectors/` (`scripts/gen_firmware_vectors.py`) trước khi build.

---

## 3. Bàn giao ngữ cảnh sản phẩm

Mục này dành cho người (hoặc phiên làm việc) tiếp quản. Đọc hết mục này là đủ
để build tiếp mà không phải đọc lại ba tài liệu gốc.

### 3.1 Các tài liệu là nguồn sự thật

| Tệp | Vai trò | Khi nào đọc |
|:---|:---|:---|
| [`neuroedge-roadmap.md`](neuroedge-roadmap.md) | **Roadmap duy nhất (Q-39):** increment I0–I18, trạng thái task, tiêu chí ra, dự báo, phụ thuộc, thẻ phát hành. §0 là bảng điều khiển | **Luôn đọc trước** |
| [`neuroedge-roadmap-phase2.md`](neuroedge-roadmap-phase2.md) | Ghi chú thiết kế — thị giác, phủ rộng phần cứng (I11, I13, I15–I18); không lịch, không trạng thái | Khi làm task của các increment đó |
| [`neuroedge-roadmap-phase1-5.md`](neuroedge-roadmap-phase1-5.md) | Ghi chú thiết kế — NeuroBrain (I12) | Khi làm task `TSK-N*` |
| [`draft-ke-hoach-mo-rong-robot-fofoca.md`](draft-ke-hoach-mo-rong-robot-fofoca.md) · [`draft-rfc-node-giao-thuc-dieu-phoi.md`](draft-rfc-node-giao-thuc-dieu-phoi.md) | Ghi chú thiết kế — robot phân tầng FOFOCA (I14; `TSK-W0-*` rải ở I2, I6, I7) · RFC nháp điều phối node (chưa cấp số) | Khi việc chạm nguyên thủy HAL mới, robot nhiều MCU hoặc multi-node |
| [`neuroedge-prd.md`](neuroedge-prd.md) | Yêu cầu `FR-*` / `NFR-*`; **§15 là sổ quyết định duy nhất** (`Q-N`); Phụ lục B là mã lỗi | Khi cần biết *phải* làm gì, và đã chốt gì |
| [`neuroedge-proposal.md`](neuroedge-proposal.md) | Kiến trúc và các Phụ lục. **Phụ lục B là đặc tả gate** | Khi cần biết *tại sao* |
| [`docs/spec/`](docs/spec/) | Đặc tả chuẩn tắc: Gated Tool Profile, mô hình mối đe doạ, phủ mô phỏng, rà soát MCU, máy trạng thái hội thoại | Trước khi đổi hành vi ở tầng tương ứng |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Quy ước; §3 việc gì cần RFC; §6 cấu trúc kho; §8 khi xong task | Trước khi sửa |
| [`docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md`](docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md) | Kế hoạch Giai đoạn 1 đã duyệt, nay lưu trữ (biên bản review cùng thư mục) | Khi cần biết *vì sao* một task bị cắt/hoãn |
| [`TODOS.md`](TODOS.md) | Việc hoãn có chủ ý, mỗi mục kèm mốc kích hoạt | Trước khi đề xuất việc "còn thiếu" |

**Thứ tự ưu tiên khi lệch nhau:** PRD và proposal (hợp đồng) → roadmap (tiến độ, lịch) →
ghi chú thiết kế → mã nguồn → tệp này. Nếu mã lệch hợp đồng, mã sai. Ghi chú thiết kế nói gì
về lịch, trạng thái hay tiêu chí ra thì roadmap đúng (R1).

### 3.2 Bản đồ kiến trúc — cái gì ở đâu

Bản đồ kho, kèm thủ tục sửa từng phần: `CONTRIBUTING.md` §6. Bốn tầng: L0 `sim/`
(phiên gõ chữ, trang cục bộ) · L1 `hal/` (năm nguyên thủy) · L2 `models/`, `perception/` ·
L3 `engine/`, `actions/` (gate, token). Firmware ở `targets/esp32s3/`.

### 3.3 Mười điều bất biến — đừng phá

Đây là các mệnh đề mà phần còn lại của hệ thống dựa vào. Vi phạm một trong số
này sẽ làm hỏng những thứ trông không liên quan.

1. **Thẩm định lược đồ KHÔNG đủ để kết luận một gate an toàn.** Nguyên tắc 2 là
   mệnh đề về **hai** tài liệu; JSON Schema thẩm định **một**. Cổng kiểm tra là
   `neuroedge gate lint` (phân giải), không phải thẩm định lược đồ. CI chạy lint, và
   một gate chưa phân giải được thì chưa được nạp lên thiết bị.
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
9. **Không copyleft mạnh trong phần phân phối.** Chính sách giấy phép là Q-11; ghim
   `jsonschema[format-nongpl]`; không dùng `copier` — `neuroedge new` là generator
   Python thuần (TSK-S3-07).
10. **Lệnh CLI chưa có engine phải thoát mã 2, không in "PASS" giả.** Đầu ra CLI
    bị dán vào báo cáo tiến độ như bằng chứng, và một dòng "VERIFIED" từ một lệnh chưa
    làm gì là thông tin sai cho người ra quyết định phạm vi. Bảng mã thoát: §2.3.

### 3.4 Hạng mục bị chặn — không đóng được bằng nỗ lực kỹ thuật

| Hạng mục | Chặn bởi | Cần ai | Mở ra điều gì |
|:---|:---|:---|:---|
| **TSK-S1-10** · I3 tiêu chí 1 | **Bo mạch ESP32-S3-BOX-3 vật lý** | Đặt hàng (roadmap Phụ lục B) | Kết luận kế hoạch thoại trên chip (TSK-S2-10) → I3, I5 |
| **TSK-I2-01** · I2 tiêu chí 4 | **RPi 5 cho nightly `linux`** | Đặt hàng (roadmap Phụ lục B) | Nightly trên phần cứng thật → I2 |
| **V6 — kỹ sư nhúng thứ hai** | Chưa tuyển; cần từ 2026-11-16 | Tuyển người (Q-39) | Âm thanh trên chip song song với HAL của V2 (TSK-S5-01, S5-02, S5-06, S5-07) — giả định của dự báo I5, I7 (roadmap §1.3) |
| **TSK-S3-15** · I1 tiêu chí 3 | Xác nhận golden = ba vết ghi chuẩn mực, hoặc mở RFC | Kỹ thuật trưởng | Đóng I1 |
| **`TODOS.md` #41** — repo công khai chứa gì | Quyết định của CPO | CPO, trước khi I6 mở | TSK-I6-01 → I6 (Công khai) |
| **RFC-0002** | Phê duyệt | Kỹ thuật trưởng, trước khi I11 mở | I11 và mọi board profile mới |

**TSK-S1-10 — việc còn lại sau khi có bo mạch:** vendoring `esp-sr` (AEC/AFE +
VAD) và `opus` kèm rà soát giấy phép §3.9, nạp chúng tại `TODO(TSK-S1-10, V2)`
trong `main.c`, gọi checkpoint `audio_ready`, điền báo cáo. Quy tắc quyết định
đã chốt **trước khi đo** để kết quả không bị giải thích lại: trượt bất kỳ một
ngưỡng Q-3 → **không cắt thoại** (Q-44): mở ngay một `Q-N` lập lại kế hoạch I5 và dời dự báo v1.0.

### 3.5 Việc tiếp theo

Xem **Thẻ bàn giao** ở `neuroedge-roadmap.md` §0.3 — nơi duy nhất ghi việc tiếp
theo và thứ tự làm (`CONTRIBUTING.md` §8.1). Lý do một task bị hoãn nằm ở dòng của
nó trong bảng task.

### 3.6 Nợ thiết kế đã biết

| # | Nợ | Phải giải quyết ở |
|:---:|:---|:---|
| 1 | **Hủy lệnh đang chờ mới có ở `sim` và `linux`.** Hợp đồng thu hồi lệnh vật lý (`docs/spec/voice_fsm.md` §5) yêu cầu cắt lời hủy xung chốt cửa đang chờ trong ≤ 1 khung âm thanh. `SimHAL` và `LinuxHAL` đã trả `PendingCommand.cancel()`; `esp32s3` phải hủy được thật ở tầng firmware | **TSK-S4-01** (I3), cùng lúc với hợp đồng thu hồi — không phải sau |
| 2 | `gate publish` dừng ở mã băm, chưa ký số | I10 (Registry) |
| 3 | `perception/` chỉ là khung | TSK-S3-11 (I4) |

### 3.7 Điều hệ thống chưa làm được

Nói rõ để không ai đọc các mốc đã đạt quá lên:

- ❌ **Phiên tương tác (`run`, `record`) mới có trên `sim`, gõ chữ trên terminal.** Trên `linux`
  hôm nay chỉ `replay` / `verify` (phiên tương tác: I2); giọng nói chưa có (Q-15; thoại: I4); intent không
  có action (`faq`) chỉ được trả lời khi agent khai `[system_two]`.
- ❌ **`esp32s3` mới chạy logic gate, chưa chạy agent.** Walker và sổ token C khớp engine host trên host và
  boot trên QEMU (TSK-S4-07, S4-08); thiết bị replay 3 vết ghi chuẩn mực và ghi vết ghi qua UART (TSK-S4-09). HAL
  firmware, replay vết ghi tuỳ ý và mọi thứ trên bo mạch là I3 (TSK-S4-01, S4-04); âm thanh trên chip là I5.
- ❌ **SystemOne chưa có nhà cung cấp cloud thật** (`TODOS.md` #27; đổi bằng cấu hình là TSK-I4-02). SystemTwo
  đã có LiteLLM và adapter tự viết (TSK-S2-11); CI chỉ thử bằng `mock_response`, lượt gọi bằng key thật chạy tay (`scripts/live_llm_smoke.py`).
- ❌ **Tương đương target mới ở mức quyết định, trên `sim` + `linux` + `esp32s3` trên QEMU.** `verify` so chuỗi
  phán quyết và lệnh chân; trên `esp32s3`, operation/duration của lệnh chân lấy từ bảng hành động dựng trên host
  (`TODOS.md` #37). So timing và bo mạch là TSK-S4-04 (I3).
- ❌ **`LinuxHAL` mới có `digital.out`.** `sensor.read`, `display` (I2) và `audio.in/out` (I4) trên `linux`
  chưa hiện thực; chân Pi thật cần `line_names` (vd `door_lock` → `GPIO17`).
- ❌ **MCP chỉ qua stdio** (`TODOS.md` #24, #25). Không có transport mạng.
- ❌ **Chưa phát hành ra ngoài.** Tag trước I6 là nội bộ; PyPI và repo công khai mở ở I6 (Q-39,
  TSK-S3-14, `docs/release.md`).
- ❌ **Chưa có CEL.** `allow_when` chỉ nhận dạng mapping toán tử (TSK-S2-06 hoãn, `TODOS.md` #42).
- ❌ **Chưa có số đo bộ nhớ.** Xem §3.4.

### 3.8 Bốn ràng buộc cho bản port HAL lên chip ở I3 (từ rà soát HAL)

RB-1 → RB-4 (không `malloc` trên đường âm thanh, đệm tĩnh đo được trong PSRAM,
`digital.out` hủy được trong ≤ 1 khung, bảng năng lực `const` trong flash) ở
[`docs/spec/hal_mcu_review.md`](docs/spec/hal_mcu_review.md) §2. Cả bốn vẫn hiệu lực
sau CR-1.0.

### 3.9 Thêm một fixture phản chứng

Quy trình và luật khép kín của cả ba corpus (gate, vết ghi, tool call): `CONTRIBUTING.md` §3.
