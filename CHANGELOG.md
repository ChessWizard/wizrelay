# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-08

### Added

- `/wizrelay:implement` — the step between planning and verifying. It reads `plan.md`,
  works the unchecked steps in order inside the role's scope, runs each step's own test
  and checks the step off only once that test has passed. Until now the plan was written
  and then nothing in the plugin carried it out, so a panel run either stopped after
  planning or opened a session with no brief, no scope and no record of which step it was
  on.
- Questions can say who they are for. `Ask:` (or `Kime:`) in `questions.md` addresses a
  question, and `@` anywhere in it does the same. A question that names nobody belongs to
  the project's research lead. A dashboard can then show a question to the person who can
  answer it instead of to everybody.

### Changed

- `/wizrelay:implement` writes no explanatory comments. Method and field summaries are
  the exception; a comment that narrates code is a second copy of it that nobody updates.

## [0.1.1] - 2026-11-08

### Fixed

- `/wizrelay:plan` now writes `plan.md` instead of describing a plan and stopping. A
  session driven headlessly has no turn in which a person can approve, so the run ended
  with the scaffold untouched and the placeholders still in it. The skill writes when
  `plan.md` is still the scaffold, and asks only when a real plan with checked-off steps
  would be replaced.
- `/wizrelay:plan` takes anything said alongside the command as part of the brief, and
  says in the plan where it changed a step.

### Added

- Repository skeleton, governance files, tooling and CI (phase 0).
- Core domain model: glob engine, text-format parsers, stdlib schema validator, layered
  configuration, routing policy engine, lock files, i18n catalogue (phase 1).
- Hub and repository operations as a CLI: `init`, `pull`, `sync`, `status`, `brief`,
  `route`, `activate`, `audit`, `doctor`, `migrate`, and the `hub` command group (phase 2).
- Hook layer for `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `Stop` and
  `PreModelSwitch`, with golden tests (phase 3).
- Developer skills, `codebase-mapper` and `test-engineer` agents, developer templates
  (phase 4).
- Researcher skills, `research-critic` agent, hub templates (phase 5).
- Tracker adapters for ClickUp, GitHub Issues, Jira, Linear, Azure DevOps and `none`
  (phase 6).
- CI audit component for GitHub Actions, GitLab CI and Azure Pipelines, plus managed
  settings examples (phase 7).
- Bilingual product documentation: 22 sections in English and Turkish, one file per
  section, with generated navigation (`scripts/docs_nav.py`), a per-language index, and
  `tests/unit/test_docs.py` enforcing section parity, link resolution and navigation
  freshness. Runnable examples under `examples/` (phase 8).

### Changed

- Every example in the repository is now a placeholder. The organisation is `acme`, the
  example repositories are `api-service`, `web-app` and `deploy-infra`, and the worked
  example is a per-tenant daily API request quota. The documentation,
  the example hub package and the example projects previously
  named a real organisation, three of its repositories and a third-party messaging
  product (invariant I1).
- The `OWNER` placeholder is filled in: the plugin manifest, the marketplace entry, the
  schema `$id`s, `pyproject.toml`, `CODEOWNERS`, the CI integrations and the install
  instructions all name `ChessWizard/wizrelay`.
- `plugin/README.md`, which the pre-release checklist for publishing requires at the plugin
  root: what installing the plugin adds, the 14 commands, what the hooks do, the
  requirements and the surfaces it runs on.
- `docs/{en,tr}/04-install-plugin.md` now covers every install surface — terminal, desktop
  app, VS Code, JetBrains and cloud sessions — states that `/plugin install` opens the panel
  rather than installing outright, corrects the claim that the panel opens on **Installed**
  (it opens on **Discover**), and says auto-update is off for this marketplace.
- One name instead of three. The product was called "Wizard Research Relay", its
  repository and marketplace `wizard-research-relay`, and only the plugin `wizrelay`.
  All of them are now `wizrelay`, so the install id is `wizrelay@wizrelay`. The manifest name did not change, so `/wizrelay:` commands, `.wizrelay/`,
  `wizrelay-hub.json` and the `[WIZRELAY-*]` tracker tags are untouched.

### Added

- `plugin/.claude-plugin/icon.png`: a 1024 x 1024 listing icon, the relay the product is
  named after drawn as a hub with three lines leaving it.

### Fixed

- The session id three skills passed was never set. They expanded `${CLAUDE_SESSION_ID:-}`,
  but the variable Claude Code sets is `CLAUDE_CODE_SESSION_ID`, so the spans sent an empty
  string and the heartbeat behind invariant I13 was never checked. `wizrelay brief` now
  reads the variable itself and the spans are fixed literals, which also stops a security
  scan reading them as commands assembled at run time. `tests/conftest.py` clears the
  variable, because a suite run from inside a Claude Code session was otherwise inheriting a
  real session id.

- Two tests assumed the machine they run on. `test_stdlib_only.py` used
  `sys.stdlib_module_names`, which arrived in Python 3.10 while the floor here is 3.9. The
  3.9 fallback now asks the import system where a module resolves instead of listing the
  standard library directory: on POSIX an extension module such as `unicodedata` sits in
  `lib-dynload` under that directory, but on Windows it sits in `DLLs`, outside every path
  `sysconfig` reports. Three tests cover the fallback on every Python version — that it
  accepts each import the runtime makes, that it still rejects an installed package, and
  that it does not read the standard library directory at all. `test_hubrepo.py` set `HOME`
  to check that `~` expands, but on Windows `expanduser` reads `USERPROFILE` and never
  looks at `HOME`, so the path resolved to the runner's real home; it now sets both.
- `plugin/bin/wizrelay.py` no longer shadows the package it imports. A script's own
  directory comes first on `sys.path`, and that directory holds `wizrelay.py`, so
  `import wizrelay` could resolve to the launcher instead of the bundled package and fail
  with `'wizrelay' is not a package`. The launcher now drops its own directory and inserts
  `plugin/lib` unconditionally rather than only when it is absent — a path already present
  further down does not give the bundled copy precedence. This also makes the guarantee
  the launcher documents true in every case: the bundled library wins over an installed
  `wizrelay`, so the hook contract always matches the plugin's own version.

[Unreleased]: https://github.com/ChessWizard/wizrelay/compare/v0.0.0...HEAD
