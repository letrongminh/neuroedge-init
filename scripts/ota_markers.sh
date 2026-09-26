#!/usr/bin/env bash
# Verdict helpers for OTA UART logs (TSK-S6-01/02/04; FR-OTA-01..04).
#
# Sourced by scripts/qemu_ota.sh and driven by the stubs in
# python/tests/test_ota_markers.py, so the fail-closed rules — a missing
# marker, a wrong order, a marker that must not be there, a reboot that must
# not happen — run on any host with bash, grep and awk.
#
# Each helper returns 1 and prints one line to stderr when the log does not
# prove what it must; none of them passes on an empty or truncated log. The
# patterns are EREs matched anywhere in the line; the callers anchor `^NE_OTA`
# so a marker quoted inside a trace line never counts. QEMU's UART ends lines
# with CRLF: every helper reads through `_ota_text`, which drops the CR, so a
# pattern ending in `$` matches the marker and not the carriage return.

# The log without carriage returns; a missing file reads as empty.
_ota_text() {
  [ -f "$1" ] && tr -d '\r' <"$1" || true
}

# First line number in file $1 whose line matches ERE $2; 0 when there is none.
ota_first() {
  local line
  line=$(_ota_text "$1" | awk -v re="$2" '$0 ~ re { print NR; exit }' 2>/dev/null || true)
  echo "${line:-0}"
}

# Every ERE appears in order: $1 file, then one or more patterns.
ota_ordered() {
  local file=$1
  shift
  local from=0 line pattern
  if [ ! -f "$file" ]; then
    echo "OTA: no log file $file" >&2
    return 1
  fi
  for pattern in "$@"; do
    line=$(_ota_text "$file" | awk -v re="$pattern" -v from="$from" \
      'NR > from && $0 ~ re { print NR; found = 1; exit } END { if (!found) exit 1 }') || {
      echo "OTA: /$pattern/ not found after line $from in $file" >&2
      return 1
    }
    from=$line
  done
  return 0
}

# The ERE never appears in the file.
ota_forbid() {
  if _ota_text "$1" | grep -aqE "$2"; then
    echo "OTA: unexpected /$2/ in $1" >&2
    return 1
  fi
  return 0
}

# The ERE appears exactly $3 times in the file.
ota_count_is() {
  local count
  count=$(_ota_text "$1" | grep -acE "$2" || true)
  count=${count:-0}
  if [ "$count" != "$3" ]; then
    echo "OTA: /$2/ appears $count time(s) in $1, expected $3" >&2
    return 1
  fi
  return 0
}

# Something matching ERE $3 after the last line matching anchor ERE $2.
ota_has_after() {
  local from
  from=$(_ota_text "$1" | awk -v re="$2" '$0 ~ re { line = NR } END { print line + 0 }')
  if [ "$from" = 0 ]; then
    echo "OTA: anchor /$2/ not found in $1" >&2
    return 1
  fi
  if _ota_text "$1" | awk -v from="$from" -v re="$3" \
    'NR > from && $0 ~ re { found = 1; exit } END { exit found ? 0 : 1 }'; then
    return 0
  fi
  echo "OTA: /$3/ not after /$2/ in $1" >&2
  return 1
}

# Nothing matching ERE $3 after the last line matching anchor ERE $2.
ota_nothing_after() {
  local from
  from=$(_ota_text "$1" | awk -v re="$2" '$0 ~ re { line = NR } END { print line + 0 }')
  if [ "$from" = 0 ]; then
    echo "OTA: anchor /$2/ not found in $1" >&2
    return 1
  fi
  if _ota_text "$1" | awk -v from="$from" -v re="$3" \
    'NR > from && $0 ~ re { found = 1; exit } END { exit found ? 1 : 0 }'; then
    return 0
  fi
  echo "OTA: /$3/ after /$2/ in $1" >&2
  return 1
}
