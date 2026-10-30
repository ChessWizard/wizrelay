# No tracker

For a team with no issue tracker, or a task that does not have one.

## Identifiers

Any name works: `quota-limits`, `2026-q1-migration`, `local-1`. It becomes the package
directory prefix, so keep it short and use only letters, digits, `.`, `_` and `-`.

## What changes

- **No comments are posted anywhere.** Questions stay in `questions.md`, and answers
  arrive as a new package version.
- **No deep links.** `hub comment` still produces the per-role acceptance list and the
  pull command, which you can paste into whatever the team does use.
- **Nothing is read from a tracker.** `/wizrelay:hub-new` takes the task from the user, so
  ask for the problem, the constraints and the acceptance expectation directly.

## The question loop without a tracker

The loop still works, it just needs a human handoff:

1. The developer's `/wizrelay:ask` writes `Q-<nnn>` into `questions.md`.
2. `questions.md` is a developer file, so it stays in the developer's repository. Tell the
   user to send the question to the researcher however the team communicates.
3. The researcher records the decision in `decisions.md` and publishes a new version.
4. The developer's next session reports a newer version and `/wizrelay:sync` brings it in.

The one thing to watch: without a tracker, nothing reminds the researcher that a question
is waiting. Say so when you write one.
