# RFC-0003: Đóng băng bố cục nhị phân của cây quyết định trên thiết bị (`NETR` v1)

| | |
|:---|:---|
| **Mã RFC** | 0003 |
| **Tiêu đề** | Bố cục nhị phân `NETR` v1 mà `neuroedge build` sinh và walker C99 đọc (Q-23) |
| **Lược đồ bị ảnh hưởng** | *(không trong `schemas/`)* — định dạng mới do RFC này đóng băng |
| **Yêu cầu PRD liên quan** | FR-ACE-01, FR-ACE-03, FR-ACE-08, FR-ACE-10, FR-CI-07, NFR-RES-01 |
| **Người đề xuất** | V1 + V2 *(theo TSK-S4-02)* |
| **Ngày mở** | 2026-09-24 |
| **Trạng thái** | ✅ Đã chấp thuận — **thu hẹp**: chỉ bố cục nhị phân. Phần ghim `extends` bằng digest (TSK-S3-21) vẫn hoãn, `TODOS.md` #15 |
| **Người phê duyệt** | minhlt (kỹ thuật trưởng), 2026-09-24 |

> **Khi nào cần RFC:** `TODOS.md` #15 và `decision_tree.py` yêu cầu đóng băng bố cục
> **trước khi có walker C đầu tiên**. Đổi bố cục sau RFC này cần RFC mới và tăng
> `layout_version`; firmware từ chối phiên bản nó không biết.

## 1. Vấn đề

Q-9 và Q-23: thiết bị không có CEL VM, cũng không có parser JSON. Nó duyệt một cây do host
biên dịch. Cây JSON (`decision_tree.v1.json`) là định dạng **nội bộ của host**, không phù hợp
trên MCU: cần parser, cấp phát động, so sánh chuỗi. Firmware cần một bố cục cố định, đọc
**tại chỗ từ flash**, kiểm được trọn vẹn trước khi dùng, và không đổi âm thầm giữa các bản
build.

## 2. Vì sao định dạng hiện có không giải quyết được

`decision_tree.v1.json` ghi rõ *"internal, not frozen"* và mang chuỗi, danh sách, số thực
dạng văn bản — không đọc được tại chỗ, không có kiểm toàn vẹn.

## 3. Thay đổi đề xuất — bố cục `NETR` v1

Mọi số nguyên little-endian; bản ghi kích thước cố định, căn tự nhiên; **không có con trỏ**
(chỉ offset trong tệp). Walker đọc từng byte nên không phụ thuộc endianness hay căn chỉnh
của CPU.

**Header — 64 byte**

| Offset | Kiểu | Trường | Quy định |
|---:|:---|:---|:---|
| 0 | `char[4]` | `magic` | `"NETR"` |
| 4 | `u16` | `layout_version` | `1` |
| 6 | `u16` | `header_size` | `64` |
| 8 | `u8[32]` | `gate_digest` | SHA-256 thô của gate đã phân giải — cùng digest với vết ghi |
| 40 | `u16` | `node_count` | 1..32 — tiêu chí `allow_when`, theo `criteria_order` |
| 42 | `u16` | `arg_count` | 0..16 — giới hạn tham số RFC-0005, theo thứ tự khai |
| 44 | `u16` | `enum_count` | 0..64 |
| 46 | `u8` | `on_block_action` | 0 deny · 1 escalate · 2 ask · 3 degrade |
| 47 | `u8` | `fail_open` | 0 closed · 1 open |
| 48 | `u32` | `p95_latency_ms` | > 0 |
| 52 | `u32` | `confirm_mask` | bit *i*: tiêu chí *i* người được xác nhận thay (RFC-0006); khác 0 chỉ khi `ask` |
| 56 | `u32` | `strings_size` | 1..16384, byte cuối là NUL |
| 60 | `u32` | `crc32` | CRC-32 (IEEE, như zlib) của toàn tệp với 4 byte này là 0 |

**Node tiêu chí — 24 byte × `node_count`**

| Offset | Kiểu | Trường |
|---:|:---|:---|
| 0 | `u8` | `kind` — 0 bool · 1 level · 2 choice |
| 1 | `u8` | `domain_size` — 1..32 (bool: 2) |
| 2 | `u16` | `name_off` — tên tiêu chí trong bảng chuỗi |
| 4 | `u32` | `admitted_mask` — bit *v*: giá trị thứ *v* của miền được nhận |
| 8 | `f64` | `confidence_floor` — [0, 1] |
| 16 | `u16` | `domain_off` — các giá trị miền, liên tiếp, mỗi chuỗi kết thúc NUL |
| 18 | `u16`, `u32` | dành riêng, bằng 0 |

Miền: bool = `false, true`; level = các mức theo thứ tự; choice = các lựa chọn **đã sắp xếp**.
Dữ kiện tới walker dưới dạng **chỉ số trong miền**, nên thiết bị không so sánh chuỗi để
quyết một tiêu chí.

