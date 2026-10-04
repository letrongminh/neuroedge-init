# Giấy phép

Quyết định: **Q-45** (`neuroedge-prd.md` §15, 2026-09-25), mở rộng phần chuẩn ở **Q-67** (2026-10-04). Tệp này
nói phần nào của kho theo giấy phép nào; nội dung và lý do của quyết định chỉ nằm ở Q-45 và Q-67.

| Phần | Giấy phép | Văn bản |
|:---|:---|:---|
| Mã NeuroEdge — runtime Python, CLI, firmware, dịch vụ, công cụ, test, tài liệu (mọi thứ không nằm ở các dòng dưới) | **PolyForm Noncommercial 1.0.0** | [`LICENSE`](LICENSE) |
| Chuẩn mở — `schemas/`, `docs/spec/`, `fixtures/compliance/` | **Apache-2.0** | [`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt) |
| Corpus tuân thủ — `fixtures/tool_calls/`, `fixtures/contracts/`, `fixtures/traces/`, và `fixtures/agents/` mà corpus dùng (Q-67) | **Apache-2.0** | [`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt) |
| Mã port hoặc chuyển thể từ bên thứ ba | Giấy phép gốc của nó | [`NOTICE`](NOTICE) |
| Phông chữ của giao diện thiết bị — `targets/esp32s3/ui/fonts/` (Be Vietnam Pro, sinh bằng `scripts/gen_ui_fonts.sh`) | **OFL-1.1** | [`LICENSES/OFL-1.1.txt`](LICENSES/OFL-1.1.txt) · NOTICE mục A.5 |

**Phi thương mại** — cá nhân, nghiên cứu, học tập, tổ chức phi lợi nhuận, và mọi mục đích khác mà
PolyForm Noncommercial cho phép — được dùng, sửa và phân phối lại toàn bộ mã miễn phí, theo đúng
điều khoản trong `LICENSE`.

**Thương mại** — dùng NeuroEdge trong sản phẩm, dịch vụ hay hoạt động của doanh nghiệp, kể cả dùng
nội bộ — cần một **license thương mại** riêng. Liên hệ tác giả qua địa chỉ trong
[`python/pyproject.toml`](python/pyproject.toml). Trong license thương mại, tính năng an toàn cốt
lõi không bao giờ bị tách thành gói trả thêm (PRD P-3).

**Chuẩn mở** và **corpus tuân thủ** giữ Apache-2.0 để bên thứ ba hiện thực chuẩn và tự chứng minh bằng bộ kiểm
tuân thủ (tiêu chí A9, A13) mà không dùng tệp PolyForm Noncommercial, và để chuyển quyền quản trị đặc tả cho một tổ
chức trung lập khi đạt G1 (proposal §1.5).

**Plugin và adapter của bên thứ ba** (Extension SDK, Q-67) nằm ở kho của tác giả, theo giấy phép do tác giả chọn;
NeuroEdge không đòi bản quyền trên chúng. Plugin chạy cùng runtime NeuroEdge nên việc *dùng* chung với runtime vẫn
theo điều khoản của runtime ở dòng đầu bảng (phi thương mại miễn phí, thương mại cần license).

**Trước thay đổi này:** mọi bản tới commit `f68a47f` (2026-09-25) phát hành theo MIT. Ai đã nhận
các bản đó giữ quyền MIT với đúng các bản đó; từ sau commit đó, mã theo bảng trên.

**Đóng góp:** pull request từ người ngoài cần CLA trước khi merge, để NeuroEdge cấp được license
thương mại cho phần đóng góp và tái cấp phép được về sau (`TODOS.md` #43, `CONTRIBUTING.md` §2).

**Về sau:** mã giữ PolyForm Noncommercial qua v1.0; việc mở giấy phép được rà lại ở điểm rẽ Beta
(Q-59, `TODOS.md` #51).

*Tệp này tóm tắt; văn bản giấy phép là thứ ràng buộc. Không phải tư vấn pháp lý.*
