"""The `wizrelay` command line.

Every deterministic operation lives here rather than in a skill's prose (invariant I10).
A skill tells Claude *what* to do and delegates the mechanical part to this CLI, which
means the same behaviour is available in CI, from a terminal, and to anyone who does not
use Claude at all.

Exit code contract, enforced in one place — `main`:

===  =============================================================================
  0  success
  1  a violation or a validation failure: the work is wrong, the invocation was fine
  2  a user or configuration error: the invocation is wrong
  3  an unexpected internal error
===  =============================================================================

`brief` is the exception that proves the rule: it **always** exits 0. A skill injects it
with `` !`...` ``, and a non-zero exit there aborts the whole skill invocation before
Claude sees any of its content. A `brief` that
failed loudly would take the skill down with it, so it reports problems in its output and
still succeeds.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Callable, Optional

from . import (
    SCHEMA_VERSION,
    __version__,
    gitcmd,
    hubrepo,
    lock,
    package,
    paths,
    routing,
    schemas,
    templates,
    trackers,
)
from . import audit as audit_mod
from . import context as context_mod
from .errors import (
    EXIT_INTERNAL,
    EXIT_OK,
    EXIT_USER,
    EXIT_VIOLATION,
    UsageError,
    ValidationError,
    WizrelayError,
)
from .i18n import Translator
from .i18n import load as load_translator
from .textformats import fold

__all__ = ["main"]

PROG = "wizrelay"

#: Deny rules `init` writes into the project's `.claude/settings.json`.
#: Every rule is `Edit(...)`: a `Write(path)` rule matches nothing at all
#:. The single leading slash anchors the pattern at
#: the primary working directory, which is the repository root for project settings.
DENY_RULES = (
    "Edit(/.wizrelay/tasks/*/task.json)",
    "Edit(/.wizrelay/tasks/*/research.md)",
    "Edit(/.wizrelay/tasks/*/scope.md)",
    "Edit(/.wizrelay/tasks/*/acceptance.md)",
    "Edit(/.wizrelay/tasks/*/contracts.md)",
    "Edit(/.wizrelay/tasks/*/decisions.md)",
    "Edit(/.wizrelay/tasks/*/roles/**)",
    "Edit(/.wizrelay/tasks/*/.lock.json)",
)

GITIGNORE_ENTRIES = [
    f"{paths.CONFIG_DIR_NAME}/{paths.DEV_LOCAL_CONFIG}",
    f"{paths.CONFIG_DIR_NAME}/{paths.ACTIVE_TASK_FILE}",
]

MAX_DIFF_LINES = 250


# --------------------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------------------


def _now_iso() -> str:
    """UTC ISO-8601, as every timestamp this project writes has to be."""
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _today() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def _dump_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump_json(payload) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Optional[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _out(text: str) -> None:
    sys.stdout.write(text if text.endswith("\n") else text + "\n")


def _require_dev(ctx: paths.Context, t: Translator) -> Path:
    """Fail with the three-part message when the command needs a connected repository."""
    if not ctx.is_dev or ctx.root is None:
        raise UsageError(
            t("err.not_initialised"),
            reason=t("err.not_initialised_why"),
            remedy=t("err.not_initialised_fix"),
        )
    return ctx.root


def _require_hub_persona(ctx: paths.Context, t: Translator) -> Path:
    if not ctx.is_hub or ctx.root is None:
        raise UsageError(
            t("err.not_hub"),
            reason=t("err.not_hub_why"),
            remedy=t("err.not_hub_fix"),
        )
    return ctx.root


def _translator_for(config: Mapping[str, Any], override: Optional[str] = None) -> Translator:
    return load_translator(override or str(config.get("language") or "en"))


# --------------------------------------------------------------------------------------
# init
# --------------------------------------------------------------------------------------


def _merge_settings_deny(path: Path, rules: Sequence[str]) -> bool:
    """Add the deny rules to `.claude/settings.json` without disturbing anything else.

    A project's own settings are the user's; `init` only appends (invariant I7). A rule
    already present is left alone, so a second run reports no change.
    """
    document = _read_json(path) or {}
    permissions = document.get("permissions")
    if not isinstance(permissions, dict):
        permissions = {}
    deny = permissions.get("deny")
    if not isinstance(deny, list):
        deny = []

    missing = [rule for rule in rules if rule not in deny]
    if not missing:
        return False

    permissions["deny"] = deny + missing
    document["permissions"] = permissions
    _write_json(path, document)
    return True


def _merge_marketplace(path: Path, repo: str) -> bool:
    """Register the marketplace and enable the plugin for everyone in the repository.

    A known risk: this path may not prompt an install on every Claude Code
    version, so the documentation puts the manual `/plugin marketplace add` route first
    and this is the convenience, not the instruction.
    """
    document = _read_json(path) or {}
    changed = False

    marketplaces = document.get("extraKnownMarketplaces")
    if not isinstance(marketplaces, dict):
        marketplaces = {}
    if "wizrelay" not in marketplaces:
        marketplaces["wizrelay"] = {"source": {"source": "github", "repo": repo}}
        document["extraKnownMarketplaces"] = marketplaces
        changed = True

    enabled = document.get("enabledPlugins")
    if not isinstance(enabled, dict):
        enabled = {}
    key = "wizrelay@wizrelay"
    if key not in enabled:
        enabled[key] = True
        document["enabledPlugins"] = enabled
        changed = True

    if changed:
        _write_json(path, document)
    return changed


def _merge_mcp(path: Path, entry: Mapping[str, Any]) -> bool:
    """Add a verified tracker MCP server to the project's `.mcp.json`."""
    document = _read_json(path) or {}
    servers = document.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
    changed = False
    for name, value in entry.items():
        if name not in servers:
            servers[name] = value
            changed = True
    if changed:
        document["mcpServers"] = servers
        _write_json(path, document)
    return changed


