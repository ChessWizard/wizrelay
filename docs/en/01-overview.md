<!-- nav:top -->
[Documentation](README.md) › **1. Overview** &nbsp;·&nbsp; [Türkçe](../tr/01-overview.md)
<!-- /nav:top -->

# Overview

What wizrelay is, the problem it solves, and the three pieces it is made of.

## The problem it solves

A researcher analyses a task and shares the analysis with the team. Each developer then
works in their own Claude Code session, and every session interprets that analysis slightly
differently. The result is changes outside the intended scope, contract mismatches between
roles, and bugs.

wizrelay does three things about it:

1. **Carries the analysis into every session identically**, from one source.
2. **Does not leave the scope to Claude** — it enforces it with rules.
3. **Does not leave an unanswered question to the developer's guess** — it sends the
   question back to the researcher.

## The three pieces

| Piece | What it is | How many | Analogy |
|---|---|---|---|
| **Plugin** (`wizrelay`) | The tool that adds commands, automatic checks and helper agents to Claude Code. Contains no team's analysis. | One product in the world; everybody installs it | The ClickUp application |
| **Hub** | The private git repository where a team's analysis packages live. Holds no code. | One per **team** | Your company's ClickUp workspace |
| **Project repositories** | The developers' code. Each is connected to the hub once. | As many as you like | The projects in that workspace |

```
                PLUGIN (wizrelay) — installed in everyone's Claude Code
                                │  reads / writes
                                ▼
                 TEAM HUB  (acme/research-hub)
                 tasks/CU-86c1abcd-…/    tasks/CU-91f2aa10-…/
                                │  /wizrelay:pull
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
          api-service           web-app               deploy-infra
          role: backend         role: frontend        role: infra
          .wizrelay/            .wizrelay/            .wizrelay/
```

### Names

| Thing | Value |
|---|---|
| Product, repository, marketplace | `wizrelay` — one name for all three |
| Plugin | `wizrelay` — every command starts with `/wizrelay:` |
| Install id | `wizrelay@wizrelay` |
| CLI (CI and terminal) | `wizrelay` |
| Project directory / hub marker | `.wizrelay/` / `wizrelay-hub.json` |
| Tracker tags | `[WIZRELAY-PUBLISH]`, `[WIZRELAY-Q]`, `[WIZRELAY-A]`, `[WIZRELAY-VERIFY]` |

The point people get wrong most often: **a hub is per team, not per project.** Adding a new
project repository to the team does not need a new hub; that repository connects to the
existing one.

## Who does what

| Role | Responsible for | Commands they use |
|---|---|---|
| Researcher | Analyses the task, writes the package, validates it, publishes it, answers questions | `/wizrelay:hub-*` |
| Developer | Pulls the package, plans, implements, asks when needed, verifies their own work | `/wizrelay:pull`, `plan`, `ask`, `verify`, `sync`, `status` |
| Team lead / installer | Sets up the hub, connects repositories, manages team settings | `/wizrelay:hub-init`, `/wizrelay:init`, `/wizrelay:doctor` |
| CI | Audits scope on pull requests | `wizrelay audit` |

## A task's journey

```
Task in the tracker (CU-86c1abcd)
   │
   ▼
[Researcher] /wizrelay:hub-new → write the package → /wizrelay:hub-validate → /wizrelay:hub-publish (v1)
   │                                                        └─► Tracker: [WIZRELAY-PUBLISH]
   ▼
[Developer] /wizrelay:pull → /wizrelay:plan → implement (checks live) → /wizrelay:verify
   │                │                                              └─► Tracker: [WIZRELAY-VERIFY]
   │                └─► a question: /wizrelay:ask ──► Tracker: [WIZRELAY-Q]
   │                                                  │
   │        [Researcher] /wizrelay:hub-inbox → decisions.md → /wizrelay:hub-publish (v2)
   │                                                  └─► Tracker: [WIZRELAY-A], [WIZRELAY-PUBLISH]
   ▼
[Developer] session start says "v2 exists" → /wizrelay:sync → carry on
   │
   ▼
Pull request → CI: wizrelay audit → merge
```

## Why it is built this way

**One source of truth.** The analysis is written only in the hub. The copies in projects
are read-only and every file's hash is recorded, so a local edit is detectable rather than
silent.

**Rules, not instructions.** Telling Claude "do not go outside the scope" is not enough. The
plugin blocks an out-of-scope edit at the Claude Code level, where the decision is not
probabilistic.

**Ambiguity goes back.** A question the package cannot answer closes with the researcher's
decision, not the developer's guess, and reaches everybody as a new version.

## What a package contains

The package is both prose and data, deliberately:

- **Prose** is what a person reads. `research.md` explains why, `scope.md` explains where
  the boundary is, `roles/<role>.md` warns about the pitfalls.
- **Data** is what the tooling enforces. `task.json` carries the scope globs, the signals
  and the enforcement mode.

The prose persuades; the data is what makes the guardrail real. Writing the scope only in
prose would leave nothing to enforce. Writing only the globs would leave nothing to
understand.

When two files say overlapping things, a fixed precedence order resolves it, and that order
is written into the protocol every session loads:

```
decisions.md  >  task.json + scope.md  >  contracts.md  >  acceptance.md  >  roles/<role>.md  >  research.md
(newest)         (scope)                  (interfaces)     (behaviour)        (the slice)        (rationale)
```

`decisions.md` wins because it is the newest thing anyone agreed. `research.md` loses
because it is the reasoning, and reasoning is what a decision is allowed to overturn.

## Next

[2. What it does and does not do](02-scope.md) draws the boundary, including the parts this
tool deliberately leaves alone.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| &nbsp; | [Contents](README.md) | [2. What it does and does not do →](02-scope.md) |
<!-- /nav:bottom -->
