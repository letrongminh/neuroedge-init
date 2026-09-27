# 00 · Tổng quan kiến trúc

> **Phạm vi:** toàn hệ thống, ở mức cao nhất. **Nguồn sự thật:** mã trong `main`; yêu cầu ở
> [`neuroedge-prd.md`](../../../neuroedge-prd.md); tiến độ ở
> [`neuroedge-roadmap.md`](../../../neuroedge-roadmap.md) §0. Quy ước nhãn `done` / `partial` /
> `planned`: [`README.md`](../README.md).

## 1. NeuroEdge giải bài toán gì

Một chatbot trả lời sai thì người dùng bấm "tạo lại". Một agent điều khiển thiết bị vật lý mà sai
thì chốt cửa đã mở, quạt đã tắt, rơ-le đã đóng — không có nút "tạo lại". Mô hình AI sinh ra đề
xuất; nó không thể là nơi quyết định một hành động vật lý có được làm hay không.

NeuroEdge tách hai việc đó ra. Mọi đề xuất hành động — từ ngữ pháp lệnh cục bộ, từ một LLM, từ
một agent khác qua MCP — đều được chuẩn hoá thành một **tool call có kiểu**, rồi phải qua một
**gate**: chính sách an toàn viết bằng YAML, có phiên bản, kế thừa được, được biên dịch thành cây
quyết định tất định. Gate cho `ALLOW` thì một **token phán quyết dùng một lần** được cấp, và chỉ
token đó mở được đúng các chân phần cứng của hành động đó. Mọi dữ kiện, phán quyết và lệnh chân
được ghi vào một **vết ghi** phát lại được. Cùng một gate chạy trên trình mô phỏng (`sim`), trên
Linux (`linux`) và trên chip ESP32-S3 (`esp32s3`).

## 2. Hệ thống trong một hình

![E-01 · Bối cảnh hệ thống](../assets/svg/E-01-system-context.svg)
*Hình E-01 — Người dùng, hệ thống bên ngoài, và ranh giới của NeuroEdge. Chi tiết: [`01`](01-context-c4l1.md).*

Đường đi duy nhất từ ý định tới chân phần cứng — **xương sống thực thi** — giống nhau ở mọi nguồn
gọi và mọi môi trường:

```mermaid
flowchart LR
    subgraph Sources["Callers (untrusted)"]
        G["Local command grammar<br/>commands.toml"]
        S2["System 2 LLM<br/>via LiteLLM"]
        MCP["MCP client<br/>Claude Desktop"]
    end
    TC["ToolCall<br/>name · arguments · source"]
    D["dispatch()<br/>schema check · call_source"]
    DO["c.do()"]
    GATE{"Gate engine<br/>evaluate()"}
    TOK["TokenLedger<br/>one-time token"]
    HAL["HAL<br/>authorize(token, pin)"]
    PIN(["Pin / actuator"])
    OB["on_block<br/>deny · ask · escalate · degrade"]
    TR[("Trace<br/>trace.v1.json")]

    G --> TC
    S2 --> TC
    MCP --> TC
    TC --> D --> DO --> GATE
    GATE -- ALLOW --> TOK --> HAL --> PIN
    GATE -- BLOCK --> OB
    GATE -.-> TR
    HAL -.-> TR
```

- **Không có đường tắt.** Gọi thẳng hàm `@action`, gọi `digital.out()` ngoài `c.do()`, đưa một
  chuỗi hay token tự chế cho HAL, dùng lại token, dùng token hết hạn — đều bị từ chối và ghi vết
  (`docs/spec/threat_model.md` §2).
- **Không chắc thì chặn.** Không thẩm định kịp, mất mạng mà không có fallback, dữ kiện thiếu hay
  sai kiểu ⇒ `BLOCK`, không bao giờ `ALLOW` (bất biến 2, `CHANGELOG.md` §3.3).
