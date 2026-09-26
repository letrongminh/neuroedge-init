# 11 · Hướng dẫn OEM port HAL

> Đối tượng: đối tác phần cứng đưa NeuroEdge lên board mới (U5).
> Chuẩn port: FR-TGT-08 bậc 3;_increment I13 (sau I11). Chính sách tài sản:
> proposal §1.7/`§6.4` (adapter/HAL port do tác giả giữ bản quyền, kho riêng,
> NeuroEdge lập chỉ mục).

## 1. Hợp đồng port (5 + 3 + 1)

```mermaid
flowchart TB
    P5[5 nguyên thủy đóng<br/>audio.in/out · digital.out<br/>sensor.read · display]
    P3[3 nghĩa vụ an toàn<br/>refuse-all mặc định<br/>authorize(token) trước mọi lệnh<br/>tên chân logic, không số vật lý]
    P1[1 bộ kiểm tuân thủ<br/>vector + 3 vết chuẩn mực<br/>verify đạt mới gọi là port]
    P5 --> P3 --> P1
```

- **Không** rẽ nhánh logic agent theo target (P-2); khác biệt phần cứng nằm
  trong `board.toml` + HAL, không trong mã agent.
- Token: dùng một lần mỗi chân, TTL=`p95×3`, đầy thì refuse; tương đương
  `ne_token.c` nếu viết C, hoặc `TokenLedger` nếu viết Python.
- Gate trên thiết bị: duyệt cây (không parser JSON/CEL trên MCU); ngữ nghĩa
  `ne_decide` ≡ `engine/` (`05`).

## 2. Checklist port (đạt mới công bố)

| # | Việc | Xong khi |
|:---:|---|:---|
| 1 | `board.toml` khai đủ năng lực theo `board.v1`, chân trùng tập tên logic | `board list/show` + `build` xanh với agent mẫu |
| 2 | 5 nguyên thủy (hoặc tập con khai báo) + refuse-all + authorize | Pentest nội bộ: không đường tắt tới actuator |
| 3 | Chạy bộ vector tuân thủ + 3 vết chuẩn mực, so với golden | `verify` đạt phạm vi port công bố |
| 4 | Ghi NOTICE + ghim phiên bản dep (nghĩa vụ port: `CONTRIBUTING.md` §4) | Review giấy phép qua (không copyleft mạnh) |
| 5 | Nightly + tài liệu vận hành board | Kết quả nightly công khai cho người dùng port |

Ba cổng kiểm soát (proposal §1.7): bộ kiểm tuân thủ · sandbox phân quyền ·
đối chiếu năng lực lúc build. Bậc 3 không chặn phát hành của đội lõi.
