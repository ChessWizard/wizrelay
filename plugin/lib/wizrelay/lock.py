"""Lock files: what was pulled, from where, and whether it still matches.

`.lock.json` sits inside the pulled package directory and records the hub commit, the
package version and a sha256 for every researcher file. It is what makes
invariant I12 (traceability) and the integrity half of `audit` possible: at any later
point the plugin can say "this file is not what the researcher published".

Hashing is over raw bytes, with one normalisation: a CRLF line ending is converted to LF
before hashing. Without that, a Windows checkout of the hub and a macOS checkout of the
same commit would disagree on every digest, and `sync` would report the whole package as
corrupted on every run.

This module is pure apart from reading the bytes it is handed a path to; it writes no
files itself.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Optional

from . import SCHEMA_VERSION

__all__ = [
    "LOCK_FILENAME",
    "IntegrityReport",
    "build",
    "digest_bytes",
    "digest_file",
    "load",
    "serialize",
    "verify",
]

LOCK_FILENAME = ".lock.json"

_CHUNK = 1 << 16


def digest_bytes(data: bytes) -> str:
    """sha256 of `data`, with CRLF normalised to LF so platforms agree."""
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def digest_file(path: Path) -> str:
    """sha256 of a file, read in chunks so a large attachment does not sit in memory.

    CRLF normalisation has to survive chunk boundaries: a chunk ending in `\\r` followed by
    a chunk starting with `\\n` is one line ending. The carry byte below handles that.
    """
    hasher = hashlib.sha256()
    carry = b""
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(_CHUNK)
            if not chunk:
                break
            buffer = carry + chunk
            carry = b""
            if buffer.endswith(b"\r"):
                carry = b"\r"
                buffer = buffer[:-1]
            hasher.update(buffer.replace(b"\r\n", b"\n"))
    if carry:
        hasher.update(carry)
    return hasher.hexdigest()


def build(
    *,
    task_id: str,
    folder: str,
    version: int,
    files: Mapping[str, str],
    pulled_at: str,
    tracker_ref: Optional[str] = None,
    title: Optional[str] = None,
    hub_commit: Optional[str] = None,
    hub_id: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    routing: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Assemble a lock document. Keys with no value are omitted, not set to null."""
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "folder": folder,
        "version": version,
        "pulled_at": pulled_at,
        "files": {path: files[path] for path in sorted(files)},
    }
    optional = {
        "tracker_ref": tracker_ref,
        "title": title,
        "hub_commit": hub_commit,
        "hub_id": hub_id,
        "role": role,
        "status": status,
    }
    for key, value in optional.items():
        if value:
            document[key] = value
    if routing:
        document["routing"] = dict(routing)
    # Stable key order keeps diffs small when only the hashes change.
    order = [
        "schema_version",
        "task_id",
        "tracker_ref",
        "title",
        "folder",
        "version",
        "status",
        "hub_commit",
        "hub_id",
        "pulled_at",
        "role",
        "files",
        "routing",
    ]
    return {key: document[key] for key in order if key in document}


def serialize(document: Mapping[str, Any]) -> str:
    """Render a lock file the way every JSON this project writes is rendered."""
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def load(path: Path) -> Optional[dict[str, Any]]:
    """Read a lock file, returning None when it is absent or unreadable.

    A corrupt lock must not break a session: callers treat None as "no lock", which makes
    the next `pull` or `sync` rewrite it.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


class IntegrityReport:
    """The difference between what the lock recorded and what is on disk now."""

    __slots__ = ("changed", "missing", "unlocked")

    def __init__(
        self,
        changed: Sequence[str] = (),
        missing: Sequence[str] = (),
        unlocked: Sequence[str] = (),
    ) -> None:
        #: Locked files whose contents no longer match the recorded digest.
        self.changed: list[str] = sorted(changed)
        #: Locked files that are gone.
        self.missing: list[str] = sorted(missing)
        #: Researcher files present on disk that the lock does not mention.
        self.unlocked: list[str] = sorted(unlocked)

    @property
    def clean(self) -> bool:
        return not (self.changed or self.missing or self.unlocked)

    def as_dict(self) -> dict[str, list[str]]:
        return {"changed": self.changed, "missing": self.missing, "unlocked": self.unlocked}

    def __bool__(self) -> bool:
        return not self.clean

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<IntegrityReport changed={len(self.changed)} missing={len(self.missing)} "
            f"unlocked={len(self.unlocked)}>"
        )


def verify(
    package_dir: Path,
    document: Mapping[str, Any],
    *,
    present: Optional[Iterable[str]] = None,
) -> IntegrityReport:
    """Compare the lock's digests against the files in `package_dir`.

    `present` is the set of researcher-owned relative paths currently on disk. When it is
    given, files on disk that the lock does not mention are reported as `unlocked` — that
    is how a researcher file someone added by hand in a developer repository is caught.
    """
    locked: Mapping[str, Any] = document.get("files") or {}
    changed: list[str] = []
    missing: list[str] = []

    for rel, expected in locked.items():
        path = package_dir / rel
        if not path.is_file():
            missing.append(rel)
            continue
        if digest_file(path) != expected:
            changed.append(rel)

    unlocked: list[str] = []
    if present is not None:
        unlocked = [rel for rel in present if rel not in locked]

    return IntegrityReport(changed=changed, missing=missing, unlocked=unlocked)


def diff_versions(
    old: Optional[Mapping[str, Any]], new: Mapping[str, Any]
) -> tuple[list[str], list[str], list[str]]:
    """Return `(added, modified, removed)` between two locks, for the `sync` summary."""
    old_files: Mapping[str, Any] = (old or {}).get("files") or {}
    new_files: Mapping[str, Any] = new.get("files") or {}
    added = sorted(set(new_files) - set(old_files))
    removed = sorted(set(old_files) - set(new_files))
    modified = sorted(
        path for path in set(new_files) & set(old_files) if new_files[path] != old_files[path]
    )
    return added, modified, removed
