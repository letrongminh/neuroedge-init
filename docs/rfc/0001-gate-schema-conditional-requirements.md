# RFC-0001: Yêu cầu trường có điều kiện cho gate kế thừa

| | |
|:---|:---|
| **Mã RFC** | 0001 |
| **Lược đồ bị ảnh hưởng** | `gate.v1` |
| **Yêu cầu PRD liên quan** | FR-GATE-02, FR-GATE-06, FR-GATE-07, FR-GATE-08, FR-DX-04 |
| **Người đề xuất** | V1 — Kỹ sư lõi nền tảng |
| **Ngày mở** | 2026-09-21 |
| **Trạng thái** | ✅ Đã chấp thuận |
| **Kiểm chứng** | `python/tests/test_gate_fixtures.py`, `python/tests/test_gate_resolver.py` |

## 1. Vấn đề

Bản `gate.v1.json` đầu tiên **không thể thẩm định một gate có kế thừa**. Ba lỗi
độc lập, cả ba phát hiện khi hiện thực bộ phân giải và viết ba gate mẫu:

### 1a. Trường bắt buộc vô điều kiện chặn đứng nguyên tắc 1

```json
"required": ["schema", "name", "version", "evaluate", "allow_when", "on_block", "budget"]
```

Nguyên tắc kế thừa 1 (Phụ lục B.5) nói gate con **tự động kế thừa toàn bộ**
`evaluate` từ gate cha. Nhưng lược đồ buộc mọi tài liệu phải tự khai `evaluate`,
`allow_when`, `on_block` và `budget`. Hệ quả: gate con muốn kế thừa thì phải
chép lại toàn bộ gate cha — đúng thứ mà `extends` tồn tại để loại bỏ.

Tài liệu tối thiểu sau đây **phải hợp lệ** theo Phụ lục B.5 nhưng bị lược đồ từ
chối:

```yaml
schema:  neuroedge.gate/v1
name:    unlock-door-night
version: 1.0.0
extends: neuroedge://gates/unlock_door@1.2.0
```

### 1b. `budget.fail` vừa bắt buộc vừa có giá trị mặc định

```json
"budget": {
  "required": ["p95_latency_ms", "fail"],
  "properties": {
    "fail": { "enum": ["closed", "open"], "default": "closed" }
  }
}
```

Đây là mâu thuẫn nội tại: một trường bắt buộc thì giá trị mặc định không bao giờ
được dùng tới. Phụ lục B.4 lại ghi rõ `closed` là **"Mặc định"**, nên `fail`
phải là trường tùy chọn.

Mâu thuẫn này có hệ quả an toàn trực tiếp. Nguyên tắc 4 nói `fail: open` **không
kế thừa** mà phải khai báo tường minh tại từng cấp. Cách diễn đạt tự nhiên của
"cấp này không xin fail-open" là **không viết gì cả** — và mặc định phải là
`closed`. Bắt buộc `fail` khiến mọi gate con phải viết `fail: closed` một cách
thủ công, và một lần quên sẽ thành lỗi thẩm định thay vì thành hành vi an toàn.

### 1c. Bốn hành vi `on_block` không có tham số bắt buộc tương ứng

Phụ lục B.3 quy định `escalate` chuyển tới `to:`, `ask` hỏi theo `message:`,
`degrade` chuyển sang `fallback_action:`. Lược đồ chỉ bắt buộc `action`, nên
gate sau đây hợp lệ về lược đồ nhưng vô nghĩa lúc chạy:

```yaml
on_block:
  action: escalate     # leo thang tới ai?
```

## 2. Vì sao lược đồ hiện tại không giải quyết được

Cả ba đều là hạn chế của JSON Schema phẳng: không có `if`/`then`, không thể nói
"bắt buộc X chỉ khi không có Y". Draft 2020-12 hỗ trợ `if`/`then` trong `allOf`,
nên không cần đổi phiên bản draft.

## 3. Thay đổi đề xuất

### 3a. Trường bắt buộc phụ thuộc vào sự có mặt của `extends`

```json
"required": ["schema", "name", "version"],
"allOf": [
  {
    "if":   { "not": { "required": ["extends"] } },
    "then": { "required": ["schema", "name", "version",
                           "evaluate", "allow_when", "on_block", "budget"] }
  }
]
```

Gate gốc (không `extends`) vẫn phải khai báo hợp đồng đầy đủ — không nới lỏng gì
ở đây. Gate dẫn xuất được phép kế thừa.

### 3b. `budget.fail` thành tùy chọn, vắng mặt nghĩa là `closed`

```json
"budget": { "required": ["p95_latency_ms"] }
```

