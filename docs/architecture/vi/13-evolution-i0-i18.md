# 13 · Tiến hoá I0–I18: hiện trạng và kế hoạch

> **Phạm vi:** kiến trúc sẽ lớn lên thế nào qua các increment, cái gì đã được chuẩn bị sẵn, cái gì cần
> RFC. **Nguồn:** trạng thái, tiến độ, ngày dự báo chỉ ở roadmap §0.2 (Q-39) — trang này không chép lại
> chúng; hình E-09 được **sinh từ chính bảng đó**. Thiết kế của các hướng mở rộng ở
> `neuroedge-design-neurobrain.md`, `neuroedge-design-phase2.md`, `draft-ke-hoach-mo-rong-robot-fofoca.md`,
> `draft-rfc-node-giao-thuc-dieu-phoi.md`.

## 1. Bức tranh

![E-09 · Tiến hoá](../assets/svg/E-09-evolution.svg)
*Hình E-09 — Mười chín increment, trạng thái, tiến độ và ngày dự báo đọc từ roadmap §0.2 lúc sinh hình.*

Đường găng (roadmap §2.2): bo mạch về → spike bộ nhớ (TSK-S1-10) → I3 → I5 → I6 → I7. Cổng nhu cầu
(Q-20; ngày ở roadmap §0.2) quyết Go / Adjust / Stop cho I3–I7.

## 2. Kiến trúc thay đổi gì qua từng chặng

