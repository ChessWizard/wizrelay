"""Assembling state, and the three texts the plugin injects.

Three texts, three audiences:

* **session-start context** — facts for the model at the start of a session and after every
  compaction. Written as statements, never as imperatives: a hook is not the place to
  issue instructions, and a model that re-reads a command every turn starts to ignore it.
* **the prompt anchor** — one short line on every user prompt, so the active task survives
  a long conversation. Hard-capped at 250 characters.
* **brief** — what a skill injects through `!` when it runs. Always exits 0, because a
  non-zero exit from an injected command aborts the whole skill invocation
 .

It also owns the **heartbeat** (invariant I13). `SessionStart` records that it ran; `brief`
checks for that record. When a repository has `.wizrelay/` but this session has no
heartbeat, the hooks are not running — another plugin with the same manifest name took the
registration (R16), hooks are disabled, or the folder was never trusted. Without the
heartbeat that failure is silent, and silent loss of scope protection is the worst outcome
this project has.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Optional

from . import audit as audit_mod
from . import config as config_mod
from . import gitcmd, hubrepo, lock, package, paths, routing, schemas, textformats
from .i18n import Translator

__all__ = [
    "MAX_ANCHOR_CHARS",
    "MAX_CONTEXT_CHARS",
    "SENTINEL_ERROR",
    "SENTINEL_NO_ACTIVE_TASK",
    "SENTINEL_NO_INIT",
    "DevState",
    "brief",
    "heartbeat_prune",
    "heartbeat_seen",
    "heartbeat_write",
    "hub_context",
    "load_dev_state",
    "prompt_anchor",
    "session_start_context",
    "status_text",
]

#: Hook context is capped at 8000 characters, below the platform's own limit, so
#: there is room for the truncation note and no risk of a silent cut.
MAX_CONTEXT_CHARS = 8000
MAX_ANCHOR_CHARS = 250

#: Sentinels. A skill reads the first line of `brief` and branches on these
#: rather than parsing prose, which keeps the skill text short and language-independent.
SENTINEL_NO_INIT = "NO_INIT"
SENTINEL_NO_ACTIVE_TASK = "NO_ACTIVE_TASK"
SENTINEL_ERROR = "WIZRELAY_ERROR"
SENTINEL_NO_GUARD = "WIZRELAY_NO_GUARD"

_HEARTBEAT_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


# --------------------------------------------------------------------------------------
# Heartbeat (invariant I13)
# --------------------------------------------------------------------------------------


def _heartbeat_file(session_id: str) -> Optional[Path]:
    safe = "".join(ch for ch in session_id if ch.isalnum() or ch in "-_")[:128]
    if not safe:
        return None
    return paths.heartbeat_dir() / safe


def heartbeat_write(session_id: str) -> None:
    """Record that `SessionStart` ran for this session. Never raises."""
    path = _heartbeat_file(session_id)
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(int(time.time())), encoding="utf-8")
    except OSError:  # pragma: no cover - read-only data directory
        pass


def heartbeat_seen(session_id: str) -> bool:
    """Whether `SessionStart` ran for this session."""
    path = _heartbeat_file(session_id)
    return bool(path and path.is_file())


def heartbeat_prune(now: Optional[float] = None) -> int:
    """Delete heartbeats older than seven days. Returns how many were removed."""
    directory = paths.heartbeat_dir()
    if not directory.is_dir():
        return 0
    cutoff = (now or time.time()) - _HEARTBEAT_MAX_AGE_SECONDS
    removed = 0
    try:
        entries = list(directory.iterdir())
    except OSError:  # pragma: no cover
        return 0
    for entry in entries:
        try:
            if entry.is_file() and entry.stat().st_mtime < cutoff:
                entry.unlink()
                removed += 1
        except OSError:  # pragma: no cover
            continue
    return removed


# --------------------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------------------


def _read_json(path: Path) -> Optional[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


class DevState:
    """Everything a developer-side command or hook needs, loaded once."""

    __slots__ = (
        "active_source",
        "config",
        "ctx",
        "hub",
        "lock_document",
        "package_dir",
        "policy",
        "profile",
        "role",
        "routing",
        "task",
        "warnings",
    )

    def __init__(self, ctx: paths.Context) -> None:
        self.ctx = ctx
        self.config: dict[str, Any] = {}
        self.profile: dict[str, Any] = {}
        self.task: Optional[dict[str, Any]] = None
        self.package_dir: Optional[Path] = None
        self.lock_document: Optional[dict[str, Any]] = None
        self.role: Optional[str] = None
        self.routing: Optional[routing.RoutingDecision] = None
        self.hub: Optional[hubrepo.HubHandle] = None
        self.policy: Optional[dict[str, Any]] = None
        self.active_source = "none"
        self.warnings: list[str] = []

    @property
    def initialised(self) -> bool:
        return self.ctx.is_dev

    @property
    def has_task(self) -> bool:
        return self.task is not None

    @property
    def enforcement(self) -> str:
        return str((self.task or {}).get("enforcement") or "strict")

    @property
    def task_id(self) -> str:
        return str((self.task or {}).get("id") or "")

    @property
    def version(self) -> int:
        value = (self.task or {}).get("version")
        return value if isinstance(value, int) else 0

    @property
    def title(self) -> str:
        return str((self.task or {}).get("title") or "")

    @property
    def language(self) -> str:
        return str(self.config.get("language") or "en")

    def scope_for_role(self) -> dict[str, list[str]]:
        scope = (self.task or {}).get("scope") or {}
        entry = scope.get(self.role) if self.role and isinstance(scope, Mapping) else None
        if not isinstance(entry, Mapping):
            return {"allow": [], "deny": []}
        return {
            "allow": [p for p in (entry.get("allow") or []) if isinstance(p, str)],
            "deny": [p for p in (entry.get("deny") or []) if isinstance(p, str)],
        }

    def scope_defined(self) -> bool:
        scope = (self.task or {}).get("scope") or {}
        return bool(self.role and isinstance(scope, Mapping) and self.role in scope)

    def read_package_text(self, name: str) -> str:
        if self.package_dir is None:
            return ""
        try:
            return (self.package_dir / name).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ""


def default_policy() -> dict[str, Any]:
    """Load the plugin's own routing policy (appendix C)."""
    here = Path(__file__).resolve()
    for candidate in (
        here.parent.parent.parent / "config" / "routing-policy.json",
        here.parent / "config" / "routing-policy.json",
    ):
        data = _read_json(candidate)
        if data:
            return data
    # A missing policy file must not break routing; this mirrors T2 from appendix C.
    return {
        "schema_version": 1,
        "modifiers": {},
        "tiers": [
            {
                "name": "T2-standard",
                "max_score": 99,
                "phases": {
                    "plan": {"model": "opus", "effort": "high"},
                    "implement": {"model": "sonnet", "effort": "high"},
                    "verify": {"model": "sonnet", "effort": "high"},
                    "ask": {"model": "sonnet", "effort": "low"},
                },
            }
        ],
    }


