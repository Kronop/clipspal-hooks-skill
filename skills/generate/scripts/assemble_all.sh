#!/usr/bin/env bash
# assemble_all.sh — assemble every final output for a project in parallel.
#
# Reads the project's hooks.json + clips/ + the broll folder, then for each
# hook n in hooks.json runs assemble.sh with:
#   - clip:    one of <project>/clips/*.mp4, round-robin'd. With the
#              default flow (5 clips × 30 hooks) each clip plays under
#              6 different hook captions. If only one clip exists it
#              fans out across every output.
#   - broll:   the n-th broll file from the supplied folder, round-robin
#              (reuses from the top if fewer broll files than hooks)
#   - hook:    the `text` field of hooks.json[n-1]
#   - out:     <project>/output/<NN>.mp4
#
# Why this exists: the previous runbook asked the LLM to drive this loop in
# the user's shell. zsh's 1-indexed arrays vs bash's 0-indexed arrays caused
# off-by-one bugs where hook 1 landed on video 2 and hook 5 was dropped.
# Moving the loop into a single bash script eliminates that whole class of
# bug.
#
# Usage:
#   assemble_all.sh <project_dir> <broll_folder>
#
# Requires: jq, ffmpeg, ffprobe, python3+Pillow, assemble.sh next to this file.

set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: assemble_all.sh <project_dir> <broll_folder>" >&2
  exit 2
fi

PROJECT_DIR="$1"
BROLL_DIR="$2"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

[[ -f "$PROJECT_DIR/hooks.json" ]] || { echo "missing $PROJECT_DIR/hooks.json" >&2; exit 1; }
[[ -d "$BROLL_DIR"             ]] || { echo "broll folder not found: $BROLL_DIR" >&2; exit 1; }

mkdir -p "$PROJECT_DIR/output"

# Collect broll files (mp4/mov/m4v/webm), sorted, deterministic order.
BROLL_FILES=()
while IFS= read -r -d '' f; do
  BROLL_FILES+=("$f")
done < <(find "$BROLL_DIR" -maxdepth 1 -type f \( \
    -iname "*.mp4" -o -iname "*.mov" -o -iname "*.m4v" -o -iname "*.webm" \
  \) ! -name ".*" -print0 | sort -z)

if [[ ${#BROLL_FILES[@]} -eq 0 ]]; then
  echo "no broll files in $BROLL_DIR" >&2
  exit 1
fi

# Hook count + texts via python (no jq dependency).
HOOK_COUNT=$(python3 -c "import json,sys; print(len(json.load(open(sys.argv[1]))))" "$PROJECT_DIR/hooks.json")

if [[ "$HOOK_COUNT" -eq 0 ]]; then
  echo "hooks.json has zero hooks" >&2
  exit 1
fi

# Collect available clip files (sorted, deterministic), then round-robin
# across however many we found. Handles 1 clip (fan-out), 5 clips
# (default — each plays under 6 hooks), or any other count.
CLIP_FILES=()
while IFS= read -r -d '' f; do
  CLIP_FILES+=("$f")
done < <(find "$PROJECT_DIR/clips" -maxdepth 1 -type f -iname "*.mp4" ! -name ".*" -print0 2>/dev/null | sort -z)

if [[ ${#CLIP_FILES[@]} -eq 0 ]]; then
  echo "no clips in $PROJECT_DIR/clips/" >&2
  exit 1
fi

pids=()
for ((i=0; i<HOOK_COUNT; i++)); do
  n=$((i+1))
  nn=$(printf '%02d' "$n")

  CLIP="${CLIP_FILES[$(( i % ${#CLIP_FILES[@]} ))]}"

  # Round-robin broll.
  BROLL="${BROLL_FILES[$(( i % ${#BROLL_FILES[@]} ))]}"

  # Hook text — read from JSON, NEVER from a shell array (this is the bug
  # this script exists to prevent).
  HOOK_TEXT=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))[int(sys.argv[2])]['text'])" \
    "$PROJECT_DIR/hooks.json" "$i")

  OUT="$PROJECT_DIR/output/$nn.mp4"

  bash "$SCRIPT_DIR/assemble.sh" "$CLIP" "$BROLL" "$HOOK_TEXT" "$OUT" &
  pids+=($!)
done

# Wait for all assemblies, fail loudly if any did.
rc=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    rc=1
  fi
done

if [[ $rc -ne 0 ]]; then
  echo "one or more assemblies failed" >&2
  exit $rc
fi

echo "DONE: $HOOK_COUNT outputs in $PROJECT_DIR/output/"
