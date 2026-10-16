# Ứng dụng di động NeuroEdge ("app nhà"): đặc tả yêu cầu phần mềm (SRS)

> **Bản nháp đề xuất**, 2026-10-16. **Chưa có quyết định (`Q-N`) nào cho ứng dụng này, chưa có task nào
> trong roadmap, và tài liệu này không đổi gì trong roadmap.** Cấu trúc theo ISO/IEC/IEEE 29148:2018 §9.6,
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
`docs/spec/blueprint.md`); ngành dọc chăm sóc người cao tuổi (hoãn bởi Q-72, rủi ro R-19; các yêu cầu AL
gắn "ngành dọc sau" chỉ là thiết kế chuẩn bị); ứng dụng gốc, Zalo Mini App và truy cập từ ngoài nhà (chờ
quyết định, AP-D-03, AP-D-04). Ứng dụng **không phát hiện bệnh, không phát hiện té ngã**; chỉ báo người
thân về thay đổi thói quen.

### 1.3 Định nghĩa

| Thuật ngữ | Nghĩa |
|:---|:---|
| **Hộp** | Máy chạy NeuroEdge tại nhà, phần tin cậy: gate, thiết bị, duyệt, trace, đường ra dữ liệu. |
| **Bộ não** | NeuroClaw (Q-78, Q-83): không tin cậy, nói với hộp qua MCP, không bao giờ duyệt. |
| **Thẻ duyệt** | Tóm tắt ≤ 5 dòng của một thay đổi, sinh từ cấu trúc đã biên dịch (MS-AP-01). |
| **Vùng xanh** | Giá trị trong khoảng chỉnh được do maker khai (MS-CT-06, BL-IN-04). |
| **Vùng vàng** | Giá trị ngoài khoảng maker nhưng trong giới hạn phần cứng; có nhãn rủi ro. **Chỉ tồn tại nếu AP-D-01 được chọn.** |
| **Vùng khóa** | Giá trị vượt giới hạn mà `board.v1` khai (envelope về thời gian bật/tắt, `safe_state`); không đổi được từ ứng dụng. Giới hạn theo giá trị cảm biến (như °C) chưa có trong `board.v1` (AP-D-13). |
| **Chạy lại trên trace** | Xem trước: chạy cấu hình đề xuất trên trace 24 giờ gần nhất, chỉ đọc ("what-if"). |
| **Đã biết** | Xác nhận một cảnh báo; khác với duyệt một thay đổi. |

### 1.4 Tài liệu tham chiếu

`01-user-stories.md`, `02-brd.md` · `docs/spec/missions.md` (Q-87) · `docs/spec/blueprint.md` (Q-86) ·
`docs/spec/studio.md` (Q-51) · `docs/spec/virtual_parts.md` (Q-84) · `docs/user/chat-voi-nha.md` ·
`docs/business/brd-ambient-intelligence.md` (Q-85) · `roadmap/neuroedge-prd.md` (Q-38, Q-72, Q-73, Q-74,
Q-77, Q-78, Q-80, Q-83 → Q-90; R-19) · RFC-0019 (`docs/rfc/0019-ban-ghi-duyet-co-chu-ky.md`), `docs/spec/deployment_profiles.md` (DP-A-05, DP-A-06, DP-COM-04 → DP-COM-09) · RFC-0014 (`docs/rfc/0014-du-kien-tu-tien-trinh-ngoai.md`), RFC-0018
(`docs/rfc/0018-co-cau-chap-hanh-tu-xa.md`) · `CONTRIBUTING.md` §3 (khi nào cần RFC) và §8.1.

---

## 2. Mô tả tổng quan

### 2.1 Bối cảnh

```
 người trong gia đình          ứng dụng (web di động)            hộp (tin cậy)                 bộ não (không tin cậy)
 ────────────────────          ──────────────────────            ─────────────                 ──────────────────────
 xem, chat, chỉnh, duyệt ───►  hiển thị, soạn thẻ chờ duyệt ───► gate · hợp đồng · trace         soạn, hỏi lại, trả lời
                                                                 duyệt (đúng người, đúng digest) ◄── MCP ──► (không duyệt)
                       ◄───── thẻ, cảnh báo, nhật ký ◄────────── đường ra dữ liệu duy nhất (MS-EG-01)
```

**Ranh giới tin cậy.** Ứng dụng chỉ nói chuyện với hộp. Bộ não không có đường nào để duyệt, khóa hay ghi
gate (MS-RT-04, MS-CH-05, FR-CH-05). Ứng dụng chỉ hiển thị và chuyển lời duyệt của người; hộp tự tính lại
mọi phán quyết, kể cả vùng màu (AP-ZN-07). Lời duyệt từ xa chỉ đến từ bot duyệt riêng của hộp, bằng bản ghi do hộp ký (DP-A-06, RFC-0019); một lần chạm trong ứng dụng chưa phải nguồn duyệt hợp lệ nào (AP-D-12).

### 2.2 Tám màn hình mẫu

| Mã | Màn hình | Nội dung chính |
|:---|:---|:---|
| **MH-1** | Nhà | Biểu ngữ khẩn; thẻ "Bể cá phòng khách" (26,8 °C, "Ổn"); thẻ "Nhà bố mẹ" ("Cần chú ý", mẫu ngành dọc sau cổng); dòng "1 đề xuất chờ bạn duyệt"; thanh tab Nhà, Chat, Thiết bị, Hoạt động, Cài đặt. |
| **MH-2** | Chat | Hỏi về bể; thẻ đề xuất "Không bật sưởi khi nước từ 28 °C" (đang 29 °C) với nhãn vùng, "Nếu áp dụng hôm qua: chặn thêm 1 lần", nút Chỉnh / Duyệt; gợi ý nhanh. |
| **MH-3** | Thiết bị | Nhóm theo không gian; máy sưởi, máy sục khí có khóa, nhiệt độ nước; thiết bị nhà bố mẹ; "Thêm thiết bị". |
| **MH-4** | Chi tiết máy sưởi | Biểu đồ 24 giờ với đường ngưỡng; luật dạng câu có nhãn vùng; giới hạn phần cứng khóa; lần chặn gần nhất; thanh trượt ba vùng. |
| **MH-5** | Hoạt động | Bộ lọc Tất cả / Bị chặn / Cảnh báo / Đã duyệt; nhật ký; "Chạy lại hôm qua với luật hiện tại". |
| **MH-6** | Thêm thiết bị, bước 3/5 | "Thử trực tiếp": cảm biến cửa, mở rồi đóng một lần, thấy sự kiện. |
| **MH-7** | Cài đặt | Người trong gia đình và vai trò; kênh báo; ngân sách AI; rủi ro đang bật; relay canh hộp. |
| **MH-8** | Duyệt Blueprint (mẫu dạng thông báo) | Thẻ "Hộp bể cá sẽ:" ba câu; nguồn của digest (BL-IN-02) và bằng chứng ghi "unsigned" (BL-EV-03); chạm để duyệt; Xem chi tiết / Từ chối. Cơ chế thông báo chưa quyết (AP-D-03). |

Số liệu trong màn hình mẫu (nhiệt độ, giờ, "0,40 / 2 USD", "30 giây trước") là **dữ liệu minh họa**, không
phải mặc định hay ngưỡng của sản phẩm. Các thẻ, thiết bị và mục "Nhà bố mẹ" và relay canh hộp (MH-1, MH-3, MH-7) là
mẫu của ngành dọc sau cổng nhu cầu (Q-72, R-19), không thuộc phạm vi trước cổng.

