"""
The decision tree as the device reads it — binary layout `NETR` v2 (RFC-0003, RFC-0009).

`neuroedge build` writes one `<gate>.netree` per gate (and, for `esp32s3`, a C
header embedding it). The firmware's C99 walker (`targets/esp32s3/components/
ne_gate/`) reads it in place from flash: no parser, no pointers, no allocation.
The layout is frozen by RFC-0009 §3d (v1 by RFC-0003); a change needs a new `LAYOUT_VERSION`.

All integers little-endian; records fixed-size and naturally aligned::

    header   80 B   magic "NETR" · u16 layout_version (2) · u16 header_size (80) ·
                    u8[32] gate_digest (raw SHA-256) · u16 node_count ·
                    u16 arg_count · u16 enum_count · u8 on_block_action ·
                    u8 fail_open · u32 p95_latency_ms · u32 confirm_mask ·
                    u32 strings_size · u32 crc32 (of the file, this field zeroed) ·
                    u16 numeric_count · u16 gate_name_off · u16 gate_version_off ·
                    u16 on_block_to_off · u16 on_block_message_off ·
                    u16 fallback_action_off · u32 0 (reserved)
    nodes    24 B × node_count   one allow_when criterion, in criteria_order
                    u8 kind · u8 domain_size · u16 name_off · u32 admitted_mask ·
                    f64 confidence_floor · u16 domain_off · u16 0 · u32 0
    numeric  48 B × numeric_count one record per numeric node (kind=3), in order
                    f64 lo · f64 hi · f64 range_min · f64 range_max ·
                    u32 max_age_ms · u16 unit_off · u8 flags · u8 0 · u64 0
    args     32 B × arg_count    one RFC-0005 argument limit, declaration order
                    u16 name_off · u8 type · u8 flags · u16 enum_first ·
                    u16 enum_count · u32 max_length · u32 0 · f64 minimum ·
                    f64 maximum
    enums    16 B × enum_count   f64 number · u32 str_off · u32 str_len
    strings  UTF-8, each NUL-terminated; domain values of a node are
             consecutive, starting at its domain_off

A fact reaches the walker as a *domain index* — the value's position in the
node's domain (bool: false, true; level: its levels in order; choice: sorted) —
or, for a numeric node, as a reading (`value`, `age_ms`), so the device never
compares strings to decide a criterion.
"""

from __future__ import annotations

import struct
import zlib
from collections.abc import Mapping
from typing import Any

from ..errors import GateSchemaError

MAGIC = b"NETR"
LAYOUT_VERSION = 2
HEADER_SIZE = 80
NODE_SIZE = 24
NUMERIC_SIZE = 48
ARG_SIZE = 32
ENUM_SIZE = 16

MAX_NODES = 32  # confirm_mask and admitted_mask are u32
MAX_DOMAIN = 32
MAX_NUMERIC = 32
MAX_ARGS = 16
MAX_ENUMS = 64
MAX_STRINGS = 16_384

KINDS = {"bool": 0, "level": 1, "choice": 2, "numeric": 3}
ACTIONS = {"deny": 0, "escalate": 1, "ask": 2, "degrade": 3}
ARG_TYPES = {"string": 0, "integer": 1, "number": 2, "boolean": 3}
HAS_MIN, HAS_MAX, HAS_ENUM, HAS_MAX_LENGTH = 1, 2, 4, 8
NUM_HAS_LOWER, NUM_LOWER_CLOSED, NUM_HAS_UPPER, NUM_UPPER_CLOSED = 1, 2, 4, 8

_HEADER = struct.Struct("<4sHH32sHHHBBIIIIHHHHHHI")
_NODE = struct.Struct("<BBHIdHHI")
_NUMERIC = struct.Struct("<ddddIHBBQ")
_ARG = struct.Struct("<HBBHHIIdd")
_ENUM = struct.Struct("<dII")
assert _HEADER.size == HEADER_SIZE and _NODE.size == NODE_SIZE
assert _NUMERIC.size == NUMERIC_SIZE
assert _ARG.size == ARG_SIZE and _ENUM.size == ENUM_SIZE


class _Strings:
    def __init__(self) -> None:
        self.data = bytearray()
        self._seen: dict[str, int] = {}

    def add(self, text: str) -> int:
        if text in self._seen:
            return self._seen[text]
        offset = len(self.data)
        self.data += text.encode("utf-8") + b"\0"
        self._seen[text] = offset
        return offset

    def add_run(self, texts: list[str]) -> int:
        """Consecutive strings (a node's domain), never deduplicated."""
        offset = len(self.data)
        for text in texts:
            self.data += text.encode("utf-8") + b"\0"
        return offset


