# RFC-0014: Dữ kiện từ tiến trình ngoài

| | |
|:---|:---|
| **Mã RFC** | 0014 |
| **Tiêu đề** | Dữ kiện số từ tiến trình ngoài (Frigate, OpenCV, hộp cảm biến, tích hợp Home Assistant): nguồn khai trong gate, danh tính nguồn ghi vào vết ghi, `age_ms` theo định nghĩa chung, nguồn rớt ⇒ không có dữ kiện ⇒ BLOCK |
| **Hợp đồng bị ảnh hưởng** | `gate.v1` *(một khoá tuỳ chọn mới `evaluate.<tên>.external_source`, §3c)* · ngữ nghĩa phân giải *(luật của khoá đó ở `engine/gate_resolver.py`, §3c)* · lượng giá của engine *(`_gather` trong `engine/gate.py`, §3g)* · khối `[external]` của `agent.toml` *(không có lược đồ trong `schemas/`; kiểm ở `neuroedge build` và lúc nạp agent, như `[vision]` của RFC-0012)* · giao thức dây giữa nguồn và bộ nhận *(đặc tả mới `docs/spec/external_facts.md`; có đưa vào `schemas/` hay không: §9 câu 5)* · quy ước sự kiện vết ghi *(không đổi `trace.v1`: `type` là chuỗi mở, `events[].data` là `object` tự do — §4)* · **không** đụng `board.v1`, **không** đụng bố cục `NETR`, **không** mã lỗi mới (§4) |
| **Yêu cầu PRD liên quan** | FR-MDL-04, FR-MDL-10, FR-GATE-03, FR-GATE-06, FR-CI-02, NFR-SEC-04, NFR-SEC-09 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-10-03 |
| **Trạng thái** | 🟡 Đang thảo luận *(bản nháp: ở danh mục `docs/rfc/README.md` là ⏳ Nháp tới khi mở PR RFC riêng; chấp thuận là chữ ký của kỹ thuật trưởng và quyết định của chủ sản phẩm ở §9, không phải của người viết)* |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (chạm `gate.v1`, ngữ nghĩa phân giải, mở một đường dữ kiện vào cổng an toàn từ ngoài tiến trình) |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3 — sửa `schemas/gate.v1.json` và ngữ nghĩa phân giải gate
> (`engine/gate_resolver.py`, `engine/constraints.py`). Task: **TSK-I6-07** (RFC này; tiêu chí ra 10 của I6 là RFC được
> chấp thuận). Mã hiện thực **không** thuộc I6: `TODOS.md` #56, làm sau v1.0 cùng phản hồi của Beta. Quyết định nền:
> `neuroedge-prd.md` §15 **Q-63** (khoảng hở thứ 3), **Q-54** (kết quả nhận thức vào gate dưới dạng dữ kiện, ngưỡng khoá bằng tiêu chí
> `numeric`, không có ngữ nghĩa gate riêng), **Q-58** (MCP qua mạng có xác thực — TSK-P2-04), **Q-62** (một định nghĩa tuổi dữ kiện;
> `age_ms < 0` ⇒ BLOCK). Khớp với [RFC-0012](0012-nguyen-thuy-vision-in.md) §9.2 (nhãn mô hình → dữ kiện gõ kiểu),
> [RFC-0009](0009-tieu-chi-so-numeric.md) (tiêu chí số, `max_age_ms`), [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md)
> (đọc hỏng ⇒ chưa quyết ⇒ BLOCK).

## 1. Vấn đề

Một dự án khác — Frigate nhận diện người ở cổng, một tiến trình OpenCV đếm xe, một hộp cảm biến chạy firmware riêng, một tích hợp Home Assistant
đọc cảm biến cửa — có **quan sát** mà gate cần, nhưng NeuroEdge không muốn (và, theo Q-52/Q-54, không phải) nhúng mô hình hay thư viện thị giác
vào lõi. Hôm nay không có đường chính thức nào đưa quan sát đó vào một phán quyết:

1. **`c.facts`** (`python/neuroedge/actions/conversation.py`, `Conversation.facts`): ngữ cảnh gate do **mã agent** đặt. `ActionContractEngine._gather` (`engine/gate.py`) nhận giá trị trong đó
   cho mọi tiêu chí, không biết nó từ đâu tới, không ghi nguồn nào ngoài chuỗi `source="context"` mặc định (`Fact` ở `engine/verdict.py`). Gate không thể đòi "tiêu chí này phải đến từ Frigate".
2. **`[sim.sensor_facts]`** (`sim/session.py`, `SensorFact`): chỉ trong `sim`, đọc từ cảm biến mô phỏng, và đặt ngưỡng (`bands`, `gte`, `lte`) ở agent — đúng thứ Q-54 và RFC-0009 §1 bác.
3. **HAL** (`sensor.read`, `digital.in`, `analog.in`): đọc phần cứng của bo mạch; không phải một tiến trình khác. `sensor.read` còn không nối được với tiêu chí `numeric` (RFC-0009 §3f).
4. **`vision.in`** (RFC-0012): mô hình chạy **trong lõi**, camera là năng lực của bo mạch, vết ghi mang `vision_ref` của khung. Đó chính là thứ Q-63 nói không cần có khi nguồn quan sát nằm ở tiến trình khác.
5. **`SystemOne`** (`models/system.py`): chỉ trả lời `bool`, `level`, `choice` (hằng `TYPES`) cho một câu nói, không phải số đo, và là cuộc gọi tới mô hình do NeuroEdge khởi tạo.
6. **Lời gọi tool** (`ToolCall`, `docs/spec/tool_calling.md`): mô hình và client MCP là bên gọi **không tin cậy** (`threat_model.md` §2b); tham số lạ bị `REJECTED`. Một dữ kiện không thể đi bằng đường này, và không nên.

Hệ quả: người tích hợp phải viết mã agent nhét giá trị vào `c.facts` — mất danh tính nguồn, mất tuổi, mất ranh giới tin cậy — hoặc cầm ngưỡng ở agent. Cả hai đều là lỗ mà
gate (thuần, bất biến số 4) không thấy được.

## 2. Vì sao lược đồ hiện tại không giải quyết được

- `schemas/gate.v1.json`: `evaluate.<tên>` có `additionalProperties: false` và chỉ biết `type`, `instructions`, `levels`, `options`, `unit`, `range`, `max_age_ms`. Không có chỗ nào để gate nói
  "dữ kiện này phải đến từ nguồn ngoài tên X". Vì gate là tệp ký số (`gate_digest` = băm của `ResolvedGate.to_artifact()`, đã gồm `evaluate`), nếu nguồn chỉ khai ở agent thì thẩm quyền
  khoá nguồn nằm ngoài chữ ký — cùng lỗi mà RFC-0012 §3c thấy ở `confidence_gte` ("gate không biết tiêu chí nào đến từ thị giác, `gate lint` không chặn được").
- `agent.toml` không có chỗ khai nguồn ngoài. `[vision]` (RFC-0012) khai nhãn mô hình → dữ kiện nhưng dựa vào `vision.in` và mô hình trong lõi.
- `board.v1` khai **phần cứng**. Nguồn ngoài là một đồng cấp phần mềm, không phải chân hay bus (§6: vì sao không làm nguyên thủy).
- Không có đặc tả giao thức nào cho một tiến trình ngoài nói chuyện với runtime: truyền tải, xác thực, đồng hồ, hình thức thông điệp, hành vi khi rớt.
- Định nghĩa tuổi của Q-62 (RFC-0009 §3c: `age_ms` = thời điểm lượng giá − mốc HAL đọc, cùng một trục đơn điệu của phiên) đã có cho số đọc do **HAL trong tiến trình** gắn mốc
  (`Fact.read_ms`, `engine/gate.py::_numeric_marks`: "a source cannot state its own age"). Một tiến trình ngoài có đồng hồ riêng; chưa có luật nói mốc của nó trên trục của phiên là gì.

## 3. Thay đổi đề xuất

### 3a. Phạm vi và ranh giới

Một **nguồn ngoài** là tiến trình ngoài NeuroEdge, cùng máy với runtime, chủ động **đẩy** trạng thái quan sát hiện tại (các số) tới một ổ cắm cục bộ do runtime lắng nghe. Lõi:

- chỉ nhận **dữ kiện số đã gõ kiểu** (`numeric`): không khung hình, không nhãn, không chuỗi tự do, không mô hình, không thư viện thị giác;
- không bao giờ **liên lạc ngược** với nguồn khi lượng giá gate hay khi replay (§3g, §3h);
- coi mọi thông điệp là **không tin cậy cho tới khi** qua xác thực (§3d) và kiểm hình thức (§3e); mọi nghi ngờ ⇒ **không có dữ kiện** ⇒ `criterion_unavailable` ⇒ BLOCK (§3i);
- không đổi một chữ nào của luật gate: ngưỡng, thang, tuổi tối đa vẫn là tiêu chí `numeric` của gate (RFC-0009), chỉ thêm **ràng buộc nguồn** (§3c).

Phạm vi bản này (các giới hạn là chủ ý, mỗi giới hạn có lý do và có câu hỏi ở §9 nếu cần chủ sản phẩm quyết):

| Giới hạn | Lý do |
|:---|:---|
| Chỉ `numeric` (số đếm, độ tin cậy, đo lường; trạng thái hai giá trị là số 0/1 với `range: { min: 0, max: 1 }`) | Mọi bảo đảm cần thiết đã có sẵn cho `numeric` (RFC-0009): `max_age_ms` bắt buộc do gate khoá, `range` bắt buộc, không `confidence_gte`, không `on_block.confirms`, và **`fail: open` không tha** dữ kiện số bị mất (`known_failure` ở `engine/decision_tree.py`). `bool` không có tuổi, và `known_failure` bỏ qua dữ kiện `bool` thiếu — đúng ba lỗ mà RFC-0012 §3c phải vá bằng tiêu chí đi kèm. Thêm `bool` là RFC sau, khi chủ sản phẩm quyết (§9 câu 4) |
| Chỉ cùng máy với runtime (ổ cắm Unix) | Xác thực mạng là việc của TSK-P2-04 (§3d); không dựng cơ chế xác thực thứ hai |
| Chỉ target `sim` và `linux` | `esp32s3` không có ổ cắm cục bộ; gate khai `external_source` mà build cho `esp32s3` ⇒ từ chối (§3i). Gateway cho MCU là TSK-P2-05 (I14) |
| Không có dữ kiện `level`/`choice`/chuỗi | Cùng lập luận RFC-0012 §3c (không `level`/`choice`); chuỗi từ tiến trình ngoài là bề mặt tiêm lệnh không có lợi ích |

### 3b. Truyền tải — các phương án đã cân và phương án chọn

