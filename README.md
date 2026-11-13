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

- **Push guard** (`guards/git-hooks/pre-push`): a push started by Claude Code, Codex, or any program without a terminal opens a macOS dialog and goes through only on a click on **Push** (it gives up, blocked, after 2 minutes). A push you type in your own terminal goes straight through. Because it's a git hook, it catches every way of pushing: any agent, any profile, scripts, `/usr/bin/git`. The other hook names chain to each repo's own `.git/hooks`, which the global `core.hooksPath` would otherwise hide. GUI git clients have no terminal either, so they get the dialog too.
- **Ask rules** (`guards/claude-permissions.json`): Claude Code asks before `git push` and before `gh` commands that publish or change things on GitHub (PRs, issues, comments, reviews, releases, repos, gists, secrets, workflow runs, `gh api` writes). It denies `--no-verify` and `core.hooksPath`, the two ways to skip the push guard. `install.sh` adds the rules to `~/.claude/settings.json` and `~/.claude-personal/settings.json`, keeping what's there and backing each file up first.
- **`kill-guard`** (`guards/claude-hooks/kill-guard.py`): a Claude Code `PreToolUse` hook that blocks killing processes by name or pattern. Wire it up in `settings.json` under `hooks.PreToolUse` with matcher `Bash` and command `python3 -I ~/.claude/hooks/kill-guard.py`.

## License

MIT
