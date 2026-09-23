# CLAUDE.md — NeuroEdge

Hướng dẫn cho coding agent làm việc trên kho này.

Nguồn sự thật, theo thứ tự ưu tiên khi hai tài liệu lệch nhau:

| Tệp | Vai trò |
|:---|:---|
| [`neuroedge-prd.md`](neuroedge-prd.md) | Yêu cầu `FR-*` / `NFR-*`. **Sổ quyết định là §15** (mã `Q-N`) |
| [`neuroedge-proposal.md`](neuroedge-proposal.md) | Kiến trúc và các Phụ lục. **Phụ lục B là đặc tả gate** |
| [`neuroedge-roadmap.md`](neuroedge-roadmap.md) | Tiến độ Giai đoạn 1. **§0 là bảng điều khiển** |
| [`neuroedge-roadmap-phase2.md`](neuroedge-roadmap-phase2.md) | Giai đoạn 2 (Tháng 9–24) |
| [`CHANGELOG.md`](CHANGELOG.md) | Đã xây gì, chạy thế nào, bàn giao ngữ cảnh |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Quy ước, và việc gì cần RFC |

Việc **đã xem xét và hoãn có chủ ý** nằm ở [`TODOS.md`](TODOS.md) — mỗi mục phải
kèm một mốc kích hoạt. Kế hoạch Giai đoạn 1 ở [`docs/designs/`](docs/designs/); biên
bản các vòng review ở [`docs/archive/`](docs/archive/). Giải mã mọi mã viết tắt
(`FR-*`, `Q-N`, `A1`, `CEO-X1`…): [`docs/user/thuat-ngu.md`](docs/user/thuat-ngu.md).

Hai điều dễ sai nhất:

- **`schemas/` đã đóng băng.** Sửa ba lược đồ, sửa ngữ nghĩa phân giải gate, hoặc
  sửa ba vết ghi chuẩn mực ở `fixtures/traces/` đều **bắt buộc có RFC**
  (`docs/rfc/`).
- **Thẩm định lược đồ không đủ để kết luận một gate an toàn.** Nguyên tắc kế thừa
  số 2 là mệnh đề về *hai* tài liệu; JSON Schema thẩm định *một*. Cổng kiểm tra là
  `neuroedge gate lint` (phân giải), không phải thẩm định lược đồ.

Đọc `CHANGELOG.md` §3 (bàn giao ngữ cảnh) trước khi bắt đầu một phiên mới.

## Testing

```bash
cd python && .venv/bin/python -m pytest -q      # kỳ vọng: 0 failed, 0 skipped
```

Framework: **pytest**. `testpaths = ["tests"]` trong `python/pyproject.toml`.
`python/tests_linux/` chạy riêng, chỉ trên máy có gpio-sim (`scripts/setup_gpio_sim.sh`,
job CI `linux-hal`) — nó không nằm trong `testpaths` để bộ chính không phải skip.
Bản đã cài (wheel, không phải editable) được kiểm bằng `scripts/wheel_smoke.sh` — chạy nó
khi đụng tới `paths.py`, `hatch_build.py` hay đường dẫn tới `schemas/`, `boards/`, `gates/`.

Hai luật không thương lượng:

- **Không test nào được skip.** CI đọc `junit.xml` và fail build nếu có bất kỳ
  skip nào. Không dùng `pytest.importorskip` cho phụ thuộc đã khai trong
  `pyproject.toml` — phụ thuộc cần cho conformance là phụ thuộc bắt buộc.
- **Corpus phản chứng khép kín hai chiều.** Mỗi tệp trong `fixtures/*/invalid/`
  phải có một mục trong `expected_errors.yaml`, và ngược lại.

Cổng kiểm tra an toàn **không phải** thẩm định lược đồ mà là
`neuroedge gate lint` (phân giải). Xem lý do ở đầu tệp này.

Số test hiện hành ở `neuroedge-roadmap.md` §0.1, không ghi ở đây.

## Khi xong một task

Làm theo **`CONTRIBUTING.md` §8**, trong cùng PR với mã: tiến độ ở roadmap, một mục
trong `CHANGELOG.md` `[Chưa phát hành]`, đặc tả nếu hành vi đổi. Mỗi sự thật có
đúng một nơi (§8.1) — nơi khác dẫn mã, không chép lại. Chạy `ruff check .` và
`ruff format --check .` trước khi commit; CI chặn cả hai.

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
- Author a backlog-ready spec/issue → invoke /spec
