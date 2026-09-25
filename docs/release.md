# Phát hành `neuroedge`

**Chính sách (Q-39):** mỗi increment kết thúc bằng một tag; tag của từng increment ở
`neuroedge-roadmap.md` §0.2. **Trước I6, mọi tag là nội bộ** — không đẩy lên index nào.
Lần phát hành ra ngoài đầu tiên là **I6 — Công khai**, lên PyPI; các bước dưới dùng số của
nó (`0.6.0`).

Workflow là [`.github/workflows/release-pypi.yml`](../.github/workflows/release-pypi.yml)
(`TSK-S3-14`). Nó có bốn job:

| Job | Chạy khi | Làm gì |
|:---|:---|:---|
| `build` | mọi lần chạy | sdist, rồi wheel build **từ** sdist; `twine check --strict` (README render được trên PyPI); với tag, kiểm tag bằng `v` + `version` trong `python/pyproject.toml` |
| `smoke` | mọi lần chạy | runner sạch tải đúng wheel vừa build, chạy `scripts/wheel_smoke.sh --wheel` trên Python 3.11 và 3.13 |
| `publish-testpypi` | tag pre-release (`v0.6.0rc1`, `v0.7.0b1`…) **và** `PUBLISH_ENABLED == 'true'` | đẩy lên test.pypi.org |
| `publish-pypi` | tag bản chính (`v0.6.0`) **và** `PUBLISH_ENABLED == 'true'` | đẩy lên pypi.org |

Đẩy lên index dùng trusted publishing (OIDC): kho không giữ token PyPI nào. Khi chưa
đặt biến `PUBLISH_ENABLED`, dù có ai đẩy tag thì hai job `publish-*` cũng bị bỏ qua.
Pull request đổi tệp đóng gói chạy `build` và `smoke`, không bao giờ tới `publish-*`.
**Giữ `PUBLISH_ENABLED` chưa đặt cho tới I6.**

## Tag nội bộ (I1–I5)

Ví dụ dưới là I1 (`v0.1.0`). Kho còn riêng tư, nên wheel chỉ tới người trong tổ chức hoặc
người đo được đội đưa tận tay (I1: buổi đo TTFV tại chỗ, `TSK-I1-02`).

- **PR phiên bản.** Đổi `version` trong `python/pyproject.toml` (I1: `0.1.0`); đổi tiêu đề
  `### [Chưa phát hành]` trong `CHANGELOG.md` §1 thành `### [0.1.0] — YYYY-MM-DD — nội bộ`, thêm
  một `### [Chưa phát hành]` rỗng phía trên. Không thêm link phiên bản cuối tệp — repo còn
  riêng tư. CI xanh, merge.
- **Tag.** `git tag v0.1.0 && git push origin v0.1.0`. `PUBLISH_ENABLED` chưa đặt nên chỉ
  `build` và `smoke` chạy; hai job `publish-*` bị bỏ qua.
- **GitHub Release nội bộ** kèm đúng wheel mà `smoke` đã kiểm:

  ```bash
  gh run download <run-id> --name dist --dir dist   # run của tag v0.1.0
  gh release create v0.1.0 dist/* --title "v0.1.0 — nội bộ (I1)" \
      --notes "Preview nội bộ, chưa phát hành ra ngoài. Thay đổi: CHANGELOG.md [0.1.0]."
  ```

- **Nghiệm thu.** Job `smoke` của run tag xanh là bằng chứng `wheel_smoke.sh --wheel` chạy
  trên đúng wheel đó (I1 tiêu chí 5). Cập nhật roadmap theo `CONTRIBUTING.md` §8.

## Các bước go-live — ở I6 (làm một lần)

Làm theo đúng thứ tự, khi I6 mở. Bước 1–4 là cấu hình; chưa bước nào phát hành gì.

1. **Repo đã công khai** từ 2026-09-25 — toàn bộ kho (Q-45, `TSK-I6-01` ✅). Trước khi phát hành,
   gitleaks quét toàn lịch sử phải sạch (`TSK-W0-03`, I6 tiêu chí 1). Trang PyPI dẫn người đọc về các link
   `https://github.com/letrongminh/neuroedge-init/...` trong `README.md`; repo private thì
   mọi link đó trả 404.