def load_dev_state(
    ctx: paths.Context,
    *,
    allow_network: bool = False,
    allow_clone: bool = False,
    resolve_hub: bool = False,
) -> DevState:
    """Load configuration, profile, the active package, the lock and the routing decision.

    Nothing here raises on bad input: a malformed file becomes a warning and the state
    degrades. Hooks run this, and everything except edit protection has to fail
    open.
    """
    state = DevState(ctx)
    if not ctx.is_dev or ctx.root is None:
        return state

    config_dir = ctx.root / paths.CONFIG_DIR_NAME
    shared = _read_json(config_dir / paths.DEV_CONFIG) or {}
    local = _read_json(config_dir / paths.DEV_LOCAL_CONFIG)
    state.config = config_mod.layer_config(shared=shared, local=local)

    for label, document in (("config.json", shared), ("config.local.json", local or {})):
        if not document:
            continue
        issues = schemas.validate(config_mod.strip_comments(document), "config")
        for issue in issues:
            state.warnings.append(f"{label}: {issue}")
        for key in config_mod.unknown_keys(document):
            state.warnings.append(f"{label}: unknown key {key!r} is ignored")

    profile = _read_json(config_dir / paths.PROFILE_FILE)
    if profile:
        state.profile = config_mod.strip_comments(profile)
        for issue in schemas.validate(state.profile, "profile"):
            state.warnings.append(f"profile.json: {issue}")

    state.role = str(state.config.get("role") or "") or None

    tasks_dir = config_dir / paths.TASKS_DIR
    branch = gitcmd.current_branch(ctx.root)
    package_dir, source = package.resolve_active(
        tasks_dir, pointer=config_dir / paths.ACTIVE_TASK_FILE, branch=branch
    )
    state.active_source = source
    state.package_dir = package_dir

    if resolve_hub:
        try:
            state.hub = hubrepo.resolve(
                state.config, allow_network=allow_network, allow_clone=allow_clone
            )
        except Exception as exc:
            state.warnings.append(f"hub: {exc}")

    if package_dir is None:
        return state

    task = _read_json(package_dir / package.TASK_FILE)
    if task is None:
        state.warnings.append(f"{package_dir.name}/task.json could not be read")
        return state
    state.task = task
    for issue in schemas.validate(task, "task"):
        state.warnings.append(f"task.json: {issue}")

    state.lock_document = lock.load(package_dir / lock.LOCK_FILENAME)

    # The team policy is found without resolving the hub, so every surface that shows a
    # tier — `route`, `status`, `brief`, the session-start context — agrees with what
    # `pull` recorded in the lock.
    policy = (
        hubrepo.read_policy(state.hub.path if state.hub else None)
        or hubrepo.local_policy(state.config)
        or default_policy()
    )
    state.policy = policy
    try:
        state.routing = routing.compute(
            task=task, profile=state.profile, policy=policy, role=state.role
        )
    except Exception as exc:
        state.warnings.append(f"routing: {exc}")

    if state.role and state.role not in (task.get("roles") or []):
        state.warnings.append(
            f"role {state.role!r} is not one of the task's roles "
            f"({', '.join(str(r) for r in task.get('roles') or [])})"
        )

    return state