### 2.3 Ứng dụng dựa trên những gì đã có

- `python/neuroedge/studio/` (`neuroedge studio`, Q-51; hợp đồng `docs/spec/studio.md`): trang web cục bộ chỉ nghe 127.0.0.1 (`docs/spec/studio.md` §2)
  với `/api/agent`, `/api/gates…`, `/api/traces…`, `/api/record`, `/api/lint`, `/api/verify`, `/api/test`,
  `/api/device…`. **Đang tạm dừng** bởi Q-72 (PRD §14).
- `python/neuroedge/viz/` và `python/neuroedge/sim/ui.py`: trang trực tiếp của `run --ui` và `mcp serve
  --ui`; `neuroedge ui-link` in liên kết một lần tới trang nhà (`docs/user/chat-voi-nha.md`). Các trang này chỉ phục vụ
  trên 127.0.0.1 (`sim/ui.py`); DP-A-02 đòi `Origin` của chính máy chủ và khóa riêng mỗi lần chạy.
- `python/neuroedge/pairing.py`: ghép **bộ não** với hộp qua mạng (khóa của hộp, `pair renew`, `pair rotate`;
  token của bộ não sống tối đa 7 ngày, DP-A-04). Ghép **chủ hộp** là việc khác: `neuroedge pair owner`, mã dùng
  một lần hiện trên hộp (Q-89, RFC-0019, TSK-I2d-12). Chưa có thiết kế đã duyệt cho thông tin xác thực riêng của
  ứng dụng (AP-D-12).
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
4. Danh sách trình duyệt hỗ trợ và ngưỡng hiệu năng: chưa xác định (AP-D-11).

---

## 3. Yêu cầu

Phương pháp kiểm chứng: **T** thử nghiệm, **D** trình diễn, **I** kiểm tra bằng đọc, **A** phân tích.
Yêu cầu cần RFC nêu rõ "(cần RFC)" theo `CONTRIBUTING.md` §3. Nơi "Nguồn" ghi mã `MS-*`, `BL-*`, `FR-*`, yêu
cầu đó **dựa vào** mã ấy và không chép lại.

### 3.1 Vỏ ứng dụng, ghép đôi, truy cập (SH)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-SH-01 | Bản đầu của ứng dụng phải là web di động, truy cập bằng trình duyệt, không cần cài từ kho ứng dụng. Cách điện thoại tới được một trang có xác thực của hộp chưa có quyết định: trang cục bộ hiện chỉ phục vụ trên 127.0.0.1 và từ chối `Host`/`Origin` khác; phục vụ trong mạng nhà là một quyết định an ninh mới, cần mục `threat_model.md` và kỹ sư trưởng duyệt (AP-D-12). | Ít phụ thuộc nhất để đạt cổng nhu cầu; dạng cuối còn chờ quyết định. | BR-APP-01, BR-APP-02; US-APP-01; Q-51, Q-72; `docs/spec/studio.md` §2, DP-A-02; AP-D-03, AP-D-12 | D |
| AP-SH-02 | Ghép chủ hộp phải theo Q-89: mã dùng một lần (8 ký tự, 10 phút) chỉ hiện trên máy nhà (CLI hoặc trang cục bộ), gửi cho bot duyệt của hộp bằng `/pair <mã>` từ cuộc chat riêng; ứng dụng không tạo cơ chế ghép thứ hai. `python/neuroedge/pairing.py` ghép bộ não, không ghép người. Thiết bị chưa ghép chỉ thấy màn hình ghép đôi. Thông tin xác thực riêng của ứng dụng với hộp chưa có thiết kế đã duyệt (AP-D-12). | Một đường ghép người, mã chỉ hiện tại nhà. | BR-APP-04; US-APP-06; Q-89, RFC-0019, FR-CH-03, MS-CH-01, TSK-I2d-12; AP-D-12 | T |
| AP-SH-03 | Ứng dụng chỉ được nói chuyện với hộp; không gọi trực tiếp bộ não hay dịch vụ ngoài. | Hộp là đường ra dữ liệu duy nhất. | BR-APP-04; US-APP-03; MS-EG-01, FR-EGR-01 | T |
| AP-SH-04 | Phần xem và duyệt tại nhà phải chạy không cần Internet. Truy cập từ ngoài nhà không thuộc bản đầu; màn hình phải nói rõ giới hạn đó. Việc điện thoại tới hộp trong mạng nhà: AP-D-12. | Truy cập ngoài nhà cần relay hoặc cloud (Q-74). | BR-APP-07; US-APP-18; Q-74, NFR-REL-05; AP-D-04, AP-D-12 | D |
| AP-SH-05 | Thanh tab dưới phải có năm mục Nhà, Chat, Thiết bị, Hoạt động, Cài đặt; phần của maker phải nằm ở nơi riêng, không lẫn trong năm tab này. | Người dùng gia đình không thấy công cụ của maker. | BR-APP-09, BR-APP-01; US-APP-16 | I |
| AP-SH-06 | Ở mặc định, ứng dụng không được hiện YAML, digest, `board.v1`, mã lỗi hay số chân; chi tiết chỉ hiện sau "Xem chi tiết", và số chân chỉ hiện trong bước đấu dây. | Che thuật ngữ nhưng vẫn mở được chi tiết. | BR-APP-01; US-APP-01, US-APP-08, US-APP-09; MS-AP-01 | I |
| AP-SH-07 | Liên kết vào trang nhà do `neuroedge ui-link` cấp phải dùng một lần; liên kết cũ hết hiệu lực khi cấp liên kết mới. | Không để lại đường vào dùng lại được. | BR-APP-04; US-APP-06; `docs/user/chat-voi-nha.md` | T |

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
| AP-CH-01 | Ứng dụng không giữ khóa LLM, và hộp không gửi câu hỏi duyệt qua bộ não. Đường tin nhắn chat của ứng dụng tới bộ não chưa được xác định: Q-83 (4) đặt chat, trí nhớ và kênh trong bộ não, còn FR-CH-01 đặt bộ chuyển kênh chat ở runtime; cần chọn giữa cổng riêng của NeuroClaw và một relay hộp tới bộ não mới (AP-D-14). | Khóa nằm ở bộ não, không ở ứng dụng. | BR-APP-04; US-APP-03; FR-CH-01, MS-RT-04, Q-83, RFC-0019; AP-D-14 | I |
| AP-CH-02 | Mỗi con số trong câu trả lời về nhà phải mở được sự kiện gốc trong nhật ký; con số không có sự kiện gốc phải bị đánh dấu là không có nguồn. | Câu trả lời "dựa trên số liệu thật" phải kiểm được. | BR-APP-01, BR-APP-08; US-APP-03; MS-TS-01 | T |
| AP-CH-03 | Điều người dùng muốn đổi, nói trong chat, phải thành thẻ đề xuất qua luồng thẻ duyệt (AP-CD); không được áp dụng trực tiếp từ chat. | Một đường duyệt duy nhất. | BR-APP-02; US-APP-04; MS-AP-04, TSK-I2d-23 | T |
| AP-CH-04 | Lời "Có" hay "Đồng ý" gõ vào chat không trả lời một yêu cầu duyệt đang chờ thì không được duyệt gì. | Tin nhắn chat là yêu cầu, không phải sự đồng ý. | BR-APP-04; US-APP-04, US-APP-06; MS-CH-02 | T |
| AP-CH-05 | Khi bộ não ngừng, tab Chat phải hiện "phân tích tạm ngưng"; các tab còn lại phải dùng được bình thường. | Mất bộ não chỉ mất phần phân tích. | BR-APP-08; US-APP-03; MS-RT-02, NFR-REL-05 | T |
| AP-CH-06 | Khi ngân sách phân tích hết, tab Chat phải báo "đã hết ngân sách phân tích kỳ này"; thiết bị và cảnh báo khẩn phải vẫn chạy. | Ngân sách chỉ dừng phân tích. | BR-APP-08; US-APP-14; MS-RT-06, NFR-REL-05 | T |

