# 05 · Code Level: gate → token → HAL (C4 L4)

> Status: `done`. Read with poster E-05 and `09-adr.md`
> (Q-9, Q-18, Q-23, Q-25, Q-26).

![E-05 · Gate spine](../assets/svg/E-05-gate-spine.svg)

## 1. Gate resolution (build/lint/resolve)

```mermaid
flowchart LR
    Y[gate YAML] --> V[schema gate.v1<br/>NE2002]
    V --> CH[extends chain<br/>≤3 levels, no cycles<br/>NE2003]
    CH --> M["merge: evaluate (P1+P3)<br/>allow_when tightens only (P2)<br/>budget/on_block (Q-18)<br/>arguments narrow only (Q-25)"]
    M --> T[compile_tree<br/>criteria_order + digest]
    T --> B[binary_tree.encode<br/>NETR v1 + C header]
```

- Redefining an inherited criterion → refused (P1). String-CEL `allow_when`
  inside an `extends` chain → refused (only standalone gates may use CEL, and
  lint currently refuses even that until a compiler exists — fail-closed).
- Child `p95` ≤ parent; an already-`closed` chain cannot be reopened with
  `fail: open`; children cannot introduce new `degrade` (Q-18). Out-of-range
  arguments are gate-BLOCKed (`argument_out_of_range`), never REJECTED (Q-25).

## 2. Runtime evaluation (one `c.do()`)

```mermaid
sequenceDiagram
    participant D as dispatch
    participant G as engine.evaluate
    participant S as SystemOne/fallback
    participant L as TokenLedger
    participant H as HAL
    D->>G: evaluate(gate, facts, args, remaining p95)
    G->>G: arguments.check()
    G->>S: adjudicate each missing criterion (p95 deadline)
    S-->>G: Fact | Unavailable
    G->>G: walk(tree, facts) → ALLOW | BLOCK
    alt BLOCK
        G->>D: on_block: deny/escalate/ask/degrade
    else ALLOW
        G->>L: issue(token, pins, TTL=p95×3)
        D->>H: digital_out(pin, op, token)
        H->>L: authorize(token, pin)
        H-->>D: actuator_command
        D->>L: close(token)
    end
```

- `BLOCK` → no token, `@action` body never runs, pins unchanged. `degrade`
  runs `fallback_action` **through its own gate** (recursive, cycle-guarded).
  `ask` with `confirms` opens a single-use `PendingConfirmation` expiring at
  `max(p95×3, 10s)`; confirmations come from humans via device only (Q-26).
- Tokens are single-use per pin; reuse/expiry/foreign-process → NE1002, pins
  stay put, `actuator_command_rejected` is logged. Contract violations (NE1001)
  **raise**, never degrade into BLOCK.

## 3. NETR v1 layout on device (RFC-0003)

64 B header (`NETR`, layout v1, `gate_digest[32]`, node/arg/enum counts,
`on_block`, `fail_open`, p95, `confirm_mask`, CRC32) + 24 B nodes ×n (kind,
domain size, offsets, `admitted_mask`, `confidence_floor`) + args/enums +
NUL strings. Max ~19 KB flash. `ne_tree_load` rejects bad magic/version/size/
CRC/limits. No allocation in the walker — why gates run on a $5 chip and still
fail closed.
