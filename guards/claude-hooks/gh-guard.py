#!/usr/bin/env python3
"""PreToolUse (Bash) dialog for `gh` commands that change GitHub or expose credentials.

permissions.ask rules for gh don't stop an agent in auto mode (the classifier decides instead),
which let `gh repo delete` through on 2026-11-20. Like the git pre-push guard, this opens a macOS
dialog and the command runs only when a human clicks Allow; Block or no answer in 5 min denies it.
Reads (view/list/status/diff/checks, `gh api` GETs) pass silently.

Pattern-based: catches accidents, not an agent set on getting around it (aliases, curl to the
API, scripts on disk). Keep the gh token's scopes small as the second layer.
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

LOG = os.path.join(os.path.expanduser("~"), ".claude", "leak-alerts.log")
DEBUG = os.environ.get("GH_GUARD_DEBUG") == "1"
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish"}
WRAPPERS = {"sudo", "time", "nice", "nohup", "command", "exec", "env", "timeout", "caffeinate", "builtin", "doas", "xargs"}

# subcommand -> actions that need a click. "*" = every action (all of them write or run code).
RISKY = {
	"repo": {"create", "delete", "archive", "unarchive", "rename", "edit", "sync", "fork", "set-default", "deploy-key", "autolink"},
	"pr": {"create", "merge", "close", "reopen", "edit", "ready", "comment", "review", "lock", "unlock", "update-branch", "revert"},
	"issue": {"create", "edit", "close", "reopen", "comment", "delete", "transfer", "lock", "unlock", "pin", "unpin", "develop"},
	"release": {"create", "delete", "edit", "upload", "delete-asset"},
	"workflow": {"run", "enable", "disable"},
	"run": {"rerun", "cancel", "delete"},
	"cache": {"delete"},
	"secret": {"set", "delete", "remove"},
	"variable": {"set", "delete", "remove"},
	"gist": {"create", "new", "edit", "delete", "rename"},
	"label": {"create", "edit", "delete", "clone"},
	"auth": {"token", "login", "refresh", "logout", "setup-git", "switch"},
	"ssh-key": {"add", "delete"},
	"gpg-key": {"add", "delete"},
	"codespace": {"create", "delete", "edit", "stop", "rebuild"},
	"project": {"create", "delete", "edit", "close", "copy", "link", "unlink", "item-add", "item-create", "item-edit", "item-delete", "item-archive", "field-create", "field-delete", "mark-template"},
	"extension": {"install", "upgrade", "remove", "exec", "create"},
	"ext": {"install", "upgrade", "remove", "exec", "create"},
	"alias": {"set", "delete", "import"},
	"config": {"set"},
	"attestation": set(),
	"ruleset": set(),
}
# Flags that take a value, so the value isn't mistaken for the subcommand.
VALUE_FLAGS = {"-R", "--repo", "--hostname", "-H"}
API_DATA = {"-f", "-F", "--field", "--raw-field", "--input"}


def log(event, **kw):
	try:
		with open(LOG, "a") as f:
			f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "hook": "gh-guard", "event": event, **kw}) + "\n")
	except Exception:
		pass


def statements(cmd):
	"""Top-level pieces split on ; && || | & and newlines, plus $(...) / `...` bodies."""
	subs = re.findall(r"\$\(([^()]*(?:\([^()]*\)[^()]*)*)\)", cmd) + re.findall(r"`([^`]*)`", cmd)
	parts, buf, quote, i = [], [], None, 0
	while i < len(cmd):
		c = cmd[i]
		if quote:
			buf.append(c)
			if c == quote:
				quote = None
			elif c == "\\" and quote == '"' and i + 1 < len(cmd):
				buf.append(cmd[i + 1])
				i += 1
			i += 1
			continue
		if c in "'\"":
			quote = c
		elif c in ";|&\n(){}":
			parts.append("".join(buf))
			buf = []
			i += 1
			continue
		buf.append(c)
		i += 1
	parts.append("".join(buf))
	return [p.strip() for p in parts if p.strip()], subs


def words_of(s):
	try:
		return shlex.split(s)
	except ValueError:
		return s.split()


def strip_prefix(words):
	while words:
		w = words[0]
		if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", w):
			words = words[1:]
			continue
		if os.path.basename(w) not in WRAPPERS:
			break
		words = words[1:]
		while words and words[0].startswith("-"):
			words = words[1:]
		if words and re.fullmatch(r"\d+[smhd]?", words[0]):  # timeout duration
			words = words[1:]
	return words


def check_api(args):
	method, data, graphql = None, False, False
	toks = iter(args)
	for t in toks:
		if t in ("-X", "--method"):
			method = (next(toks, "") or "").upper()
		elif t.startswith("--method="):
			method = t.split("=", 1)[1].upper()
		elif t.startswith("-X") and len(t) > 2:
			method = t[2:].upper()
		elif t in API_DATA or any(t.startswith(f + "=") for f in API_DATA if f.startswith("--")):
			data = True
		elif t == "graphql":
			graphql = True
	text = " ".join(args)
	if graphql:
		return "gh api graphql mutation" if re.search(r"\bmutation\b", text) else None
	if method and method != "GET":
		return f"gh api -X {method}"
	if data and method != "GET":
		return "gh api with -f/-F/--input (sends a POST)"
	return None


def check_gh(args):
	"""args: tokens after `gh`. Returns a short label of the risky action, or None."""
	rest = list(args)
	while rest and rest[0].startswith("-"):
		rest = rest[2:] if rest[0] in VALUE_FLAGS else rest[1:]
	if not rest:
		return None
	sub, tail = rest[0], rest[1:]
	if sub == "api":
		return check_api(tail)
	if sub not in RISKY:
		return None
	actions = [t for t in tail if not t.startswith("-")]
	action = actions[0] if actions else ""
	if sub in ("ruleset", "attestation"):
		return None
	if action in RISKY[sub]:
		return f"gh {sub} {action}"
	return None


def check(cmd, depth=0):
	if depth > 4 or not re.search(r"\bgh\b", cmd):
		return None
	parts, subs = statements(cmd)
	for s in subs:
		r = check(s, depth + 1)
		if r:
			return r
	for p in parts:
		words = strip_prefix(words_of(p))
		if not words:
			continue
		name = os.path.basename(words[0])
		if name in SHELLS:
			for k, w in enumerate(words[1:], 1):
				if re.fullmatch(r"-[a-zA-Z]*c[a-zA-Z]*", w) and k + 1 < len(words):
					r = check(words[k + 1], depth + 1)
					if r:
						return r
			continue
		if name == "eval":
			r = check(" ".join(words[1:]), depth + 1)
			if r:
				return r
			continue
		if name == "gh":
			r = check_gh(words[1:])
			if r:
				return r
	return None


def ask(label, cmd, cwd):
	"""Native dialog; True only on a click on Allow. Everything goes in as argv, never as AppleScript."""
	shown = cmd if len(cmd) <= 1500 else cmd[:1500] + " …"
	prompt = f"Claude Code wants to run {label}\n\nin {cwd}:\n\n{shown}"
	try:
		r = subprocess.run(["osascript",
			"-e", "on run argv",
			"-e", "display dialog (item 1 of argv) with title (item 2 of argv) buttons {\"Block\", \"Allow\"} default button \"Block\" cancel button \"Block\" with icon caution giving up after 300",
			"-e", "if gave up of result then return \"block\"",
			"-e", "return button returned of result",
			"-e", "end run", prompt, f"GitHub: {label}"],
			capture_output=True, text=True, timeout=310)
		return r.stdout.strip() == "Allow"
	except (OSError, subprocess.TimeoutExpired):
		return False


def main():
	try:
		data = json.load(sys.stdin)
		if data.get("tool_name", "Bash") != "Bash":
			sys.exit(0)
		cmd = (data.get("tool_input") or {}).get("command") or ""
		label = check(cmd)
		if not label:
			sys.exit(0)
		cwd = data.get("cwd") or os.getcwd()
		if ask(label, cmd, cwd):
			log("allow", command=cmd[:500], label=label)
			sys.exit(0)  # normal permission flow continues
		log("deny", command=cmd[:500], label=label)
		print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
			"permissionDecisionReason": f"gh-guard: blocked `{label}`: it needs a click on Allow in the dialog. Tell the user and wait; they either allow it on a retry or run it themselves."}}))
	except Exception:
		log("hook-error", error=traceback.format_exc()[-1500:])
		if DEBUG:
			raise
	sys.exit(0)


if __name__ == "__main__":
	main()
