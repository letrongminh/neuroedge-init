# 13 · Tiến hoá I0–I18: hiện trạng và kế hoạch

> **Phạm vi:** kiến trúc sẽ lớn lên thế nào qua các increment, cái gì đã được chuẩn bị sẵn, cái gì cần
> RFC. **Nguồn:** trạng thái, tiến độ, ngày dự báo chỉ ở roadmap §0.2 (Q-39) — trang này không chép lại
> chúng; hình E-09 được **sinh từ chính bảng đó**. Thiết kế của các hướng mở rộng ở
> `neuroedge-design-neurobrain.md`, `neuroedge-design-phase2.md`, `draft-ke-hoach-mo-rong-robot-fofoca.md`,
> `draft-rfc-node-giao-thuc-dieu-phoi.md`.

## 1. Bức tranh

![E-09 · Tiến hoá](../assets/svg/E-09-evolution.svg)
*Hình E-09 — Hai mươi hai increment, trạng thái, tiến độ và ngày dự báo đọc từ roadmap §0.2 lúc sinh hình.*

Đường găng (roadmap §2.2): sáu RFC của I2a → bo mạch về → spike bộ nhớ (TSK-S1-10) → I3 → I3a → I5 → I6 → I7. MVP là v1.0 đầy đủ, một lần ra mắt: trượt thì dời ngày, không cắt phạm vi (Q-52). Cổng nhu cầu
(Q-20; ngày ở roadmap §0.2) quyết Go / Adjust / Stop cho I3–I7. I12 và I15 không còn là increment: NeuroBrain thành I4a và I5a (Q-55), thị giác cơ bản nằm trong I2a và I3a (Q-53).

## 2. Kiến trúc thay đổi gì qua từng chặng

