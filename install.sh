#!/bin/sh
# Symlink this repo's AGENTS.md, bin/ scripts and skills into place. Safe to re-run.
set -e
R=$(cd "$(dirname "$0")" && pwd)
link() { # link <target-in-repo> <link-path>
	if [ -e "$2" ] && [ ! -L "$2" ]; then echo "skip $2: a real file is there, move it first"; return; fi
	mkdir -p "$(dirname "$2")"; ln -sfn "$1" "$2"; echo "$2 -> $1"
}
link "$R/AGENTS.md" "$HOME/.claude/AGENTS.md"
for f in "$R"/bin/*; do link "$f" "$HOME/.local/bin/$(basename "$f")"; done
for d in "$R"/skills/*/; do d=${d%/}; link "$d" "$HOME/.claude/skills/$(basename "$d")"; done