def _limit(label: str, what: str, count: int, maximum: int) -> None:
    if count > maximum:
        raise GateSchemaError(
            where=f"{label} -> {what}",
            why=f"{count} {what} exceed the device layout's limit of {maximum} (RFC-0003)",
            how="split the gate, or raise the limit through an RFC with a new layout version",
        )


def encode(tree: Mapping[str, Any]) -> bytes:
    """The `NETR` v2 bytes of a compiled tree (`decision_tree.compile_tree`)."""
    label = tree["gate"]
    nodes = tree["nodes"]
    limits = tree.get("arguments") or []
    on_block = tree["on_block"]
    numeric_nodes = [n for n in nodes if n["kind"] == "numeric"]
    _limit(label, "criteria", len(nodes), MAX_NODES)
    _limit(label, "numeric criteria", len(numeric_nodes), MAX_NUMERIC)
    _limit(label, "argument limits", len(limits), MAX_ARGS)

    strings = _Strings()
    raw_confirms = set(on_block.get("confirms") or ())
    confirms = raw_confirms if on_block.get("action") == "ask" else set()

    gate_name_off = 0xFFFF
    gate_version_off = 0xFFFF
    if "gate" in tree and tree["gate"]:
        gate_str = str(tree["gate"])
        if "@" in gate_str:
            g_name, g_ver = gate_str.split("@", 1)
            gate_name_off = strings.add(g_name)
            gate_version_off = strings.add(g_ver)
        else:
            gate_name_off = strings.add(gate_str)

    on_block_to_off = 0xFFFF
    if on_block.get("to") is not None:
        on_block_to_off = strings.add(str(on_block["to"]))

    on_block_message_off = 0xFFFF
    if on_block.get("message") is not None:
        on_block_message_off = strings.add(str(on_block["message"]))

    fallback_action_off = 0xFFFF
    if on_block.get("fallback_action") is not None:
        fallback_action_off = strings.add(str(on_block["fallback_action"]))

    node_bytes = bytearray()
    numeric_bytes = bytearray()
    confirm_mask = 0
    numeric_idx = 0

    for index, node in enumerate(nodes):
        criterion_name = node["criterion"]
        if criterion_name in raw_confirms and node["kind"] == "numeric":
            raise GateSchemaError(
                where=f"{label} -> confirm_mask",
                why=f"numeric criterion '{criterion_name}' cannot be in confirm_mask (RFC-0009)",
                how=(
                    "remove numeric criteria from confirms; only bool/level/choice can be "
                    "confirmed by a person"
                ),
            )
        if criterion_name in confirms:
            confirm_mask |= 1 << index

        name_off = strings.add(criterion_name)

        if node["kind"] == "numeric":
            num = node["numeric"]
            domain_off = numeric_idx
            numeric_idx += 1
            node_bytes += _NODE.pack(
                KINDS["numeric"],
                0,
                name_off,
                0,
                0.0,
                domain_off,
                0,
                0,
            )

            lower = num.get("lower")
            upper = num.get("upper")
            flags = 0
            lo = 0.0
            hi = 0.0
            if lower is not None:
                flags |= NUM_HAS_LOWER
                if lower.get("closed"):
                    flags |= NUM_LOWER_CLOSED
                lo = float(lower["value"])
            if upper is not None:
                flags |= NUM_HAS_UPPER
                if upper.get("closed"):
                    flags |= NUM_UPPER_CLOSED
                hi = float(upper["value"])

            range_min = float(num["range"]["min"])
            range_max = float(num["range"]["max"])
            max_age_ms = int(num["max_age_ms"])
            unit_off = strings.add(str(num["unit"]))

            numeric_bytes += _NUMERIC.pack(
                lo,
                hi,
                range_min,
                range_max,
                max_age_ms,
                unit_off,
                flags,
                0,
                0,
            )
        else:
            domain = list(node["domain"])
            _limit(f"{label} -> {criterion_name}", "domain values", len(domain), MAX_DOMAIN)
            mask = 0
            for value in node["admitted"]:
                mask |= 1 << domain.index(value)
            domain_off = strings.add_run(domain)
            node_bytes += _NODE.pack(
                KINDS[node["kind"]],
                len(domain),
                name_off,
                mask,
                float(node["confidence_floor"]),
                domain_off,
                0,
                0,
            )

    arg_bytes = bytearray()
    enum_bytes = bytearray()
    enum_count = 0
    for limit in limits:
        flags = 0
        kind = limit["type"]
        enum = list(limit.get("enum") or [])
        first = enum_count
        for value in enum:
            if kind == "string":
                raw = str(value).encode("utf-8")
                enum_bytes += _ENUM.pack(0.0, strings.add(str(value)), len(raw))
            else:
                enum_bytes += _ENUM.pack(float(value), 0, 0)
            enum_count += 1
        if "minimum" in limit:
            flags |= HAS_MIN
        if "maximum" in limit:
            flags |= HAS_MAX
        if "enum" in limit:
            flags |= HAS_ENUM
        if "max_length" in limit:
            flags |= HAS_MAX_LENGTH
        arg_bytes += _ARG.pack(
            strings.add(limit["name"]),
            ARG_TYPES[kind],
            flags,
            first,
            len(enum),
            int(limit.get("max_length", 0)),
            0,
            float(limit.get("minimum", 0.0)),
            float(limit.get("maximum", 0.0)),
        )
    _limit(label, "enum values", enum_count, MAX_ENUMS)
    _limit(label, "bytes of strings", len(strings.data), MAX_STRINGS)

    digest = bytes.fromhex(tree["gate_digest"].removeprefix("sha256:"))
    header = _HEADER.pack(
        MAGIC,
        LAYOUT_VERSION,
        HEADER_SIZE,
        digest,
        len(nodes),
        len(limits),
        enum_count,
        ACTIONS[on_block["action"]],
        1 if tree["budget"]["fail"] == "open" else 0,
        int(tree["budget"]["p95_latency_ms"]),
        confirm_mask,
        len(strings.data),
        0,
        len(numeric_nodes),
        gate_name_off,
        gate_version_off,
        on_block_to_off,
        on_block_message_off,
        fallback_action_off,
        0,
    )
    body = (
        bytes(header)
        + bytes(node_bytes)
        + bytes(numeric_bytes)
        + bytes(arg_bytes)
        + bytes(enum_bytes)
    )
    blob = body + bytes(strings.data)
    crc = zlib.crc32(blob) & 0xFFFFFFFF
    return blob[:60] + struct.pack("<I", crc) + blob[64:]


