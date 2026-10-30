"""Tracker adapters: identifier normalisation, deep links, and MCP facts.

A tracker adapter is two files:

* ``plugin/trackers/<type>.json`` — the machine-readable descriptor this module reads
* ``plugin/trackers/<type>.md`` — instructions a skill reads only when it needs them,
  which keeps the context budget small

The descriptor exists so that adding a tracker is data, not code. Three rules it encodes:

1. **One canonical identifier.** A user pastes `86c1abcd`, `CU-86c1abcd` or a URL; all of
   them resolve to `CU-86c1abcd`, which is what `task.json` stores and what branch-name
   detection looks for.
2. **An unverified MCP endpoint is never written anywhere.** `verified: false` means the
   adapter ships instructions only, and `wizrelay init --tracker` prints guidance rather
   than editing `.mcp.json`. Writing a guessed endpoint into a user's configuration is the
   one failure mode §9 singles out.
3. **Tracker content is data, not instruction.** This module never executes anything from
   a tracker; the skills say so explicitly in their own text.

Where the descriptors live
--------------------------
The canonical location is ``plugin/trackers/``, beside the library rather than inside it,
because that is where the plugin keeps it. A `pip install` of this project packages only
``wizrelay`` itself, so an installed CLI finds the catalogue through
``WIZRELAY_TRACKERS_DIR`` or not at all. Nothing that runs in CI needs it — `audit` is
tracker-agnostic — and `none` is always available as a built-in fallback, so the degraded
case stays usable. There is an open proposal to move the catalogue under the
package in a later version.
"""

from __future__ import annotations

import functools
import json
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Optional

from .errors import UsageError

__all__ = [
    "TAG_ANSWER",
    "TAG_PUBLISH",
    "TAG_QUESTION",
    "TAG_VERIFY",
    "available",
    "build_url",
    "descriptor",
    "instructions_path",
    "mcp_server_config",
    "normalize",
    "task_folder_name",
]

TAG_PUBLISH = "[WIZRELAY-PUBLISH]"
TAG_QUESTION = "[WIZRELAY-Q]"
TAG_ANSWER = "[WIZRELAY-A]"
TAG_VERIFY = "[WIZRELAY-VERIFY]"

#: Always available, so a repository with no tracker still has a working adapter and the
#: library never fails just because the catalogue directory is missing.
_BUILTIN_NONE: dict[str, Any] = {
    "type": "none",
    "display_name": "No tracker",
    "level": "full",
    "ref_pattern": r"^(?P<ref>[A-Za-z0-9][A-Za-z0-9._-]{0,60})$",
    "canonical_id": "{ref}",
    "url_template": None,
    "required_config": [],
    "mcp": None,
}


