---
name: hub-init
description: Turn an empty repository into a team research hub.
disable-model-invocation: true
allowed-tools: Bash(wizrelay *)
---

Set up a team research hub. One hub serves a whole team, not one project.

**A hub holds no code and nothing in it is ever executed.** If the user asks for a script
in the hub, explain that developer repositories read the hub as data and that no hub file
is run.

**Do not commit.** Propose the commit; the user runs it.

## 1. Check where you are

This must be an empty or nearly empty git repository, private, and separate from any
product repository. If the current directory is a product repository, stop and say so.

## 2. Run it

```
wizrelay hub init --name <team-hub-name> --tracker <type>
```

## 3. Fill in the hub marker

`wizrelay-hub.json` arrives with `{{placeholders}}`. Ask the user for each and write them:

- `name` — the hub's name, used in session context
- `language` — `en` or `tr`; the default language for every connected repository
- `tracker` — the type, plus what that adapter needs: `id_prefix` for ClickUp, `repo` for
  GitHub, `base_url` for Jira or Azure DevOps, `workspace` for Linear
- `roles` — the team's role vocabulary, for example `["backend", "frontend", "mobile"]`.
  This is the catalogue every package draws from, so agree on it now rather than per task.
- `default_branch`, `base_ref` — usually `main` and `origin/main`
- `default_enforcement` — `strict` unless the team has a reason otherwise

## 4. Optional extras

Mention these without setting them up unless asked:

- `policies/routing-policy.json` — a team routing policy replacing the plugin default
- `templates/package/` — team-specific package templates, overriding the shipped ones
- `.mcp.json` — the tracker's MCP server, so hub sessions can read tasks

## 5. Protect the hub, and say why

Tell the user to:

- keep the repository **private**: packages describe unreleased work
- add a `CODEOWNERS` naming the researchers, and protect the default branch

That is what keeps a developer from publishing their own analysis, which is the trust
boundary the whole system rests on.

## 6. Hand over

Files to commit: `wizrelay-hub.json`, `CLAUDE.md`, `tasks/.gitkeep`, `.gitignore`.

Next command: `/wizrelay:hub-new <tracker reference>`.

Answer in the language set in `wizrelay-hub.json`.
