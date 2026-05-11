#!/usr/bin/env python3
"""state.py — single source of truth for the hook generation pipeline.

state.json shape:
{
  "project": "<name>",
  "created_at": "...",
  "matrix": "done|idle",
  "hooks": "done|idle",
  "characters": [{"n": 1, "status": "idle|pending|done|failed", "request_id": "...", "path": "..."}],
  "clips":  [{"n": 1, "status": "idle|pending|done|failed", "request_id": "...", "path": "..."}],
  "assembly": [{"n": 1, "status": "idle|done", "path": "..."}]
}

All writes go through this module with an exclusive flock on state.json.lock.
Reads are unlocked (atomic file replace on write).
"""

from __future__ import annotations
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl  # POSIX only
    _HAS_FCNTL = True
except ImportError:
    # Windows: degrade to no-locking. Concurrent fal_submit/fal_poll calls
    # in the same project dir could race, but the skill drives them
    # serially per slot so collisions are unlikely.
    _HAS_FCNTL = False

STATE_FILE = "state.json"
LOCK_FILE = "state.json.lock"
SLOT_COUNT = 5


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def empty_state(project: str = "") -> dict:
    return {
        "project": project,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "matrix": "idle",
        "hooks": "idle",
        "characters": [{"n": i + 1, "status": "idle"} for i in range(SLOT_COUNT)],
        "clips": [{"n": i + 1, "status": "idle"} for i in range(SLOT_COUNT)],
        "assembly": "idle",
    }


def state_path(project_dir: Path) -> Path:
    return project_dir / STATE_FILE


def lock_path(project_dir: Path) -> Path:
    return project_dir / LOCK_FILE


def read_state(project_dir: Path) -> dict:
    p = state_path(project_dir)
    if not p.exists():
        return empty_state()
    with open(p, "r") as f:
        return json.load(f)


@contextmanager
def locked(project_dir: Path):
    """Acquire an exclusive flock on state.json.lock, yield the current state,
    then atomically write whatever the caller mutated in the returned dict."""
    project_dir.mkdir(parents=True, exist_ok=True)
    lock = lock_path(project_dir)
    lock.touch(exist_ok=True)
    with open(lock, "r+") as lf:
        if _HAS_FCNTL:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            state = read_state(project_dir)
            yield state
            state["updated_at"] = utc_now()
            sp = state_path(project_dir)
            # atomic replace
            with tempfile.NamedTemporaryFile("w", dir=project_dir, delete=False) as tmp:
                json.dump(state, tmp, indent=2)
                tmp_name = tmp.name
            os.replace(tmp_name, sp)
        finally:
            if _HAS_FCNTL:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def get_slot(state: dict, kind: str, n: int) -> dict:
    if kind not in ("characters", "clips"):
        raise ValueError(f"unknown slot kind: {kind}")
    for slot in state[kind]:
        if slot["n"] == n:
            return slot
    raise KeyError(f"{kind} slot {n} not found")


def init_project(project_dir: Path, name: str) -> None:
    with locked(project_dir) as s:
        if not s.get("created_at") or s.get("project") != name:
            fresh = empty_state(name)
            s.clear()
            s.update(fresh)


def cmd_init(project_dir: Path, name: str) -> None:
    init_project(project_dir, name)
    print(f"initialized {project_dir}/state.json")


def cmd_show(project_dir: Path) -> None:
    s = read_state(project_dir)
    print(json.dumps(s, indent=2))


def cmd_summary(project_dir: Path) -> None:
    """One-line status summary for Claude to read before each step."""
    s = read_state(project_dir)
    parts = [f"matrix={s.get('matrix')}", f"hooks={s.get('hooks')}"]
    for kind in ("characters", "clips"):
        statuses = [slot["status"] for slot in s.get(kind, [])]
        done = sum(1 for x in statuses if x == "done")
        pending = sum(1 for x in statuses if x == "pending")
        failed = sum(1 for x in statuses if x == "failed")
        parts.append(f"{kind}=done:{done}/pending:{pending}/failed:{failed}/total:{len(statuses)}")
    parts.append(f"assembly={s.get('assembly')}")
    print(" | ".join(parts))


def cmd_set(project_dir: Path, key_path: str, value: str) -> None:
    """Set a top-level scalar field. Used for matrix/hooks status."""
    with locked(project_dir) as s:
        s[key_path] = value
    print(f"{key_path}={value}")


def cmd_reset(project_dir: Path, kind: str, n_spec: str) -> None:
    """Reset one or more slots to `idle` so the next fal_submit will rerun
    them. `n_spec` is a comma-separated list of 1-based slot numbers, or
    "all" to reset every slot of that kind.

    Use this for re-rolls: after the user rejects character 2 and 4 at
    the checkpoint, run `state.py reset characters 2,4` then re-submit.
    """
    if kind not in ("characters", "clips"):
        raise ValueError(f"reset only supports characters|clips, got: {kind}")
    with locked(project_dir) as s:
        if n_spec.strip() == "all":
            targets = [slot["n"] for slot in s[kind]]
        else:
            targets = [int(x) for x in n_spec.split(",") if x.strip()]
        for n in targets:
            slot = get_slot(s, kind, n)
            slot["status"] = "idle"
            for f in ("request_id", "model_id", "path", "submitted_at",
                     "completed_at", "error"):
                slot.pop(f, None)
    print(f"reset {kind}={n_spec}")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: state.py <init|show|summary|set|reset> [args...]", file=sys.stderr)
        return 2
    cmd = sys.argv[1]
    pd = Path(os.environ.get("PROJECT_DIR", "."))
    if cmd == "init":
        name = sys.argv[2] if len(sys.argv) > 2 else pd.name
        cmd_init(pd, name)
    elif cmd == "show":
        cmd_show(pd)
    elif cmd == "summary":
        cmd_summary(pd)
    elif cmd == "set":
        cmd_set(pd, sys.argv[2], sys.argv[3])
    elif cmd == "reset":
        cmd_reset(pd, sys.argv[2], sys.argv[3])
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
