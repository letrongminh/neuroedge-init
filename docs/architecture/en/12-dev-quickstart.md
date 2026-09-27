# 12 · A new engineer's first day

> **Goal of the first day:** run the system on your own machine, follow one command from the keyboard
> to the hardware pin through the exact code files, and make one safe change with a test. Full syntax
> of every command: `CHANGELOG.md` §2.3; repo map: `CONTRIBUTING.md` §6; user guide:
> [`docs/user/huong-dan.md`](../../user/huong-dan.md).

## Hour 1 — run

Python 3.11+ required. No network, API key or hardware needed.

```bash
cd python
python3 -m venv .venv && .venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q          # kỳ vọng: 0 failed, 0 skipped
export PATH="$PWD/.venv/bin:$PATH"; cd ..
```

Then, from the repo root:

```bash
neuroedge run -c "mở cửa phòng 101"     # ✓ ALLOW unlock_door@1.2.0, door_lock PULSED 30s
neuroedge run -c "mở cửa phòng 202"     # ✗ BLOCK room_matches → lễ tân
neuroedge gate explain gates/unlock_door@1.2.0.yaml
neuroedge verify                        # mọi gate phân giải, mọi vết ghi chuẩn mực phát lại đúng
```

Those three results are the whole product in miniature: a gate with three levels of inheritance gives
`ALLOW` when the room matches, blocks and hands over to the receptionist when it does not; a reviewer
can read the gate in words; and one command proves that every recorded decision still comes out exactly
as before.

## Hour 2 — follow one command through the code

Open the files in the exact order of one typed turn ([`06`](06-runtime-flows.md) §1):

| # | File · function | To see |
|:---:|:---|:---|
| 1 | `python/neuroedge/cli/main.py` · `run` | the CLI loads the session, decides nothing itself |
| 2 | `python/neuroedge/sim/session.py` · `SimSession.load` | the assembly point: build, engine, token ledger, HAL, model ([`03`](03-component-host-c4l3.md) §5) |
| 3 | `python/neuroedge/models/grammar.py` · `CommandGrammar.recognize` | the typed sentence becomes intent and slots |
| 4 | `python/neuroedge/actions/tools.py` · `dispatch` | tool call, schema check, `call_source` inserted |
| 5 | `python/neuroedge/actions/conversation.py` · `Conversation._do` | gate → token → function body → close token |
| 6 | `python/neuroedge/engine/gate.py` · `ActionContractEngine.evaluate` | gather facts within budget, walk the tree, `on_block` |
| 7 | `python/neuroedge/engine/decision_tree.py` · `walk` | pure decision: first failure wins |
| 8 | `python/neuroedge/actions/token.py` · `TokenLedger.authorize` | six checks before a pin moves |
| 9 | `python/neuroedge/hal/sim.py` · `SimHAL.digital_out` | the pin command and the `actuator_command` event |
| 10 | `fixtures/agents/villa-concierge/` | a working agent: `agent.toml`, `commands.toml`, `actions/`, `gates/` |

Run the `mở cửa phòng 101` command again with `--trace-out /tmp/t.json`, then
`neuroedge trace show /tmp/t.json`: every event in the trace matches one step in the table above.

## Hour 3 — one safe change with a test

Exercise: tighten a gate and prove the tightening.

```bash
neuroedge new nhamay --template factory-monitor && cd nhamay
neuroedge test                                    # bộ test an toàn của agent: đạt
neuroedge record -c "tắt báo động"                # ✗ BLOCK: phòng máy đang nóng
```

1. Open `gates/alarm_off@1.0.0.yaml`. Change `heat_level: { lte: normal }` to `{ lte: low }` (only
   allow turning the siren off when the room is cool). This is a **tightening** — valid. Run
   `neuroedge test`: the test `test_the_alarm_stays_on_until_the_room_cools` goes red, because it
   expects the siren to be turned off in the `normal` band. The test is doing its job: a safety
   behaviour change must come with a **deliberate** test edit. Fix the test's expectation to match the
   new policy.
2. Try **loosening** it the other way to `{ lte: critical }`, then `neuroedge replay traces/sess_….json`:
   the replay reports `SAFETY REGRESSION` and exits with code 1. This is how CI catches a change that
   weakens safety.
3. Write a test in `tests/` asserting that `tắt báo động` is blocked at 45 °C (see `neuroedge.testing`:
   `assert_gate_blocked`, `assert_never_pulsed`), then `neuroedge test`.

## Rules to know before your first PR

| Rule | Why | Source |
|:---|:---|:---|
| Some changes **require an RFC**: `schemas/`, resolution semantics, the three normative traces, gates in `digests.lock`, the `NETR` layout | these are contracts other people implement | `CONTRIBUTING.md` §3 |
| A valid schema does **not** mean a safe gate; the gatekeeper is `neuroedge gate lint` | the inheritance rule is a statement about the two documents | invariant 1 |
| No test may be skipped; CI fails if one is | a skip hides a failure | `CONTRIBUTING.md` §5 |
| Every corpus is closed both ways | each file one answer, each answer one file | `CONTRIBUTING.md` §3 |
| Each fact in one place; other places cite it | documentation does not contradict itself | `CONTRIBUTING.md` §8.1 |
| A new dependency edge between packages must be declared | the architecture does not drift | `python/tests/test_architecture_layers.py` |
| `ruff check .` and `ruff format --check .` clean | CI blocks | `python/` |
| Touching `paths.py`, `hatch_build.py`, `README.md` or a path to `schemas/`, `boards/`, `gates/` ⇒ run `scripts/wheel_smoke.sh` | a wheel install differs from an editable install | `CLAUDE.md` |
| A task done: progress in the roadmap, a `CHANGELOG.md` `[Chưa phát hành]` entry | in the same PR as the code | `CONTRIBUTING.md` §8 |

## By area

| You work on | Start from | Runs locally with |
|:---|:---|:---|
| Engine, gate | [`05`](05-code-gate-hal-c4l4.md), `python/tests/test_gate_engine.py` | pytest |
| Models, voice | [`06`](06-runtime-flows.md) §5–§6, `docs/spec/voice_fsm.md` | pytest; fake provider `neuroedge.perception.providers.fake` |
| `linux` | [`10`](10-target-equivalence.md), `hal/linux.py` | a Linux machine with kernel ≥ 5.19: `bash scripts/setup_gpio_sim.sh`, then `tests_linux/` |
| Firmware | [`04`](04-component-device-c4l3.md) | Docker `espressif/idf:v5.4`: `scripts/qemu_boot.sh`, `scripts/qemu_ota.sh`, `scripts/run_ui_golden.sh` |
| Architecture docs | [`README.md`](../README.md) | `python3 scripts/gen_architecture_diagrams.py --check`, `python3 scripts/check_architecture_mermaid.py` |

## Common first-day errors

| You see | Meaning | Do |
|:---|:---|:---|
| `ModuleNotFoundError` when running tests | an old venv missing new `dev` dependencies | `pip install -e '.[dev]'` again |
| `NE3003 build failed … NE3001` | the agent needs something the board does not have | read every problem line; change the agent or pick another board |
| `NE1001` when a test calls an `@action` function directly | only `c.do()` may run an action | call through `Conversation.do` or `dispatch` |
| `NE4002 SAFETY REGRESSION` | the replay differs from golden | your change alters a decision; if deliberate it needs review and may need an RFC |
| Exit code `2` | the command or target is not implemented yet | correct behaviour; not your bug (invariant 10) |
