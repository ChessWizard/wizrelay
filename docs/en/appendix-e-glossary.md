<!-- nav:top -->
[Documentation](README.md) › **Appendix E — Glossary** &nbsp;·&nbsp; [Türkçe](../tr/appendix-e-glossary.md)
<!-- /nav:top -->

# Appendix E — Glossary

Every term this documentation uses as if you already knew it, and the pairs of terms
that are easy to confuse for each other.

| Term | What it means |
|---|---|
| **Plugin** | The tool that adds commands, checks and agents to Claude Code (`wizrelay`). Carries no team content |
| **Hub** | The private git repository holding a team's analysis packages. No code; nothing in it is ever executed. **One per team** |
| **Package** | One task's complete analysis: `tasks/<ID>-<slug>/` |
| **Researcher file** | Every file in a package that does not begin with a dot and is not one of the developer names. Read-only in a developer repository |
| **Developer file** | `plan.md`, `questions.md`, `verification.md`, `notes/`. Never arrive from the hub, never overwritten |
| **AC** | An acceptance criterion (`AC-1`, `AC-2` …). What "done" means, and what verification proves |
| **D-nnn** | A decision in `decisions.md`. Never deleted; superseded by a newer one |
| **Q-nnn** | A question in `questions.md`. Open until a decision answers it |
| **C-n** | A contract in `contracts.md`. The single place a field name or error code is defined |
| **Role** | What a repository is called inside a task (`backend`, `frontend` …). Free text; the hub decides the vocabulary |
| **Scope** | Per role, the files that may (`allow`) and may not (`deny`) be touched |
| **Enforcement mode** | `strict`, `ask` or `off`. Set per task by the researcher |
| **Signal** | A task's `complexity`, `risk` and `ambiguity`, each low/medium/high, plus an optional `kind: mechanical` |
| **Profile** | What a repository is like: its commands, size, test maturity, critical and legacy paths |
| **Policy** | The JSON that turns a score into a tier and a tier into a model and effort per phase |
| **Tier** | The level of the model and effort suggestion (T0–T4) |
| **Lock** (`.lock.json`) | The record of which version came from which hub commit, with a hash per file |
| **Hub identity** | A normalised, hashed name for one hub. What keeps two hubs on one machine apart |
| **Hook** | A check Claude Code runs automatically on a given event |
| **Heartbeat** | The record that a session's hooks ran. Without it, losing scope protection would be silent |
| **Persona** | Where you are: developer (`.wizrelay/config.json`), hub (`wizrelay-hub.json`), or neither — in which case the plugin is silent |
| **Incidental** | A path that may change without being a scope violation: a lock file, a generated client, the files `init` wrote |
| **MCP** | The protocol Claude uses to reach an external service such as ClickUp |
| **Advisor** | An experimental feature where Claude consults a stronger model at critical moments. Anthropic API only |
| **`opusplan`** | A model alias: Opus in plan mode, Sonnet for execution |
| **Invariant** | A property the implementation is not allowed to break. Thirteen of them, each with a test |

## Things that sound similar but are not

**Scope mode vs. scope.** The scope is *which files*; the mode is *what happens* when
something else is touched.

**`ask` the mode vs. `/wizrelay:ask` the command.** The mode prompts you before an
out-of-scope edit. The command asks the package a question, and the researcher if the
package has no answer.

**`NOT COVERED` vs. `FAIL`.** `FAIL` means the criterion was checked and the code is wrong.
`NOT COVERED` means nothing in the repository proves the criterion — usually because the
test does not exist yet.

**Validation vs. verification.** Validation is the researcher's gate on a package before
publishing. Verification is the developer's gate on the work before calling it done.

**Hub vs. tracker.** The tracker holds the task. The hub holds the analysis of the task.
They are different things and the hub does not replace the tracker.

**`doctor` vs. `status`.** `doctor` checks the configuration. `status` checks this session.
A configuration can be perfect while the hooks did not run here.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← Appendix D — Checklists](appendix-d-checklists.md) | [Contents](README.md) | &nbsp; |
<!-- /nav:bottom -->
