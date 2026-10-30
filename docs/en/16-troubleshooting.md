<!-- nav:top -->
[Documentation](README.md) › **16. Troubleshooting** &nbsp;·&nbsp; [Türkçe](../tr/16-troubleshooting.md)
<!-- /nav:top -->

# Troubleshooting

Symptom, cause, fix. Start with `wizrelay doctor` — it checks most of this for you.

## The table

| Symptom | Likely cause | Fix |
|---|---|---|
| "Scope protection is not active in this session" | Another plugin named `wizrelay` holds the hooks; `disableAllHooks`; the trust dialog was never accepted | Read the note on the `/plugin` **Errors** tab; disable or remove the conflicting plugin; `/reload-plugins`; `/wizrelay:doctor` |
| A short command (`/pull`) runs something unexpected | Another plugin or a project skill uses that name | Use the full form: `/wizrelay:pull` |
| `/wizrelay:` commands do not appear | The plugin is not installed or not enabled; the trust dialog was never accepted | `/plugin` → Installed and Errors tabs; `/reload-plugins`; reopen the repository and accept the trust dialog |
| No task context at session start | No `.wizrelay/config.json`; no active task; hooks are off | `/wizrelay:status`; check the wizrelay hooks in the `/hooks` menu; make sure `disableAllHooks` is not set |
| "No hub is configured" | `hub.repo` is absent or still a placeholder | Run `/wizrelay:init` again with the right hub |
| "has status draft, so it cannot be pulled" | The package is still a draft | The researcher has to publish it |
| `pull` says "No package found" | Wrong identifier; the package was not pushed; the wrong hub | `wizrelay hub list` in the hub; check the hub address in `config.json` |
| Git authentication failure | No SSH key or credential | Try `git ls-remote <hub-url>` |
| Every file looks out of scope | The `role` in `config.json` does not match the task's roles; a glob mistake | `/wizrelay:status` to check the role; the researcher checks the `allow` list |
| "locally modified" warning keeps appearing | A researcher file was edited by hand | `/wizrelay:sync` |
| "new version" warning survives a sync | You are on a different branch; the cache has not refreshed | Run `/wizrelay:sync` again; if needed set `fetch_ttl_minutes: 0` |
| "Python not found" on Windows | `python3` is not on `PATH` | Install Python, use Git Bash, `/wizrelay:doctor` |
| Tracker comments are not posted | No MCP sign-in, or the permission prompt was declined | `/mcp` to sign in; approve the prompt |
| The plugin was never suggested | A known prompt issue | Install it manually ([section 4](04-install-plugin.md)) |
| `/wizrelay:verify` could not find the agent | A Claude Code or plugin version mismatch | `claude update`, update the plugin; if it persists, report it |
| Confirmation asked when changing model | You chose a model weaker than the one the task was routed to | Approve deliberately, or stay on the suggested model |
| `--advisor` errors | A non-Anthropic-API provider, or an incompatible model | Drop `--advisor` from the command |
| The CI gate says "skipped" | No task identifier in the branch name | Rename the branch; or use `--require-task` |
| The CI gate is red and your machine is clean | CI looks at every commit in the pull request | Run `wizrelay audit --base origin/main` locally |

## The serious one, in detail

### Commands work but nothing is ever denied

Scope protection is absent while every command makes it look present. This is the failure
mode worth recognising on sight.

Run `/wizrelay:status`. If its output opens with `WIZRELAY_NO_GUARD`, the hooks did not run
in this session. Three causes:

**1. `python3` does not resolve.** The hooks run `python3`; without it they cannot start.
`wizrelay doctor` reports the `python` check as an **error**. On Windows, install Python
3.9+ so that `python3` resolves, or use Git Bash with Python available.

**2. Another plugin is named `wizrelay`.** With two same-named plugins, only one registers
its `hooks/hooks.json`. `doctor`'s `duplicate-plugin-name` check reports it; uninstall the
duplicate. Which of the two wins is not documented, so do not rely on install order.

**3. Hooks are disabled, or the folder was never trusted.** Check `disableAllHooks` in your
settings, and reopen the folder to get the trust prompt.

## By area

### `pull` and `sync`

**"The research hub could not be reached."** `hub.repo` is wrong, you have no access, or you
are behind a proxy. Try cloning it by hand with the same credentials. For a proxy, set
`hub.path` in `.wizrelay/config.local.json` to a clone you maintain yourself — with
`hub.path` set nothing is fetched, so your working copy is never touched.

**"matches more than one package."** Two package directories share the identifier prefix.
Pass the full directory name.

