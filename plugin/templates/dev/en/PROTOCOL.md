# wizrelay protocol

Imported into this repository's `CLAUDE.md`. It applies whenever a task package is active.

## 1. Ownership

Researcher files are read-only here: `task.json`, `research.md`, `scope.md`,
`acceptance.md`, `decisions.md`, `contracts.md`, `roles/*.md`, and `.lock.json`.
Developer files are yours: `plan.md`, `questions.md`, `verification.md`, `notes/`.
To change a researcher file, ask through `/wizrelay:ask`; the answer arrives as a new
package version.

## 2. Precedence when sources disagree

`decisions.md` (the newest decision) > `task.json` + `scope.md` (scope) >
`contracts.md` (interfaces) > `acceptance.md` (behaviour) > `roles/<role>.md` >
`research.md` (rationale).

## 3. Scope

Change only what this role's `allow` patterns cover. A change the guard blocks is not to
be attempted another way — not through a shell command, not through a script. If the
scope is wrong, that is a question for the researcher, not an obstacle to work around.

## 4. Ambiguity

Ask `/wizrelay:ask` first; it answers from the package and cites the file it used. When
the package has no answer, the question goes to the researcher. Carry on with the work
that does not depend on the answer. Where an assumption is unavoidable, label it as an
assumption and say so in the reply.

## 5. Acceptance criteria

Every change belongs to an acceptance criterion. Plan steps and commit messages carry the
criterion's identifier.

## 6. Contracts

`contracts.md` is implemented exactly as written. A contract that needs to change is
raised as a question, never adjusted locally.

## 7. Out-of-scope ideas

Not implemented. Record them in `questions.md` under a "Proposal" heading so they reach
the researcher.

## 8. Verification

Run `/wizrelay:verify` before calling the work done. Tests and verification are the
developer's responsibility, not the researcher's.

## 9. Updates

When a session says a newer research version exists, run `/wizrelay:sync` before
continuing.

## 10. Commands

`/wizrelay:pull` `/wizrelay:plan` `/wizrelay:ask` `/wizrelay:verify` `/wizrelay:sync`
`/wizrelay:status` `/wizrelay:doctor`