def cmd_init(args: argparse.Namespace) -> int:
    root = paths.find_repo_root(Path.cwd())
    if root is None:
        t = load_translator(args.lang)
        raise UsageError(
            t("err.not_a_repo"),
            reason=t("err.not_a_repo_why"),
            remedy=t("err.not_a_repo_fix"),
        )

    config_dir = root / paths.CONFIG_DIR_NAME
    existing = _read_json(config_dir / paths.DEV_CONFIG) or {}

    language = args.lang or str(existing.get("language") or "en")
    t = load_translator(language)
    changes: list[str] = []

    # 1. The configuration. Written once; later runs never rewrite a user's choices.
    config_document: dict[str, Any] = dict(existing)
    if not existing:
        config_document = {
            "schema_version": SCHEMA_VERSION,
            "hub": {"branch": "main"},
            "role": args.role or "{{role}}",
            "tracker": {"type": args.tracker or "none"},
            "language": language,
            "base_ref": "origin/main",
            "prompt_anchor": True,
            "session_title": True,
            "fetch_ttl_minutes": 10,
            "researcher_mention": "",
        }
        if args.hub:
            config_document["hub"]["repo"] = args.hub
        if args.hub_path:
            config_document["hub"]["path"] = args.hub_path
        _write_json(config_dir / paths.DEV_CONFIG, config_document)
        changes.append(f"{paths.CONFIG_DIR_NAME}/{paths.DEV_CONFIG}")
    else:
        # On a re-run, only fill in values the user passed explicitly and that are absent.
        updated = dict(existing)
        hub_block = dict(updated.get("hub") or {})
        if args.role and not updated.get("role", "").startswith("{{"):
            pass
        elif args.role:
            updated["role"] = args.role
        if args.hub and not hub_block.get("repo"):
            hub_block["repo"] = args.hub
        if args.hub_path and not hub_block.get("path"):
            hub_block["path"] = args.hub_path
        if hub_block != (updated.get("hub") or {}):
            updated["hub"] = hub_block
        if args.tracker and not (updated.get("tracker") or {}).get("type"):
            updated["tracker"] = {"type": args.tracker}
        if updated != existing:
            _write_json(config_dir / paths.DEV_CONFIG, updated)
            changes.append(f"{paths.CONFIG_DIR_NAME}/{paths.DEV_CONFIG}")
        config_document = updated

    # 2. The profile. A draft the user completes; Claude fills it in during /wizrelay:init.
    if templates.write_if_absent(
        config_dir / paths.PROFILE_FILE, templates.dev_template(language, "profile.json")
    ):
        changes.append(f"{paths.CONFIG_DIR_NAME}/{paths.PROFILE_FILE}")

    # 3. The protocol. Plugin-owned, so it is refreshed on upgrade but only when it differs.
    if templates.write_if_changed(
        config_dir / paths.PROTOCOL_FILE, templates.dev_template(language, "PROTOCOL.md")
    ):
        changes.append(f"{paths.CONFIG_DIR_NAME}/{paths.PROTOCOL_FILE}")

    tasks_dir = config_dir / paths.TASKS_DIR
    if not tasks_dir.is_dir():
        tasks_dir.mkdir(parents=True, exist_ok=True)
        changes.append(f"{paths.CONFIG_DIR_NAME}/{paths.TASKS_DIR}/")

    # 4. CLAUDE.md import. Appended, never replaced (invariant I7).
    if templates.append_line_if_absent(
        root / "CLAUDE.md",
        f"@{paths.CONFIG_DIR_NAME}/{paths.PROTOCOL_FILE}",
        heading="## Task protocol",
    ):
        changes.append("CLAUDE.md")

    # 5. .gitignore for the personal and ephemeral files.
    if templates.merge_gitignore(root / ".gitignore", GITIGNORE_ENTRIES):
        changes.append(".gitignore")

    # 6. Deny rules: layer 1 of the scope protection.
    if _merge_settings_deny(root / ".claude" / "settings.json", DENY_RULES):
        changes.append(".claude/settings.json")

    # 7. Optional team-wide plugin enablement.
    if args.marketplace and _merge_marketplace(
        root / ".claude" / "settings.json", args.marketplace
    ):
        changes.append(".claude/settings.json (marketplace)")

    # 8. Optional tracker MCP, only when the endpoint is verified.
    tracker_type = str((config_document.get("tracker") or {}).get("type") or "none")
    mcp_notes: list[str] = []
    if tracker_type != "none":
        entry = trackers.mcp_server_config(tracker_type)
        if entry:
            if _merge_mcp(root / ".mcp.json", entry):
                changes.append(".mcp.json")
        else:
            note = trackers.mcp_note(tracker_type)
            if note:
                mcp_notes.append(note)

    if changes:
        _out(t("init.done", count=len(changes)))
        for item in sorted(set(changes)):
            _out(f"  + {item}")
    else:
        _out(t("init.no_changes"))

    for note in mcp_notes:
        _out("")
        _out(t("init.mcp_manual", tracker=trackers.display_name(tracker_type), note=note))

    placeholders = templates.find_placeholders(
        (config_dir / paths.DEV_CONFIG).read_text(encoding="utf-8")
    ) + templates.find_placeholders((config_dir / paths.PROFILE_FILE).read_text(encoding="utf-8"))
    if placeholders or str(config_document.get("role", "")).startswith("{{"):
        _out("")
        _out(t("init.next_steps"))
    return EXIT_OK


# --------------------------------------------------------------------------------------
# pull / sync
# --------------------------------------------------------------------------------------


def _reference_for(reference: str, tracker_type: str, config: Mapping[str, Any]) -> tuple:
    """Turn whatever the user typed into `(canonical_id, raw_ref)`.

    A tracker reference is normalised; a **package directory name** is not, because no
    tracker pattern matches `CU-86c1abcd-tenant-quota`. Appendix B2 #2 requires all three
    forms — the raw reference, the canonical identifier and the directory name — to find
    the same package, so a reference that no tracker recognises but that could be a
    directory name is passed through for the directory lookup to resolve.

    Anything that is neither keeps the specific tracker error, because "that is not a
    valid ClickUp reference" is far more useful for a typo than "no package found".
    """
    try:
        return trackers.normalize(reference, tracker_type, config=config)
    except UsageError:
        if trackers.is_safe_folder_name(reference):
            return "", reference
        raise


def _resolve_hub(state: context_mod.DevState, t: Translator) -> hubrepo.HubHandle:
    """Resolve the hub, turning an unusable one into a three-part error."""
    handle = hubrepo.resolve(state.config, allow_network=True, allow_clone=True)
    if not handle.available or handle.tasks_dir is None:
        raise UsageError(
            t("err.hub_unavailable"),
            reason="; ".join(handle.notes) or t("err.hub_unavailable_why"),
            remedy=t("err.hub_unavailable_fix"),
        )
    return handle


def _hub_package(
    state: context_mod.DevState,
    t: Translator,
    *,
    canonical_id: str = "",
    raw_ref: str = "",
    folder: str = "",
) -> tuple[hubrepo.HubHandle, Path]:
    """Resolve the hub and locate one package inside it.

    Normalisation is the caller's job, deliberately. `pull` takes a tracker reference from
    a person and wants the specific "that is not a valid ClickUp reference" error on a
    typo. `sync` already knows the package directory, and a directory name matches no
    tracker pattern — normalising it there would reject the very package it just pulled.
    """
    handle = _resolve_hub(state, t)
    assert handle.tasks_dir is not None
    directory = package.find_package(
        handle.tasks_dir, canonical_id=canonical_id, raw_ref=raw_ref, folder=folder
    )
    return handle, directory


def _routing_table(decision: routing.RoutingDecision, t: Translator) -> list[str]:
    lines = [t("route.header", tier=decision.tier, score=decision.score)]
    for phase in routing.PHASES:
        setting = decision.phases.get(phase)
        if setting:
            advisor = f" + advisor {setting.advisor}" if setting.advisor else ""
            lines.append(f"  {phase:<10} {setting.model} / {setting.effort}{advisor}")
    if decision.modifiers:
        lines.append(t("route.modifiers", names=", ".join(decision.modifiers)))
    lines.append("")
    lines.append(t("route.launch", command=decision.launch))
    return lines


