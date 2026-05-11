#!/usr/bin/env bash
# assemble.sh — produce one final mp4 from: hook clip + broll clip + text overlay.
#
# Usage:
#   assemble.sh <hook_clip> <broll_clip> <hook_text> <out_path>
#
# Output: 9:16 1080x1920 mp4, AAC audio, hook clip first then broll, hook
# overlay PNG (TikTok Sans Bold + Apple color emoji) drawn on top of the
# hook segment only. Mirrors libs/captions/render-overlay.js — same font,
# same emoji set, same stroke style.
#
# Requires: ffmpeg, ffprobe, python3 with Pillow.

set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: assemble.sh <hook_clip> <broll_clip> <hook_text> <out_path>" >&2
  exit 2
fi

HOOK="$1"
BROLL="$2"
TEXT="$3"
OUT="$4"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

HOOK_DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$HOOK")
NORMALIZE='scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30'

mkdir -p "$(dirname "$OUT")"

# 1) Render the hook overlay PNG (TikTok Sans + Apple emoji) — same renderer
#    contract as the Lambda caption pipeline.
OVERLAY_PNG="$(mktemp -t clipspal-overlay.XXXXXX).png"
trap 'rm -f "$OVERLAY_PNG"' EXIT
python3 "$SCRIPT_DIR/render_overlay.py" \
  "$TEXT" "$OVERLAY_PNG" \
  --appearance outlined \
  --font-size 72 \
  --max-line-chars 22 \
  --position top \
  >/dev/null

# 2) Concat hook + broll (both normalized to 1080x1920), then overlay the PNG
#    during 0..HOOK_DUR only.
ffmpeg -hide_banner -loglevel error -y \
  -i "$HOOK" -i "$BROLL" -loop 1 -i "$OVERLAY_PNG" \
  -filter_complex "\
[0:v]${NORMALIZE}[hv]; \
[1:v]${NORMALIZE}[bv]; \
[hv][0:a?][bv][1:a?]concat=n=2:v=1:a=1[cv][ca]; \
[cv][2:v]overlay=0:0:enable='between(t,0,${HOOK_DUR})'[v]" \
  -map "[v]" -map "[ca]" \
  -c:v libx264 -pix_fmt yuv420p -preset veryfast -crf 20 \
  -c:a aac -b:a 192k -shortest \
  "$OUT"

echo "DONE:$OUT"
