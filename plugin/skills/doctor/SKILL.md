---
name: doctor
description: Check the wizrelay environment and configuration, and explain how to fix whatever is wrong.
disable-model-invocation: true
allowed-tools: Bash(wizrelay *)
---

Diagnose this installation. Change nothing without asking.

## Report

!`wizrelay doctor`

## Interpretation

Explain each line marked `x` or `!`, in the user's own terms, and give the fix.

The checks that matter most, and what they mean:

- **python** — `x` here means the hooks cannot run at all, so **scope protection is
  silently absent**. On Windows without a `python3` on PATH, the fix is to install Python
  3.9+ so that `python3` resolves, or to use Git Bash with Python available. Treat it as
  blocking, not cosmetic.
- **duplicate-plugin-name** — another installed plugin also uses the manifest name
  `wizrelay`. Only one of them registers hooks, so protection may be inactive. The fix is
  to uninstall the duplicate. If the check could not run, say so rather than implying the
  installation is clean.
- **role** — a `{{placeholder}}` means `init` was never completed; routing and scope
  cannot work without a real role.
- **hub** — not reachable means `pull` and `sync` will fail. Check `hub.repo`, or set
  `hub.path` in `.wizrelay/config.local.json` for a local working copy.
- **integrity** — a researcher file no longer matches what was published. `/wizrelay:sync`
  restores it.
- **lock-migration** — an old schema. `wizrelay migrate` brings it forward.
- **prototype** — a `.ai/` directory is present; `wizrelay migrate --from-prototype`
  converts it.

## Confirming that protection is live

`doctor` reports configuration. To confirm the hooks are actually running in **this**
session, run `/wizrelay:status`: if its output carries a `WIZRELAY_NO_GUARD` warning, the
hooks did not run here even though the configuration is correct.

Answer in the language set in `.wizrelay/config.json`.
