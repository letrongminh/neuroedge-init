# Thuật ngữ và mã định danh

Nơi **duy nhất** giải mã các ký hiệu dùng khắp kho. Mỗi dòng: mã là gì, và nơi
định nghĩa nó — đọc định nghĩa đầy đủ ở đó, tệp này không chép lại.

## 1. Mã tài liệu

| Mã | Là gì | Định nghĩa ở |
|:---|:---|:---|
| **FR-xxx-nn** | Yêu cầu chức năng, ví dụ `FR-GATE-03` (nhóm `GATE`, số 03) | `neuroedge-prd.md` §4–§8 |
| **NFR-xxx-nn** | Yêu cầu phi chức năng (hiệu năng, bảo mật, độ bền…) | `neuroedge-prd.md` §9 |
| **P0 · P1 · P2** | Độ ưu tiên: P0 bắt buộc để phát hành · P1 trượt được sang bản vá · P2 nếu còn nguồn lực | tệp này |
| **A1–A9 · B1–B5 · C1–C8** | Tiêu chí **nghiệm thu phát hành**: A = v1.0 (I7) · B = Developer Beta (I8) · C = v1.1 (I9–I10) (vd C8: độ trễ `SystemOne` < 100 ms). Giá trị đo B1–B5: roadmap §5.5 | `neuroedge-prd.md` §11 |
| **M1–M5** | Mục tiêu sản phẩm (M1 = lập trình viên lạ chạy được agent có gate mà không cần phần cứng, TTFV trung vị < 10 phút trên 10 người). Chỉ mang nghĩa này — cột mốc kế tiếp của roadmap là **I1**, nơi đo sớm M1 trên 3 người; A1 đo đầy đủ ở I7 | `neuroedge-prd.md` §1.3 |
| **TR-1…TR-7** | Tiêu chí ra cấp thực thi của v1.1 (I9–I10) — **khác** bộ C | `neuroedge-roadmap.md` §6.3 |
| **Q-N** | Quyết định kỹ thuật đã chốt hoặc đang mở, đánh số tăng dần, không có số cuối | `neuroedge-prd.md` §15 — **sổ quyết định duy nhất** |
| **PF-1…PF-4** | Bộ lọc ưu tiên tính năng — **khác** mã rủi ro `R-n` | `neuroedge-proposal.md` §2 |
| **R-1…R-7** | Rủi ro sản phẩm — **khác** luật chống lệch R1–R12 (không gạch nối) | `neuroedge-prd.md` §13.2 |
| **U1–U6** | Nhóm người dùng (U1 = maker độc lập…; U6 = đội tích hợp robot phân tầng, từ I14) | `neuroedge-prd.md` §2 |
| **J1–J7** | Nhiệm vụ cần hoàn thành — Jobs To Be Done (J1 = "thử agent giọng nói tối nay khi chưa có bo mạch") — **khác** hành trình | `neuroedge-prd.md` §2.2 |
| **Hành trình 1–3** | Ba hành trình người dùng chính: 1 mười phút đầu tiên (U1) · 2 từ sự cố hiện trường về máy lập trình viên · 3 mở rộng từ 1 lên 1.000 thiết bị | `neuroedge-prd.md` §2.3 |
| **G1–G4** | Cột mốc xác thực thị trường Giai đoạn 1 (G1 = 10.000 thiết bị active/tháng…); đạt đủ mới mở Marketplace thu phí | `neuroedge-proposal.md` §8.7 · `neuroedge-prd.md` §14 |
| **G-a…G-e** | Giả định kinh doanh cần kiểm chứng (vd G-e: tỷ lệ chuyến hiện trường do phần mềm) — **khác** G1–G4 | `neuroedge-proposal.md` Phụ lục G |
| **V-G1…V-G5** | Cột mốc xác thực Giai đoạn 2 | `neuroedge-proposal.md` §12.4 |
| **RFC-NNNN** | Đề xuất sửa lược đồ hoặc ngữ nghĩa phân giải gate | `docs/rfc/` |
| **RFC-numeric · RFC-motion · RFC-node · RFC-vision-bậc23 · RFC-pin-extends** | RFC **tạm tên**, chưa cấp số, của bản nháp mở rộng cho robot phân tầng; số cấp khi mở PR RFC | `draft-ke-hoach-mo-rong-robot-fofoca.md` §2.2 |
| **KL-1…KL-5** | Kết luận rà soát HAL dưới ràng buộc vi điều khiển | `docs/spec/hal_mcu_review.md` §1 |
| **RB-1…RB-4** | Ràng buộc kỹ thuật HAL cho bản port lên chip ở I3 (vd RB-3: lệnh chân phải huỷ được) | `docs/spec/hal_mcu_review.md` §2 |
| **Bất biến N** | Một trong mười điều không được phá (vd bất biến 7: `sim` không giàu hơn bo mạch tham chiếu) | `CHANGELOG.md` §3.3 |
| **L1 · L2 · L3** | Cấp đảm bảo của Action CI: L1 replay chuẩn xác · L2 khớp schema + `confidence` · L3 chỉ khẳng định phán quyết gate và lệnh chân | `neuroedge-prd.md` FR-CI-LVL |
| **TODOS #n** | Việc đã xem xét và hoãn có chủ ý, kèm mốc kích hoạt | `TODOS.md` |
| **§x.y** | Mục trong `neuroedge-proposal.md`. Viết *"§x.y của tài liệu này"* khi là mục nội bộ | tệp này |

