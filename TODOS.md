# TODOS — hoãn có chủ ý, kèm mốc kích hoạt

Sổ này ghi những thứ **đã được xem xét và hoãn**, không phải những thứ bị bỏ sót. Mỗi
dòng có một mốc kích hoạt; không có mốc thì không được vào đây.

Nguồn: `/autoplan` ngày 2026-09-22 — Phase 1 (CEO) · Phase 2.5 (DX) · Phase 3 (Eng, chạy
cuối nên nó thu hết) — xem `docs/designs/giai-doan-1-wedge-truoc-mcu-sau.md`
§GSTACK CEO / DX / ENG REVIEW REPORT.

## Từ CEO review

| # | Hạng mục | Vì sao hoãn | Mốc kích hoạt |
|:---:|:---|:---|:---|
| 1 | **Chữ ký mật mã cho vết ghi.** `U4` cần *"nhật ký đối soát được"* (`neuroedge-prd.md:123`); một tệp JSON không ký chỉ đối soát được với chính mình | Cần khoá thiết bị; thuộc Khối 2 | Khối 2, hoặc khách đầu tiên yêu cầu bằng chứng cho bên thứ ba. **Đã xác nhận đường thêm sau:** `trace.v1.json` có `metadata.additionalProperties: true`, nên thêm trường chữ ký **không cần RFC** (`CEO-S3-4`) |
| 2 | **Chữ ký mật mã cho token phán quyết.** Token = (digest, nonce) trong bộ nhớ, nên bất kỳ mã nào trong cùng tiến trình cũng tự mint được | Mối đe doạ **trong phạm vi** là bỏ qua gate do *nhầm lẫn*, và thế là chứng minh được bằng test. Biên này phải viết vào `docs/spec/threat_model.md` (`TSK-S2-05`) | Khách yêu cầu chống tấn công nội tiến trình, hoặc firmware có secure element |
| 3 | **Streaming khi ghi vết ghi.** `ReplaySession` giữ cả dict vết ghi + các dict dẫn xuất trong RAM | 10.000 sự kiện không sao; `trace.v1.json` là một object JSON đơn nên streaming cần append-rồi-vá | Vết ghi ≥ **100.000 sự kiện** trong thực tế |
| 4 | **Xử lý PII trong vết ghi.** Vết ghi chứa intent, tức nội dung người dùng nói | Chưa có người dùng thật | **Người dùng bên ngoài đầu tiên** (tức ngay sau `TSK-S3-14` publish thật) |
| 5 | **Cache phân giải gate cho đường `gate lint`.** `GateRegistry.load()` đọc tệp + parse YAML + validate mỗi lần, ×3 cấp chuỗi → O(3N) cho N gate *(nửa parse-schema lặp sẽ được vá ở `TSK-S2-13` — `ENG-Q4`; nửa đọc-tệp vẫn còn)* | N=3 hôm nay. Đường **chạy** đã xử ở `CEO-S7-1` (phân giải một lần lúc nạp); đây chỉ là đường lint | Registry ≥ **100 gate** |
| 6 | **Metric · dashboard · alerting** | Không có dịch vụ nào để alert trong 5 tuần. Vết ghi **là** nền quan sát, và `gate explain` trả lời được câu "vì sao lần đó bị chặn" | Fleet OS |
| 7 | **`trace why <trace>`** | Trùng `gate explain` sau khi `CEO-S8-2` lưu artifact gate cạnh vết ghi | Nếu `gate explain` hoá ra không trả lời được câu hỏi hậu kiểm |
| 8 | **`--explain` in đường đi trên cây quyết định** | Rẻ đi hẳn sau `TSK-S2-12` (cây có `criteria_order` root-first + `gate_digest`), khi đó chỉ còn là in node đầu tiên fail | Rà lại ở **Sprint 4**, không phải "không bao giờ" |
| 9 | **`gate digest <file>`** | `gate publish` đã in digest; `digests.lock` (`TSK-S3-16`) phủ nhu cầu CI | Nếu có người cần digest mà không muốn publish |

## Từ Eng review (Phase 3)

| # | Hạng mục | Vì sao hoãn | Mốc kích hoạt |
|:---:|:---|:---|:---|
| 10 | **Vector tương đương Python ↔ C trên phần cứng thật.** Trong 5 tuần chỉ phát cây + bảng sự thật host (mô hình C bằng đặc tả), chưa chạy trên silicon | Chưa có bo mạch (`TSK-S1-10`) — cùng rào cản với Approach B | **Bo mạch về**, hoặc Sprint 4–5 (Khối 1b) |
| 11 | **Bất biến phiên bản phía registry (server-side).** `TSK-S3-21` ghim `extends` bằng digest **phía client**; nó không ngăn được việc tái publish trên một registry không kiểm soát | Chưa có registry (Khối 3) | **Khối 3**, hoặc gate công khai đầu tiên được publish |
| 12 | **`on_block.ask.message` máy kiểm được.** B.3 cho phép văn bản tự do; `TSK-S2-13` chỉ kiểm `action` + `to:` | Không có ngữ nghĩa kiểm được cho văn bản; `ask` chỉ ghi vết ghi trong A1 | Khi có bề mặt tương tác `ask` (`TSK-S2-07`, Sprint 5) |

