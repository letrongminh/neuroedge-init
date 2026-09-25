# Kế hoạch mở rộng NeuroEdge cho robot phân tầng phức tạp (FOFOCA)

**Phiên bản:** 0.2 — bản nháp, chưa phải quyết định của kho (0.2: đối chiếu với kho sau TSK-S4-09 và TSK-S2-07, 2026-09-25)

**Ngày lập:** 25 tháng 9, 2026 · Lịch sử thay đổi: `CHANGELOG.md`

**Tài liệu nguồn:**

- `neuroedge-prd.md` §4.1 (FR-HAL), §4.2 (FR-TGT), §9.4 (NFR-SEC), §14 (ngoài phạm vi), §15 (Q-13, Q-29)
- `neuroedge-proposal.md` §3.2, §3.4, §3.8, §8.9, §10.1–§10.2, Phụ lục H.3
- `docs/spec/threat_model.md`, `docs/spec/tool_calling.md`, `docs/spec/hal_mcu_review.md`,
  `docs/spec/voice_fsm.md` (hợp đồng thu hồi lệnh), `docs/spec/simulation_coverage.md` (vết ghi `NE1` từ thiết bị)
- `docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md`, `docs/rfc/0003-bo-cuc-nhi-phan-cay.md`
- `neuroedge-roadmap-phase1-5.md` (bản nháp Giai đoạn 1.5), `TODOS.md`, `CONTRIBUTING.md`

**Phạm vi:** các chặng W0–W4 — mở nguyên thủy HAL, an toàn actuator, hạ tầng tin cậy,
multi-node, hệ sinh thái; kèm khung RFC cho từng thay đổi.

**Ngoài phạm vi:**

- Matter / Apple HomeKit (PRD §14).
- **Tự viết** SLAM, tránh vật cản, dẫn đường tự hành (`neuroedge-roadmap-phase2.md:218`). Ngoại lệ **Q-34**
  (2026-09-25): tích hợp nguyên bản ROS 2/Nav2 cho W4-1, gate xét mọi lệnh tốc độ.
- MHS ở bậc 1 hoặc chạm `schemas/` (Q-29 giữ nguyên: theo dõi, adapter cộng đồng khi chuẩn mở).
- Tự huấn luyện/tinh chỉnh mô hình.

> **Trạng thái quản trị.** Hướng đã được nhận (Q-32, 2026-09-25 — bắt đầu sau Developer Beta); chi tiết vẫn là kế hoạch đề xuất. Các
> điểm cần chốt phải vào `neuroedge-prd.md` §15 dưới mã `Q-N` mới (Phụ lục C); chỉ khi đó
> kế hoạch mới có hiệu lực. Tệp này **không** cập nhật tiến độ (nguồn duy nhất:
> `neuroedge-roadmap.md` §0) và **không** tạo sự thật mới — mỗi sự thật có đúng một nơi
> (`CONTRIBUTING.md` §8.1).

---

## Mục lục

