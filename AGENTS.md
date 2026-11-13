# Global agent rules

## User identity

- Always address me as Vin at the start of every response.

## Response style

- When reporting information to me, be extremely concise and sacrifice grammar for the sake of concision.

## Pull requests

- When writing a PR description (new PR, or rewriting/reformatting an existing one), first check the repo for PR guidance (`.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE/`, `CONTRIBUTING.md`, `AGENTS.md`/`CLAUDE.md`), then:
  1. Repo mandates a full PR format: follow it strictly. Skip the `pr` skill.
  2. Repo only requires certain sections or content: use the `pr` skill's format, plus whatever extra text covers each required item.
  3. No guidance: use the `pr` skill's format as-is.

## Killing processes

- Never kill by name or pattern (`pkill`, `killall`, `kill $(pgrep …)`, `… | xargs kill`): `-f` patterns match full command lines, so `pkill -f cat` hits every app under `/Applications`. Run `pgrep -fl '<pattern>'`, check the list, then `kill <PID>`. To free a port: `lsof -ti tcp:<port> -sTCP:LISTEN`. A `kill-guard` hook blocks the unsafe forms.

## Pushing

- A global `pre-push` hook opens a dialog for every push an agent starts; it goes through only when I click Push. When it says "blocked", tell me and wait: I either click Push on a retry or push myself.
