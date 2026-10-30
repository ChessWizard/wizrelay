<!-- nav:top -->
[Documentation](README.md) › **15. Worked example: a task end to end** &nbsp;·&nbsp; [Türkçe](../tr/15-walkthrough.md)
<!-- /nav:top -->

# Worked example: a task end to end

One task, from a tracker entry to a merged pull request, with the real file contents and
the real command output at every step.

Everything in this section is in the repository under
[`examples/`](../../examples/), so you can run it rather than read it.

## The setup

The **acme** team is implementing `CU-86c1abcd`, "Tenant daily API request quota",
across two repositories.

```
acme/research-hub              the team hub (private)
acme/api-service               role: backend
acme/web-app                   role: frontend
```

Organisation and repository names are examples; substitute your own.

## The directory structure, all three repositories

### The hub

```
research-hub/
├── wizrelay-hub.json
├── CLAUDE.md                                  the researcher protocol
├── .mcp.json                                  the ClickUp connection
├── policies/
│   └── routing-policy.json                    the team's own routing policy
├── templates/package/                         team package templates (optional)
└── tasks/
    └── CU-86c1abcd-tenant-daily-api-request-quota/
        ├── task.json                           ← the rules
        ├── research.md                         ← the analysis
        ├── scope.md                            ← the boundary, in prose
        ├── acceptance.md                       ← what "done" means
        ├── decisions.md                        ← the decision record
        ├── contracts.md                        ← the interface between roles
        ├── roles/
        │   ├── backend.md
        │   └── frontend.md
        └── .validation.md                      ← private; never leaves the hub
```

### The backend project, after `init` and `pull`

```
api-service/
├── CLAUDE.md                                  @.wizrelay/PROTOCOL.md appended
├── .claude/settings.json                      deny rules added
├── .gitignore                                 two lines added
├── .mcp.json                                  the ClickUp connection
├── app/
│   ├── quota/                              ← in scope
│   ├── api/limits.py                       ← in scope
│   └── billing/invoice.py                  ← explicitly denied
├── tests/quota/                            ← in scope
└── .wizrelay/
    ├── config.json                            hub, role, tracker, language
    ├── config.local.json                      personal, gitignored
    ├── profile.json                           the repository profile
    ├── PROTOCOL.md                            the working rules
    ├── .active-task                           gitignored
    └── tasks/
        └── CU-86c1abcd-tenant-daily-api-request-quota/
            ├── task.json, research.md, scope.md, acceptance.md,
            │   contracts.md, decisions.md, roles/*.md  ← read-only
            ├── .lock.json                              ← version, hub commit, hashes, routing
            ├── plan.md                                 ← yours
            └── questions.md                            ← yours
```

Note what is **not** there: `.validation.md` did not come across. Nothing beginning with a
dot ever does.

---

## Monday 10:00 — the researcher starts the package

```bash
cd research-hub
claude --add-dir ../api-service --add-dir ../web-app
```

```
/wizrelay:hub-new 86c1abcd backend,frontend
```

```text
Draft package CU-86c1abcd created in tasks/CU-86c1abcd-tenant-daily-api-request-quota.
  + task.json
  + acceptance.md
  + contracts.md
  + decisions.md
  + research.md
  + roles/backend.md
  + roles/frontend.md
  + scope.md

Next: fill in the package, then run /wizrelay:hub-validate CU-86c1abcd.
```

Claude read the ClickUp task and its comments, read both repositories, and left three
questions for the researcher — not for the developers.

## Monday 11:30 — the package, file by file

### `research.md`

```markdown
# Research — CU-86c1abcd

## Problem

Tenants can call the API with no daily limit at all. A single misconfigured tenant
exhausted the shared upstream quota last month and blocked every other tenant.

## Current state, with evidence

`app/api/limits.py:14` serves requests without any per-tenant counter. The only limit is the
provider's global rate limit, enforced in `app/api/client.py:112`.

## Approach

A per-tenant daily counter in Redis, checked before the send and incremented after a
successful one. The limit comes from the tenant's plan.

## Alternatives rejected

| Alternative | Why not |
|---|---|
| Postgres counter | A write per message on the hot path; Redis already carries session state. |
| Provider-side quota | The provider bills per account, not per tenant. |

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Redis unavailable | Sends fail closed or open | Fail open and log; a quota is not a safety control. |
```

