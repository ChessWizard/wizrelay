"""PreModelSwitch: ask before dropping below the model the task was routed to.

Routing exists so that a risky task runs on a capable model. A mid-session
switch to a weaker model silently undoes that, and the person doing it usually has a good
reason — so this asks rather than denies.

Two constraints shape the implementation:

* **A timeout blocks the switch**. A slow handler
  would strand the user, so this one avoids `load_dev_state`: no git subprocess, no
  package parsing. It reads the pointer file and the lock's stored routing decision, which
  is two small file reads.
* **An unknown model makes no decision.** `default`, `inherit` and an unrecognised
  identifier return nothing, and `opusplan` counts as Sonnet,
  because Sonnet is the model that executes under that alias.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .. import lock, paths, routing
from ..i18n import load as load_translator
from . import common

_EVENT = "PreModelSwitch"


def _implement_model(root: Path) -> Optional[str]:
    """Read the implement-phase model from the active package's lock file.

    Deliberately pointer-only: resolving the active task from the branch name needs a git
    subprocess, and this handler's latency budget does not allow one.
    """
    pointer = root / paths.CONFIG_DIR_NAME / paths.ACTIVE_TASK_FILE
    try:
        folder = pointer.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not folder:
        return None

    document = lock.load(
        root / paths.CONFIG_DIR_NAME / paths.TASKS_DIR / folder / lock.LOCK_FILENAME
    )
    if not document:
        return None
    phases = (document.get("routing") or {}).get("phases") or {}
    implement = phases.get("implement") if isinstance(phases, dict) else None
    if isinstance(implement, dict):
        model = implement.get("model")
        return str(model) if model else None
    return None


def run() -> int:
    event = common.read_event()
    if event is None:
        return common.emit_nothing()

    ctx = paths.detect(common.cwd_of(event))
    if not ctx.is_dev or ctx.root is None:
        return common.emit_nothing()

    try:
        to_model = str(event.get("to_model") or "")
        from_model = str(event.get("from_model") or "")
        target_rank = routing.model_rank(to_model)
        if target_rank is None:
            # `default`, `inherit` or something unrecognised: no decision.
            return common.emit_nothing()

        wanted = _implement_model(ctx.root)
        wanted_rank = routing.model_rank(wanted)

        # Two reasons to ask, both conservative:
        #  - the target is weaker than the task was routed to
        #  - or, with no routing on record, the target is simply weaker than the current
        #    model
        below_tier = wanted_rank is not None and target_rank < wanted_rank
        downgrade = wanted_rank is None and routing.is_downgrade(from_model, to_model)
        if not (below_tier or downgrade):
            return common.emit_nothing()

        t = load_translator("en")
        config_path = ctx.root / paths.CONFIG_DIR_NAME / paths.DEV_CONFIG
        try:
            language = str(
                (json.loads(config_path.read_text(encoding="utf-8")) or {}).get("language") or "en"
            )
            t = load_translator(language)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            pass

        reason = (
            t("hook.switch_below_tier", to_model=to_model, wanted=wanted or "-")
            if below_tier
            else t("hook.switch_downgrade", from_model=from_model or "-", to_model=to_model)
        )
        payload: dict[str, Any] = {
            "hookSpecificOutput": {
                "hookEventName": _EVENT,
                "permissionDecision": "ask",
                "permissionDecisionReason": reason,
            }
        }
        return common.emit(payload)
    except Exception as exc:
        common.debug(f"model-switch failed: {exc}")
        return common.emit_nothing()
