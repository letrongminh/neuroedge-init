# CLAUDE.md — NeuroEdge

Hướng dẫn cho coding agent làm việc trên kho này.

**Đọc `CHANGELOG.md` §3 (bàn giao ngữ cảnh) trước khi bắt đầu một phiên mới.** Nguồn
sự thật và thứ tự ưu tiên khi lệch nhau: §3.1 của tệp đó. Tiến độ: `neuroedge-roadmap.md`
§0. Quyết định: `neuroedge-prd.md` §15 (`Q-N`). Việc hoãn có chủ ý: `TODOS.md`. Giải mã
mọi ký hiệu (`FR-*`, `Q-N`, `A1`, `CEO-X1`…): `docs/user/thuat-ngu.md`. Cấu trúc kho:
`CONTRIBUTING.md` §6.

Hai điều dễ sai nhất:

- **Một số thay đổi bắt buộc có RFC** — `schemas/`, ngữ nghĩa phân giải gate, ba vết
  ghi chuẩn mực, gate đã khoá trong `digests.lock`, bố cục `NETR`. Danh sách đầy đủ, duy
  nhất: `CONTRIBUTING.md` §3.
- **Thẩm định lược đồ không đủ để kết luận một gate an toàn.** Cổng kiểm tra là
  `neuroedge gate lint` (phân giải) — bất biến `CHANGELOG.md` §3.3 #1.

## Testing

```bash
cd python && .venv/bin/python -m pytest -q      # kỳ vọng: 0 failed, 0 skipped
```

Framework: **pytest**. `testpaths = ["tests"]` trong `python/pyproject.toml`;
`python/tests_linux/` chạy riêng trên gpio-sim (job `linux-hal`). Bản đã cài (wheel, không
phải editable) được kiểm bằng `scripts/wheel_smoke.sh` — chạy nó khi đụng tới `paths.py`,
`hatch_build.py`, `README.md` hay đường dẫn tới `schemas/`, `boards/`, `gates/`.

Hai luật không thương lượng, chi tiết ở `CONTRIBUTING.md`:

- **Không test nào được skip** (§5). CI fail build nếu có bất kỳ skip nào.
- **Mọi corpus khép kín hai chiều** (§3): mỗi tệp một mục đáp án, mỗi mục một tệp —
  `expected_errors.yaml` cho gate và vết ghi, `expected_results.yaml` cho tool call.

Số test hiện hành ở `neuroedge-roadmap.md` §0.1, không ghi ở đây.

## Khi xong một task

Làm theo **`CONTRIBUTING.md` §8**, trong cùng PR với mã: tiến độ ở roadmap, một mục
trong `CHANGELOG.md` `[Chưa phát hành]`, đặc tả nếu hành vi đổi. Mỗi sự thật có
đúng một nơi (§8.1) — nơi khác dẫn mã, không chép lại. Chạy `ruff check .` và
`ruff format --check .` (trong `python/`) trước khi commit; CI chặn cả hai.

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