# --------------------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------------------


def _truncate(text: str, limit: int, t: Translator) -> str:
    if len(text) <= limit:
        return text
    note = "\n\n" + t("context.truncated", limit=limit)
    keep = max(0, limit - len(note))
    # Cut at a line boundary so the context never ends mid-sentence.
    cut = text[:keep]
    boundary = cut.rfind("\n")
    if boundary > keep // 2:
        cut = cut[:boundary]
    return cut + note


def _scope_lines(state: DevState, t: Translator) -> list[str]:
    scope = state.scope_for_role()
    lines: list[str] = []
    if scope["allow"]:
        lines.append(t("context.allow", patterns=", ".join(f"`{p}`" for p in scope["allow"])))
    if scope["deny"]:
        lines.append(t("context.deny", patterns=", ".join(f"`{p}`" for p in scope["deny"])))
    if not scope["allow"] and not scope["deny"]:
        lines.append(t("context.scope_missing", role=state.role or "-"))
    return lines


def _routing_line(state: DevState, t: Translator) -> Optional[str]:
    if state.routing is None:
        return None
    implement = state.routing.phases.get("implement")
    if implement is None:
        return None
    return t(
        "context.routing",
        tier=state.routing.tier,
        score=state.routing.score,
        model=implement.model,
        effort=implement.effort,
    )


def _ac_lines(state: DevState, t: Translator, limit: int = 12) -> list[str]:
    text = state.read_package_text("acceptance.md")
    if not text:
        return []
    criteria = textformats.acs_for_role(textformats.parse_acceptance(text), state.role)
    if not criteria:
        return []
    lines = [t("context.acceptance", count=len(criteria))]
    for criterion in criteria[:limit]:
        lines.append(f"- {criterion.identifier}: {criterion.title}")
    if len(criteria) > limit:
        lines.append(t("audit.more", count=len(criteria) - limit))
    return lines


def _open_questions(state: DevState) -> int:
    text = state.read_package_text("questions.md")
    if not text:
        return 0
    return sum(1 for question in textformats.parse_questions(text) if question.is_open)


