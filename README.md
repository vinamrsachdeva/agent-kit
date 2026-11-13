# agent-kit

My agent setup: global agent rules, skills, and guards.

```
agent-kit/
├── AGENTS.md       # global agent rules → ~/.claude/AGENTS.md
├── skills/         # skills → ~/.claude/skills
│   └── address-review/
├── guards/
│   ├── claude-hooks/            # Claude Code hooks → ~/.claude/hooks
│   ├── git-hooks/               # push guard for every repo → ~/.config/git/hooks (core.hooksPath)
│   └── claude-permissions.json  # ask/deny rules, merged into each Claude profile's settings.json
└── install.sh      # makes those symlinks, sets core.hooksPath, merges the rules; safe to re-run
```

## Local setup

```bash
git clone https://github.com/vinamrsachdeva/agent-kit ~/git/agent-kit
~/git/agent-kit/install.sh
```

Edits in the repo take effect immediately through the symlinks.

## Install the skills only

Pick one. Installing both gives you every skill twice.

**Claude Code plugin** (updates itself):

```
/plugin marketplace add vinamrsachdeva/agent-kit
/plugin install vin-skills@vinamrsachdeva
```

Skills are namespaced: `/vin-skills:address-review`.

**[skills.sh](https://skills.sh)** (copies editable files; update by hand):

```bash
npx skills add vinamrsachdeva/agent-kit
```

## Skills

| Skill | What it does |
| --- | --- |
| [address-review](skills/address-review/SKILL.md) | Settle every unresolved review thread on a PR, bot or human |

### address-review

Walks every unresolved review thread on a PR (Copilot, other bots, humans) one at a time: shows the full comment, checks its claim against the code and the spec, and proposes a bucket: real bug, style/naming, disagree, already handled, defer, design change, spec was wrong. You make the call; it fixes and commits locally (bugs via TDD) before moving on. Once every item is settled, it files issues for deferred and design items, reviews the fix commits, pushes, and posts the replies after your "go". It resolves bot threads only; human threads stay open for their reviewer.

- **Run:** `/address-review [pr-number]`. Only you can trigger it. With no number it uses the current branch's PR.
- **Needs:** `gh`, logged in. Works best alongside [Matt Pocock's skills](https://github.com/mattpocock/skills) (`/tdd`, `/code-review`, `/domain-modeling`, `/grill-with-docs`, `/retro`), which it hands work to.
- **Best run** in the session that built the PR, so the spec and earlier review findings are in context.

## Guards

Stop agents from publishing on their own. They catch accidents, not an agent set on getting around them.

- **Push guard** (`guards/git-hooks/pre-push`): a push started by Claude Code, Codex, or any program without a terminal opens a macOS dialog listing what it pushes: per branch, the new commits' subjects, or **FORCE** with how many remote commits it replaces and whether the files change. It goes through only on a click on **Push** (it gives up, blocked, after 5 minutes). A push you type in your own terminal goes straight through, unless it rewrites or deletes `main`/`master`: then it asks y/N. Because it's a git hook, it catches every way of pushing: any agent, any profile, scripts, `/usr/bin/git`. GUI git clients have no terminal either, so they get the dialog too.
- **Commit guard** (`guards/git-hooks/pre-commit`): refuses a commit that stages a secret: `.env`-style files and private keys by name, and in the added lines, common key shapes, plus your own secrets by hash when `~/.claude/hooks/secretlib.py` exists, plus `gitleaks` when installed. It names file, line and kind, never the value. It also keeps your work email out of personal repos (and in work repos), from three local settings: `identity.workEmail`, `identity.workDir`, `identity.workRemote` (see the hook's header); pair them with `includeIf` rules that set `user.email`.
- **Chaining:** every other hook name links to `_chain`, which runs the repo's own `.git/hooks/<name>`; both guards do the same after their checks. The global `core.hooksPath` would otherwise hide them.
- **Ask rules** (`guards/claude-permissions.json`): Claude Code asks before `git push` and before `gh` commands that publish or change things on GitHub (PRs, issues, comments, reviews, releases, repos, gists, secrets, workflow runs, `gh api` writes). It also asks before git commands that throw away work for good (`reset --hard`, `clean`, `checkout --`, `restore`, `stash drop`/`clear`, `branch -D`, `reflog expire`, `gc --prune`), which no git hook can see. It denies `--no-verify` and `core.hooksPath`, the two ways to skip the git hooks. `install.sh` adds the rules to `~/.claude/settings.json` and `~/.claude-personal/settings.json`, keeping what's there and backing each file up first.
- **`kill-guard`** (`guards/claude-hooks/kill-guard.py`): a Claude Code `PreToolUse` hook that blocks killing processes by name or pattern. Wire it up in `settings.json` under `hooks.PreToolUse` with matcher `Bash` and command `python3 -I ~/.claude/hooks/kill-guard.py`.

## License

MIT
