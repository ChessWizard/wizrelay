---
description: The package does answer the question, so `ask` must answer it and cite the file.
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
tags: [ask]
---

I am working on task CU-86c1abcd. The research package says this:

`decisions.md`

```
## D-001 Fail open when Redis is unavailable (v1, 2026-10-30)

- Question: What happens to a request when the counter store cannot be reached?
- Decision: Allow the request and log a warning.
- Rationale: A quota is a cost control, not a safety control, so an outage must not stop
  customer traffic.
```

The Redis connection times out while I am checking the quota. Should the send fail?