def session_start_context(state: DevState, t: Translator, *, source: str = "startup") -> str:
    """Build the `additionalContext` for `SessionStart`.

    Phrased as facts. The one directive-shaped line is the protocol pointer, which names a
    file rather than telling the model what to do.
    """
    if not state.initialised:
        return ""

    lines: list[str] = [t("context.header")]

    if not state.has_task:
        lines.append(t("context.no_active_task"))
        if state.role:
            lines.append(t("context.role_only", role=state.role))
        return _truncate("\n".join(lines) + "\n", MAX_CONTEXT_CHARS, t)

    lines.append(
        t(
            "context.task",
            task_id=state.task_id,
            title=state.title,
            version=state.version,
            role=state.role or "-",
            enforcement=state.enforcement,
        )
    )

    researcher = package.researcher_files(state.package_dir) if state.package_dir else []
    if researcher:
        lines.append(t("context.files", files=", ".join(f"`{f}`" for f in researcher)))

    lines.extend(_scope_lines(state, t))

    routing_line = _routing_line(state, t)
    if routing_line:
        lines.append(routing_line)

    ac_lines = _ac_lines(state, t)
    if ac_lines:
        lines.append("")
        lines.extend(ac_lines)

    plan_text = state.read_package_text("plan.md")
    if plan_text:
        progress = textformats.parse_plan_progress(plan_text)
        if progress.total:
            lines.append("")
            lines.append(
                t("context.plan", done=progress.done, total=progress.total)
                + (
                    f" {t('context.plan_next', step=progress.next_step)}"
                    if progress.next_step
                    else ""
                )
            )

    open_questions = _open_questions(state)
    if open_questions:
        lines.append(t("context.open_questions", count=open_questions))

    lines.append("")
    lines.append(t("context.protocol"))

    return _truncate("\n".join(lines) + "\n", MAX_CONTEXT_CHARS, t)


def session_messages(
    state: DevState, t: Translator, *, session_model: Optional[str] = None
) -> list[str]:
    """Warnings for `systemMessage`: a stale version, an integrity problem, a weak model."""
    messages: list[str] = []
    if not state.has_task or state.package_dir is None:
        return messages

    locked = state.lock_document or {}
    locked_version = locked.get("version")
    if isinstance(locked_version, int) and locked_version < state.version:
        messages.append(
            t(
                "warn.stale_version",
                task_id=state.task_id,
                locked=locked_version,
                current=state.version,
            )
        )

    if locked:
        report = lock.verify(
            state.package_dir, locked, present=package.researcher_files(state.package_dir)
        )
        if not report.clean:
            messages.append(
                t(
                    "warn.integrity",
                    changed=len(report.changed),
                    missing=len(report.missing),
                    unlocked=len(report.unlocked),
                )
            )

    if state.routing and session_model:
        if routing.below_implement_tier(session_model, state.routing.phases):
            messages.append(t("warn.model_below_tier", launch=state.routing.launch))

    return messages


def prompt_anchor(state: DevState, t: Translator) -> str:
    """One line, at most 250 characters, or empty when there is nothing to anchor."""
    if not state.has_task:
        return ""
    if not state.config.get("prompt_anchor", True):
        return ""
    text = t(
        "anchor.line",
        task_id=state.task_id,
        version=state.version,
        role=state.role or "-",
        enforcement=state.enforcement,
        questions=_open_questions(state),
    )
    return text[:MAX_ANCHOR_CHARS]


