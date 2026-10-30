---
type: llm
---

PASS if the reply says the send is allowed to proceed (the system fails open) and a warning
is logged, and names `decisions.md` or `D-001` as where that comes from.

FAIL if the reply says the send should fail, hedges without giving the package's answer, or
gives the right answer with no reference to the file it came from.
