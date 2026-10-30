---
name: status
description: Show the active task, the scope, the routing table and any warnings for this repository.
disable-model-invocation: true
allowed-tools: Bash(wizrelay *)
---

Report where this repository stands. Read-only: change nothing.

## Status

!`wizrelay status`

## What to do with it

Relay the output, then add only what it does not already say:

- a line beginning `!` is a warning that needs action — a stale version needs
  `/wizrelay:sync`, an integrity problem needs `/wizrelay:sync`, a weak session model
  needs the launch command
- a line beginning `>` is a configuration warning — point at `/wizrelay:doctor`
- `No active task package is active` → `/wizrelay:pull <reference>`
- open questions → `/wizrelay:ask`, or the tracker if they are already posted

If the launch command names a stronger model than this session is running, show it and say
the session will work but was not routed for this task.

Answer in the language set in `.wizrelay/config.json`.
