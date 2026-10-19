# Ứng dụng di động NeuroEdge ("app nhà"): đặc tả yêu cầu phần mềm (SRS)

> **Đã duyệt bởi Q-91 (2026-10-19); đồng bộ theo Q-92 (2026-10-19): I2g = API hộp + web nhà (đầu tiên, sau ra mắt công khai), I2h = app gốc React Native trên cùng backend; không gì chờ cổng nhu cầu (đã bỏ).** Q-91 trả lời các câu
> hỏi mở `AP-D-01` → `AP-D-17` (§6); task ở §7 chia giữa I2g và I2h. Yêu cầu nào dựa vào một RFC chưa
> có được ghi "(cần RFC)". **Thay đổi 2026-10-19:** bản nháp 2026-10-16 thành bản đã duyệt; ứng dụng là app gốc iOS
> và Android (không còn web di động). Cấu trúc theo ISO/IEC/IEEE 29148:2018 §9.6,
> như `docs/spec/missions.md`. Mọi mã đã có được dẫn lại thay vì chép lại (`CONTRIBUTING.md` §8.1).
> **Tài liệu cùng bộ:** `01-user-stories.md` (`US-APP-nn`), `02-brd.md` (`BR-APP-nn`),
> `prototype/index.html` (màn hình `MH-1` … `MH-8`).

---

## 1. Giới thiệu

### 1.1 Mục đích

Đặc tả này nói ứng dụng di động phải làm gì để người trong gia đình xem nhà, trò chuyện, chỉnh con số,
duyệt thay đổi, thêm và gỡ thiết bị, đọc nhật ký và nhận cảnh báo, mà không phải viết YAML, gate hay hợp
đồng. Mỗi yêu cầu truy về một yêu cầu kinh doanh (`BR-APP-nn`) và, khi dựa trên điều đã có, về mã đó
(`MS-*`, `BL-*`, `FR-*`) thay vì nhắc lại nội dung.

### 1.2 Phạm vi

Trong phạm vi: tầng giao diện và các quy tắc hiển thị, duyệt, xem trước, thêm/gỡ thiết bị, cảnh báo và đo
lường của ứng dụng, trong mười bốn nhóm ở §3. Ứng dụng đứng trước lõi sẵn có và **không thay lõi**.

Ngoài phạm vi: bản thân bộ não (NeuroClaw, Q-78, Q-83); ngữ nghĩa gate và hợp đồng (`docs/spec/missions.md`,
`docs/spec/blueprint.md`); ngành dọc chăm sóc người cao tuổi và chuỗi leo thang (hoãn bởi Q-72, rủi ro R-19, Q-91 (7);
các yêu cầu AL gắn "ngành dọc sau" chỉ là thiết kế chuẩn bị); Zalo Mini App; relay hoặc cloud canh hộp từ ngoài nhà
(Q-74). Ứng dụng **không phát hiện bệnh, không phát hiện té ngã**; chỉ báo người
thân về thay đổi thói quen.

### 1.3 Định nghĩa

| Thuật ngữ | Nghĩa |
|:---|:---|
| **Hộp** | Máy chạy NeuroEdge tại nhà, phần tin cậy: gate, thiết bị, duyệt, trace, đường ra dữ liệu. |
| **Bộ não** | NeuroClaw (Q-78, Q-83): không tin cậy, nói với hộp qua MCP, không bao giờ duyệt. |
| **Thẻ duyệt** | Tóm tắt ≤ 5 dòng của một thay đổi, sinh từ cấu trúc đã biên dịch (MS-AP-01); phần bổ sung bên dưới không tính vào 5 dòng (Q-91 (8), AP-CD-02). |
| **Vùng xanh** | Giá trị trong khoảng chỉnh được do maker khai (MS-CT-06, BL-IN-04). |
| **Vùng vàng** | Giá trị ngoài khoảng maker nhưng trong giới hạn giá trị của `board.v1`; được phép sau khi chấp nhận rõ ràng, có nhãn rủi ro (Q-91 (8), cần RFC). |
| **Vùng khóa** | Giá trị vượt giới hạn mà `board.v1` khai (envelope về thời gian bật/tắt, `safe_state`, và giới hạn theo giá trị, như °C, do RFC của TSK-I2g-02 thêm); không đổi được từ ứng dụng. |
| **Chạy lại trên trace** | Xem trước: chạy cấu hình đề xuất trên trace 24 giờ gần nhất, chỉ đọc ("what-if"). |
| **Đã biết** | Xác nhận một cảnh báo; khác với duyệt một thay đổi. |

### 1.4 Tài liệu tham chiếu

`01-user-stories.md`, `02-brd.md` · `docs/spec/missions.md` (Q-87) · `docs/spec/blueprint.md` (Q-86) ·
`docs/spec/studio.md` (Q-51) · `docs/spec/virtual_parts.md` (Q-84) · `docs/user/chat-voi-nha.md` ·
`docs/business/brd-ambient-intelligence.md` (Q-85) · `roadmap/neuroedge-prd.md` (Q-38, Q-72, Q-73, Q-74,
Q-77, Q-78, Q-80, Q-83 → Q-91; R-19) · RFC-0019 (`docs/rfc/0019-ban-ghi-duyet-co-chu-ky.md`), `docs/spec/deployment_profiles.md` (DP-A-05, DP-A-06, DP-COM-04 → DP-COM-09) · RFC-0014 (`docs/rfc/0014-du-kien-tu-tien-trinh-ngoai.md`), RFC-0018
(`docs/rfc/0018-co-cau-chap-hanh-tu-xa.md`) · `CONTRIBUTING.md` §3 (khi nào cần RFC) và §8.1.

---

## 2. Mô tả tổng quan

### 2.1 Bối cảnh

```
 người trong gia đình          ứng dụng (app gốc, RN)            hộp (tin cậy)                 bộ não (không tin cậy)
 ────────────────────          ──────────────────────            ─────────────                 ──────────────────────
 xem, chat, chỉnh, duyệt ───►  hiển thị, soạn thẻ chờ duyệt ───► gate · hợp đồng · trace         soạn, hỏi lại, trả lời
                                                                 duyệt (đúng người, đúng digest) ◄── MCP ──► (không duyệt)
                       ◄───── thẻ, cảnh báo, nhật ký ◄────────── đường ra dữ liệu duy nhất (MS-EG-01)
```

**Ranh giới tin cậy.** Ứng dụng chỉ nói chuyện với hộp. Bộ não không có đường nào để duyệt, khóa hay ghi
gate (MS-RT-04, MS-CH-05, FR-CH-05). Ứng dụng chỉ hiển thị và chuyển lời duyệt của người; hộp tự tính lại
mọi phán quyết, kể cả vùng màu (AP-ZN-07). Trong nhà, lời duyệt của ứng dụng là bản ghi ký bằng khóa thiết bị mở bằng vân tay hoặc Face ID, một nguồn người mới (Q-91 (5), AP-AV-04, cần RFC); ngoài nhà, lời duyệt chỉ đến từ bot duyệt riêng của hộp, bằng bản ghi do hộp ký (DP-A-06, RFC-0019, Q-91 (3)). Chỉ chat tự do đi qua kênh riêng của NeuroClaw (AP-CH-01), và không bao giờ mang lời duyệt.

### 2.2 Tám màn hình mẫu

| Mã | Màn hình | Nội dung chính |
|:---|:---|:---|
| **MH-1** | Nhà | Biểu ngữ khẩn; thẻ "Bể cá phòng khách" (26,8 °C, "Ổn"); thẻ "Nhà bố mẹ" ("Cần chú ý", mẫu ngành dọc sau này); dòng "1 đề xuất chờ bạn duyệt"; thanh tab Nhà, Chat, Thiết bị, Hoạt động, Cài đặt. |
| **MH-2** | Chat | Hỏi về bể; thẻ đề xuất "Không bật sưởi khi nước từ 28 °C" (đang 29 °C) với nhãn vùng, "Nếu áp dụng hôm qua: chặn thêm 1 lần", nút Chỉnh / Duyệt; gợi ý nhanh. |
| **MH-3** | Thiết bị | Nhóm theo không gian; máy sưởi, máy sục khí có khóa, nhiệt độ nước; thiết bị nhà bố mẹ; "Thêm thiết bị". |
| **MH-4** | Chi tiết máy sưởi | Biểu đồ 24 giờ với đường ngưỡng; luật dạng câu có nhãn vùng; giới hạn phần cứng khóa; lần chặn gần nhất; thanh trượt ba vùng. |
| **MH-5** | Hoạt động | Bộ lọc Tất cả / Bị chặn / Cảnh báo / Đã duyệt; nhật ký; "Chạy lại hôm qua với luật hiện tại". |
| **MH-6** | Thêm thiết bị, bước 3/5 | "Thử trực tiếp": cảm biến cửa, mở rồi đóng một lần, thấy sự kiện. |
| **MH-7** | Cài đặt | Người trong gia đình và vai trò; kênh báo; ngân sách AI; rủi ro đang bật; relay canh hộp. |
| **MH-8** | Duyệt Blueprint (mẫu dạng thông báo) | Thẻ "Hộp bể cá sẽ:" ba câu; nguồn của digest (BL-IN-02) và bằng chứng ghi "unsigned" (BL-EV-03); chạm để duyệt; Xem chi tiết / Từ chối. Thông báo đẩy không mang nội dung; thẻ này hiện trong app sau khi mở (AP-AL-11, Q-91 (7)). |

Số liệu trong màn hình mẫu (nhiệt độ, giờ, "0,40 / 2 USD", "30 giây trước") là **dữ liệu minh họa**, không
phải mặc định hay ngưỡng của sản phẩm. Các thẻ, thiết bị và mục "Nhà bố mẹ" và relay canh hộp (MH-1, MH-3, MH-7) là
mẫu của ngành dọc người cao tuổi, hoãn (Q-72, R-19, Q-91 (7)), không thuộc I2g.

### 2.3 Ứng dụng dựa trên những gì đã có

- `python/neuroedge/studio/` (`neuroedge studio`, Q-51; hợp đồng `docs/spec/studio.md`): trang web cục bộ chỉ nghe 127.0.0.1 (`docs/spec/studio.md` §2)
  với `/api/agent`, `/api/gates…`, `/api/traces…`, `/api/record`, `/api/lint`, `/api/verify`, `/api/test`,
  `/api/device…`. Bị Q-72 (PRD §14) tạm dừng; Q-91 (4) mở lại làm trang web máy tính cho maker, dùng chung một API hộp
  với ứng dụng (TSK-I2g-05).
- `python/neuroedge/viz/` và `python/neuroedge/sim/ui.py`: trang trực tiếp của `run --ui` và `mcp serve
  --ui`; `neuroedge ui-link` in liên kết một lần tới trang nhà (`docs/user/chat-voi-nha.md`). Các trang này chỉ phục vụ
  trên 127.0.0.1 (`sim/ui.py`); DP-A-02 đòi `Origin` của chính máy chủ và khóa riêng mỗi lần chạy.
- `python/neuroedge/pairing.py`: ghép **bộ não** với hộp qua mạng (khóa của hộp, `pair renew`, `pair rotate`;
  token của bộ não sống tối đa 7 ngày, DP-A-04). Ghép **chủ hộp** là việc khác: `neuroedge pair owner`, mã dùng
  một lần hiện trên hộp (Q-89, RFC-0019, TSK-I2d-12). Ghép điện thoại với API của hộp và thông tin xác thực riêng của
  ứng dụng do RFC của TSK-I2g-01 thiết kế (Q-91 (3)).
