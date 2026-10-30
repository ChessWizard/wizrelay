<!-- nav:top -->
[Documentation](README.md) › **6. Connect a repository** &nbsp;·&nbsp; [Türkçe](../tr/06-connect-repository.md)
<!-- /nav:top -->

# Connect a repository

Connecting a project repository to the hub, and getting its profile right — because routing
reads that profile.

## 1. Choose the role

A role says which part of a task this repository implements, and it has to be one of the
names in the hub's `roles` list. In our example, `api-service` → `backend`,
`web-app` → `frontend`.

In v1 a repository has **one** role. For a monorepo with several, there are two options:
give the repository a single role name (say `fullstack`) and express the scope with
sub-directory globs, or write packages against that one role. Multi-role support is on the
roadmap.

## 2. Run `/wizrelay:init`

With Claude Code open at the repository root:

```
/wizrelay:init backend git@github.com:acme/research-hub.git
```

In order, this happens:

1. The hub is contacted and its team defaults are read — language, tracker, `base_ref`.
2. `.wizrelay/` is created.
3. `@.wizrelay/PROTOCOL.md` is appended to `CLAUDE.md`. Existing content is kept; the file
   is created if it does not exist.
4. The permission rules that protect researcher files are added to
   `.claude/settings.json`. Your existing settings are kept.
5. Personal files are added to `.gitignore`: `.wizrelay/.active-task`,
   `.wizrelay/config.local.json`.
6. The project `.mcp.json` entry for the tracker is offered; it is written if you approve.
7. Claude reads the repository, drafts `profile.json`, and shows it to you for approval.

The result:

```
api-service/
├── CLAUDE.md                 ← @.wizrelay/PROTOCOL.md appended
├── .claude/settings.json     ← deny rules added
├── .gitignore                ← two lines added
└── .wizrelay/
    ├── config.json           ← hub, role, tracker, language (committed)
    ├── profile.json          ← repository profile (committed)
    ├── PROTOCOL.md           ← how Claude works with tasks in this repository
    └── tasks/                ← pulled packages will live here
```

The command is **idempotent**: run it a second time and it reports "nothing changed" and
touches no file.

### The rules it adds to `.claude/settings.json`

```json
{
  "permissions": {
    "deny": [
      "Edit(/.wizrelay/tasks/*/task.json)",
      "Edit(/.wizrelay/tasks/*/research.md)",
      "Edit(/.wizrelay/tasks/*/scope.md)",
      "Edit(/.wizrelay/tasks/*/acceptance.md)",
      "Edit(/.wizrelay/tasks/*/contracts.md)",
      "Edit(/.wizrelay/tasks/*/decisions.md)",
      "Edit(/.wizrelay/tasks/*/roles/**)",
      "Edit(/.wizrelay/tasks/*/.lock.json)"
    ]
  }
}
```

These cover Claude's file tools **and** the shell forms Claude Code recognises — `sed`,
`tee`, a `>` redirection. An "allow" rule at another settings level cannot open them.

Two details that are easy to get wrong if you write such rules yourself:

- **Every rule is `Edit(...)`.** A `Write(path)` rule matches nothing at all; Claude Code
  checks file permissions against `Edit` and `Read` rules only.
- **The single leading slash anchors at the settings source**, which for project settings is
  the repository root. It is not a filesystem-absolute path — that would be `//`.

## 3. `profile.json` — describing the repository

Claude drafts it; you confirm it. This file affects two things: which commands
`/wizrelay:verify` runs, and which model is suggested.

A Python / FastAPI backend:

```json
{
  "schema_version": 1,
  "stack": "Python 3.12 / FastAPI / PostgreSQL / Azure Service Bus",
  "commands": {
    "test": "pytest -q",
    "test_targeted": "pytest -q {path}",
    "lint": "ruff check .",
    "typecheck": "mypy app"
  },
  "codebase_size": "medium",
  "test_maturity": "medium",
  "critical_paths": ["app/auth/**", "app/billing/**", "app/tenancy/**", "alembic/versions/**"],
  "legacy_paths": ["app/legacy/**"],
  "incidental_allow": ["openapi.json"]
}
```

A React frontend:

```json
{
  "schema_version": 1,
  "stack": "React 19 / TypeScript / Vite",
  "commands": {
    "test": "npm test -- --run",
    "test_targeted": "npm test -- --run {path}",
    "lint": "npm run lint",
    "typecheck": "npx tsc --noEmit"
  },
  "codebase_size": "medium",
  "test_maturity": "low",
  "critical_paths": ["src/features/billing/**", "src/lib/auth/**"],
  "legacy_paths": [],
  "incidental_allow": ["src/api/generated/**"]
}
```

A .NET project, commands only:

```json
{ "commands": { "test": "dotnet test", "test_targeted": "dotnet test --filter {path}", "lint": "dotnet format --verify-no-changes", "typecheck": "" } }
```

| Field | What to write | What it affects |
|---|---|---|
| `commands.test` | The command that runs all the tests | `/wizrelay:verify` |
| `commands.test_targeted` | The command that tests one file or directory, with the `{path}` placeholder | Per-criterion evidence in `/wizrelay:verify` |
| `commands.lint`, `commands.typecheck` | May be left empty | `/wizrelay:verify` |
| `codebase_size` | `small` / `medium` / `large` | `large` → +1 to the routing score |
| `test_maturity` | `low` / `medium` / `high` | `low` → +1 |
| `critical_paths` | Where a mistake is expensive: authentication, payments, tenant isolation, migrations | +1 when the task's scope touches them |
| `legacy_paths` | Old, untested, or risky to touch for other reasons | +1 when the task's scope touches them |
| `incidental_allow` | Files that change naturally regardless of the task: generated clients, snapshots | Free in the scope check. Lock files are already free |

**Take the commands from the repository, never from memory.** They should come from the
`Makefile`, the `package.json` scripts, `pyproject.toml`, a `justfile` or the CI workflow.
A `test_targeted` command that does not actually work makes every verification report
useless.

And be honest about `test_maturity`. It is the single field most likely to be set
optimistically, and it is one of the two that decide whether a risky task gets a strong
model.

## 4. `config.json` and personal settings

```json
{
  "schema_version": 1,
  "hub": { "repo": "git@github.com:acme/research-hub.git", "branch": "main" },
  "role": "backend",
  "tracker": { "type": "clickup", "id_prefix": "CU-" },
  "language": "en",
  "base_ref": "origin/main",
  "prompt_anchor": true,
  "session_title": true,
  "fetch_ttl_minutes": 10,
  "researcher_mention": ""
}
```

| Field | What it does |
|---|---|
| `hub` | The connected hub and its publication branch |
| `role` | This repository's role |
| `prompt_anchor` | Adds a one-line task reminder to every message (can be turned off) |
| `session_title` | Names the session after the task |
| `fetch_ttl_minutes` | How often session start checks the hub (`0` = every time, and it really does mean every time) |
| `researcher_mention` | The tracker username to mention in question comments |

Personal settings go in `.wizrelay/config.local.json`, which is gitignored. The usual
single use: a researcher reading the hub from a local working copy.

```json
{ "hub": { "path": "~/code/research-hub" } }
```

With `hub.path` set, **nothing is cached and the working copy is never fetched or reset**,
so having the hub open in an editor is safe.

## 5. Commit

```bash
git add CLAUDE.md .claude/settings.json .gitignore .wizrelay/
git commit -m "chore: connect wizrelay (role: backend)"
git push
```

## 6. When a teammate joins

1. They pull the repository.
2. They open Claude Code in it and **accept the workspace trust dialog**. Project settings
   and the plugin suggestion only take effect after that.
3. If the plugin is suggested, they accept it. If it is not, they run the two commands in
   [4. Install the plugin](04-install-plugin.md).
4. They check with `/wizrelay:doctor`.
5. If they will post questions or verification reports, they sign in to the tracker with
   `/mcp`.

## Next

[7. Researcher: prepare and publish](07-researcher-workflow.md), or
[8. Developer: implement a task](08-developer-workflow.md) if someone has already published
one.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 5. Set up the team hub](05-set-up-hub.md) | [Contents](README.md) | [7. Researcher: prepare and publish →](07-researcher-workflow.md) |
<!-- /nav:bottom -->