1. [Mục tiêu và định nghĩa "xong"](#1-mục-tiêu-và-định-nghĩa-xong)
2. [Bất biến và kỷ luật thực thi](#2-bất-biến-và-kỷ-luật-thực-thi)
3. [Trạng thái xuất phát](#3-trạng-thái-xuất-phát)
4. [Kiến trúc mục tiêu](#4-kiến-trúc-mục-tiêu)
5. [Cơ sở: nghiên cứu giải pháp OSS/thế giới](#5-cơ-sở-nghiên-cứu-giải-pháp-ossthế-giới)
6. [Chặng 0 — việc nhẹ làm ngay](#6-chặng-0--việc-nhẹ-làm-ngay)
7. [Chặng 1 — cơ thể: HAL và an toàn actuator](#7-chặng-1--cơ-thể-hal-và-an-toàn-actuator)
8. [Chặng 2 — hệ thần kinh](#8-chặng-2--hệ-thần-kinh)
9. [Chặng 3 — multi-node](#9-chặng-3--multi-node)
10. [Chặng 4 — hệ sinh thái](#10-chặng-4--hệ-sinh-thái)
11. [Chặng 5 — chứng nhận an toàn chức năng](#11-chặng-5--chứng-nhận-an-toàn-chức-năng)
12. [Thứ tự, phụ thuộc, đường găng, ước lượng](#12-thứ-tự-phụ-thuộc-đường-găng-ước-lượng)
13. [Rủi ro và đối sách](#13-rủi-ro-và-đối-sách)
14. [Điểm mở cần chốt](#14-điểm-mở-cần-chốt)
15. [Khi thực thi — tài liệu phải cập nhật](#15-khi-thực-thi--tài-liệu-phải-cập-nhật)
16. [Bước tiếp theo](#16-bước-tiếp-theo)

**Phụ lục**

- [A — Khung các RFC dự kiến](#phụ-lục-a--khung-các-rfc-dự-kiến)
- [B — Truy vết W-item với nguồn](#phụ-lục-b--truy-vết-w-item-với-nguồn)
- [C — Quyết định chờ cấp mã Q-N](#phụ-lục-c--quyết-định-chờ-cấp-mã-q-n)

---

## Quy ước tài liệu

- Mã chung của kho (`FR-*`, `NFR-*`, `Q-N`, `TSK-*`, `RFC-NNNN`) giải mã ở
  [`docs/user/thuat-ngu.md`](docs/user/thuat-ngu.md); thuật ngữ của bản nháp (FOFOCA, node, black
  channel, W-item, RFC nháp) cũng có ở đó.
- **Mã cục bộ** chỉ có nghĩa trong tệp này, đặt tên để không trùng mã có sẵn: tiêu chí xong
  `DoD-1…5`, luật `BT1…BT7`, tầng kiến trúc `T0…T6`, làn `W1B-RFC-1…3`. `§x.y` trỏ vào tệp này
  khi ghi *"của tài liệu này"*.
- Mốc ghi bằng **ngày tuyệt đối**.
- `W`-item là mã cục bộ của bản nháp này; khi hạ cánh phải cấp `TSK-*` thật trong
  `neuroedge-roadmap.md`.

---

## 1. Mục tiêu và định nghĩa "xong"

**Mục tiêu:** một robot kiểu FOFOCA — Pi 5 làm não, nhiều MCU (motor, display, arm) làm
tay chân — chạy trên NeuroEdge với hợp đồng an toàn nguyên vẹn: mọi hành động vật lý đi
qua gate, kể cả khi hệ thống trải trên nhiều chip, và mọi mở rộng đều có đường kiểm thử.

**Definition of Done của chương trình (FOFOCA reference demo):**

| # | Tiêu chí | Cách chứng minh |
|:--:|:--|:--|
| DoD-1 | Pi 5 (`linux`) + ≥ 2 node MCU chạy HAL/gate cục bộ, liên lạc qua wire "black channel". Node thứ hai là RP2350 (Q-33) | Demo + test CI |
| DoD-2 | Ý định thoại → gate từng node quyết → actuator chạy; **mất liên lạc → node về trạng thái an toàn** (một lần dừng kiểu tắt máy, theo từng cơ cấu — Q-35; phải thêm vào `voice_fsm.md` §5) | Fault injection: drop/delay/replay/tamper |
| DoD-3 | Trace hợp nhất đa node replay được trong CI | `neuroedge verify` + replay. Hôm nay đã có `verify --targets esp32s3 --port` (một node, trên QEMU — TSK-S4-09); `replay --target esp32s3` vẫn thoát mã 2 (TSK-S4-04) |
| DoD-4 | Một bo bậc 3 được port chỉ bằng tài liệu công khai; **thời gian đội lõi hỗ trợ** bản port đầu tiên < 8 giờ | Tiêu chí ra 3 của Khối P1 (`neuroedge-roadmap-phase2.md:267`) |
| DoD-5 | SBOM + OTA ký + mTLS/cert thiết bị demo được | Chặng 2 |

---

## 2. Bất biến và kỷ luật thực thi

### 2.1 Bất biến

| # | Luật | Nguồn |
|:--:|:--|:--|
| BT1 | Một đường duy nhất tới actuator: gate → token dùng một lần → HAL authorize → vết ghi | `docs/spec/threat_model.md` §1 |
| BT2 | Gate chạy **on-device**, fail-closed; **không gate tập trung** (kể cả multi-node) | `neuroedge-proposal.md` §3.4, Phụ lục H.3 |
| BT3 | Chạm `schemas/`, ngữ nghĩa phân giải gate, ba vết ghi chuẩn mực, `digests.lock`, bố cục `NETR` → **RFC** (2 PR: RFC rồi mã) | `CONTRIBUTING.md` §3 |
| BT4 | Mỗi mở rộng: mục threat model + test (0 skip) + corpus khép kín hai chiều; fuzz nếu chạm `NETR` | `CONTRIBUTING.md` §3, §5 |
| BT5 | Milestone-gated + PF-3 (nhu cầu thật); giữ bậc 1 không pha loãng (R-7) | `neuroedge-roadmap.md` §0, PRD R-7 |
| BT6 | Nguyên thủy mới: tùy chọn theo bo mạch, `sim` không giàu hơn bo mạch, bậc 1 vẫn đủ 5 nguyên thủy | FR-HAL-01, bất biến 7 (`CHANGELOG.md` §3.3), `TODOS.md` #14 |
| BT7 | Giấy phép: allowlist Q-11; mọi port theo 5 nghĩa vụ `CONTRIBUTING.md` §4 + `NOTICE`; không copyleft mạnh | `CONTRIBUTING.md` §4 |
| BT8 | NeuroEdge **không** là chức năng an toàn được chứng nhận; robot di động có nút dừng khẩn phần cứng cắt nguồn motor không qua phần mềm | Q-38 |

### 2.2 Danh sách RFC dự kiến

| RFC | Nội dung | Hợp đồng ảnh hưởng | Trạng thái |
|:--|:--|:--|:--|
| RFC-0002 | Mở enum `target` + `TARGET_TIERS` (`vision.in` đã tách ra §9.1 của RFC, 2026-09-23) | `board.v1`, `trace.v1` (chỉ enum `target`) | Đang thảo luận → cần phê duyệt |
| RFC-0007 *(đã giữ chỗ bởi TSK-N0-03 — bản nháp Giai đoạn 1.5)* | `digital.in` + I2C chỉ đọc + chỗ cho ADC + khai báo phong bì N2 | `board.v1`; `gate.v1` **không đổi** (tiêu chí ra N0 #2) | Chưa mở; chủ trì TSK-N0-03 (V2) |
| RFC-numeric *(RFC riêng — không gộp RFC-0007 vì RFC-0007 giữ `gate.v1` nguyên byte)* | `evaluate.type: numeric` + nút `NETR` | `gate.v1`, `NETR` | Chưa mở (`TODOS.md` #30) |
| RFC-motion *(số cấp khi mở)* | `motion.*`/`analog.in` + mở rộng phong bì N2 (của RFC-0007) sang `motion.*` + token theo kênh + bố cục `NETR` mới | `board.v1`, `NETR` (phối hợp `TODOS.md` #36 để tăng bố cục một lần); gate vẫn thuần (bất biến 4) | Chưa mở; là mốc kích hoạt của `TODOS.md` #39 |
| RFC-vision-bậc23 *(số cấp khi mở)* | Hợp đồng `vision.in` + luật riêng tư — thuộc Khối V1b (`linux` + `sim` trước, bậc 2/3 sau) | `board.v1` | Chưa mở |
| RFC-node *(số cấp khi mở)* | Giao thức điều phối node + black channel + trace đa node | `trace.v1`, ngữ nghĩa phân giải? | Chưa mở — xem `draft-rfc-node-giao-thuc-dieu-phoi.md` |
| RFC-pin-extends *(số cấp khi mở)* | Ghim `extends` bằng digest | `gate.v1` | Chưa mở (`TODOS.md` #15) |

> Số RFC: `docs/rfc/README.md` — sao mẫu với **số kế tiếp** khi mở PR RFC (PR chỉ chứa tệp RFC).
> `RFC-0007` đã được TSK-N0-03 giữ chỗ, nên các RFC của bản nháp này bỏ qua 0007; các tên khác
> trong bảng là tên tạm.

---

## 3. Trạng thái xuất phát

Bảng dưới chỉ ghi **trạng thái thật**, không đánh giá quá cao phần đã đặc tả:

| Hạng mục | Trạng thái thật | Nguồn |
|:--|:--|:--|
| Gate + token dùng một lần + trace replay + bên gọi không tin cậy | Có test chặn từng đường tắt; tiêu chí A3 chưa nghiệm thu (`neuroedge-roadmap.md` §6) | `docs/spec/threat_model.md` §1–§2b |
| Secure Boot, mã hóa flash, nút ngắt micro | Đặc tả; task chưa bắt đầu | TSK-S6-05, `neuroedge-prd.md` §9.4 |
| TLS 1.3/mTLS/cert thiết bị/thu hồi | Có task, chưa bắt đầu: TSK-K2-04 (danh tính + chứng chỉ thiết bị), TSK-P2-04 (MCP mạng + mTLS); thu hồi (NFR-SEC-05) chưa có task; ghi "cần tiêu chí" | NFR-SEC-04/05, `neuroedge-prd.md:831` |
| OTA ký số | Đặc tả; TSK-S6-01..04 chưa bắt đầu | NFR-SEC-06, FR-OTA (`neuroedge-prd.md` §5.3) |
| Quyền riêng tư (vision, ẩn danh trace) | Luật đã có; `record --anonymize` có nhưng không mặc định (`TODOS.md` #4); FR-TRC-06/07 **chưa có task** | `TODOS.md` #31 |
| Ký gate/trace | Chưa có; `gate_digest` chỉ truy vết, không chứng thực | `docs/spec/threat_model.md:125` |
| Giấy phép/port OSS | Q-11 + 5 nghĩa vụ + CI; **SBOM chưa có** | `CONTRIBUTING.md` §4, `NOTICE` |
| Phân tầng target 1/2/3 | Q-13 đã chốt; RFC-0002 đang thảo luận; `TARGET_TIERS` chưa vào mã | `python/neuroedge/hal/board.py:58` |
| Chuyển giao chuẩn cho tổ chức trung lập | Cam kết **có điều kiện** tại G1 (10.000 thiết bị) | `neuroedge-proposal.md:246,709` |
| Nợ tiêu chí NFR-SEC | 6 mã "cần tiêu chí" (SEC-02→06, 08) | `neuroedge-prd.md:863` |
| Vết ghi từ thiết bị | Có (TSK-S4-09): dòng `NE1` qua UART, mỗi phiên mở bằng `device_info {board_id, agent_version, device_id, boot_id}`; `verify --targets esp32s3 --port` trên QEMU; `replay --target esp32s3` vẫn mã 2 | `docs/spec/simulation_coverage.md` §4 |
| Thu hồi lệnh khi cắt lời | Đặc tả chuẩn tắc (TSK-S2-07): chỉ hủy lệnh **chưa giao** tới chân, ≤ 20 ms; lệnh đã giao chạy hết; `cancel()` cắt xung đang chạy chỉ dành cho tắt máy | `docs/spec/voice_fsm.md` §5 |

---

## 4. Kiến trúc mục tiêu

### 4.1 Sơ đồ

```mermaid
flowchart TB
  subgraph Pi["Pi 5 — linux (agent host)"]
    S2["LLM/System2"] --> TC["ToolCall/dispatch"] --> GL["Gate (linux)"] --> HL["HAL linux"]
    ZD["zenohd"] --- TC
    ROS["ROS 2 / Nav2 (bridge, ngoài lõi)"] --> TC
    MCP["MCP server (stdio → HTTP + OAuth 2.1)"] --> TC
  end
  subgraph NA["Node MCU A — motor"]
    GN["Gate (node)"] --> HN["HAL motor"] --> M["Actuator + safe-state (pull-down/watchdog)"]
  end
  subgraph NB["Node MCU B — display/arm"]
    GB["Gate (node)"] --> HB["HAL"]
  end
  ZD <-->|"Zenoh-pico — BLACK CHANNEL (không tin cậy)"| NA
  ZD <--> NB
  GL -.->|"trace hợp nhất"| TR["trace + node id (RFC-node)"]
  GN -.-> TR
  GB -.-> TR
```

### 4.2 Bảy tầng

| Tầng | Thành phần | Vai trò |
|:--|:--|:--|
| T0 | Phần cứng node | Trạng thái an toàn cục bộ: kéo xuống/watchdog/giới hạn dòng — crash-safe (phần cứng bảo đảm; phần mềm thì không, `neuroedge-roadmap-phase1-5.md:128`) |
| T1 | **Zenoh-pico** (nhánh Apache-2.0) trên MCU; `zenohd` trên Pi | Wire "black channel" — **không tin cậy** |
| T2 | Lớp an toàn kiểu **black channel** (node id, seq, CRC, timestamp, heartbeat/TTL) | Thông điệp tự bảo vệ; mất heartbeat → node về trạng thái an toàn |
| T3 | **Gate từng node** (giữ nguyên) + agent/ý định trên Pi | Không gate tập trung; node nào tự quyết node đó |
| T4 | **Trace hợp nhất** (RFC-node) | Bằng chứng replay đa node |
| T5 | **MCP** (stdio → Streamable HTTP + OAuth 2.1) | Mặt tiếp xúc agent/control plane — không dùng làm wire MCU |
| T6 | **ROS 2 bridge** qua `zenoh-bridge-dds` (chỉ trên Pi) | ROS action → ToolCall → gate → HAL |

Nguyên tắc xuyên suốt: **an toàn không nằm ở transport**. Zenoh/WiFi được coi là mạng
không tin cậy (IEC 61784-3 black channel); an toàn nằm ở gate + token + watchdog từng node.
Qua wire chỉ có **ý định**. Phán quyết và token do node tự tính, tự cấp, tự tiêu
(`docs/spec/threat_model.md` §2); nonce không bao giờ rời sổ token. Vì vậy TTL token (p95 × 3,
tính trên đồng hồ của chính node) không bảo vệ thông điệp trên wire. Chống ý định cũ là việc của
T2: `seq` + epoch/`boot_id`.

---

## 5. Cơ sở: nghiên cứu giải pháp OSS/thế giới

### 5.1 Điều phối node

| Giải pháp | Ưu điểm | Hạn chế | Giấy phép |
|:--|:--|:--|:--|
| **Eclipse Zenoh / zenoh-pico** | Một giao thức từ MCU tới cloud; overhead ~5 byte; P2P/routed/brokered; đã chạy ESP32, RP2040/Pico, Zephyr, FreeRTOS; độ trễ WiFi/4G tốt hơn MQTT; có bridge ROS 2 (`zenoh-bridge-dds`); đang thành lựa chọn cho R2X (robot-to-anything) | Trẻ hơn DDS/MQTT; cần spike trên ESP32-S3 thật | **EPL-2.0 OR Apache-2.0** — chọn nhánh Apache-2.0 để qua Q-11 |
| **micro-ROS / Micro XRCE-DDS** | Chuẩn OMG (DDS-XRCE), ROS 2 native; đội ngũ eProsima | Cần agent trên Pi; nặng hơn; mô hình client–server | Apache-2.0 |
| **MQTT** | Phổ biến, nhiều broker | "Broker paradox": hai thiết bị cùng LAN vẫn vòng qua broker; EMQX (BSL) không dùng (Q-11, 2026-09-25); Mosquitto (EPL-2.0) không nằm trong Q-11, cần ngoại lệ riêng | Broker: vướng giấy phép |
| **ROS 2 / DDS làm wire** | Hệ sinh thái robot lớn nhất | Không lên MCU; multicast/UDP nặng; kéo máy trạng thái ra khỏi thiết bị — trái yêu cầu "gate và máy trạng thái chạy trên thiết bị" (`neuroedge-proposal.md` Phụ lục H.3) | Apache-2.0 |

### 5.2 An toàn phân tán — black channel

**IEC 61784-3** định nghĩa mẫu "black channel": truyền thông an toàn trên mạng **không
tin cậy** bằng cách để mỗi thông điệp an toàn tự mang trường bảo vệ (CRC, số thứ tự,
dấu thời gian, định danh kết nối, watchdog) và **mỗi thiết bị tự thực hiện chức năng an
toàn** của mình. Đây khớp chính xác với luật BT2 của tài liệu này (gate on-device,
fail-closed) và cho phép dùng transport phổ thông mà không phải tin nó.

Hệ quả thiết kế:

- Node giữ **trạng thái an toàn cục bộ** (ngắt điện động cơ) — phần mềm không cứu được
  khi crash/SIGKILL, cần kéo xuống phần cứng/watchdog (`neuroedge-roadmap-phase1-5.md:128,369`).
- Mất heartbeat/TTL → node từ chối mọi ý định mới và về trạng thái an toàn.
- Replay protection: số thứ tự + epoch/`boot_id` + cửa sổ; không ý định cũ nào được thực hiện lại.
  ALLOW và token không đi qua wire (§4.2 của tài liệu này).

### 5.3 MCP qua mạng

Spec MCP hiện hành (2026-07-28) đã có **authorization OAuth 2.1 cho HTTP transport**
(Streamable HTTP; Protected Resource Metadata RFC 9728; Authorization Server Metadata
RFC 8414; Client ID Metadata Documents). Khuyến nghị: dùng đúng spec thay vì tự chế, và
vẫn thêm mTLS ở tầng thiết bị (NFR-SEC-04) cùng test chống lặp lời gọi (`TODOS.md` #29)
trước khi mở cổng mạng.

### 5.4 MHS

MHS vẫn là **research preview** (2026-08-27), chưa công bố schema/giấy phép; kế hoạch mở
mã nguồn. Đối tác công bố (theo bản preview, chưa kiểm trong kho) gồm Raspberry Pi, Hugging
Face (LeRobot), AWS (Strands Robots), Universal Robots. Giữ Q-29 — lý do của nó là khác phân khúc
(lab/nhà máy qua máy tính đầy đủ, không phải thiết bị biên): theo dõi; khi chuẩn mở **và** có người
dùng thật hỏi (`TODOS.md` #33) thì làm adapter HAL host qua MCP theo mô hình cộng đồng, không bậc 1,
không chạm `schemas/`.

### 5.5 Khuyến nghị

1. **Wire protocol:** Zenoh-pico, micro-ROS là phương án B — **đã chốt ở Q-36**; spike W3-1
   trên phần cứng thật là phép thử loại với ba ngưỡng (PRD §15).
2. **An toàn:** black channel + watchdog + trạng thái an toàn cục bộ; không tin transport.
3. **MCP:** giữ ở mặt agent; mở mạng bằng Streamable HTTP + OAuth 2.1 sau mTLS.
4. **ROS 2:** bridge qua Zenoh trên Pi, tại ranh giới gate.
5. **MHS:** theo dõi (Q-29), ưu tiên thấp.

**Nguồn:** zenoh.io và zenoh-pico (EPL-2.0 OR Apache-2.0; hỗ trợ ESP32/Pico/Zephyr/FreeRTOS);
Micro XRCE-DDS (eProsima, OMG); so sánh DDS/MQTT/Zenoh cho ROS 2 (arXiv 2309.07496);
IEC 61784-3 (black channel); MCP Authorization spec 2026-07-28; Anthropic MHS preview
2026-08-27.

---

## 6. Chặng 0 — việc nhẹ làm ngay

Không cần RFC, không chạm vùng đóng băng; làm trước để tăng độ tin cậy với chi phí thấp.

| ID | Việc | Artifact | Điều kiện xong |
|:--|:--|:--|:--|
| W0-1 | Tiêu chí nghiệm thu 6 NFR-SEC (02→06, 08) + rà NFR-SEC-09 | `neuroedge-prd.md` Phụ lục A.3 + test/evidence | Hết dòng "cần tiêu chí" (`neuroedge-prd.md:863`); mỗi mã có ≥ 1 đường kiểm chứng |
| W0-2 | SBOM (CycloneDX/SPDX) từ `requirements-lock.txt` | `release-pypi.yml` + artifact phát hành | SBOM sinh trong CI phát hành, gắn đúng phiên bản wheel |
| W0-3 | Quét lỗ hổng/bí mật: `pip-audit`, gitleaks, CodeQL (Python + C firmware) | `.github/workflows/` + `CHANGELOG.md` §2.5 (danh sách duy nhất của workflow) + `CONTRIBUTING.md` §6 ("Bốn workflow") | Job chặn khi có phát hiện mức cao; không còn khoảng trống quét |
| W0-4 | Nightly drift: **tự mở issue, không chặn build** (Q-32) — giữ lựa chọn đã ghi ở `nightly-hardware.yml:96-99` (drift là thông tin, không phải lỗi) | `.github/workflows/nightly-hardware.yml:85-121` | Một issue tự mở khi resolved lệch lock |
| W0-5 | Dọn `TODOS.md` #31 (FR chưa có task) và #17 (giấy phép ESP-SR) — sớm hơn mốc của chúng (2026-11-16; bo mạch về), được phép nhưng phải ghi lý do | `TODOS.md`, roadmap | Có chủ trì hoặc quyết định văn bản |

**Ước lượng:** S (1–2 PR). **Phụ thuộc:** không.

---

## 7. Chặng 1 — cơ thể: HAL và an toàn actuator

Đây là chặng **quan trọng nhất** cho FOFOCA: multi-node và ROS 2 vô nghĩa nếu HAL không
diễn tả được chuyển động và cảm biến.

### 7.1 1A — mở rộng trong 5 nguyên thủy (làm trước, ít rủi ro)

| ID | Việc | RFC? | Điều kiện xong |
|:--|:--|:--:|:--|
| W1A-1 | Chuẩn hóa PWM (tần số/độ rộng xung) + kênh phản hồi trạng thái trong `digital.out` | Có (tham số + schema) | Ràng buộc biên có test biên; gate kiểm cả giá trị mặc định (mẫu RFC-0005) |
| W1A-2 | `sensor.read` kiểu số + **tiêu chí `numeric`** | Có | `gate.v1` + nút `NETR` + walker C + corpus; `gate lint` xanh |
| W1A-3 | Rà `board.v1.json`: khoá capability lạ phải bị từ chối lúc nạp (RFC-0002 §3c.2) — đã là TSK-V1a-03 | Gộp RFC-0002 PR2 | Khoá gõ sai bị từ chối **trong mã lúc nạp** — không đóng `capabilities` trong lược đồ (RFC-0002 §3c.2) |

### 7.2 1B — nguyên thủy mới (theo làn sóng)

| Làn | Việc | Phụ thuộc | Điều kiện xong |
|:--|:--|:--|:--|
| W1B-RFC-1 | Duyệt **RFC-0002**; dùng **RFC-0007** do TSK-N0-03 soạn (`digital.in`/I2C chỉ đọc/ADC + phong bì); soạn **RFC-numeric** | Chữ ký kỹ thuật trưởng; `Q-N` cho Giai đoạn 1.5. PR2 của RFC-0002 không hợp nhất trước Tháng 9 chương trình, trừ khi có profile bậc 2/3 thật (RFC-0002; roadmap §10.2) | RFC-0002 approved + PR2 (TSK-V1a-02..06); 3 bất biến test theo bậc; `TARGET_TIERS` trong mã |
| W1B-RFC-2 | **`motion.*`** (motor/servo) + **`analog.in`**; phong bì N2 mở rộng sang `motion.*`; token theo kênh; bố cục `NETR` mới | W1B-RFC-1 + numeric; nhu cầu/đối tác; bo mạch thật | Threat model có dòng cho từng đường tắt mới; fuzz `NETR`; test crash-safe **trên bo mạch thật** (QEMU không giả lập GPIO — `TODOS.md` #21); quyết cờ `TODOS.md` #39 |
| W1B-RFC-3 | Khoá **`vision.in`** bậc 2/3: `fps`, `modes[]`, `pixel_format`; kết quả phải quy về `bool`/`level`/`choice` trước gate; không khung hình thô vào trace | W1B-RFC-1 | Camera trong `sim` không giàu hơn bo mạch (`TODOS.md` #14); fail-closed khi mất camera/model |

**Thiết kế sơ bộ từng nguyên thủy mới:**

| Nguyên thủy | Tham số chính | An toàn | Ghi chú |
|:--|:--|:--|:--|
| `motion.*` (motor/servo) | kênh, đích, tốc độ, thời lượng, ramp | Phong bì N2: duty tối đa, thời gian chạy liên tục tối đa, rate limit; **trạng thái an toàn khai theo từng cơ cấu** — ngắt điện không phải lúc nào cũng an toàn (ví dụ chốt cửa ở `voice_fsm.md` §5.3); token thêm kênh + thời lượng tối đa | Nguyên thủy riêng (không nhồi vào `digital.out`) để hợp đồng rõ |
| `analog.in` | giá trị số, đơn vị, hiệu chuẩn | Ngưỡng qua tiêu chí `numeric`; không suy diễn ngoài thang | Phụ thuộc RFC-numeric |
| `vision.in` | `fps`, `modes[]`, `pixel_format` | Kết quả quy về `bool/level/choice`; fail-closed khi mất camera/model; không khung hình thô vào trace | RFC-0002 §9.1 mới liệt kê đầu vào đã biết; chưa có hợp đồng |
| `digital.in` / I2C / ADC | mức logic, địa chỉ thiết bị I2C, kênh ADC | I2C chỉ đọc, allowlist thiết bị; `lab_read` có cờ; ADC theo kết quả spike | Nguồn: bản nháp Giai đoạn 1.5 (N0/N3) |

### 7.3 An toàn actuator (làm cùng W1B-RFC-2, không tách)

- **T0 crash-safe:** kéo xuống/watchdog/giới hạn dòng trên node tham chiếu + runbook bắt
  buộc ghi rõ (`neuroedge-roadmap-phase1-5.md:128,369`).
- **Phong bì N2:** định nghĩa ở bản nháp Giai đoạn 1.5 — tổng thời gian bật + tần suất theo chân,
  khai ở `board.v1` qua RFC-0007, móc trong HAL trước `authorize` (TSK-N2-01). RFC-motion mở rộng
  nó sang `motion.*`. **Không** dùng cờ `[lab]` làm ngoại lệ: lab mặc định tắt và `build --release`
  từ chối khi bật (TSK-N1-02/03). Tích luỹ thời gian nằm ở HAL, không ở gate (bất biến 4).
- **Token theo kênh:** token hôm nay đã mang **tập chân**, dùng một lần mỗi chân và đóng khi
  `c.do()` trả về (`python/neuroedge/actions/token.py`, `threat_model.md` §2). Phần mới là kênh +
  thời lượng tối đa, cập nhật cả host ledger lẫn `ne_token.c`.
- **Hủy lệnh:** theo `docs/spec/voice_fsm.md` §5 — cắt lời chỉ hủy lệnh chưa giao; lệnh đã giao chạy
  hết. Cờ "vẫn cắt khi đã chạy" cho motor là `TODOS.md` #39 (cần RFC); RFC-motion là mốc kích
  hoạt của #39 và phải quyết nó.

**Ước lượng:** 1A = M; W1B-RFC-2 = L. **Đường găng:** có.

---

## 8. Chặng 2 — hệ thần kinh

Thiết kế ngay, **chưa đặt lịch**; điểm quyết định thời điểm: sau Beta, khi có (a) nhu cầu
thật, (b) bo mạch về, (c) mốc Khối 2/3 mở.

| ID | Việc | NFR / FR | Phụ thuộc | Điều kiện xong |
|:--|:--|:--|:--|:--|
| W2-1 | mTLS + cert thiết bị + thu hồi + provisioning | SEC-04/05, FR-FLT-01 | TSK-K2-04 | Provisioning cấp cert riêng; thu hồi được; test mTLS hai chiều |
| W2-2 | OTA ký + A/B + rollback; verify chữ ký trên chip | SEC-06, FR-OTA-01..04 | TSK-S6-01..04 | Boot loop → rollback; chữ ký sai → từ chối áp dụng |
| W2-3 | Secure Boot + mã hóa flash + nút ngắt micro; **bổ sung task TPM Linux** | SEC-02/03 | TSK-S6-05 + bo mạch | Cấu hình khởi động an toàn + test trên bo thật |
| W2-4 | Ký gate + verify trên thiết bị (Registry OCI/ORAS); ký trace (`TODOS.md` #1); streaming (#3) | — | Khối 2/3 | Gate cộng đồng có chuỗi tin cậy; trace ký đối soát được |
| W2-5 | Sandbox mã bên thứ ba (capability-scoped pin access; phạm vi `linux` trước) | SEC-07 | v1.1 | Mã bên thứ ba không chạm được chân ngoài phạm vi cấp |
| W2-6 | MCP qua mạng: **Streamable HTTP + OAuth 2.1** + mTLS thiết bị + test #29 — trùng TSK-P2-04, dùng task đó | SEC-09 | W2-1 | Không có đường nào tới actuator mà chưa xác thực |
| W2-7 | SBOM kèm phát hành + attestation build + pin GitHub Actions | — | W0-2/3 | SBOM + provenance cho mọi bản phát hành |

**Ước lượng:** L. **Đường găng:** không (trừ W2-1 là điều kiện của W2-6).

---

## 9. Chặng 3 — multi-node

### 9.1 Mô hình

- Một agent (chạy trên Pi/`linux`) phát **ý định**; mỗi node MCU **tự lượng giá gate của
  nó** rồi mới chạm actuator — không gate tập trung (luật BT2).
- Phân biệt rõ: **Fleet OS** (nhiều thiết bị độc lập, Khối 2) khác **multi-node** (một
  robot nhiều MCU).
- Đã lên kế hoạch, chưa bắt đầu: MCP gateway cho thiết bị (TSK-P2-05, `docs/spec/tool_calling.md:216`).
- Danh tính node dựa trên `device_info` sẵn có (`device_id`, `boot_id` — TSK-S4-09). Mỗi thiết bị
  có đồng hồ `offset_ms` riêng, đếm từ `device_info` của nó, nên trace hợp nhất cần căn đồng hồ.
- **Chưa giải** (§14 #12–#13; chính sách mất liên lạc đã chốt ở Q-35):
  - node chỉ thấy một kết nối là Pi, nên phân biệt `call_source` và xác nhận `ask`
    (`tool_calling.md` §5, §6) đi qua Pi → node thế nào;
  - MCU không có parser JSON (KL-5, `hal_mcu_review.md`), nên ý định phải có mã hoá không phải JSON;
  - cắt lời trên Pi mà lệnh đang chờ nằm ở node: cần thông điệp hủy Pi → node và ngân sách 20 ms
    (`voice_fsm.md` §5.2).

### 9.2 Black channel

| Thành phần | Nội dung |
|:--|:--|
| Định danh node | `node_id`, vai trò, khoá liên kết (PSK/mTLS) |
| Bảo vệ thông điệp | `seq`, CRC, `timestamp`, `ttl`, định danh kết nối |
| Watchdog | Heartbeat Pi↔node; mất → từ chối ý định mới, về trạng thái an toàn. Là một lần dừng kiểu tắt máy: phải thêm vào `voice_fsm.md` §5 cùng `actuator_aborted.reason` mới và một sự kiện đầu vào "mất liên lạc" replay được |
| Replay | Số thứ tự + epoch/`boot_id` + cửa sổ. Token không đi qua wire (§4.2 của tài liệu này), nên TTL token không phải cơ chế ở đây |
| Tin cậy | Transport **không** được tin; mọi phán quyết vẫn ở gate từng node |

### 9.3 Trace hợp nhất

`schemas/trace.v1.json` hiện yêu cầu `metadata.target` (enum 3 giá trị) + `board_id`
(`trace.v1.json:15,25,29`); `metadata.additionalProperties: true` (`:39`) nhưng `events`
đóng (`:58`). Dòng `NE1` của firmware cũng có đúng ba khoá (`simulation_coverage.md` §4). Hai phương án:

| Phương án | Cách làm | Ưu | Nhược |
|:--|:--|:--|:--|
| **A (khuyến nghị cho v1.x)** | Thêm `metadata.nodes[]` tùy chọn + quy ước `data.node_id` trong sự kiện | Không phá tương thích; **không sửa `schemas/`** (`metadata` mở, `data` tự do — tiền lệ RFC-0002 và `TODOS.md` #1) | Quy ước nằm trong `data`; cần tài liệu hoá ở `simulation_coverage.md` §3–§4 |
| B | `trace.v2` với `nodes[]` và `node_id` cấp sự kiện | Rõ ràng, chuẩn mực | Phá tương thích; chi phí migrate toàn bộ corpus; đổi cả đặc tả dòng `NE1` |

**Q-32 chọn A** (2026-09-25). Vết ghi đa node đặt ở `fixtures/compliance/multinode/`
(corpus khép kín), **không** thêm vào `fixtures/traces/`: thư mục đó giữ đúng ba vết ghi chuẩn mực
(`voice_fsm.md` §9); tệp thứ tư làm gãy test và đổi vector firmware (`scripts/gen_firmware_vectors.py`).

### 9.4 Việc phải làm

| ID | Việc | Artifact | Điều kiện xong |
|:--|:--|:--|:--|
| W3-1 | **Spike Zenoh-pico ↔ Pi** (ESP32-S3 và RP2350 — Q-33): phép thử loại theo ba ngưỡng của Q-36 (độ trễ, SRAM nội, nối lại), kèm flash và giấy phép | `docs/reports/` + số đo | Đạt cả ba ngưỡng ⇒ giữ Zenoh; trượt ⇒ đo micro-ROS cùng điều kiện, chỉ đổi khi micro-ROS đạt; ghi `NOTICE` nếu nhận mã |
| W3-2 | **RFC-node**: mô hình node, intent, safety wrapper, heartbeat → safe-state, wire, trace | `docs/rfc/` | RFC approved; threat model §2c; corpus tool-call mở rộng |
| W3-3 | Lớp black channel: wrapper + watchdog + replay protection | `python/` + firmware | Test drop/delay/replay/tamper: không ALLOW nào lọt; mất link → safe-state |
| W3-4 | Trace hợp nhất đa node (chọn A/B) | A: quy ước ở `simulation_coverage.md` (không sửa `schemas/`) · B: `trace.v2` | Replay đa node xanh; corpus `fixtures/compliance/multinode/` khép kín (`digests.lock` chỉ khoá gate, không liên quan) |
| W3-5 | Gateway/node: tài liệu hoá quan hệ với TSK-P2-05 (trùng phạm vi — dùng task đó) | `docs/spec/tool_calling.md` | Phân biệt Fleet OS ≠ multi-node + test |
| W3-6 | `verify` mở rộng cho cụm node (tương đương miền phán quyết) | CLI + CI | Lệch → `SafetyRegressionError` (NE4002); chưa hiện thực thì thoát mã 2 (bất biến 10). FR-CI-07 chỉ phủ bậc 1 — node bậc 3 nằm ngoài |

**Lưu ý phần cứng:** `rp2350` có trong danh sách bậc 3 dự kiến (`neuroedge-proposal.md:1692`),
nên nếu dùng thì chọn **RP2350** thay vì RP2040 cho node tay máy. **Q-33** (2026-09-25): đội lõi port
RP2350 — ngoại lệ ghi ở PRD §14 cho luật "không tự port" (`neuroedge-roadmap-phase2.md:252`). Bo mạch tham chiếu
duy nhất vẫn là ESP32-S3-BOX-3 (bất biến 6); ở đây chỉ gọi là "node tham chiếu".

**Ước lượng:** M (spike) + L (RFC + hiện thực). **Đường găng:** có.

---

## 10. Chặng 4 — hệ sinh thái

| ID | Việc | Điều kiện xong | Ước lượng |
|:--|:--|:--|:--:|
| W4-1 | **ROS 2 bridge tại ranh giới gate** (chỉ `linux`, qua `zenoh-bridge-dds`): ROS action → ToolCall → gate → HAL. Nav2 tích hợp nguyên bản, gate mọi lệnh tốc độ (Q-34) — trước đó cần RFC an toàn robot di động và câu C6 từ người mua robot (`TODOS.md` #40) | Demo trong `sim`: ý định → gate → hành động; ROS 2 không chạm actuator trực tiếp | M |
| W4-2 | Bộ kiểm thử tuân thủ portable (P1) + `docs/porting/tier3.md` + `targets/_template/` — là TSK-P1-01..04 | Tiêu chí ra 3 của P1: thời gian đội lõi hỗ trợ bản port đầu tiên < 8 giờ | M |
| W4-3 | Registry có ký (OCI/ORAS) + bất biến server-side (#11) + ghim `extends` digest (#15) | ≥ 10 gate OSS publish (TR-4); verify chữ ký trên thiết bị | L |
| W4-4 | Kho HAL port — là TSK-P2-01 (FR-REG-08 là kho adapter **provider**, khác) | HAL port cộng đồng cài được qua registry | M |
| W4-5 | MHS adapter — khi chuẩn mở **và** có người dùng thật hỏi (`TODOS.md` #33) | Adapter HAL host qua MCP; **không bậc 1, không chạm `schemas/`** (Q-29) | S–M |
| W4-6 | Q-11 chốt Hawkbit/EMQX; OFL cho font; ESP-SR | Phê duyệt văn bản trước Khối 2 | S |

**Giấy phép cho Chặng 4:** ROS 2/Nav2 Apache-2.0 (qua Q-11) nhưng vẫn theo 5 nghĩa vụ
`CONTRIBUTING.md` §4; chọn DDS permissive; bridge là thành phần **cộng đồng/đối tác**,
không bậc 1.

---

## 11. Chặng 5 — chứng nhận an toàn chức năng

Không tự quyết IN/OUT: đây là **câu hỏi cổng nhu cầu C6** — "chứng nhận an toàn chức năng
(IEC 61508, ISO 13849, hoặc tiêu chuẩn họ tự nêu) có là điều kiện mua?"
(`docs/business/cong-nhu-cau-2026-10-25/README.md:44`).

Nếu IN, khung tham chiếu:

| Chuẩn | Vai trò |
|:--|:--|
| IEC 61508 | Vòng đời an toàn chức năng, SIL, phân tích nguy cơ |
| IEC 61784-3 | Black channel — khớp thiết kế Chặng 3 |
| ISO 13482 | Robot chăm sóc cá nhân/gia đình (hợp FOFOCA hơn ISO 26262) |

Đường gần: tự công bố + bằng chứng trace/Action CI, không phải chứng nhận SIL ngay.

**Tư thế tạm thời (Q-38, 2026-09-25): OUT** cho tới khi có dữ liệu — tài liệu ghi rõ không có SIL/PL, robot
di động bắt buộc dừng khẩn phần cứng (BT8). Cổng 2026-10-25 không phỏng vấn người mua robot, nên câu C6 cho
robot hỏi riêng trước khi mở RFC an toàn di động (`TODOS.md` #40).

---

## 12. Thứ tự, phụ thuộc, đường găng, ước lượng

```text
W0 ──► RFC-0002 (duyệt) ──► RFC-0007 (TSK-N0-03) / RFC-numeric ──► W1B-RFC-2 motion + N2 ──► W3 (node) ──► W4-1 ROS 2
                        └──► W1B-RFC-3 vision ───────────────────────────────────────────┘
W2 (song song sau Beta; W2-1 trước W2-6)
```

| Ưu tiên | Gói | Đường găng? | Ước lượng | Ghi chú |
|:--:|:--|:--:|:--:|:--|
| 1 | W0 | Không | S | Làm ngay |
| 2 | RFC-0002 → 1A → W1B-RFC-2 | **Có** | M + L | Mở khóa mọi thứ robot; PR2 của RFC-0002 chờ Tháng 9 chương trình (trừ khi có profile bậc 2/3 thật) |
| 3 | W3-1 → W3-2 → W3-3/4 | **Có** (đa node) | M + L | Spike quyết wire protocol |
| 4 | W4-1, W4-2 | Không | M | Giá trị cộng đồng |
| 5 | W2-1/2/3/6 | Không | L | Mốc Beta |
| 6 | W4-3/4/5 | Không | M | Hệ sinh thái |

---

## 13. Rủi ro và đối sách

| Rủi ro | Mức | Đối sách |
|:--|:--:|:--|
| v1.0 kín lịch, mở rộng làm loãng chất lượng bậc 1 | Cao | Tách người/PR; Chặng 1 tách khỏi đường tới hạn A2/Beta; R-7 giữ nguyên |
| Zenoh trẻ hơn DDS | Trung bình | Spike W3-1 là phép thử loại (Q-36); micro-ROS là phương án B |
| Black channel thêm lớp wrapper mới | Trung bình | Fuzz/replay test riêng; tái dùng mẫu `NETR` |
| Trace đa node phá vỡ tương thích | Trung bình | Chọn A/B trong RFC; corpus `fixtures/compliance/multinode/` khép kín |
| Token theo kênh phức tạp | Trung bình | Làm cùng W1B-RFC-2, không nhồi vào 1A |
| Giấy phép (Zenoh nhánh kép, Hawkbit) | Trung bình | Chọn nhánh Apache-2.0; ghi `NOTICE`; Q-11 đã chốt (EMQX không dùng) |
| Bo mạch thật về chậm | Cao | Phần không cần bo mạch kéo lên trước (tiền lệ TSK-S4-02/07/08/09 — firmware kiểm trên host và QEMU) |
| Mở rộng không có nhu cầu thật | Trung bình | Neo vào cổng nhu cầu 2026-10-25 + PF-3; không tự phát triển SLAM |

---

## 14. Điểm mở cần chốt

| # | Điểm mở | Chốt ở đâu |
|:--:|:--|:--|
| 1 | ~~Wire protocol node: Zenoh vs micro-ROS~~ | ✅ Q-36 (Zenoh; W3-1 là phép thử loại) |
| 2 | ~~Trace: mở rộng `trace.v1` (A) vs `trace.v2` (B)~~ | ✅ Q-32 (A) |
| 3 | ~~RFC-numeric gộp vào RFC-0007 hay tách riêng~~ — **tách riêng**: RFC-0007 (TSK-N0-03) giữ `gate.v1` nguyên byte | Đã rõ từ bản nháp Giai đoạn 1.5 |
| 4 | ~~`motion.*` là nguyên thủy riêng hay mở rộng `digital.out`~~ | ✅ Q-32 (nguyên thủy riêng) |
| 5 | ~~Mô hình token theo kênh~~ | ✅ Q-37 (thuê có hạn); con số ở RFC-motion |
| 6 | Chứng nhận an toàn: IN/OUT | ✅ Q-38 tạm thời OUT; IN/OUT thật: cổng C6 + `TODOS.md` #40 |
| 7 | ~~Q-11 phần mở (Hawkbit/EMQX)~~ | ✅ Q-11 |
| 8 | ~~MCP mạng dùng OAuth 2.1 theo spec~~ | ✅ Q-32; hiện thực ở W2-6 |
| 9 | ~~Node tham chiếu multi-node: ESP32-S3 + RP2350~~ | ✅ Q-33 |
| 10 | ~~Đội lõi làm node RP2350~~ | ✅ Q-33 (ngoại lệ ở PRD §14) |
| 11 | ~~Cầu ROS 2 / demo Nav2~~ | ✅ Q-34 (tích hợp, gate mọi lệnh tốc độ) |
| 12 | Mất liên lạc → về trạng thái an toàn cắt cả lệnh đang chạy: mở rộng `voice_fsm.md` §5 (lý do hủy mới, sự kiện đầu vào replay được, trạng thái an toàn theo từng cơ cấu); cắt lời xuyên chip (Pi → node, ngân sách 20 ms) | Chính sách ✅ Q-35; chi tiết ở RFC-node + sửa `voice_fsm.md` |
| 13 | `call_source` và xác nhận `ask` khi mọi kết nối tới node đều từ Pi; mã hoá ý định không phải JSON (KL-5) | RFC-node |
| 14 | ~~Nightly drift chặn build~~ | ✅ Q-32 (mở issue, không chặn) |

---

## 15. Khi thực thi — tài liệu phải cập nhật

Theo `CONTRIBUTING.md` §8 (mỗi sự thật có đúng một nơi, §8.1):

| Tài liệu | Cập nhật gì |
|:--|:--|
| `neuroedge-roadmap.md` | Bảng task §4–§8: trạng thái từng `W`-item khi hạ cánh (cấp `TSK-*` thật); §0 chỉ tổng quan; §10.2 dòng RFC |
| `CHANGELOG.md` `[Chưa phát hành]` | Mỗi task một mục |
| `neuroedge-prd.md` | Tiêu chí NFR-SEC; FR-HAL/FR-TGT khi RFC-0002/RFC-motion hạ cánh; `Q-N` mới ở §15; §14 nếu phạm vi đổi (RP2350 lõi, ROS 2/Nav2) |
| `TODOS.md` | Mục mới (node, trace, spike) — số tiếp theo sau số lớn nhất hiện có, không dùng lại; đóng #17/#31 khi xong; đọc lại #21, #36, #37, #39 |
| `docs/spec/threat_model.md` | §2c đa node + dòng mới cho motion/analog/vision |
| `docs/spec/tool_calling.md` | Gateway/node, MCP mạng, `call_source` qua Pi |
| `docs/spec/voice_fsm.md` | §5: dừng do mất liên lạc, hủy xuyên chip; §8: sự kiện mới |
| `docs/spec/simulation_coverage.md` | §2 ô cho nguyên thủy mới; §3 sự kiện `motion.*`; §4 dòng `NE1` đa node |
| `docs/spec/hal_mcu_review.md` | RB-3 cho `motion.*`; KL-1/KL-5 |
| `neuroedge-proposal.md` | Phụ lục A (HAL), Phụ lục C (vết ghi) — theo mẫu RFC |
| `CHANGELOG.md` · `CONTRIBUTING.md` | §2.5 danh sách workflow · §3.3 nếu bất biến đổi · `CONTRIBUTING.md` §6 thư mục mới |
| `docs/rfc/README.md` · `docs/user/README.md` | Dòng RFC; dòng tài liệu |
| `docs/rfc/*` | RFC-numeric, RFC-motion, RFC-node, RFC-vision-bậc23, RFC-pin-extends (RFC-0007 là của TSK-N0-03) |
| `NOTICE` | Zenoh (nhánh Apache-2.0), ROS 2/Nav2, MHS khi port |
| `docs/user/thuat-ngu.md` | Đã có mục FOFOCA, node, black channel, W-item, RFC nháp; cập nhật khi bản nháp được nhận |

---

## 16. Bước tiếp theo

1. **PR W0** (CI + tiêu chí NFR-SEC + `TODOS.md`) — không chạm vùng RFC.
2. **Soạn RFC-numeric**; RFC-0007 do TSK-N0-03 của bản nháp Giai đoạn 1.5 soạn.
3. **Đẩy RFC-0002 qua phê duyệt** (chữ ký kỹ thuật trưởng).
4. **Draft RFC-node + kế hoạch spike W3-1** (đã có bản nháp kèm theo:
   `draft-rfc-node-giao-thuc-dieu-phoi.md`).
5. Ghi Chặng 2/3 vào roadmap/`TODOS.md` dạng "thiết kế sẵn, chưa đặt lịch" **sau khi**
   các `Q-N` tương ứng được cấp. Số `Q-N` cấp lúc đó: Q-31 đang chờ cho NeuroBrain, và TSK-N0-01
   cần thêm hai số.

---

## Phụ lục A — Khung các RFC dự kiến

Mỗi khung dưới đây là dàn ý để chuyển thành RFC đầy đủ theo
`docs/rfc/0000-template.md` khi mở PR.

### A.1 RFC-0002 (đang thảo luận — cần phê duyệt)

- **Việc cần làm:** hoàn tất thảo luận theo hướng D4→A (mã của biên bản) đã chốt trong biên bản review
  (`docs/archive/rfc-0002-review-record.md`); lấy chữ ký kỹ thuật trưởng (tiêu chí ra V1a #1);
  hợp nhất PR2 (TSK-V1a-02..06) — không trước Tháng 9 chương trình, trừ khi có profile bậc 2/3 thật.
- **Nội dung đã sẵn:** mở enum target lên 6; `TARGET_TIERS` thuộc lõi, `board.toml`
  không tự khai bậc; 3 bất biến test theo bậc; `vision.in` tách §9.1.

### A.2 RFC-0007 *(đã giữ chỗ — TSK-N0-03, bản nháp Giai đoạn 1.5)* — `digital.in` + I2C chỉ đọc + ADC

- **Vấn đề:** HAL có năm nguyên thủy, và `sensor.read` đã đọc cảm biến I2C qua driver
  (`simulation_coverage.md` §2). Còn thiếu: đọc mức logic (nút nhấn/công tắc — `digital.in`), truy
  cập bus I2C thô/quét (N3), ADC.
- **Đề xuất:** thêm `digital.in`; bus I2C **chỉ đọc** theo allowlist thiết bị; ADC theo
  kết quả spike; `lab_read` có cờ.
- **Ảnh hưởng:** `board.v1` (capability mới + khai báo phong bì N2); `gate.v1` **không đổi**
  (tiêu chí ra N0 #2); `sim` phải có mô hình tương ứng nhưng không giàu hơn bo mạch.
- **Chủ trì:** TSK-N0-03 (V2). Bản nháp này dùng kết quả, không soạn lại.
- **Nguồn:** bản nháp Giai đoạn 1.5 (N0, N3).

### A.3 RFC-numeric — `evaluate.type: numeric`

- **Vấn đề:** `schemas/gate.v1.json` chỉ nhận `bool`/`level`/`choice`; không diễn đạt
  được ngưỡng số (`pressure < 8 bar`) — `TODOS.md` #30.
- **Đề xuất:** thêm `numeric` + ngữ nghĩa siết chặt cho nguyên tắc 2 + nút trong `NETR`.
- **Ảnh hưởng:** `gate.v1` (đổi enum đã đóng băng → RFC), `NETR` layout, walker C.
- **Số:** kế tiếp sau 0007 (0007 đã giữ chỗ).

### A.4 RFC-motion — `motion.*` + `analog.in` + phong bì N2 + token theo kênh

- **Vấn đề:** robot cần chuyển động và cảm biến tương tự; `digital.out` không diễn tả
  được vòng phản hồi/duty; token hôm nay mang tập chân, một lần mỗi chân, chưa có kênh và thời
  lượng tối đa.
- **Đề xuất:** nguyên thủy `motion.*` (motor/servo) + `analog.in`; mở rộng phong bì N2 của
  RFC-0007 sang `motion.*`; trạng thái an toàn khai theo từng cơ cấu (Q-35); token **thuê có hạn** theo Q-37 (kênh +
  biên độ tối đa + thời hạn ngắn, mỗi lệnh qua gate gia hạn, hết hạn ⇒ trạng thái an toàn); bố cục `NETR` mới (tăng `layout_version`, gộp với `TODOS.md` #36 để chỉ tăng một
  lần).
- **Ảnh hưởng:** `board.v1`, `NETR`, walker C, `ne_token.c`, `sim`. Gate vẫn thuần: phong bì và
  tích luỹ thời gian ở HAL/runtime (bất biến 4).
- **An toàn:** quyết cờ "vẫn cắt khi đã chạy" (`TODOS.md` #39, `voice_fsm.md` §5.3, §10); sự
  kiện `motion.*` đặt cạnh `actuator_command`/`actuator_aborted` (`simulation_coverage.md` §3).
- **Phụ thuộc:** RFC-numeric; bo mạch thật.

### A.5 RFC-vision-bậc23 — khoá `vision.in` cho bậc 2/3

- **Vấn đề:** `vision.in` mới có danh sách đầu vào đã biết (RFC-0002 §9.1), chưa có hợp đồng
  và luật riêng tư. Thuộc Khối V1b — thị giác trên `linux` và `sim` trước (`neuroedge-roadmap-phase2.md:173`).
- **Đề xuất:** chốt `fps`/`modes[]`/`pixel_format`; kết quả quy về `bool/level/choice`
  trước gate; không khung hình thô vào trace; fail-closed khi mất camera/model.
- **Ảnh hưởng:** `board.v1`; fixture vision; bất biến "sim không giàu hơn bo mạch".

### A.6 RFC-node — giao thức điều phối node

- **Xem bản nháp kèm theo:** `draft-rfc-node-giao-thuc-dieu-phoi.md`.

### A.7 RFC-pin-extends — ghim `extends` bằng digest

- **Vấn đề:** `extends` ghim theo phiên bản, không ghim nội dung; registry không kiểm
  soát có thể tái publish (`TODOS.md` #11, #15).
- **Đề xuất:** cho phép `@<ver>#sha256:…`; đổi `pattern` của `gate.v1.json`.
- **Ảnh hưởng:** `gate.v1`, ngữ nghĩa phân giải, `digests.lock`; cần kỹ thuật trưởng.

---

## Phụ lục B — Truy vết W-item với nguồn

| W-item | Yêu cầu / nguồn liên quan |
|:--|:--|
| W0-1 | NFR-SEC-02→06, 08; `neuroedge-prd.md:863` |
| W0-2/3/4 | Q-11 (`NOTICE`), `CONTRIBUTING.md` §4; nightly `upstream-drift` |
| W0-5 | `TODOS.md` #31, #17 |
| W1A-1 | FR-HAL-01; `neuroedge-proposal.md:458`; RFC-0005 |
| W1A-2 | FR-HAL-01; `TODOS.md` #30; RFC-numeric |
| W1A-3 | RFC-0002 §3c.2 |
| W1B-RFC-1 | FR-TGT-08, RFC-0002; RFC-0007 (TSK-N0-03); bản nháp Giai đoạn 1.5 N0/N3 |
| W1B-RFC-2 | FR-HAL-01; N2 (bản nháp Giai đoạn 1.5 §7); crash-safe (`neuroedge-roadmap-phase1-5.md:128,369`); `voice_fsm.md` §5; `TODOS.md` #39 |
| W1B-RFC-3 | RFC-0002 §9.1; `TODOS.md` #14; NFR-PRIV |
| W2-1..7 | NFR-SEC-02→09; FR-FLT-01; FR-OTA-01..04; TSK-K2-04 (W2-1); TSK-P2-04 (W2-6); `TODOS.md` #1, #3, #24, #29 |
| W3-1..6 | FR-TGT-08; `docs/spec/tool_calling.md:216`; TSK-P2-05 (W3-5); FR-CI-07 (NE4002, chỉ bậc 1); `simulation_coverage.md` §4; `voice_fsm.md` §5 |
| W4-1 | `neuroedge-roadmap-phase2.md:218`; Q-11; FR-MDL-10 |
| W4-2 | FR-GOV-03/04; TSK-P1-01..04 |
| W4-3 | FR-REG-01..07; `TODOS.md` #11, #15; TR-4 |
| W4-4 | TSK-P2-01 |
| W4-5 | Q-29; `TODOS.md` #33 |
| W4-6 | Q-11 (đã chốt); `TODOS.md` #17; OFL font (bản nháp Giai đoạn 1.5) |

---

## Phụ lục C — Quyết định chờ cấp mã Q-N

Các điểm dưới đây cần một mục `Q-N` trong `neuroedge-prd.md` §15. Hướng kế hoạch đã được nhận (Q-32, 2026-09-25); ✅ là đã chốt:

| # | Câu hỏi quyết định | Gợi ý |
|:--:|:--|:--|
| 1 | Wire protocol node: Zenoh-pico hay micro-ROS? | ✅ **Q-36: Zenoh-pico, W3-1 là phép thử loại** (2026-09-25) |
| 2 | Trace đa node: mở rộng `trace.v1` hay `trace.v2`? | ✅ **Q-32: mở rộng `trace.v1`** (2026-09-25) |
| 3 | RFC-numeric gộp hay tách khỏi RFC-0007? | ✅ **Tách** — RFC-0007 (TSK-N0-03) giữ `gate.v1` nguyên byte; không cần `Q-N` |
| 4 | `motion.*` nguyên thủy riêng hay mở rộng `digital.out`? | ✅ **Q-32: nguyên thủy riêng** (2026-09-25) |
| 5 | Token theo kênh: phạm vi gồm gì? | ✅ **Q-37: thuê có hạn — kênh + biên độ tối đa + thời hạn ngắn, gia hạn mỗi lệnh** (2026-09-25) |
| 6 | Chứng nhận an toàn chức năng: IN hay OUT? | ✅ **Q-38: OUT tạm thời**, dừng khẩn phần cứng bắt buộc; IN/OUT thật sau C6 và `TODOS.md` #40 (2026-09-25) |
| 7 | Q-11 phần mở: Hawkbit EPL-2.0, EMQX BSL? | ✅ **Q-11 đã chốt** (2026-09-25) |
| 8 | MCP mạng: OAuth 2.1 theo spec? | ✅ **Q-32: có** (2026-09-25) |
| 9 | Node tham chiếu: ESP32-S3 + RP2350? | ✅ **Q-33: ESP32-S3 + RP2350 (đội lõi port)** (2026-09-25) |
| 10 | Đội lõi có làm node RP2350 không? Hiện trái `neuroedge-roadmap-phase2.md:252`, `neuroedge-proposal.md:1366` và PRD §14 ("đội lõi tự port thêm biến thể ngoài bậc 1 và bậc 2: hoãn vô thời hạn") | ✅ **Q-33: đội lõi port** (2026-09-25) |
| 11 | Cầu ROS 2 và demo Nav2 có trong phạm vi không? `neuroedge-roadmap-phase2.md:218` loại dẫn đường tự hành, không ngoại lệ; PRD §14 là sổ ngoài phạm vi duy nhất | ✅ **Q-34: tích hợp, gate mọi lệnh tốc độ** (2026-09-25) |
| 12 | Mất liên lạc có được cắt lệnh **đang chạy** không? `voice_fsm.md` §5.3 hôm nay chỉ cho tắt máy làm vậy | ✅ **Q-35: theo từng cơ cấu, mặc định dừng** (2026-09-25) |
| 13 | Nightly drift có chặn build không? Hiện `nightly-hardware.yml:96-99` cố ý chỉ báo | ✅ **Q-32: mở issue, không chặn** (2026-09-25) |
