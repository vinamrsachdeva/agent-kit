#!/usr/bin/env python3
"""PreToolUse (Bash) guard against killing processes by name / pattern.

Policy (Vin, 2026-11-10), after `pkill -f "cat"` matched every app under /Applications:
- DENY: pkill, killall, fuser -k, launchctl kill|bootout, osascript "quit".
- DENY: kill aimed at pid 0/1, negative pids (process groups), or pids found by a search
  (pgrep/pidof/ps/grep, incl. via $(...) or `| xargs kill`).
- DENY: kill fed by `lsof` without `-sTCP:LISTEN` (`lsof -ti:3000` also returns browsers connected to the port).
- ALLOW: kill [-SIG] <literal pid | $var | %job>, pids from a pidfile, `lsof -ti tcp:N -sTCP:LISTEN`.
A hook deny blocks even under --dangerously-skip-permissions.

Pattern-based: catches accidents, not an agent deliberately hiding a kill. Hard guarantee = sandbox.
Fail-open: a crash allows the call and logs to ~/.claude/leak-alerts.log.
"""
import json
import os
import re
import shlex
import sys
import time
import traceback

LOG = os.path.join(os.path.expanduser("~"), ".claude", "leak-alerts.log")
DEBUG = os.environ.get("KILL_GUARD_DEBUG") == "1"

TRIGGER = re.compile(r"kill|fuser|launchctl|osascript")
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish"}
WRAPPERS = {"sudo", "time", "nice", "nohup", "command", "exec", "env", "timeout", "caffeinate", "builtin", "doas"}
XARGS_ARG_OPTS = {"-I", "-n", "-P", "-L", "-d", "-E", "-s", "-J", "-R", "-S"}
PID_SEARCH = re.compile(r"\b(pgrep|pidof|ps|grep|rg|awk)\b")
HINT = "Find the exact process first: `pgrep -fl '<pattern>'` (or `ps -p <pid> -o pid,command`), check the list, then `kill <PID>`."


def log(event, **kw):
	try:
		with open(LOG, "a") as f:
			f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "hook": "kill-guard", "event": event, **kw}) + "\n")
	except Exception:
		pass


