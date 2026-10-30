<!-- nav:top -->
[Documentation](README.md) › **8. Developer: implement a task** &nbsp;·&nbsp; [Türkçe](../tr/08-developer-workflow.md)
<!-- /nav:top -->

# Developer: implement a task

Pulling a package, planning against it, implementing with the checks live, and verifying
with evidence.

## The flow

```
/wizrelay:pull → (suggested model) → /wizrelay:plan → implement → (/wizrelay:ask) → /wizrelay:verify → PR
```

## 1. Pull the task

When you see the `[WIZRELAY-PUBLISH]` comment on the tracker, in your own repository:

```
/wizrelay:pull CU-86c1abcd
```

The raw identifier works too: `/wizrelay:pull 86c1abcd`. So does the task URL, and so does
the package directory name.

What you get:

```text
CU-86c1abcd v1 — Tenant daily API request quota
8 researcher file(s) copied.
Created for you: plan.md, questions.md
In scope: app/quota/**, app/api/limits.py, tests/quota/**

Routing: T2-standard (score 6)
  plan       opus / high
  implement  sonnet / high
  verify     sonnet / high
  ask        sonnet / low

Launch this task's session with:
  claude --model opusplan --effort high --name 'CU-86c1abcd Tenant daily API request quota'
```

The task title is package data, not a message, so it appears exactly as the researcher
wrote it — in whatever language that was. The labels around it follow `--lang`; the title
does not. The example package shipped in [`examples/`](../../examples/) is in Turkish, so
its real output carries a Turkish title inside these English labels; the samples here show
it translated.

Then Claude gives a briefing of no more than fifteen lines: the goal, **your** criteria,
the scope, the binding decisions, the contracts and the risks. It writes no code at this
stage — that is deliberate, and it is the step where drift usually starts.

The valuable part of that briefing is the last bit: anything in the package that is
ambiguous, contradictory or missing. Read it. "AC-2 has no verification command" is worth
five minutes now and an afternoon later.

Files created in your project:

```
.wizrelay/tasks/CU-86c1abcd-tenant-daily-api-request-quota/
├── task.json, research.md, scope.md, acceptance.md, contracts.md, decisions.md
├── roles/backend.md, roles/frontend.md   ← you see the other role too, for context
├── .lock.json                            ← version, hub commit, file hashes, routing
├── plan.md                               ← yours
└── questions.md                          ← yours
```

Claude cannot change the researcher files. If **you** change one by hand, every session
start reports it as locally modified, and `/wizrelay:sync` restores it.

**Branch name:** use one containing the task identifier, for example
`feature/CU-86c1abcd-tenant-quota`. Then the active task is found from the branch
automatically — in worktrees too — and the CI gate recognises the task.

## 2. Work with the right model and effort

Two ways:

1. **Start a new session with the suggested command (preferred):**
   ```bash
   claude --model opusplan --effort high --name 'CU-86c1abcd Tenant quota'
   ```
2. **Adjust the current session:** pick the model with `/model` (pressing `s` in the picker
   applies it to this session only) and type `/effort high`.

What the terms mean:

- `opusplan` — Opus in plan mode, Sonnet for execution.
- `--advisor opus` — appears on high-risk tasks. Claude consults Opus at critical moments.
  Experimental, and only on the Anthropic API.

If you try to switch to a weaker model than the one suggested, the plugin asks for
confirmation. It is not a prohibition; it is a nudge to make the choice deliberately.

## 3. Plan

```
/wizrelay:plan
```

1. Claude enters plan mode, where it changes no files. You can enter plan mode yourself any
   time with Shift+Tab.
2. It reads the whole package, and delegates the code mapping — criterion → file/symbol →
   test — to the `codebase-mapper` helper.
3. It presents the plan: the goal, the criterion mapping, the steps (each tied to a
   criterion and touching only in-scope files), the risks, and the open questions.
4. If you approve, it writes the plan to `plan.md`.
5. It suggests a `/goal` line you can copy for the implementation:

```
/goal every one of AC-1…AC-4 for the backend role has its test shown passing in this conversation, every step in plan.md is [x], and no out-of-scope file changed; or stop after 30 turns
```

With `/goal`, Claude keeps taking turns until the condition is met, and a separate evaluator
model checks the condition at the end of each turn.

If the plan surfaced an open question, ask it with `/wizrelay:ask` before you start
implementing.

## 4. Implement, and recognise the checks

You work normally — "implement step 1 from plan.md". In the background:

| When | What happens |
|---|---|
| Every session start | The active task's summary is given to Claude. Re-given after a compaction |
| Every message | A one-line reminder is added: `[WIZRELAY] Active task CU-86c1abcd · research v1 · role backend · scope mode strict · open questions 0` |
| Before every file edit | The scope is checked |
| At the end of every turn | The git state is scanned |

Messages you may see:

| Situation | The message, as the plugin words it | What to do |
|---|---|---|
| A researcher file was about to be edited | `acceptance.md belongs to the researcher and is read-only here (CU-86c1abcd). Ask through /wizrelay:ask; the answer arrives as a new package version.` | If the change is needed, `/wizrelay:ask` |
| An explicitly denied area | `app/billing/invoice.py is explicitly denied by the scope of CU-86c1abcd (pattern app/billing/**).` | If it is genuinely needed, write the reason in `questions.md` and `/wizrelay:ask` |
| Out of scope, `strict` | `README.md is outside the scope of CU-86c1abcd. In scope: app/quota/**, … Raise a question with /wizrelay:ask rather than widening the scope locally.` | The same |
| Out of scope, `ask` mode | The same first sentence, as a permission prompt rather than a refusal | Approve or decline deliberately; if you approve, `/wizrelay:verify` reports it |
| End-of-turn warning | `wizrelay: this turn changed files outside the scope of CU-86c1abcd.` then one line per file | Revert it, or ask |

Trying to make a blocked change with a shell command or a script is both against the
protocol and caught later — by the end-of-turn audit, by `/wizrelay:verify`, and by CI.

## 5. Ask

```
/wizrelay:ask should Retry-After be seconds or a date?
```

Claude answers from the package only, and cites its source:

```text
Seconds. acceptance.md#AC-1 says Retry-After is the seconds remaining until the next UTC
midnight, and roles/backend.md#Pitfalls stresses that it is seconds rather than a date.
In this repository: ApiError in app/core/errors.py does not support headers yet, so one
will have to be added.
Sources: acceptance.md#AC-1, roles/backend.md#Pitfalls
```

You do not have to invoke this skill by hand. Ask "what does this criterion mean" or "is
this in scope" and Claude uses it on its own. It works for learning, too: "explain why the
quota counter uses an atomic upsert".

If the package has no answer:

1. **Claude does not invent a decision.** It records the question in `questions.md` as
   `Q-001`, with the options it sees and what it would do absent an answer.
2. It asks for your approval to send it. If you approve, a
   `[WIZRELAY-Q] Q-001 — CU-86c1abcd — backend` comment appears on the task and the
   researcher is mentioned.
3. Meanwhile you carry on with the steps that do not depend on the answer.

That first point is the single most important behaviour in this system. A plausible answer
the researcher never gave looks like a decision, gets implemented, and nobody knows it was
invented.

## 6. When a new version arrives

If the researcher publishes v2, the next session start tells you:

```text
WIZRELAY: research v2 is published in the hub (you have v1). Run /wizrelay:sync.
```

```
/wizrelay:sync
```

It shows the changed files and a diff. Claude analyses the impact and, with your approval:

- marks the affected steps in `plan.md` and adds any new ones,
- changes an answered question's status to `ANSWERED (D-004)`,
- lists the places in code already written that conflict with the new version.

Read `decisions.md` first. A new decision is the kind of change that can reverse something
you have already built.

## 7. Verify

```
/wizrelay:verify
```

An independent verifier (`test-engineer`) runs in a separate context. It does not see the
conversation that wrote the code; it looks only at evidence:

1. Runs the project's commands — first the targeted tests matching the criteria, then the
   whole suite.
2. Gives a verdict per criterion: `PASS`, `FAIL` or `NOT COVERED`.
3. Adds the deterministic scope and integrity audit to the report.
4. Writes `verification.md`. It does not touch code — it cannot; its edit tools are removed
   by configuration.
5. Asks for approval to post the `[WIZRELAY-VERIFY]` comment.

An example summary:

```text
Overall: PARTIAL
- AC-1 PASS — pytest tests/quota/test_quota_exceeded.py (3 passed)
- AC-2 PASS — pytest tests/quota/test_quota_concurrency.py (1 passed)
- AC-3 NOT COVERED — no test for idempotency (suggested: tests/quota/test_quota_idempotency.py)
- AC-4 PASS — pytest tests/api/test_messages_quota.py (2 passed)
Scope audit: clean · Research integrity: clean
```

With a `FAIL` or a `NOT COVERED`, go back to the main session and ask Claude to close the
gap — "write the test suggested for AC-3" — then run `/wizrelay:verify` again.

A scope violation caps the overall result at `PARTIAL` however well the tests pass. An
in-scope implementation that also changed something else is not a finished task.

## 8. Finish

- **Use criterion identifiers in commit messages:**
  `feat(quota): idempotency record (AC-3)`.
- **Commit `.wizrelay/tasks/<directory>/`:** the package copy, `plan.md`, `questions.md`,
  `verification.md`. This shows which research version the pull request was written against,
  and the CI gate needs it.
- **Open the pull request;** CI runs the scope audit
  ([12. CI integration](12-ci-integration.md)).

## Several tasks

- `/wizrelay:status` shows the active task, the version, plan progress, open questions and
  any warning.
- The active task is found from the branch name, so switching branch switches task.
- To select one by hand: `wizrelay activate <directory>`.

## Next

[9. The question and version loop](09-question-loop.md) — what happens on the researcher's
side after you ask.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 7. Researcher: prepare and publish](07-researcher-workflow.md) | [Contents](README.md) | [9. The question and version loop →](09-question-loop.md) |
<!-- /nav:bottom -->