- `python/neuroedge/hal/parts.toml`: danh mục 17 loại linh kiện (relay, light, heater, pump, fan, lock,
  button, contact, temperature, humidity, level, ph, sensor, knob, motor, servo, display; Q-84,
  `docs/spec/virtual_parts.md`); lệnh `neuroedge add part`; `python/neuroedge/templates/add_part.py`.
- `python/neuroedge/hal/pin_map.py` (TSK-I2d-32); `python/neuroedge/hal/remote.py` (RFC-0018,
  TSK-I2c-16: trạng thái do HAL giữ, "off debt", tắt về an toàn không bị từ chối);
  `python/neuroedge/hal/envelope.py` (envelope từng chân, chỉ có thể từ chối).
- `python/neuroedge/engine/compiler.py`, `python/neuroedge/engine/gate_explain.py` (`neuroedge gate
  explain`), chạy lại (`neuroedge replay`, `python/neuroedge/testing/player.py`, `python/neuroedge/trace.py`).
- `fixtures/agents/aquarium/agent.toml`: bể cá mẫu (sưởi không bật khi nước từ 29 °C hay không có số đọc;
  sục khí an toàn là bật, tắt thì hỏi chủ).
- Phụ thuộc đã lên lịch trong roadmap: xem §7.

### 2.4 Giả định và phụ thuộc

1. Lõi sẵn có đủ cho người duyệt ở nhà; những phần ghi "dự kiến" (FR-CH-07, FR-CH-08) chưa có code.
2. Mọi yêu cầu dựa trên thứ chưa có code (thẻ duyệt, bản ghi duyệt, trace theo đoạn) chỉ kiểm chứng được
   sau khi task tương ứng xong (§5, §7).
3. Q-73 (minh bạch thay vì cấm đoán, ba bất biến) và Q-38 (không là chức năng an toàn được chứng nhận)
   luôn áp dụng.
4. Hỗ trợ hai bản chính mới nhất của iOS và của Android; ngưỡng hiệu năng đặt trong thiết kế I2h và đo trên điện thoại thật (Q-91 (2), AP-NF-06).
5. I2g mở đầu tiên sau ra mắt công khai (I6), I2h sau I2g (Q-92 (8)); không gì chờ cổng nhu cầu. Chưa có ngày: dòng nào trong tài liệu này cũng không phải cam kết lịch. Duyệt có hai đường, cả hai giữ: passkey trong web nhà (TSK-I2f-08, thuộc I2g) và Face ID/vân tay trong app (TSK-I2g-01 là RFC chung).

---

## 3. Yêu cầu

Phương pháp kiểm chứng: **T** thử nghiệm, **D** trình diễn, **I** kiểm tra bằng đọc, **A** phân tích.
Yêu cầu cần RFC nêu rõ "(cần RFC)" theo `CONTRIBUTING.md` §3, kèm task RFC của I2g (§7). Nơi "Nguồn" ghi mã `MS-*`, `BL-*`, `FR-*`, yêu
cầu đó **dựa vào** mã ấy và không chép lại.

### 3.1 Vỏ ứng dụng, ghép đôi, truy cập (SH)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-SH-01 | Ứng dụng phải là app gốc cho iOS và Android viết bằng React Native, hỗ trợ hai bản chính mới nhất của mỗi hệ điều hành; bản thử phát qua TestFlight và Google Play internal testing. Hộp phục vụ một API có xác thực trong mạng nhà cho ứng dụng; việc này là một quyết định an ninh mới, cần mục `threat_model.md` do kỹ sư trưởng duyệt (cần RFC, TSK-I2g-01). | Q-91 (2), (3) chốt dạng và đường tới hộp. | BR-APP-01, BR-APP-02; US-APP-01; Q-91 (2), (3), Q-51, `docs/spec/studio.md` §2, DP-A-02; TSK-I2g-01, TSK-I2g-06, TSK-I2g-13 | D |
| AP-SH-02 | Điện thoại ghép với hộp một lần bằng mã dùng một lần (8 ký tự, 10 phút) chỉ hiện trên hộp (Q-89), sau đó dùng thông tin xác thực riêng của thiết bị với API của hộp (cần RFC, TSK-I2g-01). Ghép chủ hộp cho bot duyệt vẫn theo Q-89: `/pair <mã>` từ cuộc chat riêng; ứng dụng không tạo cơ chế ghép người thứ hai ngoài hai đường này. `python/neuroedge/pairing.py` ghép bộ não, không ghép người. Thiết bị chưa ghép chỉ thấy màn hình ghép đôi. | Một mã chỉ hiện tại nhà; không ai ghép từ xa. | BR-APP-04; US-APP-06; Q-91 (3), Q-89, RFC-0019, FR-CH-03, MS-CH-01, TSK-I2d-12, TSK-I2g-01, TSK-I2g-06 | T |
| AP-SH-03 | Ứng dụng chỉ được nói chuyện với hộp, trừ chat tự do với bộ não qua kênh riêng của NeuroClaw (AP-CH-01); không gọi dịch vụ ngoài khác. Điện thoại nhận tín hiệu đẩy từ Apple và Google (AP-AL-11), tín hiệu đó không chứa nội dung. | Hộp là đường ra dữ liệu duy nhất cho mọi việc ngoài chat. | BR-APP-04; US-APP-03; MS-EG-01, FR-EGR-01, Q-91 (6), (7) | T |
| AP-SH-04 | Phần xem và duyệt tại nhà phải chạy không cần Internet. Ngoài nhà, ứng dụng không tới hộp trực tiếp: duyệt đi qua bot duyệt riêng của hộp (AP-AV-03), và màn hình phải nói rõ giới hạn đó. Relay hoặc cloud chỉ theo Q-74 bước 2. | Truy cập ngoài nhà trực tiếp cần relay hoặc cloud (Q-74). | BR-APP-07; US-APP-18; Q-91 (3), Q-74, NFR-REL-05, RFC-0019 | D |
| AP-SH-05 | Thanh tab dưới phải có năm mục Nhà, Chat, Thiết bị, Hoạt động, Cài đặt; phần của maker phải nằm ở nơi riêng (Studio, trang web máy tính, AP-SH-08), không lẫn trong năm tab này. | Người dùng gia đình không thấy công cụ của maker. | BR-APP-09, BR-APP-01; US-APP-16; Q-91 (4) | I |
| AP-SH-06 | Ở mặc định, ứng dụng không được hiện YAML, digest, `board.v1`, mã lỗi hay số chân; chi tiết chỉ hiện sau "Xem chi tiết", và số chân chỉ hiện trong bước đấu dây. | Che thuật ngữ nhưng vẫn mở được chi tiết. | BR-APP-01; US-APP-01, US-APP-08, US-APP-09; MS-AP-01 | I |
| AP-SH-07 | Liên kết vào trang cục bộ do `neuroedge ui-link` cấp (trang web của hộp, không phải ứng dụng) phải dùng một lần; liên kết cũ hết hiệu lực khi cấp liên kết mới. Ứng dụng không dùng liên kết này để ghép (AP-SH-02). | Không để lại đường vào dùng lại được. | BR-APP-04; US-APP-06; `docs/user/chat-voi-nha.md` | T |
| AP-SH-08 | Ứng dụng và Studio (trang web máy tính cho maker) phải dùng chung một API của hộp (what-if, chạy lại, thiết bị, thẻ duyệt); Studio không có logic duyệt hay luật riêng. | Một API, hai mặt trước. | BR-APP-09, BR-APP-02; US-APP-16; Q-91 (4), Q-51, `docs/spec/studio.md`; TSK-I2g-05 | T |

### 3.2 Màn Nhà (HM)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-HM-01 | Màn Nhà phải hiện mỗi nơi trong nhà một thẻ gồm tên, giá trị chính, trạng thái bằng chữ ("Ổn", "Cần chú ý") và biểu đồ nhỏ. | Đọc được trong vài giây. | BR-APP-01; US-APP-01 | D |
| AP-HM-02 | Trạng thái của thẻ phải suy từ dữ kiện hộp đọc và từ bộ phát hiện tất định, không từ LLM. | Trạng thái nhà không phụ thuộc bộ não. | BR-APP-01, BR-APP-08; US-APP-01; MS-RT-05, FR-AGT-04 | T |
| AP-HM-03 | Dữ liệu cũ hoặc cảm biến mất tín hiệu phải hiện kèm giờ cuối ("dữ liệu từ hh:mm"), không hiện như giá trị hiện tại. | Số cũ trông như số mới là lỗi nguy hiểm. | BR-APP-01, BR-APP-07; US-APP-01, US-APP-18; MS-RT-05 (`sensor_stale`) | T |
| AP-HM-04 | Màn Nhà phải hiện số đề xuất đang chờ duyệt và mở được từng thẻ; số chờ không vượt 4 trên một hộp. | Đồng bộ với giới hạn của hộp. | BR-APP-02; US-APP-01; MS-CH-04 | T |
| AP-HM-05 | Thẻ của ngành dọc người cao tuổi (khi có) chỉ được mô tả thay đổi thói quen ("chưa thấy hoạt động từ 7:00"); không được dùng chữ chẩn đoán bệnh hay té ngã. | Tránh tuyên bố y tế và hiểu nhầm là chức năng an toàn được chứng nhận. | BR-APP-07; US-APP-02; Q-38, Q-72, R-19 | I |

### 3.3 Chat (CH)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-CH-01 | Ứng dụng không giữ khóa LLM, và hộp không gửi câu hỏi duyệt qua bộ não. Chat của ứng dụng với bộ não đi qua một kênh riêng của NeuroClaw (Q-83 (4); kho `letrongminh/neuroclaw`, TSK-I2g-11); lời duyệt không bao giờ đi qua kênh này. | Khóa nằm ở bộ não, không ở ứng dụng. | BR-APP-04; US-APP-03; FR-CH-01, MS-RT-04, Q-83, RFC-0019, Q-91 (6); TSK-I2g-11 | I |
| AP-CH-02 | Mỗi con số trong câu trả lời về nhà phải mở được sự kiện gốc trong nhật ký; con số không có sự kiện gốc phải bị đánh dấu là không có nguồn. | Câu trả lời "dựa trên số liệu thật" phải kiểm được. | BR-APP-01, BR-APP-08; US-APP-03; MS-TS-01 | T |
| AP-CH-03 | Điều người dùng muốn đổi, nói trong chat, phải thành thẻ đề xuất qua luồng thẻ duyệt (AP-CD); không được áp dụng trực tiếp từ chat. | Một đường duyệt duy nhất. | BR-APP-02; US-APP-04; MS-AP-04, TSK-I2d-23 | T |
| AP-CH-04 | Lời "Có" hay "Đồng ý" gõ vào chat không trả lời một yêu cầu duyệt đang chờ thì không được duyệt gì. | Tin nhắn chat là yêu cầu, không phải sự đồng ý. | BR-APP-04; US-APP-04, US-APP-06; MS-CH-02 | T |
| AP-CH-05 | Khi bộ não ngừng, tab Chat phải hiện "phân tích tạm ngưng"; các tab còn lại phải dùng được bình thường. | Mất bộ não chỉ mất phần phân tích. | BR-APP-08; US-APP-03; MS-RT-02, NFR-REL-05 | T |
| AP-CH-06 | Khi ngân sách phân tích hết, tab Chat phải báo "đã hết ngân sách phân tích kỳ này"; thiết bị và cảnh báo khẩn phải vẫn chạy. | Ngân sách chỉ dừng phân tích. | BR-APP-08; US-APP-14; MS-RT-06, NFR-REL-05 | T |

