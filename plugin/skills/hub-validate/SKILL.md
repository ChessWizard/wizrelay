---
name: hub-validate
description: Validate a research package structurally and review it critically before publication.
disable-model-invocation: true
context: fork
agent: wizrelay:research-critic
background: false
effort: high
allowed-tools: Bash(wizrelay *)
argument-hint: "<task reference>"
---

Validate a package and review it as a critic, not as its author.

**Change nothing.** Report problems; the researcher fixes them. The only file written is
`.validation.md`, which `wizrelay hub validate` writes itself and which never leaves the
hub.

**Say which agent you are running as** at the top of your review. If it is not
`wizrelay:research-critic`, say so: the forked agent reference did not resolve and the
review ran with wider tool access than intended.

## 1. Structural validation

```
wizrelay hub validate $ARGUMENTS
```

Errors block publication; warnings do not. Relay them as they are — each carries a
`file:line`.

## 2. Critical review

The structural check cannot judge content. Read the package and answer these, each with a
file reference:

**Against the tracker.** Read the task with the tracker's MCP tools. Does the package
answer what was actually asked? Is anything in the task missing from the package? Is
anything in the package not asked for?

**Testability.** Can each acceptance criterion be verified by someone who did not write
it? A criterion whose verification is "it works correctly" cannot.

**Contradictions.** Do `scope.md` and `task.json` agree? Does `contracts.md` match what
`acceptance.md` expects? Does a decision in `decisions.md` contradict the approach in
`research.md`? The precedence order resolves these at read time, but a contradiction left
in the package costs every developer who reads it.

**Coverage.** Does every role have at least one criterion, a role file, and a scope? Does
every criterion belong to a role that exists?

**Evidence.** Is every claim about the current state cited? An uncited claim is the most
common defect in a research package, and the most expensive: a developer trusts it.

**Risk honesty.** Do the `signals` match what the package describes? A task that rewrites
an authentication path with `risk: low` will be routed to a weak model.

## 3. Verdict

Give one of:

- **Ready to publish** — no errors, and nothing in the review blocks it
- **Needs work** — list what, in priority order, each with its file reference
- **Blocked** — something cannot be resolved without a decision from outside

Then, if ready: `/wizrelay:hub-publish <task id>`.

Answer in the language set in `wizrelay-hub.json`.
