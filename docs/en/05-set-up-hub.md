<!-- nav:top -->
[Documentation](README.md) › **5. Set up the team hub** &nbsp;·&nbsp; [Türkçe](../tr/05-set-up-hub.md)
<!-- /nav:top -->

# Set up the team hub

Creating the repository that holds your team's analysis, and the two settings that make it
trustworthy.

## How many hubs do you need?

| Situation | A new hub? |
|---|---|
| A new project repository joins the team | **No** — it connects to the existing hub |
| A new task for the same team | **No** — a new package is added to the hub |
| Your personal projects | Yes — a separate, personal hub |
| Another company or team adopts this | Yes — their own hub; they never see yours |
| A team inside the company whose access must be separate | Yes |

## 1. Create the repository

On GitHub (or GitLab, or Azure Repos), create a **private** repository, for example
`acme/research-hub`.

| Who | Access |
|---|---|
| Researcher(s) | Write |
| Developers | Read |
| CI | None needed — CI uses the copy in the project repository |

Clone it and open Claude Code inside:

```bash
git clone git@github.com:acme/research-hub.git
cd research-hub
claude
```

## 2. Run `/wizrelay:hub-init`

```
/wizrelay:hub-init
```

Claude asks for these (example answers in brackets):

1. Hub name (`acme-research-hub`)
2. Language (`en`)
3. Tracker type (`clickup`) and identifier prefix (`CU-`)
4. The team's roles (`backend, frontend, infra, mobile`)
5. Default enforcement mode for new packages (`strict`)
6. Whether to add the tracker's MCP connection to this repository (`yes`)

What you end up with:

```
research-hub/
├── wizrelay-hub.json           ← hub identity and team defaults
├── CLAUDE.md                   ← how Claude works in this repository (the researcher protocol)
├── .mcp.json                   ← tracker connection
├── policies/
│   └── routing-policy.json     ← the team's model and effort policy (a copy of the default)
├── templates/
│   └── package/                ← team-specific package templates (optional)
└── tasks/                      ← packages accumulate here
```

## 3. `wizrelay-hub.json`

```json
{
  "schema_version": 1,
  "name": "acme-research-hub",
  "language": "en",
  "tracker": { "type": "clickup", "id_prefix": "CU-" },
  "roles": ["backend", "frontend", "infra", "mobile"],
  "default_branch": "main",
  "base_ref": "origin/main",
  "default_enforcement": "strict"
}
```

| Field | What it means | What changing it does |
|---|---|---|
| `language` | Default language for templates and messages | Newly connected projects inherit it |
| `tracker` | Tracker type and identifier prefix | `/wizrelay:hub-new 86c1abcd` names the package `CU-86c1abcd` |
| `roles` | The role names the team uses | `init` and `validate` draw on this list. Lowercase; hyphens allowed |
| `default_branch` | The hub's publication branch | Projects pull packages from it |
| `base_ref` | The comparison base for scope audits in projects | Becomes the default for `audit` |
| `default_enforcement` | Enforcement mode for new packages | `strict`, `ask` or `off` |

`roles` is the field that deserves a conversation before you commit it. It is the vocabulary
every package will draw from, so agreeing on it now is better than inventing names per
task.

## 4. The tracker connection

If you chose ClickUp, `/wizrelay:hub-init` adds the official ClickUp MCP server to
`.mcp.json`. To add it by hand:

```bash
claude mcp add --scope project --transport http clickup https://mcp.clickup.com/mcp
```

Then type `/mcp` in Claude Code, select ClickUp, and complete the OAuth flow in the
browser. The ClickUp server uses OAuth, not an API key.

For the other trackers see [Trackers in appendix A](appendix-a-commands.md) and
[16. Troubleshooting](16-troubleshooting.md). **If you choose a tracker whose official
endpoint is not verified, `hub-init` writes nothing to any file** — it only explains how to
connect. That is deliberate: a guessed endpoint in your configuration fails in a way that
looks like the plugin is broken, and it can point credentials at the wrong host.

## 5. Team policy (optional)

`policies/routing-policy.json` decides which model and effort level is suggested in which
situation ([10. Routing](10-routing.md)). Leave the default alone for the first few weeks;
adjust the thresholds once you have seen a handful of tasks.

Delete the file and the plugin's own default applies.

## 6. Access and protection

These two settings are what make the hub a *source of truth* rather than a shared folder.

**`CODEOWNERS`:**

```
/tasks/      @acme/research
/policies/   @acme/research
```

**Branch protection on `main`:** with more than one researcher, require a pull request and a
CODEOWNERS review.

**Publication model:** with a single researcher, pushing straight to `main` is fine. With
several, a pull request is safer — `/wizrelay:hub-publish` asks you which you want.

Without these, anyone who can push can publish their own analysis, and the single source of
truth stops being single.

## 7. First commit

```bash
git add -A && git commit -m "chore: set up the research hub" && git push
```

## Several hubs on one machine

You can keep a second hub, say `~/code/personal-hub`, for your own projects. Each project
repository sees only the hub it is connected to.

Two hubs on one machine keep separate caches, keyed by a normalised hub identity, so the
same task identifier existing in both hubs does not mix their contents. The lock file in
each project records which hub its copy came from.

## Next

[6. Connect a repository](06-connect-repository.md) — once per repository.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 4. Install the plugin](04-install-plugin.md) | [Contents](README.md) | [6. Connect a repository →](06-connect-repository.md) |
<!-- /nav:bottom -->
