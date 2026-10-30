---
name: sync
description: Update the active task package to the hub's current version and reconcile the plan with what changed.
disable-model-invocation: true
allowed-tools: Bash(wizrelay *)
---

Bring the active package up to date and work out what the change means.

**Run this before continuing work whenever a session reports a newer version.** Working
from a superseded analysis is the failure this command exists to prevent.

**Do not edit researcher files.** `wizrelay sync` rewrites them from the hub, including
restoring any that were modified locally.

## 1. Sync

```
wizrelay sync
```

It reports the version change, which files changed, which were removed, which it restored,
and a diff.

If it reports no changes, say so and stop. There is nothing to reconcile.

## 2. Read what changed, in precedence order

`decisions.md` first. A new `D-<nnn>` is the most consequential kind of change: it can
reverse a choice already implemented.

Then `task.json` and `scope.md` — the scope may have widened or narrowed. A narrowed scope
can make work already done out of scope.

Then `contracts.md`, `acceptance.md`, `roles/<role>.md`.

## 3. Reconcile, with the user's approval

Work out and present, before changing anything:

- **Which plan steps are now wrong.** A step implementing a reversed decision, or touching
  a path that left the scope.
- **Which questions are now answered.** A new decision usually answers an open question in
  `questions.md`.
- **Whether finished work needs revisiting.** Say which files and why.

Then ask the user whether to apply the updates. On a yes:

- update `plan.md`: adjust, add or remove steps, each still tied to a criterion
- in `questions.md`, change the answered question's status line to
  `Status: ANSWERED (D-<nnn>)`, keeping the question text

Both are developer files; writing to them is correct.

## 4. Say what comes next

- the scope narrowed and work is now outside it → `/wizrelay:ask`
- the plan changed → carry on with the next unchecked step
- the acceptance criteria changed and the work looked finished → `/wizrelay:verify`

Answer in the language set in `.wizrelay/config.json`.