### 3.4 Thẻ duyệt chung (CD)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-CD-01 | Mọi thay đổi của hợp đồng (đề xuất từ chat, chỉnh thanh trượt) phải hiện qua cùng một thẻ duyệt và cùng quy trình bản nháp, kiểm tra, thẻ, duyệt, khóa. MS-AP-04 và MS-AP-05 chỉ nói về hợp đồng (`missions.lock`); thêm hoặc gỡ thiết bị và đổi `agent.toml`, linh kiện, gate chưa có đường khóa đã duyệt, vì gate khóa bằng `neuroedge gate lint` và `digests.lock` (AP-D-15). Cài Blueprint theo AP-CD-09, không theo quy trình này. | Một đường kiểm duy nhất. | BR-APP-02; US-APP-04, US-APP-05, US-APP-09, US-APP-15; MS-AP-04, MS-AP-05; AP-D-15 | T |
| AP-CD-02 | Nội dung thẻ phải là thẻ do hộp sinh (≤ 5 dòng tiếng Việt thường); ứng dụng không được tự soạn hay sửa câu chữ của thẻ. Các dòng ứng dụng muốn thêm (AP-WI-01, AP-CD-04) tính vào giới hạn 5 dòng thế nào, và dữ liệu trace có thuộc "đầu vào" của MS-AP-01 (cùng đầu vào, cùng byte) không: chưa xác định (AP-D-17). | Thẻ sinh từ cấu trúc đã biên dịch, không từ LLM. | BR-APP-02, BR-APP-01; US-APP-04; MS-AP-01; AP-D-17 | T |
| AP-CD-03 | Thẻ quá dài để duyệt qua chat phải ghi phải duyệt tại nhà, và việc duyệt chỉ được thực hiện tại chỗ với toàn bộ khác biệt. | Thay đổi dài cần đọc đủ. | BR-APP-02; US-APP-04; MS-AP-02 | T |
| AP-CD-04 | Thẻ phải hiện nhãn vùng của từng con số, trạng thái "khi hỏng" của thiết bị có trạng thái an toàn khác tắt, và các nhãn rủi ro có liên quan (các nhãn mà tài liệu đã duyệt định nghĩa, xem AP-ST-04). Tóm tắt duyệt phải mang câu Q-38 (R-19). | Người duyệt thấy rủi ro họ nhận. | BR-APP-02, BR-APP-03, BR-APP-08; US-APP-05, US-APP-14; MS-SF-06, MS-SF-05, DP-COM-06, Q-73, Q-38, R-19 | I |
| AP-CD-05 | Một thay đổi chưa được duyệt phải không có hiệu lực lên thiết bị hay luật. | Thẻ chỉ là đề xuất. | BR-APP-02, BR-APP-04; US-APP-04, US-APP-15; MS-AP-04, BL-IN-05 | T |
| AP-CD-06 | Lời duyệt phải gắn với digest của chính thay đổi đang hiển thị; hộp phải từ chối lời duyệt cho digest khác. | Digest được duyệt là digest chạy. | BR-APP-04; US-APP-06; MS-AP-05, MS-CH-03 | T |
| AP-CD-07 | Thẻ hết hạn phải bị coi là không duyệt. | Lời duyệt cũ không còn giá trị. | BR-APP-04; US-APP-06; MS-CH-04 | T |
| AP-CD-08 | Mỗi thẻ phải có nút "Xem chi tiết" mở khác biệt đầy đủ và giải thích gate (`neuroedge gate explain`). | Người chịu trách nhiệm mở được chi tiết. | BR-APP-01; US-APP-08, US-APP-15; `python/neuroedge/engine/gate_explain.py` | D |
| AP-CD-09 | Thẻ cài Blueprint phải hiện tóm tắt do hộp sinh theo BL-IN-03 (gồm đích mạng, nhãn rủi ro, và mỗi bằng chứng ghi "unsigned" theo BL-EV-03), cho biết digest được đối chiếu với `--digest`, chỉ mục, hay in ra để người xác nhận (BL-IN-02), và mang câu Q-38; thẻ không ghi "đã qua Action CI" hay "đã kiểm chứng". Không chạy tệp nào của gói trước khi duyệt (BL-IN-05); gói được ghi vào thư mục mới, không bao giờ vào thư mục có sẵn không rỗng (BL-IN-06); nút Từ chối không cài gì. Cài Blueprint là bước người dùng tự chạy (`neuroedge blueprint show`/`install`, BL-IN-01); ứng dụng chỉ là mặt trước của lệnh đó. Gói khai đích mạng chỉ duyệt tại nhà (FR-MSN-14). | Cài đặt chỉ sau khi người đọc tóm tắt. | BR-APP-02; US-APP-15; BL-IN-01 → BL-IN-03, BL-IN-05, BL-IN-06, BL-EV-03, FR-MSN-14, R-19, TSK-I2e-03 | T |
| AP-CD-10 | Khi không đẩy được thông báo lên màn hình khóa, ứng dụng phải gửi tin qua kênh chat đã ghép kèm liên kết mở thẻ; liên kết chỉ dùng được khi trang tới được từ điện thoại (AP-D-12). Duyệt bằng nút của bot duyệt không cần liên kết (RFC-0019). | Đẩy thông báo trên web khó (đặc biệt iOS). | BR-APP-02; US-APP-15; FR-CH-01, RFC-0019; AP-D-03, AP-D-12 | D |

