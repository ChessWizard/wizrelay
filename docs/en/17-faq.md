<!-- nav:top -->
[Documentation](README.md) › **17. Frequently asked questions** &nbsp;·&nbsp; [Türkçe](../tr/17-faq.md)
<!-- /nav:top -->

# Frequently asked questions

The questions that come up in the first week.

## Does the plugin work in claude.ai chat?

No. It is for **Claude Code**: the terminal, the IDE extensions, and the desktop app's Code
tab. It is not installable on claude.ai or in Cowork either — the plugin ships a `bin/`
directory, which those surfaces refuse, and the hooks that do the enforcing do not exist
there.

## Do I need a separate hub for each project?

No. A hub is per **team**; every project repository connects to the same one. A single task
can span several repositories, which is the main reason it works that way.

## Can a developer see the analysis?

Yes — the whole package. They just cannot change it.

## Does the researcher have to use Claude?

No. The whole flow runs from the CLI, and a package can be written entirely by hand by
copying `templates/package/`. `hub validate` checks a hand-written package by exactly the
same rules.

## Can the hub live on GitLab or Azure Repos?

Yes. A hub is a plain git repository.

## What if we do not use a tracker?

Set `tracker: none`. It is a first-class option, not a degraded mode. Questions stay in
`questions.md`, answers arrive as a new package version, and a person carries the question
across. The one thing to watch is that nothing reminds the researcher a question is
waiting, so `ask` says so when it writes one.

## Should `.wizrelay/tasks/` be committed?

Yes. It is needed both for traceability and for the CI gate, which reads the pulled package
to know what the scope is.

## Can two developers work the same task in the same role?

Yes; both pull the same package. Splitting the work across branches and letting one person
own `plan.md` is the arrangement that causes least friction.

## Can a developer change the scope?

No. Only the researcher changes it, with a new version. That is the point: the scope is a
decision, and changing it is a visible act that reaches everyone on the task.

## Does it work offline?

It keeps working with an already-pulled package. `pull` and `sync` need access to the hub.

## Is there a file size limit in a package?

5 MB per file, 20 MB per package in total. A package is analysis, not an asset bundle.

## Why not just put the analysis in `CLAUDE.md`?

You can, and it helps. But `CLAUDE.md` is an instruction, and following an instruction is
probabilistic: a long session drifts, a compaction drops it, a plausible-looking
improvement happens anyway. A deny rule and a `PreToolUse` hook are not probabilistic.

The other half is versioning. `CLAUDE.md` has no way to say "this analysis is v2 and you
have v1", and that is the mechanism the question loop runs on.

## Does it slow a session down?

The budget is under 300 ms p95 per hook with no network, and tests enforce it. The
per-prompt anchor is capped at 250 characters and the session-start context at 8000, with a
3000 target.

The one operation that can touch the network is session start, inside a TTL, with a
4-second timeout, failing silently.

## Does the plugin cost tokens?

Some, and it is measured. Skill and agent descriptions the model sees total 1500 characters
or fewer — the side-effecting skills set `disable-model-invocation: true`, so the model
never sees their descriptions at all. The session-start context targets 3000 characters.

Routing is the other side of that ledger: a routine task running on Sonnet instead of Opus
usually saves more than the context costs.

## Why is `ask` the only skill the model can invoke on its own?

Because it is the only one with no side effects beyond a file the developer owns.
Everything else writes, publishes or posts, and those should happen because a person asked.

Its description is deliberately eager: the moment you are about to assume something about
the task is the moment to use it.

## What if `ask` gives me a wrong answer?

It is built to decline rather than guess: if the package does not answer the question, it
says so and offers to raise it. That behaviour has its own eval case, and the requirement
is that the invented-answer rate is zero.

If it answers at all, it cites the file. Check the citation — that is what it is for.

## Can I use this without Claude Code?

Partly. Every deterministic operation has a CLI equivalent — `wizrelay pull`, `audit`,
`hub validate`, `hub publish-prep` — so the CI gate and the scripted half work from a
terminal.

What needs Claude is the judgement: drafting a package from a tracker task, planning,
verifying, answering a question from the package. The skills are prompts, and a prompt
needs a model.

## Someone edited a researcher file anyway. Now what?

`sync` restores it from the hub and reports that it did. Until then, session start and
`audit` both report the integrity problem, because the lock records a hash per file.

If the change was needed, that is a question for the researcher.

## Why does `pull` not write any code?

Because a session that starts implementing while it is still reading the analysis is the
drift this project exists to prevent. `pull` briefs and stops. Planning in plan mode with
the scope in view is a different activity from implementing.

## What does `enforcement: off` leave?

Researcher files stay read-only; the scope is not enforced. It is for a task whose scope
genuinely cannot be pinned down in advance, and it is still much better than no package:
the analysis, the criteria and the decisions all still work.

## How do I know the protection is actually on?

`/wizrelay:doctor` checks the configuration. `/wizrelay:status` checks **this session**: if
its output opens with `WIZRELAY_NO_GUARD`, the hooks did not run here even though the
configuration is correct. Two different questions, and the second one is the one that has
bitten people.

## Why Python, and why standard library only?

Because a plugin is a directory Claude Code copies into a cache, and nothing runs
`pip install` for it. A single third-party import would break the plugin for anyone whose
Python does not happen to have that package. Python itself is there because `python3` is
already present almost everywhere Claude Code runs.

## Is any of this sent anywhere?

No. There is no telemetry, no server and no SaaS component. The only network access is
`git fetch` against your own hub, and tracker access through MCP servers you authorise
yourself.

## Next

[Appendix A — Command reference](appendix-a-commands.md).

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 16. Troubleshooting](16-troubleshooting.md) | [Contents](README.md) | [Appendix A — Command reference →](appendix-a-commands.md) |
<!-- /nav:bottom -->
