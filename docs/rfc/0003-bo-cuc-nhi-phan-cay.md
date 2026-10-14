# RFC-0003: Freeze On-Device Decision Tree Binary Layout (`NETR` v1)

| | |
|:---|:---|
| **RFC ID** | 0003 |
| **Title** | On-device tree `NETR` v1 binary layout emitted by `neuroedge build` and read by C99 walker (Q-23) |
| **Affected Schema** | *(not in `schemas/`)* — new format frozen by this RFC |
| **Related PRD Requirements** | FR-ACE-01, FR-ACE-03, FR-ACE-08, FR-ACE-10, FR-CI-07, NFR-RES-01 |
| **Author** | V1 + V2 *(per TSK-S4-02)* |
| **Date Opened** | 2026-09-24 |
| **Status** | ✅ Approved — **narrowed**: binary layout only. Pinning `extends` via digest (TSK-S3-21) remains deferred, `TODOS.md` #15 · ✅ Implemented (TSK-S4-02, S4-07, S4-08; PR #27, #29) |
| **Approver** | Trong-Minh Le (@letrongminh, lead architect), 2026-09-24 |
| **Verification** | §7 — `python/tests/test_c_walker.py`, `python/tests/test_c_token.py`, CI job `firmware-qemu` |

> **When an RFC is required:** `TODOS.md` #15 and `decision_tree.py` require freezing the
> layout **before the first C walker exists**. Changing the layout after this RFC requires
> a new RFC and bumping `layout_version`; firmware rejects versions it does not recognize.

## 1. Problem

Q-9 and Q-23: the device has neither a CEL VM nor a JSON parser. It traverses a tree
compiled by the host. The JSON tree (`decision_tree.v1.json`) is an **internal host format**,
unsuitable on MCUs: requires parsers, dynamic allocation, and string comparisons. Firmware
needs a fixed layout, read **in-place from flash**, fully verifiable before use, and never
silently changing between builds.

## 2. Why the Existing Format Does Not Solve It

`decision_tree.v1.json` explicitly states *"internal, not frozen"* and contains strings,
lists, and floats in text form — not readable in-place, without integrity verification.

## 3. Proposed Change — `NETR` v1 Layout

All integers little-endian; fixed-size records, naturally aligned; **no pointers**
(file offsets only). The walker reads byte by byte, making it independent of CPU
endianness or alignment.

**Header — 64 bytes**

| Offset | Type | Field | Specification |
|---:|:---|:---|:---|
| 0 | `char[4]` | `magic` | `"NETR"` |
| 4 | `u16` | `layout_version` | `1` |
| 6 | `u16` | `header_size` | `64` |
| 8 | `u8[32]` | `gate_digest` | Raw SHA-256 of resolved gate — same digest as in trace |
| 40 | `u16` | `node_count` | 1..32 — `allow_when` criteria, following `criteria_order` |
| 42 | `u16` | `arg_count` | 0..16 — RFC-0005 argument limits, in declaration order |
| 44 | `u16` | `enum_count` | 0..64 |
| 46 | `u8` | `on_block_action` | 0 deny · 1 escalate · 2 ask · 3 degrade |
| 47 | `u8` | `fail_open` | 0 closed · 1 open |
| 48 | `u32` | `p95_latency_ms` | > 0 |
| 52 | `u32` | `confirm_mask` | bit *i*: criterion *i* confirmed by human instead (RFC-0006); non-zero only when `ask` |
| 56 | `u32` | `strings_size` | 1..16384, final byte is NUL |
| 60 | `u32` | `crc32` | CRC-32 (IEEE, like zlib) of entire file with these 4 bytes set to 0 |

**Criteria nodes — 24 bytes × `node_count`**

| Offset | Type | Field |
|---:|:---|:---|
| 0 | `u8` | `kind` — 0 bool · 1 level · 2 choice |
| 1 | `u8` | `domain_size` — 1..32 (bool: 2) |
| 2 | `u16` | `name_off` — criterion name in string table |
| 4 | `u32` | `admitted_mask` — bit *v*: *v*-th value of domain is accepted |
| 8 | `f64` | `confidence_floor` — [0, 1] |
| 16 | `u16` | `domain_off` — domain values, contiguous, each string NUL-terminated |
| 18 | `u16`, `u32` | reserved, zero |

Domains: bool = `false, true`; level = levels in order; choice = **sorted** options.
Facts arrive at the walker as **domain indices**, so the device does not perform
string comparisons to evaluate criteria.

