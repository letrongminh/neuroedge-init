# Cổng nhu cầu 2026-10-25 (Q-20)

Bộ tài liệu chuẩn bị cho cổng nhu cầu thương mại của NeuroEdge. Soạn ngày 2026-09-24.

| Tệp | Dùng khi nào |
|:---|:---|
| `README.md` (tệp này) | Mục đích, câu hỏi phải trả lời, kế hoạch theo ngày, cách ghi kết quả |
| [`phong-van.md`](phong-van.md) | Bộ câu hỏi phỏng vấn theo phân khúc, kiểu The Mom Test |
| [`demo.md`](demo.md) | Kịch bản demo ≤ 5 phút mỗi phân khúc, chỉ dùng lệnh chạy được hôm nay |
| [`cham-diem.md`](cham-diem.md) | Thang chấm từng cuộc, quy tắc cộng dồn, ngưỡng go / adjust / stop, mẫu quyết định |
| [`survey.json`](survey.json) | Câu hỏi khảo sát trực tuyến (sàng lọc + ước lượng quy mô) |
| [Trang *Phiếu cổng 25/10*](https://claude.ai/artifact/84U95aW7kxdNT2biKdGvqN) | Trang ghi phiếu dựng từ `survey.json`: tiến độ 4 phân khúc so với mục tiêu 5 cuộc, tổng hợp theo giả thuyết, danh sách người đồng ý liên hệ. **Chỉ mở được trong tổ chức** (kho phiếu dùng chung không chia sẻ công khai được): người phỏng vấn ghi thay khách, hoặc mời khách vào tổ chức với quyền *Can interact*. Người chỉ có quyền xem không lưu được phiếu |

## 1. Mục đích

Q-20 (`neuroedge-prd.md` §15) chốt: cổng **mềm**, ngày **2026-10-25** (cuối A1), **không chặn
A2**. Các thách thức kinh doanh `CEO-X2`, `CEO-X4`, `CEO-X5` và `CEO-T1`..`CEO-T4` là câu hỏi
mở, trưởng nhóm chủ trì, rà lại tại cổng (`TODOS.md` #19).

Cổng không quyết code A2. Nó quyết ba việc:

1. Mỗi mục của `TODOS.md` #19 được **đóng có lý do** hoặc **thành quyết định** trong PRD §15.
2. Khối 1b (Sprint 4 mở 2026-11-16, Q-19) có đi tiếp theo kế hoạch không, hay đổi hướng
   (Approach C / E) có bằng chứng.
3. Phân khúc nào là phân khúc đầu tiên để làm tiếp (tối đa hai).

Rủi ro số một là nhu cầu chưa kiểm chứng (premise P4, `docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md`).
Tới hôm nay: `U1`–`U5` và `J1`–`J7` (PRD §2) là giả định của chính đội, **chưa người thật nào
xác nhận** (premise P1). Không có con số thị trường nào trong bộ tài liệu này; mọi con số
cần có là thứ đi thu.

## 2. Câu hỏi cổng phải trả lời

Mỗi câu gắn với mục mở và với chỗ nó chạm vào proposal. Cột "Bằng chứng đạt / trượt" là
tóm tắt; định nghĩa chấm điểm ở `cham-diem.md`.

| # | Câu hỏi | Mã | Chạm vào | Bằng chứng đạt | Bằng chứng trượt |
|:---:|:---|:---|:---|:---|:---|
| **C1** | Có người kể được **sự cố cụ thể có số** về hành động vật lý sai hoặc cập nhật hỏng, **trước khi** người phỏng vấn nói con số nào? | P1 · tiêu chí thứ năm của thiết kế GĐ1 | §0.2, §1.1 #2–#3 | ≥ 2 người, trên ≥ 2 tổ chức | 0 người trên toàn bộ các cuộc |
| **C2** | Có tổ chức nào **hôm nay** vận hành **≥ 1.000 thiết bị có cơ cấu chấp hành** và **đang trả tiền theo thiết bị** cho công cụ quản trị (OTA, giám sát, cấu hình)? | `CEO-X2` | §6.3 · §8.7 G1 · Phụ lục G G-a | ≥ 2 tổ chức, nêu được khoản đang chi | Không tổ chức nào ≥ 1.000 thiết bị có actuator, **hoặc** mọi tổ chức lớn đều tự viết và không chi cho công cụ |
| **C3** | Nỗi đau nằm ở đâu: runtime trên thiết bị (**A**), kiểm thử thay đổi trên stack sẵn có (**C**), hay hành động của agent thoại trên cloud (**E**)? | `CEO-X4` | §1.1, §3.7 · thiết kế GĐ1 §Approaches | Một hướng chiếm ≥ 50% số cuộc có tín hiệu mạnh | Không hướng nào quá 1/3 (nỗi đau phân tán, chưa có wedge) |
| **C4** | **Ai ký tiền**, theo đơn vị gì (thiết bị / đội / dự án), và qua đường nào trong ba đường (i) tự làm U3 · (ii) bán Action CI cho chủ U2 · (iii) Approach E? | `CEO-X5` | §6.3, §7 (AURA) · PRD U3 "từ v1.1" | ≥ 2 người nêu **tên vai trò giữ ngân sách** và **một lần mua công cụ tương tự** trong 12 tháng qua | Không ai chỉ được người giữ ngân sách hay lần mua nào |
| **C5** | Tương đương target xuống MCU + fail-closed khi mất mạng (P3) có phải thứ người mua **đã trả giá** vì thiếu? | `CEO-T1` | §3.2 · §10.2 #2 | ≥ 3 cuộc kể sự cố do lệch giữa lab/mô phỏng và thiết bị, hoặc do mất mạng | ≤ 1 cuộc ⇒ chọn nhánh (b): thôi gọi P3 là moat |
| **C6** | Chứng nhận an toàn chức năng (IEC 61508, ISO 13849, hoặc tiêu chuẩn họ tự nêu) có là **điều kiện mua**? | `CEO-T2` | §5 · §10.3 | Ghi được, theo phân khúc, tỷ lệ người nói "không có chứng nhận thì không mua" | — (câu hỏi phân loại: kết quả nào cũng là quyết định IN/OUT) |
| **C7** | Đối thủ thật là ai: họ đang dùng gì hôm nay, và "tự viết" mất bao lâu? | `CEO-T3` | §10.1 | ≥ 10 cuộc nêu giải pháp hiện tại; ≥ 3 cuộc ước lượng thời gian tự viết | < 5 cuộc nêu được ⇒ giữ §10 là bối cảnh, ghi rõ không phải phân tích cạnh tranh |
| **C8** | Bao nhiêu chuyến đi hiện trường mỗi tháng, và bao nhiêu phần do phần mềm/cấu hình (không phải hỏng vật lý)? | Phụ lục G **G-e** | §1.8 (TCO), §6.2 #5 | ≥ 3 tổ chức cho số chuyến và tỷ lệ nguyên nhân | Không ai đếm ⇒ TCO §1.8 giữ nhãn giả định |
| **C9** | Họ đã từng dùng lại cấu hình/chính sách an toàn do bên khác viết chưa? | Phụ lục G **G-d** · §8.7 G2–G3 | §1.7 | ≥ 3 cuộc kể một lần dùng lại thật | Không ai ⇒ hiệu ứng mạng §1.7 giữ nhãn giả định |
| **C10** | Thứ tự quyết định / code: bằng chứng có về **trước** các cam kết code Khối 1b không? | `CEO-T4` | thiết kế GĐ1 §Nhánh quyết định | Trưởng nhóm tự trả lời tại cổng từ kết quả C1–C9 | — (không hỏi khách hàng) |

`CEO-X3` (tỷ lệ discovery 40:1) được Q-20 xử bằng chính cổng này và **không** nằm trong
`TODOS.md` #19; `docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md` §Quyết định 2026-09-23, dòng `CEO-X3`, ghi `CEO-X3 → Q-20`.
Kế hoạch dưới đây chính là câu trả lời cho nó: khoảng 40 giờ của trưởng nhóm thay vì 8.

## 3. Phân khúc và số lượng mục tiêu (đề xuất)

| Phân khúc | Ai (vai trò) | Ánh xạ PRD | Thiết bị điển hình | Cuộc phỏng vấn | Danh sách tiếp cận |
|:---|:---|:---|:---|:---:|:---:|
| **Khách sạn / nghỉ dưỡng** | Chủ / quản lý vận hành villa, resort 10–80 căn (§7.1); trưởng kỹ thuật tòa nhà | U3, U4 | Khóa cửa, điều hòa, đèn, rèm | **5** | 20 |
| **Fleet Operators** | Trưởng vận hành / kỹ thuật của đơn vị đang quản lý 100–10.000 thiết bị đã lắp | U3 | Tủ khóa, máy bán hàng, trạm sạc, barrier, thiết bị IoT lắp đặt | **5** | 20 |
| **Smart Home** | Trưởng nhóm sản phẩm/nhúng của hãng thiết bị nhà; đơn vị tích hợp nhà thông minh | U1, U2, U5 | Đèn, khóa, cổng, rèm, trợ lý giọng nói | **5** | 20 |
| **Industrial IoT** | Kỹ sư tự động hóa, trưởng bảo trì, người phụ trách an toàn | U2, U4 | Bơm, van, băng tải, rơ-le, còi báo | **5** | 20 |
| **Tổng** | | | | **20** | **80** |

Tỷ lệ chuyển đổi tiếp cận → cuộc có bản ghi là **giả định cần kiểm** (khoảng 25%); thiết kế GĐ1
ghi mức 15–30 lượt tiếp cận cho 3 cuộc có bản ghi, nên con số 80 có thể thiếu. Theo dõi hằng
ngày ở mục 5; nếu tới 10-10 một phân khúc có < 2 cuộc đã hẹn, mở rộng danh sách của phân khúc đó
thêm 10 và báo trong họp đứng.

Khảo sát (`survey.json`) mục tiêu ≥ 40 câu trả lời đủ, **chỉ để sàng lọc người phỏng vấn và ước
lượng quy mô**; không quyết go/stop từ khảo sát (khảo sát đo ý kiến, cổng cần hành vi đã xảy ra).

Tiêu chí nhận người phỏng vấn: người **đã tự tay** xử lý thiết bị ngoài hiện trường hoặc ký tiền
cho nó trong 12 tháng qua. Không nhận: người trong đội NeuroEdge, người chỉ quan tâm công nghệ,
nhà đầu tư.

## 4. Ai làm gì

| Vai trò | Người | Việc | Giờ ước tính |
|:---|:---|:---|:---:|
| Chủ trì (Q-20) | Trưởng nhóm | Duyệt danh sách, phỏng vấn chính, chấm điểm, viết quyết định | ~40 |
| Người ghi | Đề xuất: một người ngoài đường găng A1 (không phải V1) | Ghi nguyên văn, bấm giờ "con số đầu tiên xuất hiện lúc nào, ai nói trước" | ~20 |
| Người chấm thứ hai | Đề xuất: V3 hoặc người ghi của phân khúc khác | Chấm độc lập từ bản ghi, không dự phỏng vấn đó | ~6 |
| Người chạy demo | Trưởng nhóm hoặc V3 | Chạy `demo.md` **sau** phần câu hỏi vấn đề, chỉ khi người được phỏng vấn đồng ý | ~5 |
| V1, V2 | — | **Không tham gia** (đường găng A1 → A2) | 0 |

Giờ là ước tính của bộ tài liệu này: 20 cuộc × (45 phút + 30 phút ghi chép) + tuyển + tổng hợp.

## 5. Kế hoạch theo ngày (2026-09-24 → 2026-10-25)

| Ngày | Việc | Đầu ra | Ai |
|:---|:---|:---|:---|
| 09-24 → 09-26 | Duyệt bộ tài liệu này; trang khảo sát đã dựng (link ở đầu tệp) — chia sẻ cho người ghi; chạy thử `demo.md` trên máy demo | Trang khảo sát chạy; máy demo đã qua checklist `demo.md` §0 | Trưởng nhóm |
| 09-26 → 09-30 | Lập danh sách 20 người/phân khúc từ mạng quan hệ, khách hàng hiện có của tổ chức, cộng đồng kỹ thuật | Bảng tiếp cận (tên, tổ chức, phân khúc, kênh, trạng thái) — **không đưa vào kho** | Trưởng nhóm |
| 09-28 | A1 bắt đầu (Q-19); gửi đợt tiếp cận 1 + link khảo sát | ≥ 40 lời mời đã gửi | Trưởng nhóm |
| 09-30 → 10-02 | 2 cuộc thử (1 nội bộ ngoài đội, 1 thật); sửa câu hỏi nào gây dẫn dắt | `phong-van.md` bản chỉnh | Trưởng nhóm + người ghi |
| 10-01 → 10-10 | **Đợt phỏng vấn 1**: mục tiêu 10 cuộc (≥ 2 mỗi phân khúc) | 10 bản ghi + chấm sơ bộ trong 24 giờ sau mỗi cuộc | Trưởng nhóm + người ghi |
| 10-05 | Đợt tiếp cận 2 (40 lời mời còn lại + người từ khảo sát để lại liên hệ) | | Trưởng nhóm |
| 10-10 | **Điểm kiểm giữa kỳ**: đếm cuộc theo phân khúc, đếm C1 | Quyết định mở rộng danh sách phân khúc thiếu | Trưởng nhóm |
| 10-11 → 10-19 | **Đợt phỏng vấn 2**: 10 cuộc còn lại; cuộc thứ hai (demo sâu) với người có tín hiệu mạnh | 20 bản ghi | Trưởng nhóm + người ghi |
| 10-20 → 10-21 | Cuộc bù cho phân khúc < 4 cuộc; đóng khảo sát 10-21 23:59 | Dữ liệu khóa | Trưởng nhóm |
| **10-22** | **Chấm độc lập** hai người trên mọi bản ghi; đối chiếu chênh lệch ≥ 1 điểm | Bảng điểm cuối (`cham-diem.md` §2) | Trưởng nhóm + người chấm thứ hai |
| 10-23 | Tổng hợp: điểm theo câu hỏi × phân khúc, trích dẫn nguyên văn, số liệu khảo sát | Bản tổng hợp 2 trang | Trưởng nhóm |
| 10-24 | Dự thảo quyết định theo mẫu `cham-diem.md` §5; gửi sponsor đọc trước | Dự thảo | Trưởng nhóm |
| **10-25** | **Cổng**: đọc mẫu quyết định, chốt từng mục `TODOS.md` #19 | Quyết định đã ký | Trưởng nhóm, sponsor |

Cuộc phỏng vấn: 45 phút. 30 phút đầu chỉ hỏi về quá khứ (`phong-van.md`); 10 phút demo **nếu** họ
muốn xem; 5 phút kết. Không demo cho ai mà phần vấn đề chưa xong.

## 6. Ghi kết quả thế nào

Mô tả việc cần làm sau cổng; bộ tài liệu này **không sửa** tệp nào trong kho.

| Nơi | Ghi gì |
|:---|:---|
| `neuroedge-prd.md` §15 | Một dòng quyết định mới (số tiếp theo sau Q-27, hôm nay là **Q-28**): *"Kết quả cổng nhu cầu 2026-10-25"* — số cuộc theo phân khúc, điểm C1–C9, nhánh đã chọn (go / adjust / stop), phân khúc đầu tiên, và mỗi mục `CEO-*` thành quyết định con hoặc đóng |
| `TODOS.md` #19 | Từng mã (`CEO-X2`, `X4`, `X5`, `T1`, `T2`, `T3`, `T4`) gạch và dẫn tới Q-28; mục nào còn mở phải có **mốc kích hoạt mới** (luật của `TODOS.md`) |
| `neuroedge-roadmap.md` §0 | Dòng cổng nhu cầu ở bảng điều khiển: trạng thái, dẫn Q-28 |
| `CHANGELOG.md` `[Chưa phát hành]` | Một mục ngắn (CLAUDE.md "Khi xong một task", `CONTRIBUTING.md` §8) |
| `docs/archive/` | Bản tổng hợp **ẩn danh** (vai trò + phân khúc, không tên người, không tên tổ chức nếu chưa được đồng ý). Bản ghi thô **không vào kho** — `TODOS.md` #4 (PII) |
| `neuroedge-proposal.md` §1.8, §8.7, §10, Phụ lục G | Chỉ sửa nếu Q-28 đổi một giả định; mỗi con số thị trường mới phải dẫn nguồn là cuộc phỏng vấn nào (mã ẩn danh) |

Nếu kết quả là **stop** cho Khối 1b, đó là đổi phạm vi: theo `CONTRIBUTING.md` xem việc nào cần
RFC; đổi hướng sản phẩm không đụng `schemas/` thì không cần RFC, nhưng phải có dòng PRD §15.

## 7. Điều bộ tài liệu này không làm

- Không đưa ra con số thị trường. Mọi con số trong proposal (§1.8 TCO, §6.3 dự phóng, Phụ lục G)
  vẫn là giả định cho tới khi một cuộc phỏng vấn thay nó.
- Không hứa tính năng chưa có. `demo.md` liệt kê từng thứ **không** được nói là đã có.
- Không thay cổng Tuần 3 của thiết kế GĐ1 bằng thứ khác; C1 giữ nguyên ngưỡng của nó, chỉ thêm
  các câu C2–C10 mà Q-20 giao.
