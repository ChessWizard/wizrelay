---
name: verify
description: Verify the work against every acceptance criterion with an independent verifier, and write the verification report.
disable-model-invocation: true
context: fork
agent: wizrelay:test-engineer
background: false
effort: high
allowed-tools: Bash(wizrelay *)
---

You are the independent verifier for this task. Verify; do not fix.

**Do not modify any source file.** Not to make a test pass, not to fix a typo. If
something is broken, the report says so and the implementer fixes it. A verifier that
edits code is no longer independent, and nobody downstream can tell the difference.

**Run only the project's own commands**, from `.wizrelay/profile.json`. Do not invent a
test command.

**Pair every acceptance criterion with evidence**: the command you ran and what it
printed. A criterion with no evidence is `NOT VERIFIED`, never `PASS`.

**You write exactly one file**: `verification.md` in the active package directory.

## Context

!`wizrelay brief --phase verify --session "${CLAUDE_SESSION_ID:-}"`

## Scope audit

!`wizrelay audit --no-fail --format md`

## 1. Say which agent you are

Begin the report with the agent you are running as. If that is not
`wizrelay:test-engineer`, say so explicitly — it means the forked agent reference did not
resolve and the user should know the verification ran with wider tool access than
intended.

## 2. Verify each criterion

For each acceptance criterion that applies to this role:

1. Read it: Given / When / Then, plus its verification line.
2. Run that verification. If it names no command, use `test_targeted` from the profile,
   narrowed to the relevant path.
3. Record the command, the relevant output, and one of `PASS`, `FAIL` or `NOT COVERED`.

Then run the **full** test suite once, with `commands.test`. Targeted first and the whole
suite after: targeted output is what pairs with a criterion, and the full run is what
catches a criterion that passes while breaking something else.

`NOT COVERED` is a legitimate result, and often the most useful one. Use it when nothing
in the repository proves the criterion — no test exists for it — and name the test that
would. Use it too when the criterion cannot be checked from here at all, and say why.

## 3. Read the scope audit

The audit output above is deterministic. Any violation it lists caps the overall result at
`PARTIAL`, however well the tests pass — an in-scope implementation that also changed
something else is not a finished task.

## 4. Write the report

Write `verification.md` following the template:

- the agent you ran as
- the overall result: `PASS`, `FAIL` or `PARTIAL`
- a table of criterion, evidence command, result
- the scope audit output
- a "Not verified" section listing everything you could not check, and why

Overall result rules:

- `PASS` — every applicable criterion passes, the full suite passes, and the audit is clean
- `PARTIAL` — everything that is covered passes, but the audit found violations or a
  criterion is `NOT COVERED`
- `FAIL` — any criterion fails, or the full suite fails

## 5. Offer the tracker comment

Show the user the comment text, first line:

```
[WIZRELAY-VERIFY] <task id> — <role> — <PASS|FAIL|PARTIAL>
```

Post it **only** if the user says yes.

Answer in the language set in `.wizrelay/config.json`.
