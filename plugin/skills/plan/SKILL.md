---
name: plan
description: Turn the active task package into an implementation plan, in plan mode, with every step tied to an acceptance criterion.
disable-model-invocation: true
effort: high
allowed-tools: Bash(wizrelay *)
---

Build the implementation plan for the active task, and write it.

If the user gave you anything alongside the command — a constraint, a preference, an
ordering, something the package does not cover — treat it as part of the brief and say in
the plan where it changed a step.

**Propose only files inside this role's `allow` scope.** A plan step that touches a denied
or out-of-scope path is a plan that will be blocked at the first edit. If the work
genuinely needs a path outside the scope, that is a question for the researcher, not a
plan step.

**Every step names an acceptance criterion.** A step that serves none is either out of
scope or the acceptance criteria are incomplete — say which.

## Context

!`wizrelay brief --phase plan`

If the line above begins with `NO_INIT` or `NO_ACTIVE_TASK`, stop and say which command
the user needs. If it begins with `WIZRELAY_NO_GUARD`, tell the user that scope protection
is not active in this session before you continue.

## 1. Map the work

Delegate to the `wizrelay:codebase-mapper` subagent: give it the acceptance criteria and
the scope, and ask for the files, symbols and tests each criterion touches, plus anything
that looks like it falls outside the scope.

Read `roles/<role>.md` yourself for the pitfalls; they are the part a mapper cannot infer.

## 2. Draft the plan

One step per unit of work that can be verified on its own. For each step:

- the acceptance criterion it serves
- the files it changes, all inside the scope
- the test that proves it, using the project's own command from `.wizrelay/profile.json`

Order the steps so that each one leaves the repository working.

Record separately:

- **Assumptions** — anything you had to decide because the package does not say. Label
  each one, and tell the user. These are candidates for `/wizrelay:ask`.
- **Out of scope** — improvements you noticed and are not doing.

## 3. Write the plan

Present the plan, then write it to `plan.md` inside the active package directory, using
`- [ ]` steps so progress is countable.

Read `plan.md` first and let what is already there decide:

- **Still the scaffold** — it contains `{{` placeholders, or no steps at all. Write the
  plan in the same turn. Do not stop to ask: a session driven headlessly by a dashboard
  has no next turn, and a run that ends with the placeholders still in place has produced
  nothing at all.
- **A real plan is already there** — steps with no placeholders, some possibly checked
  off. Show what you would change and ask before replacing it. Finished work is recorded
  in those checkboxes and overwriting them loses it.

Say in one line what you wrote and how many steps it has.

`plan.md` is yours to write. Never touch `acceptance.md`, `scope.md`, `task.json`,
`decisions.md`, `contracts.md` or `roles/*.md`.

## 4. Suggest how to run it

Offer the user a goal that keeps the work bounded, for example:

```
/goal every step in plan.md is checked off, the acceptance tests pass, and wizrelay audit is clean; or stop after 30 turns
```

Answer in the language set in `.wizrelay/config.json`.
