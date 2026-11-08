---
name: address-review
description: "Address every unresolved review thread on a PR, bot or human: one at a time, the user's call, fixes, issues, replies."
disable-model-invocation: true
argument-hint: "[pr-number]"
---

Settle every unresolved review thread on a PR. You gather the facts, the user makes the calls. Every thread ends with a fix or a reply.

Best run in the session that built the PR (e.g. the `/implement-spec` session): its spec and `/code-review` findings are the evidence for each verdict.

## 1. Gather

1. PR is `$ARGUMENTS`, else the current branch's PR: `gh pr view --json number,title,baseRefName,headRefOid,url`. Record `headRefOid` as **BASE_SHA**, the fixed point for step 4.
2. Fetch threads with GraphQL (REST cannot see `isResolved`), paging on `endCursor`:

   ```
   gh api graphql -F o={owner} -F n={repo} -F pr={number} -f query='
   query($o:String!,$n:String!,$pr:Int!,$after:String){repository(owner:$o,name:$n){pullRequest(number:$pr){
   reviewThreads(first:100,after:$after){pageInfo{hasNextPage endCursor}nodes{
   id isResolved isOutdated path line originalLine
   comments(first:50){nodes{databaseId url body author{__typename login}}}}}}}}'
   ```

   Keep `isResolved: false`. Each **item**: thread id, first comment's `databaseId` + `url`, path, line, body, later comments, and **source**: `bot` when the first author's `__typename` is `Bot`, else `human`. Outdated threads go in their own section.
3. Find the **spec**: the session's own spec if it has one; else issue refs in the PR's commit messages; else a path the user passed; else a matching file under `docs/`, `specs/` or `.scratch/`; else ask the user. No spec means no `spec was wrong` bucket.

Done when every unresolved thread is an item.

## 2. Walk the items

Take the items one at a time, in file order, outdated ones last. For each:

1. **Show** the reviewer's comment verbatim, the whole body, with its path:line, source, comment URL and any later comments in the thread.
2. **Check** whether its **claim** is true: read the code, or write a test that fails if the claim holds. Check it against the spec and any earlier `/code-review` findings. Show the verdict, the evidence (a file:line, a test result, a spec quote) and one proposed **bucket**:

   | Bucket | When | Outcome |
   |---|---|---|
   | `real bug` | Claim true, behaviour is wrong | `/tdd` fix |
   | `style/naming` | Claim true, no behaviour change | direct fix |
   | `disagree` | Claim false, or the code is right as written | reply with evidence |
   | `already handled` | Current code already fixes it | reply naming the commit that fixed it |
   | `defer` | Valid, out of this PR's scope | GitHub issue |
   | `design change` | Fix needs a decision the spec didn't make, or touches other modules | GitHub issue, taken into `/grill-with-docs` |
   | `spec was wrong` | Code should change and the spec was wrong too | fix + spec edit (+ ADR) |

3. **Wait** for the user's call: approve the bucket or name another.
4. **Fix** fix-bucket items now, then commit locally: one commit, its message carrying the thread's comment URL.
   - `real bug`: a subagent driving `/tdd`.
   - `style/naming`: edit directly.
   - `spec was wrong`: the code fix, plus the spec edit as its own commit. A hard-to-reverse decision also gets an ADR via `/domain-modeling`.

Then move to the next item.

Done when every item has the user's call and every fix-bucket item has its local commit.

## 3. Issues

For each `defer` and `design change` item, `gh issue create` with the claim, the evidence and a link back to the thread. `design change` issues add: "Take into `/grill-with-docs`." Record each issue URL for its reply.

## 4. Review

Run `/code-review` with BASE_SHA as the fixed point, so it reviews only the fix commits. Show the user its findings.

## 5. Push and reply

1. `git push`: the first push of the run, after every item is settled, so commit links in the replies resolve.
2. Draft one reply per item, linking its commit or issue; `disagree` replies carry the evidence. Show the user every draft together.
3. After the user's one "go", post each: `gh api -X POST repos/{owner}/{repo}/pulls/{number}/comments/{databaseId}/replies -f body=...`
4. Resolve **bot** threads only: `gh api graphql -f query='mutation{resolveReviewThread(input:{threadId:"<id>"}){thread{isResolved}}}'`. Human threads stay open for their reviewer to resolve.

Done when every item has a posted reply and every bot thread is resolved.

## 6. Summary

Report to the user: counts per bucket, plus the **mechanical** items (ones a lint rule or automated check could have caught), with a suggestion to run `/retro`. Stop there; CI is a separate job.

A new review after the push is a new run of this skill: it picks up only the threads still unresolved.
