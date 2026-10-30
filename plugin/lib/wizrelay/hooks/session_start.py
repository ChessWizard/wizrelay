"""SessionStart: re-inject the package summary, and prove the hooks are running.

Fires on `startup`, `resume`, `clear`, `compact` and `fork`. The `compact` source is the
one that makes goal G2 work: after a compaction the conversation has lost the package
summary, and this is what puts it back.

Three outputs:

* `hookSpecificOutput.additionalContext` — the facts about the active package
* `sessionTitle` — only under the three conditions below
* `systemMessage` — a stale version, an integrity problem, or a session model weaker than
  the implement phase wants

And one side effect: the heartbeat (invariant I13). Writing it here is what lets `brief`
detect a session whose hooks never ran.
"""

from __future__ import annotations

from typing import Any

from .. import context as context_mod
from .. import paths
from ..i18n import load as load_translator
from . import common

#: Sources where a session title may be set. A `clear` or `compact` keeps the title the
#: session already has.
_TITLE_SOURCES = frozenset({"startup", "resume", "fork"})


def run() -> int:
    event = common.read_event() or {}
    session_id = common.session_id_of(event)
    source = str(event.get("source") or "startup")

    # The heartbeat is recorded before anything can fail, so a later error still leaves
    # proof that the hooks ran.
    if session_id:
        context_mod.heartbeat_write(session_id)
    context_mod.heartbeat_prune()

    ctx = paths.detect(common.cwd_of(event))
    if ctx.is_silent:
        return common.emit_nothing()

    try:
        if ctx.is_hub:
            t = load_translator("en")
            marker_language = None
            from .. import hubrepo

            marker = hubrepo.read_marker(ctx.root) if ctx.root else {}
            marker_language = str(marker.get("language") or "en")
            t = load_translator(marker_language)
            text = context_mod.hub_context(ctx, t)
            if not text.strip():
                return common.emit_nothing()
            return common.emit(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": text,
                    }
                }
            )

        # The developer persona. Network is allowed here and nowhere else, within the TTL,
        # and never a clone.
        state = context_mod.load_dev_state(
            ctx, allow_network=True, allow_clone=False, resolve_hub=True
        )
        t = load_translator(state.language)
        text = context_mod.session_start_context(state, t, source=source)

        payload: dict[str, Any] = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": text,
            }
        }

        messages = context_mod.session_messages(
            state, t, session_model=str(event.get("model") or "") or None
        )
        if messages:
            payload["systemMessage"] = "\n".join(messages)

        if (
            source in _TITLE_SOURCES
            and state.has_task
            and state.config.get("session_title", True)
            and not str(event.get("session_title") or "").strip()
        ):
            payload["sessionTitle"] = f"{state.task_id} {state.title}".strip()[:80]

        return common.emit(payload)
    except Exception as exc:
        common.debug(f"session-start failed: {exc}")
        return common.emit_nothing()
