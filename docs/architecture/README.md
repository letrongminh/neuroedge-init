# Kiến trúc NeuroEdge · NeuroEdge Architecture

> **VI là bản gốc (authoritative). EN is a mirror.** Mọi nhãn trong hình vẽ giữ
> tiếng Anh (tên module, mã `FR-*`/`Q-N`/`TSK-*` vốn đã là Anh) để một bộ hình
> dùng chung cho cả hai cây. Caption và tiêu đề hình song ngữ trong từng file.

## Đọc từ đâu (Start here)

| Bạn là | Đọc |
|:---|:---|
| Dev mới, muốn chạy được trong ngày đầu | `vi/12-dev-quickstart.md` → `vi/00-overview.md` → `vi/01-context-c4l1.md` |
| Kỹ sư lõi / nhúng, cần chi tiết layer và tương tác | `vi/00` → `vi/02` → `vi/03` → `vi/04` → `vi/05` → `vi/06` |
| Đối tác OEM port HAL | `vi/11-hal-port-guide.md` → `vi/10-target-equivalence.md` → `vi/07-data-contracts.md` |
| Người duyệt an toàn / QA | `vi/08-nfr.md` → `vi/09-adr.md` → `vi/06-runtime-flows.md` |

EN tree mirrors `vi/` file-for-file: `en/00-overview.md` … `en/13-evolution-i0-i18.md`.

## Bản đồ file

| File | Nội dung | C4 |
|:---|:---|:---|
| `00-overview.md` | Tuyên ngôn, nguyên tắc P-1..P-5, scope I0–I18 | — |
| `01-context-c4l1.md` | Bối cảnh hệ thống + actor ngoài | L1 |
| `02-container-c4l2.md` | Container runtime + quan hệ | L2 |
| `03-component-host-c4l3.md` | Component host Python + ma trận phụ thuộc | L3 |
| `04-component-device-c4l3.md` | Component firmware ESP32-S3 | L3 |
| `05-code-gate-hal-c4l4.md` | Luồng resolve → evaluate → token → HAL, bố cục NETR | L4 |
| `06-runtime-flows.md` | Sequence: session, voice barge-in, tool dispatch, S1/S2, trace lifecycle | L4 |
| `07-data-contracts.md` | 4 file định dạng + envelope ToolCall + versioning | — |
| `08-nfr.md` | NFR → tactic kiến trúc → bằng chứng đo | — |
| `09-adr.md` | Chỉ mục quyết định kiến trúc | — |
| `10-target-equivalence.md` | Tương đương sim/linux/esp32s3, phân tầng bậc | — |
| `11-hal-port-guide.md` | Hướng dẫn OEM port HAL | — |
| `12-dev-quickstart.md` | Đường chạy ngày đầu | — |
| `13-evolution-i0-i18.md` | As-is I0–I7 vs planned I8–I18, variation points | — |

Hình lớn: `assets/svg/` (8 poster E-01 đến E-08, export từ `assets/excalidraw/`).
Sơ đồ chính xác: Mermaid tại chỗ trong từng file.

## Quy ước (Conventions)

1. **Mỗi sự thật một nơi** (`CONTRIBUTING.md` §8.1): tài liệu này chỉ mô tả
   **cấu trúc + hành vi**. Yêu cầu → dẫn `FR-*`/`NFR-*` về PRD; trạng thái,
   ngày, tag → dẫn `I-N` về roadmap §0.2; nội dung quyết định → dẫn `Q-N` về
   PRD §15; ký hiệu → `docs/user/thuat-ngu.md`. Không chép lại.
2. Tham chiếu bằng mã/mục, không bằng số dòng (R11).
3. Nhãn `done` = đã có mã ở `main`; `planned` = mới ở PRD/roadmap/draft/RFC,
   chưa có mã. Mọi diagram ghi rõ trạng thái từng phần.
4. Sửa hình: sửa `.excalidraw` rồi export lại `.svg` **cùng commit**.
