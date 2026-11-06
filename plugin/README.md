# <img src=".claude-plugin/icon.png" alt="" width="34" align="top"> wizrelay

Carries a researcher's task analysis into every Claude Code session: deterministic context,
layered scope protection, model and effort routing, and developer-side verification.

This file documents the **plugin** — what installing it adds to a session. For the problem it
solves, the team setup and the full guide, see the
[project repository](https://github.com/ChessWizard/wizrelay).

## Install

From this repository's own marketplace, which is the only route — `wizrelay` is not listed
in Anthropic's plugin directory. The directory accepts command hooks and inline shell only
from organizations Anthropic has verified, and this plugin's scope protection is built on
both: a `PreToolUse` hook that runs a Python file and denies an out-of-scope write, and six
skills that read the task's state through the `wizrelay` CLI. A build without them would
install but could no longer stop an out-of-scope edit, so the full plugin is published here
instead. Nothing about installing from here is limited or provisional.

```bash
claude plugin marketplace add ChessWizard/wizrelay
claude plugin install wizrelay@wizrelay
```

Auto-update is off by default for marketplaces outside Anthropic's own, so new versions
arrive when you ask for them:

```bash
claude plugin update wizrelay@wizrelay
```

To have them arrive on their own, open `/plugin`, go to the **Marketplaces** tab, select
`wizrelay` and choose **Enable auto-update**.

## What it adds

| Component | Count | What it is |
|---|---|---|
| Skills | 14 | `/wizrelay:<name>` commands, 8 in a project repository and 6 in the hub |
| Agents | 3 | `codebase-mapper`, `research-critic`, `test-engineer` |
| Hooks | 5 events | `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `Stop`, `PreModelSwitch` |
| CLI | 1 | `wizrelay`, on the Bash tool's `PATH` while the plugin is enabled |

### In a project repository

| Command | What it does |
|---|---|
| `/wizrelay:init [role] [hub]` | Connects this repository to a hub |
| `/wizrelay:pull <id>` | Pulls a published package, makes it active, suggests a model |
| `/wizrelay:plan` | An in-scope plan, every step tied to an acceptance criterion |
| `/wizrelay:ask <question>` | Answers from the package only, citing the file it used |
| `/wizrelay:verify` | Independent verification against every criterion |
| `/wizrelay:sync` | Takes a new package version and works through the impact |
| `/wizrelay:status` | State and warnings |
| `/wizrelay:doctor` | Environment and configuration check |

### In the hub

`/wizrelay:hub-init` · `/wizrelay:hub-new` · `/wizrelay:hub-validate` ·
`/wizrelay:hub-publish` · `/wizrelay:hub-inbox` · `/wizrelay:hub-status`

## What the hooks do

`PreToolUse` is the one that stops something: it runs on every `Edit`, `Write`, `MultiEdit`
and `NotebookEdit`, and denies a write that falls outside the active task's scope or touches
a researcher-owned file. It is also the only hook here that fails closed — a crash or a
timeout blocks the edit rather than letting it through.

The other four add context and warn. They never block.

All five are declared in `hooks/hooks.json`, and every one runs the same shipped file,
`bin/wizrelay.py`, in exec form — `python3 <file> hook <event>` — so there is no shell and
no command assembled at run time:

| Event | Timeout | What it does | On failure |
|---|---|---|---|
| `SessionStart` | 30 s | Injects the active task's context | continue |
| `UserPromptSubmit` | 10 s | Adds a one-line reminder of the active task | continue |
| `PreToolUse` | 15 s | **Denies** an out-of-scope or researcher-owned write | **block** |
| `Stop` | 20 s | Warns about unanswered questions and unverified criteria | continue |
| `PreModelSwitch` | 10 s | Warns when the new model is below the task's routing tier | continue |

## It is silent when unused

In a directory with no `.wizrelay/` and no `wizrelay-hub.json`, the plugin adds no context,
writes no file and makes no network call. Installing it at user scope does not change how
Claude Code behaves in your other projects.

## Requirements

- Claude Code ≥ v2.1.295
- Python ≥ 3.9 — the runtime uses the standard library only, with no third-party packages
- git

`/wizrelay:doctor` checks all three and reports what is missing.

## Surfaces

Claude Code only: the terminal, the desktop app's local and SSH sessions, and the VS Code
and JetBrains extensions. This plugin ships a top-level `bin/` directory for its launchers,
which claude.ai and Cowork refuse to install, and cloud sessions load no plugins at all.

## What it reads, writes and sends

The full statement is
[PRIVACY.md](https://github.com/ChessWizard/wizrelay/blob/main/PRIVACY.md); the short
version:

There is no wizrelay service. The plugin has no backend, no telemetry and no endpoint of
its own: it ships no HTTP client at all, and nothing is ever sent to its author.

| Destination | What goes there | When |
|---|---|---|
| Your hub repository | `git clone`, `git fetch` to read packages; `git push` when the researcher publishes | On `pull`, `sync` and `hub-publish` |
| Your issue tracker | Four comment types: the published package, a developer's question, the researcher's answer, a verification report | Only on `/wizrelay:ask`, `/wizrelay:verify` and `/wizrelay:hub-publish`, and only after you approve the exact text |
| Nothing else | — | — |

Both destinations are services **you** configure: the hub is the git URL in
`.wizrelay/config.json`, and the tracker is reached through the MCP connector you connect
or through your own `gh` CLI. The plugin declares no connector of its own. `wizrelay init
--tracker clickup` can add ClickUp's published MCP endpoint to your project's `.mcp.json`;
for every other tracker it writes no endpoint and prints instructions instead, because a
guessed endpoint can point credentials at the wrong host.

On your machine it reads `.wizrelay/`, the task package, and `git status`, `git diff` and
the current branch. It never reads git author names or email addresses.

**It reads no credential.** These are the only environment variables it reads anywhere in
`lib/wizrelay/`, and `tests/unit/test_environment.py` fails if one is added:

| Variable | Read for |
|---|---|
| `WIZRELAY_CACHE_DIR` | an explicit cache location |
| `WIZRELAY_DEBUG` | diagnostics on stderr |
| `WIZRELAY_PYTHON` | the interpreter the `bin/` launcher should use |
| `WIZRELAY_TRACKERS_DIR` | an alternative tracker descriptor directory |
| `XDG_CACHE_HOME` | the cache location on Linux |
| `LOCALAPPDATA` | the cache location on Windows |
| `CLAUDE_PLUGIN_DATA` | where the heartbeat file goes, since the plugin root is replaced on update |
| `CLAUDE_MODEL` | reporting whether the session model matches the task's routing tier |
| `CLAUDE_CODE_SESSION_ID` | keying that heartbeat to one session |

No token, key, password, `.netrc`, keychain or credential helper is read, and there is no
code that could: the package ships no HTTP client and every outbound call is `git`, which
authenticates with your own git configuration exactly as it does when you run it yourself.

Two places mention credentials on purpose, and both **reject** rather than read one:

* `has_embedded_credentials()` in `lib/wizrelay/paths.py` refuses a hub URL of the form
  `https://user:token@host`, so a token can never reach a config file, a cache directory
  name or an error message.
* `wizrelay init` writes a tracker's MCP endpoint only for a tracker whose published
  endpoint has been verified, and prints instructions for the rest, because a guessed
  endpoint can point credentials at the wrong host.

The plugin's own manifest declares **no MCP server**, no `userConfig` and no `env`. The one
entry `init` can write is ClickUp's published endpoint, and it carries exactly two fields:

```json
{ "clickup": { "type": "http", "url": "https://mcp.clickup.com/mcp" } }
```

Authentication there is OAuth, performed between you and ClickUp by your client. No token
passes through wizrelay, and `trackers.mcp_server_config` copies only `type`, `url`,
`command`, `args` and `headers` — never an `env` block — so no descriptor can forward a
variable from your environment into that file. `tests/unit/test_environment.py` asserts
both halves.

It writes `.wizrelay/` in your repository and a cache under your own cache directory. The
lock file records the task identifier, title, version, the hub commit and file hashes — no
personal data.

Where a tracker task carries a person's name, that text reaches the session like any other
task content, and the researcher's package is stored in your team's own repository.

## What ships in `bin/`

Files in a plugin's `bin/` are placed on the Bash tool's `PATH` while the plugin is
enabled, which is what lets a skill call `wizrelay` as a bare command. Two files are
there, both plain text, both short, and **neither contains any logic**:

| File | What it is |
|---|---|
| `bin/wizrelay` | A 30-line `#!/bin/sh` script. It picks an interpreter (`$WIZRELAY_PYTHON`, then `python3`, then `python`) and `exec`s the file below. Nothing else. |
| `bin/wizrelay.py` | Puts `lib/` on `sys.path` and calls `wizrelay.cli:main`. Nine statements. |

There is no compiled program, no archive, no generated file and nothing downloaded at
install time or at run time — the plugin declares no dependencies and installs nothing.
All of the behaviour lives in readable Python under `lib/wizrelay/`, outside `bin/`, where
it is covered by the test suite.

## Security

The plugin holds no team's content. Tracker comments and package text are treated as data,
never as instructions. Nothing is posted to a tracker without explicit approval.

Report a vulnerability through the repository's
[security policy](https://github.com/ChessWizard/wizrelay/blob/main/SECURITY.md).

## License

Apache-2.0.
