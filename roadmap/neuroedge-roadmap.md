# NeuroEdge — Roadmap thực thi

## Từ lõi `sim` tới v1.0 và Developer Beta

**Phiên bản:** 2.0


**Ngày lập:** 21 tháng 9, 2026 · **Cập nhật:** 11 tháng 10, 2026 (thứ tự theo Q-72: I2d, I2e trước cổng nhu cầu 8 tuần) · lịch sử thay đổi: `CHANGELOG.md`

**Tài liệu nguồn:** `neuroedge-prd.md` · [`TODOS.md`](../TODOS.md)

**Phạm vi:** increment từ **I0** tới **I18** — MVP (v1.0), Developer Beta, tầng dịch vụ v1.1 và các hướng mở rộng (§0.5). Nơi duy nhất ghi trạng thái task, tiêu chí ra, phụ thuộc và ngày dự báo (Q-39).

**Ghi chú thiết kế:** `docs/spec/lab_mcp.md` (Lab, I4a, I5a; Q-71) · `docs/architecture/vi/15-target-architecture.md` §4.4 (thị giác I2a, I3a; I13, I16–I18) · `docs/architecture/vi/16-ecosystem-landscape.md` §4 (nền tảng mở, I2c) · `docs/architecture/vi/15-target-architecture.md` §4.3 và [`draft-rfc-node-giao-thuc-dieu-phoi.md`](../docs/rfc/draft-rfc-node-giao-thuc-dieu-phoi.md) (I14)

**Ngoài roadmap:** Khối 4 (AURA thực địa) · Khối 5 (Marketplace thu phí; Hub tối thiểu ở I2e — Q-72) — §8.1

---

## Mục lục