## 2. Kế hoạch và con người

| Mã | Là gì | Định nghĩa ở |
|:---|:---|:---|
| **I0 … I18** | Increment — đơn vị thời gian của roadmap (Q-39): một năng lực người dùng thấy được, có điều kiện vào, tiêu chí ra, đúng một ngày dự báo, và kết thúc bằng một thẻ phát hành cùng một tín hiệu đo. Thứ tự theo phụ thuộc; chèn giữa dùng hậu tố (`I3a`), không đánh số lại (R2) | `neuroedge-roadmap.md` §0.2 (bảng) · §4–§7 (từng increment) |
| **Preview nội bộ** | I1: người ngoài đội cài từ wheel nội bộ (tag ở roadmap §0.2), TTFV đo tại chỗ trên 3 người. Chưa phát hành ra ngoài | `neuroedge-roadmap.md` §4.2 · Q-39 |
| **Công khai (I6)** | Lần phát hành ra ngoài đầu tiên: repo công khai, `pip install neuroedge` từ PyPI, lược đồ ở URL công khai — khi demo thoại chạy trên `sim`, `linux` và Box-3. Trước I6 mọi tag là nội bộ | `neuroedge-roadmap.md` §4.7 · Q-39 · `docs/release.md` |
| **Dự báo** | Ngày duy nhất của một increment, chỉ ghi ở roadmap §0.2. Chỉ đổi cùng PR với bằng chứng làm nó đổi, và dời luôn các increment phụ thuộc (R4, R5). "sau Ix" = increment có điều kiện, chưa có ngày | `neuroedge-roadmap.md` §0.2, §2.4 |
| **Ghi chú thiết kế** | Tài liệu thiết kế không lịch, không trạng thái, không tiêu chí ra: `neuroedge-roadmap-phase1-5.md`, `neuroedge-roadmap-phase2.md`, `draft-ke-hoach-mo-rong-robot-fofoca.md`, `draft-rfc-node-giao-thuc-dieu-phoi.md`. Dẫn mã TSK của roadmap (R1, R8) | `neuroedge-roadmap.md` (đầu tệp) · `CONTRIBUTING.md` §8.1 |
| **R1 … R12** | Mười hai luật chống lệch của roadmap (vd R6: không xếp lịch bằng nhãn tuần/tháng đánh số) — **khác** rủi ro `R-n` của PRD | `neuroedge-roadmap.md` §2.4 |
| **Khối 1a · 1b · 2 · 3 · 4 · 5** | Tên lịch sử của khối công việc Giai đoạn 1: 1a lõi + Action CI · 1b vi điều khiển · 2 Fleet OS · 3 các đường ray nền tảng. Khối 2 → I9, Khối 3 → I10; task của 1a và 1b rải vào I0–I7. Khối 4 (AURA thực địa) và 5 (Marketplace) nằm ngoài roadmap | `neuroedge-roadmap.md` Phụ lục A · §8.1 |
| **Khối V1a · V1b · V2 · V3 · P1 · P2** | Khối công việc Giai đoạn 2, tên dùng trong ghi chú thiết kế: V1a → I11 · V1b → I15 · V2 → I16 · V3 → I17 · P1 → I13 · P2 → I18, riêng P2-04, P2-05 → I14 | thiết kế: `neuroedge-roadmap-phase2.md` · ánh xạ: `neuroedge-roadmap.md` Phụ lục A |
| **Chặng W0 … W4 · W-item** | Chặng của ghi chú thiết kế robot phân tầng (W0 việc nhẹ · W1 HAL và an toàn actuator · W2 hạ tầng tin cậy · W3 multi-node · W4 hệ sinh thái); `W3-1`… là chỉ mục trong ghi chú đó, task thật là `TSK-W3-01`… trong roadmap. Toàn bộ W0 và vài task W2 rải vào I2, I6, I7, I10; phần còn lại là I14 | thiết kế: `draft-ke-hoach-mo-rong-robot-fofoca.md` · ánh xạ: `neuroedge-roadmap.md` Phụ lục A |
| **Khối N0 … N7 · N5b** | Khối công việc NeuroBrain (Giai đoạn 1.5), cùng thuộc I12; task `TSK-Nk-mm` | thiết kế: `neuroedge-roadmap-phase1-5.md` · task: `neuroedge-roadmap.md` §7.2 |
| **NeuroBrain** | Trợ lý hội thoại dựng mạch cho Physical AI — "Build Physical AI by conversation, under contract" (Q-31); increment I12, sau Beta (Q-40) | `neuroedge-roadmap-phase1-5.md` §1 |
| **B-1** | Bất biến: gói `neuroedge.brain` không gọi HAL trực tiếp, chỉ qua `dispatch()` → gate | `neuroedge-roadmap-phase1-5.md` §1 |
| **Sprint 1…6** | Tên lịch sử: sáu sprint của kế hoạch gốc (Khối 1a, 1b). Task đã xong của Sprint 1–3 thuộc I0; task còn lại dời sang increment, mã `TSK-S<n>-*` giữ nguyên. Không dùng để xếp lịch mới (R6) | `neuroedge-roadmap.md` Phụ lục A |
| **`TSK-<họ>-<nn>`** | Một task. Mã cho biết task từ đâu ra; increment cho biết khi nào làm; mã không bao giờ đánh lại. Họ: `TSK-S1-*` … `TSK-S6-*` (Sprint 1–6, vd `TSK-S2-03` = Sprint 2, task 03) · `TSK-K2-*`, `TSK-K3-*` (Khối 2, 3) · `TSK-N*-*` (NeuroBrain) · `TSK-V1a-*` … `TSK-V3-*`, `TSK-P1-*`, `TSK-P2-*` (Giai đoạn 2) · `TSK-W…` · `TSK-I…` (hai dòng dưới) | `neuroedge-roadmap.md` §2.4 (họ mã task) |
| **`TSK-W<chặng>-<nn>`** | Task robot phân tầng; số theo chỉ mục của ghi chú thiết kế (W3-1 → `TSK-W3-01`); mục đã gộp vào task có sẵn để lại khoảng trống | `neuroedge-roadmap.md` §2.4 · Phụ lục A |
| **`TSK-I<n>-<nn>`** | Việc mới không thuộc họ nào; `n` là increment đầu tiên lên lịch nó (vd `TSK-I1-01`). Dời sang increment khác thì mã giữ nguyên | `neuroedge-roadmap.md` §2.4 |
| **Tuần N · Tháng N** | Nhãn lịch cũ, đếm từ ngày bắt đầu chương trình 2026-09-21 — không phải tháng dương lịch. Bỏ từ Q-39: lịch mới dùng increment và ngày tuyệt đối (R6). Gặp trong tài liệu lịch sử (`docs/archive/`, `CHANGELOG.md` §1) thì ngày tuyệt đối đi kèm là đúng | `neuroedge-roadmap.md` §2.4 (R6) |
| **V1–V4** | Vai trò trong đội: V1 kỹ sư lõi · V2 kỹ sư nhúng · V3 trải nghiệm lập trình viên · V4 hạ tầng dịch vụ | `neuroedge-roadmap.md` §1.1 |
| **V5** | Kỹ sư thị giác: HAL thị giác, mô hình, NPU; có mặt trước I15 | `neuroedge-roadmap.md` §1.1 |
| **V6** | Kỹ sư nhúng thứ hai: âm thanh trên chip, OTA và bảo mật thiết bị, song song với HAL của V2; cần từ 2026-11-16 — giả định của dự báo I5 và I7 (Q-39) | `neuroedge-roadmap.md` §1.1, §1.3 |