### 3c. Tham số `on_block` bắt buộc theo từng hành vi

```json
"allOf": [
  { "if":   { "properties": { "action": { "const": "escalate" } }, "required": ["action"] },
    "then": { "required": ["action", "to"] } },
  { "if":   { "properties": { "action": { "const": "ask" } }, "required": ["action"] },
    "then": { "required": ["action", "message"] } },
  { "if":   { "properties": { "action": { "const": "degrade" } }, "required": ["action"] },
    "then": { "required": ["action", "fallback_action"] } }
]
```

### 3d. Siết chặt kèm theo

Ba mục nhỏ, cùng tinh thần "lược đồ nói đúng điều Phụ lục B nói":

| Trường | Thay đổi |
|:---|:---|
| `extends` | Thêm `pattern` cho URI `neuroedge://gates/<path>@<semver>` |
| `evaluate.*` | `level` bắt buộc có `levels`; `choice` bắt buộc có `options`; `bool` không được có cả hai |
| `evaluate` | `minProperties: 1` — gate phải thẩm định ít nhất một đại lượng |

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | **Có**, trừ hai trường hợp ở dưới |
| Tệp đang không hợp lệ có trở nên hợp lệ? | **Có** — gate dẫn xuất tối thiểu, và `budget` không có `fail` |
| Cần tăng phiên bản lược đồ? | **Không** — xem lập luận dưới |
| Ảnh hưởng tới chữ ký gate đã phát hành? | **Không** — chưa phát hành gate nào; Gate Registry là Khối 3 |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | **Không** — thay đổi chỉ nằm ở `gate.v1` |

**Hai trường hợp siết chặt** (3c và 3d) khiến một số tài liệu đang hợp lệ trở
thành không hợp lệ — về nguyên tắc là thay đổi phá vỡ tương thích. Vẫn giữ `v1`
vì: lược đồ chưa publish ra ngoài nhóm, chưa có gate nào được ký, và bản thân
việc đóng băng lược đồ là hạng mục **đang chạy** của Sprint 1. Sau khi Sprint 1
đóng, mọi thay đổi có tính chất này bắt buộc lên `gate.v2`.

Tất cả tài liệu bị siết chặt loại bỏ đều là tài liệu **vô nghĩa lúc chạy**
(`escalate` không có người nhận, `level` không có thang, gate không thẩm định
gì). Không có tài liệu nào có nghĩa bị mất.

## 5. Ảnh hưởng an toàn

**Thay đổi này có làm gate lỏng hơn không: không.** Từng mục:

| Thay đổi | Hướng ảnh hưởng an toàn |
|:---|:---|
| 3a — bắt buộc có điều kiện | Trung tính. Gate gốc vẫn phải khai đầy đủ. Gate dẫn xuất kế thừa qua bộ phân giải, nơi năm nguyên tắc B.5 được cưỡng chế |
| 3b — `fail` tùy chọn | **Siết chặt.** Vắng mặt nghĩa là `closed`. Trước thay đổi, quên `fail` là lỗi thẩm định; sau thay đổi, quên `fail` là hành vi an toàn nhất. Đây cũng là điều làm nguyên tắc 4 diễn đạt được |
| 3c — tham số `on_block` | **Siết chặt.** Loại bỏ gate leo thang không có người nhận |
| 3d — `extends` pattern, kiểu `evaluate` | **Siết chặt.** Loại bỏ URI không phân giải được và tiêu chí không lượng giá được |

Một điểm cần ghi rõ: mục 3a chuyển trách nhiệm cưỡng chế nguyên tắc 1–5 từ JSON
Schema sang **bộ phân giải** (`python/neuroedge/engine/gate_resolver.py`). JSON
Schema không thể diễn đạt "gate con chỉ được siết chặt `allow_when`" — đó là
mệnh đề về hai tài liệu, còn lược đồ chỉ thẩm định một. Vì vậy:

> **Thẩm định lược đồ một mình KHÔNG đủ để kết luận một gate an toàn.**
> `neuroedge gate resolve` mới là cổng kiểm tra. Một tài liệu chỉ đạt lược đồ mà
> chưa phân giải được thì chưa được phép nạp lên thiết bị.

Điều này đã được ghi vào `CONTRIBUTING.md` §3 và cưỡng chế trong CI: workflow
`ci-sim-linux.yml` chạy `neuroedge gate lint`, không chỉ thẩm định lược đồ.

### Hệ quả phát sinh: `allow_when` dạng biểu thức trong chuỗi kế thừa

Trong lúc hiện thực nguyên tắc 2, một vấn đề thứ tư lộ ra và được xử lý ở đây vì
cùng chủ đề: `allow_when` cho phép cả dạng **chuỗi biểu thức** (CEL, cho Q-9
phương án A) và dạng **mapping toán tử** (Phụ lục B.2).

