# Enforcing wizrelay with managed settings

Managed settings are deployed by an administrator and cannot be overridden by a user's own
`settings.json`. They turn wizrelay from a guardrail a developer can disable into one they
cannot — which is the difference between accidental drift and a
determined bypass.

Managed settings are the **only** layer that survives a user editing their
own configuration, apart from the CI gate. Deploy both, or neither is worth much.

## Files here

| File | What it does |
|---|---|
| `managed-settings.json` | Forces the plugin on, keeps the deny rules in place, and blocks the two permission modes that would bypass them. |
| `managed-settings-strict.json` | The same, plus a model and effort floor and no hook disabling. For a team where scope matters more than convenience. |

## Where the file goes

The path is platform-specific and is documented at
<https://code.claude.com/docs/en/managed-settings.md>. Read that page before deploying:
the location, and the exact key names, are what the administrator's own tooling has to
match.

## What each key does, and the cost of it

| Key | Effect | What it costs the user |
|---|---|---|
| `extraKnownMarketplaces` | Registers the marketplace without the user adding it. | Nothing. |
| `enabledPlugins` | Enables `wizrelay` in every session. | They cannot turn it off, including in repositories that have no `.wizrelay/` — where it is silent anyway (invariant I5). |
| `permissions.deny` | Keeps the researcher-file deny rules even if a project's `.claude/settings.json` is changed. | They cannot edit a pulled researcher file at all, by any tool. That is the intent. |
| `permissions.disableBypassPermissionsMode` | Blocks `bypassPermissions`. | They lose a mode that is genuinely useful in containers. Consider leaving it enabled and relying on the CI gate instead. |
| `disableAllHooks` set to a fixed `false` | Stops a user turning hooks off. | They also cannot turn off any **other** plugin's hooks. Say so when you deploy it. |

## Before you deploy

Two honest warnings:

1. **This is still not a sandbox.** A deny rule does not stop a Python or Node script the
   session writes and runs; Claude Code's own documentation says so. For enforcement that
   covers subprocesses, enable Claude Code's sandbox as well.
2. **A model floor costs money and can cost goodwill.** `effortLevel` and a model floor
   apply to every task in every repository, not only to the ones wizrelay routes. Start
   without them.
