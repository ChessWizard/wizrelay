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

[Unreleased]: https://github.com/ChessWizard/wizrelay/compare/v0.0.0...HEAD