### 3.4 Thẻ duyệt chung (CD)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-CD-01 | Mọi thay đổi của hợp đồng (đề xuất từ chat, chỉnh thanh trượt) phải hiện qua cùng một thẻ duyệt và cùng quy trình bản nháp, kiểm tra, thẻ, duyệt, khóa. Gia đình cũng đổi được gate và linh kiện do trình hướng dẫn thiết bị sinh (AP-DV-06): mỗi gate sinh ra phải qua `neuroedge gate lint` và chỉ được khóa bằng một lời duyệt ký sinh trắc tại nhà (AP-AV-04); đường khóa này cần RFC (TSK-I2g-04), vì MS-AP-04, MS-AP-05 chỉ khóa hợp đồng (`missions.lock`) còn gate khóa bằng `digests.lock`. Cài Blueprint theo AP-CD-09, không theo quy trình này. | Một đường kiểm duy nhất. | BR-APP-02; US-APP-04, US-APP-05, US-APP-09, US-APP-15; MS-AP-04, MS-AP-05; Q-91 (9); TSK-I2g-04 | T |
| AP-CD-02 | Nội dung thẻ phải là thẻ do hộp sinh (≤ 5 dòng tiếng Việt thường); ứng dụng không được tự soạn hay sửa câu chữ của thẻ. Phần bổ sung bên dưới thẻ (kết quả chạy lại AP-WI-01, nhãn vùng, "khi hỏng", nhãn rủi ro AP-CD-04, chi tiết) không tính vào 5 dòng và không đổi phần thẻ. | Thẻ sinh từ cấu trúc đã biên dịch, không từ LLM. | BR-APP-02, BR-APP-01; US-APP-04; MS-AP-01; Q-91 (8); TSK-I2g-07 | T |
| AP-CD-03 | Thẻ quá dài để duyệt qua chat phải ghi phải duyệt tại nhà, và việc duyệt chỉ được thực hiện tại chỗ với toàn bộ khác biệt. | Thay đổi dài cần đọc đủ. | BR-APP-02; US-APP-04; MS-AP-02 | T |
| AP-CD-04 | Thẻ phải hiện nhãn vùng của từng con số, trạng thái "khi hỏng" của thiết bị có trạng thái an toàn khác tắt, và các nhãn rủi ro có liên quan (các nhãn mà tài liệu đã duyệt định nghĩa, xem AP-ST-04). Tóm tắt duyệt phải mang câu Q-38 (R-19). | Người duyệt thấy rủi ro họ nhận. | BR-APP-02, BR-APP-03, BR-APP-08; US-APP-05, US-APP-14; MS-SF-06, MS-SF-05, DP-COM-06, Q-73, Q-38, R-19 | I |
| AP-CD-05 | Một thay đổi chưa được duyệt phải không có hiệu lực lên thiết bị hay luật. | Thẻ chỉ là đề xuất. | BR-APP-02, BR-APP-04; US-APP-04, US-APP-15; MS-AP-04, BL-IN-05 | T |
| AP-CD-06 | Lời duyệt phải gắn với digest của chính thay đổi đang hiển thị; hộp phải từ chối lời duyệt cho digest khác. | Digest được duyệt là digest chạy. | BR-APP-04; US-APP-06; MS-AP-05, MS-CH-03 | T |
| AP-CD-07 | Thẻ hết hạn phải bị coi là không duyệt. | Lời duyệt cũ không còn giá trị. | BR-APP-04; US-APP-06; MS-CH-04 | T |
| AP-CD-08 | Mỗi thẻ phải có nút "Xem chi tiết" mở khác biệt đầy đủ và giải thích gate (`neuroedge gate explain`). | Người chịu trách nhiệm mở được chi tiết. | BR-APP-01; US-APP-08, US-APP-15; `python/neuroedge/engine/gate_explain.py` | D |
| AP-CD-09 | Thẻ cài Blueprint phải hiện tóm tắt do hộp sinh theo BL-IN-03 (gồm đích mạng, nhãn rủi ro, và mỗi bằng chứng ghi "unsigned" theo BL-EV-03), cho biết digest được đối chiếu với `--digest`, chỉ mục, hay in ra để người xác nhận (BL-IN-02), và mang câu Q-38; thẻ không ghi "đã qua Action CI" hay "đã kiểm chứng". Không chạy tệp nào của gói trước khi duyệt (BL-IN-05); gói được ghi vào thư mục mới, không bao giờ vào thư mục có sẵn không rỗng (BL-IN-06); nút Từ chối không cài gì. Trong ứng dụng, thẻ này là màn đồng ý cài Blueprint (MH-8, TSK-I2g-07); ứng dụng chỉ là mặt trước của `neuroedge blueprint show`/`install` (BL-IN-01). Gói khai đích mạng chỉ duyệt tại nhà (FR-MSN-14). | Cài đặt chỉ sau khi người đọc tóm tắt. | BR-APP-02; US-APP-15; BL-IN-01 → BL-IN-03, BL-IN-05, BL-IN-06, BL-EV-03, FR-MSN-14, R-19, TSK-I2e-03, TSK-I2g-07 | T |
| AP-CD-10 | Khi có thẻ cần duyệt, ứng dụng phải nhận tín hiệu đẩy không nội dung qua APNs hoặc FCM, và hộp phải gửi thêm tin qua bot Telegram đã ghép (AP-AL-11); ứng dụng tải nội dung thẻ qua mạng nhà khi mở. Ngoài nhà, duyệt bằng nút của bot duyệt không cần liên kết (RFC-0019). | Thông báo màn hình khóa không lộ nội dung. | BR-APP-02; US-APP-15; FR-CH-01, RFC-0019; Q-91 (3), (7); TSK-I2g-10 | D |

### 3.5 Ba vùng (ZN)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-ZN-01 | Mỗi con số chỉnh được phải thuộc đúng một trong ba vùng: **xanh** (trong khoảng maker khai), **vàng** (ngoài khoảng maker, trong giới hạn giá trị của `board.v1`) và **khóa** (vượt giới hạn mà `board.v1` khai, AP-ZN-02). Vùng vàng sửa BL-IN-04 (giá trị ngoài khoảng maker không còn bị hỏi lại hay từ chối nếu người dùng chấp nhận rõ ràng) và cần RFC trên `blueprint.v1` (TSK-I2g-03); luật đã khai vẫn chạy đúng như đã khai (Q-73 (b)). | Người dùng thấy mình ở đâu. | BR-APP-03; US-APP-05, US-APP-16; MS-CT-06, BL-IN-04, MS-CT-04; Q-91 (8); TSK-I2g-03 | T |
| AP-ZN-02 | Vùng khóa phải lấy từ những gì `board.v1` khai: envelope về thời gian (`window_s`, `max_on_ms_per_window`, `min_interval_ms`, `max_continuous_ms`), `safe_state` (MS-CT-04, MS-CP-02) và giới hạn theo giá trị (như °C) do một RFC thêm vào `board.v1` (cần RFC, `CONTRIBUTING.md` §3, TSK-I2g-02); không đổi được từ ứng dụng; giá trị vượt phải làm nút duyệt vô hiệu và ghi "Vượt giới hạn phần cứng". Cho tới khi RFC đó xong, vùng khóa kiểu giá trị chưa có. | Hợp đồng không nới được envelope. | BR-APP-03; US-APP-05; MS-CT-04, MS-CP-02, FR-ACE-03, `schemas/board.v1.json`; Q-91 (8); TSK-I2g-02 | T |
| AP-ZN-03 | Vùng xanh phải lấy từ khoảng chỉnh được (kiểu và khoảng) mà maker khai trong tham số `ask` hay tham số cài đặt. | Người cài chỉ chỉnh trong khoảng đã kiểm chứng. | BR-APP-03, BR-APP-09; US-APP-05, US-APP-16; MS-CT-06, BL-IN-04 | T |
| AP-ZN-04 | Giá trị ở vùng vàng phải hiện nhãn rủi ro, đổi nút thành "Duyệt, chấp nhận rủi ro", và việc chấp nhận phải ghi vào trace (cần RFC, TSK-I2g-03). | Q-73: nhãn rủi ro thay cho cấm đoán; bất biến (c). | BR-APP-03, BR-APP-08, BR-APP-10; US-APP-05, US-APP-14; Q-73, Q-91 (8); TSK-I2g-03 | T |
| AP-ZN-05 | Thanh trượt phải hiện ba vùng bằng màu, chữ và biểu tượng; không được dùng màu làm tín hiệu duy nhất. | Người không phân biệt màu vẫn đọc được. | BR-APP-03; US-APP-05 | I |
| AP-ZN-06 | Vùng xanh không được ghi "an toàn"; nhãn phải là "Trong khoảng maker cho phép". | Tránh hiểu nhầm là chức năng an toàn được chứng nhận. | BR-APP-03; US-APP-05; Q-38, R-19 | I |
| AP-ZN-07 | Khi nhận lời duyệt, hộp phải tự tính lại vùng của từng giá trị và không tin vùng do ứng dụng gửi; giá trị ở vùng khóa phải bị từ chối bất kể ứng dụng gửi gì. | Ứng dụng chỉ hiển thị; hộp quyết định. | BR-APP-03, BR-APP-04; US-APP-05; MS-CP-02, MS-CT-04 | T |
| AP-ZN-08 | Tham số cài đặt của Blueprint chỉ được ghi vào dữ kiện, luật cảm biến hoặc linh kiện; một tham số nhắm vào gate phải làm gói không hợp lệ. | Luật đã kiểm chứng không bị chỉnh. | BR-APP-03, BR-APP-09; US-APP-16; BL-IN-04 | T |

