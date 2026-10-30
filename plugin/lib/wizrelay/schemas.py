"""Runtime schema validation with the standard library only.

Two validators are kept deliberately:

* `schemas/*.schema.json` — JSON Schema draft 2020-12, for editors, CI and anyone
  validating a package outside this project.
* this module — the runtime check, because the plugin's runtime may not have
  `jsonschema` installed, and a third-party runtime import is forbidden.

Two implementations drift unless something stops them. `tests/unit/test_schemas.py` runs
both against every fixture in `tests/fixtures/schemas/{valid,invalid}/` and asserts they
agree, so a rule added to one side and not the other fails the build.

The specification below is a small declarative dialect, close enough to the JSON Schema
files to be read side by side. Error messages carry the dotted field path
(`scope.backend.allow`), which is what makes a `hub validate`
message actionable.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Optional, Union

__all__ = [
    "GLOB_PATTERN",
    "SCHEMAS",
    "SchemaError",
    "validate",
    "validate_or_raise",
]

from .errors import ValidationError

#: The same expression the JSON Schema files use for a scope glob: relative, no drive
#: letter, no `~`, no `..` segment.
GLOB_PATTERN = r"^(?!/)(?![A-Za-z]:)(?!~)(?!.*(^|/)\.\.($|/)).+$"

_DATE = r"^\d{4}-\d{2}-\d{2}$"
_SHA256 = r"^[0-9a-f]{64}$"
_SLUG = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$"
_ID = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"

TRACKER_TYPES = ("clickup", "github", "jira", "linear", "azure-devops", "none")
MODELS = ("haiku", "sonnet", "opus", "opusplan", "fable", "inherit")
EFFORTS = ("low", "medium", "high", "xhigh", "max")
ADVISORS = ("sonnet", "opus", "fable")
LEVELS = ("low", "medium", "high")
PHASES = ("plan", "implement", "verify", "ask")
STATUSES = ("draft", "published", "archived")
ENFORCEMENTS = ("strict", "ask", "off")
LANGUAGES = ("en", "tr")

Spec = dict[str, Any]


class SchemaError(ValidationError):
    """A document failed validation. `issues` holds every `path: message` line."""

    def __init__(self, name: str, issues: Sequence[str]) -> None:
        self.issues = list(issues)
        self.schema_name = name
        summary = f"{name}: {len(self.issues)} validation error(s)"
        super().__init__(
            summary,
            reason="; ".join(self.issues[:5]) + (" ..." if len(self.issues) > 5 else ""),
            remedy="Fix the fields named above, then run the command again.",
        )


# --------------------------------------------------------------------------------------
# Spec builders — thin wrappers so the schema definitions below read declaratively
# --------------------------------------------------------------------------------------


def _obj(
    *,
    required: Sequence[str] = (),
    properties: Optional[Mapping[str, Spec]] = None,
    additional: Union[bool, Spec] = False,
    min_properties: Optional[int] = None,
) -> Spec:
    return {
        "type": "object",
        "required": tuple(required),
        "properties": dict(properties or {}),
        "additional": additional,
        "min_properties": min_properties,
    }


def _str(
    *,
    enum: Optional[Sequence[str]] = None,
    pattern: Optional[str] = None,
    min_length: int = 0,
    max_length: Optional[int] = None,
) -> Spec:
    return {
        "type": "string",
        "enum": tuple(enum) if enum else None,
        "pattern": pattern,
        "min_length": min_length,
        "max_length": max_length,
    }


def _int(
    *, const: Optional[int] = None, minimum: Optional[int] = None, maximum: Optional[int] = None
) -> Spec:
    return {"type": "integer", "const": const, "minimum": minimum, "maximum": maximum}


def _bool() -> Spec:
    return {"type": "boolean"}


def _arr(
    items: Spec, *, min_items: int = 0, unique: bool = False, max_items: Optional[int] = None
) -> Spec:
    return {
        "type": "array",
        "items": items,
        "min_items": min_items,
        "max_items": max_items,
        "unique": unique,
    }


def _any() -> Spec:
    return {"type": "any"}


# --------------------------------------------------------------------------------------
# Shared fragments
# --------------------------------------------------------------------------------------

_GLOB = _str(pattern=GLOB_PATTERN, min_length=1, max_length=300)

_SIGNALS = _obj(
    properties={
        "complexity": _str(enum=LEVELS),
        "risk": _str(enum=LEVELS),
        "ambiguity": _str(enum=LEVELS),
        "kind": _str(enum=("mechanical",)),
    }
)

_PHASE_SETTING = _obj(
    properties={
        "model": _str(enum=MODELS),
        "effort": _str(enum=EFFORTS),
        "advisor": _str(enum=ADVISORS),
    }
)

_PHASE_SETTING_REQUIRED = _obj(
    required=("model", "effort"),
    properties={
        "model": _str(enum=MODELS),
        "effort": _str(enum=EFFORTS),
        "advisor": _str(enum=ADVISORS),
    },
)

_PHASES_REQUIRED = _obj(
    required=PHASES,
    properties=dict.fromkeys(PHASES, _PHASE_SETTING_REQUIRED),
)

_PHASE_OVERRIDES = _obj(properties=dict.fromkeys(PHASES, _PHASE_SETTING))

_TRACKER_CONFIG = _obj(
    properties={
        "type": _str(enum=TRACKER_TYPES),
        "id_prefix": _str(max_length=20),
        "base_url": _str(max_length=2000),
        "workspace": _str(max_length=200),
        "project": _str(max_length=200),
        "repo": _str(max_length=300),
    }
)


# --------------------------------------------------------------------------------------
# The six documents
# --------------------------------------------------------------------------------------

TASK: Spec = _obj(
    required=("schema_version", "id", "title", "version", "status", "roles", "scope"),
    properties={
        "schema_version": _int(const=1),
        "id": _str(pattern=_ID, min_length=1, max_length=120),
        "tracker": _obj(
            required=("type",),
            properties={
                "type": _str(enum=TRACKER_TYPES),
                "ref": _str(max_length=200),
                "url": _str(max_length=2000),
            },
        ),
        "title": _str(min_length=1, max_length=300),
        "slug": _str(pattern=_SLUG, max_length=60),
        "version": _int(minimum=0),
        "status": _str(enum=STATUSES),
        "updated_at": _str(pattern=_DATE),
        "roles": _arr(_str(min_length=1, max_length=60), min_items=1, unique=True),
        "repos": _obj(additional=_str(max_length=300)),
        "enforcement": _str(enum=ENFORCEMENTS),
        "scope": _obj(
            min_properties=1,
            additional=_obj(
                required=("allow",),
                properties={
                    "allow": _arr(_GLOB, min_items=1),
                    "deny": _arr(_GLOB),
                },
            ),
        ),
        "routing": _obj(
            properties={
                "signals": _SIGNALS,
                "role_signals": _obj(additional=_SIGNALS),
                "overrides": _obj(additional=_PHASE_OVERRIDES),
            }
        ),
        "changelog": _arr(
            _obj(
                required=("version", "summary"),
                properties={
                    "version": _int(minimum=0),
                    "date": _str(pattern=_DATE),
                    "summary": _str(min_length=1, max_length=500),
                },
            )
        ),
    },
)

CONFIG: Spec = _obj(
    required=("schema_version",),
    properties={
        "schema_version": _int(const=1),
        "hub": _obj(
            properties={
                "repo": _str(max_length=2000),
                "branch": _str(max_length=300),
                "path": _str(max_length=4096),
            }
        ),
        "role": _str(min_length=1, max_length=60),
        "tracker": _TRACKER_CONFIG,
        "language": _str(enum=LANGUAGES),
        "base_ref": _str(max_length=300),
        "prompt_anchor": _bool(),
        "session_title": _bool(),
        "fetch_ttl_minutes": _int(minimum=0, maximum=10080),
        "researcher_mention": _str(max_length=100),
    },
)

PROFILE: Spec = _obj(
    required=("schema_version",),
    properties={
        "schema_version": _int(const=1),
        "stack": _str(max_length=300),
        "commands": _obj(
            properties={
                "test": _str(max_length=500),
                "test_targeted": _str(max_length=500),
                "lint": _str(max_length=500),
                "typecheck": _str(max_length=500),
                "build": _str(max_length=500),
                "run": _str(max_length=500),
            }
        ),
        "codebase_size": _str(enum=("small", "medium", "large")),
        "test_maturity": _str(enum=LEVELS),
        "critical_paths": _arr(_GLOB),
        "legacy_paths": _arr(_GLOB),
        "incidental_allow": _arr(_GLOB),
    },
)

LOCK: Spec = _obj(
    required=("schema_version", "task_id", "folder", "version", "pulled_at", "files"),
    properties={
        "schema_version": _int(const=1),
        "task_id": _str(min_length=1, max_length=120),
        "tracker_ref": _str(max_length=200),
        "title": _str(max_length=300),
        "folder": _str(min_length=1, max_length=200),
        "version": _int(minimum=0),
        "hub_commit": _str(max_length=64),
        "hub_id": _str(max_length=200),
        "pulled_at": _str(min_length=10, max_length=40),
        "role": _str(max_length=60),
        "status": _str(enum=STATUSES),
        "files": _obj(additional=_str(pattern=_SHA256)),
        "routing": _obj(
            properties={
                "tier": _str(max_length=60),
                "score": _int(),
                "phases": _obj(additional=_any()),
                "launch": _str(max_length=1000),
            }
        ),
    },
)

ROUTING_POLICY: Spec = _obj(
    required=("schema_version", "tiers"),
    properties={
        "schema_version": _int(const=1),
        "modifiers": _obj(
            properties={
                "codebase_size_large": _int(minimum=0, maximum=10),
                "test_maturity_low": _int(minimum=0, maximum=10),
                "touches_critical_paths": _int(minimum=0, maximum=10),
                "touches_legacy_paths": _int(minimum=0, maximum=10),
            }
        ),
        "tiers": _arr(
            _obj(
                required=("name", "max_score", "phases"),
                properties={
                    "name": _str(min_length=1, max_length=60),
                    "max_score": _int(),
                    "phases": _PHASES_REQUIRED,
                },
            ),
            min_items=1,
        ),
        "mechanical": _obj(
            required=("name", "phases"),
            properties={
                "name": _str(min_length=1, max_length=60),
                "phases": _PHASES_REQUIRED,
            },
        ),
    },
)

HUB: Spec = _obj(
    required=("schema_version", "name"),
    properties={
        "schema_version": _int(const=1),
        "name": _str(min_length=1, max_length=120),
        "language": _str(enum=LANGUAGES),
        "tracker": _TRACKER_CONFIG,
        "roles": _arr(_str(min_length=1, max_length=60), min_items=1, unique=True),
        "default_branch": _str(max_length=300),
        "base_ref": _str(max_length=300),
        "default_enforcement": _str(enum=ENFORCEMENTS),
        "researcher_mention": _str(max_length=100),
    },
)

#: Name used on the command line and in error messages -> spec. The names match the file
#: stems under `schemas/`, which is what lets the equivalence test pair them up.
SCHEMAS: dict[str, Spec] = {
    "task": TASK,
    "config": CONFIG,
    "profile": PROFILE,
    "lock": LOCK,
    "routing-policy": ROUTING_POLICY,
    "wizrelay-hub": HUB,
}


# --------------------------------------------------------------------------------------
# The walker
# --------------------------------------------------------------------------------------


def _join(path: str, key: str) -> str:
    return key if not path else f"{path}.{key}"


def _type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return type(value).__name__


def _check(spec: Spec, value: Any, path: str, issues: list[str]) -> None:
    expected = spec["type"]
    if expected == "any":
        return

    if expected == "object":
        if not isinstance(value, dict):
            issues.append(f"{path or '<root>'}: expected an object, got {_type_name(value)}")
            return
        _check_object(spec, value, path, issues)
        return

    if expected == "array":
        if not isinstance(value, list):
            issues.append(f"{path or '<root>'}: expected an array, got {_type_name(value)}")
            return
        _check_array(spec, value, path, issues)
        return

    if expected == "boolean":
        if not isinstance(value, bool):
            issues.append(f"{path}: expected a boolean, got {_type_name(value)}")
        return

    if expected == "integer":
        # `bool` is a subclass of `int`; a JSON boolean is not an integer here.
        if isinstance(value, bool) or not isinstance(value, int):
            issues.append(f"{path}: expected an integer, got {_type_name(value)}")
            return
        const = spec.get("const")
        if const is not None and value != const:
            issues.append(f"{path}: must be {const}, got {value}")
        minimum = spec.get("minimum")
        if minimum is not None and value < minimum:
            issues.append(f"{path}: must be at least {minimum}, got {value}")
        maximum = spec.get("maximum")
        if maximum is not None and value > maximum:
            issues.append(f"{path}: must be at most {maximum}, got {value}")
        return

    if expected == "string":
        if not isinstance(value, str):
            issues.append(f"{path}: expected a string, got {_type_name(value)}")
            return
        enum = spec.get("enum")
        if enum and value not in enum:
            issues.append(f"{path}: {value!r} is not one of {', '.join(enum)}")
        min_length = spec.get("min_length") or 0
        if len(value) < min_length:
            issues.append(f"{path}: must be at least {min_length} character(s)")
        max_length = spec.get("max_length")
        if max_length is not None and len(value) > max_length:
            issues.append(f"{path}: must be at most {max_length} characters, got {len(value)}")
        pattern = spec.get("pattern")
        if pattern and not re.match(pattern, value):
            issues.append(f"{path}: {value!r} does not match the required form")
        return

    raise AssertionError(f"unknown spec type {expected!r}")  # pragma: no cover


def _check_object(spec: Spec, value: dict[str, Any], path: str, issues: list[str]) -> None:
    properties: dict[str, Spec] = spec["properties"]
    additional = spec["additional"]

    # Keys beginning with `_` are comments and are never validated.
    keys = [key for key in value if not key.startswith("_")]

    for name in spec["required"]:
        if name not in value:
            issues.append(f"{_join(path, name)}: required field is missing")

    min_properties = spec.get("min_properties")
    if min_properties is not None and len(keys) < min_properties:
        issues.append(
            f"{path or '<root>'}: needs at least {min_properties} entr"
            f"{'y' if min_properties == 1 else 'ies'}, got {len(keys)}"
        )

    for key in keys:
        child = value[key]
        child_path = _join(path, key)
        if key in properties:
            _check(properties[key], child, child_path, issues)
        elif isinstance(additional, dict):
            _check(additional, child, child_path, issues)
        elif additional is False:
            issues.append(f"{child_path}: unknown field")


def _check_array(spec: Spec, value: list[Any], path: str, issues: list[str]) -> None:
    min_items = spec.get("min_items") or 0
    if len(value) < min_items:
        issues.append(f"{path}: needs at least {min_items} item(s), got {len(value)}")
    max_items = spec.get("max_items")
    if max_items is not None and len(value) > max_items:
        issues.append(f"{path}: allows at most {max_items} item(s), got {len(value)}")
    if spec.get("unique"):
        seen: list[Any] = []
        for item in value:
            if item in seen:
                issues.append(f"{path}: duplicate item {item!r}")
                break
            seen.append(item)
    for index, item in enumerate(value):
        _check(spec["items"], item, f"{path}[{index}]", issues)


def validate(document: Any, schema: str) -> list[str]:
    """Validate `document` against a named schema and return the issues found.

    An empty list means the document is valid. Each issue is `path: message`, with the
    path in dotted form so it can be pasted into a search.
    """
    spec = SCHEMAS.get(schema)
    if spec is None:
        raise KeyError(f"unknown schema {schema!r}; known: {', '.join(sorted(SCHEMAS))}")
    issues: list[str] = []
    _check(spec, document, "", issues)
    return sorted(issues)


def validate_or_raise(document: Any, schema: str) -> None:
    """Validate and raise `SchemaError` when anything is wrong."""
    issues = validate(document, schema)
    if issues:
        raise SchemaError(schema, issues)


def known_keys(schema: str) -> Iterable[str]:
    """Top-level property names, used to warn about an unknown configuration key."""
    spec = SCHEMAS[schema]
    return tuple(spec["properties"])
