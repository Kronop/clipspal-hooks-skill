#!/usr/bin/env python3
"""install_permissions.py — merge this skill's suggested allowlist into
<cwd>/.claude/settings.local.json so Claude Code stops prompting for every
bash/python step.

Run this yourself from your project root:

    ! python3 ${CLAUDE_SKILL_DIR}/scripts/install_permissions.py

Why "yourself" (via the `!` prefix): Claude Code's auto-mode classifier
hard-blocks Claude from writing settings.local.json (anti-prompt-injection
safeguard). You running it directly bypasses the classifier.

Behavior:
- Reads <cwd>/.claude/settings.local.json (creates dir + file if missing).
- Reads <skill>/reference/permissions-suggested.json.
- Unions permissions.allow (no duplicates, preserves your existing entries).
- Writes back with 2-space indent.
- Idempotent — safe to run repeatedly.
"""

from __future__ import annotations
import json
import os
import sys
from pathlib import Path


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    suggested = script_dir.parent / "reference" / "permissions-suggested.json"
    if not suggested.exists():
        print(f"error: {suggested} not found", file=sys.stderr)
        return 1

    with suggested.open() as f:
        new_allow = json.load(f).get("permissions", {}).get("allow", [])

    target = Path.cwd() / ".claude" / "settings.local.json"
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        try:
            with target.open() as f:
                settings = json.load(f)
        except json.JSONDecodeError as e:
            print(f"error: {target} is not valid JSON: {e}", file=sys.stderr)
            print("Fix the file by hand and re-run.", file=sys.stderr)
            return 1
    else:
        settings = {}

    perms = settings.setdefault("permissions", {})
    existing = perms.setdefault("allow", [])
    before = set(existing)
    merged = list(existing)
    added = 0
    for pat in new_allow:
        if pat not in before:
            merged.append(pat)
            before.add(pat)
            added += 1
    perms["allow"] = merged

    with target.open("w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")

    print(f"ok: {target}")
    print(f"added {added} new pattern{'s' if added != 1 else ''} "
          f"({len(merged)} total in permissions.allow)")
    if added == 0:
        print("(already up to date)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
