#!/usr/bin/env bash
# check_broll.sh — validate the user's broll folder before we spend fal credits.
#
# Usage: check_broll.sh <broll_folder>
#
# Prints one usable file per line on stdout (mp4 / mov / m4v / webm).
# Exits 0 if at least one file is usable. Exits 1 with a stderr message if
# the folder is missing or empty.

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: check_broll.sh <broll_folder>" >&2
  exit 2
fi

DIR="$1"

if [[ ! -d "$DIR" ]]; then
  echo "Broll folder not found: $DIR" >&2
  exit 1
fi

USABLE=()
while IFS= read -r -d '' f; do
  USABLE+=("$f")
done < <(find "$DIR" -maxdepth 1 -type f \( \
    -iname "*.mp4" -o -iname "*.mov" -o -iname "*.m4v" -o -iname "*.webm" \
  \) ! -name ".*" -print0 | sort -z)

if [[ ${#USABLE[@]} -eq 0 ]]; then
  echo "No usable video files (.mp4/.mov/.m4v/.webm) in: $DIR" >&2
  echo "Add at least 1 broll clip to that folder and try again." >&2
  exit 1
fi

for f in "${USABLE[@]}"; do
  printf '%s\n' "$f"
done

echo "" >&2
echo "Found ${#USABLE[@]} broll file(s) in $DIR" >&2
exit 0
