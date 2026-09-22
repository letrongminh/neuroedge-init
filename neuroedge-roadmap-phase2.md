# NeuroEdge — Roadmap Giai đoạn 2

## Perception thị giác và phủ rộng phần cứng (Tháng 9 – Tháng 24)

**Phiên bản:** 1.0

**Ngày lập:** 22 tháng 9, 2026

**Tài liệu nguồn:** `neuroedge-proposal.md` v5.4 §8.9 · `neuroedge-prd.md` v1.2 · `docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md`

**Phạm vi:** Khối V1a · V1b · V2 · V3 · P1 · P2

**Ngoài phạm vi:** Khối 4 (AURA thực địa) và Khối 5 (Marketplace) — chạy theo lộ trình riêng tại `neuroedge-roadmap.md` và proposal §8. Giai đoạn 2 **song song** với chúng, không thay thế.

---

## Mục lục

1. [Định vị và nguyên tắc](#1-định-vị-và-nguyên-tắc)
2. [Ranh giới với tầng an toàn](#2-ranh-giới-với-tầng-an-toàn)
3. [Giả định nguồn lực](#3-giả-định-nguồn-lực)
4. [Đường găng và phụ thuộc](#4-đường-găng-và-phụ-thuộc)
5. [Khối V1a — Đặt chỗ kiến trúc](#5-khối-v1a--đặt-chỗ-kiến-trúc)
6. [Khối V1b — Thị giác trên `linux`](#6-khối-v1b--thị-giác-trên-linux)
7. [Khối V2 — Thị giác trên `jetson`](#7-khối-v2--thị-giác-trên-jetson)
8. [Khối V3 — Đa phương thức](#8-khối-v3--đa-phương-thức)
9. [Khối P1 và P2 — Nền tảng cho maker](#9-khối-p1-và-p2--nền-tảng-cho-maker)
10. [Cột mốc xác thực](#10-cột-mốc-xác-thực)
11. [Rủi ro và giảm thiểu](#11-rủi-ro-và-giảm-thiểu)
12. [Thang cắt phạm vi](#12-thang-cắt-phạm-vi)

**Phụ lục**

- [A — Bảng mốc tổng hợp](#phụ-lục-a--bảng-mốc-tổng-hợp)
- [B — Danh mục mua sắm](#phụ-lục-b--danh-mục-mua-sắm)

---

## Quy ước tài liệu

| Ký hiệu | Ý nghĩa | Nguồn định nghĩa |
|:---|:---|:---|
| **§x.y** | Mục trong `neuroedge-proposal.md` | proposal |
| **§x.y của tài liệu này** | Mục nội bộ của tài liệu này | — |
| **FR-… · NFR-…** | Yêu cầu chức năng và phi chức năng | `neuroedge-prd.md` |
| **V-G1…V-G5** | Cột mốc xác thực Giai đoạn 2 | proposal §12.4 |
| **PF-1…PF-4** | Bộ lọc ưu tiên tính năng | proposal §2 |
| **TSK-V… · TSK-P…** | Mã hạng mục công việc, cấp phát trong tài liệu này | tài liệu này |

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

Mục này đứng trước mọi kế hoạch công việc vì nó là điều kiện để phần còn lại được phép tồn tại.

### 2.1 Ba thứ Giai đoạn 2 không được đụng

| Thành phần | Vì sao |
|:---|:---|
| **Gate engine và ngữ nghĩa phân giải** | Đây là tài sản lõi. Thị giác là đầu vào nhận thức (L2), không phải thẩm quyền phán quyết (L3) |
| **Cơ chế fail-closed** | Mất camera, mất NPU, model trả kết quả rác — tất cả đều phải dẫn tới chặn hành động, giống hệt mất mạng ở kiến trúc cloud-first |
| **Năm nguyên tắc kế thừa gate (Phụ lục B.5)** | Không thay đổi, không thêm ngoại lệ cho gate có yếu tố thị giác |

### 2.2 Bài toán để mở, có chủ đích

**Ngữ nghĩa gate lượng giá trên bằng chứng thị giác chưa được giải.** CEL hiện lượng giá giá trị cảm biến rời rạc. Mệnh đề *"camera thấy người trong vùng cấm"* chưa có cách diễn đạt trong gate, và việc bịa ra một cách diễn đạt vội vàng sẽ làm hỏng tính xác định của rule engine — thứ đang là khác biệt cạnh tranh số một.

**Ràng buộc tạm thời cho tới khi có RFC riêng về việc này:**

> Kết quả thị giác chỉ được dùng làm **thông tin ngữ cảnh**, không được làm căn cứ trực tiếp cho phán quyết actuator. Một agent muốn hành động dựa trên camera phải đi qua một `SystemOne` trả về kiểu `bool` / `level` / `choice` — tức là quy về đúng ba kiểu nguyên thủy mà gate đã biết lượng giá, và chịu cùng cơ chế fallback và ghi vết.

Ràng buộc này không cản trở các usecase ưu tiên của Giai đoạn 2: camera an toàn, nhận cử chỉ và giám sát đều diễn đạt được qua `bool` và `choice`.

### 2.3 Quyền riêng tư của dữ liệu hình ảnh

Vết ghi **không nhúng khung hình thô**. Mặc định chỉ lưu băm SHA-256 và kích thước; lưu ảnh thô phải bật tường minh. Đây là NFR-PRIV-01 và NFR-PRIV-03 áp nguyên xi, không có ngoại lệ cho thị giác. Camera đặt trong không gian riêng tư là rủi ro quyền riêng tư lớn hơn micro, nên quy tắc này chặt hơn chứ không lỏng hơn.

---

## 3. Giả định nguồn lực

Giai đoạn 2 **không được rút người khỏi Khối 4 (AURA)**. AURA là nguồn dòng tiền sớm duy nhất sau khi doanh thu inference bị bỏ ở v5.3, đồng thời là nguồn dữ liệu PF-3 cho chính thị giác.

| Vai trò | Trọng tâm trong Giai đoạn 2 | Cần từ |
|:---|:---|:---|
| **V1 — Kỹ sư lõi nền tảng** | RFC-0002, hợp đồng HAL thị giác, Action CI cho khung hình | Tháng 9 *(bán thời gian)* |
| **V5 — Kỹ sư thị giác máy tính** *(tuyển mới)* | Pipeline vision, tích hợp NPU, mô hình qua giao diện trừu tượng | Tháng 11 |
| **V3 — Kỹ sư trải nghiệm lập trình** | Bộ công cụ port cho cộng đồng, tài liệu, kho adapter | Tháng 14 *(bán thời gian)* |

**Chỉ một vai trò tuyển mới.** Nếu ngân sách không cho phép tuyển V5, Giai đoạn 2 dừng sau Khối V1a — phần đặt chỗ kiến trúc vẫn có giá trị độc lập vì nó chống được chi phí viết lại về sau.

---

## 4. Đường găng và phụ thuộc

```text
[ RFC-0002 được phê duyệt ]  ← chặn toàn bộ Giai đoạn 2
            │
            ▼
[ V1a: sửa lược đồ, HAL vision, trace vision ]  (Tháng 9–11)
            │
            ├──────────────────────────┐
            ▼                          ▼
[ V1b: vision trên linux ]      [ P1: bộ công cụ port ]
   (Tháng 11–16)                    (Tháng 16–20)
            │                          │
            ▼                          ▼
[ V2: vision trên jetson ]      [ P2: hệ sinh thái thiết bị ]
   (Tháng 16–20)                    (Tháng 20–24)
            │
            ▼
[ V3: đa phương thức ]  (Tháng 20–24)
   cần thêm: RFC ngữ nghĩa gate thị giác
```

| # | Mắt xích | Vì sao nằm trên đường găng |
|:---:|:---|:---|
| 1 | **RFC-0002 được phê duyệt** | Không có nó thì không sửa được lược đồ, không thêm được target lẫn nguyên thủy. Chặn tất cả |
| 2 | **Hợp đồng HAL thị giác** | Mọi thứ khác gọi vào nó. Sai ở đây là viết lại toàn bộ |
| 3 | **Action CI cho khung hình** | Điều kiện để thị giác có kiểm thử hồi quy; không có nó thì V1b không nghiệm thu được |

**Không nằm trên đường găng, làm song song:** tài liệu, kho adapter, giao diện `sim` cho camera ảo, danh mục mua sắm.

---

## 5. Khối V1a — Đặt chỗ kiến trúc

**Tháng 9–11.** Khối này **không viết driver và không đụng TTFV**. Nó chỉ chốt chỗ trong các hợp đồng đã đóng băng, trước khi chi phí thay đổi trở nên quá đắt.

Lý do làm sớm nằm ở bộ lọc PF-1→PF-4 của proposal §2: thị giác **trượt PF-1** (không rút ngắn thời gian nhận giá trị) nhưng **thắng PF-2** — nếu không chốt chỗ trong lược đồ ngay, việc bổ sung sau 12 tháng sẽ phải viết lại hợp đồng HAL và lược đồ vết ghi, tức đúng định nghĩa "không bổ sung muộn được". Theo §2, thỏa PF-1 **hoặc** PF-2 là đủ để làm ngay.

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-V1a-01** | Hoàn thiện và bảo vệ RFC-0002 qua thảo luận | FR-TGT-08, FR-HAL-01 | V1 | ⏳ Chưa bắt đầu | `docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md` |
| **TSK-V1a-02** | Mở enum `target` ở hai lược đồ theo phân tầng bậc | FR-TGT-08 | V1 | ⏳ Chưa bắt đầu | `schemas/board.v1.json` · `schemas/trace.v1.json` |
| **TSK-V1a-03** | Thêm `vision_in` vào `capabilities`, là nguyên thủy **tùy chọn theo bo mạch** | FR-HAL-01, FR-HAL-04 | V1 | ⏳ Chưa bắt đầu | `schemas/board.v1.json` · `python/neuroedge/hal/board.py` |
| **TSK-V1a-04** | Nới hai bất biến kiểm thử theo RFC-0002 §5a và §5b | FR-HAL-04 | V1 | ⏳ Chưa bắt đầu | `python/tests/test_boards.py` |
| **TSK-V1a-05** | Mở trường `input` của vết ghi cho `vision_ref` (băm + kích thước, không ảnh thô) | NFR-PRIV-01, NFR-PRIV-03 | V1 | ⏳ Chưa bắt đầu | `neuroedge-proposal.md` Phụ lục C.1 · `python/neuroedge/trace.py` |
| **TSK-V1a-06** | Cập nhật corpus phản chứng: `unknown_target.json` phải dùng chuỗi vẫn nằm ngoài enum mới | FR-TRC-08 | V1 | ⏳ Chưa bắt đầu | `fixtures/traces/invalid/` · `fixtures/traces/expected_errors.yaml` |

**Đòn bẩy OSS Khối V1a:** không có. Đây là công việc hợp đồng thuần túy trên tài sản lõi.

**Tiêu chí ra Khối V1a:**

- [ ] **Tiêu chí 1:** RFC-0002 ở trạng thái ✅ Đã chấp thuận, có chữ ký kỹ thuật trưởng.
- [ ] **Tiêu chí 2:** Một `board.toml` khai `target = "jetson"` và `vision_in` thẩm định qua, đồng thời một tệp khai target bịa đặt vẫn bị từ chối kèm thông báo đúng.
- [ ] **Tiêu chí 3:** Ba bo mạch bậc 1 vẫn khai đủ năm nguyên thủy; `neuroedge verify --targets sim,linux,esp32s3` vẫn đạt 100%.
- [ ] **Tiêu chí 4:** Agent yêu cầu `vision.in` bị **từ chối lúc build** trên bo mạch không khai nó, thông báo nêu đủ ba thành phần (FR-HAL-05).
- [ ] **Tiêu chí 5:** Vết ghi có `vision_ref` thẩm định qua và `neuroedge replay` chạy được; mặc định không chứa ảnh thô.

---

## 6. Khối V1b — Thị giác trên `linux`

**Tháng 11–16.** Chứng minh thị giác chạy được trên `sim` và `linux` với chi phí phần cứng thấp.

**Điều kiện kích hoạt:** có **nhu cầu camera đo được từ khách hàng AURA thật** — ít nhất hai khách hàng nêu yêu cầu cụ thể về giám sát hoặc điều khiển bằng cử chỉ. Đây là cổng PF-3; không đạt thì Giai đoạn 2 dừng sau V1a.

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-V1b-01** | Hiện thực `vision.in` cho `linux`: luồng khung hình, độ phân giải, FPS | FR-HAL-01 | V5 | ⏳ Chưa bắt đầu | `targets/linux/vision/` |
| **TSK-V1b-02** | Camera ảo trong `sim`: phát lại chuỗi ảnh, giữ tương đương với phần cứng thật | FR-TGT-01, FR-TGT-06 | V5 | ⏳ Chưa bắt đầu | `python/neuroedge/sim/vision/` |
| **TSK-V1b-03** | Giao diện trừu tượng mô hình thị giác, đổi model bằng cấu hình | FR-MDL-04, FR-MDL-07 | V5 | ⏳ Chưa bắt đầu | `python/neuroedge/perception/vision/` |
| **TSK-V1b-04** | Action CI cho khung hình: record, replay, assert trên chuỗi phán quyết | FR-CI-01→04 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/testing/vision.py` |
| **TSK-V1b-05** | Tích hợp NPU rời (Hailo-8, Coral) sau giao diện trừu tượng | FR-MDL-04 | V5 | ⏳ Chưa bắt đầu | `python/neuroedge/perception/vision/accel/` |
| **TSK-V1b-06** | Ba gate mẫu có yếu tố thị giác, tuân thủ ràng buộc §2.2 của tài liệu này | FR-GATE-03 | V1 + V5 | ⏳ Chưa bắt đầu | `gates/vision/` |

**Đòn bẩy OSS Khối V1b:** GStreamer và V4L2 cho luồng khung hình · Ultralytics YOLO và ONNX Runtime cho mô hình · HailoRT và Edge TPU runtime cho NPU. Tiết kiệm ước tính 10 tuần, phần lớn nằm trên đường găng.

**Tiêu chí ra Khối V1b:**

- [ ] **Tiêu chí 1:** Agent mẫu nhận diện người trong vùng cấm chạy trên `sim` và `linux`, cùng một tệp mã nguồn.
- [ ] **Tiêu chí 2:** `neuroedge verify --targets sim,linux` đạt 100% trên kịch bản **có thị giác**.
- [ ] **Tiêu chí 3:** Mất camera giữa phiên → hành động bị chặn với lý do fail-closed, không treo.
- [ ] **Tiêu chí 4:** Đổi mô hình thị giác chỉ bằng cấu hình, không sửa mã agent và không sửa gate.
- [ ] **Tiêu chí 5:** Vết ghi thị giác mặc định không chứa ảnh thô; bật lưu thô phải khai tường minh.
- [ ] **Tiêu chí 6:** TTFV của luồng thoại **vẫn dưới 10 phút** — thị giác không được làm chậm trải nghiệm đầu tiên.

---

## 7. Khối V2 — Thị giác trên `jetson`

**Tháng 16–20.** Nâng `jetson` lên **target bậc 2**: đội lõi bảo trì, cam kết kiểm chứng trên miền phán quyết, không cam kết kiểm thử hằng đêm.

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-V2-01** | Port HAL lên Jetson Orin qua JetPack | FR-TGT-08, FR-HAL-01 | V5 | ⏳ Chưa bắt đầu | `targets/jetson/hal/` |
| **TSK-V2-02** | Đường dẫn thị giác tăng tốc GPU, giữ nguyên giao diện trừu tượng | FR-MDL-04 | V5 | ⏳ Chưa bắt đầu | `targets/jetson/vision/` |
| **TSK-V2-03** | `neuroedge verify` cho `jetson` trên miền phán quyết | FR-CI-07, FR-TGT-08 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/cli/verify.py` |
| **TSK-V2-04** | Profile bo mạch `jetson-orin-nano` | FR-HAL-02 | V5 | ⏳ Chưa bắt đầu | `boards/jetson-orin-nano.toml` |

**Đòn bẩy OSS Khối V2:** JetPack và TensorRT · DeepStream cho pipeline đa camera. Tiết kiệm ước tính 5 tuần.

**Phạm vi bị loại tường minh:** SLAM, tránh vật cản, dẫn đường tự hành, drone. Đây là những bài toán robot di động, không phải usecase consumer, và chúng kéo theo một tầng an toàn hoàn toàn khác.

**Tiêu chí ra Khối V2:**

- [ ] **Tiêu chí 1:** Cùng một agent thị giác chạy không sửa trên `linux` và `jetson`.
- [ ] **Tiêu chí 2:** `neuroedge verify` đạt 100% trên miền phán quyết giữa `linux` và `jetson`.
- [ ] **Tiêu chí 3:** Ngưỡng chất lượng của target bậc 1 **không suy giảm** — kiểm thử hằng đêm trên `esp32s3` vẫn xanh suốt khối.

---

## 8. Khối V3 — Đa phương thức

**Tháng 20–24.** Hợp nhất thoại và thị giác trong một máy trạng thái.

**Điều kiện kích hoạt bổ sung:** cần **một RFC riêng về ngữ nghĩa gate cho bằng chứng thị giác** được phê duyệt (§2.2 của tài liệu này). Không có nó, V3 chỉ làm được phần hợp nhất nhận thức, không làm được gate đa phương thức.

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-V3-01** | Hợp nhất thoại, thị giác và cảm biến vào một máy trạng thái | FR-PER-01→05 | V1 + V5 | ⏳ Chưa bắt đầu | `python/neuroedge/perception/fusion/` |
| **TSK-V3-02** | Mở rộng bộ vector tuân thủ cho luồng đa phương thức | FR-CI-07 | V1 | ⏳ Chưa bắt đầu | `fixtures/compliance/multimodal/` |
| **TSK-V3-03** | Gate đa phương thức *(phụ thuộc RFC ngữ nghĩa gate thị giác)* | FR-GATE-03 | V1 | ⏳ Chưa bắt đầu | `schemas/gate.v2.json` *(nếu RFC yêu cầu tăng phiên bản)* |

**Tiêu chí ra Khối V3:**

- [ ] **Tiêu chí 1:** Một agent phản ứng đúng khi lời nói và hình ảnh mâu thuẫn nhau, hành vi được đặc tả trước chứ không phát sinh.
- [ ] **Tiêu chí 2:** Mất một trong hai phương thức → suy giảm có kiểm soát, không chặn toàn bộ và không hành động sai.
- [ ] **Tiêu chí 3:** Máy trạng thái hợp nhất vượt toàn bộ bộ vector tuân thủ cũ, không hồi quy luồng thoại.

---

## 9. Khối P1 và P2 — Nền tảng cho maker

### 9.1 Khối P1 — Bộ công cụ port cho cộng đồng (Tháng 16–20)

**Đây là khối quan trọng nhất về mặt chiến lược, và nó không phải việc port.** Đội lõi **không** tự đưa NeuroEdge lên STM32 hay RP2350. Đội lõi xuất bản thứ giúp người khác làm việc đó.

Phân biệt này quyết định việc khối có vượt được bộ lọc PF-1 hay không: đội lõi tự port là dàn trải nguồn lực và trượt PF-1; xuất bản bộ công cụ là việc làm một lần, phục vụ mọi bo mạch về sau.

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-P1-01** | Bộ vector tuân thủ độc lập ngôn ngữ, đóng gói chạy được ngoài repo | FR-GOV-02 | V1 | ⏳ Chưa bắt đầu | `fixtures/compliance/portable/` |
| **TSK-P1-02** | Hướng dẫn port HAL: hợp đồng tối thiểu, cạm bẫy, cách tự kiểm chứng | FR-DX-05 | V3 | ⏳ Chưa bắt đầu | `docs/porting/` |
| **TSK-P1-03** | Khung port mẫu cho một vi điều khiển không phải ESP32 | FR-TGT-08 | V3 | ⏳ Chưa bắt đầu | `targets/_template/` |
| **TSK-P1-04** | Quy trình công nhận bậc 3: bên đóng góp tự chạy và công bố kết quả | FR-TGT-08 | V3 | ⏳ Chưa bắt đầu | `docs/porting/tier3.md` |

**Tiêu chí ra Khối P1:**

- [ ] **Tiêu chí 1:** Một kỹ sư ngoài đội hoàn thành một bản port bậc 3 **chỉ dựa vào tài liệu công khai**, không hỏi đội lõi.
- [ ] **Tiêu chí 2:** Bản port đó vượt bộ vector tuân thủ, kết quả kiểm chứng lại được bởi bên thứ ba.
- [ ] **Tiêu chí 3:** Thời gian đội lõi bỏ ra hỗ trợ bản port đầu tiên dưới 8 giờ.

### 9.2 Khối P2 — Hệ sinh thái thiết bị (Tháng 20–24)

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-P2-01** | Kho adapter và HAL port do cộng đồng đóng góp, dùng chung hạ tầng Registry | FR-REG-08 | V3 | ⏳ Chưa bắt đầu | `services/registry/ports.py` |
| **TSK-P2-02** | Hiển thị trạng thái tuân thủ của adapter đang chạy trên Fleet Dashboard | FR-FLT-03 | V3 | ⏳ Chưa bắt đầu | `services/fleet/compliance_view.py` |
| **TSK-P2-03** | Chứng nhận phần cứng **miễn phí, tự kiểm chứng** — công bố kết quả, không bảo chứng | FR-GOV-02 | V3 | ⏳ Chưa bắt đầu | `docs/porting/certification.md` |

**Hai ranh giới của P2:**

- **Không làm marketplace riêng.** Việc thương mại hóa trao đổi tài sản thuộc **Khối 5** (proposal §8.8, Tháng 18+) và chỉ kích hoạt sau cột mốc G1–G4. P2 chỉ làm phần miễn phí.
- **Chứng nhận không thu phí và không bảo chứng.** Chương trình chứng nhận **có thu phí** vẫn ở trạng thái Chặn tại PRD §14. NeuroEdge công bố kết quả bộ kiểm thử do bên đóng góp tự chạy, không đứng ra bảo đảm chất lượng bo mạch bên thứ ba — tránh nghĩa vụ pháp lý mà tổ chức chưa đủ quy trình để gánh.

---

## 10. Cột mốc xác thực

Bộ V-G1 đến V-G5, đặc tả đầy đủ tại proposal §12.4. Ba chỉ số then chốt:

| # | Chỉ số | Ngưỡng | Vì sao then chốt |
|:---:|:---|:---|:---|
| **V-G1** *(vế hai)* | Thiết bị vision thuộc đội có gói Fleet trả phí | **≥ 500** | Đây là chỗ Giai đoạn 2 dễ đi sai nhất. Usecase consumer thu hút người dùng, nhưng **người dùng cuối không trả tiền** — sau khi bỏ doanh thu inference, Fleet là dòng thu duy nhất và nó tính theo đội thiết bị doanh nghiệp. Một hộ gia đình hai camera không mua gói Fleet. Nếu tăng trưởng thiết bị không nối được vào fleet trả phí, Giai đoạn 2 tăng chi phí vận hành mà không tăng doanh thu |
| **V-G3** | Tỷ lệ thiết bị chạy tài sản của bên khác | **> 25%** | Đo thứ không mua được bằng marketing: người dùng có tin nhau đủ để chạy mã của nhau không |
| **V-G5** | Adapter và bản port cộng đồng | **≥ 10**, trong đó ≥ 3 bản port bậc 3 | Kiểm chứng trực tiếp mệnh đề nền tảng cho maker |

---

## 11. Rủi ro và giảm thiểu

| # | Rủi ro | Mức độ | Dấu hiệu sớm | Phương án ứng phó |
|:---:|:---|:---:|:---|:---|
| **1** | Thị giác làm chậm TTFV của luồng thoại | Trung bình | TTFV đo được vượt 10 phút ở bản có cài thị giác | Thị giác là gói tùy chọn, không nằm trong đường cài đặt mặc định. Tiêu chí ra V1b số 6 là cổng chặn |
| **2** | Phủ rộng phần cứng làm loãng chất lượng bậc 1 | Trung bình | Kiểm thử hằng đêm trên `esp32s3` thất bại thường xuyên hơn; hỗ trợ bậc 3 chiếm quá 10% thời gian đội lõi | Phân tầng FR-TGT-08. Đội lõi chỉ cam kết bậc 1 và bậc 2. Tiêu chí ra V2 số 3 là cổng chặn *(đồng bộ PRD R-7)* |
| **3** | Không tuyển được V5 | Cao | Quá Tháng 11 chưa có người | Dừng sau V1a. Phần đặt chỗ kiến trúc vẫn giữ nguyên giá trị vì nó chống chi phí viết lại |
| **4** | Mô hình thị giác phi xác định làm loãng mệnh đề an toàn | Cao | Xuất hiện đề xuất cho gate lượng giá trực tiếp trên đầu ra model | Ràng buộc §2.2 của tài liệu này: kết quả thị giác phải quy về `bool` / `level` / `choice` trước khi tới gate. Rule engine giữ nguyên 100% xác định |
| **5** | Tăng người dùng mà không tăng doanh thu | Cao | V-G1 vế một đạt nhưng vế hai không đạt | Xem §10. Nếu sau Tháng 20 tỷ lệ này vẫn thấp, xem lại giả định consumer-first thay vì tiếp tục đổ nguồn lực |
| **6** | RFC-0002 bị bác | Trung bình | Phản biện tập trung vào việc nới hai bất biến kiểm thử | Toàn bộ Giai đoạn 2 dừng. Đây là lý do RFC-0002 phải đối chất trực diện với tuyên bố `v2` của RFC-0001, không né |

---

## 12. Thang cắt phạm vi

Cắt theo thứ tự này khi trượt tiến độ. Bậc càng cao cắt càng sớm.

| Bậc | Hạng mục cắt | Hệ quả chấp nhận được |
|:---:|:---|:---|
| **1** | Khối V3 đa phương thức | Thoại và thị giác vẫn chạy độc lập, chỉ không hợp nhất |
| **2** | Khối V2 trên Jetson | Thị giác vẫn có trên `linux` với NPU rời, chi phí thấp hơn |
| **3** | Khối P2 hệ sinh thái | Cộng đồng vẫn port được, chỉ không có kho tập trung |
| **4** | Khối P1 bộ công cụ port | Mất mệnh đề nền tảng cho maker. Cắt tới đây là đã cắt vào phần chiến lược |
| **5** | Khối V1b hiện thực thị giác | Giai đoạn 2 chỉ còn phần đặt chỗ kiến trúc |

**Tuyệt đối không cắt:** Khối V1a. Nó là thứ duy nhất trong Giai đoạn 2 có tính chất PF-2 — không làm bây giờ thì sau này phải viết lại. Mọi hạng mục khác đều hoãn được mà không phát sinh nợ kiến trúc.

---

# Phụ lục

## Phụ lục A — Bảng mốc tổng hợp

| Mốc | Thời điểm | Nội dung | Cổng nghiệm thu |
|:---|:---|:---|:---|
| RFC-0002 phê duyệt | Tháng 9  | Mở enum target, nguyên thủy `vision.in` | Chữ ký kỹ thuật trưởng |
| **Kết thúc V1a**   | **Tháng 11** | Lược đồ và hợp đồng HAL đã mở | Tiêu chí ra Khối V1a |
| Thị giác trên `linux` | Tháng 16 | HAL vision, Action CI vision, NPU | Tiêu chí ra Khối V1b |
| Bộ công cụ port     | Tháng 20 | Cộng đồng tự port được | Tiêu chí ra Khối P1 |
| Thị giác trên `jetson` | Tháng 20 | Target bậc 2 | Tiêu chí ra Khối V2 |
| **Kết thúc Giai đoạn 2** | **Tháng 24** | Đa phương thức, hệ sinh thái thiết bị | **Toàn bộ V-G1 đến V-G5** |

## Phụ lục B — Danh mục mua sắm

| Hạng mục | Số lượng | Cần trước | Ghi chú |
|:---|:---:|:---:|:---|
| Camera USB và CSI | 4 | Tháng 11 | Nguồn khung hình cho `vision.in`; mua hai loại để kiểm chứng tính di động |
| NPU Hailo-8 hoặc Hailo-8L | 2 | Tháng 11 | Gắn ngoài cho Raspberry Pi 5 |
| Google Coral Edge TPU | 2 | Tháng 12 | Phương án NPU chi phí thấp hơn, kiểm chứng giao diện trừu tượng |
| Jetson Orin Nano | 2 | Tháng 16 | Target `jetson` bậc 2. **Chỉ mua sau khi V1b đạt tiêu chí ra** |
| Bo mạch STM32 và RP2350 | 2 mỗi loại | Tháng 16 | Phục vụ khung port mẫu của P1; không phải để đội lõi tự port |

---

*Hết tài liệu*
