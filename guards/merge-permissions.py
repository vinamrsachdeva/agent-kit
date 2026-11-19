#!/usr/bin/env python3
"""Add claude-permissions.json's ask/deny rules, and agent-kit's PreToolUse hooks, to Claude Code settings files.

  merge-permissions.py <settings.json>...

Union only: rules already in a settings file stay, so per-profile extras survive. A file whose
rules change is backed up to <settings.json>.bak-agent-kit first. Safe to re-run.
"""

import json
import shutil
import sys
from pathlib import Path

RULES = json.loads((Path(__file__).resolve().parent / "claude-permissions.json").read_text())
# Hooks wired in by install (kill-guard is still wired by hand; see README).
HOOKS = [
    {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 -I ~/.claude/hooks/push-guard.py", "timeout": 15}]},
    # Waits up to 5 min for a click in its dialog.
    {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 -I ~/.claude/hooks/gh-guard.py", "timeout": 320}]},
]

for arg in sys.argv[1:]:
    path = Path(arg).expanduser()
    if not path.exists():
        print(f"skip {path}: no such file")
        continue
    settings = json.loads(path.read_text())
    perms = settings.setdefault("permissions", {})
    added = 0
    for kind, rules in RULES.items():
        have = perms.setdefault(kind, [])
        new = [r for r in rules if r not in have]
        have.extend(new)
        added += len(new)
    pre = settings.setdefault("hooks", {}).setdefault("PreToolUse", [])
    wired = {h.get("command") for e in pre for h in e.get("hooks", [])}
    for entry in HOOKS:
        if entry["hooks"][0]["command"] not in wired:
            pre.append(entry)
            added += 1
    if not added:
        print(f"{path}: permissions and hooks up to date")
        continue
    shutil.copy2(path, f"{path}.bak-agent-kit")
    path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
    print(f"{path}: added {added} permission rules / hooks (backup: {path}.bak-agent-kit)")
