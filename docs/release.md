# Phát hành `neuroedge` lên PyPI

Workflow là [`.github/workflows/release-pypi.yml`](../.github/workflows/release-pypi.yml)
(`TSK-S3-14`). Nó có bốn job:

| Job | Chạy khi | Làm gì |
|:---|:---|:---|
| `build` | mọi lần chạy | sdist, rồi wheel build **từ** sdist; `twine check --strict` (README render được trên PyPI); với tag, kiểm tag bằng `v` + `version` trong `python/pyproject.toml` |
| `smoke` | mọi lần chạy | runner sạch tải đúng wheel vừa build, chạy `scripts/wheel_smoke.sh --wheel` trên Python 3.11 và 3.13 |
| `publish-testpypi` | tag pre-release (`v0.1.0rc1`, `v0.2.0b1`…) **và** `PUBLISH_ENABLED == 'true'` | đẩy lên test.pypi.org |
| `publish-pypi` | tag bản chính (`v0.1.0`) **và** `PUBLISH_ENABLED == 'true'` | đẩy lên pypi.org |

Đẩy lên index dùng trusted publishing (OIDC): kho không giữ token PyPI nào. Khi chưa
đặt biến `PUBLISH_ENABLED`, dù có ai đẩy tag thì hai job `publish-*` cũng bị bỏ qua.
Pull request đổi tệp đóng gói chạy `build` và `smoke`, không bao giờ tới `publish-*`.

## Các bước go-live (làm một lần)

Làm theo đúng thứ tự. Bước 1–4 là cấu hình; chưa bước nào phát hành gì.

1. **Chuyển repo sang public.** GitHub → Settings → General → Danger Zone → *Change
   visibility*. Trang PyPI dẫn người đọc về các link `https://github.com/letrongminh/neuroedge-init/...`
   trong `README.md`; repo private thì mọi link đó trả 404.
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

## Mỗi lần phát hành

5. **Tập trên TestPyPI trước.** Mở PR đổi `version` trong `python/pyproject.toml` thành
   `0.1.0rc1`, chờ CI xanh, merge. Rồi:

   ```bash
   git switch main && git pull
   git tag v0.1.0rc1 && git push origin v0.1.0rc1
   ```

   Chờ `build` → `smoke` → `publish-testpypi` xanh. Kiểm trên một máy (hoặc venv) sạch,
   ngoài mọi checkout — phụ thuộc lấy từ PyPI thật vì TestPyPI không có đủ:

   ```bash
   pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ \
       'neuroedge[mcp]==0.1.0rc1'
   neuroedge gate lint && neuroedge new my-home --template home-voice
   ```

6. **Bản chính.** PR đổi `version` thành `0.1.0`, merge, rồi
   `git tag v0.1.0 && git push origin v0.1.0`. Duyệt environment `pypi` khi GitHub hỏi.
   Nghiệm thu `TSK-S3-14`: `pip install 'neuroedge[mcp]==0.1.0'` trong venv sạch, rồi
   `neuroedge gate lint` và `neuroedge trace validate` chạy xanh từ bản cài.
7. **Sau khi phát hành:** cập nhật `TSK-S3-14` trong `neuroedge-roadmap.md` theo
   `CONTRIBUTING.md` §8, rồi đo TTFV (Sprint 3, tiêu chí 1).

## Khi có sự cố

- **Tag lệch `version`:** job `build` dừng với lỗi nêu cả hai giá trị; chưa có gì được
  đẩy. Xoá tag (`git push origin :refs/tags/vX`), sửa `version` qua PR, gắn lại tag.
- **Một phiên bản đã lên index thì không thay được.** PyPI không cho đẩy lại cùng số
  phiên bản, kể cả sau khi xoá. Sửa lỗi bằng số mới (`0.1.0rc2`, `0.1.1`).
- **Tắt phát hành ngay:** đặt `PUBLISH_ENABLED` khác `true` (hoặc xoá biến). Hai job
  `publish-*` bị bỏ qua từ lần chạy kế tiếp.
