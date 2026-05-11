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

# 2) Detect whether each input has an audio stream. Vidu i2v clips are
#    silent, and screen-recording b-roll often is too — concat with
#    `a=1` will explode if either side has no audio, so we generate
#    silence to fill the gap.
has_audio() {
  ffprobe -v error -select_streams a -show_entries stream=codec_type \
    -of default=nw=1:nk=1 "$1" 2>/dev/null | grep -q audio
}

HOOK_HAS_AUDIO=0
BROLL_HAS_AUDIO=0
has_audio "$HOOK"  && HOOK_HAS_AUDIO=1
has_audio "$BROLL" && BROLL_HAS_AUDIO=1

# Build the audio graph: normalize whatever audio exists, inject silence
# for whatever doesn't, then concat. Resample everything to 44.1k stereo
# so concat doesn't blow up on sample-rate mismatches.
AFMT='aresample=44100,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS'
if [[ "$HOOK_HAS_AUDIO" == 1 ]]; then
  HOOK_A="[0:a]${AFMT}[ha]"
else
  HOOK_A="anullsrc=channel_layout=stereo:sample_rate=44100,atrim=duration=${HOOK_DUR},${AFMT}[ha]"
fi
if [[ "$BROLL_HAS_AUDIO" == 1 ]]; then
  BROLL_A="[1:a]${AFMT}[ba]"
else
  BROLL_DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$BROLL")
  BROLL_A="anullsrc=channel_layout=stereo:sample_rate=44100,atrim=duration=${BROLL_DUR},${AFMT}[ba]"
fi

# 3) Concat hook + broll (both normalized to 1080x1920), then overlay the PNG
#    during 0..HOOK_DUR only.
ffmpeg -hide_banner -loglevel error -y \
  -i "$HOOK" -i "$BROLL" -loop 1 -i "$OVERLAY_PNG" \
  -filter_complex "\
[0:v]${NORMALIZE}[hv]; \
[1:v]${NORMALIZE}[bv]; \
${HOOK_A}; \
${BROLL_A}; \
[hv][ha][bv][ba]concat=n=2:v=1:a=1[cv][ca]; \
[cv][2:v]overlay=0:0:enable='between(t,0,${HOOK_DUR})'[v]" \
  -map "[v]" -map "[ca]" \
  -c:v libx264 -pix_fmt yuv420p -preset veryfast -crf 20 \
  -c:a aac -b:a 192k -shortest \
  "$OUT"

echo "DONE:$OUT"