| Phương án | Kết luận |
|:---|:---|
| **Đẩy, ổ cắm Unix (`AF_UNIX`, stream), runtime lắng nghe** | **Chọn.** Hạt nhân cho biết uid của đầu bên kia (`SO_PEERCRED` trên Linux, `LOCAL_PEERCRED` trên macOS) nên xác thực có chỗ dựa không phải do ta tự dựng; không mở cổng mạng, không cần TLS, không phụ thuộc mới (Q-11); độ trễ vài chục micro-giây; nguồn chết thì đầu ổ cắm đóng ngay, runtime biết tức thì (§3i) |
| Đẩy, HTTP/WebSocket qua `127.0.0.1` | Bác: kéo theo cả ngăn xếp web và xác thực HTTP; tiền lệ `mcp serve --ui` phải chặn DNS rebinding và `Origin` (`threat_model.md` §2b) cho đúng bề mặt này; không có uid của đầu bên kia |
| MQTT (runtime đăng ký topic) | Bác cho bản này: cần broker, mà broker thuộc Fleet (Q-11, I9; `TODOS.md` #52); ACL do broker, không do ta kiểm; EMQX là giấy phép BSL (Q-11). Một adapter MQTT → ổ cắm Unix là việc **ngoài lõi** (§3j) |
| Kéo (runtime hỏi Frigate/HA bằng HTTP khi cần) | Bác: hoặc phải gọi mạng **ngay trong đường lượng giá** (độ trễ nằm trong ngân sách `p95_latency_ms` của gate; replay không có gì để hỏi), hoặc lõi phải biết API của từng sản phẩm — trái FR-MDL-04 (đổi nhà cung cấp không sửa gate) và trái Q-63 ("không có thư viện thị giác trong lõi") |
| Tiến trình con qua stdio (runtime sinh adapter, như MCP stdio) | Không bác: tin cậy do cấu trúc (người vận hành chạy nó), nhưng vòng đời adapter thành việc của runtime và không hợp với Frigate là dịch vụ độc lập. Lớp thông điệp §3e dùng lại nguyên được trên đường ống; thêm sau không cần RFC mới nếu không đổi §3e |
| Ổ cắm mạng có mTLS | Hoãn: cần danh tính thiết bị của TSK-P2-04. Câu hỏi §9 câu 1 |

**Đẩy trạng thái hiện tại, không đẩy sự kiện.** Nguồn gửi lại *toàn bộ giá trị hiện tại* của các dữ kiện nó chịu trách nhiệm theo nhịp đều (khuyến nghị ≤ `max_age_ms` / 2 của tiêu chí chặt nhất dùng nó).
Một nguồn chỉ gửi "có người xuất hiện" rồi im lặng sẽ bị coi là cũ — đúng ý đồ: lặng thinh không phải là "không có gì thay đổi" (cùng tinh thần RFC-0009 §5). Gộp sự kiện thành trạng thái là việc của adapter.

### 3c. Khai nguồn: gate nắm thẩm quyền, `agent.toml` nắm ràng buộc triển khai

**Gate** (`gate.v1`) khai *rằng* một tiêu chí số phải đến từ một nguồn ngoài, và *tên logic* của nguồn đó — không khai địa chỉ, ổ cắm hay khoá:

```yaml
# gates/close_gate — thẩm quyền (ví dụ nối RFC-0012 §3c bằng nguồn ngoài thay cho mô hình trong lõi)
evaluate:
  people_at_gate:
    type: numeric
    unit: count
    range: { min: 0, max: 50 }
    max_age_ms: 500
    external_source: frigate_front        # mới
    instructions: "Số người trong vùng cổng, do nguồn frigate_front báo"
allow_when:
  people_at_gate: { lte: 0 }
```

```json
"external_source": {
  "description": "Logical name of the external process that must supply this criterion (RFC-0014). Only with type numeric.",
  "type": "string",
  "pattern": "^[a-z][a-z0-9_]{0,31}$"
}
// trong allOf: nếu type khác "numeric" thì không được có external_source (cùng khuôn với unit / range / max_age_ms của bool, level, choice)
```

Luật (resolver và engine; vi phạm ⇒ `GateSchemaError`, `NE2002`, lỗi ba phần):

| Luật | Lý do |
|:---|:---|
| `external_source` chỉ trên `type: numeric` | §3a |
| Kế thừa: tiêu chí đã có `external_source` ở gate cha, gate con khai lại khác hoặc bỏ ⇒ `GateInheritanceError` (`NE2003`, nguyên tắc 1) — **không cần mã mới**: `_merge_evaluate` (`engine/gate_resolver.py`) đã từ chối "định nghĩa lại tiêu chí kế thừa" | Gate con không gỡ được ràng buộc nguồn của cha, không đổi sang nguồn dễ hơn |
| Tiêu chí có `external_source` không được nằm trong `on_block.confirms` | Đã đúng cho mọi `numeric` (RFC-0009 §3a); người trên thiết bị không xác nhận thay một quan sát, càng không thay một nguồn đã rớt |
| `confidence_gte` trên tiêu chí này bị từ chối | Đã đúng cho mọi `numeric` (RFC-0009 §3a). Khác RFC-0012 §3c: **ở đây gate lint làm được**, vì gate tự khai nguồn |

**`agent.toml`** (maker/triển khai; không có lược đồ trong `schemas/`, kiểm ở `neuroedge build` và lúc nạp agent) khai *cách* nối nguồn logic vào runtime:

```toml
[external]
socket = "run/neuroedge-external.sock"      # đường dẫn tương đối so với thư mục chạy của agent; tối đa 100 byte sau khi mở rộng

[external.sources.frigate_front]
token_env = "NE_EXT_FRIGATE_FRONT_TOKEN"    # tên biến môi trường, như api_key_env của [system_one]; không bao giờ là giá trị
[external.sources.frigate_front.facts.people_at_gate]
unit = "count"
```

| Luật (`AgentManifestError`, `NE3002`, gom vào `BuildFailed`, `NE3003`) | Lý do |
|:---|:---|
| Tên dữ kiện trùng tên tiêu chí của gate, và `unit` bằng `unit` của tiêu chí (cùng luật nối kênh của RFC-0009 §3f) | Lệch đơn vị là lệch nghĩa ngưỡng |
| **Hai chiều:** mọi tiêu chí có `external_source: X` phải có `[external.sources.X.facts.<tiêu chí>]`, và mọi dữ kiện khai ở `[external.sources.X.facts.*]` phải ứng với một tiêu chí có `external_source: X` | Không có tiêu chí nào của gate bị bỏ trống nguồn; maker không nối một tiêu chí gate khoá cho nguồn khác, hay đẩy dữ kiện vào tiêu chí gate không đòi nguồn ngoài |
| Khoá lạ trong `[external.*]` (kể cả `range`, `bands`, `threshold`, `min`, `max`) | Không có ngưỡng nào ở agent (Q-54, RFC-0012 §3c "không có ngưỡng nào trong `agent.toml`") |
| Trường mang tên bí mật (`token`, `key`, `secret`, `password`) hoặc `token_env` không phải tên biến môi trường hợp lệ | Dùng lại `secret_fields`, `refuse_unknown` và kiểm tên biến (`ENV_NAME`) của `models/providers/common.py`, như `api_key_env`; tệp `agent.toml` được commit |
| `source_id` ngoài `^[a-z][a-z0-9_]{0,31}$`; `socket` quá dài cho `sun_path`; hai nguồn cùng `token_env` | Rõ ràng; hai nguồn một khoá là hai nguồn không phân biệt được |
| Gate có `external_source` mà agent không có khối `[external]` | Build từ chối, không để tiêu chí treo |

Tiêu chí có `external_source` không bao giờ nhận giá trị từ nơi khác. `ActionContractEngine._gather` coi nguồn của nó là bộ nhận §3g **duy nhất**: giá trị trong `c.facts` cho tiêu chí đó bị bỏ qua
(không phải bị ghi đè — bỏ qua, để lỗi nhầm không đổi phán quyết), `facts_source` không được hỏi. Thiếu ⇒ `criterion_unavailable`.

### 3d. Xác thực nguồn

Mối đe doạ trong phạm vi (`threat_model.md` §2 "bỏ qua gate do nhầm lẫn" mở rộng sang một đường dữ kiện mới; §3 loại trừ kẻ cùng quyền với runtime): **một tiến trình cục bộ không phải nguồn thật** đưa số vào gate, hoặc **một nguồn thật giả danh nguồn khác**.
Bốn lớp, mọi lớp đều phải qua:

1. **Ổ cắm là của người vận hành.** Runtime tạo thư mục cha (nếu thiếu) với quyền `0700` và ổ cắm `0600`, thuộc uid của runtime; ổ cắm đã tồn tại thì chỉ xoá khi nó **đúng là ổ cắm thuộc uid này**, nếu không ⇒ từ chối nạp (`PerceptionUnavailableError`, `NE5001` — "thành phần nhận thức không dựng được", đúng nghĩa dòng Phụ lục B). Không có ổ cắm chạy được mà không có quyền.
2. **uid của đầu bên kia** đọc từ hạt nhân; phải bằng uid của runtime (hoặc một uid khai tường minh `peer_uid = <số>` cho từng nguồn). Hệ điều hành không đọc được uid ⇒ không dựng bộ nhận (không "bỏ qua kiểm tra" trên nền tảng đó).
3. **Khoá riêng cho từng nguồn.** `hello` mang `source_id` và `token`; so sánh bằng so sánh thời gian hằng (`hmac.compare_digest`) với giá trị trong biến môi trường `token_env` của nguồn đó. Khoá tối thiểu 32 ký tự, ngắn hơn ⇒ từ chối nạp. Mỗi nguồn một khoá để khoá của nguồn A không đưa được dữ kiện của nguồn B.
4. **Kết nối gắn với một `source_id` sau handshake.** Mọi dữ kiện trong kết nối đó chỉ nhận cho các tên khai ở `[external.sources.<source_id>.facts.*]`; tên khác (kể cả tên của nguồn khác) ⇒ vi phạm giao thức, đóng kết nối, bỏ mọi dữ kiện của nguồn (§3i).

Chống vét khoá và chiếm chỗ: tối đa 8 kết nối chưa xác thực, hạn handshake 2 s; 5 lần xác thực hỏng liên tiếp cho một `source_id` ⇒ khoá nguồn đó 60 s; giữa hai handshake của một nguồn tối thiểu 1 s. Hai kết nối đã xác thực cho cùng một `source_id`: **kết nối mới thay kết nối cũ** (cũ bị đóng, dữ kiện của cũ bị bỏ, sự kiện `external_source_lost` lý do `replaced`) — thà mất dữ kiện một nhịp còn hơn giữ một kết nối nửa chết. Các hằng này là đề xuất; kỹ thuật trưởng chốt khi duyệt (§9 câu 10). Runtime không ghi khoá ở bất kỳ đâu, kể cả vết ghi và thông báo lỗi.

**Nguồn qua mạng (không thuộc RFC này).** Khi cần một nguồn ở máy khác (Frigate trên NAS), danh tính phải là **danh tính thiết bị của TSK-P2-04** — mTLS theo thiết bị (NFR-SEC-04) và quyền theo thiết bị (Q-58, Q-32) — cùng một cơ chế cấp và thu hồi, không phải "khoá chia sẻ qua mạng" thứ hai. Lớp thông điệp §3e không đổi; chỉ phần handshake §3d đổi. Câu hỏi §9 câu 1.

**Mục mới cho `docs/spec/threat_model.md`** (viết khi hiện thực, §8) — "§2c. Trong phạm vi: nguồn dữ kiện ngoài":

| Đường tắt | Chặn bởi | Kết quả |
|:---|:---|:---|
| Tiến trình của người dùng khác nối vào ổ cắm | Quyền `0700`/`0600` + uid của đầu bên kia | Từ chối, `external_source_refused` |
| Tiến trình cùng uid không có khoá | `hello` thiếu/sai `token` | Từ chối; khoá nguồn sau 5 lần hỏng |
| Nguồn A khai dữ kiện của nguồn B | Kết nối gắn `source_id` (lớp 4) | Đóng kết nối, bỏ dữ kiện của A |
| LLM hoặc client MCP "đưa dữ kiện" qua tool | Dữ kiện không là tham số của tool nào; ổ cắm không phải đường MCP | `REJECTED` như tham số lạ (`tool_calling.md` §5) |
| Mã agent đặt `c.facts["people_at_gate"] = 0` để lách | `_gather` bỏ qua `c.facts` cho tiêu chí có `external_source` (§3c) | `criterion_unavailable`. *Chỉ chặn nhầm lẫn; mã cùng tiến trình vẫn ngoài phạm vi (§3 của threat model)* |
| Phát lại thông điệp cũ trong cùng kết nối | `seq` phải tăng ngặt (§3e) | Đóng kết nối, bỏ dữ kiện |
| Gửi dồn để chiếm CPU hoặc phình vết ghi | Giới hạn kích thước dòng, tốc độ, tổng hợp từ chối theo giây (§3e, §3h) | Đóng kết nối |
| Nguồn thật nhưng treo, vẫn gửi đi gửi lại giá trị cũ kèm `observed_age_ms` nhỏ | **Không chặn được ở lõi** — nguồn nói dối về độ mới | Rủi ro còn lại, §5 |

### 3e. Giao thức dây

Một dòng = một đối tượng JSON UTF-8 kết thúc bằng `\n`, tối đa 4096 byte; khoá trùng lặp trong một đối tượng bị từ chối. Mọi thông điệp có `"v": 1`.

```json
{ "v": 1, "type": "hello",   "source_id": "frigate_front", "token": "…", "adapter": { "name": "ne-frigate-adapter", "version": "0.3.1" } }
{ "v": 1, "type": "welcome" }
{ "v": 1, "type": "facts",   "seq": 812, "observed_age_ms": 40, "facts": { "people_at_gate": 0 } }
```

- `hello` đầu tiên và duy nhất trên kết nối; `adapter` chỉ để người đọc vết ghi (không tin, không dùng để quyết). `welcome` là câu trả lời duy nhất; hỏng xác thực ⇒ đóng kết nối **không lời** (không phát ra bất kỳ lý do nào ra dây).
- `facts.<tên>` là **số JSON** (không phải `true`/`false`, không chuỗi). Số hữu hạn nhưng ngoài `range` của tiêu chí, hoặc tràn thành vô cực (`1e999`), **không** phải vi phạm giao thức: nó đến engine như đã đến, và engine phán `value_out_of_range` (RFC-0009 §3c) — hậu kiểm phân biệt được "cảm biến trả rác" với "mất nguồn".
- `seq`: số nguyên, tăng ngặt trong một kết nối. `observed_age_ms`: số nguyên `0 … 4294967295` — tuổi của quan sát **tại lúc nguồn gửi**, một **khoảng thời gian** đo bằng đồng hồ của nguồn (không phải mốc), áp cho mọi dữ kiện trong thông điệp. Mỗi thông điệp áp **cả cụm** hoặc không gì cả.
- **Vi phạm giao thức** — JSON hỏng, dòng quá dài, `type` lạ, `v` ≠ 1, thiếu/sai kiểu trường, tên dữ kiện không khai cho nguồn này, `seq` không tăng, `observed_age_ms` âm/không nguyên/vượt trần, thông điệp trước `hello`, quá 100 thông điệp/giây — ⇒ **đóng kết nối và bỏ mọi dữ kiện của nguồn** (§3i). Không có chế độ "bỏ qua dòng hỏng rồi đi tiếp": một nguồn gửi rác không được coi là nguồn đáng tin cho dòng kế tiếp.
- Một thông điệp cho nhiều dữ kiện là cách duy nhất để bảo đảm chúng cùng một quan sát (ví dụ `people_at_gate` và `person_confidence` cùng khung). Lõi không ép gate đòi cùng `seq`; vết ghi mang `seq` từng dữ kiện để hậu kiểm thấy lệch (§3h).

Đặc tả đầy đủ và bộ vector tuân thủ (§7) ở `docs/spec/external_facts.md` — thuộc phần Apache-2.0 như các đặc tả khác, để adapter của OSS khác dựa vào (Q-58, Q-59).

### 3f. Tuổi dữ kiện và miền đồng hồ (Q-62)

Chỉ có **một** trục thời gian: trục đơn điệu của phiên mà `EventLog` chạy (`monotonic_ms` ở `engine/trace_sink.py`, hoặc đồng hồ giả tiêm vào ở test). Đồng hồ của nguồn **không** vào tính toán.
Lý do: gốc đồng hồ đơn điệu của một tiến trình Go, Node hay JVM là của riêng nó; trùng với `CLOCK_MONOTONIC` của hệ điều hành chỉ là ngẫu nhiên của nền tảng; còn đồng hồ treo tường thì NTP nhảy bậc được.

```
read_ms   = recv_ms − observed_age_ms        # trên trục của phiên; recv_ms do BỘ NHẬN đo
age_ms    = eval_offset_ms − offset_of(read_ms)      # đúng công thức của RFC-0009 §3c
```

- `recv_ms` là `clock()` (đồng hồ của `EventLog`) **ngay sau khi đọc xong dòng**, trong một tác vụ đọc riêng không làm việc nặng giữa lúc đọc và lúc đo.
  Độ trễ nằm trong bộ đệm hạt nhân trước lúc đọc không được tính: là sai số dưới (tuổi thật ≥ tuổi tính được), bị chặn bởi độ trễ vòng sự kiện, ghi ở §5.
- `observed_age_ms` do nguồn khai, **chỉ cộng thêm**. Vì tuổi tính được = (tuổi từ lúc nhận, do ta đo) + (khoản nguồn khai ≥ 0), nguồn nói dối chỉ làm được tuổi **bằng** tuổi-từ-lúc-nhận, không bao giờ nhỏ hơn.
  Nguyên tắc "một nguồn không thể tự khai tuổi của mình" (`_numeric_marks` ở `engine/gate.py`) giữ nguyên theo nghĩa đó: nguồn không làm mình trẻ hơn lúc nó tới.
- `offset_of` đã làm đúng việc cho mốc trước lúc log bắt đầu (offset âm, tuổi tăng — không bao giờ "trẻ như lúc bắt đầu").
- Engine tính `age_ms`, so với `max_age_ms` của tiêu chí; `age_ms < 0` hay `> max_age_ms` ⇒ `criterion_unavailable` (RFC-0009 §3c, `engine/decision_tree.py::_classify`). Không có đường nào riêng cho nguồn ngoài.
- Dữ kiện mới tới thay dữ kiện cũ **cùng tên** trong bộ nhận (`seq` đã tăng ngặt); dữ kiện cũ hơn không bao giờ đè dữ kiện mới.
- Đồng hồ treo tường của nguồn (ví dụ `start_time` của Frigate) là việc của adapter: đổi thành `observed_age_ms` bằng đồng hồ của chính nguồn. Lõi không nhận mốc tuyệt đối.

### 3g. Bộ nhận → engine: không liên lạc ngược

Bộ nhận (lớp mới thuộc runtime, tên công khai do task hiện thực quyết và ghim ở `docs/spec/python_api.md` §2 cùng `tests/test_public_api.py`) giữ **một giá trị mới nhất cho mỗi (nguồn, dữ kiện)**:
`(value, read_ms, seq, connection, observed_age_ms)`. Khi gate lượng giá, `_gather` gọi một hàm **đồng bộ, không I/O** trả `Fact(value, source="external:<id>", read_ms=…)` hoặc `None`.
Engine sau đó tính mốc như mọi số đọc số (`gate.py`, `_numeric_marks`). Nguồn rớt, kết nối đóng, vi phạm giao thức ⇒ bộ nhận **xoá** các giá trị của nguồn đó ngay (không để hết hạn tự nhiên): không còn gì trả về ⇒ `None` ⇒ `walk()` báo `criterion_unavailable`.

Hai điều không bao giờ xảy ra: bộ nhận **không** trả `Unavailable("offline")` (sẽ thành `gate_unreachable`, một lý do *suy giảm* của gate mà `budget.fail: open` có thể biến thành ALLOW — `DEGRADED_REASONS` ở `engine/verdict.py`); và nó **không** dùng lại giá trị của kết nối trước sau khi nguồn nối lại. Dữ kiện số thiếu bị `known_failure` chặn cả dưới `fail: open` (§3a), nên đường này vẫn kín khi một nguồn khác (ví dụ SystemOne) suy giảm cùng lúc.

### 3h. Vết ghi và replay

`trace.v1` **không đổi**. Dữ kiện đi vào `gate_facts` đã có (`engine/gate.py`), thêm khoá cho dữ kiện có nguồn ngoài; mọi khoá chưa biết người phát lại bỏ qua (`recorded_steps` ở `testing/player.py` chỉ đọc `value`, `confidence`, `source` và ba mốc):

```json
{ "offset_ms": 5210, "type": "gate_facts", "data": {
    "people_at_gate": { "value": 0, "confidence": null, "source": "external:frigate_front",
                        "read_offset_ms": 5130, "eval_offset_ms": 5210, "age_ms": 80,
                        "connection": 3, "seq": 812, "observed_age_ms": 40 } } }
```

- **Danh tính nguồn** ở mỗi dữ kiện: `source = "external:<source_id>"` (cùng khuôn `"<tên>:<model>"` của `SystemOneApi.source` ở `models/providers/systemone_api.py`), kèm `connection` (số thứ tự kết nối trong phiên) và `seq` để thấy hai dữ kiện cùng quan sát hay không.
  Khoá và `adapter` không vào vết ghi; `adapter` chỉ ở `external_source_connected`.
- Sự kiện vòng đời (tên và trường vào danh mục duy nhất `docs/spec/tool_calling.md` §7 khi hiện thực; thêm sự kiện không cần RFC):
  `external_source_connected` `{source_id, connection, adapter?, peer_uid}` · `external_source_lost` `{source_id, connection, reason}` với `reason` ∈ `closed` · `protocol_violation` · `replaced` · `shutdown` ·
  `external_source_refused` `{claimed_id, reason, count}` với `reason` ∈ `unknown_source` · `bad_token` · `bad_peer` · `locked_out` — **gộp theo giây** (không để kẻ gửi dồn làm phình vết ghi); `claimed_id` bị chuẩn hoá về `"?"` nếu không khớp mẫu `source_id` (không chép chuỗi lạ vào vết ghi) ·
  `external_fact_unavailable` `{criterion, source_id, why}` với `why` ∈ `not_connected` · `no_reading_yet` — phát khi tiêu chí có `external_source` không có dữ kiện lúc lượng giá, để hậu kiểm phân biệt "nguồn rớt" với "quá cũ" (cái sau do `age_ms` trong `gate_facts` và `evaluations`).
- Lint ngữ nghĩa vết ghi ở `python/neuroedge/trace.py` (vi phạm ⇒ `TraceValidationError`, `NE4001`): mục `gate_facts` có `source` bắt đầu bằng `external:` mà thiếu `connection`/`seq`/`observed_age_ms` hay ba mốc; `age_ms` không khớp `eval_offset_ms − read_offset_ms` (người phát lại đã kiểm — `_numeric_entry`); `source_id` sai mẫu.
- **Replay chỉ dùng dữ kiện đã ghi.** `ReplaySession` cấp lại đúng `gate_facts` (giá trị và ba mốc); nó **không** mở ổ cắm, không dựng bộ nhận, không đọc biến môi trường chứa khoá (có test chặn cả ba: §7). Sự kiện vòng đời là thông tin, không vào so khớp quyết định.
  Một nguồn rớt giữa phiên replay y như lúc chạy: dữ kiện vắng ở `gate_facts` ⇒ `criterion_unavailable`.
- **`sim`**: nguồn ảo trong `neuroedge.testing` đi qua **cùng bộ nhận** (cùng kiểm hình thức, cùng `seq`, cùng tính `read_ms`) bằng hàng đợi trong tiến trình, không qua ổ cắm; ổ cắm thật được kiểm riêng trong test chạy trên máy chủ. Hai đường dùng một hàm kiểm thông điệp, để vector tuân thủ §7 phủ cả hai.
- Riêng tư: vết ghi mang **số** (số người, điểm tin cậy), không khung hình, không nhãn. Việc không để lộ ảnh là của adapter; lõi không nhận gì ngoài số. Quy tắc ẩn danh (FR-TRC-07) không đổi vì không có `text`.
- Ba vết ghi chuẩn mực `fixtures/traces/*.json` không có dữ kiện ngoài nên không đổi (RFC-0008).

### 3i. Fail-closed

Kiểm theo thứ tự; mọi nhánh BLOCK, **không nội suy, không mặc định, không dùng dữ kiện của kết nối trước**:

| Tình huống | Kết quả |
|:---|:---|
| Tiêu chí có `external_source` nhưng chưa có kết nối đã xác thực của nguồn đó; hoặc kết nối có nhưng dữ kiện này chưa tới (`not_connected` / `no_reading_yet`) | Không có dữ kiện ⇒ `criterion_unavailable` |
| Kết nối đóng, lỗi đọc, hết hạn handshake, bị thay thế | Bỏ **mọi** dữ kiện của nguồn ngay ⇒ `criterion_unavailable` tới khi nối lại và có dữ kiện mới |
| Xác thực hỏng (sai khoá, sai uid, nguồn không khai) | Đóng không lời; không dữ kiện nào được nhận |
| Vi phạm giao thức §3e (gồm tên dữ kiện của nguồn khác, `seq` lùi, `observed_age_ms` sai) | Đóng kết nối, bỏ mọi dữ kiện của nguồn ⇒ `criterion_unavailable` |
| `age_ms < 0`, hoặc `age_ms > max_age_ms` của tiêu chí | `criterion_unavailable` (engine, RFC-0009 §3c) |
| Số không hữu hạn, hoặc ngoài `range` | `value_out_of_range` (RFC-0009 §9.1) |
| Hữu hạn, trong thang, không thoả khoảng của `allow_when` | `condition_not_met` |
| `c.facts` hoặc `SystemOne` cũng cấp giá trị cho tiêu chí | Bỏ qua; chỉ bộ nhận (§3c) |
| Nạp agent: có `[external]` nhưng ổ cắm không dựng được (quyền, uid, đường dẫn quá dài, ổ cắm của người khác), hoặc khoá thiếu/ngắn | Từ chối nạp, `PerceptionUnavailableError` (`NE5001`); **không** chạy tiếp "tạm không có nguồn ngoài" |
| `neuroedge build --target esp32s3` cho gate có `external_source` | Từ chối, `BoardCapabilityError` (`NE3001`): target không cung cấp năng lực này. Không gửi cây tới thiết bị để dữ kiện đến từ nơi khác |
| Gate đang chờ nguồn mà phía người gọi chỉ muốn đưa cơ cấu **về trạng thái an toàn** (`off`, `duty = 0`, `safe_state`) | Không đi qua gate (RFC-0007 §9.7, Q-62): nguồn rớt không bao giờ chặn lệnh về phía an toàn |

### 3j. Ngoài lõi (cố ý)

Không nằm trong `neuroedge` core và không vào Apache-2.0/PolyForm của lõi (Q-45, Q-59): adapter cho Frigate, OpenCV, Home Assistant, MQTT, Zigbee; mọi thư viện thị giác; mô hình; bất kỳ biến đổi nhãn → số
(`person` trong vùng `gate_area` → số đếm); đổi mốc treo tường thành `observed_age_ms`; gộp sự kiện thành trạng thái; cầu MQTT (`TODOS.md` #52). Lõi chỉ có bộ nhận, giao thức, ràng buộc gate và bộ vector tuân thủ.
Adapter mẫu có đặt trong kho hay không: §9 câu 7.

**Quan hệ với RFC-0012.** RFC-0012 §9.2 nói "maker khai nhãn nào thành dữ kiện nào; gate khoá ngưỡng". Với nguồn ngoài, **nhãn → dữ kiện xảy ra trong adapter**, không trong `agent.toml`: lõi không thấy nhãn nào, không thấy khung nào, nên các khái niệm `zone`, `min_frames`, `vision_ref`, danh tính mô hình **không tồn tại** ở đây.
Cái còn lại giống nhau: dữ kiện đã gõ kiểu (ở đây chỉ `numeric`), tên trùng tên tiêu chí của gate, ngưỡng và `max_age_ms` ở gate, không có ngưỡng ở agent, `confidence_gte` bị từ chối.
Một agent có thể dùng cả hai (RFC-0012 cho camera cắm vào bo mạch; RFC-0014 cho Frigate) cho **các tiêu chí khác nhau**; một tiêu chí chỉ có một nguồn.

### 3k. Mã lỗi

Không thêm mã. Lớp dùng đều đã có trong `python/neuroedge/errors.py`: `GateSchemaError` (`NE2002`), `GateInheritanceError` (`NE2003`), `BoardCapabilityError` (`NE3001`), `AgentManifestError` (`NE3002`), `BuildFailed` (`NE3003`),
`TraceValidationError` (`NE4001`), `PerceptionUnavailableError` (`NE5001`). Cột *Nguyên nhân* trong Phụ lục B của `neuroedge-prd.md` nới như §4. Lúc chạy, bộ nhận **không ném** lỗi tới gate: mọi thất bại là *thiếu dữ kiện* ⇒ phán quyết `criterion_unavailable` (không phụ thuộc việc RFC-0007 §3e mở phạm vi NE5001 sang lúc chạy).

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — `external_source` là khoá tuỳ chọn; không gate nào trong `gates/`, `fixtures/gates/`, `fixtures/agents/` có nó; không agent nào có `[external]` |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có, đúng một loại: tiêu chí `numeric` có `external_source` đúng mẫu. Nới lược đồ, làm được trong `v1`. *Bản `neuroedge` cũ hơn sẽ từ chối gate dùng khoá này (`additionalProperties: false`)* — fail-closed, không phải vỡ tương thích |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không. `trace.v1` không đổi (`type` mở, `data` là `object`); `board.v1` không đổi |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không — gate không có khoá mới băm như cũ. Gate **dùng** khoá mới có digest khác gate cùng nội dung không có nó (`evaluate` nằm trong `to_artifact()`): đúng ý, nguồn nằm dưới chữ ký |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào; gate mẫu dùng nguồn ngoài vào `digests.lock` bằng PR thường (`scripts/check_digests.py --update`) |
| Bố cục `NETR` hoặc walker C phải đổi? | Không. `compile_tree` (`engine/decision_tree.py`) dựng nút số từ các trường đã biết, `external_source` không vào cây thiết bị; thiết bị không nhận dữ kiện ngoài (§3a, §3i) |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không |
| Ngữ nghĩa phân giải? | Có, hẹp: resolver nhận, kiểm và giữ nguyên `external_source` qua kế thừa; engine `_gather` bỏ qua `c.facts` cho tiêu chí có khoá |

**Hợp đồng chạm đến, nói rõ:** `gate.v1` **có đổi** (một khoá tuỳ chọn). `trace.v1` **không** đổi. `board.v1` **không** đổi. `agent.toml` **có đổi** (khối `[external]` mới; ngoài `schemas/`). Đặc tả giao thức mới ngoài `schemas/` (§9 câu 5).

**Mã lỗi** (`neuroedge-prd.md` Phụ lục B): không mã mới; nới *Nguyên nhân* của năm dòng:

| Lớp | Nguyên nhân thêm |
|:---|:---|
| `GateSchemaError` (`NE2002`) | `external_source` sai mẫu, hoặc trên tiêu chí không phải `numeric` |
| `AgentManifestError` (`NE3002`) | Khối `[external]` sai (§3c): thiếu một chiều của tương ứng gate ↔ agent, `unit` lệch, khoá lạ, khoá viết thẳng, `source_id` sai mẫu |
| `BoardCapabilityError` (`NE3001`) | Gate có `external_source` build cho target không nhận nguồn ngoài (`esp32s3`) |
| `TraceValidationError` (`NE4001`) | Lint ngữ nghĩa dữ kiện có nguồn ngoài (§3h) |
| `PerceptionUnavailableError` (`NE5001`) | Bộ nhận không dựng được lúc nạp (§3i) |

## 5. Ảnh hưởng an toàn

- **Gate không lỏng hơn và không có ngữ nghĩa mới cho phán quyết** (Q-54): ngưỡng, `range`, `max_age_ms`, kế thừa chỉ thu hẹp, cấm xác nhận thay, cấm `confidence_gte`, `fail: open` không tha dữ kiện số mất — tất cả là RFC-0009 nguyên vẹn. `external_source` chỉ **thêm** một ràng buộc (nguồn), và kế thừa không gỡ được nó (§3c).
- **Thẩm quyền ở gate, triển khai ở agent:** maker không đổi được *ai* được cấp dữ kiện cho một tiêu chí, không đặt được ngưỡng; chỉ nối nguồn logic vào ổ cắm của mình, và mọi nối thiếu hoặc thừa bị build chặn (§3c, hai chiều).
- **Bên gọi không tin cậy vẫn không tin cậy:** mô hình và client MCP không có đường nào đưa dữ kiện (không có tham số, không đi qua ổ cắm), và `call_source` không đổi (`tool_calling.md` §5).
- **Một định nghĩa tuổi (Q-62):** mốc đọc là mốc *bộ nhận* đo, trên trục của phiên; phần nguồn khai chỉ cộng thêm nên không thể làm dữ kiện trẻ hơn lúc nó tới (§3f). `age_ms < 0` ⇒ BLOCK. Vết ghi mang cả ba mốc, `replay` tính lại.
- **Nguồn rớt ⇒ BLOCK, không bao giờ ALLOW** (§3i): thiếu dữ kiện là `criterion_unavailable` thường (không phải một lý do suy giảm), nên không ai biến nó thành ALLOW bằng `budget.fail: open`. Lệnh về phía an toàn vẫn không đi qua gate (§3i), nên một nguồn rớt không khoá cơ cấu ở trạng thái nguy hiểm.
- **Không có ngưỡng ở agent, không có nhãn, không có khung hình trong lõi:** bề mặt tiêm lệnh qua nội dung (nhãn lạ, chuỗi tự do) không tồn tại; chỉ số đi qua.
- **Rủi ro còn lại — nói thẳng, không loại được ở lõi:**
  1. **Nguồn nói dối về độ mới.** Một adapter treo mà vẫn gửi lại giá trị cũ kèm `observed_age_ms` nhỏ trông như dữ kiện tươi. RFC-0012 bắt được camera đứng hình ở lõi nhờ băm khung; ở đây lõi không có khung. Giảm bằng (a) adapter phải tính `observed_age_ms` từ **thời điểm chụp của chính quan sát** chứ không từ lúc poll (bắt buộc trong `docs/spec/external_facts.md`, có vector tuân thủ cho adapter mẫu nếu có); (b) `max_age_ms` ngắn ở gate buộc nguồn gửi đều; (c) gate cho hành động nguy hiểm **ghép** một tiêu chí số do lõi tin cậy (`analog.in`, `digital.in`) với tiêu chí ngoài — gate tự quyết, lõi không ép (§9 câu 8).
  2. **Nguồn sai với độ tin cậy cao** (Frigate báo "không có ai" khi có người). Giống RFC-0012 §5: giảm bằng ngưỡng ở gate và ghép tiêu chí; không xác nhận thay được (cấm `confirms`), nên hành động không hoàn tác cần tiêu chí lõi đi kèm.
  3. **Kẻ cùng uid với runtime và có khoá** đứng ngoài phạm vi (`threat_model.md` §3: quyền ngang runtime). Khoá riêng từng nguồn chỉ giới hạn *thiệt hại* của một nguồn bị xâm phạm vào các tiêu chí của nó.
  4. **Sai số dưới của `recv_ms`:** độ trễ giữa lúc dữ liệu tới hạt nhân và lúc tác vụ đọc đo `recv_ms` không được tính. Bị chặn bởi độ trễ vòng sự kiện (mili-giây); `max_age_ms` của gate cần lớn hơn đáng kể mức đó (khuyến nghị trong đặc tả).
  5. **Dữ kiện cùng quan sát nhưng khác `seq`:** hai thông điệp liền nhau có thể chứa hai nửa của một quan sát. Giảm bằng quy ước một thông điệp một quan sát (§3e); vết ghi mang `seq` để thấy.
- Cần kỹ thuật trưởng duyệt vì chạm `gate.v1`, ngữ nghĩa phân giải và mở một đường dữ kiện từ ngoài tiến trình vào cổng an toàn.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Chỉ khai nguồn ở `agent.toml`, không đổi `gate.v1` | Gate không khoá được nguồn, `gate lint` mù (cùng lỗi RFC-0012 §3c với `confidence_gte`); maker nối một tiêu chí gate coi là nhạy cảm sang nguồn dễ hơn mà không ai thấy. Dòng TSK-I6-07 ở roadmap cũng nói "nguồn khai trong gate" |
| Khai địa chỉ ổ cắm hoặc khoá trong gate | Gate là tệp ký số, phân phối qua registry và dùng trên nhiều triển khai; địa chỉ và bí mật là của triển khai. Gate chỉ mang tên logic, như FR-HAL-06 với tên chân |
| Nguồn ngoài là một **nguyên thủy** `external.in` ở `board.v1` | RFC-0013 §2 và Q-53 đòi mọi nguyên thủy mở rộng có mặt trên **cả ba** target; `esp32s3` không có ổ cắm cục bộ. FR-HAL-01 đóng tập nguyên thủy vì bảng năng lực firmware là mảng tĩnh; `board.v1` khai phần cứng, không khai đồng cấp phần mềm |
| Nguồn gửi giá trị đã **quyết** (`person_detected: true`, ngưỡng của Frigate) | Ngưỡng nằm ngoài gate (Q-54, RFC-0009 §1); `bool` không có tuổi và `known_failure` bỏ qua `bool` thiếu (§3a) |
| Cho `bool`, `level`, `choice` ở bản đầu | Ba lỗ của §3a; thêm sau bằng RFC riêng nếu chủ sản phẩm cần (§9 câu 4) |
| Tin mốc tuyệt đối của nguồn (epoch, `start_time` của Frigate) | Đồng hồ treo tường nhảy bậc khi NTP đồng bộ; gốc đơn điệu khác nhau theo ngôn ngữ; vi phạm Q-62 (một định nghĩa tuổi, trên trục đơn điệu của phiên) |
| Chỉ tính tuổi từ lúc nhận, bỏ `observed_age_ms` | Một quan sát chụp 3 s trước nằm trong đường ống của nguồn trông tươi lúc tới. Cộng `observed_age_ms` luôn bằng hoặc già hơn, không bao giờ trẻ hơn — không có lý do an toàn để bỏ |
| Nguồn tự khai tuổi đầy đủ (`age_ms` thay vì `observed_age_ms`) | Nguồn làm mình trẻ hơn được; vi phạm "a source cannot state its own age" của engine |
| Kéo (HTTP tới nguồn) trong đường lượng giá | §3b: độ trễ trong `p95_latency_ms`, replay không có gì để hỏi, lõi biết API từng sản phẩm |
| HTTP/WebSocket cục bộ thay ổ cắm Unix | §3b: kéo theo ngăn xếp web, DNS rebinding, `Origin`, không có uid của đầu bên kia |
| MQTT trực tiếp trong lõi | §3b: broker thuộc Fleet, ACL ngoài tầm kiểm, EMQX BSL (Q-11); `TODOS.md` #52 |
| "Bỏ qua dòng hỏng rồi đi tiếp" | Một nguồn gửi rác không đáng tin cho dòng kế tiếp; đóng kết nối và bỏ dữ kiện (§3e) |
| Giữ dữ kiện cũ khi nguồn rớt, chờ hết `max_age_ms` | Cửa sổ vài trăm mili-giây mà nguồn đã chết vẫn tiếp tục "tươi"; bỏ ngay (§3g) |
| Bộ nhận trả `Unavailable("offline")` khi nguồn rớt | Thành `gate_unreachable`, lý do suy giảm mà `fail: open` có thể biến thành ALLOW (`engine/verdict.py`, `engine/gate.py::_degraded`) |
| Cho `c.facts` ghi đè tiêu chí có `external_source` | Mã agent lách được ràng buộc nguồn do nhầm; bỏ qua (§3c) |
| Một khoá chung cho mọi nguồn | Nguồn bị xâm phạm đưa dữ kiện của nguồn khác (§3d lớp 3–4) |
| Dựng xác thực mạng riêng cho nguồn ở máy khác | Hai cơ chế cấp/thu hồi danh tính; dùng TSK-P2-04 (§3d) |
| `gate.v2` | Không tệp hợp lệ nào vỡ; `v2` vô ích (cùng lập luận RFC-0002 §4, RFC-0009 §6) |

## 7. Bằng chứng kiểm chứng

Mọi dòng dưới đây là **việc phải có khi hiện thực** (`TODOS.md` #56); chưa tick vì RFC này chưa có mã. Corpus theo luật khép kín hai chiều (`CONTRIBUTING.md` §3): thêm dòng cho corpus mới vào bảng ở đó (§8).

- [ ] **Gate hợp lệ và phản chứng** (`fixtures/gates/valid/`, `fixtures/gates/invalid/` + `expected_errors.yaml`): gate dùng `external_source` đúng ⇒ lint xanh; `external_source` trên `bool`/`level`/`choice`, sai mẫu tên, tiêu chí có nó trong `on_block.confirms`, kèm `confidence_gte` ⇒ `GateSchemaError` (`NE2002`); gate con bỏ hoặc đổi `external_source` của cha ⇒ `GateInheritanceError` (`NE2003`, nguyên tắc 1)
- [ ] **Hai chiều gate ↔ agent** (`python/tests/test_compiler.py`): agent thiếu `[external.sources.X.facts.<tiêu chí>]`; dữ kiện khai mà gate không đòi; `unit` lệch; khoá lạ (`range`, `bands`, `threshold`); khoá viết thẳng; `source_id` sai mẫu; hai nguồn cùng `token_env`; gate có nguồn mà không có `[external]` ⇒ `AgentManifestError` (`NE3002`); build `--target esp32s3` ⇒ `BoardCapabilityError` (`NE3001`)
- [ ] **Vector tuân thủ giao thức** (`fixtures/external_facts/{valid,invalid}/` + `expected_results.yaml`, khép kín hai chiều; luật ở `docs/spec/external_facts.md`): chuỗi thông điệp → dữ kiện bộ nhận phải giữ hoặc kết quả đóng kết nối + bỏ. Phản chứng: JSON hỏng, dòng > 4096 byte, khoá trùng, `v` lạ, `type` lạ, thiếu trường, `true` thay cho số, chuỗi thay cho số, tên dữ kiện của nguồn khác, `seq` bằng/lùi, `observed_age_ms` âm/không nguyên/> 4294967295, thông điệp trước `hello`, quá 100 thông điệp/giây
- [ ] **Xác thực trên ổ cắm thật** (host): uid khác ⇒ từ chối; thiếu/sai khoá ⇒ từ chối không lời; 5 lần hỏng ⇒ khoá 60 s; nguồn A khai dữ kiện của B ⇒ đóng + bỏ; kết nối thứ hai thay kết nối đầu; ổ cắm của người khác đã có ⇒ `NE5001`; `sun_path` quá dài ⇒ từ chối nạp; khoá ngắn hơn 32 ký tự ⇒ từ chối nạp. Khoá không xuất hiện trong vết ghi hay thông báo lỗi
- [ ] **Tuổi và đồng hồ** (đồng hồ giả, như `tests/test_numeric_tree.py`): `observed_age_ms` cộng vào tuổi; nguồn không làm tuổi nhỏ hơn tuổi-từ-lúc-nhận; `age_ms > max_age_ms` ⇒ `criterion_unavailable`; đúng bằng `max_age_ms` ⇒ qua; `read_ms` trước lúc log bắt đầu ⇒ offset âm, không "trẻ"; dữ kiện cũ không đè dữ kiện mới; đồng hồ treo tường nhảy bậc **không** đổi phán quyết (không có đường nào dùng nó)
- [ ] **Fail-closed theo bảng §3i**, mỗi dòng một ca: chưa kết nối; kết nối đóng giữa phiên ⇒ dữ kiện bị bỏ ngay và **không** hồi sinh sau khi nối lại tới khi có dữ kiện mới; vi phạm giao thức; số ngoài thang ⇒ `value_out_of_range`; `±inf` từ `1e999` ⇒ `value_out_of_range`; `c.facts` cấp giá trị cho tiêu chí có nguồn ⇒ bị bỏ qua, `criterion_unavailable`; **gate `fail: open`, SystemOne suy giảm, nguồn ngoài rớt ⇒ vẫn BLOCK** (ghim ranh giới `known_failure`/`DEGRADED_REASONS`)
- [ ] **Vết ghi** (`fixtures/traces/invalid/` + `expected_errors.yaml`): `gate_facts` có `source: external:…` thiếu `connection`/`seq`/`observed_age_ms` hay mốc; `age_ms` lệch; `source_id` sai mẫu ⇒ `TraceValidationError` (`NE4001`). `external_source_refused` gộp theo giây (gửi dồn không phình vết ghi); `claimed_id` lạ ⇒ `"?"`
- [ ] **Replay không chạm nguồn:** `ReplaySession` trên vết ghi có dữ kiện ngoài cho cùng phán quyết với không có ổ cắm, không có biến môi trường khoá, và với ổ cắm bị chặn mọi lời gọi `socket`/`bind`/`connect` (test dùng chốt chặn)
- [ ] **Tương đương target:** `verify` cho cùng phán quyết trên `sim` và `linux` từ cùng `gate_facts`; nguồn ảo của `sim` đi qua cùng bộ nhận và cùng hàm kiểm thông điệp với ổ cắm thật
- [ ] **Hợp đồng công khai:** `tests/test_public_api.py` và `docs/spec/python_api.md` §2 ghim tên bộ nhận; không thêm lệnh CLI nào ngoài khai báo (nếu có thì `tests/test_cli_contract.py` và spec §6 cùng đổi)
- [ ] `neuroedge gate lint` và `neuroedge verify` xanh; `pytest -q` 0 failed, 0 skipped

## 8. Việc phải làm khi chấp thuận

- [ ] Cập nhật `schemas/gate.v1.json` (`external_source`, `allOf` chỉ cho `type: numeric`) và `docs/user/thuat-ngu.md` (nguồn ngoài, `external_source`)
- [ ] `engine/gate_resolver.py` (kiểm mẫu, giữ qua kế thừa), `engine/constraints.py` nếu cần, `engine/gate.py::_gather` (chỉ bộ nhận cấp dữ kiện cho tiêu chí có nguồn), `engine/compiler.py` và nạp agent (khối `[external]`, hai chiều §3c, từ chối `esp32s3`)
- [ ] Bộ nhận ổ cắm Unix, lớp thông điệp §3e, nguồn ảo trong `neuroedge.testing`; `python/neuroedge/trace.py` (lint §3h); `testing/player.py` (bảo đảm replay không chạm nguồn)
- [ ] `docs/spec/external_facts.md` (đặc tả giao thức, quy ước adapter: tính `observed_age_ms` từ thời điểm chụp, nhịp gửi, thông điệp một quan sát) và bộ vector tuân thủ §7; nếu §9 câu 5 chọn đóng băng: `schemas/external_fact.v1.json`
- [ ] `docs/spec/threat_model.md`: mục "§2c. Trong phạm vi: nguồn dữ kiện ngoài" (bảng §3d); ghi rằng dữ kiện ngoài không bao giờ vào qua `ToolCall`
- [ ] `docs/spec/tool_calling.md` §7: bốn sự kiện vòng đời §3h; `docs/spec/simulation_coverage.md`: ghi nguồn ngoài **không phải nguyên thủy HAL** nên không vào ma trận §2
- [ ] `docs/spec/python_api.md` §2 và `tests/test_public_api.py`: tên công khai của bộ nhận; `CONTRIBUTING.md` §3: thêm corpus `fixtures/external_facts/` vào bảng "Thêm một fixture phản chứng"
- [ ] `neuroedge-prd.md`: Phụ lục B (nới nguyên nhân năm dòng ở §4); FR-MDL-04/FR-MDL-10 nếu đổi lời; quyết định của chủ sản phẩm ở §9 cấp `Q-N` ở §15
- [ ] `neuroedge-roadmap.md`: TSK-I6-07 xong, tiêu chí ra 10 của I6; `TODOS.md` #56 mở khoá (mốc kích hoạt "RFC được chấp thuận" đạt)
- [ ] Gate mẫu `fixtures/gates/valid/` dùng nguồn ngoài: PR thường, `scripts/check_digests.py --update`
- [ ] `docs/rfc/README.md` (dòng RFC-0014) và `CHANGELOG.md` `[Chưa phát hành]`

## 9. Câu hỏi mở cho chủ sản phẩm

Những điều dưới đây **không do người viết RFC quyết**; mỗi câu nêu mặc định của bản nháp (đã viết vào §3) và điều gì đổi nếu quyết khác. Câu 10 là của kỹ thuật trưởng khi duyệt.

1. **Nguồn ở máy khác (Frigate trên NAS) có cần ở bản đầu không?** Bản nháp: chỉ cùng máy (§3a, §3d). Nếu có: cần danh tính thiết bị của TSK-P2-04 (mTLS) làm lớp handshake; RFC bổ sung, không thêm cơ chế xác thực thứ hai. *Quyết ở đây ảnh hưởng thứ tự làm việc sau v1.0.*
2. **`esp32s3` có nhận dữ kiện ngoài không** (qua gateway của TSK-P2-05, I14)? Bản nháp: không; build từ chối (§3i). Nếu có: cần đường từ máy chủ tới thiết bị, một RFC riêng (NETR không đổi nhưng nguồn dữ kiện trên thiết bị đổi).
3. **Người có được xác nhận thay một nguồn đã rớt?** Bản nháp: không (cấm `on_block.confirms`, đã đúng cho mọi `numeric`; §3c). Nếu chủ sản phẩm muốn "người xác nhận cổng thông thoáng khi camera chết", đó là RFC sửa RFC-0009 §3a, không thuộc RFC này.
4. **Có cần nguồn ngoài cho điều kiện hai giá trị (`bool`) ngay từ đầu?** Bản nháp: không, dùng số 0/1 với `range: { min: 0, max: 1 }` (§3a) — an toàn hơn, vụng hơn: một tích hợp Home Assistant đọc `binary_sensor` phải ánh xạ sang 0/1. Nếu muốn `bool`, cần RFC thêm tuổi và chặn `known_failure` bỏ qua `bool` thiếu cho tiêu chí có nguồn, theo nguyên tắc "an toàn cao nhất" của Q-57.
5. **Giao thức dây có đóng băng vào `schemas/` (`external_fact.v1.json`) ngay khi hiện thực, hay giữ ở `docs/spec/external_facts.md` như bản thử qua Beta?** Đóng băng sớm cho adapter của OSS khác một chuẩn Apache-2.0 để dựa vào (Q-58, Q-59) nhưng thành hợp đồng khó đổi trước khi có phản hồi (hệ quả Q-58: đổi về sau cần RFC hoặc `v2`). Bản nháp: đặc tả ở `docs/spec`, chưa lược đồ.
6. **Có kiểu dữ kiện nào ngoài `numeric` ở các phiên bản sau** (`level`, `choice`, chuỗi)? Bản nháp: không. Mỗi cái là một RFC; chuỗi có bề mặt tiêm lệnh.
7. **Có đặt adapter mẫu (Frigate, Home Assistant, MQTT) trong kho này không, và dưới giấy phép nào?** Bản nháp: lõi chỉ có bộ nhận, giao thức và vector tuân thủ (§3j). Mã lõi theo PolyForm Noncommercial (Q-59); một adapter của OSS khác dùng giao thức Apache-2.0 không bị ràng buộc bởi nó. Có thể cần một thư mục `examples/` hoặc kho riêng; ai bảo trì là câu hỏi sản phẩm.
8. **Có cho một nguồn ngoài là cơ sở **duy nhất** của một ALLOW làm di chuyển phần cứng, hay gate phải ghép với tiêu chí do lõi tin cậy (HAL)?** Cơ chế RFC này cho phép cả hai: gate tự quyết. Chủ sản phẩm quyết có thêm cảnh báo của `gate lint` hoặc quy ước cho gate mẫu (gate đóng cổng, bơm, cơ cấu không hoàn tác) hay không; xem rủi ro còn lại 1 và 2 ở §5.
9. **Mặc định "đóng": bộ nhận chỉ chạy khi `[external]` có trong `agent.toml`** (không bao giờ tự bật, giống MCP qua mạng của Q-58). Bản nháp: đúng như vậy. Nêu ra để chủ sản phẩm xác nhận không có mong muốn bật theo cờ dòng lệnh.
10. **(Kỹ thuật trưởng)** Các hằng đề xuất ở §3d–§3e: khoá tối thiểu 32 ký tự, 8 kết nối chưa xác thực, handshake 2 s, 5 lần hỏng ⇒ khoá 60 s, ≥ 1 s giữa hai handshake, 100 thông điệp/giây, dòng ≤ 4096 byte, `observed_age_ms` ≤ 4294967295 (bằng độ rộng trường `max_age_ms` của `NETR`). Chốt hoặc đổi khi duyệt.
