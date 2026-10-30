<!-- nav:top -->
[Documentation](README.md) › **12. CI integration** &nbsp;·&nbsp; [Türkçe](../tr/12-ci-integration.md)
<!-- /nav:top -->

# CI integration

The pull-request gate: the only layer that does not run inside the developer's own session.

## What it does

It compares the changes in a pull request against the scope of that pull request's task.

It needs **no access to the hub**: it uses the `.wizrelay/tasks/` copy in the repository.
That is why committing the task directory matters
([8. Developer workflow](08-developer-workflow.md)). The task itself is found from the
identifier in the branch name.

If you set up only one thing from this guide, set up this. Everything else can be turned
off by the person it protects.

## GitHub Actions

The shipped action is the short form:

```yaml
name: Scope
on:
  pull_request:
    branches: [main]

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
          on-missing-task: skip
```

Or by hand, if you want to see what it does:

```yaml
name: wizrelay-scope-gate
on:
  pull_request:
    branches: [main]

jobs:
  scope:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install wizrelay
        run: pip install "git+https://github.com/ChessWizard/wizrelay@v1.0.0"
      - name: Scope audit
        run: >
          wizrelay audit
          --branch "${{ github.head_ref }}"
          --base "origin/${{ github.base_ref }}"
          --format md | tee -a "$GITHUB_STEP_SUMMARY"
```

Two details:

- **`fetch-depth: 0` matters.** The audit diffs `base...HEAD`, and a shallow checkout has no
  merge base. Without it the audit degrades to the working tree, which in CI is empty.
- GitHub's default bash shell runs with `pipefail`, so a violation turns the step red and
  the report appears in the job summary.

Then make `wizrelay-scope-gate / scope` a required check in the branch protection rules, or
the gate is advisory.

## Inputs on the shipped action

| Input | Default | What it does |
|---|---|---|
| `version` | `v1.0.0` | The wizrelay version to install. Pin it |
| `base` | the pull request's base branch | The ref to diff against |
| `task` | from the branch name, then the PR title | The task reference |
| `on-missing-task` | `skip` | `skip` passes when no task is found; `fail` fails |
| `python-version` | `3.12` | The interpreter used to run wizrelay |

Outputs: `violations` (a count, `0` when clean or skipped) and `skipped`.

## GitLab CI

```yaml
wizrelay-scope-gate:
  image: python:3.12
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - pip install "git+https://github.com/ChessWizard/wizrelay@v1.0.0"
    - git fetch origin "$CI_MERGE_REQUEST_TARGET_BRANCH_NAME"
    - wizrelay audit --branch "$CI_MERGE_REQUEST_SOURCE_BRANCH_NAME" --base "origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME"
```

## Azure Pipelines

```yaml
steps:
  - checkout: self
    fetchDepth: 0
  - script: |
      pip install "git+https://github.com/ChessWizard/wizrelay@v1.0.0"
      wizrelay audit --branch "$(System.PullRequest.SourceBranch)" --base "origin/$(System.PullRequest.TargetBranchName)"
    displayName: wizrelay scope gate
```

A `refs/heads/` prefix is stripped by the CLI, so Azure's full ref works as given.

Ready-to-copy files for all three are in
[`integrations/`](../../integrations/).

## Behaviour settings

| Situation | Default | To change it |
|---|---|---|
| No task identifier in the branch name | Reports "skipped" and passes | `--require-task` makes it a failure |
| `--base` cannot be resolved | Looks only at the working tree, and says so | `fetch-depth: 0` to fetch the history |
| Report format | `md` | `--format json` |

**Start with the default skip.** A repository has branches that are not working on a package
— dependency bumps, documentation, hotfixes — and failing those teaches people to ignore
the check, which costs you more than the branches you were trying to catch. Switch to
`--require-task` once every branch is expected to carry a task.

## How the task is found

1. The `task` input, when given.
2. The branch name: `feature/CU-86c1abcd-quota` resolves to `CU-86c1abcd`. A `refs/heads/`
   prefix is stripped, and matching is case-insensitive.
3. Nothing matched: skip or fail, per the setting.

## What the report looks like

```markdown
## Scope audit — CU-86c1abcd (backend)
2 violation(s) found.

### Explicitly denied
- `app/billing/invoice.py` — `app/billing/**`

### Outside this role's scope
- `README.md`

### In scope (1)
- `app/quota/service.py`

### Incidental (build artefacts and wizrelay setup)
- `poetry.lock`
```

Exit codes: `0` clean or skipped, `1` a violation. `--no-fail` always exits 0, which is how
you run it for the report alone.

## If the gate is red and your machine is clean

The usual cause is that CI looks at every commit in the pull request while you looked at
your working tree. Reproduce it locally:

```bash
wizrelay audit --base origin/main
```

## Headless verification

Running the full `/wizrelay:verify` in CI — with `claude -p` — and posting the result as a
pull request comment is on the roadmap, not in v1. The deterministic half of verification,
the scope and integrity audit, is what the gate runs today.

## Next

[13. Team and enterprise administration](13-team-and-enterprise.md).

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 11. Scope protection](11-scope-protection.md) | [Contents](README.md) | [13. Team and enterprise administration →](13-team-and-enterprise.md) |
<!-- /nav:bottom -->