def cmd_pull(args: argparse.Namespace) -> int:
    ctx = paths.detect()
    t = load_translator(args.lang)
    root = _require_dev(ctx, t)
    state = context_mod.load_dev_state(ctx)
    t = _translator_for(state.config, args.lang)

    tracker_type = str((state.config.get("tracker") or {}).get("type") or "none")
    canonical, ref = _reference_for(args.ref, tracker_type, state.config)
    handle, source_dir = _hub_package(
        state, t, canonical_id=canonical, raw_ref=ref, folder=args.ref
    )

    task = package.read_task(source_dir)
    issues = schemas.validate(task, "task")
    if issues:
        raise ValidationError(
            t("err.task_invalid", folder=source_dir.name),
            reason="; ".join(issues[:5]),
            remedy=t("err.task_invalid_fix"),
        )

    status = str(task.get("status") or "draft")
    if status != "published" and not args.allow_draft:
        raise UsageError(
            t("err.not_published", task_id=task.get("id"), status=status),
            reason=t("err.not_published_why"),
            remedy=t("err.not_published_fix"),
        )

    destination = root / paths.CONFIG_DIR_NAME / paths.TASKS_DIR / source_dir.name
    plan = package.plan_copy(source_dir)
    previous_lock = lock.load(destination / lock.LOCK_FILENAME)
    digests, removed = package.copy_package(source_dir, destination, plan=plan)

    # Developer files are created once and never replaced (invariant I9).
    language = str(state.config.get("language") or "en")
    created: list[str] = []
    for name in ("plan.md", "questions.md"):
        content = templates.render(
            templates.dev_template(language, name), {"TASK_ID": str(task.get("id") or "")}
        )
        if templates.write_if_absent(destination / name, content):
            created.append(name)

    policy = (
        hubrepo.read_policy(handle.path)
        or hubrepo.local_policy(state.config)
        or context_mod.default_policy()
    )
    decision: Optional[routing.RoutingDecision] = None
    try:
        decision = routing.compute(task=task, profile=state.profile, policy=policy, role=state.role)
    except Exception as exc:
        state.warnings.append(f"routing: {exc}")

    document = lock.build(
        task_id=str(task.get("id") or canonical),
        folder=source_dir.name,
        version=int(task.get("version") or 0),
        files=digests,
        pulled_at=_now_iso(),
        tracker_ref=ref,
        title=str(task.get("title") or ""),
        hub_commit=handle.commit,
        hub_id=handle.identity,
        role=state.role,
        status=status,
        routing=decision.as_dict() if decision else None,
    )
    (destination / lock.LOCK_FILENAME).write_text(lock.serialize(document), encoding="utf-8")

    (root / paths.CONFIG_DIR_NAME / paths.ACTIVE_TASK_FILE).write_text(
        source_dir.name + "\n", encoding="utf-8"
    )

    # The briefing: at most fifteen lines, no code.
    _out(
        t(
            "pull.done",
            task_id=task.get("id"),
            version=task.get("version"),
            title=task.get("title"),
        )
    )
    _out(t("pull.files", count=len(digests)))
    if removed:
        _out(t("pull.removed", files=", ".join(removed)))
    if created:
        _out(t("pull.created", files=", ".join(created)))
    for relative, reason in plan.skipped:
        if reason == "developer-owned":
            _out(t("pull.skipped_developer", file=relative))

    added, modified, dropped = lock.diff_versions(previous_lock, document)
    if previous_lock and (added or modified or dropped):
        _out(t("pull.changes", added=len(added), modified=len(modified), removed=len(dropped)))

    role_scope = (task.get("scope") or {}).get(state.role or "")
    if isinstance(role_scope, Mapping):
        _out(t("pull.scope", patterns=", ".join(role_scope.get("allow") or [])))
    else:
        _out(t("pull.scope_missing", role=state.role or "-"))

    if decision:
        _out("")
        for line in _routing_table(decision, t):
            _out(line)

    for warning in state.warnings[:3]:
        _out("")
        _out(f"! {warning}")
    return EXIT_OK


def _unified_diff(old: str, new: str, label: str) -> list[str]:
    diff = list(
        difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            fromfile=f"a/{label}",
            tofile=f"b/{label}",
            lineterm="",
            n=2,
        )
    )
    return diff


def cmd_sync(args: argparse.Namespace) -> int:
    ctx = paths.detect()
    t = load_translator(args.lang)
    _require_dev(ctx, t)
    state = context_mod.load_dev_state(ctx)
    t = _translator_for(state.config, args.lang)

    if state.package_dir is None:
        raise UsageError(
            t("err.no_active_task"),
            reason=t("err.no_active_task_why"),
            remedy=t("err.no_active_task_fix"),
        )

    local_dir = state.package_dir
    # The package is already identified: use the directory name and the identifier the
    # lock recorded, not a tracker reference the user did not type.
    locked_id = str((state.lock_document or {}).get("task_id") or state.task_id)
    handle, source_dir = _hub_package(state, t, canonical_id=locked_id, folder=local_dir.name)
    task = package.read_task(source_dir)
    ref = str((task.get("tracker") or {}).get("ref") or "")

    # Capture the current contents so the diff can be shown before anything is written.
    before: dict[str, str] = {}
    for relative in package.researcher_files(local_dir):
        try:
            before[relative] = (local_dir / relative).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            before[relative] = ""

    previous_lock = lock.load(local_dir / lock.LOCK_FILENAME)
    integrity = (
        lock.verify(local_dir, previous_lock, present=list(before))
        if previous_lock
        else lock.IntegrityReport()
    )

    plan = package.plan_copy(source_dir)
    digests, removed = package.copy_package(source_dir, local_dir, plan=plan)

    policy = (
        hubrepo.read_policy(handle.path)
        or hubrepo.local_policy(state.config)
        or context_mod.default_policy()
    )
    decision: Optional[routing.RoutingDecision] = None
    try:
        decision = routing.compute(task=task, profile=state.profile, policy=policy, role=state.role)
    except Exception:
        decision = None

    document = lock.build(
        task_id=str(task.get("id") or ""),
        folder=source_dir.name,
        version=int(task.get("version") or 0),
        files=digests,
        pulled_at=_now_iso(),
        tracker_ref=ref,
        title=str(task.get("title") or ""),
        hub_commit=handle.commit,
        hub_id=handle.identity,
        role=state.role,
        status=str(task.get("status") or ""),
        routing=decision.as_dict() if decision else None,
    )
    (local_dir / lock.LOCK_FILENAME).write_text(lock.serialize(document), encoding="utf-8")

    added, modified, dropped = lock.diff_versions(previous_lock, document)
    old_version = (previous_lock or {}).get("version")

    if not (added or modified or dropped or removed):
        _out(t("sync.no_changes", task_id=task.get("id"), version=task.get("version")))
        if integrity.changed:
            _out(t("sync.restored", files=", ".join(integrity.changed)))
        _out(t("sync.next_no_changes"))
        return EXIT_OK

    _out(
        t(
            "sync.done",
            task_id=task.get("id"),
            old=old_version if isinstance(old_version, int) else "-",
            new=task.get("version"),
        )
    )
    if added:
        _out(t("sync.added", files=", ".join(added)))
    if modified:
        _out(t("sync.modified", files=", ".join(modified)))
    if dropped or removed:
        _out(t("sync.removed", files=", ".join(sorted(set(dropped) | set(removed)))))
    if integrity.changed:
        _out(t("sync.restored", files=", ".join(integrity.changed)))

    emitted = 0
    for relative in modified:
        try:
            new_text = (local_dir / relative).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        diff = _unified_diff(before.get(relative, ""), new_text, relative)
        if not diff:
            continue
        _out("")
        for line in diff:
            if emitted >= MAX_DIFF_LINES:
                _out(t("sync.diff_truncated", limit=MAX_DIFF_LINES))
                emitted += 1
                break
            _out(line)
            emitted += 1
        if emitted > MAX_DIFF_LINES:
            break

    decisions_changed = "decisions.md" in set(modified) | set(added)
    _out("")
    _out(t("sync.next_changes") if decisions_changed else t("sync.next_review"))
    return EXIT_OK


# --------------------------------------------------------------------------------------
# status / brief / route / activate
# --------------------------------------------------------------------------------------


def cmd_status(args: argparse.Namespace) -> int:
    ctx = paths.detect()
    if ctx.is_hub:
        return _hub_status(args, ctx)
    state = context_mod.load_dev_state(ctx)
    t = _translator_for(state.config, args.lang)
    if args.json:
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "persona": ctx.persona,
            "root": str(ctx.root) if ctx.root else None,
            "role": state.role,
            "task": None,
            "warnings": state.warnings,
        }
        if state.task:
            payload["task"] = {
                "id": state.task_id,
                "title": state.title,
                "version": state.version,
                "status": str(state.task.get("status") or ""),
                "enforcement": state.enforcement,
                "active_source": state.active_source,
                "scope": state.scope_for_role(),
            }
            if state.routing:
                payload["routing"] = state.routing.as_dict()
        _out(_dump_json(payload))
        return EXIT_OK
    _out(context_mod.status_text(state, t))
    return EXIT_OK


def cmd_brief(args: argparse.Namespace) -> int:
    """Always returns 0. See the module docstring for why."""
    try:
        ctx = paths.detect()
        if ctx.is_hub:
            t = load_translator(args.lang)
            _out(context_mod.hub_context(ctx, t))
            return EXIT_OK
        state = context_mod.load_dev_state(ctx)
        t = _translator_for(state.config, args.lang)
        _out(context_mod.brief(state, t, phase=args.phase, session_id=args.session))
    except Exception as exc:
        _out(f"{context_mod.SENTINEL_ERROR} {exc}")
    return EXIT_OK


