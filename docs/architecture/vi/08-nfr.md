# 08 · Yêu cầu phi chức năng → tactic kiến trúc

> Nguồn ngưỡng: PRD §9. Đường kiểm chứng: PRD Phụ lục A.3. Tài liệu này chỉ
> nối NFR với chỗ kiến trúc đáp ứng nó — không chép ngưỡng.

## 1. Hiệu năng + tài nguyên (đường găng v1.0)

| NFR | Tactic kiến trúc | Bằng chứng |
|:---|:---|:---|
| PERF-02 gate P95 < 120 ms cục bộ | Walker C không heap, duyệt tại chỗ; engine host đi cây đã biên dịch; ngân sách `budget.p95` mỗi gate | Đo nightly trên board thật (A2/A6) |
| PERF-03 P95 < 450 ms qua cloud | Deadline `p95 còn lại` cho `adjudicate`; timeout → `Unavailable` → fail theo gate | Vết ghi `turn_latency.gate` |
| PERF-04 SystemOne < 100 ms | 3 kiểu có cấu trúc, fallback ngữ pháp cục bộ tất định | `turn_latency`, FR-TEL-06 |
| PERF-01/07 thoại P95 850/1500 ms | Cloud-first: STT/TTS nặng ở provider; chip chỉ thu/phát + FSM + gate (P-4) | Đo lưu lượng thực, tách streaming/request-response |
| RES-02/03 SRAM ≥ 120 KB, PSRAM ≥ 2 MB, firmware ≤ 3,5 MB | Buffer tĩnh PSRAM, cây link const vào flash, không `malloc` sau init (RB-1/2/4) | `memory_probe` lúc boot + CI ngân sách flash |
| RES-04 100% an toàn offline | Gate + FSM chạy trên thiết bị; fallback lệnh cố định P0 (Q-14) | Bộ kịch bản suy giảm (A4) |

## 2. Tin cậy + bảo mật + riêng tư + quan sát

| NFR | Tactic kiến trúc |
|:---|:---|
| REL-02 fail-closed mặc định | Mọi `on_block` đều chặn vật lý ở v1.0 (Q-17); HAL refuse-all; ledger đầy thì refuse |
| REL-01 OTA 1000 thiết bị / 0 brick | Phân vùng A/B + rollback vòng lặp + ký RSA/ECDSA (FR-OTA); điều phối canary ở Fleet (planned) |
| REL-03 nightly board thật | `nightly-hardware.yml` + gpio-sim/i2c-stub/vkms trong CI; mọi drift là lỗi chặn phát hành |
| SEC-01 không đường tắt | Một đường duy nhất tới chân qua token; pentest + rà soát mã (A3) |
| SEC-02/03/04/05/06 thiết bị + mạng | Secure Boot + mã hóa flash, nút ngắt micro, TLS 1.3/mTLS/pin, chứng chỉ riêng từng thiết bị, ký firmware |
| SEC-07 sandbox mã bên thứ ba | v1.1, gắn Registry (FR-REG-07) |
| SEC-08/09 provider + bên gọi | TLS tới provider + ghi provider vào vết; MCP v1.0 chỉ stdio, LLM/MCP là bên gọi không tin cậy |
| PRIV-01..04 | Không lưu âm thanh mặc định; vết chỉ lưu quyết định; ẩn danh tại nguồn bằng hash giữ replay |
| OBS-01..03 | Một phiên = một vết đầy đủ; `turn_latency` + `session_summary` (tỷ lệ S1/S2, chi phí) trong mọi vết |
| COMP-01..06 | Lõi PolyForm Noncommercial, chuẩn Apache-2.0 (Q-45); Python 3.11+; Debian/Ubuntu ARM64+x86-64 |

Nợ truy vết đã biết (PRD Phụ lục A.3): SEC-02→06, 08 cần tiêu chí mốc đo
được trước khi đóng v1.0.
