# CLAUDE.md — NeuroEdge

Hướng dẫn cho coding agent làm việc trên kho này.

Nguồn sự thật, theo thứ tự ưu tiên khi hai tài liệu lệch nhau:

| Tệp | Vai trò |
|:---|:---|
| [`neuroedge-prd.md`](neuroedge-prd.md) | Yêu cầu `FR-*` / `NFR-*`. **Sổ quyết định là §15** (Q-1 → Q-13) |
| [`neuroedge-proposal.md`](neuroedge-proposal.md) | Kiến trúc và các Phụ lục. **Phụ lục B là đặc tả gate** |
| [`neuroedge-roadmap.md`](neuroedge-roadmap.md) | Tiến độ Giai đoạn 1. **§0 là bảng điều khiển** |
| [`neuroedge-roadmap-phase2.md`](neuroedge-roadmap-phase2.md) | Giai đoạn 2 (Tháng 9–24) |
| [`CHANGELOG.md`](CHANGELOG.md) | Đã xây gì, chạy thế nào, bàn giao ngữ cảnh |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Quy ước, và việc gì cần RFC |

Việc **đã xem xét và hoãn có chủ ý** nằm ở [`TODOS.md`](TODOS.md) — mỗi mục phải
kèm một mốc kích hoạt. Kế hoạch Giai đoạn 1 và các báo cáo review của nó ở
[`docs/designs/`](docs/designs/).

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
cd python && .venv/bin/python -m pytest -q      # kỳ vọng: 210 passed, 0 skipped
```

Framework: **pytest**. `testpaths = ["tests"]` trong `python/pyproject.toml`.

Hai luật không thương lượng:

- **Không test nào được skip.** CI đọc `junit.xml` và fail build nếu có bất kỳ
  skip nào. Không dùng `pytest.importorskip` cho phụ thuộc đã khai trong
  `pyproject.toml` — phụ thuộc cần cho conformance là phụ thuộc bắt buộc.
- **Corpus phản chứng khép kín hai chiều.** Mỗi tệp trong `fixtures/*/invalid/`
  phải có một mục trong `expected_errors.yaml`, và ngược lại.

Cổng kiểm tra an toàn **không phải** thẩm định lược đồ mà là
`neuroedge gate lint` (phân giải). Xem lý do ở đầu tệp này.

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