### 3.5 Ba vùng (ZN)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-ZN-01 | Mỗi con số chỉnh được phải thuộc đúng một trong ba vùng: **xanh** (trong khoảng maker khai), **vàng** (ngoài khoảng maker, trong giới hạn phần cứng) và **khóa** (vượt giới hạn mà `board.v1` khai, AP-ZN-02). Vùng vàng chỉ tồn tại khi AP-D-01 chọn cho phép. | Người dùng thấy mình ở đâu. | BR-APP-03; US-APP-05, US-APP-16; MS-CT-06, BL-IN-04, MS-CT-04; AP-D-01 | T |
| AP-ZN-02 | Vùng khóa phải lấy từ những gì `board.v1` khai: envelope về thời gian (`window_s`, `max_on_ms_per_window`, `min_interval_ms`, `max_continuous_ms`) và `safe_state` (MS-CT-04, MS-CP-02); không đổi được từ ứng dụng; giá trị vượt phải làm nút duyệt vô hiệu và ghi "Vượt giới hạn phần cứng". `board.v1` chưa có giới hạn theo giá trị cảm biến (như °C); thêm vào là sửa `schemas/` (cần RFC, `CONTRIBUTING.md` §3), nên chưa có vùng khóa kiểu đó (AP-D-13). | Hợp đồng không nới được envelope. | BR-APP-03; US-APP-05; MS-CT-04, MS-CP-02, FR-ACE-03, `schemas/board.v1.json`; AP-D-13 | T |
| AP-ZN-03 | Vùng xanh phải lấy từ khoảng chỉnh được (kiểu và khoảng) mà maker khai trong tham số `ask` hay tham số cài đặt. | Người cài chỉ chỉnh trong khoảng đã kiểm chứng. | BR-APP-03, BR-APP-09; US-APP-05, US-APP-16; MS-CT-06, BL-IN-04 | T |
| AP-ZN-04 | (Nếu AP-D-01 cho phép) Giá trị ở vùng vàng phải hiện nhãn rủi ro, đổi nút thành "Duyệt, chấp nhận rủi ro", và việc chấp nhận phải ghi vào trace. | Q-73: nhãn rủi ro thay cho cấm đoán; bất biến (c). | BR-APP-03, BR-APP-08, BR-APP-10; US-APP-05, US-APP-14; Q-73; AP-D-01 | T |
| AP-ZN-05 | Thanh trượt phải hiện ba vùng bằng màu, chữ và biểu tượng; không được dùng màu làm tín hiệu duy nhất. | Người không phân biệt màu vẫn đọc được. | BR-APP-03; US-APP-05 | I |
| AP-ZN-06 | Vùng xanh không được ghi "an toàn"; nhãn phải là "Trong khoảng maker cho phép". | Tránh hiểu nhầm là chức năng an toàn được chứng nhận. | BR-APP-03; US-APP-05; Q-38, R-19 | I |
| AP-ZN-07 | Khi nhận lời duyệt, hộp phải tự tính lại vùng của từng giá trị và không tin vùng do ứng dụng gửi; giá trị ở vùng khóa phải bị từ chối bất kể ứng dụng gửi gì. | Ứng dụng chỉ hiển thị; hộp quyết định. | BR-APP-03, BR-APP-04; US-APP-05; MS-CP-02, MS-CT-04 | T |
| AP-ZN-08 | Tham số cài đặt của Blueprint chỉ được ghi vào dữ kiện, luật cảm biến hoặc linh kiện; một tham số nhắm vào gate phải làm gói không hợp lệ. | Luật đã kiểm chứng không bị chỉnh. | BR-APP-03, BR-APP-09; US-APP-16; BL-IN-04 | T |

### 3.6 Duyệt và xác minh (AV)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-AV-01 | Chỉ chủ hộp đã ghép theo Q-89 mới duyệt được; bộ não, ứng dụng MCP, nhóm chat và nguồn tự động không được có đường nào để duyệt. | AI không duyệt. | BR-APP-04; US-APP-06; FR-CH-05, MS-CH-05, MS-RT-04, MS-CH-07, Q-89, RFC-0019 | T |
| AP-AV-02 | Một bản ghi duyệt giả gửi qua MCP phải bị hộp từ chối và ghi vào trace. | Bất biến Q-73 (a). | BR-APP-04; US-APP-06; MS-CH-05, Q-73 | T |
| AP-AV-03 | Duyệt hành động vật lý phải đi qua hộp bằng một trong hai đường đã duyệt: trang cục bộ tại nhà, hoặc nút của bot duyệt riêng của hộp với bản ghi duyệt do hộp ký (nonce dùng một lần, hạn dùng, digest của gate). Mọi `ask` được trả lời từ xa, trong trần, TTL và nhãn `risk=remote_approval`; cổng chỉ duyệt tại chỗ chờ TSK-I2d-20. | Không có đường duyệt nào nhờ bộ não; không chặn người dùng vì thiếu vân tay. | BR-APP-04; US-APP-06; DP-A-05, DP-A-06, RFC-0019, Q-89, MS-CH-03, MS-AP-05, `docs/user/chat-voi-nha.md` | T |
| AP-AV-04 | Vân tay (passkey) là phương thức xác minh sau, không phải tiền đề của ứng dụng. Khi có (FR-CH-08, TSK-I2f-08), ứng dụng phải cho duyệt bằng vân tay; hộp giữ khóa công khai và xác minh cục bộ, đám mây không giả mạo được lời duyệt. RFC-0019 giữ passkey là phương thức sau và nó khớp thiết kế bản ghi hiện có; `trace.v1` đã cho phép khóa phụ trong `data`, không đổi tệp schema nào. Một lần chạm trong ứng dụng mang nguồn nào (trang `ui` hay nguồn mới) chưa có quyết định (AP-D-12). | Vân tay là cách duyệt người dùng chọn, sau này. | BR-APP-04; US-APP-06; FR-CH-08, TSK-I2f-08, RFC-0019; AP-D-02, AP-D-12 | T |
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
| AP-DV-06 | Trình hướng dẫn thêm thiết bị phải chọn loại từ danh mục (`python/neuroedge/hal/parts.toml`) và ghi kết quả tương đương `neuroedge add part` (linh kiện, mục `[requires]`, và với kiểu ra: hành động, gate fail-closed, kiểm thử hai chiều; VP-PT-07), không bắt người dùng viết cấu hình. Chỉ trên `sim`, ghi `[sim.parts]`. Thiết bị trên board thật cần `[targets.<board>.pins]` (VP-PM-01; PR cần kỹ sư trưởng duyệt, VP-PM-06) và là canvas giai đoạn C của Q-84, hoãn (TSK-I2d-31). | Bỏ rào cản cấu hình. | BR-APP-06; US-APP-09; Q-84, VP-PT-07, VP-PM-01, VP-PM-06, TSK-I2d-31, `python/neuroedge/templates/add_part.py` | T |
| AP-DV-07 | Bước "Thử trực tiếp" phải hiện sự kiện thật hộp nhìn thấy (ví dụ mở lúc 15:42:08, đóng lúc 15:42:11) trước khi cho sang bước tiếp. Đọc từng cảm biến dùng `neuroedge lab doctor` (MS-LB-02, TSK-I2d-17). | Thiết bị phải chứng minh nó hoạt động. | BR-APP-06; US-APP-09 | D |
| AP-DV-08 | Ở bước đấu dây, ứng dụng phải chỉ cách đấu bằng lời ("dây đỏ vào chân số 3") lấy từ bản đồ chân của board; đây là nơi duy nhất ở mặc định được hiện số chân. Đường này cho board thật nên thuộc giai đoạn C (AP-DV-06). | Người đấu dây cần số chân; chỗ khác thì không. | BR-APP-06, BR-APP-01; US-APP-09; TSK-I2d-32, `python/neuroedge/hal/pin_map.py` | D |
| AP-DV-09 | Đường cảm biến không dây phải ghi rõ chưa dùng được cho đến khi dữ kiện từ tiến trình ngoài có code (RFC-0014 đã duyệt 2026-10-04; code hoãn sau v1.0); không được giả vờ đã thêm. Cơ cấu chấp hành từ xa đã có qua Home Assistant (RFC-0018, TSK-I2c-16) ở mức skill (MS-CP-04); trình hướng dẫn không được mô tả chúng là chưa dùng được. | Code của RFC-0014 hoãn sau v1.0. | BR-APP-06; US-APP-09; RFC-0014, RFC-0018, TSK-I2c-16, MS-CP-04 | I |
| AP-DV-10 | Kết thúc trình hướng dẫn phải tạo một thẻ duyệt (AP-CD-01); thiết bị mới không có hiệu lực trước khi được duyệt. | Một đường duyệt duy nhất. | BR-APP-02, BR-APP-06; US-APP-09; MS-AP-04 | T |
| AP-DV-11 | Gỡ thiết bị phải đưa nó về trạng thái an toàn trước khi gỡ (tắt về an toàn không bao giờ bị từ chối); hộp chỉ tắt cái hộp đã bật. | "Off debt" của hộp. | BR-APP-06; US-APP-10; `python/neuroedge/hal/remote.py`, RFC-0018, TSK-I2c-16 | T |
| AP-DV-12 | Trước khi gỡ, ứng dụng phải liệt kê luật và hợp đồng đang dùng thiết bị và cảnh báo; việc gỡ phải qua thẻ duyệt. | Không gỡ làm hỏng luật. | BR-APP-06, BR-APP-02; US-APP-10; MS-AP-04 | T |
| AP-DV-13 | Gỡ thiết bị không được xóa lịch sử trace của nó trong thời gian giữ trace. | Nhật ký còn đọc được sau khi gỡ. | BR-APP-06, BR-APP-08; US-APP-10; MS-TS-03 | T |

