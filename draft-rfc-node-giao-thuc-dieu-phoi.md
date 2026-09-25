# RFC (chưa cấp số): Giao thức điều phối node cho robot phân tầng

> **Đây là bản nháp.** Tệp nằm ngoài `docs/rfc/` vì **chưa được cấp số RFC**. Khi mở PR
> RFC theo `CONTRIBUTING.md` §3 (PR chỉ chứa tệp RFC), bản này sẽ được sao sang
> `docs/rfc/NNNN-<slug>.md` theo `docs/rfc/0000-template.md` và cấp số chính thức.

| | |
|:---|:---|
| **Mã RFC** | *(chưa cấp — cấp khi mở PR RFC)* |
| **Tiêu đề** | Giao thức điều phối node cho robot phân tầng (black channel) |
| **Hợp đồng bị ảnh hưởng** | `trace.v1` (chắc chắn) · ngữ nghĩa phân giải gate *(có thể — xem §3.6)* · `NETR` *(không, trừ khi chọn nút mới)* |
| **Yêu cầu PRD liên quan** | FR-TGT-08, FR-HAL-01, FR-CI-07, FR-MDL-10, NFR-SEC-04/05/09 |
| **Người đề xuất** | *(điền khi mở)* |
| **Ngày mở** | *(chưa mở)* |
| **Trạng thái** | Bản nháp — chưa thảo luận |
| **Người phê duyệt** | Kỹ thuật trưởng **nếu** chạm ngữ nghĩa phân giải gate; nếu chỉ chạm trace thì theo quy trình RFC thường |

**Liên quan:** `draft-ke-hoach-mo-rong-robot-fofoca.md` (kế hoạch mẹ, Chặng 3);
`docs/spec/threat_model.md`; `docs/spec/tool_calling.md`; `docs/rfc/0002-…` (phân tầng target);
IEC 61784-3 (black channel).

---

## 1. Vấn đề

Một robot kiểu FOFOCA gồm **một não (Pi 5) và nhiều bộ điều khiển (MCU)** cùng phối hợp:
motor, display, tay máy. NeuroEdge hôm nay coi mỗi môi trường thực thi là **độc lập**:

- Mỗi target là một runtime riêng (`sim`, `linux`, `esp32s3`); không có khái niệm một
  agent điều phối nhiều node.
- `docs/spec/tool_calling.md:216` đã phác "MCP cho thiết bị đi qua gateway hoặc máy
  `linux`", nhưng đó là **một thiết bị sau gateway**, không phải nhiều MCU phối hợp.
- `trace.v1` gắn cứng **một** `target`/`board_id` cho cả phiên
  (`schemas/trace.v1.json:15,25,29`) — không có chỗ cho danh tính node.