def c_header(tree: Mapping[str, Any], symbol: str) -> str:
    """A C header that links the tree into the firmware image as `const` (flash)."""
    blob = encode(tree)
    rows = [
        "  " + ", ".join(f"0x{byte:02x}" for byte in blob[i : i + 16]) + ","
        for i in range(0, len(blob), 16)
    ]
    guard = f"NE_TREE_{symbol.upper()}_H"
    return "\n".join(
        [
            f"/* Generated by `neuroedge build` from {tree['gate']} — do not edit. */",
            f"/* {tree['gate_digest']} · NETR layout v{LAYOUT_VERSION} (RFC-0003, RFC-0009) */",
            f"#ifndef {guard}",
            f"#define {guard}",
            "#include <stdint.h>",
            f"static const uint8_t ne_tree_{symbol}[{len(blob)}] = {{",
            *rows,
            "};",
            f"#endif /* {guard} */",
            "",
        ]
    )


def c_string(text: str) -> str:
    """
    `text` as a C99 string literal: printable ASCII as is, every other UTF-8 byte
    as a three-digit octal escape (never greedy, unlike `\\x`), `?` escaped so no
    trigraph can form.
    """
    out = []
    for byte in text.encode("utf-8"):
        char = chr(byte)
        if char in '"\\?':
            out.append("\\" + char)
        elif 0x20 <= byte < 0x7F:
            out.append(char)
        else:
            out.append(f"\\{byte:03o}")
    return '"' + "".join(out) + '"'


def domain_index(node: Mapping[str, Any], value: Any) -> int | None:
    """
    A fact value as the walker sees it: its index in the node's domain, or None
    when the value is out of domain (mirrors `decision_tree._classify`).
    """
    if node["kind"] == "numeric":
        return None
    if node["kind"] == "bool":
        if not isinstance(value, bool):
            return None
        key = "true" if value else "false"
    else:
        key = value
    try:
        return list(node["domain"]).index(key)
    except ValueError:
        return None
