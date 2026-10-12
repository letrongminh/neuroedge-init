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
> **Nguồn sự thật về tiến độ** vẫn là [`neuroedge-roadmap.md`](roadmap/neuroedge-roadmap.md)
> §0 (bảng theo dõi và thẻ bàn giao). Tệp này kể *đã xây gì và chạy thế nào*;
> roadmap kể *còn gì phải xây*. Thứ tự ưu tiên khi lệch nhau: §3.1.

---

## 1. Nhật ký phiên bản

Mỗi task xong thêm hoặc sửa **một** mục trong `[Chưa phát hành]`, theo
`CONTRIBUTING.md` §8.2 bước 3. Khi phát hành, đổi tiêu đề thành số phiên bản và ngày
([`docs/release.md`](docs/release.md)).

Gói chưa phát hành phiên bản nào ra ngoài; trước khi công khai chỉ có tag nội bộ (Q-39), và phiên bản đầu tiên trên PyPI sẽ là `0.6.0` ở I6. Các mốc tài liệu Giai đoạn 1 được tóm tắt ở cuối phần này.

### [Chưa phát hành]

#### Đã thêm

- **Q-74 — não trên cloud tuỳ chọn, tuỷ sống tại nhà.** Người dùng chỉ cần chat: LLM worker và trò chuyện có thể chạy trên NeuroEdge Cloud, còn gate, phản xạ và kiểm lời duyệt luôn ở hộp tại nhà (Pi, add-on Home Assistant, hoặc ESP32-S3 cho một việc). Bước 1 làm hộp dễ cài (`TODOS.md` #64); bước 2 mở cloud có thuê bao sau cổng nhu cầu nếu số đo cần (`TODOS.md` #65).
- **Q-73 — mở, có minh bạch.** Người dùng tự chọn cách xác minh (kể cả đọc mã bằng giọng nói) và luồng nhiều bước; NeuroEdge không cấm, chỉ hiện rõ mức rủi ro. Giữ ba bất biến: AI không xác minh thay người, luật chạy đúng như khai, có vết ghi. RFC theo dõi ở `TODOS.md` #63.
- **Tài liệu sản phẩm và kiến trúc theo Q-72 — đủ trước khi triển khai.** PRD 1.6: định vị NeuroEdge Blueprint, maker là người dùng đầu (U1, U5, U8, U9), yêu cầu FR-MSN, FR-AGT, FR-CH, FR-EGR, FR-BP, FR-TRC-11…13, FR-CLI-13…15, NFR chi phí LLM, tiêu chí A14–A22, cổng nhu cầu B6–B8 (đảo Q-56). Roadmap thêm increment I2d (TSK-I2d-01…19) và I2e (TSK-I2e-01…11). Kiến trúc cập nhật runtime 24/7, LLM worker, duyệt qua chat, `safe_state` đối xứng và lưu trace 30 ngày.
- **Q-72 — định vị Blueprint: từ một câu nói tới một sản phẩm vật lý có AI.** Định vị ba vòng dựng (MCP), chạy (agent vận hành, trần chi phí, báo chủ động qua chat) và chia sẻ/bán (Blueprint, Hub) với maker là người dùng đầu. Duyệt qua kênh chat ghép đôi (mở rộng Q-26), khôi phục cổng nhu cầu 8 tuần (đảo Q-56), hoãn ký trace trước MVP; `safe_state` khác `off` khai trong `board.v1`.
- **Q-71 — NeuroEdge Lab qua MCP thay NeuroBrain (TSK-N0-01, TSK-N0-04).** Client MCP (Claude Code, Claude Desktop) soạn bản nháp qua tool lab; NeuroEdge chấm (`neuroedge lab check`), cưỡng chế gate/phong bì lúc chạy, người duyệt qua PR. Phân tách quyền thiết bị và kênh tin cậy theo threat model §2c; gói dự kiến `neuroedge.lab`.
- **Bộ tài liệu đợt thử đối tác (TSK-I2c-19, Q-70).** `docs/user/doi-tac/`: hướng dẫn Home Assistant qua `proxy mcp`, `neuroedge.guard` trong Python, `proxy http` trước API thiết bị; `docs/business/doi-tac/`: thỏa thuận thử nghiệm; kiểm tự động bằng `scripts/partner_guides_check.sh`.
- **Plugin Home Assistant cho cơ cấu từ xa (TSK-I2c-16 phần B, RFC-0018 §3j).** Kho `letrongminh/neuroedge-homeassistant`: entry point `neuroedge.actuators: home_assistant`, mức L1 cho switch/light/input_boolean, xác nhận trạng thái bằng polling, đạt 9/9 conformance test trên bản giả.
- **Cơ cấu chấp hành từ xa — lõi của RFC-0018 (TSK-I2c-16 phần A).** Chân `digital.out` khai ở `[actuators.<tên>]` qua plugin `neuroedge.actuators`, chỉ tới được qua `_admit`; mức tự tắt L0–L3 (hành động không hoàn tác cần ≥ L2); mất liên lạc thành `uncertain`; HAL quản lý nợ tắt; kiểm bằng `neuroedge conformance`.
- **`allow_lan_http` cho hai proxy (Q-70).** Tùy chọn `allow_lan_http = true` trong `[proxy.mcp]` / `[proxy.http]` cho phép HTTP thuần tới dải địa chỉ riêng (RFC 1918, link-local, `*.local`, `*.lan`, `*.home.arpa`) cho thiết bị mạng nội bộ.
- **`neuroedge proxy http` và `neuroedge guard init --http` (TSK-I2c-15, FR-EXT-06).** Đặt gate chặn mặc định trước API HTTP cục bộ qua `[[proxy.http.routes]]`; yêu cầu chỉ chuyển tiếp sau phán quyết ALLOW; nguồn `bridge:<id>`.
- **`neuroedge proxy mcp` và `neuroedge guard init --mcp` (TSK-I2c-14, FR-EXT-06).** Đặt gate chặn mặc định trước MCP server sẵn có qua stdio; `guard init --mcp` sinh cấu hình và hỗ trợ cấu hình Claude Desktop qua `--desktop-config`.
- **`neuroedge.guard` — lõi an toàn dùng độc lập (TSK-I2c-07, RFC-0016 §3b).** Chạy chu trình gate → token → phong bì → vết ghi độc lập không cần `agent.toml` hay `SimSession`; `Guard.load("guard.toml")`; hỗ trợ `TracePlayer` replay vết ghi.
- **Nguồn gọi theo không gian tên — TSK-I2c-10 nửa (a), RFC-0017.** Trường `source` nhận `bridge:<id>` và `mcp:<client>`; chèn dữ kiện dẫn xuất `call_channel`; cập nhật `schemas/tool-call.v1.json`.
- **Q-70 — thử riêng với một đội đối tác, không chờ bo mạch, không lên PyPI.** Thử nghiệm bộ công cụ gate (`proxy mcp`, `neuroedge.guard`, `proxy http`) trực tiếp qua wheel giao tay, đáp ứng năm điều kiện tại roadmap §4.3; thẻ bàn giao có mục tiêu mới.
- **Trang kiến trúc tổng thể cho người ngoài nhóm kỹ thuật.** Bổ sung `docs/business/kien-truc-tong-the.html` mô tả xương sống thực thi năm tầng, cập nhật ADR Q-69 và dashboard CPO (`scripts/gen_cpo_dashboard.py`).
- **I6 · TSK-I6-05 — hợp đồng cho người tích hợp trong `schemas/` (RFC-0015, Q-66).** Bốn lược đồ `tool-call.v1`, `tool-result.v1`, `error.v1`, `error-codes.v1` (17 mã lỗi `NE…`); kiểm tra khóa `schema = "neuroedge.board/v1"`.
- **I2b · TSK-I2b-03 — thư viện gate khởi đầu `gates/home/`.** Bảy gate cơ sở (`door-lock`, `light`, `valve`, `siren`, `hvac`, `camera`, `motor`) khóa trong `digests.lock`, mỗi gate có ≥ 3 phản chứng chống nới lỏng.
- **I2b · TSK-I2b-04 — `neuroedge add action|sensor|device|gate`.** Sinh `@action`, sensor, thiết bị hoặc gate chặn mặc định, kèm test hai chiều và kiểm tra hợp đồng bo mạch.
- **I2b · TSK-I2b-01, TSK-I2b-02 — năm kit phần cứng.** `villa-concierge`, `home-voice`, `factory-monitor`, `gate-camera`, `blinds`: BOM, sơ đồ Pi 5 và ESP32-S3, vết golden `fixtures/traces/kits/`, hướng dẫn `docs/user/kit-*.md`.
- **I6 · TSK-I6-05, TSK-I6-07 — phê duyệt RFC-0014 và RFC-0015 (Q-65, Q-66).** Chấp thuận hợp đồng người tích hợp vào `schemas/` (RFC-0015) và dữ kiện số từ tiến trình ngoài cùng máy (RFC-0014).
- **I2a · TSK-V1b-04 — golden suy luận và sai số `tolerance` của từng bo (RFC-0012 §3f).** Lệnh `verify` so khớp suy luận thị giác với golden theo sha256 mô hình, nhãn, IoU và sai số điểm số; lệch sinh `NE4002`.
- **I2a — `verify` phát lại agent mẫu của cả bốn gói trên `sim-rpi5` và `linux-rpi5`.** Bổ sung corpus `fine-control` (`fan-pwm`) và `motion` (`rover`) cạnh `sensor-pack` và `vision` (RFC-0013 §3f).
- **I6 · TSK-P2-04 — MCP qua mạng có xác thực: `neuroedge mcp serve --http` (Q-58, Q-32).** Streamable HTTP với mTLS (TLS 1.3) và token OAuth 2.1 ràng buộc chứng chỉ thiết bị (NFR-SEC-09, FR-CLI-12).
- **I2a · TSK-I2a-06, TSK-I2a-07 — `board.v1` khai mọi nguyên thủy mở rộng; `sim-rpi5`; `verify` chạy từng bo tham chiếu.** Khai báo `digital_in`, `i2c`, `analog_in`, `motion`, `vision_in`, `pwm`; `verify` chạy từng cặp (target, bo).
- **I2a · TSK-I2a-02, TSK-I2a-03, TSK-I2a-04 — các nguyên thủy cảm biến (RFC-0007, RFC-0009).** `digital.in` mức logic có mốc đọc; I2C chỉ đọc qua allow-list (`/dev/i2c-N`); `analog.in` đo có đơn vị vào gate bằng tiêu chí `numeric`, ngoài thang sinh `NE5001`.
- **I2a · TSK-N2-01 → TSK-N2-05 — phong bì an toàn theo chân chạy thật trên `sim` và `linux`.** Chu trình `require_pin → envelope → authorize → record`; từ chối sinh `NE1003`; tự tắt theo thời gian và giám sát write-ahead.
- **I2a · TSK-V1b-01, TSK-V1b-02, TSK-V1b-03, TSK-V1b-06, TSK-V1b-08 — gói thị giác (RFC-0012).** V4L2 Python thuần trên Linux, camera ảo trên `sim`, `VisionPipeline` (mất/cũ khung sinh BLOCK), gate mẫu `gates/vision/`, vết ghi `vision_ref` replay không cần ảnh thô.
- **I2a · TSK-W1-01, TSK-I2a-05 — PWM và chuyển động (RFC-0010, RFC-0011).** PWM bắt buộc `duration_ms`, duty lượng tử về 0; `motion.*` (motor/servo) quản lý bằng lease một lệnh, `safe_state` khi hết lease/BLOCK.
- **I2a · TSK-W1-02 — tiêu chí `numeric` và `NETR` v2 (RFC-0009).** Ngưỡng số bắt buộc `unit`, `range`, `max_age_ms`; cấu trúc nhị phân `NETR` v2 header 80 byte và bảng số 48 byte cho walker C.
- **I1 · TSK-I1-04 — NeuroEdge Studio: `neuroedge studio` (Q-51).** Bảy màn hình web cục bộ trên 127.0.0.1: phiên trực tiếp, gate what-if, vết ghi, replay, verify, ESP32-S3 (LVGL, QEMU, OTA) và cấu hình.
- **I4 · TSK-I4-01, TSK-I4-02, TSK-I4-04 — thoại thời gian thực và mô hình.** `run --mic` trực tiếp trên laptop; wake-word và STT dự phòng cục bộ; `SystemOne` đổi được bằng cấu hình qua Jev API (Q-4).
- **I7 · TSK-S6-01…TSK-S6-04 — OTA A/B có ký, tự rollback trên QEMU.** Component `ne_ota`: tải ảnh app HTTP(S), xác minh RSA-3072, chuyển khe A/B sau self-test gate; lỗi sinh `REJECTED`, tự rollback.
- **I3 · TSK-I3-01, TSK-S4-10, TSK-S4-11 — firmware ESP32-S3 và giao diện LVGL.** `build --target esp32s3` sinh dự án ESP-IDF có component `ne_agent`; 9 màn hình LVGL v9.6.0 có golden ảnh; kiểm tra RAM tĩnh ≥ 120 KB (Q-3).
- **I2 · D1, TSK-S5-09 — cảm biến và màn hình trên Linux.** Dải `bands` trong `[sim.sensor_facts]`; đọc cảm biến sysfs hwmon/IIO và xuất hiển thị framebuffer `/dev/fbN`.
- **I1 · TSK-I1-03, TSK-W0-02…TSK-W0-04, TSK-W2-07 — công cụ và chuỗi cung ứng.** CLI `--help` có ví dụ; scaffold tạo sẵn `traces/`; SBOM CycloneDX, quét lỗ hổng `pip-audit`, quét bí mật `gitleaks`, ký provenance cho wheel/sdist.
- **Giai đoạn nền tảng: Lõi thực thi, FSM thoại, MCP, HAL và CLI.** FSM thoại Python và vector tuân thủ (TSK-S3-10, TSK-S3-11, TSK-S2-07); `LinuxHAL` và phiên tương tác trên Linux (TSK-S3-05, TSK-S5-10); System 2 qua LiteLLM (TSK-S2-11); Gated Tool Profile và MCP serve stdio/UI (Q-24, TSK-S3-24, TSK-S3-27, TSK-S3-28); xác nhận `on_block: ask` (TSK-S3-26, Q-26); walker C cho `NETR` v1 và sổ token C (TSK-S4-07, TSK-S4-02); bộ công cụ `record`, `replay`, `test`, `verify`, `gate lint/resolve/explain` (TSK-S3-01…TSK-S3-07, TSK-S3-16…TSK-S3-22); bo mạch `boards/` và agent mẫu `villa-concierge`, `home-voice`, `factory-monitor` (TSK-S2-01…TSK-S2-05, TSK-S3-08).

#### Đã sửa

- **Lệnh motion không còn trễ lease vì tra tên người gọi.** `hal/digital.py::_caller` tra cứu trực tiếp từ frame (`co_filename`, `f_lineno`) thay vì `inspect.stack()`, giảm thời gian từ 28 ms xuống 0,1 ms, tránh hết hạn lease 200 ms của kit `blinds`.
- **`mcp serve` thoát có hạn sau SIGTERM/SIGHUP.** Bổ sung luồng hẹn giờ `SIGNAL_EXIT_GRACE_S = 5 s` để đóng phiên (ghi trace, thả chân) và thoát dứt điểm `os._exit`, tránh treo tiến trình.
- **Nguồn gọi (`call_source`) không còn lẫn giữa hai lời gọi chồng nhau.** Tách biệt khung dữ kiện của từng lời gọi trong `Conversation.do_with`, không ghi đè `call_source` vào dữ kiện dùng chung.
- **Phong bì an toàn ghi thời gian bật tất định.** Khử nhiễu micro giây của đồng hồ đơn điệu trước khi làm tròn lên, đảm bảo độ dài khoảng bật ghi nhận nhất quán giữa các lần chạy.
- **Bảo mật và an toàn khi vận hành.** Trang sim và studio chặn DNS rebinding bằng cách kiểm tra `Host` ở mọi yêu cầu (FR-TGT-06); loại bỏ cú pháp markdown trước khi đưa văn bản vào TTS (TSK-S3-13); sửa thiếu `ne_ui_text.c` trong component ESP-IDF; từ chối tham số số `NaN`/`±inf` trong gate (RFC-0005); xử lý số đọc cảm biến NaN thành chưa xác định (D1); escape markup Rich trong CLI tránh nuốt tên bảng TOML.

#### Đã đổi

- **Mục tiêu thẻ bàn giao (roadmap §0.3): hoàn tất mọi việc tới v1.0 không cần phần cứng hay người (2026-10-05).** Chia bốn làn thực thi: host (I2c, I2d), firmware trước khi có bo, phát hành và chuẩn bị kịch bản đo kiểm.
- **Q-69 — giả lập ngoại vi trước khi bo mạch về (2026-10-05).** Thiết lập ba spike giả lập có thời hạn: `esp-emulator` (TSK-I3-02), `esp32sim` (TSK-I3-03) và nhân kernel đầy đủ module cho `linux-hal` (TSK-I2a-08).
- **Q-68 — phê duyệt ba RFC của nền tảng mở (2026-10-04).** Chấp thuận RFC-0016, RFC-0017, RFC-0018; chốt các hằng số vận hành cơ cấu từ xa (`OFF_SLACK_MS`, `max_state_age_ms`); tách adapter Home Assistant sang kho riêng.
- **Q-67 — NeuroEdge thành lớp an toàn mở (2026-10-04).** Bổ sung increment I2c (Nền tảng mở) gồm `neuroedge.guard`, Extension SDK, proxy MCP/HTTP, cơ cấu từ xa; chuyển corpus tuân thủ sang Apache-2.0 (`LICENSING.md`).
- **Q-63 — bổ sung khoảng hở nền tảng vào I6 (2026-10-02).** Bổ sung TSK-I6-06 (bề mặt Python công khai), mở rộng TSK-I6-05 và thêm TSK-I6-07 (RFC dữ kiện từ tiến trình ngoài).
- **Q-58 → Q-62 — bề mặt tích hợp, giấy phép và mốc phát hành (2026-10-01).** Áp dụng giấy phép PolyForm Noncommercial 1.0.0 cho mã và Apache-2.0 cho chuẩn (Q-45, Q-59); lộ trình 10 mốc phát hành người dùng (roadmap §0.5); phê duyệt 6 RFC nguyên thủy mở rộng (RFC-0007, RFC-0009…0013); chọn M5Stack CoreS3 làm bo camera thứ hai (Q-61).
- **Q-56, Q-57 — ước lượng lại phạm vi MVP và quyết định câu hỏi mở RFC (2026-09-30).** Lập kế hoạch 106 task MVP (TSK-I2a-01); dời mốc cổng nhu cầu (Q-56); giải quyết câu hỏi mở của sáu RFC theo nguyên tắc an toàn tối đa (Q-57).
- **Q-52 → Q-55 — tái cấu trúc MVP = v1.0 đầy đủ (2026-09-30).** Roadmap chia bốn phase; đưa bốn gói nguyên thủy mở rộng vào MVP qua increment I2a, I3a, I2b; đưa NeuroBrain vào MVP qua I4a, I5a.
- **Đồng bộ kiến trúc, roadmap và tài liệu vận hành (2026-09-27 tới 2026-09-28).** Quy hoạch một roadmap duy nhất (Q-39); cấu trúc tài liệu MECE (mỗi sự thật một nơi); cập nhật tài liệu kiến trúc mục tiêu theo chân trời; mặc định băm dữ liệu chữ thô trong vết ghi tại nguồn (TSK-I1-01); vết ghi chuẩn mực mang `gate_digest` (RFC-0008).

#### Đã bỏ

- **Tối giản tài liệu: bỏ bản trùng, giữ một nơi cho mỗi sự thật.** Bỏ cây kiến trúc `en/`, `docs/archive/`, proposal cũ v5.9 và ba ghi chú thiết kế (Giai đoạn 2, nền tảng mở, robot FOFOCA). Phần chuẩn tắc của proposal (§4 API, Phụ lục A–C) chuyển sang `docs/spec/core_contracts.md`; bộ lọc PF-1…PF-4 vào PRD §14; ghi chú Lab thành `docs/spec/lab_mcp.md`. Roadmap, CHANGELOG và PRD §15 nén lại, không mất mã task, quyết định hay bất biến nào. Bản cũ: `git show 7626b62:<đường dẫn>`.
- **Extra `scaffold` (`copier`).** Thay thế bằng bộ sinh template Python thuần trong `neuroedge new`, loại bỏ phụ thuộc GPL3 bắc cầu.
- **Tham số `fail_closed` của `ActionContractEngine`.** Quy tắc fail-closed được xác định trực tiếp từ thuộc tính `fail: open` của gate; lỗi luôn trả về phán quyết chặn.

### Mốc tài liệu Giai đoạn 1

Giai đoạn 1 (2026-09-21 tới 2026-09-23) đóng băng ba lược đồ lõi (`gate.v1`, `trace.v1`, `board.v1`), hiện thực lõi phân giải gate (`gate_resolver.py`), cơ chế kế thừa an toàn theo RFC-0001 và RFC-0004, chốt các quyết định nền tảng (Q-1 tới Q-20) và chuyển định hướng cloud-first (CR-1.0). Toàn bộ chi tiết quá trình và biên bản rà soát lưu tại lịch sử git (`git show 7626b62:CHANGELOG.md`).

---

## 2. Cách vận hành

### 2.1 Dựng môi trường

Yêu cầu **Python 3.11+** (dùng `tomllib` của thư viện chuẩn, không phụ thuộc TOML bên ngoài).

```bash
cd python
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q          # kỳ vọng: 0 failed, 0 skipped
```

Bản dựng tái lập được (roadmap §3.9):

```bash
.venv/bin/python -m pip install -r requirements-lock.txt
```

Tùy chọn: System 2 với model thật cài `.venv/bin/python -m pip install -e '.[cloud]'`, cấu hình `[system_two]` trong `agent.toml` và xuất API key tương ứng. System 1 với Jev qua cấu hình `[system_one]` và `OPENROUTER_API_KEY`.

### 2.2 Kiểm tra nhanh toàn bộ artifact

Các lệnh chạy tại **gốc kho** (`paths.py` tự định vị gốc monorepo):

```bash
V=python/.venv/bin

$V/neuroedge verify                      # kỳ vọng: mọi gate phân giải, trace thẩm định, tool corpus khớp, replay khớp; 0 artifact ⇒ NE4004 (mã 1)
$V/neuroedge gate lint                   # kỳ vọng: ✓ mọi gate resolved, mã 0
$V/neuroedge trace validate fixtures/traces/*.json   # kỳ vọng: mỗi tệp VALID
$V/neuroedge board list                  # kỳ vọng: liệt kê các profile trong boards/
python3 scripts/gen_cpo_dashboard.py     # sinh lại dashboard CPO (docs/business/cpo-dashboard.html) sau khi đổi nguồn
$V/python scripts/check_digests.py --check   # kỳ vọng: ✓ các tệp khớp digests.lock
```

Khẳng định nghịch đảo — corpus phản chứng **phải** tiếp tục thất bại:

```bash
$V/neuroedge gate lint fixtures/gates/invalid --registry fixtures/gates/registry
# kỳ vọng: mọi tệp trong invalid/ đều failed to resolve · mã thoát 1
```

### 2.3 Tham chiếu lệnh CLI

**Hợp đồng mã thoát** — CI và Action CI đều neo vào nó:

| Mã | Nghĩa |
|:---:|:---|
| `0` | Phép kiểm tra đã chạy và **đạt** |
| `1` | Phép kiểm tra đã chạy và **không đạt** |
| `2` | Lệnh (hoặc `--target` đó của lệnh) **chưa được hiện thực** |

Mã `2` tách biệt với `1` để CI phân biệt "hỏng" và "chưa có". Hiện tại thoát mã 2: `run` / `mcp serve --target esp32s3` (TSK-S4-01), `run` / `mcp serve --ui --target linux`, `run` / `record --voice-file` cùng `--ui`, `replay --target esp32s3` (TSK-S4-04). Target lạ là lỗi (mã 1).

Mọi lệnh nạp gate nhận `--registry <dir>` (`-r`), mặc định `gates/`. `--agent` mặc định `./agent.toml` hoặc agent mẫu `villa-concierge`.

| Lệnh | Chức năng chính |
|:---|:---|
| `gate resolve <tệp\|URI>` | Phân giải chuỗi `extends`, in chính sách hiệu dụng và mã băm. `--json` cho máy đọc |
| `gate lint [dir]` | Phân giải mọi gate trong thư mục (mặc định `gates/`, `--registry`) |
| `gate publish <tệp>` | Chuẩn hóa RFC 8785 và in mã băm SHA-256 (dừng ở mã băm, chưa ký số) |
| `gate add <URI>` | Thêm gate từ registry và phân tích ràng buộc kế thừa |
| `gate explain <tệp\|URI>` | Giải thích gate cho người duyệt (tiêu chí, mệnh đề siết chặt, ngân sách, `on_block`) |
| `trace validate <tệp…>` | Thẩm định vết ghi theo lược đồ `trace.v1.json` |
| `trace show <tệp>` | In dòng thời gian sự kiện của vết ghi |
| `trace view <tệp>` | Xuất HTML tự chứa trực quan hóa thiết bị, cảm biến, phán quyết và thanh tua |
| `trace export <tệp>` | Xuất định dạng Chrome Trace Event cho Perfetto (`--format chrome`) |
| `board list` / `board show <id>` | Liệt kê hoặc xem chi tiết năng lực bo mạch và nguyên thủy hỗ trợ |
| `verify [--targets t]` | Kiểm tra toàn diện: gate, tool corpus, trace chuẩn mực và replay trên từng target |
| `build --target <t>` | Đối chiếu năng lực agent ↔ bo mạch, biên dịch gate ra cây `NETR` và sinh firmware ESP-IDF |
| `replay <tệp> [--target t]` | Tính lại phán quyết và lệnh chân trên HAL thật rồi so khớp với golden |
| `record [--target t]` | Ghi phiên tương tác ra vết ghi đã thẩm định; mặc định băm dữ liệu chữ thô (`--raw` giữ nguyên) |
| `test [thư-mục]` | Chạy bộ Action CI (pytest) của agent |
| `run [--target t]` | REPL tương tác dòng lệnh (`-c` một lệnh, `--ui` web cục bộ, `--voice-file`, `--mic`) |
| `mcp tools` | Xuất schema của các `@action` cho MCP hoặc function-calling OpenAI |
| `mcp serve` | Máy chủ MCP qua stdio hoặc mạng (`--http` mTLS/OAuth 2.1) trên `sim` hoặc `linux` |
| `mcp desktop-config` | Tạo hoặc ghi cấu hình kết nối cho Claude Desktop (`--write`) |
| `new <tên> [--template T]` | Sinh khung dự án mới từ mẫu (`minimal`, `villa-concierge`, `home-voice`, v.v.) |
| `add action\|sensor\|device\|gate` | Sinh thành phần mã kèm gate chặn mặc định và kiểm thử hai chiều |

`python -m neuroedge …` tương đương `neuroedge …`. Hướng dẫn chi tiết từng lệnh và ví dụ sử dụng xem tại [`docs/user/huong-dan.md`](docs/user/huong-dan.md).

### 2.4 Đọc một thông báo lỗi

Mọi lỗi có đúng ba phần (FR-DX-04): **ở đâu** (`where`) · **vì sao** (`why`) · **cách xử lý** (`fix`). Lỗi kế thừa có thêm dòng `rule` chỉ ra nguyên tắc vi phạm.

```
[NE2003] loosens-level@1.0.0 (fixtures/gates/invalid/loosens_level.yaml) -> allow_when.risk_level
  why: loosens the inherited condition: base admits {low}, this gate admits {high, low, medium}
  rule: Appendix B.5 principle 2
  fix: narrow allow_when.risk_level to a subset of the base condition (base clause: {'lte': 'low'}), …
```

Danh mục mã `NE…`, phân lớp lỗi và ngữ cảnh xuất hiện xem tại PRD [Phụ lục B](roadmap/neuroedge-prd.md#phụ-lục-b--danh-mục-mã-lỗi-chuẩn).

### 2.5 CI

Danh sách workflow và job trong hệ thống tích hợp liên tục:

| Workflow | Khi nào | Job |
|:---|:---|:---|
| `ci-sim-linux.yml` | Mỗi PR và push lên `main` | `frozen-artifacts` · `tests` (Python 3.11/3.12/3.13) · `linux-hal` · `wheel-smoke` · `lint` · `licence-obligations` · `cloud-extra` · `ui-golden` (LVGL trên host, TSK-S4-10) |
| `firmware-qemu.yml` | PR/push chạm mã nguồn firmware (`targets/**`), bộ sinh, kịch bản hoặc hằng đêm | `firmware-qemu` (boot ESP-IDF 5.4 trên Espressif QEMU) · `firmware-size` (kiểm tra ngân sách flash, SRAM Q-3) · `ota-rollback` (pha a–g, RSA-3072) · `agent-firmware` (build và boot firmware của agent) · `uart-trace` (đọc UART, validate và verify) |
| `release-pypi.yml` | Tag `v*.*.*` hoặc chạy thủ công | `build` · `sbom` · `smoke` · `attest` · `publish-testpypi` · `publish-pypi` · `github-release` (quy trình tại [`docs/release.md`](docs/release.md)) |
| `nightly-hardware.yml` | Hằng đêm hoặc chạy thủ công | `firmware-build` (ESP-IDF 5.2.1) · `upstream-drift` · `drift-issue` · `memory-spike` · `report` |
| `security.yml` | Mỗi PR/push, hằng tuần hoặc chạy thủ công | `pip-audit` · `gitleaks` (toàn lịch sử) · `actionlint` · `codeql` (Python, Actions) · `firmware-changed` + `codeql-c` |

Năm cổng CI bắt buộc xanh trước khi hợp nhất:
- **Cổng chặn test skip:** Thất bại nếu có bất kỳ test nào bị skip (`CONTRIBUTING.md` §5).
- **Khẳng định nghịch đảo:** Toàn bộ corpus phản chứng phải tiếp tục thất bại đúng mã 1 (§2.2).
- **`digests.lock`:** Thay đổi gate chuẩn mực mà không qua RFC sẽ làm đỏ build (`CONTRIBUTING.md` §3).
- **Cổng giấy phép:** `licence-obligations` kiểm tra toàn bộ cây phụ thuộc lõi; `cloud-extra` kiểm tra chính sách Q-11.
- **Kiểm tra định dạng:** `ruff check .` và `ruff format --check .` trong job `lint`.

### 2.6 Firmware (khi đã có bo mạch)

Hướng dẫn nạp firmware cho agent xem tại [`docs/user/nap-firmware.md`](docs/user/nap-firmware.md). Xây dựng firmware mẫu `home-voice` trên thiết bị:

```bash
cd targets/esp32s3
idf.py set-target esp32s3
idf.py build
idf.py size --format json2 --output-file build/size.json
idf.py size-components --format json2 --output-file build/size-components.json
python ../../scripts/check_firmware_size.py build/neuroedge-esp32s3-box3.bin \
  --size-json build/size.json --components-json build/size-components.json   # ngân sách Q-3
idf.py -p /dev/ttyUSB0 flash monitor
```

Tìm dòng `NEUROEDGE_MEMORY_JSON` trong đầu ra monitor để ghi nhận số đo vào `docs/reports/memory_spike_report.md`. Khi chưa có bo mạch thật, walker C chạy trên host (`make -C targets/esp32s3/components/ne_gate check-static`) và firmware boot trên QEMU theo `firmware-qemu.yml`.

---

## 3. Bàn giao ngữ cảnh sản phẩm

Mục này dành cho người hoặc AI agent tiếp quản dự án để tiếp tục phát triển mà không phải đọc lại toàn bộ tài liệu gốc.

### 3.1 Các tài liệu là nguồn sự thật

Bản đồ "đọc gì khi nào" cho người hoặc agent tiếp quản:

| Tài liệu | Nội dung chính | Khi nào đọc |
|:---|:---|:---|
| [`neuroedge-roadmap.md`](roadmap/neuroedge-roadmap.md) | **Nguồn sự thật duy nhất về tiến độ:** bốn phase (§0.5), increment I0–I18, trạng thái task, tiêu chí ra, phụ thuộc, thẻ bàn giao (§0.3). | **Luôn đọc trước** |
| [`neuroedge-prd.md`](roadmap/neuroedge-prd.md) | Yêu cầu `FR-*` / `NFR-*`, **§15 là sổ quyết định duy nhất** (`Q-N`), Phụ lục B danh mục mã lỗi `NE…`. | Khi cần biết *phải làm gì* và đã chốt gì |
| [`docs/architecture/`](docs/architecture/README.md) · [`core_contracts.md`](docs/spec/core_contracts.md) | Kiến trúc hiện hành và mục tiêu; đặc tả API, gate (Phụ lục B), HAL, vết ghi. | Khi cần biết *tại sao* và *định dạng gì* |
| [`TODOS.md`](TODOS.md) | Danh mục việc hoãn có chủ ý kèm mốc kích hoạt rõ ràng. | Trước khi đề xuất việc "còn thiếu" |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Quy ước đóng góp; §3 việc cần RFC; §6 cấu trúc kho; §8 các bước hoàn tất task. | Trước khi sửa mã hoặc cấu trúc |
| [`docs/spec/`](docs/spec/) | Đặc tả chuẩn tắc: hợp đồng nền (`core_contracts.md`), Gated Tool Profile, threat model, NeuroEdge Lab (`lab_mcp.md`), FSM hội thoại, phủ mô phỏng, MCU review. | Khi thay đổi hành vi tầng tương ứng |

Tài liệu đã xoá khi tối giản (proposal cũ, ghi chú thiết kế, `docs/archive/`, kiến trúc `en/`): `git show 7626b62:<đường dẫn>`.

**Thứ tự ưu tiên khi lệch nhau:** PRD (yêu cầu, quyết định) và `schemas/` + RFC đã chấp thuận → roadmap (tiến độ, lịch) → kiến trúc và `docs/spec/` → mã nguồn → tệp này. Nếu mã lệch hợp đồng, mã sai. Tài liệu thiết kế nói gì về lịch, trạng thái hay tiêu chí ra thì roadmap đúng (R1).

### 3.2 Bản đồ kiến trúc — cái gì ở đâu

Cấu trúc chi tiết của kho mã nguồn xem tại `CONTRIBUTING.md` §6. Bốn tầng thực thi chính:
- **L0:** `python/neuroedge/sim/` — phiên mô phỏng, CLI, giao diện web cục bộ.
- **L1:** `python/neuroedge/hal/` — lớp trừu tượng phần cứng (năm nguyên thủy lõi và mở rộng).
- **L2:** `python/neuroedge/models/`, `perception/` — FSM hội thoại, phân loại ý định, adapter LLM/STT/TTS.
- **L3:** `python/neuroedge/engine/`, `actions/` — thẩm định gate, quản lý token, thực thi action có hợp đồng.
- **Firmware:** `targets/esp32s3/` — walker C, sổ token C và logic khởi động trên chip.

### 3.3 Mười điều bất biến — đừng phá

1. **Thẩm định lược đồ KHÔNG đủ để kết luận một gate an toàn.** JSON Schema chỉ kiểm tra một tài liệu; cổng kiểm tra an toàn là `neuroedge gate lint` (phân giải chuỗi kế thừa). Gate chưa phân giải không được nạp lên thiết bị.
2. **Fail-closed là mặc định ở mọi hướng.** Vắng `fail` → `closed`. Gate cha `fail: open` và con im lặng → `closed`. Không đo được → `INCONCLUSIVE`. Lệnh luôn fail-closed; khi suy giảm, cơ cấu về `safe_state` khai trong `board.v1` (mặc định `off`, Q-72).
3. **`allow_when` dạng chuỗi CEL không được xuất hiện trong chuỗi kế thừa.** Không chứng minh được tính siết chặt đơn điệu thì phải từ chối.
4. **Phân giải gate là hàm thuần khiết.** Không phụ thuộc đồng hồ, mạng hay tính ngẫu nhiên, đảm bảo `neuroedge verify` cho cùng kết quả trên mọi target.
5. **Không có bộ lượng giá CEL nào trên vi điều khiển (Q-9 phương án A).** Host biên dịch gate sang cây nhị phân `NETR` (RFC-0003, RFC-0009); firmware chỉ duyệt cây qua walker C99.
6. **Bo tham chiếu mặc định của `esp32s3` là ESP32-S3-BOX-3; bo tham chiếu thứ hai (có camera) là M5Stack CoreS3 (RFC-0013, Q-61).** Không đổi sang DevKitC để số đo kiểm tra bộ nhớ có giá trị thực tế.
7. **Mỗi profile `sim` không được giàu năng lực hơn bo mạch nó soi (`SIM_MIRRORS`, RFC-0013).** Đảm bảo tính tương đương giữa mô phỏng và phần cứng thật.
8. **Đuôi vết ghi là `.json` mang `$schema`.** Không đổi sang định dạng nhị phân đóng như `.ntrace`.
9. **Không copyleft mạnh trong phần phân phối.** Tuân thủ chính sách giấy phép Q-11; ghim `jsonschema[format-nongpl]`; `neuroedge new` dùng generator Python thuần (TSK-S3-07), không dùng `copier`.
10. **Lệnh CLI chưa có engine phải thoát mã 2, không in "PASS" giả.** Bắt buộc tuân thủ hợp đồng mã thoát (0: đạt, 1: không đạt, 2: chưa hiện thực) để bảo đảm tính trung thực của báo cáo CI và tiến độ.

### 3.4 Hạng mục bị chặn — không đóng được bằng nỗ lực kỹ thuật

| Hạng mục | Chặn bởi | Cần ai | Mở ra điều gì |
|:---|:---|:---|:---|
| **TSK-S1-10** (I3 tiêu chí 1) | Bo mạch ESP32-S3-BOX-3 | Mua phần cứng | Đo kiểm thoại trên chip → I3, I5 |
| **TSK-I2-01** (I2 tiêu chí 4) | RPi 5 cho nightly `linux` | Mua phần cứng | Nightly trên phần cứng thật → I2 |
| **V6 — kỹ sư nhúng thứ hai** | Chưa có người | Tuyển dụng (Q-39) | Âm thanh song song với HAL (TSK-S5-01…07) → I5, I7 |
| **`TODOS.md` #43** (CLA) | Chưa có văn bản CLA | Pháp lý / CPO | Nhận đóng góp PR từ bên ngoài (Q-45) |
| **I2b tiêu chí 2** | Cần người đo TTFV | Người đo (Q-60) | Đóng tiêu chí nghiệm thu I2b |
| **`TODOS.md` #59** | Cần phần cứng thật dựng kit | Mua kit và lắp đặt | Kiểm tra BOM và sơ đồ 5 kit I2b |
| **I6 tiêu chí 7** | Cần hai máy thử MCP mạng | Người thực hiện (Q-60) | Đóng tiêu chí MCP qua mạng |

**TSK-S1-10 sau khi có bo:** vendoring `esp-sr` (AEC/AFE + VAD) và `opus` kèm rà soát giấy phép, nạp tại `TODO(TSK-S1-10, V2)` trong `main.c`, điền báo cáo. Quy tắc đã chốt trước khi đo: trượt bất kỳ ngưỡng Q-3 nào thì **không cắt thoại** (Q-44) — mở một `Q-N` lập lại kế hoạch I5 và dời dự báo v1.0.

### 3.5 Việc tiếp theo

Xem Thẻ bàn giao tại [`neuroedge-roadmap.md`](roadmap/neuroedge-roadmap.md) §0.3 — nơi duy nhất theo dõi việc tiếp theo và thứ tự thực hiện (`CONTRIBUTING.md` §8.1).

### 3.6 Nợ thiết kế đã biết

| # | Nợ thiết kế | Cần giải quyết tại |
|:---:|:---|:---|
| 1 | Hủy lệnh đang chờ mới hỗ trợ trên `sim` và `linux`; `esp32s3` cần hủy được ở tầng firmware (`voice_fsm.md` §5). | **TSK-S4-01** (I3) |
| 2 | `gate publish` dừng ở mã băm JCS SHA-256, chưa ký số mật mã. | I10 (Registry) |

### 3.7 Điều hệ thống chưa làm được

- Phiên tương tác mới hỗ trợ nhập văn bản terminal trên `sim` và `linux` (chưa có GUI web cho Linux).
- Giọng nói chạy từ tệp WAV trên `sim`/`linux`; micro trực tiếp (`run --mic`) mới có trên laptop; mô hình wake-word do người dùng tự cung cấp.
- ESP32-S3 mới chạy walker gate và self-test trên QEMU, chưa điều khiển chân GPIO thực tế.
- Model cloud trong CI chỉ chạy qua mock/transport giả; lượt gọi key thật phải chạy thủ công.
- Tương đương target mới ở mức phán quyết và lệnh chân; chưa so khớp độ trễ thời gian thực.
- Nguyên thủy mở rộng kiểm thử trên kernel ảo Linux trong CI (`gpio-sim`, `i2c-stub`, `vivid`), chưa kiểm trên bo mạch thật.
- Chưa mở công khai trên PyPI (dự kiến phiên bản `0.6.0` tại I6; trước đó chỉ phát hành tag nội bộ và wheel giao trực tiếp).
- Chưa hỗ trợ biểu thức CEL trong `allow_when` (`TODOS.md` #42).

### 3.8 Bốn ràng buộc cho bản port HAL lên chip ở I3

Bốn ràng buộc RB-1 → RB-4 (không `malloc` trên đường âm thanh, đệm tĩnh đo được trong PSRAM, `digital.out` hủy được trong ≤ 1 khung âm thanh, bảng năng lực `const` trong flash) quy định tại [`docs/spec/hal_mcu_review.md`](docs/spec/hal_mcu_review.md) §2 tiếp tục có hiệu lực.

### 3.9 Thêm một fixture phản chứng

Quy trình và nguyên tắc khép kín hai chiều của các bộ corpus phản chứng (gate, vết ghi, tool call) quy định tại [`CONTRIBUTING.md`](CONTRIBUTING.md) §3.
