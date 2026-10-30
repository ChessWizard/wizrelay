---
name: hub-status
description: Show the hub's packages and the verification results developers have reported per role.
disable-model-invocation: true
allowed-tools: Bash(wizrelay *)
argument-hint: "[task reference]"
---

Report where the hub's work stands. Read-only: change nothing.

With a task reference in `$ARGUMENTS`, limit the report to that package.

## Packages

!`wizrelay hub list`

## What to add

The listing is structural. Fill in what it cannot know, using the tracker's MCP tools:

- For each published package, find the comments beginning `[WIZRELAY-VERIFY]` and report
  the result per role: `PASS`, `FAIL`, `PARTIAL`, or nothing reported yet.
- Find comments beginning `[WIZRELAY-Q]` with no matching `[WIZRELAY-A]`. These are
  developers waiting on a decision, which is the most time-sensitive item here.

## Summarise

Group by what the user can act on:

- **Waiting on you** — open questions, and packages with a `FAIL` that needs a decision
- **In progress** — published, no verification reported yet
- **Done** — every role reported `PASS`
- **Drafts** — not published yet

For each open question, say how long it has been waiting.

Then point at the next command: open questions → `/wizrelay:hub-inbox`; drafts →
`/wizrelay:hub-validate`.

Answer in the language set in `wizrelay-hub.json`.
