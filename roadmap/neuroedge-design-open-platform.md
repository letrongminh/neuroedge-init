# NeuroEdge — Ghi chú thiết kế nền tảng mở

## Lớp an toàn mà bên thứ ba tự nối vào

> **Ghi chú thiết kế.** Tệp này giữ định vị, nguyên tắc, kiến trúc và ranh giới an toàn của nền tảng mở. Nó
> **không** có lịch, trạng thái hay tiêu chí ra: những thứ đó chỉ nằm ở
> [`neuroedge-roadmap.md`](neuroedge-roadmap.md) — increment **I2c** (§4.3.3, task TSK-I2c-NN và TSK-V1a-NN).
> Quyết định chỉ nằm ở `neuroedge-prd.md` §15: **Q-67** (nền tảng mở, tám quyết định), Q-45 và Q-59 (giấy phép),
> Q-58 (bề mặt tích hợp), Q-62 (lệnh về phía an toàn), Q-65 (dữ kiện ngoài). Hợp đồng chỉ nằm ở RFC:
> [RFC-0002](../docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md) (target và bậc),
> [RFC-0014](../docs/rfc/0014-du-kien-tu-tien-trinh-ngoai.md) (dữ kiện ngoài),
> [RFC-0016](../docs/rfc/0016-loi-tach-duoc-va-extension-sdk.md) (lõi dùng độc lập và Extension SDK),
> [RFC-0017](../docs/rfc/0017-nguon-goi-theo-khong-gian-ten.md) (nguồn gọi theo không gian tên),
> [RFC-0018](../docs/rfc/0018-co-cau-chap-hanh-tu-xa.md) (cơ cấu chấp hành từ xa).

**Cập nhật:** 2026-10-04 · lịch sử thay đổi: `CHANGELOG.md`

**Tài liệu nguồn:** báo cáo thị trường [`docs/reports/thi-truong-tich-hop-2026-10-04.md`](../docs/reports/thi-truong-tich-hop-2026-10-04.md)
· `docs/spec/threat_model.md` · `docs/spec/python_api.md` · `neuroedge-proposal.md` §1.5, §3.8, §6.4

**Ngoài phạm vi:** Marketplace có thu phí (Khối 5, PRD §14) — index cộng đồng ở §7 không phải Marketplace.

---

## 1. Định vị

Thị trường thiết bị cho AI agent đổi theo tuần: Meta Muse Gadgets, Home Assistant qua MCP, Alexa+ MCP Toolkit,
xiaozhi, ESP-Claw, Anthropic MHS. Mỗi hệ mang sẵn agent, giọng nói và cloud riêng. Thứ họ **không** có là phần lõi
của NeuroEdge: giới hạn theo giá trị ngay trên thiết bị, chặn khi lỗi theo mặc định, vết ghi phát lại được
(báo cáo thị trường §3).

Vì vậy NeuroEdge không thắng bằng cách tự hỗ trợ từng hệ. Nó thắng khi **ai cũng tự nối được**: maker hay hãng
phần cứng cài một plugin, chạy vài lệnh, và mọi lệnh vật lý của agent của họ đi qua gate của NeuroEdge — không sửa
lõi, không chờ đội lõi, không phải theo trọn mô hình `agent.toml` + `@action` của NeuroEdge.