**Argument limits — 32 bytes × `arg_count`**: `u16 name_off` · `u8 type` (0 string · 1
integer · 2 number · 3 boolean) · `u8 flags` (1 minimum · 2 maximum · 4 enum · 8 max_length) ·
`u16 enum_first` · `u16 enum_count` · `u32 max_length` (Unicode code points) · `u32` reserved ·
`f64 minimum` · `f64 maximum`.

**Enum — 16 bytes × `enum_count`**: `f64 number` (numeric; boolean is 0/1) · `u32 str_off` ·
`u32 str_len` (UTF-8 bytes, for string type).

**String table**: UTF-8, each string NUL-terminated.

File size = 64 + 24·n + 32·a + 16·e + strings, **strictly equal** to file length. With
the limits above, a tree occupies at most ~19 KB of flash.

**Walker semantics** (identical to host engine, `python/neuroedge/engine/`):

1. Parameter limits first, in declaration order — violation ⇒ BLOCK `argument_out_of_range`.
2. Each criterion in `criteria_order`: missing fact or outside domain ⇒
   `criterion_unavailable`; confidence is not a valid probability (including NaN) ⇒ `criterion_unavailable`;
   confidence floor declared but confidence missing ⇒ `confidence_unavailable`; value not admitted or confidence below floor ⇒
   `condition_not_met`. The recorded reason is the **first** error encountered.
3. After human confirmation: criteria in `confirm_mask` are treated as satisfied. A question
   is only *answerable* when satisfying those exact criteria suffices for ALLOW.
4. Degradation (`gate_unreachable`, `budget_exceeded`) decided by caller wrapping the walker based on `fail_open`,
   identical to host behavior.

**Loading**: `ne_tree_load` rejects any file with incorrect magic, version, size, CRC, bounds,
or structure — reads nothing outside the buffer.

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| `schemas/` | Unchanged |
| Gates, digests, three canonical traces | Unchanged — layout is compiled form of gate |
| Future layouts | New RFC + `layout_version` 2; walker v1 rejects v2 (`NE_ERR_VERSION`) |

## 5. Safety Impact

- Walker has no writable state (`.data`/`.bss` empty), no allocation, no recursion;
  maximum stack 176 bytes (`ne_evaluate`, clang `-O2`) — checked on every PR, 512-byte limit.
- Corrupted file at any byte rejected by CRC; any truncated length rejected; mutated structure
  with valid CRC is either rejected or traversed without out-of-bounds reads (fuzzed under ASan/UBSan).
- `gate_digest` in file matches digest recorded in trace: an on-device verdict always
  traces back to the signed policy.

## 6. Alternatives Considered and Rejected

| Alternative | Reason for Rejection |
|:---|:---|
| Put JSON on MCU (cJSON…) | Parser + dynamic allocation on safety path; eliminated by Q-9/Q-23 |
| FlatBuffers / Cap'n Proto | Adds dependencies and code generation tools; need is just a few fixed records |
| C struct `#pragma pack` direct cast | Depends on endianness, alignment, and compiler; bounds cannot be verified |

## 7. Verification Evidence

- [x] `python/tests/test_c_walker.py`: C walker (ASan + UBSan) matches **actual host engine**
  on all gates in `gates/`, valid corpus, sample agents, and a synthetic gate covering all constraint
  types — `truth_cases` rows × {unconfirmed, confirmed} + 400 seeded random cases per gate;
  matches truth tables recorded in `fixtures/decision_trees/`; fuzz; zero static RAM; stack ≤ 512 bytes
- [x] Mutation testing: 7 deliberate defects inserted into the walker (confidence check order,
  omitting/expanding confirmation, `maximum` bound, byte length counting, integer accepting fractional values, `answerable`) all caught
- [x] `neuroedge build` emits `<gate>.netree` and `<gate>.netree.h`

## 8. Tasks upon Approval

- [x] `python/neuroedge/engine/binary_tree.py` (encoder) · `targets/esp32s3/components/ne_gate/` (walker, ESP-IDF component, host Makefile)
- [x] `neuroedge-roadmap.md` TSK-S4-02, TSK-S4-07
- [x] `TODOS.md` #15 narrowed to `extends` pinning portion
- [x] Single-use token log in C (`ne_token.c`) and walker wired into `app_main` (boot-time self-test, `gate_selftest.c`) — TSK-S4-08, PR #29
