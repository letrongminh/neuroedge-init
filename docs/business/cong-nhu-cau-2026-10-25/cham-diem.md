# Chấm điểm — cổng nhu cầu 2026-10-25

Chấm từ **bản ghi**, không từ trí nhớ. Mỗi cuộc do hai người chấm độc lập (`README.md` §4). Chỉ hành
vi đã xảy ra được điểm; ý kiến, lời khen, "chắc sẽ" đều là 0.

## 1. Thang cho từng cuộc

### 1.1 Câu có điểm 0 / 1 / 2

| Mã | Câu cổng | 2 | 1 | 0 |
|:---|:---:|:---|:---|:---|
| `P1` | C1 | Sự cố cụ thể (khi nào, thiết bị nào, chuyện gì) **và** họ tự nêu một con số (tiền, giờ, chuyến, số máy) **trước** khi người hỏi nói số nào | Sự cố cụ thể nhưng không có số, **hoặc** số chỉ ra sau khi người hỏi gợi ý | Không có sự cố cụ thể; chỉ giả định "có thể xảy ra" |
| `CEO-X2` | C2 | Tổ chức vận hành **≥ 1.000** thiết bị có cơ cấu chấp hành **và** đang trả định kỳ **theo thiết bị** cho công cụ quản trị (nêu được khoản) | Đúng một trong hai: ≥ 1.000 nhưng tự viết hoặc trả theo dự án/đội; **hoặc** trả theo thiết bị nhưng < 1.000 | < 100 thiết bị có actuator, hoặc không chi gì cho công cụ |
| `CEO-X5` | C4 | Nêu **vai trò giữ ngân sách** **và** một lần mua công cụ tương tự trong 12 tháng qua (có tiền hoặc thời gian mua) | Đúng một trong hai | Không nêu được |
| `CEO-T1` | C5 | Sự cố có hậu quả do **mất mạng** hoặc do **lệch giữa lab/mô phỏng và thiết bị** hoặc do **đổi chip** | Yêu cầu offline / đổi chip có thật (hợp đồng, kế hoạch đã duyệt) nhưng chưa gây sự cố | Không |
| `CEO-T3` | C7 | Nêu giải pháp đang dùng **và** chi phí hoặc thời gian của nó (tự viết: số người × số tháng) | Nêu giải pháp, không có chi phí | Không nêu |
| `G-e` | C8 | Số chuyến hiện trường mỗi tháng **và** tỷ lệ do phần mềm/cấu hình | Số chuyến, không có tỷ lệ | Không đếm |
| `G-d` | C9 | Một lần dùng lại chính sách hay cấu hình **an toàn** do bên khác viết | Dùng lại cấu hình không liên quan an toàn, hoặc chỉ trong nội bộ | Không (ghi thêm `✗` nếu họ **từ chối** dùng đồ người khác và nêu lý do) |
| Cam kết | E4 | Cam kết có ngày hoặc có người: buổi thứ hai với đội kỹ thuật · nhật ký sự cố ẩn danh · thử trên 1 thiết bị · giới thiệu người ký tiền | Giới thiệu tên một người khác | "Gửi tài liệu cho tôi" hoặc không có |

### 1.2 Câu phân loại (ghi nhãn, không cộng điểm)

| Mã | Câu cổng | Nhãn |
|:---|:---:|:---|
| `CEO-X4` | C3 | **A** — nỗi đau chỉ giải được bằng gate chạy trên thiết bị (chặn tại chỗ, khi mất mạng, khi đổi chip) · **C** — nỗi đau là kiểm thử thay đổi trên stack họ đang có; họ không đổi runtime · **E** — sự cố nặng nhất nằm ở hành động phần mềm của agent (hoàn tiền, đổi tài khoản, cam kết thanh toán) · **—** không có. Kèm **độ mạnh** = điểm `P1` của chính sự cố đó |
| `CEO-X5` | C4 | Đường thu: **(i)** họ muốn mua **kết quả vận hành** (thiết bị + dịch vụ, kiểu AURA), tức tổ chức mình tự làm U3 · **(ii)** họ là chủ đội U2, trả cho công cụ kiểm thử theo đội · **(iii)** = nhãn E ở trên |
| `CEO-T2` | C6 | **R** — không có chứng nhận thì không mua · **P** — ưu tiên, không bắt buộc · **N** — không liên quan. Kèm **tên tiêu chuẩn họ tự nêu** |
| Quy mô | C2 | Số thiết bị có actuator (ghi số thô) và đơn vị tính tiền họ đang trả (thiết bị / site / dự án / đội / một lần) |