def brief(
    state: DevState,
    t: Translator,
    *,
    phase: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    """Build the text a skill injects. Always returns something; the caller always exits 0.

    The first line is either a sentinel or the guard warning, so a skill can branch on it
    without parsing prose.
    """
    prefix: list[str] = []

    # Invariant I13: a connected repository whose session has no heartbeat is a session
    # whose hooks did not run.
    if state.initialised and session_id and not heartbeat_seen(session_id):
        prefix.append(f"{SENTINEL_NO_GUARD} {t('guard.inactive')}")
        prefix.append(t("guard.causes"))
        prefix.append("")

    if not state.initialised:
        return f"{SENTINEL_NO_INIT} {t('brief.no_init')}\n"

    if not state.has_task:
        body = f"{SENTINEL_NO_ACTIVE_TASK} {t('brief.no_active_task')}\n"
        return "\n".join(prefix) + body if prefix else body

    lines = list(prefix)
    lines.append(session_start_context(state, t).rstrip("\n"))

    if phase and state.routing:
        setting = state.routing.phases.get(phase)
        if setting:
            lines.append("")
            lines.append(
                t(
                    "brief.phase",
                    phase=phase,
                    model=setting.model,
                    effort=setting.effort,
                )
            )

    commands = config_mod.commands(state.profile)
    if commands:
        lines.append("")
        lines.append(t("brief.commands"))
        for name in sorted(commands):
            lines.append(f"- {name}: `{commands[name]}`")

    for warning in state.warnings[:5]:
        lines.append("")
        lines.append(f"> {warning}")

    return _truncate("\n".join(lines) + "\n", MAX_CONTEXT_CHARS, t)


def status_text(state: DevState, t: Translator) -> str:
    """The human-readable report `/wizrelay:status` and `wizrelay status` print."""
    lines: list[str] = []
    if not state.initialised:
        return f"{t('status.not_initialised')}\n"

    lines.append(t("status.header", root=str(state.ctx.root)))
    lines.append(t("status.role", role=state.role or "-"))
    hub = state.config.get("hub") or {}
    lines.append(
        t(
            "status.hub",
            hub=str(hub.get("path") or hub.get("repo") or "-"),
            branch=str(hub.get("branch") or "-"),
        )
    )

    if not state.has_task:
        lines.append("")
        lines.append(t("status.no_active_task"))
        return "\n".join(lines) + "\n"

    lines.append("")
    lines.append(
        t(
            "status.task",
            task_id=state.task_id,
            title=state.title,
            version=state.version,
            status=str((state.task or {}).get("status") or "-"),
        )
    )
    lines.append(t("status.active_source", source=state.active_source))
    lines.extend(_scope_lines(state, t))

    if state.routing:
        lines.append("")
        lines.append(t("status.routing_header"))
        for phase in routing.PHASES:
            setting = state.routing.phases.get(phase)
            if setting:
                advisor = f" + advisor {setting.advisor}" if setting.advisor else ""
                lines.append(f"- {phase}: {setting.model} / {setting.effort}{advisor}")
        lines.append("")
        lines.append(t("status.launch", command=state.routing.launch))

    plan_text = state.read_package_text("plan.md")
    if plan_text:
        progress = textformats.parse_plan_progress(plan_text)
        if progress.total:
            lines.append("")
            lines.append(t("context.plan", done=progress.done, total=progress.total))

    open_questions = _open_questions(state)
    if open_questions:
        lines.append(t("context.open_questions", count=open_questions))

    messages = session_messages(state, t)
    for message in messages:
        lines.append("")
        lines.append(f"! {message}")

    for warning in state.warnings:
        lines.append("")
        lines.append(f"> {warning}")

    return "\n".join(lines) + "\n"


def hub_context(ctx: paths.Context, t: Translator) -> str:
    """Session-start context for the hub persona: a package inventory (appendix B4)."""
    if not ctx.is_hub or ctx.root is None:
        return ""
    marker = hubrepo.read_marker(ctx.root)
    packages = package.list_packages(ctx.root / paths.TASKS_DIR)

    lines = [t("hub.header", name=str(marker.get("name") or ctx.root.name))]
    if not packages:
        lines.append(t("hub.empty"))
        return "\n".join(lines) + "\n"

    drafts: list[str] = []
    published: list[str] = []
    for directory in packages:
        task = _read_json(directory / package.TASK_FILE) or {}
        label = (
            f"{task.get('id') or directory.name} v{task.get('version', 0)} — "
            f"{task.get('title') or directory.name}"
        )
        if str(task.get("status") or "draft") == "published":
            published.append(label)
        else:
            drafts.append(label)

    lines.append(t("hub.counts", published=len(published), draft=len(drafts)))
    for label in published[:10]:
        lines.append(f"- {label}")
    for label in drafts[:10]:
        lines.append(f"- [draft] {label}")
    lines.append("")
    lines.append(t("hub.protocol"))
    return _truncate("\n".join(lines) + "\n", MAX_CONTEXT_CHARS, t)


def audit_for_state(state: DevState, *, base: Optional[str] = None) -> audit_mod.AuditReport:
    """Run the audit for the loaded state, so hooks and the CLI share one call path."""
    if state.ctx.root is None:
        return audit_mod.AuditReport()
    return audit_mod.audit(
        state.ctx.root,
        task=state.task,
        role=state.role,
        profile=state.profile,
        base=base,
        package_dir=state.package_dir,
        lock_document=state.lock_document,
    )


def session_env_model() -> Optional[str]:
    """The session's model, when Claude Code made it available to the hook process."""
    return os.environ.get("CLAUDE_MODEL") or None
