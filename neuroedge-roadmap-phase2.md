# NeuroEdge — Ghi chú thiết kế Giai đoạn 2

## Perception thị giác và phủ rộng phần cứng

> **Ghi chú thiết kế.** Tệp này giữ định vị, nguyên tắc, ranh giới với tầng an toàn và
> thiết kế từng khối của Giai đoạn 2. Nó **không** có lịch, trạng thái, tiêu chí ra, thang
> cắt hay danh mục mua sắm: những thứ đó chỉ nằm ở [`neuroedge-roadmap.md`](neuroedge-roadmap.md) —
> V1a là **I11** (§7.1), V1b là **I15** (§7.5), V2 là **I16** (§7.6), V3 là **I17** (§7.7),
> P1 là **I13** (§7.3), P2 là **I18** (§7.8) trừ TSK-P2-04 và P2-05 ở **I14** (§7.4); thang cắt
> §9.3; mua sắm Phụ lục B. Quyết định chỉ nằm ở `neuroedge-prd.md` §15: **Q-13** (phân tầng
> bậc target), **Q-40** (thứ tự sau Beta), **Q-33** (đội lõi port RP2350 làm node robot),
> **Q-34** (tích hợp ROS 2/Nav2).

**Cập nhật:** 2026-09-25 · lịch sử thay đổi: `CHANGELOG.md`

**Tài liệu nguồn:** `neuroedge-proposal.md` §8.9 · `neuroedge-prd.md` · `docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md`

**Phạm vi:** Khối V1a · V1b · V2 · V3 · P1 · P2

**Ngoài phạm vi:** Khối 4 (AURA thực địa) và Khối 5 (Marketplace) — nằm ngoài roadmap (`neuroedge-roadmap.md` §8.1) và proposal §8. Giai đoạn 2 không thay thế chúng.

---

## Mục lục

