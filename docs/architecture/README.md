# Kiến trúc NeuroEdge

Bộ tài liệu này mô tả **cấu trúc và hành vi** của NeuroEdge như nó tồn tại trong nhánh `main`, đi
từ bức tranh lớn xuống tới từng byte: bối cảnh (C4 L1) → container (L2) → thành phần (L3) → mã
(L4), rồi các luồng lúc chạy, hợp đồng dữ liệu, yêu cầu phi chức năng, quyết định kiến trúc, và
cách hệ thống sẽ lớn lên.

Thiết kế chưa có mã cũng được ghi tại chỗ trong từng góc nhìn, nhưng luôn mang nhãn `planned` — phần
của định vị Blueprint ghi `planned · Q-72` kèm increment (I2d, I2e) — và vẽ nét đứt trong hình, nên
người đọc luôn tách được cái đang có trên `main` với cái mới quy hoạch.

> Bộ tài liệu chỉ có bản tiếng Việt (`vi/`). Nhãn trong sơ đồ viết bằng tiếng Anh.

## Đọc từ đâu

| Bạn là | Mục tiêu | Đọc theo thứ tự |
|:---|:---|:---|
| Kỹ sư mới | Chạy được hệ thống và hiểu nó trong ngày đầu | [`python/README.md`](../../python/README.md) → `00` → `02` → `03` |
| Kỹ sư lõi | Hiểu từng layer và cách chúng gọi nhau | `00` → `02` → `03` → `05` → `06` → `07` → `15` |
| Kỹ sư nhúng | Firmware, bộ nhớ, khởi động, OTA, triển khai | `02` → `04` → `05` → `06` → `02` §6 |
| Đối tác OEM | Port HAL lên bo mạch mới | `10` §7 → `10` → `07` → `04` |
| Người duyệt an toàn, QA | Vì sao an toàn, bằng chứng ở đâu | `00` §9.4 → `06` → `10`; yêu cầu PRD §9, quyết định PRD §15 |
| Người lập kế hoạch | Cái gì đã có, cái gì tới sau | `00` → `15`; mốc và ngày ở roadmap §0 |

## Bản đồ tệp

Q-77 (2026-10-12) gộp bộ này từ 17 xuống 10 chương: bối cảnh vào `00`, triển khai vào `02`, hướng dẫn port vào
`10`, điểm biến thiên và nợ kiến trúc vào `15`; bỏ các chương chép lại PRD §9 (NFR), PRD §15 (ADR) và
`python/README.md` (ngày đầu). Bản cũ: `git show f7278fc:docs/architecture/vi/<tệp>`.

| Tệp | Nội dung | Góc nhìn |
|:---|:---|:---|
| [`00-overview.md`](vi/00-overview.md) | NeuroEdge là gì, sáu lời hứa, nguyên tắc, đặc tính kiến trúc, trạng thái; §9 bối cảnh: người dùng, hệ thống ngoài, ranh giới tin cậy | Tổng quan · C4 L1 |
| [`02-container-c4l2.md`](vi/02-container-c4l2.md) | Tiến trình, thư viện, firmware, kho tệp và cách chúng nói chuyện; §6 chạy ở đâu (máy dev, CI, gpio-sim, QEMU, Pi, Box-3) | C4 L2 · Deployment |
| [`03-component-host-c4l3.md`](vi/03-component-host-c4l3.md) | Các gói Python, phụ thuộc thật giữa chúng, trách nhiệm từng gói | C4 L3 · host |
| [`04-component-device-c4l3.md`](vi/04-component-device-c4l3.md) | Các component firmware ESP32-S3, trình tự khởi động, bộ nhớ | C4 L3 · device |
| [`05-code-gate-hal-c4l4.md`](vi/05-code-gate-hal-c4l4.md) | Gate từ YAML tới chân: phân giải, cây quyết định, NETR, token, HAL | C4 L4 · Code |
| [`06-runtime-flows.md`](vi/06-runtime-flows.md) | Các luồng lúc chạy: lượt gõ, hỏi lại, MCP, model, replay, khởi động, OTA | Dynamic |
| [`07-data-contracts.md`](vi/07-data-contracts.md) | Mọi định dạng tệp và định dạng đường truyền, cách đánh phiên bản | Data |
| [`10-target-equivalence.md`](vi/10-target-equivalence.md) | Vì sao cùng gate cho cùng quyết định trên `sim`, `linux`, `esp32s3`; §7 port HAL lên bo mạch mới | Cross-cutting · Guide |
| [`15-target-architecture.md`](vi/15-target-architecture.md) | Kiến trúc đích: v1.0, dải Q-72 → Q-76 (agent vận hành, Blueprint, bộ não, cloud tuỳ chọn), điểm biến thiên, nợ kiến trúc | To-be |
| [`16-ecosystem-landscape.md`](vi/16-ecosystem-landscape.md) | Các bên tham gia, tài sản chia sẻ, nền tảng và ranh giới thương mại | System Landscape |

## Quy ước

1. **Trạng thái của mọi thứ được vẽ.** Mỗi hộp, mỗi dòng trong bảng mang một trong ba nhãn:

   | Nhãn | Nghĩa | Trong hình |
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

## Sửa sơ đồ

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
tệp `.excalidraw` là bản vẽ thật, mọi poster được một trang nhúng, mọi link tương đối trỏ tới tệp có thật.