### 1.3 Hai người chấm lệch nhau

- Lệch 1 điểm: thảo luận trên trích dẫn; không thống nhất thì lấy **điểm thấp hơn**.
- Lệch 2 điểm: đọc lại bản ghi cùng nhau; nếu vẫn lệch, câu đó ghi 0 và đánh dấu trong tổng hợp.
- Nhãn phân loại lệch: ghi cả hai, tính là "—" khi cộng dồn.

## 2. Bảng điểm (mỗi dòng một cuộc)

| Mã cuộc | Phân khúc | Vai trò | P1 | X2 | X5 | T1 | T3 | G-e | G-d | Cam kết | X4 | Đường X5 | T2 | Số thiết bị | Đơn vị tính |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---:|:---|
| HS-01 | Khách sạn | | | | | | | | | | | | | | |
| FL-01 | Fleet | | | | | | | | | | | | | | |
| SH-01 | Smart Home | | | | | | | | | | | | | | |
| IN-01 | Industrial | | | | | | | | | | | | | | |

Kèm mỗi dòng: 1–3 trích dẫn nguyên văn có số (mã cuộc + phút).

## 3. Quy tắc cộng dồn

Mẫu nhỏ (≤ 5 cuộc/phân khúc), nên **đếm số cuộc đạt 2**, không lấy trung bình.

| Chỉ số | Cách tính |
|:---|:---|
| `N2(x, s)` | Số cuộc ở phân khúc `s` có điểm 2 ở mã `x` |
| `N2(x)` | Tổng `N2(x, s)` trên cả bốn phân khúc, **đếm theo tổ chức** (hai người cùng tổ chức tính một) |
| Tỷ lệ nhãn | Với `CEO-X4`: số cuộc mang nhãn A / C / E chia cho số cuộc có `P1 ≥ 1` |
| Điểm phân khúc | `N2(P1, s) + N2(Cam kết, s)`; hoà thì so `N2(X5, s)` |
| Đủ dữ liệu | Phân khúc có **≥ 3 cuộc** đã chấm; toàn cổng có **≥ 12 cuộc** |

Khảo sát (`survey.json`) **không** vào điểm. Chỉ dùng để: (a) ước lượng phân bố quy mô thiết bị theo
phân khúc, (b) đối chiếu xem người phỏng vấn có lệch quá xa người trả lời khảo sát không, (c) tìm
người để phỏng vấn thêm.

## 4. Ngưỡng quyết định

### 4.1 I3–I7 — giữ nguyên nhánh của thiết kế GĐ1

Ngưỡng này là bảng cổng nhu cầu của thiết kế GĐ1 (`docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md`),
đếm theo `N2(P1)`. Nhánh áp cho các increment **I3–I7** (roadmap §0.2; tên lịch sử: Khối 1b). Theo
Q-20 nó **không chặn** I1 và I2.

| Kết quả | Nhánh | Hành động |
|:---|:---:|:---|
| `N2(P1) ≥ 2` | **Go** | I3–I7 đi tiếp theo roadmap §0.2 |
| `N2(P1) = 1` | **Adjust** | Thêm 5 cuộc, chấm lại trước **2026-11-16** (hạn chấm lại) |
| `N2(P1) = 0` | **Stop** | I3–I7 đóng băng, I1 và I2 làm tiếp; một PR lập lại kế hoạch (roadmap §0.2). Đưa Approach C ra sponsor như đổi hướng có bằng chứng |
| Toàn cổng < 12 cuộc | **Hoãn** | Cổng lùi, I1 và I2 chạy tiếp, trưởng nhóm báo sponsor tiếp cận là rủi ro mới |

