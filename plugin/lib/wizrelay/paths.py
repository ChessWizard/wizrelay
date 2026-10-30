"""Repository roots, persona detection and cache locations.

This is the first service layer module: it touches the filesystem but runs no subprocess
and makes no network call.

Three jobs:

* **Find the repository root.** Everything else is relative to it: scope globs, deny
  rules, the `.wizrelay/` directory.
* **Decide the persona**. `.wizrelay/config.json` means developer,
  `wizrelay-hub.json` at the root means hub, neither means silence. Invariant I5 makes
  that silence absolute: no output, no file written, no network.
* **Locate caches.** One hub per directory, keyed by hub identity, so two hubs on one
  machine never mix (invariant I4).
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Optional

__all__ = [
    "CONFIG_DIR_NAME",
    "DEV_CONFIG",
    "HUB_MARKER",
    "PERSONA_DEV",
    "PERSONA_HUB",
    "PERSONA_NONE",
    "Context",
    "cache_root",
    "data_root",
    "detect",
    "find_repo_root",
    "heartbeat_dir",
    "hub_cache_dir",
    "hub_identity",
    "is_inside",
    "rel_posix",
]

CONFIG_DIR_NAME = ".wizrelay"
DEV_CONFIG = "config.json"
DEV_LOCAL_CONFIG = "config.local.json"
HUB_MARKER = "wizrelay-hub.json"
ACTIVE_TASK_FILE = ".active-task"
PROFILE_FILE = "profile.json"
PROTOCOL_FILE = "PROTOCOL.md"
TASKS_DIR = "tasks"

PERSONA_DEV = "developer"
PERSONA_HUB = "hub"
PERSONA_NONE = "none"

# Developer-owned files inside a package: never copied from the hub, never overwritten
# (invariant I9).
DEVELOPER_FILES = ("plan.md", "questions.md", "verification.md")
DEVELOPER_DIRS = ("notes",)


def find_repo_root(start: Optional[Path] = None) -> Optional[Path]:
    """Walk up from `start` to the directory containing `.git`.

    Works in a git worktree, where `.git` is a file rather than a directory. Returns None
    outside a repository, which every caller treats as "not our business".
    """
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _search_up(start: Path, relative: str) -> Optional[Path]:
    """Find the nearest ancestor (including `start`) that contains `relative`."""
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / relative).exists():
            return candidate
    return None


class Context:
    """Where we are and what that means.

    `root` is the directory the persona was detected at, which is the repository root in
    practice. Scope globs and deny rules are relative to it.
    """

    __slots__ = ("cwd", "persona", "root")

    def __init__(self, persona: str, root: Optional[Path], cwd: Path) -> None:
        self.persona = persona
        self.root = root
        self.cwd = cwd

    @property
    def is_dev(self) -> bool:
        return self.persona == PERSONA_DEV

    @property
    def is_hub(self) -> bool:
        return self.persona == PERSONA_HUB

    @property
    def is_silent(self) -> bool:
        """True when the plugin must do nothing at all (invariant I5)."""
        return self.persona == PERSONA_NONE

    @property
    def config_dir(self) -> Optional[Path]:
        return self.root / CONFIG_DIR_NAME if self.root else None

    @property
    def tasks_dir(self) -> Optional[Path]:
        return self.root / CONFIG_DIR_NAME / TASKS_DIR if self.root else None

    @property
    def hub_tasks_dir(self) -> Optional[Path]:
        return self.root / TASKS_DIR if self.root else None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Context {self.persona} root={self.root}>"


def detect(cwd: Optional[Path] = None) -> Context:
    """Detect the persona for `cwd`.

    The search walks up, so a session started in a subdirectory of a connected repository
    still resolves — appendix B4 requires it for `pre-edit` with a relative path.

    Developer wins when both markers are present: a hub that someone also connected as a
    developer repository is a misconfiguration, and the developer persona is the one with
    the protective hooks.
    """
    here = (cwd or Path.cwd()).resolve()

    dev_root = _search_up(here, f"{CONFIG_DIR_NAME}/{DEV_CONFIG}")
    if dev_root is not None:
        return Context(PERSONA_DEV, dev_root, here)

    hub_root = _search_up(here, HUB_MARKER)
    if hub_root is not None:
        return Context(PERSONA_HUB, hub_root, here)

    return Context(PERSONA_NONE, None, here)


def is_inside(root: Path, candidate: Path) -> bool:
    """True when `candidate` is `root` or below it.

    Handles the two Windows cases task 2.6 calls out, both of which must read as "outside
    the repository" rather than raising:

    * a different drive letter, where `relative_to` raises `ValueError`
    * a UNC path such as ``\\\\server\\share``, whose anchor differs from any local root
    """
    try:
        root_resolved = root.resolve()
        candidate_resolved = candidate.resolve()
    except (OSError, RuntimeError):
        return False
    if root_resolved.anchor != candidate_resolved.anchor:
        return False
    try:
        candidate_resolved.relative_to(root_resolved)
    except ValueError:
        return False
    return True


def rel_posix(root: Path, candidate: Path) -> Optional[str]:
    """Repository-relative POSIX path, or None when `candidate` is outside `root`."""
    if not is_inside(root, candidate):
        return None
    relative = candidate.resolve().relative_to(root.resolve())
    return relative.as_posix()


def cache_root() -> Path:
    """The per-user cache directory, following each platform's convention.

    `XDG_CACHE_HOME` wins when set, on every platform, because a user who sets it means
    it. Then `%LOCALAPPDATA%` on Windows, `~/Library/Caches` on macOS, `~/.cache`
    elsewhere.
    """
    override = os.environ.get("WIZRELAY_CACHE_DIR")
    if override:
        return Path(override).expanduser()

    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg).expanduser() / "wizrelay"

    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            return Path(local) / "wizrelay" / "Cache"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "wizrelay"

    return Path.home() / ".cache" / "wizrelay"


def data_root() -> Path:
    """Where state that must survive a plugin update lives.

    Claude Code exports `CLAUDE_PLUGIN_DATA` to every hook process and guarantees it
    survives plugin updates, which is exactly what the heartbeat needs. Outside a hook —
    in CI, or from a terminal — it falls back to the cache directory.
    """
    plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA")
    if plugin_data:
        return Path(plugin_data)
    return cache_root()


def heartbeat_dir() -> Path:
    """Where `SessionStart` records that it ran (invariant I13)."""
    return data_root() / "heartbeats"


_CREDENTIAL_URL = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://[^/@]*:[^/@]*@")
_SUFFIX_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def has_embedded_credentials(url: str) -> bool:
    """True for a URL carrying `user:token@`, which is rejected outright.

    An SSH URL such as `git@github.com:acme/hub.git` has a user but no password, so it is
    not treated as carrying a credential.
    """
    return bool(_CREDENTIAL_URL.match(url.strip()))


def hub_identity(url_or_path: str) -> str:
    """A stable, readable identity for one hub (invariant I4).

    The identity is `<readable-suffix>-<hash8>`:

    * the readable suffix makes a cache directory recognisable when a user looks at it
    * the hash makes collisions between two hubs with the same repository name impossible

    Normalisation first, so `git@github.com:acme/hub.git`,
    `https://github.com/acme/hub.git` and `https://github.com/acme/hub/` all produce one
    identity: they are the same hub, and a user switching protocol should not re-clone.
    """
    raw = url_or_path.strip()
    normalized = raw.rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[: -len(".git")]
    normalized = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", "", normalized)
    normalized = re.sub(r"^[^/@]+@", "", normalized)
    normalized = normalized.replace(":", "/")
    normalized = normalized.lower()

    tail = normalized.rsplit("/", 2)
    suffix = "-".join(part for part in tail[-2:] if part) or "hub"
    suffix = _SUFFIX_SAFE.sub("-", suffix).strip("-")[:40] or "hub"

    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:8]
    return f"{suffix}-{digest}"


def hub_cache_dir(url_or_path: str) -> Path:
    """The cache directory for one hub. Two hubs never share one (invariant I4)."""
    return cache_root() / "hubs" / hub_identity(url_or_path)


def split_persona_paths(root: Path) -> tuple[Path, Path]:
    """Return `(config_dir, tasks_dir)` for a developer repository."""
    config_dir = root / CONFIG_DIR_NAME
    return config_dir, config_dir / TASKS_DIR
