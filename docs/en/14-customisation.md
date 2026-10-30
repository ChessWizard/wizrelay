<!-- nav:top -->
[Documentation](README.md) › **14. Customisation** &nbsp;·&nbsp; [Türkçe](../tr/14-customisation.md)
<!-- /nav:top -->

# Customisation

Every knob, where it lives, and which layer wins when two of them disagree.

## The quick table

| What you want | Where | How |
|---|---|---|
| Project-specific rules (migration format, say) | The project's `CLAUDE.md` | Write them normally; they are read alongside the plugin protocol |
| A project-specific command | `.claude/skills/<name>/SKILL.md` | No clash: plugin commands are under the `/wizrelay:` namespace |
| Message language | `.wizrelay/config.json` → `language` | `tr` or `en` |
| Turn off the per-message reminder | `.wizrelay/config.json` → `prompt_anchor: false` | |
| Stop naming the session after the task | `.wizrelay/config.json` → `session_title: false` | |
| Read the hub from a local copy | `.wizrelay/config.local.json` → `hub.path` | [6. Connect a repository](06-connect-repository.md) |
| Team-specific package templates | The hub's `templates/package/` | `hub-new` uses them |
| Model policy | The hub's `policies/routing-policy.json` | [10. Routing](10-routing.md) |
| Turn the plugin off in one project | The project's `.claude/settings.json` | [4. Install the plugin](04-install-plugin.md) |
| Files that may change outside the scope | `.wizrelay/profile.json` → `incidental_allow` | [11. Scope protection](11-scope-protection.md) |
| Enforcement mode for one task | `task.json` → `enforcement` | The researcher sets it |

## The configuration layers

Lowest precedence first. A higher layer overrides a lower one; **objects merge deeply,
arrays replace**.

| # | Layer | Where | Who owns it |
|---|---|---|---|
| 1 | Library defaults | compiled in | the plugin |
| 2 | Hub defaults | `wizrelay-hub.json`, copied at `init` time | the researchers |
| 3 | Project, shared | `.wizrelay/config.json` — committed | the team |
| 4 | Project, personal | `.wizrelay/config.local.json` — gitignored | you |
| 5 | Task | `task.json` in the package | the researcher |

Objects merge deeply so that `config.local.json` can set `hub.path` without repeating
`hub.repo`. Arrays replace rather than accumulate because a list of paths is a single
decision — a `critical_paths` list that merged across layers would be impossible to reason
about.

A key beginning with `_` is a comment and is dropped before validation. JSON has no comment
syntax, and this is how a hub annotates its own files:

```json
{
  "_comment": "test_maturity is low because the quota module has no tests yet.",
  "schema_version": 1,
  "test_maturity": "low"
}
```

## Coexisting with what the project already has

The plugin is built not to collide:

- **Commands are namespaced.** A project skill called `plan` and `/wizrelay:plan` coexist.
  `/plan` runs the project's; `/wizrelay:plan` runs the plugin's.
- **`init` appends, never replaces.** Your `CLAUDE.md` keeps its content, your `.gitignore`
  keeps its entries, your `.claude/settings.json` keeps its own rules.
- **It can be switched off per project**, and then it is completely silent.
- **In a directory with neither marker file it does nothing at all** — no context, no file,
  no network.

## Team package templates

Put files in the hub's `templates/package/` and `hub-new` uses them instead of the shipped
ones, file by file. Only override what you actually want to change: a hub with its own
`acceptance.md` template and nothing else gets the shipped versions of the rest.

Useful when your team has a house style for analysis documents, or a section every package
must carry — a rollback plan, a data-migration note, a security review box.

## Environment variables

| Variable | What it does |
|---|---|
| `WIZRELAY_DEBUG=1` | Diagnostics on stderr, and a traceback on an unexpected error |
| `WIZRELAY_PYTHON` | The interpreter for the `bin/wizrelay` launcher, when `python3` is wrong or absent |
| `WIZRELAY_CACHE_DIR` | Override the cache location |
| `WIZRELAY_TRACKERS_DIR` | Where to find the tracker catalogue, for a pip-installed CLI |

## Adding a tracker adapter

An adapter is data, not code: two files in the plugin.

1. `plugin/trackers/<type>.json` — the descriptor: `ref_pattern`, `canonical_id`,
   `url_template`, `required_config`, `mcp`.
2. `plugin/trackers/<type>.md` — the instructions a skill loads on demand.
3. Identifier and URL cases in `tests/unit/test_trackers.py`.
4. The MCP endpoint goes in **only** once verified.

Write `ref_pattern` with ECMA-262 named groups — `(?<ref>...)` — so the same expression can
be reused by a JSON Schema `pattern`; the runtime translates it for Python. A test enforces
this.

There is an issue template for requesting one:
`.github/ISSUE_TEMPLATE/tracker_adapter.yml`.

## What you cannot customise, and why

| Not configurable | Why |
|---|---|
| Which files are researcher-owned | It is the ownership model the whole thing rests on |
| That researcher files are read-only in `off` mode | An edited criterion silently changes what "done" means |
| The precedence order between package files | A per-team order would make a package unreadable to anyone from another team |
| That `pull` only accepts published packages | A draft can change under you without a version bump |
| The copy safety limits (5 MB per file, 20 MB per package) | A package is analysis, not an asset bundle |

## Next

[15. Worked example](15-walkthrough.md) — the whole thing, one task, end to end.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 13. Team and enterprise administration](13-team-and-enterprise.md) | [Contents](README.md) | [15. Worked example: a task end to end →](15-walkthrough.md) |
<!-- /nav:bottom -->