Kèm điều kiện hướng (`CEO-X4`): nếu nhãn **C** ≥ 50% và **A** < 25% ⇒ dù `P1` đạt Go, nhánh là
**Adjust**: đặt Approach C song song trước khi cam kết I3–I7. Nếu nhãn **E** ≥ 50% ⇒ ghi Approach E
thành phương án chính thức để sponsor chọn. (Approach A–E: `docs/user/thuat-ngu.md` §3.)

Một phần I3–I7 đã làm sớm, không cần bo mạch: walker gate và sổ token C, self-test và vết ghi UART
trên QEMU (TSK-S4-02, S4-07, S4-08, S4-09), đặc tả FSM thoại (TSK-S2-07). Nhánh **Stop** dừng phần
còn lại (driver, thoại, công khai, OTA); phần đã có giữ nguyên trong kho; có tiếp tục bảo trì nó hay
không thì ghi trong quyết định cổng (§5).

### 4.2 Mô hình thương mại (`CEO-X2`, `CEO-X5`)

| Kết quả | Nhánh | Ghi vào quyết định |
|:---|:---:|:---|
| `N2(X2) ≥ 2` **và** `N2(X5) ≥ 2` | **Go** | Giữ premise $1/thiết bị/tháng làm giả thuyết chính (G-a), vẫn là giả định cho tới khi có hợp đồng |
| Có tổ chức ≥ 1.000 thiết bị nhưng đơn vị tính họ đang trả **không phải** thiết bị | **Adjust** | Đơn vị tính của §6.3 đổi theo đơn vị đa số (site / đội / dự án) |
| Không tổ chức nào ≥ 1.000 thiết bị có actuator | **Stop** | Fleet OS không phải doanh thu đầu tiên; chọn đường (i)/(ii)/(iii) có nhiều nhãn nhất trong các cuộc `X5 ≥ 1` |

### 4.3 Các mục TASTE

| Mã | Quy tắc |
|:---|:---|
| `CEO-T1` | `N2(T1) ≥ 3` ⇒ giữ P3 là moat, nhánh (a); ngược lại nhánh (b): moat là thư viện gate từ sự cố thật + corpus phát lại |
| `CEO-T2` | Phân khúc có nhãn **R** ≥ 3/5 ⇒ quyết IN (mức, ai làm) hoặc OUT (ghi rõ phân khúc đó bị loại khỏi Giai đoạn 1, viết P3 hẹp thành *"chính sách như dữ liệu có phiên bản, thay cho interlock viết cứng"*). Không để trống |
| `CEO-T3` | Dựng bảng đối thủ (tên · động cơ · kênh · thời gian để copy) từ các cuộc `T3 ≥ 1`. `≥ 3` ước lượng "tự viết" ⇒ ghi trung vị làm "thời gian để copy" của đối thủ số 3. `< 5` cuộc nêu giải pháp ⇒ nhánh (b): giữ proposal §10 làm bối cảnh, ghi rõ không phải phân tích cạnh tranh |
| `CEO-T4` | Trưởng nhóm trả lời: kết quả có trước khi I3 mở không. Có ⇒ đóng. Cổng hoãn ⇒ ghi mốc mới |

### 4.4 Giả định Phụ lục G

| Mã | Quy tắc |
|:---|:---|
| `G-e` | `N2(G-e) ≥ 3` ⇒ thay 70% trong §1.8 bằng tỷ lệ thật (trung vị) kèm mã cuộc. Ngược lại giữ nhãn giả định |
| `G-d` | `N2(G-d) ≥ 3` ⇒ G-d còn sống. Số `✗` > số điểm 2 ⇒ ghi rủi ro cho §1.7 (hiệu ứng mạng) |

### 4.5 Phân khúc đầu tiên

