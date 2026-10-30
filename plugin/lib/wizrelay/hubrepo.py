"""Resolving the team hub to a directory on disk.

Three modes, in the order `config.json` selects them:

1. **A local working copy** (`hub.path`). The hub is a checkout the user maintains. It is
   read and never touched: no fetch, no reset, no clone. Someone with the hub open in an
   editor must not have their working tree moved under them.
2. **A cached clone** (`hub.repo`). A shallow clone lives in a cache directory keyed by
   hub identity, so two hubs on one machine never share state (invariant I4). It is
   refreshed when the TTL has expired.
3. **Nothing configured.** Every caller degrades: `pull` explains what to configure,
   hooks stay silent.

The TTL rule has one trap worth naming. `fetch_ttl_minutes: 0` means "fetch every time",
and the obvious `ttl = config.get("fetch_ttl_minutes") or 10` turns that 0 into 10,
silently disabling the setting. The prototype had exactly that bug, so the value is read
with an explicit `None` check and `tests/unit/test_hubrepo.py` pins it.

Network rules:

* a hook **never clones** — cloning is slow, interactive and can prompt for credentials
* a hook may fetch, once the TTL has expired, inside a 4-second budget
* any network failure is swallowed: a stale hub is better than a broken session
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Optional

from . import gitcmd, paths
from .errors import UsageError

__all__ = ["HubHandle", "local_policy", "read_policy", "resolve"]

_STAMP_FILE = ".wizrelay-fetch-stamp"
DEFAULT_TTL_MINUTES = 10


class HubHandle:
    """Where the hub is, how it got there, and what went wrong on the way."""

    __slots__ = ("commit", "identity", "notes", "path", "read_only", "source")

    def __init__(
        self,
        path: Optional[Path],
        identity: str,
        source: str,
        *,
        commit: Optional[str] = None,
        read_only: bool = False,
        notes: Optional[list[str]] = None,
    ) -> None:
        #: None when the hub could not be resolved at all.
        self.path = path
        self.identity = identity
        #: `local`, `cache` or `none`.
        self.source = source
        self.commit = commit
        #: True for a user's own working copy, which must never be modified.
        self.read_only = read_only
        self.notes: list[str] = notes or []

    @property
    def available(self) -> bool:
        return self.path is not None and self.path.is_dir()

    @property
    def tasks_dir(self) -> Optional[Path]:
        return self.path / "tasks" if self.path else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path) if self.path else None,
            "identity": self.identity,
            "source": self.source,
            "commit": self.commit,
            "read_only": self.read_only,
            "notes": self.notes,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<HubHandle {self.source} {self.path}>"


def ttl_minutes(config: Mapping[str, Any]) -> int:
    """Read `fetch_ttl_minutes`, treating a present 0 as 0 rather than as "unset".

    >>> ttl_minutes({"fetch_ttl_minutes": 0})
    0
    >>> ttl_minutes({})
    10
    """
    value = config.get("fetch_ttl_minutes")
    if value is None:
        return DEFAULT_TTL_MINUTES
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return DEFAULT_TTL_MINUTES
    return max(0, parsed)


def _stamp_path(cache_dir: Path) -> Path:
    return cache_dir.parent / f"{cache_dir.name}{_STAMP_FILE}"


def _is_fresh(cache_dir: Path, minutes: int) -> bool:
    """Whether the last fetch is still within the TTL. A TTL of 0 is never fresh."""
    if minutes == 0:
        return False
    stamp = _stamp_path(cache_dir)
    try:
        age_seconds = time.time() - stamp.stat().st_mtime
    except OSError:
        return False
    return age_seconds < minutes * 60


def _touch_stamp(cache_dir: Path) -> None:
    stamp = _stamp_path(cache_dir)
    try:
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.write_text(str(int(time.time())), encoding="utf-8")
    except OSError:  # pragma: no cover - a read-only cache directory
        pass


def _local_hub(raw_path: str, notes: list[str]) -> HubHandle:
    path = Path(os.path.expandvars(raw_path)).expanduser()
    identity = paths.hub_identity(str(path))
    if not path.is_dir():
        notes.append(f"The configured hub path does not exist: {path}")
        return HubHandle(None, identity, "none", read_only=True, notes=notes)
    if not (path / paths.HUB_MARKER).is_file():
        notes.append(f"{path} has no {paths.HUB_MARKER}, so it does not look like a wizrelay hub.")
    return HubHandle(
        path,
        identity,
        "local",
        commit=gitcmd.head_commit(path),
        read_only=True,
        notes=notes,
    )


def resolve(
    config: Mapping[str, Any],
    *,
    allow_network: bool = True,
    allow_clone: bool = True,
) -> HubHandle:
    """Resolve the hub for this project.

    `allow_clone=False` is what hooks pass: a hook may refresh an existing cache but never
    create one. `allow_network=False` makes the whole resolution offline,
    which is what the test suite uses — there is no network in tests.
    """
    notes: list[str] = []
    hub = config.get("hub") or {}
    if not isinstance(hub, Mapping):
        hub = {}

    local = str(hub.get("path") or "").strip()
    if local:
        return _local_hub(local, notes)

    repo = str(hub.get("repo") or "").strip()
    if not repo:
        notes.append("No hub is configured.")
        return HubHandle(None, "", "none", notes=notes)

    if paths.has_embedded_credentials(repo):
        raise UsageError(
            "The configured hub URL embeds a credential.",
            reason="A URL of the form https://user:token@host is rejected so the token "
            "is never written to a cache directory or a lock file.",
            remedy="Use SSH, or a git credential helper, and set `hub.repo` without the "
            "credential.",
        )

    branch = str(hub.get("branch") or "main").strip() or "main"
    identity = paths.hub_identity(repo)
    cache_dir = paths.hub_cache_dir(repo)

    if not cache_dir.is_dir():
        if not (allow_network and allow_clone):
            notes.append(
                "The hub is not cached yet and this context does not clone. "
                "Run `wizrelay pull <ref>` once from a terminal."
            )
            return HubHandle(None, identity, "none", notes=notes)
        cache_dir.parent.mkdir(parents=True, exist_ok=True)
        result = gitcmd.clone(repo, cache_dir, branch=branch)
        if not result.ok:
            notes.append(f"Cloning the hub failed: {result.stderr.strip() or 'unknown error'}")
            return HubHandle(None, identity, "none", notes=notes)
        _touch_stamp(cache_dir)
    elif allow_network and not _is_fresh(cache_dir, ttl_minutes(config)):
        fetched = gitcmd.fetch(cache_dir, branch=branch)
        if fetched.ok:
            gitcmd.reset_hard(cache_dir, f"origin/{branch}")
            _touch_stamp(cache_dir)
        else:
            # Silent by contract: a network failure must not surface as an error
            # . The note is available to `doctor` and `--debug` only.
            notes.append(
                f"Refreshing the hub failed; using the cached copy. "
                f"({'timed out' if fetched.timed_out else fetched.stderr.strip()[:120]})"
            )

    return HubHandle(
        cache_dir,
        identity,
        "cache",
        commit=gitcmd.head_commit(cache_dir),
        read_only=False,
        notes=notes,
    )


def read_marker(hub_path: Path) -> dict[str, Any]:
    """Read `wizrelay-hub.json`, returning an empty mapping when it is absent."""
    try:
        data = json.loads((hub_path / paths.HUB_MARKER).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def local_policy(config: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    """Find the team's routing policy without resolving or fetching the hub.

    `read_policy` needs a resolved hub, and resolving one can run git. Routing is shown by
    `route`, `status`, `brief` and the session-start context as well as by `pull`, and if
    those disagree about which policy applies, the launch command a user is told to run
    does not match the tier they were shown.

    So this looks for the policy where it already is on disk — a configured working copy,
    or an existing cache directory — and never creates, fetches or resets anything. A hub
    that has never been cloned has no policy to find, and the plugin default applies.
    """
    hub = config.get("hub") or {}
    if not isinstance(hub, Mapping):
        return None

    local = str(hub.get("path") or "").strip()
    if local:
        path = Path(os.path.expandvars(local)).expanduser()
        return read_policy(path) if path.is_dir() else None

    repo = str(hub.get("repo") or "").strip()
    if not repo:
        return None
    cache_dir = paths.hub_cache_dir(repo)
    return read_policy(cache_dir) if cache_dir.is_dir() else None


def read_policy(hub_path: Optional[Path]) -> Optional[dict[str, Any]]:
    """Read the team's routing policy, if the hub ships one.

     A hub policy replaces the plugin default entirely rather than merging with it: a
     partially overridden tier table is harder to reason about than a complete one
    .
    """
    if hub_path is None:
        return None
    path = hub_path / "policies" / "routing-policy.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None
