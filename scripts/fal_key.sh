#!/usr/bin/env bash
# fal_key.sh — resolve the user's fal.ai API key from one of:
#   1. $FAL_KEY env var (already exported)
#   2. ~/.clipspal/fal_key (persisted from a previous session)
#
# Usage:
#   eval "$(bash fal_key.sh load)"      # exports FAL_KEY for this shell
#   bash fal_key.sh save <key>          # persists <key> to ~/.clipspal/fal_key
#   bash fal_key.sh check               # exit 0 if resolvable, 1 otherwise
#
# We never echo the key on stdout except in the explicit `load` form, which
# is meant to be eval'd. `save` and `check` only print booleans / status.

set -euo pipefail

CONFIG_DIR="$HOME/.clipspal"
KEY_FILE="$CONFIG_DIR/fal_key"

cmd="${1:-load}"

case "$cmd" in
  load)
    if [[ -n "${FAL_KEY:-}" ]]; then
      printf 'export FAL_KEY=%q\n' "$FAL_KEY"
      exit 0
    fi
    if [[ -f "$KEY_FILE" ]]; then
      key="$(cat "$KEY_FILE")"
      printf 'export FAL_KEY=%q\n' "$key"
      exit 0
    fi
    echo "FAL_KEY not set and ~/.clipspal/fal_key does not exist." >&2
    echo "Ask the user for their fal.ai key (https://fal.ai/dashboard/keys)" >&2
    echo "and run: bash fal_key.sh save <key>" >&2
    exit 1
    ;;
  save)
    if [[ $# -lt 2 ]]; then
      echo "usage: fal_key.sh save <key>" >&2
      exit 2
    fi
    mkdir -p "$CONFIG_DIR"
    chmod 700 "$CONFIG_DIR"
    printf '%s' "$2" > "$KEY_FILE"
    chmod 600 "$KEY_FILE"
    echo "saved to $KEY_FILE (chmod 600)"
    ;;
  check)
    if [[ -n "${FAL_KEY:-}" ]] || [[ -f "$KEY_FILE" ]]; then
      echo "ok"
      exit 0
    fi
    echo "missing"
    exit 1
    ;;
  *)
    echo "unknown command: $cmd  (use load|save|check)" >&2
    exit 2
    ;;
esac
