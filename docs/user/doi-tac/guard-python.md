# Hướng dẫn 2 — `neuroedge.guard` trong một agent Python

> **Mục tiêu:** agent Python của bạn (một vòng lặp LLM, một node ROS, một script nhà thông minh) chạm thiết bị **chỉ qua một `Guard`**: mỗi
> lời gọi qua gate trước, và hàm chạm thiết bị chỉ chạy **sau khi gate cho phép**. **Thời gian:** ≤ 15 phút từ lúc đã cài wheel.
>
> Hướng dẫn này không cần thiết bị, Home Assistant hay mạng: thiết bị là một hàm Python. Mọi khối lệnh ở đây được
> [`scripts/partner_guides_check.sh`](../../../scripts/partner_guides_check.sh) chạy từ wheel. Cú pháp đầy đủ của `guard.toml` và `Tool`:
> [`docs/spec/extension_sdk.md`](../../spec/extension_sdk.md) §1–§3; giới hạn: [`gioi-han.md`](gioi-han.md).

## 0. Bạn cần

Đã cài wheel theo [README](README.md). Làm việc trong một thư mục trống. Không có biến môi trường nào cần đặt.

## 1. Ba lệnh tới giá trị đầu

**Lệnh 1 — viết gate.** Gate nói điều kiện để một lời gọi được qua: ở đây, chương trình chủ phải xác nhận `badge_ok`, và `seconds` nằm trong 1–60.

<!-- guide: run -->
```bash
mkdir -p gates && cat > gates/plug_on@1.0.0.yaml <<'YAML'
schema:  neuroedge.gate/v1
name:    plug_on
version: 1.0.0

arguments:
  seconds: { type: integer, minimum: 1, maximum: 60 }

evaluate:
  badge_ok:
    type: bool
    instructions: "Chương trình chủ đã xác thực người ra lệnh"

allow_when:
  badge_ok: true

on_block:
  action: deny

budget:
  p95_latency_ms: 150
  fail:           closed
YAML
```

**Lệnh 2 — viết agent.** `run` là hàm duy nhất chạm thiết bị; `Guard` chỉ gọi nó sau ALLOW. `dispatcher("agent")` cấp cho bên gọi một cổng có nguồn `bridge:agent`:
bên gọi **không** nói được nguồn của mình, và `ToolRequest` không có trường `source`.

<!-- guide: run -->
```bash
cat > agent.py <<'PY'
import asyncio
import json

from neuroedge.guard import Guard, Tool
from neuroedge.sdk import ToolRequest

ran = []  # những gì thiết bị thật sự được yêu cầu


def plug_on(seconds):
    ran.append(seconds)  # <- ở đây bạn gọi thiết bị thật (HTTP, serial, …); chỉ chạy sau ALLOW


tool = Tool(
    "plug_on",
    "gates/plug_on@1.0.0.yaml",
    parameters={"seconds": {"type": "integer", "default": 5}},
    run=plug_on,
)


async def main():
    async with Guard([tool], name="my-agent") as guard:
        bridge = guard.dispatcher("agent")
        first = await bridge.dispatch(ToolRequest("plug_on", {"seconds": 5}))
        guard.set_fact("badge_ok", True)  # chương trình chủ xác nhận: đây là quyết định của BẠN
        second = await bridge.dispatch(ToolRequest("plug_on", {"seconds": 5}))
        third = await bridge.dispatch(ToolRequest("plug_on", {"seconds": 600}))
        for outcome in (first, second, third):
            print(outcome.status, outcome.content.get("reason", ""))
        print("device was asked:", ran)
        with open("trace.json", "w") as out:
            json.dump(guard.trace(), out, indent=2)


asyncio.run(main())
PY
```

**Lệnh 3 — chạy.**

<!-- guide: run expect="BLOCK criterion_unavailable" expect="ALLOW " expect="BLOCK argument_out_of_range" expect="device was asked: [5]" -->
```bash
python agent.py
```

Đọc ba dòng kết quả:

1. `BLOCK criterion_unavailable` — chưa ai nói `badge_ok`, nên gate chặn: **thiết bị chưa được hỏi**.
2. `ALLOW` — sau `guard.set_fact("badge_ok", True)` gate cho qua và `plug_on` chạy.
3. `BLOCK argument_out_of_range` — `seconds = 600` vượt giới hạn 60 của gate: bị chặn dù `badge_ok` đã đúng.

Và `device was asked: [5]`: hàm thiết bị chạy **đúng một lần**, cho lời gọi được phép.

## 2. BLOCK rồi ALLOW — mở gate có chủ ý

Trong hướng dẫn này, "mở gate" là chương trình của bạn đặt dữ kiện (`set_fact`) — quyết định nằm ở mã của bạn, không ở LLM: một LLM chỉ gửi `ToolRequest`, nó không gọi được `set_fact`
nếu bạn không đưa cho nó. Hai điều cần nhớ:

