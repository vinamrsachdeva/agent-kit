# Global agent rules

## User identity

- Always address me as Vin at the start of every response.

## Response style

- When reporting information to me, be extremely concise and sacrifice grammar for the sake of concision.

## Pull requests

- Open every PR with `ship-pr` (`--base <branch>` if not main; `--dry-run` to preview). It drafts the body, pushes and opens the PR in one step, so run it instead of `git push` + `gh pr create`.

## Killing processes

- Never kill by name or pattern (`pkill`, `killall`, `kill $(pgrep …)`, `… | xargs kill`): `-f` patterns match full command lines, so `pkill -f cat` hits every app under `/Applications`. Run `pgrep -fl '<pattern>'`, check the list, then `kill <PID>`. To free a port: `lsof -ti tcp:<port> -sTCP:LISTEN`. A `kill-guard` hook blocks the unsafe forms.
