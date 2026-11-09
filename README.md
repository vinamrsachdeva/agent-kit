# agent-kit

My agent setup: global agent rules, scripts, and skills.

```
agent-kit/
├── AGENTS.md       # global agent rules → ~/.claude/AGENTS.md
├── bin/            # scripts → ~/.local/bin
│   └── ship-pr
├── skills/         # skills → ~/.claude/skills
│   └── address-review/
└── install.sh      # makes those symlinks; safe to re-run
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

## Scripts

### ship-pr

Drafts a PR for the current branch with Claude (`claude -p`, using [Matt Pocock's](https://github.com/mattpocock/skills) `pr` skill), folds the body into one `<details><summary>` block with a blank opener for your own summary ([why](https://simonwillison.net/2026/Nov/9/details-summary/)), pushes, opens the PR, and prints the link.

- **Run:** `ship-pr` on the branch to ship. `--dry-run` prints the title and body without pushing; `--base` picks the base branch.
- **Needs:** `claude`, `gh` (logged in), the `mattpocock-skills` plugin.
- **Env:** `SHIP_PR_MODEL` (default `claude-opus-5-5`), `SHIP_PR_EFFORT` (default `medium`).

## License

MIT
