---
name: implement
description: Work through plan.md inside the role's scope, checking off each step as its test passes.
disable-model-invocation: true
effort: high
allowed-tools: Bash(wizrelay *)
---

Build what `plan.md` says, one step at a time, and check each step off when its test
passes.

The plan is the brief. You are not re-deciding the work here: `/wizrelay:plan` decided it
against the acceptance criteria, and a step you disagree with is a question, not a step to
quietly replace. If the plan is wrong, say so and stop — rewriting it mid-implementation
leaves nobody able to tell what was agreed.

If the user gave you anything alongside the command, treat it as part of the brief and say
which steps it changed.

## Context

!`wizrelay brief --phase implement`

If the line above begins with `NO_INIT` or `NO_ACTIVE_TASK`, stop and say which command
the user needs. If it begins with `WIZRELAY_NO_GUARD`, tell the user that scope protection
is not active in this session before you continue.

## 1. Read the plan

Read `plan.md` in the active package directory.

- **No plan, or still the scaffold** (`{{` placeholders, or no `- [ ]` steps) — stop. Tell
  the user to run `/wizrelay:plan` first. Do not invent one: a plan written here was never
  checked against the acceptance criteria and nobody will know that.
- **Every step checked off** — say so, and point at `/wizrelay:verify`.
- **Otherwise** — the first unchecked step is where you start.

Say in one line how many steps there are and which one you are starting.

## 2. Work one step at a time

For each unchecked step, in order:

1. **Stay in scope.** Only paths the role's `allow` list covers. A step that needs a
   denied or out-of-scope path is not a step to force through — stop and say so; that is
   a question for the researcher, through `/wizrelay:ask`.
2. **Write the change.** Follow the conventions already in the files you are editing.
3. **Run that step's test** — the command the plan names, or `test_targeted` from
   `.wizrelay/profile.json` narrowed to what you touched. Never invent a test command.
4. **Check the step off** in `plan.md` — `- [x]` — only once its test passed. A checkbox
   is a claim somebody else will rely on.
5. If the test fails twice on the same step, stop and report. A third attempt at the same
   failure is how a session spends an hour producing nothing.

Keep the repository working at every step, because the person reading this may stop you
at any one of them.

## 3. Never write a comment that is not a summary

No explanatory comments, no `// TODO`, no commented-out code, no notes to the reader about
what you just did or why. A method or field summary in the language the file already uses
for them — a docstring, a `///` or `/** */` summary — is the exception, and it describes
what the thing is, not the change you made.

This is not a style preference. A comment explaining code is a second copy of it that
nobody updates, and three sessions later it says something that is no longer true.

## 4. Say where it stands

Finish with:

- which steps are now checked off, and which are not
- the test command you ran last and what it printed
- anything you could not do, and why

Do not commit, push, or open a pull request. That decision is the user's, and in a panel
run it belongs to the approval step rather than to this session.

## 5. What comes next

When every step is checked off, point at `/wizrelay:verify` — an independent verifier,
which is the only verification that counts for the handover.

Answer in the language set in `.wizrelay/config.json`.
