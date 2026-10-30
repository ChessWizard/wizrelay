---
name: pull
description: Download a published task package from the research hub, make it active, and brief the session on it.
disable-model-invocation: true
allowed-tools: Bash(wizrelay *)
argument-hint: "<task reference>"
---

Load a published research package into this repository.

**Write no code in this turn.** Pulling is not implementing. The user runs
`/wizrelay:plan` next, and planning before the package is read is how scope drift starts.

**Do not edit any researcher file.** They are read-only here. `wizrelay pull` writes them;
you read them.

## 1. Pull

```
wizrelay pull $ARGUMENTS
```

A reference can be the canonical identifier (`CU-86c1abcd`), the raw tracker reference
(`86c1abcd`), a task URL, or the package directory name.

If it reports that the package is not published, stop and tell the user. Do not pass
`--allow-draft` unless the user asks for it: a draft can change under them without a
version bump.

## 2. Read the package

Read, in this order — it is the precedence order when sources disagree:

1. `decisions.md` — the newest decision wins over everything below it
2. `task.json` and `scope.md` — what may change
3. `contracts.md` — interfaces with other roles
4. `acceptance.md` — what "done" means, for this role
5. `roles/<your role>.md` — the slice, the pitfalls, the test expectation
6. `research.md` — why this approach

## 3. Brief the user, in at most fifteen lines

Cover, and nothing else:

- the task identifier, version and title
- this repository's role
- what is in scope, and what is explicitly denied
- the acceptance criteria for this role, by identifier and title
- the routing table and the launch command `wizrelay pull` printed
- anything in the package that is ambiguous, contradictory or missing

That last point is the valuable one. Say it plainly: "`acceptance.md` AC-2 has no
verification command", "`contracts.md` does not say what happens on a 404". Do not fill
the gap with a guess — the next step is `/wizrelay:ask`.

## 4. Point at the next step

If the routing table proposes a stronger model than this session is running, show the
launch command and say the current session will work but was not routed for this task.

Then:

- open questions in the package → `/wizrelay:ask`
- otherwise → `/wizrelay:plan`

Answer in the language set in `.wizrelay/config.json`.