2. **Tạo pending trusted publisher** trên cả hai index. Vào
   <https://test.pypi.org/manage/account/publishing/> rồi
   <https://pypi.org/manage/account/publishing/>, mục *Add a new pending publisher* → GitHub:

   | Trường | test.pypi.org | pypi.org |
   |:---|:---|:---|
   | PyPI Project Name | `neuroedge` | `neuroedge` |
   | Owner | `letrongminh` | `letrongminh` |
   | Repository name | `neuroedge-init` | `neuroedge-init` |
   | Workflow name | `release-pypi.yml` | `release-pypi.yml` |
   | Environment name | `testpypi` | `pypi` |

   Pending publisher **không giữ chỗ** tên: tên chỉ thuộc về bạn sau lần đẩy đầu tiên.
3. **Tạo hai environment** trong GitHub → Settings → Environments: `testpypi` và `pypi`
   (tên phải trùng bảng trên). Nên đặt cho `pypi` *Required reviewers* là chính bạn, và
   *Deployment branches and tags* chỉ cho tag `v*`: bản chính chỉ lên PyPI khi bạn bấm duyệt.
4. **Bật công tắc:** Settings → Secrets and variables → Actions → *Variables* →
   `PUBLISH_ENABLED` = `true` (hoặc `gh variable set PUBLISH_ENABLED --body true`).

## Mỗi lần phát hành lên PyPI (từ I6)

5. **Tập trên TestPyPI trước.** Mở PR đổi `version` trong `python/pyproject.toml` thành
   `0.6.0rc1`, chờ CI xanh, merge. Bản pre-release không đổi `CHANGELOG.md`. Rồi:

   ```bash
   git switch main && git pull
   git tag v0.6.0rc1 && git push origin v0.6.0rc1
   ```

   Chờ `build` → `smoke` → `publish-testpypi` xanh. Kiểm trên một máy (hoặc venv) sạch,
   ngoài mọi checkout — phụ thuộc lấy từ PyPI thật vì TestPyPI không có đủ:

   ```bash
   pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ \
       'neuroedge[mcp]==0.6.0rc1'
   neuroedge gate lint && neuroedge new my-home --template home-voice
   ```

6. **Bản chính.** Một PR đổi `version` thành `0.6.0` **và** đổi tiêu đề
   `### [Chưa phát hành]` trong `CHANGELOG.md` §1 thành `### [0.6.0] — YYYY-MM-DD`, thêm một
   `### [Chưa phát hành]` rỗng phía trên, và link cuối tệp
   `[0.6.0]: https://github.com/letrongminh/neuroedge-init/releases/tag/v0.6.0` (theo repo công
   khai ở bước 1). Merge, rồi `git tag v0.6.0 && git push origin v0.6.0`. Duyệt environment
   `pypi` khi GitHub hỏi. Nghiệm thu `TSK-S3-14`: `pip install 'neuroedge[mcp]==0.6.0'` trong
   venv sạch, rồi `neuroedge gate lint` và `neuroedge trace validate` chạy xanh từ bản cài.
7. **Sau khi phát hành:** cập nhật `TSK-S3-14` và I6 tiêu chí 3 trong `neuroedge-roadmap.md`
   theo `CONTRIBUTING.md` §8. A1 đo đầy đủ từ bản PyPI ở I7 (`TSK-I7-02`).

## Khi có sự cố

- **Tag lệch `version`:** job `build` dừng với lỗi nêu cả hai giá trị; chưa có gì được
  đẩy. Xoá tag (`git push origin :refs/tags/vX`), sửa `version` qua PR, gắn lại tag.
- **Một phiên bản đã lên index thì không thay được.** PyPI không cho đẩy lại cùng số
  phiên bản, kể cả sau khi xoá. Sửa lỗi bằng số mới (`0.6.0rc2`, `0.6.1`).
- **Tắt phát hành ngay:** đặt `PUBLISH_ENABLED` khác `true` (hoặc xoá biến). Hai job
  `publish-*` bị bỏ qua từ lần chạy kế tiếp.
