# 12 · Ngày đầu của kỹ sư mới

> **Mục tiêu của ngày đầu:** chạy được hệ thống trên máy mình, lần theo một lệnh từ bàn phím tới chân
> phần cứng qua đúng các tệp mã, và làm một thay đổi an toàn có test. Cú pháp đầy đủ của mọi lệnh ở
> `CHANGELOG.md` §2.3; bản đồ kho ở `CONTRIBUTING.md` §6; hướng dẫn người dùng ở
> [`docs/user/huong-dan.md`](../../user/huong-dan.md).

## Giờ 1 — chạy

Cần Python 3.11+. Không cần mạng, khoá API hay phần cứng.

```bash
cd python
python3 -m venv .venv && .venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q          # kỳ vọng: 0 failed, 0 skipped
export PATH="$PWD/.venv/bin:$PATH"; cd ..
```

Rồi, từ gốc kho:

```bash
neuroedge run -c "mở cửa phòng 101"     # ✓ ALLOW unlock_door@1.2.0, door_lock PULSED 30s
neuroedge run -c "mở cửa phòng 202"     # ✗ BLOCK room_matches → lễ tân
neuroedge gate explain gates/unlock_door@1.2.0.yaml
neuroedge verify                        # mọi gate phân giải, mọi vết ghi chuẩn mực phát lại đúng
```

Ba kết quả trên là cả sản phẩm thu nhỏ: một gate kế thừa ba cấp cho `ALLOW` khi đúng phòng, chặn và
chuyển lễ tân khi sai phòng; một người duyệt đọc được gate bằng lời; và một lệnh chứng minh mọi quyết
định đã ghi vẫn ra đúng như cũ.

## Giờ 2 — lần theo một lệnh qua mã

Mở các tệp theo đúng thứ tự một lượt gõ đi qua ([`06`](06-runtime-flows.md) §1):

| # | Tệp · hàm | Để thấy |
|:---:|:---|:---|
| 1 | `python/neuroedge/cli/main.py` · `run` | CLI nạp phiên, không tự quyết gì |
| 2 | `python/neuroedge/sim/session.py` · `SimSession.load` | nơi lắp ráp: build, engine, sổ token, HAL, model ([`03`](03-component-host-c4l3.md) §5) |
| 3 | `python/neuroedge/models/grammar.py` · `CommandGrammar.recognize` | câu gõ thành ý định và khe |
| 4 | `python/neuroedge/actions/tools.py` · `dispatch` | tool call, kiểm schema, chèn `call_source` |
| 5 | `python/neuroedge/actions/conversation.py` · `Conversation._do` | gate → token → thân hàm → đóng token |
| 6 | `python/neuroedge/engine/gate.py` · `ActionContractEngine.evaluate` | gom dữ kiện trong ngân sách, duyệt cây, `on_block` |
| 7 | `python/neuroedge/engine/decision_tree.py` · `walk` | quyết định thuần: lỗi đầu tiên thắng |
| 8 | `python/neuroedge/actions/token.py` · `TokenLedger.authorize` | sáu phép kiểm trước khi chân động |
| 9 | `python/neuroedge/hal/sim.py` · `SimHAL.digital_out` | lệnh chân và sự kiện `actuator_command` |
| 10 | `fixtures/agents/villa-concierge/` | agent đã chạy: `agent.toml`, `commands.toml`, `actions/`, `gates/` |

Chạy lại lệnh `mở cửa phòng 101` với `--trace-out /tmp/t.json`, rồi `neuroedge trace show /tmp/t.json`:
mỗi sự kiện trong vết ghi ứng với một bước trong bảng trên.

## Giờ 3 — một thay đổi an toàn có test

Bài tập: siết một gate và chứng minh việc siết đó.

```bash
neuroedge new nhamay --template factory-monitor && cd nhamay
neuroedge test                                    # bộ test an toàn của agent: đạt
neuroedge record -c "tắt báo động"                # ✗ BLOCK: phòng máy đang nóng
```

1. Mở `gates/alarm_off@1.0.0.yaml`. Đổi `heat_level: { lte: normal }` thành `{ lte: low }` (chỉ cho tắt
   còi khi phòng mát). Đây là **siết** — hợp lệ. Chạy `neuroedge test`: test
   `test_the_alarm_stays_on_until_the_room_cools` đỏ, vì nó mong tắt được còi ở dải `normal`. Test đang làm
   đúng việc: một thay đổi hành vi an toàn phải đi kèm việc sửa test **có chủ đích**. Sửa kỳ vọng của test
   cho khớp chính sách mới.
