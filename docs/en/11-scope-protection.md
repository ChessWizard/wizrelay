<!-- nav:top -->
[Documentation](README.md) › **11. Scope protection** &nbsp;·&nbsp; [Türkçe](../tr/11-scope-protection.md)
<!-- /nav:top -->

# Scope protection

The five layers, what each one actually stops, the glob syntax, and the bypasses that are
documented rather than hidden.

## The layers

| Layer | When | What it does |
|---|---|---|
| 1. Permission rules (`.claude/settings.json`) | Every edit | Protects researcher files absolutely, including through `sed`, `tee` and shell redirections |
| 2. Edit check (a `PreToolUse` hook) | Every edit | Enforces the scope, and explains why to both Claude and you |
| 3. End-of-turn audit (a `Stop` hook) | At the end of every response | Scans every change in git and warns |
| 4. `/wizrelay:verify` | When the work is done | Records violations in the report |
| 5. CI gate | On the pull request | Blocks the merge |

No single layer is enough, and each one catches what the layer above it misses. Layer 1 is
absolute but static — it cannot know which task is active. Layer 2 knows the live scope but
only sees Claude's file tools. Layer 3 sees everything git sees but only after the fact.
Layer 5 is the only one that does not run inside the developer's own session.

## Modes

| Mode | Behaviour |
|---|---|
| `strict` | An out-of-scope edit is blocked |
| `ask` | An out-of-scope edit asks for approval; the `deny` list still blocks absolutely |
| `off` | No scope check; researcher files are **still** protected |

The researcher chooses the mode per task
([7. Researcher workflow](07-researcher-workflow.md)).

`off` still protecting researcher files is deliberate. `off` turns off the *scope*; an
edited `acceptance.md` would silently change what "done" means and make the lock disagree
with the hub.

## The decision order

Layer 2 decides in this order, and the order is the design:

```
1. a path outside the repository  → no decision
2. a researcher file              → deny, in every mode
3. a developer file or .wizrelay/ → no decision
4. no active task, or mode `off`  → no decision
5. no scope defined for the role  → ask
6. an explicit `deny` match       → deny, in every mode
7. an `allow` or incidental match → no decision
8. anything else                  → deny in `strict`, ask in `ask`
```

Step 2 sits above step 4 on purpose, which is what makes "off still protects researcher
files" true. Step 5 asks rather than guessing: a task that says nothing about your role is
a configuration gap, not a licence.

"No decision" means Claude Code's normal permission flow is left untouched. The hook never
returns "allow", because that would grant permission you never gave.

## Glob cheat sheet

| Pattern | Matches | Does not match |
|---|---|---|
| `app/quota/**` | `app/quota/service.py`, `app/quota/x/y.py` | `app/quota` itself, `app/quotas/a.py` |
| `app/quota` | `app/quota` and everything below it | `app/quotas/a.py` |
| `src/*.ts` | `src/a.ts` | `src/b/a.ts` |
| `tests/**/test_*.py` | `tests/test_x.py`, `tests/a/b/test_x.py` | `tests/a/x_test.py` |
| `alembic/versions/*.py` | `alembic/versions/0012_quota.py` | `alembic/env.py` |
| `poetry.lock` (no slash) | `poetry.lock` at **any** depth | — |
| `build/` | everything below `build` | — |

Rules:

- Paths are relative to the repository root.
- `**` crosses directories; `*` never crosses a `/`.
- `..`, an absolute path and a drive letter are all rejected.
- A pattern with no slash matches that name at any depth, the way a gitignore line does.

## Always free

- Developer-owned task files: `plan.md`, `questions.md`, `verification.md`, `notes/`
- Lock files at any depth: `poetry.lock`, `uv.lock`, `package-lock.json`,
  `pnpm-lock.yaml`, `yarn.lock`, `go.sum`, `Cargo.lock`, `composer.lock`, `Gemfile.lock`,
  `packages.lock.json`, `Pipfile.lock`
- The files `wizrelay init` itself wrote: `CLAUDE.md`, `.gitignore`,
  `.claude/settings.json`, `.claude/settings.local.json`, `.mcp.json`
- Everything under `.wizrelay/`
- The `incidental_allow` list in `profile.json`
- Files outside the repository — the plugin makes no decision; Claude Code's normal
  permissions apply

The third group is there for a specific reason. Without it, the very first audit after
`init` would report four violations, in the one report a developer has no prior reason to
trust. They are reported as *incidental* rather than excluded, so a reviewer still sees
them.

## What it protects, and what it does not

**This is a guardrail against accidental drift, not a security boundary.** Someone who
disables the plugin, edits the settings, or writes files from a script can get around it.

| Layer | Does not stop |
|---|---|
| Permission rules | A Python or Node script that opens files itself |
| The edit hook | The same subprocess gap |
| The end-of-turn audit | Nothing — it only reports |
| `/wizrelay:verify` | A developer who does not run it |
| CI gate | A direct push to a branch with no required checks |

Documented bypasses, stated plainly because a guardrail whose limits are undocumented gets
trusted for things it does not do:

- Disabling the plugin, in `/plugin` or in the repository's settings.
- Editing `.claude/settings.json` and removing the deny rules.
- Writing files from a subprocess. Claude Code's own documentation says Read and Edit deny
  rules do not cover a command that opens files without naming them.
- Running in `bypassPermissions` mode.

What narrows them: **the CI gate** ([12. CI integration](12-ci-integration.md)) and
**managed settings** ([13. Team and enterprise](13-team-and-enterprise.md)). For
enforcement that covers subprocesses, enable Claude Code's own sandbox alongside this.

## Integrity, separately from scope

The lock file records a sha256 per researcher file. That gives a second, independent check:
not "did you edit something out of scope" but "is your copy of the analysis still what was
published".

A changed, missing or unrecorded researcher file is reported at session start, by the
end-of-turn audit, and by `/wizrelay:verify`. `/wizrelay:sync` restores it.

Hashing normalises CRLF to LF, so a Windows checkout of the hub and a macOS checkout of the
same commit agree. Without that, `sync` would report the whole package as corrupted on
every run.

## Error policy, and why it is asymmetric

| Component | On failure |
|---|---|
| The edit hook (`PreToolUse`) | **Fails closed.** A crash or a timeout blocks the edit; an internal error asks |
| Everything else | **Fails open.** The failure is swallowed and the session continues |

A guard that fails open is not a guard. But a session must never become unusable because of
wizrelay: a broken session-start costs context, and a broken session-start that aborted the
session would cost the user their work.

## When you are blocked

```
I am blocked
 ├─ Is the file the researcher's? ── yes ──► /wizrelay:ask (request the change)
 ├─ Is this change in the plan? ── no ──► re-read the plan; if it is genuinely needed ↓
 └─ Write the reason in questions.md → /wizrelay:ask → the researcher widens the scope
    → /wizrelay:sync → carry on
```

## Confirming the protection is live

Two different questions, and the second one is the one that has bitten people:

- **`/wizrelay:doctor`** checks the configuration.
- **`/wizrelay:status`** checks *this session*. If its output opens with a
  `WIZRELAY_NO_GUARD` warning, the hooks did not run here even though the configuration is
  correct.

How that happens, and the fixes, are in
[16. Troubleshooting](16-troubleshooting.md).

## Next

[12. CI integration](12-ci-integration.md) — the layer that does not run in the developer's
session.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 10. Model and effort routing](10-routing.md) | [Contents](README.md) | [12. CI integration →](12-ci-integration.md) |
<!-- /nav:bottom -->
