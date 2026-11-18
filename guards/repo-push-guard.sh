#!/bin/sh
# Put the push guard back in repos that hide it.
#
#   repo-push-guard.sh [repo...]
#
# A repo's own core.hooksPath (husky, lefthook, pre-commit, a scripts/git-hooks folder) beats the
# global one, so git never runs agent-kit's pre-push there. For each such repo this adds a marked
# block at the top of that folder's pre-push (creating the file if needed) that runs the guard
# first. The block does nothing on a machine without agent-kit, so it's safe in a tracked file.
# Changed tracked files are left for you to commit. Safe to re-run.
#
# With no repos given, it checks every repo one level under $AGENT_KIT_REPO_ROOTS
# (default: ~/git ~/vb/git).
set -e
G="$HOME/.config/git/hooks"
MARK="agent-kit push guard"
real() { (cd "$1" 2>/dev/null && pwd -P); }
global=$(real "$G")
[ -n "$global" ] || { echo "no $G: run install.sh first" >&2; exit 1; }

block() {
	cat <<'EOF'
# >>> agent-kit push guard: runs agent-kit's pre-push first; does nothing without agent-kit.
_ak_g="$HOME/.config/git/hooks/pre-push"
if [ -x "$_ak_g" ]; then
	_ak_refs=$(mktemp)
	cat >"$_ak_refs"
	AGENT_KIT_SHIM=1 "$_ak_g" "$@" <"$_ak_refs" || { rm -f "$_ak_refs"; exit 1; }
	exec <"$_ak_refs"
	rm -f "$_ak_refs"
fi
# <<< agent-kit push guard
EOF
}

fix() { # fix <repo>
	top=$(git -C "$1" rev-parse --show-toplevel 2>/dev/null) || return 0
	hp=$(cd "$top" && git rev-parse --git-path hooks)
	case "$hp" in /*) ;; *) hp="$top/$hp" ;; esac
	dir=$(real "$hp")
	[ -n "$dir" ] && [ "$dir" != "$global" ] || return 0
	f="$dir/pre-push"
	if [ -f "$f" ] && grep -q "$MARK" "$f"; then
		echo "ok   $top"
		return 0
	fi
	if [ ! -f "$f" ]; then
		{ echo '#!/bin/sh'; block; echo 'exit 0'; } >"$f"
	else
		tmp=$(mktemp)
		if head -1 "$f" | grep -q '^#!'; then
			{ head -1 "$f"; block; tail -n +2 "$f"; } >"$tmp"
		else
			{ echo '#!/bin/sh'; block; cat "$f"; } >"$tmp"
		fi
		cat "$tmp" >"$f" # keep the file's mode and inode
		rm -f "$tmp"
	fi
	chmod +x "$f"
	echo "fix  $top: $f"
}

if [ $# -gt 0 ]; then
	for r in "$@"; do fix "$r"; done
else
	for root in ${AGENT_KIT_REPO_ROOTS:-$HOME/git $HOME/vb/git}; do
		for r in "$root"/*/; do [ -e "$r.git" ] && fix "${r%/}"; done
	done
fi