### 3.6 Duyệt và xác minh (AV)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-AV-01 | Chỉ chủ hộp đã ghép theo Q-89 (kênh bot) hoặc điện thoại đã ghép theo AP-SH-02 mới duyệt được; bộ não, ứng dụng MCP, nhóm chat và nguồn tự động không được có đường nào để duyệt. | AI không duyệt. | BR-APP-04; US-APP-06; FR-CH-05, MS-CH-05, MS-RT-04, MS-CH-07, Q-89, RFC-0019, Q-91 (3), (5) | T |
| AP-AV-02 | Một bản ghi duyệt giả gửi qua MCP phải bị hộp từ chối và ghi vào trace. | Bất biến Q-73 (a). | BR-APP-04; US-APP-06; MS-CH-05, Q-73 | T |
| AP-AV-03 | Duyệt hành động vật lý phải đi qua hộp bằng một trong ba đường: trang cục bộ tại nhà; lời duyệt ký sinh trắc của ứng dụng trong nhà (AP-AV-04); hoặc nút của bot duyệt riêng của hộp với bản ghi duyệt do hộp ký (nonce dùng một lần, hạn dùng, digest của gate), dùng ngoài nhà. Mọi `ask` được trả lời từ xa, trong trần, TTL và nhãn `risk=remote_approval`; cổng chỉ duyệt tại chỗ chờ TSK-I2d-20. | Không có đường duyệt nào nhờ bộ não. | BR-APP-04; US-APP-06; DP-A-05, DP-A-06, RFC-0019, Q-89, Q-91 (3), (5), MS-CH-03, MS-AP-05, `docs/user/chat-voi-nha.md` | T |
| AP-AV-04 | Ứng dụng phải ký lời duyệt bằng khóa thiết bị mở bằng Face ID hoặc vân tay; hộp giữ khóa công khai và xác minh cục bộ, đám mây không giả mạo được lời duyệt. Đây là một nguồn người mới, sớm hơn FR-CH-08 (TSK-I2f-08), cần RFC sửa RFC-0006 và RFC-0019 cùng mục `threat_model.md` do kỹ sư trưởng duyệt (cần RFC, TSK-I2g-01). Lời duyệt ký sinh trắc tại nhà cũng là điều kiện khóa gate sinh ra (AP-CD-01). | Vân tay là cách duyệt người dùng chọn, nay nằm trong I2g. | BR-APP-04; US-APP-06; Q-91 (5), (9), FR-CH-08, TSK-I2f-08, RFC-0006, RFC-0019; TSK-I2g-01, TSK-I2g-07 | T |
| AP-AV-05 | Mỗi lời duyệt phải ghi người duyệt, kênh, digest và giờ vào trace và khóa. | Truy vết người chịu trách nhiệm. | BR-APP-04, BR-APP-08; US-APP-06, US-APP-11; FR-CH-04, MS-AP-05, MS-CH-03 | T |
| AP-AV-06 | Phương thức xác minh do người dùng chọn phải hiện nhãn rủi ro của nó trên thẻ; việc chọn không bị chặn. | Q-73: minh bạch thay cho cấm đoán. | BR-APP-04, BR-APP-08; US-APP-06, US-APP-14; MS-CH-06, Q-73 | I |
| AP-AV-07 | Khi có nhiều người dùng, chỉ người có vai trò duyệt mới duyệt được; người chỉ có vai trò khẩn cấp phải bị từ chối. Trước đó chỉ có một chủ hộp được ghép (Q-89). | Phân quyền theo vai trò. | BR-APP-04, BR-APP-07; US-APP-12; FR-CH-07, TSK-I2f-05, Q-89 | T |
| AP-AV-08 | Lời duyệt từ xa phải bị giới hạn bởi `[approvals] remote_per_hour` trong `agent.toml` (mặc định 10, tối đa 30, cửa sổ trượt một giờ; duyệt tại chỗ đặt lại cửa sổ). Vượt trần phải hiện "hết lượt duyệt từ xa, duyệt tại nhà" (lý do `over_cap`); mọi lời bị từ chối phải hiện lý do bằng câu thường, theo danh sách đóng của RFC-0019 (`bad_signature`, `nonce_reused`, `expired`, `gate_changed`, `not_owner`, `wrong_bot`, `over_cap`). | Tài khoản chat bị chiếm chỉ duyệt được tới trần. | BR-APP-04; US-APP-06; Q-89, RFC-0019, TC-A-06-1 | T |
| AP-AV-09 | Bot duyệt phải là bot riêng của hộp, với token khác token bot của bộ não; hộp từ chối khởi động nếu hai token trùng. Khi duyệt từ xa đang bật, nhãn `risk=remote_approval` phải hiện trên thẻ và trong danh sách rủi ro đang bật (AP-ST-04). | Bộ não bị chiếm không giả được lời duyệt. | BR-APP-04, BR-APP-08; US-APP-06, US-APP-14; DP-A-06, DP-COM-06, RFC-0019, TC-A-06-2 | T |

### 3.7 Chạy lại trên trace (WI)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-WI-01 | Trước khi duyệt, thẻ phải hiện kết quả chạy lại cấu hình đề xuất trên trace 24 giờ gần nhất của chính hộp: "nếu áp dụng hôm qua: sẽ chặn N lần" và, khi có, "sẽ báo N lần lúc hh:mm". | Người duyệt thấy hệ quả bằng dữ liệu thật trước khi khóa. | BR-APP-05; US-APP-07, US-APP-11; MS-TS-01, MS-TS-02 | T |
| AP-WI-02 | Việc chạy lại phải chỉ đọc: không gửi lệnh ra thiết bị, không ghi gate, hợp đồng hay khóa. Chạy lại chỉ đọc không nằm trong danh sách RFC của `CONTRIBUTING.md` §3 (AP-D-09 đã trả lời); sự kiện trace mới cho đoạn trace thì cần RFC (TSK-I2d-13). | Xem trước không gây tác dụng. | BR-APP-05; US-APP-07; MS-RT-04, CONTRIBUTING.md §3; AP-D-09 | T |
| AP-WI-03 | Kết quả phải do hộp tính bằng chạy lại (`neuroedge replay`, `python/neuroedge/testing/player.py`); bộ não không tính. | Con số phải tái lập được. | BR-APP-05; US-APP-07; MS-TS-02 | T |
| AP-WI-04 | Kết quả phải nêu khoảng thời gian đã dùng; mỗi lần chặn hay báo phải bấm vào xem được sự kiện gốc. | Kiểm chứng được. | BR-APP-05, BR-APP-08; US-APP-07; MS-TS-01 | D |
| AP-WI-05 | Với cảm biến mới chưa có lịch sử, kết quả phải dùng kịch bản mẫu của Blueprint và nói rõ điều đó, hoặc ghi "xem lại sau 24 giờ". | Không tạo con số giả. | BR-APP-05; US-APP-07; BL-KT-03 | D |
| AP-WI-06 | Khi đoạn trace bị thiếu hoặc bị sửa, ứng dụng phải báo lỗi và không hiện con số. | Không đưa số từ dữ liệu hỏng. | BR-APP-05; US-APP-07; MS-TS-02 | T |
| AP-WI-07 | Kết quả không được dùng lời bảo đảm ("sẽ an toàn"); chỉ nêu số lần chặn và báo trong dữ liệu đã dùng. | Tránh tuyên bố tuyệt đối. | BR-APP-05; US-APP-07; Q-38 | I |

### 3.8 Thiết bị, trình hướng dẫn, gỡ (DV)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-DV-01 | Màn Thiết bị phải nhóm theo không gian và hiện tên người đọc được, trạng thái và giờ cập nhật của mỗi thiết bị, lấy từ phần mô tả linh kiện (`label`, `kind`). | Người dùng thấy "Máy sưởi", không thấy tên chân. | BR-APP-01; US-APP-08; `docs/spec/virtual_parts.md`, `fixtures/agents/aquarium/agent.toml` | D |
| AP-DV-02 | Bật hay tắt một thiết bị phải đi qua gate như mọi lệnh khác; ứng dụng không có đường vòng qua gate. | Bất biến của lõi. | BR-APP-01; US-APP-08; FR-ACE-03 | T |
| AP-DV-03 | Khi hộp từ chối, ứng dụng phải hiện lý do bằng câu thường kèm giá trị lúc đó (ví dụ "nước đã 29,1 °C"); mã gate và điều kiện chỉ hiện sau "Xem chi tiết". | Hiểu thay vì bực. | BR-APP-01; US-APP-08; MS-CP-06, `python/neuroedge/engine/gate_explain.py` | T |
| AP-DV-04 | Thiết bị có trạng thái an toàn là bật phải có biểu tượng khóa và câu "luôn giữ; tắt thì hỏi bạn"; điều kiện của gate (ví dụ bể cá: nước từ 29 °C thì không tắt, không hỏi) hiện ở Xem chi tiết. | Cho thấy vùng khóa. | BR-APP-01, BR-APP-03; US-APP-08; MS-SF-06, `fixtures/agents/aquarium/agent.toml` | D |
| AP-DV-05 | Chi tiết một thiết bị (MH-4) phải hiện biểu đồ 24 giờ có đường ngưỡng, các luật dạng câu với nhãn vùng, giới hạn phần cứng ở vùng khóa và lần bị chặn gần nhất kèm giá trị. | Một chỗ để hiểu một thiết bị. | BR-APP-01, BR-APP-03; US-APP-05, US-APP-08; MS-CP-06 | D |
| AP-DV-06 | Trình hướng dẫn thêm thiết bị phải chọn loại từ danh mục (`python/neuroedge/hal/parts.toml`) và sinh kết quả tương đương `neuroedge add part` (linh kiện, mục `[requires]`, và với kiểu ra: hành động, gate fail-closed, kiểm thử hai chiều; VP-PT-07), không bắt người dùng viết cấu hình. Chạy trên `sim` (`[sim.parts]`) và trên board thật (TSK-I2g-09); board thật cần `[targets.<board>.pins]` (VP-PM-01; PR cần kỹ sư trưởng duyệt, VP-PM-06). Gate sinh ra phải qua `neuroedge gate lint` và chỉ khóa theo AP-CD-01 (cần RFC, TSK-I2g-04). Canvas kéo thả vẫn hoãn (TSK-I2d-31). | Bỏ rào cản cấu hình. | BR-APP-06; US-APP-09; Q-84, Q-91 (9), VP-PT-07, VP-PM-01, VP-PM-06, TSK-I2d-31, `python/neuroedge/templates/add_part.py`; TSK-I2g-04, TSK-I2g-09 | T |
| AP-DV-07 | Bước "Thử trực tiếp" phải hiện sự kiện thật hộp nhìn thấy (ví dụ mở lúc 15:42:08, đóng lúc 15:42:11) trước khi cho sang bước tiếp. Đọc từng cảm biến dùng `neuroedge lab doctor` (MS-LB-02, TSK-I2d-17). | Thiết bị phải chứng minh nó hoạt động. | BR-APP-06; US-APP-09 | D |
| AP-DV-08 | Ở bước đấu dây, ứng dụng phải chỉ cách đấu bằng lời ("dây đỏ vào chân số 3") lấy từ bản đồ chân của board; đây là nơi duy nhất ở mặc định được hiện số chân. Đường này cho board thật (AP-DV-06, TSK-I2g-09). | Người đấu dây cần số chân; chỗ khác thì không. | BR-APP-06, BR-APP-01; US-APP-09; TSK-I2d-32, `python/neuroedge/hal/pin_map.py`, Q-91 (9) | D |
| AP-DV-09 | Đường cảm biến không dây phải ghi rõ chưa dùng được cho đến khi dữ kiện từ tiến trình ngoài có code (RFC-0014 đã duyệt 2026-10-04; code hoãn sau v1.0); không được giả vờ đã thêm. Cơ cấu chấp hành từ xa đã có qua Home Assistant (RFC-0018, TSK-I2c-16) ở mức skill (MS-CP-04); trình hướng dẫn không được mô tả chúng là chưa dùng được. | Code của RFC-0014 hoãn sau v1.0. | BR-APP-06; US-APP-09; RFC-0014, RFC-0018, TSK-I2c-16, MS-CP-04 | I |
| AP-DV-10 | Kết thúc trình hướng dẫn phải tạo một thẻ duyệt (AP-CD-01); thiết bị, gate và linh kiện mới không có hiệu lực trước khi được duyệt và khóa theo AP-CD-01. | Một đường duyệt duy nhất. | BR-APP-02, BR-APP-06; US-APP-09; MS-AP-04; Q-91 (9) | T |
| AP-DV-11 | Gỡ thiết bị phải đưa nó về trạng thái an toàn trước khi gỡ (tắt về an toàn không bao giờ bị từ chối); hộp chỉ tắt cái hộp đã bật. | "Off debt" của hộp. | BR-APP-06; US-APP-10; `python/neuroedge/hal/remote.py`, RFC-0018, TSK-I2c-16 | T |
| AP-DV-12 | Trước khi gỡ, ứng dụng phải liệt kê luật và hợp đồng đang dùng thiết bị và cảnh báo; việc gỡ phải qua thẻ duyệt. | Không gỡ làm hỏng luật. | BR-APP-06, BR-APP-02; US-APP-10; MS-AP-04 | T |
| AP-DV-13 | Gỡ thiết bị không được xóa lịch sử trace của nó trong thời gian giữ trace. | Nhật ký còn đọc được sau khi gỡ. | BR-APP-06, BR-APP-08; US-APP-10; MS-TS-03 | T |

