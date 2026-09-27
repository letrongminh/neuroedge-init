# 02 · Container và ranh giới tiến trình (C4 L2)

> **Phạm vi:** các khối chạy độc lập — tiến trình, thư viện, firmware, kho tệp — và cách từng cặp
> nói chuyện. **Nguồn:** `python/pyproject.toml`, `python/neuroedge/cli/`, `sim/ui.py`,
> `mcp_server.py`, `targets/esp32s3/`, `.github/workflows/`.

## 1. Sơ đồ container

![E-02 · Container](../assets/svg/E-02-containers.svg)
*Hình E-02 — Container trên máy dev hoặc thiết bị Linux (trên), trên chip (dưới), và hệ thống ngoài (phải).*

## 2. Danh mục container

| Container | Công nghệ | Trách nhiệm | Điểm vào | Trạng thái |
|:---|:---|:---|:---|:---|
| **CLI `neuroedge`** | Python 3.11+, Typer, Rich | Mỗi lệnh là một tiến trình: nạp phiên, chuyển lỗi thành thông báo ba phần và mã thoát; không tự quyết gate | `neuroedge.cli.main:app` | `done` |
| **Thư viện `neuroedge`** | Python; phụ thuộc lõi: `pydantic`, `jsonschema`, `pyyaml`, `rfc8785`, `deepdiff`, `typer`, `rich` | Toàn bộ logic: engine gate, action, HAL, model, thoại, phiên, Action CI | `import neuroedge` | `done` |
| **Web UI của phiên** | `http.server.ThreadingHTTPServer` của thư viện chuẩn, chỉ trên 127.0.0.1 | Hiện thiết bị ảo, dòng phán quyết; nhận lệnh gõ và nút xác nhận của người có mặt | `run --ui`, `mcp serve --ui` | `done` (chỉ `sim`) |
| **Máy chủ MCP** | MCP Python SDK (extra `mcp`), stdio | Đưa mỗi `@action` ra làm công cụ; mọi `tools/call` qua gate | `neuroedge mcp serve` | `done` |
| **Tệp** | Hệ tệp cục bộ | Dự án agent (`agent.toml`, `commands.toml`, `knowledge.toml`, `gates/`, `actions/`, `traces/`); dữ liệu kho (`schemas/`, `gates/`, `boards/`, `fixtures/`, `digests.lock`) | — | `done` |
| **Đầu ra build** | Hệ tệp | `build/gates/` (cây JSON, artifact gate, `NETR`, header C); `build/esp32s3/` (project ESP-IDF đầy đủ) | `neuroedge build` | `done` |
| **Thiết bị Linux** | Kernel Linux: libgpiod v2, sysfs hwmon/IIO, framebuffer, PipeWire | Chân, cảm biến, màn hình, âm thanh thật cho `LinuxHAL` | `--target linux` | `partial` — đã kiểm trên phần cứng ảo, chưa trên Pi |
| **Ảnh firmware** | C99, ESP-IDF v5.4 | Walker `NETR`, sổ token, bảng của agent, vết ghi UART, OTA; tự kiểm lúc khởi động | `app_main` | `partial` — chạy trên QEMU, chưa điều khiển chân |
| **Flash** | 16 MB, bảng phân vùng `partitions.csv` | `factory`, `ota_0`, `ota_1` (mỗi khe 3,5 MB); `nvs`, `otadata`, `phy_init`, `storage` | — | `done` |
| **Fleet OS, Gate Registry** | Chưa chọn đủ; đã chốt Eclipse Hawkbit (Q-11), ORAS và Harbor | Quản trị đội thiết bị; kho gate có ký | — | `planned` (I9, I10) |

## 3. Mô hình tiến trình và luồng

NeuroEdge không có tiến trình nền nào chạy mãi. Mọi thứ sống trong tiến trình của lệnh đang chạy.

| Tình huống | Tiến trình | Luồng và vòng lặp sự kiện |
|:---|:---|:---|
| `run -c`, `run` (REPL), `record` | Một tiến trình `neuroedge` | Mỗi lượt một vòng lặp `asyncio` mới (`asyncio.run(session.handle(text))`) |
| `run --ui` | Như trên, cộng máy chủ HTTP | Luồng HTTP của `ThreadingHTTPServer`; mỗi lượt chạy dưới một khoá chung; SSE đẩy trạng thái khi đổi hoặc mỗi 1 giây |
| `mcp serve` | Tiến trình con do client MCP khởi động | Một vòng lặp `anyio`; khoá `turns` bảo đảm mỗi lần một lời gọi |
| `mcp serve --ui` | Như trên, cộng trang web | Lời gọi MCP và lượt trên trang dùng chung một phiên và một khoá |
| `--target linux` | Như trên | Xung GPIO có thời lượng được thả bằng `threading.Timer`; SIGTERM/SIGHUP đưa mọi line về nghỉ trước khi thoát |
| Firmware | Một task `app_main` | Không tạo task FreeRTOS nào; mọi bước khởi động chạy tuần tự ([`04`](04-component-device-c4l3.md) §3) |

Hệ quả: kết nối MCP tới server bên ngoài chỉ sống trong một lượt (`TODOS.md` #25), và một bus I2C
kẹt có thể giữ vòng lặp khoảng một giây (`TODOS.md` #48).

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
| Ảnh firmware → Fleet OS | MQTT | — | `planned` (I9) |

## 5. Container quy hoạch

Chỉ ghi công nghệ mà tài liệu quy hoạch đã nêu; mọi thứ khác là "chưa chọn".

| Container | Increment | Công nghệ đã nêu | Chưa chọn | Nguồn |
|:---|:---:|:---|:---|:---|
| **Fleet OS** | I9 | Eclipse Hawkbit cho chiến dịch OTA theo đợt; broker MQTT giấy phép dễ dãi (Mosquitto, NanoMQ hoặc VerneMQ, chọn bằng đo tải); FastAPI WebSockets cho luồng âm thanh | Kho vết ghi tập trung, cơ sở dữ liệu, cổng | Q-11, proposal §6.2 |
| **Gate Registry** | I10 | Chuẩn OCI với ORAS và Harbor; OpenMeter cho đo lường | Cơ chế ký gate cụ thể (chỉ ghi "OCI/ORAS", TSK-W2-04) | roadmap §6.2, Q-5 |
| **Node robot** | I14 | Zenoh-pico trên MCU và `zenohd` trên Pi (micro-ROS chỉ là phương án B); mTLS hoặc PSK giữa Pi và node | Mã hoá ý định trên dây, đồng bộ đồng hồ | Q-36, bản nháp RFC node |

Những gì kiến trúc hiện tại đã chuẩn bị sẵn cho các container này ở [`13`](13-evolution-i0-i18.md) §3.
