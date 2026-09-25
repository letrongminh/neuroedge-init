# RFC (chưa cấp số): Giao thức điều phối node cho robot phân tầng

> **Đây là bản nháp.** Tệp nằm ngoài `docs/rfc/` vì **chưa được cấp số RFC**. Khi mở PR
> RFC theo `CONTRIBUTING.md` §3 (PR chỉ chứa tệp RFC), bản này sẽ được sao sang
> `docs/rfc/NNNN-<slug>.md` theo `docs/rfc/0000-template.md` với số kế tiếp (`docs/rfc/README.md`;
> 0007 đã được TSK-N0-03 giữ chỗ).
>
> **Đối chiếu 2026-09-25** (sau TSK-S4-09 và TSK-S2-07): các ràng buộc mới từ đặc tả đã chốt
> nằm ở §3.1, §3.3, §3.4, §5 và Phụ lục. Các điểm chờ quyết định đã chốt ngày 2026-09-25
> (Q-32 → Q-37, `neuroedge-prd.md` §15); câu hỏi còn mở ở Phụ lục.

| | |
|:---|:---|
| **Mã RFC** | *(chưa cấp — cấp khi mở PR RFC)* |
| **Tiêu đề** | Giao thức điều phối node cho robot phân tầng (black channel) |
| **Hợp đồng bị ảnh hưởng** | `trace.v1` *(không sửa `schemas/` — Q-32 chọn phương án A, §3.4)* · đặc tả dòng `NE1` (`simulation_coverage.md` §4) · hợp đồng thu hồi lệnh (`voice_fsm.md` §5) · ngữ nghĩa phân giải gate *(có thể — xem §3.6)* · `NETR` *(không, trừ khi chọn nút mới)* |
| **Yêu cầu PRD liên quan** | FR-TGT-08, FR-HAL-01, FR-CI-07, FR-MDL-10, NFR-SEC-04/05/09 |
| **Người đề xuất** | *(điền khi mở)* |
| **Ngày mở** | *(chưa mở)* |
| **Trạng thái** | Bản nháp — chưa thảo luận |
| **Người phê duyệt** | Kỹ thuật trưởng **nếu** chạm ngữ nghĩa phân giải gate; nếu chỉ chạm trace thì theo quy trình RFC thường |

