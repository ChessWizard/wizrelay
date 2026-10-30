<!-- nav:top -->
[Documentation](README.md) › **10. Model and effort routing** &nbsp;·&nbsp; [Türkçe](../tr/10-routing.md)
<!-- /nav:top -->

# Model and effort routing

How a task's signals and a repository's profile become a model, an effort level and a launch
command.

## Why it exists

Not every task needs the same model or the same depth of thinking. Running Opus at high
effort on a trivial change wastes time and quota; running Sonnet at low effort on a critical
change is a risk.

The deeper reason is about who knows what. The person opening the session is the one least
equipped to decide: the **researcher** knows how risky the task is, and the **repository**
knows how well tested it is. Routing moves the decision to where the information already
is.

## How the score is computed

```
score = complexity + risk + ambiguity           (low = 1, medium = 2, high = 3)
      + additions from the project              (each +1 by default)
          · the codebase is large
          · test maturity is low
          · the task's scope touches critical paths
          · the task's scope touches legacy paths
```

The signals come from the task (the researcher); the additions come from the project's
`profile.json`. That is why the same task can score differently in the backend and the
frontend repository.

## The tiers (default policy)

| Tier | Score | Plan | Implement | Verify | Launch |
|---|---|---|---|---|---|
| T0 mechanical | `kind: mechanical` | sonnet / low | haiku / medium | sonnet / medium | `--model haiku --effort medium` |
| T1 routine | ≤ 4 | sonnet / medium | sonnet / medium | sonnet / medium | `--model sonnet --effort medium` |
| T2 standard | 5–6 | opus / high | sonnet / high | sonnet / high | `--model opusplan --effort high` |
| T3 critical | 7–8 | opus / xhigh | opus / high | opus / high | `--model opus --effort high` |
| T4 high risk | ≥ 9 | opus / xhigh | opus / high + advisor | opus / xhigh | `--model opus --effort high --advisor opus` |

Effort levels, briefly:

| Level | For |
|---|---|
| `low` | Quick, light work |
| `medium` | Feature work with a clear scope; the default for Opus 5.5 and Sonnet 5.5 |
| `high` | Work where verification and edge cases matter |
| `xhigh` | Deeper thinking |
| `max` | The deepest, but prone to overthinking; never used by the default policy |

Two deliberate absences from the defaults: **`max`**, because it tends toward overthinking
and is better chosen explicitly, and **Fable**, because on some plans it is billed from
usage credit and that should be a decision rather than something that happens to you.
Both are available through an override.

## The researcher's control

Choose the signals like this:

| Signal | low | medium | high |
|---|---|---|---|
| `complexity` | One file or function, a known pattern | A few modules, new but clear logic | Many modules, a new architectural pattern, concurrency |
| `risk` | Cheap to get wrong, easy to revert | Limited customer impact | Money, security, data integrity, tenant isolation |
| `ambiguity` | Everything is settled | A few areas open to interpretation | Important decisions still open (close them before publishing) |

**Publishing with `ambiguity: high` is the largest single source of scope drift**, which is
why validation warns about it.

```json
{
  "routing": {
    "signals": { "complexity": "medium", "risk": "high", "ambiguity": "low" },
    "role_signals": { "frontend": { "complexity": "low", "risk": "low" } },
    "overrides": {
      "*": { "verify": { "model": "opus", "effort": "high" } },
      "backend": { "implement": { "advisor": "opus" } }
    }
  }
}
```

- **`role_signals`** changes the signals per role — here the frontend work is simple.
- **`kind: "mechanical"`** is for renames, translation files, boilerplate.
- **`overrides`** forces specific phases whatever the tier. `*` means every role.

Set the signals honestly. Understating risk routes a dangerous task to a weak model, and
nobody downstream will notice.

## The project's influence

`codebase_size`, `test_maturity`, `critical_paths` and `legacy_paths` in `profile.json`
raise the score. The same task in a repository whose `critical_paths` include `app/api/**`
and whose `test_maturity` is `low` becomes T3 rather than T2.

### Worked example from the shipped examples

Run it yourself:

```bash
cd examples/dev-backend  && wizrelay pull CU-86c1abcd && wizrelay route
cd ../dev-frontend       && wizrelay pull CU-86c1abcd && wizrelay route
```

**`examples/dev-backend`** — the package's signals are medium/high/low = 6. The profile adds
`test_maturity: low` and a `critical_paths` overlap. The example hub's policy weights those
at 2 each, so the score is 10: **T4-high-risk**. On the plugin's defaults, weighting them
at 1 each, it would be 8: **T3-critical**.

**`examples/dev-frontend`** — the package lowers the signals for the frontend role to
low/low/low = 3, and nothing in that profile adds a modifier: **T1-routine**.

Same task, same hub, two roles, two tiers. That is the whole reason routing is computed per
role rather than per task.

## What the developer does with it

Covered in [8. Developer: implement a task](08-developer-workflow.md). Beyond the launch
command, the plugin also sets its own effort per phase:

| Command / agent | Runs at |
|---|---|
| `/wizrelay:plan` | High effort |
| `/wizrelay:verify` | High effort |
| `/wizrelay:ask` | Medium effort |
| `/wizrelay:hub-new` | Very high effort |
| Helper agents | Their own declared models |

## Changing the team policy

Edit the thresholds (`max_score`), the phase models and the modifier weights (`modifiers`)
in the hub's `policies/routing-policy.json` and commit. Projects use the new policy on their
next `pull` or `sync`.

The weights are the lever to reach for first. A team with thin test coverage across the
board can raise `test_maturity_low` to 2 and move every under-tested task up a tier without
touching a single package.

A hub policy **replaces** the plugin default entirely rather than merging with it, so list
every tier. A partially overridden tier table is harder to reason about than a complete one.

## Cost and availability

- **Fable** is billed from usage credit on some plans. Choose it deliberately with an
  override if you want it.
- **Advisor** is experimental, spends extra tokens, and works only on the Anthropic API.
- **Enterprise limits:** if your organisation restricts models or effort
  ([13. Team and enterprise](13-team-and-enterprise.md)), Claude Code enforces those
  limits. If the suggested model is not permitted, Claude Code continues with a permitted
  one.

## Honest caveats

- **A skill's `model` applies to its own turn only.** Per-phase model selection is therefore
  advisory: it reaches you through the launch command and through subagent parameters, not
  by silently switching your session.
- **The ordering across model families is a project convention.** The documentation states
  that an advisor must be at least as strong as the main model and that Haiku cannot be one,
  but it publishes no total order across families. The order used here is
  haiku < sonnet < fable < opus, and it is conservative: an uncertain pairing is dropped
  rather than proposed.

## Next

[11. Scope protection](11-scope-protection.md).

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 9. The question and version loop](09-question-loop.md) | [Contents](README.md) | [11. Scope protection →](11-scope-protection.md) |
<!-- /nav:bottom -->
