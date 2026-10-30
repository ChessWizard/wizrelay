<!-- nav:top -->
[Documentation](README.md) › **7. Researcher: prepare and publish** &nbsp;·&nbsp; [Türkçe](../tr/07-researcher-workflow.md)
<!-- /nav:top -->

# Researcher: prepare and publish

Writing a task package, file by file, and the two gates it passes before developers can
pull it.

## The flow

```
/wizrelay:hub-new  →  write the package  →  /wizrelay:hub-validate  →  /wizrelay:hub-publish
     (v0, draft)                            (anything blocking?)       (v1, published)
```

Draft packages are invisible to developers; only a published package can be pulled.

## Step 1 — Start the package

Open Claude Code in the hub. If you want Claude to read the relevant projects' code too,
add them:

```bash
cd research-hub
claude --add-dir ../api-service --add-dir ../web-app
```

Then:

```
/wizrelay:hub-new 86c1abcd backend,frontend
```

Claude will:

1. Read the task from the tracker: title, description, subtasks, **and comments**.
2. Create the directory from the template:
   `tasks/CU-86c1abcd-tenant-daily-api-request-quota/` (`version: 0`, `status: draft`).
3. Read the repositories you added, read-only, and cite its findings with file paths.
4. Draft the package files.
5. Ask **you** about anything it cannot settle. These questions are not passed to the
   developer; they become entries in `decisions.md` by your decision.

This command runs at high effort; on a substantial task it can take a few minutes.

The comments are the part worth insisting on. Tracker discussions carry decisions that
never reach the description, and a package that misses them re-asks a question the team
already settled.

## Step 2 — Write the package, file by file

### `research.md` — the analysis

Suggested sections:

1. Problem and the measurable goal
2. Current state, with evidence
3. The chosen approach
4. Alternatives rejected
5. Interaction between roles
6. Risks and edge cases
7. Scope summary
8. Assumptions

In a good analysis, **every claim rests on a citation** — "`send_template_message` in
`app/api/v1/messages.py:48`…" — and nothing is phrased in a way that invites
interpretation. "Appropriately", "if needed" and "handle gracefully" are the words to
delete.

An uncited claim is the most common defect in a research package, and the most expensive
one: a developer trusts it.

### `acceptance.md` — the acceptance criteria

This decides what a developer will treat as "done" and what `/wizrelay:verify` will prove.

```markdown
## AC-1 [backend] A request over quota is rejected with 429
- **Given** a tenant on the `basic` plan has made 1,000 requests today (UTC)
- **When** `POST /v1/exports` is called for the 1,001st
- **Then** the response is `429`, the body matches `contracts.md#C-2` exactly, and the
  request is not served
- **Verification:** `tests/quota/test_quota_exceeded.py`
```

| Badly written | The problem | Written well |
|---|---|---|
| "An appropriate error should be returned when the quota is exceeded" | "Appropriate" invites interpretation | "The response is 429, the body matches C-2 exactly" |
| "Performance should be good" | Not measurable | "p95 < 200 ms (local, 1,000 requests)" |
| No role in the heading | Which repository implements it is unclear | `## AC-1 [backend] …` |
| No verification line | What counts as proof is unclear | `**Verification:** tests/quota/…` |

Leave the role list in brackets empty and the criterion applies to every role.

### `contracts.md` — the contract between roles

The endpoint and event schemas, and the error bodies, that backend and frontend must match
exactly. A field name or an error code is defined **only** here; criteria and role files
refer to it.

```markdown
## C-1 Quota usage endpoint
- Producer: backend · Consumer: frontend
- `GET /v1/tenants/{tenant_id}/quota/template-messages`
- 200 response: `{ "used": 250, "limit": 1000, "warning_threshold": 0.8, "resets_at": "2026-10-30T00:00:00Z" }`
```

### `decisions.md` — the decision record

```markdown
## D-001 The quota day resets on UTC (v1, 2026-10-29)
- Decision: the counter's day is determined by the UTC date.
- Rationale: tenant timezone data is not consistent.
- Impact: AC-1, AC-4
```

**Decisions are never deleted.** If one changes, add a new decision and write
"Superseded by: D-00x" on the old one. When two conflict, the newest applies.

Write the `Decision` so it can be implemented without further interpretation. "Handle this
gracefully" is not a decision. "Return 429 with `Retry-After` capped at 3600 seconds" is.

### `roles/<role>.md` — the role's slice

This role's work, the criteria that apply to it, hints (which guide, and do not bind),
pitfalls, and the test expectation.

The pitfalls section is the part nobody else can produce. "Incrementing before the provider
confirms the send double-counts a failed send" is the kind of thing a reasonable developer
gets wrong once, and it costs an afternoon.

### `scope.md` — the scope in prose

Why the boundaries are where they are; what will not be touched, and why not. A developer
who sees an obvious improvement needs to know it was a decision rather than an oversight.

### `task.json` — the machine-readable definition

This is the file that sets the plugin's rules. The fields you edit by hand: `roles`,
`repos`, `enforcement`, `scope`, `routing`. Do not touch `version`, `status`, `updated_at`
or `changelog` — the publish command manages those.

```json
{
  "scope": {
    "backend": {
      "allow": ["app/quota/**", "app/api/v1/messages.py", "app/api/v1/tenants.py",
                "app/core/errors.py", "alembic/versions/**", "tests/quota/**"],
      "deny": ["app/billing/**", "app/consumers/**", "app/auth/**"]
    },
    "frontend": {
      "allow": ["src/features/quota/**", "src/api/quota.ts", "src/lib/http/errors.ts"],
      "deny": ["src/features/billing/**"]
    }
  }
}
```

