"""PreToolUse on the file-editing tools: the only fail-closed hook.

Layer 2 of the scope protection. Layer 1 is the permission deny rules,
which are absolute but static; this layer knows which task is active and what its scope
says, so it can protect a path the deny rules cannot name in advance.

The decision order is the design:

1. a path outside the repository  -> no decision
2. a researcher file              -> deny, in every mode
3. a developer file or .wizrelay/ -> no decision
4. no active task, or mode `off`  -> no decision
5. no scope defined for the role  -> ask
6. an explicit `deny` match       -> deny, in every mode
7. an `allow` or incidental match -> no decision
8. anything else                  -> deny in `strict`, ask in `ask`

Step 2 sits above step 4 on purpose: with enforcement `off` the scope is not enforced, but
researcher files stay read-only, because an edited `acceptance.md` silently changes what
"done" means and the lock would then disagree with the hub (invariant I9).

"No decision" means an empty response, which leaves Claude Code's normal permission flow
untouched. Returning `allow` instead would *grant* permission the user never gave.

An internal error returns `ask`, and `hooks.json` sets `onFailure: "block"` so a crash or
a timeout blocks the edit. Every other hook in this plugin fails open; this one must not.
"""

from __future__ import annotations

from typing import Any, Optional

from .. import audit as audit_mod
from .. import config as config_mod
from .. import context as context_mod
from .. import globs, package, paths
from ..i18n import Translator
from ..i18n import load as load_translator
from . import common

_EVENT = "PreToolUse"


def _decision(decision: str, reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": _EVENT,
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }


def _package_relative(rel: str) -> Optional[str]:
    """For a path inside `.wizrelay/tasks/<folder>/`, the part after the folder."""
    prefix = f"{paths.CONFIG_DIR_NAME}/{paths.TASKS_DIR}/"
    if not rel.startswith(prefix):
        return None
    remainder = rel[len(prefix) :]
    parts = remainder.split("/", 1)
    if len(parts) < 2:
        return None
    return parts[1]


def run() -> int:
    event = common.read_event()
    if event is None:
        # A payload we could not parse yields no decision.
        return common.emit_nothing()

    try:
        return _run(event)
    except Exception as exc:
        common.debug(f"pre-edit failed: {exc}")
        t = load_translator("en")
        return common.emit(_decision("ask", t("hook.pre_edit_error")))


def _run(event: dict[str, Any]) -> int:
    ctx = paths.detect(common.cwd_of(event))
    if not ctx.is_dev or ctx.root is None:
        # The hub persona makes no edit decision in v1, and a directory
        # with no marker is silent (invariant I5).
        return common.emit_nothing()

    target = common.resolve_tool_path(event)
    if target is None:
        return common.emit_nothing()

    # Step 1. Outside the repository: not our business. This is also where a different
    # Windows drive and a UNC path land.
    rel = paths.rel_posix(ctx.root, target)
    if rel is None:
        return common.emit_nothing()

    state = context_mod.load_dev_state(ctx)
    t: Translator = load_translator(state.language)

    inside_package = _package_relative(rel)
    if inside_package is not None:
        kind = package.classify(inside_package)
        # Step 2. Researcher-owned and hub-private files, including `.lock.json`, are
        # read-only here whatever the enforcement mode says.
        if kind in (package.RESEARCHER, package.PRIVATE):
            return common.emit(
                _decision(
                    "deny",
                    t("hook.deny_researcher", file=inside_package, task_id=state.task_id or "-"),
                )
            )
        # Step 3. Developer-owned files inside the package are the developer's.
        return common.emit_nothing()

    # Step 3 (continued). The rest of `.wizrelay/` is configuration the developer owns.
    if rel == paths.CONFIG_DIR_NAME or rel.startswith(paths.CONFIG_DIR_NAME + "/"):
        return common.emit_nothing()

    # Step 4. Nothing to enforce against.
    if not state.has_task:
        return common.emit_nothing()
    if state.enforcement == "off":
        return common.emit_nothing()

    # Step 5. The task says nothing about this role, so ask rather than guess.
    if not state.scope_defined():
        return common.emit(
            _decision("ask", t("hook.ask_no_scope", role=state.role or "-", task_id=state.task_id))
        )

    scope = state.scope_for_role()

    # Step 6. An explicit deny wins in every mode.
    denied = globs.matching_pattern(rel, scope["deny"])
    if denied:
        return common.emit(
            _decision("deny", t("hook.deny_scope", file=rel, pattern=denied, task_id=state.task_id))
        )

    # Step 7. In scope, or an incidental path such as a lock file.
    if globs.match_any(rel, scope["allow"]):
        return common.emit_nothing()
    # The same list the audit uses, so the hook never allows an edit that `audit` would
    # then report, and never blocks one it would accept.
    incidental = (
        list(audit_mod.DEFAULT_INCIDENTAL)
        + list(audit_mod.SETUP_PATHS)
        + config_mod.paths_of(state.profile, "incidental_allow")
    )
    if globs.match_any(rel, incidental):
        return common.emit_nothing()

    # Step 8. Outside the scope.
    allow_preview = ", ".join(scope["allow"][:3]) or "-"
    if state.enforcement == "ask":
        return common.emit(
            _decision(
                "ask",
                t("hook.ask_out_of_scope", file=rel, task_id=state.task_id, allow=allow_preview),
            )
        )
    return common.emit(
        _decision(
            "deny",
            t("hook.deny_out_of_scope", file=rel, task_id=state.task_id, allow=allow_preview),
        )
    )
