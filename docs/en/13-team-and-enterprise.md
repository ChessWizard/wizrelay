<!-- nav:top -->
[Documentation](README.md) › **13. Team and enterprise administration** &nbsp;·&nbsp; [Türkçe](../tr/13-team-and-enterprise.md)
<!-- /nav:top -->

# Team and enterprise administration

Rolling this out to a team, and the two layers a developer cannot turn off.

## The honest summary

Layers 1 to 4 of the scope protection live inside the developer's own session, and the
developer can turn all of them off. Two things cannot be turned off by the person they
constrain:

- **The CI gate** ([12. CI integration](12-ci-integration.md))
- **Managed settings**, deployed by an administrator

Deploy neither and you have a helpful assistant, not a guardrail. Deploy one, and make it
the CI gate: it is less intrusive and it catches the thing that matters, which is a change
reaching the main branch.

## 1. Repository-level team settings

`.claude/settings.json`, committed:

```json
{
  "extraKnownMarketplaces": {
    "wizrelay": { "source": { "source": "github", "repo": "ChessWizard/wizrelay" } }
  },
  "enabledPlugins": { "wizrelay@wizrelay": true },
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

`wizrelay init` writes the deny list in full. Add the marketplace block automatically with:

```bash
wizrelay init --marketplace ChessWizard/wizrelay
```

A teammate who opens the repository and accepts the trust dialog is then offered the
plugin.

**Caveat worth putting in your onboarding notes:** on some Claude Code versions that
suggestion does not appear. Keep the manual install from
[4. Install the plugin](04-install-plugin.md) as the documented fallback rather than letting
people conclude the repository is broken.

## 2. Enterprise enforcement with managed settings

Managed settings are deployed by an administrator and cannot be overridden by a user's own
`settings.json`. With them you can:

- Enable the plugin for everybody
- Put the researcher-file protection rules where users cannot remove them
- Restrict which models are permitted
- Cap the effort level

Ready-to-adapt files are in
[`integrations/managed-settings/`](../../integrations/managed-settings/), with a table of
what each key costs the user. **Read that table before deploying.** Two examples of the
cost: blocking `bypassPermissions` removes a mode that is genuinely useful in containers,
and a fixed `disableAllHooks: false` also stops users disabling **other** plugins' hooks.

```json
{
  "extraKnownMarketplaces": {
    "wizrelay": { "source": { "source": "github", "repo": "ChessWizard/wizrelay" } }
  },
  "enabledPlugins": { "wizrelay@wizrelay": true },
  "permissions": {
    "deny": [
      "Edit(/.wizrelay/tasks/*/research.md)",
      "Edit(/.wizrelay/tasks/*/task.json)"
    ],
    "disableBypassPermissionsMode": "disable"
  }
}
```

**Verify the key names against the current Claude Code managed-settings documentation
before you deploy.** The keys that restrict models and cap effort in particular have
changed names across versions, and a managed settings file with a wrong key is silently
ineffective — which is the worst outcome for a control you are relying on.

Start with the baseline file. Add a model or effort floor only when you have a reason: it
applies to every task in every repository, not only the ones wizrelay routes.

## 3. The access matrix

| Resource | Researcher | Developer | CI |
|---|---|---|---|
| Hub repository | Write | Read | — |
| Project repositories | Read (optional) | Write | Read |
| Tracker | Read + comment | Read + comment | — |
| `wizrelay` product repository | — | — | Read, via pip |

## 4. Rollout order

1. **The hub**, with `CODEOWNERS` and branch protection
   ([5. Set up the hub](05-set-up-hub.md)). Without these, anyone who can push can publish
   their own analysis.
2. **The CI gate**, with `on-missing-task: skip` to start.
3. **Repository settings**, so new teammates are offered the plugin.
4. **One repository connected**, and one real task through the whole loop before you roll
   out to the rest. The first task is where you discover whether your `roles` vocabulary and
   your `critical_paths` are right.
5. **Team policy**, only after a handful of tasks have shown you where the default routing
   is wrong.
6. **Managed settings**, last, and only if you need them.

## 5. Verifying the rollout

On one developer's machine:

```
/wizrelay:doctor
```

Then confirm, on a machine that has never had the plugin, that the install commands in
[4. Install the plugin](04-install-plugin.md) work and that `/wizrelay:doctor` is clean.

One check is worth doing deliberately: install a second plugin whose manifest name is also
`wizrelay`, and confirm that `doctor` reports it as an error. With two same-named plugins,
**only one registers its hooks, and scope protection disappears silently.** That is the
failure the heartbeat warning exists for, and the only way to know it works is to cause it
once.

## 6. What to tell your team

Three things, and no more:

1. **Pull before you plan.** `/wizrelay:pull`, then `/wizrelay:plan`.
2. **When you are blocked, ask — do not widen.** `/wizrelay:ask`. The scope is the
   researcher's decision, and going around it moves the problem to the pull request.
3. **Verify before you call it done.** `/wizrelay:verify`.

Everything else they will pick up from the messages the plugin itself produces.

## Upgrading

Pin a version in the marketplace entry and in the CI `pip install`. `wizrelay doctor`
reports an old schema and `wizrelay migrate` converts it; lock files written by older
versions stay readable.

## Next

[14. Customisation](14-customisation.md).

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 12. CI integration](12-ci-integration.md) | [Contents](README.md) | [14. Customisation →](14-customisation.md) |
<!-- /nav:bottom -->
