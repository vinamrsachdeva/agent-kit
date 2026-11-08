# Skills

My agent skills.

## Install

Pick one. Installing both gives you every skill twice.

**Claude Code plugin** (updates itself):

```
/plugin marketplace add vinamrsachdeva/skills
/plugin install vin-skills@vinamrsachdeva
```

Skills are namespaced: `/vin-skills:address-review`.

**[skills.sh](https://skills.sh)** (copies editable files; update by hand):

```bash
npx skills add vinamrsachdeva/skills
```

## Skills

| Skill | What it does |
| --- | --- |
| [address-review](skills/address-review/SKILL.md) | Settle every unresolved review thread on a PR, bot or human |

### address-review

Gathers every unresolved review thread on a PR (Copilot, other bots, humans), checks each reviewer's claim against the code and the spec, and proposes a bucket for each in one table: real bug, style/naming, disagree, already handled, defer, design change, spec was wrong. You approve the table; it fixes one item per commit (bugs via TDD), files issues for deferred and design items, reviews the fix commits, pushes, and posts the replies after your "go". It resolves bot threads only; human threads stay open for their reviewer.

- **Run:** `/address-review [pr-number]`. Only you can trigger it. With no number it uses the current branch's PR.
- **Needs:** `gh`, logged in. Works best alongside [Matt Pocock's skills](https://github.com/mattpocock/skills) (`/tdd`, `/code-review`, `/domain-modeling`, `/grill-with-docs`, `/retro`), which it hands work to.
- **Best run** in the session that built the PR, so the spec and earlier review findings are in context.

## License

MIT