### 3.9 Luật mặc định theo loại thiết bị (KD)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-KD-01 | Gate cho thiết bị mới phải do `neuroedge add part` sinh (VP-PT-07: hành động, gate fail-closed, kiểm thử hai chiều); ứng dụng không có bộ sinh gate thứ hai. Mặc định về giá trị của hợp đồng chỉ được có khi một Blueprint khai (MS-CT-06, FR-MSN-13, `parameters` của BL-IN-04); không được là mặc định ngầm trong runtime, vì đổi ngữ nghĩa gate cần RFC. Gate sinh ra theo AP-DV-06 phải qua `neuroedge gate lint` và được khóa theo AP-CD-01. | Một sự thật một chỗ; luật chạy đúng như đã khai. | BR-APP-06, BR-APP-02; US-APP-09; Q-73, MS-CT-06, FR-MSN-13, VP-PT-07, BL-IN-04, CONTRIBUTING.md §3; AP-D-06, Q-91 (9) | T |
| AP-KD-02 | Mức mặc định theo loại (đèn tự do; máy sưởi và máy bơm có điều kiện; khóa hỏi chủ) là đề xuất chờ chủ sản phẩm; chỉ được thực hiện qua `neuroedge add part` hoặc do Blueprint khai (AP-KD-01). | Mức rủi ro khác nhau theo loại. | BR-APP-06, BR-APP-01; US-APP-09; AP-D-06 | I |
| AP-KD-03 | Mẫu mặc định không được thêm mức "cấm hẳn" mà người dùng không thấy và không đổi được. | Q-73: không cấm thay người dùng. | BR-APP-06, BR-APP-08; US-APP-09; Q-73 | I |
| AP-KD-04 | Mỗi luật mặc định phải hiện thành câu thường; gỡ nó phải qua thẻ duyệt và thẻ phải nói đó là luật mặc định. | Người dùng thấy và quyết định được. | BR-APP-02, BR-APP-10; US-APP-04; MS-AP-01 | D |
| AP-KD-05 | Giá trị trong mẫu mặc định không được rộng hơn envelope của board; nếu rộng hơn, việc sinh phải bị từ chối. | Tighten only. | BR-APP-03, BR-APP-06; US-APP-09; MS-CP-02 | T |
| AP-KD-06 | Maker phải khai được, cho từng tham số, kiểu và khoảng chỉnh được và luật mặc định theo loại trong Blueprint; khai khoảng rộng hơn giới hạn board phải làm gói bị từ chối, nêu tham số. | Maker quyết định khoảng an toàn. | BR-APP-09, BR-APP-03; US-APP-16; MS-CT-06, BL-IN-04, MS-CP-02 | T |

### 3.10 Hoạt động và nhật ký (AC)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-AC-01 | Tab Hoạt động phải liệt kê sự kiện giảm dần theo thời gian, mỗi mục một câu thường, sinh từ trace, không từ LLM. | Nhật ký đáng tin. | BR-APP-01, BR-APP-08; US-APP-11; MS-TS-04 | T |
| AP-AC-02 | Bộ lọc phải có Tất cả, Bị chặn, Cảnh báo, Đã duyệt; mỗi mục thuộc đúng một loại. | Tìm nhanh. | BR-APP-08; US-APP-11 | T |
| AP-AC-03 | Mục bị chặn phải nêu lý do bằng lời của luật đã chặn và giá trị lúc đó. | Người dùng biết luật nào đã dừng việc. | BR-APP-01, BR-APP-08; US-APP-11; MS-CP-06 | T |
| AP-AC-04 | Mục đã duyệt phải nêu người duyệt, cách duyệt và giờ. | Truy vết người chịu trách nhiệm. | BR-APP-08; US-APP-11; MS-AP-05 | T |
| AP-AC-05 | Mỗi mục phải mở được sự kiện gốc trong trace qua "Xem chi tiết". | Không che sự thật. | BR-APP-01, BR-APP-08; US-APP-11, US-APP-03 | D |
| AP-AC-06 | Nút "Chạy lại hôm qua với luật hiện tại" phải chạy như AP-WI-01 ở chế độ chỉ đọc. | Cùng một cơ chế xem trước. | BR-APP-05, BR-APP-08; US-APP-11; AP-WI-02 | D |
| AP-AC-07 | Nhật ký chỉ phải đọc được trong thời gian hộp giữ trace; câu hỏi về xa hơn phải được báo là ngoài thời gian giữ. | Giữ trace 30 ngày trên hộp. | BR-APP-08; US-APP-11; MS-TS-03 | T |

### 3.11 Cảnh báo và leo thang (AL)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-AL-01 | Cảnh báo khẩn phải do bot của hộp gửi từ mẫu tiếng Việt cố định, không qua LLM, không bị gộp hay giữ lại bởi ngân sách tin nhắn. | Cảnh báo đến cả khi không có bộ não. | BR-APP-07; US-APP-02; MS-RT-07, FR-AGT-06, NFR-COST-02 | T |
| AP-AL-02 | Cảnh báo trên ứng dụng phải có nút "Đã biết"; bấm là xác nhận của người đã ghép, ghi vào trace và dừng chuỗi leo thang. "Đã biết" không áp dụng thay đổi nào. Chưa có quy định đã duyệt cho "Đã biết" và chuỗi leo thang (MS-RT-07 chỉ có cảnh báo mẫu cố định, MS-TS-04 không có sự kiện xác nhận); hoãn cùng ngành dọc người cao tuổi (Q-91 (7)), cần RFC sự kiện trace (mở rộng TSK-I2d-13). | Xác nhận khác duyệt. | BR-APP-07; US-APP-02; FR-CH-04; Q-91 (7) | T |
| AP-AL-03 | Chuỗi leo thang (ngành dọc sau) phải theo danh sách người có thứ tự và thời gian chờ chỉnh được: hỏi tại chỗ trước, rồi người thứ nhất qua nhiều kênh, chưa xác nhận thì người kế, lặp đến khi có xác nhận. Hoãn cùng ngành dọc người cao tuổi (Q-91 (7), R-19); thêm sự kiện trace hay trường mới thì cần RFC; thời gian chờ mặc định đặt khi ngành dọc mở (AP-D-07). Không thuộc I2g hay I2h. | Cảnh báo chắc chắn đến nơi. | BR-APP-07; US-APP-02, US-APP-12; MS-RT-07, MS-TS-04, CONTRIBUTING.md §3; AP-D-07, Q-91 (7) | T |
| AP-AL-04 | Ứng dụng phải hiện chuỗi leo thang đang ở bước nào và giờ của bước kế. | Người nhận biết còn bao lâu. | BR-APP-07; US-APP-02 | D |
| AP-AL-05 | Câu hỏi tại chỗ (ngành dọc sau) phải nhận "Tôi ổn" từ thiết bị cục bộ đã ghép (nút bấm hoặc trang cục bộ; giọng nói đã bỏ, Q-77); tín hiệu từ bộ não hay ứng dụng MCP phải bị coi là không hợp lệ. | Xác minh nghĩa là một con người. | BR-APP-07; US-APP-17; MS-CH-07, FR-CH-05, Q-73, TSK-I2d-20, TSK-I2d-21 | T |
| AP-AL-06 | Kênh báo của I2g là push không nội dung qua APNs và FCM (AP-AL-11) và bot Telegram của hộp; Zalo là P1 (FR-CH-01). Mỗi kênh thêm (Zalo, SMS qua 4G, gọi tự động) phải là một đích khai báo, chỉ thêm được khi duyệt tại nhà. | Đích dữ liệu mới không duyệt qua chat. | BR-APP-07; US-APP-13; FR-CH-01, TSK-I2d-12, MS-EG-01, MS-AP-04; AP-D-05, Q-91 (7) | T |
| AP-AL-11 | Tín hiệu đẩy qua APNs và FCM chỉ được nói "có việc cần bạn", không mang nội dung thẻ, giá trị cảm biến hay tên thiết bị; ứng dụng tải chi tiết qua mạng nhà khi mở. Khi không tới được hộp, ứng dụng chỉ báo là chưa tải được. | Nội dung không rời khỏi nhà qua Apple hay Google. | BR-APP-07, BR-APP-02; US-APP-02, US-APP-13, US-APP-15; Q-91 (7), MS-EG-01; TSK-I2g-10 | T |
| AP-AL-07 | Khi kênh chat sập, cảnh báo phải hiện ở trang cục bộ và nằm trong hàng đợi giữ giờ gốc. | Cảnh báo không mất. | BR-APP-07; US-APP-13; MS-RT-08 | T |
| AP-AL-08 | Người nhận leo thang chỉ nhận cảnh báo khẩn và không có quyền duyệt. Người nhận khác chủ hộp cần FR-CH-07 (TSK-I2f-05): Q-89 chỉ ghép một chủ, và nhóm chat không bao giờ ghép (MS-CH-01). | Quyền tối thiểu. | BR-APP-07; US-APP-12, US-APP-18; FR-CH-07 | T |
| AP-AL-09 | Hộp mất liên lạc phải được báo cho người nhận kèm giờ tín hiệu cuối; việc canh phải do relay ngoài nhà làm, nên cần relay hoặc cloud (Q-74 bước 2, mở theo dữ liệu ra mắt, Q-92 (8)); FR-EGR-05 định relay là đường hầm TLS trong suốt, chưa có nhiệm vụ canh hộp. Ngưỡng im lặng đặt cùng ngành dọc người cao tuổi (AP-D-07, Q-91 (7)). Không thuộc I2g. | Hộp chết thì không tự báo được. | BR-APP-07; US-APP-18; FR-EGR-05, Q-74; AP-D-04, AP-D-07 | T |
| AP-AL-10 | Câu chữ cảnh báo của ngành dọc người cao tuổi chỉ được nói về thay đổi thói quen; không chẩn đoán, không nói té ngã. | Rủi ro pháp lý và y tế. | BR-APP-07; US-APP-02, US-APP-17; Q-72, Q-38, R-19 | I |

