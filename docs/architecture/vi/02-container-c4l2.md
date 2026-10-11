# 02 · Container và ranh giới tiến trình (C4 L2)

> **Phạm vi:** các khối chạy độc lập — tiến trình, thư viện, firmware, kho tệp — và cách từng cặp
> nói chuyện. **Nguồn:** `python/pyproject.toml`, `python/neuroedge/cli/`, `sim/ui.py`,
> `mcp_server.py`, `targets/esp32s3/`, `.github/workflows/`.

## 1. Sơ đồ container

![E-02 · Container](../assets/svg/E-02-containers.svg)
*Hình E-02 — Container trên máy dev hoặc thiết bị Linux (trên), trên chip (dưới), và hệ thống ngoài (phải). Khối nét đứt mang nhãn I2d, I2e, Q-72 là thiết kế đích của [Q-72](../../../roadmap/neuroedge-prd.md#15-sổ-quyết-định) (`planned · Q-72`): runtime 24/7, LLM worker, nền tảng chat, Hub index, relay.*

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
(PRD §9.1) và trạng thái đo của chúng ở [`08`](08-nfr.md).

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
| **Gate Registry** | I10 | Chuẩn OCI với ORAS và Harbor; OpenMeter cho đo lường | Cơ chế ký gate cụ thể (chỉ ghi "OCI/ORAS", TSK-W2-04) | roadmap §6.2, Q-5 | [`15`](15-target-architecture.md) §3.2 |
| **Node robot (MCU node)** | I14 | Zenoh-pico trên MCU và `zenohd` trên Pi (micro-ROS chỉ là phương án B); mTLS hoặc PSK giữa Pi và node; an toàn cục bộ watchdog / black channel (IEC 61784-3) | Mã hoá ý định trên dây, đồng bộ đồng hồ | Q-36, bản nháp RFC node, `docs/architecture/vi/15-target-architecture.md` §4.3 | [`15`](15-target-architecture.md) §4.3 |
| **Vision Pipeline (đường ống thị giác)** | I2a, I3a (cơ bản); I16–I17 (`jetson`, đa phương thức) | HAL thị giác `vision.in` trên `sim`, `linux` và `esp32s3` (RFC-0012, TSK-V1b-07; Q-53), rồi `jetson`; maker khai dữ kiện `bool`/`level`/`choice` kèm độ tin cậy số từ nhãn model, gate khoá ngưỡng bằng tiêu chí `numeric` (Q-54; `docs/architecture/vi/15-target-architecture.md` §4.4), ngữ nghĩa gate riêng cho bằng chứng thị giác vẫn để mở (TSK-V3-04); vết ghi không nhúng khung hình thô, lưu thô phải bật tường minh (phase2 §2.3) | Chọn cụ thể giữa các khung đã nêu (ONNX Runtime/YOLO, HailoRT/Edge TPU, TensorRT) và mô hình | `docs/architecture/vi/15-target-architecture.md` §4.4, TSK-V1b-07, TSK-V3-04 | [`15`](15-target-architecture.md) §4.4 |

Q-72 thêm các container quy hoạch dưới đây (`planned · Q-72`; quyết định: [Q-72](../../../roadmap/neuroedge-prd.md#15-sổ-quyết-định)):

| Container | Increment | Công nghệ đã nêu | Chưa chọn | Nguồn | Kiến trúc đích |
|:---|:---:|:---|:---|:---|:---|
| **Runtime 24/7 + LLM worker** | I2d | Dịch vụ systemd; LiteLLM (BYOK, có mô hình tại chỗ); MCP cục bộ giữa hai tiến trình | Cơ chế chặn mạng của worker (user riêng + tường lửa, hay proxy của runtime) | Q-72, Q-71 | [`15`](15-target-architecture.md) |
| **Blueprint Hub index** | I2e | Kho index tĩnh kiểu index plugin của I2c; URL + digest; sau cổng nhu cầu chuyển sang Gate Registry OCI | Nơi đặt kho, định dạng index | Q-72 | [`15`](15-target-architecture.md), [`16`](16-ecosystem-landscape.md) |
| **Relay** (tuỳ chọn) | — | Ống TLS xuyên chọn đích theo SNI, không giải mã (mẫu SniTun của Nabu Casa) | Nơi chạy, chứng chỉ, giá | Q-72 | [`15`](15-target-architecture.md) |

Những gì kiến trúc hiện tại đã chuẩn bị sẵn cho các container này ở [`13`](13-evolution-i0-i18.md) §4.
