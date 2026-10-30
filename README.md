<!-- lang -->
**English** &nbsp;·&nbsp; [Türkçe](README.tr.md)
<!-- /lang -->

# wizrelay

Carry a researcher's task analysis from one source of truth into every developer's Claude
Code session — deterministically.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-%E2%89%A5%20v2.1.295-5A3FD6.svg)](https://code.claude.com/docs)

---

## The problem

In an AI-native team, an analyst works out what a task requires. Each developer then works
in their own AI coding session. Those sessions read the same analysis and interpret it
differently — and the result is scope drift, contract mismatches between roles, and bugs.

Sharing the analysis does not fix this on its own. **Following an instruction is
probabilistic; enforcing a rule has to be deterministic.** wizrelay is the
second thing.

## What it does

| | |
|---|---|
| **One source of truth** | A researcher publishes a versioned task package to a private team hub. Developers pull a read-only, hash-verified copy. |
| **Deterministic context** | The package summary is re-injected at every session start and after every compaction, so the analysis does not drift out of the conversation. |
| **Layered scope protection** | Permission deny rules, a `PreToolUse` hook, an end-of-turn audit, a verification step, and a CI gate. Five layers, because each one catches what the one above it misses. |
| **Model and effort routing** | A policy turns the task's signals and the repository's profile into a tier, and the tier into a model and effort level per phase. |
| **A question loop** | A question the package cannot answer goes to the researcher through the tracker and comes back as a decision in a new package version. |
| **Verification on the developer's side** | An independent verifier — one that cannot edit files — pairs every acceptance criterion with evidence. |

It is tracker-agnostic, role-agnostic and project-agnostic: the plugin itself carries no
team content.

## How it fits together

```
                PLUGIN (wizrelay) — installed in everyone's Claude Code
                                │  reads / writes
                                ▼
                 TEAM HUB  (acme/research-hub, private git)
                 tasks/CU-86c1abcd-…/    tasks/CU-91f2aa10-…/
                                │  /wizrelay:pull
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
          api-service           web-app               deploy-infra
          role: backend         role: frontend        role: infra
          .wizrelay/            .wizrelay/            .wizrelay/
```

One hub per **team**, not per project. Adding a repository to the team does not need a new
hub.

## Quick start

**Install**, once per machine:

```
/plugin marketplace add ChessWizard/wizrelay
/plugin install wizrelay@wizrelay
```

**Researcher**, once per team, then once per task:

```
/wizrelay:hub-init
/wizrelay:hub-new 86c1abcd backend,frontend
/wizrelay:hub-validate CU-86c1abcd
/wizrelay:hub-publish CU-86c1abcd
```

**Developer**, once per repository, then once per task:

```
/wizrelay:init backend git@github.com:acme/research-hub.git
/wizrelay:pull CU-86c1abcd
/wizrelay:plan
/wizrelay:verify
```

Full walkthrough: [docs/en/15-walkthrough.md](docs/en/15-walkthrough.md).

## Documentation

**[→ Documentation index](docs/en/README.md)** · one guide, one file per section.

| Start here | |
|---|---|
| [1. Overview](docs/en/01-overview.md) | What it is and why it is built this way |
| [2. What it does and does not do](docs/en/02-scope.md) | Scope, non-goals, and who does what |
| [15. Worked example](docs/en/15-walkthrough.md) | One task from tracker to merged pull request |

| Set it up | |
|---|---|
| [3. Prerequisites](docs/en/03-prerequisites.md) · [4. Install](docs/en/04-install-plugin.md) · [5. Hub](docs/en/05-set-up-hub.md) · [6. Connect a repository](docs/en/06-connect-repository.md) | |

| Use it | |
|---|---|
| [7. Researcher](docs/en/07-researcher-workflow.md) · [8. Developer](docs/en/08-developer-workflow.md) · [9. The question loop](docs/en/09-question-loop.md) | |

| Mechanics | |
|---|---|
| [10. Routing](docs/en/10-routing.md) · [11. Scope protection](docs/en/11-scope-protection.md) · [12. CI](docs/en/12-ci-integration.md) | |

| Operate | |
|---|---|
| [13. Team and enterprise](docs/en/13-team-and-enterprise.md) · [14. Customisation](docs/en/14-customisation.md) | |

| Reference | |
|---|---|
| [16. Troubleshooting](docs/en/16-troubleshooting.md) · [17. FAQ](docs/en/17-faq.md) · [Commands](docs/en/appendix-a-commands.md) · [Files](docs/en/appendix-b-files.md) · [Glossary](docs/en/appendix-e-glossary.md) | |

## Requirements

- Claude Code ≥ v2.1.295
- Python ≥ 3.9, with `python3` on `PATH` — the hooks need it
- git

The runtime uses the Python standard library only. Nothing installs dependencies for a
plugin, so a single third-party import would break it for anyone whose Python lacks that
package.

## Install the CLI

For CI, or to use it without Claude Code:

```bash
pip install "git+https://github.com/ChessWizard/wizrelay@v1.0.0"
```

Every deterministic operation has a CLI equivalent — `wizrelay pull`, `audit`,
`hub validate`, `hub publish-prep` — so the same behaviour is available in a terminal and
in CI.

## Try it without a hub

The repository ships a working hub and two connected projects:

```bash
cd examples/dev-backend && wizrelay pull CU-86c1abcd && wizrelay route
```

The same package routes to a different tier in `examples/dev-frontend`, because routing is
computed per role. See [examples/README.md](examples/README.md).

## Project status

Pre-release. What has landed is in [CHANGELOG.md](CHANGELOG.md). The implementation plan
is maintained outside this repository.

## Security

wizrelay is a **guardrail, not a jail**. Read
[11. Scope protection](docs/en/11-scope-protection.md) for what each layer does and does
not stop, and [SECURITY.md](SECURITY.md) for the threat model and how to report a
vulnerability.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). By participating you agree to the
[Code of Conduct](CODE_OF_CONDUCT.md).

## License

[Apache-2.0](LICENSE)