**Liên quan:** `draft-ke-hoach-mo-rong-robot-fofoca.md` (kế hoạch mẹ, Chặng 3);
`docs/spec/threat_model.md`; `docs/spec/tool_calling.md`; `docs/spec/voice_fsm.md` (thu hồi lệnh);
`docs/spec/simulation_coverage.md` §4 (vết ghi từ thiết bị); `docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md`
(phân tầng target); IEC 61784-3 (black channel).

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
| `events[].additionalProperties: false` (`trace.v1.json:58`) | Không thể thêm `node_id` cấp sự kiện nếu không đổi lược đồ — và cả đặc tả dòng `NE1`, vốn có đúng ba khoá (`simulation_coverage.md` §4) |
| `board.py` `SUPPORTED_TARGETS = ("sim","linux","esp32s3")` (`python/neuroedge/hal/board.py:58`) | Node mới phải qua RFC-0002 (bậc 3 `rp2350`) |
| Bất biến fail-closed on-device (`neuroedge-proposal.md` §3.4, Phụ lục H.3) | **Cấm** giải pháp "gate tập trung trên Pi" — nếu Pi mất, actuator phải tự về an toàn |
| MCP chỉ stdio (`TODOS.md` #24) | Chưa có kênh mạng nào để nói chuyện với node từ xa |

## 3. Thay đổi đề xuất

### 3.1 Mô hình node

- **Node** = một môi trường thực thi có `node_id`, vai trò, HAL, **gate riêng**, danh tính
  mật mã, và trạng thái an toàn cục bộ.
- Agent (System 1/2) chạy trên **Pi** phát **ý định** (intent/ToolCall). Mỗi node **tự
  lượng giá gate của nó** với dữ kiện cục bộ rồi mới chạm actuator. **Không có gate tập
  trung** (luật BT2 của kế hoạch mẹ).
- **Danh tính** dựng trên `device_info` sẵn có của TSK-S4-09 (`device_id`, `boot_id`): mỗi phiên của
  một thiết bị đã tự khai, và host dựng `metadata` từ đó (`simulation_coverage.md` §4).
- **Ý định trên wire**, không phải ALLOW hay token: node tự lượng giá, tự cấp và tự tiêu token;
  nonce không rời sổ token (`docs/spec/threat_model.md` §2). MCU không có parser JSON (KL-5,
  `hal_mcu_review.md`), nên mã hoá ý định phải không phải JSON, hoặc phải sửa KL-5.
- Phân biệt rõ: **Fleet OS** (nhiều thiết bị độc lập — Khối 2) khác **multi-node** (một
  robot nhiều MCU — RFC này).

### 3.2 Wire protocol

- Đề xuất: **Zenoh-pico** trên MCU + `zenohd` trên Pi (nhánh giấy phép **Apache-2.0** của
  Zenoh; `NOTICE` theo `CONTRIBUTING.md` §4).
- Transport **không được tin**: là "black channel" theo IEC 61784-3. Mọi bảo đảm an toàn
  nằm ở §3.3 và gate từng node.
- Phương án B: **micro-ROS / Micro XRCE-DDS** (Apache-2.0). **Đã chốt ở Q-36:** Zenoh-pico; spike W3-1
  là phép thử loại (ba ngưỡng ở PRD §15); chỉ đổi sang micro-ROS khi Zenoh trượt và micro-ROS đạt (§7).

### 3.3 Lớp an toàn kiểu black channel

Mỗi thông điệp điều phối mang thêm trường bảo vệ:

| Trường | Vai trò |
|:--|:--|
| `node_id` / `conn_id` | Định danh node và kết nối; chống giả mạo chéo node |
| `seq` | Chống phát lại và mất thứ tự; cửa sổ chấp nhận hữu hạn |
| `crc` | Phát hiện hỏng bit trên kênh không tin cậy |
| `epoch` / `boot_id` / `ttl` | Chống ý định cũ. Đồng hồ `offset_ms` của mỗi thiết bị đếm từ `device_info` của nó và đặt lại theo `boot_id`, nên dấu thời gian giữa các thiết bị không so được; TTL token (p95 × 3) chạy trên đồng hồ riêng của node và không bảo vệ wire |
| `heartbeat` | Watchdog Pi↔node; mất → node từ chối ý định mới và về trạng thái an toàn |

**Mất liên lạc là một lần dừng kiểu tắt máy.** `voice_fsm.md` §5.3 hôm nay chỉ cho tắt máy (SIGTERM) cắt
một lệnh đã giao. RFC này phải sửa §5 đó: lý do `actuator_aborted.reason` mới, một sự kiện đầu vào
"mất liên lạc" để replay tính lại được lần hủy, và trạng thái an toàn khai theo từng cơ cấu (**Q-35**: không khai thì dừng) —
cắt một xung mở chốt đang chạy là khoá cửa lại (`voice_fsm.md` §5.3). Với `motion.*`, token thuê có hạn
(**Q-37**) tự hết hạn khi không còn lệnh, nên mất liên lạc dẫn tới dừng mà không cần phát hiện riêng.

**Cắt lời xuyên chip.** Máy trạng thái hội thoại chạy trên Pi, còn lệnh đang chờ có thể nằm ở node.
§5.2 của `voice_fsm.md` đòi hủy trong ≤ 20 ms và đóng token (`ne_token_close`); RFC này phải định
nghĩa thông điệp hủy Pi → node và ngân sách thời gian của nó (RB-3, `hal_mcu_review.md`).

Trạng thái an toàn cục bộ (tầng T0 của kế hoạch mẹ): kéo xuống phần cứng / watchdog / giới hạn dòng — phần
mềm **không** cứu được khi crash/SIGKILL (`neuroedge-roadmap-phase1-5.md:128,369`).

### 3.4 Trace hợp nhất

**Q-32 (2026-09-25) chọn phương án A.** Bảng giữ lại làm lý do:

| | Phương án A (khuyến nghị cho v1.x) | Phương án B |
|:--|:--|:--|
| Cách làm | `metadata.nodes[]` tùy chọn + quy ước `data.node_id` trong sự kiện | `trace.v2` với `nodes[]` và `node_id` cấp sự kiện |
| Tương thích | Không phá: `metadata.additionalProperties: true` (`trace.v1.json:39`) | Phá: phải tăng phiên bản lược đồ |
| Chi phí | Thấp; **không sửa `schemas/`** (`metadata` mở, `data` tự do — tiền lệ RFC-0002, `TODOS.md` #1); tài liệu hoá quy ước ở `simulation_coverage.md` §3–§4 | Cao: migrate corpus; đổi cả đặc tả dòng `NE1` |
| Rủi ro | Quy ước "mềm" nằm trong `data` | Rõ ràng, chuẩn mực |

Dù chọn phương án nào: mỗi thiết bị có đồng hồ `offset_ms` riêng, nên trace hợp nhất phải căn đồng
hồ. Vết ghi đa node đặt ở `fixtures/compliance/multinode/` (corpus khép kín), **không** ở
`fixtures/traces/`: thư mục đó giữ đúng ba vết ghi chuẩn mực (`voice_fsm.md` §9), và tệp thứ tư làm
gãy test và đổi vector firmware.

### 3.5 Gateway và MCP

- Tái dùng hướng TSK-P2-05 (MCP gateway — đã lên kế hoạch, chưa bắt đầu) làm điểm vào cho node; **không** dùng MCP làm
  wire protocol MCU (JSON-RPC nặng).
- MCP qua mạng giữ ở mặt agent: **Streamable HTTP + OAuth 2.1** theo spec MCP 2026-07-28,
  sau khi có mTLS (NFR-SEC-04) và test #29.

### 3.6 CLI và `verify`

- `verify` mở rộng cho cụm node: so phán quyết và trạng thái actuator giữa các node;
  lệch → `SafetyRegressionError` (NE4002, FR-CI-07 — chỉ phủ target bậc 1). Dựng trên
  `verify --targets esp32s3 --port` đã có (TSK-S4-09); chưa hiện thực thì thoát mã 2 (bất biến 10).
- Không thêm cờ CLI mới ở v1; thiết kế cấu hình node nằm trong `agent.toml` (mục
  `[nodes]`, đề xuất — chốt trong RFC đầy đủ).

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — phương án A (Q-32) chỉ thêm trường tùy chọn trong `metadata` |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Không |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không (Q-32) |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không (gate không đổi) |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không — vết ghi đa node ở `fixtures/compliance/multinode/` |
| Gate nào trong `digests.lock` đổi digest? | Không |
| Bố cục `NETR` hoặc walker C phải đổi? | Không, trừ khi phát sinh nút mới |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Có — thêm ca multi-node (corpus khép kín) |

## 5. Ảnh hưởng an toàn

**Không cho phép gate trở nên lỏng hơn.** RFC này chỉ thêm đường đi mới, tất cả đều phải
qua gate từng node. Các mối đe dọa mới cần dòng trong `docs/spec/threat_model.md` §2c:

| Đường tắt | Chặn bởi |
|:--|:--|
| Giả mạo node (gửi intent thay node khác) | Định danh + khoá liên kết (PSK/mTLS); `node_id` trong wrapper |
| Phát lại ý định cũ | `seq` + epoch/`boot_id` + cửa sổ; ALLOW và token không đi qua wire (node tự lượng giá) |
| Sửa thông điệp trên kênh | CRC + (tuỳ chọn) MAC; transport không được tin |
| Bỏ đói/thao túng heartbeat | Watchdog → trạng thái an toàn cục bộ |
| Pi bị chiếm, gửi lệnh độc | Gate từng node vẫn là chốt cuối; phong bì N2 giới hạn duty/rate. **Chưa đủ:** `call_source` gắn theo kết nối (`tool_calling.md` §5), mà mọi kết nối tới node đều từ Pi — hoặc node không phân biệt được nguồn, hoặc Pi chuyển tiếp nguồn và một Pi bị chiếm giả được `local_grammar`. Xác nhận `ask` (Q-26) cũng đi qua Pi. Cần hàng riêng ở `threat_model.md` §2c |
| Cắt lời trên Pi, lệnh đang chờ ở node | Thông điệp hủy Pi → node trong ngân sách của `voice_fsm.md` §5.2 — chưa thiết kế (§3.3) |
| Node bị chiếm, tự mint token | Ngoài phạm vi v1 (như threat model §3); mốc ở `TODOS.md` #2 |

Nếu RFC chạm ngữ nghĩa phân giải gate: cần kỹ thuật trưởng.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Gate tập trung trên Pi | Phá fail-closed on-device khi mất mạng (luật BT2 của kế hoạch mẹ; Phụ lục H.3) |
| MQTT làm wire | "Broker paradox" — thêm một broker giữa não và node trong cùng một robot. (Q-11: EMQX không dùng; broker giấy phép dễ dãi chỉ dành cho Fleet OS, Khối 2) |
| DDS/ROS 2 làm wire | Không lên MCU; multicast nặng; kéo máy trạng thái ra khỏi thiết bị |
| Giao thức nhị phân tự thiết kế | Chi phí xây + bảo trì cao, không hệ sinh thái; phần "black channel" dù sao vẫn phải tự viết |
| MCP làm wire MCU | JSON-RPC nặng; không hợp tài nguyên vi điều khiển |
| HTTP/REST thuần | Không có pub/sub, heartbeat, discovery; tự chế nhiều hơn Zenoh |

## 7. Bằng chứng kiểm chứng

- [ ] **Spike W3-1 (phép thử loại, Q-36):** Zenoh-pico trên ESP32-S3 và RP2350 (Q-33) ↔ `zenohd` trên Pi:
      p99 Pi → node ≤ 20 ms, SRAM nội ≤ 40 KB, nối lại ≤ 2 s, kèm flash; trượt ⇒ đo micro-ROS cùng điều kiện;
      ghi báo cáo vào `docs/reports/`.
- [ ] Fault injection: drop / delay / replay / tamper → **không ALLOW nào lọt**; mất link
      → node về trạng thái an toàn — kiểm trên bo mạch thật (QEMU không giả lập GPIO, `TODOS.md` #21).
- [ ] Replay trace hợp nhất đa node xanh trong CI.
- [ ] Fuzz wrapper black channel (mẫu tái dùng từ `NETR`).
- [ ] Corpus tool call mở rộng ca multi-node theo luật khép kín hai chiều.
- [ ] `neuroedge gate lint` và `neuroedge verify` vẫn xanh; 0 test skip.
- [ ] `NOTICE` cập nhật nếu nhận mã Zenoh/micro-ROS (5 nghĩa vụ `CONTRIBUTING.md` §4).

## 8. Việc phải làm khi chấp thuận

- [ ] Phương án A (Q-32): không sửa `schemas/` — tài liệu hoá quy ước ở `simulation_coverage.md` §3–§4
- [ ] Sửa `docs/spec/voice_fsm.md` §5 (dừng do mất liên lạc, hủy xuyên chip) và §8 (sự kiện mới)
- [ ] Cập nhật `docs/spec/threat_model.md` §2c và `docs/spec/tool_calling.md`
- [ ] Cập nhật `neuroedge-prd.md` nếu có FR bị ảnh hưởng; quyết định mới → `Q-N` ở §15
- [ ] Cập nhật `neuroedge-roadmap.md` với `TSK-*` thật cho W3-1..W3-6
- [ ] Thêm fixture + test: corpus `fixtures/compliance/multinode/` + `expected_results.yaml`, khép kín hai chiều (`digests.lock` chỉ khoá gate, không liên quan)
- [ ] Cập nhật dòng RFC trong `docs/rfc/README.md` và một mục `CHANGELOG.md`
      `[Chưa phát hành]`
- [ ] `NOTICE`: Zenoh (nhánh Apache-2.0) hoặc micro-ROS

## Phụ lục — Câu hỏi mở của bản nháp

1. ~~Wire protocol: Zenoh hay micro-ROS?~~ — ✅ Q-36: Zenoh-pico, spike là phép thử loại
2. ~~Trace: A hay B?~~ — ✅ Q-32: A
3. Mô hình cấu hình node trong `agent.toml` (`[nodes]`) — hình dạng cụ thể?
4. ~~Node tham chiếu: ESP32-S3 + RP2350 hay chỉ ESP32-S3 trước?~~ — ✅ Q-33: ESP32-S3 + RP2350
5. Khoá liên kết node: PSK đối xứng trước hay mTLS ngay?
6. Mất liên lạc: chính sách ✅ Q-35 (theo từng cơ cấu, mặc định dừng); còn mở: sửa `voice_fsm.md` §5 thế nào?
7. Cắt lời xuyên chip: thông điệp hủy Pi → node, ngân sách thời gian?
8. `call_source` và xác nhận `ask` qua Pi: node tin nguồn nào?
9. Mã hoá ý định trên MCU (KL-5: không parser JSON)?
10. Căn đồng hồ giữa các thiết bị cho trace hợp nhất?
