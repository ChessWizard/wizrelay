"""UserPromptSubmit: one line of plain text, so the active task never drifts away.

Claude Code adds a successful handler's plain stdout to the conversation as context. One
short line on every prompt is what keeps the task identifier, version, role and scope in
the recent context of a long session, where a single session-start injection would have
scrolled far out of reach.

Hard-capped at 250 characters. It is on every prompt, so its cost is paid
every turn.
"""

from __future__ import annotations

import sys

from .. import context as context_mod
from .. import paths
from ..i18n import load as load_translator
from . import common


def run() -> int:
    event = common.read_event() or {}
    ctx = paths.detect(common.cwd_of(event))
    if not ctx.is_dev:
        return common.emit_nothing()
    try:
        state = context_mod.load_dev_state(ctx)
        t = load_translator(state.language)
        line = context_mod.prompt_anchor(state, t)
        if not line:
            return common.emit_nothing()
        sys.stdout.write(line + "\n")
        return 0
    except Exception as exc:
        common.debug(f"prompt anchor failed: {exc}")
        return common.emit_nothing()
