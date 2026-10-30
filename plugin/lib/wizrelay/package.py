"""Finding, classifying and safely copying task packages.

A package is a directory `tasks/<ID>-<slug>/` in the hub. This module owns
three jobs:

* **Finding one** from whatever the user typed: a canonical identifier, a raw tracker
  reference, or the directory name. An ambiguous match is an error rather than a guess,
  because pulling the wrong analysis is worse than asking.
* **Classifying its files** into researcher-owned, developer-owned and private. The
  classification is what enforces invariants I8 and I9: a dotted file never leaves the hub,
  and a developer file is never overwritten.
* **Copying it safely.** A hub is a git repository someone else writes to, so every file
  it offers is treated as untrusted input. Symbolic links, absolute
  paths, `..` segments, device files and oversized payloads are refused by name.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Optional

from . import SCHEMA_VERSION, lock, trackers
from .errors import UsageError, ValidationError
from .textformats import slugify

__all__ = [
    "DEVELOPER_DIRS",
    "DEVELOPER_FILES",
    "MAX_FILE_BYTES",
    "MAX_PACKAGE_BYTES",
    "REQUIRED_FILES",
    "CopyPlan",
    "classify",
    "copy_package",
    "find_package",
    "list_packages",
    "read_task",
    "researcher_files",
    "scaffold_names",
    "write_task",
]

#: Developer-owned names. Never copied from the hub, never overwritten,
#: even when the hub happens to contain a file with the same name.
DEVELOPER_FILES = ("plan.md", "questions.md", "verification.md")
DEVELOPER_DIRS = ("notes",)

#: Researcher files a published package must contain.
REQUIRED_FILES = ("task.json", "research.md", "scope.md", "acceptance.md", "decisions.md")

TASK_FILE = "task.json"

#: Copy limits. A package is analysis, not an asset bundle; anything larger
#: is a mistake or an attack, and both deserve the same refusal.
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_PACKAGE_BYTES = 20 * 1024 * 1024

RESEARCHER = "researcher"
DEVELOPER = "developer"
PRIVATE = "private"


def classify(relative: str) -> str:
    """Classify one package-relative path.

    * `private` — any path with a dot-prefixed component. Never published, never copied
      (invariant I8). `.validation.md` and `.notes/` live here, and so does `.lock.json`,
      which the developer side writes itself.
    * `developer` — `plan.md`, `questions.md`, `verification.md`, `notes/**`.
    * `researcher` — everything else.
    """
    parts = [part for part in relative.replace("\\", "/").split("/") if part]
    if not parts:
        return PRIVATE
    if any(part.startswith(".") for part in parts):
        return PRIVATE
    if parts[0] in DEVELOPER_DIRS:
        return DEVELOPER
    if len(parts) == 1 and parts[0] in DEVELOPER_FILES:
        return DEVELOPER
    return RESEARCHER


def _iter_relative(root: Path) -> Iterable[tuple[str, Path]]:
    """Walk `root`, yielding `(relative_posix, absolute)` for every entry.

    `Path.rglob` follows no symbolic links when matching, but it does *list* them, which is
    what the copy safety check needs: a link has to be seen in order to be refused.
    """
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        yield relative, path


def researcher_files(package_dir: Path) -> list[str]:
    """Researcher-owned relative paths present in a package directory, sorted."""
    out: list[str] = []
    for relative, path in _iter_relative(package_dir):
        if path.is_dir():
            continue
        if classify(relative) == RESEARCHER:
            out.append(relative)
    return sorted(out)


def read_task(package_dir: Path) -> dict[str, Any]:
    """Read and parse `task.json`, with a message that names the file on failure."""
    path = package_dir / TASK_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise UsageError(
            f"{TASK_FILE} is missing from {package_dir.name}.",
            reason="Every package needs a task.json.",
            remedy="Run `wizrelay hub new <ref>` to scaffold one, or add the file by hand.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"{path.name} is not valid JSON.",
            reason=f"line {exc.lineno}, column {exc.colno}: {exc.msg}",
            remedy=f"Fix the syntax in {path}.",
        ) from exc
    if not isinstance(data, dict):
        raise ValidationError(f"{path.name} must contain a JSON object.")
    return data


def write_task(package_dir: Path, document: Mapping[str, Any]) -> None:
    """Write `task.json` in the canonical format.

    `indent=2`, `ensure_ascii=False` and a trailing newline keep Turkish titles readable
    and keep diffs to the lines that actually changed.
    """
    path = package_dir / TASK_FILE
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def list_packages(tasks_root: Path) -> list[Path]:
    """Every package directory under `tasks/`, sorted, skipping unsafe names."""
    if not tasks_root.is_dir():
        return []
    return sorted(
        entry
        for entry in tasks_root.iterdir()
        if entry.is_dir()
        and not entry.name.startswith(".")
        and trackers.is_safe_folder_name(entry.name)
    )


def _candidate_matches(name: str, needles: Sequence[str]) -> bool:
    """Whether a package directory name matches one of these references.

    Three ways to match, in decreasing precision:

    * the whole name, so a directory name works as a reference
    * the name's leading identifier, so `CU-86c1abcd` finds `CU-86c1abcd-quota`
    * a dash-delimited token anywhere in the name, so the **raw** reference `86c1abcd`
      finds `CU-86c1abcd-quota` even though it is not a prefix

    The third rule is why a minimum length applies: a two-character token would match
    almost any slug. An ambiguous result is an error rather than a guess, which is the
    safety net for the looser rules.
    """
    lowered = name.lower()
    tokens = set(lowered.split("-"))
    for needle in needles:
        if not needle:
            continue
        candidate = needle.lower()
        if lowered == candidate or lowered.startswith(candidate + "-"):
            return True
        if len(candidate) >= 3 and candidate in tokens:
            return True
    return False


def find_package(
    tasks_root: Path,
    *,
    canonical_id: str = "",
    raw_ref: str = "",
    folder: str = "",
) -> Path:
    """Locate one package directory.

    Matching accepts, in order of precision: an exact directory name, the canonical
    identifier as a directory prefix, then the raw tracker reference as a prefix. Appendix
    B2 #2 requires `pull 86c1abcd`, `pull CU-86c1abcd` and `pull <folder>` to find the same
    package, and requires more than one match to be an error.
    """
    packages = list_packages(tasks_root)
    if not packages:
        raise UsageError(
            "No task packages were found.",
            reason=f"{tasks_root} contains no package directory.",
            remedy="Publish a package first, or check that the hub path is correct.",
        )

    if folder:
        exact = [p for p in packages if p.name == folder]
        if exact:
            return exact[0]

    for needles in ([canonical_id], [raw_ref]):
        matches = [p for p in packages if _candidate_matches(p.name, needles)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise UsageError(
                f"{(canonical_id or raw_ref)!r} matches more than one package.",
                reason="Matches: " + ", ".join(p.name for p in matches),
                remedy="Pass the full directory name instead of the identifier.",
            )

    reference = folder or canonical_id or raw_ref
    raise UsageError(
        f"No package found for {reference!r}.",
        reason=f"Nothing under {tasks_root} matches that reference.",
        remedy="Run `wizrelay hub list` to see the available packages.",
    )


class CopyPlan:
    """What a copy would do, and what it refused.

    Produced before anything is written, so `pull` can report a refusal without having
    left a half-copied package behind.
    """

    __slots__ = ("files", "refused", "skipped", "total_bytes")

    def __init__(self) -> None:
        #: Relative paths that will be copied.
        self.files: list[str] = []
        #: `(relative_path, reason)` for every entry refused by a safety rule.
        self.refused: list[tuple[str, str]] = []
        #: `(relative_path, reason)` for entries intentionally not copied.
        self.skipped: list[tuple[str, str]] = []
        self.total_bytes = 0

    @property
    def ok(self) -> bool:
        return not self.refused

    def as_dict(self) -> dict[str, Any]:
        return {
            "files": self.files,
            "refused": [{"path": p, "reason": r} for p, r in self.refused],
            "skipped": [{"path": p, "reason": r} for p, r in self.skipped],
            "total_bytes": self.total_bytes,
        }


def plan_copy(source: Path, *, include_developer: bool = False) -> CopyPlan:
    """Decide what may be copied out of a hub package, refusing anything unsafe.

    The refusal list is deliberately specific: the error has to name
    the file, because "the package is unsafe" is not actionable.
    """
    plan = CopyPlan()
    source = source.resolve()

    for relative, path in _iter_relative(source):
        # A symbolic link is refused whether it points inside or outside the package: a
        # link inside a copied tree is a path that resolves differently on the other
        # machine, and that is not something a data format should carry.
        if path.is_symlink():
            plan.refused.append((relative, "symbolic link"))
            continue
        if path.is_dir():
            continue
        if ".." in relative.split("/") or relative.startswith("/"):
            plan.refused.append((relative, "path escapes the package directory"))
            continue
        if not path.is_file():
            plan.refused.append((relative, "not a regular file"))
            continue

        kind = classify(relative)
        if kind == PRIVATE:
            plan.skipped.append((relative, "private to the hub"))
            continue
        if kind == DEVELOPER and not include_developer:
            plan.skipped.append((relative, "developer-owned"))
            continue

        try:
            size = path.stat().st_size
        except OSError as exc:
            plan.refused.append((relative, f"cannot be read ({exc.strerror or exc})"))
            continue

        if size > MAX_FILE_BYTES:
            plan.refused.append(
                (relative, f"{size} bytes exceeds the {MAX_FILE_BYTES}-byte file limit")
            )
            continue

        plan.total_bytes += size
        if plan.total_bytes > MAX_PACKAGE_BYTES:
            plan.refused.append(
                (relative, f"package exceeds the {MAX_PACKAGE_BYTES}-byte total limit")
            )
            continue

        plan.files.append(relative)

    plan.files.sort()
    return plan


def copy_package(
    source: Path,
    destination: Path,
    *,
    plan: Optional[CopyPlan] = None,
) -> tuple[dict[str, str], list[str]]:
    """Copy the researcher files of a package and return `(digests, removed)`.

    * Developer files are never written, so `plan.md` keeps whatever the developer wrote
      (invariant I9).
    * A researcher file that no longer exists in the hub is deleted locally, which is
      appendix B2 #6: deleting a file in the hub has to propagate.
    * Digests are returned rather than written, so the caller composes the lock file and
      one function keeps one responsibility.
    """
    plan = plan or plan_copy(source)
    if not plan.ok:
        first_path, first_reason = plan.refused[0]
        raise ValidationError(
            f"Refusing to copy {source.name}: {first_path} is {first_reason}.",
            reason=f"{len(plan.refused)} entr"
            f"{'y' if len(plan.refused) == 1 else 'ies'} failed the copy safety rules.",
            remedy="Remove the offending entry from the hub package and publish again.",
        )

    destination.mkdir(parents=True, exist_ok=True)

    wanted = set(plan.files)
    existing = set(researcher_files(destination))
    removed = sorted(existing - wanted)
    for relative in removed:
        target = destination / relative
        try:
            target.unlink()
        except OSError:  # pragma: no cover - a locked file on Windows
            pass

    digests: dict[str, str] = {}
    for relative in plan.files:
        src = source / relative
        dst = destination / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        digests[relative] = lock.digest_file(dst)

    # Clean up directories the removal emptied, so a deleted `roles/` does not linger.
    for directory in sorted(
        (p for p in destination.rglob("*") if p.is_dir()),
        key=lambda p: len(p.parts),
        reverse=True,
    ):
        try:
            next(directory.iterdir())
        except StopIteration:
            directory.rmdir()
        except OSError:  # pragma: no cover
            pass

    return digests, removed


def scaffold_names(canonical_id: str, title: str) -> tuple[str, str]:
    """Return `(folder_name, slug)` for a new package."""
    slug = slugify(title)
    return trackers.task_folder_name(canonical_id, slug), slug


def new_task_document(
    *,
    canonical_id: str,
    ref: str,
    title: str,
    roles: Sequence[str],
    tracker_type: str,
    url: Optional[str] = None,
    enforcement: str = "strict",
) -> dict[str, Any]:
    """Build the `task.json` a fresh package starts from.

    Scope is a placeholder per role, not an empty list: `hub validate` rejects
    `{{...}}` markers, so the scaffold fails validation until a researcher fills it in.
    That is the point — a package nobody completed must not be publishable.
    """
    tracker_block: dict[str, Any] = {"type": tracker_type}
    if ref:
        tracker_block["ref"] = ref
    if url:
        tracker_block["url"] = url

    return {
        "schema_version": SCHEMA_VERSION,
        "id": canonical_id,
        "tracker": tracker_block,
        "title": title,
        "slug": slugify(title),
        "version": 0,
        "status": "draft",
        "roles": list(roles),
        "enforcement": enforcement,
        "scope": {role: {"allow": ["{{path/to/allow/**}}"], "deny": []} for role in roles},
        "routing": {
            "signals": {"complexity": "medium", "risk": "medium", "ambiguity": "medium"},
            "role_signals": {},
            "overrides": {},
        },
        "changelog": [],
    }


# --------------------------------------------------------------------------------------
# Active task resolution
# --------------------------------------------------------------------------------------


def find_by_branch(tasks_root: Path, branch: str) -> Optional[Path]:
    """Find the package whose identifier appears in a branch name.

    Branch names carry the task identifier in practice — `feature/CU-86c1abcd-quota`,
    `bugfix/GH-123`. The match is case-insensitive and is made against the package
    directory name's identifier part, so `feature/cu-86c1abcd-x` resolves.

    `refs/heads/` is stripped first: CI hands over a full ref, and the resolution
    requires that form to work.
    """
    if not branch:
        return None
    name = branch.strip()
    for prefix in ("refs/heads/", "refs/remotes/origin/"):
        if name.startswith(prefix):
            name = name[len(prefix) :]
    folded = name.lower()

    best: Optional[Path] = None
    best_length = 0
    for candidate in list_packages(tasks_root):
        identifier = candidate.name.split("-")[0].lower()
        # Compare against the whole directory name too, so a branch named after the
        # package directory resolves even when the identifier alone is ambiguous.
        for token in (candidate.name.lower(), identifier):
            if token and token in folded and len(token) > best_length:
                best = candidate
                best_length = len(token)
    return best


def resolve_active(
    tasks_root: Path,
    *,
    pointer: Optional[Path] = None,
    branch: Optional[str] = None,
) -> tuple[Optional[Path], str]:
    """Decide which package is active, and say how it was decided.

    Order:

    1. the `.wizrelay/.active-task` pointer, which `pull` and `activate` write
    2. the task identifier in the current branch name

    The pointer wins, because a developer who ran `wizrelay activate` has stated an
    intention that a branch name should not override. A worktree with no pointer still
    works through the branch name, which is the case the second rule exists for.

    Returns `(package_dir_or_None, source)` where `source` is `pointer`, `branch` or
    `none`.
    """
    if pointer is not None and pointer.is_file():
        try:
            name = pointer.read_text(encoding="utf-8").strip()
        except OSError:
            name = ""
        if name:
            candidate = tasks_root / name
            if candidate.is_dir():
                return candidate, "pointer"

    if branch:
        found = find_by_branch(tasks_root, branch)
        if found is not None:
            return found, "branch"

    return None, "none"
