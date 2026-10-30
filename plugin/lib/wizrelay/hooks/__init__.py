"""Hook handlers, one module per event.

Entry points, not logic. Each handler reads the event payload from stdin, asks the core
and service layers a question, and prints the JSON Claude Code expects. The rules that
decide the answer live in `globs`, `routing` and `audit`, so they are unit-testable
without a hook payload, and the handlers themselves are pinned by golden tests in
`tests/golden/`.

The error policy is not uniform, and the asymmetry is deliberate:

* **`PreToolUse` fails closed.** `onFailure: "block"` in `hooks.json` means a crashed or
  timed-out handler blocks the edit, and an internal error returns `ask`. A guard that
  fails open is not a guard.
* **Everything else fails open.** A session must never become unusable because of
  wizrelay. A broken `SessionStart` costs context; a broken `SessionStart` that aborted
  the session would cost the user their work.
"""

from __future__ import annotations

__all__ = ["common", "model_switch", "pre_edit", "prompt", "session_start", "stop"]
