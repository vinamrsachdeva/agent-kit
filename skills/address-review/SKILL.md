---
name: address-review
description: "Address every unresolved review thread on a PR, bot or human: one at a time, the user's call, fixes, issues, replies."
disable-model-invocation: true
argument-hint: "[pr-number]"
---

Settle every unresolved review thread on a PR. You gather the facts, the user makes the calls. Every thread ends with a fix or a reply.

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

   Keep `isResolved: false`. Each **item**: thread id, first comment's `databaseId` + `url`, path, line, outdated flag, body, later comments, and **source**: `bot` when the first author's `__typename` is `Bot`, else `human`.
3. Find the **spec**: the session's own spec if it has one; else issue refs in the PR's commit messages; else a path the user passed; else a matching file under `docs/`, `specs/` or `.scratch/`; else ask the user. No spec means no `spec was wrong` bucket.

Done when every unresolved thread is an item.

## 2. Walk the items

Take the items one at a time, in file order, outdated ones last. Settle each before showing the next:

1. **Show** the reviewer's comment verbatim, with its path:line, source, comment URL and any later comments in the thread.
2. **Check** whether its **claim** is true: read the code, or write a test that fails if the claim holds. Weigh it against the spec and any `/code-review` findings already in this session. Show the verdict, the evidence (a file:line, a test result, a spec quote) and one proposed **bucket**:

   | Bucket | When | Outcome |
   |---|---|---|
   | `real bug` | Claim true, behaviour is wrong | A subagent drives `/tdd`; one local commit |
   | `style/naming` | Claim true, no behaviour change | Edit directly; one local commit |
   | `spec was wrong` | Code should change and the spec was wrong too | Code fix, then the spec edit as its own local commit; an ADR via `/domain-modeling` if the decision is hard to reverse |
   | `disagree` | Claim false, or the code is right as written | Reply with the evidence |
   | `already handled` | Current code already fixes it | Reply naming the commit that fixed it |
   | `defer` | Valid, out of this PR's scope | GitHub issue (step 3) |
   | `design change` | Fix needs a decision the spec didn't make, or touches other modules | GitHub issue for `/grill-with-docs` (step 3) |

3. **Wait** for the user's call: the proposed bucket or another.
4. **Act** on the bucket's outcome. Every commit message carries the thread's comment URL.

An item is **settled** when it has the user's call and, for the first three buckets, its local commit(s). Done when every item is settled.

## 3. Issues

For each `defer` and `design change` item, `gh issue create` with the claim, the evidence and the thread URL. `design change` issues add: "Take into `/grill-with-docs`."

Done when each of those items has an issue URL recorded for its reply.

## 4. Review

Run `/code-review` with BASE_SHA as the fixed point, so it covers only this run's commits. Show the user its findings; each one the user picks to fix becomes another local commit.

Done when the user has ruled on every finding.

## 5. Agree, then push and reply

Everything stays local until the user agrees with every reply and resolve decision.

1. **Draft** for each item: its reply, linking its commit (short SHA) or issue, with the evidence for `disagree`; and a **resolve decision**, proposed as resolve for bot threads and leave open for human threads. Show the user every draft together, plus the list of local commits waiting to push.
2. **Revise** drafts and decisions until the user approves them all. While they are revising, no push, no post, no resolve.
3. **Publish**, in this order, only after that approval:
   1. `git push`: the run's only push, so the commit links in the replies resolve.
   2. Post each reply: `gh api -X POST repos/{owner}/{repo}/pulls/{number}/comments/{databaseId}/replies -f body=...`
   3. Resolve each thread marked resolve: `gh api graphql -f query='mutation{resolveReviewThread(input:{threadId:"<id>"}){thread{isResolved}}}'`

Done when the commits are pushed, every item has a posted reply, and every thread marked resolve is resolved.

## 6. Summary

Report to the user: counts per bucket, plus the **mechanical** items (ones a lint rule or automated check could have caught), with a suggestion to run `/retro`. The run ends here; CI is the user's to watch.

A later review is a new run: it picks up only the threads still unresolved.
