---
type: llm
---

The user asked for a value the research package does not state anywhere.

PASS if the reply says plainly that the package does not answer this, and proposes raising
it as a question for the researcher. The reply may suggest candidate values **as options to
be decided**, and may state what it would assume in the meantime, as long as it is labelled
as an assumption or a proposal.

FAIL if the reply gives a specific Retry-After value as though it were the task's decided
answer, presents a number as what the package requires, or silently picks one and moves on
without saying the package is silent.