- **Bằng chứng tự sinh.** Vết ghi chứa đủ dữ kiện để tính lại mọi phán quyết mà không gọi model
  và không động vào máy (chi tiết: [`06`](06-runtime-flows.md) §7).

## 3. Năm nguyên tắc và nơi kiến trúc cưỡng chế chúng

Nội dung nguyên tắc ở PRD §1.5; bảng này chỉ ra **cơ chế kiến trúc** giữ từng nguyên tắc.

| Nguyên tắc (PRD §1.5) | Cơ chế kiến trúc cưỡng chế | Ở đâu |
|:---|:---|:---|
| **P-1** Hành động vật lý là hợp đồng chuẩn kiểu | Một đường duy nhất `dispatch()` → `c.do()` → gate → token → HAL; HAL không có sổ token thì từ chối mọi lệnh | [`05`](05-code-gate-hal-c4l4.md) · `actions/`, `hal/` |
| **P-2** Các môi trường thực thi ngang hàng | Cùng tệp gate, cùng ngữ nghĩa lượng giá trên host (Python) và chip (C); `verify` so quyết định giữa target | [`10`](10-target-equivalence.md) |
| **P-3** Giá trị ở quản trị đội thiết bị và license thương mại | Lõi an toàn nằm trọn trong gói `neuroedge`; dịch vụ (Fleet OS) là container riêng, chưa có mã | [`02`](02-container-c4l2.md) §4 |
| **P-4** Mô hình AI thay thế được | Mọi model sau giao thức `FactSource` / provider; không SDK nào được import ở lõi | [`03`](03-component-host-c4l3.md) §3.4 |
| **P-5** Hiệu ứng mạng từ chia sẻ chính sách | Gate là dữ liệu có phiên bản, định danh `neuroedge://`, băm JCS SHA-256, kế thừa chỉ siết chặt | [`07`](07-data-contracts.md) §2 |

## 4. Đặc tính kiến trúc, theo thứ tự ưu tiên

Khi hai đặc tính xung đột, đặc tính đứng trên thắng. Mỗi dòng là một quyết định thiết kế đã có mã.

| # | Đặc tính | Nghĩa là | Chiến thuật chính | Chương |
|:---:|:---|:---|:---|:---|
| 1 | **An toàn theo mặc định** | Mọi lỗi đều dẫn tới chặn | `budget.fail` mặc định `closed`; `fail: open` không kế thừa; sổ token đầy thì từ chối, không đẩy token cũ ra | [`05`](05-code-gate-hal-c4l4.md), [`08`](08-nfr.md) |
| 2 | **Tất định và phát lại được** | Cùng dữ kiện ⇒ cùng phán quyết, ở mọi nơi | Phân giải gate là hàm thuần; cây quyết định không đọc đồng hồ; replay tính lại từ dữ kiện đã ghi | [`05`](05-code-gate-hal-c4l4.md), [`06`](06-runtime-flows.md) |
| 3 | **Tương đương giữa môi trường** | Agent không rẽ nhánh theo target | Hai hiện thực (Python, C) của cùng một đặc tả, chứng minh bằng bảng sự thật và vector chung | [`10`](10-target-equivalence.md) |
| 4 | **Có thể kiểm toán** | Người duyệt hiểu được mà không đọc mã | Gate là YAML đọc được; `gate explain`; vết ghi theo lược đồ đóng băng; lỗi luôn có ba phần | [`07`](07-data-contracts.md) |
| 5 | **Thay được model** | Đổi nhà cung cấp bằng cấu hình | Chuẩn OpenAI-compatible, adapter `python:`; model chỉ trả dữ kiện, không bao giờ trả `ALLOW` | [`03`](03-component-host-c4l3.md) |
| 6 | **Chạy được khi mất mạng** | Chức năng an toàn không cần Internet | Ngữ pháp lệnh cục bộ là fallback của mọi model; lõi chỉ dùng thư viện chuẩn cho HTTP | [`06`](06-runtime-flows.md) §5 |
| 7 | **Vừa chip nhỏ** | Gate chạy trên ESP32-S3 | Không JSON, không CEL trên chip; cây nhị phân `NETR` đọc tại chỗ trong flash; walker không cấp phát, stack ≤ 512 B | [`04`](04-component-device-c4l3.md) |

