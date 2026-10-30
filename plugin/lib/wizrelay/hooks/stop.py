"""Stop: one end-of-turn summary of anything that drifted.

Layer 3 of the scope protection. `PreToolUse` catches an edit as it
happens, but not a file a shell command wrote, and not a researcher file a subprocess
changed. This hook looks at the git state once per turn and says what it sees.

It never returns `decision: "block"`. Blocking here would keep
Claude working in a loop it cannot escape — the violation has already happened, and the
person is the one who decides what to do about it. The message is for them.
"""

from __future__ import annotations

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
        if not state.has_task:
            return common.emit_nothing()

        t = load_translator(state.language)
        # No base ref: the end-of-turn check is about this turn's working tree, not the
        # whole branch. The branch is the pull request gate's job.
        report = context_mod.audit_for_state(state, base=None)
        if report.clean:
            return common.emit_nothing()

        lines: list[str] = [t("stop.header", task_id=state.task_id)]
        for path, pattern in report.forbidden[:10]:
            lines.append(t("stop.forbidden", file=path, pattern=pattern))
        for path in report.out_of_scope[:10]:
            lines.append(t("stop.out_of_scope", file=path))
        if report.integrity is not None and not report.integrity.clean:
            for path in report.integrity.changed[:10]:
                lines.append(t("stop.integrity_changed", file=path))
            for path in report.integrity.missing[:10]:
                lines.append(t("stop.integrity_missing", file=path))
        lines.append(t("stop.next"))

        return common.emit({"systemMessage": "\n".join(lines)})
    except Exception as exc:
        common.debug(f"stop hook failed: {exc}")
        return common.emit_nothing()
