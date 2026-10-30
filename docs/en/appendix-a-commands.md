<!-- nav:top -->
[Documentation](README.md) › **Appendix A — Command reference** &nbsp;·&nbsp; [Türkçe](../tr/appendix-a-commands.md)
<!-- /nav:top -->

# Appendix A — Command reference

Every command, who uses it, and its CLI equivalent.

## Claude Code commands

| Command | Who | What it does | CLI equivalent |
|---|---|---|---|
| `/wizrelay:init [role] [hub]` | Team lead | Connects the repository to a hub | `wizrelay init --role … --hub …` |
| `/wizrelay:doctor` | Everybody | Environment and configuration check | `wizrelay doctor` |
| `/wizrelay:pull <ID>` | Developer | Pulls the package, makes it active, suggests a model | `wizrelay pull <ID>` |
| `/wizrelay:plan` | Developer | In-scope plan, `plan.md`, a `/goal` suggestion | — |
| `/wizrelay:ask <question>` | Developer | An answer sourced from the package; `[WIZRELAY-Q]` if it has none | — |
| `/wizrelay:verify` | Developer | Independent verification, `verification.md`, `[WIZRELAY-VERIFY]` | `wizrelay audit` + the project's test commands |
| `/wizrelay:sync` | Developer | Takes the new version, works through the impact | `wizrelay sync` |
| `/wizrelay:status` | Developer | State and warnings | `wizrelay status` |
| `/wizrelay:hub-init` | Researcher / lead | Hub skeleton | `wizrelay hub init <directory>` |
| `/wizrelay:hub-new <ref> [roles]` | Researcher | Draft package | `wizrelay hub new <ref> --title … --roles …` |
| `/wizrelay:hub-validate <ID>` | Researcher | Structural + semantic validation | `wizrelay hub validate <ID>` |
| `/wizrelay:hub-publish <ID>` | Researcher | Version, commit, announcement | `hub publish-prep` + git + `hub comment` |
| `/wizrelay:hub-inbox [ID]` | Researcher | Answers questions, writes decisions | — |
| `/wizrelay:hub-status [ID]` | Researcher | Summary of the verification reports | — |

The four commands with no CLI equivalent are the ones whose work is judgement rather than
mechanics.

## CLI only

| Command | What it does |
|---|---|
| `wizrelay route [--json]` | The active task's routing table and launch command |
| `wizrelay activate <directory>` / `--clear` | Selects or clears the active task by hand |
| `wizrelay brief [--phase …] [--session ID]` | The context a skill injects. **Always exits 0** |
| `wizrelay audit [--base REF] [--task REF \| --branch NAME] [--require-task] [--format md\|json] [--no-fail]` | Scope and integrity audit |
| `wizrelay migrate --from-prototype` | Moves a prototype `.ai/` layout to `.wizrelay/` |
| `wizrelay hub list [--json]` | Lists the packages in the hub |
| `wizrelay hub comment <ref>` | Produces the publish comment text |
| `wizrelay hook <event>` | The hook handler. Not for direct use |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | A violation or a validation failure — the work is wrong, the invocation was fine |
| `2` | A user or configuration error — the invocation is wrong |
| `3` | An unexpected internal error |

`brief` is the exception that proves the rule: it **always** exits 0, because a skill
injects it and a non-zero exit there aborts the whole skill invocation before Claude sees
any of its content.

The `--json` output of every read command carries a `schema_version` and is
backwards-compatible across versions.

## Short command names

| Can be written short | Always written in full |
|---|---|
| `/pull`, `/ask`, `/verify`, `/sync` | `/wizrelay:plan` |
| `/hub-init`, `/hub-new`, `/hub-validate` | `/wizrelay:init` |
| `/hub-publish`, `/hub-inbox`, `/hub-status` | `/wizrelay:status`, `/wizrelay:doctor` |

The four on the right clash with Claude Code built-ins.

## Trackers

| Tracker | Canonical | Accepted input | URL needs | MCP | v1 level |
|---|---|---|---|---|---|
| ClickUp | `CU-86c1abcd` | `86c1abcd`, `CU-86c1abcd`, a task URL | nothing | **verified**: `https://mcp.clickup.com/mcp` (OAuth) | full |
| GitHub Issues | `GH-123` | `123`, `#123`, `owner/repo#123`, a URL | `tracker.repo` | not verified — use `gh` | full |
| Jira | `PROJ-123` | `PROJ-123`, `proj-123`, a URL | `tracker.base_url` | not verified | beta |
| Linear | `ENG-123` | `ENG-123`, `eng-123`, a URL | `tracker.workspace` | not verified | beta |
| Azure DevOps | `AB-123` | `123`, `AB#123`, a URL | `tracker.base_url`, `tracker.project` | not verified | beta |
| none | whatever you name it | any safe name | — | — | full |

`beta` means identifier handling and URL building are tested, and reading and commenting
depend on your own access to that tracker.

**An unverified endpoint is never written into your configuration.** For ClickUp,
`wizrelay init --tracker clickup` adds the server to `.mcp.json` and you authorise it once
in a browser. For every other adapter, `init` prints instructions instead — a guessed
endpoint fails in a way that looks like the plugin is broken, and it can point credentials
at the wrong host.

Each adapter also ships an instruction file a skill reads on demand:
`plugin/trackers/<type>.md`.

### Identifier forms

All of these find the same package:

```bash
wizrelay pull 86c1abcd
wizrelay pull CU-86c1abcd
wizrelay pull https://app.clickup.com/t/86c1abcd
wizrelay pull CU-86c1abcd-tenant-quota        # the package directory name
```

A team with its own scheme sets `tracker.id_prefix`, and that prefix becomes the canonical
one: with `id_prefix: "TASK-"`, both `123456` and `TASK-123456` resolve to `TASK-123456`.

Jira and Linear identifiers are matched case-insensitively and uppercased, so `proj-123`
works.

## Environment variables

| Variable | What it does |
|---|---|
| `WIZRELAY_DEBUG=1` | Diagnostics on stderr, and a traceback on an unexpected error |
| `WIZRELAY_PYTHON` | The interpreter for the `bin/wizrelay` launcher |
| `WIZRELAY_CACHE_DIR` | Override the cache location |
| `WIZRELAY_TRACKERS_DIR` | Where to find the tracker catalogue, for a pip-installed CLI |

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 17. Frequently asked questions](17-faq.md) | [Contents](README.md) | [Appendix B — File reference →](appendix-b-files.md) |
<!-- /nav:bottom -->
