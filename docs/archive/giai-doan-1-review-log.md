# Biên bản review — Giai đoạn 1 (lưu trữ)

> **Lưu trữ, không quy phạm.** Đây là biên bản các vòng review kế hoạch Giai đoạn 1
> ngày 2026-09-22 (adversarial spec review, `/plan-eng-review`, `/autoplan` CEO → DX → Eng),
> tách khỏi [`docs/designs/giai-doan-1-wedge-truoc-mcu-sau.md`](../designs/giai-doan-1-wedge-truoc-mcu-sau.md)
> để tài liệu thiết kế đọc được. Giữ lại để truy nguồn *vì sao* một quyết định được chọn.
>
> Kết luận của các vòng review đã thành quyết định `Q-10`, `Q-11`, `Q-14` → `Q-20`
> (`neuroedge-prd.md` §15) và task trong roadmap §4.2–§4.3. Khi biên bản này và các
> nguồn đó lệch nhau, **các nguồn đó đúng**. Giải mã `CEO-*`, `ENG-*`, `DX-*`:
> [`docs/user/thuat-ngu.md`](../user/thuat-ngu.md) §3.
>
> Số dòng trích dẫn bên trong (`prd:318`, `roadmap:121`, `design:1299`…) là số dòng
> **tại thời điểm review** và phần lớn đã trôi.

## Reviewer Concerns

Hai vòng review đối kháng: 38 phát hiện / 5-10, rồi 33 phát hiện / 7-10. Vòng 2
xác nhận 12 hạng mục tôi sửa ở vòng 1 là **đúng dữ kiện**. Dừng vòng lặp ở đây
(mức cho phép là 3) vì phần còn lại là độ chính xác và kế toán, sửa trực tiếp
được, và nhiệm vụ chính của phiên là review kỹ thuật roadmap chứ không phải
tài liệu tiền đề này.

**Đã sửa trong bản này:** kế toán task (12 chạy / 13 hoãn / 25 tổng), bảng tiêu
chí ra hợp nhất 12 dòng, số dòng citation roadmap `:568`/`:569` (vòng 2 tôi ghi
sai thành `:572`/`:573`), `prd:144` thay cho nhãn `J1`, `python/pyproject.toml`
thay cho `pyproject.toml`, `374 kB` thay cho `376 KB`, neo hệ tuần, F1, nhánh
Q-11 bị từ chối, waiver §11.3, cắt `TSK-S2-02`, định nghĩa "bản mỏng" S2-08,
delta cho tiêu chí A2, công bố phạm vi đo P3, việc cho V2, `RFC-0002` trả về
Tháng 9, nợ văn bản #8.

**Còn lại, ghi ra thay vì che:**

1. **Mục "What I noticed" là meta về phiên làm việc.** Giữ vì mẫu `/office-hours` yêu cầu. **Không mang tính quy phạm** — người tiếp quản bỏ qua được.
2. **Năm nguồn của P2 chưa được xác minh từ nguồn gốc.** Hai mục chưa đọc toàn văn; ba mục còn lại chỉ có tiêu đề hoặc bản tóm tắt. P2 đủ để **hạ một tuyên bố quá mức của mình**, **chưa đủ** để dùng trong tài liệu đối ngoại.
3. **Ước lượng vẫn là ước lượng**, và điểm vỡ thật là F1, không phải số ngày/task.
4. **`TSK-S3-14` làm Sprint 3 thành 14 task và Sprint 2-3 thành 25** *(đếm lại ở CEO review: Sprint 3 là **15** task — `S3-01..13` + `14` + `15` — và Sprint 2-3 là **26**; xem `CEO-S0-1`)*. Roadmap phải được sửa cho khớp, nếu không "24 task" sẽ tiếp tục được trích dẫn sai.

## What I noticed about how you think