Xếp theo điểm phân khúc (§3). Chọn **một**, tối đa **hai**. Phân khúc có `N2(P1, s) = 0` không được
chọn. Phân khúc không đủ dữ liệu ghi "chưa kết luận", không phải "trượt".

## 5. Mẫu quyết định (điền ngày 2026-10-25)

```text
QUYẾT ĐỊNH CỔNG NHU CẦU — 2026-10-25      (mã Q-N kế tiếp chưa dùng, neuroedge-prd.md §15)
Chủ trì: <trưởng nhóm>         Người chấm thứ hai: <tên>        Sponsor đã đọc: <có/không, ngày>

1. DỮ LIỆU
   Cuộc đã chấm:  Khách sạn __  · Fleet __  · Smart Home __  · Industrial __   · Tổng __ (≥ 12?)
   Tổ chức khác nhau: __        Khảo sát đủ: __ câu trả lời
   Lệch giữa hai người chấm: __ câu lệch 1 điểm · __ câu lệch 2 điểm

2. SỐ ĐẾM (N2 = số tổ chức đạt 2)
   P1  __   X2  __   X5  __   T1  __   T3  __   G-e  __   G-d  __   Cam kết  __
   X4: A __%  C __%  E __%  —  __%          Đường X5: (i) __  (ii) __  (iii) __
   T2: R/P/N theo phân khúc:  KS __/__/__  FL __/__/__  SH __/__/__  IN __/__/__
   Quy mô: số tổ chức ≥ 1.000 thiết bị có actuator: __ ; đơn vị tính đa số: ________

3. NHÁNH
   I3–I7 (§4.1):              [ Go | Adjust | Stop | Hoãn ]   vì: __________________________
   Thương mại (§4.2):         [ Go | Adjust | Stop ]          đường chọn: (i) / (ii) / (iii)
   Phân khúc đầu tiên (§4.5): 1. ______________   2. ______________ (nếu có)

4. TODOS.md #19 — TỪNG MỤC
   CEO-X2  [ đóng | quyết định ]  ______________________________________________
   CEO-X4  [ đóng | quyết định ]  A / C / D / E: _________________________________
   CEO-X5  [ đóng | quyết định ]  đường (i)/(ii)/(iii): ___________________________
   CEO-T1  [ (a) | (b) ]          ______________________________________________
   CEO-T2  [ IN | OUT ]           mức / ai làm, hoặc người mua bị loại: ____________
   CEO-T3  [ (a) | (b) ]          bảng đối thủ ở: ______________________________
   CEO-T4  [ đóng | mốc mới ]     ______________________________________________
   Mục nào còn mở: mốc kích hoạt mới = __________ (luật TODOS.md: không mốc thì không vào sổ)

5. GIẢ ĐỊNH PHỤ LỤC G
   G-a  [ còn giả định | đổi ]   G-d  [ sống | rủi ro ]   G-e  [ còn giả định | thay bằng __% ]

6. BA TRÍCH DẪN MẠNH NHẤT (mã cuộc · phút · nguyên văn có số)
   1. ______________________________________________________________
   2. ______________________________________________________________
   3. ______________________________________________________________

7. BA TRÍCH DẪN NGƯỢC MẠNH NHẤT (bằng chứng chống lại nhánh đã chọn)
   1. ______________________________________________________________
   2. ______________________________________________________________
   3. ______________________________________________________________

8. VIỆC SAU CỔNG (README.md §6)
   [ ] PRD §15 (Q-N của cổng)   [ ] TODOS.md #19   [ ] roadmap §0   [ ] CHANGELOG [Chưa phát hành]
   [ ] docs/archive/ bản tổng hợp ẩn danh   [ ] proposal (chỉ nếu đổi giả định)

Ký: ____________________ (trưởng nhóm)        ____________________ (sponsor)
```

Mục 7 là bắt buộc. Một quyết định không nêu được bằng chứng chống lại nó là quyết định chưa đọc hết
bản ghi.