| Chặng | Container hay thành phần mới | Hợp đồng đổi | Kiến trúc hôm nay đã chuẩn bị |
|:---|:---|:---|:---|
| **I0** Lõi trên `sim` | Lõi hợp đồng an toàn: Action Contract Engine, `sim` + web UI, CLI, MCP server/host, System 2 qua LiteLLM (Q-10); walker C, sổ token và vết ghi UART trên QEMU ([`00`](00-overview.md)) → [`15`](15-target-architecture.md) §2.1 | — (baseline hợp đồng đóng băng của dự án) | 42/42 task hoàn thành; `gate.v1`, `trace.v1`, `board.v1` đóng băng; Action CI chạy đầy đủ trên GitHub Actions |
| **I1** Preview nội bộ | Trải nghiệm lập trình viên: gói wheel nội bộ, TTFV < 10 phút trên `sim` (M1), vết ghi băm chữ người dùng tại nguồn mặc định (`--raw` để giữ văn bản, TSK-I1-01) | — (RFC-0008 ghim `gate_digest` vào ba vết ghi chuẩn mực, 2026-09-27) | `sim/ui.py`, scaffold `neuroedge new`, bộ test `test_packaging.py` và job CI `wheel-smoke` |
| **I2** `linux` ngang `sim` | `LinuxHAL` hoàn chỉnh ngang hàng `sim`: `run`, `record`, `mcp serve --target linux`; cảm biến hwmon/IIO, màn hình framebuffer; runner nightly trên Raspberry Pi 5 (TSK-I2-01) | — | Job `linux-hal` kiểm tra `LinuxHAL` trên `gpio-sim`, `i2c-stub` + `lm75`, và `vkms`; `simulation_coverage.md` §2 |
| **I2a** Nguyên thủy mở rộng trên `sim` và `linux` | Bốn gói nguyên thủy tuỳ chọn theo bo mạch (Q-53): cảm biến (`digital.in`, I2C chỉ đọc, `analog.in`, gate so ngưỡng số), điều khiển mịn (PWM), thị giác (`vision.in`), chuyển động (`motion.*`); phong bì an toàn (khối N2) thành cơ chế chung; profile `sim-rpi5` → [`15`](15-target-architecture.md) §2.1, §4.2, §4.4 | **Sáu RFC:** RFC-0007 (`digital.in`, I2C chỉ đọc, `analog.in`, trường phong bì trong `board.v1`; `gate.v1` không đổi), RFC-0009 (tiêu chí `numeric` trong `gate.v1`, nút `NETR`), RFC-0010 (PWM), RFC-0011 (`motion.*`, token thuê có hạn — Q-37, an toàn cơ cấu — Q-35), RFC-0012 (`vision.in`), RFC-0013 (nguyên thủy tuỳ chọn theo bo mạch, nhiều bo tham chiếu) | `sensor.read` và `digital.out` đã có; bất biến "`sim` không giàu hơn bo tham chiếu" được phát biểu lại theo từng bo (`TODOS.md` #14); thị giác vào gate qua dữ kiện do maker khai và tiêu chí số (Q-54) |
| **I2b** Kit mẫu và dựng nhanh | Năm kit phần cứng (BOM, sơ đồ đấu dây, gate khoá), thư viện gate khởi đầu, `neuroedge add` | — | scaffold `neuroedge new` và gate mẫu |
| **I3** Gate trên Box-3 | HAL trên chip (GPIO, I2C — TSK-S4-01, TSK-S4-03); runner hằng đêm có bo mạch thật (TSK-S4-05) → [`15`](15-target-architecture.md) §2.1 | — | walker, sổ token, vết ghi UART, component sinh cho agent, self-test — đều đã chạy trên QEMU; bốn điểm nối C ([`11`](11-hal-port-guide.md) §5) |
| **I3a** Nguyên thủy mở rộng trên `esp32s3` | Bốn gói trên chip: Box-3 và một bo ESP32-S3 có camera làm bo tham chiếu thứ hai (Q-53); HAL C cho `digital.in`, I2C chỉ đọc, `analog.in`, PWM, `motion.*`, `vision.in`; cưỡng chế phong bì trong firmware → [`15`](15-target-architecture.md) §2.1 | — (theo hợp đồng của I2a) | walker C, sổ token, bốn điểm nối C ([`11`](11-hal-port-guide.md) §5); firmware chưa có phong bì thì action gắn phong bì bị từ chối trên chip |
| **I4** Thoại trên host | Phiên thoại thời gian thực với micro thật; máy trạng thái FSM, wake-word, AEC, cắt lời, STT/TTS qua provider cloud, Jev qua System One API (Q-4, Q-12) | — | máy trạng thái, nhà cung cấp, backend micro/loa `live` trên `sounddevice` (`hal/linux.py`, mới mở thiết bị); AEC qua PipeWire theo Q-22 khi nightly Pi đạt; `TODOS.md` #45 |
| **I4a** NeuroBrain trên host | Dựng Physical AI bằng hội thoại có hợp đồng (Q-31, Q-55) trên `sim` và `linux`, phủ bốn gói: action phòng lab có gate, gói `brain/` cô lập, Chat Contracting, Lab Monitor, trigger → [`15`](15-target-architecture.md) §4.2 | — (bản nháp `motion.*` phải khai phong bì và trạng thái an toàn; `gate.v1` không đổi) | mọi thứ phải đi qua `dispatch()` → gate (bất biến B-1 của thiết kế NeuroBrain); bản nháp chỉ được khoá sau `gate lint` và người duyệt |
| **I5** Thoại trên Box-3 | Đường âm thanh trên chip (I2S, AEC, VAD, Opus), client luồng âm thanh, máy trạng thái bằng C/C++ (TSK-S5-03, Q-8) → [`15`](15-target-architecture.md) §2.2, §2.3 | — | đặc tả quy phạm `voice_fsm.md` và bộ vector tuân thủ dùng chung cho Python và C (Q-8) |
| **I5a** NeuroBrain trên chip | Lab action, gate và phong bì của NeuroBrain chạy trên Box-3 và bo camera (khối N7) → [`15`](15-target-architecture.md) §4.2 | — | walker C và sổ token lượng giá lab action trên chip |
| **I6** Công khai | Gói `neuroedge` trên PyPI và lần ra mắt (kho đã công khai từ 2026-09-25, Q-45), URL lược đồ công khai (A9); video demo thoại trên 3 target bậc 1 | — | `$id` của lược đồ đã là `https://schema.neuroedge.dev/…`; workflow phát hành có SBOM CycloneDX và Sigstore attestation |
| **I7** v1.0 | Lần ra mắt MVP (Q-52): Secure Boot, mã hoá flash, công tắc micro vật lý (TSK-S6-05); đạt toàn bộ tiêu chí A1–A12 ([`neuroedge-prd.md`](../../../roadmap/neuroedge-prd.md) §11.1) → [`15`](15-target-architecture.md) §2.4 | — | OTA có ký và rollback phân vùng kép A/B đã chạy trên QEMU; `sdkconfig.ota` là lớp riêng |
| **I8** Developer Beta | Đóng băng tính năng trên dòng `1.0.x`, 50–100 lập trình viên ngoài; đo chỉ số B1–B5, rẽ 3 nhánh A/B/C ([`neuroedge-roadmap.md`](../../../roadmap/neuroedge-roadmap.md) §5) → [`15`](15-target-architecture.md) §1, §3 | — (đóng băng tính năng mới trên `1.0.x`; ngoại lệ lỗi chặn và lỗi an toàn; RFC, đặc tả, CI vẫn merge — roadmap §5.2) | — (TSK-S3-09 viễn trắc ẩn danh chưa bắt đầu, thuộc I6; tiêu chí nhánh A là B1 và B2, Q-41) |
| **I9** Fleet OS | **Container mới phía máy chủ**: điều phối OTA theo đợt (Hawkbit EPL-2.0, Q-11), broker MQTT giấy phép dễ dãi, kho vết ghi sự cố (retention 90 ngày / 3 năm, Q-6), cấp phát danh tính thiết bị (TSK-K2-04); **lớp provider tự vận hành (self-hosted provider layer)** gom một endpoint/credential, định tuyến đa provider và failover qua `agent.toml` (TSK-K2-01→03, FR-GW, Q-28) → [`15`](15-target-architecture.md) §3.1, §3.3 | có thể thêm trường vào `metadata` của vết ghi (không cần RFC) | `metadata` nhận trường thêm; `device_id` đã có; OTA cấp thiết bị là của lõi, chiến dịch là của Fleet OS (proposal §6.4); giao diện provider `neuroedge.models.providers` (Q-10) và hợp đồng failover `SystemTwo(provider=…, fallback=…)` (Q-28) mở sẵn |
| **I10** Gate Registry | **Container mới**: kho OCI (ORAS, Harbor), đo lường sử dụng (OpenMeter) → [`15`](15-target-architecture.md) §3.2 | ký gate và kiểm chữ ký trên thiết bị (TSK-W2-04); ghim `extends` theo digest cần RFC (TSK-S3-21) | định danh `neuroedge://`, digest JCS, `gate publish`, `digests.lock`, `GateRegistry` là điểm thay backend |
| **I11** Mở danh sách target | bảng bậc `TARGET_TIERS` trong lõi, `board validate` → [`15`](15-target-architecture.md) §4.1 | **RFC-0002**: enum `target` trong hai lược đồ (`board.v1`, `trace.v1`) | danh sách target đóng tại một chỗ (`hal/board.py`, `schemas/`) |
| **I13** Bộ port cộng đồng | vector tuân thủ đóng gói chạy ngoài kho, `board check`, khung kiểm thử cho OEM và cộng đồng (Q-13, FR-TGT-08) → [`15`](15-target-architecture.md) §4.1, §4.5 | — | lõi C99 không phụ thuộc ESP-IDF; hợp đồng port ([`11`](11-hal-port-guide.md) §2) |
| **I14** Robot phân tầng | Pi 5 làm não, nhiều node MCU (ESP32-S3 + RP2350 do đội lõi port, Q-33) mỗi node tự lượng giá gate; truyền thông Zenoh-pico (Q-36); tích hợp ROS 2/Nav2 có gate kiểm soát mọi lệnh tốc độ (Q-34) → [`15`](15-target-architecture.md) §4.3 | RFC-node, RFC an toàn di động (TSK-W4-07); `motion.*` và tiêu chí số đến từ I2a (RFC-0011, RFC-0009, Q-53) | vết ghi nhiều node mở rộng `trace.v1` bằng trường tuỳ chọn (Q-32); gate thuần tái dùng trên mỗi node |
| **I16–I17** Thị giác trên `jetson`, đa phương thức | `jetson` (bậc 2) và hợp nhất thoại với thị giác; tái dùng vision stack từ `neuroedge-design-phase2.md`: JetPack và TensorRT (`jetson`); `vision.in` cơ bản trên `sim`, `linux`, `esp32s3` đã vào v1.0 ở I2a, I3a (Q-53) → [`15`](15-target-architecture.md) §4.4 | RFC ngữ nghĩa bằng chứng thị giác (TSK-V3-04) | thị giác là đầu vào L2, không bao giờ là thẩm quyền L3: maker khai dữ kiện `bool`/`level`/`choice` kèm độ tin cậy số, gate khoá ngưỡng bằng tiêu chí `numeric` (Q-54) |
| **I18** Hệ sinh thái | kho adapter và port HAL trên hạ tầng Registry, chứng nhận phần cứng miễn phí, tự kiểm chứng (TSK-P2-03); bức tranh hệ sinh thái C4 hoàn chỉnh ([`16`](16-ecosystem-landscape.md)) → [`15`](15-target-architecture.md) §4.5 | — | adapter `python:` và hợp đồng port; chuẩn mở Apache-2.0 cho `schemas/`, `docs/spec/`, `fixtures/compliance/` (Q-45) |

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
| Chưa có tiêu chí số trong gate | RFC-0009 (I2a) sẽ thêm; `bands` đủ cho mẫu hiện có | #30 |
| `NETR` v1 không mang nhãn gate và chữ `on_block` | cây link cùng firmware nên không lệch | #36 |
| Thao tác và thời lượng lệnh chân trên chip lấy từ bảng dựng trên host | cách action chạy trên MCU chưa chốt | #37 |
| Đọc cảm biến `linux` chặn vòng lặp sự kiện | chưa có agent vừa nói vừa đọc cảm biến | #48 |