When you write a scope:

- **Start narrow.** If a developer genuinely needs another file, a question comes back and
  you widen it. A scope wider than necessary makes the protection meaningless.
- **Do not forget the adjacent files.** Tests, migrations and translation files belong in
  the scope too.
- **Put the critical areas in `deny`.** `deny` blocks even in `ask` mode.
- Glob rules are in [11. Scope protection](11-scope-protection.md).

Enforcement mode:

| Mode | An out-of-scope edit | When |
|---|---|---|
| `strict` | Blocked | Default; work with a clear scope |
| `ask` | The developer is asked | Exploratory work whose scope cannot be drawn fully |
| `off` | Free (researcher files are still protected) | Spikes and prototypes |

Routing signals are in [10. Routing](10-routing.md).

The `repos` field maps a role to a GitHub `owner/repo`; the deep links in the publish
comment are built from it.

### Extra files

You can add any file to a package — `sequence.md`, `api-examples.json` — and all of it
reaches the developer read-only. **Files beginning with a dot** (`.notes/`,
`.validation.md`) stay with you and never reach a developer.

## Step 3 — Validate

```
/wizrelay:hub-validate CU-86c1abcd
```

Validation has two passes.

**1. Structural, deterministic.**

| Errors (block publication) | Warnings (do not block) |
|---|---|
| Unfilled `{{…}}` placeholders | `TODO` |
| `TBD` or `???` | `ambiguity: high` |
| A criterion naming an unknown role | An empty `contracts.md` in a multi-role package |
| A role with no criterion | A criterion with no verification line |
| An empty `allow` list | A criterion with no Given/When/Then |
| An invalid glob | |

Every finding carries a `file:line`.

**2. Semantic, by the `research-critic` agent.** It looks at:

- Does every requirement in the tracker have a criterion?
- Are the criteria testable by someone who did not write them?
- Do the files contradict each other — a field name in `contracts.md` differing from the
  one in a criterion?
- Is the scope sufficient to implement the criteria?

The result is written to `.validation.md`, and it stays in the hub. Nothing is published
while a blocking finding remains.

## Step 4 — Publish

```
/wizrelay:hub-publish CU-86c1abcd
```

In order:

1. Asks for a one-sentence summary of this version ("First publication", the first time).
2. Re-runs the structural validation and stops if there is an error.
3. Updates `task.json`: `version` 0 → 1, `status: published`, a changelog entry.
4. Commits: `research(CU-86c1abcd): v1 — First publication`.
5. Pushes, or opens a pull request, with your approval.
6. With your approval, comments on the tracker:

```text
[WIZRELAY-PUBLISH] CU-86c1abcd — research v1 published
Summary: First publication
- backend: AC-1, AC-2, AC-3, AC-4
- frontend: AC-5, AC-6
To start, in the relevant repository inside Claude Code:
/wizrelay:pull CU-86c1abcd
Deep link (paste into your browser's address bar):
- backend: claude-cli://open?repo=acme/api-service&q=%2Fwizrelay%3Apull%20CU-86c1abcd
- frontend: claude-cli://open?repo=acme/web-app&q=%2Fwizrelay%3Apull%20CU-86c1abcd
```

The deep link opens Claude Code on the developer's machine, in the right repository, with
the command pre-filled and **not sent** — they press Enter. Some platforms, GitHub among
them, strip links with a custom scheme, which is why it is given as text in a code block.

The summary line matters more than it looks: it is what a developer reads during
`/wizrelay:sync`. Write what changed and why, not "updates".

## Version rules

- **Changing a published package means a new version:** edit → validate → publish (v2).
- **Never rewrite git history.** Do not force-push; developers' lock files are tied to
  commits.
- **Archiving:** for a cancelled task, set `status` to `archived` in `task.json` by hand and
  commit. This is the one exception to not editing the status field. An archived package
  cannot be pulled again.

## Without Claude

The same flow runs from the command line:

```bash
wizrelay hub new 86c1abcd --title "Tenant daily API request quota" --roles backend,frontend
# edit the package files
wizrelay hub validate CU-86c1abcd
wizrelay hub publish-prep CU-86c1abcd --summary "First publication"
git add tasks && git commit -m "research(CU-86c1abcd): v1 — First publication" && git push
wizrelay hub comment CU-86c1abcd     # paste the output as a tracker comment
```

Entirely by hand works too: copy `templates/package/` to `tasks/<ID>-<slug>/` and fill it
in. `hub validate` checks that package by exactly the same rules.

## Before you publish — checklist

- [ ] Every tracker requirement maps to at least one criterion
- [ ] Every criterion has a role, Given/When/Then and a verification line
- [ ] Every interface between roles is defined in `contracts.md`
- [ ] No open questions remain; the decisions are in `decisions.md`
- [ ] The scope is narrow, includes tests and migrations, and has the critical areas in `deny`
- [ ] The signals were chosen with a reason you could state out loud
- [ ] `/wizrelay:hub-validate` shows nothing blocking

## Next

[8. Developer: implement a task](08-developer-workflow.md) — the other side of the handoff.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 6. Connect a repository](06-connect-repository.md) | [Contents](README.md) | [8. Developer: implement a task →](08-developer-workflow.md) |
<!-- /nav:bottom -->