### 3.12 Cài đặt, rủi ro, ngân sách (ST)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-ST-01 | Cài đặt phải hiện người trong gia đình và vai trò (duyệt, khẩn cấp, báo sau N phút); trước khi có đa người dùng, ứng dụng phải chạy ở chế độ một chủ hộp. | FR-CH-07 mới ở mức dự kiến. | BR-APP-07; US-APP-12; FR-CH-07, TSK-I2f-05, Q-89 | D |
| AP-ST-02 | Thay đổi vai trò hay thứ tự leo thang phải qua thẻ duyệt và chỉ chủ hộp được duyệt. | Quyền không tự nới. | BR-APP-07, BR-APP-02; US-APP-12; MS-AP-04 | T |
| AP-ST-03 | Ngân sách AI phải hiện đã dùng trên trần của kỳ, lấy từ ngân sách `llm` của hợp đồng; số tiền (USD) là số bộ não báo, hộp không thấy hóa đơn LLM (Q-87, MS-RT-06) và màn hình phải ghi rõ như vậy. | Người dùng thấy chi phí. | BR-APP-08; US-APP-14; MS-CT-05, MS-RT-06, NFR-COST-01 | T |
| AP-ST-04 | Danh sách "rủi ro đang bật" phải liệt kê mọi nhãn rủi ro đang có hiệu lực theo định nghĩa của các tài liệu đã duyệt, và nguồn của từng nhãn: `risk=remote_approval` (RFC-0019), `risk=virtual_board` (Q-84), `risk=simulated_interlock` (MS-SF-05, ví dụ máy sục khí của bể cá trên `sim`), `risk=single_chip`, `risk=readable_flash` (Q-79) và các nhãn riêng của bộ não (Q-80); chúng được in lúc khởi động và hiện ở `status` (DP-COM-06). | Minh bạch thay cho cấm đoán. | BR-APP-08; US-APP-14; Q-73, MS-EG-03, MS-CH-06, DP-COM-06, MS-SF-05, RFC-0019, Q-79, Q-80, Q-84 | T |
| AP-ST-05 | Người dùng phải thu hồi được chủ hộp đã ghép bằng `neuroedge pair owner --revoke` trên hộp, hoặc `/revoke` từ chủ đã ghép trên bot duyệt; `/revoke` chỉ thu hồi, không bao giờ cấp quyền. Chỉ có một chủ được ghép: ghép chủ mới thay chủ cũ. Việc thu hồi điện thoại đã ghép với API của hộp do RFC của TSK-I2g-01 quy định (cần RFC). | Mất điện thoại. | BR-APP-04; US-APP-06; Q-89, RFC-0019, TSK-I2d-12; Q-91 (3); TSK-I2g-01 | T |
| AP-ST-06 | Ứng dụng phải hiển thị ở Cài đặt, ở tóm tắt duyệt và ở thẻ Blueprint rằng NeuroEdge không phải chức năng an toàn được chứng nhận. | Tránh hiểu nhầm. | BR-APP-08; US-APP-14; Q-38, R-19 | I |
| AP-ST-07 | Trạng thái relay canh hộp (có, chưa bật, tín hiệu cuối lúc nào) phải hiện ở Cài đặt; khi chưa bật phải nêu lý do. | Người dùng biết có được canh không. | BR-APP-07; US-APP-18; FR-EGR-05, Q-74 | D |

### 3.13 Đo lường (MT)

> Chỉ số của ứng dụng (BR-APP-10) là tiêu chí thoát của I2h; không có cổng nhu cầu (Q-92). Ngưỡng đặt bằng dữ liệu ra mắt (Q-91 (10), TSK-I2g-12).

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-MT-01 | Ứng dụng phải ghi tại hộp, cục bộ, sự kiện cần cho ba chỉ số: gỡ luật mặc định (AP-KD-04), chặn đúng/chặn oan, và chấp nhận vùng vàng (AP-ZN-04). Thêm loại sự kiện trace là sửa trace chuẩn (cần RFC). | Cổng nhu cầu cần số đo. | BR-APP-10; TSK-I2e-07, TSK-I2g-12; Q-91 (10); MS-TS-04, CONTRIBUTING.md §3 | T |
| AP-MT-02 | Mục bị chặn phải có cách người dùng đánh dấu "chặn đúng" hoặc "chặn oan"; định nghĩa của "oan" đặt trong I2g cùng ngưỡng (AP-MT-04). | Không có nhãn thì không đo được. | BR-APP-10; US-APP-11; AP-D-08, Q-91 (10); TSK-I2g-12 | D |
| AP-MT-03 | Sự kiện đo không được chứa tên Blueprint, digest, URL, giá trị cảm biến hay nội dung chat, và theo chính sách ẩn danh, opt-out của FR-TEL-01 (FR-TEL-07, BL-NF-02); roadmap TSK-I2e-07 đã sửa theo cùng chính sách (Q-90). | Đếm mà không theo dõi người. | BR-APP-10; TSK-I2e-07; BL-NF-02, MS-EG-01 | T |
| AP-MT-04 | Ngưỡng đạt của các chỉ số và ngưỡng hiệu năng (AP-NF-06) không được ghi cứng trong ứng dụng; chúng là tiêu chí thoát của I2h, đặt bằng dữ liệu ra mắt. | Không tự đặt ngưỡng. | BR-APP-10; AP-D-08, Q-91 (10); TSK-I2g-12 | I |

### 3.14 Phi chức năng (NF)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-NF-01 | Mọi chữ hiển thị ở mặc định phải là tiếng Việt thường, không chứa thuật ngữ như digest, YAML hay mã lỗi. | Người dùng không kỹ thuật. | BR-APP-01; US-APP-01, US-APP-08 | I |
| AP-NF-02 | Không chuỗi giao diện nào được dùng lời tuyệt đối ("an toàn tuyệt đối", "chặn đứng"). | Tránh tuyên bố không kiểm chứng được. | BR-APP-01, BR-APP-08; US-APP-05; Q-38 | I |
| AP-NF-03 | Mất bộ não, mạng ngoài hoặc ngân sách LLM thì ứng dụng vẫn phải xem, duyệt, bật/tắt và nhận cảnh báo khẩn. | Lõi tách khỏi bộ não. | BR-APP-07, BR-APP-08; US-APP-02, US-APP-03; NFR-REL-05, MS-RT-02 | T |
| AP-NF-04 | Thẻ, cảnh báo khẩn và nhãn không được gọi LLM để tạo; chỉ chat tự do mới dùng bộ não. | Chi phí và độ tin cậy. | BR-APP-02, BR-APP-08; US-APP-04; MS-AP-01, MS-RT-07, NFR-COST-01 | T |
| AP-NF-05 | Ứng dụng không được in token, khóa hay mã ghép đôi lên màn hình, log hay URL (ngoài liên kết một lần của `ui-link`). | Không rò bí mật. | BR-APP-04; US-APP-06; MS-CH-01, AP-SH-07 | T |
| AP-NF-06 | Ứng dụng phải chạy trên hai bản chính mới nhất của iOS và của Android; ngưỡng thời gian phản hồi đặt trong thiết kế I2g và đo trên điện thoại thật. | Không tự đặt con số. | BR-APP-01; US-APP-01; Q-91 (2); AP-D-11; TSK-I2g-06 | A |

---

## 4. Truy vết

### 4.1 BR-APP → yêu cầu AP

| BR-APP | Yêu cầu AP |
|:---|:---|
| BR-APP-01 | AP-SH-01, AP-SH-05, AP-SH-06, AP-HM-01, AP-HM-02, AP-HM-03, AP-CH-02, AP-CD-02, AP-CD-08, AP-DV-01, AP-DV-02, AP-DV-03, AP-DV-04, AP-DV-05, AP-DV-08, AP-KD-02, AP-AC-01, AP-AC-03, AP-AC-05, AP-NF-01, AP-NF-02, AP-NF-06 |
| BR-APP-02 | AP-SH-01, AP-SH-08, AP-HM-04, AP-CH-03, AP-CD-01, AP-CD-02, AP-CD-03, AP-CD-04, AP-CD-05, AP-CD-09, AP-CD-10, AP-DV-10, AP-DV-12, AP-KD-01, AP-KD-04, AP-ST-02, AP-AL-11, AP-NF-04 |
| BR-APP-03 | AP-CD-04, AP-ZN-01, AP-ZN-02, AP-ZN-03, AP-ZN-04, AP-ZN-05, AP-ZN-06, AP-ZN-07, AP-ZN-08, AP-DV-04, AP-DV-05, AP-KD-05, AP-KD-06 |
| BR-APP-04 | AP-SH-02, AP-SH-03, AP-SH-07, AP-CH-01, AP-CH-04, AP-CD-05, AP-CD-06, AP-CD-07, AP-ZN-07, AP-AV-01, AP-AV-02, AP-AV-03, AP-AV-04, AP-AV-05, AP-AV-06, AP-AV-07, AP-AV-08, AP-AV-09, AP-ST-05, AP-NF-05 |
| BR-APP-05 | AP-WI-01, AP-WI-02, AP-WI-03, AP-WI-04, AP-WI-05, AP-WI-06, AP-WI-07, AP-AC-06 |
| BR-APP-06 | AP-DV-06, AP-DV-07, AP-DV-08, AP-DV-09, AP-DV-10, AP-DV-11, AP-DV-12, AP-DV-13, AP-KD-01, AP-KD-02, AP-KD-03, AP-KD-05 |
| BR-APP-07 | AP-SH-04, AP-HM-03, AP-HM-05, AP-AV-07, AP-AL-01, AP-AL-02, AP-AL-03, AP-AL-04, AP-AL-05, AP-AL-06, AP-AL-07, AP-AL-08, AP-AL-09, AP-AL-10, AP-AL-11, AP-ST-01, AP-ST-02, AP-ST-07, AP-NF-03 |
| BR-APP-08 | AP-HM-02, AP-CH-02, AP-CH-05, AP-CH-06, AP-CD-04, AP-ZN-04, AP-AV-05, AP-AV-06, AP-AV-09, AP-WI-04, AP-DV-13, AP-KD-03, AP-AC-01, AP-AC-02, AP-AC-03, AP-AC-04, AP-AC-05, AP-AC-06, AP-AC-07, AP-ST-03, AP-ST-04, AP-ST-06, AP-NF-02, AP-NF-03, AP-NF-04 |
| BR-APP-09 | AP-SH-05, AP-SH-08, AP-ZN-03, AP-ZN-08, AP-KD-06 |
| BR-APP-10 | AP-ZN-04, AP-KD-04, AP-MT-01, AP-MT-02, AP-MT-03, AP-MT-04 |

### 4.2 US-APP → yêu cầu AP

