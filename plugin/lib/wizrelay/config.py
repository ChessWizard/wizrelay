"""Layered configuration (invariant I6).

Four layers merge, lowest precedence first:

1. library defaults — this module
2. hub defaults — copied from `wizrelay-hub.json` when `wizrelay init` runs
3. `.wizrelay/config.json` — shared with the team, committed
4. `.wizrelay/config.local.json` — personal, gitignored

A lower layer is overridden by a higher one. Merging is **deep** for objects, so
`config.local.json` can set `hub.path` without having to repeat `hub.repo`, and
**replacing** for arrays, because a list of paths is a single decision rather than
something to accumulate.

Keys beginning with `_` are comments and are dropped before validation (§6.4), which gives
hubs a way to annotate a JSON file that has no comment syntax.

This module is pure: callers read the files and hand the parsed dictionaries in.
"""

from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Optional

from . import schemas

__all__ = [
    "DEFAULTS",
    "deep_merge",
    "layer_config",
    "strip_comments",
    "unknown_keys",
]

#: Library defaults. Deliberately minimal: anything a team should decide lives in the hub
#: or the project, and anything with no sensible universal default is absent (invariant I1).
DEFAULTS: dict[str, Any] = {
    "schema_version": 1,
    "language": "en",
    "base_ref": "origin/main",
    "prompt_anchor": True,
    "session_title": True,
    "fetch_ttl_minutes": 10,
    "researcher_mention": "",
    "tracker": {"type": "none"},
    "hub": {"branch": "main"},
}


def strip_comments(value: Any) -> Any:
    """Recursively drop `_`-prefixed keys from objects."""
    if isinstance(value, dict):
        return {k: strip_comments(v) for k, v in value.items() if not str(k).startswith("_")}
    if isinstance(value, list):
        return [strip_comments(item) for item in value]
    return value


def deep_merge(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    """Merge `overlay` onto `base`, recursing into objects and replacing arrays.

    Neither argument is modified.

    >>> deep_merge({"hub": {"repo": "r", "branch": "main"}}, {"hub": {"path": "~/h"}})
    {'hub': {'repo': 'r', 'branch': 'main', 'path': '~/h'}}
    """
    out: dict[str, Any] = copy.deepcopy(dict(base))
    for key, value in overlay.items():
        existing = out.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            out[key] = deep_merge(existing, value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _hub_defaults(hub_marker: Mapping[str, Any]) -> dict[str, Any]:
    """Project the hub marker onto the configuration keys it supplies.

    `wizrelay-hub.json` and `config.json` are different documents with overlapping
    meaning: the hub states the team's language, tracker and base ref, and a project
    inherits them unless it says otherwise.
    """
    out: dict[str, Any] = {}
    for key in ("language", "base_ref", "researcher_mention"):
        if key in hub_marker:
            out[key] = hub_marker[key]
    if "tracker" in hub_marker and isinstance(hub_marker["tracker"], dict):
        out["tracker"] = dict(hub_marker["tracker"])
    if "default_branch" in hub_marker:
        out["hub"] = {"branch": hub_marker["default_branch"]}
    return out


def layer_config(
    *,
    hub_marker: Optional[Mapping[str, Any]] = None,
    shared: Optional[Mapping[str, Any]] = None,
    local: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Compose the four layers into the effective configuration.

    Every layer is comment-stripped first, so a `_comment` key in any of them never
    reaches validation or the merged result.
    """
    merged = deep_merge({}, DEFAULTS)
    if hub_marker:
        merged = deep_merge(merged, _hub_defaults(strip_comments(dict(hub_marker))))
    if shared:
        merged = deep_merge(merged, strip_comments(dict(shared)))
    if local:
        merged = deep_merge(merged, strip_comments(dict(local)))
    return merged


def unknown_keys(document: Mapping[str, Any], schema: str = "config") -> list[str]:
    """Top-level keys the schema does not define, for a warning rather than an error.

    A typo in a configuration key is silent otherwise: the value is simply never read.
    A warning, not a failure, so an older project still loads
    against a newer plugin.
    """
    known = set(schemas.known_keys(schema))
    return sorted(key for key in document if not str(key).startswith("_") and key not in known)


def effective_signals(task_routing: Mapping[str, Any], role: Optional[str]) -> dict[str, str]:
    """Combine task-wide signals with the role's overrides.

    Defaults are medium across the board, so a package that states no signals routes to
    the standard tier rather than the cheapest one.
    """
    signals: dict[str, str] = {"complexity": "medium", "risk": "medium", "ambiguity": "medium"}
    base = task_routing.get("signals") or {}
    if isinstance(base, dict):
        signals.update({k: v for k, v in base.items() if isinstance(v, str)})
    if role:
        per_role = (task_routing.get("role_signals") or {}).get(role) or {}
        if isinstance(per_role, dict):
            signals.update({k: v for k, v in per_role.items() if isinstance(v, str)})
    return signals


def merge_overrides(overrides: Mapping[str, Any], role: Optional[str]) -> dict[str, dict[str, Any]]:
    """Resolve `overrides["*"]` then `overrides[role]` into one per-phase mapping."""
    out: dict[str, dict[str, Any]] = {}
    for key in ("*", role):
        if not key:
            continue
        layer = overrides.get(key)
        if not isinstance(layer, dict):
            continue
        for phase, setting in layer.items():
            if isinstance(setting, dict):
                out[phase] = deep_merge(out.get(phase, {}), setting)
    return out


def iter_layers(
    hub_marker: Optional[Mapping[str, Any]],
    shared: Optional[Mapping[str, Any]],
    local: Optional[Mapping[str, Any]],
) -> Iterable[tuple[str, Mapping[str, Any]]]:
    """Yield `(label, document)` for each present layer, for `doctor` output."""
    yield "defaults", DEFAULTS
    if hub_marker:
        yield "hub", hub_marker
    if shared:
        yield "config.json", shared
    if local:
        yield "config.local.json", local


def require(config: Mapping[str, Any], key: str) -> Any:
    """Read a key that must be present, for callers that already validated."""
    if key not in config:
        raise KeyError(key)
    return config[key]


def get_path(config: Mapping[str, Any], dotted: str, default: Any = None) -> Any:
    """Read `a.b.c` from a nested mapping without raising on a missing level."""
    node: Any = config
    for part in dotted.split("."):
        if not isinstance(node, Mapping) or part not in node:
            return default
        node = node[part]
    return node


def commands(profile: Mapping[str, Any]) -> dict[str, str]:
    """The project's own commands, with empty values dropped."""
    raw = profile.get("commands") or {}
    if not isinstance(raw, Mapping):
        return {}
    return {k: v for k, v in raw.items() if isinstance(v, str) and v.strip()}


def paths_of(profile: Mapping[str, Any], key: str) -> list[str]:
    """A glob list from the profile, always a list of non-empty strings."""
    raw = profile.get(key) or []
    if not isinstance(raw, Sequence) or isinstance(raw, str):
        return []
    return [item for item in raw if isinstance(item, str) and item.strip()]
