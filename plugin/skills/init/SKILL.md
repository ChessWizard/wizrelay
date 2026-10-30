---
name: init
description: Connect this repository to a research hub, and draft the repository profile that model routing reads.
disable-model-invocation: true
allowed-tools: Bash(wizrelay *)
argument-hint: "[role] [hub-url]"
---

Connect this repository to a wizrelay research hub.

**Write nothing outside `.wizrelay/`, `CLAUDE.md`, `.gitignore`, `.claude/settings.json`
and `.mcp.json`.** `wizrelay init` does that work; your job is the profile, which it can
only draft as placeholders.

**Do not commit.** Propose the commit and let the user run it.

## 1. Gather what `init` needs

`$ARGUMENTS` may already carry them positionally, as `backend git@github.com:acme/research-hub.git`.
Ask the user only for what neither the arguments nor the repository tell you:

- **role** — this repository's name inside a task (`backend`, `frontend`, `mobile`). The
  hub decides the vocabulary; if `--role` was passed, use it.
- **hub** — the git URL of the team hub, or a local path for a working copy.
- **tracker** — `clickup`, `github`, `jira`, `linear`, `azure-devops` or `none`.

## 2. Run it

```
wizrelay init --role <role> --hub <url> --tracker <type>
```

It is idempotent: a second run reports "nothing changed". Report what it created.

## 3. Draft the repository profile

`.wizrelay/profile.json` arrives with `{{placeholders}}`. Routing reads it, so a wrong
profile produces a wrong model choice. Determine each field from the repository itself and
show the user your reasoning before writing:

- `stack` — language, framework and datastore, from the dependency manifests.
- `commands` — the project's **own** commands for test, targeted test, lint and typecheck.
  Take them from `Makefile`, `package.json` scripts, `pyproject.toml`, `justfile` or CI
  workflow files. Never invent one. `test_targeted` uses `{path}` as the placeholder.
- `codebase_size` — `small`, `medium` or `large`. Count source files, not lines.
- `test_maturity` — `low`, `medium` or `high`. Judge it from the ratio of test files to
  source files and whether CI runs them, not from how the tests are written.
- `critical_paths` — globs where a mistake is expensive: authentication, billing,
  migrations, payment handling. These raise the routing score.
- `legacy_paths` — globs that are risky to touch for other reasons: no tests, a rewrite in
  progress, a module nobody owns.
- `incidental_allow` — paths an in-scope change may legitimately touch beyond the lock
  files already allowed by default.

Show the user the proposed JSON, ask for corrections, then write the file.

## 4. Verify and hand over

```
wizrelay doctor
```

Resolve every line marked `x`. A failing `python3` check means the hooks cannot run, which
means scope protection is silently absent — treat it as blocking.

Then tell the user:

- which files to commit: `.wizrelay/config.json`, `.wizrelay/profile.json`,
  `.wizrelay/PROTOCOL.md`, `CLAUDE.md`, `.gitignore`, `.claude/settings.json`
- which file stays local: `.wizrelay/config.local.json`, for a personal hub path
- the next command: `/wizrelay:pull <task reference>`

Answer in the language set in `.wizrelay/config.json`.
