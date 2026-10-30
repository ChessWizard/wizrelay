## What this changes

<!-- One or two sentences. -->

## Acceptance criteria and evidence

<!-- One row per behaviour this PR commits to. Evidence is a command plus its result, not a claim. -->

| What it must do | Evidence (command / test) | Result |
|---|---|---|
|  |  |  |

## Definition of done

- [ ] Every behaviour this PR commits to is proven by a test, or by a checklist where a test is impossible
- [ ] `make lint test` is green locally
- [ ] CI is green
- [ ] User-visible changes match the published documentation under `docs/`
- [ ] `CHANGELOG.md` `Unreleased` is updated
- [ ] A new configuration key is added to its schema, to the defaults, and to the docs
- [ ] New user-visible messages exist in both the `en` and `tr` catalogues

## Invariants

- [ ] No team, company or project value was added under `plugin/`
- [ ] The plugin is still silent in a directory with no marker file
- [ ] Researcher files stay read-only; developer files are never overwritten
- [ ] Hook behaviour changes, if any, appear in a golden test first

## Claude Code behaviour

- [ ] Every new assumption about Claude Code is backed by the official documentation, with the source URL, the date and the Claude Code version quoted in this pull request