### 3.9 Luật mặc định theo loại thiết bị (KD)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-KD-01 | Gate cho thiết bị mới phải do `neuroedge add part` sinh (VP-PT-07: hành động, gate fail-closed, kiểm thử hai chiều); ứng dụng không có bộ sinh gate thứ hai. Mặc định về giá trị của hợp đồng chỉ được có khi một Blueprint khai (MS-CT-06, FR-MSN-13, `parameters` của BL-IN-04); không được là mặc định ngầm trong runtime, vì đổi ngữ nghĩa gate cần RFC. | Một sự thật một chỗ; luật chạy đúng như đã khai. | BR-APP-06, BR-APP-02; US-APP-09; Q-73, MS-CT-06, FR-MSN-13, VP-PT-07, BL-IN-04, CONTRIBUTING.md §3; AP-D-06 | T |
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
| AP-AL-02 | Cảnh báo trên ứng dụng phải có nút "Đã biết"; bấm là xác nhận của người đã ghép, ghi vào trace và dừng chuỗi leo thang. "Đã biết" không áp dụng thay đổi nào. Chưa có quy định đã duyệt cho "Đã biết" và chuỗi leo thang: MS-RT-07 chỉ có cảnh báo mẫu cố định, không xác nhận, và danh sách sự kiện trace của MS-TS-04 không có sự kiện xác nhận; thuộc sau cổng, cần RFC sự kiện trace (mở rộng TSK-I2d-13). | Xác nhận khác duyệt. | BR-APP-07; US-APP-02; FR-CH-04 | T |
| AP-AL-03 | Chuỗi leo thang (ngành dọc sau) phải theo danh sách người có thứ tự và thời gian chờ chỉnh được: hỏi tại chỗ trước, rồi người thứ nhất qua nhiều kênh, chưa xác nhận thì người kế, lặp đến khi có xác nhận. Thêm sự kiện trace hay trường mới thì cần RFC. Thời gian chờ mặc định chưa xác định (AP-D-07). Chưa có task; sau cổng nhu cầu. | Cảnh báo chắc chắn đến nơi. | BR-APP-07; US-APP-02, US-APP-12; MS-RT-07, MS-TS-04, CONTRIBUTING.md §3; AP-D-07 | T |
| AP-AL-04 | Ứng dụng phải hiện chuỗi leo thang đang ở bước nào và giờ của bước kế. | Người nhận biết còn bao lâu. | BR-APP-07; US-APP-02 | D |
| AP-AL-05 | Câu hỏi tại chỗ (ngành dọc sau) phải nhận "Tôi ổn" từ thiết bị cục bộ đã ghép (nút bấm hoặc trang cục bộ; giọng nói đã bỏ, Q-77); tín hiệu từ bộ não hay ứng dụng MCP phải bị coi là không hợp lệ. | Xác minh nghĩa là một con người. | BR-APP-07; US-APP-17; MS-CH-07, FR-CH-05, Q-73, TSK-I2d-20, TSK-I2d-21 | T |
| AP-AL-06 | Telegram phải là kênh báo đầu tiên; mỗi kênh thêm (Zalo, SMS qua 4G, gọi tự động) phải là một đích khai báo, chỉ thêm được khi duyệt tại nhà. | Đích dữ liệu mới không duyệt qua chat. | BR-APP-07; US-APP-13; FR-CH-01, TSK-I2d-12, MS-EG-01, MS-AP-04; AP-D-05 | T |
| AP-AL-07 | Khi kênh chat sập, cảnh báo phải hiện ở trang cục bộ và nằm trong hàng đợi giữ giờ gốc. | Cảnh báo không mất. | BR-APP-07; US-APP-13; MS-RT-08 | T |
| AP-AL-08 | Người nhận leo thang chỉ nhận cảnh báo khẩn và không có quyền duyệt. Người nhận khác chủ hộp cần FR-CH-07 (TSK-I2f-05): Q-89 chỉ ghép một chủ, và nhóm chat không bao giờ ghép (MS-CH-01). | Quyền tối thiểu. | BR-APP-07; US-APP-12, US-APP-18; FR-CH-07 | T |
| AP-AL-09 | Hộp mất liên lạc phải được báo cho người nhận kèm giờ tín hiệu cuối; việc canh phải do relay ngoài nhà làm, nên cần relay hoặc cloud (Q-74 bước 2, sau cổng nhu cầu); FR-EGR-05 định relay là đường hầm TLS trong suốt, chưa có nhiệm vụ canh hộp. Ngưỡng im lặng chưa xác định (AP-D-07). | Hộp chết thì không tự báo được. | BR-APP-07; US-APP-18; FR-EGR-05, Q-74; AP-D-04, AP-D-07 | T |
| AP-AL-10 | Câu chữ cảnh báo của ngành dọc người cao tuổi chỉ được nói về thay đổi thói quen; không chẩn đoán, không nói té ngã. | Rủi ro pháp lý và y tế. | BR-APP-07; US-APP-02, US-APP-17; Q-72, Q-38, R-19 | I |