## Từ review RFC-0002 (2026-09-23)

Nguồn: review thủ công theo phương pháp `/autoplan` — xem
`docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md` §Review record.

| # | Hạng mục | Vì sao hoãn | Mốc kích hoạt |
|:---:|:---|:---|:---|
| 13 | **`neuroedge board check <file>` báo đạt/thiếu so với bậc**, chạy bộ vector tuân thủ trên một profile bậc 3 (`E4`) | Bộ vector tuân thủ chưa tồn tại; `board validate <path>` (kiểm tĩnh) đã phủ bước đầu | **Khối P1** (bộ công cụ port cộng đồng) mở, hoặc bản port bậc 3 đầu tiên được gửi tới |
| 14 | **Bất biến `sim` không giàu hơn bo mạch tham chiếu (#7) khi có `vision.in`.** `sim-default` sao Box-3 nên không được khai camera, mà Box-3 chưa có camera, và RFC `vision.in` về sau có thể cấm khai `vision_in` trên esp32s3 tới khi đo ngân sách bộ nhớ (RFC-0002 §9.1) → agent thị giác không chạy được trên target chính thức, Action CI cho khung hình không có đường `sim` (`R6`) | Chưa có agent thị giác nào; cách sửa (mỗi profile `sim` sao đúng một bo mạch tham chiếu, ví dụ `sim-vision` ↔ `linux` có camera) cần bo mạch tham chiếu thị giác | **TSK-V1b-02** (camera ảo trong `sim`) bắt đầu |

## Từ phiên gỡ chặn Sprint 2 (2026-09-23)

Nguồn: quyết định Q-14 → Q-20 (`neuroedge-prd.md` §15), `CHANGELOG.md` [0.4.0].

| # | Hạng mục | Vì sao hoãn | Mốc kích hoạt |
|:---:|:---|:---|:---|
| 15 | **RFC-0003 — ghim `extends` bằng digest (`TSK-S3-21`) + đóng băng `decision_tree.v1.json`.** Tái publish base cùng version vẫn nới được mọi hậu duệ (`ENG-A1`/Failure mode 5) | Chưa có registry, chưa có firmware C đọc cây. `TSK-S2-12` dựng cây phía host như **định dạng nội bộ, chưa đóng băng**; `digests.lock` (`TSK-S3-16`) phủ nhu cầu CI trong kho | **Sprint 4 mở (2026-11-16)** — trước dòng C đầu tiên duyệt cây — hoặc gate đầu tiên publish ra ngoài kho |
| 16 | **Q-11 phần còn lại: Hawkbit EPL-2.0, EMQX BSL** | Chỉ Khối 2 dùng; Giai đoạn 1 không phân phối chúng | **Trước khi mở Khối 2** — không viết thiết kế phụ thuộc nào của Fleet OS trước khi có phê duyệt bằng văn bản |
| 17 | **Xác minh giấy phép ESP-SR (WakeNet/MultiNet)** cho fallback cục bộ trên `esp32s3` (Q-14). Theo hiểu biết hiện tại, giấy phép chỉ cho dùng trên SoC Espressif — ổn cho `esp32s3`, nhưng phải ghi vào `NOTICE` và không được lọt vào gói Python | Chưa vendoring `esp-sr`; `TSK-S1-10` sẽ vendoring khi bo mạch về | **Bo mạch về (`TSK-S1-10`)**, muộn nhất trước Sprint 5. Nếu giấy phép không hợp: chuyển sang TFLite Micro / ESP-NN (Apache-2.0) |
| 18 | **Backend fallback cục bộ cho `linux`** (KWS / TFLite, cùng ngữ pháp lệnh với `sim`) | A2 chỉ cần HAL `linux` + Action CI; fallback trên `linux` dùng tạm backend chữ của `sim` trong test | **Khối 1b**, hoặc đối tác đầu tiên chạy `linux` không có mạng |
| 19 | **Câu hỏi kinh doanh mở (Q-20):** `CEO-X2` (premise $1/thiết bị/tháng chưa kiểm) · `CEO-X4` (Approach C/D/E) · `CEO-X5` (doanh thu ở cuối chuỗi 4 bên; AURA ngoài phạm vi) · `CEO-T1` (P3 có phải moat) · `CEO-T2` (chứng nhận an toàn chức năng in/out) · `CEO-T3` (bảng đối thủ thật) · `CEO-T4` (thứ tự quyết định/code). Chi tiết: design doc §USER CHALLENGE, §TASTE DECISION | Không chặn code; cổng nhu cầu là **mềm** theo Q-20 | **Cổng nhu cầu 2026-10-25** (cuối A1) — trưởng nhóm rà từng mục, ghi quyết định vào PRD §15 hoặc đóng có lý do |
| 20 | **Bề mặt tương tác thật cho `escalate`/`ask`** (người nhận, UI hỏi lại). Q-17 đặc tả v1.0 là chặn + vết ghi + hook no-op | Cần FSM thoại (`TSK-S2-07`) và sim web UI (`TSK-S2-09`), cả hai hoãn | **Sprint 5**, hoặc khách đầu tiên cần escalation tới người thật |