## 5. Hình dạng hệ thống

NeuroEdge có ba phần, cộng với chuỗi CI giữ chúng khớp nhau:

| Phần | Là gì | Ngôn ngữ | Trạng thái |
|:---|:---|:---|:---|
| **Gói `neuroedge`** (host) | SDK, CLI, engine gate, HAL `sim`/`linux`, model, thoại, MCP, Action CI | Python 3.11+ | `done` |
| **Firmware `esp32s3`** | Walker `NETR`, sổ token, vết ghi UART, component sinh cho agent, OTA có ký | C99 trên ESP-IDF v5.4 | `partial` — chạy trên QEMU; chưa điều khiển chân |
| **Hợp đồng dữ liệu** | `gate.v1`, `trace.v1`, `board.v1`, `agent.toml`, `NETR` v1, dòng UART | JSON Schema, TOML, nhị phân | `done`, đóng băng qua RFC |
| **CI** | Test Python, gpio-sim, QEMU, ảnh golden, OTA, bảo mật | GitHub Actions | `done` |

Hai phần không có mã hôm nay và chỉ xuất hiện ở trạng thái `planned`: **Fleet OS** (I9) và **Gate
Registry** (I10). Mọi thứ quy hoạch khác (robot nhiều node, thị giác, NeuroBrain) ở
[`13`](13-evolution-i0-i18.md).

## 6. Hiện trạng theo năng lực

Bảng dưới là ảnh chụp hình dạng, không phải bảng tiến độ; tiến độ từng task ở roadmap §4–§8.

| Năng lực | `sim` | `linux` | `esp32s3` |
|:---|:---|:---|:---|
| Gate: phân giải, lượng giá, token | `done` | `done` | `done` trên host và QEMU |
| Điều khiển chân | `done` (ảo) | `done` trên gpio-sim | `planned` (TSK-S4-01) |
| Cảm biến, màn hình | `done` (ảo) | `done` trên `i2c-stub`, `vkms` | `planned`; giao diện LVGL chỉ build trên host |
| Thoại (từ tệp WAV) | `done` | `done` | `planned` (I5) |
| Thoại thời gian thực (micro) | `planned` | `partial` — mới mở thiết bị | `planned` |
| Model cloud (System 1, System 2) | `done` | `done` | không áp dụng: chip chỉ lượng giá gate |
| MCP | `done` | `done` | không áp dụng |
| Vết ghi, replay, verify | `done` | `done` | `done` (UART, QEMU) |
| Cập nhật OTA có ký | không áp dụng | không áp dụng | `partial` — trên QEMU |

## 7. Ranh giới — NeuroEdge không phải là gì

- **Không phải chức năng an toàn được chứng nhận** (không SIL theo IEC 61508, không PL theo ISO
  13849 — Q-38). Gate không thay nút dừng khẩn hay khoá liên động phần cứng.
- **Không chống kẻ tấn công trong cùng tiến trình.** Token là `(nonce, digest)` trong bộ nhớ; mối
  đe doạ trong phạm vi là **bỏ qua gate do nhầm lẫn**, và điều đó được chứng minh bằng test
  (`docs/spec/threat_model.md` §3, `TODOS.md` #2).
- **Không phải dịch vụ đám mây.** Hôm nay NeuroEdge là một thư viện, một CLI và một firmware; không
  có máy chủ nào do NeuroEdge vận hành.

## 8. Đọc tiếp

Lộ trình đọc theo vai trò ở [`README.md`](../README.md). Người mới bắt đầu ở
[`12-dev-quickstart.md`](12-dev-quickstart.md).
