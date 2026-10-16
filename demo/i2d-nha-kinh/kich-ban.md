# Kịch bản trình bày — nhà kính trên bo mạch ảo

> **Agent:** [`fixtures/agents/greenhouse`](../../fixtures/agents/greenhouse/agent.toml): quạt hút,
> máy sưởi, bơm phun sương, đèn quang hợp (bốn rơ-le), cửa mái (một servo), ba cảm biến (nhiệt độ,
> độ ẩm không khí, độ ẩm đất).
> **Bo mạch:** `sim-virtual` (Q-84), dựng từ chính agent, nhãn `risk=virtual_board`. Chỉ chạy trên `sim`.
> **Thời lượng:** khoảng 5 phút. **Kiểm thử:** `python/tests/test_greenhouse.py`.

Một câu chuyện: **ai hỏi cũng vậy, hộp quyết định, cây được an toàn.** Bốn luật:

- không bật sưởi khi không khí đã nóng (từ 30 °C) hoặc không có số đo;
- không tắt quạt hút và không đóng cửa mái khi rất nóng (từ 35 °C) hoặc không có số đo;
- không phun sương khi không khí đã ẩm (từ 90 %) hoặc không có số đo;
- chiều an toàn (tắt sưởi, bật quạt, mở cửa mái, tắt bơm) và đèn luôn được phép.

## 0. Chuẩn bị

```bash
alias ne="$PWD/python/.venv/bin/neuroedge"     # từ gốc repo
ne gate lint fixtures/agents/greenhouse/gates  # ✓ 9 gate(s) resolved
ne run --agent fixtures/agents/greenhouse/agent.toml --ui
```

Trang mở ở `127.0.0.1:8765`. Đầu trang có nhãn **Bo mạch ảo** (`risk=virtual_board`): nói rõ cho
khán giả đây là bo mạch dựng từ agent, chưa phải phần cứng thật.

> [!IMPORTANT]
> **Không nói:** không có mô hình vật lý (nhiệt độ là số người trình bày gõ, không tự tăng theo
> thời gian); không chạy trên `linux` hay chip (bo mạch ảo bị từ chối ngoài `sim`).

## 1. Sáu bước

Gõ vào ô lệnh của trang (hoặc vào REPL); nhìn thẻ từng bộ phận và dòng quyết định.

| # | Gõ | Trang hiện | Lời nói |
|:--|:---|:---|:---|
| 1 | `bật đèn` | ALLOW; thẻ **Đèn quang hợp** sáng | "Đèn là việc nhẹ: ai nhờ cũng được." |
| 2 | `mở cửa mái` | ALLOW; thẻ **Cửa mái** lên 90° | "Mở cửa mái là chiều an toàn, luôn được." |
| 3 | `:sensor air_temp 31` rồi `bật sưởi` | BLOCK, dữ kiện **Không khí nóng (từ 30 °C)** | "31 °C: sưởi thêm là nấu cây. Hộp từ chối, không ai xác nhận được." |
| 4 | `:sensor air_temp 36` rồi `tắt quạt`, `đóng cửa mái` | cả hai BLOCK, dữ kiện **Rất nóng (từ 35 °C)** | "Rất nóng thì quạt phải chạy và cửa mái phải mở." Rồi `bật quạt`: ALLOW. |
| 5 | `:sensor air_humidity 95` rồi `phun sương` | BLOCK, **Không khí rất ẩm (từ 90 %)** | "Ẩm sẵn rồi, phun thêm sinh nấm." |
| 6 | `:sensor air_humidity lỗi` rồi `phun sương`; sau đó `:sensor air_humidity 70` và `phun sương` | BLOCK (không có số đo), rồi ALLOW | "Cảm biến mất tín hiệu: hộp đóng, không đoán. Có số đo trở lại mới chạy." |

Nếu muốn thử giới hạn của bộ phận: `:sensor air_humidity 150` bị từ chối vì ngoài khoảng 0…100
(một số gõ nhầm không thể giả làm số đo).

## 2. Chạy tự động

```bash
bash demo/i2d-nha-kinh/chay-sim.sh --ui     # cả sáu bước, mỗi dòng cách nhau 2,5 giây, rồi phát lại
PACE=4 bash demo/i2d-nha-kinh/chay-sim.sh   # chậm hơn để vừa nói vừa chạy
```

Cuối cùng kịch bản phát lại vết đã ghi: cùng dữ kiện vào, cùng quyết định ra. `replay` dựng lại
bo mạch ảo từ agent và từ chối nếu dấu vân tay (`virtual_board_digest`) khác lúc ghi.

## 3. Nếu bị hỏi

- **"Chân `heater` có thật không?"** Không: bo mạch ảo thêm đúng những gì agent khai trong
  `[requires]` và `[sim.parts]`, với phong bì an toàn mặc định theo loại bộ phận.
- **"Đưa lên phần cứng thế nào?"** Khi có phần cứng, ánh xạ chân theo bo mạch (VP-PM) và build lại
  trên bo mạch thật; bo mạch ảo không đi cùng.