def catalogue_dir() -> Optional[Path]:
    """Locate ``plugin/trackers/``, or None when this install has no catalogue."""
    override = os.environ.get("WIZRELAY_TRACKERS_DIR")
    if override:
        path = Path(override).expanduser()
        return path if path.is_dir() else None

    here = Path(__file__).resolve()
    # plugin/lib/wizrelay/trackers.py -> plugin/trackers
    candidates = [
        here.parent.parent.parent / "trackers",
        here.parent / "trackers",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


@functools.lru_cache(maxsize=16)
def descriptor(tracker_type: str) -> dict[str, Any]:
    """Load one descriptor. Raises `UsageError` for an unknown tracker."""
    name = (tracker_type or "none").strip().lower()
    if name in ("", "none"):
        root = catalogue_dir()
        if root:
            path = root / "none.json"
            if path.is_file():
                return _read(path)
        return dict(_BUILTIN_NONE)

    root = catalogue_dir()
    if root is not None:
        path = root / f"{name}.json"
        if path.is_file():
            return _read(path)

    raise UsageError(
        f"Unknown tracker type {name!r}.",
        reason="No descriptor for it was found in the tracker catalogue.",
        remedy=f"Use one of: {', '.join(available())}.",
    )


_ECMA_GROUP = re.compile(r"\(\?<(?![=!])")


def _py_regex(pattern: str) -> str:
    """Translate an ECMA-262 named group to Python's spelling.

    Descriptors are written in the portable `(?<name>...)` form, so the same expression can
    be reused by a JSON Schema `pattern` or by a tool in another language. Python's `re`
    only understands `(?P<name>...)`, so the translation happens here rather than forcing
    every descriptor into one language's dialect. Lookbehind `(?<=` and `(?<!` are left
    alone.
    """
    return _ECMA_GROUP.sub("(?P<", pattern)


def _read(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UsageError(
            f"Tracker descriptor {path.name} could not be read.",
            reason=str(exc),
            remedy="Reinstall the plugin, or report this as a bug.",
        ) from exc
    if not isinstance(data, dict):
        raise UsageError(f"Tracker descriptor {path.name} is not an object.")
    return data


def available() -> list[str]:
    """Tracker types this installation can use, sorted, always including `none`."""
    root = catalogue_dir()
    if root is None:
        return ["none"]
    names = sorted(p.stem for p in root.glob("*.json"))
    return names or ["none"]


def instructions_path(tracker_type: str) -> Optional[Path]:
    """The `.md` instruction file a skill loads on demand, if the adapter ships one."""
    root = catalogue_dir()
    if root is None:
        return None
    path = root / f"{(tracker_type or 'none').lower()}.md"
    return path if path.is_file() else None


def _tracker_config(config: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    """Pull the tracker block out of a project or hub configuration."""
    if not config:
        return {}
    block = config.get("tracker")
    return dict(block) if isinstance(block, Mapping) else {}


def normalize(
    raw: str,
    tracker_type: str = "none",
    *,
    config: Optional[Mapping[str, Any]] = None,
) -> tuple[str, str]:
    """Turn whatever the user pasted into `(canonical_id, ref)`.

    Accepts the raw forms the adapter's `ref_pattern` describes and, as a convenience, a
    full tracker URL: the last path segment is extracted and re-matched, so pasting a
    browser address works.

    `id_prefix` from the configuration is honoured for trackers that allow custom
    identifiers: a ClickUp workspace using `TASK-1234` sets `id_prefix: "TASK-"`, and that
    prefix is stripped before matching and restored in the canonical identifier.
    """
    spec = descriptor(tracker_type)
    tracker_config = _tracker_config(config)
    text = (raw or "").strip()
    if not text:
        raise UsageError(
            "No task reference was given.",
            reason="A task reference is required to locate the package.",
            remedy="Pass the tracker reference, for example: wizrelay pull CU-86c1abcd",
        )

    candidates = [text]
    if "://" in text:
        tail = text.rstrip("/").rsplit("/", 1)[-1]
        tail = tail.split("?", 1)[0].split("#", 1)[0]
        if tail:
            candidates.append(tail)

    # A team may use its own identifier prefix. `id_prefix` is the canonical prefix, so it
    # is stripped before matching and restored afterwards; the default comes from the
    # descriptor's own `canonical_id` template.
    prefix = str(tracker_config.get("id_prefix") or "")
    if prefix:
        candidates += [
            candidate[len(prefix) :]
            for candidate in list(candidates)
            if candidate.upper().startswith(prefix.upper())
        ]

    # An adapter whose identifiers are conventionally uppercase (Jira, Linear) matches
    # case-insensitively and uppercases the result, so a pasted `proj-123` resolves.
    flags = re.IGNORECASE if spec.get("uppercase_ref") else 0
    pattern = re.compile(
        _py_regex(str(spec.get("ref_pattern") or _BUILTIN_NONE["ref_pattern"])), flags
    )
    for candidate in candidates:
        match = pattern.match(candidate)
        if not match:
            continue
        groups = match.groupdict()
        ref = groups.get("ref") or (match.group(1) if match.groups() else candidate)
        if spec.get("uppercase_ref"):
            ref = ref.upper()
        if prefix:
            canonical = f"{prefix}{ref}"
        else:
            template = str(spec.get("canonical_id") or "{ref}")
            fields = {"ref": ref}
            # A GitHub reference may carry its own `owner/repo#n` form.
            if groups.get("repo"):
                fields["repo"] = groups["repo"]
            canonical = template.format(**fields)
        return canonical, ref

    raise UsageError(
        f"{text!r} is not a valid {spec.get('display_name', tracker_type)} reference.",
        reason=f"It does not match the expected form for this tracker ({spec.get('ref_pattern')}).",
        remedy="Pass the identifier as it appears in the tracker, or the task URL.",
    )


def build_url(
    ref: str,
    tracker_type: str = "none",
    *,
    config: Optional[Mapping[str, Any]] = None,
    extra: Optional[Mapping[str, str]] = None,
) -> Optional[str]:
    """Build the deep link to the task, or None when it cannot be built.

    None is returned rather than a broken URL when the adapter needs configuration the
    project has not supplied — a Jira `base_url`, a GitHub `repo`. A wrong link in a
    tracker comment is worse than no link.
    """
    spec = descriptor(tracker_type)
    template = spec.get("url_template")
    if not template:
        return None

    fields: dict[str, str] = {"ref": ref}
    fields.update({k: str(v) for k, v in _tracker_config(config).items() if v})
    if extra:
        fields.update({k: str(v) for k, v in extra.items() if v})

    required = [str(name) for name in (spec.get("required_config") or [])]
    if any(not fields.get(name) for name in required):
        return None

    try:
        return str(template).format(**fields)
    except (KeyError, IndexError):
        return None


def mcp_server_config(tracker_type: str) -> Optional[dict[str, Any]]:
    """The MCP server entry for `.mcp.json`, **only** when the endpoint is verified.

    Writing an unverified endpoint into any configuration is forbidden, so an
    adapter with `verified: false` returns None and the caller prints instructions instead.
    """
    spec = descriptor(tracker_type)
    mcp = spec.get("mcp")
    if not isinstance(mcp, Mapping) or not mcp.get("verified"):
        return None
    name = str(mcp.get("name") or tracker_type)
    entry: dict[str, Any] = {}
    for key in ("type", "url", "command", "args", "headers"):
        if mcp.get(key) is not None:
            entry[key] = mcp[key]
    if not entry:
        return None
    return {name: entry}


def mcp_note(tracker_type: str) -> Optional[str]:
    """Human-readable note about the adapter's MCP status, for `init` and `doctor`."""
    spec = descriptor(tracker_type)
    mcp = spec.get("mcp")
    if not isinstance(mcp, Mapping):
        return None
    if mcp.get("verified"):
        return f"Verified endpoint: {mcp.get('url')} (auth: {mcp.get('auth', 'unknown')})"
    return str(mcp.get("note") or "This endpoint is not verified and is not written automatically.")


def display_name(tracker_type: str) -> str:
    try:
        return str(descriptor(tracker_type).get("display_name") or tracker_type)
    except UsageError:
        return tracker_type


def level(tracker_type: str) -> str:
    """`full` or `beta`, as the adapter is classified for v1."""
    try:
        return str(descriptor(tracker_type).get("level") or "beta")
    except UsageError:
        return "beta"


_FOLDER_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")


def task_folder_name(canonical_id: str, slug: str) -> str:
    """Build `<ID>-<slug>` and check it against the required pattern."""
    name = f"{canonical_id}-{slug}" if slug else canonical_id
    if not _FOLDER_SAFE.match(name):
        raise UsageError(
            f"{name!r} is not a usable package directory name.",
            reason="A package directory must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$.",
            remedy="Shorten the title, or set `slug` in task.json by hand.",
        )
    return name


def is_safe_folder_name(name: str) -> bool:
    """Whether a directory name found in a hub is safe to copy."""
    return bool(_FOLDER_SAFE.match(name))
