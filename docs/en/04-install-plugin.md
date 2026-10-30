<!-- nav:top -->
[Documentation](README.md) › **4. Install the plugin** &nbsp;·&nbsp; [Türkçe](../tr/04-install-plugin.md)
<!-- /nav:top -->

# Install the plugin

Installing `wizrelay`, checking that it worked, and confirming that scope protection is
actually live in a session.

## Personal install, once per user

Each surface has its own route. All of them write the same settings files, so one user-scope
install reaches the terminal, the desktop app and the VS Code extension on that machine.

### Terminal

In a Claude Code session:

```
/plugin install wizrelay --marketplace ChessWizard/wizrelay
```

That adds the marketplace and opens `wizrelay`'s details in the `/plugin` panel. **Nothing
installs until you choose a scope there** — the command is not a one-shot install.

The same from a shell, without starting a session:

```bash
claude plugin marketplace add ChessWizard/wizrelay
claude plugin install wizrelay@wizrelay
```

### Desktop app

The `/plugin` panel does not open in the desktop app's **Code** tab. Add the marketplace from
a shell with the command above, then click **+** beside the prompt box and select **Add
plugins** — an older build shows **Plugins**, then **Browse plugins**. Select `wizrelay` and
choose a scope.

### VS Code

Type `/plugins` in the prompt box to open **Manage plugins**. Add `ChessWizard/wizrelay` on
the **Marketplaces** tab, then find `wizrelay` on the **Plugins** tab and click **Install**.

JetBrains has no plugin browser of its own: it runs Claude Code in the IDE terminal, so use
the terminal route there. A cloud session loads no plugins at all.

`ChessWizard/wizrelay` is the repository the marketplace is read from. Installing from a fork means naming that fork's owner instead.

Then confirm it:

1. Type `/` and look for the `/wizrelay:` commands. In a terminal session `/plugin` lists the
   plugin on the **Installed** tab too — press **Tab** to reach it, because the panel opens
   on **Discover** — and the **Errors** tab should be empty.
2. Run `/wizrelay:doctor`. It checks Python, git, the plugin's own integrity, whether a
   second plugin is using the same manifest name, and — if you are inside a connected
   repository — that repository's configuration.

## Install scope

Install it at **user scope**: once, and available in every project.

In a directory with neither `.wizrelay/` nor `wizrelay-hub.json`, the plugin is **completely
silent**. It adds no context, writes no file and makes no network call. So it does not get
in the way in your personal projects or in repositories that do not use it.

To have it offered automatically in team repositories, register the marketplace and the
plugin in the repository's settings — see
[13. Team and enterprise administration](13-team-and-enterprise.md).

## Updating

```
/plugin marketplace update wizrelay
```

Then apply the update for `wizrelay` from the `/plugin` screen, and run
`/reload-plugins` if the session does not pick it up. Release notes are in the product
repository's `CHANGELOG.md`.

Pin a version if you want predictability: the `version` in the plugin's manifest decides
what users receive, and a marketplace entry can pin a tag.

**Auto-update is off for this marketplace.** Claude Code turns it on only for Anthropic's own
marketplaces, so updates arrive when someone asks for them. To have them arrive on their own,
open `/plugin`, go to the **Marketplaces** tab, select `wizrelay` and choose **Enable
auto-update**. Even then the running session keeps the version it loaded; the next one picks
up the new one.

## Removing it, or turning it off in one project

Remove it entirely:

```
/plugin uninstall wizrelay@wizrelay
```

Turn it off in one project only, in that project's `.claude/settings.json`:

```json
{ "enabledPlugins": { "wizrelay@wizrelay": false } }
```

## Short command names

Claude Code also accepts a plugin command's bare name when nothing else uses it. This guide
always writes the full form; day to day, the short one is fine.

| Can be written short | Always written in full (clashes with a built-in) |
|---|---|
| `/pull`, `/ask`, `/verify`, `/sync` | `/wizrelay:plan` |
| `/hub-init`, `/hub-new`, `/hub-validate` | `/wizrelay:init` |
| `/hub-publish`, `/hub-inbox`, `/hub-status` | `/wizrelay:status`, `/wizrelay:doctor` |

If a short name runs something unexpected — another plugin or a project skill is using it —
switch to the full form.

## Knowing that scope protection is live

This is worth doing once deliberately, because it is the failure that looks like success.

Scope protection runs through hooks. If the hooks are not running in a session, wizrelay
commands show this at the top of their output:

```text
⚠ Scope protection is not active in this session.
```

Three things cause it:

- Another installed plugin uses the manifest name `wizrelay`, and it holds the hook
  registration. With two same-named plugins, **only one of them registers hooks.**
- All hooks are turned off in settings (`disableAllHooks`).
- The trust dialog for the repository folder was never accepted.

`/wizrelay:doctor` checks all three separately. [16. Troubleshooting](16-troubleshooting.md)
has the fixes.

The distinction to keep in mind: **`doctor` checks the configuration, `/wizrelay:status`
checks this session.** A configuration can be perfect while the hooks did not run here.

## Next

[5. Set up the team hub](05-set-up-hub.md) — once per team.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 3. Prerequisites](03-prerequisites.md) | [Contents](README.md) | [5. Set up the team hub →](05-set-up-hub.md) |
<!-- /nav:bottom -->
