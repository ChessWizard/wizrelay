# wizrelay scope audit — GitHub Action

Fails a pull request that changes files outside the scope the researcher published for its
task. This is layer 5 of the scope protection: the layer that does not depend on the developer's
session behaving well.

## Use it

```yaml
name: Scope
on: pull_request

jobs:
  scope:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: ChessWizard/wizrelay/integrations/github-action@v1.0.0
        with:
          version: v1.0.0
```

`fetch-depth: 0` matters: the audit diffs `base...HEAD`, and a shallow checkout has no
merge base.

## Inputs

| Input | Default | What it does |
|---|---|---|
| `version` | `v1.0.0` | The wizrelay version to install. Pin it. |
| `base` | the PR's base branch | Ref to diff against. |
| `task` | from the branch name, then the PR title | Task reference. |
| `on-missing-task` | `skip` | `skip` passes when no task is found; `fail` fails. |
| `python-version` | `3.12` | Interpreter used to run wizrelay. |

## Outputs

| Output | What it is |
|---|---|
| `violations` | Number of violations. `0` when clean or skipped. |
| `skipped` | `true` when no task was determined and the mode is `skip`. |

## How the task is found

1. `task` input, when given.
2. The branch name: `feature/CU-86c1abcd-quota` resolves to `CU-86c1abcd`. A
   `refs/heads/` prefix is stripped, and matching is case-insensitive.
3. Nothing matched: skip or fail, per `on-missing-task`.

Default to `skip`. A repository has branches that are not working on a package —
dependency bumps, documentation, hotfixes — and failing those teaches people to ignore
the check. Switch to `fail` once every branch in the repository is expected to carry a
task.

## What it requires in the repository

The audit reads `.wizrelay/` from the checkout, so the pull request branch needs the
pulled package committed. If your team does not commit `.wizrelay/tasks/`, the audit has
no scope to check against and reports a skip.
