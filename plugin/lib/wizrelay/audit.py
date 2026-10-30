"""Scope and integrity auditing: git changes crossed with the role's scope.

This is layer 4 of the scope protection and the whole of layer 5. The
same function answers two questions:

* locally, for `/wizrelay:verify` and the `Stop` hook — "did this turn change anything it
  should not have?"
* in CI, for the pull-request gate — "does this branch stay inside the scope the
  researcher published?"

Keeping one implementation for both is invariant I10: the gate cannot be more or less
strict than what the developer saw while working.

Two sources of changed paths are combined:

* ``git status`` — the working tree and index, which is what a session has just done
* ``base...HEAD`` — what the branch has changed since it diverged, which is what a pull
  request is

When the base ref does not resolve — a shallow CI checkout, a fork with no upstream — the
audit says so in a note and continues with the working tree alone, rather than failing. A
gate that breaks on a missing ref gets disabled by whoever is on call.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Optional

from . import config as config_mod
from . import gitcmd, globs, lock, paths
from .i18n import Translator

__all__ = [
    "DEFAULT_INCIDENTAL",
    "AuditReport",
    "audit",
    "render_json",
    "render_markdown",
]

#: Paths an in-scope change may legitimately touch even when the scope does not name them.
#: These are build-tool artefacts a correct change produces as a side effect, so flagging
#: them would train people to ignore the audit. Appendix B2 #9 requires lock files to be
#: allowed at any depth, which the basename glob rule gives for free. A project adds its
#: own through `profile.incidental_allow`; nothing here is team- or company-specific
#: (invariant I1).
DEFAULT_INCIDENTAL = (
    "poetry.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Gemfile.lock",
    "Cargo.lock",
    "composer.lock",
    "go.sum",
    "packages.lock.json",
    "uv.lock",
    "Pipfile.lock",
)

#: Paths `wizrelay init` writes into the repository itself.
#: Connecting a repository to a hub is setup, not task work. Without this list the very
#: first audit after `init` reports `CLAUDE.md`, `.gitignore`, `.claude/settings.json` and
#: `.mcp.json` as scope violations — four false positives, in the one report a developer
#: has no prior reason to trust. They are classified as incidental rather than excluded
#: outright, so they still appear in the report and a reviewer can see them.
SETUP_PATHS = (
    "CLAUDE.md",
    ".gitignore",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".mcp.json",
)

#: Never audited: the plugin's own directory. A developer editing `plan.md` or a `pull`
#: writing a lock file is not a scope violation. Package integrity is
#: checked separately, against the lock file.
_EXCLUDED_PREFIX = paths.CONFIG_DIR_NAME + "/"


class AuditReport:
    """Everything the audit found, ready to render as Markdown or JSON."""

    __slots__ = (
        "base",
        "base_available",
        "enforcement",
        "forbidden",
        "in_scope",
        "incidental",
        "integrity",
        "notes",
        "out_of_scope",
        "role",
        "scope_defined",
        "task_id",
    )

    def __init__(self) -> None:
        self.task_id: Optional[str] = None
        self.role: Optional[str] = None
        self.enforcement: str = "strict"
        #: True when the task defines a scope for this role at all.
        self.scope_defined: bool = False
        self.in_scope: list[str] = []
        self.out_of_scope: list[str] = []
        #: `(path, pattern)` — the change matched an explicit deny glob.
        self.forbidden: list[tuple[str, str]] = []
        self.incidental: list[str] = []
        self.integrity: Optional[lock.IntegrityReport] = None
        self.base: Optional[str] = None
        self.base_available: bool = False
        self.notes: list[str] = []

    @property
    def violations(self) -> int:
        """How many findings make this audit a failure."""
        count = len(self.forbidden) + len(self.out_of_scope)
        if self.integrity is not None and not self.integrity.clean:
            count += (
                len(self.integrity.changed)
                + len(self.integrity.missing)
                + len(self.integrity.unlocked)
            )
        return count

    @property
    def clean(self) -> bool:
        return self.violations == 0

    @property
    def changed_total(self) -> int:
        return (
            len(self.in_scope) + len(self.out_of_scope) + len(self.forbidden) + len(self.incidental)
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "task_id": self.task_id,
            "role": self.role,
            "enforcement": self.enforcement,
            "scope_defined": self.scope_defined,
            "base": self.base,
            "base_available": self.base_available,
            "in_scope": self.in_scope,
            "out_of_scope": self.out_of_scope,
            "forbidden": [{"path": p, "pattern": q} for p, q in self.forbidden],
            "incidental": self.incidental,
            "integrity": self.integrity.as_dict() if self.integrity else None,
            "violations": self.violations,
            "clean": self.clean,
            "notes": self.notes,
        }


def _collect_paths(root: Path, base: Optional[str]) -> tuple[list[str], bool, list[str]]:
    """Gather changed paths from the working tree and, when possible, from the base diff."""
    notes: list[str] = []
    working, ok = gitcmd.changed_paths(root)
    if not ok:
        notes.append("git status could not be read; the audit covers nothing.")
        return [], False, notes

    combined = set(working)
    base_available = False
    if base:
        diff, available = gitcmd.merge_base_diff(root, base)
        base_available = available
        if available:
            combined.update(diff)
        else:
            notes.append(
                f"The base ref {base!r} does not resolve here, so the audit covers the "
                "working tree only. In CI, fetch the base branch first."
            )
    return sorted(combined), base_available, notes


def audit(
    root: Path,
    *,
    task: Optional[Mapping[str, Any]] = None,
    role: Optional[str] = None,
    profile: Optional[Mapping[str, Any]] = None,
    base: Optional[str] = None,
    package_dir: Optional[Path] = None,
    lock_document: Optional[Mapping[str, Any]] = None,
) -> AuditReport:
    """Cross the repository's changes with the role's scope.

    With no task, the report carries only the note that nothing was checked: the audit
    2.10 makes "no task found" a skip rather than a failure, so a branch that is not
    working on a package does not turn the gate red.
    """
    report = AuditReport()
    changed, base_available, notes = _collect_paths(root, base)
    report.base = base
    report.base_available = base_available
    report.notes.extend(notes)

    if task is None:
        report.notes.append("No task package is active, so no scope check was performed.")
        return report

    report.task_id = str(task.get("id") or "") or None
    report.role = role
    report.enforcement = str(task.get("enforcement") or "strict")

    scope = task.get("scope") or {}
    role_scope = scope.get(role) if role and isinstance(scope, Mapping) else None
    allow: Sequence[str] = []
    deny: Sequence[str] = []
    if isinstance(role_scope, Mapping):
        report.scope_defined = True
        allow = [p for p in (role_scope.get("allow") or []) if isinstance(p, str)]
        deny = [p for p in (role_scope.get("deny") or []) if isinstance(p, str)]
    else:
        report.notes.append(
            f"The task defines no scope for role {role!r}, so changes are reported "
            "without a scope verdict."
        )

    incidental = (
        list(DEFAULT_INCIDENTAL)
        + list(SETUP_PATHS)
        + config_mod.paths_of(profile or {}, "incidental_allow")
    )

    for rel in changed:
        if rel.startswith(_EXCLUDED_PREFIX) or rel == paths.CONFIG_DIR_NAME:
            continue
        pattern = globs.matching_pattern(rel, deny)
        if pattern:
            report.forbidden.append((rel, pattern))
            continue
        if allow and globs.match_any(rel, allow):
            report.in_scope.append(rel)
            continue
        if globs.match_any(rel, incidental):
            report.incidental.append(rel)
            continue
        if not report.scope_defined:
            # No verdict is possible; count it as in scope so the audit does not fail on
            # a configuration gap. The note above already says the scope is missing.
            report.in_scope.append(rel)
            continue
        report.out_of_scope.append(rel)

    if package_dir is not None and lock_document:
        report.integrity = lock.verify(
            package_dir,
            lock_document,
            present=_researcher_present(package_dir),
        )

    report.in_scope.sort()
    report.out_of_scope.sort()
    report.incidental.sort()
    report.forbidden.sort()
    return report


def _researcher_present(package_dir: Path) -> list[str]:
    from .package import researcher_files  # local import keeps the layer graph acyclic

    return researcher_files(package_dir)


def render_markdown(report: AuditReport, t: Translator) -> str:
    """Render the report for a terminal, a CI job summary or `verification.md`."""
    lines: list[str] = []
    if report.task_id:
        lines.append(t("audit.heading", task_id=report.task_id, role=report.role or "-"))
    else:
        lines.append(t("audit.heading_no_task"))

    if report.clean:
        lines.append(t("audit.clean", count=report.changed_total))
    else:
        lines.append(t("audit.violations", count=report.violations))

    if report.forbidden:
        lines.append("")
        lines.append(t("audit.section_forbidden"))
        for path, pattern in report.forbidden:
            lines.append(f"- `{path}` — `{pattern}`")

    if report.out_of_scope:
        lines.append("")
        lines.append(t("audit.section_out_of_scope"))
        for path in report.out_of_scope:
            lines.append(f"- `{path}`")

    if report.integrity is not None and not report.integrity.clean:
        lines.append("")
        lines.append(t("audit.section_integrity"))
        for path in report.integrity.changed:
            lines.append(f"- `{path}` — {t('audit.integrity_changed')}")
        for path in report.integrity.missing:
            lines.append(f"- `{path}` — {t('audit.integrity_missing')}")
        for path in report.integrity.unlocked:
            lines.append(f"- `{path}` — {t('audit.integrity_unlocked')}")

    if report.in_scope:
        lines.append("")
        lines.append(t("audit.section_in_scope", count=len(report.in_scope)))
        for path in report.in_scope[:20]:
            lines.append(f"- `{path}`")
        if len(report.in_scope) > 20:
            lines.append(t("audit.more", count=len(report.in_scope) - 20))

    if report.incidental:
        lines.append("")
        lines.append(t("audit.section_incidental"))
        for path in report.incidental:
            lines.append(f"- `{path}`")

    for note in report.notes:
        lines.append("")
        lines.append(f"> {note}")

    return "\n".join(lines) + "\n"


def render_json(report: AuditReport) -> dict[str, Any]:
    return report.as_dict()