def cmd_route(args: argparse.Namespace) -> int:
    ctx = paths.detect()
    t = load_translator(args.lang)
    _require_dev(ctx, t)
    state = context_mod.load_dev_state(ctx)
    t = _translator_for(state.config, args.lang)
    if state.routing is None:
        raise UsageError(
            t("err.no_active_task"),
            reason=t("err.no_active_task_why"),
            remedy=t("err.no_active_task_fix"),
        )
    if args.json:
        _out(
            _dump_json(
                {
                    "schema_version": SCHEMA_VERSION,
                    "task_id": state.task_id,
                    "role": state.role,
                    "signals": state.routing.signals,
                    "modifiers": state.routing.modifiers,
                    **state.routing.as_dict(),
                }
            )
        )
        return EXIT_OK
    for line in _routing_table(state.routing, t):
        _out(line)
    return EXIT_OK


def cmd_activate(args: argparse.Namespace) -> int:
    ctx = paths.detect()
    t = load_translator(args.lang)
    root = _require_dev(ctx, t)
    state = context_mod.load_dev_state(ctx)
    t = _translator_for(state.config, args.lang)
    pointer = root / paths.CONFIG_DIR_NAME / paths.ACTIVE_TASK_FILE

    if args.clear:
        if pointer.exists():
            pointer.unlink()
            _out(t("activate.cleared"))
        else:
            _out(t("activate.already_clear"))
        return EXIT_OK

    if not args.folder:
        raise UsageError(
            t("err.activate_needs_folder"),
            remedy=t("err.activate_needs_folder_fix"),
        )

    tasks_dir = root / paths.CONFIG_DIR_NAME / paths.TASKS_DIR
    directory = package.find_package(tasks_dir, folder=args.folder, raw_ref=args.folder)
    pointer.write_text(directory.name + "\n", encoding="utf-8")
    _out(t("activate.done", folder=directory.name))
    return EXIT_OK


# --------------------------------------------------------------------------------------
# audit
# --------------------------------------------------------------------------------------


def cmd_audit(args: argparse.Namespace) -> int:
    ctx = paths.detect()
    t = load_translator(args.lang)

    if not ctx.is_dev or ctx.root is None:
        # In CI the repository may not be connected at all. Say so and skip rather than
        # failing the build.
        message = t("audit.skipped_no_init")
        if args.format == "json":
            _out(_dump_json({"schema_version": SCHEMA_VERSION, "skipped": True, "reason": message}))
        else:
            _out(message)
        return EXIT_VIOLATION if args.require_task else EXIT_OK

    state = context_mod.load_dev_state(ctx)
    t = _translator_for(state.config, args.lang)
    root = ctx.root

    # An explicit --task or --branch overrides the session's active task, which is how CI
    # audits a branch it did not check out interactively.
    if args.task or args.branch:
        tasks_dir = root / paths.CONFIG_DIR_NAME / paths.TASKS_DIR
        directory: Optional[Path] = None
        if args.task:
            tracker_type = str((state.config.get("tracker") or {}).get("type") or "none")
            try:
                canonical, ref = _reference_for(args.task, tracker_type, state.config)
            except UsageError:
                canonical, ref = args.task, args.task
            try:
                directory = package.find_package(
                    tasks_dir, canonical_id=canonical, raw_ref=ref, folder=args.task
                )
            except UsageError:
                directory = None
        if directory is None and args.branch:
            directory = package.find_by_branch(tasks_dir, args.branch)
        if directory is None:
            message = t("audit.skipped_no_task", reference=args.task or args.branch)
            if args.format == "json":
                _out(
                    _dump_json(
                        {"schema_version": SCHEMA_VERSION, "skipped": True, "reason": message}
                    )
                )
            else:
                _out(message)
            return EXIT_VIOLATION if args.require_task else EXIT_OK
        state.package_dir = directory
        state.task = _read_json(directory / package.TASK_FILE)
        state.lock_document = lock.load(directory / lock.LOCK_FILENAME)

    if state.task is None and args.require_task:
        message = t("audit.skipped_no_task", reference="-")
        _out(message)
        return EXIT_VIOLATION

    base = args.base if args.base is not None else str(state.config.get("base_ref") or "")
    report = audit_mod.audit(
        root,
        task=state.task,
        role=state.role,
        profile=state.profile,
        base=base or None,
        package_dir=state.package_dir,
        lock_document=state.lock_document,
    )

    if args.format == "json":
        _out(_dump_json(audit_mod.render_json(report)))
    else:
        _out(audit_mod.render_markdown(report, t))

    if args.no_fail:
        return EXIT_OK
    return EXIT_VIOLATION if not report.clean else EXIT_OK


# --------------------------------------------------------------------------------------
# doctor
# --------------------------------------------------------------------------------------


