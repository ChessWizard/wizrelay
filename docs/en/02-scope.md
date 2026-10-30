<!-- nav:top -->
[Documentation](README.md) › **2. What it does and does not do** &nbsp;·&nbsp; [Türkçe](../tr/02-scope.md)
<!-- /nav:top -->

# What it does and does not do

The boundary of this tool: the goals it commits to, the things it deliberately leaves
alone, and the guarantees it can and cannot make.

## What it is for

wizrelay is for a team where **one person analyses and several people
implement**, and where each implementer works through an AI coding session.

It is worth setting up when you recognise at least two of these:

- A developer implemented something the analysis did not ask for, and nobody noticed until
  review.
- Two roles implemented two sides of one interface and they did not match.
- A developer hit an unanswered question, guessed, and the guess shipped.
- A risky change ran on a weak model because that is what the session happened to start on.
- The analysis was in a document, and halfway through a long session it was no longer in
  the conversation.

It is **not** worth setting up for a single developer working alone on a task they analysed
themselves. There is no handoff to protect.

## The goals, and how each is measured

| # | Goal | How you can tell it is working |
|---|---|---|
| G1 | One source of truth | Versioned packages live in the hub; developer repositories hold a hash-verified, read-only copy |
| G2 | Deterministic context | The package summary is re-injected at every session start **and after every compaction** |
| G3 | Scope protection | Five layers: permission rules, a hook, an end-of-turn audit, verification, CI |
| G4 | A question loop | A question the package cannot answer reaches the researcher and returns as a decision in a new version |
| G5 | Model and effort routing | Policy-driven, computed from the task's signals and the repository's profile |
| G6 | Verification on the developer's side | An independent verifier pairs every criterion with evidence; the report goes to the tracker |
| G7 | Usable anywhere | Tracker adapters, free-form roles, cross-platform, English and Turkish, CI integration |

## What it deliberately does not do

| Not this | Why |
|---|---|
| **Replace your tracker** | The tracker stays the place where work is tracked. The hub holds the *analysis*, not the task list |
| **Provide OS-level sandboxing** | The target is a guardrail against accidental drift, not a jail. Claude Code's own sandbox is the tool for OS-level enforcement |
| **Run a server or a SaaS component** | There is nothing to host. A hub is a git repository; everything else is local |
| **Make its own LLM API calls** | Everything runs through Claude Code, on your own account, with your own models |
| **Provide a GUI** | Commands in Claude Code, and a CLI |
| **Work in claude.ai chat or Cowork** | The target surface is Claude Code: the terminal, the IDE extensions and the desktop app's Code tab |

## What it guarantees, and what it does not

This distinction matters more than anything else on this page.

### It does guarantee

- A researcher file in a developer repository **cannot be edited** through Claude's file
  tools, or through the file commands Claude Code recognises in Bash (`sed`, `tee`, a `>`
  redirection). Not in any enforcement mode.
- A developer file — `plan.md`, `questions.md`, `verification.md`, `notes/` — is **never
  overwritten** by `pull` or `sync`.
- A dot-prefixed file in a hub package **never reaches** a developer repository.
- Only a `published` package can be pulled, unless someone passes an explicit flag.
- The lock file records which research version came from which hub commit, with a hash per
  file, so a modified copy is detectable.
- A directory with neither marker file gets **nothing**: no output, no file written, no
  network.

### It does not guarantee

- That a developer cannot disable the plugin, edit `.claude/settings.json`, or run Claude
  Code in a mode that skips permission prompts.
- That a Python or Node script the session writes and runs cannot touch any file it likes.
  Claude Code's deny rules cover its own file tools and the commands it recognises — not an
  arbitrary subprocess.
- That the analysis is *correct*. It guarantees that everybody is working from the same
  analysis, and that disagreeing with it is a visible act rather than a silent one.

The two layers that survive a developer working around the rest are the **CI gate** and
**managed settings**. A team that cares about this runs at least the CI gate.
[11. Scope protection](11-scope-protection.md) has the full layer-by-layer account.

## What it costs

Honest accounting, because a tool that adds context to every session is spending your
tokens:

| Cost | Size |
|---|---|
| Skill and agent descriptions the model sees | ≤ 1500 characters |
| Session-start context | ≤ 8000 characters, target ≤ 3000 |
| The per-prompt anchor | ≤ 250 characters |
| Hook latency, no network | under 300 ms p95 |
| Session start with a hub refresh | under 5 s; the network call times out at 4 s and is skipped silently |

The side-effecting skills set `disable-model-invocation: true`, so the model never sees
their descriptions at all — only `ask` is offered to it.

Against that: routing a routine task to Sonnet instead of Opus usually saves more than the
context costs.

## The limits you should know before committing

- **One role per repository** in v1. A monorepo with several roles either uses one role name
  with sub-directory globs, or packages written against that one role.
- **One active task per repository.** Switch with `wizrelay activate`, or by checking out a
  branch whose name carries the task identifier.
- **Windows is tier-1 under Git Bash with `python3` available.** A PowerShell-only
  environment with no `python3` gets no hooks, and `wizrelay doctor` reports that as an
  error rather than letting it look fine.
- **Jira, Linear and Azure DevOps are beta** in v1: identifier handling and URL building are
  tested, but reading and commenting depend on your own access.

## Next

[3. Prerequisites](03-prerequisites.md) lists what each person needs before anything is
installed.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 1. Overview](01-overview.md) | [Contents](README.md) | [3. Prerequisites →](03-prerequisites.md) |
<!-- /nav:bottom -->