### 3.12 Cài đặt, rủi ro, ngân sách (ST)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-ST-01 | Cài đặt phải hiện người trong gia đình và vai trò (duyệt, khẩn cấp, báo sau N phút); trước khi có đa người dùng, ứng dụng phải chạy ở chế độ một chủ hộp. | FR-CH-07 mới ở mức dự kiến. | BR-APP-07; US-APP-12; FR-CH-07, TSK-I2f-05, Q-89 | D |
| AP-ST-02 | Thay đổi vai trò hay thứ tự leo thang phải qua thẻ duyệt và chỉ chủ hộp được duyệt. | Quyền không tự nới. | BR-APP-07, BR-APP-02; US-APP-12; MS-AP-04 | T |
| AP-ST-03 | Ngân sách AI phải hiện đã dùng trên trần của kỳ, lấy từ ngân sách `llm` của hợp đồng; số tiền (USD) là số bộ não báo, hộp không thấy hóa đơn LLM (Q-87, MS-RT-06) và màn hình phải ghi rõ như vậy. | Người dùng thấy chi phí. | BR-APP-08; US-APP-14; MS-CT-05, MS-RT-06, NFR-COST-01 | T |
| AP-ST-04 | Danh sách "rủi ro đang bật" phải liệt kê mọi nhãn rủi ro đang có hiệu lực theo định nghĩa của các tài liệu đã duyệt, và nguồn của từng nhãn: `risk=remote_approval` (RFC-0019), `risk=virtual_board` (Q-84), `risk=simulated_interlock` (MS-SF-05, ví dụ máy sục khí của bể cá trên `sim`), `risk=single_chip`, `risk=readable_flash` (Q-79) và các nhãn riêng của bộ não (Q-80); chúng được in lúc khởi động và hiện ở `status` (DP-COM-06). | Minh bạch thay cho cấm đoán. | BR-APP-08; US-APP-14; Q-73, MS-EG-03, MS-CH-06, DP-COM-06, MS-SF-05, RFC-0019, Q-79, Q-80, Q-84 | T |
| AP-ST-05 | Người dùng phải thu hồi được chủ hộp đã ghép bằng `neuroedge pair owner --revoke` trên hộp, hoặc `/revoke` từ chủ đã ghép trên bot duyệt; `/revoke` chỉ thu hồi, không bao giờ cấp quyền. Chỉ có một chủ được ghép: ghép chủ mới thay chủ cũ. Danh sách nhiều thiết bị và nút thu hồi riêng của ứng dụng chưa có thiết kế đã duyệt (AP-D-12). | Mất điện thoại. | BR-APP-04; US-APP-06; Q-89, RFC-0019, TSK-I2d-12; AP-D-12 | T |
| AP-ST-06 | Ứng dụng phải hiển thị ở Cài đặt, ở tóm tắt duyệt và ở thẻ Blueprint rằng NeuroEdge không phải chức năng an toàn được chứng nhận. | Tránh hiểu nhầm. | BR-APP-08; US-APP-14; Q-38, R-19 | I |
| AP-ST-07 | Trạng thái relay canh hộp (có, chưa bật, tín hiệu cuối lúc nào) phải hiện ở Cài đặt; khi chưa bật phải nêu lý do. | Người dùng biết có được canh không. | BR-APP-07; US-APP-18; FR-EGR-05, Q-74 | D |

### 3.13 Đo lường (MT)

> Nhóm này tạm dừng: BR-APP-10 chưa thuộc K1–K5 của Q-85 (3) và chỉ có hiệu lực nếu một `Q-N` sửa Q-85 (AP-D-16).

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-MT-01 | Ứng dụng phải ghi tại hộp, cục bộ, sự kiện cần cho ba chỉ số: gỡ luật mặc định (AP-KD-04), chặn đúng/chặn oan, và chấp nhận vùng vàng (AP-ZN-04). Thêm loại sự kiện trace là sửa trace chuẩn (cần RFC). | Cổng nhu cầu cần số đo. | BR-APP-10; TSK-I2e-07; MS-TS-04, CONTRIBUTING.md §3 | T |
| AP-MT-02 | Mục bị chặn phải có cách người dùng đánh dấu "chặn đúng" hoặc "chặn oan"; định nghĩa của "oan" do chủ sản phẩm đặt (AP-D-08). | Không có nhãn thì không đo được. | BR-APP-10; US-APP-11; AP-D-08 | D |
| AP-MT-03 | Sự kiện đo không được chứa tên Blueprint, digest, URL, giá trị cảm biến hay nội dung chat, và theo chính sách ẩn danh, opt-out của FR-TEL-01 (FR-TEL-07, BL-NF-02); roadmap TSK-I2e-07 đã sửa theo cùng chính sách (Q-90). | Đếm mà không theo dõi người. | BR-APP-10; TSK-I2e-07; BL-NF-02, MS-EG-01 | T |
| AP-MT-04 | Ngưỡng đạt của các chỉ số không được ghi cứng trong ứng dụng; chủ sản phẩm đặt (AP-D-08). | Không tự đặt ngưỡng. | BR-APP-10; AP-D-08 | I |

### 3.14 Phi chức năng (NF)

| ID | Yêu cầu | Lý do | Nguồn | Kiểm chứng |
|:---|:---|:---|:---|:---|
| AP-NF-01 | Mọi chữ hiển thị ở mặc định phải là tiếng Việt thường, không chứa thuật ngữ như digest, YAML hay mã lỗi. | Người dùng không kỹ thuật. | BR-APP-01; US-APP-01, US-APP-08 | I |
| AP-NF-02 | Không chuỗi giao diện nào được dùng lời tuyệt đối ("an toàn tuyệt đối", "chặn đứng"). | Tránh tuyên bố không kiểm chứng được. | BR-APP-01, BR-APP-08; US-APP-05; Q-38 | I |
| AP-NF-03 | Mất bộ não, mạng ngoài hoặc ngân sách LLM thì ứng dụng vẫn phải xem, duyệt, bật/tắt và nhận cảnh báo khẩn. | Lõi tách khỏi bộ não. | BR-APP-07, BR-APP-08; US-APP-02, US-APP-03; NFR-REL-05, MS-RT-02 | T |
| AP-NF-04 | Thẻ, cảnh báo khẩn và nhãn không được gọi LLM để tạo; chỉ chat tự do mới dùng bộ não. | Chi phí và độ tin cậy. | BR-APP-02, BR-APP-08; US-APP-04; MS-AP-01, MS-RT-07, NFR-COST-01 | T |
| AP-NF-05 | Ứng dụng không được in token, khóa hay mã ghép đôi lên màn hình, log hay URL (ngoài liên kết một lần của `ui-link`). | Không rò bí mật. | BR-APP-04; US-APP-06; MS-CH-01, AP-SH-07 | T |
| AP-NF-06 | Trình duyệt hỗ trợ và ngưỡng thời gian phản hồi: chưa xác định; phải được chốt trước khi kiểm chứng (AP-D-11). | Không tự đặt con số. | BR-APP-01; US-APP-01; AP-D-11 | A |

---

## 4. Truy vết

### 4.1 BR-APP → yêu cầu AP

| BR-APP | Yêu cầu AP |
|:---|:---|
| BR-APP-01 | AP-SH-01, AP-SH-05, AP-SH-06, AP-HM-01, AP-HM-02, AP-HM-03, AP-CH-02, AP-CD-02, AP-CD-08, AP-DV-01, AP-DV-02, AP-DV-03, AP-DV-04, AP-DV-05, AP-DV-08, AP-KD-02, AP-AC-01, AP-AC-03, AP-AC-05, AP-NF-01, AP-NF-02, AP-NF-06 |
| BR-APP-02 | AP-SH-01, AP-HM-04, AP-CH-03, AP-CD-01, AP-CD-02, AP-CD-03, AP-CD-04, AP-CD-05, AP-CD-09, AP-CD-10, AP-DV-10, AP-DV-12, AP-KD-01, AP-KD-04, AP-ST-02, AP-NF-04 |
| BR-APP-03 | AP-CD-04, AP-ZN-01, AP-ZN-02, AP-ZN-03, AP-ZN-04, AP-ZN-05, AP-ZN-06, AP-ZN-07, AP-ZN-08, AP-DV-04, AP-DV-05, AP-KD-05, AP-KD-06 |
| BR-APP-04 | AP-SH-02, AP-SH-03, AP-SH-07, AP-CH-01, AP-CH-04, AP-CD-05, AP-CD-06, AP-CD-07, AP-ZN-07, AP-AV-01, AP-AV-02, AP-AV-03, AP-AV-04, AP-AV-05, AP-AV-06, AP-AV-07, AP-AV-08, AP-AV-09, AP-ST-05, AP-NF-05 |
| BR-APP-05 | AP-WI-01, AP-WI-02, AP-WI-03, AP-WI-04, AP-WI-05, AP-WI-06, AP-WI-07, AP-AC-06 |
| BR-APP-06 | AP-DV-06, AP-DV-07, AP-DV-08, AP-DV-09, AP-DV-10, AP-DV-11, AP-DV-12, AP-DV-13, AP-KD-01, AP-KD-02, AP-KD-03, AP-KD-05 |
| BR-APP-07 | AP-SH-04, AP-HM-03, AP-HM-05, AP-AV-07, AP-AL-01, AP-AL-02, AP-AL-03, AP-AL-04, AP-AL-05, AP-AL-06, AP-AL-07, AP-AL-08, AP-AL-09, AP-AL-10, AP-ST-01, AP-ST-02, AP-ST-07, AP-NF-03 |
| BR-APP-08 | AP-HM-02, AP-CH-02, AP-CH-05, AP-CH-06, AP-CD-04, AP-ZN-04, AP-AV-05, AP-AV-06, AP-AV-09, AP-WI-04, AP-DV-13, AP-KD-03, AP-AC-01, AP-AC-02, AP-AC-03, AP-AC-04, AP-AC-05, AP-AC-06, AP-AC-07, AP-ST-03, AP-ST-04, AP-ST-06, AP-NF-02, AP-NF-03, AP-NF-04 |
| BR-APP-09 | AP-SH-05, AP-ZN-03, AP-ZN-08, AP-KD-06 |
| BR-APP-10 | AP-ZN-04, AP-KD-04, AP-MT-01, AP-MT-02, AP-MT-03, AP-MT-04 |

