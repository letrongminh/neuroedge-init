# Kiến trúc NeuroEdge · NeuroEdge architecture

Bộ tài liệu này mô tả **cấu trúc và hành vi** của NeuroEdge như nó tồn tại trong nhánh `main`, đi
từ bức tranh lớn xuống tới từng byte: bối cảnh (C4 L1) → container (L2) → thành phần (L3) → mã
(L4), rồi các luồng lúc chạy, hợp đồng dữ liệu, yêu cầu phi chức năng, quyết định kiến trúc, và
cách hệ thống sẽ lớn lên. *This suite describes NeuroEdge's structure and behaviour as it exists
on `main`, from the big picture down to the byte.*

> **Tiếng Việt là bản gốc; English is a mirror.** Hai cây `vi/` và `en/` có cùng tệp, cùng cấu
> trúc mục và cùng sơ đồ. Nhãn trong sơ đồ viết bằng tiếng Anh để một bộ hình dùng chung cho cả
> hai cây. *The Vietnamese tree is authoritative; the English tree mirrors it file for file.*

## Đọc từ đâu · Where to start

| Bạn là · You are | Mục tiêu · Goal | Đọc theo thứ tự · Read in order |
|:---|:---|:---|
| Kỹ sư mới · New engineer | Chạy được hệ thống và hiểu nó trong ngày đầu · Run and understand it on day one | `12` → `00` → `01` → `02` → `03` |
| Kỹ sư lõi · Core engineer | Hiểu từng layer và cách chúng gọi nhau · Every layer and how they call each other | `00` → `02` → `03` → `05` → `06` → `07` → `15` |
| Kỹ sư nhúng · Embedded engineer | Firmware, bộ nhớ, khởi động, OTA · Firmware, memory, boot, OTA | `02` → `04` → `05` → `06` → `14` |
| Đối tác OEM · OEM partner | Port HAL lên bo mạch mới · Port the HAL to a new board | `11` → `10` → `07` → `04` → `15` §4.1 |
| Người duyệt an toàn, QA · Safety reviewer, QA | Vì sao an toàn, bằng chứng ở đâu · Why it is safe, where the evidence is | `01` §4 → `08` → `09` → `06` → `10` |
| Người lập kế hoạch · Planner | Cái gì đã có, cái gì tới sau · What exists, what comes next | `00` → `13` → `15` |

## Bản đồ tệp · File map

| Tệp · File | Nội dung · Content | Góc nhìn · View |
|:---|:---|:---|
| [`00-overview.md`](vi/00-overview.md) | NeuroEdge là gì, tinh thần sản phẩm (sáu lời hứa), nguyên tắc, đặc tính kiến trúc, trạng thái | — |
| [`01-context-c4l1.md`](vi/01-context-c4l1.md) | Người dùng, hệ thống bên ngoài, ranh giới tin cậy | C4 L1 · Context |
| [`02-container-c4l2.md`](vi/02-container-c4l2.md) | Tiến trình, thư viện, firmware, kho tệp và cách chúng nói chuyện | C4 L2 · Container |
| [`03-component-host-c4l3.md`](vi/03-component-host-c4l3.md) | Các gói Python, phụ thuộc thật giữa chúng, trách nhiệm từng gói | C4 L3 · Component (host) |
| [`04-component-device-c4l3.md`](vi/04-component-device-c4l3.md) | Các component firmware ESP32-S3, trình tự khởi động, bộ nhớ | C4 L3 · Component (device) |
| [`05-code-gate-hal-c4l4.md`](vi/05-code-gate-hal-c4l4.md) | Gate từ YAML tới chân: phân giải, cây quyết định, NETR, token, HAL | C4 L4 · Code |
| [`06-runtime-flows.md`](vi/06-runtime-flows.md) | Các luồng lúc chạy: lượt gõ, hỏi lại, MCP, model, thoại, replay, khởi động, OTA | Dynamic |
| [`07-data-contracts.md`](vi/07-data-contracts.md) | Mọi định dạng tệp và định dạng đường truyền, cách đánh phiên bản | Data |
| [`08-nfr.md`](vi/08-nfr.md) | Yêu cầu phi chức năng → cách kiến trúc đáp ứng → bằng chứng | Quality |
| [`09-adr.md`](vi/09-adr.md) | Nhật ký quyết định kiến trúc (ADR) và RFC | Decisions |
| [`10-target-equivalence.md`](vi/10-target-equivalence.md) | Vì sao cùng gate cho cùng quyết định trên `sim`, `linux`, `esp32s3` | Cross-cutting |
| [`11-hal-port-guide.md`](vi/11-hal-port-guide.md) | Port HAL lên bo mạch mới: hợp đồng, bước làm, cách chứng minh | Guide |
| [`12-dev-quickstart.md`](vi/12-dev-quickstart.md) | Ngày đầu: cài, chạy, đọc mã, sửa lần đầu | Guide |
| [`13-evolution-i0-i18.md`](vi/13-evolution-i0-i18.md) | Kiến trúc qua mười mốc phát hành theo người dùng, những gì không đổi, điểm mở rộng · Architecture across the ten user-facing release milestones | Evolution |
| [`14-deployment-c4.md`](vi/14-deployment-c4.md) | Chạy ở đâu: máy dev, CI, gpio-sim, QEMU, Pi, Box-3 | C4 Deployment |
| [`15-target-architecture.md`](vi/15-target-architecture.md) | Kiến trúc mục tiêu theo chân trời (H1 v1.0, H2 v1.1, H3 sau Beta) · Target architecture by horizon | C4 To-be · Horizons |
| [`16-ecosystem-landscape.md`](vi/16-ecosystem-landscape.md) | Bức tranh hệ sinh thái, các bên tham gia, tài sản chia sẻ và mô hình thương mại · Ecosystem landscape | C4 System Landscape |