> ⚠️ **Hai mã trùng chữ, khác nghĩa:**
> - **A1** là tiêu chí nghiệm thu v1.0 trong PRD, **và** trong tài liệu lịch sử (design doc Giai đoạn 1,
>   Q-19, `CHANGELOG.md` §1) là tên cửa sổ wedge `sim`; A2 tương tự (cửa sổ `linux` + Action CI). Hai
>   cửa sổ này là lịch sử từ Q-39 — việc của chúng nay nằm ở I0–I2 (roadmap Phụ lục A). Tài liệu hiện
>   hành chỉ dùng nghĩa thứ nhất.
> - **V1** là vai trò kỹ sư lõi, **và** là tiền tố Khối V1a/V1b của Giai đoạn 2.
> - **P1** là độ ưu tiên (P0 · P1 · P2), **và** là tiền đề P1 của design doc Giai đoạn 1 (P1–P4), **và**
>   là Khối P1 của Giai đoạn 2 (I13). Bảng chấm của cổng nhu cầu dùng `P1` theo nghĩa thứ hai (điểm cho
>   tiền đề P1).
> - **R1…R12** (luật chống lệch của roadmap) khác **R-1…R-7** (rủi ro PRD) và khác R1… trong biên bản
>   review RFC-0002 (`docs/archive/rfc-0002-review-record.md`).
> - **C1…C8** là tiêu chí nghiệm thu v1.1 trong PRD, **và** C1…C10 là câu hỏi của cổng nhu cầu
>   2026-10-25. Ngữ cảnh kinh doanh (`docs/business/`) luôn theo nghĩa thứ hai.
> - **G1–G4** (cột mốc thị trường) khác **G-a…G-e** (giả định Phụ lục G) và khác **V-G1…V-G5**.

