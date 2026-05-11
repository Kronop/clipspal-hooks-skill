#!/usr/bin/env bash
# check_prereqs.sh — verify all CLI dependencies BEFORE we spend fal credits.
#
# Usage: check_prereqs.sh
#
# Exit 0 if everything is ready. Exit 1 if anything is missing — and print
# the exact command to fix each missing piece so the caller can offer to
# run it.
#
# Checked:
#   - python3 in PATH
#   - Pillow importable from python3
#   - ffmpeg in PATH
#   - ffmpeg has the drawtext filter (i.e. built with libfreetype)
#   - ffprobe in PATH

set -uo pipefail

MISSING=0

check() {
  local label="$1"
  local cmd="$2"
  local fix="$3"
  if eval "$cmd" >/dev/null 2>&1; then
    printf "  [ok] %s\n" "$label"
  else
    printf "  [missing] %s\n    fix: %s\n" "$label" "$fix"
    MISSING=1
  fi
}

echo "Checking prerequisites…"

check "python3" \
  "command -v python3" \
  "install python3 from python.org or your package manager"

check "python3 has Pillow" \
  "python3 -c 'import PIL'" \
  "python3 -m pip install --user Pillow"

check "ffmpeg" \
  "command -v ffmpeg" \
  "brew install ffmpeg   # macOS  (or apt install ffmpeg on Linux)"

# We render the caption to a transparent PNG via render_overlay.py and
# composite with ffmpeg's `overlay` filter — both ship in the stock ffmpeg
# build. No need for ffmpeg-full / drawtext.
FFMPEG_FILTERS="$(ffmpeg -hide_banner -filters 2>/dev/null || true)"
check "ffmpeg has overlay filter" \
  "grep -qw overlay <<<\"\$FFMPEG_FILTERS\"" \
  "reinstall ffmpeg from your package manager — overlay ships with the stock build"

check "ffprobe" \
  "command -v ffprobe" \
  "ships with ffmpeg — fix ffmpeg install"

if [[ $MISSING -ne 0 ]]; then
  echo ""
  echo "One or more prerequisites are missing. Run the fix commands above, then re-run check_prereqs.sh."
  exit 1
fi

echo ""
echo "All prerequisites OK."
exit 0