def strip_heredocs(cmd):
	"""Drop heredoc bodies (file contents being written), unless the heredoc feeds a shell."""
	lines, out, i = cmd.split("\n"), [], 0
	while i < len(lines):
		line = lines[i]
		out.append(line)
		m = re.search(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?", line)
		i += 1
		if not m:
			continue
		head = line[:m.start()].split()
		feeds_shell = bool(head) and os.path.basename(head[0]) in SHELLS
		body = []
		while i < len(lines) and lines[i].strip() != m.group(1):
			body.append(lines[i])
			i += 1
		i += 1  # terminator
		if feeds_shell:
			out.extend(body)
	return "\n".join(out)


def lex(cmd):
	"""Split into statements (list of pipeline stages) at top level; collect $(...) / `...` bodies."""
	statements, stages, buf, subs = [], [], [], []
	i, n, quote = 0, len(cmd), None

	def flush_stage():
		s = "".join(buf).strip()
		buf.clear()
		if s:
			stages.append(s)

	def flush_stmt():
		flush_stage()
		if stages:
			statements.append(stages.copy())
			stages.clear()

	while i < n:
		c = cmd[i]
		if quote == "'":
			buf.append(c)
			if c == "'":
				quote = None
			i += 1
			continue
		if c == "\\" and i + 1 < n:
			buf.append(cmd[i:i + 2])
			i += 2
			continue
		if c == "$" and cmd[i + 1:i + 2] == "(" and cmd[i + 2:i + 3] != "(":
			depth, j = 1, i + 2
			while j < n and depth:
				depth += {"(": 1, ")": -1}.get(cmd[j], 0)
				j += 1
			subs.append(cmd[i + 2:j - 1])
			buf.append(cmd[i:j])
			i = j
			continue
		if c == "`":
			j = cmd.find("`", i + 1)
			j = n if j == -1 else j
			subs.append(cmd[i + 1:j])
			buf.append(cmd[i:j + 1])
			i = j + 1
			continue
		if quote == '"':
			buf.append(c)
			if c == '"':
				quote = None
			i += 1
			continue
		if c in "'\"":
			quote = c
			buf.append(c)
			i += 1
			continue
		two = cmd[i:i + 2]
		if two in ("&&", "||"):
			flush_stmt()
			i += 2
			continue
		if c in ";\n" or (c == "&" and (i == 0 or cmd[i - 1] not in "<>") and cmd[i + 1:i + 2] != ">"):
			flush_stmt()
			i += 1
			continue
		if c == "|" and (i == 0 or cmd[i - 1] != ">"):
			flush_stage()
			i += 2 if two == "|&" else 1
			continue
		if c in "({}" and not "".join(buf).strip():
			i += 1  # subshell / group opener
			continue
		buf.append(c)
		i += 1
	flush_stmt()
	return statements, subs


def words_of(stage):
	try:
		return shlex.split(stage)
	except ValueError:
		return stage.split()


def strip_prefix(words):
	"""Drop env assignments and wrapper commands (with their options)."""
	while words:
		w = words[0]
		if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", w):
			words = words[1:]
			continue
		name = os.path.basename(w)
		if name not in WRAPPERS:
			break
		words = words[1:]
		if name == "timeout":
			while words and words[0].startswith("-"):
				words = words[1 + (words[0] in ("-s", "-k", "--signal", "--kill-after")):]
			words = words[1:]  # duration
		elif name in ("nice", "sudo", "doas"):
			while words and words[0].startswith("-"):
				words = words[1 + (words[0] in ("-n", "-u", "-g", "-C", "-h", "-p")):]
		else:
			while words and words[0].startswith("-"):
				words = words[1:]
	return words


def lsof_unsafe(text):
	return bool(re.search(r"\blsof\b", text)) and "-sTCP:LISTEN" not in text


def check_kill(args, raw_args, upstream):
	"""args: tokens after `kill`. raw_args: raw text after `kill`. upstream: text piped in (xargs) or ''."""
	feed = raw_args + " " + upstream
	if PID_SEARCH.search(feed):
		return f"`kill` with pids from a process search (pgrep/ps/grep) can hit unrelated processes. {HINT}"
	if lsof_unsafe(feed):
		return ("`lsof -t -i:<port>` also returns clients connected to the port (e.g. your browser). "
			"Use `lsof -ti tcp:<port> -sTCP:LISTEN` to get only the server.")
	seen_sig, only_dashdash = False, False
	toks = iter(args)
	for t in toks:
		if "$(" in t or "`" in t or t.endswith(")"):
			continue
		if not only_dashdash:
			if t in ("-l", "-L"):
				return None
			if t in ("-s", "-n"):
				next(toks, None)
				seen_sig = True
				continue
			if t == "--":
				only_dashdash = True
				continue
			if t.startswith("-") and not seen_sig:
				seen_sig = True
				continue
		if re.fullmatch(r"-?\d+", t) and int(t) <= 1:
			return f"`kill {t}` targets a whole process group / every process / launchd. {HINT}"
	return None


def check_stage(words, raw, upstream, depth):
	words = strip_prefix(words)
	if not words:
		return None
	name = os.path.basename(words[0])
	rest = words[1:]
	if name in SHELLS:
		for k, w in enumerate(rest):
			if re.fullmatch(r"-[a-zA-Z]*c[a-zA-Z]*", w) and k + 1 < len(rest):
				return check(rest[k + 1], depth + 1)
		return None
	if name == "eval":
		return check(" ".join(rest), depth + 1)
	if name == "xargs":
		k = 0
		while k < len(rest) and rest[k].startswith("-"):
			k += 2 if rest[k] in XARGS_ARG_OPTS else 1
		inner = rest[k:]
		if not inner:
			return None
		up = upstream or "<stdin>"
		return check_stage(inner, shlex.join(inner), up, depth)
	if name in ("pkill", "killall"):
		return f"`{name}` matches by name/pattern and can kill unrelated apps (`pkill -f cat` matches /Appli*cat*ions). {HINT}"
	if name == "fuser" and any(re.fullmatch(r"-[a-zA-Z]*k[a-zA-Z]*", w) for w in rest):
		return f"`fuser -k` kills every process using the file/port. {HINT}"
	if name == "launchctl" and rest[:1] and rest[0] in ("kill", "bootout"):
		return f"`launchctl {rest[0]}` stops system/user services. Ask Vin first."
	if name == "osascript" and re.search(r"\bquit\b", raw, re.I):
		return "osascript `quit` closes Mac apps. Ask Vin first."
	if name == "kill":
		m = re.search(r"\bkill\b", raw)
		raw_args = raw[m.end():] if m else " ".join(rest)
		return check_kill(rest, raw_args, upstream)
	return None


def check(cmd, depth=0):
	if depth > 4 or not TRIGGER.search(cmd):
		return None
	statements, subs = lex(strip_heredocs(cmd))
	for sub in subs:
		r = check(sub, depth + 1)
		if r:
			return r
	for stages in statements:
		for k, stage in enumerate(stages):
			upstream = " | ".join(stages[:k])
			r = check_stage(words_of(stage), stage, upstream, depth)
			if r:
				return r
	return None


def main():
	try:
		data = json.load(sys.stdin)
		if data.get("tool_name", "Bash") != "Bash":
			sys.exit(0)
		cmd = (data.get("tool_input") or {}).get("command") or ""
		reason = check(cmd)
		if reason:
			log("deny", command=cmd[:500], reason=reason[:200])
			print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
				"permissionDecision": "deny", "permissionDecisionReason": f"kill-guard: {reason}"}}))
	except Exception:
		log("hook-error", error=traceback.format_exc()[-1500:])
		if DEBUG:
			raise
	sys.exit(0)


if __name__ == "__main__":
	main()