### 4.2 US-APP → yêu cầu AP

| US-APP | Yêu cầu AP |
|:---|:---|
| US-APP-01 | AP-SH-01, AP-SH-06, AP-HM-01, AP-HM-02, AP-HM-03, AP-HM-04, AP-NF-01, AP-NF-06 |
| US-APP-02 | AP-HM-05, AP-AL-01, AP-AL-02, AP-AL-03, AP-AL-04, AP-AL-10, AP-NF-03 |
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
| US-APP-13 | AP-AL-06, AP-AL-07 |
| US-APP-14 | AP-CH-06, AP-CD-04, AP-ZN-04, AP-AV-06, AP-AV-09, AP-ST-03, AP-ST-04, AP-ST-06 |
| US-APP-15 | AP-CD-01, AP-CD-05, AP-CD-08, AP-CD-09, AP-CD-10 |
| US-APP-16 | AP-SH-05, AP-ZN-01, AP-ZN-03, AP-ZN-08, AP-KD-06 |
| US-APP-17 | AP-AL-05, AP-AL-10 |
| US-APP-18 | AP-SH-04, AP-HM-03, AP-AL-08, AP-AL-09, AP-ST-07 |

---

## 5. Kiểm chứng

Chỉ là kế hoạch: **chưa có task, chưa có test case. Tạo khi có quyết định.** Không dòng nào dưới đây là cam
kết lịch.

| Nhóm | Phương pháp dự kiến | Điều kiện để kiểm chứng |
|:---|:---|:---|
| SH, NF | D, I; T cho ghép đôi và liên kết một lần | Trang nhà dựng xong |
| HM, CH, AC | T trên trace mẫu bể cá | Thẻ duyệt, trace theo đoạn (TSK-I2d-06, TSK-I2d-13, TSK-I2d-14) |
| CD, AV | T: lời duyệt giả, hết hạn, sai digest | Bản ghi duyệt có chữ ký (TSK-I2d-11, TSK-I2d-12; RFC-0019); passkey cần TSK-I2f-08 |
| ZN, KD | T trên khoảng mẫu của Blueprint | AP-D-01, AP-D-13; Blueprint (TSK-I2e-01, TSK-I2e-03) |
| WI | T: kết quả chạy lại bằng đúng kết quả `replay`; không có lệnh ra thiết bị | Trace theo đoạn (TSK-I2d-13, TSK-I2d-14) |
| DV | T trên `sim`, D cho đấu dây | `python/neuroedge/hal/remote.py`, TSK-I2d-32; đường board thật là giai đoạn C, hoãn |
| AL | T cho cảnh báo, D cho chuỗi leo thang | TSK-I2d-09, ngành dọc sau; relay cần Q-74 |
| ST, MT | T, I | TSK-I2e-07; AP-D-08 |

---

## 6. Câu hỏi mở (`AP-D-nn`)

