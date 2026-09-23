# Nhật ký thay đổi — NeuroEdge

Toàn bộ thay đổi đáng kể của dự án được ghi tại đây, theo tinh thần
[Keep a Changelog](https://keepachangelog.com/) và
[Semantic Versioning](https://semver.org/lang/vi/).

> **Tệp này có ba phần, đọc theo nhu cầu:**
>
> | Bạn cần gì | Đọc mục |
> |:---|:---|
> | Biết đã thay đổi những gì | [§1 Nhật ký phiên bản](#1-nhật-ký-phiên-bản) |
> | Chạy được hệ thống ngay | [§2 Cách vận hành](#2-cách-vận-hành) |
> | Tiếp quản để build tiếp | [§3 Bàn giao ngữ cảnh sản phẩm](#3-bàn-giao-ngữ-cảnh-sản-phẩm) |
>
> **Nguồn sự thật về tiến độ** vẫn là [`neuroedge-roadmap.md`](neuroedge-roadmap.md)
> §0 (bảng theo dõi và thẻ bàn giao). Tệp này kể *đã xây gì và chạy thế nào*;
> roadmap kể *còn gì phải xây*. Khi hai tệp lệch nhau, roadmap đúng.

---

## 1. Nhật ký phiên bản

Mỗi task xong thêm một mục vào `[Chưa phát hành]`, theo `CONTRIBUTING.md` §8.2
bước 3. Khi phát hành, đổi tiêu đề thành số phiên bản và ngày.

### [Chưa phát hành]

#### Đã thêm

- **Cửa trước cho người mới.** `README.md` gốc: sản phẩm là gì, sơ đồ 30 giây, một gate và
  một `@action` trích từ tệp thật, 3 lệnh chạy thử. `tests/test_readme_quickstart.py` chạy đúng
  các lệnh đó và kiểm hai đoạn trích khớp tệp gốc.
- **Bảng thuật ngữ** `docs/user/thuat-ngu.md` — nơi duy nhất giải mã `FR-*`, `Q-N`, `A1`, `CEO-X1`…,
  cảnh báo hai mã trùng chữ (`A1`, `V1`). Ba bảng "Quy ước tài liệu" ở PRD và hai roadmap nay dẫn về đó.
- **Sơ đồ Mermaid** tại chỗ của từng khái niệm: luồng `c.do()` → gate → token → HAL
  (`docs/spec/threat_model.md` §1), cây kế thừa ba gate mẫu (proposal Phụ lục B.5), FSM hội thoại
  (roadmap §3.8, thay bản ASCII).
- **TSK-S2-12 — cây quyết định phía host.** `engine/decision_tree.py`: `compile_tree`
  (`criteria_order` root-first + `gate_digest`), `walk` trả phán quyết + `reason` đầu tiên.
  Bảng sự thật cho walker C: `fixtures/decision_trees/`. Kiểm: `pytest tests/test_decision_tree.py`.
- **TSK-S2-03 — Gate Engine trả phán quyết.** `engine/gate.py`: `ActionContractEngine.evaluate()`
  lấy dữ kiện trong ngân sách `p95`, đi cây, phân phát `on_block` theo Q-17; tái tạo đúng
  3 vết ghi chuẩn mực. Kiểm: `pytest tests/test_gate_engine.py`. (FR-GATE-03/04/09)
- **TSK-S2-08 — SystemOne/SystemTwo + ngữ pháp lệnh cố định.** `models/`: mất mạng thì
  hỏi `CommandGrammar` (`commands.toml`, khớp mẫu + `difflib`, giữ dấu tiếng Việt); không có
  fallback ⇒ `gate_unreachable`. Kiểm: `pytest tests/test_models.py`. (Q-14, Q-15, FR-MDL-01/02/03)
- **TSK-S2-01 — HAL `sim`.** `hal/sim.py`: `SimHAL` phủ 5 nguyên thủy trên `sim-default`,
  gõ chữ là đầu vào mặc định (Q-15), `digital_out` trả `PendingCommand.cancel()` (RB-3).
  Kiểm: `pytest tests/test_hal_sim.py`. (FR-TGT-01, FR-HAL-01)
- **TSK-S2-04 — mạch ngắt suy giảm.** `engine/circuit_breaker.py` bọc nguồn chính của
  SystemOne: lỗi liên tiếp ⇒ mở, đi thẳng fallback; không bao giờ sinh ALLOW. Ma trận A4
  đạt. Kiểm: `pytest tests/test_fail_closed.py`. (FR-ACE-03, NFR-REL-02)
- **TSK-S2-05 — `@action`, `c.do()`/`c.say()`, token phán quyết dùng một lần.** `actions/`,
  `hal/digital.py`: chỉ `c.do()` chạy được hành động; token TTL = p95 × 3, mỗi chân tiêu một
  lần (NE1002). Kiểm: `pytest tests/test_actions.py`; ranh giới: `docs/spec/threat_model.md`.
- **TSK-S2-02 — `neuroedge build`.** `engine/compiler.py` đối chiếu `agent.toml` + `@action` với
  bo mạch (Phụ lục A.1), báo **mọi** vấn đề trong một lần, ghi cây quyết định. Agent mẫu
  `fixtures/agents/villa-concierge/`. Kiểm: `pytest tests/test_compiler.py`. (FR-HAL-04/05)
- **Quy tắc hoàn thành task.** `CONTRIBUTING.md` §8: nơi duy nhất cho việc cập nhật
  tiến độ, changelog, đặc tả; bảng "mỗi sự thật một nơi"; mẫu PR có checklist.
  Roadmap §0.4, §11.2 và `CLAUDE.md` nay chỉ dẫn về đó.
- **Tài liệu cho người dùng (`docs/user/`).** Bản đồ tài liệu, hướng dẫn sử dụng,
  và trạng thái sinh tự động từ roadmap §0 (`scripts/gen_user_status.py`).
  Kiểm: `pytest tests/test_user_status_fresh.py`.

#### Đã đổi

- **Design doc Giai đoạn 1 tách biên bản review** sang `docs/archive/giai-doan-1-review-log.md`
  (~1 000 dòng, lưu trữ, không quy phạm); design doc còn ~600 dòng, thêm khối "Đọc nhanh" chỉ nơi
  thiết kế đang chạy. Tham chiếu theo số dòng trong RFC-0002 đổi sang tên mục.
- **HAL chưa gắn `Conversation` từ chối mọi lệnh,** kể cả chuỗi trông như bằng chứng — chỉ
  token do `c.do()` phát hành điều khiển được chân (A3).
- **HAL kiểm tên chân trước khi tiêu bằng chứng,** và `hal.pin()` ném lỗi với tên chân không
  có trên bo mạch — một assertion gõ sai không còn "đạt" được (CEO-S5-2).
- **`ActionContractEngine` bỏ tham số `fail_closed`.** Gate chỉ fail-open khi chính tài liệu
  của nó khai `fail: open`. PRD Phụ lục B: fail-closed là phán quyết, không phải exception.
- **Thẻ bàn giao (roadmap §0.3) rút gọn** theo §8.3: bỏ lịch sử đã có trong changelog,
  bỏ hai việc đã xong còn nằm ở *Việc tiếp theo*, *Lưu ý* chỉ giữ điều chưa có ở §3.3.
- **Bỏ con số dễ lỗi thời** khỏi `CLAUDE.md` và §2 (số test, số fixture); số test
  hiện hành chỉ còn ở roadmap §0.1.

#### Đã sửa

- **Sáu lỗ an toàn từ review đối kháng mã A1** — hai trong số đó kích được chân GPIO.
  Kiểm: `pytest tests/test_safety_regressions.py` (15/16 test fail trên mã trước khi sửa).
  - Độ tin cậy `NaN`, `True`, ngoài `[0, 1]` từng lọt ngưỡng `confidence_gte` ⇒ nay `criterion_unavailable`.
  - `fail: open` từng biến một dữ kiện đã biết là "không" thành ALLOW khi thẩm định suy giảm ⇒
    `open` chỉ tha điều không quyết được.
  - Nhà cung cấp ném lỗi hoặc treo ⇒ nay là phán quyết suy giảm (mạch ngắt ghi nhận, fallback
    được hỏi, timeout theo ngân sách còn lại), không còn là exception không có vết ghi.
  - `fallback_action` cần tham số ⇒ `build` từ chối, lúc chạy bỏ qua thay vì `TypeError`.
  - `never_pulsed()` từng đúng sau `on()`; lệnh sau từng xoá lệnh trước ⇒ chân lưu lịch sử lệnh.
  - Task sinh trong thân hành động từng gọi lại được hành động sau khi `c.do()` trả về.
- **CLI nuốt mất tên bảng TOML trong chẩn đoán.** `rich` hiểu `[requires]`,
  `[capabilities.digital_out]` là thẻ markup nên lời hướng dẫn in ra thiếu chữ. Mọi trường
  `where`/`why`/`how` nay được escape. Kiểm: `test_cli_build_fails_with_exit_1_and_every_problem`.
- **Hai nhãn lỗi thời.** `TODOS.md` #5 ghi thì quá khứ cho phần `lru_cache` đã vá ở
  `TSK-S2-13`; roadmap §0.2 ghi Sprint 2 `8%` (1/13) thay vì `0%`.

### [0.4.0] — 2026-09-23 — Gỡ chặn Sprint 2: chốt 9 quyết định, đồng bộ tài liệu

Rà soát toàn bộ tài liệu ngày 2026-09-23 kết luận **chưa triển khai được**: bốn
quyết định Tuần 1 chưa ai chốt, roadmap chưa nhận kế hoạch đã duyệt ở
`docs/designs/`, hai RFC bắt buộc chưa có, và PRD/proposal mâu thuẫn ở ba điểm
P0. Phiên này chốt quyết định với người phụ trách (minhlt) và đồng bộ lại.

#### Quyết định — ghi ở `neuroedge-prd.md` §15

| Mã | Quyết định | Gỡ chặn gì |
|:---|:---|:---|
| **Q-10** | LiteLLM là **thư viện định tuyến (SDK)** sau `neuroedge.models.providers`, cài qua extra `neuroedge[cloud]`; không chạy proxy | `TSK-S2-11` |
| **Q-11** *(một phần)* | **LiteLLM đã duyệt** + chính sách phụ thuộc bắc cầu (allowlist giấy phép, kiểm trong CI). Hawkbit/EMQX vẫn mở tới trước Khối 2 | Tiêu chí ra 6 Sprint 1, `TSK-S2-11` |
| **Q-14** | Mất mạng ⇒ gate **vẫn lượng giá** bằng bộ nhận diện **lệnh cố định** cục bộ; chỉ `gate_unreachable` khi fallback không chạy. Backend theo target, chung một ngữ pháp lệnh (`sim`: chữ gõ · `esp32s3`: ESP-SR MultiNet hoặc TFLite Micro/ESP-NN) | `CEO-X1` (FR-ACE-03 ↔ FR-MDL-03) |
| **Q-15** | `sim` mặc định **gõ chữ**, không mạng, không key; giọng nói là tuỳ chọn | FR-DX-02 ↔ FR-PER-07 |
| **Q-16** | GPIO `linux`: `gpio-sim` trong CI + mua 1 RPi 5 dự phòng | F1, `TSK-S3-05` |
| **Q-17** | `on_block` v1.0 được **đặc tả** (luôn chặn; `escalate`/`ask` ghi vết ghi + hook; `degrade` chạy `fallback_action` qua gate riêng) ⇒ **không cần waiver §11.3** | Cổng merge A1 |
| **Q-18** | Kế thừa `budget`/`on_block`: `p95` chỉ giảm · chuỗi `closed` không khai `open` · con không tự đưa vào `degrade` ([RFC-0004](docs/rfc/0004-ke-thua-budget-on-block.md)) | Lỗ `lax-night` (`ENG-A2`), `TSK-S2-13` |
| **Q-19** | Lịch bằng ngày tuyệt đối: A1 2026-09-28 → 10-25 · A2 10-26 → 11-15 · Sprint 4 mở 2026-11-16 | Mâu thuẫn 5 ↔ 6,5 tuần |
| **Q-20** | Cổng nhu cầu 2026-10-25 là **cổng mềm**; câu hỏi kinh doanh `CEO-X2..X5`, `CEO-T1..T4` vào `TODOS.md` | `CEO-X3` |

Tự chốt kèm theo, ghi để người đọc biết: RFC-0003 (ghim `extends` + đóng băng
`decision_tree.v1.json`) và `TSK-S3-21` hoãn tới Sprint 4; `TSK-S2-07`/`S3-10`/`S3-11`
hoãn cùng nhau; `TSK-S3-13` sang Sprint 5; đổi chủ trì theo `ENG-T3`.

#### Đã sửa

- **Bộ test phụ thuộc môi trường.** Shell có `FORCE_COLOR` làm 7 test CLI fail,
  và `gate resolve --json` in ra **không phải JSON**. `--json` và dòng digest của
  `gate publish` nay ghi thẳng stdout; `tests/conftest.py` gỡ `FORCE_COLOR` trước
  khi import CLI. Bộ test xanh ở cả hai môi trường.
- **Tài liệu:** PRD 1.3 (FR-ACE-03, FR-DX-02, FR-GATE-02/03/06, FR-CLI thêm
  `gate lint`/`gate resolve`, danh mục lỗi theo tên trong mã), proposal Phụ lục B
  theo RFC-0001 §9 + Q-17/Q-18, roadmap 1.3 (34 task, chủ trì mới, ngày tuyệt đối),
  `CONTRIBUTING.md` §5 ghi đúng lệnh CI.

#### Đã thêm — RFC-0004 + `TSK-S2-13`

[`docs/rfc/0004-ke-thua-budget-on-block.md`](docs/rfc/0004-ke-thua-budget-on-block.md)
(✅ chấp thuận, Q-18) và hiện thực trong `engine/gate_resolver.py`: `p95` của con ≤
cha (nguyên tắc 2), chuỗi `closed` không mở lại (nguyên tắc 4), con không tự đưa vào
`degrade` (nguyên tắc 2). Vẫn **năm** nguyên tắc. Corpus phản chứng: +4 invalid,
+1 valid, +1 registry. Test **210 → 229**, 0 skip.

### [0.3.0] — 2026-09-22 — Giai đoạn 2: thị giác, phủ rộng phần cứng, nền tảng cho maker

Thay đổi **chỉ ở tầng tài liệu**. Ba lược đồ trong `schemas/` **chưa đổi** và
không được đổi cho tới khi RFC-0002 được phê duyệt; bộ test vẫn 210/210 xanh.

#### Đã thêm — RFC-0002 *(trạng thái: đang thảo luận)*

[`docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md`](docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md)
*(Ghi chú 2026-09-23: RFC-0002 đã **thu hẹp** chỉ còn mở enum `target` +
`TARGET_TIERS`; `vision.in` chuyển sang V1b. Đoạn dưới giữ nguyên như bản gốc.)*
đề xuất mở enum `target` ở `board.v1` và `trace.v1`, thêm nguyên thủy tùy chọn
`vision.in`, và mở trường vết ghi cho bằng chứng thị giác.

**Phát hiện dẫn tới RFC này:** thêm một target **không phải hạng mục roadmap** mà
là thay đổi lược đồ đã đóng băng. Danh sách `["sim", "linux", "esp32s3"]` bị lặp
ở bốn nơi — hai lược đồ, `hal/board.py`, và chuỗi thông điệp lỗi trong
`fixtures/traces/expected_errors.yaml` — trong đó `schemas/` và `fixtures/traces/`
đều thuộc diện RFC bắt buộc theo `CONTRIBUTING.md` §3.

RFC-0002 cũng phải nới hai bất biến kiểm thử: mọi bo mạch dùng chung tập tên chân,
và mọi profile khai đủ năm nguyên thủy. §5 của RFC nêu rõ nới thế nào mà không
làm hệ thống lỏng hơn.

#### Đã thêm — Tài liệu Giai đoạn 2

[`neuroedge-roadmap-phase2.md`](neuroedge-roadmap-phase2.md) — sáu khối V1a, V1b,
V2, V3, P1, P2 từ Tháng 9 đến Tháng 24, chạy **song song** Khối 4 AURA chứ không
nối tiếp. AURA là nguồn dữ liệu R3 cho chính thị giác.

#### Đã đổi — Nguyên tắc P-2 bỏ số đếm

*"Ba môi trường thực thi ngang hàng"* → *"Các môi trường thực thi ngang hàng"* ở
proposal §0.4 và PRD §1.5. **Hệ quả kỹ thuật giữ nguyên nguyên văn** — "không rẽ
nhánh logic theo target trong mã nguồn agent" không hề bị phá khi thêm target;
chỉ con số bị phá. Khoảng 42 chỗ viết cứng "3 môi trường" trên ba tài liệu được
sửa theo cùng một mẫu.

#### Đã thêm — Phân tầng cam kết theo bậc target

| Bậc | Target | Cam kết của đội lõi |
|:---:|:---|:---|
| **1 — Chính thức** | `sim` · `linux` · `esp32s3` | `verify` 100%, kiểm thử hằng đêm |
| **2 — Mở rộng** | `jetson` | Bảo trì, verify trên miền phán quyết |
| **3 — Cộng đồng** | `stm32` · `rp2350` | Không cam kết; cộng đồng tự kiểm chứng qua Bộ kiểm thử tuân thủ |

Mọi ngưỡng chất lượng trong proposal §12 và PRD §11 nay neo tường minh vào **bậc 1**.
Ghi nhận bằng `FR-TGT-08` và `Q-13`; rủi ro pha loãng chất lượng ghi ở `R-7` (PRD)
và rủi ro #6 (proposal §11).

#### Đã đổi — Mở khóa vision và Jetson khỏi danh mục hoãn

proposal §9 và PRD §14: ba dòng chặn vision, Jetson và độ phủ bo mạch chuyển sang
*"Đưa vào Giai đoạn 2"*. Cột lý do phải **viết lại**, không chỉ đổi trạng thái —
hai dòng cũ viện dẫn chính con số *"ba môi trường đã đủ"* làm lập luận, nên giữ
nguyên sẽ khiến tài liệu tự mâu thuẫn.

**Vision trượt bộ lọc R1** (không rút ngắn TTFV) nhưng **thắng R2** (không bổ sung
muộn được mà không viết lại kiến trúc). Theo proposal §2, thỏa R1 *hoặc* R2 là đủ.
Vì vậy Giai đoạn 2 tách **V1a đặt chỗ kiến trúc** — chỉ chốt chỗ trong hợp đồng,
không viết driver, không đụng TTFV — khỏi **V1b hiện thực**, mở khóa khi có nhu
cầu đo được từ khách hàng AURA thật.

#### Đã thêm — Chính sách cho tài sản do bên thứ ba sở hữu

proposal §6.4 có thêm hàng cho **adapter và HAL port**: tác giả giữ bản quyền, mã
nằm ở kho riêng, NeuroEdge chỉ lập chỉ mục. §1.7 bổ sung lập luận an toàn riêng
cho loại tài sản này — lập luận biện minh cho việc chia sẻ gate (*"nhẹ, minh bạch,
không rủi ro pháp lý"*) **không chuyển sang được** cho mã thực thi chạy gần cơ cấu
chấp hành. Ba cổng kiểm soát: Bộ kiểm thử tuân thủ, sandbox phân quyền, đối chiếu
năng lực lúc build.

#### Đã thêm — KPI Giai đoạn 2 (§12.4) và mở rộng G2/G3

§12 trước đây kết thúc ở mốc 12 tháng, để lại vùng trắng cho Giai đoạn 2. Bổ sung
V-G1 đến V-G5 ở mốc 24 tháng. G2 và G3 mở rộng để **đếm cả adapter và HAL port**,
không chỉ gate và agent.

**V-G1 được chỉnh so với đề xuất ban đầu** để nối được vào doanh thu: ngoài ngưỡng
5.000 thiết bị vision, thêm ngưỡng **≥ 500 thiết bị thuộc đội có gói Fleet trả phí**.
Lý do: usecase consumer thu hút người dùng nhưng người dùng cuối không trả tiền, và
sau khi bỏ doanh thu inference ở v5.3, Fleet là dòng thu duy nhất và tính theo đội
thiết bị doanh nghiệp.

#### Đã đổi — Chuẩn hóa hệ ký hiệu và ma trận truy vết

Một đợt rà soát toàn bộ bộ tài liệu tìm ra năm lỗi cascade. Tất cả đã sửa.

| # | Lỗi | Cách sửa |
|:---:|:---|:---|
| 1 | **Hai bộ `C1–C7` khác nhau dùng chung nhãn** — PRD §11.3 (nghiệm thu phát hành) và roadmap §8.3 (tiêu chí ra Khối 2/3). Không phải chi tiết hóa của nhau: roadmap C2 = PRD C1, roadmap C4 (≥10 gate) lệch PRD C5 (≥20 gate), năm tiêu chí còn lại không có cặp | Bộ của roadmap đổi thành **TR-1…TR-7** kèm bảng chỉ rõ mỗi TR phục vụ tiêu chí C nào; TR nào không có C tương ứng được đánh dấu *(nội bộ)* |
| 2 | **Ký hiệu `R` mang hai nghĩa** — `R1–R4` là bộ lọc ưu tiên (proposal §2), `R-1…R-7` là rủi ro sản phẩm (PRD §13.2). Cả hai xuất hiện trong cùng một hàng bảng ở PRD §14 | Bộ lọc đổi thành **PF-1…PF-4**. Hệ mã rủi ro `R-n` giữ nguyên |
| 3 | **Sổ quyết định bị chẻ đôi** — PRD có Q-1…Q-7, Q-12, Q-13; roadmap có Q-1…Q-12. Không tài liệu nào giữ đủ bộ, và **Q-7 được ghi ĐÃ CHỐT ở PRD nhưng đang mở ở roadmap** | PRD §15 thành sổ duy nhất với đủ **Q-1…Q-13**; roadmap §10 chuyển thành bản theo dõi trạng thái và đã khớp hoàn toàn |
| 4 | **Hai sổ rủi ro chồng lấn không khai báo ranh giới**, và cả hai đánh số sai thứ tự | Khai báo ranh giới: proposal §11 = rủi ro *chiến lược*, PRD §13.2 = rủi ro *sản phẩm và thực thi*. Ba cặp giao nhau được ánh xạ tường minh. Cả hai sổ sắp lại đúng thứ tự |
| 5 | **Ký hiệu `§` mang hai nghĩa** — bảng Quy ước PRD nói `§x.y` trỏ proposal, nhưng nhiều chỗ tự trỏ chính nó; roadmap và phase2 không có bảng quy ước nào | Thêm quy ước `§x.y của tài liệu này` cho tham chiếu nội bộ và áp dụng nhất quán. Roadmap và phase2 có bảng **Quy ước tài liệu** riêng |

**Ma trận truy vết PRD mở rộng từ 44% lên 100%.** Phụ lục A trước đây chỉ truy vết theo mục tiêu (A.1) và nguyên tắc (A.2), bỏ trống 85/151 yêu cầu — trong đó có **toàn bộ NFR**. Bổ sung **A.3** (đối chiếu yêu cầu phi chức năng: cách kiểm chứng và tiêu chí nghiệm thu) và **A.4** (các nhóm yêu cầu chức năng không rơi vào trục mục tiêu hay nguyên tắc: HAL, PER, CI, GOV, CLI, DX, TEL…). Mọi hàng ghi rõ tên nhóm để truy vết kiểm được bằng máy.

Ngoài ra: tiêu chí **A1** trong roadmap có hai phát biểu lệch nhau (ngưỡng cá nhân vs trung vị trên 10 người) — đã đồng bộ về nguyên văn PRD.

#### Cần chú ý — Hai bài toán để mở có chủ đích

1. **Ngữ nghĩa gate lượng giá trên bằng chứng thị giác chưa được giải.** Cho tới
   khi có RFC riêng, kết quả thị giác chỉ được dùng làm thông tin ngữ cảnh; agent
   muốn hành động dựa trên camera phải quy về `bool` / `level` / `choice` qua
   `SystemOne`. Rule engine giữ nguyên 100% xác định.
2. **Ngân sách bộ nhớ cho nguyên thủy thứ sáu trên vi điều khiển** chưa đo được vì
   chưa có bo mạch. Không chặn RFC, nhưng chặn việc khai `vision_in` cho `esp32s3`.

### [0.2.0] — 2026-09-21 — CR-1.0: Chuyển định hướng cloud-first

Thay đổi **chỉ ở tầng tài liệu**, không đụng một dòng mã nguồn nào và không đụng
ba lược đồ đã đóng băng trong `schemas/`. Nguồn thay đổi là yêu cầu tinh chỉnh
tài liệu **CR-1.0 — chuyển định hướng cloud-first** (hồ sơ lưu ngoài kho mã), đã
áp dụng vào proposal v5.3 · PRD v1.1 · roadmap v1.1.

#### Đã đổi — Định hướng kiến trúc

- **Cloud-first, provider-pluggable.** Toàn bộ tầng AI (LLM, ASR, TTS) trở thành
  nhà cung cấp thay thế được, kết nối qua **chuẩn OpenAI API** hoặc **adapter do
  người dùng tự viết**. Phần nặng về xử lý ngôn ngữ chạy trên cloud hoặc host;
  `esp32s3` chỉ còn thu/phát âm thanh, AEC/VAD, máy trạng thái hội thoại và thẩm
  định gate.
- Ghi nhận bằng cách **mở rộng nguyên tắc P-4** (proposal §0.4 nguyên tắc 4 ·
  PRD §1.5) thay vì thêm nguyên tắc thứ sáu — số nguyên tắc bất biến vẫn là năm.
- **Fail-closed không đổi.** Gate và máy trạng thái chạy hoàn toàn trên thiết bị;
  `NFR-RES-04` (100% tính năng an toàn hoạt động ngoại tuyến) giữ nguyên tuyệt đối.

#### Đã đổi — Mô hình thương mại

- **Bỏ hoàn toàn doanh thu inference.** Mô hình cost-plus 5–10% trên token bị xóa
  khỏi proposal §6.3. **Fleet OS là dòng doanh thu duy nhất.**
- **Inference Gateway → Lớp trừu tượng nhà cung cấp (Provider Abstraction Layer).**
  Chuyển từ dịch vụ thương mại sang **lõi mã nguồn mở MIT tự vận hành**
  (proposal §6.1, §6.4). Người dùng tự chạy, tự giữ khóa, tự trả phí cho nhà
  cung cấp. Đánh số mục §6.1–§6.4 giữ nguyên nên mọi tham chiếu chéo còn đúng.
- Nhóm **FR-GW-01→07** của PRD chuyển từ mốc v1.1 (thương mại) sang **lõi OSS
  v1.0**; FR-GW-05 hạ từ P0 xuống P1.

#### Đã thêm — Yêu cầu mới trong PRD

| Mã | Nội dung | Ưu tiên |
|:---|:---|:---:|
| `FR-MDL-07` | Provider pluggable cho LLM, ASR và TTS | P0 |
| `FR-MDL-08` | Adapter kết nối do người dùng tự viết | P0 |
| `FR-MDL-09` | ASR/TTS thay thế được qua cấu hình | P0 |
| `FR-PER-07` | Cloud-first voice — MCU chỉ stream âm thanh | P0 |
| `FR-REG-08` | Kho chia sẻ adapter kết nối provider | P1 |
| `NFR-SEC-08` | TLS 1.3 cho dữ liệu gửi tới provider cloud | P0 |
| `NFR-PERF-07` | Độ trễ thoại với provider request-response: P95 < 1.500 ms | P1 |
| `R-6` | Rủi ro phụ thuộc provider cloud khi mất kết nối | — |
| `Q-12` | Chuẩn kết nối mặc định là OpenAI API *(ĐÃ CHỐT)* | — |

#### Đã đổi — Phạm vi thực thi

- **Sprint 2** nhận thêm `TSK-S2-11` (lớp trừu tượng provider) và **Sprint 3**
  nhận `TSK-S3-13` (ASR/TTS qua provider cloud) — lớp provider dựng ở **Khối 1a**
  chứ không chờ Khối 2.
- **Sprint 5 giảm phạm vi:** không hiện thực STT/TTS trên thiết bị; thêm
  `TSK-S5-06` (client streaming lên provider). Rủi ro **R-1 hạ từ Cao xuống
  Trung bình**. Bốn ràng buộc RB-1→RB-4 cho Sprint 4 **vẫn giữ nguyên hiệu lực**
  vì đường dẫn âm thanh thu/phát không đổi.
- **Khối 2** chỉ còn Fleet OS. `TSK-K2-01→03` đổi từ dịch vụ Gateway sang hoàn
  thiện lớp provider OSS, giữ nguyên mã task để không vỡ truy vết.

#### Cần chú ý — Hệ quả giấy phép

**LiteLLM chuyển từ H.2 (dịch vụ máy chủ, không phân phối) sang H.1 (phân phối
kèm sản phẩm)** trong proposal Phụ lục H. Nghĩa vụ giấy phép đổi theo phạm vi
phân phối, nên **Q-11 phải được xét lại và chốt trước khi bắt đầu `TSK-S2-11`**,
không phải trước Khối 2 như trước đây. Hạn của **Q-10** cũng đẩy từ Tháng 3 lên
Tuần 2 vì cùng lý do.

#### Đã sửa — Lỗi tồn đọng phát hiện khi rà soát

- PRD: `NFR-RES-02/03` vẫn ghi *"Cần chốt — xem §15, Q-3"* trong khi Q-3 đã chốt
  — nay điền số liệu thật.
- PRD: mục lục ghi *"15. Quyết định cần chốt"* lệch với tiêu đề thật
  *"15. Quyết định kỹ thuật đã chốt"*; typo *"Quyước"* ở Phụ lục C; Q-3 dùng cú
  pháp LaTeX lẫn trong Markdown.
- Proposal: rủi ro #4 tham chiếu §8.6 trong khi cột mốc G1–G4 nằm ở §8.7; đoạn
  *"Nền tảng hiện thực"* của §6.1 thiếu dòng trống nên bị nuốt vào bảng.
- Proposal: `Phụ lục D.2` và bảng Voice Pipeline `§3.4` lệch nhau về danh mục
  STT/TTS — nay đồng bộ.

### [0.1.0] — 2026-09-21 — Sprint 1: Đóng băng lược đồ (Khối 1a)

Sprint đầu tiên đóng băng ba lược đồ lõi và hiện thực hóa ngữ nghĩa kế thừa
gate. Mốc này **chưa chạy được tác tử nào**; nó thiết lập các hợp đồng mà
Sprint 2 và 3 sẽ hiện thực. Xem [§3.7](#37-điều-hệ-thống-chưa-làm-được) để
biết chính xác điều gì chưa tồn tại.

**Phạm vi đã đóng:** 12/13 task · 4/6 tiêu chí ra · 2 hạng mục bị chặn ngoài
tầm kỹ thuật (phần cứng và một quyết định quản trị).

#### Đã thêm — Lõi phân giải gate

- **`python/neuroedge/engine/gate_resolver.py`** — làm phẳng chuỗi `extends`
  thành một `ResolvedGate`, cưỡng chế **đủ năm nguyên tắc kế thừa an toàn**
  (Proposal Phụ lục B.5 · FR-GATE-06 → FR-GATE-08):

  | # | Nguyên tắc | Cưỡng chế bởi |
  |:---:|:---|:---|
  | 1 | Gate con kế thừa toàn bộ `evaluate` | `_merge_evaluate()` — và **từ chối** việc định nghĩa lại một tiêu chí đã kế thừa |
  | 2 | Gate con chỉ được siết chặt `allow_when` | `_merge_allow_when()` + `Constraint.is_at_least_as_strict_as()` |
  | 3 | Gate con được bổ sung `evaluate` mới | `_merge_evaluate()` |
  | 4 | `fail: open` không kế thừa | `_resolve_budget()` — chỉ tài liệu của chính cấp đó đặt được `open` |
  | 5 | Tối đa 3 cấp, chặn vòng lặp | `_load_chain()` |

- **`python/neuroedge/engine/constraints.py`** — điểm mấu chốt khiến nguyên tắc 2
  *quyết định được*. Mỗi mệnh đề `allow_when` được chuẩn hóa thành **tập giá trị
  kết quả mà nó chấp nhận**, nên "siết chặt" có nghĩa chính xác: tập con, và sàn
  tin cậy không thấp hơn. Nhờ đó `not_in: [phone]` bị phát hiện là một phép
  *nới lỏng* so với `in: [in_person, app]` dù toán tử khác nhau.
  Chỉ nhận đúng bộ toán tử Phụ lục B.2; toán tử lạ là lỗi, không phải mặc định cho qua.

- **`python/neuroedge/engine/canonical.py`** — chuẩn tắc hóa **RFC 8785 (JCS)**
  và băm SHA-256 trên *gate đã phân giải*. Bảo đảm sửa YAML mang tính hình thức
  (thụt lề, thứ tự khóa, kiểu trích dẫn) không làm đổi mã băm, nên chữ ký gate
  không bị vô hiệu mỗi lần định dạng lại tệp.

- **`python/neuroedge/errors.py`** — phân cấp lỗi **cưỡng chế hợp đồng ba thành
  phần** của FR-DX-04 *bằng cấu trúc*: `NeuroEdgeError(where=, why=, how=)`
  không thể khởi tạo mà thiếu một thành phần. Mã lỗi ổn định để test và viễn trắc
  neo vào: `NE1001` `NE2001` `NE2002` `NE2003` `NE3001` `NE4001`.

- **`python/neuroedge/trace.py`** — thẩm định vết ghi, dùng chung một đường mã
  cho CLI và test. Bật `format_checker`, nên `format: date-time` và `format: uri`
  được kiểm thật.

- **`python/neuroedge/hal/board.py`** + **`boards/`** (3 profile) — mô hình năng
  lực bo mạch cho cả ba target `sim` · `linux` · `esp32s3`.

- **`python/neuroedge/paths.py`** — định vị gốc monorepo (`schemas/`, `gates/`,
  `fixtures/`, `boards/`) từ source checkout, editable install hay wheel; ghi đè
  bằng biến môi trường `NEUROEDGE_ROOT`.

#### Đã thêm — Corpus kiểm chứng

| Đường dẫn | Số tệp | Vai trò |
|:---|:---:|:---|
| `gates/` | 3 | Gate mẫu viết tay, gồm **chuỗi kế thừa 2 cấp** (Tiêu chí ra 2) |
| `fixtures/gates/valid/` | 5 | Hành vi phân giải đúng, đặc biệt nguyên tắc 4 theo cả hai chiều |
| `fixtures/gates/invalid/` | 15 | Phản chứng — mỗi nguyên tắc đều có ca chứng minh bị từ chối |
| `fixtures/gates/registry/` | 6 | Gate cơ sở cho fixture (gồm chuỗi 3 cấp và cặp vòng lặp) |
| `fixtures/traces/invalid/` | 6 | Phản chứng cho `trace.v1.json` |
| `fixtures/gates/expected_errors.yaml` · `fixtures/traces/expected_errors.yaml` | 2 | **Thông báo lỗi kỳ vọng** cho từng phản chứng |

Corpus phản chứng **khép kín hai chiều**: mỗi tệp phải có một mục trong
`expected_errors.yaml`, và mỗi mục phải có một tệp. Không thể thêm fixture mà
không nói nó chứng minh điều gì.

#### Đã thêm — CLI vận hành được

`gate resolve` · `gate lint` · `gate publish` · `gate add` ·
`trace validate` · `trace show` · `board list` · `board show` · `verify` · `replay`

Chi tiết và hợp đồng mã thoát: [§2.3](#23-tham-chiếu-lệnh-cli).

#### Đã thêm — CI, quy trình, tài liệu

- **`.github/workflows/ci-sim-linux.yml`** (TSK-S1-12, FR-CI-05) — 4 job:
  `frozen-artifacts` · `tests` (3 bản Python) · `lint` · `licence-obligations`.
- **`.github/workflows/nightly-hardware.yml`** (TSK-S1-12, FR-CI-06) — 4 job:
  `firmware-build` · `upstream-drift` · `memory-spike` · `report`.
- **`CONTRIBUTING.md`** (TSK-S1-13) — 7 mục, gồm ranh giới chính xác của việc gì
  cần RFC.
- **`docs/rfc/`** (TSK-S1-13) — quy trình, mẫu, và
  [RFC-0001](docs/rfc/0001-gate-schema-conditional-requirements.md).
- **`docs/spec/hal_mcu_review.md`** (TSK-S1-11) — 5 kết luận rà soát + 4 ràng
  buộc chuyển tiếp sang Sprint 4.
- **`docs/reports/memory_spike_report.md`** (TSK-S1-10) — khung báo cáo, **các ô
  số đo để trống** vì chưa chạy trên bo mạch.
- **`scripts/check_firmware_size.py`** — đối chiếu ngân sách flash Q-3, đọc kích
  thước khe A/B từ chính `partitions.csv` thay vì ghim cứng.
- **`python/requirements-lock.txt`** — §3.9 nghĩa vụ 5 (ghim phiên bản).
- **`python/README.md`**, **`CHANGELOG.md`** (tệp này).

#### Đã thêm — Khung đo bộ nhớ trên thiết bị

- **`targets/esp32s3/main/memory_probe.{c,h}`** — 4 checkpoint (`boot`,
  `nvs_ready`, `network_ready`, `audio_ready`), bảng cho người đọc, và **một
  dòng JSON máy đọc được** (`NEUROEDGE_MEMORY_JSON`) để CI thu số đo mà không ai
  phải chép tay. Ngưỡng Q-3 ghim thành hằng số `NEUROEDGE_Q3_*`.
- **`targets/esp32s3/main/main.c`** — khởi tạo NVS và ngăn xếp mạng (đo *sau*
  khi đã trừ phần không thể loại bỏ), rồi báo cáo. Vị trí nạp AEC + VAD + Opus
  đánh dấu `TODO(TSK-S1-10, V2)`.

#### Đã đổi

- **`schemas/gate.v1.json` — sửa theo [RFC-0001](docs/rfc/0001-gate-schema-conditional-requirements.md).**
  Bốn thay đổi, chi tiết lập luận trong RFC:
  1. Trường bắt buộc thành **có điều kiện** theo sự có mặt của `extends`. Gate
     gốc vẫn phải khai báo hợp đồng đầy đủ; gate dẫn xuất được phép kế thừa.
  2. `budget.fail` thành **tùy chọn**, vắng mặt nghĩa là `closed`.
  3. Tham số `on_block` bắt buộc **theo từng hành vi** (`escalate`→`to`,
     `ask`→`message`, `degrade`→`fallback_action`).
  4. Siết chặt: `extends` có `pattern` URI; `level` bắt buộc có `levels`;
     `choice` bắt buộc có `options`; `evaluate` cần ít nhất một tiêu chí.
- **Phụ thuộc chuẩn tắc hóa:** `canonicaljson` → **`rfc8785`**. Phụ lục B.4 nói
  rõ RFC 8785 (JCS); `canonicaljson` là một chuẩn tắc hóa khác (dòng Matrix).
- **`python/pyproject.toml`:** `readme` trỏ tệp ngoài thư mục dự án khiến
  **gói không cài được**; thêm `pyyaml`; thêm cấu hình `ruff`.
- **CLI:** lệnh chưa có engine giờ **thoát mã 2** kèm mã task sẽ hiện thực nó,
  thay vì in bảng kết quả giả. `verify` chỉ báo phần nó thật sự kiểm và nói rõ
  phần nào của tiêu chí A2 chưa được phủ.
- **`NOTICE`:** viết lại thành ma trận giấy phép 4 mục A–D (§3.9 nghĩa vụ 1, 2, 4).
- **Chuẩn hóa mã:** `typing.Dict/Optional` → generic sẵn có; `GateVerdict` →
  `StrEnum`; toàn bộ `python/` sạch `ruff check` và `ruff format`.

#### Đã sửa

- **`pyproject.toml` khiến gói không cài được.** `readme = "../neuroedge-proposal.md"`
  nằm ngoài thư mục dự án; hatchling từ chối. `pip install -e .` thất bại, nên
  CI không thể cài được gói.
- **4 test conformance lược đồ skip trong im lặng.** Chúng dùng
  `pytest.importorskip("jsonschema")`, mà `jsonschema` không được cài, nên tình
  trạng thật là *4 passed, 4 skipped* trong khi bảng tiến độ báo
  "PASS 100% (4/4 tests passed)". Khẳng định về conformance lược đồ đang dựa
  trên những test chưa từng chạy. Đã bỏ `importorskip`, và thêm **cổng CI chặn
  mọi test bị skip**.
- **`format: date-time` và `format: uri` không được kiểm.** JSON Schema coi
  `format` là chú thích trừ khi có format checker. Một vết ghi với
  `timestamp_utc: "21/09/2026 08:00"` vẫn thẩm định đạt — và một vết ghi không
  phân tích được mốc thời gian thì không phát lại được, tức là mất đúng mục đích
  của tệp.
- **`neuroedge verify` in "TARGET EQUIVALENCE VERIFIED — 0 discrepancies" mà
  không kiểm gì.** `neuroedge test` in bảng "3 passed" cố định. Đầu ra CLI bị
  dán vào báo cáo tiến độ như bằng chứng, nên một dòng như vậy là thông tin sai
  cho người ra quyết định phạm vi.
- **Chẩn đoán thiếu ngữ cảnh tệp.** Lỗi toán tử `allow_when` chỉ nêu
  `allow_when.risk_level` mà không nêu tệp nào; vết chuỗi kế thừa in sai thứ tự.
- **Khẳng định nghịch đảo trong CI có thể đạt vì lý do sai.** Bước kiểm
  "corpus phản chứng phải tiếp tục thất bại" viết dạng `if ! <lệnh>`, nên nó coi
  *mọi* mã thoát khác 0 là bằng chứng bị từ chối — kể cả mã 2 (lỗi cú pháp lệnh).
  Mà lệnh khi đó **thật sự sai cú pháp**: `gate lint` chưa có tùy chọn
  `--registry`. Bước kiểm sẽ mãi mãi xanh mà **không bao giờ chạy phép kiểm tra
  nào**, kể cả khi ngữ nghĩa kế thừa hồi quy hoàn toàn. Đã thêm `--registry` cho
  `gate lint`, và bước CI giờ **so khớp chính xác mã thoát 1** ("đã chạy và
  không đạt"), thất bại rõ ràng nếu nhận mã khác. Hai test neo lại lỗ này.

#### An toàn và giấy phép

- **Hai đường lây nhiễm copyleft mạnh vào lõi MIT — cả hai là phụ thuộc bắc cầu,
  không ai chủ ý thêm:**

  | Đường | Giấy phép | Xử lý |
  |:---|:---|:---|
  | `neuroedge` → `copier` → `jinja2-ansible-filters` | **GPL3** | `copier` rời tập phụ thuộc lõi sang extra `scaffold` |
  | `neuroedge` → `jsonschema[format]` → `rfc3987` | **GPL** | Ghim `jsonschema[format-nongpl]`, dùng `rfc3987-syntax` (MIT) |

  Đây đúng là rủi ro §3.10 đã nêu. Điều đáng chú ý: rà soát bằng mắt ở tầng phụ
  thuộc **trực tiếp** sẽ bỏ sót cả hai. Vì vậy job `licence-obligations` chạy
  `pip-licenses --fail-on` trên **toàn bộ cây phụ thuộc** ở mỗi pull request.

- **`allow_when` dạng chuỗi CEL bị từ chối trong chuỗi kế thừa.** Nguyên tắc 2
  yêu cầu *chứng minh* gate con không lỏng hơn gate cha; với hai biểu thức bất
  kỳ, đó là bài toán không quyết định được. Phân giải **fail-closed** thay vì
  xấp xỉ một phép kiểm tra an toàn.

- **Mặc định fail-closed ở mọi hướng:** vắng `fail` → `closed`; gate cha
  `fail: open` mà gate con im lặng → `closed`; chưa lấy checkpoint `audio_ready`
  → `INCONCLUSIVE`, không phải "đạt".

#### Kiểm chứng

```
210 test PASS · 0 SKIP · ruff check sạch · ruff format sạch
```

| Bộ test | Số test | Kiểm điều gì |
|:---|:---:|:---|
| `test_gate_fixtures.py` | 40 | Corpus phản chứng khớp đúng lỗi đã ghi; mọi lỗi đủ 3 thành phần |
| `test_gate_resolver.py` | 35 | Năm nguyên tắc B.5, từng nguyên tắc độc lập, dựng tài liệu trong bộ nhớ |
| `test_cli.py` | 32 | Hành vi CLI, **neo chặt mã thoát** |
| `test_sample_gates.py` | 26 | Ba gate mẫu và chuỗi 2 cấp trên corpus thật |
| `test_boards.py` | 22 | Khai báo bo mạch; **parity giữa `sim` và bo mạch tham chiếu** |
| `test_trace_fixtures.py` | 19 | Vết ghi hợp lệ/không hợp lệ, và **nội dung kịch bản** |
| `test_schemas.py` | 18 | Conformance cấu trúc của ba lược đồ |
| `test_canonical.py` | 14 | Tính tất định của RFC 8785 và mã băm |
| `test_testing.py` | 4 | Action CI `replay()` / `scenario()` (có từ trước) |

---

## 2. Cách vận hành

### 2.1 Dựng môi trường

```bash
cd python
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q          # kỳ vọng: 0 failed, 0 skipped
```

Yêu cầu **Python 3.11+**. Bản dựng tái lập được:

```bash
.venv/bin/python -m pip install -r requirements-lock.txt
```

> **Đừng cài extra `scaffold`** trừ khi bạn thực sự cần `copier`: nó kéo
> `jinja2-ansible-filters` (GPL3) vào môi trường. Xem `NOTICE` mục B.

### 2.2 Kiểm tra nhanh toàn bộ artifact

Chạy từ **gốc kho** (mọi lệnh đều cần thấy `schemas/`, `gates/`, `fixtures/`):

```bash
V=python/.venv/bin

$V/neuroedge verify                      # phân giải mọi gate + thẩm định mọi vết ghi
$V/neuroedge gate lint                   # kỳ vọng: ✓ 3 gate(s) resolved
$V/neuroedge trace validate fixtures/traces/*.json   # kỳ vọng: 3 × VALID
$V/neuroedge board list                  # kỳ vọng: 3 profile
```

Khẳng định nghịch đảo — corpus phản chứng **phải** tiếp tục thất bại:

```bash
$V/neuroedge gate lint fixtures/gates/invalid --registry fixtures/gates/registry
# kỳ vọng: mọi tệp trong invalid/ đều failed to resolve · mã thoát 1
```

Nếu lệnh trên **thành công**, các phép kiểm tra an toàn kế thừa đã hồi quy, và
một pipeline xanh lúc đó là thông tin sai. CI có đúng một bước cho việc này.

### 2.3 Tham chiếu lệnh CLI

**Hợp đồng mã thoát** — CI và Action CI đều neo vào nó:

| Mã | Nghĩa |
|:---:|:---|
| `0` | Phép kiểm tra đã chạy và **đạt** |
| `1` | Phép kiểm tra đã chạy và **không đạt** |
| `2` | Lệnh **chưa được hiện thực** |

Mã `2` tách biệt với `1` là có chủ ý: CI phân biệt được "hỏng" và "chưa có".

#### Lệnh đã hiện thực

| Lệnh | Chức năng |
|:---|:---|
| `gate resolve <tệp\|URI>` | Phân giải chuỗi `extends`, in chính sách hiệu dụng và mã băm. `--json` cho đầu ra máy đọc; `--registry <dir>` đổi nơi tra `neuroedge://` |
| `gate lint [dir]` | Phân giải mọi gate trong thư mục (mặc định `gates/`). `--registry <dir>` đổi nơi tra `neuroedge://`; nếu không truyền, lệnh tự nhận thư mục `registry/` kế bên |
| `gate publish <tệp>` | Biên dịch sang JSON chuẩn tắc RFC 8785, in mã băm SHA-256. `--out` ghi ra tệp |
| `gate add <URI>` | Phân giải một gate từ registry và cho biết việc kế thừa nó sẽ áp đặt gì |
| `trace validate <tệp…>` | Thẩm định theo `trace.v1.json`. Một tệp sai làm cả lệnh thất bại |
| `trace show <tệp>` | In dòng thời gian sự kiện |
| `board list` / `board show <id>` | Liệt kê / xem năng lực bo mạch theo 5 nguyên thủy |
| `verify` | Quét toàn bộ artifact đã đóng băng |
| `build --target <t> --board <id>` | Đối chiếu năng lực agent ↔ bo mạch, phân giải và biên dịch gate. `--agent` (mặc định `agent.toml`), `--out` (mặc định `build/`). Hỏng ⇒ in mọi vấn đề, mã 1, không ghi gì |
| `replay <tệp>` | Đọc và thẩm định vết ghi rồi in dòng thời gian |

> `gate publish` **không ký số**. Nó dừng ở mã băm, vì ký cần khóa của Gate
> Registry (Khối 3). `replay` **không thực thi** vết ghi trên target. Cả hai
> lệnh tự nói rõ điều đó trong đầu ra — đừng đọc chúng như đã làm nhiều hơn.

#### Lệnh chưa hiện thực (thoát mã 2)

| Lệnh | Sẽ có ở |
|:---|:---|
| `run` | TSK-S3-06 — HAL `sim` đã có (TSK-S2-01), còn vòng lặp gõ chữ |
| `test` | TSK-S3-03 — hiện dùng `pytest` trong `python/` |
| `record` | TSK-S3-01 |
| `new` | TSK-S3-07 |

### 2.4 Đọc một thông báo lỗi

Mọi lỗi có đúng ba phần (FR-DX-04): **ở đâu** · **vì sao** · **cách xử lý**.
Lỗi kế thừa có thêm dòng `rule` chỉ ra nguyên tắc B.5 bị vi phạm.

```
[NE2003] loosens-level@1.0.0 (fixtures/gates/invalid/loosens_level.yaml) -> allow_when.risk_level
  why: loosens the inherited condition: base admits {low}, this gate admits {high, low, medium}
  rule: Appendix B.5 principle 2
  fix: narrow allow_when.risk_level to a subset of the base condition (base clause: {'lte': 'low'}), …
```

| Mã | Lớp lỗi | Nghĩa |
|:---:|:---|:---|
| `NE1001` | `ActionContractViolation` | Lệnh actuator không mang chữ ký gate |
| `NE2001` | `GateNotFoundError` | Không tìm thấy gate theo URI hoặc đường dẫn |
| `NE2002` | `GateSchemaError` | Vi phạm `gate.v1.json` hoặc bộ toán tử Phụ lục B.2 |
| `NE2003` | `GateInheritanceError` | Vi phạm một trong năm nguyên tắc B.5 |
| `NE3001` | `BoardCapabilityError` | Khai báo bo mạch sai, hoặc thiếu năng lực được yêu cầu |
| `NE4001` | `TraceValidationError` | Vi phạm `trace.v1.json` |

### 2.5 CI

| Workflow | Khi nào | Job |
|:---|:---|:---|
| `ci-sim-linux.yml` | Mỗi PR và push | `frozen-artifacts` · `tests` (Python 3.11/3.12/3.13) · `lint` · `licence-obligations` |
| `nightly-hardware.yml` | 01:00 UTC+7 hằng đêm | `firmware-build` · `upstream-drift` · `memory-spike` · `report` |

`ci-sim-linux.yml` phải xanh trước khi hợp nhất. Ba cổng đáng chú ý:

- **Cổng chặn test skip** — đọc `junit.xml`, thất bại nếu có bất kỳ test nào
  skip. Lý do ở [§1 mục Đã sửa](#đã-sửa).
- **Khẳng định nghịch đảo** — corpus phản chứng phải tiếp tục thất bại.
- **Cổng giấy phép** — `pip-licenses --fail-on` trên toàn bộ cây phụ thuộc.

Job `memory-spike` cần runner tự quản gắn nhãn `esp32s3-box-3`. Khi chưa có,
nó **bị bỏ qua và nói rõ là bỏ qua** trong phần summary, không bao giờ báo đạt.

### 2.6 Firmware (khi đã có bo mạch)

```bash
cd targets/esp32s3
idf.py set-target esp32s3
idf.py build
python ../../scripts/check_firmware_size.py build/*.bin   # ngân sách flash Q-3
idf.py -p /dev/ttyUSB0 flash monitor
```

Tìm dòng `NEUROEDGE_MEMORY_JSON` trong đầu ra monitor — đó là số đo. Điền vào
[`docs/reports/memory_spike_report.md`](docs/reports/memory_spike_report.md).

---

## 3. Bàn giao ngữ cảnh sản phẩm

Mục này dành cho người (hoặc phiên làm việc) tiếp quản. Đọc hết mục này là đủ
để build tiếp mà không phải đọc lại ba tài liệu gốc.

### 3.1 Các tài liệu là nguồn sự thật

| Tệp | Vai trò | Khi nào đọc |
|:---|:---|:---|
| [`neuroedge-roadmap.md`](neuroedge-roadmap.md) | **Tiến độ, task, tiêu chí ra, quyết định.** §0 là bảng điều khiển | **Luôn đọc trước** |
| [`neuroedge-prd.md`](neuroedge-prd.md) | Yêu cầu chức năng `FR-*` / `NFR-*` | Khi cần biết *phải* làm gì |
| [`neuroedge-proposal.md`](neuroedge-proposal.md) | Kiến trúc và các Phụ lục. **Phụ lục B là đặc tả gate** | Khi cần biết *tại sao* |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Quy ước, và việc gì cần RFC | Trước khi sửa `schemas/` |
| [`docs/designs/giai-doan-1-wedge-truoc-mcu-sau.md`](docs/designs/giai-doan-1-wedge-truoc-mcu-sau.md) | Kế hoạch Giai đoạn 1 đã duyệt (biên bản review: `docs/archive/`) | Khi cần biết *vì sao* một task bị cắt/hoãn |
| [`TODOS.md`](TODOS.md) | Việc hoãn có chủ ý, mỗi mục kèm mốc kích hoạt | Trước khi đề xuất việc "còn thiếu" |

**Sổ quyết định duy nhất** là `neuroedge-prd.md` §15 (Q-1 → Q-20).

**Thứ tự ưu tiên khi lệch nhau:** PRD/Proposal (hợp đồng) → roadmap (tiến độ) →
mã nguồn → tệp này. Nếu mã lệch hợp đồng, mã sai.

### 3.2 Bản đồ kiến trúc — cái gì ở đâu

```
neuroedge-init/
├── schemas/              ⚠️  ĐÃ ĐÓNG BĂNG — sửa phải có RFC
│   ├── gate.v1.json          Hợp đồng gate (Phụ lục B)
│   ├── trace.v1.json         Hợp đồng vết ghi (Phụ lục C)
│   └── board.v1.json         Hợp đồng năng lực bo mạch
├── gates/                3 gate mẫu, gồm chuỗi kế thừa 2 cấp
├── boards/               3 profile: sim-default · esp32s3-box-3 · linux-rpi5
├── fixtures/
│   ├── traces/           ⚠️  3 vết ghi chuẩn mực — sửa phải có RFC
│   │   ├── invalid/          6 phản chứng
│   │   └── expected_errors.yaml
│   ├── gates/            valid/ · invalid/ · registry/
│   │   └── expected_errors.yaml
│   ├── decision_trees/   Bảng sự thật cho walker C — sinh bằng scripts/generate_truth_tables.py
│   └── agents/villa-concierge/   Agent mẫu: agent.toml · actions/ · commands.toml
├── python/neuroedge/
│   ├── engine/           L3 — phân giải gate · cây quyết định · Gate Engine (gate.py)
│   │                         · mạch ngắt · trình biên dịch build (compiler.py) · EventLog
│   ├── actions/          L3 — @action · c.do()/c.say() · token phán quyết dùng một lần
│   ├── models/           L2 — SystemOne/SystemTwo · ngữ pháp lệnh cố định · double
│   ├── hal/              L1 — 5 nguyên thủy, mô hình bo mạch, sim.py, digital.out()
│   ├── perception/       L2 — khung, chưa hiện thực
│   ├── sim/              L0 — web simulator, khung, chưa hiện thực (TSK-S2-09)
│   ├── testing/          Action CI — replay(), scenario()
│   ├── cli/              CLI Typer
│   ├── errors.py         Hợp đồng lỗi 3 thành phần
│   ├── trace.py          Thẩm định vết ghi
│   └── paths.py          Định vị gốc monorepo
├── targets/esp32s3/      Firmware ESP-IDF + khung đo bộ nhớ
├── docs/rfc/ spec/ reports/
├── scripts/              Công cụ CI
└── .github/workflows/    2 pipeline
```

### 3.3 Mười điều bất biến — đừng phá

Đây là các mệnh đề mà phần còn lại của hệ thống dựa vào. Vi phạm một trong số
này sẽ làm hỏng những thứ trông không liên quan.

1. **Thẩm định lược đồ KHÔNG đủ để kết luận một gate an toàn.** Nguyên tắc 2 là
   mệnh đề về **hai** tài liệu; JSON Schema thẩm định **một**. Cổng kiểm tra là
   `neuroedge gate lint` (phân giải), không phải thẩm định lược đồ.
2. **Fail-closed là mặc định ở mọi hướng.** Vắng `fail` → `closed`. Gate cha
   `fail: open` + gate con im lặng → `closed`. Không đo được → `INCONCLUSIVE`.
3. **`allow_when` dạng chuỗi CEL không được xuất hiện trong chuỗi kế thừa.**
   Không chứng minh được phép siết chặt → từ chối.
4. **Phân giải gate là hàm thuần khiết** — không đồng hồ, không mạng, không ngẫu
   nhiên. Đó là điều cho phép `neuroedge verify` chứng minh cùng một chuỗi phân
   giải như nhau trên cả ba target.
5. **Không có bộ lượng giá CEL nào trên vi điều khiển** (Q-9 phương án A). Máy
   tính biên dịch sang cây quyết định phẳng; firmware chỉ duyệt cây.
6. **Bo mạch tham chiếu duy nhất là ESP32-S3-BOX-3.** Không đổi sang DevKitC —
   số đo spike sẽ vô nghĩa.
7. **`sim` không được giàu năng lực hơn bo mạch tham chiếu.** Nếu giàu hơn, lời
   hứa "TTFV dưới 10 phút" thành cái bẫy: rút ngắn 10 phút đầu, thêm hai ngày gỡ lỗi.
8. **Đuôi vết ghi là `.json` mang `$schema`.** Không đổi sang `.ntrace`.
9. **Không copyleft mạnh trong phần phân phối.** Ghim
   `jsonschema[format-nongpl]`; giữ `copier` ở extra `scaffold`.
10. **Lệnh CLI chưa có engine phải thoát mã 2, không in "PASS" giả.** Đầu ra CLI
    bị dán vào báo cáo như bằng chứng.

### 3.4 Hai hạng mục bị chặn — không đóng được bằng nỗ lực kỹ thuật

| Hạng mục | Chặn bởi | Cần ai | Mở ra điều gì |
|:---|:---|:---|:---|
| **TSK-S1-10** · Tiêu chí ra 3 | **Bo mạch ESP32-S3-BOX-3 vật lý** | Đặt hàng | Kết luận phạm vi Khối 1b (TSK-S2-10) |
| **Tiêu chí ra 6** · Q-11 | ~~Quyết định quản trị~~ — **phần LiteLLM đã duyệt 2026-09-23**; Hawkbit/EMQX còn mở, hạn trước Khối 2 | Kỹ thuật trưởng | Bắt đầu port mã Khối 2 |

**TSK-S1-10 — việc còn lại sau khi có bo mạch:** vendoring `esp-sr` (AEC/AFE +
VAD) và `opus` kèm rà soát giấy phép §3.9, nạp chúng tại `TODO(TSK-S1-10, V2)`
trong `main.c`, gọi checkpoint `audio_ready`, điền báo cáo. Quy tắc quyết định
đã chốt **trước khi đo** để kết quả không bị giải thích lại: trượt bất kỳ một
ngưỡng Q-3 → kích hoạt **bậc 5 thang cắt phạm vi (§9) ngay**, không chờ Tuần 9.

**Q-11 — chính sách phụ thuộc bắc cầu đã chốt (2026-09-23):** cho phép MIT,
BSD, Apache-2.0, ISC, PSF, MPL-2.0 (dùng nguyên bản); cấm GPL/LGPL/AGPL, SSPL, BSL,
thương mại hoặc không rõ. `litellm==1.102.0` đã kiểm: 55 phụ thuộc bắc cầu đều
trong allowlist, wheel không chứa `enterprise/`. Cưỡng chế bằng bước kiểm giấy
phép trong CI, làm cùng `TSK-S2-11`. Hai phát hiện GPL trong Sprint 1 đều đến qua
bắc cầu — đó là lý do phải có bước này.

### 3.5 Việc tiếp theo

Xem **Thẻ bàn giao** ở `neuroedge-roadmap.md` §0.3 — nơi duy nhất ghi việc tiếp
theo và thứ tự làm (`CONTRIBUTING.md` §8.1). Lý do một task bị hoãn nằm ở dòng của
nó trong bảng task.

### 3.6 Nợ thiết kế đã biết

| # | Nợ | Phải giải quyết ở |
|:---:|:---|:---|
| 1 | **Hủy lệnh đang chờ mới có ở `sim`.** Hợp đồng thu hồi lệnh vật lý (§3.8) yêu cầu `barge_in` hủy xung chốt cửa đang chờ trong ≤ 1 khung âm thanh. `SimHAL.digital_out()` đã trả `PendingCommand.cancel()` (TSK-S2-01); `esp32s3` phải hủy được thật ở tầng firmware | **TSK-S4-01**, cùng lúc với hợp đồng thu hồi — không phải sau |
| 2 | `ReplaySession._parse_events()` suy luận `blocked_by` theo lối tạm, ghim cứng tên hành động `unlock_door` | TSK-S3-02 / TSK-S3-03 |
| 3 | `gate publish` dừng ở mã băm, chưa ký số | Khối 3 (Gate Registry) |
| 4 | `perception/` và `sim/` chỉ là khung | TSK-S3-11 / TSK-S2-09 |

### 3.7 Điều hệ thống chưa làm được

Nói rõ để không ai đọc các mốc đã đạt quá lên:

- ❌ **Chưa có `neuroedge run`.** Agent chạy được trên `sim` qua `Conversation` (test), nhưng
  vòng lặp gõ chữ trên CLI là TSK-S3-06.
- ❌ **Chưa có nhà cung cấp cloud thật.** SystemOne/SystemTwo chạy với double và ngữ pháp lệnh
  cục bộ; connector LiteLLM là TSK-S2-11 (A2).
- ❌ **Chưa có tương đương target.** `verify` kiểm ở mức lược đồ. Phát lại trên
  target thật và so khớp chuỗi phán quyết là TSK-S3-02 / TSK-S4-03.
- ❌ **Chưa ghi vết ghi ra tệp.** `EventLog` giữ trong bộ nhớ; bộ ghi tệp là TSK-S3-01.
- ❌ **Chưa có CEL.** `allow_when` chỉ nhận dạng mapping toán tử.
- ❌ **Chưa có số đo bộ nhớ.** Xem §3.4.

### 3.8 Bốn ràng buộc chuyển cho Sprint 4 (từ rà soát HAL)

Ghi lại ở đây để Sprint 4 không phải suy luận lại. Đầy đủ tại
[`docs/spec/hal_mcu_review.md`](docs/spec/hal_mcu_review.md) §2.

| # | Ràng buộc | Lý do |
|:---:|:---|:---|
| RB-1 | Không `malloc` trong đường dẫn âm thanh sau khởi tạo | Phân mảnh heap gây rớt khung; Tiêu chí 4 Sprint 5 đo bộ nhớ sau 4 giờ chạy |
| RB-2 | Đệm âm thanh cấp phát tĩnh trong PSRAM, đặt tên và **đo được** | Q-3 dành ≥ 2 MB PSRAM; không đo được thì không đối chiếu được |
| RB-3 | `digital.out` hủy được lệnh đang chờ trong ≤ 1 khung âm thanh | Hợp đồng thu hồi lệnh vật lý — xem nợ thiết kế #1 |
| RB-4 | Bảng năng lực là `const` trong flash | Tiết kiệm SRAM, và loại bỏ đường tắt vòng qua gate (A3) |

*Cập nhật CR-1.0:* cả bốn ràng buộc **vẫn giữ nguyên hiệu lực** sau khi chuyển sang cloud-first. Đường dẫn âm thanh thu/phát trên thiết bị không đổi; chỉ phần STT/TTS rời khỏi vi điều khiển, nên áp lực bộ nhớ giảm chứ ràng buộc không mất.

### 3.9 Thêm một fixture phản chứng

Việc thường gặp nhất khi build tiếp, nên ghi rõ quy trình:

1. Thêm tệp vào `fixtures/gates/invalid/` (hoặc `fixtures/traces/invalid/`).
2. Thêm mục tương ứng vào `expected_errors.yaml` cùng cấp:

   ```yaml
   ten_fixture.yaml:
     error: GateInheritanceError    # lớp lỗi
     code: NE2003                   # mã ổn định
     principle: 2                   # nguyên tắc B.5 bị vi phạm
     where_contains: "allow_when.risk_level"
     why_contains: "loosens the inherited condition"
   ```

3. Chạy `pytest -q`. Test cưỡng chế corpus khép kín **hai chiều**, nên thiếu một
   trong hai bước sẽ đỏ.

`where_contains` và `why_contains` là so khớp chuỗi con, nên có thể cải thiện
cách diễn đạt lỗi mà không phải sửa tệp này — nhưng **lớp lỗi, mã ổn định và
nguyên tắc B.5 thì không được trôi trong im lặng**.

---

[0.1.0]: https://github.com/letrongminh/neuroedge-init/releases/tag/v0.1.0