- Chưa có transport mạng nào được mở (`TODOS.md` #24; NFR-SEC-09): v1.0 chỉ stdio.

Hệ quả: không thể diễn đạt "cùng một ý định, nhiều node cùng thực hiện", cũng không có
bằng chứng replay cho một phiên trải trên nhiều chip.

## 2. Vì sao lược đồ hiện tại không giải quyết được

| Mệnh đề hiện tại | Vì sao chặn multi-node |
|:--|:--|
| `metadata.target` enum 3 giá trị (`trace.v1.json:27`) | Không có chỗ khai nhiều node; node RP2350 còn chưa có target (chờ RFC-0002) |
| `events[].additionalProperties: false` (`trace.v1.json:58`) | Không thể thêm `node_id` cấp sự kiện nếu không đổi lược đồ |
| `board.py` `SUPPORTED_TARGETS = ("sim","linux","esp32s3")` (`python/neuroedge/hal/board.py:58`) | Node mới phải qua RFC-0002 (bậc 3 `rp2350`) |
| Bất biến fail-closed on-device (`neuroedge-proposal.md` §3.4, Phụ lục H.3) | **Cấm** giải pháp "gate tập trung trên Pi" — nếu Pi mất, actuator phải tự về an toàn |
| MCP chỉ stdio (`TODOS.md` #24) | Chưa có kênh mạng nào để nói chuyện với node từ xa |

## 3. Thay đổi đề xuất

### 3.1 Mô hình node

- **Node** = một môi trường thực thi có `node_id`, vai trò, HAL, **gate riêng**, danh tính
  mật mã, và trạng thái an toàn cục bộ.
- Agent (System 1/2) chạy trên **Pi** phát **ý định** (intent/ToolCall). Mỗi node **tự
  lượng giá gate của nó** với dữ kiện cục bộ rồi mới chạm actuator. **Không có gate tập
  trung** (bất biến B2 của kế hoạch mẹ).
- Phân biệt rõ: **Fleet OS** (nhiều thiết bị độc lập — Khối 2) khác **multi-node** (một
  robot nhiều MCU — RFC này).

### 3.2 Wire protocol

- Đề xuất: **Zenoh-pico** trên MCU + `zenohd` trên Pi (nhánh giấy phép **Apache-2.0** của
  Zenoh; `NOTICE` theo `CONTRIBUTING.md` §4).
- Transport **không được tin**: là "black channel" theo IEC 61784-3. Mọi bảo đảm an toàn
  nằm ở §3.3 và gate từng node.
- Phương án B: **micro-ROS / Micro XRCE-DDS** (Apache-2.0) nếu spike cho kết quả tốt hơn
  hoặc nếu ưu tiên ROS 2 native. **Chốt bằng spike** (xem §7).

### 3.3 Lớp an toàn kiểu black channel

Mỗi thông điệp điều phối mang thêm trường bảo vệ:

| Trường | Vai trò |
|:--|:--|
| `node_id` / `conn_id` | Định danh node và kết nối; chống giả mạo chéo node |
| `seq` | Chống phát lại và mất thứ tự; cửa sổ chấp nhận hữu hạn |
| `crc` | Phát hiện hỏng bit trên kênh không tin cậy |
| `timestamp` / `ttl` | Chống lệnh cũ; khớp token TTL = p95 × 3 sẵn có |
| `heartbeat` | Watchdog Pi↔node; mất → node từ chối ý định mới và về trạng thái an toàn |

Trạng thái an toàn cục bộ (L0): kéo xuống phần cứng / watchdog / giới hạn dòng — phần
mềm **không** cứu được khi crash/SIGKILL (`neuroedge-roadmap-phase1-5.md:128,369`).

### 3.4 Trace hợp nhất

Hai phương án (quyết định ở đây, trước khi viết RFC đầy đủ):

| | Phương án A (khuyến nghị cho v1.x) | Phương án B |
|:--|:--|:--|
| Cách làm | `metadata.nodes[]` tùy chọn + quy ước `data.node_id` trong sự kiện | `trace.v2` với `nodes[]` và `node_id` cấp sự kiện |
| Tương thích | Không phá: `metadata.additionalProperties: true` (`trace.v1.json:39`) | Phá: phải tăng phiên bản lược đồ |
| Chi phí | Thấp; cần tài liệu hoá quy ước + fixture mới (RFC) | Cao: migrate corpus + `digests.lock` |
| Rủi ro | Quy ước "mềm" nằm trong `data` | Rõ ràng, chuẩn mực |

Dù chọn phương án nào: **thêm một vết ghi chuẩn mực mới = RFC** (`CONTRIBUTING.md` §3).

### 3.5 Gateway và MCP

- Tái dùng hướng TSK-P2-05 (MCP gateway) làm điểm vào cho node; **không** dùng MCP làm
  wire protocol MCU (JSON-RPC nặng).
- MCP qua mạng giữ ở mặt agent: **Streamable HTTP + OAuth 2.1** theo spec MCP 2026-07-28,
  sau khi có mTLS (NFR-SEC-04) và test #29.

### 3.6 CLI và `verify`

- `verify` mở rộng cho cụm node: so phán quyết và trạng thái actuator giữa các node;
  lệch → `SafetyRegressionError` (NE4002, FR-CI-07).
- Không thêm cờ CLI mới ở v1; thiết kế cấu hình node nằm trong `agent.toml` (mục
  `[nodes]`, đề xuất — chốt trong RFC đầy đủ).

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có, nếu chọn A (thêm trường tùy chọn trong `metadata`); Không, nếu chọn B |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Không |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Chỉ khi chọn B |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không (gate không đổi) |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Có — thêm vết ghi đa node chuẩn mực (RFC) |
| Gate nào trong `digests.lock` đổi digest? | Không |
| Bố cục `NETR` hoặc walker C phải đổi? | Không, trừ khi phát sinh nút mới |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Có — thêm ca multi-node (corpus khép kín) |

## 5. Ảnh hưởng an toàn

**Không cho phép gate trở nên lỏng hơn.** RFC này chỉ thêm đường đi mới, tất cả đều phải
qua gate từng node. Các mối đe dọa mới cần dòng trong `docs/spec/threat_model.md` §2c:

| Đường tắt | Chặn bởi |
|:--|:--|
| Giả mạo node (gửi intent thay node khác) | Định danh + khoá liên kết (PSK/mTLS); `node_id` trong wrapper |
| Phát lại thông điệp ALLOW cũ | `seq` + nonce + `ttl`; token TTL = p95 × 3 |
| Sửa thông điệp trên kênh | CRC + (tuỳ chọn) MAC; transport không được tin |
| Bỏ đói/thao túng heartbeat | Watchdog → trạng thái an toàn cục bộ |
| Pi bị chiếm, gửi lệnh độc | Gate từng node vẫn là chốt cuối; phong bì N2 giới hạn duty/rate |
| Node bị chiếm, tự mint token | Ngoài phạm vi v1 (như threat model §3); mốc ở `TODOS.md` #2 |

Nếu chọn B (trace.v2) hoặc nếu RFC chạm ngữ nghĩa phân giải gate: cần kỹ thuật trưởng.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Gate tập trung trên Pi | Phá fail-closed on-device khi mất mạng (B2; Phụ lục H.3) |
| MQTT làm wire | "Broker paradox"; broker vướng Q-11 (EMQX BSL, Mosquitto EPL) |
| DDS/ROS 2 làm wire | Không lên MCU; multicast nặng; kéo máy trạng thái ra khỏi thiết bị |
| Giao thức nhị phân tự thiết kế | Chi phí xây + bảo trì cao, không hệ sinh thái; phần "black channel" dù sao vẫn phải tự viết |
| MCP làm wire MCU | JSON-RPC nặng; không hợp tài nguyên vi điều khiển |
| HTTP/REST thuần | Không có pub/sub, heartbeat, discovery; tự chế nhiều hơn Zenoh |

## 7. Bằng chứng kiểm chứng

- [ ] **Spike W3-1:** Zenoh-pico trên ESP32-S3 + RP2350 ↔ `zenohd` trên Pi: độ trễ, RAM,
      flash, reconnect; so sánh micro-ROS; ghi báo cáo vào `docs/reports/`.
- [ ] Fault injection: drop / delay / replay / tamper → **không ALLOW nào lọt**; mất link
      → node về trạng thái an toàn.
- [ ] Replay trace hợp nhất đa node xanh trong CI.
- [ ] Fuzz wrapper black channel (mẫu tái dùng từ `NETR`).
- [ ] Corpus tool call mở rộng ca multi-node theo luật khép kín hai chiều.
- [ ] `neuroedge gate lint` và `neuroedge verify` vẫn xanh; 0 test skip.
- [ ] `NOTICE` cập nhật nếu nhận mã Zenoh/micro-ROS (5 nghĩa vụ `CONTRIBUTING.md` §4).

## 8. Việc phải làm khi chấp thuận

- [ ] Cập nhật `schemas/trace.v1.json` (phương án A) hoặc mở `trace.v2` (phương án B)
- [ ] Cập nhật `docs/spec/threat_model.md` §2c và `docs/spec/tool_calling.md`
- [ ] Cập nhật `neuroedge-prd.md` nếu có FR bị ảnh hưởng; quyết định mới → `Q-N` ở §15
- [ ] Cập nhật `neuroedge-roadmap.md` với `TSK-*` thật cho W3-1..W3-6
- [ ] Thêm fixture + test; vết ghi chuẩn mực mới: `scripts/check_digests.py` nếu cần
- [ ] Cập nhật dòng RFC trong `docs/rfc/README.md` và một mục `CHANGELOG.md`
      `[Chưa phát hành]`
- [ ] `NOTICE`: Zenoh (nhánh Apache-2.0) hoặc micro-ROS

## Phụ lục — Câu hỏi mở của bản nháp

1. Wire protocol: Zenoh hay micro-ROS? (spike quyết)
2. Trace: A hay B?
3. Mô hình cấu hình node trong `agent.toml` (`[nodes]`) — hình dạng cụ thể?
4. Node tham chiếu: ESP32-S3 + RP2350 (khuyến nghị) hay chỉ ESP32-S3 trước?
5. Khoá liên kết node: PSK đối xứng trước hay mTLS ngay?
