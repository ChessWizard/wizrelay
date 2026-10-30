<!-- nav:top -->
[Documentation](README.md) › **9. The question and version loop** &nbsp;·&nbsp; [Türkçe](../tr/09-question-loop.md)
<!-- /nav:top -->

# The question and version loop

What the researcher does after a developer asks, and why the answer has to become a version
rather than a reply.

## Why a reply is not enough

A developer asks; the researcher answers on the tracker; the developer implements it. That
works once, for that developer.

It fails for everyone else. The next session that reads the package does not see the
tracker. The other role implementing the other side of the interface does not see it. And
in three weeks nobody can tell whether the implementation matches the analysis or an
answer that was given in a comment thread.

So **every answer becomes a `D-<nnn>` entry in `decisions.md`, and the package gets a new
version.** The tracker reply points at the decision; it is not the decision.

## 1. The inbox

```
/wizrelay:hub-inbox
```

1. Collects the unanswered `[WIZRELAY-Q]` comments on published tasks.
2. For each question:
   - If the package already answers it, drafts a short reply pointing at the relevant
     section.
   - If it does not, works out the options, their impact (which criteria, contracts, scope
     and roles) and a proposed decision.
3. Adds the decisions you approve to `decisions.md` (`## D-004 … (v2, date)`), and updates
   the criterion, contract and scope files where needed.
4. Replies to the question comment with `[WIZRELAY-A] Q-001 → D-004`.
5. Suggests `/wizrelay:hub-validate` and `/wizrelay:hub-publish` if the package changed.

## Four kinds of question

Knowing which kind you have changes what the decision should say. The inbox says which it
thinks each one is; check it.

| Kind | What happened | What the decision does |
|---|---|---|
| **The package is silent** | Something genuinely was not decided | Decide it |
| **The answer exists but not findably** | It is in `research.md`, where nobody looks | Decide it anyway, as a decision, so it is in the right place next time |
| **The premise is wrong** | The developer misread the scope or a contract | Clarify, and say what was misread — that usually means the package was unclear |
| **The scope is wrong** | The task genuinely needs something outside the published scope | A scope change, deserving the consideration the original scope got |

The second kind is the one worth noticing. If a developer could not find an answer that was
there, the next developer will not find it either. Moving it into `decisions.md` is not
bureaucracy; it is putting it where people look.

## 2. Writing the decision

```markdown
## D-004 Retry-After is capped at one hour (v2, 2026-10-30)
- Question: Q-001 — what upper bound applies to Retry-After?
- Decision: cap it at 3600 seconds.
- Rationale: a longer value makes clients look stuck, and the quota window never exceeds a
  day anyway.
- Impact: AC-1, and C-2 in contracts.md
```

Two rules:

**The decision has to be implementable without further interpretation.** If a developer
has to decide anything to implement your decision, it is not finished.

**Fill in `Impact` honestly.** If a criterion has to change, say so — and change it in the
same version. A decision that contradicts a criterion it did not update is worse than no
decision.

## 3. Publish and reply

`/wizrelay:hub-publish CU-86c1abcd` with a summary naming the decisions. Then the reply,
with your approval:

```text
[WIZRELAY-A] Q-001 → D-004
Retry-After is capped at 3600 seconds. Rationale: a longer value makes clients look stuck.
research v2 is published; run /wizrelay:sync in your repository.
```

## 4. Status

```
/wizrelay:hub-status CU-86c1abcd
```

| Role | Last report | Result | Missing | Scope |
|---|---|---|---|---|
| backend | 2026-11-02 | PARTIAL | AC-3 NOT COVERED | clean |
| frontend | 2026-11-01 | PASS | — | clean |

It also lists open questions with how long each has been waiting, which is the most
time-sensitive thing on the page. A developer blocked on a decision is a developer not
working.

## Scope expansion requests

A developer reporting that they need a file outside the scope — say `app/core/errors.py` —
is the most common question you will get. The flow:

1. Evaluate the request. Does the criterion genuinely require it?
2. If it does, add the file to the `allow` list in `task.json` and write the reason in
   `decisions.md`.
3. Publish the new version.

After `/wizrelay:sync`, the developer can edit the file.

Resist the temptation to widen the scope generously "to avoid more questions". A scope wider
than the work makes the protection meaningless, and the questions were the signal that the
analysis was incomplete.

## The loop without a tracker

With `tracker: none`, the loop still closes — it just needs a person to carry the question
across:

1. The developer's `/wizrelay:ask` writes `Q-001` into `questions.md`.
2. `questions.md` lives in the developer's repository, so they send the question however the
   team communicates.
3. The researcher records the decision and publishes a new version.
4. The developer's next session reports it, and `/wizrelay:sync` brings it in.

The one thing to watch: nothing reminds the researcher that a question is waiting. The
`ask` skill says so when it writes one.

## Next

[10. Model and effort routing](10-routing.md).

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 8. Developer: implement a task](08-developer-workflow.md) | [Contents](README.md) | [10. Model and effort routing →](10-routing.md) |
<!-- /nav:bottom -->
