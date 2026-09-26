# 13 · Tiến hóa I0–I18 (as-is vs planned)

> Ngày/tag: roadmap §0.2 (nơi duy nhất). Dưới đây chỉ nói *kiến trúc đổi gì*
> qua từng chặng — không chép ngày hay trạng thái task.

![E-08 · Lộ trình](../assets/svg/E-08-roadmap-timeline.svg)

## 1. As-is: I0–I4 (done, đã có mã)

Gate có kiểu + kế thừa an toàn, `sim`+`linux` ngang nhau, Action CI
(record/replay/assert/golden), MCP + System 2 qua LiteLLM, FSM thoại Python +
barge-in, walker/token/UART trên QEMU. Cổng nhu cầu 2026-10-25 (Q-20) quyết
Go/Adjust/Stop cho I3–I7.

## 2. Planned: I5–I7 (v1.0)

| Increment | Đổi kiến trúc | Rủi ro giữ |
|:---|:---|:---|
| I5 thoại trên chip | Hiện thực C/C++ thứ hai của FSM (port XiaoZhi/Pipecat, tuân cùng vector); streaming Opus lên provider | R-1 bộ nhớ (spike TSK-S1-10; trượt thì mở `Q-N` lập lại kế hoạch, không cắt thoại — Q-44) |
| I6 công khai | Lược đồ lên URL công khai; SBOM + provenance; PyPI đầu tiên | Điều khoản license thương mại (`TODOS.md` #44) |
| I7 v1.0 | OTA A/B có ký + rollback; Secure Boot + mã hóa flash; ổn định 24h; đủ A1–A9 | Nợ tiêu chí SEC-02→06/08 (Phụ lục A.3) phải đóng trước |

## 3. Planned: sau Beta

| Chặng | Variation point kiến trúc | Điều kiện mở |
|:---|:---|:---|
| I8 Beta | Đóng băng dòng `1.0.x` (chỉ lỗi chặn + an toàn); RFC/đặc tả vẫn merge (R12) | I7 đạt A1–A9 |
| I9–I10 Fleet + Registry | Một endpoint/credential cả đội; failover khai cấu hình; OTA canary; registry ORAS có ký; metering | Beta đạt B1 + B2 (Q-41) |
| I11 mở target | Enum `target` theo bậc + `TARGET_TIERS` + `board validate` (RFC-0002 PR2) | I8 |
| I12 NeuroBrain | `neuroedge.brain` chỉ qua `dispatch()` (B-1); lab action có gate; phong bì an toàn | I11 (+ I2/I3) |
| I13 bộ port | Tài liệu + vector + khung port bậc 3 (nối `11`) | I11 |
| I14 robot phân tầng | Mỗi node HAL + gate riêng; Zenoh-pico wire (Q-36); token lease `motion.*` (Q-37); ROS 2/Nav2 gate mọi lệnh tốc độ (Q-34); trạng thái an toàn từng cơ cấu (Q-35) | I13 (+ I4/I7/I11/I12) |
| I15–I17 thị giác | `vision.in` qua RFC riêng; `jetson` bậc 2; gate đa phương thức | Nhu cầu camera đo được |
| I18 hệ sinh thái | SDK đa thiết bị, kho HAL port, chứng nhận miễn phí tự kiểm | I13 (+ I9/I10) |

Ngoài roadmap: AURA thực địa (chỉ API công khai), Marketplace (chặn tới khi
đạt G1–G4).
