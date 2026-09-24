# RFC-0004: Gate con không được nới `budget` và `on_block`

| | |
|:---|:---|
| **Mã RFC** | 0004 |
| **Tiêu đề** | Mở rộng nguyên tắc kế thừa 2 và 4 sang `budget` và `on_block` |
| **Lược đồ bị ảnh hưởng** | *(không)* — chỉ ngữ nghĩa phân giải (`python/neuroedge/engine/gate_resolver.py`) |
| **Yêu cầu PRD liên quan** | FR-GATE-06, FR-GATE-07, FR-GATE-09, NFR-RES-04 |
| **Người đề xuất** | V1 — Kỹ sư lõi nền tảng *(soạn theo phát hiện `ENG-A2`, design doc Giai đoạn 1)* |
| **Ngày mở** | 2026-09-23 |
| **Trạng thái** | ✅ Đã chấp thuận · ✅ Đã hiện thực (TSK-S2-13, PR #6) |
| **Người phê duyệt** | minhlt, 2026-09-23 — quyết định **Q-18** (`neuroedge-prd.md` §15) |

> Sửa ngữ nghĩa phân giải gate cần RFC (`CONTRIBUTING.md` §3) dù không đụng
> `schemas/`. RFC này **không** sửa lược đồ, **không** sửa ba vết ghi chuẩn mực.

## 1. Vấn đề

Lời hứa trung tâm của `extends` là *gate con không bao giờ lỏng hơn gate cha*.
Bộ phân giải hiện chỉ giữ lời hứa đó cho `allow_when`. Gate sau **phân giải
thành công** trên `gates/` hôm nay (dựng lại ở design doc, `ENG-A2`):

```yaml
schema:  neuroedge.gate/v1
name:    lax-night
version: 1.0.0
extends: neuroedge://gates/unlock_door@1.2.0   # cha: 120 ms, closed, escalate
on_block:
  action:          degrade
  fallback_action: unlock_door_no_auth
budget:
  p95_latency_ms: 900000
  fail:           open
```

```
RESOLVED OK
  budget   = {'p95_latency_ms': 900000, 'fail': 'open'}
  on_block = {'action': 'degrade', 'fallback_action': 'unlock_door_no_auth'}
  allow_when kế thừa nguyên vẹn
```

Nghĩa cộng lại: *chờ thẩm định tới 15 phút; quá hạn thì cho qua; bị chặn thì
mở cửa không xác thực.* `allow_when` không đổi một chữ nên phép kiểm nguyên tắc
2 không thấy gì.

## 2. Vì sao quy tắc hiện tại không giải quyết được

Ba chỗ, cùng một tệp:

1. `_resolve_budget()` ghi đè `p95_latency_ms` của cha bằng của con **không so
   sánh**. Ngân sách là timeout của bộ phán định; nới nó là nới cửa sổ mà
   `fail` quyết định kết quả.
2. Nguyên tắc 4 chỉ chặn `fail: open` **lan xuống** từ cha. Nó không chặn con
   **tự khai** `open` trong một chuỗi mà cha đã `closed`.
3. Comment ở vòng lặp phân giải ghi *"on_block only takes effect once the
   action is already denied"*, nên `on_block` không chịu quản trị B.5. Đúng với
   `deny`/`escalate`/`ask`, **sai với `degrade`**: `fallback_action` **được thực
   thi**, tức là một hành động vật lý khác chạy thay.

## 3. Thay đổi đề xuất

Ba luật, áp dụng khi tài liệu có `extends` (cấp ≥ 2 của chuỗi). Vi phạm ⇒
`GateInheritanceError` (`NE2003`), cùng hợp đồng lỗi 3 thành phần.

| # | Luật | Nguyên tắc B.5 | Lý do |
|:---:|:---|:---:|:---|
| **R1** | `budget.p95_latency_ms` của con **≤** giá trị đã phân giải của cha | 2 | Ngân sách dài hơn là cửa sổ phán định lỏng hơn |
| **R2** | Nếu `budget.fail` đã phân giải của cha là `closed` (khai hoặc mặc định), con **không được khai** `fail: open` | 4 | `open` chỉ được giữ trong chuỗi mà chính cha đã chọn `open`; không được *mở ra* ở giữa chuỗi |
| **R3** | Con **không được tự đưa vào** `on_block.action: degrade`. Con được: giữ nguyên `degrade` **với đúng `fallback_action` của cha**; đổi sang `deny`, `escalate` hoặc `ask`; đổi `to` / `message` | 2 | `degrade` thực thi một hành động; ba hành vi còn lại chỉ chặn và báo. Đổi người nhận không đổi việc hành động bị chặn |

Không đổi:

- Gate gốc (không `extends`) khai `budget` và `on_block` tuỳ ý trong lược đồ.
- Con im lặng ⇒ kế thừa nguyên vẹn như RFC-0001; nguyên tắc 4 vẫn biến `open`
  của cha thành `closed` khi con không khai lại.
- Chuỗi mà cha đã `open` thì con vẫn được khai lại `open` —
  `fixtures/gates/valid/explicit_fail_open.yaml` giữ nguyên hợp lệ.

### Hành vi `on_block` lúc chạy (Q-17, ghi lại để R3 có nghĩa)

Với **mọi** `on_block`, hành động gốc bị chặn. `deny`: chặn. `escalate`/`ask`:
chặn + ghi sự kiện vào vết ghi + gọi hook (mặc định no-op). `degrade`: chạy
`fallback_action` **qua gate của chính nó**. R3 tồn tại vì `degrade` là hành vi
duy nhất chạy thêm một hành động.

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | **Có, với mọi tệp trong kho.** Đã đối chiếu: 3 gate mẫu (`p95` 200 → 120 → 90, `closed`, `escalate` đổi `to` ở cấp 3), 5 fixture `valid/` (`tightens_every_kind` 150 → 80; `explicit_fail_open` dưới cha `open`). Gate kiểu `lax-night` trở thành không phân giải được — đó là mục đích |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Không |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | **Không.** Lược đồ không đổi. Về ngữ nghĩa: chưa có gate nào được publish ra ngoài kho (registry là Khối 3), nên không có tài liệu ngoài nào bị phá |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không — gate phân giải được thì byte chuẩn tắc không đổi |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không |

## 5. Ảnh hưởng an toàn

Thay đổi này **chỉ siết**: nó từ chối thêm gate, không chấp nhận thêm gate nào.
Nó đóng ba trong bốn bề mặt nới lỏng mà `ENG-A2` đếm được (`allow_when` đã đóng
ở Sprint 1). Bề mặt thứ tư — tái publish gate cha cùng version — thuộc RFC-0003
(ghim `extends` bằng digest), hoãn tới Sprint 4 (`TODOS.md` #15).

Giới hạn đã biết: R3 cho con đổi `escalate.to`. Một người nhận không tồn tại
làm escalation rơi vào khoảng trống — nhưng hành động vẫn bị chặn, nên đó là lỗi
khả dụng, không phải lỗi an toàn.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Khoá hoàn toàn: con có `extends` không được khai `budget`/`on_block` | Phá `gates/unlock_door_night@1.0.0.yaml` (đổi sang `night_duty_manager`, hợp lý) và cấm cả việc siết `p95` vốn an toàn |
| Thứ bậc đầy đủ cho `on_block` (`deny > escalate > ask > degrade`, so sánh `fallback_action`) | `escalate` có "chặt hơn" `ask` không là câu hỏi không có đáp án kiểm được. Chỉ `degrade` thực thi hành động — đó là ranh giới duy nhất cần kiểm |
| Hoãn, ghi rủi ro vào threat model | Lời hứa cốt lõi sẽ sai suốt demo 2026-10-25 và bản PyPI đầu tiên (`TSK-S3-14`) |

## 7. Bằng chứng kiểm chứng *(`TSK-S2-13`)*

- [x] Ví dụ hợp lệ: 3 gate mẫu + 5 fixture `valid/` vẫn phân giải; thêm `valid/keeps_inherited_degrade.yaml`
- [x] Ví dụ sai: `invalid/loosens_p95.yaml` (R1), `invalid/reopens_closed_chain.yaml` (R2), `invalid/introduces_degrade.yaml` (R3), `invalid/changes_fallback_action.yaml` (R3) + mục tương ứng trong `expected_errors.yaml`
- [x] Test tự động: 10 test `test_rfc0004_*` trong `test_gate_resolver.py`, gồm chính trường hợp `lax-night`; bộ test 210 → 229, 0 skip
- [x] `neuroedge gate lint` xanh trên `gates/` (3) và `fixtures/gates/valid/` (6), thoát 1 trên `fixtures/gates/invalid/` (19)

## 8. Việc phải làm khi chấp thuận

- [x] Hiện thực R1–R3 trong `python/neuroedge/engine/gate_resolver.py` (`_resolve_budget`, `_resolve_on_block`), bỏ comment "on_block không chịu quản trị B.5"; kèm `lru_cache` cho `_gate_schema()` (TODOS #5, ENG-Q4)
- [x] Cập nhật Phụ lục B.5 của `neuroedge-proposal.md` *(phiên 2026-09-23)*
- [x] Cập nhật FR-GATE-06 trong `neuroedge-prd.md` *(phiên 2026-09-23)*
- [x] Cập nhật `neuroedge-roadmap.md`: `TSK-S2-13` *(phiên 2026-09-23)*
- [x] Thêm fixture và test (§7); registry thêm `degrade-base@1.0.0.yaml`