| US-APP | Yêu cầu AP |
|:---|:---|
| US-APP-01 | AP-SH-01, AP-SH-06, AP-HM-01, AP-HM-02, AP-HM-03, AP-HM-04, AP-NF-01, AP-NF-06 |
| US-APP-02 | AP-HM-05, AP-AL-01, AP-AL-02, AP-AL-03, AP-AL-04, AP-AL-10, AP-AL-11, AP-NF-03 |
| US-APP-03 | AP-SH-03, AP-CH-01, AP-CH-02, AP-CH-05, AP-AC-05, AP-NF-03 |
| US-APP-04 | AP-CH-03, AP-CH-04, AP-CD-01, AP-CD-02, AP-CD-03, AP-CD-05, AP-KD-04, AP-NF-04 |
| US-APP-05 | AP-CD-01, AP-CD-04, AP-ZN-01, AP-ZN-02, AP-ZN-03, AP-ZN-04, AP-ZN-05, AP-ZN-06, AP-ZN-07, AP-DV-05, AP-NF-02 |
| US-APP-06 | AP-SH-02, AP-SH-07, AP-CH-04, AP-CD-06, AP-CD-07, AP-AV-01, AP-AV-02, AP-AV-03, AP-AV-04, AP-AV-05, AP-AV-06, AP-AV-08, AP-AV-09, AP-ST-05, AP-NF-05 |
| US-APP-07 | AP-WI-01, AP-WI-02, AP-WI-03, AP-WI-04, AP-WI-05, AP-WI-06, AP-WI-07 |
| US-APP-08 | AP-SH-06, AP-CD-08, AP-DV-01, AP-DV-02, AP-DV-03, AP-DV-04, AP-DV-05, AP-NF-01 |
| US-APP-09 | AP-SH-06, AP-CD-01, AP-DV-06, AP-DV-07, AP-DV-08, AP-DV-09, AP-DV-10, AP-KD-01, AP-KD-02, AP-KD-03, AP-KD-05 |
| US-APP-10 | AP-DV-11, AP-DV-12, AP-DV-13 |
| US-APP-11 | AP-AV-05, AP-WI-01, AP-AC-01, AP-AC-02, AP-AC-03, AP-AC-04, AP-AC-05, AP-AC-06, AP-AC-07, AP-MT-02 |
| US-APP-12 | AP-AV-07, AP-AL-03, AP-AL-08, AP-ST-01, AP-ST-02 |
| US-APP-13 | AP-AL-06, AP-AL-07, AP-AL-11 |
| US-APP-14 | AP-CH-06, AP-CD-04, AP-ZN-04, AP-AV-06, AP-AV-09, AP-ST-03, AP-ST-04, AP-ST-06 |
| US-APP-15 | AP-CD-01, AP-CD-05, AP-CD-08, AP-CD-09, AP-CD-10, AP-AL-11 |
| US-APP-16 | AP-SH-05, AP-SH-08, AP-ZN-01, AP-ZN-03, AP-ZN-08, AP-KD-06 |
| US-APP-17 | AP-AL-05, AP-AL-10 |
| US-APP-18 | AP-SH-04, AP-HM-03, AP-AL-08, AP-AL-09, AP-ST-07 |

---

## 5. Kiểm chứng

Kế hoạch kiểm chứng cho I2g và I2h (task ở §7): **chưa có test case; tạo khi I2g mở sau ra mắt công khai (Q-92).**
Không dòng nào dưới đây là cam kết lịch.

| Nhóm | Phương pháp dự kiến | Điều kiện để kiểm chứng |
|:---|:---|:---|
| SH, NF | D, I; T cho ghép đôi, API hộp và liên kết một lần; đo hiệu năng trên điện thoại thật | RFC TSK-I2g-01, TSK-I2g-05, TSK-I2g-06; bản thử TSK-I2g-13 |
| HM, CH, AC | T trên trace mẫu bể cá | Thẻ duyệt, trace theo đoạn (TSK-I2d-06, TSK-I2d-13, TSK-I2d-14) |
| CD, AV | T: lời duyệt giả, hết hạn, sai digest | Bản ghi duyệt có chữ ký (TSK-I2d-11, TSK-I2d-12; RFC-0019); duyệt ký sinh trắc và khóa gate sinh ra cần TSK-I2g-01, TSK-I2g-04, TSK-I2g-07 |
| ZN, KD | T trên khoảng mẫu của Blueprint | RFC vùng vàng và giới hạn giá trị (TSK-I2g-02, TSK-I2g-03); Blueprint (TSK-I2e-01, TSK-I2e-03) |
| WI | T: kết quả chạy lại bằng đúng kết quả `replay`; không có lệnh ra thiết bị | Trace theo đoạn (TSK-I2d-13, TSK-I2d-14) |
| DV | T trên `sim`, D cho đấu dây | `python/neuroedge/hal/remote.py`, TSK-I2d-32, TSK-I2g-09 |
| AL | T cho cảnh báo và push không nội dung (TSK-I2g-10); D cho chuỗi leo thang | TSK-I2d-09; chuỗi leo thang hoãn cùng ngành dọc sau; relay cần Q-74 |
| ST, MT | T, I | TSK-I2e-07, TSK-I2g-12 |

---

## 6. Câu hỏi mở (`AP-D-nn`)

| Mã | Câu hỏi | Bối cảnh | Ảnh hưởng |
|:---|:---|:---|:---|
| **AP-D-01** | Vùng vàng có tồn tại không? | **Đã quyết (Q-91 (8)):** vùng vàng tồn tại: giá trị ngoài khoảng maker nhưng trong giới hạn giá trị của `board.v1` được phép sau khi chấp nhận rõ ràng, kèm nhãn rủi ro; sửa BL-IN-04 qua RFC `blueprint.v1` (TSK-I2g-03). Bối cảnh cũ: Giá trị ngoài khoảng đã khai bị hỏi lại hoặc từ chối theo BL-IN-04 (TC-IN-04-1); hợp đồng chỉ siết, không nới (MS-CP-02); Q-73 bất biến (b): luật đã khai chạy đúng như đã khai. MS-CT-06 chỉ yêu cầu tham số mở khai kiểu và khoảng. Một giá trị ngoài khoảng qua `sensor_facts` (ví dụ ngưỡng `water_hot` của bể cá) làm đổi luật hiệu lực của gate sưởi. Chủ sản phẩm chọn: (a) cho phép ngoài khoảng maker với nhãn rủi ro và chấp nhận rõ ràng, hoặc (b) từ chối giá trị ngoài khoảng maker. Nếu (a), `blueprint.v1` (TSK-I2e-01) phải khai điều đó và MS-CP-02 phải còn đúng. | AP-ZN-01, AP-ZN-04 |
| **AP-D-02** | Có cần passkey (vân tay) sớm hơn I2f không? | **Đã quyết (Q-91 (5)):** cần sớm hơn FR-CH-08: ứng dụng ký lời duyệt bằng khóa thiết bị mở bằng Face ID hoặc vân tay, một nguồn người mới, cần RFC sửa RFC-0006 và RFC-0019 (TSK-I2g-01). Bối cảnh cũ: Q-89 và RFC-0019 cho duyệt từ xa qua bot của hộp mà không cần passkey; RFC-0019 giữ passkey là phương thức sau. Còn mở: ứng dụng có cần nó sớm hơn FR-CH-08 (TSK-I2f-08, chưa có code) không. | AP-AV-03, AP-AV-04 |
| **AP-D-03** | Dạng ứng dụng: web di động, ứng dụng gốc hay Zalo Mini App? Cách thay cho đẩy thông báo màn hình khóa? | **Đã quyết (Q-91 (2), (7)):** app gốc iOS và Android bằng React Native; thay cho đẩy màn hình khóa là push không nội dung qua APNs và FCM cùng bot Telegram (TSK-I2g-10). Bối cảnh cũ: Nút của bot duyệt nằm ngay trong cuộc chat (RFC-0019), nên duyệt bằng bot không cần liên kết tới thẻ; trang cục bộ chỉ nghe 127.0.0.1 (AP-D-12). Vân tay và đẩy thông báo trên web (đặc biệt iOS) khó. | AP-SH-01, AP-CD-10 |
| **AP-D-04** | Truy cập từ ngoài nhà cần relay hoặc cloud (Q-74): làm trước hay sau ra mắt? | **Đã quyết (Q-74), xác nhận ở Q-91 (11), điều kiện mở theo Q-92 (8):** bước 2 mở sau ra mắt và chỉ khi dữ liệu ra mắt cho thấy người kẹt ở bước cài hộp; phê duyệt không đi qua relay (FR-EGR-05). Phần riêng của ứng dụng: màn hình nói rõ giới hạn (AP-SH-04). | AP-SH-04, AP-AL-09, AP-ST-07 |
| **AP-D-05** | Ưu tiên kênh Zalo so với Telegram? | **Đã quyết (Q-91 (7)):** Telegram và push không nội dung trước; Zalo giữ P1 (FR-CH-01). Bối cảnh cũ: Lời duyệt gắn với `chat:telegram:<id>` (RFC-0019, Q-89); duyệt qua Zalo cần mở rộng bot duyệt (sửa RFC). FR-CH-01: Telegram trước, Zalo sau (P1). Gia đình ở Việt Nam dùng Zalo là nhận định sản phẩm, chưa đo. Còn mở: thứ tự cho cảnh báo. | AP-AL-06 |
| **AP-D-06** | Luật mặc định theo loại sinh thành tệp tường minh, có chấp nhận không? | **Đã quyết (CONTRIBUTING.md §3), xác nhận ở Q-91 (11):** Không cần RFC: gate cho thiết bị mới do `neuroedge add part` sinh (VP-PT-07), thêm gate vào `gates/` là PR thường (`CONTRIBUTING.md` §3), mặc định về giá trị chỉ do Blueprint khai (MS-CT-06). Mặc định ngầm trong runtime vẫn cần RFC. Cách khóa gate sinh ra: AP-D-15. | AP-KD-01, AP-KD-02 |
| **AP-D-07** | Thời gian chờ mặc định của chuỗi leo thang và ngưỡng hộp im lặng? | **Đã quyết (Q-91 (7)):** chuỗi leo thang hoãn cùng ngành dọc người cao tuổi (Q-72, R-19); thời gian chờ và ngưỡng im lặng đặt khi ngành dọc mở. Bối cảnh cũ: Chưa có đặc tả đã duyệt cho chuỗi leo thang (MS-RT-07 là cảnh báo mẫu cố định, không xác nhận). Thảo luận thiết kế nêu ví dụ 2 phút (hỏi tại chỗ), 5 phút (người thứ hai), 10 phút (relay); chỉ là ví dụ chưa quyết. | AP-AL-03, AP-AL-09 |
| **AP-D-08** | "Chặn oan" định nghĩa thế nào; ngưỡng đạt của ba chỉ số là bao nhiêu? | **Đã quyết (Q-91 (10)):** Q-85 (3) không sửa; chỉ số của ứng dụng (gồm "chặn oan") và ngưỡng là tiêu chí thoát của I2h, đặt bằng dữ liệu ra mắt (TSK-I2g-12; Q-92 bỏ cổng nhu cầu). Bối cảnh cũ (trước Q-92): K1–K5 trước cổng (Q-85 (3)); xem AP-D-16. BR-APP-10. | AP-MT-02, AP-MT-04 |
| **AP-D-09** | Chạy lại cấu hình đề xuất trên trace có cần RFC không? | **Đã quyết (CONTRIBUTING.md §3), xác nhận ở Q-91 (11):** Chạy chỉ đọc không nằm trong danh sách RFC của `CONTRIBUTING.md` §3; sự kiện trace mới cho đoạn trace thì cần RFC (TSK-I2d-13). Studio đã có `POST /api/gates/<name>/whatif` và `POST /api/traces/<name>/replay` (`docs/spec/studio.md`). | AP-WI-01, AP-WI-02 |
| **AP-D-10** | Studio đang tạm dừng (Q-72): tái dùng làm nền ứng dụng hay xây trang riêng? | **Đã quyết (Q-91 (4)):** Studio mở lại làm trang web máy tính cho maker; ứng dụng và Studio dùng chung một API hộp (TSK-I2g-05). Bối cảnh cũ: Studio chỉ nghe 127.0.0.1 và đang tạm dừng (`docs/spec/studio.md`); xem AP-D-12. | AP-SH-01 |
| **AP-D-11** | Trình duyệt hỗ trợ và ngưỡng thời gian phản hồi? | **Đã quyết (Q-91 (2)):** hai bản chính mới nhất của iOS và Android; ngưỡng hiệu năng đặt trong thiết kế I2g, đo trên điện thoại thật. Chưa có số liệu. | AP-NF-06 |
| **AP-D-12** | Điện thoại tới được một trang có xác thực của hộp bằng cách nào, và một lần chạm trong ứng dụng mang nguồn duyệt nào? | **Đã quyết (Q-91 (3), (5)):** hộp phục vụ API có xác thực trong mạng nhà; điện thoại ghép một lần bằng mã dùng một lần hiện trên hộp (như Q-89); ngoài nhà duyệt qua bot của hộp (RFC-0019); một lần chạm có sinh trắc là nguồn người mới, cần RFC và mục `threat_model.md` (TSK-I2g-01). Bối cảnh cũ: Trang cục bộ (`run --ui`, `mcp serve --ui`, Studio) chỉ phục vụ trên 127.0.0.1 và từ chối `Host`/`Origin` khác (`docs/spec/studio.md` §2, DP-A-02). Để điện thoại trong mạng nhà tới được, ứng dụng cần: địa chỉ nghe khác, kiểm `Host`/`Origin` mới, cách ghép thiết bị ứng dụng (`pairing.py` ghép bộ não, `pair owner` ghép chủ, Q-89), và một mục `threat_model.md` do kỹ sư trưởng duyệt (như VP-PM-06). Nguồn người hợp lệ hiện là `local_grammar`, `ui` và `chat:<kênh>:<id>` khi bản ghi xác minh được (RFC-0019). Hoặc ứng dụng chỉ dùng bot duyệt trên Telegram. | AP-SH-01, AP-SH-02, AP-SH-04, AP-AV-04, AP-ST-05 |
| **AP-D-13** | Giới hạn theo giá trị cảm biến (vùng khóa) lấy từ đâu? | **Đã quyết (Q-91 (8)):** một RFC thêm giới hạn giá trị (value limits) vào `board.v1`, là vùng khóa (TSK-I2g-02). Bối cảnh cũ: `board.v1` `envelope` chỉ có `window_s`, `max_on_ms_per_window`, `min_interval_ms`, `max_continuous_ms`; không có giới hạn giá trị (như 32 °C). Thêm vào là sửa `schemas/` (RFC, `CONTRIBUTING.md` §3). Chọn: (a) vùng khóa chỉ gồm những gì `board.v1` khai, hoặc (b) một RFC thêm giới hạn giá trị. | AP-ZN-01, AP-ZN-02 |
| **AP-D-14** | Chat của ứng dụng đi tới bộ não bằng đường nào? | **Đã quyết (Q-91 (6)):** chat đi qua kênh riêng của NeuroClaw (Q-83 (4)); lời duyệt không đi qua đó (TSK-I2g-11). Bối cảnh cũ: Q-83 (4) đặt chat, trí nhớ, kênh trong bộ não; FR-CH-01 đặt bộ chuyển kênh chat ở runtime; MS-RT-02: bộ não nối tới hộp qua MCP; RFC-0019: hộp không gửi câu hỏi qua bộ não. Chọn: cổng riêng của NeuroClaw, hoặc relay hộp tới bộ não (task mới). | AP-CH-01 |
| **AP-D-15** | Một lần duyệt của gia đình khóa gì với `agent.toml`, linh kiện và gate? | **Đã quyết (Q-91 (9)):** gia đình đổi được tham số hợp đồng và cả gate, linh kiện do trình hướng dẫn sinh; mỗi gate qua `neuroedge gate lint` và chỉ khóa bằng lời duyệt ký sinh trắc tại nhà; đường khóa cần RFC (TSK-I2g-04). Bối cảnh cũ: MS-AP-04, MS-AP-05 chỉ khóa hợp đồng (`missions.lock`); MS-AP-03: công cụ ghi duy nhất của hộp cho bộ não là `mission_draft_write`; gate khóa bằng `neuroedge gate lint` và `digests.lock` (`CHANGELOG.md` §3.3 mục 1, `CONTRIBUTING.md` §3). Cần quy định trước khi ứng dụng sinh gate hay linh kiện rồi đưa duyệt; gate sinh ra phải qua `gate lint`. | AP-CD-01, AP-DV-10, AP-DV-12, AP-KD-01 |
| **AP-D-16** | Có mở một `Q-N` sửa Q-85 (3) để thêm chỉ số của ứng dụng (BR-APP-10) không? | **Đã quyết (Q-91 (10)):** không sửa Q-85 (3); chỉ số của ứng dụng là tiêu chí thoát của I2g (TSK-I2g-12). Bối cảnh cũ: Q-85 (3): chỉ số trước cổng là K1–K5; Q-85 (2): gia đình tới sản phẩm qua Blueprint của maker trước cổng. Đến khi có `Q-N`, nhóm MT tạm dừng. | AP-MT-01 → AP-MT-04 |
| **AP-D-17** | Các dòng ứng dụng thêm vào thẻ (kết quả chạy lại, nhãn vùng, "khi hỏng", nhãn rủi ro) tính vào giới hạn 5 dòng thế nào, và dữ liệu trace có thuộc "đầu vào" của MS-AP-01 không? | **Đã quyết (Q-91 (8)):** thẻ duyệt giữ tối đa 5 dòng (MS-AP-01); phần bổ sung bên dưới không tính vào 5 dòng. Bối cảnh cũ: MS-AP-01: tối đa 5 dòng, cùng đầu vào cùng byte. | AP-CD-02, AP-WI-01 |

