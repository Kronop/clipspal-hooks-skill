#!/usr/bin/env python3
"""fal_submit.py — submit a single fal.ai job for a slot, atomically.

Usage:
  PROJECT_DIR=./myproj FAL_KEY=... \\
    fal_submit.py <kind> <n> <model_id> <params_json_file>

Where:
  kind        = characters | clips
  n           = 1..5 (slot number)
  model_id    = e.g. "fal-ai/gemini-3.1-flash-image-preview" or "fal-ai/vidu/q3/image-to-video"
  params_json = path to a JSON file containing the input payload

Exit codes:
  0   submitted (new request_id printed)
  10  ALREADY_DONE  (slot already finished; existing path printed)
  11  ALREADY_PENDING (existing request_id printed; caller should poll, NOT resubmit)
  20  submission failed (stderr explains)

NEVER call fal.ai HTTP/SDK directly. Always use this script. State.json is the
only authority on whether a slot has been submitted.
"""

from __future__ import annotations
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

import state  # local


FAL_QUEUE_BASE = "https://queue.fal.run"
KEY_FILE = os.path.expanduser("~/.clipspal/fal_key")


def resolve_fal_key() -> str | None:
    """Read FAL_KEY from env, then from ~/.clipspal/fal_key. Returns None
    if neither is set. fal_key.sh writes/reads the same file."""
    env_key = os.environ.get("FAL_KEY")
    if env_key:
        return env_key.strip()
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, "r") as f:
                return f.read().strip()
        except OSError:
            return None
    return None


def submit_fal(model_id: str, input_payload: dict, api_key: str) -> dict:
    url = f"{FAL_QUEUE_BASE}/{model_id}"
    body = json.dumps(input_payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"fal submit failed: HTTP {e.code} {msg}") from None


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "usage: fal_submit.py <kind> <n> <model_id> <params_json_file>",
            file=sys.stderr,
        )
        return 2

    kind = sys.argv[1]
    n = int(sys.argv[2])
    model_id = sys.argv[3]
    params_file = Path(sys.argv[4])

    if kind not in ("characters", "clips"):
        print(f"kind must be characters|clips, got: {kind}", file=sys.stderr)
        return 2

    api_key = resolve_fal_key()
    if not api_key:
        print(
            "FAL_KEY not set and ~/.clipspal/fal_key does not exist. "
            "Run: bash ${CLAUDE_SKILL_DIR}/scripts/fal_key.sh save <key>",
            file=sys.stderr,
        )
        return 2

    project_dir = Path(os.environ.get("PROJECT_DIR", "."))
    if not params_file.exists():
        print(f"params file not found: {params_file}", file=sys.stderr)
        return 2

    with open(params_file, "r") as f:
        payload = json.load(f)

    # Phase 1: under lock, check current status. Decide whether to submit.
    with state.locked(project_dir) as s:
        slot = state.get_slot(s, kind, n)
        st = slot.get("status", "idle")
        if st == "done":
            print(f"ALREADY_DONE:{slot.get('path', '')}")
            return 10
        if st == "pending" and slot.get("request_id"):
            print(f"ALREADY_PENDING:{slot['request_id']}")
            return 11
        # idle or failed: mark as "submitting" with the model so subsequent
        # poll calls know what endpoint to hit
        slot["status"] = "submitting"
        slot["model_id"] = model_id
        slot.pop("request_id", None)
        slot.pop("error", None)

    # Phase 2: actually call fal (outside the lock).
    try:
        resp = submit_fal(model_id, payload, api_key)
        request_id = resp.get("request_id")
        if not request_id:
            raise RuntimeError(f"fal response missing request_id: {resp}")
    except Exception as e:
        with state.locked(project_dir) as s:
            slot = state.get_slot(s, kind, n)
            slot["status"] = "failed"
            slot["error"] = str(e)
        print(f"submit error: {e}", file=sys.stderr)
        return 20

    # Phase 3: persist pending state with the request_id.
    with state.locked(project_dir) as s:
        slot = state.get_slot(s, kind, n)
        slot["status"] = "pending"
        slot["request_id"] = request_id
        slot["model_id"] = model_id
        slot["submitted_at"] = state.utc_now()

    print(f"SUBMITTED:{request_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
