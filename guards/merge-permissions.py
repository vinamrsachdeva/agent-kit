#!/usr/bin/env python3
"""Add claude-permissions.json's ask/deny rules to Claude Code settings files.

  merge-permissions.py <settings.json>...

Union only: rules already in a settings file stay, so per-profile extras survive. A file whose
rules change is backed up to <settings.json>.bak-agent-kit first. Safe to re-run.
"""

import json
import shutil
import sys
from pathlib import Path

RULES = json.loads((Path(__file__).resolve().parent / "claude-permissions.json").read_text())

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
    if not added:
        print(f"{path}: permissions up to date")
        continue
    shutil.copy2(path, f"{path}.bak-agent-kit")
    path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
    print(f"{path}: added {added} permission rules (backup: {path}.bak-agent-kit)")