**Nguyên tắc:** mở về tích hợp, không mở về an toàn. Mọi đường tới cơ cấu chấp hành vẫn qua gate → phong bì →
token → HAL (`threat_model.md` §1); fail-closed mọi hướng (`CHANGELOG.md` §3.3 #2); lệnh về phía an toàn không
bao giờ bị chặn (Q-62).

## 2. Hôm nay đóng ở đâu

NeuroEdge đã mở ở **hợp đồng** (lược đồ, đặc tả, vết ghi — Apache-2.0) nhưng đóng ở **điểm cắm**: không có entry
point nào; backend HAL chọn bằng `if target == "linux"`; `--board` chỉ nhận id trong `boards/`; template và lệnh
`add` là tuple cố định; `source` của tool call là tập đóng năm giá trị; dữ kiện ngoài chưa có mã; thân `@action`
gọi SDK bên ngoài thì không có phong bì hay tự tắt. Chỉ provider mô hình là mở thật (`python:pkg.mod:factory`,
FR-MDL-08). Chi tiết có trích dẫn: §1–§2 của RFC-0016 và RFC-0017.

## 3. Kiến trúc ba tầng

| Tầng | Gồm | Cam kết |
|:---|:---|:---|
| **Lõi an toàn** | `gate.v1`, phân giải, engine, phong bì, sổ token, `trace.v1`, replay, `verify` | NeuroEdge giữ đúng và ổn định. Dùng **độc lập** qua `neuroedge.guard` — không bắt buộc `agent.toml`, `@action` hay `SimSession` (RFC-0016). Python trên Linux, C99 (`ne_gate`) trên MCU |
| **Extension SDK** (`neuroedge.sdk`) | Sáu loại điểm cắm qua Python entry points (§4); bộ test tuân thủ cho từng loại | Phiên bản và cam kết ổn định riêng, chặt hơn `0.x` của gói (Q-67 quyết định 7) |
| **Phân phối** | `neuroedge plugin search/install`, index cộng đồng, kit và gate từ git hay OCI ghim digest, huy hiệu "NeuroEdge-gated" | Miễn phí, không bảo chứng; kết quả tuân thủ do bên đóng góp tự chạy và công bố |

## 4. Sáu điểm cắm và bất biến cấu trúc

| Loại (nhóm entry point) | Plugin làm được | Plugin **không bao giờ** làm được | Hợp đồng |
|:---|:---|:---|:---|
| **Bridge** (`neuroedge.bridges`) | Dịch giao thức ngoài (Muse, HTTP, MQTT…) thành yêu cầu tool, gửi qua bộ điều phối do lõi cấp, trả kết quả về | Chạm HAL hay chân: API của bridge không có handle phần cứng; tự gán `source` — yêu cầu không có trường đó, lõi gán `bridge:<id>` theo tên entry point | RFC-0016, RFC-0017 |
| **Fact source** (`neuroedge.fact_sources`) | Cấp dữ kiện số cho tiêu chí đã khai nguồn | Tự khai tuổi dữ kiện; cấp cho tiêu chí không khai nguồn; làm dữ kiện mất thành ALLOW | RFC-0014, RFC-0016 |
| **Actuator** (`neuroedge.actuators`) | Lái một cơ cấu — cục bộ hay từ xa (Home Assistant, Matter…) | Chạy lệnh không qua token và phong bì; thiếu mức tự tắt khai rõ | RFC-0016, RFC-0018 |
| **Board** (`neuroedge.boards`) | Cung cấp hồ sơ `board.v1` cho bo của cộng đồng | Tự nhận bậc; được `verify` tính là bo tham chiếu | RFC-0002, RFC-0016 |
| **Template** (`neuroedge.templates`) | Cung cấp kit, mẫu dự án | Chạy mã lúc cài; ghi đè gate đã khoá | RFC-0016 |
| **Exporter** (`neuroedge.exporters`) | Đọc sự kiện, xuất ra OTel, webhook… | Ghi ngược vào phiên hay đổi phán quyết | RFC-0016 |

Plugin chỉ nạp khi người vận hành bật rõ; nạp hỏng hoặc lệch phiên bản SDK thì **không khởi động** chứ không bỏ
qua lặng lẽ; nguồn gốc (gói, phiên bản, băm tệp) in ra và ghi vào vết ghi (RFC-0016).

## 5. Bốn adapter phổ quát

Bốn hình dạng tích hợp phủ phần lớn thị trường (báo cáo thị trường §2). NeuroEdge tự làm adapter cho mỗi hình dạng;
hệ sinh thái mới chỉ cần một plugin mỏng trên hình dạng của nó.

| Hình dạng | Adapter của lõi | Điều kiện để có giá trị |
|:---|:---|:---|
| Agent gọi tool qua MCP | `neuroedge proxy mcp` + `neuroedge guard init --mcp` sinh gate chặn mặc định cho từng tool của server sẵn có | Proxy là **đường duy nhất** tới server thật; `plugin doctor` kiểm |
| Thiết bị gọi ra cloud của hãng | Bridge chạy trên thiết bị, thay bộ thực thi lệnh của SDK hãng | Gỡ lệnh thô của SDK hãng (vd `system.run` của Muse) |
| Hub / HTTP cục bộ, pub/sub | `neuroedge proxy http`; cơ cấu từ xa kiểu Home Assistant | Như trên; cơ cấu từ xa khai mức tự tắt |
| Middleware robot | Node gate cho ROS 2 | Thuộc robot phân tầng (I14, Q-34) |

Bài kiểm của cả thiết kế: một bridge cho **Muse Gadgets** viết ở kho riêng, chỉ từ tài liệu công khai, lõi không đổi
dòng nào (TSK-I2c-17; tiêu chí A13).

## 6. Vài lệnh

| Tình huống | Lệnh |
|:---|:---|
| Che một MCP server sẵn có | `pipx install neuroedge` → `neuroedge guard init --mcp <url hoặc lệnh>` → `neuroedge proxy mcp` |
| Hệ sinh thái mới (vd Muse) | `pip install neuroedge-muse` → `neuroedge guard init --kit <kit>` → `neuroedge bridge muse` |
| Bo hay driver lạ | `neuroedge board validate ./bo.toml` → `neuroedge run --board ./bo.toml` |
| Dùng lại kit hay gate của người khác | `neuroedge new <tên> --template git+https://…@<commit>` |

Tên lệnh ở đây là thiết kế; tên chốt nằm ở RFC-0016 và hợp đồng CLI (`docs/spec/python_api.md` §6) khi hiện thực.

## 7. Tin cậy, an toàn và các ranh giới

- **Plugin chạy trong tiến trình là mã người vận hành tin.** Kẻ giả mạo trong cùng tiến trình vẫn ngoài phạm vi
  (`threat_model.md` §3). Cài plugin là quyết định của người vận hành; ký số plugin đi cùng registry (I10).
- **Proxy chỉ có giá trị khi là đường duy nhất.** Tài liệu và `plugin doctor` nói rõ, kiểm được thì kiểm.
- **Cơ cấu từ xa** phân theo mức tự tắt; hành động không hoàn tác cần thiết bị tự tắt được dù mất liên lạc
  (RFC-0018). Mất liên lạc ⇒ trạng thái không chắc ⇒ từ chối lệnh bật tới khi xác nhận lại.
- **Bo của cộng đồng** dùng được qua đường dẫn hay plugin, tự chứng nhận bằng `board validate` và bộ test tuân thủ;
  không bao giờ là bo tham chiếu, không bao giờ được tính vào tương đương bậc 1 (RFC-0002, RFC-0013).
- **Index cộng đồng không phải Marketplace:** không thu phí, không xếp hạng trả tiền, không bảo chứng (PRD §14).

## 8. Giấy phép

Chuẩn và bộ test tuân thủ — `schemas/`, `docs/spec/`, `fixtures/compliance/` cùng corpus `fixtures/tool_calls/`,
`fixtures/contracts/`, `fixtures/traces/`, `fixtures/agents/` — theo Apache-2.0, để bất kỳ ai hiện thực chuẩn và tự
chứng minh. Mã runtime giữ PolyForm Noncommercial qua v1.0 (Q-45, Q-59). Plugin của bên thứ ba nằm ở kho của tác
giả, theo giấy phép của tác giả (`LICENSING.md`). Hệ quả đã chấp nhận: hãng thương mại tích hợp qua chuẩn
Apache-2.0; nhúng runtime vào sản phẩm thương mại cần license thương mại.

## 9. Ngoài lõi, theo sau

- **MCU:** `ne_gate` thành component ESP-IDF dùng được trong firmware của hãng khác, kèm lệnh sinh `NETR` không cần
  build cả agent — đi cùng chặng B (I3a, I5).
- **Chuẩn ngoài:** adapter MHS khi spec công bố (`TODOS.md` #33); Matter, MQTT (#52), OpenTelemetry (#53) — ai cũng
  viết được dưới dạng plugin; đội lõi chỉ làm khi có nhu cầu đo được.

## 10. Đo thành công

M6 và A13 (`neuroedge-prd.md` §1.3, §11.1): một bên thứ ba nối một hệ sinh thái chưa từng có, ở kho riêng, chỉ từ
tài liệu công khai, qua bộ test tuân thủ trong ≤ 1 ngày, lõi không đổi dòng nào; che một MCP server sẵn có trong
≤ 3 lệnh. Về sau: G2, G3 và V-G5 của proposal §8.7, §12.4 đo hiệu ứng mạng.

## 11. Rủi ro

| Rủi ro | Giảm bằng |
|:---|:---|
| Bề mặt an toàn rộng hơn (proxy bị vòng qua, plugin độc) | Bất biến cấu trúc §4; `plugin doctor`; bật plugin tường minh; nguồn gốc trong vết ghi |
| API plugin đổi làm vỡ hệ sinh thái | `neuroedge.sdk` có phiên bản và cam kết riêng |
| MHS thành chuẩn giới hạn của ngành | Nhập manifest MHS làm nguồn giới hạn và dữ kiện; NeuroEdge đứng ở tầng gate và vết ghi |
| Giao thức của hãng đổi nhanh | Adapter mỏng, bám ngữ nghĩa `tools/call`; plugin của cộng đồng gánh phần đuôi dài |
| Lịch MVP dài thêm | Q-52: lùi ngày, không cắt phạm vi |
