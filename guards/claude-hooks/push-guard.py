#!/usr/bin/env python3
"""PreToolUse (Bash) check that agent-kit's push guard will actually run on a `git push`.

A repo's own core.hooksPath beats the global one, so in such a repo git skips agent-kit's pre-push
and an agent's push goes out with no dialog. This denies the push unless git's hooks folder for
the repo is agent-kit's, or that folder's pre-push carries the block repo-push-guard.sh adds.

Pattern-based: catches accidents, not an agent set on getting around it.
Fail-open: a crash allows the call and logs to ~/.claude/leak-alerts.log.
"""
import json
import os
import re
import shlex
import subprocess
import sys
import time
import traceback

HOME = os.path.expanduser("~")
LOG = os.path.join(HOME, ".claude", "leak-alerts.log")
GLOBAL = os.path.join(HOME, ".config", "git", "hooks")
MARK = "agent-kit push guard"
FIX = "~/git/agent-kit/guards/repo-push-guard.sh"

# `git [opts] push`, with -C <dir> picked up; one statement at a time.
GIT_PUSH = re.compile(r"(?:^|[;&|(\s])git((?:\s+-[-\w.=]+(?:\s+(?!push\b)[^\s;&|-]\S*)?)*)\s+push\b")
CD = re.compile(r"(?:^|[;&|(]\s*)cd\s+(\"[^\"]+\"|'[^']+'|[^\s;&|]+)")


def log(event, **kw):
	try:
		with open(LOG, "a") as f:
			f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "hook": "push-guard", "event": event, **kw}) + "\n")
	except Exception:
		pass


def unquote(s):
	try:
		return shlex.split(s)[0]
	except (ValueError, IndexError):
		return s


def push_dirs(cmd, cwd):
	"""Directory each `git push` in cmd runs in, following `cd` and `git -C`."""
	dirs = []
	for m in GIT_PUSH.finditer(cmd):
		d = cwd
		cds = list(CD.finditer(cmd[:m.start() + 1]))
		if cds:
			d = os.path.join(cwd, os.path.expanduser(unquote(cds[-1].group(1))))
		c = re.search(r"-C\s+(\"[^\"]+\"|'[^']+'|\S+)", m.group(1))
		if c:
			d = os.path.join(d, os.path.expanduser(unquote(c.group(1))))
		dirs.append(d)
	return dirs


def problem(d):
	git = lambda *a: subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, timeout=5)
	r = git("rev-parse", "--show-toplevel")
	if r.returncode:
		return None
	top = r.stdout.strip()
	hp = subprocess.run(["git", "rev-parse", "--git-path", "hooks"], cwd=top, capture_output=True, text=True, timeout=5).stdout.strip()
	hooks = os.path.realpath(os.path.join(top, hp))
	if hooks == os.path.realpath(GLOBAL):
		return None
	try:
		with open(os.path.join(hooks, "pre-push")) as f:
			if MARK in f.read():
				return None
	except OSError:
		pass
	return (f"{top} keeps its git hooks in {hooks}, which hides agent-kit's push guard, so this push "
		f"would skip the user's Push dialog. Ask the user to run `{FIX} {top}` (or allow you to), then push again.")


def main():
	try:
		data = json.load(sys.stdin)
		if data.get("tool_name", "Bash") != "Bash":
			sys.exit(0)
		cmd = (data.get("tool_input") or {}).get("command") or ""
		if "push" not in cmd:
			sys.exit(0)
		cwd = data.get("cwd") or os.getcwd()
		for d in push_dirs(cmd, cwd):
			reason = problem(d)
			if reason:
				log("deny", command=cmd[:500], dir=d)
				print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
					"permissionDecision": "deny", "permissionDecisionReason": f"push-guard: {reason}"}}))
				break
	except Exception:
		log("hook-error", error=traceback.format_exc()[-1500:])
	sys.exit(0)


if __name__ == "__main__":
	main()