def _python_check() -> dict[str, Any]:
    """Whether `python3` resolves to a usable interpreter.

    This is the check the launcher strategy depends on. Hooks run `python3 <script>` in
    exec form, so a
    machine where `python3` does not resolve has **no scope protection at all** — and
    silently, which is the failure invariant I13 exists to surface. It is reported as an
    error, not a warning.
    """
    import shutil
    import subprocess

    found = shutil.which("python3")
    if not found:
        return {
            "ok": False,
            "level": "error",
            "detail": "python3 is not on PATH, so the plugin's hooks cannot run.",
        }
    try:
        result = subprocess.run(  # noqa: S603 - fixed program, list form
            [found, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "level": "error", "detail": f"python3 could not be run: {exc}"}

    version = result.stdout.strip()
    try:
        major, minor = (int(part) for part in version.split(".", 1))
    except ValueError:
        return {"ok": False, "level": "error", "detail": f"python3 reported {version!r}"}
    if (major, minor) < (3, 9):
        return {
            "ok": False,
            "level": "error",
            "detail": f"python3 is {version}; wizrelay needs 3.9 or newer.",
        }
    return {"ok": True, "level": "info", "detail": f"python3 {version} at {found}"}


def _duplicate_plugin_check() -> dict[str, Any]:
    """Look for a second installed plugin whose manifest name is also `wizrelay` (R16).

     When two enabled plugins share a manifest name, only one registers its
     `hooks/hooks.json` and the other's hooks are left out
    . Scope protection then disappears silently.

     The exact field names in `claude plugin list --json` are not yet verified against a
     live CLI, so every failure path here degrades to "could not determine" rather than
     reporting a clean result it has not established.
    """
    import shutil
    import subprocess

    claude = shutil.which("claude")
    if not claude:
        return {
            "ok": None,
            "level": "warn",
            "detail": "The claude CLI is not on PATH, so a duplicate plugin name could "
            "not be checked. Run `/wizrelay:doctor` inside Claude Code instead.",
        }
    try:
        result = subprocess.run(  # noqa: S603 - fixed program, list form
            [claude, "plugin", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,
            check=False,
        )
        payload = json.loads(result.stdout or "[]")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        return {
            "ok": None,
            "level": "warn",
            "detail": f"`claude plugin list --json` could not be read ({exc}).",
        }

    entries = payload if isinstance(payload, list) else payload.get("plugins") or []
    matches: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or entry.get("plugin") or "")
        if fold(name) == "wizrelay" or name.startswith("wizrelay@"):
            matches.append(str(entry.get("id") or entry.get("marketplace") or name))

    if len(matches) > 1:
        return {
            "ok": False,
            "level": "error",
            "detail": "More than one installed plugin uses the manifest name `wizrelay`: "
            + ", ".join(sorted(matches))
            + ". Only one of them registers hooks, so scope protection may be inactive. "
            "Uninstall the duplicate.",
        }
    return {"ok": True, "level": "info", "detail": f"{len(matches)} plugin named wizrelay."}


def cmd_doctor(args: argparse.Namespace) -> int:
    ctx = paths.detect()
    checks: list[dict[str, Any]] = []

    def add(name: str, result: Mapping[str, Any]) -> None:
        checks.append({"name": name, **result})

    add("python", _python_check())
    add("duplicate-plugin-name", _duplicate_plugin_check())
    add(
        "git",
        {"ok": True, "level": "info", "detail": "git available"}
        if gitcmd.run(["--version"]).ok
        else {"ok": False, "level": "error", "detail": "git is not on PATH."},
    )
    add(
        "persona",
        {
            "ok": not ctx.is_silent,
            "level": "info" if not ctx.is_silent else "warn",
            "detail": f"{ctx.persona} at {ctx.root or Path.cwd()}",
        },
    )
    add(
        "tracker-catalogue",
        {
            "ok": len(trackers.available()) > 1,
            "level": "info" if len(trackers.available()) > 1 else "warn",
            "detail": "available: " + ", ".join(trackers.available()),
        },
    )
    add(
        "version",
        {"ok": True, "level": "info", "detail": f"wizrelay {__version__}"},
    )

    state: Optional[context_mod.DevState] = None
    if ctx.is_dev:
        state = context_mod.load_dev_state(ctx, resolve_hub=True, allow_network=False)
        add(
            "schema",
            {
                "ok": not state.warnings,
                "level": "info" if not state.warnings else "warn",
                "detail": "; ".join(state.warnings[:5]) or "configuration validates",
            },
        )
        add(
            "role",
            {
                "ok": bool(state.role) and not str(state.role).startswith("{{"),
                "level": "info" if state.role and not str(state.role).startswith("{{") else "error",
                "detail": f"role = {state.role!r}",
            },
        )
        hub = state.hub
        add(
            "hub",
            {
                "ok": bool(hub and hub.available),
                "level": "info" if hub and hub.available else "warn",
                "detail": (
                    f"{hub.source} at {hub.path} ({hub.identity})"
                    if hub and hub.available
                    else "; ".join((hub.notes if hub else []) or ["no hub configured"])
                ),
            },
        )
        add(
            "active-task",
            {
                "ok": state.has_task,
                "level": "info" if state.has_task else "warn",
                "detail": (
                    f"{state.task_id} v{state.version} via {state.active_source}"
                    if state.has_task
                    else "no active task"
                ),
            },
        )
        if state.lock_document and state.package_dir:
            report = lock.verify(
                state.package_dir,
                state.lock_document,
                present=package.researcher_files(state.package_dir),
            )
            add(
                "integrity",
                {
                    "ok": report.clean,
                    "level": "info" if report.clean else "error",
                    "detail": (
                        "package matches the lock"
                        if report.clean
                        else f"changed={report.changed} missing={report.missing} "
                        f"unlocked={report.unlocked}"
                    ),
                },
            )
            locked_version = state.lock_document.get("version")
            if isinstance(locked_version, int) and locked_version < state.version:
                add(
                    "lock-schema",
                    {
                        "ok": False,
                        "level": "warn",
                        "detail": f"the lock records v{locked_version} but the package is "
                        f"v{state.version}; run `wizrelay sync`.",
                    },
                )
            lock_schema = state.lock_document.get("schema_version")
            if isinstance(lock_schema, int) and lock_schema < SCHEMA_VERSION:
                add(
                    "lock-migration",
                    {
                        "ok": False,
                        "level": "warn",
                        "detail": f"the lock uses schema_version {lock_schema}; run "
                        "`wizrelay migrate` to bring it forward.",
                    },
                )

    if (Path.cwd() / paths.CONFIG_DIR_NAME / "project-profile.json").exists() or (
        Path.cwd() / ".ai"
    ).is_dir():
        add(
            "prototype",
            {
                "ok": False,
                "level": "warn",
                "detail": "a prototype `.ai/` directory is present; run "
                "`wizrelay migrate --from-prototype`.",
            },
        )

    errors = [c for c in checks if c.get("level") == "error"]
    warnings = [c for c in checks if c.get("level") == "warn"]

    t = _translator_for(state.config if state else {}, args.lang)

    if args.json:
        _out(
            _dump_json(
                {
                    "schema_version": SCHEMA_VERSION,
                    "wizrelay": __version__,
                    "persona": ctx.persona,
                    "root": str(ctx.root) if ctx.root else None,
                    "platform": sys.platform,
                    "python": sys.version.split()[0],
                    "checks": checks,
                    "errors": len(errors),
                    "warnings": len(warnings),
                }
            )
        )
    else:
        _out(t("doctor.header", version=__version__, persona=ctx.persona))
        for check in checks:
            mark = {"error": "x", "warn": "!", "info": "+"}.get(str(check.get("level")), "?")
            _out(f"  {mark} {check['name']}: {check['detail']}")
        _out("")
        if errors:
            _out(t("doctor.errors", count=len(errors)))
        elif warnings:
            _out(t("doctor.warnings", count=len(warnings)))
        else:
            _out(t("doctor.ok"))

    return EXIT_VIOLATION if errors else EXIT_OK


# --------------------------------------------------------------------------------------
# migrate
# --------------------------------------------------------------------------------------


def cmd_migrate(args: argparse.Namespace) -> int:
    """Move a prototype `.ai/` layout to `.wizrelay/`."""
    t = load_translator(args.lang)
    root = paths.find_repo_root(Path.cwd())
    if root is None:
        raise UsageError(t("err.not_a_repo"), remedy=t("err.not_a_repo_fix"))

    if not args.from_prototype:
        raise UsageError(t("err.migrate_needs_flag"), remedy="wizrelay migrate --from-prototype")

    source = root / ".ai"
    if not source.is_dir():
        _out(t("migrate.nothing"))
        return EXIT_OK

    target = root / paths.CONFIG_DIR_NAME
    moved: list[str] = []

    rename_map = {
        "project-profile.json": paths.PROFILE_FILE,
        "config.json": paths.DEV_CONFIG,
        "config.local.json": paths.DEV_LOCAL_CONFIG,
        "PROTOCOL.md": paths.PROTOCOL_FILE,
        ".active-task": paths.ACTIVE_TASK_FILE,
    }

    target.mkdir(parents=True, exist_ok=True)
    for entry in sorted(source.iterdir()):
        destination_name = rename_map.get(entry.name, entry.name)
        destination = target / destination_name
        if destination.exists():
            continue
        entry.replace(destination)
        moved.append(f"{entry.name} -> {destination_name}")

    # Rewrite the tag and command names the prototype used.
    replacements = {
        ".ai/": f"{paths.CONFIG_DIR_NAME}/",
        "[RW-": "[WIZRELAY-",
        "/task:": "/wizrelay:",
    }
    rewritten: list[str] = []
    for path in sorted(target.rglob("*.md")) + sorted(target.rglob("*.json")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        updated = text
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            rewritten.append(str(path.relative_to(root)))

    try:
        next(source.iterdir())
    except StopIteration:
        source.rmdir()
        moved.append(".ai/ removed")
    except OSError:  # pragma: no cover
        pass

    _out(t("migrate.done", count=len(moved)))
    for item in moved:
        _out(f"  + {item}")
    for item in rewritten:
        _out(f"  ~ {item}")
    _out("")
    _out(t("migrate.next"))
    return EXIT_OK


# --------------------------------------------------------------------------------------
# hub commands
# --------------------------------------------------------------------------------------


def _hub_language(root: Path, override: Optional[str] = None) -> str:
    marker = hubrepo.read_marker(root)
    return override or str(marker.get("language") or "en")


def cmd_hub_init(args: argparse.Namespace) -> int:
    target = Path(args.directory).expanduser().resolve() if args.directory else Path.cwd()
    language = args.lang or "en"
    t = load_translator(language)

    target.mkdir(parents=True, exist_ok=True)
    changes: list[str] = []

    marker = target / paths.HUB_MARKER
    if not marker.exists():
        document = json.loads(templates.hub_template(language, "wizrelay-hub.json"))
        document["name"] = args.name or f"{{{{{target.name}}}}}"
        document["language"] = language
        if args.tracker:
            document["tracker"] = {"type": args.tracker}
        _write_json(marker, document)
        changes.append(paths.HUB_MARKER)

    if templates.write_if_absent(
        target / "CLAUDE.md",
        templates.render(templates.hub_template(language, "CLAUDE.md"), {"HUB_NAME": target.name}),
    ):
        changes.append("CLAUDE.md")

    for directory in ("tasks", "policies", "templates/package"):
        path = target / directory
        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
            changes.append(directory + "/")

    keep = target / "tasks" / ".gitkeep"
    if templates.write_if_absent(keep, ""):
        changes.append("tasks/.gitkeep")

    if templates.merge_gitignore(target / ".gitignore", [".DS_Store"]):
        changes.append(".gitignore")

    if changes:
        _out(t("hubinit.done", count=len(changes), path=str(target)))
        for item in sorted(set(changes)):
            _out(f"  + {item}")
        _out("")
        _out(t("hubinit.next"))
    else:
        _out(t("init.no_changes"))
    return EXIT_OK


def cmd_hub_new(args: argparse.Namespace) -> int:
    ctx = paths.detect()
    t = load_translator(args.lang)
    root = _require_hub_persona(ctx, t)
    marker = hubrepo.read_marker(root)
    language = _hub_language(root, args.lang)
    t = load_translator(language)

    tracker_type = str(args.tracker or (marker.get("tracker") or {}).get("type") or "none")
    canonical, ref = trackers.normalize(args.ref, tracker_type, config=marker)

    roles = [r.strip() for r in (args.roles or "").split(",") if r.strip()]
    if not roles:
        roles = [str(r) for r in (marker.get("roles") or []) if str(r).strip()]
    if not roles:
        raise UsageError(
            t("err.no_roles"),
            reason=t("err.no_roles_why"),
            remedy=t("err.no_roles_fix"),
        )

    title = args.title or f"{{{{title for {canonical}}}}}"
    folder, _slug = package.scaffold_names(canonical, title)
    destination = root / paths.TASKS_DIR / folder
    if destination.exists() and not args.force:
        raise UsageError(
            t("err.package_exists", folder=folder),
            remedy=t("err.package_exists_fix", folder=folder),
        )

    destination.mkdir(parents=True, exist_ok=True)
    document = package.new_task_document(
        canonical_id=canonical,
        ref=ref,
        title=title,
        roles=roles,
        tracker_type=tracker_type,
        url=trackers.build_url(ref, tracker_type, config=marker),
        enforcement=str(marker.get("default_enforcement") or "strict"),
    )
    package.write_task(destination, document)

    written = [package.TASK_FILE]
    # A hub may override the package templates; its own copies win.
    hub_templates = root / "templates" / "package"
    for relative, content in templates.package_scaffold(language, roles).items():
        override = hub_templates / relative
        if override.is_file():
            content = override.read_text(encoding="utf-8")
        content = templates.render(content, {"TASK_ID": canonical})
        if templates.write_if_absent(destination / relative, content):
            written.append(relative)

    _out(t("hubnew.done", task_id=canonical, folder=folder))
    for item in sorted(written):
        _out(f"  + {item}")
    _out("")
    _out(t("hubnew.next", task_id=canonical))
    return EXIT_OK


_FORBIDDEN_MARKERS = ("TBD", "???")
_WARN_MARKERS = ("TODO",)


def _validate_package(directory: Path, language: str) -> tuple[list[str], list[str]]:
    """Structural validation of one package.

    Returns `(errors, warnings)`, each a list of `file:line: message` strings. The split
    matters: an error blocks publication, a warning does not. Dot-prefixed files are never
    inspected, because they are private to the hub and never reach a developer.
    """
    errors: list[str] = []
    warnings: list[str] = []
    # Messages are package-relative: the report header already names the directory, and
    # repeating a 60-character folder name on every line buries the actual finding.

    task = _read_json(directory / package.TASK_FILE)
    if task is None:
        errors.append(f"{package.TASK_FILE}: missing or not valid JSON")
        return errors, warnings

    for issue in schemas.validate(task, "task"):
        errors.append(f"{package.TASK_FILE}: {issue}")

    roles = [str(r) for r in (task.get("roles") or [])]

    # Required files, plus the conditional ones.
    required = list(package.REQUIRED_FILES)
    if len(roles) > 1:
        required.append("contracts.md")
    for relative in required:
        if not (directory / relative).is_file():
            errors.append(f"{relative}: required file is missing")
    for role in roles:
        if not (directory / "roles" / f"{role}.md").is_file():
            errors.append(f"roles/{role}.md: required file is missing")

    # Scope: a non-empty allow list of valid, relative globs.
    scope = task.get("scope") or {}
    for role in roles:
        entry = scope.get(role) if isinstance(scope, Mapping) else None
        if not isinstance(entry, Mapping):
            errors.append(f"{package.TASK_FILE}: scope.{role} is missing")
            continue
        allow = [p for p in (entry.get("allow") or []) if isinstance(p, str)]
        if not allow:
            errors.append(f"{package.TASK_FILE}: scope.{role}.allow is empty")
        for key in ("allow", "deny"):
            for index, pattern in enumerate(entry.get(key) or []):
                if not isinstance(pattern, str):
                    errors.append(
                        f"{package.TASK_FILE}: scope.{role}.{key}[{index}] is not a string"
                    )
                    continue
                from . import globs as glob_mod

                reason = glob_mod.validate_glob(pattern)
                if reason:
                    errors.append(
                        f"{package.TASK_FILE}: scope.{role}.{key}[{index}] {pattern!r}: {reason}"
                    )

    # Markdown bodies: placeholders and markers, with line numbers.
    from .textformats import parse_acceptance

    for relative, path in sorted(
        (p.relative_to(directory).as_posix(), p) for p in directory.rglob("*.md")
    ):
        if package.classify(relative) != package.RESEARCHER:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{relative}: could not be read ({exc})")
            continue
        for line_number, placeholder in templates.find_placeholders(text):
            errors.append(f"{relative}:{line_number}: unfilled placeholder {placeholder}")
        for number, line in enumerate(text.splitlines(), start=1):
            for marker in _FORBIDDEN_MARKERS:
                if marker in line:
                    errors.append(f"{relative}:{number}: contains {marker}")
            for marker in _WARN_MARKERS:
                if marker in line:
                    warnings.append(f"{relative}:{number}: contains {marker}")

    # task.json may also carry placeholders, which the schema cannot catch.
    try:
        task_text = (directory / package.TASK_FILE).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        task_text = ""
    for line_number, placeholder in templates.find_placeholders(task_text):
        errors.append(f"{package.TASK_FILE}:{line_number}: unfilled placeholder {placeholder}")

    # Acceptance criteria: roles must exist, every role must be covered, and each
    # criterion should carry a verification line and Given/When/Then.
    acceptance_path = directory / "acceptance.md"
    if acceptance_path.is_file():
        criteria = parse_acceptance(acceptance_path.read_text(encoding="utf-8"))
        if not criteria:
            errors.append("acceptance.md: no `## AC-<n>` heading was found")
        known = {fold(role) for role in roles}
        covered: set = set()
        for criterion in criteria:
            for role in criterion.roles:
                if fold(role) not in known:
                    errors.append(
                        f"acceptance.md:{criterion.line}: {criterion.identifier} "
                        f"names unknown role {role!r}"
                    )
            if criterion.roles:
                covered.update(fold(role) for role in criterion.roles)
            else:
                covered.update(known)
            if not criterion.verification:
                warnings.append(
                    f"acceptance.md:{criterion.line}: {criterion.identifier} has "
                    "no verification line"
                )
            if not criterion.has_gherkin:
                warnings.append(
                    f"acceptance.md:{criterion.line}: {criterion.identifier} has no Given/When/Then"
                )
        for role in roles:
            if fold(role) not in covered:
                errors.append(f"acceptance.md: role {role!r} has no acceptance criterion")

    contracts = directory / "contracts.md"
    if len(roles) > 1 and contracts.is_file() and not contracts.read_text(encoding="utf-8").strip():
        warnings.append("contracts.md: empty in a package with multiple roles")

    signals = (task.get("routing") or {}).get("signals") or {}
    if str(signals.get("ambiguity") or "").lower() == "high":
        warnings.append(
            f"{package.TASK_FILE}: ambiguity is high; consider resolving it before publishing"
        )

    return sorted(set(errors)), sorted(set(warnings))


def cmd_hub_validate(args: argparse.Namespace) -> int:
    ctx = paths.detect()
    t = load_translator(args.lang)
    root = _require_hub_persona(ctx, t)
    marker = hubrepo.read_marker(root)
    language = _hub_language(root, args.lang)
    t = load_translator(language)

    tracker_type = str((marker.get("tracker") or {}).get("type") or "none")
    canonical, ref = _reference_for(args.ref, tracker_type, marker)
    directory = package.find_package(
        root / paths.TASKS_DIR, canonical_id=canonical, raw_ref=ref, folder=args.ref
    )

    errors, warnings = _validate_package(directory, language)

    lines: list[str] = [t("validate.header", folder=directory.name)]
    if errors:
        lines.append("")
        lines.append(t("validate.errors", count=len(errors)))
        lines.extend(f"- {item}" for item in errors)
    if warnings:
        lines.append("")
        lines.append(t("validate.warnings", count=len(warnings)))
        lines.extend(f"- {item}" for item in warnings)
    if not errors and not warnings:
        lines.append("")
        lines.append(t("validate.clean"))

    report = "\n".join(lines) + "\n"
    _out(report)

    # The report is written into the package as a private file, so it never reaches a
    # developer repository (invariant I8).
    (directory / ".validation.md").write_text(report, encoding="utf-8")

    if args.no_fail:
        return EXIT_OK
    if errors:
        return EXIT_VIOLATION
    if warnings and args.strict:
        return EXIT_VIOLATION
    return EXIT_OK


def cmd_hub_publish_prep(args: argparse.Namespace) -> int:
    ctx = paths.detect()
    t = load_translator(args.lang)
    root = _require_hub_persona(ctx, t)
    marker = hubrepo.read_marker(root)
    language = _hub_language(root, args.lang)
    t = load_translator(language)

    tracker_type = str((marker.get("tracker") or {}).get("type") or "none")
    canonical, ref = _reference_for(args.ref, tracker_type, marker)
    directory = package.find_package(
        root / paths.TASKS_DIR, canonical_id=canonical, raw_ref=ref, folder=args.ref
    )

    errors, warnings = _validate_package(directory, language)
    if errors:
        raise ValidationError(
            t("err.publish_blocked", folder=directory.name, count=len(errors)),
            reason="; ".join(errors[:5]),
            remedy=t("err.publish_blocked_fix", folder=directory.name),
        )

    document = package.read_task(directory)
    version = int(document.get("version") or 0) + 1
    document["version"] = version
    document["status"] = "published"
    document["updated_at"] = _today()

    changelog = document.get("changelog")
    if not isinstance(changelog, list):
        changelog = []
    changelog.append({"version": version, "date": _today(), "summary": args.summary})
    document["changelog"] = changelog

    package.write_task(directory, document)

    _out(t("publish.done", task_id=document.get("id"), version=version))
    for item in warnings[:5]:
        _out(f"  ! {item}")
    _out("")
    _out(t("publish.next", folder=directory.name, task_id=document.get("id")))
    return EXIT_OK


def cmd_hub_comment(args: argparse.Namespace) -> int:
    """Produce the `[WIZRELAY-PUBLISH]` comment text."""
    import urllib.parse

    ctx = paths.detect()
    t = load_translator(args.lang)
    root = _require_hub_persona(ctx, t)
    marker = hubrepo.read_marker(root)
    language = _hub_language(root, args.lang)
    t = load_translator(language)

    tracker_type = str((marker.get("tracker") or {}).get("type") or "none")
    canonical, ref = _reference_for(args.ref, tracker_type, marker)
    directory = package.find_package(
        root / paths.TASKS_DIR, canonical_id=canonical, raw_ref=ref, folder=args.ref
    )
    task = package.read_task(directory)
    task_id = str(task.get("id") or canonical)
    version = int(task.get("version") or 0)
    roles = [str(r) for r in (task.get("roles") or [])]
    repos = task.get("repos") or {}

    from .textformats import acs_for_role, parse_acceptance

    criteria = []
    acceptance = directory / "acceptance.md"
    if acceptance.is_file():
        criteria = parse_acceptance(acceptance.read_text(encoding="utf-8"))

    lines = [f"{trackers.TAG_PUBLISH} {task_id} — research v{version} published", ""]
    lines.append(str(task.get("title") or ""))
    lines.append("")

    for role in roles:
        lines.append(f"**{role}**")
        for criterion in acs_for_role(criteria, role):
            lines.append(f"- {criterion.identifier}: {criterion.title}")
        lines.append("")
        lines.append("```")
        lines.append(f"/wizrelay:pull {task_id}")
        lines.append("```")
        slug = str(repos.get(role) or "")
        if slug:
            # The prompt is encoded with safe="" so both `/` and `:` are escaped, and the
            # whole URL goes in a code block because GitHub strips `claude-cli://` links
            # .
            query = urllib.parse.urlencode(
                {"repo": slug, "q": f"/wizrelay:pull {task_id}"},
                quote_via=urllib.parse.quote,
                safe="",
            )
            lines.append("")
            lines.append(t("comment.deep_link"))
            lines.append("```")
            lines.append(f"claude-cli://open?{query}")
            lines.append("```")
        lines.append("")

    mention = str(marker.get("researcher_mention") or "")
    if mention:
        lines.append(mention)

    _out("\n".join(lines).rstrip() + "\n")
    return EXIT_OK


def cmd_hub_list(args: argparse.Namespace) -> int:
    ctx = paths.detect()
    t = load_translator(args.lang)
    root = _require_hub_persona(ctx, t)
    packages = package.list_packages(root / paths.TASKS_DIR)

    rows: list[dict[str, Any]] = []
    for directory in packages:
        task = _read_json(directory / package.TASK_FILE) or {}
        rows.append(
            {
                "folder": directory.name,
                "id": task.get("id"),
                "title": task.get("title"),
                "version": task.get("version"),
                "status": task.get("status"),
                "roles": task.get("roles"),
            }
        )

    if args.json:
        _out(_dump_json({"schema_version": SCHEMA_VERSION, "packages": rows}))
        return EXIT_OK

    if not rows:
        _out(t("hub.empty"))
        return EXIT_OK
    _out(t("hublist.header", count=len(rows)))
    for row in rows:
        _out(
            f"  {row['status'] or 'draft':<10} v{row['version'] or 0:<3} "
            f"{row['id'] or row['folder']:<18} {row['title'] or ''}"
        )
    return EXIT_OK


def _hub_status(args: argparse.Namespace, ctx: paths.Context) -> int:
    """`status` in the hub persona: the package inventory plus verification reports."""
    t = load_translator(args.lang)
    root = ctx.root
    assert root is not None
    if args.json:
        return cmd_hub_list(args)
    _out(context_mod.hub_context(ctx, t))
    return EXIT_OK


# --------------------------------------------------------------------------------------
# hook dispatch
# --------------------------------------------------------------------------------------

#: Event name on the command line -> handler module. The names are the ones
#: `plugin/hooks/hooks.json` passes, kept short and hyphenated so the JSON reads well.
_HOOKS: dict[str, str] = {
    "session-start": "session_start",
    "prompt": "prompt",
    "pre-edit": "pre_edit",
    "stop": "stop",
    "model-switch": "model_switch",
}


def cmd_hook(args: argparse.Namespace) -> int:
    """Dispatch to a hook handler.

    Imported lazily, one module per event, so a hook process loads only what it needs.
    `SessionStart` has a 30-second budget and `PreModelSwitch` blocks on a timeout, so
    import cost is part of the latency budget.
    """
    module_name = _HOOKS.get(args.event)
    if module_name is None:
        # Not an error worth a non-zero exit: an unknown event means a newer hooks.json
        # against an older library, and the right answer is to do nothing.
        return EXIT_OK
    import importlib

    module = importlib.import_module(f".hooks.{module_name}", package=__package__)
    return int(module.run())


# --------------------------------------------------------------------------------------
# argument parser
# --------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="wizrelay — carry a researcher's task analysis into every "
        "Claude Code session, deterministically.",
    )
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    parser.add_argument(
        "--lang",
        choices=("en", "tr"),
        default=None,
        help="Override the output language for this invocation.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show a traceback on an unexpected error.",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # --- developer commands ---------------------------------------------------------
    p_init = sub.add_parser("init", help="Connect this repository to a hub (idempotent).")
    p_init.add_argument("--role", help="This repository's role, e.g. backend.")
    p_init.add_argument("--hub", help="Hub git URL.")
    p_init.add_argument("--hub-path", help="Local hub working copy, instead of a URL.")
    p_init.add_argument("--tracker", choices=tuple(trackers.available()), help="Tracker type.")
    p_init.add_argument(
        "--marketplace",
        metavar="owner/repo",
        help="Also register the marketplace and enable the plugin in .claude/settings.json.",
    )
    p_init.set_defaults(func=cmd_init)

    p_pull = sub.add_parser("pull", help="Download a published package and make it active.")
    p_pull.add_argument("ref", help="Tracker reference, canonical id, or package directory.")
    p_pull.add_argument(
        "--allow-draft",
        action="store_true",
        help="Accept a package whose status is not `published`.",
    )
    p_pull.set_defaults(func=cmd_pull)

    p_sync = sub.add_parser("sync", help="Update the active package and show what changed.")
    p_sync.set_defaults(func=cmd_sync)

    p_status = sub.add_parser("status", help="Show the current state and any warnings.")
    p_status.add_argument("--json", action="store_true", help="Machine-readable output.")
    p_status.set_defaults(func=cmd_status)

    p_brief = sub.add_parser("brief", help="Context for a skill to inject. Always exits 0.")
    p_brief.add_argument("--phase", choices=routing.PHASES, help="Add the phase's routing.")
    p_brief.add_argument(
        "--session",
        metavar="ID",
        help="Session id, so the guard heartbeat can be checked (invariant I13).",
    )
    p_brief.set_defaults(func=cmd_brief)

    p_route = sub.add_parser("route", help="Show the routing table and the launch command.")
    p_route.add_argument("--json", action="store_true", help="Machine-readable output.")
    p_route.set_defaults(func=cmd_route)

    p_activate = sub.add_parser("activate", help="Select or clear the active package.")
    p_activate.add_argument("folder", nargs="?", help="Package directory name.")
    p_activate.add_argument("--clear", action="store_true", help="Clear the active task.")
    p_activate.set_defaults(func=cmd_activate)

    p_audit = sub.add_parser("audit", help="Cross the repository's changes with the scope.")
    p_audit.add_argument("--base", help="Base ref to diff against, e.g. origin/main.")
    p_audit.add_argument("--task", help="Audit this task instead of the active one.")
    p_audit.add_argument("--branch", help="Find the task in this branch name (CI).")
    p_audit.add_argument(
        "--require-task",
        action="store_true",
        help="Fail when no task can be determined, instead of skipping.",
    )
    p_audit.add_argument("--format", choices=("md", "json"), default="md")
    p_audit.add_argument(
        "--no-fail", action="store_true", help="Always exit 0, even on a violation."
    )
    p_audit.set_defaults(func=cmd_audit)

    p_doctor = sub.add_parser("doctor", help="Check the environment and the configuration.")
    p_doctor.add_argument("--json", action="store_true", help="Machine-readable output.")
    p_doctor.set_defaults(func=cmd_doctor)

    p_migrate = sub.add_parser("migrate", help="Move a prototype layout to .wizrelay/.")
    p_migrate.add_argument(
        "--from-prototype", action="store_true", help="Migrate from the `.ai/` layout."
    )
    p_migrate.set_defaults(func=cmd_migrate)

    p_hook = sub.add_parser("hook", help="Claude Code hook handler (not for direct use).")
    p_hook.add_argument("event", choices=tuple(_HOOKS))
    p_hook.set_defaults(func=cmd_hook)

    # --- hub commands ---------------------------------------------------------------
    p_hub = sub.add_parser("hub", help="Researcher-side commands, run inside the hub.")
    hub_sub = p_hub.add_subparsers(dest="hub_command", metavar="<subcommand>")

    h_init = hub_sub.add_parser("init", help="Turn an empty repository into a hub.")
    h_init.add_argument("directory", nargs="?", help="Target directory (default: here).")
    h_init.add_argument("--name", help="Hub name.")
    h_init.add_argument("--tracker", choices=tuple(trackers.available()))
    h_init.set_defaults(func=cmd_hub_init)

    h_new = hub_sub.add_parser("new", help="Scaffold a draft package.")
    h_new.add_argument("ref", help="Tracker reference.")
    h_new.add_argument("--title", help="Task title.")
    h_new.add_argument("--roles", help="Comma-separated role list.")
    h_new.add_argument("--tracker", choices=tuple(trackers.available()))
    h_new.add_argument("--force", action="store_true", help="Reuse an existing directory.")
    h_new.set_defaults(func=cmd_hub_new)

    h_validate = hub_sub.add_parser("validate", help="Structural validation of a package.")
    h_validate.add_argument("ref", help="Tracker reference or package directory.")
    h_validate.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    h_validate.add_argument("--no-fail", action="store_true", help="Always exit 0.")
    h_validate.set_defaults(func=cmd_hub_validate)

    h_publish = hub_sub.add_parser(
        "publish-prep", help="Bump the version and mark the package published."
    )
    h_publish.add_argument("ref", help="Tracker reference or package directory.")
    h_publish.add_argument("--summary", required=True, help="Changelog line for this version.")
    h_publish.set_defaults(func=cmd_hub_publish_prep)

    h_comment = hub_sub.add_parser("comment", help="Produce the publish comment text.")
    h_comment.add_argument("ref", help="Tracker reference or package directory.")
    h_comment.set_defaults(func=cmd_hub_comment)

    h_list = hub_sub.add_parser("list", help="List the packages in this hub.")
    h_list.add_argument("--json", action="store_true", help="Machine-readable output.")
    h_list.set_defaults(func=cmd_hub_list)

    def _hub_help(_args: argparse.Namespace) -> int:
        """`wizrelay hub` on its own is a usage error, not a no-op."""
        p_hub.print_help()
        return EXIT_USER

    p_hub.set_defaults(func=_hub_help)

    return parser


# --------------------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    """The single place exit codes and error rendering are decided."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    handler: Optional[Callable[[argparse.Namespace], int]] = getattr(args, "func", None)
    if handler is None:
        parser.print_help()
        return EXIT_USER

    debug = bool(getattr(args, "debug", False)) or os.environ.get("WIZRELAY_DEBUG") == "1"

    try:
        return int(handler(args))
    except WizrelayError as exc:
        sys.stderr.write(exc.render() + "\n")
        if debug:
            import traceback

            traceback.print_exc()
        return exc.code
    except KeyboardInterrupt:  # pragma: no cover - interactive only
        sys.stderr.write("\nInterrupted.\n")
        return EXIT_USER
    except BrokenPipeError:  # pragma: no cover - `wizrelay status | head`
        return EXIT_OK
    except Exception as exc:
        sys.stderr.write(f"{PROG}: unexpected error: {exc}\n")
        if debug:
            import traceback

            traceback.print_exc()
        else:
            sys.stderr.write("Re-run with --debug for a traceback.\n")
        return EXIT_INTERNAL


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
