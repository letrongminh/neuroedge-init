# 02 · Container và ranh giới tiến trình (C4 L2)

> **Phạm vi:** các khối chạy độc lập — tiến trình, thư viện, firmware, kho tệp — và cách từng cặp
> nói chuyện. **Nguồn:** `python/pyproject.toml`, `python/neuroedge/cli/`, `sim/ui.py`,
> `mcp_server.py`, `targets/esp32s3/`, `.github/workflows/`.

## 1. Sơ đồ container

![E-02 · Container](../assets/svg/E-02-containers.svg)
*Hình E-02 — Container trên máy dev hoặc thiết bị Linux (trên), trên chip (dưới), và hệ thống ngoài (phải). Khối nét đứt mang nhãn I2d, I2e, Q-72 là thiết kế đích của [Q-72](../../../roadmap/neuroedge-prd.md#15-sổ-quyết-định) (`planned · Q-72`): runtime 24/7, LLM worker, nền tảng chat, Hub index, relay; LLM worker có thể chạy trên NeuroEdge Cloud tuỳ chọn (Q-74, I2f, [`15`](15-target-architecture.md) §6.10).*

## 2. Danh mục container

| Container | Công nghệ | Trách nhiệm | Điểm vào | Trạng thái |
|:---|:---|:---|:---|:---|
| **CLI `neuroedge`** | Python 3.11+, Typer, Rich | Mỗi lệnh là một tiến trình: nạp phiên, chuyển lỗi thành thông báo ba phần và mã thoát; không tự quyết gate | `neuroedge.cli.main:app` | `done` |
| **Thư viện `neuroedge`** | Python (mã lõi source-available — Q-45); phụ thuộc lõi: `pydantic`, `jsonschema`, `pyyaml`, `rfc8785`, `deepdiff`, `typer`, `rich` | Toàn bộ logic: engine gate, action, HAL, model, thoại, phiên, Action CI | `import neuroedge` | `done` |
| **Web UI của phiên** | `http.server.ThreadingHTTPServer` của thư viện chuẩn, chỉ trên 127.0.0.1 | Hiện thiết bị ảo, dòng phán quyết; nhận lệnh gõ và nút xác nhận của người có mặt | `run --ui`, `mcp serve --ui` | `done` (chỉ `sim`) |
| **Máy chủ MCP** | MCP Python SDK (extra `mcp`), stdio | Đưa mỗi `@action` ra làm công cụ; mọi `tools/call` qua gate | `neuroedge mcp serve` | `done` |
| **Tệp** | Hệ tệp cục bộ | Dự án agent (`agent.toml`, `commands.toml`, `knowledge.toml`, `gates/`, `actions/`, `traces/`); dữ liệu kho (`schemas/`, `gates/`, `boards/`, `fixtures/`, `digests.lock`) | — | `done` |
| **Đầu ra build** | Hệ tệp | `build/gates/` (cây JSON, artifact gate, `NETR`, header C); `build/esp32s3/` (project ESP-IDF đầy đủ) | `neuroedge build` | `done` |
| **Thiết bị Linux** | Kernel Linux: libgpiod v2, sysfs hwmon/IIO, framebuffer, PipeWire | Chân, cảm biến, màn hình, âm thanh thật cho `LinuxHAL` | `--target linux` | `partial` — đã kiểm trên phần cứng ảo, chưa trên Pi |
| **Ảnh firmware** | C99, ESP-IDF v5.4 | Walker `NETR`, sổ token, bảng của agent, vết ghi UART, OTA; tự kiểm lúc khởi động | `app_main` | `partial` — chạy trên QEMU, chưa điều khiển chân |
| **Flash** | 16 MB, bảng phân vùng `partitions.csv` | `factory`, `ota_0`, `ota_1` (mỗi khe 3,5 MB); `nvs`, `otadata`, `phy_init`, `storage` | — | `done` |
| **Fleet OS, Gate Registry** | Chưa chọn đủ; đã chốt Eclipse Hawkbit (Q-11), ORAS và Harbor | Quản trị đội thiết bị; kho gate có ký | — | `planned` (I9, I10) |
| **Runtime 24/7** (máy nhà) | Python, dịch vụ systemd | Tiến trình tin cậy duy nhất giữ HAL và quyền GPIO: gate, thực thi hợp đồng nhiệm vụ, lập lịch, bộ phát hiện tất định, `llm_budget`, adapter kênh chat và kiểm bản ghi duyệt, cửa ra dữ liệu (egress), vết ghi theo đoạn | chưa có | `planned · Q-72` (I2d) |
| **LLM worker** (máy nhà) | Python, LiteLLM; user hệ điều hành riêng | Tiến trình không tin cậy: giữ key BYOK, giải thích, đề xuất, viết báo cáo; gọi runtime như một client MCP cục bộ; không bao giờ duyệt | chưa có | `planned · Q-72` (I2d) |

## 3. Mô hình tiến trình và luồng

**Hôm nay**, NeuroEdge không có tiến trình nền nào chạy mãi. Mọi thứ sống trong tiến trình của lệnh
đang chạy. *Sẽ đổi theo Q-72 (`planned · Q-72`, I2d):* agent vận hành thêm hai tiến trình sống lâu trên
máy nhà (hai dòng cuối của bảng).

| Tình huống | Tiến trình | Luồng và vòng lặp sự kiện | Trạng thái |
|:---|:---|:---|:---|
| `run -c`, `run` (REPL), `record` | Một tiến trình `neuroedge` | Mỗi lượt một vòng lặp `asyncio` mới (`asyncio.run(session.handle(text))`) | hôm nay |
| `run --ui` | Như trên, cộng máy chủ HTTP | Luồng HTTP của `ThreadingHTTPServer`; mỗi lượt chạy dưới một khoá chung; SSE đẩy trạng thái khi đổi hoặc mỗi 1 giây | hôm nay |
| `mcp serve` | Tiến trình con do client MCP khởi động | Một vòng lặp `anyio`; khoá `turns` bảo đảm mỗi lần một lời gọi | hôm nay |
| `mcp serve --ui` | Như trên, cộng trang web | Lời gọi MCP và lượt trên trang dùng chung một phiên và một khoá | hôm nay |
| `--target linux` | Như trên | Xung GPIO có thời lượng được thả bằng `threading.Timer`; SIGTERM/SIGHUP đưa mọi line về nghỉ trước khi thoát | hôm nay |
| Firmware | Một task `app_main` | Không tạo task FreeRTOS nào; mọi bước khởi động chạy tuần tự ([`04`](04-component-device-c4l3.md) §3) | hôm nay |
| **Runtime 24/7** (tin cậy) | Một dịch vụ systemd trên máy nhà (Pi, mini PC, NAS), khởi động lại khi chết | Một vòng lặp sự kiện dài: lập lịch, bộ phát hiện, adapter chat, máy chủ MCP cục bộ cho worker; một khoá lượt như `mcp serve`. Thời lượng, hạn duyệt, watchdog dùng đồng hồ đơn điệu; giờ tường mang trạng thái `unsynced` cho tới khi đồng bộ | `planned · Q-72` (I2d) |
| **LLM worker** (không tin cậy) | Tiến trình riêng, user hệ điều hành riêng; runtime giám sát và khởi động lại | Gọi runtime qua MCP cục bộ; nguồn do runtime gán theo kết nối; mạng chỉ tới endpoint provider đã khai | `planned · Q-72` (I2d) |

Hai tiến trình dùng lại ranh giới Q-71: chỉ một tiến trình giữ HAL, client MCP là bên không tin cậy.
Worker bị prompt injection vẫn chỉ gửi được lời gọi phải qua gate, không chạm được key bot, bảng lời
duyệt hay HAL. Worker chết thì runtime vẫn phản xạ, chạy bộ phát hiện, gửi cảnh báo mẫu cứng và khởi
động lại worker ([`06`](06-runtime-flows.md)). Quyết định: [Q-72](../../../roadmap/neuroedge-prd.md#15-sổ-quyết-định).

Hệ quả hôm nay: kết nối MCP tới server bên ngoài chỉ sống trong một lượt (`TODOS.md` #25), và một bus
I2C kẹt có thể giữ vòng lặp khoảng một giây (`TODOS.md` #48). Với runtime 24/7 (`planned · Q-72`), cả
hai thành rủi ro thật: runtime chạy một vòng lặp dài là đúng mốc kích hoạt của #25, và bộ phát hiện đọc
cảm biến theo chu kỳ trên cùng vòng lặp làm một bus kẹt trễ cả phản xạ lẫn lời duyệt (#48). Cả hai phải
xử lý trước khi runtime 24/7 chạy trên phần cứng thật.

## 4. Ma trận giao tiếp

Chỉ ghi những gì có trong mã. Không có ngân sách độ trễ nào ở đây được đo; ngưỡng độ trễ là NFR
(PRD §9.1) và trạng thái đo của chúng ở [PRD §9](../../../roadmap/neuroedge-prd.md#9-yêu-cầu-phi-chức-năng).

| Nguồn → Đích | Kênh | Định dạng | Kiểm soát |
|:---|:---|:---|:---|
| CLI → thư viện | Gọi hàm trong tiến trình | Đối tượng Python | — |
| Trình duyệt ↔ web UI | HTTP trên 127.0.0.1: `GET /events` (Server-Sent Events), `GET /state`, `POST /command`, `POST /confirm` | JSON; thân tối đa 4096 byte | `Host` và `Origin` phải là 127.0.0.1 hoặc localhost đúng cổng, không thì 403 |
| Client MCP → máy chủ MCP | stdin/stdout của tiến trình con | JSON-RPC (MCP); kết quả có `outputSchema` | Mọi lời gọi mang nguồn `mcp` và qua gate; `BLOCK` không phải lỗi, `REJECTED` là lỗi |
| Thư viện → LLM | HTTPS (LiteLLM) | Chat completions chuẩn OpenAI | Khoá chỉ đọc từ biến môi trường; không bao giờ vào vết ghi |
| Thư viện → Jev | HTTPS, `POST {api_base}/systemone` | JSON: `model`, `state.utterance`, `questions` | HTTPS bắt buộc trừ loopback; chỉ gửi lời người nói; client thư viện chuẩn (`net.py`): không theo redirect, không qua proxy, có hạn chót |
| Thư viện → STT/TTS | HTTPS hoặc `http://localhost` | Audio API chuẩn OpenAI | `http://` tới máy khác mà có khoá ⇒ build từ chối; cùng client `net.py` |
| Thư viện → thiết bị Linux | Ký tự thiết bị `/dev/gpiochipN`, sysfs, `/dev/fbN`, PortAudio | libgpiod v2, tệp văn bản, điểm ảnh | Line được tìm theo **tên**; thiếu thiết bị ⇒ lỗi trước khi giữ line nào |
| Thư viện → đầu ra build → ảnh firmware | `idf.py build` đọc project sinh ra | C, header `.netree.h`, `version.txt` | Build lỗi ⇒ in mọi vấn đề, không ghi tệp nào |
| Ảnh firmware → thư viện | UART (tệp log, `tcp://`, cổng serial) | Dòng `NE1 {…}` ≤ 512 byte, khung `device_info` … `trace_end` | Dòng hỏng, thiếu khung, đếm lệch ⇒ `NE4001`, không ghi gì |
| Ảnh firmware → máy chủ OTA | HTTP(S) GET | Ảnh app ký RSA-3072 | Không theo redirect; hạn chót tải; sai chữ ký ⇒ xoá khe vừa ghi |
| Ảnh firmware → Fleet OS | MQTT | — | `planned` (I9) — xem [`15`](15-target-architecture.md) §3.1 |
| Ảnh firmware ↔ nhà cung cấp (provider) *(planned)* | WebSocket (TLS 1.3) | Opus (âm thanh 16 kHz nhị phân) và JSON (sự kiện/kết quả) ([`neuroedge-prd.md`](../../../roadmap/neuroedge-prd.md) Phụ lục D.2) | Điểm kết thúc luồng âm thanh tối ưu cho MCU (FR-GW-04, TSK-S5-06); hạn mức theo thiết bị là tuỳ chọn của lớp provider (FR-GW-05, v1.1) — xem [`15`](15-target-architecture.md) §2.3 |
| LLM worker → runtime *(`planned · Q-72`, I2d)* | MCP cục bộ (stdio hoặc socket cục bộ) | JSON-RPC (MCP) | Nguồn do runtime gán theo kết nối, không do worker khai; mọi lời gọi qua gate; worker không có tool trả lời `ask` hay duyệt |
| LLM worker → nhà cung cấp LLM *(`planned · Q-72`, I2d)* | HTTPS (LiteLLM) | Chat completions chuẩn OpenAI | Key BYOK chỉ trong worker; mạng của worker chặn ở mức hệ điều hành, chỉ tới endpoint provider đã khai |
| Runtime → nền tảng chat (Telegram trước) *(`planned · Q-72`, I2d)* | HTTPS, API bot | Tin nhắn, yêu cầu duyệt `{id, nonce, hạn, digest, bản duyệt}` | Token bot chỉ trong runtime; chỉ gửi tới chat đã ghép đôi; chat sập ⇒ hàng đợi có hạn và cảnh báo tại chỗ trên UI |
| Runtime ↔ relay *(`planned · Q-72`, tuỳ chọn)* | TCP ra ngoài do máy nhà mở; TLS xuyên | Byte TLS; relay chọn đích theo SNI | Relay không giải mã; sao lưu vết ghi mã hoá phía máy nhà; lời duyệt không qua relay; relay mất ⇒ không ảnh hưởng an toàn |
| CLI → Hub index và nguồn Blueprint *(`planned · Q-72`, I2e)* | HTTPS hoặc git | Index tĩnh (URL, digest), gói NeuroEdge Blueprint | Digest phủ toàn gói; lệch ⇒ từ chối cài; gate trong gói vẫn qua `gate lint` |
| Client MCP ↔ máy chủ MCP qua mạng *(mặc định tắt: `mcp serve --http`)* | Streamable HTTP (TLS 1.3) | JSON-RPC (MCP) | OAuth 2.1 (Protected Resource Metadata RFC 9728, RFC 8414) sau mTLS (TSK-P2-04, Q-32) — xem [`15`](15-target-architecture.md) §4.3 |

## 5. Container quy hoạch

Chỉ ghi công nghệ mà tài liệu quy hoạch đã nêu; mọi thứ khác là "chưa chọn".

| Container | Increment | Công nghệ đã nêu | Chưa chọn | Nguồn | Kiến trúc đích |
|:---|:---:|:---|:---|:---|:---|
| **Fleet OS** | I9 | Eclipse Hawkbit cho chiến dịch OTA theo đợt; broker MQTT giấy phép dễ dãi (Mosquitto, NanoMQ hoặc VerneMQ, chọn bằng đo tải); FastAPI WebSockets cho kết nối và viễn trắc; âm thanh không đi qua Fleet OS mà kết thúc ở lớp provider tự vận hành (Q-47, FR-GW-04) | Kho vết ghi tập trung, cơ sở dữ liệu, cổng | Q-11, Q-47, `docs/architecture/vi/15-target-architecture.md` §3.1, roadmap §3.4, §6.1 | [`15`](15-target-architecture.md) §3.1 |
| **Gate Registry** | I10 | Chuẩn OCI với ORAS và Harbor; OpenMeter cho đo lường | Cơ chế ký gate cụ thể (chỉ ghi "OCI/ORAS", TSK-W2-04) | roadmap §6, Q-5 | [`15`](15-target-architecture.md) §3.2 |
| **Node robot (MCU node)** | I14 | Zenoh-pico trên MCU và `zenohd` trên Pi (micro-ROS chỉ là phương án B); mTLS hoặc PSK giữa Pi và node; an toàn cục bộ watchdog / black channel (IEC 61784-3) | Mã hoá ý định trên dây, đồng bộ đồng hồ | Q-36, bản nháp RFC node, `docs/architecture/vi/15-target-architecture.md` §4.3 | [`15`](15-target-architecture.md) §4.3 |
| **Vision Pipeline (đường ống thị giác)** | I2a, I3a (cơ bản); I16–I17 (`jetson`, đa phương thức) | HAL thị giác `vision.in` trên `sim`, `linux` và `esp32s3` (RFC-0012, TSK-V1b-07; Q-53), rồi `jetson`; maker khai dữ kiện `bool`/`level`/`choice` kèm độ tin cậy số từ nhãn model, gate khoá ngưỡng bằng tiêu chí `numeric` (Q-54; `docs/architecture/vi/15-target-architecture.md` §4.4), ngữ nghĩa gate riêng cho bằng chứng thị giác vẫn để mở (TSK-V3-04); vết ghi không nhúng khung hình thô, lưu thô phải bật tường minh (phase2 §2.3) | Chọn cụ thể giữa các khung đã nêu (ONNX Runtime/YOLO, HailoRT/Edge TPU, TensorRT) và mô hình | `docs/architecture/vi/15-target-architecture.md` §4.4, TSK-V1b-07, TSK-V3-04 | [`15`](15-target-architecture.md) §4.4 |

Q-72 thêm các container quy hoạch dưới đây (`planned · Q-72`; quyết định: [Q-72](../../../roadmap/neuroedge-prd.md#15-sổ-quyết-định)):

| Container | Increment | Công nghệ đã nêu | Chưa chọn | Nguồn | Kiến trúc đích |
|:---|:---:|:---|:---|:---|:---|
| **Runtime 24/7 + LLM worker** | I2d | Dịch vụ systemd; LiteLLM (BYOK, có mô hình tại chỗ); MCP cục bộ giữa hai tiến trình | Cơ chế chặn mạng của worker (user riêng + tường lửa, hay proxy của runtime) | Q-72, Q-71 | [`15`](15-target-architecture.md) |
| **Blueprint Hub index** | I2e | Kho index tĩnh kiểu index plugin của I2c; URL + digest; sau cổng nhu cầu chuyển sang Gate Registry OCI | Nơi đặt kho, định dạng index | Q-72 | [`15`](15-target-architecture.md), [`16`](16-ecosystem-landscape.md) |
| **Relay** (tuỳ chọn) | — | Ống TLS xuyên chọn đích theo SNI, không giải mã (mẫu SniTun của Nabu Casa) | Nơi chạy, chứng chỉ, giá | Q-72 | [`15`](15-target-architecture.md) |

Những gì kiến trúc hiện tại đã chuẩn bị sẵn cho các container này ở [`15`](15-target-architecture.md) §8.

## 6. Triển khai (C4 deployment)

> **Phạm vi:** mỗi container của [`02`](02-container-c4l2.md) chạy trên máy nào, trong môi trường nào, nối
> với nhau qua gì — hôm nay và khi bo mạch về. **Nguồn:** `.github/workflows/`, `scripts/`, `boards/`,
> `targets/esp32s3/components/ne_ota/Kconfig`, `python/neuroedge/models/providers/config.py`.

### 6.1 Bức tranh

![E-08 · Triển khai](../assets/svg/E-08-deployment.svg)
*Hình E-08 — Ba vùng: máy của kỹ sư, máy chạy CI của GitHub, thiết bị; thêm vùng nét đứt "máy nhà" (Pi, mini PC hoặc NAS) chạy agent vận hành, cùng nền tảng chat, relay và index Hub — `planned · Q-72`. Dải dưới cùng: NeuroEdge Cloud tuỳ chọn và hộp tại nhà nhỏ ESP32-S3 — có điều kiện, `planned · Q-74`, I2f. Khối `○ planned` chưa có phần cứng hoặc chưa có mã.*

NeuroEdge **không có dịch vụ phía máy chủ nào** trước tầng dịch vụ v1.1 (I0–I8): không tài khoản, không broker, không
backend. Mọi thứ chạy trên máy của người dùng hoặc trên thiết bị. Dịch vụ phía máy chủ đầu tiên là Fleet
OS ở I9 (roadmap §0.5).

`planned · Q-72` ([Q-72](../../../roadmap/neuroedge-prd.md#15-sổ-quyết-định)): định vị Blueprint thêm một nút **máy nhà** chạy 24/7 và hai thứ ngoài máy người
dùng, đều tuỳ chọn và **không bao giờ nằm trên đường an toàn**: index Hub (một kho git tĩnh, không phải
dịch vụ, I2e) và relay (dịch vụ duy nhất do NeuroEdge vận hành trước v1.1, chỉ chuyển gói TLS, không giải
mã). Thiết kế: [`15`](15-target-architecture.md) §6.

### 6.2 Nút triển khai

| Nút | Môi trường | Chạy gì | Trạng thái |
|:---|:---|:---|:---|
| **Máy kỹ sư** | macOS hoặc Linux, Python 3.11+, `python/.venv` | CLI và thư viện `neuroedge`, target `sim`, `mcp serve`, pytest | ✅ |
| **Trình duyệt** | cùng máy | trang `sim` của `--ui`, phục vụ **chỉ trên 127.0.0.1** (`sim/ui.py`) | ✅ |
| **Claude Desktop** (hoặc client MCP khác) | cùng máy | khởi động `neuroedge mcp serve` làm tiến trình con, nói stdio | ✅ |
| **Docker `espressif/idf:v5.4`** | cùng máy hoặc runner CI | dựng firmware ESP-IDF, Espressif QEMU; `scripts/qemu_boot.sh`, `qemu_ota.sh`, `run_ui_golden.sh` | ✅ |
| **GitHub Actions** | `ubuntu-latest` | năm workflow ở §3 | ✅ |
| **Runner tự quản có Box-3** | nhãn `[self-hosted, esp32s3-box-3]` | job `memory-spike` của `nightly-hardware.yml` | ○ planned (TSK-S1-10, TSK-S4-05) |
| **Raspberry Pi 5 + HAT I2S** | Linux, profile `boards/linux-rpi5.toml` | `neuroedge --target linux`: libgpiod, hwmon, âm thanh | ○ planned (TSK-I2-01) |
| **ESP32-S3-BOX-3** | firmware từ `neuroedge build --target esp32s3` | gate trên chip, vết ghi UART tới host, OTA | ○ planned (TSK-S4-12) — đã chạy trên QEMU |
| **Máy chủ ảnh OTA** | bất kỳ máy chủ HTTP(S) tĩnh nào | phục vụ ảnh ứng dụng đã ký | ✅ trên QEMU (`qemu_ota.sh` dùng `python3 -m http.server` trên 127.0.0.1) |
| **Nhà cung cấp model và giọng nói** | dịch vụ ngoài qua HTTPS | model ngôn ngữ, STT, TTS, Jev | ✅ tuỳ chọn; mặc định không gọi mạng |
| **Máy nhà** (Pi, mini PC hoặc NAS) | Linux, systemd; chạy giả lập G1 `sim` hoặc G2 `linux` trên `gpio-sim` trước khi có phần cứng thật | **runtime tin cậy 24/7** (dịch vụ systemd, khởi động lại khi chết): HAL, gate, thực thi hợp đồng nhiệm vụ, lập lịch, bộ phát hiện tất định, adapter kênh chat và kiểm bản ghi duyệt, cửa ra egress, vết ghi theo đoạn | ○ planned · Q-72 · I2d |
| **LLM worker** | cùng máy nhà, **user hệ điều hành riêng**, không trong nhóm `gpio`/`i2c`; tường lửa chỉ cho ra tới endpoint provider đã khai | giữ key BYOK, gọi runtime qua MCP cục bộ như một client MCP (nguồn do runtime gán); không bao giờ duyệt | ○ planned · Q-72 · I2d |
| **Nền tảng chat** (Telegram trước; Slack, Zalo sau) | cloud của bên thứ ba | nhận báo cáo chủ động và yêu cầu duyệt, gửi lệnh và lời trả lời duyệt về runtime | ○ planned · Q-72 · I2d |
| **Relay** (tuỳ chọn) | máy chủ do NeuroEdge vận hành | ống TLS xuyên chọn đích theo SNI, không giải mã (mẫu SniTun của Nabu Casa); giữ blob sao lưu vết ghi đã mã hoá phía máy nhà | ○ planned · Q-72 (ngoài I2d, I2e) |
| **Index Hub** | kho git tĩnh, đọc qua HTTPS | liệt kê URL, digest toàn gói và bằng chứng "chưa ký" của từng NeuroEdge Blueprint; gói nằm ở kho của người bán | ○ planned · Q-72 · I2e |

Điều chặn các nút này hôm nay nằm ở roadmap §0.1 ("Chặn ngoài tầm kỹ thuật").

### 6.3 CI: mỗi job chứng minh gì

| Workflow | Kích hoạt | Job | Chứng minh |
|:---|:---|:---|:---|
| `ci-sim-linux.yml` | PR, push, tay | `frozen-artifacts` | bảy lược đồ hợp lệ; gate khớp `digests.lock`; mọi gate phân giải; corpus gate hỏng vẫn hỏng; ba vết ghi chuẩn mực hợp lệ; profile bo mạch |
| | | `tests` | pytest trên Python 3.11, 3.12, 3.13; **fail nếu có test bị skip** |
| | | `linux-hal` | `LinuxHAL` trên dòng GPIO ảo (gpio-sim), cảm biến hwmon (i2c-stub + lm75), framebuffer ảo (vfb hoặc vkms — runner GitHub chỉ có vkms); `verify --targets sim,linux` |
| | | `wheel-smoke` | bản cài từ wheel chạy được, không chỉ bản editable |
| | | `lint` | `ruff check`, `ruff format --check` |
| | | `licence-obligations` | nghĩa vụ giấy phép (`CHANGELOG.md` §3.9) |
| | | `cloud-extra` | extra `neuroedge[cloud]` (LiteLLM thật) giữ đúng chính sách giấy phép Q-11, adapter chạy trên đối tượng trả về thật mà không gọi mạng |
| | | `ui-golden` | mỗi màn hình × ngôn ngữ của UI LVGL dựng trên host khớp PNG golden |
| `firmware-qemu.yml` | PR và push đụng firmware hoặc engine, hằng đêm, tay | `firmware-qemu` | firmware boot trên QEMU và self-test gate đạt; heap khi boot trên sàn Q-3 |
| | | `firmware-size` | ngân sách tĩnh Q-3: ảnh ≤ 3,5 MB, còn ≥ 120 KB SRAM trong |
| | | `ota-rollback` | cập nhật có ký, từ chối khoá sai, rollback — trên QEMU |
| | | `agent-firmware` | agent mới của người dùng build ra firmware và boot trên QEMU; agent bo mạch không phục vụ được thì không có firmware (mã thoát 1) |
| | | `uart-trace` | vết ghi UART thành `trace.v1` hợp lệ, và `verify --targets esp32s3` đạt |
| `security.yml` | PR, push, hằng tuần, tay | `pip-audit`, `gitleaks`, `actionlint`, `codeql`, `codeql-c` | lỗ hổng đã biết trong tập phụ thuộc ghim; không bí mật trong lịch sử git; workflow sạch; phân tích tĩnh Python và C |
| `release-pypi.yml` | tag `v*.*.*`, PR đụng đóng gói, tay | `build` → `sbom` → `smoke` → `attest` → `publish-*` → `github-release` | sdist và wheel; SBOM CycloneDX; provenance Sigstore; PyPI thật ở I6 |
| `nightly-hardware.yml` | hằng đêm, tay | `firmware-build`, `upstream-drift`, `drift-issue`, `memory-spike`, `report` | ảnh vừa khe OTA; trôi phụ thuộc thượng nguồn (không bao giờ làm đỏ, Q-32); đo bộ nhớ trên bo mạch khi có runner |

Bước cụ thể: chính các tệp workflow. Trạng thái xanh/đỏ hiện hành: roadmap §0.1.

### 6.4 Cấu hình và bí mật khi triển khai

| Thứ | Ở đâu | Luật |
|:---|:---|:---|
| Khoá API của nhà cung cấp | biến môi trường; `agent.toml` chỉ ghi **tên** biến (`api_key_env`) | khoá không bao giờ nằm trong tệp của agent, vết ghi hay kho |
| Địa chỉ máy chủ OTA | `CONFIG_NEUROEDGE_OTA_URL` lúc build; NVS (namespace `ne_ota`, khoá `url`) ghi đè lúc chạy | rỗng thì tắt kiểm tra; HTTP thường được phép vì chữ ký ảnh là phép kiểm toàn vẹn — nó không cho tính bí mật |
| Khoá ký OTA | ngoài kho; ảnh mang chữ ký, thiết bị kiểm bằng khoá đã ký app đang chạy | khoá sai ⇒ ảnh bị từ chối (`ota-rollback`) |
| Chọn target và bo mạch | `--target`, `--board`, profile `boards/*.toml` | profile khai những gì đã đo, không hơn ([`10`](10-target-equivalence.md) §7.3) |
| Lớp cấu hình firmware | `sdkconfig.defaults` + `sdkconfig.qemu` / `sdkconfig.ota` | QEMU và bo mạch khác nhau ở lớp cấu hình, không ở mã |
| Key LLM của người dùng (BYOK) — `planned · Q-72` · I2d | **chỉ** trong môi trường của LLM worker | runtime không giữ, không ghi vào vết ghi; worker chỉ ra mạng tới endpoint provider đã khai |
| Token bot chat — `planned · Q-72` · I2d | trong runtime tin cậy, không trong worker | worker không đọc được; lộ token thì kẻ tấn công gửi được tin nhưng không duyệt được, vì lời duyệt còn phải khớp người gửi đã ghép đôi, `nonce`, hạn và digest |
| Chứng chỉ và khoá TLS của relay — `planned · Q-72` | trên máy nhà | relay không bao giờ giữ khoá, nên không giải mã được; sao lưu vết ghi mã hoá trước khi rời máy |
| Vết ghi của runtime 24/7 — `planned · Q-72` · I2d | đĩa máy nhà (thẻ SD hoặc SSD) | chuỗi đoạn theo ngày hoặc khi vượt cỡ; giữ **30 ngày** tại chỗ, đoạn cũ nén rồi xoá hoặc xuất qua relay đã mã hoá; flush theo thời gian (khoảng 10 giây, khai được) và **ngay** khi có phán quyết chặn hay lời duyệt; mất điện mất tối đa phần đuôi sự kiện thường, `replay` báo đoạn cụt; cỡ 30 ngày đo trên G1 `sim` rồi mới ghi vào NFR |

### 6.5 Kết nối giữa các nút

| Từ → tới | Giao thức | Ghi chú |
|:---|:---|:---|
| `neuroedge` → trình duyệt | HTTP + SSE trên 127.0.0.1 | không mở ra mạng |
| Claude Desktop → `mcp serve` | MCP qua stdio | transport mạng: `--http` (TSK-P2-04), thiết bị khác qua mTLS, không phải Claude Desktop |
| `neuroedge` → Docker IDF | `neuroedge build --target esp32s3` sinh project; ESP-IDF dựng trong container | |
| Box-3 → host | UART, dòng `NE1` | `record`/`verify --port` đọc; baud và console còn mở (`TODOS.md` #35) |
| Box-3 → máy chủ OTA | HTTP(S) GET ảnh đã ký | Wi-Fi thật chưa nối (`TODOS.md` #50) |
| `neuroedge` → nhà cung cấp | HTTPS; `http://` chỉ cho máy chủ trên chính máy này | chi tiết theo từng client: [`00`](00-overview.md) §9.3 |
| LLM worker → runtime — `planned · Q-72` · I2d | MCP cục bộ (stdio hoặc socket Unix) | nguồn do runtime gán theo kết nối; mọi lời gọi qua gate như `mcp` |
| LLM worker → nhà cung cấp LLM — `planned · Q-72` · I2d | HTTPS, chỉ tới endpoint đã khai (chặn ở mức hệ điều hành) | đích không khai bị chặn và ghi vết |
| Runtime ↔ nền tảng chat — `planned · Q-72` · I2d | HTTPS tới API của nền tảng (long polling hoặc webhook) | API lỗi ⇒ hàng đợi có hạn + cảnh báo tại chỗ trên UI |
| Máy nhà → relay — `planned · Q-72` | TLS ra ngoài do máy nhà mở; relay chuyển theo SNI | không mở cổng mạng nhà; lời duyệt không đi qua relay, trang mở từ xa chưa được trả lời `ask` tới khi RFC relay chốt xác thực ([`15`](15-target-architecture.md) §6.5); relay mất thì phần an toàn vẫn chạy |
| CLI → index Hub — `planned · Q-72` · I2e | HTTPS (git) tới URL của gói, kiểm digest toàn gói khi cài | digest không khớp ⇒ từ chối cài |

### 6.6 Chưa triển khai

- **Không có máy chủ nào của NeuroEdge trước v1.1** — trừ relay tuỳ chọn của Q-72 (`planned`, ngoại lệ có giới hạn của Q-10: không giải mã, không trên đường an toàn). Q-74 (có điều kiện, sau cổng nhu cầu) thêm NeuroEdge Cloud tuỳ chọn chạy LLM worker; runtime tin cậy vẫn ở máy nhà ([`15`](15-target-architecture.md) §6.10). Điều phối OTA theo đợt (Hawkbit), broker MQTT, kho vết ghi sự cố, danh tính thiết bị là Fleet OS (I9); kho lưu trữ và phân phối gate là Gate Registry (I10) — chi tiết cấu trúc triển khai máy chủ: [`15`](15-target-architecture.md) §3.1/§3.2.
- **Cụm robot phân tầng chưa triển khai.** Cấu trúc phân tầng gồm Raspberry Pi 5 làm não kết nối với các node vi điều khiển chuyên trách ESP32-S3 và RP2350 qua bus truyền thông Zenoh-pico (I14, Q-32, Q-33, Q-36) — chi tiết bố trí nút mạng: [`15`](15-target-architecture.md) §4.3.
- **Nút suy luận thị giác Jetson chưa triển khai.** Target `jetson` (bậc 2, I16) (bậc 2 theo FR-TGT-08, Q-13) chạy thị giác qua JetPack và TensorRT (`docs/architecture/vi/15-target-architecture.md` §4.4, TSK-V2-01) — chi tiết triển khai phần cứng: [`15`](15-target-architecture.md) §4.4.
- **Chế độ lab qua MCP chưa triển khai (I4a, Q-71).** Khi có, client MCP (Claude Code, Claude Desktop) và tiến trình `mcp serve` giữ thiết bị phải tách quyền: client không nằm trong nhóm `gpio`/`i2c` — đường chính là stdio qua SSH với khoá `restrict,command=…`, hoặc `mcp serve` dưới user riêng (`mcp serve --http` chỉ khi client trình được chứng chỉ mTLS); `mcp serve` nạp chính sách từ checkout đã duyệt mà client không ghi được; khoá gate chỉ qua PR trên nhánh được bảo vệ — chi tiết: [`15`](15-target-architecture.md) §4.2, `docs/spec/threat_model.md` §2c.
- **Máy nhà 24/7 chưa triển khai (`planned · Q-72`, I2d, I2e).** Hôm nay không có tiến trình nền nào chạy mãi ([`02`](02-container-c4l2.md) §3). Runtime 24/7, LLM worker, nền tảng chat, index Hub và relay ở trên là thiết kế: [`15`](15-target-architecture.md) §6. Chạy giả lập trước (G1 `sim`, G2 `linux` trên `gpio-sim`, G3 firmware ESP32 trên QEMU của Espressif — Wokwi, Velxio chờ đối chiếu Q-21, Q-69, G4 ESPHome host), phần cứng thật mua sau.
- **Không có bo mạch thật trong CI.** Mọi bằng chứng về chip hôm nay là QEMU và test C trên host; bằng
  chứng trên silicon chờ bo mạch và runner tự quản (`TODOS.md` #10).
- **Chưa phát hành lên PyPI.** Workflow đã có; phát hành thật ở I6.
