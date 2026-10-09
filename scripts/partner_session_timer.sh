#!/usr/bin/env bash
# The observer's stopwatch for the partner session (TSK-I2c-19, docs/business/doi-tac/buoi-do.md).
#
#   scripts/partner_session_timer.sh [results.csv]      # default: partner_session_<date>.csv
#
# Prints the steps of the session; the observer presses Enter the moment the participant reaches a
# step, optionally types how many hints were given and a note, and `s` + Enter skips a step the
# participant never reached. Ctrl-D ends early. The result is a CSV the observer fills in as they go:
#
#   step,label,clock_utc,elapsed_s,hints,note
#
# Plain bash and date: nothing to install. The step ids (S0…S8) are the ones of the table in buoi-do.md.
set -euo pipefail

OUT=${1:-partner_session_$(date -u +%Y%m%d-%H%M%S).csv}

STEPS=(
  "S0|Bắt đầu: người tham gia mở README.md"
  "S1|Cài xong: lệnh neuroedge chạy được"
  "S2|Lệnh đầu của hướng dẫn xong (guard init / viết gate / khởi tạo)"
  "S3|Thấy BLOCK đầu tiên"
  "S4|Tự mở gate (sửa tay)"
  "S5|Thấy ALLOW đầu tiên có chủ ý, trên thứ thật của họ"
  "S6|Đọc vết ghi (trace show)"
  "S7|Chạy plugin doctor và nói được vì sao nó cảnh báo"
  "S8|Kết thúc buổi"
)

csv_field() { printf '"%s"' "${1//\"/\"\"}"; }

echo "step,label,clock_utc,elapsed_s,hints,note" > "$OUT"
echo "Các bước (Enter = vừa tới bước này; s+Enter = không tới; Ctrl-D = kết thúc sớm). Kết quả: $OUT"
printf '  %s\n' "${STEPS[@]//|/  }"
echo
start=
for entry in "${STEPS[@]}"; do
  id=${entry%%|*}
  label=${entry#*|}
  printf '[%s] %s — Enter khi tới bước này: ' "$id" "$label"
  if ! IFS= read -r answer; then echo; echo "kết thúc sớm tại $id"; break; fi
  if [ "$answer" = "s" ]; then
    echo "$id,$(csv_field "$label"),,,," >> "$OUT"
    continue
  fi
  now=$(date +%s)
  clock=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  [ -n "$start" ] || start=$now
  elapsed=$((now - start))
  printf '    %02d:%02d từ lúc bắt đầu. Số gợi ý đã đưa ở bước này (Enter = 0): ' $((elapsed / 60)) $((elapsed % 60))
  IFS= read -r hints || hints=
  case "$hints" in ''|*[!0-9]*) hints=0 ;; esac
  printf '    Ghi chú (Enter = bỏ qua): '
  IFS= read -r note || note=
  echo "$id,$(csv_field "$label"),$clock,$elapsed,$hints,$(csv_field "$note")" >> "$OUT"
done
echo
echo "Đã ghi $OUT"
