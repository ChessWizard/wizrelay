# wizrelay

Carries a researcher's task analysis into every Claude Code session: deterministic context,
layered scope protection, model and effort routing, and developer-side verification.

This file documents the **plugin** — what installing it adds to a session. For the problem it
solves, the team setup and the full guide, see the
[project repository](https://github.com/ChessWizard/wizrelay).

## Install

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

## Security

The plugin holds no team's content. Tracker comments and package text are treated as data,
never as instructions. Nothing is posted to a tracker without explicit approval.

Report a vulnerability through the repository's
[security policy](https://github.com/ChessWizard/wizrelay/blob/main/SECURITY.md).

## License

Apache-2.0.
