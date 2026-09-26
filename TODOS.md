# TODOS — hoãn có chủ ý, kèm mốc kích hoạt

Sổ này ghi những thứ **đã được xem xét và hoãn**, không phải những thứ bị bỏ sót. Mỗi
dòng có một mốc kích hoạt; không có mốc thì không được vào đây.

Mục xếp theo chủ đề. **Số mục cố định** — tài liệu khác dẫn `TODOS.md #N`, nên không
đánh số lại; mục xong thì xoá dòng, số không dùng lại. Khi một task xong, đọc lại mọi
mốc kích hoạt nhắc tới nó (`CONTRIBUTING.md` §8.2 bước 5).

## Chữ ký và tin cậy

| # | Hạng mục | Vì sao hoãn | Mốc kích hoạt |
|:---:|:---|:---|:---|
| 1 | **Chữ ký mật mã cho vết ghi.** `U4` cần *"nhật ký đối soát được"* (`neuroedge-prd.md` §2.1); một tệp JSON không ký chỉ đối soát được với chính mình | Cần khoá thiết bị; thuộc Fleet OS (I9) | **I9** mở, hoặc khách đầu tiên yêu cầu bằng chứng cho bên thứ ba. **Đã xác nhận đường thêm sau:** `trace.v1.json` có `metadata.additionalProperties: true`, nên thêm trường chữ ký **không cần RFC** (`CEO-S3-4`) |
| 2 | **Chữ ký mật mã cho token phán quyết.** Token = (digest, nonce) trong bộ nhớ, nên bất kỳ mã nào trong cùng tiến trình cũng tự mint được | Mối đe doạ **trong phạm vi** là bỏ qua gate do *nhầm lẫn*, và thế là chứng minh được bằng test. Biên đã ghi ở `docs/spec/threat_model.md` §3 (`TSK-S2-05`) | Khách yêu cầu chống tấn công nội tiến trình, hoặc firmware có secure element |
| 26 | **Chất lượng RNG phần cứng cho nonce và `boot_id` của sổ token C** (`ne_token.c`, TSK-S4-02). `esp_fill_random` chỉ là ngẫu nhiên thật khi RF (Wi-Fi/BT) bật hoặc bootloader đã cấp entropy; self-test chạy **trước** mạng, và trên QEMU thì không có nguồn nào | Nonce chỉ cần khác nhau giữa các token, không cần bí mật (`docs/spec/threat_model.md` §2); kẻ đoán nonce trong cùng tiến trình đã ngoài phạm vi (§3, #2) | **Bo mạch thật (TSK-S4-01)**: bật `bootloader_random_enable()` hoặc đo entropy trước khi cấp token đầu tiên; ghi kết quả vào `docs/spec/threat_model.md` §4 |

## Vết ghi và quan sát

| # | Hạng mục | Vì sao hoãn | Mốc kích hoạt |
|:---:|:---|:---|:---|
| 3 | **Streaming khi ghi vết ghi.** `ReplaySession` giữ cả dict vết ghi + các dict dẫn xuất trong RAM | 10.000 sự kiện không sao; `trace.v1.json` là một object JSON đơn nên streaming cần append-rồi-vá | Vết ghi ≥ **100.000 sự kiện** trong thực tế |
| 6 | **Metric · dashboard · alerting** | Không có dịch vụ nào để alert trong Giai đoạn 1. Vết ghi **là** nền quan sát, và `gate explain` trả lời được câu "vì sao lần đó bị chặn" | Fleet OS (**I9**) mở |
| 7 | **`trace why <trace>`** | Trùng `gate explain` sau khi `CEO-S8-2` lưu artifact gate cạnh vết ghi | Nếu `gate explain` hoá ra không trả lời được câu hỏi hậu kiểm |

## Gate và registry

| # | Hạng mục | Vì sao hoãn | Mốc kích hoạt |
|:---:|:---|:---|:---|
| 5 | **Cache phân giải gate cho đường `gate lint`.** `GateRegistry.load()` đọc tệp + parse YAML + validate mỗi lần, ×3 cấp chuỗi → O(3N) cho N gate *(nửa parse-schema lặp đã vá ở `TSK-S2-13` — `ENG-Q4`; nửa đọc-tệp vẫn còn)* | Registry hôm nay nhỏ. Đường **chạy** đã xử ở `CEO-S7-1` (phân giải một lần lúc nạp); đây chỉ là đường lint | Registry ≥ **100 gate** |
| 8 | **`--explain` in đường đi trên cây quyết định** | Rẻ đi hẳn sau `TSK-S2-12` (cây có `criteria_order` root-first + `gate_digest`), khi đó chỉ còn là in node đầu tiên fail | Rà lại ở **I3**, không phải "không bao giờ" |
| 9 | **`gate digest <file>`** | `gate publish` đã in digest; `digests.lock` (`TSK-S3-16`) phủ nhu cầu CI | Nếu có người cần digest mà không muốn publish |
| 11 | **Bất biến phiên bản phía registry (server-side).** Ghim `extends` bằng digest (#15) chỉ chặn **phía client**; nó không ngăn được việc tái publish trên một registry không kiểm soát | Chưa có registry (I10) | **I10** mở, hoặc gate công khai đầu tiên được publish |
| 30 | **`evaluate.type: numeric`** — tiêu chí số so với ngưỡng (`pressure < 8 bar`). `schemas/gate.v1.json` chỉ nhận `bool` · `level` · `choice`, nên không gate nào diễn đạt được ngưỡng số (câu hỏi mở #10 của `docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md`, `DX-H4`) | Đổi enum đã đóng băng ⇒ **cần RFC** (thêm vào `gate.v1` hay để `v2`), kèm ngữ nghĩa siết chặt cho nguyên tắc 2 và nút trong bố cục `NETR`; wedge `sim` chưa có gate nào cần | Gate đầu tiên cần ngưỡng cảm biến dạng số, hoặc đối tác đầu tiên đưa nó lên đường găng |
| 15 | **Ghim `extends` bằng digest (`TSK-S3-21`).** Tái publish base cùng version vẫn nới được mọi hậu duệ (`ENG-A1`/Failure mode 5). Cần một RFC riêng vì đổi `pattern` của `gate.v1.json`; bố cục nhị phân của cây đã tách ra và đóng băng ở RFC-0003 (`NETR` v1) | Chưa có registry; trong kho, `digests.lock` (`TSK-S3-16`) đã phủ nhu cầu CI. Firmware hôm nay link cây vào flash cùng bản build, nên host và firmware không lệch phiên bản | Cây được cập nhật qua **phân vùng flash riêng** (host và firmware lệch phiên bản được) — hoặc gate đầu tiên publish ra ngoài kho |
| 42 | **Front-end CEL cho `allow_when`** (`TSK-S2-06`, hoãn, chưa thuộc increment nào — roadmap §8.2). `allow_when` dạng chuỗi CEL, `cel-python` chỉ phân tích cú pháp trên máy tính | Dạng mapping toán tử đủ cho mọi gate hiện có. CEL phải biên dịch xuống **cùng** cây quyết định của `TSK-S2-12` (Q-9 phương án A), không có bộ lượng giá CEL trên MCU, và chuỗi CEL không được vào chuỗi kế thừa (bất biến 5 và 3, `CHANGELOG.md` §3.3) | Agent thật đầu tiên có gate không viết được bằng dạng mapping, hoặc một đối tác yêu cầu CEL |

## Firmware, mô phỏng và bo mạch

| # | Hạng mục | Vì sao hoãn | Mốc kích hoạt |
|:---:|:---|:---|:---|
| 10 | **Vector tương đương Python ↔ C trên phần cứng thật.** Walker và sổ token C đã khớp engine host trên host (ASan/UBSan, mỗi PR — TSK-S4-07) và boot trên Espressif QEMU (TSK-S4-08); chưa chạy trên silicon | Chưa có bo mạch (`TSK-S1-10`) | **Bo mạch về** (TSK-S4-01, TSK-S4-12) |
| 14 | **Bất biến `sim` không giàu hơn bo mạch tham chiếu (#7) khi có `vision.in`.** `sim-default` sao Box-3 nên không được khai camera, mà Box-3 chưa có camera, và RFC `vision.in` về sau có thể cấm khai `vision_in` trên esp32s3 tới khi đo ngân sách bộ nhớ (RFC-0002 §9.1) → agent thị giác không chạy được trên target chính thức, Action CI cho khung hình không có đường `sim` (phát hiện R6 của review RFC-0002) | Chưa có agent thị giác nào; cách sửa (mỗi profile `sim` sao đúng một bo mạch tham chiếu, ví dụ `sim-vision` ↔ `linux` có camera) cần bo mạch tham chiếu thị giác | **TSK-V1b-02** (camera ảo trong `sim`, I15) bắt đầu |
| 21 | **Wokwi CI cho `esp32s3`** (phần `board-esp32-s3-box-3`, GPIO/I2C/SPI) — Q-21 | Trình mô phỏng mã đóng, cần `WOKWI_CLI_TOKEN`, hạn mức phút CI, bản thương mại €20/chỗ/tháng; **không có I2S** nên không thay được bo mạch cho phần âm thanh. QEMU (TSK-S4-08, đã có) phủ boot và logic gate nhưng **không giả lập GPIO** (`.github/workflows/firmware-qemu.yml`) | Một task của I3 cần kiểm GPIO/I2C của `esp32s3` trước khi bo mạch về |
| 35 | **Console và baud của Box-3 cho vết ghi UART** (TSK-S4-09). PRD Phụ lục D.2 ghi 921600; `sdkconfig.defaults` không đặt (ESP-IDF mặc định UART0 115200); `nightly-hardware.yml` đọc `/dev/ttyUSB0` ở 115200; Box-3 có thể đưa console qua USB-Serial-JTAG (`/dev/ttyACM0`, baud vô nghĩa) | Không kiểm được khi chưa có bo mạch; QEMU đọc qua tệp hoặc `tcp://` nên không phụ thuộc baud | **Bo mạch về (TSK-S4-12)**: đọc console thật, chốt `CONFIG_ESP_CONSOLE_*` và baud trong `sdkconfig.defaults`, rồi sửa `nightly-hardware.yml`, `CHANGELOG.md` §2.6 và PRD D.2 cho khớp |
| 36 | **NETR v2 mang nhãn gate và chữ `on_block`** (`to`, `message`, `fallback_action`). Hôm nay firmware nhận chúng qua header sinh cạnh cây (`scripts/gen_firmware_gates.py`, `gen_firmware_vectors.py`, TSK-S4-09) | Đổi bố cục `NETR` ⇒ **cần RFC** (tăng phiên bản bố cục); khi cây link vào flash cùng bản build thì header đi cùng không lệch được | Cây được cập nhật **riêng** khỏi firmware (#15, OTA gate), hoặc bộ duyệt thứ hai đọc `NETR` |
| 37 | **Bảng hành động của vector thay cho action chạy trên MCU.** `verify --targets esp32s3` lấy operation/duration của lệnh chân từ việc chạy @action một lần trên `SimHAL` lúc sinh vector; thiết bị chỉ quyết định có phát và chân nào (TSK-S4-09) | Cách action của agent chạy trên firmware (dịch, bảng khai báo, hay mã C) chưa chốt — là phần của HAL firmware | **TSK-S4-01 bắt đầu**: chốt cách action chạy trên MCU, rồi cho vector dùng đúng đường đó và bỏ bảng |
| 38 | **`verify --targets esp32s3` tự boot QEMU** khi máy có `qemu-system-xtensa` và bản build firmware, thay vì nhận `--port` | CI đã boot QEMU (`firmware-qemu.yml`); cục bộ, `-serial tcp::5555,server` + `--port tcp://localhost:5555` là hai lệnh | Người ngoài đội đầu tiên cần chạy `verify` cho `esp32s3` cục bộ mà không có ESP-IDF, hoặc DX đo thấy hai lệnh là rào cản |
| 22 | **`espressif/esp-emulator`** (Rust, Apache-2.0, nhận hỗ trợ S3 + GPIO + Wi-Fi) — Q-21 | Quá mới (vài chục commit) để làm nền CI | Có bản phát hành ổn định có GPIO trên S3 — khi đó so với QEMU của TSK-S4-08 |

## Giấy phép

| # | Hạng mục | Vì sao hoãn | Mốc kích hoạt |
|:---:|:---|:---|:---|
| 17 | **Xác minh giấy phép ESP-SR (WakeNet/MultiNet)** cho fallback cục bộ trên `esp32s3` (Q-14). Theo hiểu biết hiện tại, giấy phép chỉ cho dùng trên SoC Espressif — ổn cho `esp32s3`, nhưng phải ghi vào `NOTICE` và không được lọt vào gói Python | Chưa vendoring `esp-sr`; `TSK-S1-10` sẽ vendoring khi bo mạch về | **Bo mạch về (`TSK-S1-10`)**, muộn nhất trước `TSK-S5-07` (điều kiện vào I5). Nếu giấy phép không hợp: chuyển sang TFLite Micro / ESP-NN (Apache-2.0) |
| 43 | **CLA cho người đóng góp** (Q-45). License thương mại chỉ cấp được cho phần mã mà NeuroEdge có quyền cấp; một PR từ người ngoài theo PolyForm Noncommercial thì không | Hôm nay mọi commit là của tác giả; cần văn bản có rà soát pháp lý, không tự soạn | **PR đầu tiên từ người ngoài** (kho đã public) — chưa merge PR đó cho tới khi có CLA ký |
| 44 | **Điều khoản license thương mại** (Q-45): phạm vi (thiết bị, đội, site), giá, cam kết hỗ trợ, quan hệ với gói Fleet OS — và **quyền dùng thử cho doanh nghiệp** (vd. PolyForm Free Trial 32 ngày): PolyForm Noncommercial không có điều khoản thử, nên kỹ sư ở công ty (U2) thử 10 phút, đo A1 hay B2 trong Beta đều chưa rõ có được phép | Chưa có khách thương mại; giá phải đo, không đoán (G-a) | **Doanh nghiệp đầu tiên hỏi dùng thương mại**, hoặc trước khi I6 ra mắt — cổng nhu cầu 2026-10-25 là nguồn dữ liệu đầu |

## Tương tác và model

| # | Hạng mục | Vì sao hoãn | Mốc kích hoạt |
|:---:|:---|:---|:---|
| 20 | **Bề mặt tương tác thật cho `escalate`/`ask`.** Đã có: ai xác nhận `ask` (Q-26) và vòng xác nhận trên `sim` — REPL, trang `--ui` (TSK-S3-26, RFC-0006). Còn hoãn: (a) người nhận `escalate` (Q-17 v1.0 là chặn + vết ghi + hook no-op); (b) `on_block.ask.message` máy kiểm được — B.3 cho phép văn bản tự do, `TSK-S2-13` chỉ kiểm `action` + `to:` *(gộp mục #12 cũ)* | Đặc tả FSM thoại đã có đường cho câu hỏi `ask` qua kênh thoại (`docs/spec/voice_fsm.md` §4, §5.4 — TSK-S2-07); còn cần hiện thực, và chưa có ngữ nghĩa kiểm được cho văn bản | **TSK-S3-11** (FSM Python) hiện thực câu hỏi `ask` qua kênh thoại, hoặc khách đầu tiên cần escalation tới người thật |
| 27 | **SystemOne cloud: gom câu hỏi của một gate, đo Jev trên tiếng Việt** (Q-4). Đã có: Jev qua System One API, bật bằng `[system_one]` (TSK-I4-02). Còn: (a) mọi tiêu chí ủy quyền của một gate đi **một** lượt gọi — Jev nhận nhiều câu hỏi một lần, engine hôm nay hỏi từng tiêu chí; (b) đo độ tin cậy của Jev trên câu tiếng Việt có nhãn, kèm lượt gọi bằng key thật (`scripts/live_jev_smoke.py`), để chọn `threshold` | (a) đổi hợp đồng `FactSource` (một tiêu chí mỗi lần) và cách `_gather` chia ngân sách; chưa gate nào ủy quyền ≥ 2 tiêu chí. (b) CI không có key; chưa có bộ câu có nhãn; TypeSafe ghi tiếng Anh là ngôn ngữ chính | (a) Gate đầu tiên ủy quyền ≥ 2 tiêu chí cho model, hoặc gate vượt ngân sách vì gọi tuần tự; (b) trước khi agent đầu tiên dùng `[system_one]` ngoài `sim` (buổi đo I8 hoặc thiết bị thật) |
| 39 | **Cờ theo từng hành động "vẫn cắt khi đã chạy" lúc bị cắt lời.** `docs/spec/voice_fsm.md` §5.3: cắt lời chỉ hủy lệnh chưa giao; lệnh đã giao (xung chốt cửa đang chạy) chạy hết | Thêm trường vào gate hoặc `@action` ⇒ **cần RFC** (`gate.v1` không nhận trường lạ; có thể đổi bố cục `NETR`), kèm ngữ nghĩa kế thừa; chưa cơ cấu chấp hành nào cần | Cơ cấu đầu tiên mà chạy tiếp sau khi người dùng phản đối là nguy hiểm (van, motor), hoặc vector V2 (§9) không đủ cho một agent thật |

## Tool call và MCP

| # | Hạng mục | Vì sao hoãn | Mốc kích hoạt |
|:---:|:---|:---|:---|
| 23 | **Đóng băng Gated Tool Profile vào `schemas/`** (lược đồ phong bì `ToolCall` và kết quả) — `docs/spec/tool_calling.md` | Corpus tuân thủ đã có (`fixtures/tool_calls/`, TSK-S3-24) nhưng chưa client bên ngoài nào dùng profile; đóng băng trước đó là mở RFC sửa ngay khi client đầu tiên đòi đổi | Một client bên ngoài dùng profile, và corpus không đổi đáp án qua một increment |
| 24 | **Transport MCP qua mạng** (HTTP của MCP) có xác thực — TSK-P2-04 | Mở cổng mạng tới hành động vật lý cần xác thực theo thiết bị và mTLS (NFR-SEC-04); v1.0 chỉ stdio (NFR-SEC-09) | Khách đầu tiên cần điều khiển thiết bị từ xa qua MCP, hoặc gateway (TSK-P2-05) cần transport mạng |
| 29 | **Test riêng cho "lặp lời gọi bị chặn tới khi lọt"** (`docs/spec/threat_model.md` §2b: *chưa có test riêng*). Lập luận hiện có: gate tất định — cùng dữ kiện ⇒ cùng phán quyết, mỗi lần đều ghi vết | Tính tất định đã được phủ gián tiếp (replay tính lại phán quyết, `tests/test_player.py`); chưa có bên gọi nào lặp tự động | Trước khi mở MCP qua mạng (#24), hoặc khi vòng ReAct của System 2 (`max_rounds`) được nới — thêm một ca vào `fixtures/tool_calls/` gọi N lần cùng dữ kiện và đòi N lần `BLOCK`, N sự kiện vết ghi |
| 25 | **Kết nối MCP bền giữa các lượt** và **transport HTTP tới MCP server bên ngoài** (Q-27) | `sim` mở kết nối theo từng lượt vì REPL chạy mỗi lượt trong một event loop riêng; HTTP cần xác thực như #24 | Runtime `linux` chạy một event loop dài, hoặc độ trễ mở kết nối vượt ngân sách lượt |

## Kinh doanh

| # | Hạng mục | Vì sao hoãn | Mốc kích hoạt |
|:---:|:---|:---|:---|
| 19 | **Câu hỏi kinh doanh mở (Q-20):** `CEO-X2` (premise $1/thiết bị/tháng chưa kiểm) · `CEO-X4` (Approach C/D/E) · `CEO-X5` (doanh thu ở cuối chuỗi 4 bên; AURA ngoài phạm vi) · `CEO-T1` (P3 có phải moat) · `CEO-T2` (chứng nhận an toàn chức năng in/out) · `CEO-T3` (bảng đối thủ thật) · `CEO-T4` (thứ tự quyết định/code). Chi tiết: `docs/archive/giai-doan-1-review-log.md` §USER CHALLENGE, §TASTE DECISION | Không chặn code; cổng nhu cầu là **mềm** theo Q-20 | **Cổng nhu cầu 2026-10-25** — trưởng nhóm rà từng mục, ghi quyết định vào PRD §15 hoặc đóng có lý do. Bộ chuẩn bị: `docs/business/cong-nhu-cau-2026-10-25/` |
| 34 | **Kênh AI-Native Agency & bán theo kết quả** — chưa cam kết; `Q-30` mới chỉ đổi thông điệp, mô hình giữ nguyên (Fleet OS) | Chưa có dữ liệu; dòng tiền thứ hai ngoài Fleet OS chưa qua PF-1..4; luận điểm Sequoia/YC/PG đã kiểm chứng nhưng chưa có agency thật nào | ≥ 3 agency hỏi mua, hoặc **cổng nhu cầu 2026-10-25**; đường dữ liệu rẻ: thêm C11 (kiểm kênh) vào bộ cổng |
| 40 | **Câu C6 (chứng nhận an toàn chức năng) cho người mua robot** (U6, Q-38). Cổng nhu cầu 2026-10-25 chỉ phỏng vấn khách sạn, fleet, smart home, industrial; Q-34 (gate mọi lệnh tốc độ của robot di động) cần câu trả lời của chính người mua robot | Hướng robot bắt đầu sau Developer Beta (Q-32); tới lúc đó tư thế tạm thời là OUT, kèm nút dừng khẩn phần cứng bắt buộc | **Trước khi mở RFC an toàn robot di động (Q-34)**: phỏng vấn ≥ 5 người mua robot theo thang `CEO-T2` (`docs/business/cong-nhu-cau-2026-10-25/cham-diem.md` §1.2), ghi IN/OUT vào Q-38 |

## Chuẩn ngoài và hệ sinh thái

| # | Hạng mục | Vì sao hoãn | Mốc kích hoạt |
|:---:|:---|:---|:---|
| 32 | **Chuyển bối cảnh §10.1 thành phân tích cạnh tranh; theo dõi MHS (Anthropic), DCP và lớp an toàn Physical AI mới nổi** — OneDiagonal ("release gate"), AI Safety Gate, STATE16 (runtime guardrails), Peridio/Avocado OS ("OS cho Physical AI"). Đã có trong bối cảnh: proposal §10.1–§10.2, Phụ lục H.3; quyết định Q-29, Q-30; khảo sát đầy đủ: `docs/archive/tai-dinh-vi-messaging-review.md` §3 | Luật C7 (`docs/business/cong-nhu-cau-2026-10-25/README.md`): chưa có cuộc phỏng vấn nào; dưới 5 cuộc nêu đối thủ thì §10 giữ nhãn *bối cảnh* | **Cổng nhu cầu 2026-10-25 (C7)**; hoặc MHS công bố open source / DCP ra spec v0.4 đổi ngữ nghĩa an toàn — đọc lại §10.1–§10.2 |
| 33 | **Adapter HAL host cho MHS** (Anthropic): kết nối thiết bị MHS qua MCP. Điểm hấp dẫn nếu mở: tag đặc tính thiết bị + giới hạn an toàn đã chuẩn hóa là nguồn dữ liệu tiềm năng cho gate | MHS chưa công bố schema/giấy phép/bộ kiểm thử tuân thủ; trượt PF-3 (chưa có nhu cầu thật); khác phân khúc (lab/nhà máy qua máy tính đầy đủ, không phải thiết bị biên). Q-29: theo dõi, không đầu tư ở v1.0 | **MHS công bố open source (schema + giấy phép + conformance)** **và** có người dùng thật hỏi hoặc đối tác port; làm theo mô hình cộng đồng — không bậc 1, không RFC-0002 |

## Nguồn

| Mục | Nguồn |
|:---|:---|
| #1–#3, #5–#9 | `/autoplan` 2026-09-22, Phase 1 (CEO) — `docs/archive/giai-doan-1-review-log.md` §GSTACK CEO / DX / ENG REVIEW REPORT |
| #10, #11 | `/autoplan` 2026-09-22, Phase 3 (Eng) — cùng biên bản |
| #14 | Review RFC-0002 (2026-09-23) — `docs/archive/rfc-0002-review-record.md` |
| #15–#17, #19–#22 | Phiên gỡ chặn Sprint 2 (2026-09-23) — quyết định Q-14 → Q-21 (`neuroedge-prd.md` §15) |
| #23–#25 | Phiên chuẩn hoá tool call (2026-09-23) — Q-24 → Q-27 |
| #26 | Sổ token C (TSK-S4-02, 2026-09-24) |
| #27 | Provider thật cho System 2 (TSK-S2-11, 2026-09-24); thu hẹp sau TSK-I4-02 (2026-09-26) |
| #29, #30 | Rà soát tài liệu MECE (2026-09-24) — `docs/spec/threat_model.md` §2b; câu hỏi mở #10 của kế hoạch Giai đoạn 1 |
| #32–#33 | Rà soát cạnh tranh MHS/DCP (2026-09-24) — `neuroedge-proposal.md` §10.1–§10.2, Phụ lục H.3; Q-29 (`neuroedge-prd.md` §15) |
| #34 | Đánh giá tái định vị thông điệp (2026-09-24) — `docs/archive/tai-dinh-vi-messaging-review.md`; Q-30 (`neuroedge-prd.md` §15) |
| #42 | Roadmap theo increment (2026-09-25) — `TSK-S2-06` rời bảng task, chưa thuộc increment nào; Q-39 (`neuroedge-prd.md` §15) |
| #43, #44 | Đổi giấy phép (2026-09-25) — Q-45 (`neuroedge-prd.md` §15), `LICENSING.md` |