*(Không mang tính quy phạm — xem Reviewer Concerns #1.)*

- Tôi đề xuất review Sprint 2. Bạn gõ lại **"Review roadmap phase 1"**. Bạn không nhận phạm vi tôi đưa mà tự đặt lại — và phạm vi của bạn đúng hơn, vì Sprint 2 vừa bị CR-1.0 viết lại nên không review rời khỏi cả Giai đoạn 1 được.
- Ở D6 tôi nói thẳng không tìm thấy bằng chứng nhu cầu nào và khuyên chọn "chưa có". Bạn chọn **"đã có người trả tiền"**. Rồi khi tôi đẩy tiếp một nhịp, bạn tự hạ xuống **"ngân sách R&D, chưa gắn khách"**. Không ai làm thế nếu đang cố bán ý tưởng cho chính mình.
- Tôi khuyên chạy Codex để đánh sập tiền đề tôi vừa dựng. Bạn **từ chối**. Hai vòng reviewer sau đó tìm ra 71 phát hiện, trong đó bảy cái là lỗi dữ kiện của tôi. Ghi lại như dữ liệu về cái giá của việc bỏ một vòng kiểm tra chéo — không phải để nhắc lại.
- Commit `eddfc59` đổi `C1-C7` thành `TR-1..TR-7` vì hai bộ nhãn trùng tên, và `R1-R4` thành `PF-1..PF-4` vì `R` mang hai nghĩa trong cùng một hàng bảng. Không ai sửa hệ ký hiệu trong một dự án chưa có người dùng — trừ khi họ định để nó sống lâu.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/autoplan` Phase 1 | Scope & strategy | 1 (+2 vòng spec review, 7/10) | ISSUES_OPEN (PLAN) | 38 phát hiện + 17 spec review + 17 tiếng nói ngoài · 50 auto-decided · 6 USER CHALLENGE · 4 TASTE DECISION |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` + `/autoplan` Phase 3 | Architecture & tests (required) | 2 | ISSUES_OPEN (PLAN) | vòng 1: 8 issue, 1 critical gap, 2 unresolved · vòng autoplan: **3 phát hiện CRITICAL** (`ENG-A1` ba chân · `ENG-A2` · `ENG-A2b`, 5 chế độ hỏng), +2 task, +1 RFC |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/autoplan` Phase 2.5 | Developer experience gaps | 1 | ISSUES_OPEN (PLAN) | 18 phát hiện · 3 CRITICAL · DX tổng **4/10** · TTHW **không tới được** |
| Outside Voice | `/plan-eng-review` | Independent plan challenge | 1 | ISSUES_FOUND (claude) | 14 phát hiện, 5 đã kiểm chứng |

**OUTSIDE VOICE:** Codex `ready` ở preflight nhưng **401 Unauthorized** lúc gọi
thật (refresh token hết hiệu lực) → fallback sang Claude subagent: ngữ cảnh mới,
**cùng họ mô hình, không phải mô hình ngoài**. Chạy `codex login` để lần sau có
góc nhìn ngoài thật. Nó tìm 14 phát hiện; tôi kiểm chứng 5 điểm chịu lực nhất và
**cả 5 đều đúng**.

**CROSS-MODEL:** Bốn tension, tất cả đã quyết, tất cả đảo hoặc sửa một quyết
định trước đó của review:

| # | Review nói | Outside voice nói | Quyết |
|:---:|:---|:---|:---|
| 1 | Tiêu chí ra Sprint 2 #3 là phép đo trực tiếp của P3 | Phép đo đó rỗng: "S2-08 bản mỏng" cắt đúng fallback cục bộ mà **Q-4 đã chốt** (`roadmap:840`), còn lại là mock trả rỗng — việc `engine/__init__.py:76–87` đã làm trong 8 dòng | **T1A** — khôi phục fallback Sherpa-ONNX vào A1 |
| 2 | Phương án A là wedge | A là platform: chi phí tiếp cận cao hơn đối thủ *"để tôi tự viết trong hai tuần"*, và trái Tiêu chí ra Sprint 3 #1 | Giữ A (T1A cứu lý do chọn A). Nửa đúng của lập luận đã xử qua **TODO 1**: un-defer `TSK-S3-07` để hạ chi phí tiếp cận |
| 3 | Issue 3 duyệt token gắn digest + chân + phiên | Token nonce **không ghi được** ở mức sự kiện (`additionalProperties:false`, có fixture phản chứng cưỡng chế); nhét vào `data` thì phá golden comparison | **T3A** — nonce ở bộ nhớ, digest gate vào `event.data` |
| 4 | Cắt `TSK-S2-02` vì không phục vụ tiêu chí ra nào | Nó là cơ chế **duy nhất** cưỡng chế bất biến mà `boards/sim-default.toml` tự khẳng định, và `linux` **đã lệch sẵn** 48 kHz / `aec=false` | **T4A** — khôi phục đầy đủ |

Hệ quả tổng: ước lượng **5 → 6,5 tuần-người V1**; task chạy **13 → 15**; hoãn
**12 → 11**; tổng **25 → 26**. *(Hai con số giữa đã sửa ở CEO review — xem
`CEO-S0-1`; vòng eng review đếm theo **dòng bảng**, không theo **task**.)*

**VERDICT:** ENG REVIEW RUN — 8 issue đã quyết, 14 phát hiện outside voice đã xử
lý, nhưng **NOT CLEARED**: còn 1 critical gap (`gpio-sim` chưa chứng minh được
trên `ubuntu-latest`, và nó là con đường duy nhất cho `TSK-S3-05`) và 2 quyết
định chưa ai chốt. CEO / Design / DX review chưa chạy và không gate việc ship.

**UNRESOLVED DECISIONS:**
- **`TSK-S2-11` có hạn cứng trong cửa sổ kế hoạch mà kế hoạch không thừa nhận.** `roadmap:235` ghi nó *"phải xong trước Tuần 6"* (= Tuần 5 của tài liệu này) vì `TSK-S3-13` và `TSK-S5-06` phụ thuộc. Kế hoạch hoãn nó với lý do **"chặn bởi Q-11"** — một lý do **hết hiệu lực ngay Tuần 1** khi Q-11 được chốt, và không có gì thay thế. Hoặc kế hoạch âm thầm phá một hạn cứng của roadmap, hoặc một task thứ 15 xuất hiện ở Tuần 2 không có chủ trì và không có ước lượng. **Cần kỹ thuật trưởng chốt, Tuần 1.**
- **Waiver §11.3 chưa có ai duyệt.** `roadmap:914` cấm hợp nhất Gate Engine kèm ghi chú "sẽ sửa sau"; kế hoạch làm đúng điều đó (`TSK-S2-03` trên test double, ba trong bốn hành vi `on_block` chỉ ghi vết ghi). Ngoài ra §11.2 DoD đòi *"tiêu chí nghiệm thu PRD đạt **và được ghi lại**"* mỗi hạng mục — `TSK-S2-08` dù đã đầy đủ vẫn chưa chắc thoả `FR-MDL-01/02/03`, và nếu DoD gate việc merge thì đầu ra A1 không merge được và A2 mất nền. Waiver hiện chỉ xử nhãn trạng thái, **không xử cổng merge**. **Cần kỹ thuật trưởng chốt, Tuần 1.**

## GSTACK CEO REVIEW REPORT

Chạy qua `/autoplan` Phase 1 ngày 2026-09-22, mode **SELECTIVE EXPANSION**.
Bản đầy đủ (Step 0 · Section 1–10 · 4 registry · Decision Audit Trail 50 dòng):
`~/.gstack/projects/letrongminh-neuroedge-init/ceo-plans/minhlt-docs-autoplan-ceo-dx-review-ceo-review-20260922-085500.md`

**TIẾNG NÓI NGOÀI:** `[subagent-only]`. `codex exec` trả **401 `invalid_refresh_token`**
lần thứ ba; đã probe lại trong phiên này để chắc chắn. Chạy `codex login` để lần sau có
mô hình ngoài thật. Tiếng nói Claude tìm 17 phát hiện; tôi kiểm chứng 6 dẫn chứng chịu
lực nhất (`grep` trên bốn tài liệu gốc) và **cả 6 đều đúng**.

### CEO DUAL VOICES — CONSENSUS TABLE

| Chiều | Claude | Codex | Consensus |
|:---|:---|:---|:---|
| 1. Premise có vững? | NO | N/A | **FLAGGED** |
| 2. Đúng bài toán? | NO | N/A | **FLAGGED** |
| 3. Hiệu chỉnh phạm vi đúng? | NO | N/A | **FLAGGED** |
| 4. Phương án đã xét đủ? | NO | N/A | **FLAGGED** |
| 5. Rủi ro cạnh tranh đã phủ? | NO | N/A | **FLAGGED** |
| 6. Quỹ đạo 6 tháng vững? | NO | N/A | **FLAGGED** |

**0/6 CONFIRMED · 6/6 FLAGGED.** Đọc cho đúng: 0/6 CONFIRMED **không** nghĩa là qua
được — nó nghĩa là không có mô hình thứ hai để đối chiếu, nên mọi phát hiện CRITICAL đi
thẳng tới Final Gate thay vì được một vòng cross-model lọc trước.

### Tổng kết

38 phát hiện của review (7 CRITICAL · 14 HIGH · 12 MEDIUM · 3 LOW, cộng 1 gộp
vào mục khác và 2 phát sinh ở vòng spec review — `CEO-S0-1`, `CEO-S0-2`)
+ 17 issue của spec review (điểm **7/10**) + 17 của tiếng nói
ngoài. **50 auto-decided.** Task **26 → 32**, chạy **15 → 21** (18 V1 + 3 V3), hoãn **11**. Sáu task mới:
`TSK-S2-12` đặc tả ngữ nghĩa quyết định · `TSK-S3-16` cổng CI `digests.lock` ·
`TSK-S3-17` đóng gói asset vào wheel · `TSK-S3-18` `gate explain` ·
`TSK-S3-19` `verify` đếm artifact (Phase 2.5) · `TSK-S3-20` README gốc (Phase 2.5). Ước lượng **6,5 → ~7,2
tuần-người V1** ở vòng này (+5 ngày: cổng digest, hai tài liệu spec, provision mô hình Sherpa, ghi
vết ghi trên đường ném, 9 test mới, siết `fail_closed`, chia `TSK-S3-14`) — **vòng spec review 2
nâng lên ~8,6; xem §Ước lượng, nói thật sau khi cộng hết**.

**Phát hiện nặng nhất của review — `CEO-S5-2`, và nó nằm trong mã đã merge.**
Bốn mặc định trong bộ khung test đều là giá trị "an toàn":
`HardwareAbstractionLayer.pin()` và `ReplaySession.pin()` trả `PinAssertion(pulsed=False)`
cho pin **không tồn tại**; `ReplaySession.action()` trả `blocked=True`; `.gate()` trả
`verdict="BLOCK"`. Nên `hal.pin("door_lok").never_pulsed()` ⇒ `True` ⇒ **test xanh**.
Tiêu chí ra Sprint 2 #2 và Sprint 3 #3 đều nghiệm thu bằng `never_pulsed()`. Fail-closed
đúng cho **thời gian chạy**; cho **assertion** thì ngược — assertion phải fail-**loud**.
Đây đúng là loại lỗi mà sản phẩm này bán thứ chống lại.

**Khuyến nghị kiến trúc số một — bốn mục hội tụ (`CEO-S1-1` / `S5-4` / `S7-1` / `S10-1`).**
Ngữ nghĩa quyết định sẽ có **ba** hiện thực: `is_at_least_as_strict_as()` lúc build (đã
có), vị từ thuộc-về lúc chạy (`TSK-S2-03`, chưa viết), trình duyệt cây C cho MCU (Q-9
phương án A). Ba hiện thực của một ngữ nghĩa = ba cơ hội lệch nhau, và "cùng gate, phán
quyết y hệt trên ba target" là thứ đang bán. Quyết: `evaluate()` **đi trên cùng cây
quyết định** mà trình biên dịch sinh ra. Giá hôm nay ≈ 0 (chưa viết dòng nào); giá ở
Sprint 4 = chứng minh tương đương giữa hai hiện thực độc lập. Reversibility của hình
dạng engine: **2/5**.

### Vòng spec review đối kháng (0D-POST) — 25 khẳng định kiểm chứng, 5 của tôi sai

Reviewer ngữ cảnh sạch, đọc mã và **chạy test thật**, không chỉ đọc tài liệu. Kết quả:
**22/25 khẳng định chịu lực đúng chính xác** (gồm 10/10 trích dẫn dòng trong bốn tài liệu
gốc), 5 sai. Cả 5 là lỗi của tôi và tôi đã kiểm chứng lại từng cái:

| Tôi ghi | Thật là | Kết luận dựng trên nó |
|:---|:---|:---|
| `CEO-S1-4`: gốc là `parents[3]` trong `testing/`, sửa bằng `paths.py` | **Gốc là wheel không chứa asset nào**; `paths.py` là *cùng* lỗi | **ĐỔI** — nặng hơn: HIGH → CRITICAL, phạm vi từ `replay()` thành *mọi lệnh*. Xem khối `CEO-S1-4` dưới |
| `prd:120` U3 "Chính (từ v1.1)" | `prd:122` | **SỐNG** — `CEO-X5` không đổi |
| `proposal:230` cam kết SemVer | `proposal:231` | **SỐNG** — `CEO-S1-7` không đổi |
| `engine/__init__.py` có 19 tên trong `__all__` | **18** | **SỐNG** — vẫn phải tách `contract.py` |
| Dream state: `run`·`test`·`record`·`replay`·`new` thoát mã 2 | `PENDING` (`cli/main.py:52`) = `new`·`run`·**`build`**·`test`·`record`. **`replay` đã hiện thực** | **ĐỔI, và làm `CEO-S5-1` mạnh hơn** — `replay` dùng được **hôm nay**, và nó đọc vết ghi bằng `json.load` thô, không qua `trace.py`. Lỗ không phải tương lai, nó đang mở |

**`CEO-S0-1` · HIGH · Danh sách cắt tự đếm sai, ba vòng review trước bỏ qua.**
Kế hoạch ghi "14 chạy / 12 hoãn" và "11 V1 + 3 V3". Nguồn lỗi: dòng bảng `TSK-S3-01..04`
gộp **bốn** task vào **một** dòng, nên tiêu đề A2 được viết theo *số dòng* (3) chứ không
theo *số task* (6). Đếm lại, mọi task ID được tính đúng một lần:

| Sprint | Universe | Chạy | Hoãn |
|:---|:---|:---|:---|
| Sprint 2 | `S2-01..11` = 11 | 01·02·03·04·05·08 = **6** | 06·07·09·10·11 = **5** |
| Sprint 3 | `S3-01..13` + 14 + 15 = 15 | 01·02·03·04·05·06·07·14·15 = **9** | 08·09·10·11·12·13 = **6** |
| **Tổng** | **26** | **15** (12 V1 + 3 V3) | **11** |

Đã sửa bốn chỗ trong tài liệu này (`:195`, `:199`, tiêu đề A2, tiêu đề bảng hoãn), số của
vòng eng review (*"12 → 14; 13 → 12"*, đúng là *"13 → 15; 12 → 11"*), và **F2**: A2 là
6 task / 10 ngày = **1,67 ngày/task**, không phải 2,0. F2 vốn đã là *"chỗ yếu nhất của
ước lượng"*; con số đúng làm nó yếu hơn, và gần như toàn bộ việc CEO review thêm vào đều
rơi vào A2.

### Spec review vòng 2 — 17 issue, điểm **7/10**, hai cái làm tôi phải đảo quyết định

`FALLS: 5, 12` — hai kết luận của tôi chết theo dữ kiện đã sửa. Mười lăm cái còn lại sống,
nhưng **bốn** cái buộc sửa cơ chế, không chỉ sửa câu chữ.

**Issue 2 · CRITICAL · Cách sửa `CEO-S5-2` của tôi làm đỏ đúng ba test nó định bảo vệ.**
`python/tests/test_testing.py:16, 25, 33` đều assert `s.pin("door_lock").never_pulsed()`
trên `unverified_attempt.json` và `network_offline.json` — hai vết ghi **không có sự kiện
`actuator_command`**, nên `_pins` rỗng. "Ném khi tên không có trong vết ghi" ⇒ cả ba ném.
Và ba test đó **chính là** cơ chế nghiệm thu của Tiêu chí ra Sprint 2 #2 và Sprint 3 #3.
Tôi đã nhập nhằng hai chuyện khác nhau.
→ **SỬA:** phân biệt *"tên không khai ở đâu cả"* (ném) với *"đã khai, chưa từng được kích"*
(trả `pulsed=False`). Việc này đòi `ReplaySession` nạp `BoardProfile` — hôm nay nó chỉ có
`target`, không có board — nên **"nạp `BoardProfile` vào `ReplaySession`" thành deliverable
có tên** của `TSK-S3-03`. Và bỏ chỗ ghim cứng `unlock_door` **trước**, cùng task, vì phần
ném phụ thuộc vào nó.

**Issue 7 · HIGH · Ba auto-decision của tôi cộng lại làm `budget_exceeded` thành mã chết.**
`CEO-S7-1` đưa phân giải gate ra khỏi đường chạy; `CEO-S7-2` đẩy tri giác ra khỏi cửa sổ
đo; `CEO-S6-1` tiêm đồng hồ tất định. Còn lại trong cửa sổ là một lượt đi
`dict[str, Constraint]` — **micro-giây**. Ngân sách 90 ms không bao giờ vượt được, nên
`budget_exceeded` là một `if` không bao giờ đúng, và `budget.fail` (`open`/`closed`) mất
nghĩa. Tôi lại gọi đúng chỗ hội tụ đó là *"tín hiệu mạnh nhất trong review này"*.
→ **SỬA `CEO-S7-2`:** cửa sổ đo bắt đầu khi `evaluate()` **bắt đầu thu dữ kiện** — tức
**gồm** các lời gọi thẩm định (`SystemOne`, kể cả qua mạng) — và kết thúc ở phán quyết.
Chỉ **tri giác** (âm thanh → intent) ở ngoài. Đó mới là thứ ngân sách nói về: nó là
timeout của **bộ phán định**, và là lý do `gate_unreachable` cùng `fail: open/closed` tồn
tại. Cách đọc cũ của tôi lẫn *tri giác* với *thẩm định*.

**Issue 11 · HIGH · `CEO-S1-1` đề xuất sửa một tệp đang bị RFC gate, và không cần sửa.**
`CONTRIBUTING.md` §3 ghi rõ *"Sửa ngữ nghĩa phân giải gate (`gate_resolver.py`,
`constraints.py`) → **RFC bắt buộc**"*. Tôi viết *"`constraints.py` sinh cây, giá hôm nay
≈ 0"* — sai cả hai nửa: nó cần RFC, và nó dư.
→ **SỬA:** để nguyên `constraints.py`. Cây quyết định suy ra từ `ResolvedGate.to_artifact()`
trong `TSK-S2-12`. Thêm `decision_tree.v1.json` vào danh sách RFC và vào `digests.lock`.
**Kết luận của `CEO-S1-1` không đổi** (một ngữ nghĩa, ba người tiêu thụ) — chỉ cơ chế đổi.

**Issue 6 · HIGH · TTL = p95 hết hạn ~5% token hợp lệ, và test sẽ không thấy.**
p95 là ngưỡng thống kê: theo định nghĩa ~5% lần thẩm định hợp lệ vượt nó. Đặt TTL = p95 ⇒
~5% token hợp lệ chết trước khi dùng — một lỗi **khả dụng** âm thầm trong sản phẩm bán
fail-closed, và `CEO-S6-1` (đồng hồ tất định) đảm bảo test không bao giờ thấy.
→ **SỬA:** `TTL = p95 × k`, **k = 3**, ghi rõ lý do. Và `token_expired` là `reason` **riêng**,
không gộp vào `token_replayed` — hai chuyện khác nhau với hai cách xử lý khác nhau.

**Issue 8 · HIGH · `digests.lock` trên "26 fixture" không chạy được.**
15 trong 26 là fixture phản chứng — **không phân giải được**, nên không có digest. Và
3 gate thật trong `gates/` lại không nằm trong 26.
→ **SỬA:** lock `gates/**` + `fixtures/gates/valid/**` + `fixtures/gates/registry/**` =
**14 tệp**. Và `CONTRIBUTING.md` §3 phải phân biệt *digest mới* (thêm gate, PR thường) với
*digest đổi* (breaking, cần RFC).

**Issue 15 · MEDIUM · "Restart huỷ mọi token sống" là câu không hiện thực được.**
Tập nonce ở bộ nhớ thì sau restart **không còn token nào để huỷ**. Rủi ro thật là token
mint **trước** restart được xuất trình **sau**.
→ **SỬA:** token mang `process_instance_id`; `consume()` từ chối token của tiến trình khác
với `NE1002`.

**`CEO-S0-2` · HIGH · Kế hoạch nói cửa sổ 5 tuần và xếp việc tới Tuần 6,5. Bốn vòng review
không ai nêu.**
`:210` A1 = **Tuần 1–4,5** · `:232` A2 = **Tuần 4,5–6,5**. Nhưng `:386` ghi *"Hết 5 tuần"*
và `:423` ghi *"Tuần 5 là tuần cuối"*. Lệch **1,5 tuần**, và nó chịu lực: `TSK-S3-14` hạn
Tuần 5 bị xếp **bên trong** A2 vốn chạy tới 6,5; còn lập luận *"Tiêu chí ra Sprint 3 #1
không đóng được vì Tuần 5 là tuần cuối"* dựng trên một con số mà chính lịch task phủ định.
→ **Cần chốt cùng `CEO-X6`:** cửa sổ là 5 tuần hay 6,5 tuần. Đây là đầu vào của quyết định
Tuần 0, không phải chuyện chữ nghĩa.

### Ước lượng, nói thật sau khi cộng hết

Issue 4 đúng: số cũ của tôi không khép. Bảng việc thêm cộng ra 5,5 ngày ≈ 1,1 tuần, nên
6,5 + 1,1 = **7,6**, không phải 7,2 như tôi ghi. Và Issue 9 đúng tiếp: A2 là **6** task
trong 10 ngày, mà `F3` đã tính DoD chiếm ~1 trong 2,0–2,5 ngày mỗi task — nên A2 ở mức
1,67 ngày/task là **không khả thi**, chưa nói tới 9 deliverable mới mà review này đổ gần
hết vào A2.

| | Kế hoạch ghi | Sau CEO review |
|:---|:---:|:---:|
| A1 | 4,5 | **~4,9** |
| A2 | 2,0 | **~3,7** |
| **Tổng tuần-người V1** | **6,5** | **~8,6** *(4,9 + 3,7; +0,2 của Phase 2.5 đã gộp vào A2)* |

**Và đây là chỗ phải nói thẳng: 8,6 tuần-người của một người trên đường găng không lắp
vào cửa sổ 5 tuần — mà 6,5 thì cũng đã không lắp.** Con số đó không mới sinh ra từ CEO
review; nó đã sai từ trước và bị che bởi `CEO-S0-2`. Đường thoát đã có sẵn trong kế hoạch,
`F2` đã chốt trước: **golden reference ra bản `sim`-only, `TSK-S3-04` so khớp xuyên target
trượt sang `TSK-S4-04`**. Dùng nó, hoặc thừa nhận cửa sổ là 6,5–9 tuần. Không có đường thứ ba.

### 11 issue còn lại — đã nhận, sửa câu chữ và kế toán

| # | Mức | Quyết |
|:---:|:---:|:---|
| 3 | HIGH | "Auto-decided: 43" → **50**, khớp bảng 1→50 và khớp `§GSTACK CEO REVIEW REPORT`. Đã sửa |
| 5 | HIGH | "14 chạy / 12 hoãn" → **15 / 11**; 6 chỗ trong tài liệu + F2. Đã sửa (`CEO-S0-1`) |
| 9 | HIGH | A2 ≈ 3 tuần, hoặc dùng fallback `F2` đẩy `TSK-S3-04` sang Sprint 4. Đã vào bảng ước lượng |
| 10 | HIGH | `gate explain` → **`TSK-S3-18`** (có ID, có ước lượng). `--json` **không** thành task riêng: nó là cờ toàn CLI, giao làm deliverable có tên của **`TSK-S3-06`** (vỏ lệnh + hợp đồng mã thoát) |
| 12 | MEDIUM | `PENDING` là **5** stub, không 3: `new`·`run`·`build`·`test`·`record` ⇒ **5/7** lệnh thoát mã 2 hôm nay. `build` tôi bỏ sót hoàn toàn — **và nó mở ra một câu chưa ai hỏi: `build` có mở được khi `TSK-S2-06` (CEL) còn hoãn?** Thêm vào §Open Questions |
| 13 | MEDIUM | `"KeyError (hoặc NE4001)"` là một chữ *hoặc* chưa quyết, vi phạm `FR-DX-04`. Một lớp: **`TraceAssertionError(TraceValidationError)` = NE4003** |
| 14 | MEDIUM | Bảng mã lỗi: bỏ `NE2004` treo, sửa lớp cha về `GateError`, tách TTL khỏi `TokenReplayError` thành `token_expired` |
| 16 | MEDIUM | `logging` **không** neo được vào FR nào, và chưa có embedder thật. Nhận **trên cơ sở chi phí và thời điểm** (20 dòng bây giờ vs sau khi `TSK-S2-03` thêm ~400 dòng), nói thẳng thế, không giả vờ có yêu cầu |
| 17 | MEDIUM | Dọn tự tham chiếu cũ: gắn nhãn `CEO-S5-5`, đánh dấu #15 và #44 là dòng trùng không tính, làm mới hai chỗ trích `Status`/`VERDICT` đã lỗi thời |
| 18 | LOW | `--allow-policy-change` chưa có ca dùng nào tới được trong Tuần 5 → **hoãn kèm mốc**. Giữ tag bảo vệ + Environment; **OIDC chuyển sang lần publish thật**, không phải TestPyPI |

**Task sau hai vòng spec review: 26 → 30** (`TSK-S2-12` · `TSK-S3-16` · `TSK-S3-17` ·
`TSK-S3-18`) · chạy **15 → 19** · hoãn **11**. *Phase 2.5 (DX) thêm hai nữa —
`TSK-S3-19`, `TSK-S3-20` — nên số cuối là **32 / 21 / 11**.*

### Reviewer Concerns — còn lại, ghi ra thay vì che

1. **Điểm 7/10 là điểm của tài liệu, không phải của kế hoạch.** Reviewer chấm chất lượng
   *bản review*; nó không phát biểu gì về việc kế hoạch có nên chạy hay không. Sáu
   `USER CHALLENGE` vẫn mở nguyên.
2. **Vòng lặp dừng ở 2, mức cho phép là 3.** Dừng vì phần còn lại là kế toán và câu chữ,
   sửa trực tiếp được — nhưng hai vòng đã đảo bốn cơ chế của tôi (Issue 2, 6, 7, 11), nên
   **tỉ lệ sai của tôi ở vòng này không thấp**, và một vòng thứ ba có thể còn tìm ra nữa.
3. **Ước lượng ~8,6 tuần-người là ước lượng của tôi, không phải của V1.** F3 đã cảnh báo
   chi phí DoD; tôi chưa hỏi người sẽ làm. Con số cần V1 xác nhận trước khi dùng để quyết
   bất cứ điều gì.
4. **`CEO-S1-4` đã đảo một lần.** Chẩn đoán hiện tại có bằng chứng chạy được (wheel thật,
   venv sạch, `force-include` đã thử), nhưng nó là bản **thứ hai**. Đừng coi nó là đã yên.

### Failure Modes Registry — 6 chế độ hỏng CRITICAL mới

| # | Chế độ hỏng | Xử |
|:---:|:---|:---|
| 1 | Fallback offline cần tệp mô hình Sherpa mà kế hoạch không nói từ đâu → nếu tải lúc chạy thì thiết bị **chưa bao giờ online không thể fallback**, và Tiêu chí ra Sprint 2 #3 đo cái không tồn tại | Mô hình ghim digest, provision lúc build; NOTICE cho runtime **và** trọng số (giấy phép riêng); test trong môi trường không mạng, không cache (`CEO-S3-2`) |
| 2 | Ba gate viết tay khai p95 **200/120/90 ms** và T1A vừa đặt suy luận ONNX vào đường quyết định — chưa ai đo | Chốt mốc đo (không gồm tri giác) + buộc `TSK-S2-08` in p95 thật (`CEO-S7-2`) |
| 3 | `fail_closed=False` là feature flag công khai tắt **toàn bộ** tính chất an toàn, im lặng, không sự kiện vết ghi. `NFR-RES-04` là P0 "không thương lượng" | 4 cổng: env var `NEUROEDGE_UNSAFE_FAIL_OPEN=1` · cảnh báo mỗi lần khởi tạo · sự kiện `unsafe_mode` vào vết ghi · `verify` từ chối chạy. Hoặc xoá tham số (`CEO-S9-1`) |
| 4 | Một cái gõ sai tên pin làm test an toàn xanh | Assertion fail-loud + 3 test phản chứng (`CEO-S5-2`) |
| 5 | Tiêu chí A7 ("100% phiên sinh vết ghi qua `trace validate`") vỡ ngay lần engine ném đầu tiên — không chỗ nào trong kế hoạch nói phiên đó có vết ghi hay không | `record` ghi cả trên đường ném: sự kiện `engine_error`, flush, rồi ném lại. Chaos test bằng `SIGKILL` (`CEO-S2-2`) |
| 6 | **Gói publish lên PyPI không chạy được việc gì.** Nâng cấp từ HIGH lên CRITICAL ở vòng spec review — chẩn đoán ban đầu của tôi sai gốc. Xem khối dưới bảng | `TSK-S3-17` (mới): `force-include` asset vào wheel + `paths.py` đọc từ gói + `repo_root()` ném lỗi 3 thành phần thay vì trả đường dẫn không tồn tại (`CEO-S1-4`, đã sửa) |

**`CEO-S1-4` — chẩn đoán lại sau spec review, và nó nặng hơn nhiều.**

Vòng đầu tôi ghi: `testing/__init__.py` dùng `Path(__file__).parents[3]` nên `replay()`
vỡ sau `pip install`, và cách sửa là *"dùng `paths.py`"*. Reviewer đối kháng chỉ ra
**cách sửa đó không sửa được gì**, và tôi đã kiểm chứng bằng cách dựng wheel thật rồi
cài vào venv sạch:

```
$ python -m build --wheel          # hatchling 1.32.4
$ unzip -l neuroedge-0.1.0-py3-none-any.whl
19 tệp — toàn bộ là mã Python.
  schemas   trong wheel: 0
  gates     trong wheel: 0
  boards    trong wheel: 0
  fixtures  trong wheel: 0

$ neuroedge gate lint
✗ no such directory: .../.venv/lib/python3.13/gates

$ neuroedge board list
No board declarations found.          ← trông như "chưa khai board", không phải "gói thiếu tệp"

$ neuroedge trace validate happy-path.json
FileNotFoundError: .../.venv/lib/python3.13/schemas/trace.v1.json   ← traceback trần, KHÔNG phải lỗi 3 thành phần
```

Gốc thật: `python/pyproject.toml:63–64` khai `packages = ["neuroedge"]`, và
`schemas/` · `gates/` · `boards/` · `fixtures/` nằm **ngoài** `python/` theo layout
monorepo (Phụ lục D). Nên **không asset nào vào wheel**. `paths.py::repo_root()` đi
ngược cây tổ tiên tìm thư mục có *cả* `schemas/` và `fixtures/`; trong `site-packages`
không có, nên nó rơi xuống fallback `parents[2]` = `.venv/lib/python3.13`. `paths.py`
**là** cùng một lỗi, không phải cách chữa nó.

Hệ quả cho kế hoạch: nghiệm thu `TSK-S3-14` (*"`pip install neuroedge==<tag>` thành công
trên một máy sạch"*) **sẽ pass** trong khi sản phẩm không làm được gì — vì cài khác chạy.
Và `FileNotFoundError` trần vi phạm `FR-DX-04`.

Cách sửa, **đã kiểm chứng chạy được** (hatchling nhận đường dẫn `../`):

```toml
[tool.hatch.build.targets.wheel.force-include]
"../schemas"         = "neuroedge/_assets/schemas"
"../boards"          = "neuroedge/_assets/boards"
"../fixtures/traces" = "neuroedge/_assets/traces"
```

cộng ba việc trong `paths.py`: (1) `schemas_dir()` và ba vết ghi chuẩn mực đọc từ
`importlib.resources.files("neuroedge") / "_assets"` **trước**, vì đó là asset đóng băng
của sản phẩm; (2) `gates_dir()` giữ tìm-theo-dự-án (gate là thứ **khách** viết), nhưng
(3) fallback cuối **ném** lỗi ba thành phần nêu `NEUROEDGE_ROOT`, không trả một đường
dẫn không tồn tại. Và nghiệm thu `TSK-S3-14` phải **chạy** `gate lint` + `trace validate`
+ `replay` sau khi cài, không chỉ cài.

### Error & Rescue Registry — 4 lớp lỗi mới, cấp phát TRƯỚC khi viết code

| Mã | Lớp | Cha | Task sở hữu |
|:---|:---|:---|:---|
| **NE1002** | `TokenReplayError` | `ActionContractViolation` | `TSK-S2-05` |
| **NE3002** | `GpioUnavailableError` | `BoardCapabilityError` | `TSK-S3-05` |
| **NE4002** | `TraceRecordError` | `TraceValidationError` | `TSK-S3-01` |
| **NE4003** | `TraceAssertionError` | `TraceValidationError` | `TSK-S3-03` — assertion gọi tên không có trong vết ghi (spec review Issue 13: `"KeyError hoặc NE4001"` là một chữ *hoặc* chưa quyết, vi phạm `FR-DX-04`) |
| **NE5001** | `PerceptionUnavailableError` | `NeuroEdgeError` | `TSK-S2-08` |

*(Spec review Issue 14: `NE2004` đã bỏ — tôi cấp phát nó "để dành" mà không có ca dùng, đúng nghĩa là mã treo.)*

**Không ném — trả PHÁN QUYẾT** (phải vào vết ghi để phát lại được):
`condition_not_met` · `criterion_unavailable` · `confidence_unavailable` ·
`gate_unreachable` · `budget_exceeded` · `token_replayed` · `token_expired` (hai cái
cuối tách riêng theo spec review Issue 6). Cộng hai **sự kiện** vết ghi: `unsafe_mode`,
`engine_error`.

### USER CHALLENGE — 6 mục cần phán đoán của người, KHÔNG auto-decide

| ID | Vấn đề | Giá của việc cứ thế mà đi |
|:---|:---|:---|
| **`CEO-X1`** | **Hai tiêu chí nghiệm thu P0 của PRD không thể cùng pass.** `prd:318` (FR-ACE-03, P0) nghiệm thu là *"`network=offline` → hành động bị **chặn** với `gate_unreachable`"*. Success Criterion #3 của kế hoạch này nói offline ⇒ *"hệ thống **vẫn quyết được**"* bằng bộ trích xuất cục bộ. Và `prd:703` (R-6) xếp fallback cục bộ là *"**bổ sung tuỳ chọn** cho khách hàng yêu cầu vận hành ngoại tuyến"* — moat đang dựa trên tính năng PRD gọi là optional, trong kiến trúc CR-1.0 vừa đưa tri giác lên cloud | Ba vòng review trước đã bỏ qua. Đọc theo FR-ACE-03 ⇒ phép đo P3 quay lại thành `if` 8 dòng mà `engine/__init__.py:76–87` đã làm, T1A mất lý do tồn tại, A1 nhỏ lại ~1 tuần, moat yếu đi. Đọc theo kế hoạch ⇒ **PRD phải sửa** và fallback cục bộ lên P0, tức CR-1.0 cần carve-out có văn bản |
| **`CEO-X2`** | **Premise thương mại chịu 100% số tiền không nằm trong §Premises.** Bốn premise P1–P4 đều về *bài toán*; không có premise nào về *kinh doanh*. Giả định thật: *"$1/thiết bị/tháng, trên thiết bị do bên thứ ba làm và bán, đạt hàng chục nghìn đơn vị"*. `proposal:1059` G1 = 10.000 thiết bị = **$120k/năm**; `:1063` hoà vốn cần *"hàng chục nghìn trở lên"*; $3M cần 250.000 thiết bị. Không phép thử phủ định, không chủ trì | 6,5–7,2 tuần-người vào một kiến trúc mà không ai kiểm giả định làm nó thành doanh nghiệp. Phép thử rẻ, không cần code: *có tổ chức nào hôm nay vận hành ≥1.000 thiết bị có cơ cấu chấp hành và sẽ trả theo thiết bị cho quản lý chính sách an toàn?* |
| **`CEO-X3`** | **P4 nói rủi ro số một là nhu cầu, rồi phân bổ ngược 40:1.** ~260 giờ kỹ thuật đường găng vs **8 giờ** discovery (4h/tuần × 2 tuần), trong khi cần 15–30 lượt tiếp cận cho 3 cuộc có bản ghi. Cộng: (a) nền của P4 vòng tròn — nợ #9 tự ghi cách giảm thiểu `R-1` là spike Tuần 2, kế hoạch hoãn bo mạch nên spike không xảy ra, mà P4 dựa chính xác vào lần hạ `R-1`; (b) cổng Tuần 3 tự nhận nhánh **dễ xảy ra nhất** là "<3 cuộc → A2 khởi động **vô điều kiện**", nên P1 chưa kiểm chứng suốt cửa sổ mà không hệ quả | Ba lựa chọn: Tuần 1 là tuần discovery (V1 không viết gì, trưởng nhóm 20 giờ) · hoặc cổng Tuần 3 thành **binding** (<3 cuộc ⇒ A2 **không** khởi động) · hoặc nói thẳng P4 sai |
| **`CEO-X4`** | **Approach C bị bác bằng hai lý do không đứng được.** Lý do 1 (*"rẽ khỏi phạm vi ngân sách R&D đã duyệt"*) là khẳng định **thẩm quyền**, không phải sự thật — và D7 nói ngân sách **chưa gắn khách nào**. Lý do 2 (*"bỏ P3 khỏi v1"*): **A cũng bỏ P3 khỏi cửa sổ đo**, chính khối ⚠️ nói thế. Trong 5 tuần, A và C **ngang nhau về P3**. Kế hoạch tự thừa nhận câu bán được là thứ **C** giao. Hai phương án chưa ai liệt kê: **D** — bán chính bản memo + bản ghi màn hình của những gì Sprint 1 *đã* có (≈1 tuần-người của trưởng nhóm, **0 của V1**, sinh đúng thông tin cổng Tuần 3, sớm 4 tuần); **E** — áp cùng bộ máy gate/Action CI lên **hành động của tác tử thoại trên cloud** (hoàn tiền, đổi tài khoản, cam kết thanh toán): cùng primitive, 0 phần cứng, khách đang trả tiền, có lịch sử sự cố thật | Delta 3,5 tuần-người là **option value thuần**. C không cần waiver, không cần bo mạch, không cần Q-11, không cần `gpio-sim`. Nếu đối thủ thật là *"để tôi tự viết trong hai tuần"* thì A thua nó vì chi phí tiếp cận của A **lớn hơn hai tuần** |
| **`CEO-X5`** | **Dòng doanh thu duy nhất ở cuối chuỗi 4 bên, và lược đồ được cho đi đúng lúc nó có giá.** `prd:122` ghi U3 là *"Chính (**từ v1.1**)"* — người trả tiền chính được xếp lịch xuất hiện sau. Chuỗi: v1.0 miễn phí → lập trình viên ngoài nhận (`prd:229–231`: B1 ≥50 trên `sim`, B2 ≥10 trên phần cứng thật, B3 ≥3 gate cộng đồng) → một người làm ra sản phẩm → bán 100–10.000 đơn vị → chủ vận hành thành U3 → U3 mua. Không khâu nào NeuroEdge kiểm soát. Cầu nối được chỉ định là **AURA** (`proposal:1105` "Early Revenue") nhưng `roadmap:17` ghi AURA **ngoài phạm vi**, 0 task, 0 chủ trì. Và `proposal:232` cam kết **chuyển giao lược đồ gate + vết ghi cho tổ chức trung lập tại G1**, giữ lại SaaS fleet $1/thiết bị nơi Balena/Memfault/Mender/AWS IoT đã phục vụ U3 hôm nay. Kèm: **`FPT` xuất hiện 0 lần trong cả 4 tài liệu** (đã `grep`) | Ba đường thu chuỗi từ 4 bên về 1, chọn một trước khi chi ~8,6 tuần: **(i)** tự làm U3 (FPT sở hữu thiết bị, bán kết quả triển khai; gate/Action CI thành IP nội bộ hạ chi phí và trách nhiệm pháp lý của chính mình) · **(ii)** bán Action CI như sản phẩm bảo đảm trả tiền cho **chủ của U2**, tính theo đội không theo thiết bị (= Approach C) · **(iii)** Approach E |
| **`CEO-X6`** | **Tuần 0 tồn tại hay không.** Tôi đã đổi nhãn `Status:` sang `BLOCKED` (auto-decide #50) vì chính tài liệu ghi `VERDICT: NOT CLEARED`, nhưng nhãn không phải câu hỏi. A1 **không merge được** cho tới khi có waiver §11.3 chưa ai duyệt — và waiver như đang viết chỉ xử **nhãn trạng thái**, không xử **cổng merge** của DoD §11.2. A2 **không có lịch** tới khi F1 chốt. `TSK-S2-11` có hạn cứng `roadmap:235` mà kế hoạch phá âm thầm, với lý do hoãn hết hiệu lực ngay Tuần 1 | Bốn quyết định, không code: Q-11 · F1 · waiver (gồm cổng merge) · hạn `TSK-S2-11`. Giá: 1 tuần. Bảo vệ: ~8,6. Nếu bỏ qua: V1 viết 5 tuần rồi phát hiện đầu ra không merge được, hoặc merge nhờ một waiver viết sau khi việc đã xong — đúng thứ §11.3 tồn tại để ngăn |

### TASTE DECISION — 4

| ID | Vấn đề | Hai đường |
|:---|:---|:---|
| **`CEO-T1`** | **P3 có phải moat không**, khi 5 tuần chỉ đo nó ở miền quyết định trên `sim`↔`linux`? MCU hoãn 12 tuần, nửa âm thanh không kiểm. Hết ~8,6 tuần-người, đội **không biết gì mới về chính điểm khác biệt mình tuyên bố** | **(a)** Mua bo mạch Tuần 1, dành 1 tuần cho một phán quyết y hệt trên silicon thật, giữ P3 là moat · **(b)** Thôi gọi P3 là moat trong 5 tuần; moat là thứ tích luỹ được (thư viện gate từ sự cố thật + corpus phát lại từ triển khai mình sở hữu) |
| **`CEO-T2`** | **Đường chứng nhận an toàn chức năng: in hay out?** P2 đối chiếu với guardrail arXiv 2026 và policy engine, **không** với IEC 61508 / ISO 13849 — nơi *"cơ cấu chấp hành tự từ chối tại chỗ khi mất liên lạc"* là mẫu đã chứng nhận, đang bán, 50 năm tuổi | **(a)** IN: nói rõ mức nhắm tới và ai làm · **(b)** OUT: nói rõ nó loại những người mua nào, viết P3 hẹp lại thành *"chính sách như dữ liệu có phiên bản, thay cho interlock viết cứng"* |
| **`CEO-T3`** | **Bảng P2 liệt kê nhà nghiên cứu, không phải đối thủ** (và 2/5 nguồn chưa đọc toàn văn — kế hoạch tự ghi). Đối thủ thật: Espressif (đã có QEMU cho ESP32, có động cơ thương mại, `esp32s3` là target **duy nhất** của NeuroEdge) · nhà cung cấp mô hình (CR-1.0 biến NeuroEdge thành *client* của hợp đồng OpenAI) · *"để tôi tự viết trong hai tuần"* — nêu tên rồi **không bao giờ định lượng** · Cedar/Rego biên dịch về evaluator tất định, WASM chạy được trên MCU | **(a)** Thay bằng bảng đối thủ có cột *động cơ · kênh phân phối · thời gian để copy*, và định lượng đối thủ số 3 bằng thí nghiệm thật · **(b)** Giữ P2 như bối cảnh, ghi rõ nó không phải phân tích cạnh tranh, đừng dùng nó biện minh phạm vi |
| **`CEO-T4`** | **Thứ tự 5 tuần.** Kế hoạch: quyết định song song với code | **(a)** Tuần 0 (4 quyết định, không code) rồi 5 tuần code — xem `CEO-X6` · **(b)** Giữ song song nhưng cổng Tuần 3 thành binding và `gpio-sim` sang Ngày 1 (auto-decide #47 đã làm nửa sau) |

### Auto-decided — 50 mục, ba cái đổi lịch ngay

- **`gpio-sim` chuyển từ "phải thử trước Tuần 4" sang NGÀY 1.** Thí nghiệm 2 giờ, và §F5 đã chứng minh nó là **con đường duy nhất** cho `TSK-S3-05`. Biết ở giờ thứ 2 tốt hơn ở tuần thứ 4. Chi phí đảo thứ tự: 0.
- **Đặt 2 bo mạch Box-3 Tuần 1, gấp**, kèm giá + lead time (siết Open Question 4: dự án gọi tương đương MCU là moat mà chưa mua một bo mạch dev nào).
- **Mọi "Tuần N" thay bằng ngày tuyệt đối**: Tuần 1 = 2026-09-22→09-28 · cổng nhu cầu Tuần 3 = 2026-10-06→10-12 · Tuần 5 = 2026-10-20→10-26. Quy ước *"Tuần N ở đây = Tuần N+1 của roadmap"* là bãi mìn cho người tiếp quản.

Cộng: điều kiện **tái nhập** Khối 1b bằng số (*≥2 tổ chức có tên nói bằng văn bản rằng
tương đương MCU — không phải Linux — là thứ chặn quyết định mua*), vì hoãn mà không có
điều kiện quay lại và không có điều kiện chết thì không phải hoãn, là **để đó**.

### Điều CEO review nói mà eng review không nói

Eng review hỏi *"kế hoạch này có chạy được không"* và trả lời là được, trừ `gpio-sim`.
CEO review hỏi *"chạy xong thì biết thêm gì"*. Câu trả lời trung thực: **10 trong 12
tiêu chí ra nội bộ, trong đó 3 đã đóng từ Sprint 1 và 1 đã thoả sẵn** — không tiêu chí
nào một khách hàng nhận ra, chứ chưa nói tới trả tiền. Hai sự thật có thể giết dự án
(không ai trả tiền · tương đương gate trên $5 MCU không đạt trong ngân sách bộ nhớ) đều
bị hoãn ra ngoài cửa sổ 5 tuần. Đó là nội dung của `CEO-X3` và `CEO-T1`, và đó là lý do
chúng **không** được auto-decide.

## GSTACK DX REVIEW REPORT

Chạy qua `/autoplan` Phase 2.5 ngày 2026-09-22, mode **DX POLISH**.
Tiếng nói ngoài: **`[subagent-only]`** (Codex 401, đã probe ba lần trong phiên).
Persona suy từ kho: **U2 — trưởng nhóm kỹ thuật nhúng**, khớp §Target User của kế hoạch.

### DX DUAL VOICES — CONSENSUS TABLE

| Chiều | Claude | Codex | Consensus |
|:---|:---|:---|:---|
| 1. Getting started < 5 phút? | **NO** — không tới được | N/A | **FLAGGED** |
| 2. Tên lệnh/API đoán được? | Một phần | N/A | **FLAGGED** |
| 3. Thông báo lỗi hành động được? | **YES** — điểm mạnh nhất của kho | N/A | **FLAGGED** (thiếu trường docs link) |
| 4. Tài liệu tìm được và đủ? | **NO** | N/A | **FLAGGED** |
| 5. Đường nâng cấp an toàn? | Chưa đo được (chưa publish) | N/A | **FLAGGED** |
| 6. Môi trường dev ít ma sát? | **YES** — 13 giây từ clone tới đầu ra đầu tiên | N/A | **FLAGGED** |

**0/6 CONFIRMED · 6/6 FLAGGED.** Một tiếng nói không tạo được consensus.
Hai chiều (3 và 6) là **điểm mạnh thật**, không phải điểm yếu — bảng này không nói thế được.

### TTHW — đo thật, không đoán

**Thời gian máy: ~13 giây** từ clone sạch tới đầu ra hữu ích đầu tiên.
`venv` 1,3s · `pip install -e '.[dev]'` 8,8s · `pytest -q` 1,9s (**210 passed, 0 skipped** —
khớp `CLAUDE.md`) · `neuroedge verify` 0,7–1,0s. **Hạ tầng không phải chỗ tắc.**

**Thời gian người: không tới được.** Không có hello world nào, tài liệu hay không. Không
thứ gì trong kho — CLI hay Python API — **nhận một dữ kiện từ lập trình viên và trả về một
phán quyết gate**. `ActionContractEngine.evaluate(gate_name, context)` ở
`engine/__init__.py:77` **bỏ qua hoàn toàn** `context` và trả về đúng cái `Gate` mà bạn đã
tự tay nhồi vào `self.gates`. Kế hoạch thừa nhận thiếu `satisfied_by(fact, confidence)` ở
`:298–300` nhưng không rút ra kết luận DX: **TTHW không phải "dài", nó chưa được định nghĩa.**

`TTHW: không tới được → mục tiêu 2–5 phút (tier Competitive), đạt được ở A1 sau TSK-S2-03 + TSK-S3-07`

Thứ gần nhất với lần thắng đầu tiên là `neuroedge verify` ở 0,7 giây — nhanh, và nó chủ động
liệt kê cái nó *chưa* phủ. Nhưng nó chứng minh **artifact của nhà cung cấp** nhất quán, không
chứng minh **thứ của bạn** chạy. Đó là demo bộ test của người bán.

### Ba phát hiện CRITICAL

**`DX-C1` · `neuroedge verify` in "verification passed" và thoát 0 sau khi không kiểm gì.**
Trên bản cài sạch, trong thư mục rỗng: 0 gate, 0 vết ghi, 0 board, panel xanh, `EXIT=0`.
Vòng lặp `cli/main.py:424–447` đi qua thư mục rỗng, `problems` giữ 0. Cùng bản cài đó
`gate lint` thoát 1 và `board list` thoát 1 — **chỉ `verify` xanh**. `verify` không phân
biệt được *"cả 3 gate phân giải"* với *"không có gate nào"*.
Kho này có luật chống đúng chuyện đó, **ở hai tài liệu**: `CONTRIBUTING.md:75`
(*"Không được in bảng 'PASS' giả… đầu ra của CLI bị dán vào báo cáo tiến độ như bằng chứng"*)
và `CHANGELOG.md:612` bất biến #10 — dòng tôi tự viết phiên trước.
Ghép với `CEO-S1-4`: cơ chế làm asset biến mất (wheel không chứa asset) và cơ chế báo xanh
khi asset biến mất nằm cạnh nhau, và `ci-sim-linux.yml:106` chạy `verify` **chỉ** từ
checkout với `pip install -e`, nên **CI không bao giờ chạy đường wheel**.
→ **AUTO-DECIDE: ACCEPT, task riêng, KHÔNG gộp vào `TSK-S3-17`.** `verify` đếm số artifact
đã kiểm và ném lỗi ba thành phần nêu `NEUROEDGE_ROOT` khi đếm bằng 0. Thêm test phản chứng:
`verify` trên cây rỗng phải thoát khác 0. Lý do không gộp: `TSK-S3-17` sửa **đường dẫn**, và
sửa đường dẫn sẽ **che** `DX-C1` chứ không đóng nó.

**`DX-C2` · Hai test đo đúng hai critical path của moat, và cả hai tham số đều là đồ trang trí.**
`ReplaySession` lưu `network=` và `slow=` rồi **không bao giờ đọc lại**. Tôi chạy thử:

```
scenario('network_offline.json', network='offline') -> blocked=True  reason='gate_unreachable'
scenario('network_offline.json', network='online')  -> blocked=True  reason='gate_unreachable'
scenario('network_offline.json', network='banana')  -> blocked=True  reason='gate_unreachable'

replay('unverified_attempt.json', slow='claude-3-5-haiku')    -> blocked=True
replay('unverified_attempt.json', slow=None)                  -> blocked=True
replay('unverified_attempt.json', slow='nonexistent-model')   -> blocked=True
```

`test_gate_fail_closed_khi_mat_mang` xanh với `network='banana'`. Assertion đọc chuỗi
`reason` **đã ghi sẵn trong tệp JSON**, không đọc hành vi nào. Cùng chuyện với `slow=`.
Hệ quả đúng chỗ đau nhất: **critical path #2** (*"mất mạng thì chặn, và chặn có lý do đọc
được"* — phép đo trực tiếp của P3) và **critical path #4** (*"đổi model, phán quyết không
đổi"* — wedge thật) **đều đang được đo bằng test rỗng**. Và nó ghép với `CEO-X1`: bằng
chứng duy nhất kế hoạch có cho việc chặn khi offline là một test đọc chuỗi ra khỏi JSON.
→ **AUTO-DECIDE: ACCEPT.** `TSK-S3-02`/`TSK-S3-03`: `network=` và `slow=` phải **chịu lực
hoặc bị xoá**. Kèm test phản chứng khẳng định phán quyết **ĐỔI** khi mỗi tham số đổi.

**`DX-C3` · Trang đích PyPI sẽ là hướng dẫn cài từ nguồn, cho một gói không chạy được.**
`python/pyproject.toml` khai `readme = "README.md"` → `python/README.md` thành trang PyPI,
và nó **mở đầu bằng** `pip install -e '.[dev]'` — lệnh cài editable từ source, hiện ra cho
người vừa `pip install neuroedge`. Không có một ví dụ dùng CLI nào. Ba liên kết `../` sẽ
chết trên PyPI. Cộng `CEO-S1-4`: bản cài đó không chứa asset nào.
→ **AUTO-DECIDE: ACCEPT**, vào `TSK-S3-14`: `README.md` gốc kho (xem `DX-H1`) thành trang
PyPI qua `force-include`; bỏ hướng dẫn editable khỏi trang đích; liên kết tuyệt đối.

### Sáu phát hiện HIGH

| ID | Phát hiện | Quyết |
|:---|:---|:---|
| **`DX-H1`** | **Không có `README.md` ở gốc kho.** Người mới đổ bộ vào ~4.000 dòng tài liệu chiến lược không có cửa vào. Hướng dẫn bắt đầu thật nằm ở `CHANGELOG.md` dòng 404/707. Hướng dẫn cài bị nhân ba và đang trôi khỏi nhau | **ACCEPT** — một `README.md` gốc **một màn hình**; chuyển `CHANGELOG` §2 sang `docs/`; dùng nó làm trang PyPI. Đây là điều kiện của Tiêu chí ra Sprint 3 #1 mà kế hoạch chưa từng nêu |
| **`DX-H2`** | **Mã thoát 2 nghĩa vừa "chưa hiện thực" vừa "bạn gõ sai lệnh".** `_not_yet()` thoát 2, và mọi lỗi cú pháp Typer cũng thoát 2. `CHANGELOG.md:354` **đã nhận ra** sự nhập nhằng rồi lấp nó lại (*"mọi mã thoát khác 0 là bằng chứng bị từ chối — kể cả mã 2"*) | **ACCEPT** — "chưa hiện thực" sang **mã 3**; một test cho mỗi mã. **Làm trước khi CI neo vào mã 2**, vì sau đó là breaking change của hợp đồng |
| **`DX-H3`** | **`replay()`/`scenario()` thử lại basename trong `fixtures/traces/`**, nên một đường dẫn gõ sai **âm thầm nạp fixture `esp32s3` của NeuroEdge** thay vì báo lỗi. Nặng hơn `CEO-S5-1` | **ACCEPT** — xoá hẳn fallback; cả hai đi qua `trace.load_trace()`; test phản chứng: đường dẫn sai phải ném |
| **`DX-H4`** | **`evaluate.type` chỉ có `["bool","level","choice"]` — không có kiểu số.** Không gate nào diễn đạt được `pressure < 8 bar`, `temperature > 60°C`, `speed <= 2 m/s`. Với một nền tảng gate an toàn cho **cơ cấu chấp hành vật lý**, đó là lỗ lớn; và lược đồ **đã đóng băng** nên cần RFC. Bốn vòng review không ai nêu | **ACCEPT, và đây là câu hỏi tuần 1** — chốt `type: numeric` vào `gate.v1` hay để `v2`, **trước khi** một đối tác đầu tiên đẩy nó lên đường găng. Thêm vào §Open Questions |
| **`DX-H5`** | **`NeuroEdgeError` không có trường liên kết tài liệu.** Phần `how` dẫn *"Phụ lục B.5 nguyên tắc 2"* trong một tệp 184 kB không có neo — và wheel **không chứa** tệp đó | **ACCEPT** — thêm `docs: str` mang URL ổn định; `render()` in thêm dòng `docs:`; nới test corpus từ ba thành **bốn** thành phần |
| **`DX-H6`** | Tên pin/action/gate không tồn tại trả mặc định "an toàn" nên gõ sai làm test xanh | **TỪ CHỐI (P4, trùng)** — đúng là `CEO-S5-2`. Nhưng ghi lại: **hai tiếng nói độc lập tìm ra cùng một lỗi**, và tiếng nói DX nói phân tích của kế hoạch *"correct and complete, no notes"*. Đó là tín hiệu mạnh nhất của Phase 2.5 |

### Chín phát hiện MEDIUM

| ID | Phát hiện | Quyết |
|:---|:---|:---|
| **`DX-M1`** | Bốn bộ render lỗi khác nhau; `gate lint` — **cổng an toàn được chỉ định** — bỏ mất dòng `rule:` mà `gate resolve` có in | **ACCEPT** — tách `_render(error)` không-thoát ra khỏi `_fail()`, gọi từ `lint`, `trace validate`, `verify` |
| **`DX-M2`** | `NE2001` khuyên chạy `neuroedge gate add <uri>` **để tải gate về**, nhưng `gate add` không tải được gì tới Khối 3 | **ACCEPT** — sửa câu ở `gate_resolver.py:174`, bỏ gợi ý tải từ xa cho tới khi registry tồn tại |
| **`DX-M3`** | `gate.v1.json` **đã đóng băng** ghi `name` *"phải khớp khoá gate khai trong `agent.toml`"* — **không có `agent.toml` nào** và không gì đọc nó | **ACCEPT** — sửa câu **bên trong RFC của `TSK-S3-15`**, không mở RFC lược đồ thứ hai |
| **`DX-M4`** | `blocked_by` là chuỗi truthy `"unknown_gate"` trên phán quyết **ALLOW**, nên `assert not s.blocked_by` fail ở happy path. Đã kiểm: `verdict=ALLOW, blocked_by='unknown_gate'` | **ACCEPT** — `None` trừ khi phán quyết là BLOCK (`testing/__init__.py:70`) |
| **`DX-M5`** | `NEUROEDGE_ROOT` là escape hatch duy nhất của cả sản phẩm, và là cách chữa một dòng cho `DX-C3`/`CEO-S1-4` — **không được ghi ở đâu** trong hướng dẫn vận hành | **ACCEPT** — ghi vào `CHANGELOG` §2.2 và **nêu tên nó trong thông báo lỗi của `repo_root()`** |
| **`DX-M6`** | `--help` xếp **năm lệnh cụt lên trên** ba nhóm chạy được; `new` đứng thứ ba và thoát 2 | **ACCEPT** — xếp lệnh chạy được lên đầu; tách hoặc ẩn lệnh pending tới khi engine về |
| **`DX-M7`** | `--json` chỉ có ở `gate resolve`; `lint`, `verify`, `trace validate`, `board list` chỉ in bảng Rich | **ACCEPT, nâng ưu tiên** — nó là deliverable của `TSK-S3-06`, và `DX-H2` (mã thoát nhập nhằng) làm nó cần hơn: máy cần đọc được kết quả khi mã thoát không nói đủ |
| **`DX-M8`** | **`run` tự khai phụ thuộc một task, thật ra bốn.** `PENDING["run"] = ("TSK-S2-01", …)` và `--help` in *"pending TSK-S2-01"*, nhưng `run` cần S2-01 + S2-03 + S2-05 + S2-08 | **ACCEPT** — `PENDING` mang danh sách task, không một task. Người đọc đang tưởng còn một bước |
| **`DX-M9`** | **Gate là YAML có JSON Schema đóng băng, và không ai nối hai thứ đó.** Không tệp gate nào mang dòng `# yaml-language-server: $schema=`, nên editor không cho autocomplete hay validate nội dòng | **ACCEPT — giá gần bằng 0, giá trị cao.** Một dòng modeline cho autocomplete + validate trong VS Code, **không viết một dòng code**. Phát từ scaffold `TSK-S3-07` **và** thêm vào ba tệp `gates/*.yaml` đã có. Đây là cách duy nhất trong kế hoạch dạy cú pháp gate mà không buộc đọc Phụ lục B.2 — `gate explain` giúp **đọc** gate, không giúp **viết** |

### DX Scorecard — 8 chiều

| Chiều | Điểm | 10 điểm cho sản phẩm NÀY nghĩa là gì |
|:---|:---:|:---|
| Getting Started | **2**/10 | `pip install neuroedge && neuroedge new my-door && cd my-door && neuroedge test` → xanh, dưới 2 phút, không đọc gì |
| API/CLI Ergonomics | **5**/10 | 7 lệnh cấp trên đều làm việc; mã thoát một nghĩa mỗi mã; `--json` ở mọi lệnh |
| Error Handling | **7**/10 | Ba thành phần **đã có và cưỡng chế bằng cấu trúc** — điểm mạnh nhất của kho. 10 cần trường `docs:` và một bộ render duy nhất |
| Documentation | **4**/10 | README gốc một màn hình; một trang quickstart copy-paste chạy được; Phụ lục B.2 có neo |
| Escape Hatches | **4**/10 | Mọi mặc định có đường ghi đè, và **được ghi ra**. Hôm nay có đúng một (`NEUROEDGE_ROOT`) và nó không được ghi ở đâu |
| Upgrade Path | **5**/10 | Chưa publish nên chưa đo được. `proposal:231` đã cam kết SemVer; `digests.lock` (`CEO-S1-7`) là thứ làm cam kết đó có thật |
| Dev Environment | **7**/10 | 13 giây clone→đầu ra, 210 test 0 skip, CI 4 job. Đây là chiều kho này **đã** làm tốt |
| **Overall** | **4**/10 | |

Hai chiều 7/10 không phải chỗ cần sửa — chúng là **tài sản kế hoạch không ghi nhận**.
Thông báo lệnh chưa làm nêu **task ID + sprint + trỏ roadmap**; `--help` gắn nhãn
`(pending TSK-…)` tại chỗ; `verify` chủ động liệt kê cái nó chưa phủ kèm task mở nó. Đó là
DX trên mức trung bình của ngành, và không mục nào trong 15 task nói phải **giữ** nó.

### DX Implementation Checklist

| # | Việc | Task | Mức |
|:---:|:---|:---|:---:|
| 1 | `verify` đếm artifact, ném khi đếm = 0 + test cây rỗng | **`TSK-S3-19`** (mới) | CRITICAL |
| 2 | `network=`/`slow=` chịu lực hoặc xoá + test phản chứng phán quyết ĐỔI | `TSK-S3-02`, `TSK-S3-03` | CRITICAL |
| 3 | `README.md` gốc một màn hình, thành trang PyPI | `TSK-S3-14` + **`TSK-S3-20`** (mới) | CRITICAL |
| 4 | "Chưa hiện thực" sang mã thoát **3**, trước khi CI neo vào 2 | `TSK-S3-06` | HIGH |
| 5 | Xoá fallback basename trong `replay()`/`scenario()` | `TSK-S3-02` | HIGH |
| 6 | Chốt `type: numeric` vào `gate.v1` hay `v2` | §Open Questions #10 | HIGH |
| 7 | Trường `docs:` trong `NeuroEdgeError`, test corpus lên 4 thành phần | `TSK-S2-05` | HIGH |
| 8 | Một bộ render lỗi duy nhất (`_render` không-thoát) | `TSK-S3-06` | MEDIUM |
| 9 | Modeline `yaml-language-server` trong scaffold + 3 gate đã có | `TSK-S3-07` | MEDIUM |
| 10 | `PENDING` mang danh sách task; `--help` xếp lệnh chạy được lên đầu | `TSK-S3-06` | MEDIUM |
| 11 | `blocked_by = None` trên ALLOW | `TSK-S3-02` | MEDIUM |
| 12 | Ghi `NEUROEDGE_ROOT` và nêu tên nó trong lỗi `repo_root()` | `TSK-S3-17` | MEDIUM |
| 13 | Sửa câu `NE2001` (`gate add` chưa tải được) và `gate.v1` `agent.toml` | `TSK-S3-15` RFC | MEDIUM |

### Developer empathy narrative

> Tôi là trưởng nhóm nhúng. Ai đó gửi tôi link kho lúc 4 giờ chiều thứ Năm. Tôi mở ra và
> thấy mười một mục ở gốc, bốn trong đó là tài liệu chiến lược nghìn dòng, và **không có
> README**. Tôi đoán `python/`, thấy README, cài trong chín giây — nhanh thật. Rồi tôi gõ
> `neuroedge run` vì đó là thứ tôi muốn làm, và được một panel vàng nói nó chưa tồn tại,
> lịch ở Sprint 2. Tôi gõ `neuroedge new` vì đó là cách mọi công cụ khác bắt đầu — panel
> vàng, Sprint 3. `test` — vàng, Sprint 3. `build` — vàng. `record` — vàng. Năm lần.
> Tôi chạy `neuroedge verify` và nó xanh trong một giây, liệt kê ba gate của họ. Tôi hiểu
> rằng nó vừa kiểm **tài liệu của họ**, không phải ý tưởng của tôi.
> Tôi đóng tab ở phút thứ hai. Không vì sản phẩm dở — thông báo lỗi của nó tốt hơn phần
> lớn thứ tôi dùng — mà vì **tôi không tìm ra cách hỏi nó một câu hỏi về cửa của tôi.**

### Developer journey map — 9 chặng

| Chặng | Hôm nay | Sau kế hoạch (nếu nhận checklist trên) |
|:---|:---|:---|
| Discover | Không README gốc; 4 tài liệu chiến lược | README một màn hình, trang PyPI |
| Evaluate | `verify` xanh trong 1s nhưng chỉ kiểm artifact của người bán; và **xanh cả khi rỗng** | `verify` đếm và ném khi rỗng |
| Install | 13 giây, mượt — **nhưng wheel không chứa asset** | `force-include`, smoke test sau cài |
| Hello world | **Không tồn tại** | `neuroedge new` → `neuroedge test` xanh, < 2 phút |
| Integrate | `@action` chưa có; `evaluate()` bỏ qua `context` | `TSK-S2-03` + `TSK-S2-05` |
| Debug | Lỗi ba thành phần tốt, thiếu link tài liệu; 4 bộ render | Trường `docs:`, một bộ render |
| Upgrade | Chưa publish | SemVer + `digests.lock` |
| Scale | Gate không diễn đạt được ngưỡng số (`DX-H4`) | Quyết `type: numeric` |
| Migrate | Không có gì để di trú | — |

## GSTACK ENG REVIEW REPORT

Chạy qua `/autoplan` Phase 3 ngày 2026-09-22 — phase cuối và là **cổng bắt buộc**, nên nó
review **bản kế hoạch đã tu chỉnh** sau CEO review và Phase 2.5. Đây là vòng eng review thứ
hai trên tài liệu này; vòng `/plan-eng-review` độc lập (8 issue, 1 critical gap) ghi ở
§GSTACK REVIEW REPORT phía trên và **không** bị thay thế bởi báo cáo này.

**TIẾNG NÓI NGOÀI:** `[subagent-only]`, lần thứ tư. `codex login status` báo *"Logged in
using ChatGPT"*, nhưng round-trip thật vẫn **401**: `could not be refreshed` +
`401 Unauthorized` tại `wss://chatgpt.com/backend-api/codex/responses` (log:
`/tmp/eng-codex.log`). Cần `codex login` lại. Tiếng nói Claude (`eng-voice`, ngữ cảnh sạch,
không thấy review trước) tìm 4 phát hiện chịu lực — `A1`, `A2`, `A2b`, `A3` — và một danh
sách "Part B" **chưa kịp gửi** khi phiên đứt; tôi đã **dựng lại chứng minh chạy được cho
cả bốn** trong phiên này rồi tự chạy nốt Section 1–4. Không có mô hình thứ hai để lọc chéo,
nên mọi CRITICAL dưới đây đi thẳng tới Final Gate.

### ENG DUAL VOICES — CONSENSUS TABLE

| Chiều | Claude | Codex | Consensus |
|:---|:---|:---|:---|
| 1. Kiến trúc vững? | **NO** — 3 CRITICAL (`ENG-A1`, `ENG-A2`, `ENG-A2b`) | N/A | **FLAGGED** |
| 2. Test phủ đủ? | **NO** — 3 test moat rỗng + 2 bề mặt mới không có phản chứng | N/A | **FLAGGED** |
| 3. Rủi ro hiệu năng đã xử? | **YES** — trừ 1 điểm cache nhỏ | N/A | **FLAGGED** |
| 4. Mối đe doạ an ninh đã phủ? | **NO** — hàng rào kế thừa phủ 1/4 bề mặt | N/A | **FLAGGED** |
| 5. Đường lỗi đã xử? | **Một phần** — RE mới cho vòng này; reason chưa có thứ tự chuẩn | N/A | **FLAGGED** |
| 6. Rủi ro triển khai quản được? | **NO** — `gpio-sim` chưa chứng minh, `extends` chưa ghim | N/A | **FLAGGED** |

**0/6 CONFIRMED · 6/6 FLAGGED.** Cùng cách đọc như hai bảng trước: không có mô hình thứ
hai, nên đây là **một** tiếng nói đã được kiểm chứng độc lập bằng chạy thật, không phải
đồng thuận.

### Step 0 — Scope Challenge

Mode **FULL_REVIEW, không giảm phạm vi** (override P2 của /autoplan: *scope challenge never
reduce*). Đã đọc mã thật thay vì tin mô tả của kế hoạch. Bảng ánh xạ bài toán con → mã sẵn có:

| Bài toán con | Mã hiện có | Dòng | Test | Trạng thái |
|:---|:---|:---:|:---:|:---|
| Phân giải + kế thừa gate | `engine/gate_resolver.py` + `engine/constraints.py` | 770 | **55** | Vững — điểm mạnh nhất |
| Canonical hoá + digest | `engine/canonical.py` | 61 | 10 | Vững |
| Vết ghi: đọc + thẩm định | `trace.py` | 96 | 24 | Vững |
| HAL: hợp đồng + board | `hal/__init__.py` + `hal/board.py` | 367 | 18 | Nửa (thiếu backend) |
| CLI | `cli/main.py` | 541 | 26 | Nửa (5 lệnh cụt) |
| **Action CI** | `testing/__init__.py` | 106 | **4 (3 rỗng)** | **Yếu nhất** — đúng chỗ bán |
| Lượng giá lúc chạy | — | 0 | 0 | Chưa có (`evaluate()` bỏ qua `context`) |
| Cây quyết định + trình duyệt C | — | 0 | 0 | Chưa có (Q-9 A) |
| `record`/`replay` thực thi | — | 0 | 0 | Chưa có |
| HAL `sim`/`linux` | — | 0 | 0 | Chưa có |

**Kiểm tra độ phức tạp:** kế hoạch nói thật ở `:302–308` rằng `TSK-S2-03` phải làm ba thứ
chưa tồn tại; đọc mã xác nhận đúng cả ba, và **thêm một thứ thứ tư** mà bốn vòng review
trước không nêu: `to_artifact()` không mang `constraints` (`ENG-A1b`). Ba phát hiện của
Step 0:

- **`ENG-A0-1` · HIGH · Đường găng thật.** 18/21 task chạy nằm ở V1; V2 **0 task** trong
  cửa sổ (kế hoạch tự ghi ở §Dependencies); V3 bị V1 kéo. Bảy task ID rời V1 được với chi
  phí 0 — xem `ENG-A3` cuối báo cáo. Ước lượng ~8,6 tuần-người phần lớn là **bài toán phân
  bổ**, không phải khối lượng.
- **`ENG-A0-2` · MEDIUM · Kế toán lại đếm sai ở một tầng khác.** Bảng chuyển task của
  `eng-voice` ghi tiêu đề *"Six tasks"* nhưng liệt kê **sáu dòng, bảy task ID**
  (`TSK-S3-19` + `TSK-S3-20` chung một dòng). Đây đúng lớp lỗi `CEO-S0-1`: đếm theo dòng
  thay vì theo task. Số đúng dùng trong báo cáo này: **7 task**.
- **`ENG-A0-3` · CRITICAL (gộp vào `ENG-A1`) · Tuyên bố kiến trúc số một hẹp hơn câu chữ.**
  Không có "một ngữ nghĩa, ba người tiêu thụ" theo cách kế hoạch viết.

### Section 1 — Architecture

```
                  schemas/gate.v1.json (ĐÓNG BĂNG, sửa = RFC)
                          │ validate
   YAML gate ─────────────┤
                          ▼
               chain merge (≤3) ──► ResolvedGate ──► to_artifact() ──RFC8785──► digest ──► ký
                gate_resolver.py        │
                                        ├─ parse_allow_when ─► Constraint.admitted/floor
                                        │        └─ is_at_least_as_strict_as()   [lúc BUILD — GIỮ NGUYÊN]
                                        │
                                        └─ TSK-S2-12 (host, import parse_constraint — không sửa, không RFC)
                                                 │  phát decision_tree.v1.json
                                                 │  { criteria_order:[…], gate_digest:sha256:…, nodes:[admitted,floor] }
                                                 │
                                    ┌────────────┴────────────┐
                                    ▼                         ▼
                          Python evaluate()          C tree-walker (~40 dòng, MCU)
                          (runtime host)             (Block 1b — ngoài 5 tuần)
                                    │
   @action ─► token(digest,nonce,pid) ─► HAL.digital_out(signature)   [hal/__init__.py:87 chỉ kiểm chuỗi rỗng]

   record ─► trace.v1.json ─► replay()/scenario() ─► ReplaySession(4 test) ─► PinAssertion
```

**`ENG-A1` · CRITICAL · `CEO-S1-1` sai ở cả ba chân.** *(Tôi đã dựng lại từng chân, output
thật ở phiên này.)*

**(a) Bao hàm trên cây *yếu hơn* phép kiểm đang có.** Phản ví dụ chạy được:

```
base : risk_level {lte: low}        request_channel {in: [in_person, app]}
child: risk_level {lte: medium}     request_channel {not_in: [cả 4 lựa chọn]}

per-criterion: risk_level stricter=False  → TỪ CHỐI
containment  : 0 ⊆ 2 tuple              = True → NHẬN
```

Con **nới** `risk_level` nhưng làm `request_channel` bất khả thoả, nên tổng thể nó "chặt
hơn" theo nghĩa tập ALLOW — và bao hàm không thấy được mệnh đề bị nới. Đã kiểm lại cho
chính xác, và điểm này quan trọng: **bao hàm ở dạng chỉ so tập giá trị còn yếu hơn nữa** —
nó **nhận luôn `loosens_confidence`** (`confidence_gte: 0.9 → 0.5`, tập giá trị không đổi);
chỉ khi bao hàm tính **cả sàn độ tin cậy** thì bốn fixture `loosens_*` mới bị từ chối, còn
phản ví dụ ghép ở trên **vẫn lọt** trong cả hai cách viết. Cái **mất** là bảo đảm *từng
mệnh đề con ≤ mệnh đề cha*, và nó mất thật. Thay phép kiểm bằng bao hàm = **nới lỏng
nguyên tắc 2** và làm hai tiêu chí ra Sprint 2 #4 / Sprint 3 #5 mất cơ chế.

→ **AUTO-DECIDE: GIỮ `is_at_least_as_strict_as`** làm phép kiểm lúc build; `CEO-S1-1` sống
nhưng **thu hẹp**: *"một ngữ nghĩa, **hai** người tiêu thụ"* (runtime Python + trình duyệt
C), **không** hợp nhất phép kiểm siết chặt.

**(b) `to_artifact()` không mang thứ cần để biên dịch cây.** Đã kiểm:

```
keys = [allow_when, budget, evaluate, name, on_block, resolved_from, schema, version]
'constraints' in artifact = False
allow_when = dạng thô tác giả viết: {"risk_level": {"lte": "low"}, ...}
```

Issue 11 bảo suy cây từ `to_artifact()` để khỏi chạm `constraints.py` (RFC-gated). Nhưng
làm thế buộc hiện thực lại `parse_constraint` — **hiện thực thứ ba quay lại, chỉ đổi chỗ**.
→ **SỬA:** trình biên dịch chạy **trên host** và **`import` `parse_constraint`** — import
không phải sửa, nên **không cần RFC**; nó phát `decision_tree.v1.json` với `admitted` đã
khai triển; trình duyệt trên thiết bị **không chuẩn hoá gì**. Một bộ chuẩn hoá, một bộ phát,
hai bộ đi.

**(c) Thứ tự lượng giá chưa được định nghĩa, mà `reason` phụ thuộc nó.** Trên
`gates/unlock_door_night@1.0.0` thật:

```
python insertion : [guest_authenticated, risk_level, room_matches, staff_co_authorized, request_channel]
canonical đã ký  : [guest_authenticated, request_channel, risk_level, room_matches, staff_co_authorized]
SAME: False
```

Khi **hai** tiêu chí cùng fail: Python quy cho `risk_level`, trình duyệt đi theo thứ tự đã
ký quy cho `request_channel`. **Phán quyết giống nhau** (hội giao hoán), **`reason` khác
nhau** — và `reason` là thứ vào vết ghi, thứ Tiêu chí #4 so khớp, thứ `DX-C2` vừa buộc phải
chịu lực. → **SỬA:** mảng `criteria_order` **tường minh** trong cây đã ký (RFC 8785 giữ thứ
tự mảng), xếp **root-first** — không dùng thứ tự từ điển, vì đổi tên một tiêu chí sẽ làm
`reason` nhiễu.

**Ba cảnh báo kèm theo của `eng-voice`, đã nhận:**
1. **Thiết bị thẩm định một tài liệu nó không lượng giá:** chữ ký phủ `to_artifact()`,
   thiết bị đi `decision_tree.v1.json`. → cây **phải mang `gate_digest`** và CI phải
   **biên dịch lại ⇒ byte y hệt**.
2. **Là *hai* bộ đi, không một:** `satisfied_by(fact, confidence)` chưa tồn tại ở đâu và
   phải tồn tại hai lần. An toàn được vì nó nhỏ: **bảng sự thật đầy đủ** (5 tiêu chí × 3–4
   giá trị, vài trăm dòng) khẳng định Python và C trùng cả `verdict` **lẫn** `reason`.
3. **RFC trên `constraints.py` trở nên chịu lực hơn:** từ chỗ định nghĩa một phép kiểm host
   thành chỗ định nghĩa thứ chạy xuống silicon. Ghi vào RFC-0003.

**`ENG-A2` · CRITICAL · Hàng rào kế thừa phủ 1 trong 4 bề mặt nới lỏng.** Đã dựng lại:

```
cha : base-access@1.0.0  budget={200ms, closed}  on_block=escalate → human_receptionist
cha : unlock_door@1.2.0  budget={120ms, closed}  on_block=escalate → human_receptionist
con : lax-night@1.0.0    → RESOLVED OK
      budget   = {'p95_latency_ms': 900000, 'fail': 'open'}
      on_block = {'action': 'degrade', 'fallback_action': 'unlock_door_no_auth'}
      allow_when kế thừa nguyên vẹn: ['guest_authenticated','risk_level','room_matches']
```

Ngữ nghĩa cộng lại: *"chờ thẩm định tới 15 phút; hết hạn thì ALLOW; nếu bị chặn thì chạy
`unlock_door_no_auth` thay thế"* — và nó **qua đúng phép kiểm mà kế hoạch nói đã đóng**.
Gốc là comment ở `gate_resolver.py:453–456`: *"on_block không chịu quản trị B.5"* — đúng với
`deny`/`escalate`/`ask`, **sai với `degrade`** vì `fallback_action` **được thực thi**.
`_resolve_budget` không có phép kiểm đơn điệu nào, và nguyên tắc 4 chỉ chặn `fail: open`
lan xuống, không chặn con **tự khai** `open` trong chuỗi đã `closed`.

→ **ACCEPT (P1):** task mới **`TSK-S2-13`** (V1, cần **RFC-0004**): `p95` chỉ giảm · con
trong chuỗi `closed` không được khai `open` · `on_block` theo dàn `deny > escalate/ask >
degrade`, và **`to:` cũng vào dàn** (`human` chặt nhất — `escalate → escalate` đổi `to:
human_receptionist` thành `to: some_agent` là nới thật, B.3 cho phép cả hai) · **`fallback_action`
cũng vào dàn** (nó **được thực thi**, nên con không được đổi sang hành động rộng hơn cha; phải
là hành động đã khai trong `evaluate`/registry của chuỗi) · **bốn fixture phản chứng** hai chiều
(`budget` · `on_block.action` · `on_block.to` · `fallback_action`) · `ask.message` **tuyên bố
ngoài phạm vi** thay vì để mập mờ.

**`ENG-A2b` · CRITICAL · Bề mặt thứ tư: `extends` không được ghim.** Đã dựng lại:

```
TRƯỚC: strict-base@1.0.0 allow_when risk_level {lte: low}
       child sha 5d8db4a16db6 · admits ['low'] · digest sha256:533377b525506765a…
>>> tái publish base ở CÙNG version, nới {lte: high}
SAU:   child sha 5d8db4a16db6 (y hệt) · admits ['high','low','medium'] · digest …ae15e177…
       KHÔNG lỗi, KHÔNG cảnh báo, KHÔNG chẩn đoán
```

*(Hai gate dựng trong thư mục tạm của phiên, không nằm trong kho; sha của con phụ thuộc đúng
byte của tệp con đó — cơ chế mới là thứ được khẳng định, không phải giá trị sha.)*

Phép kiểm siết chặt lượng giá **con-với-cha tại thời điểm phân giải**, không phải với cha mà
tác giả đã review. Digest đổi — nên `digests.lock` bắt được **trong kho này** — nhưng không
gì so digest lúc phân giải, và gate kéo từ registry **không có lock nào**. `pattern` của
`extends` trong `gate.v1.json` không có ô digest. Đây là bề mặt quan trọng nhất cho mô hình
kinh doanh *"kéo chính sách an toàn từ registry"* (`P-5`, `FR-REG-*`, Fleet OS).

→ **ACCEPT (P1):** task mới **`TSK-S3-21`** (V1): ghim danh tính base bằng
`@<ver>#sha256:…` trong `extends` (đổi `pattern` của **`gate.v1.json`** → **gộp vào
RFC-0003**) **cộng** `digests.lock` mở rộng thành lock của `extends` (`TSK-S3-16` đã có, V3)
**cộng** một phép kiểm danh tính `URI ↔ name/version khai trong tệp` (đã kiểm: một tệp phục vụ
dưới `…/trusted@1.0.0` khai `name: something-else, version: 9.9.9` vẫn phân giải sạch; ghim
digest không bắt được lệch danh tính) · bất biến phiên bản trên registry là việc **Khối 3** → TODOS.

**Bốn bề mặt nới lỏng, một cái được bảo vệ — sau Phase 3 còn 0 cái không được bảo vệ:**

| # | Bề mặt | Trước Phase 3 | Sau |
|:---:|:---|:---|:---|
| 1 | `allow_when` | Được bảo vệ (4 fixture) | Giữ nguyên |
| 2 | `budget` (`p95`, `fail`) | **Không** | `TSK-S2-13` |
| 3 | `on_block` (`action`, `to`, `fallback_action`) | **Không** | `TSK-S2-13` |
| 4 | Danh tính `extends` (digest **và** `URI ↔ name/version`) | **Không ghim** | `TSK-S3-21` |

### Section 2 — Code Quality

- **`ENG-Q1` · HIGH · `_parse_events()` ghim cứng `unlock_door`** (`testing/__init__.py:65–67`):
  với **mọi** vết ghi nó bịa ra một action và một gate tên `unlock_door`, nên
  `s.action("mã_đúng")`/`s.gate("mã_đúng")` trả rỗng-có-mặc-định và test xanh. Đã biết là nợ
  (kế hoạch `:168–169`), nay có bằng chứng chạy được. → `TSK-S3-02`/`TSK-S3-03`, kèm test
  phản chứng tên action khác.
- **`ENG-Q2` · MEDIUM · Fallback basename bị nhân đôi** trong `replay()` và `scenario()`
  (`testing/__init__.py:87–92` và `:99–103`) — hai bản sao của cùng một lỗi `DX-H3`. Sửa
  **một lần** ở một loader dùng chung `trace.load_trace()` (P4), và bản sửa phải giữ
  `validate=True` (hiện `json.load` thô, không qua schema).
- **`ENG-Q3` · MEDIUM · `deepdiff>=7` là phụ thuộc runtime của lõi MIT nhưng không được
  dùng ở đâu** (`pyproject.toml:36`; `rg` khắp `python/neuroedge` + `tests`: 0 hit). Nó là
  comparator dự định cho golden reference `TSK-S3-04` — hoặc dùng ở đó, hoặc gỡ trước khi
  publish; để nguyên là tăng bề mặt cài đặt + kiểm giấy phép cho một thứ chưa chạy.
  → Ghi vào DoD của `TSK-S3-04`.
- **`ENG-Q4` · LOW · `_gate_schema()` đọc + parse lại `schemas/gate.v1.json` mỗi lần
  `validate_gate_document()` được gọi** (`gate_resolver.py:133–135`) — lint N gate × chiều
  sâu chuỗi lần parse thừa. Sửa một dòng (`lru_cache`), gộp vào `TSK-S2-13`.
- **`ENG-Q5` · INFO · `paths.repo_root()` trả đường dẫn không tồn tại thay vì ném** — đã nhận
  ở `CEO-S1-4`, thuộc `TSK-S3-17`; không phát hiện mới.

### Section 3 — Test Review

Sơ đồ test đầy đủ nằm ở artifact (đường dẫn dưới). Bảng phủ, chỉ các đường **mới** của kế
hoạch:

| Đường mới | Loại test | Đã có? | Quyết |
|:---|:---|:---:|:---|
| `evaluate()` đi cây, phán quyết + `reason` | Unit + golden | Không | `TSK-S2-12` |
| **Python ↔ C trùng `verdict` *và* `reason`** | Bảng sự thật đầy đủ | Không | **`ENG-T1` → `TSK-S2-12`** |
| **Biên dịch lại ⇒ byte y hệt + `gate_digest` trong cây** | CI gate | Không | **`ENG-T2` → `TSK-S2-12` + `TSK-S3-16`** |
| **Phản chứng `budget`/`on_block`/`extends` tái publish** | Corpus hai chiều | Không | **`ENG-T3` → `TSK-S2-13` + `TSK-S3-21`** |
| Token một lần/TTL/restart · budget vượt · offline | Unit + Integration | Không | Đã có trong test plan nhóm B/C |
| `record`/`replay` thực thi · golden compare | Integration | Không | `TSK-S3-01..04` |
| Wheel cài sạch rồi chạy | CI + smoke | Không | `C11` (test plan) |

- **`ENG-T1` · HIGH · Không có test nào sẽ bắt hai bộ đi lệch nhau.** Với cây quyết định,
  hai hiện thực (`evaluate()` Python và walker C) phải trùng trên **cả `reason`**, và vì
  miền giá trị nhỏ, cách duy nhất đúng là **duyệt toàn bộ** chứ không lấy mẫu. Đây cũng là
  thứ khiến tuyên bố "một ngữ nghĩa, hai người tiêu thụ" kiểm chứng được thay vì là khẩu hiệu.
- **`ENG-T2` · HIGH · Chữ ký phủ artifact, thiết bị chạy cây.** Không có `gate_digest` trong
  cây + kiểm byte-reproducible thì một cây cũ/bị sửa là **không phát hiện được** trên thiết
  bị. Cùng chỗ với `CEO-S4-2` (digest trong vết ghi).
- **`ENG-T3` · HIGH · Corpus phản chứng phải phủ hai bề mặt mới, và khép kín hai chiều.**
  `fixtures/gates/expected_errors.yaml` là hợp đồng hai chiều (CLAUDE.md); thêm fixture cho
  `budget`/`on_block`/`extends` mà không thêm mục tương ứng là vỡ luật corpus.
- Ba test moat rỗng `A1–A3` (từ CEO + Phase 2.5) **vẫn là việc phải làm trước mọi test mới**
  — mọi test viết cạnh chúng sẽ thừa hưởng cùng giả định. Không đổi.

**Test plan artifact:** `~/.gstack/projects/letrongminh-neuroedge-init/minhlt-docs-autoplan-ceo-dx-review-test-plan-20260922-094800.md`
(164 dòng; thay thế bản `…-141500.md`), 35 test / 5 nhóm, và mục §7 xếp `gpio-sim` sang
**Ngày 1**.

**Eval suite:** kho chưa có prompt/LLM nào → không có suite để chạy hôm nay; ghi vào
`TSK-S2-08` rằng **bộ phán quyết golden chính là baseline** cho critical path #4.

### Section 4 — Performance

- Không database, không N+1, không mạng trên đường phân giải (pure — đã đọc mã xác nhận);
  claim *"cùng chuỗi phân giải trên ba target"* đứng về mặt tất định.
- **`ENG-P1` · LOW · Parse schema lặp** (`ENG-Q4`): ×N gate ×chiều sâu. Hôm nay N=3; đã có
  TODO #5 cho registry ≥100 gate. Sửa `lru_cache` gộp `TSK-S2-13`.
- **`ENG-P2` · INFO · `ReplaySession` giữ cả vết ghi + dict dẫn xuất trong RAM** — 10.000 sự
  kiện không sao; đã có TODO #3 với mốc 100.000.
- **`ENG-P3` · INFO · Ngân sách `p95` sau khi sửa cửa sổ đo (Issue 7) mới có thể vượt được**
  — ba gate mẫu khai 200/120/90 ms; cưỡng chế bằng **đồng hồ tiêm**, test hiệu năng riêng,
  không neo cổng merge. Không đổi.

### Failure Modes Registry — 5 chế độ hỏng CRITICAL mới

| # | Chế độ hỏng | Xử |
|:---:|:---|:---|
| 1 | **Bao hàm thay per-criterion ⇒ mệnh đề con nới lỏng lọt qua** (nới `c1`, làm `c2` bất khả thoả) | Giữ `is_at_least_as_strict_as`; thu hẹp `CEO-S1-1` còn 2 người tiêu thụ |
| 2 | **`reason` lệch giữa Python và walker** khi ≥2 tiêu chí cùng fail (thứ tự chèn ≠ thứ tự canonical) | `criteria_order` root-first trong cây đã ký + bảng sự thật đầy đủ `ENG-T1` |
| 3 | **Cây cũ/bị sửa trên thiết bị không phát hiện được** (chữ ký phủ artifact, thiết bị đi cây) | `gate_digest` trong cây + CI biên dịch lại byte-y-hệt |
| 4 | **Con nới `budget`/`on_block` và phân giải sạch** (`lax-night`: 900.000 ms + `fail: open` + `degrade` + `fallback_action`) | `TSK-S2-13` + RFC-0004 + 4 fixture phản chứng |
| 5 | **Tái publish base cùng version nới mọi hậu duệ** (byte con không đổi) | `TSK-S3-21` ghim `#sha256:` + lock; bất biến registry = Khối 3 |

*(Hai chế độ hỏng đã ghi từ Phase 1 vẫn nguyên: `gpio-sim` chưa chứng minh, và ba test moat rỗng.)*

### NOT in scope — Phase 3 nói rõ cái gì không làm

- **Trình duyệt C thật + vector tương đương trên phần cứng:** thuộc Khối 1b/Sprint 4–5
  (chưa có bo mạch). Trong 5 tuần chỉ **phát** cây + bảng sự thật host ↔ mô hình C bằng
  đặc tả.
- **Bất biến phiên bản phía registry:** việc Khối 3 (chưa có registry).
- **`on_block.ask.message` máy kiểm được:** tuyên bố ngoài phạm vi (B.3 cho văn bản tự do).
- **`TSK-S2-06` (CEL) ↔ cây:** CEL biên dịch xuống *cùng* cây; vẫn hoãn, không đổi.
- **Nửa âm thanh của P3** (FSM `barge_in`, vector tuân thủ): như khối ⚠️ ở §Premises.

### What already exists — Phase 3 kiểm lại bằng mã

| Bài toán con | Mã sẵn có | Kết luận |
|:---|:---|:---|
| Ngữ nghĩa `allow_when` + thứ tự siết chặt | `constraints.py` (261 dòng, 55 test) | **Tái dùng, không sửa** — compiler import |
| Canonical/digest | `canonical.py` | Tái dùng nguyên |
| Chain merge + 5 nguyên tắc | `gate_resolver.py` | Tái dùng + **vá** (`TSK-S2-13`) |
| Board pins (tên pin hợp lệ) | `hal/board.py` + `boards/*.toml` | **Có sẵn** cho `ENG-Q1`/`CEO-S5-2` — `ReplaySession` chỉ cần nạp `BoardProfile` |
| Trace đọc + thẩm định | `trace.py` | Tái dùng làm loader duy nhất (`ENG-Q2`) |
| CLI khung + hợp đồng mã thoát | `cli/main.py` | Tái dùng; `ENG` không thêm lệnh mới |
| Đồng hồ/ngân sách | chưa có | `TSK-S2-04` |

### Điều chỉnh lịch — `ENG-A3` (TASTE DECISION)

**Bảy task ID (sáu dòng bảng) rời V1, không cần kỹ năng mới:**

| Task | Hiện | Sang | Vì sao |
|:---|:---:|:---:|:---|
| `TSK-S2-01` HAL `sim` | V1 | **V2** | Kỹ sư nhúng; `roadmap:181` đã muốn V2 trong thiết kế HAL |
| `TSK-S3-05` HAL `linux` + `gpio-sim` | V1 | **V2** | Việc kernel/configfs — V2 đã được giao dựng runner |
| `TSK-S3-16` `digests.lock` | V1 | **V3** | CI |
| `TSK-S3-17` asset vào wheel | V1 | **V3** | Đóng gói |
| `TSK-S3-18` `gate explain` | V1 | **V3** | CLI trên resolver đã có |
| `TSK-S3-19` + `TSK-S3-20` | V1 | **V3** | CLI + tài liệu |

Sau khi chuyển (tính cả hai task mới của Phase 3): chạy **23** = **13 V1 + 2 V2 + 8 V3**
(trước: 20 V1 + 0 V2 + 3 V3). Ước lượng **~8,6 → ~5,6–6,1 tuần-người V1**. Vẫn **không lắp
vào 5 tuần**; lắp vào 6,5 **nếu** F2 (golden reference `sim`-only) được kích hoạt. Không
đổi phạm vi, chỉ đổi chủ trì — P2/P3, nhưng nó sửa một dòng kế hoạch tự khẳng định
(§Dependencies: *"V2 không có task nào"*), nên **surface ở Final Gate**.

### TASTE DECISION mới của Phase 3

| ID | Vấn đề | Hai đường |
|:---|:---|:---|
| **`ENG-T1`** | `CEO-S1-1` sống ở dạng thu hẹp (2 người tiêu thụ, giữ per-criterion) hay bị thay bằng bao hàm | **(a)** Thu hẹp — giữ bảo đảm từng mệnh đề, thêm `criteria_order` + digest trong cây · **(b)** Thay bằng bao hàm — một hiện thực ít hơn nhưng **nới lỏng nguyên tắc 2** (đã chứng minh) |
| **`ENG-T2`** | Ghim `extends` bằng đổi `pattern` (schema RFC) hay chỉ bằng lockfile | **(a)** `@<ver>#sha256:…` trong schema + lock — ghim cả gate kéo từ registry · **(b)** Chỉ lock trong kho — rẻ hơn, không bảo vệ được registry |
| **`ENG-T3`** | Chuyển 7 task khỏi V1 như `ENG-A3` | **(a)** Chuyển — 2,5–3 tuần-người rời đường găng, chi phí 0 · **(b)** Giữ nguyên — V2 tiếp tục nhàn rỗi, V1 ước lượng ~8,6 tuần |

**USER CHALLENGE: không phát sinh mới.** Sáu mục `CEO-X1`…`CEO-X6` giữ nguyên và đi tới
Final Gate; `ENG-A1` **không** phải user challenge vì nó sửa một khuyến nghị *của review*,
không sửa định hướng *của người*.

### Cross-phase themes — ba chủ đề lặp ở ≥2 phase

1. **"Bộ đo của moat là test rỗng"** — `CEO-S5-2` (Phase 1) · `DX-C2` (Phase 2.5) · mật độ
   test 4 hàm ở `testing/` + 3 test rỗng (Phase 3). Ba phase độc lập chỉ cùng một module.
   **Tín hiệu mạnh nhất của cả pipeline.**
2. **"Kế thừa/registry chính là sản phẩm, và nó đang hở"** — `CEO-X5` (bán gì, cho ai) ·
   `DX-M3` (lược đồ nói về `agent.toml` không tồn tại) · `ENG-A2`/`ENG-A2b` (3/4 bề mặt
   nới lỏng không được bảo vệ, `extends` không ghim). Mô hình kinh doanh registry cộng đồng
   đứng trên một hàng rào phủ 1/4 bề mặt.
3. **"Kế toán đếm sai theo dòng thay vì theo task"** — `CEO-S0-1` (Phase 1) ·
   `ENG-A0-2` (Phase 3). Cùng một lớp lỗi, hai vòng review khác nhau.

### Decision Audit Trail — Phase 3

| # | Quyết định | Loại | Nguyên tắc | Vì sao | Bị từ chối |
|:---:|:---|:---|:---|:---|:---|
| 1 | Giữ `is_at_least_as_strict_as`, thu hẹp `CEO-S1-1` còn 2 người tiêu thụ | Auto | P1 + P5 | Bao hàm đã chứng minh **yếu hơn**; giữ bảo đảm từng mệnh đề | Thay bằng bao hàm trên cây |
| 2 | Compiler host `import parse_constraint`; thiết bị không chuẩn hoá | Auto | P4 + P5 | Một bộ chuẩn hoá, một bộ phát; `to_artifact()` không đổi ⇒ digest không vỡ | Sửa `constraints.py` (RFC) hoặc viết lại normalizer |
| 3 | `criteria_order` tường minh, root-first, trong cây đã ký | Auto | P5 | Thứ tự từ điển làm `reason` nhiễu khi đổi tên tiêu chí; root-first cho chẩn đoán tốt hơn | Thứ tự canonical / thứ tự chèn |
| 4 | `gate_digest` trong `decision_tree.v1.json` + CI biên dịch lại byte-y-hệt | Auto | P1 | Chữ ký phủ artifact, thiết bị đi cây — phải khép khoảng hở | Tin tưởng cây trên thiết bị |
| 5 | Bảng sự thật **đầy đủ** Python ↔ C (verdict **và** reason) | Auto | P1 | Miền nhỏ, không lấy mẫu; đây là bằng chứng của "một ngữ nghĩa" | Lấy mẫu vài ca |
| 6 | Ghi vào RFC-0003: `constraints.py` giờ định nghĩa thứ chạy xuống silicon | Auto | P1 | Tăng trọng lượng RFC, phải viết ra thay vì phát hiện sau | Để ngầm |
| 7 | `TSK-S2-13` + RFC-0004 vá `budget`/`on_block`; 4 fixture phản chứng | Auto | P1 | `lax-night` chứng minh lỗ đang mở; nguyên tắc 2 không được phủ 1/4 | Chấp nhận rủi ro vì gate con "hiếm" |
| 8 | `to:` **và `fallback_action`** vào dàn chặt-lỏng (`human` chặt nhất); `ask.message` ngoài phạm vi | Auto | P1 + P5 | `human`→`agent` và đổi `fallback_action` đều là nới thật; văn bản tự do không kiểm được nên phải **nói rõ** là ngoài phạm vi | Bỏ qua `to:`/`fallback_action`; để `ask.message` mập mờ |
| 9 | `TSK-S3-21` ghim `extends` bằng `#sha256:` **cộng** kiểm `URI ↔ name/version`; pattern gộp vào RFC-0003 | Auto | P1 | Bề mặt quan trọng nhất của mô hình registry; digest không bắt được lệch danh tính | Chỉ lockfile |
| 10 | Bất biến phiên bản phía registry → TODOS #11 (Khối 3) | Auto | P2 + P3 | Không có registry hôm nay; đã ghim phía client | Làm server giả |
| 11 | `_parse_events()` bỏ ghim cứng `unlock_door` + test tên action khác | Auto | P1 | `ENG-Q1` là cùng gốc với 3 test rỗng | Để nợ tới Sprint 4 |
| 12 | Gộp hai fallback basename thành một loader `trace.load_trace()` | Auto | P4 | Hai bản sao của cùng lỗi `DX-H3` | Sửa cả hai chỗ |
| 13 | `deepdiff`: dùng ở `TSK-S3-04` hoặc gỡ trước publish | Auto | P3 + P4 | Phụ thuộc lõi chưa dùng ở đâu | Để nguyên không quyết |
| 14 | `lru_cache` cho `_gate_schema()`, gộp `TSK-S2-13` | Auto | P3 | Một dòng, cùng tệp đã mở vì RFC-0004 | TODO riêng cho N≥100 |

*(Chuyển 7 task khỏi V1 = TASTE `ENG-T3`; `ENG-T1`/`ENG-T2` là TASTE — ba cái này
**không** auto-decide, đi Final Gate. Phần hoãn của Phase 3 đã ghi vào `TODOS.md` #10–#12;
`TODOS.md` #8 nay ghi rõ `TSK-S2-12` làm `--explain` rẻ đi.)*

### Completion Summary

| Hạng mục | Kết quả |
|:---|:---|
| Step 0 | 3 phát hiện (`ENG-A0-1..3`) |
| Section 1 Architecture | **3 phát hiện CRITICAL** (`ENG-A1` gồm ba chân · `ENG-A2` · `ENG-A2b`) → 5 chế độ hỏng |
| Section 2 Code Quality | 4 phát hiện (`ENG-Q1` HIGH, Q2/Q3 MEDIUM, Q4 LOW) |
| Section 3 Test Review | 3 phát hiện (`ENG-T1..T3`, HIGH), test plan artifact đã ghi |
| Section 4 Performance | 0 phát hiện mới (3 ghi chú, 1 sửa 1 dòng) |
| Task | **+2**: `TSK-S2-13`, `TSK-S3-21` → tổng **34**, chạy **23** (13 V1 + 2 V2 + 8 V3), hoãn **11** |
| Ước lượng | ~8,6 → **~5,6–6,1 tuần-người V1** (sau `ENG-A3`) |
| RFC | +1: **RFC-0004** (kế thừa `budget`/`on_block`); `extends` gộp vào **RFC-0003** |
| TASTE DECISION | +3 (`ENG-T1..T3`) |
| USER CHALLENGE | +0 (6 cũ giữ nguyên) |
| Auto-decided | 14 mục (xem Decision Audit Trail — Phase 3) |

**VERDICT: ENG REVIEW RUN — 3 phát hiện CRITICAL (A1/A2/A2b, thành 5 chế độ hỏng) đã quyết, tất cả bằng chứng chạy được
trong phiên này. Kế hoạch vẫn NOT CLEARED:** bốn quyết định Tuần 1 (`CEO-X6`) chưa ai chốt,
`gpio-sim` chưa chứng minh, và ba bề mặt kế thừa chỉ được đóng khi `TSK-S2-13` + `TSK-S3-21`
được nhận. Đây là cổng bắt buộc — nó **không** chặn việc ship tài liệu này, nó chặn việc
merge mã.

> **Phase 3 complete.** Codex: 0 concerns (401, `[subagent-only]`). Claude subagent: 4 phát
> hiện chịu lực + Part B chưa gửi; tôi dựng lại cả 4 bằng chứng. Consensus: **0/6 CONFIRMED,
> 6/6 FLAGGED** (một tiếng nói). Passing to Phase 4 (Final Gate).