| Chặng | Container hay thành phần mới | Hợp đồng đổi | Kiến trúc hôm nay đã chuẩn bị |
|:---|:---|:---|:---|
| **I3** Gate trên Box-3 | HAL trên chip (GPIO, I2C); runner hằng đêm có bo mạch | — | walker, sổ token, vết ghi UART, component sinh cho agent, self-test — đều đã chạy trên QEMU; bốn điểm nối C ([`11`](11-hal-port-guide.md) §5) |
| **I4** Thoại trên host | Phiên thoại thời gian thực với micro thật | — | máy trạng thái, nhà cung cấp, backend micro/loa `live` (mới mở thiết bị); `TODOS.md` #45 |
| **I5** Thoại trên Box-3 | Đường âm thanh trên chip (I2S, AEC, VAD, Opus), client luồng âm thanh, máy trạng thái bằng C | — | đặc tả quy phạm `voice_fsm.md` và bộ vector tuân thủ dùng chung cho Python và C (Q-8) |
| **I6** Công khai | Lược đồ ở URL công khai; PyPI | — | `$id` của lược đồ đã là `https://schema.neuroedge.dev/…`; workflow phát hành có SBOM và attestation |
| **I7** v1.0 | Secure Boot, mã hoá flash, công tắc micro (TSK-S6-05) | — | OTA có ký và rollback đã chạy trên QEMU; `sdkconfig.ota` là lớp riêng |
| **I9** Fleet OS | **Container mới phía máy chủ**: điều phối OTA theo đợt (Hawkbit), broker MQTT giấy phép dễ dãi, kho vết ghi sự cố, danh tính thiết bị | có thể thêm trường vào `metadata` của vết ghi (không cần RFC) | `metadata` nhận trường thêm; `device_id` đã có; OTA cấp thiết bị là của lõi, chiến dịch là của Fleet OS (proposal §6.4) |
| **I10** Gate Registry | **Container mới**: kho OCI (ORAS, Harbor), đo lường (OpenMeter) | ký gate và kiểm chữ ký trên thiết bị (TSK-W2-04); ghim `extends` theo digest cần RFC (TSK-S3-21) | định danh `neuroedge://`, digest JCS, `gate publish`, `digests.lock`, `GateRegistry` là điểm thay backend |
| **I11** Mở danh sách target | bảng bậc `TARGET_TIERS` trong lõi, `board validate` | **RFC-0002**: enum `target` trong hai lược đồ | danh sách target đóng tại một chỗ (`hal/board.py`, `schemas/`) |
| **I12** NeuroBrain | action phòng lab có gate, phong bì an toàn vật lý trong HAL, I2C chỉ đọc | **RFC-0007**: `digital.in`, I2C chỉ đọc, trường phong bì trong `board.v1` | mọi thứ phải đi qua `dispatch()` → gate (bất biến B-1 của thiết kế NeuroBrain) |
| **I13** Bộ port cộng đồng | vector tuân thủ đóng gói chạy ngoài kho, `board check` | — | lõi C99 không phụ thuộc ESP-IDF; hợp đồng port ([`11`](11-hal-port-guide.md) §2) |
| **I14** Robot phân tầng | Pi làm não, nhiều node MCU mỗi node tự lượng giá gate; dây Zenoh-pico | RFC-node, RFC-motion (`motion.*`, token thuê có hạn — Q-37), tiêu chí số (`TODOS.md` #30) | vết ghi nhiều node mở rộng `trace.v1` bằng trường tuỳ chọn (Q-32); gate thuần tái dùng trên mỗi node |
| **I15–I17** Thị giác | HAL thị giác trên `linux`, rồi `jetson` | RFC `vision.in`; RFC ngữ nghĩa bằng chứng thị giác | thị giác là đầu vào L2, không bao giờ là thẩm quyền L3: phải được một `SystemOne` rút gọn về `bool`/`level`/`choice` |
| **I18** Hệ sinh thái | kho adapter và port HAL trên hạ tầng Registry | — | adapter `python:` và hợp đồng port |

## 3. Điểm biến thiên đã có sẵn

Những chỗ kiến trúc hôm nay đã cố ý để mở, để các chặng trên không phải đập lại nền:

| Điểm | Ở đâu | Cho phép |
|:---|:---|:---|
| Nguồn dữ kiện | giao thức `FactSource` (`engine/gate.py`) | thêm model quyết định, cảm biến, thị giác làm nguồn dữ kiện mà không đổi engine |
| Nhà cung cấp model và giọng nói | `models/providers/`, `perception/providers/`, adapter `python:` | đổi nhà cung cấp bằng cấu hình |
| HAL | lớp con `HardwareAbstractionLayer` + profile `boards/` | target mới (sau RFC-0002) |
| Backend registry | `GateRegistry` (`gate_resolver.py`) — docstring ghi rõ sẽ thay bằng tra cứu OCI | Gate Registry (I10) |
| Sự kiện vết ghi | `type` là chuỗi tự do trong `trace.v1`; `metadata` nhận trường thêm | sự kiện mới, vết ghi nhiều node, mà không cần `trace.v2` |
| Lớp cấu hình firmware | `SDKCONFIG_DEFAULTS` nhiều lớp | bật tính năng theo bo mạch mà không rẽ nhánh mã |
| Cây trên thiết bị | `NETR` có `layout_version` | bố cục v2 khi cần (ví dụ mang nhãn gate — `TODOS.md` #36), walker v1 từ chối v2 thay vì đọc sai |

## 4. Nợ kiến trúc đã biết

Mỗi mục là một lựa chọn có chủ đích, có mốc kích hoạt trong `TODOS.md`:

| Nợ | Vì sao chấp nhận hôm nay | `TODOS.md` |
|:---|:---|:---|
| Vết ghi chưa ký | cần khoá thiết bị; thuộc Fleet OS | #1 |
| Token là `(nonce, digest)` trong bộ nhớ, không ký | mối đe doạ trong phạm vi là bỏ qua do nhầm lẫn | #2 |
| `extends` chưa ghim theo digest | chưa có registry; `digests.lock` phủ CI | #15 |
| Gated Tool Profile chưa đóng băng vào `schemas/` | chưa client ngoài nào dùng | #23 |
| Kết nối MCP chỉ sống một lượt | mỗi lượt REPL một vòng lặp sự kiện | #25 |
| Chưa có tiêu chí số trong gate | cần RFC; `bands` đủ cho mẫu hiện có | #30 |
| `NETR` v1 không mang nhãn gate và chữ `on_block` | cây link cùng firmware nên không lệch | #36 |
| Thao tác và thời lượng lệnh chân trên chip lấy từ bảng dựng trên host | cách action chạy trên MCU chưa chốt | #37 |
| Đọc cảm biến `linux` chặn vòng lặp sự kiện | chưa có agent vừa nói vừa đọc cảm biến | #48 |