2. Thử **nới** ngược lại thành `{ lte: critical }` rồi `neuroedge replay traces/sess_….json`: phát lại
   báo `SAFETY REGRESSION` và thoát mã 1. Đây là cách CI bắt một thay đổi làm yếu an toàn.
3. Viết một test trong `tests/` khẳng định `tắt báo động` bị chặn ở 45 °C (xem `neuroedge.testing`:
   `assert_gate_blocked`, `assert_never_pulsed`), rồi `neuroedge test`.

## Luật cần biết trước lần PR đầu

| Luật | Vì sao | Nguồn |
|:---|:---|:---|
| Một số thay đổi **bắt buộc có RFC**: `schemas/`, ngữ nghĩa phân giải, ba vết ghi chuẩn mực, gate trong `digests.lock`, bố cục `NETR` | đó là hợp đồng người khác hiện thực | `CONTRIBUTING.md` §3 |
| Lược đồ hợp lệ **không** có nghĩa gate an toàn; cổng là `neuroedge gate lint` | nguyên tắc kế thừa là mệnh đề về hai tài liệu | bất biến 1 |
| Không test nào được skip; CI đỏ nếu có | skip là che lỗi | `CONTRIBUTING.md` §5 |
| Mọi corpus khép kín hai chiều | mỗi tệp một đáp án, mỗi đáp án một tệp | `CONTRIBUTING.md` §3 |
| Mỗi sự thật một nơi; nơi khác dẫn mã | tài liệu không tự mâu thuẫn | `CONTRIBUTING.md` §8.1 |
| Cạnh phụ thuộc mới giữa các gói phải được khai | kiến trúc không trôi | `python/tests/test_architecture_layers.py` |
| `ruff check .` và `ruff format --check .` sạch | CI chặn | `python/` |
| Đụng `paths.py`, `hatch_build.py`, `README.md` hay đường dẫn tới `schemas/`, `boards/`, `gates/` ⇒ chạy `scripts/wheel_smoke.sh` | bản cài từ wheel khác bản editable | `CLAUDE.md` |
| Xong một task: tiến độ ở roadmap, một mục `CHANGELOG.md` `[Chưa phát hành]` | trong cùng PR với mã | `CONTRIBUTING.md` §8 |

## Theo mảng

| Bạn làm | Bắt đầu từ | Chạy được cục bộ bằng |
|:---|:---|:---|
| Engine, gate | [`05`](05-code-gate-hal-c4l4.md), `python/tests/test_gate_engine.py` | pytest |
| Model, thoại | [`06`](06-runtime-flows.md) §5–§6, `docs/spec/voice_fsm.md` | pytest; nhà cung cấp giả `neuroedge.perception.providers.fake` |
| `linux` | [`10`](10-target-equivalence.md), `hal/linux.py` | máy Linux kernel ≥ 5.19: `bash scripts/setup_gpio_sim.sh`, rồi `tests_linux/` |
| Firmware | [`04`](04-component-device-c4l3.md) | Docker `espressif/idf:v5.4`: `scripts/qemu_boot.sh`, `scripts/qemu_ota.sh`, `scripts/run_ui_golden.sh` |
| Tài liệu kiến trúc | [`README.md`](../README.md) | `python3 scripts/gen_architecture_diagrams.py --check`, `python3 scripts/check_architecture_mermaid.py` |

## Lỗi hay gặp ngày đầu

| Thấy | Nghĩa | Làm |
|:---|:---|:---|
| `ModuleNotFoundError` khi chạy test | venv cũ thiếu phụ thuộc `dev` mới | `pip install -e '.[dev]'` lại |
| `NE3003 build failed … NE3001` | agent cần thứ bo mạch không có | đọc từng dòng vấn đề; đổi agent hoặc chọn bo mạch khác |
| `NE1001` khi test gọi thẳng một hàm `@action` | chỉ `c.do()` được chạy action | gọi qua `Conversation.do` hoặc `dispatch` |
| `NE4002 SAFETY REGRESSION` | phát lại lệch golden | thay đổi của bạn đổi một quyết định; nếu cố ý thì cần duyệt và có thể cần RFC |
| Mã thoát `2` | lệnh hoặc target chưa được hiện thực | đúng hành vi; không phải lỗi của bạn (bất biến 10) |
