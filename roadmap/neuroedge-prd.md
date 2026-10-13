# NeuroEdge — Product Requirements Document

## NeuroEdge — Nơi biến ý định thành sản phẩm vật lý có AI: dựng, chạy an toàn, chia sẻ và bán

*Lớp niềm tin: không hợp đồng, không hành động — LLM nghĩ, luật cứng giữ (Q-30, Q-72).*

**Phiên bản PRD:** 1.6
**Ngày phát hành:** 11 tháng 10, 2026 (Q-72)
**Tài liệu nguồn:** `docs/business/proposal-blueprint-2026-10-11.md` · đặc tả định dạng `docs/spec/core_contracts.md`
**Trạng thái:** Bản thảo chờ phê duyệt kỹ thuật
**Lịch sử thay đổi:** `CHANGELOG.md` — tài liệu này chỉ mô tả hiện trạng.
**Đối tượng sử dụng:** Kỹ sư phát triển · Quản lý kỹ thuật · QA · Kỹ thuật viên tài liệu · Maker và micro-OEM bán NeuroEdge Blueprint · Đối tác OEM

**Phạm vi tài liệu:** Yêu cầu chức năng và phi chức năng · Tiêu chí nghiệm thu · Đặc tả giao diện dữ liệu · Kế hoạch phát hành theo cột mốc · Hệ chỉ số và yêu cầu đo đạc
**Ngoài phạm vi:** Luận điểm chiến lược · Phân tích cạnh tranh · Mô hình tài chính (xem tài liệu nguồn)

---

## Mục lục