**Giới hạn tham số — 32 byte × `arg_count`**: `u16 name_off` · `u8 type` (0 string · 1
integer · 2 number · 3 boolean) · `u8 flags` (1 minimum · 2 maximum · 4 enum · 8 max_length) ·
`u16 enum_first` · `u16 enum_count` · `u32 max_length` (ký tự Unicode) · `u32` dành riêng ·
`f64 minimum` · `f64 maximum`.

**Enum — 16 byte × `enum_count`**: `f64 number` (số; boolean là 0/1) · `u32 str_off` ·
`u32 str_len` (byte UTF-8, cho kiểu string).

**Bảng chuỗi**: UTF-8, mỗi chuỗi kết thúc NUL.

Kích thước tệp = 64 + 24·n + 32·a + 16·e + strings, **đúng bằng** độ dài tệp. Với giới hạn
trên, một cây tối đa khoảng 19 KB flash.

**Ngữ nghĩa walker** (bằng với engine host, `python/neuroedge/engine/`):

1. Giới hạn tham số trước, theo thứ tự — vi phạm ⇒ BLOCK `argument_out_of_range`.
2. Mỗi tiêu chí theo `criteria_order`: không có dữ kiện hoặc ngoài miền ⇒
   `criterion_unavailable`; độ tin cậy không phải xác suất (kể cả NaN) ⇒ `criterion_unavailable`;
   có ngưỡng mà thiếu độ tin cậy ⇒ `confidence_unavailable`; không được nhận hoặc dưới ngưỡng ⇒
   `condition_not_met`. Lý do là lỗi **đầu tiên**.
3. Sau xác nhận của người: các tiêu chí trong `confirm_mask` coi như đạt. Câu hỏi chỉ
   *trả lời được* khi đúng các tiêu chí đó là đủ để ALLOW.
4. Suy giảm (`gate_unreachable`, `budget_exceeded`) do lớp gọi walker quyết theo `fail_open`,
   như trên host.

**Nạp**: `ne_tree_load` từ chối mọi tệp có magic, phiên bản, kích thước, CRC, giới hạn hoặc
cấu trúc sai — không đọc gì ngoài bộ đệm.

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| `schemas/` | Không đổi |
| Gate, digest, ba vết ghi chuẩn mực | Không đổi — bố cục là dạng biên dịch của gate |
| Bố cục sau này | RFC mới + `layout_version` 2; walker v1 từ chối v2 (`NE_ERR_VERSION`) |

## 5. Ảnh hưởng an toàn

- Walker không có trạng thái ghi được (`.data`/`.bss` rỗng), không cấp phát, không đệ quy;
  stack lớn nhất 176 byte (`ne_evaluate`, clang `-O2`) — kiểm trên mỗi PR, giới hạn 512 byte.
- Tệp hỏng ở bất kỳ byte nào bị CRC từ chối; mọi độ dài cắt ngắn bị từ chối; cấu trúc bị sửa
  có CRC hợp lệ thì hoặc bị từ chối, hoặc duyệt không đọc ngoài bộ đệm (fuzz dưới ASan/UBSan).
- `gate_digest` trong tệp là digest đã ghi trong vết ghi: một phán quyết trên thiết bị luôn
  truy được về chính sách đã ký.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Đưa JSON lên MCU (cJSON…) | Parser + cấp phát động trên đường an toàn; Q-9/Q-23 đã loại |
| FlatBuffers / Cap'n Proto | Thêm phụ thuộc và công cụ sinh mã; nhu cầu chỉ là vài bản ghi cố định |
| Struct C `#pragma pack` ép kiểu trực tiếp | Phụ thuộc endianness, căn chỉnh và trình biên dịch; không kiểm biên được |

## 7. Bằng chứng kiểm chứng

- [x] `python/tests/test_c_walker.py`: walker C (ASan + UBSan) khớp **engine host thật** trên
  mọi gate trong `gates/`, corpus hợp lệ, agent mẫu và một gate tổng hợp phủ mọi loại giới
  hạn — hàng `truth_cases` × {chưa, đã xác nhận} + 400 ca ngẫu nhiên có seed mỗi gate; khớp
  bảng sự thật đã ghi trong `fixtures/decision_trees/`; fuzz; RAM tĩnh 0; stack ≤ 512 byte
- [x] Kiểm tra đột biến: 7 lỗi cố ý cài vào walker (thứ tự kiểm độ tin cậy, bỏ/mở rộng xác
  nhận, biên `maximum`, đếm độ dài theo byte, integer nhận số lẻ, `answerable`) đều bị bắt
- [x] `neuroedge build` ghi `<gate>.netree` và `<gate>.netree.h`

## 8. Việc phải làm khi chấp thuận

- [x] `python/neuroedge/engine/binary_tree.py` (bộ mã hoá) · `targets/esp32s3/components/ne_gate/` (walker, component ESP-IDF, Makefile host)
- [x] `neuroedge-roadmap.md` TSK-S4-02 🟡 (walker xong; sổ token C + tích hợp firmware còn lại), TSK-S4-07 ✅
- [x] `TODOS.md` #15 thu hẹp còn phần ghim `extends`
- [ ] Sổ token dùng một lần bằng C và gắn walker vào `app_main` — cùng TSK-S4-08 (QEMU)