---

## 7. Phụ thuộc vào task hiện có

Mã đã có trong `roadmap/neuroedge-roadmap.md`, cộng các task do Q-91 mở và Q-92 chia làm hai increment (một dòng mỗi task; chi tiết và trạng thái ở roadmap §4.3.7, §4.3.8). Mã `TSK-I2g-06` → `TSK-I2g-13` giữ nguyên dù nay thuộc I2h.

**Task của I2g, API hộp và web nhà (sau ra mắt công khai, Q-92 (8)):**

| Task | Nội dung |
|:---|:---|
| TSK-I2g-01 | RFC: ghép điện thoại, bộ nghe API trên hộp và nguồn duyệt ký sinh trắc (sửa RFC-0006, RFC-0019; mục `threat_model.md`) |
| TSK-I2g-02 | RFC: giới hạn giá trị trong `board.v1` (vùng khóa) |
| TSK-I2g-03 | RFC: vùng vàng trong `blueprint.v1` (khoảng maker so với giới hạn giá trị; sửa BL-IN-04) |
| TSK-I2g-04 | RFC: khóa gate và linh kiện do ứng dụng sinh (`gate lint` cộng duyệt ký sinh trắc tại nhà) |
| TSK-I2g-05 | API hộp dùng chung cho web nhà và ứng dụng; web nhà cho gia đình; Studio mở lại làm trang web cho maker (TSK-I1-04) |
| TSK-I2f-08 | Duyệt ký bằng passkey trong web nhà, hộp tự xác minh chữ ký (chuyển từ I2f sang I2g theo Q-92 (9)); nguồn duyệt sinh trắc của app là TSK-I2g-01 |

**Task của I2h, app gốc (sau I2g, Q-92 (8)):**

| Task | Nội dung |
|:---|:---|
| TSK-I2g-06 | Vỏ ứng dụng React Native: ghép đôi, Nhà, Thiết bị, Chi tiết thiết bị, Cài đặt (MH-1, MH-3, MH-4, MH-7) |
| TSK-I2g-07 | Thẻ duyệt trong ứng dụng: ≤ 5 dòng cộng phần bổ sung, ký sinh trắc, đồng ý cài Blueprint (MH-2, MH-8) |
| TSK-I2g-08 | Hoạt động và chạy lại với trace hôm qua (MH-5) |
| TSK-I2g-09 | Trình hướng dẫn thiết bị sinh gate và linh kiện (MH-6), trên `sim` và board thật |
| TSK-I2g-10 | Push không nội dung qua APNs và FCM |
| TSK-I2g-11 | Kênh ứng dụng trong NeuroClaw (kho `letrongminh/neuroclaw`) |
| TSK-I2g-12 | Chỉ số của ứng dụng, "chặn oan" và ngưỡng hiệu năng từ dữ liệu ra mắt |
| TSK-I2g-13 | Bản thử: TestFlight và Google Play internal testing |

**Task đã có:**

| Task | Ứng dụng cần để |
|:---|:---|
| TSK-I2d-04, TSK-I2d-05 | Hợp đồng `mission.v1` và trình biên dịch, nền của thẻ và vùng (AP-CD, AP-ZN) |
| TSK-I2d-06 | Thẻ duyệt (AP-CD) |
| TSK-I2d-08, TSK-I2d-16 | Runtime chạy liên tục và giám sát bộ não; G2 trên `linux` (AP-NF-03, AP-AL) |
| TSK-I2d-09 | Bộ phát hiện cho trạng thái và cảnh báo (AP-HM, AP-AL) |
| TSK-I2d-11 | Nguồn chat và bản ghi duyệt có chữ ký, RFC-0019 (AP-AV, AP-CH) |
| TSK-I2d-12 | Bot duyệt riêng của hộp, `pair owner`, trần mỗi giờ, thu hồi (AP-SH-02, AP-AV, AP-ST-05, AP-AL-06) |
| TSK-I2d-13, TSK-I2d-14 | Trace theo đoạn cho nhật ký và chạy lại (AP-AC, AP-WI) |
| TSK-I2d-17 | `neuroedge lab doctor` cho bước "Thử trực tiếp" (AP-DV-07) |
| TSK-I2d-20, TSK-I2d-21 | Bước xác minh (MS-CH-06, MS-CH-07): cổng chỉ duyệt tại chỗ (AP-AV-03), "Tôi ổn" (AP-AL-05) |
| TSK-I2d-23, TSK-N0-07 | Công cụ MCP cho mọi worker, gồm `propose_mission`, và bề mặt công cụ đóng của nó (AP-CH-03) |
| TSK-I2d-25 | Bộ cài, `ui-link`, đường duyệt DP-A-05 (AP-SH-07, AP-AV-03) |
| TSK-I2d-30 | Danh mục linh kiện và `neuroedge add part` (AP-DV-06, AP-KD-01) |
| TSK-I2d-31 | Canvas kéo thả giai đoạn C, hoãn (AP-DV-06) |
| TSK-I2d-32 | Bản đồ chân cho bước đấu dây (AP-DV-08) |
| TSK-I2c-16 | Cơ cấu chấp hành từ xa và "off debt" (AP-DV-09, AP-DV-11) |
| TSK-I2e-01, TSK-I2e-03 | Blueprint và xem trước cài đặt (AP-CD-09, AP-KD-06) |
| TSK-I2e-07 | Mốc đo cục bộ theo FR-TEL-07 (AP-MT) |
| TSK-I2e-13 | Đã cắt (Q-92 (2); lưu ở `roadmap/archive/removed-tasks.md`): ảnh SD cho Pi và ghép bằng QR không còn; AP-SH-02 chỉ còn mã dùng một lần hiện trên hộp, cài hộp bằng CLI đến khi có web nhà |
| TSK-I2f-05 | Vai trò nhiều người (AP-AV-07, AP-ST-01) |
| TSK-I2f-08 | Passkey FR-CH-08 trong web nhà, nay thuộc I2g (bảng trên); duyệt sinh trắc của app đi song song (AP-AV-04) |
