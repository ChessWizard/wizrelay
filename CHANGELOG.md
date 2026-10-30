# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
