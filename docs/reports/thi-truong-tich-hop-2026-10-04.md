# Thị trường tích hợp thiết bị cho AI agent — 2026-10-04

Báo cáo khảo sát làm căn cứ cho **Q-67** (nền tảng mở, `roadmap/neuroedge-prd.md` §15) và cho ghi chú thiết kế
[`neuroedge-design-open-platform.md`](../../roadmap/neuroedge-design-open-platform.md). Câu hỏi: các hệ sinh thái
AI-phần cứng hiện có và mới ra nối thiết bị bằng cách nào, gate an toàn đặt ở đâu được, và họ còn thiếu gì.

**Phương pháp:** đọc tài liệu và kho mã chính thức ngày 2026-10-04. Dòng ghi *(thứ cấp)* chỉ có nguồn báo chí;
*(chưa kiểm)* là điều không xác nhận được từ nguồn gốc. Thị trường đổi nhanh — báo cáo này là ảnh chụp, không
cập nhật; lần khảo sát sau là một tệp mới.

## 1. Từng hệ sinh thái

| Hệ sinh thái | Cách tích hợp | Lệnh chạy ở đâu | Khai năng lực | An toàn sẵn có | Nguồn |
|:---|:---|:---|:---|:---|:---|
| **Meta Muse Gadgets** (ra 2026-10-02, Apache-2.0) | SDK ESP32 (C, ESP-IDF) và dịch vụ Linux; gadget mở kết nối ra phía Muse và giữ kết nối | Trên gadget; agent chạy phía Muse | Lệnh khai trong `COMMAND_SPECS` (mô tả, tham số, timeout); skill cộng đồng là Markdown | Ghép đôi xác nhận trên app; lệnh chạy dưới tài khoản không phải root. SDK Linux mang sẵn `system.run`, `file.write`. Không thấy danh sách cho phép hay xác nhận theo lệnh | [muse-gadget-sdk](https://github.com/facebookincubator/muse-gadget-sdk) · [`linux/AGENTS.md`](https://raw.githubusercontent.com/facebookincubator/muse-gadget-sdk/main/linux/AGENTS.md) |
| **Muse Home Link** | Thiết bị USB-C trên mạng nhà, gọi API HTTP cục bộ (TV, loa…) | Mạng cục bộ | Skill Markdown | Không mô tả | [unite.ai](https://www.unite.ai/meta-open-sources-muse-gadget-sdks-for-diy-ai-hardware-devices/) *(thứ cấp)* |
| **MCP** (spec 2026-07-28) | JSON-RPC qua Streamable HTTP hoặc stdio | Nơi chạy MCP server | `tools/list`, `inputSchema`/`outputSchema` JSON Schema 2020-12 | OAuth 2.1 là **tuỳ chọn**; người duyệt chỉ là SHOULD; annotation của tool "MUST be considered untrusted" | [spec — tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) · [roadmap](https://blog.modelcontextprotocol.io/posts/mcp-roadmap/) |
| **Anthropic MHS** (Model Hardware Standard) | Driver cạnh thiết bị, gọi qua MCP, CLI hoặc API mã | Trong driver | Manifest: đại lượng đo, đại lượng chỉnh, giới hạn | Giới hạn, khoá liên động, phê duyệt nằm **trong driver của hãng**. Bản xem trước (công bố 2026-08-27); mã nguồn mở "dự kiến", chưa có kho, chưa có giấy phép | [modelhardwarestandard.com](https://modelhardwarestandard.com) |
| **Home Assistant** | `/api/mcp` (MCP server, Streamable HTTP); HA cũng là MCP client; Wyoming chỉ cho giọng nói | Hub cục bộ | Thực thể "được phơi ra" | Phơi ra theo **thực thể**, không theo giá trị; không thấy xác nhận theo hành động | [mcp_server](https://www.home-assistant.io/integrations/mcp_server) · [expose](https://www.home-assistant.io/voice_control/voice_remote_expose_devices/) |
| **ESPHome** | API gốc TCP + protobuf, mã hoá Noise với PSK | Trên chip | `api.proto`; action YAML thành service | HA cấp quyền chạy action theo thiết bị | [esphome API](https://esphome.io/components/api/) |
| **Matter 1.6** | Cluster qua IP (Wi-Fi, Thread, Ethernet) | Trên thiết bị; controller ra lệnh | Mô hình cluster và thuộc tính | Chứng thực thiết bị, commissioning; ACL không biểu đạt **giới hạn giá trị** | [Matter](https://en.wikipedia.org/wiki/Matter_(standard)) *(thứ cấp)* |
| **Amazon Alexa+** | MCP Toolkit: add-on nối MCP server của bạn | MCP server của bạn | Tool MCP chuẩn | Liên kết tài khoản; luồng xác nhận không mô tả | [MCP Toolkit](https://developer.amazon.com/docs/alexaplus/add-ons/mcp-toolkit-overview.html) |
| **Google Home APIs / Gemini for Home** | SDK Android/iOS, Matter, cloud-to-cloud | Chưa nói rõ cục bộ hay cloud | Loại thiết bị Matter | Không mô tả | [Google Developers Blog](https://developers.googleblog.com/en/empowering-service-providers-and-hardware-partners-with-gemini-for-home) |
| **Apple** (iOS 27) | App Intents là đường duy nhất Siri gọi tới app | Thiết bị hoặc Private Cloud Compute | `@AppIntent` | Siri xác nhận intent có tác dụng phụ; không thấy API agent cho phụ kiện | [WWDC26 343](https://developer.apple.com/videos/play/wwdc2026/343/) |
| **ESP-Claw** (Espressif, Apache-2.0) | LLM ở cloud viết Lua chạy trên chip; MCP server và client | Trên chip (Lua) | MCP + mô-đun Lua | Không mô tả sandbox hay xác nhận | [esp-claw](https://github.com/espressif/esp-claw) |
| **xiaozhi-esp32** (MIT) | MCP (JSON-RPC) bọc trong WebSocket hoặc MQTT+UDP tới cloud | Trên chip; LLM ở cloud | `AddTool` + `inputSchema`; `AddUserOnlyTool` giấu tool khỏi AI | Chỉ tầng "tool người dùng" | [mcp-protocol.md](https://raw.githubusercontent.com/78/xiaozhi-esp32/main/docs/mcp-protocol.md) |
| **ROS 2 + ROSA**, LeRobot | Tool LangChain bọc ROS; lớp robot Python | Máy tính của robot | `@tool` có docstring | ROSA: danh sách chặn node/topic, mặc định không có tool truyền động | [nasa-jpl/rosa](https://github.com/nasa-jpl/rosa) |
| **Lớp an toàn cho agent vật lý** | `safety-harness` (tham chiếu, Python, mặc định chặn); Safe Hands (gate Cedar cho tay máy LeRobot, ngừng bảo trì) | — | — | Chỉ hai dự án nhỏ có gate; không có định dạng vết ghi chung | [safety-harness](https://github.com/arkonahomerobotics/safety-harness) |

## 2. Bốn hình dạng tích hợp và chỗ đặt gate

| # | Hình dạng | Ví dụ | Gate đặt ở đâu để không lệnh nào tới phần cứng mà không qua nó |
|:---:|:---|:---|:---|
| 1 | Agent gọi tool qua MCP | Home Assistant, Alexa+, ESP-Claw, xiaozhi, MHS | **MCP proxy** đứng trước server thật; server thật chỉ nghe trên đường proxy tới được |
| 2 | Thiết bị gọi ra cloud của hãng | Muse Gadgets, xiaozhi | **Bộ điều phối trên thiết bị** giữa đường truyền và driver; gỡ lệnh thô (`system.run`) |
| 3 | Hub / HTTP cục bộ, pub/sub | Home Assistant, ESPHome, Muse Home Link, Matter, MQTT | **Reverse proxy** trước API, hoặc **cầu nối giữ vai controller** chỉ phát lại lệnh đã qua gate |
| 4 | Middleware robot | ROS 2, LeRobot | **Node chặn** giữa planner và controller |

Mã do LLM sinh rồi chạy trên thiết bị (ESP-Claw, `system.run` của Muse) là trường hợp riêng: ranh giới tool đã
quá muộn, gate phải nằm ở lớp HAL mà mã đó gọi tới.

## 3. Điều không hệ nào có

- **Giới hạn theo giá trị, ngay trên thiết bị.** Skill Muse là Markdown; `system.run` là shell tuỳ ý; Home Assistant
  phơi ra theo thực thể; Matter không có giới hạn giá trị; MHS để giới hạn trong driver của hãng.
- **Xác nhận bắt buộc.** MCP chỉ ghi SHOULD; Apple xác nhận trong Siri; ESP-Claw không có.
- **Chặn khi lỗi theo mặc định (fail-closed).** Chỉ `safety-harness` (dự án tham chiếu, không người dùng).
- **Vết ghi phát lại được, theo định dạng chung.** MCP chỉ khuyên client ghi log; không có định dạng chung.
- **Danh tính khác quyền.** Token Muse "là định danh, không phải mật khẩu"; PSK của ESPHome dùng chung.

## 4. Rủi ro cho một lớp an toàn tách riêng

- **MHS có thể thành chuẩn giới hạn của ngành.** Hướng nên đi: nhập manifest MHS làm nguồn giới hạn và dữ kiện,
  đứng ở tầng gate và vết ghi phía trên driver — bổ sung, không cạnh tranh (`TODOS.md` #33).
- **Ngăn xếp đóng hoặc chạy trên cloud** (Google, Alexa cloud-to-cloud, Apple): chỉ chèn được gate nếu người dùng
  giữ hub hoặc firmware.
- **Giao thức đổi nhanh** (MCP 2026-07-28 bỏ phiên và SSE): adapter phải mỏng, bám ngữ nghĩa `tools/call`.
- **Xác nhận phía nền tảng bị coi là "đủ"** cho hàng tiêu dùng, dù nó nằm phía client và lách được.
- **MCU không chạy được gate Python:** lõi cần C (đã có `ne_gate`).

## 5. Hệ quả cho NeuroEdge

Bốn adapter phổ quát — MCP proxy, bộ điều phối trên thiết bị (bridge), reverse proxy/cầu nối, node robot — phủ
phần lớn thị trường; mỗi hệ sinh thái mới chỉ cần một plugin mỏng trên một trong bốn hình dạng. Thứ NeuroEdge
bán là phần **không ai có** ở §3: gate theo giá trị, fail-closed, vết ghi chung — với điều kiện lõi dùng được
độc lập và điểm cắm mở. Quyết định: Q-67; kiến trúc: `neuroedge-design-open-platform.md`.