0. [Bảng theo dõi tiến độ & Nhật ký bàn giao](#0-bảng-theo-dõi-tiến-độ--nhật-ký-bàn-giao-live-execution--handoff-dashboard)
1. [Giả định nguồn lực](#1-giả-định-nguồn-lực)
2. [Đường găng, phụ thuộc và luật chống lệch](#2-đường-găng-phụ-thuộc-và-luật-chống-lệch)
3. [Chiến lược tái sử dụng mã nguồn mở](#3-chiến-lược-tái-sử-dụng-mã-nguồn-mở)
4. [Increment tới v1.0 = MVP (I0–I7)](#4-increment-tới-v10--mvp-i0i7)
5. [Developer Beta và điểm rẽ (I8)](#5-developer-beta-và-điểm-rẽ-i8)
6. [Đã bỏ khỏi roadmap (Q-77)](#6-đã-bỏ-khỏi-roadmap-q-77)
7. [Hướng mở rộng sau Beta](#7-hướng-mở-rộng-sau-beta)
8. [Ngoài roadmap](#8-ngoài-roadmap)
9. [Thang cắt phạm vi](#9-thang-cắt-phạm-vi)
10. [Lịch chốt quyết định](#10-lịch-chốt-quyết-định)
11. [Nhịp vận hành](#11-nhịp-vận-hành)
12. [Chỉ báo sớm và ngưỡng can thiệp](#12-chỉ-báo-sớm-và-ngưỡng-can-thiệp)

**Phụ lục**

- [B — Danh mục mua sắm và hạ tầng](#phụ-lục-b--danh-mục-mua-sắm-và-hạ-tầng)
- [C — Bố cục kho mã nguồn](#phụ-lục-c--bố-cục-kho-mã-nguồn)
- [D — Giao thức truyền dẫn](#phụ-lục-d--giao-thức-truyền-dẫn)

---

## Quy ước tài liệu

Mọi mã và ký hiệu dùng trong tài liệu này (`I0`–`I18`, `TSK-*`, `A1`–`C8`, `TR-N`, `Q-N`, `RB-N`, `V1`–`V7`, `§x.y`…) được giải mã ở **[`docs/user/thuat-ngu.md`](../docs/user/thuat-ngu.md)** — nơi duy nhất, kèm chỗ định nghĩa đầy đủ. Thời gian đo bằng increment và ngày tuyệt đối; tên sprint (Sprint 1–6) và khối (Khối 1a, 1b, 2, 3) chỉ còn là tên lịch sử (Q-39).

## 0. Bảng theo dõi tiến độ & Nhật ký bàn giao (Live Execution & Handoff Dashboard)

> **Mục đích:** Cung cấp điểm nhìn tập trung duy nhất về trạng thái thời gian thực của toàn bộ dự án. Mọi phiên làm việc (session), kỹ sư hoặc AI Agent khi nhận bàn giao chỉ cần đọc mục này là nắm được ngay: *Hệ thống đang ở đâu, vừa hoàn thành gì, ai đang làm gì, và bước hành động kế tiếp là gì.*

### 0.1 Thanh trạng thái điều hành (Executive Status Bar)

| Chỉ số | Trạng thái hiện hành | Ghi chú & Liên kết |
|:---|:---|:---|
| **Pha đang thực thi** | 🟡 **Phase MVP (§0.5)**, thứ tự theo Q-72 — I2d rồi I2e (NeuroEdge Blueprint bể cá đi trọn ba vòng trên giả lập) trước cổng nhu cầu 8 tuần; phần còn lại của I1, I2a, I2c làm xen; đợt thử đối tác (Q-70) song song; thoại (I4, I5) và Studio tạm dừng, không cắt | Increment và ngày dự báo: §0.2 |
| **Increment đang mở** | 🟡 **I2d — Nhiệm vụ và agent vận hành** (Q-72) — task bắt đầu khi Bước 0 (đồng bộ tài liệu theo Q-72) xong | I1 còn TSK-I1-02 (kích hoạt lại cho cổng 8 tuần) và Studio (tạm dừng) · I0 đã xong 42 / 42 · chi tiết §0.2 |
| **Cột mốc tiếp theo** | **Cổng nhu cầu 8 tuần (Q-72, B6–B8)** — ≥ 3 người ngoài tự cài Blueprint và chạy được, ≥ 1 người chạy liên tục 2 tuần trên G2 hoặc G3, ≥ 1 maker muốn bán (PRD §11.2) | Ngày: giả định ở §0.2 · nhánh theo kết quả: §5.6 · wheel giao trực tiếp, chưa lên PyPI (Q-39) |
| **Lần cập nhật cuối** | **2026-10-13** | Phiên 2026-10-13: Q-78 — bộ não là NeuroClaw (fork cứng PicoClaw, `letrongminh/neuroclaw`, MIT); demo chat đèn và cửa qua NeuroEdge Cloud chạy đủ sáu màn qua Telegram (OrbStack làm cloud; `mcp serve --http --ui`); VPS và video hoãn (`TODOS.md` #69). Phiên 2026-10-12: Q-77 bỏ thoại, Lab, mở danh sách target và mọi increment sau Beta khỏi roadmap (§6). Q-76 thêm bộ não NeuroEdge (TSK-I2d-22 → I2d-24) và cloud mỗi người một instance (TSK-I2f-07 → I2f-09); §3.11 port tối đa theo task. Q-75 thêm 4 task I3a (liên kết Pi ↔ ESP32, bo ESP32-S3 phổ thông, Arduino) và TSK-I2e-14 (khung dự án nhiều chip). Phiên 2026-10-11: đồng bộ roadmap theo Q-72 — thêm I2d (35 task, gồm 2 task Q-73) và I2e (15 task, gồm 2 task hộp dễ cài của Q-74); I2f có điều kiện (Q-74); thoại (I4, I5), Studio, N4, N5b, V1a, TSK-I2c-13, I2c-17 tạm dừng; ngày I3 → I8 đặt lại sau cổng 8 tuần (R5). Chi tiết: `CHANGELOG.md` |
| **Trạng thái CI Lõi** | ✅ **PASS 4885/4885 · SKIP 0** | `python/tests/` 126 bộ test; `tests_linux/` 119/119 trên kernel; `ui-golden` 66 ảnh; `ota-rollback` pha a–g; security scanners |
| **Chặn ngoài tầm kỹ thuật** | 🟡 **2 hạng mục chặn** | 🔴 Box-3 và RPi 5 chưa về (TSK-S1-10 → I3; TSK-I2-01) · bo camera đã chọn là M5Stack CoreS3 nhưng chưa đặt (Q-61, TSK-I3a-01). Không chặn I2d, I2e: giả lập trước, phần cứng thật mua sau (Q-72) |
| **Hoãn có chủ ý** | 📋 [`TODOS.md`](../TODOS.md) | Mỗi mục kèm mốc kích hoạt · cổng nhu cầu khôi phục bởi Q-72 (đảo Q-56); câu hỏi kinh doanh mở (`TODOS.md` #19) rà lại ở cổng 8 tuần |

---

### 0.2 Bảng increment (Increment Matrix)

Mỗi dòng là một increment: một năng lực người dùng thấy được, kết thúc bằng một thẻ phát hành và một tín hiệu đo (Q-39). **Dự báo** là ngày duy nhất của increment; nó chỉ đổi trong cùng PR với bằng chứng làm nó đổi, và kéo theo mọi increment phụ thuộc (§2.4, R5). **Phụ thuộc** chỉ trỏ về increment số nhỏ hơn. Trước I6, mọi bản phát hành là nội bộ; ngoại lệ duy nhất là wheel giao trực tiếp, không lên index nào — cho một đội đối tác (Q-70) và cho người thử NeuroEdge Blueprint ở I2e (Q-72).

| Mốc | Increment | Dự báo | Năng lực | Tiến độ | Trạng thái | Phụ thuộc | Phát hành |
|:---:|:---|:---:|:---|:---:|:---|:---|:---|
| **0.x nội bộ** | **I0 — Lõi hợp đồng trên `sim`** | ✅ 2026-09-24 | Gate có kiểu và phiên bản (lint, resolve, kế thừa, tham số, `confirms`), `sim` + web UI, Action CI, MCP, System 2 qua LiteLLM, `linux` replay trên gpio-sim; walker C, sổ token và vết ghi UART trên QEMU | **42 / 42** | ✅ Xong | — | lịch sử |
|  | **I1 — Preview nội bộ trên `sim`** | 2026-11-15 | Người ngoài đội cài từ wheel nội bộ và chạy agent có gate trong dưới 10 phút, không cần phần cứng | **4 / 6** | 🟡 Đang làm — TSK-I1-02 tạm hoãn (phát triển nội bộ) | I0 | tag `v0.1.0` (nội bộ) |
|  | **I2 — `linux` ngang `sim`** | 2026-11-29 | `run`, `record`, `mcp serve --target linux`; cảm biến và màn hình trên `linux`; nightly trên RPi 5 | **3 / 4** | 🟡 Phiên tương tác, cảm biến, màn hình xong trên gpio-sim + i2c-stub; nightly RPi 5 còn lại | I1 | tag `v0.2.0` (nội bộ) |
|  | **I2a — Nguyên thủy mở rộng trên `sim` và `linux`** | 2026-12-06 | Bốn gói: cảm biến (`digital.in`, I2C chỉ đọc, `analog.in`, gate so ngưỡng số), điều khiển mịn (PWM), thị giác (`vision.in`), chuyển động (`motion.*`); sáu RFC; `sim-rpi5` | **22 / 27** | 🟡 Sáu RFC đã chấp thuận; tiêu chí số và `NETR` v2; `board.v1` khai đủ nguyên thủy mở rộng, `sim-rpi5`; phong bì an toàn, `digital.in`, I2C chỉ đọc, `analog.in`, thị giác (camera ảo, V4L2, mô hình, vết ghi, gate mẫu) xong trên `sim` và trên kernel (job `linux-hal`, CI run 37153005998: gpio-sim, `i2c-stub`, `vivid`; `verify --targets sim,linux` replay corpus cảm biến và thị giác); PWM và `motion.*` xong trên `sim`, dây `enable` xanh trên gpio-sim. **Còn:** `verify` chưa phát lại agent `fan-pwm` và `rover` (I2a tiêu chí 3); camera mất giữa phiên trên kernel (tiêu chí 5); kênh PWM và cơ cấu thật; golden suy luận thị giác; ô `esp32s3` của bảng phủ (TSK-I3a-01) | I2 | tag `v0.2.1` (nội bộ) |
|  | **I2b — Kit mẫu và dựng nhanh** | 2026-12-20 | Năm kit phần cứng (BOM, sơ đồ đấu dây, gate khoá), thư viện gate khởi đầu, `neuroedge add` | **4 / 4** | 🟡 Năm kit, thư viện gate, `neuroedge add` xong (tiêu chí 1, 3, 4); còn đo TTFV trên người (tiêu chí 2) và dựng kit trên phần cứng thật | I2a | tag `v0.2.2` (nội bộ) |
|  | **I2c — Nền tảng mở** | 2026-12-27 | Bên thứ ba tự nối NeuroEdge với sản phẩm mới bằng vài lệnh, không sửa lõi: lõi dùng độc lập (`neuroedge.guard`), Extension SDK sáu loại điểm cắm có bộ test tuân thủ, `proxy mcp`/`proxy http`, cơ cấu từ xa, index cộng đồng; mở danh sách target (RFC-0002) (Q-67) | **11 / 20** | 🟡 Q-67, thiết kế, giấy phép corpus xong; RFC-0002, RFC-0016 → RFC-0018 đã ký (Q-68); `neuroedge.guard` (TSK-I2c-07), `proxy mcp` + `guard init --mcp` (TSK-I2c-14), `proxy http` (TSK-I2c-15), cơ cấu từ xa + plugin Home Assistant (TSK-I2c-16), bộ tài liệu đợt thử đối tác (TSK-I2c-19) và nửa (a) của RFC-0017 xong; đợt thử với đối tác đi ra từ đây (Q-70) ; mở danh sách target và hai task tạm dừng đã bỏ theo Q-77 (§6) | I2b | tag `v0.2.3` (nội bộ) · wheel cho một đội đối tác — thử riêng, không chờ bo mạch (Q-70) |
|  | **I2d — Nhiệm vụ và agent vận hành** | 2026-11-11 | Giao nhiệm vụ cho thiết bị bằng lời: hợp đồng nhiệm vụ biên dịch xuống gate và phong bì, từ chối mâu thuẫn trước khi duyệt; agent vận hành chạy 24/7 trên máy nhà (runtime tin cậy + LLM worker không tin cậy, BYOK), bộ phát hiện tất định trước LLM, trần chi phí LLM; bộ não NeuroEdge (worker kiểu PicoClaw, Q-76) nói chuyện với runtime qua MCP; báo và xin duyệt qua Telegram bằng bản ghi duyệt; dữ liệu chỉ ra đích đã khai; vết ghi theo đoạn; an toàn có điều kiện (`safe_state` đối xứng); giả lập G1, G2; Lab vòng ① cho nhiệm vụ (Q-72) | **0 / 38** | 🟡 Mở — Bước 0 (đồng bộ tài liệu theo Q-72) đang làm, task bắt đầu khi xong; năm RFC dự kiến và RFC của `TODOS.md` #58 chờ chữ ký kỹ thuật trưởng | I2c (phần đã xong: `neuroedge.guard`, nửa (a) của RFC-0017) | tag `v0.2.4` (nội bộ) |
|  | **I2e — NeuroEdge Blueprint tối thiểu** | 2026-11-25 | Maker gói thiết bị đã chạy thành NeuroEdge Blueprint (`blueprint pack`); người khác cài bằng một lệnh từ URL + digest phủ toàn gói (`blueprint install`), chạy trên giả lập; Hub tối thiểu là index tĩnh; kit bể cá có BOM liên kết; khung dự án nhiều chip (Q-75); kênh cộng đồng; đo cổng nhu cầu 8 tuần (Q-72) | **0 / 15** | ⏳ Chưa bắt đầu | I2d | tag `v0.2.5` (nội bộ) · wheel giao trực tiếp cho người thử ngoài, không index nào (như Q-70); PyPI vẫn ở I6 (Q-39) |
|  | **I2f — NeuroEdge Cloud và hộp tại nhà ESP32** | sau cổng 8 tuần (nhánh) | Có điều kiện (Q-74 bước 2): agent trông nhà chỉ cần chat — bộ não NeuroEdge vận hành hộ trên NeuroEdge Cloud, mỗi người một instance cách ly (Q-76) điều phối nhiều thiết bị, nhiều nhà, nhiều người; gate, phản xạ, kiểm lời duyệt luôn ở hộp tại nhà (Pi, add-on Home Assistant, hoặc ESP32-S3 cho một việc) | **0 / 9** | ⏸ Chờ kết quả cổng nhu cầu 2026-12-06 (Q-74) | I2e | dịch vụ tuỳ chọn + firmware hộp ESP32 |
|  | **I3 — Gate trên Box-3 thật** | sau I2e | Gate chạy trên chip, điều khiển chân thật; người dùng tự nạp agent; `verify` ba target bậc 1 cho miền phán quyết | **6 / 16** | 🟡 Phần không cần bo mạch đã xong (kể cả firmware sinh cho agent trên QEMU, giao diện LVGL có ảnh golden); chờ bo mạch | I1 | tag `v0.3.0` + firmware (nội bộ) |
|  | **I3a — Nguyên thủy mở rộng trên `esp32s3`** | sau I2e | Bốn gói trên chip: Box-3 và M5Stack CoreS3 có camera (Q-53, Q-61); liên kết Pi ↔ ESP32 tối thiểu có nhịp tim, bo ESP32-S3 phổ thông và thư viện Arduino (Q-75) | **0 / 11** | ⏳ Chưa bắt đầu | I2a, I3 | tag `v0.3.1` + firmware (nội bộ) |
| **Công khai** | **I6 — Công khai** | sau I2e | Repo công khai, `pip install neuroedge` từ PyPI, lược đồ ở URL công khai, video demo bốn gói và Blueprint trên `sim`, `linux` và `esp32s3`; MCP qua mạng có xác thực, hợp đồng cho người tích hợp đóng băng, bề mặt Python công khai (Q-58, Q-63) | **7 / 11** | 🟡 Quét bí mật, SBOM, API Python công khai, MCP qua mạng có xác thực, hợp đồng cho người tích hợp trong `schemas/` (RFC-0015) xong; RFC-0014 chấp thuận (Q-65); chờ I3a | I2b, I2c, I3a | PyPI `v0.6.0` — lần phát hành ra ngoài đầu tiên |
| **v1.0 = MVP** | **I7 — v1.0** | sau I2e | Lần ra mắt MVP (Q-52): OTA A/B có ký, bảo mật thiết bị, ổn định 24 giờ trên chip; đủ tiêu chí PRD §11.1 | **4 / 12** | 🟡 Ghim Actions, attestation xong; OTA A/B có ký + rollback xong trên QEMU; chờ I6 | I6 | `v1.0.0` |
| **Beta** | **I8 — Developer Beta** | sau I2e | 50–100 lập trình viên ngoài trên dòng `1.0.x`; đo B1–B5, chọn nhánh | **0 / 1** | ⏳ Chưa bắt đầu | I7 | `1.0.x` (chỉ bản vá) |

**Giả định của các ngày dự báo (Q-39, Q-52, Q-72):** I2d chỉ cần phần đã xong của I2c (`neuroedge.guard`, nửa (a) của RFC-0017), nên dự báo sớm hơn I2c. I2d, I2e đi trước đo cổng nhu cầu 8 tuần (ngày 2026-12-06, B6–B8, PRD §11.2; nhánh theo kết quả: §5.6). I3 → I8 ghi "sau I2e", đặt lại ngày cùng PR có kết quả cổng (R5). Thoại, Lab và mọi increment sau Beta đã bỏ theo Q-77 (§6). Giả lập trước, phần cứng thật mua sau. Một người + AI agent (Q-60, §1.1). MVP trượt thì dời ngày, không cắt phạm vi (Q-52).

---

### 0.3 Thẻ Bàn giao Hiện tại (Active Session Handoff Card)

```text
MỤC TIÊU: Blueprint bể cá trọn 3 vòng trên giả lập (Q-72) trước cổng 8 tuần (B6–B8).
VỪA XONG: Q-76, Q-77; demo chat đèn và cửa (`demo/i2f-chat-den-cua/`): `mcp serve --http --ui`.
ĐANG LÀM: I2d. Demo chạy đủ sáu màn qua Telegram (2026-10-13, OrbStack làm cloud); VPS, đường hầm, video: TODOS #69.
LƯU Ý: Lệnh phần cứng qua c.do() và gate. LLM worker không tin cậy. Fail-closed.
```

### 0.4 Quy ước Cập nhật & Bàn giao (Handoff Protocol)

Khi xong một task: làm theo [`CONTRIBUTING.md` §8](../CONTRIBUTING.md#8-hoàn-thành-một-task--cập-nhật-tài-liệu-tiến-độ-changelog).

---

### 0.5 Phase (Q-52, Q-77)

Phase gom increment theo năng lực người dùng; ngày và phụ thuộc chỉ ở §0.2.

| Phase | Năng lực người dùng | Increment | Kết thúc bằng |
|:---|:---|:---|:---|
| **P0 — Dọn nền** | — | *(không có increment)* | Tài liệu sản phẩm ở `roadmap/` |
| **MVP = v1.0** | Chọn kit, chạy `sim` < 10 phút, dựng thiết bị thật trên `linux` hoặc `esp32s3`; đủ 4 gói mở rộng; nhiệm vụ 24/7 qua chat và Blueprint (Q-72, Q-77) | I0 → I7 (gồm I2a → I2e, I3a) | `v1.0.0` — đủ tiêu chí PRD §11.1; trượt thì dời ngày, không cắt (Q-52) |
| **Beta và cloud** | Lập trình viên và maker ngoài dùng thật; NeuroEdge Cloud thuê bao nếu số đo cần (Q-74, Q-76) | I2f (có điều kiện), I8 | `1.0.x` (§5.6) |

#### Mốc phát hành theo người dùng

Phase là cách đội lập kế hoạch; **mốc phát hành** là cách người dùng thấy sản phẩm (tám mốc sau Q-77). Mỗi mốc là một việc người dùng làm được, kết thúc khi mọi increment của nó xong. Bảng này không ghi ngày: ngày của một mốc là ngày dự báo muộn nhất trong các increment của nó ở §0.2. CPO Dashboard (`docs/business/cpo-dashboard.html`), poster E-09 và chương kiến trúc 15 §1 đọc từ bảng này. Mỗi increment thuộc đúng một mốc.

| # | Mốc | Người dùng làm được gì | Vì sao quan trọng | Increment | Ai dùng được |
|:---:|:---|:---|:---|:---|:---|
| 1 | **Thử trên laptop** | Cài một gói, chạy một agent có gate trên trình mô phỏng trong dưới 10 phút; không cần phần cứng, tài khoản hay khoá API | Cửa vào của sản phẩm: ai cũng thử được mà không tốn tiền phần cứng | I0, I1 | Đội và người thử nội bộ |
| 2 | **Thiết bị thật trên Raspberry Pi** | Đấu một kit (đèn, cửa, quạt, cảm biến, camera, motor) vào Pi 5; cùng agent, cùng gate như trên laptop; nối sản phẩm của hãng khác (Muse, Home Assistant, MCP server sẵn có) qua plugin và proxy | Lần đầu một lệnh AI chạm phần cứng thật mà vẫn qua hợp đồng — kể cả lệnh từ hệ sinh thái khác | I2, I2a, I2b, I2c | Đội, người thử nội bộ và một đội đối tác (phần proxy, `neuroedge.guard`, `sim` — Q-70) |
| 3 | **Gate chạy trên chip $5** | Nạp agent lên ESP32-S3 (Box-3, M5Stack CoreS3); gate quyết ngay trên chip, mất mạng vẫn chặn đúng | An toàn không phụ thuộc cloud; cùng một hợp đồng từ laptop tới vi điều khiển | I3, I3a | Đội và người thử nội bộ |
| 4 | **Dựng và chạy bằng hội thoại, chia sẻ Blueprint** | Mô tả thiết bị bằng lời với AI mình đang dùng (Claude Code, Claude Desktop); AI viết action, gate, phong bì và hợp đồng nhiệm vụ qua bộ tool MCP của NeuroEdge, NeuroEdge chấm, người duyệt rồi mới khoá; agent vận hành trông thiết bị cả ngày, chủ động báo và xin duyệt qua Telegram; gói thiết bị thành NeuroEdge Blueprint để người khác cài bằng một lệnh | Rút từ một ngày xuống vài phút để dựng một thiết bị có hợp đồng; hợp đồng và vết ghi thành bằng chứng để người lạ dám cài và maker bán được (Q-72) — mốc đi trước, đo bằng cổng nhu cầu 8 tuần | I2d, I2e | Đội, người thử nội bộ và người ngoài thử Blueprint trên giả lập qua wheel giao trực tiếp (Q-72) |
| 5 | **Ra mắt công khai** | Ai cũng `pip install neuroedge`; gọi thiết bị từ Claude, Home Assistant hay agent framework qua MCP có xác thực | **Lần đầu người ngoài dùng được** | I6 | Mọi người (phi thương mại miễn phí) |
| 6 | **v1.0 — đưa vào sản phẩm** | Cập nhật firmware có ký, khoá thiết bị, chạy ổn định 24 giờ; đủ tiêu chí nghiệm thu PRD §11.1 | Đủ tin cậy để đội sản phẩm đưa vào thiết bị bán ra | I7 | Mọi người; doanh nghiệp qua license thương mại |
| 7 | **Developer Beta** | 50–100 lập trình viên ngoài dùng thật trên dòng `1.0.x` | Số đo thật quyết hướng thương mại (điểm rẽ §5.6) | I8 | Lập trình viên được mời |
| 8 | **Một ô chat cho nhiều thiết bị, nhiều nhà** | Chat với một bộ não trông cả mạng lưới: nhiều ESP32, nhiều Pi, nhiều nhà, nhiều người có vai trò; tự host hoặc NeuroEdge Cloud (Q-74, Q-76) | Thuê bao cloud là dòng thu định kỳ (có điều kiện, sau cổng 8 tuần); cloud điều phối nhưng không có quyền tối cao — mỗi nút tự giữ luật | I2f | Gia đình, chủ homestay |


---

## 1. Giả định nguồn lực

### 1.1 Vai trò

| Vai trò | Trách nhiệm chính | Có mặt từ |
|:---|:---|:---:|
| **V1 — Nền tảng** | HAL, Action Contract Engine, lược đồ, Action CI, host | I0 |
| **V2 — Nhúng** | Port `esp32s3`, HAL trên chip, tối ưu bộ nhớ, node RP2350 | I0 |
| **V3 — DX** | Giao diện `sim`, CLI, scaffold, tài liệu, ví dụ mẫu, phát hành | I0 |
| **V4 — Hạ tầng** | Fleet OS, Registry, metering, provider layer | trước I9 |
| **V5 — Thị giác** | HAL thị giác, mô hình, NPU | trước I2a |
| **V7 — Lab** | Lab action, tool MCP dựng/chấm hợp đồng nháp (cùng V2) | trước I2d |
| **V6 — Nhúng 2** | Âm thanh trên chip, OTA và bảo mật thiết bị (cùng V2) | khi cần |

**Mô hình vận hành (Q-60): một người + AI agent.** Bảng trên là làn việc. AI agent làm làn host. Task phần cứng, người ngoài, chữ ký có người trong vòng.

### 1.2 Vì sao V2 phải có mặt từ đầu

Rủi ro bộ nhớ MCU (R-1) giảm nhờ cloud-first (PRD §13.2). V2 làm firmware không cần bo mạch (walker C, sổ token, UART trên QEMU) và chạy spike bộ nhớ ngay khi bo mạch về (TSK-S1-10) để kịp điều chỉnh I5 nếu cần (Q-44).

### 1.3 Độ nhạy theo quy mô đội

Một người + AI agent (Q-60): làn host giữ ngày §0.2; làn chip do một người làm nối tiếp, đối chiếu khi bo mạch về, dời ngày cùng PR có bằng chứng (R5).

---

## 2. Đường găng, phụ thuộc và luật chống lệch

### 2.1 Đồ thị phụ thuộc

Đọc `A ◄ B, C`: A phụ thuộc B và C (nguồn: cột Phụ thuộc của §0.2).
- MVP host: `I1 ◄ I0`, `I2 ◄ I1`, `I2a ◄ I2`, `I2b ◄ I2a`, `I2c ◄ I2b`.
- Q-72: `I2d ◄ I2c` (phần xong), `I2e ◄ I2d`, cổng nhu cầu 8 tuần `◄ I2e` (trên G1, G2).
- Q-74: `I2f ◄ I2e` và kết quả cổng nhu cầu (có điều kiện).
- MVP chip: `[bo mạch] ► TSK-S1-10 ► I3 ◄ I1`, `I3a ◄ I2a, I3`.
- Ra mắt: `I6 ◄ I2b, I2c, I3a`, `I7 ◄ I6`, `I8 ◄ I7`.
- Đường găng: `I2c` (phần) ► `I2d` ► `I2e` ► cổng 8 tuần (Q-72).

### 2.2 Đường găng

| # | Mắt xích | Lý do |
|:---:|:---|:---|
| **G** | **Đường găng cổng (Q-72): I2c ► I2d ► I2e ► cổng 8 tuần** | Đi trước mọi mắt xích; chạy trên giả lập G1, G2 |
| **0** | Sáu RFC của I2a được duyệt (PR #75 → #80) | Tiền đề mã nguyên thủy mở rộng (§2.3) |
| **1** | Bo mạch Box-3 về → TSK-S1-10 | Chốt ngân sách bộ nhớ cho 4 gói trên chip |
| **2** | I3 → I3a: HAL, gate và nguyên thủy mở rộng trên chip | Chứng minh tương đương target trên phần cứng thật |
| **3** | I6: công khai | Cài từ PyPI để đo A1, A9 trước v1.0 |
| **4** | I7: OTA, ổn định 24h, tiêu chí PRD §11.1 | Hoàn tất điều kiện nghiệm thu v1.0 |

### 2.3 Quy tắc đóng băng lược đồ

Từ khi I0 đóng băng lược đồ (2026-09-27), mọi thay đổi đối với lược đồ gate hoặc vết ghi bắt buộc: có RFC nêu rõ lý do và tương thích ngược; được kỹ thuật trưởng phê duyệt; kèm kịch bản di trú cho toàn bộ vết ghi đã tồn tại.

### 2.4 Luật chống lệch

| # | Luật | Kiểm bằng |
|:---:|:---|:---:|
| **R1** | Trạng thái task, tiêu chí ra, dự báo, phụ thuộc, thẻ phát hành và thang cắt chỉ ở tài liệu này | test |
| **R2** | Mã increment duy nhất và tăng dần; chỉ thêm, không đánh số lại; chèn giữa dùng hậu tố (`I3a`) | test |
| **R3** | Cột "Phụ thuộc" ở §0.2 chỉ trỏ về increment có số nhỏ hơn | test |
| **R4** | Mỗi increment đúng một ngày dự báo, chỉ ở §0.2; increment có điều kiện ghi "sau Ix" | test |
| **R5** | Dự báo chỉ đổi trong cùng PR có bằng chứng, và dời luôn các increment phụ thuộc | review |
| **R6** | Không dùng nhãn tuần hay tháng đánh số để xếp lịch; khoảng thời gian tính từ lúc increment mở | test |
| **R7** | Quyết định chỉ là `Q-N` (PRD §15); ngoài phạm vi chỉ ở PRD §14; tài liệu dẫn mã, không chép nội dung | review |
| **R8** | Mỗi mã TSK có đúng một dòng task trong tài liệu này; mọi mã được dẫn đều tồn tại ở đây | test |
| **R9** | Mỗi ô trạng thái có đúng một glyph trong ✅ 🟡 ⏳ ⏸ 🔴 | test |
| **R10** | "Tiến độ" ở §0.2 bằng số task ✅ trên tổng số task trong bảng của increment đó | test |
| **R11** | Tham chiếu chéo dùng mã hoặc mục ổn định, không dùng số dòng (`tệp.md:NNN`) | test |
| **R12** | Đóng băng Beta áp cho dòng `1.0.x` trong I8: chỉ lỗi chặn hành trình 10 phút và lỗi an toàn | review |

**Họ mã task:** `TSK-S1-*`..`S6-*` (sprint gốc); `TSK-K2-*`, `K3-*` (Khối 2, 3); `TSK-N*-*` (Lab); `TSK-V*-*`, `P*-*` (Giai đoạn 2); `TSK-W*-*` (robot); `TSK-I*-*` (việc mới theo increment).

---

## 3. Chiến lược tái sử dụng mã nguồn mở

Nguyên tắc: xây thứ tạo khác biệt, mượn thứ đã là hàng hóa.

### 3.1 Ranh giới bất di bất dịch

Ranh giới tài sản lõi (tự xây 100%) và hàng hóa (mượn tối đa) xác định tại §3.

### 3.2 Phép thử quyết định

Phụ thuộc vào nó có buộc vi phạm P-1, P-2 ([PRD §1.5](neuroedge-prd.md#15-năm-nguyên-tắc-thiết-kế-bất-biến)), hoặc ba quyết định kiến trúc (`sim` là target thật, gate là artifact có phiên bản, trace là công dân hạng nhất) không? Có → chỉ liên thông hoặc tham khảo. Không → tái sử dụng.

### 3.3 Kỷ luật giấy phép

Quy tắc giấy phép: §3, Phụ lục H. LiteLLM (MIT) dùng dạng SDK qua extra `neuroedge[cloud]` (Q-10, Q-11). Hawkbit (EPL-2.0) duyệt, EMQX không dùng (Q-11). Giấy phép NeuroEdge: [`LICENSING.md`](../LICENSING.md) (Q-45).

### 3.4 Ma trận tích hợp theo khối

Tái sử dụng: Typer/Rich/Pytest (CLI & CI), Pydantic v2 (lược đồ), XiaoZhi (driver Box-3), Pipecat/microWakeWord (âm thanh), ESP-IDF (OTA), LVGL (màn hình), LiteLLM (provider), Hawkbit (OTA canary), Mosquitto (viễn trắc), ORAS/Harbor (registry), OpenMeter (metering). Home Assistant Core API cho điều khiển phòng (Khối 4).

### 3.5 Năm dự án port trực tiếp

1. **XiaoZhi ESP32** (`targets/esp32s3/drivers/`): Codec I2S, chân Box-3, LCD ST7789.
2. **Pipecat** (`neuroedge/perception/pipeline/`): Frame processor âm thanh, barge-in thu hồi lệnh actuator.
3. **Wokwi Elements** (dự kiến, chưa dùng; TSK-S2-09 dùng web tự viết).
4. **LiteLLM** (`neuroedge/models/providers/`): Chuẩn hóa I/O provider, failover trong tiến trình (Q-10, Q-11).
5. **OpenMeter**: Engine gom sự kiện, đối soát lượt gọi agent và gate cho Khối 3.

**Bổ sung theo Q-76 (MIT, ghi nhận nguồn theo §3.9):** PicoClaw — nền của bộ não NeuroEdge, nay là fork cứng NeuroClaw (Q-78, TSK-I2d-22); zclaw và MimiClaw — tham khảo hoặc port thành phần C cho hộp ESP32 (TSK-I2f-03): client Telegram trên chip, Wi-Fi onboarding, bí mật trong NVS, boot guard, bảng điều khiển serial. Không lấy vòng lặp agent của họ làm nơi giữ quyền phần cứng.

### 3.6 Ba dự án chỉ liên thông, không phụ thuộc

ESP-Claw (liên thông qua MCP), LiveKit Agents và TEN Framework (chỉ tham khảo thiết kế) — §3. Không fork toàn bộ XiaoZhi.

### 3.7 Tác động thật lên đường găng

Đòn bẩy OSS rút ngắn thời gian port HAL lên `esp32s3` và runtime thoại trên MCU, đồng thời hạ rủi ro R-1 từ Cao xuống Trung bình.

### 3.8 Bảo toàn tương đương target khi có hai ngôn ngữ

Q-8: C/C++ trên ESP-IDF cho firmware, Python cho `sim` và `linux`. Bảo toàn bằng đặc tả FSM ([`voice_fsm.md`](../docs/spec/voice_fsm.md)), bộ vector tuân thủ (`fixtures/compliance/voice/`), vết ghi chuẩn mực (`fixtures/traces/`) và `neuroedge verify` (NE4002 nếu lệch).

### 3.9 Nghĩa vụ ghi nhận nguồn

Tuân thủ ma trận giấy phép, tệp `NOTICE`, ghi nhận trong mã, tài liệu công khai và ghim phiên bản (§3).

### 3.10 Rủi ro khi làm ngược

Tránh: fork toàn bộ XiaoZhi (mất HAL, mất an toàn); xây trên ESP-Claw (`linux` thành hạng hai); port thiếu vector (sai lệch phán quyết); nhúng copyleft (xung đột giấy phép Q-45).

### 3.11 Port tối đa theo task (Q-76)

Với mỗi task chưa làm, mượn trước, tự viết sau. Cột **Tự viết** là phần còn lại sau khi mượn, cũng là phần tạo khác
biệt. Giấy phép đã kiểm trên GitHub ngày 2026-10-12. Job `licence-obligations` chặn mọi tên chứa "GPL" (kể cả LGPL,
AGPL) trong bộ phụ thuộc lõi, nên thư viện copyleft chỉ được ở extra tuỳ chọn như `gpiod` hoặc không dùng.

| Task | Mượn | Giấy phép | Cách mượn | Tự viết |
|:---|:---|:---|:---|:---|
| TSK-I2d-22 bộ não | PicoClaw v0.3.1 → NeuroClaw (Q-78) | MIT | Fork cứng: mTLS, khoá cứng `exec`, `i2c`/`spi`/`serial`, cài skill, lệnh cron, hook; bỏ web console | Bản phát hành, theo dõi bản sửa bảo mật của PicoClaw bằng tay |
| TSK-I2d-23 tool MCP | `mcp` Python SDK (đã dùng) | MIT | Phụ thuộc | Ngữ nghĩa `propose_mission`, `mission_status`, `explain_block` |
| TSK-I2d-12 adapter Telegram của runtime | aiogram | MIT | Phụ thuộc (extra) | Bản ghi duyệt, ghép đôi (`TODOS.md` #62). **Không** dùng python-telegram-bot (LGPL-3.0, bị job giấy phép chặn) |
| TSK-I2d-09 lập lịch | APScheduler, croniter | MIT | Phụ thuộc | Bộ phát hiện tất định, `llm_budget` |
| TSK-I2d-24 cô lập worker | systemd (`DynamicUser`, `DeviceAllow`, `PrivateDevices`) | — (hệ điều hành) | Tệp unit mẫu | Test chứng minh worker không chạm phần cứng |
| TSK-I2d-11 bản ghi duyệt có chữ ký | `cryptography` (Ed25519) | Apache-2.0 / BSD | Phụ thuộc | Định dạng bản ghi, nonce, hạn (RFC) |
| Bộ phát hiện người (nhiệm vụ trông nhà) | Frigate (sự kiện qua MQTT hoặc Home Assistant); mô hình YOLOX | MIT; Apache-2.0 | Liên thông, không nhúng | Biến sự kiện thành dữ kiện cho gate. **Không** dùng Ultralytics (AGPL-3.0) |
| TSK-I2e-12 add-on Home Assistant | `home-assistant/addons-example` | Apache-2.0 | Khung mẫu | Đóng gói runtime + bộ não |
| TSK-I2e-13 ảnh thẻ SD, Wi-Fi, QR | pi-gen; balena wifi-connect | BSD-3-Clause; Apache-2.0 | Công cụ dựng ảnh; captive portal | Bước ghép đôi QR |
| TSK-I2e-14 khung dự án nhiều chip | copier | MIT | Công cụ sinh khung | Nội dung khung `host+mcu` |
| TSK-I2e-01 → I2e-03 Blueprint | ORAS (đã trong §3.4) | Apache-2.0 | Gói OCI cho `blueprint pack`/`install` | `blueprint.v1`, digest phủ toàn gói |
| TSK-I2f-02 cổng kênh và relay | NATS (leaf node, tài khoản JWT cho từng người) | Apache-2.0 | Hạ tầng | Định tuyến chat ↔ instance ↔ hộp, trần token |
| TSK-I2f-07 instance cách ly | Firecracker hoặc gVisor | Apache-2.0 | Hạ tầng | Ngủ/thức, trí nhớ mã hoá riêng |
| TSK-I2f-08 duyệt bằng passkey | py_webauthn; SimpleWebAuthn; Telegram Mini Apps SDK | BSD-3-Clause; MIT; MIT | Phụ thuộc | Kiểm chữ ký tại hộp |
| TSK-I2f-03 hộp ESP32 | zclaw, MimiClaw (client Telegram trên chip, NVS, boot guard, bảng serial); `wifi_provisioning` của ESP-IDF | MIT; Apache-2.0 | Port mã C | Walker và luật có ký đã có; nối hai phần |
| TSK-I3a-06, I3a-07 liên kết Pi ↔ ESP32 | nanopb (khung tin) + COBS và CRC | Zlib | Phụ thuộc C | Nhịp tim, `safe_state` (RFC node). Zenoh-pico vẫn để cho I14 (TSK-W3-01) |
| TSK-I3a-08 bo phổ thông | `esp-bsp` của Espressif | kiểm từng component | Hỗ trợ bo | Profile `boards/` |
| TSK-I3a-04 thị giác trên chip | esp-dl; esp-who | MIT; "ESPRESSIF MIT" (chỉ dùng trên chip Espressif) | Phụ thuộc | `vision.in` theo RFC-0012 |
| CI firmware | Workflow stack guard, ma trận target của zclaw | MIT | Chép workflow | — |

**Không mượn:** vòng lặp agent của các dự án "Claw" làm nơi giữ quyền phần cứng; mọi thứ thay gate, sổ token, vết
ghi (§3.1). Mỗi lần mượn mã (không chỉ phụ thuộc) thêm một dòng ghi nhận nguồn theo §3.9.

---

## 4. Increment tới v1.0 = MVP (I0–I7)

Từ Q-52, MVP là v1.0 đầy đủ: các increment có hậu tố (I2a, I2b, I3a, I4a, I5a) nằm cạnh increment mà chúng mở rộng.

Mỗi increment có: thẻ (mục tiêu, điều kiện vào ngoài các increment phụ thuộc, tín hiệu đo, người), bảng task, và tiêu chí ra. Increment chỉ được phát hành khi đạt mọi tiêu chí ra của nó, và kèm một demo trong `demo/` (§11.1, Q-49).

### 4.1 I0 — Lõi hợp đồng trên `sim`

| | |
|:---|:---|
| **Mục tiêu** | Lõi hợp đồng: gate có kiểu và phiên bản, `sim` là target thật, Action CI trên host, MCP và System 2 |
| **Điều kiện vào** | — |
| **Tín hiệu đo** | CI lõi (§0.1) |
| **Người** | V1, V2, V3 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S1-01** | Đặc tả 5 nguyên thủy HAL và đối chiếu | FR-HAL-01, FR-HAL-02, FR-HAL-03 | V1 | ✅ 2026-09-24 | [`schemas/board.v1.json`](../schemas/board.v1.json) |
| **TSK-S1-02** | Lược đồ gate v1 và hành vi on_block | FR-GATE-02, FR-GATE-03, FR-GATE-04 | V1 | ✅ 2026-09-24 | [`schemas/gate.v1.json`](../schemas/gate.v1.json) |
| **TSK-S1-03** | Quy tắc kế thừa extends | FR-GATE-06, FR-GATE-07, FR-GATE-08 | V1 | ✅ 2026-09-24 | [`gate_resolver.py`](../python/neuroedge/engine/gate_resolver.py) |
| **TSK-S1-04** | Lược đồ vết ghi v1 | FR-TRC-01, FR-TRC-02, FR-TRC-03 | V1 | ✅ 2026-09-24 | [`schemas/trace.v1.json`](../schemas/trace.v1.json) |
| **TSK-S1-05** | Ma trận giấy phép và tệp NOTICE | — | V2 | ✅ 2026-09-24 | [`NOTICE`](../NOTICE) |
| **TSK-S1-06** | Khung monorepo: schemas, python, targets, fixtures | — | V1 | ✅ 2026-09-24 | [`CONTRIBUTING.md`](../CONTRIBUTING.md) |
| **TSK-S1-07** | Ba tệp lược đồ chính thức trong schemas | FR-TRC-01, FR-GATE-02, FR-HAL-02 | V1 | ✅ 2026-09-24 | [`schemas/`](../schemas/) |
| **TSK-S1-08** | Ba tệp vết ghi chuẩn mực | FR-CI-01, FR-CI-02 | V1 | ✅ 2026-09-24 | [`fixtures/traces/`](../fixtures/traces/) |
| **TSK-S1-09** | Khung Python SDK, CLI và Action CI ban đầu | FR-CLI-01, FR-CI-01 | V1 | ✅ 2026-09-24 | [`python/neuroedge/`](../python/neuroedge/) |
| **TSK-S1-11** | Rà soát thiết kế HAL dưới ràng buộc MCU | — | V2 | ✅ 2026-09-24 | [`docs/spec/hal_mcu_review.md`](../docs/spec/hal_mcu_review.md) |
| **TSK-S1-12** | Hai workflow CI: ci-sim-linux và nightly-hardware | FR-CI-05, FR-CI-06 | V1 | ✅ 2026-09-24 | [`.github/workflows/`](../.github/workflows/) |
| **TSK-S1-13** | Quy ước đóng góp và mẫu RFC đổi lược đồ | — | V1 | ✅ 2026-09-24 | [`CONTRIBUTING.md`](../CONTRIBUTING.md) |
| **TSK-S2-01** | Hiện thực HAL cho target sim | FR-TGT-01, FR-HAL-01 | V2 | ✅ 2026-09-23 | `python/neuroedge/hal/sim.py` |
| **TSK-S2-02** | Đối chiếu năng lực lúc build | FR-HAL-04, FR-HAL-05, FR-DX-04 | V1 | ✅ 2026-09-23 | `python/neuroedge/engine/compiler.py` |
| **TSK-S2-03** | Gate Engine evaluate, allow_when, on_block | FR-GATE-03, FR-GATE-04, FR-GATE-09 | V1 | ✅ 2026-09-23 | `python/neuroedge/engine/gate.py` |
| **TSK-S2-04** | Fail-closed và mạch ngắt suy giảm | FR-ACE-03, NFR-REL-02 | V1 | ✅ 2026-09-23 | `python/neuroedge/engine/circuit_breaker.py` |
| **TSK-S2-05** | Decorator @action, token phán quyết dùng một lần | FR-ACE-02, FR-ACE-04, FR-ACE-05, FR-ACE-07 | V1 | ✅ 2026-09-23 | `python/neuroedge/actions/token.py` |
| **TSK-S2-08** | Interface SystemOne/SystemTwo và fallback lệnh cục bộ | FR-MDL-01, FR-MDL-02, FR-MDL-03, FR-ACE-03 | V1 | ✅ 2026-09-23 | `python/neuroedge/models/system.py` |
| **TSK-S2-09** | Giao diện web sim: cảm biến ảo, trạng thái actuator | FR-TGT-06 | V3 | ✅ 2026-09-23 | [`sim/ui.py`](../python/neuroedge/sim/ui.py) |
| **TSK-S2-11** | Lớp trừu tượng nhà cung cấp LiteLLM và System 2 | FR-MDL-06, FR-MDL-07, FR-MDL-08, FR-MDL-11, FR-GW-01, FR-GW-03 | V1 | ✅ 2026-09-24 | `python/neuroedge/models/providers/` |
| **TSK-S2-12** | Trình biên dịch cây quyết định host | FR-GATE-03, FR-ACE-01, FR-TGT-04 | V1 | ✅ 2026-09-23 | `python/neuroedge/engine/decision_tree.py` |
| **TSK-S2-13** | Kế thừa budget và on_block (RFC-0004) | FR-GATE-06, FR-GATE-07, FR-GATE-09 | V1 | ✅ 2026-09-23 | `python/neuroedge/engine/gate_resolver.py` |
| **TSK-S3-01** | Record ghi phiên ra tệp JSON hợp lệ | FR-CI-01 | V1 | ✅ 2026-09-23 | [`testing/recorder.py`](../python/neuroedge/testing/recorder.py) |
| **TSK-S3-02** | Replay trên sim và linux | FR-CI-02 | V1 | ✅ 2026-09-23 | [`testing/player.py`](../python/neuroedge/testing/player.py) |
| **TSK-S3-03** | Thư viện assert phán quyết và chân | FR-CI-03 | V1 | ✅ 2026-09-23 | [`testing/assertions.py`](../python/neuroedge/testing/assertions.py) |
| **TSK-S3-04** | Golden Reference so khớp chuỗi phán quyết | FR-CI-04 | V1 | ✅ 2026-09-23 | [`testing/golden.py`](../python/neuroedge/testing/golden.py) |
| **TSK-S3-05** | HAL target linux qua gpiod và gpio-sim | FR-TGT-02 | V2 | ✅ 2026-09-23 | [`hal/linux.py`](../python/neuroedge/hal/linux.py) |
| **TSK-S3-06** | Vỏ CLI và hợp đồng mã thoát | FR-CLI-01→04, FR-CLI-06, FR-TRC-08 | V3 | ✅ 2026-09-23 | `python/neuroedge/cli/` |
| **TSK-S3-07** | Scaffold neuroedge new Python thuần | FR-DX-01 | V3 | ✅ 2026-09-23 | [`python/neuroedge/templates/`](../python/neuroedge/templates/) |
| **TSK-S3-12** | Pipeline CI chạy sim và linux | FR-CI-05 | V1 | ✅ 2026-09-23 | [`.github/workflows/ci-sim-linux.yml`](../.github/workflows/ci-sim-linux.yml) |
| **TSK-S3-16** | Cổng CI digests.lock khoá digest gate | FR-GATE-01, FR-GOV-02, FR-CI-05 | V3 | ✅ 2026-09-24 | [`digests.lock`](../digests.lock) |
| **TSK-S3-17** | Đóng gói asset vào wheel | FR-DX-02, FR-DX-04 | V3 | ✅ 2026-09-23 | [`python/hatch_build.py`](../python/hatch_build.py) |
| **TSK-S3-18** | Lệnh neuroedge gate explain | FR-GATE-01, FR-CLI-05 | V3 | ✅ 2026-09-23 | [`engine/gate_explain.py`](../python/neuroedge/engine/gate_explain.py) |
| **TSK-S3-19** | verify đếm artifact, lỗi khi bằng 0 | FR-CI-07, FR-CLI-06, FR-DX-04 | V3 | ✅ 2026-09-24 | `python/neuroedge/cli/main.py` |
| **TSK-S3-20** | README gốc chuẩn trang PyPI | FR-DX-02, FR-DX-05 | V3 | ✅ 2026-09-24 | [`README.md`](../README.md) |
| **TSK-S3-22** | neuroedge trace view HTML tĩnh | FR-CLI-04, FR-DX-04 | V3 | ✅ 2026-09-23 | [`viz/`](../python/neuroedge/viz/) |
| **TSK-S3-23** | sensor.read và display trên sim | FR-TGT-01, FR-TGT-06, FR-CI-02 | V3 | ✅ 2026-09-23 | `python/neuroedge/hal/sim.py` |
| **TSK-S3-24** | Corpus tuân thủ Gated Tool Profile | FR-MDL-10, FR-ACE-09 | V1 | ✅ 2026-09-24 | `fixtures/tool_calls/` |
| **TSK-S3-25** | Khối arguments trong gate (RFC-0005) | FR-ACE-08, FR-GATE-06 | V1 | ✅ 2026-09-24 | `python/neuroedge/engine/arguments.py` |
| **TSK-S3-26** | Vòng xác nhận ask trên sim (RFC-0006) | FR-ACE-10 | V3 | ✅ 2026-09-24 | `python/neuroedge/actions/confirmation.py` |
| **TSK-S3-27** | neuroedge mcp serve --ui | FR-CLI-12, FR-DX-04 | V3 | ✅ 2026-09-24 | `python/neuroedge/mcp_server.py` |
| **TSK-S3-28** | System 2 làm MCP host | FR-MDL-11, FR-MDL-12 | V1 | ✅ 2026-09-23 | `python/neuroedge/mcp_host.py` |

- [x] **Tiêu chí 1:** JSON Schema của gate và trace có ví dụ hợp lệ và lỗi (`schemas/`).
- [x] **Tiêu chí 2:** Ba gate mẫu được phân giải đúng, gồm kế thừa 2 cấp (`test_sample_gates.py`).
- [x] **Tiêu chí 4:** Monorepo dựng xong, `schemas/` hợp lệ draft 2020-12 (job `frozen-artifacts`).
- [x] **Tiêu chí 5:** Ba vết ghi chuẩn mực phân giải đúng (`fixtures/traces/`).
- [x] **Tiêu chí 6:** Quyết định Q-11 đã chốt, LiteLLM và giấy phép đạt chuẩn.
- [x] **Tiêu chí 2 (A2):** `verify --targets sim,linux` đạt 100% (job `linux-hal`).
- [x] **Tiêu chí 3 (A3):** Không tồn tại đường tắt kích hoạt GPIO bỏ qua gate (`test_actions.py`).
- [x] **Tiêu chí 4 (A4):** 100% kịch bản suy giảm đều chặn hành động (`test_fail_closed.py`).
- [x] **Tiêu chí 5 (A5):** Bộ kiểm thử kế thừa gate đạt 100% (`test_gate_resolver.py`).
- [x] **Tiêu chí 6 (A7):** 100% phiên sinh vết ghi qua được `trace validate` (`test_recorder.py`).

### 4.2 I1 — Preview nội bộ trên `sim`

| | |
|:---|:---|
| **Mục tiêu** | Một lập trình viên ngoài đội, cài từ wheel nội bộ, chạy được agent có gate trong dưới 10 phút, không cần phần cứng (U1/J1 → M1; đo A1 sớm) |
| **Điều kiện vào** | — |
| **Tín hiệu đo** | TTFV trung vị trên 3 người ngoài đội, đo tại chỗ — chưa phát hành ra ngoài (Q-39) |
| **Người** | V3 (chủ trì), V1 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S3-08** | Ba ví dụ mẫu chạy được qua scaffold và wheel-smoke | FR-DX-05, FR-DX-06 | V3 | ✅ 2026-09-25 | `fixtures/agents/` · `tests/test_factory_monitor.py` |
| **TSK-S3-15** | Ba vết ghi chuẩn mực làm golden reference nguyên trạng | FR-CI-04, FR-TRC-05 | V1 | ✅ 2026-09-25 | `fixtures/traces/` · `tests/test_trace_vectors.py` |
| **TSK-I1-01** | Băm PII người dùng tại nguồn trong vết ghi | FR-TRC-06, FR-TRC-07, NFR-PRIV-03 | V1 | ✅ 2026-09-27 | `python/neuroedge/testing/recorder.py` |
| **TSK-I1-02** | Bộ đo TTFV tại chỗ (3 người ngoài đội) | FR-DX-01 | V3 | ⏳ Kích hoạt lại theo Q-72 | `docs/reports/` |
| **TSK-I1-03** | Ví dụ trong `--help`, scaffold tạo sẵn `traces/` | FR-CLI-07, FR-TRC-09 | V3 | ✅ 2026-09-26 | `python/neuroedge/cli/examples.py` |
| **TSK-I1-04** | NeuroEdge Studio ứng dụng web cục bộ | FR-TGT-06, FR-DX-06 | V3 | ⏸ Tạm dừng theo Q-72 | `python/neuroedge/studio/` |

**Tiêu chí ra I1:**

- [ ] **Tiêu chí 1 (M1):** TTFV đo tại chỗ trên 3 người ngoài đội đạt trung vị dưới 10 phút.
- [x] **Tiêu chí 2:** Mẫu thứ ba chạy được qua `neuroedge new`, có test trong `wheel-smoke`.
- [x] **Tiêu chí 3:** Golden reference là ba vết ghi chuẩn mực nguyên trạng, không cần RFC.
- [x] **Tiêu chí 4:** Vết ghi mặc định băm chữ thô người dùng tại nguồn.
- [ ] **Tiêu chí 5:** Tag `v0.1.0` có GitHub Release nội bộ; `wheel_smoke.sh` xanh trên wheel đó.

### 4.3 I2 — `linux` ngang `sim`

| | |
|:---|:---|
| **Mục tiêu** | Cùng agent chạy tương tác trên `linux` như trên `sim`: REPL, `record`, `mcp serve` |
| **Điều kiện vào** | 1 RPi 5 cho nightly (Phụ lục B) |
| **Tín hiệu đo** | Phiên tương tác trên gpio-sim; nightly RPi 5 xanh |
| **Người** | V3 (TSK-S5-10), V1 (TSK-S5-09, TSK-I2-01) |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S5-09** | `sensor.read` và `display` trên `linux` qua sysfs | FR-TGT-02, FR-HAL-01 | V1 | ✅ 2026-09-26 | `python/neuroedge/hal/linux.py` |
| **TSK-S5-10** | Phiên tương tác REPL, `record`, `mcp serve` trên `linux` | FR-CLI-02, FR-TGT-02 | V3 | ✅ 2026-09-25 | `python/neuroedge/hal/linux.py` |
| **TSK-I2-01** | Nightly `linux` trên RPi 5 phần cứng thật | FR-CI-06, FR-TGT-02 | V1 | ⏳ Chưa bắt đầu | `.github/workflows/nightly-hardware.yml` |
| **TSK-W0-04** | Trôi phụ thuộc hằng đêm tự mở issue (Q-32) | — | V3 | ✅ 2026-09-26 | `.github/workflows/nightly-hardware.yml` |

**Tiêu chí ra I2:**

- [x] **Tiêu chí 1:** `run`, `record`, `mcp serve --target linux` chạy trên gpio-sim, cùng hợp đồng mã thoát.
- [ ] **Tiêu chí 2:** `sensor.read` và `display` trên `linux` có test; hồ sơ bo chỉ khai nguyên thủy HAL chạy được.
- [x] **Tiêu chí 3:** `neuroedge verify --targets sim,linux` đạt 100%.
- [ ] **Tiêu chí 4:** Nightly trên RPi 5 chạy `tests_linux/` và `verify --targets linux` trên phần cứng thật.

### 4.3.1 I2a — Nguyên thủy mở rộng trên `sim` và `linux`

| | |
|:---|:---|
| **Mục tiêu** | Đủ bốn gói nguyên thủy mở rộng chạy trên `sim` và `linux` (Q-52, Q-53) |
| **Điều kiện vào** | — · RFC mở ngay, mã chờ RFC chấp thuận (§2.3) |
| **Tín hiệu đo** | Tiêu chí ra bên dưới |
| **Người** | V1 (chủ trì), V5 (thị giác), V2 (RFC-motion), kỹ thuật trưởng |
| **Thiết kế** | `docs/architecture/vi/15-target-architecture.md` §4.4 · `docs/architecture/vi/15-target-architecture.md` §4.3 · `docs/spec/lab_mcp.md` §7–§8 · RFC-0007, RFC-0009 → RFC-0013 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I2a-01** | Ước lượng lại phạm vi MVP (Q-52) | — | trưởng nhóm + kỹ thuật trưởng | ✅ 2026-09-30 | `docs/reports/uoc-luong-mvp-2026-09-30.md` |
| **TSK-N0-02** | Sửa FR-HAL-01: nguyên thủy mở rộng tuỳ chọn theo bo | FR-HAL-01, FR-CLI-12 | V2 | ✅ 2026-10-03 | `neuroedge-prd.md` |
| **TSK-N0-03** | RFC-0007: `digital.in`, I2C chỉ đọc, `analog.in` | FR-HAL-01 | V2 | ✅ 2026-10-01 | `docs/rfc/0007-digital-in-i2c-analog-in-phong-bi.md` |
| **TSK-I2a-07** | RFC-0013: nguyên thủy mở rộng tuỳ chọn, nhiều bo tham chiếu | FR-HAL-01, FR-TGT-08 | V1 + kỹ thuật trưởng | 🟡 RFC chấp thuận, phần host xong; còn ô esp32s3 | `docs/rfc/0013-nguyen-thuy-tuy-chon-va-nhieu-bo-tham-chieu.md` · `hal/board.py` |
| **TSK-I2a-06** | Profile `sim-rpi5` soi đúng `linux-rpi5` | FR-TGT-01, FR-TGT-06 | V1 | ✅ 2026-10-04 | `boards/sim-rpi5.toml` |
| **TSK-W1-02** | Tiêu chí `numeric` cho `sensor.read`, `NETR` v2, walker C | FR-GATE-03, FR-HAL-01 | V1 | ✅ 2026-10-03 | `python/neuroedge/engine/constraints.py` |
| **TSK-I2a-02** | `digital.in` trên `sim` và `linux` qua gpiod/gpio-sim | FR-HAL-01 | V1 | ✅ 2026-10-04 | `python/neuroedge/hal/linux.py` |
| **TSK-I2a-03** | Bus I2C chỉ đọc cho agent trên `sim` và `linux` | FR-HAL-01 | V1 | ✅ 2026-10-04 | `python/neuroedge/hal/i2c_bus.py` |
| **TSK-N3-03** | Spike ADC trên `ubuntu-latest` qua hwmon `i2c-stub` | — | — | ✅ 2026-10-03 | `scripts/setup_i2c_stub.sh` |
| **TSK-I2a-04** | `analog.in` (ADC) trên `sim` và `linux` theo RFC-0009 | FR-HAL-01 | V1 | ✅ 2026-10-04 | `python/neuroedge/hal/linux.py` |
| **TSK-W1-01** | PWM và phản hồi trạng thái trong `digital.out` (RFC-0010) | FR-HAL-01 | V1 + V2 | 🟡 Xong sim và linux giả; còn kênh PWM thật, bo thật, HAL C | `docs/rfc/0010-pwm-trong-digital-out.md` · `hal/pwm.py` |
| **TSK-I2a-08** | Spike kernel đủ module cho job `linux-hal` (Q-69) | FR-CI-06, FR-HAL-01 | V1 | ⏳ Chưa bắt đầu | `docs/reports/` |
| **TSK-V1b-07** | RFC-0012: nguyên thủy `vision.in` | FR-HAL-01, FR-HAL-04 | V1 | ✅ 2026-10-01 | `docs/rfc/0012-nguyen-thuy-vision-in.md` |
| **TSK-V1b-01** | Hiện thực `vision.in` V4L2 cho `linux` | FR-HAL-01 | V5 | ✅ 2026-10-04 | `python/neuroedge/hal/vision.py` |
| **TSK-V1b-02** | Camera ảo trong `sim` phát lại chuỗi ảnh | FR-TGT-01, FR-TGT-06 | V5 | ✅ 2026-10-04 | `python/neuroedge/sim/vision/` |
| **TSK-V1b-03** | Giao diện trừu tượng mô hình thị giác đổi bằng cấu hình | FR-MDL-04, FR-MDL-07 | V5 | ✅ 2026-10-04 | `python/neuroedge/perception/vision/` |
| **TSK-V1b-04** | Action CI cho khung hình: record, replay, assert phán quyết | FR-CI-01→04 | V1 | ✅ 2026-10-04 | `python/neuroedge/testing/vision.py` |
| **TSK-V1b-05** | Tích hợp NPU rời (Hailo-8, Coral) sau giao diện trừu tượng | FR-MDL-04 | V5 | ⏳ Chưa bắt đầu | `python/neuroedge/perception/vision/accel/` |
| **TSK-V1b-06** | Ba gate mẫu có yếu tố thị giác, ngưỡng số khoá ở gate | FR-GATE-03 | V1 + V5 | ✅ 2026-10-04 | `gates/vision/` |
| **TSK-V1b-08** | Bằng chứng thị giác trong vết ghi, lint `vision_ref` | FR-CI-02, NFR-PRIV-01, NFR-PRIV-03 | V1 | ✅ 2026-10-04 | `python/neuroedge/trace.py` |
| **TSK-W1-03** | RFC-0011: `motion.*`, token thuê có hạn, trạng thái an toàn | FR-HAL-01 | V1 + V2 | ✅ 2026-10-01 | `docs/rfc/0011-nguyen-thuy-motion.md` |
| **TSK-I2a-05** | `motion.*` trên `sim` và `linux` theo RFC-0011 | FR-HAL-01, FR-PER-02 | V1 + V2 | 🟡 Xong sim và linux giả; còn PWM thật, bo thật, HAL C | `docs/rfc/0011-nguyen-thuy-motion.md` · `hal/motion.py` |
| **TSK-N2-01** | Hook phong bì trong `digital_out`, từ chối không tiêu token | FR-HAL-* | — | ✅ 2026-10-04 | `python/neuroedge/hal/envelope.py` |
| **TSK-N2-02** | Chính sách phong bì nguyên tử, đồng hồ tiêm vào, ghi sự kiện | — | — | ✅ 2026-10-04 | `python/neuroedge/hal/envelope.py` |
| **TSK-N2-03** | Móc tắt an toàn cho `mcp serve`: `close()`, SIGTERM | — | — | ✅ 2026-10-04 | `python/neuroedge/sim/serve.py` |
| **TSK-N2-04** | Hợp đồng hồi quy năm khẳng định an toàn | — | — | ✅ 2026-10-04 | `python/tests/test_safety_regressions.py` |
| **TSK-N2-05** | Cập nhật sơ đồ đầu `mcp_server.py` thêm bước phong bì | — | — | ✅ 2026-10-04 | `python/neuroedge/mcp_server.py` |

- [x] **Tiêu chí N2.1:** Hai lệnh đồng thời cùng chân cho đúng một `envelope_refused`.
- [x] **Tiêu chí N2.2:** SIGTERM giữa xung trên gpio-sim đưa line về 0; unit của TSK-N2-03 ra `hal.close()`, mã 143.
- [x] **Tiêu chí N2.3:** Năm khẳng định của hợp đồng hồi quy đều xanh.

**Tiêu chí ra I2a:**

- [x] **Tiêu chí 1:** Sáu RFC (0007, 0009→0013) Đã chấp thuận; `schemas/` chỉ đổi trong phạm vi các RFC đó.
- [x] **Tiêu chí 2:** RFC-0007 không đổi byte nào của `schemas/gate.v1.json` — thay đổi chỉ qua RFC-0009.
- [x] **Tiêu chí 3:** Mỗi gói có agent mẫu chạy trên `sim` và `linux`; `verify --targets sim,linux` đạt 100%.
- [x] **Tiêu chí 4:** Gate so ngưỡng số: corpus hợp lệ và phản chứng khép kín; walker C khớp engine host.
- [ ] **Tiêu chí 5:** Mất nguồn dữ liệu giữa phiên thì hành động bị chặn fail-closed; cơ cấu về trạng thái an toàn.
- [x] **Tiêu chí 6:** Đổi mô hình thị giác bằng cấu hình; vết ghi không chứa ảnh thô; `replay` tái hiện phán quyết.
- [x] **Tiêu chí 7:** Agent yêu cầu nguyên thủy mở rộng bị từ chối lúc build trên bo không khai, nêu đủ ba thành phần.
- [x] **Tiêu chí 8:** Kết quả spike ADC được ghi lại và quyết định ADC đã áp dụng.
- [ ] **Tiêu chí 9:** Năm nguyên thủy lõi và ba vết ghi chuẩn mực giữ nguyên chuỗi phán quyết; TTFV dưới 10 phút.

### 4.3.2 I2b — Kit mẫu và dựng nhanh

| | |
|:---|:---|
| **Mục tiêu** | Người dùng chọn kit, chạy trên `sim` dưới 10 phút, dựng thiết bị thật từ BOM và sơ đồ đấu dây |
| **Điều kiện vào** | — |
| **Tín hiệu đo** | Tiêu chí ra bên dưới; A12 đo ở I7 |
| **Người** | V3 (chủ trì), V1, V5 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I2b-01** | Ba kit phần cứng từ ba template có sẵn | FR-DX-05, FR-DX-06 | V3 | ✅ 2026-10-04 | `python/neuroedge/templates/` · `fixtures/agents/` |
| **TSK-I2b-02** | Hai kit cho gói mới: camera cổng và rèm servo | FR-DX-05 | V3 + V5 | ✅ 2026-10-04 | `python/neuroedge/templates/` · `fixtures/agents/` |
| **TSK-I2b-03** | Thư viện gate khởi đầu để kế thừa: cửa, đèn, van, còi, điều hoà, camera, động cơ | FR-GATE-05 | V1 | ✅ 2026-10-04 | `gates/` · `digests.lock` |
| **TSK-I2b-04** | Lệnh dựng nhanh `neuroedge add` cho action, gate, sensor, device | FR-DX-01, FR-DX-08 | V3 | ✅ 2026-10-04 | `python/neuroedge/cli/main.py` |

**Tiêu chí ra I2b:**

- [x] **Tiêu chí 1:** Năm kit chạy qua `neuroedge new --template` trên `sim`, có test trong `wheel-smoke`.
- [ ] **Tiêu chí 2:** TTFV trên `sim` của mọi kit đạt dưới 10 phút.
- [x] **Tiêu chí 3:** `neuroedge add` sinh action + gate + test hai chiều; chạy lại không ghi đè tệp cũ.
- [x] **Tiêu chí 4:** Mọi gate cha trong thư viện khởi đầu có ca phản chứng chống nới lỏng.

### 4.3.3 I2c — Nền tảng mở

| | |
|:---|:---|
| **Mục tiêu** | Bên thứ ba tự nối NeuroEdge với sản phẩm mới qua điểm cắm, proxy và cơ cấu từ xa (Q-67) |
| **Điều kiện vào** | — · task mã chờ RFC tương ứng được ký |
| **Tín hiệu đo** | M6, A13; số plugin của bên thứ ba qua test tuân thủ |
| **Người** | V1 (chủ trì), V3; người cho TSK-I2c-16 trên HA thật và TSK-I2c-17 |
| **Thiết kế** | `docs/architecture/vi/16-ecosystem-landscape.md` §4 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I2c-01** | Quyết định và thiết kế nền tảng mở (Q-67) | FR-EXT-01→09 | V1 | ✅ 2026-10-04 | `docs/architecture/vi/16-ecosystem-landscape.md` §4 |
| **TSK-I2c-02** | RFC-0016: lõi an toàn dùng độc lập và Extension SDK | FR-EXT-01→05, FR-EXT-09 | V1 | ✅ 2026-10-04 | `docs/rfc/0016-loi-tach-duoc-va-extension-sdk.md` |
| **TSK-I2c-03** | RFC-0017: nguồn gọi theo không gian tên `bridge:<id>` | FR-EXT-03 | V1 | ✅ 2026-10-04 | `docs/rfc/0017-nguon-goi-theo-khong-gian-ten.md` |
| **TSK-I2c-04** | RFC-0018: cơ cấu chấp hành từ xa và mức tự tắt | FR-EXT-07 | V1 | ✅ 2026-10-04 | `docs/rfc/0018-co-cau-chap-hanh-tu-xa.md` |
| **TSK-I2c-05** | `--board <đường dẫn>` hồ sơ bo ngoài kho | FR-EXT-05, FR-TGT-08 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/hal/board.py` |
| **TSK-I2c-06** | Giấy phép: corpus tuân thủ sang Apache-2.0 | FR-GOV-03 | V1 | ✅ 2026-10-04 | `LICENSING.md` |
| **TSK-I2c-07** | API `neuroedge.guard`: lõi an toàn độc lập | FR-EXT-01 | V1 | ✅ 2026-10-09 | `python/neuroedge/guard.py` |
| **TSK-I2c-08** | Tài sản từ đường dẫn, package, git | FR-EXT-05 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/templates/` |
| **TSK-I2c-09** | Mã RFC-0014: dữ kiện từ tiến trình ngoài qua Unix socket | FR-MDL-04, FR-MDL-10, FR-EXT-02 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/` |
| **TSK-I2c-10** | Mã RFC-0017: `source` không gian tên, `tool-call.v1` | FR-EXT-03 | V1 | 🟡 Nửa a xong (`bridge:<id>`); còn nửa b `[mcp.clients]` | `python/neuroedge/actions/tools.py` |
| **TSK-I2c-11** | Bộ nạp plugin và `neuroedge.sdk` entry points | FR-EXT-02, FR-EXT-09, NFR-SEC-10 | V1 | 🟡 SDK tối thiểu và Actuator xong; 5 loại còn lại chưa | `python/neuroedge/sdk/` |
| **TSK-I2c-12** | Bộ test tuân thủ theo loại plugin (`conformance`) | FR-EXT-03, FR-EXT-04 | V1 | 🟡 Actuator vector L0–L3 xong; 5 loại còn lại chưa | `python/neuroedge/testing/conformance/` |
| **TSK-I2c-14** | `neuroedge proxy mcp` che MCP server sẵn có | FR-EXT-06 | V1 | ✅ 2026-10-09 | `python/neuroedge/proxy_mcp.py` |
| **TSK-I2c-15** | `neuroedge proxy http` trước API HTTP cục bộ | FR-EXT-06 | V1 | ✅ 2026-10-09 | `python/neuroedge/proxy_http.py` |
| **TSK-I2c-16** | Cơ cấu từ xa đầu tiên — Home Assistant (RFC-0018) | FR-EXT-07 | V1 | ✅ 2026-10-09 | `python/neuroedge/hal/remote.py` |
| **TSK-I2c-18** | Index cộng đồng và `plugin search/install` | FR-EXT-08 | V3 | ⏳ Chưa bắt đầu | kho index ngoài repo |
| **TSK-I2c-19** | Gói cho đợt thử với đối tác (Q-70) | FR-DX-02, FR-DX-05, FR-EXT-01, FR-EXT-06 | V3 | ✅ 2026-10-09 | `docs/user/doi-tac/` · `scripts/partner_guides_check.sh` |
| **TSK-S3-21** | Ghim `extends` bằng digest `@<ver>#sha256:` | FR-GATE-05, FR-GATE-06 | V1 | ⏳ Chưa bắt đầu | Cần RFC riêng |
| **TSK-V1a-01** | Hoàn thiện và bảo vệ RFC-0002 qua thảo luận | FR-TGT-08, FR-HAL-01 | V1 | ✅ 2026-10-04 | `docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md` |
| **TSK-P2-06** | Chứng nhận tự kiểm "NeuroEdge-gated" cho bên thứ ba | FR-GOV-03 | V3 | ⏳ Chưa bắt đầu | `docs/spec/tool_calling.md` §9 |

**Tiêu chí ra I2c:**

- [x] **Tiêu chí 1:** RFC-0016, 0017, 0018 và RFC-0002 Đã chấp thuận.
- [x] **Tiêu chí 2:** Chương trình không cần `agent.toml` gate được hành động qua `neuroedge.guard`, sinh vết ghi hợp lệ.
- [ ] **Tiêu chí 3:** Với mỗi loại trong sáu loại điểm cắm, package ngoài kho qua `conformance` và chạy được.
- [x] **Tiêu chí 4:** `proxy mcp` che MCP server sẵn có trong ≤ 3 lệnh; `plugin doctor` cảnh báo đường tắt.
- [x] **Tiêu chí 5:** Cơ cấu từ xa HA đạt đúng mức tự tắt L1; hành động không hoàn tác thiếu tự tắt bị từ chối.
- [ ] **Tiêu chí 6:** Dữ kiện từ tiến trình ngoài qua đủ bằng chứng RFC-0014 §7.
- [ ] **Tiêu chí 7** *(tạm dừng theo Q-72)*: Danh sách target mở theo RFC-0002.
- [ ] **Tiêu chí 8 (A13)** *(tạm dừng theo Q-72)*: Bridge `neuroedge-muse` viết ở kho riêng qua test tuân thủ ≤ 1 ngày.
- [ ] **Tiêu chí 9:** `pytest` xanh, 0 skipped; `wheel_smoke.sh` cài và chạy plugin ngoài kho từ wheel.

**Thử với đối tác (Q-70):**

- [x] **Đối tác 1:** Tiêu chí 2, 4, 5 đạt; `proxy http` xong.
- [x] **Đối tác 2:** Wheel chạy tay qua test; 47 bước của ba hướng dẫn chạy sạch trên wheel.
- [ ] **Đối tác 3:** Thoả thuận thử nghiệm bằng văn bản với đối tác.
- [ ] **Đối tác 4:** Kênh phản hồi riêng và quy trình tiếp nhận lỗi.
- [ ] **Đối tác 5:** Đối tác cài wheel và che được một MCP server/API thiết bị trong ≤ 15 phút.

### 4.3.4 I2d — Nhiệm vụ và agent vận hành

| | |
|:---|:---|
| **Mục tiêu** | Vòng ① và ② của Q-72 trên giả lập: hợp đồng nhiệm vụ, agent vận hành 24/7, duyệt qua chat |
| **Điều kiện vào** | Phần đã xong của I2c; task mã chờ RFC được ký |
| **Tín hiệu đo** | A15 → A22 (PRD §11.1); chi phí LLM; số ngày runtime chạy liên tục trên G2 |
| **Người** | V1 (chủ trì), V3, V7, V2, kỹ thuật trưởng |
| **Thiết kế** | Q-72 · PRD §4.5, §5.4–§5.6 · `docs/spec/lab_mcp.md` · proposal Blueprint |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I2d-01** | RFC khoá bắt buộc hiểu (`requires = [...]`) cho `board.v1` | FR-ACE-03, FR-HAL-02 | V1 + kỹ thuật trưởng | ⏳ Chưa bắt đầu | `docs/rfc/` |
| **TSK-I2d-02** | RFC an toàn có điều kiện (`safe_state` đối xứng) | FR-ACE-03, FR-BP-06, NFR-REL-02 | V1 + V2 + kỹ thuật trưởng | ⏳ Chờ TSK-I2d-01 | `docs/rfc/` |
| **TSK-I2d-03** | Mã an toàn có điều kiện: HAL, phong bì, sổ token, walker C | FR-ACE-03, FR-BP-06, NFR-REL-02 | V1 + V2 | ⏳ Chờ TSK-I2d-02 | `python/neuroedge/hal/` |
| **TSK-I2d-04** | RFC `mission.v1`: hợp đồng nhiệm vụ nhiều thiết bị | FR-MSN-01 → FR-MSN-09 | V1 + kỹ thuật trưởng | ⏳ Chưa bắt đầu | `docs/rfc/` |
| **TSK-I2d-05** | Trình biên dịch hợp đồng nhiệm vụ xuống phong bì và watchdog | FR-MSN-02, FR-MSN-03, FR-MSN-05, FR-MSN-07, FR-MSN-10, FR-MSN-11 | V1 | ⏳ Chờ TSK-I2d-04 | `python/neuroedge/mission/` |
| **TSK-I2d-06** | Bản duyệt ≤ 5 dòng và vòng nháp từ diff có cấu trúc | FR-MSN-12, FR-MSN-13, FR-MSN-14, FR-CLI-15 | V3 | ⏳ Chờ TSK-I2d-04 | `python/neuroedge/mission/` |
| **TSK-I2d-07** | Đồng hồ đơn điệu cho watchdog, xử lý giờ tường `unsynced` | FR-MSN-04, FR-AGT-03 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/agent/` |
| **TSK-I2d-08** | Hai tiến trình: runtime 24/7 và worker LLM không tin cậy | FR-AGT-01, FR-AGT-02, FR-AGT-07, FR-CH-05, NFR-REL-06, NFR-SEC-13 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/agent/` |
| **TSK-I2d-09** | Lập lịch, bộ phát hiện tất định, `llm_budget`, báo chủ động | FR-AGT-03 → FR-AGT-06, FR-MSN-09, NFR-COST-01, NFR-COST-02, NFR-REL-05 | V1 | ⏳ Chưa bắt đầu | `python/neuroedge/agent/` |
| **TSK-I2d-10** | RFC và mã luồng dữ liệu chống rò rỉ: runtime là cửa ra duy nhất | FR-EGR-01 → FR-EGR-04, FR-MSN-06, NFR-SEC-11 | V1 + kỹ thuật trưởng | ⏳ Chưa bắt đầu | `python/neuroedge/egress/` |
| **TSK-I2d-11** | RFC nguồn `chat:<id>` và bản ghi duyệt có chữ ký, nonce, hạn | FR-CH-02, FR-CH-04, FR-ACE-10, FR-TRC-13 | V1 + kỹ thuật trưởng | ⏳ Chưa bắt đầu | `docs/rfc/` |
| **TSK-I2d-12** | Adapter Telegram và bản ghi duyệt trong runtime | FR-CH-01, FR-CH-03, FR-CH-04, FR-GATE-04, FR-CLI-14, NFR-SEC-12 | V3 + V1 | ⏳ Chờ TSK-I2d-11 | `python/neuroedge/channels/` |
| **TSK-I2d-13** | RFC đoạn vết ghi trong `trace.v1`: chuỗi đoạn replay được | FR-TRC-11, FR-TRC-13, FR-ACE-06, NFR-OBS-01 | V1 + kỹ thuật trưởng | ⏳ Chưa bắt đầu | `docs/rfc/` |
| **TSK-I2d-14** | Mã vết ghi theo đoạn, flush định kỳ, replay từng đoạn | FR-TRC-12, NFR-OBS-04 | V1 | ⏳ Chờ TSK-I2d-13 | `python/neuroedge/testing/` |
| **TSK-I2d-15** | G1: mô hình vật lý bể cá trên `sim` (tua nhanh 30 ngày) | FR-TGT-07 | V7 + V1 | ⏳ Chưa bắt đầu | `python/neuroedge/sim/` |
| **TSK-I2d-16** | G2: runtime chạy liên tục trên `linux` tự khởi động lại | FR-AGT-01, NFR-REL-06 | V1 | ⏳ Chưa bắt đầu | `python/tests_linux/` |
| **TSK-I2d-17** | `neuroedge lab doctor` kiểm từng cảm biến nhiệm vụ | FR-DX-10 | V7 | ⏳ Chưa bắt đầu | `python/neuroedge/lab/` |
| **TSK-I2d-18** | Lab vòng ① cho hợp đồng nhiệm vụ qua tool MCP | FR-DX-10, FR-MSN-13 | V7 | ⏳ Chờ TSK-I2d-05 | `python/neuroedge/lab/` |
| **TSK-I2d-19** | Kịch bản bể cá và nghiệm thu A15→A22 trên G1 | FR-TGT-07, FR-AGT-04, NFR-COST-01 | V1 + V3 | ⏳ Chưa bắt đầu | `fixtures/agents/` · `demo/` |
| **TSK-I2d-20** | RFC bước xác minh và luồng nhiều bước do người dùng khai (Q-73) | FR-CH-06, FR-ACE-10 | V1 + kỹ thuật trưởng | ⏳ Chưa bắt đầu — trước TSK-I2d-11 | `docs/rfc/` |
| **TSK-I2d-21** | Mã bước xác minh: plugin bộ kiểm, nhãn rủi ro, vết ghi đạt/trượt | FR-CH-06, FR-TRC-13 | V1 + V3 | ⏳ Chờ TSK-I2d-20 | `python/neuroedge/actions/` |
| **TSK-I2d-22** | Bộ não NeuroEdge: NeuroClaw, fork cứng PicoClaw, chỉ MCP tới runtime (Q-76, Q-78) | FR-AGT-12, FR-AGT-02 | V1 + V3 | 🟡 NeuroClaw có repo và CI (2026-10-13): mTLS, khoá cứng, nói rõ câu hỏi `ask`; demo nội bộ chạy đủ sáu màn qua Telegram (`demo/i2f-chat-den-cua/`); VPS thật hoãn (`TODOS.md` #69) | [`letrongminh/neuroclaw`](https://github.com/letrongminh/neuroclaw) |
| **TSK-I2d-23** | Bộ tool MCP chuẩn cho mọi worker: `propose_mission`, `mission_status`, `explain_block` | FR-AGT-12, FR-MSN-13 | V1 | ⏳ Chờ TSK-I2d-04 | `python/neuroedge/mcp/` |
| **TSK-I2d-24** | Cô lập worker tại nhà: user riêng, không quyền phần cứng, test worker bị chiếm | NFR-SEC-13, FR-AGT-12 | V1 | ⏳ Chờ TSK-I2d-08 | `python/tests_linux/` |
| **TSK-N0-07** | Đặc tả bề mặt đóng tool lab (Q-71) | FR-DX-10 | V2 | ⏳ Chưa bắt đầu | `docs/spec/lab_tools.md` |
| **TSK-N0-08** | Tách quyền thiết bị khỏi client MCP (Q-71) | NFR-SEC-09 | V2 | ⏳ Chưa bắt đầu | `docs/user/` · `tests_linux/` |
| **TSK-N1-02** | Cờ `[lab] enabled` trong `agent.toml`, mặc định tắt | — | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/lab/` |
| **TSK-N1-04** | Kết quả lab call kèm `gate explain` để sửa lệnh | FR-MDL-10 | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/lab/` |
| **TSK-N1-05** | Cấu hình client trong một bước: `mcp desktop-config --lab` | FR-CLI-12 | V2 | ⏳ Chưa bắt đầu | `python/neuroedge/mcp_desktop.py` |
| **TSK-N5-01** | Tool `lab_draft_write` và `lab_draft_check` (Q-71) | FR-DX-01, FR-DX-10 | — | ⏳ Chưa bắt đầu | `python/neuroedge/lab/` |
| **TSK-N5-02** | Test hai chiều bắt buộc (ít nhất một ALLOW và một BLOCK) | FR-CI-* | — | ⏳ Chưa bắt đầu | `python/neuroedge/lab/` |
| **TSK-N5-03** | Đề xuất hỏng báo lỗi ba phần, không ghi tệp rác | — | — | ⏳ Chưa bắt đầu | `python/neuroedge/lab/` |
| **TSK-N5-05** | `trace export --report` và tool `lab_report` Markdown | FR-TRC-* | — | ⏳ Chưa bắt đầu | `python/neuroedge/cli/main.py` |
| **TSK-N5-06** | `neuroedge lab check` trong Action CI trên PR | FR-CI-*, FR-DX-10 | — | ⏳ Chưa bắt đầu | `python/neuroedge/lab/` |
| **TSK-N6-01** | Giá trị `call_source` mới `trigger` | FR-MDL-10 | — | ⏳ Chưa bắt đầu | `actions/tools.py` |
| **TSK-N6-02** | `trigger ∉ HUMAN_SOURCES`, khẳng định không trả lời `ask` | Q-26 | — | ⏳ Chưa bắt đầu | `actions/confirmation.py` |
| **TSK-N6-03** | Debounce và trần tần suất trigger, tránh thử lại vô hạn | — | — | ⏳ Chưa bắt đầu | `python/neuroedge/lab/` |
| **TSK-N6-04** | Tool `lab_trigger_check`: chấm khai báo trigger nháp | FR-DX-10 | — | ⏳ Chưa bắt đầu | `python/neuroedge/lab/` |

- [ ] **Tiêu chí N0.4:** `lab doctor` cảnh báo trên gpio-sim khi user của client nằm trong nhóm `gpio`.

**Tiêu chí ra I2d:**

- [ ] **Tiêu chí 1:** RFC dự kiến I2d Đã chấp thuận; `schemas/` chỉ đổi trong phạm vi RFC đó.
- [ ] **Tiêu chí 2 (A15, A17):** 100% hợp đồng mâu thuẫn bị từ chối; 100% lệnh vi phạm bị chặn.
- [ ] **Tiêu chí 3 (A16, A19):** Kịch bản 30 ngày trên G1: phản xạ và cảnh báo mẫu cứng vẫn chạy; chi phí dưới trần.
- [ ] **Tiêu chí 4 (A18):** Đích không khai bị chặn và ghi vết 100%; không rò ảnh khi cấm.
- [ ] **Tiêu chí 5 (A20):** Lời duyệt sai nguồn, hết hạn, nonce cũ, digest lệch đều bị từ chối.
- [ ] **Tiêu chí 6 (A21):** `safe_state: on` thiếu liên động bị từ chối; profile hiện có giữ chuỗi phán quyết.
- [ ] **Tiêu chí 7 (A22):** Replay tái hiện 100% phán quyết từ chuỗi vết ghi 30 ngày.
- [ ] **Tiêu chí 8:** Runtime chạy liên tục trên G2; client MCP dựng hợp đồng qua tool lab, người khoá.
- [ ] **Tiêu chí 9:** Bước xác minh do người dùng khai (đọc mã trên `sim`) chạy hết đường; LLM và client MCP trả lời bước xác minh đều bị từ chối 100% (Q-73).
- [ ] **Tiêu chí 10:** Bộ não NeuroEdge nói chuyện với runtime chỉ qua MCP; worker bị chiếm (lệnh shell, prompt injection) không bật được chân nào trên G2 (Q-76).
- [ ] **Tiêu chí 11:** `pytest` xanh, 0 skipped; `wheel_smoke.sh` đạt; demo trong `demo/`.

### 4.3.5 I2e — NeuroEdge Blueprint tối thiểu

| | |
|:---|:---|
| **Mục tiêu** | Vòng ③ của Q-72 trên giả lập: maker đóng Blueprint bằng `blueprint pack`, người cài bằng `blueprint install` |
| **Điều kiện vào** | I2d đạt tiêu chí 2→7 trên G1; task mã chờ RFC được ký |
| **Tín hiệu đo** | A14; B6, B7, B8 (PRD §11.2) |
| **Người** | V3 (chủ trì), V1, V7; trưởng nhóm; kỹ thuật trưởng |
| **Thiết kế** | Q-72 · PRD §7.4, §8.4 · chương kiến trúc 15 §6.4 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I2e-01** | RFC `blueprint.v1`: khai báo, digest phủ toàn gói | FR-BP-01, FR-BP-04, FR-BP-06, FR-BP-08 | V1 + kỹ thuật trưởng | ⏳ Chưa bắt đầu | `docs/rfc/` |
| **TSK-I2e-02** | `neuroedge blueprint pack` gói dự án thành Blueprint | FR-BP-02, FR-CLI-13 | V3 | ⏳ Chờ TSK-I2e-01 | `python/neuroedge/blueprint/` |
| **TSK-I2e-03** | `neuroedge blueprint install` kiểm digest, hiện bản duyệt | FR-BP-03, FR-CLI-13, NFR-SEC-14 | V3 + V1 | ⏳ Chờ TSK-I2e-01 | `python/neuroedge/blueprint/` |
| **TSK-I2e-04** | Index Blueprint tĩnh git/HTTPS không thu phí | FR-BP-05 | V3 | ⏳ Chưa bắt đầu | kho index ngoài repo |
| **TSK-I2e-05** | Kit bể cá: BOM, sơ đồ đấu dây, hợp đồng mẫu, vết ghi | FR-DX-09 | V3 + V7 | ⏳ Chưa bắt đầu | `python/neuroedge/templates/` |
| **TSK-I2e-06** | BOM có liên kết hoa hồng nằm trang riêng ngoài kit | FR-BP-07 | trưởng nhóm + V3 | ⏳ Chưa bắt đầu | `docs/user/` |
| **TSK-I2e-07** | Mốc đo của cổng ghi tại chỗ, chỉ gửi khi bật | FR-TEL-07 | V3 | ⏳ Chưa bắt đầu | `python/neuroedge/` |
| **TSK-I2e-08** | Wheel cho người thử ngoài kèm bước blueprint install | FR-DX-02 | V3 | ⏳ Chưa bắt đầu | `scripts/wheel_smoke.sh` |
| **TSK-I2e-12** | Add-on Home Assistant chạy runtime, không gõ lệnh (Q-74) | FR-DX-02, FR-AGT-01 | V3 | ⏳ Chờ TSK-I2d-16 | kho add-on ngoài repo |
| **TSK-I2e-13** | Ảnh thẻ SD cho Pi, ghép đôi Telegram bằng mã QR (Q-74) | FR-DX-02, FR-CH-03 | V3 | ⏳ Chờ TSK-I2d-12 | `scripts/` · `docs/user/` |
| **TSK-I2e-14** | `neuroedge new --layout host+mcu`: khung dự án Pi + ESP32 (Q-75) | FR-DX-01, FR-BP-02 | V3 | ⏳ Chưa bắt đầu | `python/neuroedge/templates/` |
| **TSK-I2e-09** | Buổi đo cài Blueprint (A14) trên 3 người ngoài đội | FR-DX-01 | V3 + người | ⏳ Chưa bắt đầu | `docs/reports/` |
| **TSK-I6-04** | Kênh cộng đồng trên diễn đàn HA/ESPHome, quy trình lỗi | — | V3 + trưởng nhóm | ⏳ Chưa bắt đầu | bài đăng, kênh phản hồi |
| **TSK-I2e-10** | Phỏng vấn cho cổng: ≥ 10 người (≥ 5 maker) | — | trưởng nhóm | ⏳ Chưa bắt đầu | `docs/business/` |
| **TSK-I2e-11** | Cổng nhu cầu 8 tuần (B6, B7, B8), ghi nhánh | — | trưởng nhóm + chủ sản phẩm | ⏳ Chưa bắt đầu | `roadmap/neuroedge-prd.md` §15 |

**Tiêu chí ra I2e:**

- [ ] **Tiêu chí 1:** RFC `blueprint.v1` Đã chấp thuận.
- [ ] **Tiêu chí 2 (A14):** Người ngoài cài Blueprint bể cá trên `sim` dưới 10 phút.
- [ ] **Tiêu chí 3:** `blueprint pack` và `install` cùng chuỗi phán quyết; digest lệch từ chối.
- [ ] **Tiêu chí 4:** Index tĩnh liệt kê Blueprint bể cá; kit qua test; BOM liên kết nằm ngoài.
- [ ] **Tiêu chí 5:** Cổng 8 tuần đo xong, một Q-N ghi nhánh đã chọn.
- [ ] **Tiêu chí 6:** Người thử dựng hộp tại nhà bằng add-on Home Assistant hoặc thẻ SD, ghép đôi bằng QR, không gõ lệnh (Q-74).
- [ ] **Tiêu chí 7:** `pytest` xanh, 0 skipped; `wheel_smoke.sh` đạt.

### 4.3.6 I2f — NeuroEdge Cloud và hộp tại nhà ESP32

**Có điều kiện (Q-74 bước 2).** Chỉ mở khi kết quả cổng nhu cầu 2026-12-06 cho thấy người thử vướng ở cài đặt, khoá API hay tự host; không mở thì giữ ⏸, không cắt. **Mục tiêu:** người dùng chỉ cần chat — "não" (LLM worker, trò chuyện, biên dịch hợp đồng nhiệm vụ) chạy trên NeuroEdge Cloud tuỳ chọn và điều phối nhiều thiết bị, nhiều nhà, nhiều người; "tuỷ sống" (gate, phản xạ, kiểm lời duyệt, cửa ra dữ liệu, vết ghi) luôn ở hộp tại nhà. **Thiết kế:** Q-74 · PRD FR-AGT-10, FR-AGT-11, FR-CH-07 · `docs/architecture/vi/15-target-architecture.md` §6.10 · `docs/spec/threat_model.md` §2k. **Phụ thuộc:** I2e.

| Mã Task | Mô tả | Yêu cầu | Người | Trạng thái | Bằng chứng |
|:---|:---|:---|:---|:---|:---|
| **TSK-I2f-01** | RFC kênh cloud ↔ hộp: luật có ký, lời duyệt kiểm tại nút, trần phạm vi lệnh | FR-AGT-10, FR-AGT-11 | V1 + kỹ thuật trưởng | ⏸ Chờ cổng nhu cầu (Q-74) | `docs/rfc/` |
| **TSK-I2f-02** | Cổng kênh chat chung và relay: chat ↔ instance, hộp ↔ instance, trần token theo gói (Q-76) | FR-AGT-10, NFR-COST-01 | V1 + V3 | ⏸ Chờ TSK-I2f-01 | dịch vụ ngoài repo |
| **TSK-I2f-07** | Instance bộ não cách ly mỗi người (microVM), ngủ khi rảnh, trí nhớ mã hoá riêng | FR-AGT-12, NFR-SEC-* | V1 | ⏸ Chờ TSK-I2f-02 và TSK-I2d-22 | dịch vụ ngoài repo |
| **TSK-I2f-08** | Lời duyệt ký trên điện thoại (passkey), hộp tại nhà tự kiểm chữ ký | FR-CH-08, FR-CH-04 | V1 + V3 | ⏸ Chờ TSK-I2f-01 | `python/neuroedge/channels/` |
| **TSK-I2f-09** | Spike: RAM, thời gian thức và giá mỗi instance nghỉ, trước khi định giá | NFR-COST-01 | V1 | ⏸ Chờ cổng nhu cầu (Q-74) | `docs/reports/` |
| **TSK-I2f-03** | Hộp ESP32-S3: Wi-Fi thật, nhận luật biên dịch có ký, kiểm lời duyệt trên chip | FR-AGT-10, FR-OTA-* | V2 | ⏸ Chờ TSK-I2f-01 và bo mạch | `targets/esp32s3/` |
| **TSK-I2f-04** | Mạng lưới đa nút, đa nhà: danh tính từng nút, trần phạm vi, tự khoá khi bất thường | FR-AGT-11 | V1 | ⏸ Chờ TSK-I2f-01 | `python/neuroedge/agent/` |
| **TSK-I2f-05** | Nhiều người trong một ô chat, vai trò có hạn (cùng RFC ghép đôi `TODOS.md` #62) | FR-CH-07, FR-CH-03 | V1 + V3 | ⏸ Chờ TSK-I2f-01 | `python/neuroedge/agent/` |
| **TSK-I2f-06** | Rà soát bảo mật cloud theo threat model §2k trước người dùng đầu tiên | NFR-SEC-* | V1 + người ngoài | ⏸ Chờ TSK-I2f-02 | `docs/reports/` |

**Tiêu chí ra I2f:**

- [ ] **Tiêu chí 1:** RFC kênh cloud ↔ hộp Đã chấp thuận; N4 và hệ quả "máy chủ" của Q-10 sửa trong cùng PR.
- [ ] **Tiêu chí 2:** Cắt kết nối cloud: phản xạ, gate và cảnh báo tại chỗ vẫn chạy trên G1, G2.
- [ ] **Tiêu chí 3:** Cloud gửi luật không ký hay lời duyệt không kiểm được: hộp từ chối 100%, ghi vết.
- [ ] **Tiêu chí 4:** Một ô chat điều phối ≥ 2 nhà giả lập; lệnh vượt trần phạm vi bị chặn.
- [ ] **Tiêu chí 5:** Cloud gửi "Đồng ý" không có chữ ký passkey: hộp từ chối 100%, ghi vết (FR-CH-08).
- [ ] **Tiêu chí 6:** Cùng một bản bộ não chạy tự host trên board Linux rẻ và trên NeuroEdge Cloud, không rẽ nhánh mã; instance của hai người không đọc được trí nhớ của nhau (Q-76).
- [ ] **Tiêu chí 7:** `pytest` xanh, 0 skipped; rà soát bảo mật không còn lỗi mức cao.

### 4.4 I3 — Gate trên Box-3 thật

| | |
|:---|:---|
| **Mục tiêu** | Gate chạy trên ESP32-S3-Box-3 thật và điều khiển chân thật; người dùng tự nạp agent; `verify` ba target bậc 1 cho miền phán quyết (U2/J3 → M3, A2) |
| **Điều kiện vào** | Box-3 trong tay |
| **Tín hiệu đo** | `verify --targets sim,linux,esp32s3` trên bo mạch |
| **Người** | V2 (chủ trì), V6, V1, V3 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S1-10** | Spike khả thi bộ nhớ trên ESP32-S3-Box-3 | NFR-RES-01, NFR-RES-02 | V2 | 🔴 Chờ bo mạch | `targets/esp32s3/main/memory_probe.c` · `docs/reports/memory_spike_report.md` |
| **TSK-S2-10** | Kết luận kế hoạch thoại trên chip dựa trên spike | — | V2 + trưởng nhóm | ⏳ Chờ số đo TSK-S1-10 | `docs/reports/memory_spike_report.md` |
| **TSK-S4-01** | Port 5 nguyên thủy HAL lên ESP-IDF | FR-TGT-03, FR-HAL-01 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/hal/` |
| **TSK-S4-02** | Gate Engine walker C99 duyệt `NETR` v1 trên MCU | FR-ACE-01, FR-ACE-03, FR-ACE-08 | V2 + V1 | ✅ 2026-09-24 | `targets/esp32s3/components/ne_gate/` |
| **TSK-S4-03** | Đường dẫn `digital.out` và `sensor.read` trên phần cứng | FR-HAL-06, FR-HAL-07 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/drivers/` |
| **TSK-S4-04** | Lệnh `neuroedge verify` cho cả 3 target bậc 1 | FR-CI-07, FR-TGT-04 | V1 | 🟡 QEMU chạy được; còn bo mạch | `python/neuroedge/cli/main.py` |
| **TSK-S4-05** | Runner kiểm thử nightly trên bo mạch thật | FR-CI-06, NFR-REL-03 | V3 | ⏳ Chưa bắt đầu | `.github/workflows/nightly-hardware.yml` |
| **TSK-S4-07** | Walker C biên dịch trên host gcc/clang ASan/UBSan | FR-ACE-01, FR-CI-07 | V2 | ✅ 2026-09-24 | `python/tests/test_c_walker.py` |
| **TSK-S4-08** | Smoke test firmware trên Espressif QEMU | FR-CI-06, FR-TGT-03 | V2 | ✅ 2026-09-24 | `.github/workflows/firmware-qemu.yml` |
| **TSK-S4-09** | Vết ghi từ firmware qua UART và record --target esp32s3 | FR-CI-01, FR-TGT-04, FR-CLI-04 | V2 + V1 | ✅ 2026-09-25 | `targets/esp32s3/components/ne_trace/` |
| **TSK-S4-10** | Ảnh golden cho giao diện LVGL trên host | FR-HAL-01, FR-CI-05 | V2 | ✅ 2026-09-26 | `targets/esp32s3/ui/` · `scripts/run_ui_golden.sh` |
| **TSK-S4-11** | Ngân sách RAM tĩnh trên mỗi PR (`idf.py size`) | NFR-RES-01, NFR-RES-02 | V2 | 🟡 Đạt RAM tĩnh; còn link ESP-SR AFE | `scripts/check_firmware_size.py` |
| **TSK-S4-12** | Bài kiểm ngày đầu có bo mạch (codec, loa, mic, GPIO) | FR-PER-06, FR-HAL-06 | V2 | ⏳ Khi bo mạch về | `targets/esp32s3/tests/bringup/` |
| **TSK-I3-01** | Đường nạp firmware cho agent của người dùng | FR-CLI-02, FR-TGT-03 | V2 | ✅ 2026-09-26 | `python/neuroedge/engine/firmware.py` |
| **TSK-I3-02** | Spike `esp-emulator` cho ngoại vi `esp32s3` | FR-CI-06, FR-TGT-03 | V2 | ⏳ Chưa bắt đầu | `docs/reports/` |
| **TSK-I3-03** | Spike `esp32sim`: ước lượng sớm bộ nhớ thoại và thị giác | NFR-RES-01, NFR-RES-02 | V2 | ⏳ Chưa bắt đầu | `docs/reports/` |

*Mã TSK-S4-06 chưa từng được cấp; các mã còn lại giữ nguyên.*

**Tiêu chí ra I3:**

- [ ] 🔴 **Tiêu chí 1:** Báo cáo spike bộ nhớ có số liệu đo thực đối chiếu ngưỡng Q-3 (SRAM ≥ 120 KB, PSRAM ≥ 2 MB, flash ≤ 3,5 MB).
- [ ] **Tiêu chí 2 (A2):** `verify --targets sim,linux,esp32s3` đạt 100% trên kịch bản không dùng audio.
- [x] **Tiêu chí 3:** Sai lệch phán quyết giữa các target sinh `SafetyRegressionError` (NE4002).
- [ ] **Tiêu chí 4:** Nightly runner chạy tự động và gửi báo cáo.
- [ ] **Tiêu chí 5:** Người ngoài đội tự build và nạp agent của mình lên Box-3 theo tài liệu.

### 4.4.1 I3a — Nguyên thủy mở rộng trên `esp32s3`

| | |
|:---|:---|
| **Mục tiêu** | Bốn gói nguyên thủy mở rộng chạy trên chip: Box-3 cho cảm biến, PWM, chuyển động; CoreS3 cho thị giác (Q-53, Q-61). Liên kết Pi ↔ ESP32 tối thiểu và bo ESP32-S3 phổ thông cho maker (Q-75) |
| **Điều kiện vào** | Box-3 và bo camera đã về (Phụ lục B) |
| **Tín hiệu đo** | Tiêu chí ra bên dưới |
| **Người** | V2 (chủ trì), V6, V5 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I3a-01** | Bo ESP32-S3 camera làm bo tham chiếu thứ hai (Q-61) | FR-HAL-02, NFR-RES-02 | V2 | 🟡 Đã chọn M5Stack CoreS3; còn mua, profile, đo | `boards/` · `docs/reports/` |
| **TSK-I3a-02** | HAL C: `digital.in`, bus I2C chỉ đọc, `analog.in` trên ESP-IDF | FR-HAL-01, FR-TGT-03 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/hal/` |
| **TSK-I3a-03** | HAL C: PWM (LEDC) trong `digital.out` theo RFC-0010 | FR-HAL-01 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/hal/` |
| **TSK-N7-02** | Cưỡng chế phong bì trong firmware C, thiếu từ chối fail-closed | — | — | ⏳ Chưa bắt đầu | `targets/esp32s3/components/` |
| **TSK-W1-04** | Hiện thực `motion.*` trên `esp32s3` và test crash-safe | FR-HAL-01, FR-PER-02 | V2 | ⏳ Chưa bắt đầu | `targets/` · `docs/spec/voice_fsm.md` |
| **TSK-I3a-04** | `vision.in` trên bo camera ESP32-S3 theo RFC-0012 | FR-HAL-01 | V5 + V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/` |
| **TSK-I3a-05** | `verify --targets sim,linux,esp32s3` cho agent bốn gói | FR-CI-07 | V1 + V2 | ⏳ Chưa bắt đầu | `python/neuroedge/cli/main.py` |
| **TSK-I3a-06** | RFC node tối thiểu: một host ↔ một MCU qua serial, nhịp tim, mất liên lạc ⇒ `safe_state` (Q-75) | FR-TGT-08 | V1 + kỹ thuật trưởng | ⏳ Chưa bắt đầu | `docs/rfc/` |
| **TSK-I3a-07** | Liên kết tối thiểu: hai tiến trình trên `sim`, rồi Pi 5 ↔ ESP32-S3; test cắt dây | FR-TGT-08, FR-HAL-01 | V2 + V1 | ⏳ Chờ TSK-I3a-06 | `python/` · `targets/esp32s3/` |
| **TSK-I3a-08** | Bo ESP32-S3 phổ thông (DevKitC, WROOM N16R8): profile, firmware không màn hình (Q-75) | FR-HAL-02, FR-TGT-03 | V2 | ⏳ Chưa bắt đầu | `boards/` · `targets/esp32s3/` |
| **TSK-I3a-09** | Thư viện Arduino (arduino-esp32) gói walker `NETR`, sổ token, phản xạ mất liên lạc (Q-75) | FR-TGT-03, FR-DX-09 | V2 | ⏳ Chờ TSK-I3a-08 | `targets/arduino/` |

**Tiêu chí ra I3a:**

- [ ] **Tiêu chí 1:** `verify --targets sim,linux,esp32s3` đạt 100% cho agent mẫu mỗi gói trên Box-3 và bo camera.
- [ ] **Tiêu chí 2:** Firmware đủ nguyên thủy mở rộng cùng thoại giữ SRAM trống ≥ 120 KB (Q-3).
- [ ] **Tiêu chí 3:** Mất điện/reset giữa lệnh `motion.*` trên bo thật thì cơ cấu về trạng thái an toàn.
- [ ] **Tiêu chí 4:** Phong bì cưỡng chế trong firmware, action gắn phong bì bị từ chối nếu thiếu.
- [ ] **Tiêu chí 5:** Cắt dây serial giữa host và ESP32 ⇒ mọi cơ cấu về `safe_state` trong thời hạn đã khai, có vết ghi; đạt trên `sim` hai tiến trình và trên bo thật (Q-75).
- [ ] **Tiêu chí 6:** Bo ESP32-S3 WROOM phổ thông chạy gate đã khoá và từ chối đúng corpus, không cần Box-3, cả từ firmware ESP-IDF lẫn sketch Arduino (Q-75).

### 4.7 I6 — Công khai

| | |
|:---|:---|
| **Mục tiêu** | Lần đầu người ngoài dùng được sản phẩm: repo công khai, `pip install neuroedge` từ PyPI, demo bốn gói và Blueprint (Q-39, Q-52, Q-77) |
| **Điều kiện vào** | Điều khoản license thương mại (`TODOS.md` #44) |
| **Tín hiệu đo** | Lượt cài đầu tiên từ PyPI; người ngoài đầu tiên chạy agent (B1 bắt đầu đếm) |
| **Người** | V3 (chủ trì), trưởng nhóm, V2, V1 |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S3-14** | Workflow release lên PyPI, kiểm `pip install` và chạy | FR-DX-02, FR-GOV-01 | V3 | 🟡 Sẵn workflow; go-live khi công khai | `.github/workflows/release-pypi.yml` |
| **TSK-S3-09** | Telemetry CLI ẩn danh, có thể tắt | FR-TEL-01, FR-TEL-02 | V3 | ⏳ Chưa bắt đầu | `python/neuroedge/cli/` |
| **TSK-W0-02** | SBOM CycloneDX/SPDX gắn vào mỗi bản phát hành | — | V3 | ✅ 2026-09-26 | `scripts/sbom.sh` |
| **TSK-W0-03** | Quét lỗ hổng và bí mật: pip-audit, gitleaks toàn lịch sử | — | V3 | ✅ 2026-09-26 | `.github/workflows/security.yml` |
| **TSK-I6-01** | Toàn bộ kho public từ 2026-09-25 | FR-GOV-01 | trưởng nhóm + V3 | ✅ 2026-09-25 | repo public |
| **TSK-I6-02** | Lược đồ ở URL công khai `schema.neuroedge.dev` | FR-GOV-01, FR-GOV-02 | V3 | ⏳ Chưa bắt đầu | tên miền · `schemas/` |
| **TSK-I6-03** | Video demo bốn gói và Blueprint trên `sim`, `linux` và Box-3 | FR-DX-06 | V3 + V2 | ⏳ Chưa bắt đầu | `README.md` |
| **TSK-P2-04** | MCP qua mạng có xác thực mTLS + OAuth 2.1 | NFR-SEC-09, FR-CLI-12 | V1 | ✅ 2026-10-04 | `python/neuroedge/mcp_http.py` |
| **TSK-I6-05** | Đóng băng hợp đồng Gated Tool Profile và `board.v1` | FR-MDL-10, FR-GOV-01, FR-GOV-02, FR-HAL-02 | V1 | ✅ 2026-10-04 | RFC-0015 · `schemas/` |
| **TSK-I6-06** | Bề mặt Python công khai `docs/spec/python_api.md` | FR-DX-02, FR-GOV-03 | V1 | ✅ 2026-10-03 | `python/neuroedge/__init__.py` |
| **TSK-I6-07** | RFC dữ kiện từ tiến trình ngoài (RFC-0014) | FR-MDL-04, FR-MDL-10 | V1 | ✅ 2026-10-04 | `docs/rfc/0014-du-kien-tu-tien-trinh-ngoai.md` |

**Tiêu chí ra I6:**

- [x] **Tiêu chí 1:** Gitleaks quét toàn lịch sử repo 0 phát hiện.
- [x] **Tiêu chí 2:** Repo công khai; README và CONTRIBUTING trỏ đúng kho.
- [ ] **Tiêu chí 3:** `pip install neuroedge` từ PyPI chạy được `gate lint` và `trace validate`.
- [ ] **Tiêu chí 4:** `schema.neuroedge.dev` phục vụ mọi lược đồ trong `schemas/`.
- [ ] **Tiêu chí 5:** README có video demo bốn gói và Blueprint trên ba target.
- [ ] **Tiêu chí 6:** Telemetry opt-in chạy, có thông báo lần đầu; đo B1, B4, B5.
- [ ] **Tiêu chí 7:** Client MCP trên máy khác gọi qua Streamable HTTP + OAuth 2.1 + mTLS.
- [x] **Tiêu chí 8:** Gated Tool Profile, phiên bản `board.v1` và mã lỗi vào `schemas/`.
- [x] **Tiêu chí 9:** Bề mặt Python công khai có thật, dự án ngoài chỉ import neuroedge chạy được.
- [x] **Tiêu chí 10:** RFC dữ kiện từ tiến trình ngoài được chấp thuận.

### 4.8 I7 — v1.0

| | |
|:---|:---|
| **Mục tiêu** | v1.0 = lần ra mắt MVP (Q-52, Q-77): đủ tiêu chí PRD §11.1 |
| **Điều kiện vào** | — |
| **Tín hiệu đo** | PRD §11.1 |
| **Người** | V2, V6, V1, V3 |

OTA làm trước trên QEMU (Q-39). Phần tải qua mạng thật, Secure Boot cần bo mạch.

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S6-01** | OTA cấp thiết bị phân vùng kép A/B | FR-OTA-01 | V2 | ✅ 2026-09-26 | `targets/esp32s3/components/ne_ota/` |
| **TSK-S6-02** | Tự động rollback khi phát hiện vòng lặp khởi động | FR-OTA-02 | V2 | ✅ 2026-09-26 | `targets/esp32s3/components/ne_ota/` |
| **TSK-S6-03** | Xác minh chữ ký firmware RSA-3072 trên chip | FR-OTA-03 | V2 | 🟡 Xong phần cập nhật QEMU; còn Secure Boot eFuse | `targets/esp32s3/components/ne_ota/` |
| **TSK-S6-04** | Nạp firmware từ HTTP endpoint mở bất kỳ | FR-OTA-04 | V2 | ✅ 2026-09-26 | `targets/esp32s3/components/ne_ota/` |
| **TSK-S6-05** | Secure boot, mã hóa flash, nút ngắt micro vật lý | NFR-SEC-02, NFR-SEC-03 | V2 | ⏳ Chưa bắt đầu | `targets/esp32s3/security/` |
| **TSK-S6-06** | Kiểm thử chịu tải 24 giờ | NFR-RES-01, A6 | V3 | ⏳ Chưa bắt đầu | `tests/stress/` |
| **TSK-S6-07** | Publish JSON Schema công khai và bộ test tuân thủ | FR-GOV-01, FR-GOV-03, FR-TRC-10, A9 | V1 | ⏳ Chưa bắt đầu | `schemas/`, `fixtures/compliance/` |
| **TSK-S6-08** | Hoàn thiện tài liệu, ví dụ, video minh họa | FR-DX-05, FR-DX-06, A8 | V3 | ⏳ Chưa bắt đầu | `docs/`, `examples/` |
| **TSK-W0-01** | Tiêu chí nghiệm thu cho NFR-SEC-02→06, 08 | NFR-SEC | V1 | ⏳ Chưa bắt đầu | `neuroedge-prd.md` Phụ lục A.3 |
| **TSK-W2-07** | SBOM kèm phát hành, attestation, ghim Action SHA | — | V3 | ✅ 2026-09-26 | `.github/workflows/release-pypi.yml` |
| **TSK-I7-01** | Rà soát MECE các FR v1.0 chưa có task | FR-TGT-05, FR-TGT-07, FR-DX-07, FR-CLI-08 | V1 + V3 | ⏳ Chưa bắt đầu | `neuroedge-prd.md` |
| **TSK-I7-02** | Đo A1 chính thức (10 người) và A9 (bên thứ ba) | FR-DX-01, FR-GOV-01 | V3 | ⏳ Chưa bắt đầu | `docs/reports/` |

**Tiêu chí ra I7 — cổng phát hành v1.0:**
Đạt toàn bộ tiêu chí PRD §11.1 (A11 đã bỏ cùng Lab theo Q-77):

- [ ] **A1** — Time-to-first-value
- [ ] **A2** — Tương đương môi trường (`verify --targets sim,linux,esp32s3`)
- [ ] **A3** — Không có đường tắt tới actuator
- [ ] **A4** — Fail-closed (mất mạng lượng giá qua fallback cục bộ)
- [ ] **A5** — Kế thừa gate an toàn
- [ ] **A6** — Độ ổn định 24 giờ trên vi điều khiển (gate, nguyên thủy, liên kết; không thoại — Q-77)
- [ ] **A7** — Vết ghi hợp lệ
- [ ] **A8** — Tài liệu
- [ ] **A9** — Lược đồ công khai
- [ ] **A10** — Đủ nguyên thủy trên ba target (bốn gói mở rộng)
- [ ] **A12** — Kit mẫu dựng được trong một ngày

---

## 5. Developer Beta và điểm rẽ (I8)

### 5.1 I8 — Developer Beta

| | |
|:---|:---|
| **Mục tiêu** | 50–100 lập trình viên ngoài dùng `1.0.x`; đo B1–B5 và chọn nhánh |
| **Điều kiện vào** | — |
| **Tín hiệu đo** | B1–B5 (§5.5) |
| **Người** | Cả đội |

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I8-01** | Báo cáo B1–B5 và khuyến nghị nhánh (§5.6) | FR-TEL-01 | trưởng nhóm | ⏳ Chưa bắt đầu | một `Q-N` chọn nhánh |

**Tiêu chí ra I8:** B1–B5 được đo và ghi ở §5.5; một `Q-N` ghi nhánh đã chọn theo §5.6.

### 5.2 Nguyên tắc vận hành

> **Đóng băng tính năng mới trên dòng `1.0.x`** (R12, Q-39). Chỉ sửa lỗi chặn 10 phút và an toàn.

### 5.3 Phân bổ công sức

| Trọng tâm | Tỷ lệ | Người |
|:---|:---:|:---:|
| Hỗ trợ 1:1 qua Discord và GitHub | 50% | Cả đội |
| Hoàn thiện tài liệu theo vướng mắc thực tế | 25% | V3 |
| Sửa lỗi chặn | 20% | V1, V2 |
| Đo đạc và tổng hợp chỉ số | 5% | Trưởng nhóm |

### 5.4 Mục tiêu tuyển người dùng

| Mốc | Tích lũy | Kênh |
|:---:|:---:|:---|
| Ngay khi mở | 10 | Maker cộng đồng Home Assistant / ESPHome (U1, Q-72) |
| +1 tuần | 25 | Bài viết kỹ thuật kèm video demo |
| +2 tuần | 50 | Diễn đàn Home Assistant, ESPHome, ESP32 (U5) |
| +4 tuần | 50–100 | Tích lũy tự nhiên |

### 5.5 Chỉ số phải đo trong Beta

Ngưỡng ở PRD §11.2 (B1–B8) và §11.1 (A1); chỉ theo dõi trạng thái và ghi giá trị đo (Q-72).

| Mã | Chỉ số | Trạng thái | Nguồn đo |
|:---:|:---|:---:|:---|
| **B1** | Dev ngoài chạy agent trên `sim` | ⏳ Chưa bắt đầu | FR-TEL-01 (TSK-S3-09) |
| **B2** | Dev ngoài nạp phần cứng thật | ⏳ Chưa bắt đầu | FR-TEL-01 (TSK-S3-09) |
| **B3** | Gate do cộng đồng đóng góp (Q-41) | ⏳ Chưa bắt đầu | Repo công khai |
| **B4** | Tỷ lệ giữ lại và mở rộng test gate mặc định | ⏳ Chưa bắt đầu | Telemetry (TSK-S3-09) |
| **B5** | Tỷ lệ chuyển đổi `sim` → phần cứng | ⏳ Chưa bắt đầu | FR-TEL-01 (TSK-S3-09) |
| **A1** | TTFV đo trên 10 người độc lập | ⏳ Chưa bắt đầu | TSK-I7-02 |
| **B6** | Cổng 8 tuần — người ngoài tự cài Blueprint (Q-72) | ⏳ Chưa bắt đầu | TSK-I2e-09 |
| **B7** | Cổng 8 tuần — chạy liên tục 2 tuần trên G2/G3 | ⏳ Chưa bắt đầu | TSK-I2d-07 |
| **B8** | Cổng 8 tuần — maker muốn bán Blueprint | ⏳ Chưa bắt đầu | TSK-I2e-10 |

### 5.6 Điểm rẽ

**Trước Beta — cổng nhu cầu 8 tuần (Q-72):**
- **Đạt B6, B7, B8:** Blueprint thứ hai; Hub thu phí (FR-BP-10); xét lại phạm vi v1.0; mở I3 → I7.
- **Đạt B6, B7, trượt B8:** Giữ I2d, I2e làm công cụ cá nhân; không mở Hub thu phí; chọn nguồn thu khác; mở I3 → I7.
- **Trượt B6 hoặc B7:** Dừng tính năng mới vòng ② ③; đổi phân khúc trước khi viết thêm mã.

**Sau Beta:**
| Nhánh | Điều kiện | Hành động |
|:---|:---|:---|
| **Nhánh A — Mở rộng** | Đạt B1, B2 (Q-41) | Mở NeuroEdge Cloud (I2f) nếu chưa mở; xét lại các mục ở §6 bằng số đo Beta |
| **Nhánh B — Kéo dài 4–6 tuần** | Đạt 1 tiêu chí, tiêu chí kia ≥ 60% | Giữ đóng băng tính năng, tập trung tiêu chí yếu |
| **Nhánh C — Xem xét lại** | Không đạt tiêu chí nào / < 60% | Dừng lộ trình thương mại, phỏng vấn 20 người dùng |

Chỉ báo quan trọng nhất là B2 (10 người ngoài nạp phần cứng thật).

---

## 6. Đã bỏ khỏi roadmap (Q-77)

Q-77 (2026-10-12) bỏ khỏi roadmap mọi thứ không phục vụ hướng hiện tại: maker và nhà ở, ra lệnh qua chat, bộ não là hàng hoá, tuỷ sống ở nhà, Blueprint (Q-72, Q-74, Q-76). Không xoá thông tin: mã đã có giữ nguyên và vẫn chạy test; thiết kế cũ đọc bằng `git show 6670553:roadmap/neuroedge-roadmap.md`. Mở lại một mục cần một `Q-N` mới, kèm số đo của mốc mở lại.

| Đã bỏ | Vì sao | Mốc mở lại |
|:---|:---|:---|
| **I4, I5 — Thoại trên host và trên Box-3** | Câu chuyện là chat; XiaoZhi, ESP-Claw, Home Assistant Voice đã làm thoại. Mã thoại trên host (FSM, STT/TTS, `run --mic`) giữ nguyên | ≥ 3 người thử Blueprint xin điều khiển bằng giọng nói |
| **I4a, I5a — NeuroEdge Lab** | Dựng hợp đồng qua MCP do bộ tool chuẩn (TSK-I2d-23) cùng client MCP người dùng đang có đảm nhận | Người thử không tự viết được hợp đồng nhiệm vụ qua bộ tool chuẩn |
| **Mở danh sách target cho bên thứ ba** (V1a, TSK-I2c-13, I2c-17) | Tạm dừng từ Q-72; bo phổ thông và Arduino (Q-75) phủ nhu cầu thật | Bên thứ ba xin port target mới |
| **I9 — Provider tự host và Fleet OS** | Q-75: không làm quản lý đội thiết bị trước khi có người đòi; LiteLLM và bộ não (Q-76) lo phần gọi LLM | Một khách trả tiền cho quản lý ≥ 20 thiết bị |
| **I10 — Registry, đo lường, sandbox** | Blueprint Hub (I2e) là kênh phân phối | Hub tĩnh không đủ cho số Blueprint thật |
| **I13 — Bộ port cộng đồng** | Bo phổ thông và thư viện Arduino (I3a) phủ nhu cầu | Người ngoài xin port bo bậc 3 |
| **I14 — Robot phân tầng** (ROS 2, Nav2, RP2350, black channel) | Thị trường robot, không phải nhà; liên kết Pi ↔ ESP32 đã ở I3a (Q-75), mạng lưới nhà ở I2f | Một đội robot cam kết thử |
| **I16 Jetson, I17 đa phương thức, I18 hệ sinh thái thiết bị** | Không có tín hiệu nhu cầu; I18 phụ thuộc I9, I10 | Nhu cầu đo được sau Beta |
| **Khối 4 (AURA), Khối 5 (Marketplace thu phí)** | Ngoài phạm vi; Hub thu phí của Blueprint có đường riêng sau cổng (Q-72) | Như PRD §14 |

### Task của các phần đã bỏ

Giữ một dòng mỗi task để mã và tài liệu dẫn tới vẫn tra được; trạng thái là trạng thái cuối trước Q-77.

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S2-07** | Đặc tả chuẩn tắc máy trạng thái hội thoại | FR-PER-02, FR-PER-03 | V1 | ⏸ Ngoài roadmap (Q-77) — đã xong 2026-09-25 | `docs/spec/voice_fsm.md` |
| **TSK-S3-10** | Bộ vector kiểm thử tuân thủ cho FSM thoại | FR-CI-07, FR-TGT-04 | V1 | ⏸ Ngoài roadmap (Q-77) — đã xong 2026-09-25 | `fixtures/compliance/voice/` |
| **TSK-S3-11** | Hiện thực Python của máy trạng thái hội thoại | FR-PER-02→05 | V1 | ⏸ Ngoài roadmap (Q-77) — đã xong 2026-09-25 | `python/neuroedge/perception/` |
| **TSK-S3-13** | Tích hợp ASR/TTS qua provider cloud cho `sim` và `linux` | FR-MDL-09, FR-PER-07 | V1 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/perception/providers/` |
| **TSK-S5-08** | `audio.in` / `audio.out` trên `linux` qua PipeWire/sounddevice | FR-TGT-02, FR-PER-01 | V2 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/hal/linux.py` |
| **TSK-I4-01** | Fallback lệnh cục bộ và wake-word trên host | FR-PER-01, FR-MDL-03 | V1 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/perception/providers/wake.py` |
| **TSK-I4-02** | `SystemOne` đổi được bằng cấu hình | FR-MDL-04 | V1 | ⏸ Ngoài roadmap (Q-77) — đã xong 2026-09-26 | `python/neuroedge/models/providers/systemone_api.py` |
| **TSK-I4-03** | Độ trễ từng chặng và tỷ lệ System 1 / System 2 trong vết ghi | FR-ACE-06, FR-TEL-03, NFR-OBS-02 | V1 | ⏸ Ngoài roadmap (Q-77) — đã xong 2026-09-26 | `python/neuroedge/engine/latency.py` |
| **TSK-I4-04** | Phiên thoại thời gian thực trên laptop (`run --mic`) | FR-PER-01, FR-PER-02, FR-PER-07 | V1 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/hal/audio_live.py` |
| **TSK-N0-01** | Mục Q-71 cho NeuroEdge Lab qua MCP | — | V2 | ⏸ Ngoài roadmap (Q-77) — đã xong 2026-10-10 | `neuroedge-prd.md` §15 |
| **TSK-N0-04** | Cập nhật threat model cho lab action và MCP | NFR-SEC-09 | V2 | ⏸ Ngoài roadmap (Q-77) — đã xong 2026-10-10 | `docs/spec/threat_model.md` §2c |
| **TSK-N0-05** | Quy trình duyệt gate nháp `-draft` qua PR | FR-GATE-* | V2 | ⏸ Ngoài roadmap (Q-77) | `CONTRIBUTING.md` §3 |
| **TSK-N0-06** | Mở rộng Q-11 cho OFL-1.1 font và mục NOTICE IBM Plex | — | V2 | ⏸ Ngoài roadmap (Q-77) | `neuroedge-prd.md` Q-11 · `NOTICE` |
| **TSK-N1-01** | `lab_pulse` là action mẫu + gate giới hạn `duration_ms ≤ 2000` | FR-MDL-10 | V2 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-N1-03** | `neuroedge build --release` từ chối khi `[lab] enabled` | FR-CLI-02 | V2 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/cli/main.py` |
| **TSK-N1-06** | `board show --lab` và tool `lab_board` kiểm chân allow-list | FR-HAL-05 | V2 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/cli/main.py` |
| **TSK-N1-07** | Test ranh giới B-1 quét AST cấm `lab/` gọi HAL | — | V2 | ⏸ Ngoài roadmap (Q-77) | `python/tests/test_lab_boundary.py` |
| **TSK-N1-08** | `lab_read` trên primitive `digital.in` | FR-HAL-01 | — | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-N3-01** | Quét bus bằng read-byte, đọc chip ID, không đoán | FR-HAL-01 | — | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/hal/` |
| **TSK-N3-02** | Test I2C trên `i2c-stub` + `lm75`: thiết bị, NACK, timeout | FR-TGT-02 | — | ⏸ Ngoài roadmap (Q-77) — làm dở: Đạt chip có mặt; còn bus trống rỗng | `python/tests_linux/test_i2c_read.py` |
| **TSK-N4-01** | Sổ bàn làm việc ghi vai chân và chip ID | — | — | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-N4-02** | Tool `lab_board_draft` nhận profile board mới | FR-HAL-05 | — | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/hal/board.py` |
| **TSK-N4-03** | Cảnh báo chân đặc biệt theo MCU (strapping, flash, PSRAM) | — | — | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-N5-04** | PR của bản nháp in `gate explain` bằng lời kèm diff | — | — | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-N5b-01** | Xếp hàng ask cũ nhất trước, focus mặc định ở Huỷ | — | — | ⏸ Ngoài roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-02** | Mất kết nối SSE hiện banner vàng, mờ thiết bị | — | — | ⏸ Ngoài roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-03** | Hàng đang bật có thời gian còn lại, timeline theo chân | — | — | ⏸ Ngoài roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-04** | Thước phong bì màu theo % cửa sổ từ `board.v1` | — | — | ⏸ Ngoài roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-05** | Thẻ phán quyết huy hiệu 4 màu, bấm mở `gate explain` | — | — | ⏸ Ngoài roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-06** | Tiêu đề tab cần xác nhận, tua lại giữ ask/live hiện tại | — | — | ⏸ Ngoài roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-07** | Restyle cả trang sim, nhúng IBM Plex font | — | — | ⏸ Ngoài roadmap (Q-77) | `viz/assets/ui.css` |
| **TSK-I4a-01** | NeuroEdge Lab phủ bốn gói cho client MCP | FR-MDL-10, FR-DX-01 | V2 + V7 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-S5-01** | Tích hợp WebRTC AEC, libfvad (VAD), Opus streaming | FR-PER-06 | V2 | ⏸ Ngoài roadmap (Q-77) | `targets/esp32s3/audio/` |
| **TSK-S5-02** | Port đường dẫn audio thu/phát, không STT/TTS trên chip | FR-PER-01 | V2 | ⏸ Ngoài roadmap (Q-77) | `targets/esp32s3/drivers/audio_path.c` |
| **TSK-S5-03** | Hiện thực C/C++ FSM thoại theo `voice_fsm.md` | FR-PER-02, FR-PER-03, FR-PER-05 | V1 + V2 | ⏸ Ngoài roadmap (Q-77) | `targets/esp32s3/fsm/voice_fsm.c` |
| **TSK-S5-04** | Thu hồi lệnh actuator chưa thực thi khi bị cắt lời | FR-PER-02 | V1 + V2 | ⏸ Ngoài roadmap (Q-77) | `targets/esp32s3/fsm/actuator_abort.c` |
| **TSK-S5-05** | Tối ưu bộ nhớ theo ngân sách Q-3 | NFR-RES-01, NFR-RES-02 | V2 | ⏸ Ngoài roadmap (Q-77) | `targets/esp32s3/sdkconfig.defaults` |
| **TSK-S5-06** | Client streaming âm thanh lên provider cloud | FR-PER-07, FR-GW-04 | V2 | ⏸ Ngoài roadmap (Q-77) | `targets/esp32s3/audio/provider_client.c` |
| **TSK-S5-07** | Fallback cục bộ trên `esp32s3` (MultiNet hoặc TFLite Micro) | FR-MDL-03, FR-ACE-03, NFR-RES-01 | V2 | ⏸ Ngoài roadmap (Q-77) | `targets/esp32s3/fallback/` |
| **TSK-N7-01** | Lab action + gate trên chip qua walker C và sổ token | — | — | ⏸ Ngoài roadmap (Q-77) | `targets/esp32s3/` |
| **TSK-N7-03** | Port chọn lọc từ ESP-Claw sang ESP32-S3 | — | — | ⏸ Ngoài roadmap (Q-77) | `targets/esp32s3/` |
| **TSK-K2-01** | Provider self-host: một endpoint, credential, xoay khóa | FR-GW-01, FR-GW-02 | V4 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/models/providers/auth.py` |
| **TSK-K2-02** | Provider self-host: định tuyến đa NCC, failover, hạn mức | FR-GW-03, FR-GW-05, FR-TEL-06 | V4 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/models/providers/routing.py` |
| **TSK-K2-03** | Provider self-host: giao thức edge, vết ghi đồng nhất | FR-GW-04, FR-GW-06, FR-GW-07 | V4 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/models/providers/traces.py` |
| **TSK-K2-04** | Fleet: cấp phát danh tính và chứng chỉ thiết bị | FR-FLT-01 | V4 | ⏸ Ngoài roadmap (Q-77) | `services/fleet/provisioning.py` |
| **TSK-K2-05** | Fleet: sổ kiểm kê, giám sát sức khỏe, dashboard | FR-FLT-03, FR-FLT-06 | V4 | ⏸ Ngoài roadmap (Q-77) | `services/fleet/inventory.py` |
| **TSK-K2-06** | Fleet: cập nhật cấu hình, bí mật và gate từ xa | FR-FLT-04 | V4 | ⏸ Ngoài roadmap (Q-77) | `services/fleet/config_sync.py` |
| **TSK-K2-07** | Fleet: điều phối OTA canary 1% → 10% → 100% | FR-FLT-02 | V4 | ⏸ Ngoài roadmap (Q-77) | `services/fleet/canary.py` |
| **TSK-K2-08** | Fleet: tự động tải vết ghi sự cố về kho | FR-FLT-05 | V4 | ⏸ Ngoài roadmap (Q-77) | `services/fleet/trace_collector.py` |
| **TSK-K2-09** | Thu hồi chứng chỉ thiết bị | NFR-SEC-05 | V4 | ⏸ Ngoài roadmap (Q-77) | `services/fleet/` |
| **TSK-K3-01** | Định danh ổn định cho thiết bị, agent, gate | FR-REG-05 | V4 | ⏸ Ngoài roadmap (Q-77) | `services/registry/identity.py` |
| **TSK-K3-02** | Hệ đo lường theo lượt gọi agent và thẩm định gate | FR-REG-06, FR-TEL-04 | V4 | ⏸ Ngoài roadmap (Q-77) | `services/metering/engine.py` |
| **TSK-K3-03** | Manifest và chuẩn phiên bản SemVer | FR-REG-02, FR-GATE-10 | V4 | ⏸ Ngoài roadmap (Q-77) | `schemas/manifest.v1.json` |
| **TSK-K3-04** | Kho Gate công khai miễn phí | FR-REG-01 | V4 | ⏸ Ngoài roadmap (Q-77) | `services/registry/oci_store.py` |
| **TSK-K3-05** | Cơ chế phân quyền và sandbox | FR-REG-07 | V4 | ⏸ Ngoài roadmap (Q-77) | `services/registry/sandbox.py` |
| **TSK-K3-06** | Kho adapter kết nối provider do cộng đồng đóng góp | FR-REG-08 | V4 | ⏸ Ngoài roadmap (Q-77) | `services/registry/adapters.py` |
| **TSK-W2-04** | Ký gate và kiểm chữ ký trên thiết bị (OCI/ORAS); ký vết ghi | FR-REG-04 | V4 | ⏸ Ngoài roadmap (Q-77) | `services/registry/` |
| **TSK-P1-01** | Bộ vector tuân thủ độc lập ngôn ngữ, đóng gói ngoài repo | FR-GOV-03 | V1 | ⏸ Ngoài roadmap (Q-77) | `fixtures/compliance/portable/` |
| **TSK-P1-02** | Hướng dẫn port HAL: hợp đồng tối thiểu, tự kiểm chứng | FR-TGT-08, FR-GOV-03 | V3 | ⏸ Ngoài roadmap (Q-77) | `docs/porting/` |
| **TSK-P1-03** | Khung port mẫu cho vi điều khiển ngoài ESP32 | FR-TGT-08 | V3 | ⏸ Ngoài roadmap (Q-77) | `targets/_template/` |
| **TSK-P1-04** | Quy trình công nhận bậc 3: bên đóng góp tự chạy và công bố | FR-TGT-08 | V3 | ⏸ Ngoài roadmap (Q-77) | `docs/porting/tier3.md` |
| **TSK-P1-05** | `neuroedge board check <tệp>` đạt/thiếu so với bậc | FR-TGT-08 | V1 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/cli/` |
| **TSK-W2-01** | mTLS hoặc PSK giữa Pi và node | NFR-SEC-04 | V2 | ⏸ Ngoài roadmap (Q-77) | firmware · `python/` |
| **TSK-W2-03** | TPM cho Pi (`linux`) bổ sung Secure Boot | NFR-SEC-02, NFR-SEC-03 | V2 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/hal/linux.py` |
| **TSK-W3-01** | Spike Zenoh-pico ↔ Pi trên ESP32-S3 và RP2350 (Q-36) | — | V2 | ⏸ Ngoài roadmap (Q-77) | `docs/reports/` |
| **TSK-W3-02** | RFC-node: nhiều node, wire, black channel — mở rộng RFC tối thiểu TSK-I3a-06 | FR-TGT-08 | V1 | ⏸ Ngoài roadmap (Q-77) | `docs/rfc/` |
| **TSK-W3-03** | Lớp black channel: wrapper + watchdog + chống phát lại | NFR-SEC-09 | V1 + V2 | ⏸ Ngoài roadmap (Q-77) | `python/` + firmware |
| **TSK-W3-04** | Vết ghi hợp nhất đa node (phương án A, Q-32) | FR-TRC-05 | V1 | ⏸ Ngoài roadmap (Q-77) | `fixtures/compliance/multinode/` |
| **TSK-W3-06** | `verify` cho cụm node; lệch → NE4002 | FR-CI-07 | V1 | ⏸ Ngoài roadmap (Q-77) | CLI + CI |
| **TSK-W3-07** | Port RP2350 làm node thứ hai (Q-33): HAL C, walker C99 | FR-TGT-08 | V2 | ⏸ Ngoài roadmap (Q-77) | `targets/rp2350/` |
| **TSK-P2-05** | MCP cho MCU qua gateway; MCU tự lượng giá gate | FR-GW-01, FR-MDL-10 | V1 + V2 | ⏸ Ngoài roadmap (Q-77) | `docs/spec/tool_calling.md` §8 |
| **TSK-W4-01** | Cầu ROS 2 tại ranh giới gate (`linux`) + Nav2 (Q-34) | FR-MDL-10 | V1 | ⏸ Ngoài roadmap (Q-77) | `python/` |
| **TSK-W4-07** | RFC an toàn robot di động và C6 với người mua robot | — | V1 + trưởng nhóm | ⏸ Ngoài roadmap (Q-77) | `docs/rfc/` |
| **TSK-V2-01** | Port HAL lên Jetson Orin qua JetPack | FR-TGT-08, FR-HAL-01 | V5 | ⏸ Ngoài roadmap (Q-77) | `targets/jetson/hal/` |
| **TSK-V2-02** | Đường dẫn thị giác tăng tốc GPU, giữ trừu tượng | FR-MDL-04 | V5 | ⏸ Ngoài roadmap (Q-77) | `targets/jetson/vision/` |
| **TSK-V2-03** | `neuroedge verify` cho `jetson` trên miền phán quyết | FR-CI-07, FR-TGT-08 | V1 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/cli/main.py` |
| **TSK-V2-04** | Profile bo mạch `jetson-orin-nano` | FR-HAL-02 | V5 | ⏸ Ngoài roadmap (Q-77) | `boards/jetson-orin-nano.toml` |
| **TSK-V3-01** | Hợp nhất thoại, thị giác và cảm biến vào một FSM | FR-PER-01→05 | V1 + V5 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/perception/fusion/` |
| **TSK-V3-02** | Mở rộng bộ vector tuân thủ cho luồng đa phương thức | FR-CI-07 | V1 | ⏸ Ngoài roadmap (Q-77) | `fixtures/compliance/multimodal/` |
| **TSK-V3-03** | Gate đa phương thức | FR-GATE-03 | V1 | ⏸ Ngoài roadmap (Q-77) | `schemas/gate.v2.json` |
| **TSK-V3-04** | RFC ngữ nghĩa gate cho bằng chứng thị giác | FR-GATE-03 | V1 | ⏸ Ngoài roadmap (Q-77) | `docs/rfc/` |
| **TSK-P2-01** | Kho adapter và HAL port cộng đồng trên Registry | FR-TGT-08 | V3 | ⏸ Ngoài roadmap (Q-77) | `services/registry/ports.py` |
| **TSK-P2-02** | Hiển thị trạng thái tuân thủ adapter trên Fleet Dashboard | FR-FLT-03 | V3 | ⏸ Ngoài roadmap (Q-77) | `services/fleet/compliance_view.py` |
| **TSK-P2-03** | Chứng nhận phần cứng miễn phí, tự kiểm chứng | FR-GOV-03 | V3 | ⏸ Ngoài roadmap (Q-77) | `docs/porting/certification.md` |
| **TSK-I2c-13** | Template plugin và hướng dẫn viết plugin 30 phút | FR-EXT-02, FR-DX-04 | V3 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/templates/` |
| **TSK-I2c-17** | Bài kiểm bridge `neuroedge-muse` viết ở kho riêng | FR-EXT-02, FR-EXT-04 | V3 + người | ⏸ Ngoài roadmap (Q-77) | kho `neuroedge-muse` |
| **TSK-V1a-02** | Mở enum `target` ở hai lược đồ | FR-TGT-08 | V1 | ⏸ Ngoài roadmap (Q-77) | `schemas/board.v1.json` · `schemas/trace.v1.json` |
| **TSK-V1a-03** | Bậc máy đọc được `TARGET_TIERS` do lõi sở hữu | FR-TGT-08, FR-HAL-05 | V1 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/hal/board.py` |
| **TSK-V1a-04** | Thu hẹp ba bất biến kiểm thử theo bậc | FR-HAL-04, FR-TGT-08 | V1 | ⏸ Ngoài roadmap (Q-77) | `python/tests/test_boards.py` |
| **TSK-V1a-05** | CLI: `board validate`, `board show` | FR-HAL-05 | V1 | ⏸ Ngoài roadmap (Q-77) | `python/neuroedge/cli/main.py` |
| **TSK-V1a-06** | Cập nhật corpus phản chứng `unknown_target.json` | FR-TRC-08 | V1 | ⏸ Ngoài roadmap (Q-77) | `fixtures/traces/expected_errors.yaml` |

## 7. Hướng mở rộng sau Beta

Không còn increment nào sau I8 (Q-77). Các hướng cũ và mốc mở lại ở §6.

---

## 8. Ngoài roadmap

### 8.1 Phụ thuộc ngoài

Không còn (Q-77): Khối 4 và Khối 5 ở §6.

### 8.2 Task hoãn, chưa thuộc increment nào

| Mã Task | Hạng mục công việc | Yêu cầu PRD | Người | Trạng thái | Sản phẩm bàn giao (Artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S2-06** | Lượng giá `allow_when` trên nền CEL và biên dịch gate cho thiết bị (§3.8, Q-9) | FR-GATE-03 | V1 | ⏸ Hoãn — chưa thuộc increment nào (`TODOS.md` #42) | Dạng mapping đủ cho wedge; CEL biên dịch xuống cùng cây quyết định (Q-9) |

---

## 9. Thang cắt phạm vi

MVP không cắt phạm vi (Q-52): trượt thì dời ngày cùng PR có bằng chứng (R5). Phạm vi MVP là phạm vi sau Q-77.

### 9.1 Tuyệt đối không cắt

- Hợp đồng năng lực HAL; Gate Engine và fail-closed; lược đồ vết ghi và record/replay; Golden Reference.
- `sim` là target thật (không phải mock); nguyên tắc kế thừa gate an toàn.
- Phạm vi MVP (Q-52, Q-77): bốn gói nguyên thủy mở rộng trên ba target, kit mẫu, nhiệm vụ 24/7, bộ não qua MCP, Blueprint.
- Q-77 đã bỏ thoại, Lab, mở danh sách target và mọi increment sau Beta (§6); mở lại cần một `Q-N` mới.

### 9.2 Thoại không còn trong v1.0

Q-44 từng buộc thoại trên ESP32-S3 cho v1.0; Q-77 bỏ yêu cầu đó. Mã thoại đã có giữ nguyên.

### 9.3 Thang cắt trong từng increment

Không còn increment sau Beta (Q-77), nên không còn thang cắt.

---

## 10. Lịch chốt quyết định

Sổ quyết định là [PRD §15](neuroedge-prd.md#15-sổ-quyết-định-kiến-trúc-adr) — nội dung, lý do và phương án của mọi `Q-N` quy định tập trung tại đó (nguồn sự thật duy nhất). Khi hai tài liệu lệch nhau, PRD §15 đúng.

### 10.1 Các quyết định đã chốt

Toàn bộ các quyết định kiến trúc đã chốt (`Q-1` đến `Q-77`) được lưu trữ chi tiết tại [PRD §15](neuroedge-prd.md#15-sổ-quyết-định-kiến-trúc-adr).

### 10.2 Quyết định và RFC còn mở

| Hạn | Mã | Quyết định | Vì sao hạn đó | Người quyết | Trạng thái |
|:---:|:---:|:---|:---|:---:|:---:|
| Trước task mã của từng RFC | Q-72 | Viết và duyệt RFC cho `TODOS.md` #58, 5 RFC của I2d và `blueprint.v1` của I2e | Không RFC thì không có mã cho định dạng mới | Kỹ thuật trưởng | ⏳ Đang mở |
| Trước task kênh xác nhận của I2d | Q-73 | Viết và duyệt RFC bước xác minh và luồng nhiều bước do người dùng khai (TSK-I2d-20) | Bản ghi duyệt qua chat dùng cùng đường xác nhận | Kỹ thuật trưởng | ⏳ Đang mở |
| Kết quả cổng nhu cầu 2026-12-06 | Q-74 | Mở I2f — NeuroEdge Cloud (não trên cloud, thuê bao) và hộp ESP32 — hay giữ ⏸ (§4.3.6) | Chỉ mở khi số đo cho thấy người thử vướng ở cài đặt hay tự host | Chủ sản phẩm | ⏳ Đang mở |
| Kết quả cổng nhu cầu 2026-12-06 | `TODOS.md` #67 | Chốt câu định vị (một `Q-N` mới): ba thẻ thử trong phỏng vấn Maker | Thông điệp ngoài giữ nguyên tới khi có số liệu người nghe | Chủ sản phẩm | ⏳ Đang mở |
| Trước TSK-I2d-12 | `TODOS.md` #62 | Vòng đời ghép đôi kênh chat: ghép tại chỗ, thu hồi, trần duyệt | Tài khoản chat bị chiếm thì duyệt thay chủ | Chủ sản phẩm | ⏳ Đang mở |
| Trước G3 dùng cho B7/A16 | Q-21, Q-69 | Chọn tầng G3 (firmware ESP32 giả lập): Wokwi, QEMU, `esp-emulator` | Q-72 đưa G3 vào cổng 8 tuần | Kỹ thuật trưởng | ⏳ Đang mở |

*Chính sách phụ thuộc bắc cầu (Q-11):* Cấm phụ thuộc copyleft (GPL) vào lõi; job `licence-obligations` chạy `pip-licenses --fail-on` kiểm tra toàn bộ cây phụ thuộc trên mỗi PR.

---

## 11. Nhịp vận hành

### 11.1 Nhịp định kỳ

| Tần suất | Hoạt động | Từ |
|:---|:---|:---:|
| Hằng ngày | Đồng bộ ngắn 15 phút | I0 |
| Hằng tuần | Demo chạy thật trên phần cứng thật từ khi bo mạch về; rà soát chỉ báo sớm §12 | I0 |
| Hằng đêm | Kiểm thử tự động trên bo mạch thật | I3 |
| Mỗi increment | Nghiệm thu theo tiêu chí ra; một thẻ phát hành, một tín hiệu đo (Q-39) | I0 |
| Mỗi increment | Một demo chạy được có giao diện trong `demo/<increment>/` (Q-49) | I1 |

### 11.2 Định nghĩa hoàn thành

Một hạng mục chỉ hoàn thành khi đủ cả 5 điều kiện:
1. Mã đã review và hợp nhất.
2. Có kiểm thử tự động trong CI, gồm ít nhất một ca thất bại.
3. Tiêu chí nghiệm thu PRD tương ứng đã đạt.
4. `--help`, tài liệu, tiến độ, changelog cập nhật (`CONTRIBUTING.md` §8).
5. Thông báo lỗi nêu đủ: sai ở đâu, vì sao, xử lý thế nào.

### 11.3 Quy tắc bảo vệ đường găng

| Quy tắc | Nội dung |
|:---|:---|
| **Đóng băng lược đồ** | Đổi lược đồ cần RFC, phê duyệt và kịch bản di trú |
| **Không nợ an toàn** | Gate Engine và HAL không hợp nhất với ghi chú "sẽ sửa sau". Hành vi fail-closed đã test không phải là nợ (Q-17) |
| **Sai lệch tương đương là lỗi chặn** | `SafetyRegressionError` (NE4002) giữa các target dừng mọi việc khác tới khi xử lý xong |
| **Đóng băng tính năng trong Beta** | Dòng `1.0.x` trong I8: chỉ sửa lỗi chặn 10 phút và lỗi an toàn (R12) |

---

## 12. Chỉ báo sớm và ngưỡng can thiệp

| # | Chỉ báo | Ngưỡng vàng | Ngưỡng đỏ | Hành động khi đỏ |
|:---:|:---|:---|:---|:---|
| **1** | Đóng băng lược đồ | — | — | Đã qua ở I0 |
| **2** | Spike bộ nhớ | Còn dư < 30% | Không đủ chỗ cho 4 gói | Mở `Q-N` lập lại kế hoạch I3a, dời v1.0 |
| **3** | Sai lệch `verify` | 1 ca lệch | ≥ 3 ca lệch | Dừng tính năng, truy nguyên gốc kiến trúc |
| **4** | Dev Beta ngoài đội | 2 tuần < 25 người | 2 tuần < 10 người | Dừng tuyển, phỏng vấn sâu 10 người |
| **5** | Tỷ lệ B2 nạp phần cứng | < 20% B1 | < 10% B1 | Điều tra đường lên phần cứng; chỉ báo nhánh C |
| **6** | Áp dụng Action CI | < 40% | < 25% | Xem lại scaffold và tài liệu Action CI |
| **7** | Cài Blueprint (B6) | I2e xong chưa ai cài | 2 tuần trước cổng < 3 người | Gặp từng người đo buổi cài (TSK-I2e-09), sửa điểm nghẽn |
| **8** | Chạy liên tục G2 (B7) | Dài nhất < 7 ngày khi còn 3 tuần | Không đủ 2 tuần liên tục | Dừng tính năng mới, sửa runtime G2 (TSK-I2d-16) |
| **9** | Bán Blueprint (B8) | 4 tuần chưa maker nào | Tới ngày cổng vẫn 0 | Ghi nhánh "đạt B6, B7, trượt B8" (§5.6) |
| **10** | Chi phí LLM bể cá | ≥ 50% NFR-COST-01 | Vượt NFR-COST-01 | Thêm bộ phát hiện tất định, hạ tần suất LLM |

Ngưỡng vàng thảo luận trong rà soát tuần. Ngưỡng đỏ kích hoạt hành động ngay.

---

# Phụ lục

## Phụ lục B — Danh mục mua sắm và hạ tầng

I2d, I2e chạy trên giả lập G1, G2 (Q-72); phần cứng thật mua sau theo nhánh §5.6.

| Hạng mục | Số lượng | Cần trước | Ghi chú |
|:---|:---:|:---:|:---|
| **ESP32-S3-Box-3** (bo tham chiếu chính thức) | 2 + 3–6 | Đợt 1 / I3 | Spike bộ nhớ (TSK-S1-10); nightly runner |
| **Raspberry Pi 5** (nightly `linux`, Q-16) | 1 + 2 | Đặt ngay / I2 | TSK-I2-01, `linux` ARM64 |
| Máy Linux x86-64 | 1 | I2 | Target `linux` trên x86 |
| Mạch nạp và cáp JTAG | 2 bộ | I3 | Gỡ lỗi cấp thanh ghi |
| Runner CI tự quản gắn bo mạch thật | 1 | I3 | Bắt buộc cho TSK-S4-05 |
| Tên miền `schema.neuroedge.dev` | — | I6 | FR-GOV-01, A9 (TSK-I6-02) |
| Camera USB và CSI; NPU Hailo-8 / Coral TPU | 4 + 2 | I2a | Nguồn hình ảnh `vision.in`, tăng tốc |
| **M5Stack CoreS3** (bo `esp32s3` có camera, Q-61) | 2 | Đặt ngay | TSK-I3a-01, camera cho MCU |
| Servo, driver motor và nguồn riêng | 2 bộ | I2a | Kiểm `motion.*` (TSK-W1-04) |
| **ESP32-S3-DevKitC-1 N16R8** (bo phổ thông, Q-75) | 2 | I3a | TSK-I3a-08, TSK-I3a-07 (Pi ↔ ESP32) |

## Phụ lục C — Bố cục kho mã nguồn

Cấu trúc chi tiết: [`CONTRIBUTING.md` §6](../CONTRIBUTING.md#6-cấu-trúc-kho). Bốn quy ước bắt buộc:
1. `schemas/` là nguồn sự thật duy nhất; Python và C đều sinh hoặc kiểm tra theo nó.
2. `fixtures/traces/` dùng chung cho mọi target, làm cơ sở của `neuroedge verify`.
3. `targets/` chỉ chứa hiện thực HAL, không chứa logic nghiệp vụ hay chính sách an toàn.
4. Lớp provider nằm trong `python/neuroedge/models/providers/`, không nằm trong `services/` (CR-1.0).

---

## Phụ lục D — Giao thức truyền dẫn

Kênh truyền và định dạng âm thanh chuẩn cho `record`, `replay` và luồng thoại: [PRD Phụ lục D.2](neuroedge-prd.md#d2-giao-thức-truyền-dẫn--định-dạng-vết-ghi-wire-protocol).

---
*Hết tài liệu*
