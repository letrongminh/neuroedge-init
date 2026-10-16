# Kịch bản demo — bể cá đầy đủ trên bo ảo

> **Thời lượng:** 6–8 phút, một cảnh duy nhất.
> **Agent:** [`fixtures/agents/aquarium-full`](../../fixtures/agents/aquarium-full/agent.toml):
> máy sưởi, máy sục khí, bơm lọc, van CO₂, đèn bể; cảm biến nhiệt độ nước, pH, oxy hoà tan, mực nước.
> **Bo:** `sim-virtual` (Q-84), chỉ chạy trên `sim`, luôn hiện nhãn `risk=virtual_board`.

Khác với [bể cá giả lập](../i2b-be-ca-gia-lap/kich-ban.md) (mượn chân `gate_relay`, `door_lock`,
`porch_light` của bo mẫu), bể này có **tên linh kiện của riêng nó**: người xem thấy "Máy sục khí",
"Van CO₂", "Oxy hoà tan" chứ không phải tên chân của bo cửa. Câu chuyện vẫn một: **ai yêu cầu cũng
được, hộp quyết định, cá an toàn.**

Các luật chính:

- máy sưởi không bật khi nước ấm (từ 29 °C) hoặc không có số đo;
- máy sục khí: trạng thái an toàn là **bật**; tắt thì hỏi chủ nhà, còn oxy thấp (dưới 5 mg/L), nước ấm
  hoặc mất số đo thì từ chối luôn, không hỏi;
- bơm lọc không chạy khô (mực nước dưới 30 %); tắt bơm lọc thì hỏi chủ nhà;
- van CO₂ không mở khi pH dưới 6.5 hoặc oxy dưới 5 mg/L;
- tắt sưởi, bật sục khí, đóng CO₂ và đèn luôn được phép.

---

## 0. Chuẩn bị

```bash
alias ne="$PWD/python/.venv/bin/neuroedge"     # từ gốc repo
ne gate lint fixtures/agents/aquarium-full/gates    # ✓ 9 gate(s) resolved
```

> [!IMPORTANT]
> **Không nói:**
> - **Không có mô hình vật lý:** nhiệt độ, pH, oxy, mực nước là số người trình bày gõ
>   (`:sensor ph 6.2`) hoặc đặt trên trang, không tự đổi theo thời gian.
> - **Đây là bo ảo, không phải phần cứng thật:** nhãn `risk=virtual_board` hiện ở đầu phiên và trên
>   trang; muốn đưa lên chip phải khai chân thật cho bo thật (graduation), bo ảo bị từ chối ngoài `sim`.
> - **Bộ giới hạn an toàn là mặc định của loại linh kiện:** mỗi chân đầu ra tối đa 60 s liên tục
>   (máy sưởi, bơm, van), đèn 10 phút; trong demo mỗi lệnh cách nhau hơn 2 s.

---

## 1. Chạy

```bash
bash demo/i2d-be-ca-day-du/chay-sim.sh --ui      # trang sống ở http://127.0.0.1:8765
```

Hoặc gõ tay: `ne run --agent fixtures/agents/aquarium-full/agent.toml --ui`. Dòng đầu in
`risk=virtual_board added: ...` liệt kê chân và cảm biến mà bo ảo thêm vào.

Mỗi bước dưới đây: gõ lệnh vào REPL (hoặc nói trên trang), đặt số đo bằng `:sensor <tên> <giá trị>`.

### Bước 1 — Bể khoẻ mạnh (25 °C, pH 7.0, oxy 7.5, nước 80 %)
**Nói:** "Chín linh kiện, mỗi cái có tên tiếng Việt. Bể đang khoẻ: bật đèn, bật sưởi, bật lọc, bật sục khí."
```text
bật đèn bể
bật sưởi
bật lọc
bật sục khí
```
**Thấy:** bốn `ALLOW`, bốn thẻ trên trang chuyển sang "Bật".

### Bước 2 — pH tụt thì chặn CO₂
**Nói:** "CO₂ làm nước chua thêm. pH đã xuống 6.2 thì không ai được mở van, kể cả người trong nhà."
```text
bơm CO2
:sensor ph 6.2
bơm CO2
```
**Thấy:** lần đầu `ALLOW` (pH 7.0). Sau khi đặt 6.2: `BLOCK`, tiêu chí `ph_ok`, câu từ chối bằng
tiếng Việt, không hỏi ai. Gõ `tắt CO2` vẫn `ALLOW`: đóng van luôn an toàn.

### Bước 3 — Nước cạn thì chặn bơm lọc
**Nói:** "Bơm lọc chạy khô là hỏng bơm. Mực nước 20 % thì không bật."
```text
:sensor water_level 20
tắt lọc
có
bật lọc
```
**Thấy:** `tắt lọc` hỏi chủ nhà, `có` thì tắt (bể đang 20 %, bơm đã tắt); `bật lọc` bị `BLOCK`
(`water_ok`). Tắt bơm lọc luôn phải hỏi vì nước bể sẽ bẩn dần.

### Bước 4 — Oxy thấp thì không được tắt sục khí
**Nói:** "Oxy chỉ còn 3.5. Có người muốn tắt máy sục khí: hộp từ chối ngay, thậm chí không hỏi chủ nhà,
vì một tiếng 'có' cũng không đủ cứu cá."
```text
:sensor oxygen 3.5
tắt sục khí
có
```
**Thấy:** `BLOCK` ngay ở `tắt sục khí`, không có câu hỏi; `có` sau đó cũng bị từ chối. Cũng lúc này
`bơm CO2` bị chặn vì oxy thấp (nếu pH đã trả về 7.0).

### Bước 5 — Hồi phục thì hỏi chủ nhà
**Nói:** "Oxy về 7.5. Lúc này tắt sục khí được, nhưng phải hỏi chủ nhà: lần đầu họ nói không, lần hai nói có."
```text
:sensor oxygen 7.5
tắt sục khí
không
tắt sục khí
có
```
**Thấy:** `asks`, `declined`, `asks`, `confirmed`. Máy sục khí tắt đúng một lần, sau "có".

### Bước 6 — Mất số đo và số không hợp lệ
**Nói:** "Đầu dò hỏng thì hộp không đoán: không số đo là không bật sưởi. Còn gõ nhầm pH 15 thì
trang từ chối, vì pH chỉ từ 0 đến 14."
```text
:sensor water_temp lỗi
bật sưởi
:sensor ph 15
```
**Thấy:** `bật sưởi` `BLOCK` (`criterion_unavailable`); `:sensor ph 15` bị từ chối, nêu khoảng `0…14`,
số đo cũ giữ nguyên. Gõ `exit` để kết thúc; `chay-sim.sh` phát lại phiên ghi ra và so quyết định.

---

## Kiểm tra trước buổi trình bày

`python/tests/test_aquarium_full.py` kiểm từng luật hai chiều (có số đo, không số đo, hỏi và xác nhận,
giá trị ngoài khoảng). Kịch bản trên dùng đúng các ngưỡng đó.