## 3. Mã từ các phiên review

Các mã này chỉ có nghĩa trong biên bản review; nhiều mã đã được giải thành quyết định `Q-N`.

| Mã | Là gì | Định nghĩa ở |
|:---|:---|:---|
| **CEO-X1…X6 · CEO-T1…T4 · CEO-Sn-m** | Phát hiện của review góc nhìn CEO (X = cần người quyết, T = lựa chọn khẩu vị) | `docs/archive/giai-doan-1-review-log.md` |
| **ENG-A1…A3 · ENG-T1…T3 · ENG-Qn** | Phát hiện của review kỹ thuật (A = kiến trúc, T = test, Q = chất lượng mã). Vd `ENG-T3`: thiếu phản chứng cho `budget`/`on_block`/`extends` → TSK-S2-13, TSK-S3-21 | như trên |
| **DX-C1… · DX-Hn · DX-Mn** | Phát hiện của review trải nghiệm lập trình viên (C = critical, H = high, M = medium) | như trên |
| **D6–D11** | Câu hỏi trong phiên /office-hours 2026-09-22 — không có trong kho | `docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md` (đầu tệp) |
| **P1–P4** | Bốn tiền đề của design doc Giai đoạn 1 (P1 điểm đau thuộc U2 · P2 khoảng gate không trống · P3 khác biệt là tương đương target + fail-closed · P4 rủi ro số một là nhu cầu) | `docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md` §Premises |
| **Approach A · B · C · D · E** | Các hướng đi Giai đoạn 1: A wedge `sim` trước (đã chọn) · B spike xuyên tầng · C bán Action CI rời · D bán memo + bản ghi màn hình · E gate/Action CI cho hành động của agent thoại trên cloud | A–C: `docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md` §Approaches · D, E: `docs/archive/giai-doan-1-review-log.md` (`CEO-X4`) |
| **C1…C10** (cổng nhu cầu) | Mười câu hỏi cổng nhu cầu 2026-10-25 phải trả lời — **khác** tiêu chí C1–C8 của PRD | `docs/business/cong-nhu-cau-2026-10-25/README.md` §2 |

## 4. Thuật ngữ sản phẩm

