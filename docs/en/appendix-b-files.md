<!-- nav:top -->
[Documentation](README.md) › **Appendix B — File reference** &nbsp;·&nbsp; [Türkçe](../tr/appendix-b-files.md)
<!-- /nav:top -->

# Appendix B — File reference

Every file the system creates or reads, who owns it, and whether it is committed.

## The hub repository

| File | Owner | Commit | What it is |
|---|---|---|---|
| `wizrelay-hub.json` | Researcher | Yes | Hub identity and team defaults. Its presence is what makes a directory the hub |
| `CLAUDE.md` | Researcher | Yes | The researcher protocol |
| `.mcp.json` | Researcher | Yes | The tracker connection |
| `policies/routing-policy.json` | Researcher | Yes | The team's model and effort policy |
| `templates/package/` | Researcher | Yes | Team package templates |
| `tasks/<ID>-<slug>/*` | Researcher | Yes | The packages |
| `tasks/<ID>-<slug>/.validation.md`, `.notes/` | Researcher | Yes | Stay in the hub; never published |

## A project repository

| File | Owner | Commit | What it is |
|---|---|---|---|
| `.wizrelay/config.json` | Team | Yes | Hub, role, tracker, language |
| `.wizrelay/config.local.json` | You | **No** | Personal settings |
| `.wizrelay/profile.json` | Team | Yes | The repository profile |
| `.wizrelay/PROTOCOL.md` | Plugin | Yes | The working rules; `init` writes it |
| `.wizrelay/.active-task` | You | **No** | The active-task pointer |
| `.wizrelay/tasks/<dir>/` researcher files | Researcher | Yes | A read-only copy |
| `.wizrelay/tasks/<dir>/.lock.json` | Plugin | Yes | Version, hub commit, hashes, routing |
| `.wizrelay/tasks/<dir>/plan.md`, `questions.md`, `verification.md` | Developer | Yes | Your working files |
| `.wizrelay/tasks/<dir>/notes/` | Developer | Yes | Your notes |
| `CLAUDE.md` | Project | Yes | `init` appends one import line |
| `.claude/settings.json` | Project | Yes | `init` appends the deny rules |
| `.gitignore` | Project | Yes | `init` appends two lines |

## Package files and ownership

| File | Owner | Required | Content |
|---|---|---|---|
| `task.json` | Researcher | yes | The machine-readable definition |
| `research.md` | Researcher | yes | Problem, evidenced current state, approach, rejected alternatives, risks |
| `scope.md` | Researcher | yes | The scope in prose, with its rationale |
| `acceptance.md` | Researcher | yes | The acceptance criteria |
| `decisions.md` | Researcher | yes | The decision record |
| `contracts.md` | Researcher | when more than one role | Interfaces between roles |
| `roles/<role>.md` | Researcher | per role | The role's slice, hints, pitfalls, test expectation |
| any other `*.md` or file | Researcher | no | Diagrams, flows; included automatically |
| `.*` (e.g. `.validation.md`, `.notes/`) | Researcher (private) | no | **Never published** |
| `plan.md`, `questions.md`, `verification.md`, `notes/` | Developer | — | Never copied from the hub, even if a file of that name exists there |

## Precedence when files disagree

```
decisions.md  >  task.json + scope.md  >  contracts.md  >  acceptance.md  >  roles/<role>.md  >  research.md
(newest)         (scope)                  (interfaces)     (behaviour)        (the slice)        (rationale)
```

This order is written into `.wizrelay/PROTOCOL.md`, which every session loads.

## Copy safety

`pull` refuses, by name, so the message is actionable:

- symbolic links, whether they point inside or outside the package
- absolute paths and any `..` segment
- anything that is not a regular file
- a file over 5 MB, or a package over 20 MB in total
- a directory name that does not match `^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$`

A refusal happens **before** anything is written, so a bad package never leaves a
half-copied directory behind.

## `.lock.json`

```json
{
  "schema_version": 1,
  "task_id": "CU-86c1abcd",
  "tracker_ref": "86c1abcd",
  "title": "Tenant daily API request quota",
  "folder": "CU-86c1abcd-tenant-daily-api-request-quota",
  "version": 2,
  "status": "published",
  "hub_commit": "f95f2307ad3c",
  "hub_id": "acme-research-hub-2e807908",
  "pulled_at": "2026-10-30T09:12:44+00:00",
  "role": "backend",
  "files": { "research.md": "<sha256>", "roles/backend.md": "<sha256>" },
  "routing": { "tier": "T4-high-risk", "score": 10, "phases": {}, "launch": "claude --model opus …" }
}
```

`hub_id` is what keeps two hubs on one machine apart: it is a normalised identity, so
`git@github.com:acme/research-hub.git` and `https://github.com/acme/research-hub.git`
produce the same value while a different hub produces a different one.

Hashing normalises CRLF to LF, so a Windows checkout of the hub and a macOS checkout of the
same commit agree. Without that, `sync` would report the whole package as corrupted every
time.

## Data contracts

Every JSON file carries `schema_version: 1`. The JSON Schema files are in
[`schemas/`](../../schemas/), in draft 2020-12 form, and the runtime enforces the same
rules with the standard library. Both are tested against the same fixtures, so they cannot
drift apart.

| Schema | Document |
|---|---|
| `task.schema.json` | `task.json` |
| `config.schema.json` | `.wizrelay/config.json` and `config.local.json` |
| `profile.schema.json` | `.wizrelay/profile.json` |
| `lock.schema.json` | `.lock.json` |
| `routing-policy.schema.json` | `policies/routing-policy.json` |
| `wizrelay-hub.schema.json` | `wizrelay-hub.json` |

## The plugin's own files

For reference, if you are reading the source:

```
plugin/
├── .claude-plugin/plugin.json    the manifest
├── hooks/hooks.json              five events, exec form
├── bin/wizrelay, wizrelay.py     the two launchers
├── skills/<name>/SKILL.md        14 skills
├── agents/*.md                   3 subagents
├── trackers/*.{json,md}          6 adapters
├── config/routing-policy.json    the default policy
├── templates/{dev,hub}/{en,tr}/  what init and hub-init write
├── evals/                        behavioural test cases
└── lib/wizrelay/                 the core library, stdlib only
```

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← Appendix A — Command reference](appendix-a-commands.md) | [Contents](README.md) | [Appendix C — Tracker comment tags →](appendix-c-tracker-tags.md) |
<!-- /nav:bottom -->
