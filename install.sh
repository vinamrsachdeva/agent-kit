#!/bin/sh
# Symlink this repo's AGENTS.md, bin/ scripts (if any), skills and guards into place, and
# install the guards. Safe to re-run.
set -e
R=$(cd "$(dirname "$0")" && pwd)
link() { # link <target-in-repo> <link-path>
	if [ -e "$2" ] && [ ! -L "$2" ]; then echo "skip $2: a real file is there, move it first"; return; fi
	mkdir -p "$(dirname "$2")"; ln -sfn "$1" "$2"; echo "$2 -> $1"
}
link "$R/AGENTS.md" "$HOME/.claude/AGENTS.md"
for f in "$R"/bin/*; do [ -e "$f" ] || continue; link "$f" "$HOME/.local/bin/$(basename "$f")"; done
for d in "$R"/skills/*/; do d=${d%/}; link "$d" "$HOME/.claude/skills/$(basename "$d")"; done

# Guards: Claude Code hooks, a push guard for every git repo, and permission rules per profile.
for f in "$R"/guards/claude-hooks/*; do link "$f" "$HOME/.claude/hooks/$(basename "$f")"; done
H="$HOME/.config/git/hooks"
link "$R/guards/git-hooks" "$H"
cur=$(git config --global --get core.hooksPath || true)
if [ -z "$cur" ]; then
	git config --global core.hooksPath "$H"; echo "git core.hooksPath = $H"
elif [ "$cur" != "$H" ]; then
	echo "skip git core.hooksPath: already $cur; point it at $H to get the push guard"
fi
python3 "$R/guards/merge-permissions.py" "$HOME/.claude/settings.json" "$HOME/.claude-personal/settings.json"
