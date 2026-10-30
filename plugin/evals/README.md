# Eval suite

Behavioural tests for the skills, run with `claude plugin eval`.

The unit, golden and integration suites prove the deterministic half of this project: the
CLI, the hook contract, the glob engine. They cannot prove the other half. Whether `ask`
declines to invent a decision, or `verify` resists fixing the code it is checking, is model
behaviour, and only an eval measures it.

## Why these cases are here and not in `tests/evals/`

An eval directory has to live **below the plugin root**: the default is `evals/` inside the plugin, and the `experimental.evals`
manifest key can only name another directory under the same root
. `tests/evals/` is a sibling of `plugin/`, so it
cannot be the eval directory. The suite therefore lives here.

## Run it

From the plugin root:

```bash
claude plugin eval .
```

Two cases need a workspace, so to run the whole suite:

```bash
claude plugin eval . --scaffold
```

`--scaffold` runs each case's `scaffold_script` as you, outside the agent's sandbox. Read
the scripts before passing it. Both of ours only create files under the empty workspace.

Every run and every judge call is billed to the account that runs it, so this is a nightly
and pre-release gate rather than a per-commit one.

## The cases

| Case | What it measures | Needs `--scaffold` |
|---|---|---|
| `ask-does-not-invent-a-decision` | The package is silent, so `ask` says so instead of producing a plausible answer | no |
| `ask-answers-from-the-package` | The package does answer, so `ask` answers it and cites the file | no |
| `plan-stays-in-scope` | A plan proposes only in-scope files and raises the scope gap as a question | no |
| `pull-writes-no-code` | Loading a package is not implementing it | no |
| `verify-does-not-change-code` | A verifier reports a failing criterion rather than fixing the code | yes |

`ask-does-not-invent-a-decision` is the one to watch. Its failure mode — a confident answer
the researcher never gave — is the most expensive thing this plugin can produce, because it
looks like a decision, gets implemented, and nobody knows it was invented. That rate has to
be zero.

## What an eval cannot cover

A run loads the plugin under test and nothing else: no `.claude/` directory, no
`CLAUDE.md`, no `.mcp.json`, not even files a scaffold script wrote
. So an eval exercises the hooks and skills but
**not** the permission deny rules and **not** the `CLAUDE.md` protocol import. Those two
are checked by hand.

## Reading a result

Each case runs three times with the plugin and three times without it. `Δ` is the
difference, and it is the only number that says the plugin contributed anything: a case
scoring 1.0 in both arms would have passed without wizrelay at all.

A `tool_used` grader on `Skill` is reported but not scored, because it can never pass in
the without-arm. The two "must not" graders set `arm: both` so they are scored in both
arms, which is what makes "did not edit the source" meaningful rather than vacuous.