| Thuật ngữ | Nghĩa | Đọc thêm |
|:---|:---|:---|
| **Gate** | Chính sách an toàn dạng YAML cho một hành động vật lý: tiêu chí `evaluate`, điều kiện `allow_when`, hành vi khi bị chặn `on_block`, ngân sách `budget` | `neuroedge-proposal.md` Phụ lục B |
| **Phán quyết (verdict)** | Kết quả lượng giá một gate: `ALLOW` hoặc `BLOCK` kèm `reason` | `python/neuroedge/engine/verdict.py` |
| **Kế thừa gate (`extends`)** | Gate con dùng lại gate cha và **chỉ được siết chặt** (năm nguyên tắc B.5) | `neuroedge-proposal.md` Phụ lục B.5 |
| **Fail-closed / fail-open** | Khi không thẩm định được gate — lỗi, timeout, hoặc mất mạng mà fallback ngữ pháp lệnh cục bộ không có hay không chạy (Q-14) — thì chặn (mặc định) / cho qua (chỉ khi gate tự khai `fail: open`) | `neuroedge-proposal.md` Phụ lục B.4 |
| **Hợp đồng hành động (Action Contract)** | Ràng buộc bắt buộc giữa một hành động vật lý và gate của nó: HAL không thực thi hành động nào chưa qua gate | `neuroedge-proposal.md` §3.5 |
| **Lớp hợp nhất (unified layer)** | Phạm vi của NeuroEdge: HAL, nhận thức âm thanh, điều phối agent và kiểm soát hành động trong một nền tảng | `neuroedge-proposal.md` §0.2 |
| **HAL theo hợp đồng năng lực** | HAL đối chiếu hai chiều yêu cầu của agent với năng lực của bo mạch lúc build | `neuroedge-proposal.md` §3.3 · Phụ lục A |
| **HAL port** | Bản hiện thực HAL cho một môi trường mới, có thể do bên thứ ba viết; đúng hay không chứng minh bằng bộ kiểm thử tuân thủ | `neuroedge-proposal.md` §1.7 |
| **Nguyên tắc tương đương môi trường** | Cùng mã agent cho cùng chuỗi quyết định trên mọi target; mức cam kết theo bậc target | `neuroedge-proposal.md` §3.2 |
| **OpenAI-compatible · adapter** | Chuẩn kết nối mặc định của lớp trừu tượng nhà cung cấp: nền tảng theo OpenAI API (một base URL, một key) chỉ cần cấu hình — chat completions, audio, và endpoint quyết định có kiểu như System One API cho Jev; dịch vụ khác cần một adapter mỏng do người dùng viết (`python:pkg.mod:factory`) | `neuroedge-proposal.md` §6.1 · Q-12 |
| **Lớp trừu tượng nhà cung cấp** | Phần của lõi do người dùng tự vận hành, chuẩn hoá kết nối tới LLM, ASR, TTS (FR-GW; tên cũ *Inference Gateway*) | `neuroedge-prd.md` §8.1 |
| **Fleet Management OS (Fleet OS)** | Dịch vụ thương mại duy nhất: quản trị, giám sát, chứng thực và OTA cho đội thiết bị | `neuroedge-proposal.md` §6.2 |
| **Source-available · mã nguồn công khai** | Mã ai cũng đọc được nhưng giấy phép giới hạn cách dùng — **không** phải *open source* theo OSI. Lõi NeuroEdge là source-available; lược đồ, đặc tả và bộ kiểm thử tuân thủ là **chuẩn mở** | `LICENSING.md` · Q-45 |
| **PolyForm Noncommercial 1.0.0** | Giấy phép của mã NeuroEdge từ Q-45 (thay MIT): miễn phí cho mục đích phi thương mại; dùng thương mại cần license thương mại | `LICENSE` · `LICENSING.md` |
| **License thương mại** | Giấy phép riêng cho doanh nghiệp dùng NeuroEdge vào mục đích thương mại, kể cả nội bộ. Luôn gồm trọn lõi (P-3); cùng Fleet OS là hai dòng doanh thu của nền tảng | `LICENSING.md` · `neuroedge-proposal.md` §6.3 · `TODOS.md` #44 |
| **CLA** | Contributor License Agreement — thỏa thuận người đóng góp bên ngoài ký trước khi PR được merge, để NeuroEdge cấp được license thương mại cho cả phần đóng góp | `CONTRIBUTING.md` §2 · `TODOS.md` #43 |
| **Token phán quyết** | Bằng chứng dùng một lần mà `c.do()` cấp sau một ALLOW; HAL chỉ đổi chân khi có nó | `docs/spec/threat_model.md` |
| **Sổ token (token ledger)** | Nơi phát, kiểm và đóng token phán quyết. Bản host: `TokenLedger` (Python); bản thiết bị: `ne_token.c`, cùng luật, sổ đầy thì đóng an toàn | `python/neuroedge/actions/token.py` · `targets/esp32s3/components/ne_gate/` |
| **`NETR` · `.netree`** | Bố cục nhị phân cố định của cây quyết định trên thiết bị (magic `NETR`, v1); `neuroedge build` ghi `<gate>.netree` và `<gate>.netree.h` | `docs/rfc/0003-bo-cuc-nhi-phan-cay.md` |
| **Walker C** | Hàm C99 duyệt cây `NETR` tại chỗ trong flash, không cấp phát, ra cùng phán quyết với engine host | `targets/esp32s3/components/ne_gate/` (TSK-S4-02) |
| **Cắt lời (barge-in) · `BARGE_IN`** | Người dùng nói chen khi thiết bị đang nghĩ hoặc đang nói; trạng thái tạm của máy trạng thái hội thoại, thực hiện hợp đồng thu hồi lệnh rồi nghe tiếp | `docs/spec/voice_fsm.md` §3–§5 (TSK-S2-07) |
| **Lệnh đang chờ** | Lệnh chân gate đã `ALLOW`, token đã cấp, nhưng chưa giao tới chân (hẹn giờ, hoặc xếp sau câu nói). Chỉ lệnh đang chờ bị cắt lời hủy; lệnh đã giao chạy hết | `docs/spec/voice_fsm.md` §5 |
| **Vector replay trên thiết bị** | Firmware replay từng vết ghi chuẩn mực lúc khởi động: đầu vào đã ghi vào, phán quyết và token do thiết bị tính; `verify --targets esp32s3 --port` so với golden. Lệnh chân lấy operation/duration từ **bảng hành động** dựng trên host | `docs/spec/simulation_coverage.md` §4 (TSK-S4-09) |
| **Dòng `NE1 `** | Một sự kiện vết ghi trên UART của firmware: tiền tố `NE1 ` (có dấu cách — khác mã lỗi `NE1001`) rồi một sự kiện `trace.v1` dạng JSON; mỗi phiên mở bằng `device_info`, đóng bằng `trace_end` | `docs/spec/simulation_coverage.md` §4 (TSK-S4-09) |
| **`digests.lock`** | Danh sách digest của gate chuẩn mực; CI chặn mọi thay đổi digest không kèm RFC | `CONTRIBUTING.md` §3 |
| **FOFOCA** | Robot tham chiếu của bản nháp mở rộng: Pi 5 làm não (`linux`), nhiều MCU (motor, màn hình, tay máy) làm tay chân — mọi hành động vật lý vẫn qua gate, kể cả khi trải trên nhiều chip | `draft-ke-hoach-mo-rong-robot-fofoca.md` §1 |
| **Node · multi-node** | Node = một môi trường thực thi có HAL và **gate riêng** trong một robot nhiều MCU; multi-node = một robot nhiều node (khác Fleet OS = nhiều thiết bị độc lập). Chưa có trong mã | `draft-rfc-node-giao-thuc-dieu-phoi.md` §3.1 |
| **Black channel** | Mẫu của IEC 61784-3: truyền thông an toàn trên mạng **không tin cậy** — mỗi thông điệp tự mang trường bảo vệ, mỗi thiết bị tự thực hiện chức năng an toàn. Đề xuất cho wire giữa các node | `draft-rfc-node-giao-thuc-dieu-phoi.md` §3.3 |
| **Zenoh-pico** | Giao thức pub/sub nhẹ cho MCU (nhánh giấy phép Apache-2.0), chốt làm wire giữa Pi và node; `zenohd` chạy trên Pi. Spike W3-1 là phép thử loại, micro-ROS là phương án B | `neuroedge-prd.md` §15 Q-36 |
| **Token thuê có hạn (lease)** | Token cho `motion.*`: kênh + biên độ tối đa + thời hạn ngắn; mỗi lệnh qua gate gia hạn, hết hạn thì cơ cấu về trạng thái an toàn. Chưa có trong mã | `neuroedge-prd.md` §15 Q-37 |
| **SIL · PL** | Mức toàn vẹn an toàn (IEC 61508) và mức hiệu năng an toàn (ISO 13849) của một chức năng an toàn được chứng nhận. NeuroEdge không có cả hai | `docs/spec/threat_model.md` §3b (Q-38) |
| **Crash-safe** | Chân về trạng thái an toàn cả khi tiến trình sập hoặc bị SIGKILL — chỉ phần cứng bảo đảm được (kéo xuống, watchdog), phần mềm thì không | `neuroedge-roadmap-phase1-5.md` §2.3 |
| **Phong bì N2** | Giới hạn tổng thời gian bật và tần suất theo chân, khai ở `board.v1` (RFC-0007), cưỡng chế trong HAL trước `authorize` | `neuroedge-roadmap-phase1-5.md` §7 |
| **MHS** | Chuẩn thiết bị robot của Anthropic (research preview); NeuroEdge theo dõi, không đầu tư ở v1.0 (Q-29) | `neuroedge-proposal.md` §10.1, Phụ lục H.3 |
| **Physical AI** | AI điều khiển thứ trong thế giới thật — chốt cửa, đèn, rơ-le, động cơ. Lời nói sai thì sửa được; hành động vật lý sai thì không, nên mọi hành động đi qua gate | `neuroedge-proposal.md` §0.2 |
| **`c.do()` · `c.say()`** | Cổng duy nhất tới thế giới vật lý · lời nói (không qua gate) | `python/neuroedge/actions/` |
| **RAG** | Retrieval-augmented generation: tìm đoạn tri thức liên quan (cục bộ, tất định) rồi để System 2 trả lời dựa trên chúng. Mất mạng thì nói câu trả lời cục bộ | `python/neuroedge/models/knowledge.py` |
| **Tool call** | Một lời gọi `@action` dạng `{name, arguments, source}`. Câu khớp ngữ pháp, System 1/2 và MCP đều gửi tool call; mọi tool call qua kiểm schema rồi gate (Q-24) | `python/neuroedge/actions/tools.py` |
| **MCP** | Model Context Protocol — chuẩn mở để ứng dụng AI gọi tool. `neuroedge mcp serve` đưa các `@action` ra làm tool, vẫn qua gate | `python/neuroedge/mcp_server.py` |
| **Gated Tool Profile** | Chuẩn của NeuroEdge cho tool call tới thiết bị vật lý, đặt trên MCP: ba trạng thái kết quả, nguồn gọi, xác nhận của người, vết ghi. Tài sản chuẩn thứ ba cạnh lược đồ gate và vết ghi | `docs/spec/tool_calling.md` |
| **MCP host** | Bên dùng MCP client để gọi tool. System 2 của agent là MCP host: gọi tool thiết bị qua MCP server của chính agent, và tool thông tin của MCP server bên ngoài (Q-27) | `python/neuroedge/mcp_host.py` |
| **`mcp serve --ui`** | Máy chủ MCP qua stdio kèm trang web `sim` của **cùng phiên**: lời gọi MCP, lệnh gõ và nút xác nhận trên trang dùng chung một phiên | `docs/spec/tool_calling.md` §8 |
| **`mcp desktop-config`** | Lệnh in (hoặc ghi, có sao lưu) mục cấu hình Claude Desktop cho `mcp serve`, bằng đường dẫn tuyệt đối | `docs/spec/tool_calling.md` §8 |
| **Corpus tool call · NeuroEdge-gated** | `fixtures/tool_calls/{valid,invalid}/` + `expected_results.yaml`; runtime qua corpus này mới được gọi là *NeuroEdge-gated* | `docs/spec/tool_calling.md` §9 |
| **`offline_help`** | Câu trả lời khi System 2 không trả lời được: thiết bị nói các lệnh cục bộ còn dùng được, không đoán hành động | `docs/spec/tool_calling.md` §10 |
| **`confirms` (RFC-0006)** | Trong `on_block: ask`: các tiêu chí mà lời "có" của người trên thiết bị được thay khi gate lượng giá lại. Mọi tiêu chí khác vẫn phải đạt; mô hình và client MCP không xác nhận được | `docs/spec/tool_calling.md` §6 |
| **`call_source`** | Dữ kiện do runtime chèn cho gate: tool call đến từ `local_grammar`, `system_one`, `system_two`, `mcp` hay `test`. Bên gọi không tự khai được | `docs/spec/tool_calling.md` §5 |
| **Nguồn xác nhận (`local_grammar` · `ui`)** | Hai kênh duy nhất được trả lời câu hỏi `ask`: lời gõ/nói khớp ngữ pháp, và nút trên trang của thiết bị. `ui` không phải `call_source` | `docs/spec/tool_calling.md` §6 |
| **HAL · 5 nguyên thủy** | Lớp phần cứng: `audio.in`, `audio.out`, `digital.out`, `sensor.read`, `display` | `neuroedge-prd.md` §4.1 (FR-HAL-01) |
| **Target `sim` · `linux` · `esp32s3`** | Môi trường chạy bậc 1: trình mô phỏng · Linux (RPi 5) · vi điều khiển ESP32-S3-Box-3 | `neuroedge-prd.md` §4.2 (FR-TGT) |
| **Bậc target (1 · 2 · 3)** | Mức cam kết chất lượng theo target (Q-13) | `neuroedge-prd.md` §15 |
| **SystemOne · SystemTwo** | Mô hình trả lời có cấu trúc (bool/level/choice) · mô hình sinh văn bản tự do | `neuroedge-proposal.md` §3.6 |
| **Jev** | Mô hình quyết định của TypeSafe (`typesafe/jev-1.13`, qua OpenRouter), model cloud của System 1 ở v1.0 (Q-4). Không sinh chữ: nhận `state` + câu hỏi có kiểu (noul · score · choice, ứng với `bool` · `level` · `choice`), trả giá trị kèm xác suất qua System One API (`POST {api_base}/systemone`). Bật bằng `[system_one]`; fallback là ngữ pháp lệnh cục bộ | `python/neuroedge/models/providers/systemone_api.py` (TSK-I4-02) · `neuroedge-prd.md` §15 (Q-4) |
| **Provider · `[system_two]` · `neuroedge[cloud]`** | Model thật đứng sau SystemTwo, khai trong bảng `[system_two]` của `agent.toml`: LiteLLM (cài bằng extra `cloud`, Q-10) hoặc adapter tự viết `python:pkg.mod:factory`. Chỉ ghi **tên** biến môi trường chứa key | `python/neuroedge/models/providers/` (TSK-S2-11) |
| **`[system_one]`** | Bảng của `agent.toml` chọn model cloud cho SystemOne (Jev, hoặc adapter tự viết) và **liệt kê** các tiêu chí gate nó được quyết (`criteria`); tiêu chí khác, và mọi lần model không trả lời được, đi thẳng ngữ pháp lệnh. Không có bảng ⇒ như cũ | `python/neuroedge/models/providers/config.py` (TSK-I4-02) |
| **Ngữ pháp lệnh cố định** | Fallback khi mất mạng: danh sách câu lệnh → intent, không mạng, tất định (Q-14) | `fixtures/agents/villa-concierge/commands.toml` |
| **Action CI** | Kiểm thử hồi quy hành vi vật lý bằng vết ghi (record / replay / assert) | `neuroedge-proposal.md` §4.7 |
| **Golden Reference** | Vết ghi có quyết định là quyết định kỳ vọng; replay được so với nó theo phán quyết gate + lệnh chân, bỏ qua timing và chữ | `python/neuroedge/testing/golden.py` (FR-CI-04) |
| **gpio-sim** | Mô-đun kernel Linux tạo chip GPIO ảo qua configfs; CI chạy HAL `linux` trên nó, không cần bo mạch | `scripts/setup_gpio_sim.sh` (Q-16) |
| **Vết ghi (trace)** | Tệp JSON `trace.v1` ghi mọi sự kiện một phiên | `schemas/trace.v1.json` |
| **Wedge** | Lát cắt hẹp nhất chứng minh giá trị trước: `sim` trước, vi điều khiển sau | `docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md` |
| **TTFV** | Time-to-first-value — thời gian từ cài đặt tới lần đầu thấy agent chạy (mục tiêu < 10 phút) | `neuroedge-prd.md` §2.3 (hành trình 1) |
| **CR-1.0** | Change Request 2026-09-21: chuyển kiến trúc sang cloud-first, provider-pluggable | `CHANGELOG.md`, mốc CR-1.0 (2026-09-21) |
| **NE1001…NE5001** | Mã lỗi ổn định, mỗi lỗi có 3 phần: ở đâu · vì sao · cách sửa | `neuroedge-prd.md` Phụ lục B |