**"The configured hub URL embeds a credential."** A URL of the form
`https://user:token@host` is rejected so the token never reaches a cache path or a lock
file. Use SSH, or a git credential helper.

**`sync` reports a file as "restored".** A researcher file had been changed locally and has
been put back from the hub. That is the intended behaviour. If the change was needed, raise
it with `/wizrelay:ask`.

**"Refusing to copy …: `<file>` is a symbolic link."** The hub package contains something a
copy must not carry: a symlink, a `..` path, a file over 5 MB, a package over 20 MB. The
message names the file; the researcher removes it and publishes again.

### Scope

**An edit is denied and it should not be.** `/wizrelay:status` to see the scope, then:

- **The scope is genuinely wrong.** Raise it with `/wizrelay:ask`. Do not widen it locally —
  the CI gate checks the same scope, so the problem just moves to the pull request.
- **You are on the wrong role.** `role` in `.wizrelay/config.json`.
- **You are on a stale version.** `/wizrelay:sync`.

**A researcher file is denied even with `enforcement: off`.** Correct. `off` turns off
*scope* enforcement; researcher files stay read-only in every mode.

**`audit` reports files I did not touch.** `.claude/settings.json`, `.gitignore`,
`.mcp.json` and `CLAUDE.md` appear under *Incidental*, not as violations — `wizrelay init`
wrote them. Lock files are incidental at any depth. Anything else was changed by something:
a formatter, a build step, a generator. Add genuinely incidental paths to
`incidental_allow` in the profile.

**`audit` says the base ref does not resolve.** A shallow checkout has no merge base. In CI,
fetch the base branch first; the shipped GitHub Action does this. Locally,
`git fetch origin main`.

### Routing

**`route` and `pull` disagree.** They should not, and a test covers it now. Both read the
hub's `policies/routing-policy.json` when the hub is on disk, and fall back to the plugin
default only when it is not. If you see it, report it.

**The tier looks too low for a risky task.** Routing reads two inputs; check both. The
package's `routing.signals` — if the researcher set `risk: low` on an authentication
rewrite, that is the problem. And your profile — `critical_paths` is what tells routing a
path is expensive to get wrong, `test_maturity` how much the tests will catch.

**The advisor is missing from the launch command.** Three reasons, all intentional: the main
model is Haiku (which cannot have one), the advisor is weaker than the main model, or the
model does not accept one.

### Hub side

**`hub validate` lists "unfilled placeholder".** Working as intended. A scaffolded package
is deliberately invalid until a person fills it in. Fill in each `{{…}}`.

**`publish-prep` refuses.** It will not publish a package with validation errors. Run
`/wizrelay:hub-validate <ID>` and fix every error. Warnings do not block.

**A comment was not posted.** Nothing is posted without explicit approval. If you approved
and it still did not appear: the tracker's MCP server is not authorised (`/mcp`), or the
adapter has no verified endpoint and you need the `gh` CLI or the tracker's own interface.

**The deep link in a GitHub comment is not clickable.** Expected. GitHub strips
`claude-cli://` links. That is why it is in a code block — copy it into your browser.

### Environment

**Windows: nothing works.** `python3` has to resolve. Git Bash with Python 3.9+ is the
supported path. A PowerShell-only environment with no `python3` is best-effort, and
`doctor` reports it as an error rather than letting it look fine.

**`wizrelay: command not found`.** In Claude Code, the plugin's `bin/` is on the Bash tool's
`PATH` while the plugin is enabled; if it is not found, the plugin is not enabled. In a
terminal, install the CLI. Set `WIZRELAY_PYTHON` if the launcher picks the wrong
interpreter.

**"Unknown tracker type" for a tracker that exists.** A pip-installed CLI does not ship the
tracker catalogue, because it lives beside the library rather than inside it. Set
`WIZRELAY_TRACKERS_DIR` to `plugin/trackers` in a checkout. Nothing in CI needs it —
`audit` is tracker-agnostic.

## Getting help

1. `wizrelay doctor --json` — the single dump worth attaching. It contains no credentials.
2. `WIZRELAY_DEBUG=1` for diagnostics on stderr and a traceback.
3. Open an issue with the bug template, which asks for the `doctor` output, the Claude Code
   version and the platform.

## Next

[17. Frequently asked questions](17-faq.md).

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 15. Worked example: a task end to end](15-walkthrough.md) | [Contents](README.md) | [17. Frequently asked questions →](17-faq.md) |
<!-- /nav:bottom -->