Bản tiếng Anh: cùng tên tệp trong [`en/`](en/). *English: same file names under [`en/`](en/).*

## Quy ước · Conventions

1. **Trạng thái của mọi thứ được vẽ.** Mỗi hộp, mỗi dòng trong bảng mang một trong ba nhãn:

   | Nhãn · Label | Nghĩa · Meaning | Trong hình · In a diagram |
   |:---|:---|:---|
   | `done` | Có mã trong `main` và có test chạy trong CI | nét liền |
   | `partial` | Một phần có mã; phần còn lại nêu rõ | nét liền, dấu ◐ |
   | `planned` | Mới có trong PRD, roadmap, RFC hoặc bản nháp; chưa có mã | nét đứt, dấu ○ |

   Không có chi tiết "trông hợp lý" nào được vẽ mà không có nguồn: mỗi khẳng định dẫn tới tệp mã,
   test, hoặc tài liệu quy hoạch nói ra nó.
2. **Mỗi sự thật một nơi** (`CONTRIBUTING.md` §8.1). Bộ này mô tả cấu trúc và hành vi. Yêu cầu dẫn
   mã `FR-*`/`NFR-*` về PRD; quyết định dẫn `Q-N` về PRD §15; tiến độ và ngày dẫn increment `I-N`
   về roadmap §0.2; cú pháp lệnh dẫn về `CHANGELOG.md` §2.3; ký hiệu dẫn về
   [`docs/user/thuat-ngu.md`](../user/thuat-ngu.md). Không chép lại, không ghi số test.
3. **Tham chiếu bằng tên**, không bằng số dòng: `engine/gate.py` · `ActionContractEngine.evaluate`.
4. **Hai loại sơ đồ.** Sơ đồ Mermaid nằm ngay trong trang, chính xác tới tên hàm, sửa cùng văn bản.
   Poster (`assets/svg/`) là bức tranh lớn để in hoặc trình chiếu.

## Sửa sơ đồ · Editing diagrams

**Poster** sinh từ một mô hình duy nhất, [`scripts/gen_architecture_diagrams.py`](../../scripts/gen_architecture_diagrams.py),
ra cả `assets/excalidraw/<id>.excalidraw` (mở bằng Excalidraw để xem hoặc phác thảo) lẫn
`assets/svg/<id>.svg` (ảnh các trang nhúng). Muốn đổi poster: sửa hàm của poster đó rồi chạy

```bash
python3 scripts/gen_architecture_diagrams.py           # ghi lại SVG và .excalidraw
python3 scripts/gen_architecture_diagrams.py --check   # CI: thoát 1 nếu tệp lệch mô hình
```

Mô hình tự kiểm bố cục trước khi ghi: hộp chồng nhau, chữ tràn hộp, nhãn đè hộp, mũi tên trỏ tới
hộp không có đều bị từ chối. Đừng sửa tay hai tệp sinh ra; phác thảo trong Excalidraw thì chép thay
đổi về mô hình.

**Mermaid** được GitHub vẽ trực tiếp; một lỗi cú pháp biến sơ đồ thành chữ thô. Trước khi đẩy:

```bash
npm install -g @mermaid-js/mermaid-cli        # một lần
python3 scripts/check_architecture_mermaid.py  # mọi khối phải render
```

`python/tests/test_architecture_diagrams.py` (chạy trong CI) giữ các điều sau: poster khớp mô hình,
tệp `.excalidraw` là bản vẽ thật, mọi poster được một trang nhúng, hai cây `vi/`–`en/` cùng tệp,
cùng cấu trúc mục và cùng khối Mermaid, mọi link tương đối trỏ tới tệp có thật.
