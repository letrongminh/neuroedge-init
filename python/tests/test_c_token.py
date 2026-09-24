"""
TSK-S4-02 — the C token ledger refuses exactly as the host `TokenLedger` does.

`targets/esp32s3/components/ne_gate/src/ne_token.c` is compiled on this host with
AddressSanitizer and UndefinedBehaviorSanitizer and driven by operation scripts
(issue / authorize / tamper / close / advance the clock / restart). The same
scripts run on `neuroedge.actions.token.TokenLedger` with a fake clock; every
decision — reason and NE1001/NE1002 code — must match, step by step.

The C ledger has a fixed number of slots (ne_token.h). A small model of its
slot reuse (`SlotModel`) says when an issue must fail closed and which tokens
the ledger has forgotten; a forgotten token of the current boot is
`unknown_token` in C where the host (which never forgets) says
`token_replayed` or `token_expired` — a refusal either way, and asserted so.

Then what only C has: the full ledger, the millisecond clock wrapping at 2^32,
the saturating TTL, byte-level tampering; the static budget (no .data/.bss,
stack <= 512 B); a mutation check (deliberate bugs must be caught); the boot
self-test `targets/esp32s3/main/gate_selftest.c` on the host; and the committed
firmware gate headers against a fresh `neuroedge build`.
"""

from __future__ import annotations

import dataclasses
import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

from neuroedge.actions.token import TTL_FACTOR, TokenLedger
from neuroedge.errors import NeuroEdgeError

from .test_c_walker import STACK_LIMIT, STRICT, cc

SLOTS = 4  # NE_TOKEN_SLOTS
U32 = 1 << 32
REASONS = {
    "authorized": 0,
    "not_a_token": 1,
    "unknown_token": 2,
    "pin_not_granted": 3,
    "token_replayed": 4,
    "token_expired": 5,
}
CODES = {0: "-", 1: "NE1001", 2: "NE1001", 3: "NE1001", 4: "NE1002", 5: "NE1002"}
SAN = ["-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-fno-omit-frame-pointer"]


@pytest.fixture(scope="module")
def component(root) -> Path:
    return root / "targets" / "esp32s3" / "components" / "ne_gate"


