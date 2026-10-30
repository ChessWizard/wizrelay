<!-- nav:top -->
[Documentation](README.md) › **Appendix D — Checklists** &nbsp;·&nbsp; [Türkçe](../tr/appendix-d-checklists.md)
<!-- /nav:top -->

# Appendix D — Checklists

Copy these into an issue or a wiki page. Each one exists because its steps are easy to skip
and expensive to skip.

## Team setup, once

- [ ] The `wizrelay` plugin is installed ([section 4](04-install-plugin.md))
- [ ] The hub repository is created, `/wizrelay:hub-init` has run, and it is pushed ([section 5](05-set-up-hub.md))
- [ ] The tracker MCP is connected (`/mcp`)
- [ ] `CODEOWNERS` and branch protection are set on the hub — **this is the trust boundary**
- [ ] `/wizrelay:init` has run in each project repository, `profile.json` was reviewed, and it is committed ([section 6](06-connect-repository.md))
- [ ] The CI gate is added, with `on-missing-task: skip` to start ([section 12](12-ci-integration.md))
- [ ] One real task has been through the whole loop before rolling out to the rest

That last item is the one people skip. The first task is where you find out whether your
`roles` vocabulary and your `critical_paths` are right, and finding out on one task is
cheaper than on six.

## A new team member

- [ ] Claude Code ≥ v2.1.295, Python ≥ 3.9 with `python3` on `PATH`, git
- [ ] Read access to the hub repository
- [ ] The plugin is installed and `/wizrelay:doctor` is clean
- [ ] Signed in to the tracker (`/mcp`)
- [ ] Has read [1. Overview](01-overview.md), [8. Developer workflow](08-developer-workflow.md) and [11. Scope protection](11-scope-protection.md)

## Researcher, before publishing

- [ ] Every tracker requirement maps to at least one acceptance criterion
- [ ] Every criterion has a role, Given/When/Then and a verification line naming a command
- [ ] Every interface between roles is defined in `contracts.md`, with an identifier
- [ ] No open questions remain; the decisions are in `decisions.md`
- [ ] Every claim about the current state cites a path
- [ ] The scope is narrow, includes tests and migrations, and has the critical areas in `deny`
- [ ] The signals were chosen for a reason you could state out loud
- [ ] `/wizrelay:hub-validate` shows nothing blocking

## Developer, every day

- [ ] Read the warnings at session start — a new version? an integrity problem?
- [ ] Work with the suggested model and effort
- [ ] Do nothing that is not in the plan; when unsure, `/wizrelay:ask`
- [ ] `/wizrelay:verify` before calling it done
- [ ] Commit messages carry criterion identifiers; `.wizrelay/tasks/` is committed

## Developer, when blocked

- [ ] Is the file the researcher's? → `/wizrelay:ask` to request the change
- [ ] Is the change in the plan? If not, re-read the plan
- [ ] If it is genuinely needed: write the reason in `questions.md`, `/wizrelay:ask`, wait
      for the new version, `/wizrelay:sync`
- [ ] **Do not** widen the scope locally, and do not route around the block with a shell
      command — the CI gate checks the same scope

## Researcher, answering a question

- [ ] Which of the four kinds is it? ([9. The question loop](09-question-loop.md))
- [ ] The decision is implementable without further interpretation
- [ ] `Impact` names every criterion, contract and scope entry that changes
- [ ] Anything the decision contradicts was changed in the same version
- [ ] Published, and the `[WIZRELAY-A]` reply points at the decision

## Before you trust the protection

- [ ] `/wizrelay:doctor` is clean on one developer's machine
- [ ] `/wizrelay:status` in a connected repository does **not** show `WIZRELAY_NO_GUARD`
- [ ] An edit to a researcher file is refused
- [ ] An out-of-scope edit is refused
- [ ] A deliberately out-of-scope pull request turns the CI check red
- [ ] A second plugin named `wizrelay`, installed on purpose, makes `doctor` report an error

Record the Claude Code version and the result beside each line you tick: a check without a
version is not evidence, because the behaviour it proves can change in the next release.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← Appendix C — Tracker comment tags](appendix-c-tracker-tags.md) | [Contents](README.md) | [Appendix E — Glossary →](appendix-e-glossary.md) |
<!-- /nav:bottom -->