Every claim about the current state cites a path and a line. That is the difference between
an analysis a developer can trust and one they have to re-derive.

### `acceptance.md`

```markdown
## AC-1 [backend] A tenant at its daily limit is rejected

Given a tenant whose daily counter equals its plan limit
When the tenant makes one more request
Then the request is rejected with 429 and a Retry-After header
Verification: `pytest -q tests/quota/test_limit.py`

## AC-2 [backend] An accepted request increments the counter

Given a tenant below its limit
When a request is accepted
Then the tenant's daily counter increases by exactly one
Verification: `pytest -q tests/quota/test_counter.py`

## AC-3 [frontend] The remaining quota is visible

Given an admin on the usage screen
When the page loads
Then the remaining daily quota for the tenant is shown
Verification: `npm test -- quota-indicator`
```

### `contracts.md`

```markdown
## C-1 Quota status endpoint

- Producer: backend
- Consumer: frontend

### Shape

{ "limit": 1000, "used": 240, "remaining": 760, "resets_at": "2026-10-31T00:00:00Z" }

### Rules

- `GET /api/tenants/{id}/quota`, 200 on success, 404 when the tenant does not exist.
- `remaining` is never negative.
- A request rejected by the quota returns 429 with `Retry-After` in seconds, capped at 3600.
```

### `decisions.md`

```markdown
## D-001 Fail open when Redis is unavailable (v1, 2026-10-30)

- Question: What happens to a request when the counter store cannot be reached?
- Decision: Allow the request and log a warning. The quota is a cost control, not a safety
  control, so an outage must not stop customer traffic.
- Rationale: A hard failure converts a Redis incident into an API outage.
- Impact: AC-1 applies only when the counter is readable.
```

### `task.json` — the part that is enforced

```json
{
  "schema_version": 1,
  "id": "CU-86c1abcd",
  "tracker": { "type": "clickup", "ref": "86c1abcd" },
  "title": "Tenant daily API request quota",
  "slug": "tenant-daily-api-request-quota",
  "version": 1,
  "status": "published",
  "roles": ["backend", "frontend"],
  "repos": { "backend": "acme/api-service", "frontend": "acme/web-app" },
  "enforcement": "strict",
  "scope": {
    "backend": {
      "allow": ["app/quota/**", "app/api/limits.py", "tests/quota/**"],
      "deny": ["app/billing/**"]
    },
    "frontend": {
      "allow": ["src/features/usage/**"],
      "deny": []
    }
  },
  "routing": {
    "signals": { "complexity": "medium", "risk": "high", "ambiguity": "low" },
    "role_signals": { "frontend": { "complexity": "low", "risk": "low", "ambiguity": "low" } },
    "overrides": {}
  }
}
```

Three things to notice:

- `app/billing/**` is in `deny`, not merely absent from `allow`. A `deny` blocks even in
  `ask` mode.
- `tests/quota/**` is in `allow`. Forgetting the tests is the most common scope mistake.
- `role_signals` lowers the frontend's signals, which is what gives the two repositories
  different tiers.

## Monday 11:45 — validate

```
/wizrelay:hub-validate CU-86c1abcd
```

```text
## Validation — CU-86c1abcd-tenant-daily-api-request-quota

No errors and no warnings.
```

Before the package was filled in, the same command said this — and that is the mechanism
working, not failing:

```text
### Errors (45) — these block publication
- acceptance.md:6: unfilled placeholder {{Title}}
- acceptance.md:6: AC-1 names unknown role '{{backend}}'
- acceptance.md:8: unfilled placeholder {{the starting state}}
- …
```

A scaffolded package is deliberately invalid until a person fills it in.

## Monday 12:00 — publish

```
/wizrelay:hub-publish CU-86c1abcd
```

```text
CU-86c1abcd prepared for publication as v1.

Next: commit tasks/CU-86c1abcd-tenant-daily-api-request-quota, push, then post the
comment from `wizrelay hub comment CU-86c1abcd`.
```

The comment, after approval:

```text
[WIZRELAY-PUBLISH] CU-86c1abcd — research v1 published

Tenant daily API request quota

**backend**
- AC-1: A tenant at its daily limit is rejected
- AC-2: A successful send increments the counter

```
/wizrelay:pull CU-86c1abcd
```

Or open a session directly (paste into your browser's address bar):
```
claude-cli://open?repo=acme%2Fapi-service&q=%2Fwizrelay%3Apull%20CU-86c1abcd
```

**frontend**
- AC-3: The remaining quota is visible

```
/wizrelay:pull CU-86c1abcd
```

Or open a session directly (paste into your browser's address bar):
```
claude-cli://open?repo=acme%2Fweb-app&q=%2Fwizrelay%3Apull%20CU-86c1abcd
```
```

The `q` parameter is fully encoded — `%2Fwizrelay%3Apull` — and the link is in a code block
because GitHub strips `claude-cli://` links from a Markdown link, leaving the label and
dropping the URL.

## Monday 13:00 — the backend developer pulls

```
/wizrelay:pull CU-86c1abcd
```

Real output from the shipped example:

```text
CU-86c1abcd v1 — Tenant daily API request quota
8 researcher file(s) copied.
Created for you: plan.md, questions.md
In scope: app/quota/**, app/api/limits.py, tests/quota/**

Routing: T4-high-risk (score 10)
  plan       opus / xhigh
  implement  opus / high + advisor opus
  verify     opus / xhigh
  ask        opus / low
Modifiers applied: test_maturity_low, touches_critical_paths

Launch this task's session with:
  claude --model opus --effort high --advisor opus --name 'CU-86c1abcd Tenant daily'
```

Where the 10 came from:

| Source | Contribution |
|---|---|
| The package's signals: complexity medium, risk high, ambiguity low | 2 + 3 + 1 = 6 |
| This repository's `test_maturity: low` | +2 |
| This repository's `critical_paths` overlapping the backend scope | +2 |

The last two are worth 2 rather than 1 because the hub's own
`policies/routing-policy.json` overrides the default weights. Delete that file and the same
task scores 8 — T3-critical — on the plugin's defaults.

## Monday 13:10 — the frontend developer pulls the same package

```bash
cd ../web-app
```

```
/wizrelay:pull CU-86c1abcd
```

```text
Routing: T1-routine (score 3)
  plan       sonnet / medium
  implement  sonnet / medium
  verify     sonnet / medium
  ask        sonnet / low

Launch this task's session with:
  claude --model sonnet --effort medium --name 'CU-86c1abcd Tenant daily'
```

**Same hub, same package, two roles, two tiers.** The package lowered the signals for the
frontend role, and nothing in that repository's profile adds a modifier. This is why routing
is computed per role rather than per task.

## Monday 13:15 — the session knows what it is doing

Every session start, and after every compaction, this reaches the model:

```text
## Active research package (wizrelay)
CU-86c1abcd v1 — Tenant daily API request quota. Role: backend. Enforcement: strict.
Researcher files (read-only here): `acceptance.md`, `contracts.md`, `decisions.md`,
`research.md`, `roles/backend.md`, `roles/frontend.md`, `scope.md`, `task.json`
In scope: `app/quota/**`, `app/api/limits.py`, `tests/quota/**`
Explicitly denied: `app/billing/**`
Routing: T4-high-risk, score 10. Implementation runs on opus at high effort.

Acceptance criteria for this role (2):
- AC-1: A tenant at its daily limit is rejected
- AC-2: A successful send increments the counter

Plan progress: 0 of 1 steps complete. Next: AC-1 — the counter and the pre-send check
1 question(s) are still open in questions.md.

The working rules are in .wizrelay/PROTOCOL.md, imported through CLAUDE.md.
```

And on every prompt, one line:

```text
[WIZRELAY] Active task CU-86c1abcd · research v1 · role backend · scope mode strict · open questions 1
```

## Monday 13:30 — the checks, demonstrated

Real decisions from the shipped example:

| File | Verdict | Why |
|---|---|---|
| `app/quota/service.py` | **allowed** | matches `app/quota/**` |
| `app/billing/invoice.py` | **deny** | matches the `deny` pattern `app/billing/**` |
| `README.md` | **deny** | outside the role's scope, and the mode is `strict` |
| `.wizrelay/tasks/…/acceptance.md` | **deny** | a researcher file, read-only in every mode |
| `.wizrelay/tasks/…/plan.md` | **allowed** | a developer file |
| `poetry.lock` | **allowed** | incidental at any depth |
| `CLAUDE.md` | **allowed** | written by `init`; incidental |
| `/etc/hosts` | **no decision** | outside the repository; the plugin does not interfere |

The denial a developer actually sees:

```text
README.md is outside the scope of CU-86c1abcd. In scope: app/quota/**,
app/api/limits.py, tests/quota/**. Raise a question with /wizrelay:ask rather
than widening the scope locally.
```

And for a researcher file:

```text
acceptance.md belongs to the researcher and is read-only here (CU-86c1abcd). Ask through
/wizrelay:ask; the answer arrives as a new package version.
```

## Monday 15:00 — a question the package cannot answer

```
/wizrelay:ask is there an upper bound on Retry-After?
```

`contracts.md#C-1` says "capped at 3600", so this one is answered from the package, with
the citation. Suppose it had not been:

```text
The package does not answer this. `contracts.md` C-1 specifies Retry-After in seconds but
states no upper bound, and `decisions.md` has nothing on it.

I have recorded it as Q-001 in questions.md:

  ## Q-001 Upper bound for Retry-After
  Status: OPEN
  Asked: 2026-10-30
  Context: blocks AC-1

  Retry-After is specified in seconds with no maximum. Options: (a) cap at 3600 seconds,
  (b) cap at the time to the next UTC midnight, (c) no cap. Absent an answer I would
  implement (b), because the quota window is daily — but a client library treating a
  large value as a hard stop is the risk.

Shall I post this to the tracker as [WIZRELAY-Q]?
```

Nothing is posted without a yes. And no answer is invented — that is the single most
important behaviour in the system, because a plausible answer the researcher never gave
looks like a decision and gets implemented.

## Monday 16:00 — the researcher answers

```
/wizrelay:hub-inbox
```

The decision, added to `decisions.md`:

```markdown
## D-002 Retry-After is capped at one hour (v2, 2026-10-30)

- Question: Q-001 — what upper bound applies to Retry-After?
- Decision: Cap it at 3600 seconds.
- Rationale: A longer value makes clients look stuck, and the quota window never exceeds a
  day anyway.
- Impact: AC-1, and C-1 in contracts.md.
```

Then `/wizrelay:hub-publish CU-86c1abcd` → v2, and the reply:

```text
[WIZRELAY-A] Q-001 → D-002
Retry-After is capped at 3600 seconds. research v2 is published; run /wizrelay:sync.
```

## Tuesday 09:00 — the developer syncs

Session start:

```text
CU-86c1abcd: you have v1, the hub has v2. Run /wizrelay:sync before continuing.
```

```
/wizrelay:sync
```

Real output:

```text
CU-86c1abcd updated from v1 to v2.
Changed: acceptance.md, decisions.md, task.json
Restored from the hub (they had been modified locally): scope.md

--- a/decisions.md
+++ b/decisions.md
@@ -8,2 +8,9 @@
  - Rationale: A hard failure converts a Redis incident into an API outage.
  - Impact: AC-1 applies only when the counter is readable.
+
+## D-002 Retry-After is capped at one hour (v2, 2026-10-30)
+
+- Question: Q-001 — what upper bound applies to Retry-After?
+- Decision: Cap it at 3600 seconds.

decisions.md changed. Re-read it, then update plan.md and close any question it answers.
```

Three things happened in that one command: the version moved, a locally edited researcher
file was put back, and the next-step message changed because `decisions.md` was among the
changes.

## Tuesday 14:00 — verify

```
/wizrelay:verify
```

```text
# Verification — CU-86c1abcd

Verified by: wizrelay:test-engineer

Result: PARTIAL

## Acceptance criteria

| AC | Evidence (command) | Result |
|---|---|---|
| AC-1 | `pytest -q tests/quota/test_limit.py` (3 passed) | PASS |
| AC-2 | `pytest -q tests/quota/test_counter.py` (1 passed) | PASS |
| AC-3 | — | NOT APPLICABLE (frontend role) |

Full suite: `pytest -q` — 184 passed.

## Scope audit

## Scope audit — CU-86c1abcd (backend)
No violations. 6 changed path(s) are all accounted for.

## Not verified

The Redis-unavailable path from D-001 has no test. Suggested:
tests/quota/test_counter_store_unavailable.py
```

`PARTIAL` rather than `PASS`, because a decision in the package has no test behind it. The
verifier **cannot** write that test — its edit tools are removed by configuration — so the
gap is reported rather than quietly closed.

## Tuesday 15:00 — the gap, then green

The developer asks the main session to write the missing test, then runs
`/wizrelay:verify` again:

```text
Result: PASS
```

And the tracker comment, after approval:

```text
[WIZRELAY-VERIFY] CU-86c1abcd — backend — PASS
```

## Tuesday 15:30 — the pull request

```bash
git add app/quota tests/quota app/api/limits.py .wizrelay/tasks/
git commit -m "feat(quota): per-tenant daily API request quota (AC-1, AC-2)"
git push -u origin feature/CU-86c1abcd-tenant-quota
```

Committing `.wizrelay/tasks/` is what lets the CI gate know what the scope is. The branch
name carries the identifier, which is how the gate finds the task.

CI:

```text
## Scope audit — CU-86c1abcd (backend)
No violations. 7 changed path(s) are all accounted for.

### In scope (5)
- app/api/limits.py
- app/quota/__init__.py
- app/quota/service.py
- tests/quota/test_counter.py
- tests/quota/test_limit.py

### Incidental (build artefacts and wizrelay setup)
- poetry.lock
```

Green. Merge.

And if the developer had also touched billing:

```text
2 violation(s) found.

### Explicitly denied
- `app/billing/invoice.py` — `app/billing/**`

### Outside this role's scope
- `README.md`
```

Exit code 1, the check is red, the merge is blocked. That is the layer that does not depend
on the session behaving well.

---

## Three more shapes of the same loop

### A scope that turns out to be wrong

The backend developer needs `app/core/errors.py` to add the `Retry-After` header. It is not
in v1's scope.

1. Claude tries the edit; the hook blocks it and explains why.
2. The developer writes the reason in `questions.md` as Q-002 and `/wizrelay:ask` sends it.
3. The researcher sees it in `/wizrelay:hub-inbox`, adds the file to `allow`, writes D-003
   with the reason, and publishes v3.
4. `/wizrelay:sync`, and the file is now editable.

Four steps instead of one silent edit — and at the end, every other developer on the task
knows the scope changed and why.

### A mechanical task

"Move every error message into the i18n catalogue."

- The researcher sets `routing.signals.kind: "mechanical"` and a narrow scope
  (`src/i18n/**`, `src/components/errors/**`).
- `pull` suggests T0: implementation on `haiku`, verification on `sonnet`.

A rename does not need Opus, and routing is where that gets decided once rather than
guessed every time.

### A personal project with GitHub Issues

1. Create a private `personal-hub` and run `/wizrelay:hub-init` with tracker `github` and
   role `backend`.
2. In the project: `/wizrelay:init backend git@github.com:you/personal-hub.git`.
3. For issue `#42`: `/wizrelay:hub-new 42 backend` → the package is `GH-42-…`.
4. The rest is identical. This hub is completely separate from the team's — different
   caches, keyed by hub identity, so the same identifier in both never mixes.

## Run it yourself

```bash
cp -R examples/hub examples/dev-backend examples/dev-frontend /tmp/wizrelay-demo/
cd /tmp/wizrelay-demo
for d in hub dev-backend dev-frontend; do (cd $d && git init -q -b main . && git add -A && git commit -qm init); done

cd hub         && wizrelay hub validate CU-86c1abcd
cd ../dev-backend  && wizrelay pull CU-86c1abcd && wizrelay route
cd ../dev-frontend && wizrelay pull CU-86c1abcd && wizrelay route
```

The example hub uses `hub.path`, so nothing is cloned and no network is used. Then break
something on purpose:

```bash
cd ../dev-backend
echo "x" >> app/billing/invoice.py
echo "y" > README.md
wizrelay audit --base ""     # exits 1 and names both
```

## Next

[16. Troubleshooting](16-troubleshooting.md) when something does not behave as it does here.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 14. Customisation](14-customisation.md) | [Contents](README.md) | [16. Troubleshooting →](16-troubleshooting.md) |
<!-- /nav:bottom -->