| Mã | Câu hỏi | Bối cảnh | Ảnh hưởng |
|:---|:---|:---|:---|
| **AP-D-01** | Vùng vàng có tồn tại không? | **Còn mở.** Giá trị ngoài khoảng đã khai bị hỏi lại hoặc từ chối theo BL-IN-04 (TC-IN-04-1); hợp đồng chỉ siết, không nới (MS-CP-02); Q-73 bất biến (b): luật đã khai chạy đúng như đã khai. MS-CT-06 chỉ yêu cầu tham số mở khai kiểu và khoảng. Một giá trị ngoài khoảng qua `sensor_facts` (ví dụ ngưỡng `water_hot` của bể cá) làm đổi luật hiệu lực của gate sưởi. Chủ sản phẩm chọn: (a) cho phép ngoài khoảng maker với nhãn rủi ro và chấp nhận rõ ràng, hoặc (b) từ chối giá trị ngoài khoảng maker. Nếu (a), `blueprint.v1` (TSK-I2e-01) phải khai điều đó và MS-CP-02 phải còn đúng. | AP-ZN-01, AP-ZN-04 |
| **AP-D-02** | Có cần passkey (vân tay) sớm hơn I2f không? | **Đã trả lời một phần.** Q-89 và RFC-0019 cho duyệt từ xa qua bot của hộp mà không cần passkey; RFC-0019 giữ passkey là phương thức sau. Còn mở: ứng dụng có cần nó sớm hơn FR-CH-08 (TSK-I2f-08, chưa có code) không. | AP-AV-03, AP-AV-04 |
| **AP-D-03** | Dạng ứng dụng: web di động, ứng dụng gốc hay Zalo Mini App? Cách thay cho đẩy thông báo màn hình khóa? | **Còn mở, có ràng buộc.** Nút của bot duyệt nằm ngay trong cuộc chat (RFC-0019), nên duyệt bằng bot không cần liên kết tới thẻ; trang cục bộ chỉ nghe 127.0.0.1 (AP-D-12). Vân tay và đẩy thông báo trên web (đặc biệt iOS) khó. | AP-SH-01, AP-CD-10 |
| **AP-D-04** | Truy cập từ ngoài nhà cần relay hoặc cloud (Q-74): làm trước hay sau cổng nhu cầu? | **Đã trả lời (Q-74):** bước 2 chờ số đo của cổng nhu cầu 2026-12-06 và chỉ mở nếu số đo cho thấy người thử kẹt ở cài đặt, khóa API hay tự lưu trữ; phê duyệt không đi qua relay (FR-EGR-05). Phần riêng của ứng dụng: màn hình nói rõ giới hạn (AP-SH-04). | AP-SH-04, AP-AL-09, AP-ST-07 |
| **AP-D-05** | Ưu tiên kênh Zalo so với Telegram? | **Đã trả lời một phần.** Lời duyệt gắn với `chat:telegram:<id>` (RFC-0019, Q-89); duyệt qua Zalo cần mở rộng bot duyệt (sửa RFC). FR-CH-01: Telegram trước, Zalo sau (P1). Gia đình ở Việt Nam dùng Zalo là nhận định sản phẩm, chưa đo. Còn mở: thứ tự cho cảnh báo. | AP-AL-06 |
| **AP-D-06** | Luật mặc định theo loại sinh thành tệp tường minh, có chấp nhận không? | **Đã trả lời.** Không cần RFC: gate cho thiết bị mới do `neuroedge add part` sinh (VP-PT-07), thêm gate vào `gates/` là PR thường (`CONTRIBUTING.md` §3), mặc định về giá trị chỉ do Blueprint khai (MS-CT-06). Mặc định ngầm trong runtime vẫn cần RFC. Cách khóa gate sinh ra: AP-D-15. | AP-KD-01, AP-KD-02 |
| **AP-D-07** | Thời gian chờ mặc định của chuỗi leo thang và ngưỡng hộp im lặng? | **Còn mở.** Chưa có đặc tả đã duyệt cho chuỗi leo thang (MS-RT-07 là cảnh báo mẫu cố định, không xác nhận). Thảo luận thiết kế nêu ví dụ 2 phút (hỏi tại chỗ), 5 phút (người thứ hai), 10 phút (relay); chỉ là ví dụ chưa quyết. | AP-AL-03, AP-AL-09 |
| **AP-D-08** | "Chặn oan" định nghĩa thế nào; ngưỡng đạt của ba chỉ số là bao nhiêu? | **Còn mở, bị giới hạn.** Trước cổng chỉ có K1–K5 (Q-85 (3)); xem AP-D-16. BR-APP-10; Q-72 (B6–B8). | AP-MT-02, AP-MT-04 |
| **AP-D-09** | Chạy lại cấu hình đề xuất trên trace có cần RFC không? | **Đã trả lời.** Chạy chỉ đọc không nằm trong danh sách RFC của `CONTRIBUTING.md` §3; sự kiện trace mới cho đoạn trace thì cần RFC (TSK-I2d-13). Studio đã có `POST /api/gates/<name>/whatif` và `POST /api/traces/<name>/replay` (`docs/spec/studio.md`). | AP-WI-01, AP-WI-02 |
| **AP-D-10** | Studio đang tạm dừng (Q-72): tái dùng làm nền ứng dụng hay xây trang riêng? | **Còn mở, có ràng buộc.** Studio chỉ nghe 127.0.0.1 và đang tạm dừng (`docs/spec/studio.md`); xem AP-D-12. | AP-SH-01 |
| **AP-D-11** | Trình duyệt hỗ trợ và ngưỡng thời gian phản hồi? | **Còn mở.** Chưa có số liệu. | AP-NF-06 |
| **AP-D-12** | Điện thoại tới được một trang có xác thực của hộp bằng cách nào, và một lần chạm trong ứng dụng mang nguồn duyệt nào? | Trang cục bộ (`run --ui`, `mcp serve --ui`, Studio) chỉ phục vụ trên 127.0.0.1 và từ chối `Host`/`Origin` khác (`docs/spec/studio.md` §2, DP-A-02). Để điện thoại trong mạng nhà tới được, ứng dụng cần: địa chỉ nghe khác, kiểm `Host`/`Origin` mới, cách ghép thiết bị ứng dụng (`pairing.py` ghép bộ não, `pair owner` ghép chủ, Q-89), và một mục `threat_model.md` do kỹ sư trưởng duyệt (như VP-PM-06). Nguồn người hợp lệ hiện là `local_grammar`, `ui` và `chat:<kênh>:<id>` khi bản ghi xác minh được (RFC-0019). Hoặc ứng dụng chỉ dùng bot duyệt trên Telegram. | AP-SH-01, AP-SH-02, AP-SH-04, AP-AV-04, AP-ST-05 |
| **AP-D-13** | Giới hạn theo giá trị cảm biến (vùng khóa) lấy từ đâu? | `board.v1` `envelope` chỉ có `window_s`, `max_on_ms_per_window`, `min_interval_ms`, `max_continuous_ms`; không có giới hạn giá trị (như 32 °C). Thêm vào là sửa `schemas/` (RFC, `CONTRIBUTING.md` §3). Chọn: (a) vùng khóa chỉ gồm những gì `board.v1` khai, hoặc (b) một RFC thêm giới hạn giá trị. | AP-ZN-01, AP-ZN-02 |
| **AP-D-14** | Chat của ứng dụng đi tới bộ não bằng đường nào? | Q-83 (4) đặt chat, trí nhớ, kênh trong bộ não; FR-CH-01 đặt bộ chuyển kênh chat ở runtime; MS-RT-02: bộ não nối tới hộp qua MCP; RFC-0019: hộp không gửi câu hỏi qua bộ não. Chọn: cổng riêng của NeuroClaw, hoặc relay hộp tới bộ não (task mới). | AP-CH-01 |
| **AP-D-15** | Một lần duyệt của gia đình khóa gì với `agent.toml`, linh kiện và gate? | MS-AP-04, MS-AP-05 chỉ khóa hợp đồng (`missions.lock`); MS-AP-03: công cụ ghi duy nhất của hộp cho bộ não là `mission_draft_write`; gate khóa bằng `neuroedge gate lint` và `digests.lock` (`CHANGELOG.md` §3.3 mục 1, `CONTRIBUTING.md` §3). Cần quy định trước khi ứng dụng sinh gate hay linh kiện rồi đưa duyệt; gate sinh ra phải qua `gate lint`. | AP-CD-01, AP-DV-10, AP-DV-12, AP-KD-01 |
| **AP-D-16** | Có mở một `Q-N` sửa Q-85 (3) để thêm chỉ số của ứng dụng (BR-APP-10) không? | Q-85 (3): chỉ số trước cổng là K1–K5; Q-85 (2): gia đình tới sản phẩm qua Blueprint của maker trước cổng. Đến khi có `Q-N`, nhóm MT tạm dừng. | AP-MT-01 → AP-MT-04 |
| **AP-D-17** | Các dòng ứng dụng thêm vào thẻ (kết quả chạy lại, nhãn vùng, "khi hỏng", nhãn rủi ro) tính vào giới hạn 5 dòng thế nào, và dữ liệu trace có thuộc "đầu vào" của MS-AP-01 không? | MS-AP-01: tối đa 5 dòng, cùng đầu vào cùng byte. | AP-CD-02, AP-WI-01 |

---

## 7. Phụ thuộc vào task hiện có

Chỉ dẫn mã đã có trong `roadmap/neuroedge-roadmap.md`; không thêm task mới và không ghi trạng thái.

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
| TSK-I2d-31 | Canvas giai đoạn C, hoãn (AP-DV-06) |
| TSK-I2d-32 | Bản đồ chân cho bước đấu dây (AP-DV-08) |
| TSK-I2c-16 | Cơ cấu chấp hành từ xa và "off debt" (AP-DV-09, AP-DV-11) |
| TSK-I2e-01, TSK-I2e-03 | Blueprint và xem trước cài đặt (AP-CD-09, AP-KD-06) |
| TSK-I2e-07 | Mốc đo cục bộ theo FR-TEL-07 (AP-MT; BR-APP-10 tạm dừng) |
| TSK-I2e-13 | Ảnh Pi và ghép Telegram bằng QR (AP-SH-02) |
| TSK-I2f-05, TSK-I2f-08 | Vai trò nhiều người, passkey (AP-AV-04, AP-AV-07, AP-ST-01) |