def compile_runner(component: Path, out: Path, source: Path | None = None, sanitize=True) -> Path:
    command = [
        cc(),
        *STRICT[:-1],
        "-O1",
        "-g",
        *(SAN if sanitize else []),
        "-I",
        str(component / "include"),
        str(source or component / "src" / "ne_token.c"),
        str(component / "test" / "test_token_host.c"),
        "-o",
        str(out),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return out


@pytest.fixture(scope="module")
def runner(component, tmp_path_factory) -> Path:
    return compile_runner(component, tmp_path_factory.mktemp("token") / "test_token_host")


def run(runner: Path, path: Path, scripts) -> list[str]:
    path.write_text("".join(" ".join(map(str, op)) + "\n" for s in scripts for op in s))
    result = subprocess.run([str(runner), str(path)], capture_output=True, text=True, timeout=600)
    lines = result.stdout.splitlines()
    if result.returncode != 0:  # a crash or a sanitizer report is a mismatch, never a pass
        lines.append(f"exit {result.returncode}: {result.stderr[-2000:]}")
    return lines


def digest_of(seed: int) -> str:
    return "sha256:" + bytes((seed + 37 * i) & 0xFF for i in range(32)).hex()


# --- the host reference ------------------------------------------------------------------------


class _Sink:
    def __init__(self) -> None:
        self.reasons: list[str] = []

    def emit(self, type: str, data: dict) -> None:
        self.reasons.append(data["reason"])


@dataclasses.dataclass
class Slot:
    handle: int
    issued: int
    ttl: int
    closed: bool = False


class SlotModel:
    """ne_token_issue's reuse rule: the first free, closed or expired slot."""

    def __init__(self) -> None:
        self.slots: list[Slot | None] = [None] * SLOTS

    def take(self, now: int) -> int | None:
        for i, slot in enumerate(self.slots):
            if slot is None or slot.closed or now - slot.issued > slot.ttl:
                return i
        return None


class Reference:
    """
    One script, step by step, on the host TokenLedger: `step(op)` returns the line
    the C runner must print for that op (or None when it prints nothing).
    """

    def __init__(self) -> None:
        self.now = self.boot = 0
        self.sink = _Sink()
        self.ledger: TokenLedger | None = None
        self.model = SlotModel()
        self.tokens: list = []  # handle -> (VerdictToken, boot it was minted in)
        self.forgotten: set[int] = set()

    def _new_ledger(self) -> None:
        self.ledger = TokenLedger(
            lambda: self.now, events=self.sink, process_instance_id=str(self.boot)
        )
        self.model = SlotModel()

    def _decide(self, op: str, token, pin: int, token_boot, handle) -> str:
        before = len(self.sink.reasons)
        try:
            self.ledger.authorize(token, f"p{pin}", "test")
            reason = "authorized"
        except NeuroEdgeError:
            reason = self.sink.reasons[before]
        if handle in self.forgotten and token_boot == self.boot:
            assert reason != "authorized", "the host authorised a token C has forgotten"
            reason = "unknown_token"
        r = REASONS[reason]
        return f"{op} {r} {CODES[r]}"

    def step(self, op: tuple) -> str | None:
        kind, args = op[0], op[1:]
        if kind == "S":
            self.now, self.boot = args[0], args[1]
            self._new_ledger()
        elif kind == "I":
            p95, mask, seed = args
            index = self.model.take(self.now)
            if index is None:
                return "I 2"
            old = self.model.slots[index]
            if old is not None:
                self.forgotten.add(old.handle)
            token = self.ledger.issue(
                gate="g",
                gate_digest=digest_of(seed),
                action="a",
                pins=frozenset(f"p{i}" for i in range(32) if mask >> i & 1),
                session_id="s",
                p95_ms=p95,
            )
            self.model.slots[index] = Slot(len(self.tokens), self.now, p95 * TTL_FACTOR)
            self.tokens.append((token, self.boot))
            return "I 0"
        elif kind == "A":
            token, token_boot = self.tokens[args[0]]
            return self._decide("A", token, args[1], token_boot, args[0])
        elif kind == "T":
            handle, pin, field, k = args
            token, token_boot = tamper(*self.tokens[handle], field, k)
            return self._decide("T", token, pin, token_boot, handle)
        elif kind == "N":
            return self._decide("N", object(), args[0], None, None)
        elif kind == "C":
            token, token_boot = self.tokens[args[0]]
            self.ledger.close(token)
            if token_boot == self.boot and args[0] not in self.forgotten:
                for slot in self.model.slots:
                    if slot is not None and slot.handle == args[0]:
                        slot.closed = True
        elif kind == "W":
            self.now += args[0]
        elif kind == "R":
            self.boot = args[0]
            self._new_ledger()
        elif kind == "E":
            return "E"
        return None

    def script(self, ops) -> list[str]:
        return [line for op in ops if (line := self.step(op)) is not None]


def tamper(token, boot: int, field: int, k: int):
    """The host form of the runner's T op: one field of the token changed."""
    if field == 0:
        i = ((k // 8) % 16) * 2
        flipped = "0" if token.nonce[i] != "0" else "1"
        return dataclasses.replace(
            token, nonce=token.nonce[:i] + flipped + token.nonce[i + 1 :]
        ), boot
    if field == 1:
        return dataclasses.replace(token, gate_digest=token.gate_digest + "x"), boot
    if field == 2:
        return dataclasses.replace(token, pins=token.pins ^ {f"p{k % 32}"}), boot
    if field == 3:
        return dataclasses.replace(token, issued_at_ms=token.issued_at_ms + 1), boot
    if field == 4:
        return dataclasses.replace(token, ttl_ms=token.ttl_ms + 1), boot
    boot ^= 1
    return dataclasses.replace(token, process_instance_id=str(boot)), boot


# --- random scripts ------------------------------------------------------------------------------


def random_script(rng: random.Random) -> list[tuple]:
    """At most NE_TOKEN_SLOTS live tokens at a time: beyond that, issue fails closed."""
    start = rng.choice([0, rng.randrange(U32), U32 - rng.randrange(1, 3000)])
    boot = rng.randrange(1 << 30) * 2  # even: a tampered boot_id (^ 1) is never a real one
    ref = Reference()
    ops: list[tuple] = []

    def add(op: tuple) -> None:
        ops.append(op)
        ref.step(op)

    add(("S", start, boot, rng.randrange(1 << 30)))
    for _ in range(rng.randrange(10, 50)):
        handles = len(ref.tokens)
        pick = rng.random()
        if pick < 0.22 or not handles:
            p95 = rng.choice([1, 5, 50, 150, 1000])
            mask = rng.choice([1, 3, 0b101, 0xFF, rng.randrange(1, 256), 0])
            add(("I", p95, mask, rng.randrange(256)))
        elif pick < 0.55:
            handle = rng.randrange(handles)
            granted = sorted(int(p[1:]) for p in ref.tokens[handle][0].pins)
            if granted and rng.random() < 0.6:
                pin = rng.choice(granted)  # mostly a pin the token grants
            else:
                pin = rng.choice([0, 1, 2, 3, 7, 8, 40])
            add(("A", handle, pin))
        elif pick < 0.63:
            add(
                (
                    "T",
                    rng.randrange(handles),
                    rng.choice([0, 1, 2]),
                    rng.randrange(6),
                    rng.randrange(256),
                )
            )
        elif pick < 0.72:
            add(("C", rng.randrange(handles)))
        elif pick < 0.80:
            token, _ = ref.tokens[rng.randrange(handles)]
            target = int(token.issued_at_ms + token.ttl_ms) + rng.choice([0, 1])  # the TTL edge
            add(("W", target - ref.now if target >= ref.now else rng.choice([0, 1, 17])))
        elif pick < 0.95:
            add(("W", rng.choice([0, 1, 2, 149, 150, 151, 450, 451, 3000])))
        elif pick < 0.98:
            add(("R", (ref.boot + 2 * rng.randrange(1, 1000)) % (1 << 31)))
        else:
            add(("N", rng.randrange(3)))
    add(("E",))
    return ops


def compare(expected: list[str], actual: list[str]) -> str | None:
    if expected == actual:
        return None
    for i, (e, a) in enumerate(zip(expected, actual, strict=False)):
        if e != a:
            return f"line {i}: expected {e!r}, C printed {a!r}"
    return f"expected {len(expected)} lines, C printed {len(actual)}"


def expected_of(scripts) -> list[str]:
    return [line for s in scripts for line in Reference().script(s)]


def differential_scripts(n: int, seed: int) -> list[list[tuple]]:
    rng = random.Random(seed)
    return [random_script(rng) for _ in range(n)]


# --- the cases only C has ------------------------------------------------------------------------

UNKNOWN, EXPIRED, OK = "2 NE1001", "5 NE1002", "0 -"


def c_only_cases() -> list[tuple[list[tuple], list[str]]]:
    cases = []

    # Four live tokens fill the ledger; the fifth issue fails closed, and a live token
    # is never evicted to make room. A closed or expired slot is reused.
    ops = [("S", 1000, 2, 7), *[("I", 50, 1, 0)] * 4, ("I", 50, 1, 0), ("A", 0, 0)]
    ops += [("C", 0), ("I", 50, 1, 0), ("A", 0, 0), ("A", 1, 0), ("I", 50, 1, 0)]
    ops += [("W", 151), ("I", 50, 1, 0), ("A", 5, 0), ("E",)]
    out = ["I 0"] * 4 + ["I 2", f"A {OK}", "I 0", f"A {UNKNOWN}", f"A {OK}", "I 2"]
    out += ["I 0", f"A {OK}", "E"]
    cases.append((ops, out))

    # The millisecond clock wraps at 2^32 between issue and use.
    ops = [("S", U32 - 296, 2, 1), ("I", 100, 7, 0), ("W", 250), ("A", 0, 0), ("W", 46)]
    ops += [("A", 0, 1), ("W", 4), ("I", 100, 1, 0), ("A", 0, 2), ("W", 1), ("A", 0, 3)]
    ops += [("A", 1, 0), ("E",)]
    out = ["I 0", f"A {OK}", f"A {OK}", "I 0", f"A {OK}", "A 3 NE1001", f"A {OK}", "E"]
    cases.append((ops, out))
    ops = [("S", U32 - 296, 2, 1), ("I", 100, 7, 0), ("W", 297), ("A", 0, 0), ("W", 3)]
    ops += [("A", 0, 1), ("W", 1), ("A", 0, 2), ("E",)]
    cases.append((ops, ["I 0", f"A {OK}", f"A {OK}", f"A {EXPIRED}", "E"]))

    # p95 x 3 saturates at UINT32_MAX instead of wrapping to a tiny TTL.
    for p95 in (1431655765, 1431655766, U32 - 1):
        ops = [("S", 0, 2, 1), ("I", p95, 1, 0), ("W", U32 - 1), ("A", 0, 0), ("E",)]
        cases.append((ops, ["I 0", f"A {OK}", "E"]))

    # One changed byte of nonce or digest, one bit of the mask, issued or ttl => unknown_token;
    # boot_id => token_expired (the check before). Tampered copies consume nothing.
    ops = [("S", 5, 2, 3), ("I", 50, 0xF, 9)]
    out = ["I 0"]
    for field, count in ((0, 16 * 8), (1, 32 * 8), (2, 32), (3, 1), (4, 1)):
        for k in range(count):
            ops.append(("T", 0, 0, field, k))
            out.append(f"T {UNKNOWN}")
    ops += [("T", 0, 0, 5, 0), ("A", 0, 0), ("A", 0, 0), ("N", 0), ("E",)]
    out += [f"T {EXPIRED}", f"A {OK}", "A 4 NE1002", "N 1 NE1001", "E"]
    cases.append((ops, out))

    # Two tokens with the same fields at the same instant differ by their nonce.
    ops = [("S", 9, 2, 5), ("I", 50, 1, 0), ("I", 50, 1, 0), ("A", 0, 0), ("A", 1, 0), ("E",)]
    cases.append((ops, ["I 0", "I 0", f"A {OK}", f"A {OK}", "E"]))

    # A restart: tokens from the old boot are token_expired, even unspent ones.
    ops = [("S", 9, 2, 5), ("I", 50, 1, 0), ("R", 4), ("A", 0, 0), ("I", 50, 1, 0), ("A", 1, 0)]
    ops += [("C", 0), ("A", 1, 0), ("E",)]
    cases.append((ops, ["I 0", f"A {EXPIRED}", "I 0", f"A {OK}", "A 4 NE1002", "E"]))
    return cases


def c_only_checks(runner: Path, tmp_path: Path) -> str | None:
    for i, (ops, expected) in enumerate(c_only_cases()):
        actual = run(runner, tmp_path / f"c_only_{i}.txt", [ops])
        problem = compare(expected, actual)
        if problem:
            return f"C-only case {i}: {problem}"
    return None


# --- the tests -----------------------------------------------------------------------------------


def test_the_c_ledger_refuses_exactly_as_the_host_ledger(runner, tmp_path):
    scripts = differential_scripts(2000, seed=20260924)
    expected = expected_of(scripts)
    actual = run(runner, tmp_path / "scripts.txt", scripts)
    assert compare(expected, actual) is None, compare(expected, actual)
    decisions = [line for line in expected if line[0] in "ATN"]
    seen = {line.split()[1] for line in decisions}
    assert seen == {"0", "1", "2", "3", "4", "5"}, seen  # every reason was exercised
    assert "I 2" in expected  # and the full ledger
    assert len(decisions) > 20000


def test_the_reference_host_ledger_checks_in_the_documented_order():
    """A token that is both replayed and expired is `token_replayed` on both sides."""
    ops = [("S", 0, 2, 1), ("I", 10, 1, 0), ("A", 0, 0), ("W", 31), ("A", 0, 0), ("E",)]
    assert Reference().script(ops) == ["I 0", f"A {OK}", "A 4 NE1002", "E"]


@pytest.mark.parametrize("index", range(len(c_only_cases())))
def test_what_only_the_c_ledger_has(runner, tmp_path, index):
    ops, expected = c_only_cases()[index]
    actual = run(runner, tmp_path / "case.txt", [ops])
    assert actual == expected


def test_the_ledger_uses_no_static_ram_and_a_small_stack(component, tmp_path):
    obj = tmp_path / "ne_token.o"
    command = [
        cc(),
        *STRICT,
        "-O2",
        "-fstack-usage",
        "-I",
        str(component / "include"),
        "-c",
        str(component / "src" / "ne_token.c"),
        "-o",
        str(obj),
    ]
    result = subprocess.run(command, capture_output=True, text=True, cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    symbols = subprocess.run(["nm", str(obj)], capture_output=True, text=True, check=True).stdout
    writable = [line for line in symbols.splitlines() if re.search(r"\s[bBdDC]\s", line)]
    assert writable == [], f"the ledger must hold no .data/.bss state: {writable}"
    usage = (tmp_path / "ne_token.su").read_text()
    frames = {m.group(1): int(m.group(2)) for m in re.finditer(r":(\w+)\s+(\d+)\s+\w+", usage)}
    assert "ne_token_issue" in frames and "ne_token_authorize" in frames, usage
    assert max(frames.values()) <= STACK_LIMIT, frames


MUTANTS = {
    "replay of a consumed pin allowed": (
        " || (slot->consumed_mask & (1u << pin)) != 0u)",
        ")",
    ),
    "closed token still usable": ("if (slot->state == NE_SLOT_CLOSED || ", "if ("),
    "TTL boundary exclusive": (
        "(uint32_t)(now_ms - token->issued_ms) > token->ttl_ms",
        "(uint32_t)(now_ms - token->issued_ms) >= token->ttl_ms",
    ),
    "expiry not wrap-safe": (
        "(uint32_t)(now_ms - token->issued_ms) > token->ttl_ms",
        "now_ms > token->issued_ms + token->ttl_ms",
    ),
    "restart not detected": (
        "if (token->boot_id != ledger->boot_id) return NE_TOKEN_EXPIRED;",
        "",
    ),
    "TTL wraps instead of saturating": (
        "p95_ms > UINT32_MAX / NE_TTL_FACTOR ? UINT32_MAX : p95_ms * NE_TTL_FACTOR",
        "p95_ms * NE_TTL_FACTOR",
    ),
    "full ledger evicts a live token": (
        "if (slot == NULL) return NE_TOKEN_ERR_FULL;",
        "if (slot == NULL) slot = &ledger->slots[0];",
    ),
    "nonce compared on its first byte only": (
        "diff_bytes(a->nonce, b->nonce, NE_NONCE_SIZE)",
        "diff_bytes(a->nonce, b->nonce, 1u)",
    ),
    "pin mask not checked": (
        "if (pin >= NE_MAX_PINS || (token->pin_mask & (1u << pin)) == 0u)",
        "if (pin >= NE_MAX_PINS)",
    ),
    "consumed pin not recorded": ("slot->consumed_mask |= 1u << pin;", ""),
}


def test_every_deliberate_bug_is_caught(component, tmp_path):
    source = (component / "src" / "ne_token.c").read_text()
    scripts = differential_scripts(300, seed=7)
    expected = expected_of(scripts)
    survivors = []
    for label, (old, new) in MUTANTS.items():
        assert source.count(old) == 1, label
        mutant = tmp_path / "ne_token_mutant.c"
        mutant.write_text(source.replace(old, new))
        exe = compile_runner(component, tmp_path / "mutant", source=mutant, sanitize=False)
        actual = run(exe, tmp_path / "scripts.txt", scripts)
        caught = compare(expected, actual) or c_only_checks(exe, tmp_path)
        if not caught:
            survivors.append(label)
    assert survivors == [], f"these bugs pass every test: {survivors}"
    assert len(MUTANTS) >= 5


# --- the firmware self-test ----------------------------------------------------------------------

SELFTEST_MAIN = r"""
#include <stdio.h>
#include "gate_selftest.h"
static unsigned state = 1u;
static void fill(void *buf, size_t len) {
    unsigned char *p = buf;
    for (size_t i = 0; i < len; i++) { state = state * 1103515245u + 12345u; p[i] = (unsigned char)(state >> 16); }
}
int main(void) {
    char line[96];
    int rc = neuroedge_gate_selftest(fill, 0x2468u, 4294967000u, line, sizeof line);
    puts(line);
    return rc;
}
"""


def test_the_boot_self_test_passes_on_the_host(root, component, tmp_path):
    main_dir = root / "targets" / "esp32s3" / "main"
    driver = tmp_path / "driver.c"
    driver.write_text(SELFTEST_MAIN)
    exe = tmp_path / "selftest"
    command = [
        cc(),
        *STRICT,
        "-O1",
        *SAN,
        "-I",
        str(component / "include"),
        "-I",
        str(main_dir),
        str(component / "src" / "ne_walker.c"),
        str(component / "src" / "ne_token.c"),
        str(main_dir / "gate_selftest.c"),
        str(driver),
        "-o",
        str(exe),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "NE_SELFTEST PASS walker=6 token=6"


def test_the_firmware_gate_headers_match_a_fresh_build(root):
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "gen_firmware_gates.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "targets/esp32s3/main/gates/ is stale against fixtures/agents/home-voice.\n"
        "Run: python/.venv/bin/python scripts/gen_firmware_gates.py\n"
        f"{result.stdout}{result.stderr}"
    )
