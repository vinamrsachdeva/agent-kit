#!/usr/bin/env python3
"""Scan what is staged for commit for secrets. Exit 1 and name file:line + kind on a hit, never the value.

Detectors, all that are available:
- gitleaks, when installed (the broadest rule set).
- ~/.claude/hooks/secretlib.py, when present: your own secrets by hash, plus vendor key shapes.
- The built-in patterns below, so the hook catches the common shapes on any machine.
Also refuses staged files that are secrets by name (.env, private keys).
"""
import importlib.util
import os
import re
import shutil
import subprocess
import sys

BUILTIN = [
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY")),
    ("aws-key-id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}")),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("azure-account-key", re.compile(r"(?i)AccountKey=[A-Za-z0-9+/]{40,}")),
    ("db-url-password", re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|rediss?)://[^\s:/@]+:[^\s@/$<{]{6,}@")),
]
SECRET_NAMES = re.compile(r"(^|/)(\.env(\.[\w.-]+)?|id_(rsa|ed25519|ecdsa|dsa)|[^/]+\.(pem|p12|pfx|key))$")
SAFE_NAMES = re.compile(r"\.(example|sample|template|dist)$|\.pub$")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, errors="replace").stdout


def added_lines():
    """(path, line number, text) for every line the staged diff adds."""
    path, n = None, 0
    for line in git("diff", "--cached", "-U0", "--no-color", "--no-ext-diff", "--diff-filter=ACMR").splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            n = int(m.group(1)) if m else 0
        elif line.startswith("+") and path:
            yield path, n, line[1:]
            n += 1


def secretlib():
    p = os.path.expanduser("~/.claude/hooks/secretlib.py")
    if not os.path.exists(p):
        return None
    spec = importlib.util.spec_from_file_location("secretlib", p)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def main():
    hits = []
    for f in git("diff", "--cached", "--name-only", "--diff-filter=ACR").splitlines():
        if SECRET_NAMES.search(f) and not SAFE_NAMES.search(f):
            hits.append(f"{f}: a secrets file by its name")
    lib = secretlib()
    seen = {}
    for path, n, text in added_lines():
        kinds = {k for k, rx in BUILTIN if rx.search(text)}
        seen[path] = seen.get(path, 0) + 1
        # secretlib hashes every token; past 20k lines a file is data, so keep to the cheap patterns.
        if lib and seen[path] <= 20000 and len(text) < 10000:
            kinds |= set(lib.redact_text(text)[1])
        for k in sorted(kinds):
            hits.append(f"{path}:{n}: {k}")
    if shutil.which("gitleaks"):
        p = subprocess.run(["gitleaks", "git", "--pre-commit", "--staged", "--redact", "--no-banner", "-v"],
                           capture_output=True, text=True)
        if p.returncode == 1:
            hits.append("gitleaks:\n" + (p.stdout or p.stderr).strip())
    if hits:
        print("pre-commit: blocked, possible secret staged (values not shown):", file=sys.stderr)
        for h in hits:
            print("  " + h, file=sys.stderr)
        print("Unstage it (git restore --staged <file>) and move the value to an ignored .env file.\n"
              "A false positive: commit from your own terminal with --no-verify.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