Nguyên tắc 2 yêu cầu **chứng minh** gate con không lỏng hơn gate cha. Với dạng
mapping, phép chứng minh là so sánh tập hợp giá trị được chấp nhận. Với hai
chuỗi CEL bất kỳ, đó là bài toán **không quyết định được** trong trường hợp tổng
quát.

**Quyết định:** bộ phân giải **từ chối** dạng chuỗi khi gate nằm trong chuỗi kế
thừa, với `GateInheritanceError` nêu rõ nguyên tắc 2. Fail-closed thay vì xấp xỉ
một phép kiểm tra an toàn. Gate độc lập (không `extends`, không gate con) vẫn
được phép dùng CEL khi trình biên dịch gate hoàn thành ở TSK-S2-06.

Đã ghi vào mô tả trường `allow_when` trong lược đồ.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Buộc gate con chép lại toàn bộ trường của gate cha | Xóa sạch giá trị của `extends`; mỗi lần gate cha đổi là mọi gate con phải sửa tay, và im lặng phân kỳ nếu quên |
| Bỏ `required` hoàn toàn, để bộ phân giải kiểm tra tất cả | Mất chẩn đoán ở mức tệp. Lỗi sẽ chỉ vào artifact đã làm phẳng — thứ tác giả chưa bao giờ nhìn thấy — thay vì vào dòng họ vừa viết. Vi phạm FR-DX-04 |
| Tạo `gate.v2` cho gate có kế thừa | Hai lược đồ cho một khái niệm; `extends` là tính năng cốt lõi của v1 theo Phụ lục B.1, không phải phần mở rộng |
| Xấp xỉ phép so sánh CEL bằng cách phân tích cú pháp | Một phép kiểm tra an toàn đúng "gần hết" sẽ hỏng đúng ở các trường hợp biên mà kẻ tấn công nhắm vào |

## 7. Bằng chứng kiểm chứng

- [x] Ví dụ hợp lệ: `fixtures/gates/valid/` (5 tệp) và `gates/` (3 gate mẫu)
- [x] Ví dụ sai kèm thông báo lỗi kỳ vọng: `fixtures/gates/invalid/` (15 tệp) và `fixtures/gates/expected_errors.yaml`
- [x] Test tự động: `test_gate_resolver.py` (35 test, phủ cả 5 nguyên tắc), `test_gate_fixtures.py` (40 test), `test_sample_gates.py` (26 test)
- [x] `neuroedge gate lint` xanh trên `gates/`, đỏ trên `fixtures/gates/invalid/`
- [x] Trường hợp trực tiếp cho 1a: `fixtures/gates/valid/inherits_on_block_and_budget.yaml` — tài liệu chỉ có 4 dòng định danh, phân giải ra hợp đồng đầy đủ
- [x] Trường hợp trực tiếp cho 1b: `fixtures/gates/valid/inherits_fail_open_as_closed.yaml` — gate cha `fail: open`, gate con im lặng, kết quả `closed`

## 8. Việc đã làm

- [x] Cập nhật `schemas/gate.v1.json`
- [x] Ghi chú `$comment` dẫn chiếu RFC-0001 tại khối `allOf` gốc
- [x] Hiện thực cưỡng chế 5 nguyên tắc tại `python/neuroedge/engine/gate_resolver.py`
- [x] Thêm fixture và test
- [x] Cập nhật `neuroedge-roadmap.md` (TSK-S1-02, TSK-S1-03, Tiêu chí ra 1 và 2)
- [x] Đồng bộ Phụ lục B.1, B.3 và B.4 của `neuroedge-proposal.md` — *xong 2026-09-23, proposal v5.5*

## 9. Việc còn treo

Phụ lục B.1 của `neuroedge-proposal.md` đánh dấu `evaluate`, `allow_when`,
`on_block`, `budget` là **"Bắt buộc"** không điều kiện, và Phụ lục B.4 gọi
`closed` là "Mặc định" mà không nói rõ trường là tùy chọn. Sau RFC này, hai mục
đó cần diễn đạt lại cho khớp:

- B.1: ghi rõ bốn trường là bắt buộc **với gate gốc**, và kế thừa được khi có `extends`
- B.4: ghi rõ `fail` là trường **tùy chọn**, vắng mặt nghĩa là `closed`
- B.3: ghi rõ tham số bắt buộc theo từng hành vi

Đây là sửa văn bản đề xuất, không sửa mã hay lược đồ, nên tách khỏi RFC này để
giữ phạm vi rõ ràng.