- Đừng đưa `guard` cho LLM hay cho bridge. Đưa cho chúng đúng một thứ: `dispatcher(...)`.
- `Outcome` chỉ có `status` và `content` (lý do, tiêu chí gây chặn, hành động thay thế). Nó **không** mang giá trị mà `run` trả về — chủ ý, để bên gọi không lấy dữ liệu từ đường
  này. Cần kết quả của thiết bị thì đặt nó ở chỗ chương trình của bạn đọc (như `ran` ở trên).

Muốn cấu hình bằng tệp thay vì mã: `Guard.load("guard.toml")` — ví dụ chạy được ở [`examples/guard/`](../../../examples/guard/).

## 3. Đọc vết ghi

<!-- guide: run expect="VALID" -->
```bash
neuroedge trace validate trace.json
```

<!-- guide: run expect="gate_evaluation_result" expect="guard:my-agent@" expect="bridge:agent" -->
```bash
neuroedge trace show trace.json
```

Vết ghi có ba lời gọi, nguồn `bridge:agent`, từng phán quyết và lý do. Nó chứa **tham số** của lời gọi (không băm). Phát lại một vết ghi của `Guard` bằng
`TracePlayer(trace, guard="guard.toml")` (cần `guard.toml`; xem `extension_sdk.md` §1).

## 4. Làm `Guard` thành đường duy nhất

`plugin doctor` **không** áp dụng ở đây (nó đọc `[proxy.*]` của `guard.toml`). Với `Guard` trong tiến trình, "đường duy nhất" là kỷ luật của mã bạn:

- Thiết bị chỉ được chạm trong `run` của một `Tool`. Một `requests.post(...)` ở chỗ khác trong agent là một lối vòng mà không công cụ nào của chúng tôi thấy.
- `Guard` không chặn mạng và không chống mã cùng tiến trình (mô hình đe doạ: [`threat_model.md`](../../spec/threat_model.md) §3). Nếu thiết bị nhận lệnh từ máy khác, lệnh đó không qua gate.
- Nếu thiết bị có API mạng, đặt nó sau tường lửa để chỉ máy chạy agent tới được; chúng tôi không làm việc đó thay bạn.

## 5. Lỗi thường gặp (thông báo thật)

**Id cổng sai** — chỉ `[a-z][a-z0-9_]{0,31}`:

<!-- guide: run exit=1 expect="'Bad-Id' is not a bridge id" expect="use [a-z][a-z0-9_]{0,31}" -->
```bash
python - <<'PY'
from neuroedge.guard import Guard, Tool

Guard([Tool("plug_on", "gates/plug_on@1.0.0.yaml")]).dispatcher("Bad-Id")
PY
```

**Hai cổng cùng id** — id là danh tính trong vết ghi, không dùng chung:

<!-- guide: run exit=1 expect="'bridge:agent' is already registered" -->
```bash
python - <<'PY'
from neuroedge.guard import Guard, Tool

guard = Guard([Tool("plug_on", "gates/plug_on@1.0.0.yaml")])
guard.dispatcher("agent")
guard.dispatcher("agent")
PY
```

**Không tìm thấy tệp gate** — đường dẫn tính từ thư mục bạn chạy lệnh (hoặc từ `base=` / thư mục của `guard.toml`):

<!-- guide: run exit=1 expect="GateNotFoundError" expect="file does not exist" -->
```bash
python - <<'PY'
from neuroedge.guard import Guard, Tool

Guard([Tool("plug_on", "gates/khong-co.yaml")])
PY
```

**Tool đòi chân mà `Guard` không có bo mạch** — `requires` chỉ dùng được khi khai `board=`; để đơn giản, thiết bị của bạn là một hàm `run`:

<!-- guide: run exit=1 expect="BoardCapabilityError" expect="this Guard has no board" -->
```bash
python - <<'PY'
from neuroedge.guard import Guard, Tool

Guard([Tool("plug_on", "gates/plug_on@1.0.0.yaml", requires=("digital.out:porch_light",))])
PY
```

**Tên tool hay tham số lạ** — không phải ngoại lệ mà là `REJECTED` (và không có gì chạy):

<!-- guide: run expect="REJECTED" expect="no tool named 'khong_co'" expect="unknown argument 'la'" -->
```bash
python - <<'PY'
import asyncio

from neuroedge.guard import Guard, Tool
from neuroedge.sdk import ToolRequest


async def main():
    guard = Guard([Tool("plug_on", "gates/plug_on@1.0.0.yaml")])
    bridge = guard.dispatcher("agent")
    print((await bridge.dispatch(ToolRequest("khong_co", {}))).content)
    print((await bridge.dispatch(ToolRequest("plug_on", {"la": 1}))).content)


asyncio.run(main())
PY
```

**`run` nhận tham số khác tham số đã khai** — `Tool` kiểm lúc dựng (lỗi `AgentManifestError`, "does not accept"): khai đúng `parameters` của hàm.

## 6. Tiếp theo

Gửi phản hồi theo [`phan-hoi.md`](phan-hoi.md). Hai hướng dẫn kia: [`home-assistant-mcp.md`](home-assistant-mcp.md), [`proxy-http.md`](proxy-http.md).
