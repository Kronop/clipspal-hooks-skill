#!/usr/bin/env python3
"""fal_poll.py — poll a pending fal job and download its artifact when ready.

Usage:
  PROJECT_DIR=./myproj FAL_KEY=... \\
    fal_poll.py <kind> <n>

  kind = frames | clips
  n    = 1..5

Exit codes:
  0   done (path printed)
  1   still pending (status printed)
  10  ALREADY_DONE
  20  failed (error written into state)

Polls with linear backoff up to FAL_POLL_TIMEOUT seconds (default 600).
Idempotent — safe to re-run after a Ctrl-C or stale process.
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

import state


FAL_QUEUE_BASE = "https://queue.fal.run"
DEFAULT_TIMEOUT = int(os.environ.get("FAL_POLL_TIMEOUT", "600"))
POLL_INTERVAL = float(os.environ.get("FAL_POLL_INTERVAL", "4"))
KEY_FILE = os.path.expanduser("~/.clipspal/fal_key")


def resolve_fal_key() -> str | None:
    """Read FAL_KEY from env, then from ~/.clipspal/fal_key."""
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


def fal_get(url: str, api_key: str, retries: int = 4) -> dict:
    """GET with retries on transient network errors (URLError, socket.timeout,
    HTTP 5xx). Raises on definitive 4xx (auth / not-found) so the caller marks
    the slot failed."""
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Key {api_key}"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if 500 <= e.code < 600:
                last_err = e
                time.sleep(2 ** attempt)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_err = e
            time.sleep(2 ** attempt)
            continue
    raise RuntimeError(f"fal_get exhausted retries: {last_err}")


def app_root(model_id: str) -> str:
    """fal queue status/result endpoints use only the app root (first two
    slash-separated segments), not the full model path. e.g.
    `fal-ai/vidu/q3/image-to-video` -> `fal-ai/vidu`."""
    parts = model_id.split("/")
    if len(parts) >= 2:
        return "/".join(parts[:2])
    return model_id


def fal_status(model_id: str, request_id: str, api_key: str) -> dict:
    return fal_get(f"{FAL_QUEUE_BASE}/{app_root(model_id)}/requests/{request_id}/status", api_key)


def fal_result(model_id: str, request_id: str, api_key: str) -> dict:
    return fal_get(f"{FAL_QUEUE_BASE}/{app_root(model_id)}/requests/{request_id}", api_key)


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=300) as resp:
        with open(tmp, "wb") as f:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
    os.replace(tmp, dest)


def extract_artifact_url(kind: str, result: dict) -> str:
    """fal response shapes vary by model — pluck the right url."""
    # nano-banana: {"images": [{"url": "..."}]}
    # vidu i2v:    {"video": {"url": "..."}}
    if kind == "frames":
        images = result.get("images") or []
        if images and isinstance(images, list):
            url = images[0].get("url")
            if url:
                return url
        # fallback: some endpoints use "image"
        img = result.get("image")
        if isinstance(img, dict) and img.get("url"):
            return img["url"]
    elif kind == "clips":
        vid = result.get("video")
        if isinstance(vid, dict) and vid.get("url"):
            return vid["url"]
        if isinstance(vid, str):
            return vid
    raise RuntimeError(f"could not find artifact url in result: {json.dumps(result)[:400]}")


def dest_path(project_dir: Path, kind: str, n: int) -> Path:
    if kind == "frames":
        return project_dir / "frames" / f"{n:02d}.png"
    if kind == "clips":
        return project_dir / "clips" / f"{n:02d}.mp4"
    raise ValueError(kind)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: fal_poll.py <kind> <n>", file=sys.stderr)
        return 2
    kind = sys.argv[1]
    n = int(sys.argv[2])
    if kind not in ("frames", "clips"):
        print(f"kind must be frames|clips, got: {kind}", file=sys.stderr)
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

    # Read slot (no lock — we only need request_id + model_id)
    s = state.read_state(project_dir)
    slot = state.get_slot(s, kind, n)
    st = slot.get("status")
    if st == "done":
        print(f"ALREADY_DONE:{slot.get('path', '')}")
        return 10
    if st not in ("pending",):
        print(f"slot not pending (status={st}); nothing to poll", file=sys.stderr)
        return 2

    request_id = slot.get("request_id")
    model_id = slot.get("model_id")
    if not request_id or not model_id:
        print("slot missing request_id/model_id", file=sys.stderr)
        return 2

    deadline = time.time() + DEFAULT_TIMEOUT
    last_status = "?"
    while time.time() < deadline:
        try:
            sresp = fal_status(model_id, request_id, api_key)
        except urllib.error.HTTPError as e:
            print(f"status http {e.code}, retrying", file=sys.stderr)
            time.sleep(POLL_INTERVAL)
            continue
        last_status = sresp.get("status", "?")
        if last_status == "COMPLETED":
            break
        if last_status in ("FAILED", "CANCELLED", "ERROR"):
            with state.locked(project_dir) as s2:
                slot2 = state.get_slot(s2, kind, n)
                slot2["status"] = "failed"
                slot2["error"] = json.dumps(sresp)[:600]
            print(f"FAILED:{last_status}", file=sys.stderr)
            return 20
        time.sleep(POLL_INTERVAL)
    else:
        print(f"timeout, last status={last_status}", file=sys.stderr)
        return 1

    # Fetch result + download artifact
    result = fal_result(model_id, request_id, api_key)
    url = extract_artifact_url(kind, result)
    out = dest_path(project_dir, kind, n)
    download(url, out)

    with state.locked(project_dir) as s2:
        slot2 = state.get_slot(s2, kind, n)
        slot2["status"] = "done"
        slot2["path"] = str(out.relative_to(project_dir))
        slot2["completed_at"] = state.utc_now()

    print(f"DONE:{out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
