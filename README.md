# agent-kit

My agent setup: global agent rules and skills.

```
agent-kit/
├── AGENTS.md       # global agent rules → ~/.claude/AGENTS.md
├── skills/         # skills → ~/.claude/skills
│   ├── address-review/
│   └── socratic-bootdev-tutor/
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
| [socratic-bootdev-tutor](skills/socratic-bootdev-tutor/SKILL.md) | Teach a Boot.dev chapter by questioning, lesson by lesson |

### address-review

Walks every unresolved review thread on a PR (Copilot, other bots, humans) one at a time: shows the full comment, checks its claim against the code and the spec, and proposes a bucket: real bug, style/naming, disagree, already handled, defer, design change, spec was wrong. You make the call; it fixes and commits locally (bugs via TDD) before moving on. Once every item is settled, it files issues for deferred and design items, reviews the fix commits, pushes, and posts the replies after your "go". It resolves bot threads only; human threads stay open for their reviewer.

- **Run:** `/address-review [pr-number]`. Only you can trigger it. With no number it uses the current branch's PR.
- **Needs:** `gh`, logged in. Works best alongside [Matt Pocock's skills](https://github.com/mattpocock/skills) (`/tdd`, `/code-review`, `/domain-modeling`, `/grill-with-docs`, `/retro`), which it hands work to.
- **Best run** in the session that built the PR, so the spec and earlier review findings are in context.

### socratic-bootdev-tutor

Tutors you through one chapter of a [Boot.dev](https://www.boot.dev) course, Socratic style: a short diagnostic, then one question at a time per lesson, with a 0-5 skill map that only moves on demonstrated answers. Each lesson ends on its Boot.dev exercise, done either on Boot.dev or locally: code lessons are copied down as Boot.dev's starter files and checked with the same cases Submit runs, multiple-choice and AI-graded essay lessons are answered in chat. Once every lesson is done, it offers to keep going to mastery and a final assessment. If Boot.dev's API changes, the skill repairs its own script and docs.

- **Run:** ask to be taught or quizzed on a Boot.dev chapter, e.g. "teach me chapter 3 of learn-javascript".
- **Needs:** Python 3. For local code lessons, the language's runner (`node`, `pytest`, `npx`, `go`). Reads Boot.dev's public API only, so it asks you which lessons you've already finished.

## License

MIT
