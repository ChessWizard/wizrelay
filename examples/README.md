# Examples

Three directories that make the workflow runnable without a real hub or a real tracker.

| Directory | What it is |
|---|---|
| `hub/` | A research hub with one published package, a team routing policy, and both roles filled in |
| `dev-backend/` | A small Python project, connected to `hub/`, with the backend scope |
| `dev-frontend/` | A small TypeScript project, connected to the same `hub/`, with the frontend scope |

One hub serving two repositories is design invariant I3, and these two directories are
what the integration test for it mirrors.

## Try the loop

The commands below use `hub.path`, so nothing is cloned and no network is used.

```bash
cd examples/dev-backend
wizrelay status
wizrelay pull CU-86c1abcd
wizrelay route
```

`route` should print `T4-high-risk`, score 10. Three things combine to produce it:

| Source | Contribution |
|---|---|
| The package's signals: complexity medium, risk high, ambiguity low | 2 + 3 + 1 = 6 |
| This repository's `test_maturity: low` | +2 |
| This repository's `critical_paths` overlapping the backend scope | +2 |

The last two are worth **2** rather than 1 because `hub/policies/routing-policy.json`
overrides the plugin's default modifier weights. Delete that file and the same task routes
to `T3-critical` with score 8 on the shipped defaults — which is what a team policy is
for.

Then run the same commands in `dev-frontend`: the identical package routes to
`T1-routine`, score 3. The package lowers the signals for the frontend role, and nothing
in that repository's profile adds a modifier.

Then introduce a violation and watch the audit catch it:

```bash
echo "x" >> app/billing/invoice.py     # explicitly denied
echo "y" > README.md                   # outside the scope
wizrelay audit --base ""
```

It exits 1 and names both, with the pattern that fired for the denied one.

## Try the researcher side

```bash
cd examples/hub
wizrelay hub list
wizrelay hub validate CU-86c1abcd
wizrelay hub comment CU-86c1abcd
```

`hub validate` passes on this package: it is the one the end-to-end run produced, so it is
a worked example of what a complete package looks like rather than a sketch.

## What to read

The package under `hub/tasks/` is the most useful file in here. It shows the level of
evidence `research.md` is meant to carry, what a verifiable acceptance criterion looks
like, and how `contracts.md` pins an interface between two roles.