1. [Định vị và nguyên tắc](#1-định-vị-và-nguyên-tắc)
2. [Ranh giới với tầng an toàn](#2-ranh-giới-với-tầng-an-toàn)
3. [Giả định nguồn lực](#3-giả-định-nguồn-lực)
4. [Đường găng và phụ thuộc](#4-đường-găng-và-phụ-thuộc)
5. [Khối V1a — Mở danh sách target](#5-khối-v1a--mở-danh-sách-target)
6. [Khối V1b — Thị giác trên `linux`](#6-khối-v1b--thị-giác-trên-linux)
7. [Khối V2 — Thị giác trên `jetson`](#7-khối-v2--thị-giác-trên-jetson)
8. [Khối V3 — Đa phương thức](#8-khối-v3--đa-phương-thức)
9. [Khối P1 và P2 — Nền tảng cho maker](#9-khối-p1-và-p2--nền-tảng-cho-maker)
10. [Cột mốc xác thực](#10-cột-mốc-xác-thực)
11. [Rủi ro và giảm thiểu](#11-rủi-ro-và-giảm-thiểu)
12. [Cắt phạm vi](#12-cắt-phạm-vi)

**Phụ lục**

- [A — Bảng mốc tổng hợp](#phụ-lục-a--bảng-mốc-tổng-hợp)
- [B — Danh mục mua sắm](#phụ-lục-b--danh-mục-mua-sắm)

---

## Quy ước tài liệu

Mọi mã và ký hiệu dùng trong tài liệu này (`TSK-V*` · `TSK-P*`, `V-G1`–`V-G5`, `PF-N`, `§x.y`…) được giải mã ở **[`docs/user/thuat-ngu.md`](docs/user/thuat-ngu.md)** — nơi duy nhất, kèm chỗ định nghĩa đầy đủ.

## 1. Định vị và nguyên tắc

Giai đoạn 2 làm hai việc: mở tầng nhận thức từ thoại sang **thị giác**, và mở danh mục phần cứng từ ba target lên sáu. Cả hai đều là mở rộng tầng L2 và L0 — **không đụng tầng L3**, nơi chứa toàn bộ tài sản lõi.

Về định vị sản phẩm, cần nói thẳng một điều để tài liệu không tự mâu thuẫn: **"nền tảng cho maker" không phải một hướng đi mới.** Nó đã nằm trong tài liệu từ v5.0 dưới các tên khác — cam kết không khóa tính năng cốt lõi sau tường phí (proposal §6.4), quy trình RFC công khai và cam kết chuyển giao lược đồ cho tổ chức trung lập (§1.5, §3.8), Bộ kiểm thử tuân thủ cho bên thứ ba tự hiện thực lại runtime (§3.8 trụ cột 2), Public Gate Registry miễn phí (§1.7), và mô hình "chuẩn mặc định + adapter tự viết" đã áp cho nhà cung cấp AI (PRD P-4, Q-12).

Giai đoạn 2 **đặt tên và hoàn tất** những thứ đó, đồng thời bổ sung phần còn thiếu thật sự:

| Đã có từ trước | Giai đoạn 2 bổ sung |
|:---|:---|
| Chia sẻ **dữ liệu** (gate YAML) | Chia sẻ **mã thực thi** (adapter, HAL port) — kèm lập luận an toàn riêng, vì lập luận cũ không chuyển sang được |
| Phân tầng bo mạch chính thức / cộng đồng ở Phụ lục D.1 | Phân tầng **target** thành hợp đồng tường minh (FR-TGT-08), có cam kết kiểm chứng khác nhau theo bậc |
| Bộ kiểm thử tuân thủ như một ý tưởng quản trị | Bộ kiểm thử tuân thủ như **con đường thi hành** để cộng đồng tự port phần cứng |
| Perception thoại | Perception thị giác, thay thế được qua cùng một giao diện |

### Sáu nguyên tắc định hướng

| # | Nguyên tắc | Hệ quả |
|:---:|:---|:---|
| 1 | **Usecase dễ triển khai trước** | Ưu tiên camera an toàn, cử chỉ, giám sát. Gác lại SLAM, tránh vật cản, drone, AGV |
| 2 | **Nền tảng cho maker, không lock-in** | Mọi tầng mở qua API; người dùng tự may đo module và kéo thư viện bên thứ ba vào |
| 3 | **Năm nguyên tắc bất biến giữ nguyên** | P-1 tới P-5 không đổi. P-2 đã bỏ số đếm ở v5.4 nhưng hệ quả kỹ thuật không đổi |
| 4 | **Perception thay thế được** | Đổi thoại sang thị giác không đụng lớp an toàn hành động |
| 5 | **Milestone-gated** | Mọi chuyển giao khối phụ thuộc kiểm chứng thực tế, không theo lịch giấy |
| 6 | **Chi phí thấp, tiếp cận rộng** | Bắt đầu trên Raspberry Pi 5 kèm NPU rời; Jetson chỉ khi usecase thật sự cần |

---

## 2. Ranh giới với tầng an toàn

Mục này đứng trước mọi thiết kế khối vì nó là điều kiện để phần còn lại được phép tồn tại.

### 2.1 Ba thứ Giai đoạn 2 không được đụng

| Thành phần | Vì sao |
|:---|:---|
| **Gate engine và ngữ nghĩa phân giải** | Đây là tài sản lõi. Thị giác là đầu vào nhận thức (L2), không phải thẩm quyền phán quyết (L3) |
| **Cơ chế fail-closed** | Mất camera, mất NPU, model trả kết quả rác — tất cả đều phải dẫn tới chặn hành động, như khi mất mạng mà không có fallback cục bộ chạy được (Q-14) |
| **Năm nguyên tắc kế thừa gate (Phụ lục B.5)** | Không thay đổi, không thêm ngoại lệ cho gate có yếu tố thị giác |

### 2.2 Bài toán để mở, có chủ đích

**Ngữ nghĩa gate lượng giá trên bằng chứng thị giác chưa được giải.** Gate hiện lượng giá tiêu chí rời rạc (`bool` / `level` / `choice`) qua cây quyết định biên dịch lúc build (Q-9, Q-23). Mệnh đề *"camera thấy người trong vùng cấm"* chưa có cách diễn đạt trong gate, và việc bịa ra một cách diễn đạt vội vàng sẽ làm hỏng tính xác định của rule engine — thứ đang là khác biệt cạnh tranh số một.

**Ràng buộc tạm thời cho tới khi có RFC riêng về việc này:**

> Kết quả thị giác chỉ được dùng làm **thông tin ngữ cảnh**, không được làm căn cứ trực tiếp cho phán quyết actuator. Một agent muốn hành động dựa trên camera phải đi qua một `SystemOne` trả về kiểu `bool` / `level` / `choice` — tức là quy về đúng ba kiểu nguyên thủy mà gate đã biết lượng giá, và chịu cùng cơ chế fallback và ghi vết.

Ràng buộc này không cản trở các usecase ưu tiên của Giai đoạn 2: camera an toàn, nhận cử chỉ và giám sát đều diễn đạt được qua `bool` và `choice`.

### 2.3 Quyền riêng tư của dữ liệu hình ảnh

Vết ghi **không nhúng khung hình thô**. Mặc định chỉ lưu băm SHA-256 và kích thước; lưu ảnh thô phải bật tường minh. Đây là NFR-PRIV-01 và NFR-PRIV-03 áp nguyên xi, không có ngoại lệ cho thị giác. Camera đặt trong không gian riêng tư là rủi ro quyền riêng tư lớn hơn micro, nên quy tắc này chặt hơn chứ không lỏng hơn.

---

## 3. Giả định nguồn lực

Giai đoạn 2 **không được rút người khỏi Khối 4 (AURA)**. AURA là nguồn dòng tiền sớm duy nhất sau khi doanh thu inference bị bỏ ở v5.3, đồng thời là nguồn dữ liệu PF-3 cho chính thị giác.

Chỉ V5 (kỹ sư thị giác) là tuyển mới. Không có V5 thì danh sách target đã mở (V1a) vẫn có giá trị độc lập, vì cộng đồng port được bậc 3 mà không cần V5.

→ Vai trò và thời điểm cần người: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) §1.1; điều kiện vào của I15: §7.5.

---

## 4. Đường găng và phụ thuộc

→ Phụ thuộc giữa I11, I13 và I15–I18: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) §0.2 và §2.1. Vì sao `vision.in` tách khỏi RFC-0002: §5.

---

## 5. Khối V1a — Mở danh sách target

Khối này **không viết driver và không đụng TTFV**. Nó mở enum `target` ở hai lược đồ đã đóng băng và đưa bậc target vào mã lõi (`TARGET_TIERS`), theo RFC-0002. Pull request thực thi (PR2 của RFC-0002) là increment I11 (Q-40).

*Sửa 2026-09-23 sau review RFC-0002:* bản trước của khối này còn chốt nguyên thủy `vision.in` và trường vết ghi cho bằng chứng thị giác, viện dẫn PF-2 ("không chốt chỗ ngay thì sau này phải viết lại"). Lập luận đó không đứng: chính RFC-0002 §4 chứng minh các thay đổi này là **nới lỏng**, làm được trong `v1` vào bất kỳ lúc nào. Còn chốt hợp đồng tham số camera khi chưa có camera là đoán, và sửa về sau lại là siết chặt. Vì vậy phần thị giác chuyển sang Khối V1b (TSK-V1b-07, TSK-V1b-08). V1a giữ lại phần rẻ và chắc chắn: mở danh sách target, điều kiện của V2 và P1.

**Đòn bẩy OSS Khối V1a:** không có. Đây là công việc hợp đồng thuần túy trên tài sản lõi.

→ Task và tiêu chí ra: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) I11 (§7.1).

---

## 6. Khối V1b — Thị giác trên `linux`

Chứng minh thị giác chạy được trên `sim` và `linux` với chi phí phần cứng thấp.

**Đòn bẩy OSS Khối V1b:** GStreamer và V4L2 cho luồng khung hình · Ultralytics YOLO và ONNX Runtime cho mô hình · HailoRT và Edge TPU runtime cho NPU. Tiết kiệm ước tính 10 tuần.

→ Điều kiện vào (cổng PF-3: nhu cầu camera đo được từ khách hàng AURA thật), task và tiêu chí ra: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) I15 (§7.5).

---

## 7. Khối V2 — Thị giác trên `jetson`

Nâng `jetson` lên **target bậc 2**: đội lõi bảo trì, cam kết kiểm chứng trên miền phán quyết, không cam kết kiểm thử hằng đêm.

**Đòn bẩy OSS Khối V2:** JetPack và TensorRT · DeepStream cho pipeline đa camera. Tiết kiệm ước tính 5 tuần.

**Phạm vi bị loại tường minh:** tự phát triển SLAM, tránh vật cản, dẫn đường tự hành, drone *(ngoại lệ Q-34: tích hợp nguyên bản ROS 2 / Nav2, gate xét mọi lệnh tốc độ, trong increment I14 — NeuroEdge không tự viết thuật toán dẫn đường)*. Đây là những bài toán robot di động, không phải usecase consumer, và chúng kéo theo một tầng an toàn hoàn toàn khác.

→ Task và tiêu chí ra: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) I16 (§7.6).

---

## 8. Khối V3 — Đa phương thức

Hợp nhất thoại và thị giác trong một máy trạng thái.

Gate đa phương thức cần **một RFC riêng về ngữ nghĩa gate cho bằng chứng thị giác** (§2.2 của tài liệu này; TSK-V3-04). Không có RFC đó, V3 chỉ làm được phần hợp nhất nhận thức, không làm được gate đa phương thức.

→ Task và tiêu chí ra: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) I17 (§7.7).

---

## 9. Khối P1 và P2 — Nền tảng cho maker

### 9.1 Khối P1 — Bộ công cụ port cho cộng đồng

**Đây là khối quan trọng nhất về mặt chiến lược, và nó không phải việc port.** Đội lõi **không** tự đưa NeuroEdge lên STM32 hay RP2350 *(ngoại lệ Q-33: RP2350 làm node của robot phân tầng, trong increment I14; bản port bậc 3 chung vẫn là của cộng đồng)*. Đội lõi xuất bản thứ giúp người khác làm việc đó.

Phân biệt này quyết định việc khối có vượt được bộ lọc PF-1 hay không: đội lõi tự port là dàn trải nguồn lực và trượt PF-1; xuất bản bộ công cụ là việc làm một lần, phục vụ mọi bo mạch về sau.

→ Task và tiêu chí ra: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) I13 (§7.3).

### 9.2 Khối P2 — Hệ sinh thái thiết bị

**Hai ranh giới của P2:**

- **Không làm marketplace riêng.** Việc thương mại hóa trao đổi tài sản thuộc **Khối 5** (proposal §8.8) và chỉ kích hoạt sau cột mốc G1–G4. P2 chỉ làm phần miễn phí.
- **Chứng nhận không thu phí và không bảo chứng.** Chương trình chứng nhận **có thu phí** vẫn ở trạng thái Chặn tại PRD §14. NeuroEdge công bố kết quả bộ kiểm thử do bên đóng góp tự chạy, không đứng ra bảo đảm chất lượng bo mạch bên thứ ba — tránh nghĩa vụ pháp lý mà tổ chức chưa đủ quy trình để gánh.

→ Task: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) I18 (§7.8); MCP qua mạng (TSK-P2-04) và MCP cho MCU qua gateway (TSK-P2-05) ở I14 (§7.4).

---

## 10. Cột mốc xác thực

Bộ V-G1 đến V-G5 — ngưỡng chuẩn tắc ở proposal §12.4. Ba chỉ số then chốt và vì sao:

| # | Chỉ số | Vì sao then chốt |
|:---:|:---|:---|
| **V-G1** *(vế hai)* | Thiết bị vision thuộc đội có gói Fleet trả phí | Đây là chỗ Giai đoạn 2 dễ đi sai nhất. Usecase consumer thu hút người dùng, nhưng **người dùng cuối không trả tiền** — sau khi bỏ doanh thu inference, Fleet là dòng thu duy nhất và nó tính theo đội thiết bị doanh nghiệp. Một hộ gia đình hai camera không mua gói Fleet. Nếu tăng trưởng thiết bị không nối được vào fleet trả phí, Giai đoạn 2 tăng chi phí vận hành mà không tăng doanh thu |
| **V-G3** | Tỷ lệ thiết bị chạy tài sản của bên khác | Đo thứ không mua được bằng marketing: người dùng có tin nhau đủ để chạy mã của nhau không |
| **V-G5** | Adapter và bản port cộng đồng | Kiểm chứng trực tiếp mệnh đề nền tảng cho maker |

---

## 11. Rủi ro và giảm thiểu

| # | Rủi ro | Mức độ | Dấu hiệu sớm | Phương án ứng phó |
|:---:|:---|:---:|:---|:---|
| **1** | Thị giác làm chậm TTFV của luồng thoại | Trung bình | TTFV đo được vượt 10 phút ở bản có cài thị giác | Thị giác là gói tùy chọn, không nằm trong đường cài đặt mặc định. Tiêu chí ra 6 của I15 (`neuroedge-roadmap.md` §7.5) là cổng chặn |
| **2** | Phủ rộng phần cứng làm loãng chất lượng bậc 1 | Trung bình | Kiểm thử hằng đêm trên `esp32s3` thất bại thường xuyên hơn; hỗ trợ bậc 3 chiếm quá 10% thời gian đội lõi | Ứng phó chung: PRD R-7. Riêng Giai đoạn 2: tiêu chí ra 3 của I16 (`neuroedge-roadmap.md` §7.6) là cổng chặn |
| **3** | Không tuyển được V5 | Cao | Chưa có người khi I15 sắp mở | Dừng sau V1a. Danh sách target đã mở vẫn giữ nguyên giá trị cho cộng đồng port bậc 3 |
| **4** | Mô hình thị giác phi xác định làm loãng mệnh đề an toàn | Cao | Xuất hiện đề xuất cho gate lượng giá trực tiếp trên đầu ra model | Ràng buộc §2.2 của tài liệu này: kết quả thị giác phải quy về `bool` / `level` / `choice` trước khi tới gate. Rule engine giữ nguyên 100% xác định |
| **5** | Tăng người dùng mà không tăng doanh thu | Cao | V-G1 vế một đạt nhưng vế hai không đạt | Xem §10. Nếu sau I16 tỷ lệ này vẫn thấp, xem lại giả định consumer-first thay vì tiếp tục đổ nguồn lực |
| **6** | RFC-0002 bị bác | Trung bình | Phản biện tập trung vào việc thu hẹp ba bất biến kiểm thử theo bậc | V2 và P1 dừng; V1b không bị ảnh hưởng (nguyên thủy thị giác đi qua RFC riêng). Đây là lý do RFC-0002 phải đối chất trực diện với tuyên bố `v2` của RFC-0001, không né |

---

## 12. Cắt phạm vi

→ Thang cắt của I15–I18 và phần tuyệt đối không cắt (I11): [`neuroedge-roadmap.md`](neuroedge-roadmap.md) §9.3.

---

# Phụ lục

## Phụ lục A — Bảng mốc tổng hợp

→ Mốc, ngày dự báo và thẻ phát hành: [`neuroedge-roadmap.md`](neuroedge-roadmap.md) §0.2.

## Phụ lục B — Danh mục mua sắm

→ [`neuroedge-roadmap.md`](neuroedge-roadmap.md) Phụ lục B.

---

*Hết tài liệu*
