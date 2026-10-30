# Contributing to wizrelay

Thank you for helping. This document covers the development setup, the rules the code has
to follow, and what a pull request needs before it can be merged.

## Ground rules

Two constraints shape almost every decision in this repository:

1. **Runtime code uses the Python >= 3.9 standard library only.** No third-party import
   may appear anywhere under `plugin/lib/wizrelay/`. `tests/unit/test_stdlib_only.py`
   enforces this. Development dependencies exist for testing and linting only.
2. **The plugin carries no team content** (design invariant I1). No company
   name, hub URL, role list or task value belongs in `plugin/`. Examples live in
   `examples/`, and templates use `{{placeholder}}` markers.

There are thirteen invariants in all, I1 to I13, each with the test that
guards it. A change that breaks one is not merged.

## Development setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
make lint test
```

`make` targets:

| Target | What it runs |
|---|---|
| `make lint` | `ruff check`, `ruff format --check`, `mypy` (strict on the core) |
| `make test` | The whole pytest suite |
| `make unit` | `tests/unit/` only |
| `make golden` | The hook contract tests in `tests/golden/` |
| `make e2e` | The CLI integration scenarios in `tests/integration/` |
| `make cov` | Coverage with the gate (core >= 90%, total >= 80%) |
| `make validate-plugin` | `claude plugin validate ./plugin --strict`, skipped when the CLI is absent |
| `make fmt` | Apply formatting |

## Architecture rules

- **Layers:** `core` (pure functions, no IO) <- `services` (git, filesystem) <-
  `cli` / `hooks` (entry points). `tests/unit/test_architecture.py` asserts both the layer
  direction and the absence of circular imports.
- **Subprocesses:** `subprocess.run([...], shell=False, timeout=...)`. Put `--` before
  paths and refs in git arguments. Read output with `text=True, encoding="utf-8"`.
- **Paths:** use `pathlib`. Compare repository-relative paths in POSIX form. All text files
  are UTF-8 with LF endings.
- **Deterministic output:** sort lists, write JSON with `indent=2, ensure_ascii=False` and
  a trailing newline, and use UTC ISO-8601 timestamps.
- **No global state:** pass configuration and dependencies as function parameters.
- **Forbidden constructs:** `eval`, `exec`, `pickle`, `shell=True`. The lint configuration
  rejects them.
- **Error messages** have three parts — what happened, why, what to do next, with the
  command to run — and come from the i18n catalogue, never from a literal string.

## Hook changes

The hook contract is locked by golden tests. To change hook behaviour:

1. Add or change the case under `tests/golden/<event>/<case>/{input,expected}.json`.
2. Watch it fail.
3. Change the handler.
4. Say so in the pull request if the contract itself moved, so the maintainer can update
   the plan and the research notes.

`PreToolUse` is the only fail-closed hook (`onFailure: "block"`, internal error maps to
`ask`). Everything else fails open: a session must never become unusable because of
wizrelay.

## Claude Code behaviour

Never assume it. Verify every detail — hook fields, skill and agent front matter, the
plugin manifest, marketplace and permission rules — against the official Claude Code
documentation, and quote the source URL, the date and the Claude Code version in the pull
request. The maintainer keeps a research file of those findings outside this repository.

## About the citations in the source

Comments and docstrings cite documents that are not in this repository: the implementation
plan, the architecture decision records, and the research notes on verified Claude Code
behaviour. The maintainer keeps those, and nothing in the build reads them — the citations
are there to say *why* a line is the way it is. Where one matters to a change you are
making, ask in the pull request and the relevant part will be quoted for you.

## Commits and branches

- **Conventional Commits.** Scope prefixes: `core`, `cli`, `hooks`, `skills`, `agents`,
  `trackers`, `docs`, `ci`, `release`. Example: `fix(core): treat an empty glob prefix as
  intersecting`.
- `main` is protected. Work on `phase/<n>-<slug>` for plan phases, or
  `fix/<slug>` / `feat/<slug>` otherwise. Pull request plus squash merge.
- Version tags are signed (`git tag -s`).

### Branch protection settings

`main` requires: a pull request before merging, one approving review, the `CODEOWNERS`
review where it applies, all required status checks from `.github/workflows/ci.yml`
passing, branches up to date before merging, and conversation resolution. Force pushes and
deletions are blocked.

## Definition of done

Every work package:

- [ ] The relevant acceptance criteria are proven by a test, or by a checklist where a
      test is impossible
- [ ] `make all` is green
- [ ] User-visible changes match the published documentation under `docs/`
- [ ] `CHANGELOG.md` `Unreleased` is updated
- [ ] An ADR is written when the decision is architectural
- [ ] A new configuration key is added to its schema, to the defaults, and to the docs
- [ ] New messages exist in both the `en` and `tr` catalogues

## Adding a tracker adapter

1. `plugin/trackers/<type>.json` — the machine-readable descriptor.
2. `plugin/trackers/<type>.md` — the instructions skills read on demand.
3. Add identifier-normalisation and URL cases to `tests/unit/test_trackers.py`.
4. An MCP endpoint goes into the descriptor **only** once it is verified, with the source
   quoted in the pull request. An unverified endpoint is never written into a user's
   configuration automatically.

## Reporting security issues

Do not open a public issue. Follow [SECURITY.md](SECURITY.md).