1. [Mục tiêu sản phẩm](#1-mục-tiêu-sản-phẩm)
2. [Người dùng và bối cảnh sử dụng](#2-người-dùng-và-bối-cảnh-sử-dụng)
3. [Phạm vi phát hành](#3-phạm-vi-phát-hành)
4. [Yêu cầu chức năng — Lõi thực thi](#4-yêu-cầu-chức-năng--lõi-thực-thi)
5. [Yêu cầu chức năng — An toàn hành động](#5-yêu-cầu-chức-năng--an-toàn-hành-động)
6. [Yêu cầu chức năng — Kiểm thử Action CI](#6-yêu-cầu-chức-năng--kiểm-thử-action-ci)
7. [Yêu cầu chức năng — Trải nghiệm lập trình viên](#7-yêu-cầu-chức-năng--trải-nghiệm-lập-trình-viên)
8. [Yêu cầu chức năng — Tầng dịch vụ thương mại](#8-yêu-cầu-chức-năng--tầng-dịch-vụ-thương-mại)
9. [Yêu cầu phi chức năng](#9-yêu-cầu-phi-chức-năng)
10. [Đặc tả giao diện dữ liệu](#10-đặc-tả-giao-diện-dữ-liệu)
11. [Tiêu chí nghiệm thu phát hành](#11-tiêu-chí-nghiệm-thu-phát-hành)
12. [Hệ chỉ số và yêu cầu đo đạc](#12-hệ-chỉ-số-và-yêu-cầu-đo-đạc)
13. [Phụ thuộc, rủi ro và giả định](#13-phụ-thuộc-rủi-ro-và-giả-định)
14. [Ngoài phạm vi](#14-ngoài-phạm-vi)
15. [Sổ quyết định](#15-sổ-quyết-định)

**Phụ lục**

- [A — Ma trận truy vết yêu cầu](#phụ-lục-a--ma-trận-truy-vết-yêu-cầu)
- [B — Danh mục mã lỗi chuẩn](#phụ-lục-b--danh-mục-mã-lỗi-chuẩn)
- [C — Quy ước định danh và phiên bản](#phụ-lục-c--quy-ước-định-danh-và-phiên-bản)
- [D — Cấu trúc Monorepo và Giao thức Truyền dẫn](#phụ-lục-d--cấu-trúc-monorepo-và-giao-thức-truyền-dẫn)

---

## Quy ước tài liệu

Mọi mã và ký hiệu dùng trong tài liệu này (`FR-*`, `NFR-*`, `P0`–`P2`, `A1`–`A22`, `B1`–`B8`, `C1`–`C8`, `Q-N`, `PF-N`, `R-N`, `U`/`J`, `§x.y`…) được giải mã ở **[`docs/user/thuat-ngu.md`](../docs/user/thuat-ngu.md)** — nơi duy nhất, kèm chỗ định nghĩa đầy đủ.

Từ khóa **BẮT BUỘC**, **NÊN**, **CÓ THỂ** được hiểu theo nghĩa của RFC 2119.

---

## 1. Mục tiêu sản phẩm

### 1.1 Vấn đề cần giải quyết

Chưa có công cụ nào kiểm thử được hành vi vật lý của AI agent **trước khi** thiết bị vận hành ngoài hiện trường. Khi một agent vật lý ra quyết định sai, động cơ đã quay, rơ-le đã đóng, chốt cửa đã mở — các tác động này là bất khả nghịch. Một trợ lý giọng nói trong nhà trộn cả hai loại hành vi trong một cuộc trò chuyện: câu trả lời từ knowledge base hay bản tin sai thì sửa được, còn tắt đèn khi vẫn còn người trên cầu thang thì không — sản phẩm phải tách hai đường đó ra (`docs/architecture/vi/00-overview.md` §1).

Q-72 mở rộng bài toán từ một lệnh tới cả vòng đời của một thiết bị có AI. Người muốn có thiết bị đó gặp ba rào cản: **dựng** (từ ý định tới kit, đấu dây, firmware, gate là việc của chuyên gia nhúng), **chạy** (giao nhiệm vụ bằng lời, có thứ trông thiết bị cả ngày, chủ động báo khi có chuyện, mà hoá đơn LLM vẫn đoán trước được) và **bán** (maker dựng xong một thiết bị chạy tốt nhưng không có cách đóng gói nó thành sản phẩm cho người khác). Rào cản lớn nhất của việc bán là **khoảng trống niềm tin**: người mua là người lạ, không đọc mã, nên cần bằng chứng thiết bị vẫn an toàn khi AI sai — gate trên MCU, hợp đồng chỉ người khoá, vết ghi phát lại được. Lớp hợp đồng hiện có trả lời đúng câu đó; Q-72 biến nó thành giấy thông hành cho việc chia sẻ và bán, không còn là sản phẩm đứng riêng.

Sáu câu hỏi mà công cụ hiện tại không trả lời được:

| # | Câu hỏi | Yêu cầu đáp ứng |
|:---:|:---|:---|
| 1 | Sau khi đổi prompt, agent còn từ chối mở khóa cho người chưa xác thực không? | §6 — Action CI với mẫu chuẩn Golden Reference |
| 2 | Khi đổi mô hình AI, phán quyết gate và tín hiệu GPIO có bị hồi quy không? | §6 — Assert trên phán quyết gate, không assert trên văn bản LLM |
| 3 | Cùng đầu vào, các môi trường có cho cùng phán quyết không? | §4 — Nguyên tắc tương đương môi trường |
| 4 | Tôi nói "trông bể cá giúp tôi" — làm sao ra một thiết bị chạy được mà không phải biết firmware? | §5.4 — hợp đồng nhiệm vụ (FR-MSN); §7.1 — kit và NeuroEdge Lab (FR-DX-09, FR-DX-10) |
| 5 | Ai trông thiết bị cả ngày, báo tôi khi có xu hướng lạ, mà hoá đơn LLM không vượt mức tôi đặt? | §4.5 — agent vận hành (FR-AGT); §5.5 — kênh chat (FR-CH) |
| 6 | Làm sao bán một thiết bị AI cho người lạ khi chứng minh được nó an toàn khi AI sai? | §7.4 — NeuroEdge Blueprint (FR-BP); §8.4 — dòng thu |

### 1.2 Tuyên ngôn sản phẩm

> **NeuroEdge — nơi biến ý định thành sản phẩm vật lý có AI: dựng, chạy an toàn, chia sẻ và bán** *(Q-72)*. Ba vòng: ① **dựng** — từ một câu nói tới kit, firmware, gate, chạy thử trên `sim`; ② **chạy** — agent vận hành thực thi hợp đồng nhiệm vụ cả ngày, phản xạ ngay trên thiết bị, chủ động báo và đề xuất qua kênh chat; ③ **chia sẻ và bán** — gói thành NeuroEdge Blueprint có bằng chứng, người khác cài bằng một lệnh. **LLM nghĩ, luật cứng giữ.**
>
> **Lớp niềm tin — "Hợp đồng vào Physical AI" (Q-30).** Không hợp đồng, không hành động: mọi hành động vật lý của AI agent (chốt cửa, rơ-le, van, đèn) muốn ra thế giới thực đều phải qua một **hợp đồng an toàn có kiểu, có phiên bản** — lớp bảo vệ gần nhất đứng ngay trên 5 nguyên thủy HAL. Hợp đồng được kiểm thử tự động trong CI bằng replay + assert trên phán quyết gate và trạng thái chân, và thực thi nhất quán trên mọi môi trường — từ laptop lập trình viên tới vi điều khiển biên $5. Lớp này là thứ cho phép người lạ tin một thiết bị AI do maker khác dựng.

> **Mở, có minh bạch (Q-73).** NeuroEdge không quyết hộ người dùng cách xác minh hay luồng tương tác; mọi cách đều làm được, mỗi cách mang nhãn rủi ro. **Một ô chat cho cả mạng lưới (Q-74).** Người dùng chỉ cần chat: "não" (trò chuyện, LLM, lập kế hoạch) được phép chạy trên NeuroEdge Cloud tuỳ chọn và điều phối nhiều thiết bị, nhiều nhà, nhiều người; "tuỷ sống" (luật, phản xạ, kiểm lời duyệt) luôn ở hộp tại nhà và ở từng chip — cloud điều phối nhưng không có quyền tối cao.

### 1.3 Mục tiêu sản phẩm

Thứ tự theo Q-72: **M7 → M8 → M9** (Blueprint đầu tiên đi trọn ba vòng trên giả lập) đi trước; M1 → M4 và M6 giữ nguyên; **M5** (đội thiết bị lớn) đi sau cổng nhu cầu 8 tuần.

| # | Mục tiêu | Chỉ số nghiệm thu |
|:---:|:---|:---|
| **M7** | Một câu nói thành một thiết bị chạy được, có hợp đồng *(Q-72)* | Từ câu "tôi muốn trông bể cá" tới hợp đồng nhiệm vụ đã duyệt chạy trên `sim`: hợp đồng mâu thuẫn bị từ chối trước khi duyệt, 100% lệnh vi phạm bị chặn (A15, A17) |
| **M8** | Agent vận hành chạy cả ngày, chủ động báo, chi phí LLM có trần *(Q-72)* | Kịch bản 30 ngày tua nhanh: ít nhất một phát hiện xu hướng đúng, chi phí LLM < 2 USD; mất mạng hay mất LLM thì phản xạ vẫn giữ (A16, A19) |
| **M9** | NeuroEdge Blueprint cài được bằng một lệnh, và có người muốn bán nó *(Q-72)* | Người ngoài đội cài Blueprint trên máy sạch và chạy trên `sim` trong < 10 phút (A14); ≥ 1 maker muốn đóng gói và bán Blueprint của mình (B8) |
| **M1** | Lập trình viên lạ chạy được agent có gate mà không cần mua phần cứng | TTFV trung vị < 10 phút trên 10 người dùng độc lập |
| **M2** | Mọi hành động vật lý đều đi qua một hợp đồng kiểm thử được | 100% lệnh actuator bị chặn nếu thiếu gate hợp lệ |
| **M3** | Cùng một mã nguồn agent chạy nhất quán trên mọi môi trường | `neuroedge verify` đạt 100% trên các target bậc 1: `sim`, `linux`, `esp32s3` |
| **M4** | Sự cố hiện trường tái hiện được trên máy lập trình viên | Tải vết ghi và replay thành công bằng một lệnh |
| **M6** | Bên thứ ba tự nối NeuroEdge với một sản phẩm hay hệ sinh thái mới mà không sửa lõi, không chờ đội lõi *(Q-67)* | Một bridge cho hệ sinh thái chưa từng có, viết ở kho riêng chỉ từ tài liệu công khai, qua bộ test tuân thủ trong **≤ 1 ngày**; che một MCP server sẵn có trong **≤ 3 lệnh** (A13) |
| **M5** | Đội vận hành cập nhật firmware quy mô lớn không mất thiết bị *(sau cổng 8 tuần — Q-72)* | 1.000 thiết bị / 0 sự cố brick |

### 1.4 Phi mục tiêu

| # | Phi mục tiêu | Lý do |
|:---:|:---|:---|
| **N1** | Không trở thành nhà cung cấp mô hình AI | Mô hình là thành phần thay thế được (§0.4 nguyên tắc 4) |
| **N2** | Không cạnh tranh độ sâu driver một dòng chip | Nhường cho SDK chính hãng (§10.3) |
| **N3** | Không theo đuổi độ phủ phần cứng rộng ở giai đoạn đầu | Ba môi trường bậc 1 đủ chứng minh tương đương. Từ Giai đoạn 2, độ phủ mở rộng qua phân tầng bậc (FR-TGT-08) chứ không qua việc đội lõi ôm thêm bo mạch (§9) |
| **N4** | Không bán lại token suy luận như nguồn biên lợi nhuận chính | Biên mỏng, cạnh tranh trực tiếp với model vendor (§0.4 nguyên tắc 3). Q-72 giữ nguyên: người dùng tự trả LLM bằng key của mình (BYOK). Q-74 bước 2 (có điều kiện): gói NeuroEdge Cloud có thể kèm token trong thuê bao, BYOK vẫn giữ — sửa N4 khi mở bước đó |
| **N5** | Không là lớp bảo vệ an toàn duy nhất, không là chức năng an toàn được chứng nhận | Bảo vệ khỏi nguy hiểm (cháy, quá dòng, chạy khô) luôn do phần cứng — cầu chì nhiệt, rơ-le quá dòng, công tắc phao; NeuroEdge giữ thiết bị tiếp tục làm việc khi mất não và gọi người khi phải chọn giữa hai điều xấu (Q-38, Q-72) |

### 1.5 Năm nguyên tắc thiết kế bất biến

Mọi yêu cầu trong tài liệu này phải tuân thủ năm nguyên tắc sau. Xung đột với bất kỳ nguyên tắc nào là căn cứ bác bỏ yêu cầu.

| # | Nguyên tắc | Hệ quả kỹ thuật ràng buộc |
|:---:|:---|:---|
| **P-1** | Hành động vật lý là hợp đồng chuẩn kiểu, không phải lời gọi hàm tự do | HAL từ chối mọi lệnh actuator thiếu chữ ký gate đã pass. Mọi đường từ ngôn ngữ tới hành động — giọng nói offline, LLM, client MCP, kênh chat, LLM worker của agent vận hành — là một **tool call có kiểu** đi qua cùng gate (Q-24, `docs/spec/tool_calling.md`). Ngoại lệ duy nhất là lệnh **về phía an toàn** (Q-62). *Chờ RFC an toàn có điều kiện (Q-72):* "phía an toàn" là `safe_state` của cơ cấu khai trong `board.v1` (mặc định `off`), không phải luôn là tắt; hướng *rời* `safe_state` là hướng bị gate và giới hạn, nên ngoại lệ vẫn đối xứng và không mở đường tắt mới |
| **P-2** | Các môi trường thực thi ngang hàng | Không được rẽ nhánh logic theo target trong mã nguồn agent. Mức cam kết kiểm chứng phân theo ba bậc target (FR-TGT-08); hệ quả kỹ thuật này áp dụng như nhau ở mọi bậc |
| **P-3** | Giá trị tập trung ở người tạo sản phẩm: dựng, bán và vận hành thiết bị *(sửa bởi Q-72)* | Người dùng phi thương mại có toàn bộ lõi miễn phí; bán NeuroEdge Blueprint hay thiết bị là dùng thương mại (Q-45). Dòng thu trước: hoa hồng kit (liên kết, chưa giữ kho), chia doanh thu Blueprint, giấy phép thương mại theo thiết bị, relay đám mây tuỳ chọn; Fleet OS đi sau (§8). Với doanh nghiệp, tính năng an toàn cốt lõi luôn nằm trong license thương mại, không bao giờ bị tách thành gói trả thêm; không dòng thu nào nằm trên đường an toàn |
| **P-4** | Mô hình AI là thành phần thay thế được — cloud-first, provider-pluggable | Mọi truy cập mô hình đi qua interface `SystemOne` / `SystemTwo`; chuẩn kết nối mặc định là OpenAI API, provider không tương thích đi qua adapter tự viết; ASR và TTS cũng là provider thay thế được. Phần nặng xử lý ngôn ngữ chạy trên cloud/host, `esp32s3` chỉ thu/phát âm thanh và thẩm định gate |
| **P-5** | Hiệu ứng mạng từ chia sẻ chính sách an toàn và thành phần mở rộng | Gate là tệp dữ liệu có phiên bản, chia sẻ và kế thừa được. Adapter kết nối nhà cung cấp và bản port HAL là loại tài sản chia sẻ thứ hai; chúng là mã thực thi nên đi kèm cổng kiểm soát riêng — Bộ kiểm thử tuân thủ, sandbox phân quyền và đối chiếu năng lực lúc build. Từ Q-67, mọi đường nối với bên ngoài là một điểm cắm của Extension SDK (FR-EXT): bên thứ ba tự nối mà không sửa lõi, còn bất biến an toàn không đổi. Từ Q-72, tài sản chia sẻ chính là **NeuroEdge Blueprint** (FR-BP): người dựng tạo Blueprint → người dùng cài → dữ liệu vận hành chia sẻ **có đồng ý** làm bộ phát hiện tốt hơn → Blueprint tốt hơn → thêm người dùng, thêm người dựng |

---

## 2. Người dùng và bối cảnh sử dụng

### 2.1 Nhóm người dùng mục tiêu

Theo Q-72, thị trường đầu là **cộng đồng maker toàn cầu quanh Home Assistant và ESPHome** (U1), rồi maker thành nhà sản xuất nhỏ (U5); U2 và U3 lùi xuống phụ.

| Mã | Nhóm | Bối cảnh | Nhu cầu cốt lõi | Ưu tiên |
|:---:|:---|:---|:---|:---:|
| **U1** | **Maker trong cộng đồng Home Assistant / ESPHome toàn cầu** | Có ý định ("trông bể cá", "tưới theo nhu cầu cây"), thường chưa có phần cứng trong tay; đã quen Home Assistant, ESPHome, hỏi Claude cách dựng | Từ một câu nói tới thiết bị chạy được; chạy thử trên giả lập trước khi mua; giao nhiệm vụ bằng lời, được báo qua kênh chat; không rào cản, không tài khoản trong mười phút đầu | **Chính — thị trường đầu (Q-72)** |
| **U2** | **Trưởng nhóm kỹ thuật nhúng** | Đội 3–10 người, chuẩn bị đưa sản phẩm vào sản xuất | Kiểm thử an toàn tự động, chuyển board không viết lại mã | Phụ *(từ Q-72; trước đó Chính)* |
| **U3** | **Kỹ sư vận hành đội thiết bị (Fleet Ops)** | Quản lý 100–10.000 thiết bị đã lắp đặt | Cập nhật an toàn, chẩn đoán từ xa, không mất thiết bị | Phụ — từ v1.1, sau cổng 8 tuần (Q-72) |
| **U4** | **Chuyên gia an toàn & QA** | Chịu trách nhiệm phê duyệt hành vi thiết bị | Điều kiện an toàn đọc được, nhật ký đối soát được | Phụ |
| **U5** | **Micro-OEM: maker bán NeuroEdge Blueprint hoặc thiết bị** *(Q-72; gồm cả đối tác OEM/ODM bán bo mạch)* | Đã dựng một thiết bị chạy tốt, muốn bán cho trăm người; startup phần cứng nhỏ | Đóng gói kit, firmware, hợp đồng mẫu, bộ phát hiện và bằng chứng thành một gói người khác cài bằng một lệnh; giấy phép thương mại rõ ràng; không khoá khách vào một dòng chip | **Chính — phép thử của cổng 8 tuần (B8)** |
| **U6** | **Đội tích hợp robot phân tầng** | Robot một não (Pi 5) và nhiều bộ điều khiển MCU: motor, tay máy, dẫn đường qua ROS 2/Nav2 (Q-32, Q-34) | Mọi lệnh chuyển động qua gate trên từng node; mất liên lạc thì từng cơ cấu về trạng thái an toàn (Q-35) | Phụ — từ I14; giả thuyết, kiểm bằng phỏng vấn ở `TODOS.md` #40 |
| **U7** | **Tác giả tích hợp (bên thứ ba)** | Hãng thiết bị AI mới, cộng đồng của một hệ sinh thái (Muse Gadgets, Home Assistant, xiaozhi…), maker viết cầu nối cho sản phẩm mình đang dùng | Tự nối sản phẩm của mình với lớp an toàn chỉ qua tài liệu công khai, không sửa lõi; tự chứng minh đúng bằng bộ test tuân thủ (Q-67) | Chính — từ I2c |
| **U8** | **Người dùng cuối cài NeuroEdge Blueprint** *(Q-72)* | Không phải lập trình viên; mua kit theo BOM hoặc mua thiết bị từ U5 | Cài một Blueprint, đọc bản duyệt ≤ 5 dòng, duyệt qua kênh chat, có thiết bị thông minh chạy ngay; không cần đọc mã hay gate | Chính — từ I2e |
| **U9** | **Nhà cung cấp linh kiện và kit** *(Q-72)* | Bán cảm biến, bo mạch, rơ-le theo BOM của Blueprint | Đơn hàng định sẵn theo BOM; liên kết mua đúng mã hàng | Phụ — nguồn thu thử đầu (hoa hồng kit) |

### 2.2 Nhiệm vụ cần hoàn thành (Jobs To Be Done)

| Mã | Nhóm | Nhiệm vụ | Đáp ứng bởi |
|:---:|:---:|:---|:---|
| **J1** | U1 | "Tôi muốn thử một agent giọng nói ngay tối nay mà chưa có board" *(tạm dừng phần thoại — Q-72; bản gõ chữ trên `sim` vẫn là hành trình 1)* | FR-TGT-01, FR-DX-01 |
| **J2** | U2 | "Tôi cần chắc chắn bản cập nhật prompt không làm chốt cửa mở sai" | FR-CI-03, FR-CI-04 |
| **J3** | U2 | "Tôi cần chuyển từ RPi sang ESP32-S3 mà không viết lại logic" | FR-TGT-02, FR-HAL-01 |
| **J4** | U3 | "Một thiết bị ở villa lỗi, tôi cần biết chuyện gì đã xảy ra mà không phải tới nơi" | FR-CI-01, FR-FLT-05 |
| **J5** | U3 | "Tôi cần cập nhật 1.000 thiết bị mà không có nguy cơ hỏng hàng loạt" | FR-OTA-01, FR-FLT-02 |
| **J6** | U4 | "Tôi cần duyệt điều kiện mở khóa mà không đọc mã nguồn Python" | FR-GATE-01, FR-GATE-02 |
| **J7** | U2 | "Tôi muốn dùng lại chính sách an toàn người khác đã tinh chỉnh" | FR-GATE-05, FR-REG-01 |
| **J8** | U1 | "Trông bể cá 120 lít giúp tôi: oxy thấp thì bật sục khí, có gì lạ chụp ảnh gửi tôi" *(Q-72)* | FR-DX-09, FR-DX-10, FR-MSN-01 → 14, FR-AGT-01 |
| **J9** | U1, U8 | "Báo tôi khi có xu hướng lạ, nhưng đừng nhắn cả ngày và đừng để hoá đơn LLM vượt 2 USD một tháng" *(Q-72)* | FR-AGT-04 → 07, FR-MSN-09, FR-CH-01 |
| **J10** | U5 | "Tôi muốn bán thiết bị mình dựng cho người khác, kèm bằng chứng nó an toàn" *(Q-72)* | FR-BP-01 → 10, §8.4 |
| **J11** | U8 | "Tôi muốn cài thiết bị người khác đã dựng mà không phải lập trình, và hiểu mình đang cho phép nó làm gì" *(Q-72)* | FR-BP-03, FR-MSN-12, FR-CH-04 |

### 2.3 Bốn hành trình người dùng chính

Hành trình 0 là **hành trình chính** từ Q-72; hành trình 1 giữ nguyên; hành trình 2 và 3 (đội thiết bị, Fleet OS) đi sau cổng nhu cầu 8 tuần.

#### Hành trình 0 — Bể cá đi trọn ba vòng (U1 dựng → U8 cài → U5 bán) *(Q-72, chạy trên giả lập trước)*

| Vòng | Bước | Phản hồi hệ thống kỳ vọng | Yêu cầu |
|:---:|:---|:---|:---|
| ① | Người dùng nói với Claude (client MCP nối NeuroEdge Lab): *"Tôi muốn trông bể cá 120 lít."* | Đề xuất một kit đã kiểm chứng từ danh mục (cảm biến nhiệt, oxy, camera, relay sục khí và sưởi), sơ đồ đấu dây, danh sách mua có nơi mua; chạy thử trên `sim` có mô hình bể (tầng giả lập G1) trước khi mua | FR-DX-09, FR-DX-10, FR-TGT-07 |
| ① | Dựng, nạp, kiểm lắp; nối Telegram | Cấu hình bo, firmware, gate sinh từ một nguồn; `neuroedge lab doctor` kiểm từng cảm biến (*"cảm biến oxy đọc 0 — kiểm lại dây"*); `neuroedge chat connect telegram`, ghép đôi tài khoản bằng mã hiện tại chỗ | FR-DX-10, FR-CH-01, FR-CH-03, FR-CLI-14 |
| ② | Giao nhiệm vụ: *"Trông bể, oxy thấp thì bật sục khí, có gì lạ chụp ảnh gửi tôi."* | Bản nháp hợp đồng nhiệm vụ; hỏi lại khi mơ hồ (*"Ngưỡng oxy thấp là bao nhiêu? Gợi ý 5 mg/L cho cá nhiệt đới"*); kiểm mâu thuẫn; bản duyệt ≤ 5 dòng; người duyệt trong chat hoặc UI cục bộ — LLM không khoá được | FR-MSN-01 → 14, FR-CH-04 |
| ② | Chạy | Phản xạ tại chỗ (oxy dưới ngưỡng → sục khí); LLM đề nghị *"tắt sục khí cho yên tĩnh"* → bị chặn, kèm lý do; ngắt mạng → sục khí vẫn chạy (`safe_state` đã khai); sưởi quá nhiệt 10 phút → phản xạ ngắt sưởi, báo động | FR-MSN-05, FR-MSN-10, FR-ACE-03, FR-AGT-01 |
| ② | Chủ động | Bộ phát hiện tất định thấy oxy buổi sáng giảm 3 ngày liền → LLM viết đề xuất → đề xuất biên dịch thành bản nháp sửa đổi hợp đồng → tin Telegram kèm yêu cầu duyệt và bản duyệt do trình biên dịch sinh, không do LLM viết (*"…Đề xuất vệ sinh lọc và thêm sục khí 2h–5h. Thêm vào hợp đồng?"*); trả lời "Có" đúng yêu cầu duyệt → sửa đổi được duyệt bằng bản ghi duyệt | FR-AGT-04 → 06, FR-MSN-14, FR-CH-04 |
| ③ | Chia sẻ | `neuroedge blueprint pack` gói kit, firmware, hợp đồng mẫu, bộ phát hiện và vết ghi bằng chứng; người thứ hai `neuroedge blueprint install <url>` trên máy sạch, chạy trên `sim` trong < 10 phút | FR-BP-01 → 06, FR-CLI-13 |
| ③ | Bán *(sau cổng 8 tuần)* | Giấy phép thương mại và chia doanh thu đi qua NeuroEdge; bằng chứng phải được ký trước khi Hub thu tiền cho người bán | FR-BP-08, FR-BP-10, §8.4 |

#### Hành trình 1 — Mười phút đầu tiên (U1)

| Phút | Hành động | Phản hồi hệ thống kỳ vọng | Yêu cầu |
|:---:|:---|:---|:---|
| 0–1 | `pip install neuroedge` | Cài xong, không hỏi tài khoản, không hỏi API key | FR-DX-02 |
| 1–2 | `neuroedge new my-agent` | Sinh dự án mẫu có sẵn 1 action, 1 gate, 1 test | FR-DX-01 |
| 2–4 | `neuroedge run --target sim`, gõ một lệnh (vd *"mở cửa phòng 101"*) | Không mạng, không key, tất định: bộ khớp ngữ pháp lệnh cục bộ nhận lệnh; thấy actuator ảo chuyển động và phán quyết gate. Giọng nói là tuỳ chọn — cần key STT cloud *(Q-15)* | FR-TGT-01, FR-DX-02 |
| 4–6 | Sửa `allow_when` trong gate | Agent từ chối hành động, hiển thị nguyên nhân trong vết ghi | FR-ACE-02 |
| 6–8 | `neuroedge test` | CI xanh; phá điều kiện → CI đỏ, chỉ đích danh gate vi phạm | FR-CI-03 |
| 8–10 | `neuroedge run --target linux` | Cùng mã nguồn, chạy trên phần cứng thật | FR-TGT-02, FR-CLI-02 |

**Ràng buộc bắt buộc:** trong toàn bộ hành trình này, hệ thống **KHÔNG ĐƯỢC** yêu cầu mua phần cứng, tạo tài khoản, hay nhập thông tin thanh toán. Ràng buộc áp cho **mười phút đầu** (và cho việc cài một NeuroEdge Blueprint rồi chạy nó trên `sim`, A14). Các bước sau đó của hành trình 0 có thể cần tài khoản của bên thứ ba do người dùng chọn — nền tảng chat, key LLM của chính họ (BYOK), relay tuỳ chọn — nhưng không bước nào nằm trên đường an toàn, và lõi không bao giờ đòi tài khoản NeuroEdge.

#### Hành trình 2 — Từ sự cố hiện trường về máy lập trình viên (U3 → U2) *(Fleet OS — sau cổng 8 tuần, Q-72)*

```text
Thiết bị tại hiện trường phát sinh cảnh báo
        │
        ▼
Fleet OS tự động tải tệp vết ghi JSON về kho tập trung      ← FR-FLT-05
        │
        ▼
Kỹ sư tải tệp về máy cá nhân
        │
        ▼
neuroedge trace validate traces/incidents/<session>.json     ← FR-CLI-04
        │
        ▼
neuroedge replay traces/incidents/<session>.json --target sim ← FR-CI-02
        │
        ▼
Tái hiện chính xác chuỗi phán quyết gate và tín hiệu GPIO
        │
        ▼
Bổ sung tệp vết ghi thành kịch bản hồi quy vĩnh viễn         ← FR-CI-03
```

#### Hành trình 3 — Mở rộng từ 1 lên 1.000 thiết bị (U2 → U3) *(sau cổng 8 tuần, Q-72)*

| Giai đoạn | Hành động | Yêu cầu chi phối |
|:---|:---|:---|
| 1 thiết bị | Nạp firmware thủ công, thiết bị ảo `sim` hiện trên Fleet Dashboard | FR-FLT-03 |
| 10 thiết bị | Cấp chứng chỉ tự động ở lần khởi động đầu | FR-FLT-01 |
| 100 thiết bị | Cập nhật gate và cấu hình từ xa, không nạp lại firmware | FR-FLT-04 |
| 1.000 thiết bị | Cập nhật OTA theo đợt canary 1% → 10% → 100%, tự dừng khi vượt ngưỡng lỗi | FR-FLT-02 |

---

## 3. Phạm vi phát hành

### 3.1 Ba mốc phát hành

Thứ tự và ngày dự báo của từng mốc nằm ở **một nơi**: bảng increment của roadmap (§0.2), theo Q-39. Bảng dưới chỉ
nói mốc nào gồm increment nào.

| Mốc | Tên | Increment (roadmap §0.2) | Nội dung | Điều kiện khởi động |
|:---|:---|:---:|:---|:---|
| **0.x** | Bản increment nội bộ | I1–I3a | Mỗi increment một tag nội bộ và một tín hiệu đo; **không phát hành ra ngoài** (Q-39) | — |
| **Thử với đối tác** | Wheel giao trực tiếp cho một đội đối tác — gate cho thiết bị họ đang có (Q-70) | I2c (TSK-I2c-19) | `proxy mcp`, `proxy http`, `neuroedge.guard`, `sim`, Action CI; không `esp32s3`, không thoại trên chip, không NeuroEdge Lab; không lên index nào | Điều kiện ở roadmap §4.3.3 — không chờ bo mạch |
| **Blueprint trên giả lập** | NeuroEdge Blueprint đầu tiên (bể cá) đi trọn ba vòng trên giả lập (Q-72) | I2d, I2e | Hợp đồng nhiệm vụ, an toàn có điều kiện (chờ RFC), agent vận hành, Telegram + bản ghi duyệt, `blueprint pack`/`install`, index tĩnh, kit bể cá có BOM liên kết; không phần cứng thật, không thu tiền; PyPI vẫn ở I6 (Q-39) — cách giao bản cài cho người thử ở roadmap | Cổng nhu cầu **8 tuần sau khi chốt** Q-72 đo kết quả (B6–B8, §11.2) |
| **Công khai** | Repo công khai + PyPI | I6 | Bản ứng viên của MVP: demo bốn gói nguyên thủy mở rộng và Blueprint trên `sim`, `linux` và `esp32s3` (Q-77) | I3a, I2b và I2e phát hành |
| **v1.0 = MVP** | Lõi (source-available, Q-45) — lần ra mắt MVP (Q-52, Q-77) | I7 | Khối 1a + Khối 1b + bốn gói nguyên thủy mở rộng (Q-53) + kit mẫu + nền tảng mở (Q-67) + hợp đồng nhiệm vụ, agent vận hành, kênh chat, NeuroEdge Blueprint (Q-72). Thoại, Studio, `jetson` **tạm dừng, không cắt**; phạm vi v1.0 **xét lại ở cổng 8 tuần** bằng dữ liệu (Q-72) | Đạt toàn bộ tiêu chí §11.1 (A1–A13) |
| **Developer Beta** | Beta trên dòng `1.0.x` | I8 | Đóng băng tính năng trên dòng `1.0.x`, hỗ trợ 50–100 lập trình viên | v1.0 phát hành |

Khối 4 (AURA thực địa, sau Beta — điều kiện ở §14) và Khối 5 (Marketplace thu phí) nằm ngoài phạm vi PRD này. Riêng NeuroEdge Blueprint, **Hub tối thiểu** — index tĩnh, không máy chủ, không thu phí — thuộc phạm vi I2e (FR-BP-05); Hub thu phí chỉ mở sau cổng 8 tuần (§14, Q-72), thay điều kiện cột mốc G1–G4 của §11.2 cho riêng Blueprint. Khối 4 và Khối 5 được đặc tả trong tài liệu sản phẩm riêng khi tới mốc. Theo Q-39, kế hoạch thực thi của Giai đoạn 2, NeuroEdge Lab (I4a, I5a — Q-55, Q-71) và robot phân tầng (I14) nằm trong roadmap chung; PRD này chỉ đặc tả các hợp đồng mà Giai đoạn 2 phải tuân thủ (FR-TGT-08, FR-HAL-01), không đặc tả yêu cầu chi tiết của nó.

### 3.2 Nội dung từng mốc

| Nhóm yêu cầu | v1.0 Khối 1a<br>(I0–I2) | v1.0 Khối 1b<br>(I3–I7) | Đã bỏ khỏi roadmap<br>(Q-77) |
|:---|:---:|:---:|:---:|
| HAL hợp đồng năng lực (FR-HAL) | ● | ● | — |
| Môi trường `sim` + `linux` (FR-TGT) | ● | — | — |
| Môi trường `esp32s3` (FR-TGT) | — | ● | — |
| Action Contract Engine (FR-ACE) | ● | — | — |
| Định dạng gate (FR-GATE) | ● | — | ◐ registry |
| Trừu tượng hóa mô hình (FR-MDL) | ◐ trừ FR-MDL-09 | ● FR-MDL-09 ASR/TTS | — |
| Runtime nhận thức & hội thoại (FR-PER) | ◐ đặc tả FSM (TSK-S2-07) | — (thoại bỏ khỏi v1.0, Q-77) | ● thoại trên chip |
| Action CI (FR-CI) | ● | ◐ `verify` môi trường bậc 1 | — |
| Lược đồ vết ghi (FR-TRC) | ● | — | — |
| CLI (FR-CLI) | ● | ◐ bổ sung | — |
| Trải nghiệm lập trình viên (FR-DX) | ● | ● FR-DX-08 → FR-DX-10 (kit, `neuroedge add`, NeuroEdge Lab) | — |
| Nguyên thủy mở rộng (FR-HAL-08) | ◐ `sim` + `linux` (I2a) | ● `esp32s3` (I3a) | — |
| OTA cấp thiết bị (FR-OTA) | — | ● | — |
| Lớp trừu tượng provider (FR-GW) | ◐ FR-GW-01, 03 tối thiểu (Q-28) | ◐ client streaming MCU của FR-GW-04 (TSK-S5-06) | ● phần còn lại (Q-28) |
| Fleet Management OS (FR-FLT) | — | — | ● |
| Đường ray hạ tầng (FR-REG) | — | — | ● |

**Chú thích:** ● hoàn thành trong mốc · ◐ hoàn thành một phần · — không thuộc mốc

**Nhóm yêu cầu của Q-72** đi trước Khối 1b về thứ tự; increment và task ở roadmap §0.2:

| Nhóm yêu cầu | I2d — Nhiệm vụ và agent vận hành | I2e — NeuroEdge Blueprint tối thiểu | Sau cổng 8 tuần |
|:---|:---:|:---:|:---:|
| Hợp đồng nhiệm vụ (FR-MSN) | ● | — | — |
| An toàn có điều kiện (FR-ACE-03, chờ RFC) | ● | — | — |
| Agent vận hành (FR-AGT) | ● | — | ◐ định tuyến mô hình (FR-AGT-08) |
| Kênh chat và bản ghi duyệt (FR-CH) | ● Telegram | — | ◐ Slack, Zalo |
| Luồng dữ liệu chống rò rỉ (FR-EGR) | ● | — | ◐ relay (FR-EGR-05) |
| Vết ghi theo đoạn (FR-TRC-11 → 13) | ● | — | — |
| Giả lập G1 (mô hình vật lý), G2 (FR-TGT-07) | ● | — | — |
| Bộ tool MCP chuẩn cho bộ não (FR-AGT-12; thay Lab vòng ①, Q-77) | ● | — | — |
| NeuroEdge Blueprint, index tĩnh (FR-BP-01 → 07) | — | ● | ◐ giấy phép, Hub thu phí (FR-BP-08, 10) |
| Kit bể cá có BOM liên kết (FR-DX-09) | — | ● | — |

### 3.3 Điều kiện kích hoạt v1.1

v1.1 **KHÔNG ĐƯỢC** khởi động theo lịch cố định. Chỉ khởi động khi Developer Beta đạt **đồng thời** B1 và B2 — ngưỡng ở §11.2. B3 vẫn được đo nhưng không là điều kiện (Q-41). Theo Q-72, Fleet OS (U3) còn đi sau cổng nhu cầu 8 tuần (B6–B8); kết quả cổng có thể đổi thứ tự của v1.1, không đổi B1, B2.

### 3.4 Đóng băng phạm vi Khối 1b

Các hạng mục sau **BẮT BUỘC** bị loại khỏi Khối 1b để bảo đảm độ ổn định bộ nhớ trên vi điều khiển. Đây là ràng buộc của **mốc v1.0**, không phải ràng buộc vĩnh viễn — trạng thái dài hạn của từng hạng mục xem §14 của tài liệu này.

| Hạng mục | Trạng thái trong v1.0 |
|:---|:---|
| Huấn luyện wake-word tùy biến | Không hỗ trợ — chỉ dùng wake-word pre-trained *"Hey Neuro"* |
| Độ phủ bo mạch | **Bo mạch tham chiếu chính thức ESP32-S3-Box-3** (tích hợp sẵn màn hình LCD ST7789, dual-mic ES7210, loa ES8311, dock I/O; DevKitC chuyển thành bo mạch thứ cấp do cộng đồng duy trì), cộng **một bo ESP32-S3 có camera** cho `vision.in` (Q-53): **M5Stack CoreS3** (Q-61, TSK-I3a-01) |
| Thị giác máy tính | **Thuộc phạm vi v1.0** (Q-53): `vision.in` trên ba target; kết quả vào gate dưới dạng dữ kiện do maker khai, ngưỡng tin cậy khoá bằng tiêu chí số (Q-54) |
| Kết nối tới provider AI trên đám mây (LLM · ASR · TTS) | **Thuộc phạm vi v1.0** — là kiến trúc mặc định theo P-4 |
| Dịch vụ đám mây do NeuroEdge vận hành, hệ thống tài khoản NeuroEdge | Không thuộc phạm vi cho lõi — người dùng tự vận hành lớp provider và tự giữ khóa (BYOK). **Ngoại lệ có giới hạn (Q-72):** relay tuỳ chọn (ống TLS xuyên, relay không giải mã, FR-EGR-05) và index Blueprint tĩnh (FR-BP-05) được phép; cả hai **không bao giờ nằm trên đường an toàn** — tắt hay hỏng thì phản xạ, gate, hợp đồng và lời duyệt vẫn chạy |
| Kênh nhắn tin (Telegram trước, rồi Slack, Zalo) | **Thuộc phạm vi** (Q-72): adapter chạy trong runtime trên máy nhà, không trên MCU (FR-CH) |
| Jetson, Matter, HomeKit | Không thuộc phạm vi (`jetson` tạm dừng theo Q-72) |
| Tinh chỉnh mô hình AI | Không thuộc phạm vi |

---

## 4. Yêu cầu chức năng — Lõi thực thi

### 4.1 Lớp trừu tượng phần cứng (FR-HAL)

HAL là hợp đồng kiểm tra hai chiều: bo mạch khai báo năng lực cung cấp, agent khai báo tài nguyên cần dùng, mọi điểm không tương thích bị phát hiện **tại thời điểm biên dịch**.

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-HAL-01** | Hệ thống cung cấp 5 nguyên thủy **lõi**: `audio.in`, `audio.out`, `digital.out`, `sensor.read`, `display`. Nguyên thủy lõi bắt buộc với bo mặc định của mỗi target và với mọi bo tham chiếu bậc 1 ngoài `EXTENSION_REFERENCE_BOARDS`. Ngoài lõi là các nguyên thủy **mở rộng** của FR-HAL-08 (`digital.in`, bus I2C chỉ đọc, `analog.in`, PWM trong `digital.out`, `motion.*`, `vision.in`): **tuỳ chọn theo bo mạch**, bo chỉ khai nguyên thủy mà phần cứng thật có, và agent đòi nguyên thủy bo không khai bị từ chối lúc build (FR-HAL-04, FR-HAL-05). Tập nguyên thủy, lõi lẫn mở rộng, **đóng cho v1.x**; thêm nguyên thủy chỉ qua RFC *(RFC-0013, Q-53)* | P0 | Cả 5 nguyên thủy lõi có hiện thực đầy đủ trên các môi trường bậc 1; mỗi nguyên thủy mở rộng có trên ít nhất một bo tham chiếu của mỗi target bậc 1 (FR-HAL-08) | §3.3, RFC-0013 |
| **FR-HAL-02** | Bo mạch khai báo năng lực qua tệp `board.toml` theo schema chuẩn | P0 | Tệp sai schema bị từ chối kèm thông báo chỉ rõ trường lỗi | §4.2 |
| **FR-HAL-03** | Agent khai báo yêu cầu năng lực qua khối `[requires]` trong `agent.toml` | P0 | Thiếu khối `[requires]` khi agent có hành động vật lý → build dừng | §4.3 |
| **FR-HAL-04** | Công cụ đối chiếu năng lực chạy **lúc build**, không lúc chạy | P0 | Bất tương thích làm `neuroedge build` thoát với mã lỗi khác 0, không sinh firmware | §4.9 |
| **FR-HAL-05** | Thông báo lỗi đối chiếu nêu rõ: năng lực thiếu, bo mạch cung cấp gì, vị trí mã nguồn gọi | P0 | Thông báo chứa đủ 3 thành phần và gợi ý cách xử lý | §4.9 |
| **FR-HAL-06** | Chân GPIO và cảm biến định danh bằng **tên logic**, không bằng số chân vật lý | P0 | Đổi bo mạch chỉ cần sửa `board.toml`, không sửa mã agent | Phụ lục A.2 |
| **FR-HAL-07** | HAL từ chối mọi lệnh `digital.out` không kèm chữ ký gate đã pass | P0 | Gọi trực tiếp sinh ngoại lệ `ActionContractViolation` | Phụ lục A.2 |
| **FR-HAL-08** | Bốn gói nguyên thủy mở rộng, **tuỳ chọn theo bo mạch**: cảm biến (`digital.in`, bus I2C chỉ đọc, `analog.in`, tiêu chí gate `numeric`), điều khiển mịn (PWM trong `digital.out`), thị giác (`vision.in`), chuyển động (`motion.*`). Mỗi nguyên thủy mở rộng có ít nhất một bo tham chiếu bậc 1 trên **mỗi** target bậc 1 *(Q-53; RFC-0007, RFC-0009 → RFC-0013)* | P0 | `verify --targets sim,linux,esp32s3` đạt 100% cho agent mẫu của từng gói; agent đòi nguyên thủy mà bo không khai bị từ chối lúc build (FR-HAL-05) | Q-53 |

### 4.2 Môi trường thực thi (FR-TGT)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-TGT-01** | Môi trường `sim` là môi trường thực thi chính thức, hiện thực đúng hợp đồng HAL — không phải bản mock | P0 | `sim` chạy cùng tệp mã agent như phần cứng thật, không có nhánh mã riêng | §3.7 |
| **FR-TGT-02** | Môi trường `linux` là môi trường chính thức ngang hàng, hỗ trợ RPi và x86 qua `gpiod` | P0 | Agent mẫu chạy thật trên RPi 5 và trên x86 Linux — agent mẫu cần `aec`, nên phụ thuộc Q-22 | §3.2 |
| **FR-TGT-03** | Môi trường `esp32s3` là môi trường chính thức ngang hàng, xây bằng ESP-IDF | P0 | Agent mẫu chạy thật trên bo mạch tham chiếu | §8.2 |
| **FR-TGT-04** | **Nguyên tắc tương đương:** cùng một tệp mã agent cho cùng chuỗi phán quyết trên mọi môi trường, không sửa một dòng | P0 | `neuroedge verify --targets sim,linux,esp32s3` đạt 100% | §3.2 |
| **FR-TGT-05** | Chuyển môi trường qua tham số `--target`; **cấm** rẽ nhánh logic theo target trong mã agent | P0 | Rà soát mã: không tồn tại biểu thức điều kiện theo tên target trong lớp ứng dụng | §4.1 |
| **FR-TGT-06** | `sim` cung cấp giao diện web hiển thị cảm biến ảo và trạng thái cơ cấu chấp hành | P0 | Mở được trong trình duyệt, phản ánh đúng trạng thái chân GPIO ảo theo thời gian thực; chạy không mạng (không tải CDN). Lệnh: `neuroedge run --ui` (TSK-S2-09) | §4.10 |
| **FR-TGT-07** | `sim` mô phỏng được kịch bản cảm biến và điều kiện mạng suy giảm. *Mở rộng bởi Q-72:* kịch bản **nhiệm vụ** — chuỗi cảm biến nhiều ngày sinh từ **mô hình vật lý** (bể cá: nhiệt, oxy theo thời gian, tác động của sưởi và sục khí), tua nhanh 30 ngày, kèm sự kiện mất mạng, mất LLM, kênh chat sập, mất điện (tầng giả lập G1) | **P0** *(nâng từ P1 bởi Q-72; I2d)* | Khai báo được kịch bản mất mạng để kiểm thử fail-closed. Kịch bản 30 ngày của bể cá chạy tất định (cùng hạt giống cho cùng chuỗi cảm biến và cùng phán quyết), đủ để đo A16, A19, NFR-COST-01 và cỡ vết ghi 30 ngày (NFR-OBS-04) | §4.7, Q-72 |
| **FR-TGT-08** | **Phân tầng target:** mỗi môi trường thực thi thuộc đúng một bậc cam kết — bậc 1 chính thức (`sim`, `linux`, `esp32s3`), bậc 2 mở rộng do đội lõi bảo trì, bậc 3 do cộng đồng port và tự kiểm chứng. Bậc được khai báo tường minh, không suy diễn | P0 | **Nghiệm thu ở Giai đoạn 2** — cần `TARGET_TIERS` (RFC-0002 PR2): mỗi target có bậc ghi trong tài liệu và trong bảng bậc của mã lõi (RFC-0002 §3b); `board.toml` không tự khai bậc; ngưỡng `verify` 100% chỉ ràng buộc bậc 1; bậc 3 không chặn phát hành. **Hiện tại chỉ có bậc 1** (`sim`, `linux`, `esp32s3`), kiểm chứng qua A2. **Bo tham chiếu (RFC-0013):** mỗi target bậc 1 có ít nhất một bo mạch tham chiếu (`REFERENCE_BOARDS`, phần tử đầu là mặc định); mỗi profile `sim-*` soi đúng một bo tham chiếu (`SIM_MIRRORS`) và không giàu năng lực hơn nó; mỗi nguyên thủy mở rộng có trên ít nhất một bo tham chiếu của mỗi target bậc 1; `verify` replay mọi bo tham chiếu, và `build` không `--board` không bao giờ tự chọn bo khác | §3.2 |

**Giới hạn đã biết, phải nêu rõ trong tài liệu kỹ thuật:** `sim` không mô phỏng phản xạ âm học phòng vang, nhiễu micro, beamforming mảng micro, và phân mảnh bộ nhớ trên vi điều khiển. Các nhóm lỗi này được kiểm soát bằng kiểm thử nightly trên bo mạch thật (NFR-REL-03).

**Giả lập trước, phần cứng thật sau (Q-72).** Ba vòng của hành trình 0 chạy trên bốn **tầng giả lập** trước khi mua phần cứng — mã tầng `G1`–`G4` ở đây khác cột mốc G1–G4 của §11.2 và khác giả định `G-a`… ở §13.3:

| Tầng | Công cụ | Chạy được gì | Dùng cho |
|:---|:---|:---|:---|
| **G1** Mô hình vật lý | `sim` của NeuroEdge thêm mô hình vật lý (FR-TGT-07) | Hợp đồng, gate, agent vận hành, bộ phát hiện, chi phí LLM | Vòng ② và ③; CI |
| **G2** Runtime `linux` giả ngoại vi | `gpio-sim` của kernel (đã dùng ở job `linux-hal`), thêm cảm biến giả | Đúng runtime sẽ chạy trên Pi, chỉ thiếu điện | Chạy liên tục 2 tuần trước khi có Pi (B7) |
| **G3** Firmware ESP32 trên máy | Espressif QEMU (Q-21), các spike giả lập của Q-69; Wokwi và Velxio là lựa chọn Q-72 nêu, cần đối chiếu lại với phần "không dùng" của Q-21 và Q-69 trước khi vào CI | Firmware có `ne_gate`, phản xạ khi mất mạng | Kiểm tầng phản xạ |
| **G4** Đường của maker Home Assistant | ESPHome host platform (cảm biến thay bằng template sensor) | Người dùng HA thử Blueprint không cần bo | Thử với cộng đồng HA, ESPHome |

Giả lập không bắt lỗi đấu dây, nhiễu điện, cảm biến trôi hay Wi-Fi chập chờn (R-16); phần cứng thật phải được mua trước khi bán Blueprint đầu tiên.

### 4.3 Trừu tượng hóa mô hình AI (FR-MDL)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-MDL-01** | Mọi truy cập mô hình đi qua interface `SystemOne` hoặc `SystemTwo`; giao diện kết nối mặc định tuân chuẩn OpenAI API | P0 | Không tồn tại lời gọi trực tiếp SDK nhà cung cấp trong lõi | §3.6 |
| **FR-MDL-02** | `SystemOne` hỗ trợ đúng 3 kiểu nguyên thủy: `bool`, `level`, `choice` | P0 | Ba kiểu chạy được và ánh xạ trực tiếp vào khối `evaluate` của gate | §3.6, Phụ lục B.2 |
| **FR-MDL-03** | Cả hai interface bắt buộc khai báo được đường dẫn dự phòng (`fallback`). Với `SystemOne`, fallback cục bộ là **bộ nhận diện lệnh cố định** (ngữ pháp lệnh → intent kèm độ tin cậy) và là P0 *(Q-14)* | P0 | Ngắt nhà cung cấp chính → hệ thống tự chuyển fallback, ghi sự kiện vào vết; mất mạng → `SystemOne` lượng giá bằng ngữ pháp lệnh cục bộ *(Q-14)* | §3.6 |
| **FR-MDL-04** | Thay nhà cung cấp mô hình không yêu cầu sửa mã agent hay sửa gate | P0 | Đổi `SystemOne` sang mô hình cục bộ chỉ bằng thay đổi cấu hình | §3.6 |
| **FR-MDL-05** | Chính sách định tuyến System 1 / System 2 là cấu hình khai báo, không viết cứng | P1 | Đổi ngưỡng tự tin leo thang bằng cấu hình, không biên dịch lại | §3.5 |
| **FR-MDL-06** | Hệ thống ghi nhận tỷ lệ sử dụng System 1 / System 2 và chi phí từng lượt | P0 | Số liệu xuất hiện trong tệp vết ghi của mỗi phiên: mỗi lượt gọi System 2 là một sự kiện `system_two_call` (provider, model, độ trễ, token, `cost_usd`; không prompt, không key); tỷ lệ S1/S2 ở `session_summary`, đường phục vụ và độ trễ từng chặng của mỗi lượt ở `turn_latency` (`docs/spec/tool_calling.md` §7.1). *Q-72:* `cost_usd` của từng lượt là cơ sở của trần chi phí LLM của agent vận hành (FR-AGT-05) | §12.1, Q-72 |
| **FR-MDL-07** | **Provider pluggable:** LLM, ASR và TTS kết nối qua chuẩn OpenAI API hoặc adapter do người dùng tự viết | P0 | Thêm một provider tương thích OpenAI chỉ bằng cấu hình endpoint và khóa (bảng `[system_two]`: `model`, `api_base`, `api_key_env`), không sửa mã | §3.6, §6.1 |
| **FR-MDL-08** | **Adapter tùy chỉnh:** người dùng viết được logic kết nối riêng cho provider chưa hỗ trợ chuẩn OpenAI | P0 | Một adapter mẫu do bên ngoài viết (`provider = "python:pkg.mod:factory"`, hợp đồng `neuroedge/models/providers/base.py`) chạy được mà không sửa lõi NeuroEdge | §3.6 |
| **FR-MDL-09** | **ASR/TTS là provider:** STT và TTS không gắn cứng vào một thư viện, thay thế được qua cấu hình | P0 | Đổi nhà cung cấp STT và TTS chỉ bằng cấu hình; agent và gate không đổi | §3.4, §3.6 |
| **FR-MDL-10** | **Hành động là tool call (Q-24):** mọi `@action` là một tool có schema sinh từ chữ ký; `SystemOne`, `SystemTwo`, ngữ pháp lệnh cục bộ và client MCP gọi hành động bằng cùng một `ToolCall`, qua cùng một gate — theo `docs/spec/tool_calling.md` | P0 | Tool lạ hoặc tham số lạ/sai kiểu ⇒ `REJECTED`, không chân nào đổi; cùng một lời gọi từ nguồn khác nhau nhận cùng phán quyết trừ khi gate đọc `call_source`; mất mạng thì câu khớp ngữ pháp vẫn thành tool call; runtime qua corpus `fixtures/tool_calls/` (`docs/spec/tool_calling.md` §9) | §3.6, Q-24 |
| **FR-MDL-11** | **Vòng tool của System 2:** kết quả mỗi tool call (kể cả BLOCK và lý do) trả lại cho System 2 để trả lời người dùng; số vòng có giới hạn khai báo | P0 | Gate chặn ⇒ System 2 nói lý do thay vì lặp lại lời gọi; quá giới hạn vòng ⇒ dừng, ghi sự kiện | `docs/spec/tool_calling.md` §4 |
| **FR-MDL-12** | **System 2 là MCP host (Q-27):** gọi tool của thiết bị qua MCP server của chính agent (vẫn qua gate) và tool **thông tin** của MCP server bên ngoài khai trong `[mcp.servers]` (allowlist); kết quả bên ngoài là dữ liệu không tin cậy | P0 | Tool ngoài allowlist ⇒ `REJECTED`; server không chạy ⇒ `mcp_server_unavailable`, tool thiết bị vẫn chạy; nội dung bên ngoài bị cài lệnh không vượt được gate; vết ghi chỉ có digest | `docs/spec/tool_calling.md` §10 |

### 4.4 Tầng nhận thức và runtime hội thoại (FR-PER)

Nguyên tắc: **tích hợp thư viện mã nguồn mở tốt nhất, không tự viết lại thuật toán xử lý tín hiệu cơ bản.**

*Tạm dừng theo Q-72:* nhóm FR-PER làm sau hợp đồng nhiệm vụ, agent vận hành, kênh chat và Blueprint; phạm vi v1.0 xét lại ở cổng 8 tuần (áp dụng cho NFR-PERF-01, NFR-PERF-07, A6).

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-PER-01** | Tích hợp sẵn chuỗi xử lý giọng nói theo hai tầng: **(a) trên thiết bị** — wake-word, VAD, AEC, thu/phát âm thanh, máy trạng thái hội thoại; **(b) trên cloud** — STT, TTS và suy luận ngôn ngữ qua provider | P0 | Agent mẫu hoạt động end-to-end chỉ với cấu hình provider, không cần cấu hình thêm thư viện | §3.4 |
| **FR-PER-02** | **Cắt lời (barge-in):** ngắt TTS ngay khi người dùng bắt đầu nói, đồng thời thu hồi lệnh actuator chưa thực thi | P0 | Kịch bản kiểm thử: cắt lời giữa câu → TTS dừng < 300 ms, không có lệnh actuator nào rò rỉ | §3.4 |
| **FR-PER-03** | **Khoảng lặng động:** phân biệt dừng để suy nghĩ với kết thúc lượt nói | P0 | Người nói chậm không bị cắt lời trong bộ kịch bản kiểm thử chuẩn | §3.4 |
| **FR-PER-04** | **Phản hồi dòng từng phần:** phát âm thanh từ token đầu tiên, rút lại an toàn khi mô hình đổi kết luận | P1 | Rút lại không gây phát trùng hoặc mất đoạn | §3.4 |
| **FR-PER-05** | **Tự phục hồi lỗi STT:** chuỗi rỗng hoặc nhiễu không làm treo máy trạng thái, không lặp câu hỏi vô hạn | P0 | Bơm 20 khung nhiễu liên tiếp → máy trạng thái vẫn phản hồi đúng | §3.4 |
| **FR-PER-06** | Runtime giọng nói trên `esp32s3` tối ưu bộ nhớ, gồm thu/phát âm thanh, WebRTC AEC, VAD libfvad *(khớp `docs/spec/voice_fsm.md`)*, Opus streaming, máy trạng thái hội thoại, thẩm định gate và bộ nhận diện lệnh cố định cục bộ *(ESP-SR MultiNet hoặc TFLite Micro / ESP-NN, chọn ở Khối 1b — Q-14)*. **Không bắt buộc chạy STT/TTS trên thiết bị** | P0 | Chạy ổn định liên tục 24 giờ trên bo mạch tham chiếu với pipeline thu/phát + máy trạng thái + gate, không tràn bộ nhớ | §8.2 |
| **FR-PER-07** | **Cloud-first voice:** STT và TTS mặc định chạy trên cloud qua provider; vi điều khiển chỉ truyền luồng âm thanh lên và nhận luồng âm thanh về | P0 | Vòng lặp thoại chạy end-to-end trên bo mạch tham chiếu với STT/TTS đặt ở provider cloud | §3.4, §6.1 |

### 4.5 Agent vận hành (FR-AGT)

*Dự kiến — Q-72, increment I2d; chưa có mã.* Agent vận hành chạy liên tục trên máy nhà (Pi, mini PC, NAS) sau khi phiên client MCP đóng. Hôm nay mọi tiến trình NeuroEdge sống trong lệnh đang chạy (`run`, `mcp serve`); I2d thêm tiến trình sống lâu đầu tiên. Nó tách thành **hai tiến trình**, dùng lại ranh giới của Q-71 (chỉ một tiến trình giữ quyền thiết bị; client MCP là bên gọi không tin cậy):

- **Runtime tin cậy** — HAL và quyền thiết bị, gate, thực thi hợp đồng nhiệm vụ, lập lịch, bộ phát hiện tất định, adapter kênh chat và kiểm lời duyệt, cửa ra dữ liệu (FR-EGR), vết ghi. Không gọi LLM, không giữ key LLM.
- **LLM worker không tin cậy** — giữ key LLM của người dùng (BYOK), gọi runtime như một client MCP cục bộ; nguồn do runtime gán; không bao giờ duyệt.

Agent vận hành **không dựng và không khoá** hợp đồng (vai của NeuroEdge Lab, Q-71): LLM lúc chạy chỉ giải thích và *đề xuất* sửa đổi. Phân rã thành gói và tiến trình: `docs/architecture/`.

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-AGT-01** | **Runtime tin cậy chạy liên tục:** một tiến trình sống lâu (dịch vụ systemd hoặc tương đương) giữ toàn bộ phần tin cậy liệt kê trên; khởi động lại tự động sau lỗi hoặc mất điện; mỗi lần khởi động lại là một sự kiện trong vết ghi | P0 | Giết tiến trình runtime ⇒ được khởi động lại, mọi cơ cấu đã về `safe_state` trong lúc vắng nhờ thời lượng/lease trên thiết bị (FR-ACE-03), vết ghi có sự kiện khởi động lại; chạy liên tục 2 tuần trên G2 hoặc G3 không can thiệp (B7, NFR-REL-06) | Q-72 |
| **FR-AGT-02** | **LLM worker không tin cậy:** tiến trình riêng giữ key BYOK, gọi mô hình qua LiteLLM (FR-MDL-07; gồm mô hình tại chỗ như Ollama); gọi runtime qua MCP cục bộ; nguồn do runtime gán theo kết nối, không tự khai (FR-ACE-09); mọi lời gọi hành động qua gate; không có quyền thiết bị; không bao giờ là nguồn người | P0 | Bộ test thâm nhập: worker tự khai `call_source` ⇒ `REJECTED`; worker gửi lời xác nhận `ask` hay lời duyệt ⇒ bị từ chối (FR-CH-05); user của worker không mở được `/dev/gpiochip*`, `/dev/i2c-*`; key không xuất hiện trong vết ghi, hợp đồng, Blueprint hay tin chat (NFR-SEC-13) | Q-71, Q-72 |
| **FR-AGT-03** | **Lập lịch:** chạy điều khoản theo giờ và chu kỳ (đọc cảm biến, bản tóm tắt, hết hạn quyền); thời lượng, hạn, chu kỳ đo bằng **đồng hồ đơn điệu**; giờ tường chỉ dùng cho điều khoản khung giờ, qua dữ kiện có trạng thái `unsynced` (FR-MSN-04). Một lần đọc cảm biến kẹt không được chặn vòng lặp của runtime — `TODOS.md` #48 thành rủi ro thật. Nền sẵn có: trigger theo sự kiện của NeuroEdge Lab (khối N6: chạy không cần phiên client, debounce, trần tần suất, nguồn ngoài `HUMAN_SOURCES`) | P0 | Kịch bản G1: đổi giờ tường (NTP nhảy) không làm thời lượng hay hạn duyệt dài ra hay ngắn đi; bus kẹt một cảm biến không làm trễ phản xạ của cảm biến khác quá ngân sách gate | Q-72 |
| **FR-AGT-04** | **Bộ phát hiện tất định trước, LLM sau:** ngưỡng, độ dốc xu hướng (ví dụ oxy giảm 3 ngày liền), cảm biến đứng im, dao động — tính bằng mã thường, khai trong hợp đồng nhiệm vụ hoặc Blueprint; LLM chỉ được gọi khi một bộ phát hiện bắn sự kiện, hoặc cho bản tóm tắt theo lịch; sự kiện bộ phát hiện ghi vào vết ghi và replay được | P0 | Kịch bản 30 ngày trên G1: bộ phát hiện xu hướng oxy bắn đúng ngày, không bắn trên chuỗi đối chứng; số lần gọi LLM bằng số sự kiện bắn cộng số bản tóm tắt; replay vết ghi cho cùng chuỗi sự kiện bộ phát hiện | Q-72 |
| **FR-AGT-05** | **Trần chi phí LLM (`llm_budget`):** runtime cưỡng chế trần khai trong hợp đồng (FR-MSN-09) **trước** mỗi lần giao việc cho worker, cộng dồn từ `cost_usd` của từng lượt (FR-MDL-06); chi phí một lượt không đo được thì tính theo đơn giá khai trong cấu hình, không có đơn giá thì không gọi. Chạm trần ⇒ không gọi LLM tới hết kỳ; phản xạ, bộ phát hiện và cảnh báo mẫu cứng vẫn chạy; người dùng nhận đúng một tin "đã hết ngân sách phân tích kỳ này" | P0 | Kịch bản G1 đặt trần thấp: sau khi chạm trần không còn sự kiện `system_two_call` nào; tổng chi phí của kỳ không vượt trần quá chi phí của lượt đang chạy lúc chạm; tin khẩn vẫn tới (NFR-COST-01) | Q-72 |
| **FR-AGT-06** | **Báo chủ động, gom tin, ngân sách tin nhắn:** giải thích xu hướng và đề xuất do LLM viết, gửi qua kênh chat đã ghép (FR-CH-01); tin thường được gom thành bản tóm tắt (ví dụ một bản mỗi ngày là một lần gọi LLM); **tin khẩn dùng mẫu cứng**, không cần LLM, không bị gom hay trễ; vượt ngân sách tin nhắn ⇒ tin thường dồn vào bản tóm tắt kế tiếp. Đề xuất sửa hợp đồng đi đúng đường sửa đổi (FR-MSN-14) | P0 | Kịch bản 30 ngày: số tin không khẩn không vượt ngân sách khai (NFR-COST-02); mọi tin khẩn tới trong ngân sách độ trễ của nó; một đề xuất xu hướng tới chat kèm yêu cầu duyệt | Q-72 |
| **FR-AGT-07** | **Nhánh lỗi:** worker chết hay treo ⇒ runtime vẫn phản xạ, chạy bộ phát hiện, gửi cảnh báo mẫu cứng, khởi động lại worker, báo "phân tích tạm ngưng"; kênh chat sập ⇒ hàng đợi có hạn + cảnh báo tại chỗ trên UI cục bộ, tin tới trễ mang dấu thời gian gốc; hết ngân sách LLM ⇒ FR-AGT-05; yêu cầu duyệt hết hạn ⇒ không duyệt (FR-CH-04); relay mất ⇒ không ảnh hưởng an toàn (FR-EGR-05); mất điện ⇒ vết ghi theo FR-TRC-12 | P0 | Mỗi nhánh có một kịch bản G1 (hoặc G2) với kết quả kỳ vọng ghi trước; không nhánh nào làm một cơ cấu rời `safe_state` hay làm mất một phán quyết chặn đã ghi | Q-72 |
| **FR-AGT-08** | **Định tuyến mô hình cho agent:** mô hình tại chỗ cho tóm tắt thường, mô hình mạnh cho đề xuất — cùng qua LiteLLM, khai bằng cấu hình (FR-MDL-05, FR-GW-03) | P1 | Đổi mô hình của từng loại việc chỉ bằng cấu hình; chi phí từng loại hiện riêng trong vết ghi | Q-72 |
| **FR-AGT-09** | **Agent không dựng, không khoá:** runtime và worker không có đường nào khoá bản nháp, sửa gate đã khoá, `digests.lock`, profile `board.v1` hay hợp đồng nhiệm vụ đã khoá; mọi thay đổi đó đi qua người (FR-MSN-14, Q-71) | P0 | Bộ test: mọi tool MCP mà runtime phơi cho worker đều không ghi được các tệp trên; danh sách tool ghim bằng test | Q-71, Q-72 |
| **FR-AGT-10** | **Não trên cloud tuỳ chọn** *(planned · Q-74 bước 2, có điều kiện)*: LLM worker, trò chuyện và biên dịch hợp đồng nhiệm vụ được chạy trên NeuroEdge Cloud; runtime tin cậy (gate, phản xạ, kiểm lời duyệt, cửa ra dữ liệu, vết ghi) luôn ở hộp tại nhà, mở kết nối ra, không mở cổng | P2 | Cắt kết nối cloud ⇒ phản xạ và gate vẫn chạy; cloud gửi luật không có chữ ký hợp lệ hay lời duyệt không kiểm được tại chỗ ⇒ hộp từ chối, ghi vết | Q-74 |
| **FR-AGT-11** | **Mạng lưới đa nút, đa nhà** *(planned · Q-74)*: một agent điều phối nhiều ESP32, nhiều Pi, nhiều nhà; mỗi nút chỉ thi hành luật có chữ ký và tự về an toàn khi mất kết nối; một lệnh không chạm quá số thiết bị hay số nhà khai sẵn nếu không có lời duyệt riêng; việc không hoàn tác ở bất kỳ nhà nào luôn cần người xác nhận | P2 | Lệnh giả từ cloud mở khoá ⇒ bị chặn tại nút; lệnh vượt trần phạm vi ⇒ chặn và báo; mỗi nút có danh tính và vết ghi riêng | Q-74 |
| **FR-AGT-12** | **Bộ não NeuroEdge tự host hoặc trên cloud** *(planned · Q-76; demo nội bộ 2026-10-13: `demo/i2f-chat-den-cua/`)*: cùng một worker (trò chuyện, LLM, trí nhớ, lịch) chạy trên board Linux rẻ của người dùng hoặc trên NeuroEdge Cloud, mỗi người một instance cách ly; worker chỉ chạm thế giới qua bộ tool MCP của runtime, không có lệnh shell hay công cụ phần cứng | P2 | Worker bị chiếm (prompt injection, `exec`) không bật được chân nào; cùng bản worker chạy tự host và trên cloud không rẽ nhánh mã; instance của người này không đọc được trí nhớ người kia | Q-76 |

---

## 5. Yêu cầu chức năng — An toàn hành động

### 5.1 Động cơ hợp đồng hành động (FR-ACE)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-ACE-01** | Mọi lệnh tới cơ cấu chấp hành **bắt buộc** đi qua gate tương ứng; không tồn tại đường tắt | P0 | Kiểm thử thâm nhập: không có API công khai nào kích hoạt GPIO mà bỏ qua gate | §3.5 |
| **FR-ACE-02** | Hành động vật lý chỉ gọi được qua `c.do()`; gọi trực tiếp sinh `ActionContractViolation` | P0 | Test khẳng định ngoại lệ được ném và chân GPIO không bị kích | §4.4 |
| **FR-ACE-03** | **Fail-closed mặc định cho lệnh:** timeout, hoặc mô hình trả dữ liệu không hợp lệ → chặn hành động. **Mất mạng** → gate vẫn lượng giá bằng bộ nhận diện lệnh cố định cục bộ; chỉ chặn với `gate_unreachable` khi fallback không có hoặc không chạy được *(Q-14)*. **Cơ cấu về `safe_state` đã khai** *(chờ RFC an toàn có điều kiện — Q-72)*: mỗi cơ cấu có `safe_state` khai trong `board.v1`, mặc định `off` (hôm nay chỉ `motion.*` có `safe_state`: `stop`/`hold`); thời lượng, `max_continuous_ms`, lease, mức tự tắt L0–L3 của cơ cấu từ xa (RFC-0018) và miễn gate của Q-62 đều nói về "trở về `safe_state`", còn hướng **rời** `safe_state` là hướng bị gate và giới hạn. `safe_state` khác `off` **chỉ** khai được trong `board.v1` — không trong hợp đồng nhiệm vụ, gate hay Blueprint — và cơ cấu `safe_state: on` bắt buộc khai kèm **khoá liên động phần cứng** (đấu dây mặc định bật như rơ-le thường đóng, cầu chì nhiệt, phao); phần mềm chỉ lệnh rời trạng thái đó, có hạn. Sửa `TODOS.md` #58 trước, để đầu đọc cũ không lặng lẽ bỏ khoá mới. Profile hiện có giữ nguyên hành vi | P0 | Kịch bản `network=offline` → gate lượng giá bằng ngữ pháp lệnh cục bộ: câu khớp đủ độ tin cậy được phán quyết theo `allow_when`, câu không khớp hoặc dưới ngưỡng bị BLOCK theo tiêu chí bình thường. Kịch bản `network=offline` + fallback không có/không chạy → hành động bị chặn với lý do `gate_unreachable`. *Khi RFC vào:* `board.v1` khai `safe_state: on` thiếu khoá liên động ⇒ từ chối nạp (A21); `safe_state` khai trong hợp đồng, gate hay Blueprint ⇒ từ chối; sục khí bể cá `safe_state: on` vẫn chạy khi mất mạng, mất LLM, lease hết (A16); lệnh "tắt sục khí 10 phút" bị gate và tự trở về bật khi hết hạn; ba vết ghi chuẩn mực và mọi corpus chạy lại y nguyên với profile hiện có | §3.5, Q-62, Q-72 |
| **FR-ACE-04** | Decorator `@action` ràng buộc `requires` tham gia đối chiếu năng lực lúc build | P0 | Thiếu năng lực → build dừng, chỉ rõ dòng mã gọi | §4.4 |
| **FR-ACE-05** | Decorator `@action` bắt buộc trỏ tới một gate đã khai báo trong `agent.toml` | P0 | Thiếu khai báo gate → build dừng | §4.4 |
| **FR-ACE-06** | Mỗi phiên tương tác sinh một tệp vết ghi JSON đầy đủ. *Runtime 24/7 của agent vận hành (Q-72, chờ RFC):* một phiên là một **chuỗi đoạn** vết ghi, mỗi đoạn replay được (FR-TRC-11) | P0 | Tệp chứa độ trễ từng chặng, kết quả đánh giá gate, lệnh actuator | §3.5 |
| **FR-ACE-07** | Tách biệt kiểu giữa hành vi phát ngôn (`c.say()`) và hành vi vật lý (`c.do()`) | P0 | `c.say()` không đi qua gate; `c.do()` luôn đi qua gate | §4.6 |
| **FR-ACE-08** | **Ràng buộc tham số trong gate (Q-25):** gate khai khoảng/tập giá trị cho tham số của hành động; kế thừa chỉ thu hẹp | P0 | Tool call với tham số ngoài khoảng ⇒ BLOCK `argument_out_of_range`, chân không đổi; gate con nới khoảng ⇒ `GateInheritanceError` | RFC-0005 |
| **FR-ACE-09** | **Nguồn gọi là dữ kiện tin cậy:** dispatcher chèn `call_source`; bên gọi không tự khai được | P0 | Tool call mang tham số `call_source` ⇒ `REJECTED`; gate giới hạn được nguồn gọi | `docs/spec/tool_calling.md` §5 |
| **FR-ACE-10** | **Chỉ người xác nhận `ask` (Q-26):** lời xác nhận đến từ kênh thiết bị, gắn với lần bị chặn, dùng một lần, có hạn. *Mở rộng bởi Q-72 (chờ RFC nguồn `chat:<id>`):* người cũng xác nhận được qua **kênh chat đã ghép đôi**, chỉ bằng **bản ghi duyệt** đã kiểm (FR-CH-04) — cho cả `ask` lúc chạy lẫn sửa đổi hợp đồng nhiệm vụ; LLM, nhóm chat và tài khoản chưa ghép đôi không bao giờ xác nhận được | P0 | Xác nhận từ `system_two` hoặc `mcp` bị từ chối; xác nhận quá hạn hoặc dùng lại ⇒ không có tác dụng; xác nhận hợp lệ ⇒ gate lượng giá lại, chỉ thay tiêu chí trong `confirms` (RFC-0006). *Q-72:* lời duyệt chat chỉ vào đường xác nhận khi bản ghi duyệt qua đủ phép kiểm của FR-CH-04; LLM worker gửi lời xác nhận ⇒ bị từ chối (A20) | `docs/spec/tool_calling.md` §6, Q-72 |

### 5.2 Định dạng cổng an toàn (FR-GATE)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-GATE-01** | Gate là tệp YAML có schema `neuroedge.gate/v1`, **không phải mã nguồn** | P0 | Gate đọc, diff và review được trong pull request | §3.5 |
| **FR-GATE-02** | Gate có 8 trường cấp cao: `schema`, `name`, `version`, `extends`, `evaluate`, `allow_when`, `on_block`, `budget`. Chỉ `schema`, `name`, `version` **luôn bắt buộc**; `evaluate`, `allow_when`, `on_block`, `budget` bắt buộc khi gate **không có** `extends` *(RFC-0001)*. `budget.fail` tuỳ chọn — vắng mặt nghĩa là `closed` | P0 | Thiếu trường bắt buộc theo điều kiện trên → `GateSchemaError`; gate có `extends` lược bốn trường kế thừa vẫn hợp lệ | Phụ lục B.1, RFC-0001 |
| **FR-GATE-03** | Khối `evaluate` hỗ trợ 4 kiểu: `bool`, `level`, `choice` và `numeric` (RFC-0009: `unit`, `range`, `max_age_ms` bắt buộc), kèm toán tử điều kiện tương ứng. `allow_when` **dạng ánh xạ toán tử là dạng v1**; dạng chuỗi CEL chỉ được phép ở gate không có `extends` — trong chuỗi kế thừa bị từ chối, fail-closed, vì không chứng minh được con chặt hơn cha. *Cho tới khi trình biên dịch CEL xong (TSK-S2-06, đang hoãn), `gate lint` từ chối cả CEL ở gate độc lập (`GateSchemaError`) — fail-closed, không phải lượng giá thiếu* | P0 | Bốn kiểu chạy đúng với toán tử `eq`, `lte`, `gte`, `in`, `not_in`, `confidence_gte` và, cho `numeric`, `gt`, `gte`, `lt`, `lte`; `allow_when` dạng chuỗi trong chuỗi `extends` → `GateInheritanceError` | Phụ lục B.2, Q-9 |
| **FR-GATE-04** | Khối `on_block` hỗ trợ 4 hành vi: `escalate`, `deny`, `ask`, `degrade`. Ở v1.0, **mọi** `on_block` đều chặn hành động vật lý; `escalate`/`ask` ghi sự kiện + gọi hook (mặc định no-op); `degrade` chạy `fallback_action` qua gate của chính nó *(Q-17)*. `ask` có `confirms`: lời xác nhận của người trên kênh thiết bị làm gate lượng giá lại *(Q-26, RFC-0006)*. *Q-72 (dự kiến, I2d):* khi agent vận hành chạy, `ask` và `escalate` được chuyển tới kênh chat đã ghép (người nhận `escalate` thật — một phần `TODOS.md` #20); lời trả lời cho `ask` chỉ có hiệu lực qua bản ghi duyệt (FR-CH-04). Thêm trạng thái **"báo động, gọi người"** cho cơ cấu mà cả hai hướng đều nguy hiểm (ví dụ sục khí quá nhiệt): cơ cấu giữ `safe_state` đã khai, runtime gửi tin khẩn mẫu cứng và chờ người — không bao giờ để LLM chọn | P0 | Bốn hành vi chạy đúng và được ghi vào vết. *Q-72:* `ask`/`escalate` lúc runtime chạy tạo một yêu cầu duyệt trong chat; trạng thái "báo động, gọi người" có kịch bản G1 riêng | Phụ lục B.3, Q-72 |
| **FR-GATE-05** | Gate kế thừa được qua `extends` từ URI gate cơ sở | P0 | Kéo gate cộng đồng về, ghi đè phần riêng, chạy đúng | Phụ lục B.5 |
| **FR-GATE-06** | **Gate con chỉ được siết chặt, tuyệt đối không được nới lỏng** (B.5 nguyên tắc 2) — với `allow_when`, và từ RFC-0004 cả với `budget`/`on_block` *(Q-18)*: `p95_latency_ms` của con ≤ của cha; con không được tự đưa vào `degrade`/`fallback_action` mới (chỉ giữ nguyên của cha), được đổi sang `deny`/`escalate`/`ask` và đổi `to`/`message` | P0 | Gate con nới lỏng `allow_when`, `budget` hoặc `on_block` của cha → `GateInheritanceError` (NE2003, nguyên tắc 2), từ chối phân giải *(phần `budget`/`on_block`: TSK-S2-13)* | Phụ lục B.5, RFC-0004 |
| **FR-GATE-07** | `fail: open` **không kế thừa**; phải khai báo tường minh tại từng cấp (B.5 nguyên tắc 4). Từ RFC-0004: chuỗi đã phân giải thành `closed` (khai hoặc mặc định) thì gate con **không được** mở lại bằng `fail: open` *(Q-18)* | P0 | Gate cha `fail: open`, gate con không khai báo → gate con là `closed`; chuỗi đã `closed`, con khai `fail: open` → `GateInheritanceError` (NE2003, nguyên tắc 4) | Phụ lục B.5, RFC-0004 |
| **FR-GATE-08** | Độ sâu kế thừa tối đa 3 cấp; vòng lặp phụ thuộc bị chặn khi phân giải | P0 | Chuỗi 4 cấp hoặc vòng lặp → lỗi phân giải rõ ràng | Phụ lục B.5 |
| **FR-GATE-09** | `budget.p95_latency_ms` vượt ngưỡng được xử lý như một trường hợp lỗi | P0 | Vượt ngân sách → áp dụng chính sách `fail` đã khai báo | Phụ lục B.4 |
| **FR-GATE-10** | Thay đổi `allow_when` được coi là thay đổi phá vỡ tương thích, bắt buộc tăng phiên bản chính | P1 | Công cụ cảnh báo khi sửa `allow_when` mà không tăng major version | Phụ lục B.1 |

**Lý do nghiệp vụ của FR-GATE-06 và FR-GATE-07:** hai nguyên tắc này là điều kiện để việc tái sử dụng gate cộng đồng an toàn. Thiếu chúng, `extends` trở thành một rủi ro thay vì một tính năng.

### 5.3 Cập nhật firmware cấp thiết bị (FR-OTA)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-OTA-01** | Thiết bị hỗ trợ nạp firmware phân vùng kép A/B | P0 | Cập nhật thất bại không làm mất phân vùng đang chạy | §6.4 |
| **FR-OTA-02** | Thiết bị tự động rollback cục bộ khi phát hiện vòng lặp khởi động | P0 | Nạp firmware lỗi cố ý → thiết bị tự quay về bản cũ, không cần can thiệp | §6.4 |
| **FR-OTA-03** | Thiết bị xác minh chữ ký mật mã (RSA hoặc ECDSA) của firmware trước khi áp dụng | P0 | Firmware không chữ ký hoặc sai chữ ký bị từ chối | §6.4 |
| **FR-OTA-04** | Thiết bị nạp được firmware từ một HTTP endpoint mở bất kỳ, **không bắt buộc dùng dịch vụ của NeuroEdge** | P0 | Tự dựng máy chủ firmware và cập nhật thành công mà không có tài khoản | §6.4 |

**Ràng buộc nguyên tắc P-3:** FR-OTA-01 đến FR-OTA-04 thuộc lõi, không tách thành gói trả thêm (Q-45). Phần thương mại hóa chỉ là điều phối chiến dịch quy mô lớn (FR-FLT-02).

### 5.4 Hợp đồng nhiệm vụ (FR-MSN)

*Dự kiến — Q-72, increment I2d; chưa có mã.* Hợp đồng nhiệm vụ là đơn vị luật cho cả chuỗi hành động trên nhiều thiết bị. Nó **không thay gate**: mỗi hành động vẫn trỏ một gate đã khoá, gate vẫn là hàm thuần; hợp đồng gộp, **chỉ siết** và lập lịch chúng. Trình biên dịch hạ mỗi điều khoản xuống tầng thấp nhất cưỡng chế được: **phản xạ** (thiết bị có `ne_gate`, mili giây, chạy khi mất mạng), **kỹ năng** (runtime trên host, giây), **suy nghĩ** (LLM worker, giây tới phút). Lược đồ `mission.v1` chạm `schemas/`, nên **cần RFC** (RFC dự kiến, `CONTRIBUTING.md` §3); bảng dưới là yêu cầu RFC đó phải đáp ứng.

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-MSN-01** | **Hợp đồng là dữ liệu có phiên bản:** tệp theo lược đồ `mission.v1` (cần RFC), không phải mã; nêu thiết bị, hành động và gate liên quan, điều khoản, tham số, người khoá; chỉ người khoá được, LLM và agent thì không | P0 | Hợp đồng sai lược đồ ⇒ từ chối kèm lỗi ba phần (FR-DX-04); hợp đồng trỏ gate chưa khoá (`-draft`) ⇒ từ chối; hai lần biên dịch cùng hợp đồng cho cùng digest | Q-72 |
| **FR-MSN-02** | **Được / cấm:** điều khoản cho phép và cấm hành động, kèm khoảng tham số; điều khoản chỉ **siết** so với gate của hành động, như kế thừa gate (Phụ lục B.5 nguyên tắc 2, RFC-0005) | P0 | Điều khoản "được" rộng hơn gate ⇒ từ chối biên dịch, nêu điều khoản và gate; lệnh thuộc "cấm" ⇒ BLOCK, lý do trỏ đúng điều khoản (ví dụ "tắt sục khí cho yên tĩnh") | Q-72 |
| **FR-MSN-03** | **Tần suất, thời lượng:** "tối đa N lần mỗi giờ", "chạy không quá T" hạ xuống phong bì sẵn có (`window_s`, `max_on_ms_per_window`, `min_interval_ms`, `max_continuous_ms` — RFC-0007, RFC-0010) và chỉ siết phong bì của bo | P0 | Điều khoản nới phong bì của bo ⇒ từ chối; lệnh vượt tần suất ⇒ `EnvelopeRefusedError` hoặc BLOCK như hôm nay | Q-72 |
| **FR-MSN-04** | **Khung giờ:** điều khoản "chỉ 23:00–05:00" đọc một **dữ kiện giờ tường do runtime chèn** (mới — hôm nay `RUNTIME_CRITERIA` chỉ có `call_source`, `call_channel`); dữ kiện có trạng thái `unsynced` khi máy nhà chưa có NTP hay RTC; điều khoản khung giờ coi `unsynced` là **thiếu dữ kiện** (fail-closed với lệnh rời `safe_state`). Thời lượng, hạn duyệt, watchdog, phản xạ dùng đồng hồ đơn điệu | P0 | Kịch bản mất điện, không NTP/RTC: lệnh chỉ được phép trong khung giờ bị chặn như thiếu dữ kiện; bản duyệt và UI báo "đồng hồ chưa đồng bộ"; cơ cấu không rời `safe_state` | Q-72 |
| **FR-MSN-05** | **Nghĩa vụ ("phải") là watchdog có cận:** khuôn duy nhất "X vượt ngưỡng quá T ⇒ Y về `safe_state` (hoặc trạng thái 'báo động, gọi người') và báo"; T, ngưỡng và hành động đều có cận khai; không có nghĩa vụ tự do. Hướng về `safe_state` không cần gate (Q-62 theo FR-ACE-03); hướng khác đi qua gate | P0 | Kịch bản bể cá: sưởi trên 30 °C quá 10 phút ⇒ ngắt sưởi và báo động, cả khi mất mạng nếu thiết bị có tầng phản xạ; nghĩa vụ thiếu cận ⇒ từ chối biên dịch | Q-72 |
| **FR-MSN-06** | **Luồng dữ liệu:** hợp đồng khai các **đích** (nhà cung cấp LLM, kênh chat, relay, webhook) và loại dữ liệu mỗi đích được nhận; mặc định đích người dùng khai nhận dữ liệu người dùng cho phép, kể cả ảnh tới LLM; **luật nội dung** ("ảnh không rời nhà", từ vựng sự kiện đóng) là tuỳ chọn người dùng bật. Cưỡng chế ở FR-EGR | P0 | Bản duyệt nêu mọi đích và loại dữ liệu; điều khoản thuộc loại xác suất (ví dụ "không gửi ảnh có mặt người") được ghi rõ là xác suất | Q-72 |
| **FR-MSN-07** | **Khi hỏng:** với mỗi cơ cấu, hành vi khi mất não, mạng, cảm biến hay LLM là **trở về `safe_state` đã khai trong `board.v1`**, hoặc trạng thái "báo động, gọi người" khi cả hai hướng đều nguy hiểm (FR-GATE-04); hợp đồng không khai được `safe_state` khác `off` | P0 *(chờ RFC an toàn có điều kiện)* | Hợp đồng khai `safe_state` ⇒ từ chối; mỗi cơ cấu trong bản duyệt có dòng "khi hỏng" lấy từ `board.v1` | Q-72 |
| **FR-MSN-08** | **Hết hạn:** mọi quyền trong hợp đồng có thời hạn cấp nhiệm vụ; hết hạn ⇒ quyền mất, cơ cấu về `safe_state`, người dùng được báo để gia hạn; gia hạn là một sửa đổi phải duyệt (FR-MSN-14) | P0 | Kịch bản G1 tua qua hạn: lệnh rời `safe_state` sau hạn bị chặn, có đúng một tin báo hết hạn | Q-72 |
| **FR-MSN-09** | **Ngân sách:** hợp đồng khai `llm_budget` (trần chi phí LLM mỗi kỳ, ví dụ 2 USD/tháng) và **ngân sách tin nhắn** (số tin không khẩn mỗi ngày); hành vi khi chạm trần ở FR-AGT-05, FR-AGT-06 | P0 | Hợp đồng thiếu `llm_budget` khi có điều khoản tầng suy nghĩ ⇒ từ chối biên dịch | Q-72 |
| **FR-MSN-10** | **Biên dịch theo tầng:** mỗi điều khoản được gán đúng một tầng — phản xạ, kỹ năng, suy nghĩ — là tầng thấp nhất cưỡng chế được; chỉ thiết bị có `ne_gate` có tầng phản xạ, thiết bị qua Home Assistant hay cơ cấu từ xa dừng ở tầng kỹ năng và bản duyệt nói rõ; **điều khoản an toàn không bao giờ ở tầng suy nghĩ**. Đổi bố cục `NETR` để chở điều khoản phản xạ cần RFC | P0 | Mỗi điều khoản trong bản biên dịch có đúng một tầng; điều khoản an toàn chỉ hạ được tới tầng suy nghĩ ⇒ từ chối | Q-72 |
| **FR-MSN-11** | **Từ chối mâu thuẫn trước khi duyệt:** hợp đồng mâu thuẫn (ví dụ "cấm tắt sục khí" và "tắt sục khí 2h–5h"), hay đụng `safe_state` và phong bì của bo, bị từ chối **trước** khi tới người duyệt, chỉ rõ hai điều khoản đụng nhau | P0 | Corpus hợp đồng mâu thuẫn khép kín hai chiều — mỗi tệp một đáp án (`CONTRIBUTING.md` §3); 100% bị từ chối với đúng cặp điều khoản (A15) | Q-72 |
| **FR-MSN-12** | **Bản duyệt ≤ 5 dòng:** do trình biên dịch sinh **tất định** từ diff có cấu trúc của hợp đồng, không từ chữ do LLM viết; tiếng thường; mỗi dòng ghi tầng cưỡng chế; chỉ nêu điều khoản khác mặc định; luôn nêu riêng cơ cấu có `safe_state` khác `off`, đích dữ liệu mới và điều khoản xác suất. Dùng lại năng lực của `neuroedge gate explain`. Thay đổi không tóm được trong 5 dòng thì không gửi qua chat, chỉ duyệt tại chỗ với bản đầy đủ *(đề xuất cho RFC)* | P0 | Cùng hợp đồng ⇒ cùng bản duyệt từng byte và cùng digest; bản duyệt gửi qua chat không bao giờ quá 5 dòng; LLM sửa câu chữ bản duyệt không đổi được nội dung gửi đi | Q-72 |
| **FR-MSN-13** | **Hỏi lại khi mơ hồ:** client MCP (Lab) hoặc LLM worker dịch câu nói thành bản nháp; tham số còn thiếu (ngưỡng oxy, giờ yên lặng, kênh báo) phải hỏi lại người, chỉ điền sẵn giá trị gợi ý khi Blueprint khai mặc định, và người vẫn thấy giá trị đó trong bản duyệt; bản nháp không có hiệu lực tới khi người khoá | P0 | Bản nháp thiếu tham số bắt buộc ⇒ không biên dịch được, nêu tham số cần hỏi; không đường nào bật bản nháp chưa khoá | Q-71, Q-72 |
| **FR-MSN-14** | **Sửa đổi qua cùng một đường:** mọi sửa đổi — kể cả do agent vận hành đề xuất — đi nháp → biên dịch và kiểm mâu thuẫn → bản duyệt → người duyệt tại chỗ (UI cục bộ, CLI) hoặc qua bản ghi duyệt trong chat (FR-CH-04). Sửa đổi mở rộng quyền dữ liệu (đích mới, loại dữ liệu mới) chỉ duyệt tại chỗ | P0 | Đề xuất "thêm sục khí 2h–5h" từ agent ⇒ yêu cầu duyệt trong chat, chưa có hiệu lực tới khi duyệt; đề xuất thêm đích dữ liệu ⇒ không duyệt được qua chat | Q-72 |

### 5.5 Kênh chat và lời duyệt từ xa (FR-CH)

*Dự kiến — Q-72, increment I2d; chưa có mã.* Kênh nhắn tin là nơi người dùng sống với thiết bị mỗi ngày: nhận báo cáo, ra lệnh, và **duyệt**. Vì chat là kênh từ xa chứa văn bản do người ngoài gửi, lời duyệt qua chat là một **bản ghi duyệt có mã**, không phải một "Có" tự do. Nguồn `chat:<id>` theo cùng văn phạm nguồn do runtime gán của RFC-0017 và **cần RFC** (RFC dự kiến: nguồn `chat:<id>` + bản ghi duyệt). Hôm nay `HUMAN_SOURCES = ("local_grammar", "ui")` (`python/neuroedge/actions/confirmation.py`).

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-CH-01** | **Adapter kênh chat trong runtime:** Telegram trước (I2d), Slack và Zalo sau; adapter chạy trong runtime tin cậy, chỉ đi `dispatch()`, không import `hal`; nội dung tin chat đi vào LLM worker như **dữ liệu không tin cậy** | P0 · Slack, Zalo: P1 | Gửi và nhận tin qua Telegram trong kịch bản G1; test cấu trúc: gói kênh chat không import `hal`; tin chat chứa lệnh cài cắm không vượt được gate | Q-72 |
| **FR-CH-02** | **Lệnh từ chat là tool call có nguồn:** tin của người đã ghép đôi thành tool call với nguồn `chat:<id>` do runtime gán, đi `dispatch()` → gate như mọi nguồn; nguồn `chat:<id>` **không** thuộc `HUMAN_SOURCES` — một tin thường không bao giờ xác nhận `ask` | P0 *(cần RFC)* | Tool call từ chat mang `source` tự khai ⇒ `REJECTED`; tin "Có" không nhắm một yêu cầu duyệt ⇒ không xác nhận gì | Q-72 |
| **FR-CH-03** | **Ghép đôi tại chỗ:** chỉ tài khoản chat đã ghép đôi với máy nhà bằng mã ghép đôi hiện **tại chỗ** (UI cục bộ hoặc CLI) mới gửi được lệnh và lời duyệt; **nhóm chat không bao giờ duyệt**. Thu hồi, hạn ghép đôi và trần số lời duyệt mỗi giờ: hoãn ở `TODOS.md` #62, mốc trước task duyệt qua chat của I2d | P0 | Tin từ tài khoản chưa ghép đôi ⇒ bỏ qua, ghi vết; lời duyệt từ nhóm ⇒ từ chối (A20); mã ghép đôi chỉ hiện ở UI cục bộ hoặc CLI trên máy nhà | Q-72 |
| **FR-CH-04** | **Bản ghi duyệt:** runtime phát yêu cầu duyệt `{id, nonce, hạn, digest của thay đổi, bản duyệt ≤ 5 dòng}` tới chat đã ghép; bản duyệt do trình biên dịch sinh (FR-MSN-12); trả lời phải **nhắm đúng `id`** (nút bấm hoặc mã); runtime kiểm, theo thứ tự: người gửi đã ghép đôi, không phải nhóm, nonce chưa dùng, còn hạn (đồng hồ đơn điệu), digest khớp thay đổi đang chờ — đạt đủ mới đưa vào đường xác nhận với nguồn `chat:<id>`; mỗi lời duyệt (đạt hay bị từ chối) ghi vào `trace.v1` với người gửi, `id`, digest và bản duyệt. Áp cho cả `ask` lúc chạy lẫn sửa đổi hợp đồng. Lời duyệt không đi qua relay | P0 *(cần RFC)* | Bộ kịch bản: lời duyệt từ tài khoản chưa ghép đôi, từ nhóm, nonce đã dùng, hết hạn, digest lệch (thay đổi bị sửa sau khi gửi yêu cầu), nhắm sai `id` ⇒ đều bị từ chối và ghi vết; hai yêu cầu chờ cùng lúc không bao giờ bị duyệt nhầm (A20) | Q-26, Q-72 |
| **FR-CH-05** | **LLM không bao giờ duyệt:** LLM worker và agent không có đường gửi lời duyệt; câu trả lời do LLM soạn không được đưa vào chat như lời duyệt; chỉ bản ghi duyệt từ người đã ghép đôi mới vào đường xác nhận (FR-CH-04) | P0 | Worker gửi bản ghi duyệt giả qua MCP ⇒ từ chối, ghi vết; không tool nào runtime phơi cho worker trả lời được yêu cầu duyệt | Q-26, Q-72 |
| **FR-CH-06** | **Bước xác minh do người dùng khai** *(planned · Q-73, chờ RFC TSK-I2d-20)*: `on_block` khai được một bước xác minh (đọc mã, giọng nói, khuôn mặt, bàn phím, thẻ, vân tay trên điện thoại…) qua plugin bộ kiểm; đạt thì đặt dữ kiện người dùng khai; số lần thử và hạn; mỗi cách mang nhãn rủi ro hiện trong bản duyệt, `gate explain` và Blueprint | P1 | Bước xác minh do LLM, client MCP hay nguồn tự động trả lời ⇒ từ chối; vết ghi chỉ ghi đạt/trượt, không ghi mã; nhãn rủi ro hiện ở cả ba nơi | Q-73 |
| **FR-CH-07** | **Nhiều người, có vai trò** *(planned · Q-74, TSK-I2f-05)*: một ô chat có nhiều người đã ghép đôi; vai trò quyết ai được ra lệnh, ai được duyệt, với thiết bị nào, ở nhà nào, trong khung giờ nào | P2 | Người không có vai trò duyệt gửi lời duyệt ⇒ từ chối; vai trò hết hạn (khách thuê) ⇒ mất quyền đúng giờ | Q-74 |
| **FR-CH-08** | **Lời duyệt ký trên điện thoại** *(planned · Q-76, TSK-I2f-08)*: nút duyệt trong chat mở trang ký bằng passkey tạo lúc ghép đôi; hộp tại nhà giữ khoá công khai và tự kiểm; cổng kênh chung của cloud chuyển tin nhưng không giả được lời duyệt | P2 | Cloud tự gửi "Đồng ý" không có chữ ký ⇒ hộp từ chối, ghi vết; passkey bị thu hồi ⇒ lời duyệt sau đó bị từ chối | Q-76 |

### 5.6 Luồng dữ liệu chống rò rỉ (FR-EGR)

*Dự kiến — Q-72, increment I2d; chưa có mã.* Luật luồng dữ liệu nhằm **chống rò rỉ** — hack, prompt injection, đánh cắp — chứ không hạn chế luồng người dùng tự dựng: mọi đích người dùng khai (nhà cung cấp LLM, kênh chat, relay, webhook) nhận được dữ liệu người dùng cho phép, kể cả ảnh tới LLM. **Rủi ro còn lại, phải nêu trong tài liệu và threat model:** một LLM worker bị lừa vẫn gửi được dữ liệu đã được phép tới đích đã được phép. Lược đồ khai đích **cần RFC** (RFC dự kiến: luồng dữ liệu và đích).

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-EGR-01** | **Runtime là cửa ra; chỉ đích đã khai:** runtime chỉ gửi dữ liệu ra các đích khai trong hợp đồng hoặc cấu hình; gửi tới đích không khai bị chặn và ghi vết | P0 | Kịch bản: một tin hay một webhook tới địa chỉ không khai ⇒ bị chặn, vết ghi có sự kiện chặn kèm đích (A18) | Q-72 |
| **FR-EGR-02** | **Runtime quyết định worker thấy gì:** LLM worker chỉ nhận những trường mà điều khoản luồng dữ liệu cho phép đi tới nhà cung cấp LLM | P0 | Hợp đồng không cho ảnh tới LLM ⇒ không có ảnh nào trong dữ liệu runtime đưa cho worker | Q-72 |
| **FR-EGR-03** | **Mạng của worker bị chặn ở mức hệ điều hành:** worker chỉ ra mạng tới endpoint nhà cung cấp đã khai (user riêng và luật tường lửa, hoặc proxy của runtime); công cụ chẩn đoán cảnh báo khi luật mạng này vắng | P0 | Worker mở kết nối tới một host không khai ⇒ thất bại; thiếu luật mạng ⇒ chẩn đoán cảnh báo và bản duyệt ghi rõ | Q-72 |
| **FR-EGR-04** | **Luật nội dung tuỳ chọn:** người dùng bật được luật tất định ("ảnh không rời mạng nội bộ", chỉ gửi sự kiện theo từ vựng đóng `{vùng, loại, lúc, tin_cậy}`) — cưỡng chế ở cửa ra, bảo đảm tuyệt đối — và luật xác suất ("không gửi ảnh có mặt người") — chỉ fail-closed: không chắc thì không gửi. Câu tự do do LLM viết không rời mạng khi hợp đồng chỉ cho sự kiện theo lược đồ | P0 | Bật "ảnh không rời mạng nội bộ" ⇒ trong kịch bản 30 ngày không ảnh nào tới đích ngoài (A18); bản duyệt đánh dấu luật xác suất | Q-72 |
| **FR-EGR-05** | **Relay tuỳ chọn là ống TLS xuyên:** máy nhà mở kết nối ra relay; relay chọn đích theo SNI và **không giải mã** (mẫu SniTun của Nabu Casa); sao lưu vết ghi mã hoá phía máy nhà trước khi gửi; lời duyệt không qua relay; relay tắt hay hỏng thì mọi phần an toàn vẫn chạy. Đây là ngoại lệ có giới hạn cho "không có máy chủ nào do NeuroEdge vận hành" (Q-10) | P1 | Relay bị chiếm chỉ thấy siêu dữ liệu (tên miền, thời điểm), không đọc được vết ghi, không chèn được lệnh; tắt relay giữa kịch bản ⇒ phán quyết không đổi | Q-72 |

---

## 6. Yêu cầu chức năng — Kiểm thử Action CI

### 6.1 Bốn thành phần Action CI (FR-CI)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-CI-01** | **Record:** ghi toàn bộ chuỗi sự kiện của một phiên chạy thực tế ra tệp JSON | P0 | `neuroedge record --target esp32s3` sinh tệp hợp lệ theo schema | §3.7 |
| **FR-CI-02** | **Replay:** tái hiện chuỗi sự kiện đó trên bất kỳ môi trường nào | P0 | Cùng tệp vết ghi cho cùng chuỗi phán quyết trên mọi môi trường | §3.7 |
| **FR-CI-03** | **Assert:** thư viện khẳng định hành vi — hành động bị chặn, chặn bởi gate nào, leo thang tới đâu, chân nào không được kích | P0 | Bốn nhóm khẳng định chạy được trong pytest | §4.7 |
| **FR-CI-04** | **Golden Reference:** cố định chuỗi phán quyết chuẩn; lệch mẫu chuẩn làm CI báo đỏ | P0 | Đổi prompt gây lệch phán quyết → CI thất bại, chỉ rõ điểm lệch | §3.7 |
| **FR-CI-05** | Action CI chạy tự động trên `sim` và `linux` với mỗi pull request | P0 | Pipeline CI mẫu có sẵn trong dự án scaffold | §3.2 |
| **FR-CI-06** | Action CI chạy tự động hàng đêm trên bo mạch `esp32s3` thật | P0 | Có cấu hình runner nightly và báo cáo kết quả | §3.2 |
| **FR-CI-07** | Lệnh `neuroedge verify` kiểm tra tính nhất quán phán quyết gate và trạng thái GPIO giữa các môi trường bậc 1 | P0 | Sai lệch sinh `SafetyRegressionError` (NE4002) chỉ rõ sự kiện lệch đầu tiên | §8.2 |

### 6.2 Ba cấp độ đảm bảo (FR-CI-LVL)

Đây là ranh giới kỹ thuật quan trọng nhất của sản phẩm: **Action CI không giả định mô hình ngôn ngữ là hàm tất định.**

| Mã | Cấp độ | Tính xác định | Action CI khẳng định điều gì | Ưu tiên |
|:---|:---|:---:|:---|:---:|
| **FR-CI-L1** | Thẩm định gate (rule engine): biểu thức `allow_when`, so sánh giá trị, ngân sách độ trễ | 100% xác định | Replay chuẩn xác từng bit; phán quyết đối chiếu tuyệt đối với Golden Reference | P0 |
| **FR-CI-L2** | Quyết định System 1 có cấu trúc: phân loại intent, trích xuất thực thể, schema cố định | Gần như xác định | Kiểm tra khớp schema JSON và xác thực `confidence >= threshold` | P0 |
| **FR-CI-L3** | Suy luận mở System 2 (LLM): sinh văn bản tự do | Phi xác định | **KHÔNG assert trên chuỗi văn bản sinh ra.** Chỉ assert trên **phán quyết gate (ALLOW/BLOCK)** và **trạng thái chân GPIO** | P0 |

**Hệ quả nghiệm thu:** một bài kiểm thử Action CI hợp lệ **KHÔNG ĐƯỢC** chứa khẳng định so khớp chuỗi văn bản do System 2 sinh ra. Quy tắc này phải được kiểm tra tự động trong công cụ lint của dự án mẫu.

### 6.3 Lược đồ vết ghi (FR-TRC)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-TRC-01** | Vết ghi là JSON theo JSON Schema draft 2020-12, xuất bản công khai tại `https://schema.neuroedge.dev/trace/v1.json` | P0 | URL truy cập được, schema hợp lệ | §3.7 |
| **FR-TRC-02** | Vết ghi chứa khối `metadata` đủ: `session_id`, `timestamp_utc`, `target`, `board_id`, `agent_version` | P0 | Thiếu bất kỳ trường nào → `neuroedge trace validate` báo lỗi | §3.7 |
| **FR-TRC-03** | Vết ghi bao phủ 6 nhóm sự kiện: đầu vào, nhận thức, quyết định mô hình, thẩm định gate, lệnh actuator, đầu ra | P0 | Phiên mẫu sinh đủ 6 nhóm | Phụ lục C.1 |
| **FR-TRC-04** | Vết ghi **replay được trên mọi môi trường** | P0 | FR-CI-02 đạt | Phụ lục C.2 |
| **FR-TRC-05** | Định dạng **ổn định giữa các phiên bản**: vết ghi cũ replay được sau nâng cấp phụ | P0 | Bộ vết ghi hồi quy từ phiên bản trước vẫn chạy | Phụ lục C.2 |
| **FR-TRC-06** | Vết ghi **đọc được bởi người**, không cần công cụ chuyên dụng | P0 | Mở bằng trình soạn thảo văn bản và hiểu được trình tự | Phụ lục C.2 |
| **FR-TRC-07** | Chế độ **ẩn danh tại nguồn:** một cờ cấu hình thay nội dung thô bằng hash, giữ nguyên chuỗi quyết định | P0 | Bật cờ → không còn dữ liệu âm thanh hay văn bản thô, replay vẫn đúng | Phụ lục C.2 |
| **FR-TRC-08** | Lệnh `neuroedge trace validate <tệp>` xác thực tệp theo JSON Schema | P0 | Tệp sai cấu trúc bị bắt lỗi trước khi commit | §3.7 |
| **FR-TRC-09** | Tuân thủ quy ước đường dẫn: `traces/`, `traces/incidents/<session_id>.json`, `traces/golden/<kịch-bản>.json` | P1 | Dự án scaffold tạo sẵn ba thư mục | §3.7 |
| **FR-TRC-10** | Schema được đăng ký lên SchemaStore công cộng để IDE tự nhận diện | P1 | VS Code gợi ý tự động khi mở tệp vết ghi mà không cần cài công cụ NeuroEdge | §3.7 |
| **FR-TRC-11** | **Vết ghi theo đoạn cho runtime 24/7** *(Q-72, cần RFC `trace.v1`)*: vết ghi của agent vận hành là **chuỗi đoạn** theo thời gian (mỗi ngày, hoặc sớm hơn khi vượt cỡ); mỗi đoạn mang **trạng thái đầu đoạn** (gate digest, sổ token, bộ đếm phong bì, lease đang chạy) và digest của đoạn trước. Bất biến "một vết ghi mỗi phiên" thành "một phiên một chuỗi vết ghi, mỗi đoạn replay được" | P0 | `replay` một đoạn đơn lẻ cho cùng phán quyết như lúc chạy, kể cả bộ đếm phong bì và lease vắt qua ranh giới đoạn; thiếu hay sửa một đoạn ⇒ chuỗi digest báo đúng chỗ đứt; vết ghi một phiên thường giữ nguyên định dạng | Q-72 |
| **FR-TRC-12** | **Ghi và giữ vết ghi trên máy nhà** *(Q-72)*: ghi nối tiếp, flush theo thời gian (mặc định khoảng 10 giây, khai được) và **ngay** khi có phán quyết chặn hay lời duyệt; giữ **30 ngày** gần nhất tại chỗ, đoạn cũ hơn nén rồi xoá hoặc xuất qua relay mã hoá (FR-EGR-05); mất điện chỉ mất tối đa phần đuôi sự kiện thường, và `replay` báo đoạn cụt | P0 | Kịch bản mất điện giữa đoạn: mọi phán quyết chặn và lời duyệt trước lúc mất điện còn trong vết ghi; `replay` báo đoạn cụt thay vì báo đạt; cỡ 30 ngày đo trên G1 và ghi vào NFR-OBS-04 | Q-72 |
| **FR-TRC-13** | **Sự kiện mới của Q-72** *(cần RFC `trace.v1`)*: yêu cầu duyệt và lời duyệt (người gửi, `id`, digest, bản duyệt, kết quả kiểm), bộ phát hiện bắn, gửi ra đích (đích, loại dữ liệu, bị chặn hay không), chi phí LLM cộng dồn theo kỳ, chạm trần ngân sách, khởi động lại runtime hay worker, đồng hồ `unsynced` | P0 | Kịch bản bể cá 30 ngày sinh đủ các loại sự kiện trên và qua `neuroedge trace validate` | Q-72 |

### 6.4 Quản trị lược đồ mở (FR-GOV)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-GOV-01** | Lược đồ gate và vết ghi xuất bản công khai theo giấy phép Apache-2.0 (Q-45) | P0 | Kho lược đồ công khai, có tệp giấy phép | §3.8 |
| **FR-GOV-02** | Phiên bản lược đồ quản lý theo đường dẫn URL (`/v1`, `/v2`); thay đổi phá vỡ tương thích bắt buộc tăng phiên bản chính | P0 | Có văn bản chính sách phiên bản kèm kho lược đồ | §3.8 |
| **FR-GOV-03** | **Bộ kiểm thử tuân thủ:** công bố tập vết ghi mẫu kèm kết quả replay kỳ vọng để bên thứ ba tự kiểm chứng | P0 | Bên thứ ba chạy được bộ kiểm thử mà không cần chứng nhận độc quyền | §3.8 |
| **FR-GOV-04** | Mọi thay đổi lược đồ đi qua quy trình RFC công khai trên GitHub | P1 | Có mẫu RFC và ít nhất một RFC đã qua quy trình | §3.8 |

---

## 7. Yêu cầu chức năng — Trải nghiệm lập trình viên

### 7.1 Khởi tạo và vòng lặp phát triển (FR-DX)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-DX-01** | `neuroedge new <tên>` sinh dự án mẫu có sẵn: `agent.toml`, 1 action, 1 gate, 1 kịch bản test CI | P0 | Dự án mới chạy `neuroedge test` thành công ngay, không sửa gì | §4.8 |
| **FR-DX-02** | Cài đặt và chạy `sim` **không yêu cầu** tài khoản, API key hay thẻ thanh toán. Đầu vào mặc định của `sim` là **gõ chữ** → bộ khớp ngữ pháp lệnh; giọng nói là tuỳ chọn *(Q-15)* | P0 | Máy sạch, không mạng nội bộ đặc biệt, không key: hoàn thành hành trình 10 phút bằng lệnh gõ chữ. `pip install neuroedge` không kéo LiteLLM — phụ thuộc cloud nằm ở extra `neuroedge[cloud]` *(Q-10)* | §4.10 |
| **FR-DX-03** | Time-to-first-value trung vị dưới 10 phút, đo trên 10 lập trình viên độc lập | P0 | Biên bản đo có mốc thời gian từng bước của 10 người | §12.1 |
| **FR-DX-04** | Mọi thông báo lỗi nêu rõ: cái gì sai, ở đâu, và cách xử lý | P0 | Rà soát toàn bộ mã lỗi tại Phụ lục B đạt đủ 3 thành phần | §4.9 |
| **FR-DX-05** | Tài liệu có ít nhất 3 ứng dụng mẫu hoàn chỉnh chạy được | P0 | Ba mẫu chạy thành công trên máy sạch theo hướng dẫn *(tiến độ: TSK-S3-08)* | §12.1 |
| **FR-DX-06** | Tài liệu có ít nhất 1 video hoặc ảnh động minh họa trực quan trong README | P0 | Có tài sản trực quan dưới 30 giây thể hiện vòng lặp giá trị | §12.1 |
| **FR-DX-07** | Công cụ lint của dự án mẫu chặn khẳng định so khớp văn bản do System 2 sinh ra | P1 | Test vi phạm FR-CI-L3 bị lint báo lỗi | §3.7 |
| **FR-DX-08** | `neuroedge add` sinh `@action` + gate + test hai chiều + khai `[requires]` cho mọi nguyên thủy, từ template có sẵn | P0 | Trên dự án mẫu: `gate lint` sạch, test ALLOW và BLOCK xanh; chạy lại không ghi đè tệp đã có | Q-52 |
| **FR-DX-09** | Kit mẫu cho mỗi gói nguyên thủy: BOM, sơ đồ đấu dây, profile bo mạch, gate đã khoá, vết ghi golden, hướng dẫn "từ hộp tới chạy thật". *Mở rộng bởi Q-72:* **danh mục kit** có BOM kèm nơi mua (liên kết bán, chưa giữ kho), mở đầu bằng **kit bể cá** (I2e); kit là phần `kit` của một NeuroEdge Blueprint (FR-BP-01) và chạy thử được trên giả lập trước khi mua | P0 | A12. *Q-72:* kit bể cá có BOM với nơi mua cho từng linh kiện, chạy được trên G1 trước khi mua | Q-52, Q-72 |
| **FR-DX-10** | NeuroEdge Lab: bộ tool MCP trung lập với client để một client MCP (Claude Code, Claude Desktop…) dựng bản nháp `@action` + gate `0.1.0-draft` + test hai chiều cho mọi nguyên thủy — NeuroEdge chấm bản nháp (`neuroedge lab check`, cùng mã ở tool và Action CI) chứ không tự gọi LLM; bản nháp chỉ được khoá sau `gate lint` và người duyệt qua PR — không tool nào khoá được chính sách. *Mở rộng bởi Q-72:* Lab là **vòng ①** — từ action lên **hợp đồng nhiệm vụ**: client dựng bản nháp `mission.v1` (FR-MSN-13), NeuroEdge chấm bằng cùng trình biên dịch và phép kiểm mâu thuẫn, người khoá; và `neuroedge lab doctor` kiểm **từng cảm biến** khi lắp (ví dụ *"cảm biến oxy đọc 0 — kiểm lại dây"*), ngoài cảnh báo tách quyền hiện có. Phần vòng ① cho nhiệm vụ dời từ I4a vào I2d | P0 | A11. *Q-72:* một hợp đồng nhiệm vụ bể cá do client MCP dựng qua tool của Lab, qua phép kiểm và người khoá; `lab doctor` chỉ đúng cảm biến đọc sai trong kịch bản G2 | Q-55, Q-71, Q-72 |

### 7.2 Giao diện dòng lệnh (FR-CLI)

**Hợp đồng mã thoát** *(`CHANGELOG.md` §2.3 — CI và Action CI neo vào nó)*: `0` phép kiểm tra đã chạy và **đạt** · `1` đã chạy và **không đạt** · `2` lệnh **chưa được hiện thực** (hoặc sai cú pháp lệnh). Lệnh chưa hiện thực **KHÔNG ĐƯỢC** thoát mã 0.

| Mã | Nhóm lệnh | Lệnh bắt buộc | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---|:---:|:---|:---:|
| **FR-CLI-01** | Khởi tạo | `neuroedge new <tên>` | P0 | Dự án sinh ra chạy `neuroedge test` thoát mã 0 ngay, không sửa gì (FR-DX-01) | §4.8 |
| **FR-CLI-02** | Phát triển | `neuroedge run --target sim` · `neuroedge run --target linux` · `neuroedge build --target esp32s3 --board <id>` | P0 | `run --target sim` nhận lệnh gõ chữ không cần key *(Q-15)*, kiểm năng lực agent ↔ bo mạch trước khi chạy (không hợp → mã 1); `run -c "<lệnh>"` chạy một lệnh rồi thoát mã 0 kể cả khi gate chặn; `build` gặp bất tương thích năng lực → mã 1, không sinh firmware (FR-HAL-04) | §4.8 |
| **FR-CLI-03** | Kiểm thử | `neuroedge test` · `neuroedge verify --targets sim,linux,esp32s3` | P0 | `test` thoát 0 khi mọi khẳng định đạt, 1 khi có khẳng định sai; `verify` lệch giữa các target → mã 1, chỉ rõ sự kiện lệch đầu tiên (FR-CI-07); quét được 0 artifact (gate, vết ghi chuẩn mực hoặc lượt replay) → `VerificationError` (NE4004), mã 1, không thoát 0 (TSK-S3-19); `esp32s3` cần `--port`: firmware replay các vết ghi chuẩn mực, host so với golden (TSK-S4-09, `docs/spec/simulation_coverage.md` §4); thiếu `--port` ⇒ mã 1 | §4.8 |
| **FR-CLI-04** | Chẩn đoán | `neuroedge record --target <t> --out <thư-mục>` · `neuroedge trace validate <tệp>` · `neuroedge replay <tệp> --target <t>` · `neuroedge trace view <tệp>` · `neuroedge trace export --format chrome <tệp>` | P0 · `view`/`export`: P1 | `record` sinh tệp qua được `trace validate`; `trace validate` có một tệp sai → cả lệnh mã 1 kèm `TraceValidationError`; `replay` cho cùng chuỗi phán quyết (FR-CI-02); `record --target esp32s3 --port <cổng>` đọc vết ghi từ UART (cả trên QEMU); `trace view` sinh một tệp HTML tĩnh mở không cần mạng | §4.8 |
| **FR-CLI-05** | Hệ sinh thái gate | `neuroedge gate publish <tệp>` · `neuroedge gate add <uri>` · `neuroedge gate explain <tệp\|uri>` | P1 | `publish` in mã băm SHA-256 của JSON chuẩn tắc RFC 8785, hai lần chạy cho cùng mã băm; `add` phân giải gate từ registry và nêu ràng buộc kế thừa sẽ áp đặt; `explain` nêu mỗi tiêu chí do cấp nào đưa vào, mệnh đề nào con siết chặt so với cha, ngân sách và `on_block` — gate phân giải lỗi → mã 1 kèm lỗi 3 thành phần | §4.8 |
| **FR-CLI-09** | Cổng an toàn gate | `neuroedge gate lint [thư-mục] [--registry <dir>]` | P0 | **Đây là cổng kiểm tra an toàn**, không phải thẩm định lược đồ: phân giải toàn bộ chuỗi `extends` của mọi gate và cưỡng chế các nguyên tắc Phụ lục B.5 (kể cả phần mở rộng Q-18). Vi phạm → mã 1 kèm `GateInheritanceError` hoặc `GateSchemaError`; corpus phản chứng `fixtures/gates/invalid/` BẮT BUỘC thoát **đúng** mã 1 trong CI. Thẩm định lược đồ đơn lẻ không đủ để kết luận gate an toàn | Phụ lục B.5 |
| **FR-CLI-10** | Phân giải gate | `neuroedge gate resolve <tệp\|URI> [--json] [--registry <dir>]` | P0 | In chính sách hiệu dụng và mã băm; chuỗi vi phạm → mã 1 với cùng lỗi như `gate lint`; cùng đầu vào cho cùng mã băm | Phụ lục B.5 |
| **FR-CLI-11** | Bo mạch | `neuroedge board list` · `neuroedge board show <id>` · `neuroedge board validate <path>` *(RFC-0002 PR2, Giai đoạn 2)* | P0 · `validate`: Giai đoạn 2 | `board show` in năng lực theo 5 nguyên thủy (FR-HAL-01); `board validate` tệp sai lược đồ → mã 1 kèm `BoardCapabilityError`; trước RFC-0002 PR2, `board validate` thoát mã 2 | §4.2, RFC-0002 |
| **FR-CLI-12** | Tích hợp tool | `neuroedge mcp tools [--json\|--openai] [--external]` · `neuroedge mcp serve [--agent a.toml] [--ui] [--http …]` · `neuroedge mcp desktop-config [--agent a.toml] [--ui] [--lab] [--write]` | P1 | `tools` in schema mỗi `@action`; `serve` là máy chủ MCP qua stdio (`--ui`: cùng phiên với giao diện web `sim`; `--http`: qua mạng bằng Streamable HTTP, mTLS và token OAuth 2.1 theo thiết bị, mặc định tắt, thiếu một mảnh cấu hình ⇒ mã 1 trước khi mở cổng — NFR-SEC-09, TSK-P2-04; `--ui --http`: trang tại nhà cùng phiên là nơi duy nhất trả lời `ask`), mỗi `tools/call` đi qua `dispatch()` và gate (Q-24); `desktop-config` in (hoặc ghi, có sao lưu, chỉ đúng một mục `mcpServers`) cấu hình Claude Desktop bằng đường dẫn tuyệt đối; `--lab` *(I4a, TSK-N1-05)* cấu hình cho agent lab trong một bước, vẫn đúng một mục `mcpServers` và mọi lab tool vẫn qua gate; thiếu extra `mcp` ⇒ mã 1 kèm cách cài | §4.8 |
| **FR-CLI-13** | NeuroEdge Blueprint *(Q-72, I2e; dự kiến)* | `neuroedge blueprint pack [thư-mục]` · `neuroedge blueprint install <url\|tệp> [--digest <sha256>]` | P0 | `pack` in digest phủ toàn gói, hai lần chạy cho cùng digest, từ chối gói thiếu bằng chứng hay có gate chưa khoá (mã 1); `install` lệch digest ⇒ mã 1, không ghi tệp nào; hiện bản duyệt trước khi bật (FR-BP-02, FR-BP-03) | Q-72 |
| **FR-CLI-14** | Kênh chat *(Q-72, I2d; dự kiến)* | `neuroedge chat connect <kênh>` · `neuroedge chat pair` | P0 | `connect telegram` lưu token bot vào cấu hình của runtime, không in token; `pair` chỉ chạy trên máy nhà và hiện mã ghép đôi tại chỗ (FR-CH-03); kênh chưa hỗ trợ ⇒ mã 2 | Q-72 |
| **FR-CLI-15** | Nhiệm vụ và agent vận hành *(Q-72, I2d; dự kiến)* | `neuroedge mission check <tệp>` · `neuroedge mission explain <tệp>` · `neuroedge agent run` | P0 | `mission check` thoát 0 khi hợp đồng biên dịch được, 1 kèm lỗi ba phần khi sai lược đồ hay mâu thuẫn (FR-MSN-11); `mission explain` in bản duyệt ≤ 5 dòng tất định (FR-MSN-12); `agent run` khởi động runtime tin cậy (FR-AGT-01), từ chối chạy khi hợp đồng chưa khoá. Tên lệnh chốt ở RFC `mission.v1` | Q-72 |

**Yêu cầu chung cho toàn bộ CLI:**

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu |
|:---|:---|:---:|:---|
| **FR-CLI-06** | Mọi lệnh trả mã thoát theo hợp đồng `0`/`1`/`2` ở trên, phục vụ tích hợp CI | P0 | Test CLI neo chặt mã thoát của từng lệnh; bước CI kiểm corpus phản chứng so khớp chính xác mã 1 |
| **FR-CLI-07** | Mọi lệnh có `--help` mô tả đủ tham số và ví dụ sử dụng | P0 | `--help` của mỗi lệnh thoát mã 0 và có ít nhất một ví dụ; test tự động duyệt toàn bộ lệnh |
| **FR-CLI-08** | Lệnh chạy lâu hiển thị tiến trình; lệnh phá hủy dữ liệu yêu cầu xác nhận | P1 | `build`, `verify`, `record` hiển thị tiến trình; lệnh xoá hoặc ghi đè dữ liệu không chạy khi chưa xác nhận và thoát khác 0 |

### 7.3 Mở rộng của bên thứ ba (FR-EXT)

Thiết kế: `docs/architecture/vi/16-ecosystem-landscape.md` §4; hợp đồng ở RFC-0016, RFC-0017,
RFC-0018 (`docs/rfc/`). Quyết định: Q-67.

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-EXT-01** | **Lõi an toàn dùng độc lập:** API `neuroedge.guard` cho chương trình bất kỳ (proxy, bridge, node robot) — gate → token → phong bì → vết ghi, không bắt buộc `agent.toml`, `@action` hay `SimSession` | P0 | Một chương trình ngắn gate được một hành động và ghi vết ghi hợp lệ mà không có `agent.toml` | Q-67 |
| **FR-EXT-02** | **Sáu loại điểm cắm qua entry points:** bridge, fact source, actuator, board, template, exporter. Plugin chỉ nạp khi được bật rõ; nạp hỏng hoặc lệch phiên bản SDK ⇒ không khởi động; nguồn gốc in ra và ghi vào vết ghi | P0 | Với mỗi loại, một package ngoài kho cài bằng `pip` chạy được, lõi không đổi dòng nào | Q-67 |
| **FR-EXT-03** | **Bất biến cấu trúc của plugin:** bridge chỉ gửi được yêu cầu tool không mang `source` qua bộ điều phối do lõi cấp (lõi gán `bridge:<id>`), không có handle HAL; fact source không tự khai tuổi dữ kiện; actuator chỉ được HAL lái sau token và phong bì | P0 | Bộ test tuân thủ chứng minh từng điều; A3 vẫn là 0 lối tắt | Q-67 |
| **FR-EXT-04** | **Bộ test tuân thủ theo loại plugin:** `neuroedge conformance <package>`, kết quả máy đọc được | P0 | Plugin mẫu đạt; mỗi phép kiểm có một ca phản chứng bị bắt | Q-67 |
| **FR-EXT-05** | **Tài sản ngoài gói:** `--board <đường dẫn>` cho bo cộng đồng (tự chứng nhận, không bao giờ là bo tham chiếu); template từ đường dẫn, package hay git ghim commit; nhiều gốc registry gate; `extends` ghim được bằng digest | P0 | Mỗi nguồn có test; `verify` không bao giờ tính bo ngoài kho vào tương đương bậc 1 | Q-67, RFC-0002 |
| **FR-EXT-06** | **Hai proxy phổ quát:** `neuroedge proxy mcp` che một MCP server sẵn có (`guard init --mcp` sinh gate chặn mặc định cho từng tool) và `neuroedge proxy http` | P0 | Che một MCP server sẵn có trong ≤ 3 lệnh; công cụ chẩn đoán cảnh báo khi đích còn tới được mà không qua proxy | Q-67 |
| **FR-EXT-07** | **Cơ cấu chấp hành từ xa** có mức tự tắt khai rõ; hành động không hoàn tác cần mức mà thiết bị tự tắt được dù mất liên lạc | P0 | Theo RFC-0018 §7; adapter Home Assistant đạt đúng mức nó khai | Q-67 |
| **FR-EXT-08** | **Khám phá và phân phối:** index cộng đồng (kho riêng, Apache-2.0), `neuroedge plugin search/install`, huy hiệu "NeuroEdge-gated" chỉ cấp khi đạt FR-EXT-04. Không thu phí, không xếp hạng trả tiền. Index này **chỉ cho plugin** và luôn miễn phí; NeuroEdge Blueprint có index riêng cùng kiểu kho tĩnh (FR-BP-05), là nơi duy nhất có thể thu phí, và chỉ sau cổng 8 tuần (§14, Q-72) | P1 | Một plugin bên thứ ba cài từ index, hiện kết quả tuân thủ | Q-67, Q-72 |
| **FR-EXT-09** | **`neuroedge.sdk` ổn định:** có phiên bản riêng; cam kết chặt hơn mức `0.x` của gói (`docs/spec/python_api.md`) | P0 | Test ghim bề mặt SDK như `test_public_api.py` ghim `__all__` | Q-67 |

### 7.4 NeuroEdge Blueprint (FR-BP)

*Dự kiến — Q-72, increment I2e (sau I2d); chưa có mã.* **NeuroEdge Blueprint** là đơn vị chia sẻ và bán của vòng ③: một gói khai báo gồm **kit** (profile `board.v1` + BOM có nơi mua), **firmware** (cấu hình sinh firmware có `ne_gate`), **hợp đồng nhiệm vụ mẫu** kèm tham số hỏi lại, gate đã khoá, **bộ phát hiện**, và **vết ghi làm bằng chứng**. Nó khác **Home Assistant Blueprint** (mẫu automation chia sẻ trên Blueprint Exchange, nhập bằng URL); một NeuroEdge Blueprint có thể mang kèm một HA blueprint để người dùng HA cài một lần. Lược đồ `blueprint.v1` chạm `schemas/` nên **cần RFC** (RFC dự kiến); quan hệ với `manifest.v1` của Gate Registry (FR-REG-02) chốt ở RFC đó.

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-BP-01** | **Định dạng gói:** manifest `blueprint.v1` (cần RFC) liệt kê các phần trên, tác giả, phiên bản SemVer, giấy phép; gói **chỉ khai báo** — không có mã chạy tuỳ ý trên máy nhà lúc cài; firmware sinh lại từ cấu hình bo, bản dựng sẵn nếu có thì mang digest riêng; có thể mang kèm HA blueprint | P0 | Gói sai lược đồ ⇒ từ chối kèm lỗi ba phần; gói chứa tệp ngoài danh sách khai ⇒ từ chối | Q-72 |
| **FR-BP-02** | **`neuroedge blueprint pack`:** gom các phần thành một gói, tính **digest phủ toàn gói** (kit, firmware, hợp đồng mẫu, gate, bộ phát hiện, vết ghi bằng chứng; SHA-256 trên dạng chuẩn tắc như `gate publish`); từ chối khi có gate chưa khoá, thiếu vết ghi bằng chứng, hay `replay` bằng chứng không đạt | P0 | Hai lần `pack` cùng nội dung cho cùng digest; đổi một byte ở bất kỳ phần nào ⇒ digest đổi; gói có gate `-draft` ⇒ mã 1 (FR-CLI-13) | Q-72 |
| **FR-BP-03** | **`neuroedge blueprint install`:** tải bằng URL (git hoặc HTTPS) hoặc tệp, **kiểm digest toàn gói** trước khi ghi gì; chạy `replay` bằng chứng trên máy người cài; hỏi tham số; hiện bản duyệt (quyền, đích dữ liệu, cơ cấu có `safe_state` khác `off`, nhãn "bằng chứng chưa ký") rồi mới bật; không tự khoá hợp đồng — người cài duyệt | P0 | Digest lệch ⇒ từ chối, lỗi ba phần, không ghi tệp nào; người ngoài đội cài Blueprint bể cá trên máy sạch và chạy trên `sim` trong < 10 phút, không tài khoản (A14) | Q-72 |
| **FR-BP-04** | **Bằng chứng:** vết ghi `trace.v1` chạy thật hoặc trên giả lập, ghi rõ tầng (G1–G4 hay phần cứng thật) và thời lượng; **không Blueprint nào được bán khi chưa có bằng chứng** `replay` đạt. Ở MVP bằng chứng **chưa ký** — người bán sửa được vết ghi — nên mọi nơi hiện nó ghi rõ "chưa ký"; ký vết ghi quay lại trước khi Hub thu tiền cho người bán (`TODOS.md` #1) | P0 | `install` và index hiện "chưa ký" và tầng của bằng chứng; bằng chứng `replay` lệch ⇒ `install` từ chối | Q-72 |
| **FR-BP-05** | **Hub tối thiểu là index tĩnh:** một kho index tĩnh (cùng kiểu index plugin của FR-EXT-08, TSK-I2c-18) liệt kê URL, digest, tác giả, giấy phép, tầng của bằng chứng và nhãn "chưa ký"; người bán tự host gói (ví dụ trên GitHub); không máy chủ NeuroEdge, không tài khoản, không thu phí, không xếp hạng trả tiền tới sau cổng 8 tuần; chuyển sang OCI Registry (H2, FR-REG) khi Hub thu tiền | P0 | `blueprint install` từ một mục của index kiểm đúng digest ghi trong index; index không có thành phần chạy trên máy chủ | Q-72 |
| **FR-BP-06** | **An toàn của gói:** hợp đồng mẫu và gate trong gói không khai được `safe_state`; profile `board.v1` mang theo có `safe_state` khác `off` thì phải khai khoá liên động phần cứng (FR-ACE-03), và `blueprint install` hiện **riêng** từng cơ cấu đó, người cài xác nhận tại chỗ; mọi quyền và đích dữ liệu của gói hiện trong bản duyệt | P0 *(chờ RFC an toàn có điều kiện)* | Gói khai `safe_state` trong hợp đồng ⇒ từ chối; profile `safe_state: on` thiếu khoá liên động ⇒ từ chối nạp (A21); bản duyệt khi cài nêu riêng cơ cấu `safe_state: on` | Q-72 |
| **FR-BP-07** | **Kit có BOM liên kết:** BOM của Blueprint nêu mã hàng và nơi mua (liên kết bán, NeuroEdge chưa giữ kho); kit bể cá là kit đầu tiên (FR-DX-09) | P0 | Mỗi linh kiện của kit bể cá có ít nhất một nơi mua; BOM khớp năng lực khai trong profile bo | Q-72 |
| **FR-BP-08** | **Giấy phép trong manifest:** mỗi Blueprint ghi giấy phép của nó; dùng cá nhân miễn phí; bán Blueprint hay thiết bị dựng từ NeuroEdge là dùng thương mại (Q-45, PolyForm Noncommercial) và đi qua giấy phép thương mại của NeuroEdge (điều khoản: `TODOS.md` #44) | P1 | `install` hiện giấy phép; index hiện giấy phép của từng mục | Q-45, Q-72 |
| **FR-BP-09** | **Dữ liệu chia sẻ có đồng ý:** người dùng bật được việc chia sẻ dữ liệu vận hành (đã ẩn danh) để cải thiện bộ phát hiện của một Blueprint; **mặc định tắt**, đi qua cửa ra như mọi đích khác (FR-EGR-01) | P2 | Chưa bật ⇒ không dữ liệu nào rời máy cho mục đích này; bật ⇒ đích hiện trong bản duyệt (NFR-PRIV-05) | Q-72 |
| **FR-BP-10** | **Hub thu phí** *(sau cổng 8 tuần)*: chia doanh thu Blueprint, thanh toán, trang người bán; điều kiện mở: cổng 8 tuần đạt (B6–B8), ký vết ghi (`TODOS.md` #1), chuyển phân phối sang OCI Registry dùng đường ray FR-REG (định danh, đo lường, phân quyền) | P2 | Đặc tả khi cổng đạt, theo quyết định `Q-N` mới | Q-72 |

---

## 8. Yêu cầu chức năng — Tầng dịch vụ thương mại

**§8.1 (FR-GW) thuộc lõi**, giao theo hai mốc (Q-28: FR-GW-01 và 03 tối thiểu trong v1.0, phần còn lại ở v1.1) — lớp trừu tượng provider do người dùng tự vận hành, không thu phí dịch vụ (dùng thương mại cần license lõi — Q-45). **§8.2 (FR-FLT) và §8.3 (FR-REG) thuộc mốc v1.1**, chỉ khởi động khi đạt điều kiện §3.3. **Dòng thu theo Q-72:** PolyForm Noncommercial là cơ chế thu — cá nhân dùng miễn phí, bán Blueprint hay thiết bị là dùng thương mại (§8.4). NeuroEdge không bán lại token (N4): người dùng tự trả LLM bằng key của mình.

### 8.1 Lớp trừu tượng nhà cung cấp (FR-GW)

Nhóm FR-GW thuộc **lõi**; mốc giao của từng yêu cầu theo Q-28 và §3.2. Người dùng tự chạy lớp này, tự cấu hình provider và tự giữ khóa; NeuroEdge không vận hành cổng trung gian và không bán lại token.

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-GW-01** | Lớp trừu tượng self-host cung cấp một điểm kết nối và một thông tin xác thực duy nhất cho mọi nhà cung cấp mô hình | P0 | Một cấu hình duy nhất phục vụ nhiều provider; thiết bị không nhúng cứng khóa của từng nhà cung cấp | §6.1 |
| **FR-GW-02** | Khóa bảo mật do người dùng tự quản lý trong lớp self-host, xoay vòng được mà không cần nạp lại firmware | P0 | Xoay khóa trên 10 thiết bị đang chạy, không gián đoạn dịch vụ | §6.1 |
| **FR-GW-03** | Định tuyến đa nhà cung cấp kèm chuyển đổi dự phòng tự động — tính năng thuộc lõi | P0 | Ngắt nhà cung cấp chính → thiết bị không thấy gián đoạn | §6.1 |
| **FR-GW-04** | Giao thức tối ưu cho thiết bị biên: WebSocket liên tục, khung âm thanh nhị phân, phản hồi theo luồng — tính năng thuộc lõi, không phải dịch vụ trả phí | P0 | Vi điều khiển không phải bắt tay TLS cho từng yêu cầu | §6.1 |
| **FR-GW-05** | Hạn mức sử dụng cứng theo từng thiết bị — tùy chọn trong lớp self-host | P1 | Thiết bị lỗi lặp vòng bị chặn khi chạm hạn mức, có cảnh báo | §6.1 |
| **FR-GW-06** | Bộ nhớ đệm ngữ nghĩa và thống kê tỷ lệ System 1 / System 2 — tùy chọn của lõi | P1 | Báo cáo tỷ lệ và mức tiết kiệm chi phí theo nhóm tác vụ | §6.1 |
| **FR-GW-07** | Lớp trừu tượng xuất tệp vết ghi JSON **cùng định dạng** với Action CI cho mỗi phiên | P0 | Vết ghi từ lớp provider replay được trên máy cá nhân, không cần chuyển đổi | §6.1 |

### 8.2 Hệ điều hành quản trị đội thiết bị (FR-FLT)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-FLT-01** | Cấp phát danh tính và chứng chỉ mật mã riêng cho từng thiết bị ở lần khởi động đầu | P0 | Quy trình claim tự động thành công trên lô 100 thiết bị | §6.2 |
| **FR-FLT-02** | Điều phối cập nhật OTA theo đợt canary 1% → 10% → 100%, tự dừng và khôi phục khi tỷ lệ lỗi vượt ngưỡng | P0 | Chiến dịch 1.000 thiết bị, 0 thiết bị brick | §6.2, §12.2 |
| **FR-FLT-03** | Sổ kiểm kê và giám sát sức khỏe: online/offline, phiên bản firmware, RSSI, nhiệt độ chip, cảnh báo lặp khởi động | P0 | Dashboard phản ánh đúng trạng thái trong vòng 60 giây | §6.2 |
| **FR-FLT-04** | Cập nhật cấu hình, bí mật và **gate** từ xa mà không nạp lại firmware | P0 | Đổi ngưỡng gate trên toàn đội, có hiệu lực không cần khởi động lại | §6.2 |
| **FR-FLT-05** | Tự động tải tệp vết ghi JSON về kho tập trung khi thiết bị phát sinh cảnh báo | P0 | Sự cố hiện trường xuất hiện trong kho trong vòng 5 phút | §6.2 |
| **FR-FLT-06** | Thiết bị ảo trong `sim` xuất hiện ngay trên Fleet Dashboard | P0 | Dashboard hữu ích ở quy mô n = 1, không yêu cầu phần cứng thật | §6.2 |

### 8.3 Đường ray hạ tầng nền tảng (FR-REG)

Bảy đường ray (FR-REG-01→07, khớp `docs/architecture/vi/15-target-architecture.md` §3.2) rẻ ở giai đoạn đầu nhưng **không thể bổ sung sau**. FR-REG-08 là phần mở rộng của đường ray 1 (kho Registry), không phải đường ray thứ tám. Theo Q-72, các đường ray này cũng là **nền của Hub thu phí** cho NeuroEdge Blueprint sau cổng 8 tuần (FR-BP-10): manifest và định danh cho gói, đo lường cho chia doanh thu, phân quyền cho gói của người lạ.

| Mã | Thành phần | Giá trị ngày đầu | Vai trò dài hạn | Ưu tiên |
|:---|:---|:---|:---|:---:|
| **FR-REG-01** | Kho Gate công khai miễn phí | `neuroedge gate add <uri>` | Dữ liệu về chính sách được tái sử dụng nhiều nhất | P0 |
| **FR-REG-02** | Manifest và chuẩn phiên bản SemVer | Quản lý phụ thuộc minh bạch | Đơn vị phân phối của Marketplace | P0 |
| **FR-REG-03** | Khai báo năng lực phần cứng | Chặn lỗi bất tương thích khi build | Kiểm tra tương thích trước khi cài | P0 |
| **FR-REG-04** | Gate có phiên bản, hỗ trợ `extends` | Tái sử dụng chính sách an toàn | Tài sản trao đổi giá trị cao nhất | P0 |
| **FR-REG-05** | Định danh ổn định cho thiết bị, agent, gate | Gỡ lỗi và tra cứu chính xác | Quy kết trách nhiệm và doanh thu | P0 |
| **FR-REG-06** | Hệ thống đo lường theo lượt gọi agent và lượt thẩm định gate | Thống kê sử dụng | Cơ sở phân chia doanh thu | P0 |
| **FR-REG-07** | Cơ chế phân quyền và sandbox | An toàn khi thử agent lạ | Điều kiện chạy mã bên thứ ba trên thiết bị có actuator | P0 |
| **FR-REG-08** | Kho chia sẻ adapter kết nối provider | Người dùng tải về adapter sẵn có thay vì tự viết lại | Đòn bẩy hiệu ứng mạng dễ hình thành hơn gate vì nhu cầu kết nối provider là tức thời | P1 |

**Cảnh báo kiến trúc:** FR-REG-05, FR-REG-06 và FR-REG-07 phải được thiết kế ngay ở v1.1. Thiếu chúng, hệ thống sau này không thể đối soát doanh thu và không thể cho phép mã nguồn bên thứ ba chạy trên thiết bị có cơ cấu chấp hành.

### 8.4 Dòng thu theo Q-72: kit, Blueprint Hub, giấy phép theo thiết bị, relay

Mọi dòng thu dưới đây là **tuỳ chọn** với người dùng và **không bao giờ nằm trên đường an toàn**: tắt hay hỏng thì phản xạ, gate, hợp đồng và lời duyệt vẫn chạy. Chỉ số theo dõi: C6 (§11.3). Thứ tự theo tầng thời gian của proposal Q-72; dòng nào vào trước do cổng 8 tuần quyết định.

| Dòng thu | Ai trả | Khi nào | Điều kiện, yêu cầu dẫn |
|:---|:---|:---|:---|
| **Hoa hồng kit** (liên kết bán, chưa giữ kho) | Nhà cung cấp linh kiện (U9) | **Nguồn thu thử đầu** — kit bể cá ở I2e | FR-BP-07, FR-DX-09; đo bằng báo cáo liên kết của nhà bán |
| **Chia doanh thu NeuroEdge Blueprint** | Maker bán Blueprint (U5) | Sau cổng 8 tuần | Hub thu phí FR-BP-10: cổng đạt, ký vết ghi (`TODOS.md` #1), OCI Registry và đường ray FR-REG |
| **Giấy phép thương mại theo thiết bị** | Micro-OEM, startup phần cứng bán thiết bị (U5); doanh nghiệp dùng lõi (U2) | Khi có người bán đầu tiên | Q-45 (PolyForm Noncommercial); điều khoản, giá, dùng thử: `TODOS.md` #44. Tính năng an toàn cốt lõi luôn nằm trong giấy phép, không tách gói trả thêm (P-3) |
| **Relay đám mây tuỳ chọn** — truy cập từ xa, đẩy tin, sao lưu vết ghi mã hoá | Người dùng cuối (U8), maker | Sau Blueprint tối thiểu; thứ tự theo cổng 8 tuần | FR-EGR-05, NFR-SEC-15; ngoại lệ có giới hạn cho Q-10 |
| **NeuroEdge Cloud thuê bao** — agent trông nhà chỉ cần chat, điều phối nhiều thiết bị, nhiều nhà *(Q-74 bước 2, có điều kiện)* | Người dùng cuối (U8), chủ homestay, gia đình nhiều nhà | Chỉ khi số đo cổng 8 tuần cho thấy người thử vướng ở cài đặt, khoá API hay tự host | FR-AGT-10, FR-AGT-11; sửa N4 khi mở |
| **Fleet OS** | Đội vận hành thiết bị (U3) | v1.1 — sau cổng 8 tuần và điều kiện §3.3 | §8.2 (FR-FLT) |
| **Năng lực vật lý cho agent AI khác gọi qua MCP**; chỉ số tổng hợp theo ngành từ dữ liệu có đồng ý | Agent AI khác; bên mua chỉ số | Xa — chưa đặc tả | Chưa có yêu cầu; cần `Q-N` riêng |

**Không đổi tới khi mở Q-74 bước 2:** NeuroEdge không bán lại token (N4) và không giữ key LLM của người dùng trên máy chủ của mình (NFR-SEC-13). Gói cloud thuê bao, nếu mở, dùng key của NeuroEdge; key BYOK của người dùng vẫn không rời hộp tại nhà.

---

## 9. Yêu cầu phi chức năng

### 9.1 Hiệu năng và độ trễ (NFR-PERF)

| Mã | Chỉ tiêu | Ngưỡng cam kết | Điều kiện đo | Ưu tiên |
|:---|:---|:---|:---|:---:|
| **NFR-PERF-01** | Độ trễ phản hồi thoại trọn vòng — provider hỗ trợ streaming | **P95 < 850 ms** | Kết nối Wi-Fi, provider STT/LLM/TTS hỗ trợ streaming, từ lúc dứt lời tới khi loa phát tiếng | P0 — *tạm dừng (Q-72)* |
| **NFR-PERF-02** | Độ trễ thẩm định gate — xử lý cục bộ | **P95 < 120 ms** | Trên các môi trường bậc 1 | P0 |
| **NFR-PERF-03** | Độ trễ thẩm định gate — khi cần dữ liệu từ provider cloud | **P95 < 450 ms** | Mạng ổn định | P0 |
| **NFR-PERF-04** | Quyết định `SystemOne` có cấu trúc | **< 100 ms** | Mô hình cục bộ hoặc mô hình nhanh qua lớp trừu tượng provider | P0 |
| **NFR-PERF-05** | Hiệu quả định tuyến hai mô hình | Tiết kiệm **≥ 60%** chi phí token so với chuyển toàn bộ lên System 2 | Đo trên lưu lượng thực, tách theo nhóm tác vụ. *Q-72:* NeuroEdge không bán token, nên chỉ tiêu này đo lợi ích cho người dùng tự trả LLM (BYOK); với agent vận hành, ràng buộc chi phí là **trần tuyệt đối** NFR-COST-01, không phải tỷ lệ tiết kiệm | P0 |
| **NFR-PERF-06** | Thời gian chạy bộ Action CI của dự án mẫu | **< 30 giây** trên `sim` | Máy phát triển thông thường | P1 |
| **NFR-PERF-07** | Độ trễ phản hồi thoại trọn vòng — provider request-response | **P95 < 1.500 ms** | Kết nối Wi-Fi, provider không hỗ trợ streaming, từ lúc dứt lời tới khi loa phát tiếng | P1 — *tạm dừng (Q-72)* |

### 9.2 Tài nguyên và ràng buộc phần cứng (NFR-RES)

| Mã | Chỉ tiêu | Yêu cầu | Ưu tiên |
|:---|:---|:---|:---:|
| **NFR-RES-01** | Runtime trên `esp32s3` chạy ổn định trên bo mạch tham chiếu với pipeline thu/phát âm thanh, máy trạng thái hội thoại và thẩm định gate *(STT/TTS đặt ở provider cloud)* | Không tràn bộ nhớ trong 24 giờ chạy liên tục | P0 |
| **NFR-RES-02** | Ngân sách SRAM/PSRAM tối thiểu còn tự do cho runtime | SRAM ≥ 120 KB · PSRAM ≥ 2 MB *(đã chốt tại §15 của tài liệu này, Q-3; dễ đạt hơn từ v1.0 nhờ cloud-first theo CR-1.0 — Change Request 1.0, 2026-09-21: chuyển sang cloud-first, provider-pluggable; bản ghi đầy đủ ở `CHANGELOG.md`)* | P0 |
| **NFR-RES-03** | Kích thước firmware tối đa cho bo mạch tham chiếu | ≤ 3,5 MB *(đã chốt tại §15 của tài liệu này, Q-3 — vừa phân vùng kép A/B trên 16 MB Flash)* | P1 |
| **NFR-RES-04** | Hệ thống hoạt động đầy đủ khi mất kết nối Internet trên lõi | 100% tính năng an toàn hoạt động offline | P0 |

### 9.3 Độ tin cậy (NFR-REL)

| Mã | Chỉ tiêu | Ngưỡng cam kết | Ưu tiên |
|:---|:---|:---|:---:|
| **NFR-REL-01** | Độ tin cậy cập nhật OTA quy mô lớn | **1.000 thiết bị / 0 sự cố brick** | P0 |
| **NFR-REL-02** | Hành vi mặc định khi mọi thành phần suy giảm | **Lệnh:** `fail: closed` — chặn hành động vật lý. **Cơ cấu:** trở về `safe_state` khai trong `board.v1` — mặc định `off`, nên hành vi hiện có không đổi *(chờ RFC an toàn có điều kiện — Q-72, FR-ACE-03)* | P0 |
| **NFR-REL-03** | Kiểm thử nightly trên bo mạch thật | Chạy hằng đêm, có báo cáo kết quả và xu hướng | P0 |
| **NFR-REL-04** | Vết ghi cũ replay được sau nâng cấp phiên bản phụ | 100% bộ vết ghi hồi quy vẫn chạy | P0 |
| **NFR-REL-05** | Phản xạ khi mất mạng hoặc mất LLM *(Q-72)* | **100%** điều khoản tầng phản xạ và tầng kỹ năng vẫn được cưỡng chế khi mất mạng, mất LLM worker hay hết ngân sách LLM; chỉ phần phân tích dừng | P0 |
| **NFR-REL-06** | Sống của runtime 24/7 *(Q-72)* | Runtime tự khởi động lại sau lỗi hay mất điện; worker chết không làm runtime dừng; chạy liên tục **2 tuần** trên G2 hoặc G3 không can thiệp (B7) | P0 |

### 9.4 Bảo mật (NFR-SEC)

Các lớp phòng thủ theo `docs/spec/threat_model.md` — hành động vật lý, bên gọi không tin cậy (NFR-SEC-09), thiết bị, mạng, quyền riêng tư *(đặc tả riêng ở §9.5 của tài liệu này)*, cập nhật — hoạt động theo chế độ mặc định. Bảng dưới thêm hai nhóm yêu cầu ngoài các lớp đó: mã bên thứ ba (đường ray 7, `docs/architecture/vi/15-target-architecture.md` §3.2) và nhà cung cấp bên ngoài (hệ quả của P-4).

| Mã | Lớp | Yêu cầu | Ưu tiên |
|:---|:---|:---|:---:|
| **NFR-SEC-01** | Hành động vật lý | Không có đường tắt tới cơ cấu chấp hành ngoài gate; mọi đánh giá gate được ghi vết | P0 |
| **NFR-SEC-02** | Thiết bị | Kích hoạt Secure Boot và mã hóa flash trên ESP32-S3; hỗ trợ TPM trên Linux | P0 |
| **NFR-SEC-03** | Thiết bị | Bo mạch tham chiếu có nút ngắt micro vật lý | P0 |
| **NFR-SEC-04** | Mạng | TLS 1.3 toàn tuyến; mTLS hai chiều thiết bị ↔ đám mây; certificate pinning | P0 |
| **NFR-SEC-05** | Mạng | Mỗi thiết bị có chứng chỉ mật mã riêng, thu hồi được | P0 |
| **NFR-SEC-06** | Cập nhật | Firmware ký số; xác minh chữ ký trên chip trước khi áp dụng | P0 |
| **NFR-SEC-07** | Mã bên thứ ba | Sandbox giới hạn quyền truy cập chân actuator nhạy cảm | P0 (v1.1) |
| **NFR-SEC-08** | Nhà cung cấp bên ngoài | Dữ liệu âm thanh và văn bản gửi tới provider cloud phải đi qua kênh mã hóa TLS 1.3; hệ thống ghi nhận provider đang dùng trong vết ghi. Việc chọn provider tuân thủ quy định là trách nhiệm của người dùng | P0 |
| **NFR-SEC-09** | Bên gọi tool | MCP mặc định qua **stdio** (bên chạy tiến trình là người vận hành). Transport mạng vào v1.0 (Q-58, TSK-P2-04): **mặc định tắt**, chỉ bật khi có xác thực OAuth 2.1 và mTLS theo thiết bị (NFR-SEC-04); thiếu một trong hai thì từ chối khởi động. LLM và client MCP là bên gọi **không tin cậy** — `docs/spec/threat_model.md` §2b | P0 |
| **NFR-SEC-10** | Plugin của bên thứ ba | Plugin chạy trong tiến trình là mã người vận hành tin (`threat_model.md` §3): chỉ nạp khi được bật rõ, nguồn gốc (gói, phiên bản, băm tệp) in ra và ghi vào vết ghi; không API nào của `neuroedge.sdk` trao handle phần cứng cho bridge hay fact source (FR-EXT-03, Q-67) | P0 |
| **NFR-SEC-11** | Chống rò rỉ dữ liệu *(Q-72)* | **100%** lần gửi tới đích không khai bị chặn và ghi vết; LLM worker không mở được kết nối ngoài endpoint nhà cung cấp đã khai (FR-EGR-01 → 03). Rủi ro còn lại ghi trong threat model: worker bị lừa vẫn gửi được dữ liệu đã cho phép tới đích đã cho phép | P0 |
| **NFR-SEC-12** | Kênh chat *(Q-72)* | Lời duyệt chỉ hợp lệ qua bản ghi duyệt đã kiểm đủ (FR-CH-04); token bot chỉ nằm trong runtime tin cậy, không trong worker, vết ghi hay Blueprint; threat model có mục riêng cho kênh chat, gồm rủi ro tài khoản chat bị chiếm (thu hồi, hạn, trần: `TODOS.md` #62) | P0 |
| **NFR-SEC-13** | Key LLM của người dùng (BYOK) *(Q-72)* | Key chỉ nằm trong LLM worker trên máy nhà; không bao giờ trong vết ghi, hợp đồng, Blueprint, tin chat, hay máy chủ do NeuroEdge vận hành; runtime không giữ key | P0 |
| **NFR-SEC-14** | NeuroEdge Blueprint *(Q-72)* | `install` kiểm digest toàn gói trước khi ghi gì; gói không chạy mã tuỳ ý trên máy nhà lúc cài; cơ cấu `safe_state` khác `off` hiện riêng và cần xác nhận tại chỗ; bằng chứng "chưa ký" hiện rõ ở mọi nơi (FR-BP-03 → 06) | P0 |
| **NFR-SEC-15** | Relay tuỳ chọn *(Q-72)* | Relay không giải mã; relay bị chiếm chỉ lộ siêu dữ liệu, không đọc được vết ghi, không chèn được lệnh; sao lưu mã hoá phía máy nhà (FR-EGR-05) | P1 |

### 9.5 Quyền riêng tư (NFR-PRIV)

| Mã | Yêu cầu | Ưu tiên |
|:---|:---|:---:|
| **NFR-PRIV-01** | Luồng âm thanh xử lý trực tiếp, **không lưu trữ mặc định** | P0 |
| **NFR-PRIV-02** | Xử lý ngôn ngữ mặc định theo kiến trúc cloud-first; ưu tiên on-device khi năng lực phần cứng cho phép. Người dùng tự chọn provider và cấu hình mức độ riêng tư tương ứng | P0 |
| **NFR-PRIV-03** | Vết ghi mặc định chỉ lưu quyết định, không lưu dữ liệu thô; lưu thô phải bật tường minh | P0 |
| **NFR-PRIV-04** | Chế độ ẩn danh tại nguồn thay nội dung thô bằng hash mà không phá vỡ khả năng replay | P0 |
| **NFR-PRIV-05** | Dữ liệu vận hành chỉ được chia sẻ để cải thiện bộ phát hiện khi người dùng **bật tường minh**; mặc định tắt; đích hiện trong bản duyệt *(Q-72, FR-BP-09)* | P2 |

### 9.6 Khả năng quan sát (NFR-OBS)

| Mã | Yêu cầu | Ưu tiên |
|:---|:---|:---:|
| **NFR-OBS-01** | Mỗi phiên tương tác sinh đúng một tệp vết ghi hoàn chỉnh. *Runtime 24/7 (Q-72, chờ RFC):* một phiên một chuỗi đoạn vết ghi, mỗi đoạn replay được (FR-TRC-11) | P0 |
| **NFR-OBS-02** | Vết ghi hiển thị tỷ lệ System 1 / System 2, chi phí từng lượt và toàn bộ kết quả thẩm định gate | P0 |
| **NFR-OBS-03** | Vết ghi ghi độ trễ từng chặng đủ để đối chiếu với ngân sách `budget.p95_latency_ms` | P0 |
| **NFR-OBS-04** | Vết ghi trên máy nhà *(Q-72)*: giữ **30 ngày** gần nhất; flush khoảng 10 giây (khai được) và ngay khi có phán quyết chặn hay lời duyệt; mất điện mất tối đa phần đuôi sự kiện thường. Cỡ vết ghi 30 ngày của kịch bản bể cá đo trên G1 rồi ghi số vào dòng này (FR-TRC-12) | P0 |

### 9.7 Tương thích và chuẩn mở (NFR-COMP)

| Mã | Yêu cầu | Ưu tiên |
|:---|:---|:---:|
| **NFR-COMP-01** | Lõi phát hành theo PolyForm Noncommercial 1.0.0; lược đồ, đặc tả và bộ kiểm tuân thủ theo Apache-2.0 (Q-45, `LICENSING.md`) | P0 |
| **NFR-COMP-02** | Không tính năng an toàn cốt lõi nào bị khóa sau tài khoản trả phí | P0 |
| **NFR-COMP-03** | Mọi dịch vụ đám mây truy cập qua interface thay thế được (pluggable backend) | P0 |
| **NFR-COMP-04** | Lược đồ gate và vết ghi là chuẩn mở, quản trị theo quy trình RFC công khai | P0 |
| **NFR-COMP-05** | Phiên bản Python hỗ trợ tối thiểu: **Python 3.11+** (tận dụng `tomllib` tích hợp, `asyncio.TaskGroup` và tối ưu tốc độ bytecode) | P0 |
| **NFR-COMP-06** | Hệ điều hành hỗ trợ cho môi trường `linux`: Debian/Ubuntu trên ARM64 và x86-64 | P0 |

### 9.8 Chi phí và làm phiền (NFR-COST) *(Q-72)*

| Mã | Chỉ tiêu | Ngưỡng cam kết | Điều kiện đo | Ưu tiên |
|:---|:---|:---|:---|:---:|
| **NFR-COST-01** | Chi phí LLM của agent vận hành | Kịch bản bể cá **30 ngày mô phỏng < 2 USD**; chi phí của một kỳ không bao giờ vượt `llm_budget` quá chi phí của lượt đang chạy lúc chạm trần | G1 tua nhanh, provider và mô hình mặc định của Blueprint, đơn giá ghi cùng kết quả | P0 |
| **NFR-COST-02** | Ngân sách tin nhắn | Số tin không khẩn mỗi ngày không vượt ngân sách khai trong hợp đồng; tin khẩn không bị gom hay trễ vì ngân sách | Kịch bản 30 ngày trên G1, đếm tin theo loại | P0 |

---

## 10. Đặc tả giao diện dữ liệu

Bốn tệp định dạng tạo thành toàn bộ bề mặt dữ liệu **hiện có** của sản phẩm; Q-72 thêm các định dạng dự kiến ở §10.1a. Đặc tả trường chi tiết nằm ở Phụ lục A, B, C của tài liệu nguồn; mục này quy định **ràng buộc bắt buộc** đối với hiện thực.

### 10.1 Bốn tệp định dạng

| Tệp | Định dạng | Vai trò | Đặc tả chi tiết |
|:---|:---|:---|:---|
| `board.toml` | TOML | Bo mạch khai báo năng lực cung cấp | §4.2, Phụ lục A |
| `agent.toml` | TOML | Agent khai báo năng lực cần dùng, gate và môi trường hỗ trợ | §4.3 |
| `<gate>@<version>.yaml` | YAML | Điều kiện cho phép một hành động vật lý | §4.5, Phụ lục B |
| `<phiên>.json` | JSON | Vết ghi chuỗi sự kiện của một phiên tương tác | §3.7, Phụ lục C |

### 10.1a Định dạng dự kiến của Q-72

Chưa có mã, chưa có lược đồ. Mỗi dòng chạm `schemas/` hoặc vết ghi chuẩn mực nên **cần RFC** (`CONTRIBUTING.md` §3); tên tệp là dự kiến, chốt ở RFC.

| Định dạng | Vai trò | Yêu cầu | Trạng thái |
|:---|:---|:---|:---|
| Hợp đồng nhiệm vụ (`mission.v1`) | Điều khoản được/cấm, tần suất, khung giờ, nghĩa vụ, luồng dữ liệu, khi hỏng, hết hạn, `llm_budget`, ngân sách tin nhắn, tham số hỏi lại | FR-MSN-01 → 14 | Dự kiến, cần RFC |
| Manifest NeuroEdge Blueprint (`blueprint.v1`) | Kit, BOM, firmware, hợp đồng mẫu, gate, bộ phát hiện, bằng chứng, giấy phép, digest toàn gói; quan hệ với `manifest.v1` (FR-REG-02) chốt ở RFC | FR-BP-01 → 08 | Dự kiến, cần RFC |
| Định nghĩa bộ phát hiện | Ngưỡng, độ dốc xu hướng, cảm biến đứng im, dao động — khai trong hợp đồng nhiệm vụ hoặc Blueprint | FR-AGT-04 | Dự kiến, thuộc RFC `mission.v1` |
| Khai đích dữ liệu | Đích (LLM, chat, relay, webhook) và loại dữ liệu được gửi tới từng đích | FR-MSN-06, FR-EGR | Dự kiến, cần RFC |
| Bản ghi duyệt | Yêu cầu `{id, nonce, hạn, digest thay đổi, bản duyệt ≤ 5 dòng}` và lời trả lời; sự kiện trong `trace.v1` | FR-CH-04, FR-TRC-13 | Dự kiến, cần RFC (nguồn `chat:<id>`) |
| Đoạn vết ghi | Trạng thái đầu đoạn và digest đoạn trước, mở rộng `trace.v1` | FR-TRC-11 | Dự kiến, cần RFC (`trace.v1`) |
| `safe_state` trong `board.v1` | `safe_state` cho mọi cơ cấu, khoá liên động phần cứng bắt buộc khi khác `off` | FR-ACE-03 | Dự kiến, cần RFC an toàn có điều kiện; sửa `TODOS.md` #58 trước |

### 10.2 Ràng buộc bắt buộc đối với hiện thực

| Mã | Ràng buộc | Lý do |
|:---|:---|:---|
| **DATA-01** | Chân và cảm biến định danh bằng tên logic trong cả `board.toml` và `agent.toml` | Bảo toàn nguyên tắc tương đương môi trường |
| **DATA-02** | Đối chiếu năng lực thực hiện lúc build, kết quả là chặn hoặc cho phép, không có trạng thái cảnh báo mềm | Lỗi cấu hình không được lọt ra hiện trường |
| **DATA-03** | Gate là tệp độc lập với mã nguồn, có phiên bản SemVer riêng | Chia sẻ, kiểm toán và thương mại hóa được |
| **DATA-04** | Khối `evaluate` của gate ánh xạ một-một với ba nguyên thủy của `SystemOne` | Đổi nhà cung cấp mô hình không phải viết lại gate |
| **DATA-05** | Vết ghi là nguồn sự thật duy nhất cho cả chẩn đoán hiện trường và kiểm thử CI | Hiện trường và CI dùng chung một ngôn ngữ |
| **DATA-06** | Golden Reference là tập con của vết ghi, loại bỏ mốc thời gian và nội dung thô | Chịu được việc đổi mô hình, đổi prompt và đổi môi trường |

### 10.3 Ma trận tương thích phiên bản

| Thành phần | Quy tắc phiên bản | Thay đổi phá vỡ tương thích |
|:---|:---|:---|
| Lược đồ vết ghi | URL `/v1`, `/v2` | Tăng phiên bản chính; bổ sung trường tùy chọn không tăng |
| Lược đồ gate | `neuroedge.gate/v1` | Tăng phiên bản chính |
| Tệp gate cụ thể | SemVer | Mọi thay đổi trong `allow_when` |
| Lược đồ tool call (`schemas/tool-call.v1.json`: phong bì, mô tả tool) | URL `/v1`, `/v2` | Đổi tên, bỏ hoặc siết một trường; thêm trường tuỳ chọn hoặc nới `enum` không tăng (RFC-0015) |
| Lược đồ kết quả tool (`schemas/tool-result.v1.json`) | URL `/v1`, `/v2` | Như trên; `reason` là chuỗi mở và đối tượng kết quả mở, nên thêm `Reason` hay trường tuỳ chọn không tăng; thêm `status` hay `on_block` thì tăng (RFC-0015) |
| Lược đồ lỗi (`schemas/error.v1.json`) | URL `/v1`, `/v2` | Như trên (RFC-0015) |
| Danh mục mã lỗi (`schemas/error-codes.v1.json`) | URL `/v1`, `/v2` | Đổi nghĩa, đổi tên lớp, bỏ hoặc tái dùng một mã; thêm mã, `fields` hay `aliases` không tăng (RFC-0015 §3d) |
| Lược đồ bo mạch (`schemas/board.v1.json`, khoá `schema = "neuroedge.board/v1"` ở gốc `boards/*.toml`) | `neuroedge.board/v1` | Tăng phiên bản chính; vắng khoá ⇒ `v1`; bộ đọc từ chối phiên bản nó không đọc được (NE3001) trước khi thẩm định (RFC-0015 §3c) |
| Lược đồ dự kiến của Q-72 (`mission.v1`, `blueprint.v1`, khai đích, bản ghi duyệt) | URL `/v1`, `/v2` như mọi lược đồ | Quy tắc chốt ở RFC của từng lược đồ |
| Gói `neuroedge` | SemVer | Thay đổi bề mặt API công khai ([`docs/spec/python_api.md`](../docs/spec/python_api.md)) hoặc CLI |

---

## 11. Tiêu chí nghiệm thu phát hành

Mỗi mốc chỉ được công bố khi đạt **toàn bộ** tiêu chí tương ứng. Không chấp nhận đạt một phần hoặc lấy giá trị trung bình.
Các bản increment nội bộ trước khi công khai (I1–I5) không được công bố là đạt tiêu chí nào của mục này (Q-39).

### 11.1 Nghiệm thu v1.0 — Lõi

| # | Tiêu chí | Ngưỡng | Phương pháp kiểm chứng |
|:---:|:---|:---|:---|
| **A1** | Time-to-first-value | Trung vị **< 10 phút** trên 10 lập trình viên độc lập | Biên bản đo có mốc thời gian từng bước |
| **A2** | Tương đương môi trường | `neuroedge verify` đạt **100%** trên các target bậc 1: `sim`, `linux`, `esp32s3` | Chạy trong CI, lưu nhật ký |
| **A3** | Không có đường tắt tới actuator | **0** lối đi kích hoạt GPIO bỏ qua gate | Rà soát mã và kiểm thử thâm nhập |
| **A4** | Fail-closed | **100%** kịch bản suy giảm đều chặn hành động — riêng mất mạng: lượng giá qua fallback lệnh cục bộ, chặn khi fallback không chạy *(Q-14)* | Bộ kịch bản: mất mạng (có và không có fallback), timeout, dữ liệu mô hình không hợp lệ |
| **A5** | Kế thừa gate an toàn | Gate con nới lỏng gate cha — `allow_when`, `budget`, `on_block` (Q-18) hoặc `arguments` (Q-25) — bị từ chối trong **100%** trường hợp | Bộ kiểm thử phân giải kế thừa · corpus `fixtures/gates/invalid/` qua `neuroedge gate lint` |
| **A6** | Độ ổn định trên vi điều khiển *(không thoại — Q-77)* | **24 giờ** chạy liên tục không tràn bộ nhớ, với thẩm định gate, bốn gói nguyên thủy mở rộng và liên kết với host | Kiểm thử chịu tải trên bo mạch tham chiếu |
| **A7** | Vết ghi hợp lệ | **100%** phiên sinh tệp qua được `neuroedge trace validate` | Chạy tự động trong CI |
| **A8** | Tài liệu | 3 ứng dụng mẫu chạy được + 1 tài sản trực quan trong README | Kiểm chứng trên máy sạch |
| **A9** | Lược đồ công khai | JSON Schema truy cập được tại URL công bố, kèm bộ kiểm thử tuân thủ | Bên thứ ba chạy thử thành công |
| **A10** | Đủ nguyên thủy trên ba target | Mỗi nguyên thủy mở rộng của FR-HAL-08 có agent mẫu đạt `verify` **100%** trên `sim`, `linux`, `esp32s3` *(Q-53)* | Chạy trong CI và nightly trên bo mạch thật, lưu nhật ký |
| **A11** | ~~Dựng bằng hội thoại có hợp đồng~~ | Bỏ cùng NeuroEdge Lab (Q-77); dựng qua bộ tool MCP chuẩn đo ở A15, A17 | — |
| **A12** | Kit mẫu dựng được | Trung vị **≤ 1 ngày** từ mở hộp tới thiết bị thật chạy agent có gate, trên 5 người ngoài đội, mỗi người một kit *(Q-52)* | Biên bản đo có mốc thời gian từng bước |
| **A13** | Nền tảng mở | Một bên thứ ba nối NeuroEdge với một hệ sinh thái chưa từng có, ở kho riêng, chỉ từ tài liệu công khai, qua bộ test tuân thủ trong **≤ 1 ngày**, lõi không đổi dòng nào; che một MCP server sẵn có trong **≤ 3 lệnh** *(Q-67)* | Biên bản đo của bài kiểm `neuroedge-muse` (roadmap TSK-I2c-17); test CI cài plugin ngoài kho |

**Nghiệm thu NeuroEdge Blueprint đầu tiên — bể cá (Q-72).** A14 → A22 đo được ngay khi I2d, I2e xong, trên giả lập, trước cổng 8 tuần; chúng vẫn là tiêu chí của v1.0. RFC an toàn có điều kiện viết **từ chính các ca này**, không viết trước.

| # | Tiêu chí | Ngưỡng | Phương pháp kiểm chứng |
|:---:|:---|:---|:---|
| **A14** | Cài Blueprint | Người ngoài đội cài Blueprint bể cá và chạy được trên `sim` từ máy sạch trong **< 10 phút**, không tài khoản | Biên bản đo có mốc thời gian từng bước |
| **A15** | Hợp đồng mâu thuẫn | **100%** hợp đồng mâu thuẫn trong corpus bị từ chối **trước khi duyệt**, chỉ rõ cặp điều khoản đụng nhau | Corpus khép kín hai chiều chạy trong CI |
| **A16** | Mất mạng, mất LLM | Mất mạng: sục khí giữ chạy; sưởi theo luật phản xạ cục bộ; worker chết hay hết ngân sách: phản xạ và cảnh báo mẫu cứng vẫn chạy | Kịch bản G1; tầng phản xạ firmware trên G3 |
| **A17** | Lệnh vi phạm hợp đồng | **100%** lệnh vi phạm hợp đồng bị chặn trong bộ kịch bản, kể cả lệnh do LLM đề nghị ("tắt sục khí cho yên tĩnh") | Bộ kịch bản G1, assert trên phán quyết gate và trạng thái chân (FR-CI-L3) |
| **A18** | Luồng dữ liệu | Không ảnh nào rời mạng nội bộ khi hợp đồng cấm; **100%** lần gửi tới đích không khai bị chặn và ghi vết | Kịch bản G1 có đích giả; đếm sự kiện cửa ra trong vết ghi |
| **A19** | Báo chủ động có trần | Agent gửi **≥ 1** phát hiện xu hướng đúng; chi phí LLM của kịch bản 30 ngày mô phỏng **< 2 USD** | Kịch bản 30 ngày trên G1 (NFR-COST-01) |
| **A20** | Duyệt qua chat | Lời duyệt từ tài khoản chưa ghép đôi, từ nhóm, lời duyệt cũ (nonce đã dùng), hết hạn, digest lệch, hay do LLM worker gửi đều bị từ chối trong **100%** trường hợp | Bộ kịch bản FR-CH-04, FR-CH-05 |
| **A21** | `safe_state: on` không thành đường tắt | `board.v1` khai `safe_state: on` mà thiếu khoá liên động phần cứng bị từ chối nạp trong **100%** trường hợp; `safe_state` khai ngoài `board.v1` bị từ chối | Corpus `fixtures/boards/` (khi RFC vào) |
| **A22** | Replay | `replay` tái hiện **100%** phán quyết từ vết ghi, gồm từng đoạn của chuỗi vết ghi 30 ngày | Chạy trong CI trên vết ghi bằng chứng của Blueprint |

### 11.2 Nghiệm thu Developer Beta

| # | Tiêu chí | Ngưỡng |
|:---:|:---|:---|
| **B1** | Lập trình viên bên ngoài chạy thành công agent trên `sim` | ≥ 50 người |
| **B2** | Lập trình viên bên ngoài nạp và điều khiển thành công phần cứng thật | ≥ 10 người |
| **B3** | Gate an toàn do cộng đồng bên ngoài tự viết và đóng góp | ≥ 3 gate *(đo và báo cáo, không là điều kiện mở v1.1 — Q-41)* |
| **B4** | Tỷ lệ áp dụng Action CI | ≥ 50% dự án khởi tạo giữ lại và mở rộng kịch bản test gate |
| **B5** | Tỷ lệ chuyển đổi sang phần cứng thật | ≥ 15% người chạy `sim` nạp lên bo mạch trong 30 ngày |
| **B6** | Cổng 8 tuần — người ngoài tự cài *(Q-72)* | ≥ 3 người ngoài đội tự cài một NeuroEdge Blueprint và chạy được |
| **B7** | Cổng 8 tuần — chạy liên tục *(Q-72)* | ≥ 1 người chạy liên tục 2 tuần trên giả lập G2 hoặc G3 |
| **B8** | Cổng 8 tuần — có người muốn bán *(Q-72)* | ≥ 1 maker muốn đóng gói và bán Blueprint của mình |

**Cổng nhu cầu 8 tuần (Q-72, đảo Q-56).** B6 → B8 đo **8 tuần sau khi chốt Q-72**, trước Developer Beta; chúng là **cổng quyết định**, không phải điều kiện công bố Beta. Kết quả: đạt cả ba ⇒ đầu tư Hub, danh mục kit, Blueprint thứ hai và xét lại phạm vi v1.0; đạt B6, B7 mà trượt B8 ⇒ NeuroEdge là công cụ cá nhân, giữ vòng ① ②, tìm nguồn thu khác; trượt B6 hoặc B7 ⇒ đổi phân khúc hoặc thông điệp trước khi viết thêm tính năng. Song song: chấm ba buổi phỏng vấn đã có và hỏi thêm 10 người, trong đó ít nhất 5 maker, về việc bán thiết bị — việc của trưởng nhóm, AI agent không làm thay.

**Nguyên tắc vận hành giai đoạn Beta:** đóng băng tính năng mới trên dòng `1.0.x` (Q-39). Toàn bộ nguồn lực dành cho hỗ trợ kỹ thuật trực tiếp, hoàn thiện tài liệu và làm mượt trải nghiệm.

### 11.3 Nghiệm thu v1.1 — Tầng dịch vụ thương mại

> **Không còn increment nào dùng bộ C (Q-77):** I9, I10 đã bỏ khỏi roadmap (§6 của roadmap). Giữ bảng để đọc khi một `Q-N` mới mở lại tầng dịch vụ.

| # | Tiêu chí | Ngưỡng |
|:---:|:---|:---|
| **C1** | Độ tin cậy OTA | Đạt NFR-REL-01 |
| **C2** | Độ trễ thoại *(đo trọn vòng qua provider cloud)* | Đạt NFR-PERF-01 và NFR-PERF-07 |
| **C3** | Độ trễ thẩm định gate | Đạt NFR-PERF-02 và NFR-PERF-03 |
| **C4** | Hiệu quả định tuyến | Đạt NFR-PERF-05 |
| **C5** | Chia sẻ gate cộng đồng | ≥ 20 gate đạt từ 5 lượt cài đặt bởi người dùng độc lập |
| **C6** | Cơ cấu doanh thu | **Chỉ số theo dõi, không là điều kiện phát hành (Q-42):** doanh thu theo từng dòng của §8.4 — hoa hồng kit, chia doanh thu Blueprint, giấy phép thương mại theo thiết bị và license lõi (Q-45), relay, Fleet OS — so với đường hòa vốn, báo cáo hằng tháng *(NeuroEdge không có doanh thu inference — N4; dòng thu theo Q-72)* |
| **C7** | Đồng nhất định dạng vết ghi | Vết ghi từ lớp trừu tượng provider replay được trên máy cá nhân, không chuyển đổi |
| **C8** | Độ trễ quyết định `SystemOne` có cấu trúc | Đạt NFR-PERF-04, đo trên lưu lượng thực qua FR-TEL-06 |

---

## 12. Hệ chỉ số và yêu cầu đo đạc

Nguyên tắc: **mọi chỉ số trong mục này phải có một yêu cầu đo đạc tương ứng.** Chỉ số không đo được không phải chỉ số.

### 12.1 Yêu cầu đo đạc bắt buộc (FR-TEL)

| Mã | Yêu cầu | Phục vụ chỉ số | Ưu tiên |
|:---|:---|:---|:---:|
| **FR-TEL-01** | CLI thu thập số liệu **ẩn danh, có thể tắt (opt-out)** về các mốc: cài đặt, khởi tạo dự án, lần chạy `sim` đầu tiên, lần build phần cứng đầu tiên | TTFV, tỷ lệ chuyển đổi sim → phần cứng | P0 |
| **FR-TEL-02** | Chính sách thu thập số liệu công bố rõ ràng; lệnh tắt nêu ngay trong lần chạy đầu | Niềm tin cộng đồng | P0 |
| **FR-TEL-03** | Vết ghi ghi nhận tỷ lệ System 1 / System 2 và chi phí từng lượt | Hiệu quả định tuyến | P0 |
| **FR-TEL-04** | Registry ghi nhận số lượt tải và lượt kế thừa từng gate, phân biệt tác giả và người dùng khác | Chia sẻ gate cộng đồng, cột mốc G2/G3 (§11.2) | P0 (v1.1) |
| **FR-TEL-05** | Fleet OS ghi nhận kết quả từng chiến dịch OTA: số thiết bị, tỷ lệ lỗi, số ca rollback | Độ tin cậy OTA | P0 (v1.1) |
| **FR-TEL-06** | Lớp trừu tượng provider ghi nhận độ trễ từng chặng đủ để tính P95 theo từng nhóm tác vụ | SLA độ trễ | P0 |
| **FR-TEL-07** | *(Q-72)* CLI và runtime thu thập thêm, cùng chính sách ẩn danh và opt-out của FR-TEL-01, các mốc: cài một Blueprint, nối kênh chat, hợp đồng nhiệm vụ đầu tiên được duyệt, runtime chạy liên tục mỗi 7 ngày. Index tĩnh không đếm lượt cài, nên B6 → B8 còn đo bằng tiếp xúc trực tiếp với người thử | Cổng 8 tuần (B6, B7), M9 | P0 |
| **FR-TEL-08** | *(Q-72)* Lượt bấm và đơn hàng qua liên kết kit lấy từ báo cáo liên kết của nhà bán, không từ thiết bị người dùng | Nguồn thu thử đầu, C6 | P1 |

### 12.2 Bảng chỉ số theo mốc

Ngưỡng nằm ở §11 và §9; bảng này chỉ nối mỗi chỉ số với tiêu chí và nguồn dữ liệu.

| Chỉ số | Mốc | Tiêu chí | Nguồn dữ liệu |
|:---|:---:|:---|:---|
| Time-to-first-value | v1.0 | A1 | Biên bản đo trực tiếp 10 người |
| Tương đương môi trường | v1.0 | A2 | Nhật ký CI |
| Tỷ lệ áp dụng Action CI | Beta | B4 | FR-TEL-01 |
| Tỷ lệ chuyển đổi sang phần cứng | Beta | B5 | FR-TEL-01 |
| Độ tin cậy OTA | v1.1 | C1 (NFR-REL-01) | FR-TEL-05 |
| Độ trễ thoại P95 | v1.1 | C2 (NFR-PERF-01, 07) | FR-TEL-06 |
| Độ trễ gate P95 | v1.1 | C3 (NFR-PERF-02, 03) | FR-TEL-06 |
| Độ trễ quyết định `SystemOne` | v1.1 | C8 (NFR-PERF-04) | FR-TEL-06 |
| Tiết kiệm chi phí token | v1.1 | C4 (NFR-PERF-05) | FR-TEL-03 |
| Chia sẻ gate cộng đồng | v1.1 | C5 | FR-TEL-04 |
| Cơ cấu doanh thu | v1.1 | C6 | Hệ thống hóa đơn; báo cáo liên kết kit (FR-TEL-08) |
| Cài Blueprint trên máy sạch | I2e | A14 | Biên bản đo trực tiếp |
| Chi phí LLM 30 ngày mô phỏng | I2d | A19 (NFR-COST-01) | Vết ghi kịch bản G1 |
| Người ngoài tự cài Blueprint | Cổng 8 tuần | B6 | FR-TEL-07, tiếp xúc trực tiếp |
| Chạy liên tục 2 tuần | Cổng 8 tuần | B7 | FR-TEL-07 |
| Maker muốn bán Blueprint | Cổng 8 tuần | B8 | Phỏng vấn của trưởng nhóm |

**Chỉ số bị loại bỏ có chủ ý:** số sao GitHub, lượt tải trang, lượt xem tài liệu. Các chỉ số này đo sự chú ý, không đo giá trị sử dụng.

---

## 13. Phụ thuộc, rủi ro và giả định

### 13.1 Phụ thuộc kỹ thuật bên ngoài

| Thành phần | Vai trò | Rủi ro phụ thuộc | Phương án giảm thiểu |
|:---|:---|:---|:---|
| ESP-IDF | Toolchain cho `esp32s3` | Thay đổi API giữa các bản lớn | Ghim phiên bản; kiểm thử nightly phát hiện sớm |
| libfvad, Silero VAD, WebRTC AEC, Opus | Chuỗi xử lý tín hiệu | Ngừng bảo trì thượng nguồn | Bọc sau interface nội bộ, thay thế được từng thành phần |
| ESP-SR MultiNet hoặc TFLite Micro / ESP-NN | Bộ nhận diện lệnh cố định cục bộ trên `esp32s3` *(Q-14, thay Sherpa-ONNX)* | Giấy phép ESP-SR (theo hiểu biết: chỉ cho dùng trên SoC Espressif); bộ nhớ | Xác minh giấy phép trước I5; spike TSK-S1-10 đo thêm MultiNet; cùng một ngữ pháp lệnh cho mọi backend |
| `gpiod` | Truy cập GPIO trên Linux | Khác biệt giữa các bản phân phối | Giới hạn hỗ trợ ở Debian/Ubuntu (NFR-COMP-06) |
| Nhà cung cấp `SystemOne` | Quyết định có cấu trúc | Đổi giá, siết truy cập, tự ship framework | Interface từ ngày đầu (FR-MDL-01); fallback lệnh cố định cục bộ là P0 *(Q-14)* |
| Nhà cung cấp `SystemTwo` | Suy luận mở | Tương tự | Định tuyến đa nhà cung cấp (FR-GW-03) |
| SchemaStore | Nhận diện schema trong IDE | Quy trình duyệt chậm | Không chặn phát hành; là yêu cầu P1 |
| Telegram Bot API *(Q-72)* | Kênh chat đầu tiên: báo cáo, lệnh, lời duyệt (FR-CH) | Đổi API, giới hạn tần suất, khoá bot; tài khoản người dùng bị chiếm | Adapter sau giao diện kênh của runtime; hàng đợi có hạn + cảnh báo tại chỗ khi kênh sập (FR-AGT-07); lời duyệt chỉ qua bản ghi duyệt (FR-CH-04) |
| Slack, Zalo API *(Q-72)* | Kênh chat sau Telegram | Điều khoản dùng bot, xác minh doanh nghiệp (Zalo) | P1; cùng giao diện kênh, không đổi luật duyệt |
| ESPHome (host platform, external component) *(Q-72)* | Tầng giả lập G4 và đường cắm vào thiết bị của cộng đồng Home Assistant | Đổi cấu hình hay API giữa các bản | Ghim phiên bản trong Blueprint; G4 chỉ là một tầng, không thay G1–G3 |
| Ollama và mô hình tại chỗ *(Q-72)* | LLM của người dùng chạy tại máy nhà, qua LiteLLM | Chất lượng và tài nguyên trên Pi; đổi API | Sau LiteLLM (Q-10); bộ phát hiện tất định không phụ thuộc LLM (FR-AGT-04) |
| Wokwi, Velxio *(Q-72)* | Lựa chọn cho tầng giả lập G3 (firmware ESP32 trên máy) | Wokwi mã đóng, cần token, không I2S — Q-21 và Q-69 đã loại khỏi CI chuẩn; Velxio chưa kiểm | Espressif QEMU vẫn là đường chính của G3; dùng Wokwi hay Velxio chỉ sau khi đối chiếu lại với Q-21, Q-69 |
| Nhà bán linh kiện (liên kết) *(Q-72)* | Kit có BOM và nơi mua (FR-BP-07) | Hết hàng, đổi mã hàng, đổi chương trình liên kết | Mỗi linh kiện có nơi mua thay thế; NeuroEdge chưa giữ kho |

### 13.2 Rủi ro sản phẩm

Mục này ghi rủi ro **sản phẩm và thực thi**. Rủi ro **chiến lược** (cạnh tranh, mô hình kinh doanh, phân mảnh phạm vi) nằm ở §13 với hệ đánh số `#1–#6`. Ba cặp giao nhau giữa hai sổ: **R-4 ↔ §11 #1** (phụ thuộc nhà cung cấp mô hình) · **R-6 ↔ §11 #5** (mất kết nối đám mây) · **R-7 ↔ §11 #6** (phủ rộng phần cứng). Các rủi ro còn lại thuộc đúng một sổ. R-8 → R-20 lấy từ bảng rủi ro của proposal Blueprint (`docs/business/proposal-blueprint-2026-10-11.md`, Q-72); từ đây, bảng này là nơi theo dõi chúng.


| # | Rủi ro | Mức độ | Dấu hiệu cảnh báo sớm | Phương án ứng phó |
|:---:|:---|:---:|:---|:---|
| **R-1** | Phạm vi Khối 1b vượt thời hạn do tối ưu bộ nhớ vi điều khiển | Trung bình *(hạ từ Cao theo CR-1.0)* | Spike TSK-S1-10 trượt một ngưỡng Q-3, hoặc 3 tuần sau khi I3 phát hành vẫn chưa có vòng thu/phát âm thanh trên bo mạch | Kiến trúc cloud-first đã đưa STT/TTS ra khỏi vi điều khiển, giảm đáng kể áp lực bộ nhớ (P-4, FR-PER-07). Nếu vẫn trượt: **không cắt thoại** (Q-44) — mở ngay một `Q-N` lập lại kế hoạch I5 (TSK-S5-05, TSK-S5-07) và dời dự báo v1.0 |
| **R-2** | Môi trường `sim` lệch khỏi phần cứng theo thời gian | Cao | `neuroedge verify` bắt đầu có sai lệch lẻ tẻ | Nightly trên bo mạch thật (NFR-REL-03); coi mọi sai lệch là lỗi chặn phát hành |
| **R-3** | Lập trình viên bỏ qua Action CI, chỉ dùng framework như thư viện thoại | Trung bình | Tỷ lệ áp dụng Action CI dưới 50% ở Beta | Đưa test gate vào scaffold mặc định; tài liệu lấy Action CI làm trung tâm |
| **R-4** | Nhà cung cấp mô hình thay đổi điều kiện truy cập | Trung bình | Thay đổi điều khoản API, vendor công bố SDK thiết bị | Mở rộng fallback cục bộ vượt ngữ pháp lệnh cố định của Q-14 |
| **R-5** | Hiệu ứng mạng chia sẻ — gate và NeuroEdge Blueprint — không hình thành *(viết lại theo Q-72)* | Cao | Cổng 8 tuần trượt B6 hoặc B8; dưới 3 gate cộng đồng ở cuối Beta | Theo nhánh của cổng 8 tuần (§11.2): trượt B8 ⇒ giữ vòng ① ② như công cụ cá nhân, không đầu tư Hub thu phí, tìm nguồn thu khác; trượt B6 ⇒ đổi phân khúc hoặc thông điệp trước khi viết thêm tính năng. Hub thu phí chỉ mở khi cổng đạt (FR-BP-10) |
| **R-6** | Phụ thuộc provider cloud khi mất kết nối | Trung bình | Tỷ lệ phiên kết thúc với lý do `gate_unreachable` tăng bất thường · Gián đoạn tích lũy của provider vượt cam kết | Fail-closed đã chặn mọi hành động vật lý khi không thẩm định được gate (NFR-RES-04, A4); gate và máy trạng thái chạy hoàn toàn trên thiết bị. **Fallback cục bộ là P0** (Q-14, FR-ACE-03): gate vẫn lượng giá được khi mất mạng |
| **R-7** | Phủ rộng phần cứng ở Giai đoạn 2 làm loãng chất lượng bậc 1 | Trung bình | Thời gian sửa lỗi trên bo mạch bậc 1 kéo dài · Kiểm thử hằng đêm thất bại thường xuyên hơn · Hỗ trợ bậc 3 chiếm quá 10% thời gian đội lõi | Phân tầng FR-TGT-08: đội lõi chỉ cam kết bậc 1 và bậc 2; bậc 3 do cộng đồng tự port và tự kiểm chứng. Mọi ngưỡng trong §9 và §11 vẫn neo vào bậc 1. Mỗi khối Giai đoạn 2 chỉ thêm tối đa một bo mạch tham chiếu |
| **R-8** | Dàn rộng: ba vòng là ba sản phẩm *(Q-72)* | Cao | I2d hay I2e kéo dài quá khoảng 6 tuần; làm tính năng không thuộc Blueprint bể cá | Một Blueprint đi trọn ba vòng; sáu động từ chỉ nằm trong định dạng Blueprint, không làm cùng lúc; thoại, Studio, `jetson` tạm dừng |
| **R-9** | Chợ hai phía khởi động lạnh *(Q-72)* | Cao | Index có dưới 3 Blueprint ở cổng 8 tuần | Đội NeuroEdge tự làm 5–10 Blueprint đầu, như Shopify tự dựng theme đầu tiên |
| **R-10** | Không ai muốn bán Blueprint *(Q-72)* | Cao | Không maker nào trong các buổi phỏng vấn từng bán thiết bị hay muốn bán (B8) | Hỏi maker "bạn từng làm thiết bị cho người khác chưa, có ai trả tiền chưa?" **trước** khi xây Hub thu phí; nhánh "trượt ③" của cổng 8 tuần |
| **R-11** | Tin chủ động gây phiền, người dùng tắt thông báo *(Q-72)* | Trung bình | Người thử tắt thông báo hay rời kênh chat trong hai tuần đầu | Ngân sách tin nhắn, gom tóm tắt, tin khẩn mẫu cứng (FR-AGT-06, NFR-COST-02) |
| **R-12** | Hoá đơn LLM khó đoán *(Q-72)* | Trung bình | Chi phí kịch bản 30 ngày vượt 2 USD; người thử phàn nàn về hoá đơn | Bộ phát hiện tất định trước, LLM sau; trần chi phí trong hợp đồng (FR-AGT-04, FR-AGT-05, NFR-COST-01) |
| **R-13** | Máy nhà giữ key LLM và điều khiển thiết bị *(Q-72)* | Trung bình | Prompt injection qua tin chat chạm được HAL hay key | Hai tiến trình: worker không tin cậy giữ key, runtime giữ HAL (FR-AGT-01, 02); mạng của worker chỉ tới đích đã khai (FR-EGR-03); hợp đồng chỉ người khoá (Q-71) |
| **R-14** | Blueprint độc hại trên Hub *(Q-72)* | Trung bình | Một gói khai quyền rộng, đích dữ liệu lạ, hay `safe_state` khác `off` | Blueprint chỉ khai báo; digest toàn gói; `safe_state` khác `off` chỉ trong `board.v1` có khoá liên động và hiện riêng khi cài; người cài tự chạy `replay`; quyền hiện ở bản duyệt (FR-BP-01 → 06) |
| **R-15** | Người dùng bấm duyệt không đọc *(Q-72)* | Trung bình | Lời duyệt tới trong vài giây sau yêu cầu, đều đặn | Bản duyệt ≤ 5 dòng, chỉ nêu điều khoản khác mặc định; mở rộng quyền dữ liệu chỉ duyệt tại chỗ (FR-MSN-12, FR-MSN-14) |
| **R-16** | Giả lập khác phần cứng thật *(Q-72)* | Trung bình | Người thử trên bo thật gặp lỗi không tái hiện trên G1–G4 | Bốn tầng giả lập; mua phần cứng trước khi bán Blueprint đầu tiên; giới hạn của giả lập ghi rõ (§4.2) |
| **R-17** | Bằng chứng chưa ký, người bán sửa được vết ghi *(Q-72)* | Trung bình | Một Blueprint có bằng chứng không khớp hành vi khi người cài `replay` | Chấp nhận ở MVP; mọi nơi ghi "chưa ký"; người cài tự `replay`; ký vết ghi trước khi Hub thu tiền cho người bán (`TODOS.md` #1, FR-BP-04) |
| **R-18** | Tài khoản chat bị chiếm thì duyệt được thay chủ *(Q-72)* | Trung bình | Lời duyệt từ vị trí hay thiết bị lạ; nhiều lời duyệt trong thời gian ngắn | Ghép đôi tại chỗ, bản ghi duyệt một lần có hạn và digest (FR-CH-03, 04); mở rộng quyền dữ liệu chỉ duyệt tại chỗ; thu hồi, hạn ghép đôi, trần lời duyệt: `TODOS.md` #62. Hệ quả đã chấp nhận khi chốt Q-72 |
| **R-19** | Bị hiểu là chức năng an toàn được chứng nhận *(Q-72)* | Cao (pháp lý) | Người dùng hay Blueprint quảng cáo thiết bị "an toàn" cho ca y tế, người già | Q-38 trong README, bản duyệt và Blueprint; bảo vệ nguy hiểm luôn do phần cứng (N5); ca y tế và người già để sau (§14) |
| **R-20** | Phần cứng là bùn: giao hàng, đổi trả, chất lượng *(Q-72)* | Cao | Khiếu nại về linh kiện tới NeuroEdge | Chỉ liên kết bán, chưa giữ kho (FR-BP-07) |

### 13.3 Giả định cần kiểm chứng

**Nơi duy nhất** của danh mục giả định; §13 dẫn về đây. Mỗi giả định có lý do quan trọng, phương pháp đo và mốc đánh giá.

| # | Giả định | Vì sao quan trọng | Phương pháp kiểm chứng | Mốc |
|:---:|:---|:---|:---|:---:|
| **G-a** | Đơn giá quản trị fleet $1/thiết bị/tháng là mức thị trường chấp nhận | Quyết định quy mô đội thiết bị cần đạt để hòa vốn (`docs/architecture/vi/16-ecosystem-landscape.md` §7) | Thử nghiệm gói nâng cao (cam kết SLA, kiểm toán vết) với 5 khách hàng doanh nghiệp đầu; đo mức sẵn sàng chi trả thêm | 90 ngày sau khi I9 phát hành (Q-43) |
| **G-b** | Tỷ lệ chuyển đổi `sim` → phần cứng ≥ 15% | Xác nhận `sim` thật sự là phễu dẫn tới phần cứng (`docs/architecture/vi/16-ecosystem-landscape.md` §5) | Số liệu ẩn danh từ CLI (FR-TEL-01); rà soát ở mốc 100 lập trình viên | Khi I8 (Beta) đóng — cùng chỉ số với B5 (Q-43) |
| **G-c** | Định tuyến hai mô hình tiết kiệm ≥ 60% chi phí token | Minh chứng định lượng cho kiến trúc System 1 / System 2 | Đo trên lưu lượng thực qua lớp trừu tượng provider, tách theo nhóm tác vụ | 90 ngày sau khi I9 phát hành (Q-43) |
| **G-d** | Cộng đồng thực sự muốn chia sẻ và tái sử dụng gate | Cơ sở của hiệu ứng mạng trước khi mở Marketplace | Tần suất tải và kế thừa trên Registry miễn phí trong 12 tháng | 12 tháng sau khi I10 phát hành; tín hiệu sớm: B3 (Q-43) |
| **G-e** | Tái hiện vết ghi giảm 70% chuyến đi hiện trường | Nền của mô hình TCO (Q-72) | Dữ liệu bảo hành thực tế từ 3 khách hàng AURA đầu tiên, phân loại nguyên nhân sự cố (phần mềm/cấu hình vs hỏng vật lý) | 6 tháng sau ba site AURA đầu tiên (Q-43) |
| **G-f** | Maker muốn bán thiết bị mình dựng, qua NeuroEdge Blueprint *(Q-72)* | Phép thử của cả mô hình Q-72; nếu sai, NeuroEdge là công cụ cá nhân | Phỏng vấn ít nhất 5 maker về việc bán; B8 | Cổng 8 tuần sau khi chốt Q-72 |
| **G-g** | Người dùng chấp nhận tự trả LLM bằng key của mình (BYOK) *(Q-72)* | NeuroEdge không kiếm tiền từ token và không giữ key; nếu sai, cần một đường LLM khác | Tỷ lệ người thử nhập key hay dùng mô hình tại chỗ khi tới bước báo chủ động (FR-TEL-07) | Cổng 8 tuần sau khi chốt Q-72 |
| **G-h** | Tin báo chủ động có giá trị, người dùng không tắt *(Q-72)* | Vòng ② là lý do dùng mỗi ngày | Tỷ lệ người thử còn nhận tin sau 2 tuần; phản hồi về phát hiện xu hướng | Khi người thử đầu tiên đạt B7 |
| **G-i** | Liên kết bán kit chuyển thành đơn hàng *(Q-72)* | Nguồn thu thử đầu | Báo cáo liên kết của nhà bán (FR-TEL-08) | 90 ngày sau khi I2e phát hành |

---

## 14. Ngoài phạm vi

Danh mục loại trừ tường minh — **nơi duy nhất** của trạng thái và điều kiện xem xét lại. Mọi đề xuất thuộc danh mục này bị bác bỏ trừ khi có quyết định thay đổi phạm vi chính thức.

**Bộ lọc ưu tiên PF-1 → PF-4** (cột "Tiêu chí" dưới đây):

| # | Bộ lọc | Câu hỏi |
|:---:|:---|:---|
| **PF-1** | Thời gian tới giá trị đầu tiên | Có rút ngắn thời gian từ `pip install` tới lần chạy thành công đầu tiên không? |
| **PF-2** | Nền móng không bổ sung muộn được | Không làm ngay thì sau này có phải viết lại kiến trúc không? |
| **PF-3** | Nhu cầu đã kiểm chứng | Đã có người dùng thật yêu cầu chưa, hay chỉ là phán đoán? |
| **PF-4** | An toàn pháp lý | Có kéo theo giữ tiền hộ, KYC, giấy phép tài chính hay trách nhiệm pháp lý vượt khả năng không? |

Vi phạm PF-4 → **chặn**, chỉ xét lại khi có đánh giá pháp lý riêng. Thoả PF-1 hoặc PF-2 → ưu tiên. Chưa rõ PF-3 → hoãn để kiểm chứng. Chi trả cho người bán Blueprint chạm PF-4 (giữ tiền hộ hay đứng làm merchant of record): xét sau cổng 8 tuần, trước khi Hub thu tiền (Q-72).

| Hạng mục | Trạng thái | Tiêu chí | Điều kiện xem xét lại |
|:---|:---|:---:|:---|
| Marketplace thương mại có thu phí | **Hub tối thiểu vào phạm vi** (Q-72): index tĩnh NeuroEdge Blueprint, không máy chủ, không thu phí (FR-BP-05, I2e). **Thu phí: hoãn tới sau cổng 8 tuần** | PF-3 | Cổng 8 tuần đạt (B6–B8), ký vết ghi (`TODOS.md` #1), OCI Registry và đường ray FR-REG (FR-BP-10) — thay điều kiện cột mốc G1–G4 của §11.2 cho riêng Blueprint. Index cộng đồng của plugin (FR-EXT-08) không bao giờ thu phí, không xếp hạng trả tiền |
| Thanh toán tự động giữa agent | Chặn | PF-4 | Đạt cột mốc và có đánh giá pháp lý riêng |
| Chương trình chứng nhận phần cứng có thu phí | Chặn | PF-3 | Đạt cột mốc và có quy trình kiểm chuẩn độc lập |
| Thị giác máy tính (camera, NPU) | **Đưa vào Giai đoạn 2**, tách hai bước | PF-1, PF-3 | **2a mở danh sách target:** RFC-0002 được phê duyệt · **2b hiện thực** (gồm RFC nguyên thủy `vision.in`): nhu cầu camera đo được từ khách hàng thật, TTFV thoại vẫn < 10 phút |
| Jetson | **Đưa vào Giai đoạn 2** ở bậc 2 (FR-TGT-08) — **tạm dừng** (Q-72) | PF-3 | RFC-0002 được phê duyệt và có nhu cầu đo được từ khách hàng thật; sau cổng 8 tuần |
| Tự phát triển SLAM, tránh vật cản, dẫn đường tự hành, drone | Chặn — **ngoại lệ Q-34:** tích hợp nguyên bản ROS 2/Nav2, gate xét mọi lệnh tốc độ (roadmap I14) | PF-1, PF-3 | Không có — dẫn đường thuộc ROS 2/Nav2 |
| Matter, HomeKit | Hoãn — tới khi đạt điều kiện kích hoạt | PF-3 | Có nhu cầu đo được từ khách hàng thật. Cộng đồng tự làm được dưới dạng plugin cơ cấu từ xa (FR-EXT-07, Q-67) mà không cần đội lõi |
| SSO/SAML, chứng chỉ SOC 2 | Hoãn — tới khi đạt điều kiện kích hoạt | PF-3 | Có hợp đồng doanh nghiệp yêu cầu cụ thể |
| Chứng nhận an toàn chức năng (SIL theo IEC 61508, PL theo ISO 13849, ISO 13482) | Chặn tạm thời (Q-38) | PF-3 | Câu C6 của bộ phỏng vấn (`docs/business/cong-nhu-cau-2026-10-25/`, nay chỉ là đầu vào thông tin — Q-56): một phân khúc có nhãn **R** ≥ 3/5 (`CEO-T2`), hoặc người mua robot trả lời như vậy (`TODOS.md` #40) |
| Multi-region, on-premise | Hoãn — tới khi đạt điều kiện kích hoạt | PF-3 | Có ràng buộc chủ quyền dữ liệu từ khách hàng thật |
| Mô hình dự phòng cục bộ đã tinh chỉnh | Hoãn có điều kiện | PF-3 | Xuất hiện dấu hiệu cảnh báo R-4 hoặc R-6 |
| Dashboard BI tùy biến, engine cảnh báo phức tạp | Hoãn vô thời hạn | PF-1, PF-3 | Không có. **Không gồm** bộ phát hiện tất định của agent vận hành (ngưỡng, xu hướng, cảm biến đứng im — FR-AGT-04): chúng **thuộc phạm vi** (Q-72), khai trong hợp đồng hay Blueprint, không phải engine cảnh báo tổng quát |
| Thoại (FR-PER, NFR-PERF-01, 07, A6), NeuroEdge Studio (Q-51) | **Tạm dừng** (Q-72) — vẫn thuộc phạm vi v1.0 (Q-52), không cắt, không xoá yêu cầu | PF-3 | Sau I2d, I2e; phạm vi v1.0 xét lại ở cổng 8 tuần |
| Thị trường dọc: y tế, chăm người già, giúp việc gia đình; ao tôm và nuôi trồng | Hoãn (Q-72) | PF-3, PF-4 | Sau cổng 8 tuần. Ca y tế và người già cần đánh giá pháp lý riêng vì R-19 (Q-38); ao tôm là đổi giao diện của Blueprint bể cá |
| Ký vết ghi bằng chứng của Blueprint | Hoãn (Q-72) | PF-3 | Trước khi Hub thu tiền cho người bán (`TODOS.md` #1) |
| Kiến trúc Kubernetes | Hoãn vô thời hạn | PF-1 | Vượt quy mô 50.000 thiết bị |
| Tự huấn luyện tinh chỉnh mô hình | Hoãn vô thời hạn | PF-3 | Không có |
| Huấn luyện wake-word tùy biến | Hoãn sau v1.0 | PF-1 | Sau khi runtime `esp32s3` ổn định |
| Đội lõi tự port thêm biến thể bo mạch ngoài bậc 1 và bậc 2 | Hoãn vô thời hạn — **trừ RP2350** làm node của robot phân tầng (Q-33) | PF-1 | Không có — độ phủ phần cứng mở rộng qua **bậc 3 do cộng đồng port** (FR-TGT-08), không qua đội lõi |
| Chương trình chứng nhận phần cứng **miễn phí, tự kiểm chứng** | **Đưa vào Giai đoạn 2** | PF-2, PF-3 | ≥ 3 bản port bậc 3 vượt Bộ kiểm thử tuân thủ *(phân biệt với dòng chứng nhận **có thu phí** phía trên, vẫn ở trạng thái Chặn)* |

---

## 15. Sổ quyết định

Mọi quyết định kỹ thuật, đã chốt hoặc còn mở — xem cột Trạng thái.

**Đây là sổ quyết định duy nhất của dự án.** Mọi quyết định kỹ thuật, kể cả quyết định phát sinh trong lúc thực thi, đều được cấp mã và ghi tại đây. `neuroedge-roadmap.md` §10 không định nghĩa quyết định mới — nó chỉ theo dõi **hạn chốt, người quyết và trạng thái** của cùng bộ mã này.

| # | Hạng mục | Trạng thái | Nội dung đã chốt chính thức |
|:---:|:---|:---:|:---|
| **Q-1** | Phiên bản Python tối thiểu | **ĐÃ CHỐT** | **Python 3.11+** (NFR-COMP-05: tích hợp sẵn `tomllib`, TaskGroup/ExceptionGroup, bytecode nhanh hơn 25%). |
| **Q-2** | Bo mạch tham chiếu chính thức | **ĐÃ CHỐT** | **ESP32-S3-Box-3** (§3.4: tích hợp sẵn LCD ST7789, dual-mic ES7210, loa ES8311, dock GPIO; tránh nhiễu clock I2S do câu dây). |
| **Q-3** | Ngân sách SRAM/PSRAM & firmware | **ĐÃ CHỐT** | **SRAM tự do ≥ 120 KB**, **PSRAM ≥ 2 MB** (ringbuffer + VAD/wake-word), **Firmware ≤ 3,5 MB** (vừa phân vùng kép A/B 16MB Flash). |
| **Q-4** | Nhà cung cấp System 1/2 ở v1.0 | **ĐÃ CHỐT** *(sửa 2026-09-23; 2026-09-26)* | **System 1:** Jev (cloud) + **fallback cục bộ = bộ nhận diện lệnh cố định** (Q-14); **System 2:** **`claude-sonnet-5`** & GPT-4o-mini **qua LiteLLM** (Q-10). Kết nối theo Q-12: System 2 qua chat completions; Jev qua endpoint quyết định System One của OpenRouter (`POST {api_base}/systemone`), bảng `[system_one]` (TSK-I4-02). |
| **Q-5** | Xác thực & chống lạm dụng Registry | Chờ v1.1 | Thiết kế trước khi I10 (Registry) mở, theo chuẩn CNCF ORAS và GitHub token. |
| **Q-6** | Chính sách lưu trữ vết ghi Fleet OS | **ĐÃ CHỐT** *(2026-09-25, CPO)* | **Fleet Standard giữ vết 90 ngày; Fleet Enterprise giữ 3 năm.** Vết lên kho theo FR-FLT-05 và chỉ chứa quyết định, không dữ liệu thô (NFR-PRIV-03). Ràng buộc là dữ liệu cá nhân nên thời hạn là mức trần, không phải mức sàn. Hạn mức theo thiết bị chỉ để chặn lặp vòng khi dựng Khối 2. |
| **Q-7** | Từ khóa kích hoạt mặc định v1.0 | **ĐÃ CHỐT** | *"Hey Neuro"* qua mô hình `microWakeWord` (tối ưu cho Box-3) và `openWakeWord` (Linux/Sim). |
| **Q-8** | Ngôn ngữ lõi firmware | **ĐÃ CHỐT** | **C/C++ trên ESP-IDF** cho `esp32s3`; Python cho `sim` và `linux`. Kéo theo nghĩa vụ đặc tả chuẩn tắc và bộ vector tuân thủ dùng chung cho hai hiện thực. |
| **Q-9** | Lượng giá CEL trên vi điều khiển | **ĐÃ CHỐT** | **`neuroedge build` biên dịch gate thành cây quyết định tất định**; firmware chỉ duyệt cây, không nhúng CEL VM trên thiết bị. Trình biên dịch và duyệt cây là mã NeuroEdge không nhận phụ thuộc. Dạng `allow_when` biên dịch là ánh xạ toán tử; chuỗi CEL hoãn (TSK-S2-06). Định dạng cây trên MCU dùng bố cục nhị phân `NETR` (Q-23). Lý do: bảo đảm tương đương môi trường và nhẹ bộ nhớ. |
| **Q-10** | Mức độ phụ thuộc vào LiteLLM | **ĐÃ CHỐT** *(2026-09-23)* | LiteLLM dùng như **thư viện định tuyến (SDK)** sau giao diện nội bộ `neuroedge.models.providers`, không chạy proxy server. Cài qua **extra `neuroedge[cloud]`** để giữ cài đặt mặc định nhẹ và keyless (FR-DX-02). |
| **Q-11** | Ngoại lệ giấy phép: Hawkbit EPL-2.0, EMQX BSL, LiteLLM | **ĐÃ CHỐT** *(LiteLLM 2026-09-23; Hawkbit/EMQX 2026-09-25)* | **LiteLLM: ĐÃ DUYỆT** (2026-09-23) — `litellm==1.102.0` giấy phép MIT, wheel không chứa thư mục `enterprise/`, 55 phụ thuộc bắc cầu đều MIT/BSD/Apache-2.0/PSF + MPL-2.0 (`certifi`, `tqdm`) + CNRI-Python (`regex`). **Chính sách phụ thuộc bắc cầu:** cho phép MIT, BSD-2/3-Clause, Apache-2.0, ISC, PSF, CNRI-Python, MPL-2.0 (chỉ dùng nguyên bản, không sửa); *CNRI-Python ghi thêm 2026-09-24:* giấy phép lịch sử của Python 1.6, OSI duyệt, không copyleft, chỉ buộc giữ thông báo bản quyền — đến qua `regex` (litellm → tiktoken → regex), pip tự cài, không đóng gói lại nên không phát sinh nghĩa vụ; cấm GPL/LGPL/AGPL, SSPL, BSL, giấy phép thương mại hoặc không xác định; cưỡng chế bằng `scripts/check_licences.py` trong job CI `cloud-extra`. *Zlib và CC0-1.0 ghi thêm 2026-09-26, duyệt 2026-09-27:* numpy 2.5 (dev set của `neuroedge`, và extra `wake`) khai `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` — Zlib giữ thông báo bản quyền, CC0-1.0 là hiến tặng phạm vi công cộng, cả hai không copyleft; đến qua pip, không đóng gói lại. **Hawkbit EPL-2.0: ĐÃ DUYỆT** (2026-09-25, CPO) — dùng nguyên bản làm dịch vụ Fleet OS; nếu sửa mã Hawkbit thì công bố phần sửa theo EPL-2.0; mã NeuroEdge chỉ nói chuyện qua API nên không bị ràng buộc. **EMQX BSL: KHÔNG DÙNG** — thay bằng broker MQTT giấy phép trong allowlist (Mosquitto theo EDL-1.0, NanoMQ MIT hoặc VerneMQ Apache-2.0), chọn bằng đo tải khi mở Khối 2. |
| **Q-12** | Chuẩn kết nối nhà cung cấp AI | **ĐÃ CHỐT** *(nới 2026-09-26)* | Chuẩn mặc định là **nền tảng tương thích OpenAI API** (chat completions cho LLM, `audio/transcriptions` và `audio/speech` cho ASR/TTS) và **endpoint quyết định có kiểu** cho System One (`POST /api/v1/systemone`, Q-4). Provider chưa tương thích kết nối qua adapter tự viết (FR-MDL-07→09). |
| **Q-13** | Phân tầng cam kết theo bậc target | **ĐÃ CHỐT** | Ba bậc: **bậc 1** (`sim`, `linux`, `esp32s3`) giữ toàn bộ cam kết; **bậc 2** do đội lõi bảo trì với cam kết hẹp hơn; **bậc 3** do cộng đồng port và tự kiểm chứng (FR-TGT-08). Nguyên tắc P-2 áp dụng ở mọi bậc. |
| **Q-14** | Hành vi khi mất mạng + fallback cục bộ | **ĐÃ CHỐT** *(2026-09-23)* | Mất mạng ⇒ gate **vẫn lượng giá** bằng bộ nhận diện **lệnh cố định** cục bộ (P0, FR-ACE-03, FR-MDL-03, R-6); chỉ BLOCK `gate_unreachable` khi fallback không chạy được. Backend cùng ngữ pháp: `sim` = khớp chữ gõ (A1, TSK-S2-08); `esp32s3` = ESP-SR MultiNet hoặc TFLite Micro / ESP-NN; `linux` = TFLite / KWS tương đương. |
| **Q-15** | Đầu vào mặc định của `sim` | **ĐÃ CHỐT** *(2026-09-23)* | Mặc định **gõ chữ** (CLI/UI) qua bộ khớp ngữ pháp lệnh (Q-14): không mạng, không key, tất định (FR-DX-02). Giọng nói là tuỳ chọn khi có key cloud. |
| **Q-16** | GPIO cho `linux` trong CI | **ĐÃ CHỐT** *(2026-09-23)* | CI dùng **`gpio-sim`** (kernel ≥ 5.19, configfs, job `linux-hal`, TSK-S3-05). HAL `linux` ném lỗi khi thiếu `/dev/gpiochip*`. RPi 5 dùng cho nightly phần cứng. |
| **Q-17** | Hành vi `on_block` ở v1.0 | **ĐÃ CHỐT** *(2026-09-23)* | Mọi `on_block` đều chặn hành động vật lý: `deny` chặn; `escalate`/`ask` chặn, ghi vết và gọi hook; `degrade` chặn hành động gốc và chạy `fallback_action` qua gate riêng. Xác nhận `ask` theo Q-26; người nhận `escalate` theo `TODOS.md` #20. Sửa bởi Q-72: chuyển cảnh báo tới kênh chat. |
| **Q-18** | Kế thừa `budget`/`on_block` | **ĐÃ CHỐT** *(2026-09-23, RFC-0004)* | Ngữ nghĩa kế thừa (RFC-0004, FR-GATE-06/07): (1) `p95_latency_ms` của con ≤ của cha; (2) chuỗi đã `closed` thì con cấm khai `fail: open`; (3) con không được thêm `fallback_action` mới, chỉ được đổi sang `deny`/`escalate`/`ask`. Vi phạm ném `GateInheritanceError` (TSK-S2-13). |
| **Q-19** | Lịch Sprint 2–3 | **ĐÃ CHỐT** *(2026-09-23)* | Đã bị thay bởi Q-39: roadmap chuyển sang đo bằng increment, mốc M1 neo theo ngày của I1. |
| **Q-20** | Cổng nhu cầu mềm | **ĐÃ CHỐT** *(2026-09-23)* | Đã bị thay bởi Q-56 và Q-72: cổng nhu cầu mềm 2026-10-25 được thay bằng cổng nhu cầu 8 tuần của Q-72. |
| **Q-21** | Mô phỏng theo tầng bằng OSS đã kiểm chứng | **ĐÃ CHỐT** *(2026-09-23, cùng kế hoạch lấp khoảng trống kỹ thuật)* | Không tự viết emulator, mỗi tầng dùng công cụ mở: `SimHAL` (logic), `gpio-sim` (GPIO `linux`), `sounddevice` (âm thanh CI), `i2c-stub` + `lm75`, LVGL host (`display`), mã C firmware biên dịch trên host (TSK-S4-07), Espressif QEMU cho boot `esp32s3` (TSK-S4-08); bo thật đo âm học và bộ nhớ. Không dùng Renode, Wokwi, `iio_simple_dummy`. Bổ sung bởi Q-69 và Q-72. |
| **Q-22** | AEC phần mềm trên `linux` | **ĐÃ CHỐT** *(2026-09-23, phương án A)* | `LinuxHAL` lấy `audio.in` đã khử vang qua PipeWire `libpipewire-module-echo-cancel` (`aec/libspa-aec-webrtc`). Module tạo 4 nút: `capture` → `source` (`audio.in`), `sink` (`audio.out`) → `playback`. `boards/linux-rpi5.toml` chỉ khai `aec = true` khi nightly trên Pi đạt tiêu chí (`docs/spec/simulation_coverage.md` §6). |
| **Q-23** | Định dạng cây quyết định trên MCU | **ĐÃ CHỐT** *(2026-09-23)* | **`neuroedge build` sinh cây thành bố cục nhị phân `NETR`** (RFC-0003); firmware duyệt trực tiếp, không nhúng parser JSON trên MCU. Bản v1.0 link dạng mảng `const` trong flash; cập nhật qua phân vùng flash riêng bằng `esp_partition_mmap`. Walker C99 tại `targets/esp32s3/components/ne_gate/`. |
| **Q-24** | Hành động là tool call · MCP | **ĐÃ CHỐT** *(2026-09-23)* | Mỗi `@action` là một **tool**; mọi nguồn (`local_grammar`, `system_one`, `system_two`, `mcp`) gửi cùng một `ToolCall` qua duy nhất `dispatch()` → `c.do()` → gate → token; dispatcher chèn `call_source`. SDK MCP qua extra `neuroedge[mcp]`. Đặc tả: Gated Tool Profile ([`docs/spec/tool_calling.md`](../docs/spec/tool_calling.md) §1–§5). |
| **Q-25** | Ràng buộc tham số của tool call | **ĐÃ CHỐT** *(2026-09-23; RFC-0005 chấp thuận 2026-09-24, không có `arguments_closed` ở v1)* | Ràng buộc tham số (khoảng, tập giá trị, độ dài) nằm **trong gate** (RFC-0005): kế thừa chỉ thu hẹp, `gate lint` chứng minh được và ánh xạ vào `inputSchema` cho mô hình. |
| **Q-26** | Ai xác nhận `on_block: ask` | **ĐÃ CHỐT** *(2026-09-23)* | Chỉ **người, qua kênh thiết bị** xác nhận được; `system_two` và `mcp` bị từ chối. Xác nhận làm gate lượng giá lại tiêu chí trong `on_block.confirms` (RFC-0006, [`docs/spec/tool_calling.md`](../docs/spec/tool_calling.md) §6). Sửa bởi Q-72: cho phép người duyệt qua kênh chat đã ghép đôi bằng bản ghi duyệt; LLM không bao giờ duyệt. |
| **Q-27** | NeuroEdge làm MCP client | **ĐÃ CHỐT** *(2026-09-23)* | System 2 là **MCP host**: tool thiết bị qua MCP server của agent (qua gate); MCP server bên ngoài chỉ lấy thông tin theo allowlist `[mcp.servers]`, kết quả là dữ liệu không tin cậy. MCU không làm host ([`docs/spec/tool_calling.md`](../docs/spec/tool_calling.md) §10). |
| **Q-28** | Mốc giao lớp trừu tượng provider (FR-GW) | **ĐÃ CHỐT** *(2026-09-24)* | FR-GW thuộc lõi: **v1.0 giao FR-GW-01 và FR-GW-03 tối thiểu** (bảng `[system_two]` trong `agent.toml`, key từ biến môi trường; failover trong mã). **v1.1 giao phần còn lại** (TSK-K2-01→03, FR-GW-02, 04 phía máy chủ, 05, 06, 07; client streaming MCU là TSK-S5-06). Lý do: v1.0 chạy cục bộ, phần cho đội thiết bị đi cùng Fleet OS. |
| **Q-29** | Định vị trước MHS (Anthropic) | **ĐÃ CHỐT** *(2026-09-24)* | **Theo dõi, không đầu tư ở v1.0** (trượt PF-3; [`TODOS.md`](../TODOS.md) #32–#33). Khi MHS mở mã nguồn và ổn định, hỗ trợ bằng adapter HAL host trên `linux` do cộng đồng/đối tác port; NeuroEdge định vị là tầng an toàn và kiểm thử trên thiết bị MHS. |
| **Q-30** | Định vị "Hợp đồng vào Physical AI" (engine-first) | **ĐÃ CHỐT** *(2026-09-24)* | Hợp đồng là lớp bảo vệ gần nhất trên 5 nguyên thủy HAL: không hợp đồng, không hành động; kiểm thử trong CI, chạy nhất quán mọi target. Sửa bởi Q-72: mở rộng thành nơi biến ý định thành sản phẩm vật lý có AI (dựng, chạy an toàn, chia sẻ và bán); hợp đồng thành lớp niềm tin. |
| **Q-31** | Tên và định vị NeuroBrain | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Đã bị thay bởi Q-71: bỏ tên NeuroBrain, năng lực gọi là NeuroEdge Lab qua MCP và định vị gộp vào Q-30. |
| **Q-32** | Hướng mở rộng cho robot phân tầng (FOFOCA) | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Mở rộng robot phân tầng sau Developer Beta, giữ nguyên đường găng v1.0: trace đa node mở rộng trường tuỳ chọn trong `trace.v1`, motor/servo là nguyên thủy `motion.*` riêng (Q-37), wire protocol theo Q-36, an toàn theo Q-38. |
| **Q-33** | Node RP2350 do đội lõi port | **ĐÃ CHỐT** *(2026-09-25, CPO)* | RP2350 là node tham chiếu thứ hai cho robot phân tầng sau Beta, do đội lõi port (HAL C trên Pico SDK, walker C99 ARM, test trên mạch thật). Bo tham chiếu v1.0 vẫn là ESP32-S3-Box-3 (Q-2). |
| **Q-34** | ROS 2 / Nav2 | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Tích hợp nguyên bản ROS 2 và Nav2 qua adapter tại ranh giới gate; gate xét mọi lệnh tốc độ kể cả khi Nav2 đang dẫn đường. Cần RFC riêng và kiểm chứng nhu cầu theo Q-38 trước khi thiết kế (`TODOS.md` #40). |
| **Q-35** | Trạng thái an toàn khi node mất liên lạc | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Mỗi cơ cấu tự khai trạng thái an toàn khi mất liên lạc với não (`safe_state`), không khai thì dừng (fail-closed); cần RFC khai báo (`board.v1`/`@action`). Sửa bởi Q-72: `safe_state` mở rộng cho mọi cơ cấu. |
| **Q-36** | Wire protocol giữa Pi và node MCU | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Dùng **Zenoh-pico** trên MCU và `zenohd` trên Pi (Apache-2.0). Phép thử loại trên mạch thật đo ba ngưỡng: độ trễ p99 ≤ 20 ms, SRAM nội ≤ 40 KB, tự nối lại ≤ 2 s; trượt mới xét micro-ROS. |
| **Q-37** | Token cho lệnh `motion.*` | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Lệnh `motion.*` dùng **token thuê có hạn (lease)**: kênh, biên độ tối đa và thời hạn ngắn (~200 ms). Hết hạn hoặc mất liên lạc thì cơ cấu tự về `safe_state` (Q-35); gate vẫn là hàm thuần, đếm hạn ở HAL/runtime. |
| **Q-38** | Chứng nhận an toàn chức năng (IEC 61508, ISO 13849, ISO 13482) | **ĐÃ CHỐT — tạm thời** *(2026-09-25, CPO)* | Tạm thời loại khỏi phạm vi: NeuroEdge **không** phải chức năng an toàn được chứng nhận (không SIL, không PL); bảo vệ nguy hiểm luôn do phần cứng (nút dừng khẩn, rơ-le, phao). Xem xét lại khi có dữ liệu phỏng vấn (`TODOS.md` #40). |
| **Q-39** | Roadmap theo increment và chính sách phát hành | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Roadmap duy nhất đo bằng **increment `I0…`** kèm điều kiện vào, bằng chứng ra và một ngày dự báo (roadmap §0.2). Không phát hành ra ngoài cho tới I6 (công khai PyPI, A9); riêng một đội đối tác nhận wheel trực tiếp (Q-70). Đóng băng tính năng Beta áp dụng cho dòng `1.0.x`. Nhân sự cập nhật bởi Q-60; thứ tự cập nhật bởi Q-72. |
| **Q-40** | Thứ tự các hướng mở rộng sau Beta | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Đã bị thay bởi Q-53, Q-55 và Q-71: thị giác vào v1.0 (Q-53), NeuroBrain thành NeuroEdge Lab (Q-55, Q-71); sau Beta còn mở rộng target (I11/I2c), port cộng đồng (I13) và robot (I14). |
| **Q-41** | Điều kiện mở v1.1 và B3 | **ĐÃ CHỐT** *(2026-09-25, CPO)* | v1.1 mở khi Beta đạt đồng thời **B1 và B2** (§3.3); B3 bỏ khỏi điều kiện mở (đo qua Registry ở v1.1 nên tránh phụ thuộc vòng), vẫn theo dõi để nối vào C5. |
| **Q-42** | C6 ở v1.1 | **ĐÃ CHỐT** *(2026-09-25, CPO)* | **C6 là chỉ số theo dõi**, không là điều kiện phát hành v1.1 (công bố khi đạt C1–C5, C7, C8). Lý do: hòa vốn cần hàng chục nghìn thiết bị nên không thể chặn phát hành kỹ thuật. Sửa bởi Q-72: theo dõi các dòng thu mới. |
| **Q-43** | Mốc kiểm chứng giả định G-a..G-e | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Mốc kiểm chứng giả định neo theo increment (§13.3): G-b khi I8 đóng (cùng B5); G-a và G-c đo 90 ngày sau I9; G-d đo 1 năm sau I10 (tín hiệu sớm B3); G-e đo 180 ngày sau ba site AURA. |
| **Q-44** | Bậc cắt 5 — tách thoại khỏi MCU | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Bỏ bậc cắt 5: thoại trên ESP32-S3 là bắt buộc cho v1.0, giữ A6. Nếu trượt ngưỡng Q-3 thì dời lịch I5 (TSK-S5-05, TSK-S5-07) chứ không cắt phạm vi. Sửa bởi Q-72: tạm dừng thoại để ưu tiên Blueprint bể cá, không cắt. |
| **Q-45** | Giấy phép của NeuroEdge và kho công khai | **ĐÃ CHỐT** *(2026-09-25, CPO)* | **Mã lõi theo PolyForm Noncommercial 1.0.0**, chuẩn giữ mở theo **Apache-2.0** (`schemas/`, `docs/spec/`, `fixtures/compliance/`, `LICENSING.md`). Cá nhân phi thương mại dùng miễn phí; thương mại cần license của NeuroEdge (`TODOS.md` #44). Đóng góp ngoài cần CLA (`TODOS.md` #43). Kho công khai toàn bộ từ 2026-09-25; PyPI mở ở I6. Sửa bởi Q-72: PolyForm NC là cơ chế thu tiền khi bán Blueprint hoặc thiết bị. |
| **Q-46** | Câu "có"/"không" nói ra trả lời câu hỏi nào | **ĐÃ CHỐT** *(2026-09-26)* | Câu trả lời thoại chỉ xác nhận câu hỏi `ask` của chính lượt đó (đang mở hoặc cắt lời khi đang đọc); không áp dụng cho lượt trước. TTS đọc lỗi thì về IDLE, không mở xác nhận (`docs/spec/voice_fsm.md`, RFC-0006). Lý do: tránh ảo giác STT hoặc trả lời nhầm câu hỏi. |
| **Q-47** | FastAPI WebSockets trong Fleet OS dùng cho gì | **ĐÃ CHỐT** *(2026-09-28)* | FastAPI WebSockets trong Fleet OS **chỉ dùng cho kết nối và viễn trắc**; âm thanh không qua Fleet OS mà đi thẳng tới lớp provider lõi (FR-GW-04). Lý do: bảo vệ quyền riêng tư (NFR-PRIV-03) và NeuroEdge không đứng giữa luồng token (N4). |
| **Q-48** | Máy trạng thái hội thoại thuộc tầng nào | **ĐÃ CHỐT** *(2026-09-28)* | Máy trạng thái hội thoại thuộc **L2 — Perception & runtime hội thoại** (`docs/spec/voice_fsm.md`), chạy thời gian thực trên cả chip lẫn host với cùng vector tuân thủ, không lượng giá gate và không lái chân trực tiếp. |
| **Q-49** | Mỗi increment ra kèm một demo | **ĐÃ CHỐT** *(2026-09-29)* | Mỗi increment bắt buộc kèm một demo chạy được trong `demo/<increment>/` (roadmap §11.1, `demo/README.md`), kiểm chứng bằng review trước khi đánh dấu hoàn thành. Lý do: bảo đảm tính kiểm chứng độc lập khi chưa có phần cứng. |
| **Q-50** | Phiên thoại thời gian thực trên máy tính, trước khi có Pi | **ĐÃ CHỐT** *(2026-09-29)* | Hỗ trợ thoại thời gian thực trên `sim` qua `neuroedge run --mic` (TSK-I4-04): tai nghe cho full-duplex (cắt lời được); loa ngoài dùng `--half-duplex` (không cắt lời). Pi giữ AEC PipeWire; wake-word demo chỉ thử nội bộ (`TODOS.md` #49). |
| **Q-51** | Giao diện của milestone: NeuroEdge Studio | **ĐÃ CHỐT** *(2026-09-29)* | Lệnh `neuroedge studio` mở web UI cục bộ đa màn hình trên 127.0.0.1 (TSK-I1-04, `docs/spec/studio.md`), bảo đảm an toàn: không tài nguyên ngoài, không lộ key. Sửa bởi Q-72: tạm dừng cùng thoại. |
| **Q-52** | MVP = v1.0 đầy đủ, bốn phase | **ĐÃ CHỐT** *(2026-09-30, chủ sản phẩm)* | MVP là v1.0 đầy đủ (năm nguyên thủy lõi + bốn gói mở rộng Q-53 trên ba target, nghiệm thu A1–A12), trượt thì dời ngày có bằng chứng chứ không cắt phạm vi. Nhân sự thay bởi Q-60. Sửa bởi Q-72: không cắt phạm vi nhưng đổi thứ tự, đưa Blueprint bể cá (I2d, I2e) lên trước, phạm vi v1.0 xét lại ở cổng 8 tuần. |
| **Q-53** | Bốn gói nguyên thủy mở rộng trên ba target | **ĐÃ CHỐT** *(2026-09-30, chủ sản phẩm)* | Bốn gói nguyên thủy mở rộng vào v1.0 trên cả ba target bậc 1 (RFC-0007, RFC-0009→0013): cảm biến, PWM, thị giác (`vision.in`), chuyển động (`motion.*`). Thêm bo ESP32-S3 có camera (Q-61) và profile `sim-rpi5`. Phong bì an toàn áp dụng chung cho mọi actuator. |
| **Q-54** | Thị giác trong gate | **ĐÃ CHỐT** *(2026-09-30, chủ sản phẩm)* | Dữ kiện thị giác do maker tự định nghĩa từ nhãn model; gate khoá ngưỡng tin cậy bằng tiêu chí `numeric` (RFC-0009), không có ngữ nghĩa gate riêng. Mất camera hoặc model thì dữ kiện chưa quyết và gate chặn; vết ghi chỉ lưu tham chiếu, không lưu ảnh thô (RFC-0012). |
| **Q-55** | NeuroBrain vào MVP | **ĐÃ CHỐT** *(2026-09-30, chủ sản phẩm)* | Đã bị thay bởi Q-71: chuyển thành NeuroEdge Lab qua MCP, giữ nguyên phạm vi bốn gói nguyên thủy nhưng không tự chạy LLM. |
| **Q-56** | Bỏ luật cổng nhu cầu | **ĐÃ CHỐT** *(2026-09-30, chủ sản phẩm)* | Đã bị thay bởi Q-72: khôi phục cổng nhu cầu có hiệu lực đo sau khi chốt Q-72 8 tuần với ba tiêu chí B6, B7, B8. |
| **Q-57** | Câu hỏi mở của sáu RFC nguyên thủy mở rộng | **ĐÃ CHỐT** *(2026-09-30, chủ sản phẩm uỷ quyền, nguyên tắc an toàn cao nhất)* | Chốt các câu hỏi mở của RFC-0007, RFC-0009→0013 (§9 của từng RFC): I2C chỉ ghi con trỏ thanh ghi đã khai; phong bì có `max_continuous_ms` và `min_interval_ms`; tiêu chí `numeric` cần `range` và `max_age_ms`; PWM bắt buộc `enable_pin`; `motion.*` dừng khi cắt lời/BLOCK/mất liên lạc, lease 200 ms; thị giác `present` cần ≥ 2 khung liên tiếp. Sửa bởi Q-72: mở rộng `safe_state` phủ mọi cơ cấu qua RFC an toàn có điều kiện. |
| **Q-58** | Bề mặt tích hợp vào MVP | **ĐÃ CHỐT** *(2026-10-01, chủ sản phẩm)* | Hai hạng mục vào I6: (1) MCP qua mạng có xác thực Streamable HTTP + OAuth 2.1 + mTLS (TSK-P2-04, mặc định tắt); (2) đóng băng Gated Tool Profile vào `schemas/` qua RFC (TSK-I6-05). Lý do: cho phép hệ sinh thái ngoài tích hợp qua chuẩn mở Apache-2.0 an toàn. |
| **Q-59** | Giấy phép qua v1.0, mở sau | **ĐÃ CHỐT** *(2026-10-01, chủ sản phẩm)* | Giữ PolyForm Noncommercial cho mã nguồn qua v1.0; xem xét mở sau khi có dữ liệu Beta (`TODOS.md` #51). CLA bắt buộc cấp quyền tái cấp phép để mở trong tương lai (`TODOS.md` #43). Hệ sinh thái ngoài tích hợp qua chuẩn Apache-2.0 (Q-58). |
| **Q-60** | Mô hình vận hành: một người + AI agent | **ĐÃ CHỐT** *(2026-10-01, chủ sản phẩm)* | Mô hình vận hành là chủ sản phẩm kết hợp AI agent (thay nhân sự Q-52; V1→V7 là làn việc, không phải người). AI agent làm việc trên host; việc cần phần cứng, người ngoài hoặc chữ ký do người thực hiện với kịch bản chuẩn bị sẵn. |
| **Q-61** | Bo ESP32-S3 có camera | **ĐÃ CHỐT** *(2026-10-01, chủ sản phẩm)* | Chọn **M5Stack CoreS3** làm bo tham chiếu thứ hai cho `esp32s3` (Box-3 vẫn là mặc định). Bo đạt chuẩn RFC-0013: Flash 16 MB, PSRAM 8 MB, camera GC0308 VGA, dual-mic ES7210, loa AW88298, màn cảm ứng, I/O Grove/M5-Bus. Bác bỏ ESP32-S3-EYE (thiếu loa, flash hẹp) và Korvo-2 (rời rạc). |
| **Q-62** | Sửa sáu RFC nguyên thủy mở rộng theo review độc lập | **ĐÃ CHỐT** *(2026-10-01, chủ sản phẩm duyệt hướng sửa, nguyên tắc an toàn cao nhất như Q-57)* | Sửa sáu RFC nguyên thủy mở rộng (RFC-0007, RFC-0009→0013): lệnh về phía an toàn không bị gate/phong bì chặn; tự tắt bắt buộc tại `min(hạn, max_continuous_ms)`; phong bì ghi bền write-ahead; mọi chân `digital_out` mặc định là cơ cấu chấp hành trừ khi khai `signal_pins`; watchdog cho hẹn giờ an toàn; thị giác lượng giá từng khung rồi AND; `NETR` v2 ghim byte ở RFC-0009. Sửa bởi Q-72: "phía an toàn" theo `safe_state` trong `board.v1` (bắt buộc khoá liên động phần cứng nếu khác `off`). |
| **Q-63** | Khoảng hở nền tảng cho người tích hợp | **ĐÃ CHỐT** *(2026-10-02, chủ sản phẩm)* | Bổ sung ba hạng mục nền tảng vào I6: (1) định nghĩa bề mặt Python công khai `__all__` có SemVer (TSK-I6-06); (2) mở rộng RFC TSK-I6-05 khoá schema `board.v1` và danh mục mã lỗi; (3) viết RFC dữ kiện từ tiến trình ngoài (TSK-I6-07). Không phơi tool MCP quản trị qua mạng để tránh tấn công lặp (`TODOS.md` #29). |
| **Q-64** | Quy tắc ngừng hỗ trợ của API Python công khai | **ĐÃ CHỐT** *(2026-10-03, chủ sản phẩm)* | Quy tắc ngừng hỗ trợ (`docs/spec/python_api.md` §3, §5): tên công khai đánh dấu ngừng hỗ trợ ở bản MINOR, giữ qua một bản MINOR kèm `DeprecationWarning` trước khi bỏ ở bản MAJOR (trong `0.x` bản MINOR đóng vai MAJOR). Chốt hợp đồng CLI và ghim cây lệnh bằng `test_cli_contract.py`. |
| **Q-65** | Câu hỏi mở của RFC-0014 (dữ kiện từ tiến trình ngoài) | **ĐÃ CHỐT** *(2026-10-04, chủ sản phẩm; nguyên tắc an toàn cao nhất như Q-57)* | Chốt RFC-0014 ([RFC-0014](../docs/rfc/0014-du-kien-tu-tien-trinh-ngoai.md) §9): chỉ nhận dữ kiện từ tiến trình cùng máy qua Unix socket; `esp32s3` không nhận nguồn ngoài; chỉ hỗ trợ `numeric` (nhị phân biểu diễn 0/1); chỉ bật khi `agent.toml` có `[external]`. Mã hiện thực kéo vào I2c theo Q-67. |
| **Q-66** | Câu hỏi mở của RFC-0015 (hợp đồng cho người tích hợp) | **ĐÃ CHỐT** *(2026-10-04, chủ sản phẩm và kỹ thuật trưởng; nguyên tắc an toàn cao nhất như Q-57)* | Chốt RFC-0015 ([RFC-0015](../docs/rfc/0015-hop-dong-cho-nguoi-tich-hop.md) §10): `reason` là chuỗi mở, `status` quyết định phán quyết; đóng băng `tool-call.v1.json`, `tool-result.v1.json` và danh mục `schemas/error-codes.v1.json`; khoá `schema` bo mạch mặc định `v1`, phiên bản lạ bị từ chối; hoãn khoá bắt buộc hiểu cho `board.v1` (`TODOS.md` #58). |
| **Q-67** | Nền tảng mở: bên thứ ba tự nối NeuroEdge với sản phẩm mới mà không chờ đội lõi | **ĐÃ CHỐT** *(2026-10-04, chủ sản phẩm; kỹ thuật trưởng ký RFC-0002)* | Bên thứ ba tự nối với NeuroEdge mà không sửa lõi qua **increment I2c — Nền tảng mở** (M6, U7, A13, FR-EXT). Tám điểm: không gian tên `source` (`bridge:<id>`, RFC-0017); hiện thực RFC-0014 trong I2c; RFC-0002 và `--board <đường dẫn>` (RFC-0016); cơ cấu từ xa có mức tự tắt (RFC-0018); corpus tuân thủ sang Apache-2.0; SDK `neuroedge.sdk` có phiên bản riêng; runtime giữ PolyForm NC; plugin theo giấy phép tác giả. |
| **Q-68** | Câu hỏi mở của RFC-0016, RFC-0017, RFC-0018 (nền tảng mở) | **ĐÃ CHỐT** *(2026-10-04, kỹ thuật trưởng ký trên PR #99; nguyên tắc an toàn cao nhất như Q-57)* | Chốt §9 của RFC-0016, RFC-0017, RFC-0018: `neuroedge.guard` ổn định ngang `__all__`; bridge cấm chuyển lời xác nhận `ask` (`bridge:*` ngoài `HUMAN_SOURCES`); cơ cấu từ xa khai ở `agent.toml` và bắt buộc đọc lại cho hành động không hoàn tác; adapter Home Assistant ở kho riêng; chốt các hằng số an toàn tắt (`OFF_SLACK_MS` 100 ms, `OFF_RETRY_MS` 500 ms). |
| **Q-69** | Giả lập ngoại vi `esp32s3` và kernel đủ module cho `linux` trước khi bo mạch về (bổ sung Q-21) | **ĐÃ CHỐT** *(2026-10-05, chủ sản phẩm)* | Ba spike giả lập bổ sung Q-21: (1) `esp-emulator` (Espressif) cho GPIO/I2C/Wi-Fi `esp32s3` (TSK-I3-02); (2) `esp32sim` để ước lượng sớm bộ nhớ ESP-SR và chạy suy luận (TSK-I3-03); (3) kernel trong VM (virtme-ng) cho `linux-hal` có `pwmchip` và âm thanh thật, cộng runner ARM64 (TSK-I2a-08). Vẫn loại Wokwi và Renode; không thay thế đo trên phần cứng thật. |
| **Q-70** | Thử riêng với một đội đối tác trên thiết bị họ đang có, không chờ bo mạch (bổ sung Q-39; giữ Q-52) | **ĐÃ CHỐT** *(2026-10-09, chủ sản phẩm)* | Thử nghiệm riêng trước I6 với một đội đối tác trên thiết bị sẵn có qua `proxy mcp`, `proxy http`, `neuroedge.guard`, `sim` và Action CI (TSK-I2c-19). Phân phối wheel trực tiếp, không lên index, không chờ bo mạch. Loại trừ: `esp32s3`, thoại trên chip. Lý do: lấy phản hồi người dùng thực tế trước khi công khai. |
| **Q-71** | NeuroEdge Lab: dựng hợp đồng bằng AI người dùng đang có, qua MCP — thay NeuroBrain (thay Q-31; đổi cách hiện thực của Q-55; giữ phạm vi Q-52) | **ĐÃ CHỐT** *(2026-10-10, chủ sản phẩm)* | **NeuroEdge không tự chạy LLM để dựng hợp đồng** mà phơi năng lực lab thành tool MCP trung lập: client viết, NeuroEdge chấm và cưỡng chế, chỉ người khoá qua PR (thay Q-31, đổi cách hiện thực Q-55). Hai nhóm tool: tool tác động (`lab_pulse`, `lab_read`) qua gate và tool dựng (xem bo, kiểm bản nháp, replay) chỉ ghi thư mục agent. Cấm mọi tool khoá bản nháp hay sửa `digests.lock`. Tool MCP và Action CI (`neuroedge lab check`) dùng chung mã kiểm. Client có shell là bên gọi không tin cậy: tách quyền thiết bị (chỉ `mcp serve` giữ quyền), nạp chính sách từ nhánh đã duyệt. Restyle IBM Plex chờ mở rộng Q-11 (TSK-N0-06). Sửa bởi Q-72: Lab là vòng ① dựng hợp đồng nhiệm vụ. |
| **Q-72** | Định vị Blueprint: từ một câu nói tới một sản phẩm vật lý có AI — dựng, chạy an toàn, chia sẻ và bán (sửa Q-26, Q-30, Q-45, Q-62; đảo Q-56; đổi thứ tự Q-52; bổ sung Q-57, Q-71) | **ĐÃ CHỐT HƯỚNG** *(2026-10-11, chủ sản phẩm; RFC từng phần cần chữ ký kỹ thuật trưởng)* | **Định vị ba vòng:** ① **Dựng** — client MCP gợi ý kit, sinh firmware, chạy thử trên `sim`, nạp, nối chat (Q-71); ② **Chạy** — agent vận hành 24/7 thực thi hợp đồng nhiệm vụ nhiều thiết bị (được/cấm, tần suất, khung giờ, watchdog có cận, luồng dữ liệu, khi hỏng về `safe_state`, hết hạn), phản xạ MCU, bộ phát hiện tất định trước rồi mới gọi LLM, báo chủ động qua chat; ③ **Chia sẻ, bán** — NeuroEdge Blueprint (kit + firmware + hợp đồng mẫu + bộ phát hiện + bằng chứng), `blueprint pack`/`install`, Hub. Hợp đồng là lớp niềm tin. Người dùng đầu: maker cộng đồng HA/ESPHome (U1), rồi micro-OEM (U5); U2, U3 lùi xuống phụ. Blueprint đầu tiên: bể cá. LLM: người dùng tự trả (BYOK qua LiteLLM, có mô hình tại chỗ), có trần chi phí trong hợp đồng; chạm trần thì phản xạ và cảnh báo mẫu cứng vẫn chạy. Dòng tiền: PolyForm NC (Q-45) là cơ chế thu khi bán Blueprint hoặc thiết bị; hoa hồng kit (liên kết bán kit bể cá ở I2e), relay tuỳ chọn, giấy phép theo thiết bị, chia doanh thu Blueprint; không dòng thu nào nằm trên đường an toàn. Bốn điểm chốt: (1) người duyệt qua kênh chat (Telegram trước) bằng bản ghi duyệt một lần có hạn và digest, bản duyệt ≤ 5 dòng; nhóm chat và LLM không bao giờ duyệt; (2) bằng chứng MVP chưa ký (người cài tự replay, ký trước khi Hub thu tiền ở `TODOS.md` #1); (3) `safe_state` khác `off` chỉ khai trong `board.v1` kèm khoá liên động phần cứng, sửa `TODOS.md` #58 trước; (4) giả lập trước phần cứng thật mua sau qua 4 tầng G1–G4 (firmware ESP32 trên QEMU, Wokwi và Velxio chờ đối chiếu Q-21, Q-69). Cổng nhu cầu 8 tuần đo B6, B7, B8; trượt B8 thì giữ vòng ①② làm công cụ cá nhân. Thứ tự: hợp đồng nhiệm vụ, agent vận hành, kênh chat, Blueprint tối thiểu đi trước; thoại, Studio, `jetson` tạm dừng. Cần RFC: an toàn có điều kiện, `mission.v1`, `blueprint.v1`, luồng dữ liệu, nguồn `chat:<id>`. Hệ quả đã chấp nhận: rủi ro tài khoản chat bị chiếm, bằng chứng chưa ký, giới hạn giả lập, thêm hai vai quản trị (agent vận hành, Hub). |
| **Q-73** | Mở, có minh bạch: người dùng tự chọn cách xác minh và luồng nhiều bước (sửa Q-26, Q-15) | **ĐÃ CHỐT HƯỚNG** *(2026-10-12, chủ sản phẩm; RFC cần chữ ký kỹ thuật trưởng)* | NeuroEdge giúp người dùng dựng IoT, AIoT, Physical AI nhanh và **không quyết hộ họ cách xác minh hay luồng tương tác**. **Mở:** (1) *bước xác minh do người dùng khai* — đọc mã, giọng nói, khuôn mặt, bàn phím, thẻ, điện thoại… qua plugin bộ kiểm (Extension SDK); một bước xác minh đạt thì đặt dữ kiện người dùng khai (ví dụ `user_verified`), kể cả khi bằng chứng đến từ lời nói; (2) *luồng nhiều bước do người dùng viết* (đánh thức → yêu cầu → hỏi lại → xác minh → hành động); (3) NeuroEdge không cấm cách nào; gate vẫn nới được như hôm nay (`fail: open`, bỏ tiêu chí). **Minh bạch thay cho cấm:** mỗi cách xác minh mang mức rủi ro khai sẵn (ví dụ mã đọc to: nghe lén, phát lại được), hiện trong bản duyệt, trong `gate explain` và trong NeuroEdge Blueprint để người cài thấy trước. **Ba bất biến giữ lại** — bảo vệ người dùng khỏi người khác, không giới hạn lựa chọn của họ: (a) LLM, client MCP và nguồn tự động không bao giờ trả lời bước xác minh hay câu hỏi lại dành cho người (chống prompt injection; Q-26, FR-CH-05); (b) luật đã khai chạy đúng như khai, không đường vòng ngầm; (c) mọi bước xác minh và phán quyết ghi vào vết ghi (không ghi mã bí mật — chỉ đạt/trượt). **Cần RFC** (CONTRIBUTING §3, ngữ nghĩa xác nhận): kiểu bước xác minh trong `on_block`, giao diện plugin bộ kiểm, số lần thử và hạn, sự kiện vết ghi; việc theo dõi: TSK-I2d-20. **Lý do:** người dùng muốn tự quyết cách dùng thiết bị của mình; cấm hộ làm NeuroEdge khó dùng mà không thêm an toàn cho chính chủ. **Hệ quả đã chấp nhận:** người dùng chọn cách yếu (mã đọc to) thì chịu rủi ro đã được hiện rõ; NeuroEdge không chặn. |
| **Q-74** | Não trên cloud tuỳ chọn, tuỷ sống tại nhà: "đấu vào chat là có agent" (sửa hệ quả "không máy chủ" của Q-10 và N4 ở bước 2; bổ sung Q-72) | **ĐÃ CHỐT HƯỚNG** *(2026-10-12, chủ sản phẩm; bước 2 chờ số đo cổng nhu cầu)* | Người dùng không phải tự host agent (OpenClaw hay máy chủ riêng) mà vẫn có agent trông nhà chỉ bằng chat. **Chia đôi theo ranh giới sẵn có của Q-72:** *não* (LLM worker, trò chuyện, lập kế hoạch, biên dịch hợp đồng nhiệm vụ) được phép chạy trên **NeuroEdge Cloud tuỳ chọn**; *tuỷ sống* (gate, phản xạ, kiểm bản ghi duyệt, cửa ra dữ liệu, vết ghi) **luôn ở nhà**. Hộp tại nhà mở kết nối ra, không mở cổng; mất mạng thì an toàn vẫn chạy; cloud bị chiếm thì hộp vẫn chỉ thi hành luật đã ký và lời duyệt đã kiểm tại chỗ. **Hai bậc hộp tại nhà:** *đầy đủ* — Pi hoặc add-on Home Assistant (camera, nhiều hãng, nhật ký 30 ngày, LLM tại chỗ tuỳ chọn); *nhỏ* — ESP32-S3 cho một việc cụ thể (walker `NETR`, sổ token, phản xạ, kiểm lời duyệt trên chip; luật biên dịch ở cloud, nhận có ký; nhật ký đẩy lên cloud mã hoá hoặc thẻ SD). **Hai bước:** (1) ngay — I2d như kế hoạch (runtime và Telegram tại máy nhà) cộng hộp tại nhà dễ cài (add-on Home Assistant, ảnh thẻ SD cho Pi, ghép đôi bằng QR), TSK-I2e-12, TSK-I2e-13; (2) sau cổng nhu cầu 2026-12-06 và chỉ khi số đo cho thấy người thử vướng ở cài đặt, khoá API hay tự host — mở NeuroEdge Cloud có thuê bao (lúc đó sửa N4: NeuroEdge trả token trong gói, BYOK vẫn giữ) và bậc ESP32 — increment I2f (roadmap §4.3.6). **Lý do:** người dùng muốn "đấu vào chat là có"; ranh giới runtime tin cậy / LLM worker không tin cậy của Q-72 cho phép dời worker lên cloud mà không dời quyền phần cứng; thuê bao là dòng tiền rõ nhất. **Mạng lưới đa nút, đa nhà, đa người:** một ô chat điều phối nhiều ESP32, nhiều Pi, nhiều nhà và nhiều người; bốn nguyên tắc: (a) mỗi nút chỉ thi hành luật có chữ ký, lời duyệt kiểm tại nút; (b) việc không hoàn tác ở bất kỳ nhà nào luôn cần người xác nhận; (c) trần phạm vi và tốc độ cho một lệnh, bất thường thì tự khoá; (d) mỗi nút một danh tính, một vết ghi. Vai trò theo người: TSK-I2f-05. **Hệ quả đã chấp nhận:** vận hành dịch vụ cloud 24/7 có đường gửi lệnh vào nhà người dùng (bảo mật, chi phí token, trực sự cố) với đội một người + AI; ảnh và dữ liệu lên cloud khi người dùng khai đích đó (FR-EGR). |
| **Q-75** | Bằng chứng thực địa: "host nghĩ, ESP32 làm" — liên kết Pi ↔ ESP32 sớm, bo phổ thông, khung dự án nhiều chip, chưa làm quản lý đội thiết bị (bổ sung Q-35, Q-40, Q-74) | **ĐÃ CHỐT** *(2026-10-12, chủ sản phẩm)* | **Bằng chứng:** hai bài Reddit đọc 2026-10-12. (1) r/robotics, robot phun thuốc diệt cỏ SprayShark: Pi 5 gửi lệnh chữ qua USB serial tới ESP32-S3; bơm bật bằng relay; mất kết nối thì xe dừng nhưng bơm không tắt; không có watchdog; repo lộn xộn sau ba lần làm lại phần cứng; bo Freenove WROOM với Arduino, không phải Box-3. (2) r/IOT, khoảng 20 Pi 5 + Hailo cho nuôi thủy sản: chỉ suy luận, không cơ cấu; nỗi đau là OTA, giám sát, nguồn chập chờn, thẻ SD; đã xem Balena, Mender và thấy quá nặng; mạng khách hàng chỉ cho kết nối ra qua HTTPS. **Bốn quyết định:** (a) **liên kết host ↔ MCU tối thiểu lên I3a** — RFC node một host, một MCU qua serial, nhịp tim, mất liên lạc ⇒ `safe_state` tại MCU (TSK-I3a-06, TSK-I3a-07); bản nhiều node, black channel vẫn ở I14 (TSK-W3-02); (b) **bo ESP32-S3 phổ thông và Arduino** — DevKitC/WROOM là bo maker dùng thật (TSK-I3a-08, TSK-I3a-09); (c) **khung dự án nhiều chip** — `neuroedge new --layout host+mcu` trả lời câu "tổ chức dự án Pi + ESP32 thế nào", Blueprint đóng gói từ khung này (TSK-I2e-14); (d) **không làm quản lý đội thiết bị** (OTA, giám sát, cấp nguồn lại), kể cả tích hợp, trước khi người dùng thật đòi; I9 giữ nguyên chỗ. **Lý do:** người làm thật đã tự chia việc đúng như vỏ não / tuỷ sống nhưng tự chế giao thức và quên phản xạ mất liên lạc — đúng chỗ NeuroEdge có giá trị; hạm đội chỉ suy luận thì NeuroEdge không thêm gì. Ràng buộc "chỉ kết nối ra" của khách hàng xác nhận thiết kế kênh của Q-74. **Hệ quả đã chấp nhận:** I3a thêm bốn task, cần mua bo DevKitC; thư viện Arduino là bề mặt thứ hai phải giữ tương đương target (FR-TGT-04). |
| **Q-76** | Bộ não NeuroEdge: một worker siêu nhẹ kiểu PicoClaw, tự host trên board rẻ hoặc dùng NeuroEdge Cloud, mỗi người một instance cách ly (bổ sung Q-72, Q-74) | **ĐÃ CHỐT HƯỚNG** *(2026-10-12, chủ sản phẩm)* | **Bộ não NeuroEdge** là LLM worker của Q-72: trò chuyện qua kênh chat, gọi LLM, trí nhớ dạng tệp đọc được, lịch và heartbeat, biến lời nói thành *đề xuất*. Nó **không tin cậy** và chạm thế giới **chỉ qua MCP** tới runtime tin cậy tại nhà; không có `exec`, công cụ phần cứng hay tệp ngoài vùng của nó. **Một phần mềm, hai cách chạy:** (1) **tự host** — trên board Linux rẻ (khoảng $10, chục MB RAM) hoặc cùng Pi, add-on Home Assistant với runtime, dưới một user hệ điều hành riêng không có quyền phần cứng; (2) **NeuroEdge Cloud** — cùng phần mềm đó, NeuroEdge vận hành hộ: cổng kênh chat dùng chung chỉ định tuyến, mỗi người một instance cách ly (microVM), ngủ khi không có tin nhắn, trí nhớ mã hoá riêng; hộp tại nhà mở kết nối ra tới đúng instance của mình. Cloud vì vậy là *tiện lợi* (không phải cài), không phải *năng lực riêng*. **Nền mã:** bản rút gọn của PicoClaw (MIT): giữ kênh chat, nhà cung cấp LLM, trí nhớ, cron, heartbeat, MCP client; bỏ `exec`, `i2c`/`spi`/`serial`, công cụ tệp. Worker khác (PicoClaw gốc, Claude Desktop, OpenClaw) vẫn dùng được qua cùng bộ tool MCP. Trên ESP32, "não" là bậc nhỏ của Q-74 (kiểu zclaw, walker nhúng cùng chip), không phải bộ não này. **Lời duyệt không đi qua não:** việc không hoàn tác được duyệt bằng chữ ký trên điện thoại (passkey, mở từ nút trong chat) mà hộp tại nhà tự kiểm, hoặc duyệt tại chỗ trong mạng nhà; mỗi cách mang nhãn rủi ro (Q-73). Cổng kênh chung của cloud chuyển tin nhưng **không giả được** lời duyệt (FR-CH-08). **Lý do:** bộ não đã là hàng hoá (họ OpenClaw, PicoClaw, zclaw, ESP-Claw); tự viết hai bản (tại nhà và cloud) là trùng công. Một phần mềm cho cả hai giữ lựa chọn tự host miễn phí và để thuê bao trả cho sự tiện lợi, nhiều nhà, nhiều người, bot duyệt được quản lý. **Hệ quả đã chấp nhận:** phụ thuộc một fork phải tự theo dõi bản gốc (PicoClaw ghi chưa dùng cho production trước v1.0) và rà soát bảo mật trước khi host cho người khác (TSK-I2f-06); cần nghĩa vụ ghi nhận nguồn MIT (roadmap §3.9); phần mềm chạy nhiều người (cổng kênh, relay, microVM) là việc vận hành mới cho đội một người + AI. Việc: TSK-I2d-22 → TSK-I2d-24, TSK-I2f-02, TSK-I2f-07 → TSK-I2f-09. |
| **Q-77** | Gọn roadmap: bỏ thoại, NeuroEdge Lab, mở danh sách target và mọi increment sau Beta (đảo một phần Q-44, Q-52, Q-55; thay Q-40) | **ĐÃ CHỐT** *(2026-10-12, chủ sản phẩm)* | Roadmap còn khoảng 197 task chưa xong cho một người + AI, phần lớn không phục vụ hướng hiện tại (maker và nhà ở, ra lệnh qua chat, bộ não là hàng hoá, tuỷ sống ở nhà, Blueprint — Q-72, Q-74, Q-76). **Bỏ khỏi roadmap:** thoại I4, I5 (mã thoại trên host giữ nguyên); NeuroEdge Lab I4a, I5a (bộ tool MCP chuẩn TSK-I2d-23 thay vòng ①); mở danh sách target cho bên thứ ba (V1a, TSK-I2c-13, I2c-17); I9 provider tự host và Fleet OS (khớp Q-75); I10 Registry; I13 bộ port cộng đồng; I14 robot phân tầng; I16 Jetson; I17 đa phương thức; I18 hệ sinh thái thiết bị; Khối 4, Khối 5. Task của chúng còn một dòng mỗi task ở roadmap §6 để mã và tài liệu tra được; mỗi mục có mốc mở lại. **MVP v1.0 sau Q-77:** `sim`, `linux`, `esp32s3`; bốn gói nguyên thủy mở rộng; kit mẫu; nền tảng mở; nhiệm vụ 24/7 qua chat, bộ não qua MCP, Blueprint; OTA có ký. A6 đo 24 giờ không thoại; A11 bỏ cùng Lab. **Lý do:** tập trung vào thứ đem đi đo ở cổng nhu cầu 2026-12-06; mọi thứ bỏ đều đảo lại được bằng một `Q-N` mới kèm số đo. **Hệ quả đã chấp nhận:** mất demo "nói chuyện với con chip $5" và vòng dựng hợp đồng riêng của Lab; NeuroEdge không còn kế hoạch cho robot, Jetson hay dịch vụ đội thiết bị. |
| **Q-78** | NeuroClaw: bộ não NeuroEdge là một fork cứng của PicoClaw, repo riêng MIT (cụ thể hoá Q-76) | **ĐÃ CHỐT** *(2026-10-13, chủ sản phẩm)* | Demo chat đèn và cửa (2026-10-13) cho thấy ba chỗ PicoClaw gốc không hợp vai bộ não: client MCP không trình được chứng chỉ client nên phải có cầu nối mTLS; "tắt shell" chỉ là cấu hình, lật lại được qua cron (`allow_command` mặc định bật), hook tiến trình hoặc biến môi trường `PICOCLAW_TOOLS_*`; và câu hỏi `ask` của hộp chỉ là một kết quả tool bình thường. **Chốt:** fork cứng PicoClaw v0.3.1 thành **NeuroClaw**, repo riêng [`letrongminh/neuroclaw`](https://github.com/letrongminh/neuroclaw), giấy phép MIT như gốc (mã của PicoClaw buộc giữ MIT; MIT cũng để cộng đồng dùng và đóng góp). Ba bản vá: (1) mTLS cho MCP qua HTTP (`tls.ca_file`, `cert_file`, `key_file`), bỏ cầu nối; (2) khoá cứng: `exec`, i2c, spi, serial, cài skill, lệnh trong cron, hook tiến trình, theo dõi USB, registry skill và MCP stdio luôn tắt, cấu hình hay biến môi trường đều không bật lại được; (3) `BLOCK` kèm `confirmation` được nói rõ với LLM: chưa làm, chỉ chủ nhà ở nhà duyệt được, không gọi lại. Bỏ web console. **Đánh đổi đã chấp nhận:** tự gánh bảo trì, không nhận tự động bản sửa của PicoClaw (fork cứng, không theo upstream); tên NeuroClaw đã có người dùng (một báo cáo arXiv 2026 về thần kinh học, một nhóm tích hợp OpenClaw, vài repo nhỏ), chưa tra nhãn hiệu. **Không đổi:** Q-76 (một phần mềm, hai cách chạy; bộ não chỉ chạm thế giới qua MCP); worker khác (PicoClaw gốc, Claude Desktop) vẫn cắm được qua `cau-noi.py`. Việc: TSK-I2d-22; FR-AGT-12; demo `demo/i2f-chat-den-cua/`. |

---

# Phụ lục

## Phụ lục A — Ma trận truy vết yêu cầu

### A.1 Đối chiếu mục tiêu sản phẩm

Đối chiếu từ mục tiêu sản phẩm tới yêu cầu và tiêu chí nghiệm thu.

| Mục tiêu | Yêu cầu chi phối | Chỉ số | Tiêu chí nghiệm thu |
|:---|:---|:---|:---|
| **M1** — TTFV dưới 10 phút | FR-DX-01, FR-DX-02, FR-TGT-01, FR-TGT-06, FR-CLI-01 | TTFV trung vị | A1 |
| **M2** — Mọi hành động qua hợp đồng | FR-ACE-01→10, FR-MDL-10→12, FR-GATE-01→10, FR-HAL-07, FR-CLI-12 | Số đường tắt tới actuator | A3, A4, A5 |
| **M3** — Nhất quán các môi trường bậc 1 | FR-TGT-01→05, FR-CI-07, FR-HAL-06 | Kết quả `neuroedge verify` | A2 |
| **M4** — Tái hiện sự cố hiện trường | FR-CI-01, FR-CI-02, FR-TRC-01→08, FR-FLT-05 | Thời gian từ sự cố tới tái hiện | A7, C7 |
| **M5** — Cập nhật quy mô lớn an toàn | FR-OTA-01→04, FR-FLT-02 | Số thiết bị brick | C1 |
| **M6** — Bên thứ ba tự nối mà không sửa lõi | FR-EXT-01→09 | Thời gian viết bridge; số lệnh che MCP server | A13 |
| **M7** — Một câu nói thành thiết bị có hợp đồng | FR-MSN-01→14, FR-DX-09, FR-DX-10, FR-CLI-15 | Tỷ lệ hợp đồng mâu thuẫn bị bắt; lệnh vi phạm bị chặn | A15, A17, A21 |
| **M8** — Agent vận hành chủ động, có trần chi phí | FR-AGT-01→09, FR-CH-01→05, FR-EGR-01→05, FR-TRC-11→13 | Chi phí LLM 30 ngày; phát hiện xu hướng đúng | A16, A18, A19, A20, A22 |
| **M9** — Blueprint cài được, có người muốn bán | FR-BP-01→10, FR-CLI-13 | Thời gian cài trên máy sạch; số maker muốn bán | A14, B6, B7, B8 |

### A.2 Đối chiếu nguyên tắc bất biến

| Nguyên tắc | Yêu cầu hiện thực hóa | Yêu cầu kiểm chứng |
|:---|:---|:---|
| **P-1** Hợp đồng chuẩn kiểu | FR-ACE-01, FR-ACE-02, FR-ACE-03, FR-ACE-08→10, FR-MDL-10→12, FR-HAL-07, FR-CH-02, FR-AGT-02 | A3, A20, A21 |
| **P-2** Các môi trường ngang hàng | FR-TGT-01→05, FR-TGT-08 | A2 *(ràng buộc ở bậc 1)* |
| **P-3** Giá trị ở người tạo sản phẩm *(Q-72)* | FR-OTA-04, FR-BP-07, FR-BP-08, FR-BP-10, NFR-COMP-02, NFR-COMP-03 | Rà soát ranh giới §6.4 tài liệu nguồn và §8.4 của tài liệu này; C6 |
| **P-4** Mô hình thay thế được — cloud-first, provider-pluggable | FR-MDL-01→04, FR-MDL-07→09, FR-PER-07, FR-GW-01→07 | Bài kiểm thử đổi mô hình và đổi provider STT/TTS chỉ bằng cấu hình, không sửa mã agent |
| **P-5** Hiệu ứng mạng từ chia sẻ gate, thành phần mở rộng và NeuroEdge Blueprint | FR-GATE-05→08, FR-REG-01, FR-REG-04, FR-REG-08, FR-BP-01→05, FR-BP-09 | B3, B6, B8, C5 |

### A.3 Đối chiếu yêu cầu phi chức năng

Yêu cầu phi chức năng **không được truy vết qua task roadmap** mà qua tiêu chí nghiệm thu và rà soát định kỳ — vì chúng là thuộc tính xuyên suốt của hệ thống, không phải hạng mục công việc rời. Bảng này là đường nối duy nhất giữa NFR và bằng chứng kiểm chứng.

| Nhóm | Yêu cầu | Cách kiểm chứng | Tiêu chí nghiệm thu |
|:---|:---|:---|:---:|
| **NFR-PERF** | 01→03, 05, 07 | Đo trên lưu lượng thực, tách theo nhóm tác vụ | C2, C3, C4 |
| **NFR-PERF** | 04 | Đo độ trễ quyết định `SystemOne` qua FR-TEL-06 | C8 |
| **NFR-PERF** | 06 | Đo thời gian chạy bộ Action CI của dự án mẫu trong CI | — *(chỉ số nội bộ)* |
| **NFR-RES** | 01 | Kiểm thử chịu tải 24 giờ trên bo mạch tham chiếu | A6 |
| **NFR-RES** | 02, 03 | Đo bộ nhớ và kích thước firmware trong CI; ngưỡng chốt tại Q-3 | A6 |
| **NFR-RES** | 04 | Bộ kịch bản suy giảm: mất mạng, timeout, dữ liệu mô hình không hợp lệ | A4 |
| **NFR-REL** | 01 | Chiến dịch OTA canary trên 1.000 thiết bị | C1 |
| **NFR-REL** | 02 | Bộ kịch bản suy giảm — trùng cơ chế với NFR-RES-04 | A4 |
| **NFR-REL** | 03 | Nhật ký kiểm thử hằng đêm trên bo mạch thật | A2 |
| **NFR-REL** | 04 | Chạy lại bộ vết ghi hồi quy sau mỗi lần nâng phiên bản phụ | A7 |
| **NFR-REL** | 05, 06 | Kịch bản G1 mất mạng, mất LLM, worker chết; chạy liên tục 2 tuần trên G2 hoặc G3 | A16, B7 |
| **NFR-SEC** | 01 | Rà soát mã và kiểm thử thâm nhập tìm đường tắt tới actuator | A3 |
| **NFR-SEC** | 02, 03 | Rà soát cấu hình Secure Boot, mã hóa flash, TPM và nút ngắt micro trên bo mạch tham chiếu | **cần tiêu chí** *(chưa có tiêu chí mốc A/C nào đo được)* |
| **NFR-SEC** | 06 | Nạp firmware không chữ ký hoặc sai chữ ký → bị từ chối | Tiêu chí của FR-OTA-03 · **cần tiêu chí mốc** |
| **NFR-SEC** | 04, 05 | Rà soát TLS 1.3, mTLS, certificate pinning và chứng chỉ riêng từng thiết bị (gắn FR-FLT-01, v1.1) | **cần tiêu chí** |
| **NFR-SEC** | 08 | Rà soát kênh TLS 1.3 tới provider; kiểm provider được ghi trong vết ghi | **cần tiêu chí** *(provider nằm trong dữ liệu sự kiện `system_two_call`; `trace.v1.json` không có trường provider riêng)* |
| **NFR-SEC** | 07 | Kiểm thử sandbox với mã bên thứ ba | — *(v1.1, gắn FR-REG-07)* |
| **NFR-SEC** | 09 | Test bên gọi không tin cậy (`docs/spec/threat_model.md` §2b) và corpus `fixtures/tool_calls/` | A3 |
| **NFR-SEC** | 11, 12, 13 | Kịch bản đích không khai, mạng của worker, bộ kịch bản duyệt chat; rà soát nơi giữ key và token bot | A18, A20 |
| **NFR-SEC** | 14 | Cài gói lệch digest, gói khai `safe_state` sai chỗ | A14, A21 |
| **NFR-SEC** | 15 | Rà soát thiết kế relay: không giải mã, sao lưu mã hoá | **cần tiêu chí** *(relay P1, chưa có tiêu chí mốc)* |
| **NFR-PRIV** | 01, 03, 04 | Rà soát nội dung tệp vết ghi sinh ra ở chế độ mặc định | A7 |
| **NFR-PRIV** | 02 | Rà soát ranh giới xử lý on-device và cloud theo P-4 | — *(rà soát kiến trúc)* |
| **NFR-PRIV** | 05 | Rà soát đích chia sẻ dữ liệu mặc định tắt | — *(P2, sau cổng 8 tuần)* |
| **NFR-OBS** | 01→03 | Thẩm định tệp vết ghi bằng `neuroedge trace validate` | A7 |
| **NFR-OBS** | 04 | Đo cỡ vết ghi 30 ngày trên G1; kịch bản mất điện giữa đoạn | A22 |
| **NFR-COST** | 01, 02 | Kịch bản 30 ngày trên G1, đếm chi phí và tin theo loại | A19 |
| **NFR-COMP** | 01→04 | Rà soát ranh giới giữa lõi và dịch vụ thương mại (`docs/architecture/vi/15-target-architecture.md` §3.4) | A9 |
| **NFR-COMP** | 05, 06 | Ma trận nền tảng chạy trong CI | A2 |

### A.4 Đối chiếu các nhóm yêu cầu chức năng còn lại

A.1 truy vết theo **mục tiêu sản phẩm**, A.2 theo **nguyên tắc bất biến**. Một số nhóm yêu cầu chức năng không rơi vào hai trục đó nhưng vẫn phải có đường kiểm chứng; bảng này đóng phần còn lại.

| Nhóm | Yêu cầu | Vai trò | Tiêu chí nghiệm thu |
|:---|:---|:---|:---:|
| **FR-HAL** | 01→05 | Hợp đồng năng lực và đối chiếu lúc build | A2, A3 |
| **FR-PER** | 01→06 | Chuỗi xử lý giọng nói và máy trạng thái hội thoại | A6, C2 |
| **FR-CI** | 03→06 | Thư viện assert, mẫu chuẩn, chạy trong CI, nightly | A2, A7 |
| **FR-CI-LVL** | L1→L3 | Ba cấp độ đảm bảo: L1 replay chuẩn xác, L2 khớp schema + `confidence`, L3 chỉ assert phán quyết gate và GPIO | A2 *(L1, L2)* · lint FR-DX-07 *(L3)* |
| **FR-TRC** | 09, 10 | Quy ước đường dẫn vết ghi; đăng ký SchemaStore | A7 · A9 *(10)* |
| **FR-GOV** | 01→04 | Quản trị lược đồ mở và quy trình RFC | A9 |
| **FR-CLI** | 02→08 | Bề mặt dòng lệnh | A1, A8 |
| **FR-CLI** | 09→12 | `gate lint`, `gate resolve`, `board`, `mcp` | A5 *(09, 10)* · A2 *(11)* · A3 *(12)* |
| **FR-DX** | 03→07 | Khuôn mẫu dự án, ví dụ mẫu, thông báo lỗi | A1, A8 |
| **FR-EXT** | 01→09 | Lõi dùng độc lập, điểm cắm, tuân thủ, proxy, cơ cấu từ xa, phân phối | A13, A3 |
| **FR-TGT** | 07 | Mô phỏng kịch bản suy giảm trong `sim`; kịch bản nhiệm vụ nhiều ngày có mô hình vật lý (Q-72) | A4, A16, A19 |
| **FR-MDL** | 05, 06 | Định tuyến khai báo và ghi nhận tỷ lệ S1/S2 | C4 |
| **FR-FLT** | 01, 03, 04, 06 | Provisioning, giám sát, cấu hình từ xa, thiết bị ảo | C1, roadmap TR-7 |
| **FR-REG** | 02, 03, 05, 06 | Manifest, khai báo năng lực, định danh, đo lường | C5, roadmap TR-4, TR-5 |
| **FR-REG** | 07 | Phân quyền và sandbox cho mã bên thứ ba | — *(v1.1, kiểm qua NFR-SEC-07)* |
| **FR-TEL** | 01→06 | Viễn trắc và đo đạc | B4, B5, §12.2 của tài liệu này |
| **FR-TEL** | 07, 08 | Mốc của cổng 8 tuần; báo cáo liên kết kit | B6, B7, C6 |
| **FR-MSN** | 01→14 | Hợp đồng nhiệm vụ: điều khoản, biên dịch theo tầng, mâu thuẫn, bản duyệt | A15, A17, A21 |
| **FR-AGT** | 01→09 | Agent vận hành: runtime, LLM worker, lập lịch, bộ phát hiện, trần chi phí, nhánh lỗi | A16, A19 |
| **FR-CH** | 01→05 | Kênh chat, ghép đôi, bản ghi duyệt | A20 |
| **FR-EGR** | 01→05 | Luồng dữ liệu chống rò rỉ, relay | A18 · relay: **cần tiêu chí** |
| **FR-BP** | 01→07 | NeuroEdge Blueprint, pack/install, bằng chứng, index tĩnh, kit | A14, A21, A22 |
| **FR-BP** | 08→10 | Giấy phép, dữ liệu có đồng ý, Hub thu phí | — *(sau cổng 8 tuần)* |
| **FR-TRC** | 11→13 | Vết ghi theo đoạn, ghi và giữ, sự kiện mới | A22 |
| **FR-CLI** | 13→15 | `blueprint`, `chat`, `mission`, `agent` | A14, A15 |

**Độ phủ truy vết:** sau A.1 đến A.4, mọi yêu cầu FR và NFR trong tài liệu này đều có ít nhất một đường kiểm chứng, **trừ các dòng ghi "cần tiêu chí"** (NFR-SEC-02→06, 08, 15; FR-EGR-05) — nợ truy vết đã biết, phải bổ sung tiêu chí trước khi đóng v1.0. Ba phụ lục sau A.1 tồn tại vì ba trục truy vết khác nhau — mục tiêu, nguyên tắc, và thuộc tính hệ thống — và một yêu cầu có thể xuất hiện ở nhiều trục.

---

## Phụ lục B — Danh mục mã lỗi chuẩn

Mọi mã lỗi **BẮT BUỘC** nêu đủ ba thành phần: sai ở đâu, vì sao, và cách xử lý (FR-DX-04).

**Nơi duy nhất của *cấu trúc*** — mã nào tồn tại, tên lớp, quan hệ cha con, trạng thái (`stable` · `reserved`), khoá thêm của `as_dict()` — là danh mục máy đọc được [`schemas/error-codes.v1.json`](../schemas/error-codes.v1.json) (RFC-0015, Q-66); hình dạng một lỗi đã tuần tự hoá là [`schemas/error.v1.json`](../schemas/error.v1.json). Phụ lục này giữ **lời**: thời điểm, nguyên nhân, hành vi hệ thống (FR-DX-04). Test `python/tests/test_error_catalog.py` buộc hai chiều cặp (lớp, mã) của bảng dưới ↔ danh mục, danh mục ↔ `errors.py` và mọi mã `NE…` trong `targets/`. Mọi lớp kế thừa `NeuroEdgeError`; thêm một mã là thêm một hàng ở đây **và** một mục ở danh mục. Dòng ghi *(dự kiến)* chưa có trong mã.

`NE0000` và `NE2000` là mã **chung** (`general: true` trong danh mục): người nhận **không được** rẽ nhánh theo chúng. Lớp con dùng chung mã của lớp cha (`aliases` trong danh mục; hiện chỉ `NE5001`) không có hàng riêng: hàng của lớp cha nêu tên chúng.

| Mã lỗi | Mã | Thời điểm phát sinh | Nguyên nhân | Hành vi hệ thống |
|:---|:---:|:---|:---|:---|
| `NeuroEdgeError` | NE0000 | Bất kỳ | Lỗi không phân loại: lớp gốc của mọi lỗi NeuroEdge, được dựng trực tiếp ở nơi chưa có lớp riêng (CLI, Studio, phiên mô phỏng, trình sinh firmware). Mã **chung**: không rẽ nhánh theo nó | Ném ngoại lệ ba thành phần; không đổi gì ở phần cứng. Cấp mã riêng cho từng chỗ là việc sau, và là thay đổi nới lỏng (RFC-0015 §10 mục 9) |
| `ActionContractViolation` | NE1001 | Chạy | Gọi hành động vật lý không qua `c.do()` / thiếu chữ ký gate hợp lệ | Ném ngoại lệ, chân GPIO không được kích |
| `TokenReplayError` | NE1002 | Chạy | Token phán quyết bị dùng lại (`token_replayed`), quá TTL = p95 × 3 hoặc do tiến trình khác phát hành (`token_expired`); lease của kênh `motion.*` đã dùng một lệnh (`lease_used`) hoặc quá `lease_ms` (`lease_expired`, RFC-0011 §3c) | Ném ngoại lệ (vi phạm hợp đồng, không thử lại), chân GPIO không được kích, ghi `actuator_command_rejected` (TSK-S2-05) |
| `EnvelopeRefusedError` | NE1003 | Chạy | Phong bì an toàn của chân hoặc kênh từ chối lệnh bật (`reason`): `window_budget` (hết ngân sách `max_on_ms_per_window` của cửa sổ), `min_interval_ms` (chưa đủ giãn cách từ lúc lần bật trước kết thúc), `already_on` (chân đang bật hoặc có lệnh chờ bật: không bật lại để kéo dài), `window_unreadable` (bản ghi on-time thiếu, hỏng hoặc không ghi được: coi cả cửa sổ đã dùng hết), `supervisor_unavailable` (`linux`: tiến trình giám sát line không chạy), và `max_continuous_ms` (dành cho PWM, RFC-0010 §3d: lệnh có `duration_ms` vượt trần bị từ chối; `digital.out` thì tự tắt tại trần, không từ chối). Với **cơ cấu chấp hành từ xa** (RFC-0018 §3g), chốt trạng thái từ chối trước phong bì: `actuator_state_unknown` (HAL không biết thiết bị đang tắt: lệnh trước mơ hồ, mất kênh đọc lại, lần đọc cũ hơn 2 s, vừa khởi động), `actuator_quarantined` (thiết bị đã vi phạm mức tự tắt nó khai; chỉ người vận hành gỡ) và `already_on` (lần đọc thấy đang bật mà NeuroEdge không bật). Lớp con của `ActionContractViolation` (RFC-0007 §3d, §3e) | Ném ngoại lệ, chân không được kích, token không bị tiêu, ghi sự kiện `envelope_refused`. Lệnh về phía an toàn (`digital.out` `off`, tự tắt, `hal.close()`, `off` tới cơ cấu từ xa) không bao giờ bị từ chối |
| `ToolCallError` | NE1004 | Chạy | `ToolCall` dựng với `source` không thuộc tập nguồn dispatcher gán (`docs/spec/tool_calling.md` §5): lỗi lập trình, không phải phán quyết. Cũng là `ValueError` (tương thích bản 0.1). NE1003 dành cho `EnvelopeRefusedError` (RFC-0007) | Ném ngoại lệ lúc dựng, không có lời gọi nào chạy; nêu `source` sai và các nguồn hợp lệ (TSK-I6-06) |
| `GateError` | NE2000 | Build hoặc chạy | Lớp gốc của lỗi soạn, thẩm định và phân giải gate. Mã **chung**: không rẽ nhánh theo nó, các lớp con có mã riêng (NE2001 → NE2003) | Từ chối phân giải, nêu gate và lý do |
| `GateNotFoundError` | NE2001 | Build hoặc chạy | URI hoặc đường dẫn gate không phân giải được thành tài liệu gate | Từ chối phân giải, nêu URI/đường dẫn |
| `GateSchemaError` | NE2002 | Build, `gate lint`, `gate resolve` | Gate vi phạm `schemas/gate.v1.json` hoặc tập toán tử Phụ lục B | Từ chối, nêu trường sai |
| `GateInheritanceError` | NE2003 | Build, `gate lint`, `gate resolve` | Chuỗi `extends` vi phạm nguyên tắc B.5: nới lỏng `allow_when`/`budget`/`on_block` (Q-18), `allow_when` dạng chuỗi trong chuỗi kế thừa, vượt 3 cấp, hoặc vòng lặp | Từ chối phân giải, nêu chuỗi kế thừa và dòng `rule` chỉ nguyên tắc B.5 bị vi phạm |
| `BoardCapabilityError` | NE3001 | Nạp bo mạch / Build | Khai báo bo mạch sai, hoặc agent yêu cầu năng lực bo mạch không cung cấp. Lúc nạp `board.toml` (RFC-0007, RFC-0010, RFC-0011, RFC-0012, RFC-0013): chân `digital_out` không thuộc `signal_pins` mà thiếu phong bì; `signal_pins`, `enable_pin` hoặc kênh nêu tên chưa khai; giá trị ngoài lược đồ (địa chỉ I2C ngoài 0x03..0x77, `min` ≥ `max`, `window_s` hoặc `max_continuous_ms` ≤ 0, `tolerance` vượt trần cứng); khoá năng lực gõ sai; profile khai `mirrors`. Lúc build: gate của một action `motion:<kênh>` có `p95_latency_ms` > `lease_ms / 2` của kênh (RFC-0011 §3c, §9 mục 2; `neuroedge gate lint` không đổi); `neuroedge build` không `--board` mà bo mặc định của target không thoả `[requires]` (RFC-0013 §3e). Cơ cấu chấp hành từ xa (RFC-0018 §3k): `safe_off` khai vượt `safe_off_level` của plugin; cơ cấu không hoàn tác mà plugin dưới L2 hoặc không đọc lại được; `max_continuous_ms` không lớn hơn `tolerance_ms` của plugin; `[actuators]` với target `esp32s3`; `pwm` hay `motion` nêu tên một cơ cấu từ xa | Dừng build, không sinh firmware, chỉ rõ dòng mã gọi. Build không `--board`: lỗi 3 phần nêu năng lực thiếu, bo mặc định cung cấp gì và liệt kê các bo tham chiếu của target thoả `[requires]` (hoặc nói rõ không bo nào thoả); không bao giờ tự chọn bo khác |
| `AgentManifestError` | NE3002 | Build | `agent.toml` sai cấu trúc, thiếu `[requires]`, hoặc một `@action` cần năng lực / gate mà manifest không khai. `guard.toml` sai (RFC-0016). `[plugins]` và bộ nạp plugin (RFC-0016 §3d): bản phân phối đã bật chưa cài, không import được, `sdk_requires` không tương thích, ghim phiên bản lệch, hai bản phân phối cùng tên entry point, factory sai hình dạng hay từ chối `config`. `[actuators.<tên>]` (RFC-0018 §3b, §3f): thiếu `plugin`/`safe_off`/`envelope`, mức lạ, khoá lạ, bí mật viết thẳng, tên trùng chân của bo hay không có trong `[requires] "digital.out".pins`, plugin không thuộc bản phân phối đã bật, và luật D5 — cơ cấu không hoàn tác khai `safe_off` dưới L2 | Dừng build, nêu `file:line` của hành động (TSK-S2-02) |
| `BuildFailed` | NE3003 | Build | `neuroedge build` gặp ≥ 1 vấn đề | Gom **mọi** vấn đề, in từng cái đủ 3 thành phần, thoát mã 1, không ghi artifact nào |
| `TraceValidationError` | NE4001 | `neuroedge trace validate` · `record --target esp32s3 --port` | Tệp vết ghi không hợp lệ theo `schemas/trace.v1.json`; hoặc dòng `NE1` từ UART hỏng, thiếu khung phiên, đếm lệch (`docs/spec/simulation_coverage.md` §4) | Báo lỗi kèm đường dẫn trường sai, hoặc `nguồn:dòng`; không ghi tệp nào |
| *(không phải exception — phán quyết)* | — | Chạy | Gate không thẩm định được trong ngân sách hoặc bộ thẩm định không tới được, và `fail: closed` | `BLOCK` với `reason: budget_exceeded` / `gate_unreachable`, `action: deny`, ghi vào vết ghi (TSK-S2-03). Fail-closed là phán quyết để phát lại được, không phải lỗi |
| `SafetyRegressionError` | NE4002 | `neuroedge replay`, `verify`, `assert_matches_golden` | Phán quyết gate hoặc lệnh chân của phiên replay lệch golden — kể cả lệch giữa các target (thay `TargetEquivalenceError` dự kiến); suy luận mô hình thị giác trên một target lệch golden host quá sai số `vision_in.tolerance` của bo mạch (RFC-0012 §3f) | Mã 1, chỉ rõ sự kiện và trường lệch đầu tiên; gắn nhãn *SAFETY REGRESSION* khi BLOCK thành ALLOW hoặc có lệnh chân mới (TSK-S3-04). Cũng là `AssertionError` để pytest báo test trượt |
| `ReplayError` | NE4003 | `neuroedge replay` · `verify --targets esp32s3` | Vết ghi không replay được với agent này: không biết action nào sau một gate, hoặc target không có HAL; hoặc thiết bị không có phiên replay vết ghi đó, hay replay vết ghi / gate cũ hơn checkout (firmware cũ) | Mã 1, lỗi 3 thành phần (TSK-S3-02, TSK-S4-09) |
| `VerificationError` | NE4004 | `neuroedge verify` | Một loại artifact quét được 0 — không gate nào phân giải, không vết ghi chuẩn mực nào thẩm định, không lượt replay nào — thư mục không tồn tại, hoặc một bo tham chiếu của target được yêu cầu không có lượt replay hay không có vết ghi chuẩn mực nào áp được (RFC-0013 §3f) | Mã 1, lỗi 3 thành phần nêu thư mục và `NEUROEDGE_ROOT`; quét 0 artifact không bao giờ là đạt, kể cả với một bo tham chiếu (FR-CLI-03, TSK-S3-19, RFC-0013 §3f) |
| `PerceptionUnavailableError` | NE5001 | Nạp / build / chạy (đọc HAL) | Thành phần nhận thức không dựng được: tệp ngữ pháp lệnh thiếu hoặc sai, fallback không xác định. Lúc chạy (RFC-0007 §3e): một lần đọc HAL hỏng — `digital.in`, bus I2C NACK hay timeout, `analog.in`, cảm biến mất — hoặc mốc đọc sau thời điểm lượng giá | Báo lỗi 3 thành phần. Lúc chạy, nhà cung cấp chính và fallback đều không trả lời được **không** ném lỗi: là phán quyết `Unavailable` → `gate_unreachable` / `criterion_unavailable`, áp `fail` của gate (TSK-S2-08). Lần đọc HAL hỏng thì ném lỗi này ⇒ tiêu chí chưa quyết ⇒ BLOCK `criterion_unavailable`, không bao giờ ALLOW. Lớp con dùng chung mã `NE5001`, không có hàng riêng: `CameraUnavailable` (camera không giao được khung hình), `MalformedResponse` (nhà cung cấp trả lời không phải một chat completion), `ProviderUnavailable` (nhà cung cấp không trả lời được), `SpeechUnavailable` (nhà cung cấp STT/TTS không trả lời được), `VisionUnavailable` (mô hình thị giác không trả lời được) |

## Phụ lục C — Quy ước định danh và phiên bản

| Đối tượng | Quy ước | Ví dụ |
|:---|:---|:---|
| Agent | `<tên>@<semver>` | `villa-concierge@0.3.1` |
| Gate | `<tên>@<semver>.yaml` | `unlock_door@1.2.0.yaml` |
| Gate trên Registry | `neuroedge://gates/<nhóm>/<tên>@<semver>` | `neuroedge://gates/hospitality/dual-auth-lock@1.0.0` |
| Bo mạch | `<tên>-<phiên-bản>` | `villa-panel-v2` |
| Phiên tương tác | `sess_<8 ký tự hex>` | `sess_8f9a2b1c` |
| Vết ghi thường | `traces/<mô-tả>.json` | `traces/happy-path.json` |
| Vết ghi sự cố | `traces/incidents/<session_id>.json` | `traces/incidents/sess_8f9a2b1c.json` |
| Golden Reference | `traces/golden/<kịch-bản>.json` | `traces/golden/unlock-denied.json` |
| Lược đồ công khai | `https://schema.neuroedge.dev/<loại>/v<n>.json` | `https://schema.neuroedge.dev/trace/v1.json` |
| NeuroEdge Blueprint trên index *(dự kiến, Q-72 — chốt ở RFC `blueprint.v1`)* | `neuroedge://blueprints/<tác-giả>/<tên>@<semver>` | `neuroedge://blueprints/maker/bao-ve-be-ca-nhiet-doi@1.2.0` |
| Hợp đồng nhiệm vụ *(dự kiến, Q-72 — chốt ở RFC `mission.v1`)* | `<tên>@<semver>.mission.yaml` | `trong-be-ca@0.1.0.mission.yaml` |
| Nguồn kênh chat *(dự kiến, Q-72 — chốt ở RFC nguồn `chat:<id>`)* | `chat:<id>` — `<id>` là tài khoản đã ghép đôi, do runtime gán | `chat:<id>` của tài khoản Telegram đã ghép |
| Đoạn vết ghi của runtime 24/7 *(dự kiến, Q-72 — chốt ở RFC `trace.v1`)* | `traces/runtime/<session_id>/<ngày>.json` | `traces/runtime/sess_8f9a2b1c/2026-10-11.json` |

## Phụ lục D — Cấu trúc Monorepo và Giao thức Truyền dẫn

### D.1 Bố cục Monorepo tiêu chuẩn

Bố cục kho và thủ tục sửa từng thư mục: **[`CONTRIBUTING.md` §6](../CONTRIBUTING.md#6-cấu-trúc-kho)** — nơi duy nhất.

### D.2 Giao thức Truyền dẫn & Định dạng Vết ghi (Wire Protocol)

1. **Giao thức mạng Wi-Fi / LAN:** `WebSocket` bảo mật truyền luồng âm thanh Opus (Binary Frame) và sự kiện vết ghi JSON (Text Frame).
2. **Giao thức cổng nối tiếp UART** (921600 baud): vết ghi là JSON Lines, mỗi dòng mang tiền tố `NE1 ` để tách khỏi log firmware (TSK-S4-09); khung phiên, giới hạn dòng và cách host dựng vết ghi: `docs/spec/simulation_coverage.md` §4. Khung nhị phân, nếu cần, đóng gói `SLIP`.
3. **Định dạng âm thanh nén:** Opus Voice Mode (16 kbps, 16 kHz mono, kích thước khung 20 ms = 320 mẫu). Cùng một định dạng cho mọi target; `sim` phát lại tệp WAV qua đúng đường mã hóa này để giữ tương đương với phần cứng thật.

---

*Hết tài liệu*
